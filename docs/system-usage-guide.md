# AI SOP 系统完整使用说明

> 适用仓库：`xuhao666-pro/test`  
> 编写依据：`main@4835c3c4625b97f7464e6ab95ebaac7ec3657fdb`  
> 发行包：Coordinator `2.1.1`、Member `2.1.0`

## 1. 先看当前状态

本仓库当前是一个**尚未初始化具体项目的 SOP 系统模板仓库**，不是已经运行中的项目。

当前 `.github/sop-system.json` 的关键状态为：

- `lifecycle: bootstrap`
- `project_initialized: false`
- `project_data_included: false`
- 只有 A–C 前开发能力 `predevelopment_ac` 已声明可用
- D–E 开发交付、状态看板、操作台、通知、远端反馈和自动 Skill 清理均未启用

因此，仓库中的能力分为四类：

| 能力层级 | 当前状态 | 说明 |
|---|---|---|
| 系统完整性校验 | 已启用 | 当前唯一生效的 GitHub Actions 是 `sop-system-validate.yml` |
| A–C / G1–G3 | 运行时已安装 | 初始化项目后可按需求、方案、开发准入流程使用 |
| 看板、操作台、Issue + 钉钉通知、Skill 清理 | 模板已提供 | 必须完成项目初始化、配置并显式激活后才会运行 |
| D–E / G4–G5 | 运行时已提供但禁用 | 真实通过 G3、完成主干祖先校验和开发负向门禁后才能启用 |
| 成员 push 事件级即时回流 | 尚未实现 | 当前没有 `sop-member-signal.yml` 和 `sop-member-feedback.yml`；激活看板后可使用定时轮询兜底 |

在 bootstrap 状态下：

- `sop/`、`dashboard/`、`projectcode/` 不得存在，否则系统校验会失败；
- `.github/sop-templates/workflows/` 中的文件只是模板，不会被 GitHub Actions 执行；
- 不要因为模板文件存在，就认为通知、看板或自动清理已经启用。

## 2. 系统解决什么问题

这套系统把软件交付分成五个阶段，并把任务、人员确认、来源、代码提交和 Gate 结论做成可验证证据。

```text
A 需求合同
  → G1 需求准入
B 方案验证
  → G2 方案准入
C 开发准入
  → G3 开发准入
D 开发与集成
  → G4 发布准入
E 发布、观察与收尾
  → G5 交付关闭
```

它重点解决：

- 需求、方案和代码产出能够追溯到明确来源；
- 每个人只对自己的任务、分支、提交和立场负责；
- “收到提醒”“拉取代码”“接受任务”“提交完成”“Gate 通过”不会混为一谈；
- G1–G3 通过后仍要合并审核冻结的精确成员提交，并验证其属于 `main` 历史；
- 看板和通知只是投影，不会反向改写真实事实；
- 高风险操作始终保留人工权限边界。

## 3. 角色与事实边界

### 3.1 协调者

协调者可以：

- 初始化项目、登记成员、分支和责任能力；
- 预览并正式分发任务；
- 拉取并隔离校验成员分支；
- 收轮、汇总、处理意见和构建来源台账；
- 准备 G1–G5 人工评审材料；
- 在 G1–G3 人工批准后执行精确合并、祖先校验和阶段基线冻结；
- 在 D–E 记录单项任务的代码集成、G4 灰度准入与 G5 交付关闭。

协调者不能：

- 代成员接受任务；
- 代成员确认或伪造成员提交；
- 修改成员原始证据来“修复”结论；
- 从旧项目或 AI 推断新需求、范围和验收标准；
- 把多数意见写成全体共识；
- 在合并失败时手工把 Gate 标记为已完成。

### 3.2 成员

成员可以：

- 在登记的成员分支或开发分支处理精确任务；
- 生成自己的接受凭证、提交内容、检查记录和完成报告；
- 表达 `confirm`、`oppose`、`question` 或 `reserve` 的真实立场。

成员不能：

- 修改任务合同；
- 修改中央 `project-state.yaml`、aggregation、Gate、基线或 README 看板；
- 代其他成员确认；
- 批准 Gate、冻结基线或合并其他成员分支。

### 3.3 什么才是事实

| 事件 | 权威事实 | 不是事实 |
|---|---|---|
| 任务已发布 | 已确认的 assignment 文件 | 钉钉消息或聊天口头通知 |
| 成员已接受 | 成员分支上的有效 acceptance receipt | clone、fetch、pull 或打开任务 |
| 成员已提交 | 登记分支上存在状态为 `submitted` 的 submission manifest 和精确 commit | “我做完了”的消息 |
| 成员提交有效 | 协调端从登记的精确远端 ref 完整校验通过 | 仅存在 manifest |
| 成员已确认正文 | 与文档哈希、Token 绑定的 owner confirmation | 协调者代答 |
| Gate 已批准 | 有效 `gate-decision.yaml` 和所需人工确认 | 看板显示绿色 |
| Gate 已完成 | 审核 commit 均已合并且是 `main` 祖先，基线已冻结 | 仅运行 `approve-gate` |
| 代码已集成 | 受保护 PR/CI 结果和精确集成 commit | 复制文件到主干 |
| 允许开始灰度 | G4 通过，并另有组织真实生产授权 | AI 结论、通知送达或仅有 G4 |
| 交付已关闭 | G5 通过并冻结交付事实 | 把 G5 当作代码合并或生产发布授权 |

`sop/project-state.yaml`、README、SVG 看板、GitHub Issue 和钉钉消息均为投影或提醒，不能覆盖上述原始事实。

## 4. 仓库目录

初始化前的主要目录：

```text
.
├─ ai-sop-coordinator-skill-v2.1.1/   # Coordinator 统一发行包
├─ ai-sop-member-skill-v2.1.0/        # Member 统一发行包
├─ .github/
│  ├─ scripts/                        # 仓库受信任运行时
│  ├─ sop-templates/                  # 待激活工作流与配置示例
│  ├─ workflows/
│  │  └─ sop-system-validate.yml      # 当前唯一启用的工作流
│  ├─ sop-system.json                 # 生命周期与 capability 开关
│  ├─ sop-runtime-lock.json           # 运行时版本、build ID、SHA-256
│  └─ sop-skill-retention.json        # Skill 保留策略
└─ docs/
```

项目激活后会出现：

