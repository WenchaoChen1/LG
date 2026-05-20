# Python AI 服务 ↔ Java CIOaas 集成边界

> 本文档明确 AI Chatbot 功能的服务边界。
>
> **总原则**：所有 AI Chatbot 业务全部由 **Python 服务**承担（编排、RAG、Memory、Chat History、问答、Layer 2 摄取）。
> Java 侧 **唯一职责**：作为 **文件上传通道**——前端把文档传到 Java 现有上传接口，Java 落 S3、写元数据表，并通过 **SQS 事件** 通知 Python 拉文件解析。
> 其他业务数据（Company Settings / Normalization Table / Benchmark / ACL / 用户身份）由 **Python 通过共享 PostgreSQL 的只读账号直接读取**，不再走 Java REST。
>
> 编写日期：2026-05-07
> 最近更新：2026-05-12（架构调整：Java 仅保留文件上传，其他通信改为 DB 直读 + SQS）

---

## 1. 设计原则

| # | 原则 | 含义 |
|---|------|------|
| P1 | **单一职责** | Python 全栈拥有 AI Chatbot 功能；Java 仅维护文件上传通道与 SQS 推送 |
| P2 | **数据库读写隔离** | 共享 PostgreSQL，但 Python 仅用 **只读角色** 读取 Java 写入的业务表；写权限只在 Java 拥有；Python 自有表（memory_entries、kb_chunks、chat_threads、langgraph_checkpoints 等）由 Python 独占读写 |
| P3 | **JWT 共用签名密钥** | Python 与 Java 共用 JWT 签名密钥，Python 直接验签、解析 claims，不再回调 Java `/me` |
| P4 | **Java 不感知 LLM** | Java 只接收文件、入库、发 SQS；不知道文件被怎么用 |
| P5 | **变更走 SQS 事件** | 业务表数据变化（公司创建、Settings 更新、ACL 变更、文件上传完成）由 Java 推 SQS，Python 异步消费 |
| P6 | **Python 自管缓存** | 高频读的 ACL / Company Settings 在 Python 端用 Redis 缓存，TTL ≤ 5 分钟；SQS 事件到来时立刻清 |
| P7 | **失败降级而非拒绝** | DB / S3 / LLM 任一失败时给最后已知数据 + 显著免责，不进入幻觉 |
| P8 | **接口契约最小化** | Java 不为 AI Chatbot 新建任何 `/api/internal/*` REST 接口——只复用现有文件上传接口 + 既有的 SQS 通知机制 |

---

## 2. 数据归属与访问方式

| 数据 | 写入方 | 存储位置 | Python 如何获得 |
|------|--------|---------|----------------|
| 用户认证 / 角色 | Java | PG（Java 业务表，如 `sys_user` / `sys_role`） | **PG 只读账号 + JWT claims** |
| 用户 ACL / accessible_companies | Java | PG（如 `r_user_company`、`r_company_group`） | **PG 只读账号**，按 user_id 查询；JWT 也带核心 claims |
| Company Settings（name / description / industry / stage / type） | Java | PG（`r_company` 等） | **PG 只读账号** + SQS `company.settings.updated` 事件 |
| Normalization Table（actuals / committed forecast / system generated forecast） | Java | PG（`fi_*` 表） | **PG 只读账号** 直接 SQL 查询，按 company_id + period 过滤 |
| Benchmark 数据 | Java | PG（`fi_benchmark_*`、`financial_benchmark_*` 等） | **PG 只读账号** 直接 SQL 查询 |
| **Memory File（Layer 1a / 1b 条目）** | **Python** | PG（Python 专属表 `memory_entries`） | 自管 |
| **GS Knowledge Base（Layer 2 chunks）** | **Python** | PG（`kb_chunks`） | 自管 |
| **聊天上传文档（原文件）** | Java | **S3**（复用现有上传通道） | Java 上传 S3 后发 SQS 事件，Python 用 S3 SDK 拉原文 |
| **文档 chunks / 嵌入** | **Python** | PG（`document_chunks`、`document_embeddings`） + S3（如需缓存切片） | 自管 |
| **Chat History（messages + thread state）** | **Python** | PG（`chat_threads` + `langgraph_checkpoints`） | 自管 |
| **AI 调用 trace / cost / 评估** | **Python** | LangSmith + PG | 自管 |
| **Layer 2 admin 上传 markdown / playbook 文件** | **Python**（或复用 Java 上传通道写 S3） | S3 + PG（`kb_chunks`） | 若复用 Java 上传，按"聊天上传文档"同一路径；否则 Python 直传 S3 |

