import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "ai-sop-member" / "scripts" / "development_cli.py"


def run(*args, cwd, ok=True):
    result = subprocess.run([sys.executable, str(CLI), *map(str, args)], cwd=cwd, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


class DevelopmentMemberCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "app.txt").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "switch", "-c", "feat/DEV-001-demo")
        self.assignment = self.repo / "sop/stages/04-development/dispatch/dev1/DEV-001-v1.0.yaml"
        self.assignment.parent.mkdir(parents=True)
        data = {
            "project_schema_version": "2.0",
            "assignment_id": "DEV-001",
            "assignment_version": "1.0",
            "stage_id": "04-development",
            "assignment_kind": "implementation",
            "member_id": "dev1",
            "human_owner": "owner1",
            "goal": "change app behavior",
            "allowed_scope": ["app.txt"],
            "forbidden_scope": ["secrets/"],
            "acceptance_criteria": ["AC-001"],
            "test_requirements": ["unit"],
            "required_checks": ["unit"],
            "reviewers": ["reviewer1"],
            "git": {"working_branch": "feat/DEV-001-demo", "target_branch": "main", "base_commit": self.base},
            "required_member_skill": {"name": "ai-sop-member", "version": "2.0.0", "build_id": "member-dev-cli-2.0.0-v1"},
            "dispatch_confirmation": {"status": "confirmed"},
        }
        self.assignment.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_accept_init_confirm_validate_and_submit(self):
        run("accept-assignment", self.assignment, "--member-id", "dev1", cwd=self.repo)
        init = json.loads(run("init", self.assignment, "--member-id", "dev1", cwd=self.repo).stdout)
        evidence = self.repo / init["submission_dir"]
        (evidence / "implementation-plan.md").write_text("Plan\n- modify app.txt\n- run unit tests\n", encoding="utf-8")
        (evidence / "test-plan.md").write_text("Tests\n- AC-001 unit path\n", encoding="utf-8")
        (evidence / "completion-report.md").write_text("Completed DEV-001 with tests and rollback notes.\n", encoding="utf-8")
        (self.repo / "app.txt").write_text("changed\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "feat: change app [DEV-001]")
        commit = git(self.repo, "rev-parse", "HEAD")
        run("record-check", evidence, "--assignment", self.assignment, "--member-id", "dev1", "--name", "unit", "--status", "passed", "--command", "python -m unittest", cwd=self.repo)
        preview = json.loads(run("prepare-confirmation", evidence, "--assignment", self.assignment, "--member-id", "dev1", "--implementation-commit", commit, "--position", "confirm", "--position-statement", "I confirm this change", cwd=self.repo).stdout)
        run("confirm-submission", evidence, "--assignment", self.assignment, "--member-id", "dev1", "--confirmed-by", "owner1", "--confirmation-token", preview["confirmation_token"], cwd=self.repo)
        run("validate", evidence, "--assignment", self.assignment, "--member-id", "dev1", cwd=self.repo)
        result = json.loads(run("submit", evidence, "--assignment", self.assignment, "--member-id", "dev1", cwd=self.repo).stdout)
        self.assertEqual(result["status"], "submitted")

    def test_report_change_makes_confirmation_stale(self):
        run("accept-assignment", self.assignment, "--member-id", "dev1", cwd=self.repo)
        evidence = self.repo / json.loads(run("init", self.assignment, "--member-id", "dev1", cwd=self.repo).stdout)["submission_dir"]
        for name in ("implementation-plan.md", "test-plan.md", "completion-report.md"):
            (evidence / name).write_text("complete evidence for DEV-001\n", encoding="utf-8")
        (self.repo / "app.txt").write_text("changed\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "feat: change app [DEV-001]")
        commit = git(self.repo, "rev-parse", "HEAD")
        run("record-check", evidence, "--assignment", self.assignment, "--member-id", "dev1", "--name", "unit", "--status", "passed", "--command", "unit", cwd=self.repo)
        preview = json.loads(run("prepare-confirmation", evidence, "--assignment", self.assignment, "--member-id", "dev1", "--implementation-commit", commit, "--position", "confirm", "--position-statement", "confirmed", cwd=self.repo).stdout)
        run("confirm-submission", evidence, "--assignment", self.assignment, "--member-id", "dev1", "--confirmed-by", "owner1", "--confirmation-token", preview["confirmation_token"], cwd=self.repo)
        (evidence / "completion-report.md").write_text("changed after confirmation\n", encoding="utf-8")
        failed = run("validate", evidence, "--assignment", self.assignment, "--member-id", "dev1", cwd=self.repo, ok=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("stale", failed.stderr.lower())


if __name__ == "__main__":
    unittest.main()
