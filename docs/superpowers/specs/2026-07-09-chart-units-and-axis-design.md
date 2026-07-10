# 图表单位（units）显式化 + 按通道容量分轴 — 设计

> 关联文档：[chart-backend-role-redesign](./2026-07-04-chart-backend-role-redesign.md)、[chart-data-format-design](./2026-07-04-chart-data-format-design.md)、[chart-types-expansion-design](./2026-07-04-chart-types-expansion-design.md)、[chart-end-to-end-flow](./2026-07-04-chart-end-to-end-flow.md)
> 状态：设计确认中（2026-07-09）
> 缘起：用户提出两条图表准则 —— ① 每个数据要有单位；② 不同单位不能放到同一根维度坐标。

---

## 1. 背景与问题

现有实现里「单位」是**软约束**，不够硬：

- **单位只隐含在列名里**（`"Revenue ($K)"`、`"Growth (%)"`），没有独立字段、无强制。
- **前端完全不显示单位**：坐标轴、tooltip 只做千分位（`toLocaleString('en-US')`），没有 `$ / %`（仅 treemap 硬编码 `%`、gauge 裸数字）。
- **分轴判断靠名字启发式**：`chart_validate_tool.py` 的 `_looks_ratio_like`（匹配 `%/percent/margin/growth/rate/...`）猜某列是不是比率，且**只在设了 `rightAxis` 时才触发**。
- **缺口**：若 LLM 直接画普通 `bar`，列里混了 `Revenue ($)` 与 `Growth (%)` 共用一根 Y 轴 —— 现在**拦不住**（双轴规则只管 combo）。

2026-07-09 用户点名的相关 bug（已在 `chart_validate_tool.py` 注释）：同单位多序列即使量级悬殊也应共轴，双轴会误导读数。本设计在此基础上把单位升级为一等字段，用它确定性地驱动分轴与显示，**彻底取代名字启发式**。

---

## 2. 目标与非目标

**目标**
- 单位成为显式数据字段，每个度量序列必须声明单位（落实准则①）。
- 分轴/图型选择由单位确定性驱动：一根坐标只放一种单位；不同单位放不同通道；单位种类数不得超过图型通道容量（落实准则②）。
- 前端按单位格式化数值显示（`$ / %` 等），补上「读者看不到单位」的缺口。
- 删除 `_looks_ratio_like` 名字启发式，改读显式单位。

**非目标（YAGNI，v1 不做）**
- 不引入单独的显示 label（`$K / $M` 刻度文本）字段 —— 轴标题/图例继续用列名（列名本含单位文本），`kind` 只负责分轴判等与数值格式化。将来要精确刻度归一再加。
- 不做数据库迁移、不回填历史图表。
- 不处理多币种细分（`USD` vs `EUR` 都归 `currency` 一种 kind，见 §5 已知简化）。

---

## 3. 数据模型：前后端一致的数据类型 + 按类型契约 + 显式单位

### 3.0 数据类型（`data_type`）：前后端一致的 6 值分类

wire 层所有图表是同一种结构（一张二维表 `{columns, rows(, units)}`，`data_type` 不序列化、由 chart `type` 派生），但按 **columns/rows 列契约 + 轴语义** 分成 6 类「数据类型」——每个数据类型固定支持一组图表类型，且**前后端逐值一致**（前端切换器"同组互切"依赖此分组、砍不掉，故后端与之对齐；用户 2026-07-09 定。combo 独立成类：它是双轴图、capacity=2，与 standard 单轴图不可互切，2026-07-10 拆出）：

```
class ChartFormat(StrEnum): STANDARD / COMBO / POINTS / FLOW / DISTRIBUTION / SINGLE   # 值=standard/…；standard 默认（原 series）；键处点用 ChartFormat.STANDARD、不写裸串
```

| 数据类型 | 固定支持的图表类型 | 列契约 |
|---|---|---|
| `standard`（默认） | bar, line, area, stacked_bar, horizontal_bar, pie, donut, radar, stacked_area, step_line, heatmap, treemap（12 个，单轴） | `[分类, 序列1, 序列2, …]` |
| `combo` | combo（双轴：不同单位分左右 Y） | `[分类, 序列1, 序列2, …]` + `seriesTypes` |
| `points` | scatter, bubble | scatter `[点标签,x,y]`(3列) / bubble `[点标签,x,y,size]`(4列) |
| `flow` | waterfall | `[环节, 增减值]`(2列) |
| `distribution` | boxplot | `[组标签, low,q1,median,q3,high(,you?)]`(6/7列) |
| `single` | gauge | `[标签, 值]`(2列1行, 0-100) |

