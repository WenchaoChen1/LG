# Portfolio Benchmark Intelligence — 接口对接问题清单

> 生成日期：2026-04-14 | 数据来源：api-documentation.md 对照 Benchmark Portfolio Intelligence_需求文档.md + 前端代码 `src/pages/portfolioCompanies/Benchmarking/`

---

## 与上版文档对比

本次为 Portfolio Benchmark 首次 API 审核，无上版报告。

此前已有 FI (Financial Intelligence) 公司级 Benchmark API 审核（`docs/Benchmark_API_Issues.md`，2026-04-01），部分 FI 级问题在此 Portfolio 级 API 中延续：

| FI 级已知问题 | 在 Portfolio API 中的状态 | 说明 |
|---|---|---|
| EstimationType 枚举映射不完整 | **延续 + 改进** | 新 API 明确拆分为 `BOUNDARY_ABOVE`/`BOUNDARY_BELOW`，FI 旧值 `BOUNDARY` 不再出现 |
| enabled 字段未使用 | **不适用** | Portfolio API 无 filter-options 接口 |

---

## 问题概览

| 问题类型 | 数量 | 是否阻塞开发 |
|---|---|---|
| 接口路径/方法与前端不一致 | 3 | **是** |
| 响应数据结构与前端类型不匹配 | 4 | **是** |
| 枚举值格式不匹配 | 3 | **是** |
| 接口缺失（filter-options） | 1 | **是** |
| 前端缺少字段（tooltipData / peerInfo / hasData） | 3 | **是** |
| Overall Score 接口未返回 | 1 | 否（前端可计算） |
| 默认值与需求不一致 | 1 | 否 |
| categoryId 映射不完整 | 1 | 否 |
| 前端类型字段名与接口不一致 | 5 | 否 |

---

## 一、阻塞性问题

开发前**必须解决**。

### 1.1 接口路径与 HTTP 方法不匹配

| # | 模块 | 问题描述 | 接口定义 | 前端当前实现 | 建议 |
|---|---|---|---|---|---|
| 1 | 公司列表 | 路径和参数不一致 | `GET /web/portfolio-benchmark/companies?portfolioId={id}` | `portfolioBenchmarkService.ts:14` 调用 `GET /api/web/benchmark/portfolio/${companyGroupId}/companies` | 前端改为 API 定义的路径，`portfolioId` 作为 query 参数而非路径参数 |
| 2 | Snapshot 数据 | HTTP 方法不一致（GET vs POST） | `POST /web/portfolio-benchmark/snapshot`，请求体为 JSON | `portfolioBenchmarkService.ts:33-53` 使用 `GET` + query params（逗号拼接） | 前端改为 POST 方法，请求体传 JSON 数组而非逗号拼接字符串 |
| 3 | Trend 数据 | HTTP 方法不一致（GET vs POST）+ 日期参数拆分 | `POST /web/portfolio-benchmark/trend`，请求体含 `startDate` + `endDate` | `portfolioBenchmarkService.ts:57-75` 使用 `GET` + `dateRange` 拼接字符串 | 前端改为 POST，日期拆分为 `startDate` 和 `endDate` 两个字段 |

### 1.2 Snapshot 响应数据结构与前端类型完全不匹配

| # | 模块 | 问题描述 | 接口定义 | 前端当前实现 | 建议 |
|---|---|---|---|---|---|
| 1 | Snapshot 整体 | API 使用嵌套结构 `benchmarkGroups[].dataTypeRows[].metrics{}`，前端期望扁平结构 `metrics[].dimensions[]` | API：`companies[].benchmarkGroups[].dataTypeRows[].metrics{METRIC_KEY: MetricPercentileDto}` | `types.ts:38-74`：`SnapshotCompany.metrics[].dimensions[]` 扁平结构 | **需重写适配层或重构前端类型**。建议编写 `adaptSnapshotResponse()` 函数，将 API 嵌套结构转为前端扁平结构 |
| 2 | Snapshot 分页 | 分页字段路径不同 | API：`data.pagination.{page, size, total}` | `types.ts:78-84`：期望 `data.{companies, totalElements, page, size}` | 适配层中提取 `pagination` 子对象映射到顶层字段 |
| 3 | Snapshot Benchmark 列 | API 无独立 benchmarks 数组 | API：benchmark 信息内嵌于 `benchmarkGroups[]` | `types.ts:55-58`：`SnapshotBenchmarkInfo` 期望独立的 `benchmarks[]` 数组 | 适配层从 `benchmarkGroups[]` 提取 `benchmarkSource` + `edition` 构造 `benchmarks[]` |
| 4 | Snapshot OverallScore | API 未返回此字段 | 无此字段 | `types.ts:60-65`：`SnapshotOverallScore` 期望接口返回 | 前端计算：遍历所有 metrics percentile 求均值（排除 null） |

