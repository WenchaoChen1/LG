# RAG 管理 — 设计文档审查报告

## 审查信息

| 项目 | 内容 |
|---|---|
| 审查对象 | `features/rag/dev-design/dev-design-doc.md` v1.1（终稿） |
| 对照基准 | `requirement/requirement-doc.md` v1.2；`dev-design/tech-questions.md`；`dev-design/tech-answers.md` |
| 适用规范 | `CIOaas-python/standards/architecture.md`；`CIOaas-python/standards/coding.md` |
| 审查人 | Architect Team / arch-reviewer |
| 审查日期 | 2026-05-26 |

---

## 审查结论

**[x] PASS WITH WARNINGS**

- CRITICAL（阻塞，必须修复）：**2 项**
- HIGH（强烈建议修复）：**4 项**
- MEDIUM（应修复）：**5 项**
- LOW（可选优化）：**3 项**

---

## 修订建议（按严重度）

### CRITICAL（阻塞，必须修复）

---

**CRITICAL-1：模型迁移原子切换的 3 步跨调用事务边界未定义（§7.3）**

**问题**：§7.3 时序图迁移完成序列为：
1. `UPDATE rag_space SET current_embedding_version=2, status=READY`（PG 事务）
2. `store.delete_by_space_version(space_id, version=1)`（外部调用 — pgvector DELETE 或 ES delete_index，不在 PG 事务内）
3. `UPDATE rag_migration_task SET status=SUCCEEDED`

步骤 1 和 3 是否在同一 PG 事务中原子提交？未说明。若步骤 1 提交后服务崩溃，产生以下不一致状态：
- `rag_space.status=READY / current_embedding_version=2` 已生效（检索走 version=2，正确）
- 旧向量（version=1）未清理，占用存储
- `rag_migration_task.status` 仍为 `RUNNING`，cron 超时后误标 FAILED，而空间已 READY，状态机不一致
- 用户再触发 PUT 切换模型时，空间已 READY，可创建新迁移任务，但旧向量遗留无法被 cron 清理

**建议**：在 §7.3 明确定义如下事务边界：
1. 步骤 1（`UPDATE rag_space`）+ 步骤 3（`UPDATE rag_migration_task SET status=SUCCEEDED`）在同一 PG BEGIN...COMMIT 事务内原子提交
2. 步骤 2（向量清理 `delete_by_space_version`）在步骤 1+3 事务提交后异步执行，失败允许重试（`delete_by_space_version` 实现为幂等 DELETE）
3. 若向量清理失败，不回滚步骤 1+3（迁移已完成），而是记录日志 + 后台定期重试清理

这是可安全实现的幂等设计，约需 0.5 天补充说明，是开发阶段的前置条件。

---

**CRITICAL-2：`rag_migration_task` 缺少心跳 / 超时机制，RUNNING 任务永久悬空（§4.2.6 / §11.6 / §14）**

**问题**：`§11.6` cron 机制只处理 `rag_entry.status='PROCESSING'` 的超时，将其标为 FAILED。但 `rag_migration_task.status='RUNNING'` 无对等的超时恢复机制。

崩溃场景：迁移 BackgroundTasks 进程崩溃后，`rag_space.status=MIGRATING` 和 `rag_migration_task.status=RUNNING` 永久停留，导致：
- 用户无法再触发新迁移（`PUT /rag/spaces/{id}` 返回 `40902 空间状态不支持该操作`）
- 唯一恢复路径是平台运维手动修改 DB，用户端无法自助
- §14 风险表仅说明"BackgroundTasks 单机崩溃风险已知可接受"，但未提供迁移任务的超时恢复路径

这与已有的 B1 决策（cron 兜底入库任务）不对称。入库任务有 `RAG_ENTRY_TIMEOUT_S=1800` 兜底，迁移任务却无等效机制。

**建议**：

1. 在 `rag_migration_task` DDL（§4.2.6）新增字段：
   ```sql
   heartbeat_at TIMESTAMP WITH TIME ZONE,  -- migration_runner 每 N 个 entry 更新一次
   timeout_s    INTEGER NOT NULL DEFAULT 14400  -- 默认 4 小时超时（可配置 RAG_MIGRATION_TIMEOUT_S）
   ```
