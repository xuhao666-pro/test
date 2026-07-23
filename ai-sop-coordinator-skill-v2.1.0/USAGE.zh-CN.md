# AI SOP 协调者 Skill V2.1.0 使用说明

本版本保留 D 正式开发、代码审查与集成、E 发布交付、G4/G5 和灰度闭环，并把 A—C Member 运行时发现升级为统一包模型。A—C 协调 CLI 身份为 V1.8.5；一个 Member V2.1 包可以精确承载历史 1.8.0、A—C 1.8.1 和 D—E 2.0.0 三套任务运行时。

A—C 与 G1—G3 任务继续使用 `coordinator_cli.py`；V2.0 开发、集成和发布门禁继续使用 `development_cli.py`。包版本只标识完整发行包，任务包中的 `version` 与 `build_id` 标识实际执行的 runtime；两层身份均会写入确认记录。后者机械校验任务预览确认、非作者审查、精确 commit 合入 main、G4 人工批准、灰度记录和 G5 人工关闭。

开发和发布协调必须读取：

- `ai-sop-coordinator/references/development-coordination.md`
- `ai-sop-coordinator/references/development-gates.md`
- `ai-sop-coordinator/references/development-git-governance.md`

## V2.0 开发与发布命令

先复制 `ai-sop-coordinator/assets/project-template/development-task-spec.json`，填入协调者或用户明确确认的任务内容。不得由 AI 从项目状态中静默创造目标、范围或验收条件。

```powershell
python ai-sop-coordinator/scripts/development_cli.py init-development <project-root> --g3-baseline <G3-id@sha>
python ai-sop-coordinator/scripts/development_cli.py create-task <project-root> --spec <task.json>
# 人工核对 preview 后，用返回的 token 正式派发：
python ai-sop-coordinator/scripts/development_cli.py create-task <project-root> --spec <task.json> --confirm-dispatch <token>
python ai-sop-coordinator/scripts/development_cli.py record-review <project-root> --task-id <id> --reviewer <reviewer> --commit <sha> --verdict approved --p0 0 --p1 0
python ai-sop-coordinator/scripts/development_cli.py record-integration <project-root> --task-id <id> --commit <sha> --target-ref main
python ai-sop-coordinator/scripts/development_cli.py prepare-g4 <project-root> --release-candidate <sha>
python ai-sop-coordinator/scripts/development_cli.py approve-g4 <project-root> --confirmation-token <token> --approved-by <release-owner>
python ai-sop-coordinator/scripts/development_cli.py record-rollout <project-root> --percentage 100 --observation passed
python ai-sop-coordinator/scripts/development_cli.py prepare-g5 <project-root>
python ai-sop-coordinator/scripts/development_cli.py approve-g5 <project-root> --confirmation-token <token> --approved-by <delivery-owner>
```

`record-integration` 强制验证已审查的精确 commit 是目标 `main` 的祖先；仅记录 PR 存在或分支存在不能通过。G4/G5 的 prepare 只生成绑定当前事实的预览，必须由相应人类责任人明确批准。

## V1.8.4：统一人工 Gate 评审包

每个 G1–G3 Gate 都新增一份 `gate/gate-review-pack.md`，让全体成员在线下评审时直接看懂用户问题、成员观点、方案或技术结论、分歧、风险、取舍和建议决定。标准顺序为：

`init-gate-review → 协调员 AI 撰写人工内容 → validate-gate-review → prepare-gate`

评审包只是正式候选产物、成员提交、来源台账和决策记录的只读投影，不得反向覆盖原始事实，也不能替代 Gate 人工批准、责任能力、分支合并和基线冻结。`approve-gate` 会拒绝正文哈希或来源指纹已经变化的 stale 材料；完成原有强制合并后，实际审核的 Markdown 会随 Gate 决议一起进入冻结基线。

```powershell
python ai-sop-coordinator/scripts/coordinator_cli.py init-gate-review <project-root> --stage <stage-id>
python ai-sop-coordinator/scripts/coordinator_cli.py validate-gate-review <project-root> --stage <stage-id>
```

本发行包只包含 `ai-sop-coordinator`。它用于任务输入与确认、成员和分支登记、提交状态投影、来源追踪、共享评审、Gate 审批后的强制合并以及基线冻结。

## 安装

将本目录中的 `ai-sop-coordinator` 文件夹复制到：

```text
%USERPROFILE%\.codex\skills\ai-sop-coordinator
```

重启 Codex 后即可使用。协调者环境不需要安装完整的 `ai-sop-member`；用于远程提交校验的受信任成员校验器已经内置在：

```text
ai-sop-coordinator/assets/remote-validator/member_cli.py
```

该校验器只供协调者和仓库自动化验证成员提交，不能代替成员 Skill 执行成员任务。

## 团队部署

