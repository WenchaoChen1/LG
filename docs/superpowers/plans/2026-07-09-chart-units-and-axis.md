# 图表单位显式化 + 按通道容量分轴 —— 实现计划

> ⚠️ **历史记录**：本计划按当时的中间结构写成并已执行完毕；此后结构又经数轮演进（`CHART_TYPE_DEFS`→`CHART_DATA_TYPES` 6 数据类型对象、`ChartFormat`/`ChartType` StrEnum、combo 独立数据类型、when 字段、type 必填等）。**最终事实以设计文档 [2026-07-09-chart-units-and-axis-design.md](../specs/2026-07-09-chart-units-and-axis-design.md) 与代码为准**，勿按本文代码块施工。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让图表把「单位」变成显式数据字段，`validate_chart` 强制每个度量序列声明单位、并按图型通道容量拦截"不同单位同轴"，前端按单位格式化显示。

**Architecture:** 单一事实源两端各一份（Python `spec.py` / Web `chatDto.ts`+`registry.ts`）。新增 `units` 定位数组（与 `columns` 对齐）+ `UnitKind` 枚举 + 每类型 `capacity`（通道容量）。后端 `validate_chart` 是唯一强制校验点（通过才出图、失败返回具体原因让 AI 自纠）；前端按 `kind` 格式化数值、combo 右轴由 `units` 推导、`resolveRenderType` 加容量兜底。同时把 `ChartFormat`（5 值）收敛为单值、列契约从「按 format」搬到「按 type」。

**Tech Stack:** Python 3.12 / Pydantic / LangChain `@tool`；React 16 / TypeScript / ECharts 5。

**设计文档：** [2026-07-09-chart-units-and-axis-design.md](../specs/2026-07-09-chart-units-and-axis-design.md)

## Global Constraints

- Python：v2 工具包**禁写** `from __future__ import annotations`；工具返回经 `tool_result`；提示词中文、给用户回答英文。改完不自动跑测试（在回复末尾提醒）。
- Web：需要图表类型处一律点用 `CHART_TYPE.XXX`、不写裸字符串；前后端契约手工同步。
- 命名：同业务文件/方法统一业务前缀。数据类型 `ChartFormat` 为前后端一致的 5 值（standard 默认）、每数据类型固定支持一组图表类型。
- 向后兼容：`units` 全程可选，老图（无 units）解析照旧、前端退回千分位、不做硬校验。无 DB 迁移。
- 提交：**每个 Task 独立提交**，但**提交前须用户确认**（项目 git 规则）；执行时把每个 Task 的 commit 步骤替换为"暂存 + 待确认"，最后统一经用户同意提交。

---

## 共享契约（两端必须逐字一致）

**UnitKind 六值**：`currency` | `percent` | `ratio` | `count` | `duration` | `other`

**units 字段**：与 `columns` 定位对齐的数组。`units[0]=null`（分类/标签列），`units[1..]` 每个度量列一个 UnitKind。可选（老图缺省）。

**每类型通道容量 capacity**：
| capacity | types |
|---|---|
| 1 | bar, line, area, stacked_bar, horizontal_bar, pie, donut, radar, stacked_area, step_line, heatmap, treemap, waterfall, boxplot, gauge |
| 2 | combo, scatter |
| 3 | bubble |

**容量规则**：`distinct(非 null 的 units[1..]) ≤ capacity[type]`。列 0 恒为标签列（units[0] 必 null）；列 1.. 恒为度量列（units 必非 null 合法 kind）——此约定对全部类型统一成立。

**数值格式化（前端按 kind）**：`currency`→`$`+千分位；`percent`→值+`%`；`ratio`→值+`x`；`count`/`duration`/`other`→千分位。

---

## 文件结构

**Python line（`CIOaas-python/`）**
- Modify `source/ai/agent/chatbot_graph/chart/spec.py` — `ChartFormat`→前后端一致 5 值数据类型、`CHART_FORMATS`→`CHART_TYPE_DEFS`（含 data_type/capacity）、`ChartSpec` 加 `units`、加 `UNIT_KINDS`、派生 `TYPE_CAPACITY`/`TYPE_DATATYPE`/`DATATYPE_TYPES`。
- Modify `source/ai/tools/chart_validate_tool.py` — 删 `_looks_ratio_like`/`_RATIO_NAME_TOKENS`；typed 规则按 type 分支；新增 units 校验 + 容量规则。
- Modify `source/ai/prompts/chatbot/chart_prompt.py` — CHART_SECTION 加 units 规则 + 容量选型；`_shape_card` 改从 `CHART_TYPE_DEFS` 按 shape 分组；版本 1.11→1.12。
- Test `tests/ai/chart/test_chart_spec.py`、`tests/ai/tools/test_chart_validate_tool.py`（按现有 tests 目录结构落位）。

