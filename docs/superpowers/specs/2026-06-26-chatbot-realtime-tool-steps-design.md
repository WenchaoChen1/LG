# AI Chatbot 实时工具步骤（Realtime Tool Steps）设计文档

- 日期：2026-06-26
- 范围：CIOaas-python（chatbot / ai 域）+ CIOaas-web（chat 页）
- 方案：方案 A —— LangGraph 原生 custom stream
- 关联现状：`docs/AI-Chatbot/设计/design-doc.md`、`docs/superpowers/specs/2026-06-11-sse-event-contract-design.md`

## 1. 背景与目标

### 现状

ReAct 取数节点 `retrieve_node`（`ai/chatbotgraph/retrieval_agents/retrieval_agent.py`）用
`create_react_agent` 驱动有界 ReAct 循环，由模型自主决定调哪些工具。但 `chat_turn`
（`chatbot/application/chat_turn.py:109`）对整张 chat_graph 用 **`await graph.ainvoke(state)`**
阻塞跑完，工具调用过程无法实时冒泡到 SSE 流。

当前用户可见的 `tool_step` 事件是在**取数全部完成后一次性下发**（`chat_turn.py:158-160`），
且 `ToolStep.status` 恒为 `ok`（预留态），前端 `ToolStepsCard` 每行渲染 `✓ + label`。

### 目标

把工具步骤卡片从「取数完一次性下发」改为「agent 每调一个工具就实时冒出」，并支持
**两态：进行中（running）→ 完成（ok / error）**，让用户实时看到「正在查询财务数据… → ✓ 已查询」。

### 非目标（YAGNI）

- 不展示 agent 的真实 reasoning token（中文内部推理，脱敏成本高）。
- 不展示工具中间结果数据（只展示步骤名 + 状态）。
- 不合并两段式：synthesis 二次流式成文、落库、停止语义**全部保留不变**。

## 2. 关键技术事实（已核实）

- **LangGraph 0.3.34**（`pyproject.toml` / `requirements.txt`）支持 `stream_mode="custom"`
  + `langgraph.config.get_stream_writer()`。
- **SSE 序列化零改动**：`sse/infrastructure/serializer.py` 的 `event_to_sse_bytes` 经
  `asdict(event)` 序列化整个 dataclass，给 `ToolStep` 加字段自动上 wire。
- **前端链路已存在**：`chatEvents.ts`（`tool_step` 解析 + `onToolStep`）→ `useChatStream.ts`
  → `messageReducer.ts`（`appendToolStep`）→ `ToolStepsCard.tsx`（渲染 steps）。

## 3. 架构改动总览

一句话：把 `chat_turn` 对 chat_graph 的驱动从 `ainvoke` 换成
`astream(stream_mode=["custom","values"])`，retrieve_node 工具执行时实时推 `tool_step`
原始信号，chat_turn 转成 `ToolStep` 领域事件，前端按 `step_id` 合并 running→ok。

```
retrieve_node 工具 _run（ai 域）
  --custom 帧--> chat_graph.astream
                   --> chat_turn 消费 custom 帧（chatbot 域）
                        --> ToolStep 领域事件（拼英文文案）
                             --> sse serializer --> 网关 --> 前端 upsert by step_id
chat_graph.astream 的 values 帧 --> chat_turn 留最后一帧 final_state --> synthesis 段（不变）
```

## 4. 事件契约：`chat_events.ToolStep`

```python
@dataclass(frozen=True)
class ToolStep(_ChatEvent):
    _SSE_NAME: ClassVar[str] = "tool_step"
    step_id: str          # 新增：同一工具调用 running/ok 共用，前端据此合并两态
    label: str            # 英文友好文案（产品侧，chatbot 域生成）
    tool: str             # 工具名，前端选图标
    status: str = "running"  # running | ok | error
```

- wire 形态由 `asdict` 自动产出，serializer 不改。
- `status` 三态语义：
  - `running`：工具调用发起、尚未返回。
  - `ok`：工具成功返回。
  - `error`：工具失败（前端灰显，不阻断后续）。

## 5. 后端数据流（双流分流）

### 5.1 chat_turn（chatbot 域）

```python
final_state = None
async with aclosing(get_chat_graph_app().astream(
        state, stream_mode=["custom", "values"])) as stream:
    async for mode, chunk in stream:
        if mode == "custom":
            ev = _custom_to_tool_step(chunk)   # 原始信号 → ToolStep（拼 label）
            if ev is not None:
                yield ev
        elif mode == "values":
            final_state = chunk                # 留最后一帧
result = final_state or {}
# 以下沿用现状：blocked / needs_company_pick 分支 + synthesis astream 成文 + 落库
```

- **删除**现状 `chat_turn.py:158-160`「取数完一次性下发 ToolStep」循环（被实时事件取代）。
- `_custom_to_tool_step(chunk)`：读 `{kind, step_id, tool, status, company_name}`，用现有
  `_TOOL_STEP_LABELS` 拼 label（running="Querying …"、ok="Queried … for X"），产 `ToolStep`。
  非 `kind=="tool_step"` 的 custom 帧忽略（前向兼容）。
- 标题并发 task（`generate_title`）、停止/取消 finally 落库逻辑保持不变。

### 5.2 retrieve_node（ai 域）

