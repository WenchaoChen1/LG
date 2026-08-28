> 关联文档：
> - **需求文档（本设计的唯一权威来源）**：[../../Exit_Readiness_PRD.md](../../Exit_Readiness_PRD.md)（**2026-08-28 修订版**）
> - 原型（Lovable，已发布，**仅作 UI 参考**）：`https://exit-readiness-hub.lovable.app`（项目 `exit-readiness-hub` / Readiness Compass）
> - 后端规范：[../../../CIOaas-api/standards/architecture.md](../../../CIOaas-api/standards/architecture.md) · [../../../CIOaas-api/standards/coding.md](../../../CIOaas-api/standards/coding.md)
> - Python 规范：[../../../CIOaas-python/standards/architecture.md](../../../CIOaas-python/standards/architecture.md) · [../../../CIOaas-python/standards/coding.md](../../../CIOaas-python/standards/coding.md)
> - 前端规范：[../../../CIOaas-web/standards/architecture.md](../../../CIOaas-web/standards/architecture.md) · [../../../CIOaas-web/standards/coding.md](../../../CIOaas-web/standards/coding.md)
>
> 阶段：④ 设计 | 版本：**v3.4** | 日期：2026-08-28 | 范围：ERL Card / 维度详情 / 双端填报 / 题库配置 / 基准 / Goldie 差距分析 / 组合层 ERL Tab

# Exit Readiness（ERL）设计文档 V1

## 版本说明

| 版本 | 日期 | 依据 | 说明 |
|------|------|------|------|
| v1 / v2 / v2.1 | 2026-08-26 | Lovable 原型 + Lovable story | 原型反解产物。**部分结论已被 PRD 推翻**，见 §0.2 |
| v3.0 | 2026-08-27 | `docs/Exit_Readiness_PRD.md` | 按 PRD 全量重校，共 **20 条修正**（9 处需求冲突、9 项缺失补齐、2 项无 PRD 依据的自创设计），逐条见 §0.2 |
| v3.1 | 2026-08-27 | **原型新截图**：`/readiness/benchmark`（D1）、`/readiness/benchmark/add`（D2） | **基准模块（D）按原型重做**：每期次由「两个总分」改为「五维各两个分」；D1 定为 `Latest by Dimension` + `Record History` 双卡；D2 由 Modal 改为**独立页面**。逐条见 §0.3 |
| v3.2 | 2026-08-28 | `docs/Exit_Readiness_PRD.md` **2026-08-28 修订** | 按 PRD 修订重校，共 **4 条**：题库新增 **Publish 发布态**（新增需求，影响面最大）；F2 `View` 目标由 Company Overview 改为 **Score Details 页**；每维状态摘要三值枚举**由 PRD 明文降级为设计占位**；打分格式的「0/1 二元 / 光谱型」表述从 PRD 移除。逐条见 §0.4 |
| v3.3 | 2026-08-28 | **需求方对 §13-Q11 的裁决**（2026-08-28） | **题库改为版本化**：v3.2 的「只有新增题需发布」作废 —— **新增 / 编辑 / 删除 / 重排全部经 Publish 才生效**。`erl_question` 上的状态位改为独立的**版本表 + 写时复制草稿版本**；评估绑定题库版本快照；在填草稿按 `question_key` 重基。逐条见 §0.5 |
| **v3.4（本版）** | **2026-08-28** | **需求方裁决**（2026-08-28）：「保留旧答案，以正在编辑的版本为准」 | **重基（rebase）整体删除，改为版本锁定**：评估创建时绑定当时最新已发布版本，此后**无论题库发布多少版都不跟随**（Founder 用 v3 打开就一路 v3，GSV 后填用 v4）。据此关闭 §13-Q13 ~ Q16 四条边界，并删掉重基链路的全部实现物。逐条见 §0.6 |

---

## 0. 目标与裁决原则

### 0.1 一句话目标

在 LG 平台内实现**退出准备度（Exit Readiness Level, ERL）**：**替代 Company Overview 页的 Development Intelligence（DI）板块**，由创始人（Founder）与 GSV 团队各自独立完成季度评估，从 5 个维度（FRL / PRL / BERL / RRL / TRL）打分，产出维度分 / 综合分 / 当前 Stage / 双方认知差（Perception Gap），与 Benchmarkit、Top GSV Quartile 两条外部基准对比；由 Goldie 生成差距分析与行动建议；题库可由管理员自助配置；组合层提供跨公司 ERL 总表。

### 0.2 权威来源与冲突裁决

| 来源 | 地位 |
|------|------|
| `docs/Exit_Readiness_PRD.md` | **唯一权威**。任何与之冲突的原型行为、Lovable story 描述、v2.1 结论一律作废 |
| Lovable 原型 | 仅作 **UI 布局与交互参考**；其数据、计算口径、页面结构均不构成需求 |
| Lovable story 验收标准 | 参考。v2.1 曾以 story 为准补齐 A3，PRD §3.2 已给出正式定义，以 PRD 为准 |

**v2.1 → v3.0 修正清单**（每条注明 PRD 依据）：

| # | v2.1 的问题 | 类型 | PRD 依据 | v3.0 处理 |
|---|-------------|:---:|----------|-----------|
| 1 | 建了独立 `/exitReadiness` Dashboard 落地页（A1/A2） | **冲突** | §3.1「**不设独立 Exit Readiness 落地页**；ERL 卡片是唯一入口」 | **删除 Dashboard 路由**；A1/A2 合并为 Company Overview 页内的 **ERL Card**（§8.1） |
| 2 | 完全未提 DI 板块 | **缺失** | §3.1「系统级隐藏原有 DI 卡片（使用现有 setting/toggle），DI 数据、KPA、SDP 完整保留但不再展示」 | 新增 §8.6「DI 卡片下线方案」，落到存量 `diStatus` 开关 |
| 3 | `uk_erl_assessment (company_id, period, portal)` 唯一约束 | **冲突** | §3.3 / §3.9「同一季度允许多次提交，最新一次为 source of truth」「必须完整保留并清晰区分每一次单独提交」 | **去掉唯一约束**，改 `submission_seq` + `is_latest`（§5.2） |
| 4 | 答案表无「证据/备注」字段 | **缺失** | §3.3 / §3.4「每题：可选证据/备注（Evidence/Notes）文本」；§3.6 Goldie 输入源即为该备注 | `erl_assessment_answer.note`（§5.3） |
| 5 | 无文件/图片上传 | **缺失** | §3.3 / §3.4 / §4「可选文件上传，同步写入公司 Memory File，供 Goldie 分析」 | 新增 `erl_answer_attachment` 表 + §6.7 上传登记链路 |
| 6 | 维度分只有「题目平均」一种来源 | **冲突** | §3.4「GSV 需为每个维度**手动填写一个整体维度分**；与题目推导不一致时弹软确认弹窗」；§3.1「各维度分数：新增时手动填写的」 | 新增 `erl_assessment_dimension` 表；展示分取**手动分**，推导分仅用于一致性校验（§5.4 / §7.1） |
| 7 | 明确排除「题目排序拖拽（无需求）」 | **冲突** | §3.8「**拖拽重排**：在 Era Band 内调整顺序，该顺序即评估中的**必答顺序**」 | 纳入 V1，新增 `PUT /erl/question/reorder`（§6.4） |
| 8 | 决定「不自动生成，前端显式触发」 | **冲突** | §3.6「新评估提交后**自动刷新**分析，始终反映最新数据」 | 改为**提交即置脏 + 自动重生成**（§7.5），保留手动 Regenerate |
| 9 | Goldie 单套 prompt / 单份产物 | **缺失** | §3.6「Founder 与 GSV 均可见，但两者**展示口吻不同**」 | `erl_gap_analysis.audience`（FOUNDER / GSV）+ 双 prompt（§5.6 / §6.6） |
| 10 | 明确排除「Data Sources & Cadence 卡」 | **冲突** | §5「**Data Sources & Cadence（按维度）**：显示主要与补充证据来源，以及评估频率（季度）」 | 纳入 V1，落在维度详情页（§8.4） |
| 11 | 明确排除「A6 BPMM 卡片」 | **冲突** | §3.1 卡片含 BPMM；§5「BPMM 分数仅作为参考数字（1–5）显示」 | **参考数字纳入 V1**（完整 BPMM 评估交互仍不做），数据来源见 §13-Q1 |
| 12 | 无「每维状态摘要」 | **缺失** | §5「每维度状态摘要（基于 gap 幅度推导）」（v3.0 依据的旧版 PRD 另含 `Met / Partial / Gap` 三值，**2026-08-28 修订已删去**） | 新增 §7.4 判定规则；**三值枚举自 v3.2 起为设计占位**，见 §0.4-3 |
| 13 | 打分格式仅按「题目级 answer_type」建模 | **缺失** | §3.3 / §4「MVP 用 1–9 占位，需保留切换至 Yes/No + 固定顺序的能力（"No" 中止该维度后续计分），**开发时以占位形式实现，保证未来切换不用重构**」 | 新增 §7.2「计分策略可切换设计」 |
| 14 | 雷达图无图形规范 | **缺失** | §5「仅线条无填充、每线不同色、有图例、中心轴隐藏、悬停显示精确分、架构预留新增 perspective」 | 补入 §8.4 |
| 15 | F2 无排序筛选 | **缺失** | §3.7「支持按分数、Stage、维度进行排序与筛选」 | 补入 §6.5 / §8.4 |
| 16 | 维度页无「+ New」入口；GSV Tab 对公司端可见 | **冲突/缺失** | §3.2「『+ New』入口发起新一轮评估」「**公司用户不显示 GSV Tab**」「创始人不显示 GSV 专属字段（Benchmarkit、Top GSV Quartile 等）」 | 补入 §8.4，并收紧 §4.2 权限表 |
| 17 | 自创 A4「Score Details 全维明细页」（原型 `/readiness/overall`） | **无依据** | PRD 全文无此页；§3.1 的「Score Details 页」即维度详情页 | **删除 A4**（v3.2：PRD §3.7 的 `View` 目标改写为「Score Details 页面」，仍指**维度详情页**，不复活 A4，见 §0.4-2） |
| 18 | 自创 §8.5「在 Dashboard 维度行加 View Details」 | **已被 PRD 取代** | §3.1「卡片内提供每个维度的『View Details』入口」 | 入口改挂 ERL Card |
| 19 | §7.1「展示页维度分一律取 GSV 分」 | **需重述** | §3.1 卡片同时列 Founder 分与 Perception Gap；§5 Scorecard「每维度 Founder 分与 GSV 分」 | 改为**并列展示双方分**（§7.1） |
| 20 | 把「维度分 = 题均分」写成已定口径 | **越权定稿** | §5「具体计算方法：初步为各题平均，**最终待开发前确认**」；§五 TBD-3 | 降级为**占位口径**，回填 §13-Q3 |

**保留的 v2.1 结论**（PRD 未推翻，继续有效）：
- Java 为前端唯一出口 + Python 只做 LLM 生成，HTTP 经网关同步调用（§3）。
- Era 分段 `[1,4)` / `[4,7)` / `[7,9]`；原型 FRL 6.4 标 Exit Era 是原型 bug（§7.3）。
- 综合分 = 五维简单平均（PRD §5 明确，一致）。
- Perception Gap = Founder − GSV（PRD §5 明确，一致）。
- 题库全局单份、不引入 SQS。（**v3.3**：「题目软删除」结论作废 —— 题库版本化后，草稿版本内直接物理删行，历史由版本快照保住，见 §0.5-2 / §5.1）

> **跨项目协作模式（本功能新增第三种）**：根 `CLAUDE.md` 现记录两种 Java↔Python 协作模式——智能解析走 SQS 异步、AI Chatbot 走 HTTP 经网关 + SSE 流式。ERL 差距分析是第三种：**HTTP 经网关 + 同步非流式**（单次秒级调用，Java 落库缓存）。实现落地后须把该模式补记进根 `CLAUDE.md`。

### 0.3 v3.0 → v3.1 修正清单（基准模块 D，依据 2026-08-27 原型截图）

> 原型仍**仅作 UI 参考**；PRD §4 只规定「Benchmarkit / Top GSV Quartile 是外部静态数据、平台不计算」，**未规定录入粒度与页面结构**。原型给出的粒度（**按维度**）与 PRD §5「雷达图四条序列各覆盖五维」自洽 —— v3.0 的「每期两个总分」根本画不出这两条序列，因此以原型粒度为准。

| # | v3.0 的写法 | 类型 | 原型证据 | v3.1 处理 |
|---|-------------|:---:|----------|-----------|
| 1 | `erl_benchmark_record` 每条记录只有 `benchmarkit_score` / `top_quartile_score` 两个总分 | **粒度错误** | D2 页「Scores by dimension (1–9)」表格：五维 × 两列输入；D1 页「Latest by Dimension」卡逐维列值 | 拆为**主表 + 维度明细表**：`erl_benchmark_record`（期次 / 备注 / 录入人）+ `erl_benchmark_dimension`（五维 × 两个分），见 §5.6 |
| 2 | 雷达图 `BENCHMARKIT` / `TOP_GSV_QUARTILE` 序列的 `values[5]` 无数据来源（只有一个总分） | **自洽性缺陷** | 同上 | 两条序列取**适用记录的五维值**，见 §6.1 / §7.8 |
| 3 | D2「新增基准」是 Modal | **冲突** | 原型为独立页 `/readiness/benchmark/add`，含 `< Back`、页级标题与说明、底部 `Save Record` / `Cancel` | 改为独立路由页 `/exitReadiness/benchmark/add`（§8.1） |
| 4 | D1 页结构未定义 | **缺失** | 原型两张卡：`Latest by Dimension · {period}` 与 `Record History` | 补入 §8.4 交互表 |
| 5 | 记录表带 `+0.3 vs prior` 环比（v2.1 从旧原型反解，v3.0 沿用） | **无依据** | 新原型 D1 两张卡**均无环比列** | **删除 `deltaVsPrior`**（YAGNI；PRD 未要求，趋势对比由 Record History 逐期值体现） |
| 6 | 记录表列未定义 | **缺失** | `PERIOD`（最新条带 `LATEST` 徽章）/ `RECORDED` / `RECORDED BY`（姓名 + 角色）/ `BENCHMARKIT (AVG)` / `TOP GSV QUARTILE (AVG)` / `NOTE` / `ACTIONS`（`Details`） | 补入 §6.5 出参与 §8.4 |

> 本版**只动基准模块 D**，其余章节（A / B / C / E / F）的 v3.0 结论全部有效。

### 0.4 v3.1 → v3.2 修正清单（依据 2026-08-28 PRD 修订）

> 本次 PRD 修订共 5 处，其中 1 处为纯措辞整理（§3.6 标题去掉「（原文更新）」），对设计无影响；其余 4 处逐条处理如下。

| # | PRD 变更（2026-08-28） | 类型 | v3.2 处理 | 影响章节 |
|---|------------------------|:---:|-----------|----------|
| 1 | §3.8 新增「**Publish 按钮：五个维度任意维度有新问题，按钮会被激活**」 | **新增需求** | ~~题库引入草稿 / 已发布两态，只有新增题需发布~~ —— **v3.3 已被需求方裁决取代，改为题库版本化、所有变更经发布**，见 §0.5 | §0.5 |
| 2 | §3.7 `View` 列由「跳转到该公司的 **Exit Readiness 页面**」改为「跳转到该公司的 **Score Details 页面**」 | **冲突（改口）** | F2 末列 `View →` 的目标由「Company Overview 锚点定位 ERL Card」改为该公司的**维度详情页（Score Details 模板，§0.2-17 已确立二者等价）**，默认落在 **FRL** 并带当前 `period`；面包屑首级仍回 Company Overview。**不新增全维明细页**（A4 仍不做） | §6.8 / §8.4 / §9 / §11-32 / §13-Q12 |
| 3 | §5「每维度状态摘要（**Met / Partial / Gap**，基于 gap 幅度推导）」删去括号内三值枚举 | **依据减弱** | 设计**不改实现**（仍需要一个状态摘要），但 `MET / PARTIAL / GAP` 三值由「PRD 明文」降级为**本设计占位枚举** —— 取值命名与阈值一并回填 §13-Q3，产品可整体替换。§0.2-12、§7.4-①、§8.5 的措辞同步订正 | §0.2-12 / §7.1 / §7.4 / §8.5 / §13-Q3 |
| 4 | §5 打分规则删去「（部分指标是 **0/1 二元**、部分为**光谱型**）」 | **依据减弱** | **不改设计** —— `answer_type ∈ {SCORE, YES_NO}` 的双题型建模来自 §3.3「MVP 用 1–9 占位、未来切 Yes/No + 固定顺序」与 §四「打分格式演进」，**不依赖被删的这句**；§7.2 补一行说明该表述已从 PRD 移除，避免后续被当作遗漏 | §7.2 |

> 本版**只动上述 4 处涉及的章节**，其余 v3.0 / v3.1 结论全部有效。

### 0.5 v3.2 → v3.3 修正清单（依据需求方 2026-08-28 对 §13-Q11 的裁决）

**裁决原文**：Q11 选「**所有变更都经发布，增加题库版本化**」；**不需要**撤回（已发布 → 草稿）与单维度发布。

> ⚠️ **该裁决与 PRD §3.8 现有原文冲突**：PRD 仍写着「变更**立即生效**到评估表与 Score Details 的题目列表中，无需其他配置步骤」。本设计以**裁决为准**（裁决晚于 PRD 且针对性回答了本问题），并建议 PRD §3.8 同步删去该句、补上发布语义 —— 见 §13-Q11 的「回写 PRD」一栏。

| # | v3.2 的写法 | 类型 | v3.3 处理 | 影响章节 |
|---|-------------|:---:|-----------|----------|
| 1 | 「只有**新增题**需要 Publish，编辑 / 删除 / 重排立即生效」 | **被裁决推翻** | **四类变更（新增 / 编辑 / 删除 / 重排）全部经 Publish 才对填报页与维度详情页生效**；配置页始终编辑草稿版本 | §7.9 全节重写 / §6.4 / §8.4 |
| 2 | `erl_question.publish_status` + `published_at` 两个状态位；删除用软删 `enabled` | **模型不够** | 状态位**放不下「编辑前后两份题干」** —— 改为**版本化**：新增 `erl_question_version` 版本表（第 10 张表），`erl_question` 挂 `version_id` + 跨版本稳定的 `question_key`；**删去 `publish_status` / `published_at` / `enabled` 三列**（草稿版本内物理删行，历史由版本快照保住） | §5.1 / §5.1.1 / §3.2 决策表 / §0.2 |
| 3 | 评估与题库无版本绑定 | **缺失** | `erl_assessment` 加 `question_version_id`（作答所依据的题库版本快照）。~~`erl_assessment_answer` 加 `question_key`~~ —— **v3.4 已删除**（其唯一用途是重基迁移，见 §0.6-3） | §5.2 |
| 4 | 发布后在填草稿只能整卷重载（答案丢失） | **不可接受** | ~~按 `question_key` 重基~~ —— **v3.4 已被需求方裁决取代，改为版本锁定（评估不跟随题库）**，见 §0.6 | §0.6 |
| 5 | 写接口按题目 `id` 定位（接口 11 / 12 / 13 / 14） | **契约缺陷** | 写时复制会让草稿行拿到**新 id**，前端手里的 id 属于已发布版本 → **写接口一律改按 `questionKey` 定位**（path 参数与 `reorder` 数组同步改） | §6.4 |
| 6 | Publish 按钮激活条件 = 「有新问题」 | **口径扩大** | 激活条件 = **存在草稿版本**（= 有任意未发布变更）。PRD 原文「五个维度任意维度有新问题」是该条件在「只有新增」场景下的特例，扩大后仍满足 | §6.4 / §8.4 |

**明确不做**（依裁决）：撤回（已发布 → 草稿）、单维度发布、定时发布、版本回滚与版本对比 UI（§12）。

### 0.6 v3.3 → v3.4 修正清单（依据需求方 2026-08-28 的第二次裁决）

**裁决原文**：「**保留旧答案，以正在编辑的版本为准** —— Founder 用 v3 版本打开就是 v3，GSV 用 v4 填。」

即：**评估在创建时绑定当时最新的已发布版本，此后不跟随题库变化**（版本锁定），v3.3 的「打开问卷时按 `question_key` 重基」整体作废。

