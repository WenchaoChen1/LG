> 关联文档: [AI-Chatbot 设计](../../AI-Chatbot/设计/design-doc.md) · [数据查询设计](../../AI-Chatbot-数据查询/设计/design-doc.md) · [GS知识库 Layer2 需求](../../AI-Chatbot/需求文档-GS知识库-Layer2摄取与管理.md)

# AI Chatbot 知识库文档问答 — 方案设计（V1）

> 状态: 已选型（2026-07-05）——方案 A + 三模式扩展（默认 standard / 纯知识库 kb / 组合 combo，§3.8）；实现计划见 [../plans/2026-07-05-chatbot-knowledge-base-qa.md](../plans/2026-07-05-chatbot-knowledge-base-qa.md)。本稿已经三视角对抗审查（事实 / 可行性 / 完整性）修订。

**日期**: 2026-07-05
**范围**: CIOaas-python（tool 轨新增 1 个工具 + 新增 kb/combo 两条取数轨 + rag `recall` 小幅增强 + 提示词）+ CIOaas-web（聊天页 `+` 工具菜单加斜杠命令静态提示，小改；无模式选择器）；Java **零改动**
**一句话**: 给 chatbot 的 ReAct 取数 agent 新增 `search_knowledge_base` 工具（进程内直调 RAG `search_service.recall`，space 范围按用户 token 身份自动圈定，V1 占位 = 全部可见空间），并提供三种可选智能体模式：默认（业务+知识库兜底）/ 纯知识库 / 组合（知识库必查+业务）。

---

## 0. 背景与目标

Chatbot 目前能答四类业务数据问题（公司/财务/benchmark/normalization，均经 Java 网关取数），但**不能基于知识库文档回答**。RAG 模块（`source/rag/`）已具备完整的空间管理、文件入库向量化、混合召回能力，且与 chatbot 同进程——本方案解决"把两者接起来"的方式选型与落地设计。

**目标**：
1. 用户在聊天中问到知识库文档相关内容时，chatbot 能检索可见空间的文档片段并据此作答；
2. space 权限自动跟随用户身份（token → 可见 space），**V1 占位：默认检索全部可见空间**，不做空间选择 UI；
3. 保持召回记录能力不丢（检索日志 + space/entry/chunk 三级 hit_count 照常累加），且不阻塞其他在跑的 SSE 流。

**非目标（V1）**：知识库空间选择器 UI、检索结果 rerank、STRUCTURED 财报文档召回、跨存储后端分组召回（登记为已知限制，见 §3.4/§7）、Java/前端任何改动。

## 1. 现状事实（探查 + 对抗审查双重核实，全部有代码依据）

### 1.1 chatbot 图与工具接线

- 图拓扑：`START → input_guard →(ok) init →[financial_mode: tool|sql] retrieve_tool / retrieve_sql → END`（`ai/agent/chatbot_graph/build.py:68-84`）。没有独立闲聊分支——一切未拦截问题都进取数轨，成文者就是轨内 ReAct agent 自己。
- tool 轨 `retrieve_tool_node`（`nodes/retrieval_agent.py:97-177`）绑 `TOOL_REGISTRY_V2` 全量（6 个原生 `@tool` 对象，`chatbot_graph/tools.py:28-35`），`_MAX_ITERS=6`。**新增工具只动注册表这一处代码接线**：retrieval_agent 自动拾取、`_StepCardMiddleware` 自动出步骤卡片、`_tools_for_end` 自动按端过滤。
- 提示词不描述具体工具（`prompts/chatbot/retrieval_agent_prompt.py:3-5`，docstring 即 LLM schema、单一事实源）——**工具描述层面零提示词改动**。但注意：该提示词的「职责与应答边界」①把核心能力枚举为"财务 / benchmark / Normalization Tracing / 公司信息"（`retrieval_agent_prompt.py:21`），**不含知识库**，且条款④允许"回答不了时用通用业务知识作答"——对知识库问题这是把 LLM 推离检索的反向信号，须补一行职责枚举（见 §3.6），否则"保证能使用"可能被静默打穿。
- 工具内抛异常**不会炸整轮**：create_agent 的 ToolNode 把异常转为错误 ToolMessage 回喂模型、ReAct 继续（`retrieval_agent.py:235-237` 注释实证），代价是 LLM 看到原始错误文本、步骤卡片报 error——所以工具内仍应自己 catch 并返回结构化降级结果。
- 身份链路：SSE 入口把 `auth_token / user_id / end_type / active_company_id` 等写进图 state（`sse_provider.py:235-238`）→ 节点投影为 `ReqCtx` dataclass → `create_agent(context_schema=_ReqCtx)` + `astream(context=ctx)` 注入 → 工具经 keyword-only 参数 `runtime: ToolRuntime[ReqCtx]` 读取（对 LLM 不可见、绝不进 schema）。`ReqCtx` 字段含 `auth_token / user_id / home_company_id / end_type / allowed / accessible / current_user`（`ai/tools/_support/request_context.py:16-32`）。

### 1.2 RAG 召回能力与进程内调用

`SearchService.recall`（`rag/application/service/search_service.py:165-219`，keyword-only）：

```python
async def recall(*, mode: str, query: str, top_k: Optional[int], company_id: str, user_id: str,
                 background: BackgroundTasks, space_ids: Optional[list[str]] = None,
                 file_id: Optional[str] = None) -> SearchResultDTO
```

