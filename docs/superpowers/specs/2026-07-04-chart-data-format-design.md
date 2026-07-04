# 图表数据格式（format）驱动设计 — 想法评估与方案

> 关联文档: [图表契约](./2026-06-10-chat-chart-design.md) · [图表优化方案](./2026-07-02-chatbot-chart-optimization-design.md) · [实现计划](../plans/2026-07-03-chatbot-chart-optimization.md)
> 状态: 已实施（2026-07-04）
> 提出（用户原话大意）: 图表应按返回的数据格式决定能显示哪些类型——有的格式同时支持柱状/折线，有的只支持瀑布等特定图；参考 ECharts 官方示例库的类型划分。

## 1. 想法评估：成立，架构已有雏形，两处需要明确

**结论：想法没有问题**，而且方向正确——它把"什么数据能画什么图"从启发式判断升级为**声明式契约**。现架构在 2026-07-03 的注册表设计里已经埋了雏形：`registry.ts` 的 `shape: 'categorical' | 'xy'` 就是"数据格式"概念的两格式特例（categorical 二维表组内 9 类互切、scatter 独占 xy 组不与人互切）。本方案把它升级为一等公民并扩展第三种格式。

两处需要明确（对原始想法的修正/澄清）：

1. **LLM 不需要单独输出"格式"字段**。每个图表类型唯一归属一个格式（type → format 是查表关系），协议里不加 `format` 字段、提示词不加选择负担——LLM 仍然只选 `type`。格式概念的价值体现在三处：**校验**（每格式一套列语义/schema）、**切换器**（只在同格式内互切）、**扩展**（新格式=新数据结构，不污染既有二维表协议）。
2. **"凹凸图"按瀑布图（waterfall）落地**。ECharts 示例库没有"凹凸"分类；按财务场景（现金流桥、利润桥：期初 → 各项增减起伏 → 期末）最合理的映射是瀑布/桥图。若实际指盒须图（boxplot）或 K 线（candlestick），本设计同样容纳——各自是一个新 format + 一套 schema，扩展位见 §5。

## 2. 格式定义（3 个 format、11 个 type）

| format | 数据语义 | 列约定 | 支持的 type（组内可互切） |
|--------|----------|--------|--------------------------|
| `series` | 分类 × 多序列二维表 | `columns[0]`=分类轴，`columns[1..]`=序列 | bar / line / area / stacked_bar / horizontal_bar / combo，及 suits 约束下的 pie / donut / radar |
| `points` | 带标签的 xy 数值点 | `columns` 恰 3 列 `[点标签, x, y]` | scatter |
| `flow` | 有序增减桥（**新增**） | `columns` 恰 2 列 `[环节, 增减值]`，行序即桥序 | waterfall（**新增**） |

- format 内互切安全（同一份数据换画法）；跨 format 永不互切。suits 判定继续存在于 format 之内（如 series 里多序列禁 pie）。
- 历史消息零影响：老 fence 只有 type，format 由 type 推导。

## 3. waterfall 协议与渲染

```jsonc
{
  "type": "waterfall",
  "title": "Cash Bridge FY25",
  "columns": ["Item", "Change"],
  "rows": [
    ["Opening Cash", 120],
    ["Collections", 45],
    ["OpEx", -60],
    ["Closing Cash", 105]
  ],
  "totals": ["Opening Cash", "Closing Cash"]   // 可选：绝对锚点行（期初/期末/小计），其余行是增减值
}
```

- **校验（后端 pydantic，flow 分支）**：恰 2 列；行 ≥ 2；数值格**必填数字**（瀑布桥断一格就没法画，null 直接降级文本）；`totals` 若给出必须是行标签子集（否则降级）。
- **渲染（前端 builder）**：ECharts 经典配方——透明垫底 stack + 实际柱；增（正数）用 `chart-2` 绿、减（负数）用 `chart-4` 红、totals 锚点用 `chart-1` 蓝从 0 画绝对值。tooltip 增减行显示带符号增减，锚点行显示绝对值。
- **提示词场景规则**（并入 chart_prompt 类型清单，自动生成）：增减构成的桥/瀑布（现金流桥、利润桥、headcount 变动桥）→ waterfall；正数=增、负数=减；期初/期末/小计放 `totals`。

## 4. 改动面

**后端（CIOaas-python）**
- `ai/chatbotgraph/chart/spec.py`：`CHART_TYPES` + `waterfall`；新增 `ChartFormat` 与 `TYPE_FORMAT` 映射（契约单点扩容）；`ChartSpec` 增可选 `totals`；model_validator 按 format 分支校验（points 恰 3 列规则收编进来）。
- `prompts/chatbot/chart_prompt.py`：类型行自动带上 waterfall；场景规则加一行。
- 测试：spec（flow 校验各分支）+ parser（waterfall fence 透传/降级）+ prompt（含 waterfall）。

**前端（CIOaas-web）**
- `chatDto.ts`：`ChartType` + `'waterfall'`；`ChartSpec` + `totals?: string[]`。
- `charts/registry.ts`：`ChartShape('categorical'|'xy')` 更名 `ChartFormat('series'|'points'|'flow')`（与后端词汇对齐）；注册 waterfall。
- `charts/waterfall.ts`：新 builder（§3 配方）。
- 测试：registry（3 格式分组/waterfall 注册）+ waterfall builder（垫底计算/颜色/totals 锚点/tooltip）。

**文档**：`2026-06-10-chat-chart-design.md` §4.1 补 flow 格式与 waterfall 约定。

## 5. 扩展位（格式机制的预留能力）

> 2026-07-04 更新：bubble（points 4 列）、boxplot（distribution 新格式）、heatmap（**并入 series 组**，未新建 matrix——热力矩阵与二维表同构）、gauge（single 新格式）已随类型扩展落地，现 **5 格式 / 18 类型**，见 [2026-07-04-chart-types-expansion-design.md](./2026-07-04-chart-types-expansion-design.md)。剩余扩展位：`ohlc`→candlestick（当前无行情数据）等。

新格式的加法恒定：spec.py 加 format+类型+校验分支 → chart_prompt 场景规则一行 → 前端一个 builder + registry 一行注册。
