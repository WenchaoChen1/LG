# Benchmark Portfolio Intelligence — API 接口文档

> 关联 TDD：03-technical-design.md
> 基础路径：`/web/portfolio-benchmark`
> 认证：Bearer Token（仅 admin 角色，roleType ≤ 2）
> 公司列表：使用系统已有 Portfolio Companies 接口，本功能不新建

---

## API-01：Snapshot 数据查询

`POST /web/portfolio-benchmark/snapshot`

### 请求体

```json
{
  "companyIds": ["comp-001", "comp-002", "comp-003"],  // String[]  要对标的公司 ID 列表，至少 1 个
  "date": "2025-01",                                    // String    yyyy-MM，默认当前月份
  "page": 1,                                            // Integer   页码，从 1 开始，默认 1
  "size": 10                                            // Integer   每页公司数，默认 10
}
```

> 后端始终返回**全量** 3 DataSources × 4 BenchmarkSources 的数据，DATA / BENCHMARK 筛选由前端本地执行，无需传参。

### 响应体

```json
{
  "code": 200,                                          // Integer   响应状态码，200 表示成功
  "message": "success",                                 // String    响应消息
  "data": {                                             // Object    业务数据
    "companies": [                                      // Array     当前页的公司列表，按公司名 A-Z 排序
      {
        "companyId": "comp-001",                        // String    公司 ID
        "companyName": "Accelerist",                    // String    公司名称
        "companyLogo": "https://...",                   // String    公司 Logo URL，无则为 null
        "benchmarkGroups": [                            // Array     该公司的基准分组列表，按 Internal Peers → KeyBanc → High Alpha → Benchmarkit 排序
          {
            "benchmarkSource": "INTERNAL_PEERS",        // String    基准源枚举：INTERNAL_PEERS / KEYBANC / HIGH_ALPHA / BENCHMARK_IT
            "edition": null,                            // String    外部基准版本年份如 "2025"（取自匹配 entry.edition 列）；INTERNAL_PEERS 固定为 null
            "peerInfo": {                               // Object    同行组信息；仅 INTERNAL_PEERS 有值，外部基准为 null
              "peerCount": 15,                          // Integer   同行公司数量（不含目标公司本身）
              "isFallback": false,                      // Boolean   是否回退到全平台基准（同行 < 3 家时）
              "fallbackMessage": null                   // String    回退提示文案；isFallback=false 时为 null
            },
            "dataTypeRows": [                           // Array     数据类型子行，按 Actuals → Committed Forecast → System Generated Forecast 排序
              {
                "dataType": "ACTUALS",                  // String    数据类型枚举：ACTUALS / COMMITTED_FORECAST / SYSTEM_GENERATED_FORECAST
                "metrics": {                            // Object    6 个指标的百分位结果，key = MetricEnum 名
                  "ARR_GROWTH_RATE": {                  // Object    ARR 增长率
                    "value": 0.35,                      // Number    原始指标值（Number）；无数据时为 null
                    "formattedValue": "35.00%",         // String    格式化展示值；无数据时为 "N/A"
                    "percentile": 56.0,                 // Number    百分位数值（0-100）；无数据时为 null
                    "percentileDisplay": "P56",         // String    百分位展示文本："P56" / "~P62" / ">P75" / "<P25" / "N/A"
                    "estimationType": "EXACT"           // String    EXACT / INTERPOLATED / BOUNDARY_ABOVE / BOUNDARY_BELOW / MEDIAN_ONLY；无数据为 null
                  },
                  "GROSS_MARGIN": { "value": 0.72, "formattedValue": "72.00%", "percentile": 80.0, "percentileDisplay": "P80", "estimationType": "EXACT" },
                  "MONTHLY_NET_BURN_RATE": {            // Object    月净烧钱率
                    "value": "-50000.00",               // ★ String  金额字段返回为 String（避免 JS 大数精度丢失）；无数据时为 null
                    "formattedValue": "-$50,000.00",
                    "percentile": 45.0,
                    "percentileDisplay": "P45",
                    "estimationType": "EXACT"
                  },
                  "MONTHLY_RUNWAY": { "value": 24.5, "formattedValue": "24.5", "percentile": 70.0, "percentileDisplay": "P70", "estimationType": "EXACT" },
                  "RULE_OF_40": {                       // Object    Rule of 40
                    "value": "0.42",                    // ★ String  比率字段返回为 String；无数据时为 null
                    "formattedValue": "42.00%",
                    "percentile": 65.0,
                    "percentileDisplay": "P65",
                    "estimationType": "EXACT"
                  },
                  "SALES_EFFICIENCY_RATIO": { "value": 1.2, "formattedValue": "1.20", "percentile": 30.0, "percentileDisplay": "P30", "estimationType": "EXACT" }
                },
                "tooltipData": {                        // Object    Benchmark 列 Tooltip 的参考百分位值；key = MetricEnum 名
                  "ARR_GROWTH_RATE": [                  // Array     Internal Peers 固定 5 个点（P0/P25/P50/P75/P100），External 固定 3 个点（P25/P50/P75）
                    {
                      "label": "P0",                    // String    百分位标签
                      "percentile": 0,                  // Number    百分位数值
                      "value": 0.05,                    // Number/String  参考指标值（类型与 metrics[].value 一致）；N/A 时为 null
                      "formattedValue": "5.00%"         // String    格式化展示值；N/A 时为 "N/A"
                    },
                    { "label": "P25",  "percentile": 25,  "value": 0.15, "formattedValue": "15.00%" },
                    { "label": "P50",  "percentile": 50,  "value": 0.30, "formattedValue": "30.00%" },
                    { "label": "P75",  "percentile": 75,  "value": 0.50, "formattedValue": "50.00%" },
                    { "label": "P100", "percentile": 100, "value": 0.85, "formattedValue": "85.00%" }
                  ],
                  "GROSS_MARGIN": [ /* 同上结构 */ ],
                  "MONTHLY_NET_BURN_RATE": [            // value 为 String
                    { "label": "P0",   "percentile": 0,   "value": "-100000.00", "formattedValue": "-$100,000.00" },
                    { "label": "P25",  "percentile": 25,  "value": "-50000.00",  "formattedValue": "-$50,000.00" }
                    /* ... */
                  ]
                }
              },
              {
                "dataType": "COMMITTED_FORECAST",       // 第二个数据类型子行
                "metrics": { /* 同上结构 */ },
                "tooltipData": { /* 同上结构 */ }
              }
            ]
          },
          {
            "benchmarkSource": "KEYBANC",               // 第二个基准分组（外部基准）
            "edition": "2025",                          // 外部基准版本年份（匹配到的 benchmark_entry.edition）
            "peerInfo": null,                           // 外部基准无同行组信息
            "dataTypeRows": [
              {
                "dataType": "ACTUALS",
                "metrics": {
                  "ARR_GROWTH_RATE": { "value": 0.35, "formattedValue": "35.00%", "percentile": 62.5, "percentileDisplay": "~P63", "estimationType": "INTERPOLATED" }
                  /* 其他指标同上结构 */
                },
                "tooltipData": {                        // 外部基准 Tooltip 只有 3 个点
                  "ARR_GROWTH_RATE": [
                    { "label": "P25", "percentile": 25, "value": 0.15, "formattedValue": "15.00%" },
                    { "label": "P50", "percentile": 50, "value": 0.30, "formattedValue": "30.00%" },
                    { "label": "P75", "percentile": 75, "value": 0.50, "formattedValue": "50.00%" }
                  ]
                }
              }
            ]
          }
        ]
      }
    ],
    "pagination": {                                     // Object    分页信息（按公司分页）
      "page": 1,                                        // Integer   当前页码
      "size": 10,                                       // Integer   每页公司数
      "total": 25                                       // Integer   符合条件的公司总数
    }
  }
}
```

