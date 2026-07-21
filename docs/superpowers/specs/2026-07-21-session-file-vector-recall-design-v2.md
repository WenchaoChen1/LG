# 会话文件向量召回（管理端未选公司）设计 · v2

> 关联文档：取代 `2026-07-21-session-file-vector-recall-design.md`（旧版方案 P2「哨兵 space + 结构性隔离」错误严重，**作废、勿参考**）。

- 日期：2026-07-21
- 状态：设计已对齐 —— **Stage 1 锁定**；**Stage 2 待细化**（召回/清理细节下一轮讨论）
- 范围：`CIOaas-python`（rag：会话 space 归属 + 入库向量化 + chunk 冗余列；chatbot：附件编排 + file_gate + 召回；lg.db：会话登记状态机 / 清理）
- 前提：**测试阶段，不考虑存量兼容**（组合键改动会改变既有关联行 id；现有 `ai_rag_business_association` 中 `business_type=KNOWLEDGE_BASE` 为历史错误数据，直接纠正 / 忽略）

---

## 一、背景与目标

管理端发消息**未选归属公司**的文件 = **会话作用域文件（session file）**。现状：`chat_attachment_service._attach_session_files` 只经 `register_session_file` 登记元数据（`ai_file_registry`，`business_type=SESSION_UPLOAD`、`company_id=NULL`），**不建 space/entry、不向量化、不入 chunk**，问答时即时抽全文直注。

目标：**会话文件也向量化入库（真 space + 真 entry + 真 chunk），支持按会话相似度召回，且会话之间隔离。**

---

## 二、核心决策（锁定）

### 2.1 space 归属：复用 `business_association`，business_type 跟端走

组合键 `(end_type, business_type, company_id, user_id, organization_id)`（uuid5 派生，同组合恒同 id）。三场景取值：

| 场景 | end_type | business_type | company_id | user_id | organization_id | space |
|---|---|---|---|---|---|---|
| ① APP | `APP` | `APP_COMPANY` | 公司 | 空 | 空 | 每公司一个 |
| ② ADMIN KB（本轮绑定公司） | `ADMIN` | `ADMIN_COMPANY` | 空串 | 空 | 组织 | 每组织一个 |
| ③ ADMIN 会话（本轮未绑定公司） | `ADMIN` | `ADMIN_COMPANY` | 空串 | 空 | 组织 | **与②同一个** |

- **business_type 只用 `APP_COMPANY`（APP 端）/ `ADMIN_COMPANY`（ADMIN 端），跟 end_type 走**——不用 KNOWLEDGE_BASE / ADMIN_ORGANIZATION / ADMIN_THREAD。**现有 `ai_rag_business_association` 里 `business_type=KNOWLEDGE_BASE` 是历史错误数据**，测试阶段直接纠正 / 忽略（存量不管）。
- 规律：`company_id` **仅 APP 进**、`organization_id` **仅 ADMIN 进**（APP=按公司、ADMIN=按组织，二选一进组合键）；`user_id` / `thread_id` 都不进。
- **②③ 组合键相同 → 合并为同一个 space**：管理端**每组织只有一个 space**，同时装「绑定公司的 KB 文件」（chunk `company_id` 有值）和「会话文件」（chunk `company_id` 为 NULL + `thread_id` + `created_by`）。KB / 会话**不靠 business_type 或 space 区分，全靠 chunk 列**。
- 只有 APP 端仍是「每公司一个 space」（`company_id` 进组合）。

### 2.2 space 粒度

- **APP**：每公司一个（`company_id` 进组合）。
- **ADMIN**：**每组织一个**（KB + 会话合并在同一个 space）。
- space 由 `_build_kb_space` 构造（`process_type=STANDARD` / `business_type=enterprise_kb`，普通 uuid），命名如 `Admin {org}`。

### 2.3 会话文件建**真** `ai_rag_entry` + **真** chunk

- 走与 KB 同一套 ingest（`ingest_kb_file` 建 entry → 向量化 → 写 `ai_rag_ent_kb_chunk`）。
- 会话文件因此会出现在文档管理页（可接受，见 2.4）。

### 2.4 隔离与召回作用域

