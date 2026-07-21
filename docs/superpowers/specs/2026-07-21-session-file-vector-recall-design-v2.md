# 会话文件向量召回（管理端未选公司）设计

> 取代 `2026-07-21-session-file-vector-recall-design.md`（旧版方案 P2「哨兵 space + 结构性隔离」错误严重，**作废、勿参考**）。本文**合并**原 v2 总设计 + Stage 1/2/3 三份分档为单一文档。

- 日期：2026-07-21
- 状态：**Stage 1 入库 / Stage 2 召回 已实现（另一进程）；Stage 3 文件总结工具化 待实现**
- 范围：`CIOaas-python`（rag：space 归属 + 入库向量化 + chunk 冗余列 + 召回过滤；chatbot：附件编排 + file_gate + tool 召回/摘要；lg.db：会话登记状态机）
- 前提：**测试阶段、不考虑存量兼容**（组合键改动会改变既有关联行 id；现有 `ai_rag_business_association` 中 `business_type=KNOWLEDGE_BASE` 为历史错误数据，直接纠正 / 忽略）

---

## 一、背景与目标

管理端发消息**未选归属公司**的文件 = **会话作用域文件（session file）**。原现状：只登记元数据（`ai_file_registry`，`company_id=NULL`），**不建 space/entry、不向量化**，问答时即时抽全文直注。

目标：**会话文件也向量化入库（真 space + 真 entry + 真 chunk），支持按会话相似度召回与总结，且会话之间隔离。**

---

## 二、核心决策

### 2.1 space 归属：复用 `business_association`，business_type 跟端走

组合键 `(end_type, business_type, company_id, user_id, organization_id)`（uuid5 派生，同组合恒同 id）。三场景取值：

| 场景 | end_type | business_type | company_id | user_id | organization_id | space |
|---|---|---|---|---|---|---|
| ① APP | `APP` | `APP_COMPANY` | 公司 | 空 | 空 | 每公司一个 |
| ② ADMIN KB（本轮绑定公司） | `ADMIN` | `ADMIN_COMPANY` | 空串 | 空 | 组织 | 每组织一个 |
| ③ ADMIN 会话（本轮未绑定公司） | `ADMIN` | `ADMIN_COMPANY` | 空串 | 空 | 组织 | **与②同一个** |

- **business_type 只用 `APP_COMPANY`（APP 端）/ `ADMIN_COMPANY`（ADMIN 端），跟 end_type 走**——不用 KNOWLEDGE_BASE / ADMIN_ORGANIZATION / ADMIN_THREAD。现有 `ai_rag_business_association` 里 `business_type=KNOWLEDGE_BASE` 是历史错误数据（测试阶段纠正/忽略）。
- 规律：`company_id` **仅 APP 进**、`organization_id` **仅 ADMIN 进**（APP=按公司、ADMIN=按组织，二选一进组合键）；`user_id` / `thread_id` 不进。
- **②③ 组合键相同 → 合并为同一个 space**：管理端**每组织只有一个 space**，同时装「绑定公司的 KB 文件」（chunk `company_id` 有值）和「会话文件」（chunk `company_id` 为 NULL）。KB / 会话**不靠 business_type 或 space 区分，全靠 chunk 列**。
- 只有 APP 端仍是「每公司一个 space」。

### 2.2 space 粒度

- **APP**：每公司一个（`company_id` 进组合）。
- **ADMIN**：**每组织一个**（KB + 会话合并在同一个 space）。
- space 由 `_build_kb_space` 构造（`process_type=STANDARD` / `business_type=enterprise_kb`，普通 uuid），命名如 `Admin {org}` / `App {company}`。

### 2.3 会话文件建**真** `ai_rag_entry` + **真** chunk

- 走与 KB 同一套 ingest（`ingest_kb_file` 建 entry → 向量化 → 写 `ai_rag_ent_kb_chunk`）。
- 会话文件因此会出现在文档管理页（可接受，见 2.4）。

### 2.4 隔离与召回作用域

- **隔离全在 chatbot tool 召回时按 chunk 列做**；管理面（devSupport rag：空间列表 / 召回测试 / 文档页）**照常显示所有文件、不堵漏**（已确认），故不加判别列、不改全局枚举。
- **召回作用域**：
  - **公司端 ①**：`space_id = <该公司 APP space>`（该公司 KB）。
  - **管理端（②③ 混合，无「选公司」功能、召回全部有权限公司）**：
    ```
    space_id = <本组织 ADMIN space>
    AND ( company_id IN (:可访问公司集)   -- KB（全部有权限公司）
          OR thread_id = :t )              -- 会话（本会话）
    ```
- 会话隔离到**会话级**（`thread_id`），不按 `created_by` / `company_id IS NULL` 收窄。
- **Q2a**（管理端连该公司 **APP 端** KB 一起召）：理论可行，**目前不做**。

### 2.5 chunk 冗余列（已落地）

