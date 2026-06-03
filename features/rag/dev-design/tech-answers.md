# RAG 管理 — 技术决策疑点答复

> 用户授权"自动用默认/推荐值，自己头脑风暴"。
> 共 16 个疑点全部决策完毕。其中 14 项采用 arch-questioner 推荐方案；2 项基于项目现状或风险考虑微调。

## 一、答复总览

```
A1=A   (pgvector HNSW)
A2=A   (ES 索引：公司+版本粒度)
A3=A'  (微调：本期固定 1536 维，vector(1536)，不做 padding，多维度支持留 v2)
A4=A   (本期不分区)
A5=A   (沿用现有手工 SQL；已确认项目走 sql/migrations/)
B1=A   (BackgroundTasks + cron 兜底；本期接受单机崩溃风险)
B2=A   (SELECT FOR UPDATE)
C1=B   (统一 Python 层 RRF，两后端行为一致)
C2=A   (修正：并发单空间查询，asyncio.gather)
D1=A   (Textract 主 + GPT-4o vision 备)
D2=A   (重试保留 metadata)
E1=A   (Embedding 不写 llm_call_log)
F1=A   (Java 注入 x-user-role 头；需 Java 侧确认值)
G1=A   (RDS PG；部署前确认版本)
G2=B   (DB CHECK 约束)
H1=A   (BackgroundTasks 内 sentry_sdk.new_scope)
```

## 二、逐项决策与理由

### A1. pgvector 索引类型 → **A. HNSW**（采纳推荐）
- 行数预估短期 < 50 万，HNSW 内存可承受
- recall 95-98% 优于 IVFFlat
- 增量插入自动维护索引
- **前置条件**：生产 PG 的 pgvector ≥ 0.5.0（部署 checklist 加入此项）

### A2. ES 索引粒度 → **A. 公司+版本**（采纳推荐）
- 多租户隔离强
- 迁移期清理旧版本只需 `DELETE INDEX`
- 活跃公司 > 500 的场景通过 `RAG_STORAGE_BACKEND=pg` 切换避免索引爆炸

### A3. pgvector vector 维度 → **A'（微调）：本期固定 1536 维**

**arch-questioner 给出的 3 个候选都有缺陷**：
- 选 A 原文（保 3072 + 应用层校验）依然不能解决"同表多维度并存"问题
- 选 B（按维度分表）复杂度高，本期 MVP 不值
- 选 C（按 space 独立表）违反"少表多行"原则

**自动头脑风暴的决策**：
- **本期 `rag_chunk.embedding` 列定义为 `vector(1536)`**（不是 3072）
- **本期仅允许选择 1536 维 embedding 模型**（OpenAI text-embedding-3-small / text-embedding-ada-002）
- 创建空间时 `embedding_model` 字段的下拉选项只显示 1536 维模型
- 配置变量从 `RAG_PG_VECTOR_DIM_MAX=3072` 改为 `RAG_PG_VECTOR_DIM=1536`（精确，不是上限）
- HNSW 索引 `m=16, ef_construction=64`，固定一个，无需按 space 动态建索引
- **v2 时再支持多维度**：通过按维度分表（`rag_chunk_d1536` / `rag_chunk_d3072`）实现

**理由**：
- 简单：单一维度避免所有 padding / 路由 / 分区的复杂度
- 1536 维已是当前主流 embedding 默认值，足够 MVP 验证业务价值
- 模型迁移目前只在"同维度模型"间发生（小→小 / large→large 待 v2 开放）；本期只允许小→小（如 text-embedding-3-small ↔ ada-002）

**影响 dev-design 修订**：
- §4.2 `rag_chunk.embedding` 改为 `vector(1536)` NOT NULL
- §4.2 `rag_space.embedding_model` 字段允许值约束加 CHECK 限定 1536 维模型
- §9 配置变量 `RAG_PG_VECTOR_DIM_MAX` 重命名为 `RAG_PG_VECTOR_DIM`，默认 1536
- §14 风险表新增"v2 支持多维度需分表改造"

