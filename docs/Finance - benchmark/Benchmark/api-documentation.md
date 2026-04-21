# Benchmark 接口文档

> 关联技术设计：[03-technical-design.md](03-technical-design.md)
> 重构说明：[refactor-design.md](refactor-design.md)
> 更新日期：2026-04-16

## 架构概述

重构后的架构：
- **后端**：始终返回全量 12 维度（3 DATA × 4 BENCHMARK）的原始数据，不做百分位计算和聚合
- **前端**：缓存原始数据，切换 DATA/BENCHMARK/FILTER 时纯本地重聚合（零网络请求），仅日期/视图模式变化触发 API 调用
- **前端计算层**：`calc/` 模块负责百分位计算（Nearest Rank、线性插值、Runway 分类）和聚合（Category/Overall/Dimension/Radar）

---

## 一、数据查询接口

### API-01：GET /benchmark/company/{companyId}/data

**后端始终返回全量 12 维度原始值，前端负责所有百分位计算和聚合。**

请求中的 `dataSources` 和 `benchmarkSources` 参数被忽略（兼容保留），后端始终返回全部 3 个 DATA × 4 个 BENCHMARK 的数据。

#### 请求参数

| 参数 | 位置 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|------|--------|------|
| companyId | path | String | 是 | — | 公司 UUID |
| type | query | String | 否 | SNAPSHOT | 视图类型：SNAPSHOT / TREND |
| date | query | String | 否 | last closed month | yyyy-MM，SNAPSHOT 模式生效 |
| startDate | query | String | 否 | endDate - 5 months | yyyy-MM，TREND 模式生效 |
| endDate | query | String | 否 | last closed month | yyyy-MM，TREND 模式生效 |
| dataSources | query | String[] | 否 | — | **已忽略**，后端始终返回全部 3 种 DATA |
| benchmarkSources | query | String[] | 否 | — | **已忽略**，后端始终返回全部 4 种 BENCHMARK |

#### 响应结构：BenchmarkRawDataResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| companyId | String | 公司 ID |
| companyName | String | 公司名称 |
| type | String | SNAPSHOT / TREND |
| months | String[] | 月份列表（yyyy-MM）。SNAPSHOT=1 个月，TREND=N 个月 |
| dataSources | String[] | 固定为 [ACTUALS, COMMITTED_FORECAST, SYSTEM_GENERATED_FORECAST] |
| benchmarkSources | String[] | 固定为 [INTERNAL_PEERS, KEYBANC, HIGH_ALPHA, BENCHMARK_IT] |
| peerGroupInfo | PeerGroupInfoDto | 同行匹配信息（聚合视角） |
| peers | PeerMetaDto[] | 去重后的同行元数据 |
| companyArr | BigDecimal | 公司当前 ARR（USD），用于外部基准 Segment 匹配 |
| companyArrSource | String | NORMALIZATION_ARR / MRR_X12 / NONE |
| companyArrMonth | String | ARR 所在月份 |
| companyMetrics | CompanyMetricValuesDto[] | 公司原始指标值（month × dataSource） |
| peerMetrics | PeerMetricValuesDto[] | 同行原始指标值（month × dataSource × peerId） |
| externalBenchmarks | ExternalBenchmarkEntryDto[] | 外部基准 P25/P50/P75 数据（year × benchmarkSource × metricId） |

#### PeerGroupInfoDto

| 字段 | 类型 | 说明 |
|------|------|------|
| peerCount | Integer | 最大月份的同行数 |
| isFallback | Boolean | 是否任一月份使用回退（全平台基准） |
| fallbackMessage | String | 回退提示文案（isFallback=true 时） |
| matchCriteria | Map<String, String> | 匹配维度值（type, stage, accountingMethod, arrTier） |
| peers | PeerCompanyDto[] | 保留字段（新 API 置为空列表，详细列表见顶层 `peers`） |

#### PeerMetaDto

| 字段 | 类型 | 说明 |
|------|------|------|
| peerId | String | 同行公司 ID |
| peerName | String | 同行公司名称 |

#### CompanyMetricValuesDto

公司在一个 `(month, dataSource)` 上的 6 指标原始值。前端据此计算百分位。

