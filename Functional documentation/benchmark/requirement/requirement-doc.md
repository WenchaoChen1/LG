# Benchmark（基准测试）产品需求文档

> 版本：v1.0
> 创建时间：2026-04-08
> 需求来源：features/benchmark/benchmark 原始需求/Benchmark功能完整需求文档.md、features/benchmark/Benchmark company功能需求文档_v2.md、UI 截图 2 张
> 状态：待确认
> 待确认项：5 项（见 §9）

---

## 1. 功能概述

### 1.1 功能目的

Benchmark 是 Looking Glass（LG）系统 Finance 模块中的对标分析功能，帮助用户将公司的核心财务指标与内部同行及第三方基准平台进行百分位排名比较，提供快照对比、趋势分析和综合评分等多维度洞察，支持投资组合管理中的竞争定位和战略决策。

### 1.2 功能范围

**包含：**
- 6 个核心财务指标的百分位排名计算与展示
- Internal Peers（LG 内部同行）百分位排名引擎
- 外部基准平台（KeyBanc、High Alpha、Benchmark.it）百分位推算
- Snapshot（快照）和 Trend（趋势）两种视图
- 综合评分（Overall Score）、板块评分、维度评分的聚合展示
- Metrics Summary 雷达图
- 同行匹配与回退机制

**不包含（本期不做）：**
- 导出报告或截图功能（§9 Q5 待确认）
- Committed Forecast 和 System Generated Forecast 数据类型（当前版本 DATA 筛选仅支持 Actuals，其余置灰不可选；来源：原始需求文档 §3.1「目前仅支持用户选择 Actual」）

### 1.3 相关角色

| 角色 | 与本功能的关系 |
|------|--------------|
| LG 平台用户 | 查看自己公司的 Benchmark 对标数据，使用筛选条件浏览不同视图 |

> ⚠️ 待确认（§9 Q4）：权限模型未定义。所有用户是否都能访问 Benchmark 页面？是否仅能查看自己公司的数据？

---

## 2. 使用场景

| 场景编号 | 角色 | 场景描述 | 期望结果 |
|---------|------|---------|---------|
| S1 | LG 用户 | 进入 Benchmark 页面，查看公司在同行中的综合排名 | 看到 Overall Benchmark Score 百分位和四个板块的分布情况 |
| S2 | LG 用户 | 切换 FILTER 为 GROWTH，专注查看收入增长板块 | 仅显示 Revenue & Growth 板块，其他板块隐藏 |
| S3 | LG 用户 | 选择 BENCHMARK 为 KeyBanc，对比外部基准 | 看到公司指标在 KeyBanc 基准中的百分位排名（基于 P25/P50/P75 插值） |
| S4 | LG 用户 | 切换到 Trend 视图，查看过去 6 个月趋势 | 看到各指标百分位随时间变化的折线图 |
| S5 | LG 用户 | 查看一家新建公司（无历史数据） | 日期默认为当前月，Actuals 不可选，仅显示 Forecast 相关数据（或提示无数据） |
| S6 | LG 用户 | 公司无足够同行（< 4 家） | 系统自动回退到 LG 平台基准，显示 Peer Fallback 提示 |

---

## 3. 功能清单

| 功能点 | 描述 | 优先级 | 备注 |
|--------|------|--------|------|
| 筛选条件区域 | VIEW、FILTER、DATA、BENCHMARK 四组筛选卡片 | P0 | DATA 当前仅 Actuals 可选 |
| 日历选择 | 选择查看月份，影响所有指标数据 | P0 | 默认规则见 §5.1 |
| Overall Benchmark Score Card | 综合百分位评分 + 进度条 + 维度点位 | P0 | |
| Snapshot 视图 | 4 个板块 × 6 个指标的百分位分布条展示 | P0 | |
| Trend 视图 | 4 个板块 × 6 个指标的百分位折线图展示 | P0 | |
| 百分位排名引擎 | Internal Peers 百分位计算 + 外部基准插值/边界推算 | P0 | |
| 同行匹配与回退 | 4 维匹配 + < 4 同行时回退 LG 平台基准 | P0 | |
| Metrics Summary 雷达图 | 6 维雷达图汇总所有指标百分位 | P1 | |
| 板块展开/收起 | 每个板块可展开查看详细指标，可收起仅显示板块级信息 | P1 | |
| Tooltip 交互 | 各种悬停信息展示 | P1 | 规范见 §7.3 |

---

## 4. 业务流程

### 4.1 主流程

