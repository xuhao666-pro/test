# AI SOP 新项目工作区

当前状态：**SOP 系统已安装，项目尚未初始化。**

本仓库只包含可复用的 Skill 发行包、受信任运行时、自动化源码和未激活的工作流模板；不包含任何历史项目的需求、任务包、成员提交、评审、Gate、基线、看板状态或业务代码。

## 已安装能力

- A–C / G1–G3：Coordinator 1.8.4 与 Member 1.8.1 兼容运行时。
- D–E / G4–G5：Coordinator 与 Member V2.0 发行能力，当前保持禁用。
- 状态看板、GitHub Issue、钉钉提醒、操作看板和 Skill 清理：源码与工作流模板已就绪，项目初始化后再启用。
- 初始唯一启用的 GitHub Actions 是只读系统校验，不读取 Secrets，也不会发送通知或改写状态。

## 目录说明

- `ai-sop-coordinator-skill-v2.0.0/`：完整 Coordinator V2.0 稳定发行包。
- `ai-sop-coordinator-skill-v1.8.4/`：V2.0 回归链保留的 A–C 原始发行包。
- `ai-sop-member-skill-v2.0.0/`：完整 Member V2.0 稳定发行包。
- `ai-sop-member-skill-v1.8.1/`：A–C 初始化与远端校验所需的兼容发行包。
- `ai-sop-member-skill-v1.8.0/`：Member 1.8.1 回归链所需的前序兼容发行包。
- `.github/scripts/`：项目启用后使用的受信任运行时与自动化扩展。
- `.github/sop-templates/`：未激活的工作流和配置模板。
- `.github/sop-runtime-lock.json`：四个当前运行时及一个 legacy 校验器的版本、build ID 与 SHA-256 锁。
- [启动说明](.github/SOP-BOOTSTRAP.md) 与 [开发交付 SOP](docs/development-sop.md)。

## 启动全新项目

在创建 `sop/` 前，需要录入：项目 ID、项目名称、协调者 ID、全新需求、成员与分支、执行模式、协作模型、Gate 策略、风险等级以及当前真实开发状态。协调者必须先展示精确输入并获得确认，不能从旧项目推断这些值。

初始化前可运行：

```powershell
python .github/scripts/sop_system_validate.py
```

项目初始化、成员注册、看板安装、通知配置与工作流激活的顺序见 [.github/SOP-BOOTSTRAP.md](.github/SOP-BOOTSTRAP.md)。

## 当前边界

D–E 能力随发行包保留，但在真实 G3 准入证据和对应负向门禁校验完成前不得启用。GitHub Issue、钉钉消息和看板只做提醒或投影，不构成任务接受、提交确认、Gate 批准或发布授权。详见 [.github/CURRENT-LIMITATIONS.md](.github/CURRENT-LIMITATIONS.md)。
