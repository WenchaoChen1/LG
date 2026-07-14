# AI Chatbot 实时工具步骤 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让聊天取数阶段的工具步骤卡片实时逐个出现，并支持「进行中(running) → 完成(ok/error)」两态。

**Architecture:** 方案 A —— `chat_turn` 对 chat_graph 的驱动从 `ainvoke` 换成 `astream(stream_mode=["custom","values"])`；`retrieve_node` 在节点主体取 LangGraph `get_stream_writer()` 并注入工具闭包，工具执行前后各推一帧 `tool_step` 原始信号；`chat_turn` 把 custom 帧转成 `ToolStep` 领域事件（拼英文文案），values 末帧作为最终 state 进入原 synthesis 流式成文。synthesis、落库、停止/续流语义全部不变。

**Tech Stack:** Python 3.12 / LangGraph 0.3.34 / FastAPI SSE；React 16 / TypeScript / UmiJS / Ant Design。

**关联文档:** spec `docs/superpowers/specs/2026-06-26-chatbot-realtime-tool-steps-design.md`

**Git 约定（项目强制）:** 子项目 `CIOaas-python` / `CIOaas-web` 是独立 git 仓库，各自提交；提交消息用**英文** Conventional Commits；`git add`/`commit` 前需用户确认，**不自动 push**。下文 commit 步骤是给执行者的动作，执行时遵守上述约定。

**测试约定:** 后端用 pytest（`asyncio_mode=auto`，LLM/图调用必须 mock）。前端单测基架已知损坏（`docs` / MEMORY 记录），**前端不写 jest 用例**，改用 `npm run tsc` 类型校验 + 人工 review 兜底。

---

## File Structure

**后端（CIOaas-python）**
- Modify: `source/chatbot/application/chat_events.py` — `ToolStep` 加 `step_id`、`status` 默认 `running`
- Modify: `source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py` — `_Accumulator.next_step_id`、`_dispatch_tools` 注入 writer + 两态发射、retrieve_node 主体取 writer + 建 id→name 映射
- Modify: `source/chatbot/application/chat_turn.py` — graph 驱动改 astream 双流分流、新增 `_custom_to_tool_step`、删旧一次性下发循环
- Test: `tests/ai/chatbotgraph/test_retrieval_agent.py`（已存在，追加用例）
- Test: `tests/chatbot/application/test_chat_turn.py`（不存在则新建）

**前端（CIOaas-web）**
- Modify: `src/services/api/chat/chatEvents.ts` — `ToolStepPayload`/`onToolStep` 加 `step_id`
- Modify: `src/pages/ai/chat/utils/messageReducer.ts` — `ToolStepInfo` 加 `stepId`、`appendToolStep` 改 upsert
- Modify: `src/pages/ai/chat/components/ToolStepsCard.tsx` — 按 status 渲染三态图标
- Modify: `src/pages/ai/chat/components/ToolStepsCard.less` — running spinner / error 灰显样式
- （`useChatStream.ts` 已注册 `onToolStep`，回调签名透传新字段，无需改逻辑）

---

## Task 1: Spike —— 验证 custom stream 通路

**Files:** 无（临时验证脚本，验证后删除）

- [ ] **Step 1: 写临时验证脚本**

新建 `CIOaas-python/_spike_custom_stream.py`：

```python
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from typing import TypedDict


class S(TypedDict):
    x: int


async def node(state: S) -> dict:
    writer = get_stream_writer()
    writer({"kind": "tool_step", "step_id": "1", "tool": "demo", "status": "running"})
    writer({"kind": "tool_step", "step_id": "1", "tool": "demo", "status": "ok"})
    return {"x": state["x"] + 1}


async def main() -> None:
    g = StateGraph(S)
    g.add_node("node", node)
    g.add_edge(START, "node")
    g.add_edge("node", END)
    app = g.compile()
    customs, values = [], []
    async for mode, chunk in app.astream({"x": 0}, stream_mode=["custom", "values"]):
        if mode == "custom":
            customs.append(chunk)
        elif mode == "values":
            values.append(chunk)
    print("CUSTOM:", customs)
    print("VALUES last:", values[-1])


asyncio.run(main())
```

