# BenchmarkV2 实现检查清单

> 关联 PRD：docs/Benchmark/01-prd.md | 关联 TDD：docs/Benchmark/03-technical-design.md
> 状态标记：⬜ 未开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已阻塞 | ⏭️ 跳过

---

## 后端实现（CIOaas-api / gstdev-cioaas-web）

### Phase 1: 枚举与 VO 层

| # | 任务 | TDD 章节 | 大小 | 依赖 | 状态 |
|---|------|----------|------|------|------|
| B-01 | 创建 `MetricEnum`：6 个指标枚举（metricId, displayName, categoryId, isReverse, isComputed） | 2.5.9 | S | — | ⬜ |
| B-02 | 创建 `DataSourceEnum`：ACTUALS, COMMITTED_FORECAST, SYSTEM_GENERATED_FORECAST | 2.5.8 | S | — | ⬜ |
| B-03 | 创建 `BenchmarkSourceEnum`：INTERNAL_PEERS, KEYBANC, HIGH_ALPHA, BENCHMARK_IT | 2.5.8 | S | — | ⬜ |
| B-04 | 创建 `ArrTierEnum`：5 个 ARR 分层 + fromArr() 静态方法 | 2.5.2 | S | — | ⬜ |
| B-05 | 创建 `EstimationTypeEnum`：EXACT, INTERPOLATED, BOUNDARY, MEDIAN_ONLY | 2.5.4 | S | — | ⬜ |
| B-06 | 创建 `QuartileEnum`：TOP_QUARTILE, UPPER_MIDDLE, LOWER_MIDDLE, BOTTOM_QUARTILE + fromPercentile() | 2.2 | S | — | ⬜ |
| B-07 | 创建核心 VO 类：`PeerGroupInfoDto`, `OverallScoreDto`, `CategoryScoreDto` | 2.2 | S | B-01~06 | ⬜ |
| B-08 | 创建 `MetricPercentileDto`, `DimensionPercentileDto`, `ExternalBenchmarkValuesDto` | 2.2 | S | B-01~06 | ⬜ |
| B-09 | 创建 `RadarSummaryDto`, `RadarMetricDto`, `DimensionSummaryDto` | 2.2 | S | B-01~06 | ⬜ |
| B-10 | 创建 `BenchmarkDataResponse`（统一 Snapshot/Trend 响应） | 2.2 API-01 | S | B-07~09 | ⬜ |
| B-11 | 创建 `MonthlyDataDto`（Trend 复用 MetricPercentileDto.monthlyData[]） | 2.2 API-02 | S | B-07~09 | ⬜ |
| B-11a | 创建 `ViewTypeEnum`: SNAPSHOT, TREND | 2.2 | S | — | ⬜ |
| B-12 | 创建 `BenchmarkFilterOptionsResponse`, `FilterOptionDto`（FilterOptions 响应） | 2.2 API-03 | S | — | ⬜ |

**阶段验证**：⬜ 所有枚举和 VO 编译通过，字段与 TDD 2.2 响应体一致

### Phase 2: 引擎层（Engine）

