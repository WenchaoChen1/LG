# ERL 结转锁定与回退审批 开发步骤（sprint122 LG-1581）

> 关联文档: [设计](../设计/design-doc.md)（下文「CFn」「§n」均指该文档）· 需求 [ERL Yes问题不重复回答](<../../ERL Yes问题不重复回答.md>) · [ERL 问卷锁定项的回退审批](<../../ERL 问卷锁定项的回退审批.md>)（第二个需求，步骤待追加）

- 代码在 worktree `D:\workspace\worktrees\sprint122-erl`，java / python / web 均在 `sprint122-erl` 分支。
- 第一个需求（结转锁定）先做完，第二个需求（回退审批）定完设计后续编号追加；两者同批上线（CF11）。
- Python 零改动。

## 第一个需求：已答 Yes 的题结转锁定

| # | 层 | 步骤 | 范围（端 / 表 / 接口 / 页面 / 主要文件） | 设计依据 | 依赖 | 完成标准 | 状态 |
|---|---|---|---|---|---|---|---|
| 1 | 点 | 设计评审（文档） | 评审设计文档，确认 §7 接口草案、§8 页面草案，处理 §11 待定项 ①③ | §5 / §7 / §8 / §11 | — | 用户确认，设计文档定稿 | 已完成（2026-11-04 用户确认，doc-gap-review 用户叫停未做） |
| 2 | 点 | Java：基线与锁定范围计算 | `ErlAssessmentRepository` 新增「同端同维期次早于 P 的最近一次提交」「同端同维最后提交期次」「同端同维草稿列表」查询；`ErlLevelScorer` 新增锁定前缀计算（与 `QUESTION_ORDER` 同序，兼容存量里 No 之后残留的作答）与全 Yes 判定；题集版本号比较复用 `questionVersionNosOf` | CF2 / CF3 / CF4 | 1 | `ErlLevelScorerTest` 新增用例；编译通过 | 已完成 Java c5fdc754c |
| 3 | 点 | SQL：存量草稿清理 | Java `deploy/upgrade_doc/sprint122/V1__erl_draft_cleanup.sql`：按「附件关联行 → 作答行 → 评估行」删除全部 `DRAFT`（erl_* 无外键，须手动按序）；文件头写「Java 发版后立即执行」，可重跑 | CF10 | — | 本地库执行两遍结果一致 | 待测试（已随 Java c5fdc754c 提交，第 11 步联调时在本地库跑） |
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

（设计定完后续编号追加）
