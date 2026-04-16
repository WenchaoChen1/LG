# OCR Agent 系统架构设计 — Java + Python + SQS 协作

> **关联文档**: [设计理念](./design-philosophy.md) · [技术设计](./technical-design.md) · [代码示例](./code-examples.md) · [需求分析](./requirement-analysis.md)
> **创建日期**: 2026-04-16

---

## 1. 整体数据流

```
用户                    Java (CIOaas-api)              SQS                Python (CIOaas-python)
────                   ─────────────────              ───                ──────────────────────

上传文件 ───────────→  ① 校验文件 (MIME+大小)
                       ② 存入 S3
                       ③ 写入 doc_parse_task 表
                       ④ 发送 SQS 消息 ──────────→  ocr-extract-queue
                       ⑤ 返回 202 {taskId}                              ⑥ 消费消息
                                                                        ⑦ 从 S3 下载文件
                                                                        ⑧ AI 提取 + 映射
                                                                        ⑨ 结果写入 ai_ocr_* 表
前端轮询状态 ────────→  ⑩ 查询 task 状态         ←── ocr-result-queue ←─ ⑪ 发送完成消息
                       ⑫ 更新 task 状态
                       ⑬ 返回提取结果
                       
用户审核编辑 ────────→  ⑭ 保存编辑内容

用户确认提交 ────────→  ⑮ 写入 fi_* 财务表（最终数据）
                       ⑯ 触发下游 Normalization
```

**核心原则**: Java 管生命周期（上传、状态、确认），Python 管 AI 处理（提取、映射、记忆）。通过 SQS 解耦，互不直接调用。

---

## 2. 职责边界

| 职责 | Java (CIOaas-api) | Python (CIOaas-python) |
|------|-------------------|----------------------|
| 文件上传 + S3 存储 | **Owner** | — |
| 文件校验 (MIME/大小/恶意文件) | **Owner**（上传时，S3 写入前） | — |
| Task 生命周期管理 | **Owner**（创建、状态跟踪） | 通过 SQS 回调更新状态 |
| SQS 消息生产 (extract) | **Owner** | — |
| SQS 消息消费 (extract) | — | **Owner** (aioboto3) |
| S3 文件下载用于处理 | — | **Owner**（按 s3Key 只读） |
| AI 提取 + 映射 | — | **Owner** |
| 提取结果存储 (ai_ocr_* 表) | 只读 | **Owner** |
| SQS 结果回调 (result) | **消费**（更新 task 状态） | **生产** |
| 用户审核数据服务 | **Owner**（读取 + 返回前端） | — |
| 最终确认写入 fi_* 表 | **Owner** | — |
| 认证 + 授权 | **Owner** | —（信任 SQS 消息来源） |
| 映射记忆管理 | — | **Owner** |

---

## 3. Java 端模块设计

### 3.1 包结构

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

### 3.2 与现有模块的集成点

| 集成点 | 文件 | 操作 |
|--------|------|------|
| SQS 队列注册 | `InitSqsQueueEnum.java` | 新增 `OcrExtractQueue`, `OcrResultQueue` |
| SQS 消息类型 | `SqsMessageType.java` | 新增 `OcrExtract`, `OcrResult` |
| SQS 监听 | `SQSMessageListener.java` | 新增 `ocr-result-queue` 的 `@SqsListener` |
| 文件上传 | `FileServiceImpl.java` | 复用现有 S3 上传能力 |
| 消息处理器 | `MessageProcessorManager.java` | 注册 `OcrResultProcessor` |

### 3.3 Java 端 API

```
POST   /api/v1/docparse/upload              # 上传文件（multipart）
GET    /api/v1/docparse/tasks/{id}/status    # 轮询处理状态
GET    /api/v1/docparse/tasks/{id}/result    # 获取提取结果
PATCH  /api/v1/docparse/tasks/{id}/review    # 保存用户编辑
POST   /api/v1/docparse/tasks/{id}/confirm   # 确认写入 fi_* 表
```

