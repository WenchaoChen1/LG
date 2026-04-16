# Portfolio Benchmark Intelligence — 接口字段对接映射表

> 生成日期：2026-04-14 | 数据来源：api-documentation.md（3 个接口）
> 对照：Benchmark Portfolio Intelligence_需求文档.md + 前端代码 `src/pages/portfolioCompanies/Benchmarking/`

---

## 接口范围确认

| 接口 | 路径 | 方法 | 用途 |
|---|---|---|---|
| API-01 公司列表 | `GET /web/portfolio-benchmark/companies?portfolioId={id}` | GET | Companies 筛选器下拉列表 |
| API-02 Snapshot 数据 | `POST /web/portfolio-benchmark/snapshot` | POST | Snapshot 视图表格数据 |
| API-03 Trend 数据 | `POST /web/portfolio-benchmark/trend` | POST | Trend 视图折线图数据 |

---

## 映射概览

| 页面模块 | 对应接口 | 字段覆盖率 | 问题数 |
|---|---|---|---|
| Companies 筛选器 | API-01 | 4/6 (67%) | 3 |
| 筛选栏 FilterBar | 无对应接口 | 0/8 (0%) | 1 |
| Snapshot - 公司行 | API-02 | 4/5 (80%) | 1 |
| Snapshot - Benchmark 列 | API-02 | 3/4 (75%) | 2 |
| Snapshot - Overall Score 列 | API-02 | 0/4 (0%) | 1 |
| Snapshot - 指标列（x6） | API-02 | 5/5 (100%) | 1 |
| Snapshot - Tooltip | API-02 | 4/4 (100%) | 1 |
| Snapshot - 分页 | API-02 | 3/3 (100%) | 1 |
| Trend - 指标卡片 | API-03 | 3/4 (75%) | 1 |
| Trend - 折线图 | API-03 | 5/6 (83%) | 1 |
| Trend - 数据点 | API-03 | 5/6 (83%) | 1 |

> 覆盖率 = UI 需要的字段中 API 已提供的数量 / UI 总需要的字段数

---

## 模块 1：Companies 筛选器

**对应接口**：`GET /web/portfolio-benchmark/companies?portfolioId={id}`

### 请求参数映射

| UI 控件 | 控件类型 | 请求参数 | 参数类型 | 是否必填 | 说明 |
|---|---|---|---|---|---|
| 当前 Portfolio | 路径上下文 | `portfolioId` | String | 是 | 当前所在 Portfolio 的 ID |

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| 下拉项 - 公司名 | 公司名称 | `.data[].companyName` | String | 直接使用 | — |
| 下拉项 - Logo | 公司 Logo | `.data[].companyLogo` | String\|null | null 时使用默认图标 | **前端类型定义为 `logo`，接口为 `companyLogo`，需做字段映射** |
| 下拉项 - 禁用状态 | Exit/Shut Down 置灰不可选 | `.data[].selectable` | Boolean | `!selectable` → `disabled` | **前端类型用 `disabled: boolean`，接口用 `selectable: boolean`，逻辑取反** |
| 下拉项 - 状态标签 | 状态显示文案如 "(Exited)" | `.data[].status` | String 枚举 | 需映射为中文/展示文案 | **前端类型 `status: number` + `statusLabel: string`，接口为 `status: String` 枚举("ACTIVE"/"EXIT"/"SHUT_DOWN"/"INACTIVE")** |
| **（缺失）** | 公司 ID | `.data[].companyId` | String | 直接使用 | 前端用于选中状态标识 |
| **（未使用）** | 公司状态原始值 | `.data[].status` | String | **前端未直接读取** | 前端用 `disabled` boolean 代替 |

---

## 模块 2：筛选栏 FilterBar

