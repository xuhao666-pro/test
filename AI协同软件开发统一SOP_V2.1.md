# AI 协同软件开发统一 SOP

> 版本：V2.1 同步草案
> 状态：待团队评审；尚未替代已批准的项目基线
> 对应实现：`xuhao666-pro/test` 默认分支 `main@462ff3141cefafa2b9c6602381bd4d231a364b35`
> 适用范围：从模糊需求发现、开发准入、真实实现到发布观察和交付关闭
> 核心模型：人类与 AI 组成项目小组，以 A—E 五阶段推进，通过 G1—G5 项目级人工 Gate，并在开发任务内执行独立代码审查和精确 commit 集成控制
> 与 V2.0 的主要差异：引入“发行包身份 + 任务运行时身份”双层版本模型；Member V2.1.0 统一承载 A—C、D—E 和历史兼容运行时；Coordinator V2.1.1 使用 V1.8.5 预开发运行时发现统一 Member 包；新增仓库 `bootstrap/active` 生命周期、受信任运行时锁、能力开关、系统校验、工作流激活和 Skill 清理审计规则
> 当前发行包：Member `2.1.0 / member-package-2.1.0-unified-runtimes-v1`；Coordinator `2.1.1 / coordinator-package-2.1.1-unified-runtimes-v1`
> 当前任务运行时：A—C Member `1.8.1`、Coordinator `1.8.5`；D—E Member/Coordinator `2.0.0`；Member `1.8.0` 仅用于精确绑定的历史兼容任务

## 当前实现状态快照

以下状态对应来源仓库 `main@462ff3141cefafa2b9c6602381bd4d231a364b35`，不是目标项目完成后的示例状态：

| 能力 | 当前状态 | 使用边界 |
| --- | --- | --- |
| 系统生命周期 | `bootstrap` | `project_initialized: false`，不得存在真实项目事实 |
| 系统完整性校验 | 已启用 | 当前唯一实际运行的工作流；只读，不产生项目结论 |
| A—C / G1—G3 | 运行时已安装 | `predevelopment_ac: true`，仍须用真实输入初始化项目后才能执行 |
| D—E / G4—G5 | 运行时已提供但禁用 | `development_de: false`，两个开发 runtime lock 均为 `enabled: false` |
| README 看板与操作台 | 模板已提供但禁用 | `dashboard: false`、`dashboard_actions: false` |
| Issue 与钉钉通知 | 模板已提供但禁用 | 两项 capability 均为 `false`，Secrets 不得进入仓库 |
| 自动 Skill 清理 | 模板已提供但禁用 | `automatic_skill_cleanup: false`；即使启用也只提 PR |
| 成员 push 事件级反馈 | 尚未实现 | 缺少 signal/feedback 工作流，`remote_feedback: false` |

因此，“本 SOP 覆盖 A—E”表示规则和目标运行时已定义，不表示当前 bootstrap 仓库可以直接执行 D—E、看板、通知或清理。

## 1. 目的

本 SOP 用于把模糊、分散、来源不同的需求，转化为经过团队共识、可以验证、技术上可行，并能交给人类或 AI 开发成员执行的开发任务。

本 SOP 重点解决：

1. 人类和 AI 如何以正式小组成员身份共同参与项目。
2. 不同成员如何使用不同方法独立发现需求，而不被统一输入限制。
3. 如何把需求共识一次性落实为需求池、具体定义和可验收标准。
4. 如何按协作模型让应参与成员基于同一份需求合同独立设计功能方案。
5. 如何减少不必要的人工 Gate，同时控制产品、技术和生产风险。
6. 如何保持需求、设计、验证、技术方案、任务和测试之间的追踪关系。
7. 如何同时支持职责明确的团队和全员共同参与、没有固定专业分工的团队。
8. 如何在汇合后保留逐内容块的成员贡献来源，并区分成员贡献来源与原始业务证据来源。
9. 如何让老板直接在私有仓库首页查看固定、自动更新的项目进度，而不引入独立网站和额外服务器。
10. 如何保证每个任务都来自协调者输入或明确确认，并用预览 Token 与契约哈希防止分发内容漂移。
11. 如何在不伪造人类参与的前提下，按任务显式授权真实成员参与单问题自适应需求访谈。
12. 如何保证“不开展 Grill”不会被误解为“免除提交确认”，并让每份成员贡献都能追溯到 owner 确认的精确正文哈希和个人立场。
13. 如何保证每个新任务区分并绑定经协调者确认的 Member 发行包身份与任务实际运行时身份。
14. 如何用成员分支上的显式接受凭证区分“已经拉取或收到提醒”和“成员已经接单”。
15. 如何在成员独立产出中使用受项目策略控制的 AI 对话协同，同时保持 AI 推断、成员结论、Grill、提交确认和 Gate 相互独立。
16. 如何让 G1—G3 的人工评审材料便于非技术成员理解，并对正文哈希、来源指纹和实际审核版本进行机械绑定。
17. 如何区分安装的发行包版本与任务实际执行的运行时版本，避免把 Member 包 V2.1.0 错当成任务 Skill V2.1.0。
18. 如何用受信任运行时锁把仓库入口脚本、来源包、版本、构建和文件哈希绑定为一条可验证链。
19. 如何让系统在 `bootstrap` 状态保持无项目事实、无副作用，并通过一次完整受审提交激活真实项目。
20. 如何让看板、通知、操作台和自动清理受能力开关与最小权限约束，同时不改变任务、Gate、合并和发布事实。

## 2. 流程边界

本版本详细覆盖：

- 角色分工型与共同参与型团队的组织、参与和责任规则。
- 独立需求发现与分析。
- 需求评审、需求池和需求合同。
- 独立功能设计。
- 系统盘点和技术可行性分析。
- 多方案评审、原型和用户验证。
- 最终产品方案、技术方案、测试矩阵和任务包。
- 开发准入审查。
- 跨阶段任务录入、预览确认、任务契约保护和已分发任务不可变规则。
- 阶段 A 中经显式授权的真实成员 Adaptive Grill 需求访谈。
- 所有新成员任务提交前的最终人工确认、正文哈希绑定、个人立场记录和 stale 阻断。
- Gate 后稳定 Member Skill 选择、精确任务绑定和成员版本预检。
- V1.8.1+ 任务的显式接单凭证及远端状态投影。
- 项目级 AI 对话协同策略及结构化过程证据。
- G1—G3 人工可读评审包的生成、校验、版本绑定和冻结。

本版本覆盖完整交付生命周期。A—C 详细规则仍由本文件定义；D—E 的执行细节由 [开发交付阶段 SOP](docs/development-sop.md) 承载，Git 操作细节由 [Git 协作规范](docs/gitcode.md) 承载。分册和附件不得降低本文件的任务、权限、Gate、追踪和人工责任要求。

AI 成员在 G3 后不退出项目，而是携带原角色、上下文和责任进入开发与交付阶段；生产责任始终由登记的真实人类责任人承担。

## 3. 总体原则

### 3.1 不统一需求获取方式，统一证据和表达标准

每个人类或 AI 成员可以使用不同方法和来源发现需求，包括：

- 用户访谈和用户反馈。
- 业务数据和行为数据。
- 会议、工单和历史材料。
- 旧系统问题和操作观察。
- 竞品、行业和政策研究。
- 技术约束反向分析。
- 场景推演、失败路径分析和假设挑战。

团队不建立所有人必须共同使用的“原始需求统一输入包”。

但每份分析必须使用统一的输出结构，记录来源、方法、事实、推断、假设、缺口和可信程度。

### 3.2 AI 是项目成员，不是匿名工具

每个 AI 成员必须拥有：

- 稳定的成员 ID。
- 明确的参与身份；角色分工型成员还必须有主要角色，共同参与型成员可以登记为通用参与者。
- 明确的参与范围、任务责任和需要承担的 Gate 责任能力。
- 可追溯的输入和输出。
- 允许执行的动作和禁止事项。
- 需要升级给人类的风险边界。

AI 成员拥有提案权、执行权、质询权和审查建议权，但不拥有固定人工 Gate 的最终批准权。

### 3.3 先独立发散，再公开收敛

需求发现和功能设计都采用独立工作机制。共同参与型不等于从开始就共同编辑同一份产物，也不取消独立发散：

1. 成员先独立完成自己的分析或方案。
2. 独立产物完成前，原则上不读取其他成员的结论。
3. 独立产物提交后，团队再公开比较证据、差异和取舍。
4. AI 不得把多个角色伪装成多个真实人类。
5. 共同参与型在独立提交窗口关闭后切换到公开共同评审，全体应参与成员均可质询、组合、反对或保留意见。
6. 原始独立提交不得被共同编辑覆盖，汇总产物必须保留少数意见和未决分歧。

### 3.4 需求共识必须可执行

需求共识不等于大家对方向大致同意。通过需求 Gate 时必须同时具备：

- 用户、场景、目标和成功指标。
- 完整需求池。
- 本轮范围和非目标。
- 原子需求和优先级。
- 业务、权限和数据规则。
- 业务可验收定义。
- 关键假设、缺口和风险。

通过后的结果称为“需求合同”。

### 3.5 功能设计与需求定义分离

需求定义描述系统必须实现的结果，功能设计描述产品如何让用户获得这个结果。

```text
需求定义：
审核员可以驳回已提交的申请；驳回原因必填；
申请状态变为已驳回；申请人能够收到通知。

功能设计：
申请详情页提供驳回入口；点击后打开原因填写界面；
提交后更新状态并触发通知。
```

未经批准的功能创意或新增范围不能直接混入功能方案，必须先进入需求池。

### 3.6 人工 Gate 只用于重大承诺

字段检查、追踪检查和一般团队评审不设置人工 Gate。只有当下一步会明显增加成本、风险或返工代价时才需要人工放行。

完整生命周期包含五个项目级人工 Gate；其中 A—C 的三个预开发 Gate 为：

- G1：需求合同确认。
- G2：方案与范围冻结。
- G3：开发准入。

D—E 继续使用 G4 发布准入和 G5 交付关闭。G1—G5 都只在下一步会明显增加成本、风险或返工代价时形成正式人工承诺；代码审查、专项风险审查和一般团队评审不得被伪装成其中任何一个 Gate。

### 3.7 参与、任务与 Gate 责任分离

项目必须把以下三个概念分别记录，不得用“大家都参与”替代具体责任，也不得用固定角色限制成员提出意见：

| 概念 | 含义 | 最低记录要求 |
| ---- | ---- | ------------ |
| 参与 | 谁需要参加某阶段或轮次的独立提交、公开评审和确认 | 应参与成员、实际参与状态、缺席原因和影响 |
| 任务责任 | 谁对某个具体产物或任务的按时、完整交付负责 | 单一负责人或明确的协作组、主笔、审查人和边界 |
| Gate 责任 | 谁具备业务、产品、技术、测试或专项风险的人工决策责任 | 责任能力、对应人类成员、适用 Gate 和批准记录 |

同一成员可以参与全部工作、承担多个任务或兼任多种 Gate 责任能力。共同参与不意味着多人无边界地覆盖同一文件，也不意味着所有人的意见自动成为共识。

### 3.8 任务内容与人类协同必须显式确认

具体任务的来源、目标、范围、输入、业务交付物和验收标准必须由协调者输入或明确确认。首次创建只生成完整预览和 `confirmation_token`，不写入分发文件；只有当前用户明确确认同一预览后才能正式分发。任何字段变化都使旧 Token 失效。

Adaptive Grill 不是默认需求获取方式。它只在 `requirement-analysis + isolated-discovery` 任务中，由协调者在预览里显式启用，并由登记真实成员同意参与；AI 不得自行启动、代答或把普通讨论升级为正式人类证据。

### 3.9 Grill 与最终提交确认是两条独立链路

`human_collaboration` 只控制是否开展需求 Grill：

- `mode: none`：不开展 Grill。
- `mode: adaptive-grill`：开展经显式授权的单问题动态访谈，并完成其中间证据闭环。

`submission_confirmation` 独立控制最终成员正文能否提交。对 `minimum_skill_version >= 1.7.5` 的新任务，无论 `human_collaboration.mode` 为何，登记 `human_owner` 都必须在 `submit` 前明确确认当前 `main-output.md` 的规范化正文哈希和本人个人立场。正文或受保护字段变化后，旧确认立即失效。

该确认只表示“当前哈希对应的正文准确记录本人的贡献和立场，并同意作为本成员贡献提交”。它不构成 G1、G2、G3 人工 Gate 批准，不构成分支合并许可、基线冻结、开发准入或发布授权。AI 不得从沉默、任务参与、既往讨论、Grill 同意或默认选项推断最终确认，也不得代选立场、代写确认回复或代替 owner 签署。

### 3.10 Skill 发行必须精确绑定

V2.1 起，Skill 版本必须分成两层：

- **发行包身份**：`package_version` 与包级 `build_id`，标识一个可安装、可归档的完整包。
- **任务运行时身份**：`runtime_releases.<profile>.skill_version` 与运行时 `build_id`，标识任务实际调用的 CLI 契约。

同一个 Member V2.1.0 发行包可以同时承载 A—C 的 V1.8.1 运行时、D—E 的 V2.0.0 运行时和仅兼容历史任务的 V1.8.0 运行时。包版本与运行时版本允许不同，禁止再以 `package_version == CLI.SKILL_VERSION` 作为正确性条件。

人工 Gate 通过、已审核成员分支完成强制合并、祖先关系验证和阶段基线冻结后，协调者必须先确认下一阶段使用的稳定 Member 发行包和唯一运行时，才能分发新任务。成员不得以“包版本更高”“运行时更高”“目录名相同”或“最低版本兼容”为理由替代精确匹配。

A—C 新任务同时绑定运行时名称、版本、构建、协议和 profile，以及包版本、包构建、包路径和发行 commit。当前 D—E V2.0 任务合同只机械绑定运行时 `name/version/build_id`；包来源由可信 `.github/sop-runtime-lock.json` 与 V2.1 包 manifest 交叉验证。任务未携带 `package_path` 或 `release_commit` 时，AI 和脚本均不得补写或声称任务内已经具备包级 provenance。

Skill 发行确认属于技术发布选择，`gate_effect: none`。它不修改已经通过的 Gate 或冻结基线，也不自动安装、升级或切换 Skill。

### 3.11 任务送达与成员接单分离

`clone`、`fetch`、`pull`、消息通知、Issue、钉钉送达或 AI 推断都不构成成员接单。对精确绑定 Member V1.8.1+ 的任务，只有成员使用任务绑定 CLI 在自己的登记分支生成、commit 并 push 接受凭证，且协调端从精确远端 ref 校验并首次观测后，才能投影为 `accepted`。

接受凭证只证明成员已接受该任务，`gate_effect: none`；它不表示已经提交、收轮、通过评审、通过 Gate 或允许合并。V1.8.0 及更早任务保持 `legacy-not-required`，不得追溯补签。

### 3.12 AI 对话协同由项目策略控制

A00 的 `ai_dialogue_collaboration` 只允许 `required` 或 `optional`，默认 `required`。后续任务自动继承该策略，不在每次分发时重复选择，也不允许成员自行改写。`required` 模式无法取得成员参与时保持 `blocked`；`optional` 模式允许成员明确选择完成或跳过。

AI 对话协同用于增强成员独立分析，不新增阶段，不扩大任务范围。它与 Adaptive Grill、最终提交确认和 Gate 均为独立链路，`gate_effect: none`。

### 3.13 人工 Gate 必须审核可读且已绑定的材料

每个 G1—G3 Gate 必须先形成 `gate/gate-review-pack.md`。该文件是候选产物、成员提交、参与矩阵、来源台账和决策记录的人工可读只读投影；AI 可以起草、压缩和组织内容，但不得改变事实、成员立场、共识等级或人工决定。评审包正文或其来源发生变化时，旧准备状态立即 `stale`，不得沿用旧批准。

### 3.14 系统安装、项目激活与项目执行必须分离

仓库包含 Skill、受信任脚本和工作流模板，只能证明系统已经安装，不能证明具体项目已经初始化。系统生命周期至少分为：

- `bootstrap`：系统代码存在，但没有真实项目状态、成员、任务、Gate、基线或项目通知配置；除只读系统校验外，副作用能力必须关闭。
- `active`：真实项目输入、成员与责任、运行时锁、配置和工作流已经在同一个完整受审提交中确认并合入；只允许启用已经完成配置和验证的能力。

不得从历史项目、测试夹具、旧成员或 AI 推断补齐新项目事实。不得把复制工作流模板、生成空目录、看板能打开或 Actions 运行成功解释为项目已激活。

## 4. 项目小组与角色

### 4.1 人类角色与责任能力

| 角色                 | 主要责任                             |
| -------------------- | ------------------------------------ |
| 项目负责人           | 目标、资源、阶段和最终责任           |
| 业务负责人           | 业务价值、规则和成功指标             |
| 产品负责人           | 需求合同、需求池、产品范围和产品决策 |
| 设计或用户研究负责人 | 用户任务、功能体验、原型和反馈判断   |
| 技术负责人           | 系统盘点、技术方案、迁移、监控和回滚 |
| 测试负责人           | 验收标准、测试矩阵和质量准入         |
| 数据或安全负责人     | 隐私、权限、敏感数据和高风险变更     |

上表在角色分工型中可以作为固定角色，在共同参与型中作为 Gate 责任能力和专业审查能力使用，不限制成员参与其他工作。

同一人可以兼任多个角色或责任能力，但 Gate 必须由承担实际责任的人类确认。共同参与型没有固定专业角色时，仍必须在 Gate 前把必需责任能力映射到具体人类成员。

每个人类成员也必须拥有稳定成员 ID 和成员卡。角色分工型记录主要角色和附加角色；共同参与型可以登记为 `general-contributor` 且主要角色为空。固定角色或通用参与身份都不会自动授予 Gate 批准权，Gate 责任能力必须在 A00 中单独映射。

### 4.2 AI 角色池

| AI 角色         | 主要责任                             | 项目全程连续职责                     |
| --------------- | ------------------------------------ | ------------------------------------ |
| AI 产品分析师   | 独立发现需求、分析场景和维护需求追踪 | 开发期间担任需求解释和范围守护角色   |
| AI 用户研究员   | 分析访谈、反馈、行为和竞品           | 持续分析验证结果，不冒充真实用户     |
| AI 产品设计师   | 独立功能设计、流程和原型方案         | 检查实现是否偏离共识功能设计         |
| AI 技术架构师   | 系统盘点、可行性和技术方案           | 开发期间维护架构边界和技术决策       |
| AI 测试与风险官 | 验收、测试矩阵、失败路径和风险       | 开发期间生成测试、审查缺口和回归范围 |
| AI 项目协调员   | 状态、决策、需求池、依赖和 Gate 材料 | 开发期间协调任务、变更和项目记录     |
| AI 开发成员     | 开发准入后领取并执行任务包           | 按批准范围实现和自测，不自行扩大范围 |
| AI 审查成员     | 独立审查产品、技术、测试或代码       | 不审查自己负责的同一项输出           |

项目不要求启用全部 AI 角色。项目负责人应根据规模和风险选择最小充分角色集。共同参与型可以把 AI 登记为通用参与者，并在具体任务中临时声明所采用的专业视角；这不会把一个 AI 成员变成多个独立成员。

### 4.3 AI 成员卡（角色卡）

每个 AI 成员在项目开始时建立成员卡。角色分工型填写主要角色，共同参与型允许主要角色为空，但仍必须记录参与范围、任务边界和责任能力：

