# Benchmark 接口文档

> 关联技术设计：[03-technical-design.md](03-technical-design.md)

## 一、数据查询接口

### API-01：GET /benchmark/company/{companyId}/data

#### 请求参数

| 参数 | 位置 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|------|--------|------|
| companyId | path | String | 是 | — | 公司 UUID |
| type | query | String | 否 | SNAPSHOT | 视图类型：SNAPSHOT / TREND |
| date | query | String | 否 | last closed month | yyyy-MM，SNAPSHOT 模式生效 |
| startDate | query | String | 否 | endDate - 5 months | yyyy-MM，TREND 模式生效 |
| endDate | query | String | 否 | last closed month | yyyy-MM，TREND 模式生效 |
| dataSources | query | String[] | 否 | [ACTUALS] | 可选：ACTUALS, COMMITTED_FORECAST, SYSTEM_GENERATED_FORECAST |
| benchmarkSources | query | String[] | 否 | [INTERNAL_PEERS] | 可选：INTERNAL_PEERS, KEYBANC, HIGH_ALPHA, BENCHMARK_IT |

#### 响应结构：BenchmarkDataResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| companyId | String | 公司 ID |
| companyName | String | 公司名称 |
| type | String | SNAPSHOT / TREND |
| months | String[] | 月份列表（SNAPSHOT=1个，TREND=N个） |
| peerGroupInfo | PeerGroupInfoDto | 同行匹配信息 |
| overallScore | OverallScoreDto | 综合评分 |
| categories | CategoryScoreDto[] | 4 个板块评分 |
| radarSummary | RadarSummaryDto | 雷达图数据 |
| dimensionSummary | DimensionSummaryDto[] | Overall 进度条维度点位（最多 12 个） |
| companyArr | BigDecimal | 公司当前 ARR（USD） |
| companyArrSource | String | ARR 来源：NORMALIZATION_ARR / MRR_X12 / NONE |
| companyArrMonth | String | ARR 计算月份 |

#### PeerGroupInfoDto

| 字段 | 类型 | 说明 |
|------|------|------|
| peerCount | Integer | 同行数量 |
| isFallback | Boolean | 是否使用回退（全平台基准） |
| fallbackMessage | String | 回退提示（如 "Peer Fallback: No direct peer group found..."） |
| matchCriteria | Map<String, String> | 匹配维度值（type, stage, accountingMethod, arrTier） |

#### OverallScoreDto

| 字段 | 类型 | 说明 |
|------|------|------|
| percentile | Double | 综合百分位（0-100），null 表示无数据 |
| percentileDisplay | String | 展示格式（如 "51%ile"） |
| quartile | String | TOP_QUARTILE / UPPER_MIDDLE / LOWER_MIDDLE / BOTTOM_QUARTILE |
| metricCount | Integer | 有效指标数 |
| quartileLabel | String | "6 Metrics - Top Quartile" |
| hasEstimatedPercentiles | Boolean | 是否包含估算百分位 |
| estimationMessage | String | 估算提示文案 |
| dimensionPoints | DimensionSummaryDto[] | 进度条上的维度点位 |

#### CategoryScoreDto

| 字段 | 类型 | 说明 |
|------|------|------|
| categoryId | String | cat-revenue-growth / cat-profitability / cat-burn-runway / cat-capital-efficiency |
| categoryName | String | Revenue & Growth / Profitability & Efficiency / Burn & Runway / Capital Efficiency |
| sortOrder | Integer | 排序（1-4） |
| score | Double | 板块百分位（有效指标百分位的算术平均），null=N/A |
| scoreDisplay | String | 展示格式 |
| isEstimated | Boolean | 子指标是否含估算 |
| quartile | String | 四分位归属 |
| dimensionPoints | DimensionSummaryDto[] | 板块维度点位 |
| metrics | MetricPercentileDto[] | 板块下各指标 |

#### MetricPercentileDto

