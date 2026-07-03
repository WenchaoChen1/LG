# kernel 去 langchain 化：chat 传输层迁移 openai 原生 SDK（根治方案）

> 日期：2026-07-02　范围：`CIOaas-python/source/llm/infrastructure/kernel/`（分支 sprint113）
> 性质：根治「langchain 传输税」——三类问题（流式 cost 丢失 / usage 补帧 / token 双发）一次性从结构上消灭。
> 依据：5 维度并行代码调查（openai_compat 依赖清单 / anthropic_native 依赖清单 / 边界契约面 / 原生 SDK 可行性实测 / 回归面），关键前提均有 file:line 或 .venv 实测证据。

---

## 1. 问题根因（为什么是"税"）

kernel 传输层现在用 langchain 的 `ChatOpenAI` 当 HTTP 协议客户端（`openai_compat/chat.py`）。它不是纯客户端——是 langchain Runnable，自带三类结构性代价：

| 税 | 现象 | 根因证据 | 现有补丁（迁移后退役） |
|---|---|---|---|
| ① 流式 cost 丢失 | OpenRouter 带内实报的 `usage.cost` 在流式下拿不到，被迫异步补正 | langchain-openai `base.py:1349-1368`：流式 chunk 的 usage 只经 `_create_usage_metadata` 映射 token 字段，**原始 dict（含 cost）被丢弃**；非流式却存 `llm_output["token_usage"]`——不对称即税 | `kernel/openrouter_billing.py` + `_schedule_cost_backfill` 整链 |
| ② usage/finish_reason 不透传 | 流式末段要靠 accumulated_meta 多键兜底捞 | langchain 把 finish_reason 埋进 response_metadata、usage 埋进 usage_metadata，字段名跨版本漂移 | `usage_extract.py` 三处多版本字段兜底 |
| ③ token 双发 | 一次调用两个 langchain run 各报一遍 token，前端整段复读 | ChatOpenAI 是 Runnable：被调用即注册 run + async 下 contextvars 继承外层回调 | `callback_isolation.py`（69875ed）+ `_AnswerEchoFilter` 消费端过滤 |
| （附）构造反射 | 每次调用 try 最多 6 套构造参数变体 | langchain-openai 三代构造签名不兼容（`chat.py:102-134`） | `_chat_openai_attempts` 整层 |

**根治 = 传输层换 openai 原生 SDK（`AsyncOpenAI`）直驱**。原生 SDK 无 Runnable/run/回调概念（税③结构性消失）、响应模型 `extra="allow"` 保留一切扩展字段（税①消失）、finish_reason/usage 是一等公民（税②消失）、构造签名自 v1 稳定（反射消失）。

**先例**：embeddings 路径（`openai_compat/embeddings.py`）本来就是 AsyncOpenAI 原生实现，client 构造/超时/自管重试/信号量限流模式可整套照搬。

## 2. 关键前提实测（已验证，非假设）

1. **流式 cost 原生可得**（决定性）：真实 OpenRouter 流式调用实测，最后一个 chunk 的 `usage` 原样携带 `cost`/`cost_details`（SDK BaseModel `extra="allow"`，`openai/_models.py:118-119`）→ 流式 `cost_source='provider'` 当场落库，**异步补正整链可废**。
2. **工具流式拼装有官方 helper**：`ChatCompletionStreamState`（`openai.lib.streaming.chat` 公开导出）实测正确拼装并行双工具、分片 arguments；自写 first-wins 拼装器也仅 ~30 行。
3. **langchain-core 消息类是纯数据**：实测 `AIMessage` MRO 无 Runnable、无 invoke/astream——**保留为输入契约零行为风险**（`MessageLike` 本就 TYPE_CHECKING 弱依赖，`messages.py:15-17` 注释早已预留本次替换）。
4. **工具 schema 转换有纯函数**：`langchain_core.utils.function_calling.convert_to_openai_tool`（1.4.8 实测，接受 BaseTool/dict/callable）——不必自写 pydantic 展开。
5. **vision 消息零转换**：业务侧 content-block（`{'type':'image_url','image_url':{'url':dataURL}}`）已是 OpenAI wire 格式，只需拆 HumanMessage 壳。
6. **边界契约面干净**：langchain 对象只在 3 处渗出 kernel——`TextResult.raw`（源内唯一消费方 `DBRouterChatModel._to_ai_message`，已有非 AIMessage fallback，且 json_mode 截断路径的 raw **今天就已是** openai ChatCompletion，异构早成事实）、`MessageLike` 输入、`tools` 透传。TextChunk/TextUsage/measure/SSE/落库全部鸭子类型，零改动。