- **接入路径的规范冲突（须明示）**：`rag/CLAUDE.md:7` 写的预期集成方式是 **HTTP `/search` + `x-caller-type: CHATBOT`**，且该标识通道 HTTP 层已实现（`routes.py:460-481`；`search_log` 列注释早已预期 `USER | CHATBOT` 值）。但 `standards/architecture.md` §2.1 规定 Python 域间**首选进程内调用对方 `application/service`**；且 `/search` 不带"按 process_type 自动圈定可见空间"的逻辑（那是 recall 的封装价值），走 HTTP 还要同进程绕一圈网络 + 二次解析 token。本方案选进程内直调 recall（详见 §2 方案 D 的评估），**并把 `rag/CLAUDE.md` 模块定位同步更新**（列入 §6）。
- 进程内直调可行：service 自管 session（`with get_session()`），不依赖 FastAPI Request/中间件，`company_id/user_id` 是纯参数；单例入口 `get_search_service()`（:540-544）。跨模块 import `rag.application.service` + `dto` 合规。**当前代码库尚无任何 chatbot→rag 调用——本方案是第一次接线。**
- `space_ids=None` 缺省语义 = **该 process_type 下用户全部可见空间**（:208）；显式给出则与可见集求交（:204-206）。
- 返回 `SearchResultDTO.hits`：`chunk_id / entry_id / entry_title / space_id / space_name / content / similarity([0,1]) / match_type(SEMANTIC|KEYWORD|BOTH)`。
- trace：service 内 `current_trace_id()` 有则复用——chatbot 轮内调用自动挂到 `chatbot.chat` 链路，`search_log.trace_id` 同值（:110-129）。检索内的 query embedding 走 `llm_db_router.aembed`，会以 **agent=`rag` / node=`query`** 落 `ai_llm_call_log`（`CallerNode.QUERY` / `CallerAgent.RAG` 均已存在，无需新增枚举）——即 chatbot 轮的 KB 检索成本在 By-Agent 聚合里记在 rag 名下、靠 trace_id 归并到本轮，这是预期行为，验收时勿误判。

**进程内调用的四个坑（必须适配，方案见 §3.3）**：

| # | 坑 | 事实依据 |
|---|----|---------|
| 1 | **事件循环阻塞**：recall/search 的 service 层在调用方事件循环上直接执行同步 SQLAlchemy 查询——圈定可见空间（:200-203）、`_resolve_visibility` 对 N 个 granted space 串行逐个 `get_by_id`（:257-272）、`_store_for_granted`（:338-341）、`_enrich` 两次元数据查询（:358-360），合计 **4+N 次同步 DB 往返**（业务库是远程 RDS）。processor/storage 层是真异步（`aembed`、pg_store 全 `asyncio.to_thread`），但 service 层这些阻塞点会卡住**所有并发 SSE 流的 token 泵**，违反 chatbot 域强约定（`chatbot/CLAUDE.md:68`）。该问题对既有 HTTP `/recall` `/search` async 路由同样存在（先天欠账） | `db/session.py:77-83`（同步 Session）；`ai/tools/_support/sql_exec_tool.py:80-82`（既有工具的 to_thread 先例） |
| 2 | `background` 参数只被调用 `.add_task()`（processor 侧形参本就是 `Any`，`base.py:300`）；脱离 HTTP 响应的裸 `BackgroundTasks()` **永不执行**，召回日志 + 三级 hit_count 会静默丢失 | `processor/base.py:329`；Starlette 语义 |
| 3 | recall 把检索日志 `caller_type` 写死 `"USER"`（:215）——CHATBOT 标识通道只在 HTTP `/search` 层有，recall 缺透传 | `search_service.py:215`、`routes.py:479-481` |
| 4 | **RagBusinessError 无干净分流判据**："无可召回空间"抛 `invalid_param`（400/40001，:209-210），但同一 code 40001 还被"跨后端检索"校验复用（:274-279）；存储层故障转 `service_unavailable`（503/50301，:147-149）、竞态 granted 清空是 401/40101（:93-98）——**全是 RagBusinessError**。笼统 catch 会把"向量库宕机"误报成"你没有知识库" | `rag/application/service/errors.py` 工厂体系无专属 code |

### 1.3 space 权限：「通过用户 token 获取 space 权限」的现成方法

链路已存在、无需新开发：**token → Redis 会话 → 身份 → 可见空间**。

1. token → 身份：`get_current_user`（`common/auth/identity.py:34-60`）→ `auth_store.get_user`（`common/redis/auth_store.py:69-85`）→ `AuthUser(user_id, company_id, organization_id)`。SSE 入口已完成此步，图 state / ReqCtx 里现成可用。
2. 身份 → 可见 space：`SpaceRepository.list_visible_ids(*, company_id, user_id=None, process_type=None)`（`rag/domain/repository/space_repository.py:100-128`）——可见 = 同 company 且（`binding.user_id IS NULL` 公司共享 或 `==本人` 私有）且未删除。**recall 内部已调用它**（`search_service.py:201-203`），chatbot 侧不用也不应直接 import（domain 层跨模块 import 违反 rag 约定）。
3. 因此"默认给所有"占位 = 调 recall 时 `space_ids=None`，chatbot 侧零额外代码。

