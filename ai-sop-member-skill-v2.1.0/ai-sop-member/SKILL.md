---
name: ai-sop-member
description: Use when a registered member follows the V2.0 lifecycle across requirements, design, development, code review, release validation, or incident work while preserving exact assignment acceptance, scoped Git branches, test-first implementation, commit-bound human confirmation, and Gate authority boundaries.
---

# AI SOP Member

> V2.1.0 统一发行包。包身份是 `2.1.0 / member-package-2.1.0-unified-runtimes-v1`；任务运行时身份仍分别是 1.8.0、1.8.1 和 2.0.0。不得把包版本当作任务要求的 Skill 版本。

在成员自己的工作区执行一个版本化任务包，并把结果写入该成员专属提交目录。

本 Skill 是独立成员发行包，不包含协调者命令、中央状态写入、汇总、Gate 或看板能力。成员只需安装本包；任务包由使用匹配协议版本的协调者通过 Git 分发。

本发行包覆盖 D 正式开发和 E 发布交付。执行代码、代码审查、发布验证或事故任务前完整读取 [references/development-delivery.md](references/development-delivery.md)；涉及 Git 分支与合并时同时读取 [references/development-git-rules.md](references/development-git-rules.md)。

## 发行包与运行时选择

本目录是一个发行包，内含三个保持原始身份不变的任务运行时：

- `predevelopment`：`member_cli.py`，精确身份 `1.8.1 / member-cli-1.8.1-assignment-acceptance-v1`，用于当前 A—C/G1—G3 任务。
- `development_delivery`：`development_cli.py`，精确身份 `2.0.0 / member-dev-cli-2.0.0-v1`，用于 D—E/G4—G5 任务。
- `legacy_predevelopment`：`member_cli_1_8_0.py`，精确身份 `1.8.0 / member-cli-1.8.0-ai-dialogue-exact-release-v1`，只用于已精确绑定该历史版本的兼容任务。

所有任务先读取 `required_member_skill.name`、`version` 和 `build_id`。A—C 任务还必须核对 `protocol_version`、`package_path` 和 `release_commit`；`package_path` 可以指向 `ai-sop-member-skill-v2.1.0`，但 CLI 仍必须与任务绑定的运行时版本和 build 完全一致。当前 D—E 2.0 任务合同只机械绑定运行时身份，包来源由仓库的 runtime lock 与本包 manifest 共同校验；不得为它伪造任务中没有的包字段。任务实际携带包字段时仍须逐项核对。找不到唯一匹配时停止，不尝试用包版本、较高版本或另一运行时替代。

## 强制边界

