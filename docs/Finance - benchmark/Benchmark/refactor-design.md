# Benchmark 前后端职责重构设计

> v1.0 | 2026-04-13 | 作者：重构规划
> 关联：01-prd.md、03-technical-design.md（即将过期）
> 状态：DRAFT

---

## 一、重构目标

1. **FILTER 驱动 Overall Score 计算**：选中的板块决定 Overall Score 的构成（当前 FILTER 仅影响显示）
2. **Metrics Summary 雷达图不受 FILTER 影响**：永远基于全部 6 指标聚合
3. **计算职责迁移**：百分位计算 + 聚合逻辑全部搬到前端；后端只返回原始值（公司值、同行值、外部基准 P25/P50/P75）
4. **后端保留百分位计算能力**：作为独立服务类保留（供后期其他业务使用，如通知系统），但**从 API 响应路径中剥离**

---

## 二、架构对比

### 当前架构

```
请求 → Backend
  ├─ PeerGroupResolver     解析同行
  ├─ MetricExtractor       提取指标值
  ├─ InternalPercentile    计算内部百分位
  ├─ ExternalPercentile    计算外部百分位
  ├─ buildCategories       聚合板块分数
  ├─ buildOverallScore     聚合综合分
  ├─ buildDimensionSummary 聚合维度点位
  └─ buildRadarSummary     聚合雷达图
                ↓
Response: 精装的 BenchmarkDataResponse（overall/categories/radar/dimension 全预计算）
                ↓
Frontend: 直接渲染（FILTER 仅控制显示/隐藏，不影响数值）
```

### 目标架构

```
请求 → Backend
  ├─ PeerGroupResolver     解析同行（保留）
  ├─ MetricExtractor       提取公司 + 同行指标值（保留）
  └─ matchExternalBenchmark 查外部基准 P25/P50/P75（保留）
                ↓
Response: 扁平的 BenchmarkRawDataResponse（只有原始值）
                ↓
Frontend
  ├─ percentile 计算层（Nearest Rank / 线性插值 / Runway 分类）
  ├─ 聚合层
  │   ├─ Overall Score（FILTER 敏感）
  │   ├─ Category Score
  │   ├─ Dimension Points（DATA×BENCHMARK）
  │   └─ Radar（永远全指标）
  └─ 渲染层（FILTER 切换只触发 useMemo，不触发 fetch）
```

**关键收益**：FILTER 切换零 API 调用，即时响应。

---

## 三、后端改动

### 3.1 新增/修改

| 变更 | 文件 | 说明 |
|------|------|------|
| 精简 | `BenchmarkingServiceImpl.getData()` | 只调 PeerGroupResolver + MetricExtractor + 外部基准匹配；不再调用任何 `build*` 方法 |
| 新增 | `BenchmarkRawDataResponse` (VO) | 新响应结构，见 §五 |
| 新增 | `CompanyMetricValues` (VO) | 单个月份 × dataSource 的 6 指标原始值 |
| 新增 | `PeerMetricValues` (VO) | 含 peerId 的 PeerMetricValues |
| 新增 | `ExternalBenchmarkValues` (VO) | 按年份匹配后的 {p25, median, p75} + 元数据 |
| 新增 | `PeerMetaDto` (VO) | 同行元数据（peerId、peerName） |

### 3.2 删除

| 类/方法 | 原位置 | 理由 |
|---------|--------|------|
| `BenchmarkDataResponse` | `fi.benchmark.vo` | 被新的 `BenchmarkRawDataResponse` 替代 |
| `OverallScoreDto` | `fi.benchmark.vo` | 聚合职责转前端 |
| `CategoryScoreDto` | `fi.benchmark.vo` | 同上 |
| `MetricPercentileDto` | `fi.benchmark.vo` | 百分位计算转前端 |
| `DimensionPercentileDto` | `fi.benchmark.vo` | 同上 |
| `DimensionSummaryDto` | `fi.benchmark.vo` | 同上 |
| `RadarSummaryDto` / `RadarDimensionDto` / `RadarMetricDto` | `fi.benchmark.vo` | 同上 |
| `BenchmarkingServiceImpl.buildCategories()` | service | 聚合搬前端 |
| `BenchmarkingServiceImpl.buildOverallScore()` | service | 同上 |
| `BenchmarkingServiceImpl.buildDimensionSummary()` | service | 同上 |
| `BenchmarkingServiceImpl.buildRadarSummarySnapshot/Trend()` | service | 同上 |
| `BenchmarkingServiceImpl.computeMetricData()` | service | 百分位计算转前端，此方法随之删除 |
| `BenchmarkingServiceImpl.MetricComputeResult` | 内部 record | 同上 |

