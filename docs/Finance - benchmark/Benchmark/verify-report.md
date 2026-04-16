# Benchmark 后端实现验证报告

> 验证日期：2026-04-09
> 关联文档：01-prd.md, 03-technical-design.md, api-documentation.md
> 验证方式：静态代码分析（对照 PRD/TDD 逐项检查）
> 验证范围：CIOaas-api 后端代码

---

## 一、验证结果仪表盘

| 类别 | 总项 | 通过 | 不一致 | 未实现 |
|------|------|------|--------|--------|
| 接口契约 | 7 | 7 | 0 | 0 |
| 百分位计算引擎 | 8 | 8 | 0 | 0 |
| 同行匹配 | 6 | 6 | 0 | 0 |
| 分数聚合 | 5 | 5 | 0 | 0 |
| 指标公式 | 6 | 6 | 0 | 0 |
| 展示排序 | 2 | 2 | 0 | 0 |
| 默认值/配置 | 3 | 1 | 1 | 1 |
| 特殊场景处理 | 4 | 2 | 0 | 2 |
| **合计** | **41** | **37** | **1** | **3** |

**总体符合率：37/41 = 90%**

---

## 二、通过项（37 项）

### 接口契约 ✅

| # | 验证项 | 文件 | 结果 |
|---|--------|------|------|
| 1 | API-01 GET /benchmark/company/{companyId}/data 路径与参数 | BenchmarkController.java | ✅ |
| 2 | API-02 GET /benchmark/company/{companyId}/filter-options | BenchmarkController.java | ✅ |
| 3 | API-03~07 Benchmark Entry CRUD 端点 | BenchmarkController.java | ✅ |
| 4 | 响应统一包装 Result\<T\> | BenchmarkController.java | ✅ |
| 5 | BenchmarkDataResponse 结构（overallScore, categories, radarSummary, dimensionSummary） | BenchmarkDataResponse.java | ✅ |
| 6 | BenchmarkFilterOptionsResponse 结构 | BenchmarkFilterOptionsResponse.java | ✅ |
| 7 | 错误处理：companyId 不存在 → EntityNotFoundException | BenchmarkingServiceImpl.java | ✅ |

### 百分位计算引擎 ✅

| # | 验证项 | 文件 | 结果 |
|---|--------|------|------|
| 8 | 内部百分位公式 P=(R-1)/(N-1)×100 | InternalPercentileCalculator:67 | ✅ |
| 9 | Standard Competition Ranking（并列同排名，下一跳排名） | InternalPercentileCalculator:48-62 | ✅ |
| 10 | N=1 → P100 | InternalPercentileCalculator:32 | ✅ |
| 11 | 全部值相同 → totalTie=true，排除出计分 | InternalPercentileCalculator:37-42 | ✅ |
| 12 | 外部百分位线性插值公式正确 | ExternalPercentileCalculator:164-171 | ✅ |
| 13 | 外部边界：>P75→P100, <P25→P0 | ExternalPercentileCalculator:74-84 | ✅ |
| 14 | 仅 P50 时：>P50→P75, <P50→P25 | ExternalPercentileCalculator:113-120 | ✅ |
| 15 | 反向指标处理：swap P25↔P75 | ExternalPercentileCalculator:45-48 | ✅ |

### 同行匹配 ✅

| # | 验证项 | 文件 | 结果 |
|---|--------|------|------|
| 16 | 手动同行组优先 | ColleagueCompanyServiceImpl:847 | ✅ |
| 17 | 6 维度匹配（类型、阶段、会计方法、ARR 规模、数据质量、排除条件） | ColleagueCompanyServiceImpl:762-835 | ✅ |
| 18 | ARR 分段范围 [$1,$250K), [$250K,$1M), [$1M,$5M), [$5M,$20M], ($20M,+∞) | FiDataToolService:21-25 + ColleagueCompanyServiceImpl:762-770 | ✅ |
| 19 | 数据质量：24 月窗口内连续 6 月非负 gross revenue | ColleagueCompanyServiceImpl:625-727 | ✅ |
| 20 | 有效同行 < 3 家 → 回退全平台活跃公司 | ColleagueCompanyServiceImpl:915-924 | ✅ |
| 21 | 排除 Exited / Shut Down / Inactive | CompanyActiveServiceImpl:59-70 | ✅ |

