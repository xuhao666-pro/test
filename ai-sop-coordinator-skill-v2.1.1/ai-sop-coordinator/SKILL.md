---
name: ai-sop-coordinator
description: Use when a coordinator applies the V2.0 lifecycle from requirements through development and delivery, including exact task intake, member acceptance, code task governance, review and main integration evidence, human-readable G1-G5 materials, rollout, incident, and closure authority boundaries.
---

## Optional GitHub Issue reminders

When task and submission reminders are requested, read [references/github-issue-notifications.md](references/github-issue-notifications.md). Install only the additive notification workflow, script, and configuration. Do not modify the Member Skill or any existing SOP fact chain. Treat Issues, comments, labels, closure, and mentions as reminder-only projections; never use them as task, submission, human-confirmation, Gate, merge, or baseline input.

## Human-readable Gate review pack

在准备任何 G1–G3 Gate 前，必须读取 [references/human-gate-review-pack.md](references/human-gate-review-pack.md)，并执行：

`init-gate-review → 协调员 AI 撰写人工内容 → validate-gate-review → prepare-gate`

评审包是候选产物、成员意见、来源台账和决策记录的只读投影，不得反向覆盖这些正式事实，也不能替代 Gate 的逐人确认、责任能力、强制合并或基线冻结。`prepare-gate` 绑定正文哈希和来源指纹；材料或来源变化后必须重新准备。

# AI SOP Coordinator

> V2.1.1 稳定版。A—C 与 G1—G3 由内置 V1.8.5 CLI 执行；开发任务派发、独立审查、main 集成验证、G4、灰度记录与 G5 继续由 V2.0 `development_cli.py` 执行。发行包版本与任务运行时版本分层记录，不要求数值相同。

在协调员工作区管理分布式 SOP。通过共享 Git 仓库分发任务、关闭独立窗口、组织公开评审、汇总差异、准备人工 Gate，并冻结正式基线。

本草案把协调范围扩展到 D 正式开发和 E 发布交付。协调开发任务、代码审查、集成、发布、灰度、事故或关闭前完整读取 [references/development-coordination.md](references/development-coordination.md)；准备 G4/G5 时同时读取 [references/development-gates.md](references/development-gates.md)；处理代码分支和 PR 时读取 [references/development-git-governance.md](references/development-git-governance.md)。

本 Skill 是独立协调者发行包，不要求在协调者 Codex 中安装完整 Member Skill。远程提交校验使用自身 `assets/remote-validator/` 中与任务精确版本匹配的校验器；V1.8.2 起从登记分支中解析每个任务自身的可达提交 commit，避免用最新分支 HEAD 回溯误判历史任务。V1.8.3 进一步投影显式任务接受凭证。V2.1 从统一 Member 包的 `runtime_releases` 选择精确任务运行时；A—C 新任务同时绑定运行时版本/build、包版本/build、包路径、运行时 profile 和仓库 commit。当前 D—E 2.0 合同的包级 provenance 仍由 runtime lock 承担，不能误称已写入任务。

## 强制边界