```text
.
├─ projectcode/                       # 真实业务代码；导入来源记录位置由团队另行约定
├─ dashboard/
│  └─ status.svg                      # 自动生成的看板投影
└─ sop/
   ├─ project-state.yaml              # 中央状态摘要
   ├─ roles/                          # 成员、human owner、分支、责任能力
   ├─ decisions/                      # 决策日志
   ├─ dashboard-policy.yaml           # 操作台授权策略
   ├─ notification-config.yaml        # GitHub 通知映射
   └─ stages/
      ├─ 01-requirement-contract/
      ├─ 02-solution-validation/
      ├─ 03-development-entry/
      ├─ 04-development/
      └─ 05-release/
```

每个 A–C 阶段通常包含：

```text
stage-state.yaml
dispatch/                             # 已确认任务包
acceptances/                          # 成员接受凭证；权威来源为登记成员分支
submissions/<member-id>/...           # 成员原始提交
aggregation/
  participation-matrix.yaml
  summary.md
  artifact-manifest.yaml
  rounds/<round-id>/submission-index.yaml
  provenance/
    source-block-index.yaml
    provenance-ledger.yaml
    provenance-report.md
gate/
  gate-review-pack.md
  gate-decision.yaml
baseline/<Gx-version>/
```

## 5. 版本与运行时

发行包版本和任务运行时版本不是同一个概念。

| 用途 | 根发行包 | 仓库任务运行时 |
|---|---|---|
| A–C 协调者 | Coordinator `2.1.1` | `1.8.5 / coordinator-cli-1.8.5-unified-member-package-v1` |
| A–C 成员 | Member `2.1.0` | `1.8.1 / member-cli-1.8.1-assignment-acceptance-v1` |
| 历史 A–C 提交校验 | Member `2.1.0` | legacy `1.8.0` |
| D–E 协调者 | Coordinator `2.1.1` | `2.0.0 / coordinator-dev-cli-2.0.0-v1` |
| D–E 成员 | Member `2.1.0` | `2.0.0 / member-dev-cli-2.0.0-v1` |

自动化使用 `.github/scripts/` 中由 `.github/sop-runtime-lock.json` 锁定的脚本。不要直接修改脚本后手工改哈希；应通过正式 Skill 发行、校验和升级流程更新。

个人安装的 Skill 用于指导 Codex 正确执行流程，仓库脚本用于机械校验和落盘。两者相互配合，不能互相替代。

## 6. 使用前准备

### 6.1 本地要求

- Git；
- Python 3；
- 可以访问目标 GitHub 仓库；
- 每名成员拥有独立 clone 或 worktree；
- `main` 使用分支保护；
- 协调者和成员使用各自登记的 GitHub 身份。

### 6.2 安装个人 Skill

以下 `Copy-Item` 适合目标目录尚不存在的首次安装。升级时不要直接覆盖混合旧目录；应先按团队升级流程备份/移走旧 Skill，再把新目录完整安装并核对入口文件。

协调者机器首次安装：

```powershell
Copy-Item `
  ".\ai-sop-coordinator-skill-v2.1.1\ai-sop-coordinator" `
  "$env:USERPROFILE\.codex\skills\ai-sop-coordinator" `
  -Recurse -Force
```

成员机器首次安装：

```powershell
Copy-Item `
  ".\ai-sop-member-skill-v2.1.0\ai-sop-member" `
  "$env:USERPROFILE\.codex\skills\ai-sop-member" `
  -Recurse -Force
```

安装后应确认以下文件位于精确路径：

```text
%USERPROFILE%\.codex\skills\ai-sop-coordinator\SKILL.md
%USERPROFILE%\.codex\skills\ai-sop-member\SKILL.md
```

重新打开 Codex 会话，再确认实际加载的 Skill。任务绑定的版本、build ID、包版本、包 build、包路径或发行 commit 任一项不精确匹配时，都应停止任务并安装仓库已经确认的精确稳定包；不能笼统“升级到最新”或绕过版本校验。

### 6.3 Git 分支约定

```text
main                         受保护主干
sop/member/<member-id>       A–C 成员证据分支
feat/<DEV-ID>-<slug>         功能开发
fix/<DEV-ID>-<slug>          普通缺陷
hotfix/<INC-ID>-<slug>       紧急修复
automation/...               自动化提案分支
```

禁止：

- 成员直接推送 `main`；
- 绕过 PR 和必需 CI；
- 审核后对目标 commit 强推改写；
- 用复制文件代替正式合并；
- 在一个成员工作区混用其他成员身份。

## 7. 从 bootstrap 激活为真实项目

### 7.1 先运行系统校验

```powershell
python .github/scripts/sop_system_validate.py
```

该命令应在未修改模板前通过。失败时先处理系统完整性问题，不要继续初始化。

### 7.2 收集并确认精确项目输入

初始化前必须确认：

- 项目 ID；
- 项目名称；
- 协调者 ID；
- 全新需求原文和附件来源；
- 执行模式：`standard` 或 `lightweight`；
- 协作模型：`role-based` 或 `collective-participation`；
- Gate 策略：`accountable-members` 或 `all-participants`；
- **一个**风险等级：`R0`、`R1`、`R2` 或 `R3`；
- 当前真实开发状态；
- 每个成员的 member ID、human owner 和唯一分支；
- G1、G2、G3 的责任能力映射；
- R2/R3 所需的专项责任人。

注意：

- `R0 / R1 / R2 / R3` 不是有效输入，必须选择其中一个；
- R2/R3 必须使用标准模式，并登记相应专项责任能力；
- “暂无需求，稍后输入”可以明确记录为空需求池，但不能由旧项目内容自动补全。此时可以完成系统激活和通知通道测试；在真实 task source、目标、范围、交付物和验收标准确认前，不得为测试虚构 A 阶段正式任务。

### 7.3 初始化项目

先查看当前命令参数：

```powershell
python .github/scripts/sop_coordinator_cli.py init-project --help
```

典型结构：

```powershell
python .github/scripts/sop_coordinator_cli.py init-project . `
  --project-id "<project-id>" `
  --project-name "<project-name>" `
  --coordinator-id "<coordinator-id>" `
  --execution-mode standard `
  --collaboration-model collective-participation `
  --gate-confirmation-policy accountable-members `
  --risk-level R1 `
  --real-development-status "<真实状态>" `
  --member "<member-id>:<human-owner>" `
  --member-branch "<member-id>:sop/member/<member-id>"
```

每名成员分别提供一组 `--member` 和 `--member-branch`。

初始化完成后检查：

```powershell
python .github/scripts/sop_coordinator_cli.py status .
```

### 7.4 登记 Gate 责任能力

最低责任能力：

| Gate | 最低能力 |
|---|---|
| G1 | 业务决策、产品决策 |
| G2 | 业务决策、产品决策、技术决策 |
| G3 | 项目决策、产品决策、技术决策、测试决策 |
| R2/R3 | 在上述基础上增加项目要求的专项责任能力 |

