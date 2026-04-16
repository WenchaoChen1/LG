## 需求文档审查报告

**功能**：Create Benchmark Comparison UI - Portfolio Intelligence
**文档路径**：`C:\Users\Administrator\Downloads\Benchmark Portfolio Intelligence_需求文档.md`
**审查时间**：2026-04-14
**整体评估**：需修改后再用于设计

---

### 审查总览

| 严重度 | 数量 | 说明 |
|--------|------|------|
| :red_circle: 阻断性 | 9 | 必须修复才能进入设计 |
| :yellow_circle: 重要 | 12 | 建议修复后再进入设计 |
| :blue_circle: 改进 | 8 | 可在开发过程中完善 |

#### 章节覆盖与问题分布

| 章节 | 审查状态 | :red_circle: | :yellow_circle: | :blue_circle: | 一句话说明 |
|------|---------|-----|-----|-----|-----------|
| §功能概述 | :white_check_mark: 已审查 | 0 | 0 | 0 | 无问题 |
| §目录 | :white_check_mark: 已审查 | 1 | 0 | 1 | 幽灵章节"指标卡片与详情展示"不存在 |
| §使用流程 | :white_check_mark: 已审查 | 0 | 1 | 0 | 与 Asana ticket 公司状态描述矛盾 |
| §筛选条件区域 | :white_check_mark: 已审查 | 2 | 3 | 2 | 多选筛选器无最小选择约束；公司排除状态矛盾 |
| §快照视图 | :white_check_mark: 已审查 | 4 | 4 | 2 | 排序方向未定义、行结构层级不明、公式边界缺失 |
| §趋势视图 | :white_check_mark: 已审查 | 1 | 3 | 2 | 缺失数据展示P0会误导、Info icon未覆盖 |
| §数据格式 | :white_check_mark: 已审查 | 0 | 1 | 1 | 百分位取整规则与外部基准插值结果矛盾 |
| 全局/跨章节 | :white_check_mark: 已审查 | 1 | 0 | 0 | 术语不一致（Exit vs Exited、Benchmarkit vs Benchmarkit.ai） |

---

### 功能理解

管理员用户在 Portfolio Intelligence 模块新增的 Benchmarking 页面中，从 Portfolio 内选择多家公司，通过五个筛选维度（View/Filter/Data/Benchmark/Date）配置分析视角。系统从 Normalization Tracing 模块取公司标准化财务数据，按 Peer Group Management 绑定或六维自动匹配规则构建内部同行池，从 Benchmark Entry 取外部行业基准摘要统计数据。对内部同行采用 Nearest Rank 法、对外部基准采用线性插值法计算百分位，最终在 Snapshot 视图以表格按公司分组展示百分位+实际值，在 Trend 视图以折线图按指标分组展示跨月百分位趋势。

---

### :red_circle: 阻断性问题（共 9 个，必须修复才能进入设计）

> 逻辑矛盾、规则缺失、公式错误、关键信息丢失——不修复则开发无法动工

#### §快照视图 - 计算逻辑（4 个）

1. **指标排序方向（正向/反向）未定义，百分位计算无法执行**
   - 位置：§快照视图 - 计算逻辑（行 222-241）
   - 原文：「公式：P_target = ((R - 1) / (N - 1)) × 100 ... R = 目标公司在同行中的排名」
   - 问题：百分位公式依赖 R（排名），但文档从未定义 6 个指标各自的排序方向——哪些是"越大越好"（升序排列，值大者排名高），哪些是"越小越好"（降序排列）。Asana ticket「Implement Peer-Relative Percentile Ranking Engine」明确写明："Sort values of standard metrics in ascending order (higher value results in better rank and percentile), but the 'Monthly Net Burn Rate' and 'Sales Efficiency Ratio' in descending order." PRD 缺失此关键规则，开发无法确定排序方向。
   - 建议：在计算逻辑章节增加排序方向表：

     | 指标 | 排序方向 | 说明 |
     |------|---------|------|
     | ARR Growth Rate | 升序（越大越好） | 值大 → 排名高 → 百分位高 |
     | Gross Margin | 升序 | 同上 |
     | Monthly Net Burn Rate | 降序（越小越好） | 值小 → 排名高 → 百分位高 |
     | Monthly Runway | 升序 | 值大 → 排名高 |
     | Rule of 40 | 升序 | 值大 → 排名高 |
     | Sales Efficiency Ratio | 降序 | 值小 → 排名高 |