2. `migration_runner.py` 每处理 50 个 entry（或每分钟）执行一次 `UPDATE rag_migration_task SET heartbeat_at=now() WHERE id=$1`
3. cron（§11.6 基础上扩展）扫描 `status='RUNNING' AND heartbeat_at < now() - interval '10 min'`，标为 FAILED 并同步将 `rag_space.status` 改回 `MIGRATION_FAILED`
4. 用户可通过现有 `POST /rag/migrations/{id}/retry` 恢复

预估工作量：约 1 天，建议在开发阶段第一周完成。

---

### HIGH（强烈建议修复）

---

**HIGH-1：HNSW `ef_search` 环境变量已定义，但运行时 SET LOCAL 的注入层次未明确（§9 / §10.1）**

**问题**：`RAG_HNSW_EF_SEARCH=40` 已在 §9 配置表定义，§10.1 也提到"运行时 `SET LOCAL hnsw.ef_search = 40`"，但未明确：

- 在哪一层执行（路由层？service 层？`pg_store.search_single_space()` 内？）
- pgvector 的 `hnsw.ef_search` 是连接级 / 事务级参数，在 `asyncio.gather` 并发调用场景下，`SET LOCAL` 必须在同一 transaction/connection 上下文内才生效
- 小空间（< 1000 chunks）场景下，`ef_search=40` + `top_k * 3` over-fetch 组合在极端情况下仍可能召回不足 top_k，over-fetch 不足时设计没有明确处理策略（接受 < top_k 返回？还是触发 fallback？）

**建议**：在 §5 或 §6.2.9 补充实现规范：
```python
# pg_store.search_single_space() 内
async with session.begin():
    await session.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))
    results = await session.execute(
        text("SELECT ... ORDER BY embedding <-> :vec LIMIT :limit"),
        ...
    )
```
明确 `ef_search` 在每次 `search_single_space()` 调用时注入，并说明 over-fetch 不足时的行为（接受少于 top_k 的结果，不触发 Seq Scan fallback）。

---

**HIGH-2：CHECK 约束缺少数据层面前置验证方案，`NOT VALID` 灰度策略缺失（§4.1.1 / §13.4）**

**问题**：§4.1.1 步骤 4 直接执行：
```sql
ALTER TABLE ai_files ADD CONSTRAINT chk_ai_files_purpose_task CHECK (
    (purpose = 'rag' AND task_id IS NULL) OR
    (purpose = 'financial_extract' AND task_id IS NOT NULL)
);
```

PostgreSQL `ADD CONSTRAINT CHECK` 行为：默认会扫描全表验证所有已有行是否满足约束。若存在**任何一行** `purpose='financial_extract' AND task_id IS NULL`（例如 Java 某异常分支历史遗留），该 migration 将直接 FAIL 并 ROLLBACK，导致整个 migration 流程中断。

§13.4 checklist 只有"grep Java 代码路径确认"，是代码层面验证，没有**数据层面验证**（历史数据中可能已存在违反行）。

**建议**：在 migration 脚本步骤 4 之前加验证步骤，并在 `.up.sql` 注释中标注：
```sql
-- 步骤 4a（验证，约束加前必须确认此查询返回 0）：
-- SELECT COUNT(*) FROM ai_files WHERE purpose != 'rag' AND task_id IS NULL;
-- 若 > 0，需先修数据（UPDATE ai_files SET task_id=... WHERE ...）再执行步骤 4

-- 步骤 4b（推荐使用 NOT VALID 灰度方案）：
ALTER TABLE ai_files ADD CONSTRAINT chk_ai_files_purpose_task CHECK (
    (purpose = 'rag' AND task_id IS NULL) OR
    (purpose = 'financial_extract' AND task_id IS NOT NULL)
) NOT VALID;

-- 步骤 4c（低峰期异步验证，不锁表）：
ALTER TABLE ai_files VALIDATE CONSTRAINT chk_ai_files_purpose_task;
```
`NOT VALID` 方案允许 migration 在不全表扫描的情况下先添加约束（新写入立即校验），再在低峰期 `VALIDATE`（仅扫描老数据）。

---

**HIGH-3：`POST /rag/migrations/{id}/retry` 接口在汇总表中存在但无详细 Schema 定义（§6.1 vs §6.2）**

