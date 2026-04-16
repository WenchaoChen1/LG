# Benchmark Entry 功能设计文档

> 版本：v1.1 定稿
> 更新日期：2026-03-23
> 修正：审查严重问题 3 个 + 技术疑点用户答案 5 个
> 需求来源：features/benchmark-entry-requirements/requirement/requirement-doc.md
> 截图来源：features/benchmark-entry-requirements/Benchmark Entry原始需求文档/42b2ad94-bd40-4dd2-bf33-5d66fbcd8911.png, features/benchmark-entry-requirements/Benchmark Entry原始需求文档/7c0160e3-c04a-4537-b098-0795f8d8ffb6.png
> 状态：定稿

---

## 1. 功能概述

Benchmark Entry 是面向投资分析团队的行业基准指标管理功能。SaaS 行业的基准数据分散在 Benchmarkit.ai、KeyBanc、High Alpha 等多个平台，本功能提供统一界面，按 Looking Glass（LG）指标体系将各平台的基准数据进行归类映射，集中管理和录入，使投资团队能在一屏内完成多维度的基准数据录入、查看与对比。

**核心功能范围：**
- 按 4 个固定 LG Category 分组展示 6 个固定 LG Metric，支持展开/折叠查看每个指标下的详情数据
- 详情数据的新增、编辑、删除（表格内联操作），支持确认/取消
- LG Formula 公式字段的内联编辑（失焦自动保存）
- 所有变更通过页面级"保存"按钮批量提交到后端持久化
- 年份选择器浮层组件

**关键约束：**
- Category 和 Metric 均为后端枚举管理，不可增删改
- 本期不做角色权限区分，所有登录用户拥有相同操作权限
- 数值字段（25th / Median / 75th / Best Guess）接受任意文本输入，不做格式校验
- 同一时间仅允许一行处于编辑/新增状态（编辑互斥）
- 货币单位切换功能本期不开发，延后

---

## 2. UI 界面设计

### 2.1 页面布局

页面复用 CIOaaS 平台现有 BasicLayout（侧边栏 + 顶部导航），页面自身包含标题区和主数据表格区。

```
+----------------------------------------------------------------------+
|  [CIOaaS 平台顶部导航（复用现有 Layout）]                               |
+----------+-----------------------------------------------------------+
|          |                                                           |
|          |  Benchmark Entry                              [Save]      |  <-- 标题区
|  CIOaaS  |  Manage and compare performance metrics across platforms  |
|  侧边栏   |                                                           |
| （复用    +-----------------------------------------------------------+
|  现有     |                                                           |
|  Layout） |  +-------------------------------------------------------+|
|          |  | LOOKING GLASS | LG METRIC  | LG      | PLATFORM | ... ||  <-- 表头
|          |  | CATEGORY      | NAME       | FORMULA |          |     ||
|          |  +---------------+------------+---------+----------+-----+|
|          |  | Revenue &     | v ARR      | Enter   | [详情行]  |     ||  <-- 展开
|          |  | Growth        |   Growth   | formula |          |     ||
|          |  | (纵向合并)     |   Rate     |         |          |     ||
|          |  |               +------------+---------+----------+-----+|
|          |  |               | + Add detail                          ||  <-- 按钮行
|          |  +---------------+------------+---------+----------+-----+|
|          |  | Profitability | > Gross    | Enter   |          | 2i  ||  <-- 折叠
|          |  | & Efficiency  |   Margin   | formula |          |     ||
|          |  +---------------+------------+---------+----------+-----+|
|          |  | Burn &        | > Monthly  | Enter   |          |     ||
|          |  | Runway        |  Net Burn  | formula |          |     ||
|          |  | (纵向合并)     +------------+---------+----------+-----+|
|          |  |               | > Monthly  | Enter   |          |     ||
|          |  |               |  Runway    | formula |          |     ||
|          |  +---------------+------------+---------+----------+-----+|
|          |  | Capital       | > Rule     | Enter   |          |     ||
|          |  | Efficiency    |  of 40     | formula |          |     ||
|          |  | (纵向合并)     +------------+---------+----------+-----+|
|          |  |               | > Sales    | Enter   |          |     ||
|          |  |               |  Efficiency| formula |          |     ||
|          |  |               |  Ratio     |         |          |     ||
|          |  +-------------------------------------------------------+|
|          |  <-- 横向滚动条（表格最小宽度 1100px，超出时出现）              |
+----------+-----------------------------------------------------------+
```

### 2.2 组件清单

| 组件名称 | 组件类型 | 位置 | 说明 |
|---------|---------|------|------|
| PageHeader | 标题区 | 页面顶部 | 包含主标题（28px, semibold, #0D2B56）、副标题（14px, 灰色）、保存按钮 |
| SaveButton | Button 按钮 | 标题区右侧 | 有未保存变更时高亮（primary 样式），无变更时默认样式（disabled 或淡色） |
| BenchmarkTable | 自定义表格 | 主内容区 | 不使用 Ant Design Table，需自定义实现以支持 Category 纵向合并和多行类型 |
| CategoryCell | 表格单元格 | 表格第 1 列 | 纵向合并单元格，背景浅色，带右侧和底部边框，垂直居中 |
| MetricRow | 表格行 | 表格 Metric 父行 | 包含展开/折叠箭头 + Metric 名称（加粗） + LG Formula 输入区 |
| FormulaInput | 内联文本输入 | Metric 父行第 3 列 | 默认透明边框，hover 显示边框，focus 主色调边框；占位文字 "Enter formula"，失焦自动保存 |
| DetailRow | 表格行 | 展开后的详情行 | 只读态：显示数据；hover 渐显编辑/删除按钮。编辑态：各字段变输入控件 |
| AddDetailRow | 表格行 | 详情行列表末尾 | "+ Add detail" 文字按钮行，新增行编辑时隐藏 |
| NewRow | 表格行 | 详情行列表末尾 | 高亮底色，所有子级字段为输入控件，行尾确认(check)/取消(x)按钮 |
| PlatformSelect | Select 下拉 | 详情行 Platform 列 | 选项从接口 `GET /api/web/benchmark/list` 响应的 `platformOptions` 字段获取 |
| DataSelect | Select 下拉 | 详情行 Data 列 | 选项：Actual / Forecast |
| YearPicker | 自定义年份选择器 | 详情行 FY Period 列 | 日历图标按钮触发浮层，3x4 网格显示 12 个年份，支持十年段翻页 |
| YearPickerPopover | Popover 浮层 | YearPicker 触发 | 宽度 240px，显示年份网格，当前年强调色，已选年主色，段外年半透明 |
| ActionButtons | 按钮组 | 详情行末列 | 只读态 hover：编辑(pencil) + 删除(trash, 红色)；编辑态：确认(check) + 取消(x) |
| EmptyState | 空状态组件 | 表格无数据时 | 数据库图标（40x40, 40%透明度）+ "No benchmark entries yet" + "Add entries to get started" |
| ItemCount | 文字提示 | Metric 父行尾部 | 折叠时显示 "{n} item(s)" |