**超管与身份模拟**（管理端权限面，两条都要知晓）：

- 不用模拟时：管理端操作者 Redis `company_id` 为空 → `list_visible_ids(company_id=None)` 编译为 `binding.company_id IS NULL`，只圈到**无公司归属的空间**（如超管自建），不是全部公司的空间（`space_binding_model.py:36`，nullable）。与 RAG 管理页对同一身份的可见范围一致。
- 身份模拟时（admin-only，`sse_provider.py:174-212`）：`simulate_*` 替换 company 数据范围、`user_id` 保持操作者本人 → `home_company_id` 派生为被模拟公司（`init_node.py:79-80`）→ 本工具将圈到**被模拟公司的公司级共享空间**（被模拟用户的私有空间因 user_id 不换仍不可见），检索日志 `user_id` 记操作者。即**管理员经模拟可检索任意公司的共享知识库**——这是"数据范围随模拟走"语义的自然延伸，与财务数据模拟行为一致，但属安全/隐私敏感面，须产品确认接受（已列 §5 验证清单）。

## 2. 方案选型

| 方案 | 说明 | 优点 | 缺点 | 结论 |
|------|------|------|------|------|
| **A. 知识库检索 tool 挂现有 tool 轨** | 新增 `search_knowledge_base` @tool 进 `TOOL_REGISTRY_V2`，进程内直调 `recall`，LLM 自主决定何时检索、可多轮改写 query 重试 | 贴合现架构：**1 个代码接线点**（注册表）；tool 轨本身就是 ReAct agent → 天然获得 agentic RAG（检索不理想可改写再查）；**可与财务/benchmark 工具同轮混用**（"结合我们的政策文档看这季度费用"）；步骤卡片自动呈现；进程内直调无 HTTP 开销、trace 自动挂链路 | 检索是否发生依赖 LLM 判断——知识库是开放域，无法按业务面写死触发条件，须改用程序性触发规则（§3.7）；需适配 §1.2 四个坑（其中阻塞治理落在 rag 侧，§3.3）；成为 ai/CLAUDE.md"工具经 Java 网关"约定的第二个例外，须登记 | ✅ **推荐** |
| **B. 独立知识库取数轨 / 专属子 agent**（新 mode `kb` + `retrieve_kb` 节点） | 类比 sql 轨：路由到专属节点，强制先检索后成文，专属提示词 | 检索必然发生；可定制 KB 专属应答纪律（严格引用、仅基于文档作答） | 现有模式判定只有 `/sql` 字面标记（`init_node.py:84`），没有意图分类器——要么让用户敲 `/kb`（体验差），要么新增 LLM 意图分类（加延迟加复杂度还会误判）；**分轨后 KB 与业务数据工具无法同轮混用**（真实问题常是混合的）；改动面 5 处（build/state/init/新节点/新提示词）vs A 的 1 处；四个坑一个不少照样要适配。违反 YAGNI | ❌ 排除（若未来 KB 问答需要"仅基于文档作答"强纪律模式，可在 A 之上追加，工具无需重写） |
| **C. 每轮强制检索注入上下文**（经典 RAG：init 后把 top-k chunks 拼进系统提示） | 新节点每轮拿 question 检索并注入 | 实现直观；KB 内容必然在场 | 闲聊/财务问题也无差别检索：白耗 embed+检索延迟、召回日志被噪声灌爆、hit_count 失真（违背"召回记录是真实使用记录"语义）；单发检索不能改写追问；每轮固定膨胀上下文挤占 token；阻塞坑还从"按需"变"每轮必现" | ❌ 排除 |
| **D. A 的变体：工具内走 HTTP `POST /api/ai/rag/search`（rag/CLAUDE.md 原定路径，x-caller-type=CHATBOT 通道已实现）** | 同 A 但经自身 HTTP 接口调用 | 契约与外部调用方统一；CHATBOT 标识现成；rag/CLAUDE.md 不用改 | 同进程绕一圈 HTTP + 重复解析一遍 token；`/search` **没有"按 process_type 圈定全部可见空间"逻辑**（那在 recall 里），chatbot 还得先查空间列表再传 spaceIds，多一次往返；`standards/architecture.md` §2.1 明定域间首选进程内 service 调用（规范层级高于模块 CLAUDE.md 的描述句）；阻塞坑同样存在（HTTP 路由也是 async 直调同步 service） | ❌ 排除（rag 拆独立服务时再切换，届时工具面不变、换客户端即可） |

> "agent 还是 tool"的实质：现架构里 tool 轨**本身就是一个 ReAct agent**，方案 A 等于"agentic RAG 挂进现有 agent"——B（独立 agent/轨）的增量收益只剩"强制检索 + 专属提示词"，代价是丢掉混合问答与 5 倍改动面。选 A。
>
> **更新（2026-07-05，需求追加）**：方案 B 的"❌ 排除"仅针对**自动路由**形态。纯知识库轨以「用户显式选择模式」形态进入范围（§3.8）——显式选择消除了 B 的最大阻塞点（无意图分类器可用），强纪律提示词（必检索、仅基于文档作答）的收益得以保留。

## 3. 推荐方案 A 详设

### 3.1 工具接口（LLM 可见面）

