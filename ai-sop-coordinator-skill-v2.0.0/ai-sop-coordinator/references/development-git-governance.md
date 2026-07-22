# 开发 Git 治理

## 分支职责

```text
sop/member/<member-id>       A—C 证据
feat/<DEV-ID>-<slug>         新功能代码
fix/<DEV-ID>-<slug>          普通缺陷
hotfix/<INC-ID>-<slug>       生产紧急修复
main                         受保护主干
```

任务记录精确 `base_commit`、`working_branch`、`target_branch`、主责、审查人和必需检查。证据分支不得代替代码分支。

## 合并范围

- G1—G3：全部已审核有效成员证据 commit。
- 单项代码任务：该任务经审查和 CI 批准的精确代码 commit。
- G4：验证发布范围任务已集成，不重新合并全员分支。
- G5：冻结交付事实，不产生代码合并许可。

## 保护

禁止直接 push `main`、绕过 PR/CI、审核后强推或用复制文件代替合并。高风险路径使用 CODEOWNERS 或等价专项责任规则。

审查和提交确认都绑定精确 commit；新提交使受影响结论 stale。合并后必须验证批准 commit 为 `main` 祖先。
