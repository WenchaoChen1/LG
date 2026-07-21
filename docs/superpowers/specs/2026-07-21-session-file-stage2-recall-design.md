# 会话文件向量召回 · Stage 2 召回设计（落在 `search_knowledge_base_tool`）

> 关联文档：总设计 `2026-07-21-session-file-vector-recall-design-v2.md`（§2.4 召回作用域）；Stage 1 入库 `2026-07-21-session-file-stage1-dev-design.md`。本文只细化 **Stage 2 召回**。

- 日期：2026-07-21
- 状态：召回设计已对齐（待实现）
- 范围：`CIOaas-python`（ai `knowledge_base_tool` + `ReqCtx`；rag `search_service.recall` + chunk 仓储；chatbot `file_gate` 就绪等待）
- 前提：测试阶段、不考虑存量。Stage 1（space/entry/chunk 入库）为前置。

---

## 一、目标与总原则

- **召回作用域解析 + 过滤构造全在 `search_knowledge_base_tool` 内**（不放 file_gate、不单独搞 session_recall）。
- **单趟召回、纯相似度**——**去掉 `thread_file_ids`「本轮上传优先」两趟逻辑**（作用域已按 `thread_id` 覆盖本会话全部文件，本轮上传只是子集，优先级不再保留）。
- KB / 会话在同一 ADMIN space 内，靠 chunk 列过滤区分。

---

## 二、场景判定（tool 内，从 `ReqCtx`）

| 判定 | 场景 |
|---|---|
| `ctx.home_company_id` 非空（公司端 / end=company） | ① 公司端 |
| 否则（管理端 / end=admin） | 管理端（②③ 混合，一次召回） |

---

## 三、目标 space 解析（组合键 → space_id）

tool 用 `business_association_space_id` 算确定性 id → 取该关联挂接的 STANDARD space：

| 场景 | 组合键 |
|---|---|
| ① 公司端 | `(APP, APP_COMPANY, home_company_id, "", "")` |
| 管理端 | `(ADMIN, ADMIN_COMPANY, "", "", organization_id)` |

- space 不存在（从没传过文件）→ 空作用域、返回无结果（`empty_scope_ok`）。
- 管理端无 `organization_id` → 空作用域（记日志），不召回（见开放点）。

---

## 四、召回过滤

| 场景 | 过滤 WHERE（叠在向量 / 关键词之上） |
|---|---|
| ① 公司端 | `space_id = <该公司 space>`（无额外列过滤——整公司 KB） |
| 管理端 | `space_id = <本组织 ADMIN space> AND ( company_id IN (:ctx.allowed) OR thread_id = :ctx.thread_id )` |

- 管理端一次召回 = 全部有权限公司的 KB（`company_id IN`）+ 本会话上传的全部文件（`thread_id`，含会话文件与本会话内 KB 文件）。
- 会话隔离到**会话级**（`thread_id`），不再按 `created_by` / `company_id IS NULL` 收窄（对齐 v2 §2.4 最新口径）。

---

## 五、`search_service.recall` 过滤契约扩展

给 `recall` / 底层 chunk 检索加两个可选过滤入参：

- `company_ids: list[str] | None` —— `company_id IN (...)`
- `thread_id: str | None` —— `thread_id = ...`

拼 SQL 规则（叠在 `space_id = :sid` 与向量 / 关键词之上）：

- 两者都为空 → 不加列过滤（**公司端 ①**）。
- 有值 → 拼**析取**：`AND ( company_id IN (:company_ids) OR thread_id = :thread_id )`（缺其一则只留另一支）。

落点：`rag/domain/repository/chunk_repository.py` 的 `search_vector_single_space` / `search_keyword_single_space` 增列过滤入参；`search_service.recall` / `recall_by_spaces` 透传（现有 `file_ids` 过滤保留兼容，但 chatbot 召回不再用它）。

---

## 六、去掉 `thread_file_ids`

- `knowledge_base_tool` 删除「先按 `thread_file_ids` 召回、不足退整库、合并去重」两趟逻辑，改为**单趟**：算 space + 拼上节过滤 → 一次 `recall`。
- `ReqCtx.thread_file_ids` 与 `build_req_ctx` / `retrieval_kb_agent` 的注入**不再服务召回**；可一并清理（若无其它消费者）。`file_gate` 的 `file_scope="thread"` 仅保留「就绪等待」语义（见下）。

---

## 七、就绪等待（file_gate）

会话文件现在要向量化（Stage 1），召回前需就绪：

- `file_gate` 本轮有会话上传且判需文件时，等本轮文件 entry / 登记行状态就绪（复用 KB 的 `await_entries_ready` 或会话登记行状态机 `PROCESSING→SUCCESS`）后再进召回；未就绪进度卡片反馈。
- summarize 直注路径（`extract_session_file_text`）是否保留 / 改走召回：**本 Stage 不改**，维持现状（qa 走召回、summarize 现状），后续单独议。

---

## 八、改动清单

| # | 文件 | 改动 |
|---|---|---|
| R1 | `ai/tools/knowledge_base_tool.py` | 场景判定 + 组合键算 space + 拼过滤（公司端=space；管理端=space + `company_id IN OR thread_id`）；**删两趟 thread_file_ids 逻辑**，单趟召回 |
| R2 | `rag/application/service/search_service.py` | `recall` / `recall_by_spaces` 加 `company_ids` / `thread_id` 过滤入参并透传 |
| R3 | `rag/domain/repository/chunk_repository.py` | `search_vector_single_space` / `search_keyword_single_space` 加 `company_ids` / `thread_id` 列过滤（拼析取 `(company_id IN OR thread_id =)`） |
| R4 | `ai/tools/_support/kb_scope.py` | 现 `resolve_kb_space_ids`（查 ai_file_registry 圈 space）→ 改为按组合键 `business_association_space_id` 解析目标 space（或在 tool 内直接算） |
| R5 | `ai/agent/.../file_gate_node.py` | 会话分支就绪等待（会话文件向量化后才召回）；`thread_file_ids` 注入按 R1 清理 |
| （已完成）| `ReqCtx.thread_id` | Stage 2 前置，已加并注入 |

---

## 九、开放点 / 风险

1. **HNSW 效率**：`space_id` 主过滤命中 HNSW；叠 `company_id IN` / `thread_id` 属带过滤向量检索，需评估是否给 `ai_rag_ent_kb_chunk(company_id)` / `(thread_id)` 建配套索引。
2. **管理端无 org**：`organization_id` 为空时无目标 space → 召回空。需确认管理端 ctx 恒有 org（否则该管理员的会话/KB 召不到）。
3. **`thread_file_ids` 彻底移除 vs 保留字段**：确认无其它消费者后从 `ReqCtx` / 注入点清理；否则保留字段仅停用召回用途。
4. **`resolve_kb_space_ids` 存废**：改用组合键解析后，原按 ai_file_registry 圈 space 的路径（含 `list_kb_space_ids`）在 chatbot 召回中不再使用；是否保留给其它调用方待核。
5. **summarize 直注**：本 Stage 不动；qa 走召回、summarize 维持现状。