- **后端**（`spec.py`）：两个 `StrEnum` —— `ChartFormat`（数据类型 6 值）+ `ChartType`（图表类型 18 值，与前端 `CHART_TYPE` 逐值一致）。单一事实源 `CHART_DATA_TYPES: dict[ChartFormat, DataTypeDef]`（**6 个数据类型 = 6 个对象**，每个 = `DataTypeDef{when 用途, shape 列摆法+该类型约束, example, chart_types:{ChartType:capacity}}` —— `chart_types` 即「数据类型 ↔ 图表类型」的关联；字面量里不写派生代码）；派生 `CHART_TYPES` / `TYPE_CAPACITY` / `TYPE_DATATYPE`（type→数据类型）/ `DATATYPE_TYPES`（数据类型→固定图表类型集）。`validate_chart` 按 `TYPE_DATATYPE[t]` 选列契约分支（取代原硬编码 type 名集合）。
- **前端**（`registry.ts`）：`CHART_FORMAT`(6 值) + 每类型 `format` 字段（值与后端逐字一致）；`compatibleTypes` 据此做切换器分组。
- **同步**：两端各存一份（跨语言无法共享），改一侧须同步另一侧——数据类型枚举值、type→数据类型映射、每类型 capacity 三者对齐。
- 注：`shape`/`example` 仍**按 chart 类型**（同一数据类型内 scatter/bubble 列数不同），未拆到数据类型层。

### 3.1 单位表示法：kind 枚举 + 定位数组

`ChartSpec` 新增一个**与 `columns` 定位对齐**的 `units` 数组。分类/点标签列填 `null`，每个度量列填一个 `kind`：

```jsonc
{
  "type": "combo",
  "columns": ["Quarter", "Revenue ($K)", "Growth (%)"],
  "units":   [null,      "currency",     "percent"],   // ← 新增，与 columns 逐位对齐
  "rows": [["Q1", 1200, 12], ["Q2", 1450, 20]],
  "seriesTypes": ["bar", "line"]
  // rightAxis 不再由 LLM 指定 —— 由 units 推导（见 §4）
}
```

**kind 枚举**（六种，覆盖财务域）：

| kind | 含义 | 数值格式化（前端） |
|------|------|------|
| `currency` | 货币金额（$、¥…） | `$` 前缀 + 千分位 |
| `percent` | 百分比 | 值 + `%` |
| `ratio` | 无量纲比值/倍数（如 3.5x EV/EBITDA） | 值 + `x` |
| `count` | 计数（人数、笔数） | 千分位 |
| `duration` | 时长（天/月，如 DSO） | 千分位（v1；单位文本靠列名） |
| `other` | 其他/自定义 | 千分位（默认） |

**单位粒度**：单位挂在**数据标签/序列**上 —— 一个度量列（= 一个数据标签）= 一个单位。若一组序列共享同一单位，则各自在 `units` 对应位重复填同一 kind；**不设「整图一个单位」的简写**（避免两套声明方式，YAGNI）。

**各类型的对齐约定（按列契约分组，即原 5 个 format 的形状）**：
- `standard`（bar/line/area/pie/donut/radar/heatmap/treemap/stacked_*/step_line/horizontal_bar）与 `combo`：`units[0] = null`（分类列），`units[1..]` 每个序列一个 kind。
- `points`（scatter/bubble）：`units[0] = null`（点标签列），其余对齐 `x, y(, size)` 各一个 kind。
- `flow`（waterfall）：`[null, kind]`（环节列 null，增减值列一个 kind）。
- `distribution`（boxplot）：`[null, kind, kind, kind, kind, kind(, kind?)]` —— 5（或含 you 的 6）个统计列属同一度量，**填同一个 kind**（冗余但统一，校验最简单）。
- `single`（gauge）：`[null, "percent"]`（值恒为 0–100，kind 固定 `percent`）。

---

## 4. 核心规则：按通道容量分轴（取代启发式）

> **每条坐标/通道只放一种单位；数据里的不同单位种类数 N，必须 ≤ 所选图型的通道容量。**

「通道」= 图型里能独立承载一种单位的坐标/视觉维度。各图型容量：

