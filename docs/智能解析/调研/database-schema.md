# OCR Agent 数据库 Schema（权威定义）

> 本文件是**所有表、索引、权限、枚举值**的唯一权威定义。
> 其他设计文档（java-design / python-design / code-examples）**不再重复 DDL**，只保留业务语义说明并引用本文件章节。
> 任何新增/变更表结构必须先改这里，再同步到其他文档。
>
> **关联文档**: [设计理念](./design-philosophy.md) · [系统架构](./system-architecture.md) · [Java 端设计](./java-design.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md) · [需求分析](./requirement-analysis.md)

---

## 0. 物理部署模型

**决策（2026-04-20）**: Java 和 Python 共用**同一个** PostgreSQL RDS 实例、**同一个** schema。通过 PostgreSQL 角色（`java_app` / `python_worker`）实现读写隔离。

**理由**:
- 共享 schema 下 FK 约束可生效（如 `ai_ocr_extracted_table.file_id → doc_parse_file.id`）
- 跨库 JOIN 免配置（对比 Normalization 下游查询 fi_* 时不需要 FDW）
- 两个 RDS 实例比一个大实例运维成本高 ~40%
- 权限隔离通过 `GRANT` / `REVOKE` 即可，无需额外组件

**未来扩展**: 若 `mapping_memory` 增长到亿级，可拆到独立 pgvector 集群（Python 改连接串，Java 无感知）。

---

## 1. 扩展与枚举

### 1.1 PostgreSQL 扩展

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- 模糊匹配（记忆查询）
CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector（embedding 存储 + HNSW 索引）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- UUID 生成
```

### 1.2 枚举值清单（与代码 enum 严格对应）

#### Task 状态（22 个）

应用层 enum: `com.gstdev.cioaas.web.docparse.domain.enums.DocParseStatus`

| 状态 | 含义 | 可进入方式 | 后续状态 |
|------|------|-----------|---------|
| `DRAFT` | 任务已创建，待上传 | POST /tasks 或 /revise | UPLOADING / EXPIRED |
| `UPLOADING` | 文件上传中（presigned URL 阶段） | 首个 upload/complete 成功 | UPLOAD_COMPLETE / FAILED |
| `UPLOAD_COMPLETE` | 所有文件已上传（瞬态） | 最后一个 upload/complete | PROCESSING |
| `PROCESSING` | Python 解析中 | 首条 OcrProgress 消息 | SIMILARITY_CHECKING / FAILED |
| `SIMILARITY_CHECKING` | 相似度检测中 | 所有 file.status=REVIEW_READY | SIMILARITY_CHECKED / SIMILARITY_CHECK_FAILED |
| `SIMILARITY_CHECKED` | 检测完成（瞬态） | Python 返回相似度结果 | REVIEWING |
| `SIMILARITY_CHECK_FAILED` | 检测失败（embedding API 故障等） | Python 异常或 Sweeper 超时 | REVIEWING（兜底推进，不阻塞主流程） |
| `REVIEWING` | 用户审核中（Step 5 之前的 inline 审核） | SIMILARITY_CHECKED 或人工跳过 | MAPPING_SUMMARY / FAILED |
| `MAPPING_SUMMARY` | **Step 5a** 映射汇总展示（§4.9） | REVIEWING 完成（用户点 Next） | VERIFY_PENDING / REVIEWING（回退） |
| `VERIFY_PENDING` | **Step 5a** 用户已点击 Start Verification，等待后端启动 verify（§4.9） | MAPPING_SUMMARY + 用户点击 | VERIFYING / MAPPING_SUMMARY（回退停止 verify） |
| `VERIFYING` | **Step 5b** 冲突预检中 | VERIFY_PENDING 进入实际检测 | CONFLICT_RESOLUTION / REVIEWING（失败回退） |
| `CONFLICT_RESOLUTION` | **Step 5b** 用户解决冲突中（§4.10） | verify 返回有冲突 | COMMITTING / REVIEWING |
| `COMMITTING` | **Step 5c** 写入 fi_* 中（事务，§4.11） | POST /commit | COMMITTED / REVIEWING（失败回退，Q7 方案 B） |
| `COMMITTED` | fi_* 写入成功（瞬态，等记忆学习） | commit 事务成功 | MEMORY_LEARN_PENDING |
| `MEMORY_LEARN_PENDING` | 记忆学习排队 | AFTER_COMMIT 发 SQS | MEMORY_LEARN_IN_PROGRESS |
| `MEMORY_LEARN_IN_PROGRESS` | Python 正在学习 | Python 消费消息 | MEMORY_LEARN_COMPLETE / MEMORY_LEARN_FAILED |
| `MEMORY_LEARN_COMPLETE` | 学习完成（瞬态） | Python 学习成功 | COMPLETED |
| `MEMORY_LEARN_FAILED` | 学习失败（3 次重试后） | Python 失败 3 次 | COMPLETED（财务数据已写入，学习是锦上添花） |
| `COMPLETED` | 任务终态（成功） | 记忆学习完成或失败 | SUPERSEDED（被修订版替代） |
| `SUPERSEDED` | 被修订版替代 | 修订版 COMPLETED 时 | 终态 |
| `FAILED` | 任务失败（硬终态） | 全部文件 FILE_FAILED / Sweeper 超时 / VERIFYING 卡死 | 终态（只能 revise） |
| `EXPIRED` | DRAFT 过期（24h 未操作） | Sweeper 清理 | 终态 |

> **2026-05-06 更新**: 新增 `MAPPING_SUMMARY` / `VERIFY_PENDING` 两个状态，对应 Step 5 拆分后的 5a 子阶段（详见 [requirement-analysis.md §4.9](./requirement-analysis.md)）。

#### File 状态（8 个）

应用层 enum: `DocParseFileStatus`

| 状态 | 含义 |
|------|------|
| `PENDING` | 刚创建（DRAFT 阶段申请 presigned URL 时） |
| `UPLOADING` | 前端正在 PUT 到 S3 |
| `UPLOADED` | Java 已校验 S3 对象 + magic bytes，准备发 SQS |
| `QUEUED` | 已发 ocr-extract-queue，等待 Python 消费 |
| `PROCESSING` | Python 处理中（`processing_stage` 字段描述精确阶段） |
| `REVIEW_READY` | Python 处理完成，可供用户审核 |
| `FILE_COMMITTED` | 该文件数据已写入 fi_* |
| `FILE_FAILED` | 处理失败（上传或解析） |

#### Processing Stage（12 个子状态，仅 file.status=PROCESSING 时有效）

应用层 enum: `DocParseProcessingStage`

| Stage | 进度 % | 含义 |
|-------|-------|------|
| `PREPROCESS_PENDING` | 0-5 | Python consumer 收到消息，准备开始 |
| `PREPROCESSING` | 5-15 | PDF→图片 / Excel→JSON |
| `EXTRACTING` | 15-30 | AI Vision / 直接解析 |
| `CLASSIFYING` | 30-35 | 文档类型识别 |
| `MAPPING_RULE` | 35-45 | Layer 1 规则引擎 |
| `MAPPING_MEMORY_LOOKUP` | 45-55 | Layer 2 查询 mapping_memory |
| `MAPPING_MEMORY_APPLY` | 55-65 | 应用命中的记忆 |
| `MAPPING_MEMORY_COMPLETE` | 65-70 | 记忆阶段完成 |
| `MAPPING_LLM` | 70-85 | Layer 3 LLM 推理 |
| `VALIDATING` | 85-95 | 三要素硬验证 + 软警告 |
| `PERSISTING` | 95-100 | 写入 ai_ocr_* 表 |
| `REVIEW_READY` | 100 | 可供审核（最终态，file.status 也同步 REVIEW_READY） |

#### LG Category（19 个）

应用层 enum: `com.gstdev.cioaas.web.docparse.domain.enums.LGCategory`

```
Income Statement:    Revenue / COGS / S&M Expenses / R&D Expenses / G&A Expenses /
                     S&M Payroll / R&D Payroll / G&A Payroll / Other Income / Other Expense