| # | v3.3 的写法 | 类型 | v3.4 处理 | 影响章节 |
|---|-------------|:---:|-----------|----------|
| 1 | 打开在填评估时按 `question_key` 重基（答案迁移 / 新题留空 / 删题的答案丢弃 / 改题标 `changed`） | **被裁决取代** | **整体删除**，改为**版本锁定**：评估自始至终按 `question_version_id` 渲染与计分。§7.9-⑤ 由「重基」重写为「版本锁定」 | §7.9-⑤ / §6.3 / §9 / §10.1 / §11 |
| 2 | §7.9-①「填报页、维度详情页、计分、组合层、Goldie 输入一律只读**最新已发布版本**」 | **表述错误**（版本锁定下不成立） | 订正为：**只有「新发起一次评估」这一个动作**取最新已发布版本；已存在的评估（草稿 + 已提交）、维度详情页、计分、组合层、Goldie 输入**一律读该评估绑定的版本** | §7.9-① |
| 3 | `erl_assessment_answer.question_key`；唯一约束改为 `(assessment_id, question_key)` | **YAGNI** | **删除该列**，唯一约束**改回 `(assessment_id, question_id)`** —— 该列的唯一用途是重基时迁移答案，重基没了它就没有消费者（`question_key` 仍保留在 `erl_question`，版本 diff 与写接口定位需要） | §5.4 |
| 4 | 接口 5 前置校验 0「提交时绑定版本必须是最新已发布版本，否则 400」 | **必须删除** | 版本锁定下该校验会让旧版本草稿**永远提交不了**。删除该校验，**不阻止**按旧版本提交 | §6.3 / §9 |
| 5 | 接口 3 出参 `rebase{...}`、`ErlAssessmentRebaseService` | **随重基一起删** | 出参只保留 `questionVersionNo`（供页面标注题集版本） | §6.3 / §10.1 |

**本次裁决同时关闭的四条边界**（原 §13-Q13 ~ Q16，详见 §7.10）：

| 原问题 | 结论 |
|--------|------|
| Q13 题干被编辑后旧答案是否仍有效 | **问题消失** —— 在填的评估看不到新题干，答案与题面永远同版本自洽 |
| Q14 删题时已答内容如何处置 | **问题消失** —— 删除只落在新版本，旧版本评估里该题原样保留，**不再有任何用户数据丢失路径** |
| Q15 发布是否触发 Goldie 重生成 | **不触发**（从「设计选择」升级为「逻辑结论」）—— 分析的全部输入都锚在评估绑定的版本快照上，题库发新版后输入一字未变，无从触发 |
| Q16 同期次两端可否不同版本 | **允许**（裁决原文即取值）。后果是 Perception Gap 可能跨两套题集，接受；页面标注两端题集版本号 |

**版本锁定自身新增的三条边界**（已并入 §7.10）：**N1** 旧版本草稿可无限期停留、提交不阻止；**N2** 同期次多次提交可能跨版本，历史列表须标版本号否则像 bug；**N3** 不提供「升级到最新题集」按钮。

---

## 1. 范围与分期

### 1.1 V1 范围

| 模块 | 功能点 | 在 V1 | PRD | 说明 |
|------|--------|:-----:|-----|------|
| A 展示 | **A1 ERL Card（Company Overview 页内）** | ✅ | §3.1 | 综合分 + 当前 Stage + Gap Analysis 摘要 + 5 维列表（维度分 / Perception Gap） + BPMM 参考数字 + 雷达图。**唯一入口，无独立落地页** |
| A 展示 | A2 Dimension Radar 雷达图（卡片内） | ✅ | §5 | 4 条序列：Founder / GSV / Benchmarkit / Top GSV Quartile |
| A 展示 | **A3 维度详情页（Score Details，模板）** | ✅ | §3.2 / §5 | **一套模板 5 维复用**；含 score card 头、Perception Gap、状态摘要、Strengths & Priority Gaps、Data Sources & Cadence、逐题列表、`View history`、`+ New` |
| A 展示 | A5 "How It's Scored?" 评分标准弹窗 | ✅ | §3.8 | 展示该题三段 Era 的评分标准 |
| A 展示 | **A7 DI 卡片下线** | ✅ | §3.1 | 系统级隐藏 DI 卡，数据/KPA/SDP 全保留 |
| B 填报 | B1 Founder 自评问卷 | ✅ | §3.3 | 期次选择、Era 折叠分组、逐题备注 + 附件、进度、自动存草稿、提交即只读 |
| B 填报 | B2 GSV 验证问卷 | ✅ | §3.4 | 同题库 + **每维手动整体分 + 软确认弹窗** + Fund / 评估团队 |
| B 填报 | B3 评估历史列表 | ✅ | §3.9 | 完整保留每次提交，突出最新 SOT |
| C 配置 | C1 题库列表（五维 Tab + Era band 分组） | ✅ | §3.8 | 管理端 |
| C 配置 | C2 新增题目 / C3 编辑删除 | ✅ | §3.8 | 题干 / Era band / Source / 三段式评分标准 |
| C 配置 | **C4 Era Band 内拖拽重排（= 必答顺序）** | ✅ | §3.8 | 含管理员影响提示 |
| C 配置 | **C5 题库版本化 + Publish 发布**（v3.3 改） | ✅ | §3.8 | 配置页改的是**草稿版本**；**新增 / 编辑 / 删除 / 重排全部经 Publish 才生效**；存在草稿版本即激活按钮（§7.9） |
| D 基准 | D1 基准记录页 + **D2 新增记录（独立页）** | ✅ | §4 | Benchmarkit / Top GSV Quartile 的**外部静态数据接入口**，平台不计算；**每期次按五维各录两个分**（v3.1，§0.3） |
| E AI | **E1 Gap Analysis & Suggested Actions** | ✅ | §3.6 | summary + 建议行动；**Founder / GSV 两套口吻**；提交后自动刷新 |
| E AI | **E2 每维 Strengths & Priority Gaps** | ✅ | §5 / §3.6 | 由证据/备注推导；无备注标注「未提供备注」 |
| F 联动 | **F2 Portfolio ERL Tab** | ✅ | §3.7 | 跨公司总表 + 排序筛选 |

### 1.2 明确不在 V1

| 项 | 原因 / 去向 |
|----|-------------|
| 独立 Exit Readiness 落地页 / Dashboard 路由 | **PRD §3.1 明确不做**（v2.1 的 A1/A2 独立页已删除） |
| A4 全维 Score Details 页（原型 `/readiness/overall`） | PRD 无此页；「Score Details」即维度详情页（§0.2-17） |
| 顶栏 Ask Goldie 对话接入（E3） | 与 AI Chatbot 是另一条产品线 |
| Finance 页 Exit Readiness 卡片与入口（F1 / F3） | PRD 未要求；入口统一在 Company Overview 的 ERL Card |
| **完整 BPMM 评估交互** | PRD §5「不在本 story 范围内」；V1 只显示参考数字 |
| Goldie 建议的正式跟踪 / 指派 / Deadline | PRD §3.6「MVP 不含」 |
| Goldie 生成结果的人工编辑 / 审核流 | 见 §13-Q9 |
| 评估期次间对比 / 趋势 / 导出 | PRD 未要求 |
| 「GSV vs. Founder 分数对比 Tab」MVP 替代方案 | PRD §3.6 列为待决定，见 §13-Q6 |
| 题库导入导出、题库公司级覆盖 | PRD 未要求；题库全局单份 |
| Fireflies 转录 / SharePoint 作为 Goldie 数据源 | PRD §3.6 明确为后续阶段 |

### 1.3 后续阶段索引

| 阶段 | 内容 |
|------|------|
| V1（本文档） | A（含 DI 下线）/ B / C / D / E1 / E2 / F2 |
| V2 | 完整 BPMM 评估、Ask Goldie 接入、Fireflies + SharePoint 数据源、Goldie 自动打分 |

---

## 2. 事实基线

### 2.1 存量代码事实（本次落地必须对接的现状，均已核对源码）

| 事实 | 位置 | 对设计的影响 |
|------|------|--------------|
| Company Overview 页的 **DI 卡片**由 `DiStatus` 状态控制显隐 | `CIOaas-web/src/pages/companyOverview/home/CompanyOverviewPage.tsx:82`（state）、`:1561`（`display: DiStatus ? '' : 'none'`） | ERL Card 替换该 DOM 区块；DI 组件保留但不渲染 |
| `DiStatus` 来源于 `getSdpModulesSettings(companyId)` 的 `diStatus`，**按公司维度**存储，另写入 `localStorage.diStatus` | 同上 `:99-109`；`companySettings/components/modules/ModulesTab.tsx` | PRD 要求「**系统级**隐藏」，而现有开关是公司级 → 见 §8.6 与 §13-Q2 |
| Portfolio Company List 的 Tab 键位：`1` General / `2` Investment / `3` Connections / `4` Issues / `5` Benchmarking | `CIOaas-web/src/pages/portfolioCompanies/home/PortfolioCompaniesPage.tsx:501, :825` | ERL Tab 取 **`key='6'`**，并在 `trackPortfolioButtonClick` 埋点分支补 `'ERL'` |
| 各 Tab 的内容组件是 `portfolioCompanies/` 下的**平级目录**（`Benchmarking/`、`Issues/`、`connections/`…） | `portfolioCompanies/` 目录树 | ERL Tab 组件放 `portfolioCompanies/erl/`，**不是** v2.1 写的 `home/components/` |
| 文件直传通道：`storageService.uploadFile(file, fileBusinessType)` → presign → S3 PUT → verify，返回 `fileId` | `CIOaas-web/src/services/service/storage/storageService.ts:114`；类型枚举 `services/api/storage/dto.ts:8` | ERL 逐题附件复用该通道，`fileBusinessType = 'KNOWLEDGE_BASE'` |
| 「公司 Memory File / 知识库」登记 + 向量化的完整链路是 `ensure_kb_space` → `ingest_kb_file` → register → `start_vectorization` | `CIOaas-python/source/chatbot/application/service/chat_attachment_service.py:45-146` | ERL 附件须走**同一条链路**才能被 Goldie 检索到 |
| Python `POST /api/ai/file-registry/records` 是**低层入口**：只建登记行，**不建 rag 条目、不向量化** | `CIOaas-python/source/file_registry/interfaces/routes.py:267-284` | **不能**直接复用它做 ERL 附件登记（会得到检索不到的死文件）→ 见 §6.7 |
| 前端 API 域现有 25 个目录，无 `exitReadiness` | `CIOaas-web/src/services/api/` | 需新增并登记进 `standards/architecture.md` §2，见 §13-Q7 |
| Java 升级脚本最新目录 `sprint116` | `CIOaas-api/deploy/upgrade_doc/` | ERL DDL 落 `sprint{N}`（以实际排期 sprint 为准） |

### 2.2 领域常量（PRD §一）

- **5 维度**：`FRL` Financial Readiness / `PRL` Product Readiness / `BERL` Brand Equity Readiness / `RRL` Risk Readiness / `TRL` Talent Readiness
- **9 级 Stage 分 3 个 Era**：Founder Era（Stage 1–3）、Harvest & Growth Era（Stage 4–6，PRD 注「分数约 6 表示公司进入该纪元，可开始接触投行」）、Exit Era（Stage 7–9）
- **题目 Era band**：9 档下拉 —— `Founder Era - 1/2/3`、`Harvest & Growth - 4/5/6`、`Exit Era - 7/8/9`
- **评估频率**：季度（`Data Sources & Cadence` 中展示为 `Quarterly`）
- **gap severity**：`HIGH` / `MEDIUM` / `LOW`

### 2.3 原型可复用的事实（仅 UI 与口径参考）

> 探查方式：该 Lovable 项目对当前账号是 collaborator 身份，`get_project` / `list_files` 返回 403；改为抓取已发布站点（TanStack Start SSR）的路由 chunk 与渲染 HTML 还原。**原型无后端，全部数据为前端硬编码 mock**，数据模型与接口契约由本文档首次定义。

| 结论 | 证据 | 与 PRD 的关系 |
|------|------|---------------|
| 综合分 = 五维简单平均 | (6.4+5.1+7.5+4.6+2.8)/5 = 5.28 → 显示 `5.3 /9` | ✅ 与 PRD §5 一致，采纳 |
| Perception Gap = Founder − GSV | 五维全部吻合（PRL 7.4−5.1=2.3、BERL 8.1−7.5=0.6、RRL 7.0−4.6=2.4、TRL 5.2−2.8=2.4） | ✅ 与 PRD §5 一致，采纳 |
| 基准为两条独立序列、**按期次 × 五维**存历史 | 基准页 `Latest by Dimension` 卡 + `Add Benchmark Record` 页的五维输入表（2026-08-27 截图） | ✅ 与 PRD §4「外部静态数据独立接入」相容，采纳（§5.6） |
| 旧截图记录表的 `+0.3 vs prior` 环比列 | 旧基准页记录表 | ❌ 新原型两张卡均无此列，**不实现**（§0.3-5） |
| 题量：FRL 31 题，五维合计 165 题 | 自评页进度条 `0 of 165` | ⚠️ PRD §3.3 写「30+ 题目」、§3.9 示例写 `45/45`。**题量由题库配置决定，代码不写死**；见 §13-Q4 |
| FRL 6.4 标 `Exit Era` | 原型渲染 | ❌ **原型 bug**，不予沿用（§7.3） |
| Portfolio ERL Tab 与 Dashboard 分数互相矛盾 | Example 1 两处数值完全不同 | ❌ 两份 mock 各写各的；本设计两处统一走 §7.1 实时计算 |
| 空态文案 `No gap analysis yet` + `Goldie needs scored questions with evidence notes ...` | `GoldieSuggestion` 组件 | ✅ 文案可复用（§9） |

---

## 3. 架构总览

### 3.1 落点

```
CIOaas-web (React 16 / UmiJS 3 / AntD Pro)
   src/pages/companyOverview/home/           A1/A2：ERL Card 替换 DI 卡（改存量页）
   src/pages/exitReadiness/**                ERL 页面群（维度详情 / 填报 / 历史 / 配置 / 基准）
   src/pages/portfolioCompanies/erl/         F2：Company List 第 6 个 Tab（改存量页）
   src/services/api/exitReadiness/           HTTP 调用（1:1 后端接口）
   src/services/service/exitReadiness/       Response ↔ DTO 转换
        |
        |  /api/web/erl/**            <- 前端只调 Java，不直连 Python
        v
Gateway :9000  -->  CIOaas-web(Java) :5213/web
                        com.gstdev.cioaas.web.erl/      <- 新建业务域，DDD 四层
                        |       |
                        |       +- POST /api/ai/erl/gap-analysis       同步 HTTP（LLM 生成）
                        |       +- POST /api/ai/erl/attachments/ingest 同步 HTTP（附件入知识库）
                        |                     v
                        |  CIOaas-python  source/erl/    <- 生成 + 附件编排，不落 ERL 业务表
                        |                 +- 复用 source/llm/ 基建
                        |                 +- 复用 rag ingest_service（ensure_kb_space /
                        |                 |   ingest_kb_file / start_vectorization）与 file_registry 登记
                        |                 +- prompt 放 source/ai/prompts/（Founder / GSV 两套）
                        v
                   PostgreSQL
                     erl_question / erl_assessment / erl_assessment_dimension
                     erl_assessment_answer / erl_answer_attachment
                     erl_benchmark_record / erl_benchmark_dimension
                     erl_gap_analysis / erl_gap_analysis_item
```

- **前端只有一个后端出口**（Java），不出现前端直连 Python 的路径。
- Python 侧**不落 ERL 业务表、不做公司 ACL**（Java 已校验），只做 LLM 生成与知识库入库编排。
- 不使用 SQS：ERL 的 LLM 调用是单次秒级，理由见 §3.2。

### 3.2 关键决策与理由

| 决策 | 理由 | 否掉的替代方案 |
|------|------|----------------|
| ERL 入口是 **Company Overview 页内的卡片**，不建独立落地页 | PRD §3.1 明确要求；卡片是唯一入口 | ❌ v2.1 的 `/exitReadiness` Dashboard 路由 |
| DI 卡片走**开关隐藏**而非删除代码 | PRD §3.1「使用现有 setting/toggle 能力，不删除数据」；DI 的 KPA / SDP 仍在其他页面被引用 | ❌ 删除 DI 组件与接口 |
| 新建 Java 业务域 `erl/`，走 **DDD 四层** | `standards/architecture.md` §1 强制；`quickbooks/`、`thirdParty/` 已是四层实现可作参照 | ❌ 仿照 `fi/` 的扁平结构 —— 那是历史遗留，不得在新域复制 |
| ERL 不并入 `fi/`（财务域） | ERL 覆盖五个维度，不属财务域 | ❌ 放 `fi/erl/` |
| **LLM 生成落 CIOaas-python，Java 经网关同步调用** | Java 侧零 LLM 客户端（全仓检索 bedrock / anthropic / openai / claude 的命中全是 SQS 消息类）；Python 有 `source/llm/` 完整基建 + Prompt 管理规范 + 调用追踪 | ❌ 在 Java 接 LLM SDK —— 要重建模型配置、Prompt 管理、调用追踪 |
| Java 与 Python 之间走 **HTTP 经网关**，不走 SQS | 单次、秒级、用户可等待 | ❌ SQS 异步 —— 为一个秒级调用付全套异步成本 |
| **差距分析提交后自动重生成 + 落库缓存** | PRD §3.6「新评估提交后自动刷新分析」 | ❌ v2.1 的「仅前端手动触发」（与 PRD 冲突）；❌ 每次进页面实时生成（Company Overview 首屏会被 LLM 阻塞） |
| 自动重生成走**提交事务外的异步任务 + 置脏标记**，页面读到脏数据时显示 `Refreshing…` | 提交动作本身不能被 LLM 时延拖住；PRD 只要求「自动刷新」，未要求同步 | ❌ 在提交事务里同步调 LLM —— 提交接口 RT 不可控，LLM 失败会回滚提交 |
| **评估记录不加 `(company, period, portal)` 唯一约束**，改用 `submission_seq` + `is_latest` | PRD §3.3 / §3.9 要求同季多次提交且全量留档 | ❌ v2.1 的唯一约束（会丢历史提交） |
| **GSV 维度分以手动填写为准**，题目推导分只用于软确认 | PRD §3.4 / §3.1 | ❌ v2.1 的「维度分 = 题均分」单一来源 |
| 答案表 `erl_assessment_answer` **一行一题**，不做 JSON 大字段 | 需要按维度 / Era 聚合、按题 join 题库、逐题挂附件与备注 | ❌ `answers jsonb` |
| 草稿与正式提交**同一条记录**，用 `status` 区分；提交后该行冻结，再改则新建下一条 | PRD §3.3「支持保存进度」+「提交后即只读，如需修改必须新建一次提交」 | ❌ 独立草稿表 |
| **题库版本化**：版本表 + 写时复制草稿版本，所有配置变更经 Publish 生效（v3.3，依 2026-08-28 裁决） | 需求方要求「所有变更都经发布」；状态位只能表达「新增未发布」，表达不了「同一题的编辑前后两份题干」 | ❌ v3.2 的 `publish_status` 状态位（编辑无法两态并存）；❌ 双表（草稿表 + 正式表，等于版本化但只能存两代、且两套 DDL 要同步维护） |
| 题目删除 = **在草稿版本内物理删行**（v3.3 改；原为软删 `enabled=false`） | 历史评估绑定题库版本快照，已发布版本的行不会被删，软删标记失去价值 | ❌ 继续软删 —— 版本内还留一堆 `enabled=false` 的行，查询恒要带条件 |
| **必答顺序落在 `erl_question.sort_order`**，配置页拖拽即改该列 | PRD §3.8「该顺序即评估中的必答顺序」 | ❌ 顺序只做展示、计分顺序另存 |
| **计分策略做成可替换的 Strategy**，MVP 只实现 `SCORE_1_9` | PRD §3.3 / §4「以占位形式实现，保证未来切换到 Yes/No + 固定顺序不用重构」 | ❌ 把 1–9 平均逻辑散写在各 service |
| Gap analysis 绑定 **`(company_id, period, audience)`** | 分析要同时读 Founder 与 GSV 两份；PRD §3.6 要求两套口吻 | ❌ 绑单个 `assessment_id`；❌ 只存一份共用 |
| ERL 附件复用**知识库完整入库链路**（ingest + 向量化），不用 `file-registry/records` 低层入口 | 后者只登记不向量化，Goldie 检索不到（§2.1） | ❌ 直接调 `POST /api/ai/file-registry/records` |
| 前端新增 API 域 `exitReadiness/` | `standards/architecture.md` §2 的现有域无一匹配 | 需同步登记进 §2 域表，见 §13-Q7 |

---

## 4. 鉴权与端类型

### 4.1 角色映射

