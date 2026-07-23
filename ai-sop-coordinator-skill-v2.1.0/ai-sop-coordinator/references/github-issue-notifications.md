# GitHub Issue 提醒

此功能仅用于提醒。Issue、评论、标签、关闭状态和 `@mention` 均不得作为任务状态、成员提交、人工确认、Gate、合并或基线的事实来源。

## 配置

1. 在仓库设置中启用 Issues。
2. 将 `assets/github-notifications/notification-config.example.yaml` 复制为 `sop/notification-config.yaml`，填写协调员和成员的 GitHub 登录名。
3. 将 `assets/github-notifications/sop_issue_notifier.py` 复制为 `.github/scripts/sop_issue_notifier.py`。
4. 根据已登记成员分支展开 `sop-notifications.yml` 的占位符，并安装到 `.github/workflows/sop-notifications.yml`。
5. Actions 使用仓库自动提供的 `GITHUB_TOKEN`；不得把 Token 写入配置或提交到仓库。

独立通知工作流仅申请 `contents: read` 与 `issues: write`。它在 Runner 中只读刷新可信投影，不提交 SOP 文件。

## 事件

- `task-dispatched`：确认后的 dispatch 首次进入 `main`，创建任务 Issue 并提醒成员。
- `submission-received`：精确成员提交已出现，提醒协调员当前待可信校验。
- `submission-valid`：可信隔离校验通过，提醒协调员并关闭提醒 Issue。
- `submission-invalid`：校验失败，同时提醒成员和协调员，Issue 保持打开。
- `task-blocked`：成员正式记录阻塞，提醒协调员，Issue 保持打开。

所有 Issue 和评论包含稳定隐藏标记。Actions 重跑或手动补发会复用同一任务 Issue，并跳过已经发送的同一精确事件。

## 边界

- 不读取或执行 Issue 评论中的任何命令。
- 不根据 Issue 标签或关闭状态修改 YAML。
- 不把通知成功解释为任务送达确认。
- 不把 `@mention` 解释为人类 owner 确认或 Gate 批准。
- 通知失败不得改变已有 SOP 状态；修复配置后使用 `workflow_dispatch` 按精确 ref 和 commit 补发。
