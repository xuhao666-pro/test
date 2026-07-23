# Skill 发行包清理

清理器 `.github/scripts/sop_skill_cleanup.py` 与工作流模板已迁移，但自动清理在 `bootstrap` 状态下禁用。

策略文件 `.github/sop-skill-retention.json` 固定保留：

- `ai-sop-coordinator-skill-v2.1.1`
- `ai-sop-member-skill-v2.1.0`

策略最终只固定 Coordinator 2.1.1 与 Member 2.1.0。Coordinator 1.8.4 与 2.1.0 由同名 annotated Git tag、Git 历史和逐轮清理审计保存，不再要求旧根目录常驻。Member 2.1 是唯一正式 Member 包，内部同时携带 1.8.0 legacy、1.8.1 A–C 和 2.0.0 D–E 三套精确运行时；运行时版本不再反推出同版本的根发行目录。

项目激活后仍应先运行 plan-only，审核引用关系和候选列表，再由 Pull Request 完成清理；清理器不得直接删除 `main` 上的包。引用根既可以是目录，也可以是单个文件；受信运行时所属包只根据 `.github/sop-runtime-lock.json` 中经过审核的 `source` 路径识别，不根据 CLI 内的 `SKILL_VERSION` 猜测。

正式 apply 会拒绝候选包内的未跟踪用户文件。被 Git 忽略的残留只有在命中明确缓存白名单（例如 `__pycache__`、`*.pyc`、pytest/mypy/ruff cache 或覆盖率缓存）时才会清除；`.env`、虚拟环境、日志等内容会阻塞操作并要求人工处理。

`--config` 可用于生成只读比较计划，但正式 apply 只接受仓库规范策略 `.github/sop-skill-retention.json`，确保审计校验器能从原始 Git 提交精确恢复策略内容。

每次清理必须生成 `.github/skill-cleanup/history/` 审计记录。系统校验器会重算确认 Token，并验证原始 HEAD、策略文件、包集合、实际删除、审计引入提交及其唯一父提交；审计提交后不得修改、移动或删除。所有执行该校验的 CI checkout 必须使用完整 Git 历史。