### 1.3 Trend 响应数据结构与前端类型不匹配

| # | 模块 | 问题描述 | 接口定义 | 前端当前实现 | 建议 |
|---|---|---|---|---|---|
| 1 | Trend 整体 | 字段名不一致 | API：`charts[].companySeries[].dataPoints[]` | `types.ts:102-112`：`combinations[].companies[].monthlyData[]` | 适配层做字段重命名映射 |
| 2 | Trend 数据类型字段 | 字段名不同 | API：`charts[].dataType` | `types.ts:103`：`TrendCombination.dataSource` | 映射 `dataType` → `dataSource` |
| 3 | Trend 分类 | 字段语义不同 | API：`metrics[].categoryId`（如 "cat-revenue-growth"） | `types.ts:109`：`TrendMetric.category`（期望 "Growth"/"Efficiency" 等） | 需建立 categoryId → MetricCategory 映射表 |

### 1.4 枚举值格式不匹配（UPPER_SNAKE_CASE vs PascalCase）

| # | 模块 | 问题描述 | 接口定义 | 前端当前实现 | 建议 |
|---|---|---|---|---|---|
| 1 | DataSource 枚举 | 接口 `ACTUALS`，前端 `Actuals` | `ACTUALS` / `COMMITTED_FORECAST` / `SYSTEM_GENERATED_FORECAST` | 请求参数中直接传 `Actuals` / `CommittedForecast`（`portfolioBenchmarkService.ts:46`） | 请求时：PascalCase → UPPER_SNAKE_CASE；响应时：UPPER_SNAKE_CASE → PascalCase。已有 `dataSourceFromApiString()`（`utils.ts:40`）处理响应，**但缺少请求方向的映射** |
| 2 | BenchmarkSource 枚举 | 接口 `INTERNAL_PEERS`，前端 `InternalPeers` | `INTERNAL_PEERS` / `KEYBANC` / `HIGH_ALPHA` / `BENCHMARK_IT` | 请求参数中直接传 `InternalPeers` / `KeyBanc`（`portfolioBenchmarkService.ts:47`） | **需新增双向映射函数 `benchmarkSourceToApi()` + `benchmarkSourceFromApi()`** |
| 3 | Company Status 枚举 | 类型完全不同：接口 String 枚举 vs 前端 Number | `"ACTIVE"` / `"EXIT"` / `"SHUT_DOWN"` / `"INACTIVE"` | `types.ts:9-16`：`PortfolioCompanyItem.status: number`，mock 用 4/6/7 | **需重写类型**：将 `status` 改为 String 枚举，或编写适配层；`disabled` 可直接用 `!selectable` |

### 1.5 接口缺失 — Filter Options

| # | 模块 | 问题描述 | 接口定义 | 前端当前实现 | 建议 |
|---|---|---|---|---|---|
| 1 | 筛选栏 | API 文档无 Portfolio 级 filter-options 接口 | **缺失** | `portfolioBenchmarkService.ts:19-28` 定义了 `getPortfolioBenchmarkFilterOptions()`，但未实际调用 | 与后端确认：(1) 是否有 filter-options 接口？(2) 若无，前端默认启用所有 Data/Benchmark 选项 |

### 1.6 前端类型缺少关键字段

