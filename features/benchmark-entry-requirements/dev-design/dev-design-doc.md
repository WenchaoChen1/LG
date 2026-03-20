# Benchmark Entry 功能设计文档

> 版本：v1.0
> 创建时间：2026-03-18
> 需求来源：features/benchmark-entry-requirements/requirement/requirement-doc.md
> 截图来源：features/benchmark-entry-requirements/Benchmark Entry原始需求文档/32130.jpg、14771.jpg
> 状态：草稿

---

## 1. 功能概述

Benchmark Entry 为投资分析团队提供 SaaS 行业基准指标的统一管理平台。用户可通过 Looking Glass 分类体系管理指标类别和指标，并在展开的指标行下录入来自 Benchmarkit.ai、KeyBanc、High Alpha 等平台的基准数据（含 25th/Median/75th 分位值）。整个页面采用内联编辑设计，所有操作在单页面内完成，数据存入数据库供 Benchmark 模块使用。

---

## 2. UI 界面设计

> 本章基于截图和需求文档生成。

### 2.1 页面布局

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [Logo]              [Convert all currencies to USD 开关]       [用户头像▼]  │  ← 导航栏
├──────────────────────────────────────────────────────────────────────────────┤
│  Benchmark Entry                                                             │
│  Manage and compare performance metrics across platforms                     │
├────────────┬─────────────┬─────────────────────────────────────── ─ ─ ─ ─ ─ ┤
│ LG         │ LG METRIC   │ LG      │PLATFORM│EDITION│METRIC │...│DATA│GUESS│  ← 表头
│ CATEGORY   │ NAME        │ FORMULA │        │       │NAME   │   │    │     │
│ (固定列)   │ (固定列)     │ ────────────── 可水平滚动区域 ──────────────────│
├────────────┼─────────────┼─────────┼────────┼───────┼───────┼───┼────┼─────┤
│            │ ▷ 指标行     │ Enter.. │        │       │       │   │    │     │  ← 折叠
│ 类别       ├─────────────┼─────────┼────────┼───────┼───────┼───┼────┼─────┤
│ (纵向合并) │ ▽ 指标行     │ 公式    │        │       │       │   │    │     │  ← 展开
│            ├─────────────┼─────────┼────────┼───────┼───────┼───┼────┼─────┤
│            │  (detail)   │         │Benchm. │ —     │ —     │   │ —  │ —   │  ← 详情行
│            ├─────────────┼─────────┼────────┼───────┼───────┼───┼────┼─────┤
│            │  (new row)  │         │[下拉▼] │[输入] │[输入] │   │[▼] │[输入]│✓×│ ← 新增行
│            ├─────────────┼─────────┼────────┼───────┼───────┼───┼────┼─────┤
│            │  + Add detail         │        │       │       │   │    │     │  ← detail入口
│            ├─────────────┼─────────┼────────┼───────┼───────┼───┼────┼─────┤
│            │ + Add metric ▼        │        │       │       │   │    │     │  ← metric入口
├────────────┴─────────────┴─────────┴────────┴───────┴───────┴───┴────┴─────┤
│  + Add category ▼                                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│  ◄ ══════════════════════ 水平滚动条 ══════════════════════════════════ ►    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件清单

| 组件名称 | 组件类型 | 位置 | 说明 |
|---------|---------|------|------|
| 导航栏 | Layout Header | 页面顶部 | Logo + 货币开关（Switch，本期仅 UI）+ 用户头像下拉 |
| 页面标题 | PageHeader | 导航栏下方 | 标题 "Benchmark Entry" + 副标题 |
| 主数据表格 | 自定义 Table | 主内容区 | 左 2 列固定，右侧列水平滚动；支持行分组、纵向合并、展开/折叠 |
| 指标行 | Table Row（父级） | 表格行 | 含 LG CATEGORY（合并）、LG METRIC NAME（可展开）、LG FORMULA |
| 详情行 | Table Row（子级） | 展开区域 | 11 个字段，支持内联编辑；悬停显示删除按钮 |
| 新增行 | Inline Form Row | 展开区域底部 | 高亮背景，11 个输入控件 + ✓ × 按钮 |
| Add detail 按钮 | Button（文字链） | 展开区域底部 | 橙色文字 "+ Add detail" |
| Add metric 下拉 | Dropdown + Button | 类别组底部 | 橙色文字 "+ Add metric ▼"，下拉选择预定义指标 |
| Add category 下拉 | Dropdown + Button | 表格最底部 | 橙色文字 "+ Add category ▼"，下拉选择预定义类别 |
| 内联编辑器 | Input + 确认/取消 | 类别名称、指标名称 | 悬停显示铅笔图标，点击切换为输入框 |

