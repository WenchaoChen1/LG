# RAG 管理 — 技术决策疑点

> 共 **16 个疑点**，覆盖 arch-designer §15 自审 10 条 + arch-questioner 新增 6 条。
> 每个疑点包含：背景 + 候选方案 + 推荐方案 + 影响。
> 用户已授权"自动用默认/推荐值，自己头脑风暴"，所以默认走推荐方案，除非有强烈反对理由。
> 待 Tech Lead / Arch Reviewer 确认后，将推荐方案回填到 `dev-design-doc.md` 定稿。

---

## A. 数据库与向量后端

### A1. pgvector 索引类型：HNSW vs IVFFlat

**来源**：arch-designer 自审 §15-1

**背景**：设计采用 HNSW（`m=16, ef_construction=64`）。pgvector ≥ 0.5.0 支持 HNSW。IVFFlat 在非常大的数据集下构建更快，但 recall 低于 HNSW。当前生产 PostgreSQL 中 pgvector 的确切版本未知。

**候选方案**：
- A. HNSW（推荐）——查询快（无需探针预热）、recall 高（~95-98%）、单次增量 insert 直接维护索引，缺点是内存使用约 `rows × dims × 4bytes × 1.5`，100 万行 ×1536 维约 9 GB
- B. IVFFlat——内存省、批量构建快，但需要预先聚类（`lists = sqrt(rows)`），增量插入不更新聚类中心，低于聚类规模时 recall 会明显下降（< 90%）
- C. 混合：HNSW 优先，行数超 100 万时按 company_id 分区 + 迁移 IVFFlat

**推荐**：A（HNSW）— RAG行数短期预估不会超过 50 万（中小企业场景），HNSW 的内存在可接受范围内；recall 高意味着检索质量稳定；§14 风险已有"超 100 万行预警"缓解措施。前提条件：**生产 PG 实例的 pgvector 版本必须 ≥ 0.5.0**，部署前需确认。

**影响**：若 pgvector 版本 < 0.5.0 需先升级再部署；内存基线需纳入容量规划。

---

### A2. ES 索引粒度：公司+版本 vs 全局单索引

**来源**：arch-designer 自审 §15-2

**背景**：设计命名方案为 `rag_{env}_{company_id_short}_v{n}`（公司×版本粒度）。平台客户公司数增长后，每公司每版本产生一个索引，100 个公司 × 2 个版本 = 200 个索引。ES 默认分片限制为 1000，集群扩容后更大，但小索引（< 1000 条 chunk）造成 shard overhead。

**候选方案**：
- A. 当前设计：公司+版本粒度（推荐）——多租户隔离强，删除一个公司的数据只需 delete index，不影响其他租户；迁移清理旧版本直接 delete index
- B. 全局单索引 + `company_id` / `space_id` 过滤——索引数少，小公司无浪费；但 company_id 过滤做不了 index-level 隔离，误扫数据的风险更高；跨分片 BM25 评分会因全局 term 频率失真
- C. 公司粒度（不按版本切）——版本共存于同一 index，迁移时 by `embedding_version` 字段过滤；索引数 = 公司数，相对合理

**推荐**：A（公司+版本粒度）— 多租户安全性优先，且迁移期清理旧向量代价最低（delete index 是 ES 最廉价操作）。缓解索引数膨胀的手段：对活跃公司数 > 500 的场景在配置中切换回 pg 后端（RAG_STORAGE_BACKEND=pg）。

**影响**：如果决定改为方案 C，需修改 `es_store.py` 的索引命名逻辑和迁移清理逻辑。

---

### A3. pgvector `vector(3072)` 固定维度的空间浪费

**来源**：arch-designer 自审 §15-5

**背景**：`rag_chunk.embedding` 声明为 `vector(3072)` 以容纳 text-embedding-3-large（3072 维）。但默认模型是 text-embedding-3-small（1536 维），向量列中每行有 1536 个浮点数（约 6 KB）是空的——PG 实际存储的是声明维度，填入更少维度的向量在插入时会被 PG 报错（维度不匹配），因此当前设计的含义实际上是"空间选定的模型维度 ≤ 3072"，应用层在 upsert 前做维度校验。

