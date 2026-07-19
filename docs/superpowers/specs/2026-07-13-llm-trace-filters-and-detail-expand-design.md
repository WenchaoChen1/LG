# LLM Trace 列表页筛选 + 详情页行内展开 — 设计

> 关联文档：前端 LLM Tracing 规范 [`llm.md`](../../../CIOaas-web/standards/llm.md)；实现计划 `../plans/2026-07-13-llm-trace-filters-and-detail-expand.md`（本 spec 通过后产出）
>
> 状态：设计（待用户确认）｜范围：**纯前端（CIOaas-web），不动 Python/Java**｜日期：2026-07-13

---

## 1. 背景与目标

页面 `/devSupport/llm/trace`（文件 `src/pages/devSupport/llm/TraceView.tsx`）当前有两个痛点：

1. **列表态（无 `traceId`）零筛选** —— 只有一个 Refresh 按钮，无法按厂商 / agent / call type 等维度定位链路。
2. **详情态（`?traceId=`）看得费劲** —— 甘特图每行点击直接跳到另一个页面 `CallDetail`，无法在当前页就地展开看调用详情。

目标：

- 列表页加一条 **8 项精选筛选栏**，与 `chatManage` / `tracing` 等 devSupport 页面的筛选范式一致。
- 详情页保留时间线甘特条，改为 **每行可就地展开** 看该次调用的指标 + 会话 + 错误，配「全部展开 / 收起」开关，不再跳走。

**关键前提**：8 项筛选维度后端 `/api/ai/llm-calls` 全部已支持，本次为**纯前端接线 + 交互改造**，无需改后端。

---

## 2. 现状与数据源（澄清）

`TraceView.tsx` 按 `traceId` query 参数分两态渲染：

| 态 | 触发 | 数据来源 | 现状 |
|---|---|---|---|
| 列表 | 无 `traceId` | `useRecentTraces(200)` → `fetchCallList()` → `GET /api/ai/llm-calls`，前端按 `trace_id` 聚合成链路卡片 | 零筛选，固定拉最近 200 条 |
| 详情 | `?traceId=xxx` | `useTraceCalls(traceId)` → `fetchTraceCalls()` → `GET /api/ai/llm-calls/trace/{traceId}`，返回该 trace 全部调用 | 甘特图，点行跳 `CallDetail` |

数据实体：链路（trace）是 `ai_llm_call_log.trace_id` 的软逻辑分组，**DB 无 trace 主表**；行实体是 `LlmCallDTO`（`src/services/api/llm/llmDto.ts`），已含 `provider / model / callerAgent / nodeName / callType / callMode / status / finishReason / inputTokens / outputTokens / totalTokens / costUsd / elapsedMs / traceId / errorClass / errorMessage / createdAt` 等全部所需字段。

会话内容（prompt / response）单独实体 `ConversationDTO`，经 `GET /api/ai/llm-calls/{id}/conversation` 拉取（不在列表/trace 返回里）。

相关文件：

- `src/pages/devSupport/llm/TraceView.tsx` —— 列表 + 详情（本次主改）
- `src/pages/devSupport/llm/hooks/useRecentTraces.ts` —— 列表聚合 hook（加筛选入参）
- `src/pages/devSupport/llm/hooks/useTraceCalls.ts` —— 详情取数 hook（不变）
- `src/pages/devSupport/llm/hooks/useLlmCallDetail.ts` —— 会话取数 hook（详情展开复用，按需懒加载）
- `src/pages/devSupport/llm/components/FilterToolbar.tsx` —— Call Logs 页完整筛选栏（**筛选范式参照物**）
- `src/pages/devSupport/llm/components/{MetricsCard,PromptPanel}.tsx` —— 详情展开面板**直接复用**
- `src/pages/devSupport/_shared/{FilterField,DirectorySelect,PageHeader}` —— 共享 UI 原子
- `src/pages/devSupport/llm/hooks/useLlmEnums.ts` + `src/services/api/llm/enums.ts` —— 筛选下拉选项来源
- `src/pages/devSupport/llm/index.less` —— 样式

---

## 3. 列表页筛选设计

### 3.1 筛选项（8 项，精选）

顺序遵循全站约定「归属最前、时间靠后」：

| # | 筛选项 | 控件 | 值 → API 参数 | 选项来源 |
|---|---|---|---|---|
| 1 | Company | `CompanySelect`（共享） | `companyId` | 目录接口 + 粘 UUID |
| 2 | User | `UserSelect`（共享） | `userId` | 目录接口 + 粘 UUID |
| 3 | Time Range | `RangePicker`（showTime） | `startTime` / `endTime`（ISO） | — |
| 4 | Agent | `Select`（showSearch） | `callerAgent` | `useLlmEnums().callerAgent` ← 回退静态 `CALLER_AGENTS` |
| 5 | Provider | `Select` | `provider` | `useLlmEnums().providers` ← 回退 `PROVIDERS` |
| 6 | Call Type | `Select` | `callType` | `useLlmEnums().callType` ← 回退 `CALL_TYPES` |
| 7 | Status | `Select` | `status` | 静态 `STATUS_OPTIONS` |
| 8 | Trace ID | `Input`（allowClear，精确） | `traceId` | — |

