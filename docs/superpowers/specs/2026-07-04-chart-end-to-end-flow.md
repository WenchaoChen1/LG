# 图表：从生成到展示的端到端流程

> 关联文档: [图表契约](./2026-06-10-chat-chart-design.md) · [修复回路删除](./2026-07-04-chart-repair-removal-design.md) · [规则走 tool](./2026-07-04-chart-guide-via-tool-design.md) · [前端渲染校验](./2026-07-04-chart-frontend-render-validation-design.md)
> 状态: 现状描述（2026-07-04，含两项优化落地后的目标态）
> 用途: 一页看懂图表能力的完整链路与各层职责；新人/排查入口文档

## 0. 一句话架构

**AI 用工具学规则、写完自查，把图表当作 markdown 围栏嵌进回答；后端流式切分并校验，合法发结构化事件、非法降级文本；前端渲染前再校验一次，合法组装 ECharts、非法给占位符；落库永远是原文。**

## 1. 全流程（编号步骤）

```
┌─ 生成期（Python · ReAct agent）──────────────────────────────────────┐
│ ① 系统提示词 stub（CHART_SECTION ~12 行，两轨共用）：                  │
│    能画图 + fence 协议 + 通用二维表规则 + 数据红线 + 工具流程指令       │
│ ② AI 调数据工具取真实数字（get_financials / get_benchmark_data …）    │
│ ③ 要画非 bar/line → 必须先调 get_chart_guide                          │
│    ← 返回逐类型规则目录（场景→类型、每类型列约定；只在画图轮进上下文）  │
│ ④ AI 构造 chart spec（纯数据二维表 {type?,title?,columns,rows,…}）    │
│ ⑤ 复杂类型（boxplot/combo/bubble/gauge/waterfall）→ 必须调             │
│    validate_chart 复验：ok → 规范化 spec 原样用；否则按 errors 修正重验 │
│ ⑥ 把 spec 以 ```chart {json}``` 围栏嵌进 markdown 答案（可多图混排）   │
└──────────────────────────────────────────────────────────────────────┘
┌─ 流式下发（Python · sse_provider，纯管道无 IO）───────────────────────┐
│ ⑦ 答案逐 token → ChartFenceStreamParser（状态机，跨 chunk 容错）：      │
│    · 围栏外文字 → delta 事件（即时流出）                               │
│    · 围栏闭合 → parse_chart_spec（pydantic，按 format 分支校验）        │
│         合法 → event: chart（结构化纯数据，立即下发）                   │
│         非法 → 围栏原文当文本 delta 发出（用户看到 JSON 代码块）        │
│    · 流结束仍未闭合 → 原文回吐，绝不丢内容                             │
│ ⑧ buf 累积完整原文 → 落库 ai_chatbot_message.content（恒为原文）       │
└──────────────────────────────────────────────────────────────────────┘
┌─ 展示（React 前端）──────────────────────────────────────────────────┐
│ ⑨ 流式：event: chart → isValidChartSpec（最小结构）→ blocks 插 chart 段│
│    历史/刷新：parseChartFences(content) 重切 blocks（同款渲染路径）     │
│ ⑩ ChatChart（唯一渲染收口点）：                                        │
│    a. validateChartSpec（镜像后端 _check_format）                       │
│       失败 → 占位卡「图表数据格式有误」+ 弱化「详情」（错误+原始 JSON）  │
│    b. resolveType：AI 建议 type 用之；缺省按数据特征选默认               │
│       （单序列→line / 多序列→bar）                                     │
│    c. 切换器：同 format 组内 + suits 适合的类型才列出；样式变体可选      │
│    d. buildChart(spec, type, style)：组装 ECharts option                │
│       （traits 规则 R1-R6 按数据特征自动美化）；异常 → 同占位卡          │
│ ⑪ 管理页 chatManage：MarkdownView 不解析围栏（管理员看原文代码块，刻意） │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. 各层职责与检查手段（谁在哪里查什么）

| 层 | 位置 | 用什么查 | 查什么 | 失败表现 |
|----|------|----------|--------|----------|
| 生成期·规则 | `get_chart_guide` 工具 | 返回规则目录 | 教 AI 场景→类型、列约定 | —（教学，不判定） |
| 生成期·自查 | `validate_chart` 工具 | `parse_chart_spec_verbose` | 语义合法性（同落地规则） | `{ok:false, errors}` 回喂 AI 修正 |
| 流式·落地 | `fence_parser` | `parse_chart_spec`（pydantic 单点） | 同上（列数/数值/gauge 0-100/boxplot 单调/waterfall 非 null） | 围栏原文降级文本 |
| 前端·渲染前 | `charts/validate.ts` | `validateChartSpec`（镜像后端） | 同上（防历史坏 fence 与前后端漂移） | 占位卡 + 弱化详情 |
| 前端·适合度 | `registry.suits` | 数据形状判定 | 「能看但不合适」（如多序列禁 pie） | 切换器不列（不算失败） |
| 前端·兜底 | ChatChart try/catch | builder 异常捕获 | 运行时崩溃 | 同占位卡（「图表渲染失败」） |

规则**单点**：后端三处（guide 教学文本除外）共用 `spec.py`；前端 `validate.ts` 是跨 wire 的镜像副本，**同步契约**写在两文件头注释（改一边必须同步另一边，同 benchmark calc 先例）。

## 3. 数据驱动四层（前端选型与美化）

**format（能画什么）→ validate（这份数据合不合法）→ suits（组内哪些适合）→ traits（怎么画好看）**

- format：5 格式 18 类型，`TYPE_FORMAT` 查表（LLM 只输出 type，format 推导）；切换器只在同 format 组内互切。
- validate：本页 §2 前端渲染前校验。
- suits：pie/donut/treemap 单序列≥2 行、radar≥3 类目、combo≥2 序列、bubble 恰 4 列、heatmap≥2×2。
- traits：R1 单线平滑渐变 / R2 单区渐变 / R3 密点隐标记 / R4 多线 hover 聚焦 / R5 柱顶圆角 / R6 长轴标签倾斜。

## 4. 持久化与一致性

- 落库**恒为原文**（含围栏 markdown），不改 DB schema、绝不改写——流式呈现与历史重现的一致性由「前端历史路径重解析同一份原文」保证。
- 断流恢复（sessionStorage stream_id + `/subscribe` 重放）与图表无耦合：重放的是同一批 SSE 帧。
- fork/重新生成复制原文消息，图表随原文自然重现。

## 5. 防线总览（坏图到不了用户眼前的四道闸）

1. 数据红线（提示词常驻）：没有真实数据不出图、缺数填 null 不编数。
2. validate_chart 必须复验（复杂类型）：生成期拦截 + errors 教学。
3. fence 落地校验：非法围栏降级文本（用户最多看到 JSON 代码块）。
4. 前端渲染前校验：历史路径的语义违规 spec → 占位符，不画错图。

修复回路（LLM 自动改写坏 fence）已于 2026-07-04 删除（`458c270`，存档 `8bd9dbd`，`git revert` 可一步恢复）——上述四道闸取代之。
