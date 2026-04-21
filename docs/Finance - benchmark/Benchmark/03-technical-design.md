# Benchmark 技术设计

> v5.0 | 2026-04-13 | 关联需求：docs/Benchmark/01-prd.md
> 关联重构：docs/Benchmark/refactor-design.md
> 完整接口字段文档：[api-documentation.md](api-documentation.md)

## 一、做什么 & 怎么做

**需求**：Finance 模块的 Benchmarking 页面，将公司 6 个财务指标与内部同行和外部基准（KeyBanc、High Alpha、Benchmarkit.ai）对标，展示百分位排名、趋势折线和雷达图。

**方案（2026-04 重构后）**：
- **后端**：只返回原始值（公司 + 同行 + 外部基准 P25/P50/P75）。
- **前端**：所有百分位计算 + 聚合逻辑由前端执行。FILTER 切换只触发前端重聚合，不触发 API。

**改动范围**：

| 模块 | 类型 | 说明 |
|------|------|------|
| `CIOaas-api` / `fi/benchmark/vo/` | 精简 | 新增 `BenchmarkRawDataResponse` + 4 个子 DTO；删除 12 个聚合 DTO |
| `CIOaas-api` / `fi/service/BenchmarkingServiceImpl` | 重构 | 从 1159 行精简到 443 行；只做原始值提取 + 外部基准匹配 |
| `CIOaas-api` / `fi/benchmark/engine/` | 保留 | `InternalPercentileCalculator` / `ExternalPercentileCalculator` 保留为 `@Component`，供通知系统等未来业务复用 |
| `CIOaas-api` / `fi/benchmark/engine/MetricExtractor` | 新增方法 | `extractCash()` — 提供 Runway 分类所需的 cash 值 |
| `CIOaas-web` / `companyFinance/benchmark/calc/` | 新增 | 7 个纯函数模块：类型、指标元数据、数字解析、内部百分位、Runway 分类、外部百分位、聚合 |
| `CIOaas-web` / `services/api/companyFinance/` | 重构 | service 只 fetch 原始数据；adapter 消费 `aggregate()` 输出转换为 UI 形状 |
| `CIOaas-web` / `hooks/useBenchmarkData.ts` | 重构 | 存 raw + `useMemo` 派生 view；FILTER 切换 0 网络请求 |

---

## 二、接口设计

> 详细字段说明见 `api-documentation.md`。

### API-01：获取 Benchmark 原始数据

`GET /benchmark/company/{companyId}/data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyId | path String | 是 | 公司 ID |
| type | query String | 否 | SNAPSHOT（默认）/ TREND |
| date | query String | 否 | yyyy-MM，SNAPSHOT 用；默认 closed month |
| startDate | query String | 否 | yyyy-MM，TREND 用；默认 endDate 前 5 个月 |
| endDate | query String | 否 | yyyy-MM，TREND 用；默认 closed month |
| dataSources | query String[] | 否 | ACTUALS（默认）、COMMITTED_FORECAST、SYSTEM_GENERATED_FORECAST |
| benchmarkSources | query String[] | 否 | INTERNAL_PEERS（默认）、KEYBANC、HIGH_ALPHA、BENCHMARK_IT |

**返回结构**：

```
Result<BenchmarkRawDataResponse> {
  companyId, companyName, type, months[]
  dataSources[], benchmarkSources[]              — 回显生效值
  peerGroupInfo                                  — 同行匹配信息
  peers[]                                        — 去重后的同行元数据 (peerId, peerName)
  companyArr, companyArrSource, companyArrMonth
  companyMetrics[]                               — 公司原始值 (month × dataSource × 6 指标 + cash)
  peerMetrics[]                                  — 同行原始值 (month × dataSource × peerId × 6 指标 + cash)
  externalBenchmarks[]                           — 外部基准 (year × benchmarkSource × metric) × {found, values}
}
```

**错误情况**：
- companyId 不存在 → 404 DataNotFoundException
- 公司无任何财务数据 → 200，metric 数组均为 null

### API-02：获取筛选项

`GET /benchmark/company/{companyId}/filter-options`

返回 `BenchmarkFilterOptionsResponse` — 与重构前一致。

### API-03 ~ API-07：Benchmark Entry CRUD（已有，不变）

| 编号 | 方法 | 路径 | 说明 |
|------|------|------|------|
| API-03 | GET | `/benchmark/metrics` | 获取 Category → Metric → Detail 树 |
| API-04 | POST | `/benchmark/details` | 新增外部基准 |
| API-05 | PUT | `/benchmark/details/{detailId}` | 修改外部基准 |
| API-06 | DELETE | `/benchmark/details/{detailId}` | 删除外部基准 |
| API-07 | PUT | `/benchmark/metrics/{metricId}/formula` | 更新 LG 公式 |

---

## 三、数据设计

**无新建表**。依赖已有表：

| 编号 | 表名 | 用途 |
|------|------|------|
| TBL-01 | `financial_benchmark_entry` | 外部基准数据（P25/P50/P75、Platform、Edition、Segment） |
| TBL-02 | `financial_normalization_current` | 公司/同行财务标准化数据（6 指标 + cash；Forecast 用 data_type=1/2） |
| TBL-03 | `financial_growth_rate` | Actual 数据的 ARR 溯源（同行匹配用） |
| TBL-04 | `invite` | 公司基本信息（Type、Stage、会计方法） |
| TBL-05 | `r_company_stages` | 公司阶段关联 |
| TBL-06 | `r_company_group` | 手动同行组绑定 |

---

## 四、核心逻辑

### 4.1 后端请求流程（API-01，重构后）

```
请求进入 → 解析 ViewType / dataSources / benchmarkSources
  → 确定月份列表
  → 对每个月 × 每个 dataSource：
      → PeerGroupResolver 解析同行组（缓存 key=dataSource|month）
  → 对每个月 × 每个 dataSource：
      → MetricExtractor 提取公司 6 指标原始值 + cash
      → 对每个同行：提取 6 指标原始值 + cash
  → 对每年 × 每个外部 benchmarkSource × 每个指标：
      → matchBenchmarkDetail(platform, year, segmentType=ARR, segmentValue 匹配公司 ARR 区段)
  → 组装扁平响应（不做任何百分位计算、不做任何聚合）
