import importlib.util
import json
import pathlib
import tempfile
import unittest


REPO = pathlib.Path(__file__).parents[2]
PACKAGE = pathlib.Path(__file__).parents[1]
CLI_PATH = PACKAGE / "ai-sop-coordinator" / "scripts" / "coordinator_cli.py"


def load_cli():
    spec = importlib.util.spec_from_file_location("coordinator_cli_v180", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class V180CoordinatorTests(unittest.TestCase):
    def test_release_identity_is_consistent(self):
        cli = load_cli()
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text(encoding="utf-8"))
        protocol = json.loads(
            (PACKAGE / "ai-sop-coordinator" / "assets" / "protocol-version.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(cli.SKILL_VERSION, "1.8.4")
        self.assertEqual(manifest["package_version"], "2.0.0")
        self.assertEqual(manifest["release_status"], "stable")
        self.assertEqual(protocol["skill_version"], "1.8.4")
        self.assertEqual(cli.BUILD_ID, protocol["build_id"])

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

    def test_release_confirmation_token_binds_exact_release(self):
        cli = load_cli()
        release = {
            "name": "ai-sop-member",
            "version": "1.8.0",
            "build_id": "member-cli-1.8.0-good",
            "package_path": "ai-sop-member-skill-v1.8.0",
            "release_commit": "abc123",
            "protocol_version": "1.0",
        }
        first = cli.skill_release_confirmation_token(release)
        changed = dict(release, build_id="member-cli-1.8.0-patched")
        self.assertNotEqual(first, cli.skill_release_confirmation_token(changed))


if __name__ == "__main__":
    unittest.main()
