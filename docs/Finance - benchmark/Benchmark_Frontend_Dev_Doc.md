# Benchmark 基准对标 — 前端开发文档

> 版本 v8.0 (2026-03-27) | 项目：Looking Glass CIOaas-web

---

## 一、项目技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | ^16.8.6 | UI 渲染 |
| Umi | 3.2.27 | 应用框架、路由、构建 |
| Ant Design | 4.9.2 | UI 组件库（Tabs、Spin、Tooltip、DatePicker 等） |
| DVA | 2.4.1 | 全局状态管理（Redux 封装） |
| umi-request | ^1.0.8 | HTTP 请求客户端 |
| ECharts | ^5.6.0 | 雷达图、折线图渲染 |
| echarts-for-react | ^3.0.5 | ECharts React 封装 |
| Moment.js | ^2.25.3 | 日期处理 |
| TypeScript | — | 类型系统 |
| LESS | — | 样式方案（CSS Modules 作用域） |
| classnames | ^2.2.6 | CSS 类名拼接 |
| ahooks | ^2.9.6 | React hooks 工具库 |

### 项目约定

| 约定项 | 规范 |
|--------|------|
| 路径别名 | `@/*` → `src/*`、`@@/*` → `src/.umi/*` |
| 文件命名 | 页面入口 `Index.tsx`，组件 PascalCase，hooks `useXxx.ts`，类型 `types.ts`，工具 `utils.ts` |
| 模块组织 | `src/pages/<module>/<feature>/` 下按 `components/`、`hooks/` 子目录组织 |
| HTTP 请求 | 统一使用 `@/utils/request.ts`（umi-request extend），Bearer Token 认证 |
| API 路径 | `/api/web/benchmark/company/{companyId}/...` |
| 状态管理 | 页面级用 `useReducer` + 自定义 Hook，全局用 DVA model |
| 样式 | LESS + CSS Modules（`import styles from './index.less'`），结合全局 CSS 变量和工具类 |
| 字体 | 自定义字体 Futura-PT-Demi（粗体）、Futura-PT-Medium（常规），通过 Adobe Typekit 加载 |

---

## 二、前端开发工作职责

### 页面开发

| 任务 | 文件 | 说明 |
|------|------|------|
| Benchmark 主页面 | `src/pages/companyFinance/benchmark/Index.tsx` | 页面容器：筛选面板 + 数据区 + 加载/错误状态 |
| 样式文件 | `src/pages/companyFinance/benchmark/index.less` | 页面级 LESS 样式 |
| Finance 父页面集成 | `src/pages/companyFinance/index.tsx` | 添加 Benchmarking Tab |

### 组件开发（7 个）

| 组件 | 文件 | 职责 |
|------|------|------|
| FilterBar | `components/FilterBar.tsx` | VIEW/FILTER/DATA/BENCHMARK 筛选 + 日期选择 + 警告 |
| OverallScoreBar | `components/OverallScoreBar.tsx` | Overall Score 大卡片 + 四大类别卡片 + 雷达图容器 |
| BaseBar | `components/MetricPercentileBar.tsx` | 基础百分位进度条（track + fill + dots） |
| ScoreBar | `components/MetricPercentileBar.tsx` | 百分位数值 + 进度条 + 刻度（Overall/Category 尺寸） |
| IndicatorBar | `components/MetricPercentileBar.tsx` | 单条指标进度条：dot + label + bar |
| RadarChart | `components/RadarChart.tsx` | ECharts 雷达图（6 指标 × 最多 12 条线） |
| TrendLineChart | `components/TrendLineChart.tsx` | ECharts 折线图（6 个月趋势） |

### 数据层

| 任务 | 文件 | 说明 |
|------|------|------|
| 类型定义 | `types.ts` | 全部 TypeScript 接口、枚举、联合类型 |
| 工具函数 | `utils.ts` | 颜色映射、日期工具、组合样式、常量文案 |
| Mock 数据 | `mockData.ts` | 完整 Mock 数据生成器（正常态 + 边界态） |
| 数据 Hook | `hooks/useBenchmarkData.ts` | useReducer 状态管理 + API 请求 + 缓存 |

### 数据服务

| 任务 | 文件 | 说明 |
|------|------|------|
| Benchmark API | `src/services/api/companyFinance/benchmarkService.ts` | snapshot/trend/periods 三个接口 + Mock 开关 |

### 与后端对接

| 任务 | 说明 |
|------|------|
| Snapshot API | `GET /api/web/benchmark/company/{companyId}/snapshot?dataSources=...&benchmarkSources=...&date=YYYY-MM` |
| Trend API | `GET /api/web/benchmark/company/{companyId}/trend?dataSources=...&benchmarkSources=...&dateRange=YYYY-MM_YYYY-MM` |
| 可用期间 API | `GET /api/web/benchmark/company/{companyId}/available-periods` |

---

## 三、Figma 设计稿

| 视图 | Figma 链接 |
|------|-----------|
| Snapshot: Actuals + Internal Peers | [node 539-65160](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=539-65160&m=dev) |
| Snapshot: 部分卡片收起 | [node 2699-259107](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2699-259107&m=dev) |
| Snapshot: Committed Forecast + KeyBanc | [node 2699-259702](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2699-259702&m=dev) |
| Snapshot: System Generated + KeyBanc | [node 2699-260299](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2699-260299&m=dev) |
| Snapshot: Actuals & Committed + Internal & KeyBanc | [node 2699-261632](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2699-261632&m=dev) |
| Snapshot: 全组合（3×4=12） | [node 2697-258409](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2697-258409&m=dev) |
| Trend: Actuals + Internal Peers | [node 2717-258813](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2717-258813&m=dev) |
| Trend: 部分卡片收起 | [node 2717-260783](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2717-260783&m=dev) |
| Trend: Committed Forecast + KeyBanc | [node 2717-263141](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2717-263141&m=dev) |
| Trend: System Generated + KeyBanc | [node 2717-264534](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2717-264534&m=dev) |
| Trend: Actuals & Committed + Internal & KeyBanc | [node 2717-265203](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2717-265203&m=dev) |
| Trend: 全组合（3×4=12） | [node 2445-257761](https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=2445-257761&m=dev) |

---

## 四、目录结构

