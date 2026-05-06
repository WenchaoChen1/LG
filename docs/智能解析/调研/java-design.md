# OCR Agent Java 端设计 (CIOaas-api)

> **技术栈**: Java 17 + Spring Boot 3 + Spring Cloud Gateway + AWS S3/SQS
> **关联文档**: [设计理念](./design-philosophy.md) · [需求分析](./requirement-analysis.md) · [系统架构](./system-architecture.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md)

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
│       ├── DocParseStatus.java             # Task 完整 20 值枚举（见 §3.1）
│       │                                     # DRAFT / UPLOADING / UPLOAD_COMPLETE / PROCESSING /
│       │                                     # SIMILARITY_CHECKING / SIMILARITY_CHECKED / SIMILARITY_CHECK_FAILED / REVIEWING /
│       │                                     # VERIFYING / CONFLICT_RESOLUTION / COMMITTING / COMMITTED /
│       │                                     # MEMORY_LEARN_PENDING / MEMORY_LEARN_IN_PROGRESS /
│       │                                     # MEMORY_LEARN_COMPLETE / MEMORY_LEARN_FAILED /
│       │                                     # COMPLETED / SUPERSEDED / FAILED / EXPIRED
│       ├── DocParseFileStatus.java         # PENDING / UPLOADING / UPLOADED / QUEUED / PROCESSING /
│       │                                     # REVIEW_READY / FILE_COMMITTED / FILE_FAILED
│       ├── DocParseProcessingStage.java    # 12 子状态（见 §3.2 comment）
│       ├── DocParseFileType.java           # PDF/EXCEL/CSV/IMAGE
│       ├── DocParseUploadError.java        # 5 种上传错误枚举
│       └── DocParseConflictAction.java     # [2026-04-19] OVERWRITE / SKIP（Cancel 已移除）
│
└── infrastructure/                ← 基础设施层（Infrastructure Layer）
    ├── processor/
    │   ├── OcrExtractSqsProducer.java          # 发送 ocr-extract-queue（per file）
    │   ├── OcrSimilarityCheckSqsProducer.java  # ★ 新增：发送 ocr-similarity-check-queue
    │   │                                         # （per task，所有 file.status=REVIEW_READY 后触发）
    │   ├── OcrResultSqsProcessor.java          # 消费 ocr-result-queue (implements MessageProcessor)
    │   │                                         # 按 messageType 分发到 4 个 handler:
    │   │                                         #   - OcrProgress → updateFileProgressStage()
    │   │                                         #   - OcrResult → updateFileComplete()
    │   │                                         #   - OcrSimilarityCheckResult → updateTaskSimilarityStatus()
    │   │                                         #   - OcrMemoryLearnProgress → updateTaskMemoryLearnStatus()
    │   └── OcrMemoryLearnSqsProducer.java      # 发送 ocr-memory-learn-queue（AFTER_COMMIT 后触发）
    ├── client/
    │   └── S3PresignedUrlClient.java       # 生成 presigned PUT/GET URL，封装 AWS SDK
    ├── scheduler/
    │   └── DocParseTaskSweeper.java        # [新增] @Scheduled 每 2min 扫描僵尸态 task
    │                                          - DRAFT > 24h → EXPIRED + 清理 S3 staging
    │                                          - PROCESSING > 20min 且 Python 表有数据 → 推进 REVIEW_READY
    │                                          - VERIFYING > 10min → FAILED（verify 代码卡死）
    │                                          - MEMORY_LEARN_IN_PROGRESS > 10min → MEMORY_LEARN_FAILED
    │                                          注：SIMILARITY_CHECKING 不需要 sweeper（Q16 简化后为瞬态）
    │                                          注：COMMITTING 不需要 sweeper（Q7 方案 B 下事务失败自动回 REVIEWING）
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
| 文件上传 | `storage/service/FileServiceImpl.java` | 新的 Presigned URL 流程由 `S3PresignedUrlClient` 封装，与现有 FileService 并存 |
| SQS 队列注册 | `sqs/enums/InitSqsQueueEnum.java` | 新增 `OcrExtractQueue` / `OcrResultQueue` / `OcrMemoryLearnQueue`（3 个都注册，即使 Java 只消费 OcrResultQueue） |
| SQS 消息类型 | `sqs/enums/SqsMessageType.java` | 新增 `OcrExtract` / `OcrResult` / `OcrProgress` / `OcrMemoryLearn` / `OcrMemoryLearnProgress`（5 种，覆盖所有发送/接收场景） |
| SQS Listener | `sqs/listener/SQSMessageListener.java` | **新增 `onOcrResultQueue()` 方法**（@SqsListener 消费 ocr-result-queue）；`ocr-extract-queue` 和 `ocr-memory-learn-queue` Java 只发送不消费，无需新增 Listener |
| 消息处理器注册 | `sqs/service/MessageProcessorManager.java` | 自动扫描 `@PostConstruct`（无需手工注册） |
| 事务边界 | Spring `@TransactionalEventListener` | **关键**：Commit / Revise 等涉及发 SQS 的业务必须使用 `@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)` 确保事务提交后才发消息（见 §5.4） |
| 参考实现模板 | `quickbooks/infrastructure/processor/QuickbooksSqsProcessor.java`（纯 Producer 参考）<br>其他 Processor（如 QuickbooksSyncProcessor）实现了 `MessageProcessor` 接口的消费模式 | Producer 不 implements MessageProcessor；Consumer 必须 implements MessageProcessor 并注册 |

---

## 2. API 端点

**重要变更（2026-04-20）**:
- 文件上传改为 **S3 Presigned URL 直传**（前端直传 S3，不经 Java）
- 文件查看使用 **Presigned GET URL**（前端直查 S3）
- 新增 Task 修订 / 通知查询 / 记忆学习进度端点

```
# ============ Task 生命周期 ============
POST   /api/v1/docparse/tasks                        # 新建 task（DRAFT）
POST   /api/v1/docparse/tasks/{id}/revise            # ★ 基于历史 task 创建修订版
GET    /api/v1/docparse/tasks/{id}/status            # 轮询处理状态（task + files 聚合）
GET    /api/v1/docparse/tasks/{id}/result            # 获取提取结果
GET    /api/v1/docparse/tasks/{id}/history           # ★ 查看 task 版本链

# ============ 上传（S3 Presigned URL 直传）★ ============
POST   /api/v1/docparse/upload/request-urls          # ★ 请求 presigned PUT URLs
POST   /api/v1/docparse/upload/complete              # ★ 通知 Java 单文件上传完成
POST   /api/v1/docparse/upload/abort                 # 取消上传（删 S3 对象）

# ============ 文件查看（Presigned GET URL）★ ============
POST   /api/v1/docparse/files/{fileId}/download-url  # ★ 生成 presigned GET URL（15 min）

# ============ 审核编辑 ============
PATCH  /api/v1/docparse/tasks/{id}/review            # 保存用户编辑

# ============ 提交流程（Step 5a / 5b / 5c，2026-05-06 拆分）============
# 5a — Mapping Summary Page（[requirement-analysis §4.9](./requirement-analysis.md#49-step-5a--mapping-summary-page2026-05-06-新增)）
GET    /api/v1/docparse/tasks/{id}/mapping-summary   # ★ 5a 页面摘要（文件/类型/账户数 + hard gate 检查结果）
POST   /api/v1/docparse/tasks/{id}/verify/start      # ★ 5a 用户点击 "Start Verification" 触发后端冲突检测
GET    /api/v1/docparse/tasks/{id}/verify/progress   # ★ 5a 实时进度指示器轮询端点（替代旧 verify/status）

# 5b — Conflict Resolution（[requirement-analysis §4.10](./requirement-analysis.md#410-step-5b--conflict-resolution-of-manual-uploads2026-05-06-新增)）
GET    /api/v1/docparse/tasks/{id}/conflicts         # 获取冲突列表（仅 Actuals 参与；Proforma 整体豁免）
POST   /api/v1/docparse/tasks/{id}/conflicts/{conflictId}/resolve  # ★ 单冲突解决（Note 必填硬校验，返回下一冲突定位）

# 5c — Commit & Display Results（[requirement-analysis §4.11](./requirement-analysis.md#411-step-5c--commit-uploaded-data-to-lg--display-results2026-05-06-新增)）
POST   /api/v1/docparse/tasks/{id}/commit            # 整批写入 fi_*（@Transactional，含 Proforma 追加新版本）
GET    /api/v1/docparse/tasks/{id}/commit/result     # ★ 5c 写入结果摘要（账户数、报告周期、文档类型、Imported Statements 文件夹定位、Benchmark 跳转参数）

# 兼容保留（旧端点，逐步废弃）
POST   /api/v1/docparse/tasks/{id}/verify            # 旧 verify 触发；已被 verify/start 替代
POST   /api/v1/docparse/tasks/{id}/resolve           # 旧批量 resolve；§4.10 改为单冲突逐个解决

# ============ Steps Navigation（[requirement-analysis §4.13](./requirement-analysis.md#413-edge-case--steps-navigation2026-05-06-新增)）============
POST   /api/v1/docparse/tasks/{id}/navigate-back     # ★ Previous 回退；返回是否需要重跑下游 + 已清空的 conflict 数

# ============ 通知（新增）★ ============
GET    /api/v1/docparse/tasks/{id}/notifications     # ★ 查询 task 通知发送状态
POST   /api/v1/docparse/notifications/{id}/retry     # ★ 手动重试失败的通知

# ============ 相似度检测结果（新增）★ ============
GET    /api/v1/docparse/tasks/{id}/similarity-hints       # ★ 查询 task 的相似度提示（未处理 + 已处理）
PATCH  /api/v1/docparse/similarity-hints/{hintId}         # ★ 用户决策（MERGED / IGNORED）

# ============ 记忆学习进度（新增）★ ============
GET    /api/v1/docparse/tasks/{id}/memory-learn          # ★ 查询记忆学习最新状态 + 统计
GET    /api/v1/docparse/tasks/{id}/memory-learn/history  # ★ 查询记忆学习所有历史尝试记录
POST   /api/v1/docparse/tasks/{id}/memory-learn/retry    # ★ 手动重试失败的记忆学习（前置条件 attempt_number < 3）

# ============ Note Thread（Story #7）—— RESTful 嵌套 ============
GET    /api/v1/docparse/tasks/{taskId}/conflicts/{conflictId}/notes    # 获取 note thread
POST   /api/v1/docparse/tasks/{taskId}/conflicts/{conflictId}/notes    # 追加 note 到 thread
```