**对应接口**：**无** — API 文档未提供 Portfolio 级 filter-options 接口

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| VIEW 切换 | Snapshot / Trend | — | — | 前端本地状态 | 不来自接口 |
| FILTER 标签 | All/Growth/Efficiency/Margins/Capital | — | — | 前端写死常量 | 不来自接口 |
| DATA 标签 | Actuals / Committed Forecast / System Generated Forecast | 无接口 | — | **前端写死** | 前端 `portfolioBenchmarkService.ts` 未调用 filter-options；但代码中定义了 `getPortfolioBenchmarkFilterOptions()` 和 `PortfolioFilterOptionsResponse` 类型 |
| BENCHMARK 标签 | Internal Peers / KeyBanc / High Alpha / Benchmarkit | 无接口 | — | **前端写死** | 同上 |
| 日期选择器 - Snapshot | 单月选择，默认当前月 | 无接口 | — | 前端本地计算默认月 | API 文档无 latestActualDate 等信息 |
| 日期选择器 - Trend | 月份范围，默认 6 个月 | 无接口 | — | 前端本地计算默认范围 | 同上 |
| DATA 按钮可用状态 | 根据公司数据可用性控制 | 无接口 | — | **前端全部启用** | 需求无此限制也可接受 |
| BENCHMARK 按钮可用状态 | 根据基准数据有无控制 | 无接口 | — | **前端全部启用** | 同上 |

---

## 模块 3：Snapshot - 公司行基础信息

**对应接口**：`POST /web/portfolio-benchmark/snapshot`

### 请求参数映射

| UI 控件 | 控件类型 | 请求参数 | 参数类型 | 是否必填 | 说明 |
|---|---|---|---|---|---|
| Companies 筛选 | 多选 | `companyIds` | List\<String\> | 是 | 选中的公司 ID 列表 |
| 日期选择器 | 单月 | `date` | String (yyyy-MM) | 否 | 默认当前月份 |
| DATA 标签 | 多选 | `dataSources` | List\<String\> | 否 | **枚举值需要转换** |
| BENCHMARK 标签 | 多选 | `benchmarkSources` | List\<String\> | 否 | **枚举值需要转换** |
| 分页 | 分页器 | `page` / `size` | Integer | 否 | 从 1 开始 |

### 响应字段映射 — 公司基础行

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| 第一列 - 公司名 | 公司名称 | `.data.companies[].companyName` | String | 直接使用 | — |
| 第一列 - Logo | 公司 Logo | `.data.companies[].companyLogo` | String\|null | null 时使用默认图标 | **前端类型 `SnapshotCompany.logo`，接口 `companyLogo`** |
| 第一列 - ID | 行标识 | `.data.companies[].companyId` | String | 作为 rowKey | — |
| **（缺失）** | 公司在同行中的排名 | 无 | — | — | 需求中有"Overall Benchmark Score"需要所有百分位均值，接口未直接返回 |

---

## 模块 4：Snapshot - Benchmark 列

**对应接口**：`POST /web/portfolio-benchmark/snapshot`

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| Benchmark 行 - 基准名 | "Internal Peers" / "KeyBanc - 2025" | `.data.companies[].benchmarkGroups[].benchmarkSource` + `.edition` | String | 需拼接：外部基准追加 `" - " + edition` | **前端类型 `SnapshotBenchmarkInfo.benchmarkLabel` 期望已拼接好的文案，接口需前端自行拼接** |
| Benchmark 行 - 版本 | edition 年份 | `.data.companies[].benchmarkGroups[].edition` | String\|null | Internal Peers 为 null | 外部基准显示如 "2025" |
| Benchmark Tooltip | 各百分位参考值 | `.data.companies[].benchmarkGroups[].dataTypeRows[].tooltipData` | Map\<String, List\<ReferencePercentileDto\>\> | 需按指标聚合展示 | **前端类型无 tooltipData 字段，需新增** |
| Peer Info 回退提示 | "Peer Fallback" 提示 | `.data.companies[].benchmarkGroups[].peerInfo.fallbackMessage` | String\|null | isFallback=true 时展示 | **前端类型无 peerInfo 字段，需新增** |

---

## 模块 5：Snapshot - Overall Benchmark Score 列