**候选方案**：
- A. 保持 `vector(3072)` + 应用层维度校验（推荐）——最简单，一张表，无分表逻辑；1536 维向量实际 PG 存储也是 `vector(1536)` 数据（PG 向量列存的是实际数据长度不是声明上限，因此不浪费），唯一限制是"不能插入维度超过声明值的向量"
- B. 按维度分表（`rag_chunk_1536` / `rag_chunk_3072`）——存储精准，但检索需路由到正确表，迁移中新旧版本可能在不同表，代码复杂度高
- C. 每个 space 独立表（动态 DDL）——隔离最强，但动态建表有安全隐患且 PG 表数量太多

**推荐**：A — 经验证 pgvector 的 `vector(N)` 列只允许插入**恰好 N 维**的向量（不是上限，是精确匹配）。因此当空间使用 1536 维模型时，应用层必须用 `vector(1536)` 插入——这意味着设计中的"单列 3072"方案实际上**不允许同一张表混用不同维度**。

**核心决策**：需要明确"同一 rag_chunk 表中是否存在不同维度 chunk 并存的场景"。如果不存在（每个 space 固定一个维度），则 A 方案只需按 space_id 做分区或为每个 space 建独立索引即可。**推荐把 HNSW 索引改为按 space 维度在首次入库时动态创建（`CREATE INDEX IF NOT EXISTS`），`rag_chunk.embedding` 列改为 `vector(embedding_dim)`，通过 `ALTER TABLE` 或分区解决**——但这显著增加复杂度。

**实用推荐**：本期只支持单一全局最大维度（3072），所有 space 的向量都 padding 到 3072 维（低维模型结果后面补 0），避免多维度共存问题。配置变量 `RAG_PG_VECTOR_DIM_MAX` 已预留。**或者更简单：本期只允许空间选择维度 ≤ `RAG_PG_VECTOR_DIM_MAX` 的模型，插入时严格要求精确维度，不做 padding——由工厂方法校验并拒绝不匹配维度的空间选模型**。

**影响**：需在设计文档中明确"pgvector 维度精确匹配语义"，避免开发时误解为上限语义。

---

### A4. `rag_chunk` 表未来行数与分区策略

**来源**：arch-designer 自审 §15-10

**背景**：多公司多空间共享一张 `rag_chunk` 表，每个条目约 10-50 个 chunk，100 家公司各 100 个条目时总行数约 50 万-500 万。PG 单表到 5000 万行以上查询性能会显著下降（即使有索引）。

**候选方案**：
- A. 本期不分区，监控行数，超 500 万行时再迁移（推荐）——MVP 阶段客户规模小，避免过度设计；`idx_rag_chunk_space_version` 索引已能满足查询
- B. 从一开始就按 `company_id` 做 PG 声明式分区（LIST 分区）——未来扩展容易，但每新增公司需 `CREATE TABLE PARTITION`（可自动化），且 pgvector HNSW 索引在分区表上的支持需验证（pgvector 0.7+）
- C. 改用 `timescaledb` 超表或外部分片——引入额外依赖

**推荐**：A — 预估本期客户数量不会触发 500 万行，且 §14 已有"超 100 万行预警"机制。分区改造可作为 Scale Phase 2 项目，不在本期做。

**影响**：需在代码中确保 `company_id` 始终作为过滤条件（已在 §11.2 规定），为未来分区键做铺垫。

---

### A5. 数据库 Migration 工具选型

**来源**：arch-questioner 新增

**背景**：§13.1 写的是"新增到 `CIOaas-python/migrations/`（Alembic 或现有手工 SQL 目录）"——括号内的"或"表明当前尚未确定。查看现有项目中是否已有 Alembic 配置或手工 SQL 目录。

**候选方案**：
- A. 沿用现有手工 SQL 脚本目录（推荐，前提是项目已有）——零引入新依赖，按时间戳顺序命名，`rag_001_*.sql` ... `rag_008_*.sql` 直接扩展
- B. 引入 Alembic——版本链管理、自动生成 diff、支持 downgrade；但需要把现有手工 SQL 全部补录进 Alembic 的历史版本链，工作量大
- C. 手工 SQL + 简单版本跟踪表（记录已执行脚本名，启动时检查）——比纯手工稍好，不引入框架

