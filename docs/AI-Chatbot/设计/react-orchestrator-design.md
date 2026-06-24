# AI Chatbot 主图重构设计：ReAct 取数 Agent（改动契约）

> 关联文档：
> - V1 设计（现状基线）：[./design-doc.md](./design-doc.md)
> - 数据查询层设计：[../../AI-Chatbot-数据查询/设计/design-doc.md](../../AI-Chatbot-数据查询/设计/design-doc.md)
> - 数据查询坑/决策：[../../AI-Chatbot-数据查询/设计/issues-and-caveats.md](../../AI-Chatbot-数据查询/设计/issues-and-caveats.md)
>
> 阶段：④ 设计 | 版本：v1-draft | 日期：2026-06-24 | 范围：主图编排重构（不含完整实现，实现细节留⑤开发设计）

---

## 0. 一句话目标

把 `chat_graph` 主图中**按意图确定性路由到单个 `call_*` 节点**的结构，替换为**单个 ReAct 取数 Agent 节点**：大模型绑定一组工具、自主决定调哪些/调几次（支持一轮内并行），覆盖财报 / 对标 / 公司 / normalization / 分析，并为后续接入 **playbook + 10 类记忆文件（RAG 知识库）** 预留扩展位（新增能力 = 加一个工具，不动主循环）。

---

## 1. 背景与动机

现状（确定性路由）的局限：

- **单意图单分支**：`classify_intent` 只选一个 intent → 只跑一个 `call_*`。跨域问题（"我的营收多少、同行里排第几"=financial+benchmark）命中不全。
- **不能跨工具编排**：取公司 → 取其财务 → 换币 → 对比，这类链式组合做不到。
- **扩展成本高**：加能力要"加节点 + 加路由边 + 加 classify 标签"。
- 已具备的基础：`CHATBOT_TOOLS`（company/financial/benchmark/normalization 的 `@tool`）已写好；**`text2sql` 已从 `ai/chatbotgraph/text2sql/` 提升为 `ai/text2sql/` 公共 ReAct agent**（自包含 agent + schema_provider + schema/，供 ai 域复用、不再属聊天主图私有）；`analysis` 是 plan 子图。本次主要是**补一个顶层取数 Agent 节点并退役确定性路由**。
  > 该提升正向支撑本设计：text2sql 已是可复用公共件 → 既便于以嵌套工具接入（Q1），也便于抽出共享 ReAct loop（§8 步骤 1）。

---

## 2. 决策摘要（讨论结论）

| # | 议题 | 结论 |
|---|------|------|
| Q1 | text2sql / analysis 如何接入 | **封成嵌套工具**（顶层只见一句描述，不背其内部大 schema；省 prompt/上下文，代价是多一层调用延迟） |
| Q2 | financial 双轨（api/sql）如何处理 | **收敛成一个 financial 工具**，内部按注入的 `financial_mode` 分流；mode 由节点 `resolve_financial_mode(state)`（env 短路 → state 回退）解析后 **InjectedToolArg 注入**，LLM 不可见、不可选 |
| Q3 | 顶层用 ReAct 还是 Plan | **ReAct**（加"一轮内并行 tool_calls"）；`analysis` 的 plan 作为子工具保留。RAG 问答"先检索再决定"的数据依赖链更契合 ReAct |
| Q4 | 是否保留确定性 router 作回退 | **不保留**，全量切 Agent（无并行 router 路；回退靠部署回滚，见 §8） |
| Q5 | 公司名歧义（原 needs_pick） | 工具内 `resolve_company` 匹配失败/多义 → 返 `{ok:False, need_company:[候选]}`（不抛）；Agent 据此**无工具收尾产澄清提问**（归入 Q6 机制） |
| Q6 | Agent 无工具收尾（拒答/澄清/缺数据）走哪条路 | **统一经 synthesis**：Agent 写 `_meta` 信号进 `tool_results`，由 synthesis 礼貌成文（措辞/语言/脱敏单一出口） |
| Q7 | synthesis 的全公司列表注入启发式 | 新增 `list_companies` 工具；synthesis 退化为**纯 `tool_results` 哑渲染**，删除 intent 启发式 |
| Q8 | 工具结果在循环内的累积策略 | 共享 loop **全留所有成功结果**（不按工具名去重）、每条带 `args_key`（主含 `company_id`）标识；**工具内部不变**。支撑超管"一轮对比多家"等多次同名调用；失败调用不入（无重试噪声） |

---

## 3. 节点 / 边（拓扑变更）

### 3.1 变更前（现状）

```
START → guardrail → classify_intent → resolve_company → ┬ call_financial
                  └ (并行) load_context ┘                ├ call_financial_sql
                                                          ├ call_benchmark
                                                          ├ call_company
                                                          ├ call_normalization
                                                          └ call_analysis      ┘ → build_synthesis → END
```