### 前端使用提示

```javascript
// 按 companyId 分组已天然完成（companies 数组）
// 前端按 FILTER 选择筛选指标可见性，基于可见指标在前端计算 Overall Benchmark Score：
const visibleMetricKeys = getVisibleMetricsByFilter(filter);  // 如 FILTER=GROWTH → ['ARR_GROWTH_RATE']
const overallScore = (dataTypeRow) => {
  const percentiles = visibleMetricKeys
    .map(k => dataTypeRow.metrics[k]?.percentile)
    .filter(p => p != null);
  return percentiles.length > 0
    ? Math.round(percentiles.reduce((a, b) => a + b, 0) / percentiles.length)
    : null;
};
```

### 特殊情况处理

| 场景 | 处理 |
|------|------|
| 公司无某 dataType 数据 | 该 dataTypeRow 中所有 metric 的 value=null, percentileDisplay="N/A" |
| 外部基准无匹配 entry | 该 benchmarkGroup 下所有 metric percentile=null, percentileDisplay="N/A"；Monthly Runway 也不应用分类覆盖 |
| Internal Peers peer < 3 | peerInfo.isFallback=true，使用全平台基准计算百分位 |
| Internal Peers 所有值相同（totalTie） | 百分位 percentileDisplay="N/A"；**tooltipData 5 个位置也全部 N/A** |
| Monthly Runway 特殊分类 | 外部有 entry 时：TOP_RANK → P100，BOTTOM_RANK / WORST_NEGATIVE_ZERO → P0；外部无 entry 时 N/A |