命令模式：

```powershell
python .github/scripts/sop_coordinator_cli.py assign-accountability . `
  --member-id "<member-id>" `
  --gate G1 `
  --capacity business-decision `
  --capacity product-decision
```

`accountable-members` 要求本 Gate 所有责任成员确认；`all-participants` 要求所有有效人类成员确认，但仍不能替代最低责任能力或专项责任能力。

### 7.5 导入真实业务代码

真实代码建议放入 `projectcode/`，并记录：

- 原仓库 URL；
- 原分支；
- 导入的精确 commit SHA；
- 导入时间；
- 是否保留原 Git 历史；
- 后续同步策略。

代码导入必须使用可追溯快照，不能只写“最新代码”。`projectcode/` 只应在项目激活提交中出现；bootstrap 状态会拒绝该目录。

当前系统没有固定的“源码导入来源记录”模板，也不会自动创建或验证该记录。团队应在项目治理约定中明确记录文件的位置，并通过受审 PR 保存。

### 7.6 创建看板与通知配置

从仓库示例复制：

```powershell
Copy-Item `
  ".github\sop-templates\config\dashboard-policy.example.yaml" `
  "sop\dashboard-policy.yaml"

Copy-Item `
  ".github\sop-templates\config\notification-config.example.yaml" `
  "sop\notification-config.yaml"
```

这两个文件虽然后缀是 `.yaml`，当前实现要求内容保持 JSON 兼容。应基于示例修改，不要自行发明结构。

配置要求：

- `dashboard-policy.yaml` 的 actor 键必须是实际 GitHub 登录名；
- 协调者要映射为 `coordinator` 角色；
- `notification-config.yaml` 中的 member ID 必须与任务包完全一致；
- 每个成员的 `github_login` 使用真实 GitHub 登录名。

### 7.7 配置 GitHub Environment 和 Secrets

在 GitHub 仓库中进入：

```text
Settings
→ Environments
→ New environment
→ sop-notifications
```

建议把 Environment 限制为受保护的 `main`。

在该 Environment 下配置：

| Secret | 内容 |
|---|---|
| `DINGWEBHOOK` | 钉钉机器人完整 HTTPS webhook URL |
| `DINGSECRET` | 与该机器人匹配的加签密钥 |
| `DING_MEMBER_MAP` | member ID 到钉钉 `@` 信息的 JSON 映射 |

`DING_MEMBER_MAP` 结构示例：

```json
{
  "member-a": {
    "atMobiles": ["<mobile>"],
    "atUserIds": []
  },
  "member-b": {
    "atMobiles": [],
    "atUserIds": ["<ding-user-id>"]
  }
}
```

要求：

- 顶层键必须等于任务中的精确 `member_id`；
- `atMobiles` 和 `atUserIds` 都是字符串数组；
- 手机号只能为纯数字或以 `+` 开头，不能含空格或横线；
- 自定义群机器人通常优先使用账号绑定手机号；
- 真实 webhook、secret 和手机号绝不能写进仓库。

`GITHUB_TOKEN`/`github.token` 是 Actions 内置令牌，无需自行创建，但仓库 Actions 权限必须允许对应工作流写 Issue、内容或 PR。

当前工作流不使用 `${{ vars.* }}`，无需配置 Repository Variables 或 Environment Variables。

### 7.8 激活加固工作流

可选模板：

- `.github/sop-templates/workflows/sop-dashboard-actions.yml`
- `.github/sop-templates/workflows/sop-readme-dashboard.yml`
- `.github/sop-templates/workflows/sop-notifications.yml`
- `.github/sop-templates/workflows/sop-skill-cleanup.yml`
- `.github/sop-templates/workflows/sop-skill-cleanup-validate.yml`

把确实要启用的模板复制到 `.github/workflows/`。每个已经打开的 capability 所要求的 active workflow 都必须存在，并与对应模板逐字节一致，否则系统校验会失败。

capability 与工作流的精确关系：

| capability | 必需 active workflow |
|---|---|
| `dashboard` | `sop-readme-dashboard.yml` |
| `dashboard_actions` | `sop-dashboard-actions.yml` |
| `github_issue_notifications` | `sop-notifications.yml` |
| `dingtalk_notifications` | `sop-notifications.yml` |
| `automatic_skill_cleanup` | `sop-skill-cleanup.yml`、`sop-skill-cleanup-validate.yml` |
| `remote_feedback` | `sop-member-signal.yml`、`sop-member-feedback.yml`，当前仓库未提供，必须保持 `false` |
| `development_de` | 不直接对应工作流，但必须与 runtime lock 中两个开发运行时的 `enabled` 状态同步 |

操作台还存在下游依赖：

- `refresh-state` 依赖 `sop-readme-dashboard.yml` 和 `dashboard: true`；
- `task-reminder` 依赖 `sop-notifications.yml`，且两项通知 capability 都已启用；
- `notification-test` 依赖两项通知 capability、`sop-notifications` Environment 和三个钉钉 Secrets。

不要使用旧兼容命令 `install-dashboard --force` 覆盖本仓库已加固模板。

### 7.9 切换系统生命周期

在同一个受审分支/PR 中完成：

1. 生成有效 `sop/project-state.yaml`；
2. 登记成员、分支和责任能力；
3. 导入并登记 `projectcode/`；
4. 创建看板和通知配置；
5. 复制准备启用的工作流；
6. 将 `.github/sop-system.json` 设置为：
   - `lifecycle: active`
   - `project_initialized: true`
   - `project_data_included: true`
7. 只为实际已经配置的能力打开 capability；
8. `github_issue_notifications` 与 `dingtalk_notifications` 同时启停；
9. `remote_feedback` 保持 `false`；
10. G3 真正完成前，`development_de` 保持 `false`。

不要把半完成的激活状态推到远端。bootstrap 会拒绝项目目录，而 active 又要求项目、配置和工作流完整，因此应在一个完整 PR 中切换。

### 7.10 激活校验与首次测试

```powershell
python .github/scripts/sop_system_validate.py

python .github/scripts/sop_coordinator_cli.py refresh-project-state . `
  --remote origin `
  --fetch `
  --validate-remote `
  --member-cli .github/scripts/sop_member_cli.py

python .github/scripts/sop_readme_dashboard.py `
  --state sop/project-state.yaml `
  --output dashboard/status.svg `
  --readme README.md `
  --action-url "<SOP Dashboard Actions 工作流 URL>"
```

然后：