| 通道容量 | 图型 | 能承载的单位种类数 |
|---|---|---|
| **1** | bar / line / area / stacked_bar / stacked_area / horizontal_bar / step_line / pie / donut / treemap / radar / heatmap / waterfall / boxplot / gauge | 1 |
| **2** | **combo**（左 Y + 右 Y）、**scatter**（X + Y） | 2 |
| **3** | **bubble**（X + Y + 气泡大小） | 3 |

这些通道是**不同的坐标/维度**，各承载一种单位 —— 所以 bubble 显示 3 种单位**不违反准则②**（没有把不同单位塞进同一根坐标）。

**判定（按度量序列 kind 去重后的种类数 N）：**

| N | 处理 |
|---|---|
| 0 或 1 | 任意图型。**同 kind 多序列即使量级悬殊也共用同一条 Y 轴**（贴合 2026-07-09 bug 修复）。 |
| 2 | 只允许 `combo`（第 1 种 kind → 左轴，第 2 种 → 右轴，右轴序列由 units 自动推导）或 `scatter`（X/Y 各一种）。若选了容量 1 的图型（如普通 bar 混了 `$` 和 `%`）→ **validate 拒绝**，提示改 combo 或拆图。 |
| 3 | **只有 bubble**，且数据须是点状 `[实体, x, y, size]`。若是「类别×序列」等非点状的 3 单位数据（如 `月份 × [营收$, 人数count, 满意度%]`）→ 拆图。 |
| ≥4 | 无诚实图型（容量最大的 bubble 也只有 3）→ **validate 拒绝**，提示拆成多张图（每图 ≤ 该图型容量种单位）。 |

**通道容量作为单一事实源**：容量在 §3.0 `CHART_DATA_TYPES` 各数据类型的 `chart_types:{图表类型:capacity}` 里（Python 一份；Web `registry.ts` 各类型加 `capacity` 一份，跨语言无法共享、随现有类型列表一起手工同步，与项目现状一致）。取值：standard 系均为 1、combo=2（独立数据类型）、scatter=2、bubble=3、其余均为 1。

**seriesTypes 与分轴解耦**：`units` 管分轴，`seriesTypes`（bar/line 画法）只管画法。combo 右轴序列不再由 LLM 填 `rightAxis`，而是**从 units 推导**（第 2 种 kind 的序列落右轴）。`rightAxis` 字段保留为兼容/可选，若 LLM 仍给且与 units 推导冲突，以 units 为准。

---

## 5. 分端改动

### 5.1 数据结构（single source，双端对齐）
- **Python** `source/ai/agent/chatbot_graph/chart/spec.py`：
  - `ChartSpec` 新增 `units: Optional[list[Optional[str]]]`（wire 键 `units`）+ `UnitKind` 常量。
  - `ChartFormat` 改为前后端一致的 6 值数据类型 **`StrEnum`**（§3.0，键处点用 `ChartFormat.STANDARD`、不写裸串）+ `ChartType` 图表类型 18 值 StrEnum；`CHART_FORMATS`（format→定义）重构为 `CHART_DATA_TYPES`（**6 个数据类型对象**，数据类型→`DataTypeDef{when 用途, shape 列摆法+该类型约束, example, chart_types:{ChartType:capacity}}`）；派生 `CHART_TYPES` / `TYPE_CAPACITY` / `TYPE_DATATYPE` / `DATATYPE_TYPES`；`validate_chart` 按 `TYPE_DATATYPE[t]` 选列契约分支。
- **Web** `src/services/api/chat/chatDto.ts`：`ChartSpec` 新增 `units?: (UnitKind | null)[]`；新增 `UnitKind` 联合类型。`registry.ts` 各类型补 `capacity`。

### 5.2 校验（两层，沿用现有职责切分）
- **`spec.py` 结构底线**（`parse_chart_spec_verbose`）：`units` 可选；若给了，长度须 == `columns`，元素须是合法 `kind` 或 `null`。**老图无 `units` 照常解析**（graceful）。
- **`chart_validate_tool.py` 语义自查**（新图必须过，是单位「符合标准」的唯一强制点）：
  0. `type` 必填且须是某数据类型下的图表类型（缺 type → 失败；AI 从所选数据类型的图表里挑一个，2026-07-09）；
  1. 每个度量序列必须有非 null 的 `kind` → 落实准则①；
  2. 分类/label 列的 units 必须为 `null`；
  3. 每个 `kind` 必须是六种枚举之一（`currency/percent/ratio/count/duration/other`）；
  4. 按 §4 通道容量规则校验 kind 种类数与图型兼容性 → 落实准则②；
  5. **删除** `_looks_ratio_like`、`_RATIO_NAME_TOKENS` 及依赖它们的分支，改读 `units`。