**Web line（`CIOaas-web/`）**
- Modify `src/services/api/chat/chatDto.ts` — 加 `UNIT_KIND`/`UnitKind` + `ChartSpec.units`。
- Modify `src/pages/devSupport/chat/utils/charts/registry.ts` — 每类型加 `capacity`。
- Modify `src/pages/devSupport/chat/utils/charts/shared.ts` — 加 `formatByKind` + 应用到 tooltip/axisLabel。
- Modify `src/pages/devSupport/chat/utils/charts/combo.ts` — 右轴由 `units` 推导。
- Modify `src/pages/devSupport/chat/components/ChatChart.tsx` — `resolveRenderType` 加容量兜底。

> 两 line 相互独立（不同子项目、无共享文件），可并行执行；唯一耦合是上面《共享契约》须逐字一致。

---

## Python Line

### Task P1: spec.py —— 单一格式 + 按类型契约 + units 字段

**Files:** Modify `source/ai/agent/chatbot_graph/chart/spec.py`；Test `tests/ai/chart/test_chart_spec.py`

**Interfaces (Produces):**
- `UNIT_KINDS: tuple[str,...]` = `("currency","percent","ratio","count","duration","other")`
- `ChartTypeDef = NamedTuple(shape:str, example:dict, capacity:int)`
- `CHART_TYPE_DEFS: dict[str, ChartTypeDef]`（键=type）
- `CHART_TYPES: tuple[str,...]`（= keys）、`TYPE_CAPACITY: dict[str,int]`（派生）
- `ChartFormat = Literal["standard","points","flow","distribution","single"]`（standard 默认，前后端一致）
- `ChartSpec.units: Optional[list[Optional[str]]]`（wire 键 `units`）

- [ ] **Step 1: 写失败测试**（`tests/ai/chart/test_chart_spec.py`）
```python
from ai.agent.chatbot_graph.chart.spec import (
    UNIT_KINDS, CHART_TYPES, TYPE_CAPACITY, parse_chart_spec_verbose,
)

def test_unit_kinds_and_capacity():
    assert UNIT_KINDS == ("currency", "percent", "ratio", "count", "duration", "other")
    assert TYPE_CAPACITY["bar"] == 1
    assert TYPE_CAPACITY["combo"] == 2
    assert TYPE_CAPACITY["scatter"] == 2
    assert TYPE_CAPACITY["bubble"] == 3
    assert set(TYPE_CAPACITY) == set(CHART_TYPES)

def test_units_parsed_and_passthrough():
    spec = {"type": "combo", "columns": ["Q", "Rev", "Growth"],
            "units": [None, "currency", "percent"], "rows": [["Q1", 1, 2]]}
    normalized, err = parse_chart_spec_verbose(spec)
    assert err is None
    assert normalized["units"] == [None, "currency", "percent"]

def test_units_optional_backward_compat():
    spec = {"type": "bar", "columns": ["Q", "Rev"], "rows": [["Q1", 1]]}
    normalized, err = parse_chart_spec_verbose(spec)
    assert err is None
    assert "units" not in normalized  # 缺省不出现（exclude_none）
```

- [ ] **Step 2: 跑测试确认失败** — `cd CIOaas-python && uv run pytest tests/ai/chart/test_chart_spec.py -v`（预期 ImportError / KeyError）

- [ ] **Step 3: 改 spec.py**（要点，保持文件内原注释风格）
  - 顶部 `ChartFormat = Literal["standard","points","flow","distribution","single"]`（standard 默认），每 chart 类型带 `data_type`，派生 `TYPE_DATATYPE`/`DATATYPE_TYPES`（引 spec §3.0）。
  - 新增：