### 3.3 保留（作为可复用计算服务）

| 类 | 用途 | 是否被新 API 使用？ |
|----|------|--------------------|
| `PeerGroupResolver` | 解析同行（含 ARR 分档、数据质量、回退） | ✅ 是 |
| `MetricExtractor` | 从 `financial_normalization_current` 提取指标 | ✅ 是 |
| `InternalPercentileCalculator` | Nearest Rank 百分位计算 | ❌ 否（保留供通知系统等未来业务使用） |
| `ExternalPercentileCalculator` | 线性插值 + 边界处理 | ❌ 否（同上） |

上述 4 个计算引擎保留为 `@Component`，独立可注入，**新的 API 响应路径不再调用百分位计算器**。

### 3.4 `BenchmarkingServiceImpl.getData()` 新实现伪代码

```java
public BenchmarkRawDataResponse getData(String companyId, BenchmarkDataQuery query) {
    // 1. 解析参数
    Invite company = findCompany(companyId);
    List<DataSourceEnum> dsList = parseDataSources(query.getDataSources());
    List<BenchmarkSourceEnum> bsList = parseBenchmarkSources(query.getBenchmarkSources());
    List<String> months = resolveMonths(query);
    MetricExtractor.DataCache cache = metricExtractor.createCache();
    
    // 2. 解析同行组（每月 × 每 dataSource 可能不同）
    Map<String, PeerGroupResult> peerCache = new HashMap<>();
    List<String> allPeerIds = new LinkedHashSet<>();  // 去重
    for (String month : months) {
        for (DataSourceEnum ds : dsList) {
            PeerGroupResult pg = peerGroupResolver.resolve(company, month, ds);
            peerCache.put(ds.name() + "|" + month, pg);
            allPeerIds.addAll(pg.getPeerIds());
        }
    }
    
    // 3. 提取公司各月 × dataSource 的 6 指标原始值
    List<CompanyMetricValues> companyMetrics = new ArrayList<>();
    for (String month : months) {
        for (DataSourceEnum ds : dsList) {
            Map<MetricEnum, BigDecimal> vals = metricExtractor.extractMetrics(companyId, month, ds, cache);
            BigDecimal cash = metricExtractor.extractCash(companyId, month, ds, cache);  // 新增辅助方法
            companyMetrics.add(toCompanyMetricValues(month, ds, vals, cash));
        }
    }
    
    // 4. 提取同行各月 × dataSource × peer 的 6 指标
    List<PeerMetricValues> peerMetrics = new ArrayList<>();
    for (String month : months) {
        for (DataSourceEnum ds : dsList) {
            PeerGroupResult pg = peerCache.get(ds.name() + "|" + month);
            for (String peerId : pg.getPeerIds()) {
                Map<MetricEnum, BigDecimal> vals = metricExtractor.extractMetrics(peerId, month, ds, cache);
                BigDecimal cash = metricExtractor.extractCash(peerId, month, ds, cache);
                peerMetrics.add(toPeerMetricValues(month, ds, peerId, vals, cash));
            }
        }
    }
    
    // 5. 匹配外部基准（按年份 × benchmarkSource × metric）
    List<ExternalBenchmarkValues> externalBenchmarks = matchAllExternalBenchmarks(
        company, months, bsList, companyArr);
    
    // 6. 组装响应
    return BenchmarkRawDataResponse.builder()
        .companyId(companyId).companyName(company.getCompanyName())
        .type(query.getType()).months(months)
        .peerGroupInfo(buildPeerGroupInfoOverall(peerCache))
        .peers(buildPeerMetaList(allPeerIds))
        .companyArr(...).companyArrSource(...).companyArrMonth(...)
        .companyMetrics(companyMetrics)
        .peerMetrics(peerMetrics)
        .externalBenchmarks(externalBenchmarks)
        .build();
}
```

