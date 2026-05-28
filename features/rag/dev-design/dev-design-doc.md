# RAG 管理 — 技术设计文档

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 版本 | v1.2（终稿） |
| 状态 | 开发阶段就绪（已通过审查） |
| 编写人 | Architect Team / arch-designer |
| 编写日期 | 2026-05-26 |
| 关联需求 | `features/rag/requirement/requirement-doc.md` v1.2（终稿） |
| 关联决策（需求） | `features/rag/requirement/answers.md`（22 项疑点 + 5 项自动头脑风暴补充） |
| 关联决策（技术） | `features/rag/dev-design/tech-questions.md`（16 项疑点）<br/>`features/rag/dev-design/tech-answers.md`（16 项决策 + 6 项头脑风暴补充 + 修订指引） |
| 适用规范 | `CIOaas-python/standards/architecture.md`、`CIOaas-python/standards/coding.md` |
| 业务术语 | 空间（rag_space）/ 条目（rag_entry）/ 片段（rag_chunk）— 全文统一使用，禁混用"RAG/文件 or 文本/分块" |

### 1.1 变更摘要

#### v1.1 → v1.2（本次修订，处理 arch-reviewer 审查反馈）

| 编号 | 修订要点 | 位置 | 对应 review 条目 |
|---|---|---|---|
| R1 | 模型迁移原子切换拆为 3 个明确事务边界（PG TX1 / PG TX2 / ES 操作），并补 Saga 补偿与崩溃恢复路径；§7.3 时序图重画 | §7.3 / §11.6 | CRITICAL-1 |
| R2 | `rag_migration_task` 新增 `heartbeat_at` / `timeout_at` 字段；migration_runner 心跳更新规则；cron 超时扫描 + `MIGRATION_FAILED` 状态恢复 | §4.2.6 / §11.6 / §14 | CRITICAL-2 |
| R3 | `ai_files` CHECK 约束改为 6 步迁移（增加数据层验证 + `NOT VALID` 灰度 + 低峰期 `VALIDATE CONSTRAINT`）；部署 checklist 新增 2 项 | §4.1.1 / §13.4 | HIGH-2 |
| R4 | `POST /rag/migrations/{id}/retry` 新增完整 Schema（§6.2.14） | §6.1 / §6.2.14 | HIGH-3 |
| R5 | `GET /rag/entries` / `GET /rag/entries/{id}` 新增完整 Schema（§6.2.15 / §6.2.16） | §6.1 / §6.2.15-16 | HIGH-4 |
| R6 | `rag_space` 新增 `pending_embedding_version` 字段；`POST /rag/files` 入库 chunk 的 embedding_version 路由规则；迁移流程更新 | §4.2.1 / §6.2.5 / §7.3 | MEDIUM-3 |

#### v0.1 → v1.1（历史修订）

| 编号 | 修订要点 | 位置 |
|---|---|---|
| 1 | 向量维度由 3072 改为 1536（固定单维度，v2 再支持多维度） | §4.2.4 / §4.3 / §9 / §14 |
| 2 | `rag_space.embedding_model` 加 CHECK 限定 1536 维模型 | §4.2.1 |
| 3 | `ai_files` 扩展改为 5 步迁移 + CHECK 约束 | §4.1 |
| 4 | 删除"多维度并存"相关复杂度（padding / 动态建索引） | §4 总览 |
| 5 | 跨空间检索改为 `asyncio.gather` 并发单空间查询 | §6.2.9 / §7.2 / §10 |
| 6 | ES 后端关闭 hybrid，分两次查询 + Python 层统一 RRF | §6.2.9 / §10 |
| 7 | PARTIAL 重试保留 metadata 不预先清除 | §6.2.12（新）/ §7.4 |
| 8 | `RAG_PG_VECTOR_DIM_MAX` 重命名为 `RAG_PG_VECTOR_DIM=1536` | §9 |
| 9 | HNSW 索引参数固定 `m=16, ef_construction=64` | §4.2.4 / §10 |
| 10 | 明确 `x-user-role` 头解析逻辑 + `ADMIN_ROLES` 白名单 | §11.1 |
| 11 | 部署 checklist 增加 4 项（PG 版本 / pgvector 版本 / CREATE EXTENSION 权限 / Java grep） | §13.4 |
| 12 | migration 路径明确为 `CIOaas-python/sql/migrations/`，文件名 `2026-05-26_rag_NNN_*.up.sql/.down.sql` | §13.1 |
| 13 | 风险表新增 3 条（v2 多维度分表 / 中文 OCR 精度 / BackgroundTasks 单机崩溃） | §14 |
| 14 | `vectorizer/ocr/` 子目录补充（Textract / Vision Provider） | §5 |
| 15 | 补充 esapiens 搬入映射表 + 本地化要点 | §5.3 |
| 16 | §15 改名为"已决断疑点 + 待开发阶段确认项"，列出 16 项决策摘要 + 4 项待确认 | §15 |
| 17 | 业务术语统一为"空间 / 条目 / 片段"，全文消除"待澄清/TBD/待定" | 整体 |

---

## 2. 设计目标

### 2.1 业务目标映射

| 需求目标 | 设计落点 |
|---|---|
| 公司内部资料沉淀为可被 AI 检索的"空间" | `rag_space` 表 + `/rag/spaces` REST |
| 普通用户能上传/录入并立刻验证检索 | 入库异步管线（BackgroundTasks）+ `/rag/search` 即查接口 |
| 为后续 Chatbot 提供稳定 RAG 检索 | `/rag/search` 强制携带 `user_id` 做权限裁剪，可指定多空间 |
| 管理员看使用情况 | `rag_search_log` + `/rag/stats/*` 聚合接口 |
| 切换 embedding 模型不中断业务 | `rag_migration_task` + 双 `embedding_version` 并存（旧条目保留检索，新上传走新模型），本期仅支持同维度（1536）模型互切 |

### 2.2 性能目标

- **检索 P95**（单空间，top_k ≤ 10）：< 3 秒
- **检索 P95**（跨空间 2-5 个）：< 5 秒
- **任务可见**：上传后 < 10 秒可见任务记录（图片类不保证处理完成）
- 数据库连接池 `pool_size` 显式配置（standards/coding.md §10）；LLM/Embedding 调用 timeout 60s + 指数退避 3 次

### 2.3 可维护性目标

- 完全遵循 `source/{module}/{routes,dto,service}` 三层结构
- VectorStore 走 Protocol，pg/es 两种后端一份调用代码
- esapiens 的 `embedding_pipeline` 整体搬入并去掉 `sapien_id` / `paper_drawer` 等遗留概念，新增/改造点必须留注释解释 why

---

## 3. 总体架构

### 3.1 模块全景图

```
┌─────────────────────────────────────────────────────────────────┐
│                       前端 (CIOaas-web)                          │
│   空间列表 / 空间详情 / 入库进度 / 检索测试 / 统计页              │
└─────────────────────────────────────────────────────────────────┘
        │HTTPS (Bearer JWT, x-user-id, x-company-id, x-user-role)
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Java 网关 (CIOaas-api)                         │
│   1) 认证 + 注入 x-user-id / x-company-id / x-user-role 头       │
│   2) 反向代理 /rag/** → Python                                    │
│   3) /files/presign 颁发 S3 预签名 URL（前端直传 S3）             │
└─────────────────────────────────────────────────────────────────┘
        │HTTP（内网）
        ▼
┌─────────────────────────────────────────────────────────────────┐
│           Python 服务 (CIOaas-python) — rag 模块      │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ routes.py   — REST 接入层                                     ││
│ │ service/    — 空间/入库/检索/统计/迁移业务                    ││
│ │ vectorizer/ — loaders + splitters + ocr + embedder + pipeline ││
│ │ storage/    — VectorStore Protocol (pg_store / es_store)      ││
│ │ db/         — ORM + repository                                ││
│ │ background/ — BackgroundTasks runner（入库/迁移）             ││
│ └──────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
        │              │               │              │
        ▼              ▼               ▼              ▼
   PostgreSQL    pgvector / ES    LLM/Embedding    AWS S3
   (rag_* 表)    (RAG_STORAGE_      Providers       (原始文件)
                BACKEND 切换)
```

### 3.2 与现有 LG 系统的集成关系

| 关系 | 设计选择 | 理由 |
|---|---|---|
| Java ↔ Python | **同步 REST**（Java 反向代理 `/rag/**`） | RAG强交互（实时反馈进度/检索结果），SQS 不合适 |
| 文件上传 | **前端直传 S3** + Python 拿 `file_id` | Python 不接收 multipart 大文件，规避网关 body 限制；复用现有 `files` 表 |
| 鉴权 | Java 验完 JWT 后透传 `x-user-id` / `x-company-id` / `x-user-role` HTTP 头给 Python | 与 `lg/financial_extract_task` 现状一致，避免双重鉴权 |
| 数据库 | 共享 `public` schema | `ai_files` / `files` / `company` / `user` 复用；新增表前缀 `rag_` |
| LLM/Embedding | 走 `source/llm/providers/` | 复用追踪、计费日志、限流（embedding 调用本期不写 llm_call_log，见决策 E1） |

### 3.3 数据流向

**上传链路（文件类）**：
```
前端 → Java /files/presign → S3（直传） → Java 落库 files 表 → 前端拿 file_id
   → Python POST /rag/files (file_id, space_id, chunk_size?, overlap?)
   → Python 入库 ai_files (purpose='rag', task_id=null) + rag_ingestion_task + rag_entry
   → BackgroundTasks → vectorizer.pipeline → storage.put_chunks
```

**入库链路（文本类）**：
```
前端 → Python POST /rag/texts (title, body, space_id) → rag_entry(source='text')
   → BackgroundTasks → splitter → embedder → storage
```

**检索链路**：
```
前端 → Python POST /rag/search (query, space_ids[], top_k, filters)
   → 权限裁剪（仅保留 user 可见的 space_ids）
   → 跨空间：asyncio.gather([search_single_space(sid) for sid in space_ids])
   → 单空间内：关键词召回（PG trigram / ES match）+ 向量召回（pgvector HNSW / ES knn）
   → Python 层 RRF 融合 → 写 rag_search_log → 返回 hits
```

**模型迁移链路**：
```
PUT /rag/spaces/{id} (embedding_model=new) → rag_migration_task(status=RUNNING)
   → 旧 embedding_version 仍可被检索 → BackgroundTasks 分批重做 chunks
   → 全部完成后原子切换 rag_space.current_embedding_version → 清理旧向量
```

> **本期约束**：迁移仅在同维度（1536）模型之间发生，例如 `text-embedding-3-small ↔ text-embedding-ada-002`。跨维度迁移留作 v2，需要按维度分表配套改造（见 §14 风险）。

---

## 4. 数据模型

> **关键约束（本期）**：所有 `rag_chunk.embedding` 列固定为 `vector(1536)`，所有空间的 `embedding_model` 仅允许 1536 维模型。不做 padding、不做多维度共表、不动态建索引。v2 再支持多维度（届时按维度分表 `rag_chunk_d1536` / `rag_chunk_d3072`）。

### 4.1 现有表扩展：`ai_files`

#### 4.1.1 DDL 变更（6 步迁移，含 NOT VALID 灰度策略）

> **本次修订（v1.2 / HIGH-2）**：原 5 步迁移在生产存在风险——`ADD CONSTRAINT CHECK` 默认会全表扫描验证现有行，若历史数据中有 `purpose='financial_extract' AND task_id IS NULL` 的违反行（Java 异常分支历史遗留），migration 会 FAIL 并 ROLLBACK。改为 6 步：增加数据层前置验证 + `NOT VALID` 灰度添加 + 低峰期 `VALIDATE CONSTRAINT`。