### A4. 分区策略 → **A. 本期不分区**（采纳推荐）
- 预估行数不触发分区阈值
- §14 监控 + 500 万行预警机制已具备
- 代码中 `company_id` 始终作为过滤条件铺垫未来分区键

### A5. Migration 工具 → **A. 沿用手工 SQL**（已确认项目现状）

**已核实**：`CIOaas-python/sql/migrations/` 存在；命名约定 `YYYY-MM-DD_<purpose>.up.sql / .down.sql`（实例：`2026-05-26_llm_call_log_business_prefix.up.sql`）；无 Alembic。

**决策**：
- 本期新增的 migration 文件命名遵循同款：`2026-05-26_rag_001_alter_ai_files.up.sql` / `.down.sql`，依次 `rag_001..rag_008`
- 不引入 Alembic
- pgvector 扩展通过 `CREATE EXTENSION IF NOT EXISTS vector` 写入第二个 migration（`rag_002_create_extensions.up.sql`）
- 部署侧执行顺序由人工 / shell 脚本控制

**影响 dev-design 修订**：
- §13.1 明确路径 `CIOaas-python/sql/migrations/`
- 列出 8 个 migration 文件全名

### B1. BackgroundTasks 可靠性 → **A. 接受单机崩溃风险**（采纳推荐）
- 本期 MVP，运维成本优先
- cron 超时（`RAG_ENTRY_TIMEOUT_S=1800`）兜底 + 用户手动重试
- §14 风险表已明确"单实例部署期间模型迁移任务崩溃重启丢失是已知风险，可接受"
- **未来升级路径**：迁移任务从内存任务升级为"DB 状态机 + 重启续跑"（约 1-2 天工作量，作为 v1.x 改进项）

### B2. 并发迁移控制 → **A. SELECT FOR UPDATE**（采纳推荐）
- PG 原生，无额外依赖
- `space_service.update_space()` 整体已需事务，加 `FOR UPDATE` 自然
- 后续请求行锁等待 → 读到 MIGRATING → 返回 409 Conflict（code 40902）

### C1. RRF 与 ES hybrid → **B. 统一 Python 层 RRF**（采纳推荐）
- 两种后端行为一致便于测试与回归
- ES 后端不开 `hybrid=True`，分别调 `keyword_search` + `knn_search`，Python 端 RRF 融合
- ES 查询次数翻倍可接受（< 5s SLA 内）
- 若未来 ES 性能瓶颈再切回各自最优

**影响 dev-design 修订**：
- §6 ES `search()` 实现示例：分两次查再 RRF
- §10.2 RRF 应用于两种后端

### C2. 跨空间查询 SQL → **A. 并发单空间查询**（修正设计错误）

**这是 arch-designer 自审遗漏 + arch-questioner 发现的关键架构 bug**。`pg_store.search()` 必须改：
- 原设计：`WHERE space_id = ANY(...) ORDER BY embedding <-> $query LIMIT $top_k`（HNSW 不命中，退化 Seq Scan）
- 修正：`asyncio.gather([search_single_space(sid, query, top_k) for sid in space_ids])` 后 Python 层合并取 top_k
- 单空间 SQL：`WHERE space_id = $sid ORDER BY embedding <-> $query LIMIT $top_k`（HNSW 命中）

**影响 dev-design 修订**：
- §6 POST `/rag/search` 业务规则补充"跨空间在 Python 层并发，单空间 SQL 走 HNSW"
- §10.2 性能分析章节修正
- §7 检索时序图增加"跨空间分支"

### D1. OCR 选型 → **A. Textract 主 + GPT-4o vision 备**（采纳推荐）
- 复用现有 AWS 凭证
- 成本可控（Textract ≈ $0.0015/页）
- 中文支持 Textract 也能跑（精度低于专用中文 OCR，可在 §14 风险表说明）
- **前置条件**：确认生产 Textract 区域（建议 us-east-1）+ IAM 加 `textract:DetectDocumentText` + `textract:AnalyzeDocument`
- 优化预留：`RAG_OCR_PROVIDER` 可切 `vision`（GPT-4o vision via `source/llm/providers/`）

