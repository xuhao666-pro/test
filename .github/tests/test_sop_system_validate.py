import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


cleanup = load_module("cleanup_for_system_validation", SCRIPTS / "sop_skill_cleanup.py")
validator = load_module("sop_system_validate", SCRIPTS / "sop_system_validate.py")


class CleanupHistoryValidationTests(unittest.TestCase):
    def make_staged_cleanup(self, root: Path):
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        for version in ("1.0.0", "2.0.0"):
            package = root / f"ai-sop-member-skill-v{version}"
            package.mkdir()
            (package / "package-manifest.json").write_text(
                json.dumps(
                    {
                        "package_version": version,
                        "release_status": "stable",
                    }
                ),
                encoding="utf-8",
            )
        github = root / ".github"
        github.mkdir()
        config = github / "sop-skill-retention.json"
        config.write_text(
            json.dumps(
                {
                    "reference_roots": [],
                    "retain_latest_stable": {"coordinator": 0, "member": 1},
                    "pinned_packages": [],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=root,
            check=True,
        )
        plan = cleanup.build_plan(root, config)
        result = cleanup.apply_plan(
            root,
            config,
            plan["confirmation_token"],
            "test cleanup",
        )
        return root / result["audit_path"]

    def commit_cleanup(self, root: Path):
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "cleanup",
            ],
            cwd=root,
            check=True,
        )

    def test_accepts_cleanup_tool_staged_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_staged_cleanup(root)
            validator.validate_cleanup_history(root)

    def test_accepts_cleanup_tool_committed_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_staged_cleanup(root)
            self.commit_cleanup(root)
            validator.validate_cleanup_history(root)

    def test_rejects_record_modified_after_introduction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = self.make_staged_cleanup(root)
            self.commit_cleanup(root)
            record = json.loads(audit_path.read_text(encoding="utf-8"))
            record["reason"] = "tampered after commit"
            audit_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(validator.ValidationError, "modified"):
                validator.validate_cleanup_history(root)

    def test_rejects_token_not_bound_to_package_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = self.make_staged_cleanup(root)
            record = json.loads(audit_path.read_text(encoding="utf-8"))
            record["removed_packages"] = ["ai-sop-member-skill-v9.9.9"]
            audit_path.write_text(json.dumps(record), encoding="utf-8")
            subprocess.run(["git", "add", str(audit_path)], cwd=root, check=True)
            with self.assertRaisesRegex(
                validator.ValidationError, "confirmation token"
            ):
                validator.validate_cleanup_history(root)

    def test_rejects_nested_or_extra_history_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = self.make_staged_cleanup(root)
            extra = audit_path.parent / "copied-history"
            extra.mkdir()
            with self.assertRaisesRegex(
                validator.ValidationError, "contents do not match"
            ):
                validator.validate_cleanup_history(root)

    def test_rejects_package_content_moved_outside_package_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_staged_cleanup(root)
            source = "ai-sop-member-skill-v1.0.0/package-manifest.json"
            content = subprocess.run(
                ["git", "show", f"HEAD:{source}"],
                cwd=root,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            ).stdout
            archive = root / "archive/package-manifest.json"
            archive.parent.mkdir()
            archive.write_text(content, encoding="utf-8")
            subprocess.run(["git", "add", str(archive)], cwd=root, check=True)
            with self.assertRaisesRegex(
                validator.ValidationError, "not deleted in place"
            ):
                validator.validate_cleanup_history(root)

    def test_rejects_committed_audit_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = self.make_staged_cleanup(root)
            self.commit_cleanup(root)
            audit_path.unlink()
            subprocess.run(["git", "add", "-u"], cwd=root, check=True)
            self.commit_cleanup(root)
            with self.assertRaisesRegex(
                validator.ValidationError, "must remain present"
            ):
                validator.validate_cleanup_history(root)

    def test_system_validation_workflow_fetches_full_history(self):
        workflow = Path(__file__).parents[1] / "workflows/sop-system-validate.yml"
        self.assertIn("fetch-depth: 0", workflow.read_text(encoding="utf-8"))

    def test_accepts_two_consecutive_cleanup_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_staged_cleanup(root)
            self.commit_cleanup(root)

            package = root / "ai-sop-member-skill-v3.0.0"
            package.mkdir()
            (package / "package-manifest.json").write_text(
                json.dumps(
                    {
                        "package_version": "3.0.0",
                        "release_status": "stable",
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            self.commit_cleanup(root)

            config = root / ".github/sop-skill-retention.json"
            plan = cleanup.build_plan(root, config)
            cleanup.apply_plan(
                root,
                config,
                plan["confirmation_token"],
                "second cleanup",
            )
            validator.validate_cleanup_history(root)
            self.commit_cleanup(root)
            validator.validate_cleanup_history(root)


if __name__ == "__main__":
    unittest.main()