| 字段 | 类型 | 说明 |
|------|------|------|
| metricId | String | met-arr-growth / met-gross-margin / met-net-burn / met-runway / met-rule-40 / met-sales-eff |
| metricName | String | 指标英文名 |
| lgFormula | String | LG 公式文本 |
| hasData | Boolean | 公司是否有该指标数据 |
| isTotalTie | Boolean | 所有同行值完全相同（排除出计分） |
| dimensions | DimensionPercentileDto[] | 各维度（DATA×BENCHMARK）的百分位 |

#### DimensionPercentileDto

| 字段 | 类型 | 说明 |
|------|------|------|
| dataSource | String | ACTUALS / COMMITTED_FORECAST / SYSTEM_GENERATED_FORECAST |
| benchmarkSource | String | INTERNAL_PEERS / KEYBANC / HIGH_ALPHA / BENCHMARK_IT |
| percentile | Double | 百分位（0-100），null=无数据 |
| percentileDisplay | String | "P51" / "~P64" / ">P75" / "<P25" / "NA" |
| estimationType | String | EXACT / INTERPOLATED / BOUNDARY_ABOVE / BOUNDARY_BELOW / MEDIAN_ONLY |
| isTied | Boolean | 内部同行中是否有并列 |
| isTotalTie | Boolean | 全部同行值相同 |
| peerCount | Integer | 有效同行数（仅 INTERNAL_PEERS） |
| isFallback | Boolean | 是否使用回退同行 |
| companyValue | BigDecimal | 公司指标原始值 |
| companyValueFormatted | String | 格式化后的展示值 |
| benchmarkDataMissing | Boolean | 外部基准无数据（仅外部 BENCHMARK） |
| benchmarkValues | ExternalBenchmarkValuesDto | 外部基准值详情（仅外部 BENCHMARK） |
| peerData | PeerMetricValueDto[] | 各同行值（仅 INTERNAL_PEERS） |
| monthlyPoints | MonthPointDto[] | 各月数据点（仅 TREND） |

#### ExternalBenchmarkValuesDto

| 字段 | 类型 | 说明 |
|------|------|------|
| platform | String | 平台名 |
| edition | String | 版本 |
| metricName | String | 外部指标名 |
| definition | String | 外部指标公式 |
| segmentType | String | "ARR" |
| segmentValue | String | ARR 范围 |
| bestGuess | String | 信心标签 |
| p25 | String | P25 值 |
| median | String | P50 值 |
| p75 | String | P75 值 |

#### DimensionSummaryDto

| 字段 | 类型 | 说明 |
|------|------|------|
| dataSource | String | DATA 来源 |
| benchmarkSource | String | BENCHMARK 来源 |
| dimensionLabel | String | "Actuals - Internal Peers" |
| percentile | Double | 该维度所有指标百分位的算术平均 |
| percentileDisplay | String | 展示格式 |
| quartile | String | 四分位归属 |

#### RadarSummaryDto

| 字段 | 类型 | 说明 |
|------|------|------|
| dimensions | RadarDimensionDto[] | 各维度（DATA×BENCHMARK）的雷达数据 |

#### RadarDimensionDto

| 字段 | 类型 | 说明 |
|------|------|------|
| dataSource | String | DATA 来源 |
| benchmarkSource | String | BENCHMARK 来源 |
| dimensionLabel | String | 维度标签 |
| metrics | RadarMetricPointDto[] | 6 个指标轴的百分位 |

#### RadarMetricPointDto

| 字段 | 类型 | 说明 |
|------|------|------|
| metricId | String | 指标 ID |
| metricName | String | 指标名 |
| percentile | Double | 百分位（SNAPSHOT=单月值，TREND=多月均值） |
| percentileDisplay | String | 展示格式 |

#### MonthPointDto

| 字段 | 类型 | 说明 |
|------|------|------|
| month | String | yyyy-MM |
| percentile | Double | 该月百分位 |
| percentileDisplay | String | 展示格式 |
| estimationType | String | 估算类型 |

---

## 二、筛选项接口

### API-02：GET /benchmark/company/{companyId}/filter-options

#### 请求参数

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| companyId | path | String | 是 | 公司 UUID |

#### 响应结构：BenchmarkFilterOptionsResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| availableDataSources | FilterOptionDto[] | 可用 DATA 选项 |
| availableBenchmarkSources | FilterOptionDto[] | 可用 BENCHMARK 选项 |
| defaultDate | String | 默认日期（the last closed month） |
| hasPeerGroup | Boolean | 是否有手动同行组 |
| companyActive | Boolean | 公司是否活跃（非僵尸公司）。false 表示公司已退出/关闭或无 Portfolio 关联 |

#### FilterOptionDto

| 字段 | 类型 | 说明 |
|------|------|------|
| value | String | 枚举值（如 ACTUALS） |
| label | String | 展示名（如 "Actuals"） |
| disabled | Boolean | 是否禁用（如无 Forecast 数据时） |

---

## 三、Benchmark Entry CRUD 接口（已有）

### API-03：GET /benchmark/metrics

返回 `List<BenchmarkCategoryDto>`，按 Category → Metric → Detail 树结构。

### API-04：POST /benchmark/details

请求体 `BenchmarkDetailSaveInput`：platform, edition, metricName, definition, fyPeriod, segmentType, segmentValue, p25, median, p75, dataType, bestGuess, metricId

### API-05：PUT /benchmark/details/{detailId}

请求体 `BenchmarkDetailModifyInput`：同 API-04 字段。

### API-06：DELETE /benchmark/details/{detailId}

无请求体，路径参数 detailId。

### API-07：PUT /benchmark/metrics/{metricId}/formula

请求体 `BenchmarkFormulaInput`：lgFormula (String)

---

## 四、枚举值速查

### DataSourceEnum

| 值 | 展示名 |
|----|--------|
| ACTUALS | Actuals |
| COMMITTED_FORECAST | Committed Forecast |
| SYSTEM_GENERATED_FORECAST | System Generated Forecast |

### BenchmarkSourceEnum

| 值 | 展示名 | 外部平台名 |
|----|--------|-----------|
| INTERNAL_PEERS | Internal Peers | —（计算得出） |
| KEYBANC | KeyBanc | KeyBanc |
| HIGH_ALPHA | High Alpha | High Alpha |
| BENCHMARK_IT | Benchmarkit.ai | Benchmarkit.ai |

### MetricEnum

| 值 | 展示名 | 板块 | isReverse |
|----|--------|------|-----------|
| ARR_GROWTH_RATE | ARR Growth Rate | Revenue & Growth | false |
| GROSS_MARGIN | Gross Margin | Profitability & Efficiency | false |
| MONTHLY_NET_BURN_RATE | Monthly Net Burn Rate | Burn & Runway | false |
| MONTHLY_RUNWAY | Monthly Runway | Burn & Runway | false |
| RULE_OF_40 | Rule of 40 | Capital Efficiency | false |
| SALES_EFFICIENCY_RATIO | Sales Efficiency Ratio | Capital Efficiency | true |

### EstimationTypeEnum

| 值 | 展示前缀 | 说明 |
|----|----------|------|
| EXACT | P | 精确匹配基准点 |
| INTERPOLATED | ~P | 线性插值 |
| BOUNDARY_ABOVE | >P | 超出上界 |
| BOUNDARY_BELOW | <P | 低于下界 |
| MEDIAN_ONLY | >P / <P | 仅有中位数 |

### QuartileEnum

| 值 | 展示名 | 范围 |
|----|--------|------|
| TOP_QUARTILE | Top Quartile | 75 ≤ P ≤ 100 |
| UPPER_MIDDLE | Upper Middle Quartile | 50 ≤ P < 75 |
| LOWER_MIDDLE | Lower Middle Quartile | 25 ≤ P < 50 |
| BOTTOM_QUARTILE | Bottom Quartile | 0 ≤ P < 25 |

### 展示排序

Benchmark 优先：Internal Peers → KeyBanc → High Alpha → Benchmarkit.ai
Data 次之：Actuals → Committed Forecast → System Generated Forecast
