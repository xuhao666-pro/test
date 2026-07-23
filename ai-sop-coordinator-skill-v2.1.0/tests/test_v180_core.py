import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
from types import SimpleNamespace


REPO = pathlib.Path(__file__).parents[2]
PACKAGE = pathlib.Path(__file__).parents[1]
CLI_PATH = PACKAGE / "ai-sop-coordinator" / "scripts" / "coordinator_cli.py"


def load_cli():
    spec = importlib.util.spec_from_file_location("coordinator_cli_v180", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def write_unified_member_package(root, *, cli_path="ai-sop-member/scripts/member_cli.py"):
    package = root / "ai-sop-member-skill-v2.1.0"
    protocol = package / "ai-sop-member" / "assets" / "protocol-version.yaml"
    cli_file = package / "ai-sop-member" / "scripts" / "member_cli.py"
    protocol.parent.mkdir(parents=True)
    cli_file.parent.mkdir(parents=True)
    (package / "package-manifest.json").write_text(
        json.dumps(
            {
                "manifest_schema_version": "2.1",
                "package_name": "ai-sop-member-skill",
                "package_version": "2.1.0",
                "release_status": "stable",
                "build_id": "member-package-2.1.0-unified-runtimes-v1",
                "runtime_releases": {
                    "predevelopment": {
                        "stage_ids": [
                            "A",
                            "B",
                            "C",
                        ],
                        "release_status": "stable",
                        "skill_version": "1.8.1",
                        "build_id": "member-cli-1.8.1-assignment-acceptance-v1",
                        "protocol_version": "1.0",
                        "project_schema_version": "1.5",
                        "cli_path": cli_path,
                        "protocol_path": "ai-sop-member/assets/protocol-version.yaml",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    protocol.write_text(
        json.dumps(
            {
                "protocol_version": "1.0",
                "project_schema_version": "1.5",
                "skill_version": "1.8.1",
                "build_id": "member-cli-1.8.1-assignment-acceptance-v1",
                "release_status": "stable",
            }
        ),
        encoding="utf-8",
    )
    cli_file.write_text(
        'SKILL_VERSION = "1.8.1"\n'
        'BUILD_ID = "member-cli-1.8.1-assignment-acceptance-v1"\n',
        encoding="utf-8",
    )
    return package


class V180CoordinatorTests(unittest.TestCase):
    def test_confirmed_unified_release_requires_complete_package_identity(self):
        cli = load_cli()
        project = {
            "skill_release_control": {
                "status": "confirmed",
                "confirmed_member_skill": {
                    "name": "ai-sop-member",
                    "version": "1.8.1",
                    "build_id": "member-cli-1.8.1-assignment-acceptance-v1",
                    "package_version": "2.1.0",
                    "package_path": "ai-sop-member-skill-v2.1.0",
                    "runtime_profile": "predevelopment",
                    "release_commit": "abc123",
                    "protocol_version": "1.0",
                },
            }
        }
        with self.assertRaisesRegex(cli.SopError, "package identity is incomplete"):
            cli.confirmed_member_release(project)

    def test_release_identity_is_consistent(self):
        cli = load_cli()
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text(encoding="utf-8"))
        protocol = json.loads(
            (PACKAGE / "ai-sop-coordinator" / "assets" / "protocol-version.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(cli.SKILL_VERSION, "1.8.5")
        self.assertEqual(cli.BUILD_ID, "coordinator-cli-1.8.5-unified-member-package-v1")
        self.assertEqual(manifest["manifest_schema_version"], "2.1")
        self.assertEqual(manifest["package_version"], "2.1.0")
        self.assertEqual(
            manifest["build_id"], "coordinator-package-2.1.0-unified-runtimes-v1"
        )
        self.assertEqual(manifest["release_status"], "stable")
        self.assertEqual(protocol["skill_version"], "1.8.5")
        self.assertEqual(cli.BUILD_ID, protocol["build_id"])

    def test_discovers_predevelopment_runtime_from_only_unified_member_package(self):
        cli = load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_unified_member_package(root)
            release = cli.discover_latest_stable_member_release(root)
            self.assertEqual(release["version"], "1.8.1")
            self.assertEqual(
                release["build_id"], "member-cli-1.8.1-assignment-acceptance-v1"
            )
            self.assertEqual(release["package_version"], "2.1.0")
            self.assertEqual(
                release["package_build_id"],
                "member-package-2.1.0-unified-runtimes-v1",
            )
            self.assertEqual(release["package_path"], "ai-sop-member-skill-v2.1.0")
            self.assertEqual(release["runtime_profile"], "predevelopment")

    def test_discovery_orders_candidates_by_package_version(self):
        cli = load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_unified_member_package(root)
            legacy = root / "ai-sop-member-skill-v1.9.0"
            skill = legacy / "ai-sop-member"
            (skill / "assets").mkdir(parents=True)
            (skill / "scripts").mkdir()
            (legacy / "package-manifest.json").write_text(
                json.dumps(
                    {
                        "package_name": "ai-sop-member-skill",
                        "package_version": "1.9.0",
                        "release_status": "stable",
                        "build_id": "member-cli-1.9.0-legacy-v1",
                    }
                ),
                encoding="utf-8",
            )
            (skill / "assets" / "protocol-version.yaml").write_text(
                json.dumps({"protocol_version": "1.0", "skill_version": "1.9.0"}),
                encoding="utf-8",
            )
            (skill / "scripts" / "member_cli.py").write_text(
                'SKILL_VERSION = "1.9.0"\nBUILD_ID = "member-cli-1.9.0-legacy-v1"\n',
                encoding="utf-8",
            )
            release = cli.discover_latest_stable_member_release(root)
            self.assertEqual(release["package_version"], "2.1.0")
            self.assertEqual(release["version"], "1.8.1")

    def test_unified_release_rejects_runtime_path_escape(self):
        cli = load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_unified_member_package(root, cli_path="../escaped-member-cli.py")
            (root / "escaped-member-cli.py").write_text(
                'SKILL_VERSION = "1.8.1"\n'
                'BUILD_ID = "member-cli-1.8.1-assignment-acceptance-v1"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                cli.SopError, "No consistent stable ai-sop-member release"
            ):
                cli.discover_latest_stable_member_release(root)

    def test_init_project_binds_unified_package_predevelopment_runtime(self):
        cli = load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_unified_member_package(root)
            subprocess.run(
                ["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"], cwd=root, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "fixture"], cwd=root, check=True, capture_output=True
            )
            cli.cmd_init_project(
                SimpleNamespace(
                    project_root=str(root),
                    project_id="unified-test",
                    project_name="Unified test",
                    coordinator_id="coordinator",
                    execution_mode="standard",
                    collaboration_model="role-based",
                    ai_dialogue_mode="required",
                    gate_confirmation_policy=None,
                    risk_level="R0",
                    risk_owner_role=[],
                    real_development_status="not-started",
                    member=[],
                    member_branch=[],
                    main_branch="main",
                )
            )
            state = cli.load_data(root / "sop" / "project-state.yaml")
            release = state["skill_release_control"]["confirmed_member_skill"]
            self.assertEqual(release["version"], "1.8.1")
            self.assertEqual(release["package_version"], "2.1.0")
            self.assertEqual(release["package_path"], "ai-sop-member-skill-v2.1.0")
            self.assertEqual(release["runtime_profile"], "predevelopment")
            self.assertEqual(release["release_commit"], subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True,
                capture_output=True, text=True
            ).stdout.strip())

    def test_project_ai_dialogue_defaults_to_required(self):
        cli = load_cli()
        self.assertEqual(
            cli.resolve_ai_dialogue_policy({}),
            {"mode": "required", "source": "project-policy"},
        )
        self.assertEqual(
            cli.resolve_ai_dialogue_policy(
                {"ai_dialogue_collaboration": {"mode": "optional", "source": "project-policy"}}
            )["mode"],
            "optional",
        )

    def test_discovers_only_stable_consistent_member_releases(self):
        cli = load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for version, status, build in (
                ("1.8.0", "stable", "member-cli-1.8.0-good"),
                ("1.9.0", "draft", "member-cli-1.9.0-draft"),
            ):
                package = root / f"ai-sop-member-skill-v{version}"
                skill = package / "ai-sop-member"
                (skill / "assets").mkdir(parents=True)
                (skill / "scripts").mkdir()
                (package / "package-manifest.json").write_text(
                    json.dumps(
                        {
                            "package_name": "ai-sop-member-skill",
                            "package_version": version,
                            "release_status": status,
                            "build_id": build,
                        }
                    ),
                    encoding="utf-8",
                )
                (skill / "assets" / "protocol-version.yaml").write_text(
                    json.dumps({"protocol_version": "1.0", "skill_version": version}),
                    encoding="utf-8",
                )
                (skill / "scripts" / "member_cli.py").write_text(
                    f'SKILL_VERSION = "{version}"\nBUILD_ID = "{build}"\n',
                    encoding="utf-8",
                )
            release = cli.discover_latest_stable_member_release(root)
            self.assertEqual(release["version"], "1.8.0")
            self.assertEqual(release["build_id"], "member-cli-1.8.0-good")
            self.assertEqual(release["package_version"], "1.8.0")
            self.assertEqual(release["runtime_profile"], "legacy_predevelopment")

    def test_release_confirmation_token_binds_exact_release(self):
        cli = load_cli()
        release = {
            "name": "ai-sop-member",
            "version": "1.8.1",
            "build_id": "member-cli-1.8.1-assignment-acceptance-v1",
            "package_version": "2.1.0",
            "package_build_id": "member-package-2.1.0-unified-runtimes-v1",
            "package_path": "ai-sop-member-skill-v2.1.0",
            "runtime_profile": "predevelopment",
            "release_commit": "abc123",
            "protocol_version": "1.0",
        }
        first = cli.skill_release_confirmation_token(release)
        changed = dict(release, package_build_id="member-package-2.1.0-patched")
        self.assertNotEqual(first, cli.skill_release_confirmation_token(changed))


if __name__ == "__main__":
    unittest.main()