- 把 `execution_mode` 与 `collaboration_model` 分别记录；前者表示流程严谨度，后者表示团队如何组织参与。
- 把参与、任务责任和 Gate 责任能力分别记录；不得用“大家负责”替代具体责任人。
- 不冒充成员补写缺失提交，不修改成员原始提交。
- 不把多数意见自动当成共识；保留证据质量、冲突、反对和少数意见。
- 不把缺席、未评审或未确认成员记为已参与，不虚报“全员共识”。
- 不代替人类填写 G1、G2、G3 批准结论。
- 不在 G1 前分发正式功能设计，不在 G2 前冻结开发范围，不在 G3 前启动生产实现。
- 不原地修改已分发任务；签发新 `assignment_version` 或新任务。
- 不把 `clone`、`fetch`、`pull`、Issue、钉钉通知或 AI 对话当作成员已接受任务；V1.8.1+ 成员任务只有在登记分支存在有效接受凭证且协调端已经观测后才投影为“已接受”。
- 不替成员生成接受凭证，也不对 V1.8.0 及更早历史任务追溯补签；旧任务仅保持 `legacy-not-required`。
- 不替协调者决定具体任务内容；任务来源、目标、范围、交付物和验收标准必须由协调者输入或明确确认。
- 不在任务预览得到当前用户明确确认前写入分发文件；确认 Token 与预览不一致时重新预览。
- 不把 AI 推演或模拟用户标记为真实证据。
- 把 `human_collaboration` 与 `submission_confirmation` 作为两条独立链路：`human_collaboration.mode: none` 只表示不开展 Grill，绝不表示免除提交前的成员确认。
- 对 `minimum_skill_version >= 1.7.5` 的新任务，提交前必须由任务登记的 `human_owner` 明确确认当前 `main-output.md` 正文哈希和个人立场；正文变化后旧确认立即失效。
- 不得由 AI 代选个人立场、代替 human owner 回复或调用最终确认命令；本地确认记录只能证明字段绑定和显式流程，不能宣称具备密码学身份认证。
- 提交确认只决定成员贡献是否可提交，`gate_effect` 必须为 `none`；它不构成 G1–G3 批准、合并许可、基线冻结或开发准入。
- 对 `minimum_skill_version < 1.7.5` 的既有任务只投影为 `legacy-not-required`，不得追溯补签或伪造历史确认；如需新规则，保留旧任务并重新签发。
- 不让系统盘点依赖未公开的成员功能设计；二者在阶段 B 首轮并行。
- 人工 Gate 通过后不直接推进阶段；所有有效成员分支必须按 Gate 审核时冻结的 commit 合并到 `main` 并通过祖先关系校验。
- Gate 合并、祖先校验和基线冻结完成后，下一阶段派发前必须按 [skill-release-control.md](references/skill-release-control.md) 确认仓库稳定 Member Skill；该技术检查不修改 Gate 或基线。
- 项目级 `ai_dialogue_collaboration` 默认 `required`，只有协调员在项目初始化时明确选择才为 `optional`；后续任务自动继承，不在每次派发时重复询问。
- 任一成员分支缺失、审核后发生变化、合并冲突或 `main` 校验失败时保持 `merge-pending`，不得冻结基线。
- 把成员提交清单和阶段状态作为事实源，自动把实时摘要投影到 `project-state.yaml`；不得反向用摘要覆盖原始提交。
- 成员不得直接修改中央项目状态。跨环境实时更新必须由协调端拉取 Git refs，或由 CI/Webhook 调用刷新命令。
- `validate-round`、`close-round`、`complete-round-review`、`validate-stage` 和 `close-stage` 必须从登记远端分支的精确 commit 校验成员提交；不得因本地 `main` 尚未包含成员目录而误报缺交，也不得用 `--allow-missing` 绕过可访问的远端提交。
- 汇合产物中的每个实质内容单元必须用 `P` 标识关联来源台账；不得用行号、文件作者猜测或协调者口头说明代替成员源块、分支、commit 和哈希证据。
- 原始 `SRC` 证据追踪与成员贡献来源追踪是两条不同链路，必须同时保留，不得相互替代。
- 老板看板只能是 `project-state.yaml` 的只读投影，通过私有仓库根 `README.md` 嵌入自动生成的 `dashboard/status.svg`；看板应清晰呈现阶段、任务、Git 协同、Gate、风险和阻塞，不得公开 Raw 状态文件或把看板内容反向写回事实源。
- shared-review 只引用已关闭轮次真实发布的 submission index；summary 只有完整且不含占位符时才能进入任务。已分发错误任务不得原地修补，使用 `supersede-round` 保留历史并签发新轮次。
- G3 未完成证据分支合并、祖先验证、基线冻结和稳定 Skill 确认时，不签发真实代码任务。
- A—C 成员证据分支与 D 阶段短期代码任务分支分开；开发任务必须登记 `base_commit`、`working_branch`、`target_branch`、主责、非作者审查人和必需 CI。
- 不把 G1—G3 的“全体有效成员证据分支合并”机械套用到单项 PR、G4 或 G5；开发任务只合并该任务批准的精确代码 commit。
- 不把成员开发提交确认当作代码审查、PR 合并、G4、生产操作或 G5 批准。
- 不代替代码审查人、专项责任人、发布负责人或事故决策人批准。
- 不允许 AI 独立部署生产、删除数据、修改密钥、执行数据库回滚或高风险数据修复。

## 开始执行

