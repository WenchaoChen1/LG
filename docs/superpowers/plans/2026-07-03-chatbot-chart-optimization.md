# Chatbot 图表优化实现计划（方案 B + 收尾方案 C）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 关联文档: [方案 spec](../specs/2026-07-02-chatbot-chart-optimization-design.md) · [原图表设计](../specs/2026-06-10-chat-chart-design.md)

**Goal:** 图表类型定义单点化（后端 pydantic 契约 + 提示词段共用、前端注册表 + 一类型一 builder），并新增 6 种图表类型（area / stacked_bar / horizontal_bar / donut / scatter / combo）；收尾清理 ResizeObserver 重复与 chatManage 图表复用（方案 C）。

**Architecture:** 后端新建 `ai/chatbotgraph/chart/` 包（spec 契约 + fence 解析），提示词图表段抽到 `prompts/chatbot/chart_prompt.py` 由类型枚举生成、tool/sql 两轨共用；前端新建 `pages/ai/chat/utils/charts/`（registry + builders），`ChatChart` 由注册表驱动。协议仍为纯数据二维表，combo 增加可选 `seriesTypes`/`rightAxis` 字段（向后兼容）。

**Tech Stack:** Python 3.12 + pydantic v2 + pytest；React 16 + TypeScript + ECharts 5.6 + umi-test。

**仓库规则（覆盖本 skill 默认动作，必须遵守）：**
- **不自动跑测试**：所有「Run test」步骤跳过实际执行，只做轻量校验（Python import 冒烟、`npm run tsc`）；测试统一等用户下令再跑。
- **不自动 commit**：所有「Commit」步骤为**记录提交点**，实际执行需用户确认；提交消息用英文。
- 两个子仓库当前都在 `sprint113` 分支，工作区干净；开工前再核对一次分支。
- 前端 PowerShell 环境 node 已挂 User PATH；tsc 基线有 2 个存量坏文件（非本次引入的错误不用管）。

**并行性：** Phase 1（后端 Task 1–4）与 Phase 2（前端 Task 5–9）相互独立可并行；Phase 3（文档）在两者后；Phase 4（方案 C，Task 11–13）最后。

---

## Phase 1 · 后端（CIOaas-python）

### Task 1: chart 包 + spec 契约单点

**Files:**
- Create: `CIOaas-python/source/ai/chatbotgraph/chart/__init__.py`
- Create: `CIOaas-python/source/ai/chatbotgraph/chart/spec.py`
- Test: `CIOaas-python/tests/ai/chatbotgraph/chart/test_spec.py`（新建目录，含空 `__init__.py` 若同级已有惯例则跟随；`tests/ai/chatbotgraph/` 已存在）

- [ ] **Step 1.1: 写 `spec.py`**

```python
"""chart spec 契约单点：类型枚举 + pydantic 校验模型。

前端对应契约：CIOaas-web/src/services/api/chat/chatDto.ts 的 ChartSpec/ChartType 与
src/pages/ai/chat/utils/charts/registry.ts（改任一侧必须同步另一侧与
docs/superpowers/specs/2026-06-10-chat-chart-design.md §4.1）。
提示词图表段由本枚举生成（prompts/chatbot/chart_prompt.py），新增类型只改这里 + 前端 builder。
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ChartType = Literal[
    "bar", "line", "area", "stacked_bar", "horizontal_bar",
    "pie", "donut", "radar", "scatter", "combo",
]

# 与 ChartType 保持同序（提示词模板行 / 前端 registry 均按此清单）
CHART_TYPES: tuple[str, ...] = (
    "bar", "line", "area", "stacked_bar", "horizontal_bar",
    "pie", "donut", "radar", "scatter", "combo",
)


class ChartSpec(BaseModel):
    """LLM 产出的图表纯数据二维表（wire 键 camelCase）。校验失败 → fence 降级为文本。"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: ChartType
    title: Optional[str] = None
    columns: list[str] = Field(min_length=2)
    rows: list[list[str | int | float | None]] = Field(min_length=1)
    # combo 专用（其余类型忽略）：columns[1..] 各系列画法 / 放右 Y 轴的系列名
    series_types: Optional[list[Literal["bar", "line"]]] = Field(default=None, alias="seriesTypes")
    right_axis: Optional[list[str]] = Field(default=None, alias="rightAxis")

    @field_validator("columns", mode="before")
    @classmethod
    def _coerce_columns(cls, v: object) -> object:
        # LLM 偶发把列名产成数字（如年份），宽容转字符串而非整块降级
        if isinstance(v, list):
            return [c if isinstance(c, str) else str(c) for c in v]
        return v

    @model_validator(mode="after")
    def _check_scatter(self) -> "ChartSpec":
        if self.type == "scatter" and len(self.columns) != 3:
            raise ValueError("scatter 需要恰好 3 列：[点标签, x, y]")
        return self


def parse_chart_spec(raw: object) -> Optional[dict]:
    """校验 LLM 产出的 spec；通过返回规范化 dict（columns 已转 str、None 字段剔除），失败返回 None。"""
    if not isinstance(raw, dict):
        return None
    try:
        spec = ChartSpec.model_validate(raw)
    except ValidationError:
        return None
    return spec.model_dump(by_alias=True, exclude_none=True)
```

> 注意：ai 域 `@tool`/runtime 模块禁用 `from __future__ import annotations` 的约束不涉及本文件（无 ToolRuntime），但保持不加、与包内一致。

- [ ] **Step 1.2: 写 `__init__.py`**（fence_parser 在 Task 2 迁入，本步先只导 spec，Task 2 补齐）

```python
"""chatbot 图表模块：spec 契约 + 流式 fence 解析（对外唯一入口）。"""
from ai.chatbotgraph.chart.spec import CHART_TYPES, ChartSpec, ChartType, parse_chart_spec

__all__ = ["CHART_TYPES", "ChartSpec", "ChartType", "parse_chart_spec"]
```

- [ ] **Step 1.3: 写 `tests/ai/chatbotgraph/chart/test_spec.py`**

