# 负收入逻辑全系统一致性处理 PRD 审核报告（v3）

> 评审日期：2026-06-05（第二次调整版）
> 评审对象：`docs/评审/01-prd.md`（源自 `E:/LG_DOCS/LG/docs/负收入逻辑全系统一致性处理_需求文档.md`，v3，Sprint 111）
> 已加载项目上下文：CLAUDE.md（根 + CIOaas-api）、`~/.claude/standards/common.md`、project-conventions；代码核对：`ArrTierEnum.java`、`FinancialGrowthRateServiceImpl.java`、`MetricExtractor.java`、`ColleagueCompanyServiceImpl.java`；README 未找到

---

## 〇、v3 相对 v2 的变化（已逐行 diff + 代码复核确认）

| # | 变化 | 评估 |
|---|------|------|
| D1 | §一 删除"除 ARR 增长率外，本需求还应审计系统中所有…其他区域"段落 | ✅ **解决 v2 #5/T5**：审计范围声明悬空问题消除，审计正式 descope。范围与功能章节恢复一致 |
| D2 | §2.4 ARR 区间改为 `[$5M, $20M) → 含 $5M 不含 $20M` + `[$20M, +∞) → $20M及以上` | ✅ **解决 v1/v2 #1（P0）**：已与代码 `ArrTierEnum`（TIER_4=[5M,20M)、TIER_5=[20M,+∞)，L31 `>=20M→TIER_5`）及 `calculateArrRangeForPeerFilter`（L772 `>=B20000→5`）完全一致。$20M 边界 P0 关闭 |
| D3 | §2.5 仅 Forecast 数据质量条款末尾追加"，继续执行剔除"（Actual 条款未加） | ⚠️ **不对称且重复**：与下方通用条款"即使回退到全平台 active 公司，同样执行此剔除规则"语义重叠；只加 Forecast 一侧造成读者误解为 Actual 回退后不剔除。核心交互问题（剔除 vs <3 判定先后）仍未回答 — 见 #1 |
| D4 | §4 新增"该ARR的计算与当前FE中ARR的计算不同，不应相互影响" | ⚠️ **部分回应 v1 双口径**：明确 peer-filter ARR ≠ 前端展示 ARR，方向正确；但 "FE中ARR" 为实现侧含糊术语；§1/§2 的"ARR_t-1<0"判据用哪套 ARR 口径仍未说 — 见 #2、#3 |
| D5 | ⚠️ **回退**：§4 删除 v2 的 `ARR=MRR×12 + 三种 MRR（分母=可用月份数）` 定义块，仅在示例里加 `(MRR)` 标注 | ❌ **新增退步**：v2 该块与代码 `calculateGrowthRateArrByDateForPeerFilter`（L789 分母=`subList.size()`）一致，删除后 ARR 计算口径只剩单一示例支撑；Last Month 基准月被排除（L784 缺行→`0×12=0`→TIER_0，无回溯）、窗口全负的兜底（L771/777 null/负→0/TIER_0）再次无处定义 — 见 #4、#5、#6 |

**v3 净结论**：解决了 2 项 P0（$20M 边界 D2、审计范围悬空 D1），但 **删除 MRR 口径定义（D5）造成回退**，且 v1/v2 的引擎归属、负值策略冲突、剔除×fallback 交互、Forecast 路径缺口四项核心 P0 **全部仍未解决**。综合仍为 ❌ 阻塞。

---

## 一、评分仪表盘

| 维度 | 评分 | 说明 |
|------|------|------|
| 语义与表述 | 5/10 | $20M 边界已对齐（+1）；但 D5 删除 MRR 口径、"FE中ARR"含糊、ARR vs Gross Revenue 双口径仍混用 |
| 功能完整性 | 5/10 | 审计 descope 后范围闭合（+）；但 Forecast 路径负值排除、Last Month 基准月缺失、全负兜底仍缺 |
| 操作闭环 | 4/10 | 期次级剔除 × 公司级 Peer Fallback（<3）交互仍未定义；D3 只单侧加"继续执行剔除"反而加深歧义 |
| 数据一致性 | 6/10 | $20M 边界与 `ArrTierEnum`/`calculateArrRangeForPeerFilter` 已一致（P0 关闭，+3）；但 §1 未指明约束两套增长率引擎中的哪套 |
| 权限覆盖 | N/A | 纯计算逻辑变更，无角色/权限维度（不计入综合） |
| 业务规则 | 4/10 | 仍无集中 BR 编号；§1 负 ARR 公式与引擎①"负月预过滤+CAGR 桥接"互斥且 PRD 未提及 |
| 编号与可追溯性 | 2/10 | 全文仍无 SC/BR/AC 编号，无验收标准小节，无 §七 BR 集中定义 |
| **综合** | **❌ 阻塞** | $20M、审计范围 2 项 P0 已解；但引擎归属、负值策略冲突、剔除×fallback 交互、Forecast 缺口 4 项 P0 仍未解，须先确认 |