```

**关键**：后端响应路径**不调用** `InternalPercentileCalculator` / `ExternalPercentileCalculator`。这两个类保留为 `@Component`，供其他业务（如未来通知系统）使用。

### 4.2 同行匹配（PeerGroupResolver，不变）

1. 手动同行组优先（≥3 家活跃）
2. 系统匹配 6 维度：类型、阶段、会计方法、ARR 规模、数据质量、排除条件
3. 有效同行 < 3 家 → 回退全平台活跃公司
4. Actual / Forecast 分流：Actual 用实际 ARR、Forecast 用预测 ARR；Forecast 有效数据锚点为最后有非负 revenue 的预测月

### 4.3 前端计算层（calc/ 模块）

前端消费扁平响应后，按以下顺序计算：

```
1. 对每个 metric × 每个 DATA×BENCHMARK 维度 × 每个月：
   ├─ INTERNAL_PEERS → computeInternalPercentile / computeRunwayPercentile (Nearest Rank)
   └─ EXTERNAL → computeExternalPercentile (4 Case 分支)
2. 多月聚合（TREND）→ 维度月均百分位
3. 板块分数 = 板块内有效指标全维度百分位的算术平均
4. Overall Score = 选中板块（FILTER）分数的算术平均
5. 维度点位 = DATA×BENCHMARK 下 6 指标百分位的算术平均（不受 FILTER 影响）
6. 雷达图 = 6 指标 × 维度（不受 FILTER 影响，永远全部指标）
```

### 4.4 内部百分位算法（calc/percentile.ts）

镜像后端 `InternalPercentileCalculator`：
1. N=1 → P100
2. 全相同 → `totalTie`，排除出计分
3. 排序（反向指标降序）
4. Standard Competition Ranking
5. `P = (R-1)/(N-1) × 100`，四舍五入 2 位小数

### 4.5 Monthly Runway 分类（calc/runway.ts）

| Cash | Burn | 分类 | 百分位 |
|------|------|------|--------|
| ≥0 | ≥0 | TOP_RANK | P100 |
| ≥0 | <0 | CALCULATED | 按 -(cash/burn) 计算 |
| <0 | >0 | WORST_NEGATIVE_ZERO | P0 |
| <0 | =0 / =0 & <0 | WORST_NEGATIVE_ZERO / CALCULATED | P0 / 进入计算 |
| <0 | <0 | BOTTOM_RANK | P0 |
| =0 | =0 | TOP_RANK | P100 |

排名优先级：WORST_NEGATIVE_ZERO < BOTTOM_RANK < CALCULATED < TOP_RANK

### 4.6 外部百分位算法（calc/externalPercentile.ts）

按可用基准点分 Case：

| Case | 可用点 | 值 > 上界 | 值 < 下界 | 区间内 |
|------|--------|-----------|-----------|--------|
| A | P25+P50+P75 | >P75 → P100 | <P25 → P0 | 线性插值 |
| B | 仅 P50 | >P50 → P75 | <P50 → P25 | 精确 P50 |
| C | P25+P50 | >P50 → P75 | <P25 → P0 | 插值 |
| D | P50+P75 | >P75 → P100 | <P50 → P25 | 插值 |

反向指标（Sales Efficiency Ratio）：内部 swap `P25 ↔ P75`。

### 4.7 FILTER 行为

| 区域 | FILTER 影响？ | 实现 |
|------|--------------|------|
| 4 个板块显示/隐藏 | ✅ | `categories[].visible` 派生自 selectedCategories |
| Overall Benchmark Score | ✅ | 只聚合 visible 板块 |
| 指标分布条 | ✅ | 前端过滤 |
| Metrics Summary 雷达图 | ❌ | 永远用全部 6 指标 |

FILTER 切换只重新调用 `useMemo(() => aggregate(raw, selectedCategories))`，**不触发网络请求**。

---

## 五、前端设计

### 5.1 路由

`/companyFinance/benchmark` → `Index.tsx`，嵌在 Finance 模块 Benchmarking Tab。

### 5.2 calc/ 模块目录

```
src/pages/companyFinance/benchmark/calc/
├── types.ts              — 类型定义（镜像后端响应）
├── metrics.ts            — 6 指标元数据 + 4 板块元数据
├── numberParse.ts        — P25/P50/P75 字符串解析 + 百分位展示格式化
├── percentile.ts         — 内部 Nearest Rank 算法
├── runway.ts             — Monthly Runway 8 象限分类
├── externalPercentile.ts — 外部线性插值 + 边界 + 反向指标
├── aggregate.ts          — 聚合入口 (category/overall/dimension/radar)
└── index.ts              — 统一导出
```

### 5.3 组件树（不变）

```
Index.tsx
├── FilterBar.tsx
├── OverallScoreBar.tsx
│   └── MetricPercentileBar
├── TrendLineChart.tsx
└── RadarChart.tsx
```

### 5.4 状态管理

`useBenchmarkData` Hook：
- State 持有 `snapshotRaw` / `trendRaw`（原始响应）+ UI 筛选状态
- `useMemo` 派生 view：`aggregate(raw, selectedCategories) → AggregatedView → legacy UI shape`
- fetch 依赖：`viewMode, selectedDataSources, selectedBenchmarkSources, selectedDate/Range`
- **FILTER 变化不在 fetch 依赖中** — 触发 useMemo 重聚合即可

### 5.5 Adapter 层

`benchmarkAdapters.ts`：
- `adaptFilterOptionsPayload()`：filter-options 响应适配
- `buildBenchmarkRequestSourceParams()`：DATA/BENCHMARK 枚举映射
- `adaptRawToSnapshotResponse()`：`BenchmarkRawData + selectedCategories → BenchmarkResponseData`（调用 calc.aggregate）
- `adaptRawToTrendBundle()`：返回 `{benchmark, trend, radarSummary}`

---

## 六、风险 & 待定

| # | 问题 | 应对 |
|---|------|------|
| 1 | 前端算法精度偏差 | calc/ 模块为纯函数，可对比后端 JSON fixture 做单测验证 |
| 2 | 响应体变大（原始值 × 同行 × 月份） | TREND 最坏 ~1MB；开启 Spring Boot gzip 后 <200KB |
| 3 | 大同行组下前端聚合耗时 | `useMemo` 缓存；必要时 Web Worker |
| 4 | 默认 BENCHMARK 值：PRD 写 Internal Peers，实现默认全选 | 与产品确认 |

---

## 七、规范对齐

**后端**（CIOaas-api/.claude/standards）：
- DTO：`@Data @Builder @NoArgsConstructor @AllArgsConstructor`
- 响应包装：`Result.success(data)`
- DI：`@Resource`
- 读操作：`@Transactional(readOnly = true)`（类级注解继承）

**前端**（CIOaas-web/standards）：
- `calc/*.ts` 为纯函数模块，无 React / DVA 依赖
- 类型集中在 `calc/types.ts`（扁平响应）+ `types.ts`（UI 视图）
- `useReducer` 管理 UI 状态，`useMemo` 派生计算视图

---

## 八、工作量（重构已完成）

| 任务 | 状态 |
|------|------|
| 后端 DTO 新增 + 旧 DTO 删除（12 个） | ✅ |
| `BenchmarkingServiceImpl.getData` 重构 | ✅ |
| `MetricExtractor.extractCash` | ✅ |
| 前端 calc/ 模块（7 文件，~900 行） | ✅ |
| Service / Adapter / Hook 重构 | ✅ |
| 组件兼容（UI 形状不变） | ✅ 无需改 |
| 文档更新 | ✅ |

**后端验收**：Maven 编译成功（BUILD SUCCESS）。
**前端验收**：TypeScript 编译通过（除 2 个预存在的无关错误外）。