```python
from ai.chatbotgraph.chart import CHART_TYPES, parse_chart_spec


def _base(**over):
    d = {"type": "bar", "columns": ["q", "v"], "rows": [["Q1", 1]]}
    d.update(over)
    return d


def test_valid_minimal_bar():
    assert parse_chart_spec(_base()) is not None


def test_all_types_accepted():
    for t in CHART_TYPES:
        cols = ["label", "x", "y"] if t == "scatter" else ["q", "v"]
        rows = [["A", 1, 2]] if t == "scatter" else [["Q1", 1]]
        assert parse_chart_spec(_base(type=t, columns=cols, rows=rows)) is not None, t


def test_unknown_type_rejected():
    assert parse_chart_spec(_base(type="heatmap")) is None


def test_missing_type_rejected():
    assert parse_chart_spec({"columns": ["a", "b"], "rows": [["x", 1]]}) is None


def test_single_column_rejected():
    assert parse_chart_spec(_base(columns=["only"])) is None


def test_empty_rows_rejected():
    assert parse_chart_spec(_base(rows=[])) is None


def test_non_dict_rejected():
    assert parse_chart_spec("[]") is None
    assert parse_chart_spec(None) is None


def test_null_cells_kept():
    out = parse_chart_spec(_base(rows=[["Q1", None]]))
    assert out is not None and out["rows"][0][1] is None


def test_numeric_columns_coerced_to_str():
    out = parse_chart_spec(_base(columns=[2024, 2025], rows=[[2024, 1]]))
    assert out is not None and out["columns"] == ["2024", "2025"]


def test_scatter_requires_three_columns():
    assert parse_chart_spec(_base(type="scatter", columns=["l", "x"], rows=[["A", 1]])) is None
    ok = parse_chart_spec(_base(type="scatter", columns=["l", "x", "y"], rows=[["A", 1, 2]]))
    assert ok is not None


def test_combo_optional_fields():
    ok = parse_chart_spec(_base(
        type="combo", columns=["m", "rev", "growth"], rows=[["Jan", 1, 0.1]],
        seriesTypes=["bar", "line"], rightAxis=["growth"],
    ))
    assert ok is not None and ok["seriesTypes"] == ["bar", "line"] and ok["rightAxis"] == ["growth"]


def test_combo_bad_series_type_rejected():
    assert parse_chart_spec(_base(type="combo", seriesTypes=["pie"])) is None


def test_title_none_dropped_in_dump():
    out = parse_chart_spec(_base())
    assert "title" not in out and "seriesTypes" not in out
```

- [ ] **Step 1.4: 轻量校验（不跑 pytest）**

```powershell
# CIOaas-python 目录下
uv run python -c "from ai.chatbotgraph.chart import parse_chart_spec, CHART_TYPES; print(len(CHART_TYPES))"
```
Expected: `10`

- [ ] **Step 1.5: 提交点（待用户确认后执行）** `feat(chart): add chart spec contract with pydantic validation`

### Task 2: fence_parser 迁入 chart 包 + 校验接入

**Files:**
- Move (git mv): `CIOaas-python/source/ai/chatbotgraph/chart_fence_parser.py` → `CIOaas-python/source/ai/chatbotgraph/chart/fence_parser.py`
- Modify: `CIOaas-python/source/ai/chatbotgraph/chart/__init__.py`
- Modify: `CIOaas-python/source/chatbot/application/sse_provider.py:41-44`（import 路径）
- Move: `CIOaas-python/tests/chatbot/application/test_chart_fence_parser.py` → `CIOaas-python/tests/ai/chatbotgraph/chart/test_fence_parser.py`

- [ ] **Step 2.1: git mv 并改 `_try_parse_spec` 接入 spec 校验**

```bash
cd CIOaas-python && git mv source/ai/chatbotgraph/chart_fence_parser.py source/ai/chatbotgraph/chart/fence_parser.py
```

`fence_parser.py` 头注释补一行「校验：spec.parse_chart_spec，失败降级文本」，并替换：

```python
from ai.chatbotgraph.chart.spec import parse_chart_spec


def _try_parse_spec(body: str) -> Optional[dict]:
    try:
        raw = json.loads(body.strip())
    except (ValueError, TypeError):
        return None
    return parse_chart_spec(raw)
```

（删除原「`isinstance(spec, dict) or "type" not in spec`」检查；其余状态机逻辑**一字不动**。）

- [ ] **Step 2.2: `chart/__init__.py` 补齐 re-export**

```python
"""chatbot 图表模块：spec 契约 + 流式 fence 解析（对外唯一入口）。"""
from ai.chatbotgraph.chart.fence_parser import (
    ChartFenceStreamParser, ChartSegment, Segment, TextSegment,
)
from ai.chatbotgraph.chart.spec import CHART_TYPES, ChartSpec, ChartType, parse_chart_spec

__all__ = [
    "CHART_TYPES", "ChartSpec", "ChartType", "parse_chart_spec",
    "ChartFenceStreamParser", "ChartSegment", "Segment", "TextSegment",
]
```

- [ ] **Step 2.3: 更新 `sse_provider.py` import**（现 41-44 行）

```python
from ai.chatbotgraph.chart import (
    ChartFenceStreamParser,
    ChartSegment,
)
```
（保留原 import 的全部名字，只换模块路径；先 Read 该行确认清单再改。）

- [ ] **Step 2.4: git mv 测试文件 + 更新 import + 补新类型用例**

```bash
git mv tests/chatbot/application/test_chart_fence_parser.py tests/ai/chatbotgraph/chart/test_fence_parser.py
```

首行 import 改为 `from ai.chatbotgraph.chart import (...)`（原名单不变）。文件末尾追加：

```python
def test_unknown_type_now_degrades_to_text():
    # spec 校验后：未知 type 不再作为 chart 段透传，降级为文本
    segs = _run(['```chart\n{"type":"heatmap","columns":["a","b"],"rows":[["x",1]]}\n```'])
    assert len(segs) == 1 and isinstance(segs[0], TextSegment)


def test_new_types_pass_through():
    for t in ("area", "stacked_bar", "horizontal_bar", "donut", "combo"):
        body = f'{{"type":"{t}","columns":["q","v"],"rows":[["Q1",1]]}}'
        segs = _run([f"```chart\n{body}\n```"])
        assert isinstance(segs[0], ChartSegment), t


def test_scatter_shape_enforced():
    bad = '{"type":"scatter","columns":["l","x"],"rows":[["A",1]]}'
    ok = '{"type":"scatter","columns":["l","x","y"],"rows":[["A",1,2]]}'
    assert isinstance(_run([f"```chart\n{bad}\n```"])[0], TextSegment)
    assert isinstance(_run([f"```chart\n{ok}\n```"])[0], ChartSegment)
```

> 既有用例 `test_missing_type_degrades_to_text`、`test_invalid_json_degrades_to_text` 语义不变、应继续通过。

- [ ] **Step 2.5: 全仓 grep 确认无残留旧路径**

```
grep -rn "chart_fence_parser" CIOaas-python/source CIOaas-python/tests
```
Expected: 无结果（docs/CLAUDE.md 里的提法在 Task 4 更新）。

- [ ] **Step 2.6: 轻量校验** `uv run python -c "from chatbot.application import sse_provider"`（若该 import 因环境依赖失败，退回 `uv run python -c "from ai.chatbotgraph.chart import ChartFenceStreamParser"`）

- [ ] **Step 2.7: 提交点（待用户确认）** `refactor(chart): move fence parser into chart package and validate specs`

### Task 3: 提示词图表段单点（两轨共用）

**Files:**
- Create: `CIOaas-python/source/ai/prompts/chatbot/chart_prompt.py`
- Modify: `CIOaas-python/source/ai/prompts/chatbot/retrieval_agent_prompt.py`（##图表 段，约 113-129 行）
- Modify: `CIOaas-python/source/ai/prompts/chatbot/retrieval_sql_agent_prompt.py`（##图表 段，约 119-135 行）
- Test: `CIOaas-python/tests/ai/chatbotgraph/chart/test_chart_prompt.py`