**问题**：§6.1 接口汇总表第 18 行列出了 `POST /rag/migrations/{id}/retry`，但 §6.2 的详细 Schema 章节（6.2.1 ~ 6.2.13）中：
- §6.2.11 定义的是 `POST /rag/spaces/{id}/migrate`（按空间触发迁移）
- §6.2.13 定义的是 `GET /rag/migrations/{id}`（查询迁移进度）
- **`POST /rag/migrations/{id}/retry` 没有独立的详细定义**

此外，§6.2.11 说明"留空时 = 重新执行最近一次失败的迁移"，但其 Request 是 `POST /rag/spaces/{id}/migrate`（按空间 ID），而汇总表中 `POST /rag/migrations/{id}/retry` 是按迁移任务 ID 重试。两者语义相近但路径不同，可能造成实现歧义。

**建议**：在 §6.2 补充 `POST /rag/migrations/{id}/retry` 的规范，包括：
- Request：空 body 或可选 `force: bool`
- Response：`{ data: { migrationId, status: "RUNNING" } }`
- 业务规则：校验 migration task 状态为 FAILED；复用原 task 的 from_model/to_model；在事务内 `SELECT rag_space FOR UPDATE` + 校验 status=MIGRATION_FAILED；reset `completed_entries=0, failed_entries=0, status=RUNNING`；启动 BackgroundTasks

---

**HIGH-4：`GET /rag/entries`、`GET /rag/entries/{id}` 接口缺少详细 Schema 定义（§6.1 vs §6.2）**

**问题**：§6.1 接口汇总表列出以下接口，但 §6.2 详细 Schema 章节中**均无对应定义**：
- `GET /rag/entries`（条目列表，按 space 过滤）
- `GET /rag/entries/{id}`（条目详情）

这两个接口是前端条目管理页面的核心接口，条目列表需要展示：status、sourceType、title、chunkCount、hitCount、fileSize、createdAt 等字段；条目详情需要额外展示：processingStage、errorMessage（需求 §6.3 规则 1 要求"可理解的失败原因"）。

缺少 Schema 定义导致前后端无法对齐，影响开发启动。

**建议**：在 §6.2 补充：

`GET /rag/entries` Query 参数：`spaceId`（必填）、`status`（可选过滤）、`sourceType`（可选）、`keyword`（标题模糊搜索）、`limit`、`offset`

`EntryBriefData`（列表项）：
```python
class EntryBriefData(BaseModel):
    entryId: str
    title: str
    sourceType: Literal["FILE", "TEXT"]
    status: str              # PROCESSING / SUCCESS / PARTIAL / FAILED
    chunkCount: int
    hitCount: int
    fileSizeBytes: Optional[int]
    mimeType: Optional[str]
    embeddingVersion: int
    createdAt: str
    updatedAt: str
```

`EntryDetailData`（详情，继承 EntryBriefData 并扩展）：
```python
class EntryDetailData(EntryBriefData):
    taskId: Optional[str]
    chunkSizeUsed: int
    chunkOverlapUsed: int
    totalTokens: int
    processingStage: Optional[str]  # download / ocr / split / embed / store
    errorMessage: Optional[str]
```

---

### MEDIUM（应修复）

---

**MEDIUM-1：`rag_search_log.space_ids` PG 数组类型的 ORM 映射方式未说明（§4.2.5）**

DDL 中 `space_ids VARCHAR(36)[] NOT NULL` 为 PostgreSQL 原生数组类型。SQLAlchemy 映射需使用 `from sqlalchemy.dialects.postgresql import ARRAY`；若开发者误用 `JSON` 类型，GIN 索引（`&&` / `@>` 操作符）会失效，影响热门 query 聚合性能。

建议在 §4.2.5 或 §5 db/models 补充 ORM 代码片段：
```python
from sqlalchemy.dialects.postgresql import ARRAY
space_ids = Column(ARRAY(String(36)), nullable=False)
```

---

**MEDIUM-2：`rag_entry.file_id` 与 `ai_files` 的关联类型（软关联 vs FK）未明确（§4.2.3）**