### D2. PARTIAL 重试保留 metadata → **A. 不预先清除**（采纳推荐）
- `ingest_service.retry_entry()`：保留 `entry.title / entry.file_id / status=PARTIAL`，运行新 pipeline
- 成功后 `UPDATE rag_entry SET status=SUCCESS, chunk_count=N`
- 失败后 `UPDATE rag_entry SET status=FAILED`（不保留 PARTIAL）
- 重试期间关键词召回不中断

**影响 dev-design 修订**：
- §6 POST `/rag/entries/{id}/retry` 业务规则补充

### E1. Embedding 是否写 llm_call_log → **A. 不写**（采纳推荐）
- `rag_entry.total_tokens` 直接落库
- `llm_call_log` 保留给 chat 调用
- `source/llm/providers/embeddings/` factory 不注入 tracer
- 若未来需要 embedding 成本审计，可选择性开启

### F1. 管理员角色判定 → **A. Java 注入 x-user-role 头**（采纳推荐）

**待 Java 侧确认（设计阶段不阻塞，留 TODO 进入开发阶段确认）**：
1. `x-user-role` 头是否已在 Java 网关 `/api/rag/**` 路由中注入
2. 管理员的 role 实际值（推测：`COMPANY_ADMIN` 或 `ADMIN`）
3. 若未注入，Java 侧需小改

**Python 端设计**：
- `require_user_context()` dependency 解析 `x-user-role`
- `ADMIN_ROLES = {"COMPANY_ADMIN", "ADMIN"}`（配置化）
- 不命中 admin 时按 普通用户 处理

**影响 dev-design 修订**：
- §11.1 鉴权章节明确 header 名 + role 值
- §15 风险与遗留项加 "Java 网关确认 x-user-role 注入"

### G1. pgvector 生产安装 → **A. RDS PG**（采纳推荐 + 加部署 checklist）

**部署 checklist（dev-design §13 增加）**：
- ☐ 确认生产 PG 部署方式（RDS / 自建 / Aurora）
- ☐ 确认 PG 版本 ≥ 14.5 / 15.2 / 16（支持 pgvector）
- ☐ 确认 pgvector 版本 ≥ 0.5.0（支持 HNSW）
- ☐ 确认执行账号有 `CREATE EXTENSION` 权限（RDS 需 `rds_superuser` 角色）

**如果生产是自建 PG**：OS 层安装 `apt install postgresql-15-pgvector` 后再 `CREATE EXTENSION`

### G2. ai_files.task_id 可空风险 → **B. DB CHECK 约束**（升级推荐方案）

**采纳 arch-questioner 提出的方案 B**（比原推荐方案 A 更安全）：

```sql
-- migration: 2026-05-26_rag_001_alter_ai_files.up.sql
-- 步骤 1：增加 purpose 字段，默认 'financial_extract'
ALTER TABLE ai_files ADD COLUMN purpose VARCHAR(30) NOT NULL DEFAULT 'financial_extract';

-- 步骤 2：回填（已有数据全部是 financial_extract）
-- UPDATE ai_files SET purpose='financial_extract' WHERE purpose IS NULL;  -- DEFAULT 已覆盖

-- 步骤 3：放松 task_id 约束
ALTER TABLE ai_files ALTER COLUMN task_id DROP NOT NULL;

-- 步骤 4：增加 CHECK 约束防止财务模块回归
ALTER TABLE ai_files ADD CONSTRAINT chk_ai_files_purpose_task CHECK (
    (purpose = 'rag' AND task_id IS NULL) OR
    (purpose = 'financial_extract' AND task_id IS NOT NULL)
);

-- 步骤 5：建索引
CREATE INDEX idx_ai_files_purpose ON ai_files(purpose);
```

**前置验证**：开发阶段需在 Java 仓库 grep 所有 `INSERT INTO ai_files` / `JPA save AiFile` 的代码路径，确认都传了 `task_id`（避免 CHECK 约束违反）。

