> 关联文档: [知识库问答设计](../superpowers/specs/2026-07-05-chatbot-knowledge-base-qa-design.md) · [AI-Chatbot 设计](./设计/design-doc.md) · 部署 runbook: `CIOaas-api/deploy/upgrade_doc/sprint114/README.md`

# Chatbot 知识库文件链路 — 业务走读（sprint114 终态）

**日期**: 2026-07-19（随代码演进以源码为准）
**范围**: 文件上传→向量化、提问→召回→回答、知识库面板查询、接口与主要业务方法
**读者**: 熟悉业务用（Wenchao）

## 0. 模块分工（一句话版）

| 数据 | 属主模块 | 创建入口 |
|---|---|---|
| 文件字节 + `files` 行 | **Java** storage 域 | 通用直传 presign + verify |
| business association space（业务关联行）+ 挂接空间（`ai_rag_space`） | **rag** `business_association_service` | `ensure_kb_space()`（组合键唯一定位，无则建） |
| 文档条目（`ai_rag_entry`）+ 向量 chunk | **rag** `ingest_service` / `ingest_pipeline` | `ingest_kb_file()` + `start_vectorization()` |
| 登记行（`ai_file_registry`） | **file_registry** 域 | `register_message_file()` |
| 整体编排 + 消息绑定 | **chatbot** | `chat_attachment_service.attach_files_to_message()` |

`ai_file_registry` 是全链路的**登记中枢**：一行 = 一个进入知识库的文件，携带 company / end_type / thread / message / space / entry 六个关联；检索作用域、面板查询都只看它。

## 1. 上传 → 向量化

```
前端 InputBox（选文件）
 └ fileRegistryApi.uploadKnowledgeFiles()            ← 只走 Java，Python 无上传能力
    └ storageService.uploadFile(file,'KNOWLEDGE_BASE')
       ├ POST /api/web/storage/uploads/presign        Java 建 files 行 + 预签名 PUT
       ├ 浏览器直传 S3
       └ POST /api/web/storage/uploads/{id}/verify    Java HeadObject + 魔数校验定稿
    → chip 就绪，持有 fileId（此刻知识库还没有任何数据）

用户点发送 → SSE payload { question, file_ids:[...], file_company_id? }
 │   file_company_id：仅管理端非模拟形态需要（「These files belong to」所选公司）；
 │   公司端/身份模拟恒用身份公司。
 └ chatbot sse_provider.stream_turn()
    ├ chat_history_service.append_message()           落 user 消息
    └ chat_attachment_service.attach_files_to_message()   ← 附件主编排（平铺五步）
       ① _load_file_records()          读共享 files 表（FileRecord 只读映射）取
       │                               文件名/类型/大小——不再经 Java HTTP 重取；
       │                               行不存在 = 无效 fileId，跳过
       ② rag business_association_service.ensure_kb_space(company, end, user)
       │   business association space = 业务关联行，「KNOWLEDGE_BASE + 端(APP/ADMIN) +
       │   公司(+未来维度)」**组合唯一**。有则用、没有自动创建：先按组合精确查
       │   （devSupport 手工配的同组合关联天然被复用），查不到则**经
       │   create_association(auto_create_space=True) 自动创建**（业务关联的唯一
       │   创建入口——关联行组合键 uuid5 id + 一个 STANDARD 空间同事务建成即用；
       │   并发首建靠主键幂等 + 复查复用）。已有关联则从其**多对多**挂接空间中
       │   取第一个 STANDARD 空间；没有则补建空间（普通 uuid）+ add_space 追加挂接
       ③ rag ingest_service.ingest_kb_file()          建 ai_rag_entry(PROCESSING)
       │                               同名/类型不支持 → None 跳过
       ④ file_registry_service.register_message_file()
       │   建 ai_file_registry 登记行：purpose='rag'、business_type=KNOWLEDGE_BASE、
       │   end_type=APP/ADMIN、thread/message/space/entry 一次写全
       ⑤ rag ingest_service.start_vectorization()     投递 run_file_entry
           （**登记落库后才投递**：防流水线终态镜像先于登记行）
    └ chat_history_service.set_message_files()        登记行 id 数组回填消息
                                                      ai_chatbot_message.file_registry_ids

后台 rag ingest_pipeline._process()
 ├ download_ingest_file()   经 Java getFileLinkById 取预签名 URL → httpx 流式下载
 │                          （Python 不直连 S3）
 ├ factory.vectorize_by_space()   load→split→embed→写 ai_rag_ent_kb_chunk + LLM 摘要
 └ finalize_entry()         entry 终态 SUCCESS/PARTIAL/FAILED
    └ lg.db.service.file_registry.update_status_by_entry()
                            终态**镜像回登记行 status**（面板因此不必查 entry）
```

失败语义：逐文件隔离——任一文件元数据缺失/类型不支持/同名/落库异常，只记日志跳过，不影响其余文件与本轮问答。

## 2. 提问 → 召回 → 回答

```
用户提问（standard 轨自动判断，或 /knowledge 强制知识库轨）
 └ retrieval_agent（ReAct）决定调用 search_knowledge_base 工具
    └ ai/tools/knowledge_base_tool.py
       端映射：ReqCtx.end_type company→APP / 其余→ADMIN；company=home_company_id
       （公司端=本公司；管理端身份模拟=被模拟公司；未模拟=空→空作用域）
       └ rag search_service.recall(mode="standard", company_id, end_type, ...)
          ├ 作用域：lg.db.service.file_registry.list_kb_space_ids(company, end)
          │   ← 唯一数据源 = ai_file_registry：该公司该端登记过文件的 space 集合；
          │     没登记过 = 检索不到（empty_scope_ok 返回空结果，不报错）
          ├ 按 STANDARD 过滤 → recall_by_spaces → factory.recalls
          │   （向量路 + 关键词路并发检索，RRF 融合，跨 space 归一合并取 topK）
          └ _record_recall 后台写 ai_rag_search_log + 三级 hit_count
    → 工具返回 hits[].content / similarity / source_title
    → LLM 仅基于片段作答（英文），引用 source_title 标注出处；
      空作用域时工具返回 note="no knowledge base documents available for this company"
```