### 2.3 数据展示规则

**表格列定义**

表格共 14 个数据列 + 1 个操作列：

| 列名 | 字段名 | 数据类型 | 宽度 | 对齐 | 所在行级别 | 显示格式 |
|------|--------|---------|------|------|----------|---------|
| LOOKING GLASS CATEGORY | `category` | string | 160px | 左对齐，垂直居中 | Metric 父行（纵向合并） | 常规字体 |
| LG METRIC NAME | `metricName` | string | 170px | 左对齐 | Metric 父行 | 加粗，前置展开/折叠箭头 |
| LG FORMULA | `formula` | string | 160px | 左对齐 | Metric 父行 | 内联文本输入，占位 "Enter formula" |
| PLATFORM | `platform` | string | 130px | 左对齐 | 详情行 | 只读文本 / 编辑态下拉 |
| EDITION | `edition` | string | 120px | 左对齐 | 详情行 | 只读文本 / 编辑态输入框 |
| METRIC NAME | `metricNameDetail` | string | 130px | 左对齐 | 详情行 | 只读文本 / 编辑态输入框 |
| DEFINITION | `definition` | string | 130px | 左对齐 | 详情行 | 只读文本 / 编辑态输入框 |
| FY PERIOD | `fyPeriod` | string | 110px | 左对齐 | 详情行 | 只读文本 / 编辑态年份选择器 |
| SEGMENT | `segment` | string | 100px | 左对齐 | 详情行 | 只读文本 / 编辑态输入框 |
| 25TH | `percentile25th` | string | 70px | 右对齐 | 详情行 | 等宽字体，只读 / 编辑态输入框 |
| MEDIAN | `median` | string | 70px | 右对齐 | 详情行 | 等宽字体，只读 / 编辑态输入框 |
| 75TH | `percentile75th` | string | 70px | 右对齐 | 详情行 | 等宽字体，只读 / 编辑态输入框 |
| DATA | `dataType` | string | 100px | 左对齐 | 详情行 | 只读文本 / 编辑态下拉 |
| BEST GUESS | `bestGuess` | string | 100px | 左对齐 | 详情行 | 只读文本 / 编辑态输入框 |
| （操作列） | -- | -- | 60px | -- | 详情行 | hover 显示编辑/删除；编辑态显示确认/取消 |

**表格整体样式**
- 外框：小圆角矩形，浅色边框
- 字体：Futura PT，14px
- 表头：浅灰背景，深蓝色文字，全大写，12px，中等字重，加宽字距
- 表格最小宽度 1100px，超出时横向滚动

**数字与颜色约定**
- 数值字段（25th / Median / 75th / Best Guess）为自由文本，不做格式化处理
- 空值字段显示 "--"（破折号），Metric Name 和数值字段空值不做特殊处理
- Category 单元格：浅色背景，带右侧和底部边框
- 详情行（只读）：柔和底色背景
- 新增行：高亮底色背景（与只读行区分）
- 删除按钮：红色图标

### 2.4 交互行为

| 触发元素 | 触发方式 | 效果描述 |
|---------|---------|---------|
| Metric 名称区域 | click | 切换该 Metric 的展开/折叠状态；展开时箭头 > 变 v，显示详情行 + "Add detail" 按钮行；折叠时箭头 v 变 >，隐藏详情区域，显示 "{n} item(s)" 计数（有数据时） |
| "+ Add detail" 按钮 | click | 在详情列表末尾插入空白新增行（高亮底色），按钮自身隐藏；若当前有其他编辑行则自动取消该行 |
| 新增行确认按钮 (check) | click | 校验至少一个字段已填写 + Platform+FY Period 组合唯一；通过后暂存前端状态，行变只读 |
| 新增行取消按钮 (x) | click | 移除新增行，丢弃输入，"Add detail" 按钮恢复显示 |
| 详情行 | hover | 行背景变为悬停色，行尾渐显编辑按钮和删除按钮 |
| 详情行 | mouse leave | 行背景恢复，编辑/删除按钮渐隐 |
| 编辑按钮 (pencil) | click | 该行进入编辑态，字段变输入控件，操作列变确认/取消；若有其他编辑行则自动取消 |
| 编辑行确认按钮 (check) | click | 校验同新增行；通过后更新前端状态，行恢复只读 |
| 编辑行取消按钮 (x) | click | 丢弃修改，恢复编辑前的值，行恢复只读 |
| 删除按钮 (trash) | click | 立即从前端列表移除该行（标记删除），无确认弹窗 |
| Enter 键 | keydown | 在新增/编辑行的任意输入框按 Enter，等同于点击确认按钮 |
| LG Formula 输入区 | focus | 边框从透明变为主色调可见 |
| LG Formula 输入区 | blur | 自动调用后端保存公式接口，边框恢复透明 |
| LG Formula 输入区 | hover | 边框从透明变为可见 |
| 保存按钮 | click | 将所有未保存变更（新增、编辑、删除）批量提交后端；成功后提示 "Save successful"；失败后提示错误信息 |
| 年份选择器按钮 | click | 弹出年份选择浮层（240px），3x4 网格 |
| 年份选择浮层中的年份 | click | 选中年份，浮层关闭 |
| 年份选择浮层左右箭头 | click | 切换十年段（每次 +/-10 年） |
| 浏览器后退/关闭/导航离开 | beforeunload | 若有未保存变更，弹出确认框 "有未保存的更改，是否确认离开？" |

### 2.5 空态与加载态

