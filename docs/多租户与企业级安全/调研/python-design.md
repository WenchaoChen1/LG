# Python 端（CIOaas-python）：租户作用域与隔离现状

> 关联文档: [决策摘要](./executive-summary.md) | [设计理念](./design-philosophy.md) | [系统架构](./system-architecture.md) | [Java 端](./java-design.md) | [前端](./frontend-design.md) | [证据代码](./code-examples.md)

路径以 `python/CIOaas-python/source/` 为根。

---

## 1. 身份上下文来源

### 1.1 唯一权威来源是 Java 写入的 Redis 会话

`common/redis/auth_store.py:43-47`（`_token_key`）+ `:69-86`（`get_user`）：token → `auth:token:{base64url_nopad(SHA256(jwt))}` → userId → `auth:user:{userId}` JSON。
`common/redis/auth_store.py:29-41`：`AuthUser(user_id, company_id, organization_id, authorities)`。

`common/auth/identity.py:35-61` 的 `get_current_user` 只解析身份，文件头 `:8-13` 明确声明**不做任何 company 级校验**，业务规则由各模块自行叠加。

全局中间件 `common/auth/middleware.py:38-53` 只调 Java 的令牌校验接口（`common/auth/access_check.py:47-81`），**它不知道请求要访问哪个租户的数据**。

豁免路径：`/`（精确）、`/health_check`、`/actuator` 前缀，以及环境变量 `AUTH_CHECK_EXEMPT_PATHS` 追加项（`access_check.py:89-107`）。另有 `AUTH_CHECK_ENABLED=false` 与 `AUTH_MOCK_ENABLED=true` 两个全局开关，后者在 prod/uat 有保护（`common/config/auth.py:75-85`）。

### 1.2 Redis 里的 organization_id 是哪一级

Java 侧两条装配路径：

- 缓存重建：`UserRepository.java:209-210` → `SELECT organization_id FROM r_organization_user WHERE user_id=?1 LIMIT 1`，**无 ORDER BY**
- 登录：`UserDetailsServiceImpl.java:177-184` → `userOrganizations.get(0)`

**结论：代码里没有任何"层级"的概念。它是用户在 `r_organization_user` 中直接关联的某一条记录，多条时取序不定。** 若租户定在 `Golden Section` 一级，而某用户挂的是更高层节点，Redis 里的值就是错的一级，**Python 侧完全无从察觉**。

### 1.3 客户端自报且不校验的位置

| 模块 | 位置 | 校验 |
|---|---|---|
| memory | `memory/interfaces/routes.py:48-51` | 无（但结果须过 Java 授权链） |
| file_registry 面板 | `file_registry/interfaces/routes.py:88-90,114,132-134,146` | 无 |
| chatbot manage | `chatbot/interfaces/routes.py:249,305,349,370` | 无，端点仅要求登录 |
| financial_extract | `financial_extract/interfaces/routes.py:61-62,81` | 无（DTO 注释直言"不参与鉴权，仅筛选展示"） |
| tracing | `tracing/interfaces/routes.py:85,144,173` | **无用户身份**，仅一个静态 token |
| rag 业务关联 | `rag/interfaces/routes.py:1034,1059` | 仅 `_require_admin`；**组织维度零校验** |
| chatbot 身份模拟 | `chatbot/application/sse_provider.py:281,302-304` | 仅 admin-only 门禁，组织值任意 |

memory 是唯一在代码里写明"这是不可信输入"的模块（`memory/application/memory_service.py:156-161`），但它与 file_registry 走同一条 Java 授权链，**实际安全等价**。

---

## 2. 各模块 ACL 现状

