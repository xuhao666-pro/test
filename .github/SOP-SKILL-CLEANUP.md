# Skill 发行包清理

清理器 `.github/scripts/sop_skill_cleanup.py` 与工作流模板已迁移，但自动清理在 `bootstrap` 状态下禁用。

策略文件 `.github/sop-skill-retention.json` 固定保留：

- `ai-sop-coordinator-skill-v2.0.0`
- `ai-sop-coordinator-skill-v1.8.4`
- `ai-sop-member-skill-v2.0.0`
- `ai-sop-member-skill-v1.8.1`
- `ai-sop-member-skill-v1.8.0`

其中 Coordinator 1.8.4 和 Member 1.8.0/1.8.1 是 A–C 初始化、远端校验及发行回归链的兼容依赖，不能仅因 V2.0 包存在而删除。

项目激活后仍应先运行 plan-only，审核引用关系和候选列表，再由 Pull Request 完成清理；清理器不得直接删除 `main` 上的包，也不得清理 runtime lock 引用的版本。