---

## 二、评审通过项

- ✅ 业务背景清晰：明确两类问题（个体公司指标 / 基准与同行计算），目标可理解。
- ✅ §1 ARR 增长率三分支表（>0 / =0或null / <0）逻辑自洽，含正反例。
- ✅ §3 收入基础回溯规则（24 个日历月、首个非负值）描述具体、可执行。
- ✅ §4 Target Company 排除示例（三个月 gross revenue 取均值）量化清晰，可直接转测试用例。
- ✅ §2 动态判定说明（按期间剔除而非永久踢出）消除了一处潜在歧义。
- ✅（v3 新解决）§2.4 ARR 分桶 `[$5M,$20M)` / `[$20M,+∞)` 与代码 `ArrTierEnum.fromArr`、`calculateArrRangeForPeerFilter` 完全一致，$20M 边界 P0 关闭。
- ✅（v3 新解决）§一删除审计悬空段落，审计正式 descope，范围与功能章节一致。
- ✅（v3 新增）§4 "该ARR的计算与当前FE中ARR的计算不同，不应相互影响"明确了 peer-filter ARR 与前端展示 ARR 互不影响（方向正确）。

---

## 三、问题与建议

| # | 问题分类 | 问题描述 | 严重程度 | 是否阻塞 | 修订类别 | 状态 |
|---|----------|----------|----------|----------|----------|------|
| 1 | 操作闭环 | §2 期次级剔除（t-1<0 逐期剔除同行）与 §2.5「有效同行 <3 → 回退全平台 + Peer Fallback」交互仍未定义：剔除发生在 <3 判定**之前还是之后**？剔除是**期次级**而 fallback 是**公司级整体**判定（代码 `buildBenchmarkPeerCompanyIds` L927 `matchedPeerIds.size()<3` 为公司级，无逐期次计数）；某期次剔除后 <3 是否触发该期次回退？回退到全平台再剔除后仍 <3 的终态？v3 D3 仅在 Forecast 末尾加"继续执行剔除"，未回答顺序与终态 | P0 | 阻塞 | 需用户决策 | **v1/v2 遗留，未解决** |
| 2 | 业务规则 | 系统存在**两套增长率引擎**，§1 仍未指明约束哪套：① `FinancialGrowthRateServiceImpl.calculateGrowthRate`（L163-205，基于 **Gross Revenue**，当期 GR<0→null，prev=0→0，跨月 CAGR 桥接）；② benchmark `ARR_GROWTH_RATE`（`MetricExtractor` L176-186，基于 `normalization.arr`，prev null/0→0，**无负值分支**）。§4 D4 新增"FE中ARR不同"未澄清此问题 | P0 | 阻塞 | 需用户决策 | **v1/v2 遗留，未解决** |
| 3 | 业务规则 | §1「ARR_t-1<0→分母取绝对值」与引擎①现有行为**互斥**：`buildCompanyGrowthRate` L106 入库前 `filter grossRevenue>=0`，负收入整行不入库；`calculateGrowthRate` L164/172 跳过负月并 CAGR 桥接。引擎①永不出现"负前期值"，§1 负值分支在该引擎无触发条件。两种策略二选一 | P0 | 阻塞 | 需用户决策 | **v1/v2 遗留，未解决** |
| 4 | 功能完整性 | §4「适用于 Benchmarking 和 System Generated Forecast Generation」，但 Forecast 路径 `getForecastArrForBenchmark`（L956-965）用 `normalization.arr` 或 `revenue×12`，**无负值排除**；负值排除目前仅在 Actuals 路径（因上游 L106 已过滤）事实生效。真正缺口在 Forecast 路径 | P0 | 阻塞 | 需用户决策 | **v1/v2 遗留，未解决** |
| 5 | 语义与表述 | **v3 回退**：§4 删除了 v2 的 ARR=MRR×12 与三种 MRR 定义（分母=可用月份数），仅在示例加 `(MRR)`。该定义与代码 `calculateGrowthRateArrByDateForPeerFilter`（L789 分母=`subList.size()`）一致，删除后 peer-filter ARR 计算口径只剩单一示例支撑，"可用月份数""三种 recognition 模式"无正式定义 | P0 | 阻塞 | 需用户决策 | **v3 新退步**：恢复 ARR/MRR 口径定义并写明与 §1 ARR 关系 |
| 6 | 操作闭环 | §3/§4 未定义"全部月份为负 / 24 个月窗口内无非负值"的终态：`calculateArrRangeForPeerFilter(null/负)→0`（L771/777），ARR 无法计算时落哪档、是否报错/跳过均未写；recognition=1（Last Month）基准月被排除/缺失时 L784 返回 `ZERO×12=0`→TIER_0，无回溯，§4 未定义此行为 | P1 | 阻塞 | 需用户决策 | **v1/v2 遗留，未解决** |
| 7 | 语义与表述 | §4 D4 新增"该ARR的计算与当前FE中ARR的计算不同" 中 "FE中ARR" 为实现侧含糊术语（FE=前端？指哪个计算？常规视图 ARR？）。读者无法唯一推断指代 | P1 | 阻塞 | 需用户决策 | **v3 新增**：将"FE中ARR"改为明确业务术语（如"常规视图/公司详情页展示的 ARR"），并说明两套 ARR 各自来源 |
| 8 | 编号与可追溯性 | 全文仍无 SC/BR/AC 编号，无独立「验收标准」小节，BR 未集中定义（违反 project-conventions §2） | P0 | 阻塞 | 可自动修订 | **v1/v2 遗留，未解决** |
| 9 | 语义与表述 | §2「不影响该公司自身 ARR 增长率的展示」与 §4「不影响公司在常规视图中的 ARR 展示」表达同一原则（计算剔除≠展示剔除），分散重复 | P2 | 非阻塞 | 可自动修订 | **遗留**，未合并 |
| 10 | 边界条件 | 货币/单位未说明：ARR 桶用美元，系统支持多币种。负收入判定与分桶是否在归一化货币（USD）下进行未提及 | P2 | 非阻塞 | 需用户决策 | **遗留**，未解决 |
| 11 | 数据一致性 | 目标公司自身 t-1<0 时其增长率落入"已剔除负值同行"分布求百分位，口径是否可比未说明 | P2 | 非阻塞 | 需用户决策 | **遗留**，未解决 |
| 12 | 业务规则 | 手动同行组（`getManualColleagueGroupCompanyIdsIfEligible` L851，`buildBenchmarkPeerCompanyIds` 优先走手动组）是否同样执行 t-1<0 期次剔除未说明 | P2 | 非阻塞 | 需用户决策 | **遗留**，未解决 |
| 13 | 非功能需求 | 三个 benchmark 定时业务仅 SQS 触发（项目记忆 `project_benchmark_sqs_only_trigger`）。规则变更后历史 growth rate / benchmark 是否重算、由哪条 SQS 链触发未提及；无历史回算方案 | P3 | 非阻塞 | 需用户决策 | **遗留**，未解决 |
| 14 | 语义与表述 | §2.5 D3 仅 Forecast 条款追加"，继续执行剔除"，Actual 条款未加，且与下方通用条款"回退全平台同样执行此剔除"重复 → 不对称 + 重复，易误解为 Actual 回退后不剔除 | P1 | 阻塞 | 可自动修订 | **v3 新增**：删除单侧追加，统一由通用条款"回退后同样执行剔除"覆盖两种数据源 |

