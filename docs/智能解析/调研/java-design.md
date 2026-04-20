# OCR Agent Java 端设计 (CIOaas-api)

> **技术栈**: Java 17 + Spring Boot 3 + Spring Cloud Gateway + AWS S3/SQS
> **关联文档**: [系统架构](./system-architecture.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md)

---

## 1. 模块结构

### 1.1 包结构

在现有 DDD 结构下新增 `docparse` 域（与 `fi/`、`quickbooks/`、`storage/` 同级），采用 4 层 DDD 架构：

```
com.gstdev.cioaas.web.docparse/
├── interfaces/                    ← 入口层（Interfaces Layer）
│   ├── controller/
│   │   └── DocParseController.java        # REST 端点：upload + status + confirm
│   └── vo/
│       ├── request/
│       │   ├── DocParseUploadReqVo.java              # 上传请求 VO
│       │   ├── DocParseReviewReqVo.java              # 审核编辑请求 VO
│       │   ├── DocParseConflictResolutionReqVo.java  # 冲突解决请求（含 notes）[2026-04-19]
│       │   └── DocParseNoteReplyReqVo.java           # Note thread 追加请求 [2026-04-19]
│       └── response/
│           ├── DocParseUploadRespVo.java             # 上传响应 VO
│           ├── DocParseStatusRespVo.java             # 状态查询响应 VO
│           ├── DocParseResultRespVo.java             # 提取结果响应 VO
│           ├── DocParseVerifyRespVo.java             # Verify Data Summary 响应 [2026-04-19]
│           ├── DocParseConflictListRespVo.java       # 冲突列表 + Summary 响应 [2026-04-19]
│           └── DocParseNoteThreadRespVo.java         # Note thread 响应 [2026-04-19]
│
├── application/                   ← 应用层（Application Layer）
│   ├── service/
│   │   ├── DocParseService.java            # 服务接口
│   │   ├── DocParseServiceImpl.java        # 上传 → S3 → 创建 task → 发 SQS
│   │   ├── DocParseQueryService.java       # 状态/结果查询
│   │   ├── DocParseReviewService.java      # 用户审核编辑保存
│   │   ├── DocParseVerifyService.java      # [2026-04-19] 执行 Verify + 冲突检测
│   │   ├── DocParseConflictService.java    # [2026-04-19] 冲突解决方案保存
│   │   ├── DocParseNoteService.java        # [2026-04-19] Note thread 管理
│   │   └── DocParseCommitService.java      # 两阶段 commit：整体事务写 fi_* + 触发 normalization + 邮件 + 记忆学习 SQS
│   └── dto/
│       ├── DocParseTaskDto.java            # 跨层 Task DTO
│       ├── DocParseFileDto.java            # 跨层 File DTO
│       ├── DocParseConflictDto.java        # [2026-04-19] 冲突项 DTO
│       ├── DocParseExtractMessageDto.java  # ocr-extract-queue 消息体
│       ├── DocParseResultMessageDto.java   # ocr-result-queue 消息体
│       └── DocParseMemoryLearnMessageDto.java # ocr-memory-learn-queue 消息体
│
├── domain/                        ← 领域层（Domain Layer）
│   ├── entity/
│   │   ├── DocParseTask.java               # JPA Entity: task 元数据
│   │   ├── DocParseFile.java               # JPA Entity: 文件记录（含 file_hash 用于重名校验）
│   │   └── DocParseConflictNote.java       # [2026-04-19] JPA Entity: 冲突 note (支持 thread)
│   ├── repository/
│   │   ├── DocParseTaskRepository.java     # JpaRepository
│   │   ├── DocParseFileRepository.java     # JpaRepository（含 findByCompanyIdAndFileHash）
│   │   └── DocParseConflictNoteRepository.java  # [2026-04-19] JpaRepository
│   └── enums/
│       ├── DocParseStatus.java             # PENDING/PROCESSING/COMPLETED/FAILED
│       ├── DocParseFileType.java           # PDF/EXCEL/CSV/IMAGE
│       ├── DocParseUploadError.java        # 5 种上传错误枚举（FILE_TOO_LARGE / TYPE_NOT_SUPPORTED / CORRUPTED / BATCH_TOO_LARGE / DUPLICATE_NAME）
│       └── DocParseConflictAction.java     # [2026-04-19] OVERWRITE / SKIP（Cancel 已移除）
│
└── infrastructure/                ← 基础设施层（Infrastructure Layer）
    ├── processor/
    │   ├── OcrExtractSqsProducer.java      # 发送 ocr-extract-queue
    │   ├── OcrResultSqsProcessor.java      # 消费 ocr-result-queue (implements MessageProcessor)
    │   └── OcrMemoryLearnSqsProducer.java  # 发送 ocr-memory-learn-queue（commit 后触发）
    ├── client/
    │   └── （目前无外部 client，预留扩展位）
    └── config/
        └── DocParseProperties.java         # 模块配置（最大文件大小、批量大小、保留天数等）
```

