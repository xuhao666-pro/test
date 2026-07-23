# 任务 Skill 版本预检

在读取任务正文、接受任务、访谈、创建产物或调用 Member CLI 前执行本预检。

## 区分包身份和任务运行时身份

V2.1.0 是统一发行包身份：

- `package_version: 2.1.0`
- `build_id: member-package-2.1.0-unified-runtimes-v1`
- 默认包路径：`ai-sop-member-skill-v2.1.0`

任务的 `required_member_skill.version` 和 `build_id` 描述的是包内某个运行时，不是发行包版本。不得因为包版本为 2.1.0，就把 1.8.0、1.8.1 或 2.0.0 任务改写成 2.1.0。

## 核对任务字段

所有任务从任务包读取：

- `required_member_skill.name`
- `required_member_skill.version`
- `required_member_skill.build_id`

A—C 的 1.8.x 任务还必须读取：

- `required_member_skill.package_path`
- `required_member_skill.release_commit`
- `required_member_skill.protocol_version`
- 可选的 `required_member_skill.package_version`

当前 D—E 2.0 任务合同只要求精确 `name`、`version` 和 `build_id`；其安装包来源必须由 `.github/sop-runtime-lock.json` 的 `development_member.source` 与统一包 manifest 交叉验证。不得把任务未提供的 `package_path` 或 `release_commit` 当作已绑定，也不得由 AI 补写。若任务实际提供包字段，则必须全部验证。

任务未提供其运行时合同要求的字段时按任务契约错误阻塞。若提供 `package_version`，它必须与指定包的 `package-manifest.json.package_version` 一致。

## 选择唯一运行时

A—C 从 `<package_path>/package-manifest.json` 读取 `runtime_releases`。D—E 未携带 `package_path` 时，只能从受信 runtime lock 的 `development_member.source` 反推出所属根包，并验证 source、安装态脚本和包内 CLI 哈希一致。随后按任务要求的 `version`、`build_id` 以及合同中存在的 `protocol_version` 选择唯一匹配项：

| 运行时 | 精确身份 | CLI | 协议资产 | 用途 |
| --- | --- | --- | --- | --- |
| `predevelopment` | `1.8.1 / member-cli-1.8.1-assignment-acceptance-v1` | `ai-sop-member/scripts/member_cli.py` | `ai-sop-member/assets/protocol-version.yaml` | 当前 A—C/G1—G3 |
| `development_delivery` | `2.0.0 / member-dev-cli-2.0.0-v1` | `ai-sop-member/scripts/development_cli.py` | `ai-sop-member/assets/development-protocol-version.yaml` | D—E/G4—G5 |
| `legacy_predevelopment` | `1.8.0 / member-cli-1.8.0-ai-dialogue-exact-release-v1` | `ai-sop-member/scripts/member_cli_1_8_0.py` | `ai-sop-member/assets/legacy-protocol-version.yaml` | 已绑定 1.8.0 的历史 A—C 任务 |

选择后必须再次验证：

1. CLI 文件真实存在，且其中的 `SKILL_VERSION`、`BUILD_ID` 与任务完全一致。
2. 协议资产真实存在，且 `skill_version`、`build_id`、`protocol_version` 与任务和 CLI 完全一致。
3. manifest 中登记的 CLI 与协议路径没有逃逸指定包。
4. 阶段与运行时用途一致；任何冲突都阻塞，而不是改用“最接近”或更高版本。

## 选择仓库安装态 CLI

需要从仓库安装态脚本执行时，按任务身份验证以下候选，不能只根据文件名猜测版本：

1. A—C 1.8.1：`.github/scripts/sop_member_cli.py`
2. A—C 1.8.0：`.github/scripts/sop_member_cli_1_8_0.py`
3. D—E 2.0.0：`.github/scripts/sop_member_development_cli.py`
4. 统一包：`<package_path>/<runtime_releases.<selected>.cli_path>`

兼容通配表示仍可写作 `.github/scripts/sop_member_cli_<version-with-underscores>.py`，但最终必须读取文件内的 `SKILL_VERSION` 和 `BUILD_ID` 验证。

## 不匹配提醒格式

```text
member-skill-version-mismatch
任务运行时：<version> / <build_id> / <protocol_version>
指定发行包：<package_path-or-runtime-lock-source> / <package_version-if-present>
当前候选：<version> / <build_id> / <protocol_version>
发行提交：<release_commit-if-contract-provides-it>
建议命令：python <verified-cli-path> inspect <assignment-path> --member-id <member-id>
处理结果：未开始任务，未创建或修改成员产物
```

提醒只提供可验证的修复路径，不等于自动安装或版本切换。若找不到精确运行时，提示成员同步协调者已确认的仓库提交并保持阻塞；不静默安装、升级、降级或覆盖全局 Skill。