### 3.2 变更后（目标）

```
START → guardrail ─┬───────────────→ retrieve_node → build_synthesis → END
                   └ (并行) load_context ┘
（guardrail blocked → 直接 build_synthesis 礼貌拒答；不进 retrieve_node）
```

### 3.3 节点职责

| 节点 | 去留 | 职责 |
|------|------|------|
| `guardrail` | **保留** | 安全闸门（注入/blocked 检测）。**不交给 Agent 自判**。blocked → 短路 build_synthesis |
| `load_context` | **保留（并行）** | 历史窗口 + `accessible_company_list`（公司授权范围来源） |
| `classify_intent` | **删除** | intent 分类不再需要（Agent 自选工具）；out_of_scope = Agent 不调工具直接礼貌答；blocked 归 `guardrail` |
| `resolve_company` | **删除** | 公司域收敛下沉到"每次工具调用校验 `allowed_company_ids`"（见 §4.2），不再前置统一解析 |
| `call_financial / _sql / benchmark / company / normalization / analysis` | **删除（合并）** | 全部合进 `retrieve_node`；底层取数能力改以工具形态暴露 |
| `retrieve_node` | **新增** | ReAct 取数 Agent：绑工具、循环自驱、累积 `tool_results`（见 §5） |
| `build_synthesis` | **保留（简化）** | **纯 `tool_results` 哑渲染**（删除按 intent 注入全公司列表的启发式，Q7）；读 `_meta` 信号处理拒答/澄清/缺数据（Q6）；由 `chat_turn` **流式**产出英文答案 |

> 标题 `generate_title` 仍在 `chat_turn` 用 `asyncio.create_task` 与图并发，不挂图，本次不受影响。

---

## 4. 注入契约（安全红线）

### 4.1 每轮解析一次的注入上下文（在 `retrieve_node` 节点内构造）

| 字段 | 来源 | 用途 |
|------|------|------|
| `auth_token` | `state['auth_token']` | 经 Java 网关回调透传用户 token（api 轨工具用） |
| `allowed_company_ids` | Redis `company_id` / `accessible_company_list` | **公司授权范围**：公司端=锁定的单个；超管=可访问全列表 |
| `financial_mode` | `resolve_financial_mode(state)`（env `CHATBOT_FINANCIAL_MODE` 短路 → `state['financial_mode']`） | financial 工具内部 api/sql 分流 |
| `user_id` | `state['user_id']` | trace / 审计 |

### 4.2 公司授权：从"前置节点"改为"每次工具调用校验"

- 复用现有 `@tool` 形态：`company_id`（LLM 可见、可省）+ `allowed_company_ids`（InjectedToolArg）+ 工具内部 `resolve_company(company_id, allowed_company_ids)`。
- 规则：LLM 传 `company_id`（或省略 → 唯一可访问公司）；工具校验 `company_id ∈ allowed_company_ids`，越界拒绝。
- 等价安全：公司端 `allowed_company_ids` 只有一个 → 天然锁定；超管为全列表 → 可一题问多家（今天单 intent 做不到）。

### 4.3 不可破坏的约束

- `auth_token` / `allowed_company_ids` / `financial_mode` 一律 **InjectedToolArg**，对 LLM **不可见、不可改**。
- **工具不直接读 LangGraph `state`**：state 访问是节点职责，节点解析后注入；工具保持可独立调用/可单测。
- text2sql 轨仍强制 `:company_id` 绑定 + 只读 + 表白名单 + 超时 + 行数上限（不变）。
- chatbot **不做公司级授权**（交平台/Java）；本设计只做范围收敛（allowed 列表）。

---

## 5. ReAct 循环契约（`retrieve_node`）

> 实现层面复用 `text2sql_agent` 既有循环（`_assistant_message` / 精简回喂 / `max_iters` / `tool_call_id` 对齐），本节只定契约；完整代码留⑤开发设计。

