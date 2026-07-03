# AI Chatbot 回答内嵌图表 — 设计 spec

> 依赖: 统一 SSE 协议（后端 `CIOaas-python/source/llm/infrastructure/llm_router/sse.py` 的 `event_to_sse_bytes`；前端 `CIOaas-web/src/services/sse/`）· 实现计划见 `docs/superpowers/plans/`（writing-plans 阶段产出）
> 状态: 设计已与用户确认（2026-06-10），已实现；2026-07-03 类型扩展至 10 类（方案见 [2026-07-02-chatbot-chart-optimization-design.md](./2026-07-02-chatbot-chart-optimization-design.md)）
> 图表类型: 以后端 `ai/chatbotgraph/chart/spec.py` 的 `CHART_TYPES` 为**单点**（bar / line / area / stacked_bar / horizontal_bar / pie / donut / radar / scatter / combo），前端对应 `chat/utils/charts/registry.ts`

## 1. 背景与目标

AI Chatbot（`/ai/devSupport/chat`）当前回答是纯文本 SSE 流式。需求：**回答内容里按需穿插图表**，支持「文本 → 图表 → 文本 → 图表」混排；前端按图表类型（柱状/折线/雷达/饼图）渲染；图表数据来自真实业务数据；历史会话可重现图表。

本设计延续已统一的 SSE 结构化事件协议（`thread`/`blocked`/`needs_pick` + 新增 `chart`）。

## 2. 范围

**In：**
- LLM 合成回答时按需产出图表，数据取自 `tool_results` 真实业务数据。
- 图表以 `event: chart` 结构化 SSE 事件下发；文本仍走 `delta`。
- 前端按类型组合渲染（复用现有 ECharts）。
- 历史持久化与重现。
- 图表类型 MVP：`bar` / `line` / `radar` / `pie`。

**Out（YAGNI，本期不做）：**
- 图表交互（下钻、联动、导出）。
- 图表编辑/重新生成。
- 自定义主题/配色（复用现有 `chartTheme`）。
- `bar/line/radar/pie` 以外的类型。
- 后端结构化 blocks 持久化（用 content 含 fence 原文，不改 DB schema）。

## 3. 核心决策（已与用户确认）

| 决策点 | 结论 |
|--------|------|
| 图表数据来源 | LLM 合成时产出，数据**必须取自 `<context>` 真实 `tool_results`，禁止编造** |
| LLM 载体 | LLM 输出 markdown，图表用 ` ```chart {json}``` ` fenced code block 内联 |
| 数据格式 | **与渲染库无关的二维表纯数据**：`{type, title?, columns, rows}`；后端只产数据，**前端组合成 ECharts** |
| 传输 | 后端流式 fence 切分：文本→`delta`、图表→`event: chart`（复用 `event_to_sse_bytes`），后端 SSE 设施零新增 |
| 持久化 | `ai_chatbot_message.content` 存含 fence 完整原文，**不改 DB schema**；历史靠前端 `parseChartFences` 重现 |

## 4. 数据契约

### 4.1 chart spec（fence 内 JSON / `event: chart` 的 data）

```jsonc
{
  "type": "bar | line | area | stacked_bar | horizontal_bar | pie | donut | radar | scatter | combo",
  "title": "可选标题",
  "columns": ["季度", "营收", "成本"],   // 第一列 = 分类轴，其余列 = 数据系列
  "rows": [
    ["Q1", 100, 60],
    ["Q2", 120, 70],
    ["Q3", 150, 85]
  ],
  // ↓ combo 专用可选字段（其余类型忽略；2026-07-03 扩展，向后兼容）
  "seriesTypes": ["bar", "line"],   // 对应 columns[1..] 各系列画法，缺省全 bar
  "rightAxis": ["成本"]             // 放右 Y 轴的系列名（量纲不同的 % 比率等）
}
```

**统一约定（前端按 type 组合）：**
- `columns[0]` = 分类轴标签字段；`columns[1..]` = 各数据系列名。
- 每行 `rows[i][0]` = 该分类值；`rows[i][1..]` = 各系列在该分类下的数值。
- `bar` / `line` / `area` / `stacked_bar` / `combo`：`columns[0]`→x 轴，`columns[1..]`→多条柱/线（系列名取自 `columns`）；`horizontal_bar` 类目轴换到 y（首行在最上）。
- `radar`：`rows[*][0]`→雷达指标（indicator），`columns[1..]`→多组雷达数据。
- `pie` / `donut`：取 `columns[1]`（第二列）为值，`rows[*][0]` 为扇区名；多数值列时只用第一数值列。
- `scatter`（**xy 形状，例外**）：`columns` 恰好 3 列 `[点标签, x 指标, y 指标]`，每行 `[label, x, y]`，单系列；与 categorical 组类型**不可互切**（前端切换器按数据形状分组）。
- 校验：后端 `ai/chatbotgraph/chart/spec.py` pydantic `ChartSpec`（fence 解析后校验失败降级为文本）；前端流式/历史两路径共用 `isValidChartSpec` 结构校验。

