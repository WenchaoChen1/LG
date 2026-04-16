# Benchmark Portfolio Intelligence 技术设计

> v1.1 | 2026-04-14 | 关联需求：01-prd.md（修订版）
> 变更记录：v1.1 — 新增 Trend 卡片 tooltip、图表 info icon tooltip、指标排序方向确认

## 一、做什么 & 怎么做

**需求**：在 Portfolio 详情页新增 Benchmarking tab，支持多公司 × 多基准 × 多数据类型的百分位对标分析，含 Snapshot（表格）和 Trend（折线图）两种视图。

**方案**：新建 `PortfolioBenchmarkController` + `PortfolioBenchmarkService`，复用现有 benchmark engine（`PeerGroupResolver`、`InternalPercentileCalculator`、`ExternalPercentileCalculator`、`MetricExtractor`）。**后端计算百分位**并返回预计算结果；**前端根据 Filter 动态计算 Overall Benchmark Score**（因 Filter 仅影响可见指标列，不影响百分位本身）。

**改动范围**：

| 层级 | 模块 | 变更类型 |
|------|------|----------|
| 后端 Controller | `fi/controller/PortfolioBenchmarkController.java` | 新增 |
| 后端 Service | `fi/service/PortfolioBenchmarkService.java` / `Impl` | 新增 |
| 后端 VO | `fi/benchmark/vo/portfolio/*.java` | 新增（约 17 个 DTO） |
| 后端 Engine | `fi/benchmark/engine/*` | **不改动**，直接复用 |
| 前端 | 新增 Benchmarking tab 页面 | 新增 |

**与现有 Benchmark 的关系**：现有 company benchmark 已重构 — `GET /benchmark/company/{companyId}/data` 返回纯原始值，百分位计算全部由前端完成。后端的两个 Calculator（`InternalPercentileCalculator`、`ExternalPercentileCalculator`）作为 `@Component` 保留但**当前无调用方（孤儿代码）**。本次 Portfolio Benchmark 将成为这两个 Calculator 的首个后端调用方，在服务端完成百分位计算后返回预计算结果。`PeerGroupResolver` 和 `MetricExtractor` 已被 `BenchmarkingServiceImpl` 主动使用，可直接复用。

---

## 二、接口设计

> 所有接口路径前缀：`/web/portfolio-benchmark`
> 详细字段说明见 `api-documentation.md`

### 公司列表（使用系统已有接口）

Portfolio 内公司列表由系统现有接口提供（Portfolio Companies 模块），本功能不新建接口。前端复用现有公司列表 API，在 Companies 筛选器中展示。

---

### API-01：Snapshot 数据查询（百分位预计算）

`POST /web/portfolio-benchmark/snapshot`

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyIds | List\<String\> | 是 | 至少 1 个 |
| date | String | 否 | yyyy-MM，默认当前月份 |
| dataSources | List\<String\> | 否 | 默认 ["ACTUALS"] |
| benchmarkSources | List\<String\> | 否 | 默认 ["INTERNAL_PEERS"] |
| page | Integer | 否 | 默认 1 |
| size | Integer | 否 | 默认 10 |

**返回结构 — 扁平行结构**（完整字段见 api-documentation.md）：

> 设计原则：每行 = 一个 `公司 × Benchmark × DataType` 组合，前端可直接遍历渲染表格子行，无需多层嵌套迭代。