**推荐**：A — 如果现有项目已是手工 SQL 目录，本期保持一致，避免引入迁移成本。若项目从未有过 migration 工具，选 B（Alembic）打好基础。**需确认 `CIOaas-python/` 目录下是否已有 `migrations/` 或 `alembic.ini`。**

**影响**：Alembic 与 pgvector 扩展（`CREATE EXTENSION`）的兼容性需验证（Alembic op 支持自定义 SQL，无兼容性问题）。

> ✅ **已决策（见 tech-answers A5）**：经核查，项目已有手工 SQL 目录 `CIOaas-python/sql/migrations/`（命名约定 `YYYY-MM-DD_<purpose>.up.sql` / `.down.sql`，实例 `2026-05-26_llm_call_log_business_prefix.up.sql`），无 Alembic。最终采用**方案 A**：新增脚本沿用 `sql/migrations/`，命名 `2026-05-26_rag_001_*.up.sql` … `rag_008`，不引入 Alembic。**本背景中引用的初稿路径 `CIOaas-python/migrations/` 为初稿笔误，定稿 dev-design-doc.md §13 已更正为 `CIOaas-python/sql/migrations/`。**

---

## B. 异步任务与可靠性

### B1. BackgroundTasks 单机崩溃丢任务的可靠性接受度

**来源**：arch-designer 自审 §15-7；见 §14 风险表

**背景**：设计选择 FastAPI `BackgroundTasks` 而非 SQS，原因是"需求里没有强可靠性要求"（§15）。BackgroundTasks 的任务在进程内存中，进程重启即丢任务。缓解手段是 cron 把 `PROCESSING` 超 `RAG_ENTRY_TIMEOUT_S`（1800s）的条目置为 FAILED，用户手动重试。

**候选方案**：
- A. 保持 BackgroundTasks + cron 超时兜底（推荐）——实现最简；模型迁移任务（可能数小时）崩溃后由 cron 标 FAILED + 用户"重新迁移"恢复；可靠性低但运维成本低
- B. 入库任务走 SQS，迁移任务也走 SQS——可靠性高，与 `lg/financial_extract_task` 模式一致，但需要额外 SQS 队列 + consumer 改造，开发量增加约 2 周
- C. 折中：常规入库用 BackgroundTasks，长时间迁移任务写 DB 进度 + 重启后自动续跑——需要迁移 runner 支持"断点续跑"逻辑（按已完成 entry 跳过），中等工作量

**推荐**：A（短期）/ C（中期）— 本期用 A；如果模型迁移任务在真实场景下确实出现多次崩溃丢失，升级到 C（迁移 runner 加"跳过已完成 entry"判断，成本约 1-2 天）。**需在 §14 中明确"单实例部署期间模型迁移任务崩溃重启丢失是已知风险，可接受"。**

**影响**：若客户有超大空间（10 万+ 条目），迁移任务可能需要数小时，此时 A 方案风险较高，建议优先实现 C。

---

### B2. 模型迁移任务的并发控制

**来源**：arch-questioner 新增

**背景**：设计中 PUT `/rag/spaces/{id}` 触发迁移时会检查 `status=MIGRATING` 拒绝重复（`40902`）。但存在竞态：若两个请求同时到达，两者都读到 `status=READY` 然后各自写 `MIGRATING` + 创建 `rag_migration_task`，会产生两个并发迁移任务同时跑。

**候选方案**：
- A. 数据库层唯一约束 + SELECT FOR UPDATE（推荐）——在 `service.update_space()` 中用 `SELECT rag_space ... FOR UPDATE` 锁行，再判断 status，写入 `MIGRATING` 并 commit；后来的请求获取行锁时已读到 `MIGRATING`，返回 409。需要显式事务
- B. 应用层加 Redis 分布式锁——额外依赖；若当前无 Redis 则不适用
- C. `rag_migration_task` 加唯一约束 `(space_id, status='RUNNING')`——通过 DB 约束强制幂等，违反约束时捕获异常返回 409

**推荐**：A — `SELECT FOR UPDATE` 是最轻量的 PG 原生方案，无额外依赖。`service.update_space()` 整体已需要事务（写 rag_space + 写 rag_migration_task），加 `FOR UPDATE` 自然。