- [ ] **Step 2: 运行 spike**

Run（在 `CIOaas-python/` 下，已激活虚拟环境）: `python _spike_custom_stream.py`
Expected:
```
CUSTOM: [{'kind': 'tool_step', 'step_id': '1', 'tool': 'demo', 'status': 'running'}, {'kind': 'tool_step', 'step_id': '1', 'tool': 'demo', 'status': 'ok'}]
VALUES last: {'x': 1}
```

- [ ] **Step 3: 删除 spike 脚本**

确认通过后删除：`rm CIOaas-python/_spike_custom_stream.py`

> 若 CUSTOM 为空（writer 未冒泡），停止本计划，回到 spec §9 退路（方案 C：retrieve_node 用 `agent.astream` 解析 updates）。正常情况此用法是 LangGraph 官方标准，应通过。

无 commit（验证性步骤）。

---

## Task 2: 后端事件契约 —— ToolStep 加 step_id + 两态

**Files:**
- Modify: `source/chatbot/application/chat_events.py:60-71`
- Test: `tests/chatbot/application/test_chat_events.py`（不存在则新建）

- [ ] **Step 1: 写失败测试**

在 `tests/chatbot/application/test_chat_events.py` 追加（无文件则新建，含 import）：

```python
from chatbot.application.chat_events import ToolStep


def test_tool_step_running_serializes_step_id_and_status():
    name, payload = ToolStep(step_id="3", label="Querying financial data",
                             tool="query_financial", status="running").sse_event()
    assert name == "tool_step"
    assert payload == {
        "step_id": "3",
        "label": "Querying financial data",
        "tool": "query_financial",
        "status": "running",
    }


def test_tool_step_status_defaults_to_running():
    assert ToolStep(step_id="1", label="x", tool="t").status == "running"
```

- [ ] **Step 2: 运行测试确认失败**

Run（`CIOaas-python/`）: `pytest tests/chatbot/application/test_chat_events.py -v`
Expected: FAIL（`ToolStep` 缺 `step_id` 参数 / status 默认值不符）

- [ ] **Step 3: 改 ToolStep dataclass**

把 `source/chatbot/application/chat_events.py` 的 `ToolStep` 改为：

```python
@dataclass(frozen=True)
class ToolStep(_ChatEvent):
    """工具步骤卡片：取数阶段每个工具调用实时下发两帧（running → ok/error）。

    同一工具调用的两帧共享 ``step_id``，前端据此把"进行中"原地更新为"完成"。``label`` 由
    后端代码生成（英文友好描述 + 公司名），``tool`` 给前端选图标，``status`` 取
    running / ok / error。
    """

    _SSE_NAME: ClassVar[str] = "tool_step"
    step_id: str
    label: str
    tool: str
    status: str = "running"
```

- [ ] **Step 4: 运行测试确认通过**

Run（`CIOaas-python/`）: `pytest tests/chatbot/application/test_chat_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C CIOaas-python add source/chatbot/application/chat_events.py tests/chatbot/application/test_chat_events.py
git -C CIOaas-python commit -m "feat(chatbot): add step_id and two-state status to ToolStep event"
```

---

## Task 3: retrieve_node —— writer 注入工具闭包 + 两态发射

**Files:**
- Modify: `source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py`
- Test: `tests/ai/chatbotgraph/test_retrieval_agent.py`（已存在，追加用例）

- [ ] **Step 1: 写失败测试**

在 `tests/ai/chatbotgraph/test_retrieval_agent.py` 追加：