### 2.3 数据展示规则

**表格列定义**

| 列名 | 字段名 | 数据类型 | 显示格式 | 说明 |
|------|--------|---------|---------|------|
| LOOKING GLASS CATEGORY | `categoryName` | string | 纯文本，同类别纵向合并 | 左固定列，约 140px |
| LG METRIC NAME | `metricName` | string | 粗体 + 展开箭头 ▷/▽ | 左固定列，约 150px |
| LG FORMULA | `formula` | string | placeholder "Enter formula" | 父级行字段 |
| PLATFORM | `platform` | string | 文本 / 新增时下拉 | 子级行字段 |
| EDITION | `edition` | string | 纯文本 | 子级行字段 |
| METRIC NAME | `sourceMetricName` | string | 纯文本 | 子级行字段 |
| DEFINITION | `definition` | string | 纯文本 | 子级行字段 |
| FY PERIOD | `fyPeriod` | number | 年份数字（如 2024） | 日历选择器 |
| SEGMENT | `segment` | string | 纯文本 | 子级行字段 |
| 25TH | `percentile25th` | string | 原始文本，空值 "—" | 子级行字段 |
| MEDIAN | `median` | string | 原始文本，空值 "—" | 子级行字段 |
| 75TH | `percentile75th` | string | 原始文本，空值 "—" | 子级行字段 |
| DATA | `dataType` | string | 文本 (Actual/Forecast) | 子级行字段，下拉 |
| GUESS | `bestGuess` | string | 纯文本 | 子级行字段 |