### Tooltip 百分位匹配规则（Standard Competition Ranking）

对每个 P ∈ {0, 25, 50, 75, 100}：
1. 计算 target rank `R = round((P × (N-1) / 100) + 1)`
2. 在已排序的值列表上用 SCR 赋 rank（并列值共享同 rank，下一个唯一值的 rank 会跳过）
3. 查找是否有元素的 SCR rank 等于 target R；存在则取对应值，不存在（被并列跳过）则 N/A
4. 若 `N == 1`，只有 P100 显示该值，其他 N/A
5. 若 `N == 0` 或 totalTie（所有值相等），5 个位置都 N/A

例：N=4，值 `[-949, 56, 100, 100]`，SCR ranks `[1, 2, 3, 3]`
- P0 → R=1 → `-949%`
- P25 → R=round(1.75)=2 → `56%`
- P50 → R=round(2.5)=3 → `100%`
- P75 → R=round(3.25)=3 → `100%`
- P100 → R=4 → **N/A**（rank 4 被并列跳过）

### 格式化规则

| 指标 | value 类型 | 单位 | 格式 | isReverse | 示例 |
|------|-----------|------|------|-----------|------|
| ARR Growth Rate | Number | % | 两位小数 + "%" | false | "35.00%" |
| Gross Margin | Number | % | 两位小数 + "%" | false | "72.00%" |
| **Monthly Net Burn Rate** | **String** | USD | "$" + 千分位 + 两位小数 | false | "-$50,000.00" |
| Monthly Runway | Number | months | 一位小数 | false | "24.5" |
| **Rule of 40** | **String** | % | 两位小数 + "%" | false | "42.00%" |
| Sales Efficiency Ratio | Number | ratio | 两位小数 | true | "1.20" |

---

## API-02：Trend 数据查询

`POST /web/portfolio-benchmark/trend`

### 请求体

```json
{
  "companyIds": ["comp-001", "comp-002"],               // String[]  要对标的公司 ID 列表，至少 1 个
  "startDate": "2024-08",                               // String    起始月份 yyyy-MM；默认为 endDate 往前 5 个月
  "endDate": "2025-01"                                  // String    结束月份 yyyy-MM；默认当前月份；必须 > startDate
}
```

> 同 Snapshot：后端返回全量 DATA / BENCHMARK，前端本地筛选。

### 响应体

