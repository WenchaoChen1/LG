# AI Chatbot 图表优化 — 方案头脑风暴（待选型）

> 关联文档: [2026-06-10 图表设计 spec](./2026-06-10-chat-chart-design.md) · [AI-Chatbot 设计](../../AI-Chatbot/设计/design-doc.md)
> 状态: 头脑风暴产出，含多方案对比，**待用户选型**后进 writing-plans
> 日期: 2026-07-02

## 1. 现状盘点（先纠正两个前提）

动手前先说清两件与直觉不符的事实：

**① 「单独的图表文件」前后端其实已经有了。** 现状不是"图表代码内联在大组件里"：

| 端 | 文件 | 行数 | 职责 |
|----|------|------|------|
| 前端 | `CIOaas-web/src/pages/ai/chat/components/ChatChart.tsx` | 103 | 图表渲染组件（含类型切换器、resize 兜底、降级占位） |
| 前端 | `CIOaas-web/src/pages/ai/chat/utils/chartSpec.ts` | 160 | **唯一**「二维表数据 → ECharts option」组合点 |
| 前端 | `CIOaas-web/src/pages/ai/chat/utils/parseChartFences.ts` | 42 | 历史消息 ```chart fence 解析 |
| 前端 | `CIOaas-web/src/services/api/chat/chatDto.ts` | — | `ChartSpec` / `ChartType` 数据契约 |
| 后端 | `CIOaas-python/source/ai/chatbotgraph/chart_fence_parser.py` | 111 | 流式围栏解析状态机（纯逻辑、可单测，已有 10 个用例） |

**② 雷达图已经支持。** 当前支持 4 类：`bar` / `line` / `radar` / `pie`（前端 `SUPPORTED` 枚举与后端提示词一致）。缺的是散点图、面积图、堆叠柱、柱线组合等。

## 2. 真正的问题

不是"缺独立文件"，而是**图表类型定义散落多处、无单点**。今天要新增一种图表类型，需要改 **5 处**：

1. 后端 tool 轨提示词 `prompts/chatbot/retrieval_agent_prompt.py` 图表段（类型枚举写死在提示词文本里）
2. 后端 sql 轨提示词 `prompts/chatbot/retrieval_sql_agent_prompt.py` 图表段（**与上面整段重复维护**，2026-07 提示词拆轨后遗留）
3. 前端 `chatDto.ts` 的 `ChartType` 联合类型
4. 前端 `ChatChart.tsx` 的 `SUPPORTED` + `TYPE_LABEL`
5. 前端 `chartSpec.ts` 的 `chartSpecToOption` 新增分支（该文件已 160 行，再加 6 种类型将膨胀为 400+ 行单文件）

配套问题（顺带修的候选）：

- 后端对 LLM 产出的图表 JSON **零校验**（只查 `"type"` 字段存在，无 pydantic 模型），非法 spec 原样下发靠前端兜底
- 前后端 fence 解析规则有细微不一致（前端 regex 允许 `chart` 后带空白，后端严格字符串匹配 `` ```chart ``）
- 管理页 `chatManage` 自实现图表、不复用 `ChatChart`；`ChatChart` 与 llm 模块 `ChartCard` 各写一份 ResizeObserver 兜底

## 3. 方案一：代码组织（"独立图表文件"怎么做才对）

### 方案 A — 最小收敛（不动文件布局）

- 后端新增一个 `chart_spec.py`：pydantic `ChartSpec` 模型 + 类型枚举 + **提示词图表段常量**（两轨提示词 import 同一常量，消除双份维护）；`chart_fence_parser` 解析后过 pydantic 校验。
- 前端 `chartSpecToOption` 内部改为「type → builder 函数」字典映射，文件不拆。

**优点**：改动最小，一天量级。
**缺点**：前端 `chartSpec.ts` 仍会随类型增加膨胀成巨型单文件；`SUPPORTED`/`TYPE_LABEL` 与 builder 仍分居两文件。

### 方案 B — 图表子模块 + 注册表（推荐）

前后端各建图表专属模块，**一类型一 builder 文件 + 注册表派生一切**（与 CIOaas-python "一个 @tool 一个文件" 的既有风格一致）：

**后端** `source/ai/chatbotgraph/chart/`（包）：

```
chart/
├── spec.py             # pydantic ChartSpec + ChartType 枚举（类型单点）
├── prompt_section.py   # 由枚举生成提示词图表段，tool/sql 两轨共用一份
└── fence_parser.py     # 现 chart_fence_parser.py 迁入（git mv），解析后过 spec.py 校验
```

**前端** `src/pages/ai/chat/charts/`（组件与 builder 就近内聚；`chatDto.ts` 契约不动）：

```
charts/
├── registry.ts         # type → { label, builder, shape }，SUPPORTED/TYPE_LABEL 由此派生
├── builders/           # 一类型一文件（bar.ts / line.ts / pie.ts / radar.ts / scatter.ts / …）
│   └── _shared.ts      # num()/isBlank()/tooltip 等公共件（自现 chartSpec.ts 拆出）
└── ChatChart.tsx       # 迁入（读 registry，不再自持类型枚举）
```

新增一种类型 = 后端枚举 +1 行（提示词段自动带上）+ 前端加一个 builder 文件并注册。**改 2 处、都是"加"不是"改"**。

**优点**：类型单点、扩展成本恒定、文件小而聚焦；后端提示词双份维护顺带消除。
**缺点**：一次性迁移改动面比 A 大（约 2–3 天量级，含测试）；目录移动需同步 import。

