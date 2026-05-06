# OCR Agent Java 端设计 (CIOaas-api)

> **技术栈**: Java 17 + Spring Boot 3 + Spring Cloud Gateway + AWS S3/SQS
> **关联文档**: [设计理念](./design-philosophy.md) · [需求分析](./requirement-analysis.md) · [系统架构](./system-architecture.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [接口文档](./api-doc.md) · [代码示例](./code-examples.md) · [用户输入需求清单](../user-input-requirements.md)

---

## 目录

- [0.5 文档定位说明（v2 收敛）](#05-文档定位说明v2-收敛)
- [0. 接口清单（v2 — 25 → 6）](#0-接口清单v2--25--6)
- [1. 模块结构](#1-模块结构)
  - [1.1 包结构（v2 精简）](#11-包结构v2-精简)
  - [1.2 与现有模块的集成点](#12-与现有模块的集成点)
- [2. 文件上传实现层（端点 1-3）](#2-文件上传实现层端点-1-3)
  - [2.1 端点 1：`POST /tasks/upload-init`（一站式初始化 + 预关联公司文件表）](#21-端点-1post-tasksupload-init一站式初始化--预关联公司文件表)
  - [2.2 端点 2：`POST /tasks/{id}/upload-complete`（单文件完成）](#22-端点-2post-tasksidupload-complete单文件完成)
  - [2.3 端点 3：`POST /tasks/{id}/start-processing`（新增 — 用户点 Next 触发批量入队）](#23-端点-3post-tasksidstart-processing新增--用户点-next-触发批量入队)
  - [2.4 上传错误码](#24-上传错误码)
  - [2.5 Presigned GET URL（端点 6 — 文件查看辅助）](#25-presigned-get-url端点-6--文件查看辅助)
- [3. 数据表设计（业务语义）](#3-数据表设计业务语义)
  - [3.1 Java 拥有的表（v2 概览）](#31-java-拥有的表v2-概览)
  - [3.2 关键设计决策（v2 保留）](#32-关键设计决策v2-保留)
- [4. SQS 集成（实现层）](#4-sqs-集成实现层)
  - [4.1 OcrExtractSqsProducer 设计要点](#41-ocrextractsqsproducer-设计要点)
  - [4.2 OcrResultSqsProcessor 设计要点](#42-ocrresultsqsprocessor-设计要点)
  - [4.3 OcrSimilarityCheckSqsProducer](#43-ocrsimilaritychecksqsproducer)
  - [4.4 OcrMemoryLearnSqsProducer](#44-ocrmemorylearnsqsproducer)
  - [4.5 队列配置](#45-队列配置)
  - [4.6 DocParseTaskSweeper（v2 收窄）](#46-docparsetasksweeperv2-收窄)
  - [4.7 Java/Python 数据库物理部署](#47-javapython-数据库物理部署)
- [5. Commit 流程实现层（端点 4 — 核心职责）](#5-commit-流程实现层端点-4--核心职责)
  - [5.1 v2 Commit 端点重大变更](#51-v2-commit-端点重大变更)
  - [5.2 两阶段事务模型](#52-两阶段事务模型)
  - [5.3 关键实现层约束](#53-关键实现层约束)
  - [5.4 Commit 失败的恢复路径（Q7 方案 B）](#54-commit-失败的恢复路径q7-方案-b)
  - [5.5 v2 ImportedStatementsService 职责（预占位 → 最终化）](#55-v2-importedstatementsservice-职责预占位--最终化)
  - [5.6 边界用例 — 无可提取数据（NO_DATA_BYPASS）](#56-边界用例--无可提取数据no_data_bypass)
- [6. 任务修订实现层（端点 5）](#6-任务修订实现层端点-5)
- [7. 安全要求](#7-安全要求)
  - [7.1 移除 FileController @AnonymousAccess](#71-移除-filecontroller-anonymousaccess)
  - [7.2 上传校验 MIME + magic bytes](#72-上传校验-mime--magic-bytes)
  - [7.3 SQS 消息 HMAC 签名](#73-sqs-消息-hmac-签名)
  - [7.4 SQS 消费时跨公司归属校验](#74-sqs-消费时跨公司归属校验)
  - [7.5 S3 Bucket CORS（生产必需）](#75-s3-bucket-cors生产必需)
  - [7.6 S3 Presigned URL 安全增强（5 项约束）](#76-s3-presigned-url-安全增强5-项约束)
  - [7.7 IAM 角色与数据库角色](#77-iam-角色与数据库角色)
  - [7.8 v2 Python 端点的 JWT 共享](#78-v2-python-端点的-jwt-共享)

---

## 0.5 文档定位说明（v2 收敛）

本文档**主要描述 Java 端"文件上传 + 最终提交"两条核心路径的实现层细节**：

- 文件上传：S3 presigned URL 直传、magic bytes 校验、上传完成、批量入队
- 最终提交：fi_* 写入事务、AFTER_COMMIT 触发记忆学习 SQS、Imported Statements 同步、Benchmark 跳转

其他业务逻辑（综合状态查询 / 用户编辑 / 冲突验证 / 单冲突解决 / 相似度决策 / 记忆学习状态 / 任务历史链 / mapping 变更检测）**全部由 Python 主导**，前端直接调用 Python 的 4 个端点 — 详见 [api-doc.md §1.1.3](./api-doc.md#113-python-端用户面向查询--编辑--验证--2026-05-06-v2-新边界) 与 [python-design.md](./python-design.md)。

本文档不再描述上述被迁移的端点；保留章节聚焦：
- 接口职责定义 → [api-doc.md](./api-doc.md)（Java 端 6 个端点 + 3 个 SQS 生产者 + 1 个回传消费者）
- 业务规则与状态契约 → [system-architecture.md](./system-architecture.md)（4 步流程、状态机、跨域权限）

---

## 0. 接口清单（v2 — 25 → 6）

Java 端对外接口的**完整清单 + 字段定义**已抽取到独立接口文档：

📘 **[OCR Agent 接口文档](./api-doc.md)** — 先看 §1 总览（一行一个接口），需要细节时跳转 §2-§3。

| 接口类别 | 数量 | 索引位置 |
|---------|:---:|---------|
| REST 端点（用户面向：上传 + 提交）| 5 | [api-doc.md §1.1.1](./api-doc.md#111-java-端用户面向文件上传--最终提交) |
| REST 端点（辅助：文件查看）| 1 | [api-doc.md §1.1.2](./api-doc.md#112-java-端辅助) |
| SQS 生产者（Java → Python）| 3 | [api-doc.md §1.2.1](./api-doc.md#121-java--python出口队列) |
| SQS 消费者 handler（Python → Java，按 messageType 多路复用）| 4 | [api-doc.md §1.2.2](./api-doc.md#122-python--java回传队列按-messagetype-多路复用) |

**v2 端点清单（Java 端 6 个）**：

| # | URL | 方法 | 一句话职责 |
|---:|-----|:---:|-----------|
| 1 | `/tasks/upload-init` | POST | 一站式：创建 task + presigned PUT URL + **预关联公司文件表占位行** |
| 2 | `/tasks/{id}/upload-complete` | POST | 单文件上传完成（HeadObject + magic bytes 校验，写 `ai_ocr_file`） |
| 3 | `/tasks/{id}/start-processing` | POST | **新增**：用户点 Next 触发批量入队所有 UPLOADED 文件到 `ocr-extract-queue` |
| 4 | `/tasks/{id}/commit` | POST | 写 fi_* + AFTER_COMMIT 触发记忆 SQS + 最终化 Imported Statements + 返回 Benchmark URL |
| 5 | `/tasks/{id}/revise` | POST | 任务修订：基于 COMPLETED task 创建新批次（copy-on-write） |
| 6 | `/files/{fileId}/download-url` | POST | ReviewPage 渲染 PDF/Excel 时申请 5min S3 presigned GET URL |

**v2 删除的端点（16 个，功能迁移到 Python 或合并）**：

| 旧端点 | 去向 |
|-------|------|
| `POST /tasks` 创建空任务 | 合并入 `/tasks/upload-init` |
| `GET /tasks/{id}/status` | 迁移到 Python `/ocr/tasks/{id}/state` |
| `GET /tasks/{id}/result` | 迁移到 Python `/state` |
| `GET /tasks/{id}/history` | 内嵌 Python `/state` 响应 |
| `POST /upload/abort` | 简化删除（用户放弃直接退出页面，Sweeper 24h 清 DRAFT） |
| `PATCH /tasks/{id}/review` | 迁移到 Python `/ocr/tasks/{id}/review` |
| `GET /tasks/{id}/mapping-summary` | 内嵌 Python `/state.mappingSummary` |
| `POST /tasks/{id}/verify/start` | 迁移到 Python `/ocr/tasks/{id}/verify` |
| `GET /tasks/{id}/verify/progress` | 内嵌 Python `/state.verifyState` |
| `GET /tasks/{id}/conflicts` | 内嵌 Python `/state.verifyState.conflicts` |
| `POST /tasks/{id}/conflicts/{id}/resolve` | 迁移到 Python `/ocr/conflicts/{id}/resolve` |
| `GET/POST /tasks/{id}/notes` | 合并到 Python `/review.conflictNotes` 字段 |
| `GET /tasks/{id}/commit/result` | 合并到 `/commit` 响应（含 `benchmarkRedirectUrl`） |
| `POST /tasks/{id}/navigate-back` | **功能内嵌**到 Python `/review` 端点的 mapping 变更检测 |
| `PATCH /similarity-hints/{hintId}` | 合并到 Python `/review.similarityDecisions` 字段 |
| `GET /memory-learn` / `/history` / `POST /retry` | 迁移到 Python `/state.memoryLearn` |

---

## 1. 模块结构

### 1.1 包结构（v2 精简）

在现有 DDD 结构下保留 `docparse` 域（与 `fi/`、`quickbooks/`、`storage/` 同级），4 层 DDD 架构。v2 大幅精简：删除 8 个 Controller / 7 个 Service。

```
com.gstdev.cioaas.web.docparse/
├── interfaces/                    ← 入口层（Interfaces Layer）
│   ├── controller/
│   │   ├── UploadController.java          # /tasks/upload-init + /tasks/{id}/upload-complete + /tasks/{id}/start-processing
│   │   ├── CommitController.java          # /tasks/{id}/commit（写 fi_* + 触发记忆 SQS + 返回 Benchmark URL）
│   │   ├── ReviseController.java          # /tasks/{id}/revise（任务修订 copy-on-write）
│   │   └── FileViewController.java        # /files/{fileId}/download-url（presigned GET）
│   └── vo/
│       ├── request/
│       │   ├── UploadInitReqVo.java                  # files[]: {filename, fileSize, contentType, sha256}
│       │   ├── UploadCompleteReqVo.java              # fileId, etag, actualSize
│       │   ├── StartProcessingReqVo.java             # （空 body 或 force flag）
│       │   ├── CommitReqVo.java                      # confirmFinal: bool（hard gate 二次确认）
│       │   └── ReviseReqVo.java                      # reason: str
│       └── response/
│           ├── UploadInitRespVo.java                 # taskId, uploads[]: {fileId, presignedUrl, expiresAt}, companyDocFolderId
│           ├── UploadCompleteRespVo.java             # status, error?
│           ├── StartProcessingRespVo.java            # queuedCount, skippedCount
│           ├── CommitRespVo.java                     # writtenAccounts, writtenPeriods[], importedStatementsFolderId, benchmarkRedirectUrl
│           ├── ReviseRespVo.java                     # newTaskId
│           └── FileDownloadUrlRespVo.java            # url, expiresAt
│
├── application/                   ← 应用层（Application Layer）
│   ├── service/
│   │   ├── UploadInitService.java         # 创建 task + presigned URL + 预关联公司文件表
│   │   ├── UploadCompleteService.java     # HeadObject + magic bytes 校验
│   │   ├── StartProcessingService.java    # 批量扫描 UPLOADED 文件 + 入队
│   │   ├── CommitService.java             # 两阶段 commit：事务写 fi_* + AFTER_COMMIT 触发记忆 SQS / Imported Statements / Benchmark URL
│   │   ├── ReviseService.java             # copy-on-write 任务修订
│   │   ├── ImportedStatementsService.java # 公司文件表预占位 + 最终化（设可见）
│   │   ├── ProformaForecastService.java   # Proforma appendVersion（commit 流程依赖）
│   │   ├── ClosedMonthMailService.java    # AFTER_COMMIT 闭月邮件通知
│   │   └── BenchmarkRedirectService.java  # 构建 commit 响应中的 Benchmark 跳转 URL
│   └── dto/
│       ├── DocParseTaskDto.java
│       ├── DocParseFileDto.java
│       ├── OcrExtractMessageDto.java          # ocr-extract-queue 消息体（含 mode 字段）
│       ├── OcrSimilarityCheckMessageDto.java  # ocr-similarity-check-queue 消息体
│       ├── OcrMemoryLearnMessageDto.java      # ocr-memory-learn-queue 消息体
│       └── OcrResultMessageDto.java           # ocr-result-queue 消息体（4 种 messageType 的 base）
│
├── domain/                        ← 领域层（Domain Layer）
│   ├── entity/
│   │   ├── DocParseTask.java               # JPA Entity: ai_ocr_task
│   │   └── DocParseFile.java               # JPA Entity: ai_ocr_file（含 file_hash 重名校验）
│   ├── repository/
│   │   ├── DocParseTaskRepository.java
│   │   └── DocParseFileRepository.java
│   └── enums/
│       ├── DocParseStatus.java             # Task 状态枚举（见 §3）
│       ├── DocParseFileStatus.java         # PENDING / UPLOADING / UPLOADED / QUEUED / PROCESSING / REVIEW_READY / FILE_COMMITTED / FILE_FAILED
│       ├── DocParseFileType.java           # PDF / EXCEL / CSV / IMAGE
│       └── DocParseUploadError.java        # 7 种上传错误（§2.4）
│
└── infrastructure/                ← 基础设施层（Infrastructure Layer）
    ├── processor/
    │   ├── OcrExtractSqsProducer.java          # 发送 ocr-extract-queue（mode 字段 FULL_EXTRACT / REMAP_ONLY）
    │   ├── OcrSimilarityCheckSqsProducer.java  # 发送 ocr-similarity-check-queue（task 内所有文件 REVIEW_READY 后）
    │   ├── OcrMemoryLearnSqsProducer.java      # 发送 ocr-memory-learn-queue（commit AFTER_COMMIT）
    │   └── OcrResultSqsProcessor.java          # 消费 ocr-result-queue，按 messageType 多路分发到 4 个 handler
    ├── client/
    │   └── S3PresignedUrlClient.java       # 生成 presigned PUT/GET URL，封装 AWS SDK
    ├── scheduler/
    │   └── DocParseTaskSweeper.java        # @Scheduled 每 2min 扫描僵尸任务（v2 范围收窄，见 §4.6）
    └── config/
        └── DocParseProperties.java         # 模块配置
```

**为什么大幅精简 Controller**：v2 边界变更后，前端**步骤 3-6 全部直接调 Python**（综合状态查询 / 编辑 / 冲突验证 / 单冲突解决）；Java 端只剩"上传 + 提交"两条核心路径，因此原先的 `MappingSummaryController` / `ConflictResolutionController` / `ConflictNoteController` / `NavigationController` / `SimilarityHintController` / `MemoryLearnController` / `ReviewController` / `DocParseQueryController` 全部删除。

### 1.2 与现有模块的集成点

| 集成点 | 文件 | 操作 |
|--------|------|------|
| 文件上传 | `storage/service/FileServiceImpl.java` | Presigned URL 流程由 `S3PresignedUrlClient` 封装，与现有 FileService 并存 |
| Imported Statements | `documents/service/CompanyDocService.java` | `ImportedStatementsService` 调用 CompanyDocService 创建/最终化文件夹（v2 新增预占位逻辑） |
| SQS 队列注册 | `sqs/enums/InitSqsQueueEnum.java` | 注册 `OcrExtractQueue` / `OcrSimilarityCheckQueue` / `OcrMemoryLearnQueue` / `OcrResultQueue` |
| SQS 消息类型 | `sqs/enums/SqsMessageType.java` | 注册 `OcrExtract` / `OcrSimilarityCheck` / `OcrMemoryLearn` / `OcrResult` / `OcrProgress` / `OcrSimilarityCheckResult` / `OcrMemoryLearnProgress` |
| SQS Listener | `sqs/listener/SQSMessageListener.java` | 新增 `onOcrResultQueue()` 方法（@SqsListener 消费 ocr-result-queue） |
| 事务边界 | Spring `@TransactionalEventListener` | Commit / Revise 等涉及发 SQS 必须 `phase = AFTER_COMMIT`（见 §5.3） |
| 参考实现模板 | `quickbooks/infrastructure/processor/QuickbooksSqsProcessor.java` | Producer 不 implements MessageProcessor；Consumer 必须 implements 并注册 |

---

## 2. 文件上传实现层（端点 1-3）

> **本章是 Java 端的核心职责章节之一**。所有端点 URL / DTO / 响应字段定义在 [api-doc.md §2.1-§2.3](./api-doc.md#java-端)；本节聚焦实现层决策。

### 2.1 端点 1：`POST /tasks/upload-init`（一站式初始化 + 预关联公司文件表）

参见 [api-doc.md #1](./api-doc.md#1-tasksupload-init-post)。

**实现层时序**（Controller `UploadController#initUpload` → `UploadInitService`）：

```
Java 处理（@Transactional）:
  ① JWT + company 归属校验
  ② 创建 ai_ocr_task（status=DRAFT, company_id, uploaded_by, expires_at=NOW()+24h）
  ③ 对每个 file（按文件逐项进行，部分失败不阻断其余）：
     ├─ 文件大小校验（单文件 ≤20MB / 批次累计 ≤100MB）
     ├─ 扩展名 + Content-Type 白名单（参见 §6.2）
     ├─ SHA-256 hash 重名查询（UNIQUE 约束 (company_id, file_hash) WHERE deleted=false AND status!='FILE_FAILED'）
     ├─ 合法 → 建 ai_ocr_file（status=PENDING） + 生成 S3 presigned PUT URL（15 min）
     └─ 非法 → 在 uploads[] 数组按位返回 error 项
  ④ 调 ImportedStatementsService.createPlaceholder(taskId, companyId)
     └─ 在公司文件表创建 "Imported Statements/{taskUuid}/" 占位文件夹（visible=false）
        + 为每个合法文件预创建占位行（s3_key 临时 placeholder, status=UPLOADING）
  ⑤ 写 ai_ocr_task_state_log（event_type=UPLOAD_INITIATED, payload={fileCount, totalSize}）
  ⑥ 返回 {taskId, uploads[], companyDocFolderId}
```

**S3 Key 命名规范**: `ocr-uploads/{companyId}/{taskId}/{fileId}/{hash}.ext` —— 路径含 companyId 保证 IAM 策略可按 prefix 隔离权限。

**预关联公司文件表的设计意图**：
- 用户在上传期间已能在 Documents 视图看到"正在导入的批次"占位（visible=false 时仅 owner 可见）
- 文件最终提交（`/commit` 成功）才把 `visible=true` 设为可见 → "Imported Statements" 是用户真正归档的位置
- 占位行在 `/upload/abort` 或 task EXPIRED 时由 Sweeper 清除（v2 简化：不再有显式 abort 端点，靠 24h Sweeper）

### 2.2 端点 2：`POST /tasks/{id}/upload-complete`（单文件完成）

参见 [api-doc.md #2](./api-doc.md#2-tasksidupload-complete-post)。

**实现层时序**（`UploadController#completeUpload` → `UploadCompleteService`）：

```
Java 处理（@Transactional）:
  ① JWT + task.company_id 归属校验
  ② ⚠️ 安全：从 ai_ocr_file 表查 s3Key（不信任前端传入，参见 §5.4 安全约束）
  ③ s3:HeadObject 验证对象存在 + ETag/actualSize 一致
  ④ 读取首 2KB 做 MIME + magic bytes 双重校验（白名单见 §6.2）
  ⑤ 通过 → ai_ocr_file.status=UPLOADED + 写 state_log UPLOAD_S3_PERSISTED
     → ImportedStatementsService.bindActualS3Key(fileId, s3Key)（更新占位行 s3_key）
  ⑥ 失败 → s3:DeleteObject 清理 + ai_ocr_file.status=FILE_FAILED + state_log UPLOAD_REJECTED + 错误码（§2.4）
  ⑦ ⚠️ 关键变更（v2）：不入队 ocr-extract-queue
     入队动作由 §2.3 /start-processing 端点统一触发
```

**为什么必须做 magic bytes 校验**: 前端可能上传一个改了扩展名的恶意文件（如 `.exe` 改为 `.pdf`）。仅看扩展名/Content-Type 不安全，必须读首 2KB 验证 magic bytes。

### 2.3 端点 3：`POST /tasks/{id}/start-processing`（新增 — 用户点 Next 触发批量入队）

参见 [api-doc.md #3](./api-doc.md#3-tasksidstart-processing-post)。这是 v2 新增端点，替代之前每个文件 complete 后自动入队的隐式行为。

**为什么需要这个端点**：
- v1 行为：每个文件 complete 后立即入队 → 用户还没确认就已经在跑解析（浪费 Python 资源、不可撤回）
- v2 行为：用户在前端逐个上传完成后，在上传页面点 "Next" 才统一触发 → 更明确的用户控制权 + 自然的"批次"边界
- 与前端"4 步流程"对齐：Step 1 全部上传完毕 → Step 2 解析

**实现层时序**（`UploadController#startProcessing` → `StartProcessingService`）：

```
Java 处理（@Transactional + FOR UPDATE 锁）:
  ① JWT + task.company_id 归属校验
  ② SELECT ... FOR UPDATE 锁 ai_ocr_task 行（防止用户重复点 Next 并发触发）
  ③ CAS 校验：task.status IN (DRAFT, UPLOAD_COMPLETE) → PROCESSING
       └─ 不在此范围 → 抛 INVALID_STATUS_FOR_PROCESSING（已在跑或已完成）
  ④ 批量扫描：SELECT * FROM ai_ocr_file WHERE task_id=? AND status='UPLOADED' AND deleted=false
  ⑤ 对每个 UPLOADED 文件：
     ├─ ai_ocr_file.status=QUEUED
     ├─ OcrExtractSqsProducer.send(taskId, fileId, mode=FULL_EXTRACT)（每文件 1 条消息）
     └─ 写 state_log EXTRACT_QUEUED
  ⑥ 统计：queuedCount = ⑤ 的数量；skippedCount = 非 UPLOADED 的文件数（FILE_FAILED 等）
  ⑦ 写 state_log START_PROCESSING（payload={queuedCount, skippedCount}）
  ⑧ 返回 {queuedCount, skippedCount}
```

**事务边界关键**：
- SQS 入队**在事务内**（不 AFTER_COMMIT）—— 因为本事务无回滚风险，仅更新 file.status；且我们希望"看到 file.status=QUEUED 时一定已经入队"
- 如果 SQS 发送失败 → 整个事务回滚，前端收到 500 + 重试（task.status 自动恢复）

**幂等保护**：
- CAS 推进 task.status 防止用户连点 Next 重复入队
- 即使重复入队（极端情况），Python 端 extract_consumer 也通过 ai_ocr_file.status=PROCESSING/REVIEW_READY 判定为重复消息丢弃

### 2.4 上传错误码

| 错误码 | 触发场景 | HTTP 状态 |
|-------|---------|----------|
| `FILE_TOO_LARGE` | 单文件超 20MB | 400 |
| `BATCH_TOO_LARGE` | 批次累计超 100MB | 400 |
| `UNSUPPORTED_TYPE` | 扩展名/Content-Type 不在白名单 | 400 |
| `MAGIC_BYTES_MISMATCH` | 扩展名与文件头不一致 | 400 |
| `DUPLICATE_NAME` | 同 company + 同 hash 已存在活跃记录 | 409 |
| `S3_OBJECT_NOT_FOUND` | `/upload-complete` 但 HeadObject 失败 | 404 |
| `INVALID_HASH_FORMAT` | hash 不符合 `^[a-f0-9]{64}$` | 400 |
| `INVALID_STATUS_FOR_PROCESSING` | `/start-processing` 时 task.status 非法 | 409 |

错误信息均由 Java 生成（R-2.2 约束：用户可见错误必须由 Java 转换；Python 不直接面向用户）。

### 2.5 Presigned GET URL（端点 6 — 文件查看辅助）

ReviewPage 加载 PDF/Excel 时，前端向 `POST /files/{fileId}/download-url`（参见 [api-doc.md #6](./api-doc.md#6-filesfileiddownload-url-post)）请求临时 URL。

**实现层决策**:
- URL 生存期 **5 分钟**（不是 15 分钟，参见 §5.4 安全收紧）
- 生成前必须验证 JWT + company 归属 + `ai_ocr_file.deleted=false` + `ai_ocr_file.status NOT IN (FILE_FAILED, PENDING)`
- 不附加 `Content-Disposition: attachment` —— 让浏览器直接预览

前端用此 URL：PDF/图片直接 `<iframe>` 或 `<img>` 渲染；Excel 由前端用 SheetJS 从该 URL 拉取后解析。

---

## 3. 数据表设计（业务语义）

> **DDL 权威定义**：所有表结构、索引、约束、权限 GRANT 语句的**唯一权威定义**在 [database-schema.md](./database-schema.md)。本节仅说明 Java 端表的**业务语义**与设计意图。

### 3.1 Java 拥有的表（v2 概览）

| 表 | 用途 | DDL 引用 |
|----|------|---------|
| `ai_ocr_task` | Task 生命周期（批次级状态 + 版本化字段 + summary_cache + mapping_snapshot_hash） | [§2.1](./database-schema.md#21-ai_ocr_task) |
| `ai_ocr_file` | 单个文件的上传 + 处理状态（12 子阶段 + stage_detail JSONB + has_extractable_data） | [§2.2](./database-schema.md#22-ai_ocr_file) |
| `ai_ocr_task_state_log` | **总状态日志表**（覆盖 4 步流程所有状态变更，落地 R-3.4） | [§2.9](./database-schema.md#29-ai_ocr_task_state_log) |
| `ai_ocr_conflict_note` | 冲突解决 note（thread 支持，Java + Python 共写，详见 §5.5） | [§2.4](./database-schema.md#24-ai_ocr_conflict_note) |
| `ai_ocr_memory_learn_log` | 记忆学习审计（Python 跨域 INSERT） | [§2.5](./database-schema.md#25-ai_ocr_memory_learn_log) |
| `ai_ocr_commit_audit` | fi_* 写入审计（written/overwritten/skipped） | [§2.6](./database-schema.md#26-ai_ocr_commit_audit) |
| `ai_ocr_erasure_log` | GDPR 擦除审计 | [§2.7](./database-schema.md#27-ai_ocr_erasure_log) |
| `ai_ocr_similarity_hint` | 相似度检测结果（Python 跨域 INSERT；Python 也可 UPDATE detection 字段） | [§2.8](./database-schema.md#28-ai_ocr_similarity_hint) |

### 3.2 关键设计决策（v2 保留）

#### Task 版本化
`parent_task_id` / `revision_number` / `revision_reason` / `superseded_by` 支持"基于历史 task 修订"场景。原任务在修订版 Commit 成功后自动置为 `SUPERSEDED`。**并发防护**：`UNIQUE (parent_task_id, revision_number) WHERE parent_task_id IS NOT NULL` 约束防止两个用户同时创建相同版本号。

#### File 处理阶段
12 个子状态精确描述 Python 处理进度（见 [api-doc.md MSG-1 OcrProgress](./api-doc.md#msg-1-ocrprogress)）。`stage_detail JSONB` 由 Python 透传，前端通过 Python 的 `/state` 端点直接读取并渲染（v2 边界变更 — Java 不再做查询中转）。

#### 重名文件校验的唯一约束
`UNIQUE (company_id, file_hash) WHERE deleted = false AND status != 'FILE_FAILED'` —— 只对"活跃"记录生效。`FILE_FAILED` 状态的文件允许用户重新上传同名文件。

#### v2 简化：通知机制
**不主动推送邮件/push**，用户通过 LG Dashboard "待处理任务" 列表自行发现。所有事件统一写入 `ai_ocr_task_state_log`。

#### 公司文件表预占位（v2 新增）
`/tasks/upload-init` 创建 task 时同步在 Documents 服务的 "Imported Statements" 文件夹下创建占位条目（`visible=false`），用户在上传过程中即可在 Documents 视图看到"进行中"批次。`/commit` 成功后由 `ImportedStatementsService.finalize()` 把 `visible=true` 标记为可见。详见 §5 / §6。

#### 跨域 INSERT 例外（v2 扩展）
Python 在 v2 后获得对 4 张 Java 拥有的表的写权限：

| 表 | Python 权限 | 用途 |
|----|------------|------|
| `ai_ocr_memory_learn_log` | INSERT | 记忆学习审计 |
| `ai_ocr_similarity_hint` | INSERT + UPDATE（仅 detection 字段） | 相似度检测结果 |
| `ai_ocr_task_state_log` | INSERT | Python 面向用户端点写状态变更日志 |
| `ai_ocr_conflict_record` | UPDATE（resolution 字段） | `/ocr/conflicts/{id}/resolve` 更新解决决定 |
| `ai_ocr_conflict_note` | INSERT | 解决冲突时自动追加 note |

GRANT 语句详见 [database-schema.md §4](./database-schema.md#4-数据库角色与权限)。

---

## 4. SQS 集成（实现层）

> **接口契约**: SQS 队列名 / messageType / 消息字段定义参见 [api-doc.md §3 SQS 接口详情](./api-doc.md#3-sqs-接口详情)。本节聚焦 Java 端实现层决策。

### 4.1 OcrExtractSqsProducer 设计要点

参见 [api-doc.md SQS-1](./api-doc.md#sqs-1-ocr-extract-queue)。

| 实现层关注点 | 决策 |
|------------|------|
| 粒度 | 一条消息对应一个文件（不是一个 task）—— 独立重试、天然并发、部分失败隔离 |
| `mode` 字段路由 | `FULL_EXTRACT`（首次上传，由 `/start-processing` 触发）/ `REMAP_ONLY`（mapping 变更，**由 Python `/review` 端点检测后内部入队**） |
| 触发时机（FULL_EXTRACT） | `/start-processing` 端点同一事务内发送 |
| 触发时机（REMAP_ONLY） | **v2 变更**：Python 是 producer。Python 共享 SQS API（`boto3.client('sqs').send_message`），mode 字段标识 `REMAP_ONLY` |
| HMAC-SHA256 签名 | 见 §6.3 |

### 4.2 OcrResultSqsProcessor 设计要点

`OcrResultSqsProcessor` implements `MessageProcessor`，按 `messageType` 多路分发到 4 个 handler。**接口契约见 [api-doc.md §3.2 MSG-1 ~ MSG-4](./api-doc.md#32-回传队列python--java)**；本节描述实现层决策。

#### 4.2.1 OcrProgress handler

- **幂等去重**: 用 `processing_stage` 的 ordinal 比较丢弃过期消息（避免乱序覆盖更新后的阶段）
- **FOR UPDATE 锁**: 锁 `ai_ocr_file` 行后再判定阶段，防并发 worker 同时处理两条 progress 消息
- **`stage_detail` JSONB 透传**: 必须原样写入 DB，前端从 Python `/state` 端点读取（v2：Java 不做转发）
- **状态推进**: 首次到达时推进 `file.status: QUEUED → PROCESSING` + `task.status: UPLOAD_COMPLETE → PROCESSING`（CAS 防止覆盖更后状态）
- **不触发终态**: 仅 OcrResult handler 才触发 `task.status` 终态转换

#### 4.2.2 OcrResult handler

- **`@Transactional` + FOR UPDATE 锁 task 行**: 防御场景 —— 两个 worker 同时处理 task 最后两个文件的 OcrResult，无锁会导致两条消息都把 task 推进到 SIMILARITY_CHECKING（重复触发）
- **CAS 更新 file.status**: `expectedStatus=PROCESSING`；返回 0 行则视为重复消息丢弃（幂等）
- **批次完成判定**（在锁内计数）:
  - 全部 `REVIEW_READY`（至少一个成功）→ `task.status=SIMILARITY_CHECKING` + 发布 `TaskReadyForReviewEvent`
  - 全部 `FILE_FAILED` → `task.status=FAILED`
  - 全部 `has_extractable_data=false` → `task.status=NO_DATA_BYPASS`（见 §5.6）
  - 否则保持 PROCESSING
- **AFTER_COMMIT 入队**: `TaskReadyForReviewEvent` 由 `OcrSimilarityCheckSqsProducer` 在 AFTER_COMMIT 阶段消费 + 发 SQS

#### 4.2.3 OcrSimilarityCheckResult handler

- **跨域 INSERT 例外**: `ai_ocr_similarity_hint` 由 Python 直接 INSERT；Java handler **只做状态推进 + state_log 写入**
- **跨公司归属校验**: 比对 `task.company_id == msg.companyId`，不一致直接丢弃（防伪造）
- **CAS 推进状态**: 仅 `SIMILARITY_CHECKING → REVIEWING`；过期消息丢弃
- **失败态语义**: `SIMILARITY_CHECK_FAILED` 不阻塞用户，前端在 Python `/state` 端点检测到该状态后提供"跳过相似度提示"按钮

#### 4.2.4 OcrMemoryLearnProgress handler

| `learnStage` | Java 端动作 |
|--------------|-------------|
| `IN_PROGRESS` | CAS：`MEMORY_LEARN_PENDING → MEMORY_LEARN_IN_PROGRESS` |
| `COMPLETE` | CAS：`MEMORY_LEARN_IN_PROGRESS → COMPLETED` + 写 state_log `MEMORY_LEARN_COMPLETE` |
| `FAILED` | 读 `ai_ocr_memory_learn_log` 计数：`<3` 回 PENDING 等重试；`≥3` 进 MEMORY_LEARN_FAILED 终态 |

**关键约束**: `MEMORY_LEARN_FAILED` 终态 **不回滚 fi_***（财务数据已 committed，不允许重做）。

### 4.3 OcrSimilarityCheckSqsProducer

| 实现层关注点 | 决策 |
|------------|------|
| 触发 | 由 `OcrResultSqsProcessor#handleResult` 通过 `publishEvent(TaskReadyForReviewEvent)` 派发 |
| 消费 | `@TransactionalEventListener(phase = AFTER_COMMIT)` 才发送 SQS（严禁 BEFORE_COMMIT） |
| 聚合粒度 | 每个 task 入队**仅 1 条消息**（聚合所有 mapping_result.account_label）；不是 per-file |
| HMAC-SHA256 签名 | 见 §6.3 |

### 4.4 OcrMemoryLearnSqsProducer

| 实现层关注点 | 决策 |
|------------|------|
| 触发时机 | `/tasks/{id}/commit` 事务 **AFTER_COMMIT** 阶段（fi_* 写入成功后） |
| payload 构建 | 对每个 `extracted_row` 比对 `originalAiCategory` vs `confirmedCategory`，生成 `mappingComparisons[]` 数组 |
| `wasOverridden` 计算 | Java 端计算 `originalAiCategory != confirmedCategory`；Python 端只学习 `wasOverridden=true` 的条目 |
| 重试支持 | `attemptNumber` 字段；首次为 1。**v2 注意**：原 Java `/memory-learn/retry` 端点已删除；重试改由 Python 内部 cron 或 Python `/state` 端点暴露 retry 入口（详见 python-design.md） |
| HMAC-SHA256 签名 | 见 §6.3 |

### 4.5 队列配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `visibilityTimeout` | 300s (5 分钟) | 50 页 PDF 处理需要 ~60s |
| `maxReceiveCount` | 3 | 3 次重试后进 DLQ |
| `messageRetentionPeriod` | 345600s (4 天) | 与现有队列一致 |
| DLQ | 共享 `dlq-queue` | 通过 `messageType` 字段区分 |

### 4.6 DocParseTaskSweeper（v2 收窄）

异步消息驱动状态机存在"消息丢失"或"Python/Java 崩溃"导致任务永久停留的风险。`@Scheduled(fixedDelay=120_000)` 每 2 分钟扫描自愈。

| 扫描分支 | 阈值 | 动作 |
|---------|------|------|
| `sweepDraftExpired` | DRAFT > 24h | 删 S3 对象 + `status=EXPIRED` + 清理 Imported Statements 占位行 |
| `sweepZombieProcessing` | file.PROCESSING > 20min | 跨 schema 检查 Python 是否已写 `ai_ocr_extracted_table`：有 → 推进 REVIEW_READY；无 → FILE_FAILED |
| `sweepStuckMemoryLearn` | MEMORY_LEARN_IN_PROGRESS > 10min | `status=MEMORY_LEARN_FAILED`（fi_* 不回滚） |

**v2 不再扫描的状态**:
- `VERIFYING` → 由 Python 自身管理（v2 边界变更）
- `SIMILARITY_CHECKING` → 瞬态，由 SQS DLQ 兜底
- `COMMITTING` → 事务回滚自动恢复

**实现层关键决策**:
- 使用 `@Scheduled(fixedDelay)` 而非 `fixedRate`
- 每个 sweep 分支使用独立事务，失败不影响其他分支
- 僵尸任务数 > 0 触发 Prometheus 告警

### 4.7 Java/Python 数据库物理部署

**关键决策**: Java 和 Python 共用**同一个** PostgreSQL RDS 实例 + **同一个 schema**（简化部署，避免跨库 JOIN）。通过数据库角色权限实现读写隔离 —— 完整 GRANT 语句见 [database-schema.md §4](./database-schema.md#4-数据库角色与权限)。

**角色权限矩阵概览**:

| 表归属 | `java_app` 角色 | `python_worker` 角色 |
|-------|-----------------|---------------------|
| Java 拥有的 `ai_ocr_*`（task / file / state_log / conflict_note / commit_audit）| RWUD | SELECT |
| 跨域例外 INSERT（memory_learn_log / similarity_hint / task_state_log / conflict_note）| RWUD | INSERT only |
| 跨域例外 UPDATE（conflict_record / similarity_hint detection）| RWUD | UPDATE 部分字段 |
| Python 拥有的 `ai_ocr_*`（extracted_table / row / mapping_result / conflict_record）| SELECT | RWUD |
| Python 私有：`ai_ocr_mapping_memory*` | 无权限 | RWUD |
| 财务表 `fi_*` | RWU | **v2 新增 SELECT**（用于 Python `/verify` 端点跑冲突检测） |

---

## 5. Commit 流程实现层（端点 4 — 核心职责）

> **业务流程定义** → [system-architecture.md 4 步流程 第 4 步](./system-architecture.md)；**端点 URL/字段** → [api-doc.md #4 /commit](./api-doc.md#4-tasksidcommit-post)；**Proforma/冲突业务规则** → [python-design.md](./python-design.md)。本节聚焦 Java 端事务边界与并发设计。

### 5.1 v2 Commit 端点重大变更

v1 行为 → v2 简化：

| v1 | v2 |
|----|----|
| `/commit` 同步执行；前端独立调 `/commit/result` 拿 Benchmark URL | `/commit` 响应**直接含** `benchmarkRedirectUrl`（合并 `/commit/result`） |
| `/commit` 后前端轮询 Java `/tasks/{id}/status` 看 MEMORY_LEARN 进度 | 前端轮询 Python `/state.memoryLearn.stage` 看进度 |
| 前端在 commit 成功后另起逻辑跳 Benchmark | `/commit` 响应内 `benchmarkRedirectUrl` 直接前端 router push |

### 5.2 两阶段事务模型

```
事务内（@Transactional(propagation=REQUIRED, rollbackFor=Exception.class)）:
  ① FOR UPDATE 锁 ai_ocr_task 行（防并发 Commit）
  ② CAS 校验：status IN (REVIEWING, CONFLICT_RESOLUTION, READY_TO_COMMIT) → COMMITTING
  ③ Hard gate 二次校验：
     ├─ Python `/verify` 已跑且无 PENDING 冲突
     ├─ 所有 row 都有 lg_category（unmapped 拒绝）
     └─ 任一失败 → 抛 HARD_GATE_FAILED + 回滚
  ④ 读 ai_ocr_extracted_row + ai_ocr_mapping_result（跨 schema SELECT）
  ⑤ 按 resolution 策略写 fi_* 财务表（Actuals）+ 调 ProformaForecastService.appendVersion()
  ⑥ 写 ai_ocr_commit_audit（written/overwritten/skipped + 关联 conflict_note_id）
  ⑦ task.status=COMMITTED；files.status=FILE_COMMITTED
  ⑧ 若 revision：parent.status=SUPERSEDED + parent.superseded_by=self.id
  ⑨ 构建 benchmarkRedirectUrl（BenchmarkRedirectService.buildUrl(taskId, writtenPeriods)）
  ⑩ publishEvent(CommitSuccessEvent)（Spring 事件，不立即发 SQS）
  ⑪ 返回 CommitRespVo{writtenAccounts, writtenPeriods[], importedStatementsFolderId, benchmarkRedirectUrl}

AFTER_COMMIT（@TransactionalEventListener(phase = AFTER_COMMIT)）:
  ⑫ ImportedStatementsService.finalize(taskId)
     └─ 把所有 visible=false 的占位行设为 visible=true（含 has_extractable_data=false 文件）
  ⑬ 触发下游 normalization 流程（@Async）
  ⑭ 检测新 closed month → ClosedMonthMailService.notify()（写 state_log NEW_CLOSED_MONTH）
  ⑮ 构建 mappingComparisons → OcrMemoryLearnSqsProducer.send(...)（参见 §4.4）
  ⑯ task.status=MEMORY_LEARN_PENDING
  ⑰ 写 state_log COMMIT_COMPLETE
```

### 5.3 关键实现层约束

| 约束 | 实现机制 |
|------|---------|
| 并发互斥 | `@Lock(LockModeType.PESSIMISTIC_WRITE)` 或 `SELECT ... FOR UPDATE` + CAS（受影响 0 行 → 抛 INVALID_STATUS_FOR_COMMIT） |
| ⚠️ SQS 必须在 AFTER_COMMIT 发 | `@TransactionalEventListener(phase = AFTER_COMMIT)`，否则事务回滚后 Python 已收到记忆学习消息会写入脏记忆 |
| 部分写入禁止 | 任一 metric 写入失败 → 整个 @Transactional 回滚，task.status 自动恢复 |
| Hard gate 双重校验 | 前端调 commit 前必须先调 Python `/verify` 通过；Java 端再二次校验防绕过 |

### 5.4 Commit 失败的恢复路径（Q7 方案 B）

Commit 失败**不置 task.status=FAILED**。事务 rollback 后 task.status 自动回到 `READY_TO_COMMIT` 或 `CONFLICT_RESOLUTION`。

| 异常类型 | 处理 | task.status 结果 |
|---------|------|-----------------|
| 业务异常（HARD_GATE_FAILED / INVALID_STATUS_FOR_COMMIT 等）| 直接抛出，不回滚 | 保持原值 |
| 技术异常（DB 死锁/字段约束/OOM/网络）| @Transactional 自动回滚 + 抛 `COMMIT_FAILED_RETRYABLE` | 自动恢复为进入方法前的值 |

**用户体验**: Java 返回 500 + errorCode=`COMMIT_FAILED_RETRYABLE` → 前端弹 Modal "数据未写入，请稍后重试 [重试]"；点重试再次 POST /commit 即可（幂等可接受）。

### 5.5 v2 ImportedStatementsService 职责（预占位 → 最终化）

| 阶段 | 触发 | 动作 |
|------|------|------|
| **预占位** | `/upload-init` 事务内 | 创建 "Imported Statements/{taskUuid}/" 文件夹（visible=false） + 为每个合法文件预创建占位行（s3_key=placeholder, status=UPLOADING） |
| **绑定 s3_key** | `/upload-complete` 事务内 | 文件 magic bytes 校验通过后更新占位行 s3_key（仍 visible=false） |
| **最终化** | `/commit` AFTER_COMMIT | 设 visible=true（用户可见）；含 has_extractable_data=false 文件也一并最终化 |
| **取消清理** | Sweeper DRAFT EXPIRED 24h | 删除占位行 + 删 S3 对象 |

**为什么预占位**：用户在上传过程中即可在 Documents 视图看到"导入中"状态，提供进度感。文件夹按 `company_id` 全局唯一，首次提交时由 CompanyDocService 自动创建。

### 5.6 边界用例 — 无可提取数据（NO_DATA_BYPASS）

> **业务规则** → [requirement-analysis §4.12](./requirement-analysis.md)。本节仅说明 Java 端状态机决策。

`OcrResultSqsProcessor#handleResult` 在 task 内所有 OcrResult 收到后聚合判定：

| 文件聚合结果 | task 状态推进 | 后续动作 |
|-------------|--------------|---------|
| 全部 `has_extractable_data=false` | `status=NO_DATA_BYPASS` → AFTER_COMMIT `ImportedStatementsService.finalize()` → `status=COMPLETED` | 跳过 MEMORY_LEARN（无需学习）；前端通过 Python `/state` 发现状态变化 |
| 全部 true | 走正常流程（→ SIMILARITY_CHECKING → REVIEWING → 用户审核 → /verify → /commit） | — |
| 混合 | 仅有数据文件参与 verify + commit | 无数据文件在 commit AFTER_COMMIT 时一并 finalize |

`DocParseStatus.NO_DATA_BYPASS` 是单独枚举值，区别于 `FAILED`。

---

## 6. 任务修订实现层（端点 5）

> 端点 URL / 请求字段参见 [api-doc.md #5](./api-doc.md#5-tasksidrevise-post)。

**Java 实现层关键决策**（事务内）:
- 校验 parent task.status ∈ {COMPLETED, SUPERSEDED}
- 新 task 沿用 parent 的 `s3_key`（不重新上传文件，仅 COPY `ai_ocr_file` 行）
- copy-on-write 继承：
  - `ai_ocr_extracted_table/row` 由 Java 直接 COPY（v2：Java 写入 Python 拥有的表是单向例外，仅 revise 场景）—— 或改由 Python 通过 SQS 异步复制（推荐，避免跨域写）
  - `ai_ocr_mapping_result` 由 Java 直接 INSERT（v1 行为不变）
- `revision_number = parent.revision_number + 1`（受 UNIQUE 约束保护并发）
- Commit 成功后置 parent.status=SUPERSEDED + parent.superseded_by=self.id（在 §5.2 commit 事务步骤 ⑧ 处理）
- 修订原因记录到 `ai_ocr_task.revision_reason`

**Cancel 选项已移除**（Asana 2026-04-19）。用户若要放弃提交直接退出页面，task 状态保持 REVIEWING；Sweeper 24h 后清 DRAFT。

---

## 7. 安全要求

### 7.1 移除 FileController @AnonymousAccess

| 问题 | 严重级别 | 修复 |
|------|---------|------|
| 上传端点 `@AnonymousAccess` 无认证 | **CRITICAL** | 移除 `@AnonymousAccess`，所有 `/api/v1/docparse/*` 端点必须 JWT 认证 |

### 7.2 上传校验 MIME + magic bytes

允许的 MIME 类型白名单：
- `application/pdf`
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `text/csv`
- `image/jpeg`、`image/png`、`image/tiff`

校验流程：先检查文件扩展名，再读取首 2KB magic bytes 确认真实类型，两者必须一致。

### 7.3 SQS 消息 HMAC 签名

每条 SQS 消息附加 `hmacSignature` 字段，使用共享密钥对消息体做 HMAC-SHA256 签名。消费端处理前必须校验签名有效性。Producer 与 Consumer 共享 secret 通过 AWS Secrets Manager 轮换。

### 7.4 SQS 消费时跨公司归属校验

`OcrResultSqsProcessor` 消费结果消息时，必须校验 `fileId` 对应的 `ai_ocr_file.task_id → ai_ocr_task.company_id` 与消息中的 `companyId` 一致，防止跨公司数据越权。

### 7.5 S3 Bucket CORS（生产必需）

Presigned URL 直传要求 S3 Bucket 配置 CORS 允许前端 origin。**严禁使用 `*` 或 localhost 作为 AllowedOrigins**。

| CORS 字段 | 生产值 | 开发环境 |
|----------|-------|---------|
| AllowedOrigins | `https://portal.lookingglass.com` | `http://localhost:8000`（独立 dev Bucket） |
| AllowedMethods | `PUT, GET` | 同上 |
| AllowedHeaders | `Content-Type, x-amz-*` | 同上 |
| ExposeHeaders | `ETag` | 同上 |
| MaxAgeSeconds | 3000 | 同上 |

### 7.6 S3 Presigned URL 安全增强（5 项约束）

| # | 约束 | 实现机制 |
|---|------|---------|
| 1 | Presigned PUT 必须加 `content-length-range` 条件 | `PutObjectRequest.builder().contentLength(fileSize)` —— 防止绕过 20MB 限制 |
| 2 | Presigned GET 生存期 **5 分钟**（不是 15 分钟） | `signatureDuration(Duration.ofMinutes(5))` |
| 3 | `/upload-complete` 端点严禁信任前端传入的 s3Key | 必须从 `ai_ocr_file` 表查 s3Key，再调 `s3:HeadObject`（防伪造）|
| 4 | `file_hash` 格式强校验 | DTO 字段加 `@Pattern(regexp = "^[a-f0-9]{64}$")` 防注入 |
| 5 | CloudTrail S3 Data Events 启用 | 生产 Bucket 启用 PutObject/GetObject/DeleteObject 日志 |

### 7.7 IAM 角色与数据库角色

**S3 / SQS IAM 权限划分**:

| Role | S3 权限 | SQS 权限 |
|------|--------|---------|
| Java IAM Role | `s3:PutObject` + `s3:GetObject` + `s3:DeleteObject` → `ocr-uploads/*` | `sqs:SendMessage` → `ocr-extract-queue` / `ocr-similarity-check-queue` / `ocr-memory-learn-queue`；`sqs:Receive/Delete` → `ocr-result-queue` |
| Python IAM Role | `s3:GetObject` → `ocr-uploads/*`（只读） | `sqs:Receive/Delete` → `ocr-extract-queue` / `ocr-similarity-check-queue` / `ocr-memory-learn-queue`；`sqs:SendMessage` → `ocr-result-queue` + `ocr-extract-queue`（v2：REMAP_ONLY 触发）|

**数据库角色隔离**: 见 §4.7。

### 7.8 v2 Python 端点的 JWT 共享

v2 Python 端点（`/ocr/*`）需与 Java 共享 JWT secret：
- Java 签发 JWT（登录时）
- Python 端验签使用同一 secret（通过 AWS Secrets Manager 同步）
- `company_id` 从 JWT claim 提取，与 URL path 中的 task `company_id` 比对
- 详见 [system-architecture.md §0.1 Python 必备基础设施](./system-architecture.md#01-边界划分2026-05-06-v2-重大重构)