1. 通过 PR 合入受保护 `main`；
2. 手工运行 `SOP system validation`；
3. 在操作台运行 `notification-test`，验证 webhook、secret 和通道；
4. 已有真实需求时，在首个真实任务或受控催办中验证精确成员 `@` 映射；空需求池不得为此虚构任务；
5. 验证 Assignment Issue、钉钉消息、重复执行幂等性；
6. 验证看板刷新不会绕过分支保护。

## 8. A–C：从需求到开发准入

### 8.1 A 阶段：需求合同

目标是把原始需求转成可评审、可追溯、可验收的需求合同。

流程：

1. 录入真实需求原文和附件来源；
2. `role-based` 使用 `create-assignment`，共同参与使用 `create-collective-round`；
3. 创建 `requirement-analysis + isolated-discovery` 独立任务；
4. 首次命令只生成预览和 Token，不写正式任务；
5. 用户确认后，以完全相同参数加 `--confirm-dispatch <token>` 正式分发；
6. 成员接受任务、独立分析、owner 确认、校验、提交并 push；
7. 协调者显式拉取和远端校验；
8. 关闭独立轮并发布 `submission-index.yaml`；
9. 新建引用该轮 `submission-index.yaml` 的 `shared-review` 轮；按任务包指定的参与者，成员分别提交自己的评审证据；
10. 记录每条意见的采纳、拒绝、延期和责任人；
11. 形成需求合同、需求池、用户故事和业务验收；
12. 构建来源索引并完成内容溯源；
13. 准备 G1 评审包；
14. 人工审核后进入 `merge-pending`；
15. 合并冻结的精确成员 commit；
16. 验证 commit 是 `main` 祖先并冻结 G1 基线；
17. 完成 Member Skill 发行预览与人工确认后，再分发 B 阶段任务。

G1 必需产物类型：

- `multi-view-review`
- `consensus-user-stories`
- `requirement-contract`
- `demand-pool`
- `atomic-requirements`
- `business-acceptance`

### 8.2 B 阶段：方案验证

首轮应在同一轮并行开展：

- `function-design + isolated-design`
- `system-inventory + isolated-design`

共同参与模式下，每位有效成员分别收到两类任务。没有仓库或系统权限的成员应明确登记未知项，不得猜测现状。

后续流程：

1. 关闭设计与盘点首轮；
2. 发布提交索引；
3. 创建指向首轮 `submission-index.yaml` 的 `shared-review`，并按任务包冻结的输入分别收集成员评审证据；
4. 关闭共享评审轮，完成首轮有效 summary；
5. 对设计/盘点原轮执行 `complete-round-review` 后再分发 `prototype-validation`；
6. 原型验证只使用已公开的设计、系统盘点和验证问题；
7. 关闭原型验证轮；
8. 创建指向验证轮的共享评审；
9. 收集、校验并关闭该 `shared-review` 轮；
10. 处理意见，形成采用方案、验证结果和生产差距；
11. 按第 11 节关闭阶段并完成 G2 人工审核、精确合并、祖先校验和基线冻结；
12. 完成 Member Skill 发行预览与人工确认后，再分发 C 阶段任务。

G2 必需产物类型：

- `solution-review`
- `consensus-function-design`
- `system-inventory`
- `validation-report`
- `production-gaps`

### 8.3 C 阶段：开发准入

可分发：

- `technical-design`
- `test-task-packaging`
- `generic`
- 对实质轮次的 `shared-review`

目标产出：

- 最终产品与技术方案；
- 测试矩阵；
- 可执行的开发任务包；
- 风险、灰度和回滚方案；
- 每个任务的主笔、责任人、依赖、验收和证据要求。

G3 必需产物类型：

- `final-product-technical-plan`
- `test-matrix`
- `development-task-packages`
- `risk-and-rollback`

G3 人工通过并不等于可以直接编码。还必须：

1. `approve-gate` 进入 `merge-pending`；
2. 在干净且已检出的 `main` 上执行 `merge-approved-gate`；
3. 验证审核冻结的全部 commit 都是 `main` 祖先；
4. 冻结 G3 基线；
5. 项目状态成为 `development-entry-approved`；
6. 执行 Member Skill 发行预览并完成人工确认；
7. 完成 D–E 的负向门禁；
8. 才能把 `development_de` 切换为启用。

## 9. 协调者操作手册

### 9.1 命令总览

```powershell
python .github/scripts/sop_coordinator_cli.py --help
```

按用途分组：

| 用途 | 命令 |
|---|---|
| 项目与成员 | `init-project`、`add-member`、`assign-accountability`、`migrate-project` |
| 任务与轮次 | `create-assignment`、`create-collective-round`、`supersede-round` |
| 收轮 | `validate-round`、`close-round`、`complete-round-review`、`record-shared-review` |
| 阶段 | `validate-stage`、`close-stage`、`transition` |
| 溯源 | `build-source-index`、`trace-content`、`validate-provenance`、`provenance-report` |
| Gate | `init-gate-review`、`validate-gate-review`、`prepare-gate`、`approve-gate`、`merge-approved-gate` |
| Skill 发行 | `prepare-skill-release`、`confirm-skill-release` |
| 状态 | `status`、`refresh-project-state` |
| 兼容安装 | `install-dashboard`；本仓库禁止使用 `--force` 覆盖加固模板 |

### 9.2 任务分发的双确认

任务创建命令采用两步模式：

```text
第一次：完整参数，不带 --confirm-dispatch
        → 只生成预览和一次性 Token

人工确认：核对成员、范围、输入、输出、截止条件、Skill 版本

第二次：完全相同参数 + --confirm-dispatch <Token>
        → 正式写入任务包
```

不得在第二次执行时修改参数。需要修改任务时，放弃旧 Token，重新生成预览。

已正式分发的错误轮次不能原地改写，应使用 `supersede-round` 留下替代关系和审计记录。

### 9.3 阶段与任务类型限制

| 阶段 | 可用任务类型 |
|---|---|
| `01-requirement-contract` | `requirement-analysis`、`shared-review` |
| `02-solution-validation` | `function-design`、`system-inventory`、`prototype-validation`、`shared-review` |
| `03-development-entry` | `technical-design`、`test-task-packaging`、`generic`、`shared-review` |

### 9.4 如何收集成员提交

当前没有 push 事件自动回流。协调者必须显式执行：

```powershell
python .github/scripts/sop_coordinator_cli.py refresh-project-state . `
  --remote origin `
  --fetch `
  --validate-remote `
  --member-cli .github/scripts/sop_member_cli.py
```

该步骤会：

- fetch 登记成员分支；
- 按任务要求隔离校验接受凭证和提交；
- 更新中央状态投影；
- 保留无效、缺失和阻塞原因；
- 不信任成员分支中的可执行脚本。