- 读取 A00 中的 `execution_mode`、`collaboration_model`、参与矩阵和自己的成员卡。
- 只读取任务包允许的基线、来源和已公开材料。
- 独立轮次不得读取其他成员的 `submissions/` 或分支；共同参与型同样适用。
- 只写 `submissions/<member-id>/<submission-id>/`，不覆盖其他成员或自己的历史提交。
- 对 V1.8.1+ 新任务，只能通过 `accept-assignment` 在自己的 `acceptances/<member-id>/` 目录生成任务绑定接受凭证；Git pull、Issue、钉钉送达或 AI 推断均不等于已接受。
- 不修改 `dispatch/`、`aggregation/`、`gate/`、`baseline/`、需求池、参与矩阵或项目状态。
- 不执行缺少已确认 `dispatch_confirmation`、任务契约字段或有效 `task_contract_hash` 的 V1.8.0+ 任务。
- V1.8.0+ 任务开始前必须精确匹配 `required_member_skill.version` 和 `build_id`；不得用更高版本、相同目录名或最低版本兼容性替代。
- 在读取任务正文或创建任何产物前，先按 [version-preflight.md](references/version-preflight.md) 从 `package-manifest.json.runtime_releases` 选择运行时，再比较对应协议资产。包身份与任务运行时身份不得混为一谈；不匹配时只输出结构化版本提醒和可验证的精确 CLI 路径，然后停止，不静默安装、升级、降级或覆盖全局 Skill。
- 仅在任务显式配置 `human_collaboration.mode: adaptive-grill` 时启动真实成员需求访谈；不得由 AI 自行开启、代答或伪造确认。
- `human_collaboration.mode: none` 仅表示不开展 Grill；它不免除提交前由登记 `human_owner` 确认最终 `main-output.md` 正文哈希和个人立场。
- 不代替 `human_owner` 选择个人立场或执行 `confirm-submission`。只有在当前会话中向该 owner 展示完整确认预览并取得明确回复后，才能记录确认。
- 最终提交确认只授权成员贡献提交，`gate_effect` 永远为 `none`；不得把它解释为 Gate、合并、基线、开发或发布批准。
- 不代表真实用户、其他成员或人工批准人。
- 发现新增需求时写入候选清单，不直接扩大本轮范围。
- 发现数据库、公共 API、权限、支付、隐私、生产配置或真实数据风险时标记 `gate_trigger: true`。
- 保持 `SRC → 用户故事 → REQ → DEC → AC → 功能设计 → FB → TECH → TASK → TEST` 追踪关系。
- 只在成员卡登记的 `git_branch` 工作；Gate 材料冻结 `expected_head` 后不得改写或追加该分支，变更必须退回并重新准备 Gate。
- 把 `submission-manifest.yaml` 作为实时状态事件，准确填写 `status`、`submitted_at`、数量和分支字段；只提交到成员分支，不直接更新中央 `project-state.yaml`。
- 把 `content-block-index.yaml` 与 `main-output.md` 一起提交；不得手工伪造块 ID、内容哈希、成员身份或 commit 来源。
- 在独立 clone 或 worktree 中工作；不得与协调员或其他成员共享同一工作树。开始任务前必须验证当前分支、远程成员分支和任务基线。
- 未取得 `development-entry-approved` 的 G3 冻结基线时，不修改真实目标代码。
- A—C 的 `sop/member/<member-id>` 证据分支与 D 阶段 `feat/fix/hotfix` 代码任务分支分开；只在任务登记的精确分支和 `base_commit` 工作。
- 代码修改只限 `allowed_scope`；超出范围或涉及公共 API、数据库、权限、隐私、订单、支付、上传、生产配置时停止并升级。
- 行为变化前先建立测试或测试矩阵；不得删除测试、弱化断言、跳过权限或吞掉错误使检查通过。
- 不直接 push `main`，不绕过 PR、独立审查或必需 CI，不把 PR 创建或分支存在解释为已集成。
- 不独立执行生产部署、数据删除、密钥修改、数据库回滚或高风险数据修复。

## 首次接入仓库

先从协调员取得私有仓库地址和成员卡登记的 `git_branch`，在独立目录执行：

```powershell
git clone <repository-url> <member-workspace>
cd <member-workspace>
git fetch origin --prune
git switch --track origin/<registered-member-branch>
git merge --ff-only origin/main
git branch --show-current
```

本地分支已存在时使用 `git switch <registered-member-branch>` 后再 fetch 和快进。`git merge --ff-only origin/main` 失败表示分支已分叉，停止并联系协调员，不自行 rebase、强制推送或改在 `main` 工作。

成员已有历史提交时，登记分支与 `main` 正常分叉，`--ff-only` 可能无法同步新任务。此时先停止；协调员核对双方精确 head、确认无冲突并明确授权后，成员可在自己的登记分支执行一次 `git merge --no-edit <coordinator-verified-main-sha>` 并正常 push。不得用可移动 ref 替代协调员已核验的 SHA，也不得在没有协调员授权时自行做非快进合并。任务快照进入成员分支后，后续仅修改看板或 `project-state.yaml` 投影的 `main` 提交无需反复追赶；Member CLI 会校验任务文件仍与远端已确认任务完全一致，且授权基线未偏离实际合入的 `main` 快照。

当协调员为不变的已确认任务发布兼容性修复时，必须同时给出仓库精确 commit 和 Member CLI `build_id`。成员应运行该 commit 中仓库自带的 Member CLI，并在 `workspace-check` 输出中核对 `member_cli.build_id`；不能只凭相同的 `SKILL_VERSION` 推断旧安装已包含补丁。

## 开始执行