### 3.5 MetricExtractor 增量

需要新增一个方法用于提取 Monthly Runway 分类所需的 cash：

```java
public BigDecimal extractCash(String companyId, String date, DataSourceEnum ds, DataCache cache) {
    int dataType = NormalizationDataTypeEnum.fromDataSource(ds).getCode();
    FinancialNormalizationCurrent norm = findNormCurrent(companyId, date, dataType, cache);
    return norm != null ? norm.getCash() : null;
}
```

---

## 四、前端改动

### 4.1 新增模块

| 文件 | 职责 |
|------|------|
| `src/pages/companyFinance/benchmark/calc/percentile.ts` | 内部 Nearest Rank 百分位 |
| `src/pages/companyFinance/benchmark/calc/externalPercentile.ts` | 外部线性插值 + 边界处理 |
| `src/pages/companyFinance/benchmark/calc/runway.ts` | Monthly Runway 分类 + 特殊百分位 |
| `src/pages/companyFinance/benchmark/calc/aggregate.ts` | 聚合函数（category / overall / radar / dimension） |
| `src/pages/companyFinance/benchmark/calc/metrics.ts` | 指标元数据（isReverse, categoryId, ...） |
| `src/pages/companyFinance/benchmark/calc/__tests__/*.test.ts` | 单测（关键：保证和后端语义对齐） |

### 4.2 修改

| 文件 | 变更 |
|------|------|
| `types.ts` | 更新 `BenchmarkResponseData`、`TrendResponseData` 为新扁平结构；新增内部 `CalculatedData` 类型表示前端计算出的完整视图 |
| `hooks/useBenchmarkData.ts` | 重构：fetch 返回原始数据；`useMemo(() => aggregate(raw, selectedCategories), [raw, selectedCategories])` 派生视图 |
| `services/api/companyFinance/benchmarkService.ts` | 响应类型换成 `BenchmarkRawDataResponse` |
| `services/api/companyFinance/benchmarkAdapters.ts` | 移除复杂结构变换，保留枚举映射 |
| `components/OverallScoreBar.tsx` | 从 useBenchmarkData 消费派生的聚合视图 |
| `components/RadarChart.tsx` | 消费 `aggregate.radar(raw)` 的输出（不受 FILTER 影响） |
| `components/MetricPercentileBar.tsx` | 消费派生的单指标百分位 |
| `components/TrendLineChart.tsx` | 消费派生的 trend 聚合 |

### 4.3 `useBenchmarkData` 重构后的数据流

```typescript
// state
const [raw, setRaw] = useState<BenchmarkRawDataResponse | null>(null);
const [filters, setFilters] = useState<FilterState>(defaultFilters);

// fetch: 只在 date / dataSources / benchmarkSources / viewMode 变化时触发
useEffect(() => {
  fetchBenchmarkData(companyId, buildQuery(filters))
    .then(setRaw);
}, [companyId, filters.viewMode, filters.selectedDate, filters.selectedDataSources, filters.selectedBenchmarkSources]);

// derive: FILTER（分类选择）变化时只重新聚合，不 fetch
const view = useMemo(() => {
  if (!raw) return null;
  return aggregate(raw, {
    selectedCategories: filters.selectedCategories,  // 影响 Overall + 可见板块
    // 雷达图始终用全部 6 指标，不需要传 FILTER
  });
}, [raw, filters.selectedCategories]);

return { raw, view, filters, setFilters };
```

---

## 五、API 契约（完整）

### 5.1 Endpoint

`GET /benchmark/company/{companyId}/data`

**请求参数**（与现有一致）：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| companyId | path String | 是 | — | 公司 UUID |
| type | query String | 否 | SNAPSHOT | SNAPSHOT / TREND |
| date | query String | 否 | closed month | yyyy-MM，SNAPSHOT 用 |
| startDate | query String | 否 | endDate - 5 | yyyy-MM，TREND 用 |
| endDate | query String | 否 | closed month | yyyy-MM，TREND 用 |
| dataSources | query String[] | 否 | [ACTUALS] | 可选项 × 3 |
| benchmarkSources | query String[] | 否 | [INTERNAL_PEERS] | 可选项 × 4 |