成员都“说已提交”不等于可以收轮。只有任务要求的精确提交都被验证后，才能执行 `validate-round` 和 `close-round`。

### 9.5 收轮与共享评审

所有 `shared-review` 都必须引用已关闭原轮的 `submission-index.yaml`。只有已经完成且不含 `[[FILL]]` 的 summary 才会成为任务输入；A 阶段不强制原轮存在 summary。任务可以同时冻结已完成 summary、candidate 或其他公共评审对象，成员可以查看原始提交核实来源，并分别提交自己的评审证据。

`role-based` 不一定要求所有成员参加；参与者以已确认任务包为准。`record-shared-review` 只用于 `collective-participation`，逐成员记录该成员提交目录中的评审证据。

A/C 通用顺序：

```text
refresh-project-state
→ validate-round
→ close-round
→ 发布 submission-index
→ 创建并关闭 shared-review 轮
→ 汇总处理评审意见
```

B 设计/盘点首轮的额外机械顺序：

```text
关闭 function-design + system-inventory 原轮
→ 创建并关闭 shared-review 轮
→ 完成原轮 summary
→ complete-round-review <原轮>
→ 才可分发 prototype-validation
```

`complete-round-review` 只支持阶段 B 中同时包含 `function-design + system-inventory` 的原始轮次，不是 A/C 的通用收轮命令。

### 9.6 状态主链

```text
preparing
→ collecting
→ submission-closed
→ aggregating
→ team-review
→ gate-pending
→ merge-pending
→ baselined
→ next-stage
```

`transition` 只能处理允许的状态转换，不能绕过 Gate 决策、精确合并或基线冻结。

### 9.7 每个基线后的 Skill 发行确认

G1、G2、G3 每次完成精确合并、祖先校验和基线冻结后，下一阶段任务分发前都必须完成：

```powershell
python .github/scripts/sop_coordinator_cli.py prepare-skill-release .

# 人工核对预览后，使用当次返回的 Token
python .github/scripts/sop_coordinator_cli.py confirm-skill-release . `
  --confirmation-token "<token>"
```

未确认稳定 Member Skill 时，下一阶段任务分发会被阻塞。Token 必须对应当前预览，不能复用旧轮 Token。

## 10. 成员操作手册

### 10.1 工作区要求

每名成员应使用独立 clone 或 worktree，并检出登记分支：

```text
sop/member/<member-id>
```

开始前确认：

- 当前 Git 身份属于本人；
- 当前分支与角色卡登记一致；
- 工作区没有其他成员残留；
- assignment 来自最新可信 `main`；
- 任务要求的 Member Skill 版本已安装。

### 10.2 A–C 标准执行顺序

```powershell
$assignment = "sop/stages/01-requirement-contract/dispatch/A-01-example.yaml"
$submission = "sop/stages/01-requirement-contract/submissions/xiaotan/A-01-example-v1.0"
$memberId = "xiaotan"

python .github/scripts/sop_member_cli.py workspace-check `
  $assignment --member-id $memberId --fetch

python .github/scripts/sop_member_cli.py inspect `
  $assignment --member-id $memberId --fetch

python .github/scripts/sop_member_cli.py accept-assignment `
  $assignment --member-id $memberId

# 提交并 push 接受凭证

python .github/scripts/sop_member_cli.py init `
  $assignment --member-id $memberId

# 完成 main-output.md 及任务包要求的其他文件

python .github/scripts/sop_member_cli.py index-content `
  $submission `
  --assignment $assignment `
  --member-id $memberId

python .github/scripts/sop_member_cli.py prepare-confirmation `
  $submission `
  --assignment $assignment `
  --member-id $memberId `
  --position confirm `
  --position-statement "<本人真实立场>"

# 向登记的 human owner 展示正文、哈希和 Token
$humanOwner = "<登记的 human owner>"
$documentHash = "<prepare-confirmation 返回的正文哈希>"
$confirmationToken = "<prepare-confirmation 返回的 Token>"

python .github/scripts/sop_member_cli.py confirm-submission `
  $submission `
  --assignment $assignment `
  --member-id $memberId `
  --confirmed-by $humanOwner `
  --document-hash $documentHash `
  --confirmation-token $confirmationToken

python .github/scripts/sop_member_cli.py validate `
  $submission `
  --assignment $assignment `
  --member-id $memberId

python .github/scripts/sop_member_cli.py submit `
  $submission `
  --assignment $assignment `
  --member-id $memberId

# 提交并 push 到登记成员分支
```

每条命令的精确参数以当前仓库的 `--help` 和 assignment 为准。

### 10.3 四种个人立场

- `confirm`：确认内容和结论；
- `oppose`：反对，并说明理由；
- `question`：存在未解决问题；
- `reserve`：保留意见。

后面三种仍可以形成有效个人提交，但必须进入意见处理清单，不能被系统或协调者投影成“赞同”。

### 10.4 接受、确认、提交的区别

```text
clone / fetch / pull
  只是同步代码

accept-assignment
  生成本人接受凭证

prepare-confirmation + human owner 回复
  确认精确正文哈希和本人立场

confirm-submission
  落盘 owner 确认

validate
  机械检查提交是否合法

submit
  冻结本次成员提交
