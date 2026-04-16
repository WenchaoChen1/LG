# Benchmark 技术设计

> v4.0 | 2026-04-09 | 关联需求：docs/Benchmark/01-prd.md
> 完整接口字段文档：[api-documentation.md](api-documentation.md)

## 一、做什么 & 怎么做

**需求**：Finance 模块新增 Benchmarking 页面，将公司 6 个财务指标与内部同行和外部基准（KeyBanc、High Alpha、Benchmarkit.ai）对标，展示百分位排名、趋势折线和雷达图。

**方案**：后端新增聚合查询接口，按 DATA(3)×BENCHMARK(4) 维度组合计算百分位；前端新增 Benchmark 页面，通过筛选器驱动 Snapshot/Trend 两种视图实时渲染。

**改动范围**：

| 模块 | 类型 | 说明 |
|------|------|------|
| `CIOaas-api` / `fi/benchmark/engine/` | 新增 | 百分位计算引擎（4 个 engine 类） |
| `CIOaas-api` / `fi/service/` | 新增 | BenchmarkingService（聚合查询） |
| `CIOaas-api` / `fi/controller/` | 修改 | BenchmarkController 新增 data / filter-options 端点 |
| `CIOaas-api` / `fi/benchmark/vo/` | 新增 | 请求/响应 DTO（~25 个类） |
| `CIOaas-web` / `companyFinance/benchmark/` | 新增 | 前端页面（FilterBar、OverallScoreBar、RadarChart、TrendLineChart） |
| `CIOaas-web` / `services/api/companyFinance/` | 新增 | benchmarkService.ts、benchmarkAdapters.ts |

---

## 二、接口设计

> 详细字段说明见 `api-documentation.md`。

### API-01：获取 Benchmark 对标数据

`GET /benchmark/company/{companyId}/data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyId | path String | 是 | 公司 ID |
| type | query String | 否 | SNAPSHOT（默认）/ TREND |
| date | query String | 否 | yyyy-MM，SNAPSHOT 用；默认 the last closed month |
| startDate | query String | 否 | yyyy-MM，TREND 用；默认 endDate 前 5 个月 |
| endDate | query String | 否 | yyyy-MM，TREND 用；默认 the last closed month |
| dataSources | query String[] | 否 | ACTUALS（默认）、COMMITTED_FORECAST、SYSTEM_GENERATED_FORECAST |
| benchmarkSources | query String[] | 否 | INTERNAL_PEERS（默认）、KEYBANC、HIGH_ALPHA、BENCHMARK_IT |

**返回结构**（顶层）：

```
Result<BenchmarkDataResponse> {
  companyId, companyName, type, months[]
  peerGroupInfo      — 同行匹配信息（peerCount, isFallback, fallbackMessage）
  overallScore       — 综合评分（percentile, quartile, quartileLabel, dimensionPoints[], estimationMessage）
  categories[]       — 4 个板块（score, metrics[], dimensionPoints[]）
  radarSummary       — 雷达图数据（dimensions[] × metrics[]）
  dimensionSummary[] — Overall 进度条点位（最多 12 个 DATA×BENCHMARK 维度）
  companyArr, companyArrSource, companyArrMonth
}
```

**错误情况**：
- companyId 不存在 → 404 EntityNotFoundException
- 公司无任何财务数据 → 200，overallScore.percentile = null，categories 全为 N/A

### API-02：获取筛选项

`GET /benchmark/company/{companyId}/filter-options`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyId | path String | 是 | 公司 ID |

**返回结构**：

```
Result<BenchmarkFilterOptionsResponse> {
  availableDataSources[]      — 可用的 DATA 选项（含 disabled 标记）
  availableBenchmarkSources[] — 可用的 BENCHMARK 选项
  defaultDate                 — the last closed month
  hasPeerGroup               — 是否有自定义同行组
  companyActive              — 公司是否活跃（false = 僵尸公司：已退出/关闭或无 Portfolio）
}
```

### API-03 ~ API-07：Benchmark Entry CRUD（已有）

| 编号 | 方法 | 路径 | 说明 |
|------|------|------|------|
| API-03 | GET | `/benchmark/metrics` | 获取 Category → Metric → Detail 树 |
| API-04 | POST | `/benchmark/details` | 新增外部基准数据行 |
| API-05 | PUT | `/benchmark/details/{detailId}` | 修改外部基准数据行 |
| API-06 | DELETE | `/benchmark/details/{detailId}` | 删除外部基准数据行 |
| API-07 | PUT | `/benchmark/metrics/{metricId}/formula` | 更新 LG 公式 |

---

## 三、数据设计

**无新建表**。Benchmark 对标功能为纯计算+查询，依赖以下已有表：

| 编号 | 表名 | 用途 |
|------|------|------|
| TBL-01 | `financial_benchmark_entry` | 外部基准数据（P25/P50/P75、Platform、Edition、Segment） |
| TBL-02 | `financial_normalization_current` | 公司财务标准化数据（6 个指标的源数据） |
| TBL-03 | `financial_growth_rate` | 公司增长率数据（ARR、MRR，用于同行匹配和 ARR 分段） |
| TBL-04 | `invite` | 公司基本信息（Type、Stage、会计方法） |
| TBL-05 | `r_company_stages` | 公司阶段关联 |
| TBL-06 | `r_company_group` | 手动同行组绑定关系 |

**TBL-01 关键字段**（已有，不新建）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | varchar(36) | UUID 主键 |
| platform | varchar(100) | KeyBanc / High Alpha / Benchmarkit.ai |
| edition | varchar(50) | 版本/年份 |
| metric_id | varchar(36) | 关联 LG 指标 |
| fy_period | varchar(10) | 财年（如 "2026"） |
| segment_type | varchar(50) | "ARR" |
| segment_value | varchar(100) | ARR 范围（如 "$1M - $5M"） |
| p25 | varchar(50) | 第 25 百分位值 |
| median | varchar(50) | 中位数（P50） |
| p75 | varchar(50) | 第 75 百分位值 |
| best_guess | varchar(200) | 公式信心标签 |

---

## 四、核心逻辑

### 4.1 主请求流程（API-01）

```
请求进入 → 解析 ViewType（SNAPSHOT / TREND）
  → 确定月份列表（SNAPSHOT=1月, TREND=N月）
  → 对每个月 × 每个 dataSource：
      → PeerGroupResolver 解析同行组（缓存 key=dataSource|month）
  → 对每个 metric（6 个）：
      → MetricExtractor 提取公司指标值
      → 对每个维度（DATA × BENCHMARK，最多 12 个）：
          ├─ INTERNAL_PEERS → InternalPercentileCalculator
          └─ EXTERNAL → ExternalPercentileCalculator
      → 聚合维度百分位（多月时取月均值）
  → 组装响应：
      ├─ buildCategories()        — 4 板块 × 指标百分位
      ├─ buildOverallScore()      — 板块分数算术平均
      ├─ buildDimensionSummary()  — 12 维度点位
      └─ buildRadarSummary()      — 6 轴 × 维度
