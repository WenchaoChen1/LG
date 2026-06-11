# SSE 事件契约统一 — 设计文档

- **日期**：2026-06-11（修订：纳入 2026-06-10 chat-chart 功能新增的 `chart` 事件；同日二次修订：新增 `title` 事件，见 `2026-06-11-chat-history-and-two-end-design.md` §3）
- **状态**：已批准（待实现）
- **范围**：`CIOaas-python`（chatbot 模块）+ `CIOaas-web`（chat services）
- **不涉及**：公共 `llm/.../sse.py` 原语、统一 endpoint、llm 模块对外契约、chart fence 解析逻辑本身
- **前置现状**：两个子仓库均有**未提交的 chat-chart 功能改动**（`CIOaas-python` 的 chat_service/routes/sse 等、`CIOaas-web` 的 streamApi/图表组件等）。本重构**叠加在这些改动之上**；建议实施前先提交 chat-chart 工作（由用户决定）。

---

## 1. 背景与问题

当前 chatbot 的 SSE 事件下发**散落在前后端多处**，靠人肉同步，没有单一 source of truth：

**后端 `chatbot/application/chat_service.py`** — 6 处裸序列化点：

```python
yield event_to_sse_bytes("thread", {"thread_id": thread_id})       # 行 44
yield event_to_sse_bytes("blocked", {"reason": msg})               # 行 61
yield event_to_sse_bytes("needs_pick", {"hint": msg})              # 行 68
return event_to_sse_bytes("chart", seg.spec)                       # 行 79（_seg_to_sse 嵌套函数）
return chunk_to_sse_bytes(TextChunk(delta=seg.text, is_final=False))  # 行 80（同上）
yield done_marker()                                                # 行 62 / 69 / 92
```

事件名是 magic string、payload 手搓 dict、序列化细节（`event_to_sse_bytes` / `chunk_to_sse_bytes` / `done_marker`）混进业务编排；`_seg_to_sse` 嵌套函数把"段→传输字节"的映射也埋在编排函数体内。

**前端 `services/api/chat/streamApi.ts`** — `handleFrame` 里一长串裸字符串 `if (event === 'thread' / 'needs_pick' / 'blocked' / 'chart' / 'error')` 分发 + 手搓 `parseJson` + 字段访问，外加行 40–47 一段**手写协议契约注释**靠人肉与后端对齐。

**问题**：改一个事件要同步改三处（后端业务代码、前端 handler、前端注释），**必然 drift**。chart 事件加入时三处各自长了一块，正是 drift 路径的现场演示。

此外有一个**已知缺口**：`chat_service` 的 `astream` 若抛异常，未包成 `error` 事件，异常直抛 ASGI（前端 `event: error` 已支持，但后端从不下发）。

---

## 2. 目标与非目标

**目标**

1. 后端事件下发收敛到**两个集中单点**（语义契约 + 传输序列化），`chat_service` 不再出现任何 SSE 序列化调用；
2. 前端事件消费收敛到**一个集中单点**，`streamApi.handleFrame` 不再裸 if-else；
3. 一份**权威契约文档**（本文档 §4 事件清单表）作为前后端唯一 source of truth；
4. 顺手补上 `astream` 异常 → `error` 事件的缺口。

**非目标（明确不做）**

- ❌ 统一 endpoint + `type` 路由（YAGNI：当前仅 chatbot 一个流式业务；等出现第 2、3 个再议）；
- ❌ 改动公共 `llm/.../sse.py` 4 个原语（保持零业务序列化）；
- ❌ 改动 `chart_fence_parser.py` 的解析逻辑（仅消费其 Segment 产物）；
- ❌ 调整 llm 模块对外契约（跨模块依赖既存沿用，见 §9）；
- ❌ codegen / 通用事件框架基类 / 事件名枚举（重型或冗余间接层，决策记录见 §11）。

---

## 3. 架构与分层