| 契约项 | 约定 |
|--------|------|
| 入口 | `acomplete(messages, tools=<注册表>, tool_choice="auto", trace=...)`（kernel `bind_tools`，不直连 SDK） |
| 消息 | `[SystemMessage(ORCHESTRATOR_SYSTEM), *history[-10:], HumanMessage(question)]` |
| 迭代上限 | `max_iters`（有界，控成本/延迟；缺省小值如 3-4） |
| **一轮内并行** | 模型一轮可发多个 `tool_calls`；对**相互独立**的调用 `asyncio.gather` 并发执行，再按 `tool_call_id` 对齐回灌 |
| 喂回模型 | **精简摘要**（成败 + 行数/关键字段），省 token，仅供判断是否继续 |
| 交 synthesis | **全留所有成功结果**（不按工具名去重，Q8）累积进 `state['tool_results']`，每条 `{tool, args_key, result}`——`args_key` 主含 `company_id`（必要时含 date/type），供 synthesis 区分"哪家/哪期"；失败调用不入（无重试噪声） |
| 终止 | 某轮无 `tool_calls` → 结束；若属拒答/澄清/缺数据，先写 `_meta` 信号进 `tool_results`（见 §5.1）；或达 `max_iters` → 带已取数据进 synthesis |
| 注入 | 见 §4，分发器按工具名注入 ctx 字段 |
| 流式 | **两阶段**：取数阶段（循环，不流式）→ 合成阶段（`build_synthesis`→`chat_turn`，流式）。中间 tool-calling 轮次不泄给用户 |

### 5.1 无工具收尾 / 公司歧义 / 越界 的统一处理（Q5/Q6/Q7）

切除 `classify_intent` / `resolve_company` 后，它们顺带承担的"软拒 / 歧义选择 / 列公司"三件事按下表重新落位，**统一汇入"Agent 无工具收尾 → 写 `_meta` → synthesis 成文"一条路径**：

| 场景 | 触发 | 处理 |
|------|------|------|
| **缺数据/越界**（out_of_scope） | Agent 判断这些工具都答不了 | 不调工具，写 `{tool:"_meta", result:{kind:"out_of_scope", note}}` → synthesis 礼貌说明能帮什么、不答原问题 |
| **公司歧义**（原 needs_pick） | 工具返 `{ok:False, need_company:[候选]}` | Agent 下一轮不再调工具，写 `{tool:"_meta", result:{kind:"clarify", candidates}}` → synthesis 产澄清提问 |
| **列出我的公司** | 用户问"我有哪些公司" | Agent 调 `list_companies` → 结果进 `tool_results` → synthesis 渲染（不再靠 intent 启发式） |

约定：`_meta` 是保留工具名（非真实工具），仅作 synthesis 的成文信号；`SYNTHESIS_SYSTEM` 据 `kind` 选措辞（out_of_scope 软拒 / clarify 追问 / no_data 说明缺啥）。

---

## 6. 工具注册表

> "内部实现"列标注是否为嵌套工具（内部再跑子 agent/子图，函数直调、不增加 LLM 选择轮次）。

| 工具名（LLM 可见） | LLM 可见参数 | 注入参数（InjectedToolArg） | 内部实现 | 返回要点 |
|--------------------|--------------|------------------------------|----------|----------|
| `query_company` | `company_id?` | `auth_token`, `allowed_company_ids` | `get_company_detail`（api） | 身份/简介/币种/状态；公司歧义 → `{ok:False, need_company:[候选]}`（Q5） |
| `list_companies` | —（无） | `allowed_company_ids` | 返回 `accessible_company_list` | 公司清单（"我有哪些公司"，Q7） |
| `query_financial` | `request`(自然语言), `type?`, `period?`, `company_id?` | `auth_token`, `allowed_company_ids`, **`financial_mode`** | **双轨分流**：sql→`run_text2sql`（嵌套）/ api→`query_financial` | 指标行 / rows |
| `query_benchmark` | `company_id?`, `date?`, `data_sources?`, `benchmark_sources?` | `auth_token`, `allowed_company_ids` | `query_benchmark`+`_benchmark_scoring`（Python 聚合） | 评分卡（百分位/卡片） |
| `query_normalization` | `company_id?`, `metric?`, `date?` | `auth_token`, `allowed_company_ids` | `query_normalization`（api，空则先拉 metricOptions） | 标准化值↔原始↔公式↔FX 溯源 |
| `compute_scenarios` | `from_date`, `to_date?`, `forecast_type?`, `company_id?` | `allowed_company_ids` | `compute_scenarios`（直连 DB ORM） | P05/P50/P95 情景 |
| `compute_opex_split` | `as_of_date?`, `company_id?` | `allowed_company_ids` | `compute_opex_split`（含 `peer_resolver`） | R&D/S&M/G&A 占比 |
| `get_exchange_rate` | `from_currency`, `date`, `to_currency?`, `kind?` | —（FX 与公司无关） | `get_exchange_rate`（直连 DB ORM） | 单笔汇率 |
| `convert_currency` | `amounts`, `from_currency`, `date`, `to_currency?` | — | `convert_currency` | 明确金额换算 |
| `run_analysis` | `request`(自然语言), `company_id?` | `auth_token`, `allowed_company_ids` | **嵌套**：analysis plan 子图 | 多步分析结果 |
| `query_playbook`（后续） | `question` | — | **嵌套**：playbook GraphRAG（图+pgvector） | 召回片段（带来源 id） |
| `search_memory`（后续） | `query`, `category?` | — | 记忆库检索（10 类作 `category` 枚举过滤，**单工具**非 10 个） | 召回片段（带来源 id） |

