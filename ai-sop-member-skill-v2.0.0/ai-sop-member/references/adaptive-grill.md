# Adaptive Grill 成员需求访谈

只在已确认任务包含 `human_collaboration.mode: adaptive-grill`、`required: true` 且任务类型为 `requirement-analysis` 时执行。本流程是 `ai-sop-member` 的内部环节，不是独立 Skill，也不接管任务校验、正式产物或 Git。

## 执行位置

```text
workspace-check / inspect
        ↓
init 创建成员提交目录和两个 Grill 文件
        ↓
取得登记 human_owner 的协同同意
        ↓
每轮一个问题的动态访谈
        ↓
问题定义、P0、未决分歧分别确认
        ↓
把 Grill 结果映射到正式成员产物
        ↓
index-content / validate / submit / Git push
```

`init` 后只在当前成员的 `output_dir` 更新：

- `human-collaboration-log.yaml`：原始问题、成员原话、分类、追问理由、确认、覆盖和缺口。
- `grill-summary.yaml`：经确认的问题、用户、场景、范围、风险、反例、未知项和推演。

## 启动前检查

必须同时满足：

1. `inspect` 和 `init` 已成功。
2. 当前参与者与任务及成员卡登记的 `human_owner` 一致，成员状态为 `active`。
3. 任务类型是 `requirement-analysis`，独立模式是 `isolated-discovery`。
4. 任务明确要求 `adaptive-grill`，当前真实成员能在对话中回答。
5. 仅使用任务授权来源，且不读取其他成员未公开提交。
6. 两个 Grill 文件位于本次任务的成员专属 `output_dir`。

任一条件失败时停止正式访谈，记录阻塞并返回协调者；不得生成虚假的 `member-direct` 证据。

## 协同同意

首问前向成员说明：回答代表成员本人并进入任务记录；不自动代表终端用户；AI 归纳需要成员确认；AI 推演单独标记；可以回答“不知道”或拒绝，但关键缺口会阻塞提交。

取得明确同意后，才把日志中的以下字段设为 `true`：

```yaml
collaboration_consent:
  understands_recording: true
  understands_evidence_boundary: true
  agrees_to_participate: true
```

不得替成员确认。

## 单问题循环

每轮执行：

1. 读取覆盖状态、最近回答、矛盾、缺口和剩余问题数。
2. 把成员回答分类为 `member-direct-fact`、`member-observation`、`member-judgment`、`member-assumption`、`proposed-solution`、`unknown` 或 `declined`。
3. 按阻塞未知项、问题与用户、P0、证据、反例、价值与验收、P1 的顺序选择最高价值缺口。
4. 当前回复只向成员提出一个问题；不得用编号、分号或补充句暗藏多个问题。
5. 每 3—5 问或完成一个主题后，用当轮唯一问题请求成员确认阶段复述。
6. 原样保存问题和回答，另行记录 AI 分类、归纳、推演和追问理由。
7. 成员纠正时追加更正并保留历史，不覆盖原回答。

首问优先为：“你认为这个任务最需要解决的真实问题是什么？先不要说解决方案。”如果上下文已明确回答，则询问最高优先级未覆盖项。

## 问题地图

问题地图用于选择下一问，不得一次性展示成长问卷。

| 主题 | 需要澄清 | 典型单问题 |
|---|---|---|
| 目标用户 | 操作者、问题承受者、决策者 | 谁会直接操作，谁会承受当前问题？ |
| 场景 | 触发时机、当前做法、失败情形 | 这个问题最常在哪个具体场景发生？ |
| 问题 | 表象、根因、影响 | 如果不解决，最直接的影响是什么？ |
| 价值 | 对谁有价值、改善指标 | 你会用什么变化判断它确实改善了？ |
| 证据 | 事实、观察、判断、假设 | 这是实际观察到的反馈，还是你的判断？ |
| 范围 | P0、P1、排除项、回流条件 | 第一版不可缺少的 P0 是什么？ |
| 风险 | 反例、冲突、未知项 | 有没有一个反例会让这条需求不成立？ |

追问时把方案化表达还原为问题，把“大家都认为”等泛化断言追问为来源，把不可验收表达追问为可观察信号。使用中性措辞，不评价成员个人。

## 证据边界

| 内容 | `evidence_type` |
|---|---|
| 成员原始回答 | `member-direct` |
| 经成员明确确认的 AI 归纳 | `member-confirmed-summary` |
| AI 自己的推演 | `ai-inference` |
| 有可定位访谈或行为记录的终端用户证据 | `user-direct` |

`member-direct` 永远不自动等于 `user-direct`。没有可定位来源时不得标记为终端用户直接证据。

## 完成条件

所有任务指定的 `required_topics` 必须达到 `complete`，并至少满足：

- 明确主要用户、操作者、决策者和至少一个具体场景。
- 说明问题、影响、预期业务价值和可观察验收信号。
- 区分问题与方案以及事实、判断、假设和 AI 推演。
- 检查至少一个反例或失败路径。
- 明确 P0、P1 和排除范围。
- 记录风险、未知项以及已解决或保留的矛盾。

最后必须分三轮分别确认：

1. `problem-definition`
2. `p0-scope`
3. `unresolved-disagreements`，包括明确确认“当前没有未决分歧”

不得合并成一个复合问题。只有覆盖完成、日志和摘要均为 `grill-completed`、三项确认均为 `confirmed` 时，才能进入正式产物映射和提交。

达到 `max_questions` 不代表完成。信息仍不足、身份不一致、成员不可参与、要求 AI 代答、需要读取未授权材料或存在阻塞缺口时，将两个文件状态设为 `blocked` 并返回协调者。

## 正式产物映射

Grill 文件是中间证据，不替代现有提交产物。完成后按以下关系整理：

```text
exchange / confirmation → SRC → 用户故事 → REQ → AC → RISK / GAP
```

- 成员原话进入来源台账时保留证据类型和 exchange 引用。
- AI 推演必须标记为推演，不得改写为成员直接意见。
- `main-output.md` 仍需满足标准用户故事、SRC 引用和任务验收条件。
- `validate` 和 `submit` 会确定性校验协同同意、覆盖、问题数量、三项确认及摘要完整性。