```
src/pages/companyFinance/benchmark/
├── Index.tsx                          # 主页面：筛选面板 + 数据展示 + 加载/错误状态
├── index.less                         # 页面样式
├── types.ts                           # TypeScript 类型定义（20+ 接口/类型）
├── utils.ts                           # 工具函数、常量、颜色映射
├── mockData.ts                        # Mock 数据生成器
├── components/
│   ├── FilterBar.tsx                  # 筛选条件面板（VIEW/FILTER/DATA/BENCHMARK/DATE）
│   ├── OverallScoreBar.tsx            # Overall Score + Category Cards + 雷达图
│   ├── MetricPercentileBar.tsx        # BaseBar / ScoreBar / IndicatorBar 三合一
│   ├── RadarChart.tsx                 # ECharts 雷达图
│   └── TrendLineChart.tsx            # ECharts 折线图
└── hooks/
    └── useBenchmarkData.ts            # useReducer 状态 + API 请求 + 缓存

src/services/api/companyFinance/
└── benchmarkService.ts                # API 服务层 + Mock 开关
```

### 页面完整的组件层级结构

```
<Index>                                            ← 主页面容器：disclaimer + 加载/错误状态 + 组装子组件
├── <Disclaimer />                                 ← 顶部说明文字（内联）
├── <FilterBar />                                  ← 筛选面板：VIEW/FILTER/DATA/BENCHMARK/Date + 警告横幅
├── <Spin spinning={loading}>                      ← Ant Design 加载包裹
│   └── <OverallScoreBar>                          ← 数据展示区域容器
│       ├── Overall Score 区域                      ← Overall 百分位 + 信息标注
│       │   └── <ScoreBar size="large" />          ← 百分位数值 + 大进度条 + 刻度
│       ├── CategoryCard × 4                        ← 四大类别卡片（内联渲染，非独立组件）
│       │   ├── 标题行（展开/收起 + 类别名 + 评分）  ← 点击切换 expandedCategories
│       │   ├── <ScoreBar size="medium" />         ← 类别百分位 + 中进度条
│       │   └── MetricRow × N                       ← 该类别包含的指标行（内联）
│       │       ├── Snapshot: <IndicatorBar /> × N  ← 每个 DATA-BENCHMARK 组合一条进度条
│       │       └── Trend:   <TrendLineChart />    ← ECharts 折线图（多月范围）
│       │       ↑ VIEW 仅影响此处展示组件，其他部分完全一致 ↑
│       └── <RadarChart />                         ← Metrics Summary 雷达图（两种视图均显示，逻辑相同）
└── hooks/
    └── useBenchmarkData()                         ← useReducer 状态 + API 请求 + 缓存
```

**拆分原则**：
- **独立文件的组件**：FilterBar（自治交互逻辑）、OverallScoreBar（复杂渲染逻辑）、RadarChart（ECharts 封装）、TrendLineChart（ECharts 封装）、MetricPercentileBar（三个复用组件）
- **内联渲染的区块**：CategoryCard（在 OverallScoreBar 中用 JSX 片段渲染）、MetricRow（在 CategoryCard 内迭代渲染）、Disclaimer（简单文字段落）
- **基础复用组件**：BaseBar / ScoreBar / IndicatorBar 在同一文件中通过命名导出，被 OverallScoreBar 多处引用

---

## 五、页面整体结构

### 核心概念：Snapshot 与 Trend 只是展示形式不同

**VIEW 切换（Snapshot / Trend）仅控制指标明细区域的展示方式，不影响任何筛选逻辑和数据计算。**

| 维度 | Snapshot | Trend | 说明 |
|------|----------|-------|------|
| **展示形式** | 进度条（IndicatorBar） | 折线图（TrendLineChart） | 唯一的差异 |
| **查询维度** | 单月查询 | 多月查询（日期范围） | 日期选择器形式不同 |
| **日期选择器** | 单个 MonthPicker | 两个 MonthPicker（起止月） | Trend 需选择日期范围 |
| **FILTER 逻辑** | 相同 | 相同 | 控制显示哪些类别卡片 |
| **DATA 逻辑** | 相同 | 相同 | 控制数据来源组合 |
| **BENCHMARK 逻辑** | 相同 | 相同 | 控制基准来源组合 |
| **Overall Score 卡片** | 相同 | 相同 | 始终显示，逻辑一致 |
| **Category Cards 结构** | 相同 | 相同 | 标题、得分、展开/收起一致 |
| **Category 进度条** | 相同 | 相同 | 始终显示分类得分进度条 |
| **Radar Chart** | 相同 | 相同 | 始终显示，数据来源一致 |

**一句话总结**：把 Snapshot 理解为"单月快照 + 进度条"，Trend 理解为"多月趋势 + 折线图"。除了指标明细区域的展示控件不同，页面其他所有部分完全一致。

### 页面结构（Snapshot 与 Trend 共用）