```sql
-- Migration: 2026-05-26_rag_001_alter_ai_files.up.sql

-- 步骤 1：增加 purpose 字段，默认 'financial_extract'
ALTER TABLE ai_files
    ADD COLUMN purpose VARCHAR(30) NOT NULL DEFAULT 'financial_extract';

-- 步骤 2：回填（已有数据全部是 financial_extract；DEFAULT 已覆盖，本步骤幂等）
UPDATE ai_files SET purpose = 'financial_extract' WHERE purpose IS NULL;

-- 步骤 3：放松 task_id 约束
ALTER TABLE ai_files ALTER COLUMN task_id DROP NOT NULL;

-- 步骤 4（新增数据验证 — DBA 在执行步骤 5 之前必须确认此查询返回 0）：
--   SELECT COUNT(*) FROM ai_files
--   WHERE purpose = 'financial_extract' AND task_id IS NULL;
--
--   若 > 0：导出违反行清单 → 人工补 task_id（或与财务团队联合修复历史数据）
--   → 再继续步骤 5。绝不允许在违反行存在时直接执行步骤 6（VALIDATE）。
-- 该步骤以 DBA 操作 SQL 形式独立执行，不写入 migration 脚本主体。

-- 步骤 5：增加 CHECK 约束（NOT VALID 灰度模式 — 不全表扫描，只对新写入生效）
ALTER TABLE ai_files ADD CONSTRAINT chk_ai_files_purpose_task CHECK (
    (purpose = 'rag' AND task_id IS NULL) OR
    (purpose = 'financial_extract' AND task_id IS NOT NULL)
) NOT VALID;

-- 步骤 6：建索引（RAG 列表的高频过滤路径）
CREATE INDEX idx_ai_files_purpose_company
    ON ai_files (purpose, company_id, deleted)
    WHERE deleted = FALSE;

COMMENT ON COLUMN ai_files.purpose IS
    '文件用途枚举：financial_extract / kb（RAG入库），区分多业务共用 ai_files';
COMMENT ON COLUMN ai_files.task_id IS
    'AI 财务抽取任务 ID（financial_extract 必填；rag 用途为空，由 rag_entry 关联）';
```

**步骤 7（独立 migration，低峰期异步执行，不锁表）**：

```sql
-- Migration: 2026-05-27_rag_001b_validate_ai_files_constraint.up.sql
-- 必须在生产业务低峰期执行；只对历史数据做扫描验证，不锁定写入
ALTER TABLE ai_files VALIDATE CONSTRAINT chk_ai_files_purpose_task;
```

**为什么拆两个 migration**：
- `NOT VALID` 允许约束立即对新写入生效，但跳过历史数据扫描——上线第一波不阻塞
- `VALIDATE CONSTRAINT` 只取 `SHARE UPDATE EXCLUSIVE` 锁（允许并发读写），但全表扫描耗时不可控，必须挑业务低峰期手动执行
- 若 `VALIDATE` 因违反行报错，回头只需 fix 数据 + 重跑此步骤，不影响主 migration 已交付的功能

回滚脚本 `2026-05-26_rag_001_alter_ai_files.down.sql`：

```sql
DROP INDEX IF EXISTS idx_ai_files_purpose_company;
ALTER TABLE ai_files DROP CONSTRAINT IF EXISTS chk_ai_files_purpose_task;
-- 回滚 task_id NOT NULL 前必须先清理 rag 用途数据
DELETE FROM ai_files WHERE purpose = 'rag';
ALTER TABLE ai_files ALTER COLUMN task_id SET NOT NULL;
ALTER TABLE ai_files DROP COLUMN purpose;
```

#### 4.1.2 ORM 同步（`source/lg/db/models/models.py`）

```python
class AiFile(Base):
    # ... 现有字段 ...
    task_id = Column(
        String(36), ForeignKey("ai_financial_extraction_task.id"), nullable=True
    )
    """purpose='rag' 时为 NULL；purpose='financial_extract' 时由 DB CHECK 约束保证必填"""

    purpose = Column(String(30), nullable=False, default="financial_extract")
    """文件用途：financial_extract / rag"""
```

#### 4.1.3 迁移要点 + 前置验证

- **Java 端不需要改**：Java 财务上传不感知 `purpose` 字段，由 DB default 兜底；但开发阶段必须 grep 财务模块所有 `INSERT INTO ai_files` / JPA `save(AiFile)` 路径，确认 `task_id` 都传值（避免 CHECK 约束在生产违反）
- **回填默认值** 由步骤 1 的 `DEFAULT 'financial_extract'` 覆盖，步骤 2 仅为保险
- **CHECK 约束语义**：DB 层强制"`purpose='rag'` ↔ `task_id IS NULL`"互斥，是防回归的关键保障（决策 G2=B）

### 4.2 新增表

#### 4.2.1 `rag_space` RAG空间

```sql
CREATE TABLE rag_space (
    id                       VARCHAR(36)  PRIMARY KEY,
    company_id               VARCHAR(36)  NOT NULL,
    owner_type               VARCHAR(16)  NOT NULL,                   -- 'COMPANY' / 'PERSONAL'
    owner_user_id            VARCHAR(36),                             -- owner_type=PERSONAL 时填该用户
    name                     VARCHAR(255) NOT NULL,
    description              TEXT,
    embedding_provider       VARCHAR(32)  NOT NULL,                   -- 'openai'（本期仅支持 openai）
    embedding_model          VARCHAR(128) NOT NULL,                   -- 'text-embedding-3-small' / 'text-embedding-ada-002'
    embedding_dim            INTEGER      NOT NULL DEFAULT 1536,      -- 本期固定 1536
    current_embedding_version INTEGER     NOT NULL DEFAULT 1,         -- 当前生效版本号
    pending_embedding_version INTEGER,                                 -- 迁移期间新上传/检索使用的目标版本（MEDIUM-3 / R6）
    pending_embedding_provider VARCHAR(32),                            -- 迁移目标 provider（NULL = 非迁移期）
    pending_embedding_model   VARCHAR(128),                            -- 迁移目标 model（NULL = 非迁移期）
    default_chunk_size       INTEGER      NOT NULL DEFAULT 800,
    default_chunk_overlap    INTEGER      NOT NULL DEFAULT 100,
    status                   VARCHAR(16)  NOT NULL DEFAULT 'READY',   -- READY / MIGRATING / MIGRATION_FAILED
    deleted                  BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at               TIMESTAMP WITH TIME ZONE,                -- 软删除时间（用于 30 天清理）
    created_by               VARCHAR(36)  NOT NULL,
    created_at               TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by               VARCHAR(36),
    updated_at               TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rag_space_owner CHECK (
        (owner_type = 'COMPANY' AND owner_user_id IS NULL) OR
        (owner_type = 'PERSONAL' AND owner_user_id IS NOT NULL)
    ),
    -- 本期仅允许 1536 维 embedding 模型（决策 A3）
    CONSTRAINT chk_rag_space_embedding_model CHECK (
        embedding_model IN ('text-embedding-3-small', 'text-embedding-ada-002')
    ),
    CONSTRAINT chk_rag_space_embedding_dim CHECK (embedding_dim = 1536),
    -- pending 三字段必须同时为 NULL 或同时非 NULL（R6）
    CONSTRAINT chk_rag_space_pending_consistency CHECK (
        (pending_embedding_version IS NULL AND pending_embedding_provider IS NULL AND pending_embedding_model IS NULL)
        OR (pending_embedding_version IS NOT NULL AND pending_embedding_provider IS NOT NULL AND pending_embedding_model IS NOT NULL)
    ),
    -- pending model 同样必须在 1536 维白名单内
    CONSTRAINT chk_rag_space_pending_model CHECK (
        pending_embedding_model IS NULL
        OR pending_embedding_model IN ('text-embedding-3-small', 'text-embedding-ada-002')
    )
);

-- 同所有者范围内不允许同名（业务规则 §4.1.4 规则 1）
CREATE UNIQUE INDEX uk_rag_space_company_name
    ON rag_space (company_id, name)
    WHERE owner_type = 'COMPANY' AND deleted = FALSE;
CREATE UNIQUE INDEX uk_rag_space_personal_name
    ON rag_space (company_id, owner_user_id, name)
    WHERE owner_type = 'PERSONAL' AND deleted = FALSE;

-- 列表常用过滤
CREATE INDEX idx_rag_space_company_owner ON rag_space (company_id, owner_type, deleted);
CREATE INDEX idx_rag_space_personal_owner ON rag_space (owner_user_id, deleted)
    WHERE owner_type = 'PERSONAL';
```

> **设计说明**：CHECK 约束在 v2 支持多维度时通过 migration 替换（届时白名单扩展到多个维度的模型）。

#### 4.2.2 `rag_ingestion_task` 入库任务

```sql
CREATE TABLE rag_ingestion_task (
    id                    VARCHAR(36)  PRIMARY KEY,
    space_id              VARCHAR(36)  NOT NULL REFERENCES rag_space(id),
    company_id            VARCHAR(36)  NOT NULL,                          -- 冗余便于过滤
    submitted_by          VARCHAR(36)  NOT NULL,
    total_count           INTEGER      NOT NULL,                          -- 本批次总条目数
    processing_count      INTEGER      NOT NULL DEFAULT 0,
    success_count         INTEGER      NOT NULL DEFAULT 0,
    partial_count         INTEGER      NOT NULL DEFAULT 0,
    failed_count          INTEGER      NOT NULL DEFAULT 0,
    chunk_size_override   INTEGER,                                        -- 本次临时覆盖
    chunk_overlap_override INTEGER,
    created_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rag_ingestion_task_space ON rag_ingestion_task (space_id, created_at DESC);
```

#### 4.2.3 `rag_entry` 条目（文件 / 文本）

```sql
CREATE TABLE rag_entry (
    id                  VARCHAR(36)  PRIMARY KEY,
    space_id            VARCHAR(36)  NOT NULL REFERENCES rag_space(id),
    company_id          VARCHAR(36)  NOT NULL,                            -- 多租户冗余
    task_id             VARCHAR(36)  REFERENCES rag_ingestion_task(id),    -- 入库任务（可空：手动迁移产生时）
    source_type         VARCHAR(16)  NOT NULL,                            -- 'FILE' / 'TEXT'
    file_id             VARCHAR(36),                                       -- source_type=FILE 时填 ai_files.file_id
    title               VARCHAR(512) NOT NULL,                            -- 文件名 / 文本标题
    content_text        TEXT,                                              -- source_type=TEXT 时存正文（≤ 100,000 字符）
    mime_type           VARCHAR(128),
    file_size_bytes     BIGINT,
    chunk_size_used     INTEGER      NOT NULL,                            -- 实际用的切片参数（事后可追溯）
    chunk_overlap_used  INTEGER      NOT NULL,
    embedding_version   INTEGER      NOT NULL,                            -- 入库时的空间向量版本
    chunk_count         INTEGER      NOT NULL DEFAULT 0,
    total_tokens        BIGINT       NOT NULL DEFAULT 0,                  -- 累计 embedding token（不再写 llm_call_log，见 E1）
    status              VARCHAR(16)  NOT NULL DEFAULT 'PROCESSING',       -- PROCESSING / SUCCESS / PARTIAL / FAILED
    processing_stage    VARCHAR(32),                                       -- download / ocr / split / embed / store
    error_message       TEXT,
    hit_count           BIGINT       NOT NULL DEFAULT 0,                  -- 该条目累计被命中次数（永久保留）
    deleted             BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at          TIMESTAMP WITH TIME ZONE,
    created_by          VARCHAR(36)  NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rag_entry_source CHECK (
        (source_type = 'FILE' AND file_id IS NOT NULL) OR
        (source_type = 'TEXT' AND content_text IS NOT NULL)
    )
);

CREATE INDEX idx_rag_entry_space_status ON rag_entry (space_id, status, deleted);
CREATE INDEX idx_rag_entry_task         ON rag_entry (task_id);
CREATE INDEX idx_rag_entry_file         ON rag_entry (file_id);
-- 同空间内同标题去重检查（覆盖时先 SELECT 这条索引判断）
CREATE INDEX idx_rag_entry_space_title  ON rag_entry (space_id, title)
    WHERE deleted = FALSE;
```

#### 4.2.4 `rag_chunk` 片段（本期 vector(1536) 固定单维度）