| 模块 | 结论 | 依据 |
|---|---|---|
| **memory** | **有（最严）** | `memory/application/memory_service.py:86-104`：公司端强制本公司 + Company Admin 门；管理端必须经 Java 链解析；空作用域 fail-closed（`:101-105`） |
| **file_registry** | **有** | `file_registry/application/service/file_registry_service.py:463-489`（下载三分支）、`:530,579,603`（跨公司 404）、`:216`（公司端非管理员只见己） |
| **chatbot 会话/消息** | **有（按人，非按公司）** | `chatbot/domain/repository/chat_thread_repository.py:23-37` 恒带本人 `user_id`，IDOR → 404 |
| **chatbot 端类型判定** | **有** | `chatbot/application/sse_provider.py:113-115`，由 Redis `company_id` 判，**不信前端** |
| **训练样本** | **有（每查询必带）** | `lg/db/service/ai_financial_training_data.py:66,195,211` |
| **financial_extract devSupport** | **部分** | `financial_extract/application/service/task_manage_service.py:44-56`：公司端强制本公司，管理端完全放开 |
| **lg extract-data** | **弱** | `lg/financial_extract_task/extract_data_service.py:334-342`：模块 docstring 自陈"这是一致性校验而非授权"，同时掌握 taskId 与其 companyId 即可通过 |
| **rag 读路径** | **无** | 见 §3 |
| **lg 旧任务列表** | **无** | `lg/financial_extract_task/routes.py:29-51`：**路由级零依赖**（文件头 `:8` 自陈 `Auth: none`）+ 全库分页。注意仍受全局 `AuthMiddleware` 覆盖（该路径不在豁免基线内），故实际风险是**任意已登录用户可读全平台任务**，不是匿名可读 |
| **llm tracking** | **无** | `llm/interfaces/routes.py:80-101`：共享 env token，**未配置即放行**；返回提示词全文（`:67-69` 自注含 PII） |
| **tracing** | **无** | `tracing/interfaces/routes.py:57-78` 同款开关式 token；`:12-16` 自陈租户参数可选、缺省返回全量 |
| **financial_forecast** | **无** | `financial_forecast/routes.py:112-113` 无任何依赖 |
| **playbooks** | **刻意无** | `ai/tools/search_playbooks_tool.py:6-11`：全平台共享内容，设计如此 |
| **sse** | **有（按人）** | `sse/interfaces/routes.py:204-208` owner 校验；但 `POST /stop/{stream_id}` 无 owner 校验（`:215-222`） |

---

## 3. RAG：租户隔离最薄弱的一块

### 3.1 空间是"全局资产"

`rag/interfaces/routes.py:104-110` 的 `_require_admin` 共 **19 个挂载点**，覆盖全部写操作 + 4 个 playbook 相关的 GET（`/playbook/ingest/status`、`/playbook/versions`、版本节点、版本 diff）。**空间与条目的读操作则只有 `Depends(get_current_user)`**：

- `GET /spaces`（`:149-165`）：登录可见全部空间
- `GET /spaces/{id}/chunks`（`:219-240`）与 `GET /entries/{id}/chunks`（`:436-469`）：直接分页读取**原始文档分段正文**
- service 侧显式传 `company_id=None`（`rag/application/service/stats_service.py:100-108`），模块头 `:5-7` 写明"文档读不按公司过滤"

可见性解析 `rag/application/service/search_service.py:418-450` 注释原文："旧空间租户归属表删除后空间为全局资产：space 存在且未软删即 granted" —— **没有任何 company / org / user 条件**。

### 3.2 `POST /recall` 是最直接的越权面

`rag/interfaces/routes.py:957-972`：无 `_require_admin`、无 `recall_company_ids` / `recall_created_by`，`space_ids` 由客户端任意指定；**缺省 = 全部空间**（`search_service.py:377-395`）。配合 `GET /spaces` 枚举，任何登录用户可跨公司语义检索。

### 3.3 chatbot 通道做得相当细（对照组）

`ai/tools/knowledge_base_tool.py:103-136` 按端分叉圈定空间，并传入行级过滤参数；实际下发的谓词由 `rag/domain/repository/chunk_repository.py:66-90,114-129` 组装——管理端是 `space_id` + `(company_id IN allowed OR thread_id)` 析取，公司端普通用户是 `space_id` + `created_by = 本人`（等价 SQL 见 [证据代码](./code-examples.md) §16）。

**但这一层保护有两个缺陷**：

1. 分段表的 `company_id` 由向量化完成后 **best-effort 回填**（`rag/application/pipeline/ingest_pipeline.py:263-270`，**同步内联调用但 try/except 吞异常**，注释写明"失败不影响已成功的入库"），且跨两个数据库非同事务（`rag/application/service/ingest_service.py:731-753`）。回填未完成时是 fail-closed（召不回，不泄漏），但文件会短暂"检索不到"。
2. `rag/infrastructure/storage/pg_store.py:144-152` 注释写明"空则返回 (None, None) 不过滤" —— 若调用方不传公司集也不传会话 ID，整个空间无行级过滤全暴露。当前 chatbot 路径必传，但 HTTP `/recall` 正是这种调用方。