```
┌─────────────────────────────────────────────────────────────────────┐
│  Finance > Benchmarking Tab                                          │
│  "Benchmark values are normalized for comparability..."              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌ VIEW ─────┬ FILTER ──────────────┬ DATE ────────────────────────┐│
│  │ [Snapshot] │ [All] GR EFF MA CA   │ Snapshot: [▼ 2025-11]       ││
│  │  Trend     │                      │ Trend:    [▼ 起] ~ [▼ 止]  ││
│  ├ DATA ──────┴ BENCHMARK ───────────┴──────────────────────────────┤│
│  │ [Actuals] Committed SysGen │ [Internal] KeyBanc HighAlpha Bench ││
│  └──────────────────────────────────────────────────────────────────┘│
├ [⚠ Peer Fallback Warning]（条件显示）──────────────────────────────┤
│                                                                      │
│  ┌ Overall Benchmark Score ──────────────────── [ⓘ Includes...] ──┐│
│  │ ~67P                 （← 两种视图完全相同）                     ││
│  │ ████████████████████████░░░░░░░░░░░░░░  ● ○ ◆                  ││
│  │ P0      P25      P50      P75      P100                         ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌ ▼ Revenue & Growth ─────── ~51% ──────────────────────────────┐ │
│  │ ███████████████░░░░░░░░░░░░░░░░  ● ○ ◆  （← 分类进度条相同） │ │
│  │                                                                 │ │
│  │   ARR Growth Rate  ⓘ                                           │ │
│  │   ┌─────────────────────────────────────────────────────────┐   │ │
│  │   │  Snapshot: IndicatorBar × N（每个 DATA-BENCHMARK 一条） │   │ │
│  │   │     ● Actuals-Internal ████████░░░░░ P54               │   │ │
│  │   │     ○ Actuals-KeyBanc  ██████░░░░░░░ P42               │   │ │
│  │   │                                                         │   │ │
│  │   │  Trend:    TrendLineChart（折线图，X=月份，Y=百分位）   │   │ │
│  │   │     📈 多条折线 + 图例                                  │   │ │
│  │   └────────────── ↑ 唯一差异区域 ↑ ─────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│  ┌ ▶ Profitability & Efficiency ── ~25% ─────────────────────────┐ │
│  └─────────────────────────────────────────────────────────────────┘ │
│  ┌ ▼ Burn & Runway ───────── ~89% ──────────────────────────────┐  │
│  │ ...（Monthly Net Burn Rate + Monthly Runway）                  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌ ▼ Capital Efficiency ──── ~10% ──────────────────────────────┐  │
│  │ ...（Rule of 40 + Sales Efficiency Ratio）                     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌ Metrics Summary ──────────────────────────────────────────────┐  │
│  │  （← 两种视图完全相同，始终显示雷达图）                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 六、组件规格

### 6.1 FilterBar — 筛选条件面板

**容器样式**：无独立背景，铺满页面宽度，内部分两行

#### 第一行：VIEW + FILTER + DATE

| 元素 | 属性 | 值 |
|------|------|----|
| 行布局 | display, justify-content, align-items, gap | flex, space-between, center, 24px |
| VIEW 标签 | font | Futura PT, 500, 16px, line-height 24px |
| VIEW 标签颜色 | color | `#15191C` (Grey/900) |

#### Pill 按钮样式

| 状态 | 背景 | 边框 | 文字色 | 圆角 | 字体 |
|------|------|------|--------|------|------|
| VIEW/FILTER 选中 | `#19418D` (Blue/800) | none | `#FFFFFF` | 8px | Futura PT, 500, 12px |
| VIEW/FILTER 未选中 | transparent | 1px solid `#E5F1FA` (Blue/50) | `#19418D` (Blue/800) | 8px | Futura PT, 500, 12px |
| DATA/BENCHMARK 选中 | `#F6BD7D` (Golden/200) | none | `#15191C` (Grey/900) | 16px | Futura PT, 500, 12px |
| DATA/BENCHMARK 未选中 | transparent | 1px solid `#D6D8DC` (Grey/400) | `#4E5153` (Grey/800) | 16px | Futura PT, 500, 12px |
| 禁用 | transparent | 1px solid `#ECEEF1` (Grey/300) | `#AEB0B3` (Grey/500) | — | — |

- Pill 固定高度：32px
- Pill padding：`8px 20px`
- Pill 间距（gap）：12px

#### 第二行：DATA + BENCHMARK

| 元素 | 属性 | 值 |
|------|------|----|
| 行布局 | gap | 32px |
| DATA 组 | 标签 + pill group | gap 12px |
| BENCHMARK 组 | 标签 + pill group | gap 12px |

#### 日期选择器（Period Selector）

| 属性 | 值 |
|------|----|
| 背景 | `#FFFFFF` |
| 边框 | 1px solid `#D6D8DC` (Grey/400) |
| 圆角 | 4px |
| padding | `8px 16px` |
| 高度 | 40px |
| 文字色 | `#0D2B56` (Blue/900) |
| 文字与下拉图标间距 | 8px |

#### 警告横幅（Peer Fallback Warning）

| 属性 | 值 |
|------|----|
| 背景 | `#FDEFDF` (Golden/50) |
| 圆角 | 4px |
| padding | `8px 16px` |
| 图标+文字间距 | 8px |
| 文字色 | `#986503` |
| 字体 | Futura PT, 500, 12px |
| 文案 | "Peer Fallback: No direct peer group found for this company. Benchmarking against all active companies in Looking Glass." |

#### 交互逻辑

- **VIEW**：单选（Snapshot / Trend），**仅切换指标明细区域的展示形式（进度条 ↔ 折线图）和日期选择器形式（单月 ↔ 范围），不影响 FILTER/DATA/BENCHMARK 的选中状态和逻辑**
- **FILTER**：All 与其他互斥；选 Growth/Efficiency/Margins/Capital 任一则 All 取消；最少选一个。**Snapshot 和 Trend 下逻辑完全相同**
- **DATA**：多选，最少选一个；无数据的选项灰化禁用。**Snapshot 和 Trend 下逻辑完全相同**
- **BENCHMARK**：多选，最少选一个；无数据的选项灰化禁用。**Snapshot 和 Trend 下逻辑完全相同**
- **DATE**：Snapshot 模式为单个 MonthPicker（单月选择）；Trend 模式为两个并排 MonthPicker（选择起止月份范围）
- **VIEW 切换时的状态保持**：切换 Snapshot ↔ Trend 时，FILTER/DATA/BENCHMARK 选中状态全部保留，仅日期选择器形式切换

---

### 6.2 Overall Benchmark Score 卡片

**容器样式**：

| 属性 | 值 |
|------|----|
| 背景 | `#FFFFFF` |
| 圆角 | 4px |
| padding | 24px |
| 阴影 | `0px 2px 4px 0px rgba(0, 0, 0, 0.1)` (Card Shadow) |
| 内部布局 | column, gap 24px |

#### 标题行

| 元素 | 字体 | 色值 |
|------|------|------|
| "Overall Benchmark Score" | Futura PT, 500, 28px, line-height 32px | `#0D2B56` (Blue/900) |
| 右侧信息文字 | Futura PT, 450, 14px, line-height 20px | `#6D7174` (Grey/700) |
| 右侧信息文字内容 | "6 metrics - Above median" / "Includes estimated percentiles..." | — |

#### 百分位数值（大）

显示格式为 `~67%ile`，其中数字部分大字体，`%ile` 后缀为小字体垂直居中显示。