**路径嵌套原因**: Note 是 Conflict 的子资源，Conflict 是 Task 的子资源。嵌套路径天然支持 URL 级别的权限校验（通过 taskId → company_id 链路）。

### 2.1 S3 Presigned URL 上传流程详细说明

旧 multipart 经 Java 中转方案已废弃（Java 服务器带宽瓶颈）。新方案 3 次 HTTP 调用：

**步骤 1：前端请求预签名 URL**

```json
POST /api/v1/docparse/upload/request-urls
Request:
{
  "taskId": "uuid",
  "files": [
    {"name": "2024_PnL.pdf", "size": 2048576, "type": "application/pdf", "hash": "sha256..."}
  ]
}

Java 处理:
  ├─ JWT + company 归属校验
  ├─ 预校验：大小/扩展名/hash 重名（查 ai_ocr_file）
  └─ 每个合法文件：
      ├─ 建 ai_ocr_file [status=PENDING]
      └─ 生成 S3 presigned PUT URL（15 min 有效）

Response:
{
  "uploads": [
    {
      "fileId": "uuid",
      "presignedUrl": "https://s3.amazonaws.com/bucket/key?X-Amz-Signature=...",
      "s3Key": "ocr-uploads/{companyId}/{taskId}/{fileId}/{hash}.ext",
      "expiresAt": "2026-04-20T10:15:00Z"
    }
    | {"filename": "xxx", "error": "DUPLICATE_NAME"}
  ]
}
```

**步骤 2：前端 PUT 直传 S3**

```javascript
// 前端代码示例（不经 Java）
const xhr = new XMLHttpRequest();
xhr.upload.onprogress = (e) => setProgress(e.loaded / e.total * 100);
xhr.open('PUT', presignedUrl);
xhr.setRequestHeader('Content-Type', file.type);
xhr.send(file);
```

**步骤 3：前端通知 Java 上传完成**

```json
POST /api/v1/docparse/upload/complete
Request: { "fileId": "uuid", "etag": "...", "actualSize": 2048576 }

Java 处理:
  ├─ s3:HeadObject 验证对象存在
  ├─ 验证 actualSize 和 etag
  ├─ 读取首 2KB 做 MIME + magic bytes 校验
  ├─ 通过 → file.status=UPLOADED + 发 SQS
  └─ 失败 → s3:DeleteObject + file.status=FILE_FAILED

Response: { "status": "UPLOADED" | "FILE_FAILED", "error": null | "..." }
```

### 2.2 Presigned GET URL（文件查看）

ReviewPage 加载 PDF/Excel 时，前端向 Java 请求临时 URL：

```json
POST /api/v1/docparse/files/{fileId}/download-url
Response: { "url": "https://s3.amazonaws.com/...", "expiresAt": "2026-04-20T10:15:00Z" }
```

前端用此 URL：
- PDF → `<iframe src={url}>` 或 react-pdf `Document file={url}`
- 图片 → `<img src={url}>`
- Excel → 前端用 SheetJS 从该 URL 下载解析

**安全**：URL 只在 15 分钟内有效，Java 生成前必须验证 JWT + company 归属 + `file.deleted=false`。

### 2.3 Task 修订端点

```json
POST /api/v1/docparse/tasks/{parentTaskId}/revise
Request: { "reason": "客户更正了 Q1 数据" }

Java 处理（事务）:
  ├─ 校验 parent task.status IN (COMPLETED, SUPERSEDED)
  ├─ 创建新 task:
  │   ├─ parent_task_id = parentTaskId
  │   ├─ revision_number = parent.revision_number + 1
  │   ├─ revision_reason = request.reason
  │   └─ status = DRAFT
  ├─ copy-on-write 继承:
  │   ├─ COPY parent 的 ai_ocr_file 记录（新 task_id，保留 s3_key 不重新上传）
  │   ├─ COPY ai_ocr_extracted_table / row（由 Python 执行，Java 发 SQS 通知）
  │   └─ COPY ai_ocr_mapping_result
  └─ 返回 {newTaskId}

用户进入新 task 的 ReviewPage 直接看到继承的数据，可编辑 → Commit
Commit 成功 → 新 task.status=COMPLETED → parent task.superseded_by = 新 task.id
                                         parent task.status=SUPERSEDED
```

**Cancel 选项已移除**（Asana 2026-04-19）。用户若要放弃提交直接退出页面，task 状态保持 REVIEWING。

---

## 3. 数据表设计（业务语义）

> **DDL 权威定义**：所有表结构、索引、约束、权限 GRANT 语句的**唯一权威定义**在 [database-schema.md](./database-schema.md)。本节仅说明 Java 端表的**业务语义**、字段的设计意图，和表之间的关系。任何 DDL 变更先改 database-schema.md，再同步这里的说明文字。

### 3.1 Java 拥有的 8 张表（概览）