> 该格式是**纯数据表**（无 `xAxis`/`series` 等 ECharts 概念）。后端绝不组装 ECharts option。

### 4.2 SSE `event: chart` 帧

复用上次统一的 `event_to_sse_bytes("chart", spec)`：

```
event: chart
data: {"type":"bar","title":"营收趋势","columns":["季度","营收","成本"],"rows":[["Q1",100,60]]}

```

文本仍是默认无 event 名的 `data: {"delta",...}`；结束 `data: [DONE]`；错误 `event: error`。**协议无新增帧类型，`chart` 是已有结构化事件机制的一个新事件名。**

## 5. 端到端数据流

```
LLM 合成(astream) 输出 markdown（图表用 ```chart {纯数据} ``` fence 内联）
      ↓ 逐 token 文本流
后端 chat_service：ChartFenceStreamParser.feed(delta)
   · fence 外文本片段 → chunk_to_sse_bytes（默认 delta 事件）
   · ```chart 内 → 累积 → ``` 闭合 → JSON.parse → event_to_sse_bytes("chart", spec)
   · buf 累积【完整含 fence 原文】→ stream 结束后落库 content
      ↓ SSE：delta 文本 + event: chart（结构化纯数据）
前端 streamApi.onFrame：event==='chart' → onChart(spec)；默认 → onDelta(text)
      ↓
前端消息 blocks 模型 + 渲染
   · 流式：onDelta 追加末尾 text 段；onChart push 一个 chart 段（按到达顺序）
   · chart 段 → chartSpecToOption(spec) 组合 ECharts → <ChatChart>
   · 历史：fetchMessages.content(含 fence) → parseChartFences → 同款 blocks → 同款渲染
```

## 6. 后端设计（CIOaas-python）

### 6.1 `ChartFenceStreamParser`（新增，chatbot 内）

流式状态机，输入逐个文本 chunk，输出有序片段序列 `[{kind:'text', text} | {kind:'chart', spec}]`。

- **状态**：`TEXT`（普通文本）/ `IN_FENCE`（```chart 内累积）。
- **进入 fence**：检测到行首 ` ```chart `（fence info string == `chart`）。进入前的文本作为 text 片段产出。
- **退出 fence**：检测到闭合 ` ``` `。把累积的 fence body `JSON.parse` 成 chart spec 产出。
- **跨 chunk 边界**：用 buffer 缓冲；当缓冲尾部可能是不完整的 fence 标记（如 ` ``` ` 被截断）时 hold 住、不提前作为文本产出，等下个 chunk 续上再判定。
- **降级（不阻断）**：
  - fence body JSON 解析失败 → 把原始 ` ```chart…``` ` 整段作为 **text 片段**产出（前端显示为代码块）。
  - 流结束时仍在 `IN_FENCE`（未闭合）→ 已累积内容作为 text 片段产出，不丢内容。
- 纯逻辑、无 IO，**可单测**（喂各种 chunk 切分组合，断言产出序列）。

### 6.2 `chat_service.stream_turn` 集成

正常合成分支（现 `async for chunk in llm_db_router.astream(...)`）改为：

- 每个 `chunk.delta` → `parser.feed(delta)`，对产出的片段：
  - `text` → `yield chunk_to_sse_bytes(TextChunk(delta=text, is_final=False))`
  - `chart` → `yield event_to_sse_bytes("chart", spec)`
- 循环结束 `parser.flush()`（吐出尾部缓冲）后 `yield done_marker()`。
- `buf` 仍累积**原始 `chunk.delta`（含 fence 原文）** → 落库 `content`（持久化不变）。
- `blocked`/`needs_pick`/`thread` 分支不变。

### 6.3 合成 prompt（`prompts.SYNTHESIS_SYSTEM`）

