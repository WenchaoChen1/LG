# SSE 事件契约统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 chatbot SSE 事件的定义与序列化收敛到前后端各自的集中单点，消灭散落的 magic string / 手搓 dict / 手写契约注释，并补上流中异常 → `error` 事件的缺口。

**Architecture:** 后端 1b 分层——`application/chat_events.py` 定义 frozen dataclass 事件对象（语义契约单点），`interfaces/sse_events.py` 的 `to_sse()` 统一序列化为 SSE bytes（传输单点），`routes._gen` 包 try/except 兜底 error 事件；前端 `services/api/chat/chatEvents.ts` 集中事件名常量 + payload 类型 + `dispatchChatEvent` 分发器。权威契约 = spec §4 事件清单表。

**Tech Stack:** Python 3.12 / FastAPI / pytest（`uv run pytest`，cwd=`CIOaas-python`）；TypeScript / UmiJS 3 / jest（**基架损坏跑不了**，前端门禁 = `npm run tsc`，cwd=`CIOaas-web`，必须 Node 16 + npm）。

**Spec:** `docs/superpowers/specs/2026-06-11-sse-event-contract-design.md`（含权威事件契约表 §4）

---

## ⚠️ 执行前必读

1. ~~两个子仓库有未提交的 chat-chart 改动~~ **已处理（2026-06-11）**：chat-chart 工作已提交并推送，且已 merge 远端 text-to-SQL agent 提交（`stream_turn` 现多 `financial_mode` 参数，本计划代码已同步）。基线 = `feature/ai-chatbot-v1` 最新；`CIOaas-web` 工作区仅余刻意不提交的 `config/proxy.ts` 本地配置。
2. **Git 规则（强制）**：`git add` / `git commit` 前必须征得用户确认，绝不自动提交；提交消息**英文** Conventional Commits。每个 Task 的 Commit 步骤都遵守此规则：展示变更摘要 → 等用户确认 → 才执行。
3. **嵌套仓库**：`CIOaas-python` 与 `CIOaas-web` 是独立 Git 仓库，提交分别在各自目录进行。
4. **前端测试基架损坏**：`npm test` 跑不起来（jest.config 指向缺失的 `tests/PuppeteerEnvironment`）。**勿临时修改测试基架**；测试文件照写（基架修好即生效），验证门禁 = `npm run tsc`。
5. 后端命令工作目录均为 `C:\github-code\LG\CIOaas-python`；前端为 `C:\github-code\LG\CIOaas-web`。

---

### Task 1: 后端事件契约 + 序列化器（chat_events.py / sse_events.py）

**Files:**
- Create: `CIOaas-python/source/chatbot/application/chat_events.py`
- Create: `CIOaas-python/source/chatbot/interfaces/sse_events.py`
- Test: `CIOaas-python/tests/chatbot/interfaces/test_sse_events.py`

- [ ] **Step 1: 写失败测试**

创建 `CIOaas-python/tests/chatbot/interfaces/test_sse_events.py`：

```python
"""to_sse：chatbot 领域事件 → SSE bytes 的序列化契约测试（spec §4 权威表）。"""
import json

import pytest

from chatbot.application.chat_events import (
    Blocked,
    Chart,
    Done,
    NeedsPick,
    ThreadStarted,
)
from chatbot.interfaces.sse_events import to_sse
from llm.infrastructure.capabilities.text import TextChunk


def _parse(frame: bytes) -> tuple[str | None, str | None]:
    """把单帧 SSE bytes 拆成 (event, data)；无 event 行返回 (None, data)。"""
    text = frame.decode("utf-8")
    assert text.endswith("\n\n"), "SSE 帧必须以空行结尾"
    event, data = None, None
    for line in text[:-2].split("\n"):
        if line.startswith("event: "):
            event = line[len("event: "):]
        elif line.startswith("data: "):
            data = line[len("data: "):]
    return event, data


def test_thread_started_serializes_to_thread_event():
    event, data = _parse(to_sse(ThreadStarted("t-1")))
    assert event == "thread"
    assert json.loads(data) == {"thread_id": "t-1"}


def test_chart_serializes_spec_as_payload():
    spec = {"type": "bar", "columns": ["q", "v"], "rows": [["Q1", 1]]}
    event, data = _parse(to_sse(Chart(spec)))
    assert event == "chart"
    assert json.loads(data) == spec


def test_needs_pick_serializes_hint():
    event, data = _parse(to_sse(NeedsPick("which company?")))
    assert event == "needs_pick"
    assert json.loads(data) == {"hint": "which company?"}


def test_blocked_serializes_reason():
    event, data = _parse(to_sse(Blocked("nope")))
    assert event == "blocked"
    assert json.loads(data) == {"reason": "nope"}


def test_done_serializes_to_done_marker():
    assert to_sse(Done()) == b"data: [DONE]\n\n"


def test_text_chunk_serializes_to_default_data_frame():
    event, data = _parse(to_sse(TextChunk(delta="Hi", is_final=False)))
    assert event is None  # 文本流无 event 名
    payload = json.loads(data)
    assert payload["delta"] == "Hi"
    assert payload["is_final"] is False


def test_unknown_event_type_raises_type_error():
    with pytest.raises(TypeError):
        to_sse(object())  # type: ignore[arg-type]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/chatbot/interfaces/test_sse_events.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'chatbot.application.chat_events'`