修订类别：**可自动修订** | **需用户决策**

### 表述与歧义问题

| # | 位置（章节/段落） | 原文摘录 | 问题类型 | 建议改写 |
|---|------------------|----------|----------|----------|
| T1 | §4 | "该ARR的计算与当前FE中ARR的计算不同，不应相互影响" | 歧义 | "用于同行框定的 ARR（peer-filter ARR）与公司常规视图/详情页展示的 ARR 计算口径不同，二者互不影响"，并各自标注来源（peer-filter ARR = `calculateGrowthRateArrByDateForPeerFilter`；展示 ARR = `normalization.arr`） |
| T2 | §一 / §1 / §4 | "ARR 增长率""ARR_t-1" vs §3/§4 "Gross Revenue""gross revenue" | 前后不一致 | 全文统一口径名词；恢复 §4 被删的 ARR=MRR×12 与三种 MRR 定义，并写明 §1 增长率所用 ARR 与此是否同源 |
| T3 | §1 表 | "ARR_t-1 = 0 或 null → ARR Growth Rate = 0" | 理解缺口 | 区分前期 0/null 与当期 0/null；现有引擎① `calculateGrowthRate` 当期 GR<0/null 返回 null、prev=0 返回 0，引擎② prev null/0 返回 0，需明确以哪套为准 |
| T4 | §3 步骤 3 | "在回溯窗口内找到第一个非负的 Gross Revenue 值" | 不闭环 | 补一句："若 24 个月内均为负，则 {兜底行为：用 0 / 跳过该公司 / 落 TIER_0}" |
| T5 | §4 示例 | "用历史三个月 gross revenue(MRR) 计算 ARR" | 理解缺口（v3 退步） | 恢复 v2 的三种 recognition（Last Month / Last Three Months / Trailing Twelve Months）MRR 定义与"可用 = 非负（≥0）且非空"定义，对齐代码 L780-790 |
| T6 | §2.5 Forecast 条款 | "…显示 Peer Fallback 提示，继续执行剔除。" | 重复啰嗦 + 前后不一致 | 删除此处单侧追加；剔除规则统一由下方"即使回退到全平台 active 公司，同样执行此剔除规则"集中表达，覆盖 Actual 与 Forecast 两侧 |
| T7 | §4 | "适用范围：适用于 Benchmarking 和 System Generated Forecast Generation" | 不闭环 | 明确 Forecast 路径（`getForecastArrForBenchmark`）当前无负值排除，需补回溯/排除步骤（normalization 表是否已过滤负月待确认） |