PRD §4 的权限模型 → 平台现有机制：

| PRD 角色 | 平台判定 | 说明 |
|----------|----------|------|
| Company User / Company Admin（Founder 侧） | `user.roleType > 1`，公司锁定 `user.inviteDto.id` | 公司端 |
| Portfolio Manager / Portfolio Group Manager（GSV 侧） | `user.roleType <= 1`，公司取 URL `?id=` | 管理端 |
| ERL Configuration 管理员 | 管理端 **且** 具备配置权限（粒度见 §13-Q7） | 顶部导航右侧下拉入口 |

沿用存量财务页已有的同一套判定（`src/pages/financial/home/FinancialPage.tsx:99`），**不新增端类型机制**：

```
companyId = user.roleType <= 1 ? getQueryString('id') : user?.inviteDto?.id
```

### 4.2 页面与端的对应（按 PRD §3 逐条收紧）

| 页面 / 元素 | 公司端（Founder） | 管理端（GSV） | PRD 依据 |
|------|:---:|:---:|------|
| A1 ERL Card | ✅ 只看本公司 | ✅ 看所选公司 | §3.1 |
| A2 雷达图 **Founder / GSV 两条线** | ✅ | ✅ | §5 |
| A2 雷达图 **Benchmarkit / Top GSV Quartile 两条线** | ❌ **不可见** | ✅ | §3.2「创始人不显示 GSV 专属字段（Benchmarkit、Top GSV Quartile 等）」 |
| A3 维度详情页 | ✅ 只看本公司 | ✅ | §3.2 |
| A3 **GSV Tab（逐题明细）** | ❌ **不显示** | ✅ | §3.2「公司用户不显示 GSV Tab」 |
| A3 Perception Gap / 状态摘要 / 双方维度分 | ✅ | ✅ | §5「创始人并列查看自己的分数与 GSV 分数」 |
| E1 / E2 差距分析（展示） | ✅ 只读，**Founder 口吻** | ✅ 只读，**GSV 口吻** | §3.6 |
| E 手动 Regenerate | ❌ | ✅ | 本设计（自动刷新为主，手动为兜底） |
| B1 Founder 自评问卷 | ✅ **填报** | ✅ 只读查看 | §3.3「portfolio admin 不能代填」 |
| B2 GSV 验证问卷 | ❌ 不可见 | ✅ **填报** | §3.4 |
| B3 评估历史 | ✅ 只看本公司 | ✅ | §3.9 |
| C1–C5 题库配置（含 Publish） | ❌ 不可见 | ✅（admin） | §3.8「仅 admin」 |
| D1 基准记录页 | ❌ **不可见** | ✅ | §3.2（基准属 GSV 专属字段） |
| D2 新增基准 | ❌ | ✅ | §4 |
| F2 Portfolio ERL Tab | ❌ 不可见 | ✅ | §3.7「仅 PM / PGM」 |

> ⚠️ **PRD 内部张力（已按下述口径落地，需产品复核 → §13-Q8）**：§3.2 说「创始人不显示 GSV 专属字段」，而 §5 说「创始人并列查看自己的分数与 GSV 分数」。本设计的裁决是 —— **GSV 的维度分 / 综合分对创始人可见**（Perception Gap 本身就要求可见）；**Benchmarkit 与 Top GSV Quartile 两条外部基准对创始人不可见**；**GSV 的逐题作答明细对创始人不可见**（即 §3.2 的 GSV Tab 隐藏）。

### 4.3 后端强制校验（不依赖前端）

- 所有接口的 `companyId` 一律**服务端复核**：公司端请求忽略入参 `companyId`，强制取当前登录用户所属公司（`SecurityUtils`）；管理端才允许按入参取。
- `portal=GSV` 的读写（B2 填报、A3 的 GSV 逐题明细）、C 模块写接口、D 模块全部接口、E 的生成接口、F2 的跨公司查询，服务端一律校验调用者为管理端，否则 `BadRequestException`。
- **基准值（`benchmarkitScore` / `topQuartileScore`）在公司端请求中一律不返回**，由服务端裁剪，不靠前端隐藏。
- **F2 只返回当前用户有权访问的公司集**，不返回全库。
- Java → Python 的两个内部接口带服务间鉴权；Python 侧不重复做公司 ACL，但**必须落 LLM 调用追踪**（复用 `source/llm/`）。
- 违规一律抛异常交 `GlobalExceptionHandler`，**Controller 内不 try-catch**（`standards/architecture.md` §3）。

---

## 5. 数据模型

> 库：PostgreSQL 业务库。Java 侧 `ddl-auto: update` 由 Entity 自动建表；索引 / 约束 / 种子数据补 `CIOaas-api/deploy/upgrade_doc/sprint{N}/erl_init.sql`。所有实体继承 `AbstractCustomEntity`，自动带 `created_at / created_by / updated_at / updated_by`。主键 `String(36)` + `@UuidGenerator`（与 `quickbooks_*` 一致）。

### 5.1 `erl_question` — 题库（PRD §3.8）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `dimension` | varchar(8) | not null | `FRL` / `PRL` / `BERL` / `RRL` / `TRL` |
| `era_band` | smallint | not null, 1–9 | 题目归属档位；Era 由此推导（1–3 Founder / 4–6 Harvest / 7–9 Exit） |
| `question_text` | varchar(1024) | not null | 题干 |
| `answer_type` | varchar(16) | not null | `SCORE`（1–9）/ `YES_NO` |
| `evidence_source` | varchar(255) | | 来源标签（`Founder / CFO`、`Looking Glass`、`SharePoint`、`GSV Assessment`、`Board Transcripts / Fireflies`…）；空显示 `—` |
| `criteria_founder` | varchar(1024) | | Founder Era（1–3）评分标准 |
| `criteria_harvest` | varchar(1024) | | Harvest & Growth（4–6）评分标准 |
| `criteria_exit` | varchar(1024) | | Exit Era（7–9）评分标准 |
| `sort_order` | int | not null | **同 `dimension + era_band` 内的必答顺序**，配置页拖拽即改此列（PRD §3.8） |
| **`version_id`** | **varchar(36)** | **not null** | **v3.3 新增** → `erl_question_version.id`。**一行只属于一个版本**；版本间整份克隆，故同一道题在 N 个版本里有 N 行 |
| **`question_key`** | **varchar(36)** | **not null** | **v3.3 新增**：**跨版本稳定的题目标识**。克隆时原样复制，新增题时生成新 UUID。**版本 diff（`changeType` / `changeSummary`）与 C 模块写接口定位按它**，不用 `id`。**v3.4**：答案表不再携带它（重基已删除，§0.6-3） |

约束与索引：
- `uk_erl_question_key (version_id, question_key)` —— 同一版本内一个 key 只有一行。
- `idx_erl_question_version_dim (version_id, dimension, era_band, sort_order)` —— 配置页与填报页的主查询路径（**恒带 `version_id`**）。
- 题库**全局单份**（不按公司隔离，PRD 无公司维度题库要求）；**版本序列也全局单份**（不按维度分版本 —— Publish 是全局动作，§7.9）。

**v3.3 删除的三列**（依 §0.5-2）：
- ❌ `publish_status` / `published_at` —— 发布状态上移到**版本级**（§5.1.1）。状态位表达不了「同一道题编辑前后的两份题干必须并存」，而这正是「编辑也要经发布」的硬需求。
- ❌ `enabled`（软删除）—— 删除改为**在草稿版本内物理删行**。已发布版本的行不受影响，历史评估按 `erl_assessment.question_version_id` 读旧版本，题干天然可还原（§11-24）。

### 5.1.1 `erl_question_version` — 题库版本（**v3.3 新增**，第 10 张表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `version_no` | int | not null, 唯一 | 全局递增版本号，从 1 起；配置页显示 `Published v3` / `Draft v4` |
| `status` | varchar(16) | not null | `DRAFT`（在改，未生效）/ `PUBLISHED`（已生效） |
| `based_on_version_id` | varchar(36) | | 克隆来源版本；首版（种子数据）为 `null` |
| `published_at` | timestamp | | `PUBLISHED` 才有值 |
| `published_by` | varchar(128) | | 发布人姓名快照 |
| `change_summary` | varchar(512) | | 发布时算好的变更摘要快照（`added` / `modified` / `removed` / `reordered` 四个计数 + 受影响维度），供发布记录追溯，**不实时重算** |

约束：
- **部分唯一索引** `uk_erl_question_version_draft ON erl_question_version (status) WHERE status = 'DRAFT'` —— **全局同时最多一份草稿版本**。题库全局单份，草稿也就全局单份（多管理员共享同一份草稿，后果见 §7.9）。
- `uk_erl_question_version_no (version_no)`；索引 `idx_erl_question_version_status (status, version_no DESC)`（取「最新已发布版本」的主路径）。

> **为什么不用「双表（草稿表 + 正式表）」**：双表本质就是只能存两代的版本化，却要把 `erl_question` 的全部列复制一份 DDL 并长期同步维护；版本表方案用一列 `version_id` 表达同样的语义，还顺带给了历史评估一个天然的题干快照来源（省掉软删）。

### 5.2 `erl_assessment` — 一次提交（PRD §3.3 / §3.9）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | 形如 `2026Q3` |
| `portal` | varchar(8) | not null | `FOUNDER` / `GSV` |
| `status` | varchar(16) | not null | `DRAFT` / `SUBMITTED` |
| `submission_seq` | int | not null | 同 `(company_id, period, portal)` 内递增序号，从 1 开始 |
| `is_latest` | boolean | not null, 默认 false | **source of truth 标记**；同组内最多一条 `SUBMITTED` 为 true |
| `scoring_mode` | varchar(16) | not null | 提交时生效的计分模式快照（MVP 恒 `SCORE_1_9`），见 §7.2 |
| **`question_version_id`** | **varchar(36)** | **not null** | **v3.3 新增，v3.4 收紧** → `erl_question_version.id`：本次作答所依据的**题库版本快照**。**创建评估时写入当时最新的已发布版本，此后永不改写**（含 `DRAFT` 期间 —— v3.4 取消重基，见 §7.9-⑤）。填报、计分、历史详情、Goldie 输入**全部按此版本**渲染与计算 |
| `submitted_at` | timestamp | | `SUBMITTED` 才有值 |
| `submitter_name` | varchar(128) | | 提交人姓名快照 |
| `submitter_role` | varchar(128) | | 提交人角色快照，如 `Founder & CEO` |
| `fund` | varchar(128) | | 仅 GSV 端 |
| `assessment_team` | varchar(255) | | 仅 GSV 端（PRD §3.4 元数据） |

**约束变更（对 v2.1 的关键修正）**：
- ❌ 删除 v2.1 的 `uk_erl_assessment (company_id, period, portal)` —— 它与 PRD「同一季度允许多次提交」直接冲突。
- ✅ 改为 `uk_erl_assessment_seq (company_id, period, portal, submission_seq)`。
- ✅ **部分唯一索引** `uk_erl_assessment_latest ON erl_assessment (company_id, period, portal) WHERE is_latest` —— 保证同组只有一条 SOT。
- ✅ **部分唯一索引** `uk_erl_assessment_draft ON erl_assessment (company_id, period, portal) WHERE status = 'DRAFT'` —— 同组同时只允许一份在填草稿。
- 索引 `idx_erl_assessment_company_period (company_id, period, portal, submitted_at DESC)`。

提交人姓名 / 角色 / Fund **存快照**：人员离职或改名后历史记录仍显示当时信息。

### 5.3 `erl_assessment_dimension` — 每维汇总（**v3.0 新增**，PRD §3.4 / §3.1）

GSV 端需为每维手动填一个整体分；该手动分是展示口径的 GSV 维度分，题目推导分只用于软确认。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `assessment_id` | varchar(36) | not null | → `erl_assessment.id` |
| `dimension` | varchar(8) | not null | 五维之一 |
| `manual_score` | numeric(3,1) | | **GSV 手动填写的整体维度分**（1–9）；Founder 端为 `null` |
| `derived_score` | numeric(3,1) | | 提交时由题目答案按 §7.1 推导的分数**快照** |
| `divergence_ack` | boolean | not null, 默认 false | 手动分与推导分不一致时用户已软确认 |
| `divergence_delta` | numeric(3,1) | | `manual_score − derived_score`，快照留档便于回溯 |

唯一约束 `uk_erl_assessment_dimension (assessment_id, dimension)`。

> **为什么把 `derived_score` 存快照**：题库可增删（C 模块），事后重算历史提交的推导分会漂移，导致「当时确认过的分歧」无法复现。展示用的**当前**维度分仍实时算（§7.1），此列只服务于审计与软确认留档。

### 5.4 `erl_assessment_answer` — 逐题作答（PRD §3.3 / §3.4）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `assessment_id` | varchar(36) | not null | → `erl_assessment.id` |
| `question_id` | varchar(36) | not null | → `erl_question.id`，**指向作答时所属版本的那一行**（历史详情据此还原当时题干 / Era band / 评分标准） |
| `score` | numeric(3,1) | **nullable** | 仅 `answer_type = SCORE` 的题有值，1–9 |
| `yes_no` | boolean | **nullable** | 仅 `answer_type = YES_NO` 的题有值 |
| **`note`** | **varchar(2048)** | **nullable** | **证据 / 备注（Evidence/Notes），v3.0 新增**；Goldie 的主要输入源（PRD §3.6） |

唯一约束 `uk_erl_answer (assessment_id, question_id)`；索引 `idx_erl_answer_assessment (assessment_id)`。

> **v3.4 删除了 v3.3 加的 `question_key` 列**：它的唯一用途是重基时按稳定键迁移答案；版本锁定后 `question_id` 自始至终不改写，该列没有消费者（YAGNI）。跨版本稳定键 `question_key` 仍保留在 `erl_question` 表 —— 版本 diff 与 C 模块写接口定位需要它。

> **`score` 与 `yes_no` 恰好一个非空**，由 service 层按题目的 `answer_type` 保证；建库脚本补 CHECK 约束 `(score IS NULL) <> (yes_no IS NULL)`。
>
> **`YES_NO` 题不折算成分数、不参与任何分数计算**（2026-08-26 已确认）。它仍是必答题、仍计入完成度，只是不进分母。见 §7.1.1。
>
> `note` 是**可选**字段，PRD §3.3 UX 要点明确「证据/备注字段视觉从属于打分输入，不应看起来是必填」。无备注时 Goldie 侧按 PRD §5 标注为「未提供备注」。

### 5.5 `erl_answer_attachment` — 逐题附件（**v3.0 新增**，PRD §3.3 / §3.4 / §4）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `answer_id` | varchar(36) | not null | → `erl_assessment_answer.id` |
| `file_id` | varchar(36) | not null | 直传通道返回的 `files.id` |
| `file_name` | varchar(255) | not null | 原始文件名快照 |
| `registry_id` | varchar(36) | | 知识库登记行 id（Python 回传）；未入库成功时为 `null` |
| `ingest_status` | varchar(16) | not null | `PENDING` / `SUCCESS` / `FAILED` —— 入 Memory File 的结果 |

索引 `idx_erl_attachment_answer (answer_id)`。

> 附件**先落本表**（保证问卷侧不丢文件），再异步入知识库；`ingest_status` 失败可重试，不阻断评估提交（§6.7）。

### 5.6 `erl_benchmark_record` — 外部基准主表（PRD §4，**v3.1 改粒度**）

一期次一条记录；分数落在 §5.6.1 的维度明细表。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | 形如 `2026Q3`；D2 页输入 `Q3 2026`，前端归一后提交 |
| `note` | varchar(512) | | 基准数据来源 / peer set 变化说明；空显示 `—` |

唯一约束 `uk_erl_benchmark (company_id, period)`。`Recorded` 日期由 `period` 推导（期末日，§7.8），`Recorded by` 用 `created_by`（姓名 + 角色由用户表 join 得到，**不冗余存快照** —— 基准录入人不涉及 §5.2 那种历史留档要求）。

### 5.6.1 `erl_benchmark_dimension` — 每维基准分（**v3.1 新增**，原型 D2「Scores by dimension」）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `record_id` | varchar(36) | not null | → `erl_benchmark_record.id` |
| `dimension` | varchar(8) | not null | `FRL` / `PRL` / `BERL` / `RRL` / `TRL` |
| `benchmarkit_score` | numeric(3,1) | not null | 1–9 |
| `top_quartile_score` | numeric(3,1) | not null | 1–9 |

唯一约束 `uk_erl_benchmark_dim (record_id, dimension)`；索引 `idx_erl_benchmark_dim_record (record_id)`。**一条记录必须齐五维**（D2 页十个输入框全必填，§8.4），否则提交被拒 —— 缺维会让雷达图与维度页基准位置出现空轴。

> **为什么拆两张表而不是在单表加 `dimension` 列**：`note` 与录入人属于「一次录入」的属性，摊到五行会重复且可能不一致（改一次备注要改五行）。该主从结构与 `erl_assessment` / `erl_assessment_dimension`（§5.2 / §5.3）一致。
>
> PRD §4：这两条序列是**外部静态数据输入，不由 Looking Glass 计算**。D 模块即该数据的接入口（管理端手工录入）；未来接自动同步时，只需替换写入方，读取口径不变。

### 5.7 `erl_gap_analysis` — Goldie 差距分析（PRD §3.6）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | |
| **`audience`** | **varchar(8)** | **not null** | **`FOUNDER` / `GSV` —— 两套口吻各存一份（v3.0 新增，PRD §3.6）** |
| `summary` | varchar(2048) | | 整体判断段落 |
| `source_founder_assessment_id` | varchar(36) | | 生成时所依据的 Founder 提交 |
| `source_gsv_assessment_id` | varchar(36) | | 生成时所依据的 GSV 提交 |
| `stale` | boolean | not null, 默认 false | 有更新提交后置 `true`，触发自动重生成（§7.5） |
| `model` | varchar(64) | | 生成所用模型，便于回溯 |
| `generated_at` | timestamp | not null | 前端展示「最后生成时间」 |

唯一约束 `uk_erl_gap_analysis (company_id, period, audience)`。重新生成 = 覆盖本行 + 全量替换其 item 行。

### 5.8 `erl_gap_analysis_item` — 每维优势、差距与建议（PRD §5 / §3.6）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `analysis_id` | varchar(36) | not null | → `erl_gap_analysis.id` |
| `dimension` | varchar(8) | not null | 五维之一 |
| `item_type` | varchar(16) | not null | `STRENGTH` / `GAP` / **`ACTION`** |
| `title` | varchar(512) | not null | STRENGTH 用整句；GAP 用标题；ACTION 用建议动作 |
| `note` | varchar(1024) | | GAP：补充说明；**ACTION：`为何相关`（PRD §3.6 要求说明"为何相关"）** |
| `severity` | varchar(8) | | 仅 GAP：`HIGH` / `MEDIUM` / `LOW` |
| `evidence_missing` | boolean | not null, 默认 false | 该条由**无备注**的题推导而来 → 前端标注「未提供备注」（PRD §5） |
| `sort_order` | int | not null | 组内顺序 |

索引 `idx_erl_gap_item (analysis_id, dimension, item_type, sort_order)`。

> **三类合成一张表**，用 `item_type` 区分，避免三张近乎相同的表。`ACTION` 是 v3.0 新增 —— PRD §3.6 的「Suggested Actions」是独立于 gaps 的产物（「可以做什么」+「为何相关」），v2.1 把它误并进 gaps。

---

## 6. 接口契约

> 统一前缀：Java 侧 `@RequestMapping("/erl")`，前端经网关调 `/api/web/erl/**`。响应统一 `Result<T>`。入参走 `interfaces/vo/request`、出参走 `interfaces/vo/response`（`standards/coding.md` 三层传输实体强制），**禁止直接暴露 Entity**。

### 6.1 ERL Card（A1 / A2，PRD §3.1）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 1 | `GET /erl/card` | Company Overview 的 ERL 卡片一次取全 | `companyId`、`period`（可选，默认最新已提交期次） | `period`、`overallScore`、`stage`、`era`、`bpmmScore`、`gapSummary`、`dimensions[]`、`radar`、`hasAnyAssessment` |

`dimensions[]` 每项：`dimension` / `name` / `founderScore` / `gsvScore` / `perceptionGap` / `gapDirection`（`POSITIVE`/`NEGATIVE`/`NONE`）/ `status`（`MET`/`PARTIAL`/`GAP`，**设计占位枚举**，§7.4 / §13-Q3）/ `era` / `detailUrl`。