**一句话总结**：
- **AI / 知识 / 对话 / 文档解析** → Python 拥有，**自己的表自己读写，业务表只读读取**
- **文件接收 / S3 落盘 / 用户与公司基础数据** → Java 拥有，Python 通过 **DB 只读 + SQS** 获得

---

## 3. Java 侧职责（仅文件上传通道）

> 本节列出 AI Chatbot 在 Java 侧的全部职责。原则上 **不为 AI 新建 REST 接口**，全部复用现有上传通道与 SQS 框架。

### 3.1 文件上传

复用 CIOaas-api 现有的文件上传接口（例如 `POST /api/web/documents/upload` 或现有 S3 上传通道）。AI Chatbot 不另开新端点。

**复用接口需具备的能力**（如已有则跳过；如缺失则补齐）：

- 支持 `multipart/form-data`，字段：`file`、`company_id`、`scene`（新增枚举值 `ai_chat`、`kb_layer2` 标识此次上传归 AI Chatbot 用途）
- 鉴权：用户 JWT
- 服务端校验：
  - JWT 解出 user_id / accessible_companies，校验 `company_id ∈ accessible_companies`
  - 文件类型白名单：pdf / docx / xlsx / csv / md / txt（与 OCR epic 共用）
  - 文件大小上限：≤ 50 MB（参考既有规则）
- 落盘：S3 → `s3://lg-uploads/<tenant_id>/<company_id>/<yyyy>/<mm>/<file_id>.<ext>`
- 写元数据表（Java 现有 `r_document` 或新增 `r_ai_document`），字段建议：
  ```
  document_id, tenant_id, company_id, user_id,
  scene, original_name, mime_type, size,
  s3_bucket, s3_key,
  status('uploaded'|'processing'|'indexed'|'failed'),
  created_at
  ```
- 上传成功后立即向 SQS 发布 `file.uploaded` 事件（见 §4.1）

### 3.2 既有上传接口的轻量扩展（如必要）

如果现有上传接口无法区分 AI Chatbot 用途，建议加 `scene` 字段而 **不新建端点**。这样：
- AI Chatbot 上传与 OCR 上传共享通道、共享配额、共享审计
- 后续如有 Skills/Report Builder 等子能力，复用相同管道

### 3.3 文件下载（Python 拉文件）

Python 通过两种方式之一获取原文件：

| 方式 | 说明 | 推荐场景 |
|------|------|---------|
| **直接 S3 SDK** | Python 用 AWS SDK 凭 IAM 角色直读 S3（已知 bucket/key） | **推荐**——Java 完全无 AI 流量 |
| **Java 签发 presigned URL** | 若 IAM 策略要求统一发放，Java 提供 `POST /api/internal/files/presign`（最小化新增） | 仅当公司安全策略要求 |

**默认采用 S3 直读**；只在 IAM 不放权时退化到 presigned URL。

### 3.4 Java 不做的事

明确划清不属于 Java 范畴的能力，Java **不应** 暴露任何下列接口：

- ❌ Normalization Table 查询接口
- ❌ Benchmark 查询接口
- ❌ Company Settings 查询接口（Python 直接读 DB）
- ❌ ACL 查询接口
- ❌ AI 编排 / 模型路由
- ❌ Memory File CRUD
- ❌ Chat History 查询
- ❌ 文档解析 / chunk / 嵌入

---

## 4. SQS 事件契约（Java → Python）

> 所有 Java 业务状态变更都通过 SQS 通知 Python。复用项目既有 SQS 框架（CIOaas 内 Java ↔ Python OCR 已有同款管道）。

### 4.1 必有事件

| 事件 type | 触发时机 | Payload |
|----------|---------|---------|
| `file.uploaded` | 文件上传成功后立即发 | `{ document_id, tenant_id, company_id, user_id, scene, s3_bucket, s3_key, mime_type, size, original_name, uploaded_at }` |
| `company.created` | 新建公司 | `{ company_id, tenant_id, created_at }` |
| `company.settings.updated` | name / description / industry / stage / type 等字段任一变更 | `{ company_id, version, changed_fields[], updated_at }` |
| `user.acl.updated` | 用户的 accessible_companies 增减 | `{ user_id, accessible_companies[], updated_at }` |
| `company.archived` / `company.deleted` | 公司归档或软删除 | `{ company_id, archived_at }` |

