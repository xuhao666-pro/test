# 新项目启动说明

## 1. 当前状态

仓库处于 `bootstrap`：系统代码已安装，但没有项目事实。此时不存在 `sop/`、成员登记、任务、Gate、基线或项目看板，项目工作流也未激活。

## 2. 必须先获得的输入

协调者应逐项展示并确认以下精确值：

- 项目 ID 与项目名称。
- 协调者 ID。
- 全新需求原文及附件来源。
- 执行模式：`standard` 或 `lightweight`。
- 协作模型：`role-based` 或 `collective-participation`。
- Gate 确认策略：`accountable-members` 或 `all-participants`。
- 风险等级：`R0`–`R3`，以及需要时的风险负责人角色。
- 当前真实开发状态。
- 每个新成员的 member ID、人类负责人和唯一 Git 分支。

不能从历史仓库、历史成员或历史任务中补全缺失字段。

## 3. 初始化项目

确认输入后，由协调者运行：

```powershell
python .github/scripts/sop_coordinator_cli.py init-project . `
  --project-id "<project-id>" `
  --project-name "<project-name>" `
  --coordinator-id "<coordinator-id>" `
  --execution-mode standard `
  --collaboration-model collective-participation `
  --gate-confirmation-policy all-participants `
  --risk-level R0 `
  --real-development-status "<current-status>" `
  --member "<member-id>:<human-owner>" `
  --member-branch "<member-id>:sop/member/<member-id>"
```

实际枚举值和成员数量必须来自当次确认。初始化后立即检查生成的 `sop/project-state.yaml`、成员登记与空需求池，确认它们只包含新项目输入。

## 4. 启用项目自动化

只有完成以下检查后，才能把 `.github/sop-templates/workflows/` 中的模板复制到 `.github/workflows/`：

1. 新项目状态可由统一 Coordinator 包内的 1.8.5 预开发运行时正常读取。
2. 成员和分支已登记且无重复。
3. 已刷新新项目状态，并用预装的 `sop_readme_dashboard.py` 生成新项目投影。
4. 已从示例创建新的 `sop/dashboard-policy.yaml` 和 `sop/notification-config.yaml`。
5. GitHub Environment 与 Secrets 已在新仓库中重新建立，没有复用旧值。
6. 工作流已加入 `lifecycle == active` 与项目状态存在性保护；不满足时应成功 no-op。
7. 手工运行通知测试与看板刷新，结果可审计且不改变 Gate 状态。

启用写操作前还应在仓库设置中确认 Actions 权限、受保护 Environment、`main` 分支保护以及机器人是直推还是走 PR；不要为了自动化绕过人工 Gate。当前通知工作流是 GitHub Issue 与钉钉组合通道，两项 capability 必须同步启用。

审核通过后，在同一受审提交中把 `.github/sop-system.json` 的 `lifecycle` 改为 `active`，将相应 capability 切换为 `true`。

本仓库不使用兼容运行时自带的 `install-dashboard` 安装器：目标路径已预装受信任运行时，而且该安装器会要求 `--force` 并把发行包内未加 lifecycle guard 的旧工作流覆盖回来。看板首次生成应直接运行：

```powershell
python .github/scripts/sop_coordinator_cli.py refresh-project-state . --remote origin --validate-remote --member-cli .github/scripts/sop_member_cli.py
python .github/scripts/sop_readme_dashboard.py --state sop/project-state.yaml --output dashboard/status.svg --readme README.md --action-url "<dashboard-workflow-url>"
```

随后逐文件把已加固模板复制到 `.github/workflows/`：

```powershell
Copy-Item .github/sop-templates/workflows/sop-dashboard-actions.yml .github/workflows/sop-dashboard-actions.yml
Copy-Item .github/sop-templates/workflows/sop-readme-dashboard.yml .github/workflows/sop-readme-dashboard.yml
Copy-Item .github/sop-templates/workflows/sop-notifications.yml .github/workflows/sop-notifications.yml
Copy-Item .github/sop-templates/workflows/sop-skill-cleanup.yml .github/workflows/sop-skill-cleanup.yml
Copy-Item .github/sop-templates/workflows/sop-skill-cleanup-validate.yml .github/workflows/sop-skill-cleanup-validate.yml
```

模板中的前置 guard 会在 lifecycle 或对应 capability 未启用时成功跳过副作用 job；它不替代激活提交的人工审核。

## 5. 录入第一项新需求

项目初始化不等于任务分发。新需求仍需走精确录入、分析、任务预览和 Token 确认；协调者不得在未确认时创建或分发任务包。

## 6. D–E 开发能力

D–E V2.0 文件已经安装，但初始禁用。只有真实 G3 基线已通过、证据已合并到可信 `main`、提交祖先关系可验证，并且开发门禁的负向测试通过后，才能启用开发任务、G4、发布和 G5 流程。