- [ ] **Step 3: 创建事件契约模块**

创建 `CIOaas-python/source/chatbot/application/chat_events.py`：

```python
"""chatbot SSE 领域事件对象（application 层语义契约，零传输知识）。

定义"有哪些事件 + 字段"；序列化为 SSE bytes 由 interfaces/sse_events.py 负责。
权威契约表见 docs/superpowers/specs/2026-06-11-sse-event-contract-design.md §4。
文本增量直接复用 llm 的 TextChunk，不再包一层。
"""
from __future__ import annotations

from dataclasses import dataclass

from llm.infrastructure.capabilities.text import TextChunk


@dataclass(frozen=True)
class ThreadStarted:
    thread_id: str


@dataclass(frozen=True)
class Chart:
    spec: dict  # ChartSpec：{type, title?, columns, rows}，由 chart_fence_parser 校验产出


@dataclass(frozen=True)
class NeedsPick:
    hint: str


@dataclass(frozen=True)
class Blocked:
    reason: str


@dataclass(frozen=True)
class Done:
    pass


# 文本增量原生透传 llm TextChunk；error 不在此列（由 routes 异常兜底产生）。
ChatEvent = ThreadStarted | Chart | NeedsPick | Blocked | Done | TextChunk
```

- [ ] **Step 4: 创建序列化器**

创建 `CIOaas-python/source/chatbot/interfaces/sse_events.py`：

```python
"""chatbot 领域事件 → W3C SSE bytes（interfaces 传输层，唯一序列化点）。

事件名字符串 + payload 投影集中在此；调用 llm 公共 sse 原语完成字节序列化。
权威契约表见 docs/superpowers/specs/2026-06-11-sse-event-contract-design.md §4。
"""
from __future__ import annotations

from llm.infrastructure.capabilities.text import TextChunk
from llm.infrastructure.llm_router.sse import (
    chunk_to_sse_bytes,
    done_marker,
    event_to_sse_bytes,
)

from chatbot.application.chat_events import (
    Blocked,
    Chart,
    ChatEvent,
    Done,
    NeedsPick,
    ThreadStarted,
)


def to_sse(ev: ChatEvent) -> bytes:
    """把一个 chatbot 领域事件序列化为 SSE bytes。"""
    match ev:
        case ThreadStarted():
            return event_to_sse_bytes("thread", {"thread_id": ev.thread_id})
        case Chart():
            return event_to_sse_bytes("chart", ev.spec)
        case NeedsPick():
            return event_to_sse_bytes("needs_pick", {"hint": ev.hint})
        case Blocked():
            return event_to_sse_bytes("blocked", {"reason": ev.reason})
        case Done():
            return done_marker()
        case TextChunk():
            return chunk_to_sse_bytes(ev)
    raise TypeError(f"未知 ChatEvent 类型: {type(ev).__name__}")
```

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/chatbot/interfaces/test_sse_events.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit（先征得用户确认）**

向用户展示变更摘要并确认后，在 `CIOaas-python` 目录执行：

```bash
git add source/chatbot/application/chat_events.py source/chatbot/interfaces/sse_events.py tests/chatbot/interfaces/test_sse_events.py
git commit -m "feat(chatbot): add centralized SSE event contract and serializer"
```

---

### Task 2: chat_service 改产事件对象（去序列化）

**Files:**
- Modify: `CIOaas-python/source/chatbot/application/chat_service.py`（全文件替换，现 103 行）
- Test: `CIOaas-python/tests/chatbot/application/test_chat_service.py`（改造现有 4 个测试的断言方式）

- [ ] **Step 1: 改造测试为断言事件对象序列**

将 `CIOaas-python/tests/chatbot/application/test_chat_service.py` 全文件替换为：