## 3. 目标 / 非目标

**目标**
- `openai_compat` chat/vision 路径改 AsyncOpenAI 直驱；三类税的补丁代码全部退役。
- 流式成本直接落 `cost_source='provider'`（OpenRouter），成本三层采集语义不变、来源更真。
- kernel 层首次建立字段级契约测试（现状：`ainvoke_compatible`/`stream_compatible`/`_final_chunk`/截断兜底**零直接测试**）。

**非目标（YAGNI，明确不做）**
- 不动 `MessageLike` 契约（langchain-core 消息类继续作输入类型；引入内部 Message dataclass 留到未来真要摘 langchain-core 时）。
- 不动 `DBRouterChatModel`/`create_agent` 桥（编排层继续走 langchain，这是用户设计目标本身）。
- 不动 capabilities 契约（TextRequest/TextResult/TextChunk/TextUsage）、router/measure、vendors 薄叶子、上游业务——改动面**严格收敛在 kernel 协议层**（与「仅 kernel 可碰 SDK」的分层铁律吻合）。
- anthropic_native 不在第一批（见 Phase 2 决策）。

## 4. 分阶段方案

### Phase 0：迁移前守护（先补黄金测试，再动刀）

现状最大风险不是迁移本身，而是**旧实现没有字段级回归锁**（生产上量最大的 async 路径 kernel 层零测试）。先做：

1. 手写一组 **wire fixtures**（非流式 JSON：含 usage.cost / 无 cost / 免费模型 cost=0 / finish_reason=length / tool_calls；流式 SSE：多 delta + tool_call 增量帧 + 末段 usage chunk）。
2. 经 `httpx.MockTransport` 喂**旧实现**（ChatOpenAI 已支持注入 http client，`chat.py:92-94,176-177`），断言 TextResult/TextChunk 全字段——固化旧行为为黄金基线。
3. kernel 级 5 条不变量（从 `test_chat_model.py:215-245`、`test_llm_router.py:219-323` 反推）写成参数化契约测试：
   - 逐帧 delta 拼接 = 全文；
   - 恰好一条 `is_final=True` 末段帧；
   - 末段帧携带 usage（五 token 字段 + cost）/ finish_reason / 完整 tool_calls；
   - 无元数据时 usage 为空 `TextUsage()` 而非 None；
   - 异常原样上抛不吞。

### Phase 1：openai_compat 迁 AsyncOpenAI（本体）

**改写 `kernel/openai_compat/chat.py`：**

| 现在（langchain） | 迁移后（原生 SDK） |
|---|---|
| 每次调用 `build_chat_openai`（6 变体反射）新建 ChatOpenAI | 按 `(base_url, api_key, headers)` 进程级缓存 AsyncOpenAI 单例（对齐 embeddings 先例），`http_client=_SHARED_HTTP_ASYNC_CLIENT` 注入共享池 |
| 消息由 langchain 隐式转 wire | `convert_to_openai_messages`（langchain-core 纯函数）或自写归一化：System/Human(str+blocks)/AI(tool_calls 回放→`function.arguments=json.dumps`)/Tool(tool_call_id)；dict 直通；vision 块直通 |
| `chat.bind_tools(req.tools, tool_choice)` | `create(tools=[convert_to_openai_tool(t) ...], tool_choice=归一化)`（str 工具名→dict、'any'→'required'） |
| `model_kwargs.response_format` 绕行 | `create(response_format={"type":"json_object"})` 直传 |
| `LengthFinishReasonError` 捕获 + `_result_from_truncated` | raw create 不抛该异常——直接读 `choices[0].finish_reason=='length'`，兜底逻辑简化（语义保留：截断不崩整轮） |
| 流式 `acc_msg + chunk`（AIMessageChunk.__add__） | `ChatCompletionStreamState.handle_chunk`（官方 helper）或 ~30 行 first-wins 拼装器；`stream_options={"include_usage": True}` |
| `config=ISOLATED_CALLBACKS_CONFIG` 4 处 | 不需要——原生 SDK 无回调树 |
| `raw=AIMessage` | `raw=ChatCompletion`（契约本就 `Any`；截断路径今天已如此） |
| timeout/max_retries 烘焙进构造 | `client.with_options(timeout=, max_retries=)` per-request |
| `request_extra_body`（OpenRouter usage.include） | `create(extra_body=...)` 一等支持，机制保留、载体换掉 |

