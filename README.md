# AI SOP 新项目工作区

当前状态：**SOP 系统已安装，项目尚未初始化。**

本仓库只包含可复用的 Skill 发行包、受信任运行时、自动化源码和未激活的工作流模板；不包含任何历史项目的需求、任务包、成员提交、评审、Gate、基线、看板状态或业务代码。

## 已安装能力

- A–C / G1–G3：Coordinator 2.1.1 统一包内的 1.8.5 运行时与 Member 2.1 统一包内的 1.8.1 运行时。
- 历史 A–C 校验：Member 2.1 统一包继续携带精确的 1.8.0 legacy 运行时，不再依赖单独的 1.8.0/1.8.1 根发行目录。
- D–E / G4–G5：Coordinator 与 Member 2.1 统一包内的 2.0.0 运行时，当前保持禁用。
- 状态看板、GitHub Issue、钉钉提醒、操作看板和 Skill 清理：源码与工作流模板已就绪，项目初始化后再启用。
- 初始唯一启用的 GitHub Actions 是只读系统校验，不读取 Secrets，也不会发送通知或改写状态。

## 目录说明

- `ai-sop-coordinator-skill-v2.1.1/`：当前 Coordinator 统一稳定发行包，声明 A–C 与 D–E 两套精确运行时。
- `ai-sop-member-skill-v2.1.0/`：唯一正式 Member 发行包，同时声明 1.8.0 legacy、1.8.1 A–C 与 2.0.0 D–E 三套精确运行时。
- 历史 Coordinator 1.8.4 与 2.1.0 由同名 annotated Git tag、Git 历史和清理审计保存，不再作为根目录发行包常驻。
- `.github/scripts/`：项目启用后使用的受信任运行时与自动化扩展。
- `.github/sop-templates/`：未激活的工作流和配置模板。
- `.github/sop-runtime-lock.json`：四个当前运行时及一个 legacy 运行时的版本、build ID、统一包来源与 SHA-256 锁。
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
