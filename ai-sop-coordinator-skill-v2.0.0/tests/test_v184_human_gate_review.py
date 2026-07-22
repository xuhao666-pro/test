import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
CLI_PATH = PACKAGE / "ai-sop-coordinator" / "scripts" / "coordinator_cli.py"
TEMPLATE = PACKAGE / "ai-sop-coordinator" / "assets" / "project-template" / "gate-review-pack.md"
CONTRACT = PACKAGE / "ai-sop-coordinator" / "references" / "human-gate-review-pack.md"
SKILL = PACKAGE / "ai-sop-coordinator" / "SKILL.md"
USAGE = PACKAGE / "USAGE.zh-CN.md"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


cli = load_module("coordinator_cli_v184", CLI_PATH)


class ReleaseIdentityTests(unittest.TestCase):
    def test_release_identity_and_member_binding(self):
        manifest = json.loads((PACKAGE / "package-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["package_version"], "2.0.0")
        self.assertEqual(manifest["release_status"], "stable")
        self.assertEqual(manifest["build_id"], "coordinator-dev-cli-2.0.0-v1")
        self.assertEqual(manifest["companion_package"]["exact_version"], "2.0.0")
        self.assertEqual(
            manifest["companion_package"]["exact_build_id"],
            "member-dev-cli-2.0.0-v1",
        )
        self.assertEqual(cli.SKILL_VERSION, "1.8.4")
        self.assertEqual(cli.BUILD_ID, "coordinator-cli-1.8.4-human-gate-review-v1")


class ReviewPackContractTests(unittest.TestCase):
    def test_template_declares_common_and_stage_specific_sections(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        for heading in (
            "本次要决定什么",
            "一页结论",
            "成员观点",
            "一致意见与未决分歧",
            "采纳、暂缓与拒绝",
            "风险、缺口与 Gate 条件",
            "对比版本变化",
            "全员评审检查表",
            "建议 Gate 结论",
            "原始材料附录",
        ):
            self.assertIn(f"## {heading}", text)
        self.assertIn("<!-- gate-review-metadata:", text)
        self.assertIn("[[FILL:", text)
        self.assertIn("<!-- stage-section:G1 -->", text)
        self.assertIn("<!-- stage-section:G2 -->", text)
        self.assertIn("<!-- stage-section:G3 -->", text)

    def test_stage_selection_retains_exactly_one_human_readable_block(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        expected = {
            "G1": "## G1 需求合同核心内容",
            "G2": "## G2 方案与验证核心内容",
            "G3": "## G3 开发准备核心内容",
        }
        for gate_id, heading in expected.items():
            rendered = cli._remove_unselected_stage_sections(template, gate_id)
            self.assertIn(heading, rendered)
            for other_gate, other_heading in expected.items():
                if other_gate != gate_id:
                    self.assertNotIn(other_heading, rendered)

    def test_contract_requires_stage_substance_and_read_only_authority(self):
        text = CONTRACT.read_text(encoding="utf-8")
        for phrase in (
            "用户痛点",
            "用户故事",
            "需求来源",
            "候选方案",
            "验证结果",
            "技术设计",
            "测试策略",
        ):
            self.assertIn(phrase, text)
        self.assertIn("不得反向覆盖", text)
        self.assertIn("不能替代 Gate", text)

    def test_skill_and_usage_route_the_review_pack_before_gate(self):
        expected = (
            "init-gate-review → 协调员 AI 撰写人工内容 → "
            "validate-gate-review → prepare-gate"
        )
        for path in (SKILL, USAGE):
            text = path.read_text(encoding="utf-8")
            self.assertIn(expected, text)
            self.assertIn("只读投影", text)
            self.assertIn("不能替代 Gate", text)


class ReviewPackFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.stage = "01-requirement-contract"
        self.stage_path = self.root / "sop" / "stages" / self.stage
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=self.root, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True
        )
        (self.root / "sop" / "roles").mkdir(parents=True)
        (self.root / "sop" / "decisions").mkdir(parents=True)
        (self.stage_path / "aggregation" / "provenance").mkdir(parents=True)
        (self.stage_path / "gate").mkdir(parents=True)
        cli.dump_data(
            self.root / "sop" / "project-state.yaml",
            {
                "project_schema_version": cli.PROJECT_SCHEMA_VERSION,
                "registered_member_ids": ["alice"],
                "collaboration_model": "collective-participation",
                "gate_confirmation_policy": "all-participants",
                "git_integration": {"main_branch": "main"},
            },
        )
        cli.dump_data(
            self.root / "sop" / "roles" / "alice.yaml",
            {"member_id": "alice", "status": "active", "git_branch": "sop/member/alice"},
        )
        cli.dump_data(
            self.stage_path / "stage-state.yaml",
            {"stage_id": self.stage, "gate_id": "G1", "status": "team-review"},
        )
        artifact = self.stage_path / "aggregation" / "requirement-contract.md"
        artifact.write_text("# 需求合同\n\n[P-001] 已审阅内容。\n", encoding="utf-8")
        cli.dump_data(
            self.stage_path / "aggregation" / "artifact-manifest.yaml",
            {
                "stage_id": self.stage,
                "artifacts": [
                    {
                        "path": "aggregation/requirement-contract.md",
                        "artifact_type": "requirement-contract",
                        "version": "V1.0-candidate",
                    }
                ],
            },
        )
        cli.dump_data(
            self.stage_path / "aggregation" / "participation-matrix.yaml",
            {"stage_id": self.stage, "rounds": {}},
        )
        cli.dump_data(
            self.stage_path / "aggregation" / "provenance" / "source-block-index.yaml",
            {"stage_id": self.stage, "blocks": [{"source_block_id": "SRC-001"}]},
        )
        cli.dump_data(
            self.stage_path / "aggregation" / "provenance" / "provenance-ledger.yaml",
            {"stage_id": self.stage, "entries": [{"provenance_id": "P-001"}]},
        )
        (self.stage_path / "aggregation" / "provenance" / "provenance-report.md").write_text(
            "# 来源报告\n\n覆盖率 100%。\n", encoding="utf-8"
        )
        cli.dump_data(
            self.root / "sop" / "decisions" / "decision-log.yaml",
            {"artifact_id": "A00", "decisions": []},
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "update-ref", "refs/remotes/origin/sop/member/alice", "HEAD"],
            cwd=self.root,
            check=True,
        )

    def tearDown(self):
        self.temp.cleanup()

    def render_complete_pack(self):
        path = cli.init_gate_review(self.root, self.stage, replace=False)
        text = path.read_text(encoding="utf-8")
        manifest = cli.load_data(self.stage_path / "aggregation" / "artifact-manifest.yaml")
        artifacts = manifest["artifacts"]
        first = artifacts[0]
        replacements = {
            "member_id": "alice",
            "member_name": "Alice",
            "artifact_type": first["artifact_type"],
            "artifact_label": "需求合同",
            "artifact_path": f"sop/stages/{self.stage}/{first['path']}",
            "citation_ids": "P-001",
        }
        text = re.sub(
            r"\[\[FILL:([^\]]+)\]\]",
            lambda match: replacements.get(match.group(1), "已填写"),
            text,
        )
        for artifact in artifacts[1:]:
            text += (
                f"\n<!-- artifact:{artifact['artifact_type']} -->\n"
                f"- [{artifact['artifact_type']}](sop/stages/{self.stage}/{artifact['path']})"
                " — 来源：P-001\n"
            )
        path.write_text(text, encoding="utf-8")
        return path

    def make_gate_ready_artifacts(self):
        artifact_types = sorted(cli.REQUIRED_GATE_ARTIFACT_TYPES[self.stage])
        artifacts = []
        for artifact_type in artifact_types:
            relative = f"aggregation/{artifact_type}.md"
            (self.stage_path / relative).write_text(
                f"# {artifact_type}\n\n[P-001] 已审阅内容。\n", encoding="utf-8"
            )
            artifacts.append(
                {
                    "path": relative,
                    "artifact_type": artifact_type,
                    "version": "V1.0-candidate",
                }
            )
        cli.dump_data(
            self.stage_path / "aggregation" / "artifact-manifest.yaml",
            {
                "stage_id": self.stage,
                "artifacts": artifacts,
                "traceability": {
                    "p0_source_coverage": 100,
                    "p0_user_story_coverage": 100,
                    "p0_user_story_source_coverage": 100,
                    "p0_user_story_requirement_coverage": 100,
                    "p0_acceptance_coverage": 100,
                },
            },
        )
        (self.stage_path / "aggregation" / "summary.md").write_text(
            "# 阶段汇总\n\n[P-001] 已完成。\n", encoding="utf-8"
        )

    def test_init_selects_only_current_stage_section(self):
        result = cli.init_gate_review(self.root, self.stage, replace=False)
        text = result.read_text(encoding="utf-8")
        self.assertEqual(result.name, "gate-review-pack.md")
        self.assertIn("## G1 需求合同核心内容", text)
        self.assertNotIn("## G2 方案与验证核心内容", text)
        self.assertNotIn("## G3 开发准备核心内容", text)

    def test_validate_complete_pack_returns_stable_hashes_and_coverage(self):
        self.render_complete_pack()
        result = cli.validate_gate_review(self.root, self.stage)
        self.assertTrue(result["document_hash"].startswith("sha256:"))
        self.assertTrue(result["source_fingerprint"].startswith("sha256:"))
        self.assertEqual(result["members"], ["alice"])
        self.assertEqual(result["artifact_types"], ["requirement-contract"])
        self.assertEqual(result["comparison_status"], "none")

    def test_validation_rejects_unfilled_template(self):
        cli.init_gate_review(self.root, self.stage, replace=False)
        with self.assertRaisesRegex(cli.SopError, "FILL"):
            cli.validate_gate_review(self.root, self.stage)

    def test_validation_rejects_missing_stage_substance_section(self):
        path = self.render_complete_pack()
        text = path.read_text(encoding="utf-8").replace(
            "### 用户、场景与用户痛点", "### 被错误删除的章节"
        )
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(cli.SopError, "用户、场景与用户痛点"):
            cli.validate_gate_review(self.root, self.stage)

    def test_gate_binding_rejects_review_pack_changed_after_preparation(self):
        path = self.render_complete_pack()
        reviewed = cli.validate_gate_review(self.root, self.stage)
        binding = cli.gate_review_material_binding(reviewed)
        self.assertEqual(binding["path"], "gate/gate-review-pack.md")
        self.assertEqual(binding["hash_algorithm"], "sha256-normalized-v1")
        self.assertTrue(binding["review_required"])
        path.write_text(path.read_text(encoding="utf-8") + "\n材料被修改。\n", encoding="utf-8")
        current = cli.validate_gate_review(self.root, self.stage)
        with self.assertRaisesRegex(cli.SopError, "stale"):
            cli.validate_bound_gate_review(binding, current)

    def test_baseline_copy_archives_exact_reviewed_markdown(self):
        path = self.render_complete_pack()
        cli.dump_data(self.stage_path / "gate" / "gate-decision.yaml", {"gate_id": "G1"})
        baseline = cli.copy_aggregation_to_baseline(self.stage_path, "G1-V1.0")
        archived = baseline / "gate-review-pack.md"
        self.assertEqual(archived.read_bytes(), path.read_bytes())

    def test_prepare_gate_binds_validated_human_review_material(self):
        self.make_gate_ready_artifacts()
        self.render_complete_pack()
        report = {
            "valid": True,
            "source_index_hash": "sha256:" + "a" * 64,
            "coverage_percent": 100,
            "p0_coverage_percent": 100,
            "generated_at": "2026-07-20T00:00:00Z",
        }
        args = SimpleNamespace(project_root=str(self.root), stage=self.stage, remote="origin")
        with mock.patch.object(cli, "validate_provenance", return_value=report):
            cli.cmd_prepare_gate(args)
        decision = cli.load_data(self.stage_path / "gate" / "gate-decision.yaml")
        binding = decision["human_review_material"]
        self.assertEqual(binding["path"], "gate/gate-review-pack.md")
        self.assertEqual(binding["hash_algorithm"], "sha256-normalized-v1")
        self.assertTrue(binding["review_required"])
        self.assertTrue(binding["document_hash"].startswith("sha256:"))
        self.assertTrue(binding["source_fingerprint"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
