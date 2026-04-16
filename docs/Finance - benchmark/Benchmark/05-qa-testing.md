# BenchmarkV2 测试验收文档

> 关联 PRD：docs/Benchmark/01-prd.md | 关联 TDD：docs/Benchmark/03-technical-design.md
> 测试状态：⬜ 未测 | ✅ 通过 | ❌ 失败 | ⏭️ 跳过

---

## 一、功能测试用例

### 模块 A：Data API (SNAPSHOT) — Internal Peers (Actuals)

| # | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 状态 |
|---|----------|----------|----------|----------|------|
| TC-01 | 基本 data?type=SNAPSHOT 查询 | 公司有 Actual 数据，有 ≥4 同行 | GET /benchmark/company/{id}/data?type=SNAPSHOT&dataSources=ACTUALS&benchmarkSources=INTERNAL_PEERS | 返回 200，overallScore 非 null，categories 有 4 个板块，每个板块有指标数据 | ⬜ |
| TC-02 | 默认参数查询 | 公司有 Actual 数据 | GET /benchmark/company/{id}/data?type=SNAPSHOT（无额外参数） | date 自动填充为最近 closed month，dataSources=[ACTUALS]，benchmarkSources=[INTERNAL_PEERS] | ⬜ |
| TC-03 | 指定月份查询 | 公司 2025-06 有数据 | GET ...?date=2025-06 | 返回 2025-06 的百分位数据 | ⬜ |
| TC-04 | ARR Growth Rate 计算 | 目标公司 ARR_t=500K, ARR_(t-1)=400K | 查询该月 data?type=SNAPSHOT | ARR Growth Rate companyValue=0.25(25%)，百分位根据同行排名计算 | ⬜ |
| TC-05 | Gross Margin 计算 | 目标公司 grossMargin=0.65 | 查询 data?type=SNAPSHOT | Gross Margin companyValue=0.65，percentileDisplay 正确 | ⬜ |
| TC-06 | Monthly Net Burn Rate 排序 | 同行 Burn=[-100K, -50K, -20K, 10K]，目标=-30K | 查询 data?type=SNAPSHOT | 升序排序 [-100K, -50K, -30K, -20K, 10K]，目标排名=3，P=((3-1)/(5-1))×100=50 | ⬜ |
| TC-07 | Sales Efficiency 反向排序 | 同行 SER=[2.0, 3.0, 5.0]，目标=1.5 | 查询 data?type=SNAPSHOT | 降序排序 [5.0, 3.0, 2.0, 1.5]，目标排名=4，P=((4-1)/(4-1))×100=100(最佳) | ⬜ |
| TC-08 | 百分位=100（仅 1 家公司） | 目标公司无同行（fallback 后也仅自身） | 查询 data?type=SNAPSHOT | N=1 时 P=100 | ⬜ |
| TC-09 | 相同值竞争排名 | 同行值=[10, 20, 20, 30]，目标=20 | 查询 data?type=SNAPSHOT | 排名=[1,2,2,4]（竞争排名），目标排名=2，isTied=true | ⬜ |
| TC-10 | 全部相同值 | 同行值=[50, 50, 50]，目标=50 | 查询 data?type=SNAPSHOT | isTotalTie=true，该指标不计入板块分数和 Overall Score | ⬜ |

### 模块 B：Data API (SNAPSHOT) — Internal Peers (Forecast)

| # | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 状态 |
|---|----------|----------|----------|----------|------|
| TC-11 | Committed Forecast 基本查询 | 公司有 Committed Forecast 数据 | GET ...?dataSources=COMMITTED_FORECAST&benchmarkSources=INTERNAL_PEERS | 返回百分位数据，使用预测 ARR 匹配同行 | ⬜ |
| TC-12 | System Generated Forecast 基本查询 | 公司有 System Forecast 数据（type="1"或"2"） | GET ...?dataSources=SYSTEM_GENERATED_FORECAST&benchmarkSources=INTERNAL_PEERS | 返回百分位数据 | ⬜ |
| TC-13 | Forecast 同行 ARR 匹配 | 目标公司预测 ARR=$3M，同行1 预测 ARR=$2M（同 tier），同行2 预测 ARR=$10M（不同 tier） | 查询 Committed Forecast | 同行1 被匹配，同行2 被排除（ARR tier 不同） | ⬜ |
| TC-14 | Forecast 连续性锚点验证 | 公司最后一个有预测 gross revenue 的月份=2026-06，从 2026-06 回溯有连续 6 个月非负 revenue | 查询 Forecast | 该公司通过连续性验证，被纳入同行 | ⬜ |
| TC-15 | Forecast 连续性验证失败 | 同行公司预测数据中不存在连续 6 个月非负 gross revenue | 查询 Forecast | 该同行被排除 | ⬜ |
| TC-16 | Forecast 同行无数据 | 所有同行均无 Committed Forecast | 查询 Committed Forecast | 回退到全平台基准或各指标显示 NA（取决于是否有全平台 forecast 数据） | ⬜ |
| TC-17 | 多 DATA 维度同时查询 | 公司有 Actuals 和 Committed Forecast | GET ...?dataSources=ACTUALS,COMMITTED_FORECAST | 每个指标返回 2 个 dimension（Actuals-IP, CF-IP） | ⬜ |

