# Exit Readiness（ERL）设计文档 V1

> 关联文档：
> - **需求文档（本设计的唯一权威来源）**：[../../Exit_Readiness_PRD.md](../../Exit_Readiness_PRD.md)
> - **sprint122 结转锁定与回退审批（Asana LG-1581）**：独立设计文档 [结转锁定与回退审批/设计/design-doc.md](<../结转锁定与回退审批/设计/design-doc.md>)，本文不重复
> - 原型（Lovable，已发布，**仅作 UI 参考**）：`https://exit-readiness-hub.lovable.app`（项目 `exit-readiness-hub` / `ERL-Portfolio portal`）。与 PRD 冲突处一律按 PRD；⚠️ 原型全部为五维形态，维度数量以配置为准
> - 后端规范：[../../../CIOaas-api/standards/architecture.md](../../../CIOaas-api/standards/architecture.md) · [../../../CIOaas-api/standards/coding.md](../../../CIOaas-api/standards/coding.md)
> - Python 规范：[../../../CIOaas-python/standards/architecture.md](../../../CIOaas-python/standards/architecture.md) · [../../../CIOaas-python/standards/coding.md](../../../CIOaas-python/standards/coding.md)
> - 前端规范：[../../../CIOaas-web/standards/architecture.md](../../../CIOaas-web/standards/architecture.md) · [../../../CIOaas-web/standards/coding.md](../../../CIOaas-web/standards/coding.md)

阶段：④ 设计 | 版本：v5.0 | 日期：2026-11-16 | 范围：ERL Card（含 Gap 区块）/ 维度详情 / 全维 Score Details（**双端可达**）/ 双端填报（**Yes/No 逐级解锁 + 维度级提交**）/ 题库配置（**`Question Library` / `Dimension Configuration` 两个顶层 Tab + 题库版本历史页**）/ 基准 / Goldie 差距分析（**含 Share**）/ 组合层 ERL Tab

> 2026-11-16 精简：删除版本说明、§0.3～§0.51 修正清单、§10 改动文件清单、§11 验证清单、附录 A～C；变更经过见 git 历史。代码注释里引用的旧编号见 §0.3 对照表。

---

## 0. 目标与裁决原则

### 0.1 一句话目标

在 LG 平台内实现**退出准备度（Exit Readiness Level, ERL）**：**替代 Company Overview 页的 Development Intelligence（DI）板块**，由创始人（Founder）与 GSV 团队各自独立完成季度评估，**按维度分别提交**，从若干维度（**数量与权重可由管理员配置**）打分，产出维度分 / 综合分 / 当前 Stage / 双方认知差（Perception Gap），与 Benchmarkit、Top GSV Quartile 两条外部基准对比；由 Goldie 生成差距分析与行动建议、**由 GSV 决定是否 Share 给 Founder 端**；题库与维度配置可由管理员自助维护；组合层提供跨公司 ERL 总表。

### 0.2 权威来源与冲突裁决

| 来源 | 地位 |
|------|------|
| `docs/Exit_Readiness_PRD.md` | **唯一权威**。任何与之冲突的原型行为、Lovable story 描述一律作废 |
| Lovable 原型 | 仅作 **UI 布局与交互参考**；其数据、计算口径、页面结构均不构成需求 |
| Lovable story 验收标准 | 参考；与 PRD 冲突时以 PRD 为准 |

**沿用的基础结论**：
- Java 为前端唯一出口，Python 只做 LLM 生成（§3）。
- Perception Gap = Founder − GSV（PRD §5），**公司端不展示**（§4.2）。
- 不引入 SQS；题库与权重**按组织（租户）隔离**。

> **跨项目协作模式**：ERL 差距分析是根 `CLAUDE.md` 记录的第三种 Java↔Python 协作模式 —— **HTTP 内网直连 + 同步非流式**：Java 不经网关，经 Nacos 配置项 `cio.erl.ai-base-url` 直连 Python，并转发调用者 Bearer token；Java 持编排状态，Python 持 AI 内容（§5.8 / §6.6）。

### 0.3 历史编号对照表

下列编号来自已删除的变更清单 / §10 / §11，仍被代码注释引用；按编号查当前口径。

| 旧编号 | 内容（当前口径，一句话） | 现在见 |
|--------|--------------------------|--------|
| §0.10 | 维度级提交、维度集合与权重由租户配置、展示期次缺省 = closed month 所在季度这三条全局口径，及随之的 Goldie（含 Share）、A4 双端可达、填报按钮组、历史列表等调整 | §5.2 / §5.1.3 / §7.1.2 / §6.6 |
| §0.10-D1 | 维度不是固定枚举：维度集合是租户配置数据，一律接口驱动（无静态 `DIMENSIONS` 映射）；F2 出参与列、雷达图顶点、A3 / A4 / C7 维度卡、Gap 状态点数量均按接口返回的维度列表渲染；`code` 由服务端生成，不得硬编码 | §5.1.3 / §7.11 / §6.8 / §8.4 |
| §0.10-R1 | 提交粒度 = 维度级：一次提交 = 某公司某期次某端的单个维度（`erl_assessment.dimension_code`）；提交校验只要求本维终止；同期次各维可绑不同题库版本 | §5.2 / §7.2 / §7.7 |
| §0.10-R3 | `period` 缺省 = 该公司 closed month 所在季度（读 FI 每日快照，ERL 只调不算）；closed month 取不到回退当前自然季度（UTC）+ WARN；该季两端均无提交 → 空态，不回退到更早期次；F2 同样走服务端逐公司缺省 | §7.1.2 |
| §0.41 | 差距分析任务化：Java 持 `erl_gap_analysis_report` + `erl_gap_analysis_dimension_task`（记录、任务状态、`has_gap`、分享），Python 持 `ai_erl_gap_analysis_task` + `_item`（生成日志与 AI 内容）；每任务一次 LLM；状态机 `PENDING → RUNNING → SUCCESS \| FAILED`，管理端读时按 60s 冷却重投；已分享记录不可变；不做回调 | §5.8 / §6.6 / §7.5 |
| §0.10-D5 | A4 Score Details 两端都可达（ERL Card 右上 `Full View ›`）；按维度 Tab 展示，每维带 `Add New` / `View History`（带 `dimension`）；管理端用 `GSV` / `Founder` 药丸切换（默认 `GSV`），切 Tab / 药丸重新请求接口 22 | §6.2.1 / §8.4 |
| §0.10-D4 | ERL Card Gap 区块：`Gap Analysis & Suggested Actions` + `AI GENERATED`、`View details` 弹框、`Share to founder`；每维小卡的 `bothSubmitted` / `questionSetMismatch` / `hasGap` 是三条独立信息，前端不得合并成一个枚举，mismatch 优先于 `hasGap` | §6.1 / §8.4 |
| §0.10-D3 | 差距分析单份产物 + 单 prompt，可见性由 `shared` 控制：管理端生成即可见，公司端仅在最新记录 `shared = true` 时可见、否则空态；接口 27 `POST /erl/gapAnalysis/share` 仅管理端，激活门槛由服务端判定下发 | §4.3 / §6.6 / §7.5 |
| §0.10-D8 | 填报页按钮组 `Save as draft` / `Cancel` / `Reset` / `Submit`，无自动保存；`Cancel` 只离开页面；`Reset` 走接口 28 `DELETE /erl/assessment/draft`，删除草稿的附件、答案与草稿行本身 | §6.3 / §8.4 |
| §0.10-D9 | 草稿公司共享、不区分账户，后保存者直接覆盖；接口 3 出参 `lastSavedAt` / `lastSavedBy`；提交人记录点提交的那个人 | §6.3 / §7.7 / §8.4 |
| §0.10-D7 | 基准页入口是 ERL Card 雷达图正下方的链接 `View Top GSV Quartile & External Benchmarks ›`（`benchmarkUrl` 由接口 1 下发），仅管理端渲染 | §8.1.1 / §8.4 |
| §0.10-D14 | 综合分英文 UI 文案统一为 `Overall Score` | §8.4 |
| §0.23-P1 | F2 前端不传 `period`，由服务端逐公司取缺省期次（批量 `resolveDefaultPeriods`），各行期次可能不一致 | §6.8 / §7.1.2 |
| §0.23-P2 | F2 是纯展示表：无筛选控件、无列头排序；接口 20 的 `sortBy` / `sortOrder` / `stage` / `minScore` / `maxScore` 服务端能力保留，F2 不下发 | §6.8 / §8.4 |
| §0.10-D12 | B3 历史列表：无 `Completion` 列，有 `Submitted`（提交时间）列，`Portal` 列仅管理端，分数列为维度分 `{level}/9` + Era 徽章（非加权综合分）；接口 8 可选 `dimension` 入参，带维度进入时只渲染该维 | §6.3 / §8.4 |
| §0.23-P6 | F2 页面不显示任何期次文字 | §8.4 |
| §0.10-D11 | 提交确认弹窗两套文案：该期次该端该维 `submissionCount > 0` 时用 `Submit again?` 确认框（不提 source of truth） | §8.4 |
| §0.10-D10 | 版本锁定不变；接口 3 出参 `latestPublishedVersionNo` / `hasNewerQuestionSet`，题库有新版时填报页弹强阻断二选一弹窗（`Submit draft content` / `Access new question library`） | §6.3 / §7.9 / §8.4 |
| §0.5-5 | 题库写接口（接口 11 / 12 / 13 / 14 及 `reorder`）按 `questionKey` 定位，不按题目 `id`（写时复制会换 id） | §6.4 / §7.9 |
| §0.47 | 差距分析生成门槛为维度级：两端都有 SOT 且无题集 mismatch 的维度即可分析，只为它们建 / 派发任务，一个都没有才不生成；Share 门槛仍要求全部 Active 维度 | §7.5 / §6.6 |
| §0.46 | 两端都以最新一条差距分析记录为准：公司端只在最新记录 `shared = true` 时可见，分享后再提交即回到空态，直到管理端再次 Share | §7.5 / §6.6 |
| §0.44 | 差距分析无 severity：`gaps[]` 每项只有 `title`；提示词 `erl_gap_analysis.md` 版本 1.0，模型输出 `{gaps: [str], actions: [str], narrative}`；`gaps` 无可用条目判该任务 FAILED | §6.6 |
| §0.33 | 差距分析 AI 内容由 Python 落库（`ai_` 前缀表），Java 经内网直连调 Python 并转发 Bearer token；表的具体分工以任务化后为准（见 §0.41 行） | §5.8 / §6.6 |
| §0.32-Y6 | 生成侧跳过题集 mismatch 的维度，可分析维度为 0 时不调 Python；Share 门槛要求无 mismatch（代码注释「推翻 §0.32-Y6」指的就是后半句） | §7.5 / §7.10 |
| §0.12-A1 | 附件双端统一题级：Founder 与 GSV 一律逐题挂附件（单个 ≤ 10MB），无维度级附件 | §5.5 / §6.7 |
| §0.12-A2 | 附件表为 `erl_answer_attachment`，`answer_id` not null，无 `assessment_id` 列（附件 → 作答 → 评估两跳鉴权） | §5.5 |
| §0.10-R2 | 维度配置不版本化、无期次绑定：任何期次一律读当前 Active 维度集合与权重，改权重 / 增删维度会回溯改变历史期次综合分与 Stage（§13-Q21）；进入过已发布题库版本的维度只能停用（`status = 'Inactive'`），从未进入过的可删除（`deleted = true`） | §5.1.3 / §7.11 |
| §10.1（题目查询带版本） | `ErlQuestionConfigRepository` 每个查询方法都必须带齐 `(organizationId, dimensionCode, versionNo)`，禁止无版本的「查全部题」；取某发布版本全部题须先经 §5.1.5 快照拿逐维 `question_version_no` 再逐维查。漏带版本 = 草稿题泄进问卷，漏带组织 = 跨租户串题 | §5.1 / §5.1.5 |
| §10.1（取题统一入口） | 调用方不自行拼 `(版本行 id, dimension_code)` 复合键反查快照：评估行的 `erl_question_config_dimension_version_id` 一跳取快照，取题一律经 `ErlQuestionConfigVersionService` 的入口 | §5.1.5 / §5.2 |
| §10.1（缺省期次唯一落点） | 缺省期次只经 `ErlPeriodService` 取，其余 service 禁止各自查 FI 表 | §7.1.2 |
| §10.1（Java 文件清单） | `V1__erl_init.sql` 等文件头引用的 Java 改动清单已删除；表结构以 §5 为准 | §5 / §3.1 |
| §11-6 | 公司端请求 `portal = GSV` 后端直接返回业务错误（HTTP 200 + `success: false`），不能靠前端隐藏 GSV Tab | §4.2 / §4.3 |
| §11（No 之后已答行） | 答 No（含 Yes 改 No）后，同级其后与后续 level 的作答、备注、附件全部清空，保存时服务端回收首个 No 之后的答案与附件；Goldie 只拿到首个 No 为止的作答 | §6.3 / §7.2 / §8.4 |
| §5.1.2 / §5.1.4（已删表 `erl_dimension_config_version` / `erl_company_period_config`） | 维度配置不版本化、不与期次绑定：每组织只有一份当前配置，任何期次都读当前 Active 维度集合与权重；改权重回溯影响历史期次（已接受，§13-Q21） | §5.1.3 / §7.11 |
| §5.3（已删表 `erl_assessment_dimension`） | 不再有每维汇总表：一次提交即一个维度，维度分直接落 `erl_assessment.level_score` | §5.2 |
| §9-19 | 维度停用（`Inactive`）或删除后：ERL Card、雷达图、A4 只取当前 Active 维度，不再出现该维（`Retired` 灰标只是前端防御，接口不会下发）；历史提交记录照常返回，名称 / 缩写取 `erl_assessment` 行上快照 | §9（「维度已被停用」行）/ §5.2 |

---

## 1. 范围与分期

### 1.1 V1 范围

| 模块 | 功能点 | 在 V1 | PRD | 说明 |
|------|--------|:-----:|-----|------|
| A 展示 | **A1 ERL Card（Company Overview 页内）** | ✅ | §3.1 | **加权**综合分 + 当前 Stage + Gap Analysis 区块（形态见 §8.4） + **维度列表**（条目数由当前 `status = 'Active'` 的维度集合决定，§5.1.3）（维度分 / Perception Gap **仅组合端**） + 雷达图（**仅组合端**） + **`Full View ›`（两端均有，A4 入口）** + **雷达图正下方 `View Top GSV Quartile & External Benchmarks ›`（仅管理端）**。**唯一入口，无独立落地页** |
| A 展示 | A2 Dimension Radar 雷达图（卡片内） | ✅ **仅组合端** | §3.5 | 4 条序列：Founder / GSV / External Benchmarks（屏显名；后端 key 仍为 `BENCHMARKIT`）/ Top GSV Quartile。顶点数 = 当前 `status = 'Active'` 的维度集合的维度数。**维度数 < 3 时整块不渲染**（含标题条）。PRD「该图仅在 Portfolio 端显示」→ 公司端整图不渲染 |
| A 展示 | **A3 维度详情页（Score Details，模板）** | ✅ | §3.2 / §3.5 | **一套模板全维度复用**（按维度列表复用）；含 score card 头、Perception Gap（**仅组合端**）、逐题列表、`View history`、`+ New`；Strengths & Priority Gaps 依据 §3.6 |
| A 展示 | **A4 全维 Score Details 页** | ✅ | §3.7 + §3.5 | **一页看全维度逐题明细**：**两级面包屑 → H1 `Score Details`（页头无综合分、无 Stage 徽章）→ 维度横向 Tab（一次只渲染一维，标签取 `abbr`，Tab 数按当前维度集合）+ 末位基准 Tab（`External Benchmarks & Top GSV Quartile`）→ 组合端 `GSV` / `Founder` 药丸切换（`GSV` 默认）**。入口：F2 `View` + ERL Card 的 `Full View ›`（两端）；**每张维度卡卡头各有 `+ Add New`（仅 `GSV` 侧）/ `View history`，无页级 `+ New` / `View history`**。UI 依据原型 `/readiness/overall` |
| A 展示 | **A7 Company Overview 三卡布局** | ✅ | §3.1 | **左列 `FI → DI` ＋ 右列 `ERL`**（ERL 占原 DI 的右列位置）；DI 数据、打分、入口与下钻**全部保留**，不新增任何开关（§8.6） |
| B 填报 | B1 Founder 自评问卷 | ✅ | §3.3 | **提交单元 = 单个维度**；期次选择、**Yes/No 逐级解锁**（本 level 全 Yes → 折叠打勾 → 解锁下一 level）、逐题备注 + 附件（**≤10MB/个**）、进度、**手动存草稿（只有 `Save as draft` / `Submit` 两个按钮会落盘）**、提交即只读。顶部按钮组 `Save as draft` / `Cancel` / `Reset` / `Submit`；题库更新提示为**强阻断二选一弹窗**；重复提交确认文案分支；进入草稿显示上次保存时间与保存人 |
| B 填报 | B2 GSV 验证问卷 | ✅ | §3.4 | 同题库、同解锁规则 + **逐题附件（与 B1 同口径）**；提交单元同为**单个维度** |
| B 填报 | **B4 Reset / 丢弃草稿** | ✅ | §3.3 | 填报页 `Reset` 按钮：**连草稿行一起删除**（附件 → 答案 → 草稿行，§6.3 接口 28）；**无二次确认，点下去直接清**。**接口 28** `DELETE /erl/assessment/draft`（§6.3） |
| B 填报 | B3 评估历史列表 | ✅ | §3.9 | 完整保留每次提交，无 `Current` 徽章（最新 SOT 屏上只靠行序）。含 `Submitted` 列、无 `Completion` 列、分数列为**本维度 Overall Score + Stage 徽章**、`Portal` 列仅管理端渲染、详情限本维度 |
| C 配置 | C1 题库列表（**`Question Library` 顶层 Tab** 内：各维度 Tab + Era band 分组表格；维度 Tab 数按当前 `status = 'Active'` 的维度集合动态） | ✅ | §3.8 | **仅 portfolio portal**；题库按**组织（租户）**隔离 |
| C 配置 | C2 新增题目 / C3 编辑删除 | ✅ | §3.8 | 题干 / Era band（1–9 level）/ Source（无判定标准字段）；表单字段与 PRD §3.8 完全一致 |
| C 配置 | **C4 Era Band 内拖拽重排（= 必答顺序）** | ✅ | §3.8 | 含管理员影响提示 |
| C 配置 | **C5 题库版本化 + Publish 发布** | ✅ | §3.8 | 配置页改的是**草稿版本**；**新增 / 编辑 / 删除 / 重排全部经 Publish 才生效**；存在草稿版本即激活按钮（§7.9） |
| C 配置 | **C6 维度配置** | ✅ | §3.8 / §3.1 | 配置页第二个顶层 Tab **`Dimension Configuration`**：可**新增 / 删除 / 排序 / 改权重**；维度集合与权重**整组保存、就地整组替换，不产生版本**（§7.11）；权重合计**必须 = 100%** 且需脏态才激活 Save；综合分按**当前 `status = 'Active'` 的维度集合**加权（§5.1.3 / §6.4 接口 23/24）。停用 / 删除落库均为置位、不删行（见 §1.2） |
| C 配置 | **C7 题库版本历史页** | ✅ | 原型（UI 参考） | `Question Library` Tab 的 `View history` 入口；**版本快照页**：页头版本下拉（取**接口 25**，**只列已发布版本**，草稿不进下拉）+ **各维度各一张只读题目表**（取**接口 26**；卡片张数按该版本的维度列表，由接口 26 出参 `dimensions[]` 下发 = 该版本**发布当时**的逐维快照，存于 `erl_question_config_dimension_version`（§5.1.5），后续维度增删改名不影响历史展示）。卡头**不显示 `Retired` 灰标**；**本页不取接口 23**，只读接口 25 / 26 |
| D 基准 | D1 基准记录页 + **D2 新增记录（独立页）** | ✅ | §4 | Benchmarkit / Top GSV Quartile 的**外部静态数据接入口**，平台不计算；**每期次按维度各录两个分**（维度条目数按当前 `status = 'Active'` 的维度集合动态）。入口：ERL Card 雷达图正下方 `View Top GSV Quartile & External Benchmarks ›`，**仅管理端** |
| E AI | **E1 Gap Analysis & Suggested Actions** | ✅ | §3.6 | gaps + 建议行动 + narrative；**单一口吻 + GSV 手动 Share 给 Founder 端**；ERL Card Gap 区块形态见 §8.4；提交后自动重生成（依据：本设计；任务 source ≠ 当前 SOT 即重跑，§7.5）；已分享的报告记录不被改写，重生成落在新的未分享记录上，需 GSV 重新 Share，期间公司端回到空态（§5.8 / §7.5） |
| E AI | **E2 每维 Strengths & Priority Gaps** | ✅ | §3.6 | 由证据/备注推导；无备注标注「未提供备注」。只输出 gap 条目，「有 gap 才展示建议」 |
| E AI | **E3 Share to Founder** | ✅ | §3.6 | 差距分析默认**仅 GSV 团队可见**；该 `(company, period)` 下**每个维度**的 FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录（同 `(company_id, period, portal, dimension_code)` 内按 `submitted_at DESC, id DESC` 取首条 `SUBMITTED` 判存在）时，`Share to founder` 按钮才激活。**接口 27** `POST /erl/gapAnalysis/share`（仅管理端）；`shared = false` 时公司端读到空态 |
| F 联动 | **F2 Portfolio ERL Tab** | ✅ | §3.7 | 跨公司总表；界面是纯展示表（无顶部筛选器与列头排序器），排序筛选的服务端能力保留（依据：本设计）；维度列**动态**，出参为 `dimensionScores[]`；展示期次为**各公司自己 closed month 所在季度**，取不到的回退当前自然季度（§7.1.2） |

### 1.2 明确不在 V1

| 项 | 原因 / 去向 |
|----|-------------|
| 独立 Exit Readiness 落地页 / Dashboard 路由 | **PRD §3.1 明确不做** |
| 顶栏 Ask Goldie 对话接入（E3） | 与 AI Chatbot 是另一条产品线 |
| Finance 页 Exit Readiness 卡片与入口（F1 / F3） | PRD 未要求；入口统一在 Company Overview 的 ERL Card |
| **完整 BPMM 评估交互** | PRD §5「不在本 story 范围内」；A1 卡片也不显示 BPMM 参考数字 |
| **每维状态摘要（`MET`/`PARTIAL`/`GAP` 徽章）** | PRD 无此展示项 |
| **Data Sources & Cadence 卡** | PRD 无此展示项 |
| **1–9 分打分控件 / 计分模式可切换的策略工厂** | PRD 已把打分格式定档为 Yes/No 逐级解锁，占位抽象属 YAGNI（§7.2） |
| **每维手动整体分与软确认弹窗** | PRD §3.3 / §3.4 无此要求 |
| Goldie 建议的正式跟踪 / 指派 / Deadline | PRD 未要求 |
| Goldie 生成结果的人工编辑 / 审核流 | 见 §13-Q9 |
| 评估期次间对比 / 趋势 / 导出 | PRD 未要求 |
| 「GSV vs. Founder 分数对比 Tab」MVP 替代方案 | PRD 未要求 |
| 题库导入导出、题库**公司级**覆盖 | PRD 未要求；题库按**组织（租户）**单份，组织内不按公司细分 |
| Fireflies 转录 / SharePoint 作为 Goldie 数据源 | PRD 未要求 |
| **维度的物理删除**（SQL `DELETE`） | 配置页的两个破坏性动作**落库都是置位、都不删行**：**停用** = 置 `status = 'Inactive'`（行与 `weight` 原样保留、可恢复）；**删除** = 置 `deleted = true`（行与 `weight` 同样保留，但**所有读侧排除、页面无恢复入口**）——「删除」指「从产品里彻底消失」，**不是 SQL `DELETE`**（§5.1.3 / §7.11-④）。置位下行不消失，历史提交仍能取到名称与缩写。**删除有前置拦截**：判据是「是否进入过已发布题库版本」，保护对象是**已发布题库版本的语义** |
| **展示期次在无数据时回退到更早期次** | 缺省期次 = closed month 所在季度，**该季度两端均无提交即空态，不回退** |
| 提交快照「基金 / 组合」「评估团队」（PRD §3.3 / §3.4） | 不落库：无权威数据源；GSV 填报页 `FUND` 按当下归属现算（§13-Q37） |

### 1.3 后续阶段索引

| 阶段 | 内容 |
|------|------|
| V1（本文档） | A（含 A7 三卡布局）/ B（含 **B4 Reset**）/ C（含 C6 **维度配置**、**C7 版本历史**）/ D / **E1 + E2 + E3 Share** / F2 |
| V2 | 完整 BPMM 评估、Ask Goldie 接入、Fireflies + SharePoint 数据源、Goldie 自动打分 |

---

## 2. 事实基线

### 2.1 存量代码事实（本次落地必须对接的现状，均已核对源码）

| 事实 | 位置 | 对设计的影响 |
|------|------|--------------|
| Company Overview 页的 **DI 卡片**由 `DiStatus` 状态控制显隐 | `CIOaas-web/src/pages/companyOverview/home/CompanyOverviewPage.tsx:82`（state）、`:1561`（`display: DiStatus ? '' : 'none'`） | ERL Card **插入**该位置，DI 卡片**下移到 FI 卡片之后**并**照旧受 `DiStatus` 控制**（不改它的渲染条件，§8.6） |
| `DiStatus` 来源于 `getSdpModulesSettings(companyId)` 的 `diStatus`，**按公司维度**存储，另写入 `localStorage.diStatus` | 同上 `:99-109`；`companySettings/components/modules/ModulesTab.tsx` | PRD 不要求隐藏 DI ⇒ 该开关语义原样不动，不新增 `erl.enabled` |
| 平台**租户 = `organization_id`**：JWT claim `organization_id` → `SecurityUtils.getOrganizationId()` / `UserContext.organizationId`；`ai_file_registry` 等存量表已按该列隔离 | `CIOaas-api/gstdev-cioaas-common/.../security/jwt/JwtTokenProvider.java:83`、`.../utils/SecurityUtils.java:63`、`.../web/ai/financial/extract/domain/AiFileRegistry.java:79` | PRD §4「ERL 配置层级按照**租户**层级」落到该列，**不新增租户概念**（§5.1.1） |
| 存量上传的单文件上限：chat 附件 `MAX_FILE_BYTES = 20 * 1024 * 1024` | `CIOaas-web/src/pages/devSupport/chat/components/InputBox.tsx:27` | ERL 附件上限 PRD 明确为 **10MB/个**，比 chat 更严 ⇒ **不能复用 chat 常量**，ERL 域自带 `ERL_MAX_FILE_BYTES = 10 * 1024 * 1024`（§6.7） |
| Portfolio Company List 的 Tab 键位：`1` General / `2` Investment / `3` Connections / `4` Issues / `5` Benchmarking | `CIOaas-web/src/pages/portfolioCompanies/home/PortfolioCompaniesPage.tsx:501, :825` | ERL Tab 取 **`key='6'`**，并在 `trackPortfolioButtonClick` 埋点分支补 `'ERL'` |
| 各 Tab 的内容组件是 `portfolioCompanies/` 下的**平级目录**（`Benchmarking/`、`Issues/`、`connections/`…） | `portfolioCompanies/` 目录树 | ERL Tab 组件放 `portfolioCompanies/erl/` |
| 文件直传通道：`storageService.uploadFile(file, fileBusinessType)` → presign → S3 PUT → verify，返回 `fileId` | `CIOaas-web/src/services/service/storage/storageService.ts:114`；类型枚举 `services/api/storage/dto.ts:8` | ERL 逐题附件复用该通道，`fileBusinessType = 'KNOWLEDGE_BASE'` |
| 「公司 Memory File / 知识库」登记 + 向量化的完整链路是 `ensure_kb_space` → `ingest_kb_file` → register → `start_vectorization`；Python `POST /api/ai/file-registry/records` 是只建登记行的低层入口 | `CIOaas-python/source/chatbot/application/service/chat_attachment_service.py:45-146`；`CIOaas-python/source/file_registry/interfaces/routes.py:267-284` | 只对 chatbot 自己的附件成立；ERL 附件**两条都不走** —— 摘要由差距分析 `refresh` 现场生成、不落任何库（§6.7） |

### 2.2 领域常量（PRD §一）

- **维度不是常量，而是租户级配置数据** —— 见 §5.1.3（`erl_dimension_config`）与 §5.1.5（`erl_question_config_dimension_version`，题库版本 ↔ 维度快照）。
  - PRD §3.8 把维度列表写作 `FRL / PRL / BERL / RRL / TRL...`，**省略号即表示不固定五个**；配置页可新增 / 删除 / 排序 / 改权重
  - `FRL` Financial Readiness / `PRL` Product Readiness / `BERL` Brand Equity Readiness / `RRL` Risk Readiness / `TRL` Talent Readiness 只是**叙述用的举例**（存量库里有这几行真实数据）；`V1__erl_init.sql` 不含种子数据，新库的维度集合完全由租户在配置页录入；维度不是编译期枚举，**接口驱动**（接口 23）
  - 维度 `code` 是**组织内稳定标识**，历史数据靠它关联；`code` **由服务端生成（`{abbr 前 3 位}{4 位随机}`，§5.1.3），此后永不改变**（`abbr` 可随时改名，`code` 不跟随，§5.1.3）；停用 = 置 `status = 'Inactive'`、删除 = 置 `deleted = true`，行均保留（§1.2），历史提交记录照常显示（名称/缩写取评估行快照），但**实时聚合值（综合分 / Stage / 雷达图）会因停用而变**
  - 维度数一律按当前 `status = 'Active'` 的维度集合取，不固定为五
- **9 级 Stage 分 3 个 Era**（领域常量）：Founder Era（Stage 1–3）、Harvest & Growth Era（Stage 4–6）、Exit Era（Stage 7–9）
- **题目 level（= Era band）**：9 档 —— `Founder Era - 1/2/3`、`Harvest & Growth - 4/5/6`、`Exit Era - 7/8/9`。**一道题恒属一个 level**，一个 level 内可有多题（PRD §3.3 的「level」与本设计的 `era_band` 是同一概念，字段名用 `era_band`、展示标签用 `Era-level`）
- **分数值域**：**维度分 = 0–9 整数**（最后一个全 Yes 的 level；level 1 即出现 No → `0`）；**综合分（UI 文案统一为 `Overall Score`）= 0.00–9.00 两位小数**（F2 同为两位小数），按**当前 `status = 'Active'` 的维度集合**中各维度的权重加权求和
- **评估频率**：季度（PRD §4「评估周期：季度提交」）；**展示缺省期次 = 该公司 closed month 所在季度**（口径复用 Financial Intelligence 域既有服务，读其每日 KPI 快照，见 §3.1 / §3.2）
- **提交粒度**：一次提交 = **某公司 + 某期次 + 某端 + 单个维度**

### 2.3 原型可复用的事实（仅 UI 与口径参考）

> 原型（Lovable 已发布站 `https://exit-readiness-hub.lovable.app`）**无后端，全部数据为前端硬编码 mock**，数据模型与接口契约由本文档定义。原型为**固定五维**形态，只作 UI 排版与文案参考：条目数一律按当前 `status = 'Active'` 的维度集合动态渲染，不得据此把维度数写死；**原型的分数展示、雷达图取值、Score Details 的逐题 `x.x/9` 均属旧口径，不得照抄**（维度分为 level 整数 0–9，§7.1）。

| 结论 | 证据 | 用途 |
|------|------|------|
| 填报页吸底条文案：`Keep answering the current level. The next level unlocks when every answer is Yes; a No ends the dimension.` / 完成时 `All questions answered — ready to submit.` | 原型填报页 | 文案可复用（§8.4） |
| Era 徽章配色 token：`--founder:#e1990f` / `--harvest:#ded87a` / good `#1e8e4a`；标签 `Founder Era - {n}` / `Harvest & Growth - {n}` / `Exit Era - {n}` | 已发布 chunk 原始 token | 与 §6.2 的 `eraLabel` 口径一致 |

---

## 3. 架构总览

### 3.1 落点

```
CIOaas-web (React 16 / UmiJS 3 / AntD Pro)
   src/pages/companyOverview/home/           A1/A2：ERL Card（改存量页，占原 DI 卡右列位置，§8.6）
   src/pages/exitReadiness/**                ERL 页面群（维度详情 / 全维明细 / 填报 / 历史 / 配置 / 基准）
   src/pages/portfolioCompanies/erl/         F2：Company List 第 6 个 Tab（改存量页）
   src/services/api/exitReadiness/           HTTP 调用（1:1 后端接口）
   src/services/service/exitReadiness/       Response ↔ DTO 转换
        |
        |  /api/web/erl/**            <- 前端只调 Java，不直连 Python
        v
Gateway :9000  -->  CIOaas-web(Java) :5213/web
                        com.gstdev.cioaas.web.erl/      <- 新建业务域，DDD 四层
                        |       |
                        |       +- POST /api/ai/erl/gap-analysis/refresh  同步 HTTP（LLM 生成 + 落库）
                        |       +- POST /api/ai/erl/gap-analysis/items    按任务批量取条目
                        |       |      erl 域只有这两个端点；附件摘要在 refresh 内现场生成（§6.7）
                        |       |             v
                        |       |  CIOaas-python  source/erl/  <- 编排 + 事务 + 落库，持有
                        |       |                 ai_erl_gap_analysis_task / _task_item 两张表；
                        |       |                 生成在 source/ai/agent/erl_gap_agent/gap_analysis.py
                        |       |                 +- 复用 source/llm/ 基建
                        |       |                 +- 只调 rag 的 IngestService.summarize_file_inline
                        |       |                 |   （下载 → 解析 → 摘要，不建 entry / space / 登记行）；
                        |       |                 |   摘要覆盖全文，超过 6 万字符分段并发（每份 ≤ 6 路）+ 合并
                        |       |                 +- prompt 放 source/ai/prompts/erl/（单份，
                        |       |                     不分 Founder / GSV 两套口吻）
                        |       |
                        |       +- 进程内调用 fi/（Financial Intelligence 域）
                        |             closed month 服务（读其每日 KPI 快照）—— 求「该公司 closed month 所在季度」
                        |             作为所有读接口的缺省期次
                        v
                   PostgreSQL   ← Java 侧 11 张表
                     erl_question_config_version / erl_question_config
                     erl_dimension_config
                     erl_question_config_dimension_version      ← 题库版本发布时的维度快照
                     erl_assessment                             ← 含 dimension、level_score /
                     erl_assessment_answer / erl_answer_attachment   terminated_level / unlocked_level
                     erl_reference_score / erl_reference_score_item
                     erl_gap_analysis_report / erl_gap_analysis_dimension_task  ← 报告分享记录 / 维度任务（§5.8）
```

- **前端只有一个后端出口**（Java），不出现前端直连 Python 的路径。
- Python 侧**不做公司 ACL**（Java 已校验）。它持有差距分析任务的两张表（`ai_erl_gap_analysis_task` / `ai_erl_gap_analysis_task_item`）；**其余 ERL 业务表（评估 / 维度配置 / 题库 / 附件）属 Java，Python 不查**。
- 不使用 SQS：ERL 的 LLM 调用是单次秒级，理由见 §3.2。
- **ERL 域对 Financial Intelligence（`fi/`）域有跨域依赖**：所有 `period` 可选的读接口（1 / 17 / 20 / 22）缺省期次 = **该公司 closed month 所在季度**，closed month 沿用 FI 域既有口径（按公司 Manual / Automatic 两种推导，数据来自 Financial Entry actuals；读 FI 每日 KPI 快照 `company_quickbooks_data.last_updated`）。约束：
  - **复用 FI 既有服务，ERL 不自己算 closed month**，也不复制其推导逻辑；调用方向单向 `erl/ → fi/`，不得反向
  - closed month 取不到 → 回退当前自然季度（§7.1.2）
  - 该季度两端均无提交 → **同样空态，不回退**

### 3.2 关键决策与理由

| 决策 | 理由 | 否掉的替代方案 |
|------|------|----------------|
| ERL 入口是 **Company Overview 页内的卡片**，不建独立落地页 | PRD §3.1 明确要求；卡片是唯一入口 | ❌ 独立 `/exitReadiness` Dashboard 路由 |
| **DI 卡片保留在页面上、下移到 FI 卡片之后** | PRD §3.1「DI 卡片**放在 FI 卡片下**；DI 数据、打分**保留概览信息和入口**」 | ❌ 新增 `erl.enabled` 开关隐藏 DI（PRD 不要求隐藏）；❌ 删除 DI 组件与接口 |
| 新建 Java 业务域 `erl/`，走 **DDD 四层** | `standards/architecture.md` §1 强制；`quickbooks/`、`thirdParty/` 已是四层实现可作参照 | ❌ 仿照 `fi/` 的扁平结构 —— 那是历史遗留，不得在新域复制 |
| ERL 不并入 `fi/`（财务域） | ERL 覆盖多个维度，不属财务域 | ❌ 放 `fi/erl/` |
| **LLM 生成落 CIOaas-python，Java 经网关同步调用** | Java 侧零 LLM 客户端（全仓检索 bedrock / anthropic / openai / claude 的命中全是 SQS 消息类）；Python 有 `source/llm/` 完整基建 + Prompt 管理规范 + 调用追踪 | ❌ 在 Java 接 LLM SDK —— 要重建模型配置、Prompt 管理、调用追踪 |
| Java 与 Python 之间走 **HTTP 经网关**，不走 SQS | 单次、秒级、用户可等待 | ❌ SQS 异步 —— 为一个秒级调用付全套异步成本 |
| **差距分析提交后自动重生成 + 落库缓存** | 依据：本设计（实现手段）。边界：已分享的报告记录不被改写，重生成落在新的未分享记录上，需 GSV 重新 Share，期间公司端回到空态（§5.8 / §7.5） | ❌ 仅前端手动触发；❌ 每次进页面实时生成（Company Overview 首屏会被 LLM 阻塞）；❌ 重生成后静默改写 Founder 已看到的内容 |
| 自动重生成走**提交事务外的异步任务**，是否重跑由 `reconcile` 比对任务 source 与当前 SOT 判定（§7.5），进行中的维度小卡显示 `Analyzing…` | 提交动作本身不能被 LLM 时延拖住 | ❌ 在提交事务里同步调 LLM —— 提交接口 RT 不可控，LLM 失败会回滚提交 |
| **评估记录不加 `(company, period, portal, dimension)` 唯一约束**，按 `submitted_at DESC, id DESC` 取 SOT（无数据库级「至多一条 SOT」保证，§5.2） | PRD §3.3 / §3.9 要求同季多次提交且全量留档 | ❌ 唯一约束（会丢历史提交） |
| **提交粒度 = 维度级** | 一次提交 = 某公司 + 某期次 + 某端 + **单个维度**；提交前置校验为「**本维度终止**」；PRD §3.5 / §3.7 的「每维 `Add New` / `View History`」由此天然成立；逐级解锁天然按维度独立 | ❌ 整卷一次提交 —— 单维完不成就全卷交不了，且与 PRD 的每维入口矛盾；❌ 另设维度子表 `erl_assessment_dimension`（维度级后恒一行，属多余一层） |
| **同一期次不同维度允许绑不同题库版本** | 维度级提交后 `erl_question_config_version_id` 的绑定粒度**每维一份**；先交的维度锁旧版、后交的锁新版是正常现象，**系统不阻止、不告警**，各自按自己的版本渲染与计分 | ❌ 强制同期次全维同版本 —— 会要求先交的维度回退重填，与「提交后即只读」冲突 |
| **维度分 = 逐级解锁推导的 level 分，无任何手动录入** | PRD §3.1 / §3.3「该维度最后一个全部 Yes 的 level 的 level 为此维度得分」「分数就是此回答为 No 的 level 减一」 | ❌ 维度分 = 题均分；❌ 手动录入维度分 / 软确认弹窗（PRD 无此要求） |
| **综合分按配置权重加权**，权重独立保存、**不随版本化** | 维度与权重只有一份**当前值**（`erl_dimension_config`，§5.1.3），综合分**实时按当前权重算** —— **改权重 / 增删维度会回溯改变历史期次的综合分与 Stage（已接受）**；§7.10-W1 接受历史漂移，§13-Q21 | §5.1.3 / §7.1 / §7.11 / §13-Q21 |
| **题库、维度配置按组织（`organization_id`）隔离**，不按公司 | PRD §4「ERL 配置层级按照**租户**层级」；平台已有 `organization_id`（§2.1） | ❌ 题库全局单份（跨租户串题）；❌ 按公司隔离（PRD 只说到租户层级，公司级覆盖是 §1.2 明确不做的） |
| **展示缺省期次 = closed month 所在季度，无数据即空态** | 季度提交的口径要与财务已结账月对齐，避免展示一个财务上尚未闭合的季度；closed month **复用 FI 域既有服务**，ERL 不自己算（§3.1） | ❌ 缺省 = 最新已提交期次；❌ 无数据时回退到更早期次 —— 会悄悄显示上一季数据，用户误以为是本季结果 |
| **计分不做策略抽象**，只有一个 level 计分器 | PRD 已把打分格式定档，策略工厂成了为假想场景预留的扩展点，违反根 `CLAUDE.md` 的 YAGNI | ❌ `ErlScoringStrategy` + `ErlScoringStrategyFactory` + `erl_assessment.scoring_mode` 快照 |
| 答案表 `erl_assessment_answer` **一行一题**，不做 JSON 大字段 | 需要按维度 / level 聚合、按题 join 题库、逐题挂附件与备注 | ❌ `answers jsonb` |
| **附件只有题级一种粒度**，双端同口径：表 `erl_answer_attachment`、`erl_assessment_answer_id` not null | 粒度归一后「附件属于哪道题」是表上自明的事实，不需要「空 / 非空」这种隐式区分标志 | ❌ 可空 `erl_assessment_answer_id` 只在服务端拦维度级写入（表结构仍在说谎，日后必被误用）；❌ `erl_answer_attachment` + `erl_dimension_attachment` 两张近乎相同的表 |
| **计分不落库、实时算**（含维度 level 分与加权综合分） | 与 §12「不冗余存储聚合分数」一致；level 分由答案唯一决定，无二义。**加权综合分与 Stage 一律按当前 `status = 'Active'` 的维度集合与其当前 `weight` 实时算**（§7.1 / §7.11）—— 故会随配置变更**回溯改变历史期次的值**（已接受，§13-Q21）。某维无分（未填 / 0 题）按 0 计入、其余权重不归一化（§7.1） | ❌ 提交时把综合分 / Stage 写死 |
| 草稿与正式提交**同一条记录**，用 `status` 区分；提交后该行冻结，再改则新建下一条 | PRD §3.3「支持保存进度」+「提交后即只读，如需修改必须新建一次提交」 | ❌ 独立草稿表 |
| **题库版本化**：版本表 + 写时复制草稿版本，所有配置变更经 Publish 生效 | 需求方要求「所有变更都经发布」；状态位只能表达「新增未发布」，表达不了「同一题的编辑前后两份题干」 | ❌ `publish_status` 状态位（编辑无法两态并存）；❌ 双表（草稿表 + 正式表，等于版本化但只能存两代、且两套 DDL 要同步维护） |
| 题目删除 = **在草稿版本内物理删行** | 历史评估绑定题库版本快照，已发布版本的行不会被删，软删标记失去价值 | ❌ 软删 —— 版本内留一堆 `enabled=false` 的行，查询恒要带条件 |
| **必答顺序落在 `erl_question_config.sort_order`**，配置页拖拽即改该列 | PRD §3.8「该顺序即评估中的必答顺序」 | ❌ 顺序只做展示、计分顺序另存 |
| **level 计分收在 `application/scoring/ErlLevelScorer` 一个类里** | 逐级解锁的「终止 level」判定同时被填报解锁、提交校验、展示计分、组合层、Goldie 输入五处消费，散写必然漂移 | ❌ 把 level 判定散写在各 service；❌ 策略接口 + 工厂（只有一种模式，抽象无消费者） |
| Gap analysis 绑 **`(company_id, period)`**（不分 audience）+ `shared` / `shared_at` / `shared_by` 状态位 | PRD 要求单一口吻、「GSV 团队可见，点 `Share to founder` 分享给 Founder 端」⇒ 一份 prompt；激活门槛 = 该 `(company, period)` 下**每个维度**的 FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录（同 `(company_id, period, portal, dimension_code)` 内按 `submitted_at DESC, id DESC` 取首条 `SUBMITTED` 判存在）（接口 27） | ❌ 绑单个 `assessment_id`；❌ 按 Founder / GSV 两套口吻各生成一份；❌ 生成即对 Founder 可见（PRD 要求 GSV 主动 Share） |
| ERL 附件**不入知识库、不向量化、不登记**：唯一消费方是 Goldie 差距分析，摘要在 `refresh` 时现场生成、用完即弃（§6.7） | 知识库链路与 `file-registry/records` 都只服务 chatbot（§2.1） | ❌ 走知识库完整入库链路；❌ 直接调 `POST /api/ai/file-registry/records` |
| 前端新增 API 域 `exitReadiness/` | `standards/architecture.md` §2 的现有域无一匹配 | 需同步登记进 §2 域表，见 §13-Q7 |

---

## 4. 鉴权与端类型

### 4.1 角色映射

PRD §4 的权限模型 → 平台现有机制：

| PRD 角色 | 平台判定 | 说明 |
|----------|----------|------|
| Company User / Company Admin（Founder 侧） | `user.roleType > 1`，公司锁定 `user.inviteDto.id` | 公司端 |
| Portfolio Manager / Portfolio Group Manager（GSV 侧） | `user.roleType <= 1`，公司取 URL `?id=` | 管理端 |
| ERL Configuration 管理员 | 管理端（PRD §3.8「**仅 portfolio portal**」）**且** 具备配置权限（粒度见 §13-Q7）；**其读写一律限定在调用者自己的 `organization_id` 内**（PRD §4「ERL 配置层级按照租户层级」） | 顶部导航右侧下拉入口；题库版本与维度配置按组织隔离（§5.1.1 / §5.1.3） |

沿用存量财务页已有的同一套判定（`src/pages/financial/home/FinancialPage.tsx:99`），**不新增端类型机制**：

```
companyId = user.roleType <= 1 ? getQueryString('id') : user?.inviteDto?.id
isAdmin   = user.roleType <= 1        // 管理端（portfolio portal）
```

> ⚠️ **前端端类型判定只认 `roleType`，禁止用 `isAdminEnd()`**：`isAdminEnd()` 是**域名白名单**（`utils.ts:304`，只认 `admin.lgpi.io` / `admin-staging|uat|test.lgpi.io`），在 **`localhost` 上恒为 `false`** —— 用它判端会让本地开发时整个 ERL 前端锁死在公司端形态（无 GSV Tab、无雷达图、无基准、`portal` 恒被归一回 `FOUNDER`），管理端功能在本地**完全不可达**。全仓 `src/pages/` 有 **100+ 处** `roleType` 同款写法，`isAdminEnd()` 仅 5 处且属域名路由用途 —— 后者不是功能可见性的判据。

### 4.2 页面与端的对应（按 PRD §3 逐条收紧）

| 页面 / 元素 | 公司端（Founder） | 管理端（GSV） | PRD 依据 |
|------|:---:|:---:|------|
| A1 ERL Card | ✅ 只看本公司 | ✅ 看所选公司 | §3.1 |
| **A1 卡片内的 GSV 维度分** | ❌ **不可见** | ✅ | §3.5「创始人（公司 portal）：**只能查看自己的分数**」 |
| **A1 卡片内的 Perception Gap** | ❌ **不可见** | ✅ | 同上 —— gap 与自己的分合起来可反推 GSV 分，给 gap 等于给分。⚠️ PRD §3.1 卡片清单仍列 Perception Gap，以本设计为准 |
| **A2 雷达图（整图）** | ❌ **不渲染** | ✅ 4 条序列 | §3.5「**该图仅在 Portfolio 端显示**」 |
| A3 维度详情页 | ✅ 只看本公司 | ✅ | §3.2 |
| A3 **GSV Tab（逐题明细）** | ❌ **不显示** | ✅ | §3.2「公司用户不显示 GSV Tab」 |
| **A3 页头的 GSV 维度分 / Perception Gap** | ❌ **不可见** | ✅ | §3.5（同 A1 两行） |
| **A4 全维 Score Details 页** | ✅ 只看本公司，**经 ERL Card 右上角 `Full View ›` 进入** | ✅ 由 F2 `View` **或** ERL Card 的 `Full View ›` 进入 | §3.7 + §3.5 |
| **A4 每张维度卡卡头的 `Add New` / `View history`** | ✅ 仅 Founder 侧（单端模式，`+ Add New` 照常渲染 → 填报页带 `?dimension={code}`） | ✅ 双端数据一次取回、以 `GSV` / `Founder` 药丸切换查看；**`+ Add New` 只在 `GSV` 药丸下渲染**，`View history` 两侧都有 | §3.5 / §3.7；无**页级** `+ New` / `View history`。⚠️ 这是**渲染条件**，不是权限口径 —— 后端仍按 §4.3 校验，`addNewUrl` / `historyUrl` 一律由接口 22 下发，前端不拼路径 |
| A4 **GSV 药丸与末位基准 Tab** | ❌ **不显示** | ✅ | §3.2（同 A3 口径，服务端裁剪）。⚠️ **基准 Tab 的显隐判据是「端类型」，不是 `benchmark == null`** —— 服务端在「公司端不下发」与「管理端但该期次无基准记录」两种情况下都发 `null`，按 `null` 判会让还没录过基准的管理端整个 Tab 消失 |
| E1 / E2 差距分析（展示） | ✅ 只读，**仅 `shared = true` 后**（`shared = false` 时接口 17 对公司端直接返回空态） | ✅ 只读（生成即可见，无需 Share） | §3.6 |
| **E1 / E2 维度小卡的 `No Gap`** | ✅ **仅分享后**；评分相等的维度两端都显示 `No Gap` | ✅ | ⚠️ **已知取舍**：创始人可据此得知 GSV 该维打分与自己**相同**（只透露「相同」，不给分值、不给 Perception Gap），已接受 —— 分享出去的差距分析正文本来就逐题对照两端答案，透露面更大。若日后收紧，改为只在管理端出参判 `No Gap`，代价是两端显示不一致 |
| **E1 / E2 已分享记录上的 `questionSetMismatch` / `bothSubmitted`** | ✅ 按**当前**提交状态现算，不随已分享记录冻结 | ✅ 同左 | 分享后某维两端换版（或补交）⇒ 若其余维度依据未变，**不新建记录**（`forkSharedReport` 无变化维度即返回原记录），创始人仍看这份已分享记录，但该维小卡现算成 `New version pending`、弹框里该维已分享的结论**不再渲染**（前端优先级 mismatch 先于 hasGap）。方向安全，已接受 |
| **E3 `Share to founder` 按钮** | ❌ **不可见** | ✅ 门槛未达成时置灰（该 `(company, period)` 下每个维度的两端都有 `SUBMITTED`（按 `submitted_at DESC, id DESC` 判存在）才激活）；接口 27 | §3.6 |
| E 手动 Regenerate | ❌ | ✅（接口 18；前端目前无入口） | 本设计（自动刷新为主，手动为兜底） |
| B1 Founder 自评问卷 | ✅ **填报** | ✅ 只读查看 | §3.3「portfolio admin 不能代填」 |
| B2 GSV 验证问卷 | ❌ 不可见 | ✅ **填报** | §3.4 |
| B3 评估历史 | ✅ 只看本公司 | ✅ | §3.9 |
| **B3 的 `Portal` 列** | ❌ **不渲染**（公司端只有 Founder 侧数据，该列恒定值、无信息量） | ✅ 渲染 | §3.9 |
| **B4 Reset / 丢弃草稿** | ✅ 对自己公司的 Founder 草稿 | ✅ 对 GSV 草稿；接口 28 按 `portal` + `dimension` 定位草稿 | §3.3 |
| C1–C7 题库配置（含 Publish、**`Dimension Configuration`**、**版本历史**） | ❌ 不可见 | ✅ 且**只能读写本 `organization_id` 的题库与维度配置** | §3.8「**仅 portfolio portal**」+ §4「ERL 配置层级按照租户层级」 |
| D1 基准记录页 | ❌ **不可见** | ✅ | §3.2（基准属 GSV 专属字段） |
| **ERL Card 雷达图下方 `View Top GSV Quartile & External Benchmarks ›` 链接** | ❌ **不渲染**（仅管理端；雷达图另有 < 3 维度不渲染的门槛，本链接**不跟**） | ✅ | §3.5 |
| D2 新增基准 | ❌ | ✅ | §4 |
| F2 Portfolio ERL Tab | ❌ 不可见 | ✅ | §3.7「仅 PM / PGM」 |

> 现口径（PRD §3.5「创始人**只能查看自己的分数**」）：
>
> - 公司端**只见 Founder 侧的一切**（自己的维度分、综合分、Stage、逐题作答、备注、附件）；
> - 公司端**看不到** GSV 维度分 / GSV 综合分 / Perception Gap / GSV 逐题明细 / 雷达图 / Benchmarkit / Top GSV Quartile；
> - 以上一律**服务端裁剪**，不靠前端隐藏（§4.3）。
>
> ⚠️ **残留矛盾**：PRD §3.1 的卡片内容清单仍把「Perception Gap」列为卡片内容且无端限定，而卡片在公司端也要渲染。设计口径已定，只剩 PRD 清单未同步；本设计按「公司端不给 gap」落地。

### 4.3 后端强制校验（不依赖前端）

> ⚠️ **业务错误的 HTTP 形态**：ERL 服务层的业务校验失败一律 `throw new BadRequestException(...)`（`assertNotStale`、入参形态校验、集合完整性校验、空入参、组织 / 端类型越权……全是它），而 `gstdev-cioaas-common` 的 `GlobalExceptionHandler` 对 `BadRequestException` / `ServiceException` / `EntityExistException` / `EntityNotFoundException` 四者**统一返回 `HttpStatus.OK` + `Result.fail(message)`**，即 **HTTP 200 + `success: false` + 提示语**（与乐观锁冲突 `OptimisticLockingFailureException` 同形态）。全文「业务错误」均指此形态。
>
> ⚠️ **真正的非 200 只有三类**：① `UnrecognizedPropertyException`（请求体带未知字段）→ **HTTP 400**，这是本仓库唯一会返回 400 的分支；② `MethodArgumentNotValidException` / `BindException`（`@Valid` 校验、参数绑定失败）→ **HTTP 422**；③ 兜底 `Throwable` → **HTTP 500**。
>
> ⚠️ **对前端与测试的实际影响**：抓包核对时**看 `success` 字段与 `msg`，不要看状态码** —— 按状态码 400 写断言会全部失败；前端 axios 拦截器也不会把它当成网络错误。

- 所有接口的 `companyId` 一律**服务端复核**：公司端请求忽略入参 `companyId`，强制取当前登录用户所属公司（`SecurityUtils`）；管理端才允许按入参取。
- **C 模块（题库 + 维度配置）的 `organization_id` 缺省取 `SecurityUtils.getOrganizationId()`，接受可选入参 `organizationId`**：不传即登录态组织；传值时服务端按**组织树**复核 —— 只认调用者自身组织或其子孙组织，否则 `BadRequestException("You do not have access to this organization.")`。校验集中在 `ErlAccessService.resolveOrganizationId(...)`，各 service **显式传参**、不从请求上下文夹带。跨组织树读写他人题库 / 维度配置直接 `BadRequestException`。
- **维度配置的租户隔离与合法性校验**：
  - 接口 23 / 24 只操作调用者 `organization_id` 名下的 `erl_dimension_config` 行（入参无 `versionId`）；写入时按 `(organization_id, dimension_code)` upsert，**跨组织的 `dimension_code` 天然命中不到**。
  - 接口 24 保存前服务端**必须**校验：① 数组每项**显式二选一**：带 `dimensionCode`（已有，必须命中本组织已有行）或带 `isNew: true` + `clientRef`（新增，服务端生成 code）；两者都不带 / 同时带 → **业务错误**（HTTP 200 + `success: false`）。**并做集合完整性校验**：当前 `Active` 且**未删除**的集合 恰等于 带 code 的项 ∪ `deactivatedCodes` ∪ **`deletedCodes`**（缺第三项则每次删除都被误判为漏传），对不上即**业务错误**（HTTP 200 + `success: false`）（防前端漏传造成静默软删 + 身份分叉）；新增 code 与已有 code 冲突时服务端内部重试 —— 用户无法指定 code，天然撞不到旧 code；② **`status = 'Active'` 的维度**的 `weight` 合计**恰为 `100.00`**（`Inactive` 行不计入），且**至少保留一个 `Active` 维度**；③ 提交里**缺席的维度置 `status = 'Inactive'`（软删，不删行）**；④ **`deletedCodes[]` 里的每个 code** 必须命中本组织已有行、且**不得出现在任何已发布题库版本的维度快照里**（join `erl_question_config_version` 过滤 `status = 'PUBLISHED'`），并**不得与 `dimensions[]` / `deactivatedCodes[]` 里的 code 重叠**；三者任一不满足即业务错误（HTTP 200 + `success: false`）且**库中无任何写入**（文案与理由见 §6.4-3-⑧⑨⑩）。⚠️ **前端不显示垃圾桶不等于拦住了** —— 抓包可以直接给已发布维度的 code 传 `deletedCodes`，这条服务端校验是唯一的实际防线。校验通过即**就地整组替换**。
  - 一切按期次渲染维度、计分、绘雷达图的读接口，**服务端按 `erl_dimension_config` 取当前 `status = 'Active'` 的维度集合**，不接受前端传入的维度配置参数。
- **填报写接口的维度合法性**：接口 4 / 5 / 28（存草稿 / 提交 / Reset）的入参 `dimensionCode` **必须属于当前 `status = 'Active'` 的维度集合**（查 `erl_dimension_config`；**`Inactive` 的维度也算不合法**；`deleted = true` 的行已从所有读侧排除，「当前 `Active` 集合」天然不含它，无需额外分支），否则**业务错误**（HTTP 200 + `success: false`），并按配置里的规范写法归一大小写。不校验则任何满足 `^[A-Za-z0-9]{1,8}$` 的字符串（如 `ZZZ`）都能一路落库成 `SUBMITTED`，污染 ERL Card / 组合层 / Share 门槛判定，还会白触发一次 LLM 差距分析。只读的接口 3 同样校验（它要拿配置项渲染页头）。
- **差距分析的 share 可见性**：接口 17 在**公司端**调用且该 `(company_id, period)` 的**最新一条**记录 `shared = false`（含无记录）时，**直接返回空态**，不下发 `narrative` / `gaps` / `actions` / `dimensions` 中的任何分析内容。**是不下发，不是下发后前端隐藏**。接口 27（Share）仅管理端可调。
- `portal=GSV` 的读写（B2 填报、A3 的 GSV 逐题明细）、C 模块写接口、D 模块全部接口、E 的生成接口与**接口 27 Share**、F2 的跨公司查询，服务端一律校验调用者为管理端，否则 `BadRequestException`。
- **公司端请求一律裁剪掉以下字段**（PRD §3.5）：`gsvScore`、`perceptionGap`、整个 `radar`、`benchmark*`（`benchmarkitScore` / `topQuartileScore` / `benchmarkPosition`）。**是不下发，不是下发后前端隐藏**。
- **F2 只返回当前用户有权访问的公司集**，不返回全库。
- Java → Python 的两个内部接口带服务间鉴权；Python 侧不重复做公司 ACL，但**必须落 LLM 调用追踪**（复用 `source/llm/`）。
- 违规一律抛异常交 `GlobalExceptionHandler`，**Controller 内不 try-catch**（`standards/architecture.md` §3）。

---

## 5. 数据模型

> 库：PostgreSQL 业务库。Java 侧 `ddl-auto: update` 由 Entity 自动建表；索引 / 约束补 `CIOaas-api/deploy/upgrade_doc/sprint{N}/erl_init.sql`（**该脚本不含任何种子数据**）。所有实体继承 `AbstractCustomEntity`，自动带 `created_at / created_by / updated_at / updated_by`。主键 `String(36)` + `@UuidGenerator`（与 `quickbooks_*` 一致）。

**表清单**（Java 11 张 + Python 2 张）

| # | 表 | 小节 | 归属 |
|---|------|------|------|
| 1 | `erl_question_config` | §5.1 | Java |
| 2 | `erl_question_config_version` | §5.1.1 | Java |
| 3 | `erl_question_config_dimension_version` | §5.1.5 | Java |
| 4 | `erl_dimension_config` | §5.1.3 | Java |
| 5 | `erl_assessment` | §5.2 | Java |
| 6 | `erl_assessment_answer` | §5.4 | Java |
| 7 | `erl_answer_attachment` | §5.5 | Java |
| 8 | `erl_reference_score` | §5.6 | Java |
| 9 | `erl_reference_score_item` | §5.6.1 | Java |
| 10 | `erl_gap_analysis_report` | §5.8 | Java（建表脚本 `deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql`，含部分唯一索引） |
| 11 | `erl_gap_analysis_dimension_task` | §5.8 | Java（同上；状态机 `PENDING / RUNNING / SUCCESS / FAILED`） |
| 12 | `ai_erl_gap_analysis_task` | §5.8 | Python |
| 13 | `ai_erl_gap_analysis_task_item` | §5.8 | Python |

> **E 模块（Goldie）的表无条件建**：Java 两张 + Python 两张（Python 的走版本化迁移，不走 Java `ddl-auto`），见 §5.8。

### 5.1 `erl_question_config` — 题库（PRD §3.8）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`organization_id`** | **varchar(36)** | **not null** | 所属组织（租户）。取值缺省来自 `SecurityUtils.getOrganizationId()`（§2.1），可由可选入参 `organizationId` 指定组织树内的组织（§4.3） |
| **`question_key`** | **varchar(36)** | **not null** | **跨版本稳定的题目标识**。克隆时原样复制，新增题时生成新 UUID。**版本 diff（`changeType`）与 C 模块写接口定位按它**，不用 `id`。答案表不携带它 |
| **`dimension_code`** | **varchar(8)** | **not null** | **创建时生成、与 `dimension_abbr` 解耦**。**组织内稳定** —— `erl_question_config.dimension_code`、`erl_assessment.dimension_code`、`erl_reference_score_item.dimension_code`、`erl_question_config_dimension_version.dimension_code`、`erl_gap_analysis_dimension_task.dimension_code` 五处历史数据全靠它关联，故**一经创建即永不改变**。<br>**生成规则：`{前缀}{随机后缀}`，如 `OPS4K7M`**<br>· **前缀** = 创建时 `dimension_abbr` 的**前 3 位**（大写化，只保留 `A-Z0-9`；不足 3 位就用实际长度）—— **只是创建时的一次快照，此后 `dimension_abbr` 怎么改都不影响它**。<br>· **后缀** = **4 位随机**，字符集取 **Crockford Base32**（`0-9A-Z` 去掉 `I` / `L` / `O` / `U`）—— 去 `I/L/O/U` 是为了 `0/O`、`1/I/L` 不混淆（这串要被人从日志里抄进 SQL），去 `U` 顺带避开冗余拼出冒犯性单词。<br>· **总长 ≤ 7**，`varchar(8)` **留 1 位余量**（日后加前缀 / 校验位不用 ALTER 五张表）。<br>· **唯一性按全局查重**（生成时 `SELECT 1 WHERE dimension_code = ?` **不带 `organization_id`**）—— 落库约束仍是组织内唯一，但全局查重成本为零，可让「用户新建的维度」彻底免疫跨租户串号。<br>· ⚠️ **生成必须在写事务之前完成**（循环「生成 → 查重 → 命中则重生成」+ 本次请求内维护已分配集合），**不得在整组替换的事务内 catch 唯一冲突重试** —— PostgreSQL 下唯一冲突会把整个事务置为 aborted，同事务内重试必抛 `current transaction is aborted`；且 JPA 延迟 flush 会让冲突在提交那一刻才爆。真撞上了就**整个请求失败重试**，不在事务内继续。<br>· 页面上哪里都不显示、**也不允许用户指定**（§8.4-C6） |
| `era_band` | smallint | not null, 1–9 | **题目归属的 level**（PRD §3.3 的「level」即此列）；Era 由此推导（1–3 Founder / 4–6 Harvest / 7–9 Exit）。**逐级解锁与维度分判定的唯一依据**（§7.2） |
| `question_text` | **varchar(2048)** | not null | 题干。配置页 C2 / C3 的输入框限 **2000 字符**（前端 `maxLength` + `n / 2000` 字数提示），库留 48 余量，**那 48 不是第二个业务上限**；服务端 `@Size(max = 2048)` 跟列宽走 |
| `evidence_source` | varchar(255) | | 来源标签（**`Founder / CFO`**、`Looking Glass`、`SharePoint`、`GSV Assessment`、`Board Transcripts / Fireflies`…）；空显示 `—`。**PRD §3.3 写的 `Founder/CTO` 是输入错误**，以 `Founder / CFO` 为准 |
| `sort_order` | int | not null | **同 `dimension_code + era_band` 内的必答顺序**，配置页拖拽即改此列（PRD §3.8）。**level 内的作答顺序**，跨 level 的推进由解锁规则控制（§7.2） |
| **`version_no`** | **int** | **not null** | **按 `dimension_code` 自增**的题目集版本号，从 1 起 —— **每个维度各有一条独立的版本线**（`FRL` 到 v7 时 `PRL` 可能才 v2）。一行只属于「该维度的某一版」；同一维度的版本间整份克隆，故同一道题在该维度的 N 个版本里有 N 行。⚠️ **与 `erl_question_config_version.version_no` 不是同一个东西** —— 后者是**组织级发布批次号**（§5.1.1），两者由 §5.1.5 的快照表建立对应关系 |

约束与索引（定位键 `(organization_id, dimension_code, version_no)`）：
- `uk_erl_question_config_key (organization_id, dimension_code, version_no, question_key)` —— **同组织同维度的同一版本内**一个 key 只有一行。
- `idx_erl_question_config_version_dim (organization_id, dimension_code, version_no, era_band, sort_order)` —— 配置页与填报页的主查询路径（**恒带 `(organization_id, dimension_code, version_no)`** —— 一次只取一个维度的一版）。
- **题库按组织（租户）单份**（PRD §4「ERL 配置层级按照租户层级」），本表直接带 `organization_id`（`erl_question_config.version_no` 与 `erl_question_config_version.version_no` 不是同一个数，无法经版本号间接归属）。**发布批次在组织内单份**（Publish 是组织内的全局动作，§7.9），但**各维度的题目集版本线相互独立**。

> **题库版本是「每维一条版本线」**：`version_no` 按 `dimension_code` 自增，一份维度题目由 `(dimension_code, version_no)` 定位。**组织级的「第 n 次发布」在 `erl_question_config_version`**（§5.1.1），它与各维度当时 `version_no` 的对应关系逐行落在 `erl_question_config_dimension_version`（§5.1.5）—— 即「本次发布 = FRL 的 v7 + PRL 的 v2 + …」。只改了某一个维度的题目时，**只有那个维度的 `version_no` 前进**，其余维度在新发布批次里仍指向各自的旧版本号，不整库克隆。
>
> **草稿态的题目集怎么定位**：已发布版本经 §5.1.5 快照拿到各维 `question_version_no`；**草稿没有快照行**，故草稿态取该维的 `max(version_no)`。为让这条规则安全，配套两条约束：
> - **新版本号只在写时复制时分配**：某维度本轮首次被编辑时，在**草稿版本行的悲观锁内**算 `version_no = max(version_no) + 1 WHERE organization_id = ? AND dimension_code = ?` 并克隆该维题目；未被编辑的维度**不产生新号**，其 `max` 恰等于已发布号，读侧行为自洽。§7.9-②’’ 的 `max(version_no)` 与写时复制的取号**一律带 `organization_id` 作用域**。
> - **丢弃草稿必须同事务清理高版本号题目行**（删除该组织所有 `version_no` 大于“当前已发布版本快照里该维的 `question_version_no`”的行）—— 否则那批行会被 `max` 永久命中，成为**幽灵草稿**。⚠️ 本仓当前**没有丢弃题库草稿的接口**（§7.10 边界 5：“不做丢弃草稿”），故该风险当前不可达；**日后若补丢弃接口，这条清理是必选项**。
>
> 题目行按 `(organization_id, dimension_code, version_no)` 定位，各组织互不相干；脚本不插任何种子题目，题目行一律由业务侧写入。

> **本表不含的字段**：
> - 发布状态在**版本级**（§5.1.1），题目行无 `publish_status` / `published_at`。
> - 无软删列 —— 删除题目 = **在草稿版本内物理删行**。已发布版本的行不受影响，历史评估按 `erl_assessment.erl_question_config_version_id` 读旧版本，题干天然可还原。
> - 全部题恒 Yes/No，无 `answer_type`。
> - **判定标准（`criteria`）不进需求设计**：配置页不采集、题目行不展示、不作为 Goldie 输入。题库字段清单**与 PRD §3.8 逐项对齐**（题干 / Era Band / Source）。

### 5.1.1 `erl_question_config_version` —— 题库版本

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`organization_id`** | **varchar(36)** | **not null** | 所属组织（租户）。PRD §4「ERL 配置层级按照租户层级」；取值缺省来自 `SecurityUtils.getOrganizationId()`（§2.1）；管理端可用可选入参 `organizationId` 指定**自身组织树内**的组织（§4.3） |
| `version_no` | int | not null | **组织内**递增的**发布批次号**，从 1 起；配置页显示 `Published v3` / `Draft v4`。⚠️ 与 `erl_question_config.version_no` 不是同一个东西 —— 后者按 `dimension_code` 自增、是各维度题目集各自的版本号（§5.1），两者的对应关系落在 §5.1.5 |
| `status` | varchar(16) | not null | `DRAFT`（在改，未生效）/ `PUBLISHED`（已生效）。**在用版本 = 本组织 `status = 'PUBLISHED'` 中 `version_no` 最大的那一条**（新发起的评估绑定它，§7.9-①）；`version_no` 组织内唯一且草稿号恒为 `max + 1`，故结果天然唯一、不需要次级排序键。**不用 `published_at` 作判据**（只是时间戳、无唯一约束，草稿行为 `null`）。⚠️ 草稿行的 `version_no` 恒为最大，取在用版本**必须带 `status = 'PUBLISHED'`**，漏了就会把未发布的草稿当成在用版本发到问卷上。Publish 只翻本版的状态，**一行都不碰上一版** |
| `published_at` | timestamp | | `PUBLISHED` 才有值 |
| `published_by` | varchar(128) | | 发布人姓名快照 |
| `version` | bigint | not null, default 0 | JPA `@Version` 乐观锁版本号。草稿版本行是**同组织多管理员共编**的对象：A 的加题事务持有草稿行时、B 把同一行发布成 PUBLISHED，A 随后把新题写进那个版本号（`erl_question_config.version_no`）—— 一道从未发布过的题瞬间进入线上问卷。题目的增删改排写的是 `erl_question_config`、**不碰本表**，故防线是 `ensureDraftVersion` 对草稿行发的那条带版本谓词的 UPDATE |

约束（全部带 `organization_id` 前缀）：
- **部分唯一索引** `uk_erl_question_config_version_draft ON erl_question_config_version (organization_id) WHERE status = 'DRAFT'` —— **同一组织内同时最多一份草稿版本**。题库按组织单份，草稿也就按组织单份（同组织的多个管理员共享同一份草稿，后果见 §7.9-④）。
- `uk_erl_question_config_version_no (organization_id, version_no)` —— 同时是「至多一个在用版本」的兜底：在用版本 = `PUBLISHED` 里 `version_no` 最大的那条，组织内号唯一 ⇒ 结果必然唯一。
- 索引 `idx_erl_question_config_version_status (organization_id, status, version_no DESC)` —— 版本历史列表、建草稿时算 `version_no = max + 1`、取本组织最新已发布版本的主路径。

> **本表不存克隆来源与变更摘要**：版本序列由 `version_no` 表达；变更摘要不落库，接口 9 只返回根节点 `hasDraft` 一个布尔值、接口 25 不返回 `changeSummary`（§6.4）。发布当时的维度集合由 §5.1.5 逐维快照（`dimension_code` / `dimension_name` / `dimension_abbr` / `sort_order`），不依赖维度配置留存历史。

> **为什么不用「双表（草稿表 + 正式表）」**：双表本质就是只能存两代的版本化，却要把 `erl_question_config` 的全部列复制一份 DDL 并长期同步维护；版本表方案用版本号表达同样的语义，还顺带给了历史评估一个天然的题干快照来源（省掉软删）。

### 5.1.3 `erl_dimension_config` —— 维度集合与权重（PRD §3.8 / D1）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`organization_id`** | **varchar(36)** | **not null** | 所属组织（租户）。维度配置**每组织一份当前值**，不版本化；取值缺省来自 `SecurityUtils.getOrganizationId()`（§2.1），可由可选入参 `organizationId` 指定组织树内的组织（§4.3） |
| **`dimension_code`** | **varchar(8)** | **not null** | **系统生成的不透明标识**。**组织内稳定** —— `erl_question_config.dimension_code`、`erl_assessment.dimension_code`、`erl_reference_score_item.dimension_code`、`erl_question_config_dimension_version.dimension_code`、`erl_gap_analysis_dimension_task.dimension_code` 五处历史数据全靠它关联，故**一经创建即永不改变**。<br>**生成规则**：新增维度时由**服务端生成** `{abbr 前 3 位}{4 位随机}`（规则同 §5.1），此后新增 / 修改都**不跟随 `dimension_abbr` 变动**。不用 UUID：本列为 `varchar(8)` 且被上述五处引用，改 UUID 要把五处列宽拉到 36。<br>**生成时碰撞**则**重新生成并重试**（上限 5 次，超限报 500）。<br>配置页**不显示本列**（§8.4-C6），行内编辑能改的只有名称 / 缩写 / 权重 |
| **`dimension_name`** | **varchar(64)** | **not null** | 全称，如 `Financial Readiness` |
| **`dimension_abbr`** | **varchar(8)** | **not null，1–8 字符** | 显示缩写。与 `dimension_code` 解耦：code 仅在**创建时**取它前 3 位做前缀，此后本列**可随时改名、code 一律不跟随**。雷达图顶点、A3 维度 chip、F2 列头、A4 卡头徽章用它。<br>**唯一性：无** —— 新增维度不做任何重名 / 重缩写校验，**同组织内本列可以任意重复**（两个 `Active` 维度同缩写、甚至同名都合法），它们靠 `dimension_code` 区分；重名的代价（F2 两列同名、雷达图两个同名顶点、送给 LLM 的维度列表歧义）需求方已接受。⚠️ **`1–8` 字符的长度约束保留**（列宽就是 `varchar(8)`，接口 24 校验，§6.4-2-③） |
| `sort_order` | int | not null | 展示顺序：维度卡列表、雷达图顶点、题库 Tab、F2 列序、Gap 状态点一律按它排（PRD §3.8 拖拽排序即改此列） |
| `weight` | numeric(5,2) | not null, 0–100 | **百分比数值**（如 `20.00` 表示 20%）。**同一组织内 `status = 'Active'` 的行合计必须 = 100.00**，由服务端在保存时校验（§6.4 接口 24）。`Inactive` 行的 `weight` **原样保留不清零**，供历史回看 |
| **`status`** | **varchar(16)** | **not null，默认 `Active`** | 维度启用状态，取值 **`Active`（启用）/ `Inactive`（停用）**。**停用 = 置 `Inactive`**（入口为行尾**电源按钮** `PoweroffOutlined`，**不物理删行**）：停用后该维度不再出现在填报 / 计分 / 雷达图的当前口径里，但行仍在，历史数据（`erl_assessment.dimension_code`、`erl_reference_score_item`、Gap items 与 §5.1.5 的发布快照）仍能反查到它的名称与缩写。`Inactive` 的维度可在面板底部常显的 `Deactivated Dimensions` 区块置回 `Active` 恢复（§8.4-C6） |
| **`deleted`** | **boolean** | **not null，默认 `false`** | 配置页的「**删除**」= 置 `deleted = true`。**行与 `weight`、`dimension_name` / `dimension_abbr` 全部原样保留**（历史数据仍按 `dimension_code` 反查得到），但**所有读侧一律排除**，页面上**没有恢复入口**（既不在主列表、也不在 `Deactivated Dimensions` 区块）。**只有 `deletable = true`（该 code 从未进入任何已发布题库版本的维度快照）的维度才允许删**，否则服务端拒绝并要求改用停用（§6.4 接口 24）。<br>⚠️ **与 `status` 正交，不是它的第三个取值**：`Active + false` = 主列表 / `Inactive + false` = `Deactivated Dimensions` 区块 / `deleted = true` = 完全不显示。合并成三值枚举后，「删掉一个当前**已停用**的维度」（可达：从未发布过的维度可以先停用再删除）就只能靠丢掉原状态来表达。<br>⚠️ **删除不改 `status`** —— 一个被删掉的行 `status` 仍是它被删那一刻的值。所以**每一处按 `status` 过滤的读都必须同时过滤 `deleted = false`**，漏一处就会漏出一个用户已经删掉、且再也管理不到的维度。 |

> **`status` 取值**：库值 = 接口 23 / 24 与卡片、评分详情里的 `status` 出参 = `Active` / `Inactive`（前端不消费该字段）。`ErlDimensionConfigStatusEnum.fromDbValue` 读侧兼容旧字面值 `Activate` / `Deactivate`（映射到同一枚举、不抛异常），**写侧永远只写新值**；⚠️ 这条兼容保不住按 `status` 过滤的 SQL 查询（转换器绑定的字面值是 `'Active'`，库里若还是旧值一行都命不中、且不报错）。入参字段名接口 23 的 `includeDeactivated` 与接口 24 的 `deactivatedCodes` 保持原名（它们表达的是「动作 / 要停用哪些」，不是状态值本身）。

> **`savedAt` / `savedBy` 取自审计列**（本表无独立的保存时间列）：**接口 23 / 24 出参是 `savedAt` / `savedBy`，入参收 `savedAt` 乐观锁令牌**；`savedAt` = 该组织**全部行**（含 `Inactive`，**也含 `deleted = true` 的行**）的 `max(updated_at)`，`savedBy` 取其中 `updated_at` 最大那一行的 `updated_by`。保存为单阶段直接写终态，`max(updated_at)` 只被真正发生变更的行 bump —— 有变更就抬高令牌、无变更则令牌不变。
> - ⚠️ **为什么 `savedAt` 必须算上已删行**：删除也是一次写入，**必须 bump 乐观锁令牌**。反例：A 删掉维度 X，B 的页面是删除**之前**打开的、本地数组里**还有 X**。若 `max()` 把已删行排除在外，A 那次删除就没抬高令牌 ⇒ B 的 `savedAt` 仍然匹配、**被判为无冲突**，B 那份含 X 的数组照常提交 —— X 被当成「已有维度」upsert 回 `Active`，**A 的删除被静默撤销**，而两次请求都返回成功、日志一行不报。算上已删行，B 会正常拿到「配置已被他人修改，请重新加载」，重载后 X 不再出现。
> - ⚠️ **实现硬约束：`savedAt` 必须从库里读回**（`select max(d.updatedAt) …`），**不得**取一级缓存里实体的字段值 —— `updated_at` 落库是 `timestamp(6)`（微秒），而审计基类写入的 `Instant.now()` 带纳秒；回显未截断的纳秒值，同一个管理员**连续保存第二次必被乐观锁判成「已被他人修改」**，而根本没有第二个人。也**不能靠客户端侧 `truncatedTo(MICROS)` 规避** —— pgjdbc 文本模式下 PG 是**四舍五入**到微秒，截断与舍入会差 1 微秒。
> - **`savedBy` 的一处边界**（已接受）：接口 23 默认不带停用行，若全局 `updated_at` 最大的那行恰是 `Inactive` 行，`savedBy` 会取到这批行里较早的那个保存人 —— `savedAt` 不受影响（它查的是全部行），而 `savedBy` 当前**无任何展示方**（前端只存进 state 不渲染），故不为它多查一次库。

约束与索引：
- `uk_erl_dimension_config (organization_id, dimension_code)` —— 同一组织内一个 code 只有一行。**本表唯一的唯一约束**；缩写不唯一（见上表）。ERL 的部分唯一索引共四条：`uk_erl_question_config_version_draft`（§5.1.1）、`uk_erl_assessment_draft`（§5.2）、`uk_erl_gap_analysis_report_unshared` 与 `uk_erl_gap_analysis_dimension_task`（§5.8）。
- 索引 `idx_erl_dimension_config_org (organization_id, sort_order)` —— 按组织取有序维度列表的主查询路径。
- **乐观锁**：本表是「同组织多管理员整组替换」的写入对象，而整组替换 + 缺席即停用 = 典型的 lost update（A 加维度 X 保存，B 随后保存自己那份不含 X 的数组 ⇒ X 静默被置 `Inactive`，A 完全无感）。因此：**接口 24 入参必须带上接口 23 返回的 `savedAt` 作为前置条件**，不匹配即返回「配置已被他人修改，请重新加载」。该令牌取自审计列 —— 该组织**全部行**的 `max(updated_at)`（见上）。
- 保存是**整组替换**（一次提交整份启用维度集合），不支持单维更新 —— 否则中间态必然破坏「合计 100%」。⚠️ 「整组替换」写的是本组织的这批行本身（就地覆盖 `dimension_name` / `dimension_abbr` / `sort_order` / `weight` / `status`），**改动前的旧值不留存**；提交里缺席的维度不删行，改为置 `status = 'Inactive'`（「缺席」**只表示停用**）。删除同样不删行，改为置 `deleted = true`，必须由 `deletedCodes[]` 显式点名（§6.4 接口 24）。
- ⚠️ **两处读侧刻意不过滤 `deleted`** —— 其余每一处读都必须过滤：
  - **全局 code 占用探针 `existsByDimensionCode`**：已删维度的 `dimension_code` **永久保留占用**，生成新 code 时照旧要避开它。理由是那个 code 仍被**五张表**当历史数据引用（`erl_question_config` / `erl_assessment` / `erl_reference_score_item` / `erl_question_config_dimension_version` / `erl_gap_analysis_dimension_task.dimension_code`）—— 若把它重新分配给一个新维度，**旧历史会静默地挂到新维度身上**：库里每一行都长得完全正常，只有对着历史列表看名字才发现串了，而那时已无从判断哪些行属于哪一个维度。这些引用全部没有外键、没有级联（§5.8），探针是唯一的防线。
  - **`savedAt` 的 `max(updated_at)`**：见上方乐观锁反例。

> **`dimension_code` 与 `dimension_abbr` 的关系**：
> - **新增**：用户只填 `Dimension name` 与 `Abbreviation`；`dimension_code` 由**服务端生成**为 `{abbr 前 3 位}{4 位随机}`（如 `OPS4K7M`），前端不传、不可指定。
> - **修改**：改 `Abbreviation` **不会**带动 `dimension_code`，两者此后永不同步。前缀只是**创建时的历史提示**，不是对当前 `abbr` 的断言 —— `OPS4K7M` 的维度今天可能叫 `Finance (FIN)`，**排查时以 `dimension_abbr` 为准**。
> - **为什么不用纯随机码**：纯随机码让 code 全站不可读，代价集中在四处 —— ① **LLM 需逐字回传 code**，抄错一位就被 §9 当成「该维无 gap」静默丢弃；② 日志 / URL / 手工改数全靠回表 join；③ 客服无处可查；④ 实现极易写成 `UUID.substring(0,8)`（那是 16⁸ 的纯十六进制，与本规则不符）。加一个前缀就能把这四样一起拿回来，**而不损失任何不可预测性与不可变性**。
> - **新库不插任何种子维度**，全部 code 走生成路径。`FRL / PRL / BERL / RRL / TRL` 在全文与 PRD 里只作**叙述举例**；**存量库**里它们仍可能是真实数据行，故下面那条「格式无约束」的结论成立。
>
> ⚠️ **`dimension_code` 无任何格式约束**：同一列里既有存量库遗留的 `FRL`（3 位）又有 `OPS4K7M`（7 位），**任何正则 / 长度 / 前缀 / 大写断言都会误杀一方**。合法性的**唯一判据是「命中 `erl_dimension_config` 中该组织的行」**；大小写不敏感比较仅作输入容错，**不得用于生成或存储归一**。

> **维度数量不固定**：`FRL / PRL / BERL / RRL / TRL` 只是**叙述用的举例**，不是模型约束（PRD §3.8 的维度列表本身就写作 `FRL / PRL / BERL / RRL / TRL...`，省略号即「不固定五个」）。一律「按维度配置中的维度集合，按 `sort_order` 排序」。无 `ErlDimensionEnum` 枚举与前端 `constants.ts` 的静态 `DIMENSIONS` 映射，改**接口驱动**（接口 23）。
>
> **脚本不插任何维度行**：新库与新建组织在管理员于配置页保存第一组维度之前，`erl_dimension_config` 是**零行** ⇒ 维度列表为空、综合分按 §9 的**等权降级**路径算并打 WARN。这是既定行为、不是 bug，但产品上**没有任何引导**（已记入 `CIOaas-api/docs/待优化项.md`）。
>
> **按期次的取数口径**：按期次渲染维度、算综合分与 Stage、画雷达图、Gap 状态点计数、Share 门槛 —— 一律读 `erl_dimension_config` 中该组织 **`status = 'Active'`** 的当前维度集合，按 `sort_order` 排序。历史期次上出现过、如今已 `Inactive` 的维度，其名称 / 缩写由 `erl_assessment` 行上的 `dimension_name` / `dimension_abbr` 快照还原（§5.2）。
>
> ⚠️ **历史期次会漂移（已接受，§13-Q21）**：① 改权重会**回溯改变**已提交历史期次的综合分与 Stage —— `erl_assessment` 上有每维的 `level_score` 快照，但**权重不在快照里**，综合分是实时加权算出来的（§7.1）；② 新增维度会让历史期次凭空多出一个「未填」的维度，`Inactive` 维度会从历史雷达图上消失。
>
> **删除维度 —— 两个动作，按「是否进入过已发布题库版本」二选一**：
> - **`deletable = true`（该 code 从未进入任何已发布题库版本的维度快照）** ⇒ 行尾是**垃圾桶 = 删除**，落库 `deleted = true`（行留、页面两处都不显示、**无恢复入口**）；
> - **`deletable = false`** ⇒ **删除被禁止**，行尾是**电源按钮**（`PoweroffOutlined`）= 停用，落库 `status = 'Inactive'`，可从 `Deactivated Dimensions` 区块 `Activate`。
> - **只有垃圾桶（删除）要二次确认，电源按钮（停用）点了直接生效**；`status` 只有两个取值，`deleted` 与它**正交**。
>
> 停用（或删除）后剩余维度的权重合计会不足 100%，**需在同一次 Save 里补齐**。已 `Inactive` 的维度：① 不进填报页、不进当前的综合分与雷达图；② **已提交的历史记录照常显示**（B3 历史列表 / A4 详情 / C7 版本快照）—— 名称 / 缩写取 `erl_assessment.dimension_name` / `dimension_abbr` 行上快照或 §5.1.5 的发布快照，`Retired` 灰样式由 `status = 'Inactive'` **直接判定**；③ ⚠️ **但「按当前口径重算」的东西会变** —— 综合分、Stage、雷达图顶点集合一律只取 `Active` 维度，故历史期次的这三项**会因停用而漂移**（已接受，§13-Q21）。**两者不矛盾：存下来的提交行还在、能看；实时算出来的聚合值会变。**
>
> **C7 与 `erl_dimension_config` 的当前值无任何耦合** —— 该页既不按当前配置过滤维度，也不打 `Retired` 灰标（不调接口 23），只读接口 25 / 26 的历史快照 ⇒ **停用 / 删除一个维度对 C7 的展示零影响**，上面 ② 里「C7 版本快照」那一项只依赖 §5.1.5 的发布快照。`Retired` 灰标在**历史期次**（B3 / A4 / A1 / A2 雷达图）上照常按 `status = 'Inactive'` 显示。

### 5.1.5 `erl_question_config_dimension_version` —— 题库版本 ↔ 维度快照

> ⚠️ **本表也在草稿阶段写入**。某维本轮首次被编辑、触发克隆时就写一行
> （挂在**草稿版本行**上）—— 它是「本轮克隆过哪些维度」的**唯一记录**（§7.9-②’’）。
> Publish 只是把同一条版本行翻成 `PUBLISHED`，这批行随之成为该发布版本的快照。
>
> ⚠️ **这条特性直接决定接口 23 的 `deletable` 怎么算**（§6.4）。「该维度是否进入过
> 已发布题库版本」**不能**只查本表有没有行 —— 草稿版本上也有行。判据必须 **join 到 `erl_question_config_version`
> 并过滤 `status = 'PUBLISHED'`**；只查本表会把「只在未发布草稿里改过题」的维度误判成不可删，
> 用户看到一个电源按钮却找不出任何理由（那一版从未发布，删掉它不会让任何已发布版本失去指向）。

**题库版本发布当时的维度集合，逐维冻结一行。** 本表把名称与顺序直接抄进来，不依赖维度配置留存历史。C7 版本历史页据此还原「那一版有哪些维度、叫什么、什么顺序」，后续维度改名 / 停用 / 调序**一律不影响**已发布版本的历史展示。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `erl_question_config_version_id` | varchar(36) | not null | → `erl_question_config_version.id`（§5.1.1）：本行快照所属的题库版本 |
| `dimension_code` | varchar(8) | not null | 快照自 `erl_dimension_config.dimension_code`（§5.1.3） |
| `dimension_name` | varchar(64) | not null | 快照自 `erl_dimension_config.dimension_name` —— **发布当时**的全称，此后不随配置改名 |
| `dimension_abbr` | varchar(8) | not null | 快照自 `erl_dimension_config.dimension_abbr` —— **发布当时**的缩写，此后不随配置改名 |
| `question_version_no` | int | not null | 快照自 `erl_question_config.version_no`（§5.1）：**该维度在本次发布时所用的题目集版本号**（按 `dimension_code` 自增的那条版本线）。本次没改动的维度，此列仍指向它上一版的号 |
| `sort_order` | int | not null | 排序：C7 版本快照页的维度卡顺序按它排（= 发布当时 `erl_dimension_config.sort_order` 的快照） |
| `bound_at` | timestamp | not null | 绑定时间（= 该题库版本的发布时刻） |

> ⚠️ **本表的行会被评估行直接指向**：`erl_assessment.erl_question_config_dimension_version_id` 存的就是本表某一行的 id（§5.2）。因此「**已发布版本的快照行此后永不改写、永不删除**」是**评估取题的前提** —— 行被删掉，那条评估就退回复合键路径（仍能取到题，但「作答依据」的直连断了）。Publish 时删行的那一支（§7.9-②'''' 边界 ①：草稿期克隆过、发布前又被置 `Inactive`）删的是**草稿版本**的行，评估只会绑到**已发布版本**的行上，两者不重叠。

约束与索引：
- `uk_erl_question_config_dimension_version (erl_question_config_version_id, dimension_code)` —— 同一题库版本内一个维度只有一行。
- 索引 `idx_erl_question_config_dimension_version (erl_question_config_version_id, sort_order)` —— 按版本取有序维度列表的主查询路径（接口 26 出参 `dimensions[]`）。

**写入时机**：**草稿版本行上就有快照行** —— 某维本轮首次被编辑、触发克隆时就写一行挂在草稿版本行上（`ErlQuestionConfigVersionServiceImpl.ensureDimensionCloned`），它是「本轮克隆过哪些维度」的**唯一记录**（§7.9-②''）。**接口 21 Publish 在同一事务内**只把同一条版本行翻成 `PUBLISHED`，这批行随之成为该发布版本的快照，**无需重写**；Publish 当时只补写「本轮未克隆过的 `Active` 维度」那几行（取该组织当时 `erl_dimension_config` 中 `status = 'Active'` 的行，带上该维度当时的 `question_version_no`），`bound_at` = 发布时刻；**此后永不改写**。⚠️ 若实现成「草稿不写本表」，§7.9-②'' 的判据就没有落点，写时复制会退回用两个 `max` 比大小反推 —— 那有两个可达的静默错误分支（§7.9-②'' 已列）。

> **`question_version_no` 与 `erl_question_config_version_id` 不冗余**：前者是**该维度题目集自己的版本号**（`erl_question_config.version_no`，按 `dimension_code` 自增，§5.1），后者是**组织级的发布批次**（§5.1.1）。本表正是两者的对应关系表 —— 一行 = 「第 n 次发布时，维度 X 用的是它自己的第 m 版题目」。取某个发布版本下某维度的题目：先按 `erl_question_config_version_id` 查出本行，再用 `(dimension_code, question_version_no)` 回 `erl_question_config` 取题。
>
> **本表不含 `weight`**（权重不做任何快照）：接口 26 出参 `dimensions[]` 为 **`{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }`**（§6.4 接口 26），由单独的窄 Response `ErlQuestionConfigDimensionVersionResponse` / `ErlQuestionConfigDimensionVersionDTO` 承载，**不复用** `ErlQuestionConfigListResponse`。C7 页面本身**不显示权重**（卡头只有 `{全称} ({缩写})` + `{n} questions`，§8.4-C7）。

### 5.2 `erl_assessment` — 一次提交（粒度为「一次维度级提交」，PRD §3.3 / §3.9）

> 一次提交的单元是「某公司某期次某端的**单个维度**」：① 维度列 `dimension_code` 进入**每一条**唯一约束 / 索引；② 每维的 `level_score` / `terminated_level` / `unlocked_level` 直接在本表；③ 题库版本 `erl_question_config_version_id` 的绑定粒度为**每维一份**。提交前置校验为「**本维度到达终止态**」（§7.2 / §6.3）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | 形如 `2026Q3` |
| `portal` | varchar(8) | not null | `FOUNDER` / `GSV` |
| **`dimension_code`** | **varchar(8)** | **not null** | 本次提交所属维度的 code（对应 `erl_dimension_config.dimension_code`，§5.1.3）。取值域 = 该组织当前 `status = 'Active'` 的维度集合，**不是固定五值枚举**（D1） |
| **`dimension_name`** | **varchar(64)** | **not null** | 提交时该维度全称的**快照**。维度日后改名或 `Inactive` 后，历史详情、雷达图图例、Gap 报告仍显示当时的名字 |
| **`dimension_abbr`** | **varchar(8)** | **not null** | 提交时该维度缩写的**快照**，同上 |
| `status` | varchar(16) | not null | `DRAFT` / `SUBMITTED`。SUBMITTED 行只有一种形态：未答完的提交会**自动补一道 No 先终止**，漏答数恒为 0 |
| **`erl_question_config_version_id`** | **varchar(36)** | **not null** | → `erl_question_config_version.id`（§5.1.1）：本次作答所依据的**题库版本快照**。**创建评估时写入当时最新的已发布版本，此后永不改写**（含 `DRAFT` 期间 —— 不做重基，见 §7.9-⑤）。填报、计分、历史详情、Goldie 输入**全部按此版本**渲染与计算。绑定粒度为**每维一份** —— 见下方说明 |
| **`erl_question_config_dimension_version_id`** | **varchar(36)** | **可空** | → `erl_question_config_dimension_version.id`（§5.1.5）：本次作答所依据的**那一维的题目集快照行**。上一列绑的是**组织级发布批次**，要取「这一维当时用的是第几版题目」还得拿 `(erl_question_config_version_id, dimension_code)` 去 §5.1.5 按复合键反查；本列把**那一行的 id 直接记在评估上**，一跳 `findById` 即得 `question_version_no`（连同发布当时的维度名 / 缩写 / 排序）。**创建草稿时写入，此后永不改写**（与上一列同口径）。<br>**为什么可空**：① 本仓库 `ddl-auto: update` **加不上 NOT NULL 列**；② 该维度在所绑那一版下**可能本来就没有快照行**（例如它在那次 Publish 之后才启用），此时 `null` 是**正确状态、不是异常**。<br>**读侧优先级**：非空 ⇒ 一跳直达，但要过三道校验 —— 行还在、行的 `dimension_code` 与评估行一致、行的 `erl_question_config_version_id` 等于评估绑定的批次；任一不成立即按**脏数据**处理（打 WARN 后回退，**不抛异常**）。正常路径下两列是同一时刻由同一个版本行写入的，永远相等；不相等只能是手工改数或迁移写歪，此时宁可回退也不能拿别的维度 / 别的一版的号去取题。为空 ⇒ **回退复合键查询**。两条路径结果必须一致。<br>**不取代 `erl_question_config_version_id`**：`organization_id`（评估表上没有）与版本号徽章（`questionVersionNo` / `hasNewerQuestionSet`）仍从批次列解，本列只是取题的捷径 |
| **`level_score`** | **smallint** | **提交时非空，0–9** | 本维度得分 = 最后一个全 Yes 的 level。`0` = 一级都没通关（该维第一个有题 level 内就有 No）；全通关 = 该维最大有题 level（配满九级时为 `9`）。`DRAFT` 期间为 `null`（尚未终止），提交时由服务端算出并落库。⚠️ 取值虽在 0–9 内，但**只可能是该维配置过的 level 或 `0`**（只配 level 1/2/7/9 ⇒ 该列只会出现 0 / 1 / 2 / 7 / 9）；⚠️ 该列是**提交时冻结的快照**，计分口径变化**不追溯存量行** |
| **`terminated_level`** | **smallint** | 0–9 | **首次出现 No 的 level**。稀疏题库下与 `level_score` 不一定相差 1 —— `level_score` 取的是**上一个有题且整级通关的 level**，两列之间可能隔着若干个该维没配题的 level，如 levels `[1, 2, 7, 9]` 在 L7 踩 No ⇒ `terminated_level = 7`、`level_score = 2`；全通关时为 `null`。冗余存一列是为了历史详情页能直接标出「止于 Level n」而不必重扫答案 |
| **`unlocked_level`** | **smallint** | not null, 1–9 | **草稿期的解锁进度**，当前已解锁到第几 level。创建草稿时写 `1`，填报页据此渲染（§7.2）；提交后即等于 `terminated_level ?? 9` |
| `submitted_at` | timestamp | | `SUBMITTED` 才有值 |
| `submitter_name` | varchar(128) | | 提交人姓名快照 |
| `submitter_role` | varchar(128) | | 提交人角色快照，如 `Founder & CEO` |
| `version` | bigint | not null, default 0 | JPA `@Version` 乐观锁版本号。草稿行是**公司共享**的多人写入对象，存草稿事务读到 DRAFT 行后、若另一事务已把同一行提交成 SUBMITTED，落盘时会把 `status` / `submitted_at` / `submitter_*` 整行写回旧值 —— 一次已完成的提交被静默抹掉 |

> **为什么 `level_score` 落库而不是全靠实时算**：它由答案唯一决定、实时可算（§3.2 的「计分不落库」指的是**综合分 / Stage / Era**）；但 `unlocked_level` 是**草稿期的交互状态**，必须持久化（否则刷新页面后解锁进度丢失、PRD §3.3「支持保存进度、稍后继续，无数据丢失」不成立）。既然这行本就要存，`level_score` 与 `terminated_level` 一并落库，省掉展示与组合层的重复扫表 —— 且**提交后答案冻结，二者不会与答案不一致**。评估行本身就是「这一维」的那一行：它不存在就是「这一维还没开始」。

约束与索引：
- **不设** `(company_id, period, portal)` 唯一约束 —— PRD「同一季度允许多次提交」。
- **部分唯一索引** `uk_erl_assessment_draft ON erl_assessment (company_id, period, portal, dimension_code) WHERE status = 'DRAFT'` —— **每维**同时只允许一份在填草稿（草稿仍是公司共享、不含用户维度，D9）。**本表唯一的部分唯一索引。**
- 索引 `idx_erl_assessment_company_period (company_id, period, portal, dimension_code, submitted_at DESC, id DESC)` —— 「取最新提交」的主路径。

> ⚠️ **「最新一次提交」（SOT）的取法**：本表没有提交序号与 SOT 标记列。① 「最新一次提交」= 同 `(company_id, period, portal, dimension_code)` 内 `status = 'SUBMITTED'` 且 `submitted_at DESC, id DESC` 的第一条，读侧每一处 SOT 取数（A1 卡片、A2 雷达图、A4、F2、Gap 输入、Share 门槛）都按此取，**并发下没有索引兜底「至多一条 SOT」**；② `submitted_at` 相同（同秒两次提交）时靠 `id` 作次级排序键兜底，**读侧必须全部走同一个 Repository 方法**，否则不同页面会选出不同的一条；③ **提交序号 `Submission #n` 不落库** —— A2 / A4 历史列表的序号按 `submitted_at` 倒排后的行号实时计算（翻页时会漂移）。

提交人姓名 / 角色 **存快照**：人员离职或改名后历史记录仍显示当时信息。即使草稿由他人保存，`submitter_name` / `submitter_role` 只记录**点提交的那个人**（D9）。

> **`erl_question_config_version_id` 每维一份的后果**：维度 A 在 3 月创建草稿（绑 v5），维度 B 在 5 月才创建（此时最新已发布是 v7，绑 v7）—— **同一公司同一期次的各维度可能绑不同的题库版本**。**系统不阻止、不告警**，各维度按各自绑定的版本渲染题目、判定解锁与计分；历史详情同理按行上的版本还原。理由：题库版本本就是「按维度独立的作答依据」，强行对齐要么阻塞后开的维度（不能用新题）、要么重基已开的维度（不做重基，§7.9-⑤）。
>
> 维度的名称与缩写由本表的 `dimension_name` / `dimension_abbr` 逐行快照，**权重没有快照**（见 §5.1.3 ⚠️）。

### 5.4 `erl_assessment_answer` — 逐题作答（PRD §3.3 / §3.4）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`erl_assessment_id`** | **varchar(36)** | **not null** | → `erl_assessment.id`（§5.2） |
| **`erl_question_config_id`** | **varchar(36)** | **not null** | → `erl_question_config.id`（§5.1），**指向作答时所属维度版本的那一行**（历史详情据此还原当时的题干 / level / 来源标签） |
| **`yes_no`** | **boolean** | **not null** | **唯一的作答字段**。已解锁且已作答的题恒有值；**未解锁的题不落行**（不是落 `null` 行 —— 见下方说明） |
| **`note`** | **varchar(2048)** | **nullable** | **证据 / 备注（Evidence/Notes）**；Goldie 的主要输入源（PRD §3.6）。列宽与接口 4 的 `@Size(max = 2048)` 一致，**填报页的输入上限是 2000**（前端 `maxLength` + `n / 2000` 字数提示），那 48 是留白、**不是**第二个业务上限 |

唯一约束 `uk_erl_answer (erl_assessment_id, erl_question_config_id)`；索引 `idx_erl_answer_assessment (erl_assessment_id)`。

> 本表不带 `question_key`：`erl_question_config_id` 自始至终不改写，无需跨版本稳定键。`question_key` 只在 `erl_question_config` 表 —— 版本 diff 与 C 模块写接口定位需要它。
>
> **未解锁的题不落答案行**：逐级解锁下，用户根本看不到未解锁 level 的题，落 `null` 行会让「未解锁」与「看到了但没答」无法区分，而后者要拦住提交、前者不能拦。因此 `answeredCount` 就是本表行数，判定简单且无歧义（§6.3 / §7.2）。
>
> `note` 是**可选**字段（PRD §3.3「可选『证据/备注（Evidence/Notes）』文本」）。无备注时 Goldie 侧标注为「未提供备注」（PRD §3.6）。

### 5.5 `erl_answer_attachment` — 逐题附件（PRD §3.3 / §4）

**只有题级一种粒度**：Founder 与 GSV **一律把附件挂在具体某一道题的作答上**（PRD §3.3「每题…可上传附件（单个最大 10MB）」），没有维度级附件。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`erl_assessment_answer_id`** | **varchar(36)** | **not null** | → `erl_assessment_answer.id`（§5.4）。**附件恒挂在一条作答上**，双端同口径；所属评估、维度、期次、端一律经该作答带出（删附件鉴权，接口 19，经 `answer → assessment` 两跳） |
| `file_id` | varchar(36) | not null | 直传通道返回的 `files.id`。文件名与字节数不在本表快照，按 `file_id` 取 `files.original_name` / `files.length` |

> **本表只有七列**：`id` / `erl_assessment_answer_id` / `file_id` + 四个审计列（`created_at` / `created_by` / `updated_at` / `updated_by`）。它记录的**只是「哪条作答挂了哪个文件」**，**不承载任何处理状态**。
> - **为什么没有状态可记**：摘要在**差距分析 `refresh` 时现场生成、用完即弃**（下载 → 解析 → 摘要（覆盖全文，超过 6 万字符分段并发 + 合并），**不建 entry / space / 登记行**，§6.7），所以既没有「登记行 id」可回写，也没有「这次生成成没成」需要留存 —— 每轮重生成都重跑一次，**上一轮的成败对下一轮没有任何意义**。
> - ⚠️ **代价（需求方知情）**：① 每轮重生成都**重付一次**解析与摘要 LLM 成本（接口 18 以 `force=true` 重跑全部可分析维度时，会重算该期次**全部**附件；超长附件每份是「段数 + 合并次数」次调用，成本随全文长度增长）；② 「某份证据没被 Goldie 读进去」**全站无任何痕迹** —— 不落库、同一份附件这次失败下次可能成功，屏上与库里都不留痕。「要给用户提示」的产品诉求留在 `CIOaas-web/docs/待优化项.md`（三个候选落点待需求方定）。
> - ⚠️ **索引 `idx_erl_attachment_file` 刻意保留**：本索引当前无消费者。留着是因为 `docs/待优化项.md` 记着要给本表补 `(erl_assessment_answer_id, file_id)` 唯一索引，那条落地后它即为前缀冗余、届时一并处理；在那之前只有可忽略的写放大成本。

> **文件名与字节数一律按 `file_id` 去 `files` 取**（`original_name` / `length`）—— 那是这两个值的**真值来源**，附件行只是「这道题挂了哪个文件」的指针。
> - **入参**：接口 4 / 5 的 `answers[].attachments[]` **只收 `fileId`**。前端多发的 `fileName` / `fileSize` 服务端忽略（`fail-on-unknown-properties: false`）。
> - **10MB 上限按 `files.length` 复核**（§6.7 第 ③ 步）：`files.length` 在 `presign` 阶段落的**也是客户端自报的数**，只有 `verify` 才用 S3 `HeadObject` 的真实大小覆盖它并写上 `etag`。所以服务端**先断言 `files.etag` 非空**（= 已 verify）再看 `length`；少了这一条，「presign 声明 1MB → PUT 一个 100MB 对象 → 跳过 verify → 挂上来」就能绕过上限（`KNOWLEDGE_BASE` 的 presign 上限是 1024MB，绕过空间很大）。前端 `storageService.uploadFile` 走的是 `putAndVerify`，正常链路必然已 verify。<br>⚠️ **仍未校验的一项**：`fileId` 的**归属**（谁上传的、是不是 `KNOWLEDGE_BASE` 业务类型、属不属于本公司）—— 任意 `files.id` 都能挂到本公司作答上，属存量口径，已记入 `CIOaas-api/docs/待优化项.md`。两种取不到大小的情况**一律报业务错误**（§4.3）：① `file_id` 在 `files` 里查不到；② 查到了但 `length <= 0`（直传只 presign 占了行、还没 verify，或 legacy 行从未回填大小）—— **不得**把 `0` 当成「0 字节，肯定不超限」放过去，S3 上那个对象可以任意大。
> - **出参**：`fileName` / `fileSize` 照常下发（B2 / A3 / A4 的附件行要显示名字与大小），由 `files` **批量**回填（一次 `findAllById`，绝不逐个查 —— `coding.md §10`）。
> - ⚠️ **代价（已接受）**：历史附件的名字与大小**依赖 `files` 行仍在**。`files` 行若被清理，回显变 `null`（`file_id` 仍在、附件行本身不丢）；Python 侧的现场摘要**也取不到文件** ⇒ 该附件在差距分析里无摘要（无摘要的附件整条不送进 prompt）。当前没有任何清理 `files` 的定时任务，故这是理论风险而非现存缺陷。

索引 `idx_erl_attachment_answer (erl_assessment_answer_id)`、以及建库脚本里那条按 `file_id` 的索引 `idx_erl_attachment_file`（现无消费者、刻意保留，理由见上）。**按维度 / 按一次提交查附件 = 先取该评估的作答行，再按 `erl_assessment_answer_id` 批量取**（`findByAnswerIdIn`，即填报页、维度页、A4 的主路径）。

> 附件**只落本表**，保存 / 提交之后**没有任何后续异步动作** —— 既不入知识库、也不预生成摘要。文件的内容第一次被读取，是在**差距分析 `refresh` 那一刻**（§6.7）。附件不阻断评估提交（没有会失败的旁路）。
>
> **双端完全同口径**：同一个接口、同一张表、同一个 10MB 上限、同一套前端组件；**服务端不做端限制，前端两端都渲染逐题上传入口**。

### 5.6 `erl_reference_score` — 外部基准主表（PRD §4）

**同一 `(company, period)` 允许多条记录**（peer set 换了、口径改了要重新录一份，属正常路径）；分数落在 §5.6.1 的维度明细表 `erl_reference_score_item`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | 形如 `2026Q3`；D2 页输入 `Q3 2026`，前端归一后提交 |
| `note` | **varchar(2048)** | | 基准数据来源 / peer set 变化说明；空显示 `—`。D2 录入框限 **2000 字符**（前端 `maxLength` + `n / 2000` 字数提示），库留 48 余量，**那 48 不是第二个业务上限**；接口 16 的 `@Size(max = 2048)` 跟列宽走 |

索引 `idx_erl_reference_score_company_period (company_id, period)`（**普通索引，非唯一**）。⚠️ **没有数据库级「同期次至多一条」保证** —— 取「适用记录」必须用 **`period DESC, created_at DESC, id DESC`**；`Record History` 列表与 `LATEST` 徽章用 `created_at DESC NULLS LAST, id DESC`（`id` 是同一微秒的平局兜底；与 §5.2 评估 SOT 的 `submitted_at DESC, id DESC` 同源），且一律走 `ErlReferenceScoreRepository` 的那两个方法 —— 各处自己拼查询会在同期次多条时选出不同的一条（§7.8）。**`recordedAt` 直接下发审计列 `created_at`（真实录入时刻，`Instant` / ISO-8601）** —— 屏上列头写的是 `SUBMISSION TIME`，排序键本就在用这一列，展示位跟着它才不会与行序打架；不新增存储列。`Recorded by` 用 `created_by`（姓名 + 角色由用户表 join 得到，**不冗余存快照** —— 基准录入人不涉及 §5.2 那种历史留档要求）。

### 5.6.1 `erl_reference_score_item` —— 每维基准分（原型 D2「Scores by dimension」）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`erl_reference_score_id`** | **varchar(36)** | **not null** | → `erl_reference_score.id`（§5.6） |
| **`dimension_code`** | **varchar(8)** | **not null** | 维度 code，取值来自 `erl_dimension_config.dimension_code`（§5.1.3）（D1） |
| **`dimension_name`** | **varchar(64)** | **not null** | 录入时该维度全称的**快照**，同 `erl_assessment`（§5.2）—— 维度日后改名或 `Inactive` 后，历史基准记录仍显示当时的名字 |
| **`dimension_abbr`** | **varchar(8)** | **not null** | 录入时该维度缩写的**快照**，雷达图基准环的图例用它 |
| `benchmarkit_score` | numeric(3,1) | not null | 1–9 |
| `top_quartile_score` | numeric(3,1) | not null | 1–9 |

唯一约束 `uk_erl_reference_score_item (erl_reference_score_id, dimension_code)`；索引 `idx_erl_reference_score_item (erl_reference_score_id)`。**一条记录必须齐当前 `status = 'Active'` 的全部维度**，D2 页按该维度集合渲染「每维两个输入框」并**全部必填**（§8.4），否则提交被拒 —— 缺维会让雷达图与维度页的基准位置出现空轴。

> **为什么拆两张表而不是在单表加 `dimension_code` 列**：`note` 与录入人属于「一次录入」的属性，摊到每个维度一行会重复且可能不一致（改一次备注要改 N 行）。
>
> PRD §4：这两条序列是**外部静态数据输入，不由 Looking Glass 计算**。D 模块即该数据的接入口（管理端手工录入）；未来接自动同步时，只需替换写入方，读取口径不变。

### 5.8 差距分析的四张表（PRD §3.6）

> 详细列定义、类型、约束、不变量论证唯一权威见设计稿 [`2026-09-24-erl-gap-analysis-task-model-design.md`](../../superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md) §2 / §3；本节只记结论。

**归属**：Java 持有编排状态 —— `erl_gap_analysis_report`（报告分享记录）+ `erl_gap_analysis_dimension_task`（维度任务）；Python 持有 AI 内容 —— `ai_erl_gap_analysis_task`（生成日志 + 幂等标记）/ `ai_erl_gap_analysis_task_item`（NARRATIVE / GAP / ACTION 条目，一次写入永不改）。四张表全部无外键，按 id 列关联。建表脚本：Java `deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql`；Python `sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql`。

**`erl_gap_analysis_report`**：一个 `(company_id, period)` 下可有多条，"最新记录"统一 `ORDER BY created_at DESC, id DESC`；`shared / shared_at / shared_by` 只由接口 27 写、永不复位；`created_by` 由服务在异步线程内显式赋值为触发提交的用户。索引 `idx_erl_gap_analysis_report (company_id, period, created_at DESC)` + 部分唯一索引 `uk_erl_gap_analysis_report_unshared (company_id, period) WHERE shared = false`（不变量 I5）。

**`erl_gap_analysis_dimension_task`**：`status` 取 `PENDING / RUNNING / SUCCESS / FAILED`（不加 CHECK、不加 `@Version`，状态更新一律条件 UPDATE）；`has_gap`（SUCCESS 时必填）；`source_founder_assessment_id / source_gsv_assessment_id`（该任务依据的两端 SOT）；`result_task_id`（复制任务时指向真正持有 Python 内容的原任务）；`deleted`（仅在未分享记录内、旧任务被新任务取代时软删）。部分唯一索引 `uk_erl_gap_analysis_dimension_task (erl_gap_analysis_report_id, dimension_code) WHERE deleted = false` + `idx_erl_gap_analysis_dimension_task_report (erl_gap_analysis_report_id)`。

**Python 两表**：`ai_erl_gap_analysis_task_item` 的 GAP 条目只有 `content`（标题）与 `sort_order`（= 模型输出顺序，第一条固定为分歧题），不带 severity。`ai_erl_gap_analysis_task` 不记模型 —— 要查「用了哪个模型」看 `ai_llm_call_log.llm_model`，按 `caller_agent = 'erl'` / `caller_node = 'erl_gap_analysis'` 过滤（每次调用都带 `TraceContext(agent=ERL, node=ERL_GAP_ANALYSIS)`）。

**不变量**：

| # | 内容 |
|---|---|
| I1 | `shared = true` 的报告记录及其任务永不修改、永不软删 |
| I2 | Python 条目表一次写入永不 UPDATE / DELETE |
| I3 | 任务状态只能 `PENDING → RUNNING → SUCCESS \| FAILED`，所有状态更新都是条件 UPDATE（CAS） |
| I4 | 同一报告记录下同一维度至多一个未软删任务（部分唯一索引兜底） |
| I5 | 同一 `(company_id, period)` 至多一条未分享记录（部分唯一索引兜底） |

---

## 6. 接口契约

> 📌 **维度字段的命名规则（§6 全域适用）**：
>
> | 位置 | 写法 |
> |------|------|
> | **数据库列** | `dimension_code` / `dimension_name` / `dimension_abbr`（§5） |
> | **出参（所有接口）** | **`dimensionCode` / `dimensionName` / `dimensionAbbr`** —— 包括 `dimensions[]` 数组内的元素 |
> | **入参（query / path / body）** | **一律 `dimensionCode`**（接口 2 的 path 变量为 `{dimensionCode}`） |
> | **Python 内部接口** | 同出参规则（Python 内部契约按任务传参，见 §6.6） |
>
> 下文各接口表格中仍写作 `dimension` / `code` / `name` / `abbr` 的，**一律以本规则为准**，ERL 全域无例外。

> ⚠️ **破坏性变更**：`CIOaas-api/standards/coding.md` §9 要求「已发布接口禁止删除字段或改类型，破坏性变更须新路径 + `BREAKING CHANGE`」。ERL 域接口上线前的契约改动**不走「新路径 + BREAKING CHANGE」流程，直接改契约**；⚠️ **一旦 ERL 上线，本豁免即失效**，后续同类改动必须按 §9 走版本化。**前后端必须同一个发版周期上线**。


> 统一前缀：Java 侧 `@RequestMapping("/erl")`，前端经网关调 `/api/web/erl/**`。响应统一 `Result<T>`。入参走 `interfaces/vo/request`、出参走 `interfaces/vo/response`（`standards/coding.md` 三层传输实体强制），**禁止直接暴露 Entity**。
>
> **接口共 29 个**：1~20、#21 publish、#22 scoreDetails、#23 / #24 维度配置读写、#25 题库版本历史、#26 版本题面快照、#27 `POST /erl/gapAnalysis/share`（§6.6）、#28 `DELETE /erl/assessment/draft`（§6.3）、#29 `POST /erl/assessment/progress`（§6.3 —— 草稿期推进解锁进度，**只算不存、零写入**）。编号只增不改，删除的接口保留编号空位以免全文交叉引用失效。
>
> **三条全局规则，逐接口不再重复声明**：
> ① **维度级提交（R1）** —— 一次提交 = 某公司某期次某端的**单个维度**，填报域（接口 3 / 4 / 5 / 28）的请求体与响应体一律带 `dimension`，单维平铺。
> ② **动态维度（D1 / R2）** —— 没有「固定五项 / 五维固定顺序」；维度列表、顺序、权重一律**按当前 `status = 'Active'` 的维度集合**（`erl_dimension_config`，§5）返回，期次尚无任何评估时同样按当前 `status = 'Active'` 的维度集合返回。
> ③ **`period` 缺省口径（R3）** —— 所有 `period` 可选的读接口（1 / 17 / 20 / 22 等），缺省值为**该公司 closed month 所在季度**（复用 Financial Intelligence 域既有服务，读其每日 KPI 快照）；该季度无提交即**返回空态，不回退**到更早期次。

### 6.1 ERL Card（A1 / A2，PRD §3.1）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 1 | `GET /erl/card` | Company Overview 的 ERL 卡片一次取全 | `companyId`、`period`（可选，缺省为该公司 closed month 所在季度，R3） | `period`、`overallScore`、`stage`、`era`、`bpmmScore`、**`shared`**、**`shareable`**（仅管理端）、`dimensions[]`、`radar`、**`benchmarkUrl`**、`hasAnyAssessment` |

`dimensions[]` 每项：`dimensionCode` / `dimensionName` / `dimensionAbbr` / `weight`（该维权重百分比，供卡片标注加权口径）/ `founderScore`（**0–9 整数**）/ `gsvScore` / `perceptionGap` / `gapDirection`（`POSITIVE`/`NEGATIVE`/`NONE`）/ `era` / `detailUrl` / **`bothSubmitted`** / **`hasGap`** / **`questionSetMismatch`** / **`mismatchSide`** / **`hasDraft`** / **`draftPeriod`** / **`lastSubmittedAt`** / **`status`**。

- **`hasDraft` / `draftPeriod`** —— 卡片这一卷（管理端 GSV 卷、公司端 Founder 卷，与 `Start an Assessment` 落地的那一卷同端）在填报页的**落地季度**（所看季度已封住时是该卷该维最后提交的季度）该维有未提交草稿（`DRAFT` 行存在，不看有无作答），驱动维度行的 `There is a draft`；`draftPeriod` 为草稿所在季度，接口 2 页头同；见《结转锁定与回退审批》设计 §8.1 `CLOSED` 行。全部维度一次查全、不按维度循环；该期次两端都未提交的空态卡同样下发。
- **`lastSubmittedAt`** —— 卡片这一卷（管理端 GSV、公司端 Founder，与该行分数同一端）该维该期次 SOT（最新一条 `SUBMITTED`）的 `submitted_at`，UTC ISO 串 `yyyy-MM-ddTHH:mm:ssZ`；该端未提交为 `null`，**不回退取另一端**（管理端 GSV 未交、只有 Founder 交了也是 `null`）；两端都下发。驱动 A1 维度行下的提交信息条（§8.4）。
- **`dimensions[]` 不恒五项（D1 / R2）**：按当前 `status = 'Active'` 的维度集合返回，顺序取 `sort_order`；该期次尚无任何评估时同样按当前 `status = 'Active'` 的维度集合返回。已停用 / 删除的维度不再返回（历史期次同样不返回），其历史提交只在历史列表（接口 7）按行上快照名称展示。
- **`status`（`Active` / `Inactive`，落库列）** —— `dimensions[]` 每项随带，**直接下发 `erl_dimension_config.status` 列值**（§5.1.3）：该维度启用中 ⇒ `Active`，已软删停用 ⇒ `Inactive`（前端据此给历史期次的维度标灰）。
- **`bothSubmitted` / `hasGap` / `questionSetMismatch`** —— 卡片 Gap 区块每维小卡的三条**互相独立**的信息，前端不要合成一个枚举：
  - `bothSubmitted` 决定**圆点颜色**（该维 FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录（同 `(company_id, period, portal, dimension_code)` 内按 `submitted_at DESC, id DESC` 取首条 `SUBMITTED`） → 绿点，否则灰点）；
  - `questionSetMismatch` = 两端该维**题集版本号不等**（不可比，该维未送进分析）⇒ 圆点与 ready 同绿、文字琥珀；`mismatchSide`（`FOUNDER` / `GSV`）是**落后的那一端**，`questionSetMismatch = false` 时不下发（判据只能是维度级 `question_version_no`；任一端版本号解不出（快照行缺失）⇒ 打 WARN、按不 mismatch 继续（fail-open），解不出不等于版本号 0）；
  - 文字按**五级优先级**取（写死，不靠隐式短路）：`!bothSubmitted` → `Not submitted`；`questionSetMismatch` → `New version pending`（管理端括号内按 `mismatchSide` 点名落后一端 `New version pending (Founder)` / `(GSV)`，公司端不带括号）；`!analyzed` → `Analyzing…`（排队、在跑、失败都落在这一态，接口 17 没有维度级的失败标志）；`hasGap` → `Gap analysis ready`；else → `No Gap`。⚠️ **mismatch 排在 `hasGap` 之前**：旧产物未被本轮覆盖时两者会同真，此时显示 mismatch、旧条目不渲染。
  - 计数文案 `{n} of {total} dimensions have gap analysis for {period}` 由前端按本数组自算（`n` = 处于 ready / updating 态的项数，`total` = 数组长度；一个可分析维度都没有时整句不渲染），**不另加计数字段**。
- **`shared`（D3）**：该 `(company, period)` 的差距分析是否已分享给 Founder 端。管理端据此决定 `Share to founder` 按钮态（服务端 `shareable` 放行才激活，门槛见 §6.6 接口 27；未达成置灰，底部提示 `Share unlocks once gap analysis is available for all {total} dimensions in {period}.`（`{total}` = 当前 `Active` 维度数））；公司端 `shared = false` 时整个 Gap 区块显示空态（同接口 17，§6.6）。Share 动作走**接口 27**。

- ⚠️ **公司端不下发 `gsvScore` / `perceptionGap` / `gapDirection`**（PRD §3.5「创始人只能查看自己的分数」，§4.3）。
- `overallScore` 为**加权**综合分（§7.1），随出参附 `weightsApplied[{dimension, weight}]`，供前端在 tooltip 里说明「按 FRL 30% / PRL 20% … 加权」。

`radar`：**仅管理端下发；公司端整个字段不返回**（PRD §3.5「该图仅在 Portfolio 端显示」）。结构为 `series[]`，每项 `{ key, label, values[] }`，`values` 与出参 `dimensions[]` **同长、同序**（按当前 `status = 'Active'` 的维度集合的 `sort_order`），前端按数组长度渲染顶点数。取值为**维度 level 分（0–9 整数）**。四条序列：`FOUNDER` / `GSV` / `BENCHMARKIT` / `TOP_GSV_QUARTILE`，后两条取**适用基准记录的各维度分**（§7.8），无适用记录时该序列不下发。

- **`benchmarkUrl`（D7）**：**`/exitReadiness/benchmark?companyId={id}`**`[&period={period}]` —— **期次空则整段不拼**（写法与 `ErlDimensionServiceImpl#historyUrl` 一致），正常卡与空态卡**两个 build 点都带**。⚠️ **D1 自己不按期次取数** —— 该参数纯粹是 D1 面包屑「Score Details」回 A4 的**返回上下文**，不带则 A4 走服务端缺省期次（closed month 所在季度，R3）打开另一期。**仅管理端下发**（与 `radar` 同条件，公司端整个字段不返回）。前端在**雷达图正下方**渲染链接 `View Top GSV Quartile & External Benchmarks ›`（PRD §3.5）—— 基准页 D1 的站内入口（另一入口见 §6.5）。
- `bpmmScore` 为 1–5 参考数字，来源见 §13-Q1；A1 卡片不论有无数据都不渲染 BPMM，字段保留（恒 `null`）。
- **无提交即空态，不回退（R3）**：缺省期次取该公司 closed month 所在季度，该季度两端均无提交 → `hasAnyAssessment = false` + 各分数字段 `null`，**不降级显示上一季度数据**；closed month 取不到时回退当前自然季度（§7.1.2）。

### 6.2 维度详情页（A3 / E2，PRD §3.2 / §3.5）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 2 | `GET /erl/dimension/{dimension}` | A3 单维度模板页 | path `dimension`（即维度配置项的 code）；`companyId`、`period`、`portal`（默认 `FOUNDER`） | `header`、`submission`、`questions[]`、`gaps[]`、`actions[]` |

- `header`：`name` / `abbr` / `questionCount` / `weight` / `founderScore` / `gsvScore` / `perceptionGap` / `era` / `levelScore` / `terminatedLevel` / `benchmarkPosition`（**公司端恒不下发**） / `hasDraft` / `draftPeriod`（`+ New` 落地那一卷：管理端 GSV、公司端 Founder，与 `portal` 入参无关；口径同接口 1）。
  - ⚠️ **公司端不下发 `gsvScore` / `perceptionGap` / `benchmarkPosition`**（§4.3）。
  - **`levelScore` / `terminatedLevel`**：该端在本维度的得分与止步 level（全通关时 `terminatedLevel = null`）；A3 页头不渲染这两项，字段照常下发。
  - `benchmarkPosition`：`{ period, benchmarkitScore, topQuartileScore }` —— **本维度**的两个基准分（取 §7.8 的适用记录），无适用记录时为 `null`。
- `submission`：`period` / `submittedBy` / `role` / `submittedAt`（接口 2 / 8 / 22 共用此节点）。
- `questions[]`：`questionKey`（题目业务键，跨题库版本稳定 —— `erl_question_config.id` 每版一换，而 §5.2 允许同期次同维度两端绑不同题库版本，A4 双端并列按它对齐题目）/ `questionText` / `eraBand` / `eraLabel`（**`{Era 名} - {level}`，如 `Founder Era - 1`**，PRD §3.2）/ `evidenceSource` / `yesNo` / `note` / `attachments[]` / `locked`（该题所属 level 是否未解锁 —— 未解锁题在**已提交**记录里恒不出现，此字段只在填报页接口 3 用得到，A3 侧恒 `false`）。
  - **只返回已作答（= 已解锁）的题**，按 `eraBand` 升序、`sortOrder` 升序；未解锁 level 的题不在列表中（用户当时没看到它，展示它等于伪造未发生的作答，§7.2）。
  - `portal=GSV` 且调用者为公司端 → 直接 `BadRequestException`（PRD §3.2 公司用户无 GSV Tab）。
- `gaps[]` / `actions[]`：来源为 Python 的 `ai_erl_gap_analysis_task_item`，只取该维一个任务的条目，按 `result_task_id ?? id` 定位（§6.6）；无记录 / 未分析 / 无差距时为空数组。**每项只有 `title`**。差距分析是**单份产物**（无 `audience` 维度，D3），两端读到的是同一份内容。

### 6.2.1 全维 Score Details（A4）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 22 | `GET /erl/scoreDetails` | A4 一页取全维度逐题明细 | `companyId`、`period`（可选，缺省为 closed month 所在季度，R3）、`portal`（可选，见下） | `period`（取数所用期次，取不到为 null）、`dimensions[]`（每项带 `submission`）、`benchmark` |

- `dimensions[]`：**按当前 `status = 'Active'` 的维度集合动态返回**，顺序取 `sort_order`；期次尚无评估时同样按当前 `status = 'Active'` 的维度集合。每项：`code` / `name` / `abbr` / `levelScore`（0–9 整数）/ `terminatedLevel` / `weight` / `questionCount`（**该维已作答题数**）/ `totalQuestionCount`（该版本该维全部题数）/ `questions[]` / **`submission`**（见下）/ **`addNewUrl`** / **`historyUrl`**。
- **`status`（`Active` / `Inactive`）**：`dimensions[]` 每项随带，口径与接口 1 完全相同（直接下发落库列值，§5.1.3）。
- **每张维度卡的卡头入口（D5，PRD §3.5 / §3.7）**：后端随每维下发两个链接，体例同 F2 的 `detailUrl` —— `addNewUrl` = `/exitReadiness/assessment?companyId={id}&period={period}&dimension={code}`（`Add New`；这张卡装的是 **GSV 卷**时再追加 **`&portal=gsv`** —— 判据是「所看的卷」而非调用端，公司端恒 Founder 卷、恒不带），`historyUrl` = `/exitReadiness/history?companyId={id}`**`[&period={period}]`**`&dimension={code}`（`View history`，h 小写；**期次空白时整段不拼** —— B3 自己不按期次过滤、该参数**不参与取数**，只作 B3 面包屑「Score Details」回 A4 的返回上下文，不带则 A4 落到服务端缺省期次而非用户来时那一期）。两条链接由后端算好整条下发、前端不拼路径。A4 没有页级 `+ New` / `View history`。
- **`hasDraft` / `draftPeriod`** —— `addNewUrl` 指向的那一卷（判据同 `&portal=gsv`：所看的卷，双端模式即 GSV 卷）在填报页的**落地季度**（所看季度已封住时是该卷该维最后提交的季度）该维有未提交草稿，驱动卡头 `+ Add New` 前的 `There is a draft`（与 `+ Add New` 同显隐）；`draftPeriod` 为草稿所在季度，接口 2 页头同；见《结转锁定与回退审批》设计 §8.1 `CLOSED` 行。
- **`portal` 可选，管理端两端一起返回（D5，PRD §3.7「组合端需同时呈现 GSV 与 Founder 的记录」）**：管理端不传 `portal` 时，`dimensions[]` 每项以 **`portals[{ portal, submission, levelScore, terminatedLevel, questionCount, totalQuestionCount, questions[] }]`** 承载两端数据，本模式下 `dimensions[].submission` 恒 `null`；显式传 `portal` 时为单端模式，元数据由每维的 `dimensions[].submission` 承载（见下）。**公司端忽略该入参，恒按 `FOUNDER` 单端返回**（PRD §3.5「创始人只能查看自己的分数」，§4.3）。
- **`questions[]` 与接口 2 完全同一个结构**（同一个 `ErlQuestionDetailDTO`）：`questionKey`（双端并列按它对齐，见接口 2）/ `questionText` / `eraBand` / `eraLabel` / `evidenceSource` / `yesNo` / `note` / `attachments[]` —— **不新造第二套题目结构**。
- **`dimensions[].submission`** —— 单端模式下 = **本维最新一次提交**（SOT，`submitted_at DESC, id DESC`）的元数据 `period` / `portal` / `submittedBy` / `role` / `submittedAt`，**与该维 `questions[]` 取自同一条评估**，该维无提交时**不下发**该字段（`@JsonInclude(NON_NULL)`，前端归一为 `null`）；**双端模式不下发**，走 `dimensions[].portals[].submission`。理由：各维度提交时间戳各自独立，且须与答题卷同源显示最新一版。
- `benchmark`：该期次适用基准记录的**各维度明细**（`ErlBenchmarkDimensionDTO[]`，§5.6.1；项数随维度配置，不恒五项），取数规则同 §7.8；**公司端一律不下发**（§4.3），无适用记录为 `null`。
- **实现挂在既有的 `ErlDimensionService` 上新增一个方法**（`listAll`），Controller 用既有 `ErlDimensionController`，**不新建 service / controller 类** —— A4 与 A3 的差别只是「全维 vs 单维」，权限、版本、计分、裁剪规则完全相同。
- **一次查全**：全部维度的题目、答案、附件批量查出后在内存归组，**禁止按维度循环调接口 2 的逻辑**（N+1）；管理端双端模式同理，两端一次查出。
- 题目一律按该评估绑定的 `erl_question_config_version_id` 渲染（§7.9-①，与接口 2 同）。`erl_question_config_version_id` **每维一份**，同一期次不同维度可能绑不同题库版本，各自按自己的版本渲染，系统不阻止也不告警（R1）。
- **A4 公司端可访问（D5）**：ERL Card 右上角 `Full View ›` 是 A4 入口，**两端都有**（PRD §3.5 写「仅 Company portal」，按原型两端都有）。公司端访问时按上一条恒 `FOUNDER` 单端、`benchmark` 不下发；显式传 `portal=GSV` 仍 `BadRequestException`（同接口 2）。

### 6.3 填报（B，PRD §3.3 / §3.4）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 3 | `GET /erl/assessment` | B1 / B2 打开问卷（含回填草稿）；**恒按该评估绑定的题库版本渲染**（§7.9-⑤） | `companyId`、`period`、`portal`、**`dimension`**（必填，R1） | `assessmentId`、`status`、`dimension`、`questionVersionNo`、`answeredCount`、`totalCount`、`levelScore`、`canSubmit`、`levels[]`、**`lastSavedAt`**、**`lastSavedBy`**、**`latestPublishedVersionNo`**、**`hasNewerQuestionSet`**、**`fund`**（该公司 Portfolio Name，按当下归属现算，取不到为 `null`；仅 GSV 卷计算，Founder 卷不显示该格、恒为 `null`） |
| 4 | `POST /erl/assessment/draft` | 手动存草稿（幂等增量；**只由 `Save as draft` / `Submit` 两个按钮触发**）+ **回算解锁进度** | `companyId`、`period`、`portal`、**`dimension`**（必填）、`answers[{questionId, yesNo, note?, attachments[{fileId}]}]`（服务端按 `file_id` 查 `files`，§5.5；附件只有题级，只经 `answers[].attachments` 提交） | `unlockedLevel`、`levelScore`、`terminated`、`answeredCount`、`canSubmit`、`savedAt`、**`lastSavedBy`** |
| 5 | `POST /erl/assessment/submit` | 提交**本维度** | 同接口 4 + **`autoAnswerNo`**（缺省 `false`；**仅本接口读**，接口 4 / 29 忽略 —— 三个接口共用同一张入参） | `assessmentId`、`dimensionCode`（+ `dimensionName` / `dimensionAbbr` 快照）、`levelScore`、`terminatedLevel`、`era` |
| 6 | `GET /erl/assessment/periods` | 期次下拉 | `companyId`、**可选 `dimension`** | `currentPeriod`（当前季度 = 关账月所在季度，与接口 1 / 2 / 22 缺省期次同一口径，没有财务数据时退回当前自然季度；填报页网址没带期次时据此定默认季度）+ `periods[]`（`period` + 各端 `latestStatus` + `submissionCount`，口径见下；恒含 `currentPeriod`） |
| 7 | `GET /erl/assessment/history` | B3 历史列表 | `companyId`、可选 `dimension`（见下）、可选 `portal` | `records[]` |
| 8 | `GET /erl/assessment/{id}` | B3 某次提交的详情（复用 A3 题级布局） | path `id`、**可选 `dimension`**（D12） | 同接口 2 的 `submission` + `questions[]`（该次提交时的状态） |
| **28** | **`DELETE /erl/assessment/draft`** | **B1 `Reset` 按钮：丢弃当前草稿（D8）** | `companyId`、`period`、`portal`、`dimension` | `assessmentId`、`unlockedLevel`（恒 `1`）、`answeredCount`（恒 `0`） |
| **29** | **`POST /erl/assessment/progress`** | **草稿期推进解锁进度：只算不存、零写入** | `companyId`、`period`、`portal`、**`dimension`**、`answers[{questionId, yesNo}]`（与接口 4 同形入参；`note` / `attachments` 可传但服务端不读） | `dimensionCode`、`unlockedLevel`、`levelScore`、`terminated`、`answeredCount`、`canSubmit`、`levels[]` |

**规则**：
- **`questionVersionNo`**：该评估绑定的题库版本号。**首次打开（无草稿记录）时取当时最新的已发布版本并落库，此后不再变**；题库后续发布新版本对本次评估**完全无影响**（§7.9-⑤）。字段照常下发，前端只映射不渲染（§8.4「B 题集版本标注」）。**绑定粒度为「每维一份」（R1）** —— 同一公司同一期次的各维度可能绑不同题库版本（各自首次打开的时点不同），系统**不阻止、不告警**，各自按自己的版本渲染与计分。
- **单维平铺（接口 3，R1）**：一次填报 = 一个维度，出参不含维度数组，直接平铺 `dimensionCode` / `dimensionName` / `dimensionAbbr` / `weight` / `unlockedLevel` / `levelScore` / `terminated`（本维是否已到终止态）/ `levels[]`；`levels[]` 每项 `{ eraBand, eraLabel, state, questions[] }`，`state ∈ { CLEARED（全 Yes，前端折叠并打勾）, ACTIVE（当前作答中）, BLOCKED（本 level 有 No，终止于此）, LOCKED（未解锁） }`。**`LOCKED` 的 level 只下发 `eraBand` / `eraLabel` / `state`，`questions[]` 为空数组** —— 未解锁的题面不下发到前端，否则用户可从网络面板提前看到后续题目（PRD §3.3「就不再显示下一 Level」）。
- **`lastSavedAt` / `lastSavedBy`（接口 3 出参，D9，PRD §3.3）**：取 `erl_assessment.updated_at` / `updated_by` join 用户表得到 `{ name, role }`，**不新增快照列**。前端显示为按钮行左下的 `Draft saved {UTC 时刻} (UTC) by {姓名}`（**不显示角色**），且**只在本次访问内点过 `Save as draft` 之后才出**；「进来时接手了谁的草稿」由顶部 `Draft restored` 横幅讲，见 §8.4「B 草稿语义与上次保存提示」。产品语义：**草稿是公司共享的、不区分账户** —— A 保存后 B 打开看到的是 A 的内容，B 的保存**直接覆盖**（草稿唯一索引 `(company_id, period, portal, dimension_code) WHERE status = 'DRAFT'` 不含用户维度）。提交人以**最终点提交的那个人**为准（`submitter_name` / `submitter_role` 提交时快照），即使草稿全程由他人保存。
- **`latestPublishedVersionNo` / `hasNewerQuestionSet`（接口 3 出参，D10，PRD §3.3「若题库已更新，则提示题库更新，不做强制退出和更新」）**：`hasNewerQuestionSet = latestPublishedVersionNo > questionVersionNo`。版本锁定本体不变（仍恒按绑定版本渲染，§7.9-⑤）；前端为**强阻断二选一弹窗**（见 §8.4）——**存过草稿**（`status = DRAFT`）、草稿**有内容**且 `hasNewerQuestionSet` 时一进页面就弹、不可关闭。`answeredCount = 0` 的空草稿由前端在载入时就地走接口 28（删除该空草稿行，重拉后按最新已发布版本出题），**不弹窗**；服务端出参口径不变。
- 草稿保存**幂等增量**：只 upsert 传入的 `answers`（含其 `attachments`），不影响未传项 —— 首个 No 之后的除外，由改答回收删除。**服务端在每次保存后按 §7.2 重算该维的 `unlocked_level` / `level_score` / `terminated_level` 并回写**（三列在 `erl_assessment` 上，R1），出参把新的解锁进度带回前端 —— **解锁判定只在服务端做**，前端不自行推断（否则前端算法与提交校验会漂移）。草稿期解锁进度由**接口 29 只算不存**地推进，计分用的是服务端同一份 `ErlLevelScorer`，且落盘（接口 4）与提交（接口 5）时服务端仍会按传入答案**重算一遍**，前端带来的进度值一概不采信。
- **不做期次-配置绑定**：任何期次的维度列表、权重、综合分、Stage、雷达图一律读 `erl_dimension_config` 当前 `Active` 行 —— **历史会随改权重 / 增删维度而漂移（已接受，§13-Q21）**。
- **拒绝对未解锁 level 的题作答**：`answers` 中出现 `eraBand > unlockedLevel` 的题 → `BadRequestException("Answer levels in order.")`。这是逐级解锁的服务端兜底，防绕过前端直接提交后续 level。
- **改答已作答的题会重算并可能回收解锁**：把某题从 No 改回 Yes → 该 level 若因此全 Yes，则解锁下一 level；把某题从 Yes 改成 No → **该 level 之后的所有答案与附件一并删除**（它们已不该存在），同级排在那道 No 后面的答案与附件也一并删除，出参 `unlockedLevel` 回退。前端在答 No 当场已清空其后作答、不提示（§8.4「B 答 No 后后面答题全部重置」）
- `totalCount` = 该题集版本**本维度**的全部题数；`answeredCount` = 本维度已作答题数（= `erl_assessment_answer` 行数（`where erl_assessment_id = ?`））。逐级解锁下二者通常**不相等**，这是正常的。
- **`canSubmit`**：**本维度**到达终止态且本维度已解锁题全部作答时为 `true`（PRD §3.3「就不再显示下一 Level，激活提交按钮」）。前端提交按钮直接绑该字段，不自行判断。不看期次，未来季度与当季一样可提交（填报状态非 `OPEN` 或本期处于回退审核冻结时为 `false`，见《结转锁定与回退审批》设计）。
- 提交前置校验。⚠️ **校验对任何调用方一视同仁，没有旁路** —— `autoAnswerNo = true`（B 填报页「题库已更新」弹窗的 `Submit draft content`）只是在校验**之前**先把顺序上第一道未作答的题补成 No（本维随之终止、漏答归零），补完照样逐条走下面的校验；而且它**本身还有一条前置** —— 仅当该草稿确实还绑在旧题库版本上（`hasNewerQuestionSet`）时才被接受，否则**静默忽略**、按原规则校验。⚠️ **编号不是报错优先级** —— 服务端实际先判校验 3（`totalCount <= 0`）再判 1、2；三条不会同时命中（0 题维度的 `unansweredCount` 恒 0 且 `terminated` 恒 true），编号沿用是因为全仓注释与台账都按「§6.3 校验 3」引用它：
  - **校验 1**：**已解锁的题全部已作答**，否则 `BadRequestException("Please answer all visible questions before submitting.")`。
  - **校验 2**：**本维度到达终止态**（本维出现至少一个 No，或该维全部有题 level 全 Yes），否则 `BadRequestException("Keep answering until this dimension reaches a No or clears all nine levels.")`。该维 0 题时一律拒绝提交，见校验 3。其余维度是否已提交**不影响本次提交**。
  - **校验 3**：**该维在本期次绑定的题库版本里必须有题**（`totalCount > 0`），否则 `BadRequestException("This dimension has no questions in the question library version bound to this period.")`。与视图侧 `canSubmit` 的条件**逐条对齐**（否则 0 题维度会落出 `level_score` 恒为 null 的 SUBMITTED 行，污染 ERL Card / 组合层 / Share 门槛判定）。
- 提交成功后：该行 `status = SUBMITTED`、写 `submitted_at` 与 `dimension_name` / `dimension_abbr` 快照；组的定义为 `(company_id, period, portal, dimension_code)`，**最新一条由 `submitted_at DESC, id DESC` 判定**；**`erl_assessment` 本行的 `level_score` / `terminated_level` / `unlocked_level` 由服务端算定并冻结**。**已 SUBMITTED 的记录不可再改**（PRD §3.3）；再次填报即新建下一条 `DRAFT`。
- **接口 28（D8，PRD §3.3 `Reset`）**：在一个事务内删除**当前草稿**（`status = 'DRAFT'` 的那一行），删序：附件 → 答案 → 草稿行 —— 回到 §7.7「`DRAFT → 无记录`」与 §7.9-⑤ 的正路，此后新建的草稿自然绑定当时最新的已发布版本。出参为 `assessmentId`（**被删那一行的 id**）/ `unlockedLevel` / `answeredCount` 三个字段 —— 前端 Reset 成功后重拉接口 3，新版本号与题目列表由那一次取回。
  - **附件一并删除**：附件挂在作答上，随作答一并删（`erl_answer_attachment` 按 `erl_assessment_answer_id` 批量删）；附件不产生任何知识库 / rag 条目（§6.7），删附件时没有第二处东西需要联动。
  - 不做二次确认：`Reset` / `Discard draft` 点下去直接调本接口。
  - 找不到 `DRAFT` 行时**幂等返回成功**（`assessmentId = null` / `unlockedLevel = 1` / `answeredCount = 0`，不抛异常）；已提交记录**不受影响**（§9）。
  - 顶部按钮组为 `Save as draft` / `Cancel` / `Reset` / `Submit`：`Save as draft` = 手动落盘（走接口 4；无自动保存，**接口 4 只由 `Save as draft` 与 `Submit` 两个按钮触发**，草稿期的解锁推进走**接口 29**）；`Cancel` = 直接离开页面，**不做任何数据操作**（不调接口）。⚠️ **草稿未必已在服务端** —— 没点 `Save as draft` 就离开即全部丢失，且**不做任何拦截或提示**（§8.4「B 草稿落盘时机」）。
- **接口 29（不点按钮绝不写库）**：与接口 4 **同形入参**（复用同一张请求体），服务端照常按 §7.2 算 `unlockedLevel` / `levelScore` / `terminated` / `canSubmit` 并按解锁进度装配 `levels[]` 回传，但**不写任何一张表** —— 不建草稿行、不 upsert 答案、不删附件、不回写 `unlocked_level` / `level_score` / `terminated_level` 三列，**零写入是本接口的核心不变量**。
  - **只有 `questionId` + `yesNo` 参与计算**：`note` / `attachments` **不参与计分、服务端读都不读**；`yesNo` 仍 `@NotNull`，未作答的题前端不发（与接口 4 一致）。
  - **鉴权与维度校验与接口 4 逐条相同**：`portal` 可读性、`dimension` 必须属于当前 `status = 'Active'` 的维度集合（§4.3「填报写接口的维度合法性」）、跨租户题库隔离；取题的组织来源是**被填报的公司**，不是调用者登录态组织（读写必须同源）。
  - **`LOCKED` 的 level 不下发题面这条过滤照旧生效**（`questions[]` 为空数组，见上方单维平铺条） —— 正因为新解锁 level 的题面只能由服务端按进度下发，草稿期才需要这么一个接口（否则答满一级后屏上毫无反应、Submit 永远亮不起来）。
  - 因不落库，出参 `levels[].questions[].yesNo` **恒为 `null`**，前端必须**以本地作答为准**、不得用回包重建答案（否则用户答案会被抹平）。
  - 出参**刻意不带** `submissionCount` / `fund` / `latestPublishedVersionNo` —— 这些值在一次填报期间不会变，接口 3 已经给过。
  - 已 `SUBMITTED` 的记录不受影响（本接口本就不写库）；本接口**不替代接口 4** —— 答案要持久化仍必须点 `Save as draft` 或 `Submit`。
- **接口 6 的口径（R1）**：`latestStatus` / `submissionCount` 是「该端**该维度**」的口径 —— 传 `dimension` 时按该维度返回；不传时 `latestStatus` 取该端**各维度的最保守值**（有任一维度未提交即 `DRAFT`），`submissionCount` 取各维度之和。维度列表按当前 `status = 'Active'` 的维度集合取（D1）。
- `records[]` 字段（PRD §3.9，D12 / R1）：`assessmentId` / `period` / `portal` / **`dimensionCode`**（一条记录 = 一个维度；随带 `dimensionName` / `dimensionAbbr` 快照）/ `submittedAt` / `submitterName` / `submitterRole` / `levelScore` / `stage` / `era`。默认 `submittedAt DESC`。
  - **排序**：实现只按 `submitted_at DESC, id DESC` 排（两个派生查询 `findByCompanyIdAndStatusOrderBySubmittedAtDescIdDesc` / `...AndPortalAnd...` 的排序键就写在方法名里），即**一条按提交时间倒排的平铺列表**，不做按 `(companyId, period, portal, dimensionCode)` 四元组的外层归组排序。
  - **提交序号**：本接口**不下发任何序号字段**；B3 列表**不显示 `Submission #n`**（若后续要序号，只能按分组内行号实时算，**翻页会漂移**）。
- **列语义（D12，PRD §3.9）**：
  - **`Submitted` 列** —— 直接渲染 `submittedAt`。
  - **无 `Completion` 列**，B3 列表不显示题集版本 / 止步 level。
  - **分数列为「维度 Overall Score」** —— 取该维 level 分（`{levelScore}/9` 整数）+ 该维 Era 徽章，**不是加权综合分**（`records[]` 无 `overallScore`）。
  - **`Portal` 列仅管理端渲染** —— 公司端只有 Founder 侧数据，该列恒定值、无信息量。
- **接口 7 的 `dimension` 口径（R1）**：一条记录只属于一个维度，`dimension` 是**真正的行过滤**（`where dimension_code = ?`）。不传 `dimension` 时返回该公司全部维度的提交记录，混排按 `submittedAt DESC`（此时 `Dimension` 列必显示）。前端从 A4 的 `View history` 进入时带 `?dimension={code}`，在列表页头标注当前过滤维度（`Financial Readiness (FRL)`）。
- **接口 8 的 `dimension` 入参（D12）**：从带维度的历史列表进入详情时透传，**只渲染该维度**的题目明细；不传时按该记录自身的 `dimension` 渲染（记录已是维度级，该入参实为一致性校验 —— 与记录不符即 `BadRequestException`）。

### 6.4 题库配置（C，PRD §3.8）

> C 模块的读写**一律面向草稿版本**，写接口的定位参数是 **`questionKey`** 而非题目 `id` —— 写时复制会让草稿行拿到新 `id`，前端手里的 `id` 属于已发布版本，按 `id` 定位在「首次编辑」这一步必然失配。

| # | 方法 / 路径 | 用途 | 关键入参 |
|---|-------------|------|----------|
| 9 | `GET /erl/question` | C1 列表（按 `eraBand` 分组、组内带题数、按 `sortOrder` 排序）；**返回草稿版本**，无草稿时返回最新已发布版本 | `dimension` |
| 10 | `POST /erl/question` | C2 新增 | `dimension`、`eraBand`（1–9 level）、`questionText`、`evidenceSource` —— 与 PRD §3.8 的题目字段逐项一致 |
| 11 | `GET /erl/question/{questionKey}` | C3 编辑回填 | path `questionKey` + **query `dimensionCode`（必传）** |
| 12 | `PUT /erl/question/{questionKey}` | C3 更新 | path `questionKey` + **query `dimensionCode`（定位用的**原维度**，必传）** + 体同 10（体里的 `dimensionCode` 是**目标维度**） |
| 13 | `DELETE /erl/question/{questionKey}` | C3 删除（**草稿版本内物理删行**） | path `questionKey` + **query `dimensionCode`（必传）** |
| 14 | **`PUT /erl/question/reorder`** | **C4 拖拽重排** | `dimension`、`eraBand`、**`questionKeys[]`**（该 band 内的完整新顺序） |
| 21 | **`POST /erl/question/publish`** | **C5 发布草稿版本** | 仅可选 `organizationId`；出参 `versionNo`、`publishedAt` + **`dimensions[{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }]`**（本次发布写入 `erl_question_config_dimension_version` 的逐维快照，§5.1.5；与接口 26 共用同一个出参结构，发布后的 toast 可直接报维度名） |
| 23 | **`GET /erl/dimension/config`** | **C6 读维度配置**（`Dimension Configuration`，D13） | 可选 `organizationId`（缺省 = 登录态组织）+ **可选 `includeDeactivated`**（默认 `false`）；出参 `savedAt` / `savedBy`（取本组织**全部行审计列 `updated_at` 的 max**、`savedBy` 取该行的 `updated_by`）、`dimensions[{dimensionCode, dimensionName, dimensionAbbr, sortOrder, weight, **status**}]`（默认只返 `Active` 行，带 `includeDeactivated=true` 时返全量供 C6 回看与恢复；C6 **恒**带 `includeDeactivated=true`（停用行由常显区块承载，§8.4-C6），该入参保留供其它调用方）+ **`deletable`**（boolean 非空：`true` ⟺ 该 `dimension_code` **从未进入任何已发布题库版本的维度快照** ⇒ 行尾给垃圾桶=删除；`false` ⇒ 给电源按钮=停用。⚠️ **判据必须 join `erl_question_config_version` 并过滤 `status = 'PUBLISHED'`** —— `erl_question_config_dimension_version` **草稿版本上也有行**（§5.1.5），只查快照表会把「只在未发布草稿里改过题」的维度误判为不可删）。⚠️ **`deleted = true` 的行任何情况下都不下发**（**含 `includeDeactivated=true`**）—— 那个入参管的是 `status`，与 `deleted` 正交，混用会把已删维度重新暴露到 `Deactivated Dimensions` 区块里）、`total`（**`Active` 行**的权重合计 —— 含 `Inactive` 行的合计永远不是 100，前端的 Exceeds/Needs 提示会算错） |
| 24 | **`PUT /erl/dimension/config`** | **C6 整组保存维度配置**（D13） | **顶层**：`savedAt`（**必传**，取自上一次接口 23；不匹配即「配置已被他人修改，请重新加载」，防 lost update。该组织**首次保存**时库里一行都没有、令牌本身就是 `null`，此时**必须传 null** —— 一边有一边没有同样算冲突；不匹配返回**业务错误**：**HTTP 200 + `success: false`**（§4.3），既不是 409、也不是 400）+ `deactivatedCodes[]`（**必传**，本次要停用的已有维度 code，**可为空数组**）+ **`deletedCodes[]`**（本次要**删除**的已有维度 code ⇒ 置 `deleted = true`。⚠️ **与 `deactivatedCodes` 不同，它可缺省**（缺省 / null = 空数组）：`deactivatedCodes` 必传是为了杜绝「未出现即停用」的隐式软删（下方校验 ⑥），而 `deletedCodes` 缺省表达的就是「什么都没删」，本身安全）+ `dimensions[]`（**整组替换**）。<br>**数组每项二选一**（显式判别）：① **已有维度**：`{dimensionCode, dimensionName, dimensionAbbr, sortOrder, weight}` —— `dimensionCode` 必须命中本组织已有行；② **新增维度**：`{isNew: true, clientRef, dimensionName, dimensionAbbr, sortOrder, weight}` —— **不带 `dimensionCode`**，`clientRef` 是前端生成的**幂等键**（本次请求内唯一）。**两者都不带、或同时带 `dimensionCode` 与 `isNew` → 业务错误**（§4.3）。<br>新增项**不做任何重名 / 重缩写校验**：与任何已有行（含 `Inactive` 行）同名 / 同缩写一律**直接创建**，不阻断、不要求二次确认；两行靠 `dimension_code` 区分。<br>出参：同 23 **+ `created[{clientRef, dimensionCode}]` 映射**（前端用出参 `dimensions[]` 整体替换本地列表、不读 `created`（§8.4-C6）；该映射保留给需要保持本地行身份的调用方，也便于排障）；出参 `dimensions[]` **按 `sortOrder` 升序**（契约保证） |
| 25 | **`GET /erl/question/version`** | **C7 版本清单** —— C7 页头版本下拉的数据源 | 仅可选 `organizationId`（缺省 = 登录态组织）；出参 `versions[]`，返回 `DRAFT` + `PUBLISHED`、按 `versionNo` 倒序草稿最前；C7 的版本下拉**只取 `status === 'PUBLISHED'` 的项**，过滤做在前端取数 hook `useQuestionVersions` 里 |
| 26 | **`GET /erl/question/version/{versionNo}`** | **C7 某一版的整份题面** | path `versionNo`；出参复用接口 9 的 `{ version, questions[] }` + **`dimensions[]`**（全部维度一次给全，项数动态） |

- **C 模块 11 个接口（9-14 / 21 / 23 / 24 / 25 / 26）的组织归属：缺省取 `SecurityUtils.getOrganizationId()`，接受可选 query 入参 `organizationId`**（POST / PUT 亦走 query，不进 Request 体），且只认调用者组织树内的组织（§4.3）；仅管理端可调。
- **接口 24 的校验（D13 / R2）**：
  1. **`status = 'Active'` 的维度权重合计恰为 `100.00`**（`numeric(5,2)` 精确比较，不用浮点等值；`Inactive` 行仍在表里，计入则永远凑不满 100），每个 `0 ≤ weight ≤ 100`，否则 `BadRequestException("Dimension weights must add up to 100%.")`。前端 Save 按钮同条件禁用，**服务端不因前端已拦就省掉校验**。
  2. **维度集合合法**：① **带 `dimensionCode` 的项**必须命中本组织已有行，否则**业务错误**（HTTP 200 + `success: false`，§4.3）（跨组织的 code 天然命中不到）；② **带 `isNew` 的项**由服务端生成 code（§5.1.3），**不对 code 做任何格式 / 长度 / 大写校验**（同一列里 `FRL` 与 `OPS4K7M` 并存，任何断言都会误杀一方）；③ `dimensionAbbr` **1–8 字符**，不查重 —— ⚠️ **长度校验必须保留**：`abbr` 与 `code` 已解耦，列宽就是 `varchar(8)`，不校验会直接撞列宽；④ `sortOrder` 无重复；⑤ **至少保留一个 `Active` 维度**（全停用时合计恒为 0，Save 永远失败）；⑥ **集合完整性校验（防静默软删）**：`当前 Active 集合`（`deleted = false` 的那些）必须恰等于 `带 code 的项` ∪ `deactivatedCodes` ∪ **`deletedCodes`**。对不上即**业务错误**（§4.3）并列出缺口 —— 前端漏传一行的 code 就会落到这里，**不得静默当新增处理**。⚠️ 并集里**必须有 `deletedCodes`**：被删的那一行既不在 `dimensions[]` 也不在 `deactivatedCodes[]` 里，漏了这一项每次删除都会被判成「前端漏传了一行」。
     - **同名不校验的代价（已接受）**：管理员误删后重填会建出**孪生维度**，历史照旧挂在旧停用行的 `dimension_code` 上；恢复旧行的正路是 `Deactivated Dimensions` 区块的 `Activate`（§8.4-C6-⑤）。
  3. **`deletedCodes[]` 的三条校验** —— 一律是**业务错误：HTTP 200 + `success: false`**（与乐观锁冲突同形态），**且库中不得有任何写入**：
     - ⑧ **code 不命中本组织已有行** → `Unknown dimension code: {code}`（跨组织的 code 天然命中不到，与 ① 同一道理）。
     - ⑨ **该 code 在已发布版本的快照里出现过**（`erl_question_config_dimension_version` join `erl_question_config_version` 且 `status = 'PUBLISHED'`）→ `This dimension was published in a question set and cannot be deleted: {code}. Deactivate it instead.` ⚠️ **前端不显示垃圾桶，但抓包可以直接传** —— 这条校验是唯一的实际防线，**不得因「前端已按 `deletable` 拦了」而省掉**。文案点名替代动作（改用停用）。
     - ⑩ **同一个 code 同时出现在 `dimensions[]` / `deactivatedCodes[]` / `deletedCodes[]` 中的两个及以上** → `Dimension cannot be saved, deactivated and deleted at once: {code}`。**不定义优先级** —— 任何优先级都是在猜用户意图，而三个桶的组合是前端状态机出 bug 时的典型产物，报错让它暴露在开发期而不是变成一次静默的错误落库。
     - ⚠️ 三条校验与 ⑥ 的集合完整性一律在 **`validate()` 阶段、用整组锁读到的 `existing` 判定**（§7.11-②），**落库前不写任何一行**（业务错误要求「库中不得有任何写入」）。
  - **Save 按钮双条件**：① 脏态（维度增 / 删 / 排序 / 权重任一变化）② 权重合计 = 100%；越界提示 `Exceeds 100% by {n}%` / `Needs {n}% more`。
- **就地整组替换，不产生版本**：每次接口 24 成功即按 `(organization_id, dimension_code)` **upsert** `erl_dimension_config`（覆盖 name / abbr / sort_order / weight / status；「上次保存于何时 / 谁保存的」由审计列 `updated_at` / `updated_by` 承接），**提交里缺席的维度置 `status = 'Inactive'`（软删，不删行）**。**保存即全局生效**。
  - **保存后立即影响所有期次（含历史期次）的综合分与 Stage**。Save 不弹确认框，点了直接保存；页面上没有任何一处提示「保存会回溯改变历史期次」（§8.4 C6）。⚠️ **连带副作用**：改维度集合会回溯改变 Share 门槛（§7.5「报告就绪（ready）」判断，ready 只用于 Share 门槛）与 Gap 区块的 `{n} of {total}` 计数。产物在另一个服务的库里、跨服务不可能同事务，因此由 `reconcile` 自然覆盖 —— 停用维度退出可分析集合，下次读或下次提交时 `reconcile` 按当前 Active 集合新建记录（已分享记录不变，I1）；改权重不改变作答，不触发重跑。<br>⚠️ **残留边界（已知并接受）**：**新增**一个 Active 维度、而该期次的分析此前已 `shared = true` 时，公司端会继续看到那份按旧维度集合生成的分析（内容不假、只是少一维），直到新维两端提交后重生成 —— 因为「新维未提交 ⇒ 不进可分析集合 ⇒ 不重生成」是刻意的（否则该期次永远处于分析中）。要收需新接口或新判定，属产品口径问题，已记 `CIOaas-api/docs/待优化项.md`。
  - 配置页的「**停用**维度」（入口为**电源按钮**）= **软删**：该维度**不出现在接口 24 提交的 `dimensions[]` 里**、且其 code 在 `deactivatedCodes[]` 中，服务端据此置 `status = 'Inactive'`；**行与 `weight` 原样保留**，历史提交记录照常可查，`Retired` 灰样式由 `status` 列**直接判定**。
  - 配置页的「**删除**维度」= 置 **`deleted = true`**：只对 `deletable = true`（该 code 从未进入任何已发布题库版本的快照）的维度开放，code 走 `deletedCodes[]` 显式点名；行留在表里但**所有读侧一律排除**、页面两处都不显示、**无恢复入口**（§5.1.3）。
  - 删除拦截的判据是「**是否进入过已发布题库版本**」而不是「**有无历史数据**」—— 后者会连「有人填过、但题库从没发布过」的维度也拦住（那种维度删掉是安全的）；保护对象是**已发布题库版本的语义**：那份版本的维度快照与按 code 关联的历史，必须始终解得出那个维度。
- **`Dimension Configuration` 的改动不进题库版本、不激活 Publish，走自己的 Save**（§5.1.3；题库 Tab 的 Publish 语义不变，§7.9）。
- **单题接口（11 / 12 / 13）必传 query 参数 `dimensionCode`**：题目行的键位是
  `(organization_id, dimension_code, version_no, question_key)`，而题目集版本号按维度各自自增 ——
  **不知道维度就解析不出用哪个 `version_no`**，`questionKey` 单独不是一个完整的定位符。
  配置页本就按维度分 Tab，前端手上一定有这个值。
  - ⚠️ **接口 12 的两个 `dimensionCode` 不是同一个**：query 里的是**原维度**（定位用，= 当前所在 Tab），
    请求体里的是**目标维度**。两者不同即**跨维度移动**：题目行从原维的版本线移到目标维的版本线上，
    **两条线都要先克隆**（各调一次 `ensureDimensionCloned`），并排到目标组末尾；diff 上表现为
    原维 removed + 目标维 added，口径自洽。
- **接口 10 / 12 / 13 / 14 均触发写时复制**：进入 service 先 `ensureDraftVersion()`（**两级判据**，§7.9-②）—— ① 无草稿版本行则同事务内建一条（组织级 `version_no = max + 1`），有则**取行锁复用**；② **再判本维度本轮是否已克隆**（`draftDimensionVersions()`），未克隆才克隆该维题目行并拿新的 `version_no`（只克隆被改动的那个维度）。**漏了第二级判据 = 直接写穿已发布版本**，再在草稿版本上执行本次变更。四个接口都不改已发布版本一个字节。
- 接口 14 在一个事务内按数组下标重写该 band 全部题目的 `sort_order`；**只允许同 band 内重排**。**跨 band 移动不走本接口**，而是由题目行内的 `Era band` 下拉触发**接口 12 的全量更新**（§8.4 C4）。
- 接口 9 出参：根节点增加 `version { versionNo, status, lastEditedBy, lastEditedAt }` 与 **`hasDraft`**（布尔）—— **`hasDraft` 即 Publish 按钮的激活依据**（存在草稿版本 = 有未发布变更）；每题增加 `changeType`（`ADDED` / `MODIFIED` / `REORDERED` / `UNCHANGED`，由草稿与最新已发布版本按 `question_key` 逐字段 diff 得出），供列表打徽章。**`hasDraft` 是全局的，切 Tab 不重算**（PRD §3.8「**任意维度**有变更，按钮即激活」，维度数动态）。
- 接口 21 在一个事务内把草稿版本 `status` 置 `PUBLISHED`、写 `published_at` / `published_by`，**并为每个 `Active` 维度写一行 `erl_question_config_dimension_version`**（`dimension_code` / `dimension_name` / `dimension_abbr` / `question_version_no` / `sort_order` / `bound_at`，§5.1.5）。**无草稿版本时返回业务错误**（§4.3）（前端按钮此时已禁用）；不做「重复点击幂等」的特殊处理 —— 发布成功后草稿已不存在，第二次点击落到同一分支。
- **接口 25 出参**：`versions[]`，每项 `versionNo` / `status`（`DRAFT` | `PUBLISHED`）/ `publishedAt` / `publishedBy` / `lastEditedBy` / `lastEditedAt`。**按 `versionNo` 倒序，草稿（`DRAFT`）排在最前**。
  - **仅可选入参 `organizationId`**（缺省取 `SecurityUtils.getOrganizationId()`，可指定组织树内的组织）、**仅管理端可调**，公司端报业务错误（§4.3 —— 端类型 / 组织越权同样由 `ErlAccessServiceImpl` 抛 `BadRequestException`）。**只读接口，不触发写时复制**（不调 `ensureDraftVersion()`）。
  - ⚠️ **草稿行照常下发，但 C7 不显示它们**：C7 的版本下拉按 `status === 'PUBLISHED'` 过滤，过滤**落在前端取数 hook `useQuestionVersions`**、**不下沉到服务端** —— 「库里到底有没有草稿版本」是「`Publish` 按钮能不能点」的判据来源，服务端一旦把草稿行滤掉，那个判断就没了数据来源；C7 是本接口**当前唯一的消费方**，过滤放在页面侧的代价只是一个 `filter`。⚠️ 由此带来一个**空态**：只有草稿、没有任何已发布版本的组织，C7 下拉为空、页体走 `No published question set versions yet.`（§8.4-C7）。
- **接口 26**：出参**复用接口 9 的 `ErlQuestionConfigListResponse`**（`version` + `questions[]` + `dimensions[]`），不为它另造一对 DTO/Response。与接口 9 的四点不同：
  - **版本由 `versionNo` 指定**，不是「草稿优先的当前版本」；`versionNo` **只在组织内唯一**，故解析时必须带组织（缺省登录态，可由可选入参 `organizationId` 指定并经 §4.3 复核），查不到即 `BadRequestException("Question set version not found.")`。
  - **全部维度一次给全**（接口 9 是单维度），复用已有的 `findByVersionIdOrderByDimensionAscEraBandAscSortOrderAsc`。⚠️ 其中维度序是 `dimension` 列的**字典序**，不是业务序 —— **前端按本接口的 `dimensions[]` 归组与排序**，**不读接口 23 的当前生效配置**（`ErlDimensionEnum` 枚举与前端静态 `DIMENSIONS` 映射均不存在）。
  - **`dimensions[{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }]`**：取 `erl_question_config_dimension_version` 中该 `erl_question_config_version_id` 的逐维快照行（§5.1.5），按 `sortOrder` 升序。名称 / 缩写 / 顺序均为**发布当时的快照**，后续改名不影响。⚠️ **出参里没有 `weight`**：接口 26 的 `dimensions[]` 是**不含 `weight`** 的窄 Response `ErlQuestionConfigDimensionVersionResponse`（DTO `ErlQuestionConfigDimensionVersionDTO` 同形，两处 builder 见 `ErlQuestionConfigVersionServiceImpl` 的发布态与草稿回退分支，**从不 set weight**），所以**既不下发、也无从漂移**；前端 `CIOaas-web/src/services/api/exitReadiness/response.ts` 的对应类型注释亦写明「**没有 `weight`、没有 `status`**」。<br>　**`questionVersionNo`**（int）= **该维在这一版下用的题目集版本号**（§5.1.5 的 `question_version_no`，按 `dimension_code` 自增的那条独立版本线，§5.1；**该维在该版下无题时为 `0`**）—— 前端据此知道「第 n 次发布里，各维分别落到了自己的第几版题目」；它与外层的组织级发布批次号 `versionNo` 不是同一个东西（§5.1.5 的「两者不冗余」一段）。C7 当前不渲染它，字段留着是因为它是这张快照表**唯一**能表达「这一版用的是哪份题」的列。**草稿版本（无快照行）时回退当前 `Active` 集合**（C7 下拉只列已发布版本，该回退在 C7 上不可达，**保留**给 API 直调方）。**接口 9 恒为 `null`** —— 配置页 C1 的维度骨架另走接口 23。本字段是 C7 卡片骨架的**唯一**来源 —— C7 不拿接口 23 的当前生效配置做任何事（既不过滤、也不打 `Retired` 灰标），**本页与「今天的维度配置」彻底解耦**。本字段**不按当前配置过滤**：发布当时快照里有几个维度就出几张卡。
  - **`hasDraft` 与每题 `changeType` 恒为 `null`** —— `changeType` 是「草稿 vs 最新已发布」的实时 diff，套到历史版本上没有意义（历史版本的对比基线早已改变）。
  - **只读接口，不触发写时复制**（不调 `ensureDraftVersion()`）；**仅管理端**，公司端报业务错误（§4.3）。**不新增表**，也**不新增「查全部题」的无版本查询** —— 仍先解析出 `versionId` 再查。
- 新增题目（接口 10）`sort_order = 该 band 当前 max + 1`，`question_key` 新生成 UUID。
- **生效范围**：四类变更**全部只落草稿版本**，对填报页、维度详情页、计分、组合层**一概不可见**，直到接口 21 发布。详见 §7.9。

### 6.5 基准（D，PRD §4）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 15 | `GET /erl/benchmark` | D1 页（两张卡一次取全） | `companyId` | `records[]` |
| 16 | `POST /erl/benchmark` | D2 保存记录 | `companyId`、`period`、`note`、`dimensions[]`（项数动态，见下） | `recordId` |

**出参结构**：

```
records[] { id, period, isLatest,
            recordedAt,                              // 真实录入时刻 = 审计列 created_at，ISO-8601 串；为空下发 null
            recordedBy { name, role },               // created_by join 用户表
            benchmarkitAvg, topQuartileAvg,          // 各维度平均，服务端算（§7.8）
            note,                                    // 空返回 null，前端显示 "—"
            dimensions[{ code, name, abbr, benchmarkitScore, topQuartileScore }] }   // 前端按 `6.5/9` 渲染
```

- **维度列表动态（D1 / R2）**：读接口 15 按**当前 `status = 'Active'` 的维度集合**返回维度与顺序，写接口 16 按**当前 `status = 'Active'` 的维度集合的全部维度**校验。
- **页面入口（D7）**：D1 页的站内入口是 **ERL Card 雷达图正下方的链接 `View Top GSV Quartile & External Benchmarks ›`**（`/exitReadiness/benchmark?companyId=`**`[&period={period}]`**，随接口 1 的 `benchmarkUrl` 下发，**仅管理端渲染**）；**另一个入口是 A4 末位基准 Tab 的 `View history`**（同款带期次，由前端拼）—— 两个入口都带期次，是为了让 D1 的面包屑「Score Details」能回到用户来时那一期（**D1 自己不按期次取数**）。
- `records[]` 按 **`created_at DESC NULLS LAST, id DESC`** 倒序（纯录入时间倒序，补录旧期次的那条也排在最前；同期次可有多条）；只有首条 `isLatest = true`（D1 的 `LATEST` 徽章）。⚠️ 这个 `isLatest` 是**基准记录的派生字段**（按上述排序的首条），与 `erl_assessment` 无关。
- `recordedAt`：**审计列 `created_at` 的真实录入时刻**，Java 类型 `Instant`、下发 **ISO-8601 串**（如 `2026-09-10T07:21:33Z`）；`created_at` 为空的历史行下发 **`null`**（不拿期末日兜底）。三个展示位（D1 `Record History` 的 `SUBMISSION TIME` 列、D1 卡一与 D3 详情卡的提交元信息行）一律经 `formatErlIsoDate()` 渲染成 **`YYYY-MM-DD`**（只到日），**不直出原串**（§8.4-D1）。⚠️ 同期次可有多条且 `PERIOD` 列相同 ⇒ 这一列是屏上**唯一能分辨先后**的信息，**不可退回期末日**。
- **`Details` 不额外发请求** —— 每条记录的各维度明细随 `records[]` 一并下发（单公司按季度累积，量级极小），前端行内展开 / Modal 渲染，复用 `Current Version` 卡的表格组件。
- 接口 16 的 `dimensions[{ code, benchmarkitScore, topQuartileScore }]` **必须覆盖当前 Active 维度集合的全部维度、各值在 1–9**，否则 `BadRequestException`；**同期次可重复新增** —— 数据库为普通索引（非唯一），重复期次照常落库为新的一条记录。
- 两个接口**仅管理端可调**（§4.2），公司端调用直接报业务错误（§4.3）。

### 6.6 Goldie 差距分析（E，PRD §3.6）

> 详细字段级契约、状态机、reconcile 九步流程唯一权威见设计稿 [`2026-09-24-erl-gap-analysis-task-model-design.md`](../../superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md)（下称设计稿）§5 / §6 / §7，本节只记结论。

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 17 | `GET /erl/gapAnalysis` | E1 + E2 读取；管理端读会异步投一次对账（60s 冷却），公司端读无写副作用 | `companyId`、`period`（缺省为 closed month 所在季度） | 期次级 `shared` / `shareable`（仅管理端） / `analysisServiceUnavailable`；维度级见下 |
| 18 | `POST /erl/gapAnalysis/generate` | 手动重新生成（仅管理端，同步，D10） | `companyId`、`period` | 内部触发 `reconcile(force=true)` 后返回同 17 |
| **27** | **`POST /erl/gapAnalysis/share`** | **把最新记录分享给 Founder 端（仅管理端）** | `companyId`、`period` | `{ shared, sharedAt, sharedBy }` |

**接口 17 出参**：

- 期次级：`shared`（两端同义 = 最新记录 `.shared`）、`shareable`（仅管理端，判定条件见设计稿 §7.4，与本节接口 27 的门槛表同源）、`analysisServiceUnavailable`（= 向 Python 批量取条目失败；没有条目可取时恒 `false`）。
- 维度级字段：`dimensionCode / dimensionAbbr / bothSubmitted / analyzed / hasGap / dimensionStale(恒 false，字段保留供前端兼容) / questionSetMismatch / mismatchSide / narrative / gaps[{title}] / actions[{title}]`。
- 管理端遍历**当前 Active 维度**、读最新记录里各维的任务；公司端**最新记录已分享时只遍历该记录里 `status = SUCCESS` 的任务**（消掉"分享后新增维度"的假阴性），**最新记录未分享（或没有记录）时**退回 Active 维度骨架渲染空态。
- 管理端每次读接口异步投一次对账（`reconcile(force=false)`），Redis 冷却键 60s；公司端读**绝不产生写副作用**。

**接口 18**：同步（D10）；请求线程直接调 `reconcile(force=true)`，返回接口 17 同形结果。**没有任何维度两端都交了** ⇒ 400 `"At least one dimension must be submitted by both sides before generating."`；两端都交了的维度**全部**题库 mismatch ⇒ 不报错，记 INFO 后原样返回；其余情况 `force=true` 重跑**全部可分析维度**；派发（HTTP 调 Python）失败 ⇒ 500 `"Gap analysis failed. Please try again."`（文案以 `ErlGapAnalysisServiceImpl#generate` 实测为准）。

**接口 27**：请求体不带 analysisId；出参 `{ shared, sharedAt, sharedBy }`。校验顺序刻意反直觉 —— **先 `SELECT … FOR UPDATE` 锁最新记录，再读 SOT / 维度配置 / mismatch**（防 TOCTOU：若先读校验依据再等锁，锁等待期间新落地的提交不会被这次校验看见）。门槛与 400 文案（逐字以 `ErlGapAnalysisServiceImpl#share` 为准）：

| 情形 | 文案 |
|---|---|
| 有 Active 维度未两端提交 | `All dimensions must be submitted by both sides before sharing.` |
| 有维度题库 mismatch | `The question bank has been updated and one side has not yet submitted the new-version questionnaire. Both sides must re-submit before sharing.` |
| 无记录 | `There is no gap analysis to share for this period.` |
| 已分享 | `This gap analysis has already been shared.` |
| 尚未分析完（有 Active 维度任务非 SUCCESS，或任务依据的 source ≠ 当前 SOT） | `Some dimensions have not been analyzed for the latest submissions yet. Please wait for the analysis to finish before sharing.` |
| 窄竞态（锁等待期间被并发新建的记录抢先） | `Content updated, please refresh.` |

**接口 1（卡片）/ 接口 2（维度详情）**：接口 1 的 `dimensions[].hasGap` / `shared` / `shareable` 全部来自 Java 任务表、**不调 Python**（与接口 17 同源）。接口 2 只按该维一个任务的 `result_task_id ?? id` 取条目（§6.2）。

**Java ↔ Python 契约**（内网直连 `cio.erl.ai-base-url`、转发调用者 Bearer token；读超时 refresh 500s / items 10s）：

```
POST /api/ai/erl/gap-analysis/refresh

入参  { companyId, period,
        tasks: [ { taskId, name, abbr, weight,
                   founderLevelScore, gsvLevelScore, perceptionGap,
                   founderTerminatedLevel, gsvTerminatedLevel,
                   questions: [ { questionText, eraBand, eraLabel, evidenceSource,
                                  founderYesNo, gsvYesNo, founderNote, gsvNote,
                                  attachments: [ { fileId, fileName } ] } ] } ] }
      —— Python 渲染 prompt 时只取其中一部分（白名单）

出参  { tasks: [ { taskId, status: "SUCCESS" | "FAILED", hasGap } ] }

POST /api/ai/erl/gap-analysis/items

入参  { taskIds: [...] }
出参  { items: [ { taskId, narrative, gaps: [ { title } ], actions: [ { title } ] } ] }
      —— 无条目的 taskId 不出现
```

- **`questions` 只含两端都作答过的题**：作答行存在且选了 Yes / No 才算答了；一端没答到的题（止步在更低的 level）题干、作答、附件都不送，这些附件也不做现场摘要。得分较高一端在更高 level 的作答不进输入；止步 level 不进 prompt，模型只看得到两端评分。
  - **由此一维只有一道分歧题**：答 No 之后同级后面的作答全部重置（§6.3），分数高那端在分数低那端止步的那一级整级都是 Yes，列表又只含两端都答过的题 ⇒ 送到模型的维度里**恰好只有一道题两端答得不一样**（分数低那端止步的那道 No）；零感知差维度不送、题库版本不一致的维度不派发（只跳过该维，§7.5 步骤 2）。⚠️ 只对「答 No 后同级后续作答重置」规则上线之后的提交成立 —— 之前提交的存量 SOT 不回收，首个 No 之后若还留有两端都答过的题，列表里可能不止一道。
- **每任务一次 LLM**（Python 侧并发 3、失败重试 2 次），`taskId` 只供落库定位、**不进 prompt**；提示词 1.0：user prompt = 概况（期次 / 维度名 / 权重 / Founder 评分 / GSV 评分，**不给止步 level**）+ 答题列表 JSON（题目字段白名单 `questionText / eraBand / founderYesNo / gsvYesNo / founderNote / gsvNote`，附件只送有摘要的 `{fileName, summary}`）；模型输出 `{gaps: [str], actions: [str], narrative}`，gaps 1–3 条、第一条固定为分歧题，Python 落库后经 `/items` 仍按 `{title}` 回给 Java。
- **解析与失败**：输出不是对象、没有 `gaps` 数组、或 `gaps` 里没有一条可用条目（空数组 / 条目全不是非空字符串）⇒ 该任务 `FAILED`（日志行 FAILED、不写条目、回 `hasGap = null`），交 Java 按 §7.5 重投，**绝不当「无差距」**；丢弃不可用条目打 WARN。送 LLM 的任务一旦 `SUCCESS`，`hasGap` 恒为 `true`；`hasGap = false` 只来自零感知差任务。
- **无期次级锁**：单派发由 Java CAS 保证，双跑由 Python 侧唯一键兜底，撞键按成功处理。

详细字段级说明、Python 落库顺序见设计稿 §6；提示词 1.0 的要点见设计稿 §6.4，完整写法规则以 `CIOaas-python/source/ai/prompts/erl/erl_gap_analysis.md` 为准。

### 6.7 附件上传与现场摘要（供 Goldie）（PRD §3.3 / §4）

> ERL 答题附件**只有题级**（§5.5），**不写入公司 Memory File / 公司知识库**，也**不预生成、不落任何库**：摘要在差距分析 `refresh` 时**现场生成、用完即弃**，**唯一消费方是 §6.6 的 Goldie 差距分析**。附件因此**不出现在** chatbot 检索、Memory 面板与知识库面板里。⚠️ **PRD §四「所有维度附件同步写入公司 Memory File」尚未回写，以本节为准**。
> - Python `erl/` 域只有两个端点：`POST /gap-analysis/refresh`、`POST /gap-analysis/items`。
> - Python 的 `factory.summarize_only_by_space` 管线保留 —— `summarize_file_inline` 现场摘要在用。

前端沿用**存量直传通道**，不新建上传接口：

```
⓪ 前端  本地校验 file.size ≤ ERL_MAX_FILE_BYTES(10MB)      ← PRD §3.3「单个最大 10MB」
① 前端  storageService.uploadFile(file, 'KNOWLEDGE_BASE')   →  fileId
                （内部 presign → S3 PUT → verify，见 §2.1）
                ⚠ 这个 'KNOWLEDGE_BASE' 是「上传通道」的业务类型（只决定 S3 目录与扩展名白名单）
② 前端  POST /erl/assessment/draft   { companyId, period, portal, dimension, ... }   ← 维度在请求体顶层（R1）
          双端一律题级     answers[].attachments[{fileId}]
③ Java  按 file_id 查 files，复核 files.length ≤ 10MB → 落 erl_answer_attachment
                （不落 file_name / file_size 快照，不信入参自报的大小）

   ⇒ 保存 / 提交之后【没有任何后续动作】：附件落表即结束，文件内容一次都不会被读。
```

**摘要在差距分析里现场生成**：

```
差距分析 refresh（§6.6）被触发
   │
   ├─ Java   入参每题照常带 attachments[{fileId, fileName}]（只送 id 与文件名）
   │
   └─ Python 分两处：
          source/erl/application/service/erl_gap_analysis_service.py  refresh()
              ← 编排：整轮开跑前调一次，已 SUCCESS 的任务不进这一步
          source/ai/agent/erl_gap_agent/gap_analysis.py  fill_attachment_summaries(tasks, company_id, period)
              ← 实现，下面 ① ~ ⑤ 与三个常量都在这里
           ① 把本次派发全部任务、全部题的 attachments 摊平，【按 fileId 跨任务去重】（同一份文件只烧一次）
           ② 并发生成，闸门 _ATTACHMENT_SUMMARY_CONCURRENCY = 3
           ③ 每份 _ATTACHMENT_SUMMARY_TIMEOUT_SECONDS = 90s 预算
              → IngestService.summarize_file_inline(file_id, title)
                   下载（经服务间内部端点取 S3 文件）→ 解析 → 摘要
                   全文都进摘要 —— ≤ 6 万字符一次调用；超过切成
                     ⌈全文 / 6 万⌉ 段、段摘要并发（每份 ≤ 6 路）+ 按原文顺序合并；
                     失败的段跳过、全部失败 = 无摘要
                   【不建 entry / 不建 space / 不写登记行 / 不落任何库】
           ④ 整个阶段 _ATTACHMENT_SUMMARY_STAGE_TIMEOUT_SECONDS = 120s 总闸
              → 墙钟上界恒为 120s，【与附件数量无关】
           ⑤ 只回填 summary；有摘要的附件以 {fileName, summary} 送进 prompt，没摘要的整条不送；用完即弃
```

- **为什么要有这三个常量**：需求方明确**不限制附件数量**，所以必须由服务端自己兜住墙钟与资源 —— 单份 90s 预算挡住个别巨大文件拖垮整轮，阶段 120s 总闸让**最坏耗时与附件数解耦**（否则 N 份附件就是 N × 90s），并发闸 3 则是**必需**而非调优：rag 的解析走 `asyncio.to_thread`，用的是**全进程共享**的默认线程池（2 vCPU 仅 6 线程），放开并发会连累 chatbot SSE 与财务提取。
- **超时算术**：对齐 **Java refresh 的读超时 500s** —— 附件摘要阶段 120s + 3 次 LLM 尝试 × 120s + 退避 2s / 4s = 486s（见 `ErlPythonClient` 注释）；Python 单测只钉单任务 LLM 部分 366s（`test_single_task_worst_case_is_bounded`）。多任务按并发 3 分批时整轮可能超过 500s，设计接受：任务留 `RUNNING`、10 分钟后同 id 重投（§7.5）。
- **降级口径**：单份**下载失败 / 类型不受支持 / 解析为空 / 超时**一律**继续分析、不阻断**（只落一条 `logger.warning`），这类附件**整条不送进 prompt**，模型看不到这份文件。
- ⚠️ **代价（需求方知情）**：① **每轮重生成都重付**一次解析 + 摘要 LLM 成本（接口 18 以 `force=true` 重跑全部可分析维度时，会重算该期次**全部**附件；超长附件每份是「段数 + 合并次数」次调用、全文都进 `ai_llm_conversation`，成本随全文长度增长）；② 哪份证据被跳过了，**全站无任何提示**，且不落库 ⇒ 同一份附件这次失败下次可能成功、屏上与库里都不留痕（已记 `CIOaas-web/docs/待优化项.md`）；③ 超长附件至少两轮 LLM（并发段摘要 + 合并），更容易触到单份 90s，到点即按无摘要继续；三个常量不调。

| # | 方法 / 路径 | 用途 |
|---|-------------|------|
| 19 | `DELETE /erl/assessment/attachment/{id}` | 草稿态删除附件（已提交则拒绝）。鉴权经「附件 → 作答 → 评估」回溯所属评估 |

- **10MB 双侧校验**：前端 `ERL_MAX_FILE_BYTES = 10 * 1024 * 1024`（**不复用 chat 的 20MB 常量**，§2.1），超限文件不发起上传并提示 `File exceeds the 10 MB limit.`；服务端在第③步**按 `files.length`** 复核，超限 `BadRequestException`；`file_id` 查不到、或 `files.length <= 0`（未 verify / legacy 未回填）同样报业务错误（§4.3）—— 前端可绕过，服务端是底线。
- **附件归属的回溯路径**：`erl_answer_attachment` 只有 `erl_assessment_answer_id` 一条外链 —— 附件 → 作答 → 评估 → 该评估自带的 `company / period / portal / dimension`。表上**没有** `assessment_id`、也**没有** `dimension`（§5.5），任何「按维度 / 按提交取附件」都先取作答再按 `erl_assessment_answer_id` 批量查，不再有第二条捷径。
- **改答导致 level 回收时，被删 level 上的附件一并删除**（§6.3）；**接口 28 `Reset` 时本次草稿的全部附件一并删除**（D8）。附件不产生 `ai_rag_entry`，删附件时**没有任何知识库侧的东西需要联动**。

### 6.8 组合层 ERL 总表（F2，PRD §3.7）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 20 | `GET /erl/portfolio` | F2 Tab | 可选 `period`（缺省为该公司 closed month 所在季度，R3；F2 不发 `period`、走服务端逐公司缺省；缺省期次全部公司一次批量取）、`portfolioId`、`sortBy`、`sortOrder`、`stage`、`minScore`、`maxScore`（这五个排序筛选入参保留，但 F2 恒不下发 —— 界面无排序与筛选）、`dimension` | `dimensionColumns[{ code, abbr, sortOrder }]`、`companies[{ companyId, name, overallScore, dimensionScores[{ code, abbr, score }], stage, era, period, detailUrl }]` |

- **`detailUrl`**：`View` 列的跳转目标 —— 指向 **A4 全维 Score Details 页**。后端下发 `/exitReadiness/scoreDetails?companyId={id}&period={period}`，**不带维度参数**；带该行取数所用期次；无评估的公司仍下发（进页面看空态）。
- 只返回当前登录用户**有权访问的公司集**（§4.3）。
- **维度列动态化（D1）**：`dimensionScores[{ code, abbr, score }]`；表格列头取根节点 `dimensionColumns[]`（按 `sort_order`），前端**不得**依赖静态 `DIMENSIONS` 映射渲染列。⚠️ 跨组织同屏时各公司的维度集合可能不同 —— `dimensionColumns[]` 取**当前登录用户所属组织当前 `status = 'Active'` 的维度集合**的维度作为列集合，某公司缺该维度时 `score = null`，前端显示 `—`。
- 不传 `period` 时按**该公司 closed month 所在季度**取该期次各维度的 GSV **最新一条 `SUBMITTED`**（按 `submitted_at DESC, id DESC`），**该季度无提交即整行空态（`overallScore = null`，各维 `—`），不回退到更早期次**；closed month 取不到回退当前自然季度（§7.1.2）。无评估的公司仍列出。
- 各维度列的值是 **level 分（0–9 整数）**；`overallScore` 是**该公司当前 `status = 'Active'` 维度集合上的加权和**（§7.1）—— `Σ(各维度分 × 该维权重)`，该期次未提交的维度按 `0` 计入、其余维度的权重**不做归一化**，结果两位小数（F2 与 A1 同样显示两位小数）。⚠️ **跨组织同屏时维度集合可能不同** —— F2 只列当前用户有权访问的公司，正常场景同属一个组织；若出现跨组织，综合分**各按各自组织的维度集合与权重算**，不做任何跨公司归一化，那会改变每家公司自己的分数。
- **排序与筛选在服务端做**（依据为本设计，D15）：`sortBy` 白名单**动态化**为 `{name, overallScore, stage} ∪ {当前 Active 维度的 code}`，非白名单值 `BadRequestException`；筛选支持 Stage 精确值与分数区间。⚠️ 白名单与请求值一律用 **`dimensionCode`**，而 F2 列头显示的是 **`dimensionAbbr`**（`code` 为 `{前缀}{随机}`，与 abbr 不同）—— 点列头排序必须取 `dimensionColumns[].dimensionCode`，**不得用列头文案**，否则稳定报业务错误（§4.3）。F2 界面上无筛选控件与列头排序器，`sortBy` / `sortOrder` / `stage` / `minScore` / `maxScore` 由 F2 恒不下发；服务端白名单校验照旧，供其它调用方用。
- **必须批量聚合**：一次查出全部公司的答案并在内存归组，禁止按公司循环查询（N+1）。每家每期次有 N 行 `erl_assessment`（每维一行），聚合时按 `(company_id, dimension)` 归组后按 `submitted_at DESC, id DESC` 取首条，仍是一次查询。

---

## 7. 计算口径与状态流转

### 7.1 分数（PRD §3.1 / §3.3 / §3.5）

| 口径 | 规则 | 依据 |
|------|------|:---:|
| 单题 | 只有 **Yes / No** 两个取值，**本身不折算成分数** | PRD §3.3 / §3.4 |
| **维度分（Founder / GSV 同口径）** | **该维度最后一个「整级全部 Yes」通关的 level**，取值 **0–9 整数**：<br>· 某 level 内**出现任一 No** → 维度分 = **踩 No 那一级在该维有题 level 升序列表里的前一个 level**（题库只配 level 1/2/7/9 时：L9 内有 No → **`7`**，L7 内有 No → **`2`**）<br>· 该维**第一个有题 level** 内即出现 No（= 一级都没通关） → **`0`**<br>· **全部有题 level 均为 Yes → 该维最大有题 level**（题库配满九级时即 `9`；**不是固定 9**，§7.2-①）<br>· 该维在该题集版本内 **0 题** → `null`（不按 0 计）<br>⚠️ **取值离散**：维度分**只可能落在「该维配置过的 level」或 `0`** 上（只配 1/2/7/9 ⇒ 只会是 0 / 1 / 2 / 7 / 9），**综合分水位随配置稀疏度下移**<br>⚠️ **不追溯**：`erl_assessment.level_score` 是提交时冻结的快照，计分口径变化只影响此后的提交；按旧口径（「No 的 level 减一」）提交的稀疏维度存量继续带旧分（偏高），是否回刷另行裁决 | PRD §3.1 / §3.3（「No 的 level 减一」已被本口径取代，见 §7.2） |
| **综合分** | **Σ(各维度分 × 该维权重)**，**保留 2 位小数（HALF_UP）**，以 `X/9` 展示（A1 与 F2 均显示两位小数）。权重取 `erl_dimension_config` 中该组织 `Active` 行的当前 `weight`（百分比数值，合计 100）。<br>**这是加权和，不是平均 —— 没有「分母 = 维度个数」这回事**：权重本身合计 100%，Σ 出来就已经落在 0–9 的量纲上。需求方算例：FRL 2 分（20%）、PRL 4 分（20%）、其余维度未填 ⇒ `2×0.2 + 4×0.2 = 1.20`，A1 与 F2 均显示 `1.20`。<br>**未填写的维度按 `0` 计入，其余维度的权重不做归一化** —— 上例里已填的两维权重合计只有 40%，分数就只能顶到 40% 的天花板。没做的评估就是没分，会把综合分拉低。<br>**维度集合**：取当前 **`status = 'Active'`** 的维度集合（`Inactive` 行不参与、权重也不计入），**个数不固定、不假设五维**。维度停用后，它在历史期次的已提交分数随之退出计算。<br>**百分比换算的除数取「权重表里全部维度的权重合计」而不是写死的 `100`** —— 正常配置下两者等价，但 §9 的等权降级是 `100 ÷ 维度数` 保留 4 位小数（3 维时合计 `99.9999`），写死 100 会让降级路径上的满分算成 `8.9999`。<br>**唯一的空态**：该公司该期次**一维都没填** ⇒ 综合分 `null`（前端灰底 `—`），**不按 `0.00` 算**。⚠️ 这条必须留着 —— 否则「零提交」与「填了、level 1 就没过」的合法 `0` 分在界面上分不出来（见本节末段 `0` vs `null`） | PRD §3.1 / §3.8 |
| Perception Gap | `Founder 维度分 − GSV 维度分`（两个整数相减，结果为整数）；`> 0`（创始人高于 GSV，可能是盲区）显示 `Negative`，`< 0`（公司实际比创始人自认的好）显示 `Positive`（标签由后端 `gapDirection` 下发）；取绝对值展示。**仅管理端展示** | PRD §3.5；可见性见 §4.2 |
| Era / Stage | 见 §7.3（含 `score = 0` 的取值） | — |

**计算示例**（供实现自测）：

```
某维度题库（level : 题数）  1:3  2:4  3:2  4:5  5:3 ...
作答          level 1 → Yes Yes Yes          → 全 Yes，解锁 level 2
              level 2 → Yes Yes Yes Yes      → 全 Yes，解锁 level 3
              level 3 → Yes No               → 出现 No，终止
维度分        = 最后一个整级通关的 level = 2   （terminated_level = 3, level_score = 2）
已答题数      = 3 + 4 + 2 = 9        （level 3 答到第一道 No 即终止，此例恰好 2 题都已作答；No 之后的题不要求作答）
level 4/5 的题 从未解锁 → 不下发、不落答案行

综合分（= Σ(维度分 × 权重)，未填按 0、不归一化；①②④⑤ 设该组织配了
        5 个维度 FRL / PRL / BERL / RRL / TRL，权重各 20%）
        // 服务端两位小数，A1 与 F2 均显示两位小数

① **只填了 2 维**（需求方算例）：FRL = 2、PRL = 4，其余三维未填
              = 2×0.2 + 4×0.2 + 0 + 0 + 0 = 1.20 → 展示 1.20/9.00（Stage 1 · Founder Era）
                ⚠️ 不是 (2+4)/2 = 3.0 —— 未填的三维不从权重里剔除，天花板只有 40%

② 五维全填，维度分 2 / 5 / 7 / 4 / 1（等权 20%）
              = (2+5+7+4+1) × 0.2 = 3.80 → 展示 3.80/9.00（Founder Era）

③ 同一份分数、权重改为 50 / 20 / 10 / 10 / 10
              = 2×0.5 + 5×0.2 + 7×0.1 + 4×0.1 + 1×0.1 = 3.20 → 展示 3.20/9.00
                （权重一改，同一份历史数据的综合分与 Stage 立刻跟着变，接受漂移，§7.10-W1）

④ 只填 1 维且得 0 分：= 0×0.2 = 0.00 → 展示 0.00/9.00，红底 + Era 显示 `—`
⑤ 一维都没填：= null（**不是 0.00**）→ 灰底 `—`，Stage / Era 一并空
```

> **示例只是示例，维度数不固定**：上式取五维仅因原型如此，**实现不得写死 5**。
> 真正的算法是「遍历当前 `status = 'Active'` 的全部维度，Σ(维度分，未填按 0) × 该维权重，再除以权重合计」——
> 维度个数、代码、权重、排序全部来自 `erl_dimension_config`（`organization_id` + `status='Active'`，按 `sort_order`），
> 而**不是**编译期枚举或前端静态映射。
> **唯一实现**：`ErlScoreCalculator#overallWeighted(levelScores, weights)`（Java），权重一律经 `ErlDimensionConfigService#weightsOf` 取（脏数据在那里已等权降级，§9）；前端不自算综合分 —— 权重表由后端按被查看公司所属组织现取。

**展示口径**：

- **管理端**：ERL Card 上**并列展示 Founder 分与 GSV 分 + Perception Gap**（维度详情页不展示分数，§8.5）；雷达图四条序列。
- **公司端**：**只展示 Founder 侧**的维度分 / 综合分 / Stage（PRD §3.5「创始人只能查看自己的分数」）；**不展示** GSV 分、Perception Gap、雷达图、基准（§4.2 / §4.3）。
- 两端的维度分**同口径**（都是 level 分），Perception Gap 是两个同口径整数之差，可解释性无问题。
- 任一侧未提交时的降级见 §9。

> **`0` 是合法分数（必读）**：**`0` 表示「level 1 就没通过」，`null` 表示「该维无题」**，两者语义不同、展示不同（`0/9` vs `—`）。全链路的空值判断**不得用 `!score` 这类真值判断**（会把 0 当成缺数据），必须显式判 `null` —— 这是最容易踩的坑，代码审查专项检查。

### 7.1.1 已解锁范围 ≠ 全部题（易错点）

逐级解锁下，**一次评估只会作答「已解锁 level」的题**，后续 level 的题从未出现在用户面前。下表三个数在计分、页头文案、Goldie 输入组装里必须分清：

| 概念 | 口径 | 举例（某维度 5 个 level，题数 3/4/2/5/3 = 17 题；止步 level 3） |
|------|------|------|
| **`answeredCount`（已答）** | 已解锁 level 内已作答的题数（= 答案行数） | `3 + 4 + 2 = 9` |
| **`totalCount`（题数）** | 该题集版本该维**全部**题数 | `17` |
| **维度分** | 最后一个**整级通关**的 level | `2`（止于 level 3，上一个整级通关的是 level 2） |

- **`answeredCount == totalCount` 不是提交条件** —— 只有该维全通关（全部有题 level 全 Yes）才会相等。提交条件为「**本维度到达终止态**」（§6.3 前置校验 2 / §7.2-③）。
- 题数 / 已答数由接口 2 `header` 与接口 3 下发（接口 7 / 8 不带）。
- **维度页页头的「17 questions」是题数，不是已答数**（页头不展示已答数，§8.4）。
- **`null` 与 `0` 的区分见 §7.1 末尾的加粗提醒** —— 该维 0 题 → 维度分 `null`、在综合分里按 `0` 计（权重不剔除）；level 1 有 No → 维度分 `0`、照常进综合分。

### 7.1.2 展示期次的确定（`period` 缺省口径）

所有「`period` 可选」的读接口，调用方不传 `period` 时按下表确定渲染期次：

| 项 | 取值 |
|------|------|
| **缺省期次** | **该公司 closed month 所在的季度** |
| **closed month 从哪来** | **读 FI 每日 KPI 快照 `company_quickbooks_data.last_updated`** —— 与 portfolio General 页的 Last Financial Month 同一个值；定时任务 `SaveCompanyQuickbooksDataEveryday` 每天 02:00 UTC 按 Manual / Automatic 口径从 actuals 算出，新录入的 actuals **次日**生效；按公司取最新写入的一行、不分币种；FI `ColleagueCompanyService#findLastFinancialMonths` 一次 `IN` 查询。**ERL 复用 FI 既有服务，自己不算、不复制一份规则**（§3 架构） |
| **季度换算** | closed month → 所属自然季度，形如 `2026Q2`（`2026-04` ~ `2026-06` → `2026Q2`） |
| **该季度两端均无提交** | **空态**（§9 的空态文案），**明确不回退到更早期次** |
| **closed month 取不到**（还没有快照 / 最新快照无月份 / FI 侧抛异常 / 月份格式坏） | **回退当前自然季度**（`YYYYQn`，**按 UTC 算** —— 即 `ErlPeriodService.currentPeriod()`）；FI 侧抛异常、月份格式坏打 WARN（`companyId` + 原因），还没有快照 / 快照无月份只打 DEBUG。⚠️ **例外**：`companyId` 为空时仍返回 `null`（连公司都没有，给季度只是凭空造上下文；五个调用方都先经 `ErlAccessService#resolveCompanyId`，拿不到即抛，该分支只是防御） |
| **显式传 `period`** | 一律以入参为准，本节缺省逻辑不介入 |

- **⚠️ 不做期次回退**：宁可空态，也不能让用户在没有标注的情况下把上一季的分数当成本季的分数。
- **⚠️ 两步别混为一谈**：**①「期次定不下来」** —— closed month 取不到，**回退当前自然季度**；**②「期次定下来但该季没数据」** —— **空态、绝不取更早期次反填**，上一条的禁令只管 ②。
- **影响接口**：**接口 1**（ERL Card / overview）、**接口 17**（差距分析）、**接口 20**（F2 组合层总表，前端不发 `period`）、**接口 22**（A4 全维 Score Details）、**接口 6**（出参 `currentPeriod`：ERL 域的「当前季度」就是本节的缺省期次，填报页网址没带期次时默认打开它），
  以及其余任何 `period` 可选的读接口 —— 缺省口径统一走本节，**不得各接口各写一套**（收在 `ErlPeriodService#resolveDefaultPeriod`（批量 `resolveDefaultPeriods`）里）。
- **这是 ERL 域对 FI 域的跨域依赖**：ERL 读侧依赖 FI 的 closed month 服务（读每日 KPI 快照的批量方法 `findLastFinancialMonths`）。
  依赖方向为**单向只读**（ERL → FI），不反向、不写 FI 数据；FI 侧不可用时按「closed month 取不到」处理（回退当前自然季度 + WARN），**不阻断整页**。
- **维度配置的取用与本节一致**：先定期次（期次只决定取哪批评估数据）；**维度集合与期次无关，一律读当前 `status = 'Active'` 的配置**；期次都定不下来时不渲染任何维度。

### 7.2 逐级解锁计分模型（PRD §3.3）

PRD §3.3 原文：

> 全部问题包含 Era 和 level，为 **Yes/No + 固定顺序必答**模式（在 ERL configuration 中配置的顺序）；五个维度的所有问题按照 Era 和等级依次显示。
> 例如用户回答完了 Founder Era-1 的问题，且答案全部为 yes，**该 level 折叠并显示 Check**，再显示下一 level 的问题，**直到有 No 回答（或全部答完），就不再显示下一 Level，激活提交按钮**，分数就是此回答为 No 的 Level 减一；**若 9 个层级都是 yes 回答，则最终得分为 9**。

> ⚠️ **上文「分数就是此回答为 No 的 Level 减一」已被取代**：维度分取「**最后一个整级全部 Yes 通关的 level**」，稀疏题库下与「No 的 Level 减一」不等（§7.1 / §7.2-① 口径 1）。PRD 原文照录于此；「若 9 个层级都是 yes 回答，则最终得分为 9」那半句**仍然成立**（全通关 = 该维最大有题 level）。

**① 状态机（一次提交就是一个维度，状态机与评估记录一一对应）**

> 提交单元是「某公司某期次某端的**单个维度**」：`level_score` / `terminated_level` / `unlocked_level` 三列在 `erl_assessment` 上（§5.2），
> 一条评估记录 = 一个维度 = 一份状态机。逐级解锁**按维度独立**。

> ⚠️ **level 分布是稀疏的，不得假设 1..9 连续**：如原型中 PRL 维度只用 level **3 / 6 / 9**（首个可作答的是 L3），RRL 只到 L8。因此状态机遍历的是**该维度实际存在的 level 升序列表**，而不是 1→9 的计数器；否则 PRL 会卡在「L1 无题、既非全 Yes 也非含 No」的死锁上。

```
levels = 该维度在该评估绑定版本内 distinct(era_band) 升序     // 如 PRL → [3, 6, 9]

for L in levels:
    qs = level L 的全部题（按 sort_order）
    │
    ├── qs 中出现第一道 No ──► level L = BLOCKED              // 扫到即终止，不等本级答满
    │                            维度终止：level_score = 上一个已 CLEARED 的 level（一级都没通关则 0），terminated_level = L
    │                                      // 不是 L − 1 —— 稀疏 levels 下两者不等，如 [1,2,7,9] 在 L7 踩 No ⇒ 2
    │                            unlocked_level = L，后续 level 全部 LOCKED，跳出
    │                            该 No 之后的题不再要求作答（不计入 unansweredCount）；
    │                            它之前漏答的题仍计入 ⇒ canSubmit 仍为 false
    │                            ⚠ 「首个 No 之前的第一道漏答题」正是提交时自动补 No 的落点
    │                            （scorer 顺带出参 firstUnansweredQuestionId，§6.3 接口 5 的 autoAnswerNo）
    │
    ├── 到此全为 Yes、但仍有题未作答 ──► level L = ACTIVE
    │                            维度未终止：level_score = null，unlocked_level = L
    │                            后续 level 全部 LOCKED，跳出
    │
    └── qs 全部已答且全为 Yes ──► level L = CLEARED（前端折叠 + 打勾）
                                   继续下一个 L

循环自然走完（所有存在的 level 全 CLEARED）：
    维度终止：level_score = max(levels)     ← **不是固定 9**
              terminated_level = null
              unlocked_level = max(levels)

levels 为空（该维 0 题）：
    level_score = null，terminated_level = null，unlocked_level = 1
    **视为已终止，但不可提交**（§6.3 校验 3）
```

**三条反直觉但必须照做的口径**（实现与代码审查专项检查）：

1. **得分 = 最后一个「整级全部 Yes」通关的 level，与踩 No 那一级的编号无关**。取**踩 No 那一级在 `levels` 升序列表里的前一个**；一级都没通关即 **`0`**（即 `ErlLevelScorer` 内部的 `clearedLevel` 局部变量）。PRL 只配了 level 3 / 6 / 9：在 L3（它的首个有题 level）答 No → **得 `0` 分**；在 L6 答 No → **得 `3` 分**（不是 5）。⚠️ **level 连续时与 PRD 原文「No 的 level 减一」同值** —— 本文档中 level 1/2/3 的连续举例因此不受影响。
2. **「全通关」= 该维度最大的有题 level，不是无条件 9 分。** RRL 只到 L8，全 Yes → **8 分**。PRD 的「若 9 个层级都是 yes 回答，则最终得分为 9」是**题库配满九级时的特例**。
3. **`unlocked_level` 存实际 level 值，不是序号。** PRL 停在 L6 存 `6`（不是「第 2 组」的 2）。前端据此与 `levels[].eraBand` 对齐。

- **「level 内出现 No」即终止，不要求答完该 level 的其余题**：按 `sort_order` 扫到**第一道 No** 就终止，该 No 之后的题（本级剩下的 + 其后所有 level）一律不必作答，填报页把它们**禁用**；答 No 的那一刻就把它们清空（作答、备注、附件），落盘时服务端一并删除。禁用同时是**逐题解锁**：第一道未作答的题之后同样禁用。Goldie 拿到的就是「答到第一个 No 为止」的那批答案。
  ⚠️ **那道 No 自己及它之前的题仍可改**（点错 No 必须能改回 Yes）—— 禁用的粒度是**题**，不是整级。改回 Yes 后其后的题重新可答（被清空的不恢复，从下一题起重新往下答），**终止随之解除**：`canSubmit` 落回 `false`、Submit 变回不可提交（前端为此把「No→Yes」也列为立即落盘的时机）。
- **解锁与终止判定只在服务端做**（`ErlLevelScorer`），前端消费接口 3 / 4（草稿期为接口 29）返回的 `levels[].state` 与 `unlockedLevel`，**不自行推断**（§6.3）。草稿期由接口 29 **只算不存**地推进（同一份 `ErlLevelScorer`，只是不写库）；落盘（接口 4）与提交（接口 5）时服务端仍会按传入答案**重算一遍**。
- **改答的回收规则**见 §6.3：删除**首个 No 之后**的全部答案与附件 —— 解锁位置之后所有 level 的，加上同级排在那道 No 后面的；**只按首个 No 截、不按首个漏答截**。

**② 唯一实现，不做策略抽象**

- 计分逻辑收在 **`application/scoring/ErlLevelScorer`** 一个类里：`computeDimension(orderedQuestions, answers)` → `{levelScore, terminatedLevel, unlockedLevel}`；综合分直接调 `ErlScoreCalculator.overallWeighted(levelScores, weights)`。
  - `overallWeighted` 的 `weights` 入参**由调用方取自 `erl_dimension_config` 当前 `Active` 行**，`ErlLevelScorer` 本身不查库；`levelScores` 是**变长**集合，方法内不得假设 5 项。
- **不建**策略接口 / 策略工厂 / 计分模式枚举与列：PRD 已把格式定档，为单一实现留一层策略工厂属违反根 `CLAUDE.md` 的 YAGNI。
- 五处消费者（填报解锁、提交校验、展示计分、组合层、Goldie 输入组装）**一律调该类**，不得内联 level 判定。

**③ 前端渲染**

- 题目顺序**恒按后端返回的 `levels[]` 与 `questions[]` 顺序**，前端不重排、不合并 level。级内顺序 = `sortOrder` 升序、`id` 破平，与 `ErlLevelScorer` 同一个比较器。
- `CLEARED` 折叠 + 打勾、`ACTIVE` 展开、`BLOCKED` 展开且标注止步（首个 No 之后的题禁用，那道 No 及它之前的仍可改；另有逐题解锁 —— 第一道未作答的题之后同样禁用）、`LOCKED` 只显示占位行（`Level n · locked`）或整段不渲染（§8.4）。
- 提交按钮绑接口 3 / 4 返回的 `canSubmit`，不自行判断（§6.3）。
  - **`canSubmit` 的判定口径**：**只看本次填报的这一个维度是否终止** —— 本维 BLOCKED 或全 CLEARED、且已解锁题全部作答（首个 No **之后**的题不算在「已解锁题」里），即 `canSubmit = true`；**该维 0 题时恒为 `false`**；不看期次（未来季度同样可提交），
    **与其他维度填没填、填到哪一级完全无关**。

### 7.3 Era / Stage 分段规则

以 **1–3 / 4–6 / 7–9** 分段为准。精确边界（综合分 2 位小数，Era / Stage 按两位小数的值判定；需明确开闭区间）：

| 分数区间 | Era | Stage |
|----------|-----|-------|
| **`score == 0`** | **`—`（未达 Stage 1）** | **`0`** |
| `0 < score < 4.0` | **Founder Era** | 1–3 |
| `4.0 ≤ score < 7.0` | **Harvest & Growth** | 4–6 |
| `7.0 ≤ score ≤ 9.0` | **Exit Era** | 7–9 |

**`score == 0` 的取值**：维度分 `0` 表示「level 1 内就有 No」，即连 Stage 1 的准入准则都未达成 ⇒ **Stage `0`、Era 显示 `—`**，前端渲染为灰色 `—` 徽章（文案与「无数据」相同，`0` 与 `null` 只靠分数格 `0/9` vs `—` 及形态区分，「显式判 `null`」因此更不能省）。**不归入 Founder Era** —— Founder Era 的定义是 Stage 1–3，`0` 不在其中。加权综合分为 `0.00` 时同理。

**Stage 整数值**：`stage = clamp(round(score), 1, 9)`，但 **`score == 0` 时 `stage = 0`**（不 clamp 到 1）。PRD §3.5「当前 Stage（1–9）由综合分数与 Workbook 中的 Era 边界推导」未给出取整规则 → 取整方式待产品确认，见 §13-Q3。Era 判定**只按上表区间**，不经由 Stage 二次转换，避免 6.5 → round 7 → Exit Era 的错判。

> **维度分是整数，综合分是小数**：维度分为 0–9 整数，落在上表时区间判定无边界歧义；**只有加权综合分**会出现 3.9 / 4.0 / 6.9 / 7.0 这类边界值，上表的开闭区间因此仍然必要。

> 题目的 `era_band`（1–9 整数档位）到 Era 的映射：band 1–3 → Founder Era、4–6 → Harvest & Growth、7–9 → Exit Era，整数无边界歧义。

### 7.5 差距分析的生成、刷新与分享

> 详细九步伪代码、状态机、并发论证唯一权威见设计稿 [`2026-09-24-erl-gap-analysis-task-model-design.md`](../../superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md)（下称设计稿）§2 / §4 / §5 / §8，本节只记结论。

**术语与门槛**（照抄设计稿 §2）：

- **SOT**：某公司某期次某端某维度最新一次 `SUBMITTED` 的评估（`submitted_at DESC, id DESC`）。
- **可分析维度**：两端都有 SOT 且不处于题库版本 mismatch。**它就是生成门槛**：`reconcile` 只为可分析维度建 / 补 / 重建与派发任务（设计稿 D17）。
- **报告就绪（ready）**：每个 Active 维度都是可分析维度。**只用于 Share 门槛**（PRD:193 字面约束的就是 share 按钮）。
- **零感知差维度**：两端 `levelScore` 相等，不送 LLM，建任务时直接判无差距。
- 两端已交且可分析的维度即建任务，屏上 `Analyzing…` 就是真在跑；一个可分析维度都没有才不建任何行；题库版本不一致的维度只跳过该维。

**结论先行：没有定时任务、没有扫描器。** 三个触发点共用一个 `reconcile(companyId, period, callerUserId, force)`：

| 触发点 | 调用方式 | 说明 |
|---|---|---|
| ① 评估提交 | 事务提交后 `AfterCommitExecutor` → `@Async("ioExecutor")`，`force=false` | Bearer token 与 userId 在请求线程内捕获后作为参数传入 |
| ② 管理端读接口 17 | 异步投一次 `reconcile(force=false)`，Redis 冷却键 `erl:gapAnalysis:cooldown:{companyId}:{period}`（TTL 60s） | 兜住存量已交齐期次的首次生成、提交后异步对账丢失、FAILED / 超龄 RUNNING 重投；公司端读**绝不产生写副作用** |
| ③ 接口 18 手动 Generate | 请求线程**同步**调 `reconcile(force=true)` | D10；没有任何维度两端都交了 ⇒ 400（同 §6.6）；force 重跑全部可分析维度 |

**`reconcile` 九步**（规划锁 `erl:gapAnalysis:plan:{companyId}:{period}`，SETNX 60s；规划是一个 `REQUIRED` 事务，派发在锁外与事务外）：

```
1  加规划锁；抢不到直接返回，下次读再来
2  Active 维度、每维两端 SOT、mismatch 集合 → A = 可分析维度集合；A 为空 ⇒ 释放锁返回（不建、不改任何行）
3  R = 最新记录；A 中每维目标 source = (F_sot.id, G_sot.id)，zero = noPerceptionGap(F, G)
4  R 不存在 ⇒ 建 R + A 中各维任务：zero ⇒ SUCCESS/has_gap=false；否则 PENDING
5  R 已分享 ⇒ changed = A 中 R 内没有该维活任务、source 不同、或 R 内该维活任务非 SUCCESS 的维度（force ⇒ A 全部）
     changed 为空 ⇒ 不建新记录；否则建 R'（只含 A 中各维）：changed 维建新任务，未变维原任务 SUCCESS ⇒ 复制
     （result_task_id = 原.result_task_id ?? 原.id），原任务非 SUCCESS ⇒ 不复制、建新 PENDING
6  R 未分享 ⇒ A 中：R 内没有该维活任务 ⇒ 直接补建；source 变了（force ⇒ A 全部）⇒ 旧活任务软删，同 R 下建新任务；不在 A 里的维度旧任务原样留着
7  待派发 = 最新记录下属于 A 的活任务里 status ∈ {PENDING, FAILED} ∪ {RUNNING 且超龄} 的，逐个 CAS → RUNNING
8  释放锁
9  待派发非空 ⇒ 组包一次调 Python refresh ⇒ 按响应逐任务 CAS 落 status + has_gap
```

规划锁 fail-open（Redis 不可用）时，由部分唯一索引 `uk_erl_gap_analysis_report_unshared`（同期次并发首建 / 分叉）与 `uk_erl_gap_analysis_dimension_task`（同记录同维度）兜底，后到的事务撞键回滚，不会建出重复报告或重复任务。

**任务状态机与自愈**（设计稿 §4）：

```
PENDING ──(派发前 CAS)──► RUNNING ──(Python 回 SUCCESS，CAS)──► SUCCESS
                             │
                             └──(Python 回 FAILED，CAS)───────► FAILED
自愈（管理端读接口，60s 冷却）：FAILED、或 RUNNING 且超 10 分钟 ⇒ CAS → RUNNING，同一 task id 重新派发
```

- 所有状态更新都是条件 `UPDATE … WHERE id = ? AND status = ? AND deleted = false`，rowcount = 0 记 INFO 忽略（迟到结果、已软删任务自然落空）。
- HTTP 传输失败 / 读超时**不**置 FAILED，留 RUNNING 交给 10 分钟规则 —— Python 可能仍在跑，立刻重投会双跑。
- 零感知差任务建行即 `SUCCESS + has_gap=false`，不经过 PENDING。
- **不加扫描器**：判断只发生在读、写两个时刻（提交后异步对账、管理端读接口对账、手动 Generate）。
- 超龄 RUNNING 的重投是 `RUNNING → RUNNING` 的等值 CAS、不是互斥锁；真正的串行化靠规划锁，锁 fail-open 时才可能双派发，由 Python 侧同 id 的日志行 / 条目唯一键收口（撞键按先到者的终态处理）。

**读路径**：选行只在一处 `visibleReport` —— **两端都取 `latestReport`，公司端仅当它 `shared = true` 时可见、否则空态**。条目按 `result_task_id ?? id` 一次批量取，只取 `status = SUCCESS ∧ has_gap = true` 的任务；取失败 ⇒ `analysisServiceUnavailable = true`（前端走失败态 + Retry，而不是「正在分析」）。

**Share**：门槛与流程见 §6.6。已分享记录及其任务不可变（I1）；后续任一端再提交，`reconcile` 新建记录并复制未变维度（`result_task_id` 链，若复制源本身非 SUCCESS 则视为变更、不复制、重新建 PENDING 任务重跑）。记录的 `shared` 不复位，但公司端以最新记录为准 —— 分享后再提交、新建出未分享记录，创始人即回到空态，直到管理端再次 Share。

**并发、幂等、自愈汇总**（照抄设计稿 §8）：

| 场景 | 处理 |
|---|---|
| 同期次两次 `reconcile` 并发 | 规划锁 60s；抢不到直接返回，下次读再来。锁 fail-open 时由两个部分唯一索引兜底，后到事务回滚 |
| 双端交错提交各读到对方旧 SOT | 建出依据旧一方 SOT 的任务；下次管理端读 ⇒ source ≠ SOT ⇒ 未分享则软删重建 / 已分享则新记录 |
| Java 500s 超时、Python 仍在跑 | 任务留 RUNNING；10 分钟后重投 ⇒ Python 命中 SUCCESS 日志直接回，不重复烧 LLM |
| Python 崩溃 | 日志行无 / FAILED ⇒ 10 分钟后重投 |
| Java 发版重启、派发线程被杀 | 同上 |
| 迟到响应撞已软删 / 已终态任务 | CAS rowcount 0，忽略 |
| 同一 task 被双跑 | 日志行 / 条目撞唯一键 ⇒ 先到者 SUCCESS ⇒ 按它的 has_gap 返回；先到者 FAILED ⇒ 重试写入一次覆盖为 SUCCESS；查不到行 ⇒ 记 FAILED |
| 已分享记录后又提交 | 新记录（未分享，I1）；公司端空态，直到再次 Share |
| 已分享后又有新维度交齐 | 新记录（未分享，I1）：复制可分析维度里未变且 SUCCESS 的任务、为新交齐的维度建新任务；公司端空态，直到再次 Share |

### 7.7 评估状态流转

> **状态流转的作用域**：下图的每一条流转线都发生在 **`(company_id, period, portal, dimension_code)` 这一个四元组内部**。
> **一次提交就是一个维度**，唯一草稿约束按四元组分组；维度之间**互不影响**：FRL 已提交过 3 次、PRL 还停在草稿、TRL 一次没填，都是合法且常见的状态组合。

```
作用域 = (company_id, period, portal, dimension_code)   ← 每个维度一条独立的流转线
最新一次提交（SOT）= 同四元组内 status='SUBMITTED' 且 ORDER BY submitted_at DESC, id DESC 的第一条

                    (首次打开该维问卷)      (Save as draft / Submit)          (提交该维)
无记录          ────────────► DRAFT ──────────────────────► DRAFT ──────────────► SUBMITTED
                                 ▲   │                                              │ 只写 submitted_at
                                 │   │ 丢弃草稿 / Reset（接口 28）                   │
                                 │   └──────────► 无记录（DRAFT 行连同答案、附件删除，
                                 │                        unlocked_level 概念回到 1）
                                 └──── 提交后不可回退；该维再填 = 新建一条记录 ────┘
```

- `GET /erl/assessment`（带 `dimension`）命中无草稿时**不建记录**，返回**只有该维首个可作答 level 解锁**的题目结构（其余 level 为 `LOCKED`、题面不下发，§6.3）；首次 `POST draft` 才落 `DRAFT` 行。`level_score` / `terminated_level` / `unlocked_level` 三列**直接落在 `erl_assessment` 这一行上**（§5.2），首次落草稿时 `unlocked_level` 初始化为该维首个有题 level。
- **草稿的唯一性与共享语义**：
  - **同公司 + 同期次 + 同端 + 同维度只有一份草稿**（`uk_erl_assessment_draft` 部分唯一索引，§5.2）。
  - **草稿是公司共享的、不区分账户**（唯一索引里没有用户维度，模型上天然如此，但产品语义必须写明）：**A 保存后 B 打开看到的就是 A 的内容，B 的保存直接覆盖 A 的** —— 后保存覆盖先保存，不做冲突检测、不做编辑锁、不做按人隔离的草稿（V1，§12）。
  - 为降低「不知道自己在改谁的东西」的风险：进入草稿时页头显示**上次保存时间与保存人**（接口 3 出参 `lastSavedAt` / `lastSavedBy{name, role}`，取 `updated_at` / `updated_by` join 用户表，**不新增快照列**）。
  - **提交人以最终点提交的那个人为准**：`submitter_name` / `submitter_role`（同时快照 `dimension_name` / `dimension_abbr`，§5.2 这两列的**唯一写入点**）在提交时快照 —— **即使草稿全程由他人保存，提交人只记录点提交的那一个**。
  - ⚠ **「后保存覆盖先保存」只限草稿之间**：它<b>不</b>意味着「草稿写入可以覆盖已提交记录」。「已 SUBMITTED 的记录任何写接口一律拒绝」这条不变量在并发下**由数据库层兜底、不靠代码自觉** —— 写路径（存草稿 / 提交 / Reset / 删附件）一律先用 `SELECT … FOR UPDATE` 取草稿行再写。不能只靠 `@Version`：存草稿与 Reset 只改 `unlocked_level` / `level_score` / `terminated_level` 三列，而 Reset 恰好把它们设回与自己加载快照**逐字相同**的初始值 —— 配 `@DynamicUpdate` 后 Hibernate 判定该行干净、**一条 UPDATE 都不发**，版本谓词根本不出现，于是它能把别人刚提交记录的作答与证据附件删空且全程无异常。加行锁后，对方先提交时查询直接返回空，调用方走「新建草稿」分支，用户这一轮的作答一条不丢。
- **丢弃草稿 / Reset 的状态转移（接口 28 `DELETE /erl/assessment/draft`）**：
  - 转移方向 **`DRAFT → 无记录`**（不是「回到某个更早的草稿」，也不产生历史记录）：删除该四元组的 `DRAFT` 行、其全部答案行与附件登记行，`unlocked_level` 概念随之回到该维起点（§6.3 接口 28）。
  - **不可逆**；无二次确认，点下去直接清。
  - **只对 `DRAFT` 生效**：该四元组已 `SUBMITTED` 的历史记录一行不动，最新提交的判定不受影响。
  - 附件只有 `erl_answer_attachment` 一份记录，删就删干净（§6.7）。
  - 这同时是换题集的路径：不必先把旧草稿提交掉，直接 Reset 后 `Add New` 即可（§7.9-⑤）。
- **只有 `SUBMITTED` 的记录**进 B3 历史列表、ERL Card、维度详情页与 F2 总表。
- **四元组内 `submitted_at DESC, id DESC` 的第一条是该维度的 source of truth**，展示页与 F2 按维度各取各的；B3 展示全部。
  - ⚠️ **没有索引兜底「至多一条 SOT」**：并发双提交会产生两条合法记录，读侧只是“选出一条”。因此**读侧每一处取 SOT 必须走同一个 Repository 方法**（排序键完全一致），否则同一秒两次提交时不同页面会选出不同的一条。**唯一例外**：接口 7 要列出**全部**记录，故走派生查询 + 在内存里按四元组取首条；允许的前提是**排序键与该 Repository 方法的谓词逐字一致**（§6.3）—— 除此之外一律不得自拼查询。
  - 因此 ERL Card / 雷达图上的一组维度分，**可能来自不同时间、不同提交批次、甚至不同题库版本的多次提交** —— 这是维度级提交的必然结果，不阻止、不告警（§7.10）。
- 已 `SUBMITTED` 的记录**任何写接口一律拒绝**（PRD §3.3「提交后即只读」），接口 28 同样拒绝。
- **重复提交确认文案分两支**：该 `(company, period, portal, dimension_code)` 的 `submissionCount = 0` 时沿用首次提交文案；`> 0` 时标题 `Submit again?`、正文 `An evaluation for this quarter has already been submitted. Do you want to submit again?`、主按钮 `Submit again`（不提 source of truth，见 §13-Q30）。

### 7.8 基准记录口径（PRD §4）

> 本节说的「基准记录」= `erl_reference_score`（§5.6），「每维基准分」= `erl_reference_score_item`（§5.6.1）；维度键为 `dimension_code`，并随行快照 `dimension_name` / `dimension_abbr`。HTTP 路径为 `/erl/benchmark`。

| 口径 | 规则 |
|------|------|
| 基准分本身 | **外部输入，平台不计算、不折算**（PRD §4）；1–9，按维度存。**存储是一位小数**（`numeric(3,1)`），但 **D2 录入侧只收整数** —— 两者不一致是刻意的 |
| `benchmarkitAvg` / `topQuartileAvg` | 该记录**各维基准分的算术平均**，保留 1 位小数（接口 15 照常下发，前端当前不展示）。录入表单按**当前 `status = 'Active'` 的维度**动态渲染，**全部必填**，故无缺维分母问题；分母是该记录实际的维度个数，**不写死 5** |
| `recordedAt` | 取**审计列 `created_at`** 下发**真实录入时刻**（`Instant` / ISO-8601，为空则 `null`），屏上列头为 `SUBMISSION TIME`；同期次可重复录入，这一列是屏上唯一能分先后的信息。⚠️ **不新增存储列** —— `created_at` 是审计基类自带的列（§5.6） |
| **卡片 / 维度页取哪条记录**（「适用记录」） | 取该公司 `period ≤ 当前展示期次` 中**最近的一条**（**`period DESC, created_at DESC, id DESC` 的第一条** —— 同期次可有多条，取最后录入的那条） —— 评估期次晚于最后一次基准录入时沿用最近基准，不留空；无满足条件的记录则视同无基准（§9）。<br>这里的「当前展示期次」由 §7.1.2 确定（closed month 所在季度）。**基准记录的「向前沿用」与 §7.1.2 明令禁止的「期次回退」不是一回事** —— 前者是在**已确定的展示期次**内挑一条外部录入的参照值（基准本就按季稀疏录入），后者是把**整页的展示期次**偷偷换成上一季。基准可以沿用，评估分数不可以 |
| **卡一取哪条**（`Current Version` 卡） | 取**该公司 `period` = 前端上下文期次（URL `?period=`）中提交时间最新的那条** —— 由前端从接口 15 的 `records[]` 里挑（每条都带逐维明细），该期次无记录或 URL 未带期次时落到**记录表首条 = 全库最近一次提交**。卡头显示 `Current Version · {所取记录的 period}`。⚠️ 服务端拿不到那个上下文期次，接口 15 只下发 `records[]`，由前端挑 |
| 与评估分的关系 | 基准**只并列展示，不参与**综合分与 Perception Gap 的任何计算 |
| 基准分的值域 | 基准**存储**是一位小数 1–9（`numeric(3,1)`），而评估维度分是 **0–9 整数**（§7.1）。⚠️ **D2 录入框只允许整数**，故**新录**的基准分事实上都是整数；存量的一位小数记录原样保留，服务端与列类型未改。两者同轴对比**不做取整或折算** —— 雷达图与维度页并列展示原值即可（基准是外部口径，平台无权改写，PRD §4） |

### 7.9 题库版本化与发布（PRD §3.8）

**新增 / 编辑 / 删除 / 重排四类变更全部经 Publish 才生效**。版本序列的作用域是**组织（租户）内**（PRD §4「ERL 配置层级按照租户层级」）。

**① 版本模型**

| 概念 | 落地 |
|------|------|
| 已发布版本 | `erl_question_config_version.status = 'PUBLISHED'` 中**本组织 `version_no` 最大**的那条（`version_no` 组织内唯一 ⇒ 结果唯一，§5.1.1）。⚠️ **必须带 `status` 条件** —— 草稿行的 `version_no` 恒为最大。**只被「新发起一次评估」这一个动作读取** |
| 草稿版本 | `status = 'DRAFT'`，**每个组织最多一份**（部分唯一索引保证）。**只有 ERL Configuration 页读它** |
| 一道题的跨版本身份 | `question_key`（§5.1）。`id` 每版一换，`key` 恒定 |
| 一次评估依据的题面 | `erl_assessment.erl_question_config_version_id` 快照 + **`erl_question_config_dimension_version_id`**（该维题目集快照行的 id，取题一跳直达，为空回退复合键查询，§5.2）。**填报页、维度详情页、计分、组合层、Goldie 输入一律读它，而不是最新已发布版本** |
| **绑定粒度** | **每维一份** —— `erl_question_config_version_id` 挂在维度级的 `erl_assessment` 行上，故**同一公司同一期次的各个维度可能绑不同的题库版本**（如 FRL 绑 v3、PRL 绑 v4，只因两维不是同一天开始填的）。**系统不阻止、不告警**，各维按各自绑定的版本渲染、计分、组装 Goldie 输入 |

> ⚠️ 一次评估从创建到提交、再到被展示与计分，全程锚在自己绑定的版本上。取「最新已发布版本」的地方**全系统只有一处** —— 创建新评估记录时（`ErlAssessmentService` 的首次 `POST draft`）。

**② 写时复制（copy-on-write）—— 两级判据**

> ⚠️ **为什么必须两级**：克隆粒度是**维度级**，而草稿版本行是**组织级**。若只用单一判据「本组织有无草稿版本」，则「先改 FRL（建草稿 + 克隆 FRL）→ 再改 PRL」时，PRL 会走「已有草稿 → 直接改」分支，而它**从未被克隆** —— `erl_question_config` 既无 `status`、也无指向版本行的外键，草稿题与已发布题在库里长得一模一样，于是该改动会**直接写穿已发布版本的题目行**，击穿 §7.9-⑤「版本锁定 / 无用户数据丢失路径」与 §7.9-⑥「不允许改已发布版本的题目行」。

```
管理员在配置页对维度 D 做任一变更（新增 / 编辑 / 删除 / 重排）
        │
        ├── 【第一级・组织级】本组织有 DRAFT 版本行吗？
        │      否 → 同事务内新建 DRAFT 行（version_no = 组织内 max + 1）
        │      是 → 复用它（并 SELECT … FOR UPDATE 取行锁，见 ②’’’）
        │
        ├── 【第二级・维度级】维度 D 在**本轮草稿**里已经克隆过了吗？
        │      （判定：草稿行下有没有 D 的 erl_question_config_dimension_version 快照行，见 ②’’）
        │      是 → 直接改那批草稿题目行
        │      否 → 同事务内克隆 D 的题目行：
        │            question_key 原样复制、id 重新生成、
        │            新 version_no = max(version_no WHERE organization_id = O AND dimension_code = D) + 1，
        │            并写草稿快照行
        │            → 再在新克隆出来的那批行上改
        │
        └──► 填报页 / 维度页 / 计分 此刻读到的仍是旧的已发布版本，毫无变化

⚠️ 两个 max 是**不同集合**的 max：第一级的是 erl_question_config_version.version_no（组织级发布批次号），
   第二级的是 erl_question_config.version_no（按 dimension_code 分组的题目集版本号）。

管理员点 Publish（接口 21）
        │
        └──► DRAFT.status = PUBLISHED，写 published_at / by
             同一事务内：为每个 status='Active' 的维度写一行
             erl_question_config_dimension_version（code/name/abbr/
             question_version_no/sort_order/bound_at）—— 发布当时的维度快照
             ↑ question_version_no = max(version_no WHERE organization_id = 本组织 AND dimension_code = 该维)，
               本轮被克隆过的维度拿到新号，未改动的拿到与上一版相同的旧号
             本版 status 翻成 PUBLISHED，它自己就成了「PUBLISHED 里 version_no 最大」的那一版
             （**一行都不碰上一版**）
             → 此刻起**新发起的评估**用新版本
             → **已存在的评估（含正在填的草稿）继续用各自绑定的旧版本**
             → **Publish 不推进任何 version_no**（推进发生在每维首次编辑的克隆时刻）
```

**②’’ 本轮草稿改动了哪些维度（三处共用）**

「哪些维度被本轮草稿改过」是三个地方的前提，统一由**一个解析函数** `draftDimensionVersions(organizationId)` 给出。**判据是显式记录**：克隆某维时，**同事务往 `erl_question_config_dimension_version` 写一行草稿版本的快照**。

> ⚠️ **不得用「`max(erl_question_config.version_no)` > 最新快照里该维的 `question_version_no`」反推是否已克隆** —— 该推论在两个产品可达的状态下给出错误答案，且都是静默的：「停用某维 → 发布 → 恢复该维」会误判「已克隆」（编辑直接写穿已发布版本，走接口 13 则物理删掉已发布的题目行，绑定该版本的历史评估永久丢题）；「把某维的题删光」会误判「未克隆」（删除被静默撤销，题目原样复活）。根因是 `max(version_no)` 同时承担了「哪一版是草稿」与「是否已克隆」两个职责。

```
ensureDimensionCloned(organizationId, dimensionCode)：
    若存在快照行 (erl_question_config_version_id = 草稿行 id, dimension_code)
        ⇒ 本轮已克隆，直接返回该行的 question_version_no
    否则
        ⇒ draftNo = max(erl_question_config.version_no WHERE organization_id AND dimension_code) + 1
           克隆该维**现有最新一批行**（即 max 那一版）到 draftNo
             —— 取 max 而不是取已发布号，是为了兑现 ②'''' 边界 ①「孤儿行在维度恢复时直接用上」
           写快照行 (草稿行 id, dimension_code, draftNo)
           返回 draftNo

draftDimensionVersions(organizationId)：
    对每个 status = 'Active' 的维度：
        published = 最新已发布版本的快照行.question_version_no（无则 0）
        若草稿行有该维快照 ⇒ 本轮**已克隆**，草稿题集 = 快照行.question_version_no
        否则                ⇒ 本轮**未改**，草稿题集 = published
```

> 💡 草稿行与发布行是**同一条 `erl_question_config_version`**
> （Publish 只是把它的 `status` 翻成 `PUBLISHED`，`id` 不变），所以克隆时写下的那批快照行
> **自动成为该发布版本的快照**，无需重写。Publish 时只剩两件事：为**本轮未克隆**的
> `Active` 维度补行（取旧号 / 从未有题写 `0`），以及删掉「草稿期克隆过、发布前又被
> `Inactive`」的行（②'''' 边界 ①）。

三个消费方：① 写时复制的第二级判据（上图）；② 草稿态的读侧取题（§7.9-②’）；③ 发布前的变更摘要 diff（§7.9-③）—— **diff 必须逐维做**，跨维度的整版本查询不成立。

**②’’’ 并发防线的准确表述**

`@Version` **只在「首次创建草稿」那一次生效**：`ensureDraftVersion` 在「草稿已存在」时只是一次 SELECT，不发 UPDATE ⇒ 版本谓词根本没出现。真正兜住竞争的是行锁：

- **每次题库写事务开头对草稿版本行 `SELECT … FOR UPDATE`** —— 这才是「A 加题 vs B 发布」与「两人同时首次编辑同一维度」两个竞争的唯一防线，也是第二级判据与克隆必须原子的原因。
- `@Version` 仅兜住**并发建草稿**（两个事务同时发现无草稿），与部分唯一索引 `uk_erl_question_config_version_draft` 双保险。
- ⚠️ **懒克隆的窗口**：A 首次编辑 PRL（触发 PRL 克隆）与 B 点 Publish 并发时，若 B 先提交，A 的克隆行会落在一个已变成 PUBLISHED 的版本头之下，既不在任何快照里、又是下一轮草稿的克隆基线 ⇒ A 未经审阅的改动会**静默混进下一次发布**。行锁能挡住（前提是编辑方真的取锁），**代码审查须专项检查**。

**②’’’’ Publish 写快照的三个边界**

| 情形 | `question_version_no` 取值 |
|------|------|
| 本轮被克隆改过的维度 | 新克隆出的那个号（= 该维 `max`） |
| 本轮未改动的维度 | 与上一版快照**相同的旧号**（该维 `max` 恰等于它） |
| **`Active` 但从未有题的维度**（新增后还没加题） | `max` 为空 ⇒ **写 `0`**，表示「该版本下本维题集为空」。**仍要写这一行**（否则 C7 缺卡）；该维的填报与提交由 §6.3 校验 3「0 题维度不可提交」拦住 |

另两个并发边界：① 某维在草稿期被克隆改过、**发布前又被置 `Inactive`** ⇒ 不写快照，其克隆行成为**孤儿行**（无快照指向，但仍是该维 `max`）—— 日后该维被恢复为 `Active` 时会被下一轮直接用上，**需在恢复时提示管理员确认**；② 发布前新 `Active` 但本轮未克隆的维度 ⇒ 按上表第二/第三行取值，正常写快照。

**②’ 两个 `version_no` 的分工与读侧解析**

| 列 | 含义 | 自增维度 |
|------|------|------|
| `erl_question_config_version.version_no` | **组织级发布批次号**（配置页显示 `Published v3` / `Draft v4`） | 组织内自增 |
| `erl_question_config.version_no` | **某个维度的题目集版本号** | 按 `dimension_code` 各自自增 |

两者由 `erl_question_config_dimension_version`（§5.1.5）建立对应。**读侧取「某发布版本下某维的题」分三条路径**：

- **已发布版本**：先按 `erl_question_config_version_id` + `dimension_code` 命中快照行拿到 `question_version_no`，再按 `(dimension_code, version_no)` 取题。
- **草稿版本**：按 §7.9-②’’ 的 `draftDimensionVersions` 取 —— 草稿行有该维快照（本轮已克隆）⇒ 快照行的 `question_version_no`；否则（本轮未改）⇒ 最新已发布号。
- **已绑定快照行的评估**（优先级最高）：`erl_assessment.erl_question_config_dimension_version_id` 非空时**直接一跳**取该行的 `question_version_no`，不再按复合键反查（§5.2）—— 前提是该行还在、维度与批次都对得上，否则打 WARN 回退。为空（存量行、或该维在那一版下本就没有快照行）时回落到上面两条路径 —— **三条路径对同一份数据必须解出同一个号**。

> **为什么草稿仍是「组织级一份」而不是每维一份**：§5.1.1 保留了 `uk_erl_question_config_version_draft ON (organization_id) WHERE status = 'DRAFT'`，即每组织至多一份草稿。这同时保住了并发论证 —— 所有题库编辑仍经同一条草稿版本行的 `@Version` 乐观锁 + 悲观锁，如果改成每维一份草稿，那条论证会失效。

**③ Publish 按钮**

- **激活条件 = 存在草稿版本**，与 PRD「有**新问题、新顺序或新编辑内容**」（即四类变更任一）一致。
- **维度配置不受 Publish 管辖**：配置页第二个 Tab **`Dimension Configuration`**（维度新增 / 删除 / 排序 / 权重）有**自己的 Save 按钮**与「权重合计 = 100.00」校验，**就地整组替换，不产生版本**（§7.11），**不产生题库版本、不激活 Publish 按钮**（§6.4 接口 24）。反之，题库 Publish **不改**维度配置，但**会读**当时 `Active` 的维度写入 §5.1.5 快照 —— 本模块**只有题库一条版本线**。
- 按钮**不分维度**：一次发布整个草稿版本（**该版本内的全部维度一起**），不做单维发布（§12）。
- 变更摘要由草稿与最新已发布版本按 `question_key` 逐字段 diff 得出（**必须逐维做** —— 先用 `draftDimensionVersions()`（§7.9-②’’）解出每维的草稿号与已发布号，再逐维比；跨维度的整版本查询不成立）（`added` / `modified` / `removed` / `reordered`）。⚠️ **只实时算、不落库**：历史版本的对比基线早已随后续发布改变，实时 diff 会算出与当时不同的数字，因此**接口 25（C7 版本历史）不返回 `changeSummary`**（接口 9 照常下发 `changeSummary` / `changeType`，前端不渲染）。

**④ 多管理员共享同一份草稿（已接受）**

草稿版本**在组织内**单份 ⇒ **同一组织的两个管理员同时改的是同一份草稿**，且**任一人点 Publish 会把另一人尚未改完的变更一并发布出去**。这是「题库按组织单份」的必然结果，不是缺陷，但界面不提示多人共编与连带发布（版本条、变更摘要、发布确认均已撤下），属已接受的代价。

V1 不做草稿的编辑锁、按人隔离的草稿、变更逐条勾选发布 —— 题库配置是低频管理动作，为它上并发控制不划算（§12）。

**⑤ 版本锁定**

**规则只有一条**：一次评估在**创建时**绑定当时最新的已发布版本（写入 `erl_assessment.erl_question_config_version_id`；同一时刻写 `erl_question_config_dimension_version_id` —— 本维在那一版下的快照行 id，取不到则留 `null`，§5.2），此后无论期间题库发布了多少个新版本，**在填的那一份都不会自己升级**。只有用户显式 Reset（接口 28，答案随草稿行一并删除）后再 `Add New`，新建的草稿才绑定当时最新的已发布版本。

| 场景 | 行为 |
|------|------|
| 正在填的草稿，期间题库发布了新版 | **内容零变化**：题目、题序、题数、来源标签、**level 结构与解锁进度**全部不变，已答内容原封不动（`unlocked_level` 同样锚在旧版本的 level 结构上）。<br>**版本不跟随，但要提示**：PRD §3.3 要求「若题库已更新，则**提示**题库更新，**不做强制退出和更新**」—— 填报页弹**强阻断二选一弹窗**（见 §8.4；数据来自接口 3 出参 `latestPublishedVersionNo` / `hasNewerQuestionSet`） |
| 题干在新版本里被改了 | 该评估看不到 —— 它读的是自己那版的题面。**答案与题面永远同版本自洽** |
| 某题在新版本里被删了 | 该评估里这题还在，分数 / 备注 / 附件一个不动（**无任何用户数据丢失路径**） |
| 新版本加了题 | 该评估不会多出未答题，`totalCount` 不变，不会被打断 |
| 提交 | **不校验版本是否最新** —— 半年前开的草稿仍按半年前的题集提交，不阻止 |
| 已 `SUBMITTED` 的记录 | 同样恒按 `erl_question_config_version_id` 渲染；历史详情、计分、Goldie 输入全部据此 |
| 下一次 `+ New` 发起新评估 | 才取当时最新的已发布版本 |

**衍生结论**：

- **同一期次的两端可以不同版本**：Founder 用 v3 提交 → 管理员发布 v4 → GSV 用 v4 填。Perception Gap 因此可能跨两套题集，**提交侧不阻止**；两端都已提交且该维题集版本号不等时，A1 Gap 区块该维显示 `New version pending` 且不送进 Goldie 分析（§7.10-13）。
  - 维度级提交下，**同一期次同一端的各个维度之间也可以不同版本**（FRL 绑 v3、PRL 绑 v4）。不阻止、不告警，各维按各自版本渲染与计分；前端不显示题集版本号（§13-Q31）。
- **同一期次多次提交也可能跨版本**：第 1 次基于 v3、第 2 次基于 v4，题数（`totalCount`）不同是正常现象，只体现在详情页页头的题数文案上。
- **Goldie 分析不受题库发布影响**：其输入（答案 + 备注 + 题干 / level）全部取自评估绑定的版本快照，题库发新版后输入一字未变 → **发布不触发重生成**。
- **不提供「把在填评估升级到最新题集」的按钮**（§7.10-N3）：代价是若新版修正了写错的题干，在填的人享受不到；换来的是「答案与题面永远自洽」这条硬保证。⚠️ Reset 后新草稿绑最新版**不属于**这条禁令 —— 禁的是「保着答案换题面」，而 Reset 是「答案清空后重新开始」。
  - **换题集的路径**：直接 **Reset（接口 28，Founder Flow 的 `Reset` 按钮）丢弃旧草稿 → `Add New` 重新发起**，新草稿创建时绑定当时最新的已发布版本，不需要「为了换题集而提交」的垃圾记录（§7.7）。Reset 连草稿行一起删，之后没有草稿行，题库更新弹窗自然不再出现。
  - 唯一草稿约束的作用域为 `(company, period, portal, dimension_code)`（§5.2）。
  - 代价是「**丢掉已填内容与附件**」（无二次确认）。

**⑥ 首版与部署**

- `erl_init.sql` **不落任何版本行与题目行** ⇒ **「系统起来后没有已发布版本、填报页全空」是新库的既定状态**，直到管理员在配置页 Publish 第一版（`ensureDraftVersion` 建 `version_no = 1` 草稿 → Publish 转 `PUBLISHED` 并逐维写 `erl_question_config_dimension_version`）。
- 上线后**不允许直接改库里已发布版本的题目行**（会让历史评估的题面漂移）；任何修正都走配置页 → 草稿 → Publish。

### 7.10 版本化的边界

题库版本化把「题面」从一份变成多份，随之产生一批**必须明确取值、否则实现会各写各的**的边界。下表是全量清单：**A 类**由裁决直接给出、**B 类**本设计已取默认值（需求方知悉即可）。

| # | 边界 | 类 | 本设计取值 | 若取反面 |
|---|------|:--:|-----------|----------|
| 1 | **发布粒度** | A | 一次发布整个草稿版本（**该版本内的全部维度一起**） | 单维发布 —— 裁决已明确不做 |
| 2 | **撤回 / 回滚** | A | 不做（已发布不可退回草稿，无版本回滚 UI） | 需要版本切换与「当前生效版本」指针，模型要再改一层 |
| 3 | **变更类型** | A | 新增 / 编辑 / 删除 / 重排**四类全部**经发布 | 只有新增经发布 —— 不做 |
| 4 | **草稿唯一性** | B | **本组织一份草稿**，多管理员共享；任一人发布会连带发布他人未完成的改动（§7.9-④） | 每人一份私有草稿 → 需要三方合并与冲突解决，V1 不划算 |
| 5 | **丢弃草稿** | B | **不做**。误改只能手工改回来（题库低频） | 加 `DELETE /erl/question/draft` 即可，不影响模型（§12） |
| 6 | **评估是否跟随题库** | A | **不跟随（版本锁定）** —— 评估创建时绑定版本，此后题库发布多少版都与它无关（§7.9-⑤） | 重基 —— 不做 |
| 7 | **版本数据保留** | B | **只克隆被改动的那个维度**（按 `dimension_code` 分版本线），**永久保留、不清理** | 定期归档旧版本 —— 会让历史评估取不到题面，不可做 |
| 8 | **谁能 Publish** | B | C 模块的 admin 均可，不再分级 | 若需「编辑者 / 发布者」分权，属 §13-Q7 的角色细化 |
| 9 | **组合层跨版本可比性** | B | 不做提示 —— F2 总表可能同屏比较基于不同题库版本的分数 | 要提示则需在表内标版本号，噪音大于价值（V1 不做趋势对比） |
| **W1** | **改权重会改变历史期次的综合分与 Stage** | **A** | **接受漂移**：权重不版本化、**不做任何快照**，综合分实时按当前 `erl_dimension_config.weight` 算（§5.1.3 / §7.1）；Save 不弹确认框，页面上无处提示这一点（§8.4-C6）。见 §13-Q21 | 要不漂移 —— 需在 `erl_assessment` 上存每维权重快照，需求方已选择不补 |
| **W2** | **跨组织题库结构不同 ⇒ 分数不可比** | B | **接受、不提示**：F2 只列有权访问的公司，正常同组织；跨组织时综合分各按各组织权重算（§6.8） | 要求全平台统一题库 —— 与 PRD §4「配置层级按租户」直接冲突 |
| 12 | **发布是否触发 Goldie 重新生成** | **A** | **不触发** —— 分析输入全部锚在评估绑定版本上，题库发新版后输入一字未变 | — |
| 13 | **同一期次两端可否基于不同版本作答** | **A** | **允许**。提交侧不阻止；前端不显示任何题集版本号（§8.4「B 题集版本标注」）；两端都已提交且该维题集版本号不等时，A1 Gap 区块该维渲染成绿点 + 琥珀字 `New version pending`（另有面板级告警，§9）且**不送进 Goldie 分析** | 要求两端同版本 —— 会让「发布」被在填评估无限期阻塞 |
| **N1** | **旧版本草稿的时效** | B | **可无限期停留**：提交时**不校验**绑定版本是否最新，半年前的草稿按半年前的题集提交。**但要提示** —— 填报页弹**强阻断弹窗、必须二选一**（见 §8.4）：要么按旧题库就地提交、要么 Reset 换新题库（接口 28）—— 于是「无限期停留」实际只剩「不主动进这一页」这一种方式。一方停在旧题集期间，若两端**都已提交**且该维题集版本号不等，A1 Gap 区块该维显示 `New version pending` 并跳过分析，落后一方补交后自动消失（§7.7） | 设过期时间强制重开 —— 会丢已填内容，与「不丢数据」的取向冲突 |
| **N2** | **同期次多次提交跨版本** | B | **允许**：第 1 次基于 v3、第 2 次基于 v4。前端不显示题集版本号（§13-Q31；接口 7 与 `submission` 不带 `questionVersionNo`）。跨版本本身照旧允许、不阻断，但两端同维版本号不等时 Goldie 不分析该维、小卡出 `New version pending` 提示 | 强制同期次同版本 —— 同 13 的问题 |
| **N3** | **在填评估「升级到最新题集」按钮** | B | **不做**（指的是「**保着答案**换题面」；**Reset 后新建草稿绑最新版不在此列**，那时答案已全部清空）。代价：新版若修正了写错的题干，在填的人享受不到 —— 但用户至少**知道有新版**（N1 的强阻断弹窗，§8.4）。换题集直接 **Reset（接口 28）丢弃草稿 → `Add New`** 即可（§7.7 / §7.9-⑤） | 做升级按钮 —— 等于把重基又请回来 |
| **N4** | **维度删除对历史期次的影响** | A | 配置页有**两个**破坏性动作，且**能删的与能影响历史的不重叠** —— **垃圾桶 = 删除**只对「从未进入过任何已发布题库版本」的维度开放（`deleted = true`），**电源按钮 = 停用**才是已发布维度唯一能做的事；**已被填报过、且题库发布过的维度删不掉**，只能停用，本行讨论的漂移场景全部由停用触发。**停用 = 软删**（`status = 'Inactive'`，行与 `weight` 原样保留，§5.1.3）：① **历史提交记录照常显示** —— 名称 / 缩写取 `erl_assessment.dimension_name` / `dimension_abbr` 行上快照（§5.2），`Retired` 灰标由 `status` **直接判定**；② 不进新期次的问卷、不参与新期次的综合分与 Share 门槛（见 §7.5「报告就绪（ready）」）。⚠️ **但历史期次的综合分、Stage 与雷达图形状会因此漂移**（该维退出加权集合，同一次保存须把其余维度权重重新分到合计 100%）—— 这是已接受的代价 | 物理删除 —— 历史记录连名字都查不到，已否决（「删除」也不是物理删除：置 `deleted = true`、行留、历史按 code 仍解得出，§5.1.3） |
| **N5** | **同一期次的各维度绑不同题库版本** | B | **允许，各自独立**（维度级提交的必然结果）：渲染按各维自己的 `erl_question_config_version_id`（再经 §5.1.5 快照解析出该维的 `question_version_no`），计分按各维自己的 level 结构（`max(levels)` 可能因版本而异），Goldie 输入按各维自己的题面组装。**不阻止、不告警** | 要求同期次全维同版本 —— 会让「发布」被任一在填维度无限期阻塞，且与维度级提交直接矛盾 |

> 取「最新已发布版本」的代码路径全系统只有一处（创建评估记录时），是本模块的**唯一版本入口**，代码审查专项检查。
>
> 本模块**只有一条版本线** —— **题库版本**（`erl_question_config_version`，Publish 生效，绑在 `erl_assessment.erl_question_config_version_id`；版本内各维的题目集另有按 `dimension_code` 自增的 `erl_question_config.version_no`，两者由 §5.1.5 快照表对应）。维度配置只有一份**当前值**，没有版本线，也不与期次绑定。Publish 时只是把当时 `Active` 的维度**逐维快照**进 §5.1.5，供 C7 回看。
>
> 另一条计分边界（不属版本化，记在此处便于集中核对）：**逐级解锁的「同一 level 内是否要答完才算终止」** —— **不要求**，按 `sort_order` 扫到第一道 No 即终止（§7.2-①）。

### 7.11 维度配置的保存与生效

维度不是编译期枚举，而是**租户级的配置数据**（**接口驱动**）。本节写「怎么保存」「怎么生效」「删除怎么算」三件事。

**① 只有一张表**（模型见 §5.1.3）

| 表 | 作用 |
|------|------|
| `erl_dimension_config` | 一个**组织**的维度集合当前值：`dimension_code` / `dimension_name` / `dimension_abbr` / `sort_order` / `weight` / `status` / **`deleted`**（与 `status` 正交：`deleted = true` 的行**所有读侧一律排除**、页面无恢复入口，§5.1.3）；「上次保存于何时 / 谁保存的」取审计列 `updated_at` / `updated_by`（整组取 `max(updated_at)`）。`dimension_code` 是**稳定身份**、一经创建永不改变，历史数据靠它关联 |

**② 保存：整组就地替换，不产生版本**

```
管理员在配置页 Dimension Configuration Tab 增 / 删 / 改名 / 排序 / 改权重
        │
        └──► 点 Save（接口 24 PUT /erl/dimension/config，整组提交）
                 │
                 ├── 服务端校验：带 dimensionCode 的行必须命中已有行；
                 │                          不带的为新增，由服务端随机生成 code
                 │                + status = 'Active' 的行权重合计恰为 100.00
                 │
                 └── 同一事务内单阶段直接写终态：按 (organization_id, dimension_code) upsert erl_dimension_config
                                 （覆盖 name / abbr / sort_order / weight / status；保存时间 / 保存人
                                   由审计列 updated_at / updated_by 承接）
                                 + 提交里缺席的维度置 status = 'Inactive'（软删，不删行）
                                 + deletedCodes[] 点名的维度置 deleted = true
                                   （真删：行留、页面两处都不显示、无恢复入口；只 setDeleted(true)，status 不动）
                     → 保存即全局生效，无版本、无生效延迟
```

- 缩写不设唯一约束：「停用 FRL + 新增一个也叫 FRL 的维度」「A/B 互换缩写」这类终态合法的操作直接合法，不需要中间态。
- `savedAt` = 全部行 `max(updated_at)`；**只有真正发生变更的行会 bump**（乐观锁仍然正确：有变更必 bump，无变更则令牌不变、下次仍校验得过）。

⚠️ **可删性检查的落点**：`deletedCodes[]` 的三条校验（§6.4-3-⑧⑨⑩）与集合完整性校验（§6.4-2-⑥）**必须都在 `validate()` 阶段完成**，用**整组锁读**（`findForUpdateByOrganizationId`）拿到的 `existing` 判定 —— 校验一律跑在任何写入之前，因为业务错误要求「**库中不得有任何写入**」（§6.4-3）。

**删除只写 `deleted` 一列、完全不碰 `status`**：落库为「删掉启用中的维度 = `(Active, true)`、删掉停用中的维度 = `(Inactive, true)`」（§5.1.3）。
> ⚠️ **代价是库里会真实存在 `status = 'Active'` 且 `deleted = true` 的行**，于是「已删维度不被热读捞出来」**完全依赖读侧都带 `deleted` 这一半**：每一个读侧方法名上的 `AndDeletedFalse`。漏掉它，这一行就会**以启用维度的身份复活**（重新出现在主列表、进权重合计与问卷）。

⚠️ **落库要绕开已删行**：
- **「缺席即停用」必须跳过 `deleted = true` 的行** —— 已删行**永远**不出现在 `dimensions[]` 里，若照「缺席」规则处理，每一次保存都会去改一批用户看不见的行的 `status`（本身无害，但把这些行的 `updated_at` 一路推高、`savedBy` 会指向一个从没碰过它们的人）。⚠️ **真正危险的是写成整行覆盖或 upsert 时带上 `deleted` 的默认值** —— 那会把 `deleted` 冲回 `false`，**已删的维度在下一次保存后集体复活**，而页面上看起来只是「保存成功」。

- **整组替换语义**：接口 24 提交的是**完整的维度列表**，服务端不做逐条 diff、不做部分更新 —— 否则中间态必然破坏「合计 100%」。⚠️ 整组替换写的是本组织的这批行本身，**改动前的旧值不留存**。
- **Save 按钮双条件**：① 脏态（维度增 / 删 / 排序 / 权重 / **启停用**任一变化）② **`Active` 行**权重合计 = 100%；越界提示 `Exceeds 100% by {n}%` / `Needs {n}% more`。
- **与题库 Publish 的关系**：配置改动**不激活 Publish 按钮**，走自己的 Save；题库 Publish 也**不改维度配置** —— 但它**会读**当时 `Active` 的维度写入 §5.1.5 快照。
- **Save 不弹确认框**，点了直接保存。

**③ 生效：只有一份当前值，无期次绑定**

| 场景 | 取哪些维度 |
|------|------|
| 任何按期次渲染 / 计分的地方（卡片、雷达图、A3 / A4、F2、Gap 状态点、Share 门槛） | **一律读 `erl_dimension_config` 中该组织 `status = 'Active'` 且 `deleted = false` 的行**（删除**不改** `status`，漏掉 `deleted` 这半边会漏出一个用户已经删掉、且再也管理不到的维度），按 `sort_order` 排序 |
| 历史提交里出现过、今天已 `Inactive` **或已删**的维度 | 该维的名称 / 缩写由 `erl_assessment.dimension_name` / `dimension_abbr` **行上快照**还原（§5.2），或回本表读那一行（**两种情况下行都仍在** —— 这正是删除做成置位而不是 `DELETE` 的原因，§5.1.3） |
| C7 题库版本快照页 | **不读本表当前值** —— 读 `erl_question_config_dimension_version` 的发布当时快照（§5.1.5，接口 26 出参 `dimensions[]`） |
| 期次都定不下来（closed month 取不到，§7.1.2） | 不渲染任何维度，走空态 |

⚠️ **历史期次会漂移**（已接受）：
- 改权重会**回溯改变**已提交历史期次的综合分与 Stage —— `erl_assessment` 上有每维的 `level_score` 快照，但**权重不在快照里**，综合分是实时加权算出来的（§7.1）。
- 新增维度会让历史期次凭空多出一个「未填」的维度；`Inactive` 维度会从历史雷达图上消失。
- 见 §13-Q21，取值「改权重影响历史」。

**④ 两个破坏性动作：停用（软删）与删除（真删）**

**判据只有一条**：该 `dimension_code` **有没有出现在某个 `PUBLISHED` 题库版本的维度快照里**（`erl_question_config_dimension_version` join `erl_question_config_version`，§5.1.5）。服务端把结论作为接口 23 的 `deletable` 下发，前端据此决定行尾给哪个图标 —— **前端不自己算**，判据只有一处实现。

| `deletable` | 前端本地状态 | 行尾图标 | 落库 | 之后在哪儿 |
|---|---|---|---|---|
| `true`（**从未**进入过已发布版本） | 常规行 | **垃圾桶** = 删除 | **`deleted = true`**（`status` 不动） | **哪儿都没有** —— 主列表没有、`Deactivated Dimensions` 区块也没有，**无恢复入口** |
| `false`（进入过已发布版本） | 常规行 | **电源按钮**（`PoweroffOutlined`）= 停用 | `status = 'Inactive'`（`deleted` 不动） | `Deactivated Dimensions` 区块，行尾 **`Activate`** |
| **任意**（含 `true`） | **`isRestored`** —— 本次会话里刚从停用区 `Activate` 回来、尚未 Save | **电源按钮** = **撤销恢复** | 撤销后回到「本次不恢复」，Save 时其 code 仍进 `deactivatedCodes[]` | 回到 `Deactivated Dimensions` 区块 |

⚠️ **行尾图标是三态、不是二选一**：判据是 **`row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`**。刚恢复回来的行若照常给垃圾桶，用户想撤销刚才的恢复时，行尾**最近的那个按钮**恰好是**不可逆**的真删。撤销恢复那一支另有独立的原生 `title` 与 aria-label `Undo restore`（见 §8.4-C6-③）。

- **只有垃圾桶要二次确认**，电源按钮点了直接生效；「为什么不能删」由列表下方常驻的 `dimensionConfigDeleteHint` 说明（否则用户只看到「这一行的图标跟别的行不一样」）。
- **停用（`Inactive`）那一支**：入口是电源按钮；`Save` 时该维度**不出现在提交的 `dimensions[]` 里**、其 code 进 `deactivatedCodes[]`，服务端据此置 `Inactive`；**行与 `weight` 原样保留**，可再置回 `Active` 恢复。
- **删除（`deleted = true`）那一支**：code 由 **`deletedCodes[]` 显式点名**（不是靠「缺席」表达 —— 缺席**只表示停用**）；行与 `weight`、`dimension_name` / `dimension_abbr` 全部原样保留，历史数据仍按 `dimension_code` 反查得到，但**所有读侧一律排除**（§5.1.3）。
- 停用或删除后剩余维度的权重合计会不足 100%，**需在同一次 Save 里补齐**。
- **已 `Inactive` 的维度**：① 不进填报页、不进当前的综合分与雷达图；② 历史提交记录照常可查（名称/缩写取评估行快照）。**已 `deleted` 的维度同 ①②** —— 区别只在配置页上看不见、也拿不回来。
- `ErlDimensionConfigStatusEnum` 是**落库枚举**：取值 `Active` / `Inactive`，就是 `erl_dimension_config.status` 列；`Retired` 灰标由列值**直接判定**。⚠️ **`deleted` 不进这个枚举**：它与 `status` 正交，合并成三值后「删掉一个当前已停用的维度」（可达）就没有落点了。
- **删除有前置拦截** —— 已进入过已发布题库版本的维度**禁止删除**（服务端硬校验，§6.4-3-⑨），只能停用。
  - **判据不是「有无历史数据」**：那个判据会连「有人填过、但题库从没发布过」的维度也拦住 —— 那种维度删掉是**安全的**（它本就不是任何已发布版本的一部分，而 `dimension_code` 仍被占用、历史仍解得出名字）。
  - **保护对象也不是那一行**（软删/真删下行都不消失），而是**已发布题库版本的语义**：那份版本的维度快照、以及按 code 关联到它的历史（`erl_assessment` / `erl_reference_score_item` / Gap items），**必须始终解得出那个维度**。一旦它从产品里彻底消失且不可恢复，那份已发布版本就成了「引用着一个用户再也管理不到的维度」的版本。
- ✅ **C7 不受维度配置变更影响**：C7 既不隐藏「今天已不在配置里」的维度、也不给它打 `Retired` 灰标，**不调接口 23**。本节的保存流程（单阶段 upsert；停用与删除两个动作）对 C7 的展示**零影响**，C7 只读 §5.1.5 的发布当时快照。

**⑤ 相关接口**

| 接口 | 语义 |
|------|------|
| **接口 23** `GET /erl/dimension/config` | 返回该组织的维度配置（`dimensionCode` / `dimensionName` / `dimensionAbbr` / `sortOrder` / `weight` / **`status`** / **`deletable`** / `savedAt` / `savedBy`）。**默认只返 `Active`**；**配置页恒带 `includeDeactivated=true`**（停用行由常显区块承载）。⚠️ **`deleted = true` 的行任何情况下都不下发** |
| **接口 24** `PUT /erl/dimension/config` | **整组保存**维度集合 + 排序 + 权重，校验通过即**就地替换**（缺席维度置 `Inactive`；另按 `deletedCodes[]` 置 `deleted = true`，**只对从未进入过已发布题库版本的维度开放**） |
| 接口 1 / 20 / 22 等按期次读的接口 | 维度列表与权重一律取**当前 `Active` 集合**（本节 ③），出参中的维度**是变长数组，不是固定五项** |

---

## 8. 前端设计（功能级）

### 8.1 路由（`config/routes.ts`）

| URL | component | 页面 | 说明 |
|-----|-----------|------|------|
| `/companyOverview` | `./companyOverview/home` | **A1 / A2 ERL Card** | **存量页，不新增路由** |
| `/exitReadiness/dimension/:dimension` | `./exitReadiness/dimension` | A3 | |
| `/exitReadiness/scoreDetails` | `./exitReadiness/scoreDetails` | **A4 全维 Score Details** | **F2 `View` 的落地页**，同时是**两端 ERL Card 右上 `Full View ›` 的落地页** |
| `/exitReadiness/assessment` | `./exitReadiness/assessment` | B1（`?portal=gsv` 切 B2） | |
| `/exitReadiness/history` | `./exitReadiness/history` | B3 | |
| `/exitReadiness/history/:assessmentId` | `./exitReadiness/history/detail` | B3 单次提交详情 | |
| `/exitReadiness/benchmark` | `./exitReadiness/benchmark` | D1 基准记录页（两张卡） | 仅管理端 |
| `/exitReadiness/benchmark/add` | `./exitReadiness/benchmark/add` | **D2 新增记录（独立页，非 Modal）** | 仅管理端 |
| `/exitReadiness/configuration` | `./exitReadiness/configuration` | **两个顶层 Tab**：`Question Library`（C1 + C3 删除 + C4 拖拽 / 改 band）+ **`Dimension Configuration`**（C6 维度新增 / 删除 / 排序 / 权重） | **仅管理端**（PRD §3.8「仅 portfolio portal」） |
| `/exitReadiness/configuration/history` | `./exitReadiness/configuration/history` | **C7 题库版本快照页** | **仅管理端**；入口为 `Question Library` Tab 的 `View history` |
| `/exitReadiness/configuration/add` | `./exitReadiness/configuration/add` | C2 | |
| `/exitReadiness/configuration/edit/:questionKey` | `./exitReadiness/configuration/edit` | C3 | 按 **`:questionKey`** 定位 —— §6.4 的 C 模块写接口一律按 `questionKey` 定位，写时复制后草稿行是新 `id`，用 `id` 进页面必然失配 |

**不设 `/exitReadiness`（Dashboard）落地页** —— PRD §3.1「不设独立 Exit Readiness 落地页」。

**F2 不新增路由** —— 它是 `/company`（`./portfolioCompanies/home`）页内的**第 6 个 Tab**（`key='6'`）。

**菜单入口**（PRD §3.1 / §3.8）：
- ERL 展示入口**只在 Company Overview 的 ERL Card 上**，主导航不新增一级菜单。ERL Card 内部下钻的三个入口：右上 `Full View ›` → A4（两端）、维度行 `View Details →` → A3、雷达图下方 `View Top GSV Quartile & External Benchmarks ›` → D1（仅管理端）。
- **ERL Configuration 挂顶部导航右侧下拉菜单**（PRD §3.8），**仅管理端可见**；其内容按调用者 `organization_id` 隔离。
- B1/B2 填报入口在 **Assessments 区块**内（PRD §3.3 / §3.4）；另从维度详情页的 `+ New`、**以及 A4 每张维度卡卡头的 `Add New`** 进入，两者均带 `?dimension={code}`（填报单元＝单个维度，见 §8.4「B 填报单元」）。
- C 模块路由对管理端可见，公司端由菜单与路由守卫双重拦截。

#### 8.1.1 ⚠️ 菜单入口的落地前提

「挂顶部下拉菜单」不是写一行前端代码就完事 —— 该下拉是**数据驱动**的，缺一条库记录入口就不出现。链路：

```
BasicLayout 里硬编码的 menuRight_SuperAdmin（含 `ERL Configuration`）
        │
        ├── 门 1：userData.roleType === 1 才取用这份清单
        │
        └── 门 2：getVerifyRoles() 把它与后端菜单权限按 `path` **求交集**
                  └── POST /api/web/menus/getMenuTreeByRoleId
                        └── select m.* from menu m
                              join r_role_menu rm on m.id = rm.menu_id
                              join r_user_role  ur on rm.role_id = ur.role_id
                            where ur.user_id = ?
                        └── buildTree(...)：**只返回 pid = '0' 的根节点**
```

**因此必须满足三个条件，缺一个菜单就不显示**：

| # | 条件 | 落地位置 |
|:--:|------|----------|
| 1 | `menu` 表有 `path = '/exitReadiness/configuration'` 的行，且 **`pid = '0'`**（根节点） | **管理后台菜单配置** |
| 2 | 该菜单经 `r_role_menu` 授权给用户的角色（后台配菜单时授权给超管角色） | 同上 |
| 3 | 清缓存后重新登录 | 见下 |

- **`pid` 必须是 `'0'`**：`MenuServiceImpl.buildTree` 只把 `pid = '0'` 的行放进返回数组顶层，而 `getVerifyRoles` **只比较顶层 `path`、不递归 `menuDtoList`**。挂到某个父菜单下会被嵌进子级，下拉里依然不显示。
- **缓存**：服务端 `MenuServiceImpl.findAllByUserId` 不缓存、每次现查；浏览器 `localStorage.roles` + 同名 cookie（`utils.ts` 的 `saveRoles`）会缓存，且 `BasicLayout` 只在 `!rolesData || length < 1` 时才重新拉。**不清浏览器缓存，改了库也不生效。**
- **基准页 `/exitReadiness/benchmark` 不需要菜单行** —— 它不在那份下拉清单里。站内入口有两个：① **ERL Card 雷达图正下方的链接 `View Top GSV Quartile & External Benchmarks ›`**（→ `/exitReadiness/benchmark?companyId=`**`[&period={period}]`**，由接口 1 的 `benchmarkUrl` 下发），**仅管理端渲染**（与雷达图同一端裁剪条件）；② A4 末位基准 Tab 卡头的 `+ Add New` / `View history`（同样带 `&period=`）。`/benchmark/add` 由 D1 页内 `+ Add New` 进入。

**路由守卫**：`SecurityLayout.tsx` 对 `/exitReadiness/configuration*` 与 `/exitReadiness/benchmark*` 拦截 `roleType > 1`（公司端）→ 重定向回 Company Overview。

> **为什么守卫按端类型判、不按菜单权限判**：菜单权限决定「入口显不显示」；基准页本就没有菜单入口，而配置页若也压在菜单权限上，一旦**菜单未在管理后台配置**（或配错成非根节点、忘了授权），管理员会被彻底锁在门外。PRD §3.8 的原话只是「仅 portfolio portal」，端类型判定已足够。后端另有一层：C 模块写接口与 D 模块全部接口一律校验管理端（§4.3）。

> ⚠️ **端类型判定必须用 `roleType`，不得用 `isAdminEnd()`**（见 §4.1 末段）。
- **A4 无菜单入口**：A4 **不进**顶部下拉菜单，页内入口有两个：① **两端 ERL Card 右上角的 `Full View ›`**（PRD §3.5 写「仅 Company portal」，原型截图显示组合端卡片同样有 `Full View`，按原型两端都渲染）；② F2 ERL Tab 的 `View ›`（管理端）。

### 8.2 目录结构

遵循 `CIOaas-web/CLAUDE.md`「同域多功能归入域文件夹作第二层」「域根须有 README.md」「转发式 index.tsx 仅限路由页面入口」：

```
src/pages/exitReadiness/
├── README.md                      域文档（职责 / 目录 / 域内要求）
├── components/                    域级共享：
│                                  ErlRadarChart(A2，仅管理端渲染)、DimensionScoreRow、
│                                  LevelAccordion(B，逐级解锁分组：CLEARED/ACTIVE/BLOCKED/LOCKED)、
│                                  YesNoField(B，唯一的作答控件)、
│                                  QuestionRow、
│                                  EvidenceNoteField、AttachmentUploader(10MB 校验)、
│                                  GapAnalysisPanel(E1)、
│                                  GapAnalysisDetailModal(A1「View details」弹框，按维度分区)、
│                                  ShareToFounderButton(A1「Share to founder」，门槛未达成置灰)、
│                                  DimensionConfigForm(C6，维度新增/删除/排序/权重 + 100% 校验，
│                                    只有数字输入、无滑条)、
│                                  PeriodSelect、PortalTabs、
│                                  SubmissionMetaBar(A3 元数据栏)、
│                                  QuestionSetUpdatedModal(B 强阻断题库更新弹窗)、
│                                  useDimensionConfig(读接口 1/23 的维度配置，
│                                    维度名/缩写/排序/主题色的唯一来源)、
│                                  types.ts
│                                  维度元数据一律接口驱动（useDimensionConfig），不设静态 `DIMENSIONS` 映射；
│                                    `constants.ts` 只放与维度无关的常量（Era 配色、附件上限等）
├── dimension/{index.tsx, DimensionPage.tsx, hooks/, components/}
├── scoreDetails/{index.tsx, ScoreDetailsPage.tsx, ScoreDetailsPage.test.tsx, hooks/, components/}   A4
│                                  components/ 内（均为 A4 私有）：
│                                    DimensionQuestionsCard.tsx（维度横向 Tab，一次只渲染一维，卡片不折叠）、
│                                    BenchmarkPanel.tsx（末位基准 Tab 的内容）、
│                                    ScoreQuestionRow.tsx（三态徽章 + NOTES / ATTACHMENTS 块）
├── assessment/{index.tsx, AssessmentPage.tsx, hooks/, components/}
├── history/{index.tsx, HistoryPage.tsx, detail/, hooks/, components/}
├── benchmark/{index.tsx, BenchmarkPage.tsx, add/, hooks/, components/}
│                                  components/ 内含 BenchmarkDimensionTable（D1 两张卡与 D2 表单共用的
│                                    **按维度行结构**，行数随配置维度动态）
└── configuration/{index.tsx, ConfigurationPage.tsx, add/, edit/, history/, hooks/, components/}
                                   ConfigurationPage.tsx 组装两个顶层 Tab：
                                     Question Library → 维度 Tab（按配置动态）+ QuestionLibraryTable
                                       （表格 + Era band 分组行 + 拖拽列 + 行内 Era band 下拉）
                                     Dimension Configuration → DimensionConfigForm（维度行的新增 / 删除 /
                                       拖拽排序 / 权重输入，整组 Save 走接口 24）
                                   history/ 为 C7 版本快照页 —— 页头版本下拉取接口 25（只列已发布版本，
                                     草稿不进下拉）、只读题目表取接口 26；卡片按该版本的 §5.1.5 逐维快照渲染
                                     （该维度集合随接口 26 出参 `dimensions[]` 下发）

改存量页：
src/pages/companyOverview/home/
├── CompanyOverviewPage.tsx        DI 卡区块 → 渲染 ErlCard；DI 分支保留但不再进入
└── components/ErlCard/            A1 卡片（含 A2 雷达图，复用 exitReadiness/components/）

src/pages/portfolioCompanies/erl/  F2 Tab 内容组件（与 Benchmarking/ Issues/ 平级）
├── ErlTab.tsx                     纯展示表格（非路由 Tab 内容，不写转发 index.tsx）
├── ErlTab.less
└── hooks/useErlPortfolio.ts       取数 + `currentQuarterPeriod()`（无 query 状态，只随 portfolioId 变）
```

分层口径按 `standards/architecture.md` §3：`index.tsx` 只转发；`XxxPage.tsx` 组装 hooks 与 components；**业务逻辑（调 API / 管状态）只写在 `hooks/`，`components/` 收 DTO props 不调 API**。

> ErlCard 放 `companyOverview/home/components/` 而非 `src/components/` —— 当前只此一处使用（YAGNI）；其内部复用的雷达图等下沉在 `exitReadiness/components/`，跨域 import 只允许 import 该域的公开组件与 `erlService`。

### 8.3 服务层（`src/services/`）

```
services/api/exitReadiness/       erlApi.ts / request.ts / response.ts / dto.ts / README.md
services/service/exitReadiness/   erlService.ts   （Response ↔ DTO 转换，跨页面复用）
```

F2 的 `GET /erl/portfolio`、ERL Card 的 `GET /erl/card` 均归入 `exitReadiness/` 域（**按后端接口归域，不按页面归域**）。

**服务方法**（编号见 §6）：

| 服务方法 | 接口 | 用途 |
|---|---|---|
| `shareGapAnalysis({ companyId, period })` | **接口 27** `POST /erl/gapAnalysis/share` | A1 Gap 区块的 `Share to founder`，**仅管理端**；成功后本地把 `shared` 置 true，按钮随之置灰（文案不变） |
| `discardDraft({ companyId, period, portal, dimension })` | **接口 28** `DELETE /erl/assessment/draft` | B 填报页 `Reset`：连草稿行一起删除（附件 → 答案 → 草稿行，§6.3 接口 28）；**无二次确认** |
| `getDimensionConfig()` | **接口 23** `GET /erl/dimension/config` | **当前 `status = 'Active'` 的维度集合**（维度列表 + `sortOrder` + `weight`）；`useDimensionConfig` 与 C6 共用 |
| `saveDimensionConfig(items)` | **接口 24** `PUT /erl/dimension/config` | **整组保存**维度集合 + 排序 + 权重，服务端校验 **`Active` 行**合计 = 100.00；**就地整组替换，缺席维度置 `Inactive`，不产生版本** |
| `getAssessmentHistoryDetail(assessmentId, { dimension })` | 接口 8（可选 `dimension` 入参） | B3 从带维度的历史列表进入时只渲染该维度 |

### 8.4 关键交互

| 交互 | 设计 | PRD 依据 |
|------|------|------|
| **A1 ERL Card 内容** | **卡头右上 `Full View ›`** → A4（`/exitReadiness/scoreDetails?companyId={id}&period={period}`），**两端都渲染**。卡头标题 `Exit Readiness` 下加一行 `Through {季度}`（取接口 1 `period`，为空或加载中不显示）。卡体自上而下：**`Overall Score`**（全站不出现 `Composite Score`；**加权** `X/9`，tooltip 列出所用权重；大号数字与 `X.XX points out of 9.00`（两位小数））+ 当前 Stage 徽章 + **Gap 区块**（见下一行，常驻渲染）+ **维度列表**（按接口 1 返回的维度配置**动态渲染**，条数不固定；每行：维度分 `n/9` **整数** + `Level n` 标注 + `View Details →`；每行下加提交信息条，见「A1 维度行提交信息条」行）+ **雷达图（仅管理端）** + **雷达图正下方链接 `View Top GSV Quartile & External Benchmarks ›`**（→ `/exitReadiness/benchmark?companyId=`**`[&period={period}]`**，整条由接口 1 的 `benchmarkUrl` 下发；**仅管理端**，与雷达图同一端裁剪条件）。**管理端额外**：每维 GSV 分与 Perception Gap。不渲染状态徽章与 BPMM。该期次一个维度都没提交时照常渲染上述组件（综合分 `N/A`，各维度行走行内空态），不设整卡空态；`period == null` 时 `Reporting period unavailable.` 单独常驻显示（只剩防御分支可达，§9） | §3.1 / §3.5 + 原型 |
| **A1 维度行 `There is a draft`** | 该维 `hasDraft = true`（卡片这一卷有未提交草稿：管理端 GSV 卷、公司端 Founder 卷）时，维度行显示琥珀 **`There is a draft for {卡片季度}`**（如 `There is a draft for Q3 2026`；lucide `file-clock` 16px 图标 + 14px / 600，`#E1990F`）：**空态行**放在左侧、右侧 `Start an Assessment ›` 照常；**有分数的行**放在分数那一行左侧、分数仍靠右。两端都显示；无草稿时空态行只剩右侧 `Start an Assessment ›`、有分数的行不变。提示**可点**，落点与该行 `Start an Assessment ›` 相同（填报页） | 需求方（空态行即原型形态；有分数的行原型未画，需求方选定也显示） |
| **A1 维度行提交信息条** | 每条维度行下一条信息条，展示端 = 管理端 GSV、公司端 Founder（与该行分数同一端）：该端本期未提交（该端分数为空，与该行空态同一判据）⇒ **`Information Not Submitted for this quarter`**；已提交 ⇒ **`Information Last Submitted {MMM. D, YYYY} \| {N days ago}`**（如 `Information Last Submitted Aug. 15, 2026 \| 54 days ago`），时间取接口 1 维度项 `lastSubmittedAt`（UTC），天数按浏览器本地日历日算、当天为 `today`。有分数但后端没下发 `lastSubmittedAt` 时整条不显示 | 需求方 |
| **A1 Gap 区块** | 区块头：标题 **`Gap Analysis & Suggested Actions`** + **`AI GENERATED`** 标签；右侧两个按钮 —— **`View details`**（弹 `GapAnalysisDetailModal`，**按维度分区**列出该维的 gap 与 `actions[{title}]`；每条 gap 只显示标题）、**`Share to founder`**（**仅管理端**，调接口 27；**门槛未达成时置灰**，置灰时**不挂任何 tooltip**，还差哪些维度由区块底部那句常驻提示承担）。<br>区块体：**期次 chip**（如 `Q2 2026`，取接口 17 的 `period`）+ 计数文案 **`{n} of {total} dimensions have gap analysis for {period}`**（`total` = 当前 `status = 'Active'` 的维度集合的维度数，**不写死 5**）；**期次行下方**：有维度处于 mismatch 态时出一条**面板级琥珀告警**（三角图标），标题 `Question bank updated — new-version submission pending`，正文 = `The question bank has been updated.` + 逐维 `{缩写}: {Founder / GSV} has not yet submitted the new-version questionnaire for {期次}.`（公司端主语一律 `One side`）+ 收尾 `The questions no longer match, so gap analysis for this dimension (these dimensions) is unavailable until both sides re-submit.`；只点名 mismatch 态的维度（未提交优先，灰点维度不点名），没有 mismatch 维度时整条不出；其下**每维一张小卡**，卡内一个圆点 + 一行文字，**五态**（优先级**写死**、不靠隐式短路）：<br>· 灰点 + `Not submitted` —— `bothSubmitted = false`<br>· **绿点（与 ready 同绿，方向只靠琥珀字）+ `New version pending (Founder)`**（管理端括号内按 `mismatchSide` 点名 `Founder` / `GSV`，公司端只出 `New version pending`、不点名）—— `questionSetMismatch = true`（两端答的不是同一套题 ⇒ 不可比，该维未送进分析）<br>· 蓝点 + `Analyzing…` —— `analyzed = false`（另有 `dimensionStale` → `Updating…` 一态，后端恒发 `false`，实际不出现）<br>· 绿点 + `Gap analysis ready` —— `hasGap = true`<br>· 绿点 + `No Gap` —— 其余<br>⚠️ **`bothSubmitted` / `questionSetMismatch` / `hasGap` 是三条互相独立的信息，前端不要合并成一个枚举字段**；**mismatch 必须排在 `hasGap` 之前** —— 旧产物未被本轮覆盖时两者会同真，此时显示 mismatch、旧条目不渲染。<br>区块底部提示：**`Share unlocks once gap analysis is available for all {total} dimensions in {period}.`**<br>数据全部取**接口 17** 的 `shared` + `dimensions[].{code, abbr, bothSubmitted, questionSetMismatch, mismatchSide, hasGap}`。<br>本区块只呈现 gap 与建议动作，**不展示 Strengths**（`strengths[]` 出参已摘除） | 原型 + PRD §3.6 |
| **A1 Share 后的状态与复位** | **按钮文案恒为 `Share to founder`，已分享只置灰不改字**，两端都不显示分享人 / 时间等次级文字；**任一端重新提交后 `reconcile` 新建未分享记录，接口 17 的 `shared`（= 最新记录 `.shared`）为 `false`**（已分享记录不变，I1），按钮回到可点态。**公司端**：`shared = false` 时接口 17 直接返回空态，卡片内该区块显示 `No gap analysis shared yet.`，**不渲染** `View details` / `Share to founder` | 本设计 |
| **A1 卡片位置** | 占据**原 DI 卡片的位置与栅格宽度**，即两列布局的**右列**（DI 下移到左列 FI 之后，§8.6）；与左列 Financial Intelligence 卡等宽、顶部对齐 | §3.1 |
| **A1 公司端裁剪** | 公司端卡片**不渲染**：GSV 维度分列、Perception Gap 列、雷达图、**雷达图下方的 `View Top GSV Quartile & External Benchmarks ›` 链接**、**Gap 区块的 `Share to founder` 按钮**。列宽随之收缩为「维度名 + Founder 分 + View Details」三列，**不留空列**。⚠️ **`Full View ›` 两端都渲染**，不在裁剪之列 | §3.5「创始人只能查看自己的分数」「该图仅在 Portfolio 端显示」 |
| **A2 雷达图规范** | **仅线条无填充**、每条序列不同色、**有图例**、**中心轴隐藏**；**顶点数与顺序按当前 `status = 'Active'` 的维度集合动态生成**（`sortOrder` 决定顶点顺序）；**维度数 < 3 时整块不渲染**；**无数据也照画** —— 渲染门槛只看「管理端 + 维度数」，不看 `radarSeries` 有没有序列，无提交时画出网格与顶点名（无折线、无图例行）；域 `0–9`（含 0）；**悬停数据点显示该维度 + 该 perspective 的精确分数**。**仅在管理端渲染** | §3.5 |
| **A2 序列可扩展** | `series[]` 由后端下发，前端按数组渲染，**不硬编码 4 条** —— 后续新增 perspective 无需改前端 | §3.5「预留后续新增 perspective 的能力」 |
| **A3 模板参数化** | **`useDimensionConfig` 从接口取维度元数据**（`code` / `name` / `abbr` / `sortOrder`），页面按 `:dimension` 在返回列表里查；`:dimensionCode` 不在配置表内（压根没这个 code）时走 404 空态；**`status = 'Inactive'` 的维度不走 404** —— 行仍在表里，历史提交照常渲染并标 `Retired`，仅**不允许新建填报**（⚠️ 实现注意：`useDimensionConfig` 走的接口 23 **默认只返 `Active`**，照此实现停用维度会查不到而走 404 —— A3 需**单独带 `includeDeactivated=true` 取配置**，或改由接口 2 的 `header` 直接下发该维元数据（更省一次请求））。**禁止**按维度硬编码分支文案 | §3.2「同一套模板，通过 dimension 参数驱动」 |
| **A3 Founder / GSV Tab** | 双 Tab 切换逐题明细；**公司端不渲染 GSV Tab**（且后端拒绝该请求） | §3.2 |
| **A3 元数据栏** | Period / Submitted By / Role / Submitted At。**两端一律「该端该期次无提交（`submission == null`）⇒ 元数据栏整条不渲染」**，屏上只留下方那句 `No {端} submission for this period.`，不显示占位符。实现：`DimensionPage` 渲染条件为 **`detail?.submission`**；组件 `SubmissionMetaBar` 的 **`submission` 入参为非空**、**无 `fallbackPeriod` 入参**。**与 A4 卡内四格同一条规则**（§8.4「A4 元数据栏」） | §3.2 |
| **A3 页头分数** | 页头第三行**只有 `{n} questions`**，本页**不展示任何维度分**（无已答数、Era 徽章、止步 level、双端分数栏与 Overall Score）；有草稿时页头右侧出草稿提示 | §3.1 / §3.2 / §3.5 |
| **A3 `View history`** | 跳 `/exitReadiness/history?companyId={id}&period={period}&dimension={dim}&from=companyOverview,dimension`（本页当前期次一并透传；`from` 写死，B3 面包屑 = A3 的面包屑 + `History`，再到详情页是 `… › History › Record`），**限定当前维度**。提交单元是**单个维度**，列表天然只有该维的记录；无 `Completion` 列，分数列即该维 Overall Score。列表页头标注当前维度（口径见 §6.3 接口 7），无 `Clear` 入口 | §3.2 |
| **A3 `+ New`** | 公司端跳 B1、管理端跳 B2，带当前 `period` 预选 + **`?dimension={code}`**。**填报单元＝单个维度**，从维度页进去**只填该维度**，PRD §3.2「发起该维度新一轮评估」按字面落地。左侧有可点击的 `There is a draft`（`header.hasDraft`；管理端只在 GSV Tab 显示，`+ New` 两个 Tab 都在） | §3.2 / §3.3 |
| **A3 面包屑** | 管理端 `Portfolio Companies › {公司名} › {缩写} Score Details`（公司端无首级），`{公司名}` 回 Company Overview | **§4**（§四「导航一致性」） |
| **A3 维度间跳转** | 页头提供维度 chip 切换器，不必回卡片；**chip 数量与顺序按当前 `status = 'Active'` 的维度集合渲染** | 本设计（模板页自然延伸） |
| **A4 可达性** | **公司端与组合端都可达**。入口：两端 ERL Card 右上 `Full View ›`；组合端另有 F2 ERL Tab 的 `View ›`。页面按端类型裁剪（见下「A4 双端呈现」「A4 公司端」） | PRD §3.5 / §3.7 + 原型 |
| **A4 页面结构** | 自上而下：**面包屑**（见下「A4 面包屑」）`Portfolio Companies › Score Details` → **H1 `Score Details`（页头到此为止：无综合分、无 Era/Stage 徽章）** → **维度横向 Tab**（标签 = `dimensions[].abbr`，顺序与张数按接口 22 返回；**末位是基准 Tab**）→ **`GSV` / `Founder` 药丸切换**（组合端才有，`GSV` 在前且默认选中）→ **当前维度的单张卡**（卡头 + 四格元数据栏 + 该维逐题列表）；容器宽度与 A3 一致。⚠️ **无页级 `+ New` / `View history`**（在维度卡卡头）；接口 22 不下发页级 `header` | 原型 `/readiness/overall` |
| **A4 面包屑** | 跟来处走：从 F2 进是 `Portfolio Companies › Score Details`；从 ERL Card `Full View ›` 进（`from=companyOverview`）是 `Portfolio Companies › {公司名} › Score Details`；公司端不出 `Portfolio Companies` 一级；末级不可点 | 原型 |
| **A4 双端呈现** | · **组合端**：维度 Tab 下方一组 **`GSV` / `Founder` 药丸**，**`GSV` 在前且默认选中**（原型口径，与 A3 的 `PORTAL_TABS` 顺序相反）；选中哪端就只渲染哪端。<br>· ⚠️ **取数**：管理端**不传 `portal`，一次请求取回双端**（`dimensions[].portals[]`，§6.2.1）；**切药丸 / 切维度 Tab（含末位基准 Tab）时重新请求一次接口 22**（入参不变；公司端没有药丸，切维度 Tab 同样重取），再从新数据里换切片；**点当前已选中的不发**；请求期间先显示旧内容加转圈、返回后替换；**切换触发的重取失败保留旧数据、页顶报错**（换公司 / 期次后的取数失败仍清空）；只在点切换时刷新，不轮询 —— 「同时呈现 GSV 与 Founder 的记录」（PRD §3.7）由此满足。某端该期次无提交时该侧走空态、不报错。<br>· **卡内空态文案按端生成**（`noPortalSubmissionText(portal)`）：**`No GSV submission for this period.`** / **`No Founder submission for this period.`** —— 管理端取**当前选中的药丸**，公司端恒 `Founder`。⚠️ **不要在卡内用 `No assessment for {period} yet.`** —— 管理端一次取双端，「GSV 有、Founder 没有」是常态，说「整个期次没评估」是错的；那句**只用于两处**：页顶的提示条（该期次两端皆无提交）与「一个维度都没有」时的整页空态。<br>· **公司端**：只有 Founder 侧，**不渲染药丸、不渲染 GSV 内容**（后端同样拒绝 `portal=GSV`，§4.2 / §4.3） | PRD §3.7 + 原型 + 需求方 |
| **A4 元数据栏** | 四格 **`PERIOD` / `SUBMITTED BY` / `ROLE` / `SUBMITTED AT`**（大写小标签），**渲染在维度卡内、不在页级** —— 维度级提交后**同一期次的不同维度可能绑不同题库版本、不同提交人与提交时间**，页级取不到一份正确的元数据；组合端切药丸时这四格随所选端整体切换。取值为**每维自己的** `submission`（单端取 `dimensions[].submission`、双端取 `portals[].submission`），均为该维该端最新一次提交、与卡内题目同源；**两端一律该维该端无提交 ⇒ 整条不渲染**（公司端看 `dimensions[].submission`，管理端看所选端 `portals[].submission`），只留卡内空态 `No {端} submission for this period.`；无占位符、无 `fallbackPeriod`。A4 不显示题集版本号（见「B 题集版本标注」） | 原型 |
| **A4 维度卡** | **维度为横向 Tab，一次只渲染一维** —— Tab 标签取 `dimensions[].abbr`，**顺序与张数按接口 22 返回**，默认选中第一项。<br>卡头 = 缩写徽章 + `{全称} ({缩写})` + **`{总数} questions`**（A4 只报总题数，不呈现已答数与「stopped at Level N」，**其它页面不受影响**）+ **`+ Add New`**（**仅 `GSV` 药丸下渲染**，公司端单端模式照常）+ **`View history`**（h 小写，原型原文）；`dimension.status === 'RETIRED'` 的 **`Retired` 灰标在 A4 保留**。<br>· 两个入口的 URL **一律取接口 22 出参 `addNewUrl` / `historyUrl`，前端不拼路径**；为 `null` 时不渲染；`addNewUrl` 在 GSV 卷上带 `&portal=gsv`、`historyUrl` 带 `&period=`（形状见 §6 接口 22）<br>· 卡体 = 四格元数据栏（见上行）+ 该维逐题列表 | 原型 + §3.3 + PRD §3.5 / §3.7 |
| **A4 卡头 `There is a draft`** | 该维 `hasDraft = true` 时，卡头 `+ Add New` 前显示同款 `There is a draft for {本页季度}`，**与 `+ Add New` 同显隐**（`hasDraft` 说的正是 `addNewUrl` 那一卷；双端模式下指 GSV 卷，切到 `Founder` 侧一起隐藏）；卡头一行放不下时操作区整块换到第二行（左对齐），无草稿时布局不变。提示**可点**，与 `+ Add New` 同一处理（同样带 `from` 来源参数） | 需求方 |
| **A4 逐题行** | 题干 + 次级行 **`{eraLabel} · Source: {evidenceSource}`**（level 信息在此，**不按 level 分组、无组头 ✓ / `Stopped here`**）+ 右侧**作答徽章三态**（**三态不得合并**）：`Yes` 绿丸 / `No` 红丸 / `yesNo === null` **灰圈减号 `Not answered`**。<br>备注与附件是题干下方两个**大写小标签块** `NOTES` / `ATTACHMENTS`；**附件 chip 显示 `{文件名} {体积}` 并带下载按钮**，下载走既有 `storageService.getFileLink(fileId)` 现取预签名 GET 链接（**无新接口**）。<br>⚠️ **A4 不与 A3 复用同一个 `QuestionRow`**：A3 是可作答的填报行、A4 是只读明细行，两者形态不同 —— A4 侧为 `ScoreQuestionRow.tsx` | 原型 + §3.2 / §3.3 |
| **A4 基准** | **维度 Tab 的末位挂一个基准 Tab**，标题 **`External Benchmarks & Top GSV Quartile`**（卡头带 `BQ` 徽章，D1 两张卡与 D3 同款），卡内直接是表格 / 空态；内容是**按维度的明细表**（行数随维度集合），复用 D1 的 `BenchmarkDimensionTable`；列头为 `DIMENSION` / `EXTERNAL BENCHMARKS` / `TOP GSV QUARTILE`（**D1 同名**）；**只有明细行、无表尾 `Average` 行**（组件无 `weights` 入参）。**该 Tab 仅管理端渲染**（后端对公司端亦不下发，§4.3）。⚠️ **判据是端类型而非 `benchmark == null`** —— 管理端但该期次没有基准记录时后端同样发 `null`，此时 Tab 照常在、卡内走空态 `No benchmark records yet.`；管理端切到 `Founder` 药丸时该 Tab 只显示一句 `External Benchmarks & Top GSV Quartile is recorded by GSV only.`。卡头右侧 **`+ Add New`**（→ D2）与 **`View history`**（→ D1），A4 由此成为基准页的**第二个**入口；两条都是 `?companyId={id}`**`[&period={期次}]`**（期次空则整段不拼、值走 `encodeURIComponent`）—— D1 的面包屑第二级「Score Details」靠这个参数回到用户来时那一期，不带则 A4 走服务端缺省期次（closed month 所在季度）。⚠️ **带的是本页 `shownPeriod`（= 接口 22 返回的 `period` 兜 URL 参数）、不是 URL 原参** —— URL 没带期次时，后端解出来的那一期才是本页真正在看的那一期。⚠️ 这两条**由前端拼**（编译期固定的站内路由），与维度卡那两条后端下发的动态 URL 不同；ERL Card 雷达图下方那条入口（§8.1.1）同时保留 | 原型 + §5.6.1 |
| **A4 与原型的三处有意偏离** | ① 原型 `+ New` 恒跳 GSV 问卷（`/assessments/gsv`）→ 本设计按端类型分流、下沉到卡头并带 `dimension`，URL 取后端下发的 `addNewUrl`；② 原型切端只换写死 mock → 本设计是真数据，缺一端时该侧走空态而不是假数字；③ 原型基准是**一对写死总分**（6.5 / 8.2）且两端都显示 → 本设计为**按维度明细**（条数动态）且**公司端不下发** | §4.2 / §4.3 / §5.6.1 / §7.10-N2 |
| **A4 与 A3 的关系** | A4 **不是** A3 的替代：A3 是单维页，A4 做**逐题明细的全维平铺**，**只有逐题明细**，整体判断在 ERL Card 与 F2 上看。A4 **不重复** E2、Perception Gap 与雷达图。<br>A4 每张维度卡卡头有 `+ Add New` / `View history` 两个维度级入口；单维页仍从 ERL Card 的 `View Details →` 进，A4 卡头**不额外**加第三个跳 A3 的链接（避免与 `View history` 混淆） | 本设计（§8.5 的延伸） |
| **B 填报单元 = 单个维度** | **一次填报 / 一次提交只覆盖一个维度**。填报页**必须带 `?dimension={code}`**（缺参时按当前期次「尚未提交的第一个维度」兜底，仍只填一个维度）；页头显示 `{维度全称} ({缩写})` + 期次 + 端别；**页内无维度切换器**（换维度＝换一次填报，从 A3 / A4 的入口重进）。题库版本按**该维**绑定（同期次不同维度可能是不同版本，系统不阻止、不告警） | PRD §3.2 |
| **B 顶部按钮组** | 页面顶部固定四个按钮：**`Save as draft`** / **`Cancel`** / **`Reset`** / **`Submit`**。<br>· **`Save as draft`** = 把当前全部作答落盘（走接口 4）；**接口 4 只由 `Save as draft` 与 `Submit` 两个按钮触发**（见下「B 草稿落盘时机」）；成功 toast `Draft saved.`<br>· **`Cancel`** = **只离开页面**，草稿已在服务端，**不做任何数据操作、不弹确认**（回来源页；无来源时回 Company Overview）<br>· **`Reset`** = 调**接口 28** `DELETE /erl/assessment/draft`，连草稿行一起删除（附件 → 答案 → 草稿行，§6.3 接口 28）；**无二次确认**，点下去直接清，随后重拉接口 3 重绘为全新草稿<br>· **`Submit`** = 见下「B 提交」<br>只读态（公司端看 B2、或打开已 `SUBMITTED` 的记录）下四个按钮**均不渲染**。<br>⚠️ **该维度没有已发布的题时（接口 3 回 `levels = []`，屏上是 `No questions published for this dimension yet.`），`Reset` 与 `Save as draft` 置灰** —— 没题就没作答，存存不出东西、清也没东西可清；`Cancel` **不在此列**（它只是离开页面），`Submit` 本就由 `canSubmit` 把门（该情形下恒为 false）。前端判据与卡内空态 `DimensionSection` 的 `isEmpty` **同一条**（`levels.length === 0`），不得各写各的 | PRD §3.3 |
| **B `Save as draft` 置灰** | **没有改动时置灰**：待保存集合里有点下去真会发出去的题（作答、备注、附件改过且可发）才可点；只记「动过」、不与服务端比对（改过又改回仍算改动）；保存在途保持 loading、不变灰；保存失败保持可点；`Reset` 不跟（它清的是服务端草稿） | 需求方 |
| **B 草稿语义与上次保存提示** | **草稿是公司共享的、不区分账户**（草稿唯一索引不含用户维度，模型上天然成立，此处显式写明产品语义）：**A 保存后 B 打开看到的是 A 的内容，B 的保存直接覆盖 A 的**，无锁、无冲突提示、无版本合并。<br>保存信息分两处、分工不重叠，数据都取**接口 3** 出参 `lastSavedAt` / `lastSavedBy`（由 `updated_at` / `updated_by` join 用户表得到，**不新增快照列**）：<br>· **顶部 `Draft restored` 横幅**讲「进来时接手了谁的草稿」：`You are continuing the company’s shared draft, last saved {时刻} (UTC) by {姓名}.` + 右端 `Discard draft`；**进这份填报的首次载入判一次就钉住**，三条判据缺一不可：服务端 `status = DRAFT`、有 `lastSavedAt`、且有用户自己的作答（`hasOwnAnswers`：`answeredCount` 多于结转题数）。清空 / 提交 / 本次自己存过一次之后撤掉。<br>· **按钮行左下 `Draft saved {时刻} (UTC) by {姓名}`**（**不显示角色**）讲「这一页此刻的保存状态」；**只在本次访问内点过 `Save as draft` 且落盘成功之后才出** —— 刷新、退出重进都不显示。<br>**提交人以最终提交者为准**：`submitter_name` / `submitter_role` 在**提交时**快照 —— 即使草稿全程由他人保存，提交人只记录**点提交的那个人** | PRD §3.3 |
| **B 题库更新提示** | 版本锁定本体不变（评估恒按自己绑定的 `erl_question_config_version_id` 渲染与计分）。接口 3 出参含 `latestPublishedVersionNo` + `hasNewerQuestionSet`。<br>**强阻断二选一弹窗**（`QuestionSetUpdatedModal`）：**存过草稿**（接口 3 `status = DRAFT`）、`hasNewerQuestionSet` 且**草稿真有内容**（`answeredCount > 0`）时**一进页面就弹**，只有标题 `The question library has been updated` 与两颗按钮、**不可关闭**（无 ×、点遮罩与 ESC 都不关）：<br>· **`Submit draft content`** = 按**旧题库**就地交掉这份草稿（接口 5 带 **`autoAnswerNo = true`**）。没答完时服务端先把顺序上第一道未作答的题补成 No 使本维终止，再走**完全正常**的提交校验与计分，Share 与 Goldie 差距分析一切照旧；唯一仍会拦的是「该维 0 题」那条。前端刻意不看 `canSubmit`、也不弹「B 提交」的重复提交确认；提交成功后就地重拉接口 3（该行已翻 `SUBMITTED`，服务端按最新版下发空白问卷）。<br>· **`Access new question library`** = 走 `Reset`（接口 28）：服务端连草稿行一起删（附件 → 答案 → 草稿行）。⚠️ 这不是 §7.10-N3 否决的「保着答案换题面」。<br>· 空草稿（`answeredCount = 0`）期间又发布了新版时，前端在载入时就地走接口 28 删掉这条空草稿（屏上直接换新题库、弹窗不弹），删除失败也仍然不弹：那两条路对着一份空白问卷都没有意义。<br>⚠️ **失败不关弹窗**（用户可改选另一支）；两支都失败时页面上没有出路，已登记在 [`CIOaas-web/docs/待优化项.md`](../../../CIOaas-web/docs/待优化项.md)。 | PRD §3.3 |
| **B level 逐级解锁** | 每维度内**按 level（1–9）分组**，组头 `{Era 名} - {level}` + 题数/已答数 + 状态图标：<br>· `CLEARED` → **折叠 + ✓ Check**（PRD §3.3 原文「该 level 折叠并显示 Check」）<br>· `ACTIVE` → 展开，可作答<br>· `BLOCKED` → 展开，组头标 `Stopped here`；**首个 No 之后的题禁用、之前的仍可改**（非整级只读）<br>· `LOCKED` → **整组不渲染**（后端也不下发题面，§6.3）<br>一次填报只有**一个**维度：每维一条 `erl_assessment`、各自推进，页面上不同屏出现多个维度 | §3.3 |
| **B 逐题解锁** | 在逐级解锁之内再加一层：按渲染顺序只有**第一道未作答的题**及它之前的题可答，其后全部禁用（首个 No 之后照旧禁用，那道 No 自己可改回 Yes）。跳着答的存量草稿：下面已答的题照样显示、但锁住，等上面补齐 | 需求方 |
| **B 答 No 后后面答题全部重置** | 答 No（含展开已折叠的 `CLEARED` level 把 Yes 改成 No）**当场**清空它之后所有题（同级 + 后续 level）的作答、备注、附件，不弹确认、不提示；改回 Yes **不恢复**，从下一题起重新往下答；载入草稿时首个 No 之后的存量作答按未作答展示；落盘时服务端一并删除 | 需求方 |
| **B 解锁反馈** | 某 level 最后一题答完且全 Yes → 该组**动画折叠 + 打勾**，下一组随即展开并滚动到视口；出现 No（不必答完该 level）→ 该组标 `Stopped here`，该 No 之后的题禁用，下一组**不出现**，并提示 `Dimension score: {levelScore}/9`（⚠️ 该数**直出接口返回的 `levelScore`**，前端一律不自行推导 —— 稀疏题库下按 `level−1` 推会算错） | §3.3 |
| **B level 进度指示** | 每维度分组顶部一条 **1–9 level 进度条**：已通关 level 实心、当前 level 高亮、未解锁 level 置灰；旁标 `Founder Era 1–3 / Harvest & Growth 4–6 / Exit Era 7–9` | 本设计 |
| **B 证据/备注字段** | 折叠式次级输入，**视觉从属于 Yes/No 选择，不呈现为必填**；占位文案 `Add evidence or notes (optional)` | §3.3（「可选」明文）+ 本设计 |
| **B 附件上传** | **轻量小图标**紧邻备注，不喧宾夺主；已传文件以小 chip 列出（文件名 + 大小 + 删除 + 失败重试）；**选择文件时本地校验 ≤10MB**，超限不上传并提示 `File exceeds the 10 MB limit.`。**B1 / B2 两端渲染完全一致**（均为逐题上传），不做端区分 | §3.3「单个最大 10MB」+ 本设计 |
| **B 来源标签** | 每题显示 `Source: {evidenceSource}`，空显示 `—` | §3.3 / §3.4 |
| **B 草稿落盘时机** | **接口 4 只由 `Save as draft` 与 `Submit` 两个按钮触发**，作答 / 改备注 / 传附件本身**一律不落库**；草稿期的解锁推进走**接口 29**（只算不存、零写入，§6.3），**解锁进度与维度分一律采用服务端返回值、前端不本地推断**（§6.3）；保存中 / 已保存状态在吸底条提示。<br>⚠️ **不做**未保存离开拦截（`<Prompt>` / `beforeunload` / `Cancel` 与切期次二次确认 / `Unsaved changes` 常驻），也**不做**浏览器本地草稿缓存与 `Restore unsaved answers?` 恢复提示 —— 口径是**「没点保存就是没保存」**，**答一半关标签 / 刷新 / 切期次即全部丢失**，是**刻意接受**的后果 | §3.3「支持保存进度、稍后继续」（「无数据丢失」以用户自己点 `Save as draft` 为前提）+ 本设计 |
| **B 提交** | 提交按钮在**顶部按钮组**与吸底条各一处；**启用条件直接取接口 3/4 的 `canSubmit`**，门槛为「**本维度到达终止态**」，禁用 tooltip 说明**本维还差哪一级**（`Keep answering Level 4`）。<br>**提交确认弹窗分两种文案**：<br>· **首次提交**（该期次该端该维 `submissionCount = 0`）：提交后锁定为只读、如需修改要新建提交、下一步是对方独立评估后出现对比<br>· **重复提交**（`submissionCount > 0`）：标题 `Submit again?`、正文 `An evaluation for this quarter has already been submitted. Do you want to submit again?`、主按钮 `Submit again`（不提 source of truth，见 §13-Q30） | §3.3「激活提交按钮」 |
| **B 期次** | 期次选择器（季度 + 年份两个下拉，选项写在前端：季度 Q1～Q4、年份当前年 ±15）。URL 带合法 `?period=` 时以 URL 为准；否则**默认打开「当前季度」= 关账月所在季度**（取接口 6 `currentPeriod`，与 A1 / A3 / A4 缺省期次同一口径，取到后同切下拉一样回写 URL）；接口失败或未下发时兜底为当前自然季度（UTC，`currentErlPeriod()`），兜底值不回写 URL。**未来季度照常可选、可答、可存草稿、可提交**，题库更新弹窗照常弹 | 需求方 |
| **Yes/No 呈现** | 填报页每题渲染 Yes / No 两个按钮（**唯一的作答控件**）；A3 / A4 逐题列表右侧显示 `Yes` / `No` 徽章。所有题都是 Yes/No，没有「不计分的题」这个概念 | §3.3 / §3.4 |
| **题数与已答数说明** | A3 页头只有 `{n} questions`，A4 卡头只报总题数；填报页不显示题数与已答数；无维度分说明 tooltip（§13-Q31） | §7.1.1 |
| **C6 `Dimension Configuration`** | 配置页**第二个顶层 Tab `Dimension Configuration`**（与 `Question Library` 并列）。**面板自上而下五块：面板头 / 新增栏 / 主列表 / 规则提示 / `Deactivated Dimensions` 区块**。<br>**① 面板头**：**左侧**标题 + 说明 `Configure the Exit Readiness dimensions and their weights in the overall score. The total must equal 100%.`、**右侧** `Total: {n}%` + **`Save`** 按钮。页面**恒**带 `includeDeactivated=true` 取数，停用行由底部常显区块承载（见 ⑤），不设 `Show deactivated` 开关 —— 开关自身会成为脏态（开/关要不要确认、开着时提交集合算不算变化都得单独定义），常显区块让「展开」不再是一个动作。<br>**② 面板头下一行 = 新增栏**：`Dimension name` 输入 + `Abbreviation` 输入（**1–8 字符**，否则直撞 `varchar(8)`；新增维度**不做任何重名 / 重缩写校验**）+ **`+ Add`** 按钮。`code` 由**服务端生成**（`{Abbreviation 前 3 位}{4 位随机}`，§5.1.3），**页面不展示、用户不可指定**；`code` **永不改变**，**改 `Abbreviation` 也不会带动它**（它是 `erl_assessment.dimension_code` 等历史数据的关联键，§5.1.3）。<br>**③ 面板体 = 卡片行列表**（取**接口 23**，按 `sortOrder`），**只渲染 `Active` 且未删除的行**，每行：**拖拽手柄**（改排序）+ **`Name (ABBR)`** 文本 + **权重输入（带 `%`）** + **铅笔**（进入行内编辑）+ **行尾图标三态**，判据是 **`row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`** —— `deletable` 由**接口 23** 下发（该 code 从未进入任何已发布题库版本的维度快照 ⇒ `true`），**前端不自己算**；**只有垃圾桶弹二次确认，两种电源按钮点了直接生效**；三态按钮的悬浮提示一律是原生 `title`（`deleteDimensionTip` / `deactivateDimensionTip` / `undoRestoreTip` = `Delete` / `Deactivate` / `Undo restore`），文案逐字取自 `CIOaas-web/src/pages/exitReadiness/components/constants.ts`：<br>　· **垃圾桶 = 删除**（`canDelete && !isRestored`）：`Modal.confirm`，标题 `deleteDimensionTitle` = `Delete dimension?`，正文 `This will remove {name} and its weight allocation from the ERL configuration. This action cannot be undone.`（`{name}` 加粗），OK 文案 `Delete`，焦点落 `Cancel`，aria-label `Delete dimension`；<br>　· **电源按钮 = 停用**（`canDelete === false`）：点了直接停用；悬浮提示为原生 `title` `Deactivate`，aria-label `Deactivate dimension`；<br>　· **电源按钮 = 撤销恢复**（`isRestored` —— **本次会话里刚从停用区 `Activate` 回来的行，即便 `deletable = true` 也走这一支**）：点了直接撤销恢复；悬浮提示为原生 `title` `Undo restore`，aria-label **`Undo restore`**。<br>　⚠️ **第三态是防误删设计，不是实现细节**：真删在本页**没有**恢复入口，而「恢复一行 → 想撤销 → 点行尾最近的按钮」是一条高频路径；若那个按钮是垃圾桶，一次误点就把维度连历史一起葬掉。tooltip 之外还得有 ④ 那段提示，否则用户只看到「这一行的图标跟别的行不一样」。主列表不显示 `code`、无状态列，**只渲染 `Active` 行**，停用行由底部常显区块承载（见 ⑤）。<br>· **行内编辑态**：`name` 输入 + `abbr` 输入 + 权重输入 + 行内 **`Save` / `Cancel`**。⚠️ **行内 `Save` 只是把这一行的编辑提交到本地状态，不调任何接口**；**只有右上角的 `Save` 调接口 24**，整组就地替换，不产生版本。行内可改的只有 `name` / `abbr` / `weight` —— `code` 不可改、也不显示<br>· **电源按钮 = 停用 = 软删**（置 `status = 'Inactive'`，行与 `weight` 保留、可恢复）：点击后本地标为停用，右上角 `Save` 落库时它**不出现在提交的 `dimensions[]` 里**、其 code 进 `deactivatedCodes[]`，服务端据此置 `status = 'Inactive'`；**行与 `weight` 保留**，历史提交记录**照常显示并标灰色 `Retired`**（由 `status` 列**直接判定**）；该行随即出现在底部 `Deactivated Dimensions` 区块里，可 `Activate`。<br>· **垃圾桶 = 删除**（只在 `deletable = true` 的行上出现）：确认后本地标为已删，右上角 `Save` 时其 code 进 **`deletedCodes[]`**（**显式点名，不是靠「缺席」表达** —— 缺席只表示停用），服务端置 **`deleted = true`**。此后该行**从页面彻底消失**：主列表没有、`Deactivated Dimensions` 区块也没有、**没有恢复入口**；库里行与 `weight` / 名称 / 缩写原样保留（历史按 `dimension_code` 仍解得出），`dimension_code` **永久保留占用**（不会被重新分配给新维度，§5.1.3）。**二次确认文案必须写明不可恢复**（即上述 `Delete dimension?` 弹框）—— 这是产品里唯一一个不可撤销的维度动作，与旁边那个「随时能 `Activate`」的电源按钮只差一个图标，不写明必被当成停用点。<br>**⚠️ C6 本地行模型与提交语义（不写死就会出僵尸维度）**：本地数组同时存在五类行（接口 23 来的 `Active` 行 / 来的 `Inactive` 行 / `+ Add` 产生的**无 code** 行 / 被电源按钮标记停用的行 / **被垃圾桶标记已删的行**），故：① **`rowKey = dimensionCode ?? localId`**（`localId` 前端生成、仅本地存活，**提交时作为 `clientRef` 上行**）—— 拖拽排序、行内编辑、二次确认弹框都靠它定位；② **`isNew = !dimensionCode`**，提交时转为 `isNew: true` + `clientRef`；③ **`isDeactivated` 是独立本地标志位**，决定该行进 `dimensions[]` 还是进 `deactivatedCodes[]`；**③' `isDeleted` 是另一个独立的本地标志位**（与 `isDeactivated` **并列、不复用**），另存服务端下发的 **`canDelete`**（= 接口 23 的 `deletable`，决定这一行给哪个图标）。⚠️ **一行在提交时只能进三个桶之一**（`dimensions[]` / `deactivatedCodes[]` / `deletedCodes[]`）—— 进两个即触发服务端的 ⑩ 号校验（§6.4-3）；把删除塞进 `isDeactivated` 或反过来，落库会变成另一个动作，而 UI 上两者只差一个图标、**测不出来**。⚠️ **新增但未保存的行没有 code，垃圾桶对它是直接从数组里抹掉**（不进 `deletedCodes[]`，那个数组只收「已有维度」的 code；服务端根本不认识这一行，点名它只会撞 ⑧ 号校验 `Unknown dimension code`）。**权重合计（`Total`）排除已删行与停用行**；④ 常显区块里**看得见**的停用行，没点 `Activate` 就仍进 `deactivatedCodes[]`，**不得混进 `dimensions[]`**（否则全部被误恢复，且它们原样保留的 `weight` 会把合计冲爆）；⑤ **保存成功后必须用出参整体替换本地数组**（丢弃全部本地临时行，按 `created[{clientRef → dimensionCode}]` 接管服务端下发的 code），**不得增量合并** —— 否则用户不刷页再点一次 Save，那些行**仍然没有 code** ⇒ 再建一批新行、上一批因缺席被软删，**每多点一次 Save 多一批僵尸维度**；⑥ **整组 Save 失败（含 409 / 500）时不得清空本地编辑态** —— 行内 `Save` 不调接口，用户可能已改了十几行。<br>**④ 列表下方的规则提示**（**有启用维度时才显示**）：`dimensionConfigDeleteHint` = `Dimensions already published in a question set cannot be deleted — deactivate them instead. Deactivated dimensions are excluded from the weight total and from new assessments, while past records stay intact.`。⚠️ **这段不是装饰**：垃圾桶与电源按钮同列出现、只差一个图标，而后果一个可逆一个不可逆，光靠 tooltip（要悬停才看得到）不足以让人在点之前知道差别。<br>**⑤ 面板底部常显 `Deactivated Dimensions` 区块**：区块标题 `Deactivated Dimensions` + **空态 `No deactivated dimensions.`**（**常显 ⇒ 必须有空态**）+ 停用行列表（虚线框里灰化的 `Name (ABBR)` + `INACTIVE` 标 + 行尾 **`Activate`**；不给拖拽手柄、铅笔，也不显示 `code` 与权重）+ 区块尾一段说明（**仅在有停用行时显示；区块标题与空态常驻**）`deactivatedSectionNote` = `Deactivated dimensions remain in historical questionnaires and cannot be fully deleted; they are hidden from new assessments and excluded from the weight total.`。⚠️ **区块里只有 `Inactive` 行，没有已删行**（§5.1.3：无恢复入口）；接口 23 对 `deleted = true` 的行**任何情况下都不下发**，所以这条在前端天然成立，**但不要为了「让用户知道删过什么」自己去补一个已删列表**，那等于把不可恢复的删除又变成软删。<br>**⚠️ 恢复口径**：取数恒带 `includeDeactivated=true`。点 `Activate` 把它从 `deactivatedCodes[]` 移到 `dimensions[]`，**必须原样携带接口 23 下发的 `dimensionCode`**（恢复的唯一判据就是该 code 命中一行 `Inactive`）—— ⚠️ **千万不能把停用行的 name/abbr/weight 拷进一个新行对象**，那会变成新增一个新 code 的维度、旧行仍停用，而 UI 上看起来「恢复成功了」。右上角 `Save` 后该行回到 `Active`；它原样保留的 `weight` 会破坏 100% 合计，**需在同一次 Save 里补齐**。停用行只有 `Name (ABBR)` + `INACTIVE` + `Activate`，`code`、最后一次被提交的期次、关联提交条数都不显示 —— 同名 / 同缩写的两行是合法的（§5.1.3），`dimension_code` 是唯一能把它们分开的东西，此时 `Activate` 分不清是哪一行。没有这个区块，§5.1.3「可再置回 `Active` 恢复」在前端不可达。<br>· **删除拦截**：已进入过已发布题库版本的维度**没有垃圾桶**，服务端亦硬拦（§6.4-3-⑨）。判据是「**是否进入过已发布题库版本**」而不是「**有无历史数据**」，保护对象不是那一行（软删下行不消失），而是**已发布题库版本的语义**（§7.11-④）。⚠️ **前端按 `deletable` 不显示垃圾桶只是体验，不是防线** —— 抓包能直接传 `deletedCodes`，服务端那条校验不可省。<br>· **`Save` 启用条件**（实现即 `dirty && total === 100 && rowsIssue === null && editingKey === null && !saving`；③ 的否决原因回一个 `DimensionRowsIssue` 并**渲染在 `Total` 左侧**，承载 `name` / `abbr` 为空、`abbr` 超长、无启用维度三档）：① **脏态**（维度增 / **删** / **停用** / 改名 / 排序 / 权重任一变化）② **全部 `Active` 维度**权重合计 = 100%（`Inactive` 行与已删行不计入）③ **`rowsValid`** —— 每行 `name` / `abbr` 非空、`abbr` **≤ 8 字符**、且**至少有一个启用维度** ④ **无行处于编辑态**（`editingKey === null`）—— ⚠️ **这条产品可感知**：任一行点铅笔进入行内编辑后，右上角 `Save` 就是灰的，必须先行内 `Save` / `Cancel`（另有提交中 `!saving` 的防重入）；不满足即禁用，`Total` 红色标注并提示 `Exceeds 100% by {n}%` / `Needs {n}% more`（二选一）<br>· **Save 走接口 24 整组保存**（维度集合 + 排序 + 权重），服务端校验合法性与合计 100.00，**保存出参只有一个需要二次确认的分支 `CONFLICT`（乐观锁）**；**就地整组替换，不产生版本、旧值不留存**<br>· **Save 不弹确认框，点了直接保存**<br>· 保存成功 toast `Dimension configuration saved.`，并**刷新 overview 页 / 雷达图 / 题库 Tab 的维度回显**<br>· 不进题库版本、**不激活 `Publish`**、走自己的 Save（§7.9） | PRD §3.8（`0333162`：维度可新增 / 删除 / 排序 / 改权重，总权重 100%）+ 需求方 C6 布局与 mockup（两个破坏性动作 + 常显 `Deactivated Dimensions` 区块）；⚠️ 原型为五维表格形态，**布局部分已过期** |
| **C7 题库版本历史** | 入口：`Question Library` Tab 操作区的 `View history` → `/exitReadiness/configuration/history`。**页面是「选一个版本 → 看那一版的整份题库」**，不是版本清单表。<br>**页头**：H1 `Question Library History` + 说明 `All questions across the Exit Readiness dimensions for the selected version.`；**右侧**同排 `Version` 标签 + 版本下拉 + `Back`（回配置页）。<br>**版本下拉**（取**接口 25**，按版本号倒序）**只列已发布（`PUBLISHED`）版本**：接口 25 的出参在**前端取数 hook `useQuestionVersions`** 里按 `status === 'PUBLISHED'` 过滤后才进下拉与默认选中；**接口 25 的契约不变**（仍返回 `DRAFT` + `PUBLISHED`）—— 「库里有没有草稿」是 `Publish` 按钮能不能点的判据来源，服务端不能替 C7 把草稿滤掉，而 C7 是它当前唯一的消费方，过滤放在页面侧的代价只是一个 `filter`。下拉的 placeholder 为 `No published versions yet`；选项文案两种：最新已发布 `v{n} — Current (published {日期})` / 其余已发布 `v{n} (published {日期})`。**默认选中最新已发布版本**（填报页正在用的那一版）；**没有任何已发布版本时**下拉置空、页体走空态 `No published question set versions yet.` —— 只有草稿的组织（如新建组织在第一次 Publish 之前）在 C7 上是空态，不是 bug。<br>**页体**（取**接口 26**）：**按该版本对应的维度配置顺序**（`sortOrder`，张数不固定）；该维度集合由**接口 26 出参 `dimensions[]`** 下发（数据源为 `erl_question_config_dimension_version` 的**发布当时逐维快照**，§5.1.5），**不取接口 23 的当前生效配置** —— 发布当时的每个维度**照常整卡展示**、连带它的题目一律照出（脏数据仍兜底出卡、name / abbr 退化为 code、不打标）；**卡头不显示 `Retired` 灰标**；**本页不调接口 23**，只读接口 25 / 26 的历史快照，与当前维度配置完全解耦。⚠️ **`TEXT.retired` 这个文案本身还在用**（`ErlCard` 的维度行与 A4 `DimensionQuestionsCard` 仍按 `status === 'RETIRED'` 打标）—— 只有 C7 不打。发布后新增的维度**不会**在旧版本上多出空卡。每个维度渲染一张卡，卡头左 `{维度全称} ({缩写})`、右 `{n} question(s)`；卡内表格列 `QUESTION` / `ERA BAND`（Era 徽章，三个 Era 三套配色：Founder `#E1990F` / Harvest `#DED87A` / Exit `#1E8E4A`）/ `SOURCE`（空值 `—`）。**维度内题目平铺、不打 Era band 组头行**（与 C1 有意不同：C1 的分组行是为拖拽服务的，C7 只读、分组只会把页面切碎）；某维在该版 0 题时卡片保留、内文 `No questions in this dimension for this version.`。<br>只读、无操作列（不提供回滚、不做版本间 diff——V1 不做，§12） | 原型+ §6.4 接口 25 / 26 |
| **只读态** | 公司端打开 B2、或打开已 `SUBMITTED` 的记录时，问卷渲染为只读（无输入、无提交条） | §3.3 |
| **E1 展示** | ERL Card 内为 **Gap 区块**（见上「A1 Gap 区块」），**常驻渲染**。只生成**一份**内容，GSV 团队可见，点 `Share to founder` 后 Founder 端才可见；前端不做措辞转换。维度详情页（A3）**不渲染差距分析**：接口 2 的 `gaps[]` / `actions[]` 照常下发、前端 service 照常映射，但无页面渲染；差距与建议只在 A1 `View details` 弹框里看 | §3.6 |
| **BPMM** | **A1 卡片不渲染 BPMM**，两端、不论有无数据；接口 1 的 `bpmmScore` 仍在契约里（恒 `null`） | §5 |
| **B3 历史列表** | 列序：**Period** / **Dimension**（仅未带 `?dimension=` 时）/ **Portal**（**仅管理端渲染** —— 公司端只有 Founder 侧数据，该列恒定值、无信息量）/ **Submitted**（取 `submittedAt`，**只到日** `M/D/YYYY`，同日多次提交屏上不分先后，B3 详情页同样只到日）/ **Submitted by**（`姓名 · 角色` 同行同字号）/ **`{缩写} Score`**；**无 `Fund` 列、无 `Completion` 列**，页头**无 `Clear` 入口、无计数**；行尾人字形，整行可点进详情。<br>· 分数列下方无次级文字，B3 列表不显示题集版本与止步 level；接口 7 不下发 `answeredCount` / `totalCount`（§13-Q31）<br>· **分数列 = 该维度的 Overall Score**：一枚 Era 配色药丸 `{level} /9 {Era}`（`0` 分为灰药丸 `0/9 —`）—— **不是加权综合分**（提交单元是单个维度，加权综合分在这里没有意义）<br>· 最近在前；无 `Current` 徽章、无高亮或降级，每行样式一致；同期次多条时屏上只靠行序（最近在前）看出哪条是 SOT<br>· **空态**：`PRESENTED_IMAGE_SIMPLE` 配图 + `No submitted assessments yet.`，且**连列头一起收掉**（全仓唯一这样的表）；**加载中仍留列头**；**取数失败时整块空态压掉、只留错误横幅** | §3.9 |
| **B 元信息栏** | 页头下方一条元信息栏，标签屏上大写：`PORTAL` / `ASSESSED BY` / `ROLE` / `FUND`。**打开页面就要有值**：`ASSESSED BY` / `ROLE` 取进页时恢复的那份有作答的草稿的保存人（接口 3 `lastSavedBy`），没有时退回**当前登录用户**（姓名 + 当前组织下的角色名），两格整体二选一、不各自兜底；`FUND` 取接口 3 出参 `fund`（该公司 Portfolio Name），取不到显 `—`。**Founder 卷不显示 `FUND`**，收成三格；GSV 卷四格 | 需求方 |
| **B 题集版本标注** | **前端任何页面都不显示 `Question set v{n}`**（接口 3 仍下发 `questionVersionNo`（供 `hasNewerQuestionSet`），前端不渲染；接口 7 与 `submission` 节点不含该字段，§13-Q31）。两端题集版本不一致只由 A1 Gap 区块的 mismatch 态（`New version pending`）体现；C7 版本下拉里的 `v{n}` 是题库版本本身，不在此列 | §7.10-13 / N2 |
| **B3 详情** | 点击某行进 `/exitReadiness/history/:assessmentId`，复用 A3 的题级布局呈现该次提交时的状态；从**带 `dimension` 的历史列表**（A3 / A4 卡头的 `View History`）进入时，URL 透传 `?dimension={code}`，**接口 8 有可选 `dimension` 入参**，页面**只渲染该维度**。提交单元本就是单维，故该参数在实现上恒等于该条记录的 `dimension`，透传只为页头标注与直链一致。URL 同时透传 **`?period={period}`**（列表页 URL 上有才带）。详情页**自身取数不用它**（题目与元数据都取该条记录本身），它只让详情页面包屑回列表那一级把用户送回**带同一期次**的 B3。⚠️ **这一跳只带 `period`、不带 `dimension`** —— 返回落到的仍是**全维混排**的 B3，`?dimension=` 过滤态不保留 | §3.9 |
| **C1 页面结构** | 页头：H1 `ERL Configuration` + 说明 `Configure dimension weights and the question library for each Exit Readiness dimension.`；页头右侧为**租户选择器**（数据取存量 `/api/web/organization/findByTree`，ERL 不另加接口）：组织树根节点下没有子组织（`subdata` 为空，如 Portfolio Group Manager）或取数失败时不渲染，与 `/settings` 的 Portfolio User Management 同口径。选中的组织只记在 URL 的 `?organizationId=` 上；选择器可见而 URL 未带值时默认取树的第一个组织。C 模块的接口一律把它作为 query 参数带上，进入 `add` / `edit` / `history` 子页时随 URL 带过去。维度配置保存过程中选择器置灰。其下**两个顶层 Tab**：`Question Library` / **`Dimension Configuration`**。`Question Library` 内自上而下：操作区（`Add New` / `Publish` / `View history`，**右对齐**）→ **维度 Tab（按当前生效配置动态渲染，非固定五个；已删除的维度不出 Tab）** → **题目表格**：列 `QUESTION` / `ERA BAND` / `SOURCE` / `ACTIONS`（另有**最左拖拽列**），按 **Era band 分组**、每组一条组头行（band 徽章 + `{n} questions`）。**维度 Tab 回跳定位**：进 `add` / `edit` / `history` 子页与从子页回来（`Back`、保存后回跳）都在 URL 上带 `?dimension={code}`（与 `?organizationId=` 一起透传），配置页拿它当维度 Tab 的**一次性种子** —— 该 code 在接口 23 当前配置里才采纳，否则落 `sortOrder` 首位；切 Tab 本身不回写 URL | §3.8 + 原型 |
| **C4 拖拽重排 + 改 Era band** | **同 band 内**：表格最左拖拽列拖动排序，松手即调接口 14 **写入草稿版本**（不影响填报页，直到 Publish）；行上不打徽章、不弹提示<br>**跨 band 移动**：直接改题目行内 `ERA BAND` 列的**下拉**，选中即调**接口 12 全量更新**该题，行随即移动到目标分组末尾。接口 14 **只做同 band 重排**（§6.4） | §3.8「拖拽重排…该顺序即评估中的必答顺序」+ 原型+ 本设计（警告提示） |
| **C3 删除** | `Modal.confirm` 二次确认（与 C6 删维度同款：无图标、antd 默认遮罩、焦点落 `Cancel`、琥珀 `Delete`）：标题 `Delete question?` + 正文 `This will remove the question from the {维度名} dimension. This action cannot be undone.`（维度名加粗） | §3.8 |
| **C5 草稿态线索** | 不显示版本条；有草稿时整页加浅色「编辑中」边框，与「无草稿即禁用」的 `Publish` 是仅有的两条草稿态线索 | §7.9-④ |
| **C5 Publish 按钮** | 页面右上角主按钮 `Publish`；**存在草稿版本即激活**（任意维度的任意变更，与当前所处 Tab 无关；**`Dimension Configuration` Tab 的改动不激活它** —— 维度集合 / 排序 / 权重走自己的 Save（接口 24）；配置无版本，只有题库一条版本线，**Publish 会把当时 `Active` 的维度逐维快照进 §5.1.5**）；禁用条件 `!hasDraft || library.loading`，无 tooltip、无变更计数；点击不弹确认，直接调接口 21，成功 toast `Published v{n}.` 并刷新列表 | §3.8 |
| **C5 离开页面** | 草稿是服务端持久对象、非表单脏数据，离开不拦截、不弹确认；⚠️ **例外**：`Dimension Configuration` Tab 是**普通表单脏态**（不是服务端草稿），未 Save 就离开**要弹确认** | 本设计（§7.9） |
| **D1 页头** | 面包屑跟来处走（`from` 链，同 A4）：从 A4 来是 `Portfolio Companies › Score Details › Top GSV Quartile & External Benchmarks`，从 Company Overview 基准入口来是 `Portfolio Companies › {公司名} › Top GSV Quartile & External Benchmarks`；`Score Details` 那一级，链接 `scoreDetailsUrl` 回 A4 **带 `&period=`**（URL 上带了就带回去）。标题下一句说明「Reference scores used to compare this company's Exit Readiness against the GSV top quartile and the **External Benchmarks** peer set. Each entry is kept as a dated record.」；右上 `+ Add New` → D2，**同样带期次**（`addUrl`） | §4 + 原型 |
| **D1 卡一：`Current Version`** | 卡头 `Current Version · {period}`（期次取**卡一实际显示的那条记录**，取哪条见 §7.8）；表格三列 `DIMENSION` / **`EXTERNAL BENCHMARKS`** / **`TOP GSV QUARTILE`**（`BenchmarkDimensionTable` 是 A4 末位基准 Tab 与 D1 两张卡共用组件，同一个概念两页同名）；⚠️ **无 `Average` 行** —— 三处一律只有明细行。**一维一行，行数按配置维度动态**；维度列 `**FRL** Financial Readiness`（缩写加粗 + 全称次级色）；分值格式 `6.5/9`，`/9` 次级字号；卡头下另有**一行提交元信息**：`Submitter: {姓名 · 角色}` · `Submission time: {YYYY-MM-DD}`（组件 `BenchmarkSubmissionMeta`，与 D3 详情卡共用；时刻 = 审计列 `created_at`，走 `formatErlIsoDate()`，为空显示 `—`） | 原型 |
| **D1 卡二：Record History** | 列 `PERIOD`（最新一条加 `LATEST` 徽章）/ **`SUBMISSION TIME`**（**真实录入时刻**：审计列 `created_at`，经 `formatErlIsoDate()` 渲染 **`YYYY-MM-DD`**，为空显示 `—`）/ `SUBMITTER`（姓名 · 角色）+ 行尾 `›`，整行可点进 D3 记录详情页（键盘 Enter / Space 同效）；按 **`created_at DESC NULLS LAST, id DESC`**（纯提交时间倒序，补录旧期次的那条也排在最前）—— 同期次可有多条**并列**，最近录入的排在前面，`LATEST` 徽章只给这个排序下的**首条** | 原型 |
| **D1 / D3 提交元信息行** | D1 卡一卡头下与 D3 记录详情卡内各有一行裸小字：`Submitter: {姓名 · 角色}` · `Submission time: {时刻}` —— 同一个组件 `BenchmarkSubmissionMeta`（`benchmark/components/`），两个标签与 D1 `Record History` 的列头**同取**一份源串 `BENCHMARK_META_LABELS`，别各写字面量。时刻取审计列 `created_at`、走 `formatErlIsoDate()` 显示 **`YYYY-MM-DD`**，为空 `—`。⚠️ **不复用 A3 / A4 那个四格 `SubmissionMetaBar`**（那是带灰底边框的盒子，这里是裸的一行两项）。 | 原型 |
| **D3 备注块** | `note` 在 `By Dimension` 卡内、维度表之下，复用 `.noteBlock` / `.noteLabel`；标签字面量 `Note (optional)`（私有 `.noteLabelCased` 关掉大写，不动 `TEXT.notesLabel`）；空则不渲染 | 本设计 |
| **D1 / D3 / D2 的期次返回上下文** | **口径**：期次在 D 模块**只作面包屑 / 返回按钮的返回上下文，除 D1 卡一外各页取数都不用它** —— D1 `Record History` 跨期次全量、D1 卡一按 URL `?period=` 挑该期次最新一条（无则取全库最近一条）、D3 按 `recordId` 打开、D2 的期次由表单自己填，除 D1 卡一外都**不按** URL 上的 `period` 过滤。页面取数用不到，**面包屑要用**；不带就等于把用户甩到服务端缺省期次那一期。落地三处：<br>· **D1 → 下游**：抽出一份 `periodQuery`，到 D2 的 `addUrl`、到 D3 的 `recordUrl(id)`、回 A4 的 `scoreDetailsUrl` **三条共用**。<br>· **D3 → D1**：从路由取 `contextPeriod`，面包屑第二级与右上 `Back`（正常态与错误态两处）回 D1 时带上。⚠️ **与本页「展示」的期次是两件事** —— 标题、面包屑末级、卡头 `By Dimension · {period}` 一律取**记录自身的 `record.period`**（属于哪一期是记录自己的事实），`contextPeriod` 只往回传、不参与本页展示与取数。<br>· **D2 → D1**：**保存成功**跳回 D1 时带上 `contextPeriod`；`Back` / `Cancel` 走 `history.goBack()` 原路退回，**不受影响**。<br>⚠️ 三处判空一律「期次空则整段不拼」，值走 `encodeURIComponent`。⚠️ **只带 `period`、不带其它上下文** —— 回到 A4 后当前维度 Tab 与 `portal` 药丸仍落缺省态 | 本设计 |
| **D2 独立页** | 路由 `/exitReadiness/benchmark/add`，页首 `< Back` 回 D1；标题 `Add Benchmark Record` + 说明「Enter the **External Benchmarks** and Top GSV Quartile reference scores (1–9) for each Exit Readiness dimension for a reporting period.」 | 原型 |
| **D2 表单** | `Period` 季度 + 年份两个下拉（缺省 closed month 所在季度）→ `Scores by dimension (1–9)` 表格（**每个维度一行** × 两列数字输入）→ `Note (optional)` 文本域（placeholder `Source of the benchmark data, peer set changes, etc.`）；底部右对齐 `Save Record`（主按钮）/ `Cancel` | 原型 |
| **D2 校验与返回** | **全部分数框必填**（`2 × 维度数` 个）、范围 1–9、**只允许整数**（前端 `onKeyPress` 拦非 `0-9` 字符 + `parser` 截断粘贴 + `precision={0}`，无整数校验文案；⚠️ **服务端未加整数校验**）；`Period` 必填并归一为 `{YYYY}Q{n}`；**同期次可重复保存**，前端无期次重复报错路径（catch 里把业务错误挂到 `Period` 字段的通用处理保留，其它保存失败仍走这条路）；保存成功回 D1 时**带上 URL 上的 `contextPeriod`**（期次空则不拼）并刷新两张卡 —— 否则 D1 的面包屑回 A4 又落到服务端缺省期次；`Back` / `Cancel` 走 `history.goBack()`，不受影响 | §5.6 / §6.5 |
| **F2 ERL Tab** | 与现有 5 个 Tab 同一套表格样式（`key='6'`）；列 Company / ERL Score / **维度列（按接口出参 `dimensionScores: [{ code, abbr, score }]` 动态生成**，列头取 `abbr`、列序取配置 `sortOrder`，**不硬编码**；**均为 level 整数 0–9**）/ Stage / View。① `ERL Score` = **加权两位小数 + 分母**，渲染 `7.20/9.00`（与 A1 同口径，整数补零），无分数渲染 `—`（**不是 `—/9`**）；② **`Stage` 列只渲染一枚 Era 徽章**（同色文字 + 该色 10% 薄底），**stage 整数不显示**，`0` 出灰徽章 `—`（与 `null` 的 `—` 同底色，靠同行 `ERL Score` 列区分）、`null` 出 `—`；③ **着色只给 `ERL Score` 与 `Stage`，维度列走中性色**；`ERL Score` 与维度列的 `0` 与 `—` 用不同底色，勿混（Stage 列例外，见 ②；§7.1 末段）；④ **不排序、不筛选** —— 无 Stage 下拉、分数区间框与列头排序器，F2 是一张纯展示表（服务端排序能力保留、`sortBy` 白名单随维度动态，前端恒不下发）；⑤ **页面不显示期次** —— 既不逐行挂在公司名后面，表格上方也**不放期次标签**（前端不发 `period`，各行按服务端逐公司缺省期次取数，各行期次可能不一致，已接受） | §3.7（Tab 与列）+ 本设计（排序）+ 原型 `/portfolio` ERL Tab |
| **F2 `View` 跳转** | 末列 **`View ›`**（文字 + 右尖角图标）跳该公司的 **A4 全维 Score Details 页**，取后端下发的 `detailUrl`（`/exitReadiness/scoreDetails?companyId={id}&period={period}`，**不带维度**），前端不拼路径 | §3.7「View（跳转到该公司的 Score Details 页面）」 |
| **响应式** | 桌面 + 移动均可用；表格类窄屏横向滚动、卡片单列堆叠、雷达图等比缩放。⚠️ 用户录入的长文本（题干 / 来源 / 备注）先限宽（flex 子项 `min-width: 0`、表格 `table-layout: fixed`），再加 `overflow-wrap: break-word`，只做后一步无效 | §4「所有页面覆盖桌面与移动端」 |
| **国际化** | 文案走 `locales/`，不硬编码中文 | 前端规范 |

### 8.5 ERL Card 与维度详情页的职责划分（对 PRD 的落地解释）

PRD 中「Scorecard」（§5）的展示项分散在两处，本设计的归属如下（需产品复核 → §13-Q8）：

| PRD §3.5 展示项 | 落在 ERL Card | 落在维度详情页 | 公司端可见 |
|---------------|:---:|:---:|:---:|
| 综合 ERL 分数（加权，文案 `Overall Score`） | ✅ | ❌（页头不展示分数） | ✅ |
| 当前 Stage 与 Era | ✅ | ❌ | ✅ |
| 本端维度分（level 整数） | ✅（列表，条数动态） | ❌ | ✅ |
| **对端维度分**（GSV 分之于公司端） | ✅（列表） | ❌ | ❌ |
| 每维度 Perception Gap | ✅ | ❌ | ❌ |
| Priority Gaps | ❌ | ❌（差距与建议只在 A1 `View details` 弹框里看） | — |
| 雷达图 | ✅ | ❌（本维不适用多维雷达） | ❌（仅组合端） |
| **基准入口链接 `View Top GSV Quartile & External Benchmarks ›`** | ✅（雷达图正下方；维度 < 3 时雷达图不渲染，本链接仍在原位） | ❌ | ❌（仅管理端，只在端裁剪这一层与雷达图同条件） |
| **A4 入口 `Full View ›`** | ✅（卡头右上） | ❌ | ✅ **两端都渲染** |
| 访问历史评估记录 | ❌ | ✅（`View history`） | ✅ |
| Gap Analysis & Suggested Actions | ✅（完整 Gap 区块，含 `View details` 弹框与 `Share to founder`） | ❌ | ✅ **仅 `shared = true` 后**（`Share to founder` 按钮仅管理端） |

依据：PRD §3.1 明确列出卡片内容清单（综合分 / Stage / Gap 摘要 / 维度列表 / BPMM / 雷达图），§3.2 明确列出维度页内容。「公司端可见」一列按 PRD「每维度 Founder 分**或** GSV 分（根据账户权限）」「创始人只能查看自己的分数」与「雷达图仅 Portfolio 端」收紧。

> **A4 基本不参与本表的划分** —— 它承载「逐题明细的全维平铺」+ 基准 Tab；**A4 页头只有 H1，不显示任何分数** —— PM 的「整体判断」在 F2 该行（`ERL Score` / `Stage`）与 ERL Card 上，进 A4 是为了看逐题依据。A4 是 F2 `View` 与两端 ERL Card `Full View ›` 的落地页；Scorecard 的其余展示项（Perception Gap / Priority Gaps / BPMM / 雷达图）一律不在 A4 上重复，见 §8.4「A4 与 A3 的关系」。**唯一例外**：A4 每张维度卡卡头承载 `+ Add New` / `View history` 两个**维度级操作入口**（不是展示项，见 §8.4「A4 维度卡」）。

### 8.6 Company Overview 三卡布局方案（PRD §3.1）

**PRD 要求**：

> Company Overview 页原有的 DI 卡片**放在 FI 卡片下**；DI 数据、打分**保留概览信息和入口**。
> 原 DI 卡片位置由新的 ERL 卡片替代。

即：**DI 不下线**，只是**让位**。

> ⚠️ **「位置」不是「顺序」**：不要读成「三张卡纵向排成一列」。**存量 Company Overview 本来就是左右两列**（`.btmContent{ display:flex; flex-direction:row; justify-content:space-between }`，`.finanStyle` / `.deveStyle` 各写死 `604px`，左 FI、右 DI），PRD 说的「原 DI 卡片的位置」指的是**右列**，「DI 放在 FI 卡片下」指的是 DI 落到**左列 FI 的下方**。原型 Company Overview 截图与这个读法一致。**两列布局是存量事实，不是本设计新引入的东西。**

三张卡的最终布局：

```
Company Overview 页（Revenue / Financials 两张通栏卡在上，不变）
  ├── 左列  ├── FI Card    ← 存量，位置不变（Financial Intelligence）
  │        └── DI Card    ← 存量，由右列移到左列 FI 之下；概览信息与下钻入口全部保留
  └── 右列  └── ERL Card   ← 新增，占据原 DI 卡片的位置与栅格宽度
```

落地方案：

1. **前端**（`CompanyOverviewPage.tsx`）：`bottomHtml` 内加两个列容器 —— 左列 `.btmLeft` 收 FI（Automatic / Manual 两个分支）+ DI，右列 `.btmRight` 放 `<ErlCard />`。**DI 的渲染条件 `DiStatus` 原样不动** —— 它仍按公司级开关决定 DI 卡显隐。
   - 列宽用 `flex: 1 1 0` 等分而**不写死 `604px`**：`.mainover` 内容宽 1232、列间距 24，算出来正好 604，与存量像素一致，但容器变窄时不会溢出。
   - 两个列容器**必须带 `min-width: 0`**：左列的 FI / DI 里有宽表格与长数字串，flex item 默认 `min-width:auto` 会被内容撑破，把右列挤没。
   - `.btmContent` 加 `align-items: flex-start`，让两列各自按内容高度收尾（右列 ERL 通常比左列矮）；`max-width: 1024px` 以下回落单列纵排。
2. **后端**：**无改动**，不设系统级开关 —— PRD 不要求隐藏 DI，没有任何东西需要开关来控制。
3. **不动 `diStatus` / `diWeight` / `fiWeight`**：这三个值仍影响 SDP 总分与 Company Settings 的模块页；卡片顺序是纯前端布局问题。
4. **Company Settings 的 Modules 页**：**无需加说明** —— DI 开关的效果没有被 ERL 接管，打开就显示、关闭就隐藏。

> ⚠️ **注意**：DI 卡片换列后，`CompanyOverviewPage.tsx`（已超 2300 行、DI/FI 分支混杂）的 JSX 结构调整范围不小，容易带出样式与栅格问题（如把存量两列栅格误压成单列）。该文件的拆分建议已记入待优化项。

---

## 9. 失败降级

| 场景 | 服务端 | 前端表现 |
|------|--------|----------|
| **展示期次缺省 = closed month 所在季度，该季度两端均无提交** | 接口 1 / 17 / 20 / 22 等所有「`period` 可选」的读接口，缺省期次一律取 **该公司 closed month 所在季度**（closed month 读 FI 每日 KPI 快照，ERL 域**复用 FI 既有服务、不自己算**）。该季度**两端均无提交** → 返回**空态**（分数 `null`、`dimensions[]` 按**当前 `status = 'Active'` 的维度集合**返回但分数全 `null`），**明确不回退到更早期次** | A3 / A4 显示该季度的**空态**（`No assessment for {period} yet.` + 去填报入口）；ERL Card 不设整卡空态，照常渲染有数据那套组件 —— 综合分 `N/A`、各维度行走行内空态（见 §8.4 A1）；期次 chip 照常显示该季度；⚠️ **不得**悄悄显示上一季的数据 —— 用户看到的期次标签必须和数据是同一个期次 |
| **closed month 取不到（无快照 / 快照无月份 / FI 抛异常 / 格式坏）** | 回退**当前自然季度**（UTC），FI 抛异常 / 月份格式坏打 WARN（含 `companyId`），无快照 / 快照无月份只打 DEBUG。⚠️ 该季度通常一份提交都没有 ⇒ 落到上一行的「该季度两端均无提交」走空态，**但期次是确定的** | ERL Card 走该季度的空态，**期次 chip 显示该当前季度**；`Reporting period unavailable.` 这句次级说明**只剩 `companyId` 为空这一条防御分支可达**。⚠️ **代价**：季度初财务尚未结账时，屏上会出现一个**财务尚未闭合**的季度标签（已知取舍） |
| 该公司无任何已提交评估 | 接口 1/2 返回空结构（分数 `null`、`hasAnyAssessment=false`） | ERL Card 照常渲染 —— 综合分 `N/A`（不出 Era 与 `X points out of 9`），维度行走行内空态（只有 `Start an Assessment ›`）；**管理端雷达图照画**网格与顶点名（无折线、无图例，仍受 ≥ 3 个维度门槛约束）；`hasAnyAssessment` 在卡片上无渲染方 |
| 只有 Founder 提交、GSV 未提交 | `gsvScore = null`、`perceptionGap = null` | **管理端**：该维走行内空态（`Information Not Submitted for this quarter` + `Start an Assessment ›`；管理端行分数取 GSV 端）；雷达图 GSV 序列不绘制。**公司端**：本就不展示 GSV 与 gap，页面无任何变化 |
| 只有 GSV 提交、Founder 未提交 | `founderScore = null`、`perceptionGap = null` | 管理端维度行显示 GSV 分，右下角标注 `Perception Gap: -`；**公司端显示与「无任何提交」相同的空态**（它看不到 GSV 那份，§4.2） |
| **维度分为 `0`（level 1 内即有 No）** | `levelScore = 0`（**不是 `null`**）、`terminatedLevel = 1`；**照常计入加权综合分** | 维度行显示 `0/9` + Era 处灰色 `—`（§7.3）；**分数格**不得显示为 `—` —— `—` 是「无数据」，`0` 是「有数据且很低」；Era 文案已相同，两者只剩分数格 `0/9` 能区分，混淆会让用户以为没填（§7.1 末段） |
| **某维在该题集版本内 0 题** | `levelScore = null`；该维按 `0` 计入综合分（权重仍计入合计、其余维度不归一化，同 §7.1）；**该维不可提交**（§6.3 校验 3） | 维度行显示 `—`；填报页该维度走空态 |
| 无基准记录 | `benchmarkPosition = null`、`records = []`、雷达图两条基准序列缺省 | D1 两张卡合并为一处空态 `No benchmark records yet.`（**空态内不放按钮** —— 新增入口只有页头那颗 `+ Add New`，口径同 A4 基准 Tab：按钮在卡头、空态只有配图与文案）；雷达图图例不显示缺失序列 |
| **展示期次早于最早一条基准记录** | 无 `period ≤ 当前期次` 的记录（§7.8） → 同「无基准记录」处理，**不取更晚的记录反填** | 同上 |
| **公司端请求** | 服务端裁剪掉：整个 `radar` 字段、`gsvScore`、`perceptionGap` / `gapDirection`、`benchmarkPosition` 与全部基准值（§4.3） | **不渲染雷达图区块**；维度列表只有「维度名 + 本端分 + View Details」三列，**不留空列、不显示 `—` 占位** |
| **权重未配置 / 合计 ≠ 100%** | 新库的默认路径：任何组织在配置页保存第一组维度之前 `erl_dimension_config` 都是零行。库中数据异常（改坏权重、`Active` 行合计 ≠ 100）同样走这一支：**按等权（各 `100 / {Active 维度数}`%）**降级计算并打 WARN 日志，**不抛异常** —— 综合分不该因配置数据坏掉而整页报错 | 综合分正常显示，旁加 tooltip `Weights unavailable — using equal weighting.`；配置页 **`Dimension Configuration`** Tab 顶部红条提示需重新保存 |
| **维度已被停用（`Inactive`）、但历史期次用过它**（已发布过的维度**只能**停用、删不掉，故这是历史期次唯一会遇到的情形；已删（`deleted = true`）的维度行同样留着、名称与缩写同样解得出，**降级行为与本行一致**，区别只在配置页两处都不显示它） | 软删后行仍在，历史提交记录照常返回；该维名称 / 缩写取 `erl_assessment.dimension_name` / `dimension_abbr` 行上快照（§5.2）| ERL Card、雷达图与 A4 只按当前 Active 维度渲染，**不再出现该维**（`Retired` 灰标只是前端防御，接口不会下发）；历史列表照常列出该维的提交；该维**不出现**在新期次的填报、题库 Tab 与配置页的默认维度列表中。⚠️ **历史分数、Stage 与雷达图形状会漂移**（权重不快照、停用维度退出当前集合，§7.11）。C7 只按 §5.1.5 的发布当时快照整卡展示（含已停用的维度） |
| **改答收回 level 后再打开页面** | 已删除的后续 level 答案与附件不再返回；`unlockedLevel` 为回退后的值 | 填报页只渲染到回退后的 level；**不显示「你曾答过但被清除」的历史**（PRD 无此要求，且会让页面语义混乱） |
| **无差距分析记录** | **`dimensions[]` 照常返回该期次每个维度**（含 `bothSubmitted` / `hasGap`），**不是空数组** | 区块整体仍渲染（标题 + `AI GENERATED` + 期次 chip + 计数 `0 of {total} dimensions have gap analysis for {period}`）；**每维小卡按下面几行分别取态** |
| **某维：双方已提交且有 gap** | `bothSubmitted = true`、`hasGap = true`，该维 `gaps[]` 非空 | 小卡 **绿点 + `Gap analysis ready`**；`View details` 弹框内该维分区列出 gap 与 `actions[{title}]` |
| **某维：双方已提交但无 gap** | `bothSubmitted = true`、`hasGap = false`，该维 `gaps[]` / `actions[]` 为空（**没有 gap 就不产出条目**，不用「优势」占位）。`hasGap = false` 只可能来自零感知差维度（两端评分相等，Java 建任务时直接判、不送 LLM）；送 LLM 的维度回空 gaps 判 `FAILED`，不会落到这一行 | 小卡 **绿点 + `No Gap`**；`View details` 弹框内该维分区显示 `No gap identified for this dimension.`，**不列任何建议** |
| **某维：双方已提交但题集版本不一致** | `bothSubmitted = true`、`questionSetMismatch = true`、`mismatchSide = FOUNDER \| GSV`；该维**不进**本轮分析输入，故 `gaps[]` / `actions[]` 正常为空（上一代旧条目若还在产物里也照常下发，由前端按优先级挡住） | ① Gap 面板期次行下方出**面板级琥珀告警** `Question bank updated — new-version submission pending`（逐维点名落后一端 + 恢复条件，§8.4「A1 Gap 区块」）；② 小卡 **绿点 + 琥珀字 `New version pending (Founder)`**（圆点与 ready 同绿；管理端括号内点名，公司端只出 `New version pending`）；③ `View details` 该维只出**一整条带描边与三角图标的琥珀告警**，不显示维度全称与小结：`Question bank updated — {Founder / GSV} has not yet submitted the new-version questionnaire for {期次}. Gap analysis is unavailable until both sides re-submit.`（公司端主语一律 `One side`）。三处点名同一口径：管理端按 `mismatchSide`，公司端或 `mismatchSide` 缺失时一律中性。**旧条目与旧 `narrative` 都不渲染**；Share 门槛不满足（须无 mismatch，§7.5「报告就绪」） |
| **某维：未双方提交** | `bothSubmitted = false`（缺 Founder 或缺 GSV 或两者都缺），该维不参与生成 | 小卡 **灰点 + `Not submitted`**；⚠️ **圆点颜色只表示「双方是否都已提交」，文字按 §6.1 的优先级取（不只是有无 gap）** —— 前端**不要**把两者压成一个枚举渲染 |
| **Share 门槛未达成** | 该 `(company, period)` 下**存在任一 `Active` 维度**未两端提交、或有维度题集 mismatch、或有维度未按最新提交分析完（门槛全表见 §6.6 接口 27） | `Share to founder` **置灰**，置灰时无悬停提示；区块底部常驻提示 **`Share unlocks once gap analysis is available for all {total} dimensions in {period}.`** |
| **公司端且 `shared = false`** | 接口 17 对公司端**直接返回空态**（不下发 `narrative` / `gaps` / `actions` / `dimensions` 的分析内容），§4.3 后端强制校验 | ERL Card 该区块显示 `No gap analysis shared yet.`；**不渲染** `View details`、`Share to founder`、每维小卡 |
| **Share 后又有新提交** | `reconcile` 新建一条未分享记录（已分享记录及其任务不变，I1），最新记录 `.shared = false` | 公司端**回到未分享空态**（已看过的内容消失属预期）；管理端按钮回到可点态 |
| **LLM 生成失败 / 超时** | Python 侧单任务重试 2 次后放弃（退避 2s / 4s），日志行记 `FAILED`、不写条目，同批其他任务不受影响；Java 该任务 CAS 置 `FAILED`（HTTP 传输失败 / 读超时**不**置 FAILED，任务留 `RUNNING`）；管理端下次读接口 17（60s 冷却）把 `FAILED` 与超 10 分钟的 `RUNNING` 同 id 重投，Python 命中 SUCCESS 日志直接回状态、不重复烧 LLM；手动接口 18 派发调用失败抛 `ServiceException`（见 §7.5） | 手动触发时提示 `Gap analysis failed. Please try again.`；自动失败时该维小卡沿用 `Analyzing…`；已分享给创始人的记录不受影响 |
| **LLM 返回结构不合法** | 单任务解析失败（非对象 / 缺 `gaps` 数组 / `gaps` 没有可用条目 —— 空数组或条目全不是非空字符串被过滤光；只丢部分条目时任务照常成功、打 WARN）⇒ Python `_parse_dimension` 抛 `RuntimeError`，`_run_task` 收口为该任务写一行 `FAILED` 日志（不写条目）、回 `{taskId, status: FAILED, hasGap: null}`（`_parse_dimension` 在 ai 侧 `source/ai/agent/erl_gap_agent/gap_analysis.py`、只抛不吞；`_run_task` 与落库在 erl 侧 `erl_gap_analysis_service.py`）；Java 该任务 CAS 落 `FAILED`，**其他任务不受影响、各自独立成败**；下次管理端读接口 / 手动 Generate 对同 id 重投（10 分钟自愈或 force），见 §7.5 | 该维小卡沿用 `Analyzing…`（`analyzed = false`），不会误判为 `No Gap`；重投成功后正常翻到 `Gap analysis ready` / `No Gap`，见 §6.6 |
| **单份附件取不到摘要** | 失败只可能发生在差距分析 `refresh` 内 —— **下载失败 / 类型不受支持 / 解析为空 / 单份超 90s / 阶段超 120s** 一律降级：该附件**整条不送进 prompt**，**继续分析、不阻断**，只落一条 `logger.warning` | **全站无任何提示**：屏上与库里都看不出哪份证据被跳过，且不落库 ⇒ 同一份附件这次失败下次可能成功。要不要提示、提示在哪（题级 chip / 分析产物内标注「有 N 份附件未能解析」/ 仅管理端），三个候选待需求方定，已记 `CIOaas-web/docs/待优化项.md` |
| **附件解析抽不出内容** | `summarize_file_inline` 抽不出内容即返回空，该附件按上一行降级（整条不送进 prompt）。扫描件 / 图片照走 OCR，OCR 失败同样降级 | 同上：**无任何提示** |
| **附件上传中提交** | 服务端只认已落 `erl_answer_attachment` 的附件 | 提交前 flush 上传队列；仍在传的文件弹提示「N files still uploading」 |
| **附件超过 10MB** | 服务端按 `files.length` 复核后 `BadRequestException`（前端可被绕过，服务端是底线，§6.7） | 选择文件时即在本地拦下，提示 `File exceeds the 10 MB limit.`，**不发起上传**、不占用上传队列 |
| **对未解锁 level 的题提交答案** | `BadRequestException("Answer levels in order.")`（§6.3） | 正常交互下不会触发（未解锁题面不下发）；触发时提示重新加载问卷 |
| **A4 该端在该期次无提交** | 接口 22 单端模式 `dimensions[].submission = null`、双端模式该端 `portals[].submission = null`；`dimensions[]` **按当前 `status = 'Active'` 的维度集合返回**（条数动态），`score = null`、`questions[] = []` | **维度 Tab 与卡片照常渲染**（卡头 `0 questions`，`+ Add New` / `View history` 仍可点）；**两端均不渲染卡内四格元数据栏**（无占位符、无 `PERIOD` 回退），只留下方空态，题目区空态**按端出文案**：**`No GSV submission for this period.`** / **`No Founder submission for this period.`**（管理端取当前药丸，公司端恒 `Founder`；**不是** `No assessment for {period} yet.`）；组合端切到缺失的那一端时该端走同一条按端文案；页面不整体空白 |
| **A4 公司端** | 服务端不下发 `benchmark`，且拒绝 `portal=GSV` | 公司端**不渲染 `GSV` / `Founder` 药丸、不渲染 GSV 侧内容**；**末位基准 Tab 整个不渲染**（判据是端类型，**不是** `benchmark == null` —— 后者在管理端无记录时同样为 `null`）。⚠️ **公司端可正常进入 A4**（`Full View ›`） |
| **A4 该公司无任何评估（由 F2 `View` 或 `Full View ›` 进入）** | 各维 `submission`（双端为各 `portals[].submission`）均为 `null`，且无可用期次（含 closed month 空态） | **维度 Tab 与当前那一维的空卡照常渲染**，顶部一句 `No assessment for {period} yet.`（无可用期次时 `No assessment submitted yet.`）；发起入口为**每张卡卡头的 `Add New`**；**不报错、不 404** |
| **A4 切维度 Tab / 切药丸触发的重取失败** | — | **保留旧数据**：维度 Tab、药丸与当前卡内容照常在、照常可切，页顶 `Alert` 报错；再切一次即再重取一次 —— 请求一发出提示就清掉，再失败再出，成功则内容更新。⚠️ 只有「同一组入参的重取」才保留旧数据 —— **换了公司 / 期次**（入参变化）后的取数失败**仍清空**，不拿别家 / 别期的旧数据充数；**首次进页失败**整块不渲染、只剩页顶报错 |
| F2 某公司在**其缺省期次（closed month 所在季度）**无评估 | 该行 `overallScore = null`、各维 `score = null`，`detailUrl` **仍下发**；**不回退到更早期次** | `ERL Score` 与各维度列显示 `—`，**Stage 列显示 `—`**（不留空 —— 空单元格与「没渲染出来」分不清），`View ›` 仍可点（进该公司 **A4 全维页**看空态）。⚠️ **本页不标期次** —— 整表全 `—` 时看不出是哪个季度的空态，需经 `View ›`（`detailUrl` 带 `period`）进 A4 才看得到 |
| 草稿保存失败（网络） | — | 吸底条红色提示 **`Draft not saved.`**，本地作答原样留在页面上，**由用户自己再点一次 `Save as draft`**（无自动重试、无离开拦截） |
| **在填期间题库发布了新版** | **不是降级场景，是正常路径**：评估恒按 `erl_question_config_version_id` 渲染与计分，服务端行为与没发布过完全一致。接口 3 出参含 `latestPublishedVersionNo` + `hasNewerQuestionSet` | **存过草稿**且 `hasNewerQuestionSet` 时一进页面弹**强阻断二选一弹窗**、不可关闭，必须在「按旧题库就地提交」与「Reset 换新题库」之间选一个（见 §8.4「B 题库更新提示」）—— **服务端行为不受影响**（版本锁定本体不变）；页头不显示题集版本 |
| **提交时绑定版本已不是最新** | **不校验、不拦截**，正常提交 | 无提示；B3 列表不显示题集版本（§8.4「B 题集版本标注」），与新版本提交的行分母不同属正常（§7.10-N2） |
| **配置页有草稿但未发布** | 填报页 / 维度页 / 计分**读不到任何草稿变更**，行为与没改过完全一致 | 无任何感知（这是版本化的目的）；仅配置页显示 `Draft v{n} — unpublished changes` |
| **某维度在已发布版本中 0 题** | 同「题库为空」：该维度 `levelScore = null`，`totalCount` 不含未发布内容 | 填报页该维度显示空态 `No questions published for this dimension yet.`（填报单元＝单个维度，此时整页即空态，`Submit` 禁用）；配置页则正常列出草稿内容 + `Publish` 提示 |
| **提交时题序已变更** | 不阻断，且**因版本锁定而不可能影响本次评估** —— 评估恒按自己绑定的版本渲染与计分（§7.9-⑤） | 无提示。⚠️ 题序**直接影响 level 内的作答顺序**（PRD §3.8「该顺序即评估中的必答顺序」），但**不影响维度分** —— 维度分只看「该 level 是否全 Yes」，与 level 内答题先后无关 |
| **某 level 内混有 Yes 和 No** | 扫到**第一道 No** 即 `BLOCKED`，`levelScore = 该维上一个整级通关的 level`（一级都没通关则 `0`；level 连续时与 `level − 1` 同值）；**该 No 之后的题不必作答**；该 No 之后已答的那些当场清空、落盘时删除，Goldie 只拿到首个 No 为止的作答 | 该 level 组头标 `Stopped here`，组内逐题各显示自己的 Yes / No 徽章；**不把整组显示为 No** |
| 重复提交（**该条记录**已 SUBMITTED） | `BadRequestException` | 提示已提交并跳转到该次提交的只读详情。⚠️ 这指「同一条 `erl_assessment` 被提交两次」；**该期次该端该维再提交一份新的**是**正常路径**（`submissionCount > 0` 时按「B 提交」的第二套确认文案弹窗，新记录因 `submitted_at` 最大而成为该维 SOT，历史提交保留） |
| **并发写同一行（乐观锁冲突）** | `@Version` 版本号不匹配 → `ObjectOptimisticLockingFailureException`，由 `GlobalExceptionHandler` 统一转成 **HTTP 200 + `success: false`**（业务错误口径，`coding.md §1`），文案 `This record was changed by someone else. Please reload and try again.`；日志记 **WARN 带异常**（并发竞争是可恢复的正常竞争，不需要人介入，记 ERROR 会污染 Sentry 告警面）。注：写路径的草稿行取数已加悲观锁（§7.7），本分支主要覆盖题库发布与其它未加锁的写入 | 提示后重拉当前接口即可；不阻断其它操作 |
| **`Reset` 时草稿已被他人清空 / 已提交** | 接口 28 找不到 `DRAFT` 记录 → 幂等返回成功（不抛异常） | 提示 `Draft already cleared.` 并重拉接口 3 重绘；若该维已被他人提交，则重绘为**只读态**并提示 `This dimension was submitted by another user.`（草稿为公司共享、不区分账户） |
| 跨端越权访问 | `BadRequestException` | 统一错误提示，路由守卫先行拦截 |

---

## 12. V1 明确不做（YAGNI / 风险控制）

- **不建独立 Exit Readiness 落地页 / Dashboard 路由**（PRD §3.1）。
- **A4 全维 Score Details 页已纳入 V1**（§6.2.1 / §8.4）；但 A4 上**不做**维度间对比图、导出、以及 Gap 建议 / Data Sources 的重复区块 —— 单维深度仍走 A3。
- 不做完整 BPMM 评估交互（PRD §5）；A1 卡片也不显示 BPMM 参考数字。
- 不做 Ask Goldie 对话接入、Finance 页 ERL 卡片与回跳。
- 不做 Goldie 建议的跟踪 / 指派 / Deadline（PRD 未要求）。
- **不做「GSV vs. Founder 分数对比 Tab」** —— 差距分析（E1）已实现，该替代方案无必要；PRD 未要求。
- 不做 Goldie 生成结果的人工编辑 / 审核流（§13-Q9）。
- 不做差距分析的版本历史，报告记录逐次追加（已分享记录不可变），但不做逐次浏览 UI。
- **不做计分模式的可切换抽象** —— PRD 已把打分格式定档为 Yes/No 逐级解锁，只实现这一种（§7.2-②）。
- **不做 1–9 分打分控件、题均分、手动维度分、软确认弹窗、每维状态摘要、Data Sources & Cadence** —— PRD 已无这六项的依据。
- **不做「权重快照」** —— 权重独立保存、**实时生效**，既不随题库版本快照、也不在 `erl_assessment` 上存每维权重快照；代价是**改权重会回溯改变历史期次的综合分与 Stage**（§7.10-W1 / §13-Q21）。
- **不做维度的物理删除**：配置页的两个破坏性动作**落库都是置位、都不删行** —— 停用 = 置 `erl_dimension_config.status = 'Inactive'`（行与 `weight` 原样保留、可恢复），**删除 = 置 `deleted = true`**（行与 `weight` 同样原样保留，只是**所有读侧一律排除、页面无恢复入口**，§5.1.3 / §7.11-④）。⚠️ **「删除」指的是「从产品里彻底消失」，不是 SQL `DELETE`** —— `dimension_code` 被五张表当历史外键引用，真 `DELETE` 会让那些历史数据解不出维度名。
- **维度删除的前置拦截只按「是否进入过已发布题库版本」判**：
  - **拦的是「已进入过某个已发布题库版本的维度不许删」**（只能停用），判据是 `erl_question_config_dimension_version` join `erl_question_config_version` 且 `status = 'PUBLISHED'`（§6.4-3-⑨）。
  - **不做「有历史数据禁止删除」这个判据** —— 它会连「有人填过、但题库从没发布过」的维度也拦住，而那种维度删掉是安全的；**也不做**「删除前查五张表的引用计数」这类阻断（引用照旧存在、照旧解得出名字，那不是删除该关心的事）。
  - **保护对象不是那一行**（置位下行不消失），是**已发布题库版本的语义**（§7.11-④）。
- **不做全局统一题库** —— 题库与权重**按组织（租户）**隔离（PRD §4）；组织内不按公司细分，公司级覆盖也不做。**题库版本化已纳入 V1**（§7.9）。
- **不做撤回（已发布 → 草稿）、单维度发布、变更逐条勾选发布、定时发布、版本回滚与版本对比 UI** —— V1 只实现「改草稿 → 全量发布」一条路径（§7.9）。只读的**版本历史页**（C7）已纳入 V1，能按版本回看**那一版的整份题面**（接口 26），但**不含回滚、不含版本间 diff 视图**（两版并排比对、逐题标红绿都不做）——「能看某一版长什么样」与「能比较两版差在哪」是两件事。
- **不做草稿的丢弃（Discard changes）** —— 未要求；代价是误改只能手工改回来（题库低频、变更摘要可见，可接受）。若实际使用中成为痛点，加一个 `DELETE /erl/question/draft` 即可，不影响现有模型。
- **不做草稿的编辑锁 / 按人隔离的草稿 / 变更冲突合并** —— 题库配置是低频管理动作，多人共编不做界面提示（§7.9-④）。⚠ 这里只指**草稿之间**不做编辑锁与冲突合并（后保存覆盖先保存，接受）；「已发布版本一个字节都不改」（§7.9）与「已 SUBMITTED 的记录一律只读」（§7.7）这两条**不变量**由 `@Version` 乐观锁 + `SELECT … FOR UPDATE` 悲观锁在数据库层兜底，别把本条读成「跨状态覆盖也不管」。题库草稿的并发编辑取悲观锁而非乐观锁，是为了让**失败落在低频的发布方**：两个管理员同时编辑不同维度的题目是允许的，若靠乐观锁，后提交者会因为版本号被对方改过而丢掉刚录的题目。
- **不做在填评估的重基 / 「升级到最新题集」按钮** —— 评估版本锁定，一次评估自始至终用同一版题集（§7.9-⑤）。
- **不做题集版本不一致的阻断** —— 同期次两端跨版本、旧版本草稿延迟提交照旧**允许**，前端不显示版本号（§8.4「B 题集版本标注」；§7.10-13 / N1 / N2）；**但维度级的「不可比」要告警**：两端同维 `question_version_no` 不等时，接口 1 / 17 的该维下发 `questionSetMismatch` + `mismatchSide`，A1 小卡渲染绿点 + 琥珀字 `New version pending`（并出面板级告警）、该维不送进 Goldie。判据只能是维度级题集版本号（用组织级发布批次号会假阳性）。
- 不做评估期次之间的对比、趋势图、导出。
- 不做题库批量导入导出。
- 不做 `SUBMITTED` 回退为 `DRAFT` 的重开流程 —— PRD 的口径是新建提交，不是重开。
- 不冗余存储展示用聚合分数（**综合分 / Stage / Era 全部实时算**，维度与权重一律取当前 `Active` 值，因而会随配置变化而漂移）；`level_score` / `terminated_level` / `unlocked_level` 落库在 `erl_assessment` 上，是因为解锁进度是草稿期交互状态、必须持久化（理由见 §5.2）。
- 不新增 dva model（`src/models/` 已冻结）。
- 不引入 SQS：Java 与 Python 走同步 HTTP 经网关。
- 不接 Fireflies / SharePoint 作为 Goldie 数据源（PRD 未要求）。

**识别到但本次不处理**：

- `fi/` 业务域仍是扁平结构、`QuickbooksController` 在 Controller 内 try-catch 并直接收发 Entity，均不符合 `standards/`，属存量技术债 —— 已记入 `CIOaas-api/docs/待优化项.md`。
- `CompanyOverviewPage.tsx` 单文件超 1600 行、DI / FI 分支混杂。
- 题量较大的问卷页单页渲染；题量再翻倍需考虑虚拟滚动。

---

## 13. 待确认事项（开发前必须对齐）

> 编号与 **PRD §五「明确的 TBD 事项」** 对齐；PRD 未列但本设计发现的新问题标注为「设计新增」。已关闭的问题已删除；新问题续接编号（当前最大 Q37）。

| # | 对应 PRD | 问题 | 影响 | 本设计取值 / 建议 |
|---|---|------|------|------|
| **Q1** | §五-1 | **ERL 卡片上 Gap Analysis 的呈现方案**（摘要几行？点开何处？）与 **BPMM 的内容 / 规则 / 数据来源**（1–5 的分值从哪来？现有系统有无该数据？） | 卡片布局与 `bpmmScore` 的取数实现；BPMM 无数据源则该字段无法落地 | Gap 区块按维度小卡 + `View details` 弹框呈现（§8.4 A1）；**BPMM 数据源必须先给** —— 在此之前 `bpmmScore` 恒 `null`，其余照常开发；A1 卡片不论有无数据一律不显示 BPMM |
| **Q3** | §五-2 / §五-3 | **计分口径**：Stage 由**加权综合分**推导的**取整规则**（round / floor / 查表？）—— PRD §3.5 只说「由综合分数与 Workbook 的 Era 边界推导」 | 只影响 Stage 徽章的整数显示；Era 徽章不受影响（Era 只按 §7.3 的区间判，不经 Stage） | 现按 `stage = clamp(round(score), 1, 9)`，**且 `score == 0` 时 `stage = 0`**（§7.3）。实现集中在 `ErlLevelScorer`，改规则只改一处 |
| **Q4** | 设计新增 | **题库初始内容从哪里来**？PRD §3.3 说「30+ 题目」、§3.9 示例 `45/45`、原型是 165 题，三者不一致。正式题库清单是否已有？ | 决定首版题库内容；影响 UAT 可用性（`erl_init.sql` 不预置任何题目，只能靠录入） | 代码不写死题量（已按题库配置驱动）。从原型已能反解出**完整 165 题 + 每题的 level 归属 + Source 标签**（level 分布见 §7.2），这是目前唯一成型的候选题库 —— 建议**要么由产品确认直接采用它作为首版种子**，要么给出正式清单。**UAT 前必须从零录入**，走配置页草稿 → Publish，不要直接改库（§7.9-⑥）。⚠️ 自测想跑通「level 1 全 Yes → 解锁 level 2」的解锁链路，至少每维铺 3 道（`era_band` 1 / 2 / 3 各一道）；⚠️ 真实题库的 level 分布是**稀疏**的（PRL 只用 level 3/6/9、RRL 最高到 L8），「首个可作答 level 不是 1」「全通关得分不是 9」两条分支要按真实分布录入后才走得到 |
| **Q7** | §五-7 | **可见角色子集**：① ERL 卡片及后续页面是否对「当前可访问 Company Overview 的全部角色」开放，还是需收窄？② ERL Configuration 仅管理端、按 `organization_id` 隔离（PRD §3.8 / §4）；同一组织内是否要再分「可编辑题库 / 可发布 / 可改权重」三级？③ 前端新增 API 域 `exitReadiness/` 需登记进 `CIOaas-web/standards/architecture.md` §2 | 权限矩阵（§4.2）与规范符合性 | ① 本设计按 §4.1 的 `roleType` 二分实现；② 本设计**不分级**（组织内管理端均可编辑 + 发布 + 改权重，§7.10-8）；③ 随本功能一并更新规范文件 |
| **Q8** | 设计新增 | PRD §3.5「Scorecard」的展示项在 ERL Card 与维度页之间的归属 —— 本设计的划分见 §8.5（含「公司端可见」一列）。（创始人只能查看自己的分数，口径见 §4.2） | 影响公司端可见范围与两个页面的信息密度 | 请产品对 §8.5 的表格直接勾选确认 |
| **Q9** | 设计新增 | LLM 生成的 **gaps / actions** 是否需要 GSV **人工编辑或审核**后才对公司端可见？ | 影响是否需要 `status` 字段与编辑页 | **Share 机制已覆盖「未审核内容直接推给创始人」的风险** —— `shared = false` 时公司端看不到，GSV 点 `Share to founder` 才推给创始人；再提交后重生成落在新的未分享记录上，需 GSV 重新 Share。剩余问题仅是「是否还要一层可编辑 / 可审批的正式流程」，V1 **不做**（生成即可 Share） |
| **Q21** | §3.8（权重） | 已定：接受漂移 —— 权重不快照，改权重 / 启停用维度会回溯改变已提交历史期次的综合分、Stage 与雷达图形状（见 §7.1 / §7.11 / §12） | — | 若日后不可接受：在 `erl_assessment` 补一列 `weight` 快照（提交时冻结本维权重），但救不回「那个期次有哪些维度」，完整方案仍需期次级的维度集合冻结 |
| 🟡 **Q26** | 设计新增（实现期发现） | 题库 band pill（C1 / C7）和 Era 徽章、分数色是否共用一套三色？现在 pill 按原型用绿 `#1E8E4A`，Era 用 `#4CAF50`，另两色一致。另外，pill 配色未沿用需求方先前定的那套，至今未确认 | 同一个 Exit 档，配置页和 A1 / F2 / B3 显示两种绿，容易被读成两种状态 | ① 全站统一成一种绿（需指定是哪种）；② 保持两套。**当前为 ②**。定下来后收成一处共享色值 |
| 🟡 **Q27** | 设计新增（实现期发现） | 两处按需求方 / 原型指定的配色没达到 WCAG AA，要不要调：① Harvest 浅黄 `#DED87A` 文字放在同色浅底上，对比度约 1.4:1；② 配置页题目 / 维度删除确认的琥珀 `Delete` 按钮，白字对比度 2.40:1（要求 4.5:1） | 浅黄 pill 文字和 `Delete` 按钮文字在普通屏上就难认，弱视或强光下更差 | ① 保持现配色，接受不达标；② 底色不动、只换字色：`Delete` 改藏青 `#0D2B56`（5.85:1），Harvest 文字压深一档。**当前为 ①** |
| 🟡 **Q28** | 设计新增（实现期发现） | 基准模块的标题统一用哪种词序？A4 末位 Tab 和面板标题是 `External Benchmarks & Top GSV Quartile`，D1 页头和 A1 入口是 `Top GSV Quartile & External Benchmarks` | 同一个功能两种叫法：从 A1 点进 D1 看到的标题，和 A4 Tab 上的标题不一样 | ① 统一为 `Top GSV Quartile & External Benchmarks`；② 统一为 `External Benchmarks & Top GSV Quartile`。**当前两种并存** |
| 🟡 **Q29** | 设计新增（实现期发现） | 基准分数表的列头怎么定：① 要不要保留 `(1–9)`（每格已有 `/9`）；② 大小写：分数列首字母大写，`DIMENSION` 全大写，而 D3 原型是全大写；③ 列头字号 D3 是 12px，A4 / D1 是 11px | 这张表 A4 基准 Tab、D1、D3 三处共用，同一行混着两种大小写，三屏两种字号；两次圈图的结论相反；列宽随方案一并定（共用组件写死 240px，原型约 400px） | ① 全大写、去掉 `(1–9)`（D3 原型）；② 首字母大写、保留 `(1–9)`（较新一次圈图）。**当前分数列按 ②，`DIMENSION` 没跟着改**（正文 §8.4-A4 / §8.4-D1 仍按较早一次圈图的口径，待定档后回写）；字号随选定方案三处统一 |
| 🟡 **Q30** | 设计新增（实现期发现） | 「再提交一次会成为本季 source of truth，旧提交留档」这层意思还要不要告诉用户？B3 已撤掉 `Current` 徽章，`Submit again?` 确认框删了这句原话，题库弹窗的 `Submit draft content` 连重复提交确认都不弹 | 用户看不出哪条提交在计分，可能无意中用新提交（包括替同事提交）顶掉之前的结果 | ① 保持现状，只靠行序（最新在前）；② B3 加回 `Current` 徽章，并且已有提交时 `Submit draft content` 也弹 `Submit again?`。**当前为 ①**（正文 §7.7 / §8.4「B 提交」仍要求确认框带该句，待定档后回写） |
| **Q31** | 设计新增 | 已定：提交的追溯信息（题库版本号、止步 level / 是否全通关、已答 / 总题数、已提交记录的 `Fund`）不再显示，接口 7 相应出参已删（见 §6.3 / §8.4-B3） | — | — |
| 🟡 **Q32** | 设计新增（实现期发现） | F2 ERL Tab 每行取各公司 closed month 所在季度，同一屏上 Q2、Q3 可能混在一起，而页面不显示期次，要不要标出来？ | 各行的 `ERL Score`、维度分、`Stage` 不能横向比较，用户也无从知道哪一行是哪一季 | ① 保持现状，不标注；② 每行显示期次（接口 20 已下发 `period`，加一列或在公司名下加一行小字）。**当前为 ①** |
| 🟡 **Q33** | 设计新增（实现期发现） | B 页清空草稿（答案 + 附件，不可恢复）有三个入口：按钮行 `Reset`、`Draft restored` 横幅的 `Discard draft`、题库弹窗的 `Access new question library`。三处都没有确认，也没有文字警示，要不要补？ | 草稿是全公司共享的，点一下可能清掉同事刚存的答案和附件，且找不回；`Reset` 和 `Discard draft` 是同一个动作，却用了两种叫法 | ① 保持现状；② 不加弹窗正文，改用按钮下一行小字或在按钮文案里带上 `(deletes saved answers)`（文案需定），同时统一两颗按钮的叫法。**当前为 ①** |
| 🟡 **Q34** | 设计新增（实现期发现） | ERL 的日期写法要不要收敛？现在有四种：`Jun. 30, 2026`（A1 / C7）、`30 Jun 2026, 14:05`（A3 / A4）、`2026-06-30`（基准三页）、`6/30/2026`（B3），都是按各页原型定的 | 同样是「何时提交 / 录入」，跨页对照时要在脑子里换算格式 | ① 收成两种（到日一种、到分钟一种，具体格式需定）；② 保持各页原型写法。**当前为 ②** |
| 🟡 **Q35** | 设计新增（实现期发现） | B 页有三处只按圈图改了 Founder 卷，GSV 卷要不要跟进：① 标题破折号后，Founder 是公司名，GSV 是 `GSV Validation`；② 元信息栏 Founder 三格，GSV 四格（多 `FUND`）；③ 面包屑末级，Founder 是 `New Assessment`，GSV 是 `Add New` | 管理端在两卷间切换时，标题、元信息格数和面包屑都会变，看起来像两个页面 | ① GSV 卷跟进，与 Founder 一致；② 保持两端差异（需求方的原意）。**当前为 ②** |
| 🟡 **Q36** | 设计新增（实现期发现） | 基准分（`External Benchmarks` / `Top GSV Quartile`）要不要从录入到存储全链路改成整数？D2 页面只能输入 1–9 的整数，但服务端与库表仍是一位小数口径：接口 16 的 `ErlBenchmarkCreateRequest` 只有 `@DecimalMin("1.0")` / `@DecimalMax("9.0")`、没有整数校验，保存时按一位小数 HALF_UP 标定；列 `erl_reference_score_item.benchmarkit_score` / `top_quartile_score` 仍是 `numeric(3,1)`；早先录入的一位小数记录原样保留、原样展示 | 绕过页面直调接口 16 仍能写进 `7.5`，前后端口径不一致；D1 / D3 / A4 基准表里整数与一位小数记录并存 | ① 保持现状：只在录入侧收紧，存储与展示沿用一位小数；② 服务端补整数校验（只拦新写入，存量与列类型不动）；③ 全链路改整数：服务端校验 + 列类型迁移 + 存量取整（需定取整规则）。**当前为 ①** |
| 🟡 **Q37** | §3.4（GSV 元数据「基金/组合」）；设计新增（实现期发现） | 一家公司同时挂在多个 portfolio 下时，GSV 填报页元信息栏 `FUND` 一格该显示哪个？ | GSV 卷填报页 `FUND`（接口 3 出参 `fund`，按当下归属现算，不落库）；Founder 卷不显示这一格 | 当前实现：`resolveFund` 取 `companies()` 结果里该公司**第一条命中**的 `portfolioName`，顺序不保证，同一家公司不同时刻可能显示不同组合。建议需求方定口径：列出全部 / 取某个主组合 / 按固定规则排序取一个。（`companies()` 带用户级可见性过滤、调用者看不见该 portfolio 时取不到名字，是另一个问题，仍记 Java 台账「ERL 组合层总表比同页其它 Tab 多一层用户级可见性过滤」） |