| 属性 | 值 |
|------|----|
| 数值字体 | Futura PT, 500, 72px |
| 数值色 | `#0D2B56` (Blue/900) |
| "%ile" 后缀 | font-size 约 25px (72 × 0.35), **颜色与数字相同** `#0D2B56`，margin-left 2px |
| 居中方式 | 数字与 `%ile` 包裹在 `display: inline-flex; align-items: center` 容器中，确保后缀相对数字垂直居中 |
| 显示格式 | `{prefix}{number}` + `<span>%ile</span>`，如 `~67` + `%ile` |
| 容器宽度 | 200px |
| padding | `24px 0px` |

**5 个总指标均使用此格式**：Overall Benchmark Score（72px）、Revenue & Growth / Profitability & Efficiency / Burn & Runway / Capital Efficiency（48px，后缀约 17px）。

#### 进度条（Large 尺寸）

| 属性 | 值 |
|------|----|
| 轨道背景 | `#ECEEF1` (Grey/300) |
| 轨道高度 | 20px |
| 轨道圆角 | 12px |
| 填充条圆角 | `12px 0px 0px 12px` |
| 填充条颜色 | 按百分位动态取色（见颜色规则） |
| 数值与进度条间距 | 48px |
| 进度条内 padding | `0px 32px` |

#### 圆点标记（Dot）

| 属性 | 值 |
|------|----|
| 尺寸 | 20px × 20px（Large）/ 12px（Medium）/ 8px（Small） |
| 填充 | `#FFFFFF` |
| 边框 | 2px solid {组合颜色} |
| 阴影 | `1px 2px 4px 0px rgba(0, 0, 0, 0.3)` |
| 位置 | 水平按百分位值定位，垂直居中 |

#### 刻度标签（P0/P25/P50/P75/P100）

| 属性 | 值 |
|------|----|
| 字体 | Futura PT, 500, 10px, line-height 14px |
| 颜色 | `#6D7174` (Grey/700) |
| 分布 | flex space-between |

#### Quartile 标签

| 属性 | 值 |
|------|----|
| 格式 | "{COUNT}-{Quartile Name}" |
| 映射 | P≥75: Top Quartile, P≥50: Upper Middle, P≥25: Lower Middle, P<25: Bottom |

#### 右上角信息图标

| 属性 | 值 |
|------|----|
| 图标 | 灰色圆形 (i) |
| 图标尺寸 | 24px × 24px |
| 图标背景 | `#ECEEF1` (Grey/300) |
| 图标文字 | `#4E5153` (Grey/800) |
| Tooltip 内容 | "Includes estimated percentiles (interpolated/boundary values used)" |

#### Tooltip 样式

| 属性 | 值 |
|------|----|
| 背景 | `#FFFFFF` |
| 边框 | 1px solid `#ECEEF1` (Grey/300) |
| 圆角 | 4px |
| padding | `12px 16px` |
| 阴影 | `0px 2px 4px 0px rgba(0, 0, 0, 0.1)` |
| 文字 | Futura PT, 500, 12px, `#4E5153` |
| 内容格式 | 第 1 行：{DataSource} - {BenchmarkSource}；第 2 行：Percentile: P{val} |
| 适用范围 | Overall Score 卡片和四大 Category 卡片的进度条圆点均显示此 Tooltip（即使只有 1 个组合也显示） |

---

### 6.3 Category Card — 类别评分卡片

**容器样式**：与 Overall Score 相同（白底、4px 圆角、24px padding、Card Shadow）

#### 标题行

| 元素 | 属性 | 值 |
|------|------|----|
| 展开图标 | 尺寸 | 24px × 24px |
| 类别名 | 字体 | Futura PT, 500, 28px, line-height 32px, `#0D2B56` |
| 百分位值 | 字体 | Futura PT, 500, 48px, line-height 40px, `#0D2B56`；`%ile` 后缀 ~17px, 同色 `#0D2B56`, inline-flex align-items center 居中 |
| 布局 | | row, space-between, align center |

#### 进度条（Medium 尺寸）

| 属性 | 值 |
|------|----|
| 轨道高度 | 12px |
| 轨道圆角 | 12px |
| 数值与进度条间距 | 24px |
| 进度条内 padding | `0px 16px` |

#### 展开/收起

- 默认：**Snapshot 视图四个类别全部展开，Trend 视图四个类别全部收起**
- 动画：300ms ease-in-out
- 点击标题行或 ▼/▶ 图标切换

#### 四大类别

| 类别 | CategoryKey | 包含指标 |
|------|------------|---------|
| Revenue & Growth | `revenueAndGrowth` | ARR Growth Rate |
| Profitability & Efficiency | `profitabilityAndEfficiency` | Gross Margin |
| Burn & Runway | `burnAndRunway` | Monthly Net Burn Rate, Monthly Runway |
| Capital Efficiency | `capitalEfficiency` | Rule of 40, Sales Efficiency Ratio |

---

### 6.4 MetricRow — 指标明细行（内联）

#### 指标标题

| 属性 | 值 |
|------|----|
| 字体 | Futura PT, 500, 24px, line-height 32px |
| 颜色 | `#0D2B56` (Blue/900) |
| 信息图标 | 24px, bg `#ECEEF1`, color `#4E5153` |
| 行布局 | row, align center, gap 16px |

#### Snapshot 模式 — IndicatorBar 列表（进度条展示）

VIEW=Snapshot 时，每个 DATA-BENCHMARK 组合渲染一条进度条：

| 元素 | 属性 | 值 |
|------|------|----|
| 组合标签 | 字体 | Futura PT, 450, 14px, `#4E5153` |
| 百分位值 | 字体 | Futura PT, 500, 14px, `#4E5153` |
| 小进度条 | 高度 8px, 圆角 8px |
| 小圆点 | 8px × 8px, fill `#FFFFFF`, stroke 2px {组合颜色} |
| 行间距 | 指标内行间距 6px，指标间距 12px |
| 进度条 padding | `0px 16px` |

**排序规则**：所有 IndicatorBar 按百分位值从高到低排序

#### Trend 模式 — TrendLineChart（折线图展示）

VIEW=Trend 时，替代 IndicatorBar，渲染 ECharts 折线图。**注意：指标标题、信息图标、类别卡片结构、分类进度条等均与 Snapshot 完全一致，仅替换指标明细区域的展示控件。**

