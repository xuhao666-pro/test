# Gate 后 Skill 稳定版本确认

人工 Gate 通过、成员分支合并、祖先校验和阶段基线冻结完成后，下一阶段任务派发前确认仓库中的稳定 Member Skill。

```text
Gate 通过
→ 合并冻结提交
→ 冻结阶段基线
→ prepare-skill-release
→ 协调员审阅运行时身份、包身份、包路径和仓库 commit
→ confirm-skill-release
→ 下一阶段任务派发
```

## 双层发行身份

V2.1 起必须区分：

- 包身份：`package_version` 与包级 `build_id`，标识完整 Member 发行包。
- 任务运行时身份：`runtime_releases.<profile>.skill_version` 与 `build_id`，标识任务真正执行的 CLI 合同。

一个统一 Member 包可以同时承载 `legacy_predevelopment`、`predevelopment` 和 `development_delivery`。因此包版本与任务运行时版本可以不同；不得再要求 `package_version == CLI.SKILL_VERSION`。

系统为 A—C 新任务发现 `runtime_releases.predevelopment`，并且只接受同时满足以下条件的候选包：

- 包与运行时条目都是 `release_status: stable`。
- 包目录名、`package_version` 和包级 `build_id` 完整有效。
- 运行时声明的 `cli_path` 与 `protocol_path` 是包内相对路径，解析后不能逃逸包目录。
- 运行时条目、协议元数据和 CLI 的 `skill_version`、`build_id`、协议版本与项目 schema 完全一致。

仍可读取历史扁平 manifest，但其 profile 明确记录为 `legacy_predevelopment`；新统一包按 `package_version` 选择最新稳定候选。

协调员必须确认预览 Token，不手动输入版本号。确认只选择下一阶段任务使用的技术发布组合，`gate_effect` 为 `none`，不修改刚冻结的 Gate 或基线，也不自动安装 Skill。

A—C 新任务同时记录精确的运行时 `version`/`build_id`、`runtime_profile`、包 `package_version`/`package_build_id`、`package_path` 和 `release_commit`。Member Skill 在任务启动与提交链路中重复核对；任何不一致都阻塞任务。

当前 D—E 2.0 开发 CLI 的任务合同只写入精确运行时 `name`、`version` 和 `build_id`，包级 provenance 由仓库 runtime lock 与统一包 manifest 保护。不得把这种仓库级绑定表述为任务内已经携带 `package_path` 或 `release_commit`；在 D—E 合同完成包级字段升级前保持这一限制可见。