`CIOaas-python` DDD 依赖方向：`interfaces → application → domain ← infrastructure`，且 interfaces 只认 Request/Response、零业务逻辑。因此事件契约不能放 interfaces 再让 application 调（会违反依赖方向）。本设计采用 **1b**：

| 单点 | 位置 | 层 | 职责 |
|---|---|---|---|
| **语义契约** | `chatbot/application/chat_events.py`（新建） | application | 事件对象（有哪些事件 + 字段），零传输知识 |
| **传输序列化** | ~~`chatbot/interfaces/sse_events.py`~~ → **`llm/infrastructure/llm_router/sse.py`**（2026-06-11 用户决策合并） | llm 平台层 | 通用 `to_sse()`：TextChunk→文本帧、`StreamDone`→[DONE]、实现 `SSEEventLike` 协议（`sse_event()` 返回事件名+payload）的业务事件→结构化帧。**全部 SSE 机制在 llm 这一个文件**；业务事件在 `chat_events.py` 经 `sse_event()` 自描述 wire 形态（llm 零业务依赖、无反向 import） |
| **前端契约** | `services/api/chat/chatEvents.ts`（新建） | web service | 事件名常量 + payload 类型 + 分发器 |
| **文档契约** | 本文档 §4 | — | 前后端唯一权威 source of truth |

数据流：

```
chat_service (application)            routes._gen (interfaces)              前端
  产 ChatEvent 对象      ──yield──▶   to_sse(ev) 序列化 + try/except   ──SSE──▶  dispatchChatEvent(frame, cb)
  （零传输知识）                       异常 → error_to_sse_bytes(e)               按 event 名分发到回调
```

依赖方向校验：`routes`(interfaces) → `chat_service`/`chat_events`(application) ✅ 合规；application 不再 import `llm.infrastructure.llm_router.sse`（挪到 interfaces）。

---

## 4. 事件清单（权威契约表）

| 语义 | SSE 形态 | event 名 | payload | 触发点 |
|---|---|---|---|---|
| thread 开始 | 结构化事件 | `thread` | `{thread_id: string}` | 流最前 |
| 文本增量 | 文本流（无 event 名） | — | `{delta, is_final, finish_reason?, usage?}` | 合成流文本段 |
| 图表 | 结构化事件 | `chart` | ChartSpec `{type, title?, columns, rows}` | 合成流 ```chart fence 切出 |
| 标题已生成 | 结构化事件 | `title` | `{thread_id: string, title: string}` | 新建 thread 首轮，主文本流结束后、`[DONE]` 前 |
| 需选公司 | 结构化事件 | `needs_pick` | `{hint: string}` | 命中需澄清 |
| 被拦截 | 结构化事件 | `blocked` | `{reason: string}` | 图拦截 |
| 异常 | 结构化事件 | `error` | `{error_class, error_message}` | 流中抛错（routes 兜底） |
| 结束 | 标记 | — | `data: [DONE]` | 收尾 |

> 修改事件时，**先改本表**，再同步三个代码单点。
> 行为注记：合成流的末段 chunk（`is_final=True` 携带 finish_reason/usage）**不下发**（现状即如此——delta 为空被跳过），前端靠 `[DONE]` 终结。
> title 实现注记（2026-06-11）：触发条件实现为 **thread 尚无 title 即生成**（比字面"新建首轮"更稳——首轮 blocked/needs_pick 无正文时第二轮自动补）；标题经 `llm_db_router.acomplete` 生成（≤16 字 prompt、截 50 字符），**先 `repo.set_title` 落库再下发事件**（保证 `[DONE]` 后前端会话列表刷新必然拿到）；生成或落库失败只记 warning 跳过、不阻断主流程（title 留 None 下一轮重试）；客户端打断时不生成。前端侧边栏靠既有 `[DONE]` 后 `reloadThreads()` 显示新标题，`onTitle` 回调为契约出口、暂无消费方。

---

## 5. 后端设计

### 5.1 `chatbot/application/chat_events.py`（新建，语义契约单点）

```python
"""chatbot SSE 领域事件对象（application 层语义契约，零传输知识）。

定义"有哪些事件 + 字段"；序列化为 SSE bytes 由 interfaces/sse_events.py 负责。
文本增量直接复用 llm 的 TextChunk，不再包一层。
"""
from __future__ import annotations

