import importlib.util
import json
import re
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / "ai-sop-member"


def load_cli(relative_path: str, module_name: str):
    path = PACKAGE / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def script_identity(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    version = re.search(r'^SKILL_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    build = re.search(r'^BUILD_ID\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    assert version and build
    return version.group(1), build.group(1)


class UnifiedPackageTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(
            (PACKAGE / "package-manifest.json").read_text(encoding="utf-8")
        )

    def test_package_identity_is_separate_from_runtime_identities(self):
        self.assertEqual(self.manifest["manifest_schema_version"], "2.1")
        self.assertEqual(self.manifest["package_version"], "2.1.0")
        self.assertEqual(
            self.manifest["build_id"],
            "member-package-2.1.0-unified-runtimes-v1",
        )
        self.assertEqual(
            set(self.manifest["runtime_releases"]),
            {"predevelopment", "development_delivery", "legacy_predevelopment"},
        )

    def test_every_runtime_matches_its_cli_and_protocol(self):
        expected = {
            "predevelopment": (
                "1.8.1",
                "member-cli-1.8.1-assignment-acceptance-v1",
                ["A", "B", "C"],
                "stable",
            ),
            "development_delivery": (
                "2.0.0",
                "member-dev-cli-2.0.0-v1",
                ["D", "E"],
                "stable",
            ),
            "legacy_predevelopment": (
                "1.8.0",
                "member-cli-1.8.0-ai-dialogue-exact-release-v1",
                ["A", "B", "C"],
                "legacy",
            ),
        }
        for runtime_name, expected_profile in expected.items():
            with self.subTest(runtime=runtime_name):
                identity = expected_profile[:2]
                runtime = self.manifest["runtime_releases"][runtime_name]
                cli_path = (PACKAGE / runtime["cli_path"]).resolve()
                protocol_path = (PACKAGE / runtime["protocol_path"]).resolve()
                cli_path.relative_to(PACKAGE.resolve())
                protocol_path.relative_to(PACKAGE.resolve())
                self.assertTrue(cli_path.is_file())
                self.assertTrue(protocol_path.is_file())
                protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    (runtime["skill_version"], runtime["build_id"]), identity
                )
                self.assertEqual(script_identity(cli_path), identity)
                self.assertEqual(
                    (protocol["skill_version"], protocol["build_id"]), identity
                )
                self.assertEqual(
                    runtime["protocol_version"], protocol["protocol_version"]
                )
                self.assertEqual(runtime["stage_ids"], expected_profile[2])
                self.assertEqual(runtime["release_status"], expected_profile[3])

    def test_v181_task_accepts_v210_package_path(self):
        cli = load_cli(
            "ai-sop-member/scripts/member_cli.py", "member_cli_v181_from_v210"
        )
        assignment = {
            "minimum_skill_version": "1.8.1",
            "required_member_skill": {
                "name": "ai-sop-member",
                "version": "1.8.1",
                "build_id": "member-cli-1.8.1-assignment-acceptance-v1",
                "protocol_version": "1.0",
                "package_version": "2.1.0",
                "package_path": "ai-sop-member-skill-v2.1.0",
                "release_commit": "abc123",
            },
        }
        cli.validate_exact_member_skill(assignment)

    def test_legacy_v180_runtime_remains_self_contained(self):
        cli = load_cli(
            "ai-sop-member/scripts/member_cli_1_8_0.py",
            "member_cli_v180_from_v210",
        )
        assignment = {
            "minimum_skill_version": "1.8.0",
            "required_member_skill": {
                "name": "ai-sop-member",
                "version": "1.8.0",
                "build_id": "member-cli-1.8.0-ai-dialogue-exact-release-v1",
                "protocol_version": "1.0",
                "package_version": "2.1.0",
                "package_path": "ai-sop-member-skill-v2.1.0",
                "release_commit": "abc123",
            },
        }
        cli.validate_exact_member_skill(assignment)
        self.assertEqual(cli.SKILL_VERSION, "1.8.0")
        self.assertEqual(
            cli.BUILD_ID, "member-cli-1.8.0-ai-dialogue-exact-release-v1"
        )

        changed = dict(assignment)
        changed["required_member_skill"] = dict(
            assignment["required_member_skill"], build_id="member-cli-1.8.0-other"
        )
        with self.assertRaisesRegex(cli.SopError, "exact Member Skill"):
            cli.validate_exact_member_skill(changed)


if __name__ == "__main__":
    unittest.main()