新文件 `source/ai/tools/knowledge_base_tool.py`（一个 @tool 一个文件、@tool 置顶、**禁写 `from __future__ import annotations`**）：

```python
@tool("search_knowledge_base", parse_docstring=True)
async def search_knowledge_base_tool(
    query: str,
    top_k: Optional[int] = None,
    *,
    runtime: ToolRuntime[ReqCtx],
) -> str
```

- `query`：检索词，由 LLM 按用户问题生成/改写（docstring 指导：用陈述式关键词而非原句照抄；结果不相关可换措辞重试一次）。
- `top_k`：可选，缺省 5；recall 内部钳制 [1,20]。
- **space 范围不进 LLM schema**——权限边界一律走 ReqCtx，与公司范围同原则。
- docstring 写明：何时用（用户问公司制度/流程/文档/知识库内容，或点名"根据知识库/文档"）；何时不用（财务数字/benchmark 走对应工具）；返回怎么读（`hits[].content` 为文档片段、作答时引用 `source_title` 标注出处；`content` 为 `[仅文件名可检索，正文未入库]` 占位时只能确认文件存在）；`hits` 为空 + `note` 时如何向用户解释。

### 3.2 运行期上下文与权限

工具体内从 `runtime.context` 取身份，直接映射 recall 参数：

| recall 参数 | 取值 | 说明 |
|------------|------|------|
| `company_id` | `ctx.home_company_id`（公司端=本公司；管理端=None；**身份模拟时=被模拟公司**，见 §1.3） | 与 Redis 身份、RAG 管理页可见范围一致——用户在聊天里能查到的 = 他在知识库页面能看到的 |
| `user_id` | `ctx.user_id`（模拟时仍为操作者本人） | 参与"公司共享 or 本人私有"过滤 |
| `space_ids` | **V1 恒 `None`（占位）** | = 全部可见空间；未来空间选择器落地时经 payload → state → ReqCtx 透传，recall 显式交集逻辑现成，工具面不变 |
| `top_k` | LLM 传入或 None | recall 钳制 |

### 3.3 进程内调用 recall 的四个适配（对应 §1.2 坑表）

1. **事件循环阻塞治理（坑 1，推荐随本方案一并做）**：在 rag `search_service` 内把 service 层 4 处同步查询用 `asyncio.to_thread` 包装（圈定可见空间 :200-203、`_resolve_visibility` :257-272、`_store_for_granted` :338-341、`_enrich` :358-360），对齐仓库既定习惯（`chatbot/CLAUDE.md:68`、`sql_exec_tool.py:80-82` 先例）。收益不止 chatbot：既有 HTTP `/recall` `/search` async 路由的同款阻塞（先天欠账）一并治好。`_resolve_visibility` 的 N 次串行 `get_by_id` 合并为单次 in 查询留作后续优化，不在本方案。
   **备选（若坚持 rag 零结构改动）**：V1 接受阻塞并量化登记——4+N 次远程 RDS 往返 ≈ 数百 ms/次调用，期间所有并发 SSE 流 token 泵停顿；仅在确认近期并发极低时可选，且须在文档留 TODO。**不推荐**。
2. **副作用不丢（坑 2）**：工具内自带极简 runner 代替 `BackgroundTasks`——

   ```python
   class _AsyncBackground:  # recall 的 background 形参是鸭子类型（processor 侧注解本就是 Any），只调 .add_task
       def add_task(self, fn, *args, **kwargs):
           asyncio.get_running_loop().run_in_executor(None, functools.partial(fn, *args, **kwargs))
   ```

   `SearchSideEffect.run` 是同步写库函数（自管 session、异常自吞，`search_service.py:461-486`），丢线程池执行不阻塞事件循环；检索日志与三级 hit_count 照常累加。**选型说明**：不用 `tracing/infrastructure/async_writer.py` 的 `create_task + to_thread + 全局持引`模式，因 `run_in_executor` 的 work item 由 executor 持有、天然免 GC 丢任务问题，且此处无需回压/批量语义。
3. **来源标识（坑 3）**：`recall` 加向后兼容可选参 `caller_type: str = "USER"`（:215 处透传进 SearchDTO），工具传 `"CHATBOT"`——与 HTTP `/search` 的 `x-caller-type` 通道同值域（`search_log` 列注释本就预期 `USER | CHATBOT`），管理页统计不混淆。
4. **错误分流（坑 4）**：不能笼统 catch RagBusinessError（会把向量库宕机误报成"你没有知识库"）。方案：`recall` 再加一个可选参 **`empty_scope_ok: bool = False`**——为 True 时"圈定可见空间为空"不再抛 `invalid_param`，直接返回空 `SearchResultDTO`（在 :209-210 处短路，语义上"没有空间"对 chatbot 本就不是错误）。工具侧于是形成干净二分：
   - 正常返回且 `hits=[]`、granted 为空 → `ok=true, hits=[], note="当前无可用知识库空间"`（LLM 正常告知用户）；
   - 任何 RagBusinessError / 其他异常（含 503 存储故障、40001 跨后端、40101）→ `ok=false, message="knowledge base is temporarily unavailable"`（参照 `financials_tool.py:113-115` 降级模式；ToolNode 本身不会让异常炸整轮，catch 的收益是结构化降级语义 + 步骤卡片不报 error）。

   随手项：recall 的注解按真实用法修正（`company_id: Optional[str]`、`background: Any`）——HTTP 路由本就传可空 `ctx.company_id`（`routes.py:931-936`），现注解与运行期事实不符。