```python
import pytest

from ai.chatbotgraph.retrieval_agents import retrieval_agent as ra


@pytest.mark.asyncio
async def test_dispatch_tools_emit_running_then_ok(monkeypatch):
    frames = []

    async def fake_dispatch(name, args):
        return {"ok": True, "row_count": 2, "source": name}

    acc = ra._Accumulator()
    id_to_name = {"c1": "Acme"}
    tools = ra._dispatch_tools(fake_dispatch, acc, frames.append, id_to_name)
    # 取 query_financial 工具直接执行其 coroutine
    tool = next(t for t in tools if t.name == "query_financial")
    summary = await tool.coroutine(company_id="c1", from_date="2025-01-01")

    assert len(frames) == 2
    assert frames[0]["status"] == "running" and frames[0]["company_name"] is None
    assert frames[1]["status"] == "ok" and frames[1]["company_name"] == "Acme"
    assert frames[0]["step_id"] == frames[1]["step_id"]
    assert frames[0]["tool"] == "query_financial"
    # 回喂模型的摘要不含内部字段
    assert "company_name" not in summary and "step_id" not in summary


@pytest.mark.asyncio
async def test_dispatch_tools_emit_error_on_failure(monkeypatch):
    frames = []

    async def fake_dispatch(name, args):
        return {"ok": False, "error": "boom"}

    acc = ra._Accumulator()
    tools = ra._dispatch_tools(fake_dispatch, acc, frames.append, {})
    tool = tools[0]
    await tool.coroutine()
    assert [f["status"] for f in frames] == ["running", "error"]


def test_accumulator_step_ids_are_unique():
    acc = ra._Accumulator()
    assert acc.next_step_id() != acc.next_step_id()
```

- [ ] **Step 2: 运行测试确认失败**

Run（`CIOaas-python/`）: `pytest tests/ai/chatbotgraph/test_retrieval_agent.py -k "dispatch_tools or step_ids" -v`
Expected: FAIL（`_dispatch_tools` 签名不接受 writer/id_to_name、`next_step_id` 不存在）

- [ ] **Step 3: 给 _Accumulator 加 step_id 计数器**

在 `retrieval_agent.py` 的 `_Accumulator.__init__` 末尾加一行计数器，并加方法：

```python
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.attempts = 0
        self._step_seq = 0

    def next_step_id(self) -> str:
        """单调递增的工具步骤 id（asyncio 单线程，自增即唯一）；running/ok 两帧共用。"""
        self._step_seq += 1
        return str(self._step_seq)
```

- [ ] **Step 4: 改 _dispatch_tools 签名并发两态帧**

把 `_dispatch_tools` 整体替换为（新增 `writer` / `id_to_name` 形参）：

```python
def _dispatch_tools(dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
                    acc: _Accumulator,
                    writer: Callable[[dict[str, Any]], None],
                    id_to_name: dict[str, str]) -> list:
    """以 ``TOOL_REGISTRY`` 工具对象为 schema 源，造一批「真执行（经 dispatch）」的同名工具。

    LLM 可见 schema 完全继承；鉴权经 ``dispatch`` 闭包注入（LLM 不可见）；完整结果留 ``acc``、
    仅摘要回喂模型。每次调用经 ``writer`` 实时推 running → ok/error 两帧（``step_id`` 配对，
    前端据此把"进行中"原地更新为"完成"）；``id_to_name`` 把 LLM 给的 company_id 尽力翻成公司名
    （翻不到为 None，不影响功能）。
    """
    def _make(schema_tool):
        async def _run(**llm_args: Any) -> str:
            sid = acc.next_step_id()
            writer({"kind": "tool_step", "step_id": sid, "tool": schema_tool.name,
                    "status": "running", "company_name": None})
            out = await dispatch(schema_tool.name, llm_args)
            acc.record(schema_tool.name, llm_args, out)
            writer({"kind": "tool_step", "step_id": sid, "tool": schema_tool.name,
                    "status": "ok" if out.get("ok") else "error",
                    "company_name": id_to_name.get(llm_args.get("company_id"))})
            return default_summary(out)
        return StructuredTool(
            name=schema_tool.name,
            description=schema_tool.description,
            args_schema=schema_tool.tool_call_schema,
            coroutine=_run,
        )
    return [_make(t) for t in TOOL_REGISTRY]
```

- [ ] **Step 5: retrieve_node 主体取 writer + 建 id→name + 传入**

在 `retrieve_node` 顶部加 import 与 writer 获取，并把 `_dispatch_tools(...)` 调用补两个实参。

文件顶部 import 区追加：

```python
from langgraph.config import get_stream_writer
```

