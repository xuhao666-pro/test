# 协调者任务录入与确认

## 1. 任务内容来源

具体任务必须由协调者基于以下一种或多种已识别来源输入，不得由脚本或 AI 自行创造业务范围：

- 人类发起人的明确指令或已记录决定。
- 当前有效需求池、原子需求或业务验收项。
- 已批准的上一 Gate 基线。
- 已关闭评审轮次中的待处理意见、缺口或风险。
- 经责任人确认的新需求回流记录。

记录 `task_source`，说明任务为何产生。新增范围尚未完成相应 Gate 时，只能回流，不得直接作为后续阶段正式任务。

## 2. 对话式录入

当用户要求创建、分发或安排任务时，先读取项目状态；除非用户已明确提供，否则逐项收集：

```yaml
project_root: 项目根目录
stage: 所属阶段
round: 轮次
task_source: 任务来源或决定记录
kind: 任务类型
objective: 明确、可验证的任务目标
scope:
  included: [至少一项]
  excluded: []
input_refs: []
members: [角色分工型成员；共同参与型自动取全部有效成员]
deliverables: [至少一项业务交付物]
acceptance_criteria: [至少一项可验证条件]
constraints: []
dependencies: []
priority: P0 | P1 | P2 | P3
independence_mode: isolated-discovery | isolated-design | specialized-preparation | shared-review
deadline: null
review_of_round: null
coordinator_notes: []
human_collaboration:
  mode: none | adaptive-grill
  max_questions: 20
```

只追问缺失字段；可以分批提问，但不得根据模糊上下文擅自补写任务目标、范围、交付物或验收标准。用户提供自然语言后，可整理为结构化草案，但必须把推定内容明确展示在预览中。

## 3. 预览和确认

首次运行 `create-assignment` 或 `create-collective-round` 时不写项目状态，只输出完整任务预览和 `confirmation_token`。协调者必须把预览展示给用户，至少包含：

- 任务来源、目标、范围内和范围外事项。
- 成员或共同参与范围。
- 输入、交付物、验收标准、约束、依赖、优先级和期限。
- 自动派生的基线、Git 分支、允许动作和禁止动作。
- 是否要求登记真实成员参与 adaptive Grill、问题上限和两份附加协同产物。
- 独立的 `submission_confirmation` 策略、登记 `human_owner`、正文哈希算法、允许的个人立场、stale 阻塞规则和 `gate_effect: none`。

只有用户明确确认该预览后，才使用完全相同的参数并增加：

```text
--confirm-dispatch <confirmation_token>
```

Token 与当前预览不一致时停止，重新展示新预览。不得把“继续”“运行 Skill”或历史审批推定为对当前任务预览的确认。

## 4. 任务包字段职责

- 协调者输入：`task_source`、`objective`、`scope`、`input_refs`、`deliverables`、`acceptance_criteria`、`constraints`、`dependencies`、`priority`、`coordinator_notes`、成员、期限和是否启用 `human_collaboration`。
- SOP 限制：当前阶段允许的任务类型、独立模式和前后顺序。
- 脚本派生：任务 ID、成员身份、Git 分支、协作模型、参与模式、基线、权限、标准提交文件、提交确认策略和质量检查。
- 人工确认：`dispatch_confirmation`，记录 Token、协调者 ID 和确认时间。

`deliverables` 是业务交付要求；`required_outputs` 是统一技术提交文件，两者不得混用。

`adaptive-grill` 仅适用于 `requirement-analysis` 和 `isolated-discovery`。启用时使用 `--human-collaboration-mode adaptive-grill`，可用 `--human-collaboration-max-questions` 设置 3—100 的问题上限；脚本把登记的 `human_owner`、必需主题、三项 Grill 人工确认和附加输出写入受任务哈希保护的契约。未显式启用时使用 `none`，成员不得自行升级为正式 Grill。

`human_collaboration.mode: none` 只表示不开展 Grill，不免除最终提交确认。Coordinator V1.7.6 创建的每个新任务都必须同时写入受 `task_contract_hash` 保护的 `submission_confirmation`：登记 owner 必须在 submit 前明确确认当前 `main-output.md` 的正文哈希和个人立场；AI 不得代签；该确认不产生任何 G1–G3 Gate 效果。

## 5. 已分发任务

任务包写入后不得原地修改。任何任务来源、目标、范围、交付物、验收标准或输入基线的变化，都必须签发新任务版本或替代轮次并保留旧任务。

`minimum_skill_version < 1.7.5` 的历史任务保持 `legacy-not-required`。不得在旧任务中补写过去的确认；需要立即执行新规则时，supersede 未完成轮次并重新签发。