**为什么是 4 层 DDD 而非扁平结构？**

这个结构与现有 `quickbooks/`、`fi/` 等域完全一致（实际代码的 `interfaces/application/domain/infrastructure` 4 层模式）。优势：
- **interfaces 层** 隔离外部协议（HTTP/SQS），便于切换通信方式
- **application 层** 编排业务流程，不含技术细节
- **domain 层** 是纯业务模型，不依赖框架
- **infrastructure 层** 实现外部资源访问（DB/SQS/S3）
- VO 与 DTO 分离：VO 跨进程边界（前端↔Controller），DTO 跨层边界（Service↔Service）

### 1.2 与现有模块的集成点

| 集成点 | 文件 | 操作 |
|--------|------|------|
| 文件上传 | `storage/service/FileServiceImpl.java` | 复用现有 S3 上传能力 |
| SQS 队列注册 | `sqs/enums/InitSqsQueueEnum.java` | 新增 `OcrExtractQueue` / `OcrResultQueue` / `OcrMemoryLearnQueue` |
| SQS 消息类型 | `sqs/enums/SqsMessageType.java` | 新增 `OcrExtract` / `OcrResult` / `OcrMemoryLearn` |
| 消息处理器注册 | `sqs/service/MessageProcessorManager.java` | 自动扫描 `@PostConstruct`（无需手工注册） |
| 参考实现模板 | `quickbooks/infrastructure/processor/QuickbooksSqsProcessor.java` | 对照其 Producer/Processor 模板实现 OCR 的三个处理器 |

---

## 2. API 端点

**Asana Story #6 2026-04-19 重构为两阶段提交流程**：verify → resolve conflicts → commit

```
# 上传/状态
POST   /api/v1/docparse/upload                      # 上传文件（multipart）
GET    /api/v1/docparse/tasks/{id}/status            # 轮询处理状态
GET    /api/v1/docparse/tasks/{id}/result            # 获取提取结果

# 审核编辑
PATCH  /api/v1/docparse/tasks/{id}/review            # 保存用户编辑

# 提交流程（两阶段，2026-04-19 新增 verify）
POST   /api/v1/docparse/tasks/{id}/verify            # 触发 Verify Data Summary + 冲突检测（异步）
GET    /api/v1/docparse/tasks/{id}/verify/status     # 查询 verify 进度
GET    /api/v1/docparse/tasks/{id}/conflicts         # 获取冲突列表 + Summary
POST   /api/v1/docparse/tasks/{id}/resolve           # 提交冲突解决方案（含 notes）
POST   /api/v1/docparse/tasks/{id}/commit            # 所有冲突解决后，写入 fi_* 表（整体事务）

# Note thread（Story #7 2026-04-19）
GET    /api/v1/docparse/notes/{conflictId}           # 获取某冲突的 note thread
POST   /api/v1/docparse/notes/{conflictId}/reply     # 追加 note 到 thread
```

**Cancel 选项已移除**（Asana 2026-04-19）。用户若要放弃提交直接退出页面，task 状态保持 REVIEWING。

---

## 3. 数据表设计

### 3.1 doc_parse_task 表