| 字段 | 类型 | 说明 |
|------|------|------|
| month | String | yyyy-MM |
| dataSource | String | ACTUALS / COMMITTED_FORECAST / SYSTEM_GENERATED_FORECAST |
| arrGrowthRate | BigDecimal | ARR 增长率 = (ARR_t - ARR_(t-1)) / ARR_(t-1)（后端预计算，因需前月数据） |
| grossMargin | BigDecimal | 毛利率 |
| monthlyNetBurnRate | BigDecimal | 月度净消耗 = Net Income - Capitalized R&D |
| ruleOf40 | BigDecimal | Rule of 40 |
| salesEfficiencyRatio | BigDecimal | 销售效率比 |
| cash | BigDecimal | 现金（前端 Monthly Runway 分类需要） |

#### PeerMetricValuesDto

同行在一个 `(month, dataSource, peerId)` 上的 6 指标原始值。字段与 `CompanyMetricValuesDto` 相同，额外包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| peerId | String | 同行公司 ID |

#### ExternalBenchmarkEntryDto

按 `(year, benchmarkSource, metricId)` 匹配后的外部基准数据。TREND 跨年时同一 benchmarkSource × metricId 可能有多条（每年一条）。

| 字段 | 类型 | 说明 |
|------|------|------|
| year | String | 年份（从 month 的 yyyy 部分提取） |
| benchmarkSource | String | KEYBANC / HIGH_ALPHA / BENCHMARK_IT |
| metricId | String | 指标 ID（如 `met-gross-margin`） |
| found | Boolean | 是否匹配到外部基准数据 |
| values | ExternalBenchmarkValuesDto | 详细数据（found=false 时为 null） |

#### ExternalBenchmarkValuesDto

| 字段 | 类型 | 说明 |
|------|------|------|
| platform | String | 平台名 |
| edition | String | 版本 |
| metricName | String | 外部指标名 |
| definition | String | 外部指标公式 |
| fyPeriod | String | 财年 |
| segmentType | String | "ARR" |
| segmentValue | String | ARR 区间 |
| p25 | String | P25 值（原始字符串，如 "30%" 或 "0.30"） |
| median | String | P50 中位数 |
| p75 | String | P75 值 |
| dataType | String | Actual / Forecast |
| bestGuess | String | 信心标签 |

**外部基准匹配规则**：
1. 精确年份匹配（`fyPeriod = year`）
2. 平台名称不区分大小写（`equalsIgnoreCase`）
3. ARR Segment 匹配（公司 ARR 落在 segmentValue 区间）→ 无匹配则回退到空 Segment 条目
4. 多条候选时按 edition 择优（优先当年 edition，否则最新）

---

## 二、筛选项接口

### API-02：GET /benchmark/company/{companyId}/filter-options

| 字段 | 类型 | 说明 |
|------|------|------|
| companyId | String | 公司 ID |
| companyActive | Boolean | 公司是否活跃（非僵尸公司：非 Exited/Shut Down 且有 Portfolio 关联） |
| availableDataSources | FilterOptionDto[] | 可用 DATA 选项（含 enabled 标记） |
| availableBenchmarkSources | FilterOptionDto[] | 可用 BENCHMARK 选项 |
| latestActualDate | String | 最后一个有 Actual 数据的月份 |
| latestCommittedForecastDate | String | 最后一个有 Committed Forecast 的月份 |
| latestSystemForecastDate | String | 最后一个有 System Forecast 的月份 |
| earliestDataDate | String | 最早有数据的月份（Trend 日历下限） |
| defaultDate | String | 默认日期（the last closed month） |
| peerGroupInfo | PeerGroupInfoDto | 同行信息 |

#### FilterOptionDto

| 字段 | 类型 | 说明 |
|------|------|------|
| value | String | 枚举值 |
| label | String | 展示名 |
| disabled | Boolean | 是否禁用 |

---

## 三、Benchmark Entry CRUD（不变）

| 编号 | 方法 | 路径 | 说明 |
|------|------|------|------|
| API-03 | GET | `/benchmark/metrics` | 获取 Category → Metric → Detail 树 |
| API-04 | POST | `/benchmark/details` | 新增外部基准 |
| API-05 | PUT | `/benchmark/details/{detailId}` | 修改外部基准 |
| API-06 | DELETE | `/benchmark/details/{detailId}` | 删除外部基准 |
| API-07 | PUT | `/benchmark/metrics/{metricId}/formula` | 更新 LG 公式 |

---

## 四、前端计算层说明

### 数据流