- [ ] **Step 3.1: 写 `chart_prompt.py`**（类型行由枚举生成；用 `.replace` 注入避免 f-string 花括号转义——与 sql 轨 `__TABLE_LIST__` 同一手法）

```python
# version: 1.0
"""聊天两轨（tool/sql）共用的图表提示词段。

类型枚举来自 ai.chatbotgraph.chart.spec.CHART_TYPES（契约单点）：新增图表类型时改
spec.py + 前端 registry 即可，本段模板行自动带上新类型；场景→类型的一句话规则如需
调整在本文件维护，**绝不**再在两轨提示词里各写一份。
"""
from ai.chatbotgraph.chart.spec import CHART_TYPES

_TEMPLATE = """\


##图表：
当数据值得可视化时，用 info string 为 `chart` 的围栏代码块嵌入图表，可放在段落之间任意位置。块\
体是严格 JSON，形如下例。下面这个块仅是格式模板——`<category>` / `<num>` 是说明结构的占位符，绝\
不要把这些占位符值抄进你的回答：
```chart
{"type":"__CHART_TYPES__","title":"optional","columns":["<category>","<seriesA>","<seriesB>"\
],"rows":[["<category>","<num>","<num>"],["<category>","<num>","<num>"]]}
```
（格式模板到此为止——上面的占位符不含真实数据，不得复述。）
通用规则：columns[0] 是分类轴；columns[1..] 是数据序列；每个 row 形如 [categoryValue, seriesA, \
seriesB, ...]。
类型怎么选（一句话规则，按需挑最贴切的一种）：
- 趋势 / 随时间变化 → line；要强调累计量感 → area
- 并排对比 → bar；类目名很长或按名次排列 → horizontal_bar；各期内部构成拆分 → stacked_bar
- 占比 → pie 或 donut（以 columns[1] 为数值）
- 多维评分（如 benchmark 各维百分位）→ radar
- 两个数值指标的相关性（每点一个公司/实体）→ scatter：columns **恰好 3 列** [点标签, x 指标, y \
指标]，每 row = [label, x, y]
- 量纲/量级不同的两组指标合并一图（如 $ 金额柱 + % 比率线）→ combo：另加 "seriesTypes":["bar","\
line",...]（对应 columns[1..] 各系列画法，缺省 bar）与 "rightAxis":["<系列名>"]（放右 Y 轴的系\
列，通常是 % 比率）——原「量纲差异大只能分图」的场景优先用 combo 合并
columns/rows 里的数字必须来自工具结果（ToolMessage）——绝不捏造、估算或补数。**缺数据的格必须填 JSO\
N `null`（不是 0、不要编数）**：某序列在某周期没有该值时填 `null`，只有确有数值才填数值——前端会\
把 `null` 显示为 NA 并把点位落到 0；填 0 会被误读成真实的 0。反之，**真实的 0 必须照填 0**（不\
要因为这个 0 看着异常 / 不合理就当成缺失填 `null`）。没有真实数据可画时，不要输出图表。图表前后\
保留正文叙述；一次回答可以使用多个图表。"""

CHART_SECTION = _TEMPLATE.replace("__CHART_TYPES__", "|".join(CHART_TYPES))

# sql 轨追加「表/图二选一」提醒（tool 轨的版面规则在其【展现样式风格】另有表述）
SQL_CHART_SECTION = CHART_SECTION + """\
**但同一份数据若已画图，就不要再为它附一张同数据的数值表**\
（表 / 图二选一，见上文【展现样式风格】）。"""
```

- [ ] **Step 3.2: `retrieval_agent_prompt.py` 接入**

删除 `AGENT_SYSTEM` 字符串末尾的整段 `##图表：…一次回答可以使用多个图表。`（原 113-129 行，含其前的空行），字符串在【数值精度】/【展现样式风格】等段落后正常收尾；然后在常量定义后拼接：

```python
from ai.prompts.chatbot.chart_prompt import CHART_SECTION
from ai.prompts.chatbot.prompts import current_date_note

AGENT_SYSTEM = """\
你是 LG AI Operating Partner，……（原文其余部分不动，删掉 ##图表 段）……
"""

AGENT_SYSTEM = AGENT_SYSTEM + CHART_SECTION
```

（模块 docstring 补一句「图表段来自 chart_prompt.CHART_SECTION（两轨共用）」。）

- [ ] **Step 3.3: `retrieval_sql_agent_prompt.py` 同法接入**

删除 `SQL_AGENT_SYSTEM` 末尾 `##图表：…（表 / 图二选一，见上文【展现样式风格】）。` 整段，然后：

```python
from ai.prompts.chatbot.chart_prompt import SQL_CHART_SECTION

SQL_AGENT_SYSTEM = SQL_AGENT_SYSTEM + SQL_CHART_SECTION
```

> ⚠️ 该文件用 `__TABLE_LIST__`/`__SCHEMA__` `.replace` 注入，图表段不含这两个标记，拼接顺序不影响 `sql_agent_system()`。

- [ ] **Step 3.4: 写 `test_chart_prompt.py`（契约同步测试）**

```python
from ai.chatbotgraph.chart import CHART_TYPES
from ai.prompts.chatbot.chart_prompt import CHART_SECTION, SQL_CHART_SECTION
from ai.prompts.chatbot.retrieval_agent_prompt import AGENT_SYSTEM
from ai.prompts.chatbot.retrieval_sql_agent_prompt import SQL_AGENT_SYSTEM


def test_all_types_in_section():
    assert "|".join(CHART_TYPES) in CHART_SECTION


def test_no_placeholder_left():
    assert "__CHART_TYPES__" not in CHART_SECTION


def test_both_prompts_carry_section_once():
    for prompt in (AGENT_SYSTEM, SQL_AGENT_SYSTEM):
        assert prompt.count("##图表：") == 1
        assert "|".join(CHART_TYPES) in prompt


def test_sql_section_has_table_or_chart_rule():
    assert "表 / 图二选一" in SQL_CHART_SECTION
    assert "表 / 图二选一" not in CHART_SECTION
```

- [ ] **Step 3.5: 轻量校验**

```powershell
uv run python -c "from ai.prompts.chatbot.retrieval_agent_prompt import AGENT_SYSTEM; from ai.prompts.chatbot.retrieval_sql_agent_prompt import SQL_AGENT_SYSTEM; assert AGENT_SYSTEM.count('##图表') == 1 and SQL_AGENT_SYSTEM.count('##图表') == 1; print('ok')"
```

- [ ] **Step 3.6: 提交点（待用户确认）** `feat(chart): single-source chart prompt section shared by both retrieval tracks`

### Task 4: 后端文档同步