**对应接口**：`POST /web/portfolio-benchmark/snapshot`（需前端计算）

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| Overall Score 值 | "35%ile" | **API 未返回此字段** | — | **需前端计算**：遍历该行所有 `metrics{}.percentile`，排除 null / "N/A"，求算术平均值，四舍五入取整 + "%ile" 后缀 | 前端类型 `SnapshotOverallScore` 期望接口返回，但实际需自行计算 |
| Overall Score 颜色 | 按 DATA 类型区分颜色 | — | — | Actuals=黑色，Committed/System=紫色 | 前端已有 `getDataSourceTextColor()` |
| Overall Score 每行 | 每个 DATA × BENCHMARK 组合一行 | — | — | 需遍历 `benchmarkGroups[].dataTypeRows[]` 聚合 | — |
| System Forecast 标记 | 剪刀图标 | — | — | `isSystemGeneratedForecast()` | — |

---

## 模块 6：Snapshot - 指标列（6 列）

**对应接口**：`POST /web/portfolio-benchmark/snapshot`

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| 百分位 | "P56" / "~P63" / ">P75" | `.benchmarkGroups[].dataTypeRows[].metrics{METRIC_KEY}.percentileDisplay` | String | 直接使用 | API 已格式化 |
| 实际值 | "35.00%" / "-$50,000.00" | `.benchmarkGroups[].dataTypeRows[].metrics{METRIC_KEY}.formattedValue` | String | 直接使用 | API 已格式化 |
| 估算类型 | 影响百分位前缀展示 | `.benchmarkGroups[].dataTypeRows[].metrics{METRIC_KEY}.estimationType` | String 枚举 | 前端已通过 `percentileDisplay` 体现 | **API 新增了 BOUNDARY_ABOVE / BOUNDARY_BELOW** |
| 数据类型 | 区分 Actuals / Forecast | `.benchmarkGroups[].dataTypeRows[].dataType` | String 枚举 | 控制文字颜色 | **枚举值为 UPPER_SNAKE_CASE，前端为 PascalCase** |
| N/A 状态 | 无数据时显示 "N/A" | `value=null, percentileDisplay="N/A"` | — | 直接使用 formattedValue | — |

### 指标 Key 映射

| UI 列名 | 接口 metrics{} Key | 前端 metricNameToKey() |
|---|---|---|
| ARR Growth Rate | `ARR_GROWTH_RATE` | `arrGrowthRate` |
| Gross Margin | `GROSS_MARGIN` | `grossMargin` |
| Monthly Net Burn Rate | `MONTHLY_NET_BURN_RATE` | `monthlyNetBurnRate` |
| Monthly Runway | `MONTHLY_RUNWAY` | `monthlyRunway` |
| Rule of 40 | `RULE_OF_40` | `ruleOf40` |
| Sales Efficiency Ratio | `SALES_EFFICIENCY_RATIO` | `salesEfficiencyRatio` |

> 注意：接口用 UPPER_SNAKE_CASE 作为 Map key，前端 `SnapshotMetric.metricName` 用的是展示名（如 "ARR Growth Rate"），需要在适配层做映射。

---

## 模块 7：Snapshot - Tooltip（参考百分位）

**对应接口**：`POST /web/portfolio-benchmark/snapshot`

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| Tooltip 百分位标签 | "P0" / "P25" / "P50" / "P75" / "P100" | `.tooltipData{METRIC_KEY}[].label` | String | 直接使用 | Internal Peers 5 档，外部基准 3 档 |
| Tooltip 百分位值 | 百分位数值 | `.tooltipData{METRIC_KEY}[].percentile` | Double | 直接使用 | — |
| Tooltip 参考值 | 格式化的指标值 | `.tooltipData{METRIC_KEY}[].formattedValue` | String | 直接使用 | — |
| Tooltip 原始值 | 数值 | `.tooltipData{METRIC_KEY}[].value` | BigDecimal | 可选使用 | — |

> **前端类型缺失**：`SnapshotCompany`、`SnapshotMetric` 等类型中无 `tooltipData` 字段定义。

---

## 模块 8：Snapshot - 分页

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| 分页器 - 当前页 | 当前页码 | `.data.pagination.page` | Integer | 直接使用 | **前端期望 `data.page`，接口为 `data.pagination.page`** |
| 分页器 - 每页条数 | 每页记录数 | `.data.pagination.size` | Integer | 直接使用 | **前端期望 `data.size`** |
| 分页器 - 总数 | 总记录数 | `.data.pagination.total` | Integer | 直接使用 | **前端期望 `data.totalElements`，接口为 `data.pagination.total`** |