DDL 中 `file_id VARCHAR(36)` 注释为"source_type=FILE 时填 ai_files.file_id"，但无 `REFERENCES ai_files(id)` FK 约束，这与 `rag_entry REFERENCES rag_space(id)` 有 FK 的做法不一致。

是有意设计（软关联，因 ai_files.purpose='rag' 与 rag_entry 一对一，避免外键级联复杂度）还是遗漏？需在 §4.2.3 明确标注，例如：
> `file_id` 为软关联（无 FK）。删除条目时由 `entry_repo` 显式软删对应 ai_files 行，不依赖 DB CASCADE。

---

**MEDIUM-3：迁移期间"新上传使用新 embedding_version"的实现字段缺失（§7.3 / §4.2.1）**

§7.3 注释提到：
> "新上传：直接走 version=2（pipeline 读 space.target_embedding_version_pending）"

但 `rag_space` DDL（§4.2.1）中**没有 `target_embedding_version_pending` 字段**。`pipeline_runner` 在空间 `status=MIGRATING` 时需要知道"新上传该用哪个 embedding version"，但无法从 DDL 中找到存储位置。

可选实现路径：
- 方案 A：`rag_space` 加字段 `pending_embedding_version INTEGER`，迁移开始时写入目标版本号
- 方案 B：`pipeline_runner` 查 `rag_migration_task WHERE space_id=? AND status='RUNNING'` 得到 `to_version`

两种方案均可接受，但必须在 §4.2.1 或 §7.3 明确选择并定义实现，否则开发者无法实现"迁移不阻塞新上传"这条核心功能（对应需求 §4.1.4 规则 3 和验收标准第 9 条）。

---

**MEDIUM-4：`rag_ingestion_task` 缺少整体 status 字段（§4.2.2 / §6.2.7）**

`rag_ingestion_task` 表有各分类计数（processing_count / success_count / partial_count / failed_count），但没有整体 `status VARCHAR(16)` 字段（如 `PROCESSING / COMPLETED`）。

`GET /rag/tasks/{id}` 的 `IngestionTaskData`（§6.2.7）也没有任务级别整体状态字段。前端需要判断"整批任务是否全部处理完"，当前只能由客户端计算 `total == success+partial+failed`，且需要 entries 中所有项均非 PROCESSING 状态才能确认完成——这增加了前端轮询逻辑复杂度，且在"total_count 更新时机"边界场景下容易误判。

建议在 `rag_ingestion_task` 加 `status VARCHAR(16) NOT NULL DEFAULT 'PROCESSING'`，入库管线在所有 entries 处理完成后将 task 更新为 `COMPLETED`，并在 `IngestionTaskData` response 中暴露该字段。

---

**MEDIUM-5：`topK` 的 Pydantic 校验与业务错误码 `40004` 重叠，分工不明确（§6.2.9 vs §8.2）**

`SearchRequest.topK = Field(5, ge=1, le=20)` 的 Pydantic 校验失败时，FastAPI 自动返回 HTTP 422（Unprocessable Entity），不会触发业务层的 `40004`。

§8.2 错误码表中单独定义了 `40004: 检索 topK 超过 20`，但在 Pydantic `le=20` 约束下，该错误码永远不会被触发（`le` 约束先于业务层生效）。

需说明：
- `40004` 是否为 Pydantic 校验失败（422）的别名（前端统一解析），或
- `topK` 的 `le=20` 应改为无约束，由 service 层判断并返回 `40004 + HTTP 400`

整个错误码体系中"Pydantic 校验产生 422 vs 业务层返回 400+自定义 code"的分工边界没有在 §8 说明，建议补充一段说明。

---

### LOW（可选优化）

---

**LOW-1：§13.3 新增依赖未给出版本号，与 coding.md §13 要求不一致**

§13.3 步骤 4 提到将以下库加入 requirements.txt：pdfplumber、python-docx、openpyxl、ebooklib、Pillow、langchain-text-splitters、langchain-elasticsearch——但均未提供版本号。

`coding.md §13` 要求 `requirements.txt` 用 `==` 精确锁定版本。设计文档中建议补注："版本号在开发阶段第一天对照 esapiens 现有安装版本确认后锁定，并通过 `pip audit` 检查 CVE"。

---

