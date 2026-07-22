# Gate 后 Skill 稳定版本确认

人工 Gate 通过、成员分支合并、祖先校验和阶段基线冻结完成后，下一阶段任务派发前确认仓库中的稳定 Member Skill。

```text
Gate 通过
→ 合并冻结提交
→ 冻结阶段基线
→ prepare-skill-release
→ 协调员审阅精确版本、build_id、包路径和仓库 commit
→ confirm-skill-release
→ 下一阶段任务派发
```

系统只推荐同时满足以下条件的包：

- `release_status: stable`
- 包版本、协议元数据和 CLI `SKILL_VERSION` 一致
- 包 `build_id` 与 CLI `BUILD_ID` 一致
- 协议兼容

协调员必须确认预览 Token，不手动输入版本号。确认只选择下一阶段任务使用的技术发布组合，`gate_effect` 为 `none`，不修改刚冻结的 Gate 或基线，也不自动安装 Skill。

新任务同时记录精确 `version`、`build_id`、包路径和 release commit。Member Skill 在 `workspace-check`、`inspect`、`init`、索引、确认、验证和提交时重复核对；任何不一致都阻塞任务。