```text
AI 成员 ID：
参与类型：专业角色 / 通用参与者
主要角色：可为空
附加角色：可为空或多个
角色目标：
专业视角：
负责阶段：
参与范围：指定轮次 / 全部轮次
Gate 责任能力：仅记录建议或审查能力；AI 不得成为人工批准人
允许执行的动作：
必须输出的产物：
禁止事项：
需要升级给人类的情况：
可使用的数据和工具：
持续上下文位置：
```

### 4.4 AI 成员权限

| 权限                             | 是否允许           |
| -------------------------------- | ------------------ |
| 独立分析和提出方案               | 允许               |
| 对人类或其他 AI 方案提出质疑     | 允许               |
| 在批准范围内生成文档、原型和测试 | 允许               |
| 在开发准入后执行批准的任务包     | 允许               |
| 代表真实用户提供证据             | 不允许             |
| 冒充真实团队成员                 | 不允许             |
| 单独批准 G1、G2 或 G3            | 不允许             |
| 未经批准扩大 P0/P1 范围          | 不允许             |
| 修改生产数据、密钥或配置         | 未经专项授权不允许 |

### 4.5 团队协作模型

项目在 A00 中选择一种 `collaboration_model`：

| 协作模型 | 标识 | 适用情况 | 任务分发 | 评审与共识 |
| -------- | ---- | -------- | -------- | ---------- |
| 角色分工型 | `role-based` | 产品、技术、测试等职责边界较明确 | 按主要角色、附加角色和专业能力分发，可指定跨角色协作 | 相关角色参加，责任人汇总并形成候选结论 |
| 共同参与型 | `collective-participation` | 小团队、合伙团队或没有稳定专业分工，全员共同工作 | 每轮默认分发给全部有效成员；具体产物仍指定主笔或任务负责人 | 独立窗口关闭后全员公开评审，保留确认、反对和保留意见 |

协作模型只决定团队如何组织参与，不改变需求、方案、验证、开发准入的质量标准，也不改变 AI 不得批准人工 Gate 的边界。项目可以通过正式决策变更协作模型，但必须更新 A00、参与矩阵、任务责任和 Gate 责任映射，并评估对在途产物的影响。

### 4.6 共同参与型工作规则

共同参与型必须遵守：

1. 每个有效成员拥有独立、稳定的成员身份，不要求固定专业角色。
2. 独立发散轮次中，每个应参与成员分别提交自己的产物，不读取或覆盖他人未公开的结论。
3. 独立窗口关闭后，全部有效提交同时公开，进入共同评审。
4. 共同评审记录每个成员的确认、反对、质询和保留意见；不能只保留最终多数结论。
5. 共识产物由明确的主笔或协调员汇总，原始成员提交保持只读，不被重写。
6. 证据质量、风险和用户代表性高于简单票数；“全员参与”不等于“按多数票决定”。
7. 某成员缺席或未完成时，参与矩阵必须记录原因和影响；参与不完整时不得声称“全员共识”。

### 4.7 全员参与矩阵

共同参与型必须在 A00 中维护参与矩阵；角色分工型也应维护，用于证明关键视角和责任覆盖。矩阵按阶段和轮次记录：

```text
阶段与轮次：
协作模型：role-based / collective-participation
应参与成员：
独立提交状态：未开始 / 已提交 / 豁免
公开评审状态：未开始 / 已完成 / 豁免
Gate 确认状态：不适用 / 待确认 / 已确认 / 反对 / 保留
任务责任：
缺席或豁免原因：
影响评估：
参与覆盖率：
```

参与矩阵至少分别计算独立提交覆盖率、公开评审覆盖率和 Gate 确认覆盖率。覆盖率以轮次开始时登记的应参与成员为分母；豁免不得从历史分母中无痕删除，应同时显示原始覆盖率、豁免后调整覆盖率及豁免清单。

共同参与型的轮次关闭条件是：所有应参与成员已完成要求的独立提交和公开评审，或者在窗口关闭前由项目负责人记录合理豁免、影响和补救措施。使用豁免后只能声明“已记录例外的共同结论”，不能声明“全员一致”。

### 4.8 Coordinator 与 Member 独立发行边界

Coordinator 与 Member 继续是两个可分别安装、权限不同的独立发行包；V2.1 只统一每个包内部的多个运行时，不合并两种角色：

| 运行端 | 允许能力 | 禁止越界 |
| ------ | -------- | -------- |
| `ai-sop-coordinator` | 任务录入与确认、成员和分支登记、远程提交校验、中央状态、汇总、Gate、基线和 README/SVG 看板 | 不执行成员任务，不冒充成员补交，不代替人类批准 Gate |
| `ai-sop-member` | 在登记分支和独立工作区校验并执行一个已确认任务，生成个人提交、内容块索引和评审意见 | 不写中央状态、汇总、Gate、基线、看板或他人提交 |

当前发行与运行时矩阵：

| 发行包 | 包身份 | profile | 任务运行时身份 | 阶段 |
| --- | --- | --- | --- | --- |
| Member V2.1.0 | `member-package-2.1.0-unified-runtimes-v1` | `predevelopment` | `1.8.1 / member-cli-1.8.1-assignment-acceptance-v1` | A—C / G1—G3 |
| Member V2.1.0 | 同上 | `development_delivery` | `2.0.0 / member-dev-cli-2.0.0-v1` | D—E / G4—G5 |
| Member V2.1.0 | 同上 | `legacy_predevelopment` | `1.8.0 / member-cli-1.8.0-ai-dialogue-exact-release-v1` | 仅历史 A—C |
| Coordinator V2.1.1 | `coordinator-package-2.1.1-unified-runtimes-v1` | `predevelopment` | `1.8.5 / coordinator-cli-1.8.5-unified-member-package-v1` | A—C / G1—G3 |
| Coordinator V2.1.1 | 同上 | `development_delivery` | `2.0.0 / coordinator-dev-cli-2.0.0-v1` | D—E / G4—G5 |

协调端不要求安装完整 Member Skill；远程成员提交由协调包内置的受信任 Member 校验器在精确 commit 的隔离 worktree 中验证。成员端只需安装统一 Member 包，并按任务运行时身份选择唯一 CLI 和协议资产。Coordinator 与 Member 的协议、schema、运行时、包 provenance 或哈希不匹配时必须停止，不得靠手工改文件兼容。

Member 包的 `legacy_predevelopment` 只服务已经精确绑定 V1.8.0 的历史任务。它不得用于签发新任务，也不得因为被统一包携带而被描述为当前稳定预开发运行时。

## 5. 执行模式与风险

`execution_mode` 与 `collaboration_model` 是两个正交维度：前者决定流程严谨度和产物合并程度，后者决定参与和任务组织方式。标准/轻量均可分别与角色分工型/共同参与型组合，不能根据执行模式推断协作模型。

### 5.1 标准模式

适用于多人协作、对外交付、中高风险和需要审计的项目。

- 至少包含产品、技术和测试视角。
- 人类和 AI 成员都可以提交独立分析和功能设计。
- AI 成员产物必须明确标注成员身份，不计为真实用户证据。
- 三个固定 Gate 均保留人工批准记录。

### 5.2 轻量模式

适用于个人项目、小团队验证和低风险内部工具。

- 可以由一名人类负责人和多个 AI 角色组成项目小组。
- 可以合并文件和团队评审会议。
- 不能省略需求合同、需求池、验收定义、系统盘点和开发准入。
- 进入 R2/R3 风险时自动切换为标准模式。

### 5.3 风险分级

| 等级 | 定义                             | 示例                                             |
| ---- | -------------------------------- | ------------------------------------------------ |
| R0   | 低影响、容易撤回                 | 文案、静态展示、低影响体验优化                   |
| R1   | 影响业务逻辑但可快速回退         | 内部流程、已有接口上的功能扩展                   |
| R2   | 影响关键数据、安全或外部契约     | 权限、支付、订单、隐私、上传、迁移、公共 API     |
| R3   | 可能造成不可逆、合规或大范围损失 | 生产批量变更、资金结算、不可逆迁移、核心鉴权重构 |

AI 可以建议升级风险等级，但不能单独降低风险等级。

### 5.4 执行模式与协作模型组合

| 组合 | 典型用法 | 必须保留的控制 |
| ---- | -------- | -------------- |
| 标准 + 角色分工型 | 多专业团队、对外交付、审计项目 | 角色覆盖、独立审查、完整 Gate 责任映射 |
| 标准 + 共同参与型 | 全员共创但风险或审计要求较高 | 全员参与矩阵、明确主笔、完整专业责任和人工 Gate |
| 轻量 + 角色分工型 | 小型低风险项目，人员兼任角色 | 可合并产物，但保留任务与 Gate 责任 |
| 轻量 + 共同参与型 | 小团队低风险验证 | 可合并会议和文件，但保留独立提交、参与矩阵和人工 Gate |

当风险升至 R2/R3 时，项目无论采用哪种协作模型，都自动切换为标准执行模式，并登记对应技术、安全、数据、合规或其他专项人类责任人。共同参与型和 `all-participants` 确认策略均不得取消这项要求。

## 6. 控制机制

### 6.1 AI 自动质量检查

每个阶段完成产物后，由 AI 项目协调员执行：

- 字段完整性检查。
- 编号和版本检查。
- 来源和证据检查。
- 需求、验收、设计、任务和测试追踪检查。
- 汇合内容标识、成员源块、分支 commit、内容哈希和来源台账一致性检查。
- 协作模型、参与矩阵、任务责任和 Gate 责任覆盖检查。
- 范围外内容检查。
- 冲突、缺口和高风险事项检查。
- 任务契约字段、`dispatch_confirmation`、`task_contract_hash` 和协同模式一致性检查。
- A—C 任务绑定的 Member 运行时名称、profile、精确版本、运行时 `build_id`、协议，以及发行包版本、包级 `build_id`、包路径和发行 commit 一致性检查；D—E 按当前合同检查精确运行时，并通过 runtime lock 校验包来源。
- V1.8.1+ 任务接受凭证的任务哈希、契约哈希、成员、owner、登记分支、Skill 构建、远端可达性和 `gate_effect: none` 检查。
- `ai_dialogue_collaboration` 项目策略、任务快照和 `ai-dialogue-summary.yaml` 的状态与过程证据检查。
- Adaptive Grill 启用时的人类同意、主题覆盖、问题计数、三项独立确认和正式产物映射检查。
- V1.7.5+ 成员提交的登记 owner、当前正文哈希、个人立场、确认 Token、两项确认主题、确认记录哈希及 `gate_effect: none` 一致性检查。
- Gate 评审包的固定结构、成员/产物标记、正文哈希、来源指纹、来源 commit、对比版本和 stale 状态检查。

一般质量检查默认不暂停无关工作，问题直接进入待处理清单。但身份、任务契约、授权基线、提交确认、正文哈希、来源追踪或 Gate 硬性条件失败时，必须阻断对应提交或阶段动作，不得降级为普通提醒。

### 6.2 团队工作评审

团队评审用于公开比较和形成工作结论，不等同于正式 Gate。评审结论由 AI 项目协调员记录，团队可以继续下一项准备工作。

- 角色分工型由相关角色和任务责任人参加，并记录关键视角是否覆盖。
- 共同参与型在独立窗口关闭后由全部应参与成员参加，逐项记录确认、反对和保留意见，并同步更新参与矩阵。

### 6.3 A—C 固定人工 Gate

G1—G3 必须暂停并等待具备责任主体的人类明确确认。A00 必须选择 `gate_confirmation_policy`：

- `accountable-members`：所有映射到该 Gate 的责任人类成员均须确认；适合角色分工型，也是默认兼容策略。
- `all-participants`：所有当前有效的人类参与成员均须确认，同时仍须覆盖该 Gate 要求的业务、产品、技术、测试和专项责任能力；适合共同参与型。

两种策略都只计算人类确认。`all-participants` 下任一应确认成员缺失、反对或保留，即不得记录为全员通过；如需改变策略或成员范围，必须在 Gate 审查前形成决策并更新 A00 和参与矩阵，不得在 Gate 失败后追溯性排除成员。

| Gate              | 决策内容                               | 通过后投入             |
| ----------------- | -------------------------------------- | ---------------------- |
| G1 需求合同确认   | 是否已经明确要解决什么，以及如何验收   | 功能方案和系统分析     |
| G2 方案与范围冻结 | 是否已验证采用什么方案，最终做哪些内容 | 最终技术设计和开发准备 |
| G3 开发准入       | 是否可以安全开始真实开发               | 生产级实现             |

### 6.4 G1—G3 人工通过后的强制 main 合并

G1、G2 或 G3 的人工结论为通过或条件通过，只表示审核决策成立，不表示阶段已经完成。每个 A—C 固定 Gate 必须执行以下不可绕过的状态转换：

```text
gate-pending
  -> 人工审核覆盖全部有效成员分支的精确 commit
  -> merge-pending
  -> 在临时集成分支合并全部已审核成员分支
  -> 验证每个冻结 commit 都是 main 的祖先
  -> baselined / next-stage
```

强制规则：

- A00 为每名有效成员登记唯一 `git_branch`，并登记目标 `main_branch`；成员分支不得等于 `main` 或与其他成员重复。
- Gate 材料冻结全部有效成员分支的 `expected_head`。人工批准必须明确确认审核覆盖这些精确 commit，而非只审核汇总文档或浮动分支名。
- 人工通过后先进入 `merge-pending`；此时不得冻结基线、推进阶段或开始下一阶段受控工作。
- 合并必须先在临时集成分支完成。任一分支缺失、分支头变化或发生冲突时，放弃临时集成分支并保持 `main` 不变。
- 全部分支合并成功后，验证每个 `expected_head` 都是合并后 `main` 的祖先，并记录 `main` 合并前后 commit、成员分支和合并时间。
- 只有合并及验证全部成功，才生成正式基线并推进阶段。普通状态转换、手工复制文件、只合并汇总分支或事后删除成员均不得绕过该门禁。
- 如人工审核后任何成员分支需要改变，必须退回团队评审，重新冻结 commit 并重新人工审核。

本规则适用于 `accountable-members` 和 `all-participants`，也适用于角色分工型和共同参与型。Gate 确认策略决定谁批准，强制合并策略决定哪些有效成员分支必须进入 `main`，两者不得相互替代。

本节不适用于 G4/G5。D 阶段按任务逐一合并经非作者审查和 CI 批准的精确代码 commit；G4/G5 只验证发布范围的 main 集成、生产观察和交付事实，不执行“全体成员证据分支再次合并”。

成员提交前的 `human-submission-confirmation.yaml` 只证明登记 owner 确认某一精确正文哈希和个人立场。它不能代替本节的 Gate 人工审核、精确 commit 冻结或强制 `main` 合并；同样，Gate 批准也不能追溯替代成员在 submit 前应完成的最终正文确认。

成员首次接入必须使用独立 clone 目录或独立 worktree，先 fetch、切换并跟踪登记分支，再优先使用 `git merge --ff-only origin/main` 同步任务基线并验证当前分支。已有历史提交导致正常分叉时必须停止并升级，只有协调者核验精确 head 并明确授权后才可合入已核验的 `main` SHA；不得自行 rebase、reset、squash、强推或改在 `main` 工作。任务进入成员分支后，脚本以协调者授权任务 commit 和实际合入的 main 快照校验任务与基线，不因无关看板更新要求循环追赶最新 main。成员脚本的 `submit` 只冻结提交清单，不代替 Git commit 和 push。

shared-review 任务只能引用已关闭轮次真实发布的材料。`submission-index.yaml` 必须存在、可解析且匹配阶段和轮次；`summary.md` 只有非空且不含 `[[FILL]]` 时才可加入任务。阶段 A 默认不要求轮次 summary。成员在 `inspect` 前必须校验全部 `baseline_refs`，不得创建中央缺失文件或忽略错误。已分发的错误任务保持不可变，协调员必须记录原因、把旧轮次标记为 `superseded`，并使用新轮次 ID 重新签发。

### 6.5 成员提交状态投影

`project-state.yaml` 必须提供项目级最新提交摘要，但不得替代成员原始提交、阶段状态、参与矩阵或提交索引。状态投影至少记录：

- 各阶段预期、已提交、进行中、有效、待校验、无效和缺失任务数量。
- 已提交、待校验和缺失成员 ID。
- 每项任务的成员、轮次、类型、登记分支、观察 ref/commit、提交时间、提交路径、状态和校验结论。
- 来源、假设、新需求和风险计数，以及最后刷新时间、触发来源和递增 revision。
- 每项任务的提交确认是否必需、确认状态、登记 owner、个人立场、确认时间、正文哈希、确认记录哈希及是否需要后续处理。
- 各阶段及全项目的 `confirmation_required_count`、`confirmation_confirmed_count`、`confirmation_pending_count`、`confirmation_attention_count` 和 `confirmation_legacy_count`。
- V1.8.1+ 各任务的 `acceptance_status: pending | accepted | invalid`、凭证路径、成员声明接受时间、协调端首次观测时间、观察 ref/head 和校验结果；历史任务使用 `legacy-not-required`。

更新规则：

- 所有协调者写操作结束后，在同一项目锁内重新计算投影并原子更新 `project-state.yaml`。
- 成员只更新自己分支内的 `submission-manifest.yaml`，不得直接修改中央项目状态。
- 同一工作树内的提交可以立即进行完整文件与 schema 校验；通过后标记 `valid`。
- 跨电脑成员 push 后，当前由协调者显式执行 fetch 并直接读取远程成员 ref；项目激活且看板工作流启用后，计划任务可以作为轮询兜底。未合并但文件完整、尚未完成隔离校验的提交标记 `pending-validation`。
- 完整远程校验必须在精确 commit 的隔离 worktree 中使用 `main` 上受信任的 Member CLI；对每个任务解析其提交目录最后一次变更的精确 commit，并验证该 commit 仍可从登记成员分支 head 到达。校验通过后可标记 `valid`，但不得把成员分支提前合并到 `main`。
- 不得使用成员分支当前最新 HEAD 回溯替代历史任务自己的提交 commit；分支改写导致任务提交 commit 不再可达时，必须标记无效并阻断相应动作。
- 刷新时从登记成员远端 ref 校验接受凭证；只有任务哈希、契约哈希、成员、owner、分支、精确 Skill 版本和构建全部匹配时才记录 `accepted`。成员填写的 `accepted_at` 是声明时间，协调端的 `observed_at` 是首次观测时间。
- V1.7.5+ 任务只有在 `human-submission-confirmation.yaml` 与任务、提交清单、当前正文哈希、登记 owner 和个人立场全部匹配且状态为 `confirmed` 时，才可标记 `valid`。
- `confirm`、`oppose`、`question` 和 `reserve` 都可形成有效个人提交；后三者必须投影为 `requires_review: true`，不得显示成团队共识或 Gate 通过。
- 远程 ref 的精确 commit、观察来源和提交路径必须写入投影，使状态可追溯且不会依赖浮动分支名。
- 状态摘要只能由事实源重新生成，不得手工修改摘要后反向覆盖成员提交或阶段记录。
- 投影内容没有语义变化时不得递增 revision、更新时间或产生空提交。

推荐命令：

```text
refresh-project-state <project-root> [--fetch] [--validate-remote] [--commit]
```

`--commit` 只允许协调者或 CI 在干净的 `main` 上执行。当前可承诺的是“成员 push 后，协调者显式刷新即可读取；计划任务只作兜底”，不是事件级自动反馈，也不表示多个成员同时编辑同一份中央状态文件。

### 6.6 老板项目状态看板

对于个人名下的私有 GitHub 仓库，项目激活后可优先在仓库根 `README.md` 中嵌入自动生成的 `dashboard/status.svg` 作为老板状态看板，不再部署独立静态网站、公开读取 Raw 文件或依赖 Issue 页面样式。当前 bootstrap 仓库的看板能力尚未启用，模板存在不等于看板已经运行。