```

任何一步都不等于 Gate 批准或合并。

## 11. G1–G3 Gate 操作

正确顺序：

```text
validate-stage
→ close-stage                         # collecting → submission-closed
→ transition --to aggregating
→ build-source-index
→ 完成带 P 标识的 summary 和 artifact-manifest
→ trace-content                       # 写入来源台账
→ validate-provenance
→ transition --to team-review
→ init-gate-review
→ 人工完善 gate-review-pack.md
→ validate-gate-review
→ prepare-gate                        # team-review → gate-pending
→ 人工填写 gate-decision.yaml 和逐人确认
→ approve-gate                        # → merge-pending
→ merge-approved-gate
→ main 祖先校验
→ 基线冻结
→ prepare-skill-release
→ 人工核对并 confirm-skill-release
```

Gate 可选结论：

- `pass`
- `conditional-pass`
- `return`
- `terminate`

只有有效的 `pass` 或 `conditional-pass` 可以进入 `merge-pending`。

注意：

- `approve-gate` 只记录人工批准并进入待合并；
- `merge-approved-gate` 才负责合并冻结的精确成员 commit；
- 只有全部 commit 成为 `main` 祖先，才可冻结基线；
- `close-stage` 只到 `submission-closed`，不会自动跳到 `team-review`；
- `prepare-gate` 强制要求阶段已经处于 `team-review`；
- `gate-review-pack.md` 是人类可读投影，不能反向覆盖成员原始提交、来源台账或候选产物。

## 12. D–E：开发、发布与交付

本节描述**G3 后才允许启用的目标流程**。当前 bootstrap 仓库不能直接执行，D–E 的负向 G3/main 祖先门禁仍需在启用前验证。

### 12.1 启用前提

- G3 已按完整顺序通过；
- G3 审核 commit 已全部合入；
- commit 祖先校验通过；
- G3 基线已冻结；
- 项目状态为 `development-entry-approved`；
- D–E 负向门禁通过；
- `.github/sop-system.json` 中 `development_de` 与开发运行时 lock 状态一致。

### 12.2 协调者开发 CLI

```powershell
python .github/scripts/sop_development_cli.py --help
```

命令：

- `init-development`
- `create-task`
- `record-review`
- `record-integration`
- `prepare-g4`
- `approve-g4`
- `record-rollout`
- `prepare-g5`
- `approve-g5`
- `status`

### 12.3 成员开发 CLI

```powershell
python .github/scripts/sop_member_development_cli.py --help
```

命令：

- `accept-assignment`
- `init`
- `record-check`
- `prepare-confirmation`
- `confirm-submission`
- `validate`
- `submit`

### 12.4 D–E 启用后的目标流程

1. 协调者以 `init-development --g3-baseline <G3-id@sha>` 初始化开发；
2. 协调者依据 G3 基线显式准备开发任务 JSON spec，系统不会自动把 G3 任务包转换成开发任务；
3. 使用同一 spec 先生成预览，再按 Token 正式分发；
4. 成员显式接受任务；
5. 成员先补测试，再实现；
6. 使用 `record-check` 登记精确测试、构建、扫描命令和结果；
7. human owner 确认实现 commit、报告哈希和个人立场；
8. 成员校验、冻结并 push 功能分支；
9. 非作者审查精确 commit；
10. 协调者记录 review；
11. 通过受保护 PR 和 CI 合入；
12. 协调者记录 integration，并验证批准 commit 是目标 `main` 祖先；
13. 发布范围内任务全部集成后准备 G4；
14. 发布负责人使用 Token 人工批准 G4；
15. 分批 rollout，比例只能单调增加；
16. 达到 100%、观察通过且没有未关闭事故后准备 G5；
17. 交付负责人批准 G5并冻结交付基线。

开发任务 spec 模板：

```text
ai-sop-coordinator-skill-v2.1.1/
  ai-sop-coordinator/assets/project-template/development-task-spec.json
```

双确认命令模式：

```powershell
$spec = "path/to/development-task-spec.json"

python .github/scripts/sop_development_cli.py create-task . `
  --spec $spec

# 人工核对预览后，使用同一 spec 和当次 Token
python .github/scripts/sop_development_cli.py create-task . `
  --spec $spec `
  --confirm-dispatch "<token>"
```

当前 D–E 还存在必须明确的机械边界：

- 没有显式事故开启/关闭 CLI；
- G4 当前只有批准命令，没有与 A–C 等价的 `reject`/`conditional-pass` 记录命令；
- D–E 任务合同尚无与 A–C 相同的包级 provenance；
- 单项开发任务只合并该任务批准的精确代码 commit；
- G4 不重新合并全体成员分支，只验证发布范围任务已经集成；
- G5 冻结交付事实，不授予代码合并权。

G4/G5 不能替代组织的真实生产授权。AI 不得独立：

- 部署生产；
- 删除生产数据；
- 修改密钥；
- 执行数据库回滚；
- 执行高风险数据修复。

## 13. GitHub Actions 工作流

### 13.1 工作流总表

| 工作流 | 当前状态 | 主要触发 | 权限/Secrets | 主要作用 |
|---|---|---|---|---|
| `sop-system-validate.yml` | 已启用 | push `main`、PR、手工 | `contents: read`，无 Secrets | 系统、运行时、发行包和测试完整性校验 |
| `sop-dashboard-actions.yml` | 未激活模板 | 手工 | 按子任务使用 `contents/issues` 写权限；通知测试读钉钉 Secrets | 低风险操作台 |
| `sop-readme-dashboard.yml` | 未激活模板 | 状态路径 push、cron 轮询、被操作台调用 | `contents: write` | 刷新远端成员状态、README 和 SVG |
| `sop-notifications.yml` | 未激活模板 | `main` 上任务包、submission manifest、project-state 路径变化，或被操作台调用 | `issues: write`、钉钉 Secrets | Assignment Issue 与钉钉提醒 |
| `sop-skill-cleanup.yml` | 未激活模板 | 每周、手工、Skill 变化 | `contents: write`、`pull-requests: write` | 生成 Skill 清理分支和 PR |
| `sop-skill-cleanup-validate.yml` | 未激活模板 | Skill 相关 PR | `contents: read` | 清理 PR 的只读回归校验 |

### 13.2 SOP System Validate

入口：

```text
GitHub
→ Actions
→ SOP system validation
→ Run workflow
```

对应文件为 `.github/workflows/sop-system-validate.yml`。

它检查：

- bootstrap/active 生命周期边界；
- 运行时 lock；
- Skill frontmatter、布局、manifest、build ID 和 SHA；
- 清理审计与保留策略；
- 是否误提交真实钉钉 webhook 或大陆手机号；
- Python 脚本编译；
- Coordinator、Member、Issue 和钉钉测试；
- 校验结束后仓库是否出现意外 tracked/untracked 变化。

这是只读工作流。任一步骤非零退出或产生意外文件，整个工作流失败。

### 13.3 SOP Dashboard Actions 操作台

入口：

```text
GitHub
→ Actions
→ SOP 协调操作台
→ Run workflow
```

对应文件为 `.github/workflows/sop-dashboard-actions.yml`。

可选动作：

| `dashboard_action` | 作用 | 额外输入 |
|---|---|---|
| `refresh-state` | 刷新远端成员状态和中央看板 | 可选 `base_main_sha`、`base_revision` |
| `notification-test` | 测试 webhook、secret 和钉钉通道 | 不读取具体 assignment，不验证成员 `@` 映射 |
| `task-reminder` | 催办一个精确 assignment | 必填 `assignment_id`，可选 `reminder_detail` |

保护规则：

- 只能从当前可信 `main` 新开运行；
- 拒绝对旧运行点击 rerun；
- 可使用 `main SHA + project-state revision` 做乐观锁；
- 触发者必须在 `sop/dashboard-policy.yaml` 中被授权；
- 催办只允许针对 `missing`、`blocked`、`not-submitted` 或 `invalid`；
- `reminder_detail` 只用于显示，不得被当作事实；
- 操作台不能接单、正式分发任务、关轮、批准 Gate、部署或回滚。

### 13.4 README Dashboard

