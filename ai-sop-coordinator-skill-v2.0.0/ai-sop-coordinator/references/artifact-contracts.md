# 协调产物契约

## A00 项目状态

`project-state.yaml` 至少保存：

- 项目、协议和 project schema 版本。
- `execution_mode` 与 `collaboration_model`。
- `gate_confirmation_policy`。
- 最高风险、真实开发状态、当前阶段、下一 Gate、阻塞项和 G1–G3 基线。
- 有效成员列表、成员状态、专项责任和 `gate_accountability`。
- `git_integration`：强制标志、`main_branch`、合并策略、待合并 Gate 和最近一次合并证据。
- `submission_tracking`：投影版本、递增 revision、刷新时间/来源、各阶段汇总、逐任务成员记录和全项目总计。
- `provenance_tracking`：强制模式、生效 schema、迁移来源、历史无归属内容策略，以及各阶段来源索引哈希、实质/P0 覆盖率、问题数、报告路径和最后校验时间。
- 参与矩阵位置和已记录例外。

默认兼容组合为 `role-based + accountable-members`。共同参与型默认推荐 `all-participants`。角色卡、项目状态、参与矩阵和决策日志共同构成 A00。

`submission_tracking` 至少包含：

- 各阶段 `expected/submitted/in_progress/valid/pending_validation/invalid/missing` 数量。
- 各阶段及全项目提交确认 `required/confirmed/pending/attention/legacy` 数量；`attention` 表示已确认但个人立场为反对、质询或保留。
- 已提交、待校验和缺失成员 ID。
- 每个任务的成员、轮次、类型、分支、观察 ref/commit、状态、校验结论、提交时间、路径和计数。
- 每个任务的 `human_submission_confirmation` 投影：是否必需、状态、登记 owner、个人立场、是否需后续处理、确认时间、正文哈希和确认记录哈希。
- `last_refreshed_at`、`last_refresh_source`、观察模式和 Git remote。

该字段只能由协调者脚本生成。远程分支发现的完整提交先标记 `pending-validation`；进入协调工作树并通过完整 schema/文件校验后标记 `valid`。不得手工把待校验记录改成有效。

## 成员卡

角色分工型必须记录 `primary_role`；共同参与型允许为空并使用 `general-contributor`：

```yaml
member_id: member-001
status: active
participation_type: general-contributor
primary_role: null
additional_roles: []
professional_perspective: general-contributor
git_branch: sop/member/member-001
participation_scope: all-rounds
accountability_capacities: []
allowed_actions: []
prohibited_actions: []
```

只有真实人类成员可承担 Gate 人工责任能力。AI 成员卡可记录建议或审查能力，但不能进入人工批准映射。

## Gate 责任映射

`project-state.yaml` 中的映射使用稳定 Gate 和责任能力：

```yaml
gate_accountability:
  G1:
    business-decision: [member-001]
    product-decision: [member-002]
  G2:
    business-decision: [member-001]
    product-decision: [member-002]
    technical-decision: [member-003]
  G3:
    project-decision: [member-001]
    product-decision: [member-002]
    technical-decision: [member-003]
    test-decision: [member-004]
```

R2/R3 增加项目风险需要的专项能力。不得用 `team`、`all` 或空白值代替具体成员 ID。

## 参与矩阵

每个阶段在 `aggregation/participation-matrix.yaml` 维护轮次级状态。使用 [参与矩阵模板](../assets/project-template/participation-matrix.yaml)，至少记录：

- 阶段、轮次、协作模型和确认策略。
- 应参与成员及其有效/豁免状态。
- 独立提交、公开评审和 Gate 确认状态。
- 任务责任、主笔、缺席/豁免原因和影响。
- 每轮 `submission_coverage`、`shared_review_coverage`，以及 Gate 的 `approved_member_ids`。
- 可用共识声明和阻塞项。

共同参与型未完成要求且无事前豁免时不得关闭轮次。存在豁免时不得使用 `unanimous`；存在未处理反对、保留或缺席时不得声称全员通过。

## 任务包

任务包必须包含：