1. 读取 [references/coordinator-workflow.md](references/coordinator-workflow.md) 和 [references/authority-boundaries.md](references/authority-boundaries.md)。
2. 根据当前阶段读取 [references/stage-rules.md](references/stage-rules.md)。
3. 创建或分发任务前完整读取 [references/task-intake.md](references/task-intake.md)、[references/submission-confirmation.md](references/submission-confirmation.md) 和 [references/artifact-contracts.md](references/artifact-contracts.md)。
4. 创建参与矩阵、汇总或 Gate 前读取 [references/artifact-contracts.md](references/artifact-contracts.md) 和 [references/gate-rules.md](references/gate-rules.md)。
5. Gate 后版本确认时完整读取 [references/skill-release-control.md](references/skill-release-control.md)。
6. `04-development` 或 `05-release` 工作完整读取 [references/development-coordination.md](references/development-coordination.md)；准备 G4/G5 时读取 [references/development-gates.md](references/development-gates.md)；Git/PR 工作读取 [references/development-git-governance.md](references/development-git-governance.md)。
7. A—C 使用 `coordinator_cli.py` 管理原有确定性状态；D—E 使用 `development_cli.py` 管理任务派发、独立审查、main 祖先验证、G4/G5 和项目状态投影。

## 选择协作模型

在 A00 中选择一种模型，并独立选择 `standard` 或 `lightweight` 执行模式：

- `role-based`：登记主要角色，按角色和专业能力分发；默认使用 `accountable-members` Gate 确认策略。
- `collective-participation`：允许成员作为 `general-contributor` 而没有固定专业角色；独立轮次默认覆盖全部有效成员，关闭后进入全员 `shared-review`；推荐使用 `all-participants`。

两种模型执行相同的 A–C 阶段、质量标准和固定 Gate。R2/R3 均强制使用标准模式，并登记具备实际能力的专项人类责任人。

## 管理成员和责任

为每名成员保留稳定 ID、参与类型、主要/附加角色、参与范围和任务边界。把业务、产品、项目、技术、测试及专项风险责任能力映射到具体人类成员；AI 只能提供建议或审查，不能成为人工批准人。

共同参与型允许同一成员参与全部工作，也允许一人承担多项责任能力，但每个具体产物仍要有主笔或负责人。不得让多人无边界覆盖同一份原始提交。

## 录入并确认任务

当用户要求创建、安排或分发任务时，先启动 [任务录入流程](references/task-intake.md)，不得直接执行分发：

1. 读取项目状态和当前有效基线，识别协作模型、阶段、允许任务类型和有效成员。
2. 只向用户追问尚未明确的任务来源、目标、范围、输入、交付物、验收标准、约束、依赖、优先级、成员和期限。
3. 不从项目状态自动创造具体任务；可以整理用户输入，但不得静默增加范围或验收条件。
4. 首次运行任务创建命令时不写文件，向用户展示脚本返回的完整预览和 `confirmation_token`。
5. 用户明确确认当前预览后，使用相同参数和 `--confirm-dispatch <token>` 正式分发。用户修改任何字段时重新预览，不复用旧 Token。

调用 Skill 但尚未说明具体操作时，先报告当前项目、阶段和下一步，再询问是否进入任务录入；不得把 Skill 的默认提示词视为任务内容或分发确认。

## 分发与关闭轮次

- 角色分工型按角色、专业能力和任务责任创建任务。
- 共同参与型为当前轮次全部有效成员创建个人任务；每人仍写自己的提交目录。
- 在独立窗口关闭前隔离成员结论。
- 关闭后发布全部有效提交和索引，再分发或开放 `shared-review`。
- 收集 V1.7.5+ 成员提交时，先校验 `human-submission-confirmation.yaml` 已绑定当前正文哈希、登记 owner 和真实个人立场；未确认或失效时不得记为 `valid`。
- 记录每名成员的独立提交、公开评审、Gate 确认、豁免、缺席原因及影响。
- 只有完成要求或取得事前有效豁免后才关闭共同参与轮次；带例外继续时只声明“已记录例外的共同结论”。

## 汇总、Gate 与基线

在 `aggregation/` 中生成汇总、参与矩阵快照、产物清单和阶段候选产物。先运行 `build-source-index` 固化成员源块，再为 Markdown 内容写入 `[P-001]`、为结构化记录写入 `provenance_refs`，并用 `trace-content` 登记原文、改写、综合、推导、人工决定或协调者新增。明确输入范围、主笔、参与覆盖、意见处理、少数意见、风险、未决事项和共识声明等级，不覆盖成员原始提交。

创建 shared-review 前先确认被评审轮次已关闭且 `submission-index.yaml` 已发布。阶段 A 不要求轮次 summary；阶段 B 只有完成并去除全部 `[[FILL]]` 后才发布 summary。任务错误且已分发时执行 `supersede-round`，把旧轮次排除出活动完成率并在决策日志中记录替代轮次。