### 5.2 响应：`BenchmarkRawDataResponse`

```typescript
interface BenchmarkRawDataResponse {
  // === 元数据 ===
  companyId: string;
  companyName: string;
  type: 'SNAPSHOT' | 'TREND';
  months: string[];                      // 1 for SNAPSHOT, N for TREND
  dataSources: string[];                 // 回显生效的 DATA
  benchmarkSources: string[];            // 回显生效的 BENCHMARK
  
  // === 同行组信息（整体视角，不区分月份）===
  peerGroupInfo: {
    peerCount: number;                   // 最大月份的同行数（用于 UI 展示总览）
    isFallback: boolean;                 // 是否任一月份使用回退
    fallbackMessage: string | null;
    matchCriteria: Record<string, string>;  // 匹配维度值
  };
  
  // === 同行元数据（去重，一次性）===
  peers: Array<{
    peerId: string;
    peerName: string;
  }>;
  
  // === 公司 ARR（用于展示和外部基准 Segment 匹配溯源）===
  companyArr: number | null;
  companyArrSource: 'NORMALIZATION_ARR' | 'MRR_X12' | 'NONE';
  companyArrMonth: string;
  
  // === 公司指标原始值：month × dataSource ===
  companyMetrics: Array<{
    month: string;                       // "2026-03"
    dataSource: 'ACTUALS' | 'COMMITTED_FORECAST' | 'SYSTEM_GENERATED_FORECAST';
    arrGrowthRate: number | null;        // 已由后端按 (arr_t - arr_{t-1}) / arr_{t-1} 计算好
    grossMargin: number | null;
    monthlyNetBurnRate: number | null;
    ruleOf40: number | null;
    salesEfficiencyRatio: number | null;
    cash: number | null;                 // Runway 分类必需
    // 注：monthlyRunway 不单独返回，前端用 cash + monthlyNetBurnRate 自己分类 + 计算
  }>;
  
  // === 同行指标原始值：month × dataSource × peerId ===
  peerMetrics: Array<{
    month: string;
    dataSource: string;
    peerId: string;
    // 指标字段与 companyMetrics 完全一致
    arrGrowthRate: number | null;
    grossMargin: number | null;
    monthlyNetBurnRate: number | null;
    ruleOf40: number | null;
    salesEfficiencyRatio: number | null;
    cash: number | null;
  }>;
  
  // === 外部基准：按 (年份, benchmarkSource, metric) 匹配后的结果 ===
  // 注意：外部基准数据是年度级的（fyPeriod=年份），不是月度级
  //      若 TREND 跨年，会有多条记录（每年一条）
  externalBenchmarks: Array<{
    year: string;                        // "2026"（从 month 中提取年份）
    benchmarkSource: 'KEYBANC' | 'HIGH_ALPHA' | 'BENCHMARK_IT';
    metricId: string;                    // "GROSS_MARGIN" 等
    found: boolean;                      // 是否匹配到数据
    // 匹配到时填充以下字段（found=false 时全部为 null）
    platform: string | null;
    edition: string | null;
    metricName: string | null;
    definition: string | null;
    segmentType: string | null;
    segmentValue: string | null;
    bestGuess: string | null;
    p25: string | null;                  // 保持字符串（源表存的就是字符串，如 "12.5%"）
    median: string | null;
    p75: string | null;
  }>;
}
```

### 5.3 关键设计取舍说明

| 问题 | 决策 | 理由 |
|------|------|------|
| ARR Growth Rate 为何仍由后端预计算？ | 需要前一月 ARR，跨月访问 DB 更重，后端原样保留此计算 | 这不是"百分位"计算，是指标提取的一部分 |
| 为何不直接返回 `monthlyRunway` 值？ | 分类逻辑依赖原始 cash & burn，需要发 raw | 前端用 `cash + monthlyNetBurnRate` 即可分类并求值 |
| 同行值会暴露隐私吗？ | peerName 已脱敏为系统值，values 为聚合财务指标 | 现有实现已发送相同数据，无新增暴露 |
| 响应体大小？ | 最坏情况 TREND 6 月 × 3 DS × 50 同行 × 6 指标 ≈ 1.1MB | 可接受；后续按需开启 gzip |