| # | 模块 | 问题描述 | 接口定义 | 前端当前实现 | 建议 |
|---|---|---|---|---|---|
| 1 | Snapshot Tooltip | 前端类型无 `tooltipData` | API 在 `dataTypeRows[]` 中返回 `tooltipData: Map<String, ReferencePercentileDto[]>`，包含各百分位的参考值 | `types.ts` 中 `SnapshotMetric`/`SnapshotDimension` 均无此字段 | 新增 `tooltipData` 字段到类型定义；在 Snapshot 表格 Benchmark 列的 Tooltip 中展示 |
| 2 | Snapshot PeerInfo | 前端类型无 `peerInfo` | API 在 `benchmarkGroups[]` 中返回 `peerInfo: {peerCount, isFallback, fallbackMessage}` | `types.ts` 中 `SnapshotBenchmarkInfo` 无此字段 | 新增 `peerInfo` 字段；当 `isFallback=true` 时显示回退提示 |
| 3 | Trend hasData | 前端类型无 `hasData` | API `dataPoints[].hasData: boolean`，false 时折线画在 P0 | `types.ts:88-94`：`TrendMonthlyPoint` 无 `hasData` | 新增 `hasData` 字段；`TrendChartCard.tsx:47` 已用 `?? 0` 做兜底，但语义不够精确 |

---

## 二、非阻塞性问题

### 2.1 默认 Benchmark 源与需求不一致

| # | 模块 | 接口字段 | 需求定义 | 前端实际做法 | 影响 |
|---|---|---|---|---|---|
| 1 | 筛选栏 | `benchmarkSources` 默认值 | 需求文档 §5：默认值为 **Internal Peers**；API 默认 `["INTERNAL_PEERS"]` | `usePortfolioBenchmark.ts:33`：`selectedBenchmarkSources: ['KeyBanc']` | 首次加载默认选中 KeyBanc 而非 Internal Peers，与需求不符 |

### 2.2 前端类型字段名与接口不一致

| # | 前端类型 | 位置 | 差异说明 |
|---|---|---|---|
| 1 | `PortfolioCompanyItem.logo` | `types.ts:12` | 接口返回 `companyLogo`，前端字段名 `logo` |
| 2 | `PortfolioCompanyItem.disabled` | `types.ts:15` | 接口返回 `selectable`（boolean），前端用 `disabled`（逻辑取反） |
| 3 | `PortfolioCompanyItem.statusLabel` | `types.ts:14` | 接口未返回 `statusLabel`，需前端从 `status` 枚举映射 |
| 4 | `SnapshotCompany.logo` | `types.ts:68` | 接口返回 `companyLogo`，前端字段名 `logo` |
| 5 | `TrendCombination.dataSource` | `types.ts:103` | 接口返回 `dataType`，前端字段名 `dataSource` |

### 2.3 categoryId 映射不完整

| # | 模块 | 接口字段 | 问题描述 | 前端默认处理 |
|---|---|---|---|---|
| 1 | Trend FILTER | `metrics[].categoryId` | API 文档仅给出 `"cat-revenue-growth"` 一个示例值，缺少 Efficiency/Margins/Capital 的 categoryId | 前端 mock 中使用 "Growth"/"Efficiency"/"Margins"/"Capital" 直接作为 category 值（`mockData.ts:142-149`） |

### 2.4 Trend 响应缺少 months 顶层字段的前端映射

| # | 模块 | 接口字段 | 问题描述 | 前端默认处理 |
|---|---|---|---|---|
| 1 | Trend 折线图 | `data.months[]` | API 在顶层返回 `months[]` 数组（所有图表共用的月份列表），前端类型 `PortfolioTrendResponse` 未定义此字段 | 前端从 `companySeries[].dataPoints[].month` 中提取月份集合（`TrendChartCard.tsx:38-40`），功能等效但冗余 |

### 2.5 Overall Benchmark Score 需前端计算

| # | 模块 | 问题描述 | 需求定义 | 前端默认处理 |
|---|---|---|---|---|
| 1 | Snapshot Overall Score | API 未返回 Overall Benchmark Score | 需求 §快照视图：Overall Score = 该行所有百分位的算术平均值，N/A 不参与 | 前端类型定义了 `SnapshotOverallScore` 但 API 未提供。需在适配层遍历 `benchmarkGroups[].dataTypeRows[].metrics{}` 计算平均百分位 |