启用后会：

1. fetch 登记成员分支；
2. 使用可信 `main` 脚本隔离校验；
3. 更新 `sop/project-state.yaml`；
4. 渲染 `dashboard/status.svg`；
5. 更新 README 中的操作入口；
6. 只有发生语义变化时才提交中央快照。

触发：

- `main` 上中央状态、接受凭证或提交发生变化；
- cron 每 5 分钟尝试执行一次作为兜底；
- 操作台委托调用。

GitHub cron 只在默认分支生效，也可能因平台排队而延迟；“每 5 分钟”不是 5 分钟处理 SLA。

当前模板会以 GitHub Actions bot 直接提交到 `main`。如果分支保护不允许机器人直推，应在启用前选择：

- 明确允许受控 bot 更新这些投影文件；或
- 改成受审 PR/人工中央快照流程。

不得为了看板而绕过组织的主干保护。

### 13.5 SOP Notifications

支持事件：

- `task-dispatched`
- `task-reminder`
- `submission-received`
- `submission-valid`
- `submission-invalid`
- `task-blocked`

自动 push 触发只监听可信 `main` 上的精确状态路径。成员分支 push 不会直接运行这个带写权限和 Secrets 的工作流；成员事实要先经过可信刷新并投影到 `main`。

工作流先维护 Assignment Issue，再发送钉钉，并写入幂等标记。若 Issue 成功而钉钉失败，可能出现部分副作用；重新运行时依靠幂等记录避免重复。

通知失败不代表成员提交无效，通知成功也不代表成员已接受或已提交。

### 13.6 Skill Cleanup

自动清理模板：

- 每周一 `01:30 UTC`，即北京时间周一 `09:30`；
- 也可手工运行；
- 先生成 plan；
- 没有候选项时只报告；
- 有候选项时创建或更新 `automation/sop-skill-cleanup`；
- 运行系统校验和回归测试；
- 创建或更新 PR；
- 永不自动合并 `main`。

计划时间是 GitHub cron 的尝试频率，实际开始时间可能因平台排队而延迟。

清理校验模板在相关 PR 上执行只读回归。

`sop-skill-cleanup-validate.yml` 一旦复制到 active workflows，命中路径的 PR 就会执行；它是只读校验，设计上不受 `automatic_skill_cleanup` capability guard 控制。`sop-system-validate.yml` 同样始终执行。

清理器遇到未跟踪用户文件、`.env`、虚拟环境或非白名单忽略残留时会拒绝继续。清理审计必须永久保留，CI 应使用完整 Git 历史。

## 14. 钉钉与 GitHub Issue 通知

### 14.1 通知链路

```text
可信 main 中的任务/状态变化
→ sop-notifications.yml
→ 建立或更新 Assignment Issue
→ 调用钉钉机器人
→ 写入幂等标记
```

GitHub Issue 与钉钉通知 capability 必须同时启用或同时禁用。

### 14.2 成员 `@` 映射

任务包中的精确 `member_id`、`notification-config.yaml` 的 `members` 对象键，以及 `DING_MEMBER_MAP` 的顶层键必须完全一致，包括大小写。

钉钉不 `@` 人时依次检查：

1. member ID 是否精确一致；
2. `DING_MEMBER_MAP` 是否为合法 JSON；
3. `atMobiles` 是否非空且格式合法；
4. 手机号是否绑定该钉钉账号；
5. 自定义机器人是否支持当前 `atUserIds` 类型；
6. webhook 与 secret 是否来自同一个机器人。

### 14.3 GitHub 邮件提醒

工作流只负责 Issue 与评论。成员是否收到 GitHub 邮件，由成员自己的 GitHub Notifications/Watching 设置决定，仓库工作流不能替所有用户统一关闭邮件。

## 15. 状态看板

看板显示的是中央 `project-state.yaml` 的投影。

建议展示：

- 当前阶段与 Gate；
- 每轮任务数；
- 已分发、已接受、已提交、有效、无效、缺失和阻塞数量；
- 每名成员的接受时间、提交时间和校验结果；
- 当前轮次和待办；
- G1–G5 状态；
- 操作台入口。

“已接受”只能来自有效 acceptance receipt，不能由成员执行 pull 自动推断。

看板适合查看和发起低风险动作，但不应成为可任意修改 SOP 事实的后台。正式任务分发、关轮、Gate、合并、发布和回滚仍通过受信任 CLI、PR 和人工授权完成。

## 16. 远端反馈的当前限制

当前仓库未提供：

- `sop-member-signal.yml`
- `sop-member-feedback.yml`

因此 `remote_feedback` 必须保持 `false`。

目前的正确收集方式：

```text
成员 push 登记分支
→ 协调者手工 refresh-project-state --fetch --validate-remote
→ 中央状态更新
→ 看板定时刷新仅作兜底
```

即使启用看板的 5 分钟计划任务，也不等于事件级自动收轮。使用说明、看板和消息中都不应承诺“成员一 push 就自动完成反馈回流”。

## 17. 日常工作清单

### 17.1 协调者开始一天

```powershell
git fetch origin
git switch main
git pull --ff-only

python .github/scripts/sop_system_validate.py

python .github/scripts/sop_coordinator_cli.py refresh-project-state . `
  --remote origin `
  --fetch `
  --validate-remote `
  --member-cli .github/scripts/sop_member_cli.py

python .github/scripts/sop_coordinator_cli.py status .
```

随后检查：

- 有无新接受凭证；
- 有无新提交或无效提交；
- 当前轮是否满足收轮条件；
- 是否有真实阻塞或保留意见；
- 是否需要催办；
- Gate 证据是否完整。

### 17.2 成员开始任务

```text
同步可信 main
→ 切换本人登记分支
→ workspace-check
→ inspect
→ accept-assignment
→ push 接受凭证
→ init
→ 完成工作
→ owner 确认
→ validate
→ submit
→ push 本人分支
```

### 17.3 合并或发布前

- 工作区干净；
- 审核对象是精确 commit；
- 必需 CI 通过；
- 人工确认哈希未变化；
- 所有 required reviewer 已确认；
- 合并后执行祖先校验；
- 基线只在祖先校验成功后冻结；
- G4/G5 不代替真实生产授权。

## 18. 常见问题与修复

### 18.1 工作流显示成功，但什么也没发生

对于带 capability guard 的副作用工作流，先看 guard 输出。常见原因：

- 系统仍为 `bootstrap`；
- 对应 capability 为 `false`；
- 当前工作流只是模板，尚未复制到 `.github/workflows/`。

`sop-system-validate.yml` 和只读的 `sop-skill-cleanup-validate.yml` 不使用该 capability guard 逻辑。