新增图表指令：
- **何时出图**：数据适合可视化时（趋势→`line`、对比→`bar`、多维评分→`radar`、占比→`pie`）；不适合则正常文字、不强行出图。
- **怎么出图**：用 ` ```chart ` 代码块，块内是 `{type,title?,columns,rows}` 二维表 JSON。
- **数据红线（强约束）**：`columns`/`rows` 的数值**必须来自 `<context>` 里的真实 `tool_results`，禁止编造、估算、补全**；无对应数据则不出图。
- 附 1–2 个 few-shot（含 fence + 二维表格式）。

## 7. 前端设计（CIOaas-web）

### 7.1 `services/api/chat/streamApi.ts`
- `StreamChatCallbacks` 新增 `onChart?(spec: ChartSpec)`。
- `onFrame`：`event==='chart'` → `parseJson<ChartSpec>` → `onChart`。其余分发不变。

### 7.2 消息内存模型（升级）
- 消息内容从纯 `string` → 有序段 `blocks: (TextBlock | ChartBlock)[]`，`TextBlock={type:'text',text}`、`ChartBlock={type:'chart',spec}`。
- 流式（`useChatStream`/reducer）：`onDelta` 追加到末尾 text 段（无则新建）；`onChart` push 一个 chart 段。
- `messageReducer` 增加 `appendChart` action。

### 7.3 `chartSpecToOption(spec)`（新增，纯函数）
- 输入二维表 `{type,columns,rows}`，按 §4.1 约定组合成 ECharts `EChartsOption`，复用 `pages/ai/_shared/chartTheme`。
- 按 type 分支：bar/line（columns[0]→category，columns[1..]→series）、radar（rows[*][0]→indicator，columns[1..]→series）、pie（columns[1]+rows）。
- **此处是唯一「数据→ECharts」的组合点**，后端不参与。

### 7.4 `parseChartFences(content)`（新增，纯函数）
- 输入历史 `content`（含 ` ```chart``` ` 的 markdown），输出与流式一致的 `blocks`。
- 与后端 `ChartFenceStreamParser` 的 fence 约定一致（` ```chart ` 起、` ``` ` 止），解析失败的 fence 降级为 text 段。

### 7.5 渲染组件
- `<MessageContent blocks>`：text 段渲染（markdown/纯文本，沿用现状）、chart 段渲染 `<ChatChart spec>`。
- `<ChatChart spec>`：`chartSpecToOption(spec)` → 复用现有 `ChartCard`/`ReactECharts`；不支持的 type → 占位提示（不崩）。
- **流式与历史共用** `blocks` 模型与 `<MessageContent>`。

## 8. 错误处理与降级（均不阻断对话）

| 场景 | 处置 |
|------|------|
| 后端 fence JSON 解析失败 | 原始 ` ```chart…``` ` 作为文本 delta 发出（前端显示代码块） |
| 流结束 fence 未闭合 | 已累积内容作为文本发出，不丢 |
| 前端不支持的 `type` | chart 段显示占位提示，不崩 |
| 前端 `chartSpecToOption` 异常 | 捕获并降级为占位 + 原始数据提示 |

## 9. 持久化

- `ai_chatbot_message.content` 存 LLM 完整输出（含 ` ```chart``` ` fence）。**不改 DB schema**。
- 历史重现：前端 `parseChartFences(content)` → blocks → 同款渲染。

## 10. 测试要点

- 后端 `ChartFenceStreamParser`：单测各种 chunk 切分（fence 标记跨 chunk、多图表、fence 内非法 JSON、未闭合、fence 与文本交替）。
- 后端 `chat_service`：mock astream 产含 fence 文本，断言产出 `delta` + `event: chart` 顺序、`content` 落库含 fence 原文。
- 前端 `chartSpecToOption`：各 type 二维表 → ECharts option 断言。
- 前端 `parseChartFences`：历史 content → blocks 断言（含降级）。
- 前后端**契约对齐**：同一 chart spec 在「流式 event:chart」与「历史 parseChartFences」两条路径渲染结果一致。

## 11. 复用与改动面小结

- **复用**：统一 SSE 协议（`event_to_sse_bytes`）、前端 ECharts（`ChartCard`/`chartTheme`）、`services/sse` 公共读流、`blocks` 渲染。
- **后端新增**：`ChartFenceStreamParser` + `stream_turn` 集成 + prompt 图表指令。
- **前端新增**：`onChart`、`blocks` 模型 + reducer action、`chartSpecToOption`、`parseChartFences`、`<ChatChart>`/`<MessageContent>`。
- **不动**：DB schema、SSE 协议帧类型、`event_to_sse_bytes` 本身。