**LOW-2：`GET /rag/stats/entries/{id}` 接口缺少 Response Schema（§6.1 vs §6.2）**

§6.1 接口汇总表列出 `GET /rag/stats/entries/{id}`，但 §6.2 详细 Schema 只有 `GET /rag/stats/spaces/{id}`（`SpaceStatsData`），无 entry 级别统计的 Response 定义。

需求 §4.6.3 要求：条目被命中次数（累计）+ 被命中最多的片段排行。建议补充：
```python
class EntryStatsData(BaseModel):
    entryId: str
    hitCount: int                      # 累计被命中次数（永久保留）
    topHitChunks: List[dict]           # [{chunkId, seq, contentPreview, hitCount}]
```

---

**LOW-3：`rag_chunk.metadata JSONB` 字段内容约定缺失（§4.2.4）**

`metadata JSONB NOT NULL DEFAULT '{}'` 定义了字段，但各 loader 写入的 metadata schema 未定义（例如 pdf_loader 可能写 `page_number`、excel_loader 写 `sheet_name / row_range`、image_loader 写 `ocr_confidence`）。

后续若需要"按页码过滤"或"展示文档结构位置"，metadata 约定缺失会导致各 loader 自由发挥，schema 蔓延无法统一查询。建议在 §5 vectorizer/loaders 或 §4.2.4 附注最小 metadata schema 约定：
```json
{
  "page": 1,              // PDF / 图片类，页码（1-based）
  "sheet": "Sheet1",      // Excel/CSV，表名
  "source_path": "...",   // 原始文件相对路径
  "ocr_provider": "textract"  // 图片类，OCR 提供者
}
```

---

## 完整性核对

### 16 个技术疑点落实核查

| 编号 | 疑点 | 设计文档落点 | 状态 |
|---|---|---|---|
| A1 | HNSW 索引类型（`m=16, ef_construction=64`） | §4.2.4 DDL + §9 `RAG_HNSW_*` 变量 | 落实 |
| A2 | ES 索引粒度（公司+版本） | §4.3.1 命名约定 + §4.3.2 Mapping | 落实 |
| A3 | vector 固定 1536 维，不做 padding | §4.2.4 `vector(1536)`；§4.2.1 CHECK 约束；§9 `RAG_PG_VECTOR_DIM=1536` | 落实 |
| A4 | 本期不分区 | §14 风险表"超 500 万行再分区" | 落实 |
| A5 | 沿用手工 SQL migration | §13.1 路径 `sql/migrations/` + 8 个文件名 | 落实 |
| B1 | BackgroundTasks + cron 超时兜底 | §11.6 cron 机制；§14 已知风险说明 | 落实（但 CRITICAL-2 要求扩展到迁移任务） |
| B2 | SELECT FOR UPDATE 并发控制 | §6.2.3 业务规则；§7.3 时序图 | 落实 |
| C1 | 统一 Python 层 RRF，ES 关闭 hybrid | §6.2.9 规则 4；§10.1 RRF 融合 | 落实 |
| C2 | asyncio.gather 并发单空间查询 | §6.2.9 规则 3；§7.2 时序图；§10.2 | 落实 |
| D1 | Textract 主 + GPT-4o vision 备 | §5 `vectorizer/ocr/` 子目录；§13.4 checklist | 落实 |
| D2 | PARTIAL 重试保留 metadata 不预清除 | §6.2.12 业务规则；§7.4 时序图 | 落实 |
| E1 | Embedding 不写 llm_call_log | §8.4 日志要求；§5.1 EmbeddingClient 注释 | 落实 |
| F1 | Java 注入 x-user-role + ADMIN_ROLES 白名单 | §11.1 鉴权；§9 `RAG_ADMIN_ROLES` 变量 | 落实 |
| G1 | RDS PG + 部署 checklist | §13.4 部署 checklist（4 项版本验证） | 落实 |
| G2 | DB CHECK 约束（5 步迁移） | §4.1.1 完整 DDL；§4.1.2 ORM 同步 | 落实（HIGH-2 要求补充 NOT VALID 方案） |
| H1 | BackgroundTasks Sentry new_scope | §10.3 监控埋点；§7.1 / §7.3 引用 | 落实 |

**16/16 全部落实**

