# 负收入逻辑全系统一致性处理 PRD 审核报告（v2）

> 评审日期：2026-06-05
> 评审对象：`docs/评审/01-prd.md`（源自 `E:/LG_DOCS/LG/docs/负收入逻辑全系统一致性处理_需求文档.md`，v2，Sprint 111）
> 已加载项目上下文：CLAUDE.md（根 + CIOaas-api）、project-conventions、`ArrTierEnum.java`、`FinancialGrowthRateServiceImpl.java`、`MetricExtractor.java`、`ColleagueCompanyServiceImpl.java`、`Invite.java`；README 未找到

---

## 〇、v2 相对 v1 的变化（已逐行 diff 确认）

| # | 变化 | 评估 |
|---|------|------|
| D1 | §2.4 区间文案 `($20M, +∞) → $20M 及以上` 改为 `$20M 以上` | **未解决矛盾，反而恶化**：现仍声明 `[$5M, $20M]` 含 $20M，且 `($20M, +∞)` 用开区间 + "$20M 以上"措辞，等于明确把 $20M 归入 `[$5M, $20M]` 桶。这与代码相反 — 见问题 #1 |
| D2 | §4 末尾新增 `ARR=MRR×12` 及三种 MRR 计算（Last Month / Last Three Months / Trailing Twelve Months，分母为"可用月份数"） | 补齐了 ARR 取值口径，方向正确；但"可用"未定义、术语 Last Three Months 与代码不符、是否为全局定义不明 — 见问题 #6/#7/#8 |
| D3 | 原 §5「系统全面审计」整节删除，但 §一 背景仍写"本需求还应审计系统中所有…其他区域" | **新增范围声明矛盾**：背景声明审计范围，功能章节已无对应可验收条目 — 见问题 #5 |

**结论**：v2 解决了 v1 的 #5（data type 与 ARR 取值已部分补全）方向，但 **v1 的 4 项 P0 中 0 项被真正解决**，并新增 2 项不一致（D1 边界恶化、D3 范围声明悬空）。

---

## 一、评分仪表盘

| 维度 | 评分 | 说明 |
|------|------|------|
| 语义与表述 | 4/10 | ARR 与 Gross Revenue 双口径仍混用；"可用"无定义；MRR 块嵌在示例下，全局性不明 |
| 功能完整性 | 5/10 | §5 删除后背景悬空；Forecast 路径负值排除、Last Month 基准月缺失行为仍缺 |
| 操作闭环 | 4/10 | 期次级剔除 × 公司级 Peer Fallback 交互仍未定义；全负月落档无终态 |
| 数据一致性 | 3/10 | $20M 边界 v2 后与 `ArrTierEnum`/`calculateArrRangeForPeerFilter` 明确相反；两套增长率引擎未指明约束哪套 |
| 权限覆盖 | N/A | 纯计算逻辑变更，无角色/权限维度（不计入综合） |
| 业务规则 | 4/10 | BR 仍未集中编号；§1 负 ARR 公式与现有"跳过负月 + 复合桥接"策略互斥且 PRD 未提及 |
| 编号与可追溯性 | 2/10 | 全文仍无 SC/BR/AC 编号，无验收标准小节 |
| **综合** | **❌ 阻塞** | ≥4 项 P0 未解；$20M 边界、ARR 引擎归属、剔除×fallback 交互必须先确认 |

---

## 二、评审通过项

- ✅ 业务背景清晰：明确两类问题（个体公司指标 / 基准与同行计算），目标可理解。
- ✅ §1 ARR 增长率三分支表（>0 / =0或null / <0）逻辑自洽，含正反例。
- ✅ §3 收入基础回溯规则（24 个日历月、首个非负值）描述具体、可执行。
- ✅ §4 Target Company 排除示例（三个月 gross revenue 取均值）量化清晰，可直接转测试用例。
- ✅ §2 动态判定说明（按期间剔除而非永久踢出）消除了一处潜在歧义。
- ✅（v2 新增）§4 补充 `ARR=MRR×12` 及三种 MRR 公式，明确了同行 ARR 取值口径，与 `calculateGrowthRateArrByDateForPeerFilter` 的窗口求均 ×12 思路一致。

---

## 三、问题与建议

