# Python AI 服务 ↔ Java CIOaas 集成边界

> 本文档明确 AI Chatbot 功能的服务边界：**所有 AI 编排、RAG、Memory、Chat History 功能由 Python 服务承担**；当需要业务数据（财务、Benchmark、Company Settings、ACL）时，**Python 通过 Java REST 接口拉取，不直连 Java 业务库**。
> 编写日期：2026-05-07。

---

## 1. 设计原则

| # | 原则 | 含义 |
|---|------|------|
| P1 | **单一职责** | Python 只管 AI 推理与知识；Java 仍是业务系统的真相之源 |
| P2 | **数据库不共享** | Python 不直连 Java 业务库；Java 也不写 Python 知识库表 |
| P3 | **Java 侧再校验一次 ACL** | 即使 Python 侧已做过滤，Java 收到请求时仍要根据 JWT 二次校验访问范围（双重保险） |
| P4 | **Java 不感知 LLM** | Java 接口只暴露结构化业务数据；不知道也不需要知道 AI 怎么用 |
| P5 | **同步优先用 Pull，少量场景用事件** | 默认 Python 主动调 Java；只有 Company Settings 变更才需要 Java 推事件 |
| P6 | **缓存仅短期** | Python 端可缓存 ACL / Company Settings ≤ 5 分钟，避免授权变更滞后 |
| P7 | **失败降级而非拒绝** | Java 不可用时，Python 用最后已知数据 + 显著免责说明继续服务 |

---

## 2. 数据归属表

| 数据 | 归属方 | 存储 | Python 如何获得 |
|------|--------|------|-----------------|
| 用户认证 / 角色 / accessible_companies | **Java** | Java DB | JWT claims + `/api/internal/me` |
| Company Settings（name / description / industry / stage / type） | **Java** | Java DB | `/api/internal/companies/{id}` 拉取；变更时 Java 推事件给 Python |
| Normalization Table（actuals / committed forecast / system forecast） | **Java** | Java DB | `/api/internal/normalization/query` 按需查询 |
| Benchmark 数据 | **Java** | Java DB | `/api/internal/benchmark/query` 按需查询 |
| Portfolio / 公司 ACL 关系 | **Java** | Java DB | JWT claims + `/api/internal/acl/companies` |
| **Memory File（Layer 1a / 1b 条目）** | **Python** | PG `memory_entries` + `kb_chunks` | 自管 |
| **GS Knowledge Base（Layer 2 chunks）** | **Python** | PG `kb_chunks` | 自管 |
| **上传文档（原文 + chunks + 摘要）** | **Python** | S3 + PG | 自管 |
| **Chat History（messages + thread state）** | **Python** | PG（LangGraph checkpointer + `chat_threads`） | 自管 |
| **AI 调用 trace / cost / 评估数据** | **Python** | LangSmith / PG | 自管 |
| **Layer 2 admin 上传的 markdown** | Python（文件）+ Java（管理员操作日志） | S3 + PG | Python 自管文件；操作审计可同步到 Java |

**简化总结**：
- 一切 **AI / 知识 / 对话** 相关 → Python 拥有
- 一切 **业务 / 财务 / 用户身份** 相关 → Java 拥有

---

## 3. Java 需要新暴露的内部接口

> 路径前缀：`/api/internal/*`（仅服务间调用，不对外）
> 鉴权方式：Service-to-Service mTLS 或共享密钥 + Forwarded JWT
> 协议：HTTP/JSON，UTF-8

### 3.1 鉴权与用户上下文

#### `GET /api/internal/me`
解析 JWT 并返回 AI 路由所需的用户上下文。

**请求头**：`Authorization: Bearer <user-jwt>`

**响应**：
```json
{
  "user_id": "u_001",
  "tenant_id": "gs",
  "role": "pm",
  "primary_company_id": null,
  "accessible_companies": ["c_acme", "c_beta", "c_gamma"]
}
```

**错误**：`401 Unauthorized`、`403 Forbidden`

---

### 3.2 公司元数据（用于 Layer 1a Memory 初始化）

#### `GET /api/internal/companies/{company_id}`

**响应**：
```json
{
  "company_id": "c_acme",
  "tenant_id": "gs",
  "name": "ACME Inc.",
  "description": "B2B SaaS for warehouse...",
  "industry": "Logistics SaaS",
  "company_type": "Series A",
  "stage": "growth",
  "extra_fields": { "...": "..." },
  "version": 17,
  "updated_at": "2026-05-06T10:30:00Z"
}
```

**用途**：
- 首次为公司创建 Layer 1a 时全量拉取并写入 `memory_entries`
- 收到 `company.settings.updated` 事件时增量同步

#### `POST /api/internal/companies/batch-get`

```json
{ "company_ids": ["c_acme", "c_beta"] }
```

返回上述结构数组。Portfolio Manager 看自己访问范围内多家公司时使用。

---

### 3.3 Normalization Table 查询

