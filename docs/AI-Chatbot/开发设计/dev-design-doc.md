# AI Chatbot 主图重构 开发设计：ReAct 取数 Agent（Python）

> 关联文档：
> - 设计契约（上游）：[../设计/react-orchestrator-design.md](../设计/react-orchestrator-design.md)
> - V1 设计基线：[../设计/design-doc.md](../设计/design-doc.md)
> - 数据查询坑/决策：[../../AI-Chatbot-数据查询/设计/issues-and-caveats.md](../../AI-Chatbot-数据查询/设计/issues-and-caveats.md)
>
> 阶段：⑤ 开发设计 | 版本：v1-draft | 日期：2026-06-24 | 端：Python（CIOaas-python） | 范围：主图编排重构落地方案
>
> 说明：本文给到**签名 / 关键算法 / 异常处理 / 文件改动**级别；完整函数体不写在此（遵循 docs 规范），落地以代码为准。Q1–Q8 决策见上游设计契约。

---

## 1. 前置与范围

- 纯 **Python** 改动（`CIOaas-python`），不涉及 Java / 前端。
- 上游契约（Q1–Q8）已定：嵌套工具、financial 单工具内部按注入 mode 分流、ReAct + 一轮内并行、不留 router、`_meta` 统一收尾、`list_companies`、synthesis 哑渲染、循环全留成功结果 + `args_key`。
- 现有可复用件：`ai/text2sql/`（公共 ReAct agent）、`ai/tools/*`（各 `@tool` + `_scope.resolve_company`）、`ai/chatbotgraph/`（图/节点/提示词）、`financial_strategy.resolve_financial_mode`。

---

## 2. 文件改动清单

| 操作 | 路径 | 说明 |
|------|------|------|
| 新增 | `ai/agent_loop.py` | **ai 域公共**有界 ReAct 工具循环 `run_tool_loop`（§3）。落点选 ai 顶层而非 `ai/text2sql/`：循环是通用件、不专属 text2sql |
| 新增 | `ai/chatbotgraph/gather_agent.py` | `gather_node` + ctx 构造 + 工具注册表 + dispatch 闭包工厂（§4） |
| 新增 | `ai/tools/company_list_tool.py` | `list_companies` 工具（§6）；或并入 `company_tool.py` |
| 修改 | `ai/tools/financial_tool.py` | 统一 `query_financial`：注入 `financial_mode` 内部分流 sql/api（§5） |
| 修改 | `ai/tools/_scope.py` | `CompanyScopeError` 加 `code`（`NEEDS_PICK`/`OUT_OF_SCOPE`/`REQUIRED`），供工具区分歧义 vs 越界（§7） |
| 修改 | `ai/text2sql/text2sql_agent.py` | `run_text2sql` 改为 `run_tool_loop` 的薄封装（§9） |
| 修改 | `ai/chatbotgraph/chat_graph.py` | 拓扑：删 `classify_intent`/`resolve_company`/6 个 `call_*` 及路由边；接 `gather_node`（§4.4） |
| 修改 | `ai/chatbotgraph/nodes.py` | 删 `classify_intent`/`resolve_company`/`call_*`；`build_synthesis` 简化为哑渲染 + 读 `_meta`（§8） |
| 修改 | `ai/chatbotgraph/prompts.py` | 新增 `ORCHESTRATOR_SYSTEM`；删 `CLASSIFY_SYSTEM`；`SYNTHESIS_SYSTEM` 增 `kind` 分支（§10） |
| 修改 | `ai/tools/__init__.py` | 导出 `list_companies`；维护注册表用到的工具集 |

> `state.py`：移除 `intent` / `company_mention` / `needs_pick` / `blocked_reason`（classify 产物）相关字段（保留 guardrail 的 blocked 标记）。

---

## 3. 共享 ReAct loop（`ai/agent_loop.py`）

### 3.1 返回类型