`radar`：`series[]`，每项 `{ key, label, values[5] }`，`values` 按 `FRL / PRL / BERL / RRL / TRL` 固定顺序。**公司端只返回 `FOUNDER` / `GSV` 两条序列**；管理端额外返回 `BENCHMARKIT` / `TOP_GSV_QUARTILE`（§4.3）—— 这两条取**适用基准记录的五维分**（§7.8），无适用记录时整条序列不下发（v3.1：v3.0 每期只有两个总分，画不出五顶点）。

- `bpmmScore` 为 1–5 参考数字，来源见 §13-Q1；无数据返回 `null`，前端隐藏该行。
- `gapSummary` 取 §6.6 中**当前用户 audience** 对应的 `summary`，截断展示。

### 6.2 维度详情页（A3 / A5 / E2，PRD §3.2 / §5）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 2 | `GET /erl/dimension/{dimension}` | A3 单维度模板页 | path `dimension`；`companyId`、`period`、`portal`（默认 `FOUNDER`） | `header`、`submission`、`questions[]`、`strengths[]`、`gaps[]`、`actions[]`、`dataSources` |

- `header`：`name` / `abbr` / `questionCount` / `founderScore` / `gsvScore` / `perceptionGap` / `status` / `era` / `benchmarkPosition`（**公司端恒 `null`**）。
  - `benchmarkPosition`：`{ period, benchmarkitScore, topQuartileScore }` —— **本维度**的两个基准分（取 §7.8 的适用记录），供页头与 GSV 分并列对比；无适用记录时为 `null`（v3.1 明确到维度粒度）。
- `submission`：`period` / `submittedBy` / `role` / `submittedAt` / **`questionVersionNo`**（v3.4：元数据栏标注该次提交所用的题集版本，PRD §3.2 元数据栏）。
- `questions[]`：`questionText` / `eraBand` / `eraLabel` / `evidenceSource` / `answerType` / `score` / `yesNo` / `note` / `attachments[]` / `criteria{founder,harvest,exit}`。
  - **A5「How It's Scored?」弹窗不单独发请求** —— 三段评分标准随 `criteria` 返回。
  - `portal=GSV` 且调用者为公司端 → 直接 `BadRequestException`（PRD §3.2 公司用户无 GSV Tab）。
- `strengths[]` / `gaps[]` / `actions[]` 来自 `erl_gap_analysis_item`，按**当前用户 audience** 过滤；无分析记录时为空数组。
- `dataSources`：`{ primary[], supplementary[], cadence: "Quarterly" }` —— **primary / supplementary 由该维度题目的 `evidence_source` 去重聚合得出**（出现次数 ≥ 阈值为 primary，其余 supplementary；阈值见 §7.6），PRD §5「Data Sources & Cadence（按维度）」。

### 6.3 填报（B，PRD §3.3 / §3.4）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 3 | `GET /erl/assessment` | B1 / B2 打开问卷（含回填草稿）；**恒按该评估绑定的题库版本渲染**（§7.9-⑤） | `companyId`、`period`、`portal` | `assessmentId`、`status`、`scoringMode`、`questionVersionNo`、`answeredCount`、`totalCount`、`scoredCount`、`overallAverage`、`dimensions[]` |
| 4 | `POST /erl/assessment/draft` | 自动存草稿（幂等增量） | `companyId`、`period`、`portal`、`answers[{questionId, score?, yesNo?, note?}]`、`dimensionScores[{dimension, manualScore}]`（仅 GSV） | `answeredCount`、`overallAverage`、`savedAt` |
| 5 | `POST /erl/assessment/submit` | 提交 | 同上 + `divergenceAcks[{dimension, ack}]`（仅 GSV） | `assessmentId`、`submissionSeq`、`overallScore`、`stage`、`era` |
| 6 | `GET /erl/assessment/periods` | 期次下拉 | `companyId` | `periods[]`（`period` + 各端 `latestStatus` + `submissionCount`） |
| 7 | `GET /erl/assessment/history` | B3 历史列表 | `companyId`、可选 `dimension`、可选 `portal` | `records[]` |
| 8 | `GET /erl/assessment/{id}` | B3 某次提交的详情（复用 A3 题级布局） | path `id` | 同接口 2 的 `submission` + `questions[]`（该次提交时的状态） |

**规则**：
- **`questionVersionNo`（v3.4）**：该评估绑定的题库版本号。**首次打开（无草稿记录）时取当时最新的已发布版本并落库，此后不再变**；题库后续发布新版本对本次评估**完全无影响**（§7.9-⑤）。前端在问卷页头以次级文字显示 `Question set v{n}`。
- 草稿保存**幂等增量**：只 upsert 传入的 `answers` / `dimensionScores`，不影响未传项。每条 `answers` 按题目 `answerType` 二选一填 `score` 或 `yesNo`，填错的一方由服务端拒绝（§5.4 的互斥约束）。
- `totalCount` 含全部已启用题（含 `YES_NO`）；`scoredCount` 只含 `SCORE` 题，前端用它解释「题数 ≠ 分数分母」（§7.1.1）。
- 提交前置校验：
  1. `answeredCount == totalCount`（**含 `YES_NO` 题**），否则 `BadRequestException("Please answer all questions before submitting.")`。
  2. **GSV 端**：五个维度的 `manualScore` 必填，否则拒绝（PRD §3.4）。
  3. **GSV 端软确认**：`abs(manualScore − derivedScore) > 阈值`（§7.4）的维度必须带 `ack = true`，否则返回 `divergences[]` 让前端弹确认弹窗；**确认后放行，不阻止提交**（PRD §3.4「仅需确认，不阻止提交」）。
- 提交成功后：该行 `status = SUBMITTED`、`is_latest = true`，同组前一条 `is_latest` 置 `false`；`submission_seq` 取组内 `max + 1`。**已 SUBMITTED 的记录不可再改**（PRD §3.3）；再次填报即新建下一条 `DRAFT`。
- `records[]` 字段（PRD §3.9）：`assessmentId` / `period` / `portal` / `submittedAt` / `submitterName` / `submitterRole` / `answeredCount` / `totalCount` / `overallScore` / `stage` / `era` / **`isLatest`**（前端据此突出 SOT 那条）/ **`questionVersionNo`**（v3.4 新增 —— 同期次多次提交可能基于不同题库版本，`Completion` 分母因此不同，不标版本号会被当成 bug，见 §7.10-N2）。默认 `submittedAt DESC`。

### 6.4 题库配置（C，PRD §3.8）

| # | 方法 / 路径 | 用途 | 关键入参 |
|---|-------------|------|----------|
> **v3.3 契约变更**：C 模块的读写**一律面向草稿版本**，写接口的定位参数由题目 `id` 改为 **`questionKey`**（§0.5-5）—— 写时复制会让草稿行拿到新 `id`，前端手里的 `id` 属于已发布版本，按 `id` 定位在「首次编辑」这一步必然失配。

| # | 方法 / 路径 | 用途 | 关键入参 |
|---|-------------|------|----------|
| 9 | `GET /erl/question` | C1 列表（按 `eraBand` 分组、组内带题数、按 `sortOrder` 排序）；**返回草稿版本**，无草稿时返回最新已发布版本 | `dimension` |
| 10 | `POST /erl/question` | C2 新增 | `dimension`、`eraBand`、`questionText`、`answerType`、`evidenceSource`、三段 `criteria` |
| 11 | `GET /erl/question/{questionKey}` | C3 编辑回填 | path `questionKey` |
| 12 | `PUT /erl/question/{questionKey}` | C3 更新 | 同 10 |
| 13 | `DELETE /erl/question/{questionKey}` | C3 删除（**草稿版本内物理删行**） | path `questionKey` |
| 14 | **`PUT /erl/question/reorder`** | **C4 拖拽重排（v3.0 新增）** | `dimension`、`eraBand`、**`questionKeys[]`**（该 band 内的完整新顺序） |
| 21 | **`POST /erl/question/publish`** | **C5 发布草稿版本（v3.3 重定义）** | 无入参；出参 `versionNo`、`publishedAt`、`changeSummary{added,modified,removed,reordered}` |

- **接口 10 / 12 / 13 / 14 均触发写时复制**：进入 service 先 `ensureDraftVersion()` —— 无草稿版本则在**同一事务内**整份克隆最新已发布版本为新草稿（`version_no = max + 1`），再在草稿版本上执行本次变更。四个接口都不改已发布版本一个字节。
- 接口 14 在一个事务内按数组下标重写该 band 全部题目的 `sort_order`；**只允许同 band 内重排**，跨 band 移动请走接口 12 改 `eraBand`。
- 接口 9 出参：根节点增加 `version { versionNo, status, basedOnPublishedVersionNo, lastEditedBy, lastEditedAt }` 与 **`changeSummary { added, modified, removed, reordered, hasDraft }`** —— **`hasDraft` 即 Publish 按钮的激活依据**（存在草稿版本 = 有未发布变更）；每题增加 `changeType`（`ADDED` / `MODIFIED` / `REORDERED` / `UNCHANGED`，由草稿与最新已发布版本按 `question_key` 逐字段 diff 得出），供列表打徽章。**`changeSummary` 是全局的，切 Tab 不重算**（PRD §3.8「五个维度任意维度有变更，按钮即激活」）。
- 接口 21 在一个事务内把草稿版本 `status` 置 `PUBLISHED`、写 `published_at` / `published_by` / `change_summary` 快照。**无草稿版本时返回 400**（前端按钮此时已禁用）；不做「重复点击幂等」的特殊处理 —— 发布成功后草稿已不存在，第二次点击落到同一分支。
- 新增题目（接口 10）`sort_order = 该 band 当前 max + 1`，`question_key` 新生成 UUID。
- **生效范围（v3.3 全改）**：四类变更**全部只落草稿版本**，对填报页、维度详情页、计分、组合层**一概不可见**，直到接口 21 发布。详见 §7.9。

### 6.5 基准（D，PRD §4；**v3.1 按原型重做**）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 15 | `GET /erl/benchmark` | D1 页（两张卡一次取全） | `companyId` | `latest`、`records[]` |
| 16 | `POST /erl/benchmark` | D2 保存记录 | `companyId`、`period`、`note`、`dimensions[5]` | `recordId` |

**出参结构**：

```
latest    { period,                                  // 最新一条记录的期次；无记录为 null
            dimensions[{ dimension, name,            // 固定五维顺序 FRL/PRL/BERL/RRL/TRL
                         benchmarkitScore,
                         topQuartileScore }] }        // 前端按 `6.5/9` 渲染

records[] { id, period, isLatest,
            recordedAt,                              // period 期末日（§7.8）
            recordedBy { name, role },               // created_by join 用户表
            benchmarkitAvg, topQuartileAvg,          // 五维平均，服务端算（§7.8）
            note,                                    // 空返回 null，前端显示 "—"
            dimensions[{ dimension, name, benchmarkitScore, topQuartileScore }] }
```

- `records[]` 按 `period` **倒序**；只有首条 `isLatest = true`（D1 的 `LATEST` 徽章）。
- **`Details` 不额外发请求** —— 每条记录的五维明细随 `records[]` 一并下发（单公司按季度累积，量级极小），前端行内展开 / Modal 渲染，复用 `Latest by Dimension` 的表格组件。
- 接口 16 的 `dimensions[{ dimension, benchmarkitScore, topQuartileScore }]` **必须齐五维、各值在 1–9**，否则 `BadRequestException`；`period` 已存在时返回 `BadRequestException("A benchmark record for this period already exists.")`（唯一约束，§5.6）。
- 两个接口**仅管理端可调**（§4.2），公司端调用直接 400。
- ❌ **删除 v3.0 的 `deltaVsPrior`** —— 新原型两张卡均无环比列（§0.3-5）。

### 6.6 Goldie 差距分析（E，PRD §3.6）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 17 | `GET /erl/gapAnalysis` | E1 + E2 读取（读缓存，不触发 LLM） | `companyId`、`period`、可选 `dimension` | `summary`、`dimensions[{dimension, strengths[], gaps[], actions[]}]`、`generatedAt`、`model`、`stale`、`generating` |
| 18 | `POST /erl/gapAnalysis/generate` | 手动重新生成（仅管理端） | `companyId`、`period` | 同 17 |

- **`audience` 不由前端传**：服务端按调用者端类型判定（公司端 → `FOUNDER`，管理端 → `GSV`），避免越权取到另一套口吻。
- `stale = true`（有更新提交尚未重生成）或 `generating = true` 时，前端在卡片上显示 `Refreshing…` 并展示旧内容，不清空（§7.5）。

**Python 内部接口**（Java 经网关调，非前端可达）：

```
POST /api/ai/erl/gap-analysis

入参  companyId、period、
      dimensions[{ dimension, name, gsvScore, founderScore, perceptionGap,
                   questions[{ questionText, eraBand, eraLabel, evidenceSource, answerType,
                               criteria{founder,harvest,exit},        // Workbook 准入准则
                               founderScore, gsvScore,                 // SCORE 题
                               founderYesNo, gsvYesNo,                 // YES_NO 题
                               founderNote, gsvNote }] }]              // 证据/备注（关键输入）

出参  results[{ audience: FOUNDER|GSV,
                summary,
                dimensions[{ dimension,
                             strengths[string],
                             gaps[{ title, note, severity, evidenceMissing }],
                             actions[{ title, why }] }] }]
```

- **一次调用产出两套 audience**（Founder 口吻「你可以做什么…」/ GSV 口吻「我们建议这家公司…」），避免两次 LLM 往返。
- **`YES_NO` 题的答案照样传给 Python** —— 它不计分，但对判断优势与差距有信息量。prompt 中须说明这类题不参与打分，**不要在文案里编造它的分值**。
- **`criteria` 三段即 PRD §3.6 的「ERL Workbook 各 Stage/维度准入准则」**，是生成建议的依据来源。
- **无备注的题**：prompt 要求在据其产出的条目上置 `evidenceMissing = true`，前端渲染为「未提供备注」（PRD §5）。
- **双方分数均高、无实质差距时**，prompt 明确要求承认此为公司优势，**不得强行套用差距叙述**（PRD §3.6）。
- Python 侧**不落库、不查 ERL 表**：全部输入由 Java 传入，输出交 Java 落库。
- Prompt 放 `source/ai/prompts/erl_gap_analysis_founder.md` 与 `erl_gap_analysis_gsv.md`，带 `# version: x.x`，变更须附回归测试（`CIOaas-python/standards/coding.md` §15）。
- `severity` 值域固定 `HIGH` / `MEDIUM` / `LOW`，在 prompt 中约束并在 Java 侧校验，非法值降级为 `MEDIUM`。

### 6.7 附件入 Memory File（PRD §3.3 / §3.4 / §4）

前端沿用**存量直传通道**，不新建上传接口：

```
① 前端  storageService.uploadFile(file, 'KNOWLEDGE_BASE')   →  fileId
                （内部 presign → S3 PUT → verify，见 §2.1）
② 前端  POST /erl/assessment/draft  带 answers[].attachments[{fileId, fileName}]
③ Java  落 erl_answer_attachment（ingest_status = PENDING）
④ Java  异步 POST /api/ai/erl/attachments/ingest  { companyId, fileIds[] }
⑤ Python  ensure_kb_space → ingest_kb_file → file_registry 登记 → start_vectorization
⑥ Python  回传 [{fileId, registryId, status}]  →  Java 回写 ingest_status / registry_id
```

| # | 方法 / 路径 | 用途 |
|---|-------------|------|
| 19 | `DELETE /erl/assessment/attachment/{id}` | 草稿态删除附件（已提交则拒绝） |

- **为什么不直接调 `POST /api/ai/file-registry/records`**：该接口是低层入口，只建登记行、**不建 rag 条目也不向量化**（§2.1），文件会进知识库列表却检索不到，Goldie 拿不到内容 —— 与 PRD「供 Goldie 后续分析」的目的相悖。
- 入库失败**不阻断评估提交**：`ingest_status = FAILED`，前端在附件旁给重试入口。

### 6.8 组合层 ERL 总表（F2，PRD §3.7）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 20 | `GET /erl/portfolio` | F2 Tab | 可选 `period`、`portfolioId`、`sortBy`、`sortOrder`、`stage`、`minScore`、`maxScore`、`dimension` | `companies[{ companyId, name, overallScore, frl, prl, berl, rrl, trl, stage, era, period, detailUrl }]` |

- **`detailUrl`（v3.2 新增）**：`View` 列的跳转目标 —— PRD §3.7 已改为「跳转到该公司的 **Score Details 页面**」，即该公司的**维度详情页**（§0.2-17）。后端下发 `/exitReadiness/dimension/FRL?companyId={id}&period={period}`，**默认维度 FRL**、带该行取数所用期次；无评估的公司仍下发（进页面看空态）。默认维度是本设计的选择，待产品确认 → §13-Q12。
- 只返回当前登录用户**有权访问的公司集**（§4.3）。
- 每家取其**最新已提交期次**的 `is_latest` GSV 评估；无评估的公司 `overallScore = null`，前端显示 `—`。
- **排序与筛选在服务端做**（PRD §3.7「支持按分数、Stage、维度进行排序与筛选」）：`sortBy ∈ {name, overallScore, stage, FRL, PRL, BERL, RRL, TRL}`；筛选支持 Stage 精确值与分数区间。
- **必须批量聚合**：一次查出全部公司的答案并在内存归组，禁止按公司循环查询（N+1）。

---

## 7. 计算口径与状态流转

### 7.1 分数（PRD §5）

| 口径 | 规则 | 状态 |
|------|------|:---:|
| 单题分 | 仅 `answer_type = SCORE` 的题有分，取 1–9。**`YES_NO` 题不折算、不计分** | 已确认 2026-08-26 |
| **Founder 维度分** | 该维度**已启用且 `answer_type = SCORE`** 的题目得分**算术平均**，保留 1 位小数 | ⚠️ **占位口径**，PRD §5 / §五-3 列为待确认 → §13-Q3 |
| **GSV 维度分** | **取 GSV 提交时手动填写的 `manual_score`**（PRD §3.4 / §3.1），**不是**题目平均 | 已确认（PRD） |
| 综合分 | 五个维度分的算术平均，以 `X/9` 展示，保留 1 位小数 | 已确认（PRD §5 + 原型交叉验证） |
| Perception Gap | `Founder 维度分 − GSV 维度分`；`> 0` 显示 `Positive`，`< 0` 显示 `Negative`，取绝对值展示 | 已确认（PRD §5） |
| Era / Stage | 见 §7.3 | 已确认 2026-08-26 |
| 每维状态摘要 | `MET` / `PARTIAL` / `GAP`，见 §7.4 | ⚠️ **v3.2：枚举取值与阈值均为设计占位**（PRD 2026-08-28 已删去三值明文）→ §13-Q3 |

**展示口径（对 v2.1 的修正）**：v2.1 写「展示页的维度分一律取 GSV 分」，与 PRD 不符。PRD §3.1 卡片列出各维度分数**与** Perception Gap，§5 Scorecard 明确「每维度 Founder 分与 GSV 分」——因此：

- **ERL Card 与维度详情页均并列展示 Founder 分与 GSV 分**；
- **卡片上的「维度分数」列（用于综合分与雷达图 GSV 序列）取 GSV 手动分**；
- 综合分按上述维度分聚合；GSV 侧未提交时的降级见 §9。

> **口径不对称（需产品确认 → §13-Q3）**：GSV 侧维度分来自手动填写，Founder 侧来自题目推导。这意味着 Perception Gap 混合了两种口径。本设计按 PRD 字面落地；若产品希望对称，可选方案是 Founder 端也填手动整体分，或 GSV 端也用推导分（则手动分退化为纯审核动作）。

### 7.1.1 计分范围 ≠ 完成度范围（易错点）

`YES_NO` 题不计分，但**仍是必答题**。两个分母必须分开：

| 用途 | 分母 | 举例（某维度 31 题，含 3 道 YES_NO） |
|------|------|------|
| **维度分 / 综合分** | 只数 `SCORE` 题 | 28 题求平均 |
| **完成度 / 进度条 / 提交校验** | 数**全部**已启用题 | `31 / 31` 才算答满 |

- 维度详情页页头的「31 questions」是**题数**（含 YES_NO），与分数的分母不是同一个数。
- B1/B2 进度、B3 完成度、提交时的 `answeredCount == totalCount` 校验，一律按**全部题**算。
- 某维度**全是 `YES_NO` 题**（无计分题）时，该维度分为 `null`，走 §9 降级；综合分按剩余有分维度平均。

### 7.2 计分策略可切换设计（PRD §3.3 / §4）

PRD 要求：MVP 用 1–9 占位，**未来极可能切到「Yes/No + 固定必答顺序」（某题答 No 后该维度后续题目不再计分）**，且「开发时以占位形式实现，保证未来切换不用重构」。落地方式：

