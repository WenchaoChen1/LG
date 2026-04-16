# OCR Agent Java 端设计 (CIOaas-api)

> **技术栈**: Java 17 + Spring Boot 3 + Spring Cloud Gateway + AWS S3/SQS
> **关联文档**: [系统架构](./system-architecture.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md)

---

## 1. 模块结构

### 1.1 包结构

在现有 DDD 结构下新增 `docparse` 域（与 `fi/`、`quickbooks/`、`storage/` 同级）：

```
com.gstdev.cioaas.web.docparse/
  controller/
    DocParseController.java           # upload + status + confirm 端点
  service/
    DocParseService.java              # 接口
    DocParseServiceImpl.java          # 上传→S3、创建 task、发 SQS
  repository/
    DocParseTaskRepository.java       # JPA: task 元数据
  domain/
    DocParseTask.java                 # Entity: task 生命周期 + S3 引用
  contract/
    DocParseUploadResponse.java       # 上传响应 DTO
    DocParseTaskStatusResponse.java   # 状态轮询响应 DTO
    DocParseResultResponse.java       # 提取结果 DTO
    DocParseSqsMessageDto.java        # SQS 消息 DTO
    DocParseConfirmRequest.java       # 用户确认请求 DTO
  enums/
    DocParseStatus.java               # PENDING / PROCESSING / COMPLETED / FAILED
    DocParseFileType.java             # PDF / EXCEL / CSV / IMAGE
  infrastructure/
    processor/
      OcrSqsProducer.java            # 发送 SQS extract 消息
      OcrResultProcessor.java        # 消费 SQS result 消息（implements MessageProcessor）
```

### 1.2 与现有模块的集成点

| 集成点 | 文件 | 操作 |
|--------|------|------|
| SQS 队列注册 | `InitSqsQueueEnum.java` | 新增 `OcrExtractQueue`, `OcrResultQueue` |
| SQS 消息类型 | `SqsMessageType.java` | 新增 `OcrExtract`, `OcrResult` |
| SQS 监听 | `SQSMessageListener.java` | 新增 `ocr-result-queue` 的 `@SqsListener` |
| 文件上传 | `FileServiceImpl.java` | 复用现有 S3 上传能力 |
| 消息处理器 | `MessageProcessorManager.java` | 注册 `OcrResultProcessor` |

---

## 2. API 端点

```
POST   /api/v1/docparse/upload              # 上传文件（multipart）
GET    /api/v1/docparse/tasks/{id}/status    # 轮询处理状态
GET    /api/v1/docparse/tasks/{id}/result    # 获取提取结果
PATCH  /api/v1/docparse/tasks/{id}/review    # 保存用户编辑
POST   /api/v1/docparse/tasks/{id}/confirm   # 确认写入 fi_* 表
```

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
    filename        VARCHAR(500) NOT NULL,
    file_type       VARCHAR(10) NOT NULL,
    file_size       BIGINT NOT NULL,
    s3_bucket       VARCHAR(200) NOT NULL,
    s3_key          VARCHAR(1000) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.3 索引

```sql
-- 扩展
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- Java 端索引
CREATE INDEX idx_doc_parse_task_company
    ON doc_parse_task (company_id, created_at DESC);

CREATE INDEX idx_doc_parse_file_task
    ON doc_parse_file (task_id, status);
```

---

## 4. SQS 集成

### 4.1 发送提取消息 (OcrSqsProducer -> ocr-extract-queue)

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

### 4.2 消费结果消息 (OcrResultProcessor <- ocr-result-queue)

Python 端完成 AI 提取和映射后，向 `ocr-result-queue` 发送结果消息。Java 端 `OcrResultProcessor`（通过 `@SqsListener` 注册在 `SQSMessageListener.java`）消费此消息，更新 `doc_parse_task` 表状态。

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

### 4.3 发送记忆学习消息 (MemoryLearnProducer -> ocr-memory-learn-queue)

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
    → ② 存入 S3 (ocr-uploads/{companyId}/{sessionId}/{fileId}/filename)
    → ③ 创建 doc_parse_task 记录 (status=PENDING)
    → ④ 创建 doc_parse_file 记录
    → ⑤ 发送 SQS 消息到 ocr-extract-queue (每文件一条)
    → ⑥ 返回 202 {taskId, sessionId}
```

**关键细节**:
- 文件校验在 S3 写入前执行（扩展名 + magic bytes 双重校验）
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

### 5.4 确认提交

```
用户确认提交
    → POST /api/v1/docparse/tasks/{id}/confirm
    → ① 读取 ai_ocr_extracted_row + ai_ocr_mapping_result (最终数据)
    → ② 写入 fi_* 财务表（最终确认数据）
    → ③ 触发下游 Normalization 流程
    → ④ 构建 mappingComparisons (对比 original_ai_suggestion vs 最终确认)
    → ⑤ 发送 SQS 消息到 ocr-memory-learn-queue
    → ⑥ 返回 200 {success: true}
```

**关键细节**:
- 记忆学习在 fi_* 写入成功后触发（不是审核编辑时）
- `mappingComparisons` 通过对比 `ai_ocr_mapping_result.original_ai_suggestion` 与最终确认的分类来构建
- 只有 `wasOverridden: true` 的条目才会被 Python 端学习

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

`OcrResultProcessor` 消费结果消息时，必须校验 `fileId` 对应的 `doc_parse_file` 记录的 `task_id` → `doc_parse_task.company_id` 与消息中的 `companyId` 一致，防止跨公司数据越权。

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