`retrieve_node` 内（`dispatch = _make_dispatch(ctx)` 之后、`tools = ...` 之前）插入：

```python
    try:
        writer = get_stream_writer()
    except RuntimeError:
        # 非 custom 流上下文（如 ainvoke / 单测直调）：退化为 no-op，逻辑不受影响。
        def writer(_data: dict[str, Any]) -> None:
            return None
    id_to_name = {c["id"]: c["name"]
                  for c in (state.get("accessible_company_list") or [])
                  if c.get("id") and c.get("name")}
```

并把：

```python
    tools = [t for t in _dispatch_tools(dispatch, acc) if t.name not in disabled]
```

改为：

```python
    tools = [t for t in _dispatch_tools(dispatch, acc, writer, id_to_name)
             if t.name not in disabled]
```

- [ ] **Step 6: 运行测试确认通过**

Run（`CIOaas-python/`）: `pytest tests/ai/chatbotgraph/test_retrieval_agent.py -v`
Expected: PASS（新增用例 + 原有用例全绿）

- [ ] **Step 7: Commit**

```bash
git -C CIOaas-python add source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py tests/ai/chatbotgraph/test_retrieval_agent.py
git -C CIOaas-python commit -m "feat(ai): emit realtime two-state tool_step frames from retrieve_node tools"
```

---

## Task 4: chat_turn —— astream 双流分流 + 删旧一次性下发

**Files:**
- Modify: `source/chatbot/application/chat_turn.py`
- Test: `tests/chatbot/application/test_chat_turn.py`（不存在则新建）

- [ ] **Step 1: 写失败测试**

新建/追加 `tests/chatbot/application/test_chat_turn.py`：

```python
import pytest

from chatbot.application import chat_turn as ct
from chatbot.application.chat_events import ToolStep


def test_custom_to_tool_step_running_label():
    ev = ct._custom_to_tool_step({"kind": "tool_step", "step_id": "1",
                                  "tool": "query_financial", "status": "running",
                                  "company_name": None})
    assert isinstance(ev, ToolStep)
    assert ev.step_id == "1" and ev.status == "running"
    assert ev.label == "Querying financial data"


def test_custom_to_tool_step_ok_label_with_company():
    ev = ct._custom_to_tool_step({"kind": "tool_step", "step_id": "2",
                                  "tool": "query_financial", "status": "ok",
                                  "company_name": "Acme"})
    assert ev.status == "ok"
    assert ev.label == "Queried financial data for Acme"


def test_custom_to_tool_step_ignores_unknown_kind():
    assert ct._custom_to_tool_step({"kind": "other"}) is None
```

- [ ] **Step 2: 运行测试确认失败**

Run（`CIOaas-python/`）: `pytest tests/chatbot/application/test_chat_turn.py -v`
Expected: FAIL（`_custom_to_tool_step` 不存在）

- [ ] **Step 3: 新增标签常量与 _custom_to_tool_step**

把 `chat_turn.py` 现有的 `_TOOL_STEP_LABELS` 改为带两态文案，并替换 `_step_label`/`_custom_to_tool_step`。

将现有 `_TOOL_STEP_LABELS` 与 `_step_label`（`chat_turn.py:53-70`）整段替换为：

```python
# 工具名 → (running 文案, 完成文案) 的用户可读英文（代码生成，不依赖 agent 推理文字）。
_TOOL_STEP_LABELS: dict[str, tuple[str, str]] = {
    "get_company_detail": ("Looking up company profile", "Looked up company profile"),
    "query_financial": ("Querying financial data", "Queried financial data"),
    "query_benchmark_scorecard": ("Pulling benchmark scorecard", "Pulled benchmark scorecard"),
    "query_normalization_trace": ("Tracing normalized figures", "Traced normalized figures"),
    "run_analysis": ("Running cross-company analysis", "Ran cross-company analysis"),
    "list_companies": ("Listing accessible companies", "Listed accessible companies"),
}


def _custom_to_tool_step(chunk: dict) -> ChatEvent | None:
    """图内 custom 帧（retrieve_node 工具推的原始信号）→ ToolStep 领域事件。

    running 用进行时文案；ok/error 用完成时文案，``company_name`` 存在时补 "… for X"。
    非 tool_step 帧返回 None（忽略，前向兼容）。
    """
    if chunk.get("kind") != "tool_step":
        return None
    tool = chunk.get("tool", "")
    status = chunk.get("status", "running")
    running_label, done_label = _TOOL_STEP_LABELS.get(tool, (tool, tool))
    base = running_label if status == "running" else done_label
    name = chunk.get("company_name")
    label = f"{base} for {name}" if name else base
    return events.ToolStep(step_id=str(chunk.get("step_id", "")),
                           label=label, tool=tool, status=status)
```