看板规则：

- `project-state.yaml` 和阶段状态仍是看板的数据来源；README 和 SVG 只是只读摘要，不得成为新的事实源。
- 安装器只更新 README 中成对标记包围的看板区块，必须保留标记之外的项目说明；重复运行不得产生重复区块。
- 激活看板时必须使用 runtime lock 锁定的 Coordinator CLI、Member CLI 和渲染脚本生成首版 SVG，并在同一个完整受审 PR 中启用 `dashboard` 及所需工作流。
- 当前仓库没有成员 push 信号与可信反馈处理器，`remote_feedback` 必须保持 `false`。成员 push 后由协调者显式执行 `refresh-project-state --fetch --validate-remote`；已启用看板的计划任务只能作为轮询兜底，不得承诺事件级即时回流。
- 中央状态、README 和 SVG 应在同一受控提交或同一受审 PR 中更新；不得依赖 `GITHUB_TOKEN` 产生的提交再触发第二个 push 工作流。
- 看板至少展示项目状态、当前阶段、下一 Gate、风险等级、真实开发状态、任务有效进度、各阶段提交统计、当前阶段任务、阻塞项和最后更新时间。
- 仓库必须保持私有；不得发布公共 Pages、公共 Raw 状态文件或无认证链接。个人私有仓库无法提供所需只读权限时，应评估迁移到支持精细权限的组织。
- 自动化使用仓库内置 `GITHUB_TOKEN`，仅申请提交 README/SVG 快照所需的 `contents: write`；不得在浏览器、状态文件或仓库中保存个人访问令牌。
- SVG 必须是无脚本、无外部资源的静态图形；所有状态文字必须进行 XML 转义，不得包含超出老板授权范围的密钥、个人隐私或原始业务敏感数据。
- 看板刷新以中央状态提交并推送到 `main` 为准。本地未提交、成员尚未 push、协调者尚未完成远端刷新或中央状态尚未更新时，不得宣称看板已经反映这些变化。
- 看板写入失败只影响展示，不得阻断或回滚任务、Gate、合并和基线事实；失败必须在 GitHub Actions 中可见并由协调员处理。
- 若分支保护禁止机器人直推，协调员必须在中央状态提交前运行仓库内渲染脚本，把状态、README 和 SVG 纳入同一次人工审核提交，或采用团队批准的 PR 更新流程。

### 6.7 汇合文档内容来源追踪

成员贡献来源追踪和原始证据追踪是两条相连但不同的链：

```text
汇合内容块 P
  -> 成员提交内容块 SB
  -> 成员提交文档
  -> 成员登记分支的精确 commit
  -> 成员正文引用的原始证据 SRC
```

成员提交规则：

- 每个 `main-output.md` 必须生成 `content-block-index.yaml`，使用稳定 `SB` 标识记录内容哈希、标题路径、摘要和 `SRC` 引用。
- 块 ID 不使用行号。提交脚本必须根据正文自动生成并校验；正文与索引哈希不一致时不得提交。
- 提交后正文、内容块索引和分支 commit 同时作为只读事实源。返工必须创建新任务版本和新 commit。

协调汇合规则：

- 协调者从成员登记分支的精确 commit 读取内容块索引，形成 `aggregation/provenance/source-block-index.yaml`；无需提前合并成员分支。
- Markdown 实质段落或表格行使用 `[P-001]`；YAML/JSON 业务记录使用 `provenance_refs: [P-001]`。
- `aggregation/provenance/provenance-ledger.yaml` 为每个 `P` 保存目标产物、目标内容块和哈希，以及成员 ID、任务、源文档、`SB`、分支、commit、源块哈希和 `SRC`。
- 形成方式必须如实标记为 `verbatim`、`paraphrased`、`synthesis`、`derived`、`human-decision`、`coordinator-added` 或 `conflict-retained`。`verbatim` 必须与唯一源块哈希一致；`synthesis` 至少保留两个实际源块并列出全部实际来源；人工决定和协调者新增必须引用决定记录，不得伪造成成员原文。
- 迁移项目的既有基线确实无法还原时，才允许经人工审核并说明原因的 `legacy-unattributed`；v1.5 及之后的新内容禁止使用。

Gate 前必须生成 `provenance-report.md` 并满足：全部实质内容单元覆盖率 100%，全部 `P` 有且仅有一条台账映射，所有成员源块真实存在，commit/哈希/成员元数据一致，且来源选择和形成方式已完成团队评审。孤立标识、孤立台账、失效哈希、伪造来源、未审核记录或实质内容豁免均阻塞 `prepare-gate`。

### 6.8 风险触发 Gate

以下事项不为所有项目设置固定阶段，但一旦出现必须进行专项人工审查：

- 数据库结构变化或不可逆迁移。
- 公共 API 和外部契约变化。
- 登录、权限、租户隔离和核心鉴权。
- 支付、退款、订单和资金处理。
- 隐私、敏感数据、上传和数据保留。
- 生产配置、密钥和部署架构。
- 使用真实用户数据或生产写入制作原型。
- G2 后改变 P0 范围或核心流程。

专项审查只暂停受影响工作，不必冻结无关任务。

R2/R3 项目的专项责任必须映射到具备实际能力的人类负责人。共同参与、全员确认或多人共同签字不能替代专项责任人，也不能把专项责任稀释为“团队共同负责”。

### 6.9 任务录入、预览确认与契约保护

任何阶段创建、安排或分发任务前，协调者先读取项目状态和有效基线，只收集尚未明确的字段，不得从上下文静默创造业务范围。任务录入至少包含：

```yaml
project_root: 项目根目录
stage: 所属阶段
round: 轮次
task_source: 人类指令、需求池、批准基线、已关闭评审待办或已确认回流
kind: 当前阶段允许的任务类型
objective: 明确且可验证的目标
scope:
  included: [至少一项]
  excluded: []
input_refs: []
deliverables: [至少一项业务交付物]
acceptance_criteria: [至少一项可验证条件]
constraints: []
dependencies: []
priority: P0 | P1 | P2 | P3
members: []
independence_mode: isolated-discovery | isolated-design | specialized-preparation | shared-review
deadline: null
review_of_round: null
coordinator_notes: []
human_collaboration:
  mode: none | adaptive-grill
  max_questions: 20
ai_dialogue_collaboration: required | optional
required_member_skill:
  name: ai-sop-member
  runtime_profile: predevelopment
  version: "1.8.1"
  build_id: member-cli-1.8.1-assignment-acceptance-v1
  package_version: "2.1.0"
  package_build_id: member-package-2.1.0-unified-runtimes-v1
  package_path: ai-sop-member-skill-v2.1.0
  release_commit: <精确 commit>
  protocol_version: "1.0"
acceptance_policy:
  required: true
  evidence: member-branch-receipt
  gate_effect: none
submission_confirmation:
  required: true
  human_owner: <成员卡登记 owner>
  source_file: main-output.md
  hash_algorithm: sha256-normalized-v1
  required_subjects: [main-output-hash, personal-stance]
  allowed_positions: [confirm, oppose, question, reserve]
  stale_policy: block
  gate_effect: none
```

上例是当前 A—C 新任务合同。`required_member_skill` 中运行时字段与包级字段只要任一出现，就必须完整记录，并全部纳入 `task_contract_hash`；`package_path` 必须与 `package_version` 一致。任一字段变化都必须重新生成预览并取得新的确认 Token。D—E 当前合同不得照抄这些包级字段，必须按第 20.1 节只写运行时 `name/version/build_id`，包来源由 runtime lock 与 manifest 保护。

分发控制链：

```text
读取项目状态和基线
  -> 收集缺失任务字段
  -> 生成完整预览和 confirmation_token（不写文件）
  -> 当前用户明确确认同一预览
  -> --confirm-dispatch <token>
  -> 写入 dispatch_confirmation、task_contract_hash 和精确 Skill 绑定
  -> 成员版本预检与 inspect
  -> 成员生成并 push 接受凭证
  -> 协调端观测 accepted
  -> 成员 init
```

强制规则：

- `deliverables` 是业务交付要求，`required_outputs` 是统一技术文件，两者不得混用。
- 脚本只派生任务 ID、成员资料、Git 分支、基线、权限和标准质量检查，不得代替协调者定义任务。
- 预览至少展示任务来源、目标、范围内外、成员、输入、交付物、验收、约束、依赖、优先级、期限、派生基线、允许/禁止动作、是否启用 Adaptive Grill、项目级 AI 对话协同策略、适用阶段的精确 Member 运行时及包来源绑定、接受策略，以及独立的提交确认策略。
- `task_contract_hash` 保护任务内容；V1.7.4 起保护 `human_collaboration` 配置，V1.7.5 起保护 `submission_confirmation`，V1.8.0 起保护 AI 对话协同和精确 Skill 绑定，V1.8.1 起保护接受策略。Adaptive Grill 的问题上限为 3—100，预览必须显示登记的 `human_owner`、必需主题、三项 Grill 确认、最终正文哈希与个人立场确认，以及相应附加输出。缺字段、未确认或哈希不一致的任务不得执行。
- 已分发任务不可原地修改。任何任务内容、协同模式或输入基线变化都必须签发新 `assignment_version` 或使用新轮次；错误轮次使用 `supersede-round` 保留历史。

### 6.10 成员提交前最终人工确认

V1.7.5+ 新任务的 `required_outputs` 必须包含 `human-submission-confirmation.yaml`。该文件由受信任 Member CLI 创建和更新，至少记录：

```yaml
schema_version: "1.0"
status: not-prepared | awaiting-human-confirmation | confirmed
assignment_id: A-...
assignment_version: "1.0"
submission_id: A-...-v1.0
member_id: member-...
human_owner: <登记 owner>
source_file: main-output.md
hash_algorithm: sha256-normalized-v1
document_hash: sha256:<64 hex>
personal_stance:
  code: confirm | oppose | question | reserve
  statement: <owner 原话>
confirmed_subjects:
  exact_document_hash: true | false
  personal_stance: true | false
human_collaboration_mode: none | adaptive-grill
authority_scope: member-contribution-submission-only
gate_effect: none
prepared_at: <ISO 8601>
confirmed_by: <登记 owner>
confirmed_at: <ISO 8601>
confirmation_method: explicit-human-owner
confirmation_token: <当前预览 Token>
```

执行顺序：

1. 成员完成全部正式产物；启用 Grill 时，先完成 Grill 闭环并把结果映射到正式正文。
2. 运行 `index-content`，生成当前 `main-output.md` 的规范化文档哈希和内容块索引。
3. 只使用 owner 本人提供的立场和原话说明运行 `prepare-confirmation`，生成绑定任务、成员、owner、正文哈希、立场和权限声明的确认预览与 Token。
4. 把预览原样展示给登记 owner，并暂停等待对当前预览的明确回复。沉默、历史讨论、Grill 同意、任务参与或默认选项均不构成确认。
5. 只有收到明确回复后，才可运行 `confirm-submission`。随后运行 `validate` 和 `submit`；`submit` 必须重新生成内容索引，正文变化时旧确认自动失效并阻断提交。
6. 提交清单中的 `human_submission_confirmation` 必须保存确认文件、状态、正文哈希、立场、确认人、确认时间和确认记录规范化哈希，并与确认文件完全一致。

本地 `explicit-human-owner` 记录只能证明字段、哈希和流程匹配，不能被描述成密码学身份认证。需要强身份保证时，应另接受保护审批、WebAuthn 或签名收据，但不得因此省略本 SOP 的正文哈希与立场绑定。

历史兼容按任务的 `minimum_skill_version` 判断：低于 V1.7.5 的既有任务投影为 `legacy-not-required`，不得补写过去的确认时间或声称旧提交已完成提交前确认。若未完成旧轮次需要立即执行新规则，协调者必须保留历史并 supersede 旧轮次，再以新版本任务重新签发。

### 6.11 Gate 后 Skill 发行控制

固定顺序如下：

```text
Gate 人工通过
  -> 合并审核冻结的成员 commit
  -> 验证所有冻结 commit 都是 main 的祖先
  -> 冻结阶段基线
  -> prepare-skill-release
  -> 协调者审核稳定包身份、唯一运行时身份、包路径和仓库 commit
  -> confirm-skill-release <preview-token>
  -> 允许分发下一阶段新任务
```

系统从稳定包的 `runtime_releases` 中选择与阶段匹配的唯一 profile，不再要求包版本等于 CLI 运行时版本。候选必须同时满足：

- 包本身为 `release_status: stable`，包目录、`package_version` 和包级 `build_id` 完整有效。
- 统一包 manifest schema 为 `2.1`，目录名严格等于 `ai-sop-member-skill-v<package_version>`；不得从目录名反推并覆盖 manifest。
- 运行时条目为当前可用状态，阶段、`skill_version`、运行时 `build_id`、协议版本和项目 schema 与任务一致。
- A—C 新任务只从 `runtime_releases.predevelopment` 选择，`stage_ids` 必须精确为 `A/B/C`；D—E 只允许 `development_delivery` 且 `stage_ids` 为 `D/E`。`legacy_predevelopment` 仅用于既有精确绑定任务。
- `cli_path` 与 `protocol_path` 是包内相对路径且不能逃逸包目录。
- manifest、协议资产和 CLI 常量的版本、构建与协议完全一致。
- 仓库 `.github/sop-runtime-lock.json` 中的安装态路径、来源包路径和 SHA-256 与候选文件一致。
- 多个合格统一包并存时按 `package_version` 选择最新稳定包，再在该包内选择精确 profile；不得按 runtime version 排序或因运行时版本相同而任意取包。历史扁平 manifest 只允许用于兼容解析，不得成为新任务发行候选。

未完成发行确认时，只阻塞下一阶段新任务分发，不回滚已通过 Gate、已完成合并或已冻结的基线。A—C 新任务记录运行时和包的双层精确身份；D—E 按当前合同记录精确运行时，并由运行时锁补充仓库级来源保护。Member 在预检、接受、初始化、确认、验证和提交链路中重复核对。

当前 A—C 的中央发行投影至少为：

```yaml
skill_release_control:
  status: confirmed
  confirmed_member_skill:
    name: ai-sop-member
    runtime_profile: predevelopment
    version: "1.8.1"
    build_id: member-cli-1.8.1-assignment-acceptance-v1
    package_version: "2.1.0"
    package_build_id: member-package-2.1.0-unified-runtimes-v1
    package_path: ai-sop-member-skill-v2.1.0
    protocol_version: "1.0"
    release_commit: <精确仓库 commit>
  confirmation_source: repository-stable-release
  requires_post_gate_confirmation: false
  gate_effect: none
```

`project-state.yaml` 只投影已确认身份；不得用看板显示值、目录最新版本或本地已安装版本反向覆盖该记录。

### 6.12 显式任务接受凭证

V1.8.1+ 新任务的接受凭证保存于：

```text
sop/stages/<stage>/acceptances/<member-id>/<assignment-id>-v<assignment-version>.yaml
```

凭证由成员 CLI 在登记成员分支生成，至少绑定任务文件哈希、任务契约哈希、成员 ID、登记 `human_owner`、登记分支、精确 Member 运行时版本和运行时 `build_id`，并固定 `gate_effect: none`。包身份已由任务契约哈希或 runtime lock 间接保护，不得把包版本写成接受凭证中的运行时版本。成员必须 commit 并 push；协调端只从登记远端 ref 读取，不把中央工作区副本、普通拉取或通知送达作为接受事实。

协调投影区分 `pending`、`accepted`、`invalid` 和 `legacy-not-required`。接受状态不参与提交完成率、收轮条件、Gate 确认、合并许可或基线冻结；但 V1.8.1+ 任务在有效接受凭证出现前不得 `init` 创建产出。

### 6.13 成员独立产出中的 AI 对话协同

每个 V1.8.0+ 任务从 A00 继承 `ai_dialogue_collaboration`，并创建 `ai-dialogue-summary.yaml`。标准过程为：

1. AI 复述任务目标、范围、材料、禁止事项、交付物和验收标准，由成员确认或纠正。
2. AI 独立形成初始思路地图，并把建议或推断显式标记为 AI 内容。
3. 每轮只问一个问题，与当前成员发散方案、边界和依据。
4. 每 3—5 问或完成一个主题后复述当前理解，由成员纠正。
5. 比较替代方案、反例、风险和取舍。
6. 收敛成员的确认、反对、质询和保留意见。
7. 把成员确认的结论映射到现有正式产物。

不要求保存完整聊天原文。摘要只记录结构化过程证据，必须分开记录 AI 推断与成员确认结论，不得替代正式产物、Adaptive Grill 文件、最终正文确认或 Gate。`required` 未完成时保持 `blocked`；`optional` 可以由成员明确跳过并记录。

### 6.14 人工可读 Gate 评审包

G1—G3 的固定顺序升级为：

```text
init-gate-review
  -> 协调员 AI 撰写人工可读内容
  -> validate-gate-review
  -> prepare-gate
  -> 人工审阅
  -> approve-gate
  -> merge-approved-gate
```

`gate/gate-review-pack.md` 必须包含：本次决定、评审身份、一页结论、逐成员观点、一致意见与未决分歧、采纳/暂缓/拒绝、风险/缺口/Gate 条件、对比版本变化、全员评审检查表、建议结论和原始材料附录。每名有效人类成员使用 `<!-- member:<member_id> -->` 标记；每项 Gate 必需产物使用 `<!-- artifact:<artifact_type> -->` 标记，并提供仓库内真实相对链接和可见来源引用。

`prepare-gate` 绑定评审包正文哈希、来源指纹、来源 commit、成员分支冻结 head 和对比版本身份。正文、候选产物、参与成员、来源台账、决策记录、分支头或对比版本任一变化都使材料 `stale`，必须重新生成、校验和准备。人工通过并完成强制合并后，把实际审核的评审包原样复制到 `baseline/<version>/`；历史基线不得覆盖。

### 6.15 可选 GitHub Issue 提醒

项目需要任务和提交提醒时，可以安装只读事实链的 GitHub Issue 通知。Issue、评论、标签、关闭状态和 `@mention` 只允许作为提醒投影，不得作为任务分发、任务接受、成员提交、人工确认、Gate、合并或基线的输入。通知失败不得改变 SOP 状态；不得读取或执行 Issue 评论中的命令，也不得把 Token 写入仓库。

### 6.16 受信任运行时锁与仓库入口

项目仓库必须用 `.github/sop-runtime-lock.json` 固定所有受信任入口。每个运行时至少记录：

```yaml
path: .github/scripts/<trusted-entry>.py
version: <runtime-version>
build_id: <runtime-build-id>
sha256: <file-sha256>
source: <package-path>/<runtime-cli-path>
# enabled: true | false  # 仅能力门控的运行时需要显式记录
```

`path/version/build_id/sha256/source` 是所有条目的必需字段。当前 A—C 与历史校验入口未写 `enabled`，按安装态可用处理；D—E 两个条目必须显式为 `enabled: false`，直到真实 G3 和开发负向门禁通过后再在受审提交中启用。

当前标准入口为：

| 用途 | 仓库入口 | 运行时 |
| --- | --- | --- |
| A—C 协调 | `.github/scripts/sop_coordinator_cli.py` | Coordinator 1.8.5 |
| A—C 成员 | `.github/scripts/sop_member_cli.py` | Member 1.8.1 |
| 历史 A—C 成员 | `.github/scripts/sop_member_cli_1_8_0.py` | Member 1.8.0，仅兼容 |
| D—E 协调 | `.github/scripts/sop_development_cli.py` | Coordinator 2.0.0 |
| D—E 成员 | `.github/scripts/sop_member_development_cli.py` | Member 2.0.0 |

