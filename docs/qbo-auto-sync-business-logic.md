# QBO 连接与自动数据拉取 — 业务逻辑文档

> 范围：仅覆盖 **自动模式（Automatic）** 下，从用户点击连接到数据入库的完整链路。

---

## 1. 流程总览

```
用户点击连接
  → OAuth 授权（Intuit）
  → OAuth Callback 处理
  → 异步触发三项操作：
      ├─ [A] 保存 Datasource 元数据
      ├─ [B] 创建 AWS EventBridge 每日调度
      └─ [C] 发送 SQS 消息（立即触发首次拉取）
  → SQS 消费 → 调用 ETL 服务
  → Token 刷新 → 拉取 7 个数据流 → 写入 Redshift
  → 回调通知 Web 服务（更新状态 & 日志）
```

---

## 2. OAuth 连接流程

### 2.1 发起授权

| 项目 | 说明 |
|------|------|
| 接口 | `GET /companyQuickbooks/authorization?companyId={id}&roleType={role}&userId={userId}` |
| Controller | `CompanyQuickbooksController.authorization()` |
| Service | `CompanyQuickbooksServiceImpl.authorization()` |

**处理逻辑：**

1. 读取配置构建 `OAuth2Config`（clientId、clientSecret、environment）
2. 设置授权范围：`Scope.Accounting`
3. 构造 `state = companyId + "," + roleType + "," + userId`（回调时恢复上下文）
4. 生成 Intuit OAuth 授权 URL，302 重定向用户到 Intuit 授权页

### 2.2 OAuth Callback — Token 交换与存储

| 项目 | 说明 |
|------|------|
| 接口 | `GET /companyQuickbooks?code={code}&realmId={realmId}&state={state}` |
| Controller | `CompanyQuickbooksController.findById()` |
| Service | `CompanyQuickbooksServiceImpl.findById()` |

**处理逻辑：**

1. **解析 state**：还原 `companyId`、`roleType`、`userId`
2. **校验参数**：验证 `code` 和 `realmId` 非空
3. **Token 交换**：调用 `OAuth2PlatformClient.retrieveBearerTokens(code, redirectUri)` 获得 `BearerTokenResponse`
4. **持久化 Token**：
   - 更新 `company_quickbooks` 表：`realmId`、`refreshToken`、`status="success"`、`isFirst=true`
5. **异步触发三项操作**（`CompletableFuture.runAsync`，使用 IO 线程池）：

| 操作 | 方法 | 说明 |
|------|------|------|
| A — 保存 Datasource | `self.quickbooksAirflow(save, userId)` | 在 `datasource` 表创建/更新 QBO 数据源配置 |
| B — 创建调度 | `qboSchedulerService.createOrUpdateSchedule(companyId, realmId, "cron(0 0 * * ? *)", true)` | AWS EventBridge Scheduler，**每天 00:00 UTC** 触发 |
| C — 首次拉取 | `qboSchedulerService.sendSyncMessage(companyId, realmId)` | 发送 SQS 消息，**立即**触发首次数据同步 |

6. **页面重定向**：将用户重定向回前端页面

---

## 3. 调度机制（EventBridge + SQS）

### 3.1 EventBridge Scheduler

| 项目 | 说明 |
|------|------|
| 实现类 | `QBOSchedulerService` |
| Schedule 名称 | `qbo-sync-{companyId}` |
| Cron 表达式 | `cron(0 0 * * ? *)` — 每天 UTC 00:00 |
| 目标队列 | `qbo-scheduler-queue`（SQS） |
| 幂等性 | `createOrUpdateSchedule` — 重复调用安全 |

### 3.2 SQS 消息格式

```json
{
  "messageType": "QboScheduler",
  "schedulerType": "QboSync",
  "companyId": "{companyId}",
  "realmId": "{realmId}",
  "sendTime": "<aws.scheduler.scheduled-time>",
  "uuid": "<aws.scheduler.execution-id>"
}
```

### 3.3 SQS 消息消费

| 项目 | 说明 |
|------|------|
| 监听器 | `QBOSqsMessagePoller`（`@PostConstruct` 注册） |
| 队列 | `qbo-scheduler-queue` |
| 处理器 | `QBOScheduleProcessor.processMessage()` |