```json
{
  "code": 200,                                          // Integer   响应状态码
  "message": "success",                                 // String    响应消息
  "data": {                                             // Object    业务数据
    "months": [                                         // Array     有序月份列表（yyyy-MM），与 series 中数组索引对齐
      "2024-08", "2024-09", "2024-10",
      "2024-11", "2024-12", "2025-01"
    ],
    "companies": [                                      // Array     图例公司列表，按公司名 A-Z 排序
      { "companyId": "comp-001", "companyName": "Accelerist" },
      { "companyId": "comp-002", "companyName": "Brokerage Engine LLC" }
    ],
    "charts": [                                         // Array     扁平图表列表，按 指标 → Benchmark → DataType 顺序
      {
        "metricKey": "ARR_GROWTH_RATE",                 // String    MetricEnum 枚举名，前端按此字段分组渲染卡片
        "metricName": "ARR Growth Rate",                // String    指标展示名称
        "categoryId": "cat-revenue-growth",             // String    分类 ID，前端用于 FILTER 映射
        "benchmarkSource": "INTERNAL_PEERS",            // String    基准源枚举
        "dataType": "ACTUALS",                          // String    数据类型枚举
        "title": "Actuals - Internal Peers",            // String    图表标题，格式 "[DataType 显示名] - [Benchmark 显示名]"
        "calculationInfo": {                            // Object    卡片级 tooltip 内容（见下方详细说明）
          "metricName": "ARR Growth Rate",
          "method": "Nearest Rank Percentile",
          "description": "(ARR_t - ARR_(t-1)) / ARR_(t-1)",
          "cohortDescription": "Compared against 15 peer companies matching Type, Stage, Accounting Method, and ARR range",
          "externalInfo": null                          // 外部基准非 null，见下方 externalInfo 详细说明
        },
        "referencePercentiles": [                       // Array     图表级 info icon tooltip：取 endDate 月的参考值（Internal 5 个 / External 3 个）
          { "label": "P0",   "percentile": 0,   "value": 0.05, "formattedValue": "5.00%"  },
          { "label": "P25",  "percentile": 25,  "value": 0.15, "formattedValue": "15.00%" },
          { "label": "P50",  "percentile": 50,  "value": 0.30, "formattedValue": "30.00%" },
          { "label": "P75",  "percentile": 75,  "value": 0.50, "formattedValue": "50.00%" },
          { "label": "P100", "percentile": 100, "value": 0.85, "formattedValue": "85.00%" }
        ],
        "series": [                                     // Array     公司折线数据，按公司名 A-Z
          {
            "companyId": "comp-001",
            "companyName": "Accelerist",
            "percentiles": [80.0, null, 65.0, 70.0, 75.0, 56.0],                 // Array<Number>  百分位数组，与 months 等长；null = 无数据
            "displays":    ["P80", "N/A", "P65", "P70", "P75", "P56"],           // Array<String>  展示文本数组
            "values":      [0.45, null, 0.35, 0.38, 0.40, 0.35],                 // Array<Number|String>  原始值（金额/比率字段为 String）
            "referencePercentilesByMonth": [                                     // ★ Array<Array>  按月对齐的参考分布（数据点 hover tooltip）
              [                                                                  // 索引 0 对应 months[0] = "2024-08"
                { "label": "P0",   "percentile": 0,   "value": 0.05, "formattedValue": "5.00%"  },
                { "label": "P25",  "percentile": 25,  "value": 0.20, "formattedValue": "20.00%" },
                { "label": "P50",  "percentile": 50,  "value": 0.35, "formattedValue": "35.00%" },
                { "label": "P75",  "percentile": 75,  "value": 0.55, "formattedValue": "55.00%" },
                { "label": "P100", "percentile": 100, "value": 0.90, "formattedValue": "90.00%" }
              ],
              [ /* 索引 1 对应 months[1] = "2024-09"... */ ],
              [ /* 索引 2 */ ], [ /* 索引 3 */ ], [ /* 索引 4 */ ], [ /* 索引 5 */ ]
            ]
          },
          {
            "companyId": "comp-002",
            "companyName": "Brokerage Engine LLC",
            "percentiles": [40.0, 45.0, 50.0, 55.0, 60.0, 62.0],
            "displays":    ["P40", "P45", "P50", "P55", "P60", "P62"],
            "values":      [0.20, 0.22, 0.25, 0.28, 0.30, 0.31],
            "referencePercentilesByMonth": [ /* 6 个月每月一组 */ ]
          }
        ]
      },
      {
        "metricKey": "GROSS_MARGIN",                    // 第二个图表：不同指标
        "metricName": "Gross Margin",
        /* 其他字段同上结构 */
      }
    ]
  }
}
```