---

## 模块 9：Trend - 指标卡片

**对应接口**：`POST /web/portfolio-benchmark/trend`

### 请求参数映射

| UI 控件 | 控件类型 | 请求参数 | 参数类型 | 是否必填 | 说明 |
|---|---|---|---|---|---|
| Companies 筛选 | 多选 | `companyIds` | List\<String\> | 是 | 选中的公司 ID |
| 日期范围 - 开始 | 月份选择 | `startDate` | String (yyyy-MM) | 否 | **前端传 `dateRange` 拼接字符串，接口分 `startDate`/`endDate`** |
| 日期范围 - 结束 | 月份选择 | `endDate` | String (yyyy-MM) | 否 | 同上 |
| DATA 标签 | 多选 | `dataSources` | List\<String\> | 否 | 枚举值需转换 |
| BENCHMARK 标签 | 多选 | `benchmarkSources` | List\<String\> | 否 | 枚举值需转换 |

### 响应字段映射 — 指标卡片

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| 卡片标题 | 指标名称 | `.data.metrics[].metricName` | String | 直接使用 | — |
| FILTER 分类匹配 | 用于筛选显示 | `.data.metrics[].categoryId` | String | **需映射 categoryId → MetricCategory** | **前端类型 `TrendMetric.category` 期望 "Growth"/"Efficiency" 等，接口返回 `categoryId` 如 "cat-revenue-growth"** |
| 月份轴 | 时间范围 | `.data.months[]` | String[] | 直接使用 | — |
| **（未使用）** | 指标 Key | `.data.metrics[].metricKey` | String | — | 前端用 `metricName` 匹配 |

---

## 模块 10：Trend - 折线图

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| 图表标题 | "Actuals - Internal Peers" | `.data.metrics[].charts[].title` | String | 直接使用 | API 已拼接好标题 |
| 基准源 | 用于排序 | `.data.metrics[].charts[].benchmarkSource` | String | 排序用 | — |
| 数据类型 | 用于排序+样式 | `.data.metrics[].charts[].dataType` | String | 排序+线型 | **前端类型 `TrendCombination` 用 `dataSource`，接口用 `dataType`** |
| 公司折线 | 每家公司的数据点 | `.data.metrics[].charts[].companySeries[]` | List | 按公司名 A-Z 排序 | **前端类型用 `companies[]`，接口用 `companySeries[]`** |
| Legend | 公司名 + 颜色 | `.companySeries[].companyName` | String | 自动分配颜色 | — |
| **（缺失）** | 公司 Logo | — | — | — | Trend 接口不返回 Logo，但 Legend 可能不需要 |

---

## 模块 11：Trend - 数据点

### 响应字段映射

| UI 展示位 | 展示内容描述 | 接口字段路径 | 字段类型 | 前端转换 | 备注 |
|---|---|---|---|---|---|
| Y 轴坐标 | 百分位值 | `.dataPoints[].percentile` | Double\|null | 直接使用 | null 时画在 P0 |
| Hover Tooltip | 百分位展示 | `.dataPoints[].percentileDisplay` | String | 直接使用 | — |
| Hover Tooltip | 格式化指标值 | `.dataPoints[].formattedValue` | String | 直接使用 | — |
| X 轴 | 月份 | `.dataPoints[].month` | String | 格式化为 "MMM YYYY" | — |
| 数据缺失处理 | hasData=false 画在 P0 | `.dataPoints[].hasData` | Boolean | `hasData=false` → `percentile=0` | **前端类型 `TrendMonthlyPoint` 无 `hasData` 字段** |
| **（未使用）** | 原始值 | `.dataPoints[].value` | BigDecimal | — | Trend 折线画百分位，原始值仅 Tooltip 使用 |

---

## 附录 A：枚举映射

### A.1 DataSource 枚举