---

## 4. SQS 消息设计

### 4.1 队列拓扑

```
Java (Producer)                              Python (Consumer)
──────────────                               ──────────────────

  OcrSqsProducer ──→ ocr-extract-queue ──→ SQS Consumer (aioboto3)
                                                    │
  OcrResultProcessor ←── ocr-result-queue ←─────────┘
  
  共享: dlq-queue（两个队列都 redrive 到这里）
```

**一条消息对应一个文件**（不是一个 session）。原因：独立重试、天然并发、部分失败隔离。`sessionId` 字段用于前端聚合。

### 4.2 消息 Schema

**Java → Python (ocr-extract-queue)**

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

**Python → Java (ocr-result-queue)**

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

### 4.3 队列配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `visibilityTimeout` | 300s (5 分钟) | 50 页 PDF 处理需要 ~60s，留足余量 |
| `maxReceiveCount` | 3 | 3 次重试后进 DLQ |
| `messageRetentionPeriod` | 345600s (4 天) | 与现有队列一致 |
| DLQ | 共享 `dlq-queue` | 通过 `messageType=OcrExtract` 区分 |

### 4.4 错误处理

| 场景 | 处理方式 |
|------|----------|
| Python 处理中崩溃 | 消息不可见超时后重新出现，SQS 自然重试 |
| AI 模型超时 | Python 捕获异常，发送 `status=failed` 结果消息 |
| 瞬态故障（S3 读取、网络） | SQS 重试（最多 3 次，指数退避） |
| 所有重试耗尽 | 进 DLQ，Java 通过 `QueueMessageLog.isDlq=true` 追踪 |
| 结果消息发送失败 | Python 直接写 DB 状态；Java 轮询时 fallback 查 Python 表 |

---

## 5. Python 端 AI 处理设计

Python 端负责 AI 提取和映射两大核心能力：

- **文件类型路由**: PDF/图片走 AI Vision，Excel/CSV 直接解析（零 AI 成本）
- **大文件处理**: PDF 逐页并发提取（`asyncio.Semaphore(5)`），每页独立失败/重试
- **三层映射引擎**: 规则引擎（~60%）→ 公司记忆（~25%）→ LLM 推理（~15%），仅 15% 行项产生 AI 成本
- **模型路由**: 提取用 Gemini Flash（低成本），映射用 Claude Sonnet（高质量）

> **详细设计**: AI 提取引擎、三层映射架构、模型路由策略、映射规则等完整设计见 [technical-design.md](./technical-design.md) 第 5-6 章。

---

## 6. 记忆系统设计

### 6.1 两层架构

```
┌──────────────────────────────────────────────┐
│               mapping_memory 表               │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │ Tier 1: 通用层 (company_id = NULL)       │ │
│  │ ~500 条种子数据 + 管理员维护              │ │
│  │ 所有公司共享                              │ │
│  │ 例: "revenue" → Gross Revenue             │ │
│  ├─────────────────────────────────────────┤ │
│  │ Tier 2: 公司层 (company_id = 具体值)     │ │
│  │ 每公司最多 5,000 条                       │ │
│  │ 用户确认/修正时自动学习                    │ │
│  │ 例: "AWS Infra" → COGS (SaaS 公司 A)     │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

**为什么是同一张表？** 一条 SQL 查询，`COALESCE` 降级，公司结果优先于通用结果。分两张表则需要两次查询 + 应用层合并。

### 6.2 查询策略

公司优先，通用降级，单次查询：

```sql
SELECT DISTINCT ON (source_term)
    source_term, normalized_category, confidence, is_trusted, source
FROM mapping_memory
WHERE source_term = ANY(:terms)
  AND (company_id = :company_id OR company_id IS NULL)
  AND archived_at IS NULL
  AND is_trusted = TRUE
ORDER BY source_term,
         company_id NULLS LAST,   -- 公司记忆优先于通用记忆
         confidence DESC;
