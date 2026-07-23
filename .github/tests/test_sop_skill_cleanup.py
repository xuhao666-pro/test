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
            'SKILL_VERSION = "1.8.5"\n', encoding="utf-8"
        )
        (scripts / "sop_member_cli.py").write_text(
            'SKILL_VERSION = "1.8.1"\n', encoding="utf-8"
        )
        (scripts / "sop_member_cli_1_8_0.py").write_text(
            'SKILL_VERSION = "1.8.0"\n', encoding="utf-8"
        )
        runtime_lock = root / ".github/sop-runtime-lock.json"
        runtime_lock.write_text(json.dumps({
            "runtimes": {
                "predevelopment_coordinator": {
                    "path": ".github/scripts/sop_coordinator_cli.py",
                    "source": (
                        "ai-sop-coordinator-skill-v2.0.0/"
                        "ai-sop-coordinator/scripts/coordinator_cli.py"
                    ),
                },
                "predevelopment_member": {
                    "path": ".github/scripts/sop_member_cli.py",
                    "source": (
                        "ai-sop-member-skill-v2.0.0/"
                        "ai-sop-member/scripts/member_cli.py"
                    ),
                },
                "legacy_predevelopment_member": {
                    "path": ".github/scripts/sop_member_cli_1_8_0.py",
                    "source": (
                        "ai-sop-member-skill-v2.0.0/"
                        "ai-sop-member/scripts/member_cli_1_8_0.py"
                    ),
                },
            }
        }), encoding="utf-8")
        sop = root / "sop"
        sop.mkdir()
        (sop / "task.yaml").write_text(
            'package_path: "ai-sop-member-skill-v1.0.0"\n', encoding="utf-8"
        )
        config = root / ".github/sop-skill-retention.json"
        config.write_text(json.dumps({
            "reference_roots": ["sop", ".github/sop-runtime-lock.json"],
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
            self.assertNotIn("ai-sop-member-skill-v1.8.1", retained)

    def test_single_file_reference_root_is_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.make_repo(root)
            config.write_text(json.dumps({
                "reference_roots": ["single-reference.json"],
                "retain_latest_stable": {"coordinator": 0, "member": 0},
                "pinned_packages": [],
            }), encoding="utf-8")
            (root / "single-reference.json").write_text(json.dumps({
                "package_path": "ai-sop-member-skill-v1.0.0",
            }), encoding="utf-8")
            references = cleanup.referenced_package_paths(
                root, ["single-reference.json"]
            )
            self.assertEqual(
                references["ai-sop-member-skill-v1.0.0"],
                ["single-reference.json"],
            )

    def test_multiple_runtime_identities_are_owned_by_one_unified_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_repo(root)
            lock_path = root / ".github/sop-runtime-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            runtime = cleanup.runtime_package_paths(root)
            self.assertEqual(
                set(runtime),
                {
                    "ai-sop-coordinator-skill-v2.0.0",
                    "ai-sop-member-skill-v2.0.0",
                },
            )
            self.assertEqual(
                len(runtime["ai-sop-member-skill-v2.0.0"]),
                2,
            )
            self.assertEqual(len(lock["runtimes"]), 3)
            self.assertNotIn("ai-sop-member-skill-v1.8.0", runtime)
            self.assertNotIn("ai-sop-member-skill-v1.8.1", runtime)

    def test_target_policy_makes_superseded_root_packages_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for role, version in (
                ("coordinator", "1.8.4"),
                ("coordinator", "2.0.0"),
                ("coordinator", "2.1.0"),
                ("coordinator", "2.1.1"),
                ("member", "1.8.0"),
                ("member", "1.8.1"),
                ("member", "2.0.0"),
                ("member", "2.1.0"),
            ):
                package = root / f"ai-sop-{role}-skill-v{version}"
                package.mkdir()
                (package / "package-manifest.json").write_text(json.dumps({
                    "package_version": version,
                    "release_status": "stable",
                }), encoding="utf-8")
            github = root / ".github"
            github.mkdir()
            (github / "sop-runtime-lock.json").write_text(json.dumps({
                "runtimes": {
                    "coordinator_ac": {"source": (
                        "ai-sop-coordinator-skill-v2.1.1/"
                        "ai-sop-coordinator/scripts/coordinator_cli.py"
                    )},
                    "coordinator_de": {"source": (
                        "ai-sop-coordinator-skill-v2.1.1/"
                        "ai-sop-coordinator/scripts/development_cli.py"
                    )},
                    "member_legacy": {"source": (
                        "ai-sop-member-skill-v2.1.0/"
                        "ai-sop-member/scripts/member_cli_1_8_0.py"
                    )},
                    "member_ac": {"source": (
                        "ai-sop-member-skill-v2.1.0/"
                        "ai-sop-member/scripts/member_cli.py"
                    )},
                    "member_de": {"source": (
                        "ai-sop-member-skill-v2.1.0/"
                        "ai-sop-member/scripts/development_cli.py"
                    )},
                }
            }), encoding="utf-8")
            config = github / "sop-skill-retention.json"
            config.write_text(json.dumps({
                "reference_roots": [".github/sop-runtime-lock.json"],
                "retain_latest_stable": {"coordinator": 1, "member": 1},
                "pinned_packages": [
                    "ai-sop-coordinator-skill-v2.1.1",
                    "ai-sop-member-skill-v2.1.0",
                ],
            }), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.name=test", "-c",
                 "user.email=test@example.invalid", "commit", "-qm", "fixture"],
                cwd=root,
                check=True,
            )
            plan = cleanup.build_plan(root, config)
            self.assertEqual(
                [item["path"] for item in plan["candidates"]],
                [
                    "ai-sop-coordinator-skill-v1.8.4",
                    "ai-sop-coordinator-skill-v2.0.0",
                    "ai-sop-coordinator-skill-v2.1.0",
                    "ai-sop-member-skill-v1.8.0",
                    "ai-sop-member-skill-v1.8.1",
                    "ai-sop-member-skill-v2.0.0",
                ],
            )
            retained = {item["path"]: item for item in plan["retained"]}
            self.assertIn(
                "installed-runtime-validator",
                retained["ai-sop-member-skill-v2.1.0"]["reasons"],
            )

    def test_apply_requires_exact_token_and_stages_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.make_repo(root)
            plan = cleanup.build_plan(root, config)
            info_exclude = root / ".git/info/exclude"
            info_exclude.write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
            cache = (
                root
                / "ai-sop-coordinator-skill-v1.0.0"
                / "tests"
                / "__pycache__"
                / "test_cache.pyc"
            )
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"ignored bytecode")
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

    def test_apply_refuses_untracked_nonignored_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.make_repo(root)
            candidate = root / "ai-sop-coordinator-skill-v1.0.0"
            (candidate / "local-notes.txt").write_text(
                "do not delete", encoding="utf-8"
            )
            plan = cleanup.build_plan(root, config)
            with self.assertRaisesRegex(
                cleanup.CleanupError, "untracked non-ignored"
            ):
                cleanup.apply_plan(
                    root,
                    config,
                    plan["confirmation_token"],
                    "test cleanup",
                )
            self.assertTrue((candidate / "package-manifest.json").is_file())
            self.assertTrue((candidate / "local-notes.txt").is_file())

    def test_apply_refuses_ignored_files_outside_cache_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.make_repo(root)
            candidate = root / "ai-sop-coordinator-skill-v1.0.0"
            info_exclude = root / ".git/info/exclude"
            info_exclude.write_text(".env\n*.log\n", encoding="utf-8")
            (candidate / ".env").write_text("LOCAL_SECRET=value", encoding="utf-8")
            plan = cleanup.build_plan(root, config)
            with self.assertRaisesRegex(cleanup.CleanupError, "cache allowlist"):
                cleanup.apply_plan(
                    root,
                    config,
                    plan["confirmation_token"],
                    "test cleanup",
                )
            self.assertTrue((candidate / "package-manifest.json").is_file())
            self.assertTrue((candidate / ".env").is_file())

    def test_apply_refuses_noncanonical_policy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.make_repo(root)
            custom = root / "custom-retention.json"
            custom.write_bytes(config.read_bytes())
            plan = cleanup.build_plan(root, custom)
            with self.assertRaisesRegex(cleanup.CleanupError, "canonical"):
                cleanup.apply_plan(
                    root,
                    custom,
                    plan["confirmation_token"],
                    "test cleanup",
                )


if __name__ == "__main__":
    unittest.main()
