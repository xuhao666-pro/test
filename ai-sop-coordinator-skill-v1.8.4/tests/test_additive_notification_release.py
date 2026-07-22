import json
import pathlib
import unittest


REPO = pathlib.Path(__file__).parents[2]
OLD = REPO / "ai-sop-coordinator-skill-v1.8.3"
NEW = pathlib.Path(__file__).parents[1]


class AdditiveReleaseTests(unittest.TestCase):
    def test_original_release_is_still_present(self):
        self.assertTrue(OLD.is_dir())
        self.assertTrue(NEW.is_dir())

    def test_release_metadata_is_184_and_member_binding_is_181(self):
        manifest = json.loads((NEW / "package-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["package_version"], "1.8.4")
        self.assertEqual(manifest["companion_package"]["exact_version"], "1.8.1")

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

    def test_member_release_has_no_worktree_changes(self):
        # The feature branch must not contain tracked edits under the Member package.
        import subprocess

        changed = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                "origin/main...HEAD",
                "--",
                "ai-sop-member-skill-v1.8.0",
                "ai-sop-member-skill-v1.8.1",
            ],
            cwd=REPO,
            text=True,
        ).strip()
        self.assertEqual(changed, "")


if __name__ == "__main__":
    unittest.main()