**关键决策**：不依赖「工具内 `get_stream_writer()` 穿透手动 `ainvoke` 的 react agent 子图」
这一不确定点。改为在 **retrieve_node 主体**（确定在 chat_graph 节点上下文）取 writer，
注入工具闭包，工具内直接调用 writer 引用。

```python
from langgraph.config import get_stream_writer

async def retrieve_node(state):
    writer = get_stream_writer()          # 节点主体一定可用；非 custom 驱动时为 no-op
    ...
    tools = [t for t in _dispatch_tools(dispatch, acc, writer) if t.name not in disabled]
    ...

def _dispatch_tools(dispatch, acc, writer):
    def _make(schema_tool):
        async def _run(**llm_args):
            sid = acc.next_step_id()      # asyncio 单线程，计数器自增即唯一
            writer({"kind": "tool_step", "step_id": sid, "tool": schema_tool.name,
                    "status": "running", "company_name": None})
            out = await dispatch(schema_tool.name, llm_args)
            acc.record(schema_tool.name, llm_args, out)
            writer({"kind": "tool_step", "step_id": sid, "tool": schema_tool.name,
                    "status": "ok" if out.get("ok") else "error",
                    "company_name": _resolve_company_name(out, ctx)})
            return default_summary(out)
        return StructuredTool(...)
    return [_make(t) for t in TOOL_REGISTRY]
```

- `writer` 同步可调用，async 工具内直接调用无问题。
- `step_id`：`_Accumulator` 增 `next_step_id()` 计数器（`str(self._seq)`，自增）。
- **公司名实时性**：
  - `running` 态此时 cid 未解析 → `company_name=None`。
  - `ok` 态：`dispatch` 在结果 dict 回填 resolved company_id（**内部字段，不进回喂 LLM 的
    `default_summary`**），retrieve_node 用 `ctx["accessible"]` 映射成名字。
- 产品文案（`_TOOL_STEP_LABELS`）留 chatbot 域；ai 域只产 tool/status/company_name 原始数据，符合分层。
- react agent 仍用 `agent.ainvoke`（不变），`_Accumulator` 结果收集不变，`_classify_closeout`
  收尾逻辑不变。

## 6. 前端改动（按 step_id 合并两态）

| 文件 | 改动 |
|---|---|
| `services/api/chat/chatEvents.ts` | `ToolStepPayload` + `onToolStep` 回调加 `step_id`；`status` 透传 running/ok/error |
| `pages/ai/chat/utils/messageReducer.ts` | `ToolStepInfo` 加 `stepId`；`appendToolStep` 改 **upsert**：按 `stepId` 命中则更新 status，否则追加 |
| `pages/ai/chat/components/ToolStepsCard.tsx` | 按 status 渲染：`running`→spinner、`ok`→✓、`error`→✗（灰显）；`key` 用 `stepId` |
| `pages/ai/chat/hooks/useChatStream.ts` | `onToolStep` 透传 step_id（字段/类型扩展） |

历史加载（`load` 路径）的消息不携带 steps（与改造前一致——steps 仅由实时 `appendToolStep` 产生），故历史 assistant 消息不渲染工具步骤卡片，行为不变。

## 7. 错误 / 取消处理

- **astream 取消**（用户停止 / 断连）：`aclosing(graph.astream(...))` 确定性关闭；retrieve
  段被取消不落 assistant（与现状一致——assistant 仅在 synthesis 段落库）。
- **工具失败**：发 `status:"error"`，前端灰显该步、不阻断后续。
- **GraphRecursionError**：仍 catch 在 retrieve_node 内部（agent.ainvoke 在节点里跑）；已发
  running 由对应 ok/error 收尾。极端情况（到上限未收尾）残留 running：前端兜底——synthesis
  首个 delta 到达时把所有残留 running 视为完成。

## 8. 测试点

- **chat_turn**（`tests/chatbot/application/`）：mock graph.astream 产 custom+values 混合流，
  断言产出的 ToolStep 顺序 / status 配对、final_state 正确进 synthesis、删除旧一次性下发后
  无重复 ToolStep。
- **retrieve_node**（`tests/ai/chatbotgraph/`）：mock writer，断言每个工具调用产 running +
  ok/error 两帧、step_id 配对、`default_summary` 回喂内容**不含**内部 resolved cid。
- **前端 reducer 单测**：同 stepId 的 running→ok upsert 不新增行；error 态渲染。

## 9. 实施顺序与风险

1. **Spike（先做）**：~10 行验证 chat_graph.astream(stream_mode=["custom","values"]) +
   retrieve_node 主体 `get_stream_writer()` 写一帧，确认 chat_turn 收到 custom 帧。
   因 writer 在**节点主体**取（非工具内），属 LangGraph 官方标准用法，风险低；spike 仅确认
   版本行为。若异常，退路为方案 C（retrieve_node 用 `agent.astream` 解析 updates）。
2. 后端事件契约 + retrieve_node writer 注入。
3. 后端 chat_turn 双流分流 + 删旧一次性下发。
4. 前端两态合并渲染。
5. 后端 + 前端测试。
6. 规范自查（standards 审一遍）。

## 10. 验收标准

- 用户发起一次需多工具的提问，能**实时**看到步骤逐个出现，每步先 spinner 后 ✓。
- 工具失败的步骤显示 ✗ 灰显，回答仍正常流式产出。
- 停止 / 断连 / 续流行为与现状一致（无回归）。
- 后端 / 前端测试通过，覆盖率 ≥ 80%。