---

## 六、核心算法迁移（Java → TypeScript）

### 6.1 Nearest Rank 内部百分位（calc/percentile.ts）

```typescript
export interface InternalPercentileResult {
  percentile: number | null;       // null 表示 totalTie 或无数据
  percentileDisplay: string;       // "P45" / "N/A"
  peerCount: number;
  isTied: boolean;
  isTotalTie: boolean;
}

// 镜像 InternalPercentileCalculator.calculate()
export function computeInternalPercentile(
  targetValue: number | null,
  peerValues: Array<number | null>,
  isReverse: boolean,
): InternalPercentileResult {
  if (targetValue === null) return { percentile: null, percentileDisplay: 'N/A', peerCount: 0, isTied: false, isTotalTie: false };
  
  const validPeerValues = peerValues.filter((v): v is number => v !== null);
  const all = [...validPeerValues, targetValue];
  const n = all.length;
  
  if (n === 1) return { percentile: 100, percentileDisplay: 'P100', peerCount: 0, isTied: false, isTotalTie: false };
  
  // totalTie 检测
  if (all.every(v => v === all[0])) {
    return { percentile: null, percentileDisplay: 'N/A', peerCount: n - 1, isTied: true, isTotalTie: true };
  }
  
  // 排序（反向指标降序）
  const sorted = [...all].sort((a, b) => isReverse ? b - a : a - b);
  
  // Standard Competition Ranking
  let rank = 0;
  let prevValue: number | null = null;
  let currentRank = 0;
  for (let i = 0; i < sorted.length; i++) {
    const v = sorted[i];
    if (prevValue === null || v !== prevValue) {
      currentRank = i + 1;
    }
    if (v === targetValue && rank === 0) {
      rank = currentRank;
    }
    prevValue = v;
  }
  
  const percentile = Math.round(((rank - 1) / (n - 1)) * 100 * 100) / 100;
  const isTied = all.filter(v => v === targetValue).length > 1;
  
  return { percentile, percentileDisplay: `P${Math.round(percentile)}`, peerCount: n - 1, isTied, isTotalTie: false };
}
```

### 6.2 外部线性插值（calc/externalPercentile.ts）

镜像 `ExternalPercentileCalculator.calculate()`：按 Case A/B/C/D 分支（详见 03-technical-design §4.4）。支持 EXACT / INTERPOLATED / BOUNDARY_ABOVE / BOUNDARY_BELOW / MEDIAN_ONLY 五种 `estimationType`。

**反向指标**：内部 swap `p25 ↔ p75`。

**关键：P25/P50/P75 从字符串解析为数字**。输入可能是 `"12.5%"` 或 `"-2.3"` 等格式，需要规范化的数字解析工具。可以从后端 `NumberParseUtil.java` 平移逻辑。

### 6.3 Monthly Runway 分类（calc/runway.ts）

```typescript
export type RunwayClassification = 
  | 'TOP_RANK'              // cash ≥ 0 & burn ≥ 0
  | 'CALCULATED'            // 正常计算
  | 'WORST_NEGATIVE_ZERO'   // cash<0 & burn=0 或 cash=0 & burn<0
  | 'BOTTOM_RANK'           // cash < 0 & burn < 0
  | 'NO_DATA';

export function classifyRunway(cash: number | null, burn: number | null): RunwayClassification {
  if (cash === null || burn === null) return 'NO_DATA';
  if (cash >= 0 && burn >= 0) return 'TOP_RANK';
  if (cash < 0 && burn < 0) return 'BOTTOM_RANK';
  if ((cash < 0 && burn === 0) || (cash === 0 && burn < 0)) return 'WORST_NEGATIVE_ZERO';
  return 'CALCULATED';
}

// 镜像 InternalPercentileCalculator.calculateRunway()
export function computeRunwayPercentile(
  targetCash: number | null,
  targetBurn: number | null,
  peerEntries: Array<{ cash: number | null; burn: number | null }>,
): InternalPercentileResult {
  const targetClass = classifyRunway(targetCash, targetBurn);
  if (targetClass === 'NO_DATA') return noData();
  
  // 同行分 4 类，分别桶排序；桶间用排名优先级（TOP > CALCULATED > BOTTOM > WORST）
  // 桶内按 runway 值排序（CALCULATED 用 -(cash/burn)）
  // 然后合并桶并用 Nearest Rank 计算
  // ...（见 Java 版本详细逻辑）
}
```