| 属性 | 值 |
|------|----|
| X 轴 | 用户选择的日期范围内的月份（YYYY-MM） |
| Y 轴 | 0-100 百分位 |
| 折线样式 | 每个 DATA-BENCHMARK 组合使用对应颜色和线型（Actuals/Committed=实线，System Generated=虚线） |
| 数据点 | 圆点标记 |
| 图例 | 自定义 HTML 图例，flex-wrap 居中排列，根据选中组合数量动态显示 |
| Tooltip | 该月份所有组合百分位值列表 |

---

### 6.5 RadarChart — 雷达图（Snapshot 与 Trend 完全相同）

**雷达图在两种视图下保持完全一致的逻辑和展示，始终基于当前选中的 DATA × BENCHMARK 组合数据渲染。**

| 属性 | 值 |
|------|----|
| 容器 | 白底，固定高度 320px，fill width |
| 标题 | "Metrics Summary", Heading/H1, `#0D2B56` |
| 形状 | **六边形**（`shape: 'polygon'`），固定 6 个顶点对应 6 个核心指标 |
| 中心 | P0 (0%) |
| 分割环 | P25, P50, P75, P100（六边形同心环，splitNumber: 4） |
| 6 个顶点 | ARR Growth Rate, Gross Margin, Monthly Net Burn Rate, Monthly Runway, Rule of 40, Sales Efficiency Ratio |
| 折线 | 最多 12 条，颜色和线型对应组合映射 |
| 填充 | 半透明色填充围成区域 |
| 指标标签 | Futura PT, 500, 14px, `#4E5153` |
| 底部注释 | "雷达图数据为选定日期往前 6 个月的平均百分位值，与上方当月数据可能不一致" |

#### 雷达图 Tooltip（按顶点触发）

hover 到某个顶点时，显示**该指标**在所有组合线中的百分位值，而非某条线的全部指标。

| 属性 | 值 |
|------|----|
| 触发方式 | hover 到顶点 symbol，通过鼠标角度计算最近的指标轴 |
| 标题行 | 指标名（如 "Sales Efficiency Ratio"），font-weight 600, 13px |
| 内容行 | 每个组合一行：`{彩色圆点} {组合名}: P{值}`，按 12 组合映射颜色 |
| 背景 | `rgba(37, 37, 37, 0.6)` (半透明深色) |
| 边框 | 1px solid `#ECEEF1` |
| 圆角 | 4px |
| padding | `8px 12px` |
| 文字 | Futura PT, 450, 12px, `#FFFFFF` |

**示例**（hover 到 Sales Efficiency Ratio 顶点，选中了 2 个组合）：
```
Sales Efficiency Ratio
● Actuals - Internal Peers: P18
● Committed Forecast - KeyBanc: P22
```

---

### 6.6 TrendLineChart — 折线图（仅 Trend 视图的指标明细区域使用）

**此组件仅替换 Snapshot 视图中 IndicatorBar 的位置，其他所有页面结构不变。**

| 属性 | 值 |
|------|----|
| X 轴 | 用户选择的日期范围内的月份标签，font 12px |
| Y 轴 | 0-100 百分位刻度（P0/P30/P60/P90/P100） |
| 折线 | 2px 宽度，颜色对应组合映射，**Actuals/Committed=实线，System Generated=虚线** |
| 数据点 | 圆点 5px，fill 对应颜色 |
| 图例 | 自定义 HTML flex-wrap 居中排列，非 ECharts 内置图例 |
| Tooltip | 半透明深色背景 `rgba(37,37,37,0.6)`，显示该月份所有组合百分位值 |
| 图表高度 | 固定 304px（不含图例） |

---

## 七、多源样式配置

### 12 种 DATA-BENCHMARK 组合的完整样式速查表

| # | 数据源 | 基准源 | 圆点边框色 | Hex | 线型 |
|---|--------|--------|-----------|-----|------|
| 1 | Actuals | Internal Peers | Accent Yellow/700 | `#E3C200` | solid |
| 2 | Committed Forecast | Internal Peers | Purple/800 | `#833ACE` | solid |
| 3 | System Generated | Internal Peers | Purple/800 | `#833ACE` | dashed (5,5) |
| 4 | Actuals | KeyBanc | Accent Orange/600 | `#D85E18` | solid |
| 5 | Committed Forecast | KeyBanc | Accent Orange/800 | `#753815` | solid |
| 6 | System Generated | KeyBanc | Accent Orange/800 | `#753815` | dashed (5,5) |
| 7 | Actuals | High Alpha | Blue/400 | `#5B9CE3` | solid |
| 8 | Committed Forecast | High Alpha | Blue/800 | `#19418D` | solid |
| 9 | System Generated | High Alpha | Blue/800 | `#19418D` | dashed (4,4) |
| 10 | Actuals | Benchmarkit.ai | Green/300 | `#87CA90` | solid |
| 11 | Committed Forecast | Benchmarkit.ai | Green/700 | `#009344` | solid |
| 12 | System Generated | Benchmarkit.ai | Green/700 | `#009344` | dashed (4,4) |

**样式规律**：Actuals 使用每个基准源独有的颜色；Committed Forecast 使用同基准源的第二色；System Generated Forecast 使用与 Committed 相同的颜色但虚线边框以区分。

所有圆点共用：fill `#FFFFFF`，strokeWeight 2px，shadow `1px 2px 4px 0px rgba(0, 0, 0, 0.3)`。

### 进度条填充颜色规则

| 百分位范围 | 颜色 | Hex |
|-----------|------|-----|
| P ≥ 75 | Green/700 | `#007235` |
| 50 ≤ P < 75 | Golden/300 | `#F6CD7D` |
| 25 ≤ P < 50 | Red/200 | `#F29E9D` |
| P < 25 | Red/400 | `#DA5858` |
| 无数据 | Grey/300 | `#ECEEF1` |

---

## 七-B、接口对接（BenchmarkV2 API）

> 基于 `03-technical-design.md` TDD v1.0 对接。Mock 开关 `USE_MOCK = true`，后端就绪后改为 `false`。

### API 基础路径

```
/api/web/benchmark
```

### 接口总览（2 个接口）

| # | 接口 | 方法 | 路径 | 调用时机 |
|---|------|------|------|---------|
| API-01 | 统一数据接口 | GET | `/benchmark/company/{companyId}/data` | Snapshot/Trend 共用，通过 `type` 参数区分 |
| API-02 | 筛选条件选项 | GET | `/benchmark/company/{companyId}/filter-options` | 页面首次加载 |