```
API 响应（BenchmarkRawData，全量 12 维度）
    ↓ 缓存在 useBenchmarkData hook 的 state 中
    ↓
前端筛选器变化（DATA / BENCHMARK / FILTER）
    ↓ 只触发 useMemo 重聚合，不触发 API 调用
    ↓
filterRawBySelection(raw, selectedDS, selectedBS)  ← 按选中维度过滤原始数据
    ↓
aggregate({ raw: filtered, selectedCategories })    ← 计算百分位 + 聚合
    ↓
AggregatedView → adaptRawToSnapshotResponse / adaptRawToTrendBundle → 组件渲染
```

### 触发 API 调用的条件（仅 2 种）

| 触发 | 说明 |
|------|------|
| 日期变化 | Snapshot 月份 / Trend 日期范围 |
| 视图切换 | Snapshot ↔ Trend |

### 纯前端重聚合的条件（3 种，零请求）

| 触发 | 说明 |
|------|------|
| DATA 切换 | Actuals / Committed Forecast / System Generated Forecast |
| BENCHMARK 切换 | Internal Peers / KeyBanc / High Alpha / Benchmarkit.ai |
| FILTER 切换 | ALL / GROWTH / EFFICIENCY / MARGINS / CAPITAL |

### 百分位计算（calc/ 模块）

| 算法 | 文件 | 说明 |
|------|------|------|
| Internal Nearest Rank | `calc/percentile.ts` | P = (R-1)/(N-1)×100，Standard Competition Ranking |
| External 线性插值 | `calc/externalPercentile.ts` | Case A-D（按可用基准点分支），反向指标 swap P25↔P75 |
| Monthly Runway 分类 | `calc/runway.ts` | 3 层级（TOP_RANK / CALCULATED / BOTTOM_RANK），TOP→P100, BOTTOM→P0 |
| 聚合 | `calc/aggregate.ts` | Category/Overall/Dimension/Radar，FILTER 影响 Overall 和板块显示 |

### Monthly Runway 分类规则（PRD §5.1.4）

| Cash | Burn | 分类 | 百分位 |
|------|------|------|--------|
| >0 | >0 | TOP_RANK | P100 |
| >0 | =0 | TOP_RANK | P100 |
| =0 | >0 | TOP_RANK | P100 |
| =0 | =0 | TOP_RANK | P100 |
| >0 | <0 | CALCULATED | 按公式排名 |
| =0 | <0 | BOTTOM_RANK | P0 |
| <0 | >0 | BOTTOM_RANK | P0 |
| <0 | =0 | BOTTOM_RANK | P0 |
| <0 | <0 | BOTTOM_RANK | P0 |

TOP_RANK 和 BOTTOM_RANK 直接返回固定百分位，不参与相对排名。仅 CALCULATED 参与位置排名。
分类仅在"非 N/A 月份"（至少 1 个指标有值）中生效。

### 展示排序

**BENCHMARK 优先排序**：先展示一个 Benchmark 对所有选中 Data 的数据，再展示下一个 Benchmark。

```
Internal Peers - Actuals
Internal Peers - Committed Forecast
Internal Peers - System Generated Forecast
KeyBanc - Actuals
KeyBanc - Committed Forecast
KeyBanc - System Generated Forecast
High Alpha - Actuals
...
```

### FILTER 行为

| 区域 | FILTER 影响？ | 说明 |
|------|--------------|------|
| 4 个板块显示/隐藏 | ✅ | `categories[].visible` 派生 |
| Overall Benchmark Score | ✅ | 只聚合 visible 板块的分数 |
| 指标分布条 | ✅ | 前端过滤 |
| Metrics Summary 雷达图 | ✅ | 被过滤指标显示为 0 + 灰色轴名（`filtered: true`） |

### 百分位展示格式

| 类型 | 展示 | 说明 |
|------|------|------|
| EXACT | `P45` | 精确值 |
| INTERPOLATED | `~P64` | 线性插值 |
| BOUNDARY_ABOVE | `>P75` | 固定显示 ">P75"（不是 ">P100"） |
| BOUNDARY_BELOW | `<P25` | 固定显示 "<P25"（不是 "<P0"） |
| MEDIAN_ONLY（>P50） | `>P50` | 仅有中位数且高于 |
| MEDIAN_ONLY（<P50） | `<P50` | 仅有中位数且低于 |

### 数值格式化

| 类型 | 规则 | 示例 |
|------|------|------|
| 百分比 (%) | 整数四舍五入，无小数 | `0.6523` → `"65%"` |
| 金额 (currency) | 保留两位小数 + 千分位逗号 | `-120000.5` → `"$-120,000.50"` |
| 月份 (none) | 整数四舍五入 | `18.7` → `"19"` |

