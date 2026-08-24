# Chatbot 按文件圈定召回 — 开发设计

> 关联文档：[知识库问答三智能体](./2026-07-05-chatbot-knowledge-base-qa-design.md)、[会话文件向量召回 v2](./2026-07-21-session-file-vector-recall-design-v2.md)
> 范围：仅 Python（`CIOaas-python`）。无 Java / 前端 / DDL 改动。
> 状态：设计定稿，待「开发」指令实现。日期 2026-07-22。

## 一、背景与目标

现状 chatbot 的知识库检索（`search_knowledge_base`）按**端 + 公司作用域**整体召回，用户无法在提问时**点名某个文件**让回答只基于该文件。本设计新增「按文件圈定召回」能力：

- 示例 1（指代式）："刚才上传的这个文件，帮我分析一下 xxx" —— 指本轮/本会话最近上传的文件。
- 示例 2（显式文件名）："2019 Monthly Sheet.pdf 里，拉出第一季度财务数据跟三季度对比" —— 按文件名指定。

可圈定范围 = 各端现有 `search_knowledge_base` 的召回范围：

| 端 | 可圈定文件范围 |
|----|----------------|
| 公司端 | 本公司范围内任意文件 |
| 管理端 | 可访问公司 + 管理端 + 当前会话 任意文件 |

## 二、关键前提：底座现成，安全零回归

排查确认三块已就位，本设计只做「文件收窄」这一薄层 + 一个「文件指代 → file_id」解析步骤：

1. **`search_service.recall` 已支持 `file_ids` 过滤**，且在 chunk 层与权限闸门是 `AND` 叠加：
   ```
   WHERE space_id IN (按端圈定的 spaces)
     AND (company_id IN 可访问集 OR thread_id = 本会话)   -- 权限闸门（不变）
     AND file_id IN (圈定的文件)                           -- 新：文件收窄
   ```
   → `file_ids` 是「收窄」不是「授权」：越权 file_id 也召不到（不在 scoped space / 不满足 company·thread）。`search_knowledge_base` 侧安全自动成立。

2. **本轮上传文件在图/工具运行前已登记**：`sse_provider.stream_turn` 先 `attach_files_to_message`（写 `ai_file_registry`）再 `astream` 跑图。故 find_files 查登记表时，本轮文件与历史文件一视同仁可查。

3. **`ai_file_registry` / `ai_rag_entry` 列齐全**：registry 有 `company_id` / `thread_id` / `business_type` / `status`；entry 有 `file_id` / `summary`（`company_id` 已由 V017 放开 NOT NULL 供会话文件）。**无需 DDL/迁移**。

## 三、已定决策

| # | 决策 | 结论 |
|---|------|------|
| D1 | 指代式是否单独维护 turn 逻辑 | **否**。指代语义跨轮（"前几分钟上传的"），turn_entry_ids 只覆盖当前消息、本就不够；统一走 find_files，消除双路径与模型路由歧义。 |
| D2 | `get_file_summary` 是否一并统一 | **是（严格统一 / A 方案）**。改为收 `file_ids`（来自 find_files），不再读 `ctx.turn_entry_ids`；`turn_entry_ids` 彻底退役。代价：总结常见场景 +1 次 find_files 调用（已接受）。 |
| D3 | find_files 独立工具 vs 并进 search | **独立工具**。解析（可能多候选/消歧）与召回职责分离，且 summary 与 search 共用同一解析结果。 |
| D4 | 作用域收口 | 抽 ai 层公共 helper，find_files / get_file_summary / knowledge_base_tool 三方共用，杜绝漂移。 |

## 四、工具拓扑与调用契约

```
                    ┌──────────────────────────────────────┐
用户问题 ─[ReAct]──▶│ find_files(name_hint?)   ← 唯一解析器  │
                    │  从 ctx 取 scope → 查 registry⨝files   │
                    │  返回 files[] 按 uploaded_at 倒序       │
                    └───────────────┬──────────────────────┘
                       模型挑出 file_id（多候选消歧/问用户）
                    ┌───────────────┴──────────────────────┐
                    ▼                                        ▼
   search_knowledge_base(query, file_ids=[...])     get_file_summary(file_ids=[...])
   = 该文件内相似度召回片段（问某点）                  = 该文件整篇摘要（总结）
```

| 工具 | 入参 | 返回 | 变化 |
|------|------|------|------|
| `find_files`（新） | `name_hint?: str`、`limit?: int`（默认 10，最大 20） | `files[]: {file_id, filename, uploaded_at, company, source, uploaded_this_turn}`（`source` = `session` / `company`；`uploaded_this_turn` 见 §5.4），按 `uploaded_at` 倒序 | 新增 |
| `search_knowledge_base`（扩展） | 加 `file_ids?: list[str]` | 不变 | 空=整范围（行为不变）；给了=收窄 |
| `get_file_summary`（改） | `file_ids: list[str]` | 不变（`summaries[]`） | 由读 `ctx.turn_entry_ids` 改为收入参 |