| 前端枚举值（PascalCase） | 接口值（UPPER_SNAKE_CASE） | 展示文案 | 说明 |
|---|---|---|---|
| `Actuals` | `ACTUALS` | Actuals | 已有 `RAW_DS_TO_TYPE` 映射（`utils.ts:31-37`） |
| `CommittedForecast` | `COMMITTED_FORECAST` | Committed Forecast | 同上 |
| `SystemGeneratedForecast` | `SYSTEM_GENERATED_FORECAST` | System Generated Forecast | 同上 |

> 前端已有双向映射，覆盖完整。

### A.2 BenchmarkSource 枚举

| 前端枚举值（PascalCase） | 接口值（UPPER_SNAKE_CASE） | 展示文案 | 说明 |
|---|---|---|---|
| `InternalPeers` | `INTERNAL_PEERS` | Internal Peers | **前端无反向映射函数**，需新增 |
| `KeyBanc` | `KEYBANC` | KeyBanc | 同上 |
| `HighAlpha` | `HIGH_ALPHA` | High Alpha | 同上 |
| `BenchmarkIt` | `BENCHMARK_IT` | Benchmarkit.ai | 同上 |

> **缺失**：前端缺少 `benchmarkSourceFromApiString()` 类似 `dataSourceFromApiString()` 的映射函数。

### A.3 Company Status 枚举

| 前端枚举值 | 接口值 | 展示文案 | 说明 |
|---|---|---|---|
| `status: number` (如 4=Thriving) | `"ACTIVE"` | — | **类型完全不同** |
| `status: number` (如 6=Shut down) | `"SHUT_DOWN"` | Shut down | **类型完全不同** |
| `status: number` (如 7=Exited) | `"EXIT"` | Exited | **类型完全不同** |
| — | `"INACTIVE"` | Inactive | **前端未覆盖此枚举值** |

> **阻塞**：前端 `PortfolioCompanyItem.status` 为 number，接口返回 String 枚举。Mock 中用数字 4/6/7，需完全重写映射逻辑。

### A.4 EstimationType 枚举

| 前端枚举值 | 接口值 | 说明 |
|---|---|---|
| `EXACT` | `EXACT` | 精确匹配 |
| `INTERPOLATED` | `INTERPOLATED` | 线性插值 |
| `BOUNDARY` (FI 旧值) | — | **新接口拆分为以下两个** |
| — | `BOUNDARY_ABOVE` | 超上界，如 ">P75" |
| — | `BOUNDARY_BELOW` | 低于下界，如 "<P25" |
| `MEDIAN_ONLY` | `MEDIAN_ONLY` | 仅有中位数 |

> FI 的 `ApiEstimationType` 仍含旧值 `BOUNDARY`（`types.ts:284`）；新 Portfolio API 使用 `BOUNDARY_ABOVE`/`BOUNDARY_BELOW`。`percentileEstimationPrefix()` 已处理新值（`utils.ts:184-197`），但 TS 类型需更新。

### A.5 Metric Key 枚举

| UI 展示名 | 接口 Key | FILTER 分类 | 说明 |
|---|---|---|---|
| ARR Growth Rate | `ARR_GROWTH_RATE` | Growth | — |
| Gross Margin | `GROSS_MARGIN` | Efficiency | — |
| Monthly Net Burn Rate | `MONTHLY_NET_BURN_RATE` | Margins | — |
| Monthly Runway | `MONTHLY_RUNWAY` | Margins | — |
| Rule of 40 | `RULE_OF_40` | Capital | — |
| Sales Efficiency Ratio | `SALES_EFFICIENCY_RATIO` | Capital | — |

> 前端 `RADAR_METRICS` 使用展示名（`utils.ts:87`），接口用 UPPER_SNAKE_CASE。需在适配层建立双向映射。

### A.6 Trend categoryId → MetricCategory 映射

| 接口 categoryId | 前端 MetricCategory | 说明 |
|---|---|---|
| `cat-revenue-growth` | `Growth` | **仅从示例推断，需与后端确认完整列表** |
| （未知） | `Efficiency` | 接口文档仅给出一个示例 |
| （未知） | `Margins` | 同上 |
| （未知） | `Capital` | 同上 |

> **缺失**：接口文档仅给出 `categoryId: "cat-revenue-growth"` 一个示例，缺少其他 3 个分类的 categoryId 值。