### 4.2 队列与消费

| 队列名 | 方向 | 备注 |
|--------|------|------|
| `ai-chatbot-document-events` | Java → Python | 文件上传通知 |
| `ai-chatbot-company-events` | Java → Python | Company / ACL / Settings 变更 |
| `ai-chatbot-callbacks`（可选） | Python → Java | Python 完成索引后可选回写状态（如更新 `r_ai_document.status='indexed'`） |

- 消息格式：JSON，必含 `event_id`（UUID，幂等键）、`event_type`、`tenant_id`、`occurred_at`、`payload`
- Python 端：FastAPI + Celery 消费，幂等（按 event_id 去重）
- 死信队列（DLQ）：消费失败 ≥ 5 次进 DLQ，由 ops 人工排查

### 4.3 索引状态回写（可选）

Python 完成文档索引后，向 `ai-chatbot-callbacks` 推 `document.indexed`：
```json
{
  "event_id": "...",
  "event_type": "document.indexed",
  "payload": {
    "document_id": "doc_001",
    "chunk_count": 42,
    "indexed_at": "2026-05-12T10:00:00Z",
    "summary_written_to_memory": true
  }
}
```
Java 收到后更新 `r_ai_document.status='indexed'`，用于前端展示"已索引/解析中/失败"。

---

## 5. Python 直读 PostgreSQL 业务表

> 这是本架构的关键能力：Python 用 **只读角色** 直接读取 Java 写入的业务表。

### 5.1 DB 用户与权限

| 角色 | 权限 | 用途 |
|------|------|------|
| `cioaas_app` | RW on Java 业务表 + Python 自有表 | Java 应用使用 |
| `cioaas_ai_ro` | **READ ONLY** on Java 业务表 + RW on Python 专属 schema (`ai_chatbot`) | Python AI 服务专用 |

DDL 示例：
```sql
CREATE ROLE cioaas_ai_ro LOGIN PASSWORD '<secret>';
GRANT USAGE ON SCHEMA public TO cioaas_ai_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cioaas_ai_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO cioaas_ai_ro;

CREATE SCHEMA ai_chatbot AUTHORIZATION cioaas_ai_ro;
GRANT ALL ON SCHEMA ai_chatbot TO cioaas_ai_ro;
```

### 5.2 Python 读 Java 表的安全约束

| 约束 | 做法 |
|------|------|
| **不允许跨 tenant 读** | 所有 SQL 必须带 `tenant_id = :tenant_id`，由 Python ORM 在 base query 中强制 |
| **ACL 二次校验** | 即便 SQL 已过滤 tenant，Python 仍要根据 JWT claims 校验 `company_id ∈ accessible_companies` |
| **不允许 SELECT \*** | Python repository 显式列出字段，避免无意拉敏感列（密码 hash、API key 等） |
| **慢查询保护** | Python 连接池设 `statement_timeout = 5s`，防止长时间扫描 |
| **审计** | Python 调用业务表查询时落日志 `ai-pg-readonly-access.log`，便于追溯 |

### 5.3 Python 重点 SQL（示例）

#### 拉取 Company Settings
```sql
SELECT company_id, tenant_id, name, description, industry, stage, company_type,
       extra_fields, updated_at
FROM r_company
WHERE company_id = :company_id AND tenant_id = :tenant_id AND deleted = false;
```

#### Normalization Table 查询（actuals）
```sql
SELECT company_id, metric, period, value, unit
FROM fi_normalization_actuals
WHERE tenant_id = :tenant_id
  AND company_id = ANY(:company_ids)
  AND metric = ANY(:metrics)
  AND period BETWEEN :from_period AND :to_period;
```
（committed / system_generated forecast 各自类似，使用对应表）

#### Benchmark 查询
```sql
SELECT metric, company_value, percentile, peer_group, source, as_of_month
FROM fi_company_benchmark_snapshot
WHERE tenant_id = :tenant_id
  AND company_id = :company_id
  AND metric = ANY(:metrics)
  AND peer_group = :peer_group
ORDER BY as_of_month DESC LIMIT 1;
```

#### ACL 拉取
```sql
SELECT DISTINCT r.company_id
FROM r_user_company r
JOIN r_company c USING (company_id)
WHERE r.user_id = :user_id AND r.tenant_id = :tenant_id
  AND c.deleted = false;
```