**Files:**
- Modify: `CIOaas-python/source/ai/CLAUDE.md`（目录表：`chatbotgraph/chart_fence_parser.py` 行 → `chatbotgraph/chart/` 包；prompts 相关行补 `chart_prompt.py`）

- [ ] **Step 4.1:** 目录表两处更新：
  - `chatbotgraph/chart_fence_parser.py` 行改为：`chatbotgraph/chart/` — 图表模块（`spec.py` 契约单点：ChartType 枚举 + pydantic ChartSpec + parse_chart_spec；`fence_parser.py` 流式 fence 解析，校验失败降级文本；前端契约同步见 spec.py 头注释）
  - `prompts/chatbot/prompts.py` 行后补一行：`prompts/chatbot/chart_prompt.py` — 两轨共用图表提示词段（类型行由 `chart.spec.CHART_TYPES` 生成；新增类型改 spec.py + 前端 registry 即可）
- [ ] **Step 4.2: 提交点（待用户确认）** `docs(ai): update module map for chart package`

---

## Phase 2 · 前端（CIOaas-web，与 Phase 1 并行）

### Task 5: 契约扩展（chatDto.ts）

**Files:**
- Modify: `CIOaas-web/src/services/api/chat/chatDto.ts:22-36`

- [ ] **Step 5.1:** 替换 ChartType / ChartSpec：

```ts
/** 图表类型（前后端数据契约，与后端 ai/chatbotgraph/chart/spec.py CHART_TYPES 同步）。 */
export type ChartType =
  | 'bar'
  | 'line'
  | 'area'
  | 'stacked_bar'
  | 'horizontal_bar'
  | 'pie'
  | 'donut'
  | 'radar'
  | 'scatter'
  | 'combo';

/**
 * 图表纯数据二维表（前后端数据契约 \ SSE `event: chart` 的 data）。
 * columns[0] = 分类轴标签字段；columns[1..] = 各数据系列名。
 * scatter 特例：columns 恰好 3 列 [点标签, x, y]。
 * 见 docs/superpowers/specs/2026-06-10-chat-chart-design.md §4.1。
 */
export interface ChartSpec {
  type: ChartType;
  title?: string;
  columns: string[];
  // null = 该格无数据（前端 tooltip 显示 NA、点位落 0）；区别于真 0。
  rows: (string | number | null)[][];
  /** combo 专用：columns[1..] 各系列画法，缺省全 bar。 */
  seriesTypes?: ('bar' | 'line')[];
  /** combo 专用：放右 Y 轴的系列名（columns 里的名字）。 */
  rightAxis?: string[];
}
```

- [ ] **Step 5.2: 提交点（待用户确认）** `feat(chat): extend chart contract with 6 new types and combo fields`

### Task 6: charts 模块（shared + 10 builders + registry）

**Files:**
- Create: `CIOaas-web/src/pages/ai/chat/utils/charts/shared.ts`
- Create: `CIOaas-web/src/pages/ai/chat/utils/charts/{bar,line,area,stackedBar,horizontalBar,pie,donut,radar,scatter,combo}.ts`
- Create: `CIOaas-web/src/pages/ai/chat/utils/charts/registry.ts`

- [ ] **Step 6.1: `shared.ts`**（自现 `chartSpec.ts` 平移 num/isBlank/标题图例逻辑，语义零变化）

```ts
/**
 * 图表 builders 公共件：数值清洗 + 标题/图例基础件 + 分类轴通用组装。
 * 自原 utils/chartSpec.ts 抽出（2026-07-03 图表模块化），语义不变。
 */
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import {
  CHART_PALETTE,
  defaultTooltip,
  defaultGrid,
  defaultLegend,
  axisLabelStyle,
  axisLineStyle,
} from '@/pages/ai/_shared/chartTheme';

export function num(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

/** 空/缺数据（null/undefined/空串/非数字）≠ 真 0：tooltip 显示 NA、点位落 0。 */
export function isBlank(v: unknown): boolean {
  if (v === null || v === undefined) return true;
  if (typeof v === 'number') return !Number.isFinite(v);
  const s = String(v).trim();
  if (s === '') return true;
  return !Number.isFinite(Number(s));
}

export const seriesNames = (spec: ChartSpec): string[] => spec.columns.slice(1);

export interface BaseParts {
  base: Pick<EChartsOption, 'color' | 'title'>;
  hasTitle: boolean;
  /** 有标题时图例下移到标题之下 */
  legendTop: number;
  /** 单系列时图例与标题/坐标轴信息冗余，隐藏（饼图另论） */
  showSeriesLegend: boolean;
}

export function baseParts(spec: ChartSpec): BaseParts {
  const hasTitle = !!spec.title;
  const titleOpt = hasTitle
    ? { title: { text: spec.title, left: 'center' as const, top: 4, textStyle: { fontSize: 13 } } }
    : {};
  return {
    base: { color: [...CHART_PALETTE], ...titleOpt },
    hasTitle,
    legendTop: hasTitle ? 28 : 0,
    showSeriesLegend: seriesNames(spec).length > 1,
  };
}

/** 分类轴 tooltip：空格显示 NA、真 0 显示 0，数值千分位（语义同原 chartSpec.ts）。 */
export function categoricalTooltip(rows: ChartSpec['rows']): EChartsOption['tooltip'] {
  return {
    ...defaultTooltip,
    formatter: (params: unknown) => {
      const list = (Array.isArray(params) ? params : [params]) as {
        dataIndex: number;
        seriesIndex: number;
        seriesName: string;
        marker: string;
        axisValue?: string;
      }[];
      if (!list.length) return '';
      const idx = list[0].dataIndex;
      const header = String(rows[idx]?.[0] ?? list[0].axisValue ?? '');
      const lines = list.map((p) => {
        const raw = rows[idx]?.[p.seriesIndex + 1];
        const display = isBlank(raw) ? 'NA' : num(raw).toLocaleString('en-US');
        return `${p.marker} ${p.seriesName}: <b>${display}</b>`;
      });
      return [header, ...lines].join('<br/>');
    },
  };
}

/**
 * 分类轴图表（bar/line/area/stacked/horizontal/combo）的公共组装：
 * 轴 + 网格 + 图例 + tooltip；series 由各 builder 构造传入。
 */
export function categoricalOption(
  spec: ChartSpec,
  series: NonNullable<EChartsOption['series']>,
  opts: { horizontal?: boolean; extraYAxis?: boolean } = {},
): EChartsOption {
  const names = seriesNames(spec);
  const { base, hasTitle, legendTop, showSeriesLegend } = baseParts(spec);
  const categoryAxis = {
    type: 'category' as const,
    data: spec.rows.map((r) => String(r[0])),
    axisLabel: axisLabelStyle,
    axisLine: axisLineStyle,
  };
  const valueAxis = {
    type: 'value' as const,
    axisLabel: axisLabelStyle,
    splitLine: axisLineStyle,
  };
  return {
    ...base,
    tooltip: categoricalTooltip(spec.rows),
    legend: { ...defaultLegend, show: showSeriesLegend, data: names, top: legendTop },
    grid: { ...defaultGrid, top: hasTitle ? (showSeriesLegend ? 60 : 36) : defaultGrid.top },
    // 条形图（horizontal）：类目轴换到 y 且 inverse，让第一行显示在最上（排名阅读顺序）
    xAxis: opts.horizontal ? valueAxis : categoryAxis,
    yAxis: opts.horizontal
      ? { ...categoryAxis, inverse: true }
      : opts.extraYAxis
        ? [valueAxis, { ...valueAxis, splitLine: { show: false } }]
        : valueAxis,
    series,
  };
}
```

