# OCR Agent Java 端设计 (CIOaas-api)

> **技术栈**: Java 17 + Spring Boot 3 + Spring Cloud Gateway + AWS S3/SQS
> **关联文档**: [设计理念](./design-philosophy.md) · [需求分析](./requirement-analysis.md) · [系统架构](./system-architecture.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md) · [用户输入需求清单](../user-input-requirements.md)

---

## 0.5 文档定位说明

本文档**主要描述 Java 端"文件上传"相关的实现层细节**（presigned URL 直传、magic bytes 校验、S3 集成、Imported Statements 同步、上传错误码等）—— 因为这是 Java 端面向用户的核心职责（参见 [user-input-requirements.md §2 R-2.1/R-2.2](../user-input-requirements.md#2-javapython-边界要求2026-05-06)）。

其他 Java 端实现（commit / conflict resolution / note thread / memory learn producer / navigation 等）：
- **接口职责定义** → 参见 [api-doc.md](./api-doc.md)（端点 URL、请求/响应字段、Controller 方法）
- **业务规则与状态契约** → 参见 [system-architecture.md](./system-architecture.md)（4 步流程、状态机、跨域权限）
- **AI 智能业务逻辑** → 参见 [python-design.md](./python-design.md)（Python 端为业务主导方）

本文档相关章节（§5.4 之后）只保留 Java 端**实现层面的设计决策**：事务边界、AOP 切面、错误处理策略、状态机推进的并发防护等，不再重复接口签名。

---

## 0. 接口清单（→ 见独立接口文档）

Java 端对外接口（REST 端点 + SQS 生产者 + SQS 回传消费者）的**完整清单 + 详细职责**已抽取到独立接口文档：

📘 **[OCR Agent 接口文档](./api-doc.md)** — 先看 §1 总览（一行一个接口），需要细节时跳转 §2-§3 详细章节

| 接口类别 | 数量 | 索引位置 |
|---------|:---:|---------|
| REST 端点（Java 对外，前端调用）| 25 | [api-doc.md §1.1](./api-doc.md#11-rest-端点java-对外前端调用) |
| SQS 生产者（Java → Python，3 个出口队列）| 3 | [api-doc.md §1.2.1](./api-doc.md#121-java--python出口队列) |
| SQS 消费者 handler（Python → Java，4 种 messageType）| 4 | [api-doc.md §1.2.2](./api-doc.md#122-python--java回传队列按-messagetype-多路复用) |

> 本文档 §1-§7 描述 Java 端**实现层**（包结构、Service 层、事务边界、AOP 切面、错误处理等）。如需查看具体 endpoint 的 URL/DTO/职责，请直接跳转 [api-doc.md](./api-doc.md)。

---

## 1. 模块结构

### 1.1 包结构

在现有 DDD 结构下新增 `docparse` 域（与 `fi/`、`quickbooks/`、`storage/` 同级），采用 4 层 DDD 架构：

```
com.gstdev.cioaas.web.docparse/
├── interfaces/                    ← 入口层（Interfaces Layer）
│   ├── controller/
│   │   ├── DocParseController.java        # Task 生命周期：create / revise / status / result / history
│   │   ├── UploadController.java          # 上传：request-urls / complete / abort
│   │   ├── FileViewController.java        # 文件查看：download-url（presigned GET）
│   │   ├── ReviewController.java          # PATCH /tasks/{id}/review（保存编辑 + 清空 summary_cache）
│   │   ├── MappingSummaryController.java  # 5a：mapping-summary / verify/start / verify/progress
│   │   ├── ConflictResolutionController.java  # 5b：conflicts / conflicts/{id}/resolve
│   │   ├── ConflictNoteController.java    # Note thread：GET/POST /conflicts/{id}/notes
│   │   ├── CommitController.java          # 5c：commit / commit/result
│   │   ├── NavigationController.java      # §4.13：navigate-back（hash 对比 + 触发 REMAP_ONLY）
│   │   ├── SimilarityHintController.java  # similarity-hints 列表 + PATCH 决策
│   │   └── MemoryLearnController.java     # memory-learn 状态/历史/手动重试
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

## 2. 文件上传实现层（Java 核心职责）

> **本章是 Java 端的核心职责章节**（参见 §0.5）。所有端点 URL / DTO / 响应字段定义在 [api-doc.md §2 端点 6-9](./api-doc.md#6-uploadrequest-urls-post)；本节聚焦实现层决策。

**重要变更（2026-04-20）**:
- 文件上传改为 **S3 Presigned URL 直传**（前端直传 S3，不经 Java）
- 文件查看使用 **Presigned GET URL**（前端直查 S3）

### 2.1 S3 Presigned URL 上传流程（实现层时序）

旧 multipart 经 Java 中转方案已废弃（Java 服务器带宽瓶颈）。新方案 3 次 HTTP 调用，Java 实现层关键决策如下：

**步骤 1：前端调用 `POST /upload/request-urls`（参见 [api-doc.md #6](./api-doc.md#6-uploadrequest-urls-post)）**

```
Java 处理 (UploadController#requestPresignedUrls):
  ├─ JWT + company 归属校验
  ├─ 预校验（按文件逐项进行，部分失败不阻断其余）：
  │   ├─ 文件大小校验（单文件 ≤20MB / 批次 ≤100MB）
  │   ├─ 扩展名白名单（参见 §6.2）
  │   └─ SHA-256 hash 重名查询（ai_ocr_file 唯一约束）
  ├─ 合法文件 → 建 ai_ocr_file 记录 [status=PENDING] + 生成 S3 presigned PUT URL（15 min）
  └─ 非法文件 → 在 uploads[] 数组中按位返回 error 项（不抛全局异常）
```

**S3 Key 命名规范**: `ocr-uploads/{companyId}/{taskId}/{fileId}/{hash}.ext` —— 路径含 companyId 保证 IAM 策略可按 prefix 隔离权限。

**步骤 2：前端 PUT 直传 S3（无 Java 参与）**

前端使用 `XMLHttpRequest` 走 presigned URL 上传 + `progress` 事件追踪。S3 Bucket 必须先配置 CORS（参见 §5.4.2）。

**步骤 3：前端调用 `POST /upload/complete`（参见 [api-doc.md #7](./api-doc.md#7-uploadcomplete-post)）**

```
Java 处理 (UploadController#completeUpload):
  ├─ ⚠️ 安全：从 DB 查 s3Key（不信任前端传入，参见 §5.4.3）
  ├─ s3:HeadObject 验证对象存在 + ETag/actualSize 一致
  ├─ 读取首 2KB 做 MIME + magic bytes 双重校验（白名单见 §6.2）
  ├─ 通过 → file.status=UPLOADED + 发 SQS ocr-extract-queue（mode=FULL_EXTRACT）
  └─ 失败 → s3:DeleteObject 清理 + file.status=FILE_FAILED + 错误码（见 §2.4）
```

**为什么必须做 magic bytes 校验**: 前端可能上传一个改了扩展名的恶意文件（如 `.exe` 改为 `.pdf`）。仅看扩展名/Content-Type 不安全，必须读首 2KB 验证 magic bytes。

### 2.2 Presigned GET URL（文件查看）

ReviewPage 加载 PDF/Excel 时，前端向 `POST /files/{fileId}/download-url`（参见 [api-doc.md #9](./api-doc.md#9-filesfileiddownload-url-post)）请求临时 URL。

**实现层决策**:
- URL 生存期 **5 分钟**（不是 15 分钟，参见 §5.4.3 的安全收紧）
- 生成前必须验证 JWT + company 归属 + `ai_ocr_file.deleted=false`
- 不附加 `Content-Disposition: attachment` —— 让浏览器直接预览

前端用此 URL：PDF/图片直接 `<iframe>` 或 `<img>` 渲染；Excel 由前端用 SheetJS 从该 URL 拉取后解析。

### 2.3 Task 修订端点（实现层）

> 端点 URL / 请求字段参见 [api-doc.md #2](./api-doc.md#2-tasksidrevise-post)。

**Java 实现层关键决策**（事务内）:
- 校验 parent task.status ∈ {COMPLETED, SUPERSEDED}
- 新 task 沿用 parent 的 `s3_key`（不重新上传文件，仅 COPY `ai_ocr_file` 行）
- copy-on-write 继承：`ai_ocr_extracted_table/row` 由 Python 通过 SQS 异步复制；`ai_ocr_mapping_result` 由 Java 直接 INSERT
- `revision_number = parent.revision_number + 1`（受 UNIQUE 约束保护并发，参见 §3.2）
- Commit 成功后置 parent.status=SUPERSEDED + parent.superseded_by=self.id（在 §5.4 commit 事务中处理）

**Cancel 选项已移除**（Asana 2026-04-19）。用户若要放弃提交直接退出页面，task 状态保持 REVIEWING。

### 2.4 上传错误码

| 错误码 | 触发场景 | HTTP 状态 |
|-------|---------|----------|
| `FILE_TOO_LARGE` | 单文件超 20MB | 400 |
| `BATCH_TOO_LARGE` | 批次超 100MB | 400 |
| `UNSUPPORTED_TYPE` | 扩展名/MIME 不在白名单 | 400 |
| `MAGIC_BYTES_MISMATCH` | 扩展名与文件头不一致 | 400 |
| `DUPLICATE_NAME` | 同 company + 同 hash 已存在活跃记录 | 409 |
| `S3_OBJECT_NOT_FOUND` | `/upload/complete` 但 HeadObject 失败 | 404 |
| `INVALID_HASH_FORMAT` | hash 不符合 `^[a-f0-9]{64}$` | 400 |

错误信息均由 Java 生成（R-2.2 约束：用户可见错误必须由 Java 转换，Python 不直接面向用户）。

---

## 3. 数据表设计（业务语义）

> **DDL 权威定义**：所有表结构、索引、约束、权限 GRANT 语句的**唯一权威定义**在 [database-schema.md](./database-schema.md)。本节仅说明 Java 端表的**业务语义**、字段的设计意图，和表之间的关系。任何 DDL 变更先改 database-schema.md，再同步这里的说明文字。

### 3.1 Java 拥有的表（概览）

> **2026-05-06 清理（v1.5）**：删除 `ai_ocr_notification`（事件统一并入 `ai_ocr_task_state_log`）+ 删除 `ai_ocr_extraction_skip_log`（事件并入 state_log 的 `EXTRACT_NO_DATA`）。详见本文件 §7 变更日志和 [user-input-requirements.md §6 Q3](../user-input-requirements.md#q-3-state_log-是否过度设计).

| 表 | 用途 | DDL 引用 |
|----|------|---------|
| `ai_ocr_task` | Task 生命周期（批次级状态 + 版本化字段 + summary_cache + mapping_snapshot_hash） | [§2.1](./database-schema.md#21-ai_ocr_task) |
| `ai_ocr_file` | 单个文件的上传 + 处理状态（12 子阶段 + stage_detail JSONB + has_extractable_data） | [§2.2](./database-schema.md#22-ai_ocr_file) |
| `ai_ocr_task_state_log` | **总状态日志表**（25+ event_type，覆盖 4 步流程所有状态变更，落地 R-3.4） | [§2.9](./database-schema.md#29-ai_ocr_task_state_log) |
| `ai_ocr_conflict_note` | 冲突解决 note（Story #7，支持 thread） | [§2.4](./database-schema.md#24-ai_ocr_conflict_note) |
| `ai_ocr_memory_learn_log` | 记忆学习审计（Python INSERT，跨域例外） | [§2.5](./database-schema.md#25-ai_ocr_memory_learn_log) |
| `ai_ocr_commit_audit` | fi_* 写入审计（written/overwritten/skipped） | [§2.6](./database-schema.md#26-ai_ocr_commit_audit) |
| `ai_ocr_erasure_log` | GDPR 擦除审计 | [§2.7](./database-schema.md#27-ai_ocr_erasure_log) |
| `ai_ocr_similarity_hint` | 相似度检测结果（Python INSERT，跨域例外） | [§2.8](./database-schema.md#28-ai_ocr_similarity_hint) |

### 3.2 关键设计决策解释

#### Task 版本化（2026-04-20 新增字段）
`parent_task_id` / `revision_number` / `revision_reason` / `superseded_by` 支持"基于历史 task 修订"场景。原任务在修订版 Commit 成功后自动置为 `SUPERSEDED`，前端展示 v1 → v2 → v3 版本链。**并发防护**：`UNIQUE (parent_task_id, revision_number) WHERE parent_task_id IS NOT NULL` 约束防止两个用户同时创建相同版本号。

#### File 处理阶段 (`processing_stage` + `stage_detail`)
12 个子状态精确描述 Python 处理进度（见 [database-schema.md §1.2 Processing Stage](./database-schema.md#processing-stage12-个子状态仅-filestatusprocessing-时有效)）。`stage_detail JSONB` 由 Python 透传：例如 `MAPPING_MEMORY_APPLY` 阶段带 `{ appliedMemoryCount: 8, totalRowCount: 47 }`，前端渲染为"已应用 8/47 条记忆"。

#### 重名文件校验的唯一约束
`UNIQUE (company_id, file_hash) WHERE deleted = false AND status != 'FILE_FAILED'` —— 只对"活跃"记录生效。`FILE_FAILED` 状态的文件允许用户重新上传同名文件（因为之前失败了）。

#### 通知机制的简化（Q16 + 2026-05-06 清理）
**不主动推送邮件/push**，用户通过 LG Dashboard "待处理任务" 列表自行发现。原 `ai_ocr_notification` 表已删除，所有事件统一写入 `ai_ocr_task_state_log`（含 PARSE_COMPLETE / COMMIT_COMPLETE / NEW_CLOSED_MONTH 等 event_type），字段为 `event_type + payload JSONB + created_at + actor`。**没有重试 / 推送 / channel 概念**——只是一份事件流，用户主动查询。

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


## 4. SQS 集成（实现层）

> **接口契约**: SQS 队列名 / messageType / 消息字段定义参见 [api-doc.md §3 SQS 接口详情](./api-doc.md#3-sqs-接口详情)。本节聚焦 Java 端实现层决策（事务边界、幂等、并发防护、Sweeper 自愈）。

### 4.1 OcrExtractSqsProducer 设计要点

参见 [api-doc.md SQS-1 ocr-extract-queue](./api-doc.md#sqs-1-ocr-extract-queue) 的完整字段定义。Java 实现层关键决策：

- **粒度**: 一条消息对应一个文件（不是一个 task），原因：独立重试、天然并发、部分失败隔离
- **mode 字段路由**: `FULL_EXTRACT`（首次上传，默认）/ `REMAP_ONLY`（navigate-back 检测 mapping 变化触发，参见 §5.10）
- **触发时机**: `/upload/complete` 通过校验后**同一事务内**发送（不延迟到 AFTER_COMMIT，因为本事务无回滚风险——只更新 file.status）
- **HMAC-SHA256 签名**: 见 §6.3

### 4.2 OcrResultSqsProcessor 设计要点

`OcrResultSqsProcessor` implements `MessageProcessor`，按 `messageType` 多路分发到 4 个 handler。**接口契约见 [api-doc.md §3.2 MSG-1 ~ MSG-4](./api-doc.md#32-回传队列python--java)**；本节仅描述各 handler 的实现层决策。

#### 4.2.1 OcrProgress handler 实现层决策

> 字段定义见 [api-doc.md MSG-1 OcrProgress](./api-doc.md#msg-1-ocrprogress)。

- **幂等去重**: 用 `processing_stage` 的 ordinal 比较丢弃过期消息（避免乱序覆盖更新后的阶段）
- **FOR UPDATE 锁**: 锁 `ai_ocr_file` 行后再判定阶段，防并发 worker 同时处理两条 progress 消息
- **`stage_detail` JSONB 透传**: 必须原样写入 DB，前端按 frontend-design §5.2 渲染细节文字
- **状态推进**: 首次到达时推进 `file.status: QUEUED → PROCESSING` + `task.status: UPLOAD_COMPLETE → PROCESSING`（CAS 防止覆盖更后状态）
- **不触发终态**: 仅 OcrResult handler 才触发 `task.status` 终态转换（→ SIMILARITY_CHECKING / REVIEWING）

**`ai_ocr_file.stage_detail JSONB` 列**: DDL 见 [database-schema.md §2.2](./database-schema.md#22-ai_ocr_file)。前端 `GET /tasks/{id}/status` 读这张表时把 `stage_detail` 字段透传给前端，前端按 `frontend-design.md §5.2` 规则渲染细节文字（"第 3/8 页"、"已应用 8/47 条记忆"等）。

#### 4.2.2 OcrResult handler 实现层决策

> 字段定义见 [api-doc.md MSG-2 OcrResult](./api-doc.md#msg-2-ocrresult)。

- **`@Transactional` + FOR UPDATE 锁 task 行**: 防御场景 —— 两个 worker 同时处理 task 最后两个文件的 OcrResult，无锁会导致两条消息都把 task 推进到 SIMILARITY_CHECKING（重复触发）
- **CAS 更新 file.status**: `expectedStatus=PROCESSING`；返回 0 行则视为重复消息丢弃（幂等）
- **批次完成判定**（在锁内计数）:
  - 全部 `REVIEW_READY`（至少一个成功）→ `task.status=SIMILARITY_CHECKING` + 发布 `TaskReadyForReviewEvent`
  - 全部 `FILE_FAILED` → `task.status=FAILED`
  - 否则保持 PROCESSING
- **AFTER_COMMIT 入队**: `TaskReadyForReviewEvent` 由 `OcrSimilarityCheckSqsProducer` 在 AFTER_COMMIT 阶段消费 + 发 SQS（避免事务回滚后 Python 已收到悬空 task）—— 见 §4.2a

#### 4.2.3 OcrSimilarityCheckResult handler 实现层决策

> 字段定义见 [api-doc.md MSG-3 OcrSimilarityCheckResult](./api-doc.md#msg-3-ocrsimilaritycheckresult)。

- **跨域 INSERT 例外**: `ai_ocr_similarity_hint` 由 Python 直接 INSERT（参见 §3.2 + database-schema.md §4 GRANT 配置）；Java handler **只做状态推进 + state_log 写入**
- **跨公司归属校验**: 比对 `task.company_id == msg.companyId`，不一致直接丢弃（防伪造）
- **CAS 推进状态**: 仅 `SIMILARITY_CHECKING` 才能转；过期消息丢弃
- **失败态语义**: `SIMILARITY_CHECK_FAILED` 是**预留状态**（将来邮件通道可用），目前不阻塞用户：前端在该状态下仍提供"跳过相似度提示直接进入审核"按钮
- **Sweeper 不扫描 `SIMILARITY_CHECKING`**: Python 崩溃会被 SQS 重试 3 次后进 DLQ；DLQ 监控触发人工介入即可

#### 4.2.4 OcrMemoryLearnProgress handler 实现层决策

> 字段定义见 [api-doc.md MSG-4 OcrMemoryLearnProgress](./api-doc.md#msg-4-ocrmemorylearnprogress)。

| `learnStage` | Java 端动作 |
|--------------|-------------|
| `MEMORY_LEARN_IN_PROGRESS` | CAS：`MEMORY_LEARN_PENDING → MEMORY_LEARN_IN_PROGRESS` |
| `MEMORY_LEARN_COMPLETE` | CAS：`MEMORY_LEARN_IN_PROGRESS → COMPLETED` + 写 state_log `MEMORY_LEARN_COMPLETE` |
| `MEMORY_LEARN_FAILED` | 读 `ai_ocr_memory_learn_log` 计数：`<3` 回 PENDING 等重试；`≥3` 进 MEMORY_LEARN_FAILED 终态 |

**关键约束**: `MEMORY_LEARN_FAILED` 终态 **不回滚 fi_***（财务数据已 committed，不允许重做）。`ai_ocr_memory_learn_log` 由 Python 跨域 INSERT，Java 不重复写。

### 4.2a OcrSimilarityCheckSqsProducer 设计要点

> 字段定义见 [api-doc.md SQS-2 ocr-similarity-check-queue](./api-doc.md#sqs-2-ocr-similarity-check-queue)。

- **触发**: 由 `OcrResultSqsProcessor#handleResult` 通过 `publishEvent(TaskReadyForReviewEvent)` 派发
- **消费**: `@TransactionalEventListener(phase = AFTER_COMMIT)` 才发送 SQS，**严禁**在 `BEFORE_COMMIT`（事务回滚时 Python 已收到悬空 task）
- **聚合粒度**: 每个 task 入队**仅 1 条消息**（聚合所有 mapping_result.account_label）；不是 per-file
- **HMAC-SHA256 签名**: 见 §6.3

### 4.3 OcrMemoryLearnSqsProducer 设计要点

> 字段定义见 [api-doc.md SQS-3 ocr-memory-learn-queue](./api-doc.md#sqs-3-ocr-memory-learn-queue)。

Java 端实现层决策：

- **触发时机**: `/tasks/{id}/commit` 事务 **AFTER_COMMIT** 阶段（fi_* 写入成功后）
- **payload 构建**: 对每个 `extracted_row` 比对 `originalAiCategory`（AI 初始建议，存于 `ai_ocr_mapping_result.original_ai_category`）vs `confirmedCategory`（用户最终确认，存于 `ai_ocr_mapping_result.lg_category`），生成 `mappingComparisons[]` 数组
- **`wasOverridden` 字段**: Java 端计算 `originalAiCategory != confirmedCategory`；Python 端只学习 `wasOverridden=true` 的条目（业务规则在 [python-design.md §X memory learn](./python-design.md)）
- **重试支持**: `attemptNumber` 字段；首次为 1，`MemoryLearnController#retry` 时递增
- **HMAC-SHA256 签名**: 见 §6.3

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

异步消息驱动的状态机存在"消息丢失"或"Python/Java 崩溃在中间态"导致任务永久停留的风险。通过 `@Scheduled(fixedDelay=120_000)` 每 2 分钟扫描自愈。

**扫描策略**:

| 扫描分支 | 阈值 | 动作 |
|---------|------|------|
| `sweepDraftExpired` | DRAFT > 24h | 删 S3 对象 + `status=EXPIRED`（清理未完成任务）|
| `sweepZombieProcessing` | file.PROCESSING > 20min | 跨 schema SELECT 检查 Python 是否已写 `ai_ocr_extracted_table`：有 → 强制推进 REVIEW_READY；无 → FILE_FAILED |
| `sweepStuckVerifying` | task.VERIFYING > 10min | `status=FAILED`（verify 代码死循环或连接池耗尽） |
| `sweepStuckMemoryLearn` | MEMORY_LEARN_IN_PROGRESS > 10min | `status=MEMORY_LEARN_FAILED`（fi_* 不回滚） |

**不扫描的状态**（设计上无 TTL 风险）:
- `SIMILARITY_CHECKING` —— Q16 简化为瞬态事件日志，Python 崩溃由 SQS DLQ 兜底
- `COMMITTING` —— Q7 方案 B 下事务 rollback 时 `status` 自动回 REVIEWING
- `SIMILARITY_CHECKED` —— 用户登录时从待审核列表自然发现

**实现层关键决策**:
- 使用 `@Scheduled(fixedDelay)` 而非 `fixedRate` — 确保前一次完成后才启动下一次
- 每个 sweep 分支使用**独立事务**，失败不影响其他分支
- 日志级别 WARN / INFO，扫描结果发 metric 到 Prometheus，僵尸任务数 > 0 时触发告警

### 4.7 Java/Python 数据库物理部署模型

**关键决策（2026-04-20）**: Java 和 Python 共用**同一个** PostgreSQL RDS 实例 + **同一个 schema**（简化部署，避免跨库 JOIN）。通过数据库角色权限实现读写隔离 —— 完整 GRANT 语句见 [database-schema.md §4 数据库角色与权限](./database-schema.md#4-数据库角色与权限)。

**角色权限矩阵（实现层概览）**:

| 表归属 | `java_app` 角色 | `python_worker` 角色 |
|-------|-----------------|---------------------|
| Java 拥有的 `ai_ocr_*`（task / file / state_log / conflict_note / commit_audit）| RWUD | SELECT |
| 跨域例外：`ai_ocr_memory_learn_log` | RWUD | INSERT only（不允许 UPDATE/DELETE，防篡改）|
| 跨域例外：`ai_ocr_similarity_hint` | RWUD | INSERT only |
| Python 拥有的 `ai_ocr_*`（extracted_table / row / mapping_result / conflict_record）| SELECT | RWUD |
| Python 私有：`ai_ocr_mapping_memory*` | 无权限（跨公司商业机密）| RWUD |
| 财务表 `fi_*` | RWU | REVOKE ALL |

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

**副作用（2026-05-06 补充，关系到 5a/5b/§4.13 一致性）**:

| 副作用 | 触发条件 | 字段更新 |
|-------|---------|---------|
| 清空 `summary_cache` | 任意行项被改/删/新增、任意 mapping.lg_category 改 | `ai_ocr_task.summary_cache = NULL`（强制 5a 重新聚合）|
| 更新 `mapping_changed_at` | 同上 | `ai_ocr_task.mapping_changed_at = NOW()` |
| **不重算 `mapping_snapshot_hash`** | — | hash 仅在 `verify/start` 或 `navigate-back` 时计算（避免每次编辑都重算）|
| 写 state_log | 每次 PATCH 成功 | `event_type=REVIEW_EDITED, payload={updatedRowCount, updatedMappingCount, actor}` |

### 5.4 Commit 流程实现层（事务边界与并发防护）

> **业务流程定义** → [system-architecture.md 4 步流程 第 4 步](./system-architecture.md)；**端点 URL/字段** → [api-doc.md #18 /commit](./api-doc.md#18-tasksidcommit-post) + [#19 /commit/result](./api-doc.md#19-tasksidcommitresult-get)；**Proforma/冲突业务规则** → [python-design.md](./python-design.md)。本节聚焦 Java 端事务边界与并发设计。

#### 5.4.1 两阶段事务模型

```
事务内（@Transactional(propagation=REQUIRED, rollbackFor=Exception.class)）:
    ① FOR UPDATE 锁 ai_ocr_task 行（防并发 Commit）
    ② CAS 校验：status IN (REVIEWING, CONFLICT_RESOLUTION) → COMMITTING
    ③ 读 ai_ocr_extracted_row + ai_ocr_mapping_result
    ④ 按 resolution 策略写 fi_* 财务表（Actuals）+ 调 ProformaForecastService.appendVersion()
    ⑤ 写 ai_ocr_commit_audit（written/overwritten/skipped）
    ⑥ task.status=COMMITTED；files.status=FILE_COMMITTED
    ⑦ 若 revision：parent.status=SUPERSEDED + parent.superseded_by=self.id
    ⑧ publishEvent(CommitSuccessEvent)（Spring 事件，不立即发 SQS）

AFTER_COMMIT（@TransactionalEventListener(phase = AFTER_COMMIT)）:
    ⑨ ImportedStatementsService.syncAllFiles(taskId)（含无数据文件）
    ⑩ 触发下游 normalization 流程
    ⑪ 检测新 closed month → 调 ClosedMonthMailService.notify()（Java 职责，不是 Python）
    ⑫ 构建 mappingComparisons → 发 ocr-memory-learn-queue（参见 §4.3）
    ⑬ task.status=MEMORY_LEARN_PENDING
    ⑭ 写 ai_ocr_task_state_log（COMMIT_COMPLETE / NEW_CLOSED_MONTH，仅事件流，不主动推送）
```

#### 5.4.2 关键实现层约束

| 约束 | 实现机制 |
|------|---------|
| 并发互斥 | `@Lock(LockModeType.PESSIMISTIC_WRITE)` 或 `SELECT ... FOR UPDATE` + CAS（受影响 0 行 → 抛 INVALID_STATUS_FOR_COMMIT） |
| ⚠️ SQS 必须在 AFTER_COMMIT 发 | `@TransactionalEventListener(phase = AFTER_COMMIT)`，否则事务回滚后 Python 已收到记忆学习消息会写入脏记忆 |
| 部分写入禁止 | 任一 metric 写入失败 → 整个 @Transactional 回滚，task.status 自动恢复到 REVIEWING/CONFLICT_RESOLUTION |
| Cancel 已移除 | 用户放弃提交直接退出页面，task 状态保持 REVIEWING |

#### 5.4.3 Commit 失败的恢复路径（Q7 方案 B：可恢复重试）

Commit 失败**不置 task.status=FAILED**。事务 rollback 后 task.status 自动回到 `REVIEWING`，用户可直接在 ConfirmPage 再点 "Commit" 重试（数据干净，幂等执行）。

**异常处理矩阵**:

| 异常类型 | 处理 | task.status 结果 |
|---------|------|-----------------|
| 业务异常（INVALID_STATUS_FOR_COMMIT 等）| 直接抛出，不回滚 | 保持原值 |
| 技术异常（DB 死锁/字段约束/OOM/网络）| @Transactional 自动回滚 + 抛 `COMMIT_FAILED_RETRYABLE` | 自动恢复为进入方法前的值 |

**用户体验**: Java 返回 500 + errorCode=`COMMIT_FAILED_RETRYABLE` → 前端弹 Modal "数据未写入，请稍后重试 [重试] [取消]"；点重试再次 POST /commit 即可（task.status 还是 REVIEWING，幂等可接受）；24 小时内浏览器关闭也可恢复。

**何时真正 `task.status = FAILED`**（只有 3 种）:
1. 所有文件 FILE_FAILED（Phase 2 Python 处理全失败）
2. VERIFYING 阶段异常（Phase 4 验证代码 bug）— 由 Sweeper 10min 超时推进
3. DRAFT > 24 小时未操作 → EXPIRED（不是 FAILED，是单独的过期态）

Commit 失败不进 FAILED，是 Q7 方案 B 的核心契约。

### 5.4.1 通知事件记录（Q16 简化版，不发送）

**关键决策**: 系统**不主动推送通知**。以下所有场景都只写一条 `ai_ocr_task_state_log` 事件日志，用户下次登录 LG 主页时通过"待处理任务"自行发现。

> **2026-05-06 调整**: 原 `ai_ocr_notification` 表已删除，事件统一并入 `ai_ocr_task_state_log`（落地 R-3.4 "全流程状态留 log"）。

事件触发点（`TaskStateLogService.log()` 在各业务事务 AFTER_COMMIT 后调用）：

| event_type | 触发时机 | payload 字段示例 |
|------------|---------|------------------|
| `PARSE_COMPLETE` | task.status = REVIEWING 时 | `{totalFiles:3, completedFiles:3, failedFiles:0}` |
| `EXTRACT_NO_DATA` | 单文件 has_extractable_data=false 时（替代旧 `ai_ocr_extraction_skip_log`）| `{fileId, reason:"NO_FINANCIAL_DATA"}` |
| `COMMIT_COMPLETE` | task.status = COMMITTED 时 | `{writtenPeriods:["2024-01","2024-02"], writtenRows:47}` |
| `COMMIT_FAILED` | commit 事务抛异常时 | `{error:"..."}`（供运维排查） |
| `MEMORY_LEARN_COMPLETE` | task.status = COMPLETED 时 | `{newMemoryCount:5, updatedMemoryCount:3}` |
| `MEMORY_LEARN_FAILED` | 3 次重试后失败 | `{lastError:"..."}` |
| `NEW_CLOSED_MONTH` | commit 引入新期间时 | `{newPeriods:["2024-03"]}` |
| `SIMILARITY_CHECK_COMPLETE` | OcrSimilarityCheckResult 成功消费 | `{candidateCount:3, processingTimeMs:850}` |
| `SIMILARITY_CHECK_FAILED` | OcrSimilarityCheckResult 失败 | `{error:"..."}` |

### 5.4.2 S3 Bucket CORS 配置（生产必需）

Presigned URL 直传要求 S3 Bucket 配置 CORS 允许前端 origin。**严禁使用 `*` 或 localhost 作为 AllowedOrigins**。

| CORS 字段 | 生产值 | 开发环境 |
|----------|-------|---------|
| AllowedOrigins | `https://portal.lookingglass.com` | `http://localhost:8000`（独立 dev Bucket） |
| AllowedMethods | `PUT, GET` | 同上 |
| AllowedHeaders | `Content-Type, x-amz-*` | 同上 |
| ExposeHeaders | `ETag` | 同上 |
| MaxAgeSeconds | 3000 | 同上 |

Terraform 配置通过环境变量区分；**严禁**在生产 Bucket 上允许 localhost。

### 5.4.3 S3 Presigned URL 安全增强（实现层 5 项约束）

| # | 约束 | 实现机制 |
|---|------|---------|
| 1 | Presigned PUT 必须加 `content-length-range` 条件 | `PutObjectRequest.builder().contentLength(fileSize)` —— 防止绕过 20MB 限制 |
| 2 | Presigned GET 生存期缩短到 **5 分钟** | `signatureDuration(Duration.ofMinutes(5))`，不是 15 分钟（折中：大 PDF 加载需时间但过期可自动续签）|
| 3 | `/complete` 端点严禁信任前端传入的 s3Key | 必须从 `ai_ocr_file` 表查 `s3Key`，再调 `s3:HeadObject`（防伪造）|
| 4 | `file_hash` 格式强校验 | DTO 字段加 `@Pattern(regexp = "^[a-f0-9]{64}$")` 防注入 |
| 5 | CloudTrail S3 Data Events 启用 | 生产 Bucket 启用 PutObject/GetObject/DeleteObject 日志，存独立审计 Bucket（启用 MFA Delete）|

### 5.4.4 URL 响应字段统一（`expiresAt` ISO 时间戳）

全文统一使用 `expiresAt`（ISO 8601 时间戳）而非 `expiresIn`（秒数）。原因：前端直接用 `new Date(expiresAt) > Date.now()` 判断是否过期，无需额外保存"签发时刻"。响应字段示例见 [api-doc.md #6 / #9](./api-doc.md#6-uploadrequest-urls-post)。

### 5.5 DTO / VO 契约

DTO/VO 字段定义见 [api-doc.md §2 REST 端点详情](./api-doc.md#2-rest-端点详情)（每个端点列出请求 DTO + 响应 DTO 名称）。本章节不重复 DTO 字段定义。


### 5.6 Step 5a / 5b / 5c 实现层（接口对接说明）

> **接口职责定义** → [api-doc.md](./api-doc.md)（端点 #11-#19）；**业务规则** → [system-architecture.md](./system-architecture.md) + [python-design.md](./python-design.md)。本节仅说明 Java 端实现层的事务边界与状态机推进。

#### 5.6.1 Step 5a — Mapping Summary + Verify 触发（[api-doc.md #11-#13](./api-doc.md#11-tasksidmapping-summary-get)）

**核心契约**: 用户主动点击 "Start Verification" 才触发冲突检测；后端必须先做 hard gate 校验，存在 unmapped/unreviewed/缺失元数据的行项时**直接拒绝**进入 verify。

| 实现层关注点 | 决策 |
|------------|------|
| `getSummary` 缓存策略 | 命中 `ai_ocr_task.summary_cache` 直接返回；`mapping_changed_at` 变化或 cache=null 时重算并写回 |
| `startVerification` 事务 | FOR UPDATE 锁 task；CAS 推进 `REVIEWING → VERIFYING`；publishEvent 启动异步 ConflictDetectionJob |
| Hard gate 检查 | 三类硬错误：`UNMAPPED_ROWS`（lg_category 为空）/ `UNREVIEWED_ROWS`（user_reviewed=false 的非 confidence-high 项）/ `MISSING_METADATA`（account_label / value / reporting_period 任一为空）；任一非空 → 抛 `HARD_GATE_FAILED` 拒绝进入 verify |
| has_extractable_data=false 分支 | 跳到 §5.9 No-Data 分支（不进 verify）|
| 用户中途 Previous | `abortVerification(taskId)` 异步 Job 收到 cancel 信号，回到 REVIEWING |

#### 5.6.2 Step 5b — 单冲突逐个解决（[api-doc.md #14-#15](./api-doc.md#14-tasksidconflicts-get)）

**重大变更**（相对原批量 resolve）: 改为**逐个冲突解决**，前端弹窗驱动；**Note 强制非空**（与原 "可选填写 Note" 不同）。

| 实现层关注点 | 决策 |
|------------|------|
| 列表过滤 | 仅 Actuals 冲突参与；Proforma 整体豁免不入此列表（按 `lg_metric, reporting_period` 排序）|
| Note 必填 | DTO 上 `@NotBlank @Size(max=2000)`；Service 二次防御校验 |
| 状态校验 | `task.status IN (CONFLICT_RESOLUTION, VERIFYING)` 才允许 resolve |
| 写表 | `ai_ocr_conflict_record.resolution` + `ai_ocr_conflict_note`（thread 支持） |
| Save & Next 导航 | (1) 同 metric 下一未解决月 → (2) 跨 metric 第一未解决 → (3) 全部解决 → `isLast=true`（前端按钮变 "Save"，引导进入 5c）|
| 状态保持 | 全部解决后 `task.status=CONFLICT_RESOLUTION`（保持，等用户主动点 Commit）|

#### 5.6.3 Step 5c — Commit / Proforma / Imported Statements（[api-doc.md #18-#19](./api-doc.md#18-tasksidcommit-post)）

事务编排见 §5.4；本节列举 Java 端**新增的辅助 Service 职责**：

| Service 接口 | 职责 |
|------------|------|
| `ProformaForecastService.appendVersion()` | Proforma 追加新版本：找当前 active committed forecast（24 个月窗口最新版本）；上传月份 ∩ 现有月份 → 替换值；∉ 现有月份 → 追加月份；创建新 forecast_version 记录（user=上传者，supersedes=旧版本 ID）；旧版本保留为历史不删除（审计要求）|
| `ImportedStatementsService.syncAllFiles()` | 同步文件元数据到 Documents 服务的 "Imported Statements" 文件夹：该文件夹按 `company_id` 全局唯一，首次提交时由 CompanyDocService 自动创建；元数据包含 `{ fileName, s3Key, uploadedAt, uploadedBy, taskId, hasExtractableData }`；含 `has_extractable_data=false` 的文件 |
| `ClosedMonthMailService.notify()` | AFTER_COMMIT 事件监听器调用 `commitAuditRepo.findNewlyIntroducedPeriods(taskId)`，新 period 集合非空时调用 Java 现有邮件服务（不走 Python）+ 写 state_log `NEW_CLOSED_MONTH` |

**核心实现层差异**（相对原 §5.4 单一 commit）:
- Proforma 行项**不参与冲突解决**（豁免），独立走 `appendVersion`
- `ai_ocr_commit_audit` 全量记录（Proforma append 也算 written）
- 所有上传文件（含无数据）都通过 `syncAllFiles` 同步到 Documents
- AFTER_COMMIT 阶段并行触发：(a) Imported Statements 同步、(b) 闭月邮件、(c) 下游 normalization、(d) 记忆学习 SQS（仅 wasOverridden=true 行项）

---

### 5.7 边界用例 — 无可提取数据（NO_DATA_BYPASS）

> **业务规则** → [requirement-analysis §4.12](./requirement-analysis.md#412-edge-case--documents-without-extractable-data2026-05-06-新增)。本节仅说明 Java 端状态机决策。

`NoDataHandlerService.evaluateExtractability(taskId)` 由 `OcrResultSqsProcessor#handleResult()` 在 task 内所有 OcrResult 收到后调用：

| 文件聚合结果 | task 状态推进 | 后续动作 |
|-------------|--------------|---------|
| 全部 `has_extractable_data=false` | `status=NO_DATA_BYPASS` → AFTER_COMMIT `syncAllFiles()` → `status=COMPLETED` | 跳过 MEMORY_LEARN（无需学习）；前端轮询发现状态变化弹"未提取到财务数据"提示 |
| 全部 true | 走正常 5a/5b/5c 流程 | — |
| 混合 | 仅有数据文件参与 5a 摘要 + 5b 冲突 + 5c commit | 无数据文件在 5c AFTER_COMMIT 时一并 sync 到 Imported Statements |

**新增枚举值**: `DocParseStatus.NO_DATA_BYPASS` —— 区别于 `FAILED`（处理失败）。Sweeper 不需要扫描该状态（瞬态）。

---

### 5.8 边界用例 — Steps Navigation 变更检测

> **业务规则** → [requirement-analysis §4.13](./requirement-analysis.md#413-edge-case--steps-navigation2026-05-06-新增)；**端点** → [api-doc.md #20](./api-doc.md#20-tasksidnavigate-back-post)。本节仅说明 Java 端状态机决策。

**核心契约**: Previous 在所有步骤都可用；回退后**未修改**则保留下游结果不重跑；**有修改**则重跑下游 + 清空旧 conflict resolutions。判定靠 `mapping_snapshot_hash` 对比。

**`NavigationService.handleNavigateBack` 实现层流程**:

1. 计算 `computeSnapshotHash(taskId)`：SHA-256(JSON(sorted_rows + sorted_mappings))；关键字段 `row.value` / `row.account_label` / `row.reporting_period` / `mapping.lg_category`
2. 对比 `ai_ocr_task.mapping_snapshot_hash`：
   - **相等** → `mappingChanged=false`，前端无延迟前进（保留下游结果）
   - **不等** → `mappingChanged=true`，执行：
     - 清空 `ai_ocr_conflict_record.resolution_action`（重置为 NULL）
     - 推进 `task.status=REVIEWING`（即使是从 CONFLICT_RESOLUTION 回来）
     - 清空 `ai_ocr_task.summary_cache`（强制 5a 重新聚合）
     - 更新 `mapping_snapshot_hash` + `mapping_changed_at`
     - 入队 `ocr-extract-queue`（`mode=REMAP_ONLY`，参见 §4.1）
3. 返回 `{ mappingChanged, clearedConflictCount, message }`

**Conflict 清空策略**: 仅清空 `resolution_action`；`ai_ocr_conflict_note` 不删除（用户历史 thread 是审计记录的一部分，下次进入 5b 仍可见）。

---

> 注：旧 §5.6.1-5.6.3 / §5.7 / §5.8 / §5.9 / §5.10 的详细 Java Controller / Service 代码示例已删除，规格请查 [api-doc.md](./api-doc.md)（端点 #11-#20）+ [system-architecture.md](./system-architecture.md)（业务规则）。本文档保留以上简化版本（§5.6-§5.8）即可。

---

### 5.11 后端基础设施（2026-05-06 技术 Story）

> 需求来源：[requirement-analysis §4.14](./requirement-analysis.md#414-backend-infrastructure--framework-setup2026-05-06-新增--技术-story)

本 Story 是其他 Story 的前置依赖，多数已在原 §1-§4 中覆盖。本节仅追加**Liang Chunru 验收清单**层面的明确说明：

| 基础能力 | 现状 | 对应章节 |
|---------|------|---------|
| S3 安全存储 + presigned 直传 | 已设计 | §2.1 / §5.4.2 / §5.4.3 / §5.4.4 |
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

### 5.12 辅助端点实现层（接口对接说明）

> **端点 URL / DTO** → [api-doc.md](./api-doc.md)（端点 #5 / #8 / #16-17 / #21-22 / #23-25）。本节仅说明 Java 端实现层副作用与状态推进。

| 端点（api-doc.md 编号）| 实现层关键决策 |
|---------------------|---------------|
| `/tasks/{id}/history` (#5) | `historyService.buildVersionChain` 递归 `parent_task_id` 链直到 `parent_task_id IS NULL`；按 `revision_number` 升序返回；仅返回 status ∈ {COMMITTED, SUPERSEDED, COMPLETED, MEMORY_LEARN_*} 的版本（DRAFT/FAILED/EXPIRED 不暴露） |
| `/upload/abort` (#8) | (1) 校验 `task.status ∈ {DRAFT, UPLOADING, UPLOAD_COMPLETE}`（已 PROCESSING 不允许）；(2) 每个 fileId 执行 `s3:DeleteObject(s3Key)` + `ai_ocr_file.deleted=true` + `status=FILE_FAILED(error="USER_ABORTED")`；(3) 写 state_log `UPLOAD_ABORTED`；(4) 不入队 `ocr-extract-queue`；若文件已入队但 Python 未消费，Python 端在拉取后会发现 `deleted=true` 直接 ack 丢弃（详见 python-design.md 幂等保护）|
| `/conflicts/{id}/notes` (#16-#17) | `noteService.append`：校验 `conflictId` 归属 `taskId`、`taskId` 归属 `jwtCompanyId`；写 `ai_ocr_conflict_note(conflict_id, content, parent_note_id, author_id, auto_generated=false)`；**不变更 task.status**（note 是辅助记录，不影响主流程） |
| `/similarity-hints/{hintId}` (#22) | `hintService.applyDecision`：(1) JWT scope `hint.companyId == jwtCompanyId`；(2) 校验 `hint.user_decision IS NULL`（已决策不允许覆盖）；(3) UPDATE `ai_ocr_similarity_hint SET user_decision=?, decided_at=NOW(), decided_by=?`；(4) 若 `decision=MERGED` 且 `hint.merge_strategy` 允许 → 联动更新 `ai_ocr_mapping_result.lg_category` 为 `hint.suggested_category`；(5) 写 state_log `SIMILARITY_HINT_DECIDED` |
| `/memory-learn/retry` (#25) | `memoryLearnService.retry`：(1) FOR UPDATE 锁 task；校验 `status=MEMORY_LEARN_FAILED`；(2) 查 `ai_ocr_memory_learn_log` 取最大 `attempt_number`，必须 `<3`；(3) 推进 `status=MEMORY_LEARN_PENDING`；(4) **不重写 fi_***（财务数据已 committed）；(5) 重发 `ocr-memory-learn-queue` 消息（`attemptNumber+1`）；(6) 写 state_log `MEMORY_LEARN_MANUAL_RETRY` |

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

**S3 / SQS IAM 权限划分**:

| Role | S3 权限 | SQS 权限 |
|------|--------|---------|
| Java IAM Role | `s3:PutObject` + `s3:GetObject` → `ocr-uploads/*` | `sqs:SendMessage` → `ocr-extract-queue` / `ocr-similarity-check-queue` / `ocr-memory-learn-queue`；`sqs:Receive/Delete` → `ocr-result-queue` |
| Python IAM Role | `s3:GetObject` → `ocr-uploads/*`（只读） | `sqs:Receive/Delete` → `ocr-extract-queue` / `ocr-similarity-check-queue` / `ocr-memory-learn-queue`；`sqs:SendMessage` → `ocr-result-queue` |

**数据库角色隔离**:

| 角色 | 权限 |
|------|------|
| `java_app` | 完全访问 Java 拥有的表 + `SELECT` 权限访问 Python 表 |
| `python_worker` | 完全访问 Python 拥有的表 + `SELECT` 权限访问 `ai_ocr_task`、`ai_ocr_file`（查状态） + 零权限访问 `fi_*` 表 |

---

## 7. 变更日志

| 日期 | 摘要 |
|------|------|
| 2026-04-16 | 首版：DDD 模块、SQS 集成、上传/审核/提交流程 |
| 2026-04-19 | Verify Data Summary 两阶段、冲突 Note thread、Cancel 移除 |
| 2026-04-20 | S3 Presigned URL 直传、Task 修订、相似度提示、记忆学习进度 |
| 2026-05-06 | Asana §4.9-4.14：Step 5 拆分为 5a/5b/5c，新增 4 个 Controller + 4 个 Service + 4 个字段 |
| 2026-05-06 | 多 agent 头脑风暴清理：删 OcrRemap 生产者（合并 mode 字段）、删 /notifications/retry 端点、删 ai_ocr_notification + extraction_skip_log 引用、新增 OcrSimilarityCheck 生产者 |
| 2026-05-06 | 文档简化：§0 接口清单抽取到独立 [api-doc.md](./api-doc.md)、§5.4.2 已删除通知重试章节移除、§5.5 DTO 定义指向 api-doc |
| 2026-04-20（v1.6）| **聚焦"文件上传"**：§0.5 新增文档定位说明；删除全部 Java/JSON 实例代码块（接口签名归 api-doc.md，业务规则归 system-architecture.md / python-design.md）；§2 重写为"文件上传实现层"；§5.4-§5.10 commit/conflict/navigation 章节折叠为接口对接说明；§5.12 辅助端点改为表格 |

> 完整变更详情见 [api-doc.md](./api-doc.md) 与 [system-architecture.md §16](./system-architecture.md#16-变更日志)。