### 3.4 process_type 决策：V1 只召回 STANDARD

单次 recall 只能覆盖一种 process_type（mode 一一对应、跨 business_type/embedding/后端均被 `_resolve_visibility` 硬拒）。V1 **只查 `mode="standard"`（enterprise_kb 通用文档空间）**，理由：

- 用户需求是"基于知识库**文档**"问答，即通用文档空间；
- STRUCTURED 是财报结构化分块，而 chatbot 财务问题的权威源已定为 `financial_normalization`（`financial_tool`）——同轮出现"财报文档片段"与"标准化指标"两个口径会打架，违反 tool 轨提示词的真实性/权威源纪律。

**已知限制（跨存储后端）**：space 创建时 `storage_backend` 可选 pg/es，`list_visible_ids` 不按后端过滤——若某公司同时存在 pg 与 es 的 STANDARD 空间，`space_ids=None` 全量圈定会命中"跨后端检索"硬拒（40001），本工具将持续 `ok=false`。当前部署 ES 是默认关闭的可选服务（RAG 默认全走 PG），实际风险低；V1 登记为已知限制 + 验证用例，按后端分组多路召回列为演进项（§7）。

演进：若"财报原文档问答"成为真实需求，工具内改为 `asyncio.gather` 双路 recall（各自降级、按 `similarity` 合并重排取 top_k）即可，LLM 面与注册面均不变。

### 3.5 返回契约

新文件 `source/ai/tools/dto/knowledge_result.py`（pydantic，每字段中文 description，**全 snake_case 无 alias**——对齐 `dto/company_result.py:5` 约定，`tool_result` 的 `by_alias=True` 对无 alias 模型是空操作，LLM 看到的键就是 snake_case；不加入 `dto/__init__.py` 导出，跟随最近先例直接 from 导入）：

```
KnowledgeSearchResult
├─ ok: bool                  # 成败
├─ message: Optional[str]    # 失败原因（ok=false 时）
├─ note: Optional[str]       # 无空间/无命中等非错误提示
└─ hits: list[KnowledgeHit]
   ├─ content: str           # 文档片段正文
   ├─ similarity: float      # [0,1] 相似度
   ├─ match_type: str        # SEMANTIC | KEYWORD | BOTH
   ├─ source_title: str      # 来源文件标题（entry_title，作答引用出处）
   └─ space_name: str        # 所属知识库空间名
```

统一 `return tool_result(...)` 序列化；**实现注意**：`exclude_unset` 语义下"ok=true 空命中"路径必须显式构造 `hits=[]`（否则键整个消失，LLM 无法区分"空列表"与"无此字段"）；失败路径沿用既有工具"不带 hits 键"形状。结果全量作 ToolMessage 回喂模型（既有决策：只给摘要会答"暂无数据"）。

### 3.6 注册、提示词与呈现

- 定义后赋值 `metadata = {"ui_label": ("Searching knowledge base", "Searched knowledge base"), "result_model": KnowledgeSearchResult}`；不设 `end_types`（两端可用）。
- `chatbot_graph/tools.py`：import + 追加 `TOOL_REGISTRY_V2`（数据工具区段）+ `__all__` + **模块头注释工具清单 6→7 同步改写**（:9 逐一点名）。
- **提示词改 2 处（工具描述仍零改动）**：`retrieval_agent_prompt.py` ①职责边界的核心能力枚举补"知识库文档问答"；②条款④"回答不了公司相关问题时用通用业务知识补充"改写为"**先检索知识库，无结果再用通用知识补充并说明**"。两处都是能力边界/编排纪律声明（符合"提示词不描述具体工具"原则）；不改则条款④会把 KB 问题导向通用知识作答，工具静默闲置。触发策略的完整论证见 §3.7。
- 前端步骤卡片、结果收集（`tool_results`/`attribution`）、端过滤全部自动生效。

### 3.7 触发策略：何时调用（开放域知识库的固有难题）

知识库与财务/benchmark 工具有本质区别：**它是开放域**——空间里装的是用户上传的任意文档，"答案在不在库里"在检索之前不可知，因此无法像其他工具那样从业务面写死"什么问题调用"。理论上任何公司相关问题都可能命中库内文档。对策分三档：

| 档 | 策略 | 取舍 | 结论 |
|---|------|------|------|
| 1 | **程序性触发规则**：不按"内容像不像知识库问题"判断，按**过程规则**——凡公司/组织相关、且结构化数据工具覆盖不了（或只有定量没有定性）的问题，**先查知识库、无结果再用通用知识并说明**；用户点名"知识库/文档/上传的资料"必查 | LLM 无需预知库里有什么；闲聊、纯计算、纯财务数字问题天然豁免；公司定性问题"宁可多调"——一次多余检索 ≈ 一次 embed + PG 混合查询，数百 ms 级，且发生在 ReAct 轮内不加首 token 延迟 | ✅ **V1 采用**（落在 docstring"何时用"段 + 条款④改写，§3.6） |
| 2 | **知识库目录注入**：init 时拉该用户可见空间的名称 + 文件标题（+`entry.summary` 摘要，入库时已自动生成），注入系统提示词，让 LLM"知道库里有什么"再决定 | 判断有据、误调最少，还能回答"我有哪些知识库可用"；代价：每轮 token 占用 + 一次额外查询（可缓存）、文件名/摘要是用户内容（新增提示注入面）、目录随库变大需截断策略 | 🔜 **V2 演进位**：若 §5-4 触发率验证不达标，以此根治 |
| 3 | **每轮强制预检索**（=方案 C 复活） | 真"每次都调"：闲聊也付一次 embed+检索延迟且加在首答之前；检索日志/hit_count 成噪声；预检索只有一次机会、query 只能用原句（不能像 agent 那样按上下文改写、不命中再换措辞重试），命中质量反而更差 | ❌ 仍排除 |

