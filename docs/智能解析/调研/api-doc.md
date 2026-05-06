# OCR Agent 接口文档

> **本文档定位**: OCR Agent 所有接口（REST / SQS / LangGraph 节点）的**唯一权威清单**，从 java-design.md / python-design.md 中抽取，独立维护。
>
> **使用方式**: 先看 §1 总览（一行一个接口） → 需要细节时跳转 §2-§4 详细章节。
>
> **关联文档**: [系统架构](./system-architecture.md) · [数据库 Schema](./database-schema.md) · [Java 设计](./java-design.md)（实现层）· [Python 设计](./python-design.md)（实现层）· [前端设计](./frontend-design.md) · [用户输入](../user-input-requirements.md)

---

## 1. 接口总览（快速索引）

### 1.1 REST 端点（Java 对外，前端调用）

> 共 **22 个**端点；前缀 `/api/v1/docparse`；JWT + `company_id` 归属校验。

| # | URL | 方法 | 一句话职责 | 详情 |
|---:|-----|:---:|----------|:---:|
| 1 | `/tasks` | POST | 创建新 OCR Task（DRAFT） | [→](#1-tasks-post) |
| 2 | `/tasks/{id}/revise` | POST | 基于历史 task 创建修订版（copy-on-write） | [→](#2-tasksidrevise-post) |
| 3 | `/tasks/{id}/status` | GET | 前端 2s 轮询：task + files 进度 | [→](#3-tasksidstatus-get) |
| 4 | `/tasks/{id}/result` | GET | 取 task 所有提取结果，供 ReviewPage | [→](#4-tasksidresult-get) |
| 5 | `/tasks/{id}/history` | GET | 沿 parent_task_id 链返回所有版本 | [→](#5-tasksidhistory-get) |
| 6 | `/upload/request-urls` | POST | 文件预校验 + 生成 S3 presigned PUT URL | [→](#6-uploadrequest-urls-post) |
| 7 | `/upload/complete` | POST | 验证上传 + 入队 ocr-extract-queue | [→](#7-uploadcomplete-post) |
| 8 | `/upload/abort` | POST | 取消上传 + 删 S3 对象 | [→](#8-uploadabort-post) |
| 9 | `/files/{fileId}/download-url` | POST | ReviewPage 渲染用：S3 presigned GET URL | [→](#9-filesfileiddownload-url-post) |
| 10 | `/tasks/{id}/review` | PATCH | 保存用户对 row/mapping 的修改 | [→](#10-tasksidreview-patch) |
| 11 | `/tasks/{id}/mapping-summary` | GET | Step 5a：摘要 + hardGate 错误 | [→](#11-tasksidmapping-summary-get) |
| 12 | `/tasks/{id}/verify/start` | POST | Step 5a：触发后台冲突检测 | [→](#12-tasksidverifystart-post) |
| 13 | `/tasks/{id}/verify/progress` | GET | Step 5a：进度轮询 | [→](#13-tasksidverifyprogress-get) |
| 14 | `/tasks/{id}/conflicts` | GET | Step 5b：列出 Actuals 冲突 | [→](#14-tasksidconflicts-get) |
| 15 | `/tasks/{id}/conflicts/{conflictId}/resolve` | POST | Step 5b：单冲突解决（Note 必填） | [→](#15-tasksidconflictsconflictidresolve-post) |
| 16 | `/tasks/{taskId}/conflicts/{conflictId}/notes` | GET | 取 conflict note thread | [→](#16-tasksidconflictsconflictidnotes-get) |
| 17 | `/tasks/{taskId}/conflicts/{conflictId}/notes` | POST | 追加 note 到 thread | [→](#17-tasksidconflictsconflictidnotes-post) |
| 18 | `/tasks/{id}/commit` | POST | Step 5c：整批写入 fi_* | [→](#18-tasksidcommit-post) |
| 19 | `/tasks/{id}/commit/result` | GET | Step 5c：拉成功摘要 + Benchmark URL | [→](#19-tasksidcommitresult-get) |
| 20 | `/tasks/{id}/navigate-back` | POST | §4.13 Previous 回退 + 变更检测 | [→](#20-tasksidnavigate-back-post) |
| 21 | `/tasks/{id}/similarity-hints` | GET | 查相似度提示列表 | [→](#21-tasksidsimilarity-hints-get) |
| 22 | `/similarity-hints/{hintId}` | PATCH | 用户决策：MERGED / IGNORED | [→](#22-similarity-hintshintid-patch) |
| 23 | `/tasks/{id}/memory-learn` | GET | 记忆学习最新状态 | [→](#23-tasksidmemory-learn-get) |
| 24 | `/tasks/{id}/memory-learn/history` | GET | 记忆学习所有尝试历史 | [→](#24-tasksidmemory-learnhistory-get) |
| 25 | `/tasks/{id}/memory-learn/retry` | POST | 手动重试记忆学习（attempt<3） | [→](#25-tasksidmemory-learnretry-post) |

### 1.2 SQS 队列（Java ↔ Python）

> 严禁 HTTP 直连，仅 SQS。详见 [system-architecture.md §0.2](./system-architecture.md#02-java--python-通信仅通过-sqs-队列)。

#### 1.2.1 Java → Python（出口队列）

| 队列 | 触发场景 | 一句话职责 | 详情 |
|------|---------|----------|:---:|
| `ocr-extract-queue` | 用户场景 A：文件解析 | 触发 OCR + AI 提取 + AI 映射；`mode` 字段区分 FULL_EXTRACT / REMAP_ONLY | [→](#sqs-1-ocr-extract-queue) |
| `ocr-similarity-check-queue` | 内部辅助：所有文件 REVIEW_READY 后 | 触发 embedding + KNN 相似度检测 | [→](#sqs-2-ocr-similarity-check-queue) |
| `ocr-memory-learn-queue` | 用户场景 B：fi_* 写入成功后 | 触发记忆学习更新 mapping_memory | [→](#sqs-3-ocr-memory-learn-queue) |

#### 1.2.2 Python → Java（回传队列，按 messageType 多路复用）

> 单一队列 `ocr-result-queue`；4 个 messageType 分发到 4 个 handler。

| messageType | Handler | 一句话职责 | 详情 |
|-------------|---------|----------|:---:|
| `OcrProgress` | `OcrResultSqsProcessor#handleProgress` | 文件级精细进度上报（每个 stage 一条） | [→](#msg-1-ocrprogress) |
| `OcrResult` | `OcrResultSqsProcessor#handleResult` | 单文件最终结果上报 | [→](#msg-2-ocrresult) |
| `OcrSimilarityCheckResult` | `OcrResultSqsProcessor#handleSimilarityCheckResult` | 相似度检测完成回执 | [→](#msg-3-ocrsimilaritycheckresult) |
| `OcrMemoryLearnProgress` | `OcrResultSqsProcessor#handleMemoryLearnProgress` | 记忆学习进度回报 | [→](#msg-4-ocrmemorylearnprogress) |

### 1.3 LangGraph Pipeline 节点（Python 内部）

> 共 5 个核心节点；周期推断作为 Extract 尾部子步骤（不是独立节点）。

| 节点 | 文件 | 一句话职责 | 详情 |
|------|------|----------|:---:|
| **Preprocess** | `workflow/nodes/preprocess.py` | PDF/图片/Excel 标准化为统一可消费格式 | [→](#node-1-preprocess) |
| **Extract** | `workflow/nodes/extract.py` | Vision LLM 提取表格 + 周期推断 + 可提取性判定 | [→](#node-2-extract) |
| **Classify** | `workflow/nodes/classify.py` | 文档类型识别（PNL/BS/CF/Proforma/MISC） | [→](#node-3-classify) |
| **Map** | `workflow/nodes/map.py` | 三层级联映射到 19 个 LG 分类 | [→](#node-4-map) |
| **Validate** | `workflow/nodes/validate.py` | OCR 数据自洽性硬验证 + 软警告 | [→](#node-5-validate) |

---

## 2. REST 端点详情

> 通用约定：所有端点位于 `/api/v1/docparse` 前缀下；JWT 认证 + `company_id` 归属校验；返回 `Result<T>` 标准包装。

### 1. /tasks (POST)
- **Controller**: `DocParseController#createTask`
- **请求**: `DocParseCreateTaskReqVo`（可空）
- **响应**: `DocParseUploadRespVo`（含 `taskId`）
- **职责**: 创建一个新的 OCR Task（status=DRAFT），返回 taskId 供后续上传

### 2. /tasks/{id}/revise (POST)
- **Controller**: `DocParseController#reviseTask`
- **请求**: `DocParseReviseReqVo`（含 `reason`）
- **响应**: `{newTaskId}`
- **职责**: 基于历史已 COMPLETED/SUPERSEDED 的 task 创建修订版（copy-on-write 继承文件 + 提取数据 + 映射），新 task.status=DRAFT

### 3. /tasks/{id}/status (GET)
- **Controller**: `DocParseController#getStatus`
- **响应**: `DocParseStatusRespVo`
- **职责**: 前端 2s 轮询：返回 `task.status` + `files[].status` + `processing_stage` + `progress_pct` + `stage_detail`，驱动 UI 进度条

### 4. /tasks/{id}/result (GET)
- **Controller**: `DocParseController#getResult`
- **响应**: `DocParseResultRespVo`
- **职责**: 取所有 file 的提取结果（`extracted_table` / `extracted_row` + `mapping_result`），供 ReviewPage 渲染

### 5. /tasks/{id}/history (GET)
- **Controller**: `DocParseController#getHistory`
- **响应**: `DocParseHistoryRespVo`
- **职责**: 沿 `parent_task_id` 链回溯，返回此 task 的所有版本（v1→v2→v3）+ 每版本的 commit 时间 / 操作者 / `revision_reason`

### 6. /upload/request-urls (POST)
- **Controller**: `UploadController#requestPresignedUrls`
- **请求**: `DocParseUploadReqVo`（`taskId, files[]`）
- **响应**: `DocParseUploadRespVo`（`uploads[]`）
- **职责**: 每个文件预校验（大小/扩展名/SHA-256 重名）→ 创建 `ai_ocr_file(PENDING)` → 生成 S3 presigned PUT URL（15min）；重名/超限文件返回 error

### 7. /upload/complete (POST)
- **Controller**: `UploadController#completeUpload`
- **请求**: `DocParseUploadCompleteReqVo`（`fileId, etag, actualSize`）
- **响应**: `{status, error}`
- **职责**: `s3:HeadObject` 验证对象存在 + magic bytes 校验 → `file.status=UPLOADED` + 入队 `ocr-extract-queue`（mode=FULL_EXTRACT）；失败则 `s3:DeleteObject` + `FILE_FAILED`

### 8. /upload/abort (POST)
- **Controller**: `UploadController#abortUpload`
- **请求**: `DocParseUploadAbortReqVo`（`taskId, fileIds[]`）
- **响应**: `{abortedCount}`
- **职责**: 用户取消上传：批量删 S3 对象 + 标记 `ai_ocr_file.deleted=true`；task 仍保持 DRAFT 等待重传或过期

### 9. /files/{fileId}/download-url (POST)
- **Controller**: `FileViewController#getDownloadUrl`
- **响应**: `{url, expiresAt}`
- **职责**: ReviewPage 加载 PDF/Excel/图片时调用：生成 S3 presigned GET URL（5min），前端用此 URL 直接渲染

### 10. /tasks/{id}/review (PATCH)
- **Controller**: `ReviewController#saveReview`
- **请求**: `DocParseReviewReqVo`（`rows[], mappings[]`）
- **响应**: `{updatedRowCount, updatedMappingCount}`
- **职责**: 保存用户对 `extracted_row` / `mapping_result` 的修改
- **副作用**: 清空 `task.summary_cache` + 更新 `mapping_changed_at`（触发 5a 重新聚合）

### 11. /tasks/{id}/mapping-summary (GET)
- **Controller**: `MappingSummaryController#getSummary`
- **响应**: `DocParseMappingSummaryRespVo`
- **职责**: Step 5a 进入：返回文件总数 / 映射类型数 / 映射账户数 + `hardGateErrors[]`（unmapped/unreviewed/missing-metadata）；命中 `summary_cache` 直接返回

### 12. /tasks/{id}/verify/start (POST)
- **Controller**: `MappingSummaryController#startVerification`
- **响应**: `DocParseVerifyStartRespVo`
- **职责**: Step 5a 用户点 "Start Verification"：FOR UPDATE 锁 task → hard gate 检查 → 推进 `status=VERIFYING` → 异步启动冲突检测 Job

### 13. /tasks/{id}/verify/progress (GET)
- **Controller**: `MappingSummaryController#getProgress`
- **响应**: `DocParseVerifyProgressRespVo`
- **职责**: Step 5a 进度轮询：返回 `stage`(PENDING/RUNNING/COMPLETED/ABORTED) + `percent` + 已检测冲突数

### 14. /tasks/{id}/conflicts (GET)
- **Controller**: `ConflictResolutionController#listConflicts`
- **响应**: `DocParseConflictListRespVo`
- **职责**: Step 5b 入口：返回 Actuals 冲突列表（Proforma 整体豁免不入此列表），按 `lg_metric, reporting_period` 排序

### 15. /tasks/{id}/conflicts/{conflictId}/resolve (POST)
- **Controller**: `ConflictResolutionController#resolveOne`
- **请求**: `DocParseSingleConflictResolveReqVo`（`action, note`）
- **响应**: `DocParseConflictResolveRespVo`
- **职责**: Step 5b 单冲突解决：Note 必填硬校验 → 写 `conflict_record.resolution` + `conflict_note` → 计算下一冲突定位（Save & Next 导航）

### 16. /tasks/{taskId}/conflicts/{conflictId}/notes (GET)
- **Controller**: `ConflictNoteController#getThread`
- **响应**: `DocParseNoteThreadRespVo`
- **职责**: 取冲突 note thread（含 `parent_note_id` 链），用于审计与多人协作历史展示

### 17. /tasks/{taskId}/conflicts/{conflictId}/notes (POST)
- **Controller**: `ConflictNoteController#appendNote`
- **请求**: `DocParseNoteReplyReqVo`（`content, parentNoteId?`）
- **响应**: `{noteId, createdAt}`
- **职责**: 追加一条 note 到 thread；`auto_generated=false`（系统自动生成的另走 `CommitController` 的 §5.4 流程）

### 18. /tasks/{id}/commit (POST)
- **Controller**: `CommitController#commit`
- **响应**: `DocParseCommitRespVo`
- **职责**: Step 5c 整批写入：FOR UPDATE 锁 task → Actuals 写 `fi_*` / Proforma 调 `appendVersion` → `ai_ocr_commit_audit` 全量审计 → AFTER_COMMIT 触发 Documents 同步/闭月邮件/记忆学习 SQS

### 19. /tasks/{id}/commit/result (GET)
- **Controller**: `CommitController#getResult`
- **响应**: `DocParseCommitResultRespVo`
- **职责**: Step 5c 完成后跳 Benchmark 前端拉摘要：账户数 / 写入周期 / 文档类型 / Imported Statements 文件夹 ID / Benchmark 跳转 URL

### 20. /tasks/{id}/navigate-back (POST)
- **Controller**: `NavigationController#navigateBack`
- **请求**: `DocParseNavigateBackReqVo`（`targetStep`）
- **响应**: `DocParseNavigateBackRespVo`
- **职责**: §4.13 Previous 回退：重算 `mapping_snapshot_hash` 对比 → 未变保留下游结果；变了则清空 conflict resolution + summary_cache + 入队 `ocr-extract-queue`(mode=REMAP_ONLY)

### 21. /tasks/{id}/similarity-hints (GET)
- **Controller**: `SimilarityHintController#listHints`
- **响应**: `DocParseSimilarityHintListRespVo`
- **职责**: 查询 task 的相似度提示（`ai_ocr_similarity_hint` 由 Python 跨域 INSERT），区分 PENDING / MERGED / IGNORED 三态

### 22. /similarity-hints/{hintId} (PATCH)
- **Controller**: `SimilarityHintController#updateDecision`
- **请求**: `SimilarityHintDecisionReqVo`（`decision`）
- **响应**: `{updatedAt}`
- **职责**: 用户对相似度提示做决策：MERGED（合并到现有账户）/ IGNORED（忽略），UPDATE `ai_ocr_similarity_hint.user_decision`

### 23. /tasks/{id}/memory-learn (GET)
- **Controller**: `MemoryLearnController#getStatus`
- **响应**: `MemoryLearnStatusRespVo`
- **职责**: 返回最新一次记忆学习尝试的 `stage`(PENDING/IN_PROGRESS/COMPLETE/FAILED) + 统计（`newCount/updatedCount`）

### 24. /tasks/{id}/memory-learn/history (GET)
- **Controller**: `MemoryLearnController#getHistory`
- **响应**: `MemoryLearnHistoryRespVo`
- **职责**: 查询所有历史尝试（`ai_ocr_memory_learn_log`），含每次的 `attempt_number` / 错误信息 / 触发者

### 25. /tasks/{id}/memory-learn/retry (POST)
- **Controller**: `MemoryLearnController#retry`
- **响应**: `{newAttemptNumber}`
- **职责**: 手动重试：前置条件 `attempt_number<3` → 推进 `status=MEMORY_LEARN_PENDING` → 重发 `ocr-memory-learn-queue` 消息（不重写 fi_*）

---

## 3. SQS 接口详情

### 3.1 出口队列（Java → Python）

#### SQS-1: ocr-extract-queue
- **Producer**: `OcrExtractSqsProducer`
- **消息 DTO**: `DocParseExtractMessageDto`
- **触发时机**:
  - (a) `/upload/complete` 单文件上传完成且 magic bytes 通过
  - (b) `/tasks/{id}/navigate-back` 检测到 mapping 变更需 REMAP
- **关键字段**:
  - `messageType=OcrExtract`
  - `mode`: `FULL_EXTRACT` (默认) / `REMAP_ONLY`
  - `taskId / fileId / companyId`
  - `s3Bucket / s3Key / filename / contentType / fileSize`
  - `uploadedBy / callbackMeta`
- **Python 消费者**: `consumers/extract_consumer.py#handle_extract_message`
- **职责**:
  - `FULL_EXTRACT`: 全量走 OCR/Extract/Classify/Map/Validate（约 30-60s）
  - `REMAP_ONLY`: 仅重跑 Map 节点（约 1-10s），跳过 Preprocess/Extract/Classify

#### SQS-2: ocr-similarity-check-queue
- **Producer**: `OcrSimilarityCheckSqsProducer`
- **消息 DTO**: `OcrSimilarityCheckRequest`
- **触发时机**: task 内所有非 FAILED 文件 `file.status=REVIEW_READY` 时（在 `OcrResultSqsProcessor.handleResult()` 计数完成判定后），AFTER_COMMIT 入队
- **关键字段**:
  - `messageType=OcrSimilarityCheck`
  - `taskId / companyId`
  - `accountLabels[]`（聚合 task 下所有 mapping_result 的 account_label）
- **Python 消费者**: `consumers/similarity_check_consumer.py#handle_similarity_check`
- **职责**: 对所有 row 批量调 `text-embedding-3-small` → pgvector HNSW KNN → 过滤 cosine > 0.9 的对 → 批量 INSERT `ai_ocr_similarity_hint`（跨域写）

#### SQS-3: ocr-memory-learn-queue
- **Producer**: `OcrMemoryLearnSqsProducer`
- **消息 DTO**: `DocParseMemoryLearnMessageDto`
- **触发时机**: `/tasks/{id}/commit` 事务 AFTER_COMMIT 阶段，fi_* 写入成功后入队
- **关键字段**:
  - `messageType=OcrMemoryLearn`
  - `taskId / fileId / companyId`
  - `mappingComparisons[]`（`accountLabel / originalAiCategory / confirmedCategory / wasOverridden`）
  - `attemptNumber`
- **Python 消费者**: `consumers/memory_learn_consumer.py#handle_memory_learn`
- **职责**: 基于"AI 原始建议 vs 用户最终确认"差分做记忆学习；只学习 `wasOverridden=true` 的条目，写 `ai_ocr_mapping_memory` + 双重日志（`ai_ocr_mapping_memory_audit` 行级 + `ai_ocr_memory_learn_log` 任务级）

### 3.2 回传队列（Python → Java）

> 单一队列 `ocr-result-queue`，按 `messageType` 多路复用到 Java 的 `OcrResultSqsProcessor` 4 个 handler 方法。

#### MSG-1: OcrProgress
- **Java Handler**: `OcrResultSqsProcessor#handleProgress`
- **写哪些表**: UPDATE `ai_ocr_file`(`processing_stage` / `progress_pct` / `stage_detail` JSONB)
- **状态变更**:
  - `file.status: QUEUED → PROCESSING`（首次到达时）
  - `task.status: UPLOAD_COMPLETE → PROCESSING`（首次到达时，CAS）
- **职责**: 文件级精细进度上报，每个 Python 子阶段切换时一条；幂等去重靠 `processing_stage` ordinal 比较丢弃过期消息；不触发 task 终态转换

**`processingStage` 12 个枚举值**（按 ordinal 升序，旧 stage 消息会被 Java 丢弃）：

| Stage | 进度区间 | 对应 LangGraph 节点 | 前端显示 | 持久化时机 |
|-------|---------|------------------|---------|-----------|
| `QUEUED` | 0% | — | "已入队" | Java 入队 ocr-extract-queue 时 |
| `PREPROCESS_PENDING` | 1-5% | Preprocess（开始） | "准备解析" | Python 收到消息 |
| `PREPROCESSING` | 6-15% | Preprocess（执行中） | "格式转换中" | 调 eSapiens 或 openpyxl 时 |
| `EXTRACTING` | 16-50% | Extract | "AI 识别表格" | 进入 Vision LLM 调用 |
| `MAPPING_RULE_LAYER` | 51-60% | Map（Layer 1） | "应用业务规则" | 规则引擎匹配中 |
| `MAPPING_MEMORY_LOOKUP` | 61-70% | Map（Layer 2） | "查询历史记忆" | pg_trgm 模糊匹配中 |
| `MAPPING_INDUSTRY_LAYER` | 71-78% | Map（Layer 3） | "应用行业模板" | 行业高频映射中 |
| `MAPPING_LLM_FALLBACK` | 79-90% | Map（Layer 4） | "AI 智能映射" | 仅未命中行批量送 LLM |
| `VALIDATING` | 91-95% | Validate | "校验数据一致性" | 内部一致性检查 |
| `PERSISTING` | 96-99% | — | "保存结果" | 写 ai_ocr_extracted_* / ai_ocr_mapping_result |
| `REVIEW_READY` | 100% | — | "可审核" | file.status 推进到 REVIEW_READY |
| `FAILED` | — | — | 显示错误 | OcrResult{status=failed} 收到时 |

**`stageDetail` JSONB 各阶段附带字段**：

| Stage | stageDetail 字段示例 | 用途 |
|-------|--------------------|------|
| `EXTRACTING` | `{model: "gemini-2.5-flash", pageIdx: 3, totalPages: 5, retries: 0}` | 大文档时让前端展示"正在识别第 3/5 页" |
| `MAPPING_MEMORY_LOOKUP` | `{queriedRows: 42, hitCount: 28, missCount: 14}` | 让用户感知记忆命中率 |
| `MAPPING_LLM_FALLBACK` | `{batchedRows: 14, model: "claude-sonnet-4", attemptedAt: "2026-05-06T10:32:14Z"}` | LLM 兜底时的可观测性 |
| 其他 | `null` 或省略 | — |

#### MSG-2: OcrResult
- **Java Handler**: `OcrResultSqsProcessor#handleResult`
- **写哪些表**:
  - UPDATE `ai_ocr_file`(`status` / `extracted_table_count` / `total_rows` / `has_extractable_data`)
  - INSERT `ai_ocr_task_state_log`(EXTRACT_COMPLETE / EXTRACT_NO_DATA / EXTRACT_FAILED)
- **状态变更**:
  - `file.status: PROCESSING → REVIEW_READY | FILE_FAILED`（CAS）
  - 当 task 内所有非 FAILED 文件 REVIEW_READY 时 → `task.status: PROCESSING → SIMILARITY_CHECKING`（FOR UPDATE + 计数）+ AFTER_COMMIT 入队 `ocr-similarity-check-queue`
- **职责**: 单文件最终结果上报；FOR UPDATE 锁 task 行做计数，全部失败 → `task.status=FAILED`；任一成功且全部完成 → 进入相似度检测阶段

**`status` 三个终态枚举值**：

| status | 含义 | file 终态 | 写入 state_log event_type | 后续动作 |
|--------|------|----------|------------------------|---------|
| `completed` | 解析成功，含可提取财务数据 | `REVIEW_READY` | `EXTRACT_COMPLETE` | 等同 task 内其他文件，全部完成后进入相似度检测 |
| `completed_no_data` | 解析成功，但无可提取财务数据（空文档/纯文字/封面）| `REVIEW_READY`（仍标已完成）| `EXTRACT_NO_DATA`（携带 `skipReason`）| **跳过** mapping/conflict/write，文件仍保存到 Imported Statements；混合批次时不阻塞其他文件 |
| `failed` | 解析失败（OCR 异常 / LLM 超时 / 格式不支持）| `FILE_FAILED` | `EXTRACT_FAILED`（携带 `error`）| 全部失败 → `task.status=FAILED`；部分失败 → 该文件不参与下游 |

**`completed_no_data` 时的 `skipReason` 5 类**: `NO_TABLES` / `NARRATIVE_ONLY` / `IMAGE_NO_DATA` / `EMPTY_TABLE` / `INDISTINGUISHABLE_NUMBERS`

#### MSG-3: OcrSimilarityCheckResult
- **Java Handler**: `OcrResultSqsProcessor#handleSimilarityCheckResult`
- **写哪些表**: INSERT `ai_ocr_task_state_log`(SIMILARITY_CHECK_COMPLETE / SIMILARITY_CHECK_FAILED)；不写 `ai_ocr_similarity_hint`（已由 Python 跨域 INSERT）
- **状态变更**:
  - `task.status: SIMILARITY_CHECKING → REVIEWING`（成功）
  - `SIMILARITY_CHECKING → SIMILARITY_CHECK_FAILED`（失败，预留给将来邮件通道，目前不阻塞用户）
- **职责**: 相似度检测完成回执；推进 task 进入用户审核阶段，让前端轮询发现状态变化

#### MSG-4: OcrMemoryLearnProgress
- **Java Handler**: `OcrResultSqsProcessor#handleMemoryLearnProgress`
- **写哪些表**:
  - INSERT `ai_ocr_memory_learn_log`（已由 Python 跨域 INSERT，Java 不重复写）
  - INSERT `ai_ocr_task_state_log`(MEMORY_LEARN_*)
- **状态变更**:
  - `task.status: MEMORY_LEARN_PENDING → MEMORY_LEARN_IN_PROGRESS → COMPLETED`（成功路径）
  - 失败且 `attempt<3` → 回 PENDING 等待重试
  - `attempt≥3` → MEMORY_LEARN_FAILED（fi_* 不回滚）
- **职责**: 记忆学习阶段进度回报（PENDING/IN_PROGRESS/COMPLETE/FAILED 四态），驱动 task 终态切换

**`learnStage` 4 个枚举值**：

| learnStage | 含义 | 前端显示 | 触发时机 |
|-----------|------|---------|---------|
| `PENDING` | 已入队等待 Python 消费 | "记忆学习排队中..." | Java AFTER_COMMIT 发 SQS 后立即写 state_log |
| `IN_PROGRESS` | Python 已开始处理 | "正在学习用户修正..." | Python consumer 拉到消息时回报 |
| `COMPLETE` | 学习成功完成 | "学习完成" | Python 写完 mapping_memory + audit log 后 |
| `FAILED` | 本次尝试失败 | 静默（attempt<3 自动重试）/ "学习失败但财务数据已提交"（attempt≥3）| 业务异常或 DB 异常 |

---

## 4. LangGraph Pipeline 节点详情

> Pipeline 共 5 个核心节点；周期推断（Period Inference）作为 **Extract 节点的尾部子步骤**，不是独立节点。`OCRPipelineState` TypedDict 定义见 [python-design.md §0.4](./python-design.md#04-ocrpipelinestate-typeddict-完整字段定义)。

### NODE-1: Preprocess
- **文件**: `workflow/nodes/preprocess.py`
- **输入 state 字段**: `file_id, file_bytes, content_type, filename`
- **输出 state 字段**:
  - `processed_pages: list[bytes|dict]`（PDF/图片 → Base64 PNG；Excel/CSV → dict）
  - `page_count, ocr_text, has_text_layer`
- **调用的 AI 服务**: eSapiens OCR（仅当扫描件 / 图片型 PDF 且无文本层）；Excel 走 openpyxl/pandas，无 AI 调用
- **失败处理**:
  - eSapiens 503 → 重试 3 次（httpx exponential backoff）
  - 超时 → 抛出让 SQS 重试
  - MIME 不允许 → 直接 `OcrResult{status=failed, error="unsupported_mime"}`
- **职责**: 把 PDF/图片/Excel 转成下游统一可消费的 page list + 提取出可用 OCR 文本，按 MIME 分支决定是否调 eSapiens

### NODE-2: Extract
- **文件**: `workflow/nodes/extract.py`
- **输入 state 字段**: `processed_pages, page_count, ocr_text, document_type_hint?`
- **输出 state 字段**:
  - `tables: list[ExtractedTable]`（含 `rows / reporting_periods / currency / has_extractable_data / extraction_skip_reason / unresolved_period_count`）
  - `skip_downstream: bool`
- **调用的 AI 服务**:
  - 默认: OpenRouter `google/gemini-2.5-flash`（Vision + Instructor 结构化输出，max_retries=3）
  - 复杂场景升级: `anthropic/claude-sonnet-4`
- **失败处理**:
  - LLM 超时/解析失败 → Instructor 自动重试 3 次，仍失败抛出让 SQS 重试
  - 输出无表格但有 OCR 文本 → 走 `classify_extractability` 判定 `skip_reason`
- **职责**: 调用 Vision LLM 把每页转成统一的 `ExtractedTable` Pydantic 模型，并显式判定文档是否含可继续走下游的财务数据
- **尾部子步骤**: 周期推断（4 个信号 fallback：列头 → Sheet 名 → 表格标题 → 文件名）

### NODE-3: Classify
- **文件**: `workflow/nodes/classify.py`
- **输入 state 字段**: `tables`
- **输出 state 字段**:
  - `tables[*].document_type`（PNL/BALANCE_SHEET/CASH_FLOW/PROFORMA/MISC）
  - `classification_confidence`
- **调用的 AI 服务**: 不调 AI（纯本地评分算法：sheet name + row label + 结构线索三路加权）
- **失败处理**: 评分 < 2 → 标记 `MISC` + LOW confidence，**不阻断**下游（用户可在 Review 阶段手动修正）
- **职责**: 用规则评分给每张表打 `document_type` 标签，让 Map 节点能用 document_type 上下文做更准确的映射

### NODE-4: Map
- **文件**: `workflow/nodes/map.py`
- **输入 state 字段**: `tables, company_id, industry, document_type`
- **输出 state 字段**:
  - `mapping_results: list[MappingResult]`（含 `lg_category / confidence / source / reasoning / core_engine_version / company_memory_version`）
  - `unresolved_rows`
- **调用的 AI 服务**: 三层级联
  - Layer 1: 规则引擎（无 AI）
  - Layer 2: 公司记忆 PostgreSQL pg_trgm（无 AI）
  - Layer 3: 行业高频（无 AI）
  - Layer 4: OpenRouter `anthropic/claude-sonnet-4`（仅未命中的批量送入）
- **失败处理**:
  - LLM 超时 → Instructor 重试 3 次后剩余行项标记 `UNMAPPED + LOW`（不阻断 pipeline，让用户审核）
  - DB 故障 → 抛出 SQS 重试
- **职责**: 用三层（规则→记忆→LLM）级联把每行 `account_label` 映射到 19 个 LG 分类之一，并附 `reasoning` 供 Review 阶段审计

### NODE-5: Validate
- **文件**: `workflow/nodes/validate.py`
- **输入 state 字段**: `tables, mapping_results`
- **输出 state 字段**:
  - `validation_warnings: list[ValidationWarning]`
  - `internal_conflicts: list[InternalConflict]`
  - `pipeline_status: REVIEW_READY | FAILED`
- **调用的 AI 服务**: 不调 AI（纯算法 + SQL 内部一致性检查）
- **失败处理**:
  - 三要素硬验证失败（期间/货币/类别完整性缺失）→ 写 `validation_warnings` 但**不阻断**（让 Java 在 Step 3 校验时呈现给用户决定）
  - 行加总不等于合计 → 写 `ai_ocr_conflict_record{conflict_type=INTERNAL_INCONSISTENCY}`
- **职责**: 做"OCR 提取数据**自身**的内部一致性"硬验证，并把警告/内部冲突落库供 Review 阶段决策
- **与 Java §4.10 冲突检测的边界**:
  - **Python validate**: 一份数据是否"自洽"（Assets ≈ Liabilities + Equity，行加总 ≈ 合计）
  - **Java §4.10**: 这份数据与 fi_* 历史数据"打不打架"（同 company + period + LG category 是否冲突）
  - 两者写同一张 `ai_ocr_conflict_record` 但 `conflict_type` 不同

---

## 5. 变更历史

| 日期 | 变更 |
|------|------|
| 2026-05-06 | 初版：从 java-design.md §0 + python-design.md §0 抽取，独立成文（用户指令：接口文档单独列出） |
| 2026-05-06 | 增强 MSG-1/2/4 详细枚举：`OcrProgress.processingStage` 12 阶段表 + `stageDetail` 字段约定、`OcrResult.status` 3 终态语义 + 5 类 skipReason、`OcrMemoryLearnProgress.learnStage` 4 枚举 |