```python
from types import SimpleNamespace

import pytest

from chatbot.application import chat_service as svc
from chatbot.application.chat_events import Chart, Done, NeedsPick, ThreadStarted
from llm.infrastructure.capabilities.text import TextChunk


@pytest.mark.asyncio
async def test_stream_turn_streams_and_persists(mocker):
    class _Graph:
        async def ainvoke(self, state):
            return {"needs_company_pick": False, "blocked_reason": None,
                    "active_company_id": "c-1",
                    "synthesis_messages": [{"role": "system", "content": "s"},
                                           {"role": "user", "content": "q"}],
                    "attribution": ["source:financial"],
                    "tool_results": [{"tool": "financial"}]}

    mocker.patch.object(svc, "get_chat_graph_app", return_value=_Graph())

    async def _astream(messages, **kw):
        for d in ("Hel", "lo"):
            yield SimpleNamespace(delta=d, is_final=False, finish_reason=None, usage=None)
        yield SimpleNamespace(delta="", is_final=True, finish_reason="stop", usage=None)

    mocker.patch.object(svc.llm_db_router, "astream", _astream)
    append = mocker.patch.object(svc.repo, "append_message", return_value="m1")

    identity = SimpleNamespace(user_id="u1", org_id="o1")
    events = []
    async for ev in svc.stream_turn(thread_id="t1", question="q", identity=identity,
                                    end_type="company", active_company_id="c-1",
                                    auth_token="tok"):
        events.append(ev)

    assert events[0] == ThreadStarted("t1")
    deltas = "".join(e.delta for e in events if isinstance(e, TextChunk))
    assert deltas == "Hello"
    assert events[-1] == Done()
    assert append.call_count == 2  # user + assistant


@pytest.mark.asyncio
async def test_stream_turn_needs_company_pick_short_circuits(mocker):
    class _Graph:
        async def ainvoke(self, state):
            return {"needs_company_pick": True, "needs_data_hint": "which company?"}

    mocker.patch.object(svc, "get_chat_graph_app", return_value=_Graph())
    append = mocker.patch.object(svc.repo, "append_message", return_value="m1")

    identity = SimpleNamespace(user_id="u1", org_id="o1")
    events = []
    async for ev in svc.stream_turn(thread_id="t1", question="q", identity=identity,
                                    end_type="admin", active_company_id=None,
                                    auth_token="tok"):
        events.append(ev)

    assert events == [ThreadStarted("t1"), NeedsPick("which company?"), Done()]
    assert append.call_count == 2  # user + assistant pick-prompt


@pytest.mark.asyncio
async def test_stream_turn_splits_chart_event_and_persists_raw(mocker):
    class _Graph:
        async def ainvoke(self, state):
            return {"needs_company_pick": False, "blocked_reason": None,
                    "active_company_id": "c-1",
                    "synthesis_messages": [{"role": "user", "content": "x"}],
                    "tool_results": [], "attribution": []}

    mocker.patch.object(svc, "get_chat_graph_app", return_value=_Graph())

    body = '{"type":"bar","columns":["q","v"],"rows":[["Q1",1]]}'

    async def _astream(messages, **kw):
        for d in ("hello ", "```chart\n", body, "\n```", " bye"):
            yield TextChunk(delta=d)

    mocker.patch.object(svc.llm_db_router, "astream", _astream)

    appended: dict[str, str] = {}

    def _append(**kw):
        if kw.get("role") == "assistant":
            appended["content"] = kw.get("content")
        return "m1"

    mocker.patch.object(svc.repo, "append_message", side_effect=_append)

    identity = SimpleNamespace(user_id="u1", org_id=None)
    events = []
    async for ev in svc.stream_turn(thread_id="t1", question="q", identity=identity,
                                    end_type="admin", active_company_id=None):
        events.append(ev)

    # 1) 结构化 Chart 事件存在且 spec 正确
    charts = [e for e in events if isinstance(e, Chart)]
    assert len(charts) == 1
    assert charts[0].spec["type"] == "bar"
    # 2) 文本走 TextChunk（hello / bye）
    text = "".join(e.delta for e in events if isinstance(e, TextChunk))
    assert "hello " in text and " bye" in text
    # 3) Done 收尾
    assert events[-1] == Done()
    # 4) content 落库含 fence 原文
    assert "```chart" in appended["content"] and body in appended["content"]