具体表名以 `gstdev-cioaas-web` 实际 schema 为准，落地前由 Python 团队与 Java 团队对齐表/字段映射。

---

## 6. Python 对前端的接口

> 路径前缀：`/ai/*`，前端直接调用（带 JWT）

### 6.1 聊天

#### `POST /ai/chat`
```json
{
  "conversation_id": "uuid (首次为 null，由后端生成)",
  "company_id": "c_acme (公司端固定 / Portfolio 端可空)",
  "question": "我们的 ARR 增长在同行中处于什么位置？"
}
```

**响应**：
```json
{
  "thread_id": "u_001:conv_42",
  "answer": "...",
  "attribution": ["Based on GS best practices"],
  "needs_data_hint": null,
  "tool_calls": [...]
}
```

#### `GET /ai/threads`
返回当前用户的会话列表（按 `last_message_at` 倒序，前端做 Today/Yesterday 分组）。

#### `GET /ai/threads/{thread_id}/messages`
返回某次对话的完整历史。

### 6.2 文档列表与状态查询（不接收文件本身）

- 文件上传走 **Java 上传接口**（见 §3.1）
- Python 仅暴露查询：

#### `GET /ai/documents?company_id=...`
返回该公司可见文档列表（含 GS Playbook 对授权用户），含 `status` (`uploaded` / `indexing` / `indexed` / `failed`) 与 chunk 数量。

#### `GET /ai/documents/{document_id}`
返回单文档详情 + 自动生成的摘要。

### 6.3 Memory File 浏览

#### `GET /ai/memory?company_id=...&layer=1a&q=...`
返回 `memory_entries` 分页列表，按角色过滤可见 layer。

### 6.4 Layer 2 KB 管理（仅 Admin / PGM）

#### `POST /ai/kb/playbooks`（multipart/form-data）
- Layer 2 markdown / playbook 直传 Python（**或复用 Java 上传通道后通过 SQS 流转**——两种实现都可，本文档不强制）
- 字段：`file`、`title`、`tags[]`

#### `DELETE /ai/kb/playbooks/{id}`
软删除 Layer 2 条目。

---

## 7. 鉴权与租户传递

```
浏览器 ──JWT──→ Java（文件上传等业务接口）
浏览器 ──JWT──→ Python（/ai/*）
                  │
                  ├─ 共用密钥本地验签
                  ├─ 解析 claims: user_id / tenant_id / role / accessible_companies
                  └─ 所有 PG 查询带 tenant_id 强制过滤 + ACL 二次校验
```

**JWT 必须包含的 claims**（与 Java 团队对齐）：
```json
{
  "sub": "u_001",
  "tenant_id": "gs",
  "role": "pm",
  "accessible_companies": ["c_acme", "c_beta"],
  "exp": 1730000000
}
```

若 `accessible_companies` 过长（>50 家公司），改用 `acl_version` 字段；Python 收到 token 后查 `r_user_company` 表（PG 直读）并缓存到 Redis。

---

## 8. 缓存策略

| 数据 | TTL | 失效触发 |
|------|-----|---------|
| 用户 ACL（从 `r_user_company` 派生） | 5 分钟 | 收到 `user.acl.updated` SQS 事件立即清 |
| Company Settings（按 company_id 缓存） | 10 分钟 | 收到 `company.settings.updated` 事件立即清 |
| Normalization Table 查询结果 | **不缓存** | 数据敏感且变化频繁，每次实时查 |
| Benchmark 查询结果 | 1 小时 | 按月更新，TTL 长 |
| GS Playbook 解析后的 chunks | 不主动失效 | admin 上传新版本或删除时手动重建 |

**实现**：Redis（与 Celery broker 同实例或独立实例），key 形如 `ai:cache:company:{company_id}:v{acl_version}`。

---

## 9. 失败降级

| 场景 | Python 行为 |
|------|-------------|
| **PG 只读连接整体不可达** | 财务 / Benchmark / Company 查询返回 `service_unavailable`，AI 回复："抱歉，业务数据系统暂时无法访问，请稍后重试。" |
| **单条 SQL 超时（>5s）** | 触发 tool 超时，返回部分结果 + 末尾追加："（部分指标查询超时，未能展示完整数据）" |
| **Company Settings 缓存命中但已过期、DB 同时失败** | 用本地最后一次缓存 + 在回复末尾追加："（公司元数据可能不是最新）" |
| **某 metric 在 Java 表里为空** | 进入 `compose_no_data` 节点，给出补全指引（如"请在 Financial Entry 录入"） |
| **S3 拉取上传文件失败** | 文档状态置 `failed`，发 callback；用户可点重试 |
| **SQS 消费失败** | 重试 5 次后入 DLQ，告警 ops；不阻塞实时聊天 |

