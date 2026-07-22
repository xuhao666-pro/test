import importlib.util
import json
import pathlib
import tempfile
import unittest


PACKAGE = pathlib.Path(__file__).parents[1]
CLI_PATH = PACKAGE / "ai-sop-member" / "scripts" / "member_cli.py"


def load_cli():
    spec = importlib.util.spec_from_file_location("member_cli_v180", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class V180MemberTests(unittest.TestCase):
    def test_release_identity_is_consistent(self):
        cli = load_cli()
        protocol = json.loads(
            (PACKAGE / "ai-sop-member" / "assets" / "protocol-version.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(cli.SKILL_VERSION, "1.8.1")
        self.assertEqual(protocol["skill_version"], "1.8.1")
        self.assertEqual(cli.BUILD_ID, protocol["build_id"])

    def test_exact_required_member_release_rejects_different_build(self):
        cli = load_cli()
        assignment = {
            "minimum_skill_version": "1.8.1",
            "required_member_skill": {
                "name": "ai-sop-member",
                "version": "1.8.1",
                "build_id": "member-cli-1.8.1-other",
                "package_path": "ai-sop-member-skill-v1.8.1",
                "release_commit": "abc123",
            },
        }
        with self.assertRaisesRegex(cli.SopError, "exact Member Skill"):
            cli.validate_exact_member_skill(assignment)

    def test_legacy_assignment_uses_minimum_version_behavior(self):
        cli = load_cli()
        cli.validate_exact_member_skill({"minimum_skill_version": "1.7.5"})

    def test_required_dialogue_cannot_be_skipped(self):
        cli = load_cli()
        assignment = {
            "minimum_skill_version": "1.8.0",
            "ai_dialogue_collaboration": {"mode": "required", "source": "project-policy"},
        }
        summary = cli.default_ai_dialogue_summary(assignment, "xiaotan")
        summary["status"] = "skipped"
        with self.assertRaisesRegex(cli.SopError, "cannot be skipped"):
            cli.validate_ai_dialogue_summary(summary, assignment, "xiaotan")

    def test_completed_dialogue_requires_all_collaboration_evidence(self):
        cli = load_cli()
        assignment = {
            "minimum_skill_version": "1.8.0",
            "ai_dialogue_collaboration": {"mode": "required", "source": "project-policy"},
        }
        summary = cli.default_ai_dialogue_summary(assignment, "xiaotan")
        summary["status"] = "completed"
        with self.assertRaises(cli.SopError):
            cli.validate_ai_dialogue_summary(summary, assignment, "xiaotan")

    def test_optional_dialogue_may_be_skipped(self):
        cli = load_cli()
        assignment = {
            "minimum_skill_version": "1.8.0",
            "ai_dialogue_collaboration": {"mode": "optional", "source": "project-policy"},
        }
        summary = cli.default_ai_dialogue_summary(assignment, "xiaotan")
        summary["status"] = "skipped"
        cli.validate_ai_dialogue_summary(summary, assignment, "xiaotan")


if __name__ == "__main__":
    unittest.main()