```
Result<PortfolioSnapshotResponse> {
  rows: List<SnapshotRowDto> {
    — 行标识
    companyId: String
    companyName: String
    companyLogo: String
    benchmarkSource: String         — "INTERNAL_PEERS" | "KEYBANC" | ...
    benchmarkLabel: String          — "Internal Peers" | "KeyBanc - 2025"
    edition: String                 — 外部基准版本如 "2025"，内部为 null
    dataType: String                — "ACTUALS" | "COMMITTED_FORECAST" | ...
    dataTypeLabel: String           — "Actuals" | "Committed Forecast" | ...

    — 同行信息（仅 INTERNAL_PEERS 有值，外部基准为 null）
    peerCount: Integer
    isFallback: Boolean
    fallbackMessage: String

    — 6 个指标百分位结果（key = MetricEnum 名）
    metrics: Map<String, MetricPercentileDto> {
      value: BigDecimal             — 原始值
      formattedValue: String        — "35.00%" / "$1,234.56"
      percentile: Double            — 56.0（N/A 时为 null）
      percentileDisplay: String     — "P56" / "~P62" / ">P75" / "N/A"
      estimationType: String        — EXACT / INTERPOLATED / BOUNDARY_ABOVE / ...
    }

    — Tooltip 参考值（key = MetricEnum 名）
    tooltipData: Map<String, List<ReferencePercentileDto>> {
      label: String                 — "P0" / "P25" / "P50" / "P75" / "P100"
      percentile: Double
      value: BigDecimal
      formattedValue: String
    }
  }
  pagination: {
    page: Integer
    size: Integer
    totalCompanies: Integer         — 按公司计数（非行数）
  }
}
```

**行排序**：先按公司名 A-Z → 同公司内按 Benchmark 顺序（Internal Peers → KeyBanc → High Alpha → Benchmarkit）→ 同 Benchmark 内按 DataType 顺序（Actuals → Committed Forecast → System Generated Forecast）

**分页**：按公司分页（每页 10 家），返回该页所有公司的全部行。如选 2 个 Benchmark × 2 个 DataType = 每公司 4 行，则每页最多 40 行。

**错误情况**：
- companyIds 为空 → 400 BadRequestException
- companyIds 含不存在的 ID → 忽略无效 ID，仅返回有效公司数据

---

### API-02：Trend 数据查询（百分位预计算）

`POST /web/portfolio-benchmark/trend`

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyIds | List\<String\> | 是 | 至少 1 个 |
| startDate | String | 否 | yyyy-MM，默认当前月前 5 个月 |
| endDate | String | 否 | yyyy-MM，默认当前月份；必须 ≠ startDate |
| dataSources | List\<String\> | 否 | 默认 ["ACTUALS"] |
| benchmarkSources | List\<String\> | 否 | 默认 ["INTERNAL_PEERS"] |

**返回结构 — 扁平图表列表**（完整字段见 api-documentation.md）：

> 设计原则：每个 chart = 一个 `指标 × Benchmark × DataType` 组合，前端按 metricKey 分组即可渲染卡片。无需 metric → charts 两层嵌套。

```
Result<PortfolioTrendResponse> {
  months: List<String>                    — 有序月份列表
  companies: List<CompanyLegendDto> {     — 图例，A-Z 排序
    companyId: String
    companyName: String
  }
  charts: List<TrendChartDto> {
    — 图表标识
    metricKey: String                     — "ARR_GROWTH_RATE"
    metricName: String                    — "ARR Growth Rate"
    categoryId: String                    — "cat-revenue-growth"（前端 Filter 映射用）
    benchmarkSource: String               — "INTERNAL_PEERS" | "KEYBANC" | ...
    dataType: String                      — "ACTUALS" | ...
    title: String                         — "Actuals - Internal Peers"

    — 卡片 tooltip（同一 metricKey 的所有 chart 共享）
    calculationInfo: CalculationInfoDto {
      method: String                      — "Nearest Rank Percentile" / "Linear Interpolation"
      description: String                 — 指标公式说明
      cohortDescription: String           — 同群组说明（不含公司名）
    }

    — 图表 info icon tooltip：该组合下的参考百分位值（取 endDate 月）
    referencePercentiles: List<ReferencePercentileDto> {
      label: String                       — "P0" / "P25" / "P50" / "P75" / "P100"
      percentile: Double
      value: BigDecimal
      formattedValue: String
    }

    — 公司折线数据
    series: List<TrendSeriesDto> {
      companyId: String
      companyName: String
      — 以下三个数组与 months 数组等长、索引对齐，前端可直接 zip
      percentiles: List<Double>           — [80.0, null, 65.0, ...]（null = 无数据，画 P0）
      displays: List<String>              — ["P80", "N/A", "P65", ...]
      values: List<BigDecimal>            — [0.45, null, 0.35, ...]
    }
  }
}
```