> 注：`ChatEvent` 已从 `chat_events` 导入（文件顶部 `from chatbot.application.chat_events import ChatEvent`）。若未导入则在顶部 import 区补上。

- [ ] **Step 4: graph 驱动改 astream 双流分流**

把 `chat_turn.py` 的：

```python
    try:
        result = await get_chat_graph_app().ainvoke(state)
    except BaseException:
        # 图失败/被取消时回收并发的标题任务，避免孤儿 task 告警。
        if title_task is not None:
            title_task.cancel()
        raise
```

替换为：

```python
    final_state: dict = {}
    try:
        async with aclosing(get_chat_graph_app().astream(
                state, stream_mode=["custom", "values"])) as stream:
            async for mode, chunk in stream:
                if mode == "custom":
                    ev = _custom_to_tool_step(chunk)
                    if ev is not None:
                        yield ev          # 实时下发工具步骤卡片（running → ok/error）
                elif mode == "values":
                    final_state = chunk   # 留最后一帧为最终 state
    except BaseException:
        # 图失败/被取消时回收并发的标题任务，避免孤儿 task 告警。
        if title_task is not None:
            title_task.cancel()
        raise
    result = final_state
```

并在文件顶部 import 区补：

```python
from contextlib import aclosing
```

- [ ] **Step 5: 删除旧的一次性下发循环**

删除 `chat_turn.py` 中「工具步骤卡片：取数完一次性下发」整段（原 `_companies = {...}` 与紧随的 `for _t in result.get("tool_results") ...: yield events.ToolStep(...)` 循环，约 `chat_turn.py:154-160`）。其余 synthesis 流式逻辑保持不变。

- [ ] **Step 6: 运行测试确认通过**

Run（`CIOaas-python/`）: `pytest tests/chatbot/application/test_chat_turn.py -v`
Expected: PASS

- [ ] **Step 7: 跑相关回归**

Run（`CIOaas-python/`）: `pytest tests/chatbot/ tests/ai/chatbotgraph/ -q`
Expected: PASS（无回归）

- [ ] **Step 8: Commit**

```bash
git -C CIOaas-python add source/chatbot/application/chat_turn.py tests/chatbot/application/test_chat_turn.py
git -C CIOaas-python commit -m "feat(chatbot): stream tool steps in realtime via graph astream custom mode"
```

---

## Task 5: 前端事件契约 —— chatEvents.ts 透传 step_id

**Files:**
- Modify: `src/services/api/chat/chatEvents.ts:49-67,137-143`

- [ ] **Step 1: 改 ToolStepPayload 与回调类型**

`chatEvents.ts` 的 `ToolStepPayload` 改为：

```typescript
export interface ToolStepPayload {
  step_id?: string;
  label?: string;
  tool?: string;
  status?: string;
}
```

`ChatEventCallbacks.onToolStep` 改为：

```typescript
  onToolStep?: (step: { stepId: string; label: string; tool: string; status: string }) => void;
```

- [ ] **Step 2: 改分发逻辑透传 step_id**

`dispatchChatEvent` 中 `CHAT_EVENT.TOOL_STEP` 分支改为：

```typescript
  if (event === CHAT_EVENT.TOOL_STEP) {
    const p = parseJson<ToolStepPayload>(data);
    if (p?.label && p?.tool) {
      cb.onToolStep?.({
        stepId: p.step_id || '',
        label: p.label,
        tool: p.tool,
        status: p.status || 'running',
      });
    }
    return false; // 工具步骤不终结流，后续文本 / [DONE] 继续
  }
```