```

`NULLS LAST` 确保公司记忆总是覆盖通用记忆。批量查询（一次 50-200 个标签）一个 round trip。

### 6.3 存储限制

| 层级 | 上限 | 满时策略 |
|------|------|----------|
| 通用层 | ~500 条 | 仅管理员维护，不自动增长 |
| 公司层 | 5,000 条/公司 | 淘汰 `hit_count` 最低 + `is_trusted = FALSE` 的最旧条目 |

### 6.4 信任提升规则

记忆从 `is_trusted = FALSE` 变为 `TRUE` 的条件：

| 条件 | 说明 |
|------|------|
| `source = 'seed'` | 种子数据，预审通过 |
| `confirm_count >= 2` | 至少 2 次独立用户确认 |
| `confirm_count >= 1 AND reject_count = 0` | 1 次确认且无人反对 |
| 管理员手动设置 | 通用层覆盖 |

### 6.5 冲突解决

当用户修正与已有记忆矛盾时：

1. 已有记忆 `reject_count += 1`
2. 若 `reject_count >= confirm_count` → 设 `is_trusted = FALSE` + 软删除
3. 新映射插入，`confirm_count = 1`，`is_trusted = FALSE`（需再次达到信任阈值）

**多用户冲突**: 用户 A 映射为 COGS，用户 B 映射为 R&D → 旧记忆归档，新记忆需重新达到信任阈值。最近的人类决策为准。

### 6.6 种子数据

预装 ~120 条通用记忆，覆盖现有 `FieldMapper` 关键词表：

```
source_term          → normalized_category      confidence
────────────────────────────────────────────────────────────
revenue              → Gross Revenue            1.0
sales                → Gross Revenue            1.0
subscriptions        → Gross Revenue            0.95
refund               → Revenue Contra           1.0
cogs                 → COGS                     1.0
cost of goods        → COGS                     1.0
materials            → COGS                     0.9
rent                 → Operating Expenses       1.0
marketing            → Operating Expenses       1.0
wages                → Payroll Expense          1.0
salary               → Payroll Expense          1.0
cash                 → Cash                     1.0
accounts receivable  → Accounts Receivable      1.0
accounts payable     → Accounts Payable         1.0
long-term debt       → Long-Term Debt           1.0
... (~120 条)
```

### 6.7 记忆生命周期

| 事件 | 操作 |
|------|------|
| 创建 | `created_at = now()`，按信任规则设 `is_trusted` |
| 命中 | `hit_count += 1`，`updated_at = now()` |
| 用户确认 | `confirm_count += 1`，重算 `is_trusted` |
| 用户拒绝 | `reject_count += 1`，重算 `is_trusted`，可能归档 |
| 软删除 | `archived_at = now()`，查询自动排除 |
| TTL | 无自动删除。18 个月未命中的标记待审核（月度 cron） |

### 6.8 审计

每次 `mapping_memory` 变更都产生一条审计记录：

```
mapping_memory_audit 表:
  mapping_id, event_type, old_category, new_category,
  actor (用户/系统), reason, metadata (upload_id, session_id),
  created_at
```

---

## 7. 表归属

### 7.1 Java 拥有的表

| 表 | 用途 |
|----|------|
| `doc_parse_task` | Task 元数据：company_id, user_id, file_id, s3_key, status |
| `file_objects` (现有) | S3 文件记录，复用 storage 模块 |
| `fi_*` (现有) | 最终确认的财务数据 |

### 7.2 Python 拥有的表

| 表 | 用途 |
|----|------|
| `ai_ocr_extracted_table` | 提取的表格结构 |
| `ai_ocr_extracted_row` | 提取的行数据 |
| `ai_ocr_mapping_result` | AI 映射结果 |
| `mapping_memory` | 两层映射记忆（通用+公司） |
| `mapping_memory_audit` | 记忆变更审计日志 |

### 7.3 数据库隔离

| 角色 | 权限 |
|------|------|
| `java_app` | 完全访问 Java 拥有的表 + `SELECT` 权限访问 Python 表 |
| `python_worker` | 完全访问 Python 拥有的表 + `SELECT` 权限访问 `doc_parse_task`（查状态） + 零权限访问 `fi_*` 表 |

---

## 8. 状态通知方案

**轮询（Polling）** — 不用 WebSocket，不用 SNS。

理由：
- 现有前端 (Ant Design Pro + dva) 轮询模式成熟
- 处理时间 10-60 秒，2 秒间隔轮询完全可接受
- 简单可靠，无额外基础设施

```
前端                     Java                           Python
────                    ────                           ──────
POST /docparse/upload
                        → S3 + task(PENDING) + SQS
                        ← 202 {taskId}

