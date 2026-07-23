# AI SOP 新项目工作区

一套面向多人 AI 协作软件交付的可审计流程系统，把需求、任务、成员确认、Git 提交、评审、Gate 和发布证据记录为可验证事实。

> **当前状态：`bootstrap`**
>
> 系统发行包、受信任运行时和只读校验已经安装，但真实项目尚未初始化。
> 当前没有项目成员、需求、任务、Gate、基线、看板状态或业务代码。
> 看板、通知、操作台、自动清理和 D–E 开发交付能力目前均未启用。

第一次接触本系统，建议按顺序阅读：

- [5 分钟入门](docs/getting-started.md)
- [完整使用说明](docs/system-usage-guide.md)
- [新项目初始化与激活](.github/SOP-BOOTSTRAP.md)
- [开发交付 SOP](docs/development-sop.md)

## 你现在该怎么开始

| 你的情况 | 建议从哪里开始 |
|---|---|
| 我只是想了解系统 | 先读“生命周期全景”和“当前真正可用的能力”，再运行 5 分钟只读校验 |
| 我是仓库管理员 | 准备受保护 `main`、Actions 权限、成员 Git 身份和后续 Environment |
| 我是 Coordinator | 安装 Coordinator Skill，收集真实项目输入，再按初始化章节执行 |
| 我是 Member | 安装 Member Skill；收到正式 assignment 后，在本人登记分支检查并接受 |
| 我要把 SOP 接入已有代码仓库 | 先读“新仓库与已有代码仓库”并保留现有代码、CI 和发布门禁 |
| 项目已经通过 G3，要进入开发 | 阅读 [开发交付 SOP](docs/development-sop.md)，不要继续使用 A–C 命令处理代码任务 |

快速跳转：