```
ToolLoopResult = TypedDict:
    results: list[ToolResultItem]     # 全留所有成功结果（Q8）
    final_text: str                   # 模型无工具收尾文本（拒答/澄清/纯知识），无则 ""

ToolResultItem = { "tool": str, "args_key": dict, "result": dict }
```

### 3.2 签名

```
async def run_tool_loop(*,
    system: str,
    question: str,
    history: list | tuple = (),
    tools: list,                       # @tool 对象，仅供 acomplete 绑定 schema
    dispatch: Callable[[str, dict], Awaitable[dict]],   # (name, args) -> result；注入封闭在闭包内
    summarize: Callable[[dict], str] = default_summary, # result -> 精简回喂文本
    arg_key: Callable[[str, dict], dict] = default_arg_key,  # (name,args) -> 识别性入参(主 company_id)
    model, trace,
    max_iters: int = 3,
    parallel: bool = True,
) -> ToolLoopResult
```

### 3.3 关键算法

1. `messages = [SystemMessage(system), *history, HumanMessage(question)]`；`results=[]`、`final_text=""`。
2. 循环至多 `max_iters` 次：
   - `res = await llm_db_router.acomplete(messages, model=, temperature=0, tools=tools, tool_choice="auto", trace=)`；异常 → 记 warning、`break`（不崩本轮）。
   - `tool_calls = res.tool_calls or []`；为空 → `final_text = res.content.strip()`、`break`。
   - 追加 `_assistant_message(res)`（复用 text2sql 现有：优先 kernel 原始 AIMessage，保 tool_call id 对齐）。
   - **并行分发（Q3）**：`outs = await asyncio.gather(*[dispatch(tc.name, tc.args) for tc in tool_calls], return_exceptions=True)`；按**下标**对回 `tool_calls`，逐个：
     - 异常或 `ok=False` → 记日志；`ok=True` → **追加**到 `results`（**不按名去重，Q8**）：`{"tool": name, "args_key": arg_key(name,args), "result": out}`。
     - 追加 `ToolMessage(content=summarize(out), tool_call_id=tc.id)`（成败摘要回喂，省 token）。
3. 返回 `{results, final_text}`。

### 3.4 默认 hook

- `default_summary(out)`：`ok=False` → `{ok:false, error|message}`；`ok=true` → 取轻量字段（`row_count`/`columns`、`period_count`、`tier/grouped_rates`、`rate`、`need_company` 等），不灌大数组。
- `default_arg_key(name,args)`：抽 `company_id`（有则带，外加 `date`/`type` 若存在），用于 synthesis 区分。

### 3.5 并发与对齐约束

- `gather(..., return_exceptions=True)` 保证单个工具抛错不拖垮整轮；该项落为 `{ok:False, error}`。
- **必须按下标/`tool_call_id` 对齐**回灌 `ToolMessage`（每个 tool_call 必须有且仅有一条对应 ToolMessage，否则 kernel 报错）。

---

## 4. `gather_node`（`ai/chatbotgraph/gather_agent.py` + 接图）

### 4.1 节点签名与返回

```
async def gather_node(state: dict) -> dict:        # 返回 {"tool_results": [...]}
```

### 4.2 ctx 构造（每轮一次，注入隔离在此）

```
ctx = {
  "auth_token":          state["auth_token"],
  "allowed_company_ids": _resolve_allowed(state),       # 见 4.3
  "financial_mode":      resolve_financial_mode(state), # 复用 financial_strategy
  "user_id":             state.get("user_id"),
  "accessible":          state.get("accessible_company_list") or [],  # list_companies / need_company 候选用
}
```

### 4.3 `_resolve_allowed(state)`

- 公司端（Redis `company_id` 有值）→ `[company_id]`（锁定单家）。
- 超管（空）→ `accessible_company_list` 的 id 列表。
- 与现 `resolve_company` 节点同口径，只是产出"范围"而非"单个"。

### 4.4 工具注册表 + dispatch 闭包

