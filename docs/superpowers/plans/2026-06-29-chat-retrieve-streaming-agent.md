# 方案：聊天取数改造为「原生工具 + 单流式 ReAct agent」

> 关联文档：[design-doc](../../AI-Chatbot/设计/design-doc.md)、[dev-design-doc](../../AI-Chatbot/开发设计/dev-design-doc.md)、[断流恢复](./2026-06-15-ai-chatbot-resume-streaming.md)、[SSE 事件契约](../specs/2026-06-11-sse-event-contract-design.md)
>
> 状态：方案（不含代码改动）。三块改动按依赖排序，块①含一个必须先验证的「地基未知」。
> 性质：跨 `llm`（流式竖切）+ `ai`（取数节点）+ `chatbot`（单轮编排/SSE）三模块。

---

## 1. 目标

| # | 目标 | 当前痛点 |
|---|------|----------|
| 1 | retrieve 取数阶段把**思考/工具进度**实时给前端，消灭长时间转圈 | retrieve 内模型调用是 `acomplete`（非流式），取数期间前端只能转圈 |
| 2 | **单流 + 合并答案**：最终英文答案 = retrieve agent **同一上下文末轮**流式产出，SSE 收成一条流 | 最终答案是图外**另起**一次 `llm_db_router.astream`（200 行），与取数两段隔离 |
| 3 | **原生工具执行**：去掉中央 `dispatch(name,args)`，每个工具自包含、交 LangChain `create_agent` 的 ToolNode 直调 | 取数走中央 `dispatch` 名字路由 + `_dispatch_tools` 包装，手工重做了 ToolNode 已做的事 |

> 已选方案 = **A**（融进 retrieve，一个模型上下文里既调工具又出最终答案），非「synthesis 作独立末节点」的折中。

---

## 2. 现状与根因（已对照真实代码）

**① 转圈根因**：`retrieve_tool_node` 用 `create_agent(...).ainvoke(...)`（[retrieval_agent.py:118](../../../python/CIOaas-python/source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py)），底层 `DBRouterChatModel` 只实现了 `_agenerate`（[chat_model.py:81](../../../python/CIOaas-python/source/llm/infrastructure/langchain/chat_model.py)）——无 `_astream`。模型思考/决定工具的整段时间是静默的，只有工具**边界**上的 `custom` 帧能下发 ToolStep 卡片。

**② 两段隔离**：图（含 retrieve）整个 `astream` 跑完 → `build_synthesis` 攒出 `synthesis_messages` → `chat_turn` 在**图外**再起第二次 `llm_db_router.astream`（[chat_turn.py:200](../../../python/CIOaas-python/source/chatbot/application/chat_turn.py)）流式生成答案。两次调用、两套 SSE 阶段逻辑。

**③ dispatch 间接层**：工具执行经中央 `dispatch(name, args)`（[retrieval_agent.py:202-252](../../../python/CIOaas-python/source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py)）的大 if/elif 路由 + `_dispatch_tools` 包装（[:284-312](../../../python/CIOaas-python/source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py)）。LangChain 的 ToolNode 已能做「tool_call→工具→执行」，这层是手工重做。

**流式可行性结论**（三个 Explore 子代理已摸）：带工具的流式在 llm 模块**每层都缺**——见 §4。

---

## 3. 三块改动 + 依赖/顺序

| 块 | 内容 | 依赖 | 风险 | 模块 |
|----|------|------|------|------|
| ① | llm 流式竖切（带工具的 `_astream`） | 无（但有「地基未知」） | 高 | `llm` |
| ② | retrieve 原生工具重构（去中央 dispatch） | 无，可独立先落 | 低 | `ai` |
| ③ | 合并 synthesis + SSE 单流 | **依赖 ①** | 中 | `ai` + `chatbot` |

**落地顺序**：地基验证 → ②（独立、低风险、先见效）→ ①（llm 竖切）→ ③（合并）。

---

## 4. 块①：llm 模块流式竖切（带工具的 `_astream`）

口径：**末段整块交付 tool_calls、不做逐 token 增量**——前端「在调什么工具」靠 ToolStep 卡片（`custom` 帧），不需要把工具参数一个字一个字流出来；只有最终答案那一轮需要 token 级流。

### 4.1 地基验证（✅ 已通过 — 2026-06-29）