`ai_rag_ent_kb_chunk` 已加 8 列（`vector/V003`）：`file_registry_id / end_type / business_type / thread_id / message_id / organization_id / company_id / created_by`。**区分键**：`company_id` 有值=KB、`NULL`=会话。入库后由 stamp 回填（见 Stage 1）。

### 2.6 ⚠️ 两个 `business_type` 概念，别混

| 列 | 取值 | 用途 |
|---|---|---|
| `ai_rag_business_association.business_type`（**space 组合键**） | `APP_COMPANY` / `ADMIN_COMPANY` | 决定文件落哪个 space |
| `ai_file_registry.business_type`（+ chunk 镜像列） | KB=`KNOWLEDGE_BASE` / 会话=`SESSION_UPLOAD`（**不变**） | 登记行 / chunk 的来源标记 |

召回区分 KB / 会话靠 chunk `company_id`，**不靠任何 business_type**。

---

## 三、Stage 1：会话文件入 space / entry / chunk（**已实现**）

| # | 文件 | 改动 |
|---|---|---|
| S1 | `rag/.../business_association_service.py` | `ensure` 加 `organization_id`；组合键 business_type 跟端走（`APP_COMPANY`/`ADMIN_COMPANY`）、ADMIN 去 `company_id`；ADMIN KB 与会话**共用** `(ADMIN, ADMIN_COMPANY, "", org)` 一个 space（find-or-create，会话不单独建） |
| S2 | `chatbot/.../chat_attachment_service.py` | 两分支**统一**为 `ensure space → ingest_kb_file(真 entry) → register → start_vectorization`；`attach_files_to_message` 加 `organization_id`。差异仅 `company_id`（会话=None）与登记函数（会话 `register_session_file`、`business_type=SESSION_UPLOAD`、company 空） |
| S3 | （基本复用）`ingest_service` / `file_registry.get_kb_registry_stamp_by_entry` | stamp 按 `ai_rag_entry_id` 反查登记行、**不筛 business_type** → 会话登记行（S4 带 entry_id）天然被覆盖，把 `company_id=NULL`/`thread_id`/`created_by`/`org`/`end_type` 回填进会话 chunk。无需额外改 |
| S4 | `lg/db/service/file_registry.py` | `register_session_file` 加 `space_id`/`ai_rag_entry_id`/`organization_id` + 状态机 `PROCESSING → SUCCESS/FAILED`（供 file_gate 就绪等待）；维持 `company_id=NULL` |

**会话文件端到端数据流**：
```
上传（管理端未选公司, end=ADMIN）
 → attach_files_to_message(company_id=None, end=ADMIN, org)
 → ensure(ADMIN, ADMIN_COMPANY, "", org) space
 → ingest_kb_file → ai_rag_entry（真 entry）
 → register_session_file(space/entry/org, PROCESSING)
 → start_vectorization → ingest_pipeline：vectorize + store → ai_rag_ent_kb_chunk
 → stamp：回填 company_id=NULL / thread_id / created_by / org / end_type
 → update_status_by_entry → 登记行 SUCCESS
```

---

## 四、Stage 2：召回（**已实现**，落在 `search_knowledge_base_tool`）

- **召回作用域解析 + 过滤全在 tool 内**；**单趟召回、纯相似度**（已去掉 `thread_file_ids` 两趟优先逻辑）。
- **场景判定**（从 `ReqCtx`）：`ctx.home_company_id` 非空 = 公司端①；否则 = 管理端（②③混合）。
- **目标 space**（组合键算确定性 id → 取挂接 STANDARD space）：① `(APP, APP_COMPANY, home_company_id, "", "")`；管理端 `(ADMIN, ADMIN_COMPANY, "", "", org)`。space 不存在 / 管理端无 org → 空作用域返回无结果。
- **召回过滤**（叠在向量/关键词之上）：① `space_id=<公司 space>`（无列过滤）；管理端 `space_id=<组织 ADMIN space> AND (company_id IN (:ctx.allowed) OR thread_id = :ctx.thread_id)`。

| # | 文件 | 改动 |
|---|---|---|
| R1 | `ai/tools/knowledge_base_tool.py` | 场景判定 + 组合键算 space + 拼过滤；删两趟 `thread_file_ids` 逻辑，单趟召回 |
| R2 | `rag/.../search_service.py` | `recall`/`recall_by_spaces` 加 `company_ids`/`thread_id` 过滤入参并透传 |
| R3 | `rag/domain/repository/chunk_repository.py` | `search_vector_single_space`/`search_keyword_single_space` 加列过滤，拼析取 `(company_id IN OR thread_id =)` |
| R4 | `ai/tools/_support/kb_scope.py` | 按组合键 `business_association_space_id` 解析目标 space（替代原查 ai_file_registry 圈 space） |
| R5 | `ai/agent/.../file_gate_node.py` | 会话 qa 就绪等待后 `file_scope="thread"` → 走召回（不置 `file_source="session"`） |
| （前置） | `ReqCtx.thread_id` | 已加并注入（standard/kb 两取数节点） |