### 模块 C：Data API (SNAPSHOT) — 外部基准

| # | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 状态 |
|---|----------|----------|----------|----------|------|
| TC-18 | KeyBanc 精确匹配 | ARR Growth P25=20%, P50=30%, P75=40%，公司值=30% | GET ...?benchmarkSources=KEYBANC | percentile=50, percentileDisplay="50%ile", estimationType="EXACT" | ⬜ |
| TC-19 | KeyBanc 线性插值 | P25=20%, P50=30%, P75=40%，公司值=35% | 查询 | percentile≈62.5, percentileDisplay="~63%ile", estimationType=INTERPOLATED | ⬜ |
| TC-20 | KeyBanc 超上界 | P25=20%, P50=30%, P75=40%，公司值=50% | 查询 | percentile=75(边界值), percentileDisplay=">75%ile", estimationType=BOUNDARY_ABOVE | ⬜ |
| TC-21 | KeyBanc 超下界 | P25=20%, P50=30%, P75=40%，公司值=10% | 查询 | percentile=25(边界值), percentileDisplay="<25%ile", estimationType=BOUNDARY_ABOVE | ⬜ |
| TC-22 | 仅 P50 高于中位数 | 仅有 Median=30%，无 P25/P75，公司值=40% | 查询 | percentile=75, percentileDisplay=">50%ile", estimationType=MEDIAN_ONLY | ⬜ |
| TC-23 | 仅 P50 低于中位数 | 仅有 Median=30%，公司值=20% | 查询 | percentile=25, percentileDisplay="<50%ile", estimationType=MEDIAN_ONLY | ⬜ |
| TC-24 | 仅 P50 等于中位数 | 仅有 Median=30%，公司值=30% | 查询 | percentile=50, percentileDisplay="50%ile", estimationType="EXACT" | ⬜ |
| TC-25 | 外部基准无数据 | KeyBanc 无 ARR Growth Rate 数据 | GET ...?benchmarkSources=KEYBANC | 该指标 KeyBanc 维度 percentile=null, percentileDisplay="NA" | ⬜ |
| TC-26 | 反向指标+线性插值 | Sales Eff Ratio P25=2.0, P50=3.0, P75=5.0，公司值=2.5（反向:值低=好） | 查询 | 应落在 P50-P75 区间（因反向），percentile≈62.5 | ⬜ |
| TC-27 | Forecast + 外部基准 | 公司 Committed Forecast Gross Margin=45%，KeyBanc P25=30%, P50=40%, P75=50% | GET ...?dataSources=COMMITTED_FORECAST&benchmarkSources=KEYBANC | 用预测值 45% 与 KeyBanc 基准计算，percentile≈62.5 | ⬜ |

### 模块 D：Monthly Runway 特殊处理

| # | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 状态 |
|---|----------|----------|----------|----------|------|
| TC-28 | Runway Top Rank | 目标公司 Cash=1M, Burn=50K（均 ≥ 0） | 查询 data?type=SNAPSHOT | Runway=N/A 但分类为 Top Rank，百分位=100(最高) | ⬜ |
| TC-29 | Runway Bottom Rank | 目标公司 Cash=-100K, Burn=-20K（均 < 0） | 查询 data?type=SNAPSHOT | Runway=N/A 但分类为 Bottom Rank，百分位=0(最低) | ⬜ |
| TC-30 | Runway Calculated | 目标公司 Cash=500K, Burn=-50K（XOR 关系） | 查询 data?type=SNAPSHOT | Runway=10 个月，按计算值与同行排名 | ⬜ |
| TC-31 | Runway 混合排名 | 同行=[Top, Calculated(12mo), Calculated(6mo), Bottom]，目标=Calculated(8mo) | 查询 data?type=SNAPSHOT | 排序: Bottom(0), Calc(6), Calc(8-target), Calc(12), Top → 目标排名=3, P=50 | ⬜ |