```python
UNIT_KINDS: tuple[str, ...] = ("currency", "percent", "ratio", "count", "duration", "other")

class ChartTypeDef(NamedTuple):
    shape: str      # 本类型 columns/rows 摆法（喂提示词卡 + validate 报错自纠）
    example: dict   # 一个具体合法样例
    capacity: int   # 通道容量：能独立承载的单位种类数（分轴上限）

_SERIES_SHAPE = "[分类, 序列1, 序列2, …]（每序列一个 units；combo 另加 seriesTypes，右轴由 units 推导）"
_SERIES_EXAMPLE = {"type": "bar", "columns": ["Quarter", "Revenue ($K)", "EBITDA ($K)"],
                   "units": [None, "currency", "currency"],
                   "rows": [["Q1", 1200, 200], ["Q2", 1450, 310]]}
_SERIES_CAP1 = ("bar", "line", "area", "stacked_bar", "horizontal_bar", "pie", "donut",
                "radar", "stacked_area", "step_line", "heatmap", "treemap")

CHART_TYPE_DEFS: dict[str, ChartTypeDef] = {
    **{t: ChartTypeDef(_SERIES_SHAPE, _SERIES_EXAMPLE, 1) for t in _SERIES_CAP1},
    "combo": ChartTypeDef(_SERIES_SHAPE, {**_SERIES_EXAMPLE, "type": "combo",
             "columns": ["Quarter", "Revenue ($K)", "Growth (%)"],
             "units": [None, "currency", "percent"],
             "rows": [["Q1", 1200, 12], ["Q2", 1450, 20]], "seriesTypes": ["bar", "line"]}, 2),
    "scatter": ChartTypeDef("[点标签, x, y]（3 列，x/y 各一 units）",
             {"type": "scatter", "columns": ["Company", "ARR Growth %", "EBITDA Margin %"],
              "units": [None, "percent", "percent"],
              "rows": [["Acme", 45, 12], ["Globex", 30, -5]]}, 2),
    "bubble": ChartTypeDef("[点标签, x, y, size]（4 列，x/y/size 各一 units）",
             {"type": "bubble", "columns": ["Company", "ARR Growth %", "Margin %", "Revenue ($K)"],
              "units": [None, "percent", "percent", "currency"],
              "rows": [["Acme", 45, 12, 900]]}, 3),
    "waterfall": ChartTypeDef("[环节, 增减值]（2 列，增正减负、必填；锚点行放 totals）",
             {"type": "waterfall", "columns": ["Stage", "Change ($K)"], "units": [None, "currency"],
              "rows": [["Opening", 500], ["Collections", 320], ["OpEx", -280], ["Closing", 540]],
              "totals": ["Opening", "Closing"]}, 1),
    "boxplot": ChartTypeDef("[组标签, low, q1, median, q3, high(, you?)]（6/7 列、升序）",
             {"type": "boxplot", "columns": ["Metric", "Low", "Q1", "Median", "Q3", "High"],
              "units": [None, "percent", "percent", "percent", "percent", "percent"],
              "rows": [["ARR Growth %", 5, 18, 32, 48, 70]]}, 1),
    "gauge": ChartTypeDef("[标签, 值]（2 列 1 行、值 0-100）",
             {"type": "gauge", "columns": ["Metric", "Percentile"], "units": [None, "percent"],
              "rows": [["Overall", 72]]}, 1),
}

CHART_TYPES: tuple[str, ...] = tuple(CHART_TYPE_DEFS.keys())
TYPE_CAPACITY: dict[str, int] = {t: d.capacity for t, d in CHART_TYPE_DEFS.items()}
```
  - `ChartSpec` 加字段：`units: Optional[list[Optional[str]]] = None`（注释：与 columns 对齐、列 0 null、度量列一个 UnitKind；结构层不校验 kind 合法性，交 validate_chart）。
  - 删除旧 `ChartFormat`（5 值）、`ChartFormatDef`、`CHART_FORMATS`、`TYPE_FORMAT`（若他处 import 需在 P2/P3 同步）。
  - 更新文件头注释：新增图表类型 = 往 `CHART_TYPE_DEFS` 加一项（含 capacity）+ 前端 registry。

- [ ] **Step 4: 跑测试确认通过** — `uv run pytest tests/ai/chart/test_chart_spec.py -v`（预期 PASS）

- [ ] **Step 5: 暂存待确认** — `git add source/ai/agent/chatbot_graph/chart/spec.py tests/ai/chart/test_chart_spec.py`（提交文案见末尾，待用户确认）