任务执行时优先使用任务和 runtime lock 验证过的仓库入口。不得只根据文件名、包目录名或“最新版本”猜测运行时；文件内容、运行时常量、协议资产、来源路径或哈希任一不一致都必须阻塞。

### 6.17 Bootstrap、激活和能力开关

`.github/sop-system.json` 是系统生命周期与能力开关的权威配置。初始状态必须为：

```yaml
lifecycle: bootstrap
project_initialized: false
project_data_included: false
capabilities:
  predevelopment_ac: true
  development_de: false
  dashboard: false
  dashboard_actions: false
  github_issue_notifications: false
  dingtalk_notifications: false
  remote_feedback: false
  automatic_skill_cleanup: false
```

从 `bootstrap` 激活真实项目时必须：

1. 由真实负责人明确确认项目 ID、名称、协调者、全新需求输入、执行模式、协作模型、Gate 策略、单一风险等级、真实开发状态、成员 ID、human owner、唯一成员分支和 G1—G3 责任能力。
2. 初始化 `sop/`，检查生成内容只包含当前项目事实，不混入旧项目、测试夹具或历史成员。
3. 建立运行时锁、成员与分支登记、看板策略和通知配置；Secrets 只存放于受保护的 GitHub Environment。
4. 只复制准备实际启用且具有 lifecycle/capability guard 的加固工作流。
5. 运行系统校验和相应负向测试。
6. 在同一个完整受审 PR 中把 lifecycle 切换为 `active` 并启用已经配置完成的 capability。

不得把半激活状态、真实 Secret、真实手机号或未受审工作流推入 `main`。G3 前 `development_de` 必须保持 `false`；尚无可信 signal/handler 反馈链时 `remote_feedback` 必须保持 `false`。

### 6.18 自动化工作流的事实边界

- `sop-system-validate.yml` 始终只读校验系统、运行时、包、脚本、敏感值和测试完整性。
- 看板操作台只允许刷新、通知测试和精确任务催办等低风险动作；不得接单、分发、关轮、批准 Gate、部署或回滚。
- README/SVG 看板只在语义变化时更新中央投影；定时任务是兜底，不构成处理时限承诺。
- Issue 与钉钉通知必须同时启停，且只消费可信 `main` 中的精确状态；成员分支不得直接在带写权限和 Secrets 的 job 中执行。
- 自动 Skill 清理只能生成计划、分支和 PR，永不自动合并 `main`；清理前必须通过完整系统校验和回归测试。
- 所有有写权限的 Actions 只能运行可信 `main` 中的脚本；PR 或成员分支内容只能作为不可信数据读取。

## 7. 总体流程

三阶段和三个固定 Gate 对两种协作模型完全一致。差异只体现在每一轮由谁参与、如何分发任务、如何公开评审以及由谁确认；这些状态均写入 A00 参与矩阵。

每个阶段内的任何任务在进入成员工作区前，都先经过“任务录入 → 完整预览 → 当前用户确认 → 契约哈希保护 → 精确 Skill 绑定”。V1.8.1+ 任务还必须在成员产出前完成“显式接受凭证 → push → 协调端观测”。阶段 A 的 Adaptive Grill 和各阶段的 AI 对话协同都只是受控的成员任务内部环节，不新增 Gate，也不替代正式产物。

```text
阶段 A：需求发现与需求合同
按协作模型分发独立需求发现与分析
  -> 多视角评审
  -> 需求池
  -> 原子需求和业务验收标准
  -> 人工可读 G1 评审包
  -> G1 需求合同确认

阶段 B：功能设计与方案验证
               ┌-> 按协作模型进行独立功能设计 ─┐
G1 通过且完成 main 合并后 ┤               ├-> 多方案评审
               └-> 系统盘点与可行性分析 ───┘
  -> 共识功能设计
  -> 原型和用户验证
  -> 反馈回流
  -> 人工可读 G2 评审包
  -> G2 方案与范围冻结

阶段 C：开发准备与准入
按协作模型收集建议并形成最终产品方案
  -> 技术方案
  -> 工程测试矩阵
  -> 开发任务包
  -> 灰度、监控和回滚准备
  -> 人工可读 G3 评审包
  -> G3 开发准入

阶段 D：正式开发
G3 通过、成员证据分支合并且基线冻结
  -> D0 G3 基线交接校验
  -> D1 开发任务录入、预览和确认
  -> D2 成员显式接单与实施计划
  -> D3 测试先行
  -> D4 正式实现
  -> D5 本地与 CI 质量检查
  -> D6 独立代码审查
  -> D7 精确 commit 合并与 main 祖先验证

阶段 E：发布交付
全部发布范围任务已集成
  -> E0 人工可读 G4 发布准入
  -> E1 灰度、监控、停止和回滚
  -> E2 事故处置、数据修复和恢复验证
  -> E3 人工可读 G5 交付关闭与复盘
```

## 8. 标准产物

| 编号 | 产物                     | 主要内容                               |
| ---- | ------------------------ | -------------------------------------- |
| SYS  | 系统与运行时基线         | 生命周期、capability、运行时锁、发行包/运行时身份、文件哈希、工作流激活和清理审计 |
| A00  | 项目状态、成员与决策日志 | 执行模式、协作模型、成员卡、参与矩阵、Gate 责任、内容来源策略、版本、风险和决策 |
| A01  | 独立需求分析集           | 按协作模型确定的每个人类和 AI 成员独立需求分析（含用户故事） |
| A02  | 多视角评审与证据对照表   | 观点、证据、参与状态、冲突、少数意见、可信度和处理决定 |
| A03  | 需求合同                 | 共识基线、用户故事、原子需求、规则和业务验收标准 |
| A04  | 需求池                   | 本轮、待确认、暂缓、拒绝和新增需求     |
| A05  | 独立功能设计集           | 应参与成员基于同一需求合同的独立完整方案 |
| A06  | 系统盘点与技术可行性报告 | 仓库、数据库、API、权限、部署和风险    |
| A07  | 共识功能设计与验证报告   | 方案决策、成员意见、原型、用户反馈和生产差距 |
| A08  | 最终产品与技术方案       | 最终 PRD、架构、数据、接口、成员评审和风险控制 |
| A09  | 测试矩阵与开发任务包     | 工程验收、测试、任务责任、边界和执行顺序 |
| A10  | 开发准入审查包           | 人工可读 Gate 评审包、检查项、参与覆盖、来源指纹、Gate 策略、阻塞项、风险、批准人和结论 |
| T    | 跨阶段任务包             | 任务来源、目标、范围、输入、业务交付物、验收、约束、依赖、优先级、确认记录、契约哈希、精确 Skill 绑定、接单策略和协同模式 |
| D01  | 开发任务包               | G3 基线、REQ/AC、允许与禁止范围、代码分支、审查人、风险责任、测试、停止和回滚要求 |
| D02  | 实施计划与测试证据       | 变更文件、核心逻辑、数据读写、权限、错误处理、测试用例、命令和结果 |
| D03  | 开发提交与审查记录       | 精确 commit、完成报告、人工提交确认、PR、代码审查、CI 和返工记录 |
| D04  | 集成证据                 | main 合并前后 commit、任务 commit 可达性、集成测试和未决问题 |
| E01  | 发布准入包               | 发布候选、范围、验收、迁移、配置、监控、灰度、停止、回滚和 G4 决策 |
| E02  | 发布与观察记录           | 灰度批次、指标、告警、停止/回滚动作、事故、修复和恢复验证 |
| E03  | 交付关闭包               | 生产验证、观察期结论、遗留事项、复盘改进、发布基线和 G5 决策 |

文件格式可以使用 Markdown、Word、Excel、数据库或项目管理系统。关键是字段完整、版本明确和可追溯，不要求机械拆成大量文件。

## 9. 编号与追踪

### 9.1 标准编号

| 类型     | 格式              |
| -------- | ----------------- |
| 来源     | `SRC-NNN`       |
| 成员源块 | `SB-<hash>`      |
| 汇合来源 | `P-NNN`          |
| 需求     | `REQ-NNN`       |
| 验收标准 | `AC-REQ-NNN-NN` |
| 用户反馈 | `FB-NNN`        |
| 风险     | `RISK-NNN`      |
| 决策     | `DEC-NNN`       |
| 技术事项 | `TECH-NNN`      |
| 开发任务 | `TASK-NNN`      |
| 测试场景 | `TEST-NNN`      |
| Grill 会话 | `HC-<assignment>-v<version>` |
| Grill 交流 | `EX-NNN` |
| Grill 确认 | `CONF-NNN` |

### 9.2 追踪链路

```text
来源 SRC
  -> 独立分析（含用户故事）
  -> 用户故事（As a / I want / so that）
  -> 需求 REQ
  -> 需求决策 DEC
  -> 业务验收 AC
  -> 功能设计
  -> 原型与反馈 FB
  -> 技术设计 TECH
  -> 开发任务 TASK
  -> 测试 TEST
```

P0 需求必须达到 100% 来源、用户故事、验收、任务和测试追踪覆盖。

### 9.3 成员贡献来源链路

`P` 回答“汇合稿中的这段内容由哪些成员提交形成”，`SRC` 回答“成员提交依据了什么原始事实或证据”。二者必须同时保留：

```text
P-001
  -> member-001 / assignment / main-output.md / SB-... / branch / commit / hash
  -> member-002 / assignment / main-output.md / SB-... / branch / commit / hash
  -> 各源块原有 SRC 引用
```

内容原样采用、改写、综合、推导、冲突保留、人工决定和协调者新增必须分别记录。成员贡献被拒绝时保留在原始提交和评审记录中，不得删除或改写为未提交。

参与追踪与需求追踪并行维护，不互相替代：

```text
应参与成员
  -> 独立提交或事前豁免
  -> 公开评审或事前豁免
  -> 意见处理与少数意见保留
  -> Gate 确认（如适用）
```

共同参与型只有在参与矩阵完成上述链路后，才能声称该轮形成共同结论；P0 全链路追踪完整也不能弥补成员参与缺失。

显式启用 Adaptive Grill 时，还必须保留独立的人类协同追踪链：

```text
任务预览与人类协同授权
  -> 登记 human_owner 明确同意
  -> EX 原始问题与成员原话
  -> CONF 问题定义 / P0 / 未决分歧三项独立确认
  -> SRC（member-direct 或 member-confirmed-summary）
  -> 用户故事 -> REQ -> AC -> RISK / GAP
```

`member-direct` 不自动等于 `user-direct`；没有可定位终端用户来源时，不得把成员判断标记为真实用户直接证据。

### 9.4 版本规则

- `V0.x`：草案或未通过当前 Gate。
- `V1.0`：首次通过人工 Gate、完成全部成员分支合并并验证 `main` 后的正式基线。
- `V1.x`：不改变核心目标和 P0 范围的更新。
- `V2.0`：核心用户、目标、P0 范围、流程或外部契约重大变化。

## 10. 阶段 A：需求发现与需求合同

### 10.1 目标

允许不同成员通过不同来源和方法独立发现需求，随后统一评审证据和结论，形成可进入功能设计的需求合同。

### 10.2 A00 项目启动

项目负责人和 AI 项目协调员建立 A00：

```text
项目名称：
当前阶段：
执行模式 execution_mode：standard / lightweight
协作模型 collaboration_model：role-based / collective-participation
Gate 确认策略 gate_confirmation_policy：accountable-members / all-participants
AI 对话协同 ai_dialogue_collaboration：required / optional
Coordinator/Member 发行包版本与包级 build_id：
当前阶段 Coordinator/Member runtime profile、精确运行时版本及 build_id：
协议版本与项目 schema：
已确认稳定 Member 包路径与 release commit：
真实开发状态：
最高风险等级：
人类成员及成员卡：成员 ID、参与类型、主要角色、附加角色、参与范围
AI 成员及成员卡：成员 ID、参与类型、主要角色、附加角色、参与范围、权限边界
Gate 责任映射：G1/G2/G3 的业务、产品、项目、技术、测试和专项责任能力对应人类成员
当前阶段和轮次的应参与成员：
参与矩阵位置：
已记录的缺席、豁免及影响：
当前基线版本：
下一固定 Gate：
当前阻塞问题：
```

本版本 A—C 的参考组合为 Coordinator 包 V2.1.1 中的 `predevelopment` 运行时 V1.8.5（`coordinator-cli-1.8.5-unified-member-package-v1`）与 Member 包 V2.1.0 中的 `predevelopment` 运行时 V1.8.1（`member-cli-1.8.1-assignment-acceptance-v1`），协议版本 1.0、项目 schema 1.5。初始化必须先发现合格稳定 Member 统一包，选择其唯一 `predevelopment` 条目，把当前仓库精确 `HEAD` 固定为 `release_commit`，并将完整双层身份写入 `project-state.yaml.skill_release_control.confirmed_member_skill`。未找到唯一合格候选时阻塞初始化，不得静默构造发行记录。协调包保留受信任的 V1.8.1 当前校验器与 V1.8.0 历史任务校验器。

`ai_dialogue_collaboration` 默认 `required`；只有协调者在项目初始化时明确选择才可设为 `optional`。该项目级策略随任务契约快照自动继承，不得在任务分发时静默改变。

默认兼容设置为 `role-based + accountable-members`。共同参与型推荐 `all-participants`，但项目可依据治理需要选择 `accountable-members`；无论选择哪一种，都不能省略必需 Gate 责任能力。

Gate 责任映射至少覆盖：G1 的业务和产品决策，G2 的业务、产品和技术决策，G3 的项目、产品、技术和测试决策；R2/R3 再增加与风险相对应的安全、数据、合规或其他专项责任。一个人类成员可以承担多项能力，但每项能力都必须显式登记。

角色分工型成员卡必须记录主要角色。共同参与型可以使用以下通用成员卡：

```text
成员 ID：
成员类型：人类 / AI
参与类型：general-contributor
主要角色：空
附加角色：可为空
参与范围：all-rounds / 指定轮次
任务责任：按轮次或任务登记
Gate 责任能力：仅人类成员可承担人工批准责任
```

### 10.3 A01 独立需求发现与分析

角色分工型由 A00 指定的需求分析成员自行选择需求获取方式和材料，独立生成分析文档；至少覆盖产品、用户、业务和风险视角。共同参与型由当前轮次全部应参与成员分别生成独立分析文档。

没有统一输入包，没有分析准入 Gate。独立提交窗口关闭前，成员不得读取其他成员结论或共同编辑同一份 A01。窗口关闭后，完成的分析同时公开并进入多视角评审。

每份 A01 至少包含：

```text
分析成员：
成员类型：人类 / AI
角色视角：
需求获取方法：
使用的信息来源：
目标用户：
用户故事：
  格式：As a <角色>, I want <功能>, so that <价值>
  每条用户故事关联来源 SRC-NNN
核心场景：
用户问题：
业务价值：
需求建议：
已确认事实：
推断及依据：
工作假设：
不同意见：
信息缺口：
结论可信度：
```

AI 项目协调员同步更新参与矩阵中的应参与成员、独立提交状态和例外。共同参与型缺少任一应参与成员提交且没有事前豁免时，不得关闭独立轮次。

**用户故事要求：**
- 每条用户故事使用标准格式：`As a <具体角色>, I want <具体功能>, so that <业务价值>`。
- 每条用户故事必须关联至少一个来源 `SRC-NNN`。
- 按用户角色分组，覆盖该角色的核心任务和异常处理。
- AI 推演的用户故事必须标注 `[AI 推演]`，不得与真实用户证据混淆。
- 从访谈、观察或数据中直接提取的用户故事标记为 `[直接证据]`。

来源记录至少包含：

| 字段           | 要求                                          |
| -------------- | --------------------------------------------- |
| 来源 ID        | 使用`SRC-NNN`                               |
| 来源类型       | 访谈、数据、会议、工单、竞品、观察、AI 推演等 |
| 原始内容或摘要 | 尽量保留原话和原始含义                        |
| 获取方法       | 说明成员如何获得信息                          |
| 时间和场景     | 记录证据产生背景                              |
| 证据属性       | 直接证据、间接证据、推断或模拟                |
| 可信度         | 高、中、低及理由                              |
| 冲突状态       | 无冲突、待核实或存在冲突                      |

AI 推演、模拟用户和合成数据不能标记为真实用户证据。

#### 10.3.1 显式授权的 Adaptive Grill

仅当已确认任务同时满足以下条件时，成员才可启动 Adaptive Grill：任务类型为 `requirement-analysis`，独立模式为 `isolated-discovery`，`human_collaboration.mode` 为 `adaptive-grill`，任务登记的 `human_owner` 为当前可参与的真实成员，且 `inspect` 与 `init` 已成功。未显式启用时，成员不得自行把聊天、讨论或 AI 推演登记为正式 Grill。

执行顺序：

1. `init` 在当前成员本次提交目录创建 `human-collaboration-log.yaml` 与 `grill-summary.yaml`。
2. 首问前说明记录用途、证据边界和退出权，取得登记真实成员对记录、证据边界及参与的明确同意；不得代替成员确认。
3. 每轮只问一个问题，不得用编号、分号或补充句暗藏多个问题；每 3—5 问或完成一个主题后，用当轮唯一问题请求成员确认阶段复述。
4. 按阻塞未知项、问题与用户、P0、证据、反例、价值与验收、P1 的顺序动态选择下一问，保留原始问题、成员原话、AI 分类、追问理由和更正历史。
5. 完成目标用户、场景、问题、业务价值、证据、反例、范围、优先级和风险等必需主题，并分三轮分别确认 `problem-definition`、`p0-scope`、`unresolved-disagreements`。
6. 把交流和确认映射到正式 `SRC → 用户故事 → REQ → AC → RISK / GAP`，再执行内容索引、最终提交确认、校验、提交和 Git push。两份 Grill 文件是中间证据，不替代 `main-output.md`、来源台账、最终提交确认或正式需求产物。

达到 `max_questions` 不等于完成。信息不足、身份不一致、真实成员不可参与、要求 AI 代答、需要未授权材料或仍有阻塞缺口时，两个文件保持 `blocked` 并返回协调者。只有日志和摘要均为 `grill-completed`、全部必需主题完成且三项确认均为 `confirmed`，任务才可提交。

Grill 的参与同意、问题定义、P0 范围和未决分歧确认只证明访谈过程与中间结论。Grill 结束后 `main-output.md` 仍可能变化，因此它们不得替代 `human-submission-confirmation.yaml: status: confirmed`。`human_collaboration.mode: none` 只跳过本节，不跳过 6.10 的最终提交确认。

### 10.4 A02 多视角需求评审

独立提交窗口关闭后再公开共享全部有效提交。AI 项目协调员生成 A02，团队评审：

1. 目标用户和场景是否一致。
2. 证据来源是否可靠并具有代表性。
3. 核心问题和业务价值有哪些差异。
4. 是否只是术语不同，还是实际判断冲突。
5. 哪些结论来自事实，哪些仍是假设。
6. 哪些建议属于需求，哪些已经提前进入方案。
7. 哪些事项进入本轮、需求池或待验证列表。

不得按简单多数票判断需求。证据质量、用户代表性和风险影响高于意见数量。

差异处理结果只有：采纳、合并、补证据、待确认、暂缓或拒绝。

角色分工型由 A00 指定的相关角色参加评审。共同参与型要求全部应参与成员完成公开评审，并在 A02 中逐项记录成员的确认、反对、质询或保留意见；协调员不得把未处理的少数意见从汇总中删除。


### 10.5 A03 需求合同与 A04 需求池