```sql
-- Task 生命周期
CREATE TABLE doc_parse_task (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      BIGINT NOT NULL,
    uploaded_by     BIGINT NOT NULL,
    session_id      UUID,  -- groups multiple files
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    total_files     INT NOT NULL DEFAULT 0,
    completed_files INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.2 doc_parse_file 表

```sql
-- 上传文件记录
CREATE TABLE doc_parse_file (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES doc_parse_task(id),
    company_id      BIGINT NOT NULL,       -- 冗余存储，支持按公司建立唯一约束
    filename        VARCHAR(500) NOT NULL,
    file_type       VARCHAR(10) NOT NULL,
    file_size       BIGINT NOT NULL,
    file_hash       VARCHAR(64) NOT NULL,  -- 用于重名文件校验（同公司同 hash 算重名）
    s3_bucket       VARCHAR(200) NOT NULL,
    s3_key          VARCHAR(1000) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_message   TEXT,
    deleted         BOOLEAN NOT NULL DEFAULT false,  -- 软删除标记
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.3 doc_parse_conflict_note 表（Story #7 2026-04-19 新增）

存储冲突解决 note。支持 note thread（父子引用）和自动生成默认 note。

```sql
CREATE TABLE doc_parse_conflict_note (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES doc_parse_task(id),
    conflict_id     UUID NOT NULL,                                 -- 关联冲突项（由 verify 阶段分配）
    parent_note_id  UUID REFERENCES doc_parse_conflict_note(id),   -- 支持 thread（NULL = 顶层 note）
    author_id       BIGINT NOT NULL,                                -- 作者 user_id（系统自动生成时为系统用户）
    note_text       VARCHAR(2000) NOT NULL,
    auto_generated  BOOLEAN DEFAULT FALSE,                          -- 系统自动生成的默认 note
    resolution      VARCHAR(20),                                    -- "OVERWRITE" / "SKIP"（仅顶层 note 填充）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_doc_parse_conflict_note_task
    ON doc_parse_conflict_note (task_id, conflict_id, created_at);

CREATE INDEX idx_doc_parse_conflict_note_parent
    ON doc_parse_conflict_note (parent_note_id)
    WHERE parent_note_id IS NOT NULL;
```

**说明**:
- `parent_note_id` 为 NULL 的是 thread 的顶层 note（冲突初次解决时创建）
- 追加 note 时设置 `parent_note_id = <顶层 note id>`，形成 thread 结构
- `auto_generated = true` 标记系统在用户不填写时自动创建的默认 note
- Note 在 `doc_parse_task.status = COMPLETED` 后变为只读（应用层强制）

### 3.4 索引

```sql
-- 扩展
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- Java 端索引
CREATE INDEX idx_doc_parse_task_company
    ON doc_parse_task (company_id, created_at DESC);

CREATE INDEX idx_doc_parse_file_task
    ON doc_parse_file (task_id, status);

-- 重名文件校验：同 company 下同 hash 唯一
-- 仅对"活跃"记录生效；FAILED/归档/删除的允许重新上传同名文件
CREATE UNIQUE INDEX idx_doc_parse_file_company_hash_active
    ON doc_parse_file (company_id, file_hash)
    WHERE deleted = false
      AND status IN ('PENDING', 'PROCESSING', 'COMPLETED');
```

---

## 4. SQS 集成

### 4.1 发送提取消息 (infrastructure/processor/OcrExtractSqsProducer -> ocr-extract-queue)

上传文件成功后，Java 向 `ocr-extract-queue` 发送一条消息，触发 Python 端 AI 提取。**一条消息对应一个文件**（不是一个 session），原因：独立重试、天然并发、部分失败隔离。

**消息 Schema (Java -> Python)**:

```json
{
  "messageType": "OcrExtract",
  "queueName": "ocr-extract-queue",
  "batchId": "uuid",
  "sendTime": "2026-04-16T10:00:00Z",
  "uuid": "msg-uuid",
  "sessionId": "session-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "s3Bucket": "lg-prod-files",
  "s3Key": "ocr-uploads/123/session-uuid/file-uuid/2024_PnL.pdf",
  "filename": "2024_PnL.pdf",
  "contentType": "application/pdf",
  "fileSize": 2048576,
  "uploadedBy": "user-uuid",
  "callbackMeta": {
    "totalFiles": 3,
    "fileIndex": 1
  }
}
```

### 4.2 消费结果消息 (infrastructure/processor/OcrResultSqsProcessor <- ocr-result-queue)

Python 端完成 AI 提取和映射后，向 `ocr-result-queue` 发送结果消息。Java 端 `OcrResultSqsProcessor`（implements `MessageProcessor`，由 `MessageProcessorManager` 在 `@PostConstruct` 阶段自动扫描注册）消费此消息，更新 `doc_parse_task` 表状态。

**消息 Schema (Python -> Java)**:

```json
{
  "messageType": "OcrResult",
  "queueName": "ocr-result-queue",
  "batchId": "uuid",
  "sendTime": "2026-04-16T10:00:15Z",
  "uuid": "msg-uuid",
  "sessionId": "session-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "status": "completed",
  "extractedTableCount": 2,
  "totalRows": 47,
  "processingTimeMs": 12340,
  "error": null
}
```

### 4.3 发送记忆学习消息 (infrastructure/processor/OcrMemoryLearnSqsProducer -> ocr-memory-learn-queue)

用户确认提交后，Java 成功写入 `fi_*` 财务表，随即向 `ocr-memory-learn-queue` 发送记忆学习消息。Python 端对比 AI 原始建议 vs 用户最终确认，**只有被用户修正过的映射才存入记忆**。

**消息 Schema (Java -> Python)**:

```json
{
  "messageType": "OcrMemoryLearn",
  "queueName": "ocr-memory-learn-queue",
  "uuid": "msg-uuid",
  "sendTime": "2026-04-16T10:05:00Z",
  "taskId": "task-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "mappingComparisons": [
    {
      "accountLabel": "AWS Infrastructure",
      "originalAiCategory": "R&D Expenses",
      "confirmedCategory": "COGS",
      "wasOverridden": true
    },
    {
      "accountLabel": "Total Revenue",
      "originalAiCategory": "Revenue",
      "confirmedCategory": "Revenue",
      "wasOverridden": false
    }
  ]
}
```

**Python 记忆学习逻辑**:
- 只处理 `wasOverridden: true` 的条目
- `wasOverridden: false` 的忽略（AI 猜对了，不需要存记忆）
- 对比 `originalAiCategory` vs `confirmedCategory`，将修正存入 `mapping_memory`
- 如果已有同公司同标签的记忆，更新 `confirm_count` + `normalized_category`

### 4.4 队列配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `visibilityTimeout` | 300s (5 分钟) | 50 页 PDF 处理需要 ~60s，留足余量 |
| `maxReceiveCount` | 3 | 3 次重试后进 DLQ |
| `messageRetentionPeriod` | 345600s (4 天) | 与现有队列一致 |
| DLQ | 共享 `dlq-queue` | 通过 `messageType=OcrExtract` 区分 |

### 4.5 错误处理

| 场景 | 处理方式 |
|------|----------|
| Python 处理中崩溃 | 消息不可见超时后重新出现，SQS 自然重试 |
| AI 模型超时 | Python 捕获异常，发送 `status=failed` 结果消息 |
| 瞬态故障（S3 读取、网络） | SQS 重试（最多 3 次，指数退避） |
| 所有重试耗尽 | 进 DLQ，Java 通过 `QueueMessageLog.isDlq=true` 追踪 |
| 结果消息发送失败 | Python 通过 SQS 回调通知 Java 更新状态；Java 轮询时 fallback 查 Python 表 |

---

## 5. 业务流程

### 5.1 上传流程

```
用户上传文件 (multipart)
    → ① 校验文件 (MIME + magic bytes + 文件大小)
    → ①.5 计算文件 SHA-256 hash → 查 doc_parse_file 是否已存在同 company_id + file_hash
          → 若存在则抛 DUPLICATE_NAME 错误
    → ② 存入 S3 (ocr-uploads/{companyId}/{sessionId}/{fileId}/filename)
    → ③ 创建 doc_parse_task 记录 (status=PENDING)
    → ④ 创建 doc_parse_file 记录（写入 file_hash）
    → ⑤ 发送 SQS 消息到 ocr-extract-queue (每文件一条)
    → ⑥ 返回 202 {taskId, sessionId}
```

**关键细节**:
- 文件校验在 S3 写入前执行（扩展名 + magic bytes 双重校验）
- 重名检测在 S3 写入前执行，避免浪费 S3 写入和 SQS 消息额度
- 重名判定口径：同 `company_id` + 同 `file_hash`（SHA-256）视为重名，与原始文件名无关
- 批量上传时，一个 session 包含多个 file，每个 file 独立一条 SQS 消息
- 返回 202 (Accepted) 而非 200，表明异步处理已启动

### 5.2 状态查询

```
前端轮询 (每 2 秒)
    → GET /api/v1/docparse/tasks/{id}/status
    → 查 doc_parse_task 表
    → 返回 {status, progress, completedFiles, totalFiles}
```

**状态枚举**:
- `PENDING` — task 已创建，等待 Python 处理
- `PROCESSING` — Python 正在提取/映射
- `COMPLETED` — 所有文件处理完成，等待用户审核
- `FAILED` — 处理失败（部分或全部文件）

### 5.3 审核编辑

```
用户在审核页面修改数据
    → PATCH /api/v1/docparse/tasks/{id}/review
    → 保存用户对提取行数据和映射分类的修改
    → 更新 ai_ocr_extracted_row.user_edited = true
    → 更新 ai_ocr_mapping_result (如用户修改了分类)
```

**编辑范围**:
- 修改行项的 account_label
- 修改行项的数值
- 修改 AI 映射的 LG 分类
- 删除不需要的行（软删除: `deleted = true`）

### 5.4 确认提交流程（Asana 2026-04-19 重构为两阶段）

**阶段一：Verify Data Summary（冲突预检）**

```
用户在 ReviewPage 点击 "Next"
    → POST /api/v1/docparse/tasks/{id}/verify （异步）
    → 后端执行:
        ① 统计: 源文件总数 / 映射类型数 / 映射账户数
        ② 与 fi_* 对比: 检测同 company + 同 metric + 同 reporting_period 的冲突
        ③ 构建 DocParseVerifyRespVo 返回
    
前端显示 VerifyDataSummary 屏幕（摘要 + 进度条）
用户点击 "Start Verification" → 触发异步 verify
前端轮询 GET /api/v1/docparse/tasks/{id}/verify/status
完成后 GET /api/v1/docparse/tasks/{id}/conflicts 获取冲突列表
```

**阶段二：Conflict Resolution + Commit**

```
用户针对每个冲突选择（Cancel 已移除，只剩 Overwrite/Skip）:
    ○ Overwrite: 映射值覆盖 LG 现有值，旧值保留为历史记录
    ○ Skip: 保留 LG 现有值，跳过该指标

可选填写 Note（Story #7 2026-04-19 更新）:
    - 手动输入 → 写入 doc_parse_conflict_note
    - 不填写 → 系统自动生成默认 note（auto_generated=true）
    - 支持 note thread（parent_note_id）

用户解决所有冲突后点击 Commit
    → POST /api/v1/docparse/tasks/{id}/resolve （保存解决方案）
    → POST /api/v1/docparse/tasks/{id}/commit
    → 后端执行（@Transactional，整体成功或失败）:
        ① 读取 ai_ocr_extracted_row + ai_ocr_mapping_result
        ② 按 resolution 策略写入 fi_* 财务表
        ③ 记录 doc_parse_commit_audit（written/overwritten/skipped）
        ④ 无论是否提取到财务账户，把源文件记录到 Company Documents 页面
        ⑤ 触发下游 Normalization 流程
        ⑥ 如果存在新的 reporting period → 触发新闭月邮件通知
        ⑦ 构建 mappingComparisons 发送 ocr-memory-learn-queue（Python 学习）
        ⑧ 返回 200 {success, writtenPeriods, skippedItems}
    → 任何一步失败 → ROLLBACK，不允许部分写入
```

**关键约束（2026-04-19 强化）**:

- **整体事务**: `@Transactional(propagation=REQUIRED, rollbackFor=Exception.class)` 包裹 commit 逻辑
- **部分写入禁止**: 任何一个 metric 写入失败，整个 commit 回滚
- **Cancel 已移除**: 用户放弃提交 → 直接退出页面，task 状态保持 REVIEWING
- **源文件始终记录**: 无论是否提取到账户，上传文件都出现在 Company Documents
- **新闭月邮件**: Java 职责（不是 Python），写入成功后通过 EventBridge/邮件服务触发
- **记忆学习触发**: 仅在 commit 成功后，只学习 `wasOverridden: true` 的条目

### 5.5 DTO / VO 契约（新增）

```java
// Verify 响应
class DocParseVerifyRespVo {
    UUID verifyJobId;            // 异步任务 ID
    String status;               // PENDING/RUNNING/COMPLETED/FAILED
    VerifySummary summary;       // completed 时填充
    List<ConflictItem> conflicts;
}

class VerifySummary {
    int totalFiles;
    int totalMappedTypes;
    int totalMappedAccounts;
}

class ConflictItem {
    UUID conflictId;
    String lgMetric;
    String reportingPeriod;      // YYYY-MM
    BigDecimal currentLgValue;
    BigDecimal mappedResultSum;
    String cellRowRef;           // UI 高亮定位
}

// Resolve 请求
class DocParseConflictResolutionReqVo {
    List<Resolution> resolutions;
}

class Resolution {
    UUID conflictId;
    String action;               // "OVERWRITE" | "SKIP"（Cancel 已移除）
    String userNote;             // 可选，≤2000 字符
}
```

---

## 6. 安全要求

### 6.1 移除 FileController @AnonymousAccess

| 问题 | 严重级别 | 位置 | 修复方案 |
|------|---------|------|----------|
| 上传端点 `@AnonymousAccess` 无认证 | **CRITICAL** | `FileController.java` | 移除 `@AnonymousAccess`，加 JWT 认证 |

所有 `/api/v1/docparse/*` 端点必须通过 JWT 认证，不允许匿名访问。

### 6.2 上传时校验 MIME + magic bytes

| 问题 | 严重级别 | 位置 | 修复方案 |
|------|---------|------|----------|
| 无 MIME 类型校验就写入 S3 | **HIGH** | `FileServiceImpl.java` | 上传时校验扩展名 + magic bytes |

允许的 MIME 类型白名单：
- `application/pdf`
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `text/csv`
- `image/jpeg`、`image/png`、`image/tiff`

校验流程：先检查文件扩展名，再读取文件头 magic bytes 确认真实类型，两者必须一致。

### 6.3 SQS 消息加 HMAC 签名

| 问题 | 严重级别 | 位置 | 修复方案 |
|------|---------|------|----------|
| SQS 消息无签名 | **HIGH** | `SqsMessage.java` | 加 HMAC-SHA256 签名字段 |

每条 SQS 消息附加 `hmacSignature` 字段，使用共享密钥对消息体做 HMAC-SHA256 签名。消费端在处理前必须校验签名有效性。

### 6.4 消费前校验 file -> company 归属

| 问题 | 严重级别 | 位置 | 修复方案 |
|------|---------|------|----------|
| SQS 消息中 companyId 未做归属校验 | **HIGH** | `SQSMessageListener.java` | 消费前校验 file -> company 归属 |

`OcrResultSqsProcessor` 消费结果消息时，必须校验 `fileId` 对应的 `doc_parse_file` 记录的 `task_id` → `doc_parse_task.company_id` 与消息中的 `companyId` 一致，防止跨公司数据越权。

### 6.5 其他安全措施

| 问题 | 严重级别 | 修复方案 |
|------|---------|----------|
| 静态 IAM 密钥而非实例角色 | **HIGH** | 改为 EC2/ECS 实例角色 |
| 跨服务 DB 无角色隔离 | **HIGH** | 分 `java_app` / `python_worker` 角色 |

**S3 权限划分**:

```
Java IAM Role:
  s3:PutObject  → ocr-uploads/*    (写)
  s3:GetObject  → ocr-uploads/*    (读)
  sqs:SendMessage → ocr-extract-queue

Python IAM Role:
  s3:GetObject  → ocr-uploads/*    (只读)
  sqs:ReceiveMessage → ocr-extract-queue
  sqs:DeleteMessage  → ocr-extract-queue
  sqs:SendMessage    → ocr-result-queue
```

**数据库角色隔离**:

| 角色 | 权限 |
|------|------|
| `java_app` | 完全访问 Java 拥有的表 + `SELECT` 权限访问 Python 表 |
| `python_worker` | 完全访问 Python 拥有的表 + `SELECT` 权限访问 `doc_parse_task`、`doc_parse_file`（查状态） + 零权限访问 `fi_*` 表 |