- 复用 `FilterToolbar.tsx` 已验证的原语：`FilterField` 包裹（label 大写、控件统一 36px）、`withAll()` + `ALL_VALUE` 占位（「All」预选、比 placeholder 直观）、受控 `value + onChange`。
- 控件宽度沿用 `FilterToolbar` 的约定值：Company 200 / User 240 / Time Range 380 / Provider 140 / Status 130 / Agent 180 / Call Type 150 / Trace ID 260。
- 操作区：`Reset`（次要，`UndoOutlined`）+ `Refresh`（主色，`ReloadOutlined`），与 `FilterToolbar` 一致。
- **不用 antd `<Space>` 包子项**（会垂直居中导致底端错位）；容器为 flex 一行：`display:flex; flex-wrap:wrap; align-items:flex-end; gap`。

### 3.2 页头

列表态顶部用共享 `PageHeader`：

- `title`: `LLM Traces`
- `description`: `N traces match current filters`（计数）
- `extra`: 时区提示（可选）——Refresh 已并入筛选区，页头不重复放。

（替换掉现有裸 `<h1> + Refresh` 的 `titleBar`。）

### 3.3 聚合语义（已与用户确认）

筛选作用在**调用**上，走**一次请求**：

1. `useRecentTraces` 接收筛选入参，透传给 `fetchCallList()`（`firstAttemptOnly=false`、`sortBy=created_at`、`sortDesc=true`、`limit` = 窗口上限）。
2. 后端返回**匹配到的调用**，前端 `aggregate()` 按 `trace_id` 聚合成链路卡片。
3. 因此：列表展示「**含匹配调用的链路**」，每张卡片的 Calls / Tokens / Cost / Failed 汇总的是**匹配到的那部分调用**（非整条链路的完整统计）。
4. 点进某条 trace 的**详情页仍按 `traceId` 拉该 trace 全部调用**（`useTraceCalls`），**不受列表筛选影响** —— 打开即看完整链路。

**窗口**：聚合发生在「最近 N 条匹配调用」上（与现状同性质，只是加了过滤）。窗口上限 `limit` 从现在的 200 提到 **500**（后端 `/api/ai/llm-calls` 上限），覆盖更多链路；聚合是「最近窗口内分组」而非全库统计，此语义在页面副标题/说明中明示，避免误解为全量精确统计。

> 备选（未采纳）：卡片始终显示整条链路完整统计 —— 需两步请求（先筛出 `trace_id`，再按 id 拉全量再聚合），更重，YAGNI 不做。

### 3.4 URL query 同步

筛选状态同步到 URL query（`companyId` / `userId` / `startTime` / `endTime` / `callerAgent` / `provider` / `callType` / `status` / `traceIdFilter`），刷新/分享可复现（对齐 `CallList` / `tracing/TraceList` 范式）。空值不写入 query。

**注意（实现时发现并定案）**：Trace ID 筛选的 URL 键名用 **`traceIdFilter`** 而非 `traceId`——`/devSupport/llm/trace` 路由用 `?traceId=` 切换到详情态（甘特图），列表筛选若原名写入 URL 会被误判为详情跳转。前端 filters 对象内部字段仍是 `traceId`（透传后端参数不变），仅 URL 键名做映射。

---

## 4. 详情页行内展开设计

### 4.1 布局

保留现有结构：顶部 summary 4 卡 + 时间刻度尺 + 甘特行。改动集中在**甘特行**：

- 行首加展开图标（`▸` / `▾`），点击行或图标 → 切换该行展开态（**不再** `goDetail` 跳走）。
- 顶部工具区（Back 旁）加一个 **`Expand all` / `Collapse all`** 开关。
- 展开态：在甘特行下方插入一块详情面板。

### 4.2 展开面板内容

一块轻量面板（`CallExpandPanel`，见 §5），复用现有组件、不新造展示轮子：

- **指标**：复用 `MetricsCard`（Total Tokens in/out · Cost · Latency + 失败错误面板）。
- **补充元信息行**（小 chip，`MetricsCard` 未覆盖的）：`callType` · `callMode` · `finishReason`。
- **会话**：复用 `PromptPanel`（system / user / assistant 三色气泡）；无会话记录时显示「No conversation recorded」（组件已内建）。
- **深看入口**：面板内一个 `Open full detail ↗` 链接跳原 `CallDetail`（`/devSupport/llm/detail?id=`，带 `state.call`），保留完整详情页（含 Raw messages JSON）。

### 4.3 懒加载

- 会话（`ConversationDTO`）按需拉：展开面板组件 `CallExpandPanel` **内部** `useLlmCallDetail(callLogId)`，组件仅在行展开时挂载 → 首次展开才发请求，收起卸载。
- `Expand all` = 全部行展开 → 所有面板挂载 → 各自拉会话（trace 内调用通常 ≤ 数十条，可接受）。
- 面板内会话区带 loading 态。