**影响**：需确保 `space_service.py` 的迁移触发逻辑在同一事务内完成 SELECT FOR UPDATE → 状态校验 → 写入。

---

## C. 检索算法

### C1. RRF 融合与 ES hybrid 的双重融合冗余

**来源**：arch-designer 自审 §15-4

**背景**：设计推荐 RRF（k=60）做关键词+向量结果的融合。但如果 ES 后端使用 `ElasticsearchStore(ApproxRetrievalStrategy(hybrid=True))`，ES 内部已做了一次 hybrid（BM25+knn 的线性融合），再在 Python 层做 RRF 相当于对"已融合结果"再融合一次，可能产生排名失真。

**候选方案**：
- A. PG 后端：Python 层 RRF（完全自控）；ES 后端：使用 ES 自带 hybrid，Python 层不再做 RRF（推荐）——两种后端各自走最优路径，但两种后端结果分布有差异
- B. 两种后端统一用 Python 层 RRF，ES 后端不开 hybrid——ES 分两次查（keyword + knn）再 Python 合并，行为与 PG 完全一致；ES 查询次数翻倍
- C. 两种后端统一用 ES hybrid / pgvector 融合，不在 Python 层做 RRF——pg 后端需自己实现权重融合，放弃 RRF 优势

**推荐**：B — 统一用 Python 层 RRF 保证两种后端行为一致，便于测试和结果对比；ES 每次检索多一次查询（keyword + knn = 2 次），在 < 5s 的 SLA 下可接受。若未来 ES 后端性能成瓶颈可切回 A。

**影响**：`es_store.search()` 实现时不开 `hybrid=True`，而是分别调 `keyword_search` 和 `knn_search`，在 `search_service.py` 统一 RRF。

---

### C2. 跨空间检索的 SQL 实现策略

**来源**：arch-questioner 新增

**背景**：§10.2 描述"同版本下走单条 SQL `WHERE space_id = ANY(...)`"，但 pgvector ANN 查询（`<-> ORDER BY LIMIT`）在 `space_id = ANY(...)` 的多值场景下**无法使用 HNSW 索引**——pgvector 的 HNSW 需要 `space_id =` 单值过滤才能 Index Scan；多值 ANY 会退化为 Seq Scan。

**候选方案**：
- A. 跨空间时并发多条单空间查询，Python 层 `asyncio.gather()` 合并（推荐）——每条 SQL 都能命中 HNSW 索引；代码简单；N 个空间 = N 条并发查询，但通常 2-5 个空间，延迟可叠加到 < 5s
- B. 单条 SQL 加 `pgvector_hnsw_ef_search` + 大 probes——无法走索引，退化为顺序扫描，P95 > 5s 风险高
- C. 按 space_id 做分区表，每分区建 HNSW——可以分区裁剪，但分区表+pgvector 兼容性需验证

**推荐**：A — `asyncio.gather()` 并发单空间查询是目前 pgvector 跨空间的唯一有效方案，§10.2 的"单条 SQL WHERE space_id = ANY"描述需要**修正**为"按 space_id 循环并发查询"。

**影响**：`pg_store.search()` 实现时需改为 `gather([search_single_space(sid) for sid in space_ids])`，而非单条多值 SQL。§10.2 需更新。

---

## D. OCR 实现

### D1. OCR Provider 选型与中文场景

**来源**：arch-designer 自审 §15-3

**背景**：设计推荐 Textract 为主，GPT-4o vision 为备。Textract 在英文 + 结构化表格场景效果好，成本低（约 $0.0015/页）；但中文 OCR 效果不如 Azure Document Intelligence 或 PaddleOCR。`RAG_OCR_PROVIDER=auto` 已预留切换机制。

**候选方案**：
- A. Textract 主 + GPT-4o vision 备（已在设计中，推荐）——复用现有 AWS 凭证，成本可控；中文场景 Textract 也能识别（支持中文），但精度低于专用中文 OCR
- B. Azure Document Intelligence——中文效果最优，但需要引入新的 Azure 账号/凭证 + Python SDK（`azure-ai-formrecognizer`），且需确认公司 Azure 订阅是否覆盖
- C. PaddleOCR（开源本地部署）——无 API 成本，中文最优，但需要容器内额外安装（约 1 GB 模型权重），冷启动慢，增加 infra 复杂度
- D. `auto` 模式：语言检测 → 英文走 Textract，中文走 GPT-4o vision——折中，无需新依赖，GPT-4o vision 对中文文档效果好但成本高（$0.01+/页）