**失败模式不对称，是档 1 站得住的根本原因**：漏调可自救——用户一句"查一下知识库"即必触发（docstring 写明点名必查），且 §5-4 触发率专项验证兜底、不达标升档 2；多调只浪费一次数百 ms 的检索。反过来档 3 的成本每轮必付、永不可退。用户还可直接切换纯知识库/组合模式（§3.8）获得"必检索"保证。

### 3.8 三智能体：默认 / 纯知识库 / 组合（2026-07-05 需求追加，三个独立 build）

**三个独立智能体 = 三张图、三个 build 函数**，用户在聊天页显式选择（不选 = 默认）。kb / combo 是**用户显式选择**而非自动路由——这正是 §2 方案 B 阻塞点（无意图分类器）的消除方式：

| 智能体 | payload 值 | 图（build 函数） | 行为 |
|--------|-----------|-----------------|------|
| 默认（方案 A 本体） | `standard`（缺省） | `build_chat_graph()`——现有图**不动**（含 /sql 轨），只是 `TOOL_REGISTRY_V2` 多了 KB 工具 | 业务工具 + KB 工具，业务优先、KB 程序性兜底触发（§3.7 档 1） |
| 纯知识库 | `kb` | `build_kb_graph()`（新）：`guardrail → init → retrieve_kb → END` | 只绑 `search_knowledge_base`：**必检索**（先检索再作答、不命中可改写重查）、**仅基于召回内容作答**、无结果明说"知识库未找到"（不用通用知识兜底）、引用 `source_title` |
| 组合 | `combo` | `build_combo_graph()`（新）：`guardrail → init → dispatch →[场景] retrieve_kb / retrieve_tool / 两者顺序执行 → END` | **把上面两个智能体的核心（retrieve 节点）作为子智能体编排**：`dispatch` 节点（轻量 LLM）按问题做场景分析（`business` / `kb` / `both`）；`both` 时顺序跑两个子智能体，答案**分两个场景小节**流式输出（知识库视角 + 业务数据视角，段落头区分） |

机制与约定：

- **三张图共用同一套基建**：guardrail / init 节点、`ChatState`、`_StepCardMiddleware`、SSE 帧协议、KB 工具实现与 §3.3 全部适配。**落位（2026-07-06 用户指正修正——三智能体三子包，各占 `agent/` 下自己的子包）**：standard=`agent/chatbot_graph/`（主图 + 共享基建 `chatbot_graph/nodes/`、`ChatState`、装配原语 `_traced_node`/`_route_after_guard` 均在此单点定义）；**kb=`agent/chatbot_kb_graph/`**（纯知识库智能体，含 build/nodes(`retrieval_kb_agent.py`)/tools，按 `source/ai/CLAUDE.md`「每个智能体一个子包」约定独立）；**combo=`agent/chatbot_combo_graph/`**（kb + business 的组合智能体，含 build/nodes/tools）。kb / combo 两子包跨包复用 chatbot_graph 的 guard/init 节点与装配原语，combo 另引用 chatbot_kb_graph 的 retrieve_kb_node。`main.py` lifespan 编译三张图，`sse_provider` 按 payload `agent_mode` 取对应图。
- **`financial_mode` / `/sql` 完全不动**：/sql 标记只在 standard 图内有意义，kb / combo 图没有 sql 轨；无需字段改名。
- **combo 的 both 场景顺序执行**（kb 先、business 后）：规避 LangGraph 并行分支的 `answer_delta` 帧交错与超步 barrier 问题；两个子智能体写 state 的 `tool_results` / `attribution` 需合并（reducer 或 combo 包装节点合并）；每段前由包装节点发段落头帧（英文小节标题）。
- **dispatch 失败降级**：场景分析异常 → 按 `both` 执行（宁全勿漏，代价可控）。
- **模式为轮级**：选图判定收口在后端 `stream_turn`——按问题文本的**斜杠命令 `/knowledge` `/combined`**（与既有 `/sql` 同款文本标记：per-turn、不剥字符，标记随消息文本落库，重试/fork 重发原文自然复现模式）。优先级 `/sql` ＞ `/knowledge` ＞ `/combined` ＞ payload `agent_mode` ＞ standard（`/sql` 走 standard 图、由图内 init 归一到 sql 轨照旧）。不落额外 DB、不改 schema。**命令字面与内部模式值的映射**：`/knowledge`→`kb`、`/combined`→`combo`（图 dict/子包/payload 枚举一律仍用 `kb`/`combo`，只有用户敲的命令字面是 `/knowledge` `/combined`）；命令字面收口 `sse_provider._MODE_MARKERS` 常量（便于改名）。`/knowledge` `/combined` 用**词边界正则**匹配（行首/空白开头、后随空白/行尾）防 URL 路径中段误触发；`/sql` 保持原裸子串语义不动。
- **前端**：无模式选择器——纯文本斜杠命令，聊天页 footer `+` 工具菜单加静态提示行（`/knowledge` / `/combined` 说明，发现性用途）提示用户可用命令；流式请求 payload **不再发** `agent_mode`（后端字段保留供 API 调用方，前端零该字段）。
- kb / combo 的"必检索"由各自系统提示词约束（不加代码级强制，首轮跳过检索属提示词缺陷，按 §5-4 方法修）。

