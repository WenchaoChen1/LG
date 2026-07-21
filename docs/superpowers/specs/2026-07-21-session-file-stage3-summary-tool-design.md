# 会话文件向量召回 · Stage 3 文件总结工具化设计

> 关联文档：总设计 `2026-07-21-session-file-vector-recall-design-v2.md`；Stage 1 入库 `...-stage1-dev-design.md`；Stage 2 召回 `...-stage2-recall-design.md`。本文细化 **文件总结（summarize）工具化**。

- 日期：2026-07-21
- 状态：设计待评审（编码由另一进程执行）
- 范围：`CIOaas-python`（ai `tools/` 新增摘要工具 + 三图取数节点绑定；chatbot `file_gate` 瘦身；退役 `session_file_extract` / `_file_directive` summarize 分支）

---

## 一、背景与目标

**问题**：Stage 1/2 后，文件总结仍是 `file_gate` 里「haiku 判 summarize 意图 → 抽内容直注提示词」的特殊路径，和 qa（`search_knowledge_base` 工具）**两套机制**，且：
- KB 总结用 `entry.summary`；**会话总结仍即时抽全文（`extract_session_file_text`，截 20000）**、不一致、且没用上 Stage 1 已生成的会话 `entry.summary`；
- 带来 `_file_directive` summarize/session 分支、`file_source="session"` 直注禁工具等一堆特判。

**目标**：把「获取文件摘要」做成**工具**，与 `search_knowledge_base` 并列；退役 file_gate 的 summarize 直注，KB/会话统一。

---

## 二、新工具 `get_file_summary`

- **职责**：按作用域返回文件整篇摘要（**不做相似度召回**——那是 `search_knowledge_base` 的事）。
- **返回**：`[{file_id, title, summary}]`。summary = **`entry.summary`**（入库时对全文生成），空则退 `content_text` 预览。**不做 top-N chunk 升级**（已定）。
- **入参**：无需 LLM 传 file_id（一致于「工具不让 LLM 编 UUID」原则）——作用域从 `ctx` 取（见三）。
- **绑定**：standard `retrieve` + kb `retrieve_kb`（+ combo 两段），与 `search_knowledge_base` 同列，模型按问题自选（"总结" → 本工具；"问某点" → search）。

---

## 三、作用域（从 `ctx`，不经 LLM）

- `file_gate` 把**本轮上传文件**的标识（`file_id` / `entry_id`）注入 `ReqCtx`（新增字段，如 `ctx.turn_file_ids` / `ctx.turn_entry_ids`）。
- `get_file_summary` **默认总结本轮上传的文件**（"总结我刚传的" 命中）。历史轮文件的总结需求少，若要再按 thread 扩。
- 与 `search_knowledge_base` 的 ctx 作用域机制一致（都不让 LLM 提供 id）。

---

## 四、就绪等待（保留在 file_gate）【#3 默认】

- 用户「传完即问总结」时 `entry.summary` 异步生成、可能未就绪 → **file_gate 保留 `await_entries_ready`**，就绪后模型再调工具，拿到非空 summary。
- 备选（不采纳）：就绪等待挪进工具——工具变有状态、且每次调用都要等，不如 file_gate 一次性等。

---

## 五、`file_gate` 瘦身

- **删除**：summarize 意图分支的直注（`extract_session_file_text` 循环）、`file_source="session"` 分支、`_file_directive` 的 summarize/session 段。
- **保留**：本轮有附件 → 就绪等待（`await_entries_ready`）+ 把本轮 file/entry id 注入 ctx。
- **意图门**：`summarize`/`qa` 二分**不再需要**（模型按工具选）；`need_file`（问题是否与文件相关，省不必要的就绪等待延迟）**建议保留**（轻量 haiku，纯延迟优化）——见开放点。
- qa 现状（Stage 2：`file_scope="thread"` → `search_knowledge_base` 按 thread 召回）不变。

---

## 六、改动清单

| # | 文件 | 改动 |
|---|---|---|
| T1 | `ai/tools/file_summary_tool.py`（新增） | `get_file_summary`：按 ctx 本轮文件取 `entry.summary`（空退 content_text 预览）；typed 返回 + `metadata`（ui_label / result_model） |
| T2 | `ai/agent/chatbot_graph/tools.py`（`TOOL_REGISTRY_V2`）| 注册新工具 |
| T3 | `ai/tools/_support/request_context.py` | `ReqCtx` 加本轮文件字段（`turn_file_ids` / `turn_entry_ids`） |
| T4 | `retrieval_agent.build_req_ctx` + `retrieval_kb_agent` | 注入本轮文件字段 |
| T5 | `ai/agent/chatbot_graph/nodes/file_gate_node.py` | 瘦身：删 summarize 直注 / session 分支；保留就绪 + ctx 注入；意图门简化 |
| T6 | `ai/agent/.../retrieval_agent.py` `_file_directive` | 删 summarize/session 段（qa 段是否保留见开放点） |
| T7 | （退役）`rag/application/service/session_file_extract.py` | 若无其它调用方则删除；否则停用 |

---

## 七、已定

- **#2 摘要源**：`entry.summary`（空退 `content_text` 预览）。**不做 top-N chunk 升级**——接受摘要偏短。
- **#3 就绪等待**：留在 `file_gate`。

---

## 八、开放点 / 风险

1. **`need_file` 门去留**：保留=省"传文件却问无关"时的就绪等待延迟（值一次 haiku）；去掉=每有附件必等。建议保留。
2. **`_file_directive` qa 段**：Stage 2 后 qa 靠 `file_scope="thread"` + 召回；`_file_directive` 里是否还有 qa 提示需保留，实现时核。
3. **历史轮文件总结**：默认只总结本轮上传；"总结本会话所有传过的文件"需求若存在，工具作用域按 thread 扩。
4. **摘要偏短（已接受）**：`entry.summary` ~200 字，"总结"≈复述短摘要；已定不做 top-N chunk 升级。
5. **`get_file_summary` vs `search_knowledge_base` 职责边界**：前者整篇摘要、后者片段召回；工具 description 要写清让模型正确选择。
