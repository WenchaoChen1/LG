# 图表显示样式预设（数据特征驱动）— 方案

> 关联文档: [数据格式设计](./2026-07-04-chart-data-format-design.md) · [图表契约](./2026-06-10-chat-chart-design.md)
> 状态: 已实施（2026-07-04）
> 提出（用户原话大意）: 参考 ECharts 示例库——折线图有单条/多条之分，显示样式也有区别；仔细分析需求与 ECharts 后出方案处理。

## 1. 需求分析

ECharts 示例库同一类型下的样式差异，本质是**按数据特征选择的显示预设**：

| 示例库现象 | 数据特征 | 样式差异 |
|-----------|----------|----------|
| Basic Line vs Smoothed/Area Line | 单序列 | 平滑曲线 + 渐变面积（视觉重点是"这一条的走势"） |
| Stacked/Multiple Line | 多序列 | 普通直折线 + 图例 + hover 聚焦单线（视觉重点是"序列间对比"，平滑会互相误导交点） |
| 大数据量折线 | 点数多 | 隐藏数据点标记（symbol），只画线 |
| Bar with rounded corner | 柱状 | 柱顶圆角（本仓 chatManage 已有 `borderRadius [3,3,0,0]` 先例） |
| 类目很多的轴 | 行数多 | 轴标签倾斜避免重叠 |

我们目前的问题：11 个 builder 对任何数据都输出同一份"素"样式——单序列折线和八序列折线长得一样，24 个月的 x 轴标签挤成一团。

**定位**：这是纯前端显示层增强。**协议零改动、后端零改动、LLM 零感知**——样式由前端按数据特征确定性推导（与 format/suits 同属"数据驱动"思想的第三层：format 决定能画哪些类型 → suits 决定组内哪些适合 → traits 决定这一类型怎么画好看）。

## 2. 样式预设规则（确定性，全部可单测）

数据特征就两个维度：`seriesCount = columns.length - 1`、`rowCount = rows.length`。

| 规则 | 适用 builder | 条件 | 样式 |
|------|--------------|------|------|
| R1 单线平滑渐变 | line | seriesCount === 1 | `smooth: true` + 渐变面积（主色 22% → 4% 透明度纵向线性渐变，声明式 gradient 对象、不 import echarts 运行时） |
| R2 单区渐变 | area | seriesCount === 1 | 同 R1 的渐变面积（多序列保持现有 18% 平涂，避免叠加渐变浑浊） |
| R3 密点隐藏标记 | line / area | rowCount > 20 | `showSymbol: false`（悬停仍出 tooltip） |
| R4 多线 hover 聚焦 | line / area / stacked_bar | seriesCount >= 3 | `emphasis: { focus: 'series' }`（hover 高亮该序列、淡化其余） |
| R5 柱顶圆角 | bar / combo 的 bar 系列 | 恒定 | `borderRadius: [3, 3, 0, 0]`（对齐 chatManage 先例）；horizontal_bar 为 `[0, 3, 3, 0]`；**stacked_bar 不加**（分段圆角难看） |
| R6 长轴标签倾斜 | 全部 categorical 轴（shared） | rowCount > 12 | 类目轴 `axisLabel.rotate: 30`（horizontal_bar 的 y 轴类目不转） |

不做（明确排除，与 2026-07-02 spec 的"图表交互不做"一致）：dataZoom 滑条、markPoint/markLine 最值标注、toolbox、动画定制——聊天气泡里的图是"阅读物"不是"分析工作台"，交互密度点到为止；将来要做也是显示层独立小任务。

## 3. 实施落点（仅前端 CIOaas-web）

- `charts/shared.ts`：`categoricalOption` 增加 rowCount > 12 时类目轴 rotate 30（horizontal 分支不转）；新增导出小工具 `seriesCountOf(spec)`（columns.length - 1 的语义化封装，R1/R2/R4 共用）与渐变面积常量工厂 `areaGradient(color)`。
- `line.ts`：按 R1/R3/R4 组装 series。
- `area.ts`：按 R2/R3/R4。
- `bar.ts` / `horizontalBar.ts` / `combo.ts`：按 R5（combo 只给 bar 画法的系列加圆角）。
- `stackedBar.ts`：按 R4。
- 测试 `registry.test.ts`（或拆 builder 专测）：每条规则两侧断言（命中/不命中），如单序列 line 有 smooth+areaStyle、双序列没有；21 行 showSymbol false、20 行不隐藏；13 行 rotate 30、12 行不转。

## 4. 与 ECharts 示例库其余"数据格式"的关系

示例库其余大类已在 [数据格式设计 §5](./2026-07-04-chart-data-format-design.md) 登记为 format 扩展位（bubble / boxplot / candlestick / heatmap 等），加法恒定；本方案不新增类型，只让已有 11 类"按数据长相把自己画好看"。