@pytest.mark.asyncio
async def test_stream_turn_logs_when_assistant_persist_fails(mocker):
    """assistant 落库失败时：不中断流（Done 照常产出）且显式记 error 日志。"""
    class _Graph:
        async def ainvoke(self, state):
            return {"needs_company_pick": False, "blocked_reason": None,
                    "active_company_id": "c-1",
                    "synthesis_messages": [{"role": "user", "content": "q"}],
                    "tool_results": [], "attribution": []}

    mocker.patch.object(svc, "get_chat_graph_app", return_value=_Graph())

    async def _astream(messages, **kw):
        yield TextChunk(delta="hi")

    mocker.patch.object(svc.llm_db_router, "astream", _astream)

    # user 消息正常落库；assistant 落库抛错（模拟 DB 写失败）。
    def _append(**kw):
        if kw.get("role") == "assistant":
            raise RuntimeError("db down")
        return "m1"

    mocker.patch.object(svc.repo, "append_message", side_effect=_append)
    log_error = mocker.patch.object(svc.logger, "error")

    identity = SimpleNamespace(user_id="u1", org_id=None)
    events = []
    async for ev in svc.stream_turn(thread_id="t1", question="q", identity=identity,
                                    end_type="admin", active_company_id=None):
        events.append(ev)

    # 1) 流未被吞掉，正常收尾
    text = "".join(e.delta for e in events if isinstance(e, TextChunk))
    assert "hi" in text
    assert events[-1] == Done()
    # 2) 失败被显式记日志：含 thread_id + exc_info
    assert log_error.call_count == 1
    _, kwargs = log_error.call_args
    assert kwargs.get("exc_info") is True
    assert "t1" in log_error.call_args.args
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/chatbot/application/test_chat_service.py -v`
Expected: FAIL（当前实现产出 bytes，`events[0] == ThreadStarted("t1")` 等断言不成立）

- [ ] **Step 3: 改造 chat_service.py**

将 `CIOaas-python/source/chatbot/application/chat_service.py` 全文件替换为：

```python
"""编排：落用户消息 → 跑图 → （拦截/需选公司则直返）→ 流式合成 → 落 assistant。

最终答案的 token 流式由本服务用 ``llm_db_router.astream`` 产出；图只做路由/取数/准备。
本服务只产 ``chat_events.ChatEvent`` 领域事件对象（零传输知识）；
序列化为 SSE bytes 由 ``interfaces/sse_events.to_sse`` 负责（调用方 routes 完成）。
追踪由调用方（routes）的 ``trace_scope`` 经 ContextVar 注入。
"""
from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from llm.application.router import llm_db_router
from llm.infrastructure.model_registry.models import Models
from llm.infrastructure.capabilities.text import TextChunk

from chatbot.application.chat_events import (
    Blocked,
    Chart,
    ChatEvent,
    Done,
    NeedsPick,
    ThreadStarted,
)
from chatbot.application.chart_fence_parser import (
    ChartFenceStreamParser,
    ChartSegment,
    Segment,
)
from chatbot.domain import repository as repo

logger = logging.getLogger("CIOaaS.chatbot.chat_service")


def get_chat_graph_app():
    """返回已编译聊天图（main.py lifespan 注入）。"""
    from main import get_chat_graph_app as _g
    return _g()


def _seg_to_event(seg: Segment) -> ChatEvent:
    """图表段 → Chart 事件；文本段 → TextChunk（语义对象，非 SSE bytes）。"""
    if isinstance(seg, ChartSegment):
        return Chart(seg.spec)
    return TextChunk(delta=seg.text, is_final=False)