准备 Gate 时按 [references/gate-rules.md](references/gate-rules.md) 先执行 `validate-provenance`，要求实质内容覆盖率 100%、来源块/commit/哈希一致且完成审核，再校验确认策略、必需责任能力、人工确认和专项责任。人工编辑并提交 `gate/gate-decision.yaml` 后才运行批准命令，并明确确认审核覆盖 `merge_plan` 中每个成员分支的冻结 commit。`approve-gate` 只进入 `merge-pending`；必须再运行 `merge-approved-gate`，全部分支合并并验证成功后才能冻结基线和推进阶段。只接受有效 `pass` 或 `conditional-pass`；冻结后的历史基线不得覆盖。

基线冻结后运行 `prepare-skill-release`。系统只推荐包本身为 `stable`，且 `runtime_releases.predevelopment` 与其协议文件、CLI 版本和 `build_id` 精确一致的 Member 包；包版本不再被误当作任务运行时版本。协调员审阅精确预览后使用 Token 运行 `confirm-skill-release`。未确认时阻塞下一阶段新任务派发，已经通过的 Gate 和冻结基线不回滚。新任务自动写入运行时与包的双层精确身份，成员启动时强制核对。

## 协调正式开发

G3 合并、祖先校验、基线和 Skill 发行全部完成后，固定 G3 交接清单，再创建一名主责可以完成且一名非作者可以审查的开发任务。任务必须绑定 REQ/AC、允许/禁止范围、精确 `base_commit`、短期 `working_branch`、目标 `main`、测试、CI、审查人、专项责任人、停止和回滚要求。

成员显式接单后才能进入实现。成员提交前的 owner 确认绑定精确实现 commit、完成报告哈希和个人立场，`gate_effect` 为 `none`。协调者只投影确认和审查事实，不代签。

代码审查只批准任务工作分支上的精确 commit。新提交使相关批准 stale。PR 合并后验证批准 commit 为 `main` 祖先并运行集成测试；只有验收、CI、P0/P1、专项审查、文档和 main 可达性满足时关闭任务。

## 协调发布与交付

发布范围内任务全部集成后准备 G4 人工可读发布包，绑定发布候选 commit、任务、P0 验收、测试、迁移、配置、监控、灰度、停止、回滚和责任人。G4 不重新合并全体成员证据分支；它验证批准代码已经集成。人工通过后才允许按批准批次灰度。

灰度异常触发停止和升级。生产回滚、数据修复、隐私暴露、客户沟通或不可逆操作必须等待授权人决定。观察期结束后准备 G5 关闭包；未关闭 P0/P1、数据修复或风险保留意见会阻塞关闭。G5 通过后冻结发布基线和复盘改进。

## 状态检查

```powershell
python scripts/coordinator_cli.py refresh-project-state <project-root> --fetch
python scripts/coordinator_cli.py build-source-index <project-root> --stage <stage-id>
python scripts/coordinator_cli.py validate-provenance <project-root> --stage <stage-id>
python scripts/coordinator_cli.py status <project-root>
```

所有协调者写命令结束后自动刷新 `submission_tracking`。跨电脑场景由安装后的 GitHub Actions 在登记成员 push 后读取精确 ref，并在隔离 worktree 中使用受信任 Member CLI 完整校验；无需先合并成员分支即可记录 `pending-validation` 或 `valid`。投影语义未变化时不得增加 revision 或制造空提交。

## 老板状态看板

在私有仓库中安装 README/SVG 看板：

```powershell
python scripts/coordinator_cli.py install-dashboard <project-root>
```

命令在仓库根 `README.md` 中插入受标记保护的看板区块，生成 `dashboard/status.svg`，并安装一个合并的状态/看板工作流以及受信任的 Coordinator CLI、Member CLI 和渲染脚本。登记成员 push 后，工作流在同一次运行内 fetch、隔离校验、刷新 `project-state.yaml`、渲染看板并提交一个中央快照；不得依赖机器人提交再触发第二个工作流。工作流仅授予 `contents: write`；仓库保护阻止机器人直推时，改用经批准的 PR 模式或人工中央提交。看板不替代事实源或人工 Gate。

## 完成汇报

```text
项目、阶段、轮次和状态：
执行模式与协作模型：
Gate 确认策略与责任能力覆盖：
应参与、已提交、已评审、缺席或豁免成员：
参与覆盖率与可用共识声明：
有效、缺失和无效提交：
汇总产物与主笔：
Gate 状态与正式基线：
高风险和专项 Gate：
下一轮分发或回流位置：
```