**改写 `usage_extract.py`**：多版本字段兜底 → 单一 `CompletionUsage` 直读；cost 从 `usage.model_extra['cost']` 取；`provider_response_id` = `completion.id` / 流式首帧 `chunk.id`（实测同为 `gen-…`，语义不变）。**流式与非流式统一 `cost_source='provider'`（OpenRouter）**。

**强化桥接层 `langchain/chat_model.py` `_to_ai_message`**：raw 不再是 AIMessage 时全量重建——补 `id`（取 `TextUsage.provider_response_id`）、`usage_metadata`（取 TextUsage token 字段）、`response_metadata`（finish_reason/model）。数据源 100% 已在 TextResult/TextUsage 字段中，**不需要给契约加新字段**；`isinstance(raw, AIMessage)` 快路径保留（Phase 1 期间 anthropic_native 仍产 AIMessage raw）。

**显式行为变更点（须在提交信息与代码注释标注）**：`extra_kwargs` 语义从「ChatOpenAI 构造参数」变为「`create()` 调用参数（wire 语义）」。全仓 grep 已确认无业务方传 ChatOpenAI 专属键，风险为零，但属契约变更。

**退役清单（Phase 1 内删除）**：
- `_chat_openai_attempts` + `build_chat_openai` 反射层；
- `kernel/openrouter_billing.py` + `llm_router_db_service._schedule_cost_backfill/_backfill_openrouter_cost/_COST_BACKFILL_TASKS`（gate 三条件之一 `cost_source != 'provider'` 在原生 SDK 下对 OpenRouter 恒不成立——补正机制失去存在理由；黄金测试断言流式 `cost_source='provider'` 锁住）；
- `callback_isolation.py` 在 openai_compat 的 4 处引用（文件本体保留给 anthropic，Phase 2 后整体删）；
- `tests/llm/test_kernel_callback_isolation.py`（机制随 ChatOpenAI 退役；其中「内容透传 + 末段 is_final」断言语义并入 Phase 0 黄金测试）。

**必红测试改写清单**（调查已定位，均为形状迁移非语义变更）：
- `test_openrouter_cost.py:61-77`（build_chat_openai extra_body 断言 → 新请求组装函数断言）；
- `test_cost_layered.py:67-92` + `test_openrouter_cost.py:85-103`（extract 输入从 langchain 形状 → `CompletionUsage` 形状，金额断言不变）;
- `test_chat_model.py:43-47`、`tests/ai/text2sql/test_text2sql_agent.py:19-21`（raw=AIMessage 假设 → `_to_ai_message` 等价产出口径）。

**安全网（零改动、必须全绿）**：`test_llm_router.py`（564 行全链路）、`test_chat_model.py` 其余、`tests/ai` 全部图/agent 测试（真实 create_agent + mock router）、`tests/chatbot` SSE/编排——它们全在 TextResult/TextChunk 口径，恰好锁死三类税的下游契约。

### Phase 2：anthropic_native——**建议保持现状（暂不迁）**

调查结论：该协议族是 **dormant path**——全仓业务代码零调用方（默认 provider=openrouter，vision 硬锁 openrouter+Opus，`.env_example` 连 ANTHROPIC_API_KEY 都没有），仅 2 个 mock 测试触达。税①对它不适用（Anthropic 本就不返 cost），税③已被 callback_isolation 打上。

- **决策：不迁**（YAGNI）。`callback_isolation.py` 保留仅供 anthropic 使用，文件 docstring 更新说明"仅剩 anthropic_native 使用"。
- **触发条件**：anthropic 直连要上生产流量时再迁原生 AsyncAnthropic（届时需自建消息转换 system 抽离/content blocks/tool_result、OpenAI schema→input_schema 映射、流式事件聚合——`client.messages.stream()` 的 `get_final_message()` 反而比现在的手工 meta 累积更简单；anthropic SDK 0.104.1 已在依赖树、lint 豁免已覆盖）。

### Phase 3：真实环境验收 + 补丁清算

