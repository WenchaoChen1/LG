# OCR Agent 接口文档

> **本文档定位**: OCR Agent 所有接口（REST / SQS / LangGraph 节点）的**唯一权威清单**。
>
> **使用方式**: 先看 §1 总览（一行一个接口） → 需要细节时跳转 §2-§4 详细章节。
>
> **架构边界（2026-05-06 v2 更新）**:
> - 前端**同时**与 Java（上传/提交）+ Python（查询/编辑/验证）直接交互
> - Java↔Python 仅 SQS（不变）
> - 详见 [system-architecture.md §0](./system-architecture.md#0-职责边界声明顶层规则)
>
> **关联文档**: [系统架构](./system-architecture.md) · [数据库 Schema](./database-schema.md) · [Java 设计](./java-design.md)（实现层）· [Python 设计](./python-design.md)（实现层）· [前端设计](./frontend-design.md) · [用户输入](../user-input-requirements.md)

---

## 目录

- [1. 接口总览（快速索引）](#1-接口总览快速索引)
  - [1.1 REST 端点](#11-rest-端点)
  - [1.2 SQS 队列（Java ↔ Python）](#12-sqs-队列java--python)
  - [1.3 LangGraph Pipeline 节点（Python 内部）](#13-langgraph-pipeline-节点python-内部)
- [2. REST 端点详情](#2-rest-端点详情)
  - [Java 端](#java-端)
  - [Python 端](#python-端)
- [3. SQS 接口详情](#3-sqs-接口详情)
  - [3.1 出口队列（Java → Python）](#31-出口队列java--python)
  - [3.2 回传队列（Python → Java）](#32-回传队列python--java)
- [4. LangGraph Pipeline 节点详情](#4-langgraph-pipeline-节点详情)
  - [NODE-1: Preprocess](#node-1-preprocess)
  - [NODE-2: Extract](#node-2-extract)
  - [NODE-3: Classify](#node-3-classify)
  - [NODE-4: Map](#node-4-map)
  - [NODE-5: Validate](#node-5-validate)

---

## 1. 接口总览（快速索引）

### 1.1 REST 端点

> 共 **10 个**用户面向端点（Java 6 + Python 4）+ 1 辅助端点（Java）。Java/Python 都需 JWT + `company_id` 归属校验。

#### 1.1.1 Java 端（用户面向：文件上传 + 最终提交）

| # | URL | 方法 | 用户步骤 | 一句话职责 | 详情 |
|---:|-----|:---:|:---:|----------|:---:|
| 1 | `/tasks/upload-init` | POST | 步骤 1 | 一站式：创建 task + 申请 S3 presigned URL + **预关联公司文件表** | [→](#1-tasksupload-init-post) |
| 2 | `/tasks/{id}/upload-complete` | POST | 步骤 1 | 单文件上传完成（写 `ai_ocr_file`，magic bytes 校验） | [→](#2-tasksidupload-complete-post) |
| 3 | `/tasks/{id}/start-processing` | POST | 步骤 2 | **点 Next 触发**：批量入队所有已上传文件到 `ocr-extract-queue` | [→](#3-tasksidstart-processing-post) |
| 4 | `/tasks/{id}/commit` | POST | 步骤 7 | 写 fi_* + 触发记忆 SQS + 最终化 Imported Statements + 返回 Benchmark 跳转 URL | [→](#4-tasksidcommit-post) |
| 5 | `/tasks/{id}/revise` | POST | — | 任务修订：基于已 COMPLETED task 创建新批次（copy-on-write） | [→](#5-tasksidrevise-post) |

#### 1.1.2 Java 端（辅助）

| # | URL | 方法 | 用途 | 详情 |
|---:|-----|:---:|------|:---:|
| 6 | `/files/{fileId}/download-url` | POST | ReviewPage 渲染 PDF/Excel 时申请 5min S3 presigned GET URL | [→](#6-filesfileiddownload-url-post) |

#### 1.1.3 Python 端（用户面向：查询 + 编辑 + 验证 — **2026-05-06 v2 新边界**）

> Python 端通过 FastAPI 暴露以下端点；前端**直接调用**（不经 Java 中转）。需 JWT 验证 + `company_id` 归属校验。

| # | URL | 方法 | 用户步骤 | 一句话职责 | 详情 |
|---:|-----|:---:|:---:|----------|:---:|
| 7 | `/ocr/tasks/{id}/state` | GET | 步骤 3/5 | **综合状态聚合**：task.status + 文件进度 + 提取数据 + 映射结果 + 相似度提示 + 记忆学习状态 + 历史链 + Mapping Summary（前端轮询的唯一接口） | [→](#7-ocrtasksidstate-get) |
| 8 | `/ocr/tasks/{id}/review` | PATCH | 步骤 4 | 客户变更：编辑 row/mapping + 写 note + **自动检测 mapping 变更触发重映射 SQS** + 接受相似度决策 | [→](#8-ocrtasksidreview-patch) |
| 9 | `/ocr/tasks/{id}/verify` | POST | 步骤 6 | 启动验证：跑冲突检测（读 fi_*）→ 写 `ai_ocr_conflict_record` → 进度通过 `/state` 轮询 | [→](#9-ocrtasksidverify-post) |
| 10 | `/ocr/conflicts/{id}/resolve` | POST | 步骤 6 | 单冲突解决（note 必填，自动写 conflict thread） | [→](#10-ocrconflictsidresolve-post) |

### 1.2 SQS 队列（Java ↔ Python）

> Java↔Python 仅通过 SQS（不变）。详见 [system-architecture.md §0.2](./system-architecture.md#02-java--python-通信仅通过-sqs-队列)。

#### 1.2.1 Java → Python（出口队列）

| 队列 | 触发场景 | 一句话职责 | 详情 |
|------|---------|----------|:---:|
| `ocr-extract-queue` | 步骤 3：用户点 Next 后由 `start-processing` 端点批量入队 | 触发 OCR + AI 提取 + AI 映射；`mode` 字段区分 `FULL_EXTRACT` / `REMAP_ONLY` | [→](#sqs-1-ocr-extract-queue) |
| `ocr-similarity-check-queue` | 内部辅助：所有文件 REVIEW_READY 后 | 触发 embedding + KNN 相似度检测 | [→](#sqs-2-ocr-similarity-check-queue) |
| `ocr-memory-learn-queue` | 步骤 7：`commit` 端点写 fi_* 成功后 AFTER_COMMIT 入队 | 触发记忆学习更新 mapping_memory | [→](#sqs-3-ocr-memory-learn-queue) |

> **注**：原 navigate-back 端点已删除，REMAP_ONLY 触发改由 Python 的 `/review` 端点检测 mapping 变更后内部入队 `ocr-extract-queue`。

#### 1.2.2 Python → Java（回传队列，按 messageType 多路复用）

> 单一队列 `ocr-result-queue`；4 个 messageType 分发到 Java 的 4 个 handler。

| messageType | Handler | 一句话职责 | 详情 |
|-------------|---------|----------|:---:|
| `OcrProgress` | `OcrResultSqsProcessor#handleProgress` | 文件级精细进度上报（每个 stage 一条） | [→](#msg-1-ocrprogress) |
| `OcrResult` | `OcrResultSqsProcessor#handleResult` | 单文件最终结果上报 | [→](#msg-2-ocrresult) |
| `OcrSimilarityCheckResult` | `OcrResultSqsProcessor#handleSimilarityCheckResult` | 相似度检测完成回执 | [→](#msg-3-ocrsimilaritycheckresult) |
| `OcrMemoryLearnProgress` | `OcrResultSqsProcessor#handleMemoryLearnProgress` | 记忆学习进度回报 | [→](#msg-4-ocrmemorylearnprogress) |

### 1.3 LangGraph Pipeline 节点（Python 内部）

> 共 5 个核心节点；周期推断作为 Extract 尾部子步骤。

| 节点 | 文件 | 一句话职责 | 详情 |
|------|------|----------|:---:|
| **Preprocess** | `workflow/nodes/preprocess.py` | PDF/图片/Excel 标准化 | [→](#node-1-preprocess) |
| **Extract** | `workflow/nodes/extract.py` | Vision LLM 提取表格 + 周期推断 + 可提取性判定 | [→](#node-2-extract) |
| **Classify** | `workflow/nodes/classify.py` | 文档类型识别 | [→](#node-3-classify) |
| **Map** | `workflow/nodes/map.py` | 三层级联映射到 19 个 LG 分类 | [→](#node-4-map) |
| **Validate** | `workflow/nodes/validate.py` | OCR 数据自洽性硬验证 | [→](#node-5-validate) |

---

## 2. REST 端点详情

### Java 端

通用约定：所有 Java 端点位于 `/api/v1/docparse` 前缀下；JWT 认证 + `company_id` 归属校验；返回 `Result<T>` 标准包装。

#### 1. /tasks/upload-init (POST)
- **Controller**: `UploadController#initUpload`
- **请求**: `UploadInitReqVo`（`files[]: {filename, fileSize, contentType, sha256}`）
- **响应**: `UploadInitRespVo`（`taskId, uploads[]: {fileId, presignedUrl, expiresAt}, companyDocFolderId`）
- **职责**:
  - 创建 `ai_ocr_task`（status=DRAFT）
  - 每个文件预校验（大小/扩展名/SHA-256 重名）
  - 创建 `ai_ocr_file`（status=PENDING）
  - 生成 S3 presigned PUT URL（15min）
  - **同时预关联公司文件表**（创建 Imported Statements 文件夹占位行，task 完成时再标记可见）

#### 2. /tasks/{id}/upload-complete (POST)
- **Controller**: `UploadController#completeUpload`
- **请求**: `UploadCompleteReqVo`（`fileId, etag, actualSize`）
- **响应**: `{status, error?}`
- **职责**:
  - `s3:HeadObject` 验证对象存在 + magic bytes 校验
  - 成功 → `ai_ocr_file.status=UPLOADED`
  - 失败 → `s3:DeleteObject` + `ai_ocr_file.status=FILE_FAILED`
  - **不入队**（入队动作由步骤 3 `start-processing` 触发）

#### 3. /tasks/{id}/start-processing (POST)
- **Controller**: `UploadController#startProcessing`
- **响应**: `{queuedCount, skippedCount}`
- **职责**:
  - 用户点 "Next" 后调用
  - 批量扫描 task 下所有 `ai_ocr_file.status=UPLOADED` 的文件
  - 每个文件入队 `ocr-extract-queue`（`mode=FULL_EXTRACT`）
  - 推进 `task.status: DRAFT → UPLOAD_COMPLETE → PROCESSING`
  - 写 `ai_ocr_task_state_log`（`event_type=START_PROCESSING`）
- **新增端点**：替代之前每文件 complete 后自动入队的隐式行为

#### 4. /tasks/{id}/commit (POST)
- **Controller**: `CommitController#commit`
- **响应**: `CommitRespVo`（`writtenAccounts, writtenPeriods[], importedStatementsFolderId, benchmarkRedirectUrl`）
- **职责**:
  - FOR UPDATE 锁 task → hard gate 检查（无未解决冲突）
  - Actuals 写 `fi_*` / Proforma 调 `appendVersion`
  - `ai_ocr_commit_audit` 全量审计
  - **AFTER_COMMIT 触发**：
    - 入队 `ocr-memory-learn-queue` → 触发记忆学习
    - 最终化 Imported Statements 文件夹（设为可见）
    - 闭月 email 通知
  - 响应直接含 Benchmark 跳转 URL（前端跳转用，不再有独立 `/commit/result` 端点）

#### 5. /tasks/{id}/revise (POST)
- **Controller**: `ReviseController#reviseTask`
- **请求**: `ReviseReqVo`（`reason`）
- **响应**: `{newTaskId}`
- **职责**:
  - 基于已 COMPLETED/SUPERSEDED task 创建修订版
  - copy-on-write 继承文件 + 提取数据 + 映射
  - 新 task.status=DRAFT，原 task.status=SUPERSEDED
  - **任务修订作为独立批次**：用户在新批次中重新走 4 步流程

#### 6. /files/{fileId}/download-url (POST)
- **Controller**: `FileViewController#getDownloadUrl`
- **响应**: `{url, expiresAt}`
- **职责**: ReviewPage 加载 PDF/Excel 时调用：生成 S3 presigned GET URL（5min）

---

### Python 端

通用约定：所有 Python 端点位于 `/ocr` 前缀下；FastAPI 实现；JWT 中间件 + `company_id` 归属校验；返回标准 JSON。**新边界（2026-05-06 v2）**：前端**直接**调用 Python，不经 Java 中转。

#### 7. /ocr/tasks/{id}/state (GET)
- **Endpoint**: `routes.py#get_task_state` → `services/task_state_service.py#aggregate_state`
- **响应**: `TaskStateResponse`（综合状态聚合）：
  ```
  {
    "task": {id, status, mapping_changed_at, has_extractable_data, ...},
    "files": [{id, status, processing_stage, progress_pct, stage_detail}],
    "extractedData": [{tableId, rows: [...]}],   // 提取结果，供 ReviewPage 渲染
    "mappingResults": [...],                      // AI 映射结果
    "similarityHints": [...],                     // 相似度提示（含 PENDING/MERGED/IGNORED 状态）
    "memoryLearn": {stage, history[], canRetry},  // 记忆学习状态 + 历史 + 是否可重试
    "history": [{taskId, version, completedAt}],  // 任务版本链（修订历史）
    "mappingSummary": {totalFiles, mappedTypes, mappedAccounts, hardGateErrors[]},
    "verifyState": {stage, percent, conflicts[]}  // 验证进度 + 冲突列表（步骤 6 阶段填充）
  }
  ```
- **职责**:
  - **替代原 9 个查询端点的统一聚合接口**：`/status` + `/result` + `/history` + `/mapping-summary` + `/verify/progress` + `/conflicts` + `/similarity-hints` + `/memory-learn` + `/memory-learn/history`
  - 前端按当前 task 状态决定渲染哪个屏幕（DRAFT → 上传页；PROCESSING → 进度页；REVIEWING → 审核页；CONFLICT_RESOLUTION → 冲突页；MEMORY_LEARN_* → 成功页）
  - 实现：单次 DB 查询聚合多表（task + files + extracted + mapping + hints + memory_log + state_log）

#### 8. /ocr/tasks/{id}/review (PATCH)
- **Endpoint**: `routes.py#patch_review` → `services/review_service.py#apply_changes`
- **请求**: `ReviewPatchRequest`：
  ```
  {
    "rowEdits": [{rowId, accountLabel?, cellValues?, deleted?}],
    "mappingEdits": [{rowId, lgCategory, userNote?}],
    "similarityDecisions": [{hintId, decision: "MERGED" | "IGNORED"}],
    "conflictNotes": [{conflictId, parentNoteId?, content}]   // 追加 note thread
  }
  ```
- **响应**: `{updatedRowCount, updatedMappingCount, remapTriggered: bool}`
- **职责**:
  - 写 `ai_ocr_extracted_row` / `ai_ocr_mapping_result` / `ai_ocr_similarity_hint` / `ai_ocr_conflict_note`
  - **自动变更检测**：对比当前 mapping snapshot hash
    - 有变化 → 清空已解决冲突 + 入队 `ocr-extract-queue`（mode=REMAP_ONLY）+ 响应 `remapTriggered=true`
    - 无变化 → 仅写编辑数据
  - **替代之前的 navigate-back 端点**：变更检测内嵌
  - 写 `ai_ocr_task_state_log`（`event_type=MAPPING_EDITED`）

#### 9. /ocr/tasks/{id}/verify (POST)
- **Endpoint**: `routes.py#start_verify` → `services/verify_service.py#run_verification`
- **响应**: `{verifyJobId, status: "RUNNING"}`
- **职责**:
  - 推进 `task.status: REVIEWING → VERIFYING`
  - 异步跑冲突检测（**Python 读 fi_***：对比每个 (company, lg_category, period) 是否有现存值）
  - 检测到冲突 → 写 `ai_ocr_conflict_record`（status=PENDING）
  - 完成后 `task.status: VERIFYING → CONFLICT_RESOLUTION`（有冲突）/ `→ READY_TO_COMMIT`（无冲突）
  - 进度通过 `/state` 轮询
- **新增能力**: Python 需要 SELECT 权限读 `fi_*`（架构边界 §0.5 更新）

#### 10. /ocr/conflicts/{id}/resolve (POST)
- **Endpoint**: `routes.py#resolve_conflict` → `services/conflict_service.py#resolve_one`
- **请求**: `ResolveRequest`（`action: "OVERWRITE" | "SKIP"`, `note: str(必填非空)`）
- **响应**: `ResolveResponse`（`nextConflictId?`，自动 Save & Next 导航）
- **职责**:
  - Note 必填硬校验（length(trim(note)) > 0）
  - 写 `ai_ocr_conflict_record.resolution` + 自动追加 `ai_ocr_conflict_note`（auto_generated=false）
  - 计算下一冲突定位（同 metric 内按月份从左到右；跨 metric 按顺序）
  - 全部解决后 → `task.status: CONFLICT_RESOLUTION → READY_TO_COMMIT`

---

## 3. SQS 接口详情

### 3.1 出口队列（Java → Python）

#### SQS-1: ocr-extract-queue
- **Producer**: `OcrExtractSqsProducer`（Java）
- **消息 DTO**: `OcrExtractMessage`
- **触发时机**:
  - (a) `/tasks/{id}/start-processing` 端点：批量入队 task 下所有 UPLOADED 文件（`mode=FULL_EXTRACT`）
  - (b) Python `/review` 端点：检测到 mapping 变更时由 Python 内部触发（**Python 也是 producer，但通过共享 SQS API**，`mode=REMAP_ONLY`）
- **关键字段**:
  - `messageType=OcrExtract`
  - `mode`: `FULL_EXTRACT` / `REMAP_ONLY`
  - `taskId / fileId / companyId`
  - `s3Bucket / s3Key / filename / contentType / fileSize`
  - `uploadedBy / callbackMeta`
- **Python 消费者**: `consumers/extract_consumer.py#handle_extract_message`
- **职责**:
  - `FULL_EXTRACT`: 全量走 OCR/Extract/Classify/Map/Validate（约 30-60s）
  - `REMAP_ONLY`: 仅重跑 Map 节点（约 1-10s）

#### SQS-2: ocr-similarity-check-queue
- **Producer**: `OcrSimilarityCheckSqsProducer`（Java）
- **消息 DTO**: `OcrSimilarityCheckRequest`
- **触发时机**: task 内所有非 FAILED 文件 `REVIEW_READY` 时（在 Java 收到 `OcrResult` 计数完成判定后）
- **Python 消费者**: `consumers/similarity_check_consumer.py#handle_similarity_check`
- **职责**: embedding + pgvector HNSW KNN → 写 `ai_ocr_similarity_hint`

#### SQS-3: ocr-memory-learn-queue
- **Producer**: `OcrMemoryLearnSqsProducer`（Java）
- **消息 DTO**: `OcrMemoryLearnMessage`
- **触发时机**: `/tasks/{id}/commit` 事务 AFTER_COMMIT 阶段
- **关键字段**:
  - `messageType=OcrMemoryLearn`
  - `taskId / fileId / companyId`
  - `mappingComparisons[]`（`accountLabel / originalAiCategory / confirmedCategory / wasOverridden`）
  - `attemptNumber`
- **Python 消费者**: `consumers/memory_learn_consumer.py#handle_memory_learn`
- **职责**: 仅学习 `wasOverridden=true` 的条目，写 `ai_ocr_mapping_memory` + 双重日志

### 3.2 回传队列（Python → Java）

> 单一队列 `ocr-result-queue`，按 `messageType` 多路复用到 Java `OcrResultSqsProcessor` 4 个 handler。

#### MSG-1: OcrProgress
- **Java Handler**: `OcrResultSqsProcessor#handleProgress`
- **写哪些表**: UPDATE `ai_ocr_file`(`processing_stage` / `progress_pct` / `stage_detail` JSONB)
- **状态变更**:
  - `file.status: QUEUED → PROCESSING`（首次到达时）
  - `task.status: UPLOAD_COMPLETE → PROCESSING`（首次到达时，CAS）
- **职责**: 文件级精细进度上报；幂等去重靠 `processing_stage` ordinal

**`processingStage` 12 个枚举值**：

| Stage | 进度 | 对应节点 | 前端显示 |
|-------|---:|---------|---------|
| `QUEUED` | 0% | — | "已入队" |
| `PREPROCESS_PENDING` | 1-5% | Preprocess（开始）| "准备解析" |
| `PREPROCESSING` | 6-15% | Preprocess（执行）| "格式转换中" |
| `EXTRACTING` | 16-50% | Extract | "AI 识别表格" |
| `MAPPING_RULE_LAYER` | 51-60% | Map（Layer 1）| "应用业务规则" |
| `MAPPING_MEMORY_LOOKUP` | 61-70% | Map（Layer 2）| "查询历史记忆" |
| `MAPPING_INDUSTRY_LAYER` | 71-78% | Map（Layer 3）| "应用行业模板" |
| `MAPPING_LLM_FALLBACK` | 79-90% | Map（Layer 4）| "AI 智能映射" |
| `VALIDATING` | 91-95% | Validate | "校验数据一致性" |
| `PERSISTING` | 96-99% | — | "保存结果" |
| `REVIEW_READY` | 100% | — | "可审核" |
| `FAILED` | — | — | 显示错误 |

#### MSG-2: OcrResult
- **Java Handler**: `OcrResultSqsProcessor#handleResult`
- **职责**: 单文件最终结果上报；FOR UPDATE 锁 task 行做计数；全部完成 → 进入相似度检测阶段

**`status` 三个终态**：

| status | 含义 | file 终态 | state_log event_type |
|--------|------|----------|---------------------|
| `completed` | 解析成功，含可提取财务数据 | `REVIEW_READY` | `EXTRACT_COMPLETE` |
| `completed_no_data` | 解析成功，无可提取财务数据 | `REVIEW_READY` | `EXTRACT_NO_DATA`（含 `skipReason`）|
| `failed` | 解析失败 | `FILE_FAILED` | `EXTRACT_FAILED` |

**`skipReason` 5 类**: `NO_TABLES` / `NARRATIVE_ONLY` / `IMAGE_NO_DATA` / `EMPTY_TABLE` / `INDISTINGUISHABLE_NUMBERS`

#### MSG-3: OcrSimilarityCheckResult
- **Java Handler**: `OcrResultSqsProcessor#handleSimilarityCheckResult`
- **状态变更**: `task.status: SIMILARITY_CHECKING → REVIEWING`
- **职责**: 相似度检测完成回执，推进 task 进入用户审核阶段

#### MSG-4: OcrMemoryLearnProgress
- **Java Handler**: `OcrResultSqsProcessor#handleMemoryLearnProgress`
- **状态变更**: `MEMORY_LEARN_PENDING → IN_PROGRESS → COMPLETED` / `FAILED`
- **职责**: 记忆学习阶段进度回报，驱动 task 终态切换

**`learnStage` 4 个枚举**：

| learnStage | 含义 | 前端显示 |
|-----------|------|---------|
| `PENDING` | 已入队等待 Python 消费 | "记忆学习排队中..." |
| `IN_PROGRESS` | Python 已开始处理 | "正在学习用户修正..." |
| `COMPLETE` | 学习成功完成 | "学习完成" |
| `FAILED` | 本次尝试失败 | 静默或"学习失败但财务数据已提交" |

---

## 4. LangGraph Pipeline 节点详情

> Pipeline 共 5 个核心节点；周期推断（Period Inference）作为 Extract 节点的尾部子步骤，不是独立节点。

### NODE-1: Preprocess
- **文件**: `workflow/nodes/preprocess.py`
- **输入 state**: `file_id, file_bytes, content_type, filename`
- **输出 state**: `processed_pages, page_count, ocr_text, has_text_layer`
- **AI 服务**: eSapiens OCR（仅扫描件 / 图片型 PDF 且无文本层）；Excel 走 openpyxl/pandas
- **失败处理**: eSapiens 503 → 重试 3 次；超时 → SQS 重试；MIME 不允许 → `OcrResult{status=failed}`
- **职责**: 把 PDF/图片/Excel 转成下游统一可消费的 page list + 提取 OCR 文本

### NODE-2: Extract
- **文件**: `workflow/nodes/extract.py`
- **输入 state**: `processed_pages, page_count, ocr_text, document_type_hint?`
- **输出 state**: `tables[], skip_downstream`
- **AI 服务**: OpenRouter `google/gemini-2.5-flash`（Vision + Instructor）；复杂场景升级 `claude-sonnet-4`
- **失败处理**: LLM 超时 → Instructor 自动重试 3 次；无表格 → 走可提取性判定
- **尾部子步骤**: 周期推断（4 个信号 fallback：列头 → Sheet 名 → 表格标题 → 文件名）
- **职责**: 调 Vision LLM 把每页转成 `ExtractedTable` Pydantic 模型，并显式判定文档是否含可继续走下游的财务数据

### NODE-3: Classify
- **文件**: `workflow/nodes/classify.py`
- **输入 state**: `tables`
- **输出 state**: `tables[*].document_type, classification_confidence`
- **AI 服务**: 不调 AI（纯本地评分算法）
- **失败处理**: 评分 < 2 → `MISC` + LOW，不阻断
- **职责**: 用规则评分给每张表打 `document_type` 标签

### NODE-4: Map
- **文件**: `workflow/nodes/map.py`
- **输入 state**: `tables, company_id, industry, document_type`
- **输出 state**: `mapping_results[], unresolved_rows`
- **AI 服务**: 三层级联（规则 → 公司记忆 → 行业高频 → LLM）
- **失败处理**: LLM 超时后剩余行项标记 `UNMAPPED + LOW`
- **职责**: 三层级联把每行 `account_label` 映射到 19 个 LG 分类之一

### NODE-5: Validate
- **文件**: `workflow/nodes/validate.py`
- **输入 state**: `tables, mapping_results`
- **输出 state**: `validation_warnings[], internal_conflicts[], pipeline_status`
- **AI 服务**: 不调 AI（纯算法 + SQL 内部一致性）
- **失败处理**: 三要素硬验证失败 → 写 warnings 但不阻断
- **职责**: OCR 提取数据**自身**的内部一致性硬验证（与 Java fi_* 跨期间冲突检测互不重叠）
