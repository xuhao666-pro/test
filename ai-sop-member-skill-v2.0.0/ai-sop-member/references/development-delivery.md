# 开发与发布任务执行规则

## 适用任务

本规则用于 `04-development` 和 `05-release` 的实现、测试、代码审查、集成验证、发布验证、灰度观察、事故响应和交付关闭任务。

当前发行提供专用 `scripts/development_cli.py`。开发任务必须由该 CLI 绑定 V2.0 任务、实现 commit、检查结果、完成报告哈希和登记 owner 的明确确认；CLI 不能替代独立代码审查、G4/G5 或生产授权。

## 开发准入

真实实现前验证：

- G3 结论有效，证据分支合并和祖先校验完成。
- G3 基线已冻结，项目状态为 `development-entry-approved`。
- 任务绑定精确 Skill、G3 基线、`base_commit` 和代码工作分支。
- 需求、验收、允许/禁止范围、审查人、风险责任和必需检查完整。

任一项缺失时保持 `blocked`，不修改目标代码。

## 实施顺序

1. 生成并 push 精确任务接受凭证。
2. 编写实施计划：文件、逻辑、数据读写、错误、权限、测试和回滚。
3. 先写测试或测试矩阵。
4. 在 `allowed_scope` 内完成最小实现。
5. 运行任务要求的 lint、类型、测试、构建和专项检查。
6. 形成完成报告，列出命令、结果、未运行项和风险。
7. 取得 owner 对实现 commit、报告哈希和个人立场的明确确认。
8. push 工作分支并创建 PR。
9. 由非作者完成代码审查和专项审查。
10. 合并后验证任务 commit 为 `main` 祖先并执行集成测试。

## 开发提交确认

```yaml
development_submission_confirmation:
  task_id: DEV-001
  assignment_version: "1.0"
  member_id: member-001
  human_owner: ""
  implementation_commit: ""
  completion_report_hash: "sha256:"
  personal_stance: confirm | oppose | question | reserve
  authority_scope: development-contribution-submission-only
  gate_effect: none
```

AI 不选择立场、不代签。commit、报告或任务变化后旧确认失效。该确认不替代代码审查、PR、G4、生产操作或 G5。

## 代码审查

绑定任务版本和精确 commit，检查验收、范围、异常、认证授权、数据、迁移、并发、幂等、兼容、日志、敏感信息、性能、测试和回滚。

- P0：阻塞合并。
- P1：原则上合并前修复；延期登记责任、影响和期限。
- P2：可选优化。

新 commit 出现后重新验证受影响结论。审查通过只授权该精确 commit 进入合并流程。

## 发布与事故

G4 前核对发布候选、集成任务、测试、迁移、配置、监控、灰度、停止和回滚。未获真实批准不得发布。

灰度异常时停止扩量并按批准顺序关闭开关或回滚。数据库回滚、数据修复、隐私暴露、客户沟通和密钥操作等待授权人决定。G5 前记录生产指标、事故、遗留、文档和复盘改进。

## 完成报告

```text
任务、版本、G3 基线和工作分支：
精确实现 commit：
修改文件与范围校验：
关联 REQ / AC：
测试、CI 命令与结果：
未运行项与影响：
开发提交确认：
代码审查与专项审查：
main 可达性与集成结果：
发布或事故状态：
残余风险与下一控制点：
```