async def stream_turn(*, thread_id: str, question: str, identity,
                      end_type: str, active_company_id: Optional[str],
                      accessible_company_list: Optional[list[dict]] = None,
                      home_company_id: Optional[str] = None,
                      auth_token: str = "",
                      financial_mode: str = "api") -> AsyncIterator[ChatEvent]:
    repo.append_message(thread_id=thread_id, role="user", content=question)

    # 让前端尽早拿到 thread_id（替代原 HTTP header），走结构化 SSE 事件下发。
    yield ThreadStarted(thread_id)

    state = {
        "user_id": identity.user_id, "org_id": getattr(identity, "org_id", None),
        "end_type": end_type, "auth_token": auth_token,
        "accessible_company_list": accessible_company_list or [],
        "home_company_id": home_company_id,
        "thread_id": thread_id, "history": [], "question": question,
        "tool_results": [], "needs_company_pick": False,
        "active_company_id": active_company_id,
        "financial_mode": financial_mode,
    }
    # 图含 async 节点 → 必须 ainvoke
    result = await get_chat_graph_app().ainvoke(state)

    if result.get("blocked_reason"):
        msg = "抱歉，无法处理该请求。"
        repo.append_message(thread_id=thread_id, role="assistant", content=msg)
        yield Blocked(msg)
        yield Done()
        return
    if result.get("needs_company_pick"):
        msg = result.get("needs_data_hint") or "请告诉我是哪家公司。"
        repo.append_message(thread_id=thread_id, role="assistant", content=msg,
                            attribution=["needs_company_pick"])
        yield NeedsPick(msg)
        yield Done()
        return

    messages = result["synthesis_messages"]
    buf: list[str] = []
    parser = ChartFenceStreamParser()

    async for chunk in llm_db_router.astream(
        messages, model=Models.openrouter.text.sonnet, temperature=0.3,
    ):
        delta = getattr(chunk, "delta", None)
        if delta:
            buf.append(delta)               # buf 累积原始 delta（含 fence 原文）
            for seg in parser.feed(delta):
                yield _seg_to_event(seg)
    for seg in parser.flush():
        yield _seg_to_event(seg)
    yield Done()

    # Done 已下发、用户体验不中断；assistant 落库失败必须显式记日志（否则被
    # StreamingResponse 生成器框架静默吞掉，消息不落库且无任何痕迹）。
    try:
        repo.append_message(thread_id=thread_id, role="assistant", content="".join(buf),
                            attribution=result.get("attribution"),
                            used_tools=[t["tool"] for t in result.get("tool_results", [])])
    except Exception:
        logger.error("persist assistant message failed, thread_id=%s", thread_id,
                     exc_info=True)
```

要点（相对现状的差异）：删 `llm.infrastructure.llm_router.sse` import；`_seg_to_sse` 嵌套函数改为模块级 `_seg_to_event`（产事件对象）；`event_to_sse_bytes(...)` → 对应事件对象；`done_marker()` → `Done()`；返回类型 `AsyncIterator[bytes]` → `AsyncIterator[ChatEvent]`。其余逻辑（state 构造、落库时序、try/except）一概不动。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/chatbot/application/ -v`
Expected: 全部 passed（含 test_chart_fence_parser / test_company_service 等同目录既有测试）

注意：此刻 `routes.py` 还在直接 yield 事件对象（未序列化），属于中间态——Task 3 立即修复。两个 Task 同属一个功能闭环，**Task 2 与 Task 3 一起提交**（见 Task 3 Step 5），避免提交一个接口已坏的中间态。

- [ ] **Step 5: 不单独提交（与 Task 3 合并提交）**

---

### Task 3: routes 序列化 + 异常兜底 error 事件

**Files:**
- Modify: `CIOaas-python/source/chatbot/interfaces/routes.py`（仅 import 区 + `_gen`）
- Test: `CIOaas-python/tests/chatbot/interfaces/test_routes.py`（追加 2 个测试）

- [ ] **Step 1: 追加失败测试**

在 `CIOaas-python/tests/chatbot/interfaces/test_routes.py` 文件末尾追加：

```python
def test_send_streams_serialized_events(mocker):
    """POST /api/ai/chat：stream_turn 产出的事件对象被 to_sse 序列化为 SSE 帧。"""
    from chatbot.interfaces import routes
    from chatbot.application.chat_events import Done, ThreadStarted
    from llm.infrastructure.capabilities.text import TextChunk

    mocker.patch.object(routes.repo, "create_thread", return_value="t-9")

    async def _turn(**kw):
        yield ThreadStarted("t-9")
        yield TextChunk(delta="hi", is_final=False)
        yield Done()

    mocker.patch.object(routes.chat_service, "stream_turn", _turn)
    c = TestClient(_app())
    r = c.post("/api/ai/chat",
               json={"question": "q", "thread_id": None, "company_id": None})
    assert r.status_code == 200
    assert "event: thread" in r.text
    assert "t-9" in r.text
    assert "hi" in r.text
    assert "[DONE]" in r.text


def test_send_stream_error_yields_error_event(mocker):
    """流中抛异常 → 兜底成 event: error 下发（不再直抛 ASGI）。"""
    from chatbot.interfaces import routes

    mocker.patch.object(routes.repo, "create_thread", return_value="t-9")

    async def _turn(**kw):
        raise RuntimeError("boom")
        yield  # pragma: no cover — 使函数成为 async generator

    mocker.patch.object(routes.chat_service, "stream_turn", _turn)
    c = TestClient(_app())
    r = c.post("/api/ai/chat",
               json={"question": "q", "thread_id": None, "company_id": None})
    assert r.status_code == 200
    assert "event: error" in r.text
    assert "boom" in r.text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/chatbot/interfaces/test_routes.py -v`
Expected: 新增 2 个 FAIL——第一个因 `_gen` 直接 yield 事件对象（非 bytes）报 TypeError 或响应体不含 `event: thread`；第二个因异常直抛而非 error 事件。既有测试仍 PASS。