```
步骤1：用户进入 Benchmark 页面
  └── 入口：Finance 模块 → Benchmarking Tab
  └── 系统加载默认参数（见 §5.1）

步骤2：系统确定同行并计算百分位
  ├── 数据来源（读取）：
  │   - 目标公司指标值：来自 Normalization Tracing 模块，取选定月份的归一化指标值
  │   - 同行公司指标值：来自 Normalization Tracing 模块，按同行匹配规则（见 §5.2）筛选
  │   - 外部基准数据：来自 Benchmark Entry 模块，用户录入的第三方 P25/P50/P75 数据
  ├── 计算内容：6 个指标各自的百分位（见 §6）
  ├── 聚合：板块分数、维度分数、Overall Score（见 §6.2）
  └── 执行结果：页面渲染完成，用户看到 Overall Score、4 个板块、雷达图

步骤3：用户调整筛选条件
  ├── 切换 VIEW → 页面在 Snapshot / Trend 视图之间切换
  ├── 切换 FILTER → 显示/隐藏对应板块（规则见 §5.1）
  ├── 切换 DATA → 维度数量变化，点位/分布条/折线更新
  ├── 切换 BENCHMARK → 维度数量变化，点位/分布条/折线更新
  └── 选择日历月份 → 所有指标重新查询和计算

步骤4：用户进行数据钻取
  ├── 悬停进度条点位 → 显示该维度的 Tooltip（见 §7.3）
  ├── 展开/收起板块 → 查看/隐藏板块内的详细指标
  ├── 悬停单个指标分布条 → 显示指标 Tooltip
  └── 在 Trend 视图中悬停折线 → 显示月份详情

终态：用户完成分析，离开页面或切换到其他 Tab
```

### 4.2 分支流程

**分支 A：无同行或同行不足**
```
触发条件：同行匹配结果 < 4 家公司（匹配规则见 §5.2）
步骤：
  1. 系统自动将 Internal Peers 切换为 LG 平台基准（定义见 §5.2）
  2. 页面显示 Peer Fallback 提示（文案见 §5.4）
  3. 百分位正常计算并展示
```

**分支 B：新建公司（无历史 Actual 数据）**
```
触发条件：公司在系统中无任何 Actual 数据
步骤：
  1. 日历默认为当前日历月
  2. Actuals 选项置灰不可选
  3. 若当前版本不支持 Forecast → 所有指标显示 N/A
```

---

## 5. 业务规则

### 5.1 筛选与默认值规则

**默认参数（页面初始化时）：**

| 筛选项 | 默认值 | 说明 |
|--------|--------|------|
| VIEW | Snapshot | 快照视图 |
| FILTER | ALL | 显示全部 4 个板块 |
| DATA | Actuals | 当前版本仅支持 Actuals |
| BENCHMARK | Internal Peers | 若无足够同行则自动回退（见 §5.2） |
| 日历月份 | 最后一个有 Actual 数据的月份 | 新建公司则为当前日历月 |

> ⚠️ 待确认（§9 Q1）：原始需求另有一条规则「15 号之前用上上个月，15 号之后用上个月」，与上述规则冲突。当前文档采用「最后一个有 Actual 数据的月份」。

**VIEW 规则：**
- 单选：Snapshot 或 Trend，二选一
- 选中项蓝色点亮（#2196F3）

**FILTER 规则：**
- 选项：ALL、GROWTH、EFFICIENCY、MARGINS、CAPITAL
- 交互模式：ALL 是全选快捷键。选中 ALL 时其他四项自动全部选中；取消 ALL 时其他四项自动全部清空。用户也可在 ALL 选中状态下手动取消个别分类（此时 ALL 自动取消选中）
- 至少保留一项选中（不允许全部取消）
- 选中项蓝色点亮（#2196F3）
- FILTER 与板块对应关系：

| FILTER 选项 | 对应板块 | 包含指标 |
|-------------|---------|---------|
| GROWTH | Revenue & Growth | ARR Growth Rate |
| EFFICIENCY | Profitability & Efficiency | Gross Margin |
| MARGINS | Burn & Runway | Monthly Net Burn Rate、Monthly Runway |
| CAPITAL | Capital Efficiency | Rule of 40、Sales Efficiency Ratio |
| ALL | 所有板块 | 所有 6 个指标 |

**DATA 规则：**
- 选项：Actuals、Committed Forecast、System Generated Forecast
- 当前版本：仅 Actuals 可选，其余两项置灰
- 选中项黄色点亮（#FFC107）
- 多选模式（未来版本启用时）：至少选择一项

