# 会话文件向量召回 · Stage 1 开发设计（入 space / entry / chunk）

> 关联文档：总设计见 `2026-07-21-session-file-vector-recall-design-v2.md`。本文只细化 **Stage 1** 的落地实现（S1–S4），召回/清理（Stage 2）不在此。

- 日期：2026-07-21
- 状态：开发设计待评审
- 范围：`CIOaas-python`（rag `business_association_service` / `ingest_service`；chatbot `chat_attachment_service` / `sse_provider`；lg.db `file_registry`）
- 前提：测试阶段、不考虑存量兼容。

---

## 〇、前置澄清：**两个 `business_type` 概念，别混**

| 列 | 取值 | 用途 |
|---|---|---|
| `ai_rag_business_association.business_type`（**space 组合键**） | `APP_COMPANY` / `ADMIN_COMPANY` | 决定文件落哪个 space（本次改这个） |
| `ai_file_registry.business_type`（+ chunk 镜像列） | KB=`KNOWLEDGE_BASE` / 会话=`SESSION_UPLOAD`（**不变**） | 登记行/chunk 的来源标记 |

- **召回（Stage 2）区分 KB / 会话靠 chunk `company_id`（有值=KB / NULL=会话），不靠任何 business_type。**
- 本 Stage 只改**关联表**的 business_type（组合键）；登记表 business_type 维持现状。

---

## S1 — `business_association_service`：组合键改造 + 统一 ensure

**现状**：`ensure_kb_space(company_id, end_type, user_id)` 构造 DTO `(end_type, KNOWLEDGE_BASE, company_id, user_id=None, org=None)` → find-or-create。

**改为**：
1. `ensure` 增加入参 `organization_id`（仅 ADMIN 组合键用；APP 不含 org，见 v2 §2.1 表）。
2. 组合键按端拼：
   - `APP`  → `(APP,  APP_COMPANY,  company_id, "", "")`（**org 不进组合**，靠 company_id 每公司一个）
   - `ADMIN`→ `(ADMIN, ADMIN_COMPANY, "",        "", org)`（**company_id 不进组合**）
3. 因此 **ADMIN KB（有 company）与会话（无 company）解析到同一个** `(ADMIN, ADMIN_COMPANY, "", org)` space —— 会话不单独建 space。
4. `_build_kb_space` 命名：`App {company}` / `Admin {org}`。

**签名（建议）**：`ensure_chat_space(*, end_type, organization_id, company_id=None, user_id)`（保留 `ensure_kb_space` 名亦可）。`company_id` 仅 APP 端用于组合键；ADMIN 端忽略。

---

## S2 — `chat_attachment_service`：两分支统一走 ingest

**现状**：`attach_files_to_message` 分两支——有 company 走 KB ingest；无 company 走 `_attach_session_files`（只登记、不建 entry/space、不向量化）。

**改为**：**两支统一**为同一序列（会话不再是"只登记"）：

```
ensure_chat_space(end_type, org, company_id) → space_id
  → ingest_kb_file(space_id, file, thread, company_id, user)  → entry_id   （建真 entry）
  → register(file, space_id, entry_id, org, thread, message, company_id)   （登记行）
  → start_vectorization(entry_id)                                          （投递）
```

差异仅两处：
- `company_id`：KB=公司；会话=`None`。
- 登记函数：KB=`register_message_file`（登记 business_type=KNOWLEDGE_BASE）；会话=`register_session_file`（business_type=SESSION_UPLOAD，company 空）。

`attach_files_to_message` 新增入参 `organization_id`，透传给 ensure 与 register。

---

## S3 — chunk stamp：**基本复用，无需新代码**