- [ ] **Step 3: 改造 routes.py**

在 `CIOaas-python/source/chatbot/interfaces/routes.py` 的 import 区追加（紧跟现有 import 之后）：

```python
from llm.infrastructure.llm_router.sse import error_to_sse_bytes

from chatbot.interfaces.sse_events import to_sse
```

将 `send()` 内的 `_gen` 替换为：

```python
    async def _gen():
        tid = uuid.uuid4().hex
        with trace_id_scope(tid), trace_scope(
            TraceContext(agent="chat", node="turn", user_id=ctx.user_id, trace_id=tid)
        ):
            try:
                async for ev in chat_service.stream_turn(
                    thread_id=thread_id, question=request.question, identity=ctx,
                    end_type=end_type, active_company_id=active,
                    accessible_company_list=[],
                    home_company_id=home_company_id, auth_token=auth_token,
                    financial_mode=financial_mode):
                    yield to_sse(ev)
            except Exception as e:  # noqa: BLE001 — 流中任何异常都兜底成 error 事件
                yield error_to_sse_bytes(e)
```

`send()` 其余部分（鉴权、thread 归属校验、`StreamingResponse(...)`）一概不动。

- [ ] **Step 4: 跑测试确认通过 + 后端全量回归**

Run: `uv run pytest tests/chatbot/interfaces/test_routes.py -v`
Expected: 全部 passed（既有 + 2 新）

Run: `uv run pytest tests/chatbot/ -v`
Expected: 全部 passed

- [ ] **Step 5: Commit（Task 2 + Task 3 一起，先征得用户确认）**

向用户展示变更摘要并确认后，在 `CIOaas-python` 目录执行：

```bash
git add source/chatbot/application/chat_service.py source/chatbot/interfaces/routes.py tests/chatbot/application/test_chat_service.py tests/chatbot/interfaces/test_routes.py
git commit -m "refactor(chatbot): emit typed chat events, serialize SSE only in interfaces layer"
```

---

### Task 4: 前端契约单点 chatEvents.ts + streamApi 收敛

**Files:**
- Create: `CIOaas-web/src/services/api/chat/chatEvents.ts`
- Create: `CIOaas-web/src/services/api/chat/chatEvents.test.ts`（基架损坏暂不可执行，照写备未来）
- Modify: `CIOaas-web/src/services/api/chat/streamApi.ts`（全文件替换，现 126 行）

- [ ] **Step 1: 创建 chatEvents.ts**

创建 `CIOaas-web/src/services/api/chat/chatEvents.ts`：

```typescript
import type { SSEFrame } from '@/services/sse';
import type { ChartSpec } from './chatDto';

/**
 * chatbot SSE 事件契约单点（事件名 + payload 类型 + 分发）。
 * 权威契约表：docs/superpowers/specs/2026-06-11-sse-event-contract-design.md §4。
 * 改事件先改契约表，再同步这里与后端 chatbot/interfaces/sse_events.py。
 */
export const CHAT_EVENT = {
  THREAD: 'thread',
  CHART: 'chart',
  NEEDS_PICK: 'needs_pick',
  BLOCKED: 'blocked',
  ERROR: 'error',
} as const;

export interface ThreadPayload {
  thread_id?: string;
}
export interface NeedsPickPayload {
  hint?: string;
}
export interface BlockedPayload {
  reason?: string;
}
export interface ErrorPayload {
  error_class?: string;
  error_message?: string;
}
export interface TextDeltaPayload {
  delta?: string;
  is_final?: boolean;
  finish_reason?: string;
}

export interface ChatEventCallbacks {
  onDelta: (delta: string) => void;
  onThreadId?: (threadId: string) => void;
  onChart?: (spec: ChartSpec) => void;
  onNeedsPick?: (hint: string) => void;
  onBlocked?: (reason: string) => void;
  onDone?: (finishReason?: string) => void;
  onError?: (err: Error) => void;
}

function parseJson<T>(data: string): T | null {
  try {
    return JSON.parse(data) as T;
  } catch (e) {
    return null;
  }
}

/** chart 最小结构校验：与历史路径 parseChartFences 强度一致，不符则丢弃不分发。 */
function isValidChartSpec(spec: ChartSpec | null): spec is ChartSpec {
  return (
    !!spec &&
    typeof spec.type === 'string' &&
    Array.isArray(spec.columns) &&
    Array.isArray(spec.rows)
  );
}

/**
 * 按事件名把一帧 SSE 分发到回调。
 * 返回 true 表示流已终结（DONE / is_final / error），调用方据此置 finished。
 */
export function dispatchChatEvent(frame: SSEFrame, cb: ChatEventCallbacks): boolean {
  const { event, data } = frame;

  if (data === '[DONE]') {
    cb.onDone?.();
    return true;
  }
  if (event === CHAT_EVENT.ERROR) {
    const p = parseJson<ErrorPayload>(data);
    cb.onError?.(new Error(p?.error_message || p?.error_class || data));
    return true;
  }
  if (event === CHAT_EVENT.THREAD) {
    const p = parseJson<ThreadPayload>(data);
    if (p?.thread_id) cb.onThreadId?.(p.thread_id);
    return false;
  }
  if (event === CHAT_EVENT.CHART) {
    const spec = parseJson<ChartSpec>(data);
    if (isValidChartSpec(spec)) cb.onChart?.(spec);
    return false;
  }
  if (event === CHAT_EVENT.NEEDS_PICK) {
    const p = parseJson<NeedsPickPayload>(data);
    if (p?.hint) cb.onNeedsPick?.(p.hint);
    return false;
  }
  if (event === CHAT_EVENT.BLOCKED) {
    const p = parseJson<BlockedPayload>(data);
    if (p?.reason) cb.onBlocked?.(p.reason);
    return false;
  }

  // 默认文本流（无 event 名）
  const p = parseJson<TextDeltaPayload>(data);
  if (!p) return false;
  if (p.delta) cb.onDelta(p.delta);
  if (p.is_final) {
    cb.onDone?.(p.finish_reason);
    return true;
  }
  return false;
}
```