- [生命周期](#生命周期全景)
- [能力状态](#当前真正可用的能力)
- [5 分钟校验](#5-分钟检查系统)
- [初始化项目](#如何启动一个真实项目)
- [A–C 任务与 Gate](#ac-workflow)
- [GitHub Actions](#github-actions-与模板)
- [常见问题](#常见问题)

## 这是什么项目

AI SOP 不是业务应用，也不是一个已经开始运行的项目。它是一个可以复制或接入真实代码仓库的协作治理工作区，主要解决以下问题：

- 把模糊需求整理为可验收的需求合同；
- 让多人分别分析、提交和评审，不用聊天记录冒充正式结论；
- 把任务绑定到精确成员、分支、基线、输入、交付物和验收标准；
- 记录成员是否真正接受任务、提交了什么、由谁确认；
- 把需求、设计、代码、测试和发布证据串成可追溯链路；
- 在 G1–G5 人工 Gate 前准备可读材料，并阻止流程越级；
- 在开发阶段约束功能分支、非作者审查、CI、主干集成和发布责任；
- 通过 GitHub Issue、钉钉和看板提醒或展示状态，但不让这些投影替代正式事实。

简单来说，它回答的是：

```text
需求从哪里来？
谁负责什么？
成员是否真正接受了任务？
提交内容对应哪个精确 commit？
谁确认了正文或代码？
哪些意见仍未处理？
为什么可以进入下一阶段？
发布、回滚和关闭由谁决定？
```

## 适合哪些场景

适合：

- 新项目从需求分析开始建立完整协作流程；
- 已有代码仓库接入后续功能开发治理；
- 多名成员共同参与需求、方案、测试和开发准入；
- 需要保留个人意见、少数意见和来源证据的团队；
- 需要明确 G1–G5 人工决策、代码审核和发布责任的项目；
- 希望用 GitHub 分支、PR、Actions 和钉钉形成协作闭环的团队。

不适合直接拿来做：

- 单人一次性脚本或无需审计的临时实验；
- 绕过组织审批的自动生产部署；
- 让 AI 代替真实成员、审核人或 Gate 责任人作出批准；
- 把聊天消息、Issue、通知或看板当作唯一事实源。

## 生命周期全景

系统把软件交付划分为五个阶段和五个人工 Gate：

```text
A 需求合同
  → G1 需求准入
B 方案验证
  → G2 方案准入
C 开发准入
  → G3 开发准入
D 开发、审查与集成
  → G4 灰度/发布准入
E 发布观察、事故处理与收尾
  → G5 交付关闭
```

| 阶段 | 主要目标 | 典型核心产物 | 下一步条件 |
|---|---|---|---|
| A 需求合同 | 明确问题、范围、用户价值和验收标准 | 需求合同、来源索引、意见处理记录 | G1 人工决定、合并与基线冻结 |
| B 方案验证 | 对比设计、盘点现状、验证原型与生产差距 | 功能设计、系统盘点、原型验证、方案评审包 | G2 人工决定、合并与基线冻结 |
| C 开发准入 | 固化技术方案、测试策略、风险和任务拆分 | 技术设计、测试方案、开发任务包、G3 交接清单 | G3 人工决定、主干祖先校验与稳定 Skill |
| D 开发与集成 | 测试优先实现、独立审查、CI 和主干集成 | 代码、测试、审查证据、集成记录、G4 发布包 | G4 人工批准发布范围 |
| E 发布与收尾 | 灰度、观察、事故处理、回滚和复盘 | 发布记录、观察证据、事故/回滚记录、G5 关闭包 | G5 人工关闭与交付基线冻结 |

Gate 不是一次口头“确认”。G1–G3 通过后还必须完成精确成员分支合并、祖先关系校验和基线冻结；G4/G5 也不能替代真实组织的生产授权。

## 当前真正可用的能力

“文件存在”“运行时已安装”和“能力已经启用”是三件不同的事。

| 能力 | 当前状态 | 准确含义 |
|---|---|---|
| SOP 系统完整性校验 | **已启用** | 当前 `main` 中唯一 active workflow 定义，只读且不使用 Secrets |
| A–C / G1–G3 | **运行时已安装** | 初始化真实项目后才能开始使用 |
| D–E / G4–G5 | **运行时随包提供、当前禁用** | 真实通过 G3 和开发负向门禁前不得启用 |
| README/SVG 状态看板 | **模板已提供、未启用** | 需要项目状态、看板策略和受审工作流 |
| 协调操作台 | **模板已提供、未启用** | 只支持刷新、通知测试和精确任务催办 |
| GitHub Issue + 钉钉通知 | **模板已提供、未启用** | 需要 Environment、Secrets 和项目通知映射 |
| Skill 自动清理 | **模板已提供、未启用** | 只创建受审清理 PR，不自动合并或直接删除 `main` 内容 |
| 成员 push 即时反馈 | **尚未实现** | 当前只能由 Coordinator 显式远端刷新；激活看板模板后可增加定时/手工受控刷新 |

当前 `.github/sop-system.json` 的关键事实：

```text
lifecycle: bootstrap
project_initialized: false
project_data_included: false
predevelopment_ac: true
development_de: false
dashboard: false
dashboard_actions: false
github_issue_notifications: false
dingtalk_notifications: false
remote_feedback: false
automatic_skill_cleanup: false
```

其中 `predevelopment_ac: true` 只表示 A–C 运行时可用，不表示仓库里已经存在活动项目、任务或 Gate。

## 必须理解的事实原则

```text
提醒不等于分发
拉取不等于接受
接受不等于提交
提交有效不等于赞同
正文确认不等于 Gate
Gate 批准不等于已经合并
合并不等于已经发布
AI 建议不等于人工授权
```

权威事实来自：

- 经确认写入的 assignment；
- 成员登记分支上的接受凭证；
- submission manifest、正文、哈希和精确 commit；
- human owner 对当前正文或开发提交的真实确认；
- 评审记录、来源台账和意见处理结果；
- Gate 决策、合并证据、祖先校验和冻结基线；
- 开发 PR、CI、非作者审查、发布和观察记录。

Issue、钉钉消息、README 看板和 AI 对话只是提醒或投影，不得反向覆盖这些事实。

## 谁负责什么

| 身份 | 主要职责 | 不得代替谁 |
|---|---|---|
| 仓库管理员 | 分支保护、Actions 权限、Environment、Secrets 和仓库安全设置 | 不代替成员或 Gate 责任人确认 |
| Coordinator | 初始化项目、登记成员、录入任务、收轮、汇总、准备 Gate、远端校验和状态投影 | 不代成员接单、提交或批准 |
| Member | 在本人登记分支接受并完成任务，保留内容、测试和确认凭证 | 不修改中央状态、其他成员证据或 Gate |
| human owner | 核对本人任务的精确正文/代码哈希和个人立场 | 不把提交确认当作 Gate 批准 |
| Gate 责任人 | 阅读评审包并作出真实业务、产品、技术、测试或专项决定 | 不用沉默或聊天表态代替正式决定 |
| 代码审核人 | 审查精确开发 commit、测试和风险 | 不批准审核后又变化的代码 |
| 发布/事故责任人 | 决定灰度、停止、回滚、修复和关闭 | 不把 AI 或 G4/G5 当作生产权限来源 |

同一个自然人可以承担多个身份，但每次操作都必须明确当前身份和责任边界。

## 常用术语

| 术语 | 通俗含义 |
|---|---|
| assignment | Coordinator 经预览和 Token 确认后签发的正式任务合同 |
| acceptance receipt | 成员在本人登记分支提交的接单凭证 |
| submission | 成员在任务允许目录内完成的正文、索引、确认和 manifest |
| human owner | 对该成员精确正文或代码提交作真实确认的人类负责人 |
| confirmation Token | 绑定当前预览内容的确认令牌；内容变化后旧 Token 失效 |
| runtime | 实际执行任务校验或开发治理的 CLI 版本，不等于发行包版本 |
| Gate | 由具备责任能力的人类基于评审包作出的阶段准入决定 |
| baseline | Gate 决定、精确合并和祖先校验完成后冻结的可信阶段基线 |
| projection | 看板、Issue 或钉钉等从正式事实生成的只读摘要/提醒 |

## 仓库里有什么

当前 bootstrap 仓库的简化结构：

```text
.
├─ ai-sop-coordinator-skill-v2.1.1/   # Coordinator 稳定发行包
├─ ai-sop-member-skill-v2.1.0/        # Member 稳定发行包
├─ .github/
│  ├─ scripts/                        # 仓库受信任运行时与扩展
│  ├─ tests/                          # 仓库级校验测试
│  ├─ sop-templates/                  # 尚未激活的配置和工作流模板
│  ├─ workflows/
│  │  └─ sop-system-validate.yml      # 当前唯一启用的工作流
│  ├─ sop-system.json                 # 生命周期和 capability 开关
│  ├─ sop-runtime-lock.json           # 版本、build ID、来源和 SHA-256
│  ├─ sop-skill-retention.json        # Skill 保留策略
│  └─ …                               # 启动、通知、清理、限制及不可变审计
├─ docs/
│  ├─ getting-started.md              # 新手引导
│  ├─ system-usage-guide.md           # 完整操作说明
│  └─ development-sop.md              # 开发交付流程
└─ README.md
```

当前没有：

- `sop/`：没有项目、成员、任务、提交、Gate 或基线事实；
- `dashboard/`：没有项目看板；
- `projectcode/`：没有业务代码。

在 bootstrap 状态提前创建这些项目目录会导致系统校验失败。真实项目初始化和 capability 激活应在同一个完整、受审的 PR 中完成。

## Skill 包与任务运行时

包版本和任务运行时版本是两个不同维度。

| 用途 | 包版本 | 运行时版本 | 当前状态 |
|---|---|---|---|
| Coordinator 统一发行包 | 2.1.1 | — | stable |
| Member 统一发行包 | 2.1.0 | — | stable |
| A–C Coordinator | 包含于 Coordinator 2.1.1 | 1.8.5 | 已安装 |
| A–C Member | 包含于 Member 2.1.0 | 1.8.1 | 已安装 |
| 历史 A–C Member 校验 | 包含于 Member 2.1.0 | 1.8.0 legacy | 仅兼容历史任务 |
| D–E Coordinator | 包含于 Coordinator 2.1.1 | 2.0.0 | 禁用 |
| D–E Member | 包含于 Member 2.1.0 | 2.0.0 | 禁用 |

运行时锁会校验精确 version、build ID、来源文件和 SHA-256。成员读取任务包时也必须检查任务要求的 Member 版本与 build ID；版本不匹配时应停止，并安装或切换到 assignment 精确绑定且仓库确认的发行包。不得笼统升级到“最新版”，也不得绕过校验。

安装个人 Skill 时分别阅读：

- [Coordinator 安装与使用](ai-sop-coordinator-skill-v2.1.1/USAGE.zh-CN.md)
- [Member 安装与使用](ai-sop-member-skill-v2.1.0/USAGE.zh-CN.md)

## 使用前准备

最低环境要求：

- Git；
- Python 3.10 或更高版本（当前发行包声明的最低版本）；
- 能访问团队 GitHub 仓库的账号；
- Coordinator 和每名 Member 使用独立 clone 或 worktree；
- 每名成员使用自己的 Git 身份和唯一登记分支；
- 受保护的 `main`，禁止绕过 PR、审核和 CI；
- 如需通知，再单独配置 GitHub Environment 与 Secrets。

系统 Python 运行时只使用标准库，不需要额外安装 Python 包。

本 README 的命令示例主要采用 Windows PowerShell 写法。Linux/macOS 使用 `python3`，并把 PowerShell 的反引号续行改为对应 shell 写法；完整命令说明见 [系统使用指南](docs/system-usage-guide.md)。

## 5 分钟检查系统

克隆并进入仓库：

```powershell
git clone https://github.com/xuhao666-pro/test.git
cd test
```

运行只读系统校验：

```powershell
$env:PYTHONUTF8 = "1"
python .github/scripts/sop_system_validate.py
```

成功输出应包含：

```text
SOP system validation passed (lifecycle=bootstrap).
```

这只证明：

- 必需发行包集合、manifest、关键 runtime 资产和锁定关系满足校验规则；
- runtime lock 与受信任文件匹配；
- bootstrap capability 和工作流边界正确；
- 没有发现被规则命中的敏感信息或非法项目目录。

它不证明：

- 项目已经初始化；
- 需求已经录入；
- 成员已经接单或提交；
- 看板或通知已经启用；
- 任一 Gate 已经通过；
- 代码已经获准开发或发布。

也可以在 GitHub 页面运行：

```text
GitHub → Actions → SOP system validation → Run workflow → main
```

该工作流在 `main` push、Pull Request 和手工触发时运行，权限只有 `contents: read`。

## 如何启动一个真实项目

### 1. 选择接入方式

新仓库：

- 以本仓库作为空白 SOP 工作区；
- 初始化项目事实后，再按团队方案导入或关联真实代码；
- 记录代码来源 URL、分支、精确 commit 和同步策略。

已有业务代码仓库：

- 把当前 SOP 发行包、运行时、模板、锁文件和文档迁入业务仓库；
- 保留现有业务代码、Git 历史、CI、Jenkins、部署和发布门禁；
- 不复制旧项目的 `sop/`、看板、成员映射、Secrets 或任务事实；
- 不复制绑定其他 Git 历史的 `.github/skill-cleanup/history/` 审计；
- 先只读盘点现有 `.github/workflows/` 和根目录 `sop/`、`dashboard/`、`projectcode/` 是否与 bootstrap 规则冲突；
- 只有目标仓库没有其他 active workflows 和上述根路径冲突时，才能直接保持 `bootstrap` 并运行未改造的系统校验；
- 记录迁移来源 commit 和业务代码最新可信 `main`；
- 再用独立 PR 初始化当前项目并激活所需 capability。

已有代码不需要为了 SOP 被强制移动到 `projectcode/`。SOP 应适配真实仓库结构，不能为通过校验删除用户代码或原有门禁。

如果目标仓库已有产品 GitHub Actions，或业务本身使用了根 `dashboard/`、`projectcode/`、`sop/`：

- 不得为通过 bootstrap 校验删除或移动用户资产；
- 在一个原子、受审 PR 中建立真实 `sop/project-state.yaml` 并切换为 `active`，再按 active 规则验证；或
- 先正式修改并测试 bootstrap workflow allowlist / 路径语义，再迁移；
- 不把半完成、当前校验必然失败的中间状态合入 `main`。

### 2. 先准备真实输入

必须由人类明确提供并核对：

- 项目 ID、项目名称；
- Coordinator ID；
- 全新需求原文或附件来源；
- 执行模式：`standard` 或 `lightweight`；
- 协作模型：`role-based` 或 `collective-participation`；
- Gate 策略：`accountable-members` 或 `all-participants`；
- 风险等级：`R0`、`R1`、`R2` 或 `R3`；
- 当前真实开发状态；
- 每名成员的稳定 member ID、human owner 和唯一分支；
- 如接入已有代码：代码来源、精确 commit 和原有合并/发布门禁。

R2/R3 必须使用标准模式，并登记真实专项责任人。

### 3. 安装并调用 Coordinator Skill

按 [Coordinator 使用说明](ai-sop-coordinator-skill-v2.1.1/USAGE.zh-CN.md) 安装后，在对话中明确要求使用 `ai-sop-coordinator`，并逐项确认上述输入。

不要根据历史项目、旧成员或示例值补全缺失信息。

### 4. 初始化项目事实

先从最新可信 `main` 创建受审初始化分支，不要直接在 `main` 工作树生成项目事实：

```powershell
git fetch origin
git switch main
git pull --ff-only
git switch -c "sop/initialize-project" main
```

然后运行初始化。下面只展示命令框架，所有占位符都必须替换为当前项目的真实确认值：

```powershell
python .github/scripts/sop_coordinator_cli.py init-project . `
  --project-id "<project-id>" `
  --project-name "<project-name>" `
  --coordinator-id "<coordinator-id>" `
  --execution-mode "<standard|lightweight>" `
  --collaboration-model "<role-based|collective-participation>" `
  --gate-confirmation-policy "<accountable-members|all-participants>" `
  --risk-level "<R0|R1|R2|R3>" `
  --real-development-status "<真实状态>" `
  --member "<member-id>:<human-owner>" `
  --member-branch "<member-id>:sop/member/<member-id>"
```

每名成员分别增加一组 `--member` 和 `--member-branch`。初始化后立即检查：

```powershell
python .github/scripts/sop_coordinator_cli.py status .
```

初始化命令只建立仓库内项目事实，不会替你：

- 创建或保护 GitHub 分支；
- 安装个人 Skill；
- 配置 Environment 或 Secrets；
- 激活看板、通知或操作台；
- 创建真实业务需求；
- 自动创建远端成员分支。

### 5. 通过独立 PR 激活

在一个完整受审 PR 中完成：

1. 检查初始化后的 `sop/` 只包含本项目事实；
2. 登记成员、唯一分支和 G1–G3 责任能力；
3. 如接入已有代码，登记精确来源和基线；无代码项目明确记录为不适用；
4. 从示例创建看板与通知配置；
5. 只复制准备启用的加固工作流；
6. 将 lifecycle 切换为 `active`，只开启已经完整配置和审核的 capability；
7. 在真实 G3 完成前，`development_de` 和两个 2.0.0 开发运行时的 `enabled` 必须保持 `false`；
8. 运行系统校验；
9. 通过受保护 PR 合入 `main`。

完整步骤见 [新项目启动说明](.github/SOP-BOOTSTRAP.md)。

### 6. 创建真实远端成员分支

`init-project` 只登记分支名，不会自动在 GitHub 创建分支。初始化 PR 合入后，Coordinator 应从最新可信 `main` 为每名成员创建唯一登记分支：

```powershell
git fetch origin
git switch main
git pull --ff-only
git switch -c "sop/member/<member-id>" main
git push --set-upstream origin "sop/member/<member-id>"
git switch main
```

如果远端分支已经存在，不要重复创建或强推；先确认它来自正确基线。之后成员才能在独立 clone/worktree 中跟踪本人分支、检查 assignment 并接单。

正确顺序：

```text
初始化 PR 合入
→ 从最新可信 main 创建并 push 每名成员登记分支
→ 成员建立独立工作区并跟踪本人分支
→ Coordinator 正式分发任务
→ 成员检查并接受
```

<a id="ac-workflow"></a>

## A–C 任务、收轮与 Gate

下面使用的是 A–C 预开发 CLI。真实通过 G3 后的代码任务、审查、集成和 G4/G5 使用独立的开发运行时，见 [开发交付 SOP](docs/development-sop.md)。

### A–C 单个成员任务

单个 assignment 的事实链：

```text
协调者录入任务
→ 生成预览与 Token
→ 人工核对并确认同一份预览
→ 写入正式 assignment
→ 成员检查身份、分支、基线和版本
→ 成员提交接受凭证并 push
→ 协调者从远端观测为“已接受”
→ 成员完成内容、索引和测试
→ human owner 确认精确正文哈希与个人立场
→ 成员 validate、submit、commit、push
→ 协调者远端校验
```

一个成员提交有效，不代表整个轮次已经完成，也不代表该成员赞同候选结论。

#### Coordinator 的关键动作

- 从真实需求或批准基线录入任务；
- 首次运行只生成预览和 confirmation Token；
- 用户修改任何字段后重新预览，不复用旧 Token；
- 正式分发后不原地改 assignment，使用新版本或替代轮次；
- 成员 push 后从登记远端 ref 校验接受凭证和提交；
- 保留反对、质询和保留意见，不把 `valid` 自动写成 `confirm`。

远端刷新示例：

```powershell
python .github/scripts/sop_coordinator_cli.py refresh-project-state . `
  --remote origin `
  --fetch `
  --validate-remote `
  --member-cli .github/scripts/sop_member_cli.py
```

#### Member 的关键动作

成员必须在本人登记分支和独立工作区执行：

```powershell
$memberId = "<member-id>"
$branch = "sop/member/$memberId"

git fetch origin

# 本地还没有登记分支时：
git switch --track -c $branch "origin/$branch"

# 本地已经存在登记分支时，改用：
# git switch $branch
# git pull --ff-only origin $branch

git merge --ff-only origin/main
git branch --show-current
```

最后一条必须显示本人登记分支。若跟踪、拉取或 `merge --ff-only` 失败，立即停止并联系 Coordinator。

然后检查和接受 assignment：

```powershell
python .github/scripts/sop_member_cli.py workspace-check `
  "<assignment-path>" --member-id "<member-id>" --fetch

python .github/scripts/sop_member_cli.py inspect `
  "<assignment-path>" --member-id "<member-id>" --fetch

python .github/scripts/sop_member_cli.py accept-assignment `
  "<assignment-path>" --member-id "<member-id>"
```

接受凭证需要 commit 并 push 到本人登记分支。随后成员才能初始化、完成、确认和提交任务：

```text
init
→ 编辑任务允许的 submission 目录
→ index-content
→ prepare-confirmation
→ human owner 真实确认
→ confirm-submission
→ validate
→ submit
→ commit/push 本人分支
```

成员不得修改 assignment、中央状态、Gate、基线、看板或其他成员目录。

分支、成员身份、任务版本、基线、runtime、输入或 human owner 任一不一致时，成员必须停止并联系 Coordinator；不得自行 reset、rebase、强推或修改 assignment。

### 一轮团队工作怎样完成

```text
全部应参与成员分别完成独立 assignment
→ Coordinator 从登记远端分支校验
→ 处理缺交、无效、反对、质询和保留意见
→ 关闭独立轮次
→ 发布 submission-index
→ 创建指向已关闭轮次的 shared-review
→ 成员分别提交评审立场
→ 关闭评审轮次
→ 主笔/Coordinator 形成候选产物和来源台账
```

shared review 不是让所有人覆盖同一份原稿，也不是让每个人重复审查四份独立文档。成员共同评审的是冻结的 submission index、完整 summary 和候选产物。

### G1–G3 怎样完成

```text
完成阶段要求与来源覆盖
→ 生成并人工撰写 Gate 评审包
→ 校验评审包和来源指纹
→ Gate 责任人作出真实决定
→ approve-gate 进入 merge-pending
→ 按冻结 commit 合并全部有效成员分支
→ 验证这些 commit 均为 main 祖先
→ 冻结基线
→ 确认稳定 Member Skill
→ 才能分发下一阶段任务
```

Gate 材料或来源变化后必须重新准备。合并冲突、分支缺失、审核后 commit 变化或祖先校验失败时保持 `merge-pending`，不得手工标记完成。

## GitHub Actions 与模板

### 当前已启用

| 工作流 | 触发 | 权限 | 用途 |
|---|---|---|---|
| `sop-system-validate.yml` | `main` push、PR、手工运行 | `contents: read` | 校验 bootstrap/active 边界、发行包、运行时锁、测试和敏感信息 |

### 当前仅位于模板目录

| 模板 | 激活后的用途 | 重要边界 |
|---|---|---|
| `sop-dashboard-actions.yml` | 启用后可手工刷新状态、测试通知、催办精确任务 | 不能接单、分发、关轮、过 Gate、合并、部署或回滚 |
| `sop-readme-dashboard.yml` | 刷新已有 `project-state` 并生成 README/SVG 看板 | 当前模板会 commit 并直推 `main`，没有内置 PR 模式 |
| `sop-notifications.yml` | 创建/更新 Assignment Issue 并发送钉钉 | Issue 和钉钉不进入事实链 |
| `sop-skill-cleanup.yml` | 启用后生成 Skill 清理计划和受审 PR | 不自动合并，不直接删除 `main` |
| `sop-skill-cleanup-validate.yml` | 校验清理 PR、Token、包引用和审计历史 | 只读验证 |

模板文件位于 `.github/sop-templates/workflows/`，本身不会执行。复制为 active workflow 后，仍须满足对应事件、默认分支、lifecycle/capability guard、Environment 和权限条件，副作用 job 才会真正运行。

当前看板模板只实现受控机器人直推 `main`。如果分支保护或仓库策略不允许：

- 不得原样启用会写入的 `refresh-state`；
- 先实现并评审一个 PR 变体；或
- 由 Coordinator 在受审分支手工刷新并提交中央投影。

## 看板和操作台

项目激活、`dashboard=true`、加固工作流安装且状态策略和写入路径可用后，看板可展示：

- 项目、当前阶段、阶段进度和下一 Gate；
- Git 是否连接、主分支和合并策略；
- G1–G3 基线状态；
- 当前任务的任务类型、成员、接受状态、assignment ID、校验状态和提交时间；
- 最高风险、阻塞项和刷新时间。

任务卡默认只展示当前范围的前 8 项，其余任务显示隐藏数量。完整事实仍应查看 assignment、acceptance、submission manifest、精确 commit 和 Gate 文件。

“已接受”只能来自成员登记分支上的有效 acceptance receipt，并由协调端观测。clone、fetch、pull、打开 Issue 或收到钉钉消息都不能显示为已接受。

操作台只提供三类低风险动作：

- `refresh-state`：刷新远端事实和看板；
- `notification-test`：验证通知通道配置；
- `task-reminder`：催办一个精确 assignment。

它不是通用管理后台，不能代替正式 CLI、PR、Gate 或生产控制。

其中 `refresh-state` 复用当前看板工作流的写入方式；未实现 PR 变体前，它会尝试受控直推 `main`。

## GitHub Issue 与钉钉通知

启用前需要 GitHub Environment：

```text
sop-notifications
```

在 Environment 中设置：

```text
DINGWEBHOOK
DINGSECRET
DING_MEMBER_MAP
```

只在 GitHub Settings 中保存真实值。README、配置示例、commit、PR、Issue、日志和聊天中都不得出现真实 webhook、secret、手机号或成员私密映射。

正常通知链：

```text
可信 main 中的正式任务/状态变化
→ 创建或更新 Assignment Issue
→ 发送钉钉提醒
→ 写入幂等标记
```

通知成功只说明消息送达，不表示成员已接受、已提交或赞同，也不表示 Gate 已通过。

详见 [通知说明](.github/SOP-NOTIFICATIONS.md)。

## 如何验证完整系统

系统校验：

```powershell
python .github/scripts/sop_system_validate.py
```

Coordinator 发行测试：

```powershell
python -m unittest discover `
  -s ai-sop-coordinator-skill-v2.1.1/tests `
  -p "test_*.py"
```

Member 发行测试：

```powershell
python -m unittest discover `
  -s ai-sop-member-skill-v2.1.0/tests `
  -p "test_*.py"
```

通知和仓库扩展测试：

```powershell
python .github/scripts/test_sop_issue_notifier.py
python .github/scripts/test_sop_dingtalk_notifier.py
python -m unittest discover -s .github/tests -p "test_*.py"
```

GitHub Actions 会运行 Coordinator、Member、通知和仓库扩展测试，编译检查受信任 Python 运行时，并要求测试后不存在 tracked diff 或任何 untracked 文件。具体测试数量以当前代码和工作流输出为准。

## 安全与权限边界

- 禁止把 Secrets、真实 webhook、手机号或访问令牌提交到仓库；
- 成员和人工操作不得绕过保护直接 push `main`，应使用受审分支和 PR；
- 如启用看板机器人更新中央投影，只有仓库策略明确允许时才可使用现有直推模板；否则必须先实现受审 PR 变体，或由 Coordinator 在受审分支人工刷新并提交；
- 禁止 AI 代替成员接受任务、代替 human owner 确认，或代替 Gate、代码审核、发布和事故责任人批准；
- 禁止把成员提交确认解释为 Gate、合并或发布许可；
- 禁止越过 G1–G3 阶段边界启动后续受控工作；
- 禁止 AI 独立部署生产、修改密钥、删除数据、回滚数据库或执行高风险修复；
- 禁止成员直接修改中央 `project-state.yaml`；
- 禁止为了通过校验而伪造成员、任务、意见、Gate 或历史记录。
- 分支、身份、基线、版本、确认或权限不一致时停止，联系仓库管理员或 Coordinator，不自行改写证据历史。

## 常见问题

### 为什么仓库里有工作流文件，Actions 页面却只有一个工作流？

因为除 `sop-system-validate.yml` 外，其余文件都在 `.github/sop-templates/workflows/`，目前只是模板。项目初始化、配置和 capability 激活完成后，才能通过受审 PR 复制到 active workflows。

### 为什么系统校验成功，却看不到项目、任务或看板？

当前校验的是 bootstrap 系统完整性。`project_initialized=false` 是正常状态，不代表文件丢失。

### 成员已经 pull 任务，为什么看板不能显示“已接受”？

pull 不是可审计的接受事实。成员必须运行 `accept-assignment`，commit/push 接受凭证，并由协调者从登记远端分支观测。

### 钉钉提醒已经成功，为什么任务仍然是 missing？

提醒只负责送达，不改变接受或提交状态。接受凭证只更新“已接受”子状态；`missing`、`not-submitted` 或校验状态只有在精确 submission 被远端校验后才会变化。

### 为什么 Member 包是 2.1.0，任务运行时却是 1.8.1？

2.1.0 是统一发行包版本，1.8.1 是其中的 A–C Member 运行时。包版本和运行时版本不是同一字段。

### Skill 版本不匹配时会自动升级吗？

不会。版本预检会提醒或阻塞。成员应安装或切换到 assignment 精确绑定且仓库确认的发行包，不得默认安装“最新版”，完成后重新检查任务。

### 为什么成员 push 后中央状态没有立刻变化？

当前没有 `sop-member-signal.yml` 和 `sop-member-feedback.yml` 即时反馈工作流。协调者需要运行远端刷新，或在项目激活后使用受控的定时/手工看板刷新。

### 为什么 D–E 文件已经存在，却不能直接进入开发？

发行包携带 D–E 运行时是为了版本完整性，不代表 capability 已启用。必须真实完成 G3、证据合并、祖先校验、基线冻结、稳定 Skill 确认和开发负向门禁。

### 自动 Skill 清理会直接删除旧版本吗？

不会。它先生成计划和确认 Token，再创建受审 PR；清理提交和审计历史必须通过校验，不能绕过主干保护。

## 文档导航

| 我想做什么 | 阅读 |
|---|---|
| 第一次了解系统 | [第一次使用 AI SOP](docs/getting-started.md) |
| 查看完整命令、流程和 GitHub 操作 | [AI SOP 系统完整使用说明](docs/system-usage-guide.md) |
| 初始化项目并激活工作流 | [新项目启动说明](.github/SOP-BOOTSTRAP.md) |
| 了解当前不能做什么 | [当前限制](.github/CURRENT-LIMITATIONS.md) |
| 进入开发、审查和发布阶段 | [开发交付 SOP](docs/development-sop.md) |
| 配置 GitHub Issue 和钉钉 | [通知说明](.github/SOP-NOTIFICATIONS.md) |
| 管理和清理 Skill 发行包 | [Skill 清理说明](.github/SOP-SKILL-CLEANUP.md) |
| 查看模板工作流和配置 | [SOP 模板说明](.github/sop-templates/README.md) |

## 推荐的第一次成功闭环

不要第一天就尝试完整开发和发布。建议先完成一个真实、低风险的 A 阶段任务闭环：

1. 用真实输入初始化项目；
2. 注册两名或以上真实成员及唯一分支；
3. 通过预览和 Token 正式分发一项需求分析任务；
4. 让成员检查并提交接受凭证；
5. 让成员完成正文、索引和 human owner 确认；
6. 从远端校验提交；
7. 关闭独立轮次并开展共享评审；
8. 形成候选需求合同和 G1 人工评审包；
9. 记录真实决定，不用测试数据冒充项目事实。

完成这条 A 阶段链后，可以按配置逐项启用看板或通知，并继续完成 B、C。D–E 必须等到真实 G3、成员证据合并、`main` 祖先校验、基线冻结、稳定 Skill 确认和开发负向门禁全部完成后，再通过独立受审变更启用。