评审完成后，产品负责人和 AI 产品分析师形成 A03 与 A04。

A03 需求合同至少包含：

- 目标用户和角色。
- **用户故事（共识版）**：基于 A02 多视角评审，从各成员 A01 的用户故事中确认、合并或修订形成。每条用户故事格式为 `As a <角色>, I want <功能>, so that <价值>`，关联来源 `SRC-NNN` 和对应需求 `REQ-NNN`。
- 业务目标和成功指标。
- 核心场景、正常流程和异常流程。
- 本轮范围和非目标。
- 原子需求。
- P0/P1/P2 优先级。
- 业务规则、权限规则和数据规则。
- Given/When/Then 业务验收标准。
- 关键假设、信息缺口、依赖和风险。

A04 需求池最低字段：

| 字段       | 内容                               |
| ---------- | ---------------------------------- |
| 需求 ID    | 唯一且稳定                         |
| 来源       | 关联一个或多个`SRC`              |
| 目标用户   | 用户或角色                         |
| 需求定义   | 描述需要实现的结果，不写具体方案   |
| 业务价值   | 为什么需要                         |
| 优先级     | P0、P1、P2                         |
| 状态       | 本轮、待确认、暂缓、拒绝、已替代等 |
| 验收标准   | 关联`AC`                         |
| 风险和依赖 | 关联`RISK` 或外部依赖            |
| 决策       | 关联`DEC`                        |
| 回流位置   | 需要返回的阶段                     |

业务验收标准模板：

```text
验收编号：
关联需求：
优先级：
场景类型：正常 / 异常 / 权限 / 边界 / 数据一致性
Given：
When：
Then：
验证方式：用户验证 / 业务检查 / 数据检查 / 测试
```

此时只要求业务行为可验收。性能、安全、迁移、监控和回滚等工程验收要求在阶段 C 补充。

### 10.6 G1 需求合同确认

责任能力：产品决策、业务决策；R2/R3 项目增加技术、安全、数据或其他对应专项责任。

批准人按 A00 的 Gate 确认策略确定：`accountable-members` 由上述责任能力映射到的人类成员全部确认；`all-participants` 由全部有效人类参与成员确认，并同时验证上述责任能力已覆盖。共同参与型不得因为没有固定角色而省略产品或业务责任。

检查内容：

- 用户、场景、目标和成功指标是否明确。
- **用户故事是否覆盖所有核心角色及其关键任务。**
- **每条用户故事是否关联来源 SRC 和对应 REQ。**
- **用户故事是否区分直接证据和 AI 推演。**
- 启用 Adaptive Grill 时，是否有真实成员同意、完整主题覆盖、单问题记录、三项独立确认和正式需求映射；成员证据是否与终端用户证据严格区分。
- 参与矩阵是否记录全部应参与成员的独立提交和公开评审状态。
- 共同参与型是否保留反对、保留和缺席影响，且没有虚报全员共识。
- 需求池是否包含本轮和非本轮事项。
- P0 需求是否具体、原子、可判断。
- 本轮范围和非目标是否清楚。
- 权限、数据和关键业务规则是否明确。
- P0 需求是否具备业务验收标准。
- 关键冲突是否已经决策或明确标记。
- 高风险事项是否有责任人。

结论：

- 通过：进入 `merge-pending`；完成全部成员分支合并和 `main` 验证后进入功能设计与方案验证。
- 条件通过：仅存在不影响功能设计的非阻塞事项；仍须先完成强制合并和验证。
- 退回：返回独立分析、多视角评审或需求合同编写。
- 终止：需求价值或风险不支持继续投入。

## 11. 阶段 B：功能设计与方案验证

### 11.1 目标

让人类和 AI 成员基于同一需求合同独立提出完整功能方案，同时盘点系统现实约束，通过方案比较、原型和用户验证形成最终范围。角色分工型按专业角色组织参与，共同参与型按全员轮次组织参与，但两者使用同一 G1 基线和相同质量标准。

### 11.2 B1 独立功能设计

所有设计成员必须使用同一份通过 G1 的 A03 需求合同和 A04 需求池版本。角色分工型由 A00 指定设计成员；共同参与型由当前轮次全部应参与成员分别提交 A05。

设计完成前，成员原则上不读取其他人的功能设计。共同参与型也不得以共同编辑代替独立方案。每份设计采用相同公共结构，同时保留成员身份和所采用的视角。

A05 模板：

```text
设计成员：
成员类型：人类 / AI
协作模型：role-based / collective-participation
轮次：
角色视角：
使用的需求合同版本：

设计目标和原则：
需求覆盖矩阵：
整体功能架构：
核心用户流程：
异常流程：
功能模块：
页面或服务行为：
业务规则：
权限与角色行为：
数据输入与输出：
状态变化：
消息、通知和外部交互：
MVP 实现范围：
未覆盖需求：
新增需求建议：
关键取舍：
风险和待确认问题：
```

每项功能必须关联 `REQ` 和 `AC`。未获批准的新需求只能进入 A04，不能直接加入当前方案。

AI 项目协调员在独立设计窗口关闭时更新参与矩阵。共同参与型必须明确每名应参与成员的 A05 提交位置；存在事前豁免时记录原因、影响和补救措施。

### 11.3 B2 系统盘点与技术可行性

系统盘点和独立功能设计并行进行。

- 角色分工型由技术负责人和 AI 技术架构师负责 A06，其他被指定成员提供补充。
- 共同参与型由全部应参与成员分别提交系统事实、约束、未知项或无法访问说明，再由指定主笔汇总 A06；具备技术责任能力的人类成员负责确认关键系统事实和高风险技术判断。

默认只读检查：

- 目标仓库、主要模块和技术栈。
- 数据库表、字段、状态值、迁移和数据质量。
- API、任务、回调、消息和第三方服务。
- 登录、权限、租户和隐私边界。
- 日志、监控、部署、配置和环境。
- 与需求冲突的现有约束。
- 需要原型验证的技术未知项。
- 数据迁移、兼容和回滚风险。

A06 必须区分已确认系统事实、未知项和技术推断。无法访问的系统不得标记为已盘点。共同参与不代表所有成员都必须具备同等系统权限；没有权限时应提交“无法访问”和待核实项，不得猜测为系统事实。

参与矩阵分别记录 B1 独立功能设计和 B2 系统盘点贡献状态。共同参与型任一轮次缺失不得被 A06 汇总结果掩盖。

### 11.4 B3 多方案评审与共识功能设计

所有独立方案完成且独立窗口关闭后，团队同时查看 A05 和 A06。角色分工型由相关角色参加，共同参与型由全部应参与成员完成公开评审，按以下顺序比较：

1. 需求覆盖是否完整。
2. 核心流程和异常流程有什么差异。
3. 业务规则、权限和状态变化是否冲突。
4. 是否存在未批准的新需求。
5. 哪种方案对用户更简单。
6. 哪种方案符合真实系统约束。
7. 哪些部分可以组合。
8. 哪些差异必须通过原型或用户验证决定。

差异处理：

| 差异类型             | 处理方式                       |
| -------------------- | ------------------------------ |
| 需求理解不同         | 返回阶段 A 修订需求合同        |
| 正常功能方案差异     | 记录`DEC` 并选择、组合或验证 |
| 未批准的新需求       | 进入 A04 需求池                |
| 技术不可行或风险过高 | 调整方案或触发专项 Gate        |
| 缺少证据             | 进入原型或用户验证             |

本环节形成共识功能设计草案，但不设置固定人工 Gate。

共同参与型的评审记录必须列出每名成员对关键方案决策的确认、反对或保留意见。协调员或指定主笔负责形成草案，但不得覆盖 A05 原始提交；没有完整参与时不得把草案标记为“全员一致”。

### 11.5 B4 原型与用户验证

原型只用于降低不确定性，不代表生产实现。

角色分工型由设计、用户研究、产品和技术相关成员按任务分工参与。共同参与型由全部应参与成员参加原型任务定义、结果评审和反馈处理；真实用户验证仍必须由真实用户证据支持，AI 或团队成员意见不能冒充用户证据。

必须：

- 标注“原型、草案、Demo 或验证用途”。
- 使用样例、脱敏或测试数据。
- 明确每个原型要验证的问题和判定标准。
- 使用非诱导性的用户任务。
- 保留用户原话、来源、场景和行为证据。
- 记录验证了什么、没有验证什么。
- 记录不能直接生产化的原因和生产差距。
- 在参与矩阵记录原型定义评审和结果评审状态。

反馈分类：

- 理解偏差。
- 新增需求。
- 体验问题。
- 边界问题。
- 伪需求。
- 技术限制。
- 暂缓项。

### 11.6 B5 反馈回流和 A07 定稿

| 反馈影响                       | 处理位置                    |
| ------------------------------ | --------------------------- |
| 用户、场景、目标或 P0 需求改变 | 返回阶段 A，重新通过 G1     |
| 新增需求或优先级变化           | 更新 A04，必要时重新通过 G1 |
| 功能流程或规则变化             | 更新共识功能设计            |
| 技术约束变化                   | 更新 A06 和方案决策         |
| 仅为非本轮优化                 | 进入 A04，不改变当前范围    |

A07 共识功能设计与验证报告包括：

- 使用的协作模型、参与矩阵摘要、缺席或豁免影响。
- 采用的功能方案和决策依据。
- 成员确认、反对、保留意见及其处理结果。
- 最终核心流程、功能模块和规则。
- 需求覆盖矩阵。
- 原型目标、用户任务和验证证据。
- 用户反馈及处理结果。
- 本轮范围变化。
- 原型未验证内容。
- 原型到生产的差距。
- 更新后的 A03、A04 和验收标准版本。

A07 由明确的主笔或协调员汇总。共同参与型全员可以评审候选稿，但任何成员不得直接重写或删除他人的原始 A05、系统盘点贡献或评审意见。

### 11.7 G2 方案与范围冻结

责任能力：产品决策、业务决策和技术决策；R2/R3 项目增加测试、安全、数据或其他对应专项责任。

批准人按 A00 的 Gate 确认策略确定：`accountable-members` 由上述责任能力映射到的人类成员全部确认；`all-participants` 由全部有效人类参与成员确认，并同时验证上述责任能力已覆盖。

检查内容：

- 采用的功能方案是否清楚。
- P0 需求是否全部被方案覆盖。
- 核心流程是否经过适当验证。
- 用户反馈是否保留来源并完成处理。
- 新增需求是否进入需求池而非直接扩大范围。
- 系统约束和重大技术风险是否暴露。
- 原型到生产差距是否完整。
- 最终 MVP 范围和非本轮项是否明确。
- 参与矩阵是否覆盖 B1/B2 独立贡献、B3 共同评审及 B4/B5 验证评审。
- 共同参与型的反对、保留和缺席影响是否已处理或明确为阻塞/非阻塞事项。

人工通过并完成全部成员分支合并和 `main` 验证后冻结：

- P0 范围。
- 核心用户流程。
- 关键业务、权限和数据规则。
- 需求验收口径。
- 采用的功能方案。

G2 后改变以上内容必须执行变更影响评估；改变 P0 或高风险边界时重新通过 G2 或触发专项 Gate。

## 12. 阶段 C：开发准备与准入

### 12.1 目标

把冻结后的产品方案转化为正式技术方案、工程验收标准、测试矩阵和边界明确的任务包，并判断是否允许开始真实开发。

- 角色分工型由产品、技术、测试和项目责任成员分别承担主责并进行交叉审查。
- 共同参与型由全部应参与成员分别提交产品、技术、测试、风险和任务拆分建议，协调员或指定主笔形成 A08/A09 候选稿，再由全体应参与成员交叉评审。

两种模式都必须为 A08、A09 指定主笔和最终任务负责人。全员参与不能替代具体任务责任，也不能让多人无协调地覆盖同一候选文件。

### 12.2 C1 最终产品与技术方案

A08 至少包含：

- 协作模型、参与成员、主笔和交叉评审状态。
- 最终产品目标、范围和非目标。
- 最终功能模块、流程、规则和状态变化。
- 最终需求与功能覆盖矩阵。
- 受影响代码模块和责任边界。
- 数据模型、数据库变化和迁移策略。
- 正式 API、应用、云函数和外部契约。
- 认证、权限、隐私和租户隔离。
- 支付、退款、上传、通知和第三方服务边界。
- 异步任务、回调、缓存、限流和幂等。
- 日志、监控和告警。
- 兼容、灰度、停止条件和回滚方案。
- 原型到生产差距的处理方式。
- 高风险事项、负责人和备选方案。

共同参与型的 A08 必须附成员建议的采纳、拒绝、待确认和保留意见对照；关键技术事实由具备技术责任能力的人类成员确认，R2/R3 专项判断由对应专项负责人确认。

### 12.3 C2 工程验收与测试矩阵

在阶段 A 的业务验收标准上补充：

- API 和集成验证。
- 权限、安全和隐私验证。
- 数据迁移、兼容和一致性验证。
- 性能、容量和稳定性验证。
- 日志、监控和告警验证。
- 灰度、停止和回滚验证。

测试矩阵字段：

| 字段           | 内容                                                 |
| -------------- | ---------------------------------------------------- |
| 测试 ID        | `TEST-NNN`                                         |
| 关联需求和验收 | `REQ`、`AC`                                      |
| 优先级         | P0、P1、P2                                           |
| 类型           | 正常、异常、权限、边界、数据、集成、安全、性能、回滚 |
| 前置条件       | 环境、数据和依赖                                     |
| 操作和输入     | 测试动作                                             |
| 预期结果       | 可判断的结果                                         |
| 自动化适合度   | 是、否、部分                                         |
| 执行阶段       | 单元、集成、端到端、发布前或发布后                   |

共同参与型由全体应参与成员交叉评审 P0 测试覆盖和失败路径，测试责任能力对应的人类成员对质量准入口径承担最终责任。参与矩阵记录建议提交和交叉评审状态。

### 12.4 C3 开发任务包

每个 A09 任务包必须可以由一个人类或 AI 开发成员独立领取：

```text
任务编号：
任务名称：
负责人类型：人类 / AI / 协作
任务负责人 ID：
协作成员 ID：
主笔或主要修改者：
目标：
关联需求和验收：
前置依赖：
允许修改的模块或文件：
禁止修改的范围：
上下文和输入：
预期输出：
测试要求：
数据迁移和回滚要求：
实现约束：
风险等级：
人工审查点：
完成定义：
最终报告要求：
```

任务拆分规则：

- 单个任务只有一个清晰目标。
- 每个任务必须有一个可追责的任务负责人；协作任务还必须明确主笔、成员边界和合并方式。
- 数据库、公共 API、权限和部署变更尽量单独成包。
- 多个 AI 成员不得无协调地修改同一核心模块或迁移。
- 高风险任务必须由人类负责人承担批准责任。
- 任务包不得自行改变需求和功能基线。
- 共同参与型允许所有成员参与任务建议和评审，但不默认授权所有成员修改全部文件或生产资源。

### 12.5 G3 开发准入

责任能力：项目决策、产品决策、技术决策和测试决策；R2/R3 项目增加安全、数据、合规或其他对应专项责任。

批准人按 A00 的 Gate 确认策略确定：`accountable-members` 由上述责任能力映射到的人类成员全部确认；`all-participants` 由全部有效人类参与成员确认，并同时验证上述责任能力已覆盖。

检查表：

```text
- [ ] G1 需求合同已通过且版本明确
- [ ] G2 方案与范围已冻结
- [ ] P0 需求来源、验收、功能、任务和测试追踪率为 100%
- [ ] 汇合产物实质内容来源覆盖率为 100%，来源块、成员分支 commit 和哈希校验通过
- [ ] 协作模型、Gate 确认策略、参与矩阵和 Gate 责任映射完整
- [ ] 共同参与型的建议提交、交叉评审、反对和保留意见均已记录并处理
- [ ] 最终产品方案和技术方案一致
- [ ] 目标仓库、技术栈、部署环境和责任边界明确
- [ ] 数据库、API、权限、隐私和外部依赖已审查
- [ ] 原型到生产差距已进入正式方案
- [ ] 数据迁移、兼容和回滚策略明确
- [ ] 测试矩阵覆盖正常、异常、权限、边界和数据场景
- [ ] 高风险项目具备安全、性能、监控和回滚验证
- [ ] 任务包范围、禁止事项、依赖和执行顺序明确
- [ ] 每个任务包均有具体负责人，协作任务的主笔和修改边界明确
- [ ] R2/R3 风险均有责任人和批准记录
- [ ] 所有开发阻塞项已清零
```

结论只有：

- 通过：进入 `merge-pending`；完成全部成员分支合并和 `main` 验证后允许人类和 AI 开发成员进入真实开发。
- 条件通过：仅存在不影响安全开发的非阻塞事项，必须记录负责人和期限；仍须先完成强制合并和验证。
- 退回：返回阶段 C 补充；涉及范围或方案时返回 G1 或 G2。
- 终止：价值、成本、合规或风险不再支持继续。

以下情况一票否决：

- P0 需求无法测试或验收。
- P0 范围、核心流程或关键规则仍存在未决冲突。
- 目标仓库、技术栈或部署环境不明确。
- 数据库迁移没有兼容和回滚方案。
- 权限、隐私、支付、订单或敏感数据未经审查。
- 原型被当作正式实现，生产差距未处理。
- 公共 API 或外部契约变化未获批准。
- 任务包没有范围、测试或完成定义。
- R2/R3 风险无责任人。
- 共同参与型参与矩阵不完整却声称全员共识，或 `all-participants` 缺少任一应确认的人类成员。
- 人工批准记录缺失。
- 汇合内容存在未标记、无台账、伪造来源、失效 commit/哈希或未审核来源记录。

## 13. G1—G3 Gate 通用规则

本节的 `gate-review-pack`、冻结成员 `expected_head`、`merge-pending` 和阶段基线规则仅适用于 A—C 的 G1—G3。G4/G5 使用第 21 节的发布候选、集成、灰度和观察证据，并受当前 D—E CLI 能力边界约束。

### 13.1 Gate 材料

AI 项目协调员必须先按 `init-gate-review → 撰写 → validate-gate-review → prepare-gate` 形成并绑定 `gate/gate-review-pack.md`。评审包面向真实人类决策者，不能只罗列 YAML 和 ID；必须解释用户问题、成员观点、方案或技术结论、分歧、风险、取舍和建议决定。它是正式事实的只读投影，不得反向覆盖候选产物、成员提交、来源台账、参与状态或决策记录。

评审包和 Gate 详细材料至少包括：

- 当前执行模式、协作模型和 Gate 确认策略。
- 当前轮次参与矩阵、缺席/豁免及影响。
- Gate 必需责任能力、对应人类成员和覆盖结果。
- 当前基线版本。
- 已确认事项。
- 需要决策的差异。
- 阻塞和非阻塞事项。
- 高风险事项及负责人。
- 建议结论和回退位置。
- 目标 `main`、全部有效成员的登记分支、冻结 `expected_head`，以及人工审核是否覆盖这些精确 commit。
- 成员来源索引哈希、汇合内容溯源台账、覆盖报告、形成方式和已审核状态。
- 逐名有效人类成员的观点、原始立场、处理结果和仍保留意见，并使用成员标记定位。
- 每项 Gate 必需产物的仓库相对链接、产物标记和可见来源引用。
- 评审包正文哈希、来源指纹、来源 commit、对比版本身份和 stale 状态。

### 13.2 Gate 结论记录

