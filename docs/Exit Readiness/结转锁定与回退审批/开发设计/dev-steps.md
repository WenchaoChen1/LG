# ERL 结转锁定与回退审批 开发步骤（sprint122 LG-1581）

> 关联文档: [设计](../设计/design-doc.md)（下文「CFn」「§n」均指该文档）· 需求 [ERL Yes问题不重复回答](<../../ERL Yes问题不重复回答.md>) · [ERL 问卷锁定项的回退审批](<../../ERL 问卷锁定项的回退审批.md>)（第二个需求，第 14～23 步）

- 代码在 worktree `D:\workspace\worktrees\sprint122-erl`，java / python / web 均在 `sprint122-erl` 分支。
- 第一个需求（结转锁定）先做完，第二个需求（回退审批）续编号；两者同批上线（CF11）。
- Python 零改动。

## 第一个需求：已答 Yes 的题结转锁定

| # | 层 | 步骤 | 范围（端 / 表 / 接口 / 页面 / 主要文件） | 设计依据 | 依赖 | 完成标准 | 状态 |
|---|---|---|---|---|---|---|---|
| 1 | 点 | 设计评审（文档） | 评审设计文档，确认 §7 接口草案、§8 页面草案，处理 §11 待定项 ①③ | §5 / §7 / §8 / §11 | — | 用户确认，设计文档定稿 | 已完成（2026-11-04 用户确认，doc-gap-review 用户叫停未做） |
| 2 | 点 | Java：基线与锁定范围计算 | `ErlAssessmentRepository` 新增「同端同维期次早于 P 的最近一次提交」「同端同维最后提交期次」「同端同维草稿列表」查询；`ErlLevelScorer` 新增锁定前缀计算（与 `QUESTION_ORDER` 同序，兼容存量里 No 之后残留的作答）与全 Yes 判定；题集版本号比较复用 `questionVersionNosOf` | CF2 / CF3 / CF4 | 1 | `ErlLevelScorerTest` 新增用例；编译通过 | 已完成 Java c5fdc754c |
| 3 | 点 | SQL：存量草稿清理 | Java `deploy/upgrade_doc/sprint122/V2__erl_draft_cleanup.sql`（原 V1，2026-11-05 与建表对调编号）：按「附件关联行 → 作答行 → 评估行」删除全部 `DRAFT`（erl_* 无外键，须手动按序）；文件头写「Java 发版后立即执行」，可重跑 | CF10 | — | 本地库执行两遍结果一致 | 待测试（已随 Java c5fdc754c 提交，第 11 步联调时在本地库跑） |
| 4 | 线 | Java：填报接口接入锁定 | `ErlAssessmentServiceImpl`：接口 3 无草稿时预览带出锁定作答、每题标 `locked`；`findOrCreateDraft` 新建分支复制锁定作答（Yes + 备注 + 附件关联）；`applyAnswers` 跳过锁定题；接口 29 合并锁定作答；出参 DTO / Response / Mapper。两端同一套 | CF3 / CF5 | 1, 2 | `ErlAssessmentServiceImplTest` 新增：无草稿预览、首次存草稿复制、直接提交复制、入参改锁定题被忽略、换版不锁、重复提交 L 不锁 L 自己 | 已完成 Java c5fdc754c |
| 5 | 线 | Java：封住历史季度 + 提交清理其它期次草稿 | 接口 3 下发最后提交期次与其它期次草稿列表；接口 4 / 5 / 29 拒收早于最后提交期次的季度；接口 5 同一事务删除该端该维其它期次草稿（含作答、附件关联） | CF6 / CF8 | 1, 2 | 单测：早于 L 拒收、L 可重复提交、首次任意季度、提交后其它期次草稿被删 | 已完成 Java c5fdc754c |
| 6 | 线 | Web：填报页锁定渲染 | `pages/exitReadiness/assessment/`：DTO 类型；锁定题只读 + 结转标记；打开后定位到第一道可答题；本地状态不允许改锁定题；Reset 后重拉 | CF3 / CF5 | 1（联调依赖 4） | `DimensionSection.test` / `useAssessmentDraft.test` 新增用例；tsc 无新增错误 | 已完成 Web 04536191a |
| 7 | 线 | Web：期次下拉置灰 + 提交确认弹窗 | `PeriodSelect` 按最后提交期次置灰更早季度，URL 指向历史季度时只读提示；提交确认弹窗列出将被删除的草稿期次 | CF6 / CF8 | 1（联调依赖 5） | `AssessmentPage.test` / `assessmentState.test` 新增用例 | 已完成 Web 04536191a |
| 8 | 面 | Java：全 Yes 视为已提交 —— 填报侧 | 接口 3 返回视为已提交态（只读，带出那次全 Yes 的作答）；接口 4 / 5 拒收；按季度判断生效题库版本（`ErlQuestionConfigVersion.publishedAt`：已结束的季度取季末前最后一次发布，未结束取当前最新） | CF7 | 2, 4, 5 | 单测：全 Yes 之后的季度只读、换版所在季度起恢复可填、之前季度不变 | 已撤销（设计 v1.1：CF7 改为每季手动确认，代码由第 12、13 步撤回） |
| 9 | 面 | Java：全 Yes 视为已提交 —— 展示侧回退 | 统一「某季某端某维的提交（含视为已提交）」解析，替换 `ErlCardServiceImpl` / `ErlDimensionServiceImpl` / `ErlGapAnalysisServiceImpl` / `ErlPortfolioServiceImpl` 各自的 `latestSubmitted`；卡片、A3 / A4、Portfolio、Gap 对账与 Share 门槛按已提交处理；两端都只是视为已提交时卡片的显示（§0.52 待定 ②） | CF7 | 8 | 四个 service 单测补回退用例，现有单测全过 | 已撤销（设计 v1.1：CF7 改为每季手动确认，代码由第 12、13 步撤回） |
| 10 | 面 | Web：视为已提交的页面形态 | 填报页只读态与说明（第 6 步的结转提示条现在只看 `carriedForwardFromPeriod`，DEEMED 时它也非空，要改成 `fillState === 'OPEN'` 才显示，只读按钮同理）；卡片 / A3 / A4 如需「沿用 Qx」标注 | CF7 | 1（联调依赖 8, 9） | 页面测试新增用例 | 已撤销（设计 v1.1：CF7 改为每季手动确认，代码由第 12、13 步撤回） |
| 11 | 面 | 本地联调 + E2E | 本地起 Java + Web，挑代表场景走一遍：两端各自时间线、换版不锁、跳季、重复提交 L、全 Yes 后下季全部锁定并手动提交、提交清理草稿、历史季度只读 | 全部 | 1～7、12、13 | 场景逐条通过 | 待开发 |
| 12 | 线 | Java：撤回「视为已提交」 | 撤掉第 8、9 步代码：`ErlFillStateEnum` 去掉 `DEEMED_SUBMITTED`；`ErlAssessmentServiceImpl` 去掉视为已提交判定 / 只读问卷 / 拒收文案，基线全 Yes 时走第 4 步的 OPEN 全部锁定；删 `ErlEffectiveSubmissionService(Impl/Test)`；卡片 / 维度 / Gap / Portfolio 四个 service 及测试、两个仓储恢复第 9 步前的样子 | CF7（v1.1） | 8, 9 | 编译通过；新增「全 Yes 基线 ⇒ 下季 OPEN、全部锁定、canSubmit = true、可直接提交」单测；ERL 单测全过 | 已完成 Java c5fdc754c |
| 13 | 线 | Web：撤回视为已提交页面 + 全 Yes 提示条 | 撤掉第 10 步代码与 `ErlFillState` 的 `DEEMED_SUBMITTED`；全部题都结转时提示条改为 `All questions were answered Yes in {期次} and are carried forward. Submit to confirm this quarter.` | CF7（v1.1）、§8.1 | 10 | 页面测试改写；ERL 前端单测全过 | 已完成 Web 04536191a |