### 方案 C — 全局共享图表库（范围最大）

在方案 B 之上继续外扩：模块提升到 `ai/_shared/charts/`，`chatManage` 改复用 `ChatChart`，`ChartCard` 升级为通用容器，ResizeObserver 抽 `useEChartsResize` hook，llm/chat/chatManage 三域统一。

**优点**：一次清掉全部重复。
**缺点**：范围溢出"聊天图表"需求，动到 llm 域回归面大，违背 YAGNI。**不建议本期做**，其中"chatManage 复用"与"useEChartsResize hook"可拆成后续独立小任务。

### 结论建议

**选 B**。A 是"能用但很快又要拆"，C 是"顺手把别人家也装修了"。B 恰好覆盖你的诉求（独立图表文件、前后端一致），且为类型扩展付一次性成本。

## 4. 方案二：图表类型扩展（加什么、怎么加）

按财务问答场景真实价值 + 实现成本分梯队。当前协议 `{type, title?, columns, rows}` 二维表的表达力是分界线：

### 第一梯队 — 本期建议全做（协议零改动或仅加可选字段）

| 类型 | 场景 | 协议影响 | 实现成本 |
|------|------|----------|----------|
| `scatter` 散点 | 相关性（如各公司 ARR vs 增长率） | 约定 `columns=["<点标签>","<x>","<y>"]`，行 = [label, x, y]；单系列 | 低 |
| `area` 面积 | 趋势（line 的填充变体） | 零（新 type 值） | 极低 |
| `stacked_bar` 堆叠柱 | 构成对比（OpEx 构成、收入构成） | 零 | 极低 |
| `horizontal_bar` 条形 | 排名 + 长类目名（公司名列表） | 零 | 极低 |
| `donut` 环形 | 占比（pie 变体） | 零 | 极低 |
| `combo` 柱线双轴 | **财务经典**：收入柱 + 增长率线；解决现提示词"量纲差异大只能分图"的痛点 | 加可选字段（见 §4.1） | 中 |

### 第二梯队 — 下期可选

- `waterfall` 瀑布图：现金流桥/利润桥，财务价值高；ECharts 需堆叠柱模拟（透明垫底系列），渲染层成本中等，协议可用单系列二维表表达。

### 不做（YAGNI）

- `heatmap`（需矩阵语义，协议大改）、`gauge`（单值，一句话能说清）、`funnel`、K 线。

### 4.1 combo 协议扩展（建议格式，待定）

向后兼容的可选字段，仅 `combo` 类型读取：

```jsonc
{
  "type": "combo",
  "columns": ["Month", "Revenue", "Growth %"],
  "rows": [["Jan", 100, 0.12], ["Feb", 120, 0.20]],
  "seriesTypes": ["bar", "line"],     // 对应 columns[1..]，缺省全 bar
  "rightAxis": ["Growth %"]           // 放右 Y 轴的系列名，缺省无
}
```

### 4.2 LLM 选型风险与缓解

类型越多，提示词越长、LLM 选错越多。缓解：

- 提示词按「场景 → 类型」一句话决策规则（趋势→line/area、对比→bar、构成→stacked_bar、排名→horizontal_bar、占比→pie/donut、相关→scatter、多维评分→radar、量纲混合→combo），由 `prompt_section.py` 随枚举生成。
- 前端类型切换器兜底——但注意：**切换器需按数据形状分组**。现在 4 类共用同一份二维表可任意互切；`scatter`（[label,x,y] 形状）与 `combo`（带 seriesTypes）加入后不能与 categorical 组互切。registry 里每类型标 `shape: 'categorical' | 'xy'`，切换器只列同组类型。

## 5. 配套修缮（随方案 B 一并做，成本低）

1. **后端 pydantic 校验**：`fence_parser` 解析出的 dict 过 `ChartSpec.model_validate`，失败降级为文本段（沿用现降级语义，绝不丢内容）。
2. **提示词图表段单点**：`prompt_section.py` 一份常量，tool/sql 两轨 import（消除现在的整段复制）。
3. **fence 解析规则对齐**：前端 `parseChartFences` 的 regex 与后端 `_OPEN`/`_CLOSE` 严格语义统一（以后端为准）。
4. **契约文档更新**：更新 `2026-06-10-chat-chart-design.md` 的类型清单与 §4.1 协议（或在本文件定稿后取代之）。

## 6. 明确不做（本期）

- chatManage 复用 ChatChart、`useEChartsResize` 抽 hook（拆为后续独立小任务）
- 图表交互（下钻、导出）、图表编辑/重生成
- 换图表协议为"LLM 直出 ECharts option"（灵活但无法校验、与渲染库耦合、注入面大，明确否决）
- DB schema 改动（图表仍以 fence 原文落库，历史重现路径不变）

## 7. 待你决策的点

1. **代码组织**：A（最小收敛）/ B（图表子模块+注册表，推荐）/ C（全局图表库）？
2. **类型范围**：第一梯队 6 种全做？还是先做点名的 `scatter` + 免费的变体（area/stacked/horizontal/donut），`combo` 与 `waterfall` 放下期？
3. **combo 协议**（若做）：§4.1 的 `seriesTypes` + `rightAxis` 格式是否认可？
4. **前端模块落位**：`src/pages/ai/chat/charts/`（就近）还是 `src/pages/ai/_shared/charts/`（为 chatManage 复用预留）？——推荐前者，复用等真做 chatManage 时再提升。

选定后我按 writing-plans 出前后端实现计划。
