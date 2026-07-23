import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "ai-sop-member"


class DevelopmentContentTests(unittest.TestCase):
    def test_stable_manifest_declares_development_automation(self):
        manifest = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["package_version"], "2.1.0")
        self.assertEqual(manifest["release_status"], "stable")
        self.assertIn("deterministic D-E", manifest["runtime"]["automation_scope"])
        self.assertTrue((SKILL / "scripts" / "development_cli.py").is_file())
        self.assertEqual(
            manifest["runtime_releases"]["development_delivery"]["skill_version"],
            "2.0.0",
        )

    def test_member_skill_routes_development_and_release_references(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/development-delivery.md", text)
        self.assertIn("references/development-git-rules.md", text)
        self.assertIn("development_submission_confirmation", text)
        self.assertIn("development-entry-approved", text)

    def test_authority_chains_remain_separate(self):
        text = (SKILL / "references" / "development-delivery.md").read_text(encoding="utf-8")
        for term in ("implementation_commit", "completion_report_hash", "gate_effect: none", "代码审查", "G4", "G5"):
            self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