#### `POST /api/internal/normalization/query`

**请求体**：
```json
{
  "company_ids": ["c_acme"],
  "metrics": ["arr", "burn_rate", "gross_margin"],
  "period": { "from": "2025-01", "to": "2026-04" },
  "forecast_type": "actuals",
  "granularity": "monthly"
}
```

`forecast_type` 取值：`actuals` | `committed` | `system_generated`
若需多种 forecast，可一次请求多个对象（数组形式）。

**响应**：
```json
{
  "data": [
    {
      "company_id": "c_acme",
      "metric": "arr",
      "forecast_type": "actuals",
      "series": [
        { "period": "2025-01", "value": 1200000, "unit": "USD" },
        { "period": "2025-02", "value": 1280000, "unit": "USD" }
      ]
    }
  ],
  "missing": [
    { "company_id": "c_acme", "metric": "burn_rate", "reason": "no_committed_forecast" }
  ]
}
```

**关键点**：
- Java 必须根据 JWT 二次校验 `company_ids ⊆ user.accessible_companies`，越权返回 `403`
- 缺数据时返回 `missing` 清单，**不要**抛 500，AI 需要据此告知用户"如何补全"

---

### 3.4 Benchmark 查询

#### `POST /api/internal/benchmark/query`

**请求体**：
```json
{
  "company_id": "c_acme",
  "metrics": ["arr_growth", "gross_margin"],
  "peer_group": "industry"
}
```

`peer_group` 取值：`internal`（同投资组合内） | `industry`（外部行业基准）

**响应**：
```json
{
  "data": [
    {
      "metric": "arr_growth",
      "value": 0.42,
      "percentile": 0.45,
      "peer_group": "industry",
      "source": "KeyBanc 2024 SaaS Survey",
      "as_of": "2024-12"
    }
  ]
}
```

---

### 3.5 ACL（可选 / 用于跨公司查询解析）

#### `GET /api/internal/acl/companies?user_id=u_001`

**响应**：
```json
{
  "user_id": "u_001",
  "tenant_id": "gs",
  "accessible_companies": [
    { "company_id": "c_acme", "via_portfolio": "pf_alpha", "role_in_company": "pm" }
  ]
}
```

**用途**：JWT 中如已包含 `accessible_companies` 可省略此接口；当用户访问范围频繁变化（新增 portfolio）时用于强制刷新。

---

### 3.6 用户列表（Memory File 显示用，可选）

#### `GET /api/internal/users/{user_id}`
返回用户名、邮箱用于在 Memory Settings 面板显示"由谁记录"。

---

## 4. Python 需要新暴露的接口

> 路径前缀：`/ai/*`，对前端开放（需 JWT）

### 4.1 聊天

