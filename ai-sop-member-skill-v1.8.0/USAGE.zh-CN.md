# AI SOP 成员 Skill V1.8.0 使用说明

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
3. 运行 `workspace-check` 和 `inspect`，核对身份、分支、任务契约哈希、确认状态、授权输入和基线。
4. 运行 `init` 创建自己的提交目录，只处理任务契约授权的范围。
5. 如果任务明确要求 `adaptive-grill`，按照 `init` 返回的提示先取得登记真实成员的同意，再每轮只问一个问题，完成问题定义、P0 和未决分歧三项独立确认。
6. 把 Grill 中间结果映射到正式来源、用户故事、验收、风险和缺口；未启用 Grill 只表示跳过访谈。
7. 完成正式产物后运行 `index-content` 和 `prepare-confirmation`，向登记 `human_owner` 展示当前正文哈希、个人立场、说明和确认 Token。
8. 取得 owner 对该预览的明确回复后运行 `confirm-submission`；再运行 `validate` 和 `submit`。正文变化会使确认失效。
9. 将成员产物 commit 并 push 到自己的登记分支，等待协调者远程校验、汇合评审和 Gate 审核。

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
- V1.8.0 任务必须精确匹配任务指定的版本与 `build_id`；更高、较低或同版本不同构建都阻塞。
- 独立产出时按任务中的项目策略执行 AI 对话协同；默认 `required`，`optional` 才可明确跳过。
- AI 对话辅助文件不替代现有正式产物、Adaptive Grill 或最终 human owner 哈希与立场确认。
