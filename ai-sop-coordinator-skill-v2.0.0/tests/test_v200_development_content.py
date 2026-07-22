import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "ai-sop-coordinator"


class DevelopmentCoordinationContentTests(unittest.TestCase):
    def test_stable_manifest_declares_development_automation(self):
        manifest = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["package_version"], "2.0.0")
        self.assertEqual(manifest["release_status"], "stable")
        self.assertIn("deterministic development", manifest["runtime"]["automation_scope"])
        self.assertTrue((SKILL / "scripts" / "development_cli.py").is_file())

    def test_coordinator_routes_all_development_references(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for name in ("development-coordination.md", "development-gates.md", "development-git-governance.md"):
            self.assertIn(f"references/{name}", text)

    def test_gate_and_merge_scopes_are_separate(self):
        gates = (SKILL / "references" / "development-gates.md").read_text(encoding="utf-8")
        git_rules = (SKILL / "references" / "development-git-governance.md").read_text(encoding="utf-8")
        self.assertIn("G4 不产生全体成员分支合并", gates)
        self.assertIn("G5 不替代生产发布授权", gates)
        self.assertIn("单项代码任务", git_rules)
        self.assertIn("main` 祖先", git_rules)


if __name__ == "__main__":
    unittest.main()
