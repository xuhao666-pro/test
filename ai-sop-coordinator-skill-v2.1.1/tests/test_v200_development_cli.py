import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "ai-sop-coordinator" / "scripts" / "development_cli.py"


def run(*args, cwd, ok=True):
    result = subprocess.run([sys.executable, str(CLI), *map(str, args)], cwd=cwd, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


class DevelopmentCoordinatorCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        run("init-development", self.repo, "--g3-baseline", f"G3-V1.0@{self.base}", cwd=self.repo)
        self.spec = self.repo / "task.json"
        self.spec.write_text(json.dumps({
            "task_id": "DEV-001", "assignment_version": "1.0", "member_id": "dev1", "human_owner": "owner1",
            "goal": "implement demo", "requirement_refs": ["REQ-001"], "acceptance_refs": ["AC-001"],
            "allowed_scope": ["app.txt"], "forbidden_scope": ["secrets/"], "test_requirements": ["unit"],
            "required_checks": ["unit"], "reviewers": ["reviewer1"], "risk_owners": [], "risk_level": "R0",
            "working_branch": "feat/DEV-001-demo", "target_branch": "main", "base_commit": self.base,
        }, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def create_task(self):
        preview = json.loads(run("create-task", self.repo, "--spec", self.spec, cwd=self.repo).stdout)
        result = json.loads(run("create-task", self.repo, "--spec", self.spec, "--confirm-dispatch", preview["confirmation_token"], cwd=self.repo).stdout)
        return self.repo / result["assignment_path"]

    def test_task_review_integration_g4_rollout_and_g5(self):
        self.create_task()
        git(self.repo, "switch", "-c", "feat/DEV-001-demo", self.base)
        (self.repo / "app.txt").write_text("implementation\n", encoding="utf-8")
        git(self.repo, "add", "app.txt")
        git(self.repo, "commit", "-m", "feat: demo [DEV-001]")
        commit = git(self.repo, "rev-parse", "HEAD")
        self_review = run("record-review", self.repo, "--task-id", "DEV-001", "--reviewer", "dev1", "--commit", commit, "--verdict", "approved", cwd=self.repo, ok=False)
        self.assertNotEqual(self_review.returncode, 0)
        run("record-review", self.repo, "--task-id", "DEV-001", "--reviewer", "reviewer1", "--commit", commit, "--verdict", "approved", "--p0", "0", "--p1", "0", cwd=self.repo)
        git(self.repo, "switch", "main")
        git(self.repo, "merge", "--no-ff", "feat/DEV-001-demo", "-m", "merge DEV-001")
        run("record-integration", self.repo, "--task-id", "DEV-001", "--commit", commit, "--target-ref", "main", cwd=self.repo)
        g4 = json.loads(run("prepare-g4", self.repo, "--release-candidate", git(self.repo, "rev-parse", "main"), cwd=self.repo).stdout)
        run("approve-g4", self.repo, "--confirmation-token", g4["confirmation_token"], "--approved-by", "release-owner", cwd=self.repo)
        run("record-rollout", self.repo, "--percentage", "100", "--observation", "passed", cwd=self.repo)
        g5 = json.loads(run("prepare-g5", self.repo, cwd=self.repo).stdout)
        result = json.loads(run("approve-g5", self.repo, "--confirmation-token", g5["confirmation_token"], "--approved-by", "delivery-owner", cwd=self.repo).stdout)
        self.assertEqual(result["delivery_status"], "closed")

    def test_g4_blocks_unintegrated_task(self):
        self.create_task()
        failed = run("prepare-g4", self.repo, "--release-candidate", self.base, cwd=self.repo, ok=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("not integrated", failed.stderr.lower())


if __name__ == "__main__":
    unittest.main()