### 指标公式 ✅

| # | 验证项 | 文件 | 结果 |
|---|--------|------|------|
| 22 | ARR Growth Rate = (ARR_t - ARR_(t-1)) / ARR_(t-1) | MetricExtractor:102-123 | ✅ |
| 23 | Gross Margin = norm.getGrossMargin() | MetricExtractor:107 | ✅ |
| 24 | Monthly Net Burn Rate = Net Income - Capitalized R&D | MetricExtractor:163-172 | ✅ |
| 25 | Monthly Runway = -(Cash / MonthlyNetBurnRate) | MetricExtractor:178-190 | ✅ |
| 26 | Rule of 40 = norm.getRuleOf40() | MetricExtractor:109 | ✅ |
| 27 | Sales Efficiency Ratio = norm.getSalesEfficiencyRatio() | MetricExtractor:110 | ✅ |

### 分数聚合 ✅

| # | 验证项 | 文件 | 结果 |
|---|--------|------|------|
| 28 | Overall Score = 4 板块分数算术平均，N/A 板块排除 | BenchmarkingServiceImpl:724-727 | ✅ |
| 29 | Category Score = 有效指标全维度百分位算术平均 | BenchmarkingServiceImpl:667-673 | ✅ |
| 30 | 维度点位 = DATA×BENCHMARK 下 6 指标百分位均值 | BenchmarkingServiceImpl:754-782 | ✅ |
| 31 | 雷达图 SNAPSHOT = 单月百分位 | BenchmarkingServiceImpl:877-910 | ✅ |
| 32 | 雷达图 TREND = 各月百分位算术平均 | BenchmarkingServiceImpl:917-949 | ✅ |

### Monthly Runway 特殊分类 ✅

| # | 验证项 | 文件 | 结果 |
|---|--------|------|------|
| 33 | Cash≥0 & Burn≥0 → TOP_RANK(P100) | InternalPercentileCalculator:150-170 | ✅ |
| 34 | Cash<0 & Burn>0 → WORST_NEGATIVE_ZERO(P0) | InternalPercentileCalculator:150-170 | ✅ |
| 35 | Cash<0 & Burn<0 → BOTTOM_RANK(P0) | InternalPercentileCalculator:150-170 | ✅ |

### 展示排序 + 估算提示 ✅

| # | 验证项 | 文件 | 结果 |
|---|--------|------|------|
| 36 | DATA/BENCHMARK 排序：Benchmark 优先 → Data 次之 | BenchmarkingServiceImpl:44-54 | ✅ |
| 37 | 估算提示三种变体（interpolated / boundary / both） | BenchmarkingServiceImpl:732-743 | ✅ |

---

## 三、不一致项（1 项）

| # | 严重度 | 位置 | PRD 要求 | 实际实现 | 影响 |
|---|--------|------|----------|----------|------|
| D-1 | ⚠️ 中 | BenchmarkDataQuery.applyDefaults():38 | 默认 BENCHMARK = Internal Peers 仅一个 | 默认全选 4 个：INTERNAL_PEERS, KEYBANC, HIGH_ALPHA, BENCHMARK_IT | 首屏加载时会计算 12 个维度（3 DATA × 4 BENCHMARK）而非 3 个维度，数据量和计算量更大 |

**代码位置**：
```
gstdev-cioaas-web/.../fi/benchmark/vo/BenchmarkDataQuery.java:38
benchmarkSources = List.of("INTERNAL_PEERS", "KEYBANC", "HIGH_ALPHA", "BENCHMARK_IT");
```

**建议**：与产品确认后统一。若以 PRD 为准，改为 `List.of("INTERNAL_PEERS")`。

---

## 四、未实现项（3 项）