**推荐**：A（本期）— 保持设计方案。中文场景如果真的出现大量图片 OCR 需求，通过 `RAG_OCR_PROVIDER=vision` 切到 GPT-4o vision 兜底；Azure / PaddleOCR 留作后续优化项。**需确认生产环境的 Textract 区域（us-east-1 / ap-southeast-1）和是否需要申请 quota 提升。**

**影响**：IAM 权限需要 `textract:DetectDocumentText` + `textract:AnalyzeDocument`；若 S3 文件在非 Textract 支持区域，需要 cross-region 处理策略。

---

### D2. PARTIAL 条目重试期间旧检索能力的保持实现

**来源**：arch-questioner 新增

**背景**：需求 §4.7.2 明确"'部分成功'重试期间原条目的'文件名可检索'能力保持不变"。但设计文档中重试逻辑只写了"从头重做"（`POST /rag/entries/{id}/retry`），没有明确说"重试开始时不删元数据，只有在新流程成功后才替换"。

**候选方案**：
- A. 重试时不清 entry 元数据，直接新建 pipeline runner，成功后覆盖，失败后 entry.status=FAILED（推荐）——PARTIAL 条目的 `entry.title`、`entry.file_id` 保持不变，关键词召回一直可用；pipeline 成功后 `UPDATE rag_entry SET status=SUCCESS, chunk_count=...`；失败后 `UPDATE rag_entry SET status=FAILED`
- B. 重试时先清 entry 数据再重建——会导致重试中的短暂窗口内关键词召回也不可用，不符合需求

**推荐**：A — 设计文档需要在 `ingest_service.py` 的重试逻辑中明确注释："PARTIAL entry 重试时保留 metadata，不预先清除"。

**影响**：`ingest_service.retry_entry()` 实现时需保留 entry 现有的 `title / file_id / status=PARTIAL`，只在成功时覆盖，在失败时改为 `FAILED`（不保留 PARTIAL）。

---

## E. Embedding 与 LLM Provider

### E1. Embedding 调用是否记录 llm_call_log

**来源**：arch-questioner 新增

**背景**：§8.4 提到"LLM/Embedding 调用走 `source/llm/tracing/` 已有埋点，自动写 LLMCallLog"，但 `rag_space.total_tokens`（通过 `rag_entry.total_tokens` 聚合）已经记录了 embedding token 消耗。如果两者都写，会有重复计量。

**候选方案**：
- A. Embedding 调用不写 `llm_call_log`，只写 `rag_entry.total_tokens`（推荐）——RAG场景的 token 计量通过 `rag_entry.total_tokens` 聚合已满足需求；`llm_call_log` 保留给 LLM 对话（chat）调用
- B. Embedding 调用也写 `llm_call_log`，两个口径并存——双重计量，不冲突，但查询时要注意去重
- C. 只写 `llm_call_log`，`rag_entry.total_tokens` 从 `llm_call_log` 聚合——去掉 `total_tokens` 字段，但聚合查询更复杂

**推荐**：A — `total_tokens` 字段直接落在 entry 上，查询统计最便捷（不需要 join `llm_call_log`）；`llm_call_log` 用于 LLM chat 调用的追踪。若未来需要 embedding 成本审计，`source/llm/providers/embeddings/` 的 factory 可以选择性注入 tracer。

**影响**：`embedder.py` 实现时不需要注入 tracing，只需返回 `(vectors, total_tokens)` 并在调用方写 `rag_entry.total_tokens`。

---

## F. 安全与鉴权

### F1. 管理员角色的判定方式

**来源**：arch-designer 自审 §15-8

**背景**：设计依赖 Java 网关注入 `x-user-role` HTTP 头来判断"公司管理员"。但 Java 现有鉴权中 role 字段的确切值不明（可能是 `ADMIN` / `COMPANY_ADMIN` / `CIO` 等）。需要确认 Java 网关是否已在转发 `/rag/**` 请求时注入该字段，以及具体的 role 值。