2. **同行匹配最小有效同行数与 Asana ticket 矛盾**
   - 位置：§同行匹配属性 - 数据质量（行 261-262）
   - 原文 A（PRD）：「若有效同行 < 3 家，回退到全平台基准」
   - 原文 B（Asana Peer Ranking Engine ticket）：「Peer groups requires min. 4 companies, so it will fall back to portfolio benchmark」
   - 问题：PRD 要求最少 3 家同行，Asana ticket 要求最少 4 家。开发不知道按哪个实现。
   - 建议：与 Peer Ranking Engine ticket owner 确认统一阈值，PRD 和 ticket 同步修改为一致数值。若采用 4 家（Asana 版本），则 PRD 修改为「若有效同行 < 4 家」。

3. **Overall Benchmark Score 计算范围在多 Data 类型时模糊**
   - 位置：§表格列 - 第三列（行 209）
   - 原文：「数据值为该行中4-N列所有列的百分位的算术平均值，百分位是N/A时不参与计算」
   - 问题：当用户选择多种 Data 类型（如 Actuals + Committed Forecast）时，每个指标列会显示多个百分位值（每种 Data 类型一个）。"该行中4-N列所有列的百分位"是指当前 Benchmark 行对应的某一种 Data 类型的百分位，还是所有 Data 类型的百分位都参与平均？另外，Asana Peer Ranking Engine ticket 定义了"Category Score: Arithmetic mean of all valid metric percentiles within that category. Overall Score: Arithmetic mean of the four category scores."——这是先按类别平均再跨类别平均，与 PRD 的"所有指标列直接平均"不同。
   - 建议：
     1. 明确 Overall Score 的计算粒度：仅基于当前行对应的 Benchmark + Data Type 组合的百分位
     2. 明确计算层级：是所有指标直接平均，还是先按 Category 平均再取 Category 均值（与 Asana ticket 对齐）
     3. 明确 >P75 / <P25 等估算百分位是否参与计算（用边界值还是排除）

4. **"全平台基准"（Portfolio Benchmark / Platform Benchmark）概念未定义**
   - 位置：§同行匹配规则（行 245、261、262）
   - 原文：「回退到全平台基准，显示 Peer Fallback 提示」
   - 问题：三处提及"全平台基准"但从未定义。Asana ticket 使用"Portfolio Benchmark (all active companies within LG)"这一表述，但 PRD 中无此定义。开发无法确定：全平台基准的公司池是什么？是当前 Portfolio 内所有活跃公司，还是 LG 平台上所有活跃公司？是否仍按 ARR 规模/会计方法等维度分组？
   - 建议：在同行匹配规则章节增加"全平台基准"的定义段落，明确：(1) 公司池范围；(2) 是否保留部分匹配维度（如 ARR 规模）；(3) 排除条件是否与同行匹配一致。

#### §筛选条件区域（2 个）

5. **Data / Benchmark / Filter 三个多选筛选器均无最小选择约束**
   - 位置：§4. Data（行 139-157）、§5. Benchmark（行 159-181）、§3. Filter（行 118-136）
   - 原文 Data：「交互方式：多选标签」（未提及最小选择数）
   - 原文 Benchmark：「交互方式：多选复选框」（未提及最小选择数）
   - 原文 Filter：仅定义了 "All" 互斥规则，未定义取消所有选项后的行为
   - 问题：三个多选筛选器都没有定义"至少选一项"的约束。如果用户取消所有选项，页面行为未知。Companies 筛选器有空状态定义（行 82-83），但 Data/Benchmark/Filter 没有。
   - 建议：为每个多选筛选器补充以下规则之一：
     - 方案 A：至少保留一项选中，最后一项不可取消（交互上禁用取消操作）
     - 方案 B：允许全部取消，定义空状态展示（如"请至少选择一项"提示文案）