1. **真实环境验收**（合并现有 3-1 待验收项）：重启服务 → `/devSupport/chat` 聊数轮（含取数问题、含长答案）→ 确认 ①文字不复读 ②工具卡片正常 ③速度正常 ④`ai_llm_call_log` 流式记录 `cost_source='provider'` 且 cost 与 OpenRouter 后台一致 ⑤vision 提取跑一单。
2. 验收通过后删 `_AnswerEchoFilter`（`retrieval_agent.py`/`retrieval_sql_agent.py` + `test_answer_echo_filter.py`）——迁移后单 run 恒放行，过滤器成死重。⚠️ 该文件有并发会话在改（v2 tools），删除前先看当时分支状态、窄暂存。
3. 依赖清理：`langchain-openai` 从 pyproject 移除（迁移后全仓无引用；`langchain`/`langchain-core`/`langchain-anthropic` 保留——编排桥与 anthropic 仍用）。
4. 文档同步：`source/llm/CLAUDE.md`「成本三层采集」改为两层（provider 带内实报含流式 / estimated 估算兜底，异步补正段删除）；「LangChain 集成」段补注 kernel 传输层已原生化；`pyproject.toml` TID251 黑名单中 `langchain_openai` 项保留（业务侧仍禁直连）。

## 5. 与在途工作的关系

- **69875ed（callback 隔离修复）尚未推送**：本迁移建立在其上、并最终取代它的 openai 侧机制——不冲突，迁移 Phase 1 时其 openai_compat 部分自然被删除；anthropic 侧保留。原定的 3-1 真实环境验收**并入 Phase 3 验收**（同一批验证动作）。
- 上一轮记档的「第 3 次惹事再立项」触发条件：用户本轮明确要求根源解决，**视为已触发**，本方案即立项产物。

## 6. 风险与对策

| 风险 | 等级 | 对策 |
|---|---|---|
| kernel 旧路径零测试，迁移无对照 | 高 | Phase 0 黄金测试先行，同一 fixture 新旧对拍，字段级一致才切 |
| 非标上游（OpenRouter 转发的各家模型）流式帧不规范（如每帧重发 id） | 中 | 拼装器用 first-wins 策略；fixtures 收入 tool_call 分片/免费模型 cost=0/length 截断样本 |
| `ChatCompletionStreamState` 在 length+response_format 时抛 LengthFinishReasonError | 中 | 二选一决策点：用官方 helper 则保留 try 捕获；自写 30 行拼装器则完全掌控（**推荐自写**，消灭最后一个隐式异常源） |
| raw 类型变更影响未知消费方 | 低 | 全仓 grep 已确认源内唯一消费方 + 已有 fallback；契约注释 raw 本就是 Any"调试用，不入库" |
| extra_kwargs 语义变更 | 低 | 无存量调用方；提交信息 + 契约 docstring 显式标注 |
| 成本补正删除后 OpenRouter 偶发末帧无 usage | 低 | `usage.include=true` 是 OpenRouter 文档化行为；黄金测试覆盖"无 usage 帧→空 TextUsage + cost 走 estimated"的降级路径（估算兜底本就保留） |
| 并发会话同改 retrieval_agent.py | 中 | Phase 3 删补丁前先 `git status`/看分支，窄暂存提交 |

## 7. 工作量与批次

- **Phase 0**：fixtures + 黄金测试 ~300-400 行（半天）
- **Phase 1**：chat.py 重写（含消息/工具转换器 + 流拼装）~400-500 行 + usage_extract 改写 + 桥接强化 + 必红测试改写（1 天）
- **Phase 3**：真实环境验收（用户参与）+ 清算删除（半小时）

单批次可完成（Phase 0→1 连续执行，Phase 3 等真实环境）。测试按项目规则：改完不自动跑，收到"跑测试"指令统一跑。

## 8. 完成后的世界（验收定义）

- `kernel/openai_compat/` 内无任何 langchain ChatModel import（langchain-core 纯函数工具除外）；
- `ai_llm_call_log` 流式 OpenRouter 记录 `cost_source='provider'`，无 estimated→provider 两段式补写；
- `callback_isolation.py` 仅 anthropic 引用、`openrouter_billing.py` 不存在、`_AnswerEchoFilter` 不存在；
- 全仓测试 0 failed；真实环境聊天/取数/vision 三路验收通过。