**消费逻辑：**

1. 解析 SQS 消息为 `QBOSyncMessageDto`
2. 校验 `schedulerType == "QboSync"`
3. 查询 PostgreSQL：
   - `CompanyQuickbooks` → 获取 `realmId`、`refreshToken`
   - `Datasource` → 获取数据源配置
   - `QuickbooksCategoryAccount` → 获取账户分类映射
4. 生成 `batchId`（UUID）
5. 序列化 `categoryAccounts` 为 JSON
6. 写入日志：`qbo_logs` → `AIRFLOW_DAILY_SCHEDULE_BEGIN`
7. 构造 `QBOSyncRequest`，通过 OpenFeign 调用 ETL 服务

---

## 4. ETL 数据同步

### 4.1 入口

| 项目 | 说明 |
|------|------|
| Feign Client | `QBOSyncFeignClient` → `POST /etl/internal/openfeign/qbo/sync2` |
| Controller | `QBOSyncController.sync2()` — 异步执行 |
| 编排器 | `QBOSyncOrchestrator.sync()` |

### 4.2 Phase 1 — Token 刷新

| 项目 | 说明 |
|------|------|
| 实现类 | `QBOTokenServiceImpl.refresh()` |
| 刷新端点 | `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer` |
| 认证方式 | HTTP Basic Auth（`Base64(clientId:clientSecret)`） |
| 请求参数 | `grant_type=refresh_token`、`refresh_token={token}` |

**刷新成功：**
- 获得新的 `accessToken` 和 `refreshToken`
- 回调 Web 服务：`webQBOFeignClient.tokenRefreshed()`
  - 更新 `company_quickbooks.refreshToken`（新 Token）
  - 更新 `datasource.parameters`（accessToken、refreshToken）
  - 写入日志：`REFRESH_TOKEN_BEGIN` → `REFRESH_TOKEN_END`（成功）
  - 备份到 S3：`qbo/{companyId}/{batchId}/token_refresh.json`

**刷新失败：**
- 回调 Web 服务：`webQBOFeignClient.tokenFailed()`
  - 更新 `company_quickbooks.status = "Invalid"`
  - 更新 `datasource.tokenRefreshStatus = false`
  - 写入日志：`REFRESH_TOKEN_END`（失败）+ 错误信息
  - **流程中止**，用户需重新连接

### 4.3 Phase 2 — 拉取 7 个数据流

所有数据通过 QBO REST API 拉取，使用 `Authorization: Bearer {accessToken}` 认证。

| # | 数据流 | QBO API | 主要字段 | Redshift 表 | 清理策略 |
|---|--------|---------|----------|-------------|---------|
| 1 | Account List Detail | `GET /v3/company/{realmId}/reports/AccountList` | number, accountName, accountType, detailAccType, accountDesc, accountBal | `account_list_detail` | **TRUNCATE**（覆盖） |
| 2 | Account Category Mapping | 基于 Account List + categoryAccounts 配置映射 | accountName → category (Sales, COGS, Expenses…) | `r_account_category` | **TRUNCATE**（覆盖） |
| 3 | Profit & Loss | `GET /v3/company/{realmId}/reports/ProfitAndLoss?summarize_column_by=Month&start_date={}&end_date={}` | totalIncome, cogs, grossProfit, totalExpenses, netIncome, otherIncome | `profit_and_loss` | 追加 |
| 4 | Balance Sheet | `GET /v3/company/{realmId}/reports/BalanceSheet?summarize_column_by=Month&start_date={}&end_date={}` | assets, cash, accountsReceivable, liabilities, accountsPayable, longTermDebt | `balance_sheet` | 追加 |
| 5 | Profit & Loss Log | 利润表完整历史 | 同 P&L + batchId | `profit_and_loss_log` | 仅保留最新 batchId |
| 6 | Balance Sheet Log | 资产负债表完整历史 | 同 BS + batchId | `balance_sheet_log` | 仅保留最新 batchId |
| 7 | Close Date | 期末结账日期 | date, pullTime | `close_date` | 仅保留最新 batchId |

**实现类：**
- 数据拉取与解析：`QBODataServiceImpl`
- Redshift 写入：`QBOEtlWriteServiceImpl`
  - 多行 INSERT，每批 500 行
  - 参数化查询，防止 SQL 注入

