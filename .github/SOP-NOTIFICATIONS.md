# SOP 通知与反馈回流配置

通知只做提醒和状态投影，不构成任务接受、成员提交确认、Gate 批准或发布授权。

## 初始状态

通知工作流位于 `.github/sop-templates/workflows/`，在项目初始化前不会被 GitHub 执行。不要把旧仓库的 Environment、Secrets、成员映射、Issues 或运行记录复制到本仓库。

## 新仓库配置

在 GitHub 中建立受保护 Environment `sop-notifications`，限制到 `main`，并重新创建：

- `DINGWEBHOOK`：钉钉机器人完整 webhook。
- `DINGSECRET`：机器人加签 secret。
- `DING_MEMBER_MAP`：member ID 到钉钉目标的 JSON 映射。

映射结构：

```json
{
  "member-id": {
    "atMobiles": ["<ding-mobile>"],
    "atUserIds": ["<ding-user-id>"]
  }
}
```

实际机器人是否支持 `atUserIds` 取决于钉钉机器人类型；群自定义机器人通常应使用与钉钉账号绑定的手机号。值只保存在 GitHub Secret 中，不写入仓库。

## 安全边界

- 当前通知模板是 GitHub Issue + 钉钉的组合通道；`github_issue_notifications` 与 `dingtalk_notifications` 必须同时启用或同时禁用。
- 有写权限的处理器只执行可信 `main` 中的脚本。
- 成员分支内容只能作为被校验的数据，不能作为工作流代码执行。
- 每次回流必须绑定登记分支、精确 commit 和任务合同。
- 同一事件使用稳定幂等标识，避免重复 Issue、评论或钉钉消息。
- 缺失配置时应禁用或安全退出，不能把通知失败解释为任务未提交，也不能把通知成功解释为任务已接受。

## 启用顺序

1. 从示例生成全新的 `sop/notification-config.yaml`。
2. 新建 Environment 和三个 Secrets。
3. 审核模板工作流的权限、分支保护和 `active` guard。
4. 安装工作流后先运行 `notification-test`。
5. 再用一个新项目测试任务验证 GitHub Issue 与钉钉两条通道的幂等行为。

当前模板的已知边界见 `CURRENT-LIMITATIONS.md`。