**图表排序**：先按指标固定顺序（ARR Growth Rate → ... → Sales Efficiency Ratio）→ 同指标内按 Benchmark 顺序 → 同 Benchmark 内按 DataType 顺序

**series 排序**：按公司名 A-Z

**错误情况**：
- startDate == endDate → 400 BadRequestException
- startDate > endDate → 400 BadRequestException

---

## 三、数据设计

> **无新建表**。所有数据来源于现有表。

**复用已有表**：

| 表名 | 用途 |
|------|------|
| `invite`（Company） | 公司信息、Type、Stage、会计方法、状态 |
| `financial_normalization_current` | 标准化财务数据（Actuals + Forecast），唯一键 (company_id, date, data_type) |
| `financial_benchmark_entry` | 外部基准数据（KeyBanc / High Alpha / Benchmarkit 的 P25/P50/P75） |
| `financial_benchmark_metric` | 基准指标定义（metricId → LG metric 映射） |
| `r_colleague_company` / 相关表 | 手动同行组绑定关系 |
| `r_company_stage` | 公司阶段信息 |

---

## 四、核心逻辑

### 4.1 Snapshot 处理流程

```
请求进入
  │
  ├─ 1. 参数校验 + 默认值填充
  │
  ├─ 2. 查询公司列表（分页），按公司名 A-Z 排序
  │
  ├─ 3. 创建 MetricExtractor.DataCache（请求级缓存）
  │
  ├─ 4. 批量预加载数据（性能优化，详见 §五）
  │
  └─ 5. 遍历当前页公司
       │
       └─ 遍历 benchmarkSources
            │
            ├─ INTERNAL_PEERS:
            │    遍历 dataSources:
            │      a. PeerGroupResolver.resolve(company, date, dataSource)
            │      b. MetricExtractor.extractMetrics(companyId, date, dataSource, cache)
            │      c. 批量提取同行指标值
            │      d. 遍历 6 个指标:
            │         - 普通指标: InternalPercentileCalculator.calculate(companyValue, peerValues, isReverse)
            │         - Monthly Runway: InternalPercentileCalculator.calculateRunway(cash, burn, runway, peerEntries)
            │      e. 计算 Tooltip 参考值（§4.5）
            │
            └─ KEYBANC / HIGH_ALPHA / BENCHMARK_IT:
                 a. MetricExtractor.resolveCompanyArrForBenchmark(companyId, date, cache)
                 b. 根据 ARR 确定 Segment Value 范围
                 c. 查询匹配的 financial_benchmark_entry（platform + metricId + fyPeriod + segmentValue）
                 d. 遍历 dataSources:
                    - MetricExtractor.extractMetrics(companyId, date, dataSource, cache)
                    - 遍历 6 个指标:
                      ExternalPercentileCalculator.calculate(companyValue, p25, median, p75, isReverse, benchmarkValues)
                 e. Tooltip: 直接返回 P25/P50/P75 原始值
```

### 4.2 Trend 处理流程

```
请求进入
  │
  ├─ 1. 参数校验，生成月份列表（startDate → endDate）
  │
  ├─ 2. 创建 DataCache，批量预加载所有公司×所有月份的数据
  │
  └─ 3. 遍历 MetricEnum（固定 6 个）
       │
       ├─ 3a. 构建 calculationInfo（卡片 tooltip，详见 §4.6）
       │
       └─ 遍历 benchmarkSource × dataSource 组合（按排序规则）
            │
            ├─ 3b. 计算 referencePercentiles（图表 info tooltip，取 endDate 月，详见 §4.6）
            │
            └─ 遍历月份
                 │
                 └─ 遍历公司
                      │
                      ├─ INTERNAL_PEERS: resolve peer → calculate percentile
                      └─ EXTERNAL: match segment → calculate percentile
                      │
                      └─ 填充 TrendSeriesDto 的 percentiles/displays/values 数组
```