```

### 4.2 同行匹配（PeerGroupResolver）

1. 查公司是否有手动绑定同行组 → 有效（≥3 家活跃）则使用
2. 否则系统匹配，**6 维度同时满足**：
   - 公司类型相同、阶段相同、会计方法相同
   - ARR 规模同一区间：[$1,$250K) / [$250K,$1M) / [$1M,$5M) / [$5M,$20M] / ($20M,+∞)
   - 数据质量：24 月窗口内连续 6 月非负 gross revenue
   - 排除状态：Exited / Shut Down / Inactive
3. 有效同行 < 3 家 → 回退到全平台所有活跃公司，isFallback=true

**注意**：同行组按 month×dataSource 缓存，因为 ARR 分段随月份变化。

### 4.3 内部百分位计算（Nearest Rank）

输入：公司值、同行值列表、isReverse
1. 合并公司值到同行列表，N = 总数
2. N=1 → P100
3. 排序（正向=升序，反向=降序；仅 Sales Efficiency Ratio 为反向）
4. 全部值相同 → totalTie=true，排除出板块/Overall 计分
5. Standard Competition Ranking：相同值同排名，下一值跳排名
6. **P = (R-1)/(N-1) × 100**，四舍五入 2 位小数

### 4.4 外部百分位计算（线性插值 + 边界处理）

输入：公司值、外部基准 P25/P50/P75（可能缺失）、isReverse

按可用基准点分 Case：

| Case | 可用点 | 值 > 上界 | 值 < 下界 | 区间内 |
|------|--------|-----------|-----------|--------|
| A | P25+P50+P75 | >P75 → P100 | <P25 → P0 | 线性插值 ~P |
| B | 仅 P50 | >P50 → P75 | <P50 → P25 | =P50 → P50 |
| C | P25+P50 | >P50 → P75 | <P25 → P0 | 插值 |
| D | P50+P75 | >P75 → P100 | <P50 → P25 | 插值 |

插值公式：`~P = P_low + (P_high - P_low) × (value - D_low) / (D_high - D_low)`

反向指标：内部 swap P25↔P75，比较逻辑取反。

估算提示：插值 → "interpolated values used"；边界 → "boundary values used"；两者都有 → "interpolated values & boundary values used"

### 4.5 Monthly Runway 特殊分类

| Cash | Burn | 分类 | 百分位 |
|------|------|------|--------|
| ≥0 | ≥0 | TOP_RANK | P100 |
| ≥0 | <0 | CALCULATED | 按公式正常计算 |
| <0 | >0 | WORST_NEGATIVE_ZERO | P0 |
| <0 | =0 | WORST_NEGATIVE_ZERO | P0 |
| =0 | <0 | CALCULATED | Runway=0，进入排名 |
| <0 | <0 | BOTTOM_RANK | P0 |
| =0 | =0 | TOP_RANK | P100 |

排名优先级：WORST_NEGATIVE_ZERO < BOTTOM_RANK < CALCULATED < TOP_RANK

### 4.6 分数聚合

- **板块分数** = 该板块所有有效指标（hasData=true 且非 totalTie）全维度百分位的算术平均
- **Overall Score** = 4 个板块分数的算术平均（N/A 板块排除，分母减 1）
- **维度点位** = 该 DATA×BENCHMARK 下 6 个指标百分位的算术平均
- **雷达图 SNAPSHOT** = 单月各指标各维度百分位
- **雷达图 TREND** = 各月百分位的算术平均

---

## 五、前端设计

### 5.1 路由

```
/companyFinance/benchmark → companyFinance/benchmark/Index.tsx
```

嵌套在 Finance 模块的 Benchmarking Tab 下，与 Overview、Financial Statements、Performance 同级。

### 5.2 组件树

```
Index.tsx                    — Snapshot/Trend 切换容器
├── FilterBar.tsx            — 4 筛选卡片 (VIEW/FILTER/DATA/BENCHMARK) + 日历
├── OverallScoreBar.tsx      — Overall Score 进度条 + 维度点位 + 4 板块卡片
│   └── MetricPercentileBar  — 单指标分布条 + Show All/Hide
├── TrendLineChart.tsx       — Trend 折线图 (ECharts)
└── RadarChart.tsx           — 6 轴雷达图 (ECharts)
```

### 5.3 状态管理

`useBenchmarkData.ts`（useReducer Hook），页面级状态不走 DVA。

State 关键字段：viewMode、selectedDataSources[]、selectedBenchmarkSources[]、selectedCategories[]、selectedDate/DateRange、data、trendData、filterOptions、loading

数据流：筛选变更 → dispatch → useEffect 调 API → 更新 state → 组件重渲染

### 5.4 API 对接

| 文件 | 作用 |
|------|------|
| `benchmarkService.ts` | 封装 API-01、API-02 调用 |
| `benchmarkAdapters.ts` | API 枚举 ↔ 前端类型适配（ACTUALS↔Actuals, INTERNAL_PEERS↔InternalPeers 等） |

### 5.5 权限

复用 Finance 模块现有权限体系，无额外权限控制。

---

## 六、风险 & 待定

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | 默认 BENCHMARK：PRD 写 Internal Peers，后端实现为全选 | 首屏数据量差异 | 与产品确认后统一 |
| 2 | 12维度×6指标×N月计算在大同行组时可能慢 | 响应时间 | 已有 request-scoped 缓存；监控后按需加 Redis |
| 3 | 外部基准 Segment 匹配依赖 Benchmark Entry 数据质量 | 无匹配时返回 N/A | 前端已处理 N/A 展示 |

---

## 七、工作量

| 任务 | 大小 | 依赖 |
|------|------|------|
| 后端：百分位计算引擎（4 engine） | L | — |
| 后端：BenchmarkingService 聚合 | L | 计算引擎 |
| 后端：Controller + VO | M | Service |
| 后端：同行匹配增强 | M | — |
| 前端：FilterBar | M | API-02 |
| 前端：OverallScoreBar + MetricPercentileBar | L | API-01 |
| 前端：TrendLineChart | M | API-01 |
| 前端：RadarChart | M | API-01 |
| 前端：useBenchmarkData + Adapters | M | API-01/02 |
| 联调 + 边界验证 | L | 全部 |

> S=半天 | M=1天 | L=2天+