- [ ] **Step 3: 类型校验**

Run（`CIOaas-web/`）: `npm run tsc`
Expected: 报错指向 `useChatStream.ts` / `messageReducer.ts`（onToolStep 入参形状变了）—— 由 Task 6 修复；本步只确认 chatEvents.ts 自身无类型错误。

无 commit（与 Task 6 合并提交，避免中间态 tsc 不过）。

---

## Task 6: 前端 reducer —— ToolStepInfo 加 stepId + upsert 合并

**Files:**
- Modify: `src/pages/ai/chat/utils/messageReducer.ts:5-10,110-118`
- Modify: `src/pages/ai/chat/hooks/useChatStream.ts:170-173,294-297`（onToolStep 透传，仅字段）

- [ ] **Step 1: 改 ToolStepInfo**

`messageReducer.ts` 的 `ToolStepInfo` 改为：

```typescript
/** 工具步骤卡片：取数阶段每个工具调用一条（后端 tool_step 事件，running→ok/error 两态）。 */
export interface ToolStepInfo {
  stepId: string;
  label: string;
  tool: string;
  status: string;
}
```

- [ ] **Step 2: appendToolStep 改 upsert（按 stepId 合并两态）**

`messageReducer.ts` 的 `appendToolStep` 分支改为：

```typescript
    case 'appendToolStep': {
      // 工具步骤卡片：按 stepId upsert——running 帧新增一行，后续 ok/error 帧原地更新状态/文案。
      const msgs = state.messages.slice();
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        const steps = last.steps ?? [];
        const idx = steps.findIndex((s) => s.stepId === action.step.stepId);
        const nextSteps =
          idx >= 0
            ? steps.map((s, i) => (i === idx ? action.step : s))
            : [...steps, action.step];
        msgs[msgs.length - 1] = { ...last, steps: nextSteps };
      }
      return { ...state, messages: msgs };
    }
```

（`ChatAction` 中 `{ type: 'appendToolStep'; step: ToolStepInfo }` 类型不变，`step` 形状随 `ToolStepInfo` 更新自动生效。）

- [ ] **Step 3: useChatStream 两处 onToolStep 透传**

`useChatStream.ts` 的 `send`（约 170-173 行）与 `enterThread`（约 294-297 行）两处 `onToolStep` 回调体不变（仍是 `dispatch({ type: 'appendToolStep', step })`）；因 `step` 现在带 `stepId`，类型自动对齐。确认两处回调入参直接透传 `step` 即可，无需逻辑改动。

- [ ] **Step 4: 类型校验**

Run（`CIOaas-web/`）: `npm run tsc`
Expected: PASS（chatEvents / messageReducer / useChatStream 类型自洽；ToolStepsCard 仍读旧字段则报错 → Task 7 修复）。若仅 ToolStepsCard 报错，继续 Task 7。

无 commit（与 Task 7 合并提交完整前端改动）。

---

## Task 7: 前端渲染 —— ToolStepsCard 三态图标

**Files:**
- Modify: `src/pages/ai/chat/components/ToolStepsCard.tsx`
- Modify: `src/pages/ai/chat/components/ToolStepsCard.less`

- [ ] **Step 1: 改 ToolStepsCard 按 status 渲染**

`ToolStepsCard.tsx` 整体替换为：

```tsx
import React from 'react';
import { LoadingOutlined } from '@ant-design/icons';
import type { ToolStepInfo } from '../utils/messageReducer';
import styles from './ToolStepsCard.less';

interface Props {
  steps: ToolStepInfo[];
}

function StepIcon({ status }: { status: string }) {
  if (status === 'running') return <LoadingOutlined className={styles.spin} />;
  if (status === 'error') return <span className={styles.error}>✕</span>;
  return <span className={styles.ok}>✓</span>;
}

/**
 * 工具步骤卡片：取数阶段每个工具调用一行，渲染在 assistant 答案上方。
 * 数据源是后端 tool_step 事件（running→ok/error 两态，前端按 stepId 原地合并）。
 */
const ToolStepsCard: React.FC<Props> = ({ steps }) => (
  <div className={styles.steps}>
    {steps.map((s) => (
      <div key={s.stepId || s.tool} className={styles.step}>
        <span className={styles.icon}>
          <StepIcon status={s.status} />
        </span>
        <span>{s.label}</span>
      </div>
    ))}
  </div>
);

export default ToolStepsCard;
```