### 4.4 顺手修复的 bug

- `TraceView.tsx:203` 甘特行 label 用了 `r.callerNode`，但 `LlmCallDTO` 字段是 **`nodeName`**（无 `callerNode`）→ 当前渲染为空。改为 `r.nodeName`。这是本次改动直接涉及的行，属「改到就顺手修」。

---

## 5. 数据流与组件划分

```
TraceView (route /devSupport/llm/trace)
├── 无 traceId → RecentTracesList
│     ├── PageHeader (title/description/extra)
│     ├── TraceFilterBar   ← 新增：8 项受控筛选栏（复用 FilterField/DirectorySelect/useLlmEnums/withAll）
│     │     value: TraceListFilters  onChange/onReset/onRefresh
│     └── 卡片列表 ← useRecentTraces(filters, limit=500)   ← 改：加 filters 入参，透传 fetchCallList
│           └── URL query ↔ filters 同步
│
└── 有 traceId → 甘特详情
      ├── summary 4 卡（不变）
      ├── Expand all / Collapse all 开关   ← 新增
      └── 甘特行（可展开）← useTraceCalls(traceId)（不变）
            └── 展开 → CallExpandPanel   ← 新增
                  ├── MetricsCard(call)        （复用）
                  ├── 元信息 chips: type/mode/finishReason
                  ├── PromptPanel(conversation)（复用）← useLlmCallDetail(callLogId) 懒加载
                  └── Open full detail ↗ → CallDetail
```

- **新增前端单元**：`TraceFilterBar`（列表筛选栏）、`CallExpandPanel`（详情展开面板）、`useRecentTraces` 的 filters 入参、`TraceView` 展开态管理。
- **无跨业务域边界破坏**：仍只经 `services/service/llm/llmService` 公开导出取数，不碰 Response/Request 类型（`llm.md` §3）。
- **筛选栏取舍**：`TraceFilterBar` 是 `FilterToolbar` 的 8 项子集，但 `FilterToolbar` 与 `CallList` 的完整 `ListCallsInput` 强耦合，直接复用会带入 Node/Mode/Model/Cost/Sort/Show-retries 等多余项。按 YAGNI 新建一个精简受控组件、复用同一批 `_shared` 原子，不复用整个 `FilterToolbar`。

---

## 6. 边界与错误处理

- 筛选空结果：卡片列表显示 `Empty`（沿用现有空态；历史无 `trace_id` 数据的说明保留）。
- 取数失败：列表/详情沿用现有 `error` 文案区（红字）。
- 会话懒加载失败：`PromptPanel` 区内提示，不影响指标区与其他行。
- hooks 全部保留 `cancelled` flag cleanup（`llm.md` §9 / `coding.md` §10）——`useRecentTraces` 加 filters 后 `useEffect` 依赖需含 filters（序列化后作为依赖，避免对象引用抖动导致重复请求）。
- Trace ID 精确输入 trim 后为空则不发字段（对齐 `FilterToolbar`）。

---

## 7. 规范符合性（`standards/llm.md`）

- §1 路由前缀不变（`/devSupport/llm/trace`）。
- §3 三层传输实体：只用 `LlmCallDTO` / `ConversationDTO`，筛选入参用 `services` 层已有的 Input 类型（`ListCallsInput` 或其精简子类型）；组件不 import Request/Response。
- §5 状态色 / 设计 token：复用 `STATUS_CLASS_MAP` 与 `_shared/tokens.less` 色板，新增样式走 `index.less`（已 `@import _shared/tokens.less`），不引孤立调色板。
- §8 权限：路由 `authority` 与 `hideInMenu` 不变；前端不做公司硬过滤，信任后端。
- §9 测试：`useRecentTraces` 加 filters 后的聚合、URL↔filters 同步、`CallExpandPanel` 懒加载与展开/收起为关键覆盖点。

---

## 8. 测试要点（详见后续测试用例）

- 列表：设/清各筛选项 → 请求参数正确、卡片按匹配调用聚合、URL query 同步、Reset 清空。
- 列表：Provider/Agent/CallType 组合筛选下卡片统计口径符合 §3.3 语义。
- 详情：单行展开/收起、Expand all/Collapse all、会话懒加载（仅展开才请求）、失败行错误展示、`Open full detail ↗` 跳转带 state。
- 详情：`nodeName` 正确渲染（回归 bug 修复）。

---

## 9. 非目标（YAGNI）

- 不加 `Purpose` / `Cost Source` 筛选（后端未暴露筛选参数 / 列表未返回字段，另立后端任务再做）。
- 不加 Model / Node / Call Mode / Finish Reason / Cost 区间 / Token 区间 / Show-retries（属「完整版」，本次精选 8 项不含）。
- 不把列表卡片改成 Table，不改甘特图为表格/抽屉（详情按「时间线 + 行内展开」定稿）。
- 不做卡片「整条链路完整统计」的两步请求（§3.3 备选未采纳）。
- 不动后端、不改数据模型。