### 4.4 Phase 3 — 回调通知

**同步成功** → `webQBOFeignClient.syncCompleted()`：
1. 更新 `company_quickbooks.status = "success"`
2. 批量更新 `quickbooks_category_account.number`（从 API 返回的账号信息）
3. 写入日志：`AIRFLOW_DAILY_SCHEDULE_END`（成功）
4. 上传 S3：`qbo/{companyId}/{batchId}/sync_summary.json`

**同步失败** → `webQBOFeignClient.syncFailed()`：
1. 更新 `company_quickbooks.status = "error"`（如果不是 Invalid）
2. 写入日志：`AIRFLOW_DAILY_SCHEDULE_END`（失败）+ 错误信息

---

## 5. 数据存储架构

### 5.1 PostgreSQL（主业务库）

| 表 | 用途 |
|----|------|
| `company_quickbooks` | QBO 连接状态（realmId、refreshToken、status、mode、isFirst） |
| `qbo_logs` | 全链路操作日志 |
| `quickbooks_category_account` | 账户分类映射配置 |
| `datasource` | 数据源元数据（parameters JSON 包含 Token） |
| `qbo_sync_record` | 同步记录（batchId、status、耗时、错误信息、每流行数） |

### 5.2 Amazon Redshift（数据仓库）

- **Schema 命名**：`quickbooks_{companyId}`（companyId 中 `-` 替换为 `_`）
- **7 张数据表**：见 Phase 2 表格
- **写入时机**：每次同步时由 ETL 服务直接写入
- **创建时机**：首次同步时 `ensureSchemaAndTables()` 自动建表

### 5.3 Amazon S3（日志备份）

- 路径：`qbo/{companyId}/{batchId}/`
- 文件：`token_refresh.json`、`sync_summary.json`

---

## 6. 完整时序图

```
┌──────┐     ┌───────────┐     ┌───────┐     ┌─────┐     ┌─────────┐     ┌────────┐
│ 用户  │     │  Web 服务  │     │ Intuit │     │ SQS │     │EventBridge│    │ETL 服务 │
└──┬───┘     └─────┬─────┘     └───┬───┘     └──┬──┘     └────┬────┘     └───┬────┘
   │  点击连接      │               │            │              │              │
   │───────────────>│               │            │              │              │
   │                │  302 重定向    │            │              │              │
   │<───────────────│               │            │              │              │
   │  授权页面       │               │            │              │              │
   │───────────────────────────────>│            │              │              │
   │                │  callback     │            │              │              │
   │                │<──────────────│            │              │              │
   │                │               │            │              │              │
   │                │── Token 交换 ─>│            │              │              │
   │                │<── Token ─────│            │              │              │
   │                │               │            │              │              │
   │                │── 保存 Token + Datasource  │              │              │
   │                │               │            │              │              │
   │                │── 创建 Schedule ──────────────────────────>│              │
   │                │               │            │              │              │
   │                │── 发送首次同步消息 ────────>│              │              │
   │                │               │            │              │              │
   │  重定向回前端   │               │            │              │              │
   │<───────────────│               │            │              │              │
   │                │               │            │              │              │
   │                │  消费 SQS 消息 │            │              │              │
   │                │<──────────────────────────│              │              │
   │                │               │            │              │              │
   │                │── 查询 DB（Token、分类）   │              │              │
   │                │               │            │              │              │
   │                │── OpenFeign: sync2 ─────────────────────────────────────>│
   │                │               │            │              │              │
   │                │               │            │              │  刷新 Token   │
   │                │               │<───────────────────────────────────────│
   │                │               │── 新 Token ──────────────────────────>│
   │                │               │            │              │              │
   │                │  tokenRefreshed 回调       │              │              │
   │                │<────────────────────────────────────────────────────────│
   │                │               │            │              │              │
   │                │               │            │              │  拉取 7 流    │
   │                │               │<───────────────────────────────────────│
   │                │               │── 数据 ────────────────────────────────>│
   │                │               │            │              │              │
   │                │               │            │              │ 写入 Redshift │
   │                │               │            │              │              │
   │                │  syncCompleted 回调        │              │              │
   │                │<────────────────────────────────────────────────────────│
   │                │               │            │              │              │
   │                │── 更新状态 & 日志          │              │              │
   │                │               │            │              │              │
   │                │               │  ┌─────────────────┐     │              │
   │                │               │  │ 每天 00:00 UTC  │     │              │
   │                │               │  │ 重复上述同步流程 │     │              │
   │                │               │  └─────────────────┘     │              │
```

