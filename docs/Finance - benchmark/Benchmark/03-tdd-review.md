# BenchmarkV2 TDD 评审报告

> 评审日期：2026-03-26
> 评审对象：docs/Benchmark/03-technical-design.md v1.0
> 关联 PRD：docs/Benchmark/01-prd.md v2.0

---

## 一、评审总结

| 维度 | 状态 | 说明 |
|------|------|------|
| 需求覆盖 | ✅ | PRD 中全部 15 条验收标准和 30 条业务规则均有对应设计 |
| API 契约 | ✅ | 3 个 API 端点完整，请求/响应字段有详细类型和说明 |
| 数据模型 | ✅ | 复用已有表结构，无需新建 DDL，降低风险 |
| 前后端一致性 | ✅ | API 响应结构化良好，前端可直接映射到 UI 组件 |
| 授权矩阵 | ✅ | 3 个 API 均为只读，依赖既有登录态鉴权 |
| 数据流 | ✅ | 主流程清晰，数据源切换（Actuals vs Forecast）有明确设计 |
| 错误处理 | ✅ | HTTP 400/404/500 覆盖，GlobalExceptionHandler 统一处理 |
| 安全 | ✅ | Bearer Token 认证，只读操作无写入风险 |

---

## 二、需求覆盖检查

| PRD 需求/BR | TDD 对应章节 | 覆盖状态 | 备注 |
|-------------|-------------|----------|------|
| BR-01~03 6 指标/4 板块/映射固定 | 2.5.9 MetricEnum | ✅ | 枚举定义完整 |
| BR-04 Internal Peer 百分位公式 | 2.5.5 InternalPercentileCalculator | ✅ | 伪代码完整 |
| BR-05 外部基准插值 | 2.5.4 ExternalPercentileCalculator | ✅ | 三种 Case 覆盖 |
| BR-06 仅 P50 规则 | 2.5.4 calculateWithMedianOnly | ✅ | |
| BR-07 Actuals 同行匹配 | 2.5.2 PeerGroupResolver (ACTUALS 分支) | ✅ | |
| BR-08 Forecast 同行匹配 | 2.5.2 PeerGroupResolver (Forecast 分支) | ✅ | 含连续性验证 |
| BR-09 同行回退 | 2.5.2 回退判断 | ✅ | |
| BR-10 排除公司 | 2.5.2 CompanyActiveService | ✅ | |
| BR-11 DATA 与同行关系 | 2.5.2 + 2.5.3 | ✅ | 各维度独立同行集 |
| BR-12 Forecast + 外部基准 | 2.5.1 步骤 3b | ✅ | 用 Forecast 值与外部 P25/P50/P75 比较 |
| BR-13~15 板块/Overall/维度分数 | 2.5.7 汇总计算 | ✅ | |
| BR-16 指标排序 | 2.5.9 isReverse 定义 | ✅ | |
| BR-17 Runway N/A | 2.5.5 calculateRunway | ✅ | Top/Bottom/Calculated 三分类 |
| BR-18 全部相同值 | 2.5.5 totalTie 检测 | ✅ | |
| BR-20 实时计算 | 2.5.1 无缓存设计 | ✅ | |
| BR-21 数据来源 | 2.5.3 MetricExtractor | ✅ | Actuals→Normalization, Forecast→forecast_current |
| BR-22 外部基准数据 | 2.5.1 步骤 3b BenchmarkDetail | ✅ | |
| BR-23 Trend 自定义时间 | API-02 startDate/endDate | ✅ | |
| BR-27 代码整合 | 2.3 包结构 | ✅ | benchmark 独立包 |
| BR-29 插值公式 | 2.5.4 interpolate 方法 | ✅ | |
| AC-01~15 验收标准 | 全部有对应设计 | ✅ | |

---

## 三、前后端一致性检查

### API 契约对照

| API 端点 | 后端定义 | 前端调用建议 | 字段匹配 | 状态 |
|----------|----------|------------|----------|------|
| GET /benchmark/company/{id}/data?type=SNAPSHOT\|TREND | 完整定义 | getData() | ✅ | ✅ |
| GET /benchmark/company/{id}/filter-options | 完整定义 | getFilterOptions() | ✅ | ✅ |

### 数据字段链路

| PRD 字段 | 数据源表/列 | DTO 字段 | API 响应路径 | 状态 |
|----------|-----------|----------|-------------|------|
| Overall Score | 计算值 | OverallScoreDto.percentile | data.overallScore.percentile | ✅ |
| 板块分数 | 计算值 | CategoryScoreDto.score | data.categories[].score | ✅ |
| 指标百分位 | 计算值 | DimensionPercentileDto.percentile | data.categories[].metrics[].dimensions[].percentile | ✅ |
| 同行数量 | 计算值 | PeerGroupInfoDto.peerCount | data.peerGroupInfo.peerCount | ✅ |
| 回退标记 | 计算值 | PeerGroupInfoDto.isFallback | data.peerGroupInfo.isFallback | ✅ |
| 外部基准 P25/P50/P75 | benchmark_detail | ExternalBenchmarkValuesDto | dimensions[].benchmarkValues | ✅ |
| LG Formula | benchmark_metric.lg_formula | MetricPercentileDto.lgFormula | metrics[].lgFormula | ✅ |
| 雷达图数据 | 计算值 | RadarSummaryDto | data.radarSummary | ✅ |

