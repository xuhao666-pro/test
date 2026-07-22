# 开发与发布协调规则

## 草案边界

V2.0 使用 `scripts/development_cli.py` 自动管理开发任务预览与确认、独立代码审查、精确 commit 的 main 可达性、G4、灰度记录和 G5。内置 V1.8.4 Coordinator CLI 继续兼容 A—C 与 G1—G3。

## G3 交接

首批代码任务前确认：

- G3 人工结论有效。
- 所有审核冻结的有效成员证据 commit 已进入 `main` 并通过祖先验证。
- G3 基线已冻结，项目为 `development-entry-approved`。
- 稳定 Member Skill 已通过精确版本、构建、包和发行 commit 确认。
- 目标仓库、技术栈、责任人、分支保护、CI、灰度、停止和回滚草案完整。

缺失项创建准备任务，不签发宽泛代码任务。

## 开发任务

任务必须包含：

```yaml
task_id: DEV-001
baseline_ref: G3-V1.0@<commit>
requirement_refs: []
acceptance_refs: []
primary_owner: ""
reviewers: []
risk_owners: []
risk_level: R0
allowed_scope: []
forbidden_scope: []
expected_files: []
test_requirements: []
evidence_branch: sop/member/<member-id>
working_branch: feat/DEV-001-<slug>
target_branch: main
base_commit: ""
required_checks: []
stop_condition: ""
rollback_considerations: ""
```

首次创建只预览；当前用户确认 Token 后分发。成员 push 有效接受凭证后才投影 `accepted`。任务范围或基线变化时签发新版本。

## 提交、审查和集成

成员开发提交确认绑定实现 commit、完成报告哈希、owner 和个人立场，只授权个人开发贡献提交。代码审查由非作者执行，高风险任务增加专项责任人。

审查结论绑定任务版本和精确 commit。P0 阻塞合并；P1 原则上合并前修复。新 commit 使受影响结论 stale。

通过受保护 PR 和必需 CI 合并后，验证批准 commit 为 `main` 祖先并执行集成测试。PR、远端分支、口头完成或审查通过都不能单独计为已集成。

## 状态投影

```yaml
development_tracking:
  planned: 0
  accepted: 0
  in_progress: 0
  submitted: 0
  under_review: 0
  changes_requested: 0
  approved: 0
  integrated: 0
  blocked: 0
quality_tracking:
  tests_passed: 0
  ci_passed: 0
  security_reviewed: 0
  pending_checks: 0
release_tracking:
  gate_status: not-ready
  release_candidate: null
  rollout_percentage: 0
  observation_status: not-started
  rollback_readiness: unknown
  open_incidents: 0
  delivery_status: not-started
```

这些字段是事实源的只读摘要，不接受成员直接写入。

## 熔断

一轮未关闭任何 P0，或同一阻塞连续两次得到相同结果时停止重复派发。新任务必须改变前提、方法、责任人或证据标准。