### 模块 E：汇总计算

| # | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 状态 |
|---|----------|----------|----------|----------|------|
| TC-32 | 板块分数计算 | Burn & Runway: Net Burn P=55, Runway P=45 | 查询 data?type=SNAPSHOT | Burn & Runway score=(55+45)/2=50 | ⬜ |
| TC-33 | 板块分数排除无数据 | Capital Efficiency: Rule of 40 P=60, Sales Eff=NA | 查询 data?type=SNAPSHOT | Capital Efficiency score=60（仅 Rule of 40 参与） | ⬜ |
| TC-34 | Overall Score 计算 | 4 板块分数=[51, 25, 89, 10] | 查询 data?type=SNAPSHOT | Overall=(51+25+89+10)/4=43.75 | ⬜ |
| TC-35 | Overall Score 排除全无数据板块 | Revenue P=50, Profitability=NA, Burn P=80, Capital P=30 | 查询 data?type=SNAPSHOT | Overall=(50+80+30)/3=53.3 | ⬜ |
| TC-36 | 维度分数计算 | Actuals-IP: ARR P=50, GM P=55, Burn P=60, Runway P=65, Ro40 P=45, SER P=40 | 查询 data?type=SNAPSHOT | dimensionSummary Actuals-IP averagePercentile=(50+55+60+65+45+40)/6=52.5 | ⬜ |
| TC-37 | estimationMessage 生成 | 存在插值和边界值 | 查询 data?type=SNAPSHOT | hasEstimatedPercentiles=true, estimationMessage 包含 "interpolated values used & boundary values used" | ⬜ |
| TC-38 | isTotalTie 不计入汇总 | 某指标 isTotalTie=true | 查询 data?type=SNAPSHOT | 该指标不计入板块分数和 Overall Score 分母 | ⬜ |

### 模块 F：Data API (TREND)

| # | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 状态 |
|---|----------|----------|----------|----------|------|
| TC-39 | 基本 data?type=TREND 查询 | 公司有 6 个月数据 | GET /benchmark/company/{id}/data?type=TREND&startDate=2025-09&endDate=2026-02 | 返回 months=[2025-09,...,2026-02]，每月有完整 categories 数据 | ⬜ |
| TC-40 | 默认 data?type=TREND 查询 | 公司 closed month=2026-02 | GET .../data?type=TREND（无其他参数） | startDate=2025-09, endDate=2026-02（默认 6 个月） | ⬜ |
| TC-41 | 自定义时间范围 | 公司有 12 个月数据 | GET .../data?type=TREND&startDate=2025-03&endDate=2026-02 | 返回 12 个月数据 | ⬜ |
| TC-42 | 部分月份无数据 | 6 个月中有 2 个月无数据 | 查询 data?type=TREND | 无数据月份 hasData=false, dimensions=[]；折线图断线 | ⬜ |
| TC-43 | Trend 雷达图两步平均 | ARR Growth: 月1 P=40, 月2 P=50, 月3 P=60 | 查询 data?type=TREND | radarSummary ARR Growth averagePercentile=(40+50+60)/3=50 | ⬜ |
| TC-44 | Trend 多维度 | Actuals+CF, IP+KeyBanc | 查询 data?type=TREND | 每月每指标最多 4 个 dimension，折线图 4 条线 | ⬜ |

### 模块 G：Filter Options API

| # | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 状态 |
|---|----------|----------|----------|----------|------|
| TC-45 | 基本 Filter Options | 公司有 Actuals + Committed Forecast，KeyBanc 有数据 | GET /benchmark/company/{id}/filter-options | ACTUALS enabled=true, CF enabled=true, SGF enabled=false; KEYBANC enabled=true | ⬜ |
| TC-46 | 新建公司 | 公司无任何数据 | 查询 filter-options | latestActualDate=null, defaultDate=当前月 | ⬜ |
| TC-47 | 日期信息完整 | 公司有历史数据 | 查询 filter-options | latestActualDate, earliestDataDate, defaultDate 均正确 | ⬜ |