---

## 五、Stage 3：文件总结工具化（**待实现**）

**问题**：文件总结仍是 `file_gate`「haiku 判 summarize → 抽内容直注」的特殊路径，与 qa（工具）两套机制；会话总结仍即时抽全文（`extract_session_file_text` 截 20000），没用上会话已生成的 `entry.summary`。

**目标**：把「获取文件摘要」做成**工具**，与 `search_knowledge_base` 并列；退役 file_gate summarize 直注，KB/会话统一。

- **新工具 `get_file_summary`**：按作用域返回 `[{file_id, title, summary}]`，summary = **`entry.summary`**（空退 `content_text` 预览），**不做 top-N chunk 升级**（已定）；**不做相似度召回**。入参不含 file_id（作用域从 ctx 取），绑定 standard/kb/combo 取数节点，模型按问题自选（总结→本工具、问某点→search）。
- **作用域**：`file_gate` 把**本轮上传文件** id 注入 `ReqCtx`（新字段 `turn_file_ids`/`turn_entry_ids`）；工具默认总结本轮上传。
- **就绪等待**：保留在 `file_gate`（`await_entries_ready`；传完即问时 entry.summary 异步生成，就绪后模型再调工具）。
- **file_gate 瘦身**：删 summarize 直注 / `extract_session_file_text` / `file_source="session"` / `_file_directive` summarize·session 段；保留就绪 + ctx 注入；summarize/qa 意图二分不再需要（模型选工具），`need_file` 门建议保留（延迟优化）。

| # | 文件 | 改动 |
|---|---|---|
| T1 | `ai/tools/file_summary_tool.py`（新增） | `get_file_summary`：按 ctx 本轮文件取 `entry.summary`；typed 返回 + `metadata` |
| T2 | `ai/agent/chatbot_graph/tools.py` | 注册进 `TOOL_REGISTRY_V2` |
| T3 | `ai/tools/_support/request_context.py` | `ReqCtx` 加 `turn_file_ids`/`turn_entry_ids` |
| T4 | `retrieval_agent.build_req_ctx` + `retrieval_kb_agent` | 注入本轮文件字段 |
| T5 | `ai/agent/.../file_gate_node.py` | 瘦身（删 summarize 直注 / session 分支；保留就绪 + ctx 注入） |
| T6 | `ai/agent/.../retrieval_agent.py` `_file_directive` | 删 summarize/session 段 |
| T7 | （退役）`rag/.../session_file_extract.py` | 无其它调用方则删除 |

**已定**：#2 摘要源 = `entry.summary`（不升级 top-N chunk，接受偏短）；#3 就绪等待留 `file_gate`。

---

## 六、关键取舍

- **复用 `business_association` + KB ingest 机器**，最小化重复；business_type 跟端走，KB 与会话同 space、靠 chunk `company_id` 区分。
- **隔离只有一层**：chatbot tool 召回时按 chunk 列过滤（KB=`company_id IN 可访问集`；会话=`thread_id`）。管理面**不隔离**（可见）。
- **ADMIN 每组织一个 space**：space/关联行数量少；公司 / 会话的区分下沉到 chunk 列。
- **总结工具化**：qa=`search_knowledge_base`（片段召回）、summarize=`get_file_summary`（整篇摘要），模型自选，退役 file_gate 直注特判。

---

## 七、开放点 / 风险

1. **HNSW 效率**：`space_id` 主过滤命中 HNSW；叠 `company_id IN` / `thread_id` 属带过滤向量检索，需评估是否给 `ai_rag_ent_kb_chunk(company_id)` / `(thread_id)` 建配套列索引。
2. **管理端无 org**：`organization_id` 为空 → 无目标 space → 召回空。需确认管理端 ctx 恒有 org。
3. **`resolve_kb_space_ids` 存废**：改用组合键解析后，原按 ai_file_registry 圈 space 的路径（含 `list_kb_space_ids`）在 chatbot 召回中不再使用；是否保留给其它调用方待核。
4. **`need_file` 门去留**（Stage 3）：保留=省"传文件却问无关"时就绪等待延迟；建议保留。
5. **历史轮文件总结**：默认只总结本轮上传；"总结本会话所有传过的文件"需求若有，工具作用域按 thread 扩。
6. **摘要偏短（已接受）**：`entry.summary` ~200 字，"总结"≈复述短摘要；已定不升级。

---

## 八、已落地的零星前置代码（未提交）

- `ReqCtx.thread_id`（Stage 2 前置）：`request_context.py` + `retrieval_agent`/`retrieval_kb_agent` 注入。
- `business_association_service.py` L41-42：`_BIZ_TYPE_*` 改引 `ASSOCIATION_BUSINESS_TYPE_SEEDS[...].code`（防漂移）。
