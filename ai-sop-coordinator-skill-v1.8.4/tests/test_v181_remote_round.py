import argparse
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "ai-sop-coordinator"
    / "scripts"
    / "coordinator_cli.py"
)
SPEC = importlib.util.spec_from_file_location("coordinator_cli_v181", MODULE_PATH)
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class AuthoritativeRemoteRoundTests(unittest.TestCase):
    def test_v181_release_identity_is_consistent(self):
        package = MODULE_PATH.parents[2]
        manifest = json.loads((package / "package-manifest.json").read_text(encoding="utf-8"))
        protocol = json.loads(
            (package / "ai-sop-coordinator" / "assets" / "protocol-version.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(cli.SKILL_VERSION, "1.8.4")
        self.assertEqual(manifest["package_version"], "1.8.4")
        self.assertEqual(protocol["skill_version"], "1.8.4")
        self.assertEqual(cli.BUILD_ID, manifest["build_id"])
        self.assertEqual(cli.BUILD_ID, protocol["build_id"])

    def test_parser_exposes_remote_for_round_and_stage_commands(self):
        parser = cli.build_parser()
        for argv in (
            ["validate-round", ".", "--stage", "02-solution-validation", "--round", "R1"],
            ["close-round", ".", "--stage", "02-solution-validation", "--round", "R1"],
            ["complete-round-review", ".", "--stage", "02-solution-validation", "--round", "R1"],
            ["validate-stage", ".", "--stage", "02-solution-validation"],
            ["close-stage", ".", "--stage", "02-solution-validation"],
        ):
            args = parser.parse_args(argv)
            self.assertEqual(args.remote, "origin")

    def test_bundled_remote_validator_is_the_default(self):
        path = cli.default_remote_member_cli()
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, "member_cli.py")
        self.assertEqual(path.parent.name, "remote-validator")

    def test_authoritative_inspection_reads_exact_registered_remote_ref(self):
        assignment_id = "A-02-R1-xiaotan-shared-review"
        assignment = {
            "assignment_id": assignment_id,
            "assignment_version": "1.0",
            "member_id": "xiaotan",
            "git_branch": "sop/member/xiaotan",
            "collaboration_model": "collective-participation",
            "participation_mode": "collective-round",
            "required_outputs": ["submission-manifest.yaml", "main-output.md"],
        }
        manifest = {"status": "submitted", "submitted_at": "2026-07-17T00:00:00Z"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sop = root / "sop"
            stage = sop / "stages" / "02-solution-validation"
            dispatch = stage / "dispatch"
            dispatch.mkdir(parents=True)
            assignment_path = dispatch / f"{assignment_id}.yaml"
            assignment_path.write_text(json.dumps(assignment), encoding="utf-8")

            def fake_load(path):
                path = Path(path)
                if path.name == "project-state.yaml":
                    return {"project_schema_version": cli.PROJECT_SCHEMA_VERSION}
                if path.name == "stage-state.yaml":
                    return {
                        "status": "collecting",
                        "expected_assignments": [assignment_id],
                        "rounds": {"R1": {"assignment_ids": [assignment_id]}},
                    }
                if path == assignment_path:
                    return assignment
                raise AssertionError(path)

            with (
                mock.patch.object(cli, "sop_root", return_value=sop),
                mock.patch.object(cli, "stage_root", return_value=stage),
                mock.patch.object(cli, "load_data", side_effect=fake_load),
                mock.patch.object(cli, "require_current_schema"),
                mock.patch.object(cli, "find_git_root", return_value=root),
                mock.patch.object(
                    cli,
                    "run_git",
                    return_value=subprocess.CompletedProcess([], 0, "https://example.invalid/repo.git\n", ""),
                ),
                mock.patch.object(
                    cli,
                    "resolve_observation_ref",
                    return_value=("origin/sop/member/xiaotan", "a" * 40),
                ),
                mock.patch.object(cli, "read_git_mapping", return_value=manifest),
                mock.patch.object(cli, "git_submission_files_complete", return_value=True),
                mock.patch.object(cli, "validate_remote_submission", return_value=(True, None)) as validate,
                mock.patch.object(cli, "submission_confirmation_projection", return_value={"status": "confirmed"}),
                mock.patch.object(cli, "collective_participation_issues", return_value=[]),
            ):
                result = cli.inspect_authoritative_stage(root, "02-solution-validation", "R1")

        self.assertEqual(result["observation_mode"], "exact-remote-ref")
        self.assertEqual(result["valid_submissions"][0]["observed_ref"], "origin/sop/member/xiaotan")
        self.assertEqual(result["valid_submissions"][0]["observed_head"], "a" * 40)
        self.assertEqual(result["missing_submissions"], [])
        self.assertEqual(result["invalid_submissions"], [])
        self.assertEqual(validate.call_args.kwargs["remote"], "origin")
        self.assertEqual(validate.call_args.kwargs["observed_head"], "a" * 40)

    def test_validate_round_uses_authoritative_inspection(self):
        args = argparse.Namespace(project_root=".", stage="02-solution-validation", round="R1", remote="upstream")
        result = {
            "missing_submissions": [],
            "invalid_submissions": [],
            "participation_issues": [],
        }
        with mock.patch.object(cli, "inspect_authoritative_stage", return_value=result) as inspect:
            with mock.patch("builtins.print"):
                cli.cmd_validate_round(args)
        inspect.assert_called_once_with(".", "02-solution-validation", "R1", remote="upstream")


if __name__ == "__main__":
    unittest.main()