6. **公司筛选器置灰状态与 Asana ticket 矛盾**
   - 位置：§1. Companies 筛选器（行 88）、§使用流程 第2步（行 34）
   - 原文 A（PRD 行 88）：「状态为Exit或Shut down的公司在列表中置灰」
   - 原文 B（Asana ticket AC）：「Inactive companies will be greyed out in the filter list.」
   - 问题：PRD 说 Exit/Shut Down 置灰，Asana ticket 说 Inactive 置灰。这是两组不同的状态。Asana Peer Ranking Engine ticket 的排除条件包含三个状态：Exited、Shut Down、Inactive。PRD 仅提及两个。
   - 建议：与产品确认：Companies 筛选器中应该置灰不可选的状态列表是什么？建议统一为 Exited + Shut Down + Inactive 三种状态均置灰不可选，与 Peer Ranking Engine 排除条件保持一致。

#### §目录 / 全局（3 个）

7. **目录中"指标卡片与详情展示"章节在正文中不存在**
   - 位置：§目录（行 18）
   - 原文：「- [指标卡片与详情展示](#指标卡片与详情展示)」
   - 问题：目录引用了一个不存在的章节。这可能意味着该章节应该存在但被遗漏，或者是文档重构后残留的幽灵链接。如果该章节原本应包含指标卡片的展开/收起、详情弹窗等交互定义，则这部分需求是缺失的。
   - 建议：确认该章节是否有计划内容。如有，补充完整；如无，从目录中删除。

8. **外部基准数据缺失时的处理未定义**
   - 位置：§外部行业基准（行 270-287）
   - 原文：仅定义了超范围处理和插值处理
   - 问题：Internal Peers 有完整的回退链（绑定同行 → 自动匹配 → 全平台基准），但外部基准（KeyBanc / High Alpha / Benchmarkit）当选定指标/时间段/ARR范围在 Benchmark Entry 中无数据时，没有任何处理规则。另外，Asana Manual Import ticket 的 Benchmarking Map 显示：KeyBanc 无 Monthly Net Burn 数据，High Alpha 无 Monthly Runway 和 Monthly Net Burn 数据。这些确定缺失的场景在 PRD 中完全未覆盖。
   - 建议：增加外部基准数据缺失处理规则：
     - 若选定指标在某外部基准中无对应映射 → 该指标列显示"N/A"或"Not Benchmarked"
     - 若选定时间段/ARR范围无匹配数据 → 显示"No Data"并说明原因
     - Overall Score 计算时排除无数据的指标

9. **Snapshot 表格行结构层级不明（Company > Benchmark > Data Type 还是 Company > Data Type > Benchmark）**
   - 位置：§表格行（行 200-204）
   - 原文 A：「行内黑色字体是Actuals值，紫色字体是Committed Forecast值，紫色带标记的字体是System Generated Forecast的值」
   - 原文 B：「Benchmark按照以下顺序展示：Internal Peers → KeyBanc → High Alpha → Benchmarkit」
   - 问题：当用户选择多个 Data 类型和多个 Benchmark 时，每家公司的子行结构不清晰。例如用户选了 Actuals + CF 和 Internal Peers + KeyBanc，是展示为：
     - 方案 A：Internal Peers (Actuals行 + CF行) → KeyBanc (Actuals行 + CF行)？
     - 方案 B：Actuals (Internal Peers行 + KeyBanc行) → CF (Internal Peers行 + KeyBanc行)？
     文档描述暗示行按字体颜色区分 Data Type（方案 B 倾向），但 Benchmark 按顺序展示（方案 A 倾向），两者冲突。
   - 建议：明确子行层级结构并用表格示例说明。建议参考 Asana ticket 中提及的 Figma 设计稿确定层级，然后在 PRD 中补充一个具体的多选组合表格 mockup。

---

### :yellow_circle: 重要问题（共 12 个，建议修复后再进入设计）

> 描述模糊、边界未覆盖、可能有歧义——不修复则开发需要反复确认

#### §筛选条件区域（3 个）

1. **公司排除状态术语不一致：Exit vs Exited、Shut down vs Shut Down**
   - 位置：§使用流程（行 34）、§Companies 筛选器（行 88）、§排除条件（行 264-267）
   - 原文 A（行 34/88）：「Exit或Shut down」
   - 原文 B（行 265-266）：「#Exited  #Shut Down」
   - 问题：同一文档中，状态名称拼写不一致。"Exit" vs "Exited"（时态不同），"Shut down" vs "Shut Down"（大小写不同）。且行 267 出现的 "#Inactive" 状态仅在排除条件中出现，筛选器章节未提及。
   - 建议：统一为 Asana ticket 中的标准命名（Exited / Shut Down / Inactive），全文替换。

2. **Trend 视图起止月相同时的 UI 行为未定义**
   - 位置：§View 筛选器（行 112）、§日期选择器（行 187）
   - 原文：「开始月份和结束月份，且两者必须不同」
   - 问题：定义了约束但未定义违反时的交互行为。开发不知道是禁用提交按钮、弹出错误提示、还是阻止选择相同月份。
   - 建议：补充交互行为，如"当用户选择的开始月份与结束月份相同时，结束月份选择器不允许选中该月份（置灰），或弹出提示'开始月份与结束月份不能相同'"。

3. **Data 筛选器缺少互斥/全选规则**
   - 位置：§4. Data（行 139-157）
   - 原文：「交互方式：多选标签」
   - 问题：Filter 筛选器有详细的 "All" 互斥规则定义（行 122-124），但 Data 筛选器虽然也是多选，却没有类似的交互规则说明。是否有"Select All"功能？是否允许全部取消？这些在 Filter 筛选器中都有定义但在 Data 筛选器中缺失。
   - 建议：补充 Data 筛选器的交互规则，至少说明是否有全选/全不选场景及对应行为。

#### §快照视图（4 个）

4. **反向公式（从百分位 P 推导排名 R）的用途未说明**
   - 位置：§计算逻辑（行 235-241）
   - 原文：「根据目标百分位数 (P) 计算排名 (R)：R = ((P * (N - 1))/100) + 1」
   - 问题：文档给出了从 P 到 R 的反向公式，但未说明这个公式在 UI 中的使用场景。是用于 Tooltip 中展示 P25/P50/P75 对应的实际值？还是用于内部计算？如果是 Tooltip 用途，应与 Tooltip 内容描述（行 208）关联。
   - 建议：在公式后补充说明"此公式用于在 Snapshot 视图 Tooltip 中，根据标准百分位点（P25、P50、P75）确定对应的同行指标值"（或实际用途）。

5. **精确百分位示例 P45 在外部基准场景下不合理**
   - 位置：§外部行业基准 - 特殊处理（行 278）
   - 原文：「若指标值完全匹配，显示精确百分位（例如 P45）」
   - 问题：外部基准通常只提供 P25、P50、P75 三个点位。"完全匹配"只可能产生 P25、P50 或 P75，不可能产生 P45。示例 P45 会让开发误以为有更多数据点。
   - 建议：将示例改为「例如 P50」，并说明"精确百分位仅在公司值恰好等于某已知百分位点的值时出现"。

6. **百分位取整规则与外部基准插值结果显示矛盾**
   - 位置：§数据格式（行 351）、§外部行业基准 - 插值处理（行 283）
   - 原文 A（行 351）：「百分位取整」
   - 原文 B（行 283）：「~P62.5」（显示小数）
   - 问题：全局数据格式规则要求"百分位取整"，但插值举例中显示了 ~P62.5（一位小数）。两处规则矛盾。
   - 建议：确认外部基准的插值百分位是取整显示（~P63）还是保留小数（~P62.5），然后统一两处描述。

7. **同行匹配中"连续六个月非负 gross revenue"的"连续"定义模糊**
   - 位置：§数据质量（行 261）
   - 原文：「从closed month开始往前数24个日历月内，连续六个月非负gross revenue」
   - 问题："连续六个月"是指 24 个月窗口内任意连续 6 个月满足条件即可，还是必须是最近的 6 个月？两种理解会产生不同的有效公司集合。
   - 建议：明确为以下之一：
     - "在 24 个日历月窗口内，存在至少一段连续 6 个月期间 gross revenue ≥ 0"
     - "从 closed month 起向前回溯，最近的 6 个连续月份的 gross revenue 均 ≥ 0"

#### §趋势视图（3 个）

8. **数据缺失展示 P0 可能严重误导用户**
   - 位置：§数据缺失处理（行 342）
   - 原文：「某家公司某个月份无数据，则展示最低点P0」
   - 问题：P0 表示该公司在同行中排名最末。但"无数据"与"表现最差"是完全不同的含义。将无数据展示为 P0 会误导用户认为该公司该月表现极差。
   - 建议：
     - 方案 A：无数据月份折线断开（不画点），Tooltip 显示"No Data"
     - 方案 B：用虚线连接缺失区间，数据点用空心/灰色标记，Tooltip 明确标注"Data Not Available"
     - 无论哪种方案，缺失数据不应参与视觉上的百分位定位

9. **Trend 视图的 Info Icon 交互在 PRD 中未覆盖**
   - 位置：§趋势视图（行 290-349）
   - Asana ticket 原文：「Hover on info icon on the right of the metric name at trend view will see info box explain: How the benchmark is calculated, Any relevant cohort or filtering logic」 以及「Hover on info icon on the right of chart title at trend view will see info box explain absolute values of the selected benchmark」
   - 问题：Asana ticket AC 明确要求 Trend 视图中有两种 Info Icon（指标名称右侧 + 图表标题右侧），但 PRD 趋势视图章节完全未提及 Info Icon 的存在和交互行为。
   - 建议：在趋势视图章节补充 Info Icon 的定义：
     - 指标卡片标题右侧 Info Icon：Hover 展示该指标的计算方法和同行匹配逻辑（不暴露具体公司）
     - 图表标题右侧 Info Icon：Hover 展示该 Benchmark 的绝对值（P25/P50/P75 对应的实际数值）

10. **Trend 视图无数据空状态未定义**
    - 位置：§趋势视图（行 290-349）
    - 问题：Snapshot 视图有空状态定义（行 82-83："To begin select a company"），但 Trend 视图在以下场景均无空状态说明：(1) 选定时间范围内所有公司均无数据；(2) 选定 Benchmark 在选定时间范围内无数据。
    - 建议：补充 Trend 视图的空状态场景和展示文案。

#### §数据格式（1 个）

11. **Snapshot 某月无数据的公司展示行为未定义**
    - 位置：§快照视图（行 195-219）
    - 问题：趋势视图定义了无数据展示 P0（行 342），但 Snapshot 视图当某公司在选定月份完全无指标数据时的展示行为未定义。是显示整行为 N/A？不显示该公司？还是显示空值？
    - 建议：补充 Snapshot 视图中公司无数据时的展示规则。

#### §全局（1 个）

12. **Peer Fallback 提示的 UI 表现未定义**
    - 位置：§同行匹配规则（行 245、261、262）
    - 原文：「显示 Peer Fallback 提示」（出现 3 次）
    - 问题：三处均提到"显示 Peer Fallback 提示"但从未定义：提示出现在哪里（Tooltip？Badge？Toast？）、提示文案是什么、提示是常驻还是可关闭。
    - 建议：定义 Peer Fallback 提示的 UI 规格：位置（建议在 Benchmark 列旁显示标记）、文案（如"Peer data unavailable, showing platform benchmark"）、交互方式。

---

### :blue_circle: 改进建议（共 8 个，可在开发过程中完善）

#### §全局术语与格式（4 个）

1. **"Benchmarkit" vs "Benchmarkit.ai" 名称不一致**
   - 位置：行 41/179/204 使用 "Benchmarkit"，行 346 使用 "Benchmarkit.ai"
   - 建议：全文统一为 "Benchmarkit"（与 Asana ticket 一致），或与产品确认官方名称。

2. **"Gross Morgin" 拼写错误**
   - 位置：§快照视图 - 指标列（行 213）
   - 原文：「Gross Morgin」
   - 建议：修正为 "Gross Margin"。

3. **"列表展示" vs "表格展示" 描述不一致**
   - 位置：§目录（行 16）写 "列表展示"，§快照视图标题（行 195）写 "表格展示"
   - 建议：统一为"表格展示"（与实际展示形式一致）。

4. **"Data" vs "DATA" 大小写不一致**
   - 位置：行 139 使用 "Data"，行 203 使用 "DATA"
   - 建议：全文统一为 "Data"。

#### §外部模块引用（3 个）

5. **"Normalization Tracing 模块"、"Benchmark Entry"、"Peer Group Management"、"Company Settings" 均为外部引用，未提供接口定义或文档链接**
   - 位置：行 146/149/152（Normalization Tracing）、行 170/174/178/271（Benchmark Entry）、行 244（Peer Group Management）、行 251-252（Company Settings）
   - 建议：为每个外部模块引用补充简要说明或文档链接，至少包含：模块名称、可获取的数据字段、API 端点或 Asana ticket 引用。

6. **"closed month" 术语未定义**
   - 位置：行 261
   - 原文：「从closed month开始往前数24个日历月内」
   - 建议：补充"closed month"的定义，如"closed month 指公司在 LG 中已完成月度结账的最后一个月份"。

7. **"benchmark-edition" 概念仅出现一次且未解释**
   - 位置：行 208
   - 原文：「勾选外部基准时，要显示benchmark-edition」
   - 建议：说明 benchmark-edition 指 Benchmark Entry 中的 Edition 字段（如"KeyBanc SaaS Survey — 2024"），并举例。

#### §趋势视图（1 个）

8. **Trend 视图组合数量可达 72 个图表，无上限约束**
   - 位置：§趋势视图（行 290-349）
   - 问题：3 Data × 4 Benchmark = 12 图表/指标 × 6 指标 = 72 个折线图。Asana ticket 提到"up to 12 per metric"表明已意识到此问题，但 PRD 未说明分页、懒加载或性能相关约束。
   - 建议：补充说明最大组合数场景下的展示策略（如默认折叠部分图表、分页加载等）。

---

### 外部任务系统交叉验证（Asana Epic: FI Trends and Benchmarks）

#### 映射关系

| PRD 章节 | 对应 Ticket | 覆盖情况 |
|---------|------------|---------|
| §筛选条件区域 | 1213147557267595 (Create Benchmark Comparison UI - Portfolio Intelligence) | :white_check_mark: 覆盖 |
| §快照视图 - 表格展示 | 1213147557267595 (同上) | :white_check_mark: 覆盖 |
| §趋势视图 - 折线图展示 | 1213147557267595 (同上) | :white_check_mark: 覆盖 |
| §计算逻辑 - 内部同行百分位 | 1211863946919851 (Implement Peer-Relative Percentile Ranking Engine) | :warning: 部分覆盖 |
| §计算逻辑 - 外部基准百分位 | 1212797421602472 (Implement External Industry Percentile Ranking Engine) | :warning: 部分覆盖 |
| §同行匹配规则 | 1211863946919851 (同上) | :warning: 部分覆盖 |
| §外部行业基准数据来源 | 1212797421602471 (Manual Import of Benchmark Data) | :white_check_mark: 覆盖 |
| Trend 视图 Tooltip（图表标题） | 1214056508423455 (Display Absolute Benchmark Values in Trend Chart Tooltips) | :warning: PRD 未覆盖 |
| Trend 视图绝对值分布图 | 1214006226322516 (Portfolio Benchmark Trend View - Absolute Values) | :heavy_minus_sign: 独立新功能，不在本 PRD 范围 |
| Forecast 对标 | 1213480662840596 (Create Benchmark Comparison UI - Forecast) | :heavy_minus_sign: 独立 ticket，PRD 已引用 |

#### PRD 有但 Ticket 未覆盖（功能可能无人开发）

| 需求点 | PRD 位置 | 严重度 | 说明 |
|--------|---------|--------|------|
| ARR 无数据时同行匹配兜底 | §同行匹配属性 第4条 | :yellow_circle: | PRD 定义了 ARR 规模匹配，但未定义公司在选定月份无 ARR 数据时的处理。Asana ticket 也未覆盖此边界 |
| 外部基准数据完全缺失的展示 | §外部行业基准 | :red_circle: | PRD 和 ticket 均未定义 |

#### Ticket 有但 PRD 未写（PRD 不是 single source of truth）

| Ticket | 规则描述 | 严重度 | 说明 |
|--------|---------|--------|------|
| Peer Ranking Engine | 指标排序方向（升序/降序）定义 | :red_circle: | Ticket 明确定义了每个指标的排序方向，PRD 缺失 |
| Peer Ranking Engine | 并列排名处理（Standard Competition Rank）及 UI indication | :red_circle: | Ticket 定义了相同值并列排名规则和全部并列场景，PRD 完全未提及 |
| Peer Ranking Engine | Monthly Runway "NA" 场景的特殊排名规则 | :yellow_circle: | Ticket 定义了 Cash ≥ 0 & Net Burn ≥ 0 → Top Rank，Cash < 0 → Bottom Rank，PRD 未覆盖 |
| Peer Ranking Engine | Sales Efficiency 排除规则（N/A 或 S&M < 5% 总费用） | :yellow_circle: | Ticket 定义了特定条件下排除 Sales Efficiency 计算，PRD 未覆盖 |
| Peer Ranking Engine | Grade Mapping (A/B/C/D/F) 和 Category Score | :yellow_circle: | Ticket 定义了成绩等级映射和按类别计算 Overall Score 的规则，PRD 仅有简单的 Overall score 算术平均 |
| Main UI Ticket | Variance（绝对值和/或百分比差异）展示 | :yellow_circle: | Ticket AC 写"Variance (absolute and/or percentage)?"（带问号），PRD 完全未提及 |
| Main UI Ticket | Responsiveness（桌面/平板/移动端适配） | :blue_circle: | Ticket AC 要求 desktop + tablet + mobile 适配，PRD 无 |
| Main UI Ticket | Trend 视图 Info Icon（指标名称右侧 + 图表标题右侧） | :yellow_circle: | Ticket AC 定义了两种 Info Icon 的 hover 行为，PRD 趋势视图未提及 |
| Tooltip Ticket | 图表标题 Info Icon 展示绝对 Benchmark 值 | :yellow_circle: | 独立 ticket 1214056508423455 定义了完整的 Tooltip 行为，PRD 未覆盖 |

#### PRD 与 Ticket 逻辑矛盾（开发不知道按哪个做）

| 需求点 | PRD 描述 | Ticket 描述 | 影响 |
|--------|---------|------------|------|
| 同行最小有效数量 | < 3 家则回退 | min. 4 companies（Peer Ranking Engine） | :red_circle: 阈值不同，直接影响回退触发条件 |
| 置灰公司状态 | Exit 或 Shut down | Inactive（Main UI Ticket） | :red_circle: 不同的状态集合被置灰 |
| Overall Score 计算 | 所有指标列百分位直接算术平均 | 先按 Category 算均值，再 4 个 Category 算均值（Peer Ranking Engine） | :red_circle: 两种算法结果不同 |
| 公司状态命名 | Exit / Shut down | Exited / Shut Down（Peer Ranking Engine） | :yellow_circle: 术语不一致，需确认哪个是系统实际状态名 |

---

### 追溯性检查清单

#### 无来源的逻辑引用

| 编号 | 位置 | 原文 | 问题 | 建议 |
|------|------|------|------|------|
| L1 | §Data 行 146-152 | 「来自Normalization tracing模块」 | 三种 Data Type 均引用此模块，但未注明 API 端点、数据字段或文档链接 | 补充引用路径或注明"详见 Normalization Tracing 功能文档" |
| L2 | §Benchmark 行 166 | 「同行判断方式在下方同行（Peer）定义和匹配规则」 | 引用了本文后续章节，但 Peer Group Management 功能本身无外部文档链接 | 补充 Peer Group Management 的 Asana ticket 链接 |
| L3 | §Benchmark 行 170/174/178 | 「Benchmark Entry 中输入的 XX 数据」 | 引用了 Benchmark Entry 功能但未定义该功能的数据结构或入口 | 补充 Benchmark Entry 的功能说明链接或 Asana ticket 1212797421602471 |
| L4 | §同行匹配 行 244 | 「Peer Group Management中绑定了同行公司」 | 引用外部功能但未说明绑定数据的结构和有效性判断逻辑 | 补充 Peer Group Management ticket 链接 |
| L5 | §同行匹配 行 251-252 | 「Company Settings中的Type/Stage」 | 引用 Company Settings 但未说明可选值枚举 | 补充 Type 和 Stage 的可选值列表或引用来源 |
| L6 | §同行匹配 行 261 | 「从closed month开始」 | "closed month"概念未在文档内或外部引用中定义 | 定义 closed month 或引用相关功能文档 |

#### 无数据源的字段/查询

| 编号 | 位置 | 字段/描述 | 问题 | 建议 |
|------|------|----------|------|------|
| D1 | §表格列 行 208 | 「benchmark-edition」 | 仅此一处出现，未定义含义，推测对应 Benchmark Entry 中的 Edition 字段 | 定义并举例（如"2024"对应 KeyBanc 2024 年报告版本） |
| D2 | §表格列 行 208 | Tooltip 中「所有百分位及百分位对应的实际值」 | 「所有百分位」指哪些？Internal Peers 的 P0-P100 中哪些？外部基准的 P25/P50/P75？ | 明确列出 Tooltip 中展示的百分位点位列表 |
| D3 | §表格列 行 207 | 「公司名称（包括Logo）」 | Logo 数据来源未说明 | 补充 Logo 取自 Company Settings 或其他来源 |
| D4 | §外部基准 行 273 | 「FY Period」 | Benchmark Entry 字段中列出了 FY Period，但未说明与 PRD 中月度选择器的映射关系（外部基准通常按财年提供，PRD 按月展示） | 说明 FY Period 如何映射到月度视图（是全年统一使用同一基准值，还是其他逻辑） |

---

### 结论

**是否可进入设计阶段**：修复 9 个阻断性问题后可以进入设计

**必须优先修复的 Top 3 问题：**

1. **[阻断 §快照视图] 指标排序方向未定义 + 并列排名规则缺失**（问题 #1 + Ticket 交叉验证）—— 百分位计算是整个功能的核心，排序方向决定了 P0 和 P100 的含义。Asana Peer Ranking Engine ticket 已有完整定义但 PRD 遗漏，不补充则开发无法实现正确的百分位计算。

2. **[阻断 §筛选/§匹配] PRD 与 Asana Ticket 三处逻辑矛盾**（问题 #2、#6 + 矛盾表）—— 同行最小有效数量（3 vs 4）、置灰公司状态（Exit/Shut Down vs Inactive）、Overall Score 计算方式（直接平均 vs 按类别平均）在 PRD 和 Asana ticket 之间存在直接矛盾，不统一则前后端实现会不一致。

3. **[阻断 §快照视图] Snapshot 表格行结构层级不明 + Overall Score 计算范围模糊**（问题 #3、#9）—— 多 Data Type × 多 Benchmark 组合下的表格展示结构和分数计算是 UI 最复杂的部分，定义不清会导致前端反复返工。
