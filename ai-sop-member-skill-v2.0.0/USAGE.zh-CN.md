# AI SOP 成员 Skill V2.0.0 使用说明

本版本在 V1.8.1 的需求、设计、接受凭证、AI 对话协同和最终 owner 确认能力上，新增 D 正式开发和 E 发布交付执行能力。

A—C 兼容任务继续使用 `member_cli.py`；V2.0 开发和发布成员任务使用 `development_cli.py`。后者机械校验精确 Skill、接受凭证、工作分支、修改范围、必需检查、实现 commit 和 owner 对完成报告哈希及个人立场的确认。

开发或发布任务必须先读取：

- `ai-sop-member/references/development-delivery.md`
- `ai-sop-member/references/development-git-rules.md`

## V2.0 开发任务命令

```powershell
python ai-sop-member/scripts/development_cli.py accept-assignment <assignment.yaml> --member-id <member-id>
python ai-sop-member/scripts/development_cli.py init <assignment.yaml> --member-id <member-id>
python ai-sop-member/scripts/development_cli.py record-check <submission-dir> --assignment <assignment.yaml> --member-id <member-id> --name <check> --status passed --command <command>
python ai-sop-member/scripts/development_cli.py prepare-confirmation <submission-dir> --assignment <assignment.yaml> --member-id <member-id> --implementation-commit <sha> --position confirm --position-statement <statement>
# 向登记 human_owner 展示 preview，取得明确同意后再执行：
python ai-sop-member/scripts/development_cli.py confirm-submission <submission-dir> --assignment <assignment.yaml> --member-id <member-id> --confirmed-by <human-owner> --confirmation-token <token>
python ai-sop-member/scripts/development_cli.py validate <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
python ai-sop-member/scripts/development_cli.py submit <submission-dir> --assignment <assignment.yaml> --member-id <member-id>
```

`submit` 只冻结并标记成员提交，不代表独立代码审查、合并、G4、生产授权或 G5。

本发行包只包含 `ai-sop-member`。它用于成员在自己的独立工作区和登记分支中，读取已确认任务契约、完成分析或设计、生成内容块索引、校验并提交成员产物。

## 安装

将本目录中的 `ai-sop-member` 文件夹复制到：

```text
%USERPROFILE%\.codex\skills\ai-sop-member
```

重启 Codex 后即可使用。成员环境不需要安装 `ai-sop-coordinator`；任务、基线和项目状态从协调者管理的私有 Git 仓库获取。

## 开始任务

1. 从协调者取得仓库地址、成员 ID、登记分支和已确认的任务文件路径。
2. 使用独立 clone 或 worktree，切换到自己的登记分支，并用 `--ff-only` 同步 `main`。
3. Skill 先读取任务的 `required_member_skill` 并与自身 `assets/protocol-version.yaml` 比较；不匹配时停止并显示任务要求、当前版本、指定包、发行提交和经过验证的精确 CLI 命令。
4. 版本匹配后运行 `workspace-check` 和 `inspect`，核对身份、分支、任务契约哈希、确认状态、授权输入和基线。
5. 运行 `accept-assignment`，将生成的接受凭证 commit 并 push 到注册成员分支；协调端观测后看板显示“已接受”。
6. 运行 `init` 创建自己的提交目录，只处理任务契约授权的范围；缺少有效接受凭证时 V1.8.1+ 任务会被阻止。
7. 如果任务明确要求 `adaptive-grill`，按照 `init` 返回的提示先取得登记真实成员的同意，再每轮只问一个问题，完成问题定义、P0 和未决分歧三项独立确认。
8. 把 Grill 中间结果映射到正式来源、用户故事、验收、风险和缺口；未启用 Grill 只表示跳过访谈。
9. 完成正式产物后运行 `index-content` 和 `prepare-confirmation`，向登记 `human_owner` 展示当前正文哈希、个人立场、说明和确认 Token。
10. 取得 owner 对该预览的明确回复后运行 `confirm-submission`；再运行 `validate` 和 `submit`。正文变化会使确认失效。
11. 将成员产物 commit 并 push 到自己的登记分支，等待协调者远程校验、汇合评审和 Gate 审核。

常用命令入口：

```powershell
python "$env:USERPROFILE\.codex\skills\ai-sop-member\scripts\member_cli.py" --help
```

## 分离边界

- 成员不能创建或改写任务契约，也不能绕过协调者的预览确认流程。
- 成员只维护自己的分支、产物和提交清单，不直接修改 `project-state.yaml`、README 看板、中央来源台账或 Gate 结论。
- 成员不能代替协调者做团队汇总、批准 Gate、冻结基线或合并其他成员分支。
- 成员不得自行把普通对话升级成正式 Grill，也不得由 AI 代替真实成员回答或确认。
- `human_collaboration: none` 只关闭 Grill，不免除最终正文确认；成员确认不具有任何 Gate 效力。
- V1.8.1 任务必须精确匹配任务指定的版本与 `build_id`；更高、较低或同版本不同构建都阻塞。
- `git clone`、`fetch`、`pull` 或收到通知不代表接受任务；只有已推送并被协调端观测到的接受凭证才显示“已接受”。
- 版本预检只提醒并阻塞，不自动安装或覆盖本地 Skill；安装精确 Skill 后需要按客户端要求重启或开启新会话。
- 独立产出时按任务中的项目策略执行 AI 对话协同；默认 `required`，`optional` 才可明确跳过。
- AI 对话辅助文件不替代现有正式产物、Adaptive Grill 或最终 human owner 哈希与立场确认。