可并行：2 与 3；4 与 6；5 与 7；8 / 9 与 10（Java 与 Web 按第 1 步契约各做各的，联调放到依赖的 Java 步骤完成后）。

## 第二个需求：锁定项回退审批

设计依据为设计文档 §12（v1.2），下文「RBn」「§12.x」均指该文档。

| # | 层 | 步骤 | 范围（端 / 表 / 接口 / 页面 / 主要文件） | 设计依据 | 依赖 | 完成标准 | 状态 |
|---|---|---|---|---|---|---|---|
| 14 | 点 | Java：申请表 | `deploy/upgrade_doc/sprint122/V1__erl_assessment_rollback_application.sql`（建表 `erl_assessment_rollback_application` + 部分唯一索引 `(company_id, dimension_code) WHERE status = 'PENDING'`）；实体 `ErlAssessmentRollbackApplication`、状态枚举、仓储：按公司 × 维度 / 按公司查待审核、批准 / 拒绝 / 单条作废的条件更新、按公司 × 维度与按组织 × 维度作废 | §12.2 / §12.3 | — | 本地库执行 DDL 两遍不报错；编译通过 | 已完成 Java 479d39d6e |
| 15 | 点 | Java：审批人判定与收件人查询 | 审批人：管理端 && 公司在组织子树内 && `UserServiceImpl.canAccessCompany`（SA 不算，2026-11-05 定）。收件人：公司所属那一级组织下（`r_organization_user`）任一角色带 `seeAllPortfolio`、非 SA 的用户 ∪ 公司所属 Portfolio（`r_company_group` → `r_portfolio_user`）的 PM，按邮箱去重。有没有审批人 = 收件人非空。`UserRepository` 新增查询，按 ERL 规范放进 ERL 的访问服务 | RB8 / RB9 | — | 单测：SA、PGM、负责 / 不负责的 PM、公司端各自的判定；收件人去重、排除 SA | 已完成 Java 479d39d6e |
| 16 | 线 | Java：回退提交 + GSV 直接回退（接口 31） | `ErlAssessmentServiceImpl` 新增回退提交：从基线复制 qk 之前的锁定作答、备注、附件关联，qk 记 No、原因写进备注；绑定版本取草稿的，没有取最新；只删早于 P 的草稿；提交人可指定；事务提交后触发 Gap 对账（token 由调用方传入）。接口 31 的 Controller / Request / Response | RB3 / RB4 | —（GSV 不建申请，不依赖第 14 步） | 单测：提交内容（锁定前缀 + No + 备注）、草稿保留 / 删除范围、qk 不是锁定题时拒收、`CLOSED` 拒收、全 Yes 基线 | 已完成 Java 479d39d6e |
| 17 | 线 | Java：Founder 申请（接口 30）+ 冻结 + 作废 ①② + 接口 3 出参 | 接口 30：校验 → 作废旧申请 → 插入 → 事务提交后发邮件 01（先留调用点，邮件由第 19 步接上）。接口 4 / 5 / 28 / 删附件在 P 审核中时拒收；接口 5 提交其他季度时作废申请。接口 3 加 `pendingRollbackRequest`、`canReviewRollback` | RB2 / RB5 / RB6 / RB7 ①② / §12.4 | 14, 15 | 单测：同季 / 更晚季度顶掉旧申请、更早季度拒收、无审批人拒收、冻结拒收、提交其他季度作废、接口 3 出参 | 待开发 |
| 18 | 线 | Java：审批（接口 32 / 33 / 34）+ 接口 22 出参 + 换版作废 ③ | 接口 32 详情；接口 33 批准：先用不抛异常的判定重算 qk 是否仍锁定（不是就 `voidById` 后正常返回「已处理」；`submitRollback` 抛异常会把整个事务标成只能回滚），再调第 16 步的回退提交（提交人记申请人、审批人 token），最后 `approve` 条件更新带上审批字段与提交 id，0 行则抛异常整体回滚；接口 34 拒绝。接口 22 管理端 Founder 维度加 `pendingRollbackRequest`。`publishDraft` 同一事务作废换版维度的待审核申请 | RB4 / RB7 ③ / RB8 / RB10 / §12.3 | 15, 16, 17 | 单测：批准生成提交并回写 `submission_id`、拒绝、已处理返回、非审批人拒收、qk 不再锁定时作废、换版只作废版本号变了的维度 | 待开发 |
| 19 | 线 | Java：三封邮件 | 三个 `EmailComposer`（01 审批人、02 批准、03 拒绝）与模板，`bizKey` = 申请 id，每个收件人一封；接到第 17、18 步留的调用点，都在事务提交后发 | RB9 / §12.6 / §12.9 | 14, 15 | Composer 单测：内容字段齐全、链接参数正确、收件人注销时抛 `NonRetryableEmailException` | 待开发 |
| 20 | 线 | Web：填报页 `Change to No` + 审核中态 | 两端锁定题加按钮与弹框（Founder `Apply` / GSV `Submit`）；Founder 审核中：提示条、非锁定题与按钮置灰；比 P 早的季度置灰按钮并提示；DTO 映射新字段 | §12.5.1 | 1（联调依赖 16, 17） | 页面测试新增用例；tsc 无新增错误 | 待开发 |
| 21 | 线 | Web：提交确认弹窗返工 | 第 7 步的合并弹窗改成设计稿弹窗 1、2；有待审核申请时提交其他季度弹弹窗 3，与 1 / 2 合并；题库更新弹窗的 `Submit draft content` 加弹窗 3 那句 | §12.5.1 / §12.9 | 7（弹窗 3 联调依赖 17） | `AssessmentPage.test` 改写并新增用例 | 待开发 |
| 22 | 线 | Web：A4 审核页 + 作废页 | Founder 药丸：卡片、读 P 的草稿（接口 3）只读渲染、高亮 qk、`Refuse` / `Approve` 与两个弹框；`rollbackRequestId` 落地按状态显示（作废整页 / 已处理提示 / 待审核） | §12.5.2 / §12.5.3 / §12.9 | 1（联调依赖 18） | `ScoreDetailsPage.test` 新增用例；tsc 无新增错误 | 待开发 |
| 23 | 面 | 本地联调 + E2E | 挑代表场景：Founder 申请 → 批准 / 拒绝、同季与更晚季度顶掉、更早季度置灰、提交其他季度作废、换版作废、GSV 直接回退、邮件 01～03 落 SQS、两人同时审批。可与第 11 步合并跑 | 全部 | 14～22 | 场景逐条通过 | 待开发 |

可并行：14、15、16 三步互不依赖；17 与 19；20、21、22（Web 按 §12.4 契约先做，联调放到对应 Java 步骤完成后）。
