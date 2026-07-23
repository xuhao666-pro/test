# 成员提交前最终人工确认

## 两条独立链路

`human_collaboration` 只决定是否开展需求 Grill：

- `mode: none`：不开展 Grill。
- `mode: adaptive-grill`：开展已授权的单问题动态访谈并完成其中间证据闭环。

`submission_confirmation` 决定最终成员正文能否提交。V1.7.5 新任务无论采用哪种 Grill 模式，都必须由任务登记的 `human_owner` 确认最终 `main-output.md` 的当前正文哈希和本人立场。

最终确认只表示“该哈希对应的正文准确记录本人立场，并同意作为本成员贡献提交”。它不构成 Gate 审批、合并许可、基线冻结、开发准入或发布授权。

## 必需流程

1. 完成全部正式产物；启用 Grill 时先完成 Grill 闭环并映射到正式正文。
2. 运行 `index-content`，检查正文内容块和哈希。
3. 运行 `prepare-confirmation`，同时输入 human owner 本人选择的立场及原话说明。
4. 把命令输出的 owner、正文哈希、个人立场、立场说明、固定权限声明和 Token 原样展示给登记 owner。
5. 暂停并等待 owner 对当前预览的明确回复。不得从沉默、既往讨论、Grill 同意、任务参与或默认选项推断确认。
6. 只有收到明确回复后，才运行 `confirm-submission`，并传入当前预览的 owner、正文哈希和 Token。
7. 运行 `validate` 与 `submit`。`submit` 会再次重建索引；正文变化会使旧确认失效。

```powershell
python scripts/member_cli.py prepare-confirmation <submission-dir> `
  --assignment <assignment.yaml> `
  --member-id <member-id> `
  --position <confirm|oppose|question|reserve> `
  --position-statement "<human owner 原话>"

python scripts/member_cli.py confirm-submission <submission-dir> `
  --assignment <assignment.yaml> `
  --member-id <member-id> `
  --confirmed-by "<registered human_owner>" `
  --document-hash "<preview document_hash>" `
  --confirmation-token "<preview confirmation_token>"
```

## 个人立场

- `confirm`：正文准确表达 owner 的当前结论或意见。
- `oppose`：正文准确记录 owner 的反对立场；允许提交异议，不得把它改写成赞同。
- `question`：正文准确记录 owner 的质询和待回答问题。
- `reserve`：正文准确记录 owner 的保留意见和可接受条件。

四种立场都可以形成有效成员提交。立场说明必须非空，并保留 owner 原意。提交有效不等于团队共识；协调者仍须在共同评审、参与矩阵和 Gate 中保留反对、质询与保留意见。

## 确认文件

`human-submission-confirmation.yaml` 由 CLI 创建和更新，核心字段为：

```yaml
schema_version: "1.0"
status: confirmed
assignment_id: A-...
assignment_version: "1.0"
submission_id: A-...-v1.0
member_id: member-001
human_owner: <registered owner>
source_file: main-output.md
hash_algorithm: sha256-normalized-v1
document_hash: sha256:<64 hex>
personal_stance:
  code: reserve
  statement: <owner 原话>
confirmed_subjects:
  exact_document_hash: true
  personal_stance: true
human_collaboration_mode: none
authority_scope: member-contribution-submission-only
gate_effect: none
prepared_at: <ISO 8601>
confirmed_by: <registered owner>
confirmed_at: <ISO 8601>
confirmation_method: explicit-human-owner
confirmation_token: <preview token>
```

`sha256-normalized-v1` 与 `content-block-index.yaml.document_hash` 使用同一正文规范化算法。确认后新增、删除或改写实质文本会改变哈希并阻塞提交；即使只是重新运行命令，也不能把 stale 确认自动改回 `confirmed`，必须重新生成预览并由 owner 再次确认。

## 能力边界

CLI 能防止 owner、任务、成员、提交、正文哈希、立场和预览 Token 错配，但本地文件不能密码学证明命令操作者就是人类。Skill 必须在会话层强制真实 owner 明确回复；AI 不得代选立场、代写确认回复、自动运行确认命令或把 Grill 记录当作最终确认。

如果未来需要强身份保证，应接入独立认证页面、GitHub 受保护审批、WebAuthn 或签名收据。本地 `explicit-human-owner` 记录不得被描述成密码学身份认证。

## 历史兼容

`minimum_skill_version < 1.7.5` 的既有任务属于 `legacy-not-required`。不得原地修改已确认任务、补写过去的确认时间或声称旧提交已完成“提交前确认”。需要应用新规则时，由协调者 supersede 旧的未完成轮次并重新签发任务；要求零历史例外时，重开实质任务和后续评审。