```text
Gate：
审查日期：
基线版本：
最高风险等级：
执行模式：standard / lightweight
协作模型：role-based / collective-participation
Gate 确认策略：accountable-members / all-participants
必需责任能力：
责任能力对应人类成员：
应确认人类成员：
已确认人类成员：
反对或保留成员：
参与矩阵位置：
内容来源索引：
内容来源台账：
实质内容来源覆盖率：
来源索引哈希与审核状态：
人工可读评审包路径：
评审包正文哈希：
评审包来源指纹与来源 commit：
对比版本状态与身份：none / published / reviewed / baseline
评审材料是否 stale：
缺席、豁免及影响：
结论：通过 / 条件通过 / 退回 / 终止

已确认：
未确认但不阻塞：
阻塞事项：
高风险事项：
条件通过要求：
回退位置：
下一步：

人工批准人：

强制合并状态：pending-human-approval / approved-pending-merge / merged-and-verified
目标 main 分支：
成员分支与 expected_head：
人工审核是否覆盖全部分支头：
main 合并前 commit：
main 合并后 commit：
祖先关系校验：
合并时间：
```

Gate 记录必须能机械判断策略是否满足：`accountable-members` 检查全部责任成员已确认；`all-participants` 检查全部有效人类参与成员已确认，同时检查必需责任能力均已映射。R2/R3 还必须单独列出专项责任人和专项批准记录。`approve-gate` 必须拒绝正文哈希、来源指纹、对比身份或冻结分支头已经变化的材料。人工确认满足后只能进入 `merge-pending`；全部成员分支进入 `main` 且祖先关系校验通过后，记录才能变为 `merged-and-verified`，把实际审核评审包复制入不可覆盖基线，并进入 Skill 发行确认。

### 13.3 条件通过

条件通过只能用于非阻塞事项，必须记录责任人、完成日期和逾期动作。影响产品范围、数据安全、技术可行性或开发安全的问题不得条件通过。

缺少必需责任能力、必需人工批准、共同参与型独立提交/公开评审记录，或 `all-participants` 下任一应确认成员未确认，均不得用条件通过绕过。

## 14. 需求和范围变更

### 14.1 新需求

任何新增需求先进入 A04，不得直接写入当前功能方案、技术方案或开发任务。

### 14.2 回流规则

| 变化                            | 回流位置                            |
| ------------------------------- | ----------------------------------- |
| 用户、目标、场景、P0 需求改变   | 阶段 A，重新 G1                     |
| 新增 P1/P2 需求                 | A04，由产品负责人判断是否影响 G1/G2 |
| 核心功能流程或规则改变          | 阶段 B，重新 G2                     |
| 技术实现调整但不改变功能和验收  | 阶段 C                              |
| 数据、API、权限或部署高风险变化 | 专项 Gate，必要时重新 G2/G3         |
| G3 后扩大开发范围               | 正式变更控制，不得直接加入任务      |

### 14.3 基线版本升级

以下变化升级主版本：

- 核心用户或业务目标变化。
- P0 范围变化。
- 核心流程和关键业务规则变化。
- 权限模型、数据模型或公共 API 重大变化。
- 业务验收口径变化。

### 14.4 协作模型、成员范围和 Gate 策略变更

协作模型、应参与成员范围或 Gate 确认策略变更必须：

1. 形成 `DEC`，说明原因、生效轮次和影响。
2. 更新 A00 成员卡、参与矩阵、任务责任和 Gate 责任映射。
3. 在独立窗口开始前生效；若在窗口中改变应参与成员，受影响轮次原则上关闭并重新分发。
4. 在 Gate 审查开始前完成；不得为使失败的 Gate 通过而追溯性排除成员或降低确认要求。
5. 对 R2/R3 专项责任重新校验，确保专业负责人和批准链未丢失。

## 15. AI 成员运行规范

### 15.1 开始任务前

第一步只能读取 assignment 的 Skill 契约元数据、发行包 `package-manifest.json` 和仓库 `.github/sop-runtime-lock.json`，不得先读取任务正文、接受任务、开展访谈或创建产物。预检必须：

1. 按任务阶段和 `runtime_profile` 从 `runtime_releases` 中选出唯一候选。
2. 核对运行时名称、精确版本、运行时 `build_id`、协议、项目 schema 和阶段用途。
3. 核对包版本、包级 `build_id`、包路径和发行 commit；D—E 当前任务未携带包级字段时，改由 runtime lock 的 `source` 和 SHA-256 与 manifest 交叉验证。
4. 确认 CLI 与协议路径真实存在、均为包内相对路径且解析后没有逃逸发行包。
5. 核对 CLI 内 `SKILL_VERSION`、`BUILD_ID` 与协议资产、manifest 和 runtime lock 完全一致。
6. 找不到唯一匹配时，只输出结构化版本提醒和仓库中真实存在的候选路径，然后停止；不得自动安装、升级、降级、使用更高版本或切换到另一 profile。

当前 Member 路由为：

| profile | 任务运行时 | 受信任仓库入口 | 统一包内 CLI |
| --- | --- | --- | --- |
| `predevelopment` | `1.8.1 / member-cli-1.8.1-assignment-acceptance-v1` | `.github/scripts/sop_member_cli.py` | `ai-sop-member/scripts/member_cli.py` |
| `development_delivery` | `2.0.0 / member-dev-cli-2.0.0-v1` | `.github/scripts/sop_member_development_cli.py` | `ai-sop-member/scripts/development_cli.py` |
| `legacy_predevelopment` | `1.8.0 / member-cli-1.8.0-ai-dialogue-exact-release-v1` | `.github/scripts/sop_member_cli_1_8_0.py` | `ai-sop-member/scripts/member_cli_1_8_0.py` |

当前没有一个自动选择全部 profile 的统一 dispatcher。上表路由属于调用具体 CLI 前的预检与仓库治理责任；不能只根据文件名选择，最终必须验证脚本常量和哈希。`legacy_predevelopment` 只服务已经精确绑定的历史任务，不用于签发新任务，也不追溯补签接受凭证。

预检成功后，AI 成员才读取：

- 自己的成员卡（角色卡）。
- A00 当前阶段、执行模式、协作模型、Gate 确认策略和最新 Gate 结论。
- 当前轮次参与矩阵、自己的参与义务和任务责任。
- 当前批准的需求、方案和版本。
- 与本任务相关的风险、依赖和禁止事项。
- 登记分支、协调者授权任务 commit、实际合入该任务的 `main` 基线快照、全部授权基线，以及任务来源、目标、范围、交付物、验收标准、`dispatch_confirmation`、`task_contract_hash` 和 `submission_confirmation`。
- 项目级 `ai_dialogue_collaboration` 快照，以及适用时的 `acceptance_policy`。

随后必须在独立 clone 或 worktree 中执行对应运行时的 `workspace-check` 和 `inspect`。当前分支、远程登记分支、授权任务文件、实际合入的 main 快照、协议、schema、身份、协作模型、轮次、基线或任务契约任一不一致时停止，不得切到 `main`、自行 rebase、强推或手工修补中央文件。任务进入成员分支后，后续只更新看板或中央状态投影的 `main` commit 不要求成员循环合并；Member CLI 必须重复校验本地任务与协调者授权任务完全一致，并拒绝成员修改授权基线。

成员已有历史提交时，登记分支与 `main` 正常分叉，`git merge --ff-only origin/main` 可能失败。此时成员先停止；只有协调者核对双方精确 head、确认无冲突并明确授权后，成员才可在登记分支执行一次 `git merge --no-edit <coordinator-verified-main-sha>` 并普通 push。不得使用可移动 ref 替代已核验 SHA，不得 rebase、reset、squash 或强推。

```powershell
python .github/scripts/sop_member_cli.py workspace-check <assignment.yaml> --member-id <member-id> --fetch
python .github/scripts/sop_member_cli.py inspect <assignment.yaml> --member-id <member-id>
python .github/scripts/sop_member_cli.py accept-assignment <assignment.yaml> --member-id <member-id>
# commit 并 push acceptances/<member-id>/ 下的接受凭证
python .github/scripts/sop_member_cli.py init <assignment.yaml> --member-id <member-id>
```

以上命令是当前 A—C V1.8.1 新任务示例。D—E 使用 `.github/scripts/sop_member_development_cli.py`；精确绑定的历史 V1.8.0 任务使用 `.github/scripts/sop_member_cli_1_8_0.py`，并按其旧合同跳过不存在的 `accept-assignment` 步骤。

### 15.2 执行任务时

AI 成员必须：

- 在成员身份、参与范围、任务责任和批准边界内工作；共同参与型主要角色为空时，可提出跨专业意见，但不得冒充专业批准人。
- 明确区分事实、推断、假设和模拟内容。
- 使用稳定编号建立关联关系。
- 由脚本生成并校验自己 `main-output.md` 的内容块索引，不手工伪造块 ID 或哈希。
- 发现新需求时提交 A04 候选项。
- 发现高风险或范围冲突时升级给对应负责人。
- 不通过悄悄修改文档来消除意见冲突。
- 不覆盖其他成员的原始提交，不把多数意见伪装成全员共识。
- 不替代人工批准 Gate。
- 只在任务显式授权时执行 Adaptive Grill；取得真实成员同意，每轮只问一个问题，保留证据边界并完成三项独立确认。
- 按任务继承的 AI 对话协同策略完成任务复述、思路地图、逐问发散、阶段复述、替代方案/反例/风险/取舍比较和成员立场收敛；AI 推断与成员确认内容分开记录。
- 无论是否开展 Grill，都必须在提交前取得登记 `human_owner` 对当前最终正文哈希和本人个人立场的明确确认；AI 不得代选、代答或代签。
- 只写 `submissions/<member-id>/<submission-id>/`；`submit` 只冻结提交清单，随后仍须在登记分支 commit 和 push。

每次 V1.8.0+ 新任务提交至少包含 `submission-manifest.yaml`、`main-output.md`、`content-block-index.yaml`、`source-ledger.yaml`、`assumptions-and-gaps.yaml`、`risks-and-new-requirements.yaml`、`human-submission-confirmation.yaml` 和 `ai-dialogue-summary.yaml`。V1.8.1+ 任务还必须在提交目录之外具有已 push 且可达的任务接受凭证；启用 Adaptive Grill 时再增加 `human-collaboration-log.yaml` 和 `grill-summary.yaml`。提交清单状态只允许 `in-progress`、`submitted`、`blocked`，且只有脚本可以封装为 `submitted`。

```powershell
python .github/scripts/sop_member_cli.py index-content <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
python .github/scripts/sop_member_cli.py prepare-confirmation <submission-dir> --assignment <assignment.yaml> --member-id <member-id> --position <confirm|oppose|question|reserve> --position-statement "<owner 原话>"
python .github/scripts/sop_member_cli.py confirm-submission <submission-dir> --assignment <assignment.yaml> --member-id <member-id> --confirmed-by "<registered human_owner>" --document-hash "<preview hash>" --confirmation-token "<preview token>"
python .github/scripts/sop_member_cli.py validate <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
python .github/scripts/sop_member_cli.py submit <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
```

### 15.3 完成任务后

```text
AI 成员：
协作模型：
当前角色：可为空
当前轮次和参与类型：
本次任务责任：
任务来源、范围、验收与契约哈希校验：
Member 任务运行时 profile、版本与运行时 build_id：
Member 发行包版本、包级 build_id、包路径与发行 commit（D—E 当前由 runtime lock 提供）：
任务接受状态与远端凭证：pending / accepted / invalid / legacy-not-required
AI 对话协同：required-completed / optional-completed / optional-skipped / blocked
人类协同模式：none / adaptive-grill
Grill 状态与三项确认：不适用 / grill-completed / blocked
最终提交确认：required / legacy-not-required
确认正文哈希：
个人立场：confirm / oppose / question / reserve
确认人、确认时间和确认记录哈希：
提交确认 Gate 效力：none
执行阶段：
本次输入版本：
创建或更新的产物：
新增假设：
新增需求候选：
新增风险：
未解决问题：
建议下一步：
是否越过人工 Gate：否
```

## 16. 最小执行版本

低风险项目可以把产物合并为四组文件：

1. 项目状态、协作模型、成员卡、参与矩阵、Gate 责任、独立分析和需求评审。
2. 需求合同和需求池。
3. 独立功能设计、系统盘点、共识方案和验证报告。
4. 最终产品技术方案、测试任务包和开发准入记录。

即使采用最小版本，也不能省略：

- AI 成员身份、参与范围和职责。
- 执行模式、协作模型、任务责任、Gate 责任映射和参与矩阵。
- 每个分发任务的任务来源、目标、范围、交付物、验收、预览确认和契约哈希。
- Gate 后稳定 Member Skill 发行确认；A—C 新任务完整绑定运行时与发行包双层身份，D—E 当前任务精确绑定运行时并由 runtime lock 保护包来源。
- V1.8.1+ 新任务由成员在登记分支生成并 push 的显式接受凭证，以及协调端精确远端观测结果。
- 项目级 AI 对话协同策略和每项 V1.8.0+ 任务的 `ai-dialogue-summary.yaml`。
- V1.7.5+ 新任务的最终正文哈希与个人立场确认、确认记录哈希和 stale 阻断。
- 独立需求分析的来源记录和用户故事。
- 启用 Adaptive Grill 时的真实成员同意、两份协同文件、必需主题覆盖、三项独立确认和正式产物映射。
- 需求池、P0 需求和业务验收标准。
- 独立功能设计。
- 系统盘点和原型生产差距。
- 工程测试矩阵和开发任务边界。
- 成员提交内容块索引、汇合稿 `P` 标识、来源台账和 100% 内容来源覆盖报告。
- G1、G2、G3 人工结论。
- G1、G2、G3 人工可读评审包、正文哈希、来源指纹和 stale 校验。
- 每个 A—C 固定 Gate 的全部有效成员分支合并证据和 `main` 祖先关系校验。

## 17. A—C 完成标准

本 SOP 完成必须满足：

- 人类和 AI 项目成员身份明确，A00 已选择执行模式、协作模型和 Gate 确认策略。
- 参与、任务责任和 Gate 责任分别记录，没有以“团队共同负责”替代具体负责人。
- 参与矩阵覆盖阶段 A、B、C 的应参与成员、独立提交、公开评审、例外和 Gate 确认状态。
- 共同参与型保持先独立发散再公开收敛，原始提交、少数意见、缺席和豁免影响均可追溯。
- 独立需求分析保留来源、方法和身份。
- 所有任务均经过当前用户确认的完整预览，`dispatch_confirmation` 和 `task_contract_hash` 有效，已分发任务未被原地改写。
- Coordinator 与 Member 保持独立发行；成员在任何产出前完成唯一 runtime profile、精确运行时、协议、schema、发行包来源和 runtime lock 预检，只在登记分支和独立工作区提交，协调端使用受信任校验器验证任务自身可达的远程精确 commit。
- V1.8.1+ 新任务具有成员生成并 push 的有效接受凭证，中央投影区分成员声明时间和协调端首次观测时间；历史任务未被追溯补签。
- 项目级 AI 对话协同策略已被全部 V1.8.0+ 任务继承；必需协同已完成，可选协同的完成或明确跳过均有结构化记录，且没有替代正式产物或人工权限链。
- 启用 Adaptive Grill 的任务已取得登记真实成员同意、完成全部主题和三项独立确认，并把中间证据映射到正式需求产物。
- 所有 V1.7.5+ 新任务均具有登记 owner 对当前最终正文哈希和个人立场的明确确认；`oppose`、`question` 和 `reserve` 已如实保留并进入后续处理，且提交确认未被当作 Gate 批准。
- G1 形成正式需求合同和需求池。
- 多个功能设计基于同一需求合同独立产生。
- 系统盘点在方案冻结前完成。
- 原型和用户反馈已处理，生产差距已记录。
- G2 已冻结范围和功能方案。
- 最终产品、技术、测试和任务包保持一致。
- G3 明确允许进入正式开发。
- G1、G2、G3 人工通过后均已把全部有效成员的已审核分支 commit 合并到 `main`，且合并证据可追溯。
- 每个 Gate 都使用已校验并绑定正文哈希、来源指纹和冻结分支头的人工可读评审包；实际审核版本随决议进入不可覆盖基线。
- `accountable-members` 已取得全部责任成员确认，或 `all-participants` 已取得全部有效人类参与成员确认且责任能力完整。
- R2/R3 项目具有对应专项人类负责人和专项批准记录，不因共同参与或全员确认而被取消。
- P0 需求全链路追踪率为 100%。
- 汇合文档实质内容来源覆盖率为 100%，每条内容可反查到成员提交、分支精确 commit、源块哈希和原始 `SRC`。
- 没有未解决的一票否决项。

以下情况视为 SOP 未完成：

- AI 冒充人类、用户或人工批准人。
- 关键来源、需求变化或决策只存在于聊天记录。
- 协调者或 AI 自行发明任务范围，未展示完整预览即分发，复用失效 Token，或成员执行未确认/哈希不一致的任务。
- AI 未经授权启动 Adaptive Grill、代替真实成员回答或确认、一次提出多个问题、把成员判断冒充终端用户证据，或仅因达到问题上限就宣称完成。
- 把 `human_collaboration: none` 解释为免除最终提交确认，AI 代选立场、代签确认，正文变化后继续复用旧确认，或把成员提交确认解释为 Gate、合并、基线或发布批准。
- Coordinator/Member 协议、schema、profile、运行时版本、运行时 `build_id`、包来源或 runtime lock 不匹配，把包版本误作任务运行时版本，使用更高版本或另一 profile 替代任务绑定运行时，成员修改中央状态，或协调端冒充成员补写提交/接受凭证。
- 把 clone、pull、通知或 Issue 当作任务接受，V1.8.1+ 任务未有有效远端接受凭证就开始产出，或对历史任务追溯补签。
- 必需 AI 对话协同未完成仍继续提交，AI 替成员回答或选择立场，或把 `ai-dialogue-summary.yaml` 当作 Grill、正式产物、最终提交确认或 Gate 证据。
- 新需求绕过需求池直接进入方案或开发。
- 原型被当作生产实现。
- 固定 Gate 未经人工确认即进入下一承诺阶段。
- Gate 评审包缺少逐成员观点或必需产物链接，材料或来源变化后继续沿用 stale 准备/批准，或从评审包反向覆盖正式事实。
- 人工已确认但仍处于 `merge-pending` 时冻结基线、推进阶段，或遗漏任一有效成员分支。
- 审核后成员分支头变化却继续合并，合并冲突后手工标记完成，或未验证冻结 commit 是 `main` 的祖先。
- 共同参与型参与不完整却声称“全员共识”或“全员通过”。
- 多人共同编辑覆盖原始独立提交，或共同任务没有明确负责人、主笔和边界。
- Gate 必需责任能力未映射到具体人类成员，或以全员签字替代 R2/R3 专项负责人。
- 高风险事项未触发专项审查。
- 汇合内容缺少来源标识或台账，台账与成员 commit/哈希不一致，或以协调者新增、人工决定冒充成员原文。

## 18. 版本结构映射

### 18.1 与 V1.0 的结构映射

| V1.0 内容             | V1.1 调整                            |
| --------------------- | ------------------------------------ |
| U0 阶段识别           | 合并进入 A00 项目启动                |
| U1 统一输入与独立分析 | 删除统一输入包，改为多来源独立分析   |
| G1 分析准入           | 删除，不再设置 Gate                  |
| U2 需求共识           | 与需求池、原子需求和验收定义合并     |
| U3 需求池与可验收定义 | 合并进入阶段 A 和 G1 需求合同        |
| U4 系统盘点           | 与独立功能设计并行                   |
| U5 PRD 与原型方案     | 拆为独立功能设计和多方案评审         |
| U6 原型与用户验证     | 合并进入阶段 B，完成后统一 G2        |
| U7 最终方案与任务包   | 合并进入阶段 C                       |
| U8 开发准入           | 保留并改为 G3                        |
| 八个阶段 Gate         | 压缩为三个固定 Gate，加风险触发 Gate |