| # | 问题分类 | 问题描述 | 严重程度 | 是否阻塞 | 修订类别 | 建议 |
|---|----------|----------|----------|----------|----------|------|
| 1 | 数据一致性 | §2.4 ARR 分桶：v2 仍标注 `[$5M, $20M]` 含 $20M，且 `($20M, +∞) → $20M 以上`。但代码 `ArrTierEnum.fromArr`（L31）与 `ColleagueCompanyServiceImpl.calculateArrRangeForPeerFilter`（L772）均为 **arr≥20M → TIER_5/range5**，即实际是 `[$5M, $20M)` + `[$20M, +∞)`。PRD 与实现对 $20M 归属完全相反 | P0 | 阻塞 | 需用户决策 | 二选一并对齐：(a) 改 PRD 为 `[$5M, $20M)` / `[$20M, +∞)`（与现有两处代码一致，零代码改动）；(b) 维持 PRD 含 $20M 于低桶，则需同步改两处 `>= B20000` 为 `> B20000`。强烈建议 (a) |
| 2 | 业务规则 | 系统存在**两套增长率引擎**：① `FinancialGrowthRateServiceImpl.calculateGrowthRate`（L163-205，基于 **Gross Revenue**，当期 GR<0 返回 null，prev=0 返回 0，跨月用 CAGR 复合桥接）；② benchmark 指标 `ARR_GROWTH_RATE`（`MetricExtractor` L174-186，基于 `financial_normalization_current.arr`，prev null/0→0，**无负值分支**）。§1 未指明约束哪一套、是否两套都改 | P0 | 阻塞 | 需用户决策 | 明确 §1 的"ARR 增长率"指 ①还是②还是两者。若指②，需在 `MetricExtractor` L176-186 增加 `prevArr<0 → 取绝对值分母`分支；若指①，则与 #3 的现有"跳过负月"策略冲突 |
| 3 | 业务规则 | §1「ARR_t-1 < 0 → 分母取绝对值」与引擎①现有行为**互斥**：`buildCompanyGrowthRate` L106 在入库前 `filter grossRevenue>=0`，负收入整行不入库；`calculateGrowthRate` L164/172 跳过负月并用复合增长率桥接缺口。即引擎①永远不会出现"负的前期值"，§1 的负值分支在该引擎下无触发条件。这套"跳过负月+复合桥接"本身就是一种负收入处理策略，与 §1"负值用绝对值分母直接计算"二选一 | P0 | 阻塞 | 需用户决策 | 明确：保留现有"负月预过滤+CAGR 桥接"还是改为"负 t-1 取绝对值"。两者不能并存——若改后者，需移除 L106 的 `grossRevenue>=0` 过滤与 L164/172 的跳过逻辑 |
| 4 | 操作闭环 | §2 期次级剔除（t-1<0 逐期剔除同行）与 §2.5「有效同行 <3 → 回退全平台 + Peer Fallback」交互仍未定义：剔除发生在 fallback 判定之前还是之后？fallback 后是否再次执行剔除？代码 `buildBenchmarkPeerCompanyIds` L927 的 fallback 为公司级整体判定，无逐期次计数 | P0 | 阻塞 | 需用户决策 | 明确剔除与 fallback 先后顺序及剔除致 <3 时终态。建议：先按维度匹配 → 逐期次剔除 t-1<0 → 若 <3 触发 fallback → fallback 池同样执行逐期剔除 |
| 5 | 功能完整性 | §一背景仍写"本需求还应审计系统中所有当前使用或可能引入负收入值的其他区域"，但 v2 已删除原 §5 审计功能章节 → 范围声明与功能章节不一致，审计任务无可验收落点 | P1 | 阻塞 | 需用户决策 | 二选一：(a) 删/弱化 §一该句，确认审计不在本 Sprint 范围；(b) 恢复 §5 并列出已知待审计模块清单（如 PortfolioBenchmark、System Generated Forecast、`MetricExtractor` ARR_GROWTH_RATE 等）+ 每处一致性判定项 |
| 6 | 语义与表述 | §4 新增 MRR 定义中"可用"（可用 Gross Revenue / 可用月份数）未定义：是"非空"、"非负"还是两者？影响分母取值 | P1 | 阻塞 | 需用户决策 | 明确"可用 = 非负（≥0）且非空"。据 §4 示例（-1000 不计入、只用两个月）应为"非负"，建议显式写明并与 §3「≥0」口径统一 |
| 7 | 数据一致性 | §4 MRR 定义中 "Last Three Months" 与代码不符：`Invite.java` L116 `revenueRecognition` 注释为 `2: Last Quarter`（非 Last Three Months）。recognition=1 注释为 Last Month、3 为 Trailing Twelve Months（这两项一致） | P2 | 非阻塞 | 需用户决策 | 统一术语：要么 PRD 改回 "Last Quarter"，要么代码注释/枚举改为 "Last Three Months"（建议后者，PRD 措辞更准确，因实现 L786 取窗口为当月往前 2 个月共 3 个月） |
| 8 | 语义与表述 | §4 的 `ARR=MRR×12` 与三种 MRR 块挂在 §4 示例之下，未说明是否为**全局定义**（§一/§1 提到的"ARR"是否与此同源）。§1 用 ARR_t-1，§4 才定义 ARR 来源，定义位置滞后于使用 | P1 | 阻塞 | 需用户决策 | 将 ARR/MRR 口径上提为独立"术语与口径"小节，明确 §1 增长率所用 ARR 是否即此 MRR×12，还是引擎②的 `normalization.arr` |
| 9 | 操作闭环 | recognition=1（Last Month）时若该基准月行缺失（含被 L106 过滤掉的负月）→ `calculateGrowthRateArrByDateForPeerFilter` L784 返回 `ZERO×12=0` → `calculateArrRangeForPeerFilter(0)=0 → TIER_0`，无回溯。§4 未定义 Last Month 模式下基准月被排除时的行为（回溯？置 0？落 TIER_0？） | P1 | 阻塞 | 需用户决策 | 补充 Last Month 模式下基准月不可用时的取值规则（建议与 §3 一致：向前回溯至首个非负月） |
| 10 | 操作闭环 | §3/§4 未定义"全部月份为负 / 24 个月窗口内无非负值"时的终态：`ArrTierEnum.fromArr(null/负)→TIER_0`，但 ARR 无法计算时落哪档、是否报错/跳过均未写 | P1 | 阻塞 | 需用户决策 | 补充：回溯窗口内全负时的兜底（用 0？落 TIER_0？跳过该公司？），并与代码 TIER_0 行为对齐 |
| 11 | 功能完整性 | §4「适用于 Benchmarking 和 System Generated Forecast Generation」，但 Forecast 路径 `getForecastArrForBenchmark`（L956-965）用 `normalization.arr` 或 `revenue×12`，**无负值排除**；负值排除目前仅在 Actuals 路径（因上游 L106 已过滤）事实生效。真正缺口在 Forecast 路径 | P1 | 阻塞 | 需用户决策 | 明确 Forecast 路径如何排除负 gross revenue（normalization 表是否已过滤负月？若未，需在 `getForecastArrForBenchmark` 增加排除/回溯逻辑） |
| 12 | 编号与可追溯性 | 全文仍无 SC/BR/AC 编号，无独立「验收标准」小节，BR 未集中定义（违反 project-conventions §2） | P0 | 阻塞 | 可自动修订 | 为各功能点分配 SC-01~SC-04；散落规则提炼为 BR-01~BR-nn 集中列出；每个 SC 补可判定 AC |
| 13 | 语义与表述 | §2「不影响该公司自身 ARR 增长率的展示」与 §4「不影响公司在常规视图中的 ARR 展示」表达同一原则（计算剔除 ≠ 展示剔除），分散重复 | P2 | 非阻塞 | 可自动修订 | 提炼为统一 BR：「负值剔除仅作用于同行/基准计算输入，不改变公司自身指标展示」，他处引用 |
| 14 | 边界条件 | 货币/单位未说明：ARR 桶用美元，系统支持多币种。负收入判定与分桶是否在归一化货币下进行未提及 | P2 | 非阻塞 | 需用户决策 | 明确分桶与正负判定使用的币种基准（归一化后 USD？） |
| 15 | 数据一致性 | 目标公司自身 t-1<0 时的百分位可比性未定义：§2 剔除的是同行 t-1<0，但若目标公司自身 t-1<0（§1 用绝对值算出一个增长率），该值落入由"已剔除负值同行"构成的分布求百分位，口径是否可比未说明 | P2 | 非阻塞 | 需用户决策 | 明确目标公司自身 t-1<0 时其增长率百分位的计算/展示规则 |
| 16 | 业务规则 | 手动同行组（manual colleague group，`getManualColleagueGroupCompanyIdsIfEligible` L851）路径未被 §2 覆盖：手动组是否同样执行 t-1<0 期次剔除未说明 | P2 | 非阻塞 | 需用户决策 | 明确手动同行组是否适用本剔除规则（建议适用，保持一致） |
| 17 | 非功能需求 | 三个 benchmark 定时业务仅 SQS 触发（项目记忆 `project_benchmark_sqs_only_trigger`）。规则变更后历史 growth rate / benchmark 是否需重算、由哪条 SQS 链触发未提及 | P3 | 非阻塞 | 需用户决策 | 补充历史数据重算策略与触发链路 |