### 18.2 `actor-not-authorized`

触发人的真实 GitHub 登录名未精确登记在 `sop/dashboard-policy.yaml`。不要填写昵称或 member ID 代替 GitHub login。

### 18.3 `stale-main-sha` 或 `stale-project-revision`

主干或项目状态已变化。不要 rerun 旧运行；回到最新 `main` 新建一次操作。

### 18.4 `Assignment Issue does not exist; deliver task-dispatched first`

后续通知到达前，任务初次分发 Issue 没有建立。

处理：

1. 确认 assignment 已在可信 `main` 正式分发；
2. 先重新投递 `task-dispatched`；
3. 确认 Assignment Issue 存在；
4. 再处理 `submission-received` 等后续事件。

该错误只说明通知链路顺序不完整，不应自动把成员提交判为失败。

### 18.5 钉钉 webhook 失败

检查：

- `DINGWEBHOOK` 是完整 HTTPS URL；
- Secret 值中没有 `DINGWEBHOOK=` 前缀；
- 没有多余引号或 GitHub 表达式文本；
- 域名属于 `dingtalk.com`；
- `DINGSECRET` 与 webhook 属于同一机器人；
- Environment 名称为 `sop-notifications`。

### 18.6 钉钉摘要出现 `????`

通常是生成消息的进程、控制台或子进程边界使用了错误编码。仓库文档和脚本使用 UTF-8；调用 Python、PowerShell 和 subprocess 时都应显式保持 UTF-8，不能先用错误代码页解码再发送。

### 18.7 看板无法 push

模板会由 bot 直接更新 `main`。若主干保护拒绝：

- 不要关闭必要保护；
- 明确允许受控 bot 更新投影文件；或
- 把看板更新改成 PR/人工快照。

### 18.8 成员提交提示 Skill 版本不匹配

任务绑定与成员当前环境未精确匹配。更高或更低版本、同版本不同 build ID、包版本、包 build、包路径或发行 commit 不同都会阻塞。应安装任务精确绑定或仓库已经确认的稳定统一包并重新打开会话，不能修改 assignment、笼统升级到“最新”或跳过校验。

### 18.9 阶段有效项突然变少

常见原因：

- 远端分支被删除或不再指向登记 commit；
- 接受凭证或提交不在登记分支；
- 任务包要求的 Skill/runtime 发生不兼容；
- owner confirmation 的正文哈希与当前文件不一致；
- 主干状态是旧投影，尚未刷新；
- 旧轮被 supersede，但看板仍在查看旧轮。

先运行远端刷新和轮次校验，再按具体失败原因修复事实，不要直接改看板数字。

### 18.10 自动 Skill 清理没有执行

检查：

- 工作流是否仍只在模板目录；
- `automatic_skill_cleanup` 是否启用；
- 是否到达计划时间或有相关触发；
- 清理 plan 是否真的有候选项；
- 是否存在未跟踪或非白名单忽略文件；
- Actions 是否拥有创建分支和 PR 的权限。

候选数为 `0` 时，不产生清理 PR 是正常结果。

## 19. 安全与权限要求

- 所有有写权限的 Actions 只能运行可信 `main` 中的脚本；
- 成员分支一律作为不可信数据读取；
- 不在仓库保存 webhook、secret、手机号、token 或生产凭据；
- 不让 PR 分支代码在带生产 Secrets 的环境执行；
- 任务分发 Token、成员正文确认 Token、Skill 发行确认 Token，以及 D–E 的 G4/G5 预览批准 Token，只能用于对应预览；G1–G3 使用人工 Gate 决策和精确分支头绑定，不使用分发式 Gate Token；
- 通知、看板、AI 回复不能替代人工审批；
- 不绕过分支保护、required checks 和 required reviews；
- 不用 AI 独立执行部署、回滚、删库、密钥修改或高风险修复。

系统校验会主动扫描真实钉钉 access token 和大陆手机号。一旦发现疑似敏感值，应先轮换 Secrets，再清理 Git 历史风险。

## 20. 快速命令索引

### 系统

```powershell
python .github/scripts/sop_system_validate.py
```

### A–C 协调者

```powershell
python .github/scripts/sop_coordinator_cli.py --help
python .github/scripts/sop_coordinator_cli.py status .
```

### A–C 成员

```powershell
python .github/scripts/sop_member_cli.py --help
```

### D–E 协调者

```powershell
python .github/scripts/sop_development_cli.py --help
```

### D–E 成员

```powershell
python .github/scripts/sop_member_development_cli.py --help
```

### 看板生成

```powershell
python .github/scripts/sop_readme_dashboard.py --help
```

### Skill 清理

```powershell
python .github/scripts/sop_skill_cleanup.py --help
```

## 21. 推荐阅读顺序

1. 本文；
2. [新项目启动说明](../.github/SOP-BOOTSTRAP.md)；
3. [当前限制](../.github/CURRENT-LIMITATIONS.md)；
4. [通知说明](../.github/SOP-NOTIFICATIONS.md)；
5. [Skill 清理说明](../.github/SOP-SKILL-CLEANUP.md)；
6. [开发交付 SOP](development-sop.md)；
7. [Coordinator 使用说明](../ai-sop-coordinator-skill-v2.1.1/USAGE.zh-CN.md)；
8. [Member 使用说明](../ai-sop-member-skill-v2.1.0/USAGE.zh-CN.md)；
9. [工作流模板说明](../.github/sop-templates/README.md)。

## 22. 项目正式启动检查表

在把本仓库用于真实项目之前，逐项确认：

- [ ] 已选择一个明确风险等级；
- [ ] 已录入全新需求原文或明确保持空需求池；
- [ ] 项目 ID、名称、协调者 ID 已确认；
- [ ] 成员 ID、human owner 和唯一分支已确认；
- [ ] G1–G3 最低责任能力已登记；
- [ ] R2/R3 专项责任人已登记；
- [ ] 真实代码已按精确来源 commit 导入；
- [ ] `sop/project-state.yaml` 有效且非空；
- [ ] 看板与通知配置来自仓库示例；
- [ ] `sop-notifications` Environment 已建立；
- [ ] 三个钉钉 Secrets 只保存在 Environment；
- [ ] 只复制实际准备启用的加固工作流；
- [ ] Issue 与钉钉 capability 同时启停；
- [ ] `remote_feedback` 保持 `false`；
- [ ] G3 前 `development_de` 保持 `false`；
- [ ] 系统校验通过；
- [ ] 激活变化通过受保护 PR 合入；
- [ ] 看板、通知和幂等测试通过；
- [ ] 团队理解“提醒不等于事实、批准不等于合并”。