> RAG 工具（`query_playbook` / `search_memory`）作为**后续新增 case** 接入分发器，**不改主循环**；召回**内容走 tool 结果、不进 system prompt**；来源 id 进 `attribution` 供 synthesis 标注出处。

---

## 7. ORCHESTRATOR_SYSTEM 提示词大纲

> 提示词一律中文；最终面向用户的回答默认英文（沿用 `SYNTHESIS_SYSTEM` 约定，本提示词只管取数编排）。

1. **角色**：你是取数编排者，调用工具收集回答所需数据/知识；**不直接面向用户措辞**（最终答案由后续合成阶段产出）。
2. **工具选择**：列各工具能力边界——何时 financial / benchmark / normalization / scenario / opex / fx / analysis / playbook / memory；不确定先检索知识（playbook/memory）再取数。
3. **公司处理**：从可访问公司传 `company_id`；只有一个公司时可省略；不要臆造公司 id。
4. **并行**：对**相互独立**的子任务，**同一轮内一次性发起多个工具调用**。
5. **依赖链**：需要先知道口径/定义时，先 `query_playbook`/`search_memory` 再据结果取数。
6. **节制与诚实**：能用已有结果就别重复调；这些工具/表都查不到所需数据时，**不调用任何工具**，一句话说明缺什么；不臆造数字。
7. **有界**：迭代受 `max_iters` 限制。

---

## 8. 灰度开关与迁移（Q4：不保留 router）

- **决策**：**不保留确定性 router 作并行回退**。主图只有 Agent 路，删除 `classify_intent` / `resolve_company` / 6 个 `call_*` 节点与对应路由边。
- **因此**：无 `router|agent` 运行期切换开关。
- **仍保留的运行期开关**：`CHATBOT_FINANCIAL_MODE`（`sql|tool|未设`）——它现在作用于 **financial 工具内部** 的轨道选择（§4.1 注入），语义不变。
- **回滚策略**：因无应用内回退，线上回退 = **部署回滚（git revert / 回退构建）**。取舍：去掉 router 让代码与心智更简单，代价是回滚是部署级而非开关级。
  - 可选（本次决定**不做**）：迁移期临时加一个短命 kill-switch env。若上线后需要，再单独评估。
- **迁移步骤建议**（顺序）：
  1. 抽公共 ReAct loop（把 `ai/text2sql/text2sql_agent.py` 的循环提为 **ai 域公共件**，text2sql 与 retrieve 及后续 ai 域 agent 共用；与 text2sql 已是公共件的定位一致）。
  2. 统一 `query_financial` 工具（双轨内部分流，§6）。
  3. 实现 `retrieve_node`（注册表 + 并行分发 + 注入），改主图拓扑（§3.2），删除旧路由节点。
  4. 回归：财报/对标/公司/normalization/分析全意图 + 跨域组合问。
  5. 后续：`query_playbook` / `search_memory` 作为新 case 接入（不动主循环）。

---

## 9. 影响面

| 类别 | 内容 |
|------|------|
| **删除** | `classify_intent`、`resolve_company`、`call_financial`、`call_financial_sql`、`call_benchmark`、`call_company`、`call_normalization`、`call_analysis` 及其路由边；intent 分类提示词/标签 |
| **新增** | `retrieve_node` 节点 + `ORCHESTRATOR_SYSTEM` + 工具分发器 + `_resolve_allowed(state)` + 统一 `query_financial` 工具 + `list_companies` 工具 + `_meta` 收尾信号约定 + 可复用 ReAct loop |
| **复用（含简化）** | `guardrail` / `load_context` / `chat_turn`（流式两阶段）；`build_synthesis` **简化为纯 `tool_results` 哑渲染 + 读 `_meta`**；`SYNTHESIS_SYSTEM` 增 `kind` 措辞分支；`CHATBOT_TOOLS` 及各 `@tool`；**`ai/text2sql` 公共 agent**（`run_text2sql` → `query_financial` sql 轨）；`analysis` 子图（→ `run_analysis`）；`resolve_financial_mode`、`peer_resolver`、ORM 模型 |
| **不变** | chatbot 不做公司级授权；只读/白名单/超时护栏；流式 UX；标题并发生成 |

---

## 10. 待定 / 后续

- RAG 接入（playbook GraphRAG + 10 类记忆）的具体工具契约（入参/召回排序/来源标注），在其专属功能目录另立设计。
- `max_iters`、并发度、各工具超时的具体取值（⑤开发设计定）。
- 可观测性：每轮工具调用 trace、引用来源透出。