**BENCHMARK 规则：**
- 选项：Internal Peers、KeyBanc、High Alpha、Benchmark.it
- 多选模式，至少选择一项
- 选中项黄色点亮（#FFC107）

**日历规则：**
- Snapshot 视图：选择单个月份
- Trend 视图：选择起止月份范围，开始月份和结束月份不能是同一个月；默认范围为从最后一个有 Actual 数据的月份往前 6 个月

**维度定义：**
- 一个「维度」= 一个 DATA 选项 × 一个 BENCHMARK 选项的组合
- 示例：「Actuals - Internal Peers」是一个维度
- 最多 12 个维度（3 DATA × 4 BENCHMARK）
- 当前版本最多 4 个维度（1 DATA × 4 BENCHMARK）

**维度展示排序：**
- 按 BENCHMARK 优先排序：Internal Peers → KeyBanc → High Alpha → Benchmark.it
- 同一 BENCHMARK 内按 DATA 排序：Actuals → Committed Forecast → System Generated Forecast

### 5.2 同行匹配规则

**匹配条件**（必须同时满足以下四个维度）：

| 维度 | 说明 | 备注 |
|------|------|------|
| 公司类型 | 如 SaaS、PaaS 等 | 必须完全匹配 |
| 公司阶段 | 融资阶段，如 Series A、Series B 等 | 必须完全匹配 |
| 会计方法 | 现金制（Cash Basis）或权责发生制（Accrual Basis） | 必填项，必须完全匹配 |
| ARR 规模 | 基于选定月份的 ARR 值，落入以下区间之一 | 左闭右开区间 |

**ARR 规模区间：**

| 区间 | 范围 |
|------|------|
| Tier 1 | [$1, $250K) |
| Tier 2 | [$250K, $1M) |
| Tier 3 | [$1M, $5M) |
| Tier 4 | [$5M, $20M) |
| Tier 5 | [$20M, +∞) |

**排除条件**：以下状态的公司不参与同行计算：
- Exited（已退出）
- Shut Down（已关闭）
- Inactive（不活跃）

**同行回退规则：**

| 条件 | 处理 | UI 提示 |
|------|------|--------|
| 匹配到 ≥ 4 家同行 | 使用该同行组 | Tooltip 中显示 "Peer Count: X" |
| 匹配到 < 4 家同行 | 回退到 LG 平台基准 | 显示 Peer Fallback 提示（见 §5.4） |

**LG 平台基准定义**：所有状态为 Active 的 LG 平台公司，不限公司类型、阶段、ARR 范围，仅排除 Exited / Shut Down / Inactive 状态的公司。

**DATA 类型与同行的关系**（未来版本启用 Forecast 时适用）：
- 系统使用同行公司相同 DATA 类型的数据计算百分位
- 若同行没有该 DATA 类型数据，该同行在该维度下被排除
- 不同维度可能有不同数量的有效同行

### 5.3 外部基准匹配规则

外部基准数据来自 Benchmark Entry 模块，用户录入的第三方数据包含以下字段：Category、LG Metric Name、LG Formula、Platform、Edition、Metric Name、Definition、FY Period、Segment Type、Segment Value、P25、Median、P75、Data Type、Best Guess。

**匹配逻辑**：
- Segment Type 对应数据年份
- Segment Value 对应 ARR 范围
- 匹配时使用目标公司对应年份 + 相同 Segment Value 范围的百分位数据

> ⚠️ 待确认（§9 Q2）：外部基准无匹配年份或 ARR 范围时的回退规则未定义。

### 5.4 边界条件与异常处理

| 场景 | 处理规则 | 展示 |
|------|---------|------|
| 同行不足 4 家 | 回退到 LG 平台基准（见 §5.2） | "Peer Fallback: No direct peer group found for this company. Benchmarking against all active companies in Looking Glass." |
| 新建公司无 Actual 数据 | 日历默认当前月，Actuals 置灰 | Forecast 数据或 N/A |
| 单个指标无数据 | 排除该指标（不计入板块分数，见 §6.2） | 灰色空白进度条，数值显示 N/A |
| 某基准源对某指标无数据 | 该维度下该指标不展示 | 灰色进度条，基准名后加 "(N/A)"，如 "Actual - Internal Peers (N/A)" |
| 整个板块无数据 | 排除该板块（不计入 Overall Score，见 §6.2） | 板块显示 "N/A" |
| 所有同行指标值完全相同 | 分配相同百分位（使用竞争排名） | 不显示百分位，不计入 Metrics Summary 和 Overall Score |
| Trend 视图数据不足 6 个月 | 显示实际有数据的月份 | 无数据月份百分位 = P0，Tooltip 显示 N/A |