---

### Task P2: chart_validate_tool.py —— units 校验 + 容量规则 + 删启发式

**Files:** Modify `source/ai/tools/chart_validate_tool.py`；Test `tests/ai/tools/test_chart_validate_tool.py`

**Interfaces (Consumes):** P1 的 `CHART_TYPES`/`CHART_TYPE_DEFS`/`TYPE_CAPACITY`/`UNIT_KINDS`。

- [ ] **Step 1: 写失败测试**（`tests/ai/tools/test_chart_validate_tool.py`，用现有 `_check_chart_spec` 同步入口或 `chart_validate_tool` 异步入口；下用内部同步函数便于断言）
```python
from ai.tools.chart_validate_tool import _check_chart_spec

def _errs(spec):
    r = _check_chart_spec(spec)
    return r.errors if not r.ok else []

def test_measure_missing_unit_fails():
    e = _errs({"type": "bar", "columns": ["Q", "Rev"], "rows": [["Q1", 1]]})
    assert any("单位" in x or "units" in x for x in e)

def test_category_col_must_be_null():
    e = _errs({"type": "bar", "columns": ["Q", "Rev"], "units": ["currency", "currency"],
               "rows": [["Q1", 1]]})
    assert any("分类" in x for x in e)

def test_illegal_kind_fails():
    e = _errs({"type": "bar", "columns": ["Q", "Rev"], "units": [None, "dollars"],
               "rows": [["Q1", 1]]})
    assert any("dollars" in x for x in e)

def test_capacity_exceeded_bar_two_units():
    e = _errs({"type": "bar", "columns": ["Q", "Rev", "Growth"], "units": [None, "currency", "percent"],
               "rows": [["Q1", 1, 2]]})
    assert any("轴" in x or "combo" in x for x in e)

def test_combo_two_units_ok():
    r = _check_chart_spec({"type": "combo", "columns": ["Q", "Rev", "Growth"],
                           "units": [None, "currency", "percent"], "rows": [["Q1", 1, 2]],
                           "seriesTypes": ["bar", "line"]})
    assert r.ok, r.errors

def test_same_unit_multi_series_shares_axis_ok():
    r = _check_chart_spec({"type": "bar", "columns": ["Q", "Rev", "Cash"],
                           "units": [None, "currency", "currency"], "rows": [["Q1", 1, 999999]]})
    assert r.ok, r.errors

def test_bubble_three_units_ok():
    r = _check_chart_spec({"type": "bubble", "columns": ["Co", "x", "y", "size"],
                           "units": [None, "percent", "percent", "currency"], "rows": [["A", 1, 2, 3]]})
    assert r.ok, r.errors
```

- [ ] **Step 2: 跑测试确认失败** — `uv run pytest tests/ai/tools/test_chart_validate_tool.py -v`

- [ ] **Step 3: 改 chart_validate_tool.py**
  - import 改为从 P1 取 `CHART_TYPES, CHART_TYPE_DEFS, TYPE_CAPACITY, UNIT_KINDS, parse_chart_spec_verbose`（删 `CHART_FORMATS`/`TYPE_FORMAT`）。
  - **删** `_RATIO_NAME_TOKENS`、`_looks_ratio_like`，及 combo 分支里依赖它的 rightAxis 报错。
  - `_typed_errors`：`fmt = TYPE_FORMAT[t]` 全部改为按 type 判定：
```python
    if t in ("scatter", "bubble"):   # 原 points
        expected = 4 if t == "bubble" else 3
        ...（列数 / 逐行数字，原逻辑不变）
    if t == "waterfall":             # 原 flow
        ...（原逻辑不变）
    if t == "boxplot":               # 原 distribution
        ...（原逻辑不变）
    if t == "gauge":                 # 原 single
        ...（原逻辑不变）
    if t == "combo":
        bad = [s for s in (spec.get("seriesTypes") or []) if s not in ("bar", "line")]
        if bad:
            errors.append(f"seriesTypes: combo 各系列画法只能是 bar 或 line，非法值：{bad}")
        # rightAxis 不再自查（右轴由前端按 units 推导）；单位/分轴统一走 _unit_errors
```
  - 新增 `_unit_errors(spec)`（对**所有类型**统一校验，落实准则①②）：