**① 模式枚举与快照**
- `ErlScoringModeEnum`：`SCORE_1_9`（MVP 唯一实现）、`YES_NO_SEQUENTIAL`（预留，V1 不实现）。
- 模式值来自**系统配置项**（单一全局配置，不做公司级），提交时写入 `erl_assessment.scoring_mode` 快照 —— 历史提交永远按当时模式解释，切换模式不改写历史。

**② 策略接口（Java）**

```
public interface ErlScoringStrategy {
    ErlScoringModeEnum mode();
    DimensionScore compute(List<ErlQuestion> orderedQuestions, List<ErlAnswer> answers);
    boolean isCountedInScore(ErlQuestion q, List<ErlAnswer> priorAnswers);
}
```

- 所有维度分计算**只走该接口**，`ErlOverviewService` / `ErlAssessmentService` / `ErlPortfolioService` 一律不内联平均逻辑。
- `orderedQuestions` **按 `sort_order` 有序传入** —— 顺序敏感的 `YES_NO_SEQUENTIAL` 实现届时无需改调用方。
- `isCountedInScore` 的存在使「某题之后的题不计分」成为策略内部细节，前端只消费返回的 `countedQuestionIds`。

**③ 前端占位**
- 接口 3 返回 `scoringMode`；填报页按该值渲染打分控件（`SCORE_1_9` → 1–9 选择器；`YES_NO_SEQUENTIAL` → Yes/No 按钮 + 顺序锁）。
- 题目渲染顺序**恒按后端返回顺序**，前端不重排。

**④ V1 不实现的部分（明确边界）**
- 「No 中断后该维度分数如何处理」的精确规则属 PRD §五-2 待确认项，V1 **不写实现**，只保证接口形状不变（PRD §3.8 也明确该逻辑属评估表/Scorecard story）。

> **关于 PRD 2026-08-28 删去的「部分指标是 0/1 二元、部分为光谱型」**（§0.4-4）：本节的双题型建模（`answer_type ∈ {SCORE, YES_NO}`，§5.1）**不是**由那句话推导来的 —— 它的依据是 §3.3「MVP 用 1–9 占位、未来极可能切 Yes/No + 固定顺序」与 §四「打分格式演进」，这两处 PRD 修订后原样保留。因此该句被删**不触发任何设计变更**；此处留档，避免后续复核时误判为遗漏。

### 7.3 Era / Stage 分段规则（2026-08-26 已确认）

以 **1–3 / 4–6 / 7–9** 分段为准；原型 FRL 6.4 标 `Exit Era` 是**原型错误**，不予沿用。精确边界（分数为 1 位小数，需明确开闭区间）：

| 分数区间 | Era | Stage |
|----------|-----|-------|
| `1.0 ≤ score < 4.0` | **Founder Era** | 1–3 |
| `4.0 ≤ score < 7.0` | **Harvest & Growth** | 4–6 |
| `7.0 ≤ score ≤ 9.0` | **Exit Era** | 7–9 |

**Stage 整数值**：`stage = clamp(round(score), 1, 9)`（PRD §5「当前 Stage（1–9）由综合分数与 Workbook 中的 Era 边界推导」，未给出取整规则）→ 取整方式待产品确认，见 §13-Q3。Era 判定**只按上表区间**，不经由 Stage 二次转换，避免 6.5 → round 7 → Exit Era 的错判。

**交叉验证**：该规则套原型的 6 个数值，5 个与原型显示一致（综合 5.3 → Harvest ✓；PRL 5.1 → Harvest ✓；BERL 7.5 → Exit ✓；RRL 4.6 → Harvest ✓；TRL 2.8 → Founder ✓），唯一不一致的就是被判定为 bug 的 FRL 6.4（原型 Exit，本规则 **Harvest & Growth**）。

> 题目的 `era_band`（1–9 整数档位）到 Era 的映射不受影响：band 1–3 → Founder Era、4–6 → Harvest & Growth、7–9 → Exit Era，整数无边界歧义。

### 7.4 状态摘要与软确认阈值

**① 每维状态摘要（PRD §5「每维度状态摘要，基于 gap 幅度推导」）**

> **v3.2 说明**：PRD 2026-08-28 修订**删去了 `Met / Partial / Gap` 三值枚举**，只保留「基于 gap 幅度推导」。下表的三值与阈值因此**全部是本设计的占位**（v3.0 时它们还有 PRD 明文依据），命名与分档均可由产品整体替换 → §13-Q3。实现上三值收在 `ErlDimensionStatusEnum` + `application/scoring/`，改动面限于一处。

| 状态 | 规则（**枚举与阈值均为占位**，待产品确认 → §13-Q3） |
|------|------|
| `MET` | `abs(perceptionGap) ≤ 0.5` 且双方维度分均 `≥ 7.0` |
| `PARTIAL` | `0.5 < abs(perceptionGap) ≤ 1.5`，或双方分数落在同一 Era 内 |
| `GAP` | `abs(perceptionGap) > 1.5`，或双方分数跨 Era |
| `—` | 任一方未提交（走 §9 降级） |

**② GSV 手动分 vs 推导分的软确认阈值（PRD §3.4）**

- 触发条件：`abs(manual_score − derived_score) > 1.0`。
- 触发后弹**软确认弹窗**，列出分歧维度、两个分数与差值；**用户确认即放行，不阻止提交**。
- 确认结果写 `erl_assessment_dimension.divergence_ack = true` 与 `divergence_delta` 快照。
- 阈值 `1.0` 为占位值，与 §7.4-① 一并待产品确认。

### 7.5 差距分析的生成与刷新（PRD §3.6「新评估提交后自动刷新」）

```
Founder 或 GSV 提交评估（接口 5，事务提交成功）
        |
        +--> 同事务内：UPDATE erl_gap_analysis SET stale = true
        |        WHERE company_id = ? AND period = ?
        |
        +--> 事务提交后（TransactionSynchronization afterCommit）
                 投递异步任务 -> ErlGapAnalysisService.regenerate(companyId, period)
                        |
                        +-- Java 组装输入（双方答案 + 备注 + 题目 criteria）
                        +-- 经网关同步调 Python POST /api/ai/erl/gap-analysis
                        +-- 一次返回 FOUNDER / GSV 两套，落库覆盖，stale = false

页面读取（接口 17）
        |
   +----+----------------+-------------------+
   |                     |                   |
 有缓存且 !stale      有缓存但 stale       无缓存
   |                     |                   |
 直接渲染          渲染旧内容 + "Refreshing…"   空态 §9
                         + 后台任务完成后前端下次进入自然刷新
```

- **置脏的触发点只有「评估提交」一个**（v3.4 明确）：**题库发布新版本不置脏、不重生成** —— 分析的输入（答案 + 题干 + 评分标准）全部取自评估绑定的版本快照，发布后一字未变（§7.9-⑤）。
- **自动重生成是异步的**：提交接口不等 LLM，RT 不受影响；LLM 失败不回滚提交（§3.2）。
- **失败重试**：异步任务失败最多重试 2 次（指数退避），仍失败则保留 `stale = true` 与旧内容，管理端可手动 `POST /erl/gapAnalysis/generate` 兜底。
- **并发去重**：同 `(companyId, period)` 已有生成任务在跑时不重复投递（Redis 短锁，TTL 5 分钟）。
- 已有缓存时管理端页面显示 **Regenerate** 按钮 + `generatedAt`；公司端只读，看不到该按钮。

### 7.6 Data Sources & Cadence 的推导（PRD §5）

- **数据源**：该维度全部已启用题的 `evidence_source` 去重统计。
- **primary / supplementary 划分**：出现题数 `≥ 该维度题数 × 20%` 的来源为 `primary`，其余为 `supplementary`（阈值可配，属展示逻辑，无需产品确认）。
- **cadence**：固定 `Quarterly`（PRD §4「评估周期：季度提交」）。
- 无来源标签的题不参与统计；全维度都无来源时该卡片隐藏。

### 7.7 评估状态流转

```
                    (首次打开问卷)          (自动存草稿)              (提交)
无记录 (seq=n+1) ────────────► DRAFT ──────────────► DRAFT ──────────────► SUBMITTED
                                 ▲                                          │ is_latest=true
                                 │                                          │ 前一条 is_latest=false
                                 └────── 提交后不可回退；再填 = 新建 seq+1 ───┘
```

- `GET /erl/assessment` 命中无草稿时**不建记录**，返回空答案的题目结构；首次 `POST draft` 才落 `DRAFT` 行（`submission_seq = 组内 max + 1`）。
- **只有 `SUBMITTED` 的记录**进 B3 历史列表、ERL Card、维度详情页与 F2 总表。
- **`is_latest = true` 的那条是 source of truth**，展示页与 F2 一律只读它；B3 展示全部。
- 已 `SUBMITTED` 的记录**任何写接口一律拒绝**（PRD §3.3「提交后即只读」）。

### 7.8 基准记录口径（**v3.1 新增**，PRD §4）

| 口径 | 规则 |
|------|------|
| 基准分本身 | **外部输入，平台不计算、不折算**（PRD §4）；1–9，一位小数，按维度存 |
| `benchmarkitAvg` / `topQuartileAvg` | 该记录五维基准分的算术平均，保留 1 位小数（D1 记录表两列）。五维必填，故无缺维分母问题 |
| `recordedAt` | 由 `period` 推导为**期末日**（`2026Q2 → 2026-06-30`），不另存字段 |
| **卡片 / 维度页取哪条记录**（「适用记录」） | 取该公司 `period ≤ 当前展示期次` 中**最近的一条** —— 评估期次晚于最后一次基准录入时沿用最近基准，不留空；无满足条件的记录则视同无基准（§9） |
| `latest` 卡取哪条 | 记录表首条（`period` 最大），卡头显示 `Latest by Dimension · {period}` |
| 与评估分的关系 | 基准**只并列展示，不参与**综合分、Perception Gap、状态摘要（§7.4）的任何计算 |

### 7.9 题库版本化与发布（**v3.3 重写**，PRD §3.8 + 需求方 2026-08-28 裁决）

依裁决：**新增 / 编辑 / 删除 / 重排四类变更全部经 Publish 才生效**（v3.2 的「只有新增题需发布」作废）。PRD §3.8「变更立即生效」一句以裁决为准作废，需回写 PRD（§13-Q11）。

**① 版本模型**

| 概念 | 落地 |
|------|------|
| 已发布版本 | `erl_question_version.status = 'PUBLISHED'` 中 `version_no` 最大的一条。**只被「新发起一次评估」这一个动作读取**（v3.4 订正） |
| 草稿版本 | `status = 'DRAFT'`，**全局最多一份**（部分唯一索引保证）。**只有 ERL Configuration 页读它** |
| 一道题的跨版本身份 | `question_key`（§5.1）。`id` 每版一换，`key` 恒定 |
| 一次评估依据的题面 | `erl_assessment.question_version_id` 快照。**填报页、维度详情页、计分、组合层、Goldie 输入一律读它，而不是最新已发布版本**（v3.4 订正） |

> ⚠️ **v3.4 订正**：v3.3 曾写「填报 / 展示 / 计分 / 组合层一律只读最新已发布版本」—— 那是重基模型下的表述。**版本锁定后它不成立**：一次评估从创建到提交、再到被展示与计分，全程锚在自己的 `question_version_id` 上。取「最新已发布版本」的地方**全系统只有一处** —— 创建新评估记录时（`ErlAssessmentService` 的首次 `POST draft`）。

**② 写时复制（copy-on-write）**

```
管理员在配置页做任一变更（新增 / 编辑 / 删除 / 重排）
        │
        ├── 已有草稿版本？──是──► 直接在草稿版本上改
        │                    否
        │                    └──► 同一事务内：
        │                         整份克隆最新已发布版本的全部题目行
        │                         （question_key 原样复制，id 重新生成）
        │                         新建 DRAFT 版本 version_no = max + 1
        │                         → 再在草稿版本上改
        │
        └──► 填报页 / 维度页 / 计分 此刻读到的仍是旧的已发布版本，毫无变化

管理员点 Publish（接口 21）
        │
        └──► DRAFT.status = PUBLISHED，写 published_at / by / change_summary
             → 此刻起**新发起的评估**用新版本
             → **已存在的评估（含正在填的草稿）继续用各自绑定的旧版本**（v3.4 版本锁定）
             → 下次再改，重新克隆出下一个草稿版本
```

**③ Publish 按钮**

- **激活条件 = 存在草稿版本**。PRD 原文「五个维度任意维度有新问题，按钮会被激活」是该条件在「只有新增」场景下的特例；扩大到四类变更后仍满足原文（有新问题 ⇒ 有草稿版本 ⇒ 激活）。
- 按钮**不分维度**：一次发布整个草稿版本（五维一起），不做单维发布（依裁决，§12）。
- 变更摘要由草稿版本与最新已发布版本按 `question_key` 逐字段 diff 得出（`added` / `modified` / `removed` / `reordered`），用于按钮旁提示与发布确认框。

**④ 多管理员共享同一份草稿（必须知会）**

草稿版本全局单份 ⇒ **两个管理员同时改的是同一份草稿**，且**任一人点 Publish 会把另一人尚未改完的变更一并发布出去**。这是「题库全局单份」的必然结果，不是缺陷，但必须在界面上说清：

- 配置页页头常驻显示 `Draft v{n} · last edited by {name} at {time}`；
- 发布确认框列出**全量变更摘要**（含他人的改动），而不只是当前管理员这次改的部分（§8.4 C5）。

V1 不做草稿的编辑锁、按人隔离的草稿、变更逐条勾选发布 —— 题库配置是低频管理动作，为它上并发控制不划算（§12）。

**⑤ 版本锁定（v3.4 重写，依 2026-08-28 第二次裁决）**

> 裁决原文：「**保留旧答案，以正在编辑的版本为准** —— Founder 用 v3 版本打开就是 v3，GSV 用 v4 填。」v3.3 的重基（rebase）机制**整体删除**。

**规则只有一条**：一次评估在**创建时**绑定当时最新的已发布版本（写入 `erl_assessment.question_version_id`），**此后永不改写** —— 无论期间题库发布了多少个新版本。

| 场景 | 行为 |
|------|------|
| 正在填的草稿，期间题库发布了新版 | **毫无感知**：题目、题序、题数、完成度分母、评分标准全部不变，已答内容原封不动 |
| 题干在新版本里被改了 | 该评估看不到 —— 它读的是自己那版的题面。**答案与题面永远同版本自洽**（原 §13-Q13 消失） |
| 某题在新版本里被删了 | 该评估里这题还在，分数 / 备注 / 附件一个不动（原 §13-Q14 消失，**无任何用户数据丢失路径**） |
| 新版本加了题 | 该评估不会多出未答题，`totalCount` 不变，不会被打断 |
| 提交 | **不校验版本是否最新**（v3.3 的前置校验 0 已删除）—— 半年前开的草稿仍按半年前的题集提交，不阻止 |
| 已 `SUBMITTED` 的记录 | 同样恒按 `question_version_id` 渲染；历史详情、计分、Goldie 输入全部据此（§11-24） |
| 下一次 `+ New` 发起新评估 | 才取当时最新的已发布版本 |

**衍生结论**：

- **同一期次的两端可以不同版本**（裁决明确接受）：Founder 用 v3 提交 → 管理员发布 v4 → GSV 用 v4 填。Perception Gap 因此可能跨两套题集，**不阻止、不告警**，但**两端的题集版本号在 Scorecard 与历史列表上标出**（§7.10-N2）。
- **同一期次多次提交也可能跨版本**：第 1 次 `45/45`（v3）、第 2 次 `47/47`（v4），`Completion` 分母不同是正常现象。
- **Goldie 分析不受题库发布影响**：其输入（答案 + 题干 + 评分标准）全部取自评估绑定的版本快照，题库发新版后输入一字未变 → **发布不触发重生成**（原 §13-Q15 由设计选择升级为逻辑结论）。
- **不提供「把在填评估升级到最新题集」的按钮**（§7.10-N3）：代价是若新版修正了错误的评分标准，在填的人享受不到，需重开一份评估；换来的是「答案与题面永远自洽」这条硬保证。

**⑥ 首版与部署**

- `erl_init.sql` 种子数据落 `version_no = 1`、`status = 'PUBLISHED'`、`published_by = 'system'`，题目行 `question_key` 与 `id` 各自生成 —— 否则系统起来后没有已发布版本，填报页全空。
- 上线后**不允许直接改库里已发布版本的题目行**（会让历史评估的题面漂移）；任何修正都走配置页 → 草稿 → Publish。

### 7.10 版本化的边界（**v3.3 新增** —— 开发前逐条对齐）

题库版本化把「题面」从一份变成多份，随之产生一批**必须明确取值、否则实现会各写各的**的边界。下表是全量清单：**A 类**由裁决直接给出、**B 类**本设计已取默认值（需求方知悉即可）、**C 类**会改变实现结果，**必须产品拍板**（已登记 §13-Q13 ~ Q16）。

| # | 边界 | 类 | 本设计取值 | 若取反面 |
|---|------|:--:|-----------|----------|
| 1 | **发布粒度** | A | 一次发布整个草稿版本（五维一起） | 单维发布 —— 裁决已明确不做 |
| 2 | **撤回 / 回滚** | A | 不做（已发布不可退回草稿，无版本回滚 UI） | 需要版本切换与「当前生效版本」指针，模型要再改一层 |
| 3 | **变更类型** | A | 新增 / 编辑 / 删除 / 重排**四类全部**经发布 | v3.2 的「只有新增经发布」——已作废 |
| 4 | **草稿唯一性** | B | **全局一份草稿**，多管理员共享；任一人发布会连带发布他人未完成的改动（§7.9-④） | 每人一份私有草稿 → 需要三方合并与冲突解决，V1 不划算 |
| 5 | **丢弃草稿** | B | **不做**。误改只能手工改回来（变更摘要可见，题库低频） | 加 `DELETE /erl/question/draft` 即可，不影响模型（§12） |
| 6 | **评估是否跟随题库** | A | **不跟随（版本锁定）** —— 评估创建时绑定版本，此后题库发布多少版都与它无关（v3.4 裁决，§7.9-⑤） | 重基（v3.3 方案）—— 已被裁决取代 |
| 7 | **版本数据保留** | B | 每发布一版整份克隆题目行，**永久保留、不清理**（165 题 × 一年 20 版 ≈ 3300 行，无压力） | 定期归档旧版本 —— 会让历史评估取不到题面，不可做 |
| 8 | **谁能 Publish** | B | C 模块的 admin 均可，不再分级 | 若需「编辑者 / 发布者」分权，属 §13-Q7 的角色细化 |
| 9 | **组合层跨版本可比性** | B | 不做提示 —— F2 总表可能同屏比较基于不同题库版本的分数 | 要提示则需在表内标版本号，噪音大于价值（V1 不做趋势对比） |
| 10 | ~~题干被编辑后旧答案是否仍有效~~ | **A** | **问题消失**（v3.4）—— 评估看不到新题干，答案与题面永远同版本自洽 | — |
| 11 | ~~删题时该题的已答内容~~ | **A** | **问题消失**（v3.4）—— 删除只落新版本，旧版本评估里该题原样保留。**全设计无用户数据丢失路径** | — |
| 12 | **发布是否触发 Goldie 重新生成** | **A** | **不触发**（v3.4 由设计选择升级为逻辑结论）—— 分析输入全部锚在评估绑定版本上，题库发新版后输入一字未变 | — |
| 13 | **同一期次两端可否基于不同版本作答** | **A** | **允许**（v3.4 裁决原文即取值）。不阻止、不告警，但**两端版本号在 Scorecard 与历史列表标出** | 要求两端同版本 —— 会让「发布」被在填评估无限期阻塞 |
| **N1** | **旧版本草稿的时效** | B | **可无限期停留**：提交时**不校验**绑定版本是否最新，半年前的草稿按半年前的题集提交 | 设过期时间强制重开 —— 会丢已填内容，与「不丢数据」的取向冲突 |
| **N2** | **同期次多次提交跨版本** | B | **允许**：第 1 次 `45/45`（v3）、第 2 次 `47/47`（v4）。**历史列表与 Scorecard 必须标题集版本号**，否则分母不同会被当成 bug | 强制同期次同版本 —— 同 13 的问题 |
| **N3** | **在填评估「升级到最新题集」按钮** | B | **不做**。代价：新版若修正了错误的评分标准，在填的人享受不到，需重开一份 | 做升级按钮 —— 等于把已删除的重基又请回来 |