**影响 dev-design 修订**：
- §4.1 ai_files 扩展章节用上述完整 SQL 替换
- §13 部署 checklist 增加"Java 财务模块代码路径 grep 确认"

### H1. BackgroundTasks Sentry 追踪 → **A. sentry_sdk.new_scope**（采纳推荐）

```python
# background/pipeline_runner.py
import sentry_sdk

async def run_file_entry(entry_id: str):
    with sentry_sdk.new_scope() as scope:
        scope.set_tag("entry_id", entry_id)
        scope.set_tag("space_id", ...)
        scope.set_tag("company_id", ...)
        scope.set_tag("pipeline", "file_ingest")
        try:
            await _do_pipeline(entry_id)
        except Exception:
            sentry_sdk.capture_exception()
            raise
        finally:
            sentry_sdk.flush(timeout=2.0)
```

迁移 runner 同理。

## 三、自动头脑风暴补充（arch-questioner 未问但需要明确）

### 补充 1：esapiens 代码搬入的具体落点

**决策**：把 `esapiens-python/esapiens/embedding_pipeline/` 复制到 `CIOaas-python/source/rag/vectorizer/`，并做以下本地化：

| 原 esapiens 位置 | 新位置 | 本地化要点 |
|---|---|---|
| `document_loaders/` | `source/rag/vectorizer/loaders/` | 去掉 `sapien_id` / `paper_drawer` 等业务遗留；改用 `rag_space_id` / `rag_entry_id`；图片 loader 增加 OCR 调用 |
| `text_splitting/` | `source/rag/vectorizer/splitters/` | 直接复用，无业务字段 |
| `embedding_vectorization/embedding_manager.py` | 废弃 | 改走 `source/llm/providers/embeddings/factory.py`，不再单例 OpenAIEmbeddings |
| `embedding_storage/es_storage.py` | `source/rag/storage/es_store.py` | 元数据字段重命名（`botFileId` → `entry_id`, `sapienId` → `space_id`, `tenantId` → `company_id`）；删除 paper_drawer 分支；删除 publish/delete flag |
| `embedding_storage/csv_storage.py` | 不搬 | 测试用，本期不需要 |
| `vectorization_enum.py` | `source/rag/vectorizer/file_types.py` | 删除 `paper_drawer` 训练类型 |

**Python import 注意**：esapiens 代码引用了 `esapiens.common.*` / `esapiens.vectore.*` / `config.config`，搬入时全部替换为 CIOaas-python 的等价：
- `esapiens.common.logging_config.logging` → `from common.logger import setup_logger`
- `esapiens.vectore.common.num_tokens_from_string` → 新写一个简单工具或用 `tiktoken`
- `esapiens.vectore.common.get_es_client` → 走 `source/rag/storage/es_store.py` 的 client 工厂
- `esapiens.integrations.datasource_manager.get_tenant_elasticsearch_config` → 走 `os.environ` 配置（部署期单选，不做租户级动态）
- `config.config.config.ES_API_KEY` → `os.environ['RAG_ES_API_KEY']`

### 补充 2：embedding 调用并发与限流

- 默认 OpenAI embedding 单批最多 96 inputs（按 OpenAI API 限制）
- 默认 token 配额 1M TPM（按账号配置）
- `embedder.py` 实现自己的批次分片 + 重试（指数退避，3 次）+ 限流（基于 semaphore，并发上限 8）
- 失败重试上限达到后，向 pipeline_runner 抛 `EmbeddingError`，pipeline 把整个 entry 标 FAILED

### 补充 3：检索 API 的鉴权降级

- 默认要求 `x-user-id` header
- 缺失时返回 401，不允许"匿名"调用
- 与 F1 决策一致（系统调用方 Chatbot 必须携带用户身份，对应需求 A5=A）

### 补充 4：文件大小校验的执行位置