- [ ] **Step 6.2: 分类轴系 builders（6 个小文件）**

`bar.ts`：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { categoricalOption, num, seriesNames } from './shared';

export function buildBar(spec: ChartSpec): EChartsOption {
  return categoricalOption(
    spec,
    seriesNames(spec).map((name, i) => ({
      name,
      type: 'bar' as const,
      data: spec.rows.map((r) => num(r[i + 1])),
    })),
  );
}
```

`line.ts`：同 bar，`type: 'line' as const`，函数名 `buildLine`。

`area.ts`：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { categoricalOption, num, seriesNames } from './shared';

export function buildArea(spec: ChartSpec): EChartsOption {
  return categoricalOption(
    spec,
    seriesNames(spec).map((name, i) => ({
      name,
      type: 'line' as const,
      areaStyle: { opacity: 0.18 },
      data: spec.rows.map((r) => num(r[i + 1])),
    })),
  );
}
```

`stackedBar.ts`：同 bar，series 每项加 `stack: 'total'`，函数名 `buildStackedBar`。

`horizontalBar.ts`：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { categoricalOption, num, seriesNames } from './shared';

export function buildHorizontalBar(spec: ChartSpec): EChartsOption {
  return categoricalOption(
    spec,
    seriesNames(spec).map((name, i) => ({
      name,
      type: 'bar' as const,
      data: spec.rows.map((r) => num(r[i + 1])),
    })),
    { horizontal: true },
  );
}
```

`combo.ts`：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { categoricalOption, num, seriesNames } from './shared';

/** 柱线混合，可选右 Y 轴（rightAxis 指名的系列，通常是 % 比率）。 */
export function buildCombo(spec: ChartSpec): EChartsOption {
  const names = seriesNames(spec);
  const right = new Set(spec.rightAxis ?? []);
  const hasRight = names.some((n) => right.has(n));
  return categoricalOption(
    spec,
    names.map((name, i) => ({
      name,
      type: (spec.seriesTypes?.[i] === 'line' ? 'line' : 'bar') as 'bar' | 'line',
      yAxisIndex: hasRight && right.has(name) ? 1 : 0,
      data: spec.rows.map((r) => num(r[i + 1])),
    })),
    { extraYAxis: hasRight },
  );
}
```

- [ ] **Step 6.3: pie/donut/radar/scatter（4 个文件）**

`pie.ts`（自原 chartSpec.ts 平移，抽 radius 参数）：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { defaultTooltip, defaultLegend } from '@/pages/ai/_shared/chartTheme';
import { baseParts, num } from './shared';

/** 饼/环共用：图例底部横向可滚动、扇区引导线关闭（原因见原 chartSpec.ts 注释）。 */
export function pieOption(spec: ChartSpec, radius: string | [string, string]): EChartsOption {
  const { base, hasTitle } = baseParts(spec);
  return {
    ...base,
    tooltip: { ...defaultTooltip, trigger: 'item' },
    legend: { ...defaultLegend, type: 'scroll', top: 'auto', bottom: 0, left: 'center' },
    series: [
      {
        type: 'pie',
        radius,
        center: hasTitle ? ['50%', '54%'] : ['50%', '48%'],
        label: { show: false },
        labelLine: { show: false },
        data: spec.rows.map((r) => ({ name: String(r[0]), value: num(r[1]) })),
      },
    ],
  };
}

export const buildPie = (spec: ChartSpec): EChartsOption => pieOption(spec, '58%');
```

`donut.ts`：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { pieOption } from './pie';

export const buildDonut = (spec: ChartSpec): EChartsOption => pieOption(spec, ['38%', '58%']);
```

`radar.ts`（原样平移）：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { defaultTooltip, defaultLegend } from '@/pages/ai/_shared/chartTheme';
import { baseParts, num, seriesNames } from './shared';

export function buildRadar(spec: ChartSpec): EChartsOption {
  const names = seriesNames(spec);
  const { base, hasTitle, legendTop, showSeriesLegend } = baseParts(spec);
  return {
    ...base,
    tooltip: { ...defaultTooltip, trigger: 'item' },
    legend: { ...defaultLegend, show: showSeriesLegend, data: names, top: legendTop },
    radar: {
      indicator: spec.rows.map((r) => ({ name: String(r[0]) })),
      center: hasTitle ? ['50%', showSeriesLegend ? '58%' : '56%'] : ['50%', '50%'],
      radius: '60%',
    },
    series: [
      {
        type: 'radar',
        data: names.map((name, i) => ({
          name,
          value: spec.rows.map((r) => num(r[i + 1])),
        })),
      },
    ],
  };
}
```

`scatter.ts`：

```ts
import type { EChartsOption } from 'echarts';
import type { ChartSpec } from '@/services/api/chat/chatDto';
import {
  defaultTooltip,
  defaultGrid,
  axisLabelStyle,
  axisLineStyle,
  axisNameStyle,
} from '@/pages/ai/_shared/chartTheme';
import { baseParts, num } from './shared';

/** 散点：columns 恰好 3 列 [点标签, x, y]（后端 spec 校验保证），单系列。 */
export function buildScatter(spec: ChartSpec): EChartsOption {
  const [, xName, yName] = spec.columns;
  const { base, hasTitle } = baseParts(spec);
  return {
    ...base,
    tooltip: {
      ...defaultTooltip,
      trigger: 'item',
      formatter: (p: unknown) => {
        const { name, value } = p as { name: string; value: [number, number] };
        return [
          `<b>${name}</b>`,
          `${xName}: ${num(value?.[0]).toLocaleString('en-US')}`,
          `${yName}: ${num(value?.[1]).toLocaleString('en-US')}`,
        ].join('<br/>');
      },
    },
    grid: { ...defaultGrid, top: hasTitle ? 36 : defaultGrid.top },
    xAxis: {
      type: 'value',
      name: xName,
      nameTextStyle: axisNameStyle,
      axisLabel: axisLabelStyle,
      splitLine: axisLineStyle,
    },
    yAxis: {
      type: 'value',
      name: yName,
      nameTextStyle: axisNameStyle,
      axisLabel: axisLabelStyle,
      splitLine: axisLineStyle,
    },
    series: [
      {
        type: 'scatter',
        symbolSize: 10,
        data: spec.rows.map((r) => ({ name: String(r[0]), value: [num(r[1]), num(r[2])] })),
      },
    ],
  };
}
```

- [ ] **Step 6.4: `registry.ts`**

```ts
/**
 * 图表类型注册表：type → { label, shape, build }。
 * SUPPORTED / 切换器选项 / chartSpecToOption 全部由此派生——新增类型 = 加一个
 * builder 文件 + 此处一行注册（后端同步 ai/chatbotgraph/chart/spec.py CHART_TYPES）。
 */