```python
def _unit_errors(spec: dict[str, Any]) -> list[str]:
    """单位校验（所有类型统一）：列 0 是标签列须 null、列 1.. 是度量列须合法 kind；
    不同单位种类数 ≤ 该类型通道容量（一根坐标只放一种单位）。"""
    t = spec.get("type")
    columns = spec["columns"]
    units = spec.get("units")
    errors: list[str] = []
    if units is None:
        return [f"units: 缺单位。请给与 columns 对齐的 units 数组"
                f"（列 0 = null；每个度量列声明 kind：{', '.join(UNIT_KINDS)}）"]
    if len(units) != len(columns):
        return [f"units: 长度（{len(units)}）须与 columns（{len(columns)}）一致、逐位对齐"]
    if units[0] is not None:
        errors.append(f"units[0]: 分类/标签列 '{columns[0]}' 不应带单位，请填 null")
    measure_kinds = []
    for i in range(1, len(units)):
        k = units[i]
        if k is None:
            errors.append(f"units[{i}]: 度量列 '{columns[i]}' 缺单位，请声明 kind："
                          f"{', '.join(UNIT_KINDS)}")
        elif k not in UNIT_KINDS:
            errors.append(f"units[{i}]: '{k}' 不是合法单位，只能是 {', '.join(UNIT_KINDS)}")
        else:
            measure_kinds.append(k)
    distinct = sorted(set(measure_kinds))
    cap = TYPE_CAPACITY.get(t) if t in TYPE_CAPACITY else None
    if cap is not None and len(distinct) > cap:
        hint = {1: "改用 combo（2 种）/ bubble（3 种）或拆成多张图",
                2: "改用 bubble（3 种）或拆成多张图",
                3: "拆成多张图"}.get(cap, "拆成多张图")
        errors.append(f"units: 图型 '{t}' 只能承载 {cap} 种单位，但检出 {len(distinct)} 种"
                      f"（{', '.join(distinct)}）——一根坐标只放一种单位；{hint}")
    return errors
```
  - 在 `_check_chart_spec` 里，结构底线过之后、typed 之外，把 `_unit_errors` 并入（typed + unit 一起返回，`t in CHART_TYPE_DEFS` 时附正确摆法）：
```python
    typed = _typed_errors(normalized) + _unit_errors(normalized)
    if typed:
        t = normalized.get("type")
        if t in CHART_TYPE_DEFS:
            typed.append(f"{t} 正确摆法：{CHART_TYPE_DEFS[t].shape}")
        return ChartValidateResult(ok=False, errors=typed, message="...")
```
  （注：`_typed_errors` 末尾原自纠附加行移到此处统一加，避免重复。）

- [ ] **Step 4: 跑测试确认通过** — `uv run pytest tests/ai/tools/test_chart_validate_tool.py -v`

- [ ] **Step 5: 暂存待确认** — `git add source/ai/tools/chart_validate_tool.py tests/ai/tools/test_chart_validate_tool.py`

---

### Task P3: chart_prompt.py —— 提示词加 units + 容量选型

**Files:** Modify `source/ai/prompts/chatbot/chart_prompt.py`

**Interfaces (Consumes):** P1 的 `CHART_TYPE_DEFS`。

- [ ] **Step 1: 改 `_shape_card`** —— 从 `CHART_TYPE_DEFS` 按 shape 分组（同 shape 的 types 合并一行，保持卡片简洁），每行附 capacity：
```python
def _shape_card() -> str:
    from collections import OrderedDict
    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for t, d in CHART_TYPE_DEFS.items():
        groups.setdefault((d.shape, d.capacity), []).append(t)
    lines = ["各类型列约定（columns/rows 照此填；capacity=可承载的单位种类数）："]
    for (shape, cap), types in groups.items():
        lines.append(f"- types={', '.join(types)}（capacity={cap}）; shape={shape}")
    return "\n".join(lines)
```

- [ ] **Step 2: CHART_SECTION 正文加 units 规则**
  - 「### series 通用规则」后补：`每个度量列必须在 units 里声明单位 kind（{UNIT_KINDS}）；units 与 columns 对齐，列 0（分类/标签）填 null。`（kind 列表内联或从 spec 引）
  - 「### 选型偏好」把 combo 段改为按单位数：
    - `同一根坐标只放一种单位。数不同单位的种类数 N：N=1 → 任意图型；N=2 → combo（自动左右分轴，无需填 rightAxis）或 scatter；N=3 → bubble（点状数据 [实体,x,y,size]）；N≥4 → 拆成多张图。`
    - 保留「同单位多序列即使量级悬殊也共用一条 Y 轴」。
    - 删除/改写旧的"用 rightAxis 放右轴"（右轴现由前端按 units 推导）。
  - 「### 数据红线」补一条：`每个度量序列必须带单位；不同单位不得共用一根坐标轴。`
  - 「### 自查流程」不变（validate_chart 通过才出图）。