### 6.4 聚合（calc/aggregate.ts）

```typescript
export interface AggregateInput {
  raw: BenchmarkRawDataResponse;
  selectedCategories: string[];  // ["GROWTH", "EFFICIENCY"] 等，ALL 表示全部
}

export interface AggregatedView {
  // 按板块 → 指标 → 维度组装好的视图
  categories: Array<{
    categoryId: string;
    categoryName: string;
    visible: boolean;              // 是否受 FILTER 包含
    score: number | null;          // 板块分
    scoreDisplay: string;
    quartile: string;
    metrics: Array<{
      metricId: string;
      metricName: string;
      hasData: boolean;
      isTotalTie: boolean;
      dimensions: Array<{
        dataSource: string;
        benchmarkSource: string;
        percentile: number | null;
        percentileDisplay: string;
        estimationType: string;
        companyValue: number | null;
        // tooltip 所需的额外信息
        peerCount?: number;
        peerData?: Array<{peerId, peerName, value}>;
        benchmarkValues?: ExternalBenchmarkValues;
      }>;
    }>;
  }>;
  
  // Overall Score — 基于 visible 板块的算术平均
  overallScore: {
    percentile: number | null;
    quartile: string;
    metricCount: number;
    quartileLabel: string;          // "6 Metrics - Top Quartile"
    hasEstimated: boolean;
    estimationMessage: string | null;
    dimensionPoints: Array<{        // 最多 12 个点位
      dataSource: string;
      benchmarkSource: string;
      percentile: number | null;
    }>;
  };
  
  // 雷达图 — 永远全部 6 指标（不受 selectedCategories 影响）
  radar: {
    axes: MetricId[];                // 固定 6 个
    series: Array<{
      dataSource: string;
      benchmarkSource: string;
      points: number[];              // 6 个百分位
    }>;
  };
}

export function aggregate(input: AggregateInput): AggregatedView {
  const { raw, selectedCategories } = input;
  
  // 1. 每个维度 × 每个指标 × 每个月：计算百分位
  //    - INTERNAL_PEERS → computeInternalPercentile (或 computeRunwayPercentile)
  //    - EXTERNAL → computeExternalPercentile
  // 2. SNAPSHOT 单月即终值；TREND 多月取月均
  // 3. 按指标 → 板块组装
  // 4. 板块分 = 该板块有效指标的全维度百分位算术平均
  // 5. Overall = 选中板块（visible）的板块分算术平均
  // 6. Dimension Points = 每个 DATA×BENCHMARK 下 6 指标百分位算术平均（不受 FILTER 影响）
  // 7. Radar = 按维度分组的 6 指标百分位
  
  // 关键：selectedCategories 只影响 overallScore 和 categories[].visible
  //      radar、dimensionPoints、每个指标本身的百分位都不受影响
}
```

### 6.5 单元测试策略

新增 `__tests__/` 目录，为每个算法至少写 5 个用例：

| 算法 | 关键用例 |
|------|---------|
| `computeInternalPercentile` | N=1、全部相同、并列排名、反向指标、正常分布 |
| `computeExternalPercentile` | Case A/B/C/D 各至少 2 例；反向指标 swap；精确匹配 P25/P50/P75 |
| `classifyRunway` | 8 种 cash×burn 组合全覆盖 |
| `aggregate` | 空数据、部分板块 N/A、totalTie 排除、FILTER 单选/多选/ALL |

**黄金输出验证**：保存当前后端完整响应 JSON 作为 fixture，跑新前端聚合后对比结果。允许浮点容差 ≤ 1e-6。

---

## 七、迁移步骤

建议**三阶段、可回滚**的渐进式迁移：

