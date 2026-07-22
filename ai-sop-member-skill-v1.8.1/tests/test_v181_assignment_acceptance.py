import argparse
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
CLI_PATH = PACKAGE / "ai-sop-member" / "scripts" / "member_cli.py"


def load_cli():
    spec = importlib.util.spec_from_file_location("member_cli_v181", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class AssignmentAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.cli = load_cli()

    def assignment(self):
        return {
            "assignment_id": "A-03-C01-R1-xiaotan-design",
            "assignment_version": "1.0",
            "member_id": "xiaotan",
            "human_owner": "谭雅暄",
            "git_branch": "sop/member/xiaotan",
            "minimum_skill_version": "1.8.1",
            "task_contract_hash": "a" * 64,
            "acceptance_policy": {
                "mode": "explicit-member-receipt",
                "required": True,
                "receipt_schema_version": "1.0",
                "gate_effect": "none",
            },
        }

    def test_release_identity_is_consistent(self):
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text(encoding="utf-8"))
        protocol = json.loads(
            (PACKAGE / "ai-sop-member/assets/protocol-version.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(self.cli.SKILL_VERSION, "1.8.1")
        self.assertEqual(manifest["package_version"], "1.8.1")
        self.assertEqual(self.cli.BUILD_ID, manifest["build_id"])
        self.assertEqual(self.cli.BUILD_ID, protocol["build_id"])

    def test_accept_command_creates_exact_receipt_and_is_idempotent(self):
        assignment = self.assignment()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            path = root / "sop/stages/03-development/dispatch/task.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(assignment, ensure_ascii=False), encoding="utf-8")
            args = argparse.Namespace(
                assignment=str(path), member_id="xiaotan", remote="origin",
                fetch=False, detached_validation=False,
            )
            with (
                mock.patch.object(self.cli, "validate_assignment", return_value=assignment),
                mock.patch.object(self.cli, "validate_git_workspace", return_value={}),
            ):
                self.cli.cmd_accept_assignment(args)
                self.cli.cmd_accept_assignment(args)
            summary = self.cli.validate_assignment_acceptance(path, assignment)
            self.assertEqual(summary["status"], "accepted")
            receipt = self.cli.load_data(self.cli.acceptance_path_for(path, assignment))
            self.assertEqual(receipt["assignment_document_hash"], self.cli.file_hash(path))
            self.assertEqual(receipt["member_skill"]["version"], "1.8.1")
            self.assertEqual(receipt["gate_effect"], "none")

    def test_missing_or_tampered_receipt_blocks_acceptance(self):
        assignment = self.assignment()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            path = root / "sop/stages/03-development/dispatch/task.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(assignment), encoding="utf-8")
            with self.assertRaisesRegex(self.cli.SopError, "not been explicitly accepted"):
                self.cli.validate_assignment_acceptance(path, assignment)
            pending = self.cli.validate_assignment_acceptance(
                path, assignment, require_accepted=False
            )
            self.assertEqual(pending["status"], "pending")


if __name__ == "__main__":
    unittest.main()