- 项目、阶段、轮次、任务、成员身份和任务版本。
- Skill、协议、project schema、输入基线。
- `collaboration_model` 和 `participation_mode`。
- 成员卡登记的 `git_branch` 和项目 `main_branch`；两者不得相同。
- 任务类型、目标、专业视角和独立性模式。
- 协调员输入的 `task_source`、`scope.included`、`scope.excluded`、`input_refs`、`deliverables`、`acceptance_criteria`、`constraints`、`dependencies`、`priority` 和 `coordinator_notes`。其中任务来源、目标、范围内事项、业务交付物和验收标准不得为空。
- `task_contract_hash`，用于校验上述任务内容在分发和成员初始化之间未发生变化。
- `dispatch_confirmation`，记录当前预览的确认 Token、协调员 ID 和确认时间；未确认预览不得进入 `distributed`。
- 独立于 Grill 的 `submission_confirmation` 策略：`required: true`、登记 `human_owner`、`source_file: main-output.md`、`hash_algorithm: sha256-normalized-v1`、正文哈希与个人立场两项确认主题、允许立场、stale 阻塞策略和 `gate_effect: none`；该策略必须进入 `task_contract_hash`。
- `shared-review` 任务必须包含 `review_of_round`，指向同阶段已关闭或已评审的独立轮次；`baseline_refs` 必须包含该轮已发布且匹配的 `submission-index.yaml`，只有非空且不含 `[[FILL]]` 的 `summary.md` 才可加入。其他任务不得携带 `review_of_round`。
- 允许来源、动作、路径和禁止动作。
- 必需输出、质量检查、期限和返回对象。

Coordinator V1.7.6 新任务的 `required_outputs` 必须包含 `human-submission-confirmation.yaml`。`human_collaboration.mode: none` 只关闭 Grill，不得删除该输出或降低确认要求。

`deliverables` 描述成员需要完成的业务交付；`required_outputs` 描述统一提交目录中的技术文件，两者必须分别记录。任务内容由协调员输入，脚本只能根据项目状态和成员卡补齐派生字段。创建命令第一次运行只输出预览；只有使用匹配的 `--confirm-dispatch` Token 才能写入任务包和阶段状态。

`participation_mode` 可为：

- `role-assigned`：角色分工型或指定成员任务。
- `collective-round`：共同参与型全员轮次任务。
- `individual-exception`：经记录的单独补充或例外任务。

阶段 B 首轮在同一轮次并行包含 `function-design` 和 `system-inventory`。关闭后生成轮次索引和公开评审摘要，完成评审后才能分发 `prototype-validation`。

## 提交索引与共享评审

关闭独立窗口后生成提交索引，明确有效、缺失、无效和带例外继续的成员。为公开评审创建新的 `shared-review` 任务轮次，通过 `review_of_round` 绑定被评审轮次；`independence_mode` 使用 `shared-review`。阶段 A 可只引用提交索引；候选汇总只有完成后才进入基线。已分发错误任务不得原地修改，旧轮次必须标记为 `superseded` 并记录替代轮次。

评审记录至少包含成员 ID、评审时间、关键事项、立场（确认/反对/质询/保留）、依据、建议处理和是否阻塞。协调员把记录同步到参与矩阵，不改写成员意见。

## 成员提交确认

V1.7.5+ 成员提交必须包含 `human-submission-confirmation.yaml`。确认记录至少绑定 assignment、version、submission、member、登记 `human_owner`、当前 `main-output.md` 正文哈希、个人立场及原话说明、两项确认主题、确认时间、确认方法和预览 Token；`authority_scope` 只允许成员贡献提交，`gate_effect` 固定为 `none`。

协调端必须把确认记录与任务包、提交清单和 `content-block-index.yaml.document_hash` 交叉校验。正文变化、owner 不匹配、立场说明为空、确认主题不全、Token 失配或状态未确认时，提交不得标记为 `valid`。`confirm`、`oppose`、`question` 和 `reserve` 都可作为有效个人提交；后三者必须进入后续意见处理，不能改写为赞同。

AI 不得生成 owner 的确认回复或代替 owner 完成最终确认。`minimum_skill_version < 1.7.5` 的历史任务只记录 `legacy-not-required`，不得追溯补签。完整字段和校验边界见 [submission-confirmation.md](submission-confirmation.md)。

## 内容来源索引与溯源台账

每个阶段使用三个互相关联的产物：

- `aggregation/provenance/source-block-index.yaml`：从成员登记分支的精确 commit 读取并验证 `content-block-index.yaml`，记录成员、任务、源文档、分支、commit、块哈希和原始 `SRC`。
- `aggregation/provenance/provenance-ledger.yaml`：把汇合产物的 `P-001` 映射到一个或多个成员源块，或映射到明确的人工决定/协调者新增原因。
- `aggregation/provenance/provenance-report.md`：报告实质内容覆盖率、来源成员、形成方式、审核状态和阻塞问题。

汇合内容按格式标记：Markdown 段落使用 `[P-001]`；结构化 YAML/JSON 记录使用 `provenance_refs: [P-001]`；表格在来源列使用 `[P-001]`。标题、分隔符等纯结构内容由解析器自动排除；实质内容不得以豁免绕过来源登记。