修订类别：**可自动修订** | **需用户决策**

### 表述与歧义问题

| # | 位置（章节/段落） | 原文摘录 | 问题类型 | 建议改写 |
|---|------------------|----------|----------|----------|
| T1 | §2.4 ARR 规模 | `[$5M, $20M] → 包含 $5M，包含 $20M`；`($20M, +∞) → $20M 以上` | 前后不一致 | `[$5M, $20M) → 含 $5M，不含 $20M`；`[$20M, +∞) → 含 $20M 及以上`（与 `ArrTierEnum`/`calculateArrRangeForPeerFilter` 左闭右开一致） |
| T2 | §一 / §1 / §4 | "ARR 增长率""ARR_t-1" vs §3/§4 "Gross Revenue""gross revenue" | 前后不一致 | 全文统一口径名词；§4 已补 `ARR=MRR×12`，应将该换算上提到首次出现处并写明 §1 增长率所用 ARR 与此同源 |
| T3 | §1 表 | "ARR_t-1 = 0 或 null → ARR Growth Rate = 0" | 理解缺口 | 区分前期 0/null 与当期 0/null；现有引擎① `calculateGrowthRate` 当期 GR<0/null 返回 null，引擎② prev null/0 返回 0，需明确以哪套为准 |
| T4 | §3 步骤 3 | "在回溯窗口内找到第一个非负的 Gross Revenue 值" | 不闭环 | 补一句："若 24 个月内均为负，则 {兜底行为}" |
| T5 | §一 | "本需求还应审计系统中所有当前使用或可能引入负收入值的其他区域" | 套话/范围悬空 | v2 已删 §5 功能章节 → 删除此句或恢复 §5 并列具体待审计模块清单 |
| T6 | §4 MRR 块 | "（包括当月的最近三个月可用 Gross Revenue 总和）/（可用月份数）" | 理解缺口 | 定义"可用 = 非负（≥0）且数据非空"；"最近三个月/十二个月"明确为"含当月往前数 N 个日历月" |
| T7 | §4 MRR 块 | "Last Three Months" | 前后不一致 | 与代码 `Invite.java` L116 `2: Last Quarter` 统一术语（建议代码改注释为 Last Three Months） |
| T8 | §4 | "适用范围：适用于 Benchmarking 和 System Generated Forecast Generation" | 不闭环 | 明确 Forecast 路径（`getForecastArrForBenchmark`）当前无负值排除，需补回溯/排除步骤 |

