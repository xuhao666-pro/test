# 第一次使用 AI SOP

> 面向从未接触过本系统的协调者、成员和审核人。  
> 先读第 1–4 节约 5 分钟；按角色完成第一次操作约 25–40 分钟。  
> 完整规则见：[AI SOP 系统完整使用说明](system-usage-guide.md)。

## 1. 先记住这八句话

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

如果只记住一件事，请记住：

> 系统通过文件、精确 Git commit 和人工决定记录事实。GitHub Issue、钉钉消息和状态看板只负责提醒或展示。

## 2. 当前仓库处于什么状态

当前仓库仍是 `bootstrap`，即“系统已经装好，但具体项目还没有初始化”。

现在的正常表现：

- 有 Coordinator 和 Member 两个 Skill 发行包；
- 有 `.github/scripts/` 受信任脚本；
- 有 `.github/sop-templates/` 工作流模板；
- 没有真实项目的 `sop/`、`dashboard/`、`projectcode/`；
- 没有成员、任务、Gate 或项目状态；
- GitHub Actions 当前只有 `SOP system validation` 真正可运行。

这不是文件丢失。项目没有正式激活前，模板目录中的看板、操作台、通知和清理工作流都不会运行。

## 3. 先确认你是哪种身份

| 身份 | 你负责什么 | 你不能做什么 |
|---|---|---|
| 协调者 | 初始化项目、登记成员、预览和分发任务、远端校验、收轮、准备 Gate | 代成员接受、代成员确认、代人工批准 Gate |
| 成员 | 在自己的分支接受并完成精确任务，提交真实内容和个人立场 | 修改中央状态、Gate、基线或其他成员提交 |
| human owner | 核对成员的精确正文哈希和个人立场 | 把正文确认当作 Gate 批准 |
| Gate 责任人 | 阅读评审包并作出真实人工决定 | 用沉默、聊天表态或 AI 建议代替正式决定 |
| 代码审核人 | 审查精确开发 commit 和测试证据 | 审核后仍允许 commit 被悄悄改写 |
| 发布/交付负责人 | 决定是否允许灰度、是否关闭交付 | 把系统建议当作生产授权 |

协调者和成员必须是不同的事实责任链。即使同一个自然人兼任多个角色，也要明确当前是在以哪个角色操作。

## 4. 三分钟认识常用名词

| 名词 | 通俗解释 |
|---|---|
| assignment | 正式任务包；它定义谁做、做什么、输入输出和验收条件 |
| member branch | 成员专用分支，A–C 默认是 `sop/member/<member-id>` |
| acceptance receipt | 接受凭证；证明成员明确接单 |
| submission | 成员提交目录和完成报告 |
| human owner confirmation | 对精确正文哈希和个人立场的人工确认 |
| round | 一轮独立任务或共享评审 |
| shared-review | 独立轮关闭后的新评审轮，成员分别提交评审证据 |
| project-state | 中央状态摘要，不是原始事实 |
| Gate | G1–G5 人工决策点 |
| baseline | G1–G3 完整完成后冻结的阶段基线，或 G5 关闭时冻结的交付事实；G4 不冻结新代码基线 |
| Token | 绑定一次预览的确认值；输入变化后旧 Token 失效 |

## 5. 协调者：第一次启动项目

### 5.1 安装 Coordinator Skill

第一次操作前，先按以下说明安装协调者 Skill：