| # | 任务 | TDD 章节 | 大小 | 依赖 | 状态 |
|---|------|----------|------|------|------|
| B-13 | 创建 `InternalPercentileCalculator`：Standard Competition Ranking 百分位计算 | 2.5.5 | M | B-01 | ⬜ |
| B-14 | 实现 `InternalPercentileCalculator.calculateRunway()`：Monthly Runway N/A 三分类（Top/Bottom/Calculated）处理 | 2.5.5 | M | B-13 | ⬜ |
| B-15 | 创建 `ExternalPercentileCalculator`：线性插值、边界值、仅 P50 三种计算 | 2.5.4 | M | B-05 | ⬜ |
| B-16 | 实现 `ExternalPercentileCalculator` 反向指标处理（isReverse=true 时 p25/p75 交换） | 2.5.4 | S | B-15 | ⬜ |
| B-17 | 创建 `MetricExtractor`：从 FinancialNormalization 提取 Actuals 6 个指标值 | 2.5.3 | M | B-01 | ⬜ |
| B-18 | 实现 `MetricExtractor` Forecast 路径：从 financial_forecast_current 加载并通过 FiDataDto 计算指标 | 2.5.3 | L | B-17 | ⬜ |
| B-19 | 创建 `ForecastFiDataBuilder` 工具类：正确初始化 FiDataDto 的 lastYearMrr/lastMrr/lastMrrMonths/capitalizedRdTotal/recognition 等字段 | TDD Review P1-#4 | M | B-18 | ⬜ |
| B-20 | 创建 `PeerGroupResolver`：Actuals 同行匹配（委托 ColleagueCompanyService.buildBenchmarkPeerCompanyIds） | 2.5.2 | L | B-04, B-17 | ⬜ |
| B-21 | 实现 `PeerGroupResolver` Forecast 同行匹配：预测 ARR + 调整锚点（最后一个有预测 gross revenue 的月份） | 2.5.2 | L | B-20 | ⬜ |
| B-22 | 实现 `PeerGroupResolver` 回退逻辑：validPeers < 3 时 fallback 到全平台活跃公司 | 2.5.2 | S | B-20 | ⬜ |
| B-23 | 创建 `NumberParseUtil`：BenchmarkDetail string→BigDecimal 解析（百分比、金额格式） | TDD Review P2-#5 | S | — | ⬜ |

**阶段验证**：⬜ 各引擎类单元测试通过；百分位计算结果符合 PRD 示例

### Phase 3: 服务层（Service）

| # | 任务 | TDD 章节 | 大小 | 依赖 | 状态 |
|---|------|----------|------|------|------|
| B-24 | 创建 `BenchmarkingService` 接口：定义 getData / getFilterOptions 两个方法签名 | 2.3 | S | B-10~12 | ⬜ |
| B-25 | 实现 `BenchmarkingServiceImpl.getData()`：统一 Snapshot/Trend 编排逻辑（加载公司→确定日期→遍历维度→百分位计算→汇总） | 2.5.1 | L | B-13~23 | ⬜ |
| B-26 | 实现 `getData()` 汇总计算：板块分数、Overall Score、维度汇总、estimationMessage 生成 | 2.5.7 | M | B-25 | ⬜ |
| B-27 | 实现 `getData()` 雷达图计算：Snapshot 模式=单月各维度平均；Trend 模式=两步平均 | 2.5.1 | S | B-25 | ⬜ |
| B-28 | 已合并到 getData()，按 type 区分单月/多月 | 2.5.6 | — | — | ⏭️ 跳过 |
| B-29 | 已合并到 B-27（Trend 雷达图两步平均逻辑在 getData() 内实现） | 2.5.6 | — | — | ⏭️ 跳过 |
| B-30 | 实现 Trend 内同行缓存优化：同一请求内同一 dataSource 的 PeerGroupResult 复用 | TDD Review P1-#3 | M | B-28 | ⬜ |
| B-31 | 实现 `BenchmarkingServiceImpl.getFilterOptions()`：检测各 dataSource/benchmarkSource 可用性 | 2.2 API-03 | M | B-17 | ⬜ |

**阶段验证**：⬜ Service 逻辑正确，Snapshot 和 Trend API 返回结构完整

### Phase 4: 接口层（Controller）

| # | 任务 | TDD 章节 | 大小 | 依赖 | 状态 |
|---|------|----------|------|------|------|
| B-32 | 创建 `BenchmarkingController`：@RestController @RequestMapping("/benchmark/company") | 2.2 | S | B-24 | ⬜ |
| B-33 | 实现 GET `/{companyId}/data?type=SNAPSHOT\|TREND`（统一端点）：参数绑定 + Result.success() 包装 + @Operation 注解 | 2.2 API-01 | S | B-32 | ⬜ |
| B-34 | 已合并到 B-33 | 2.2 API-02 | — | — | ⏭️ 跳过 |
| B-35 | 实现 GET `/{companyId}/filter-options` 端点 | 2.2 API-03 | S | B-32 | ⬜ |
| B-36 | 参数校验：dataSources/benchmarkSources 空数组返回 400；startDate==endDate 返回 400 | 2.2 | S | B-33~35 | ⬜ |
| B-37 | OpenAPI 注解：@Tag, @Operation, @Parameter 完整标注，支持 SpringDoc 自动生成接口文档（2 个端点：/data, /filter-options） | 2.2 | S | B-33~35 | ⬜ |