| 场景 | 展示方式 |
|------|---------|
| 页面首次加载 | 全表格区域显示 Spin 加载动画 |
| 数据加载成功但无任何详情数据 | 固定的 6 个 Metric 父行正常显示（Category + Metric Name + LG Formula），展开后无详情行仅显示 "Add detail" 按钮 |
| 表格结构数据为空（异常情况） | 显示空状态组件：数据库图标（40x40, 40%透明度） + "No benchmark entries yet"（14px, 中等字重）+ "Add entries to get started"（12px），垂直居中，上下内边距 64px |
| 保存中 | 保存按钮显示加载状态（loading），禁止重复点击 |
| LG Formula 保存中 | 输入框可保持可输入状态，不阻塞用户操作（后台静默保存） |
| 接口报错 | Ant Design message.error 全局提示，显示错误信息 |

---

## 3. 前端实现要点

### 3.1 路由与文件结构

```
路由：/benchmarkEntry
路由配置（config/routes.ts 根级新增，不嵌套在 BasicLayout / SecurityLayout 内）：
  {
    path: '/benchmarkEntry',
    name: 'Benchmark Entry',
    component: './benchmarkEntry/index',
  }

文件目录：src/pages/benchmarkEntry/
  ├── index.tsx                      # 页面入口组件
  ├── index.less                     # 页面样式
  ├── components/
  │   ├── PageHeader/
  │   │   ├── index.tsx              # 标题区组件（标题 + 保存按钮）
  │   │   └── index.less
  │   ├── BenchmarkTable/
  │   │   ├── index.tsx              # 主表格组件（自定义实现，非 Ant Design Table）
  │   │   └── index.less
  │   ├── MetricRow/
  │   │   ├── index.tsx              # Metric 父行组件（展开/折叠 + Formula）
  │   │   └── index.less
  │   ├── DetailRow/
  │   │   ├── index.tsx              # 详情行组件（只读/编辑两种模式）
  │   │   └── index.less
  │   ├── NewRow/
  │   │   ├── index.tsx              # 新增行组件
  │   │   └── index.less
  │   ├── YearPicker/
  │   │   ├── index.tsx              # 年份选择器组件
  │   │   └── index.less
  │   ├── EmptyState/
  │   │   ├── index.tsx              # 空状态组件
  │   │   └── index.less
  │   └── ActionButtons/
  │       ├── index.tsx              # 操作按钮组（编辑/删除/确认/取消）
  │       └── index.less
  └── __tests__/                     # 测试目录

API 服务文件：src/services/api/benchmark/
  ├── benchmarkService.ts            # Benchmark Entry 相关 API 请求
  └── types.ts                       # TypeScript 接口类型定义（DTO）
```

### 3.2 状态管理

采用页面级本地状态（React useState/useReducer），不使用 dva 全局 model。理由：Benchmark Entry 是独立页面，数据不需要跨页面共享。

```
需要维护的状态：
- metricsData: MetricData[]           -- 完整的指标数据（包含 Category、Metric、详情行）
- platformOptions: string[]           -- Platform 下拉选项列表（从接口获取）
- expandedMetrics: Set<string>        -- 当前展开的 Metric key 集合
- editingRowId: string | null         -- 当前正在编辑的详情行 ID（编辑互斥）
- addingMetricKey: string | null      -- 当前正在新增详情行的 Metric key
- newRowData: DetailRowData | null    -- 新增行的临时数据
- editRowData: DetailRowData | null   -- 编辑行的临时数据（编辑前的副本用于取消恢复）
- pendingChanges: PendingChanges      -- 未保存的变更集合 { added: [], updated: [], deleted: [] }
- loading: boolean                    -- 页面加载状态
- saving: boolean                     -- 保存中状态
- isDirty: boolean                    -- 是否有未保存变更（derived from pendingChanges）
```

**TypeScript 类型定义（位于 `src/services/api/benchmark/types.ts`）：**

```typescript
/** GET /api/web/benchmark/list 响应中的顶层结构 */
interface BenchmarkListResponse {
  platformOptions: string[];          // Platform 下拉选项列表
  categories: CategoryData[];         // 分类数据
}

interface CategoryData {
  category: string;                   // LG Category 枚举值
  categoryDisplayName: string;        // 展示名称
  metrics: MetricData[];
}

interface MetricData {
  metricKey: string;                  // Metric 枚举标识（如 ARR_GROWTH_RATE）
  metricName: string;                 // LG Metric Name
  formula: string;                    // LG Formula
  details: DetailRowData[];           // 详情行列表
}

interface DetailRowData {
  id: string;                         // UUID，新增时前端生成临时 ID
  metricKey: string;                  // 所属 Metric 枚举标识
  platform: string;                   // 平台枚举值
  platformDisplayName: string;        // 平台展示名称
  edition: string;
  metricNameDetail: string;           // 平台方指标名称
  definition: string;
  fyPeriod: string;                   // 4 位年份字符串
  segment: string;
  percentile25th: string;
  median: string;
  percentile75th: string;
  dataType: string;                   // Actual / Forecast 枚举值
  dataTypeDisplayName: string;        // 数据类型展示名称
  bestGuess: string;
  version: number;                    // 乐观锁版本号
  isNew?: boolean;                    // 前端标记：新增未保存
  isModified?: boolean;               // 前端标记：已修改未保存
}

interface PendingChanges {
  added: DetailRowData[];             // 新增的行
  updated: DetailRowData[];           // 修改的行（含 version）
  deleted: string[];                  // 删除的行 ID 列表
}

/** PUT /api/web/benchmark/formula 请求体 */
interface FormulaUpdateRequest {
  metricKey: string;
  formula: string;
  version: number;
}

/** PUT /api/web/benchmark/formula 响应 data */
interface FormulaUpdateResponse {
  version: number;                    // 更新后的新版本号
}
```

### 3.3 关键实现说明

1. **自定义表格而非 Ant Design Table**：由于 Category 纵向合并单元格需要随展开/折叠状态动态变化行数，且行类型多样（Metric 父行、详情行、新增行、按钮行），建议使用 `<table>` 原生 HTML + CSS 自定义实现，通过 `rowSpan` 动态计算合并行数。

2. **Category 纵向合并行数计算**：每个 Category 的 rowSpan = 该 Category 下所有 Metric 的行数之和。每个 Metric 的行数 = 1（父行）+ 展开时的详情行数 + 展开时的 "Add detail" 按钮行（1） + 展开时的新增行（0 或 1）。