- [ ] **Step 3: 版本号** —— 头部 `# version: 1.11` → `1.12`，并在演进注释追加一行 1.12 说明（units 显式化 + 容量选型 + 格式收敛、shape 卡改按 type 分组）。

- [ ] **Step 4: 冒烟** —— `cd CIOaas-python && uv run python -c "from ai.prompts.chatbot.chart_prompt import CHART_SECTION; print(CHART_SECTION)"`（预期正常打印、含 units 与 capacity 文案，无 import 错）

- [ ] **Step 5: 暂存待确认** — `git add source/ai/prompts/chatbot/chart_prompt.py`

---

## Web Line

### Task W1: chatDto.ts —— UnitKind + units 字段

**Files:** Modify `src/services/api/chat/chatDto.ts`

**Interfaces (Produces):** `UNIT_KIND` (as const) / `UnitKind` (union) / `ChartSpec.units?: (UnitKind | null)[]`

- [ ] **Step 1:** 在 `CHART_TYPE` 附近新增（照 `CHART_TYPE` 的 `as const` + union 约定）：
```ts
export const UNIT_KIND = {
  CURRENCY: 'currency', PERCENT: 'percent', RATIO: 'ratio',
  COUNT: 'count', DURATION: 'duration', OTHER: 'other',
} as const;
export type UnitKind = (typeof UNIT_KIND)[keyof typeof UNIT_KIND];
```
- [ ] **Step 2:** `ChartSpec` 加字段（含中文注释，说明与 columns 对齐、列 0 null、可选/老图缺省）：
```ts
  /** 单位（与 columns 对齐）：列 0=null（分类/标签），列 1.. 每个度量列一个 UnitKind。可选（老图无）。 */
  units?: (UnitKind | null)[];
```
- [ ] **Step 3: 类型检查** — `cd CIOaas-web && npm run tsc`（需 node PATH；预期无新增错误，基线 2 个存量坏文件除外）
- [ ] **Step 4: 暂存待确认** — `git add src/services/api/chat/chatDto.ts`

---

### Task W2: registry.ts —— 每类型 capacity

**Files:** Modify `src/pages/devSupport/chat/utils/charts/registry.ts`

- [ ] **Step 1:** 读现有 registry 条目结构（type → {label, builder, format, suits, ...}）。给每个类型条目加 `capacity` 字段，取值同《共享契约》表（combo/scatter=2、bubble=3、其余=1）。若 registry 有共享默认工厂，补 `capacity` 到类型元数据处。
- [ ] **Step 2:** 导出一个便捷读取（若他处需要）：`export const capacityOf = (t?: ChartType) => (t && REGISTRY[t]?.capacity) ?? 1;`（按现有 registry 命名习惯）
- [ ] **Step 3: tsc** — `npm run tsc`
- [ ] **Step 4: 暂存待确认** — `git add src/pages/devSupport/chat/utils/charts/registry.ts`

---

### Task W3: shared.ts —— 按 kind 格式化数值

**Files:** Modify `src/pages/devSupport/chat/utils/charts/shared.ts`

**Interfaces (Produces):** `formatByKind(value: number|null|undefined, kind?: UnitKind|null): string`

- [ ] **Step 1:** 新增 `formatByKind`（复用现有 `num`/`isBlank`/千分位）：
```ts
export function formatByKind(raw: unknown, kind?: UnitKind | null): string {
  if (isBlank(raw)) return 'NA';
  const n = num(raw);
  const s = n.toLocaleString('en-US');
  switch (kind) {
    case 'currency': return `$${s}`;
    case 'percent': return `${s}%`;
    case 'ratio': return `${s}x`;
    default: return s; // count / duration / other / undefined
  }
}
```
- [ ] **Step 2:** 把各 tooltip/axisLabel 里裸 `num(raw).toLocaleString('en-US')` 处，按该序列对应的 `spec.units[i]` 传入 kind 调 `formatByKind`。序列 index→units 映射：series 系 `units[seriesIndex+1]`；points 系按 x/y/size 维度对应 `units[1..]`。**老图 `units` 缺省 → kind=undefined → 退回千分位**（兼容）。
- [ ] **Step 3: tsc** — `npm run tsc`
- [ ] **Step 4: 暂存待确认** — `git add src/pages/devSupport/chat/utils/charts/shared.ts`