### ★ `referencePercentilesByMonth`（数据点 hover tooltip）

每个 `series` 新增 `referencePercentilesByMonth` 字段：**二维数组**，外层按月对齐 `months`，内层为该公司在该月的 P0/P25/P50/P75/P100 参考分布（外部基准为 3 条 P25/P50/P75）。

**前端渲染示例**（hover 月份 `monthIdx` 的 tooltip）：

```javascript
const title = formatMonth(months[monthIdx]);  // "JAN 2025"
const lines = series.map(s => {
  const pct = s.displays[monthIdx];           // "P80"
  const refs = s.referencePercentilesByMonth[monthIdx] || [];
  const refsStr = refs.map(r => `${r.label} ${r.formattedValue}`).join('  ');
  return `● ${s.companyName}: ${pct}   ${refsStr}`;
});
// 输出：
// JAN 2025
// ● Accelerist: P80   P0 5%  P25 25%  P50 40%  P75 60%  P100 90%
// ● Brokerage: P40    P0 5%  P25 25%  P50 40%  P75 60%  P100 90%
```

**每个公司的参考分布独立**：因为每家公司的 peer group 基于其自身 Type/Stage/会计方法/ARR 解析，不同公司可能匹配到不同的 peers，参考分布也会不同。

**计算位置**：`PortfolioBenchmarkServiceImpl.buildPerMonthReferences(metric, bs, ds, month, company, ...)`。

### `calculationInfo` 详细说明

**Internal Peers**（`benchmarkSource = INTERNAL_PEERS`）：

```json
{
  "metricName": "ARR Growth Rate",
  "method": "Nearest Rank Percentile",
  "description": "(ARR_t - ARR_(t-1)) / ARR_(t-1)",
  "cohortDescription": "Compared against 15 peer companies matching Type, Stage, Accounting Method, and ARR range",
  "externalInfo": null
}
```

**External（KeyBanc / High Alpha / Benchmarkit）**：

> 由于图表时间段可能跨年、公司 ARR 可能跨 segment 边界，`segments` 和 `sources` 按月聚合去重，可能包含多个条目。`metricName` / `dataType` / `definition` / `bestGuess` 在同一 platform+metric 内假定一致，取首次匹配结果。

```json
{
  "metricName": "ARR Growth Rate",                      // LG 指标名
  "method": "Linear Interpolation",
  "description": "(ARR_t - ARR_(t-1)) / ARR_(t-1)",    // LG 公式
  "cohortDescription": "Compared against KeyBanc survey data, segment: $5M - $20M",
  "externalInfo": {                                     // 仅外部基准非 null
    "metricName": "NEW ARR Growth Rate",                // String   外部平台指标名（benchmark_entry.metric_name）
    "dataType": "Best Guess",                           // String   "Best Guess" / "Exact" / "Inferred"
    "definition": "(New ARR this year - New ARR last year) / New ARR last year",  // String  外部平台公式
    "bestGuess": "Estimated from ARR band medians",     // String   benchmark_entry.best_guess 首个匹配值
    "editions": ["2024", "2025"],                       // Array    跨月匹配到的唯一 edition 值
    "segments": [                                       // Array    每项 = "SegmentType-SegmentValue (Mon YYYY, Mon YYYY, ...)"
      "ARR-< $1M (Oct 2024, Nov 2024, Dec 2024)",       //          公司 ARR 在 < $1M 档位的月份
      "ARR-$1M - $5M (Jan 2025, Feb 2025, Mar 2025)"    //          公司 ARR 升到 $1M-$5M 档位的月份
    ],
    "sources": [                                        // Array    跨月匹配到的唯一 "Platform - Edition"
      "KeyBanc - 2024",
      "KeyBanc - 2025"
    ]
  }
}
```