3. **编辑互斥逻辑**：当用户触发新的编辑或新增操作时，先检查 `editingRowId` 和 `addingMetricKey`，若有则自动取消（恢复原值或移除新增行），再进入新的编辑状态。

4. **未保存变更追踪**：每次新增确认、编辑确认、删除操作后，将变更记录到 `pendingChanges`。保存成功后清空 `pendingChanges`。`isDirty` 可由 `pendingChanges` 派生：`added.length > 0 || updated.length > 0 || deleted.length > 0`。

5. **离开页面保护**：通过监听 `window.beforeunload` 事件实现。在 `useEffect` 中注册/注销监听器，当 `isDirty` 为 true 时阻止离开。

6. **LG Formula 自动保存**：FormulaInput 组件在 `onBlur` 事件中调用后端保存接口。使用防抖（debounce 300ms）避免频繁请求。保存失败时用 `message.error` 提示但不阻塞用户操作。请求和响应中都需要携带/接收 `version` 字段。

7. **年份选择器组件**：自定义实现，不使用 Ant Design DatePicker。浮层通过 `Popover` 或 `Portal` 渲染。当前十年段范围计算：`decadeStart = Math.floor(currentYear / 10) * 10`，显示 `decadeStart - 1` 到 `decadeStart + 10`（共 12 个年份）。

8. **Platform + FY Period 唯一性校验**：前端在确认新增/编辑时，遍历当前 Metric 下所有详情行（排除当前正在编辑的行），检查是否存在相同 Platform + FY Period 组合。仅当两个字段都已填写时才校验。

9. **保存按钮视觉反馈**：当 `isDirty` 为 true 时，保存按钮使用 primary 样式（高亮）；否则使用 default 样式。保存中时按钮显示 loading 状态。

10. **Platform 下拉选项来源**：前端不硬编码 Platform 选项，而是从 `GET /api/web/benchmark/list` 响应中的 `platformOptions` 字段获取，页面加载时缓存到 `platformOptions` state 中。

11. **乐观锁版本号管理**：前端需在 `updated` 列表中为每行附带当前的 `version` 值；保存成功后刷新数据以获取最新 `version`。Formula 保存同理，请求携带 `version`，响应返回新 `version` 并更新前端状态。

---

## 4. 后端接口设计

### 4.1 接口汇总

| 接口名称 | 方法 | Controller 路径 | 前端调用路径 | 用途 |
|---------|------|----------------|-------------|------|
| 获取 Benchmark 全量数据 | GET | `/benchmark/list` | `/api/web/benchmark/list` | 页面加载时获取所有 Category、Metric 及详情数据和 Platform 选项 |
| 批量保存变更 | POST | `/benchmark/save` | `/api/web/benchmark/save` | 批量提交新增、编辑、删除的详情数据 |
| 保存 LG Formula | PUT | `/benchmark/formula` | `/api/web/benchmark/formula` | 单个 Metric 的公式自动保存 |

> **路径说明**：后端 Controller 使用 `@RequestMapping("/benchmark")`，网关统一添加 `/api/web/` 前缀进行路由转发。前端服务文件中使用完整路径 `/api/web/benchmark/...`。

### 4.2 接口详情

---

#### GET `/api/web/benchmark/list`

**用途**：页面加载时获取所有 Benchmark 数据，包含 Platform 下拉选项、Category 分组、Metric 列表、每个 Metric 下的详情数据和公式。

**请求参数**

无请求参数。

**响应结构**

```json
{
  "success": true,
  "message": null,
  "code": "0",
  "data": {
    "platformOptions": ["Benchmarkit.ai", "KeyBanc", "High Alpha"],
    "categories": [
      {
        "category": "REVENUE_AND_GROWTH",
        "categoryDisplayName": "Revenue & Growth",
        "metrics": [
          {
            "metricKey": "ARR_GROWTH_RATE",
            "metricName": "ARR Growth Rate",
            "formula": "(Current ARR - Previous ARR) / Previous ARR",
            "formulaVersion": 3,
            "details": [
              {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "metricKey": "ARR_GROWTH_RATE",
                "platform": "BENCHMARKIT_AI",
                "platformDisplayName": "Benchmarkit.ai",
                "edition": "2024 Edition",
                "metricNameDetail": "ARR Growth",
                "definition": "Year-over-year ARR growth rate",
                "fyPeriod": "2024",
                "segment": "$1M-$10M ARR",
                "percentile25th": "15%",
                "median": "25%",
                "percentile75th": "40%",
                "dataType": "ACTUAL",
                "dataTypeDisplayName": "Actual",
                "bestGuess": "30%",
                "version": 0
              }
            ]
          }
        ]
      },
      {
        "category": "PROFITABILITY_AND_EFFICIENCY",
        "categoryDisplayName": "Profitability & Efficiency",
        "metrics": [
          {
            "metricKey": "GROSS_MARGIN",
            "metricName": "Gross Margin",
            "formula": "",
            "formulaVersion": 0,
            "details": []
          }
        ]
      },
      {
        "category": "BURN_AND_RUNWAY",
        "categoryDisplayName": "Burn & Runway",
        "metrics": [
          {
            "metricKey": "MONTHLY_NET_BURN_RATE",
            "metricName": "Monthly Net Burn Rate",
            "formula": "",
            "formulaVersion": 0,
            "details": []
          },
          {
            "metricKey": "MONTHLY_RUNWAY",
            "metricName": "Monthly Runway",
            "formula": "",
            "formulaVersion": 0,
            "details": []
          }
        ]
      },
      {
        "category": "CAPITAL_EFFICIENCY",
        "categoryDisplayName": "Capital Efficiency",
        "metrics": [
          {
            "metricKey": "RULE_OF_40",
            "metricName": "Rule of 40",
            "formula": "",
            "formulaVersion": 0,
            "details": []
          },
          {
            "metricKey": "SALES_EFFICIENCY_RATIO",
            "metricName": "Sales Efficiency Ratio",
            "formula": "",
            "formulaVersion": 0,
            "details": []
          }
        ]
      }
    ]
  }
}
```

**后端业务逻辑**

1. 从 `Platform` 枚举动态生成 `platformOptions` 列表（取每个枚举值的 `displayName`）
2. 查询 `benchmark_detail` 表获取所有详情数据，按 `metric_key` 分组
3. 按固定的 Category-Metric 枚举映射关系组装嵌套响应结构，填入每个 metric 的 `formula`、`version`（作为 `formulaVersion`）和对应的 `details`
4. Platform 和 DataType 枚举值转换为 displayName 返回
5. 涉及表：`benchmark_detail`