---

### Task W4: combo.ts —— 右轴由 units 推导

**Files:** Modify `src/pages/devSupport/chat/utils/charts/combo.ts`

- [ ] **Step 1:** 在 `buildCombo` 里，若 `spec.units` 存在：取度量列 kinds（`units[1..]`）去重按出现序，**第 2 种 kind 的序列 → 右轴**（`yAxisIndex:1`），其余左轴；`hasRight = 出现≥2 种 kind`。`spec.units` 缺省时退回原 `rightAxis` 字段逻辑（兼容老图）。
```ts
const kinds = (spec.units ?? []).slice(1);
const order = [...new Set(kinds.filter(Boolean))];
const rightKind = order[1];
const onRight = (i: number) => spec.units ? kinds[i] === rightKind && !!rightKind
                                          : right.has(names[i]); // 老图回退 rightAxis
```
  （保留 `alignedDualAxisBounds` 零线对齐逻辑不变。）
- [ ] **Step 2: tsc** — `npm run tsc`
- [ ] **Step 3: 暂存待确认** — `git add src/pages/devSupport/chat/utils/charts/combo.ts`

---

### Task W5: ChatChart.tsx —— resolveRenderType 容量兜底

**Files:** Modify `src/pages/devSupport/chat/components/ChatChart.tsx`

- [ ] **Step 1:** 在 `resolveRenderType` 里，若 `spec.units` 存在：算度量列去重 kind 数 N；若 `N > capacityOf(finalType)` → 返回 null（→ 已有 `ChartFallback` 展示、不画误导图）。`units` 缺省时跳过此检查（兼容老图）。
- [ ] **Step 2: tsc** — `npm run tsc`
- [ ] **Step 3: 暂存待确认** — `git add src/pages/devSupport/chat/components/ChatChart.tsx`

---

## Self-Review（写完计划对照 spec）

- **准则①（每数据有单位）**：P1 加字段 + P2 `_unit_errors` 强制度量列非 null kind + W3 前端显示 `$/%` ✔
- **准则②（不同单位不共轴）**：P2 容量规则（distinct ≤ capacity）拦普通 bar 混 $/% + W4 右轴按 units 推导 + W5 容量兜底 ✔
- **数据类型前后端一致**：P1 `ChartFormat`→5 值 + data_type、`CHART_FORMATS`→`CHART_TYPE_DEFS`、派生 TYPE_DATATYPE/DATATYPE_TYPES、P2 按 data_type 分支、P3 shape 卡按 shape 分组 ✔
- **删启发式**：P2 删 `_looks_ratio_like`/`_RATIO_NAME_TOKENS` ✔
- **校验闭环 + 失败目录**：P2 各失败原因文案对应 spec §5.2 目录（缺单位/非法 kind/分类列带单位/长度不符/超容量）✔
- **向后兼容**：P1 units 可选 + W3/W4/W5 units 缺省回退 ✔
- **类型一致性**：UnitKind 六值、capacity 表两端逐字一致（见《共享契约》）✔
- **无占位符**：Python 步骤含完整代码；Web 步骤给出改动点 + 关键代码，具体行由执行者对照现有文件补全（现有 builder 代码风格执行时读取匹配）。

---

## 提交文案（待用户确认后统一提交）

- P1 `feat(chart): unify data format to single table with per-type defs and units field`
- P2 `feat(chart): validate units and enforce channel-capacity axis rule; drop ratio-name heuristic`
- P3 `feat(chart): prompt requires units and capacity-based chart selection (v1.12)`
- W1 `feat(chart): add UnitKind and units field to ChartSpec DTO`
- W2 `feat(chart): add per-type channel capacity to chart registry`
- W3 `feat(chart): format chart values by unit kind`
- W4 `feat(chart): derive combo right axis from units`
- W5 `feat(chart): fall back when unit kinds exceed chart channel capacity`