两种用法收敛为一条链：
- 指代式：`find_files()`（不带 name，拿最近几条）→ 挑 file_id → search/summary。
- 显式名：`find_files("2019 Monthly Sheet")` → 挑 → search/summary。

`search` / `summary` 的 `file_ids` 均为 find_files **检索得到**的 id（非模型编造），与 `get_companies` 的 UUID-only 范式一致；`get_file_summary` 原「绝不让模型传 file_id」口径随之反转，理由同 get_companies。

## 五、作用域收口与安全

### 5.1 文件级作用域谓词（直接镜像 recall 行级过滤）

| 端 | 谓词（施于 `ai_file_registry`） |
|----|------|
| 公司端 | `company_id = home_company_id AND end_type = 'APP'` |
| 管理端 | `(company_id IN 可访问集 AND end_type IN ('APP','ADMIN')) OR (company_id IS NULL AND thread_id = 本会话)` |

与 recall 的行级过滤 `(company_id IN 可访问集 OR thread_id = 本会话)` 同源，保证「find_files 能列出的 ⊆ recall 能召回的」，无漂移。

### 5.2 公共 helper

`ai/tools/_support/file_scope.py`：`resolve_chat_file_scope(ctx) -> ChatFileScope`（`{company_ids, thread_id, is_company_end}`）。三方共用：

- `find_files`：据此查候选。
- `get_file_summary`：据此把入参 file_ids **交集**到可见文件（见 5.3）。
- `knowledge_base_tool`：复用其 `company_ids` / `thread_id` 供现有空间圈定（空间解析仍走 `business_association_service`）。

### 5.3 ⚠️ 安全点：get_file_summary 必须做作用域校验

- `search_knowledge_base(file_ids)`：安全**自动成立**（recall 内 `file_ids` 与 space+company/thread 是 AND，越权 id 召空）。
- `get_file_summary`：现实现是 `session.get(RagEntry, id)` 按 id 直取摘要、**无作用域过滤**。改收 LLM 传的 file_ids 后，若不校验，模型传别家 file_id 即可读到摘要 = **越权**。
  → get_file_summary **必须**先用 `resolve_chat_file_scope` 把入参 file_ids 交集到本人可见文件（复用 find_files 的 registry 谓词、附加 `file_id IN (入参)`），只对幸存者取摘要。

### 5.4 「本轮上传」标记（同名文件消歧，2026-07-22 修）

**问题**：统一走 find_files、退役 turn_entry_ids 后，"本条消息刚上传的就是 file_id X" 的精确信号丢失。
当同一公司 KB 里存在**同名文件的新旧两份**（用户在新会话再次上传同名文件），且**只传文件无文字**时，
find_files 按名/时间只能给出两个同名候选，模型分不清哪个是本次刚传的 → 弹消歧反问（回归）。

**修法（保持 find_files 单路径，仅补回精确信号作 hint）**：
- `ReqCtx` 增 `turn_file_ids`（本轮上传文件的 **file_id**，两处 build_req_ctx 从 `state["turn_files"]` 投影）——
  注意是 file_id、非退役的 entry_id，且**只作 find_files 的"本轮"标记**，不作总结取数键（总结仍收 find_files 的 file_ids，单路径不变）。
- `find_files` 对 `file_id ∈ turn_file_ids` 的候选置 `uploaded_this_turn=true`。
- 提示词：用户指代"刚才/这次上传的这个文件"时，**优先选 `uploaded_this_turn=true` 的候选、哪怕存在同名旧文件也直接用、不反问**；
  仅在无本轮标记 / 用户明确要历史文件时才列候选消歧。

## 六、逐文件改动清单

### 新增
| 文件 | 内容 |
|------|------|
| `ai/tools/find_files_tool.py` | `@tool find_files`：从 `runtime.context` 取 scope → 调 file_registry `application/service` 查候选 → 返回 typed DTO；`metadata`（ui_label / result_model） |
| `ai/tools/dto/find_files_result.py` | `FindFilesResult` / `FoundFile`（每字段中文 description） |
| `ai/tools/_support/file_scope.py` | `resolve_chat_file_scope(ctx)` 公共 helper + `ChatFileScope` dataclass |