| 表 | 用途 | DDL 引用 |
|----|------|---------|
| `ai_ocr_task` | Task 生命周期（批次级状态 + 版本化字段） | [§2.1](./database-schema.md#21-ai_ocr_task) |
| `ai_ocr_file` | 单个文件的上传 + 处理状态（12 子阶段 + stage_detail JSONB） | [§2.2](./database-schema.md#22-ai_ocr_file) |
| `ai_ocr_notification` | 事件日志（Q16 简化：不主动推送，仅记录任务状态变化事件） | [§2.3](./database-schema.md#23-ai_ocr_notification事件日志q16-简化版) |
| `ai_ocr_conflict_note` | 冲突解决 note（Story #7，支持 thread） | [§2.4](./database-schema.md#24-ai_ocr_conflict_note) |
| `ai_ocr_memory_learn_log` | 记忆学习审计（Python INSERT，跨域例外） | [§2.5](./database-schema.md#25-ai_ocr_memory_learn_log) |
| `ai_ocr_commit_audit` | fi_* 写入审计（written/overwritten/skipped） | [§2.6](./database-schema.md#26-ai_ocr_commit_audit) |
| `ai_ocr_erasure_log` | GDPR 擦除审计 | [§2.7](./database-schema.md#27-ai_ocr_erasure_log) |
| `ai_ocr_similarity_hint` | 相似度检测结果（Python INSERT，跨域例外） | [§2.8](./database-schema.md#28-ai_ocr_similarity_hint新增相似度检测结果) |

### 3.2 关键设计决策解释

#### Task 版本化（2026-04-20 新增字段）
`parent_task_id` / `revision_number` / `revision_reason` / `superseded_by` 支持"基于历史 task 修订"场景。原任务在修订版 Commit 成功后自动置为 `SUPERSEDED`，前端展示 v1 → v2 → v3 版本链。**并发防护**：`UNIQUE (parent_task_id, revision_number) WHERE parent_task_id IS NOT NULL` 约束防止两个用户同时创建相同版本号。

#### File 处理阶段 (`processing_stage` + `stage_detail`)
12 个子状态精确描述 Python 处理进度（见 [database-schema.md §1.2 Processing Stage](./database-schema.md#processing-stage12-个子状态仅-filestatusprocessing-时有效)）。`stage_detail JSONB` 由 Python 透传：例如 `MAPPING_MEMORY_APPLY` 阶段带 `{ appliedMemoryCount: 8, totalRowCount: 47 }`，前端渲染为"已应用 8/47 条记忆"。

#### 重名文件校验的唯一约束
`UNIQUE (company_id, file_hash) WHERE deleted = false AND status != 'FILE_FAILED'` —— 只对"活跃"记录生效。`FILE_FAILED` 状态的文件允许用户重新上传同名文件（因为之前失败了）。

#### 通知表的职责降级（Q16）
`ai_ocr_notification` 不再是"通知发送状态追踪表"，而是"任务事件日志"。**不主动推送邮件/push**，用户通过 LG Dashboard "待处理任务" 列表自行发现。字段精简为 `event_type + payload + created_at`，删除了 `recipient_id` / `channel` / `status` / `retry_count`。

#### Step 5 拆分新增字段（2026-05-06）
为支撑 [requirement-analysis §4.9-4.13](./requirement-analysis.md#49-step-5a--mapping-summary-page2026-05-06-新增) 的 5a/5b/5c 流程与导航变更检测，在 `ai_ocr_task` 上新增 4 个字段（DDL 同步至 [database-schema.md §2.1](./database-schema.md#21-ai_ocr_task)）：

| 字段 | 类型 | 用途 |
|------|------|------|
| `mapping_snapshot_hash` | VARCHAR(64) | mapping + extracted_row 的 SHA-256 指纹。用户 Previous 回到 Review 修改后再 Next 时，重新计算 hash 与此值对比，决定是否重跑下游（§4.13 Scenario 1 vs 2 判定）|
| `mapping_changed_at` | TIMESTAMPTZ | 上次 mapping 变更时间。用于 Sweeper 判断"REVIEWING 是否需要刷新摘要缓存"，以及前端展示"上次修改时间" |
| `has_extractable_data` | BOOLEAN | 文件提取阶段聚合后写入；`false` 时 Step 5a/5b/5c 全部跳过，仅落 Imported Statements（§4.12 No Extractable Data 边界用例）|
| `summary_cache` | JSONB | 5a Mapping Summary 摘要缓存（totalFiles / totalMappedTypes / totalMappedAccounts / hardGateErrors[]），命中后避免重复聚合查询；mapping 变更时清空 |

#### 跨域 INSERT 例外（2 张表）
Python 有 INSERT 权限访问 `ai_ocr_memory_learn_log` 和 `ai_ocr_similarity_hint`（Java 拥有的表）。理由：这两张表由 Python 生成内容（记忆学习审计 + 相似度检测结果），走 SQS 回传增加延迟和复杂度；直接 INSERT 简单可靠。Python 无 UPDATE/DELETE 权限，不能篡改已有记录。GRANT 语句详见 [database-schema.md §4](./database-schema.md#4-数据库角色与权限)。

### 3.3 状态推进示例（两级状态协同）

下表展示一次上传 3 个文件时，task 和 file 状态如何协同推进：

| 时间点 | task.status | file_1.status | file_1.stage | file_2.status | file_2.stage | file_3.status |
|-------|------------|---------------|--------------|---------------|--------------|---------------|
| t0 用户选择 3 个文件 | DRAFT | PENDING | — | PENDING | — | PENDING |
| t1 前端 presigned PUT 完成 | UPLOADING | UPLOADED | — | UPLOADED | — | FILE_FAILED（重名） |
| t2 Java 发 SQS | PROCESSING | QUEUED | — | QUEUED | — | FILE_FAILED |
| t3 Python 开始 file_1 | PROCESSING | PROCESSING | EXTRACTING | QUEUED | — | FILE_FAILED |
| t4 file_1 映射中 | PROCESSING | PROCESSING | MAPPING_LLM | PROCESSING | EXTRACTING | FILE_FAILED |
| t5 file_1 完成 | PROCESSING | REVIEW_READY | — | PROCESSING | MAPPING_RULE | FILE_FAILED |
| t6 file_2 完成 | **SIMILARITY_CHECKING** | REVIEW_READY | — | REVIEW_READY | — | FILE_FAILED |
| t7 相似度检测完成 | **REVIEWING** (瞬间推进) | REVIEW_READY | — | REVIEW_READY | — | FILE_FAILED |
| t8 用户 verify + commit | COMMITTING → COMMITTED → MEMORY_LEARN_PENDING | FILE_COMMITTED | — | FILE_COMMITTED | — | FILE_FAILED |
| t9 记忆学习完成 | **COMPLETED** | FILE_COMMITTED | — | FILE_COMMITTED | — | FILE_FAILED |

**关键点**:
- **t6**: 即使 file_3 失败，只要**非失败文件都 REVIEW_READY**，task 进入 SIMILARITY_CHECKING（相似度检测阶段）
- **t7**: Python 完成相似度检测后瞬间推进到 REVIEWING
- **t9**: COMPLETED 不要求所有 file 成功，只要求所有**非失败文件**都 FILE_COMMITTED
- **后置动作**（记忆学习、事件日志）在 t9 COMPLETED 触发**一次**，不会因 file_3 FILE_FAILED 而跳过

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

Python 端向 `ocr-result-queue` 发送**三种**消息：`OcrProgress`、`OcrResult`、`OcrMemoryLearnProgress`。Java 端 `OcrResultSqsProcessor`（implements `MessageProcessor`）按 `messageType` 字段分发到不同 handler：

```java
@Override
public void process(SqsMessage message) {
    switch (message.getMessageType()) {
        case "OcrProgress":              handleProgress(message); break;
        case "OcrResult":                handleResult(message); break;
        case "OcrMemoryLearnProgress":   handleMemoryLearnProgress(message); break;
        default: log.warn("Unknown messageType: {}", message.getMessageType());
    }
}
```

#### 4.2.1 OcrProgress 消息（文件级进度上报，轻量，频繁）

每当 Python 切换处理阶段时发送，让前端展示精确进度。

**消息 Schema (Python -> Java)**:

```json
{
  "messageType": "OcrProgress",
  "queueName": "ocr-result-queue",
  "uuid": "msg-uuid",
  "sendTime": "2026-04-16T10:00:05Z",
  "taskId": "task-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "processingStage": "MAPPING_MEMORY_APPLY",
  "progressPct": 55,
  "stageDetail": {
    "appliedMemoryCount": 8,
    "totalRowCount": 47
  }
}
```

**Java 处理**:
```java
void handleProgress(OcrProgressMessage msg) {
    // 1. 幂等去重：相同 (fileId, processingStage) 的重复消息合并
    DocParseFile file = fileRepo.findByIdForUpdate(msg.getFileId());
    if (file.getProcessingStage() != null
        && ordinalOf(file.getProcessingStage()) > ordinalOf(msg.getProcessingStage())) {
        return;  // 收到过期消息（已推进到更后阶段），丢弃
    }

    // 2. 更新 file 字段 —— 原子更新
    fileRepo.updateProgress(
        msg.getFileId(),
        msg.getProcessingStage(),
        msg.getProgressPct(),
        msg.getStageDetail()  // ⚠️ stageDetail 必须透传到 DB（JSONB 列），前端会用
    );

    // 3. 首次收到 → 推进 file.status 和 task.status
    if (file.getStatus() == DocParseFileStatus.QUEUED) {
        fileRepo.updateStatus(msg.getFileId(), DocParseFileStatus.PROCESSING);
        taskRepo.updateStatusIfCurrently(msg.getTaskId(),
            DocParseStatus.UPLOAD_COMPLETE, DocParseStatus.PROCESSING);
    }
    // 不触发 task 级状态最终转换（仅 OcrResult 才触发 → REVIEWING）
}
```

**`ai_ocr_file.stage_detail JSONB` 列**：
```sql
ALTER TABLE ai_ocr_file ADD COLUMN stage_detail JSONB;
```
前端 `GET /tasks/{id}/status` 读这张表时把 `stage_detail` 字段透传给前端，前端按 `frontend-design.md §5.2` 规则渲染细节文字（"第 3/8 页"、"已应用 8/47 条记忆"等）。

#### 4.2.2 OcrResult 消息（文件级最终结果，每个文件一次）

Python 完成一个文件的全部处理后发送。

**消息 Schema (Python -> Java)** —— 与 python-design.md §1.3.2 保持完全一致：

```json
{
  "messageType": "OcrResult",
  "queueName": "ocr-result-queue",
  "batchId": "uuid",
  "sendTime": "2026-04-16T10:00:15Z",
  "uuid": "msg-uuid",
  "taskId": "task-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "status": "completed",
  "extractedTableCount": 2,
  "totalRows": 47,
  "processingTimeMs": 12340,
  "unresolvedPeriodCount": 0,
  "currencyWarning": false,
  "detectedCurrencies": ["USD"],
  "memoryHitCount": 8,
  "llmMapCount": 15,
  "error": null
}
```

**Java 处理逻辑（事务 + FOR UPDATE 锁避免竞态）**:

```java
@Transactional
void handleResult(OcrResultMessage msg) {
    // 1. 先锁 task 行（并发防护：两个 worker 同时处理最后两个文件的结果）
    DocParseTask task = taskRepo.findByIdForUpdate(msg.getTaskId());

    // 2. 更新单个 file 状态（使用 CAS 防止旧消息覆盖新状态）
    int updated = fileRepo.compareAndSetStatus(
        msg.getFileId(),
        expectedStatus=PROCESSING,
        newStatus= msg.getStatus().equals("completed") ? REVIEW_READY : FILE_FAILED,
        additionalFields=msg
    );
    if (updated == 0) {
        log.warn("File {} status already advanced, ignore duplicate result", msg.getFileId());
        return;  // 幂等
    }

    // 3. 原子更新 task 统计字段
    if (msg.getStatus().equals("failed")) {
        task.setFailedFiles(task.getFailedFiles() + 1);
    }

    // 4. 检查批次是否完成（锁状态下计数）
    long pendingFiles = fileRepo.countByTaskIdAndStatusNotIn(
        msg.getTaskId(),
        Set.of(DocParseFileStatus.REVIEW_READY, DocParseFileStatus.FILE_FAILED));

    if (pendingFiles == 0 && task.getFailedFiles() < task.getTotalFiles()) {
        // 所有非失败文件都已 REVIEW_READY，且至少有一个成功
        task.setStatus(DocParseStatus.SIMILARITY_CHECKING);  // 进入通知阶段
        eventPublisher.publishEvent(new TaskReadyForReviewEvent(msg.getTaskId()));
    } else if (pendingFiles == 0) {
        // 全部失败
        task.setStatus(DocParseStatus.FAILED);
    }

    taskRepo.save(task);
}
```

#### 4.2.3 OcrMemoryLearnProgress 消息（任务级记忆学习进度）

Python 记忆学习 consumer 在 3 个时机发送此消息（IN_PROGRESS / COMPLETE / FAILED），与 `ai_ocr_task.status` 中的 `MEMORY_LEARN_*` 子态对应。

**消息 Schema (Python -> Java)**:

```json
{
  "messageType": "OcrMemoryLearnProgress",
  "queueName": "ocr-result-queue",
  "uuid": "msg-uuid",
  "sendTime": "2026-04-16T10:10:00Z",
  "taskId": "task-uuid",
  "companyId": "123",
  "learnStage": "MEMORY_LEARN_IN_PROGRESS",
  "stageDetail": {
    "processedFileCount": 2,
    "totalFileCount": 3,
    "newMemoryCount": 5,
    "updatedMemoryCount": 3
  }
}
```

**Java 处理逻辑**:

```java
void handleMemoryLearnProgress(OcrMemoryLearnProgressMessage msg) {
    DocParseTask task = taskRepo.findByIdForUpdate(msg.getTaskId());
    switch (msg.getLearnStage()) {
        case "MEMORY_LEARN_IN_PROGRESS":
            // 仅从 MEMORY_LEARN_PENDING 推进到 IN_PROGRESS
            taskRepo.updateStatusIfCurrently(
                msg.getTaskId(),
                DocParseStatus.MEMORY_LEARN_PENDING,
                DocParseStatus.MEMORY_LEARN_IN_PROGRESS);
            break;
        case "MEMORY_LEARN_COMPLETE":
            // 推进到 COMPLETED 终态（含记忆学习）
            taskRepo.updateStatusIfCurrently(
                msg.getTaskId(),
                DocParseStatus.MEMORY_LEARN_IN_PROGRESS,
                DocParseStatus.COMPLETED);
            // 创建 MEMORY_LEARN_COMPLETE 通知
            notificationService.create(task, NotificationType.MEMORY_LEARN_COMPLETE);
            break;
        case "MEMORY_LEARN_FAILED":
            // 检查 attempt_number，若 < 3 则回到 PENDING 等重试；否则终态 FAILED
            long attempts = memoryLearnLogRepo.countByTaskId(msg.getTaskId());
            if (attempts < 3) {
                taskRepo.setStatus(msg.getTaskId(), DocParseStatus.MEMORY_LEARN_PENDING);
            } else {
                taskRepo.setStatus(msg.getTaskId(), DocParseStatus.MEMORY_LEARN_FAILED);
                // ⚠️ 财务数据已写入 fi_*，不回滚
            }
            break;
    }
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
- 对比 `originalAiCategory` vs `confirmedCategory`，将修正存入 `ai_ocr_mapping_memory`
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

### 4.6 DocParseTaskSweeper 僵尸态自愈（@Scheduled）

异步消息驱动的状态机存在"消息丢失"或"Python/Java 崩溃在中间态"导致任务永久停留的风险。通过定时扫描自愈：

```java
@Component
@Slf4j
public class DocParseTaskSweeper {

    @Scheduled(fixedDelay = 120_000)  // 每 2 分钟
    @Transactional
    public void sweep() {
        Instant now = Instant.now();

        // 1. DRAFT > 24h → EXPIRED（清理用户未完成的任务 + S3 对象）
        sweepDraftExpired(now.minus(Duration.ofHours(24)));

        // 2. PROCESSING > 20min 且 Python 端已写数据 → 同步推进到 REVIEW_READY
        sweepZombieProcessing(now.minus(Duration.ofMinutes(20)));

        // 3. VERIFYING > 10min → FAILED（verify 代码死循环或 DB 连接池耗尽）
        sweepStuckVerifying(now.minus(Duration.ofMinutes(10)));

        // 4. MEMORY_LEARN_IN_PROGRESS > 10min（Python 崩溃）→ MEMORY_LEARN_FAILED
        sweepStuckMemoryLearn(now.minus(Duration.ofMinutes(10)));

        // 注：不扫描 SIMILARITY_CHECKING（Q16 简化为瞬态事件日志，不会卡住）
        // 注：不扫描 COMMITTING（Q7 方案 B 下事务 rollback 时 status 自动回 REVIEWING）
        // 注：不扫描 SIMILARITY_CHECKED（用户登录时从待审核列表自然发现，无 TTL）
    }

    private void sweepDraftExpired(Instant threshold) {
        List<DocParseTask> drafts = taskRepo.findByStatusAndCreatedAtBefore(
            DocParseStatus.DRAFT, threshold);
        for (DocParseTask t : drafts) {
            // 删除 S3 临时文件
            t.getFiles().forEach(f -> s3Client.deleteObject(bucket, f.getS3Key()));
            t.setStatus(DocParseStatus.EXPIRED);
            taskRepo.save(t);
            log.info("Expired DRAFT task {} (created_at={})", t.getId(), t.getCreatedAt());
        }
    }

    private void sweepZombieProcessing(Instant threshold) {
        // 找 PROCESSING 超过 20 分钟的 file
        List<DocParseFile> zombies = fileRepo.findByStatusAndUpdatedAtBefore(
            DocParseFileStatus.PROCESSING, threshold);
        for (DocParseFile f : zombies) {
            // 检查 Python 端是否已完成（通过 SELECT 跨 schema 只读）
            boolean hasResult = extractedTableRepo.existsByFileId(f.getId());
            if (hasResult) {
                // Python 处理完了但 OcrResult 丢失 → 同步推进
                f.setStatus(DocParseFileStatus.REVIEW_READY);
                f.setProcessingStage(null);
                f.setProgressPct(100);
                fileRepo.save(f);
                log.warn("Recovered zombie file {}: Python result missing, forced REVIEW_READY",
                    f.getId());
                // 触发 task 状态检查
                statusService.checkAndAdvanceTask(f.getTaskId());
            } else {
                // Python 真的卡住了 → 失败
                f.setStatus(DocParseFileStatus.FILE_FAILED);
                f.setErrorMessage("Processing timeout after 20 minutes");
                fileRepo.save(f);
            }
        }
    }

    // ... 其他 sweep 方法类似
}
```

**关键设计**:
- 使用 `@Scheduled(fixedDelay)` 而非 `fixedRate` — 确保前一次完成后才启动下一次
- 每个 sweep 方法使用独立事务，失败不影响其他方法
- 日志级别用 WARN / INFO，便于监控告警
- 扫描结果要发 metric 到监控系统（如 Prometheus），僵尸任务数 > 0 时触发告警

### 4.7 Java/Python 数据库物理部署模型

**关键决策（2026-04-20）**: Java 和 Python 共用**同一个** PostgreSQL RDS 实例，**同一个 schema**（简化部署，避免跨库 JOIN）。通过数据库角色权限实现读写隔离：

```sql
-- 创建角色
CREATE ROLE java_app LOGIN PASSWORD '***';
CREATE ROLE python_worker LOGIN PASSWORD '***';

-- Java 表（ai_ocr_*）— Java 拥有，Python 只读（少数例外）
GRANT SELECT, INSERT, UPDATE, DELETE ON
    ai_ocr_task, ai_ocr_file, ai_ocr_notification,
    ai_ocr_conflict_note, ai_ocr_commit_audit
TO java_app;

GRANT SELECT ON
    ai_ocr_task, ai_ocr_file, ai_ocr_notification,
    ai_ocr_conflict_note, ai_ocr_commit_audit
TO python_worker;

-- ⚠️ 例外：Python 对 ai_ocr_memory_learn_log 有 INSERT 权限
GRANT INSERT ON ai_ocr_memory_learn_log TO python_worker;
-- 无 UPDATE / DELETE 权限，只能追加审计记录，不能篡改历史

-- Python 表（ai_ocr_* + ai_ocr_mapping_memory*）— Python 拥有，Java 只读
GRANT SELECT, INSERT, UPDATE, DELETE ON
    ai_ocr_extracted_table, ai_ocr_extracted_row, ai_ocr_mapping_result,
    ai_ocr_conflict_record, ai_ocr_mapping_memory, ai_ocr_mapping_memory_audit
TO python_worker;

GRANT SELECT ON
    ai_ocr_extracted_table, ai_ocr_extracted_row, ai_ocr_mapping_result,
    ai_ocr_conflict_record
TO java_app;
-- Java 无权查询 ai_ocr_mapping_memory（涉及跨公司商业机密）

-- fi_* 财务表 — 仅 Java 可写
GRANT SELECT, INSERT, UPDATE ON fi_* TO java_app;
REVOKE ALL ON fi_* FROM python_worker;
```

**为什么不分独立实例**:
- 分实例需要 postgres_fdw 或跨库查询代理（复杂）
- 共享实例下 FK 约束可生效（`ai_ocr_extracted_table.file_id → ai_ocr_file.id`）
- 权限隔离足够防止误写
- 生产成本更低（单 RDS 实例可扩展 vCPU，两个小实例比一个大实例贵）

**未来扩展**: 如果 ai_ocr_mapping_memory 增长到亿级记录，可将 `ai_ocr_mapping_memory*` 表拆到独立 pgvector 集群（迁移时 Python 改用新连接串，Java 无感知）。

## 5. 业务流程

### 5.1 上传流程

```
用户上传文件 (multipart)
    → ① 校验文件 (MIME + magic bytes + 文件大小)
    → ①.5 计算文件 SHA-256 hash → 查 ai_ocr_file 是否已存在同 company_id + file_hash
          → 若存在则抛 DUPLICATE_NAME 错误
    → ② 存入 S3 (ocr-uploads/{companyId}/{sessionId}/{fileId}/filename)
    → ③ 创建 ai_ocr_task 记录 (status=PENDING)
    → ④ 创建 ai_ocr_file 记录（写入 file_hash）
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
    → 查 ai_ocr_task 表
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
    - 手动输入 → 写入 ai_ocr_conflict_note
    - 不填写 → 系统自动生成默认 note（auto_generated=true）
    - 支持 note thread（parent_note_id）

用户解决所有冲突后点击 Commit
    → POST /api/v1/docparse/tasks/{id}/resolve （保存解决方案）
    → POST /api/v1/docparse/tasks/{id}/commit
    → 后端执行（两阶段：事务 + AFTER_COMMIT 事件）:
        事务内（@Transactional）:
          ① FOR UPDATE 锁 ai_ocr_task 行（防并发 Commit）
          ② 检查 task.status IN (REVIEWING, CONFLICT_RESOLUTION)；否则抛异常
          ③ 推进 task.status = COMMITTING
          ④ 读取 ai_ocr_extracted_row + ai_ocr_mapping_result
          ⑤ 按 resolution 策略写入 fi_* 财务表
          ⑥ 记录 ai_ocr_commit_audit（written/overwritten/skipped）
          ⑦ 推进 task.status = COMMITTED；file.status = FILE_COMMITTED
          ⑧ 如果是 revision task：parent.status = SUPERSEDED, parent.superseded_by = self.id
          ⑨ publishEvent(CommitSuccessEvent) —— Spring 事件，不立即发 SQS

        AFTER_COMMIT（@TransactionalEventListener(phase = AFTER_COMMIT)）:
          ⑩ 把源文件记录到 Company Documents（调用 CompanyDocService）
          ⑪ 触发下游 Normalization 流程
          ⑫ 如果存在新的 reporting period → 触发新闭月邮件通知
          ⑬ 构建 mappingComparisons 发送 ocr-memory-learn-queue
          ⑭ 推进 task.status = MEMORY_LEARN_PENDING
          ⑮ 创建 ai_ocr_notification 条目 → 调用通知服务发送

    → 事务内任何一步失败 → ROLLBACK，task.status 回到 REVIEWING（依赖事件监听补偿，见下方）
    → AFTER_COMMIT 阶段失败不回滚 fi_*（财务数据已提交），仅记录到 dlq，后续可重试
```

**关键约束（2026-04-19 强化 + 2026-04-20 并发修正）**:

- **并发互斥**: Commit 入口用 `@Lock(LockModeType.PESSIMISTIC_WRITE)` 或 `SELECT ... FOR UPDATE` 锁 `ai_ocr_task`，再用 CAS 更新 `status = COMMITTING WHERE status IN (REVIEWING, CONFLICT_RESOLUTION)`；受影响 0 行则抛异常（已被另一用户 commit）
- **整体事务**: `@Transactional(propagation=REQUIRED, rollbackFor=Exception.class)` 包裹 fi_* 写入
- **⚠️ SQS 必须在 AFTER_COMMIT 后发**: 使用 `@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)` 监听 `CommitSuccessEvent`；否则事务回滚后 Python 已收到记忆学习消息，会写入脏记忆
- **部分写入禁止**: 任何一个 metric 写入失败，整个 commit 回滚，`task.status` 自动回到 `REVIEWING`（通过事务回滚 + 异常处理器）
- **Cancel 已移除**: 用户放弃提交 → 直接退出页面，task 状态保持 REVIEWING
- **源文件始终记录**: 无论是否提取到账户，上传文件都出现在 Company Documents
- **新闭月邮件**: Java 职责（不是 Python），写入成功后通过 EventBridge/邮件服务触发
- **记忆学习触发**: 仅在 commit 成功后，只学习 `wasOverridden: true` 的条目

**Commit 失败的恢复路径（Q7 方案 B：可恢复重试）**

Commit 失败**不置 task.status=FAILED**。事务 rollback 后 task.status 自动回到 `REVIEWING`，用户可直接在 ConfirmPage 再点 "Commit" 重试（数据库已回滚，数据干净，幂等执行）。

```java
@Transactional
public void commit(UUID taskId) {
    try {
        // 1. FOR UPDATE 锁 task 行
        DocParseTask task = repo.findByIdForUpdate(taskId);
        if (!Set.of(REVIEWING, CONFLICT_RESOLUTION).contains(task.getStatus())) {
            throw new BusinessException("INVALID_STATUS_FOR_COMMIT");
        }
        task.setStatus(COMMITTING);
        repo.save(task);

        // 2. 写 fi_* 财务表（核心事务）
        financialDataService.writeBatch(taskId);

        // 3. 推进 task.status = COMMITTED；file.status = FILE_COMMITTED
        task.setStatus(COMMITTED);
        repo.save(task);

        // 4. 发布事件（AFTER_COMMIT 才消费，见 @TransactionalEventListener）
        eventPublisher.publishEvent(new CommitSuccessEvent(taskId));

    } catch (BusinessException e) {
        // 业务异常（如 INVALID_STATUS）直接抛出，task.status 保持
        throw e;
    } catch (Exception e) {
        // 技术异常（DB 死锁/字段约束/OOM/网络）：
        //   @Transactional 自动回滚 fi_* + task.status 字段更新
        //   task.status 自动恢复为进入方法前的值（REVIEWING 或 CONFLICT_RESOLUTION）
        // ⚠️ 绝对不把 task.status 置为 FAILED —— 这样用户可以直接重试
        log.error("Commit failed for task {}, auto-reverted to REVIEWING. User can retry.", taskId, e);
        throw new BusinessException("COMMIT_FAILED_RETRYABLE",
            "Commit failed due to technical error, please retry", e);
    }
}
```

**用户体验**:

```
用户在 ConfirmPage 点击 Commit
  → Java 返回 500 + errorCode=COMMIT_FAILED_RETRYABLE
  → 前端弹 Modal: "提交失败：{errorMessage}。数据未写入，请稍后重试。[重试] [取消]"
  → 点"重试" → 再次 POST /commit（task.status 还是 REVIEWING，可接受）
  → 点"取消" → 返回 ConfirmPage，用户可以继续调整后再提交
  → 即使关闭浏览器，DRAFT 态和 task 仍保留在 REVIEWING，24 小时内可恢复
```

**何时真正 task.status = FAILED**（只有以下 3 种）:
1. 所有文件 FILE_FAILED（Phase 2 Python 处理全失败）
2. VERIFYING 阶段异常（Phase 4 验证代码 bug）— 由 Sweeper 10min 超时推进
3. DRAFT > 24 小时未操作 → EXPIRED（不是 FAILED，是单独的过期态）

Commit 失败不进 FAILED，是 Q7 方案 B 的核心契约。

### 5.4.1 通知事件记录（Q16 简化版，不发送）

**关键决策**: 系统**不主动推送通知**。以下所有场景都只写一条 `ai_ocr_notification` 事件日志，用户下次登录 LG 主页时通过"待处理任务"自行发现。

事件触发点（`NotificationEventService.log()` 在各业务事务 AFTER_COMMIT 后调用）：

| event_type | 触发时机 | payload 字段示例 |
|------------|---------|------------------|
| `PARSE_COMPLETE` | task.status = REVIEWING 时 | `{totalFiles:3, completedFiles:3, failedFiles:0}` |
| `COMMIT_COMPLETE` | task.status = COMMITTED 时 | `{writtenPeriods:["2024-01","2024-02"], writtenRows:47}` |
| `COMMIT_FAILED` | commit 事务抛异常时 | `{error:"..."}`（供运维排查） |
| `MEMORY_LEARN_COMPLETE` | task.status = COMPLETED 时 | `{newMemoryCount:5, updatedMemoryCount:3}` |
| `MEMORY_LEARN_FAILED` | 3 次重试后失败 | `{lastError:"..."}` |
| `NEW_CLOSED_MONTH` | commit 引入新期间时 | `{newPeriods:["2024-03"]}` |

### 5.4.2 已移除的通知重试机制

旧设计中的 `NotificationRetryScheduler` / `retry_count` / 立即/1min/5min 重试策略均已移除（因为根本不发送，也不会失败）。

**Task 状态 `SIMILARITY_CHECK_FAILED` 仍保留**在 enum 中作为"邮件服务将来接入时的预留值"，目前不会进入此状态（`SIMILARITY_CHECKING` 瞬间完成，只写一条日志就推进到 `SIMILARITY_CHECKED` 再立即到 `REVIEWING`）。

### 5.4.3 S3 Bucket CORS 配置（生产必需）

Presigned URL 直传要求 S3 Bucket 配置 CORS 允许前端 origin。**严禁使用 `*` 或 localhost 作为 AllowedOrigins**。

```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://portal.lookingglass.com"],
      "AllowedMethods": ["PUT", "GET"],
      "AllowedHeaders": ["Content-Type", "x-amz-*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

**开发环境**：使用独立的 dev Bucket（`AllowedOrigins: ["http://localhost:8000"]`），**严禁**在生产 Bucket 上允许 localhost。Terraform 配置通过环境变量区分。

### 5.4.4 S3 Presigned URL 安全增强

1. **Presigned PUT 必须加 `content-length-range` 条件**（防止绕过 20MB 限制）:
   ```java
   PresignedPutObjectRequest req = S3Presigner.presignPutObject(r -> r
       .signatureDuration(Duration.ofMinutes(15))
       .putObjectRequest(PutObjectRequest.builder()
           .bucket(bucket).key(s3Key)
           .contentLength(fileSize)  // ⚠️ 强制
           .build()));
   ```

2. **Presigned GET 生存期缩短到 5 分钟**（折中：大 PDF 加载需时间，但过期会自动续签）:
   ```java
   PresignedGetObjectRequest req = S3Presigner.presignGetObject(r -> r
       .signatureDuration(Duration.ofMinutes(5))   // ← 不是 15 分钟
       .getObjectRequest(GetObjectRequest.builder().bucket(bucket).key(s3Key).build()));
   ```

3. **`complete` 端点严禁信任前端传入的 s3Key**：
   ```java
   // ❌ 错误：信任前端传入的 s3Key
   s3Client.headObject(b -> b.bucket(bucket).key(request.getS3Key()));

   // ✅ 正确：从 DB 查 s3Key
   DocParseFile file = fileRepo.findByIdAndCompanyId(fileId, jwtCompanyId);
   s3Client.headObject(b -> b.bucket(bucket).key(file.getS3Key()));
   ```

4. **`file_hash` 格式强校验**（防注入）:
   ```java
   @Pattern(regexp = "^[a-f0-9]{64}$", message = "Invalid SHA-256 hash")
   private String hash;
   ```

5. **CloudTrail S3 数据事件启用**：生产 Bucket 必须启用 CloudTrail Data Events（PutObject / GetObject / DeleteObject），日志存到独立的审计 Bucket（启用 MFA Delete）。

### 5.4.5 URL 响应字段统一（`expiresAt` ISO 时间戳）

全文统一使用 `expiresAt`（ISO 8601 时间戳）而非 `expiresIn`（秒数）。原因：前端直接用 `new Date(expiresAt) > Date.now()` 判断是否过期，无需额外保存"签发时刻"。

```json
{
  "url": "https://s3.amazonaws.com/...",
  "expiresAt": "2026-04-20T10:15:00Z"
}
```

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

### 5.6 Step 5a — Mapping Summary 与 Verify 触发（2026-05-06 新增）

> 需求来源：[requirement-analysis §4.9](./requirement-analysis.md#49-step-5a--mapping-summary-page2026-05-06-新增)

**核心契约**: 用户主动点击 "Start Verification" 才触发冲突检测；后端必须先做 hard gate 校验，存在 unmapped/unreviewed/缺失元数据的行项时**直接拒绝**进入 verify。

#### 5.6.1 端点设计

```java
@RestController
@RequestMapping("/api/v1/docparse/tasks/{taskId}")
@Validated
public class MappingSummaryController {

    /** 5a 页面进入时调用：返回三组统计 + hard gate 错误清单 */
    @GetMapping("/mapping-summary")
    public DocParseMappingSummaryRespVo getSummary(@PathVariable UUID taskId) {
        return mappingSummaryService.computeSummary(taskId);   // 命中 summary_cache 直接返回
    }

    /** 5a 点击 "Start Verification" 触发，状态机推进 REVIEWING → VERIFYING */
    @PostMapping("/verify/start")
    public DocParseVerifyStartRespVo startVerification(@PathVariable UUID taskId) {
        return verificationService.startVerification(taskId);  // hard gate 校验 + 异步入队
    }

    /** 5a 进度轮询；返回 stage（PENDING/RUNNING/COMPLETED/ABORTED）+ percent + 已检测冲突数 */
    @GetMapping("/verify/progress")
    public DocParseVerifyProgressRespVo getProgress(@PathVariable UUID taskId) {
        return verificationService.getProgress(taskId);
    }
}
```

#### 5.6.2 Service 关键方法签名

```java
public interface MappingSummaryService {
    /**
     * 聚合: 文件总数 / 映射类型数（Actuals + Proforma）/ 映射账户数 + hard gate 检查
     * 命中 ai_ocr_task.summary_cache 直接返回；mapping_changed_at 变化或 cache 为 null 时重算并写回
     */
    DocParseMappingSummaryRespVo computeSummary(UUID taskId);
}

public interface VerificationService {
    /**
     * 1. FOR UPDATE 锁 task；检查 status=REVIEWING
     * 2. 调 MappingSummaryService.computeSummary() 取最新 hardGateErrors
     * 3. 若 hardGateErrors 非空 → 抛 BusinessException("HARD_GATE_FAILED", errors)
     * 4. 若 has_extractable_data=false → 跳到 §5.9 No-Data 分支
     * 5. 推进 status=VERIFYING；publish event 启动异步 ConflictDetectionJob
     */
    DocParseVerifyStartRespVo startVerification(UUID taskId);

    /** 用户中途 Previous → 异步任务收到 cancel 信号，回到 REVIEWING（§4.9 回退处理） */
    void abortVerification(UUID taskId);

    DocParseVerifyProgressRespVo getProgress(UUID taskId);
}
```

#### 5.6.3 Hard Gate 检查规则

```java
// MappingSummaryService 内部实现
List<HardGateError> validate(UUID taskId) {
    List<HardGateError> errors = new ArrayList<>();
    // 1. unmapped 行项（lg_category 为空）
    long unmapped = mappingResultRepo.countByTaskIdAndLgCategoryIsNull(taskId);
    if (unmapped > 0) errors.add(new HardGateError("UNMAPPED_ROWS", unmapped));
    // 2. unreviewed 行项（user_reviewed=false 的非 confidence-high 项）
    long unreviewed = extractedRowRepo.countUnreviewedRequired(taskId);
    if (unreviewed > 0) errors.add(new HardGateError("UNREVIEWED_ROWS", unreviewed));
    // 3. 缺失元数据：account_label / value / reporting_period 任一为空
    long missing = extractedRowRepo.countMissingMetadata(taskId);
    if (missing > 0) errors.add(new HardGateError("MISSING_METADATA", missing));
    return errors;
}
```

---

### 5.7 Step 5b — 单冲突逐个解决 + Note 必填（2026-05-06 重构）

> 需求来源：[requirement-analysis §4.10](./requirement-analysis.md#410-step-5b--conflict-resolution-of-manual-uploads2026-05-06-新增)

**重大变更**: 由原 §5.4 的"批量 resolve"改为**逐个冲突解决**，前端弹窗驱动。Note 强制非空（与原 §5.4 "可选填写 Note" 不同）。

#### 5.7.1 端点设计

```java
@RestController
@RequestMapping("/api/v1/docparse/tasks/{taskId}/conflicts")
public class ConflictResolutionController {

    /** 仅 Actuals 冲突；Proforma 整体豁免不入此列表 */
    @GetMapping
    public DocParseConflictListRespVo listConflicts(@PathVariable UUID taskId) {
        return conflictService.listActualsConflicts(taskId);
    }

    /** 单冲突解决：Note 必填硬校验；返回下一冲突定位（Save & Next 导航） */
    @PostMapping("/{conflictId}/resolve")
    public DocParseConflictResolveRespVo resolveOne(
            @PathVariable UUID taskId,
            @PathVariable UUID conflictId,
            @RequestBody @Valid DocParseSingleConflictResolveReqVo req) {
        return conflictService.resolve(taskId, conflictId, req);
    }
}

@Data
public class DocParseSingleConflictResolveReqVo {
    @NotNull
    private DocParseConflictAction action;     // OVERWRITE | SKIP（Cancel 已移除）
    @NotBlank @Size(max = 2000)
    private String note;                       // ⚠️ 必填硬校验，前端按钮 disabled until note
}

@Data
public class DocParseConflictResolveRespVo {
    private UUID resolvedConflictId;
    private boolean isLast;                    // 末尾冲突 → 前端按钮文案变为 "Save"，否则 "Save & Next"
    private UUID nextConflictId;               // 同 metric 下一月 → 跨 metric 第一冲突
    private String nextMetric;
    private int remainingCount;
}
```

#### 5.7.2 Save & Next 导航逻辑（§4.10）

```java
// ConflictService.resolve() 内部
DocParseConflictResolveRespVo computeNext(UUID taskId, UUID currentConflictId) {
    Conflict cur = conflictRepo.findById(currentConflictId);
    // 1. 同 metric 下一未解决月份
    Optional<Conflict> sameMetric = conflictRepo
        .findFirstByTaskIdAndMetricAndResolvedFalseAndIdNotOrderByReportingPeriod(
            taskId, cur.getLgMetric(), currentConflictId);
    if (sameMetric.isPresent()) return resp(sameMetric.get(), false);
    // 2. 跨 metric 的第一个未解决冲突
    Optional<Conflict> nextMetric = conflictRepo
        .findFirstByTaskIdAndResolvedFalseOrderByLgMetricAscReportingPeriodAsc(taskId);
    if (nextMetric.isPresent()) return resp(nextMetric.get(), false);
    // 3. 全部解决 → isLast=true，按钮变 "Save"，前端引导用户进入 5c
    return new DocParseConflictResolveRespVo(currentConflictId, true, null, null, 0);
}
```

#### 5.7.3 Service 方法签名

```java
public interface ConflictService {
    /** 仅返回 Actuals 冲突（按 lg_metric, reporting_period 排序） */
    DocParseConflictListRespVo listActualsConflicts(UUID taskId);

    /**
     * 1. 校验 task.status IN (CONFLICT_RESOLUTION, VERIFYING)
     * 2. 校验 note 非空（@Valid 已做但二次防御）
     * 3. 写 ai_ocr_conflict_record.resolution + ai_ocr_conflict_note
     * 4. 计算下一冲突定位
     * 5. 若全部解决 → 推进 task.status=CONFLICT_RESOLUTION（保持，等用户点 Commit）
     */
    DocParseConflictResolveRespVo resolve(UUID taskId, UUID conflictId,
                                          DocParseSingleConflictResolveReqVo req);
}
```

---

### 5.8 Step 5c — Commit、Proforma 追加版本、Imported Statements（2026-05-06 新增）

> 需求来源：[requirement-analysis §4.11](./requirement-analysis.md#411-step-5c--commit-uploaded-data-to-lg--display-results2026-05-06-新增)

**核心变更**（相对原 §5.4）：
- Proforma 走**追加新 committed forecast 版本**路径，**不参与冲突解决**
- 所有上传文件（含无数据文件）都同步到 Documents 的 `Imported Statements` 文件夹
- Commit 引入新 closed month 时触发邮件通知
- 成功后跳转 Benchmark Info Page，附带提示参数

#### 5.8.1 Commit Controller

```java
@RestController
@RequestMapping("/api/v1/docparse/tasks/{taskId}")
public class CommitController {

    @PostMapping("/commit")
    @Transactional
    public DocParseCommitRespVo commit(@PathVariable UUID taskId) {
        return commitService.commit(taskId);
    }

    /** 5c 跳转 Benchmark 前端获取写入摘要 + 跳转参数 */
    @GetMapping("/commit/result")
    public DocParseCommitResultRespVo getResult(@PathVariable UUID taskId) {
        return commitService.getResult(taskId);
    }
}

@Data
public class DocParseCommitResultRespVo {
    private int writtenAccountCount;
    private List<String> writtenPeriods;          // ["2024-01", "2024-02"]
    private List<String> documentTypes;           // ["P&L", "Balance Sheet"]
    private UUID importedStatementsFolderId;      // Documents 服务返回的文件夹 ID
    private boolean newClosedMonthIntroduced;
    private String benchmarkRedirectUrl;          // 5c 跳转目标
    private String banner;                        // "View your updated benchmarks"
}
```

#### 5.8.2 Service 方法（在原 §5.4 基础上增加）

```java
public interface CommitService {
    /**
     * 整批事务（@Transactional + FOR UPDATE 锁 task）：
     * 1. 校验 task.status=CONFLICT_RESOLUTION 且所有冲突已解决
     * 2. 分流写入：
     *    - Actuals 行项 → fi_* 表（按 §5.7 resolution OVERWRITE/SKIP 规则）
     *    - Proforma 行项 → 调 ProformaForecastService.appendVersion() 追加新版本
     * 3. ai_ocr_commit_audit 全量记录（written/overwritten/skipped + Proforma append 也算 written）
     * 4. AFTER_COMMIT 阶段：
     *    a. 调 ImportedStatementsService.syncAllFiles(taskId)（含 has_extractable_data=false 的文件）
     *    b. 检测新 closed month → 发邮件
     *    c. 触发下游 normalization
     *    d. 发记忆学习 SQS（仅 wasOverridden=true 行项）
     */
    DocParseCommitRespVo commit(UUID taskId);

    DocParseCommitResultRespVo getResult(UUID taskId);
}

public interface ProformaForecastService {
    /**
     * Proforma 追加版本逻辑：
     * 1. 找当前 active committed forecast（取最新版本，24 个月窗口）
     * 2. 上传 proforma 月份 ∩ 现有月份 → 替换值
     * 3. 上传 proforma 月份 ∉ 现有月份 → 追加月份
     * 4. 创建新 forecast_version 记录（user=上传者，supersedes=旧版本 ID）
     * 5. 旧版本保留为历史不删除（审计要求）
     */
    UUID appendVersion(UUID taskId, UUID companyId, List<ProformaRow> rows);
}

public interface ImportedStatementsService {
    /**
     * 同步上传文件元数据到 Documents 服务的 "Imported Statements" 文件夹：
     * - 该文件夹按 company_id 全局唯一，首次提交时由 CompanyDocService 自动创建
     * - 文件元数据: { fileName, s3Key, uploadedAt, uploadedBy, taskId, hasExtractableData }
     * - 包含 has_extractable_data=false 的文件（§4.12 边界用例）
     */
    UUID syncAllFiles(UUID taskId);
}
```

#### 5.8.3 闭月邮件触发条件

```java
// AFTER_COMMIT 事件监听器
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void onCommitSuccess(CommitSuccessEvent event) {
    // 1. 检测是否引入新 reporting period
    Set<String> newPeriods = commitAuditRepo.findNewlyIntroducedPeriods(event.getTaskId());
    if (!newPeriods.isEmpty()) {
        // 2. 触发新闭月邮件（同步 Java 现有邮件服务，不走 Python）
        closedMonthMailService.notify(event.getCompanyId(), newPeriods);
        // 3. 同步事件日志（§5.4.1 Q16 简化版，不重试）
        notificationEventService.log(event.getTaskId(), "NEW_CLOSED_MONTH",
            Map.of("newPeriods", newPeriods));
    }
}
```

---

### 5.9 边界用例 — 无可提取数据（2026-05-06 新增）

> 需求来源：[requirement-analysis §4.12](./requirement-analysis.md#412-edge-case--documents-without-extractable-data2026-05-06-新增)

**业务规则**: 全部文件 `has_extractable_data=false` 时跳过 5a/5b/5c，**仅同步到 Imported Statements**；混合批次不阻塞有数据文件流程。

```java
public interface NoDataHandlerService {
    /**
     * 由 Python 端 OcrResultSqsProcessor.handleResult() 收到所有结果后调用：
     * 聚合 task 下所有 file 的 has_extractable_data 字段：
     *   - 全部 false → 推进 task.status=NO_DATA_BYPASS（新增枚举值）
     *                  → AFTER_COMMIT 调 ImportedStatementsService.syncAllFiles()
     *                  → 推进 task.status=COMPLETED（跳过 MEMORY_LEARN，无需学习）
     *                  → 前端轮询发现状态变化，弹"未提取到财务数据"提示
     *   - 全部 true  → 走正常 5a/5b/5c 流程
     *   - 混合       → 仅有数据文件参与 5a 摘要 + 5b 冲突 + 5c commit；
     *                  无数据文件在 5c AFTER_COMMIT 时一并 sync 到 Imported Statements
     */
    void evaluateExtractability(UUID taskId);
}
```

**新增枚举值**: `DocParseStatus.NO_DATA_BYPASS` —— 仅供"全部无数据"批次使用，区别于 `FAILED`（处理失败）。Sweeper 不需要扫描该状态（瞬态）。

---

### 5.10 边界用例 — Steps Navigation 变更检测（2026-05-06 新增）

> 需求来源：[requirement-analysis §4.13](./requirement-analysis.md#413-edge-case--steps-navigation2026-05-06-新增)

**核心契约**: Previous 在所有步骤都可用；回退后**未修改**则保留下游结果不重跑；**有修改**则重跑下游 + 清空旧 conflict resolutions。判定靠 `mapping_snapshot_hash` 对比。

```java
@RestController
@RequestMapping("/api/v1/docparse/tasks/{taskId}")
public class NavigationController {

    /**
     * 用户在 5a/5b/5c 点 Previous 回到 Review 时调用。
     * 返回值告知前端是否需要"置灰下游 + 重跑"。
     */
    @PostMapping("/navigate-back")
    @Transactional
    public DocParseNavigateBackRespVo navigateBack(
            @PathVariable UUID taskId,
            @RequestBody DocParseNavigateBackReqVo req) {
        return navigationService.handleNavigateBack(taskId, req.getTargetStep());
    }
}

public interface NavigationService {
    /**
     * 1. 计算当前 mapping_snapshot_hash（基于 ai_ocr_extracted_row + ai_ocr_mapping_result 的稳定序列化哈希）
     * 2. 与 ai_ocr_task.mapping_snapshot_hash 对比：
     *    - 相等 → mappingChanged=false，前端无延迟前进
     *    - 不等 → mappingChanged=true，执行：
     *        a. 清空 ai_ocr_conflict_record 和 ai_ocr_conflict_note 的 resolution（保留 thread 历史）
     *        b. 推进 task.status=REVIEWING（即使是从 CONFLICT_RESOLUTION 回来）
     *        c. 清空 ai_ocr_task.summary_cache（强制 5a 重新聚合）
     *        d. 更新 mapping_snapshot_hash + mapping_changed_at
     * 3. 返回 { mappingChanged, clearedConflictCount, message }
     */
    DocParseNavigateBackRespVo handleNavigateBack(UUID taskId, NavStep targetStep);

    /**
     * 计算稳定 hash：SHA-256(JSON(sorted_rows + sorted_mappings))
     * 关键字段：row.value、row.account_label、row.reporting_period、mapping.lg_category
     */
    String computeSnapshotHash(UUID taskId);
}
```

**Conflict 清空策略**: `ai_ocr_conflict_record.resolution_action` 重置为 NULL，但 `ai_ocr_conflict_note` 不删除（用户历史 thread 是审计记录的一部分，下次可见）。

---

### 5.11 后端基础设施（2026-05-06 技术 Story）

> 需求来源：[requirement-analysis §4.14](./requirement-analysis.md#414-backend-infrastructure--framework-setup2026-05-06-新增--技术-story)

本 Story 是其他 Story 的前置依赖，多数已在原 §1-§4 中覆盖。本节仅追加**Liang Chunru 验收清单**层面的明确说明：

| 基础能力 | 现状 | 对应章节 |
|---------|------|---------|
| S3 安全存储 + presigned 直传 | 已设计 | §2.1 / §5.4.3 / §5.4.4 |
| 唯一 ID 关联 company + upload session | 已设计（task_id + file_id + file_hash） | §3.1 / §3.2 |
| 文件类型校验（PDF/Excel/CSV/JPG/JPEG/PNG/TIFF） | 已设计 | §6.2 |
| 文件大小限制（单 20MB / 批 100MB） | DocParseProperties 配置 | §1.1 |
| Company User / Admin / Portfolio Admin 访问控制 | 走 JWT scope 校验 | §6.1 |
| OCR provider（eSapiens）API key 安全存储 | AWS Secrets Manager（Python 端读取） | python-design.md |
| SQS 处理队列（OCR 路径 + 直接解析路径） | 已设计 3 队列 | §4.1-4.5 |
| 内部数据契约（line items / 文档类型 / 报告周期 / source ref） | extracted_table/row schema | python-design.md / database-schema.md |
| 为未来 LG 财务分类扩展留空间 | mapping_result.lg_category 字符串字段，无枚举绑定 | database-schema.md |
| AI provider 集成测试 | OpenRouter / Instructor，Story #4 实现 | python-design.md |
| Audit Logging（company / user / timestamp / file type / file size） | ai_ocr_file 表已包含 + commit_audit 全量审计 | §3.1 |

**新增 Liang Chunru 验收点**: 所有 5a/5b/5c 端点必须支持 `X-Request-Id` 透传到 SQS 消息和审计日志，便于跨 Java/Python 链路追踪。

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

`OcrResultSqsProcessor` 消费结果消息时，必须校验 `fileId` 对应的 `ai_ocr_file` 记录的 `task_id` → `ai_ocr_task.company_id` 与消息中的 `companyId` 一致，防止跨公司数据越权。

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
| `python_worker` | 完全访问 Python 拥有的表 + `SELECT` 权限访问 `ai_ocr_task`、`ai_ocr_file`（查状态） + 零权限访问 `fi_*` 表 |

---

## 7. 变更日志

| 日期 | 版本 | 变更摘要 | 关联需求 |
|------|------|---------|---------|
| 2026-04-16 | v1.0 | 首版：DDD 模块结构、SQS 集成、上传/审核/提交流程 | 初始 EPIC |
| 2026-04-19 | v1.1 | 新增 Verify Data Summary 两阶段、冲突 Note thread、Cancel 移除 | Story #5/#6/#7 |
| 2026-04-20 | v1.2 | S3 Presigned URL 直传、Task 修订、相似度提示、记忆学习进度 | 项目内部补丁 |
| **2026-05-06** | **v1.3** | **Step 5 拆分为 5a/5b/5c**：新增 `MappingSummaryController` / `ConflictResolutionController` / `CommitController` / `NavigationController`；`ai_ocr_task` 新增 4 字段（mapping_snapshot_hash / mapping_changed_at / has_extractable_data / summary_cache）；新增 `NoDataHandlerService` / `ProformaForecastService` / `ImportedStatementsService` / `NavigationService`；冲突解决改为单冲突逐个 + Note 必填硬校验；Commit 后同步所有文件到 Imported Statements 文件夹 + 闭月邮件 + Benchmark 跳转；新增 `DocParseStatus.NO_DATA_BYPASS` 状态 | [requirement-analysis §4.9-4.14](./requirement-analysis.md#49-step-5a--mapping-summary-page2026-05-06-新增) |
