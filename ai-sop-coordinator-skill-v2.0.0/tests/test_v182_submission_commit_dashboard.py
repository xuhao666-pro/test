import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
CLI_PATH = PACKAGE / "ai-sop-coordinator" / "scripts" / "coordinator_cli.py"
DASHBOARD_PATH = (
    PACKAGE
    / "ai-sop-coordinator"
    / "assets"
    / "github-dashboard"
    / "sop_readme_dashboard.py"
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cli = load_module("coordinator_cli_v182", CLI_PATH)
dashboard = load_module("dashboard_v182", DASHBOARD_PATH)


class SubmissionCommitValidationTests(unittest.TestCase):
    def test_release_identity_is_consistent(self):
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text(encoding="utf-8"))
        protocol = json.loads(
            (PACKAGE / "ai-sop-coordinator" / "assets" / "protocol-version.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(cli.SKILL_VERSION, "1.8.4")
        self.assertEqual(manifest["package_version"], "2.0.0")
        self.assertEqual(cli.BUILD_ID, protocol["build_id"])

    def test_submission_commit_must_be_reachable_from_registered_ref(self):
        commit = "b" * 40
        with mock.patch.object(
            cli,
            "run_git",
            side_effect=(
                subprocess.CompletedProcess([], 0, commit + "\n", ""),
                subprocess.CompletedProcess([], 0, "", ""),
            ),
        ) as run_git:
            resolved = cli.resolve_submission_commit(
                Path("."), "origin/sop/member/xiaoniu", Path("sop/submission")
            )
        self.assertEqual(resolved, commit)
        self.assertEqual(run_git.call_args_list[1].args[1:4], ("merge-base", "--is-ancestor", commit))

    def test_authoritative_inspection_validates_submission_commit_not_branch_head(self):
        assignment_id = "A-02-R1-xiaoniu-review"
        assignment = {
            "assignment_id": assignment_id,
            "assignment_version": "1.0",
            "member_id": "xiaoniu",
            "git_branch": "sop/member/xiaoniu",
            "collaboration_model": "collective-participation",
            "participation_mode": "collective-round",
            "required_outputs": ["submission-manifest.yaml", "main-output.md"],
        }
        manifest = {"status": "submitted", "submitted_at": "2026-07-17T00:00:00Z"}
        branch_head = "a" * 40
        submission_commit = "b" * 40
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
                    return_value=("origin/sop/member/xiaoniu", branch_head),
                ),
                mock.patch.object(cli, "resolve_submission_commit", return_value=submission_commit),
                mock.patch.object(cli, "read_git_mapping", return_value=manifest) as read_mapping,
                mock.patch.object(cli, "git_submission_files_complete", return_value=True) as complete,
                mock.patch.object(cli, "validate_remote_submission", return_value=(True, None)) as validate,
                mock.patch.object(cli, "submission_confirmation_projection", return_value={}),
                mock.patch.object(cli, "collective_participation_issues", return_value=[]),
            ):
                result = cli.inspect_authoritative_stage(root, "02-solution-validation", "R1")

        self.assertEqual(read_mapping.call_args.args[1], submission_commit)
        self.assertEqual(complete.call_args.args[1], submission_commit)
        self.assertEqual(validate.call_args.kwargs["submission_commit"], submission_commit)
        self.assertEqual(
            result["valid_submissions"][0]["observed_submission_commit"], submission_commit
        )


class CurrentRoundDashboardTests(unittest.TestCase):
    def test_dashboard_cards_focus_on_current_collecting_round(self):
        state = {
            "project_name": "demo",
            "current_stage": "02-solution-validation",
            "highest_risk_level": "R0",
            "next_fixed_gate": "G2",
            "submission_tracking": {
                "totals": {"expected_count": 2, "valid_count": 1, "invalid_count": 1},
                "stages": {
                    "02-solution-validation": {
                        "current_round_id": "CURRENT",
                        "records": {
                            "HISTORICAL-INVALID": {
                                "round_id": "OLD",
                                "validation_status": "invalid",
                            },
                            "CURRENT-VALID": {
                                "round_id": "CURRENT",
                                "validation_status": "valid",
                            },
                        },
                    }
                },
            },
        }
        svg = dashboard.render_svg(state)
        self.assertIn("CURRENT-VALID", svg)
        self.assertNotIn("HISTORICAL-INVALID", svg)


if __name__ == "__main__":
    unittest.main()
