# Adaptive Grill 输出契约

两个文件均使用 UTF-8 YAML 或 JSON 兼容 YAML，保留成员原话，时间使用 ISO 8601。`init` 自动创建初始结构，AI 只更新当前成员本次提交目录中的文件。

## human-collaboration-log.yaml

核心字段：

```yaml
schema_version: "1.0"
session_id: HC-<assignment>-v<version>
assignment_id: <assignment-id>
member_id: <member-id>
mode: adaptive-grill
human_owner: <registered-owner>
status: grill-in-progress
collaboration_consent:
  human_owner: <registered-owner>
  understands_recording: true
  understands_evidence_boundary: true
  agrees_to_participate: true
exchanges:
  - exchange_id: EX-001
    topic: problem-definition
    asked_at: "2026-01-01T00:00:00Z"
    ai_question: 这个任务最需要解决的真实问题是什么？先不要说解决方案。
    human_answer: <成员原话>
    answer_classification: [member-judgment]
    evidence_type: member-direct
    follow_up_required: true
    follow_up_reason: <原因>
    correction_of: null
confirmations:
  - confirmation_id: CONF-001
    subject: problem-definition
    statement: <确认内容>
    status: confirmed
    confirmed_at: "2026-01-01T00:10:00Z"
coverage:
  target_users: complete
  scenarios: complete
  problems: complete
  business_value: complete
  evidence: complete
  counterexamples: complete
  scope: complete
  priority: complete
  risks: complete
gaps: []
question_count: 12
max_questions: 20
```

允许状态：`not-started`、`grill-in-progress`、`awaiting-human-answer`、`analyzing-answer`、`follow-up-required`、`awaiting-human-confirmation`、`grill-completed`、`blocked`。

`question_count` 必须等于 `exchanges` 数量且不得超过任务上限。每个任务指定主题在完成时都必须为 `complete`。阻塞 gap 使用 `blocking: true`，并记录责任人和验证方式。

## grill-summary.yaml

```yaml
schema_version: "1.0"
session_id: HC-<assignment>-v<version>
assignment_id: <assignment-id>
member_id: <member-id>
status: grill-completed
problem_definition:
  statement: <已确认问题定义>
  evidence_refs: [EX-001, CONF-001]
  confirmation: confirmed
target_users: []
scenarios: []
member_judgments: []
ai_inferences: []
p0_scope: []
p1_scope: []
excluded_scope: []
risks: []
counterexamples: []
unknowns: []
unresolved_disagreements: []
required_confirmations:
  problem-definition: confirmed
  p0-scope: confirmed
  unresolved-disagreements: confirmed
```

每个摘要项应保留 `evidence_refs`。AI 新推演只进入 `ai_inferences` 并标记 `evidence_type: ai-inference`。空的未决分歧清单也必须由真实成员明确确认。

阻塞时保留已有交流，将两个文件状态设为 `blocked`，并添加：

```yaml
blocking:
  code: human-unavailable
  reason: 缺少真实成员对 P0 的确认。
  missing_confirmations: [p0-scope]
  return_to: <coordinator-id>
```

不得为通过校验把 `pending` 人工改为 `confirmed`。

## 与最终提交确认的关系

以上 Grill 文件只证明访谈过程、主题覆盖和阶段性确认。Grill 结果映射成 `main-output.md` 后正文仍可能变化，因此所有 V1.7.5 新任务还必须按 `submission-confirmation.md` 单独确认最终正文哈希和个人立场。`grill-completed` 不能替代 `human-submission-confirmation.yaml: status: confirmed`。
