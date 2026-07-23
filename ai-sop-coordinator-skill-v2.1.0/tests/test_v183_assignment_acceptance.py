import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
CLI_PATH = PACKAGE / "ai-sop-coordinator" / "scripts" / "coordinator_cli.py"
DASHBOARD_PATH = PACKAGE / "ai-sop-coordinator/assets/github-dashboard/sop_readme_dashboard.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


cli = load_module("coordinator_cli_v183", CLI_PATH)
dashboard = load_module("dashboard_v183", DASHBOARD_PATH)


class AssignmentAcceptanceProjectionTests(unittest.TestCase):
    def assignment(self):
        return {
            "assignment_id": "A-03-C01-R1-xiaotan-design",
            "assignment_version": "1.0",
            "member_id": "xiaotan",
            "human_owner": "谭雅暄",
            "git_branch": "sop/member/xiaotan",
            "minimum_skill_version": "1.8.1",
            "task_contract_hash": "a" * 64,
            "required_member_skill": {
                "name": "ai-sop-member",
                "version": "1.8.1",
                "build_id": "member-cli-1.8.1-assignment-acceptance-v1",
            },
            "acceptance_policy": {
                "mode": "explicit-member-receipt",
                "required": True,
                "receipt_schema_version": "1.0",
                "gate_effect": "none",
            },
        }

    def test_legacy_project_without_release_control_keeps_member_180(self):
        release = cli.confirmed_member_release({})
        self.assertEqual(release["version"], "1.8.0")
        self.assertEqual(
            release["build_id"], "member-cli-1.8.0-ai-dialogue-exact-release-v1"
        )
        self.assertEqual(release["package_version"], "2.1.0")
        self.assertEqual(release["package_path"], "ai-sop-member-skill-v2.1.0")
        self.assertEqual(release["runtime_profile"], "legacy_predevelopment")

    def test_remote_receipt_projects_accepted_and_preserves_observed_time(self):
        assignment = self.assignment()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / "sop/stages/03-development"
            path = stage / "dispatch/task.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(assignment), encoding="utf-8")
            receipt_path = cli.acceptance_receipt_path(stage, assignment)
            receipt = {
                "schema_version": "1.0", "status": "accepted",
                "assignment_id": assignment["assignment_id"],
                "assignment_version": "1.0", "member_id": "xiaotan",
                "human_owner": "谭雅暄", "git_branch": "sop/member/xiaotan",
                "assignment_path": path.relative_to(root).as_posix(),
                "assignment_document_hash": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                "task_contract_hash": "a" * 64,
                "receipt_path": receipt_path.relative_to(root).as_posix(),
                "accepted_at": "2026-07-20T01:00:00Z",
                "acceptance_method": "explicit-member-command", "gate_effect": "none",
                "member_skill": assignment["required_member_skill"],
            }
            previous = {"assignment_acceptance": {
                "observed_acceptance_commit": "b" * 40,
                "observed_at": "2026-07-20T02:00:00Z",
            }}
            with (
                mock.patch.object(cli, "resolve_submission_commit", return_value="b" * 40),
                mock.patch.object(cli, "read_git_mapping", return_value=receipt),
            ):
                result = cli.assignment_acceptance_projection(
                    git_root=root, stage_path=stage, assignment_path=path,
                    assignment=assignment, observed_ref="origin/sop/member/xiaotan",
                    observed_head="c" * 40, previous_record=previous,
                )
            self.assertEqual(result["status"], "accepted")
            self.assertEqual(result["observed_at"], "2026-07-20T02:00:00Z")
            self.assertEqual(result["gate_effect"], "none")

    def test_validator_selection_supports_new_and_legacy_exact_releases(self):
        base = PACKAGE / "ai-sop-coordinator/assets/remote-validator/member_cli.py"
        current = self.assignment()
        legacy = {"required_member_skill": {
            "name": "ai-sop-member",
            "version": "1.8.0",
            "build_id": "member-cli-1.8.0-ai-dialogue-exact-release-v1",
        }}
        self.assertEqual(cli.select_remote_member_cli(base, current), base)
        selected_legacy = cli.select_remote_member_cli(base, legacy)
        self.assertEqual(selected_legacy.name, "member_cli_1_8_0.py")

    def test_dashboard_labels_only_explicit_new_acceptance(self):
        accepted = dashboard.acceptance_label({"assignment_acceptance": {
            "required": True, "status": "accepted",
            "observed_at": "2026-07-20T02:00:00Z",
        }})
        pending = dashboard.acceptance_label({"assignment_acceptance": {
            "required": True, "status": "pending",
        }})
        legacy = dashboard.acceptance_label({"assignment_acceptance": {
            "required": False, "status": "legacy-not-required",
        }})
        self.assertIn("已接受", accepted)
        self.assertEqual(pending, "待接受")
        self.assertEqual(legacy, "")


if __name__ == "__main__":
    unittest.main()
