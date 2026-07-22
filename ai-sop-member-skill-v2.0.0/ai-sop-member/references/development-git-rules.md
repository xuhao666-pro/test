# 开发任务 Git 规则

## 分支

```text
sop/member/<member-id>       A—C 证据分支
feat/<DEV-ID>-<slug>         新功能
fix/<DEV-ID>-<slug>          普通缺陷
hotfix/<INC-ID>-<slug>       紧急修复
main                         受保护主干
```

只使用任务登记的 `working_branch`、`target_branch` 和精确 `base_commit`。证据分支不得代替代码分支。

## 禁止事项

- 不直接 push `main`。
- 不自行 reset、强推或改变冻结基线。
- 不在已公开审查或多人依赖的分支上改写历史。
- 不用复制文件代替正式 Git 合并。
- 不把分支、PR、通知或口头声明解释为已集成。

## 提交与 PR

Commit 使用 `<type>(<scope>): <summary> [DEV-ID]`。PR 关联任务、REQ/AC、精确 commit、修改文件、测试/CI、风险、未运行项和回滚。

作者不得成为唯一审查人。高风险路径增加专项责任人。审查和提交确认都绑定精确 commit；新提交使受影响结论 stale。

## 集成完成

仅在必需 CI、独立审查、专项审查和 P0/P1 处理满足后合并。合并后验证批准 commit 是 `main` 祖先并运行集成检查。单任务集成不构成 G4 发布批准。