### 3.4 管理端空间按组织派生，组织内跨公司混装

`rag/application/service/business_association_service.py:79-81,245-247`：空间关联 ID 由 uuid5 派生，**APP 端用 company_id，ADMIN 端用 organization_id**，即"每组织一个管理端空间"，空间名就是 `Admin {organization_id}`（`:271-272`）。

后果：该组织下**所有公司**的管理端上传文件 + 全部会话文件落进同一个空间，跨公司隔离**完全依赖分段的 `company_id` best-effort 回填 + 召回时的析取过滤**。

若 organization_id 取错层级：

- **取高于租户的层级** → 该层下所有子租户的管理端文件落进同一空间，隔离全压在 `company_id IN allowed` 这一道上；而 `allowed` 来自树根（见 §4），一旦覆盖多租户公司，**跨租户读取直接成立**
- **取低于/旁于租户的层级**，或不同用户挂在不同层级 → 同一租户的两个管理员派生出**两个不同的空间**，A 传的文件 B 检索不到，且 `find_chat_space_id` 返回 None 时静默返空，看不出原因
- **组织节点被搬家/合并** → uuid5 组合键"启用后不可改"（`:46` 注释），旧空间变孤儿，而 `ai_rag_space` 无组织列，无法反查归属

### 3.5 存储连接全局化

`rag/application/service/connection_service.py` 对应的主表无 `company_id`（code 全局唯一），且其 CRUD **不在管理端闸门内** → 任意登录用户可增删改数据源连接（凭据经 AES-GCM 加密存储，`rag/infrastructure/crypto/connection_cipher.py:19,66-76`）。

---

## 4. 两个 organization 源在同一请求中并存

| 源 | 位置 | 取值 |
|---|---|---|
| `ctx.organization_id` | Redis 会话 | Java `LIMIT 1` 无序取一 |
| `ctx.allowed`（可访问公司集） | `chatbot/application/service/company_service.py:55-61` | `query_user_organizations` → `organizations[0]` |

而 `lgpi_api/user_organizations_api.py:70-84` 的拍平是**前序 DFS**（父节点先入列），因此 **`organizations[0]` 恒为组织树的第一个根节点**。

两个值在 `ai/agent/chatbot_graph/nodes/retrieval_agent.py:199-217` 被装进同一个上下文对象（`:201` `allowed=...`、`:208` `organization_id=...`），随后在 `ai/tools/knowledge_base_tool.py` 分头使用：`:126` 用 organization_id 定位管理端知识库空间，`:120` 用 allowed 作分段级公司过滤。**两个值来自不同层级、不同算法，无任何一致性检查。**

另外 `lgpi_api/user_organizations_api.py:59-84` 的拍平**主动丢弃 `pid`、深度与父子关系**，只留 id + name。**想判断"哪一级是租户"，Python 侧目前连数据都拿不到。**

---

## 5. organization → 公司集解析链

```
memory._authorized_company_ids            (memory_service.py:148-188)
file_registry.list_documents / _scope_company_ids  (file_registry_service.py:164-184)
      └─> _resolve_admin_company_ids      (file_registry_service.py:432-449)
            └─> list_org_companies        (file_registry_service.py:363-400)
                  └─> query_organization_companies  (lgpi_api/organization_companies_api.py:85-91)
                        └─> GET /api/web/companyGroup/companies?organizationId=
```

Java 侧实现 `CompanyGroupRepository.java:51-56` 是 **`cg.organization_id = :orgId` 等值、不递归子树**，且**无"调用者是否属于该组织"的校验**，`seeAll = TRUE` 时对任意组织 ID 全开。

**传入层级不对的后果**：若传入的组织节点下并未直接挂载 Portfolio，返回空列表 → 面板/记忆/召回空白，**无任何"层级不对"的信号**。注意这条路径**不由用户点选**（前端组织树切换属于另一条路径，按单节点浏览是设计如此），用户无法自救。

**失败语义两套不一致**：

- `file_registry_service.py:384-386`：静默 fail-closed 并写入 120 秒缓存；且**无 try/except**，网络异常会一路抛成 HTTP 500
- `memory_service.py:169-183`：显式接住转 50301（可用性问题而非权限问题）