### 需求 v1.2 功能覆盖核查

| 功能 | 需求节 | 设计覆盖情况 |
|---|---|---|
| F1 RAG空间管理 | §4.1 | §6.2.1~6.2.4 + §4.2.1 + §7.3 — 完整覆盖 |
| F2 文件入库 | §4.2 | §6.2.5 + §7.1 + §4.2.2~4.2.3 — 完整覆盖 |
| F3 文本直传入库 | §4.3 | §6.2.6 — 覆盖 |
| F4 条目读取与拆分（可参数化） | §4.4 | §6.2.8 片段预览 + §9 chunk 环境变量 — 覆盖 |
| F5 检索 | §4.5 | §6.2.9 + §7.2 + §10 — 完整覆盖（含跨空间、权限裁剪、PARTIAL 条目） |
| F6 使用统计 | §4.6 | §6.2.10（空间统计有完整 Schema）— 部分覆盖（entry 统计接口 Schema 缺失，见 HIGH-4 / LOW-2） |
| F7 配置与维护 | §4.7 | §6.2.12（重试）+ §11.5（软删除）+ §11.6（超时）— 覆盖 |

**功能覆盖：6.5/7（F6 entry 维度统计接口 Schema 缺失）**

### TBD/待澄清残留

全文无"待澄清"/"TBD"/"待定"字样残留。§15.2 的 4 项"待开发阶段确认"是有意保留的前置确认项，已明确默认假设与确认时机，不属于设计遗留。

---

## 规范符合度

### standards/architecture.md

| 检查项 | 结果 |
|---|---|
| `source/{module}/{routes,dto,service}` 三层结构 | 符合（§5 目录结构完整） |
| `dto/request.py / response.py / dto.py` 三层分离 | 符合（§6.2 所有 Schema 按层放置） |
| 路由层 `Request → DTO → Service → DTO → Response` 数据流 | 符合（§5.1 明确约定） |
| VectorStore Protocol / EmbeddingClient Protocol（duck typing） | 符合（§5.1 两个 Protocol 定义） |
| BackgroundTasks 异步处理模式与现有模块一致 | 符合（与 lg/ 模块模式一致） |
| 路由挂载方式（app.include_router） | 符合（§5.2 明确） |

**结论：符合 architecture.md**

### standards/coding.md

| 检查项 | 结果 |
|---|---|
| 响应信封 `{ success, code, message, data }` | 符合（所有 Response 类均包含四字段） |
| JSON key lowerCamelCase | 符合（所有 DTO 字段均为 lowerCamelCase） |
| 时间格式 `"yyyy-MM-dd HH:mm:ss"` UTC | 部分符合（字段类型为 `str`，但 DTO 注释未说明格式；建议在 `Field(description="ISO8601 UTC, yyyy-MM-dd HH:mm:ss")` 补充） |
| 所有路由 `async def` | 符合（§6 明确声明） |
| Pydantic BaseModel + `@model_validator` | 符合（chunk_overlap < chunk_size 校验已定义） |
| `path.resolve()` + 目录白名单 | 符合（§11.3 `/tmp/rag-ingest/` 白名单） |
| `pool_size / max_overflow` 显式配置 | 符合（§10.1 `pool_size=10, max_overflow=10`） |
| `timeout=60s + 指数退避 3 次` | 符合（§8.3 重试策略表） |
| 日志不输出 PII/key/密码 | 符合（§8.4 + §11.4 明确限制） |
| `requirements.txt` 用 `==` 精确锁定 | 部分符合（新增依赖未给版本号，见 LOW-1） |
| 测试覆盖率 ≥ 80% | 符合（§12.4 目标定义） |
| 金额用 Decimal | 不适用（本项目无金额字段） |
| 错误处理：路由 HTTPException，服务 ValueError/RuntimeError | 符合（§8.1 分级说明） |

**结论：基本符合 coding.md（2 项细节需补充）**

---

## arch-designer 自审疑点的验证结论

### 5.1 HNSW + filter 交互（§4.2.4 / §10.2）