Balance Sheet:       Cash / Accounts Receivable / R&D Capitalized / Other Assets /
                     Accounts Payable / Short Term Debt / Long Term Debt / Other Liabilities / Equity
特殊值:              UNMAPPED（兜底，不写入 fi_*，用户必须审核）
```

#### Conflict Action（2 个）

应用层 enum: `DocParseConflictAction`

| 值 | 含义 |
|------|------|
| `OVERWRITE` | 用修订版/新数据覆盖 fi_* 现有值 |
| `SKIP` | 保留 fi_* 现有值，丢弃本次数据 |

（Cancel 选项 Asana 2026-04-19 移除）

#### Upload Error（5 个）

应用层 enum: `DocParseUploadError`

| 值 | 含义 |
|------|------|
| `FILE_TOO_LARGE` | 单文件 > 20MB 或批量 > 100MB |
| `TYPE_NOT_SUPPORTED` | MIME 不在允许列表 |
| `CORRUPTED` | magic bytes 校验失败 |
| `BATCH_TOO_LARGE` | 批量总大小超限 |
| `DUPLICATE_NAME` | 同 company_id + file_hash 已存在（活跃状态） |

#### Notification Event Type（6 个，Q16 简化版：事件日志，不发送）

| 值 | 含义 |
|------|------|
| `PARSE_COMPLETE` | 所有文件处理 + 相似度检测完成 |
| `COMMIT_COMPLETE` | fi_* 写入成功 |
| `COMMIT_FAILED` | commit 事务失败（不进 FAILED，仅记录供运维分析） |
| `MEMORY_LEARN_COMPLETE` | 记忆学习完成 |
| `MEMORY_LEARN_FAILED` | 记忆学习 3 次重试失败 |
| `NEW_CLOSED_MONTH` | commit 引入新期间（触发 Benchmark 数据更新） |

---

## 2. Java 拥有的表（`doc_parse_*`）

归属 Java 域，由 `CIOaas-api` 的 `docparse` 包管理。Python 一般只有 SELECT 权限，少数例外明确标注。

### 2.1 doc_parse_task

```sql
CREATE TABLE doc_parse_task (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      BIGINT NOT NULL,
    uploaded_by     BIGINT NOT NULL,
    session_id      UUID,                                            -- 批次分组
    status          VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
        -- 20 个状态枚举，见 §1.2 Task 状态

    -- 版本化字段（2026-04-20 新增）
    parent_task_id  UUID REFERENCES doc_parse_task(id),
    revision_number INT NOT NULL DEFAULT 0,
    revision_reason VARCHAR(500),
    superseded_by   UUID REFERENCES doc_parse_task(id),

    -- 文件统计
    total_files     INT NOT NULL DEFAULT 0,
    completed_files INT NOT NULL DEFAULT 0,
    failed_files    INT NOT NULL DEFAULT 0,

    -- Step 5 拆分相关字段（2026-05-06 新增，需求 §4.9-4.14）
    mapping_changed_at        TIMESTAMPTZ,                           -- §4.13 用户最后一次修改 mapping 的时间（变更检测核心）
    mapping_snapshot_hash     VARCHAR(64),                           -- §4.13 进入 5a 时记录的 mapping 数据 SHA-256 hash
    has_extractable_data      BOOLEAN NOT NULL DEFAULT TRUE,         -- §4.12 false 表示绕过 mapping/conflict/write 流程
    extraction_skip_reason    VARCHAR(50),                           -- §4.12 跳过原因：NO_TABLES/NARRATIVE_ONLY/IMAGE_NO_DATA
    summary_cache             JSONB,                                 -- §4.9 5a 摘要缓存：{ "files": N, "types": N, "accounts": N, "computed_at": ... }
    committed_forecast_id     UUID,                                  -- §4.11 关联生成的新 committed forecast 版本（Proforma 写入产物）
    imported_statements_folder_id UUID,                              -- §4.11 关联 Documents 页 "Imported Statements" 文件夹

    completed_at    TIMESTAMPTZ,                                     -- 全部完成时间
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 约束：跳过原因仅在 has_extractable_data=false 时允许写入
    CHECK (
        (has_extractable_data = TRUE  AND extraction_skip_reason IS NULL) OR
        (has_extractable_data = FALSE AND extraction_skip_reason IN ('NO_TABLES', 'NARRATIVE_ONLY', 'IMAGE_NO_DATA'))
    )
);
```

**索引**:
```sql
CREATE INDEX idx_doc_parse_task_company
    ON doc_parse_task (company_id, created_at DESC);