import type { EChartsOption } from 'echarts';
import type { ChartSpec, ChartType } from '@/services/api/chat/chatDto';
import { buildBar } from './bar';
import { buildLine } from './line';
import { buildArea } from './area';
import { buildStackedBar } from './stackedBar';
import { buildHorizontalBar } from './horizontalBar';
import { buildPie } from './pie';
import { buildDonut } from './donut';
import { buildRadar } from './radar';
import { buildScatter } from './scatter';
import { buildCombo } from './combo';

/** 数据形状组：同组类型共用同一份二维表语义，可在切换器里互切；跨组不可。 */
export type ChartShape = 'categorical' | 'xy';

export interface ChartTypeDef {
  label: string;
  shape: ChartShape;
  build: (spec: ChartSpec) => EChartsOption;
}

export const CHART_REGISTRY: Record<ChartType, ChartTypeDef> = {
  bar: { label: 'Bar', shape: 'categorical', build: buildBar },
  line: { label: 'Line', shape: 'categorical', build: buildLine },
  area: { label: 'Area', shape: 'categorical', build: buildArea },
  stacked_bar: { label: 'Stacked Bar', shape: 'categorical', build: buildStackedBar },
  horizontal_bar: { label: 'Horizontal Bar', shape: 'categorical', build: buildHorizontalBar },
  pie: { label: 'Pie', shape: 'categorical', build: buildPie },
  donut: { label: 'Donut', shape: 'categorical', build: buildDonut },
  radar: { label: 'Radar', shape: 'categorical', build: buildRadar },
  combo: { label: 'Combo', shape: 'categorical', build: buildCombo },
  scatter: { label: 'Scatter', shape: 'xy', build: buildScatter },
};

export function isSupported(type: string): type is ChartType {
  return type in CHART_REGISTRY;
}

/** 切换器可选类型 = 与当前类型同数据形状组的全部类型。 */
export function compatibleTypes(type: ChartType): ChartType[] {
  const { shape } = CHART_REGISTRY[type];
  return (Object.keys(CHART_REGISTRY) as ChartType[]).filter(
    (t) => CHART_REGISTRY[t].shape === shape,
  );
}

/** 唯一「数据 → ECharts」组合点（原 utils/chartSpec.chartSpecToOption）。 */
export function chartSpecToOption(spec: ChartSpec): EChartsOption {
  return CHART_REGISTRY[spec.type].build(spec);
}
```

- [ ] **Step 6.5: 提交点（待用户确认）** `feat(chat): chart builders module with type registry (10 types)`

### Task 7: 接线迁移（删 chartSpec.ts、组件与消息层改引）

**Files:**
- Delete: `CIOaas-web/src/pages/ai/chat/utils/chartSpec.ts`
- Modify: `CIOaas-web/src/pages/ai/chat/utils/messageReducer.ts:1-3`
- Modify: `CIOaas-web/src/pages/ai/chat/utils/parseChartFences.ts`
- Modify: `CIOaas-web/src/pages/ai/chat/components/ChatChart.tsx`
- Modify: `CIOaas-web/src/services/api/chat/chatEvents.ts`（`isValidChartSpec` 加 export）

- [ ] **Step 7.1: `messageReducer.ts` 自持 MessageBlock**（原从 chartSpec re-export）

```ts
import type { ChartSpec } from '@/services/api/chat/chatDto';

/**
 * 前端 UI 渲染模型：有序段（文本 / 图表）。
 * `id`：流式追加时的稳定 key（本 reducer 生成），历史 block 可缺省回退 index。
 */
export type MessageBlock =
  | { type: 'text'; text: string; id?: string }
  | { type: 'chart'; spec: ChartSpec; id?: string };
```

（删除原第 1-3 行的 `import ... from './chartSpec'` 与 `export type { MessageBlock }`，其余不动。）

- [ ] **Step 7.2: `chatEvents.ts` 导出校验函数**：`function isValidChartSpec` 前加 `export`（实现不动，其注释「强于历史路径」删除——历史路径即将对齐）。

- [ ] **Step 7.3: `parseChartFences.ts` 改引 + 校验对齐流式路径**

```ts
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { isValidChartSpec } from '@/services/api/chat/chatEvents';
import type { MessageBlock } from './messageReducer';

function tryParse(body: string): ChartSpec | null {
  try {
    const parsed: unknown = JSON.parse(body.trim());
    return isValidChartSpec(parsed as ChartSpec | null) ? (parsed as ChartSpec) : null;
  } catch (e) {
    return null;
  }
}
```

（`parseChartFences` 函数体与正则不动；头注释补「校验与流式 chart 事件同源（isValidChartSpec），两路径行为一致」。）

- [ ] **Step 7.4: `ChatChart.tsx` 注册表驱动**（整文件按此替换，Resize 两个 useEffect 与降级逻辑不动）：

```tsx
import React, { useEffect, useRef, useState } from 'react';
import { Select } from 'antd';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { ChartSpec, ChartType } from '@/services/api/chat/chatDto';
import {
  CHART_REGISTRY,
  chartSpecToOption,
  compatibleTypes,
  isSupported,
} from '../utils/charts/registry';
import styles from './ChatChart.less';

const CHART_HEIGHT = 300;

const ChatChart: React.FC<{ spec: ChartSpec }> = ({ spec }) => {
  // …（wrapperRef/echartsRef 与两个 resize useEffect 原样保留）…

  const supported = !!spec && isSupported(spec.type);
  const [type, setType] = useState<ChartType>(supported ? (spec.type as ChartType) : 'bar');

  if (!supported) {
    return <div className={styles.fallback}>暂不支持的图表类型: {spec?.type}</div>;
  }
  let option: EChartsOption;
  try {
    option = chartSpecToOption({ ...spec, type });
  } catch (e) {
    return <div className={styles.fallback}>图表渲染失败</div>;
  }
  const switchable = compatibleTypes(spec.type as ChartType);
  return (
    <div ref={wrapperRef} className={styles.chartWrapper}>
      {switchable.length > 1 && (
        <div className={styles.chartToolbar}>
          <Select<ChartType>
            size="small"
            value={type}
            onChange={setType}
            className={styles.chartTypeSelect}
            options={switchable.map((t) => ({ value: t, label: CHART_REGISTRY[t].label }))}
          />
        </div>
      )}
      <ReactECharts
        ref={echartsRef}
        option={option}
        style={{ width: '100%', height: CHART_HEIGHT }}
        notMerge
        lazyUpdate
      />
    </div>
  );
};