**问题类型枚举**：歧义｜不闭环｜理解缺口｜前后不一致｜套话/水分｜重复啰嗦｜详略失当

---

## 三、待确认事项

| # | 问题 | 需要谁确认 | 是否阻塞后续设计 |
|---|------|-----------|----------------|
| C1 | §1「ARR 增长率」约束哪套引擎：① gross-revenue 引擎（`FinancialGrowthRateServiceImpl`）还是② benchmark `ARR_GROWTH_RATE`（`MetricExtractor`），还是两者都改？ | 业务 + 后端 | 阻塞 |
| C2 | $20M 归属哪个桶？（建议对齐代码：`[$5M,$20M)` / `[$20M,+∞)`） | 业务/产品 | 阻塞 |
| C3 | §1「负 t-1 取绝对值」是替换现有"负月预过滤 + CAGR 复合桥接"（L106/164/172）还是叠加？二者互斥 | 业务 + 后端 | 阻塞 |
| C4 | 期次级剔除与公司级 Peer Fallback（<3 回退）的执行顺序与终态；手动同行组是否同样剔除 | 业务 + 后端 | 阻塞 |
| C5 | §4 MRR "可用"的精确定义（非负？非空？两者？）；ARR/MRR 是否为全局口径，与 §1 ARR 同源 | 业务 | 阻塞 |
| C6 | Forecast 路径（`getForecastArrForBenchmark`）如何排除负 gross revenue；normalization 表是否已过滤负月 | 后端 | 阻塞 |
| C7 | Last Month（recognition=1）模式下基准月被排除/缺失时的取值（回溯？置 0？TIER_0？） | 业务 | 阻塞 |
| C8 | 24 个月窗口内全负 / ARR 无法计算时的兜底落档行为 | 业务 | 阻塞 |
| C9 | 目标公司自身 t-1<0 时其增长率百分位可比性 | 业务 | 非阻塞 |
| C10 | 正负判定与 ARR 分桶的币种基准（是否归一化 USD）；历史数据重算与 SQS 触发时机 | 业务 + 后端 | 非阻塞 |
| C11 | 术语 "Last Three Months" vs 代码 "Last Quarter" 以谁为准 | 产品 + 后端 | 非阻塞 |