- [ ] **Step 2: 创建 chatEvents.test.ts**

创建 `CIOaas-web/src/services/api/chat/chatEvents.test.ts`（⚠️ 基架损坏暂不可执行，照写、基架修复即生效）：

```typescript
import { dispatchChatEvent } from './chatEvents';
import type { ChatEventCallbacks } from './chatEvents';

function cbs(over: Partial<ChatEventCallbacks> = {}): ChatEventCallbacks {
  return { onDelta: () => undefined, ...over };
}

describe('dispatchChatEvent', () => {
  it('dispatches thread event to onThreadId and does not finish the stream', () => {
    let threadId = '';
    const finished = dispatchChatEvent(
      { event: 'thread', data: '{"thread_id":"t-9"}' },
      cbs({
        onThreadId: (t) => {
          threadId = t;
        },
      }),
    );
    expect(threadId).toBe('t-9');
    expect(finished).toBe(false);
  });

  it('dispatches text delta to onDelta', () => {
    const deltas: string[] = [];
    const finished = dispatchChatEvent(
      { event: '', data: '{"delta":"Hel","is_final":false}' },
      cbs({ onDelta: (d) => deltas.push(d) }),
    );
    expect(deltas).toEqual(['Hel']);
    expect(finished).toBe(false);
  });

  it('finishes on is_final with finish_reason passed to onDone', () => {
    let reason: string | undefined;
    const finished = dispatchChatEvent(
      { event: '', data: '{"delta":"","is_final":true,"finish_reason":"stop"}' },
      cbs({
        onDone: (r) => {
          reason = r;
        },
      }),
    );
    expect(finished).toBe(true);
    expect(reason).toBe('stop');
  });

  it('finishes on [DONE]', () => {
    let done = false;
    const finished = dispatchChatEvent(
      { event: '', data: '[DONE]' },
      cbs({
        onDone: () => {
          done = true;
        },
      }),
    );
    expect(done).toBe(true);
    expect(finished).toBe(true);
  });

  it('dispatches a valid chart event to onChart', () => {
    let chartType = '';
    const finished = dispatchChatEvent(
      { event: 'chart', data: '{"type":"bar","columns":["q"],"rows":[["Q1"]]}' },
      cbs({
        onChart: (s) => {
          chartType = s.type;
        },
      }),
    );
    expect(chartType).toBe('bar');
    expect(finished).toBe(false);
  });

  it('drops a chart event missing required structure', () => {
    let called = false;
    dispatchChatEvent(
      { event: 'chart', data: '{"type":"bar","columns":"oops"}' },
      cbs({
        onChart: () => {
          called = true;
        },
      }),
    );
    expect(called).toBe(false);
  });

  it('dispatches needs_pick and blocked', () => {
    let hint = '';
    let reason = '';
    dispatchChatEvent(
      { event: 'needs_pick', data: '{"hint":"pick one"}' },
      cbs({
        onNeedsPick: (h) => {
          hint = h;
        },
      }),
    );
    dispatchChatEvent(
      { event: 'blocked', data: '{"reason":"not allowed"}' },
      cbs({
        onBlocked: (r) => {
          reason = r;
        },
      }),
    );
    expect(hint).toBe('pick one');
    expect(reason).toBe('not allowed');
  });

  it('finishes with Error on error event', () => {
    let msg = '';
    const finished = dispatchChatEvent(
      { event: 'error', data: '{"error_class":"X","error_message":"boom"}' },
      cbs({
        onError: (e) => {
          msg = e.message;
        },
      }),
    );
    expect(msg).toBe('boom');
    expect(finished).toBe(true);
  });

  it('ignores malformed JSON without throwing', () => {
    const finished = dispatchChatEvent({ event: '', data: 'not-json' }, cbs());
    expect(finished).toBe(false);
  });
});
```