---

## 6. 计算公式

### 6.1 指标定义清单

#### 6.1.1 ARR Growth Rate（年度经常性收入增长率）

```
公式：ARR Growth Rate(t) = (ARR(t) - ARR(t-1)) / ARR(t-1)
说明：衡量公司的年度经常性收入增速
```

| 属性 | 值 |
|------|-----|
| 方向 | 正向（数值越高越好） |
| 排序 | **降序**（数值大 → 排名靠前 → 百分位高） |
| 除零处理 | ARR(t-1) = 0 时显示 N/A，不参与百分位计算和汇总 |
| 数据口径 | 选定月份的 ARR 值 vs 上一期 ARR 值（数据来源：Normalization Tracing 模块） |

#### 6.1.2 Gross Margin（毛利率）

```
公式：Gross Margin = (Gross Profit / Gross Revenue) × 100%
说明：衡量公司销售商品后的盈利能力
```

| 属性 | 值 |
|------|-----|
| 方向 | 正向（数值越高越好） |
| 排序 | **降序** |
| 取值范围 | 理论上可为负值（COGS > Revenue 时） |
| 除零处理 | Gross Revenue = 0 时显示 N/A |
| 数据口径 | 选定月份数据（数据来源：Normalization Tracing 模块） |

#### 6.1.3 Monthly Net Burn Rate（月度净现金消耗率）

```
公式：Monthly Net Burn Rate = Net Income - Capitalized R&D (Monthly)
说明：衡量公司每月实际消耗的现金。数值为负表示净亏损（在烧钱），数值为正表示净盈利
```

| 属性 | 值 |
|------|-----|
| 方向 | 反向（数值越小/越负 = 烧钱越多 = 越差） |
| 排序 | **升序**（数值小 → 排名靠前 → 百分位高。即：烧钱少的公司百分位更高） |
| 数据口径 | 选定月份数据（数据来源：Normalization Tracing 模块） |

> 说明：虽然业务上"少烧钱"是好事（反向指标），但排序上使用升序，效果等价于：数值越大（烧钱越少/盈利越多）百分位越低。这里按原始需求「数值小的排名靠前，百分位更高」的定义。

#### 6.1.4 Monthly Runway（现金跑道）

```
公式：Monthly Runway = -(Cash / Monthly Net Burn Rate)
说明：基于现有现金和月度消耗速率，公司还能坚持的月份数
```

| 属性 | 值 |
|------|-----|
| 方向 | 正向（数值越高越好，能撑越久越好） |
| 排序 | **降序** |
| 数据口径 | 选定月份的 Cash 余额和 Monthly Net Burn Rate（数据来源：Normalization Tracing 模块） |

**N/A 处理规则（Monthly Runway 特有）：**

Monthly Runway 在某些 Cash 和 Burn Rate 组合下无法产生有意义的数值，需按以下矩阵处理：

| Cash | Net Burn Rate | 处理 | 排名 | 含义 |
|------|--------------|------|------|------|
| ≥ 0 | ≥ 0 | N/A | Top Rank（100%ile） | 盈利且有现金，无破产风险 |
| < 0 | < 0 | N/A | Bottom Rank（0%ile） | 负现金且持续亏损 |
| 仅一方为负（XOR） | | 正常计算 | 按 Runway 数值与其他公司混排 | 来源：原始需求 §5.1.4 "Calculated Rank" |
| 一方为负，另一方为 0 | | N/A | Bottom Rank（0%ile） | 无法计算有意义的 Runway |
| ≥ 0 | = 0 | N/A | Top Rank（100%ile） | 盈亏平衡且有现金 |

> ⚠️ 待确认（§9 Q3）：Cash < 0 且 Burn > 0（负现金但盈利）的场景，公式结果为正数（恢复期），是否按正常排名处理？

#### 6.1.5 Rule of 40（40 法则）

```
公式：Rule of 40 = (Net Profit Margin + ARR Growth Rate) × 100%
说明：衡量公司增长与盈利的平衡。理想情况下应超过 40%
```

| 属性 | 值 |
|------|-----|
| 方向 | 正向（数值越高越好） |
| 排序 | **降序** |
| 子指标来源 | ARR Growth Rate 定义见 §6.1.1；Net Profit Margin 数据来源：Normalization Tracing 模块 |