### 4.3 Internal Peers 百分位计算（复用现有逻辑）

**普通指标**（复用 `InternalPercentileCalculator.calculate`）：
```
输入: companyValue, peerValues[], isReverse
处理:
  1. allValues = peerValues + companyValue，排序（isReverse 则降序）
  2. 全部相同值 → N/A（totalTie）
  3. Standard Competition Ranking 找 rank
  4. P = (rank - 1) / (N - 1) × 100
  5. N=1 → P100
输出: { percentile, percentileDisplay, peerCount, isTied }
```

**Monthly Runway**（复用 `InternalPercentileCalculator.calculateRunway`）：
```
输入: targetCash, targetBurn, targetRunway, peerEntries[]
处理:
  1. 分类: classifyRunway(cash, burn) → TOP_RANK / BOTTOM_RANK / WORST_NEGATIVE_ZERO / CALCULATED / NO_DATA
  2. 排序: WORST_NEGATIVE_ZERO(0) < BOTTOM_RANK(1) < CALCULATED(2, 按 runway 升序) < TOP_RANK(3)
  3. 找 rank，计算百分位
输出: 同上
```

### 4.4 External 百分位计算（复用现有逻辑）

**复用 `ExternalPercentileCalculator.calculate`**：

| 情况 | 处理 | 展示 |
|------|------|------|
| 三点齐全，值在 P25-P50 之间 | 线性插值 `~P = 25 + (50-25) × (v-d25)/(d50-d25)` | ~P38 |
| 三点齐全，值精确匹配 | 精确百分位 | P25 / P50 / P75 |
| 三点齐全，值超范围 | 边界值 | \<P25（计算用 P0） / \>P75（计算用 P100） |
| 仅有 Median | 大于 → \>P50（计算用 P75）；小于 → \<P50（计算用 P25） | \>P50 / \<P50 |
| 部分缺失 | 有区间内插值，无区间用 median-only 逻辑 | 同上组合 |

**ARR Segment 匹配规则**：
```
companyArr = MetricExtractor.resolveCompanyArrForBenchmark(companyId, date, cache)
segmentValue = 根据 ARR 值确定范围:
  [$1, $250K) / [$250K, $1M) / [$1M, $5M) / [$5M, $20M] / ($20M, +∞)
fyPeriod = date 所属日历年份（如 2025-03 → "2025"）
查询: SELECT * FROM financial_benchmark_entry
  WHERE platform = :benchmarkSource AND metric_id = :metricId
    AND fy_period = :fyPeriod AND segment_value = :segmentValue
```

### 4.5 Tooltip 参考值计算

**Internal Peers — 计算 P0/P25/P50/P75/P100 处的参考值**：

```
输入: peerValues[]（含目标公司，已排序，共 N 个）
对每个目标百分位 P ∈ {0, 25, 50, 75, 100}:
  R = ((P × (N - 1)) / 100) + 1
  R = round(R)（四舍五入取整）
  referenceValue = sortedValues[R - 1]
输出: List<ReferencePercentileDto>
```

**External Benchmarks — 直接返回原始数据**：
```
输出: [
  { label: "P25", value: benchmarkEntry.p25 },
  { label: "P50", value: benchmarkEntry.median },
  { label: "P75", value: benchmarkEntry.p75 }
]
```

### 4.6 Trend 视图 Tooltip 数据（v1.1 新增）

**卡片级 tooltip（`calculationInfo`）**：

每个 TrendChartDto 携带该指标的计算说明（同一 metricKey 的 chart 共享），前端在卡片右上角 info icon 悬停时展示。

```
构建逻辑:
  对每个 metricKey:
    method =
      - 含 INTERNAL_PEERS → "Nearest Rank Percentile"
      - 仅含外部基准 → "Linear Interpolation"
      - 混合 → "Nearest Rank (Internal) / Linear Interpolation (External)"
    description = MetricEnum.getLgFormula()
    cohortDescription =
      - INTERNAL_PEERS → "Compared against [peerCount] peer companies matching
        Type, Stage, Accounting Method, and ARR range"
        （不列出具体公司名）
      - EXTERNAL → "Compared against [platform] [edition] survey data,
        segment: [segmentValue]"
```

