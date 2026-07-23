# 成员产物契约

## 必需文件

每次 V1.7.5 新任务提交包含 `submission-manifest.yaml`、`main-output.md`、`content-block-index.yaml`、`source-ledger.yaml`、`assumptions-and-gaps.yaml`、`risks-and-new-requirements.yaml` 和 `human-submission-confirmation.yaml`。

任务显式要求 `adaptive-grill` 时，还必须包含 `human-collaboration-log.yaml` 和 `grill-summary.yaml`。两个文件由 `init` 创建，只记录本任务登记真实成员的协同过程；提交前必须达到 `grill-completed`，完成全部任务主题覆盖，并分别取得问题定义、P0 和未决分歧确认。

清单必须与任务的身份、阶段、轮次、类型、协议、schema、基线、`collaboration_model`、`participation_mode`、`git_branch` 和 `main_branch` 一致。成员分支不得等于 `main`。状态只有 `in-progress`、`submitted`、`blocked`；只有脚本可以封装 `submitted`。

从 V1.7.2 起签发的任务还必须包含协调员确认的任务契约：任务来源、目标、范围、输入引用、业务交付物、验收标准、约束、依赖、优先级和协调员备注。V1.7.4 起任务契约同时保护 `human_collaboration` 配置。成员 CLI 校验 `task_contract_hash` 和 `dispatch_confirmation`，并把任务契约快照写入提交清单；成员不得自行改写任务内容或协同模式。

V1.7.5 起任务契约另外保护 `submission_confirmation`。它对 `none` 和 `adaptive-grill` 都强制生效，绑定登记 `human_owner`、`main-output.md`、`sha256-normalized-v1` 正文哈希、个人立场和 stale 阻塞策略。`human_collaboration.required: false` 只表示不开展 Grill，不得省略最终确认文件。

提交清单同时是协调端实时状态投影的成员事件。`submitted` 必须具有 `submitted_at`，并准确记录来源、假设、新需求和风险计数；成员不得直接修改中央 `project-state.yaml`。

提交清单中的 `human_submission_confirmation` 是确认文件的只读摘要，至少记录文件、状态、正文哈希、立场、确认人、确认时间和确认记录哈希。摘要必须与 `human-submission-confirmation.yaml` 完全一致。正文、任务、成员、owner、立场说明或 Token 任一不匹配时不得提交。

## 内容块索引

`content-block-index.yaml` 由脚本根据 `main-output.md` 自动生成，至少记录：

- 提交、任务和成员 ID。
- 文档哈希与内容块总数。
- 每个稳定 `source_block_id` 的顺序、标题路径、内容哈希、摘要和原始 `SRC` 引用。

块 ID 不使用易漂移的行号。`submit` 会重建索引并验证文档哈希；索引与正文不一致时不得提交。提交后正文和索引同时只读，修改必须使用新任务版本和新 commit。

该索引表示“哪位成员贡献了哪段内容”；`source-ledger.yaml` 表示“该成员内容依据了哪些原始证据”。两类来源不得混为一类。

## 参与和任务身份

提交清单记录：

- 成员 ID、参与类型、主要角色或 `general-contributor`。
- 本任务实际采用的专业视角。
- `role-assigned`、`collective-round` 或 `individual-exception` 参与模式。
- 独立提交或 `shared-review` 类型。
- `shared-review` 的 `review_of_round` 及被评审材料版本。
- 非空 `baseline_refs`；所有路径必须位于项目内并真实存在，summary 不得为空或含 `[[FILL]]`，submission index 必须可解析并匹配轮次。

共同参与型的个人提交仍只代表该成员，不得在 `main-output.md` 中自行声明“团队共识”或“全员通过”。

## 来源台账

每条来源至少包含：

```yaml
source_id: SRC-001
source_type: interview
summary: 脱敏摘要
acquisition_method: 访谈
occurred_at: 2026-01-01
context: 证据产生的场景
evidence_type: direct
confidence: high
confidence_reason: 判断理由
conflict_status: none
```

`evidence_type` 只允许 `direct`、`indirect`、`inference`、`simulation`。模拟和 AI 推演不能写为 `direct`。

## 假设、缺口、风险和新增需求

假设记录声明、是否阻塞和验证方式；缺口记录内容和影响。风险使用 `R0`–`R3`，记录负责人和 `gate_trigger`。

新增需求候选至少记录来源、目标用户、定义、价值、建议优先级、基线影响和回流位置，不直接改变正式范围。

## 独立 `main-output.md`

内容由任务模板决定，删除所有 `[[FILL]]`。显式区分事实、推断、假设、模拟和未知项，并使用稳定编号建立追踪。

`requirement-analysis` 必须包含标准用户故事和 `SRC` 关联；`function-design` 必须包含 `REQ/AC` 关联；`system-inventory` 必须区分已确认事实、技术推断、未知项和无法访问范围。

## `shared-review` 输出

只使用协调员发布的材料，逐项记录：

- 评审对象及版本。
- 立场：`confirm` / `oppose` / `question` / `reserve`。
- 证据和理由。
- 建议处理：采纳、合并、补证据、待确认、暂缓或拒绝。
- 是否阻塞当前轮次或 Gate。
- 少数意见和可接受条件。

不得修改被评审的原始提交，也不得替其他成员填写立场。