---

## 7. 关键设计要点

| 要点 | 说明 |
|------|------|
| **异步解耦** | OAuth Callback 立即返回，三项后续操作全部异步，避免阻塞用户 |
| **Batch 追踪** | 每次同步生成唯一 `batchId`，贯穿日志、Redshift 清理、S3 备份 |
| **幂等设计** | EventBridge `createOrUpdateSchedule` 重复调用安全；Redshift 账户表 TRUNCATE，日志表基于 batchId 去重 |
| **Token 自动续期** | 每次同步前先刷新 Token，新 Token 回写 PostgreSQL，保证长期可用 |
| **失败隔离** | Token 刷新失败 → 状态标记 `Invalid`，不影响其他公司；同步失败 → 状态标记 `error`，下次调度重试 |
| **全链路日志** | `qbo_logs` 表记录每一步操作（连接、Token 刷新、同步开始/结束），支持问题排查 |
| **S3 备份** | Token 刷新和同步摘要持久化到 S3，用于审计和故障恢复 |

---

## 8. 涉及的核心代码文件

### Web 模块（`gstdev-cioaas-web`）

| 文件 | 职责 |
|------|------|
| `fi/controller/CompanyQuickbooksController.java` | OAuth 连接入口（connect、authorization、callback） |
| `fi/service/CompanyQuickbooksServiceImpl.java` | OAuth 流程、Datasource 保存、调度创建 |
| `fi/domain/CompanyQuickbooks.java` | `company_quickbooks` 表实体 |
| `fi/domain/QBOLog.java` | `qbo_logs` 表实体 |
| `quickbooks/scheduler/QBOSchedulerService.java` | EventBridge Scheduler + SQS 消息发送 |
| `quickbooks/scheduler/QBOScheduleProcessor.java` | SQS 消息消费 → 构造同步请求 |
| `quickbooks/sqs/QBOSqsMessagePoller.java` | SQS 监听器注册 |
| `quickbooks/controller/QBOCallbackController.java` | ETL 回调接收端点 |
| `quickbooks/service/QBOCallbackService.java` | 回调处理（Token 更新、状态更新、日志） |

### ETL 模块（`gstdev-cioaas-etl`）

| 文件 | 职责 |
|------|------|
| `quickbooks/controller/QBOSyncController.java` | 同步入口（sync2） |
| `qbosync/QBOSyncOrchestrator.java` | 三阶段同步编排 |
| `quickbooks/service/QBOTokenServiceImpl.java` | Token 刷新 |
| `quickbooks/service/QBODataServiceImpl.java` | QBO REST API 调用 + 数据解析 |
| `quickbooks/service/QBOEtlWriteServiceImpl.java` | Redshift 数据写入 |

### OpenFeign 模块（`gstdev-cioaas-openfeign`）

| 文件 | 职责 |
|------|------|
| `etl/QBOSyncFeignClient.java` | Web → ETL 同步请求 |
| `web/WebQBOFeignClient.java` | ETL → Web 回调通知（4 种回调） |
| `etl/dto/QBOSyncRequest.java` | 同步请求 DTO |

---

## 9. 日志 Action 枚举

| Action | 触发时机 |
|--------|---------|
| `CLICK_CONNECT_QBO` | 用户点击连接按钮 |
| `CONNECT_QBO_SUCCESS` | OAuth 连接成功 |
| `CONNECT_QBO_FAILED` | OAuth 连接失败 |
| `REFRESH_TOKEN_BEGIN` | Token 刷新开始 |
| `REFRESH_TOKEN_END` | Token 刷新结束（成功/失败） |
| `AIRFLOW_DAILY_SCHEDULE_BEGIN` | 每日同步开始 |
| `AIRFLOW_DAILY_SCHEDULE_END` | 每日同步结束（成功/失败） |
| `DISCONNECT_QBO` | 用户断开连接 |