---

#### POST `/api/web/benchmark/save`

**用途**：批量提交页面上所有未保存的变更（新增、编辑、删除），保证事务一致性。

**请求参数**（Body）

```json
{
  "added": [
    {
      "metricKey": "ARR_GROWTH_RATE",
      "platform": "BENCHMARKIT_AI",
      "edition": "2024 Edition",
      "metricNameDetail": "ARR Growth",
      "definition": "Year-over-year ARR growth rate",
      "fyPeriod": "2024",
      "segment": "$1M-$10M ARR",
      "percentile25th": "15%",
      "median": "25%",
      "percentile75th": "40%",
      "dataType": "ACTUAL",
      "bestGuess": "30%"
    }
  ],
  "updated": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "version": 0,
      "metricKey": "ARR_GROWTH_RATE",
      "platform": "KEYBANC",
      "edition": "2024 SaaS Survey",
      "metricNameDetail": "Revenue Growth",
      "definition": "Annual recurring revenue growth",
      "fyPeriod": "2024",
      "segment": "All",
      "percentile25th": "12%",
      "median": "22%",
      "percentile75th": "35%",
      "dataType": "ACTUAL",
      "bestGuess": "25%"
    }
  ],
  "deleted": [
    "660e8400-e29b-41d4-a716-446655440001"
  ]
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `added` | array | 否 | 新增的详情行列表 |
| `added[].metricKey` | string | 是 | 所属 Metric 枚举标识（如 `ARR_GROWTH_RATE`） |
| `added[].platform` | string | 否 | 平台枚举值：BENCHMARKIT_AI / KEYBANC / HIGH_ALPHA |
| `added[].edition` | string | 否 | 版本/期次 |
| `added[].metricNameDetail` | string | 否 | 平台方指标名称 |
| `added[].definition` | string | 否 | 定义说明 |
| `added[].fyPeriod` | string | 否 | 4 位年份 |
| `added[].segment` | string | 否 | 细分市场 |
| `added[].percentile25th` | string | 否 | 25 分位值（自由文本） |
| `added[].median` | string | 否 | 中位数（自由文本） |
| `added[].percentile75th` | string | 否 | 75 分位值（自由文本） |
| `added[].dataType` | string | 否 | 数据类型枚举：ACTUAL / FORECAST |
| `added[].bestGuess` | string | 否 | 最佳猜测值 |
| `updated` | array | 否 | 修改的详情行列表，结构同 added 但必须包含 `id` 和 `version` |
| `updated[].id` | string | 是 | 详情行 UUID |
| `updated[].version` | integer | 是 | 当前乐观锁版本号 |
| `deleted` | array | 否 | 删除的详情行 ID 列表 |

**响应结构**

```json
{
  "success": true,
  "message": "Save successful",
  "code": "0",
  "data": null
}
```

> 保存成功后，前端应重新调用 `GET /api/web/benchmark/list` 刷新数据（获取最新的 `version` 和服务端生成的 `id`）。

**后端业务逻辑**

1. 开启事务（`@Transactional`）
2. **校验**：
   - 遍历 `added` 和 `updated`，校验每行至少有一个业务字段非空（排除 `id`、`metricKey`、`version`）
   - 校验 `metricKey` 是否为有效 `MetricKey` 枚举值；无效则抛 `BadRequestException("Invalid metric key: {metricKey}")`
   - 校验 `platform` 是否为有效 `Platform` 枚举值（若非空）；无效则抛 `BadRequestException("Invalid platform: {value}")`
   - 校验 `dataType` 是否为有效 `DataType` 枚举值（若非空）；无效则抛 `BadRequestException("Invalid data type: {value}")`
   - **唯一性校验**：校验同一 `metricKey` 下 `platform` + `fyPeriod` 组合的唯一性（仅当两字段均非空时校验）。校验范围 = （数据库现有数据 - deleted 中的 ID - updated 中原有的 ID） + updated 中更新后的数据 + added 数据。**added 列表内部也需要互相检查**（例如两条 added 记录有相同 metricKey + platform + fyPeriod）。违反唯一性则抛 `BadRequestException("Duplicate platform and FY period combination for metric: {metricName}")`
3. **删除**：批量删除 `deleted` 列表中的记录（`DELETE FROM benchmark_detail WHERE id IN (...)`），不存在的 ID 静默跳过（幂等处理）
4. **新增**：为 `added` 列表中的每条记录生成 UUID，写入 `metric_key` 字段，设置 `version = 0`，批量插入 `benchmark_detail`
5. **更新**：逐条更新 `updated` 列表中的记录，SQL 加乐观锁条件：`UPDATE benchmark_detail SET ... , version = version + 1 WHERE id = :id AND version = :version`。若影响行数为 0，抛 `OptimisticLockException`（消息："数据已被他人修改，请刷新后重试"）
6. 提交事务
7. 涉及表：`benchmark_detail`

---

#### PUT `/api/web/benchmark/formula`

**用途**：保存单个 Metric 的 LG Formula（失焦自动触发）。

**请求参数**（Body）

```json
{
  "metricKey": "ARR_GROWTH_RATE",
  "formula": "(Current ARR - Previous ARR) / Previous ARR",
  "version": 3
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `metricKey` | string | 是 | Metric 枚举标识 |
| `formula` | string | 是 | 公式文本内容（可为空字符串表示清空） |
| `version` | integer | 是 | 当前乐观锁版本号 |

**响应结构**

```json
{
  "success": true,
  "message": null,
  "code": "0",
  "data": {
    "version": 4
  }
}
```

**后端业务逻辑**

1. 校验 `metricKey` 是否为有效枚举值；无效则抛 `BadRequestException("Invalid metric key: {metricKey}")`
2. 更新 `benchmark_detail` 表中 `metric_key = :metricKey` 的记录的 `formula` 字段，加乐观锁条件：`UPDATE benchmark_detail SET formula = :formula, version = version + 1 WHERE metric_key = :metricKey AND version = :version`。若影响行数为 0，抛 `OptimisticLockException`（消息："数据已被他人修改，请刷新后重试"）
3. 返回更新后的新 `version` 值
4. 涉及表：`benchmark_detail`

---

## 5. 数据模型

### 5.1 涉及表结构

本功能采用**单表设计**。所有指标元数据（Category、Metric、Formula）和详情数据统一存储在 `benchmark_detail` 表中。Category 和 Metric 通过后端 Java 枚举管理，不单独建表。

**表：`benchmark_detail`**

存储每个 Metric 的公式和基准数据详情行。对于 6 个固定 Metric，每个 Metric 的 `formula` 字段存储在该 Metric 下的任意一条详情行中（或通过枚举映射在 Service 层管理）。

> 设计说明：由于 Category 和 Metric 均为固定枚举（4 Category / 6 Metric），无需单独建表维护。`metric_key` 字段直接存储枚举字符串，通过 `CHECK` 约束保证值的有效性。Formula 字段作为 Metric 级别的属性，独立于详情行存在——在数据库层面，每个 `metric_key` 对应一条 formula 记录（没有详情行的 Metric 也有 formula 行）。具体实现方式：每个 metric_key 在表中至少有一条 `is_formula_row = true` 的记录用于存储 formula 和 formula 的 version，详情行的 `is_formula_row = false`。

```sql
CREATE TABLE benchmark_detail (
    id                  VARCHAR(36)   NOT NULL PRIMARY KEY,   -- UUID 主键
    metric_key          VARCHAR(50)   NOT NULL,               -- Metric 枚举标识
    formula             TEXT          DEFAULT '',              -- LG Formula 公式文本（仅 formula 行使用）
    is_formula_row      BOOLEAN       NOT NULL DEFAULT FALSE, -- 是否为 formula 行（每个 metric_key 一条）
    platform            VARCHAR(30),                          -- 平台枚举值
    edition             VARCHAR(255),                         -- 版本/期次
    metric_name_detail  VARCHAR(255),                         -- 平台方指标名称
    definition          VARCHAR(500),                         -- 定义说明
    fy_period           VARCHAR(4),                           -- 财年，4 位年份字符串
    segment             VARCHAR(255),                         -- 细分市场
    percentile_25th     VARCHAR(100),                         -- 25 分位值（自由文本）
    median              VARCHAR(100),                         -- 中位数（自由文本）
    percentile_75th     VARCHAR(100),                         -- 75 分位值（自由文本）
    data_type           VARCHAR(20),                          -- 数据类型枚举
    best_guess          VARCHAR(255),                         -- 最佳猜测值
    version             INTEGER       NOT NULL DEFAULT 0,     -- 乐观锁版本号
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(), -- 创建时间
    created_by          VARCHAR(36),                          -- 创建人
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(), -- 更新时间
    updated_by          VARCHAR(36),                          -- 更新人

    CONSTRAINT chk_metric_key CHECK (metric_key IN (
        'ARR_GROWTH_RATE',
        'GROSS_MARGIN',
        'MONTHLY_NET_BURN_RATE',
        'MONTHLY_RUNWAY',
        'RULE_OF_40',
        'SALES_EFFICIENCY_RATIO'
    )),
    CONSTRAINT chk_platform CHECK (platform IS NULL OR platform IN (
        'BENCHMARKIT_AI',
        'KEYBANC',
        'HIGH_ALPHA'
    )),
    CONSTRAINT chk_data_type CHECK (data_type IS NULL OR data_type IN (
        'ACTUAL',
        'FORECAST'
    ))
);

-- 索引
CREATE INDEX idx_benchmark_detail_metric_key ON benchmark_detail(metric_key);
CREATE INDEX idx_benchmark_detail_platform_fy ON benchmark_detail(metric_key, platform, fy_period);
CREATE UNIQUE INDEX idx_benchmark_detail_formula_row ON benchmark_detail(metric_key) WHERE is_formula_row = TRUE;

COMMENT ON TABLE benchmark_detail IS 'Benchmark 数据表，存储指标公式和各平台基准详情数据';
COMMENT ON COLUMN benchmark_detail.metric_key IS 'Metric 枚举标识：ARR_GROWTH_RATE, GROSS_MARGIN, MONTHLY_NET_BURN_RATE, MONTHLY_RUNWAY, RULE_OF_40, SALES_EFFICIENCY_RATIO';
COMMENT ON COLUMN benchmark_detail.formula IS 'LG Formula 公式文本，仅 is_formula_row=true 的行使用';
COMMENT ON COLUMN benchmark_detail.is_formula_row IS '标识该行是否为 formula 行（每个 metric_key 恰好一条）';
COMMENT ON COLUMN benchmark_detail.platform IS '平台枚举：BENCHMARKIT_AI, KEYBANC, HIGH_ALPHA';
COMMENT ON COLUMN benchmark_detail.percentile_25th IS '25 分位值，自由文本输入';
COMMENT ON COLUMN benchmark_detail.median IS '中位数，自由文本输入';
COMMENT ON COLUMN benchmark_detail.percentile_75th IS '75 分位值，自由文本输入';
COMMENT ON COLUMN benchmark_detail.data_type IS '数据类型枚举：ACTUAL, FORECAST';
COMMENT ON COLUMN benchmark_detail.version IS '乐观锁版本号，每次更新 +1';
```

**初始化数据（6 条 formula 行）：**

```sql
INSERT INTO benchmark_detail (id, metric_key, is_formula_row, formula, version) VALUES
    (gen_random_uuid(), 'ARR_GROWTH_RATE', TRUE, '', 0),
    (gen_random_uuid(), 'GROSS_MARGIN', TRUE, '', 0),
    (gen_random_uuid(), 'MONTHLY_NET_BURN_RATE', TRUE, '', 0),
    (gen_random_uuid(), 'MONTHLY_RUNWAY', TRUE, '', 0),
    (gen_random_uuid(), 'RULE_OF_40', TRUE, '', 0),
    (gen_random_uuid(), 'SALES_EFFICIENCY_RATIO', TRUE, '', 0);
```

### 5.2 关联关系

单表设计，无外键关联。

- `metric_key` 通过 `CHECK` 约束保证值的有效性，与后端 Java `MetricKey` 枚举对应
- 每个 `metric_key` 恰好有一条 `is_formula_row = TRUE` 的记录（通过 partial unique index 保证），用于存储 formula
- 每个 `metric_key` 下可有 0~N 条 `is_formula_row = FALSE` 的详情行
- Category 信息完全由后端枚举 `MetricKey` 的映射关系提供（`MetricKey.ARR_GROWTH_RATE -> Category.REVENUE_AND_GROWTH`），不在数据库中存储

---

## 6. 业务规则与计算公式

### 6.1 计算公式

本功能不涉及系统自动计算逻辑。LG Formula 字段是用户手动录入的文本公式，系统不解析或执行。

典型公式示例（供参考，非系统计算）：

| 指标 | 公式示例 |
|------|---------|
| ARR Growth Rate | (Current ARR - Previous ARR) / Previous ARR |
| Gross Margin | (Revenue - COGS) / Revenue |
| Monthly Net Burn Rate | Monthly Cash Out - Monthly Cash In |
| Rule of 40 | Revenue Growth Rate + Profit Margin |

### 6.2 枚举定义

**Category 枚举（后端 Java enum `Category`）**

| 枚举值 | 展示名称 | 包含 Metric |
|--------|---------|------------|
| `REVENUE_AND_GROWTH` | Revenue & Growth | ARR Growth Rate |
| `PROFITABILITY_AND_EFFICIENCY` | Profitability & Efficiency | Gross Margin |
| `BURN_AND_RUNWAY` | Burn & Runway | Monthly Net Burn Rate, Monthly Runway |
| `CAPITAL_EFFICIENCY` | Capital Efficiency | Rule of 40, Sales Efficiency Ratio |

**MetricKey 枚举（后端 Java enum `MetricKey`）**

| 枚举值 | 展示名称 | 所属 Category | 排序 |
|--------|---------|--------------|------|
| `ARR_GROWTH_RATE` | ARR Growth Rate | REVENUE_AND_GROWTH | 1 |
| `GROSS_MARGIN` | Gross Margin | PROFITABILITY_AND_EFFICIENCY | 2 |
| `MONTHLY_NET_BURN_RATE` | Monthly Net Burn Rate | BURN_AND_RUNWAY | 3 |
| `MONTHLY_RUNWAY` | Monthly Runway | BURN_AND_RUNWAY | 4 |
| `RULE_OF_40` | Rule of 40 | CAPITAL_EFFICIENCY | 5 |
| `SALES_EFFICIENCY_RATIO` | Sales Efficiency Ratio | CAPITAL_EFFICIENCY | 6 |

> `MetricKey` 枚举中包含 `displayName`、`category`、`sortOrder` 属性，后端根据枚举定义动态生成 Category-Metric 映射关系，无需数据库维护。

**Platform 枚举（后端 Java enum `Platform`）**

| 枚举值 | 展示名称 |
|--------|---------|
| `BENCHMARKIT_AI` | Benchmarkit.ai |
| `KEYBANC` | KeyBanc |
| `HIGH_ALPHA` | High Alpha |

> `GET /api/web/benchmark/list` 响应中的 `platformOptions` 字段由后端从 `Platform` 枚举动态生成（取每个枚举的 `displayName`），前端不硬编码。

**DataType 枚举（后端 Java enum `DataType`）**

| 枚举值 | 展示名称 |
|--------|---------|
| `ACTUAL` | Actual |
| `FORECAST` | Forecast |

### 6.3 数据校验规则

| 字段/场景 | 规则 |
|---------|------|
| 新增/编辑详情行提交 | 至少一个业务字段非空方可提交（排除 id、metricKey、version）；全空时前端提示 "请至少填写一个字段" 并阻止 |
| Platform + FY Period 唯一性 | 同一 Metric 下，Platform + FY Period 组合不允许重复；仅当两个字段均已填写时校验；违反时前端提示 "该平台和年度组合已存在" 并阻止 |
| **added 列表内部唯一性** | 批量保存时，added 列表中多条记录之间也需要校验 metricKey + platform + fyPeriod 组合的唯一性（不仅仅与数据库已有数据比较） |
| **唯一性校验完整范围** | 校验范围 = （数据库现有数据 - deleted 中的 ID - updated 中原有的 ID） + updated 中更新后的数据 + added 数据 |
| Platform 字段 | 下拉选择，仅允许选择枚举值或留空 |
| FY Period 字段 | 通过年份选择器选择，不支持手动键入，值为 4 位年份字符串 |
| Data 字段 | 下拉选择，仅允许 Actual / Forecast 或留空 |
| 数值字段（25th / Median / 75th / Best Guess） | 接受任意文本输入，不做格式校验或转换 |
| LG Formula | 自由文本输入，无字符数限制，支持中英文及特殊字符 |
| metricKey（后端校验） | 必须为有效 MetricKey 枚举值 |
| platform（后端校验） | 若非空则必须为有效 Platform 枚举值 |
| dataType（后端校验） | 若非空则必须为有效 DataType 枚举值 |
| 编辑互斥 | 同一时间仅允许一行处于编辑/新增状态；新操作自动取消当前编辑行 |
| 删除无确认 | 删除即时在前端状态移除，无二次确认弹窗，不可撤销 |

### 6.4 Category 纵向合并行数计算规则

每个 Category 的 `rowSpan` 动态计算公式：

```
categoryRowSpan = SUM(metricRowCount) for each metric in category

metricRowCount =
  1 (Metric 父行)
  + (isExpanded ? details.length : 0)                       // 详情行
  + (isExpanded ? 1 : 0)                                    // "Add detail" 按钮行
  + (isExpanded && addingMetricKey === metricKey ? 1 : 0)   // 正在新增的空白行
```

### 6.5 展开/折叠规则

- 多个 Metric 可同时展开，互不干扰
- 折叠时若有详情数据，Metric 父行尾部显示 `"{n} item(s)"` 文字提示
- 展开/折叠不影响其他 Metric 的编辑状态

### 6.6 保存按钮状态规则

| 条件 | 按钮状态 |
|------|---------|
| pendingChanges 为空（无新增/编辑/删除） | 默认样式（default），可点击但不高亮 |
| pendingChanges 非空（有未保存变更） | 高亮样式（primary） |
| 正在保存中 | 显示 loading 动画，禁止重复点击 |

### 6.7 乐观锁更新规则

- 每条记录（包括 formula 行和详情行）都有 `version` 字段，初始值为 0
- 每次更新操作（编辑详情行、保存 formula）在 SQL 的 `WHERE` 子句中加 `AND version = :version`，同时 `SET version = version + 1`
- 若 `UPDATE` 影响行数为 0，说明该记录已被其他用户修改，抛出 `OptimisticLockException`
- 前端收到乐观锁冲突错误后，提示用户"数据已被他人修改，请刷新后重试"，用户刷新页面即可获取最新数据

---

## 7. 异常处理

所有业务异常统一由 `GlobalExceptionHandler` 捕获处理，返回 HTTP 200 + `Result.fail(msg)` 格式。后端不直接在 Controller 中构造 `Result.fail`，而是通过抛出对应异常类来触发。

**异常抛出规范：**
- 业务校验失败（枚举无效、全字段为空、唯一性冲突等）：抛 `BadRequestException(msg)`
- 数据不存在：抛 `EntityNotFoundException(clazz, field, val)`
- 乐观锁冲突：抛 `OptimisticLockException(msg)`（自定义异常，需在 `GlobalExceptionHandler` 中新增处理，统一返回 HTTP 200 + `Result.fail(msg)`）

| 异常场景 | 后端异常类 | 异常消息 | 前端展示 |
|---------|-----------|---------|---------|
| 页面加载失败（网络异常） | -- | -- | `message.error("Failed to load benchmark data, please try again")` |
| 保存时 metricKey 无效 | `BadRequestException` | `"Invalid metric key: {metricKey}"` | `message.error` 显示后端返回的 message |
| 保存时 platform 枚举值无效 | `BadRequestException` | `"Invalid platform: {value}"` | `message.error` 显示后端返回的 message |
| 保存时 dataType 枚举值无效 | `BadRequestException` | `"Invalid data type: {value}"` | `message.error` 显示后端返回的 message |
| 保存时详情行全部字段为空 | `BadRequestException` | `"At least one field must be filled"` | `message.error` 显示后端返回的 message |
| 保存时 Platform + FY Period 组合重复 | `BadRequestException` | `"Duplicate platform and FY period combination for metric: {metricName}"` | `message.error` 显示后端返回的 message |
| 保存时删除的 ID 不存在 | 静默跳过 | 不报错（幂等处理） | 无影响 |
| 更新的详情行 ID 不存在 | `EntityNotFoundException` | `"BenchmarkDetail with id {id} does not exist"` | `message.error` 显示后端返回的 message |
| 乐观锁冲突（更新详情行） | `OptimisticLockException` | `"数据已被他人修改，请刷新后重试"` | `message.error("数据已被他人修改，请刷新后重试")` |
| 乐观锁冲突（保存 formula） | `OptimisticLockException` | `"数据已被他人修改，请刷新后重试"` | `message.error("数据已被他人修改，请刷新后重试")` |
| Formula 保存失败（网络异常） | -- | -- | `message.error("公式保存失败，请重试")`，不阻塞用户操作 |
| Formula 保存时 metricKey 无效 | `BadRequestException` | `"Invalid metric key: {metricKey}"` | `message.error` 显示后端返回的 message |
| 前端校验：全部字段为空 | -- | -- | `message.warning("请至少填写一个字段")`，阻止提交 |
| 前端校验：Platform + FY Period 重复 | -- | -- | `message.warning("该平台和年度组合已存在")`，阻止提交 |
| 保存成功 | -- | -- | `message.success("Save successful")`，清空 pendingChanges，重新加载数据 |

**前端统一错误处理逻辑**：
- 后端返回 `success === false` 时，取 `message` 字段内容通过 `message.error()` 展示
- 网络异常（HTTP 非 200 或超时）时，展示通用错误提示

---

## 8. 开发注意事项

1. **后端新建业务域 `benchmark/`**：在 `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/` 下新建 `benchmark/` 目录，包含标准分层：`controller/`、`service/`、`repository/`、`domain/`、`contract/`、`mapper/`、`enums/`。

2. **枚举可扩展性**：Platform 枚举虽当前固定 3 个值，但数据结构设计为可扩展。后端使用 Java enum 管理，前端 Platform 下拉选项从 `GET /api/web/benchmark/list` 响应的 `platformOptions` 字段获取，而非前端硬编码。

3. **事务一致性**：批量保存接口（`POST /api/web/benchmark/save`）中的新增、更新、删除操作必须在同一事务中完成，任一操作失败则全部回滚。使用 `@Transactional` 注解。

4. **自定义表格性能**：由于 Metric 数量固定为 6 个，详情行数量通常有限（每个 Metric 下预计 3-10 行），无需虚拟滚动优化。但 Category 的 `rowSpan` 计算应缓存（useMemo），避免每次 render 重复计算。

5. **审计字段**：Entity 继承 `AbstractCustomEntity`，自动填充 `created_at`、`created_by`、`updated_at`、`updated_by`。

6. **ID 生成策略**：使用 Java `UUID.randomUUID().toString()` 生成详情行 ID。前端新增行使用临时 ID（前缀 `temp_`），后端保存时替换为正式 UUID。

7. **接口路径命名**：后端 Controller 使用 `@RequestMapping("/benchmark")`，网关统一添加 `/api/web/` 前缀。前端服务文件中使用完整路径 `/api/web/benchmark/...`。

8. **前端 API 服务文件**：在 `src/services/api/benchmark/benchmarkService.ts` 中定义 API 请求函数，使用 `request` 工具函数（来自 `@/utils/request`）。TypeScript 接口类型统一定义在 `src/services/api/benchmark/types.ts` 中。

9. **字体依赖**：表格使用 Futura PT 字体。需确认项目中是否已引入该字体，若未引入需在全局样式中添加。数值列使用等宽字体（如 `monospace` 或项目中已有的等宽字体）。

10. **横向滚动**：表格外层容器设置 `overflow-x: auto`，表格设置 `min-width: 1100px`，确保在窄屏幕上可横向滚动查看所有列。

11. **乐观锁异常注册**：需在 `GlobalExceptionHandler` 中新增 `OptimisticLockException` 的处理方法，与 `BadRequestException` 类似返回 HTTP 200 + `Result.fail(msg)`。或者直接让 `OptimisticLockException` 继承 `BadRequestException`，复用现有处理链。

12. **单表设计中的 formula 行**：每个 `metric_key` 在 `benchmark_detail` 表中有一条 `is_formula_row = TRUE` 的行，用于存储 formula 和对应的 version。此行通过初始化 SQL 脚本预插入，应用层不允许删除。详情行的 `is_formula_row` 字段始终为 `FALSE`。查询时通过 `WHERE is_formula_row = FALSE` 过滤出纯详情行。