> **v3.4 后本表已无 C 类**（需产品拍板的边界）—— 第 10–13 条随「版本锁定」裁决一并关闭，§13 的 Q13 ~ Q16 同步关闭。取「最新已发布版本」的代码路径全系统只有一处（创建评估记录时），是本模块的**唯一版本入口**，代码审查专项检查。

---

## 8. 前端设计（功能级）

### 8.1 路由（`config/routes.ts`）

| URL | component | 页面 | 变化 |
|-----|-----------|------|------|
| `/companyOverview` | `./companyOverview/home` | **A1 / A2 ERL Card** | **改存量页，不新增路由** |
| `/exitReadiness/dimension/:dimension` | `./exitReadiness/dimension` | A3 / A5 / E2 | 新增 |
| `/exitReadiness/assessment` | `./exitReadiness/assessment` | B1（`?portal=gsv` 切 B2） | 新增 |
| `/exitReadiness/history` | `./exitReadiness/history` | B3 | 新增 |
| `/exitReadiness/history/:assessmentId` | `./exitReadiness/history/detail` | B3 单次提交详情 | 新增 |
| `/exitReadiness/benchmark` | `./exitReadiness/benchmark` | D1 基准记录页（两张卡） | 新增，仅管理端 |
| `/exitReadiness/benchmark/add` | `./exitReadiness/benchmark/add` | **D2 新增记录（独立页，非 Modal）** | 新增，仅管理端（v3.1，§0.3-3） |
| `/exitReadiness/configuration` | `./exitReadiness/configuration` | C1 + C3 删除 + C4 拖拽 | 新增，仅 admin |
| `/exitReadiness/configuration/add` | `./exitReadiness/configuration/add` | C2 | 新增 |
| `/exitReadiness/configuration/edit/:id` | `./exitReadiness/configuration/edit` | C3 | 新增 |

**对 v2.1 的删除**：
- ❌ `/exitReadiness`（Dashboard）—— PRD §3.1「不设独立 Exit Readiness 落地页」。
- ❌ `/exitReadiness/scoreDetails`（A4 全维明细）—— PRD 无此页。

**F2 不新增路由** —— 它是 `/company`（`./portfolioCompanies/home`）页内的**第 6 个 Tab**（`key='6'`）。

**菜单入口**（PRD §3.1 / §3.8）：
- ERL 展示入口**只在 Company Overview 的 ERL Card 上**，主导航不新增一级菜单。
- **ERL Configuration 挂顶部导航右侧下拉菜单**（PRD §3.8），仅 admin 可见。
- B1/B2 填报入口在 **Assessments 区块**内（PRD §3.3 / §3.4）；另从维度详情页的 `+ New` 进入。
- C 模块路由对管理端可见，公司端由菜单与路由守卫双重拦截。

### 8.2 目录结构

遵循 `CIOaas-web/CLAUDE.md`「同域多功能归入域文件夹作第二层」「域根须有 README.md」「转发式 index.tsx 仅限路由页面入口」：

```
src/pages/exitReadiness/
├── README.md                      域文档（职责 / 目录 / 域内要求）
├── components/                    域级共享：
│                                  ErlRadarChart(A2)、DimensionScoreRow、EraProgressBar、
│                                  QuestionRow、ScoringCriteriaModal(A5)、
│                                  EvidenceNoteField、AttachmentUploader、
│                                  GapAnalysisPanel(E1)、StrengthsGapsActions(E2)、
│                                  DataSourcesCadenceCard、PeriodSelect、PortalTabs、
│                                  StatusBadge、constants.ts、types.ts
├── dimension/{index.tsx, DimensionPage.tsx, hooks/, components/}
├── assessment/{index.tsx, AssessmentPage.tsx, hooks/, components/}
├── history/{index.tsx, HistoryPage.tsx, detail/, hooks/, components/}
├── benchmark/{index.tsx, BenchmarkPage.tsx, add/, hooks/, components/}
│                                  components/ 内含 BenchmarkDimensionTable（D1 两张卡与 D2 表单共用五维行结构）
└── configuration/{index.tsx, ConfigurationPage.tsx, add/, edit/, hooks/, components/}

改存量页：
src/pages/companyOverview/home/
├── CompanyOverviewPage.tsx        DI 卡区块 → 渲染 ErlCard；DI 分支保留但不再进入
└── components/ErlCard/            A1 卡片（含 A2 雷达图，复用 exitReadiness/components/）

src/pages/portfolioCompanies/erl/  F2 Tab 内容组件（与 Benchmarking/ Issues/ 平级）
├── index.tsx                      表格 + 排序筛选
└── hooks/useErlPortfolio.ts
```

分层口径按 `standards/architecture.md` §3：`index.tsx` 只转发；`XxxPage.tsx` 组装 hooks 与 components；**业务逻辑（调 API / 管状态）只写在 `hooks/`，`components/` 收 DTO props 不调 API**。

> ErlCard 放 `companyOverview/home/components/` 而非 `src/components/` —— 当前只此一处使用（YAGNI）；其内部复用的雷达图等下沉在 `exitReadiness/components/`，跨域 import 只允许 import 该域的公开组件与 `erlService`。

### 8.3 服务层（`src/services/`）

```
services/api/exitReadiness/       erlApi.ts / request.ts / response.ts / dto.ts / README.md
services/service/exitReadiness/   erlService.ts   （Response ↔ DTO 转换，跨页面复用）
```

F2 的 `GET /erl/portfolio`、ERL Card 的 `GET /erl/card` 均归入 `exitReadiness/` 域（**按后端接口归域，不按页面归域**）。

### 8.4 关键交互

| 交互 | 设计 | PRD 依据 |
|------|------|------|
| **A1 ERL Card 内容** | 综合分（`X/9`）+ 当前 Stage 徽章 + Gap Analysis 摘要 + 5 维列表（维度分 / Perception Gap / 状态徽章 / `View Details →`）+ BPMM 参考数字（1–5）+ 雷达图 | §3.1 |
| **A1 卡片位置** | 占据原 DI 卡片的 DOM 位置与栅格宽度，视觉与 Financial Intelligence 卡对齐 | §3.1 |
| **A2 雷达图规范** | **仅线条无填充**、每条序列不同色、**有图例**、**中心轴隐藏**；5 个顶点标注五维；域 `0–9`；**悬停数据点显示该维度 + 该 perspective 的精确分数** | §5 |
| **A2 序列可扩展** | `series[]` 由后端下发，前端按数组渲染，**不硬编码 4 条** —— 后续新增 perspective 无需改前端 | §5「预留后续新增 perspective 的能力」 |
| **A3 模板参数化** | 维度名称、缩写、简介、主题色收在 `components/constants.ts` 的 `DIMENSIONS` 映射，页面按 `:dimension` 取；**禁止**在 5 个分支里硬编码文案 | §3.2「同一套模板，通过 dimension 参数驱动」 |
| **A3 Founder / GSV Tab** | 双 Tab 切换逐题明细；**公司端不渲染 GSV Tab**（且后端拒绝该请求） | §3.2 |
| **A3 元数据栏** | Period / Submitted By / Role / Submitted At | §3.2 |
| **A3 `View history`** | 跳 `/exitReadiness/history?dimension={dim}`，**限定当前维度** | §3.2 |
| **A3 `+ New`** | 公司端跳 B1、管理端跳 B2（带当前 `period` 预选） | §3.2 |
| **A3 面包屑** | `Exit Readiness ›〔Dimension Name〕`，返回落回 Company Overview | §3.1 / §4 |
| **A3 维度间跳转** | 页头提供 5 个维度 chip 切换器，不必回卡片 | 本设计（模板页自然延伸） |
| **A5 评分标准弹窗** | 每题右侧 `How It's Scored?` 图标，弹出三段 Era 标准；数据随题目返回，不额外请求 | §3.8（三段式评分标准） |
| **B 打分标度图例** | 每个 Era section 顶部显示 `1–3 Founder Era / 4–6 Harvest & Growth / 7–9 Exit Era` 图例 | §3.3 UX |
| **B Era 折叠分组** | 每维度内按 3 个 Era 折叠分组，组头显示题数与已答数 | §3.3 UX「避免长度令用户不堪重负」 |
| **B 证据/备注字段** | 折叠式次级输入，**视觉从属于打分输入，不呈现为必填**；占位文案 `Add evidence or notes (optional)` | §3.3 UX |
| **B 附件上传** | **轻量小图标**紧邻备注，不喧宾夺主；已传文件以小 chip 列出（文件名 + 删除 + 失败重试） | §3.3 UX |
| **B 来源标签** | 每题显示 `Source: {evidenceSource}`，空显示 `—` | §3.3 / §3.4 |
| **B 自动存草稿** | 打分/备注变更后本地即时更新进度与均分；**去抖 1.5s 批量 POST**；保存中/已保存状态在吸底条提示；离开页面前 flush | §3.3「自动保存无感」 |
| **B 提交** | 吸底提交条；未答满时按钮禁用并提示剩余题数；**提交确认弹窗须明确告知：提交后锁定为只读、如需修改要新建提交、下一步是对方独立评估后出现对比** | §3.3 UX |
| **B2 每维手动整体分** | 每个维度分组头部一个 1–9 输入；**未填不可提交** | §3.4 |
| **B2 软确认弹窗** | 提交时若某维 `abs(手动分 − 推导分) > 1.0`，弹窗列出分歧维度与两个数值，文案「Your manual score differs from the score derived from your answers.」+ Confirm / Back；**Confirm 即放行** | §3.4「仅需确认，不阻止提交」 |
| **`YES_NO` 题呈现** | 填报页渲染 Yes / No 两个按钮；A3 逐题列表右侧显示 `Yes` / `No` 徽章**而非 `x.x/9`**，并带 `Not scored` 次级标注 | §3.3（打分格式占位） |
| **题数与分数分母说明** | A3 页头显示 `{totalCount} questions · {score}/9`；当 `scoredCount < totalCount` 时分数旁加 tooltip：`Score averages the {scoredCount} scored questions; Yes/No questions are not scored.` | §7.1.1 |
| **只读态** | 公司端打开 B2、或打开已 `SUBMITTED` 的记录时，问卷渲染为只读（无输入、无提交条） | §3.3 |
| **E1 展示** | ERL Card 内为 summary 摘要（截断 + `View details`）；维度详情页内为完整 summary + 该维 `actions[]`（每条：动作标题 + 「为何相关」说明） | §3.1 / §3.6 |
| **E1 口吻** | 文案由后端按 audience 生成，前端不做措辞转换 | §3.6 |
| **E2 区块（A3 内）** | 左 Strengths 列表；右 Priority Gaps 条目（`title` 加粗 + `note` 次级文字 + severity 色标徽章 HIGH 红 / MEDIUM 黄 / LOW 灰）；`evidenceMissing` 的条目追加灰色标注 `No notes provided` | §5 |
| **Data Sources & Cadence** | A3 内独立卡片：`Primary sources` / `Supplementary sources` 两组标签 + `Cadence: Quarterly` | §5 |
| **BPMM** | ERL Card 内一行参考数字 `BPMM {n}/5`，带 tooltip 说明为参考值；无数据隐藏 | §5 |
| **B3 历史列表** | 列：Period / Portal / Submitted By（姓名 + 角色）/ Completion（`45/45`）/ Overall Score（含 Stage 徽章）；最近在前；**`isLatest` 那条加 `Current` 徽章 + 高亮底色**，其余行标题色降级，避免误当作现行有效记录；**Completion 旁以次级文字标 `v{n}`（v3.4）** —— 同期次两次提交可能基于不同题集，分母不同不标版本会被当成 bug（§7.10-N2） | §3.9 |
| **B 题集版本标注**（v3.4） | 问卷页头、维度详情页元数据栏、Scorecard 的 Perception Gap 旁，均以次级文字显示 `Question set v{n}`；Founder 与 GSV 版本号不同时，Perception Gap 旁并列显示两个版本号（不告警、不阻止，§7.9-⑤） | §7.10-13 / N2 |
| **B3 详情** | 点击某行进 `/exitReadiness/history/:assessmentId`，复用 A3 的题级布局呈现该次提交时的状态 | §3.9 |
| **C1 分组** | 五维 Tab + 组内按 Era band 折叠分组，组头显示题数 | §3.8 |
| **C4 拖拽重排**（v3.3 改） | Era band 内拖拽 handle 排序，松手即调接口 14 **写入草稿版本**（不影响填报页，直到 Publish）；行上出现 `Moved` 徽章；**首次拖拽弹一次性提示**：「Reordering changes the required answering sequence. It takes effect when you publish. Submitted assessments keep the order in effect at the time.」 | §3.8「需考虑对进行中或历史评估解释产生的潜在影响，给管理员必要的警告」 |
| **C3 删除** | `Modal.confirm` 二次确认，文案含所属维度、提示**删除在发布后才生效**、说明已提交的历史评估仍按当时版本展示该题 | §3.8 |
| **C5 版本条**（v3.3） | 配置页页头常驻一行：无草稿时 `Published v{n} · {date}`；有草稿时 `Draft v{n} — unpublished changes · last edited by {name} at {time}`，整页加浅色「编辑中」边框，提示当前所见**不是**填报页正在用的题面 | §7.9-④ |
| **C5 Publish 按钮**（v3.3 改） | 页面右上角主按钮 `Publish`；**存在草稿版本即激活**（任意维度的任意变更，与当前所处 Tab 无关），无草稿时禁用 + tooltip `No unpublished changes.`；按钮旁显示 `{a} added · {m} modified · {r} removed · {o} reordered`；点击弹确认框列出**全量变更摘要（含其他管理员的改动）**并提示「发布后所有变更立即对填报页与 Score Details 生效；正在填写的评估会保留已答内容」，确认后调接口 21，成功 toast `Published v{n}.` 并刷新列表 | §3.8 + 2026-08-28 裁决 |
| **C5 变更徽章**（v3.3） | 草稿版本中，题目行按 `changeType` 打徽章：`New` / `Edited` / `Moved`；被删除的题**不再显示**（草稿内已物理删行），删除动作的痕迹只体现在按钮旁的摘要计数里 | §7.9-③ |
| **C5 离开页面**（v3.3） | 草稿是服务端持久对象、非表单脏数据，离开不拦截、不弹确认；但五维 Tab 头对**含未发布变更**的维度加小圆点，避免管理员漏发某一维 | 本设计（§7.9） |
| **D1 页头** | 面包屑 `Portfolio Companies › {公司名} › Top GSV Quartile & Benchmarkit`；标题下一句说明「Reference scores used to compare this company's Exit Readiness against the GSV top quartile and the Benchmarkit peer set. Each entry is kept as a dated record.」；右上 `+ Add New` | §4 + 原型（§0.3） |
| **D1 卡一：Latest by Dimension** | 卡头 `Latest by Dimension · {period}`；表格三列 `DIMENSION` / `BENCHMARKIT` / `TOP GSV QUARTILE`，五行；维度列 `**FRL** Financial Readiness`（缩写加粗 + 全称次级色）；分值格式 `6.5/9`，`/9` 次级字号 | 原型（§0.3-4） |
| **D1 卡二：Record History** | 列 `PERIOD`（最新一条加 `LATEST` 徽章）/ `RECORDED`（期末日）/ `RECORDED BY`（姓名 + 角色两行）/ `BENCHMARKIT (AVG)` / `TOP GSV QUARTILE (AVG)`（同 `x.x/9` 格式）/ `NOTE`（空显示 `—`）/ `ACTIONS`；按期次**倒序** | 原型（§0.3-6） |
| **D1 `Details`** | 展开该记录五维明细，复用 `BenchmarkDimensionTable`；数据已随列表返回，**不发新请求**（§6.5） | 本设计 |
| **D2 独立页** | 路由 `/exitReadiness/benchmark/add`，页首 `< Back` 回 D1；标题 `Add Benchmark Record` + 说明「Enter the Benchmarkit and Top GSV Quartile reference scores (1–9) for each of the five Exit Readiness dimensions for a reporting period.」 | 原型（§0.3-3） |
| **D2 表单** | `Period` 输入（placeholder `e.g. Q3 2026`）→ `Scores by dimension (1–9)` 表格（五行 × 两列数字输入，placeholder 示例 `6.8` / `7.9`）→ `Note (optional)` 文本域（placeholder `Source of the benchmark data, peer set changes, etc.`）；底部右对齐 `Save Record`（主按钮）/ `Cancel` | 原型（§0.3） |
| **D2 校验与返回** | 十个分数框**全必填**、范围 1–9、最多一位小数；`Period` 必填并归一为 `{YYYY}Q{n}`；期次重复由后端 400，错误挂在 `Period` 字段下且**已填分数不清空**；保存成功回 D1 并刷新两张卡 | §5.6 / §6.5 |
| **F2 ERL Tab** | 与现有 5 个 Tab 同一套表格样式（`key='6'`）；列 Company / ERL Score / FRL / PRL / BERL / RRL / TRL / Stage / View；ERL Score 与 Stage 按分数着色；**表头支持排序、顶部提供 Stage 与分数区间筛选器** | §3.7 |
| **F2 `View` 跳转**（v3.2 改） | 末列 `View →` 跳该公司的 **Score Details 页面 = 维度详情页**（§0.2-17），取后端下发的 `detailUrl`（默认维度 `FRL`，带该行期次），前端不拼路径；到页后可用页头维度 chip 横切五维，面包屑首级回该公司 Company Overview。**v3.1 的「跳 Company Overview 锚点定位 ERL Card」作废** | §3.7「View（跳转到该公司的 Score Details 页面）」（2026-08-28 修订） |
| **响应式** | 桌面 + 移动均可用；表格类窄屏横向滚动、卡片单列堆叠、雷达图等比缩放 | §4「所有页面覆盖桌面与移动端」 |
| **国际化** | 文案走 `locales/`，不硬编码中文 | 前端规范 |

### 8.5 ERL Card 与维度详情页的职责划分（对 PRD 的落地解释）

PRD 中「Scorecard」（§5）的展示项分散在两处，本设计的归属如下（需产品复核 → §13-Q8）：

| PRD §5 展示项 | 落在 ERL Card | 落在维度详情页 |
|---------------|:---:|:---:|
| 综合 ERL 分数 | ✅ | ✅（页头） |
| 当前 Stage 与 Era | ✅ | ✅ |
| 每维度 Founder 分与 GSV 分 | ✅（列表） | ✅（页头，仅本维） |
| 每维度 Perception Gap | ✅ | ✅ |
| 每维度状态摘要（基于 gap 幅度推导，§7.4） | ✅（徽章） | ✅ |
| Strengths & Priority Gaps | ❌ | ✅ |
| Data Sources & Cadence | ❌ | ✅ |
| BPMM 参考数字 | ✅ | ❌ |
| 雷达图 | ✅ | ❌（本维不适用五维雷达） |
| 访问历史评估记录 | ❌ | ✅（`View history`） |
| Gap Analysis & Suggested Actions | ✅（摘要） | ✅（完整） |

依据：PRD §3.1 明确列出卡片内容清单（综合分 / Stage / Gap 摘要 / 5 维列表 / BPMM / 雷达图），§3.2 明确列出维度页内容，§5 的其余展示项按「按维度」的措辞归入维度页。

### 8.6 DI 卡片下线方案（PRD §3.1）

PRD 要求：**系统级隐藏** DI 卡片，用现有 setting/toggle 能力，**不删除数据**；DI 数据、KPA 评估、SDP 打分完整保留但不再展示。

现状（§2.1）：`CompanyOverviewPage.tsx` 的 DI 区块由 `DiStatus` 控制，值来自 `getSdpModulesSettings(companyId).diStatus`，是**公司级**开关，且与 SDP 权重（`diWeight` / `fiWeight`，两者需合计 100）耦合。

落地方案：

1. **前端**：`CompanyOverviewPage.tsx` 中 DI 区块的渲染条件改为 `DiStatus && !erlEnabled`，`erlEnabled` 来自新增的**全局配置项**；ERL Card 在 `erlEnabled` 时渲染于同一位置。DI 的 JSX、数据请求（`getDevelopmentIntelligenceScore` 等）与下钻页面**全部保留**，只是不再进入渲染分支。
2. **后端**：新增系统级配置 `erl.enabled`（全局单值，非公司级），随 Company Overview 的现有配置接口一并下发。
3. **不动 `diStatus` / `diWeight`**：这两个值仍影响 SDP 总分与 Company Settings 的模块页，改它们会连带改分数 —— 与「数据完整保留」冲突。
4. **Company Settings 的 Modules 页**：ERL 上线后 DI 开关对 Company Overview 不再产生可见效果，需在该处加一行说明（否则管理员会困惑于「打开了却不显示」）。

