# 系统迁移排除清单

本次采用白名单迁移，不复制原仓库 Git 历史，也不复制任何项目实例。

明确排除：

- `sop/**`：项目状态、成员、输入、需求池、任务分发、接受回执、提交、聚合、评审、Gate、基线和决定。
- `projectcode/**` 及任何历史业务实现。
- `dashboard/**`、旧 README 看板区块和项目专属看板说明。
- 旧项目已有的 `.github/skill-cleanup/history/**`；迁移完成后只允许由本仓库清理器生成、且通过 Token 与 Git 父提交校验的本仓库审计记录，禁止手工复制历史记录。
- 旧项目通知配置、看板策略、成员映射及任何个人信息。
- 旧 Issues、Pull Requests、Actions 记录、Artifacts、Caches、分支、标签、Environments、Secrets、Deploy keys 和 Webhooks。
- `__pycache__/**`、`*.pyc`、日志及本地临时目录。

迁移内容仅为稳定 Skill 发行包、通用运行时、自动化扩展、工作流模板和重新编写的无项目事实文档。发行包自身不可篡改的构建 provenance 不视为项目实例数据。