### 18.2 V1.1 到 V1.2 的新增规则

| V1.1 状态 | V1.2 调整 |
| ---------- | --------- |
| 默认按固定角色描述团队 | 新增 `role-based` 和 `collective-participation` 两种协作模型 |
| 执行模式同时承载部分组织含义 | 明确 `execution_mode` 与 `collaboration_model` 正交，可形成四种组合 |
| 参与和角色责任混合表达 | 分离成员参与、具体任务责任和 Gate 责任能力 |
| 主要按角色分发工作 | 共同参与型每轮默认覆盖全部有效成员，仍指定主笔和任务负责人 |
| 独立提交后进行团队评审 | 共同参与型明确全员公开评审、少数意见保留和禁止覆盖原始提交 |
| Gate 按固定角色列批准人 | 新增 `accountable-members` 与 `all-participants` 两种确认策略 |
| 没有统一参与状态载体 | 在 A00 中新增贯穿 A/B/C 的全员参与矩阵 |
| R2/R3 增加专业负责人 | 保留并强化；任何协作模型和确认策略均不得取消专项责任 |

### 18.3 V1.2 到 V1.3 的新增规则

| V1.2 状态 | V1.3 调整 |
| --- | --- |
| 人工 Gate 通过后直接冻结基线 | 增加不可绕过的 `merge-pending`，合并验证后才冻结 |
| 成员分支只作为分布式协作建议 | A00 强制登记唯一成员分支和目标 `main` |
| Gate 主要审核汇总产物 | Gate 同时冻结并审核每个有效成员分支的精确 commit |
| 协调员汇总分支可在 Gate 后合并 | 强制合并全部有效成员分支，不得只合并汇总分支 |
| 合并冲突处理未形成门禁 | 使用临时集成分支；任一失败保持 `main` 不变并阻塞阶段 |
| 缺少合并完成的机械证据 | 记录 `main` 前后 commit，并验证每个冻结 commit 为其祖先 |

### 18.4 V1.3 到 V1.4 的新增规则

| V1.3 状态 | V1.4 调整 |
| --- | --- |
| `project-state.yaml` 主要在阶段和 Gate 动作时更新 | 所有协调者写命令完成后自动刷新成员提交投影 |
| 协调者主要读取当前工作树中的成员提交 | 新增对远程成员分支的只读观察，无需先合并即可识别提交 |
| 提交索引可能落后于成员最新 push | 新增 `refresh-project-state --fetch`，供协调者、CI 或 Webhook 即时重算 |
| 项目总状态缺少逐任务提交明细 | 新增 `submission_tracking`，记录阶段汇总、成员、分支、观察 commit、校验状态和缺失项 |
| 远程提交与本地已校验提交未明确区分 | 远程完整提交先记为 `pending-validation`，进入工作树并校验后记为 `valid` |
| 中央状态的写入触发点不统一 | 成员保持只写自己分支，中央状态只由协调者命令或授权自动化更新 |

### 18.5 V1.4 到 V1.5 的新增规则

| V1.4 状态 | V1.5 调整 |
| --- | --- |
| 能确认成员提交是否存在，但不能逐段解释汇合稿来源 | 新增 `SB` 成员内容块和 `P` 汇合来源标识 |
| 主要按文件和提交层面追踪成员工作 | 新增正文块哈希、标题路径、摘要和原始 `SRC` 引用 |
| 汇总稿通过文字说明来源，缺少机器校验 | 新增来源索引、溯源台账和覆盖报告三件套 |
| 多成员综合、人工决定和协调者新增未统一分类 | 新增八种 `derivation_type`，多来源必须全部保留 |
| 来源可能依赖浮动分支名或行号 | 强制记录登记分支的精确 commit 和稳定内容块哈希 |
| Gate 只校验需求追踪、参与和成员分支合并 | `prepare-gate` 新增 100% 实质内容来源覆盖及哈希一致性门禁 |
| 历史汇合内容无法回溯时没有统一表达 | 迁移项目允许经审核并说明原因的 `legacy-unattributed`；新项目禁止使用 |

### 18.6 V1.5 到 V1.6 的新增规则

| V1.5 状态 | V1.6 调整 |
| --- | --- |
| `project-state.yaml` 已实时更新，但老板需要进入仓库查找文件 | 新增一个固定 GitHub Issue 作为老板状态看板 |
| 独立静态页面需要部署、认证和 Token 管理 | 使用私有仓库权限和 GitHub Actions，不新增服务器或浏览器 Token |
| 状态展示方式未统一 | 统一展示总览、阶段统计、当前任务、阻塞、风险和更新时间 |
| 看板可能被误认为事实源 | 明确 Issue 仅是只读投影，状态文件、任务、提交和 Gate 记录仍是事实源 |
| “实时”容易被理解为本地修改立即可见 | 明确刷新边界为中央状态提交并推送到 `main` 后自动更新 |

### 18.7 V1.6 到 V1.7 的新增规则

| V1.6 状态 | V1.7 调整 |
| --- | --- |
| 老板看板使用固定 GitHub Issue，界面受 Issue 样式限制 | 改为仓库根 README 内嵌自动生成的静态 SVG |
| 老板需要收藏 Issue 地址 | 老板进入私有仓库首页即可查看项目状态 |
| 工作流使用 `issues: write` 更新正文 | 工作流使用 `contents: write` 提交 README/SVG 快照 |
| 看板安装只生成工作流和脚本 | 安装时同时生成首版 README 看板和 SVG，提交后即可查看 |
| 分支保护对看板写入的处理未明确 | 禁止机器人直推时，将渲染结果纳入中央状态提交或采用受审 PR |
| 个人私有仓库访问权限存在限制 | 明确 README 看板可用，但严格只读访问需迁移到支持精细权限的组织 |
| Issue 被定义为只读投影 | README/SVG 继续保持只读投影，事实源和 Gate 规则不变 |

### 18.8 V1.7 到 V1.7.1 的修复规则

| V1.7 问题 | V1.7.1 修复 |
| --- | --- |
| 成员首次接入缺少 clone、登记分支和 main 同步步骤 | 增加独立工作区接入流程和 `workspace-check` 机械预检 |
| 成员 push 后必须人工刷新中央状态 | 安装登记分支触发、定时兜底的合并式状态/看板工作流 |
| 远程提交只能长期停留在 `pending-validation` | 在精确 commit 的隔离 worktree 中使用受信任 Member CLI 完整校验 |
| 状态提交后依赖第二个 push 工作流更新看板 | 状态、README 和 SVG 在同一次工作流和同一个 commit 中更新 |
| 阶段 A shared-review 引用不存在的 summary | submission index 强制存在；summary 仅在真实完成时引用 |
| 成员 inspect 不检查任务基线文件 | inspect/init/validate/submit 统一校验 baseline refs |
| 已分发错误任务缺少安全恢复方式 | 新增 `supersede-round`，保留旧任务和决策记录后签发新轮次 |

### 18.9 V1.7.1 到 V1.7.2 的新增规则

| V1.7.1 问题 | V1.7.2 调整 |
| --- | --- |
| 协调者可直接创建任务，具体业务字段可能由 AI 或脚本隐式补全 | 增加强制任务录入，只允许整理人类指令、需求池、批准基线、评审待办或确认回流 |
| 任务创建命令立即写文件 | 第一次只输出完整预览和 `confirmation_token`，当前用户明确确认后才正式分发 |
| 任务内容缺少不可漂移保护 | 增加 `task_contract_hash` 与 `dispatch_confirmation`，成员在 inspect/init 前再次校验 |
| 业务交付与模板文件容易混淆 | 明确 `deliverables` 与 `required_outputs` 分别记录 |
| 已分发任务变更缺少统一入口 | 任何字段变化签发新版本或替代轮次，不得原地修改 |

### 18.10 V1.7.2 到 V1.7.3 的发行调整

| V1.7.2 状态 | V1.7.3 调整 |
| --- | --- |
| Coordinator 与 Member 随同一组合包发布 | 拆为可分别安装、协议匹配的 Coordinator 与 Member 独立发行包 |
| 协调端远程校验可能依赖另装完整 Member Skill | Coordinator 包内置受信任 Member 校验器，在精确 commit 的隔离 worktree 中执行完整校验 |
| 成员包与中央能力边界主要依赖流程约定 | 明确 Member 包不包含中央状态、汇总、Gate、基线和看板能力 |

### 18.11 V1.7.3 到 V1.7.4 的新增规则

| V1.7.3 状态 | V1.7.4 调整 |
| --- | --- |
| 需求分析支持多来源方法，但没有标准化的实时人机追问闭环 | 新增任务内置 Adaptive Grill，仅限 `requirement-analysis + isolated-discovery` |
| 普通对话与正式成员协同证据边界不够明确 | 必须由协调者在任务预览中显式启用并登记 `human_owner`；成员不得自行升级 |
| 动态访谈可能一次询问多项或由 AI 代答 | 强制真实成员同意、每轮一个问题、保留原话与更正历史，禁止 AI 代答或伪造确认 |
| 访谈完成标准容易等同于问题数量 | 问题上限仅是限制；完成必须覆盖必需主题并分别确认问题定义、P0 和未决分歧 |
| 访谈记录可能取代正式需求产物 | 新增 `human-collaboration-log.yaml` 与 `grill-summary.yaml` 作为中间证据，并强制映射到 `SRC → 用户故事 → REQ → AC → RISK/GAP` |
| 任务哈希只保护一般任务字段 | V1.7.4 起同时保护 `human_collaboration` 模式、问题上限和协同输出契约 |

### 18.12 V1.7.4 到 V1.7.6 的新增规则

| V1.7.4 问题 | V1.7.6 调整 |
| --- | --- |
| `human_collaboration: none` 容易被误解为不需要任何人工确认 | 明确它只关闭 Grill；所有 V1.7.5+ 新任务仍强制执行独立的提交前最终人工确认 |
| Grill 三项确认绑定访谈中间结论，没有绑定最终正文 | 新增 `submission_confirmation` 契约和 `human-submission-confirmation.yaml`，绑定当前 `main-output.md` 规范化哈希和 owner 个人立场 |
| 成员确认可能被误解为赞同或 Gate 批准 | 允许 `confirm`、`oppose`、`question`、`reserve` 四种真实立场；提交确认的 `authority_scope` 仅限个人贡献，`gate_effect` 固定为 `none` |
| 正文在确认后仍可能变化 | `prepare-confirmation → 明确人工回复 → confirm-submission → validate → submit`；submit 重建索引，正文变化立即使旧确认 stale 并阻断 |
| 中央状态只能看到任务是否提交 | `submission_tracking` 升级为 1.1，逐任务投影确认状态、owner、立场、正文哈希、记录哈希和后续处理标记，并增加阶段/全局确认计数 |
| 本地确认记录可能被夸大为强身份认证 | 明确 `explicit-human-owner` 只保证字段和流程匹配；需要密码学身份保证时另接保护审批、WebAuthn 或签名收据 |
| 新规则可能被追溯伪造到旧任务 | 以 `minimum_skill_version` 版本门控；旧任务只记 `legacy-not-required`，未完成任务需要新规则时必须 supersede 并重新签发 |
| 成员历史分支与 main 正常分叉时可能被要求反复追赶看板提交 | 保留任务快照和授权 main 基线校验；仅在协调者核验精确 SHA 后允许一次普通合并，不因无关状态快照循环同步 |

### 18.13 V1.7.6 到 V1.8.4 的新增规则

| V1.7.6 状态 | V1.8.4 调整 |
| --- | --- |
| 任务只要求最低 Member Skill 版本，可能误用更高版或同版不同构建 | Gate 合并和基线冻结后执行 `prepare-skill-release → confirm-skill-release`；新任务精确绑定名称、版本、`build_id`、包路径、协议和发行 commit |
| 成员是否接单只能从拉取或开始产出间接推断 | Member V1.8.1 新增 `accept-assignment`；成员在登记分支 push 任务哈希、契约哈希、身份、分支和 Skill 构建绑定的接受凭证，协调端从精确远端 ref 投影 |
| 拉取、通知与接单语义容易混淆 | 明确 clone、fetch、pull、Issue、钉钉和 AI 推断都不构成接受；接受的 `gate_effect` 为 `none`，V1.8.0 及更早任务不追溯补签 |
| 成员独立工作没有统一的 AI 对话收敛证据 | A00 新增默认 `required` 的 `ai_dialogue_collaboration`；任务自动继承并生成 `ai-dialogue-summary.yaml`，AI 推断与成员确认分开 |
| 协调端可能使用成员分支最新 HEAD 回溯校验历史任务 | 每个任务解析其提交目录最后变更的精确 commit，并要求该 commit 仍可从登记分支 head 到达；分支改写或不可达时判定无效 |
| Gate 材料偏向机器产物和 YAML，线下人类评审理解成本高 | 新增固定结构的 `gate-review-pack.md`，按 `init → 撰写 → validate → prepare` 形成，绑定正文哈希、来源指纹、来源 commit、对比版本和冻结分支头 |
| Gate 评审后材料变化可能继续沿用旧批准 | 候选产物、参与成员、来源台账、决策记录、评审正文、对比版本或分支头任一变化都使材料 `stale`；实际审核版本在强制合并后进入冻结基线 |
| GitHub Issue 可能被误用为流程事实 | Issue 仅作为可选提醒投影，不得成为任务、接受、提交、确认、Gate、合并或基线输入 |

该阶段参考发行组合：Coordinator V1.8.4 + Member V1.8.1，协议 1.0，项目 schema 1.5。

### 18.14 V2.0 到 V2.1 的新增规则

| V2.0 状态 | V2.1 调整 |
| --- | --- |
| Member A—C 与 D—E 能力以不同版本包目录交付，安装和版本选择容易混淆 | Member V2.1.0 改为统一发行包，同时自包含 `predevelopment`、`development_delivery` 和 `legacy_predevelopment` 三个运行时 |
| 包版本、CLI 版本和任务要求可能被当作同一个版本 | 引入包身份与任务运行时身份双层模型；包版本允许与运行时版本不同，任务始终按唯一运行时执行 |
| A—C Coordinator 只能按扁平 Member manifest 发现稳定版本 | Coordinator 预开发运行时升级到 V1.8.5，从 `runtime_releases.predevelopment` 发现并确认统一 Member 包 |
| A—C 任务只表达精确 Skill 运行时和部分发行路径 | 新任务同时绑定运行时 profile/版本/build 与包版本/build/路径/发行 commit，成员在全链路重复核对 |
| D—E 包来源主要依靠安装目录约定 | 明确当前 D—E 合同仍只绑定运行时身份，包 provenance 由 runtime lock 与包 manifest 交叉验证；限制必须可见 |
| 仓库有脚本但缺少统一安装态事实 | 新增 `.github/sop-runtime-lock.json`，绑定入口路径、版本、build、来源和 SHA-256 |
| 系统代码存在可能被误认为项目已经初始化 | 新增 `bootstrap/active` 生命周期，bootstrap 不包含项目事实，副作用 capability 默认关闭 |
| 看板、通知、清理工作流可能被直接复制启用 | 工作流必须经过 lifecycle/capability guard、最小权限、Secrets 隔离、负向测试和受审 PR 才能激活 |
| 早期版本曾描述登记分支 push 触发状态回流 | 当前仓库未提供 `sop-member-signal.yml` 与 `sop-member-feedback.yml`，`remote_feedback` 必须为 `false`；改用协调者显式刷新，计划任务仅兜底 |
| 旧 Skill 目录长期堆积或被直接删除 | 根目录只保留被 pin 的最新稳定包；历史由 annotated tag、Git 历史和永久清理审计保留，清理只提 PR 不自动合并 |
| 使用者需要从大量规则中自行推断首次操作 | 新增第一次使用和系统完整使用指南，明确“提醒不等于分发、批准不等于合并、合并不等于发布” |

V2.1 对应参考发行组合为：Coordinator 包 V2.1.1（A—C 运行时 V1.8.5、D—E 运行时 V2.0.0）+ Member 包 V2.1.0（A—C V1.8.1、D—E V2.0.0、历史兼容 V1.8.0），协议 1.0；A—C 项目 schema 1.5，D—E 项目 schema 2.0。

同步边界：上述两个 V2.1 发行包的 manifest 在当前来源 commit 中仍把 `source_sop` 标为 `AI协同软件开发统一SOP_V2.0.md`。本文件是依据实际 V2.1 manifest、运行时、脚本、测试、runtime lock 和使用指南形成的对应同步草案，不追溯改写已发布包。下一次 Skill 发版必须把 `source_sop` 更新到经团队批准的本文件版本，并重新执行包校验；在此之前，以精确来源 commit 和 manifest 的机械身份为安装事实，不得伪称旧包已重新发布。

## 19. G3 向开发交付的正式交接

G3 人工通过后，仍须完成原 A—C 门禁：全部审核冻结的有效成员证据分支合并到 `main`，每个 `expected_head` 通过祖先关系验证，G3 基线冻结，并确认下一阶段 Member 发行包身份、D—E 唯一运行时身份和 runtime lock 来源。只有项目状态为 `development-entry-approved` 才能签发真实代码任务。

D0 固定以下输入：

- G3 基线版本与精确 commit。
- 已批准的需求、P0 验收、最终产品技术方案和测试矩阵。
- 原型结论、生产化差距和不得直接复用的原型边界。
- 项目、产品、技术、测试、发布和专项风险人类责任人。
- 目标代码仓库、目标 `main`、分支保护、必需 CI 和合并策略。
- 稳定 Member 发行包身份、D—E 唯一运行时 `2.0.0 / member-dev-cli-2.0.0-v1`、runtime lock 来源和发行 commit。
- 灰度、监控、停止和回滚草案。

缺少关键输入时创建准备任务，不用宽泛开发任务吸收缺口。D0 只校验 G3 交接，不重复批准 G3。

## 20. 阶段 D：正式开发

V2.1 发行包随附 D—E V2.0 运行时，但仓库默认 `development_de: false`，runtime lock 中两个开发运行时默认 `enabled: false`。只有真实 G3 已完整通过、审核证据已进入可信 `main`、G3 commit 是当前主干祖先，并且“缺少 G3、伪造 G3、非 main 祖先均失败”的负向测试通过后，才能在受审提交中启用开发能力。

### 20.1 开发任务录入与确认

每个开发任务必须足够小，由一名主责完成并由至少一名非作者独立审查。任务除第 6.9 节通用字段外，还必须包含：

```yaml
task_id: DEV-001
baseline_ref: G3-V1.0@<commit>
requirement_refs: []
acceptance_refs: []
primary_owner: member-...
reviewers: []
risk_owners: []
risk_level: R0 | R1 | R2 | R3
allowed_scope: []
forbidden_scope: []
expected_files: []
test_requirements: []
evidence_branch: sop/member/<member-id>
working_branch: feat/DEV-001-<slug>
target_branch: main
base_commit: <exact-main-sha>
required_checks: []
stop_condition: ""
rollback_considerations: ""
```

当前 D—E 开发任务的 `required_member_skill` 必须精确写入 `name: ai-sop-member`、`version: 2.0.0` 和 `build_id: member-dev-cli-2.0.0-v1`。包级来源由启用开发能力时已经审核的 runtime lock 指向 Member V2.1.0 统一包；在合同升级前，任务内不得虚构 `package_path`、`package_build_id` 或 `release_commit`。