- `TOOL_REGISTRY: list` = 绑定给 `acomplete` 的 `@tool` 对象集（§6 表）。
- `_make_dispatch(ctx)` 返回 `async dispatch(name, args)`：按 `name` 分发到底层函数，**从 ctx 注入** `auth_token/allowed_company_ids/financial_mode`（LLM 不可见）；未知名 → `{ok:False, error:"unknown tool"}`。
- 节点体：
  ```
  res = await run_tool_loop(system=ORCHESTRATOR_SYSTEM, question=state["question"],
                            history=state.get("history") or [], tools=TOOL_REGISTRY,
                            dispatch=_make_dispatch(ctx), model=..., trace=...)
  tool_results = list(state.get("tool_results") or [])
  tool_results += res["results"]
  if not res["results"] and res["final_text"]:        # 无工具收尾
      tool_results.append({"tool":"_meta","args_key":{},
                           "result": _classify_closeout(res["final_text"])})  # 见 §7
  return {"tool_results": tool_results}
  ```

### 4.5 图拓扑（`chat_graph.py`）

```
START → guardrail → (load_context 并行) → gather_node → build_synthesis → END
guardrail blocked → build_synthesis（拒答），不进 gather_node
```
删除节点：`classify_intent` / `resolve_company` / `call_financial` / `call_financial_sql` / `call_benchmark` / `call_company` / `call_normalization` / `call_analysis` 及其条件路由（`_route_after_resolve` 等）。

---

## 5. 统一 `query_financial` 工具（`ai/tools/financial_tool.py`）

### 5.1 签名（LLM 可见 + 注入）

```
@tool("query_financial", parse_docstring=True)
async def query_financial_tool(
    request: str,                                  # 要查什么财务数据（自然语言）
    company_id: str | None = None,
    type: Literal["entry","forecast","system"] | None = None,
    from_date: str | None = None,
    view: Literal["Annually","Quarterly"] | None = None,
    *,
    auth_token:          Annotated[str, InjectedToolArg],
    allowed_company_ids: Annotated[list[str]|None, InjectedToolArg] = None,
    financial_mode:      Annotated[str, InjectedToolArg] = "tool",   # 'sql' | 'tool'
) -> dict
```

### 5.2 内部分流

1. `cid = resolve_company(company_id, allowed_company_ids)`；捕 `CompanyScopeError` → 转 `{ok:False, ...}`（§7）。
2. `financial_mode == "sql"`：`return await run_text2sql(question=request, company_id=cid)`
   - sql 轨的 `type`/日期口径由 `request` 自然语言 + text2sql 的 date/data_type 规则覆盖；`type/from_date/view` 仅 api 轨用。
3. 否则（api）：映射 `FinancialStatementsParams(company_id=cid, type=type or "entry", view=view or "Annually", from_date=from_date or 默认当年 1/1, auth_token=auth_token)` → 复用现有 `query_financial(...)` api 实现 → 干净投影。
4. 统一返回 `{ok, mode, ...}`：api 给 `metric_view`/`headers`，sql 给 `rows/columns`。synthesis 哑渲染。

> 现 `financial_statements_tool`（api-only）被本工具取代；`query_financial`（api 函数）保留为内部实现。

---

## 6. 工具注册表（绑定 + dispatch 映射）