`derivation_type` 只允许 `verbatim`、`paraphrased`、`synthesis`、`derived`、`human-decision`、`coordinator-added`、`conflict-retained` 和受迁移策略限制的 `legacy-unattributed`。`verbatim` 必须且只能引用一个哈希完全相同的源块；`synthesis` 至少引用两个实际源块；`paraphrased`、`derived` 和 `conflict-retained` 必须引用真实源块；人工决定和协调者新增必须引用决定记录。新建 v1.5 项目禁止 `legacy-unattributed`。

台账中的源元数据必须与来源索引逐字段一致。成员分支 commit、正文或块哈希变化后，旧台账自动失效，必须退回并重新登记、评审。

## 汇总与产物清单

`aggregation/summary.md` 描述协作模型、输入范围、参与覆盖、主笔、证据、差异、意见处理、共识声明、风险和未决事项。

`aggregation/artifact-manifest.yaml` 列出当前阶段候选产物、参与矩阵路径和追踪覆盖：

```yaml
stage_id: 01-requirement-contract
input_baseline: A00-V0.1
collaboration_model: collective-participation
participation_matrix: aggregation/participation-matrix.yaml
provenance:
  source_index: aggregation/provenance/source-block-index.yaml
  ledger: aggregation/provenance/provenance-ledger.yaml
  report: aggregation/provenance/provenance-report.md
  substantive_content_coverage: 100
  p0_content_coverage: 100
consensus_claim: collective-with-recorded-exceptions
artifacts:
  - path: aggregation/requirement-contract.md
    artifact_type: requirement-contract
    version: V1.0-candidate
traceability:
  p0_source_coverage: 100
  p0_user_story_coverage: 100
  p0_user_story_source_coverage: 100
  p0_user_story_requirement_coverage: 100
  p0_acceptance_coverage: 100
  p0_design_coverage: 0
  p0_task_coverage: 0
  p0_test_coverage: 0
blocking_items: []
```

`consensus_claim` 的推荐值：

- `role-reviewed`：角色分工型已按责任和视角评审。
- `unanimous`：共同参与型全部应参与成员已完成要求且无反对、保留或例外。
- `collective-with-recorded-exceptions`：共同参与型存在已记录豁免或非一致意见。
- `no-consensus`：参与或意见阻塞，不能声称共同结论。

Gate 必需产物类型：

| 阶段 | 必需 `artifact_type` |
| --- | --- |
| G1 | `multi-view-review`、`consensus-user-stories`、`requirement-contract`、`demand-pool`、`atomic-requirements`、`business-acceptance` |
| G2 | `solution-review`、`consensus-function-design`、`system-inventory`、`validation-report`、`production-gaps` |
| G3 | `final-product-technical-plan`、`test-matrix`、`development-task-packages`、`risk-and-rollback` |

清单中的路径必须位于当前阶段目录并真实存在。G1 校验 P0 来源、用户故事、故事来源、故事需求和业务验收；G2 追加设计覆盖；G3 校验完整链路。所有当前 Gate 必需覆盖率和实质内容贡献来源覆盖率均为 100；原始证据追踪、成员贡献追踪和参与覆盖是三个独立约束，不得相互替代。

## Gate 决策与基线

`gate/gate-decision.yaml` 记录协作模型、确认策略、参与矩阵快照、来源索引/台账/报告、共识声明、责任能力映射、逐人确认和 `merge_plan`。`merge_plan` 必须列出全部有效成员的登记分支和 Gate 准备时的 `expected_head`；人工通过时必须明确确认审核覆盖这些 commit。`all-participants` 下全部有效人类参与成员都必须出现在确认记录中。成员 `human-submission-confirmation.yaml` 只证明一份贡献的正文哈希和个人立场，不能替代这里的 Gate 确认。

人工 Gate 通过后状态先变为 `merge-pending`。只有全部成员分支合并到 `main` 且每个 `expected_head` 通过祖先关系校验后，才把候选产物、参与矩阵快照、Gate 决策和合并证据复制到 `baseline/<baseline-version>/`。历史基线不得覆盖。
## 任务接受凭证

Member V1.8.1+ 任务在 `sop/stages/<stage>/acceptances/<member>/<assignment-id>-v<version>.yaml` 保存成员生成的显式接受凭证。凭证必须绑定任务文件哈希、任务契约哈希、成员、human owner、登记分支、精确 Member 版本与 build，并固定 `gate_effect: none`。协调端只从登记远端 ref 读取，不将本地中央副本作为接受事实。