**数字与颜色约定**
- 表头行：深蓝色背景 (#1B3A5C)，白色字体，全大写
- 类别分组行：白色背景，类别名称黑色粗体
- 详情行：白色背景，空值字段显示 "—"（灰色）
- 新增行：浅蓝色高亮背景
- 操作链接（Add category/metric/detail）：橙色文字 (#E8833A)
- 展开/折叠箭头：橙色

### 2.4 交互行为

| 触发元素 | 触发方式 | 效果描述 |
|---------|---------|---------|
| LG METRIC NAME 文字 | 点击 | 展开该指标的详情区域（含已有 detail 行 + Add detail 按钮），再次点击折叠 |
| Add detail 按钮 | 点击 | 在详情列表末尾插入一行高亮新增行（11 个输入控件 + ✓×），同一指标下仅允许一个新增行 |
| 新增行 ✓ 按钮 / Enter | 点击/按键 | 提交保存，成功后新增行消失、数据行出现；失败则保留数据并 Toast 报错 |
| 新增行 × 按钮 / Escape | 点击/按键 | 取消新增行，丢弃填入数据 |
| Add metric ▼ | 点击 | 展开下拉，显示该类别下未使用的预定义指标；选择后新增指标行 |
| Add category ▼ | 点击 | 展开下拉，显示未使用的预定义类别；选择后新增类别 + 该类别的第一个默认指标 |
| 类别名称 / 指标名称 | hover | 显示铅笔编辑图标 |
| 铅笔图标 | 点击 | 切换为 Input 输入框 + ✓× 按钮；Enter 确认，Escape 取消 |
| 详情行 | hover | 行尾显示删除图标（红色垃圾桶） |
| 删除图标 | 点击 | 直接删除该行，无二次确认 |
| LG FORMULA 单元格 | 点击 | 直接进入编辑模式，失焦后自动保存 |
| 详情行单元格 | 点击 | 直接进入内联编辑，失焦后自动保存 |
| Currency 开关 | toggle | 本期仅切换 UI 状态，不触发数据变化 |

### 2.5 空态与加载态

| 场景 | 展示方式 |
|------|---------|
| 页面加载中 | 表格区域显示 Spin loading 骨架 |
| 表格无数据（首次使用） | 仅显示表头 + Add category 入口 |
| 某指标下无详情数据 | 展开后显示 Add detail 按钮，无额外空态提示 |
| 接口报错 | 页面顶部 Toast 提示错误原因，3 秒后自动消失 |

---

## 3. 前端实现要点

### 3.1 路由与文件结构

```
路由：/benchmark/entry
文件目录：CIOaas-web/src/pages/Benchmark/Entry/
  ├── index.tsx                    # 页面入口，数据加载和顶层状态
  ├── components/
  │   ├── BenchmarkTable.tsx       # 主表格组件（分组、合并、固定列）
  │   ├── MetricRow.tsx            # 指标行（展开/折叠、公式编辑）
  │   ├── DetailRow.tsx            # 详情行（内联编辑、删除）
  │   ├── NewDetailRow.tsx         # 新增行（表单输入 + 确认/取消）
  │   ├── InlineEditor.tsx         # 通用内联编辑组件（Input + ✓×）
  │   ├── AddMetricDropdown.tsx    # + Add metric 下拉
  │   └── AddCategoryDropdown.tsx  # + Add category 下拉
  └── service.ts                   # API 请求函数 + TS 类型定义
```

### 3.2 状态管理

```
本地状态（React useState/useReducer）：

需要维护的状态：
- categories: BenchmarkCategory[]  — 类别列表（含其下指标和详情数据的嵌套结构）
- enumMaps: EnumMaps              — 从 GET 接口获取的枚举映射（categories/platforms/dataTypes 的 value→displayName）
- expandedMetricIds: Set<string>   — 当前展开的指标 ID 集合
- editingCellId: string | null     — 当前正在内联编辑的单元格标识
- addingDetailMetricId: string | null — 当前正在显示新增行的指标 ID（仅允许一个）
- loading: boolean                 — 页面加载状态
```

### 3.3 关键实现说明

- **左侧固定列**：使用 CSS `position: sticky` 或 Ant Design Table 的 `fixed: 'left'` 实现 LOOKING GLASS CATEGORY 和 LG METRIC NAME 两列固定
- **类别纵向合并**：自行计算每个类别组的 `rowSpan`，同类别的第一行显示类别名称，后续行该列为空
- **展开/折叠不使用 Table expandable**：因为子行结构（detail 行）需要跨越父行列结构，建议用自定义渲染，手动控制 detail 行的显隐
- **内联编辑**：点击单元格切换为 Input/Select，失焦或 Enter 触发 auto-save（调用 PATCH 接口）；失败时 revert 值
- **新增行确认/取消**：确认时收集所有字段值调用 POST 接口，成功后清除 `addingDetailMetricId`，刷新该指标的 detail 列表
- **页面初始化**：调用一次 GET 接口获取全量数据（类别 → 指标 → 详情）+ 枚举映射表（`enums`），嵌套结构一次返回
- **枚举映射**：所有枚举的 value → displayName 映射从 GET 接口的 `enums` 字段获取，前端不硬编码枚举值。下拉选项、表格展示均基于此映射渲染

---

## 4. 后端接口设计

### 4.1 接口汇总

| 接口名称 | 方法 | 路径 | 用途 |
|---------|------|------|------|
| 获取全量数据 | GET | `/api/fi/benchmark-entry` | 页面初始化，获取所有类别、指标和详情数据 |
| 新增类别 | POST | `/api/fi/benchmark-entry/categories` | 从预定义列表中添加一个类别（含默认指标） |
| 更新类别名称 | PATCH | `/api/fi/benchmark-entry/categories/{categoryId}` | 重命名类别 |
| 新增指标 | POST | `/api/fi/benchmark-entry/metrics` | 在某类别下添加一个预定义指标 |
| 更新指标 | PATCH | `/api/fi/benchmark-entry/metrics/{metricId}` | 重命名指标 或 更新公式 |
| 新增详情数据 | POST | `/api/fi/benchmark-entry/metrics/{metricId}/details` | 在某指标下新增一条详情数据 |
| 更新详情数据 | PATCH | `/api/fi/benchmark-entry/details/{detailId}` | 内联编辑更新详情数据的单个/多个字段 |
| 删除详情数据 | DELETE | `/api/fi/benchmark-entry/details/{detailId}` | 删除一条详情数据 |

### 4.2 接口详情

---

#### GET `/api/fi/benchmark-entry`

**用途**：页面初始化，获取全量嵌套数据

**请求参数**：无

**响应结构**

```json
{
  "code": 200,
  "data": {
    "categories": [
      {
        "id": "uuid",
        "category": "REVENUE_GROWTH",
        "categoryName": "Revenue & Growth",
        "displayOrder": 1,
        "metrics": [
          {
            "id": "uuid",
            "metric": "ARR_GROWTH_RATE",
            "metricName": "ARR Growth Rate",
            "formula": "公式文本或 null",
            "displayOrder": 1,
            "details": [
              {
                "id": "uuid",
                "platform": "BENCHMARKIT_AI",
                "edition": "Q3 2024 Report",
                "sourceMetricName": "ARR Growth",
                "definition": "Year-over-year ARR growth rate",
                "fyPeriod": 2024,
                "segment": "$1M-$10M",
                "percentile25th": "15%",
                "median": "25%",
                "percentile75th": "40%",
                "dataType": "ACTUAL",
                "bestGuess": "~30%",
                "createdAt": "2026-03-18T10:00:00Z"
              }
            ]
          }
        ]
      }
    ],
    "availableCategories": ["BURN_RUNWAY"],
    "categoryMetricMap": {
      "REVENUE_GROWTH": [{"metric": "ARR_GROWTH_RATE", "displayName": "ARR Growth Rate"}],
      "PROFITABILITY_EFFICIENCY": [{"metric": "GROSS_MARGIN", "displayName": "Gross Margin"}],
      "BURN_RUNWAY": [{"metric": "MONTHLY_NET_BURN_RATE", "displayName": "Monthly Net Burn Rate"}],
      "CAPITAL_EFFICIENCY": [
        {"metric": "RULE_OF_40", "displayName": "Rule of 40"},
        {"metric": "SALES_EFFICIENCY_RATIO", "displayName": "Sales Efficiency Ratio"}
      ]
    },
    "enums": {
      "categories": [
        {"value": "REVENUE_GROWTH", "displayName": "Revenue & Growth"},
        {"value": "PROFITABILITY_EFFICIENCY", "displayName": "Profitability & Efficiency"},
        {"value": "BURN_RUNWAY", "displayName": "Burn & Runway"},
        {"value": "CAPITAL_EFFICIENCY", "displayName": "Capital Efficiency"}
      ],
      "platforms": [
        {"value": "BENCHMARKIT_AI", "displayName": "Benchmarkit.ai"},
        {"value": "KEYBANC", "displayName": "KeyBanc"},
        {"value": "HIGH_ALPHA", "displayName": "High Alpha"}
      ],
      "dataTypes": [
        {"value": "ACTUAL", "displayName": "Actual"},
        {"value": "FORECAST", "displayName": "Forecast"}
      ]
    }
  },
  "message": "success"
}
```

**后端业务逻辑**

1. 查询 `fi_benchmark_entry` 表中 `entry_type = 'METRIC'` 的行，按 `category`, `display_order` 排序
2. 对每个 METRIC 行，查询 `fi_benchmark_entry` 表中 `parent_id = 该 METRIC 行 id` 的 DETAIL 行，按 `created_at` 正序
3. 按 `category` 枚举值分组组装嵌套结构；`categoryName` 优先取 `category_display_name`，为 NULL 时取枚举 displayName
4. 计算 `availableCategories`：BenchmarkCategory 全量枚举值 - 已存在的 category 值
5. 返回 `categoryMetricMap`：从 BenchmarkMetric 枚举中按 category 分组获取
6. 返回 `enums`：将 BenchmarkCategory、BenchmarkPlatform、BenchmarkDataType 枚举的 value+displayName 列表化返回，供前端下拉选项和展示映射使用
6. 涉及表：`fi_benchmark_entry`

---

#### POST `/api/fi/benchmark-entry/categories`

**用途**：新增一个预定义类别（含默认指标）

**请求参数**（Body）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `category` | string | 是 | — | 类别枚举值（如 `REVENUE_GROWTH`） |

**响应结构**

```json
{
  "code": 200,
  "data": {
    "createdCategory": {
      "id": "uuid",
      "category": "BURN_RUNWAY",
      "categoryName": "Burn & Runway",
      "displayOrder": 3,
      "metrics": [
        {
          "id": "uuid",
          "metric": "MONTHLY_NET_BURN_RATE",
          "metricName": "Monthly Net Burn Rate",
          "formula": null,
          "displayOrder": 1,
          "details": []
        }
      ]
    },
    "availableCategories": ["CAPITAL_EFFICIENCY"]
  },
  "message": "success"
}
```

**后端业务逻辑**

1. 校验 `category` 是合法的 BenchmarkCategory 枚举值
2. 校验该 category 在 `fi_benchmark_entry` 表中不存在 METRIC 行
3. 计算 `displayOrder` = 当前 METRIC 行最大 display_order + 1
4. 插入一条 METRIC 行（`entry_type='METRIC'`, `parent_id=NULL`, `category=枚举值`, `metric=该类别的默认指标枚举值`）
5. 默认指标从 BenchmarkMetric 枚举中取 `category` 匹配且 `defaultOrder=1` 的值
6. 返回新类别及其默认指标，同时返回更新后的 `availableCategories`
7. 涉及表：`fi_benchmark_entry`

---

#### PATCH `/api/fi/benchmark-entry/categories/{categoryId}`

**用途**：重命名类别

**请求参数**（Path + Body）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `categoryId` | UUID (path) | 是 | — | 类别 ID |
| `categoryDisplayName` | string (body) | 是 | — | 新的自定义显示名称，不可为空字符串 |

**响应结构**

```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "category": "REVENUE_GROWTH",
    "categoryDisplayName": "新名称",
    "displayOrder": 1
  },
  "message": "success"
}
```

**后端业务逻辑**

1. 校验 `categoryDisplayName` 非空
2. 更新 `fi_benchmark_entry` 表中该 METRIC 行及其所有同 `category` 行的 `category_display_name` 字段
3. 涉及表：`fi_benchmark_entry`

---

#### POST `/api/fi/benchmark-entry/metrics`

**用途**：在某类别下新增一个预定义指标

**请求参数**（Body）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `category` | string | 是 | — | 所属类别枚举值（如 `CAPITAL_EFFICIENCY`） |
| `metric` | string | 是 | — | 指标枚举值（如 `SALES_EFFICIENCY_RATIO`） |

**响应结构**

```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "metric": "SALES_EFFICIENCY_RATIO",
    "metricName": "Sales Efficiency Ratio",
    "formula": null,
    "displayOrder": 2,
    "details": []
  },
  "message": "success"
}
```

**后端业务逻辑**

1. 校验 `metric` 是合法的 BenchmarkMetric 枚举值，且其 `category` 属性匹配请求的 `category`
2. 校验该 `category` + `metric` 组合在 `fi_benchmark_entry` 表中不存在 METRIC 行
3. 计算 `displayOrder` = 该 category 下 METRIC 行最大 display_order + 1
4. 插入一条 METRIC 行（`entry_type='METRIC'`, `parent_id=NULL`, `category`, `metric`）
5. 涉及表：`fi_benchmark_entry`

---

#### PATCH `/api/fi/benchmark-entry/metrics/{metricId}`

**用途**：更新指标名称 或 公式

**请求参数**（Path + Body，字段全部可选）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `metricId` | UUID (path) | 是 | — | 指标 ID |
| `metricDisplayName` | string (body) | 否 | — | 新的自定义显示名称，不可为空字符串 |
| `formula` | string (body) | 否 | — | 公式文本，允许空字符串（清空公式） |

**响应结构**

```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "metric": "ARR_GROWTH_RATE",
    "metricDisplayName": "ARR Growth Rate",
    "formula": "Current ARR / Prior ARR - 1"
  },
  "message": "success"
}
```

**后端业务逻辑**

1. 若提供 `metricDisplayName`，校验非空后更新 `fi_benchmark_entry` 表该 METRIC 行的 `metric_display_name` 字段
2. 若提供 `formula`，直接更新 `formula` 字段（允许空字符串）
3. 涉及表：`fi_benchmark_entry`

---

#### POST `/api/fi/benchmark-entry/metrics/{metricId}/details`

**用途**：在某指标下新增一条详情数据

**请求参数**（Path + Body）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `metricId` | UUID (path) | 是 | — | 所属指标 ID |
| `platform` | string (body) | 否 | null | 平台名称 |
| `edition` | string (body) | 否 | null | 版本信息 |
| `sourceMetricName` | string (body) | 否 | null | 平台原始指标名 |
| `definition` | string (body) | 否 | null | 指标定义 |
| `fyPeriod` | integer (body) | 否 | null | 财年年份 |
| `segment` | string (body) | 否 | null | 分段 |
| `percentile25th` | string (body) | 否 | null | 第 25 百分位 |
| `median` | string (body) | 否 | null | 中位数 |
| `percentile75th` | string (body) | 否 | null | 第 75 百分位 |
| `dataType` | string (body) | 否 | null | 数据类型 (Actual/Forecast) |
| `bestGuess` | string (body) | 否 | null | 最佳猜测 |

**响应结构**

```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "platform": "Benchmarkit.ai",
    "edition": "Q3 2024 Report",
    "sourceMetricName": "ARR Growth",
    "definition": "...",
    "fyPeriod": 2024,
    "segment": "$1M-$10M",
    "percentile25th": "15%",
    "median": "25%",
    "percentile75th": "40%",
    "dataType": "Actual",
    "bestGuess": "~30%",
    "createdAt": "2026-03-18T10:00:00Z"
  },
  "message": "success"
}
```

**后端业务逻辑**

1. 校验 `metricId` 存在且为 METRIC 行
2. 所有 body 字段均可选，允许全部为 null
3. 若 `platform` 有值，校验其为合法的 BenchmarkPlatform 枚举值
4. 若 `dataType` 有值，校验其为合法的 BenchmarkDataType 枚举值
5. 插入一条 DETAIL 行（`entry_type='DETAIL'`, `parent_id=metricId`, `category` 从父行继承），`created_at` 设为当前时间
6. 涉及表：`fi_benchmark_entry`

---

#### PATCH `/api/fi/benchmark-entry/details/{detailId}`

**用途**：内联编辑更新详情数据（PATCH 语义，仅更新提供的字段）

**请求参数**（Path + Body，字段全部可选）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `detailId` | UUID (path) | 是 | — | 详情数据 ID |
| `platform` | string | 否 | — | 平台名称 |
| `edition` | string | 否 | — | 版本信息 |
| `sourceMetricName` | string | 否 | — | 平台原始指标名 |
| `definition` | string | 否 | — | 指标定义 |
| `fyPeriod` | integer | 否 | — | 财年年份 |
| `segment` | string | 否 | — | 分段 |
| `percentile25th` | string | 否 | — | 第 25 百分位 |
| `median` | string | 否 | — | 中位数 |
| `percentile75th` | string | 否 | — | 第 75 百分位 |
| `dataType` | string | 否 | — | 数据类型 |
| `bestGuess` | string | 否 | — | 最佳猜测 |

**响应结构**

```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "platform": "KeyBanc",
    "edition": "...",
    "sourceMetricName": "...",
    "definition": "...",
    "fyPeriod": 2024,
    "segment": "...",
    "percentile25th": "...",
    "median": "...",
    "percentile75th": "...",
    "dataType": "Actual",
    "bestGuess": "...",
    "createdAt": "..."
  },
  "message": "success"
}
```

**后端业务逻辑**

1. 校验 `detailId` 存在且为 DETAIL 行
2. 仅更新请求体中提供的非 null 字段
3. 若 `platform` 有值，校验其为合法的 BenchmarkPlatform 枚举值
4. 若 `dataType` 有值，校验其为合法的 BenchmarkDataType 枚举值
5. 更新 `fi_benchmark_entry` 表该行，同时更新 `updated_at`
6. 涉及表：`fi_benchmark_entry`

---

#### DELETE `/api/fi/benchmark-entry/details/{detailId}`

**用途**：删除一条详情数据

**请求参数**（Path）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `detailId` | UUID (path) | 是 | — | 详情数据 ID |

**响应结构**

```json
{
  "code": 200,
  "data": null,
  "message": "success"
}
```

**后端业务逻辑**

1. 校验 `detailId` 存在且为 DETAIL 行
2. 物理删除 `fi_benchmark_entry` 表中该 DETAIL 行
3. 涉及表：`fi_benchmark_entry`

---

## 5. 数据模型

### 5.0 Java 枚举定义

```java
// 类别枚举
public enum BenchmarkCategory {
    REVENUE_GROWTH("Revenue & Growth"),
    PROFITABILITY_EFFICIENCY("Profitability & Efficiency"),
    BURN_RUNWAY("Burn & Runway"),
    CAPITAL_EFFICIENCY("Capital Efficiency");

    private final String displayName;
}

// 指标枚举（含所属类别映射）
public enum BenchmarkMetric {
    ARR_GROWTH_RATE("ARR Growth Rate", BenchmarkCategory.REVENUE_GROWTH, 1),
    GROSS_MARGIN("Gross Margin", BenchmarkCategory.PROFITABILITY_EFFICIENCY, 1),
    MONTHLY_NET_BURN_RATE("Monthly Net Burn Rate", BenchmarkCategory.BURN_RUNWAY, 1),
    RULE_OF_40("Rule of 40", BenchmarkCategory.CAPITAL_EFFICIENCY, 1),
    SALES_EFFICIENCY_RATIO("Sales Efficiency Ratio", BenchmarkCategory.CAPITAL_EFFICIENCY, 2);

    private final String displayName;
    private final BenchmarkCategory category;  // 固定归属
    private final int defaultOrder;            // 类别内默认排序
}

// 平台枚举
public enum BenchmarkPlatform {
    BENCHMARKIT_AI("Benchmarkit.ai"),
    KEYBANC("KeyBanc"),
    HIGH_ALPHA("High Alpha");

    private final String displayName;
}

// 数据类型枚举
public enum BenchmarkDataType {
    ACTUAL("Actual"),
    FORECAST("Forecast");

    private final String displayName;
}
```

### 5.1 涉及表结构

> 单表设计：通过 `entry_type` 区分指标行（METRIC）和详情行（DETAIL），自引用 `parent_id` 建立父子关系。

**表：`fi_benchmark_entry`**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK | 主键 |
| `parent_id` | UUID | NULLABLE, FK → fi_benchmark_entry(id) | 自引用：METRIC 行为 NULL，DETAIL 行指向所属 METRIC 行 |
| `entry_type` | VARCHAR(10) | NOT NULL | 行类型：`METRIC` 或 `DETAIL` |
| `category` | VARCHAR(30) | NOT NULL | 类别枚举值（如 `REVENUE_GROWTH`），METRIC 和 DETAIL 行均设置 |
| `category_display_name` | VARCHAR(100) | NULLABLE | 重命名后的自定义类别名；NULL 表示使用枚举默认 displayName |
| `metric` | VARCHAR(30) | NULLABLE | 指标枚举值（如 `ARR_GROWTH_RATE`），仅 METRIC 行必填 |
| `metric_display_name` | VARCHAR(100) | NULLABLE | 重命名后的自定义指标名；NULL 表示使用枚举默认 displayName |
| `formula` | TEXT | NULLABLE | 计算公式文本，仅 METRIC 行使用 |
| `display_order` | INTEGER | NOT NULL, DEFAULT 0 | 排序：METRIC 行为类别内顺序；DETAIL 行未使用（按 created_at 排序） |
| `platform` | VARCHAR(20) | NULLABLE | 平台枚举值（如 `BENCHMARKIT_AI`），仅 DETAIL 行使用 |
| `edition` | VARCHAR(200) | NULLABLE | 版本/出版期号，仅 DETAIL 行 |
| `source_metric_name` | VARCHAR(200) | NULLABLE | 平台原始指标名称，仅 DETAIL 行 |
| `definition` | TEXT | NULLABLE | 指标定义说明，仅 DETAIL 行 |
| `fy_period` | INTEGER | NULLABLE | 财年年份，仅 DETAIL 行 |
| `segment` | VARCHAR(200) | NULLABLE | 分段维度，仅 DETAIL 行 |
| `percentile_25th` | VARCHAR(50) | NULLABLE | 第 25 百分位值，仅 DETAIL 行 |
| `median` | VARCHAR(50) | NULLABLE | 中位数值，仅 DETAIL 行 |
| `percentile_75th` | VARCHAR(50) | NULLABLE | 第 75 百分位值，仅 DETAIL 行 |
| `data_type` | VARCHAR(20) | NULLABLE | 数据类型枚举值（`ACTUAL`/`FORECAST`），仅 DETAIL 行 |
| `best_guess` | VARCHAR(500) | NULLABLE | 最佳猜测，仅 DETAIL 行 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 更新时间 |

### 5.2 关联关系

```
fi_benchmark_entry (METRIC 行, parent_id = NULL)
    │
    └──< fi_benchmark_entry (DETAIL 行, parent_id = METRIC 行的 id)
```

**行类型约束**：
- `entry_type = 'METRIC'`：`parent_id` 必须为 NULL，`metric` 必填，detail 字段均为 NULL
- `entry_type = 'DETAIL'`：`parent_id` 必须指向一个 METRIC 行，`metric` 可为 NULL（从父行继承）

**删除策略**：本期仅支持删除 DETAIL 行（物理删除），不支持删除 METRIC 行。

**索引建议**：
- `idx_entry_type_category` ON (`entry_type`, `category`, `display_order`) — 查询 METRIC 行按类别分组排序
- `idx_entry_parent_id` ON (`parent_id`, `created_at`) — 查询某 METRIC 行下的 DETAIL 行
- `uidx_entry_category_metric` UNIQUE ON (`category`, `metric`) WHERE `entry_type = 'METRIC'` — 保证同 category 下 metric 不重复（部分唯一索引）

---

## 6. 业务规则与计算公式

### 6.1 计算公式

本功能无系统自动计算。LG Formula 为自由文本，系统不解析。

### 6.2 状态流转规则

```
指标行：折叠 ↔ 展开（前端状态，不持久化）
```

### 6.3 数据校验规则

| 字段/场景 | 规则 |
|---------|------|
| category（新增） | 必填；必须为 BenchmarkCategory 枚举值；不可与已有类别重复 |
| categoryDisplayName（编辑） | 必填，不可为空字符串 |
| metric（新增） | 必填；必须为 BenchmarkMetric 枚举值且其 category 属性匹配；不可与同类别已有指标重复 |
| metricDisplayName（编辑） | 必填，不可为空字符串 |
| platform（detail） | 可选；有值时必须为 BenchmarkPlatform 枚举值 |
| dataType（detail） | 可选；有值时必须为 BenchmarkDataType 枚举值 |
| fyPeriod（detail） | 可选；有值时必须为合法年份数字（如 2020-2099） |
| 其他 detail 字段 | 可选，无格式校验 |

---

## 7. 异常处理

| 异常场景 | 错误码 | 后端处理 | 前端展示 |
|---------|--------|---------|---------|
| 新增类别名不在预定义列表 | 400 | 返回 `{ code: 400, message: "Invalid category name" }` | Toast 报错 |
| 类别已存在 | 409 | 返回 `{ code: 409, message: "Category already exists" }` | Toast 报错 |
| 指标不在该类别预定义列表 | 400 | 返回 `{ code: 400, message: "Invalid metric for this category" }` | Toast 报错 |
| 指标已存在于该类别下 | 409 | 返回 `{ code: 409, message: "Metric already exists in this category" }` | Toast 报错 |
| 类别/指标名编辑为空 | 400 | 返回 `{ code: 400, message: "Name cannot be empty" }` | 内联提示 "名称不能为空" |
| platform 枚举值非法 | 400 | 返回 `{ code: 400, message: "Invalid platform value" }` | Toast 报错 |
| dataType 枚举值非法 | 400 | 返回 `{ code: 400, message: "Invalid data type value" }` | Toast 报错 |
| 详情记录不存在（编辑/删除） | 404 | 返回 `{ code: 404, message: "Detail not found" }` | Toast 报错 |
| 网络异常 / 服务端 500 | 500 | 返回通用错误 | Toast "操作失败，请稍后重试"，3 秒消失 |
| 内联编辑保存失败 | 任意 | — | 恢复编辑前的值 + Toast 报错 |
| 删除失败 | 任意 | — | 数据行不移除 + Toast 报错 |

---

## 8. 开发注意事项

- **表格性能**：数据量预期不大（4 类别 × 5 指标 × N 条 detail），不需要分页或虚拟滚动，但仍需避免不必要的全量 re-render
- **枚举驱动**：类别、指标、平台、数据类型均使用 Java 枚举（BenchmarkCategory / BenchmarkMetric / BenchmarkPlatform / BenchmarkDataType），数据库存储枚举 name()，前端展示枚举 displayName
- **单表设计**：`fi_benchmark_entry` 通过 `entry_type` 和 `parent_id` 自引用区分 METRIC 行和 DETAIL 行，避免多表 JOIN
- **PATCH 语义**：detail 的内联编辑仅发送变更的字段（单字段 PATCH），不发送整行数据
- **左侧列固定**：确保在各种屏幕宽度下固定列不错位，尤其注意展开/折叠时 rowSpan 变化对固定列布局的影响
- **并发编辑**：本期不考虑多用户并发编辑的冲突问题，采用 last-write-wins 策略
- **数据持久化**：所有数据存入 PostgreSQL 主库，供 Benchmark 其他模块读取使用
- **外键级联**：删除 DETAIL 行使用物理删除；本期不支持删除 METRIC 行，无需配置级联删除
- **枚举序列化**：数据库存储枚举的 `name()`（大写下划线），接口 JSON 响应中同时返回枚举值和 displayName，前端下拉选项从接口获取枚举列表
