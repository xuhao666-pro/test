import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = PACKAGE / "ai-sop-member/SKILL.md"
REFERENCE = PACKAGE / "ai-sop-member/references/version-preflight.md"


class VersionPreflightDocumentationTests(unittest.TestCase):
    def test_skill_requires_preflight_before_task_execution(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("references/version-preflight.md", text)
        self.assertIn("不匹配时提醒并停止", text)
        self.assertIn("不静默安装、升级、降级或覆盖全局 Skill", text)

    def test_reference_requires_exact_verified_remediation(self):
        text = REFERENCE.read_text(encoding="utf-8")
        self.assertIn("member-skill-version-mismatch", text)
        self.assertIn("SKILL_VERSION", text)
        self.assertIn("BUILD_ID", text)
        self.assertIn("sop_member_cli_<version-with-underscores>.py", text)
        self.assertIn("runtime_releases", text)
        self.assertIn("legacy_predevelopment", text)
        self.assertIn("包身份和任务运行时身份", text)
        self.assertIn("未开始任务，未创建或修改成员产物", text)


if __name__ == "__main__":
    unittest.main()