### API-01 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | query | 是 | `SNAPSHOT` 或 `TREND` |
| date | query | 否 | SNAPSHOT 专用，格式 `yyyy-MM` |
| startDate | query | 否 | TREND 专用，起始月 |
| endDate | query | 否 | TREND 专用，结束月 |
| dataSources | query | 否 | 逗号分隔：`ACTUALS,COMMITTED_FORECAST,SYSTEM_GENERATED_FORECAST` |
| benchmarkSources | query | 否 | 逗号分隔：`INTERNAL_PEERS,KEYBANC,HIGH_ALPHA,BENCHMARK_IT` |

**核心特点**：Snapshot 和 Trend 共用同一响应结构。SNAPSHOT 时 `monthlyData[]` 含 1 个月，TREND 时含 N 个月。

### 枚举映射（API ↔ 前端）

| 类型 | API 值 | 前端值 |
|------|--------|--------|
| DataSource | `ACTUALS` | `Actuals` |
| DataSource | `COMMITTED_FORECAST` | `CommittedForecast` |
| DataSource | `SYSTEM_GENERATED_FORECAST` | `SystemGeneratedForecast` |
| BenchmarkSource | `INTERNAL_PEERS` | `InternalPeers` |
| BenchmarkSource | `KEYBANC` | `KeyBanc` |
| BenchmarkSource | `HIGH_ALPHA` | `HighAlpha` |
| BenchmarkSource | `BENCHMARK_IT` | `BenchmarkIt` |

### 数据适配层

API 返回结构为 `categories[].metrics[].dimensions[]`（按指标分组，维度嵌套），前端 UI 消费的结构为 `combinations[].categoryScores[].metrics[]`（按组合分组）。

适配器在 `benchmarkService.ts` 中实现（`adaptSnapshotResponse` / `adaptTrendResponse`），组件层无需感知 API 结构差异。

### 页面调用流程

```
页面加载
  ├── 1. filter-options → 初始化 FilterBar 选项 + 默认日期 + enabled/disabled 状态
  ├── 2. snapshot（默认参数）→ Overall Score + 4 板块 + 雷达图
  └── 用户交互
        ├── 切换 DATA/BENCHMARK/日期 → 重新调用 snapshot 或 trend
        ├── 切换 VIEW → Snapshot 调 snapshot，Trend 调 trend
        └── 切换 FILTER → 纯前端过滤，不调接口
```

### Service 层封装

```typescript
// services/api/companyFinance/benchmarkService.ts
import request from '@/utils/request';

const BASE_URL = '/api/web/benchmarkV2';
const USE_MOCK = true; // 后端就绪后改为 false

// 接口 1
export async function getBenchmarkFilterOptions(companyId: string): Promise<FilterOptionsData>

// 接口 2（内部包含适配器，返回 UI 模型）
export async function getBenchmarkSnapshot(companyId, dataSources, benchmarkSources, date?): Promise<BenchmarkResponseData>

// 接口 3（内部包含适配器，返回 UI 模型）
export async function getBenchmarkTrend(companyId, dataSources, benchmarkSources, dateRange?): Promise<TrendResponseData>
```

---

## 八、筛选器与数据联动

### 核心原则

**FILTER、DATA、BENCHMARK 是纯筛选条件，与 VIEW（Snapshot/Trend）无关。** VIEW 只决定指标明细区域用进度条还是折线图来展示，不改变筛选逻辑、数据计算、组件结构。

### 筛选器联动关系

| 筛选器 | 类型 | 影响范围 | 联动规则 | Snapshot/Trend 差异 |
|--------|------|---------|---------|-------------------|
| VIEW | 单选 | 指标明细展示形式 + 日期选择器形式 | Snapshot→IndicatorBar；Trend→TrendLineChart | **仅此一项有差异** |
| FILTER | 多选(互斥All) | 类别卡片可见性 | All=全显示；选单项=仅显示对应类别 | 无差异 |
| DATA | 多选 | 组合条数（进度条/折线/雷达线/Overall 点位） | 增减数据源→增减对应组合 | 无差异 |
| BENCHMARK | 多选 | 组合条数（进度条/折线/雷达线/Overall 点位） | 增减基准源→增减对应组合 | 无差异 |
| DATE | 单选/范围 | 数据重新计算 | Snapshot=单月 MonthPicker；Trend=两个 MonthPicker（起止月范围） | 选择器形式不同，但都触发数据请求 |

### 数据过滤规则（Snapshot 和 Trend 通用）

- DATA × BENCHMARK 笛卡尔积 = 显示的组合条数（最多 3×4=12）
- 取消某 DATA/BENCHMARK 选项后，相关组合的进度条/折线/雷达线/Overall 点位立即隐藏
- 所有百分位和 Overall Score 基于当前可见组合重新计算
- **以上规则在 Snapshot 和 Trend 下完全一致**

### 排序规则

- **指标内 IndicatorBar（Snapshot）**：按百分位值从高到低排序
- **类别卡片顺序**：固定（Revenue & Growth → Profitability & Efficiency → Burn & Runway → Capital Efficiency）

### VIEW 切换的状态保持

- 切换 VIEW 时 **保持** FILTER、DATA、BENCHMARK 选择状态，不重置
- DATE 在 Snapshot↔Trend 间独立管理（Snapshot 单月，Trend 起止月范围）
- 卡片展开/收起状态在 VIEW 切换时**重置**：切到 Snapshot 全展开，切到 Trend 全收起

---

## 九、日期选择逻辑

| 模式 | 日期组件 | 默认值 | 说明 |
|------|---------|--------|------|
| Snapshot | 单个 Ant Design MonthPicker | 最新有 Actual 数据的月份 | 单月查询，仅显示有数据的月份 |
| Trend | 两个并排 Ant Design MonthPicker（起止月） | 起：最新月往前 5 个月；止：最新有 Actual 数据的月份 | 多月范围查询，默认跨 6 个月 |

- 日期范围：过去 24 个月（可向前滚动）
- 选择后自动关闭选择器，触发数据刷新
- 若选择的月份无数据，显示 "No data available" 提示
- **Snapshot 和 Trend 的日期状态独立管理**：切换 VIEW 时各自保留上次选择的日期

