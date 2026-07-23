# Skill 发行包清理

清理器 `.github/scripts/sop_skill_cleanup.py` 与工作流模板已迁移，但自动清理在 `bootstrap` 状态下禁用。

策略文件 `.github/sop-skill-retention.json` 固定保留：

- `ai-sop-coordinator-skill-v2.1.0`
- `ai-sop-coordinator-skill-v1.8.4`
- `ai-sop-member-skill-v2.1.0`

Coordinator 1.8.4 只保留发行谱系与历史审计。Member 2.1 是唯一正式 Member 包，内部同时携带 1.8.0 legacy、1.8.1 A–C 和 2.0.0 D–E 三套精确运行时；运行时版本不再反推出同版本的根发行目录。

项目激活后仍应先运行 plan-only，审核引用关系和候选列表，再由 Pull Request 完成清理；清理器不得直接删除 `main` 上的包。引用根既可以是目录，也可以是单个文件；受信运行时所属包只根据 `.github/sop-runtime-lock.json` 中经过审核的 `source` 路径识别，不根据 CLI 内的 `SKILL_VERSION` 猜测。
