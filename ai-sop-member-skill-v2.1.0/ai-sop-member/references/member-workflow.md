# 成员本地工作流

## 1. 首次接入仓库

1. 从协调员取得仓库地址、成员 ID 和成员卡登记分支。
2. 使用独立 clone 目录或独立 worktree；不得与协调员或其他成员共享工作树。
3. 首次接入执行：

```powershell
git clone <repository-url> <member-workspace>
cd <member-workspace>
git fetch origin --prune
git switch --track origin/<registered-member-branch>
git merge --ff-only origin/main
git branch --show-current
git status
```

4. 本地分支已存在时执行 `git switch <registered-member-branch>`，然后 fetch；优先用 `git merge --ff-only origin/main` 安全快进。
5. 成员已有历史提交时分支可能正常分叉。快进失败后先停止并联系协调员；只有协调员核对精确 head、确认合并无冲突并明确授权，才在登记分支执行 `git merge --no-edit <coordinator-verified-main-sha>` 和普通 push。不得用可移动 ref 替代已核验 SHA，也不得 rebase、reset、squash、强推或切到 `main` 代做。
6. 运行仓库精确 commit 自带的 Member CLI 执行 `workspace-check <assignment> --member-id <id> --fetch`，确认 `member_cli.build_id`、远程、登记分支、授权任务 commit 和合入该任务时的 `main` 基线快照。任务进入成员分支后，后续仅更新看板或中央状态投影的 `main` commit 不要求循环合并；脚本会在开始、索引、验证和提交时重复校验本地任务与协调员授权任务完全一致，并拒绝成员对授权基线的改动。

## 2. 开始任务

1. 拉取最新正式基线和自己的任务分支。
2. 先按 `version-preflight.md` 比较任务精确版本/build 与当前 Skill；不匹配时输出提醒并停止，不读取任务正文、不创建产物。
3. 使用提醒中经过内容校验的精确 `member_cli.py inspect` 校验协议、schema、身份、阶段、轮次、任务版本以及全部 `baseline_refs`；缺失、越界、空白或仍含 `[[FILL]]` 的中央材料必须在 `init` 前失败。
4. 对 V1.8.1+ 任务运行 `accept-assignment`，提交并 push 生成的接受凭证。只有协调端从注册成员分支观测到与任务文件哈希、任务契约哈希、成员和 Skill 构建完全匹配的凭证，才能显示“已接受”；单纯 pull 不构成证据。
5. 核对协调员输入的任务来源、目标、范围、输入引用、业务交付物和验收标准；确认 `dispatch_confirmation.status=confirmed`，并由 Member CLI 校验 `task_contract_hash`。缺少确认、字段或哈希不一致时停止。
6. 读取 A00、自己的成员卡、参与矩阵快照、最新 Gate 结论、任务风险和禁止事项。
7. 确认两个独立字段：
   - `execution_mode`：`standard` / `lightweight`
   - `collaboration_model`：`role-based` / `collective-participation`
8. 确认 `participation_mode`、任务责任和本任务采用的专业视角。共同参与型允许没有固定主要角色，但不能没有任务目标和边界。
9. 使用 `init` 创建成员专属提交目录，完成模板、来源、假设、缺口、风险和需求候选。
10. 如果任务显式要求 `adaptive-grill`，读取 `adaptive-grill.md`，取得登记真实成员的记录同意，执行单问题动态访谈并完成三项独立确认；未授权任务只跳过 Grill，不跳过最终提交确认。
11. 把 Grill 结果映射为正式来源、用户故事、需求、验收、风险和缺口；两个 Grill 文件是中间证据，不能替代正式产物。
12. 运行 `index-content` 检查内容块划分；再按 `submission-confirmation.md` 运行 `prepare-confirmation`，向登记 owner 展示正文哈希、个人立场、说明和 Token，并等待明确确认。
13. 只有取得当前预览的明确确认后才运行 `confirm-submission`；随后运行 `validate` 和 `submit`。`submit` 自动重建索引并确保正文哈希、最终人工确认、Grill 闭环、清单状态、时间和计数准确。
14. `submit` 只更新并冻结成员提交清单；随后提交并推送成员卡登记的 Git 分支，不得把工作提交到 `main`。push 触发中央状态远程校验和 README/SVG 刷新。

## 3. 独立性模式

- `isolated-discovery`：不读取其他需求分析。
- `isolated-design`：共享正式 G1 基线，不读取其他成员设计或盘点。
- `specialized-preparation`：只读取任务列出的公开基线和评审材料。
   - `shared-review`：仅在 `review_of_round` 指向的独立窗口已关闭后，读取协调员发布的提交索引、有效提交和候选汇总。

共同参与型不取消独立性。收到 `collective-round` 任务时，仍独立提交自己的产物；不得直接共同编辑一份 A01、A05 或系统盘点原稿。

## 4. 角色分工型

按任务包指定的角色视角和专业边界执行。可以提出跨角色问题和风险，但不得擅自接管其他成员的任务或修改他人产物。

## 5. 共同参与型

- 作为 `general-contributor` 参与时，明确本任务实际采用的视角和证据边界。
- 对要求的每类独立任务分别提交；没有系统访问权时记录“无法访问”和待核实项，不猜测事实。
- 独立窗口关闭后参加 `shared-review`，逐项记录确认、反对、质询、保留意见和理由。
- 不把自己的意见表述成团队意见，不把投票数量替代证据和风险判断。
- 发现自己被错误标记为已提交、已评审或已确认时，立即通知协调员；不要直接修改参与矩阵。

## 6. 证据、身份和共识

真实成员对提交负责。本地 AI 可以研究、生成草案和检查，但不能替代真实成员确认来源，也不能冒充用户、其他成员或批准人。

无论是否开展 Grill，最终正文都必须由任务登记 owner 确认当前哈希和本人立场。反对、质询和保留仍可作为有效提交，但不得被协调者改写成赞同。该确认只针对成员贡献，不替代团队共同评审或 Gate。

独立提交只代表该成员结论；`shared-review` 只代表该成员的评审立场。只有协调员依据完整参与矩阵和意见处理结果形成候选共识声明。

成员负责提交真实正文和原始 `SRC`；脚本负责生成内容块 ID 与哈希。成员不填写中央 `P-001` 台账，也不决定汇合稿采用、综合或拒绝了哪些成员内容。

## 7. 新需求和回流

新增需求只写入 `risks-and-new-requirements.yaml`。填写来源、价值、优先级、基线影响和建议回流位置；不得直接修改需求池、正式方案或任务包。

## 8. 提交窗口和失败处理

独立窗口关闭后不要修改原提交。协调员准备 Gate 并记录 `expected_head` 后，不得再改写或追加该分支；需要补交时等待退回和新任务版本。Git 冲突时先检查是否误改共享文件。

- 身份、协作模型、参与范围或基线不一致：停止并联系协调员。
- 缺少权限或无法访问系统：记录未知项，不猜测事实。
- 高风险缺少人工决定：停止受影响部分并触发升级。
- 校验失败：只修复自己的提交。
- 共享评审输入未公开或窗口未关闭：拒绝提前读取并报告阻塞。