按 standards/coding.md 安全规则：
- 上传链路：Java 网关在颁发 S3 预签名时校验 `content_length` 不超 `RAG_MAX_FILE_SIZE_MB=50`
- Python 收到 `POST /rag/files` 时再次按 `file_id` 反查 `files.length` 校验
- S3 桶策略也限制单个 PUT 大小

### 补充 5：测试数据 fixtures

- `tests/rag/fixtures/` 放最小化测试文件（每种类型一个，1-2 KB）
- mock OpenAI embedding：用预生成的固定向量 fixtures，不真调 API
- mock OCR：mock 返回固定文本
- 集成测试用 `testcontainers-postgresql` + `pgvector` 镜像

### 补充 6：S3 文件名编码兼容

文件名含中文 / 空格的场景，S3 key 应 URL-encode 但 entry.title 保留原始名。`pipeline_runner` 下载 S3 时按 `files.name` （已 encode 的 S3 key），展示时用 `files.original_name`。

## 四、未拍板项 / 待开发阶段确认

| 项目 | 何时确认 | 默认假设 |
|---|---|---|
| 生产 PG 版本 + pgvector 版本 | 部署前由运维确认 | 假设 ≥ 0.5.0 |
| Java 网关注入 `x-user-role` 与 admin role 值 | 开发阶段 Java 侧确认 | 假设值为 `COMPANY_ADMIN` |
| 生产 AWS Textract 区域 | 部署前运维确认 | 假设 us-east-1 |
| Java 财务模块写 ai_files 是否都传 task_id | 开发前 grep 确认 | 假设都传 |

## 五、本次决策对设计文档的修订指引（给 arch-designer 修正定稿）

按以下编号修订 `dev-design-doc.md`：

1. **§4.2 `rag_chunk` DDL** — `embedding` 改为 `vector(1536)` NOT NULL；删除 `embedding_version` 与维度相关复杂度（v2 再考虑）
2. **§4.2 `rag_space` DDL** — `embedding_model` 字段加 CHECK：只允许 `('text-embedding-3-small', 'text-embedding-ada-002')`
3. **§4.1 ai_files 扩展** — 完整 SQL 替换为 tech-answers §G2 的 5 步迁移
4. **§4 总览** — 修正"多维度支持"的描述为"本期固定 1536 维"
5. **§6 检索 API** — 业务规则补充"跨空间 Python 层并发，单空间 SQL 走 HNSW；ES 后端分两次查再 Python RRF"
6. **§6 重试 API** — 业务规则补充"PARTIAL 条目重试时保留 metadata，不预先清除"
7. **§7 检索时序图** — 新增跨空间分支 `asyncio.gather`
8. **§9 配置变量** — `RAG_PG_VECTOR_DIM_MAX` 重命名为 `RAG_PG_VECTOR_DIM=1536`
9. **§10 性能** — 跨空间策略段更新；HNSW 索引参数固定为 `m=16, ef_construction=64`
10. **§11 安全** — 明确 `x-user-role` 头解析逻辑 + `ADMIN_ROLES` 白名单
11. **§13 部署** — 增加 4 项 checklist（PG 版本 / pgvector 版本 / CREATE EXTENSION 权限 / Java 财务模块 grep）
12. **§13 migration** — 路径明确为 `CIOaas-python/sql/migrations/`；文件名遵循 `YYYY-MM-DD_rag_NNN_*.up.sql/.down.sql`
13. **§14 风险** — 新增三条：① v2 支持多维度需分表改造；② 中文 OCR 精度低于专用方案；③ BackgroundTasks 单机崩溃风险已知可接受
14. **§5 模块结构** — `source/rag/vectorizer/` 增加 `ocr/` 子目录（Textract / Vision Provider）
15. **§5 模块结构** — 补充 esapiens 搬入映射表（tech-answers §补充 1）
16. **§15 待决断** — 改名为"已决断疑点 + 待开发阶段确认项"，将 16 个疑点的决策结果摘要列出 + 待确认的 4 项
17. **整体** — 全文检索"待澄清"/"TBD"/"待定"字样并消除