### Stage 1 — 后端双写（1-2 天）

目标：后端同时返回新旧字段，前端零改动。

1. `BenchmarkRawDataResponse` 新增为**顶层响应的嵌套字段**（而非替换）：
   ```typescript
   {
     // 旧字段全部保留
     overallScore, categories, radarSummary, dimensionSummary, ...
     // 新字段
     rawData: BenchmarkRawDataResponse;
   }
   ```
2. 后端在一次请求内同时产出两套数据（复用 MetricExtractor 输出）。
3. 前端不变化，继续消费旧字段。
4. **价值**：拿到线上真实请求的双份输出，可 diff 验证前端聚合将来是否等价。

### Stage 2 — 前端切换（3-5 天）

目标：前端用 rawData 自行计算，旧字段仅作 fallback。

1. 实现前端 `calc/*.ts` 所有算法 + 单测。
2. 用 Stage 1 采集的 fixture 做黄金输出对比验证。
3. 重构 `useBenchmarkData` + 组件，消费 `calc.aggregate(rawData)` 的输出。
4. 开关：`ENABLE_CLIENT_CALC` 环境变量控制，默认 false。通过 feature flag 灰度打开。
5. **验收点**：开关 ON/OFF 下所有数值和 UI 完全一致（允许浮点容差）。

### Stage 3 — 后端精简（1 天）

目标：删除旧字段和聚合代码。

1. 响应只返回 `BenchmarkRawDataResponse` 的内容（扁平到顶层）。
2. 删除 `buildCategories/buildOverallScore/buildDimensionSummary/buildRadarSummary` 方法。
3. 删除 `OverallScoreDto/CategoryScoreDto/MetricPercentileDto/DimensionPercentileDto/DimensionSummaryDto/RadarSummaryDto` 等 DTO。
4. 前端移除 `ENABLE_CLIENT_CALC` 开关，删除旧结构消费代码。
5. 更新 API 文档。

**保留的后端计算服务**（供未来通知系统使用）：
- `PeerGroupResolver` ✅
- `MetricExtractor` ✅
- `InternalPercentileCalculator` ✅
- `ExternalPercentileCalculator` ✅

---

## 八、风险与验证

| 风险 | 等级 | 应对 |
|------|------|------|
| 前端算法移植精度偏差 | 🔴 高 | 黄金输出对比 + 单测覆盖率 ≥ 90%；浮点容差 ≤ 1e-6 |
| 响应体过大影响性能（最坏 ~1.1MB） | 🟡 中 | 启用 gzip（Spring Boot 一行配置）；监控大请求，必要时分片 |
| TREND 模式前端计算量大（月数 × 12 维度 × 6 指标） | 🟡 中 | `useMemo` 缓存；若慢用 `Comlink` 搬 worker |
| FILTER 切换时 Overall 不变化的 bug | 🟡 中 | 单测：`aggregate(raw, {selectedCategories: ["ALL"]}) ≠ aggregate(raw, {selectedCategories: ["GROWTH"]})` |
| `BigDecimal` → JavaScript `number` 精度丢失 | 🟡 中 | 财务数值保留 10 位小数即可，百分位最终四舍五入 2 位。大数值（如 ARR）后端转 string 传前端（遵循 common.md §1 Long-as-String 规范）；小数值直接 number |
| Stage 1-2 之间响应体翻倍 | 🟢 低 | 灰度期（~1 周），监控后端内存与带宽 |
| 通知系统未来需要完整聚合 | 🟢 低 | `aggregate` 逻辑的后端版本仍可在需要时用 Java 重新实现（单变量纯函数易移植） |

---

## 九、验收清单

实施完成的验收标准：

