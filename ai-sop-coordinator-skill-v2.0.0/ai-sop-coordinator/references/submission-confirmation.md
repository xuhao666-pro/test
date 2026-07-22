# 协调端成员提交确认契约

## 独立于 Grill

`human_collaboration` 只决定是否开展需求 Grill：

- `mode: none`：不开展 Grill。
- `mode: adaptive-grill`：开展已授权的单问题动态访谈并完成其中间证据闭环。

`submission_confirmation` 决定最终成员正文能否提交。Coordinator V1.7.6 签发的新任务要求 Member V1.7.5 或兼容更高版本；无论 `human_collaboration.mode` 为何，都必须由任务登记的 `human_owner` 确认当前 `main-output.md` 的正文哈希和本人立场。

确认只表示“该哈希对应的正文准确记录本人立场，并同意作为本成员贡献提交”。它不构成 G1–G3 Gate 审批、合并许可、基线冻结、开发准入或发布授权。

## 分发契约

新任务包必须把以下策略写入受 `task_contract_hash` 保护的契约：

```yaml
submission_confirmation:
  required: true
  human_owner: <role-card registered owner>
  source_file: main-output.md
  hash_algorithm: sha256-normalized-v1
  required_subjects: [main-output-hash, personal-stance]
  allowed_positions: [confirm, oppose, question, reserve]
  stale_policy: block
  gate_effect: none
```

`required_outputs` 必须包含 `human-submission-confirmation.yaml`。协调员不得把 `human_collaboration.mode: none`、轻量模式、共同参与、既往 Grill 记录或任务预览确认解释为对最终正文的确认。

## 校验要求

协调端只把满足以下条件的 V1.7.5+ 提交记为 `valid`：

1. 确认文件的 assignment、version、submission、member 和 `human_owner` 与任务包及提交清单一致。
2. `source_file` 为 `main-output.md`，`document_hash` 与当前 `content-block-index.yaml.document_hash` 一致，算法为 `sha256-normalized-v1`。
3. `status` 为 `confirmed`；`confirmed_subjects.exact_document_hash` 与 `confirmed_subjects.personal_stance` 均为 `true`。
4. `personal_stance.code` 为 `confirm`、`oppose`、`question` 或 `reserve`，且 owner 原话说明非空。
5. `confirmed_by` 等于登记 owner，确认时间、方法和预览 Token 完整；正文或受保护字段变化时旧确认不得继续有效。
6. `authority_scope` 仅为成员贡献提交，`gate_effect` 必须为 `none`。
7. 提交清单中的确认摘要与确认文件一致，并记录确认文件的规范化 `record_hash`。

四种立场均可形成有效成员提交；`oppose`、`question` 和 `reserve` 必须作为需要后续处理的真实意见投影到项目状态并带入共同评审，不得改写为赞同或团队共识。

## 人工权限边界

AI 可以生成待确认预览、校验字段和报告缺失，但不得：

- 替 human owner 选择立场或编造立场说明。
- 从沉默、既往讨论、Grill 同意、任务参与或默认值推断最终确认。
- 代替 owner 回复，或在没有当前明确回复时调用最终确认命令。
- 把本地 `explicit-human-owner` 记录描述成密码学身份认证。

本地 CLI 只能防止 owner、任务、提交、正文哈希、立场和 Token 错配。需要强身份保证时，应另接受保护审批、WebAuthn 或签名收据；未接入前不得夸大认证强度。

## 历史兼容

`minimum_skill_version < 1.7.5` 的既有任务投影为 `legacy-not-required`。不得原地修改已确认任务、补写过去的确认时间或声称旧提交已经完成提交前确认。

若当前未完成轮次需要立即执行新规则，协调员应 supersede 旧轮次并以 V1.7.6 重新签发；要求零历史例外时，重开实质任务及其后续评审。