---

## 二、业务规则验证

| 规则编号 | 规则名称 | 验证方法 | 状态 |
|----------|----------|----------|------|
| BR-04 | Internal Peer 百分位公式 | TC-06, TC-07, TC-08, TC-09, TC-10 覆盖 | ⬜ |
| BR-05 | 外部基准插值 | TC-18~TC-21 覆盖 | ⬜ |
| BR-06 | 仅 P50 规则 | TC-22, TC-23, TC-24 覆盖 | ⬜ |
| BR-07 | Actuals 同行匹配 | TC-01~TC-03 覆盖 | ⬜ |
| BR-08 | Forecast 同行匹配 | TC-11~TC-16 覆盖 | ⬜ |
| BR-09 | 同行回退 | TC-43(E-05) 覆盖 | ⬜ |
| BR-12 | Forecast + 外部基准 | TC-27 覆盖 | ⬜ |
| BR-13~15 | 汇总计算 | TC-32~TC-38 覆盖 | ⬜ |
| BR-16 | 指标排序 | TC-06(升序), TC-07(反向) 覆盖 | ⬜ |
| BR-17 | Runway N/A | TC-28~TC-31 覆盖 | ⬜ |
| BR-18 | 全部相同值 | TC-10 覆盖 | ⬜ |
| BR-27 | 代码整合 | E-09 覆盖 | ⬜ |
| BR-29 | 插值公式 | TC-19 覆盖 | ⬜ |

---

## 三、边界与异常测试

| # | 场景 | 操作 | 预期行为 | 状态 |
|---|------|------|----------|------|
| E-01 | 公司不存在 | GET .../data?type=SNAPSHOT&companyId=invalid-uuid | 404, "Company not found" | ⬜ |
| E-02 | dataSources 为空 | GET ...?dataSources= | 400, "At least one data source required" | ⬜ |
| E-03 | benchmarkSources 为空 | GET ...?benchmarkSources= | 400, "At least one benchmark source required" | ⬜ |
| E-04 | 无效 dataSources 值 | GET ...?dataSources=INVALID | 400, 参数校验失败 | ⬜ |
| E-05 | Trend startDate == endDate | GET .../data?type=TREND&startDate=2026-01&endDate=2026-01 | 400, "Start date must differ from end date" | ⬜ |
| E-06 | Trend startDate > endDate | GET .../data?type=TREND&startDate=2026-06&endDate=2026-01 | 400, "Start date must be before end date" | ⬜ |
| E-07 | 日期格式错误 | GET ...?date=2026-13 | 400, 日期格式校验失败 | ⬜ |
| E-08 | 新建公司无数据 | 公司无 Actual/Forecast 数据 | data?type=SNAPSHOT 返回 200，所有指标 percentile=null, hasData=false | ⬜ |
| E-09 | Benchmark Entry API 不受影响 | 调用 GET /benchmark（Entry CRUD 接口） | Entry CRUD 正常返回，不受 Benchmarking 代码影响 | ⬜ |
| E-10 | 超长 Trend 范围 | GET .../data?type=TREND&startDate=2020-01&endDate=2026-02 | 正常返回（如有时间限制则返回 400） | ⬜ |
| E-11 | BenchmarkDetail P25/P50/P75 格式异常 | Benchmark Entry 中输入 "N/A" 或非数值字符串 | 该维度 percentile=null, percentileDisplay="NA"（优雅降级） | ⬜ |
| E-12 | 公司无 ARR 数据 | 公司该月 ARR 为 null | ARR Growth Rate hasData=false，不影响其他指标 | ⬜ |
| E-13 | ARR Growth 前月无数据 | 目标公司前一个月无 Normalization 数据 | ARR Growth Rate percentile=null | ⬜ |
| E-14 | 无效 type 参数 | GET .../data?type=INVALID | 400, "Invalid view type" | ⬜ |

---

## 四、API 接口验证