export default ChatChart;
```

要点：切换器选项 = `compatibleTypes(spec.type)`（按**原始** spec.type 的形状组，不随切换漂移）；scatter 组只有自己 → 切换器隐藏；原 `SUPPORTED`/`TYPE_LABEL` 常量删除。

- [ ] **Step 7.5: 删除 `utils/chartSpec.ts`**，然后 grep 确认无残留：

```
grep -rn "utils/chartSpec\|from './chartSpec'\|from '../utils/chartSpec'" CIOaas-web/src
```
Expected: 无结果。

- [ ] **Step 7.6: 提交点（待用户确认）** `refactor(chat): registry-driven ChatChart, drop chartSpec.ts facade`

### Task 8: 前端测试迁移与新增

**Files:**
- Move/rewrite: `CIOaas-web/src/pages/ai/chat/utils/chartSpec.test.ts` → `CIOaas-web/src/pages/ai/chat/utils/charts/registry.test.ts`
- Modify: `CIOaas-web/src/pages/ai/chat/utils/parseChartFences.test.ts`

- [ ] **Step 8.1:** 原 `chartSpec.test.ts` 用例平移进 `registry.test.ts`（断言目标从 `chartSpecToOption` import 路径改到 `./registry`，既有 bar/line/pie/radar 断言全保留），再补新类型：

```ts
import type { ChartSpec } from '@/services/api/chat/chatDto';
import { CHART_REGISTRY, chartSpecToOption, compatibleTypes, isSupported } from './registry';

const cat = (type: ChartSpec['type']): ChartSpec => ({
  type,
  columns: ['Month', 'Revenue', 'Cost'],
  rows: [
    ['Jan', 100, 60],
    ['Feb', 120, null],
  ],
});

describe('registry', () => {
  it('registers all 10 types with labels', () => {
    expect(Object.keys(CHART_REGISTRY)).toHaveLength(10);
    expect(isSupported('scatter')).toBe(true);
    expect(isSupported('heatmap')).toBe(false);
  });

  it('groups switcher types by shape', () => {
    expect(compatibleTypes('bar')).toContain('combo');
    expect(compatibleTypes('bar')).not.toContain('scatter');
    expect(compatibleTypes('scatter')).toEqual(['scatter']);
  });
});

describe('new builders', () => {
  it('area = line series with areaStyle', () => {
    const s = chartSpecToOption(cat('area')).series as any[];
    expect(s[0].type).toBe('line');
    expect(s[0].areaStyle).toBeTruthy();
  });

  it('stacked_bar stacks all series', () => {
    const s = chartSpecToOption(cat('stacked_bar')).series as any[];
    expect(s.every((x) => x.stack === 'total')).toBe(true);
  });

  it('horizontal_bar swaps axes and inverses category', () => {
    const o = chartSpecToOption(cat('horizontal_bar')) as any;
    expect(o.xAxis.type).toBe('value');
    expect(o.yAxis.type).toBe('category');
    expect(o.yAxis.inverse).toBe(true);
  });

  it('donut renders ring radius', () => {
    const s = chartSpecToOption(cat('donut')).series as any[];
    expect(Array.isArray(s[0].radius)).toBe(true);
  });

  it('scatter maps [label,x,y] rows', () => {
    const o = chartSpecToOption({
      type: 'scatter',
      columns: ['Company', 'ARR', 'Growth'],
      rows: [['Acme', 10, 0.4]],
    }) as any;
    expect(o.series[0].type).toBe('scatter');
    expect(o.series[0].data[0]).toEqual({ name: 'Acme', value: [10, 0.4] });
    expect(o.xAxis.name).toBe('ARR');
  });

  it('combo honors seriesTypes and rightAxis', () => {
    const o = chartSpecToOption({
      ...cat('combo'),
      seriesTypes: ['bar', 'line'],
      rightAxis: ['Cost'],
    }) as any;
    expect(o.series[0].type).toBe('bar');
    expect(o.series[1].type).toBe('line');
    expect(o.series[1].yAxisIndex).toBe(1);
    expect(Array.isArray(o.yAxis)).toBe(true);
  });

  it('combo without extras falls back to all bars single axis', () => {
    const o = chartSpecToOption(cat('combo')) as any;
    expect((o.series as any[]).every((x) => x.type === 'bar')).toBe(true);
    expect(Array.isArray(o.yAxis)).toBe(false);
  });
});
```

- [ ] **Step 8.2:** `parseChartFences.test.ts` 补两用例（既有用例不动，import 若引用 chartSpec 则改 messageReducer）：

```ts
it('degrades structurally invalid spec to text (aligned with stream path)', () => {
  const blocks = parseChartFences('```chart\n{"type":"bar","columns":"oops"}\n```');
  expect(blocks[0].type).toBe('text');
});

it('keeps unknown-but-structured type as chart block (ChatChart shows fallback)', () => {
  const blocks = parseChartFences(
    '```chart\n{"type":"heatmap","columns":["a","b"],"rows":[["x",1]]}\n```',
  );
  expect(blocks[0].type).toBe('chart');
});
```

> 注：历史路径对「未知 type」保留 chart block（由 ChatChart 占位降级），与流式一致——后端新版会把未知 type 降级为文本，此用例只覆盖旧库存消息。

- [ ] **Step 8.3: 轻量校验（不跑测试）**：PowerShell 下 `npm run tsc`，对照基线（已知 2 个存量坏文件），确认无新增错误。

- [ ] **Step 8.4: 提交点（待用户确认）** `test(chat): cover chart registry and new builders`

---

## Phase 3 · 契约文档同步

### Task 9: 更新图表契约 spec 文档

**Files:**
- Modify: `docs/superpowers/specs/2026-06-10-chat-chart-design.md`（§4.1 类型清单 + combo/scatter 约定；头部状态行）
- Modify: `docs/superpowers/specs/2026-07-02-chatbot-chart-optimization-design.md`（§7 记录决策：B + 6 类型 + combo 协议确认 + 前端落位 `utils/charts/`；方案 C 同期收尾）

- [ ] **Step 9.1:** 2026-06-10 文档：头部「图表类型 MVP」行改为「类型清单以 `ai/chatbotgraph/chart/spec.py CHART_TYPES` 为单点（2026-07-03 扩展至 10 类，见 2026-07-02-chatbot-chart-optimization-design.md）」；§4.1 JSON 注释补 scatter 3 列与 combo `seriesTypes`/`rightAxis` 约定。
- [ ] **Step 9.2:** optimization 文档 §7 改为「已决策（2026-07-03）」清单。
- [ ] **Step 9.3: 提交点（待用户确认，父仓库）** `docs: sync chart contract docs with type expansion`

---

## Phase 4 · 方案 C 收尾（前端，最后执行）

### Task 10: `useEChartsResize` hook 抽取

**Files:**
- Create: `CIOaas-web/src/pages/ai/_shared/useEChartsResize.ts`
- Modify: `CIOaas-web/src/pages/ai/chat/components/ChatChart.tsx`（两个 resize useEffect → hook）
- Modify: `CIOaas-web/src/pages/ai/llm/components/ChartCard.tsx:47-68`（observer useEffect → hook）

- [ ] **Step 10.1: hook**

```ts
/**
 * ECharts 宽度自适应兜底：echarts-for-react 内置 size-sensor 在本项目复杂布局
 * （fixed Sider + CSS Grid / chat 气泡 flex 滚动容器）下读值不准。原生 ResizeObserver
 * 监听 wrapper 主动 resize()，并在首帧与 resizeOn 变化后的下一帧各兜底一次。
 * （原 ChatChart.tsx / llm ChartCard.tsx 各写一份，2026-07-03 抽公共。）
 */