| 工具名 | LLM 可见参数 | 注入 | 底层 |
|--------|--------------|------|------|
| `query_company` | `company_id?` | auth_token, allowed | `get_company_detail`；歧义→`need_company` |
| `list_companies` | —（无） | allowed / accessible | 返回 `accessible`（§4.2 ctx） |
| `query_financial` | `request,type?,from_date?,view?,company_id?` | auth_token, allowed, **financial_mode** | §5 分流 |
| `query_benchmark` | `company_id?,date?,data_sources?,benchmark_sources?` | auth_token, allowed | `query_benchmark`+`_benchmark_scoring` |
| `query_normalization` | `company_id?,metric?,date?` | auth_token, allowed | `query_normalization` |
| `compute_scenarios` | `from_date,to_date?,forecast_type?,company_id?` | allowed | `compute_scenarios` |
| `compute_opex_split` | `as_of_date?,company_id?` | allowed | `compute_opex_split` |
| `get_exchange_rate` | `from_currency,date,to_currency?,kind?` | —（与公司无关） | `get_exchange_rate` |
| `convert_currency` | `amounts,from_currency,date,to_currency?` | — | `convert_currency` |
| `run_analysis` | `request,company_id?` | auth_token, allowed | analysis 子图 |
| `query_playbook`（后续） | `question` | — | playbook GraphRAG |
| `search_memory`（后续） | `query,category?` | — | 记忆检索 |

> `list_companies`：`@tool` 无 LLM 可见参，节点 dispatch 直接回 `ctx["accessible"]`，不需要二次取数。

---

## 7. 公司歧义 / 越界 / 收尾（Q5/Q6）

### 7.1 `CompanyScopeError` 加 `code`

```
class CompanyScopeError(Exception):
    code: Literal["NEEDS_PICK","OUT_OF_SCOPE","REQUIRED"]
```
`resolve_company` 抛错时带 code：多家未指定→`NEEDS_PICK`；越界→`OUT_OF_SCOPE`；缺省无范围→`REQUIRED`。

### 7.2 工具层转换

工具捕 `CompanyScopeError`：
- `NEEDS_PICK` → `{ok:False, need_company:[{id,name}...]}`（候选取自注入范围/`accessible`）。
- 其余 → `{ok:False, message:...}`。

### 7.3 `_classify_closeout(final_text)`（§4.4 无工具收尾）

- 产 `{kind, note}`：默认 `out_of_scope`；若上一轮 `results` 里出现 `need_company` → `clarify`（带候选）；模型明示缺数据 → `no_data`。
- 进 `tool_results` 作 `_meta`，由 synthesis 成文（§8）。

---

## 8. synthesis 改造（`nodes.build_synthesis` + `prompts.SYNTHESIS_SYSTEM`）

- **删除** 按 `intent` 注入全公司列表的启发式：`build_synthesis` 只组 `{identity, active_company_id, tool_results}`（公司清单由 `list_companies` 的结果体现）。
- **读 `_meta`**：`tool_results` 中若含 `{tool:"_meta", result:{kind,...}}`，作为成文指令传给 synthesis。
- `SYNTHESIS_SYSTEM` 增 `kind` 分支：`out_of_scope`（软拒，说明能帮什么）/ `clarify`（追问选公司）/ `no_data`（说明缺什么）；其余正常据 `tool_results` 作答。保持**默认英文、面向业务、不泄技术细节**。
- `attribution`：沿用 `source:{tool}`；RAG 接入后追加召回来源 id。

---

## 9. text2sql 适配（`ai/text2sql/text2sql_agent.py`）

- `run_text2sql(question, company_id, ...)` 改为 `run_tool_loop` 的薄封装：
  - `dispatch` 闭包注入 `company_id` + `allowed_tables`/`company_scoped_tables`（schema_provider），分发 `run_sql`/scenario/opex/fx（即现 `_dispatch_tool`）。
  - `system = REACT_SYSTEM.format(...)`、`tools = _TOOLS`、`max_iters` 沿用。
  - 返回形状对齐现状：从 `ToolLoopResult.results` 取（Q8 后为列表）→ 仍回 `{ok, mode:"sql", results:[...]}`（与现一致）。
- 收益：text2sql 与 gather 共用一份循环实现，行为一致、维护一处。

---

## 10. prompts 改动（`ai/chatbotgraph/prompts.py`）