> 注：原始需求使用「MRR YoY Growth Rate」术语，本文档统一为「ARR Growth Rate」（二者增长率理论上相同）。若实际为不同计算，需在此补充 MRR YoY Growth Rate 的独立公式。

#### 6.1.6 Sales Efficiency Ratio（销售效率比）

```
公式：Sales Efficiency Ratio = (S&M Expenses + S&M Payroll) / New MRR LTM
说明：每获得 $1 的新 MRR，需要花费多少美元在销售与市场上
```

| 属性 | 值 |
|------|-----|
| 方向 | 反向（数值越低越好，花越少钱获客越好） |
| 排序 | **升序**（数值小 → 排名靠前 → 百分位高） |
| 除零处理 | New MRR LTM = 0 时显示 N/A，不参与百分位计算和汇总 |
| 数据口径 | LTM（Last Twelve Months）数据（数据来源：Normalization Tracing 模块） |

#### 排序方向汇总表

| 指标 | 方向 | 排序 | 业务含义 |
|------|------|------|---------|
| ARR Growth Rate | 正向 | 降序 | 增长快 → 百分位高 |
| Gross Margin | 正向 | 降序 | 利润率高 → 百分位高 |
| Monthly Net Burn Rate | 反向 | 升序 | 烧钱少 → 百分位高 |
| Monthly Runway | 正向 | 降序 | 跑道长 → 百分位高 |
| Rule of 40 | 正向 | 降序 | 得分高 → 百分位高 |
| Sales Efficiency Ratio | 反向 | 升序 | 获客成本低 → 百分位高 |

### 6.2 百分位计算方法

#### 6.2.1 Internal Peers 百分位（Nearest Rank Percentile Method）

**步骤 1：排序**
- 按 §6.1 各指标的排序方向（升序/降序）对同行公司的指标值排序

**步骤 2：竞争排名（Standard Competition Ranking）**
- 相同数值的公司分配相同排名
- 下一个不同数值的公司排名 = 上一排名 + 相同数值公司数

**步骤 3：百分位公式**
```
P_target = ((R - 1) / (N - 1)) × 100%

其中：
  P_target = 目标公司的百分位排名
  R = 目标公司在排序后的排名
  N = 参与计算的同行公司总数（含目标公司）
```

**特殊情况：**

| 场景 | 处理 |
|------|------|
| N = 1（仅目标公司） | 百分位 = 100 |
| 多家公司指标值相同 | 使用竞争排名，分配相同百分位 |
| 所有同行指标值完全相同 | 不显示百分位，不计入 Metrics Summary 和 Overall Score |

#### 6.2.2 外部基准百分位（基于 P25/P50/P75 推算）

外部基准通常仅提供 P25、P50（Median）、P75 三个分位数据点。系统根据目标公司指标值与这三个点的关系推算百分位。

**情况 1：精确匹配**
- 指标值恰好等于某数据点 → 显示该精确百分位（如 P50）

**情况 2：区间内插值**
- 指标值落在两个相邻数据点之间 → 线性插值
- 公式：`~P = P_low + (P_high - P_low) × (d - d_low) / (d_high - d_low)`
- 示例：P50 = 30%, P75 = 40%, d = 35% → ~P = 50 + (75-50) × (35-30) / (40-30) = 62.5
- 显示形式：**~P63**（波浪线表示估算值）
- 汇总提示："Includes estimated percentiles (interpolated values used)"

**情况 3：超出范围**
- 指标值超出已知数据点范围 → 使用阶梯式边界值

| 指标值位置 | 展示 | 汇总计算用值 |
|-----------|------|------------|
| < P25 数据点 | <P25 | P0 |
| P25 ~ P50 之间 | ~Pxx（插值） | 插值结果 |
| P50 ~ P75 之间 | ~Pxx（插值） | 插值结果 |
| > P75 数据点 | >P75 | P100 |

- 汇总提示："Includes estimated percentiles (boundary values used)"
- 若同时存在插值和超范围："Includes estimated percentiles (interpolated values used & boundary values used)"

**情况 4：仅有 P50（Median）**
- 指标值高于 P50 → 汇总使用 P75
- 指标值低于 P50 → 汇总使用 P25
- 指标值等于 P50 → 汇总使用 P50

### 6.3 聚合计算

#### 板块分数（Category Score）

```
板块分数 = 该板块所有有效指标百分位的算术平均

示例：
  Burn & Runway 板块：
    Monthly Net Burn Rate: P55
    Monthly Runway: P45
  板块分数 = (55 + 45) / 2 = P50
```