1. 定位协调员分发的任务包。
2. 完整读取 [references/version-preflight.md](references/version-preflight.md)，核对任务要求的精确版本与当前 Skill；不匹配时提醒并停止，不继续加载任务执行流程。
3. 读取 [references/member-workflow.md](references/member-workflow.md) 和 [references/authority-boundaries.md](references/authority-boundaries.md)。
4. 根据 `stage_id` 和 `assignment_kind` 读取 [references/stage-rules.md](references/stage-rules.md)。
5. 创建或校验提交时读取 [references/artifact-contracts.md](references/artifact-contracts.md)。
6. 准备、记录或校验最终人工确认时完整读取 [references/submission-confirmation.md](references/submission-confirmation.md)。
7. V1.8.0+ 任务完整读取 [references/ai-dialogue-collaboration.md](references/ai-dialogue-collaboration.md)。
8. `stage_id` 为 `04-development` 或 `05-release` 时完整读取 [references/development-delivery.md](references/development-delivery.md)；需要创建、同步、审查或合并代码分支时再读取 [references/development-git-rules.md](references/development-git-rules.md)。
9. 当前 A—C 使用 `member_cli.py`，精确绑定 1.8.0 的历史 A—C 任务使用 `member_cli_1_8_0.py`；D—E 使用 `development_cli.py`。每个入口只检查自身运行时身份、任务接受和对应阶段契约，不混用版本资产。

```powershell
python scripts/member_cli.py workspace-check <assignment.yaml> --member-id <member-id> --fetch
python scripts/member_cli.py inspect <assignment.yaml> --member-id <member-id>
python scripts/member_cli.py accept-assignment <assignment.yaml> --member-id <member-id>
# commit 并 push 接受凭证后，协调端看板才显示“已接受”
python scripts/member_cli.py init <assignment.yaml> --member-id <member-id>
```

`workspace-check` 确认 Git 仓库、`origin`、登记分支、远程成员分支、协调员授权任务 commit 和实际合入的 `main` 基线快照；它不因任务分发后产生的无关看板快照要求循环合并最新 `origin/main`。`inspect` 同时验证任务与远端已确认文件完全一致、所有 `baseline_refs` 未被成员改动、路径位于项目内，且 summary/index 已完整发布；失败时不得 `init`。`init` 输出成员专属提交目录，只在该目录内完成工作。

V1.8.0+ 任务还会在任何产出创建前核对精确 Member Skill 版本与 `build_id`。V1.8.1+ 任务必须先生成并推送显式接受凭证；`init` 创建辅助 `ai-dialogue-summary.yaml`：`required` 必须完成，`optional` 可由成员明确跳过。该文件只记录结构化过程证据，不替代七类正式产物，也不产生 Gate 效果。

如果任务的 `human_collaboration.mode` 为 `adaptive-grill`，`init` 会同时创建 `human-collaboration-log.yaml` 和 `grill-summary.yaml`，并明确返回等待真实成员同意的下一动作。此时完整读取 [references/adaptive-grill.md](references/adaptive-grill.md)；维护两个中间文件时同时读取 [references/adaptive-grill-output-contracts.md](references/adaptive-grill-output-contracts.md)。先取得登记 `human_owner` 的同意，再每轮只问一个问题。访谈完成后将结果映射到正式来源、用户故事、需求、验收、风险和缺口；不得用两个 Grill 文件替代正式产物。

## 按任务阶段工作

### 独立轮次

无论采用哪种协作模型，都先独立工作：自行形成分析、设计或盘点，不读取他人未公开结论。共同参与型表示每名应参与成员都要提交，不表示从一开始共同编辑。

在独立产出内部按项目策略执行 AI 对话协同：任务理解与成员纠正、AI 初始思路地图、逐问逐答发散、阶段复述、替代方案/反例/风险/取舍比较、成员立场收敛，再映射到现有正式产物。AI 推断必须与成员确认结论分开。

需求分析须记录来源和证据属性，使用 `As a <角色>, I want <功能>, so that <价值>` 用户故事并关联 `SRC`。功能设计只使用指定 G1 基线，并逐项关联 `REQ/AC`。系统盘点默认只读，与功能设计并行。

### 公开共同评审