CREATE INDEX idx_doc_parse_task_status
    ON doc_parse_task (status, updated_at)
    WHERE status NOT IN ('COMPLETED', 'SUPERSEDED', 'FAILED', 'EXPIRED');
    -- 只为"活跃"状态建索引，节约空间 + 加速 Sweeper 扫描

-- 修订链查询
CREATE INDEX idx_doc_parse_task_parent
    ON doc_parse_task (parent_task_id)
    WHERE parent_task_id IS NOT NULL;

-- 防并发修订（同 parent + 同 revision_number 唯一）
CREATE UNIQUE INDEX uq_doc_parse_task_parent_revision
    ON doc_parse_task (parent_task_id, revision_number)
    WHERE parent_task_id IS NOT NULL;

-- §4.13 mapping 变更检测：按 mapping_changed_at 查询最近变更的活跃任务
CREATE INDEX idx_doc_parse_task_mapping_changed
    ON doc_parse_task (mapping_changed_at DESC)
    WHERE mapping_changed_at IS NOT NULL
      AND status NOT IN ('COMPLETED', 'SUPERSEDED', 'FAILED', 'EXPIRED');

-- §4.12 过滤"无可提取数据"任务（Documents 页"Imported Statements"展示用）
CREATE INDEX idx_doc_parse_task_skipped
    ON doc_parse_task (company_id, created_at DESC)
    WHERE has_extractable_data = FALSE;
```

### 2.2 doc_parse_file

```sql
CREATE TABLE doc_parse_file (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES doc_parse_task(id),
    company_id      BIGINT NOT NULL,                                 -- 冗余，便于唯一约束
    filename        VARCHAR(500) NOT NULL,
    file_type       VARCHAR(10) NOT NULL,                            -- PDF/EXCEL/CSV/IMAGE
    file_size       BIGINT NOT NULL,                                 -- bytes
    file_hash       VARCHAR(64) NOT NULL,                            -- SHA-256 十六进制
    s3_bucket       VARCHAR(200) NOT NULL,
    s3_key          VARCHAR(1000) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        -- 8 个状态枚举，见 §1.2 File 状态
    processing_stage VARCHAR(32),                                    -- 12 子状态，见 §1.2
    progress_pct    SMALLINT DEFAULT 0,                              -- 0-100
    stage_detail    JSONB,                                           -- Python 透传，前端渲染细节
    upload_error    VARCHAR(20),                                     -- 5 种上传错误枚举
    error_message   TEXT,
    deleted         BOOLEAN NOT NULL DEFAULT false,                  -- 软删除

    -- §4.11 / §4.12 Imported Statements 文件夹同步标记（2026-05-06 新增）
    imported_statements_synced BOOLEAN NOT NULL DEFAULT FALSE,       -- 是否已同步到 Documents 页 "Imported Statements" 文件夹
    synced_at                  TIMESTAMPTZ,                          -- 最近一次同步时间

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**索引**:
```sql
CREATE INDEX idx_doc_parse_file_task
    ON doc_parse_file (task_id, status);

-- 重名文件校验：同 company 下同 hash 唯一（FAILED 的允许重上传）
CREATE UNIQUE INDEX idx_doc_parse_file_company_hash_active
    ON doc_parse_file (company_id, file_hash)
    WHERE deleted = false
      AND status != 'FILE_FAILED';

-- Sweeper 扫描用
CREATE INDEX idx_doc_parse_file_stuck_processing
    ON doc_parse_file (status, updated_at)
    WHERE status = 'PROCESSING';

-- §4.11 / §4.12 待同步到 Imported Statements 的文件
CREATE INDEX idx_doc_parse_file_pending_sync
    ON doc_parse_file (task_id, status)
    WHERE imported_statements_synced = FALSE
      AND deleted = FALSE;
```

### 2.3 doc_parse_notification（事件日志，Q16 简化版）

**用途**: 仅作为"任务状态变化事件"的审计日志，**不主动推送**（不发邮件/push/站内信）。用户通过 LG Dashboard 的"待处理任务"列表自行发现。

```sql
CREATE TABLE doc_parse_notification (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES doc_parse_task(id),
    company_id      BIGINT NOT NULL,
    event_type      VARCHAR(30) NOT NULL,                            -- 见 §1.2 Notification Event Type
    payload         JSONB,                                           -- 事件快照数据
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    -- 注意：无 recipient_id / channel / status / retry_count
    -- 不发送给任何人，用户自己来看
);
```

**索引**:
```sql
CREATE INDEX idx_doc_parse_notification_task
    ON doc_parse_notification (task_id, event_type, created_at DESC);

CREATE INDEX idx_doc_parse_notification_company_recent
    ON doc_parse_notification (company_id, created_at DESC);
```

### 2.4 doc_parse_conflict_note

**用途**: 冲突解决时用户填写的备注（支持 thread 多条回复，Story #7）。

```sql
CREATE TABLE doc_parse_conflict_note (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES doc_parse_task(id),
    conflict_id     UUID NOT NULL,                                   -- verify 阶段分配的冲突 ID
    parent_note_id  UUID REFERENCES doc_parse_conflict_note(id),     -- NULL = thread 顶层
    author_id       BIGINT NOT NULL,
    note_text       VARCHAR(2000) NOT NULL,
    auto_generated  BOOLEAN DEFAULT FALSE,                           -- 系统自动生成
    resolution      VARCHAR(20),                                     -- OVERWRITE/SKIP（仅顶层填充）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**索引**:
```sql
CREATE INDEX idx_doc_parse_conflict_note_task
    ON doc_parse_conflict_note (task_id, conflict_id, created_at);

CREATE INDEX idx_doc_parse_conflict_note_parent
    ON doc_parse_conflict_note (parent_note_id)
    WHERE parent_note_id IS NOT NULL;
```

### 2.5 doc_parse_memory_learn_log

**用途**: 记忆学习审计。**Python 有 INSERT 权限**（跨域写入例外，见 §4）。

```sql
CREATE TABLE doc_parse_memory_learn_log (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id              UUID NOT NULL REFERENCES doc_parse_task(id),
    attempt_number       INT NOT NULL DEFAULT 1,                     -- 第几次（最多 3 次）
    result               VARCHAR(20) NOT NULL,                       -- 'success' / 'failed'
    new_memory_count     INT NOT NULL DEFAULT 0,
    updated_memory_count INT NOT NULL DEFAULT 0,
    error_message        TEXT,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, attempt_number)                                 -- SQS at-least-once 幂等
);
```

**索引**:
```sql
CREATE INDEX idx_doc_parse_memory_learn_log_task
    ON doc_parse_memory_learn_log (task_id, attempt_number);

