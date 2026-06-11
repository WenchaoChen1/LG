# AI Chatbot 回答内嵌图表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Git 规则**：本项目 git 操作需用户明确确认，commit 步骤执行前先征得用户同意（不自动 push）。

**Goal:** 让 AI Chatbot 回答按需在文本间穿插图表（柱/折线/雷达/饼），后端流式切出结构化 `event: chart`、前端按类型组合 ECharts，历史可重现。

**Architecture:** LLM 合成时在 markdown 里用 ` ```chart {纯二维表JSON}``` ` fence 内联图表；后端 `ChartFenceStreamParser` 流式状态机切分（文本→`delta`、图表→`event: chart`），`content` 落库存含 fence 原文；前端公共 SSE 收 `chart` 事件、`chartSpecToOption` 把二维表组合成 ECharts、消息升级为 blocks 模型，历史 `parseChartFences` 重现。

**Tech Stack:** Python(FastAPI/LangGraph 已编译图 + astream)、统一 SSE(`event_to_sse_bytes`)、React16/UmiJS3/TS、echarts-for-react。

**Spec:** `docs/superpowers/specs/2026-06-10-chat-chart-design.md`

---

## File Structure

**后端（CIOaas-python）**
- Create `source/chatbot/application/chart_fence_parser.py` — 流式 fence 状态机（纯逻辑）
- Create `tests/chatbot/application/test_chart_fence_parser.py`
- Modify `source/chatbot/application/chat_service.py` — `stream_turn` 正常流分支集成 parser
- Modify `source/chatbot/graph/prompts.py` — `SYNTHESIS_SYSTEM` 加图表指令
- Create/Modify `tests/chatbot/application/test_chat_service.py` — 流式切分断言

**前端（CIOaas-web）**
- Create `src/pages/ai/chat/utils/chartSpec.ts` — `ChartSpec`/`MessageBlock` 类型 + `chartSpecToOption`
- Create `src/pages/ai/chat/utils/chartSpec.test.ts`
- Create `src/pages/ai/chat/utils/parseChartFences.ts` + `.test.ts`
- Modify `src/pages/ai/chat/utils/messageReducer.ts` — `ChatMsg` 改 blocks 模型 + `appendChart`
- Modify `src/pages/ai/chat/utils/messageReducer.test.ts`
- Modify `src/services/api/chat/streamApi.ts` — `onChart` 分发
- Create `src/pages/ai/chat/components/ChatChart.tsx` — ECharts 渲染（含降级）
- Modify `src/pages/ai/chat/components/MessageBubble.tsx` — 渲染 blocks
- Modify `src/pages/ai/chat/hooks/useChatStream.ts` — 接 `onChart` + load 时 `parseChartFences`

**并行性**：后端组（B1→B2→B3）与前端组（F1→F2→F3→F4→F5）相互独立，可两组并行；组内按序。

---

## Task B1: ChartFenceStreamParser（后端流式 fence 状态机）

**Files:**
- Create: `source/chatbot/application/chart_fence_parser.py`
- Test: `tests/chatbot/application/test_chart_fence_parser.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/chatbot/application/test_chart_fence_parser.py
from chatbot.application.chart_fence_parser import (
    ChartFenceStreamParser, TextSegment, ChartSegment, Segment,
)


def _normalize(segs: list[Segment]) -> list[Segment]:
    """合并相邻 TextSegment，便于断言。"""
    out: list[Segment] = []
    for s in segs:
        if isinstance(s, TextSegment) and out and isinstance(out[-1], TextSegment):
            out[-1] = TextSegment(out[-1].text + s.text)
        else:
            out.append(s)
    return out


def _run(chunks: list[str]) -> list[Segment]:
    p = ChartFenceStreamParser()
    out: list[Segment] = []
    for c in chunks:
        out.extend(p.feed(c))
    out.extend(p.flush())
    return _normalize(out)


def test_plain_text_no_fence():
    assert _run(["hello ", "world"]) == [TextSegment("hello world")]


def test_single_chart_between_text():
    body = '{"type":"bar","columns":["q","v"],"rows":[["Q1",1]]}'
    segs = _run([f"intro ```chart\n{body}\n```outro"])
    assert len(segs) == 3
    assert segs[0] == TextSegment("intro ")
    assert isinstance(segs[1], ChartSegment)
    assert segs[1].spec["type"] == "bar"
    assert segs[2] == TextSegment("outro")


def test_fence_split_across_chunks():
    body = '{"type":"line","columns":["q","v"],"rows":[["Q1",2]]}'
    full = f"a ```chart\n{body}\n``` b"
    # 逐字符喂入，最严苛的跨 chunk 切分
    segs = _run(list(full))
    assert [type(s) for s in segs] == [TextSegment, ChartSegment, TextSegment]
    assert segs[1].spec["type"] == "line"


def test_multiple_charts():
    b1 = '{"type":"bar","columns":["a","b"],"rows":[["x",1]]}'
    b2 = '{"type":"pie","columns":["a","b"],"rows":[["x",1]]}'
    segs = _run([f"```chart\n{b1}\n```mid```chart\n{b2}\n```"])
    kinds = [type(s) for s in segs]
    assert kinds == [ChartSegment, TextSegment, ChartSegment]


def test_invalid_json_degrades_to_text():
    segs = _run(["```chart\n{not json}\n```"])
    assert len(segs) == 1 and isinstance(segs[0], TextSegment)
    assert "```chart" in segs[0].text and "{not json}" in segs[0].text