import { useEffect } from 'react';
import type ReactECharts from 'echarts-for-react';

export function useEChartsResize(
  wrapperRef: React.RefObject<HTMLDivElement | null>,
  echartsRef: React.RefObject<ReactECharts | null>,
  options: { enabled?: boolean; resizeOn?: unknown[] } = {},
): void {
  const { enabled = true, resizeOn = [] } = options;

  useEffect(() => {
    if (!enabled) return undefined;
    const el = wrapperRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const triggerResize = () => {
      const inst = echartsRef.current?.getEchartsInstance?.();
      if (inst) inst.resize();
    };
    const raf = window.requestAnimationFrame(triggerResize);
    const observer = new ResizeObserver(triggerResize);
    observer.observe(el);
    return () => {
      window.cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [enabled]);

  // option 纯变更（类型切换等）不改变容器尺寸，ResizeObserver 覆盖不到 → 下一帧强制重排
  useEffect(() => {
    if (!enabled) return undefined;
    const raf = window.requestAnimationFrame(() => {
      echartsRef.current?.getEchartsInstance?.()?.resize();
    });
    return () => window.cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...resizeOn]);
}
```

- [ ] **Step 10.2:** ChatChart 删除两个 useEffect，改 `useEChartsResize(wrapperRef, echartsRef, { enabled: supported, resizeOn: [type, spec] })`；ChartCard 删除 47-68 行 useEffect，改 `useEChartsResize(wrapperRef, echartsRef, { enabled: !empty })`（其文件头 Resize 注释指向 hook）。
- [ ] **Step 10.3:** `npm run tsc` 对照基线。
- [ ] **Step 10.4: 提交点（待用户确认）** `refactor(ai): extract shared useEChartsResize hook`

### Task 11: ChartCard 提升 `_shared` + chatManage 复用

**Files:**
- Move: `CIOaas-web/src/pages/ai/llm/components/ChartCard.tsx` → `CIOaas-web/src/pages/ai/_shared/ChartCard/index.tsx`
- Create: `CIOaas-web/src/pages/ai/_shared/ChartCard/index.less`（自 `llm/index.less` 抽 chartCard/chartTitleRow/chartTitle/chartExtra/chartEmpty/chartFullWidth 相关样式；llm/index.less 对应类保留给页面栅格布局的引用则不动，仅组件内类迁移）
- Modify: llm 域引用（`grep -rn "components/ChartCard" CIOaas-web/src/pages/ai/llm` 全部改为 `@/pages/ai/_shared/ChartCard`）
- Modify: `CIOaas-web/src/pages/ai/chatManage/index.tsx`（104-128 行 option 工厂保留；225-228 行的自渲染容器换成 `<ChartCard title="…" option={chartOption} height={120} />`）

- [ ] **Step 11.1:** 迁移组件与样式（`styles from '../index.less'` → `./index.less`；先 Read `llm/index.less` 确认待抽类名清单）。
- [ ] **Step 11.2:** llm 页面 import 更新；`npm run tsc` + llm 页 6 张图人工回归提醒记入总结。
- [ ] **Step 11.3:** chatManage 接入 ChartCard（读该页 90-235 行现状后落改；option 工厂 useMemo 不动）。
- [ ] **Step 11.4: 提交点（待用户确认）** `refactor(ai): promote ChartCard to _shared and reuse in chatManage`

---

## 执行期修正记录（2026-07-03，审查发现，以此为准）

1. **Task 3 的双常量设计作废**：git diff 证实原文件里 tool/sql 两轨的 `##图表` 段完全相同（都含「表 / 图二选一」句）——计划把该句误判为 sql 轨专属。已修正为**单一 `CHART_SECTION`**（含该句），两轨共用，无 `SQL_CHART_SECTION`；`test_chart_prompt.py` 断言相应改为两轨都含该句。
2. **Task 6 的 pie 代码块过时 + Task 7.4 丢了切换器适配语义**：并发提交 `985edd21`（fix(chat): disable unfit chart types and wrap pie legend）在本计划编写后落地。已合并其语义：pie/donut 用 plain 换行图例（bottom 8、radius 50%、center 44%/42%，donut 环 ['30%','50%']）；registry 增 `suits?: (spec) => boolean`（pie/donut 单序列且 ≥2 行、radar ≥3 类目、combo ≥2 序列）+ `isSuitable`；ChatChart 切换器列同形状组全部类型、不适合的置灰禁用（title 提示）、初始类型回退首个适合项；985edd21 的 3 个 suitableChartTypes 用例适配进 registry.test.ts。

3. **两轨【展现样式风格】的载体路由与新图表段矛盾（对抗审查发现，已修复）**：原「并排对比 / 排名 / 量纲混杂 → 表格」会把 horizontal_bar / combo 的旗舰场景压回表格。已改为「图表类型按下文【图表】的类型规则选；量纲混杂 → combo 双轴合并、不再因量纲退回表格；仅逐项核对精确数值 / 长明细才用表格」；`chart_prompt.py` combo 行误引的「原『量纲差异大只能分图』」一并修正。

## 验收清单（执行完自查）

1. 后端：`CHART_TYPES` 单点 → 提示词两轨模板行自动包含 10 类型；`##图表：` 在两轨各出现 1 次。
2. 后端：非法 spec（未知 type / 单列 / scatter≠3 列 / 非 dict）降级文本，合法新类型走 Chart 事件。
3. 前端：`chartSpecToOption` 仅存在于 `charts/registry.ts`；`SUPPORTED`/`TYPE_LABEL` 硬编码消失。
4. 前端：切换器 categorical 组 9 类互切、scatter 无切换器；unknown type 占位降级不崩。
5. 契约三处同步：`spec.py` ↔ `chatDto.ts` ↔ `2026-06-10` spec 文档。
6. 方案 C：全仓 ResizeObserver 图表兜底只剩 `useEChartsResize` 一份；chatManage 无自渲染图表容器。
7. **测试未运行**（等用户指令统一跑）：建议命令
   - 后端 `uv run pytest tests/ai/chatbotgraph/chart/ -v`
   - 前端 `npx umi-test src/pages/ai/chat/utils --coverage=false`（PowerShell 先挂 node PATH）
8. **未提交**：提交点已在各 Task 标注，等用户确认后按序提交（消息英文）。