- 协调者安装本包。
- 每名成员安装统一的 `ai-sop-member` V2.1 包；执行任务时再按任务包的 `runtime_profile`、运行时 `version` 与 `build_id` 选择该包内的精确 CLI。任务要求 1.8.1 runtime 不代表需要另装一个 1.8.1 根包。

## V1.8.3 新增技术控制

- 新任务精确绑定 Member V1.8.1 后，成员必须运行 `accept-assignment` 并将接受凭证推送到登记分支。
- 看板只在协调端从精确远端 ref 观测并校验凭证后显示“已接受”；普通 Git 拉取和消息送达不算接受。
- 接受状态只代表接单，不代表提交完成、收轮或 Gate 通过；V1.8.0 历史任务不追溯补签。
- 协调者同时内置 V1.8.1 与 V1.8.0 校验器，确保新版启用后仍可验证历史任务。

V1.8.2 的以下控制继续保留：

- 历史任务按各自提交目录最后一次变更的可达 commit 校验，不再用成员分支最新 HEAD 回溯旧任务。
- 看板任务卡默认聚焦当前 collecting 轮次；历史任务继续保留在总量和事实记录中。

V1.8.1 的以下控制继续保留：

- `validate-round`、`close-round`、`complete-round-review`、`validate-stage` 和 `close-stage` 直接读取登记成员远端分支的精确 commit。
- 远端收轮使用包内受信任 Member CLI 完成任务、分支、基线、正文哈希和 human owner 确认校验；不要求提前合并成员分支或复制提交到本地 `main`。
- 收轮索引记录 `observed_ref`、`observed_head` 和提交时间；远端缺失、无效或不可访问时继续阻塞，不允许用本地空目录冒充远端事实。

V1.8.0 的以下控制继续保留：

- 项目初始化时 AI 对话协同默认 `required`；协调员可明确选择 `optional`。
- Gate 合并和基线冻结后运行 `prepare-skill-release`，审阅系统发现的稳定统一 Member 包及其 `predevelopment` runtime。
- 使用预览 Token 运行 `confirm-skill-release` 后，下一阶段任务自动携带精确运行时版本/build、包版本/build、包路径、runtime profile 与发行 commit。
- 版本确认和 AI 对话协同均不改变既有 Gate、基线、正式产物或最终人工确认。
- 两类 Skill 通过同一个私有 Git 仓库中的任务契约、成员分支和提交清单协作，不依赖同机安装。

## 基本使用流程

1. 在协调者环境启动 `ai-sop-coordinator`，先输入任务来源、目标、范围、交付物、验收标准、约束、依赖和优先级。
2. 对需求分析任务明确决定是否启用 `--human-collaboration-mode adaptive-grill`；启用时确认真实成员可参与以及问题上限。选择 `none` 只关闭 Grill，不关闭提交确认。
3. 让 Skill 生成任务预览；确认预览同时包含独立的 `submission_confirmation` 策略后，才允许使用确认令牌正式签发任务。
4. 初始化项目并登记成员、成员分支、参与方式和 Gate 责任。
5. 成员完成正文后，由任务登记的 `human_owner` 确认当前 `main-output.md` 正文哈希和个人立场；AI 不得代签。该确认只允许个人贡献提交，不构成 G1–G3 Gate 批准。
6. 成员先推送接受凭证；刷新后看板显示“已接受”。成员完成产物并再次推送后，再刷新 `project-state.yaml`，隔离校验远程提交和 `human-submission-confirmation.yaml`。
7. 关闭独立提交窗口后，构建来源索引、组织共享评审并形成带来源标记的汇合稿。
8. 准备 G1–G3 审核包。人工审核通过后进入 `merge-pending`，再执行强制合并命令，将审核过的所有成员精确提交合并到 `main`。
9. 只有全部合并和祖先关系校验成功后，才冻结基线并推进阶段。

常用命令入口：

```powershell
python "$env:USERPROFILE\.codex\skills\ai-sop-coordinator\scripts\coordinator_cli.py" --help
```

## 分离边界

- 协调者可以读取和验证成员提交，但不替成员生成、修改或提交成员产物。
- 协调者不根据拉取操作或通知送达推断接受，也不替成员生成接受凭证。
- `human_collaboration` 只控制 Grill；V1.7.5+ 新任务始终要求登记 owner 在 submit 前确认正文哈希和个人立场。
- AI 不得代替 owner 选择立场或确认。`confirm`、`oppose`、`question`、`reserve` 均可作为有效个人提交，后三者必须保留为待处理意见。
- 提交确认的 `gate_effect` 固定为 `none`，不能替代 Gate 的责任能力、确认策略或人工审批。
- V1.7.5 之前的任务只标记 `legacy-not-required`，不得追溯补签；需要新规则时重新签发任务。
- 协调者维护中央状态、来源台账、看板、Gate 和合并记录；成员不得直接修改这些中央事实源。
- 本包不会向成员环境安装 Member Skill。成员包必须独立发放和安装。
- 历史合并发行包可保留用于审计，但新部署只需按人员职责安装相应独立包。