### 修改
| 文件 | 改动 |
|------|------|
| `ai/tools/knowledge_base_tool.py` | args_schema 加 `file_ids: Optional[list[str]]`；透传 `recall(file_ids=...)`；空间圈定改用公共 helper 的 company_ids/thread_id（等价重构，不改语义） |
| `ai/tools/file_summary_tool.py` | 由读 `ctx.turn_entry_ids` 改为收 `file_ids` 入参；先作用域交集校验再取摘要；docstring 反转口径 |
| `ai/tools/_support/request_context.py` | **删 `turn_entry_ids` 字段**（`turn_files` 在 state 保留给 file_gate） |
| `ai/agent/chatbot_graph/nodes/retrieval_agent.py` | build_req_ctx 删 `turn_entry_ids` 投影（约 L316）；`TOOL_REGISTRY` 纳入 find_files |
| `ai/agent/chatbot_graph/nodes/retrieval_kb_agent.py` | build_req_ctx 删 `turn_entry_ids` 投影（约 L59）；kb 节点绑定加 find_files + get_file_summary |
| `ai/agent/chatbot_graph/tools.py` | `TOOL_REGISTRY_V2` 加 `find_files` |
| `rag/application/service/ingest_service.py` | 加 `load_entry_summaries_by_file_ids(file_ids)`（现有 by-entry_id 版的兄弟，`WHERE file_id IN`；返回结构 `{file_id, title, summary}` 不变） |
| `file_registry/application/service/file_registry_service.py` | 加 `list_files_for_chat(company_ids, thread_id, is_company_end, name_keyword, limit)` → 返回 DTO |
| `file_registry/domain/repository/file_registry_repository.py` | 加 `list_chat_scope_files(...)`：`ai_file_registry ⨝ files` 拿文件名，镜像 5.1 谓词，`status IN (SUCCESS, PARTIAL)` 只列可召回文件，按 `created_at` 倒序 |
| `ai/tools/dto/file_summary_result.py` | 基本不变（summaries 结构沿用） |
| `prompts/chatbot/retrieval_agent_prompt.py` | 教何时圈文件、指代 vs 文件名两条路径、多候选消歧 / 找不到如实告知 |
| `prompts/chatbot/retrieval_kb_agent_prompt.py` | 同上（kb 轨） |

### 无需 DDL/迁移
recall 的 `file_ids` 过滤、`ai_file_registry` 的 `company_id`/`thread_id`/`status`、`ai_rag_entry` 的 `file_id`/`summary` 全已就位（V017 已放开 `ai_rag_entry.company_id` NOT NULL）。

## 七、图接线范围

- **standard**：全上（find_files + search file_ids + get_file_summary）。
- **kb**：kb 图 `retrieve_kb` 目前仅绑 `search_knowledge_base` → 加绑 `find_files` + `get_file_summary`（纯知识库亦应能圈文件）。
- **combo**：kb 段 / business 段分别复用上面两图节点，自动继承，无需单独改。

## 八、跨模块边界

- `find_files`（ai 域工具）调 `file_registry` 的 `application/service`（`list_files_for_chat`）——符合 architecture §2.1「只 import 对方 application/service」；**不** import 其 domain。
- `get_file_summary` 调 rag `ingest_service`（既有例外，§5 登记例外）。
- 三工具同步 DB 读一律 `asyncio.to_thread` 下线程，不挡 SSE 事件循环。

## 九、测试点（tests/，全 mock LLM/rag）

- **find_files 作用域**：公司端只出本公司 APP；管理端出可访问公司 + 本 thread session、**不出别 thread 的 session**；`name_hint` 模糊；recency 倒序；`status` 过滤未就绪文件。
- **get_file_summary 越权（安全回归）**：传别公司 file_id → 被作用域交集滤掉 → 返回空。
- **search_knowledge_base(file_ids)**：传越权 id → 召回空（自动安全）；传合法 id → 收窄到该文件片段。
- **turn_entry_ids 退役后**：`get_file_summary(file_ids)` 正常取摘要；两处 build_req_ctx 不再投影该字段。
- **注入探针**：增删工具后用 `tool_call_schema` 验证 find_files 入参进 schema、runtime 不进 schema。

## 十、边界与风险

- **就绪**：圈到的历史文件已向量化（有 chunk / summary）；本轮刚传文件走 file_gate 就绪门控（不变）。find_files 用 `status IN (SUCCESS, PARTIAL)` 过滤，未就绪不列。
- **+1 跳**（D2 已接受）：总结常见场景多一次 find_files 调用；若后续觉慢，可加「file_ids 省略时服务端按本会话 recency 兜底」的增量（不复活 turn_entry_ids）。
- **多候选消歧**：管理端跨公司同名文件靠候选带 `company` 标识，模型据此让用户确认。

## 十一、开放点

1. `find_files` 的 `name_hint` 模糊匹配用简单 `ILIKE %kw%` 还是 trigram/RapidFuzz？初版建议 `ILIKE`（登记行文件名量级小、由模型二次比对），需要再升级。
2. `limit` 上限与默认值（暂定默认 10 / 最大 20），按实际会话文件规模调。