| # | 严重度 | PRD 章节 | PRD 要求 | 当前状态 | 建议 |
|---|--------|----------|----------|----------|------|
| M-1 | 🔴 高 | §4.1.2 DATA 筛选项 | DATA 支持 Actuals、Committed Forecast、System Generated Forecast 三种 | **Forecast 数据源被硬编码禁用**。BenchmarkingServiceImpl:140-142 强制过滤为仅 ACTUALS | 删除 TODO 过滤代码，启用 Forecast 数据路径 |
| M-2 | 🟡 中 | §7.2 新建公司 | 新建公司无 Actual 数据时，Actuals 不可选或显示为灰色 | filter-options API 返回 latestActualDate 但**未返回 disabled 标记**，前端无法判断是否禁用 Actuals | FilterOptionsResponse 中增加 availableDataSources[] 含 disabled 字段 |
| M-3 | 🟡 中 | §6.1.2 外部基准匹配 | Segment Type 是 ARR，匹配时应对应正确年份的相同 Segment Value 范围 | 外部基准匹配用 **SegmentValueEnum**（7 档：<$1M, $1M-$5M, ...,$50M-$100M, >$100M），与内部同行 **ArrTierEnum**（5 档：$1-$250K, ...,$20M+）范围定义完全不同。**非 bug**（两者用途不同），但 PRD 未区分说明 | PRD 补充说明：内部同行 ARR 分段（5 档）与外部基准 Segment 分段（7 档）是独立的 |

### M-1 详细说明

**当前代码**（BenchmarkingServiceImpl.java:140-142）：
```java
// TODO: Currently only ACTUALS is supported.
dsList = dsList.stream().filter(ds -> ds == DataSourceEnum.ACTUALS).collect(Collectors.toList());
if (dsList.isEmpty()) dsList = List.of(DataSourceEnum.ACTUALS);
```

这段代码将所有传入的 dataSources 强制过滤为仅 ACTUALS。即使前端选择了 Committed Forecast 或 System Generated Forecast，后端也会忽略并只返回 Actuals 数据。

**影响**：
- 用户无法查看预测数据的对标结果
- PRD §6.2.3 中 "Forecast vs Forecast" 和 "Forecast vs 外部基准" 的对标场景完全不可用
- PRD §7.2 新建公司仅显示 Forecast 数据的场景不可用

---

## 五、验证通过但值得注意的项

| # | 类别 | 说明 |
|---|------|------|
| N-1 | 性能 | 12 维度 × 6 指标 × N 月计算无缓存层，依赖 request-scoped DataCache。大同行组（>50 家）时可能影响响应时间 |
| N-2 | 外部基准匹配 | matchBenchmarkDetail 按 YEAR（非 yyyy-MM）匹配 fyPeriod，若同年有多条记录按 edition 择优（优先当年 edition） |
| N-3 | Monthly Runway 公式 | 代码中 `divide.compareTo(BigDecimal.ZERO) <= 0 ? null : divide` 会将 Runway ≤ 0 的情况返回 null，这些由 InternalPercentileCalculator.classifyRunway() 统一处理为特殊分类 |
| N-4 | 只读指标 isReverse | 仅 SALES_EFFICIENCY_RATIO 标记 isReverse=true，其余 5 个指标（含 Monthly Net Burn Rate）均为 false。与 PRD 一致：Burn Rate 数值越大越好 |

---

## 六、总结

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  后端实现验证报告 — Benchmark
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  验证总项：41
  ✅ 通过：37（90%）
  ⚠️ 不一致：1（默认 BENCHMARK 源）
  🔴 未实现：3（Forecast 数据源、新建公司处理、PRD 未区分 ARR 分段）

  核心计算引擎：100% 通过
  ├─ 内部百分位（Nearest Rank）     ✅
  ├─ 外部百分位（线性插值+边界）    ✅
  ├─ 同行匹配（6 维度+回退）       ✅
  ├─ 分数聚合（板块/Overall/雷达）  ✅
  └─ Monthly Runway 特殊分类       ✅

  需修复优先级：
  P0  M-1  启用 Forecast 数据源（删除硬编码过滤）
  P1  D-1  统一默认 BENCHMARK 值
  P1  M-2  filter-options 返回 DATA 可用性标记
  P2  M-3  PRD 补充 ARR 分段说明（文档问题，非代码问题）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