- [完整使用说明：安装个人 Skill](system-usage-guide.md#62-安装个人-skill)

安装后重新打开 Codex 会话，确认加载的是仓库当前稳定发行包。

### 5.2 准备独立工作分支

不要直接在 `main` 上初始化。先从最新 `main` 创建受审分支：

```powershell
git fetch origin
git switch main
git pull --ff-only
git switch -c "sop/initialize-project"
```

### 5.3 确认系统模板完整

在仓库根目录运行：

```powershell
python .github/scripts/sop_system_validate.py
```

当前预期：

```text
SOP system validation passed (lifecycle=bootstrap).
```

如果失败，停止初始化，先解决系统完整性问题。

### 5.4 一次性收齐真实项目输入

必须由真实负责人确认：

- 项目 ID；
- 项目名称；
- 协调者 ID；
- 新需求原文和附件来源；
- 执行模式：`standard` 或 `lightweight`；
- 协作模型：`role-based` 或 `collective-participation`；
- Gate 策略：`accountable-members` 或 `all-participants`；
- 一个明确风险等级：`R0`、`R1`、`R2` 或 `R3`；
- 当前真实开发状态；
- 每名成员的 ID、human owner 和唯一分支；
- G1–G3 人工责任能力；
- R2/R3 的专项责任人。

不知道的内容必须询问，不能从旧项目或 AI 推断。

“风险等级：R0/R1/R2/R3”不是有效结果，必须选一个。

没有新需求时可以记录“暂无，等待录入”，但不能为了测试流程虚构正式任务。

### 5.5 初始化并检查

先看精确参数：

```powershell
python .github/scripts/sop_coordinator_cli.py init-project --help
```

最小命令结构如下。每个值必须来自刚才确认的真实输入：

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

每名成员分别增加一组 `--member` 和 `--member-branch`，不要照抄示例风险等级或成员值。

然后检查：

```powershell
python .github/scripts/sop_coordinator_cli.py status .
```

确认生成内容只包含当前项目的真实事实。

### 5.6 激活 GitHub 自动化

项目激活不是复制一个工作流就完成。

先由有权限的仓库管理员在 GitHub Settings 中完成外部设置：

1. 创建 GitHub Environment `sop-notifications`；
2. 在该 Environment 中配置 `DINGWEBHOOK`、`DINGSECRET`、`DING_MEMBER_MAP`；
3. 确认 Actions 所需的 Issue、内容和 PR 权限。
4. 决定看板投影如何进入受保护 `main`：
   - 允许受控 GitHub Actions bot 更新投影文件；或
   - 使用受审 PR/人工中央快照。

Secret 值绝不能进入 commit 或 PR。

随后在同一个完整受审 PR 中完成仓库内变更：

1. 初始化 `sop/`；
2. 登记成员、分支和 G1–G3 责任能力；
3. 导入并记录真实代码的精确来源 commit；
4. 创建 `sop/dashboard-policy.yaml`；
5. 创建 `sop/notification-config.yaml`；
6. 复制准备启用的加固工作流；
7. 把系统生命周期切换为 `active`；
8. 只打开已经完整配置的 capability；
9. 运行系统校验；
10. 通过受保护 PR 合入 `main`。

当前必须保持：

- `remote_feedback: false`
- G3 前 `development_de: false`

不要把半完成的激活状态推入 `main`，也不要使用旧兼容命令的 `--force` 覆盖加固工作流。

仓库内激活变更全部完成并通过本地校验后：

```powershell
git branch --show-current
git status --short

# 逐个填写并暂存已经人工核对的初始化路径，不使用 git add .
git add -- "<已核对路径-1>" "<已核对路径-2>"

git diff --cached --stat
git diff --cached
git commit -m "sop: initialize project"
git push --set-upstream origin "sop/initialize-project"
```

随后在 GitHub 创建从 `sop/initialize-project` 指向 `main` 的 PR，等待系统校验和人工审核。不要直接推送 `main`。

详细步骤见：

- [完整使用说明：从 bootstrap 激活为真实项目](system-usage-guide.md#7-从-bootstrap-激活为真实项目)

### 5.7 创建实际远程成员分支

`init-project` 和 `add-member` 只登记分支名，不会自动创建远程 Git 分支。项目激活提交合入后，协调者必须从最新可信 `main` 为每名成员创建并 push 登记分支。

每名成员执行一次，替换 `$branch`：

```powershell
git fetch origin
git switch main
git pull --ff-only

$branch = "sop/member/xiaotan"
git switch -c $branch main
git push --set-upstream origin $branch
git switch main
```

如果远端分支已经存在，不要重复创建或强推；先检查它是否来自正确的可信基线。

## 6. 协调者：第一次发布任务

### 6.1 先准备真实任务

正式任务至少需要：

- 任务来源；
- 目标；
- 范围内事项；
- 明确不做什么；
- 输入；
- 交付物；
- 验收标准；
- 负责人和参与成员；
- Skill/runtime 要求。

系统不会替协调者创造这些内容。

### 6.2 任务必须经过两次命令

```text
第一次
完整参数，不带 --confirm-dispatch
→ 只生成预览和 Token

人工核对
成员、目标、范围、输入、交付物、验收、版本

第二次
完全相同参数 + --confirm-dispatch <Token>
→ 才正式写入 assignment
```

任一字段变化都要重新生成预览。不能修改参数后继续使用旧 Token。

已正式分发的任务不能原地编辑。需要修改时，签发新版本或使用 `supersede-round` 建立替代关系。

### 6.3 分发后告诉成员什么

给成员的开始信息应包含：

- assignment ID；
- assignment 文件路径；
- member ID；
- 登记分支；
- 要求的 Member Skill/runtime；
- 输入位置；
- 输出目录；
- 截止或停止条件。

钉钉或 Issue 只负责把这些信息送到成员面前，不代表成员已经接受。

## 7. 成员：第一次接任务

### 7.1 准备自己的工作区

每名成员必须：

- 使用自己的 clone 或 worktree；
- 使用自己的 Git 身份；
- 只使用登记成员分支；
- 不与其他成员共用工作区；
- 按[个人 Skill 安装说明](system-usage-guide.md#62-安装个人-skill)安装仓库要求的 Member Skill；
- 从可信 `main` 读取 assignment。

A–C 默认分支：

```text
sop/member/<member-id>
```

第一次切换本人分支：

```powershell
$memberId = "xiaotan"
$branch = "sop/member/$memberId"

git fetch origin

# 本地已有该分支时
git switch $branch
git pull --ff-only origin $branch

# 本地没有、但远端已登记该分支时，改用：
# git switch --track -c $branch "origin/$branch"

# 确保最新可信 main 可以快进到当前成员分支
git merge --ff-only origin/main

git branch --show-current
```

最后一条必须显示本人登记分支，不能是 `main` 或其他成员分支。

如果 `pull --ff-only` 或 `merge --ff-only origin/main` 失败，立即停止并联系协调者。成员不得自行使用 rebase、reset、强推或普通 merge 改写登记证据分支。

如果本地和远端都不存在登记分支，同样停止并联系协调者创建或核实；不要从任意本地 HEAD 自行建立同名分支。

收到钉钉、打开 Issue、clone、fetch、pull 都不等于接单。

### 7.2 先检查，再接受

在成员工作区中设置实际路径：

```powershell
$assignment = "sop/stages/01-requirement-contract/dispatch/A-01-example.yaml"
```

检查：

```powershell
python .github/scripts/sop_member_cli.py workspace-check `
  $assignment --member-id $memberId --fetch

python .github/scripts/sop_member_cli.py inspect `
  $assignment --member-id $memberId --fetch
```

重点核对：

- assignment ID 和版本；
- 当前成员身份；
- 登记分支；
- 基线；
- Skill/runtime 的精确 version 与 build ID；
- 输入是否存在；
- 范围和交付物是否清楚。

任何一项不一致，都先停止并联系协调者。

### 7.3 明确接单

```powershell
python .github/scripts/sop_member_cli.py accept-assignment `
  $assignment --member-id $memberId
```

随后：

1. 从命令输出复制实际接受凭证路径；
2. 用 `git status --short` 确认只生成本人凭证；
3. commit；
4. push 到本人登记分支。

```powershell
$acceptance = "<复制 accept-assignment 输出的实际凭证路径>"

git branch --show-current
git status --short
git add -- $acceptance
git commit -m "sop: accept assigned task"
git push origin $branch
```

如果当前分支不是 `$branch`，不要提交。

只有协调端从精确远端分支校验到有效接受凭证后，看板才能显示“已接受”。

接受任务不代表已经完成任务。

### 7.4 初始化并完成任务

```powershell
python .github/scripts/sop_member_cli.py init `
  $assignment --member-id $memberId
```

`init` 会输出本次实际 submission 路径。复制该返回值，不能照抄示例或自行拼接：

```powershell
$submission = "<复制 init 输出的实际 submission 路径>"
```

只编辑任务包允许的提交目录。不要修改：

- assignment；
- 中央 `project-state.yaml`；
- aggregation；
- Gate；
- baseline；
- README/SVG 看板；
- 其他成员目录。

完成 `main-output.md` 和任务要求的文件后，运行内容索引：

```powershell
python .github/scripts/sop_member_cli.py index-content `
  $submission `
  --assignment $assignment `
  --member-id $memberId
```

### 7.5 让登记 human owner 确认正文

先由真实成员和登记 human owner 明确个人立场，再生成确认预览。AI 不能把 `confirm` 当作默认答案：

```powershell
$position = "<confirm|oppose|question|reserve>"
$positionStatement = "<本人真实说明>"

python .github/scripts/sop_member_cli.py prepare-confirmation `
  $submission `
  --assignment $assignment `
  --member-id $memberId `
  --position $position `
  --position-statement $positionStatement
```

把以下内容完整展示给登记的 human owner：

- 当前正文；
- 正文哈希；
- 个人立场；
- 确认 Token。

可选立场：

- `confirm`
- `oppose`
- `question`
- `reserve`

后三种仍可成为有效提交，但会进入后续意见处理，不能显示为“赞同”。

human owner 真实确认后，使用预览返回值：

```powershell
$humanOwner = "<登记的 human owner>"
$documentHash = "<预览返回的正文哈希>"
$confirmationToken = "<预览返回的 Token>"

python .github/scripts/sop_member_cli.py confirm-submission `
  $submission `
  --assignment $assignment `
  --member-id $memberId `
  --confirmed-by $humanOwner `
  --document-hash $documentHash `
  --confirmation-token $confirmationToken
```

AI、协调者或其他成员不能代替 human owner 回复。

正文变化后旧哈希和旧确认立即失效，必须重新准备和确认。

### 7.6 校验、冻结并 push

```powershell
python .github/scripts/sop_member_cli.py validate `
  $submission `
  --assignment $assignment `
  --member-id $memberId

python .github/scripts/sop_member_cli.py submit `
  $submission `
  --assignment $assignment `
  --member-id $memberId
```

然后只暂存本次 submission，commit 并 push 到本人登记分支：

```powershell
git branch --show-current
git status --short
git add -- $submission
git commit -m "sop: submit assigned task"
git push origin $branch
```

如果 `git status` 还显示 assignment、中央状态、Gate、基线或其他成员文件被修改，先停止并处理越界文件，不要一起提交。

含义：

- `validate`：机械校验；
- `submit`：冻结本次个人贡献；
- push：让协调者可以从远端读取。

以上都不代表团队已经收轮、Gate 已通过或内容已经合入 `main`。

## 8. 协调者：怎样看到成员结果

成员在聊天中说“已提交”不是系统事实。成员 push 后，协调者运行：

```powershell
python .github/scripts/sop_coordinator_cli.py refresh-project-state . `
  --remote origin `
  --fetch `
  --validate-remote `
  --member-cli .github/scripts/sop_member_cli.py
```

它会从登记成员远端分支校验：

- 接受凭证；
- submission manifest；
- 精确 commit；
- human owner confirmation；
- 正文哈希；
- Skill/runtime；
- 文件范围和任务合同。

中央 `project-state.yaml` 和看板只是该结果的投影。不要根据聊天消息手工改数字。

## 9. 独立提交、共享评审和收轮

正确理解：

```text
成员分别完成独立任务
→ 协调者远端校验
→ 关闭独立轮
→ 发布 submission-index.yaml
→ 创建新的 shared-review 轮
→ 参与成员分别提交评审证据
→ 关闭评审轮
→ 协调者处理意见并形成候选产物
```

共享评审不是让多人直接覆盖同一份可写原稿，也不是把所有人的内容自动变成共识。

成员可以查看原始提交核实来源；评审对象以正式任务包冻结的 submission index、完整 summary 和候选产物为准。

阶段 B 的 `complete-round-review` 只用于同时包含 `function-design + system-inventory` 的原始轮次，不能在 A、C 或普通原型验证轮中随意调用。调用前必须按顺序满足：

```text
关闭原设计/盘点轮
→ 收集、校验并关闭指向该原轮的 shared-review
→ 完成原轮 summary，且不含 [[FILL]]
→ complete-round-review <原轮>
```

## 10. 怎样理解 Gate

### 10.1 成员确认不是 Gate

human owner confirmation 只说明：

> 这份精确正文和个人立场可以作为该成员贡献提交。

它不表示：

- 团队一致；
- 需求或方案已批准；
- 允许合并；
- 允许进入开发；
- 允许发布。

### 10.2 G1–G3 的完整结果

下面是便于理解的结果链，不是可以跳步执行的命令链。实际执行必须按[完整使用说明第 11 节](system-usage-guide.md#11-g1g3-gate-操作)完成阶段关闭、状态转换、来源索引、溯源、评审包和 Gate 准备。

```text
来源覆盖与阶段校验
→ 人工评审包
→ Gate 责任人正式决定
→ approve-gate
→ merge-pending
→ merge-approved-gate
→ 审核冻结 commit 成为 main 祖先
→ 冻结基线
→ 确认稳定 Member Skill
→ 才能分发下一阶段任务
```

`approve-gate` 只进入 `merge-pending`，不是 Gate 已完成。

发生合并冲突、分支缺失、审核后 commit 变化或祖先校验失败时，保持 `merge-pending`，不能手工标记完成。

### 10.3 G4 和 G5

- G4：验证发布范围任务已集成，并决定是否允许进入灰度；
- 真正生产操作仍需要组织授权；
- G5：观察结束后关闭交付并冻结交付事实；
- G5 不授予代码合并权，也不是生产发布授权。

## 11. GitHub 页面怎么使用

### 11.1 当前 bootstrap 页面

当前进入：

```text
GitHub
→ Actions
→ SOP system validation
→ Run workflow
```

选择 `main` 后运行。

绿色表示：

- 系统模板完整；
- Skill 和运行时锁通过；
- 测试通过；
- bootstrap 边界正确。

绿色不表示：

- 项目已经初始化；
- 代码已经导入；
- 需求已经录入；
- 任务已经分发；
- Gate 已通过。

### 11.2 激活后可能看到的工作流

- `SOP system validation`
- `SOP 协调操作台`
- `SOP 中央状态与 README 看板`
- `SOP reminders`
- `SOP Skill 自动清理提案`
- `SOP Skill 清理提案校验`

模板被复制到 `.github/workflows/` 并合入默认分支后，就会出现在 Actions 页面。对应 capability 未开启时，带 guard 的副作用 job 会成功跳过；“看得到工作流”不等于“该能力已启用”。

### 11.3 操作台

入口：

```text
GitHub
→ Actions
→ SOP 协调操作台
→ Run workflow
```

使用最新 `main`，不要 Re-run 旧运行。

| 动作 | 用途 | 新手怎么填 |
|---|---|---|
| `refresh-state` | 刷新远端成员状态和看板 | 通常只选动作，乐观锁字段可留空 |
| `notification-test` | 测试 webhook、secret 和钉钉通道 | 不填 assignment ID |
| `task-reminder` | 催办一个精确任务 | 必填 `assignment_id`，说明文字可选 |

`notification-test` 不验证某个成员能否被 `@`。成员 `@` 只能在真实任务或受控催办中验证。

如果出现 `stale-main-sha` 或 `stale-project-revision`，不要重跑旧运行；从最新 `main` 新开一次。

操作台不能：

- 接受任务；
- 正式分发任务；
- 关闭轮次；
- 批准 Gate；
- 合并代码；
- 部署或回滚。

### 11.4 通知

正常链路：

```text
可信 main 中的任务或状态变化
→ 建立/更新 Assignment Issue
→ 发送钉钉
→ 写入幂等标记
```

成员分支 push 不会直接运行带 Secrets 的通知工作流。成员事实需要先经过可信刷新并投影。

Issue 已创建或钉钉已送达，都不代表成员已接受或已提交。

### 11.5 看板

激活后，README 中的 `dashboard/status.svg` 显示：

- 当前阶段；
- 成员接受、提交和校验状态；
- Gate；
- 阻塞项。

需要立即刷新时使用操作台 `refresh-state`。cron 名义上每 5 分钟尝试一次，但可能排队延迟，不是 5 分钟 SLA。

看板与原始文件冲突时，以 assignment、acceptance receipt、submission manifest、精确 commit、Gate 决策和基线为准。

## 12. 不要只看 Actions 绿色圆点

| 页面显示 | 不能自动理解为 |
|---|---|
| System validation 绿色 | 项目已初始化或 Gate 通过 |
| 工作流绿色但副作用 job skipped | 动作真的执行了 |
| `notification-test` 绿色 | 成员 `@` 映射正确 |
| Issue/钉钉送达 | 成员已接受 |
| 看板显示 valid | 可以替代原始 manifest 和远端校验 |
| `approve-gate` 成功 | 已合并并冻结基线 |
| Skill 清理成功 | 旧包已经从 `main` 删除 |

对于带 guard 的项目副作用工作流，判断是否真的做了事：

1. 查看 preflight/guard 是否为 active；
2. 查看副作用 job 是 success 还是 skipped；
3. 查看绑定的 `main` SHA 和 project revision；
4. 查看是否真的产生预期 commit、Issue/comment 或钉钉消息；
5. 最后检查权威事实文件和精确 commit。

`sop-system-validate.yml` 和只读的 `sop-skill-cleanup-validate.yml` 没有该 capability guard，不会出现上述同类 preflight 判断。

## 13. 哪些情况必须停下

### 协调者必须停下

- 项目、需求、范围、验收或责任人不明确；
- 风险等级或专项责任能力缺失；
- 用户尚未确认当前任务预览；
- 成员缺交、提交无效、反对或保留意见尚未处理；
- Gate 需要人类作出结论；
- 审核 commit 改变；
- 合并冲突或祖先校验失败；
- G3 尚未完成却准备进入真实开发。

### 成员必须停下

- assignment、身份、分支或基线不匹配；
- version、build ID、包路径或发行 commit 不匹配；
- 输入不存在或无权访问；
- 实际工作会超出任务允许范围；
- 需要修改公共 API、数据库、权限、隐私、支付或生产配置，但任务未授权；
- human owner 尚未确认当前正文；
- 测试、CI 或安全检查失败且无法在原范围修复。

### AI 永远不能独立执行

- 绕过主干保护、required review 或 CI；
- 代替真实人员批准；
- 部署生产；
- 删除或修复生产数据；
- 修改密钥、Webhook 或生产配置；
- 执行数据库回滚；
- 执行不可逆操作。

缺少有效 G4、事故流程或组织授权时，所有人都必须停止上述生产操作。具备明确授权的真实发布或事故责任人，只能按已批准方案和组织控制执行。

停下不是失败。缺少输入、权限或人工决定时，正确动作是记录阻塞并联系责任人，而不是猜测或绕过。

## 14. 第一次成功闭环

有真实需求时，在正式项目完成下面的闭环。若只想验证系统，应使用独立测试项目或测试仓库，不能在真实项目事实链中伪造任务、成员意见或 Gate。

协调者侧：

- [ ] 项目从 `bootstrap` 完整切换到 `active`；
- [ ] 系统校验通过；
- [ ] 一个真实任务经过预览和 Token 正式分发；
- [ ] 成员接受凭证已从远端观测；
- [ ] 成员提交已从远端完整校验；
- [ ] 通知和看板只投影事实，没有代替事实。

成员侧：

- [ ] 使用本人独立工作区和登记分支；
- [ ] 运行 `workspace-check` 和 `inspect`；
- [ ] 接受凭证已 commit/push；
- [ ] 只修改任务允许范围；
- [ ] human owner 已确认精确正文和个人立场；
- [ ] `validate`、`submit` 通过；
- [ ] 提交已 commit/push；
- [ ] 没有修改中央状态或其他成员证据。

审核侧：

- [ ] 评审对象、commit 和哈希明确；
- [ ] 反对、问题和保留意见没有被写成赞同；
- [ ] Gate 责任能力完整；
- [ ] 批准后仍完成精确合并、祖先校验和基线冻结。

完成第一次真实闭环后，再进入完整 A–C/G1–G3 流程。第一天不要直接尝试开发、发布或生产操作。

## 15. 下一步读什么

- 要初始化项目：阅读[新项目启动说明](../.github/SOP-BOOTSTRAP.md)；
- 要查完整命令和 GitHub 工作流：阅读[AI SOP 系统完整使用说明](system-usage-guide.md)；
- 要进入真实开发：阅读[开发交付 SOP](development-sop.md)；
- 要了解当前不能做什么：阅读[当前限制](../.github/CURRENT-LIMITATIONS.md)。