from dataclasses import dataclass

from llm.infrastructure.capabilities.text import TextChunk  # 既存跨模块依赖，见 §9


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


# 文本增量原生透传 llm TextChunk；error 不在此列（由 routes 异常兜底产生）
ChatEvent = ThreadStarted | Chart | NeedsPick | Blocked | Done | TextChunk


# ── 事件工厂（统一产出口，2026-06-11 用户要求增补）────────────────────
# 业务编排（chat_service）一律经下列工厂产事件，不直接实例化 dataclass。

def thread(thread_id: str) -> ThreadStarted: ...
def chart(spec: dict[str, Any]) -> Chart: ...
def needs_pick(hint: str) -> NeedsPick: ...
def blocked(reason: str) -> Blocked: ...
def done() -> Done: ...
def text(delta: str) -> TextChunk: ...   # 恒非末段（is_final=False）
```

> `Chart` 是独立契约对象，不直接复用 `chart_fence_parser.ChartSegment`——解析器内部产物不外溢为对外事件契约（解析器重构不应牵动契约）。
> 工厂层使"事件的定义与构造"都收敛在 `chat_events.py` 这一个文件：`chat_service` 统一 `yield events.xxx(...)`（`from chatbot.application import chat_events as events`），连 `TextChunk(delta=..., is_final=False)` 的构造细节也不出现在业务编排里。

### 5.2 ~~`chatbot/interfaces/sse_events.py`~~（已删除——2026-06-11 用户决策：所有 SSE 序列化合并进 `llm/.../sse.py`）

> **现行实现**：llm `sse.py` 提供通用 `to_sse(ev)`（TextChunk→文本帧；`StreamDone` 哨兵→`[DONE]`；实现 `SSEEventLike` 协议的对象→`event_to_sse_bytes(*ev.sse_event())`；未知类型 TypeError）+ `stream_sse` 泵（`to_bytes` 默认即 `to_sse`，routes 无需传参）。chatbot 各事件 dataclass 在 `chat_events.py` 内实现 `sse_event() -> (事件名, payload)` 自描述 wire 形态，`Done = StreamDone` 别名。依赖方向 chatbot→llm 合规，llm 不反向 import 业务。下方为**历史设计稿**（评审时的 interfaces 层 match 版本），仅留档：

```python
"""chatbot 领域事件 → W3C SSE bytes（interfaces 传输层，唯一序列化点）。

事件名字符串 + payload 投影集中在此；调用 llm 公共 sse 原语完成字节序列化。
"""
from __future__ import annotations