**候选方案**：
- A. Java 注入 `x-user-role` 头，Python 端直接读取，白名单校验（推荐）——与 `financial_extract` 模块的鉴权模式一致；只需确认 Java 实际注入的 role 字段名与值
- B. Python 端查 DB `user` 表获取 role——Python 需要直接查 `users` / `roles` 表，与 Java 共享 DB 读，增加 Python 的 DB 依赖
- C. 专门增加 `/rag/auth/check-admin` 调用 Java——引入回调调用，性能开销 + 循环依赖风险

**推荐**：A — 需要 Java 开发确认：① `x-user-role` 头是否已在 `/rag/**` 代理时注入；② 管理员角色的具体 role 值（例如 `COMPANY_ADMIN`）；③ 如果 Java 未注入，是否需要 Java 端小改。

**影响**：Python `require_user_context()` dependency 需要解析 `x-user-role`，明确 admin 判定逻辑（`role in ADMIN_ROLES`，配置化）。

---

## G. 部署与迁移

### G1. pgvector 扩展在生产环境的安装策略

**来源**：arch-questioner 新增

**背景**：`rag_002_create_extensions.sql` 包含 `CREATE EXTENSION IF NOT EXISTS vector`，但在 AWS RDS / Aurora PostgreSQL 上安装 pgvector 需要 RDS 实例版本支持（pgvector 在 RDS PG 14.5+ / 15.2+ / 16+ 上通过 `CREATE EXTENSION` 可用），且必须有 `rds_superuser` 权限。生产环境是 RDS 还是自建 PG 不明确。

**候选方案**：
- A. 确认生产是 RDS，通过 `CREATE EXTENSION IF NOT EXISTS vector` 安装（推荐 + 需确认版本）
- B. 生产是自建 PG，需要 OS 层安装 pgvector（`apt install postgresql-${VERSION}-pgvector`）然后 `CREATE EXTENSION`
- C. 生产是 Aurora Serverless——Aurora Serverless v2 支持 pgvector，但需确认 Aurora 版本

**推荐**：A — 在 `rag_002_create_extensions.sql` 执行之前，需要运维确认：① 生产 PG 部署方式；② pgvector 版本是否 ≥ 0.5.0（HNSW 支持）；③ 执行账号是否有 `CREATE EXTENSION` 权限。把这 3 个检查项加入部署 checklist。

**影响**：这是部署阻断项——如果 pgvector 未安装，所有 `rag_chunk` 相关 migration 都会失败。

---

### G2. `ai_files.task_id` 改可空对现有财务抽取链路的影响

**来源**：arch-questioner 新增

**背景**：`rag_001_alter_ai_files.sql` 执行 `ALTER COLUMN task_id DROP NOT NULL`。现有财务抽取模块（Java 端）在创建 `ai_financial_extraction_task` 后写入 `ai_files`，`task_id` 原为 `NOT NULL`。修改为可空后，Java 端如果有代码路径在写 `ai_files` 时不传 `task_id`（例如某些异常分支），原来会被 DB 约束拦截，改后会静默写入 `NULL`，可能导致财务抽取任务关联丢失。

**候选方案**：
- A. 接受约束放松，但在应用层加 purpose 检查——Java 写 `ai_files` 时强制传 `purpose='financial_extract'` + `task_id`；在 Python 的 RAG 入库代码中只写 `purpose='rag'` + `task_id=NULL`；DB 约束层面无法强制"financial_extract 时 task_id 非空"（推荐）
- B. 加 DB 级 CHECK 约束——`CONSTRAINT chk_ai_files_task CHECK ((purpose='rag' AND task_id IS NULL) OR (purpose='financial_extract' AND task_id IS NOT NULL))`，严格在 DB 层保证；但这依赖 `purpose` 字段先存在（migration 顺序：先 ADD purpose DEFAULT，再 ADD CONSTRAINT）
- C. 不修改 `task_id NOT NULL`，为 RAG 入库创建单独的 `rag_files` 关联表——彻底隔离，不触碰 `ai_files`；但 §13.3 esapiens 代码复用可能依赖 `ai_files`