**PG 后端（pgvector）**：

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_chunk (
    id                 VARCHAR(36)  PRIMARY KEY,
    entry_id           VARCHAR(36)  NOT NULL REFERENCES rag_entry(id) ON DELETE CASCADE,
    space_id           VARCHAR(36)  NOT NULL,                            -- 冗余便于跨空间检索按 space_id 过滤
    company_id         VARCHAR(36)  NOT NULL,                            -- 多租户冗余
    embedding_version  INTEGER      NOT NULL,                            -- 与 rag_entry.embedding_version 对齐
    seq                INTEGER      NOT NULL,                            -- 在条目内的序号
    content            TEXT         NOT NULL,
    content_tokens     INTEGER      NOT NULL,
    embedding          vector(1536) NOT NULL,                            -- 本期固定 1536 维（决策 A3）
    metadata           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    hit_count          BIGINT       NOT NULL DEFAULT 0,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 关键词召回：trigram + GIN（PG 不做中文分词，本期符合需求 §4.5.4 规则 5）
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_rag_chunk_content_trgm ON rag_chunk USING gin (content gin_trgm_ops);

-- 向量召回：HNSW（决策 A1，参数固定）
CREATE INDEX idx_rag_chunk_embedding_hnsw ON rag_chunk
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 单空间检索 SQL 必须命中 HNSW，故按 (space_id, embedding_version) 单值过滤（决策 C2）
CREATE INDEX idx_rag_chunk_space_version ON rag_chunk (space_id, embedding_version);
CREATE INDEX idx_rag_chunk_entry ON rag_chunk (entry_id);
```

**ES 后端时**：`rag_chunk` 仅保留元数据（id / entry_id / space_id / company_id / seq / content_tokens / hit_count），不写 embedding/content（这两列由 ES 持有）。这样 `hit_count` 累计、按 entry_id 反查、迁移时清理统计等场景仍走 PG，避免 ES 与 PG 双向写同步问题。

#### 4.2.5 `rag_search_log` 检索日志

```sql
CREATE TABLE rag_search_log (
    id              BIGSERIAL    PRIMARY KEY,
    company_id      VARCHAR(36)  NOT NULL,
    user_id         VARCHAR(36)  NOT NULL,
    space_ids       VARCHAR(36)[] NOT NULL,                              -- 实际生效（裁剪后）的空间集合
    query_text      TEXT         NOT NULL,                                -- 用于热门 query 统计
    top_k           INTEGER      NOT NULL,
    hit_count       INTEGER      NOT NULL,
    duration_ms     INTEGER      NOT NULL,
    caller_type     VARCHAR(16)  NOT NULL DEFAULT 'USER',                -- USER / CHATBOT
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rag_search_log_company_time ON rag_search_log (company_id, created_at DESC);
-- 热门 query 30 天窗口的高效聚合
CREATE INDEX idx_rag_search_log_space_time ON rag_search_log USING gin (space_ids);
```

#### 4.2.6 `rag_migration_task` 模型迁移任务

```sql
CREATE TABLE rag_migration_task (
    id                    VARCHAR(36)  PRIMARY KEY,
    space_id              VARCHAR(36)  NOT NULL REFERENCES rag_space(id),
    company_id            VARCHAR(36)  NOT NULL,
    from_version          INTEGER      NOT NULL,
    to_version            INTEGER      NOT NULL,
    from_provider         VARCHAR(32)  NOT NULL,
    from_model            VARCHAR(128) NOT NULL,
    to_provider           VARCHAR(32)  NOT NULL,
    to_model              VARCHAR(128) NOT NULL,
    to_embedding_dim      INTEGER      NOT NULL,                          -- 本期恒为 1536
    status                VARCHAR(16)  NOT NULL DEFAULT 'RUNNING',       -- RUNNING / SUCCEEDED / FAILED / CLEANUP_PENDING
    total_entries         INTEGER      NOT NULL,
    completed_entries     INTEGER      NOT NULL DEFAULT 0,
    failed_entries        INTEGER      NOT NULL DEFAULT 0,
    started_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at           TIMESTAMP WITH TIME ZONE,
    heartbeat_at          TIMESTAMP WITH TIME ZONE,                       -- migration_runner 每处理 10 个 entry 更新（CRITICAL-2 / R2）
    timeout_at            TIMESTAMP WITH TIME ZONE,                       -- 迁移启动时计算 = started_at + RAG_MIGRATION_TIMEOUT_S（默认 4 小时）
    cleanup_retries       INTEGER      NOT NULL DEFAULT 0,                -- 切换后旧数据清理重试次数（R1）
    error_message         TEXT,
    created_by            VARCHAR(36)  NOT NULL
);

CREATE INDEX idx_rag_migration_task_space ON rag_migration_task (space_id, started_at DESC);
-- cron 扫描超时迁移任务（R2）
CREATE INDEX idx_rag_migration_task_heartbeat ON rag_migration_task (status, heartbeat_at)
    WHERE status = 'RUNNING';
-- cron 扫描待清理迁移任务（R1）
CREATE INDEX idx_rag_migration_task_cleanup ON rag_migration_task (status, finished_at)
    WHERE status = 'CLEANUP_PENDING';
```

### 4.3 ES 索引设计（RAG_STORAGE_BACKEND=es）

#### 4.3.1 索引命名

`rag_{env}_{company_id_short}_v{embedding_version}`，例如 `rag_prod_abc12345_v1`。
- 公司级隔离（每公司独立索引，避免大索引 + 多租户混搜的开销）
- 版本隔离（模型迁移期间 v1 / v2 并存，迁移结束后 delete v1）
- 决策 A2=A，活跃公司 > 500 的场景通过 `RAG_STORAGE_BACKEND=pg` 切回

#### 4.3.2 Mapping（v1）

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "index.knn": true
  },
  "mappings": {
    "properties": {
      "chunk_id":          { "type": "keyword" },
      "entry_id":          { "type": "keyword" },
      "space_id":          { "type": "keyword" },
      "company_id":        { "type": "keyword" },
      "embedding_version": { "type": "integer" },
      "seq":               { "type": "integer" },
      "content":           { "type": "text" },
      "embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      "metadata":          { "type": "object", "enabled": true },
      "created_at":        { "type": "date" }
    }
  }
}
```

本期 `dims=1536` 固定。

---

## 5. Python 模块结构

```
source/rag/
├── __init__.py
├── routes.py                          # FastAPI router: prefix="/rag"
├── dto/
│   ├── __init__.py
│   ├── request.py                     # SpaceCreateRequest / FileIngestRequest / SearchRequest 等
│   ├── response.py                    # 统一信封 + lowerCamelCase
│   └── dto.py                         # 服务层 DTO（snake_case）
├── service/
│   ├── __init__.py
│   ├── space_service.py               # CRUD 空间 + 权限矩阵 + SELECT FOR UPDATE 并发迁移控制
│   ├── ingest_service.py              # 入库提交 + 任务编排 + PARTIAL 重试保留 metadata
│   ├── search_service.py              # 检索 + 权限裁剪 + Python 层 RRF 融合
│   ├── stats_service.py               # 空间/条目统计聚合
│   └── migration_service.py           # 模型迁移调度
├── vectorizer/                        # 主要来自 esapiens/embedding_pipeline，剥离 sapien_id/paper_drawer
│   ├── __init__.py
│   ├── loaders/                       # 1:1 搬入 esapiens/embedding_pipeline/document_loaders/
│   │   ├── base_loader.py
│   │   ├── csv_loader.py
│   │   ├── pdf_loader.py
│   │   ├── doc_loader.py              # docx + 通过 libreoffice 兼容 doc
│   │   ├── excel_loader.py
│   │   ├── image_loader.py            # 改造：OCR 走 source/rag/vectorizer/ocr/
│   │   ├── epub_loader.py
│   │   ├── text_file_loader.py
│   │   ├── direct_text_loader.py      # 改造：去除 PaperDrawerTextConfig，改为通用 DirectTextConfig
│   │   ├── document.py
│   │   └── factory_loader.py          # 改造：清除 paper_drawer 相关函数
│   ├── splitters/                     # 来自 text_splitting/，扩展按文件类型差异化默认值
│   │   └── text_splitter.py
│   ├── ocr/                           # 决策 D1：Textract 主 + Vision 备
│   │   ├── __init__.py
│   │   ├── base.py                    # OCRProvider Protocol
│   │   ├── textract_provider.py       # AWS Textract（复用平台已有凭证）
│   │   └── vision_provider.py         # GPT-4o vision via llm.providers
│   ├── embedder.py                    # 调度 source/llm/providers/embeddings/；批次分片 + 重试 + 并发上限
│   ├── file_types.py                  # 取代 esapiens/vectorization_enum.py，删除 paper_drawer
│   └── pipeline.py                    # 编排：load → split → ocr → embed → store
├── storage/
│   ├── __init__.py
│   ├── base.py                        # VectorStore Protocol（duck typing）
│   ├── pg_store.py                    # pgvector 实现（新写）
│   ├── es_store.py                    # 复用 esapiens ESStorage 改造（剥离 sapien_id）
│   └── factory.py                     # 按 RAG_STORAGE_BACKEND 路由
├── db/
│   ├── __init__.py
│   ├── models/
│   │   └── rag_models.py               # KbSpace / KbEntry / KbChunk / KbIngestionTask /
│   │                                   # KbSearchLog / KbMigrationTask（共享 lg.db.models.models.Base）
│   └── repository/
│       ├── space_repo.py
│       ├── entry_repo.py
│       ├── chunk_repo.py
│       └── stats_repo.py
└── background/
    ├── __init__.py
    ├── pipeline_runner.py             # FastAPI BackgroundTasks 入口（含 sentry_sdk.new_scope）
    └── migration_runner.py            # 迁移 BackgroundTasks 入口（含 sentry_sdk.new_scope）

source/llm/providers/embeddings/        # 新增 embeddings 子家族
├── __init__.py
├── base.py                            # EmbeddingClient Protocol
├── openai.py                          # text-embedding-3-small、text-embedding-ada-002（本期仅 1536 维）
└── factory.py                         # 按 provider+model 取实例（本期不注入 tracer，见 E1）
```

### 5.1 关键类与协议

```python
# source/rag/vectorizer/pipeline.py
from typing import Protocol

class VectorizerPipeline:
    """编排 load → split → ocr → embed → store。
    
    Pipeline 是 stateless 的，每次入库 new 一个实例由 BackgroundTasks 调用。
    """

    def __init__(
        self,
        loader_factory,
        splitter,
        ocr_provider,
        embedder,
        store,
        logger,
    ) -> None: ...

    async def run_file(
        self, *, entry_id: str, file_path: str, mime: str,
        chunk_size: int, chunk_overlap: int,
    ) -> "IngestResult": ...

    async def run_text(
        self, *, entry_id: str, title: str, body: str,
        chunk_size: int, chunk_overlap: int,
    ) -> "IngestResult": ...


# source/rag/storage/base.py
from typing import Protocol

class VectorStore(Protocol):
    """统一向量存储接口；pg/es 实现两份。
    
    跨空间检索由 search_service 在 Python 层并发调用 search()（决策 C2），
    本接口约定每次调用只查单个 space_id。
    """

    async def upsert_chunks(
        self, *, space_id: str, company_id: str,
        embedding_version: int, chunks: list["ChunkInput"],
    ) -> None: ...

    async def search_single_space(
        self, *, space_id: str, company_id: str,
        query_text: str, query_vector: list[float],
        embedding_version: int,
        top_k: int, filters: dict,
    ) -> list["ChunkHit"]:
        """单空间召回。pg_store 必须用 space_id = $1 单值过滤以命中 HNSW。
        es_store 必须分两次查（keyword + knn），不开 ES 自带 hybrid（决策 C1）。
        """

    async def delete_by_entry(self, *, entry_id: str) -> None: ...

    async def delete_by_space_version(
        self, *, space_id: str, embedding_version: int
    ) -> None: ...


# source/llm/providers/embeddings/base.py
from typing import Protocol

class EmbeddingClient(Protocol):
    name: str
    model: str
    dim: int   # 本期固定 1536

    async def embed_documents(self, texts: list[str]) -> tuple[list[list[float]], int]:
        """返回 (vectors, total_tokens)。
        不写 llm_call_log（决策 E1），token 数由调用方累加到 rag_entry.total_tokens。
        """
```

### 5.2 路由挂载

`source/main.py` 在现有 `app.include_router` 之后新增：

```python
from rag import router as rag_router
app.include_router(rag_router)
```

### 5.3 esapiens 代码搬入映射表（决策补充 1）

把 `esapiens-python/esapiens/embedding_pipeline/` 复制到 `CIOaas-python/source/rag/vectorizer/`，并做以下本地化：

| 原 esapiens 位置 | 新位置 | 本地化要点 |
|---|---|---|
| `document_loaders/` | `source/rag/vectorizer/loaders/` | 去掉 `sapien_id` / `paper_drawer` 等业务遗留；改用 `rag_space_id` / `rag_entry_id`；图片 loader 增加 OCR Provider 依赖注入 |
| `text_splitting/` | `source/rag/vectorizer/splitters/` | 直接复用，无业务字段 |
| `embedding_vectorization/embedding_manager.py` | 废弃 | 改走 `source/llm/providers/embeddings/factory.py`，不再单例 OpenAIEmbeddings |
| `embedding_storage/es_storage.py` | `source/rag/storage/es_store.py` | 元数据字段重命名（`botFileId` → `entry_id`, `sapienId` → `space_id`, `tenantId` → `company_id`）；删除 paper_drawer 分支；删除 publish/delete flag；不开启 hybrid 检索 |
| `embedding_storage/csv_storage.py` | 不搬 | 测试用，本期不需要 |
| `vectorization_enum.py` | `source/rag/vectorizer/file_types.py` | 删除 `paper_drawer` 训练类型 |

**Python import 本地化要点**：

- `esapiens.common.logging_config.logging` → `from common.logger import setup_logger`
- `esapiens.vectore.common.num_tokens_from_string` → 新写一个简单工具或直接用 `tiktoken`
- `esapiens.vectore.common.get_es_client` → 走 `source/rag/storage/es_store.py` 的 client 工厂
- `esapiens.integrations.datasource_manager.get_tenant_elasticsearch_config` → 走 `os.environ` 配置（部署期单选，不做租户级动态）
- `config.config.config.ES_API_KEY` → `os.environ['RAG_ES_API_KEY']`

---

## 6. 接口规范（REST API）

所有接口：
- 统一前缀 `/rag`
- 路由层 `async def` + `response_model=`（standards/coding.md §3）
- 鉴权依赖 `Depends(require_user_context)` 从 `x-user-id` / `x-company-id` / `x-user-role` 注入 `UserContext`
- 响应统一信封 `{ success, code, message, data }`（standards/coding.md §1）
- 错误：路由层抛 `HTTPException`，服务层抛 `ValueError`/`RuntimeError` 由统一 exception handler 转换

### 6.1 接口汇总

| 方法 | 路径 | 用途 | 鉴权 |
|---|---|---|---|
| POST | `/rag/spaces` | 创建空间 | user |
| GET | `/rag/spaces` | 列表（按可见性过滤） | user |
| GET | `/rag/spaces/{id}` | 详情 | user |
| PUT | `/rag/spaces/{id}` | 更新（含切换 embedding 模型，触发迁移） | user |
| DELETE | `/rag/spaces/{id}` | 软删除 | user |
| POST | `/rag/files` | 文件入库（已传 S3，传 file_id） | user |
| POST | `/rag/texts` | 文本直传入库 | user |
| GET | `/rag/tasks/{id}` | 入库任务状态 | user |
| GET | `/rag/entries` | 条目列表（按 space 过滤；详见 §6.2.15） | user |
| GET | `/rag/entries/{id}` | 条目详情（详见 §6.2.16） | user |
| GET | `/rag/entries/{id}/chunks` | 片段预览 | user |
| POST | `/rag/entries/{id}/retry` | 重试入库（PARTIAL 时保留 metadata） | user |
| DELETE | `/rag/entries/{id}` | 删除条目 | user |
| POST | `/rag/search` | 检索（单/跨空间） | user / chatbot |
| GET | `/rag/stats/spaces/{id}` | 空间统计 | user |
| GET | `/rag/stats/entries/{id}` | 条目统计 | user |
| POST | `/rag/spaces/{id}/migrate` | 触发模型迁移 | user |
| GET | `/rag/migrations/{id}` | 迁移进度 | user |
| POST | `/rag/migrations/{id}/retry` | 重新迁移（详见 §6.2.14） | user |

### 6.2 详细 Schema

#### 6.2.1 POST /rag/spaces

**Request**（`SpaceCreateRequest`）：
```python
class SpaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="空间名称")
    description: Optional[str] = Field(None, max_length=2000)
    ownerType: Literal["COMPANY", "PERSONAL"] = Field(..., description="所有者类型")
    embeddingProvider: str = Field("openai", description="本期仅支持 openai")
    embeddingModel: Literal["text-embedding-3-small", "text-embedding-ada-002"] = Field(
        ...,
        description="本期仅支持 1536 维模型；v2 再开放更多",
    )
    defaultChunkSize: int = Field(800, ge=100, le=4000)
    defaultChunkOverlap: int = Field(100, ge=0, le=1000)
```

**Response**（`SpaceResponse`）：
```python
class SpaceData(BaseModel):
    id: str
    name: str
    description: Optional[str]
    ownerType: str
    ownerUserId: Optional[str]
    embeddingProvider: str
    embeddingModel: str
    embeddingDim: int                # 本期固定 1536
    currentEmbeddingVersion: int
    defaultChunkSize: int
    defaultChunkOverlap: int
    status: str                      # READY / MIGRATING / MIGRATION_FAILED
    migrationProgress: Optional[int] # status=MIGRATING 时给出 0-100
    entryCount: int
    searchCount: int
    createdAt: str
    updatedAt: str

class SpaceResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: SpaceData
```

**业务规则**：
- ownerType=PERSONAL 时 `owner_user_id = current_user.id`
- 名称在同所有者范围内查重，重复返回 `code=40901`
- `chunk_overlap < chunk_size` 校验（`@model_validator`）
- `embeddingDim` 由 `EmbeddingFactory.get(provider, model).dim` 解析填入（本期恒为 1536）
- `embeddingModel` 必须在 CHECK 约束白名单内，否则 DB 拒插

**错误码**：
- 400 / `40001` 参数校验失败
- 401 / `40101` 缺少用户上下文
- 409 / `40901` 同名空间已存在
- 422 / `42201` embedding 模型不支持

#### 6.2.2 GET /rag/spaces

**Query**：`ownerType=COMPANY|PERSONAL|ALL`、`limit=20`、`offset=0`、`keyword`

**Response**：`{ data: { items: SpaceData[], total: int } }`

**业务规则（权限）**：
- COMPANY 角色管理员（`x-user-role IN ADMIN_ROLES`）：返回本公司全部 spaces（含他人个人空间）
- 普通用户：返回公司级空间 + `owner_user_id = current_user.id` 的个人空间

#### 6.2.3 PUT /rag/spaces/{id}

**Request**（部分更新）：
```python
class SpaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    defaultChunkSize: Optional[int] = None
    defaultChunkOverlap: Optional[int] = None
    embeddingProvider: Optional[str] = None
    embeddingModel: Optional[Literal[
        "text-embedding-3-small", "text-embedding-ada-002"
    ]] = None
```

**业务规则**：
- 若 (provider, model) 与现状不同 → 进入迁移流程：
  1. 在事务内 `SELECT rag_space ... FOR UPDATE`（决策 B2）
  2. 校验 status=READY；否则返回 409 / `40902`
  3. 自动创建 `rag_migration_task` 并将空间 status 改为 MIGRATING
  4. 返回 `migrationTaskId`
- 名称变更走查重
- chunk 默认值变更只影响后续入库
- **本期约束**：embeddingModel 仅支持同维度（1536）切换；DB CHECK 约束强制

#### 6.2.4 DELETE /rag/spaces/{id}

**Response**：`{ success: true, code: 0, data: { deletedAt: "..." } }`

**业务规则**：
- 软删除：`deleted=true, deleted_at=now()`
- 级联：`rag_entry.deleted=true`，但不立即清向量；30 天后 cron 任务硬删除
- 迁移中的空间允许删除（迁移任务自动 FAILED）

#### 6.2.5 POST /rag/files

**Request**：
```python
class FileIngestItem(BaseModel):
    fileId: str = Field(..., description="files.id（Java 创建）")
    overwrite: bool = Field(False, description="同名时是否覆盖")

class FileIngestRequest(BaseModel):
    spaceId: str
    items: List[FileIngestItem] = Field(..., min_length=1, max_length=10)
    chunkSize: Optional[int] = Field(None, ge=100, le=4000)
    chunkOverlap: Optional[int] = Field(None, ge=0, le=1000)
```

**Response**：
```python
class FileIngestResponseData(BaseModel):
    taskId: str
    accepted: List[str]            # 已接受处理的 fileId
    skipped: List[dict]            # [{fileId, reason: 'DUPLICATE_SKIPPED'}]
    rejected: List[dict]           # [{fileId, reason: 'UNSUPPORTED_TYPE'/'TOO_LARGE'/'NOT_FOUND'}]
```

**业务规则**：
- 校验 `files.id` 存在且属同 company
- 校验 MIME / 扩展名：CSV / PDF / DOC / DOCX / XLS / XLSX / PNG / JPG / JPEG / EPUB / TXT
- 单文件大小：从 `files.length` 读，> 50MB → rejected
- 同名查重：`rag_entry.title == files.original_name AND space_id AND NOT deleted`，命中且 overwrite=true → 删旧 entry + 清向量；overwrite=false → skipped
- 创建 `rag_ingestion_task` + 每个 accepted 创建 `rag_entry(status=PROCESSING)` + 创建 `ai_files(purpose='rag', task_id=NULL)`
- **chunk 的 embedding_version 路由（R6 / MEDIUM-3）**：在创建 `rag_entry` 与后续 chunk 入库时按以下规则选择 `embedding_version`：
  - 若 `space.status='READY'`：使用 `space.current_embedding_version` + `(space.embedding_provider, space.embedding_model)`
  - 若 `space.status='MIGRATING'`：使用 `space.pending_embedding_version` + `(space.pending_embedding_provider, space.pending_embedding_model)`（保证迁移期间新上传直接走目标模型，不需要被迁移）
  - 若 `space.status='MIGRATION_FAILED'`：拒绝入库，返回 409 / `40902`（用户需先 retry 或回滚迁移）
- `BackgroundTasks.add_task(pipeline_runner.run_file_entry, entry_id, ...)` 逐条投递

**错误码**：
- 400 / `40001` 单次超过 10 个
- 404 / `40401` fileId 不存在
- 409 / `40902` space 状态非 READY/MIGRATING
- 413 / `41301` 文件超过 50MB（如未在 Java 端拦截）

#### 6.2.6 POST /rag/texts

**Request**：
```python
class TextIngestRequest(BaseModel):
    spaceId: str
    title: str = Field(..., min_length=1, max_length=512)
    body: str = Field(..., min_length=1, max_length=100_000)
    overwrite: bool = False
    chunkSize: Optional[int] = Field(None, ge=100, le=4000)
    chunkOverlap: Optional[int] = Field(None, ge=0, le=1000)
```

**Response**：`{ data: { taskId, entryId, accepted: bool } }`

#### 6.2.7 GET /rag/tasks/{id}

**Response**：
```python
class IngestionTaskData(BaseModel):
    taskId: str
    spaceId: str
    totalCount: int
    processingCount: int
    successCount: int
    partialCount: int
    failedCount: int
    entries: List[EntryBriefData]   # 该任务下所有条目摘要（id, title, status, error）
```

#### 6.2.8 GET /rag/entries/{id}/chunks

**Query**：`limit=50` `offset=0`

**Response**：
```python
class ChunkData(BaseModel):
    chunkId: str
    seq: int
    content: str
    contentTokens: int
    hitCount: int

class ChunksData(BaseModel):
    entryId: str
    chunkSizeUsed: int
    chunkOverlapUsed: int
    chunkSource: Literal["SPACE_DEFAULT", "TASK_OVERRIDE"]
    total: int
    items: List[ChunkData]
```

#### 6.2.9 POST /rag/search

**Request**：
```python
class SearchFilter(BaseModel):
    mimeTypes: Optional[List[str]] = None
    sourceTypes: Optional[List[Literal["FILE", "TEXT"]]] = None
    uploadedFrom: Optional[str] = None  # ISO datetime
    uploadedTo: Optional[str] = None
    entryIds: Optional[List[str]] = None

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    spaceIds: List[str] = Field(..., min_length=1)
    topK: int = Field(5, ge=1, le=20)
    filter: Optional[SearchFilter] = None
    callerType: Literal["USER", "CHATBOT"] = "USER"
    onBehalfOfUserId: Optional[str] = None  # CHATBOT 必填
```

**Response**：
```python
class SearchHit(BaseModel):
    chunkId: str
    content: str                # PARTIAL 条目固定为 "[仅文件名可检索，正文未入库]"
    entryId: str
    entryTitle: str
    spaceId: str
    spaceName: str
    similarity: float           # 0-1
    matchType: Literal["SEMANTIC", "KEYWORD", "BOTH"]

class SearchData(BaseModel):
    hits: List[SearchHit]
    grantedSpaceIds: List[str]   # 裁剪后实际生效的 spaceIds
    droppedSpaceIds: List[str]   # 被裁剪掉的（透明告知）
    durationMs: int
```

**业务规则**：

1. 必须携带 `x-user-id`（或 CHATBOT 模式下的 `onBehalfOfUserId`），否则 401
2. 权限裁剪后 grantedSpaceIds 为空 → 整体 401（不返回空 hits 而 200）
3. **跨空间策略（决策 C2，关键架构）**：
   - 跨空间在 Python 层并发：`results = await asyncio.gather([store.search_single_space(sid, ...) for sid in granted_space_ids])`
   - 每条单空间 SQL 用 `WHERE space_id = $1 AND embedding_version = $2 ORDER BY embedding <-> $vec LIMIT $top_k * 3`，能命中 HNSW 索引
   - 不使用 `WHERE space_id = ANY(...)`（会退化为 Seq Scan）
4. **单空间内召回（关键词 + 向量）**：
   - PG 后端：关键词 `content ILIKE '%query%'` + trigram；向量 pgvector ANN
   - ES 后端：分两次查（keyword `match` + knn），**不开 `hybrid=True`**（决策 C1）
   - 两个后端都在 Python 层做 RRF 融合，保证行为一致
5. **多 embedding_version 路由**：每个 granted space 按 `current_embedding_version` 取 embedder embed query；跨版本时分组复用 embedding
6. **融合**：RRF（k=60）— 详见 §10.1
7. **"部分成功"条目**：仅在关键词路径出现（content 字段返回固定占位）
8. **命中后异步**：`BackgroundTasks` 累加 `rag_chunk.hit_count` 和 `rag_entry.hit_count`、写 `rag_search_log`
9. **中文分词**：PG/ES 都不开中文分词（需求 §4.5.4 规则 5）

#### 6.2.10 GET /rag/stats/spaces/{id}

**Response**：
```python
class SpaceStatsData(BaseModel):
    spaceId: str
    chunkCount: int
    totalTokens: int
    searchCount: int                                # 累计被检索次数
    topQueries30d: List[dict]                       # [{query, count}]
    topHitChunks: List[dict]                        # [{chunkId, entryTitle, hitCount, contentPreview}]
```

**业务规则**：
- 管理员可看本公司全部 space 统计；普通用户只能看自己可见的 space
- topQueries30d：按 `created_at >= now() - 30 days` 聚合 `rag_search_log.query_text`
- topHitChunks：`SELECT ... FROM rag_chunk WHERE space_id = ? ORDER BY hit_count DESC LIMIT 10`

#### 6.2.11 POST /rag/spaces/{id}/migrate

**Request**：可空（PUT 接口自动触发时不必单独调）；提供独立路径供"重新迁移"使用：
```python
class MigrateRequest(BaseModel):
    embeddingProvider: Optional[str] = None
    embeddingModel: Optional[Literal[
        "text-embedding-3-small", "text-embedding-ada-002"
    ]] = None
    # 留空时 = 重新执行最近一次失败的迁移
```

**Response**：`{ data: { migrationTaskId, status: "RUNNING" } }`

**业务规则**：内部走 `SELECT FOR UPDATE` 串行化（决策 B2），同一空间不可并发迁移。

#### 6.2.12 POST /rag/entries/{id}/retry

**Request**：可空

**Response**：`{ data: { entryId, status: "PROCESSING" } }`

**业务规则（决策 D2）**：

- **PARTIAL 状态重试**：保留 `entry.title / entry.file_id / status=PARTIAL` 不变（关键词召回不中断），新启 pipeline runner
- **FAILED 状态重试**：同样保留 metadata，新启 pipeline
- 新 pipeline 成功：`UPDATE rag_entry SET status=SUCCESS, chunk_count=N, error_message=NULL`
- 新 pipeline 失败：`UPDATE rag_entry SET status=FAILED, error_message=...`（**不保留 PARTIAL**，避免假象）
- 重试期间所有更新对外可见即时（不另起事务）

#### 6.2.13 GET /rag/migrations/{id}

**Response**：
```python
class MigrationData(BaseModel):
    id: str
    spaceId: str
    fromVersion: int
    toVersion: int
    fromModel: str
    toModel: str
    status: str           # RUNNING / SUCCEEDED / FAILED / CLEANUP_PENDING
    totalEntries: int
    completedEntries: int
    failedEntries: int
    progressPercent: int  # = completed/total
    startedAt: str
    finishedAt: Optional[str]
    heartbeatAt: Optional[str]    # 最近一次 runner 心跳时间（用于用户判断"是否卡死"）
    timeoutAt: Optional[str]      # 计划超时时间（运行时长上限）
    errorMessage: Optional[str]
```

#### 6.2.14 POST /rag/migrations/{id}/retry（R4 / HIGH-3 新增）

按迁移任务 ID 重试一次已失败的迁移（与 §6.2.11 `POST /rag/spaces/{id}/migrate` 互补；后者按空间 ID 触发，前者用于在已知 migration task ID 的情况下直接重做）。

**Request**：
```python
class MigrationRetryRequest(BaseModel):
    force: bool = Field(False, description="忽略 cleanup_retries 上限强制重试（仅 admin）")
```

**Response**：
```python
class MigrationRetryData(BaseModel):
    migrationId: str          # 新创建或复用的迁移任务 ID
    spaceId: str
    status: Literal["RUNNING"]
    fromVersion: int
    toVersion: int
    startedAt: str

class MigrationRetryResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: MigrationRetryData
```

**业务规则**：

1. 路径参数 `{id}` 是 `rag_migration_task.id`；在事务内 `SELECT rag_migration_task ... FOR UPDATE`
2. 仅允许在 `status IN ('FAILED', 'CLEANUP_PENDING')` 时重试；其他状态返回 409 / `40902`
3. 同时锁住对应 `rag_space FOR UPDATE`，校验 `rag_space.status IN ('MIGRATION_FAILED', 'MIGRATING')`
4. 复用原 task 的 `from_provider/from_model/to_provider/to_model` 与 `from_version/to_version`；不开新 task，原地 reset：
   - `UPDATE rag_migration_task SET status='RUNNING', completed_entries=0, failed_entries=0, started_at=NOW(), heartbeat_at=NULL, timeout_at=NOW() + RAG_MIGRATION_TIMEOUT_S, error_message=NULL, finished_at=NULL`
   - `UPDATE rag_space SET status='MIGRATING', pending_embedding_version=$to_version, pending_embedding_provider=$to_provider, pending_embedding_model=$to_model`
5. `force=true` 仅 admin 可用（普通用户传 `force=true` 返回 403 / `40303`），允许重试 `cleanup_retries >= 3` 的"已耗尽自动重试"任务
6. 提交事务后 `BackgroundTasks.add_task(migration_runner.run, migration_id)`

**错误码**：
- 401 / `40101` 缺少用户上下文
- 403 / `40303` 非 admin 传 `force=true`
- 404 / `40401` migration_id 不存在
- 409 / `40902` migration 状态不允许重试

#### 6.2.15 GET /rag/entries（R5 / HIGH-4 新增）

条目列表，支持按空间 / 状态 / 类型 / 关键词过滤。

**Query 参数**：
| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `spaceId` | string | 是 | — | 必须为当前用户可见的空间 |
| `status` | string | 否 | — | `PROCESSING` / `SUCCESS` / `PARTIAL` / `FAILED` |
| `sourceType` | string | 否 | — | `FILE` / `TEXT` |
| `keyword` | string | 否 | — | 按 `rag_entry.title` 模糊搜索（PG `ILIKE`） |
| `limit` | int | 否 | 20 | 1-100 |
| `offset` | int | 否 | 0 | ≥ 0 |

**Response**：
```python
class EntryBriefData(BaseModel):
    entryId: str
    spaceId: str
    title: str
    sourceType: Literal["FILE", "TEXT"]
    status: str                  # PROCESSING / SUCCESS / PARTIAL / FAILED
    chunkCount: int
    hitCount: int
    fileSizeBytes: Optional[int]
    mimeType: Optional[str]
    embeddingVersion: int
    createdAt: str               # ISO8601 UTC, "yyyy-MM-dd HH:mm:ss"
    updatedAt: str

class EntryListData(BaseModel):
    items: List[EntryBriefData]
    total: int
    limit: int
    offset: int

class EntryListResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: EntryListData
```

**业务规则**：
- 必须强制 `WHERE company_id = ctx.company_id AND space_id = $spaceId AND deleted = FALSE`
- 若 `spaceId` 不可见 → 403 / `40301`（避免泄漏空间存在性）
- 按 `created_at DESC` 排序

**错误码**：
- 400 / `40001` limit/offset 越界
- 403 / `40301` 空间不可见
- 404 / `40401` spaceId 不存在（仅 admin 跨公司场景；同公司同上 403）

#### 6.2.16 GET /rag/entries/{id}（R5 / HIGH-4 新增）

**Response**：
```python
class EntryRecentHitData(BaseModel):
    chunkId: str
    seq: int
    contentPreview: str          # 截断 100 字
    hitCount: int                # 该 chunk 累计命中次数

class EntryDetailData(EntryBriefData):
    taskId: Optional[str]                # 入库任务（迁移产生时为空）
    fileId: Optional[str]                # sourceType=FILE 时存在
    chunkSizeUsed: int
    chunkOverlapUsed: int
    totalTokens: int
    processingStage: Optional[str]       # download / ocr / split / embed / store（PROCESSING / FAILED 时有值）
    errorMessage: Optional[str]          # 失败原因（用户可读，对应需求 §6.3 规则 1）
    topHitChunks: List[EntryRecentHitData]  # 该条目下被命中最多的前 5 个 chunk

class EntryDetailResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: EntryDetailData
```

**业务规则**：
- 校验 entry 属于当前公司 + 用户可见的空间
- `topHitChunks` 由 `SELECT * FROM rag_chunk WHERE entry_id = ? ORDER BY hit_count DESC LIMIT 5` 取
- PARTIAL 状态时 `topHitChunks` 可能为空（无 chunk 入库），但 `hitCount` 仍统计（基于 entry-level 标题命中）

**错误码**：
- 401 / `40101` 缺少用户上下文
- 403 / `40301` 跨公司或不可见空间
- 404 / `40401` entry 不存在或已软删

---

## 7. 关键流程时序图

### 7.1 文件上传 + 入库

```
前端    Java网关         S3      Python            Embedder     VectorStore
 │        │              │         │                 │             │
 │─presign│              │         │                 │             │
 │        │───签名─────→ │         │                 │             │
 │←──URL──│              │         │                 │             │
 │─PUT 文件────────────→ │         │                 │             │
 │←─ ETag───────────── │         │                 │             │
 │─POST /files/commit────→  落 files 表  │           │             │
 │←─file_id─────────────│         │                 │             │
 │                                │                 │             │
 │─POST /rag/files──────→ Java────→│                 │             │
 │                                │ 校验 + 写        │             │
 │                                │ rag_entry(PROCESSING)            │
 │←────taskId / accepted──────────│                 │             │
 │                                │                 │             │
 │                                │ BackgroundTasks │             │
 │                                │ (sentry_sdk.new_scope)         │
 │                                │   loader.load() │             │
 │                                │   (image→OCR)   │             │
 │                                │   splitter.split│             │
 │                                │   embedder ────→│             │
 │                                │←──vectors,tokens│             │
 │                                │   store.upsert ─────────────→ │
 │                                │   rag_entry status=SUCCESS      │
 │                                │   rag_ingestion_task.success+=1 │
 │ (轮询 GET /rag/tasks/{id})       │                 │             │
```

### 7.2 检索（含跨空间分支 + 混合检索）

```
前端──POST /rag/search (query, spaceIds[], topK)──→ Python
                                                    │
                                                    │ 1) 鉴权（x-user-id + x-user-role）
                                                    │    + 裁剪 spaceIds，得 grantedSpaceIds
                                                    │
                                                    │ 2) 按 space 的 embedding_version 分组
                                                    │    embeddings = {ver: embedder.embed_query(q)}
                                                    │
                                                    │ 3) 跨空间并发（asyncio.gather）：
                                                    │  ┌─────────────────────────────────────┐
                                                    │  │ for sid in grantedSpaceIds:         │
                                                    │  │   单空间 search_single_space(sid):   │
                                                    │  │     ┌──────────────────────────┐    │
                                                    │  │     │ 并行（同一 space 内）：    │    │
                                                    │  │     │ kw  = keyword_search()    │    │
                                                    │  │     │ vec = vector_search()     │    │
                                                    │  │     │   PG: WHERE space_id=$1   │    │
                                                    │  │     │     ORDER BY emb <-> $v   │    │
                                                    │  │     │     LIMIT topK*3 (HNSW)   │    │
                                                    │  │     │   ES: 分别 match + knn    │    │
                                                    │  │     │     不开 hybrid           │    │
                                                    │  │     │ RRF(kw, vec, k=60)        │    │
                                                    │  │     └──────────────────────────┘    │
                                                    │  └─────────────────────────────────────┘
                                                    │
                                                    │ 4) Python 层全局合并：所有空间结果统一 RRF
                                                    │    取 top_k
                                                    │
                                                    │ 5) 注入 entry/space 元数据
                                                    │
                                                    │ 6) BackgroundTasks:
                                                    │    - 写 rag_search_log
                                                    │    - hit_count += 1 (chunk/entry)
                                                    │
                                                    ←── hits[]
```

### 7.3 模型迁移（在线，本期同维度 1536）

#### 7.3.1 启动阶段（同步事务）

```
PUT /rag/spaces/{id} (embeddingModel=new)
    │
    ▼
service.update_space():
    BEGIN TX;
    1) SELECT * FROM rag_space WHERE id=$1 FOR UPDATE   -- 决策 B2
    2) 校验 status=READY；否则 ROLLBACK 返回 409
    3) 校验 new_model 在 CHECK 白名单内
    4) INSERT rag_migration_task (
         status='RUNNING',
         from_version=current_v, to_version=current_v + 1,
         heartbeat_at=NULL,
         timeout_at=NOW() + INTERVAL '4 hours'  -- RAG_MIGRATION_TIMEOUT_S
       )
    5) UPDATE rag_space SET
           status='MIGRATING',
           pending_embedding_version = current_v + 1,
           pending_embedding_provider = new_provider,
           pending_embedding_model = new_model
    COMMIT;
    6) BackgroundTasks.add_task(migration_runner.run, migration_id)
    7) 返回 migrationTaskId
```

#### 7.3.2 后台迁移阶段（migration_runner.run，sentry_sdk.new_scope）

```
┌────────────────────────────────────────────────────────────────────┐
│ entries_total = SELECT COUNT(*) FROM rag_entry                      │
│   WHERE space_id=$1 AND embedding_version=$from_v AND deleted=FALSE│
│ UPDATE rag_migration_task SET total_entries=$total                  │
│                                                                    │
│ for i, entry in enumerate(entries_with_from_version):              │
│     try:                                                           │
│         chunks = repo.list_chunks(entry, embedding_version=from_v) │
│         vectors_new = embedder.embed_documents([c.content])        │
│         store.upsert_chunks(                                       │
│             space_id, version=to_v, chunks=...)                    │
│         repo.mark_entry_embedded_version(entry.id, to_v)           │
│         migration_task.completed_entries += 1                      │
│     except Exception as e:                                         │
│         migration_task.failed_entries += 1                         │
│         logger.exception(...)                                      │
│                                                                    │
│     # 心跳（CRITICAL-2 / R2）：每 10 个 entry 更新一次              │
│     if i % 10 == 0:                                                │
│         UPDATE rag_migration_task SET heartbeat_at=NOW()            │
│                                                                    │
│ # 期间并发（R6 / MEDIUM-3）：                                      │
│ #   新上传：pipeline 读 space.pending_embedding_version → 走 to_v  │
│ #   检索：search_service 按 space.current_embedding_version 走 from_v│
│ #   （切换前所有检索仍走旧版本，对用户无感知）                      │
└────────────────────────────────────────────────────────────────────┘
```

#### 7.3.3 切换阶段（CRITICAL-1 / R1 — 3 个明确事务边界 + Saga 补偿）

> **设计原则**：跨 PG 和 ES（或跨 PG TX）的步骤无法用同一个 ACID 事务包裹。采用 Saga 风格：步骤 1 是"业务可见性的切换点"，提交后即视为迁移对用户完成；步骤 2/3 是"清理操作"，失败可重试不回滚。

```
迁移循环结束后（所有 entry 已处理；failed_entries 允许 = 0 或 > 0 分支处理）：

  ┌─ 分支 A：failed_entries == 0（成功路径）
  │
  │ ▼ 步骤 1（PG 事务 1 — 原子切换业务可见性）
  │   BEGIN TX;
  │     SELECT 1 FROM rag_space WHERE id=$1 FOR UPDATE;
  │     UPDATE rag_space SET
  │         current_embedding_version = pending_embedding_version,
  │         embedding_provider = pending_embedding_provider,
  │         embedding_model = pending_embedding_model,
  │         pending_embedding_version = NULL,
  │         pending_embedding_provider = NULL,
  │         pending_embedding_model = NULL,
  │         status = 'READY',
  │         updated_at = NOW()
  │       WHERE id = $space_id AND status = 'MIGRATING';
  │     UPDATE rag_migration_task SET
  │         status = 'CLEANUP_PENDING',
  │         finished_at = NOW(),
  │         heartbeat_at = NOW()
  │       WHERE id = $migration_id;
  │   COMMIT;
  │   # ↑↑↑ 提交后：对用户完全表现为"迁移完成"，检索走新版本
  │   # ↑↑↑ 若此 COMMIT 之前进程崩溃：状态保持 MIGRATING，由 R2 心跳超时 cron 兜底
  │
  │ ▼ 步骤 2（PG 事务 2 — 删旧版本 chunk，失败可重试）
  │   BEGIN TX;
  │     DELETE FROM rag_chunk
  │       WHERE space_id = $space_id AND embedding_version = $from_v;
  │   COMMIT;
  │   # 失败：保持 status='CLEANUP_PENDING'，cleanup_retries += 1，cron 重试
  │   # 不影响业务（已切到新版本）
  │
  │ ▼ 步骤 3（ES 操作 — 仅 RAG_STORAGE_BACKEND=es 时执行；幂等）
  │   store.delete_by_space_version(space_id, embedding_version=from_v)
  │   # ES 实现：DELETE INDEX rag_{env}_{company}_v{from_v}
  │   # 失败：保持 status='CLEANUP_PENDING'，cleanup_retries += 1，cron 重试
  │
  │ ▼ 步骤 4（PG 事务 3 — 标记清理完成）
  │   UPDATE rag_migration_task SET status='SUCCEEDED' WHERE id=$migration_id;
  │
  └─ 分支 B：failed_entries > 0（失败路径，不切换）
      BEGIN TX;
        UPDATE rag_space SET
            status = 'MIGRATION_FAILED',
            pending_embedding_version = NULL,
            pending_embedding_provider = NULL,
            pending_embedding_model = NULL
          WHERE id = $space_id;
        UPDATE rag_migration_task SET
            status = 'FAILED',
            finished_at = NOW(),
            error_message = '已尝试 ${total} 条，失败 ${failed} 条'
          WHERE id = $migration_id;
      COMMIT;
      # 不清理旧版本（保持 from_v 可检索）；用户可通过 POST /retry 重试
      # 注意：此时新上传期间已写入的 to_v chunks 会"孤悬"，由 cron 在 retry
      #       场景中复用，或 retry 时由 migration_runner 跳过已存在 chunks
```

#### 7.3.4 崩溃恢复路径

| 崩溃位置 | DB 状态 | 恢复机制 |
|---|---|---|
| 迁移循环中（步骤 7.3.2） | `space.status=MIGRATING`, `migration_task.status=RUNNING`, `heartbeat_at` 不再更新 | cron 每 5 分钟扫 `status='RUNNING' AND heartbeat_at < NOW() - INTERVAL '15 minutes'`，标 `FAILED` + 写 `error_message='heartbeat_timeout'` + 把 `rag_space.status` 改为 `MIGRATION_FAILED` + 清 `pending_*`。用户可 POST `/retry` 恢复 |
| 步骤 1（切换 PG TX）提交前 | `space.status=MIGRATING`, `migration_task.status=RUNNING` | 同上（heartbeat 超时兜底） |
| 步骤 1 已提交，步骤 2/3 未完成 | `space.status=READY`（业务已切换）, `migration_task.status=CLEANUP_PENDING` | cron 每 10 分钟扫 `status='CLEANUP_PENDING' AND cleanup_retries < 3`，重做步骤 2/3；超过 3 次则记入 Sentry 报警，由运维介入（旧 chunks 占用存储，但不影响检索正确性） |
| 步骤 4 未执行 | `migration_task.status=CLEANUP_PENDING`，但数据已清理 | cron 重做步骤 2 时 DELETE 返回 0 行属正常；步骤 3 (DELETE INDEX) 在 ES 后端是幂等的；cron 检测到 DELETE 0 行 + ES index 不存在则推进到步骤 4 |

迁移中失败：单 entry 失败 → `failed_entries += 1` 继续；全部尝试结束后 `failed_entries > 0` → 走分支 B（status=FAILED，`rag_space.status=MIGRATION_FAILED`，**不清旧版本**）。

### 7.4 OCR 失败回退（部分成功）

```
pipeline.run_file(entry, mime='image/png'):
    │
    ▼ 1) loader = ImageLoader → 调 OCRProvider.recognize(file_path)
    │    （默认 Textract，失败回退 GPT-4o vision，决策 D1）
    │
    ├─ 成功且文本非空 → 走正常 split + embed + store → status=SUCCESS
    │
    └─ 失败或返回空文本：
        - UPDATE rag_entry SET status=PARTIAL,
              error_message='OCR 失败，已仅保留文件名可检索',
              chunk_count=0, total_tokens=0
        - 不写 rag_chunk（关键词召回直接用 rag_entry.title）
        - rag_ingestion_task.partial_count += 1

# 用户重试（决策 D2）：
POST /rag/entries/{id}/retry
    - 保留 entry.title / file_id / status=PARTIAL 不变
    - 新启 pipeline；成功改 SUCCESS，失败改 FAILED（不再 PARTIAL）
    - 关键词召回在重试全程不中断
```

---

## 8. 异常处理与错误码

### 8.1 业务异常分级

| 级别 | 来源 | 表现 |
|---|---|---|
| 用户错误 (4xx) | 参数校验 / 权限 / 资源不存在 | HTTPException + 明确 message |
| 系统错误 (5xx) | DB / 内部 bug | 返回通用 message，详情写日志（standards/coding.md §8）|
| 第三方错误 | LLM / Embedding / OCR / S3 | 内部重试，仍失败则映射到 entry.error_message 业务化文本 |

### 8.2 错误码约定

业务 code 按 `HTTP_STATUS * 100 + seq` 编码：

| code | 含义 |
|---|---|
| 0 | 成功 |
| 40001 | 参数校验失败 |
| 40002 | 单次上传超过 10 个文件 |
| 40003 | 文本超过 100,000 字 |
| 40004 | 检索 topK 超过 20 |
| 40101 | 缺少用户上下文 |
| 40301 | 跨公司访问 / 空间不可见 |
| 40302 | 普通用户访问他人个人空间 |
| 40303 | 非 admin 使用 admin-only 参数（如 retry `force=true`） |
| 40401 | 资源不存在 |
| 40901 | 同名空间已存在 |
| 40902 | 空间状态不支持该操作（如并发迁移被锁） |
| 40903 | 同名条目已存在 |
| 41301 | 文件过大 |
| 41501 | 不支持的文件类型 |
| 42201 | embedding 模型不支持（不在 1536 维白名单） |
| 50001 | 内部错误 |
| 50301 | LLM/Embedding 服务暂不可用 |

### 8.3 重试策略

| 调用 | 策略 |
|---|---|
| Embedding API | timeout=60s，指数退避 3 次（standards/coding.md §10）；并发上限 8（semaphore） |
| LLM (vision OCR) | 同上 |
| AWS S3 | boto3 默认（max_attempts=3） |
| AWS Textract | 同上 |
| DB | 不重试，立即失败 |

### 8.4 日志要求

- logger 名 `CIOaaS.rag.{submodule}`
- 禁止打印：query 全文（截断 200 字符）、user PII、API key
- 入库管线每个 stage 打 INFO；失败打 ERROR + `exc_info=True`
- **embedding 调用不写 `llm_call_log`**（决策 E1），token 数累加到 `rag_entry.total_tokens`；`llm_call_log` 保留给 chat 调用

---

## 9. 配置与环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `RAG_STORAGE_BACKEND` | `pg` | `pg` / `es`，部署期决定 |
| `RAG_DEFAULT_EMBEDDING_PROVIDER` | `openai` | 本期仅 openai |
| `RAG_DEFAULT_EMBEDDING_MODEL` | `text-embedding-3-small` | dim=1536，与 CHECK 白名单一致 |
| `RAG_DEFAULT_CHUNK_SIZE_DOC` | `800` | 文档类默认 |
| `RAG_DEFAULT_CHUNK_SIZE_TABLE` | `1200` | 表格类默认 |
| `RAG_DEFAULT_CHUNK_OVERLAP_DOC` | `100` | |
| `RAG_DEFAULT_CHUNK_OVERLAP_TABLE` | `0` | |
| `RAG_OCR_PROVIDER` | `textract` | `textract` / `vision` / `auto`（auto=优先 textract，失败回退 vision） |
| `RAG_MAX_FILE_SIZE_MB` | `50` | |
| `RAG_SINGLE_BATCH_MAX_FILES` | `10` | |
| `RAG_TEXT_MAX_CHARS` | `100000` | |
| `RAG_TOPK_MAX` | `20` | |
| `RAG_ENTRY_TIMEOUT_S` | `1800` | 单条目入库超时（30 分钟），超时由 cron 置 FAILED |
| `RAG_MIGRATION_TIMEOUT_S` | `14400` | 单次迁移整体超时（4 小时），用于初始化 `rag_migration_task.timeout_at`（R2） |
| `RAG_MIGRATION_HEARTBEAT_INTERVAL` | `10` | migration_runner 每处理 N 个 entry 更新一次 heartbeat（R2） |
| `RAG_MIGRATION_HEARTBEAT_TIMEOUT_S` | `900` | cron 判定迁移悬空的心跳阈值（15 分钟，R2） |
| `RAG_MIGRATION_CLEANUP_MAX_RETRIES` | `3` | 切换后清理失败的最大自动重试次数（R1） |
| `RAG_HOT_QUERY_WINDOW_DAYS` | `30` | |
| `RAG_SOFT_DELETE_WINDOW_DAYS` | `30` | |
| `RAG_ES_CLOUD_ID` / `RAG_ES_API_KEY` | — | ES 后端必需 |
| `RAG_PG_VECTOR_DIM` | `1536` | pgvector 列固定维度（本期；v2 多维度时按维度分表，本变量随之退场） |
| `RAG_HNSW_M` | `16` | 构建参数固定 |
| `RAG_HNSW_EF_CONSTRUCTION` | `64` | 构建参数固定 |
| `RAG_HNSW_EF_SEARCH` | `40` | 检索期参数（运行时 `SET LOCAL hnsw.ef_search = 40`） |
| `RAG_EMBED_BATCH_SIZE` | `96` | OpenAI 单批最多 96 inputs |
| `RAG_EMBED_CONCURRENCY` | `8` | embedder 并发 semaphore 上限 |
| `RAG_RRF_K` | `60` | Python 层 RRF 融合参数 |
| `RAG_ADMIN_ROLES` | `COMPANY_ADMIN,ADMIN` | 管理员角色白名单（决策 F1） |

---

## 10. 性能与监控

### 10.1 P95 < 3s（单空间）保证手段

1. **向量索引**：PG HNSW（`m=16, ef_construction=64`，固定）；ES 默认 HNSW
2. **预解析 embedding**：query 在调 store 之前 embed 一次，跨版本场景按 version 分组复用
3. **关键词 + 向量并行**：单空间内 `asyncio.gather()` 并行发起 keyword/vector 两路
4. **RRF 融合**：Python 层统一实现（`RAG_RRF_K=60`），两个后端行为一致（决策 C1）
5. **分页友好**：每路只取 `top_k * 3` 候选做融合，避免 over-fetch
6. **连接池**：复用 SQLAlchemy session（pool_size=10，max_overflow=10）

### 10.2 跨空间 < 5s（2-5 个）

- **关键修正（决策 C2）**：跨空间在 Python 层并发：`asyncio.gather([store.search_single_space(sid, ...) for sid in granted_space_ids])`，每条单空间 SQL 用 `WHERE space_id = $1`（单值过滤）才能命中 HNSW
- **不使用** `WHERE space_id = ANY(...)` —— 多值会让 pgvector HNSW 退化为 Seq Scan，无法满足 SLA
- **跨 embedding_version**：分别 embed query 一次，并行查询；本期由于单维度，version 路由仅按 space 当前 version
- **全局合并**：所有 space 的候选汇总，Python 层再做一次 RRF 取 top_k

### 10.3 监控埋点

- **Sentry**（已有）：捕获 unhandled exception
  - BackgroundTasks 内（pipeline_runner / migration_runner）顶层用 `sentry_sdk.new_scope()` + 设置 tags（entry_id / space_id / company_id / pipeline），finally 中 `sentry_sdk.flush()`（决策 H1）
- **New Relic**（已有）：标记 `/rag/**` transaction
- **新增 metrics**（写日志，由 New Relic 抽取）：
  - `rag.search.duration_ms`（带 tag: spaces_count, version_groups, backend）
  - `rag.search.rrf_candidates`（融合前候选数）
  - `rag.ingest.entry.duration_ms`（tag: source_type, mime_type）
  - `rag.ingest.entry.tokens`
  - `rag.migration.entries_per_min`
  - `rag.ocr.duration_ms` + `rag.ocr.success/fail` 计数（tag: provider=textract/vision）

---

## 11. 安全

### 11.1 鉴权

- 沿用 Java 网关验 JWT，注入 `x-user-id` / `x-company-id` / `x-user-role` 三个 HTTP 头
- Python 端 dependency `require_user_context()` 校验三个头缺一不可，缺则抛 401
- **管理员判定（决策 F1）**：
  - 解析 `x-user-role` 头
  - `ADMIN_ROLES = set(os.environ.get('RAG_ADMIN_ROLES', 'COMPANY_ADMIN,ADMIN').split(','))`
  - `is_admin = role in ADMIN_ROLES`
  - 不命中 admin 时按普通用户处理
- CHATBOT 调用：额外要求 `x-caller-type=CHATBOT` + `x-on-behalf-of-user-id`，按 on-behalf user 做权限裁剪
- 永远不暴露不带 user 的 service account（决策 A5=A，需求决策 A5）
- **待开发阶段确认**：Java 网关是否已在 `/api/rag/**` 注入 `x-user-role`、实际 admin role 值（详见 §15）

### 11.2 多租户隔离

- 所有 repository 查询**强制 `company_id` 过滤**（即使本接口已通过 space_id 间接限定）
- 列表查询 SQL 模板：`WHERE company_id = :ctx_company AND ...`，绝不允许走 SQL 拼接
- code review 时 grep `rag_` 表名 + `WHERE.*company_id`，每一处必须命中

### 11.3 上传防护

- MIME + 扩展名双重校验（前者由 `files.content_type` 提供，后者从 `files.original_name` 解析）
- 单文件 50MB 上限：直接读 `files.length`，不下载就拒
- 下载 S3 到本地临时目录走 `pathlib.Path.resolve()` + 限定 `/tmp/rag-ingest/` 白名单（standards/coding.md §9）
- S3 桶策略也限制单个 PUT 大小（部署侧配置）
- 删除条目时事务级联清理 chunks + 向量（`ON DELETE CASCADE` + `store.delete_by_entry()`）

### 11.4 OCR / Embedding 调用脱敏

- 日志只记录文件名与前 200 字符内容预览
- API key 通过 `EmbeddingFactory` 单例持有，不进入业务代码与日志

### 11.5 软删除清理

- 独立 cron 任务（本期复用现有 `consumer` 进程的定时器）每天 02:00 扫 `deleted_at < now() - 30 days` 的 `rag_space` / `rag_entry`，执行硬删除：
  ```sql
  DELETE FROM rag_chunk WHERE entry_id IN (...);
  DELETE FROM rag_entry WHERE id IN (...);
  DELETE FROM rag_space WHERE id IN (...);
  ```
- ES 后端同步调 `store.delete_by_entry`

### 11.6 BackgroundTasks 超时兜底

#### 11.6.1 入库任务超时（已有）

- cron 每 5 分钟扫 `rag_entry.status='PROCESSING' AND updated_at < now() - interval '1800s'` → 改为 FAILED + 写 error_message='超时'（应对单机崩溃，决策 B1）

#### 11.6.2 迁移任务超时（R2 / CRITICAL-2 新增）

- cron 每 5 分钟扫描悬空迁移任务：
  ```sql
  -- 心跳超时：15 分钟未更新 heartbeat
  SELECT id, space_id FROM rag_migration_task
    WHERE status = 'RUNNING'
      AND (heartbeat_at IS NULL AND started_at < NOW() - INTERVAL '15 minutes'
           OR heartbeat_at < NOW() - INTERVAL '15 minutes');
  ```
- 对每条悬空任务执行：
  ```sql
  BEGIN;
    UPDATE rag_migration_task SET
        status='FAILED',
        finished_at=NOW(),
        error_message='heartbeat_timeout'
      WHERE id=$1 AND status='RUNNING';
    UPDATE rag_space SET
        status='MIGRATION_FAILED',
        pending_embedding_version=NULL,
        pending_embedding_provider=NULL,
        pending_embedding_model=NULL
      WHERE id=$space_id AND status='MIGRATING';
  COMMIT;
  ```
- 用户在 `MIGRATION_FAILED` 状态可调用 `POST /rag/migrations/{id}/retry`（§6.2.14）恢复

#### 11.6.3 切换后清理重试（R1 新增）

- cron 每 10 分钟扫描 `CLEANUP_PENDING` 状态：
  ```sql
  SELECT id, space_id, from_version FROM rag_migration_task
    WHERE status='CLEANUP_PENDING' AND cleanup_retries < 3
    ORDER BY finished_at ASC LIMIT 50;
  ```
- 对每条执行步骤 2（DELETE 旧 PG chunks）+ 步骤 3（DELETE ES index）：
  - 全部成功 → `UPDATE status='SUCCEEDED'`
  - 任一失败 → `UPDATE cleanup_retries = cleanup_retries + 1, error_message=...`
  - `cleanup_retries >= 3` → 不再自动重试，写 Sentry，由运维介入（admin 可用 `POST /retry` 加 `force=true` 重新触发）

---

## 12. 测试策略

### 12.1 单元测试

| 模块 | 覆盖点 |
|---|---|
| `vectorizer/loaders/*` | 每种文件类型 happy path + 损坏文件 + 空内容 |
| `vectorizer/splitters/` | chunk_size / chunk_overlap 边界、OCR 内容保护 |
| `vectorizer/ocr/*_provider.py` | 成功 / 失败 / 空文本回退；Textract 失败回退到 Vision |
| `vectorizer/embedder.py` | 批次分片、token 计算、并发上限、重试 |
| `storage/pg_store.py` | upsert / search_single_space（含混合）/ delete by entry / by version；HNSW 命中校验 |
| `storage/es_store.py` | 同上（mock ESStorage）；不开 hybrid 的两次查询路径 |
| `service/space_service.py` | 同名校验、权限矩阵（管理员/普通/Chatbot）、模型变更触发迁移、SELECT FOR UPDATE 并发控制 |
| `service/search_service.py` | 权限裁剪、跨空间 gather、RRF 融合、PARTIAL 条目仅关键词路径 |
| `service/ingest_service.py` | PARTIAL retry 保留 metadata；成功覆盖 / 失败改 FAILED |
| `repository/*` | 各 SQL 查询，含分页、软删过滤 |

mock 策略：LLM / Embedding / OCR / S3 全部 mock；DB 用 testcontainers 起 postgres+pgvector。

### 12.2 集成测试

- 端到端入库：POST /rag/files (mock S3 下载) → 等 BackgroundTasks → GET /rag/tasks/{id} 看 success
- 端到端检索：建空间 → 入库 3 条 → 检索 → 命中数据 + 命中后统计 +1
- 端到端迁移：建空间 → 入库 → PUT 切换模型（同 1536 维内）→ 迁移完成 → 检索仍工作
- 并发迁移控制：两个并发 PUT 切换 → 第二个返回 409（SELECT FOR UPDATE 生效）

### 12.3 性能测试

- 单空间 5000 chunks → 检索 P95 < 3s
- 5 空间各 2000 chunks 跨空间 → 检索 P95 < 5s
- HNSW 命中验证：`EXPLAIN ANALYZE` 单空间 SQL 应显示 `Index Scan using idx_rag_chunk_embedding_hnsw`

### 12.4 覆盖率

`pytest --cov=rag --cov-report=term-missing`，目标 ≥ 80%（standards/coding.md §11）

---

## 13. 部署 / 迁移

### 13.1 数据库 migration

路径：`CIOaas-python/sql/migrations/`（决策 A5=A，已确认项目现状）
命名约定：`YYYY-MM-DD_rag_NNN_<purpose>.up.sql` / `.down.sql`（对照现有 `2026-05-26_llm_call_log_business_prefix.up.sql`）

按顺序新增的 9 个 migration 文件（v1.2 / R3 增加 001b）：

1. `2026-05-26_rag_001_alter_ai_files.up.sql` — 见 §4.1.1（6 步迁移：ADD purpose / 回填 / DROP NOT NULL / 数据验证 / ADD CHECK NOT VALID / 建索引）
1b. `2026-05-27_rag_001b_validate_ai_files_constraint.up.sql` — 低峰期单独执行：`ALTER TABLE ai_files VALIDATE CONSTRAINT chk_ai_files_purpose_task`
2. `2026-05-26_rag_002_create_extensions.up.sql`
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```
3. `2026-05-26_rag_003_create_rag_space.up.sql` — 含 CHECK 约束限定 1536 维白名单
4. `2026-05-26_rag_004_create_rag_ingestion_task.up.sql`
5. `2026-05-26_rag_005_create_rag_entry.up.sql`
6. `2026-05-26_rag_006_create_rag_chunk.up.sql` — `vector(1536)` + HNSW + trigram 索引
7. `2026-05-26_rag_007_create_rag_search_log.up.sql`
8. `2026-05-26_rag_008_create_rag_migration_task.up.sql`

每个 `.up.sql` 配对一个 `.down.sql` 回滚脚本（仅 rag_001 需要处理数据回填，其他直接 DROP TABLE）。

### 13.2 ES mapping 初始化

应用启动时（`rag/storage/es_store.py` 内）按公司+版本懒创建索引（首次写入时检测 + put_index），`dims=1536`。

### 13.3 esapiens 代码搬入步骤

1. 整体复制 `esapiens-python/esapiens/embedding_pipeline/` 到 `CIOaas-python/source/rag/vectorizer/`
2. **包路径替换**（全文 sed）：
   - `from esapiens.embedding_pipeline.` → `from rag.vectorizer.`
   - `from esapiens.common.logging_config import logging` → `from common.logger import get_logger; logger = get_logger(__name__)`
   - 删除 `from esapiens.vectore.*` / `from esapiens.integrations.*` 引用
3. **去除 sapien_id / paper_drawer 相关代码**（详细映射见 §5.3 表）：
   - `direct_text_loader.py` 的 `PaperDrawerTextConfig` → `DirectTextConfig(text_id, title, body, metadata)`
   - `factory_loader.py` 删除 `direct_text_loader` / `batch_direct_text_loader` 中 paper_drawer 参数
   - `es_storage.py` 删除 `sapien_id` / `paper_drawer` 分支，元数据字段重命名为 `{entry_id, space_id, company_id, embedding_version, ...}`；删除 publish/delete flag；**不开启 ES 自带 hybrid**
   - `image_loader.py` 的 OCR 调用改为依赖注入 `OCRProvider`（Textract 主 + Vision 备）
4. **依赖整合**：把 esapiens 用到的第三方库（pdfplumber、python-docx、openpyxl、ebooklib、Pillow、langchain-text-splitters、langchain-elasticsearch）补到 `CIOaas-python/requirements.txt`，版本对齐
5. **删除 csv_storage.py**（本期不用，RAG 全走 pg/es）

### 13.4 部署 checklist（决策 G1 / G2 / D1）

部署前由运维 + 开发联合确认：

- ☐ 生产 PG 部署方式（RDS / 自建 / Aurora）
- ☐ 生产 PG 版本 ≥ 14.5 / 15.2 / 16（支持 pgvector）
- ☐ 生产 pgvector 版本 ≥ 0.5.0（支持 HNSW）；自建 PG 需 `apt install postgresql-${VERSION}-pgvector`
- ☐ 执行 migration 的账号有 `CREATE EXTENSION` 权限（RDS 需 `rds_superuser` 角色）
- ☐ Java 财务模块 grep 所有 `INSERT INTO ai_files` / JPA `save(AiFile)` 代码路径，确认 `task_id` 都传值（避免 CHECK 约束生产违反）
- ☐ **执行数据层验证 SQL**（R3 / HIGH-2，必须在 migration 步骤 5 之前）：
  ```sql
  SELECT COUNT(*) FROM ai_files WHERE purpose='financial_extract' AND task_id IS NULL;
  ```
  期望返回 0；若非 0 则导出违反行清单 → 联合财务团队补数据 → 再继续 migration
- ☐ **选定低峰期执行 VALIDATE CONSTRAINT**（R3 / HIGH-2）：迁移上线后 24 小时内，挑业务低峰期执行 `2026-05-27_rag_001b_validate_ai_files_constraint.up.sql`
- ☐ 确认生产 AWS Textract 区域（建议 us-east-1）+ IAM 包含 `textract:DetectDocumentText` + `textract:AnalyzeDocument`
- ☐ Java 网关确认已在 `/api/rag/**` 反向代理时注入 `x-user-role` 头，并确认管理员的实际 role 值（更新 `RAG_ADMIN_ROLES`）
- ☐ ES 后端仅在公司活跃数 < 500 时启用（否则索引数膨胀，回退 `RAG_STORAGE_BACKEND=pg`）

### 13.5 配置开关

部署 yaml 新增：
```yaml
RAG_STORAGE_BACKEND: pg            # test=pg, prod=pg
RAG_DEFAULT_EMBEDDING_PROVIDER: openai
RAG_DEFAULT_EMBEDDING_MODEL: text-embedding-3-small
RAG_OCR_PROVIDER: textract
RAG_PG_VECTOR_DIM: 1536
RAG_ADMIN_ROLES: COMPANY_ADMIN,ADMIN
```

---

## 14. 风险与缓解

| 风险 | 缓解 |
|---|---|
| pgvector 在大数据量下 HNSW 内存占用大、写入慢 | 提供 `RAG_STORAGE_BACKEND=es` 切换路径；监控 `rag_chunk` 行数，超 100 万行预警，超 500 万行触发分区改造规划 |
| 模型迁移期间向量版本不一致 | `embedding_version` 字段双写、查询时按 space 当前版本路由、迁移完成原子切换 + 清旧 |
| OCR 成本失控 | 优先 Textract（按页计费可控）；记录 `rag.ocr.duration_ms` + 公司维度月度配额告警 |
| 跨公司数据泄漏 | repository 强制 `company_id` 过滤 + code review checklist 项 |
| 同一文件被多空间引用，删除时误清原 file | `ai_files` 表与 `rag_entry` 一对一（每空间一条 rag_entry + 一条 ai_files 行），删 entry 只软删 ai_files |
| BackgroundTasks 进程重启导致任务丢失 | rag_entry 状态 `PROCESSING` 超 `RAG_ENTRY_TIMEOUT_S` 由 cron 改为 FAILED；不引入额外队列（决策 B1=A） |
| 文本直传与文件去重逻辑差异 | 同名查重以 `rag_entry.title` 为准，文件 entry 的 title = files.original_name，文本 entry 的 title = 用户填的 title，统一字段统一逻辑 |
| 迁移期间空间被删除 | 删除时 `rag_migration_task.status=FAILED` 标记并停止 BackgroundTasks 工作循环（通过 polling rag_space.deleted 标志） |
| **v2 支持多维度需分表改造**（新增） | 本期 `rag_chunk.embedding` 固定 `vector(1536)`；v2 引入 `text-embedding-3-large(3072)` 等需要按维度分表 `rag_chunk_d1536` / `rag_chunk_d3072`，伴随 repository 路由与迁移工具改造（评估约 1 周工作量） |
| **中文 OCR 精度低于专用方案**（新增） | Textract 中文识别精度低于 Azure Document Intelligence / PaddleOCR；本期通过 `RAG_OCR_PROVIDER=vision` 切到 GPT-4o vision 兜底，作为 v1.x 优化项再评估接入专用中文 OCR |
| **BackgroundTasks 单机崩溃风险已知可接受**（新增） | 本期 MVP 不引入 SQS；单实例宕机会丢失内存中的入库/迁移任务，由 cron 超时兜底 + 用户手动重试承接；超大空间（10 万+ 条目）的迁移崩溃风险较高，列为 v1.x 升级项（迁移 runner 加"跳过已完成 entry"逻辑实现断点续跑，约 1-2 天） |
| **迁移切换跨存储 Saga 不一致**（v1.2 / R1 新增） | 迁移切换跨 PG（rag_space / rag_chunk）+ ES（INDEX），无法用 ACID 事务包裹。已采用 Saga：步骤 1（PG 切换 + 标记 CLEANUP_PENDING）原子提交后用户即视为完成；步骤 2/3（清旧数据）异步重试，失败不影响业务可见性；cron `RAG_MIGRATION_CLEANUP_MAX_RETRIES` 兜底，超限报 Sentry |
| **迁移任务悬空（runner 崩溃）**（v1.2 / R2 新增） | `rag_migration_task.heartbeat_at` + cron 心跳超时扫描（15 分钟），自动标 FAILED + 把 `rag_space.status` 改回 `MIGRATION_FAILED`，用户可 `POST /retry` 恢复 |

---

## 15. 已决断疑点 + 待开发阶段确认项

### 15.1 已决断的 16 个技术疑点（摘要）

| 编号 | 疑点 | 决策 | 文档落点 |
|---|---|---|---|
| A1 | pgvector 索引类型 | HNSW（`m=16, ef_construction=64`） | §4.2.4 |
| A2 | ES 索引粒度 | 公司+版本（`rag_{env}_{company}_v{n}`） | §4.3.1 |
| A3 | 向量维度 | **本期固定 1536 维**（CHECK 限定模型白名单；v2 再做多维度按维度分表） | §4.2.1 / §4.2.4 / §9 |
| A4 | 分区策略 | 本期不分区；超 500 万行再分区 | §14 |
| A5 | Migration 工具 | 沿用 `CIOaas-python/sql/migrations/` 手工 SQL；命名 `2026-05-26_rag_NNN_*.up/.down.sql` | §13.1 |
| B1 | BackgroundTasks 可靠性 | 接受单机崩溃风险 + cron 超时兜底；v1.x 升级到迁移断点续跑 | §11.6 / §14 |
| B2 | 并发迁移控制 | `SELECT FOR UPDATE` | §6.2.3 / §7.3 |
| C1 | 混合检索融合 | 统一 Python 层 RRF（ES 后端关闭 hybrid，分两次查） | §6.2.9 / §10.1 |
| C2 | 跨空间查询 SQL | **`asyncio.gather` 并发单空间查询**（单空间 SQL 用 `WHERE space_id = $1` 命中 HNSW） | §6.2.9 / §7.2 / §10.2 |
| D1 | OCR 选型 | Textract 主 + GPT-4o vision 备（`RAG_OCR_PROVIDER=auto`） | §5 / §13.4 |
| D2 | PARTIAL 重试 | 保留 metadata 不预先清除，成功覆盖 / 失败改 FAILED | §6.2.12 / §7.4 |
| E1 | Embedding 日志 | 不写 `llm_call_log`，只累加 `rag_entry.total_tokens` | §8.4 |
| F1 | 管理员判定 | Java 注入 `x-user-role` + Python `ADMIN_ROLES` 白名单 | §11.1 |
| G1 | pgvector 生产安装 | RDS PG（部署 checklist 验证版本与权限） | §13.4 |
| G2 | `ai_files.task_id` 改可空 | **DB CHECK 约束**（`purpose='rag' XOR task_id IS NULL`） | §4.1.1 |
| H1 | BackgroundTasks Sentry | `sentry_sdk.new_scope` + 设置 tags + `flush()` | §7.1 / §7.3 / §10.3 |

### 15.2 待开发阶段确认的 4 项

| 项目 | 何时确认 | 默认假设 | 不命中默认值时的影响 |
|---|---|---|---|
| 生产 PG 版本 + pgvector 版本 | 部署前由运维确认 | pgvector ≥ 0.5.0 | < 0.5.0 需先升级 RDS / 自建包 |
| Java 网关注入 `x-user-role` 与 admin role 值 | 开发阶段 Java 侧确认 | role 值 = `COMPANY_ADMIN`；header 已注入 | 若未注入需 Java 小改；若 role 值不同，更新 `RAG_ADMIN_ROLES` 环境变量即可 |
| 生产 AWS Textract 区域 + IAM 权限 | 部署前运维确认 | us-east-1 + 含 `textract:Detect/AnalyzeDocument` | 区域不支持需 cross-region 处理；权限缺失 Textract 调用失败 |
| Java 财务模块写 `ai_files` 是否都传 `task_id` | 开发前 grep 确认 | 都传 | 若某分支未传，CHECK 约束会拒插，需在 Java 端补；建议开发阶段第一天完成确认 |

### 15.3 自动头脑风暴的额外决策（已纳入设计）

- **esapiens 搬入映射表**（详见 §5.3）：明确 `embedding_pipeline/` 各子目录的搬入位置与本地化要点
- **Embedding 并发与限流**（已纳入 §9 / §12.1）：批次 96 / 并发 8 / 指数退避 3 次
- **检索鉴权降级**（已纳入 §6.2.9）：必须携带用户身份，不允许匿名
- **文件大小校验位置**（已纳入 §11.3）：Java 网关 + Python 双重校验 + S3 桶策略
- **测试 fixtures**（已纳入 §12.1）：mock 向量 fixtures + testcontainers-postgresql
- **S3 文件名编码**：S3 key = 已 URL-encode 的 `files.name`，展示用 `files.original_name`
- **迁移切换 Saga**（v1.2 / R1 新增）：跨 PG 和 ES 用 Saga 替代 ACID 事务，详见 §7.3.3
- **迁移心跳与超时恢复**（v1.2 / R2 新增）：`heartbeat_at` + cron 兜底，详见 §11.6.2

---

> **后续动作（v1.2）**：
> 1. v1.2 已处理 arch-reviewer 审查报告中 2 CRITICAL + 4 HIGH + 1 MEDIUM（共 6 项必修），其余 MEDIUM/LOW 在开发阶段内嵌处理
> 2. 进入 `/dev/gen-user-test-doc` 与 `/dev/run` 实现阶段
> 3. 开发阶段第一天必须完成 §15.2 的 4 项前置确认
> 4. 数据库迁移上线流程：先跑 `rag_001`（含 NOT VALID 灰度），24 小时内挑低峰期跑 `rag_001b`（VALIDATE CONSTRAINT）