`ChatOpenAI` / `ChatAnthropic` 的 `.astream` 在 `bind_tools` 之后，能否「**流正文 token + 末段给出完整 tool_calls**」？这是整条链能否成立的地基。

**已用一次性脚本（OpenRouter + Anthropic Sonnet，绑假工具 `get_weather`）实测，结论 = 成立**：

- **调工具轮**：先流正文 token（`'Sure'` / `'! Let me fetch...'`），再流 `tool_call_chunks` 增量（name → args delta `{"city": "Paris` → `"}`），拼装后的 FINAL 消息**同时带正文 + 完整 `tool_calls`**（`[{'name':'get_weather','args':{'city':'Paris'},...}]`）。
- **纯答案轮**：正文 token 逐块流出，无 tool_call_chunks，FINAL.tool_calls 空。

**实测坐实的关键点**：调工具轮里模型**默认会先吐一句正文 preamble**（"Sure! Let me fetch..."）。故决策 (d)「调工具轮禁止输出正文」**是必需而非可选**；消费侧再兜一道——**只渲染「无 tool_calls 的末轮」content，调工具轮的 content 一律丢弃**（防 prompt 偶发不遵守）。

> 落地提示：底层 `ChatOpenAI.astream` 本就产出带 content + tool_call_chunks 的 `AIMessageChunk`；kernel 流式路径当前只取 `.content` 丢了 tool_call_chunks。改点 = 在 `TextChunk` 保留 tool_call_chunks，`_astream` 据此重建 `AIMessageChunk(content, tool_call_chunks)` 透传，LangChain 自动拼装。

### 4.2 逐层改点

| 层 | 改点 | 文件 |
|----|------|------|
| 适配器 | 新增 `_astream`：流式 yield content chunk；末 chunk 挂完整 tool_calls（`tool_call_chunks`），供 `create_agent` 拼装执行 | [chat_model.py:81](../../../python/CIOaas-python/source/llm/infrastructure/langchain/chat_model.py) |
| router | `astream` 签名加 `tools` / `tool_choice` 并透传 `_build_text_request`（`acomplete` 已有、astream 缺） | [llm_router_db_service.py:263](../../../python/CIOaas-python/source/llm/application/router/llm_router_db_service.py) + [base.py:231](../../../python/CIOaas-python/source/llm/infrastructure/llm_router/base.py) |
| 契约 | `TextChunk` 加一个「末段 tool_calls」字段（整块，非增量结构） | [capabilities/text.py:77](../../../python/CIOaas-python/source/llm/infrastructure/capabilities/text.py) |
| kernel | 流式路径补 `bind_tools`；轮末用现成 `_extract_tool_calls` 把完整 tool_calls 挂到末 chunk | [openai_compat/chat.py:296](../../../python/CIOaas-python/source/llm/infrastructure/kernel/openai_compat/chat.py)、[anthropic_native/chat.py:160](../../../python/CIOaas-python/source/llm/infrastructure/kernel/anthropic_native/chat.py) |
| 落库 | **免改**（见下） | [llm_router_db_service.py:682](../../../python/CIOaas-python/source/llm/application/router/llm_router_db_service.py) |

> **落库层免改的实证依据**：非流式 tool 路径（`acomplete` 带 tools）**本就不单独持久化 tool_calls**（只存 `result.content` 进 `msg_assistant`）。流式为保持**一致**同样不持久化——tool_calls 只搭在末段 TextChunk 上交给适配器，DB 仍存累积正文 + usage/cost（已验证）。原计划"扩存 tool_calls"经核对属过度设计，撤掉。
>
> **块① 状态：✅ 已实现并验证（2026-06-29）**。改了 4 层（契约/kernel 双协议/router astream/适配器 `_astream`），落库层免改。验证：①真实 LLM probe——`DBRouterChatModel.bind_tools([...]).astream(...)` 流正文 + 末段拼出完整 `tool_calls`（调工具轮）/ 纯答案轮 tool_calls 空；②`tests/llm/test_chat_model.py` 新增 2 个确定性 `_astream` 单测通过。既有非工具流式（synthesis 200 行）`tools=None` 走原路径、零行为变化。

---

## 5. 块②：retrieve 原生工具重构（去中央 dispatch）