**阶段验证**：⬜ 接口可调通，参数校验正确，OpenAPI 文档可生成

### Phase 5: 集成验证

| # | 任务 | TDD 章节 | 大小 | 依赖 | 状态 |
|---|------|----------|------|------|------|
| B-38 | /data?type=SNAPSHOT 端到端测试：Actuals + Internal Peers 维度 | AC-01 | M | B-33 | ⬜ |
| B-39 | /data?type=SNAPSHOT 端到端测试：Actuals + 外部基准（KeyBanc）维度 | AC-02 | M | B-33 | ⬜ |
| B-40 | /data?type=SNAPSHOT 端到端测试：Committed Forecast + Internal Peers（预测 ARR 匹配） | AC-03 | M | B-33 | ⬜ |
| B-41 | /data?type=SNAPSHOT 端到端测试：System Generated Forecast + Internal Peers | AC-04 | M | B-33 | ⬜ |
| B-42 | /data?type=TREND 端到端测试：6 个月 Actuals + Internal Peers | AC-09 | M | B-33 | ⬜ |
| B-43 | 同行回退测试：无匹配同行 → isFallback=true | AC-06 | S | B-33 | ⬜ |
| B-44 | Monthly Runway N/A 测试：Top/Bottom/Calculated 三种分类 | AC-07 | S | B-33 | ⬜ |
| B-45 | 全相同值测试：isTotalTie=true，不计入汇总 | AC-08 | S | B-33 | ⬜ |
| B-46 | Overall Score + 板块分数计算验证 | AC-10, AC-11 | M | B-33 | ⬜ |
| B-47 | 雷达图数据验证：Snapshot 单月平均 + Trend 两步平均 | AC-12 | M | B-33 | ⬜ |
| B-48 | 代码整合验证：Benchmark Entry API 不受影响 | AC-14 | S | B-33 | ⬜ |

**阶段验证**：⬜ 全部端到端测试通过

### Phase 6: 文档

| # | 任务 | TDD 章节 | 大小 | 依赖 | 状态 |
|---|------|----------|------|------|------|
| B-49 | 生成 OpenAPI/Swagger 接口文档（含每个字段描述） | AC-15 | M | B-37 | ⬜ |
| B-50 | 编写前端对接指南：接口调用示例 + 字段映射 + 颜色编码规则 | AC-15 | M | B-49 | ⬜ |

**阶段验证**：⬜ 接口文档完整，前端可据此开发

---

## 前端实现

> 本期不实现前端。以下为后续迭代参考。

| # | 任务 | 大小 | 状态 |
|---|------|------|------|
| F-01 | 路由配置：/company/:id/finance/benchmarking（复用 V1 路由或新增 V2） | S | ⏭️ |
| F-02 | API Service 层：benchmarkService.ts（3 个接口调用） | S | ⏭️ |
| F-03 | 筛选条件组件（VIEW/FILTER/DATA/BENCHMARK 四卡片 + 日历选择器） | M | ⏭️ |
| F-04 | Overall Benchmark Score Card 组件 | M | ⏭️ |
| F-05 | Snapshot 指标板块组件（4 板块 × 展开/收起 × 分布条） | L | ⏭️ |
| F-06 | Trend 折线图组件（ECharts 折线图 × 4 板块） | L | ⏭️ |
| F-07 | Metrics Summary 雷达图组件（ECharts radar） | M | ⏭️ |
| F-08 | Tooltip 组件（统一 Tooltip 渲染） | M | ⏭️ |

---

## 完成标准

| 标准 | 状态 |
|------|------|
| 所有 PRD 业务规则已实现（BR-01~30） | ⬜ |
| 3 个 API 接口可调通 | ⬜ |
| 15 条验收标准全部通过（AC-01~15） | ⬜ |
| V2 代码在 benchmark 包下，V1 不受影响 | ⬜ |
| OpenAPI 接口文档已生成 | ⬜ |
| 前端对接文档已交付 | ⬜ |

大小说明：S=半天内 | M=1天 | L=2天+