GET /docparse/tasks/{id}/status  (每 2 秒)
                        → 查 doc_parse_task 表
                        ← {status: "processing", progress: 30%}

                        ← (SQS result 到达)
                        → 更新 task 状态 = completed

GET /docparse/tasks/{id}/status
                        ← {status: "completed"}

GET /docparse/tasks/{id}/result
                        → 查 ai_ocr_* 表
                        ← {tables: [...], mappings: [...]}
```

---

## 9. 安全设计

### 9.1 现有代码中发现的安全问题（必须修复）

| 问题 | 严重级别 | 位置 | 修复方案 |
|------|---------|------|----------|
| 上传端点 `@AnonymousAccess` 无认证 | **CRITICAL** | `FileController.java` | 移除 `@AnonymousAccess`，加 JWT 认证 |
| 无 MIME 类型校验就写入 S3 | HIGH | `FileServiceImpl.java` | 上传时校验扩展名 + magic bytes |
| SQS 消息无签名 | HIGH | `SqsMessage.java` | 加 HMAC-SHA256 签名字段 |
| 静态 IAM 密钥而非实例角色 | HIGH | `S3AutoConfiguration.java` | 改为 EC2/ECS 实例角色 |
| 跨服务 DB 无角色隔离 | HIGH | 数据库配置 | 分 `java_app` / `python_worker` 角色 |
| SQS 消息中 companyId 未做归属校验 | HIGH | `SQSMessageListener.java` | 消费前校验 file → company 归属 |
| Python `file_url` 接受任意 URL (SSRF) | MEDIUM | `routes.py` | 限制为 S3 域名白名单 |
| 财务数据发送到外部 LLM | MEDIUM | `langchain_service.py` | 确认 OpenRouter DPA + 脱敏公司标识 |

### 9.2 S3 权限划分

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

S3 key 按公司隔离：`ocr-uploads/{companyId}/{sessionId}/{fileId}/filename`

---

## 10. 并发与扩展

| 场景 | 方案 |
|------|------|
| 100 文件同时上传 | 每文件一条 SQS 消息，SQS 自然处理背压 |
| Python 并发控制 | `asyncio.Semaphore(5)` — 每实例最多 5 个并发提取 |
| SQS 可见性超时 | 300s (5 分钟)，长时任务用心跳延长 |
| 横向扩展 | 加 Python 实例即可，SQS 自动分配消息 |
| 批量上传 UX | 前端按文件追踪状态，session 下所有文件 completed/failed 后聚合 |

---

## 11. 开发分期（更新版）

| Phase | Java 工作 | Python 工作 | 前端工作 |
|-------|-----------|-------------|----------|
| **1 (MVP)** | docparse 模块 + 上传 + SQS 生产 + 状态 API | SQS 消费 + Excel 直接解析 + 规则引擎映射 | 上传页 + 状态轮询 |
| **2** | 确认写入 fi_* + 冲突检测 API | AI Vision 提取 (PDF/图片) + LLM 映射 | 并排审核页 + 内联编辑 |
| **3** | 审核编辑 PATCH API | 记忆系统 + Few-Shot 注入 + 冲突解决 | 冲突解决页 + Note 字段 |
| **4** | 安全加固 (认证/IAM/DB 隔离) | 大文件优化 + 质量检测 + 性能调优 | Mobile 上传适配 |