## 3. 知识库面板查询（只查登记表）

```
GET /api/ai/file-registry/files
 └ file_registry_service.list_documents()
    ├ _scope_company_ids()：公司端=本公司；管理端=手选 companyIds 或 organizationId 解析公司集
    └ FileRegistryRepository.list_kb_documents()：ai_file_registry ⨝ files
       文件名/类型/大小 ← files（FileRecord 只读）
       向量化状态/归属/会话/上传者 ← 登记行（status 由流水线镜像回写）
       角色可见性：公司端成员 creator_id=本人（只见己）、Company Admin 见全公司
下载 GET /files/{entryId}/download
 └ 按 entryId 反查登记行（归属校验：公司/本人/KB 行）→ lgpi query_file_link（Java 预签名）
删除 DELETE /records/{registryId}
 └ 有关联条目 → rag delete_entry（软删 entry + 清 chunk + 联动软删登记行）→ 文件退出面板与检索
```

## 4. 接口与主要业务方法对照表

| 接口 | 主要业务方法（代码位置） |
|---|---|
| SSE `chatbot.chat`（payload `file_ids` / `file_company_id`） | `chatbot/application/sse_provider.py::stream_turn` → `chatbot/application/service/chat_attachment_service.py::attach_files_to_message` |
| （space 定位/创建，无 HTTP 接口） | `rag/application/service/business_association_service.py::ensure_kb_space` |
| （条目 + 向量化，无 HTTP 接口） | `rag/application/service/ingest_service.py::ingest_kb_file` / `start_vectorization`；流水线 `rag/application/pipeline/ingest_pipeline.py` |
| （登记行创建，无 HTTP 接口） | `file_registry/application/service/file_registry_service.py::register_message_file`；底层原语 `lg/db/service/file_registry.py::upsert_kb_registration` |
| `GET /api/ai/file-registry/files` / `/files/uploaders` / `/companies` | `file_registry_service.list_documents` / `list_uploaders` / `list_org_companies` |
| `GET /api/ai/file-registry/files/{entryId}/download` | `file_registry_service.get_download_url`（→ lgpi `query_file_link`） |
| `GET/POST /api/ai/file-registry/records`、`GET/PUT/DELETE /records/{id}` | `list_records` / `create_record` / `get_record` / `update_record` / `delete_record` |
| （知识库检索，工具进程内直调） | `ai/tools/knowledge_base_tool.py` → `rag/application/service/search_service.py::recall`；作用域 `lg/db/service/file_registry.py::list_kb_space_ids` |

## 5. 关键设计决定备忘

- **business association space = 业务关联行，组合键唯一；space 多对多挂接**：「业务类型 + 端类型 + 公司/用户/组织(+未来维度)」的组合唯一确定一个 business association space——**关联行 id 的唯一来源是 `business_association_space_id()`**（uuid5 组合键派生，**所有**向 `ai_rag_business_association` 落库的行都经它取 id：devSupport 手工创建、chatbot 惰性创建；同组合恒同 id，重复创建被主键拦截、并发首建幂等；创建/编辑另有精确查重复校验兜底存量随机 id 行；未来加维度 = 加参数、拼组合串（空缺维度空串占位）、收窄精确查询），**不落在 space**：business association space ↔ space 是**多对多**（`ai_r_business_association_space`，一个关联可挂多个空间、一个空间可在多个关联下），入库目标从挂接集合里选 STANDARD 空间、没有则建一个 `add_space` 追加（不动其余挂接）。定位顺序：组合精确查（手工配的关联优先复用）→ **经 `create_association(auto_create_space=True)` 自动创建**。`create_association` 是唯一创建入口、两种用法共性收口：手工=选好空间主动关联（管理页缺省）、自动=未选空间时同事务自动建一个 STANDARD 空间并挂接（`_build_kb_space` 共享构造）；`ensure_kb_space` 只做「有则用、没有自动创建」的 find-or-create 薄编排（并发被拒后按组合复查复用赢家；**不按 id 兜底查**——防组合键 id 行被手工改走作用域后把 A 公司文件挂进 B 组合的空间）。
- **end_type 取值 APP / ADMIN（2026-07-19 定稿）**：客户端=APP、管理端=ADMIN，登记表与 `ai_rag_business_association`、Java `AiFileRegistry` 列注释共用同一枚举；存量 'CLIENT' 值由 business/V012 迁移改写为 'APP'（V005 回填当时写的是 CLIENT）。`business_association_space_id()` 对 end_type/business_type 双枚举强校验（id 是组合键编码，脏值会派生永久性错误 id）。
- **登记行 status 是向量化状态镜像**：PROCESSING（登记即投递）→ SUCCESS/PARTIAL/FAILED（`update_status_by_entry` 由 rag finalize/retry 回写），面板与登记表自洽、不依赖 entry。
- **file_ids 只在普通发送携带**：编辑重问/重试不重复登记（重试复用原 user 消息及其绑定）。
- **OCR 文件防冒用**：登记原语命中 purpose='financial_extract' 行直接拒绝（防止拿智能解析的 fileId 把财务文件拉进知识库检索）。
