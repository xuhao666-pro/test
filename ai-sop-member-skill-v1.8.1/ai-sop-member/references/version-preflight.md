# 任务 Skill 版本预检

在读取任务正文、接受任务、访谈、创建产物或调用 Member CLI 前执行本预检。

## 核对字段

从任务包读取：

- `required_member_skill.name`
- `required_member_skill.version`
- `required_member_skill.build_id`
- `required_member_skill.package_path`
- `required_member_skill.release_commit`
- `required_member_skill.protocol_version`

从当前 Skill 的 `assets/protocol-version.yaml` 读取 `skill_version`、`build_id` 和 `protocol_version`。任务未提供完整精确绑定时按任务契约错误阻塞；当前 Skill 与任务的名称、版本、build 或协议任一不一致时，不执行任务。

## 选择提醒路径

提醒路径必须真实存在，且文件中的 `SKILL_VERSION` 与 `BUILD_ID` 必须与任务一致。按以下顺序查找：

1. `.github/scripts/sop_member_cli.py`
2. `.github/scripts/sop_member_cli_<version-with-underscores>.py`
3. `<package_path>/ai-sop-member/scripts/member_cli.py`

不得只根据文件名猜测版本。找不到精确 CLI 时提示成员同步协调者已确认的仓库提交，并保持阻塞；不得推荐“最接近”或更高版本。

## 不匹配提醒格式

```text
member-skill-version-mismatch
任务要求：<version> / <build_id>
当前 Skill：<version> / <build_id>
指定包：<package_path>
发行提交：<release_commit>
建议命令：python <verified-cli-path> inspect <assignment-path> --member-id <member-id>
处理结果：未开始任务，未创建或修改成员产物
```

提醒仅提供修复路径，不等于自动安装或版本切换。安装新的 Codex Skill 后按客户端要求重启或开启新会话；若只运行仓库精确 CLI，仍必须遵守任务所绑定版本的 `SKILL.md`。