- **校验闭环**（对齐用户要求「符合通过 / 不符合返回失败原因 → AI 自查处理」）：
  1. AI 在输出任何 ```chart 围栏前**必须先调用** `validate_chart`；
  2. 全部通过 → 返回 `{ok: true}` → AI 才输出围栏；
  3. 任一项不符 → 返回 `{ok: false, errors: [具体失败原因…]}`（沿用现有 `ChartValidateResult` 结构）→ AI 读原因、改 `units`/图型/列，**重新调用** `validate_chart`，直到 `ok: true`。

- **单位相关失败原因目录**（`errors` 里返回的具体文案，让 AI 自查有据可依）：

  | 情形 | 返回的失败原因（示例） |
  |------|------|
  | 度量列缺单位 | `序列 "Revenue" 缺单位：请在 units 对应位声明 kind（currency/percent/ratio/count/duration/other）` |
  | kind 非法 | `units[2] "dollars" 不是合法单位：只能是 currency/percent/ratio/count/duration/other` |
  | 分类列填了单位 | `分类列 "Quarter" 不应带单位：units 对应位请填 null` |
  | units 长度不符 | `units 长度（2）须与 columns（3）一致，每列逐位对齐` |
  | 超通道容量 | `图型 "bar" 只有 1 条数值轴，但检出 2 种单位（currency, percent）：改用 combo（2 种）或拆成多张图` |

### 5.3 提示词 `source/ai/prompts/chatbot/chart_prompt.py`（现 v1.11，随本次改动递增）
- 强制：每张图必须给 `units`，与 `columns` 对齐（度量列声明 kind、分类/标签列 null）。
- 选型规则改写：不再判断「名字像不像比率」，而是**数 kind 种类数 N** → 1 种任意图、2 种走 combo（自动分轴）/scatter、3 种走 bubble（点状数据）、≥4 种拆多张图。
- 自查流程（先调 `validate_chart` 再输出）保持不变。

### 5.4 前端渲染（Web，ECharts）
- **数值格式化按 kind**（`charts/shared.ts` 及各 builder 的 tooltip/axisLabel）：`currency`→`$`+千分位、`percent`→值+`%`、`ratio`→值+`x`、`count/duration/other`→千分位。
- **combo 左右轴分配从 `units` 推导**（`combo.ts`：第 2 种 kind 的序列 → 右轴），零线对齐逻辑 `alignedDualAxisBounds` 保留。
- **`resolveRenderType`（`ChatChart.tsx`）增加通道容量校验**：若 spec 的 kind 种类数 > 所选图型容量（如非 combo 却 2 种 kind、非 bubble 却 3 种）→ 返回 null → 走 `ChartFallback`，不画误导图。这是对老图/被编辑图的防御性兜底。
- **`registry.ts`**：为每种类型补 `capacity` 元数据（与 §4 表一致）。

### 5.5 向后兼容
- `units` 全程**可选**：DB 里已存的老 fence 无 units → 前端退回现状（千分位、不做 kind 格式化、不硬分轴校验），无需迁移、无需回填。
- 新图：`validate_chart` 强制 units。

### 已知简化
- 多币种（`USD` vs `EUR`）都归为 `currency` 一种 kind，会被判为同轴。v1 接受此简化；跨币种同图的正确性由数据/LLM 负责。

---

## 6. 验收标准（对齐两条准则）

- **准则①**：任一新图，每个度量序列都带非 null 的 `kind`，缺则 `validate_chart` 失败；前端按 kind 显示 `$ / %` 等，读者能看出单位。
- **准则②**：
  - 普通 bar 混 `$` 与 `%` → `validate_chart` 拒绝，提示改 combo 或拆图。
  - 同 kind 多序列（含量级悬殊，如 Revenue 与 Cash 都是 `currency`）→ 共用一条 Y 轴，不误拆双轴。
  - 2 种 kind → combo 自动左右分轴（右轴由 units 推导）。
  - bubble 的 x/y/size 三种单位 → 正常渲染，不被误杀。
  - ≥4 种 kind → 拒绝并提示拆图。

---

## 7. 待办衔接

设计确认后进入实现计划（writing-plans），拆分为 Python（spec/validate/prompt）与 Web（dto/render/registry）两条相对独立的任务线。
