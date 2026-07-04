# 图表总入口与显示样式框架 — 设计

> 关联文档: [类型扩展](./2026-07-04-chart-types-expansion-design.md) · [样式预设](./2026-07-04-chart-style-presets-design.md) · [图表契约](./2026-06-10-chat-chart-design.md)
> 状态: 已实施（2026-07-04）
> 需求（用户原话大意）: ①前后端图表代码各自隔离、有总入口，方便其他功能/项目复用；②前端下拉只显示该数据支持的类型，类型下可选显示样式（都有默认），AI 返回建议类型则用、不返回用默认；③多条/多维数据的入口框架搭好，每种能力一个代表实现即可，按需求增加。

## 1. 总入口隔离（复用边界）

| 端 | 总入口 | 约定 |
|----|--------|------|
| 后端 | `ai/chatbotgraph/chart/`（包），`__init__.py` 即唯一对外 API | 包内**全部纯逻辑（无 IO）**经入口 import（SSE 修复回路 `repair.py` 已于 2026-07-04 删除，原「深路径例外」不复存在，见 [修复回路删除](./2026-07-04-chart-repair-removal-design.md)）。其他功能/项目复用 = `from ai.chatbotgraph.chart import ChartSpec, parse_chart_spec, ChartFenceStreamParser` |
| 前端 | `chat/utils/charts/index.ts`（新增） | re-export registry 全部公共 API 与类型；**外部（组件/其他页面/未来项目）只从 `charts` 目录根 import**，builders 是包内实现细节不导出。既有深路径引用收口 |

## 2. 类型选择：AI 建议优先，默认兜底（协议变化）

`type` 从必填改为**建议性可选**；新增可选 `style`（显示样式建议，暂不进提示词、框架预留）：

```jsonc
{ "type": "bar",          // 可选：AI 的建议类型；省略时前端按数据特征选默认
  "style": "flat",        // 可选：AI 的建议显示样式；省略/未注册时用该类型默认样式
  "columns": [...], "rows": [...] }
```

- **后端校验**：有 type → 按其 format 规则校验（现状）；**缺 type → 按 series 基础规则兜底校验**（columns ≥2、rows ≥1，二维表是最宽形状）；`style` 透传不校验枚举（样式表是前端资产）。
- **前端选型**：`resolveType(spec)` —— spec.type 有效则用之；否则 `defaultTypeFor(spec)`（单序列 → line，多序列 → bar；兜底 bar）。
- 提示词只加半句（type 可省略、省略时由前端自动选型），不宣传 style（AI 不返回即默认，符合需求）。

## 3. 切换器：只显示支持的类型（行为变化）

下拉从"全组列出 + 不适合置灰"改为**只列 suitable 类型**（`allowed`）——用户明确要求"不支持就不要显示"。OptGroup 分组保留（组内成员随数据动态增减）；组内只剩 1 个可选类型时切换器仍显示（用户需要看到"当前是什么图"并可选样式）——仅当既无可切类型又无可选样式时整个工具条隐藏。

## 4. 显示样式框架（每类型多样式、有默认）

`ChartTypeDef` 增可选 `styles?: Record<string, (spec) => EChartsOption>`：

- `build(spec)` 即**默认样式**（现状零改动）；`styles` 里每项是一个命名变体工厂。
- 统一组装入口 `buildChart(spec, type, style?)`：style 命中注册表用变体，未命中/未注册回退默认。
- UI：类型切换器旁增第二个小 Select（Style），仅当该类型注册了 ≥1 个变体时显示（选项 = Default + 变体名）；初始值 = `spec.style`（若已注册）否则 Default。
- **代表实现（框架验证，各一个，按需求再加）**：`line` 注册 `plain`（无平滑无渐变的朴素折线，对照默认的单序列平滑渐变）；`bar` 注册 `flat`（无圆角平顶柱）。

## 5. 多维数据入口现状（无需新增）

多序列（bar/line/stacked_*）、双轴混合（combo）、三维点（bubble）、二维交叉矩阵（heatmap）、分布（boxplot）、单值（gauge）——各维度能力均已有一个代表类型；后续按真实需求经"校验分支 + 提示词一行 + builder 注册"恒定三步增加。

## 6. 兼容性

- 历史消息全部带 type（旧协议必填）→ 行为不变；新协议只是放宽。
- `chatEvents.isValidChartSpec` 与 `parseChartFences` 同步放宽（type 可缺省，结构校验不变）。
- 后端 validate_chart 随 `parse_chart_spec` 单点自动继承新规则（修复回路已于 2026-07-04 删除，见 [修复回路删除](./2026-07-04-chart-repair-removal-design.md)）。