- [ ] **Step 3: 收敛 streamApi.ts**

将 `CIOaas-web/src/services/api/chat/streamApi.ts` 全文件替换为：

```typescript
import { getToken } from '@/utils/utils';
import { streamSSE } from '@/services/sse';
import type { SSEFrame } from '@/services/sse';
import { dispatchChatEvent } from './chatEvents';
import type { ChatEventCallbacks } from './chatEvents';

export interface StreamChatRequest {
  threadId: string | null;
  companyId: string | null;
  question: string;
  endType: 'company' | 'admin';
}

/** 回调契约统一定义在 chatEvents.ts；此别名保持既有调用方 import 路径不变。 */
export type StreamChatCallbacks = ChatEventCallbacks;

/**
 * 流式聊天：经公共 streamSSE 读 SSE，按 chatEvents 契约分发到回调。
 * token 用 getToken() 经 headers 注入；端类型经 x-chat-end 头传给后端。
 * 事件契约见 docs/superpowers/specs/2026-06-11-sse-event-contract-design.md §4。
 */
export async function streamChat(req: StreamChatRequest, cb: StreamChatCallbacks): Promise<void> {
  const token = getToken();
  let finished = false;
  const handleFrame = (frame: SSEFrame): void => {
    if (finished) return;
    if (dispatchChatEvent(frame, cb)) finished = true;
  };

  await streamSSE('/api/ai/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'x-chat-end': req.endType,
    },
    body: JSON.stringify({
      thread_id: req.threadId,
      company_id: req.companyId,
      question: req.question,
    }),
    onFrame: handleFrame,
    onError: (e) => {
      if (!finished) cb.onError?.(e);
    },
  });

  if (!finished) cb.onDone?.();
}
```

注意：`streamApi.test.ts` **一行不改**（契约保留，基架修复后即回归验证）。

- [ ] **Step 4: TypeScript 门禁**

在 `CIOaas-web` 目录 Run: `npm run tsc`
Expected: 零错误（`useChatStream.ts` 等调用方经 `StreamChatCallbacks` 别名零改动通过编译）

- [ ] **Step 5: Lint**

Run: `npm run lint:fix`
Expected: 无新增 error（warning 维持现状）

- [ ] **Step 6: Commit（先征得用户确认）**

向用户展示变更摘要并确认后，在 `CIOaas-web` 目录执行：

```bash
git add src/services/api/chat/chatEvents.ts src/services/api/chat/chatEvents.test.ts src/services/api/chat/streamApi.ts
git commit -m "refactor(chat): centralize SSE event contract in chatEvents.ts"
```

---

### Task 5: 全量回归 + 规范自审

**Files:** 无新改动（验证 + 按需修复）

- [ ] **Step 1: 后端全量测试**

在 `CIOaas-python` 目录 Run: `uv run pytest tests/ -v`
Expected: 全部 passed（不只 chatbot——确认无跨模块破坏）

- [ ] **Step 2: 前端编译门禁复跑**

在 `CIOaas-web` 目录 Run: `npm run tsc`
Expected: 零错误

- [ ] **Step 3: 规范自审**

按子项目 CLAUDE.md 要求，对照 `CIOaas-python/standards/`（architecture.md / coding.md）与 `CIOaas-web/standards/` 审查本次全部改动：分层依赖方向（interfaces→application）、类型注解、命名、错误处理、无 console.log/print。发现不符合项就地修复并复跑对应测试。

- [ ] **Step 4: 收尾报告**

向用户汇报：改动文件清单、测试结果、`docs/superpowers/specs/2026-06-11-sse-event-contract-design.md` §4 为今后改事件的唯一入口。提醒：手动冒烟（dev 起服务发一条消息看流式 + chart + 异常路径）建议在合并前做一次。