**推荐**：B — DB 级 CHECK 约束最安全，能在 DB 层防止财务模块回归风险。migration 脚本调整为：① ADD COLUMN purpose WITH DEFAULT；② UPDATE 回填；③ DROP NOT NULL task_id；④ ADD CONSTRAINT chk。

**影响**：如果选 B，需要确认 Java 财务模块在所有写 `ai_files` 的代码路径都传了 `task_id`（可以通过 `grep` 确认），避免 CHECK 约束违反。

---

## H. 监控与可观测性

### H1. BackgroundTasks 的 Sentry / New Relic 追踪

**来源**：arch-questioner 新增（参考 §10.3 监控埋点）

**背景**：§10.3 列出了多个 metrics，但 BackgroundTasks 在 FastAPI 中是在请求结束后异步执行的，**不在原始请求的 transaction 上下文中**。Sentry 的 `hub` / `scope` 不会自动传播到 `BackgroundTasks`；如果入库 pipeline 抛出未捕获异常，Sentry 可能无法将其关联到原始请求，导致监控盲区。

**候选方案**：
- A. 在 `pipeline_runner.py` 和 `migration_runner.py` 入口处手动 `with sentry_sdk.new_scope():` 创建新 scope + 设置 tags（entry_id, space_id, company_id）（推荐）——轻量，无需改 BackgroundTasks 机制
- B. 把后台任务包装成一个 Sentry transaction（`sentry_sdk.start_transaction`）——追踪更完整，但需要每个 runner 都手动管理 transaction 生命周期
- C. 依赖当前 Sentry 全局异常捕获（不做特殊处理）——入库失败时 Sentry 会捕获 exception 但无 context（不知道是哪个 entry/space），难以调试

**推荐**：A — 在 `pipeline_runner.run_file_entry()` 和 `migration_runner.run()` 的顶层加 try-except + Sentry scope，在 finally 中调用 `sentry_sdk.flush()`；同时在 scope 中设置 `entry_id` / `space_id` / `company_id` tags，与 New Relic 自定义 metrics 的 tag 体系保持一致。

**影响**：需在 `background/pipeline_runner.py` 和 `background/migration_runner.py` 中补充 Sentry scope 设置，约 10 行代码。

---

## 批量答复模板

请逐条填写（可合并相同答案）：

```
A1（HNSW vs IVFFlat）：确认推荐方案 A / 补充：pgvector 版本 = ___
A2（ES 索引粒度）：确认推荐方案 A / 改为方案 C（公司粒度不按版本）
A3（vector 维度语义）：确认"精确匹配，不做 padding" / 改为"padding 到 3072"
A4（分区策略）：确认本期不分区 / 加分区
A5（Migration 工具）：现有项目已有 ___ / 选 A（手工 SQL）/ 选 B（Alembic）
B1（BackgroundTasks 可靠性）：接受方案 A / 升级方案 C（迁移任务断点续跑）
B2（并发迁移控制）：确认推荐方案 A（SELECT FOR UPDATE）
C1（RRF vs ES hybrid）：确认推荐方案 B（统一 Python RRF）/ 选方案 A（后端各自最优）
C2（跨空间 SQL 策略）：确认需修正为并发单空间查询 / 其他
D1（OCR 选型）：确认 Textract 主方案 / 需要 Azure / 生产 Textract 区域 = ___
D2（PARTIAL 重试保持能力）：确认方案 A / 其他
E1（llm_call_log 记录）：确认方案 A（embedding 不写 llm_call_log）/ 选 B（双写）
F1（管理员角色判定）：x-user-role 头已注入 / 未注入需 Java 改 / 管理员 role 值 = ___
G1（pgvector 生产安装）：RDS PG 版本 = ___ / 自建 PG / pgvector 版本 = ___
G2（ai_files.task_id 可空风险）：确认方案 B（DB CHECK 约束）/ 方案 A（应用层）
H1（BackgroundTasks Sentry）：确认方案 A / 选方案 B（完整 transaction）/ 跳过本期
```

---

**共 16 个疑点，分 8 个类别。建议优先决断影响架构的 C2（跨空间查询 SQL 修正）、G2（ai_files 约束安全性）、A3（pgvector 维度精确语义）。**