- 若某指标无数据，该指标排除，分母减 1
- 若板块内所有指标均无数据，板块分数 = N/A

#### 维度分数（Dimension Score）

```
维度分数 = 该维度（DATA × BENCHMARK）下所有指标百分位的算术平均

示例：
  维度 "Actuals - Internal Peers"：
    ARR Growth Rate: P50, Gross Margin: P55, Net Burn Rate: P60,
    Monthly Runway: P65, Rule of 40: P45, Sales Efficiency: P40
  维度分数 = (50+55+60+65+45+40) / 6 = P52.5
```

- 用途：Overall Score 进度条上的点位表示各维度分数

#### Overall Score（总体分数）

```
Overall Score = 四个板块分数的算术平均

公式：
  Overall = (Revenue & Growth + Profitability & Efficiency
           + Burn & Runway + Capital Efficiency) / 4
```

- 若某板块分数 = N/A，该板块排除，分母减 1

> ⚠️ 待确认（§9 Q3-补充）：当选中多个维度时，板块分数和 Overall Score 是按默认维度（Actuals - Internal Peers）计算，还是跨所有维度取平均？当前文档假设为按默认维度计算。

---

## 7. 数据展示逻辑

### 7.1 颜色编码规范

**百分位等级（用于进度条和分布条着色）：**

| 百分位范围 | 等级名称 | 颜色 |
|-----------|---------|------|
| 0 ≤ n < 25 | Bottom Quartile | 红色 #FF4444 |
| 25 ≤ n < 50 | Lower Middle Quartile | 粉色 #FF88BB |
| 50 ≤ n < 75 | Upper Middle Quartile | 黄色 #FFBB44 |
| 75 ≤ n ≤ 100 | Top Quartile | 绿色 #44BB44 |
| N/A | 无数据 | 灰色 #CCCCCC |

**筛选项选中状态：**

| 筛选组 | 选中颜色 |
|--------|---------|
| VIEW、FILTER | 蓝色 #2196F3 |
| DATA、BENCHMARK | 黄色 #FFC107 |

### 7.2 Overall Score Card 展示

| 元素 | 数据来源 | 展示格式 | 说明 |
|------|---------|---------|------|
| 百分位数值 | §6.3 Overall Score 计算结果 | **XX%ile** 或 **~XX%ile** | 四个板块分数的算术平均 |
| 进度条 | Overall Score 值 | 0-100% 水平条，着色规则见 §7.1 | 长度占卡片宽度约 2/3 |
| 维度点位 | §6.3 各维度分数 | 进度条上的标记点，最多 12 个 | 颜色见 UI 图例，排序见 §5.1 |
| 右上角标签 | Overall Score 所属等级 + 有效指标数 | "X - Top Quartile" 等 | X = 有效指标数量 |
| 特殊计算提示 | 是否使用了插值或边界值 | "Includes estimated percentiles (...)" | 仅在存在估算时显示 |

**维度点位重合处理**：若多个点位百分位完全相同，打包展示。点位显示采用排序最前的维度的颜色和形状（排序见 §5.1 维度展示排序），悬停时打包展示所有重合维度信息。

### 7.3 Tooltip 交互规范

| 触发位置 | 显示内容 | 示例 |
|---------|---------|------|
| Overall Score 进度条点位 | 第一行：维度标识；第二行：百分位值 | "Actuals - Internal Peers / P52" |
| 指标名称（悬停） | 指标内容、标签（Guess/Exact）、指标公式、Segment、Source | 详见下方说明 |
| 指标分布条（悬停） | 指标名称、数据类型、基准来源、百分位值、同行规模、具体数值 | "ARR Growth Rate / Actuals - Internal Peers / P45 / Peer Count: 45" |
| Trend 折线某月份 | 竖向网格线 + 该月份所有 DATA-BENCHMARK 组合的百分位值 | "2026-03 / Actuals-Internal: P50 / Actuals-KeyBanc: P55" |
| Trend 折线点 | 高亮该线，显示该点详细信息 | |
| 雷达图指标轴线 | 该指标所有 DATA-BENCHMARK 组合的百分位详情 | "Rule of 40 / Actuals-Internal Peers: P62" |

**指标名称 Tooltip 说明**：
- Guess/Exact 标签：标识该指标百分位是精确匹配（Exact）还是估算值（Guess，包括插值和边界值）
- Segment：该指标对应的 ARR 范围区间
- Source：数据来源（Internal Peers / KeyBanc / High Alpha / Benchmark.it）

### 7.4 Snapshot 视图展示