---

## 三、接口有返回但 UI 未使用的字段

| # | 接口字段 | 类型 | 说明 | 建议 |
|---|---|---|---|---|
| 1 | `companies[].benchmarkGroups[].peerInfo.peerCount` | Integer | 同行公司数量 | 建议在 Internal Peers 行显示 "(N peers)" 增强用户信任度 |
| 2 | `companies[].benchmarkGroups[].peerInfo.isFallback` | Boolean | 是否回退到全平台基准 | **应使用**：需求提到 "Peer Fallback 提示" |
| 3 | `companies[].benchmarkGroups[].peerInfo.fallbackMessage` | String | 回退提示文案 | 同上 |
| 4 | `metrics{}.value` (Snapshot) | BigDecimal | 指标原始数值 | 可选使用；`formattedValue` 已够展示 |
| 5 | `metrics{}.estimationType` (Snapshot) | String | 估算类型 | `percentileDisplay` 已包含前缀，可选择额外使用 |
| 6 | `dataPoints[].value` (Trend) | BigDecimal | 趋势原始值 | Tooltip 中已使用 `formattedValue`，原始值备用 |
| 7 | `data.months[]` (Trend) | String[] | 顶层月份列表 | 可用于统一 X 轴，当前从数据点提取 |
| 8 | `data.companies[]` (Trend) | List | 顶层公司列表 | 可用于 Legend，当前从 series 提取 |

---

## 四、提问清单（需与后端确认）

| # | 问题 | 关联模块 | 前端默认处理（如无回复） |
|---|---|---|---|
| 1 | Portfolio 级是否有 **filter-options** 接口？若有，路径和响应结构是什么？ | 筛选栏 | 前端默认启用所有 Data/Benchmark 选项，日期范围使用本地计算 |
| 2 | 请求体中 `dataSources` 和 `benchmarkSources` 的枚举值是 **UPPER_SNAKE_CASE** 还是 **PascalCase**？文档示例为 UPPER_SNAKE_CASE，请确认 | Snapshot + Trend 请求 | 前端按 UPPER_SNAKE_CASE 发送（需新增映射） |
| 3 | Trend `categoryId` 的完整枚举值列表是什么？文档仅示例 `"cat-revenue-growth"` | Trend FILTER | 前端 mock 用 "Growth"/"Efficiency" 等直接匹配，需完整映射表 |
| 4 | 公司列表 API-01 的 `portfolioId` 参数是 Portfolio ID 还是 CompanyGroup ID？前端当前使用 `companyGroupId` | Companies 筛选器 | 前端传 `companyGroupId` |
| 5 | Snapshot 是否需要后端返回 **Overall Benchmark Score**？还是确认前端自行计算？ | Snapshot Overall Score | 前端自行计算：所有非 null 百分位的算术平均值，四舍五入 + "%ile" |
| 6 | Trend `dataPoints[].hasData` 为 `false` 时，`percentile` 是返回 `null` 还是 `0`？ | Trend 折线图 | 前端将 `null` 视为 0（画在 P0）。如果 API 已返回 0，则无需额外处理 |
| 7 | API-01 公司列表的 `status` 字段是否包含 `"INACTIVE"` 以外的其他值？如 `"THRIVING"` / `"HEALTHY"` 等活跃子状态？ | Companies 筛选器 | 前端将所有非 `selectable=false` 的状态视为可选 |
| 8 | 外部基准（KeyBanc 等）的 `edition` 字段，是否可能为 null？若某外部基准未配置 edition，前端如何展示？ | Snapshot Benchmark 列 | edition 为 null 时不拼接年份，仅显示基准名 |
| 9 | API 文档提到 `isReverse` 字段（格式化规则表中 Sales Efficiency Ratio 为 true），但 `MetricPercentileDto` 中无此字段。是否在其他接口返回，或前端自行维护？ | Snapshot/Trend 指标 | 前端 `RADAR_METRICS` 配置中写死 reverse 属性 |
| 10 | Trend 接口是否支持分页？当公司数量很多时，折线图数据量可能很大 | Trend 性能 | 前端一次请求所有数据，不分页 |