**问题类型枚举**：歧义｜不闭环｜理解缺口｜前后不一致｜套话/水分｜重复啰嗦｜详略失当

---

## 三、待确认事项

| # | 问题 | 需要谁确认 | 是否阻塞后续设计 |
|---|------|-----------|----------------|
| C1 | §1「ARR 增长率」约束哪套引擎：① gross-revenue 引擎（`FinancialGrowthRateServiceImpl`）还是② benchmark `ARR_GROWTH_RATE`（`MetricExtractor`），还是两者都改？ | 业务 + 后端 | 阻塞 |
| C2 | §1「负 t-1 取绝对值」是替换现有"负月预过滤 + CAGR 复合桥接"（L106/164/172）还是叠加？二者互斥 | 业务 + 后端 | 阻塞 |
| C3 | 期次级剔除与公司级 Peer Fallback（<3 回退）的执行顺序与终态；某期次剔除致 <3 是否触发该期次回退；回退后再剔除仍 <3 的终态；手动同行组是否同样剔除 | 业务 + 后端 | 阻塞 |
| C4 | Forecast 路径（`getForecastArrForBenchmark`）如何排除负 gross revenue；normalization 表是否已过滤负月 | 后端 | 阻塞 |
| C5 | §4 被删的 ARR/MRR 口径是否恢复；"可用月份数"精确定义（非负？非空？两者？）；§1 ARR 与 peer-filter ARR 是否同源 | 业务 | 阻塞 |
| C6 | "FE中ARR"具体指代（常规视图展示 ARR？哪段计算？） | 产品 + 前端 | 阻塞 |
| C7 | Last Month（recognition=1）模式下基准月被排除/缺失时的取值（回溯？置 0？TIER_0？）；24 个月窗口内全负 / ARR 无法计算时的兜底落档 | 业务 | 阻塞 |
| C8 | 目标公司自身 t-1<0 时其增长率百分位可比性 | 业务 | 非阻塞 |
| C9 | 正负判定与 ARR 分桶的币种基准（是否归一化 USD）；历史数据重算与 SQS 触发时机 | 业务 + 后端 | 非阻塞 |

---

## 四、假设（待验证）