- `RAG_HNSW_EF_SEARCH=40` 已定义，§10.1 提到运行时注入 `SET LOCAL`，但 `pg_store.py` 实现层次未说明（HIGH-1）
- `top_k * 3` over-fetch 缓解机制存在，但 over-fetch 不足时的处理策略未说明（HIGH-1）
- pgvector 0.8+ iterative scan 未提及，属于未来优化项，不作为本期阻塞
- 跨空间 `asyncio.gather` + 单空间 `WHERE space_id=$1` 设计正确，解决了 HNSW filter 限制

**结论**：ef_search 注入实现层次需补充（HIGH-1），其余正确

### 5.2 ai_files CHECK 约束灰度（§4.1.1）

- `NOT VALID` 灰度方案缺失（HIGH-2）
- 数据层面验证（预查历史违反行）缺失（HIGH-2）
- Java 端 grep 确认已在 §13.4 checklist 和 §15.2 列出，是代码层面的充分条件，但无法替代数据层验证

**结论**：需补充 NOT VALID 灰度方案（HIGH-2）

### 5.3 模型迁移原子切换 + 心跳（§7.3 / §14）

- 3 步切换的事务边界未定义（CRITICAL-1）
- `heartbeat_at` 字段 `rag_migration_task` 缺失（CRITICAL-2）
- `rag_space` 缺少 `pending_embedding_version` 相关字段，导致"迁移期间新上传走新模型"实现路径不完整（MEDIUM-3）

**结论**：3 项均需修复，其中 CRITICAL-1/2 是开发前置条件

---

## 总体评价

### 优点

1. **技术疑点全部落实**：16/16 项技术决策均在文档中明确体现，无 TBD 残留，文档完成度高于同类设计文档
2. **数据模型设计扎实**：索引策略（HNSW + trigram GIN + 复合索引）覆盖全部查询路径；DDL 约束（CHECK / UNIQUE INDEX / PARTIAL INDEX）精细设计
3. **检索策略正确**：`asyncio.gather` 并发单空间查询有效解决 pgvector HNSW 的多值 filter 限制；Python 层统一 RRF 保证两套后端行为一致
4. **安全设计完整**：多租户 company_id 强制过滤（§11.2）、路径白名单（§11.3）、MIME+扩展名双校验、Chatbot 代用户必须携带身份——完整覆盖需求 §5 权限矩阵
5. **esapiens 代码搬入映射表详细**：§5.3 给出逐文件映射和 import 本地化要点，开发者可直接执行
6. **异常处理分级清晰**：用户错误/系统错误/第三方错误三级，错误码命名规则统一（`HTTP * 100 + seq`）

### 主要风险

1. **迁移状态机完整性**（CRITICAL-1/2 + MEDIUM-3）：原子切换边界、心跳超时、新上传使用版本路由三处设计不完整，是"切换 embedding 模型"核心功能能否安全运作的根本保障
2. **接口 Schema 不完整**（HIGH-3/4 + LOW-2）：3 个接口（`POST /rag/migrations/{id}/retry`、`GET /rag/entries`、`GET /rag/entries/{id}`）及 entry 统计接口缺少详细定义，影响前后端对齐
3. **CHECK 约束灰度风险**（HIGH-2）：生产迁移时可能因历史数据违反约束而 migration 失败，需在低风险方案（NOT VALID）和数据层面前置验证上补充

### 建议下一步

| 优先级 | 行动 | 责任方 | 预计时长 |
|---|---|---|---|
| P0（开发前必须） | 修复 CRITICAL-1（定义迁移切换事务边界）+ CRITICAL-2（添加 heartbeat_at + cron 机制）+ MEDIUM-3（补充 `pending_embedding_version` 字段） | arch-designer | 1 天 |
| P1（开发第一周同步） | 修复 HIGH-4（补充 entries 接口 Schema）+ HIGH-3（补充 migrations/retry Schema）+ HIGH-2（NOT VALID 方案） | arch-designer | 0.5 天 |
| P2（开发阶段跟进） | 修复 MEDIUM-1/2/4/5 + HIGH-1 | dev-backend | 开发阶段内嵌 |
| P3（可选） | LOW-1/2/3 | dev-backend | 按需 |

**进入开发阶段的前提**：CRITICAL-1/2 和 MEDIUM-3 修复后，由 arch-reviewer 进行轻量确认（不需要完整二次审查），确认可进入实现阶段。