- 现有 `file_registry.get_kb_registry_stamp_by_entry(entry_id)` 按 `ai_rag_entry_id` 查登记行、**不筛 business_type**；`ingest_service.stamp_kb_registry_columns` 在 `ingest_pipeline` 向量化成功后调用。
- 只要 **S4 让会话登记行带上 `ai_rag_entry_id`**，会话文件走同一 ingest pipeline → stamp 自动命中会话登记行 → 把 `company_id=NULL` / `thread_id` / `created_by` / `organization_id` / `end_type=ADMIN` 等回填进会话 chunk。
- **区分键 `company_id`（会话为 NULL）天然落位**，Stage 2 召回即可用。
- 结论：S3 无需额外改动（前提是 S4 完成）。

---

## S4 — `register_session_file` 扩展

**现状**：`register_session_file(file_id, user_id, end_type, thread_id, message_id)` → 写登记行（`SESSION_UPLOAD`、company_id NULL、无 space/entry、status 固定）。

**改为**新增入参并落列 + 状态机：
- 加 `space_id` / `ai_rag_entry_id` / `organization_id`。
- `status` 初始 `PROCESSING`；向量化终态由现有 `update_status_by_entry`（rag 流水线回写）镜像成 `SUCCESS`/`FAILED`。
- 维持 `business_type=SESSION_UPLOAD`、`company_id=NULL`（KB / 会话的区分键）。

---

## org 来源

`sse_provider.stream_turn` 侧已有 `organization_id`（身份解析结果）；沿调用链透传：`stream_turn → attach_files_to_message(organization_id=…) → ensure_chat_space / register_*`。**需确认管理端 ctx 一定能拿到 org**（见开放点）。

---

## 会话文件端到端数据流（改造后）

```
上传（管理端未选公司, end=ADMIN）
 → attach_files_to_message(company_id=None, end=ADMIN, org)
 → ensure_chat_space(ADMIN, org, company_id=None) → (ADMIN, ADMIN_COMPANY, "", org) space
 → ingest_kb_file → ai_rag_entry（真 entry）
 → register_session_file(space_id, ai_rag_entry_id, org, thread, message, PROCESSING)
 → start_vectorization → ingest_pipeline：vectorize + store → ai_rag_ent_kb_chunk（新行）
 → stamp_kb_registry_columns：按 entry 反查会话登记行 → 回填 company_id=NULL / thread_id / created_by / org / end_type
 → update_status_by_entry → 登记行 SUCCESS
```

---

## 待实现清单（文件）

| # | 文件 | 改动 |
|---|---|---|
| S1 | `rag/application/service/business_association_service.py` | ensure 加 `organization_id`、组合键 business_type→APP_COMPANY/ADMIN_COMPANY、ADMIN 去 company_id；`_build_kb_space` 命名 |
| S2 | `chatbot/application/service/chat_attachment_service.py` | 合并两分支为统一 ingest 序列；`attach_files_to_message` 加 `organization_id` |
| S2' | `chatbot/application/sse_provider.py` | `stream_turn` 透传 `organization_id` 给 attach |
| S4 | `lg/db/service/file_registry.py` | `register_session_file` 加 space_id/ai_rag_entry_id/organization_id + status PROCESSING |
| S3 | （复用）`ingest_service` / `file_registry.get_kb_registry_stamp_by_entry` | 无需改（前提 S4） |

---

## 开放点 / 风险

1. **org 可得性**：管理端会话上传时 `ctx.organization_id` 是否恒有值？为空则组合键 org 空串 → 全 org 落同一 space（需确认可接受）。
2. **登记函数是否合并**：`register_session_file` 与 `register_message_file` 目前分开；本设计维持分开（差异=company/business_type）。若后续想合并再议。
3. **现有 KB 关联行作废**：组合键 business_type 从 KNOWLEDGE_BASE 改为 APP_COMPANY/ADMIN_COMPANY 后，既有关联行 id 全变；测试阶段直接忽略，新上传建新关联。
4. **`ingest_kb_file` 对会话文件的适配**：确认其入参（space_id/company_id/thread 等）对 company_id=None 场景无强依赖（实现时核对）。