**板块结构（4 个固定板块，排列见 §5.1 FILTER 对应关系）：**

每个板块包含：
1. **板块标题行**：板块名称（加粗）+ 板块百分位排名（右对齐）+ 板块进度条（着色规则见 §7.1）
2. **板块进度条**：仅显示该板块的平均百分位，不显示维度点位
3. **指标列表**：每个指标一行，包含指标名称 + 分布条 + 百分位数值

**板块展开/收起规则：**
- 默认：板块卡片展开，板块内指标收起
- 板块展开状态：显示板块名称、百分位、进度条 + 每个指标默认展示一条 DATA-BENCHMARK 分布条
- 若一个指标存在多条分布条，显示 "Show All" 按钮，点击展示所有分布条，按钮变为 "Hide"
- 板块收起状态：仅显示板块名称、百分位和进度条

**百分位数值展示格式：**
- 精确百分位：P45
- 估算百分位：~P64（使用了线性插值）
- 超范围：>P75 或 <P25

**无数据展示：**
- 指标无数据：灰色空白进度条，数值显示 "N/A"
- 基准无数据：灰色空白进度条，进度条名称后加 "(N/A)"
- 板块全无数据：显示 "N/A"

### 7.5 Trend 视图展示

**板块结构**：同 Snapshot，仍为 4 个板块

**折线图展示（每个板块下每个指标一张折线图）：**

| 属性 | 说明 |
|------|------|
| 横坐标 | 月份（用户选定的时间范围内有数据的月份） |
| 纵坐标 | 百分位排名（0-100%ile） |
| 线条数 | 根据选中的 DATA × BENCHMARK，最多 12 条 |
| 线条颜色 | 与 Snapshot 中的颜色编码一致（按维度区分） |
| 切换选项 | Percentile / Amount（默认 Percentile；Amount 模式下纵坐标按实际值划分） |

### 7.6 Metrics Summary 雷达图

**位置**：页面底部（Snapshot 和 Trend 视图中都显示）

**结构：**
- 固定六边形雷达图，6 个角度分别对应 6 个指标
- 中心点：0%（最低百分位）
- 同心圆：25%、50%、75%、100%
- 线条数：根据选中的 DATA × BENCHMARK，最多 12 条
- 附图例，用户可控制各线条的显隐

**计算方式：**

- **Snapshot 模式**（单月数据）：每个角的值 = 该指标在选定月份下、所有选中 DATA-BENCHMARK 组合百分位的算术平均（来源：原始需求 §4.3「该指标在该月所有 data-benchmark 组合百分位的算术平均」）
- **Trend 模式**（多月数据，两步平均）：
  1. 先算每月平均：该指标在该月所有 DATA-BENCHMARK 组合百分位的算术平均
  2. 再算月份平均：所有月度平均值的算术平均

---

## 8. 页面层级说明

### 8.1 页面总览

```
Finance 模块 → Benchmarking Tab
  └── 页面：Benchmark 主页        # 唯一页面，包含筛选、评分、板块、雷达图
```

### 8.2 页面详情

#### 页面：Benchmark 主页

**路由**：Finance → Benchmarking Tab
**职责**：展示公司财务指标的对标分析结果，支持用户通过筛选条件切换视图和维度，查看百分位排名
**访问角色**：LG 平台用户（⚠️ 权限待确认，见 §9 Q4）
**布局来源**：截图（ScreenShot_2026-03-24_185710_771.png、ScreenShot_2026-03-24_185728_030.png）

**页面布局：**