def test_missing_type_degrades_to_text():
    segs = _run(['```chart\n{"columns":["a"],"rows":[]}\n```'])
    assert isinstance(segs[0], TextSegment)


def test_unclosed_fence_on_flush_degrades():
    segs = _run(['tail ```chart\n{"type":"bar"'])
    # tail 文本 + 未闭合内容降级为文本
    assert all(isinstance(s, TextSegment) for s in segs)
    joined = "".join(s.text for s in segs)
    assert "```chart" in joined and '{"type":"bar"' in joined


def test_normal_triple_backtick_codeblock_is_text():
    # 普通 ```python 代码块不应被当成 chart
    segs = _run(["```python\nprint(1)\n```"])
    assert len(segs) == 1 and isinstance(segs[0], TextSegment)
    assert "```python" in segs[0].text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd C:\github-code\LG\CIOaas-python && uv run pytest tests/chatbot/application/test_chart_fence_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: chatbot.application.chart_fence_parser`

- [ ] **Step 3: 实现 parser**

```python
# source/chatbot/application/chart_fence_parser.py
"""流式解析 LLM markdown 输出中的 ```chart fence```，切分为文本段与图表段。

设计见 docs/superpowers/specs/2026-06-10-chat-chart-design.md §6.1。纯逻辑、无 IO。
状态机：TEXT / IN_FENCE；跨 chunk 边界用 _partial_suffix_len hold 可能被切断的标记；
降级：fence 内非法 JSON / 缺 type / 未闭合 → 原文当文本产出，绝不丢内容。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Union

_OPEN = "```chart"
_CLOSE = "```"


@dataclass(frozen=True)
class TextSegment:
    text: str


@dataclass(frozen=True)
class ChartSegment:
    spec: dict


Segment = Union[TextSegment, ChartSegment]


def _partial_suffix_len(buf: str, marker: str) -> int:
    """buf 尾部同时是 marker 非空前缀的最长长度（< len(marker)）。用于 hold 被 chunk 切断的标记。"""
    max_k = min(len(marker) - 1, len(buf))
    for k in range(max_k, 0, -1):
        if marker.startswith(buf[-k:]):
            return k
    return 0


def _try_parse_spec(body: str) -> Optional[dict]:
    try:
        spec = json.loads(body.strip())
    except (ValueError, TypeError):
        return None
    if not isinstance(spec, dict) or "type" not in spec:
        return None
    return spec


class ChartFenceStreamParser:
    """feed(chunk) 增量产出 Segment 列表；流结束调 flush() 收尾。"""

    def __init__(self) -> None:
        self._buf = ""
        self._in_fence = False
        self._fence_body = ""

    def feed(self, chunk: str) -> list[Segment]:
        self._buf += chunk
        return self._drain(final=False)

    def flush(self) -> list[Segment]:
        return self._drain(final=True)

    def _drain(self, final: bool) -> list[Segment]:
        out: list[Segment] = []
        while True:
            if not self._in_fence:
                idx = self._buf.find(_OPEN)
                if idx != -1:
                    if idx > 0:
                        out.append(TextSegment(self._buf[:idx]))
                    self._buf = self._buf[idx + len(_OPEN):]
                    self._in_fence = True
                    self._fence_body = ""
                    continue
                if final:
                    if self._buf:
                        out.append(TextSegment(self._buf))
                    self._buf = ""
                    break
                hold = _partial_suffix_len(self._buf, _OPEN)
                emit = len(self._buf) - hold
                if emit > 0:
                    out.append(TextSegment(self._buf[:emit]))
                    self._buf = self._buf[emit:]
                break
            # in_fence
            idx = self._buf.find(_CLOSE)
            if idx != -1:
                body = self._fence_body + self._buf[:idx]
                self._buf = self._buf[idx + len(_CLOSE):]
                self._in_fence = False
                self._fence_body = ""
                spec = _try_parse_spec(body)
                if spec is not None:
                    out.append(ChartSegment(spec))
                else:
                    out.append(TextSegment(_OPEN + body + _CLOSE))
                continue
            if final:
                out.append(TextSegment(_OPEN + self._fence_body + self._buf))
                self._buf = ""
                self._fence_body = ""
                self._in_fence = False
                break
            hold = _partial_suffix_len(self._buf, _CLOSE)
            emit = len(self._buf) - hold
            self._fence_body += self._buf[:emit]
            self._buf = self._buf[emit:]
            break
        return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd C:\github-code\LG\CIOaas-python && uv run pytest tests/chatbot/application/test_chart_fence_parser.py -v`
Expected: PASS（8 passed）

- [ ] **Step 5: Commit（需用户确认）**

```bash
git add source/chatbot/application/chart_fence_parser.py tests/chatbot/application/test_chart_fence_parser.py
git commit -m "feat(chatbot): add streaming chart-fence parser"
```

---

## Task B2: chat_service.stream_turn 集成 parser

**Files:**
- Modify: `source/chatbot/application/chat_service.py`（正常流分支 line ~63-75）
- Test: `tests/chatbot/application/test_chat_service.py`

- [ ] **Step 1: 写失败测试**（mock astream 产含 fence 文本，断言 delta+chart 事件顺序 + content 落库含 fence）

```python
# tests/chatbot/application/test_chat_service.py（新增/追加）
import json
import pytest
from unittest.mock import patch, MagicMock
from llm.infrastructure.capabilities.text import TextChunk


def _chunks(*deltas):
    async def _gen(*a, **k):
        for d in deltas:
            yield TextChunk(delta=d)
    return _gen


@pytest.mark.asyncio
async def test_stream_turn_splits_chart_event_and_persists_raw():
    from chatbot.application import chat_service

    body = '{"type":"bar","columns":["q","v"],"rows":[["Q1",1]]}'
    fake_graph = MagicMock()
    async def _ainvoke(state):
        return {"synthesis_messages": [{"role": "user", "content": "x"}],
                "tool_results": [], "attribution": []}
    fake_graph.ainvoke = _ainvoke

    appended = {}
    def _append(**kw):
        if kw.get("role") == "assistant":
            appended["content"] = kw.get("content")

    identity = MagicMock(user_id="u1", org_id=None)
    with patch.object(chat_service, "get_chat_graph_app", return_value=fake_graph), \
         patch.object(chat_service.repo, "append_message", side_effect=_append), \
         patch.object(chat_service.llm_db_router, "astream",
                      _chunks("hello ", "```chart\n", body, "\n```", " bye")):
        frames = []
        async for b in chat_service.stream_turn(
            thread_id="t1", question="q", identity=identity,
            end_type="admin", active_company_id=None):
            frames.append(b.decode("utf-8"))

    joined = "".join(frames)
    # 1) 结构化 chart 事件存在
    assert "event: chart" in joined
    assert '"type": "bar"' in joined or '"type":"bar"' in joined
    # 2) 文本走默认 delta（hello / bye）
    assert "hello " in joined and " bye" in joined
    # 3) [DONE] 收尾
    assert "[DONE]" in joined
    # 4) content 落库含 fence 原文
    assert "```chart" in appended["content"] and body in appended["content"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd C:\github-code\LG\CIOaas-python && uv run pytest tests/chatbot/application/test_chat_service.py::test_stream_turn_splits_chart_event_and_persists_raw -v`
Expected: FAIL（当前 astream chunk 直接 `chunk_to_sse_bytes`，无 `event: chart`）

- [ ] **Step 3: 修改 stream_turn 正常流分支**

`chat_service.py` 顶部 import 增补：

```python
from llm.infrastructure.llm_router.sse import (
    chunk_to_sse_bytes,
    done_marker,
    event_to_sse_bytes,
)
from llm.infrastructure.capabilities.text import TextChunk
from chatbot.application.chart_fence_parser import (
    ChartFenceStreamParser, TextSegment, ChartSegment,
)
```

把正常流分支（现 `messages = result["synthesis_messages"]` 起到函数末尾的 astream 循环）替换为：

```python
    messages = result["synthesis_messages"]
    buf: list[str] = []
    parser = ChartFenceStreamParser()

    def _seg_to_sse(seg) -> bytes:
        if isinstance(seg, ChartSegment):
            return event_to_sse_bytes("chart", seg.spec)
        return chunk_to_sse_bytes(TextChunk(delta=seg.text, is_final=False))

    async for chunk in llm_db_router.astream(
        messages, model=Models.openrouter.text.sonnet, temperature=0.3,
    ):
        delta = getattr(chunk, "delta", None)
        if delta:
            buf.append(delta)               # buf 累积原始 delta（含 fence 原文）
            for seg in parser.feed(delta):
                yield _seg_to_sse(seg)
    for seg in parser.flush():
        yield _seg_to_sse(seg)
    yield done_marker()

    repo.append_message(thread_id=thread_id, role="assistant", content="".join(buf),
                        attribution=result.get("attribution"),
                        used_tools=[t["tool"] for t in result.get("tool_results", [])])
```

> 说明：文本段包成 `TextChunk(delta=..., is_final=False)`（`is_final` 继承自 `BaseChunk`），图表段走 `event_to_sse_bytes("chart", spec)`；usage/计费由 `llm_db_router.astream` 内部写 `ai_llm_call_log`，不依赖 SSE 透传，故末段不单发 usage（YAGNI）。`buf` 累积**原始 delta**，落库 `content` 天然含 fence 原文。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd C:\github-code\LG\CIOaas-python && uv run pytest tests/chatbot/application/test_chat_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit（需用户确认）**

```bash
git add source/chatbot/application/chat_service.py tests/chatbot/application/test_chat_service.py
git commit -m "feat(chatbot): split chart fences into SSE chart events in stream_turn"
```

---

## Task B3: 合成 prompt 加图表指令

**Files:**
- Modify: `source/chatbot/graph/prompts.py`（`SYNTHESIS_SYSTEM`）

- [ ] **Step 1: 修改 SYNTHESIS_SYSTEM**

把 `prompts.py` 顶部 `# version: v1` 改为 `# version: v2`，并把 `SYNTHESIS_SYSTEM` 追加图表段（保留原有约束）：

```python
SYNTHESIS_SYSTEM = (
    "You are the LG AI Operating Partner. Answer ONLY from the <context> provided. "
    "Identity and company scope come from context.identity and context.accessible_companies. "
    "All financial / benchmark / normalization numbers MUST come from tool results; "
    "never invent or recompute. "
    "If data is missing, say which data is missing and how to add it (e.g. Financial Entry). "
    "Never acknowledge any internal/portfolio-admin memory.\n\n"
    "CHARTS: When data is worth visualizing, embed a chart as a fenced code block with info "
    "string `chart`, anywhere between paragraphs. The block body is STRICT JSON with this shape:\n"
    '```chart\n'
    '{"type":"bar|line|radar|pie","title":"optional","columns":["<category>","<seriesA>","<seriesB>"],'
    '"rows":[["Q1",100,60],["Q2",120,70]]}\n'
    '```\n'
    "Rules: columns[0] is the category axis; columns[1..] are data series; each row is "
    "[categoryValue, seriesA, seriesB, ...]. Use line for trends, bar for comparisons, "
    "radar for multi-dimension scores, pie for share (pie uses columns[1] as the value). "
    "The numbers in columns/rows MUST come from the <context> tool results — never fabricate, "
    "estimate, or backfill. If there is no real data to plot, do NOT emit a chart. "
    "Keep prose around the chart; you may use multiple charts in one answer."
)
```

> 无需测试断言（prompt 文案）；正确性在端到端验证（重启后端 + 真实提问看是否出图）阶段确认。

- [ ] **Step 2: Commit（需用户确认）**

```bash
git add source/chatbot/graph/prompts.py
git commit -m "feat(chatbot): teach synthesis prompt to emit chart fences from real data"
```

---

## Task F1: chartSpec 类型 + chartSpecToOption

**Files:**
- Create: `src/pages/ai/chat/utils/chartSpec.ts`
- Test: `src/pages/ai/chat/utils/chartSpec.test.ts`

- [ ] **Step 1: 写失败测试**

```ts
// src/pages/ai/chat/utils/chartSpec.test.ts
import { chartSpecToOption } from './chartSpec';
import type { ChartSpec } from './chartSpec';

const bar: ChartSpec = { type: 'bar', title: 'T', columns: ['q', '营收', '成本'], rows: [['Q1', 100, 60], ['Q2', 120, 70]] };

test('bar 组合 xAxis 分类 + 多 series', () => {
  const opt: any = chartSpecToOption(bar);
  expect(opt.xAxis.data).toEqual(['Q1', 'Q2']);
  expect(opt.series).toHaveLength(2);
  expect(opt.series[0]).toMatchObject({ name: '营收', type: 'bar', data: [100, 120] });
  expect(opt.series[1].data).toEqual([60, 70]);
});

test('line 复用同结构、type=line', () => {
  const opt: any = chartSpecToOption({ ...bar, type: 'line' });
  expect(opt.series[0].type).toBe('line');
});

test('radar indicator 来自首列、series 来自其余列', () => {
  const opt: any = chartSpecToOption({ type: 'radar', columns: ['维度', '本公司'], rows: [['增长', 82], ['盈利', 65]] });
  expect(opt.radar.indicator).toEqual([{ name: '增长' }, { name: '盈利' }]);
  expect(opt.series[0].type).toBe('radar');
  expect(opt.series[0].data[0]).toMatchObject({ name: '本公司', value: [82, 65] });
});

test('pie 取第二列为值', () => {
  const opt: any = chartSpecToOption({ type: 'pie', columns: ['名', '占比'], rows: [['A', 30], ['B', 70]] });
  expect(opt.series[0].type).toBe('pie');
  expect(opt.series[0].data).toEqual([{ name: 'A', value: 30 }, { name: 'B', value: 70 }]);
});

test('非有限数值降级为 0', () => {
  const opt: any = chartSpecToOption({ type: 'bar', columns: ['q', 'v'], rows: [['Q1', 'N/A' as any]] });
  expect(opt.series[0].data).toEqual([0]);
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd C:\github-code\LG\CIOaas-web && npm test -- src/pages/ai/chat/utils/chartSpec.test.ts`
Expected: FAIL — 找不到模块 `./chartSpec`
（注：若 `umi test` 基架报缺 `tests/PuppeteerEnvironment` 等 pre-existing 问题，先按仓库现有方式修复测试基架或用项目约定的单测命令；类型正确性可用 `npm run tsc` 兜底。）

- [ ] **Step 3: 实现 chartSpec.ts**

```ts
// src/pages/ai/chat/utils/chartSpec.ts
import type { EChartsOption } from 'echarts';
import {
  CHART_PALETTE,
  defaultTooltip,
  defaultGrid,
  defaultLegend,
  axisLabelStyle,
  axisLineStyle,
} from '@/pages/ai/_shared/chartTheme';

export type ChartType = 'bar' | 'line' | 'radar' | 'pie';

export interface ChartSpec {
  type: ChartType;
  title?: string;
  columns: string[];
  rows: Array<Array<string | number>>;
}

export type MessageBlock =
  | { type: 'text'; text: string }
  | { type: 'chart'; spec: ChartSpec };

function num(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

export function chartSpecToOption(spec: ChartSpec): EChartsOption {
  const { type, title, columns, rows } = spec;
  const seriesNames = columns.slice(1);
  const titleOpt = title ? { title: { text: title, left: 'center' as const, textStyle: { fontSize: 13 } } } : {};
  const base = { color: CHART_PALETTE as string[], ...titleOpt };

  if (type === 'pie') {
    return {
      ...base,
      tooltip: { ...defaultTooltip, trigger: 'item' },
      legend: { ...defaultLegend },
      series: [{ type: 'pie', radius: '60%', data: rows.map((r) => ({ name: String(r[0]), value: num(r[1]) })) }],
    };
  }

  if (type === 'radar') {
    return {
      ...base,
      tooltip: { ...defaultTooltip, trigger: 'item' },
      legend: { ...defaultLegend, data: seriesNames },
      radar: { indicator: rows.map((r) => ({ name: String(r[0]) })) },
      series: [{ type: 'radar', data: seriesNames.map((name, i) => ({ name, value: rows.map((r) => num(r[i + 1])) })) }],
    };
  }

  // bar | line
  return {
    ...base,
    tooltip: defaultTooltip,
    legend: { ...defaultLegend, data: seriesNames },
    grid: defaultGrid,
    xAxis: { type: 'category', data: rows.map((r) => String(r[0])), axisLabel: axisLabelStyle, axisLine: axisLineStyle },
    yAxis: { type: 'value', axisLabel: axisLabelStyle, splitLine: axisLineStyle },
    series: seriesNames.map((name, i) => ({ name, type, data: rows.map((r) => num(r[i + 1])) })),
  };
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd C:\github-code\LG\CIOaas-web && npm test -- src/pages/ai/chat/utils/chartSpec.test.ts`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit（需用户确认）**

```bash
git add src/pages/ai/chat/utils/chartSpec.ts src/pages/ai/chat/utils/chartSpec.test.ts
git commit -m "feat(chat): add chart spec types and chartSpecToOption (2D table -> ECharts)"
```

---

## Task F2: parseChartFences（历史 content → blocks）

**Files:**
- Create: `src/pages/ai/chat/utils/parseChartFences.ts`
- Test: `src/pages/ai/chat/utils/parseChartFences.test.ts`

- [ ] **Step 1: 写失败测试**

```ts
// src/pages/ai/chat/utils/parseChartFences.test.ts
import { parseChartFences } from './parseChartFences';

test('纯文本 → 单个 text block', () => {
  expect(parseChartFences('hello')).toEqual([{ type: 'text', text: 'hello' }]);
});

test('文本+图表+文本 → 3 blocks', () => {
  const body = '{"type":"bar","columns":["q","v"],"rows":[["Q1",1]]}';
  const blocks = parseChartFences('a\n```chart\n' + body + '\n```\nb');
  expect(blocks.map((b) => b.type)).toEqual(['text', 'chart', 'text']);
  expect((blocks[1] as any).spec.type).toBe('bar');
});

test('非法 JSON 的 fence 降级为 text', () => {
  const blocks = parseChartFences('```chart\n{bad}\n```');
  expect(blocks).toHaveLength(1);
  expect(blocks[0].type).toBe('text');
  expect((blocks[0] as any).text).toContain('```chart');
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd C:\github-code\LG\CIOaas-web && npm test -- src/pages/ai/chat/utils/parseChartFences.test.ts`
Expected: FAIL — 找不到模块

- [ ] **Step 3: 实现 parseChartFences.ts**

```ts
// src/pages/ai/chat/utils/parseChartFences.ts
import type { ChartSpec, MessageBlock } from './chartSpec';

const FENCE_RE = /```chart[ \t]*\r?\n?([\s\S]*?)```/g;

function tryParse(body: string): ChartSpec | null {
  try {
    const o = JSON.parse(body.trim());
    if (o && typeof o === 'object' && typeof (o as any).type === 'string') return o as ChartSpec;
    return null;
  } catch (e) {
    return null;
  }
}

/** 把含 ```chart fence``` 的 markdown 原文切成有序 blocks；非法 fence 降级为 text。 */
export function parseChartFences(content: string): MessageBlock[] {
  const blocks: MessageBlock[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  FENCE_RE.lastIndex = 0;
  // eslint-disable-next-line no-cond-assign
  while ((m = FENCE_RE.exec(content)) !== null) {
    if (m.index > last) blocks.push({ type: 'text', text: content.slice(last, m.index) });
    const spec = tryParse(m[1]);
    blocks.push(spec ? { type: 'chart', spec } : { type: 'text', text: m[0] });
    last = FENCE_RE.lastIndex;
  }
  if (last < content.length) blocks.push({ type: 'text', text: content.slice(last) });
  return blocks.length ? blocks : [{ type: 'text', text: content }];
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd C:\github-code\LG\CIOaas-web && npm test -- src/pages/ai/chat/utils/parseChartFences.test.ts`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit（需用户确认）**

```bash
git add src/pages/ai/chat/utils/parseChartFences.ts src/pages/ai/chat/utils/parseChartFences.test.ts
git commit -m "feat(chat): parse chart fences from history content into blocks"
```

---

## Task F3: messageReducer 升级 blocks 模型

**Files:**
- Modify: `src/pages/ai/chat/utils/messageReducer.ts`
- Test: `src/pages/ai/chat/utils/messageReducer.test.ts`

- [ ] **Step 1: 改测试（断言 blocks + appendChart）**

```ts
// src/pages/ai/chat/utils/messageReducer.test.ts（替换/补充）
import { chatReducer, initialChatState } from './messageReducer';
import type { ChartSpec } from './chartSpec';

const spec: ChartSpec = { type: 'bar', columns: ['q', 'v'], rows: [['Q1', 1]] };

test('appendDelta 累积到末尾 text block', () => {
  let s = chatReducer(initialChatState, { type: 'startAssistant' });
  s = chatReducer(s, { type: 'appendDelta', delta: 'he' });
  s = chatReducer(s, { type: 'appendDelta', delta: 'llo' });
  expect(s.messages[0].blocks).toEqual([{ type: 'text', text: 'hello' }]);
});

test('appendChart 在 text 后追加 chart block', () => {
  let s = chatReducer(initialChatState, { type: 'startAssistant' });
  s = chatReducer(s, { type: 'appendDelta', delta: 'intro' });
  s = chatReducer(s, { type: 'appendChart', spec });
  s = chatReducer(s, { type: 'appendDelta', delta: 'outro' });
  expect(s.messages[0].blocks.map((b) => b.type)).toEqual(['text', 'chart', 'text']);
});

test('addUser 存为单 text block', () => {
  const s = chatReducer(initialChatState, { type: 'addUser', content: 'hi' });
  expect(s.messages[0]).toEqual({ role: 'user', blocks: [{ type: 'text', text: 'hi' }] });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd C:\github-code\LG\CIOaas-web && npm test -- src/pages/ai/chat/utils/messageReducer.test.ts`
Expected: FAIL（`blocks` 不存在 / `appendChart` 未处理）

- [ ] **Step 3: 改 messageReducer.ts**

```ts
// src/pages/ai/chat/utils/messageReducer.ts
import type { ChartSpec, MessageBlock } from './chartSpec';

export type { MessageBlock };

export interface ChatMsg {
  role: 'user' | 'assistant';
  blocks: MessageBlock[];
}
export interface ChatState {
  messages: ChatMsg[];
  streaming: boolean;
  error: string | null;
}

export const initialChatState: ChatState = { messages: [], streaming: false, error: null };

export type ChatAction =
  | { type: 'addUser'; content: string }
  | { type: 'startAssistant' }
  | { type: 'appendDelta'; delta: string }
  | { type: 'appendChart'; spec: ChartSpec }
  | { type: 'finish' }
  | { type: 'error'; message: string }
  | { type: 'load'; messages: ChatMsg[] };

function updateLastAssistant(state: ChatState, fn: (blocks: MessageBlock[]) => MessageBlock[]): ChatState {
  const msgs = state.messages.slice();
  const last = msgs[msgs.length - 1];
  if (last && last.role === 'assistant') {
    msgs[msgs.length - 1] = { ...last, blocks: fn(last.blocks) };
  }
  return { ...state, messages: msgs };
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'addUser':
      return { ...state, messages: [...state.messages, { role: 'user', blocks: [{ type: 'text', text: action.content }] }] };
    case 'startAssistant':
      return { ...state, streaming: true, error: null, messages: [...state.messages, { role: 'assistant', blocks: [] }] };
    case 'appendDelta':
      return updateLastAssistant(state, (blocks) => {
        const out = blocks.slice();
        const lastBlock = out[out.length - 1];
        if (lastBlock && lastBlock.type === 'text') {
          out[out.length - 1] = { type: 'text', text: lastBlock.text + action.delta };
        } else {
          out.push({ type: 'text', text: action.delta });
        }
        return out;
      });
    case 'appendChart':
      return updateLastAssistant(state, (blocks) => [...blocks, { type: 'chart', spec: action.spec }]);
    case 'finish':
      return { ...state, streaming: false };
    case 'error':
      return { ...state, streaming: false, error: action.message };
    case 'load':
      return { ...state, messages: action.messages };
    default:
      return state;
  }
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd C:\github-code\LG\CIOaas-web && npm test -- src/pages/ai/chat/utils/messageReducer.test.ts`
Expected: PASS

- [ ] **Step 5: Commit（需用户确认）**

```bash
git add src/pages/ai/chat/utils/messageReducer.ts src/pages/ai/chat/utils/messageReducer.test.ts
git commit -m "feat(chat): upgrade message model to ordered blocks (text/chart)"
```

---

## Task F4: streamApi 分发 chart 事件

**Files:**
- Modify: `src/services/api/chat/streamApi.ts`

- [ ] **Step 1: 改 streamApi.ts**

import 增补：

```ts
import type { ChartSpec } from '@/pages/ai/chat/utils/chartSpec';
```

`StreamChatCallbacks` 增补 `onChart`：

```ts
export interface StreamChatCallbacks {
  onDelta: (delta: string) => void;
  onThreadId?: (threadId: string) => void;
  onNeedsPick?: (hint: string) => void;
  onBlocked?: (reason: string) => void;
  onChart?: (spec: ChartSpec) => void;
  onDone?: (finishReason?: string) => void;
  onError?: (err: Error) => void;
}
```

在 `handleFrame` 的 `blocked` 分支之后、默认文本分支之前插入：

```ts
    if (event === 'chart') {
      const spec = parseJson<ChartSpec>(data);
      if (spec) cb.onChart?.(spec);
      return;
    }
```

- [ ] **Step 2: 改/加测试**

```ts
// src/services/api/chat/streamApi.test.ts（追加用例）
test('event: chart 分发到 onChart', () => {
  // 复用本文件已有的 streamSSE mock 模式（参考现有 thread/needs_pick 用例）：
  // 喂入 `event: chart\ndata: {"type":"bar","columns":["q","v"],"rows":[["Q1",1]]}\n\n`
  // 断言 onChart 收到的 spec.type === 'bar'
});
```

> 按本文件既有 mock 写法补全该用例（现有用例已 mock 了 fetch/stream，照搬其结构，注入一帧 chart 事件）。

- [ ] **Step 3: 跑类型 + 测试**

Run: `cd C:\github-code\LG\CIOaas-web && npm run tsc && npm test -- src/services/api/chat/streamApi.test.ts`
Expected: tsc 本文件零错误；测试 PASS

- [ ] **Step 4: Commit（需用户确认）**

```bash
git add src/services/api/chat/streamApi.ts src/services/api/chat/streamApi.test.ts
git commit -m "feat(chat): dispatch SSE chart event to onChart callback"
```

---

## Task F5: ChatChart 组件 + MessageBubble 渲染 blocks + useChatStream 接线

**Files:**
- Create: `src/pages/ai/chat/components/ChatChart.tsx`
- Modify: `src/pages/ai/chat/components/MessageBubble.tsx`
- Modify: `src/pages/ai/chat/hooks/useChatStream.ts`

- [ ] **Step 1: 创建 ChatChart.tsx（含降级）**

```tsx
// src/pages/ai/chat/components/ChatChart.tsx
import React from 'react';
import ReactECharts from 'echarts-for-react';
import type { ChartSpec } from '../utils/chartSpec';
import { chartSpecToOption } from '../utils/chartSpec';

const SUPPORTED = ['bar', 'line', 'radar', 'pie'];

const ChatChart: React.FC<{ spec: ChartSpec }> = ({ spec }) => {
  if (!spec || !SUPPORTED.includes(spec.type)) {
    return <div style={{ color: '#65758b', fontSize: 12 }}>暂不支持的图表类型: {spec?.type}</div>;
  }
  let option;
  try {
    option = chartSpecToOption(spec);
  } catch (e) {
    return <div style={{ color: '#65758b', fontSize: 12 }}>图表渲染失败</div>;
  }
  return <ReactECharts option={option} style={{ height: 300, width: '100%' }} notMerge lazyUpdate />;
};

export default ChatChart;
```

- [ ] **Step 2: 改 MessageBubble.tsx 渲染 blocks**

```tsx
// src/pages/ai/chat/components/MessageBubble.tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMsg } from '../utils/messageReducer';
import ChatChart from './ChatChart';
import styles from './MessageBubble.less';

const MessageBubble: React.FC<{ msg: ChatMsg }> = ({ msg }) => {
  if (msg.role === 'user') {
    const text = msg.blocks.map((b) => (b.type === 'text' ? b.text : '')).join('');
    return <div className={styles.user}><span>{text}</span></div>;
  }
  return (
    <div className={styles.assistant}>
      <div className={styles.markdown}>
        {msg.blocks.map((b, i) =>
          b.type === 'text' ? (
            <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>{b.text || ' '}</ReactMarkdown>
          ) : (
            <ChatChart key={i} spec={b.spec} />
          ),
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
```

- [ ] **Step 3: 改 useChatStream.ts（接 onChart + load 时 parseChartFences）**

import 增补：

```ts
import { parseChartFences } from '../utils/parseChartFences';
```

`loadThread` 的 `dispatch({ type: 'load', ... })` 改为按 role 构造 blocks：

```ts
      dispatch({
        type: 'load',
        messages: msgs
          .filter((m) => m.role !== 'system')
          .map((m) =>
            m.role === 'assistant'
              ? { role: 'assistant' as const, blocks: parseChartFences(m.content) }
              : { role: 'user' as const, blocks: [{ type: 'text' as const, text: m.content }] },
          ),
      });
```

`send` 的 `streamChat` 回调对象增补 `onChart`：

```ts
          onChart: (spec) => {
            if (alive()) dispatch({ type: 'appendChart', spec });
          },
```

- [ ] **Step 4: 跑类型检查**

Run: `cd C:\github-code\LG\CIOaas-web && npm run tsc`
Expected: 本任务触碰文件零类型错误（仓库既有 baseline 报错与本任务无关）

- [ ] **Step 5: Commit（需用户确认）**

```bash
git add src/pages/ai/chat/components/ChatChart.tsx src/pages/ai/chat/components/MessageBubble.tsx src/pages/ai/chat/hooks/useChatStream.ts
git commit -m "feat(chat): render message blocks with inline ECharts charts"
```

---

## Self-Review

**Spec coverage：**
- §3 数据来源（LLM+真实数据）→ B3 prompt 红线 ✓
- §3 载体 chart fence → B1 parser + B3 prompt ✓
- §4.1 二维表数据格式 → F1 `ChartSpec` + `chartSpecToOption` ✓
- §4.2 `event: chart` 帧 → B2 `event_to_sse_bytes("chart", spec)` ✓
- §5 端到端数据流 → B1+B2（后端切分）+ F4+F5（前端渲染）✓
- §6.1 ChartFenceStreamParser（fence/跨 chunk/降级）→ B1 ✓
- §6.2 stream_turn 集成 + buf 含 fence 落库 → B2 ✓
- §6.3 prompt → B3 ✓
- §7.1 onChart → F4 ✓；§7.2 blocks 模型 → F3 ✓；§7.3 chartSpecToOption → F1 ✓；§7.4 parseChartFences → F2 ✓；§7.5 渲染组件 → F5 ✓
- §8 错误降级 → B1（JSON/未闭合）+ F1（num 兜底）+ F5（ChatChart try/catch + 不支持 type）✓
- §9 持久化（content 含 fence、不改 DB）→ B2 buf 累积原文 ✓
- §10 测试要点 → B1/B2/F1/F2/F3 单测，F4/F5 类型+用例 ✓

**Placeholder scan：** F4 Step2 / F5 无完整测试代码块的项已注明"按既有 mock 写法补全"——这是因复用现有 test 基架结构，非逻辑占位；其余步骤均含完整代码。

**Type consistency：** `ChartSpec`/`MessageBlock` 统一定义在 `chartSpec.ts`，被 parseChartFences/messageReducer/streamApi/组件复用；后端 `ChartSegment.spec` 为 dict，与前端 `ChartSpec` 字段（type/title/columns/rows）一致；`chartSpecToOption`/`parseChartFences`/`appendChart` 命名前后一致。