- 假设 §1「ARR 增长率」涉及的至少是引擎② benchmark `ARR_GROWTH_RATE`（因 §1 强调"负的前期 ARR"，而引擎① 基于 gross revenue 且已预过滤负月，不会出现负前期值）。待 C1 确认。
- 假设 §4 的 peer-filter ARR 即 `calculateGrowthRateArrByDateForPeerFilter`（L780-790，窗口求均 ×12，分母 = `subList.size()`），"可用月份数" = 窗口内非负行数（代码因上游 L106 过滤已等价）。
- 假设 §2.5 数据质量与回退规则为现有规则，本需求仅"新增 t-1<0 期次剔除"。
- 假设 Peer Fallback 文案沿用现有 `FALLBACK_MSG`（L830），本需求不新增展示文案。
- 假设本需求为纯后端计算逻辑变更，无新增前端页面/角色权限。

---

## 五、建议补充到 PRD 的内容

- **术语与口径小节**（新增，置于 §二之前）：明确 ARR = MRR×12、三种 MRR 定义（恢复 v2 被删块）、"可用"定义、peer-filter ARR 与展示 ARR（"FE中ARR"）各自来源、data type 枚举（Actuals / Committed forecast / System generated forecast / Internal Peer）、§1 增长率约束的引擎。
- **编号体系**：为功能点分配 SC-01~SC-04，散落规则集中为 §七 BR-01~BR-nn，每 SC 补可判定 AC。
- **验收标准**：至少覆盖 $20M 边界归桶、负 t-1 取绝对值两示例、24 个月回溯命中/未命中兜底、剔除致 <3 触发 fallback、Forecast 路径负值排除、Last Month 基准月缺失行为、自身展示不受剔除影响。
- **范围澄清**：§2.5 Forecast 单侧"继续执行剔除"统一为通用条款（删除不对称表述）。
- **非功能需求**：历史数据重算策略与 SQS 触发；多币种归一化基准。

---

## 六、已自动修订项（流水线调用时填写）

| # | 位置 | 修订内容 | 类型 |
|---|------|----------|------|
| 1 | `docs/评审/01-prd.md` | 同步为外部 PRD v3 内容（§一删除审计悬空段；§2.4 区间改 `[$5M,$20M)`+`[$20M,+∞)`；§4 删除 ARR=MRR×12 及三种 MRR 定义、改为示例内 `(MRR)` 标注、新增"该ARR与FE中ARR不同"；§2.5 Forecast 末尾加"继续执行剔除"） | 状态补充（同步上游） |
| — | 正文 | 未对 PRD 正文做语义级自动修订：P0（引擎归属 C1、负值策略二选一 C2、剔除×fallback 交互 C3、Forecast 缺口 C4、MRR 口径恢复 C5、FE中ARR 含义 C6）均涉及业务决策，须先确认 | — |

---

## 结论

**❌ 阻塞**。v3 取得两项实质进展：**$20M 边界（§2.4）已与代码 `ArrTierEnum`/`calculateArrRangeForPeerFilter` 完全一致，关闭 v1/v2 长期 P0**；**§一删除审计悬空段，审计正式 descope，范围闭合**。但同时出现一处回退：**§4 删除了 v2 与代码一致的 ARR=MRR×12 及三种 MRR 定义（D5/#5）**，使 peer-filter ARR 口径退回单一示例支撑。

进入 gen-tdd 前必须先确认四项历史 P0：①§1 约束哪套增长率引擎（C1）；②"负 t-1 取绝对值"与现有"负月预过滤+CAGR 桥接"二选一（C2）；③期次剔除与 Peer Fallback 的先后顺序与终态（C3）；④Forecast 路径负值排除缺口（C4）；并恢复 §4 MRR 口径定义（C5）、澄清"FE中ARR"指代（C6）。

以下此前代码核对结论本次已重新复核并继续有效：
- 两套增长率引擎并存（引擎① `financial_growth_rate` GR 基、L106 负月整行预过滤 + L194-201 CAGR 跨月桥接；引擎② `MetricExtractor` 的 `ARR_GROWTH_RATE` L176-186，无负值分支），§1 未指明约束哪套。
- §1"绝对值分母"与引擎①"负月预过滤 + 复合桥接"互斥（L106/164/172）。
- §4 负值排除在 Actuals 路径已因上游 L106 过滤事实生效，真正缺口在 Forecast 路径 `getForecastArrForBenchmark`（L956-965，无负值排除）。
- §3 回溯 24 个月无果的兜底缺失（`calculateArrRangeForPeerFilter` null/负→0/TIER_0，L771/777）。
- 全文无 SC/BR/AC 编号与验收标准；无历史回算 / SQS 触发方案；无前端需求。