from llm.infrastructure.capabilities.text import TextChunk
from llm.infrastructure.llm_router.sse import (  # 既存跨模块依赖，见 §9
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

### 5.3 `chat_service.stream_turn` 改造（产领域事件对象）

> **2026-06-11 增补**：实现已按 §5.1 工厂决策落地——`chat_service` 统一 `from chatbot.application import chat_events as events`，所有产事件语句为 `yield events.thread(thread_id)` / `events.blocked(msg)` / `events.needs_pick(msg)` / `events.done()`，`_seg_to_event` 内为 `events.chart(seg.spec)` / `events.text(seg.text)`。下方示意代码保留评审时的直接实例化形态，以工厂版为准。

基于**当前磁盘版本**（含 chart fence 集成 + assistant 落库 try/except）改造：

```python
# 删去 from llm.infrastructure.llm_router.sse import (...)（序列化挪到 interfaces）
# TextChunk import 保留（构造文本段事件仍需要）
from chatbot.application.chat_events import (
    Blocked, Chart, ChatEvent, Done, NeedsPick, ThreadStarted,
)
from chatbot.application.chart_fence_parser import (
    ChartFenceStreamParser, ChartSegment, Segment,
)

async def stream_turn(...) -> AsyncIterator[ChatEvent]:   # 返回类型由 bytes 改为 ChatEvent
    repo.append_message(thread_id=thread_id, role="user", content=question)
    yield ThreadStarted(thread_id)

    state = {...}  # 原样不动
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

    def _seg_to_event(seg: Segment) -> ChatEvent:
        # 图表段 → Chart 事件；文本段 → TextChunk（语义对象，非 SSE bytes）。
        if isinstance(seg, ChartSegment):
            return Chart(seg.spec)
        return TextChunk(delta=seg.text, is_final=False)

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

    # done 已下发、用户体验不中断；assistant 落库失败必须显式记日志（原行为保留）。
    try:
        repo.append_message(thread_id=thread_id, role="assistant", content="".join(buf),
                            attribution=result.get("attribution"),
                            used_tools=[t["tool"] for t in result.get("tool_results", [])])
    except Exception:
        logger.error("persist assistant message failed, thread_id=%s", thread_id,
                     exc_info=True)
```

### 5.4 `routes.py` 的 `_gen` 改造（序列化 + 异常兜底）

```python
import logging

from chatbot.interfaces.sse_events import to_sse
from llm.infrastructure.llm_router.sse import error_to_sse_bytes

logger = logging.getLogger("CIOaaS.chatbot.routes")

async def _gen():
    tid = uuid.uuid4().hex
    with trace_id_scope(tid), trace_scope(
        TraceContext(agent="chat", node="turn", user_id=ctx.user_id, trace_id=tid)
    ):
        try:
            async for ev in chat_service.stream_turn(...):  # 入参原样不动
                yield to_sse(ev)
        except Exception:  # noqa: BLE001 — 流中任何异常都兜底成 error 事件
            logger.error("chat stream failed, thread_id=%s, trace_id=%s",
                         thread_id, tid, exc_info=True)
            yield error_to_sse_bytes(RuntimeError("服务暂时不可用，请稍后重试"))

return StreamingResponse(_gen(), media_type="text/event-stream")
```

> 注 1：`error_to_sse_bytes` 是 llm 公共原语（与 `to_sse` 同属传输序列化），由 routes 直接调用——error 事件不经 application（异常本就是传输层兜底语义）。
> 注 2（2026-06-11 审查修订）：原始异常**详情只进服务端日志**（`exc_info=True`，含 thread_id/trace_id），客户端只收到净化的通用文案——`str(e)` 可能含 DSN / 内部 URL / SQL 片段，不得透传给终端用户（standards/coding.md「错误消息不泄露敏感数据」）。`except Exception`（非 BaseException）保证 `GeneratorExit` / `CancelledError` 正常传播。

---

## 6. 前端设计

### 6.1 `services/api/chat/chatEvents.ts`（新建，前端契约单点）

```typescript
import type { SSEFrame } from '@/services/sse';
import type { ChartSpec } from './chatDto';

export const CHAT_EVENT = {
  THREAD: 'thread',
  CHART: 'chart',
  NEEDS_PICK: 'needs_pick',
  BLOCKED: 'blocked',
  ERROR: 'error',
} as const;

export interface ThreadPayload { thread_id?: string }
export interface NeedsPickPayload { hint?: string }
export interface BlockedPayload { reason?: string }
export interface ErrorPayload { error_class?: string; error_message?: string }
export interface TextDeltaPayload { delta?: string; is_final?: boolean; finish_reason?: string }

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
  try { return JSON.parse(data) as T; } catch { return null; }
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

  if (data === '[DONE]') { cb.onDone?.(); return true; }

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
  if (p.is_final) { cb.onDone?.(p.finish_reason); return true; }
  return false;
}
```

### 6.2 `streamApi.ts` 收敛

- 删除本地 `ChatDeltaPayload` / `parseJson` / chart 校验逻辑（移入 chatEvents.ts）；
- 删除行 40–47 手写协议契约注释（契约移到本 spec §4）；
- `StreamChatCallbacks` 改为 `ChatEventCallbacks` 的 re-export 别名（`export type StreamChatCallbacks = ChatEventCallbacks`），调用方（`useChatStream` 等）import 路径零改动；
- `handleFrame` 收敛为：

```typescript
import { dispatchChatEvent } from './chatEvents';
import type { ChatEventCallbacks } from './chatEvents';

const handleFrame = (frame: SSEFrame): void => {
  if (finished) return;
  if (dispatchChatEvent(frame, cb)) finished = true;
};
```

其余（`streamSSE` 调用、token/header 注入、`onError`/收尾 `onDone`）保持不变。**现有 `streamApi.test.ts`（5 个测试）不改动**，重构后必须全绿——这是行为不变的回归证明。

---

## 7. 错误处理

| 场景 | 处理 |
|---|---|
| `astream`/图执行抛异常 | `routes._gen` 的 `try/except` 兜底：服务端 `logger.error(..., exc_info=True)` 记详情（thread_id/trace_id），客户端下发**净化**的 error 事件（通用文案，不泄露原始异常文本），不再直抛 ASGI；error 即终结流（其后无 `[DONE]`） |
| assistant 落库失败 | 原行为保留：不中断流（Done 已下发），`logger.error(..., exc_info=True)` |
| chart payload 结构非法 | 前端 `isValidChartSpec` 校验失败丢弃不分发（原行为保留） |
| 前端收到 `event: error` | `dispatchChatEvent` → `cb.onError`，返回 true 终结流 |
| 未知 ChatEvent 类型 | `to_sse` 抛 `TypeError`（开发期暴露，被 routes `except` 兜底成 error 事件） |

行为保持：`needs_pick` / `blocked` 后仍由后端 `Done()` → `[DONE]` 终结流；assistant 消息在 `Done()` 之后落库（与现状行序一致）。

---

## 8. 测试

**后端**（`tests/chatbot/`，pytest，`uv run pytest`）

- `interfaces/test_sse_events.py`（新建）：`to_sse` 对每种 ChatEvent → 期望 SSE bytes（`thread` / `chart` / `needs_pick` / `blocked` / `Done` → `[DONE]` / `TextChunk` → `data:` 帧）；未知类型抛 `TypeError`。
- `application/test_chat_service.py`（**改造现有 4 个测试**）：断言从"拼接 bytes 找子串"改为"事件对象序列"——正常流 `ThreadStarted → TextChunk… → Done`；needs_pick 流 `ThreadStarted → NeedsPick → Done`；chart 流含 `Chart(spec)` 且落库含 fence 原文；persist-fail 流不中断且记日志。
- `interfaces/test_routes.py`（增补 2 个）：`POST /api/ai/chat` 全链路——mock `stream_turn` 产事件对象，断言响应文本含 `event: thread` / delta / `[DONE]`；mock `stream_turn` 抛异常，断言响应含 `event: error`。

**前端**（jest；⚠️ 测试基架当前损坏——jest.config 指向缺失的 `tests/PuppeteerEnvironment`，单测跑不起来，**门禁以 `npm run tsc` 为准**，勿临时改测试基架）

- `services/api/chat/chatEvents.test.ts`（新建）：`dispatchChatEvent` 各事件帧分发到正确回调；`[DONE]` / `is_final` / `error` 返回 true 终结；chart 非法结构丢弃；非法 JSON 不崩。基架修复后即可执行。
- `services/api/chat/streamApi.test.ts`（**不改**）：契约保留；基架修复后作为行为不变的回归证明。
- 实际验证门禁：`npm run tsc` 零错误 + 人工 review。

---

## 9. 已知既存瑕疵（不在本次范围）

跨模块依赖：`chatbot.interfaces.sse_events` / `chatbot.application.chat_events` import `llm.infrastructure.llm_router.sse` 与 `llm.infrastructure.capabilities.text`。按 `standards/architecture.md` §2.1，跨模块**应只调对方 `application/`**，调 `infrastructure` 属违规。

- 此依赖**重构前已存在**（`chat_service` 当前就 import 这两个路径）；1b 只是把 sse 原语依赖从 application 平移到 interfaces，并未新增。
- 本次**沿用、不扩大范围**。
- 可选后续（独立任务）：由 `llm.application` re-export SSE 序列化能力与 `TextChunk` 类型，chatbot 改调 `llm.application`，彻底合规。

---

## 10. 影响文件清单

**新建（3）**

- `CIOaas-python/source/chatbot/application/chat_events.py`
- `CIOaas-python/source/chatbot/interfaces/sse_events.py`
- `CIOaas-web/src/services/api/chat/chatEvents.ts`

**修改（3）**

- `CIOaas-python/source/chatbot/application/chat_service.py`（yield 事件对象、去 sse import、`_seg_to_sse`→`_seg_to_event`、返回类型 `AsyncIterator[ChatEvent]`）
- `CIOaas-python/source/chatbot/interfaces/routes.py`（`_gen` 序列化 + try/except 兜底 error）
- `CIOaas-web/src/services/api/chat/streamApi.ts`（handleFrame 收敛、删契约注释与本地 parseJson/chart 校验、StreamChatCallbacks 改 re-export 别名）

**测试（4）**

- `CIOaas-python/tests/chatbot/interfaces/test_sse_events.py`（新建）
- `CIOaas-python/tests/chatbot/application/test_chat_service.py`（改造现有 4 个测试的断言方式）
- `CIOaas-python/tests/chatbot/interfaces/test_routes.py`（增补 2 个 send 流式测试）
- `CIOaas-web/src/services/api/chat/chatEvents.test.ts`（新建；`streamApi.test.ts` 不改、作回归）

---

## 11. 决策记录

| 决策点 | 选择 | 备选与否决理由 |
|---|---|---|
| endpoint 形态 | 一业务一 endpoint，不动 | 统一 `type` 路由总入口：union request 违反传输实体规范、鉴权纠缠、当前仅 1 个流式业务（YAGNI） |
| 契约一致性 | 两端集中模块 + 文档 | codegen：6-7 个事件收益有限、引入构建步骤；通用基类：无第二实现验证、过度设计 |
| 后端落点 | 1b（application 产事件对象、interfaces 序列化） | 1a（application 直接产 bytes）：改动更小但 application 携带传输知识，分层不纯 |
| 事件名枚举 | 不加 | dataclass 类型本身已是类型安全的事件标识且连 payload 字段一起管住；事件名字符串只在 `to_sse` 出现一次，枚举是冗余间接层 |
| 事件工厂 facade | 加（用户决策，2026-06-11） | chat_service 统一经 `chat_events` 工厂函数产事件、不直接实例化 dataclass——"定义+构造"单点化，TextChunk 构造细节也收走；代价是一层薄间接 |
| 序列化归属 | 合并进 llm `sse.py`（用户决策，2026-06-11） | 删除 `chatbot/interfaces/sse_events.py`；llm 提供通用 `to_sse` + `SSEEventLike` 协议 + `StreamDone` 哨兵，业务事件 `sse_event()` 自描述 wire 形态。否决"llm 直接 import chatbot 事件类型"（平台层反向依赖业务，违反 standards §2.1）——协议方案同样实现"全部 SSE 机制一个文件"且合规 |
| Chart 事件对象 | 独立 `Chart` dataclass，不复用 `ChartSegment` | 解析器内部产物不外溢为对外契约；映射成本仅 `Chart(seg.spec)` 一行 |