## 4. space 范围占位与演进路线

| 阶段 | space 范围 | 实现 |
|------|-----------|------|
| **V1（本方案）** | 用户全部可见空间（token 身份自动圈定） | 工具内 `space_ids=None`，零额外代码 |
| V2（待需求） | 会话级/轮级指定空间 | 前端空间选择器 → SSE payload → 图 state → ReqCtx 加 `space_ids` 字段 → 工具透传；recall 显式交集逻辑现成 |
| 待决 1 | 管理端超管不模拟时只能召回"无公司归属"空间（§1.3）；若要"超管按当前所选公司查该公司知识库"，需把 `active_company_id` 加进 ReqCtx（`retrieval_agent.py:104-113` 组装处同步）并以之作 `company_id` | V1 不做，保持与 RAG 管理页一致的最小惊讶原则；是否放开属产品决策 |
| 待决 2 | **身份模拟下管理员可检索被模拟公司的共享知识库**（不含他人私有空间，日志记操作者，§1.3）——与财务数据模拟语义一致，但属敏感面 | 产品确认接受即可，代码零改动；不接受则工具内按 `end_type` 原始值拒绝模拟场景（需 ReqCtx 增标记，改动小） |

## 5. 验证清单（实现后逐项过）

1. `tool_call_schema` 探针：`runtime` 不进 schema、参数 description 保真；
2. 注册表契约测试通过（`tests/ai/tools_v2/test_interface_doc_v2.py` 自动覆盖新工具 ui_label / result_model）；
3. 单测（mock `get_search_service`）：正常命中 / 无可见空间（empty_scope_ok 空结果 → ok+note）/ RagBusinessError 503（→ ok=false）/ top_k 透传 / hits=[] 显式序列化；
4. **KB 触发率专项**：多样问法 N 条（制度/流程/"根据知识库"/不点名知识库的文档内容问题/该用通用知识答的问题作反例），确认 LLM 按 §3.7 档 1 规则发起或豁免调用——不达标先调 docstring/提示词措辞，仍不行升级目录注入（§3.7 档 2）；这是方案 A 的核心风险项；
5. 真实环境冒烟（本地需 RAG 库有已入库 STANDARD 空间）：聊天问文档内容 → 步骤卡片"Searching knowledge base"→ 回答引用来源标题；
6. 副作用与可观测：`ai_rag_search_log` 新增 `caller_type=CHATBOT` 且 `trace_id`=本轮 `chatbot.chat` trace；space/entry/chunk 三级 `hit_count` +1；`ai_llm_call_log` 出现 agent=rag / node=query 的 embed 记录且 trace_id 同值；
7. 身份模拟场景：模拟某公司后提问 → 只命中该公司共享空间、不含他人私有空间（产品确认行为，§4 待决 2）；
8. 混合后端用例：人工造一个 es 空间与 pg 空间并存 → 工具返回 ok=false（不误报"无知识库"）；
9. 并发回归：KB 检索进行中，另一会话 SSE 流 token 输出无明显停顿（阻塞治理生效）；
10. 常规回归：不涉知识库的问题（闲聊/财务）不触发该工具（观察数轮）；
11. 三智能体切换：斜杠命令三档各发数轮——无标记时行为与现状一致（`standard`，向后兼容）；问题含 `/knowledge` 必检索且不调任何业务工具；含 `/combined` 时 dispatch 三分支各验一轮（纯业务问题只跑业务、纯文档问题只跑 kb、混合问题双场景两段作答且段落头清晰、`tool_results` 合并无丢失）；`/sql` 优先级最高、仅 standard 图有效（同时含 `/sql` 与 `/knowledge`/`/combined` 时走 standard）；词边界反例（URL 路径中段 `/knowledge/` 不触发）走 standard。

## 6. 改动文件清单