```
┌─────────────────────────────────────────────────────────────────┐
│  Finance ▸ Overview │ Financial Statements │ Performance │ [Benchmarking] │  ← Tab 导航
├─────────────────────────────────────────────────────────────────┤
│  Benchmarking                                                    │
│  "Benchmark values are normalized for comparability..."          │  ← 标题 + 说明文字
├──────────┬──────────┬─────────────┬──────────────┬─────────────┤
│  VIEW    │  FILTER  │    DATA     │  BENCHMARK   │  📅 日历    │  ← 筛选条件区域
│ [Snap]   │ [ALL]    │ [Actuals]   │ [Int.Peers]  │  [Month]    │
│ [Trend]  │ [GRO]... │ [CF] [SGF]  │ [KB][HA][B]  │             │
├──────────┴──────────┴─────────────┴──────────────┴─────────────┤
│  Overall Benchmark Score    [6 Metrics - Top Quartile]          │
│  ~67P  ████████████████████████░░░░░░░░░  ●  ●  ●              │  ← Overall Score Card
│         0%                              100%                     │
├────────────────────────────────┬────────────────────────────────┤
│  Revenue & Growth    ~51%     │  Profitability & Efficiency ~25%│
│  ████████████░░░░░░░░░░░      │  ████░░░░░░░░░░░░░░░░░░       │  ← 板块区域
│  ▸ ARR Growth Rate    P45     │  ▸ Gross Margin         P25    │    （2×2 网格）
├────────────────────────────────┼────────────────────────────────┤
│  Burn & Runway       ~89%     │  Capital Efficiency     ~10%   │
│  ██████████████████████░░     │  ██░░░░░░░░░░░░░░░░░░░░       │
│  ▸ Monthly Net Burn Rate P82  │  ▸ Rule of 40           P15    │
│  ▸ Monthly Runway        P96  │  ▸ Sales Efficiency     P5     │
├────────────────────────────────┴────────────────────────────────┤
│  Metrics Summary（雷达图）                                       │
│            ARR Growth Rate                                       │
│               ╱    ╲                                             │
│     Sales Eff/      \Gross Margin                                │
│              \      /                                            │
│     Rule of 40╲  ╱Monthly Runway                                │
│           Monthly Net Burn Rate                                  │  ← 雷达图区域
└─────────────────────────────────────────────────────────────────┘
```

**页面模块（从上到下）：**

| 模块名称 | 模块类型 | 功能描述 |
|---------|---------|---------|
| Tab 导航 | 全局导航 | Finance 模块内的 Tab 切换（Overview / Financial Statements / Performance / Benchmarking） |
| 标题 + 说明 | 信息展示 | 页面标题 "Benchmarking" + 免责说明文字 |
| 筛选条件区域 | 筛选区 | 4 组筛选卡片 + 日历选择器，交互规则见 §5.1 |
| Overall Score Card | 汇总展示 | 综合百分位 + 进度条 + 维度点位 + 等级标签，展示规则见 §7.2 |
| 板块区域（Snapshot 视图） | 数据展示 | 4 个板块卡片，每个含板块级进度条 + 指标级分布条，展示规则见 §7.4 |
| 板块区域（Trend 视图） | 数据展示 | 4 个板块卡片，每个含折线图，展示规则见 §7.5 |
| Metrics Summary 雷达图 | 汇总展示 | 6 维雷达图，计算规则见 §7.6 |

**操作入口：**

| 触发操作 | 触发位置 | 目标 | 说明 |
|---------|---------|------|------|
| 切换 VIEW | 筛选区 VIEW 卡片 | 同页切换 Snapshot / Trend 视图 | 板块区域内容变化（分布条 ↔ 折线图） |
| 切换 FILTER | 筛选区 FILTER 卡片 | 同页显示/隐藏板块 | 规则见 §5.1 |
| 切换 DATA / BENCHMARK | 筛选区对应卡片 | 同页刷新维度 | 点位/分布条/折线数量变化 |
| 选择月份 | 日历选择器 | 同页重新计算 | 所有指标数据刷新 |
| 展开/收起板块 | 板块标题行 | 同页展开/收起 | 规则见 §7.4 |
| 悬停 | 进度条点位/分布条/折线/雷达轴 | Tooltip 浮层 | 内容见 §7.3 |

---

## 9. 待确认问题

| 编号 | 问题描述 | 影响范围 | 当前假设 | 状态 |
|------|---------|---------|---------|------|
| Q1 | 默认月份：原始需求另有「15 号之前用上上个月，15 号之后用上个月」的规则，与「最后一个有 Actual 数据的月份」冲突。 | §5.1 日历默认值 | 采用「最后一个有 Actual 数据的月份」 | 待确认 |
| Q2 | 外部基准无匹配年份或 ARR 范围时如何处理？ | §5.3 外部基准匹配 | 未定义回退规则（建议：该基准源该指标显示 N/A） | 待确认 |
| Q3 | Monthly Runway：Cash < 0 且 Burn > 0（负现金但盈利中）是否按公式正常计算？多维度时 Overall Score 用哪个维度？ | §6.1.4、§6.3 | Runway 按正常计算；Overall Score 按默认维度 | 待确认 |
| Q4 | 权限模型：所有用户都能访问 Benchmark 页面吗？用户只能看自己公司数据？ | §1.3 角色 | 所有 LG 用户可访问，仅能查看自己公司数据 | 待确认 |
| Q5 | 导出功能是否纳入当前版本？如果纳入，导出格式和内容范围？ | §1.2 范围 | 不纳入当前版本 | 待确认 |
