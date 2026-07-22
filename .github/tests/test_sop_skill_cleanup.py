import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/sop_skill_cleanup.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sop_skill_cleanup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


cleanup = load_module()


class SkillCleanupTests(unittest.TestCase):
    def make_repo(self, root: Path):
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        for role, version, stable in (
            ("coordinator", "1.0.0", False),
            ("coordinator", "2.0.0", True),
            ("member", "1.0.0", True),
            ("member", "2.0.0", True),
        ):
            package = root / f"ai-sop-{role}-skill-v{version}"
            package.mkdir()
            (package / "package-manifest.json").write_text(
                json.dumps({
                    "package_version": version,
                    "release_status": "stable" if stable else "legacy",
                }), encoding="utf-8"
            )
        scripts = root / ".github/scripts"
        scripts.mkdir(parents=True)
        (scripts / "sop_coordinator_cli.py").write_text(
            'SKILL_VERSION = "2.0.0"\n', encoding="utf-8"
        )
        (scripts / "sop_member_cli.py").write_text(
            'SKILL_VERSION = "2.0.0"\n', encoding="utf-8"
        )
        sop = root / "sop"
        sop.mkdir()
        (sop / "task.yaml").write_text(
            'package_path: "ai-sop-member-skill-v1.0.0"\n', encoding="utf-8"
        )
        config = root / ".github/sop-skill-retention.json"
        config.write_text(json.dumps({
            "reference_roots": ["sop"],
            "retain_latest_stable": {"coordinator": 1, "member": 1},
            "pinned_packages": [],
        }), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
             "commit", "-qm", "fixture"], cwd=root, check=True
        )
        return config

    def test_plan_retains_runtime_latest_and_referenced_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.make_repo(root)
            plan = cleanup.build_plan(root, config)
            self.assertEqual(
                [item["path"] for item in plan["candidates"]],
                ["ai-sop-coordinator-skill-v1.0.0"],
            )
            retained = {item["path"]: item["reasons"] for item in plan["retained"]}
            self.assertIn("repository-reference", retained["ai-sop-member-skill-v1.0.0"])
            self.assertIn("installed-runtime-validator", retained["ai-sop-member-skill-v2.0.0"])

    def test_apply_requires_exact_token_and_stages_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.make_repo(root)
            plan = cleanup.build_plan(root, config)
            with self.assertRaisesRegex(cleanup.CleanupError, "token"):
                cleanup.apply_plan(root, config, "wrong", "test cleanup")
            result = cleanup.apply_plan(
                root, config, plan["confirmation_token"], "test cleanup"
            )
            self.assertFalse((root / "ai-sop-coordinator-skill-v1.0.0").exists())
            self.assertTrue((root / result["audit_path"]).is_file())
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-status"],
                cwd=root, text=True, encoding="utf-8", capture_output=True, check=True,
            ).stdout
            self.assertIn("ai-sop-coordinator-skill-v1.0.0", staged)
            self.assertIn(".github/skill-cleanup/history/", staged)


if __name__ == "__main__":
    unittest.main()