- **新增** `ORCHESTRATOR_SYSTEM`（大纲见设计文档 §7）：角色=取数编排者、各工具能力边界、公司处理（传/省 `company_id`）、鼓励一轮内并行、依赖链（先检索再取数）、节制与诚实、有界。中文指令。
- **删除** `CLASSIFY_SYSTEM`（intent 分类不再需要）。
- **扩展** `SYNTHESIS_SYSTEM`：增 `_meta.kind` 三分支措辞。

---

## 11. 异常处理与安全

- **每工具** body try/except → `{ok:False, message}`，绝不抛断本轮（沿用现有契约）。
- **循环** `acomplete` 失败 → break；单工具 `gather` 异常 → 该项 `{ok:False}`，不影响同轮其它。
- **注入红线**：`auth_token`/`allowed_company_ids`/`financial_mode` 一律 `InjectedToolArg`，LLM 不可见；工具不读 `state`（注入在节点 dispatch 闭包）。
- **护栏不变**：sql 轨 `:company_id` 绑定 + 只读 + 表白名单 + 超时 + 行数上限；ORM 只读映射只读不写。
- chatbot **不做公司级授权**（交平台/Java）；本重构只做范围收敛（`allowed_company_ids`）。

---

## 12. 删除清单（细化）

- `nodes.py`：`classify_intent`、`resolve_company`、`call_financial`、`call_financial_sql`、`call_benchmark`、`call_company`、`call_normalization`、`call_analysis`、`_route_after_resolve` 及相关私有（`_match_company` 视情保留给工具层 need_company）。
- `chat_graph.py`：上述节点的 `add_node`/`add_edge`/条件路由。
- `prompts.py`：`CLASSIFY_SYSTEM`。
- `state.py`：`intent`/`company_mention`/`needs_pick` 等 classify 产物字段。
- `financial_statements_tool`（被统一 `query_financial` 取代）。

---

## 13. 待定取值（实现时定，先给建议）

| 项 | 建议初值 | 备注 |
|----|----------|------|
| `max_iters`（gather） | 4 | 比 text2sql(3) 略大，容纳"检索→取数→对比" |
| 并发度 | 不设硬上限（依赖工具自身 to_thread/超时） | 一轮 tool_calls 数天然有限 |
| 各工具 statement_timeout | 沿用现 8000ms | sql/scenario/opex/fx 已有 |
| history 注入窗口 | 最近 10 条 | 对齐现 synthesis |

---

## 14. 测试要点（指向 ⑨ 单元测试）

- `run_tool_loop`：并行分发 + `tool_call_id` 对齐；Q8 全留（同名多次/多公司不丢、失败不入）；无工具收尾→`final_text`；`acomplete` 异常→优雅 break。
- `_make_dispatch`：注入正确、LLM 不可见；未知工具回错。
- `query_financial`：mode=sql→走 text2sql、mode=tool→走 api；参数映射；`CompanyScopeError`→`need_company`/越界 message。
- `_resolve_allowed`：公司端锁单家 / 超管全列表。
- `build_synthesis`：哑渲染、`_meta.kind` 分支、无 intent 依赖。
- AI/网络调用一律 mock（`llm_db_router.acomplete`、lgpi_api、DB）。

---

## 15. 实现顺序

1. `ai/agent_loop.py`（`run_tool_loop` + 默认 hooks）。
2. `text2sql_agent` 改薄封装（验证回归：text2sql 行为不变）。
3. `_scope.CompanyScopeError.code` + 工具层 `need_company` 转换。
4. 统一 `query_financial` 工具 + `list_companies` 工具。
5. `gather_agent.py`（ctx + 注册表 + dispatch）+ `ORCHESTRATOR_SYSTEM`。
6. `chat_graph` 拓扑切换 + `nodes` 删旧 + `build_synthesis`/`SYNTHESIS_SYSTEM` 改造。
7. 回归：财报/对标/公司/normalization/分析 + 跨域组合 + 歧义/越界/超范围。
8. 后续：`query_playbook`/`search_memory` 作为新 case 接入（不动主循环）。