#### `POST /ai/chat`
```json
{
  "conversation_id": "uuid（首次为 null，由后端生成）",
  "company_id": "c_acme（公司端固定 / Portfolio 端可空）",
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

---

### 4.2 文档上传

#### `POST /ai/documents`（multipart/form-data）
- 字段：`file`、`company_id`
- 返回：`{ "document_id": "...", "status": "indexing" }`

#### `GET /ai/documents?company_id=...`
返回文档列表（含 GS Playbook 对授权用户）。

---

### 4.3 Memory File 浏览

#### `GET /ai/memory?company_id=...&layer=1a&q=...`
返回 `memory_entries` 分页列表（按角色过滤 layer）。

---

## 5. 事件 / Webhook（Java → Python）

只有少量场景需要 Java 主动通知 Python；其他全部 Pull 即可。

### 5.1 必须 Push 的事件

| 事件 | 触发时机 | Payload |
|------|----------|---------|
| `company.settings.updated` | Company Settings 字段变更（包括 industry、description、stage） | `{ company_id, version, changed_fields[] }` |
| `company.created` | 新建公司 | `{ company_id, tenant_id }` |
| `user.acl.updated` | 用户的 accessible_companies 增减 | `{ user_id, accessible_companies[] }` |

### 5.2 推送方式

推荐顺序：
1. **HTTP Webhook**：Java 调 Python `POST /ai/events`（带签名头）
2. **消息总线**：若已有 Kafka / RabbitMQ，订阅同名 topic
3. **轮询**：Python 每 5 分钟调 `GET /api/internal/companies?updated_since=...`（兜底）

#### Python 端 endpoint

```
POST /ai/events
Header:  X-LG-Signature: <hmac-sha256>
Body:    { "type": "company.settings.updated", "data": {...}, "ts": ... }
```

收到事件后只做轻量入队（Redis），由 Celery worker 异步同步到 `memory_entries`。

---

## 6. 鉴权与租户传递

```
浏览器 ──JWT──→ Java（业务接口）
浏览器 ──JWT──→ Python（/ai/*）
                  │
                  ├─ 解析 JWT，提取 user_id / tenant_id / role / accessible_companies
                  │
                  └─ 调 Java 内部接口时：
                       Authorization: Bearer <forwarded-jwt>
                       X-LG-Service: ai-chatbot
                       X-Trace-Id: <opentelemetry trace id>
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

若 `accessible_companies` 太长（>50 家公司），改用 `acl_version` 字段，Python 收到 token 后调 `/api/internal/acl/companies` 拉详情并缓存。

---

## 7. 缓存策略

| 数据 | TTL | 失效触发 |
|------|-----|----------|
| `/me` 返回的角色与 ACL | 5 分钟 | 收到 `user.acl.updated` 事件立即清 |
| `companies/{id}` 元数据 | 10 分钟 | 收到 `company.settings.updated` 事件立即清 |
| Normalization Table 查询结果 | **不缓存** | 数据敏感、变化频繁 |
| Benchmark 查询结果 | 1 小时 | 按月更新，TTL 长 |
| GS Playbook 解析后的 chunks | 不主动失效 | 由 admin 上传新版本时手动重建 |

实现：用 Redis（已有 Celery broker），key 形如 `ai:cache:company:{company_id}:v{acl_version}`。

---

## 8. 失败降级

| 场景 | Python 行为 |
|------|-------------|
| Java 整体不可达 | 财务 / Benchmark Tool 调用返回 `service_unavailable`，AI 回复："抱歉，财务数据系统暂时无法访问，请稍后重试。" 并不进入幻觉 |
| `/me` 超时 | 用 JWT claims 内的兜底字段（accessible_companies 必填） |
| Company Settings 拉取失败 | 用本地最后一次缓存 + 在回复末尾追加："（公司元数据可能不是最新）" |
| 单个 metric 在 Java 返回 `missing` | 进入 `compose_no_data` 节点，给出补全指引 |
| Webhook 验签失败 | 拒绝事件、记日志、不重试 |

---

## 9. 监控与对账

### 9.1 跨服务追踪
- 强制 `X-Trace-Id` 透传（OpenTelemetry）
- LangSmith trace 与 Java APM（如 Skywalking / Datadog）共用 trace id

### 9.2 对账定时任务
每天凌晨：
1. 抽样 100 个 AI 给出的财务回复
2. Python 把回复中的数字与同时请求 Java 接口拿到的真实值对比
3. 差异 > 0 视为 hallucinate，告警

### 9.3 关键 SLI

| 指标 | 阈值 |
|------|------|
| Java `/api/internal/normalization/query` P95 | < 500ms |
| Java `/api/internal/benchmark/query` P95 | < 300ms |
| AI 回复中 financial 数字与 Java 对账一致率 | 100% |
| Webhook 处理延迟 | < 30s |

---

## 10. 接口版本与契约管理

- 用 OpenAPI 3.1 定义所有 `/api/internal/*` 接口，放在 `gstdev-cioaas-web/src/main/resources/openapi/ai-internal.yaml`
- Python 端用 `datamodel-code-generator` 自动生成 Pydantic 客户端
- 任何破坏性变更：
  - 新接口加 `/api/internal/v2/*` 前缀
  - Java 同时维护 v1 / v2 ≥ 1 个 sprint
  - Python 提前升级，按 feature flag 切流

---

## 11. 实施分工与里程碑

| 阶段 | Java 团队 | Python 团队 |
|------|-----------|-------------|
| Sprint 1 | `/api/internal/me` + JWT claims 调整 | LangGraph 骨架 + JWT 解析 |
| Sprint 2 | `/api/internal/companies/{id}` + batch-get + webhook 框架 | Layer 1a 初始化 + 摄取 markdown 到 Layer 2 |
| Sprint 3 | `/api/internal/normalization/query` | Tool calling + 财务节点 |
| Sprint 4 | `/api/internal/benchmark/query` | Benchmark 节点 + 跨公司聚合 |
| Sprint 5 | `company.settings.updated` 事件推送 | 文档上传 + Memory 抽取异步链 |
| Sprint 6 | `acl.updated` 事件推送 | Portfolio 端图分支 + Layer 1b |
| Sprint 7 | 接口加速 / 限流 / 监控接入 | 红队测试 + 对账任务 + 上线 |

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
| Q1 | JWT 已有 `accessible_companies` claim 吗？ | 没有则尽快加，避免每次调 `/me` |
| Q2 | Java 现有事件总线（Kafka / SQS）？ | 复用为优先；否则起轻量 webhook |
| Q3 | Normalization Table 的查询接口是否已存在？ | 看 `gstdev-cioaas-web` 现有控制器，能复用就复用，否则新建 `/api/internal/*` |
| Q4 | 是否允许 Python 服务直读 Redis（共享缓存）？ | 不允许，Python 用自己的 Redis 实例 |
| Q5 | 服务间调用走 mTLS 还是网关（如 Spring Cloud Gateway）？ | 走网关并打 service principal |
| Q6 | Layer 2 admin 上传是否需要在 Java 留审计？ | 是，Python 在每次上传 / 删除后调 `/api/internal/audit/log` |
