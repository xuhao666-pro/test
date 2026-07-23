import json
import pathlib
import unittest


REPO = pathlib.Path(__file__).parents[2]
OLD = REPO / "ai-sop-coordinator-skill-v1.8.4"
NEW = pathlib.Path(__file__).parents[1]


class AdditiveReleaseTests(unittest.TestCase):
    def test_original_release_is_still_present(self):
        self.assertTrue(OLD.is_dir())
        self.assertTrue(NEW.is_dir())

    def test_release_metadata_is_v210_and_declares_member_runtime_requirements(self):
        manifest = json.loads((NEW / "package-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_schema_version"], "2.1")
        self.assertEqual(manifest["package_version"], "2.1.0")
        requirements = manifest["companion_package"]["runtime_requirements"]
        self.assertEqual(requirements["predevelopment"]["skill_version"], "1.8.1")
        self.assertEqual(requirements["development_delivery"]["skill_version"], "2.0.0")

    def test_sidecar_workflow_has_least_privilege_and_no_issue_command_trigger(self):
        workflow = (
            NEW
            / "ai-sop-coordinator"
            / "assets"
            / "github-notifications"
            / "sop-notifications.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("issue_comment", workflow)
        self.assertNotIn("pull_request_target", workflow)

    def test_reference_declares_reminder_only_boundary(self):
        reference = (
            NEW
            / "ai-sop-coordinator"
            / "references"
            / "github-issue-notifications.md"
        ).read_text(encoding="utf-8")
        self.assertIn("仅用于提醒", reference)
        self.assertIn("不得", reference)
        self.assertIn("GITHUB_TOKEN", reference)

if __name__ == "__main__":
    unittest.main()