---

## 6. 表与隔离列

### 6.1 带 organization_id 的表

| 表 | 可空 | 查询是否真用它过滤 |
|---|---|---|
| `ai_chatbot_thread` | ✅ | 仅管理端筛选，业务读写路径不过滤 |
| `ai_trace` | ✅ | dev-support 可选筛选；**两个作用域参数都不给时直接放行**（`tracing/application/service/trace_query_service.py:93-94`） |
| `ai_file_registry` | ✅（存量行与财务抽取行恒 NULL） | **仅会话文件那一支**（`file_registry/domain/repository/file_registry_repository.py:153-157`） |
| `ai_rag_business_association` | ✅ | ✅ 精确等值 + uuid5 组合键 |
| `ai_rag_ent_kb_chunk` | ✅ | ❌ **写入但从不进 WHERE** |
| `ai_financial_extraction_task` | ✅（存量行留 NULL） | 仅筛选，DTO 注释"不参与鉴权" |

### 6.2 只有 company_id、无 organization_id

`ai_rag_entry`（记忆面板/文档管理主表）、`ai_rag_ingestion_task`、`ai_llm_call_log.ref_company_id`、`ai_llm_tool_call_log.ref_company_id`、`ai_financial_extraction_mapping_data`、`ai_financial_extraction_conflict_record`、`ai_financial_training_data`。

**以 organization 为租户时，这些表必须靠 company → org 反查才能归属——而那条反查链正是 §5 里那条不递归的链。**

### 6.3 两个都没有（归属完全不明）

`ai_rag_space`、`ai_rag_fin_report_chunk`、`ai_rag_playbook_chunk`、`ai_rag_search_log`（含用户原始提问）、`ai_rag_operation_log`、`ai_chatbot_message`（全部对话正文）、`ai_trace_span`、`ai_rag_playbook` / `_version`、`ai_llm_conversation`（**完整提示词与回复全文**）。

> ⚠️ 迁移注释与现实不符：向量库 V001 对分段表的列注释写着"tenant isolation via space binding, no company_id here"，而那张 binding 表已在业务库 V005 被 `DROP TABLE`。

---

## 7. 数据库、存储、缓存

| 层 | 现状 |
|---|---|
| 连接 | 两个连接串（业务库 `CIO_DATABASE_*` + 向量库 `RAG_DATABASE_*`，后者未配则回落前者）；`db/session.py:60-74,136-158` |
| 角色 | **同一个 DB 用户**，示例配置均为超级用户 |
| RLS / schema 隔离 / 分库 | **全部 0**。`SET ROLE` / `row level security` / `search_path` 在 `source/`、`sql/`、`scripts/` 下**零命中** |
| schema 覆盖字段 | `ai_rag_space.pg_schema` / `pg_table_name` 存在，但 `rag/infrastructure/storage/pg_store.py:48-52` 注释写明**未真正应用到 SQL** |
| S3 | Python **不直连 S3、不构造 key**；key 前缀由 Java 按业务类型决定，**不含 company / organization** |
| SQS | 消息体带 `taskId` / `companyId` / `createdBy` / `fileIds`（`consumer/messages.py:52-70`）；消费端**只校验非空**，`msg.companyId` **从不与任务行的 company_id 比对**（`consumer/handlers.py:165-176`、`ai/agent/financial_extract_graph/nodes/init_task_node.py:44-88`）。Java 若发错 companyId，训练样本会落到错误公司下 |
| Redis | 4 类 key（`auth:token:*` / `auth:user:*` / `chatbot:turn:*` / `sse:*`），均带天然唯一标识，**无串租户风险**；但 key 不带租户前缀，全服务共用 `CIO_REDIS_DB=10` |
| 进程内缓存 | 3 处，均按 user 分片（`chatbot/application/service/company_service.py:36-39`、`file_registry_service.py:68-70`、`ai/tools/_support/company_cache.py`） |

---

## 8. 超管与身份模拟

`chatbot/application/sse_provider.py:279-304`：