**删**：`dispatch(name, args)` 中央路由（[retrieval_agent.py:202-252](../../../python/CIOaas-python/source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py)）、`_dispatch_tools` 的「经 dispatch」间接层。

**改成**：每个工具 = 一个工厂闭包 over `ctx`，工具体直接干（把现散在 `_run` + `dispatch` 两处的逻辑收进单工具）：

```
writer running 帧 → (公司域) _cid 收敛 → 调底层函数(注入 auth) → acc.record → writer ok/error 帧 → return default_summary
```

- `_cid`（[:179-200](../../../python/CIOaas-python/source/ai/chatbotgraph/retrieval_agents/retrieval_agent.py)）提成 ctx 闭包**共享 helper**，只被公司域工具（detail/financial/benchmark/normalization）调；`list_companies` / `run_analysis` 不调。
- `CompanyScopeError → scope_error_result` 移进各公司域工具体。
- **disabled** 只靠绑定层 `if t.name not in disabled` 不绑（模型看不到），删 dispatch 兜底拦截。
- LangChain ToolNode 直接调这些工具，**不再有中央 name→函数 switch**。参照 text2sql `_build_run_sql_tool` 的闭包模式扩到 6 个工具。

**行为等价校验点（重构必须保持）**：公司名→UUID 收敛、scope 软拒、`_meta` 三态收尾（`_classify_closeout`）、tool-step 卡片、`_Accumulator` 全留结果——全不变。

---

## 6. 块③：合并 synthesis + SSE 单流（✅ 已实现并验证 — 2026-06-29）

> **状态**：完成。retrieve 节点改为 `agent.astream(stream_mode="messages")`，先调工具再写答案，答案
> token 经 stream writer 推 `custom` 帧 `answer_delta`；删了 `build_synthesis` 节点（`chatbot_build_synthesis.py`
> 删除）+ 端点二次 synthesis astream；`agent_system()` 合并 ORCHESTRATOR 前导 + SYNTHESIS 成文规则 +
> 决策(d)；needs_pick 结构化（need_company 且无结果 → 抑制答案 + `needs_company_pick`）；标题在**答案首帧前**
> 经 `_flush_title` 发出（保留 title-before-text）；sql 占位轨/空答案有英文兜底。**spike 修正**：外层 messages
> 模式抓不到嵌套 agent，改 custom writer（见 §6.2）。测试：`test_chat_graph`(5,端到端流式) /
> `test_retrieval_agent`(21) / `test_chat_turn`(19) / 三目录共 179 passed。落库层免改（与非流式 tool 路径一致）。


### 6.1 节点与图

- `retrieve` 节点升级为「**工具 + 末轮英文答案**」单 agent；system prompt = `ORCHESTRATOR_SYSTEM` + `SYNTHESIS_SYSTEM` 合并（取数指令 + 成文/英文/chart 围栏指令）。
- **删** `build_synthesis` 节点 + `chat_turn` 200 行那次独立 astream。
- guardrail blocked → END（已有）。

### 6.2 chat_turn 改消费一条流（spike 修正：custom writer，非 messages 模式）

> **spike（2026-06-29）实证**：外层 `graph.astream(stream_mode="messages")` **抓不到**节点内 `agent.ainvoke()` 的 token（ainvoke 走 `_agenerate` 非流式，一帧不出）。可行解 = **节点内自己流**：`retrieve_node` 内跑 `agent.astream(stream_mode="messages")`，把答案 token 经 **custom writer** 推成 `answer_delta` 帧。tool 步骤与答案都走 **custom 一条流**，不依赖外层 messages 模式。

`graph.astream(stream_mode=["custom","values"])`，单循环分流：

| 帧 | 处理 |
|----|------|
| `custom` `kind=answer_delta` | 答案文本增量，经现有 `ContextPrefixStripper` + `ChartFenceStreamParser` + buf |
| `custom` `kind=tool_step` | ToolStep 卡片（沿用块② 的 writer） |
| `values` 末帧 | blocked / needs_company_pick 短路 + 落库元数据（attribution / used_tools） |

`buf` 累积 / 先落库再 `Done` / 打断 `partial` 兜底，从 200 行那处迁过来。

**区分调工具轮 vs 答案轮**：`retrieve_node` 的 astream 循环里——chunk 带 `tool_call_chunks` = 调工具轮（不推 `answer_delta`）；纯 content chunk = 答案轮（推 `answer_delta`）。配合决策 (d)（调工具轮不出正文），content 即答案。