---

## 10. 监控与对账

### 10.1 跨服务追踪
- 强制 `X-Trace-Id` 透传（OpenTelemetry）；Java 上传接口与 Python `/ai/*` 共用 trace id
- LangSmith trace 与 Java APM 共用 trace id

### 10.2 对账定时任务
每天凌晨：
1. 抽样 100 个 AI 给出的财务回复
2. Python 把回复中的数字与同时间用 SQL 直查 `fi_*` 表的真实值对比
3. 差异 > 0 视为 hallucinate，告警

### 10.3 关键 SLI

| 指标 | 阈值 |
|------|------|
| Python PG 只读查询 P95（normalization） | < 500ms |
| Python PG 只读查询 P95（benchmark） | < 300ms |
| AI 回复中 financial 数字与 DB 对账一致率 | 100% |
| SQS 事件处理延迟（end-to-end） | < 30s |
| 文件上传 → 索引完成 P95 | < 2 min |

---

## 11. 实施分工与里程碑

> 与旧版相比，**Java 工作量大幅缩减**：除 Sprint 1 的 SQS 与上传接口微调外，Java 团队几乎无新工作量。

| 阶段 | Java 团队 | Python 团队 |
|------|----------|-------------|
| Sprint 1 | 现有上传接口加 `scene` 字段；建 SQS 队列 `ai-chatbot-document-events`、`ai-chatbot-company-events`；JWT claims 补 `accessible_companies` 或 `acl_version` | 创建 `cioaas_ai_ro` 只读账号；LangGraph 骨架 + JWT 解析 |
| Sprint 2 | 上传成功后发 `file.uploaded` SQS 事件 | Layer 1a 初始化逻辑（从 `r_company` 拉初始化数据）；Layer 2 ingestion |
| Sprint 3 | — | Tool calling：实现 `query_normalization` SQL repository；财务问答节点 |
| Sprint 4 | — | Benchmark SQL repository；跨公司聚合节点 |
| Sprint 5 | 现有 Company Settings 修改逻辑加 `company.settings.updated` SQS 事件 | 文档上传 SQS 消费 + S3 拉文件 + chunk + 嵌入 + Memory 抽取异步链 |
| Sprint 6 | ACL 变更加 `user.acl.updated` 事件 | Portfolio 端图分支 + Layer 1b |
| Sprint 7 | 接口限流、SLO 监控接入 | 红队测试 + 对账任务 + 上线 |

---

## 12. 不属于本文档范畴的事

以下不由本文档描述（请参阅对应文档）：

- LangGraph 内部节点 / 路由 / 状态：见 [langgraph-technical-design.md](./langgraph-technical-design.md)
- Asana 业务需求原文：见 `.raw/`
- 各功能的中文需求：见 `part-A` ~ `part-D`
- 前端 UI 设计：另行由前端团队产出

---

## 13. 待与 Java 团队对齐的开放问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | JWT 已有 `accessible_companies` 或 `acl_version` claim 吗？ | 没有则尽快加，避免 Python 每次都查 ACL 表 |
| Q2 | 现有上传接口是否能携带 `scene` 字段？是否够强（鉴权 + S3 + 元数据落表）？ | 评估后补齐 |
| Q3 | SQS 队列由谁创建？走 IaC（CloudFormation / Terraform）还是手工？ | 与运维对齐 |
| Q4 | Python 是否能拿到 S3 直读 IAM 角色？ | 推荐拿；否则退化到 presigned URL |
| Q5 | `cioaas_ai_ro` 只读账号是否需要在 RDS 上单独配额管理？ | 与 DBA 对齐慢查询保护 |
| Q6 | Layer 2 admin 上传是否复用 Java 上传通道？ | **建议复用**（统一审计、配额、S3 路径） |
| Q7 | Java 现有的 `fi_*` 表 schema 是否已稳定？是否会被重命名 / 迁移？ | Python 需要在 Sprint 1 与 Java 团队 freeze 这些表的字段语义；后续变更需提前通知 |