- **隔离全在 chatbot tool 召回时按 chunk 列做**；管理面（devSupport rag：空间列表 / 召回测试 / 文档页）**照常显示所有文件、不堵漏**（已确认），故不加判别列、不改全局枚举。
- **召回作用域**：
  - **公司端 ①**：`space_id=<该公司 APP space>`（该公司 KB）。
  - **管理端（②③ 混合，无「选公司」功能、召回全部有权限公司）**：
    ```
    space_id = <本组织 ADMIN space>
    AND ( company_id IN (:可访问公司集)                                   -- KB（全部有权限公司）
          OR  thread_id = :t )  -- 会话（本会话 ）
    ```
- **Q2a**（管理端连该公司 **APP 端** KB 一起召）：理论可行，**目前不做**。
- 注意：KB 与会话现在**同 business_type（ADMIN_COMPANY）、同 space**，不再有「business_type 天然分离」；两者区分**唯一靠 chunk `company_id`（有值=KB / NULL=会话）**。

### 2.5 chunk 冗余列（已落地）

`ai_rag_ent_kb_chunk` 已加 8 列（`vector/V003`）：`file_registry_id / end_type / business_type / thread_id / message_id / organization_id / company_id / created_by`。**区分键**：`company_id` 有值=KB、`NULL`=会话；会话再用 `thread_id` + `created_by` 收窄。入库后由 stamp 回填（见 Stage 1）。

---

## 三、Stage 1（锁定）：会话文件入 space / entry / chunk

| # | 文件 | 改动 |
|---|---|---|
| S1 | `rag/application/service/business_association_service.py` | 组合键 business_type 改 `APP_COMPANY`/`ADMIN_COMPANY`、**补传 `organization_id`**、ADMIN 去掉 `company_id`；ADMIN KB 与会话**共用** `(ADMIN, ADMIN_COMPANY, "", org)` 一个 space（find-or-create，会话不单独建 space） |
| S2 | `chatbot/application/service/chat_attachment_service.py` | `_attach_session_files` 从「只登记」改为「**ensure 组织 ADMIN space → `ingest_kb_file` 建真 entry → 向量化入 chunk → register(带 space/entry/thread/message，company_id 空) → start_vectorization**」 |
| S3 | `rag/application/service/ingest_service.py` + `lg/db/service/file_registry.py` | **chunk stamp 扩到会话**：现回填按 KB 登记行经 entry 反查；会话登记行也要被 stamp 认出，把 `thread_id`/`created_by`/`company_id=NULL`/`end_type=ADMIN` 填进会话 chunk（`company_id` 空是 KB / 会话的区分键） |
| S4 | `lg/db/service/file_registry.py` | 会话登记行补 `space_id`/`ai_rag_entry_id` 关联 + **状态机**（`PROCESSING → SUCCESS/FAILED`），供 file_gate 就绪等待 |

---

## 四、Stage 2（待细化 · 下一轮讨论）

| # | 文件 | 方向（细节 TBD） |
|---|---|---|
| S5 | `ai/tools/knowledge_base_tool.py`（召回作用域）+ `file_gate_node.py` | 召回作用域改为 2.4 口径：公司端 = 该公司 space；管理端 = 本组织 ADMIN space + `(company_id IN 可访问集 OR thread )` 混合；会话就绪等待 |
| S6 | `chatbot/application/service/chat_history_service.py` | thread 软删联动：按 `thread_id` 删会话 chunk |

> Stage 2 的召回口径（是否仍保留 summarize 直注、就绪等待机制、清理事务边界、HNSW 列索引等）在下一轮敲定。

---

## 五、关键取舍

- **复用 `business_association` + KB ingest 机器**，最小化重复；business_type 跟端走（`APP_COMPANY`/`ADMIN_COMPANY`），KB 与会话同 space、靠 chunk `company_id` 区分。
- **隔离只有一层**：chatbot tool 召回时按 chunk 列过滤（KB=`company_id IN 可访问集`；会话= thread ）。管理面**不隔离**（可见）。
- **ADMIN 每组织一个 space**：space/关联行数量少；公司 / 会话 / 上传者的区分全部下沉到 chunk 列。