| 文件 | 动作 |
|------|------|
| `CIOaas-python/source/ai/tools/knowledge_base_tool.py` | 新增：@tool + 进程内调 recall + `_AsyncBackground` + 错误二分降级 |
| `CIOaas-python/source/ai/tools/dto/knowledge_result.py` | 新增：返回契约 pydantic 模型（snake_case 无 alias，不入 `dto/__init__.py`） |
| `CIOaas-python/source/ai/agent/chatbot_graph/tools.py` | 注册：import + `TOOL_REGISTRY_V2` + `__all__` + 头注释清单 6→7 |
| `CIOaas-python/source/ai/prompts/chatbot/retrieval_agent_prompt.py` | 2 处：职责边界①枚举补"知识库文档问答"；条款④改写为"先查知识库再用通用知识"（§3.7 档 1） |
| `CIOaas-python/source/rag/application/service/search_service.py` | 增强：`recall` 加 `caller_type="USER"` / `empty_scope_ok=False` 可选参并透传；service 层 4 处同步查询 `asyncio.to_thread` 化；注解修正（`company_id: Optional[str]`、`background: Any`） |
| `CIOaas-python/tests/ai/tools_v2/test_knowledge_base_tool.py` | 新增单测（mock recall；与既有 v2 工具测试同目录） |
| `CIOaas-python/source/ai/agent/chatbot_kb_graph/`（新子包，2026-07-06 迁出） | kb 纯知识库智能体独立子包（按「每个智能体一个子包」约定）：`build.py`（`build_kb_graph()` `guard→init→retrieve_kb→END`）/ `nodes/retrieval_kb_agent.py`（纯知识库子智能体节点，孪生 `retrieval_sql_agent.py` 结构，只绑 KB 工具、强纪律提示词）/ `tools.py`（约定占位）。横切件与流契约、装配原语跨包复用 chatbot_graph |
| `CIOaas-python/source/ai/agent/chatbot_graph/build.py` | `build_chat_graph()`（standard 主图）不动；`_traced_node`/`_route_after_guard` 保持在此供 kb/combo 子包跨包复用（build_kb_graph 已随 kb 迁往 chatbot_kb_graph） |
| `CIOaas-python/source/ai/agent/chatbot_combo_graph/`（新子包，2026-07-06 迁出） | combo 组合智能体独立子包：`build.py`（`build_combo_graph()` + `_route_after_dispatch`，含段落头包装与 attribution 合并）/ `nodes/dispatch_node.py`（场景分析：轻量 LLM 判 `business`/`kb`/`both`，失败降级 `both`）/ `nodes/combo_kb_node.py` + `nodes/combo_tool_node.py`（both 双段包装，combo_kb 引用 chatbot_kb_graph 的 retrieve_kb_node）/ `tools.py`（约定占位） |
| `CIOaas-python/source/ai/agent/chatbot_graph/state.py` | 新增 combo 场景键 `combo_scenario`（dispatch 结果，三图共享 `ChatState`）；`financial_mode` 不动 |
| `CIOaas-python/source/main.py` | lifespan 编译三张图 + 按 `agent_mode` 取图的访问器 |
| `CIOaas-python/source/ai/prompts/chatbot/`（kb 轨 + dispatch 提示词） | 新增：kb 子智能体系统提示词、dispatch 场景分析提示词、combo 段落头文案常量（确切文件名见实现计划） |
| `chatbot.chat` payload 模型 + `sse_provider.py` | payload 保留可选 `agent_mode`（归一 standard，供 API 调用方）；`stream_turn` 选图判定按问题文本斜杠命令 `/sql`＞`/knowledge`＞`/combined`＞ payload `agent_mode`＞standard（命令字面→模式：`/knowledge`→kb、`/combined`→combo，收口 `_MODE_MARKERS` 词边界正则常量） |
| `CIOaas-web`（聊天页） | `+` 工具菜单加斜杠命令静态提示（`/knowledge` `/combined`）；下拉选择器方案已撤除（2026-07-06 用户拍板改斜杠命令，前端不再发 `agent_mode`） |
| `CIOaas-python/source/ai/CLAUDE.md` | 文档同步：tools/ 清单加新工具；"工具经 Java 网关、不直连"约定登记第二个例外（知识库工具走 rag application/service 进程内调用，属 Python 域内跨模块、非 LG 业务数据取数） |
| `CIOaas-python/source/rag/CLAUDE.md` | 文档同步：模块定位"被 chatbot 经 /search 端点调用"改为"被 chatbot 经进程内 recall(caller_type=CHATBOT) 调用" |
| `CIOaas-python/CLAUDE.md` | 文档同步："数据查询能力（均经 Java 网关）"表补知识库行并注明例外 |
| `docs/AI-Chatbot/chatbot-tools-v2-interface.md` | 实现后经 `tools/interface_doc.py` 重新生成 |

不改：`retrieval_agent.py`（tool 轨节点本体）/ Java / DB schema。

## 7. V1 明确不做（YAGNI / 风险控制）

- 不加**自动路由**的意图分类器（用户显式选择的 kb/combo 轨已进范围，§3.8——路由依据是用户选择，不是模型判定）；
- 不做每轮强制检索（方案 C / §3.7 档 3）；
- 不做知识库目录注入（§3.7 档 2——触发率验证不达标时再上，数据面 `entry.summary` 已现成）；
- 不走 HTTP 自调用（方案 D；rag 拆独立服务时再切换）；
- 不做空间选择器 UI / 会话级空间绑定（V2 演进位已留）；
- 不召回 STRUCTURED 财报空间（口径冲突，§3.4 已留升级点）；
- 不做跨存储后端分组多路召回（已知限制登记，ES 默认关闭、风险低）；
- 不做 `_resolve_visibility` N 次串行查询的合并优化（独立小优化，另行处理）；
- 不做 rerank / 引用角标（LLM 文内引用 `source_title` 已够 V1）；
- sql 轨（`/sql`）不绑本工具——它是财务直查专用模式；
- 不为超管（非模拟态）放开跨公司知识库可见性（待产品决策，§4 待决 1）。