**前端展示格式建议**：

```
[metricName]
该指标计算方式: [description]

若 externalInfo 非 null：
[externalInfo.metricName], [externalInfo.dataType]
[externalInfo.definition]
Best Guess: [externalInfo.bestGuess]
Segment: [segments[0]]
Segment 2 (如有): [segments[1]]
Source: [sources.join(" / ")]
```

**字段为 null 的情形**：
- 外部基准整段时间无任何匹配 entry → `externalInfo = null`
- `metricName` / `dataType` / `definition` / `bestGuess` 在 entry 中缺失 → 对应字段为 null，但 `externalInfo` 对象仍存在

### 前端分组渲染提示

```javascript
// 按指标分组渲染卡片
const metricCards = charts.reduce((acc, chart) => {
  (acc[chart.metricKey] ??= []).push(chart);
  return acc;
}, {});

// 按 categoryId 过滤（Filter 控件）
const filterMap = {
  GROWTH: ['cat-revenue-growth'],
  EFFICIENCY: ['cat-profitability'],
  MARGINS: ['cat-burn-runway'],
  CAPITAL: ['cat-capital-efficiency'],
};
const visibleCharts = filter === 'ALL'
  ? charts
  : charts.filter(c => filterMap[filter].includes(c.categoryId));
```

### Trend 无数据处理

| 场景 | percentiles | values | 前端处理 |
|------|-------------|--------|---------|
| 正常有数据 | 实际百分位值 | Number/String | 正常画点 |
| 某月无数据 | null | null | 画在 P0 位置，tooltip 显示 "N/A" |
| 某公司整段无数据 | 全 null | 全 null | 折线贴底 P0 |
| 外部基准无匹配 entry（整段或某月） | null | 原始值（如有）| P0 位置；Monthly Runway 不应用分类覆盖 |

### Monthly Runway 特殊行为

Monthly Runway 的 percentile 基于 Cash/Burn 分类排序：

| 分类 | Cash / Burn 条件 | 百分位 | runway 值 |
|------|-----------------|--------|-----------|
| TOP_RANK | Cash ≥ 0 且 Burn ≥ 0 | **P100** | N/A |
| BOTTOM_RANK | Cash < 0 且 Burn < 0 | **P0** | N/A |
| WORST_NEGATIVE_ZERO | (Cash < 0 且 Burn = 0) 或 (Cash = 0 且 Burn < 0) | **P0** | N/A |
| CALCULATED | 其他可计算情况 | 正常排名 | 实际跑道月数 |
| NO_DATA | Cash 或 Burn 为 null | null / N/A | N/A |

- Internal Peers：总是应用上述分类规则
- External Benchmark：**仅当有匹配 entry 时**才应用分类覆盖；无 entry → 全部 N/A
- tooltip 参考值采用分类感知 SCR 排名（含 TOP/BOTTOM/WORST 实体，值为 null 则该位置展示 N/A）

### Tooltip N/A 规则总结

| 触发条件 | 结果 |
|---------|------|
| N = 0（完全无数据） | 5 个位置全部 N/A |
| N = 1（仅 target 有值，常见于稀疏预测数据） | 仅 P100 展示值，其他 4 个 N/A |
| totalTie（所有值相等） | 5 个位置全部 N/A |
| SCR rank 跳过（如 ranks=[1,2,3,3] 无 rank 4） | 对应 P 位置 N/A |
| Monthly Runway 该 rank 实体为 TOP/BOTTOM/WORST | 该位置 N/A（runway 值为 null） |