**needs_pick（决策 b）保留结构化**：scope 歧义在工具返回时（答案轮之前）发生 → `_Accumulator` 记 `need_company`。`retrieve_node` 一旦发现 `need_company` 失败且无成功结果，**就不推答案 token**（answer_delta 不发），节点返回 `needs_company_pick` 状态；chat_turn 读 `values` 照旧发结构化 `NeedsPick`。时序上工具失败先于答案轮，拦得住。

### 6.3 已定决策（本次拍板）

- **(a) 答案数据源 = 全量**：合并后答案由同一模型从上下文写出，故回喂给模型的工具结果**从 `default_summary` 摘要改为全量内容**（保答案质量；token 成本上升可接受）。需复核单轮上下文是否超模型窗口，必要时只对超大表做投影。
- **(b) needs_company_pick = 保留结构化**：不改成 agent 自然语言追问。`_cid` 歧义/越界仍产结构化 `_meta(clarify)` → `chat_turn` 短路发结构化 `NeedsPick` 事件（前端公司选择器不变）。即合并后**仍需在「进 synthesis 末轮」之前判定 needs_pick 并短路**，不让 agent 写答案。
- **(c) 模型 = Sonnet**：取数 + 答案同一上下文，统一用 `Models.openrouter.text.sonnet`（不降级取数模型）。
- **(d) 防泄漏约束**：系统提示硬加「**决定调工具的轮次只输出 tool_calls、不准输出正文**；只有拿齐数据要给用户最终答案时才输出正文」。顺带根治此前「假 tool-call JSON 泄漏进答案」的问题。前端只渲染「无 tool_calls 的末轮」content。

---

## 7. 风险与对抗点

| 风险 | 缓解 |
|------|------|
| **地基未知**（块①最高）：bind_tools-in-stream 行为 | §4.1 先验证，不成立则方案 A 不可行、回退讨论 B（仅 retrieve 流式、保留两次调用） |
| 多轮思考文字/假 JSON 泄漏进答案 | 决策 (d) 系统提示约束 + 只渲染无 tool_calls 末轮 |
| 全量回喂撑爆上下文（决策 a） | 复核窗口；超大表投影；保留逐工具 summary 作 fallback 开关 |
| 落库 partial/success 时序 | 流式 begin/finish 已有；扩 tool_calls 字段；迁移后回归打断场景 |
| needs_pick 与流式末轮竞态（决策 b） | 在末轮 content 流出**之前**用 `values`/`_meta` 判定短路 |

---

## 8. 影响面（文件清单）

- **块①**：`llm/infrastructure/langchain/chat_model.py`、`llm/application/router/llm_router_db_service.py`、`llm/infrastructure/llm_router/base.py`、`llm/infrastructure/capabilities/text.py`、`llm/infrastructure/kernel/{openai_compat,anthropic_native}/chat.py`
- **块②**：`ai/chatbotgraph/retrieval_agents/retrieval_agent.py`（主）、可能动 `ai/tools/*` 工具定义
- **块③**：`ai/chatbotgraph/{chat_graph,nodes}.py`、`chatbot/application/chat_turn.py`、`ai/prompts/chatbot/prompts.py`
- **测试**：`tests/llm/`、`tests/ai/chatbotgraph/`、`tests/chatbot/application/`

---

## 9. 分阶段落地步骤

1. **地基验证**（§4.1）：确认 bind_tools-in-stream 行为 → 决定方案 A 是否成立。
2. **块②**：retrieve 去中央 dispatch、改原生工具（行为等价，独立可测）→ 回归 `tests/ai/chatbotgraph/`。
3. **块①**：llm 五层竖切 → `tests/llm/` 补流式带工具用例（mock vendor stream）。
4. **块③**：合并 synthesis 进 retrieve、改 system prompt（含决策 a/d）、`chat_turn` 单流消费、保留结构化 needs_pick（决策 b）→ 回归 `tests/chatbot/application/`。
5. 端到端联调（UAT 工具禁用、超管多公司、needs_pick、打断 partial、chart 围栏）。

> 每步改完按项目规范「**改完不自动跑测试，回复末尾提醒待测试**」，由开发下令统一跑。
