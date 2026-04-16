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
  "dataSources": ["ACTUALS", "COMMITTED_FORECAST"],     // String[]  ACTUALS / COMMITTED_FORECAST / SYSTEM_GENERATED_FORECAST，默认 ["ACTUALS"]
  "benchmarkSources": ["INTERNAL_PEERS", "KEYBANC"],    // String[]  INTERNAL_PEERS / KEYBANC / HIGH_ALPHA / BENCHMARK_IT，默认 ["INTERNAL_PEERS"]
  "page": 1,                                            // Integer   页码，从 1 开始，默认 1
  "size": 10                                            // Integer   每页公司数，默认 10
}
```

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
            "edition": null,                            // String    外部基准版本年份如 "2025"；INTERNAL_PEERS 固定为 null
            "peerInfo": {                               // Object    同行组信息；仅 INTERNAL_PEERS 有值，外部基准为 null
              "peerCount": 15,                          // Integer   同行公司数量（不含目标公司本身）
              "isFallback": false,                      // Boolean   是否回退到全平台基准（同行 < 3 家时）
              "fallbackMessage": null                   // String    回退提示文案；isFallback=false 时为 null
            },
            "dataTypeRows": [                           // Array     数据类型子行，按 Actuals → Committed Forecast → System Generated Forecast 排序
              {
                "dataType": "ACTUALS",                  // String    数据类型枚举：ACTUALS / COMMITTED_FORECAST / SYSTEM_GENERATED_FORECAST
                "metrics": {                            // Object    6 个指标的百分位结果，key = MetricEnum 名
                  "ARR_GROWTH_RATE": {                  // Object    ARR 增长率的百分位结果
                    "value": 0.35,                      // Number    原始指标值；无数据时为 null
                    "formattedValue": "35.00%",         // String    格式化展示值；无数据时为 "N/A"
                    "percentile": 56.0,                 // Number    百分位数值（0-100）；无数据时为 null
                    "percentileDisplay": "P56",         // String    百分位展示文本："P56" / "~P62" / ">P75" / "<P25" / "N/A"
                    "estimationType": "EXACT"           // String    估算类型：EXACT / INTERPOLATED / BOUNDARY_ABOVE / BOUNDARY_BELOW / MEDIAN_ONLY；无数据为 null
                  },
                  "GROSS_MARGIN": {                     // Object    毛利率
                    "value": 0.72,
                    "formattedValue": "72.00%",
                    "percentile": 80.0,
                    "percentileDisplay": "P80",
                    "estimationType": "EXACT"
                  },
                  "MONTHLY_NET_BURN_RATE": {            // Object    月净烧钱率
                    "value": -50000.00,
                    "formattedValue": "-$50,000.00",
                    "percentile": 45.0,
                    "percentileDisplay": "P45",
                    "estimationType": "EXACT"
                  },
                  "MONTHLY_RUNWAY": {                   // Object    月跑道
                    "value": 24.5,
                    "formattedValue": "24.5",
                    "percentile": 70.0,
                    "percentileDisplay": "P70",
                    "estimationType": "EXACT"
                  },
                  "RULE_OF_40": {                       // Object    Rule of 40
                    "value": 0.42,
                    "formattedValue": "42.00%",
                    "percentile": 65.0,
                    "percentileDisplay": "P65",
                    "estimationType": "EXACT"
                  },
                  "SALES_EFFICIENCY_RATIO": {           // Object    销售效率比
                    "value": 1.2,
                    "formattedValue": "1.20",
                    "percentile": 30.0,
                    "percentileDisplay": "P30",
                    "estimationType": "EXACT"
                  }
                },
                "tooltipData": {                        // Object    Benchmark 列 Tooltip 的参考百分位值；key = MetricEnum 名
                  "ARR_GROWTH_RATE": [                  // Array     该指标在各百分位处的参考值；Internal Peers 5 个点，External 3 个点
                    {
                      "label": "P0",                    // String    百分位标签：P0 / P25 / P50 / P75 / P100
                      "percentile": 0,                  // Number    百分位数值
                      "value": 0.05,                    // Number    该百分位处的参考指标值
                      "formattedValue": "5.00%"         // String    格式化展示值
                    },
                    { "label": "P25",  "percentile": 25,  "value": 0.15, "formattedValue": "15.00%" },
                    { "label": "P50",  "percentile": 50,  "value": 0.30, "formattedValue": "30.00%" },
                    { "label": "P75",  "percentile": 75,  "value": 0.50, "formattedValue": "50.00%" },
                    { "label": "P100", "percentile": 100, "value": 0.85, "formattedValue": "85.00%" }
                  ],
                  "GROSS_MARGIN": [ /* 同上结构 */ ]
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
            "edition": "2025",                          // 外部基准版本年份
            "peerInfo": null,                           // 外部基准无同行组信息
            "dataTypeRows": [
              {
                "dataType": "ACTUALS",
                "metrics": {
                  "ARR_GROWTH_RATE": {
                    "value": 0.35,
                    "formattedValue": "35.00%",
                    "percentile": 62.5,
                    "percentileDisplay": "~P63",        // 插值结果：~P63 表示线性插值估算
                    "estimationType": "INTERPOLATED"
                  }
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
| 外部基准无匹配 segment | 该 benchmarkGroup 下所有 metric percentile=null, percentileDisplay="N/A"，tooltipData 为空数组 |
| Internal Peers peer < 3 | peerInfo.isFallback=true，使用全平台基准计算百分位 |
| Internal Peers 所有值相同 | percentileDisplay="N/A"（totalTie） |
| Monthly Runway 特殊分类 | TOP_RANK → 最高百分位，BOTTOM_RANK / WORST_NEGATIVE_ZERO → 最低百分位 |

### 格式化规则

| 指标 | 单位 | 格式 | isReverse | 示例 |
|------|------|------|-----------|------|
| ARR Growth Rate | % | 两位小数 + "%" | false | "35.00%" |
| Gross Margin | % | 两位小数 + "%" | false | "72.00%" |
| Monthly Net Burn Rate | USD | "$" + 千分位 + 两位小数 | false | "-$50,000.00" |
| Monthly Runway | months | 一位小数 | false | "24.5" |
| Rule of 40 | % | 两位小数 + "%" | false | "42.00%" |
| Sales Efficiency Ratio | ratio | 两位小数 | true | "1.20" |

---

## API-02：Trend 数据查询

`POST /web/portfolio-benchmark/trend`

### 请求体

```json
{
  "companyIds": ["comp-001", "comp-002"],               // String[]  要对标的公司 ID 列表，至少 1 个
  "startDate": "2024-08",                               // String    起始月份 yyyy-MM；默认为 endDate 往前 5 个月
  "endDate": "2025-01",                                 // String    结束月份 yyyy-MM；默认当前月份；必须 > startDate
  "dataSources": ["ACTUALS"],                           // String[]  同 API-01
  "benchmarkSources": ["INTERNAL_PEERS"]                // String[]  同 API-01
}
```

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
      {
        "companyId": "comp-001",                        // String    公司 ID
        "companyName": "Accelerist"                     // String    公司名称
      },
      {
        "companyId": "comp-002",
        "companyName": "Brokerage Engine LLC"
      }
    ],
    "charts": [                                         // Array     扁平图表列表，按 指标 → Benchmark → DataType 顺序
      {
        "metricKey": "ARR_GROWTH_RATE",                 // String    MetricEnum 枚举名，前端按此字段分组渲染卡片
        "metricName": "ARR Growth Rate",                // String    指标展示名称
        "categoryId": "cat-revenue-growth",             // String    分类 ID，前端用于 FILTER 映射
        "benchmarkSource": "INTERNAL_PEERS",            // String    基准源枚举
        "dataType": "ACTUALS",                          // String    数据类型枚举
        "title": "Actuals - Internal Peers",            // String    图表标题，格式 "[DataType 显示名] - [Benchmark 显示名]"
        "calculationInfo": {                            // Object    卡片级 tooltip 内容（同一 metricKey 的 chart 内容一致）
          "method": "Nearest Rank Percentile",          // String    计算方法名称
          "description": "(ARR_t - ARR_(t-1)) / ARR_(t-1)",  // String  指标公式说明，取自 MetricEnum.lgFormula
          "cohortDescription": "Compared against 15 peer companies matching Type, Stage, Accounting Method, and ARR range"  // String  同群组说明（不含公司名）
        },
        "referencePercentiles": [                       // Array     图表 info icon tooltip — 取 endDate 月的参考百分位值；Internal 5 个，External 3 个
          {
            "label": "P0",                              // String    百分位标签
            "percentile": 0,                            // Number    百分位数值
            "value": 0.05,                              // Number    该百分位处的参考指标值
            "formattedValue": "5.00%"                   // String    格式化展示值
          },
          { "label": "P25",  "percentile": 25,  "value": 0.15, "formattedValue": "15.00%" },
          { "label": "P50",  "percentile": 50,  "value": 0.30, "formattedValue": "30.00%" },
          { "label": "P75",  "percentile": 75,  "value": 0.50, "formattedValue": "50.00%" },
          { "label": "P100", "percentile": 100, "value": 0.85, "formattedValue": "85.00%" }
        ],
        "series": [                                     // Array     公司折线数据，按公司名 A-Z
          {
            "companyId": "comp-001",                    // String    公司 ID
            "companyName": "Accelerist",                // String    公司名称
            "percentiles": [                            // Array<Number>  百分位数组，与 months 等长、索引对齐；null = 无数据
              80.0, null, 65.0, 70.0, 75.0, 56.0
            ],
            "displays": [                               // Array<String>  展示文本数组，与 months 等长；"P80" / "N/A"
              "P80", "N/A", "P65", "P70", "P75", "P56"
            ],
            "values": [                                 // Array<Number>  原始指标值数组，与 months 等长；null = 无数据
              0.45, null, 0.35, 0.38, 0.40, 0.35
            ]
          },
          {
            "companyId": "comp-002",
            "companyName": "Brokerage Engine LLC",
            "percentiles": [40.0, 45.0, 50.0, 55.0, 60.0, 62.0],
            "displays":    ["P40", "P45", "P50", "P55", "P60", "P62"],
            "values":      [0.20, 0.22, 0.25, 0.28, 0.30, 0.31]
          }
        ]
      },
      {
        "metricKey": "GROSS_MARGIN",                    // 第二个图表：不同指标
        "metricName": "Gross Margin",
        "categoryId": "cat-profitability",
        "benchmarkSource": "INTERNAL_PEERS",
        "dataType": "ACTUALS",
        "title": "Actuals - Internal Peers",
        "calculationInfo": { /* 同上结构 */ },
        "referencePercentiles": [ /* 同上结构 */ ],
        "series": [ /* 同上结构 */ ]
      }
    ]
  }
}
```

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

| 场景 | percentiles 中的值 | 前端处理 |
|------|-------------------|----------|
| 正常有数据 | 实际百分位值 | 正常画点 |
| 某月无数据 | null | 画在 P0 位置，tooltip 显示 "N/A" |
| 某公司整段无数据 | 全 null | 折线贴底 P0 |
