# 前端渲染前格式校验 + 「格式有误」占位符 — 方案

> 关联文档: [修复回路删除](./2026-07-04-chart-repair-removal-design.md)（§8 已知口子，本方案将其关闭） · [图表契约](./2026-06-10-chat-chart-design.md) · [规则走 tool](./2026-07-04-chart-guide-via-tool-design.md)
> 状态: 已实施（2026-07-04，CIOaas-web `cc35755c`，charts 75 tests passed、tsc 零新增）
> 提出（用户原话大意）: 前端应校验返回的数据结构是不是自己能渲染的、格式有没有问题；有问题就把图表换成「数据格式有问题」占位符，可看详情，详情按钮弱化。

## 1. 解决什么问题

[修复回路删除方案 §8](./2026-07-04-chart-repair-removal-design.md) 记录的前后端宽严差：后端按 format 语义校验（gauge 0-100、boxplot 五数单调、waterfall 不许 null…），前端历史路径 `parseChartFences` 只查最小结构——后端流式期拒绝并降级为文本的坏 fence，落库原文在**刷新/重进会话后会被前端画成错误的图**（如 150 的 gauge 照画超表）。

本方案用「校验失败 → 占位符 + 弱化详情」取代「照画错图」：信息不丢（详情可看原始数据与错误原因）、也不误导（不呈现语义违规的图）。**取代 §8 的"接受现状"决策**（实施时同步更新该节）。

## 2. 校验器：镜像后端规则，单点同步契约

新增 `chat/utils/charts/validate.ts`（经 `index.ts` 总入口导出）：

```ts
/** 渲染前格式校验：规则镜像后端 spec.py `_check_format`（不更严、不更松）。
 *  ⚠️ 同步契约：后端改 `_check_format` 必须同步本文件（对照 spec.py 头注释）。 */
export function validateChartSpec(spec: ChartSpec): string[]   // 错误列表，空数组 = 通过
```

规则（按 `resolveType(spec)` 的 format 分支，与后端逐条对齐）：

| format | 校验 |
|--------|------|
| 基础（全部） | `columns` 数组长度 ≥2、`rows` 非空数组且每行是数组 |
| series | 不加格值校验（与后端一致——`null` 是合法的 NA 语义） |
| points | scatter 恰 3 列 / bubble 恰 4 列；数值格是数字 |
| flow (waterfall) | 恰 2 列、行 ≥2、每行恰 2 格、`row[1]` 必须数字（null 不合法）、`totals` ⊆ 行标签 |
| distribution (boxplot) | 6 或 7 列、行长 == 列数、格 1..5 数字且单调不减、第 7 格数字或 null |
| single (gauge) | 恰 2 列、恰 1 行、`row[1]` 是 0-100 数字 |

**刻意不做**：不比后端多校验一条（如 series 行长一致性后端没拦，前端也不拦）——否则历史合法图会被误伤，且两份规则的对齐语义从「镜像」漂移成「各自为政」。

## 3. 占位符 UI（ChatChart 内，唯一渲染收口点）

`ChatChart` 在 `buildChart` 之前先 `validateChartSpec(spec)`：

- **通过** → 现状渲染（切换器/样式/图）。
- **失败** → 占位卡片（复用现 `.fallback` 样式基调）：
  - 主文案：`图表数据格式有误`（与现有「图表渲染失败」文案风格一致）
  - 右侧/下方一个**弱化**的详情开关：`Button type="link" size="small"`（次要色、不加图标），文案 `详情`
  - 点开在卡片内展开（不弹 Modal）：错误列表（validateChartSpec 返回值逐条）+ 原始 spec 的 JSON 代码块（`<pre>`，等宽、可滚动）
- **builder 运行时异常**（现 try/catch「图表渲染失败」）统一收编进同一占位组件（错误内容 = 异常消息），一个组件两种入口，不再两套降级 UI。

放在 ChatChart 意味着**流式、历史、fork 预览三条路径全覆盖**：流式 `event: chart` 本已后端校验通过、validate 应恒通过（留着是防前后端版本漂移的双保险，成本为零）；历史路径是本方案的主战场。chatManage 管理页走 MarkdownView 不画图，不受影响。

## 4. 改动面（全在 CIOaas-web）

| 位置 | 改动 |
|------|------|
| `chat/utils/charts/validate.ts`（新） | `validateChartSpec`，纯函数 |
| `chat/utils/charts/index.ts` | 导出 validateChartSpec |
| `chat/components/ChatChart.tsx` | 渲染前校验 + 占位组件（含详情展开），builder 异常并入 |
| `chat/components/ChatChart.less` | 占位卡片/弱化详情按钮/展开区样式 |
| 测试 | `validate.test.ts` 每格式命中/不命中双侧断言（镜像后端 `test_spec.py` 用例表：scatter 少列、waterfall null、boxplot 错位、gauge 越界…）；ChatChart 测试补占位/详情展开/异常并入三例 |
| 后端 `spec.py` | 仅头注释补一行同步契约（前端 validate.ts 对照），无逻辑改动 |
| 文档 | 本文件 + 修复回路删除方案 §8 更新（口子由本方案关闭） |

## 5. 与既有分层的关系

前端图表数据驱动分层从三层变四层：**format（能画什么）→ validate（这份数据合不合法，新增）→ suits（组内哪些适合）→ traits（怎么画好看）**。validate 与 suits 职责不同：validate 拦「画出来是错的」（语义违规→占位符），suits 过滤「画出来能看但不合适」（切换器不列）。