> ⚠️ 「系统级」与现有「公司级」开关的差异是本方案的主要风险点 —— 是否需要保留按公司回退到 DI 的能力，见 **§13-Q2**。

---

## 9. 失败降级

| 场景 | 服务端 | 前端表现 |
|------|--------|----------|
| 该公司无任何已提交评估 | 接口 1/2 返回空结构（分数 `null`、`hasAnyAssessment=false`） | ERL Card 显示空态「No assessment submitted yet.」+ 去填报入口；不显示雷达图 |
| 只有 Founder 提交、GSV 未提交 | `gsvScore = null`、`perceptionGap = null`、`status = '—'` | 维度行显示 Founder 分并标注 `Awaiting GSV validation`，Perception Gap 隐去；雷达图 GSV 序列不绘制 |
| 只有 GSV 提交、Founder 未提交 | `founderScore = null`、`perceptionGap = null` | 对称处理，标注 `Awaiting founder self-assessment` |
| **GSV 已提交但某维手动分为空**（历史数据 / 异常） | 该维 `gsvScore` 回退取 `derived_score` 并置 `scoreSource = 'DERIVED'` | 分数旁加 tooltip `Derived from answers` |
| 无基准记录 | `benchmarkPosition = null`、`latest = null`、`records = []`、雷达图两条基准序列缺省 | A3 隐去基准位置项；D1 两张卡合并为一处空态 `No benchmark records yet.` + `Add New`；雷达图图例不显示缺失序列 |
| **展示期次早于最早一条基准记录** | 无 `period ≤ 当前期次` 的记录（§7.8） → 同「无基准记录」处理，**不取更晚的记录反填** | 同上 |
| **D2 保存时该期次已存在** | 唯一约束冲突 → `BadRequestException` | `Period` 字段下报错 `A benchmark record for this period already exists.`；已填的十个分数与备注保留 |
| **公司端请求** | 服务端裁剪掉 `BENCHMARKIT` / `TOP_GSV_QUARTILE` 序列与 `benchmarkPosition` | 雷达图只渲染 2 条线，图例同步只有 2 项（非「有图例项但无线」） |
| 题库为空（某维度 0 题） | 该维度 `score = null` | 维度行显示 `—`，综合分按有题维度平均并提示口径 |
| 某维度只有 `YES_NO` 题（无计分题） | 该维度 `score = null`、`scoredCount = 0` | 维度行分数显示 `—` 并标注 `No scored questions`；该维度不进综合分分母；雷达图该轴不绘点 |
| **无差距分析记录** | 接口 17 返回 `summary = null`、`dimensions = []` | 沿用原型空态文案：**`No gap analysis yet`** + **`Goldie needs scored questions with evidence notes for this dimension before it can suggest gaps and recommended actions.`**；管理端多一个 Generate 按钮 |
| **分析已过期（`stale = true`）或正在生成** | 返回旧内容 + `stale/generating = true` | 卡片顶部条 `Refreshing analysis…`，**继续展示旧内容不清空** |
| **LLM 生成失败 / 超时** | 异步任务重试 2 次后放弃，**不写库、不覆盖已有分析**，保留 `stale = true`；手动接口 18 抛 `ServiceException` | 手动触发时提示 `Gap analysis failed. Please try again.`；自动失败静默保留旧内容 + `Refreshing` 条消失 |
| **LLM 返回结构不合法** | Java 侧校验维度枚举与 `severity` 值域；非法 `severity` 降级 `MEDIUM`；缺失维度该维 items 为空；缺失某个 audience 则该 audience 不覆盖旧数据 | 缺失维度的区块显示空态，其余正常渲染 |
| **无备注可依据** | 该条 item 带 `evidenceMissing = true` | 条目下方灰字 `No notes provided`（PRD §5「如无笔记，标注为未提供备注」） |
| **附件入知识库失败** | `ingest_status = FAILED`，**不阻断评估提交** | 附件 chip 显示告警图标 + `Retry` |
| **附件上传中提交** | 服务端只认已落 `erl_answer_attachment` 的附件 | 提交前 flush 上传队列；仍在传的文件弹提示「N files still uploading」 |
| F2 某公司无评估 | 该行 `overallScore = null`，`detailUrl` 仍下发 | 各分数列显示 `—`，Stage 留空，`View` 仍可点（进该公司维度详情页看空态，**v3.2 改**：不再跳 Company Overview） |
| 草稿保存失败（网络） | — | 吸底条红色提示 `Draft not saved — retrying`，本地保留未保存变更并自动重试；离开前二次确认 |
| **在填期间题库发布了新版（v3.4）** | **不是降级场景，是正常路径**：评估恒按 `question_version_id` 渲染，服务端行为与没发布过完全一致 | 填报页**无任何提示、无任何变化**；仅页头次级文字 `Question set v{n}` 可看出用的是哪版 |
| **提交时绑定版本已不是最新（v3.4）** | **不校验、不拦截**（v3.3 的前置校验 0 已删除），正常提交 | 无提示；历史列表该行标 `Question set v{n}`，与新版本提交的行分母不同属正常（§7.10-N2） |
| **配置页有草稿但未发布（v3.3）** | 填报页 / 维度页 / 计分**读不到任何草稿变更**，行为与没改过完全一致 | 无任何感知（这是版本化的目的）；仅配置页显示 `Draft v{n} — unpublished changes` |
| **某维度在已发布版本中 0 题（v3.3）** | 同「题库为空」：该维度 `score = null`，`totalCount` 不含未发布内容 | 填报页该维度分组显示空态 `No questions published for this dimension yet.`；维度详情页维度分显示 `—`；配置页则正常列出草稿内容 + `Publish` 提示 |
| **提交时题序已变更** | 不阻断（V1 计分与顺序无关） | 无提示；`YES_NO_SEQUENTIAL` 模式启用后需重新评估此场景（§13-Q5） |
| 重复提交（该记录已 SUBMITTED） | `BadRequestException` | 提示已提交并跳转到该次提交的只读详情 |
| 跨端越权访问 | `BadRequestException` | 统一错误提示，路由守卫先行拦截 |

---

## 10. 改动文件清单

### 10.1 CIOaas-api（新增业务域 `erl/`）

```
gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/erl/
├── interfaces/controller/     ErlCardController / ErlDimensionController
│                              ErlAssessmentController / ErlQuestionController
│                              ErlBenchmarkController / ErlGapAnalysisController
│                              ErlPortfolioController
├── interfaces/vo/request/     ErlCardQueryRequest / ErlDimensionQueryRequest
│                              ErlAssessmentQueryRequest / ErlAssessmentSaveRequest
│                              ErlAssessmentSubmitRequest / ErlQuestionCreateRequest
│                              ErlQuestionUpdateRequest / ErlQuestionReorderRequest
│                              （Publish 无入参，接口 21 不需要 Request VO）
│                              ErlQuestionVersionResponse / ErlQuestionChangeSummaryResponse（v3.3）
│                              ErlBenchmarkCreateRequest / ErlGapAnalysisGenerateRequest
│                              ErlPortfolioQueryRequest
├── interfaces/vo/response/    ErlCardResponse / ErlDimensionDetailResponse
│                              ErlAssessmentResponse / ErlAssessmentSubmitResponse
│                              ErlAssessmentHistoryResponse / ErlQuestionResponse
│                              ErlBenchmarkResponse / ErlGapAnalysisResponse
│                              ErlPortfolioResponse
├── interfaces/converter/      ErlConverter（MapStruct，Request/Response ↔ DTO）
├── application/service/       ErlCardService(+Impl) / ErlDimensionService(+Impl)
│                              ErlAssessmentService(+Impl)      ← 含提交事务 + 置脏 + afterCommit 投递
│                              ErlQuestionService(+Impl)        ← 含 reorder 事务
│                              ErlQuestionVersionService(+Impl) ← v3.3：ensureDraftVersion 写时复制 /
│                                                                 publish 事务 / 版本 diff（changeSummary）
│                              ErlBenchmarkService(+Impl)
│                              ErlGapAnalysisService(+Impl)     ← 含自动重生成、重试、Redis 去重锁
│                              ErlPortfolioService(+Impl)
│                              ErlAttachmentService(+Impl)      ← 附件登记 + 入库回写
├── application/scoring/       ErlScoringStrategy（接口，§7.2）
│                              Score1To9Strategy（MVP 唯一实现）
│                              ErlScoringStrategyFactory
├── application/dto/erl/       ErlDimensionScoreDTO / ErlAssessmentDTO / ErlAnswerDTO
│                              ErlAttachmentDTO / ErlQuestionDTO
│                              ErlBenchmarkDTO / ErlBenchmarkDimensionDTO
│                              ErlGapAnalysisDTO / ErlGapItemDTO / ErlRadarSeriesDTO
├── application/mapper/        ErlMapper（MapStruct，DTO ↔ Entity）
├── domain/entity/             ErlQuestionVersion（v3.3） / ErlQuestion / ErlAssessment / ErlAssessmentDimension
│                              ErlAssessmentAnswer / ErlAnswerAttachment
│                              ErlBenchmarkRecord / ErlBenchmarkDimension
│                              ErlGapAnalysis / ErlGapAnalysisItem
├── domain/enums/              ErlDimensionEnum / ErlEraEnum / ErlPortalEnum
│                              ErlAssessmentStatusEnum / ErlAnswerTypeEnum
│                              ErlScoringModeEnum / ErlGapItemTypeEnum / ErlSeverityEnum
│                              ErlDimensionStatusEnum / ErlAudienceEnum / ErlIngestStatusEnum
│                              ErlQuestionVersionStatusEnum / ErlQuestionChangeTypeEnum（v3.3）
├── domain/repository/         ErlQuestionVersionRepository（v3.3） / ErlQuestionRepository / ErlAssessmentRepository
│                              ErlAssessmentDimensionRepository / ErlAssessmentAnswerRepository
│                              ErlAnswerAttachmentRepository / ErlBenchmarkRecordRepository
│                              ErlBenchmarkDimensionRepository
│                              ErlGapAnalysisRepository / ErlGapAnalysisItemRepository
└── infrastructure/client/     ErlPythonClient   ← 经网关调 Python 生成接口与附件入库接口
```

另需 `deploy/upgrade_doc/sprint{N}/erl_init.sql`：**10 张表**（v3.3 增 `erl_question_version`）的索引与唯一约束（含**三个部分唯一索引**：§5.2 两个 + §5.1.1 的单草稿版本约束）、CHECK 约束（§5.4）、题库种子数据（见 §13-Q4，**种子须先建 `version_no = 1` 且 `status = 'PUBLISHED'` 的版本行**，题目行挂其 `version_id`，否则系统起来后无已发布版本、填报页全空）、系统配置项 `erl.enabled` 初始值。

> **题库查询的统一入口（v3.3 改）**：`ErlQuestionRepository` 的**每个查询方法都必须带 `versionId` 入参**，禁止「查全部题」的无版本方法。上层只有两个取版本的入口 —— `ErlQuestionVersionService.currentPublished()`（填报 / 展示 / 计分 / 组合层 / Goldie）与 `ensureDraftVersion()`（仅 C 模块写接口）、`currentDraftOrPublished()`（仅 C 模块读接口）。**漏带版本 = 草稿题泄进问卷**，是本模块最容易出的错，代码审查须专项检查这一条。

> 分数聚合、状态摘要、Data Sources 归并、洞察合成属跨表编排，写在 `application/service`；`domain/repository` 只做单表访问（`standards/architecture.md` §1.2 / §1.3）。计分逻辑一律经 `application/scoring/` 的策略接口，不内联。

### 10.2 CIOaas-python（生成 + 附件编排，不落 ERL 业务表）

```
新增  source/erl/interfaces/router.py                    POST /api/ai/erl/gap-analysis
                                                          POST /api/ai/erl/attachments/ingest
新增  source/erl/interfaces/vo/{request,response}.py
新增  source/erl/application/service/erl_gap_analysis_service.py
新增  source/erl/application/service/erl_attachment_service.py   ← 复用 rag ingest_service 与 file_registry
新增  source/ai/prompts/erl_gap_analysis_founder.md      带 # version: 1.0
新增  source/ai/prompts/erl_gap_analysis_gsv.md          带 # version: 1.0
修改  source/main.py                                     注册 router
新增  tests/erl/test_erl_gap_analysis_service.py         prompt 回归测试（固定输入 → 验证输出结构 / severity 值域 / 双 audience）
新增  tests/erl/test_erl_attachment_service.py           入库链路顺序（ingest → register → vectorize）
```

Python 侧**无 domain 层、无 ERL repository** —— 不落 ERL 业务表；附件编排复用 rag / file_registry 的既有服务。

### 10.3 CIOaas-web

```
新增  src/pages/exitReadiness/**                      （§8.2 全部）
修改  src/pages/companyOverview/home/CompanyOverviewPage.tsx
                                                       DI 区块渲染条件改为 DiStatus && !erlEnabled；
                                                       同位置渲染 ErlCard（§8.6）
新增  src/pages/companyOverview/home/components/ErlCard/**
新增  src/pages/portfolioCompanies/erl/**             F2 Tab 内容组件 + 取数 hook
修改  src/pages/portfolioCompanies/home/PortfolioCompaniesPage.tsx
                                                       新增 TabPane key='6'；trackPortfolioButtonClick 补 'ERL' 分支
修改  src/pages/companySettings/components/modules/ModulesTab.tsx
                                                       DI 开关旁加「ERL 已接管 Company Overview 展示」说明（§8.6-4）
新增  src/services/api/exitReadiness/**
新增  src/services/service/exitReadiness/erlService.ts
修改  config/routes.ts                                 （§8.1 九条路由 + Configuration 顶部下拉入口）
修改  src/locales/en-US/**                             （ERL 文案）
修改  CIOaas-web/standards/architecture.md §2          （登记新 API 域 exitReadiness/，见 §13-Q7）
```

### 10.4 台账

- `CIOaas-api/docs/待优化项.md` 已于 2026-08-26 记入 `fi/` 分层与 `QuickbooksController` 存量违规一条。
- 本次新增待优化项（实现阶段登记）：
  - Company Overview 的 DI 开关语义与 ERL 接管后的冲突（§8.6-4），属存量配置模型问题。
  - `CompanyOverviewPage.tsx` 已超 1600 行且 DI/FI 分支混杂，ERL Card 接入后建议拆分。

---

## 11. 验证清单（实现后逐项过）

**入口与卡片（PRD §3.1）**
1. Company Overview 页**不再出现** DI 卡片，同位置出现 ERL Card；DI 的 SDP / KPA 数据接口仍可正常返回（数据未删）。
2. ERL Card 完整包含：综合分 `X/9`、当前 Stage、Gap Analysis 摘要、5 维列表（分数 + Perception Gap + 状态徽章）、BPMM 参考数字、雷达图。
3. **全站不存在独立的 Exit Readiness 落地页路由**；`/exitReadiness` 直接访问返回 404 或重定向到 Company Overview。
4. 卡片上每个维度的 `View Details` 正确跳到对应维度页；维度页面包屑为 `Exit Readiness ›〔Dimension Name〕`，返回落回 Company Overview。

**维度页与模板（PRD §3.2）**
5. 五个维度页 `/exitReadiness/dimension/{FRL|PRL|BERL|RRL|TRL}` 均由**同一组件**渲染，文案随参数变化，无硬编码分支；非法 `dimension` → 404，不崩溃。
6. **公司端进入维度页看不到 GSV Tab**；直接构造 `?portal=gsv` 请求后端返回 400。
7. **公司端在维度页与雷达图中都看不到 Benchmarkit / Top GSV Quartile**；抓包确认服务端未下发这两个值（非前端隐藏）。
8. 维度页 `View history` 进入历史列表且**已按当前维度过滤**；`+ New` 正确进入对应端问卷。
9. 维度页展示 Data Sources & Cadence 卡（primary / supplementary 标签 + `Quarterly`）。

**计分（PRD §5）**
10. Founder 提交 7.8 / GSV 手动填 6.4 时，卡片该维度显示 Founder `7.8`、GSV `6.4`、`Perception Gap: Positive 1.4`。
11. 五维 GSV 分 6.4 / 5.1 / 7.5 / 4.6 / 2.8 → 综合分显示 `5.3`。
12. **Era 边界**：3.9 → `Founder Era`、4.0 → `Harvest & Growth`、6.9 → `Harvest & Growth`、7.0 → `Exit Era`；**6.4 必须显示 `Harvest & Growth`**（原型的 Exit Era 是 bug，不得复现）。
13. **`YES_NO` 不计分**：某维 10 题中 3 题 `YES_NO`、7 题 `SCORE` 且分数全为 6 → 维度分 `6.0`；页头显示 `10 questions`，分数 tooltip 说明按 7 题平均。
14. **完成度含 `YES_NO`**：上述维度只答完 7 道 `SCORE` 题时进度 `7 / 10`，提交按钮禁用；补答 3 道 Yes/No 后才可提交。
15. 某维度全为 `YES_NO` 题时维度分显示 `—`，且**不进综合分分母**。
16. **计分策略隔离**：全仓检索确认维度分计算只出现在 `application/scoring/`，各 service 无内联平均逻辑（为 §7.2 的模式切换留路）。

**填报（PRD §3.3 / §3.4）**
17. 自评页答 3 题（含 1 条备注 + 1 个附件）后关闭浏览器，重进同期次同端，答案、备注、附件完整回填。
18. 附件上传后可在**公司 Knowledge Base / Memory File 面板中检索到**（验证走的是 ingest + 向量化链路，而非只登记）。
19. **提交后只读**：已提交记录的问卷页无输入控件；直接调 draft/submit 接口返回 400。
20. **同季多次提交**：同一 `period` + 同一端连续提交两次 → B3 出现**两条独立记录**，第二条带 `Current` 徽章，第一条不带；展示页与 F2 取第二条。
21. **GSV 手动维度分**：五维任一未填则提交被拒；填 8.0 而题目推导为 5.0（差 3.0 > 1.0）→ 弹软确认弹窗，**确认后提交成功**（不阻断），`divergence_ack` 落库为 true。
22. 提交确认弹窗明确告知「锁定只读 / 修改需新建提交 / 下一步对方独立评估」。

**配置（PRD §3.8）**
23. Era band 内拖拽重排后**先不生效**（填报页与维度页题序不变），**点 Publish 后**两处才按新 `sort_order` 呈现；首次拖拽出现影响提示（含「takes effect when you publish」）。
24. 题库删除某题**并发布**后，历史评估详情页仍能展示该题题干与当时得分与备注（由 `question_version_id` 版本快照保证，非软删）。

**差距分析（PRD §3.6）**
25. **提交任一端评估后无需手动操作**，稍后进入卡片可看到刷新后的分析；刷新期间显示 `Refreshing…` 且旧内容不被清空。
26. **同一份数据下，公司端与管理端看到的建议文案口吻不同**（Founder「你可以…」/ GSV「我们建议这家公司…」），且互相取不到对方的 audience。
27. 建议条目包含「为何相关」说明，且能引用到该公司具体证据/备注（非通用建议）。
28. **无备注**的题推导出的条目标注 `No notes provided`。
29. 双方分数均高且无实质差距的维度，文案承认为优势，**不出现强行套用的差距叙述**。
30. **Python 生成接口断连时**：自动重试后仍失败 → 库中原有分析不被清空、页面仍显示旧分析；管理端手动 Generate 返回错误提示。
31. LLM 返回非法 `severity`（如 `critical`）时降级为 `MEDIUM` 且不报错。

**组合层（PRD §3.7）**
32. F2 ERL Tab 位于 Company List 第 6 个 Tab，只列当前用户有权访问的公司；无评估的公司各分数列显示 `—`。
    - **`View` 跳该公司的维度详情页（Score Details）**（v3.2 改）：落在 `FRL` 且带该行期次；**不再跳 Company Overview**；无评估的公司点 `View` 进入后为空态而非报错。
33. **按 ERL Score、Stage、任一维度分排序与筛选均生效**，且为服务端排序（翻页后顺序稳定）。
34. F2 在 20 家以上公司时只发 1 次请求、后端无 N+1 查询（开 SQL 日志核对）。