CREATE INDEX idx_doc_parse_memory_learn_log_failed
    ON doc_parse_memory_learn_log (result, created_at)
    WHERE result = 'failed';
```

### 2.6 doc_parse_commit_audit

**用途**: 记录每次 commit 对 fi_* 的写入操作（written / overwritten / skipped）。

```sql
CREATE TABLE doc_parse_commit_audit (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id          UUID NOT NULL REFERENCES doc_parse_task(id),
    row_id           UUID NOT NULL,                                  -- ai_ocr_extracted_row.id
    lg_category      VARCHAR(50) NOT NULL,
    reporting_period VARCHAR(10) NOT NULL,                           -- YYYY-MM
    action           VARCHAR(20) NOT NULL,                           -- 'written' / 'overwritten' / 'skipped'
    old_value        NUMERIC(20,4),
    new_value        NUMERIC(20,4),
    conflict_note_id UUID REFERENCES doc_parse_conflict_note(id),
    committed_by     BIGINT NOT NULL,
    committed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**索引**:
```sql
CREATE INDEX idx_commit_audit_task
    ON doc_parse_commit_audit (task_id, committed_at);

CREATE INDEX idx_commit_audit_period
    ON doc_parse_commit_audit (lg_category, reporting_period);
```

### 2.7 doc_parse_erasure_log

**用途**: GDPR "Right to be Forgotten" 擦除请求和执行审计。

```sql
CREATE TABLE doc_parse_erasure_log (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type        VARCHAR(20) NOT NULL,                         -- 'task' / 'user' / 'company'
    target_id          VARCHAR(50) NOT NULL,
    requested_by       BIGINT NOT NULL,
    reason             VARCHAR(500),
    status             VARCHAR(20) NOT NULL DEFAULT 'PENDING',       -- PENDING/PROCESSING/COMPLETED/FAILED
    s3_objects_deleted INT DEFAULT 0,
    db_records_deleted INT DEFAULT 0,
    error_message      TEXT,
    requested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at       TIMESTAMPTZ
);

CREATE INDEX idx_erasure_log_status
    ON doc_parse_erasure_log (status, requested_at);
```

### 2.8 doc_parse_similarity_hint（新增：相似度检测结果）

**用途**: 存储 Python 相似度检测器发现的"高相似度 account_label 对"，供前端 ReviewPage 顶部横幅展示。**Python 有 INSERT/UPDATE 权限**（跨域写入例外）。

```sql
CREATE TABLE doc_parse_similarity_hint (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id           UUID NOT NULL REFERENCES doc_parse_task(id),
    row_id_a          UUID NOT NULL,                                 -- ai_ocr_extracted_row.id（较小 ID）
    row_id_b          UUID NOT NULL,                                 -- ai_ocr_extracted_row.id（较大 ID）
    label_a           VARCHAR(200) NOT NULL,                         -- 冗余存储便于展示
    label_b           VARCHAR(200) NOT NULL,
    file_id_a         UUID NOT NULL,                                 -- 便于"跨文件相似"提示
    file_id_b         UUID NOT NULL,
    similarity_score  NUMERIC(4,3) NOT NULL,                         -- 0.900 ~ 1.000
    user_decision     VARCHAR(20),                                   -- 'MERGED' / 'IGNORED' / NULL
    decided_at        TIMESTAMPTZ,
    decided_by        BIGINT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- 唯一约束：同 task 下同一对 row 只记录一次（强制 row_id_a < row_id_b 去重）
    UNIQUE (task_id, row_id_a, row_id_b),
    CHECK (row_id_a < row_id_b),                                     -- 保证顺序，避免 (A,B) 和 (B,A) 同时存在
    CHECK (similarity_score >= 0.9 AND similarity_score <= 1.0)
);
```

**索引**:
```sql
CREATE INDEX idx_doc_parse_similarity_hint_task
    ON doc_parse_similarity_hint (task_id, user_decision)
    WHERE user_decision IS NULL;
    -- 仅索引"未处理"的 hint，前端查询快
```

**设计要点**:
- `row_id_a < row_id_b` 约束：避免同一对被记录两次（(A,B) 和 (B,A) 视为相同）
- `similarity_score >= 0.9` 约束：只存真正高相似度的（低相似度无业务价值）
- `user_decision` 三态：`NULL`（待处理，前端高亮）/ `'MERGED'`（用户选择合并）/ `'IGNORED'`（用户选择忽略）
- 不含 embedding 字段：embedding 存在 `ai_ocr_extracted_row.label_embedding`（§3.2），这里只存对比结果

---

## 3. Python 拥有的表（`ai_ocr_*` + `mapping_memory*`）

归属 Python 域，由 `CIOaas-python` 的 `source/ocr_agent/persistence/entities.py` 管理。Java 一般只有 SELECT 权限，`mapping_memory*` 无权限（商业机密）。

### 3.1 ai_ocr_extracted_table

```sql
CREATE TABLE ai_ocr_extracted_table (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id               UUID NOT NULL,                             -- 引用 doc_parse_file(id)
    table_index           INT NOT NULL DEFAULT 0,
    document_type         VARCHAR(20) NOT NULL DEFAULT 'MISC',       -- PNL/BALANCE_SHEET/CASH_FLOW/PROFORMA/MISC
    doc_type_confidence   VARCHAR(10) NOT NULL DEFAULT 'LOW',        -- HIGH/MEDIUM/LOW
    currency              VARCHAR(10) DEFAULT 'USD',
    currency_warning      BOOLEAN DEFAULT FALSE,
    detected_currencies   JSONB,                                     -- ["USD", "EUR", ...]
    source_page           INT,                                       -- PDF 页码
    source_sheet_name     VARCHAR(200),                              -- Excel sheet 名
    unresolved_period_count INT DEFAULT 0,                           -- 报告周期无法识别的列数
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- SQS 幂等：同 file_id + table_index 唯一
    UNIQUE (file_id, table_index)
);
```

### 3.2 ai_ocr_extracted_row（新增 label_embedding 列）

```sql
CREATE TABLE ai_ocr_extracted_row (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id        UUID NOT NULL REFERENCES ai_ocr_extracted_table(id) ON DELETE CASCADE,
    row_index       INT NOT NULL,
    account_label   VARCHAR(200) NOT NULL,                           -- 从 500 降到 200 防 token 炸弹
    section_header  VARCHAR(200),
    cell_values     JSONB NOT NULL,                                  -- { "2024-01": 12345.67, ... }
    is_header       BOOLEAN DEFAULT false,
    is_total        BOOLEAN DEFAULT false,
    user_edited     BOOLEAN DEFAULT false,
    deleted         BOOLEAN DEFAULT false,

    -- 相似度检测用（2026-04-20 新增）
    label_embedding VECTOR(1536),                                    -- text-embedding-3-small 维度

    UNIQUE (table_id, row_index)
);
```

**索引**:
```sql
CREATE INDEX idx_ai_ocr_extracted_row_table
    ON ai_ocr_extracted_row (table_id, row_index);

-- pgvector HNSW 索引（相似度检测）
CREATE INDEX idx_ai_ocr_row_embedding_hnsw
    ON ai_ocr_extracted_row USING hnsw (label_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE label_embedding IS NOT NULL;
```

**HNSW 参数说明**:
- `m = 16`: 每个节点的连接数（默认，balance 查询速度和索引大小）
- `ef_construction = 64`: 构建时的候选集大小（越大越准但建索引慢）
- `vector_cosine_ops`: 使用余弦相似度（与 OpenAI embedding 推荐操作符一致）
- `WHERE label_embedding IS NOT NULL`: 只索引已生成 embedding 的行，节约空间

### 3.3 ai_ocr_mapping_result

```sql
CREATE TABLE ai_ocr_mapping_result (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    row_id                 UUID NOT NULL REFERENCES ai_ocr_extracted_row(id) ON DELETE CASCADE,
    lg_category            VARCHAR(50) NOT NULL,                     -- 见 §1.2 LG Category
    confidence             VARCHAR(10) NOT NULL,                     -- HIGH/MEDIUM/LOW
    source                 VARCHAR(30) NOT NULL,
        -- rule_engine / company_memory / industry_common / llm / user_override
    original_ai_suggestion VARCHAR(50),                              -- 用户覆盖前的 AI 建议
    reasoning              TEXT,
    user_note              VARCHAR(2000),
    core_engine_version    VARCHAR(20),                              -- 映射引擎版本
    company_memory_version VARCHAR(64),                              -- 公司记忆版本哈希
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (row_id)                                                  -- 一行最多一条映射
);

-- 强校验：lg_category 必须是 19 分类 + UNMAPPED
ALTER TABLE ai_ocr_mapping_result ADD CONSTRAINT chk_lg_category
    CHECK (lg_category IN (
        'Revenue', 'COGS',
        'S&M Expenses', 'R&D Expenses', 'G&A Expenses',
        'S&M Payroll', 'R&D Payroll', 'G&A Payroll',
        'Other Income', 'Other Expense',
        'Cash', 'Accounts Receivable', 'R&D Capitalized', 'Other Assets',
        'Accounts Payable', 'Short Term Debt', 'Long Term Debt', 'Other Liabilities', 'Equity',
        'UNMAPPED'
    ));
```

### 3.4 ai_ocr_conflict_record

> **2026-05-06 更新**（需求 §4.10 Step 5b）: Note 字段从可选改为**必填**（主按钮在 Note 填好前禁用）；resolution 增加 `PENDING` 默认值；新增 `resolved_order` 字段供"按 metric+month 排序解决"使用。

```sql
CREATE TABLE ai_ocr_conflict_record (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id             UUID NOT NULL,                               -- 引用 doc_parse_task(id)
    company_id          BIGINT NOT NULL,
    document_type       VARCHAR(20) NOT NULL,
    reporting_month     INT NOT NULL,
    reporting_year      INT NOT NULL,
    data_classification VARCHAR(20) NOT NULL,
    lg_category         VARCHAR(50),                                 -- §4.10 metric 维度（用于 Save & Next 同 metric 跳转）
    existing_value      NUMERIC(20,4),                               -- §4.10 LG 中现有值（弹窗展示）
    mapped_value        NUMERIC(20,4),                               -- §4.10 映射 sum（弹窗展示）
    resolution          VARCHAR(20) NOT NULL DEFAULT 'PENDING',      -- §4.10 PENDING / OVERWRITE / SKIP
    note                VARCHAR(2000) NOT NULL DEFAULT '',           -- §4.10 必填备注（CHECK 约束保证非空）
    resolved_order      INT,                                         -- §4.10 用户解决顺序（按 metric+month 排序）
    resolved_by         BIGINT,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_conflict_resolution CHECK (resolution IN ('PENDING', 'OVERWRITE', 'SKIP')),
    -- §4.10 必填 note：只要 resolution 不是 PENDING（即用户已操作），note 必须非空
    CONSTRAINT chk_conflict_note_required CHECK (
        resolution = 'PENDING' OR length(trim(note)) > 0
    )
);
```

**索引**:
```sql
CREATE INDEX idx_ai_ocr_conflict_record_task
    ON ai_ocr_conflict_record (task_id, resolution, resolved_order);

-- §4.10 同 metric 内冲突按 month 排序（Save & Next 跳转逻辑）
CREATE INDEX idx_ai_ocr_conflict_record_metric
    ON ai_ocr_conflict_record (task_id, lg_category, reporting_year, reporting_month);
```

### 3.5 mapping_memory（两层架构：通用 + 公司）

```sql
CREATE TABLE mapping_memory (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id          BIGINT,                                      -- NULL = 通用层，非 NULL = 公司层
    source_term         VARCHAR(500) NOT NULL,
    normalized_category VARCHAR(50) NOT NULL,
    confidence          NUMERIC(3,2) NOT NULL DEFAULT 0.5,
    source              VARCHAR(20) NOT NULL DEFAULT 'user',         -- 'seed' / 'user' / 'admin'
    is_trusted          BOOLEAN NOT NULL DEFAULT FALSE,
    hit_count           INT NOT NULL DEFAULT 0,
    confirm_count       INT NOT NULL DEFAULT 0,
    reject_count        INT NOT NULL DEFAULT 0,
    archived_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, source_term) WHERE archived_at IS NULL
);
```

**索引**:
```sql
CREATE INDEX idx_mapping_memory_term_trgm
    ON mapping_memory USING gin (source_term gin_trgm_ops);          -- 模糊匹配

CREATE INDEX idx_mapping_memory_company
    ON mapping_memory (company_id);                                   -- 公司记忆查询

-- 同行业频率查询（Layer 2b fallback）
CREATE INDEX idx_mapping_memory_industry
    ON mapping_memory (normalized_category, source_term)
    WHERE company_id IS NOT NULL AND archived_at IS NULL AND is_trusted = true;
```

### 3.6 mapping_memory_audit

**用途**: 记忆变更审计（Python 的 SQS at-least-once 防护依赖 `idempotency_key`）。

```sql
CREATE TABLE mapping_memory_audit (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mapping_id      UUID NOT NULL REFERENCES mapping_memory(id),
    idempotency_key VARCHAR(128) NOT NULL,                           -- f"{task_id}:{row_id}"
    event_type      VARCHAR(20) NOT NULL,                            -- CREATE/CONFIRM/REJECT/ARCHIVE
    old_category    VARCHAR(50),
    new_category    VARCHAR(50),
    actor           VARCHAR(100) NOT NULL,                           -- user:{id} / admin:{id} / system
    reason          TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (idempotency_key)                                         -- 幂等保护
);
```

### 3.7 ai_ocr_extraction_skip_log（2026-05-06 新增）

**用途**: §4.12 边界用例审计 — 记录哪些文件因"无可提取数据"被跳过 mapping/conflict/write 流程。混合批次时也用此表区分"哪些文件走完整流程、哪些只入 Imported Statements"。

```sql
CREATE TABLE ai_ocr_extraction_skip_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID NOT NULL REFERENCES doc_parse_task(id),
    file_id     UUID NOT NULL REFERENCES doc_parse_file(id),
    skip_reason VARCHAR(50) NOT NULL,                                -- NO_TABLES / NARRATIVE_ONLY / IMAGE_NO_DATA
    detail      JSONB,                                               -- 可选：模型给出的判定依据（页面截图、文本片段统计等）
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_skip_reason CHECK (skip_reason IN ('NO_TABLES', 'NARRATIVE_ONLY', 'IMAGE_NO_DATA')),
    UNIQUE (task_id, file_id)                                        -- SQS at-least-once 幂等
);
```

**索引**:
```sql
CREATE INDEX idx_ai_ocr_extraction_skip_log_task
    ON ai_ocr_extraction_skip_log (task_id, detected_at DESC);

-- 审计/统计：按 reason 聚合
CREATE INDEX idx_ai_ocr_extraction_skip_log_reason
    ON ai_ocr_extraction_skip_log (skip_reason, detected_at DESC);
```

### 3.8 ai_ocr_mapping_change_log（2026-05-06 新增）

**用途**: §4.13 Step Navigation 边界用例 — 追踪用户在 5a/5b 阶段回退后修改 mapping 的次数和影响范围。每次 `mapping_snapshot_hash` 变化都记录一条；`downstream_invalidated_count` 字段记录因此清空了多少条已解决的 conflict_record（决定是否需要 reprocess + 用户提示文案）。

```sql
CREATE TABLE ai_ocr_mapping_change_log (
    id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                       UUID NOT NULL REFERENCES doc_parse_task(id),
    changed_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    old_snapshot_hash             VARCHAR(64),                       -- 修改前的 hash（首次变更时为 NULL）
    new_snapshot_hash             VARCHAR(64) NOT NULL,              -- 修改后的 hash
    downstream_invalidated_count  INT NOT NULL DEFAULT 0,            -- 此次变更清空了多少 conflict_record（reset 为 PENDING）
    triggered_by                  BIGINT NOT NULL,                   -- 触发用户 ID
    change_summary                JSONB                              -- 可选：差异概要（哪些 row 的 lg_category 变了）
);
```

**索引**:
```sql
CREATE INDEX idx_ai_ocr_mapping_change_log_task
    ON ai_ocr_mapping_change_log (task_id, changed_at DESC);

-- 仅索引"实际触发了下游失效"的变更（无失效的变更对运维排查无用）
CREATE INDEX idx_ai_ocr_mapping_change_log_invalidated
    ON ai_ocr_mapping_change_log (task_id, changed_at DESC)
    WHERE downstream_invalidated_count > 0;
```

---

## 4. 数据库角色与权限

```sql
-- 角色创建
CREATE ROLE java_app LOGIN PASSWORD '***';
CREATE ROLE python_worker LOGIN PASSWORD '***';

-- schema 访问权限
GRANT USAGE ON SCHEMA public TO java_app, python_worker;

-- =================================================================
-- Java 拥有的表（doc_parse_*）
-- =================================================================

-- Java 完全访问
GRANT SELECT, INSERT, UPDATE, DELETE ON
    doc_parse_task,
    doc_parse_file,
    doc_parse_notification,
    doc_parse_conflict_note,
    doc_parse_memory_learn_log,
    doc_parse_commit_audit,
    doc_parse_erasure_log,
    doc_parse_similarity_hint
TO java_app;

-- Python 只读（查状态用）
GRANT SELECT ON
    doc_parse_task,
    doc_parse_file,
    doc_parse_notification,
    doc_parse_conflict_note,
    doc_parse_commit_audit,
    doc_parse_erasure_log
TO python_worker;

-- ⚠️ 跨域写入例外（2 张表）
-- Python 需要 INSERT 这两张表（异步回调场景），但无 UPDATE/DELETE 权限，不能篡改
GRANT INSERT ON doc_parse_memory_learn_log TO python_worker;
GRANT INSERT, UPDATE ON doc_parse_similarity_hint TO python_worker;
-- similarity_hint 需要 UPDATE 是因为 Python 可能多次触发检测（覆盖旧结果）
-- user_decision 字段由 Java 更新（用户在 UI 点击合并/忽略时）

-- =================================================================
-- Python 拥有的表（ai_ocr_* + mapping_memory*）
-- =================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON
    ai_ocr_extracted_table,
    ai_ocr_extracted_row,
    ai_ocr_mapping_result,
    ai_ocr_conflict_record,
    mapping_memory,
    mapping_memory_audit
TO python_worker;

-- Java 只读 ai_ocr_*（commit 时读取用）
GRANT SELECT ON
    ai_ocr_extracted_table,
    ai_ocr_extracted_row,
    ai_ocr_mapping_result,
    ai_ocr_conflict_record
TO java_app;

-- Java 对 ai_ocr_conflict_record 需要 UPDATE（5b 用户解决冲突时写 resolution / note / resolved_order）
GRANT UPDATE ON ai_ocr_conflict_record TO java_app;

-- =================================================================
-- 2026-05-06 新增表（Step 5a/5b/5c 边界用例支持）
-- =================================================================

-- ai_ocr_extraction_skip_log：Python 写入（提取阶段判定），Java 读取（5a 决定是否跳过流程）
GRANT INSERT, SELECT ON ai_ocr_extraction_skip_log TO python_worker;
GRANT SELECT ON ai_ocr_extraction_skip_log TO java_app;

-- ai_ocr_mapping_change_log：Java 写入（5a 入口 + Previous 回退检测），Python 只读（学习阶段了解修改频次）
GRANT SELECT, INSERT ON ai_ocr_mapping_change_log TO java_app;
GRANT SELECT ON ai_ocr_mapping_change_log TO python_worker;

-- ⚠️ Java 无权访问 mapping_memory*（跨公司商业机密）
-- 不需要 GRANT，默认 DENY

-- =================================================================
-- fi_* 财务表（Java 写，Python 零权限）
-- =================================================================

GRANT SELECT, INSERT, UPDATE ON fi_* TO java_app;
-- Python 零权限，显式 REVOKE 所有 fi_* 表（防止误授予）
REVOKE ALL ON fi_financial_data FROM python_worker;
REVOKE ALL ON fi_metrics FROM python_worker;
-- 其他 fi_* 表同理
```

---

## 5. 数据生命周期

### 5.1 文件保留策略（S3）

```
0-90 天    Standard Tier   频繁访问（审核中、已提交待比对）
90-180 天  Glacier Tier    低频访问（历史追溯）
180 天后   自动删除        除非 task 处于 COMPLETED + 合规要求保留
```

实现方式：S3 Lifecycle Policy + Java `DocParseArchiveScheduler`（日级 cron）。

### 5.2 DB 记录清理

| 表 | 保留策略 |
|----|---------|
| `doc_parse_task` | 永久（审计） |
| `doc_parse_file` | 180 天后 s3_key 清空（对象已删除），记录保留 |
| `doc_parse_notification` | 180 天（事件日志，按需查询） |
| `doc_parse_conflict_note` | 永久（审计） |
| `doc_parse_memory_learn_log` | 永久（审计） |
| `doc_parse_commit_audit` | 永久（fi_* 数据溯源关键） |
| `doc_parse_similarity_hint` | 与 task 同生命周期（180 天） |
| `ai_ocr_*` | 180 天后清理原始数据，保留 aggregated 统计 |
| `ai_ocr_extraction_skip_log` | 永久（审计：哪些上传无可提取数据） |
| `ai_ocr_mapping_change_log` | 与 task 同生命周期（180 天，调试用） |
| `mapping_memory` | 18 个月未命中的标记待审核（月度 cron） |

### 5.3 GDPR 擦除流程

触发：用户 / 公司发起 Right to be Forgotten 请求。

```
1. 写入 doc_parse_erasure_log，status=PENDING
2. DocParseErasureService:
   a. 删除 S3 对象（立即，不走 Lifecycle）
   b. 软删除 doc_parse_file（deleted=true，保留审计记录，清空 s3_key 和 filename）
   c. 硬删除 ai_ocr_extracted_row / ai_ocr_extracted_table（含 embedding）
   d. 硬删除 doc_parse_similarity_hint
   e. 保留 doc_parse_task 记录（但清空 revision_reason 等 PII 字段）
   f. 保留 doc_parse_memory_learn_log / doc_parse_commit_audit（审计不可删）
   g. 如有 mapping_memory 条目 company_id = target → 归档（archived_at=now）
3. 更新 erasure_log.status=COMPLETED, s3_objects_deleted, db_records_deleted
```

---

## 6. 变更历史

| 日期 | 变更 |
|------|------|
| 2026-04-16 | 初始版本：Java `doc_parse_*` 基础表 + Python `ai_ocr_*` + `mapping_memory*` |
| 2026-04-17 | 加入 Asana 2026-04-17 Story 更新字段（currency_warning、unresolved_period_count 等） |
| 2026-04-19 | 新增 `doc_parse_conflict_note`（Story #7）；Cancel 移除 |
| 2026-04-20 | 新增 `parent_task_id`/`revision_number`/`revision_reason`/`superseded_by`（修订） |
| 2026-04-20 | 新增 `doc_parse_memory_learn_log`（记忆学习审计） |
| 2026-04-20 | 新增 `doc_parse_commit_audit` / `doc_parse_erasure_log` DDL |
| 2026-04-20 | `doc_parse_notification` 简化为事件日志（Q16） |
| 2026-04-20 | 所有表加 UNIQUE 约束防 SQS at-least-once 重复 |
| 2026-04-20 | `ai_ocr_extracted_row.account_label` 从 500 降到 200（防 token 炸弹） |
| 2026-04-20 | 新增 `ai_ocr_extracted_row.label_embedding VECTOR(1536)` + HNSW 索引 |
| 2026-04-20 | 新增 `doc_parse_similarity_hint` 表（相似度检测结果） |
| 2026-04-20 | Task 状态重命名：NOTIFYING→SIMILARITY_CHECKING, NOTIFIED→SIMILARITY_CHECKED, NOTIFY_FAILED→SIMILARITY_CHECK_FAILED |
| 2026-05-06 | Step 5 拆分（需求 §4.9-4.14）：Task 状态新增 `MAPPING_SUMMARY` / `VERIFY_PENDING`（5a） |
| 2026-05-06 | `doc_parse_task` 扩展 7 个字段：`mapping_changed_at` / `mapping_snapshot_hash`（§4.13）、`has_extractable_data` / `extraction_skip_reason`（§4.12）、`summary_cache`（§4.9）、`committed_forecast_id` / `imported_statements_folder_id`（§4.11）+ CHECK 约束 |
| 2026-05-06 | `doc_parse_file` 扩展 `imported_statements_synced` / `synced_at`（§4.11/§4.12 Imported Statements 同步标记） |
| 2026-05-06 | `ai_ocr_conflict_record` 扩展（§4.10）：`note` 必填（CHECK 约束）、`resolution` 默认 PENDING、新增 `resolved_order` / `lg_category` / `existing_value` / `mapped_value` |
| 2026-05-06 | 新增 `ai_ocr_extraction_skip_log`（§4.12 无可提取数据审计） |
| 2026-05-06 | 新增 `ai_ocr_mapping_change_log`（§4.13 Previous 导航变更追踪） |
| 2026-05-06 | GRANT 更新：Java 获 `ai_ocr_conflict_record` UPDATE 权限；新表权限分配（Python 写 skip_log、Java 写 change_log） |
| 2026-05-06 | 新增索引：`mapping_changed_at` / `has_extractable_data=FALSE` / Imported Statements pending sync / 冲突按 metric 排序 |