---

## 四、问题清单

| # | 优先级 | 维度 | 问题描述 | 影响 | 是否阻塞 | 建议修改 |
|---|--------|------|----------|------|----------|----------|
| 1 | P1 | 数据一致性 | PeerGroupResolver 回退阈值使用 `validPeers.size() < 3`（注释说"有效同行 < 4 含目标公司"），但 PRD BR-09 定义为"有效同行 < 4"。需明确：是 peerCount < 4 还是 peerCount < 3？V1 PeerGroupResolver 使用 < 4。 | 同行回退阈值不一致可能导致 V1/V2 行为差异 | 否 | 建议统一为 `validPeers.size() < 3`，即需要至少 3 个同行（加上目标公司共 4 个），与注释和 V1 逻辑一致。在代码中加注释说明。 |
| 2 | P1 | API 契约 | Snapshot API 中 `peerGroupInfo` 是请求级别的，但不同 dataSource 可能有不同的同行集（Actuals 同行 ≠ Forecast 同行）。需要明确：peerGroupInfo 是否按 dataSource 区分？ | 前端可能误解同行信息 | 否 | 建议 `peerGroupInfo` 改为 Map<DataSource, PeerGroupInfoDto>，或在每个 dimension 中嵌入 peerCount。当前设计已在 dimension 中包含 peerCount，建议顶层 peerGroupInfo 反映 Actuals 的同行信息（主要维度），并加 `peerGroupInfoByDataSource` 可选字段。 |
| 3 | P1 | 性能 | Trend API 逐月调用 Snapshot 逻辑，6 个月 × 每月需查询同行+计算百分位。如果每月都做独立的 PeerGroupResolver，可能产生 6×N 次数据库查询。 | 响应可能超 5s | 否 | 建议优化：同一请求内缓存 PeerGroupResolver 结果（同一 dataSource 的同行在时间范围内不变），仅数据加载和百分位计算逐月执行。 |
| 4 | P1 | 数据一致性 | MetricExtractor 中 Forecast 指标通过 FiDataDto 计算，但 FiDataDto 的 ARR 计算依赖 `recognition`（收入确认方式，1/2/3），需要在 Forecast 路径中正确设置 recognition | ARR 和衍生指标可能计算错误 | 否 | 在 loadForecastAsFiDataDto 中从 Company(Invite) 获取 revenueRecognition 并注入 FiDataDto |
| 5 | P2 | API 契约 | BenchmarkDetail 中 P25/Median/P75 存储为 string，但 ExternalPercentileCalculator 需要 BigDecimal。TDD 中提到"需要数值解析"但未定义解析规则 | 解析失败时行为不确定 | 否 | 建议增加 NumberParseUtil：尝试解析 "35%" → 0.35，"$1.2M" → 1200000，解析失败返回 null（该维度显示 NA） |
| 6 | P2 | 功能完整性 | Snapshot API 的 `date` 参数格式为 `yyyy-MM`，但 FinancialNormalization.date 和 FinancialForecastCurrent.date 存储为 `yyyy-MM-dd`。需要日期格式转换 | 查询可能匹配不到数据 | 否 | API 入参用 `yyyy-MM`，内部转换为 `yyyy-MM-01` 再查询，或使用 LIKE 'yyyy-MM%' 匹配 |
| 7 | P2 | 边界条件 | ExternalPercentileCalculator 的反向指标处理中，交换 p25/p75 的逻辑需要更详细的测试用例验证。反向指标 + 超范围的组合场景较复杂 | 反向指标百分位可能计算错误 | 否 | 在 QA 文档中增加反向指标×超范围的组合测试用例 |
| 8 | P2 | 数据一致性 | MetricEnum 中 Monthly Net Burn Rate 的 isReverse=false，TDD 说明"升序排列时负值大的排前面"。但 FinancialNormalization.monthlyNetBurnRate 的值域可以是正数（盈利）或负数（亏损），需确认排序方向在正负混合场景下正确 | 百分位排名可能反转 | 否 | 建议增加单元测试覆盖：[-100, -50, 0, 50, 100] 的排名应为 [1, 2, 3, 4, 5]（升序，值大=排名靠后=百分位高） |
| 9 | P2 | 完整性 | TDD 未定义 `companyValueFormatted` 的格式化规则（哪些指标用 %，哪些用 $，精度几位） | 前端显示不一致 | 否 | 建议：Gross Margin/ARR Growth/Rule of 40 → 百分比格式(xx.x%)；Net Burn/Runway/Sales Eff → 金额格式($xx,xxx) |
| 10 | P2 | 安全 | TDD 未提及 companyId 的访问控制——用户是否只能查看自己有权访问的公司？ | 越权访问 | 否 | 依赖既有鉴权中间件（项目级权限检查），V2 不单独处理。建议在 TDD 中注明此假设。 |