| # | 接口 | 方法 | 测试数据 | 预期响应 | 状态码 | 状态 |
|---|------|------|----------|----------|--------|------|
| A-01 | /benchmark/company/{id}/data?type=SNAPSHOT | GET | companyId=有效UUID, 默认参数 | 完整 Snapshot 响应 | 200 | ⬜ |
| A-02 | /benchmark/company/{id}/data?type=SNAPSHOT | GET | dataSources=ACTUALS,COMMITTED_FORECAST&benchmarkSources=INTERNAL_PEERS,KEYBANC | 多维度响应，每指标 4 个 dimension | 200 | ⬜ |
| A-03 | /benchmark/company/{id}/data?type=TREND | GET | startDate=2025-09&endDate=2026-02 | 6 个月 Trend 响应 | 200 | ⬜ |
| A-04 | /benchmark/company/{id}/filter-options | GET | companyId=有效UUID | 返回可用筛选选项 | 200 | ⬜ |
| A-05 | /benchmark/company/invalid/data?type=SNAPSHOT | GET | companyId=不存在 | 错误响应 | 404 | ⬜ |
| A-06 | /benchmark/company/{id}/data?type=TREND | GET | startDate=endDate | 错误响应 | 400 | ⬜ |
| A-07 | /benchmark/company/{id}/data?type=SNAPSHOT | GET | 无 Authorization header | 未授权响应 | 401 | ⬜ |

---

## 五、权限测试

| # | 角色 | 操作 | 预期 | 状态 |
|---|------|------|------|------|
| P-01 | Company User | GET snapshot（自己的公司） | 200, 正常返回 | ⬜ |
| P-02 | Portfolio User | GET snapshot（投资组合内公司） | 200, 正常返回 | ⬜ |
| P-03 | Admin | GET snapshot（任意公司） | 200, 正常返回 | ⬜ |
| P-04 | 未登录用户 | GET snapshot | 401, 未授权 | ⬜ |

---

## 六、性能测试

| # | 检查项 | 预期 | 状态 |
|---|--------|------|------|
| PERF-01 | Snapshot API 响应时间（单维度） | < 2s | ⬜ |
| PERF-02 | Snapshot API 响应时间（12 维度） | < 3s | ⬜ |
| PERF-03 | Trend API 响应时间（6 个月，单维度） | < 3s | ⬜ |
| PERF-04 | Trend API 响应时间（6 个月，12 维度） | < 5s | ⬜ |
| PERF-05 | Filter Options API 响应时间 | < 1s | ⬜ |

---

## 七、测试总结

| 统计项 | 数量 |
|--------|------|
| 总用例数 | 75 |
| 功能测试 | 47 |
| 边界/异常测试 | 14 |
| API 接口验证 | 7 |
| 权限测试 | 4 |
| 性能测试 | 5 |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | 0 |
| 通过率 | — |

### 遗留问题

| # | 问题描述 | 严重程度 | 状态 |
|---|----------|----------|------|
| — | 待实现后执行 | — | — |

### 验收结论

- [ ] 功能验收通过
- [ ] 可以发布到 test 环境

---

## 附录：接口字段变更记录（2026-03-30）

| 变更 | 说明 |
|------|------|
| `overallScore.quartileLabel` | 新增：右上角信息提示 "6 Metrics - Top Quartile" |
| `overallScore.dimensionPoints` | 新增：最多 12 个维度点位 |
| `estimationType` | `BOUNDARY` 拆分为 `BOUNDARY_ABOVE` (>P75) 和 `BOUNDARY_BELOW` (<P25) |
| `categories[].metrics[].dataSourceValues` | 新增：各数据源真实值+货币（SNAPSHOT only） |
| `categories[].metrics[].benchmarkValues` | 新增：外部基准值列表（含全部 Entry 字段，按平台去重） |
| `categories[].metrics[].monthlyData` | 移除：提取到顶层 `monthlyData` |
| `monthlyData` | 新增顶层字段：按维度(DATA×BENCHMARK)→月→指标 组织 |
| `radarSummary` | 结构变更：从指标优先改为维度优先 |
| `ExternalBenchmarkValuesDto` | 补全：新增 platform, edition, metricName, definition, fyPeriod |
| `percentileDisplay` | 格式：`51%ile`, `~64%ile`, `>75%ile`, `<25%ile` |
| 外部基准匹配 | 优先最新 Edition → 匹配 fyPeriod 年份 |
| 同行匹配 | 按月独立匹配，委托 ColleagueCompanyService |
| `Benchmark.it` | 改名为 `Benchmarkit.ai` |