- 唯一门槛是**操作者 Redis `company_id` 为空**；无角色检查、无 Java 回调确认
- `simulate_organization_id` **不做存在性校验、不做成员校验、不做子树范围校验**，任意字符串即成为本轮 `ctx.organization_id`
- 该值随后驱动 `ensure_kb_space(organization_id=…)`（`:374`）→ **可往任意组织的管理端空间写文件、建空间**；读取侧被分段 `company_id IN ctx.allowed` 挡了一半，**写入侧完全没挡**
- `simulate_user_id` 走 `auth_store.get_user_by_id`，目标用户只要有活跃会话即可被模拟，同样无跨组织限制

### 「company_id 为空 ⟺ 超管」不变式

三处明文依赖：`financial_extract/application/service/task_manage_service.py:47-53`（注释原文称其为"平台不变式，不变式破产属平台级问题"）、`rag/interfaces/routes.py:104-109`、`chatbot/application/sse_provider.py:286`。

**多租户下的失效方式**：租户管理员的 `company_id` 天然为空 → 与真超管完全不可区分 → 立即获得跨公司列表与回放、RAG 空间增删改（而空间是全局资产、无归属列，可删别的租户的空间）、以及模拟任意组织/公司/用户的能力。

---

## 9. 文档与代码漂移（需清理）

| 描述位置 | 声称 | 实际 |
|---|---|---|
| `python/CIOaas-python/CLAUDE.md`、`rag/CLAUDE.md` | chatbot 检索圈定由 `ai_file_registry.list_kb_space_ids` 驱动，标为"安全关键" | 已改走 `business_association_service.find_chat_space_id` + 分段行级过滤；`search_service.py:355-376` 的该分支**零调用方，是未测死代码** |
| `rag/CLAUDE.md` | 分段表"不存 company_id" | `EnterpriseKbChunk` 自向量库 V003 起已有 `company_id` / `created_by` / `thread_id` 并**参与召回过滤** |
| 向量库 V001 列注释 | "tenant isolation via space binding" | binding 表已被业务库 V005 删除 |
| **`rag/domain/repository/chunk_repository.py:109-110` docstring** | "**无 company_id 过滤**：租户隔离由调用方按 company 圈定 space 范围保证（chunk 表已不存 company_id 列）" | **同一文件 `:79-80` 正在执行 `company_id.in_(...)`**。这条漂移在**代码本体**里，比 CLAUDE.md 的漂移更危险——照 docstring 改动召回逻辑会直接拆掉现有的行级过滤 |

---

## 10. Python 侧缺口清单（以 organization 为租户）

| # | 缺口 | 优先级 |
|---|---|---|
| P-1 | 没有"租户级 organization"的概念，也没有取它的函数；两个 org 源（Redis 无序取一 / 树根）并存且无一致性检查 | P0 |
| P-2 | 组织树拍平时**主动丢弃 pid 与层级**，判断租户所需数据不可得 | P0 |
| P-3 | 零处校验"调用者是否属于该 organization" | P1 |
| P-4 | 「`company_id` 为空 ⟺ 超管」在多租户下等价于"每个租户管理员 = 全局超管"，被 3 个模块当硬前提 | P1 |
| P-5 | RAG 读路径无归属：`/spaces`、`/spaces/{id}/chunks`、`/entries/{id}/chunks` 登录即全量；`/recall` 缺省全部空间且无行级过滤 | P1 |
| P-6 | `simulate_organization_id` 可任意指定，写入侧完全无边界 | P1 |
| P-7 | 管理端空间"一组织一空间"，组织内跨公司混装，隔离依赖 best-effort 回填（跨库非同事务） | P1 |
| P-8 | org→公司集解析链不递归子树，服务端自动圈定时若层级不对则静默返空（用户不可自救）；失败语义两套不一致 | P1 |
| P-9 | `/lg/financial-extract-tasks*` 无鉴权依赖 + 全库分页；`/api/ai/llm-calls/*` 与 `/api/ai/traces/*` token 未配置即放行且返回提示词全文 | P1 |
| P-10 | 归属不明的数据面很大（10 张表既无 company 也无 org） | P2 |
| P-11 | 所有 `organization_id` 列可空且存量为 NULL，改为过滤条件会让历史数据整批消失 | P2 |
| P-12 | 无审计基类，每个模型手写重复列 | P2 |
| P-13 | SQS 消息的 companyId 从不与任务行比对 | P2 |
| P-14 | 三处文档与代码漂移 | P2 |