---

## 五、设计决策评价

| 决策 | 评价 | 建议 |
|------|------|------|
| 复用已有表结构，无需新 DDL | ✅ 优秀 | 降低数据迁移风险，减少工作量 |
| benchmark 独立包 | ✅ 合理 | 隔离清晰，不影响 V1 |
| Forecast 指标通过 FiDataDto 计算 | ⚠️ 可行但需注意 | FiDataDto 设计为手动构建的值对象，在 Forecast 场景下需正确初始化所有依赖字段（lastYearMrr, lastMrr, lastMrrMonths, capitalizedRdTotal 等），否则衍生指标计算会出错。建议封装 ForecastFiDataBuilder 工具类。 |
| PeerGroupResolver 每个 dataSource 独立匹配 | ✅ 正确 | 符合 PRD BR-08 要求，不同 DATA 类型使用不同 ARR 和锚点 |
| Trend 逐月计算 | ⚠️ 可接受 | 6 个月内性能可接受，但需缓存同行集以优化 |
| 不缓存中间结果 | ✅ 符合 PRD BR-20 | 实时查询计算，数据始终最新 |

---

## 六、遗漏项

| # | 缺失内容 | 应在 TDD 哪个章节 | 优先级 |
|---|----------|------------------|--------|
| 1 | `companyValueFormatted` 格式化规则 | 2.5.3 MetricExtractor | P2 |
| 2 | BenchmarkDetail string→BigDecimal 解析规则 | 2.5.4 或新增 2.5.x | P2 |
| 3 | API 日期格式转换说明（yyyy-MM → yyyy-MM-dd） | 2.2 API 设计 | P2 |
| 4 | FiDataDto 在 Forecast 场景下的初始化策略 | 2.5.3 | P1 |
| 5 | 公司访问控制说明（依赖既有鉴权） | 2.4 授权矩阵 | P2 |
| 6 | Trend API 时间范围上限（建议 24 个月） | 2.2 API-02 | P2 |

---

## 七、后端专项检查

### DDL 质量
- ✅ 无需新 DDL，复用已有成熟表结构
- ✅ 已有索引覆盖主要查询路径（company_id + date）

### API 设计规范
- ✅ RESTful 风格，GET 方法用于只读查询
- ✅ 路径命名遵循 `/benchmark/company/{id}/resource` 模式
- ✅ 请求参数使用 query string（适合 GET 请求）
- ✅ 响应包装在 `Result<T>` 中
- ⚠️ `dataSources` 和 `benchmarkSources` 参数为数组，建议文档明确逗号分隔格式（如 `?dataSources=ACTUALS,COMMITTED_FORECAST`）

### Service 架构
- ✅ Interface + Impl 分离
- ✅ 引擎类职责单一（PeerGroup/Percentile/MetricExtract 分离）
- ⚠️ BenchmarkingServiceImpl 可能较大（编排逻辑复杂），建议拆分内部方法或引入 Helper 类

### 并发安全
- ✅ 所有 API 为只读查询，无并发写入风险
- ✅ 无共享可变状态

### 数据一致性
- ⚠️ Trend API 跨月查询时，同行集可能在不同月份不同（公司状态变更、ARR 变化导致 tier 变化）。当前设计逐月独立匹配是正确的，但性能需优化。

---

## 八、评审结论

- [x] TDD 可有条件通过（P1/P2 问题可在实现中修复）
- [ ] TDD 评审通过，可以进入实现阶段
- [ ] TDD 需修改后重新评审（存在 P0 阻塞问题）

### 无 P0 阻塞问题

### 修改建议优先级

1. **P1-#4**：FiDataDto 在 Forecast 场景下的初始化策略——需确保 lastYearMrr/lastMrr/capitalizedRdTotal 等字段正确设置，否则 ARR Growth Rate、Rule of 40、Sales Efficiency 等衍生指标会计算出错
2. **P1-#1**：统一回退阈值为 `validPeers.size() < 3`（等效 peerCount < 4）
3. **P1-#2**：peerGroupInfo 按 dataSource 区分或补充说明
4. **P1-#3**：Trend API 内缓存 PeerGroupResolver 结果优化性能
5. **P2-#5~10**：数值解析、日期格式、格式化规则等可在实现中处理