---

## 十、特殊状态处理

### 同行回退（Peer Fallback）

| 条件 | 处理 |
|------|------|
| 同行数 < 4 | 自动回退到 LG 平台基准（所有活跃公司） |
| UI 表现 | FilterBar 下方显示黄色警告横幅 |
| 文案 | "Peer Fallback: No direct peer group found for this company. Benchmarking against all active companies in Looking Glass." |
| 可关闭 | 用户可单次关闭提示 |

### 指标无数据

| 条件 | 处理 |
|------|------|
| 某指标某企业无数据 | 灰色空条 `#ECEEF1`，无点位，显示 "—" |
| 该指标不参与百分位计算 | 类别评分仅用有效指标计算 |

### 类别全部无数据

| 条件 | 处理 |
|------|------|
| 该类别所有指标都无数据 | 显示 "N/A"，灰色背景 |
| 不参与整体评分计算 | Overall Score 排除该类别 |

### Total Tie（所有公司值完全相同）

| 条件 | 处理 |
|------|------|
| 所有同行该指标值相同 | 灰色空条，不显示百分位值 |
| 文案 | "Value shared across entire peer group" |
| 不参与类别和整体平均计算 | — |

### Partial Tie（部分公司值相同）

| 条件 | 处理 |
|------|------|
| 部分公司值相同 | 正常显示百分位，附加 "Tied value" 标签 |
| 参与计算 | 正常参与 |

### 插值/边界估算

| 条件 | 处理 |
|------|------|
| 使用了线性插值 | 百分位显示 `~P{val}`（波浪号前缀） |
| 超出范围 | 百分位显示 `>P75` 或 `<P25` |
| Overall Score 右上角 | 显示 "Includes estimated percentiles (interpolated/boundary values used)" |

### 预测数据不存在

| 条件 | 处理 |
|------|------|
| 企业无 Committed Forecast | DATA 中该选项灰化禁用 |
| 企业无 System Generated Forecast | DATA 中该选项灰化禁用 |

### Monthly Runway NA 特殊处理

| 情景 | Cash | Net Burn | 排名 |
|------|------|----------|------|
| Top Rank (A 类) | ≥ 0 | ≥ 0 | 最高（P75~P100） |
| Calculated (B 类) | XOR（仅一个为负） | — | 正常计算 |
| Bottom Rank (C 类) | < 0 | < 0 | 最低（P0~P25） |

### Sales Efficiency NA 排除

| 条件 | 处理 |
|------|------|
| S&M Expenses + S&M Payroll < 总成本 × 5% | 该公司从 Sales Efficiency 排名中排除 |
| 目标公司满足条件 | 显示 "Sales Efficiency: No Data Available" |

---

## 十一、响应式设计

| 布局区域 | 桌面端 (≥1280px) | 移动端 (<768px) |
|---------|-----------------|----------------|
| 页面宽度 | 1280px 居中，padding 0 24px | 100%，padding 0 16px |
| FilterBar | 两行横排 | 堆叠换行 |
| Overall Score 数值 | 72px | 48px |
| Category 数值 | 48px | 36px |
| 类别卡片 | 纵向排列 | 纵向排列 |
| 雷达图 | 固定高度 320px | 高度自适应 |
| Pill 间距 | 12px | 8px |

---

## 十二、性能要求

| 操作 | 目标 | 实现方式 |
|------|------|---------|
| 筛选切换（FILTER/DATA/BENCHMARK） | < 100ms | 本地状态更新，无网络请求 |
| 日期切换数据加载 | < 800ms | API 请求 + Loading Spin |
| VIEW 切换 | < 500ms | 仅切换指标明细区域的展示组件（IndicatorBar ↔ TrendLineChart），其他部分无需重渲染 |
| 展开/收起类别 | 300ms | CSS transition ease-in-out |
| 进度条动画 | 300ms | CSS width transition |
| 首次加载 | < 2s | 骨架屏 + 逐项淡入 |
| Tooltip 显示 | 200ms delay | Ant Design Tooltip mouseEnterDelay |
| 数据缓存 | 避免重复请求 | 按 key 缓存 snapshot/trend 数据 |

---

## 十三、模块开发完成校验

### 校验流程

```
开发完成
  ↓
逐模块对照 Figma 设计稿截图/节点
  ↓
UI 还原度校验 → 记录差异
  ↓
交互逻辑校验 → 记录异常
  ↓
输出校验报告（通过 / 待修复列表）
```

### UI 还原度校验清单

| 检查项 | 校验内容 | 方法 |
|--------|---------|------|
| 布局结构 | 元素排列顺序、间距、对齐方式是否与设计稿一致 | 截图叠加对比 |
| 色值 | 背景色、文字色、边框色、图标色是否与 Figma 标注一致 | 取色器对比 |
| 字体 | 字号、字重、行高、字体族是否正确（Futura PT） | DevTools 检查 |
| 间距 | margin、padding、gap 是否与设计稿标注值一致 | DevTools 测量 |
| 圆角与阴影 | borderRadius、boxShadow 是否匹配 | 视觉对比 |
| 进度条 | 颜色分段、高度、圆角、填充宽度是否正确 | 取色器 + 测量 |
| 圆点标记 | 尺寸、边框色、位置是否与设计稿一致 | 逐个核对 |
| 响应式 | 各断点下布局是否按设计稿适配 | 调整窗口宽度 |
| 空状态/错误态 | 无数据、加载失败、禁用等状态 UI 是否与设计稿一致 | 模拟各状态 |

### 交互逻辑校验清单

| 检查项 | 校验内容 | 方法 |
|--------|---------|------|
| Pill 选中/取消 | 状态变化是否正确（互斥/至少选一/禁用不可点） | 手动操作 |
| Hover 效果 | 鼠标悬停时样式变化是否与设计稿一致 | 鼠标悬停测试 |
| 展开/收起 | 动画方向、时长 300ms、缓动 ease-in-out | 反复操作观察 |
| Tooltip | 2 行格式、显示延迟 200ms、位置、样式 | 逐一悬停检查 |
| 筛选联动 | DATA/BENCHMARK 变化后进度条增减是否正确 | 全组合测试 |
| 排序 | IndicatorBar 是否按百分位从高到低排序 | 切换筛选观察 |
| 数据刷新 | 切换日期后数据是否重新请求，Loading 状态是否显示 | 操作 + Network |
| 边界交互 | 禁用项不可点击、最少选一的限制、空数据灰色条 | 边界操作测试 |
| 雷达图 | ECharts Tooltip、图例点击显隐、数据点悬停 | 图表交互测试 |
| 折线图 | Trend 模式下折线是否正确渲染、Tooltip 内容 | 切换到 Trend 测试 |