- [ ] **Step 2: 改 less 加 spinner / error 样式**

`ToolStepsCard.less` 整体替换为：

```less
.steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.step {
  display: flex;
  align-items: center;
  font-size: 12px;
  line-height: 18px;
  color: #8c8c8c;
}

.icon {
  margin-right: 6px;
  font-weight: 600;
}

.ok {
  color: #52c41a;
}

.error {
  color: #bfbfbf;
}

.spin {
  color: #1890ff;
}
```

- [ ] **Step 3: 类型 + lint 校验**

Run（`CIOaas-web/`）: `npm run tsc`
Expected: PASS（全项目类型自洽）

Run（`CIOaas-web/`）: `npm run lint:fix`
Expected: 无遗留 error

- [ ] **Step 4: Commit（前端整体）**

```bash
git -C CIOaas-web add src/services/api/chat/chatEvents.ts src/pages/ai/chat/utils/messageReducer.ts src/pages/ai/chat/hooks/useChatStream.ts src/pages/ai/chat/components/ToolStepsCard.tsx src/pages/ai/chat/components/ToolStepsCard.less
git -C CIOaas-web commit -m "feat(chat): render realtime two-state tool steps (running/ok/error)"
```

---

## Task 8: 规范自查 + 端到端验证

**Files:** 无（验证 + 文档）

- [ ] **Step 1: 后端规范自查**

按 `CIOaas-python/standards/coding.md` + `architecture.md` 审本次改动：类型注解完整、无 `print`、跨模块边界（ai 域不 import chatbot domain）未破、LLM 仍走 `llm_db_router`。修复不符合项。

- [ ] **Step 2: 后端全量测试**

Run（`CIOaas-python/`）: `pytest tests/chatbot/ tests/ai/chatbotgraph/ -q`
Expected: PASS

- [ ] **Step 3: 前端类型 + 构建校验**

Run（`CIOaas-web/`）: `npm run tsc`
Expected: PASS

- [ ] **Step 4: 手动端到端验证**

启动后端（`cd source && uvicorn main:app --port 8090`）+ 前端（`npm run start:dev`），在 `/devSupport/chat` 发一个需要多工具的问题（如「benchmark + 财务对比某公司」），确认：
- 工具步骤逐个实时出现，每步先 spinner（蓝）后 ✓（绿）。
- 工具失败步骤显示 ✕（灰），最终答案仍正常流式产出。
- 切换会话 / 刷新续流行为正常（无回归）。
- 历史会话重新进入，步骤显示为完成态（✓）。

- [ ] **Step 5: 更新 spec 验收勾选（可选）**

在 spec §10 验收标准对照确认全部满足。

无 commit（验证性步骤；如自查产生代码修复，按 Task 2-7 同款 commit 规范单独提交）。

---

## Self-Review 记录

- **Spec 覆盖**：§4 事件契约→Task2；§5.2 retrieve_node→Task3；§5.1 chat_turn 双流→Task4；§6 前端→Task5/6/7；§7 错误处理（error 态、astream aclosing 取消）→Task3/4/7；§8 测试→各 Task 测试步 + Task8；§9 spike→Task1。无遗漏。
- **占位扫描**：无 TBD/TODO，每步含完整代码或具体命令。
- **类型一致**：`step_id`(后端) / `stepId`(前端) 命名跨任务一致；`_dispatch_tools(dispatch, acc, writer, id_to_name)` 签名 Task3 定义、同任务测试与调用一致；`_custom_to_tool_step` Task4 定义并被同任务测试引用；`ToolStepInfo{stepId,label,tool,status}` Task6 定义、Task7 渲染消费一致。
