# 图表类型扩展：11 → 18 类 / 3 → 5 格式 — 设计与决策记录

> 关联文档: [数据格式设计](./2026-07-04-chart-data-format-design.md) · [样式预设](./2026-07-04-chart-style-presets-design.md) · [图表契约](./2026-06-10-chat-chart-design.md)
> 状态: 已实施（2026-07-04）
> 决策来源: 用户拍板（第一/二档全做 + 第三档精选）+ Plan 代理对抗性设计验证 + 用户定位指正

## 1. 定位原则（用户指正，最高优先）

**图表层是纯展示契约：渲染 AI 回答中给出的数据，与工具层解耦。** AI 的数据来源不限于 LG 工具——用户在消息里粘贴的数据、上下文中的数据同样可能出图。因此：

- 图表类型的存在性**不按"当前工具返回什么"设门槛**（工具能力只影响某类型出现的频率，不影响它该不该存在）
- 图表层改动**不碰 `tools/v2` 工具层**
- 数据真实性由既有红线兜底：数字必须来自工具结果或用户给出的内容，没有真实数据不出图

## 2. 格式与类型总表（5 格式 / 18 类型）

| format | 数据语义 | 类型（组内可互切） | 数量 |
|--------|----------|--------------------|------|
| `series` | 分类 × 序列二维表 | bar、line、area、stacked_bar、horizontal_bar、pie、donut、radar、combo、**stacked_area、step_line、heatmap、treemap** | 13 |
| `points` | 带标签 xy 数值点 | scatter（恰 3 列）、**bubble**（恰 4 列 [标签,x,y,size]） | 2 |
| `flow` | 有序增减桥 | waterfall | 1 |
| `distribution`（新） | 分布五数概括 | **boxplot** | 1 |
| `single`（新） | 有界 0-100 单值 | **gauge** | 1 |

## 3. 新类型协议要点

- **bubble**：points 格式按类型分列数（scatter 恰 3 / bubble 恰 4）；前端 suits——bubble 需 4 列、scatter 3/4 均可（bubble→scatter 是合法降维切换，反向缺 size 列置灰）。
- **stacked_area / step_line / treemap**：series 免费变体，零协议改动；treemap 的 suits 同 pie（单序列 ≥2 行）。
- **heatmap**：放 series 组（热力矩阵与二维表同构，bar↔heatmap 互切正是核心场景：月×指标百分位矩阵换视图）；suits = 序列 ≥2 且行 ≥2；**同量纲约束写提示词行**（格式层只管形状）。
- **boxplot**（distribution）：row = `[组标签, low, q1, median, q3, high(, you?)]`，columns 恰 6 或 7 **按位置取义**（列名仅作展示，AI 有分位填分位、有极值填极值，协议不预设统计口径）；校验：格 1..5 数值且**单调不减**（拦"真数错位"的语义 tripwire）、you 不限范围（越界正是要暴露的信息）；前端 tooltip 用 columns[1..5] 的列名标注（不用 ECharts 默认 min/max 文案，避免统计口径误读）。同行场景下提示词引导优先用聚合分位（P10/P90 一类插值统计量，保密更稳）。
- **gauge**（single）：恰 2 列 `[标签, 值]`、恰 1 行、0<=值<=100（越界降级文本）——0-100 校验即量纲声明，堵住"$2.3M 单值切成仪表盘"的语义漏洞；配套提示词例外：「数据点很少→写正文」规则对单个 0-100 百分位/评分值放行 gauge（正文仍须点明数值）。

## 4. 提示词膨胀控制

免费变体**并入既有场景行**（step_line 并趋势行、stacked_area 并构成行、treemap 并占比行、bubble 并 scatter 行），新行仅 heatmap / gauge / boxplot 3 条；boxplot 行强措辞防错位（仅当手里有**现成的分布统计量**才用，绝不把时间序列/多指标数值当五数填）。`CHART_SECTION` 总行数预算 ~35 行，超限先合并再新增。

## 5. 切换器分组（series 组 13 成员）

registry 的 `ChartTypeDef` 增可选 `menuGroup`，ChatChart 派生 antd OptGroup（registry 仍是唯一事实源）：**Bars**(bar/horizontal_bar/stacked_bar) / **Trend**(line/step_line/area/stacked_area/combo) / **Proportion**(pie/donut/treemap) / **Other**(radar/heatmap)；`listHeight` 320；置灰禁用逻辑不变。points 组升至 2 成员、切换器首次在该组出现。

## 6. 第三档取舍记录

- **入选**：gauge（评分卡标志性类型，0-100 单值语义清晰）、treemap（构成占比的现代表达，一层即可、不需层级数据）。
- **排除**：funnel（数据结构虽同 pie 但 LG 无管道类业务语义）、sankey（LLM 构造 nodes/links 图结构出错率高）、candlestick（无行情数据）、map/calendar/graph/parallel/themeRiver（数据不具备或可读性差）、pictorialBar/effectScatter（装饰性与严肃商务风不符）。
- 排除不是永久否决：格式机制的加法恒定（spec 校验分支 + 提示词一行 + 前端 builder），真实需求出现时按此三步加。