**图表级 tooltip（`referencePercentiles`）**：

每个 TrendChartDto 携带该 benchmark×dataType 组合下、**最后一个月**的参考百分位值。结构复用 Snapshot 的 `ReferencePercentileDto`。

```
构建逻辑:
  取 endDate 月份（Trend 最后一个月）的数据:
    INTERNAL_PEERS → 同 §4.5 Internal Peers 逻辑，计算 P0/P25/P50/P75/P100 参考值
    EXTERNAL → 同 §4.5 External 逻辑，返回 P25/P50/P75 原始值
  注意: 仅计算一次（最后月），不逐月计算（性能考虑）
```

### 4.7 指标排序方向确认（v1.1 补充）

PRD v2 新增了指标排序方向表，与现有代码 `MetricEnum.isReverse` 完全一致：

| 指标 | PRD 方向 | MetricEnum.isReverse | 排序效果 |
|------|----------|---------------------|----------|
| ARR Growth Rate | 升序 | false | 高值 = 高百分位 ✅ |
| Gross Margin | 升序 | false | 高值 = 高百分位 ✅ |
| Monthly Net Burn Rate | 升序 | false | 少烧钱 = 高百分位 ✅ |
| Monthly Runway | 升序 | false | 长跑道 = 高百分位 ✅ |
| Rule of 40 | 升序 | false | 高值 = 高百分位 ✅ |
| Sales Efficiency Ratio | 降序 | true | 低值 = 高百分位 ✅ |

> 无需代码改动，仅作文档确认。

### 4.8 前端 Overall Benchmark Score 计算

> 此逻辑在前端实现，后端不参与。

```
输入: 当前行（DataTypeRow）的 metrics Map + 当前 Filter 选择
处理:
  1. 根据 Filter 确定可见指标列表:
     - ALL → 全部 6 个指标
     - GROWTH → [ARR_GROWTH_RATE]
     - EFFICIENCY → [GROSS_MARGIN]
     - MARGINS → [MONTHLY_NET_BURN_RATE, MONTHLY_RUNWAY]
     - CAPITAL → [RULE_OF_40, SALES_EFFICIENCY_RATIO]
  2. 收集可见指标的 percentile 值（跳过 null / N/A）
  3. overallScore = 算术平均值，四舍五入取整
  4. 展示格式: "35%ile"；若全部 N/A → "N/A"
```

---

## 五、性能优化

**目标**：10 家公司 × 4 基准 × 3 数据类型 × 6 指标 = 720 次百分位计算，Snapshot 响应 < 3s。

| 策略 | 说明 |
|------|------|
| 请求级缓存 | `MetricExtractor.DataCache`，每个 (companyId, dataType) 只查一次 DB |
| 批量预加载 | 进入处理前，一次性加载当前页所有公司 + 所有同行的 normalization 数据 |
| Peer 复用 | 同公司同 dataSource 的 peer group 在 Snapshot 中只 resolve 一次（不同 dataSource 的 peer 可能不同） |
| 外部基准缓存 | 同一 (platform, fyPeriod, segmentValue) 的 benchmark_entry 只查一次 |
| Trend 月份并行 | Trend 模式下各月份的计算相互独立，可用 `CompletableFuture` 并行（需评估线程池大小） |

**DataCache 预加载扩展**：

```java
// 在 PortfolioBenchmarkServiceImpl 中，进入循环前批量加载
public void preloadCache(DataCache cache, List<String> allCompanyIds, 
                          List<String> allPeerIds, List<Integer> dataTypes) {
    Set<String> allIds = new HashSet<>(allCompanyIds);
    allIds.addAll(allPeerIds);
    for (Integer dt : dataTypes) {
        List<FinancialNormalizationCurrent> batch = 
            normalizationCurrentRepository.findByCompanyIdInAndDataType(allIds, dt);
        // 按 companyId 分组填入 cache
        batch.stream().collect(Collectors.groupingBy(FinancialNormalizationCurrent::getCompanyId))
             .forEach((cid, rows) -> cache.normCache.put(cid + "|" + dt, rows));
    }
}
```