---

## 五、枚举速查

### DataSourceEnum → data_type 映射

| 枚举值 | 显示名 | data_type |
|--------|--------|-----------|
| ACTUALS | Actuals | 0 |
| COMMITTED_FORECAST | Committed Forecast | 1 |
| SYSTEM_GENERATED_FORECAST | System Generated Forecast | 2 |

### BenchmarkSourceEnum

| 枚举值 | 显示名 | 外部平台名 |
|--------|--------|-----------|
| INTERNAL_PEERS | Internal Peers | —（从同行组计算） |
| KEYBANC | KeyBanc | KeyBanc |
| HIGH_ALPHA | High Alpha | High Alpha |
| BENCHMARK_IT | Benchmarkit.ai | Benchmarkit.ai |

### MetricEnum

| metricId | 显示名 | 板块 | isReverse | LG 公式 |
|----------|--------|------|-----------|---------|
| met-arr-growth | ARR Growth Rate | Revenue & Growth | false | (ARR_t - ARR_(t-1)) / ARR_(t-1) |
| met-gross-margin | Gross Margin | Profitability & Efficiency | false | Gross Profit / Gross Revenue * 100% |
| met-net-burn | Monthly Net Burn Rate | Burn & Runway | false | Net Income - Capitalized R&D (Monthly) |
| met-runway | Monthly Runway | Burn & Runway | false | -(Cash / Monthly Net Burn Rate) |
| met-rule-40 | Rule of 40 | Capital Efficiency | false | (Net Profit Margin + MRR YoY Growth Rate) * 100% |
| met-sales-eff | Sales Efficiency Ratio | Capital Efficiency | **true** | (S&M Expenses + S&M Payroll) / New MRR LTM |

### Quartile

| 值 | 展示名 | 范围 |
|----|--------|------|
| TOP_QUARTILE | Top Quartile | 75 ≤ P ≤ 100 |
| UPPER_MIDDLE | Upper Middle Quartile | 50 ≤ P < 75 |
| LOWER_MIDDLE | Lower Middle Quartile | 25 ≤ P < 50 |
| BOTTOM_QUARTILE | Bottom Quartile | 0 ≤ P < 25 |

---

## 六、Tooltip 交互规范（PRD §8.2）

| 触发条件 | 显示内容 | 示例 |
|---------|--------|------|
| 鼠标悬停 Overall Score 进度条点位 | 维度标识 + 百分位值 | "Actuals - Internal Peers\nP52" |
| 鼠标悬停指标分布条 | 指标名 + 维度 + 百分位 + 同行数 + 数值 | "ARR Growth Rate\nActuals - Internal Peers\nPercentile: P45\nPeer Count: 45\nValue: 15%" |
| 鼠标悬停指标名称（info icon） | LG 指标名 + LG 公式 + 各外部平台信息 | LG: ARR Growth Rate\n公式: (ARR_t-ARR_(t-1))/ARR_(t-1)\n---\nKeyBanc - 2025 SaaS\nMetric: ARR Growth\n... |
| 鼠标悬停 Trend 折线点 | 月份 + 所有交集点百分位 | "2026-03\nActuals-Internal: P50\nActuals-KeyBanc: P55" |
| 鼠标悬停雷达图轴 | 指标名 + 各维度百分位 | "Rule of 40\nActuals-Internal Peers: P62\nKeyBanc-Actuals: >P75" |

---

## 七、迁移说明（重构前 → 重构后）

| 原字段（已删除） | 新位置 |
|------------------|--------|
| `overallScore` | 前端 `aggregate(raw, selectedCategories).overallScore` |
| `categories[]` | 前端 `aggregate().categories`（FILTER 影响 visible + Overall 计算） |
| `radarSummary` | 前端 `aggregate().radar`（FILTER 控制 filtered 标记，被过滤指标=0+灰色） |
| `dimensionSummary[]` | 前端 `aggregate().dimensionSummary` |
| `metrics[].dimensions[].percentile` | 前端 `computeInternalPercentile` / `computeRunwayPercentile` / `computeExternalPercentile` |
| `dataSources`/`benchmarkSources` 请求参数 | 已忽略，后端始终返回全量 12 维度 |

完整重构细节见 [refactor-design.md](refactor-design.md)。