- [ ] 前端单测覆盖 `calc/*` 所有导出函数，覆盖率 ≥ 90%
- [ ] 至少 10 个黄金输出 fixture（覆盖 SNAPSHOT/TREND、单/多 DATA、单/多 BENCHMARK、有/无同行回退）
- [ ] FILTER 切换（GROWTH ↔ ALL ↔ EFFICIENCY）触发 0 次 fetch，Overall Score 数值按选中板块变化
- [ ] 雷达图始终显示 6 个指标轴（切 FILTER 无变化）
- [ ] 后端代码 `grep -r "buildCategories\|buildOverallScore\|buildRadarSummary\|buildDimensionSummary"` 零命中
- [ ] 后端保留：`InternalPercentileCalculator`、`ExternalPercentileCalculator`、`PeerGroupResolver`、`MetricExtractor` 均作为 `@Component` 可注入
- [ ] 响应体大小（gzip 后）：SNAPSHOT < 20KB、TREND 6 月 < 200KB
- [ ] Tooltip 数据完整：指标悬停显示 peerCount（内部）或 platform/edition/segment（外部），与重构前一致
- [ ] 同行回退提示（Peer Fallback）正确显示
- [ ] 新建公司（无 Actual 数据）场景：Actuals 禁用、Forecast 可用
- [ ] API 文档（`api-documentation.md`）已同步更新

---

## 十、工作量

| 任务 | 负责端 | 大小 | 依赖 |
|------|--------|------|------|
| B1. 新 DTO `BenchmarkRawDataResponse` + 子类型 | 后端 | S | — |
| B2. `MetricExtractor.extractCash()` | 后端 | S | — |
| B3. `BenchmarkingServiceImpl.getData()` 重构（Stage 1 双写） | 后端 | M | B1, B2 |
| B4. 删除聚合逻辑与旧 DTO（Stage 3） | 后端 | S | F4 |
| F1. `calc/percentile.ts` + 单测 | 前端 | M | — |
| F2. `calc/externalPercentile.ts` + 单测 | 前端 | M | — |
| F3. `calc/runway.ts` + 单测 | 前端 | S | — |
| F4. `calc/aggregate.ts` + 单测 | 前端 | L | F1, F2, F3 |
| F5. `useBenchmarkData` 重构 + 组件改造 | 前端 | M | F4 |
| F6. 黄金输出对比验证 | 前端 | M | Stage 1 部署 |
| D1. 更新 `api-documentation.md` + `03-technical-design.md` | 文档 | S | B4 |
| D2. 更新 `02-prd-review.md` 中残留的 "Overall Score 不受 FILTER 影响" 假设描述 | 文档 | S | — |

> S=半天 | M=1 天 | L=2 天+

**总工时估算**：后端 ~2 天，前端 ~5-6 天，联调+验证 ~2 天，共 ~9-10 人天。

---

## 十一、规范对齐

### 后端（遵循 CIOaas-api/.claude/standards）

- 新 DTO 使用 `@Data @Builder @NoArgsConstructor @AllArgsConstructor`
- 响应走 `Result.success(data)`
- DI 使用 `@Resource`
- MetricExtractor 新方法读操作加 `@Transactional(readOnly = true)` 的继承或显式标注
- 字段命名 lowerCamelCase，数据库字段 snake_case（无新建表，跳过）
- 文档放 `.claude/doc/features/`

### 前端（遵循 CIOaas-web/standards）

- `src/pages/companyFinance/benchmark/calc/*.ts` 为纯函数模块，不依赖 React
- 类型定义集中在 `types.ts`
- 单测用 jest；命名 `*.test.ts`
- 不污染全局状态，所有计算基于 props/hook state
- Less modules 复用 `src/global.less` 变量

---

## 十二、未决事项

| # | 问题 | 需要谁决策 |
|---|------|-----------|
| 1 | 响应体字段命名：扁平数组 vs 按 month/ds 嵌套 map？本文档选扁平，如有前端性能顾虑可改为 map | 前端 |
| 2 | 外部基准 `p25/median/p75` 是 string 还是 number？本文档建议保持 string（源表就是 string，含百分号），由前端解析。如果前端希望统一数字，后端需加解析层 | 前后端协商 |
| 3 | 是否保留 Stage 1 的双写期？可缩短为 1-2 天，或直接跳过走 Stage 2+3（有风险） | 项目组 |

---

**下一步**：确认本设计后，我可以：
- A) 开始实施 Stage 1（后端双写）
- B) 先出前端 `calc/*.ts` 的详细 TypeScript 代码草稿（无 React，纯算法层），便于离线 review
- C) 补充 API 文档到 `api-documentation.md`