> 需要在 `FinancialNormalizationCurrentRepository` 新增批量查询方法：
> `List<FinancialNormalizationCurrent> findByCompanyIdInAndDataType(Collection<String> companyIds, Integer dataType)`

---

## 六、新增代码清单

### 6.1 后端新增文件

```
com/gstdev/cioaas/web/fi/
├── controller/
│   └── PortfolioBenchmarkController.java        — 2 个 API 端点（Snapshot + Trend）
├── service/
│   ├── PortfolioBenchmarkService.java           — 接口
│   └── PortfolioBenchmarkServiceImpl.java       — 核心编排逻辑
└── benchmark/vo/portfolio/
    ├── PortfolioSnapshotRequest.java            — API-01 请求体
    ├── PortfolioTrendRequest.java               — API-02 请求体
    ├── PortfolioSnapshotResponse.java           — API-01 响应（含扁平 rows）
    ├── PortfolioTrendResponse.java              — API-02 响应（含扁平 charts）
    ├── SnapshotRowDto.java                      — Snapshot 扁平行（公司×基准×数据类型）
    ├── MetricPercentileDto.java                 — 单指标百分位结果
    ├── ReferencePercentileDto.java              — Tooltip 参考值
    ├── TrendChartDto.java                       — Trend 扁平图表（指标×基准×数据类型）
    ├── TrendSeriesDto.java                      — Trend 公司折线（数组对齐 months）
    ├── CalculationInfoDto.java                  — 卡片 tooltip 计算说明
    ├── CompanyLegendDto.java                    — 图例
    └── PaginationDto.java                       — 分页信息
```

### 6.2 现有文件改动

| 文件 | 改动 |
|------|------|
| `FinancialNormalizationCurrentRepository.java` | 新增 `findByCompanyIdInAndDataType` 批量查询方法 |
| `MetricExtractor.DataCache` | 将 `normCache` 访问改为 package-private 或提供 put 方法，支持外部预加载 |

---

## 七、风险 & 待定

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| R1 | Trend 查询性能 — 6 月 × 10 公司 × 4 基准 × 3 DataType = 4320 次百分位计算，peer resolve 可能 N×M 次 DB 查询 | 响应超 3s | 批量预加载 + Trend 的 peer group 按月缓存；若仍慢，考虑后台预计算 |
| R2 | Internal Peers 的 peer group 每月可能不同（因 ARR 变化） | Trend 视图中同一公司不同月份的 peer set 不一致 | 符合业务逻辑（PRD 要求按查询月的 ARR 匹配），但需在 UI 上有说明 |
| R3 | 外部基准 FY Period 匹配规则待确认 | 可能匹配到错误年份数据 | 当前假设取日历年度；待产品确认 |
| R4 | Snapshot Tooltip 参考值计算 — N 较小时 P25/P75 可能无法精确插值 | 参考值精度受限 | 使用 Nearest Rank 四舍五入，与 PRD 一致 |
| R5 | Overall Score 前端计算 — Filter 多选时指标子集变化 | 需前端正确映射 categoryId → metricKeys | 提供 categoryId 字段供前端映射 |

---

## 八、工作量

| 任务 | 大小 | 依赖 |
|------|------|------|
| DTO 定义（约 15 个类） | M | — |
| PortfolioBenchmarkController | S | DTO |
| PortfolioBenchmarkService — Snapshot 逻辑 | L | Engine 类、Repository |
| PortfolioBenchmarkService — Trend 逻辑 | L | Engine 类、Repository |
| 批量预加载 + DataCache 扩展 | M | Repository |
| Repository 新增批量查询 | S | — |
| 接口联调 + 测试 | M | 全部 |
| **合计** | **约 6-7 天** | |

> 大小：S=半天内 | M=1天 | L=2天+