只在任务明确使用 `shared-review` 且独立窗口已关闭时读取协调员发布的全部有效提交、索引和汇总草案。逐项记录确认、反对、质询、保留意见和依据；不要修改任何原始提交，也不要把自己的意见表述为团队共识。

### 开发准备

在共同参与型中，可对技术、测试、风险和任务拆分提出完整建议；协调员或指定主笔形成候选 A08/A09 后，再按任务进行交叉评审。G3 通过前不开始正式生产实现。

## 提交

完成脚本生成的全部文件并删除所有 `[[FILL]]`，然后运行：

```powershell
python scripts/member_cli.py index-content <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
python scripts/member_cli.py prepare-confirmation <submission-dir> --assignment <assignment.yaml> --member-id <member-id> --position <confirm|oppose|question|reserve> --position-statement <成员原话>
# 向登记 human_owner 展示命令返回的完整预览，并等待其明确确认
python scripts/member_cli.py confirm-submission <submission-dir> --assignment <assignment.yaml> --member-id <member-id> --confirmed-by <human-owner> --document-hash <preview-hash> --confirmation-token <preview-token>
python scripts/member_cli.py validate <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
python scripts/member_cli.py submit <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
```

`index-content` 可在编写过程中显式刷新索引。正文及正式产物完成后运行 `prepare-confirmation`，它重建索引并生成绑定正文哈希、个人立场和 owner 的只读预览，但不会代替人类确认。取得登记 owner 对当前预览的明确回复后才能运行 `confirm-submission`。`submit` 会再次重建索引；正文变化、owner/任务/成员不匹配、立场缺失或确认 Token 过期都会阻塞。`submit` 只把提交清单状态改为 `submitted`，不执行 Git commit 或 push。随后必须在登记分支执行 `git add`、`git commit` 和 `git push`。

启用 adaptive Grill 时，`validate` 和 `submit` 还会强制校验真实成员同意、任务主题覆盖、问题数量、问题定义/P0/未决分歧三项独立确认以及摘要完整性。Grill 完成仍不能替代最终正文确认，因为映射后的 `main-output.md` 可能继续变化。达到问题上限不等于完成；信息不足或成员无法参与时保持 `blocked` 并返回协调员。

## 开发与发布任务

### 正式实现

仅在 G3 基线已冻结且项目状态为 `development-entry-approved` 时开始。先核对任务的精确 Skill、`baseline_ref`、`base_commit`、工作分支、允许/禁止范围、审查人、专项责任和必需检查；再生成实施计划和测试，最后进行最小范围实现。

开发提交前向登记 `human_owner` 展示精确实现 commit、完成报告哈希、个人立场和权限声明。只有 owner 明确确认后才能记录 `development_submission_confirmation`。实现 commit、报告或任务字段变化会使确认 stale。该确认的 `gate_effect` 固定为 `none`。

### 代码审查

审查成员必须独立于开发主责，绑定任务版本和精确 commit，记录 P0/P1/P2、证据和再次提交条件。新 commit 出现后重新检查受影响结论。审查通过只授权该精确 commit 进入 PR 合并流程；合并后还要验证其为 `main` 祖先并完成集成测试。

### 发布验证与事故任务

G4 前只验证发布候选、任务集成、测试、迁移、配置、监控、灰度、停止和回滚证据，不代替真实批准人。灰度期间按批准批次观察；触发停止条件时停止扩量并升级。事故任务优先止血和保全证据，涉及生产写入、数据修复、隐私或客户沟通时等待授权人决定。G5 关闭前保留指标、事故、遗留和复盘意见。

## 阻塞与升级

遇到身份、协议、schema、协作模型、基线或参与范围不一致，要求读取未授权材料，需求与正式基线冲突，缺少高风险人工决定，或任务要求修改 Gate/基线时，停止受影响工作并向 `return_to` 提交阻塞说明。不要自行修复协调员文件。

## 完成汇报

```text
成员 ID、参与类型和本任务视角：
任务 ID、类型和协作模型：
输入基线和轮次：
提交目录与状态：submitted / blocked
独立提交或 shared-review 状态：
确认、反对、质询和保留意见：
新增来源、假设与缺口：
新增需求候选：
风险与 Gate 触发：
需要协调员处理：
```