---

## 四、假设（待验证）

- 假设 §1「ARR 增长率」涉及的至少是引擎② benchmark `ARR_GROWTH_RATE`（因 §1 强调"负的前期 ARR"，而引擎① 基于 gross revenue 且已预过滤负月，不会出现负前期值）。待 C1 确认。
- 假设 §4 的 `ARR=MRR×12` 与 `calculateGrowthRateArrByDateForPeerFilter`（L780-790，窗口求均 ×12）为同一逻辑，"可用月份数" = 窗口内非负行数（代码因上游 L106 过滤已等价）。
- 假设 §2.5 数据质量与回退规则为现有规则，本需求仅"新增 t-1<0 期次剔除"。
- 假设 Peer Fallback 文案沿用现有 `FALLBACK_MSG`，本需求不新增展示文案。
- 假设本需求为纯后端计算逻辑变更，无新增前端页面/角色权限。

---

## 五、建议补充到 PRD 的内容

- **术语与口径小节**（新增，置于 §二之前）：明确 ARR = MRR×12、三种 MRR 定义、"可用"定义、ARR 与 Gross Revenue 关系、data type 枚举（Actuals / Committed forecast / System generated forecast / Internal Peer）、§1 增长率约束的引擎。
- **编号体系**：为功能点分配 SC-01~SC-04，散落规则集中为 §七 BR-01~BR-nn，每 SC 补可判定 AC。
- **验收标准**：至少覆盖 $20M 边界归桶、负 t-1 取绝对值两示例、24 个月回溯命中/未命中兜底、剔除致 <3 触发 fallback、Forecast 路径负值排除、Last Month 基准月缺失行为、自身展示不受剔除影响。
- **范围澄清**：§一审计句与已删 §5 二选一（删句或恢复 §5 列模块清单）。
- **非功能需求**：历史数据重算策略与 SQS 触发；多币种归一化基准。

---

## 六、已自动修订项（流水线调用时填写）

| # | 位置 | 修订内容 | 类型 |
|---|------|----------|------|
| 1 | `docs/评审/01-prd.md` | 同步为外部 PRD v2 内容（§2.4 "$20M 及以上"→"$20M 以上"；§4 新增 ARR=MRR×12 及三种 MRR 定义；删除原 §5 审计章节） | 状态补充（同步上游） |
| — | 正文 | 未对 PRD 正文做语义级自动修订：P0（$20M 边界、ARR 引擎归属、剔除×fallback 交互、负值策略二选一）均涉及业务决策，须先确认 C1~C8 | — |

---

## 结论

**❌ 阻塞**。v2 在 ARR 取值口径上有进展（补全 MRR×12 定义），但 **v1 的 4 项 P0 无一真正解决**，并因 §2.4 措辞调整使 $20M 边界与代码（`ArrTierEnum.fromArr`、`calculateArrRangeForPeerFilter` 均 `>=20M→TIER_5`）变为明确相反，同时 §一审计句因 §5 删除而范围悬空。

进入 gen-tdd 前必须先确认：①§1 约束哪套增长率引擎（C1）；②$20M 归属并对齐代码（C2）；③"负 t-1 取绝对值"与现有"负月预过滤+CAGR 桥接"二选一（C3）；④期次剔除与 Peer Fallback 的先后与终态（C4）；⑤Forecast 路径负值排除缺口（C6）。