一个任务只解决一个清晰目标或一组强耦合目标。数据模型、公共接口、前端交互、后台能力和测试可以独立时分别拆分。前置依赖未进入 `main` 时，后继任务不得标记 `ready`。每条 P0 验收必须关联至少一个实现任务和测试项。

首次创建仍只生成预览；当前用户确认预览 Token 后才分发。已分发任务不得原地扩大范围，使用新 `assignment_version` 或替代任务。

### 20.2 成员接受与实施计划

V1.8.1+ 的显式接受原则继续适用。成员必须在任务登记的精确 ref 生成并 push 接受凭证；`clone`、`fetch`、`pull`、打开任务、Issue 或消息通知都不等于接受。

开始编码前提交实施计划，列出变更文件、核心逻辑、数据读写、错误处理、权限检查、测试和质量命令。环境、权限、依赖或输入不完整时标记 `blocked` 并创建准备任务，不重复盲目尝试。

### 20.3 测试先行与正式实现

行为变化前先建立测试或测试矩阵，覆盖成功、失败、权限拒绝、边界、数据一致性，以及适用的并发、幂等、重试和兼容场景。禁止删除测试、弱化断言、跳过权限或吞掉异常以使检查通过。

实现只允许修改任务 `allowed_scope` 内的真实目标代码，采用符合现有架构的最小变更。公共 API、数据库、权限、隐私、订单、支付、上传、生产配置和密钥相关操作必须按风险等级升级。原型代码不得未经审查直接作为生产实现。

### 20.4 开发提交确认

开发任务保留“成员提交确认”但改变绑定对象：确认必须同时绑定精确实现 commit 和完成报告哈希，而不是仅绑定 `main-output.md`。

```yaml
development_submission_confirmation:
  task_id: DEV-001
  assignment_version: "1.0"
  member_id: member-...
  human_owner: <registered-owner>
  implementation_commit: <sha>
  completion_report_hash: sha256:<hash>
  personal_stance: confirm | oppose | question | reserve
  authority_scope: development-contribution-submission-only
  gate_effect: none
```

AI 不得代替 owner 选择立场或确认。实现 commit、完成报告、任务版本或受保护字段变化后，旧确认立即 stale。该确认不构成代码审查、PR 合并、G4、生产操作或 G5 批准。

### 20.5 代码审查与返工

开发主责不得成为唯一审查人。审查必须绑定任务版本和精确 commit，并检查验收、范围、异常、认证授权、数据、迁移、并发、幂等、兼容、日志、敏感信息、性能、测试和回滚。

- `P0`：必须修复，禁止合并。
- `P1`：原则上合并前修复；延期必须有责任人、影响和期限。
- `P2`：可选优化，不阻塞当前交付。

提交变化后重新验证受影响结论。返工使用新 commit，不改写已归档审查事实。同一问题连续两轮无实质进展时执行第 24 节熔断。

### 20.6 集成与任务关闭

代码审查通过只产生“允许合并该任务精确 commit”的权限。必须通过受保护 PR 和必需 CI 合并到 `main`，再验证该 commit 是 `main` 的祖先并运行受影响的集成测试。

开发任务仅在验收、范围、必需检查、P0/P1、专项审查、文档、迁移说明、风险记录及 main 可达性全部满足后关闭。单任务关闭不等于允许发布。

## 21. 阶段 E：发布交付

来源仓库当前 `docs/development-sop.md` 仍沿用开发分册的连续旧编号。统一生命周期按以下方式解释，不新增或重复执行步骤：

| 开发分册旧编号 | 本统一 SOP | 含义 |
| --- | --- | --- |
| D8 | E0 / G4 | 发布准入 |
| D9 | E1—E2 | 灰度、监控、停止、回滚与事故处置 |
| D10 | E3 / G5 | 交付关闭与基线冻结 |

项目状态目录继续使用 `04-development` 和 `05-release`。不得因为旧分册编号带 `D`，把 G4、灰度或 G5 误记入正式开发阶段，也不得将同一 Gate 执行两次。

### 21.1 G4 发布准入

所有发布范围任务已集成后，协调者生成面向人类的发布准入包，绑定发布候选 commit、任务清单、P0 验收、CI、系统测试、迁移、配置、监控、灰度、停止、回滚、未决问题和责任人。

G4 只允许 `pass`、`conditional-pass` 或 `reject`。权限、隐私、数据一致性、不可回滚问题和未关闭 P0 不得条件放行。G4 不执行“全体成员分支再合并”；它验证发布范围内所有已批准任务 commit 已在 `main` 可达。通过后才允许按批准方案灰度。

当前 Coordinator D—E V2.0 CLI 只机械实现 `prepare-g4` 和通过型 `approve-g4`，尚无与 A—C Gate 等价的 `reject` 或 `conditional-pass` 记录命令。人工结论为条件通过或退回时，必须保存在受审决定文件中并停止调用通过命令；不得把手工记录伪称为 CLI 已执行。后续升级 CLI 时必须保持本节三类政策结论和人类批准权不变。

### 21.2 灰度、监控、停止和回滚

灰度比例按项目风险确定，每次扩量前必须完成上一批观察。至少监控错误率、延迟、资源、数据库、队列、异常日志、核心业务完成率和用户反馈。

核心流程、数据一致性、权限、隐私、专项安全或无法解释的指标异常触发停止。优先关闭 Feature Flag，再按批准顺序回滚前端、后端和数据库。数据库回滚和数据修复只能由授权人批准并执行。

### 21.3 事故处理

生产事故必须记录影响、时间线、证据、止血、回滚、修复、验证、沟通和恢复。涉及数据修复、隐私暴露、客户沟通或不可逆操作时暂停自动推进，进入专项人工决定。

当前 D—E V2.0 CLI 尚无独立的事故开启、更新和关闭命令。事故台账、授权决定和关闭证据必须作为受审事实文件维护；看板或 `open_incidents` 数字不能替代事故记录，也不得因为缺少专用命令而跳过事故闭环。

### 21.4 G5 交付关闭

观察期结束后，G5 审核生产验证、指标、事故、遗留项、文档和复盘改进。存在未关闭 P0/P1 事故、数据修复未完成或风险责任人保留意见时，状态保持 `released` 或 `verifying`，不得标记 `closed`。

G5 通过后冻结发布基线，记录发布 commit/tag、实际配置、迁移版本、观察结论、遗留任务和复盘责任。G5 不代替生产发布授权；它确认本次交付可以关闭。

## 22. Git 分支与合并模型

预开发证据分支和开发代码分支必须分开：

```text
main                              # 受保护主干
sop/member/<member-id>            # A—C 成员证据
feat/<DEV-ID>-<slug>              # 新功能
fix/<DEV-ID>-<slug>               # 普通缺陷
hotfix/<INC-ID>-<slug>            # 生产紧急修复
```

G1—G3 延续“审核全部有效证据分支 commit → merge-pending → 合并 main → 祖先验证”。D 阶段每项代码任务只合并经独立审查和 CI 批准的工作分支精确 commit。G4/G5 审核集成和发布事实，不机械合并所有成员分支。

禁止直接 push `main`、绕过 PR/CI、审核后强推或用复制文件代替 Git 合并。详细命名、同步、PR、冲突和权限规则见 [Git 协作规范](docs/gitcode.md)。

## 23. 开发到发布的追踪和状态投影

完整追踪链扩展为：

```text
SRC → 用户故事 → REQ → AC → TECH → DEV
→ 实施计划 → commit → PR / Review → TEST / CI
→ main 集成 commit → REL → 灰度批次 → 生产验证
→ INC / 遗留任务 → POST 复盘改进
```

`P → SB → commit → SRC` 继续用于需求、设计、完成报告、评审包和发布说明等文档内容。生产代码使用任务 ID、变更文件清单、精确 commit、PR、审查和测试证据追踪，不要求逐代码块添加 `P`。

`project-state.yaml` 增加 `development_tracking`、`quality_tracking` 和 `release_tracking`，但仍是只读投影。开发成员只更新自己的分支、任务证据和代码，不直接写中央状态。

## 24. 阻塞熔断和变更控制

阻塞项至少记录类型、来源、责任人、前提、关闭证据、尝试次数、最后结果和剩余差距。一轮没有关闭任何 P0，或同一阻塞连续两次得到相同结果时，不得自动重复签发；新任务必须说明变化的前提、方法、责任或证据标准。

开发中发现新增产品范围时回流 A04；改变已冻结功能方案时回流 B；改变技术实现但不改变产品与验收时在 C/D 形成新决定和任务版本；改变发布范围、迁移、权限或风险条件时重新准备 G4。事故修复不得静默扩大原任务。

## 25. 系统安装、激活与日常运行

### 25.1 安装个人 Skill

个人 Codex Skill 用于指导角色行为，仓库 `.github/scripts/` 入口用于机械校验和落盘，两者不能互相替代。首次安装时目标目录必须尚不存在：

```powershell
# 协调者机器
Copy-Item `
  ".\ai-sop-coordinator-skill-v2.1.1\ai-sop-coordinator" `
  "$env:USERPROFILE\.codex\skills\ai-sop-coordinator" `
  -Recurse -Force

# 成员机器
Copy-Item `
  ".\ai-sop-member-skill-v2.1.0\ai-sop-member" `
  "$env:USERPROFILE\.codex\skills\ai-sop-member" `
  -Recurse -Force
```

升级时不得把新旧目录混合覆盖。应按团队升级流程先备份或移走旧 Skill，再完整安装新目录，并检查以下入口：

```text
%USERPROFILE%\.codex\skills\ai-sop-coordinator\SKILL.md
%USERPROFILE%\.codex\skills\ai-sop-member\SKILL.md
```

安装后重新打开 Codex 会话并确认实际加载的角色 Skill。个人安装完成不代表任务版本自动匹配；任务运行前仍须按第 15.1 节核对 runtime、build、包身份、来源 commit 和 runtime lock。

### 25.2 Bootstrap 仓库不是空项目故障

正式系统仓库可以只包含两套最新稳定发行包、`.github/scripts/`、运行时锁、系统校验和未激活模板，而没有 `sop/`、`dashboard/` 或真实项目代码。此时生命周期必须是 `bootstrap`，不得创建虚假成员、示例任务、空 Gate 或伪造基线来“让看板有内容”。

在 bootstrap 状态：

- 只读 `sop-system-validate.yml` 可以运行。
- 看板、通知、操作台、远端反馈、D—E 和自动清理的副作用 job 必须关闭或由 guard 成功 no-op。
- 示例成员、测试手机号、通知模板和回归夹具不得进入未来项目事实。

### 25.3 激活项目必须走受保护 PR

协调者从最新可信 `main` 创建独立初始化分支，并按以下最小顺序执行：

1. 运行 `python .github/scripts/sop_system_validate.py`，确认 bootstrap 安装态完整。
2. 使用真实必填参数运行 `init-project`，明确项目、协调者、全新需求输入、执行模式、协作模型、Gate 策略、风险、真实开发状态、成员、owner、成员分支和 G1—G3 责任能力。
3. 运行 `status`，确认生成内容只含当前项目事实。
4. 补齐 Gate accountability、真实代码来源的精确 commit、`dashboard-policy.yaml` 和 `notification-config.yaml`。
5. 项目管理员在 GitHub 外部设置 Environment、Secrets、Actions 权限和主干保护；Secret 不进入 commit 或 PR。
6. 只复制准备实际启用的加固工作流，使 lifecycle、capability、runtime lock 和工作流彼此一致。
7. 运行系统校验及相应负向测试。
8. 在同一个完整受审 PR 中切换为 `active`，通过保护规则合入 `main`。
9. 从最新可信 `main` 为每名成员创建并 push 唯一登记分支；已存在分支不得强推或静默复用。

完整逐命令说明见来源 commit 固定的 [第一次使用](https://github.com/xuhao666-pro/test/blob/462ff3141cefafa2b9c6602381bd4d231a364b35/docs/getting-started.md)、[系统完整使用说明](https://github.com/xuhao666-pro/test/blob/462ff3141cefafa2b9c6602381bd4d231a364b35/docs/system-usage-guide.md) 和 [Bootstrap 说明](https://github.com/xuhao666-pro/test/blob/462ff3141cefafa2b9c6602381bd4d231a364b35/.github/SOP-BOOTSTRAP.md)。

### 25.4 系统校验是安装态门禁

以下命令是每次系统发行、激活和清理前的基础门禁：

```powershell
python .github/scripts/sop_system_validate.py
```

校验至少覆盖：

- lifecycle 与 capability 一致性。
- 两套发行包 manifest、frontmatter、目录和 build 身份。
- runtime lock 的路径、来源、版本、build 和 SHA-256。
- Python 入口可编译，回归测试通过。
- 清理保留策略与审计链完整。
- 仓库未包含真实 webhook、token、手机号、密码或其他生产凭据。
- 校验后没有产生意外 tracked/untracked 变化。

系统校验成功只证明安装态一致，不等于任务完成、成员接受、Gate 通过、代码合并或生产授权。

### 25.5 远端反馈的当前限制

当前标准仓库尚未提供完整的 `sop-member-signal` 与可信处理器反馈链，因此 `remote_feedback` 必须保持 `false`。正确流程为：

```text
成员 push 登记分支
  -> 协调者显式 refresh-project-state --fetch --validate-remote
  -> 可信 main 脚本重新抓取并校验精确 ref
  -> 中央状态与看板投影更新
```

定时看板刷新只是兜底，不能承诺“成员 push 后立即自动收轮”。未来反馈链必须让成员分支只发送只读信号，由可信 `main` 处理器重新抓取；带写权限和 Secrets 的 job 不得执行成员分支脚本。

### 25.6 Skill 保留与自动清理

仓库根目录默认只保留被 pin 的最新稳定 Coordinator 和 Member 包。当前保留：

- `ai-sop-coordinator-skill-v2.1.1`
- `ai-sop-member-skill-v2.1.0`

历史发行通过 annotated Git tag、完整 Git 历史和 `.github/skill-cleanup/history/` 永久审计保留。自动清理必须遵循：

1. 读取运行时锁和引用根，拒绝删除仍被任务、基线或 lock 引用的包。
2. 先生成只读 plan；无候选时不制造提交。
3. 有候选时只创建或更新清理分支与 PR。
4. 在 PR 中重新运行系统校验和全部相关回归。
5. 永不自动合并 `main`，不得删除 Git tag、审计历史或仍需兼容的运行时。

### 25.7 每日角色入口

- 协调者先同步可信 `main`，运行系统校验、远端状态刷新和 `status`，再决定收轮、催办或 Gate。
- 成员先选择任务精确运行时，校验工作区和 assignment，显式接受后才初始化和产出。
- human owner 只确认精确正文或完成报告及个人立场，不替代 Gate。
- Gate 责任人只对绑定当前事实的评审包作决定，不用聊天表态或沉默代替。
- 代码审查人只审查精确 commit，新 commit 必须重新评估。
- 发布与事故责任人保留生产、回滚、数据修复和客户沟通的最终授权。

全员必须理解：

```text
提醒不等于分发
拉取不等于接受
接受不等于提交
提交有效不等于赞同
确认不等于 Gate
批准不等于合并
合并不等于发布
生产、数据、密钥和回滚必须找授权人
```

### 25.8 快速命令路由

| 用途 | 受信任入口 | 主要命令或资产 |
| --- | --- | --- |
| 系统校验 | `.github/scripts/sop_system_validate.py` | 直接运行，无项目副作用 |
| A—C 协调者 | `.github/scripts/sop_coordinator_cli.py` | `init-project`、任务/轮次、收轮、阶段、溯源、G1—G3、Skill 发行、`status`、`refresh-project-state` |
| A—C 成员 | `.github/scripts/sop_member_cli.py` | `workspace-check`、`inspect`、`accept-assignment`、`init`、内容索引、owner 确认、`validate`、`submit` |
| 历史 A—C 成员 | `.github/scripts/sop_member_cli_1_8_0.py` | 仅按既有 V1.8.0 任务合同运行 |
| D—E 协调者 | `.github/scripts/sop_development_cli.py` | `init-development`、`create-task`、review/integration、G4、rollout、G5、`status` |
| D—E 成员 | `.github/scripts/sop_member_development_cli.py` | 接受、初始化、检查记录、commit/报告确认、校验和提交 |
| README 看板 | `.github/scripts/sop_readme_dashboard.py` | 仅渲染中央状态投影 |
| Skill 清理 | `.github/scripts/sop_skill_cleanup.py` | 计划、清理分支和 PR；不自动合并 |
| 开发任务模板 | `ai-sop-coordinator-skill-v2.1.1/ai-sop-coordinator/assets/project-template/development-task-spec.json` | D—E `create-task` 双确认输入 |

各入口先运行 `python <entry> --help` 核对当前 commit 的真实参数。D—E 入口存在不等于已启用；`development_de` 和两个开发 runtime 未按第 20 节解锁前，只能查看帮助和执行明确允许的负向验证。

### 25.9 GitHub Actions 运维判断

- 工作流页面绿色只证明实际运行的 job 成功；带 capability guard 的副作用 job 为 `skipped` 时，不表示看板、通知、催办或清理已经执行。
- 判断副作用时依次检查 guard 是否为 `active`、副作用 job 是否实际成功、绑定的 `main` SHA 与 project revision、预期 commit/Issue/消息是否真实产生，最后回到权威事实文件和精确 commit。
- 操作台只能从最新可信 `main` 新开运行。出现 `stale-main-sha` 或 `stale-project-revision` 时不得 rerun 旧运行，必须回到最新 `main` 新建操作。
- 出现 `actor-not-authorized` 时，核对 `sop/dashboard-policy.yaml` 中登记的是触发者精确 GitHub login，不得用昵称或 member ID 代替。
- 看板 bot 被主干保护拒绝时，不得关闭必要保护；只能经审核允许受控 bot 更新投影文件，或改用受审 PR/人工中央快照。
- `notification-test` 成功不证明成员 `@` 映射正确；真实任务映射还须核对 member ID、配置键、Environment、webhook/secret 同源和 UTF-8 编码。
- Actions、Issue、钉钉或看板失败只影响自动化与展示，不改变 assignment、acceptance、submission、Gate、合并、基线、发布或事故事实。

## 26. V2.1 完成标准

除第 17 节 A—C 完成条件外，完整交付还必须满足：

- 每项开发任务绑定 G3 基线、REQ/AC、精确 Skill、主责、审查人、风险责任和工作分支。
- 未接受任务的成员没有开始真实实现。
- 每项开发提交均绑定精确实现 commit、完成报告哈希和 owner 个人立场。
- 必需测试和 CI 已执行，未运行项如实记录。
- 非作者独立代码审查和专项审查满足要求。
- 所有发布范围 commit 已进入 `main` 并通过祖先关系验证。
- G4 使用绑定发布候选和来源的人工可读材料批准灰度。
- 灰度、监控、停止和回滚证据完整。
- 生产事故和数据修复没有被状态投影掩盖。
- G5 在观察期结束后由真实责任人确认并冻结发布基线。
- 需求、任务、代码、测试、发布和事故可以双向追踪。
- 安装态已经区分发行包身份与任务运行时身份，所有任务选择唯一 profile，且 runtime lock 与来源包、协议和 CLI 哈希一致。
- 项目由真实输入从 `bootstrap` 通过完整受审 PR 激活；未配置能力保持关闭，没有用测试夹具或旧项目事实补全新项目。
- D—E 只有在真实 G3、可信 main 祖先验证和负向门禁通过后启用；当前包 provenance、G4 结论命令和事故 CLI 限制均保持可见。
- 看板、通知、操作台、远端刷新和自动清理均未越过任务、成员确认、Gate、合并或生产授权链。