**基准（PRD §4 / §0.3）**
35. D1 两张卡齐全：`Latest by Dimension · {period}` 五行逐维列出两个基准分（`x.x/9`），`Record History` 七列且按期次倒序、最新一条带 `LATEST` 徽章。
36. D2 是**独立页面**（地址栏变为 `/exitReadiness/benchmark/add`、浏览器可后退），不是 Modal；`< Back` 与 `Cancel` 均回 D1 且不留脏数据。
37. D2 十个分数框任一为空或超出 1–9 → 保存被拒并定位首个非法输入；录入已存在的期次 → `Period` 下报错且已填分数不丢失。
38. 保存成功后 D1 立即出现该期次记录，`Latest by Dimension` 切到新期次；点 `Details` 展开五维明细**不产生新的网络请求**。
39. 管理端雷达图的 `BENCHMARKIT` / `TOP_GSV_QUARTILE` 两条线**逐维取值不同**（非五顶点同值），且与该期适用记录（§7.8）的五维分逐一吻合。

**通用**
40. 公司端调卡片接口并伪造他人 `companyId` → 服务端仍返回本公司数据。
41. 公司端访问 `/exitReadiness/configuration`、`/exitReadiness/benchmark`、`/exitReadiness/benchmark/add`、`?portal=gsv` 均被拦截；直接调后端写接口返回 400。
42. 无 GSV 提交时卡片按 §9 降级，不出现 `NaN` / `null` 字样。
43. 雷达图：**无填充、每线异色、有图例、中心轴隐藏、悬停显示精确分**；公司端只有 2 条线且图例同步只有 2 项。
44. 移动端（≤768px）各页可用，表格横向滚动、页面不整体横向滚动。
45. `npm run tsc` 与 `npm run lint:fix` 无新增错误；`mvn -pl gstdev-cioaas-web test` 通过；`uv run pytest tests/erl/` 通过。

**题库版本化与发布（PRD §3.8 + 2026-08-28 裁决，v3.3 重写）**
46. **四类变更均不立即生效**：分别做一次新增、改题干、删除、拖拽重排后**不点 Publish** —— 填报页与维度详情页的题目、题序、题数、完成度分母**全部保持原样**；配置页则显示 `Draft v{n} — unpublished changes` 与对应徽章（`New` / `Edited` / `Moved`）。
47. **第一次写触发写时复制**：库中出现一条 `status='DRAFT'` 的新版本行，`based_on_version_id` 指向原已发布版本，且**已发布版本的题目行一字未改**（对比发布前后的 `erl_question` 快照）。
48. **草稿全局单份**：连续做 5 次变更只产生**一条** DRAFT 版本行（不是 5 条）；两个管理员分别改不同维度后，任一人点 Publish，**两人的改动一起生效**，确认框中列出的是全量摘要。
49. 点 `Publish` 后：填报页与维度页立即按新版本渲染；配置页版本条变为 `Published v{n+1}`，按钮禁用 + tooltip `No unpublished changes.`；库中无 `DRAFT` 版本；`change_summary` 快照与发布前确认框显示的计数一致。
50. **按钮激活条件是「有草稿版本」而非「有新题」**：只在 PRL **改一道题干**（不新增），切到 FRL Tab 时 `Publish` 仍激活。
51. **版本锁定（v3.4 核心）**：Founder 答了 20 题后管理员发布一版（新增 2 题 / 改 1 题题干 / 删 1 道**已答**题）→ 重新打开问卷：**题目数、题序、题干、已答内容、完成度分母逐项不变**，被删的题还在、被改的题仍是旧题干、新增的 2 题不出现；页头仍显示 `Question set v{n}`（旧版本号）。
52. **旧版本草稿可正常提交**：承接上一项，该草稿在题库已发布 v{n+1} 的情况下**提交成功**（无 400、无版本校验），历史列表该行标 `v{n}`。
53. **两端跨版本**：Founder 用 v3 提交后发布 v4，GSV 用 v4 填并提交 → 两条记录的 `Completion` 分母不同且各自标注版本号；Scorecard 的 Perception Gap 正常计算并在旁并列显示 `v3 / v4`，**不告警、不阻止**。
54. **发布不触发 Goldie**：发布新题库版本后，已有的差距分析记录 `stale` **保持 false**、内容不变、无 LLM 调用（查日志确认）。
55. **已提交记录不受影响**：任何发布之后，已 `SUBMITTED` 的历史详情页题干、题序、题数、分数**逐项不变**（按其 `question_version_id` 渲染）。
56. **版本入口唯一**：全仓检索确认 `ErlQuestionRepository` 无「不带 `versionId`」的查询方法；且「取最新已发布版本」**只出现在创建评估记录这一处**（§7.9-①），填报 / 展示 / 计分 / 组合层 / Goldie 的取数一律来自 `erl_assessment.question_version_id`。

---

## 12. V1 明确不做（YAGNI / 风险控制）

- **不建独立 Exit Readiness 落地页 / Dashboard 路由**（PRD §3.1）。
- 不做全维 Score Details 页（原型 `/readiness/overall`，PRD 无依据）。
- 不做完整 BPMM 评估交互，只显示参考数字（PRD §5）。
- 不做 Ask Goldie 对话接入、Finance 页 ERL 卡片与回跳。
- 不做 Goldie 建议的跟踪 / 指派 / Deadline（PRD §3.6「MVP 不含」）。
- 不做 Goldie 生成结果的人工编辑 / 审核流（§13-Q9）。
- 不做差距分析的版本历史，只保留「最新一份 + 自动刷新 + 手动 Regenerate」。
- **不实现 `YES_NO_SEQUENTIAL` 计分模式**，只留策略接口占位（§7.2）。
- 不做题库的公司级覆盖（题库全局单份）。**题库版本化已按 2026-08-28 裁决纳入 V1**（§7.9）。
- **不做撤回（已发布 → 草稿）、单维度发布、变更逐条勾选发布、定时发布、版本回滚与版本对比 UI** —— 依 2026-08-28 裁决，V1 只实现「改草稿 → 全量发布」一条路径（§7.9）。
- **不做草稿的丢弃（Discard changes）** —— 裁决未要求；代价是误改只能手工改回来（题库低频、变更摘要可见，可接受）。若实际使用中成为痛点，加一个 `DELETE /erl/question/draft` 即可，不影响现有模型。
- **不做草稿的编辑锁 / 按人隔离的草稿 / 变更冲突合并** —— 题库配置是低频管理动作，多人协作靠界面提示（§7.9-④），不上并发控制。
- **不做在填评估的重基 / 「升级到最新题集」按钮**（v3.4 依裁决删除）—— 评估版本锁定，一次评估自始至终用同一版题集（§7.9-⑤）。
- **不做题集版本不一致的告警 / 阻断** —— 同期次两端跨版本、旧版本草稿延迟提交均**允许**，只在界面标注版本号（§7.10-13 / N1 / N2）。
- 不做评估期次之间的对比、趋势图、导出。
- 不做题库批量导入导出。
- 不做 `SUBMITTED` 回退为 `DRAFT` 的重开流程 —— PRD 的口径是新建提交，不是重开。
- 不冗余存储展示用聚合分数（维度分 / 综合分 / Stage / Era / 状态摘要全部实时算；`derived_score` 只作审计快照，§5.3）。
- 不新增 dva model（`src/models/` 已冻结）。
- 不引入 SQS：Java 与 Python 走同步 HTTP 经网关。
- 不接 Fireflies / SharePoint 作为 Goldie 数据源（PRD §3.6 明确为后续）。

**识别到但本次不处理**：

- `fi/` 业务域仍是扁平结构、`QuickbooksController` 在 Controller 内 try-catch 并直接收发 Entity，均不符合 `standards/`，属存量技术债 —— 已记入 `CIOaas-api/docs/待优化项.md`（2026-08-26 条目）。
- `CompanyOverviewPage.tsx` 单文件超 1600 行、DI / FI 分支混杂（§10.4）。
- 题量较大的问卷页单页渲染；题量再翻倍需考虑虚拟滚动。

---

## 13. 待确认事项（开发前必须对齐）

> 编号已与 **PRD §五「明确的 TBD 事项」** 对齐；PRD 未列但本设计发现的新问题标注为「设计新增」。

| # | 对应 PRD TBD | 问题 | 影响 | 建议 |
|---|---|------|------|------|
| **Q1** | §五-1 | **ERL 卡片上 Gap Analysis 的呈现方案**（摘要几行？点开何处？）与 **BPMM 的内容 / 规则 / 数据来源**（1–5 的分值从哪来？现有系统有无该数据？） | 卡片布局与 `bpmmScore` 的取数实现；BPMM 无数据源则该字段无法落地 | Gap 摘要建议取 summary 前 2 行 + `View details`；**BPMM 数据源必须先给** —— 在此之前 `bpmmScore` 恒 `null` 且隐藏该行，其余照常开发 |
| **Q2** | 设计新增 | **DI 卡片「系统级隐藏」与现有公司级 `diStatus` 开关的差异**（§8.6）：是否需要保留按公司回退到 DI 的能力？ERL 是全量上线还是灰度？ | 决定新增 `erl.enabled` 是全局单值还是公司级；影响 Company Settings 模块页的语义 | 建议**全局单值**（PRD 说「系统级」），不做公司灰度；若需灰度则改为公司级配置并明确与 `diStatus` 的优先级 |
| **Q3** | §五-2 / §五-3 | **计分口径三连**：① 每维度分数的具体计算方法（是否即题均分）；② Stage 由综合分推导的**取整规则**（round / floor / 查表）；③ 状态摘要的**枚举取值与阈值**（**v3.2**：PRD 2026-08-28 已删去 `Met/Partial/Gap` 三值，现三值与阈值**均为设计占位**，产品可整体替换），以及 GSV 软确认的**分歧阈值**（占位 1.0） | 分数、Stage 徽章、状态徽章、软确认弹窗触发条件全部依赖 | 现按 §7.1 / §7.3 / §7.4 的占位实现（题均分 / `clamp(round(score),1,9)` / 三值 `MET`/`PARTIAL`/`GAP` + 阈值 0.5 与 1.5 / 分歧阈值 1.0），**全部集中在 `application/scoring/` 与 `ErlDimensionStatusEnum`，改口径只改一处** |
| **Q3b** | 设计新增 | **口径不对称**：GSV 维度分取手动填写、Founder 维度分取题目推导，Perception Gap 因此混合两种口径（§7.1） | Perception Gap 的可解释性 | 建议产品确认；若要对称，二选一：Founder 端也填手动整体分，或 GSV 手动分退化为纯审核动作、展示仍用推导分 |
| **Q4** | 设计新增 | **题库初始内容从哪里来**？PRD §3.3 说「30+ 题目」、§3.9 示例 `45/45`、原型是 165 题，三者不一致。正式题库清单是否已有？ | 决定 `erl_init.sql` 种子数据；影响 UAT 可用性 | 代码不写死题量（已按题库配置驱动）；**种子数据需产品提供正式题库清单**，否则先导入原型题库供联调 |
| **Q5** | §五-2 / §五-8 | **打分格式切换的后续细节**：切到 Yes/No + 固定顺序后，① 「No 中断」时该维度分数如何计算（剩余题按 0 分？不计入？维度分封顶？）；② 题序变更对**进行中**与**历史**评估的解释策略 | V1 不实现，但会决定 `ErlScoringStrategy` 接口是否够用 | V1 只留接口占位（§7.2）；两问在切换那个 story 前必须给出，届时复核接口形状 |
| **Q6** | §五-5 / §五-6 | ① 是否以「**GSV vs. Founder 分数对比 Tab**」作为完整 AI 建议上线前的 MVP 替代方案？② 「Gap」的粒度是**按题 / 按维度 / 综合分差值**？ | ① 决定是否要在维度页多加一个 Tab；② 决定 Goldie 输入组织方式与 gaps 条目粒度 | ① 本设计**未包含**该 Tab（E1/E2 已完整实现，替代方案无必要）；② 本设计按**按维度**产出 gaps，逐题证据作为输入上下文 —— 需 Li 团队确认 |
| **Q7** | §五-7 | **可见角色子集**：① ERL 卡片及后续页面是否对「当前可访问 Company Overview 的全部角色」开放，还是需收窄？② ERL Configuration 的 admin 是哪一级（平台 admin / portfolio admin）？③ 前端新增 API 域 `exitReadiness/` 需登记进 `CIOaas-web/standards/architecture.md` §2（该规范写明「禁止自创目录名」） | 权限矩阵（§4.2）与规范符合性 | ①② 本设计按 §4.1 的 `roleType` 二分实现，Configuration 归管理端；如需更细粒度需给出角色清单。③ 随本功能一并更新规范文件 |
| **Q8** | 设计新增 | **PRD 内部两处需产品裁决**：① §3.2「创始人不显示 GSV 专属字段」 vs §5「创始人并列查看自己的分数与 GSV 分数」——本设计的裁决见 §4.2 注；② PRD §5「Scorecard」的展示项在 ERL Card 与维度页之间的归属——本设计的划分见 §8.5 | 影响公司端可见范围与两个页面的信息密度 | 请产品对 §4.2 注与 §8.5 的表格直接勾选确认 |
| **Q9** | 设计新增 | LLM 生成的 strengths / gaps / actions 是否需要 GSV **人工编辑或审核**后才对公司端可见？ | 影响是否需要 `status` 字段与编辑页；也影响「提交后自动刷新」是否会把未审核内容直接推给创始人 | V1 建议**不做**（生成即可见），本文档按此设计。若要审核，`erl_gap_analysis` 需加 `review_status` 且自动刷新只更新 GSV audience |
| **Q10** | 设计新增 | ERL 附件写入公司 Memory File 后，**是否与 chatbot 知识库共用同一空间**？公司端上传的 ERL 证据是否应对管理端可见、反之如何？ | 决定 `ensure_kb_space` 的空间组合键（现有链路：APP 按公司 / ADMIN 按组织） | 建议沿用现有端类型规则（公司端上传 → 公司空间；管理端上传 → 组织空间），与 chatbot 一致，不为 ERL 单开空间 |
| ~~**Q11**~~ | §3.8（2026-08-28 新增 Publish） | ✅ **已裁决（2026-08-28）**：**所有变更都经发布 + 题库版本化**；**不需要**撤回与单维度发布。设计已按此重写（§0.5 / §5.1.1 / §7.9） | — | **待回写 PRD**：§3.8「变更**立即生效**到评估表与 Score Details 的题目列表中，无需其他配置步骤」一句**与裁决冲突，需删除**，并补上：「配置页的新增 / 编辑 / 删除 / 重排均落草稿，点 Publish 后统一生效；正在填写的评估保留已答内容」。**遗留（无需答复、开发时按设计执行）**：多管理员共享同一份草稿、任一人发布会连带发布他人改动（§7.9-④）；V1 不提供丢弃草稿（§12） |
| ~~**Q13 ~ Q16**~~ | 设计新增（v3.3 边界 §7.10） | ✅ **已随「版本锁定」裁决一并关闭（2026-08-28）**：Q13（题干被编辑后旧答案是否有效）与 Q14（删题时已答内容如何处置）**问题本身消失** —— 评估锁定在自己的题库版本上，看不到新题面；Q15（发布是否触发 Goldie 重生成）**结论为不触发** —— 分析输入锚在版本快照上、发布后一字未变；Q16（同期次两端可否不同版本）**结论为允许** —— 裁决原文即取值，页面标注两端版本号。详见 §0.6 / §7.9-⑤ / §7.10 | — | 无需答复。**版本锁定衍生的 N1 ~ N3 三条边界**（旧草稿无限期有效、同期次多次提交跨版本、不做题集升级按钮）已在 §7.10 定档，开发时按设计执行 |
| **Q12** | §3.7（2026-08-28 改口） | **F2 `View` 的落地页**：PRD 改为「跳转到该公司的 Score Details 页面」，而 Score Details = 维度详情页（按维度）。从组合层一行（五维齐全）点进去应落在**哪个维度**？ | 决定 `detailUrl` 的默认维度；也决定是否需要一个全维汇总页（§0.2-17 已删的 A4） | 本设计默认落 **FRL** 并提供页头五维 chip 横切（§8.4）；若产品期望的是「一页看全五维」，则需复活 A4 全维 Score Details 页 —— **该页 PRD 至今无定义，需先给内容清单** |

---

## 附录 A：与 v2.1 的差异速查（供已读过 v2.1 的同学）

| v2.1 章节 | 变化 |
|-----------|------|
| §1.1 范围表 | A1 由「独立 Dashboard」改为「Company Overview 卡片」；删除 A4；新增 A7（DI 下线）、C4（拖拽）、D 归入管理端；E1 由「规则合成三条洞察」改为「LLM 生成建议 + 双 audience」 |
| §2 现状事实 | 新增 §2.1「存量代码事实」（7 条，均带文件行号）；原型事实降级为参考并逐条标注是否被 PRD 采纳 |
| §3.2 决策表 | 新增 6 条决策（卡片入口、DI 开关、自动刷新、多次提交、手动维度分、附件链路）；修正 1 条（差距分析生成时机） |
| §4.2 权限表 | 新增 GSV Tab、基准两条线、D 模块的公司端拒绝；新增 PRD 内部张力的裁决说明 |
| §5 数据模型 | 表由 6 张增至 8 张（新增 `erl_assessment_dimension`、`erl_answer_attachment`；**v3.1 再增 `erl_benchmark_dimension`，共 9 张；v3.3 再增 `erl_question_version`，共 10 张**）；`erl_assessment` 去唯一约束加 `submission_seq`/`is_latest`/`scoring_mode`；`erl_assessment_answer` 加 `note`；`erl_gap_analysis` 加 `audience`/`stale`/`source_*`；`erl_gap_analysis_item` 加 `ACTION` 类型与 `evidence_missing` |
| §6 接口契约 | 接口由 18 个增至 20 个；`/erl/overview` → `/erl/card`；删 `/erl/scoreDetails`；新增 `/erl/question/reorder`、`/erl/assessment/{id}`、附件删除；F2 加排序筛选参数；Python 接口加 note/criteria 输入与双 audience 输出，新增附件入库接口 |
| §7 计算口径 | 维度分拆为 Founder（推导）/ GSV（手动）；新增 §7.2 计分策略、§7.4 状态摘要与软确认阈值、§7.6 Data Sources 推导；§7.5 生成时机由手动改为自动 |
| §7.3「三条洞察卡规则」 | **整节删除** —— 那是原型 mock 的反解规则，PRD 未要求；改由 LLM 产出 `actions[]`（含「为何相关」） |
| §8 前端 | 删除 Dashboard 与 scoreDetails 路由；新增 §8.5 职责划分、§8.6 DI 下线方案；F2 组件位置更正为 `portfolioCompanies/erl/`；交互表补 14 项 PRD 要求 |
| §9 降级 | 由 13 条增至 21 条 |
| §11 验证清单 | 由 20 项增至 40 项，按 PRD 章节分组 |
| §13 待确认 | 重编号并与 PRD §五 的 8 项对齐；关闭 v2.1 的 Q8（已确认）、Q1（PRD 已定义 A3）、Q9（已统一口径）；新增 Q2 / Q3b / Q4 / Q8 / Q10 |

> **v3.1 的增量不在此表** —— 该版只动基准模块 D（§5.6 / §5.6.1 / §6.5 / §7.8 / §8.1 / §8.4 / §9 / §11），逐条见 §0.3。
>
> **v3.2 的增量亦不在此表** —— 该版按 2026-08-28 PRD 修订只动 4 处：题库 Publish 发布态、F2 `View` 目标改为 Score Details 页（§6.8 / §8.4 / §9 / §11-32 / §13-Q12）、状态摘要三值降级为设计占位（§0.2-12 / §7.4 / §8.5 / §13-Q3）、打分格式表述依据减弱（§7.2，不改设计），逐条见 §0.4。
>
> **v3.4 的增量亦不在此表** —— 本版按需求方第二次裁决（「保留旧答案，以正在编辑的版本为准」）把 v3.3 的**重基整体删除、改为版本锁定**：删 `erl_assessment_answer.question_key`（唯一约束改回 `question_id`）、删接口 3 的 `rebase` 出参与接口 5 的版本一致性校验、删 `ErlAssessmentRebaseService`；§7.9-① 的「一律读最新已发布版本」订正为「一律读评估绑定版本」；§13-Q13 ~ Q16 四条边界全部关闭。逐条见 §0.6。
>
> **v3.3 的增量亦不在此表** —— 该版按需求方对 §13-Q11 的裁决把题库改为**版本化**：表由 9 张增至 **10 张**（新增 `erl_question_version`，§5.1.1），`erl_question` 删 `publish_status` / `published_at` / `enabled` 三列、加 `version_id` / `question_key`，`erl_assessment` 加 `question_version_id`，`erl_assessment_answer` 加 `question_key`；C 模块写接口由 `id` 改按 `questionKey` 定位；新增在填评估的**重基**机制。逐条见 §0.5。