### 校验报告格式

```markdown
## 模块校验报告 — [模块名]

**校验日期**：YYYY-MM-DD
**对照 Figma**：[Figma 链接或节点 ID]
**校验结果**：通过 / 有待修复项

### 待修复项

| # | 类型 | 组件/区域 | 问题描述 | 严重程度 | Figma 参考 |
|---|------|----------|---------|---------|-----------|
| 1 | UI | FilterBar | Pill 圆角应为 8px，实际为 4px | 低 | [节点链接] |

### 通过项

- [x] FilterBar 布局结构
- [x] Overall Score 进度条颜色规则
- [x] ...
```

**严重程度定义**：
- **高**：功能阻断或数据展示错误（百分位计算错误、筛选联动失效）
- **中**：交互行为与设计不符但不阻断使用（动画缺失、状态未重置）
- **低**：视觉细节偏差（间距差 2px、色值偏差）

---

## 附录

### 附录一：6 个核心指标

| 分类 | 名称 | 公式 | 排序方向 | 值单位 |
|------|------|------|---------|--------|
| Revenue & Growth | ARR Growth Rate | (ARR_t - ARR_{t-1}) / ARR_t | 升序（越高越好） | `%`（百分比，如 45.2%） |
| Profitability & Efficiency | Gross Margin | Gross Profit / Revenue × 100% | 升序 | `%`（百分比，如 68.5%） |
| Burn & Runway | Monthly Net Burn Rate | Net Income - Capitalized R&D | 降序（越低越好） | `currency`（金钱，如 $350k） |
| Burn & Runway | Monthly Runway | -Cash / Monthly Net Burn Rate | 升序 | `none`（无单位，如 18） |
| Capital Efficiency | Rule of 40 | (Net Profit Margin + MRR YoY Growth) × 100% | 升序 | `%`（百分比，如 30.0%） |
| Capital Efficiency | Sales Efficiency Ratio | (S&M Expenses + S&M Payroll) / New MRR LTM | 升序（越低越好） | `currency`（金钱，如 $650k） |

### 附录二：百分位计算方法

**内部同行（Nearest Rank Method）**：
$$P_{target} = \frac{R - 1}{N - 1} \times 100$$

**外部基准（线性插值法）**：
- 数据在 P25~P75 范围内：线性插值 → 显示 `~P{val}`
- 超出范围：显示 `>P75` 或 `<P25`，汇总用边界值
- 仅有 P50 时：> P50 → P75，= P50 → P50，< P50 → P25

### 附录三：Design Token 色板

| Token | Hex | 用途 |
|-------|-----|------|
| Blue/900 | `#0D2B56` | 标题、数值文字 |
| Blue/800 | `#19418D` | VIEW/FILTER Pill 选中背景 |
| Blue/400 | `#5B9CE3` | Actuals-High Alpha 组合色 |
| Blue/50 | `#E5F1FA` | VIEW/FILTER Pill 未选中边框 |
| Golden/Primary | `#E1990F` | 主题金色 |
| Golden/300 | `#F6CD7D` | P50-75 进度条填充 |
| Golden/200 | `#F6BD7D` | DATA/BENCHMARK Pill 选中背景 |
| Golden/50 | `#FDEFDF` | 警告横幅背景 |
| Grey/900 | `#15191C` | 标签文字 |
| Grey/800 | `#4E5153` | 正文文字、指标标签 |
| Grey/700 | `#6D7174` | 辅助文字、刻度标签 |
| Grey/400 | `#D6D8DC` | DATA/BENCHMARK Pill 未选中边框 |
| Grey/300 | `#ECEEF1` | 进度条轨道、信息图标背景 |
| Grey/50 | `#F9F9F9` | 页面背景 |
| Green/700 | `#007235` | P≥75 进度条填充 |
| Red/400 | `#DA5858` | P<25 进度条填充 |
| Red/200 | `#F29E9D` | P25-50 进度条填充 |
| Accent Yellow/700 | `#E3C200` | Actuals-Internal Peers 组合色 |
| Accent Orange/600 | `#D85E18` | Actuals-KeyBanc 组合色 |
| Accent Orange/800 | `#753815` | Committed/SysGen-KeyBanc 组合色 |
| Purple/800 | `#833ACE` | Committed/SysGen-Internal Peers 组合色 |
| Green/300 | `#87CA90` | Actuals-Benchmarkit.ai 组合色 |
| Green/700 | `#009344` | Committed/SysGen-Benchmarkit.ai 组合色 |

### 附录四：Typography 速查

| Style Token | Font | Weight | Size | Line Height |
|-------------|------|--------|------|-------------|
| Heading/H1 | Futura PT | 500 | 28px | 32px |
| Heading/H2 | Futura PT | 500 | 24px | 32px |
| Number/Big Number | Futura PT | 500 | 72px | 32px |
| Number/Medium Number | Futura PT | 500 | 48px | 40px |
| Body/Body | Futura PT | 450 | 14px | 20px |
| Body/Body Bold | Futura PT | 500 | 14px | 20px |
| Table Header/Small Bold | Futura PT | 500 | 12px | 16px |
| Table Header/Small | Futura PT | 450 | 12px | 16px |
| Other/Extra Small | Futura PT | 500 | 10px | 14px |
| Button/Body Medium Bold | Futura PT | 500 | 16px | 24px |

### 附录五：UI 动画规范

| 动画类型 | 时长 | 缓动函数 |
|---------|------|---------|
| 展开/收起 | 300ms | ease-in-out |
| 进度条增长 | 300ms | ease |
| 数值更新 | 200ms | — |
| Tooltip 显示 | 150ms (delay 200ms) | — |
| VIEW 切换 | 300-500ms | — |
| 骨架屏加载 | — | 逐项淡入 |
