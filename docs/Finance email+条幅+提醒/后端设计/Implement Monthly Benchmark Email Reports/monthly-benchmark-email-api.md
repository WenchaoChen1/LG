# Monthly Benchmark Email — 前端对接文档

> 面向前端 / QA 团队的运维管理 API 文档。描述 Monthly Benchmark Email 模块的 7 个管理接口、枚举字典、典型使用场景及排查指南。
>
> **2026-04-29 修复批次（影响响应字段）**：
> - `DELETE /baselines` 现在返回真实的 `deletedHistoryRows` 计数（之前永远 0）
> - `GET /baselines` 返回的 `baseline.lastNotifiedAt` 在 FIRE/FIRST_FIRE 时被写入（之前永远 NULL）
> - `GET /runs` / `GET /runs/{runId}` 中 `silent_updated_count` / `first_fire_count` 不再因 PM portfolio fanout 翻倍

## 概述

Monthly Benchmark Email 是基于 `fi/benchmark/position` 数据的自动化通知模块，面向两类受众：

- **Company Admin（公司管理员）**：收到本公司的 6 项指标对比邮件
- **Portfolio Manager（投资组合经理）**：收到所辖 portfolio 下所有命中阈值的公司的汇总邮件

模块与既有功能的关系：

- 指标数据来源：`fi/benchmark/position` 模块输出的公司自身指标 + benchmark 分位数据
- 公司归属：`r_company_group` 表（公司 ↔ portfolio），只考虑 `status=0`（Active）
- 邮件发送：复用系统 SendGrid 通道，模板位于 `resources/templates/BenchmarkingReportCompanyAdmin.html` 和 `BenchmarkingReportPortfolioManager.html`
- 本模块新增 5 张物理表（见末尾"相关表结构"）

本文档描述的 7 个 API 面向运维 / 调试场景，不提供业务用户界面。

## 调度机制

| Cron | 时机 (UTC) | Phase | 用途 |
|---|---|---|---|
| `0 30 0 * * *` | 每日 00:30 | `DAILY` | 扫描新 closed month、修订触发的变化 |
| `0 45 0 25 * *` | 每月 25 日 00:45 | `MONTHLY_25TH` | 月度固定提醒，不看阈值 |

**幂等**：同一 `(phase, run_date, triggerType=SCHEDULED)` 只能执行一次；`triggerType=MANUAL` 不受约束，可重复触发（便于调试 / QA / 补偿）。

**异步执行**：`POST /runs` 立即返回 `runId`，实际扫描与发送在后台线程进行。`status=RUNNING` → `COMPLETED | FAILED`。

## 鉴权

沿用系统管理员 Bearer Token（与 CIOaas 其他管理 API 一致）。需具有管理员权限方可访问。

生产环境下，`DELETE /baselines` 返回 `HTTP 403 Forbidden`（避免误删）。

## Base URL

| 环境 | URL |
|---|---|
| 开发本地 | `http://localhost:5213/web` |
| test / uat / stage / prod | 由网关统一代理，前缀 `/api/web` |

## 通用响应结构

所有接口返回 `Result<T>` 包装：

```json
{
  "success": true,
  "code": "0",
  "message": "success",
  "data": { ... }
}
```

分页响应 `data` 为 Spring `Page<T>`：`{ content: [...], totalElements, number, size, ... }`，其中 `number` 为 0-based 页码。

---

## 1. 触发 Run — `POST /benchmark-email/runs`

**用途**：手动触发一次扫描，常用于 QA 反复验证、开发调试、线上出现漏发时补偿。

### 请求体

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `phase` | String | 是 | - | `DAILY` 或 `MONTHLY_25TH` |
| `dryRun` | Boolean | 否 | `false` | `true` 时仅计算快照，不写 baseline、不发邮件 |
| `targetCompanyIds` | String[] | 否 | 全部 eligible 公司 | 限定扫描公司列表 |
| `asOfDate` | String (yyyy-MM-dd) | 否 | 当前 UTC 日期 | 调试用，强制"今天"为指定日期 |

### 请求示例

```http
POST /benchmark-email/runs
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "phase": "DAILY",
  "dryRun": false,
  "targetCompanyIds": ["company-uuid-a", "company-uuid-b"]
}
```

### 成功响应

```json
{
  "success": true,
  "code": "0",
  "message": "success",
  "data": {
    "runId": "f8c1d3a0-....",
    "status": "RUNNING",
    "triggerType": "MANUAL"
  }
}
```

收到 `runId` 后，调用 API 2 / API 3 查询结果；`status` 会在几秒至几分钟内转为 `COMPLETED` / `FAILED`。

### 错误

| 场景 | HTTP | success / code | message |
|---|---|---|---|
| `phase` 非法 | 200 | `false / INVALID_PHASE` | `phase must be DAILY or MONTHLY_25TH` |
| `asOfDate` 格式错 | 400 | 由 `@DateTimeFormat` 抛出 | Spring 默认绑定错误 |
| Token 无效 | 401 | - | - |

---

## 2. 查询 Run 列表 — `GET /benchmark-email/runs`

**用途**：查看历史 run 概览，支持分页、过滤。前端可据此做"近 30 日扫描总览"页。

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `page` | int | 1 | 1-based 页码 |
| `size` | int | 20 | 每页条数 |
| `phase` | String | - | `DAILY` / `MONTHLY_25TH` |
| `triggerType` | String | - | `SCHEDULED` / `MANUAL` |
| `status` | String | - | `RUNNING` / `COMPLETED` / `FAILED` |
| `from` | Instant (ISO) | - | `runTriggerTime >= from`，例 `2026-04-01T00:00:00Z` |
| `to` | Instant (ISO) | - | `runTriggerTime <= to` |

### 响应

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "runId": "...",
        "phase": "DAILY",
        "triggerType": "SCHEDULED",
        "runDate": "2026-04-24",
        "runTriggerTime": "2026-04-24T00:30:01Z",
        "status": "COMPLETED",
        "adminFiredCount": 3,
        "pmFiredCount": 1,
        "silentUpdatedCount": 42,
        "firstFireCount": 0,
        "errorMessage": null
      }
    ],
    "totalElements": 128,
    "number": 0,
    "size": 20
  }
}
```

### 字段解读

- `adminFiredCount`：该 run 为 Company Admin 发出的邮件数
- `pmFiredCount`：为 Portfolio Manager 发出的邮件数
- `silentUpdatedCount`：未达阈值但静默更新了 baseline 的 (company × role) 对数
- `firstFireCount`：首封邮件数
- `errorMessage`：run 级别的错误（非单条快照错误）

---

## 3. Run 明细 — `GET /benchmark-email/runs/{runId}`

**用途**：查看某次 run 的逐行决策快照和邮件记录。排查"为什么没发"、"为什么发了"的核心入口。

### 路径参数

- `runId` — 从 API 1 / API 2 得到

### 可选过滤查询参数

| 参数 | 说明 |
|---|---|
| `companyId` | 限定公司 |
| `role` | `COMPANY_ADMIN` / `PORTFOLIO_MANAGER` |
| `decision` | `FIRST_FIRE` / `FIRE` / `SILENT` / `ERROR` |

### 响应结构

```json
{
  "success": true,
  "data": {
    "run": { /* RunSummary 同 API 2 */ },
    "snapshots": [
      {
        "companyId": "...",
        "role": "PORTFOLIO_MANAGER",
        "metricId": "arr",
        "benchmarkSource": "INTERNAL_PEERS",
        "dataSource": "ACTUALS",
        "closedMonth": "2026-03",
        "ownValue": 12000000.0,
        "percentile": 62.5,
        "percentileMarker": "~",
        "baselinePercentile": 55.0,
        "baselineMarker": null,
        "delta": 7.5,
        "crossedQuartile": false,
        "rowChangeType": "MEANINGFUL_CHANGE",
        "decision": "FIRE",
        "contributesToEmail": true,
        "errorMessage": null
      }
    ],
    "emails": [
      { /* SendLog 同 API 4 */ }
    ]
  }
}
```

### 字段解读

- `snapshots[]` 为 `(company × role × metric × benchmarkSource × dataSource)` 粒度；一次 run 每公司最多产生 2 (role) × 6 (metric) × 4 (benchmarkSource) × 3 (dataSource) = 144 行
- `decision` 为 `(company, role)` 级别聚合后的决策，在同一 (company, role) 下所有 snapshot 的 `decision` 一致
- `contributesToEmail`：该行是否出现在邮件正文中（PM 可能只展示 FIRE 行）

### 错误

| 场景 | code |
|---|---|
| runId 不存在 | `NOT_FOUND` |

---

## 4. 发送历史 — `GET /benchmark-email/sent-emails`

**用途**：审计 / 排查邮件发送失败。

### 查询参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `recipientUserId` | String | 按收件用户 ID 过滤 |
| `recipientEmail` | String | 按收件邮箱过滤（精确匹配） |
| `companyId` | String | 按公司过滤（PM 邮件有 `companyIdsInContent` 多值） |
| `status` | String | `SUCCESS` / `FAILED` / `PENDING` |
| `from` / `to` | Instant (ISO) | `createdAt` 时间范围 |
| `page` / `size` | int | 分页，默认 1 / 20 |

### 响应字段

每条 `SendLog`：

| 字段 | 说明 |
|---|---|
| `sendLogId` | 记录主键 |
| `runId` | 所属 run |
| `emailId` | 邮件逻辑 ID（可关联同批重发场景） |
| `role` | `COMPANY_ADMIN` / `PORTFOLIO_MANAGER` |
| `recipientUserId` / `recipientEmail` | 收件人 |
| `companyId` | PM 邮件为 `null` 或代表主公司 |
| `portfolioId` | PM 邮件专属 |
| `companyIdsInContent` | PM 邮件内容中包含的公司 ID 列表（逗号分隔） |
| `isFirstFire` | 是否为首封 |
| `sendStatus` | `PENDING` / `SUCCESS` / `FAILED` |
| `sendgridStatusCode` | SendGrid 返回的 HTTP 状态码 |
| `errorMessage` | 失败时的错误描述 |
| `createdAt` | 记录创建时间 |

---

## 5. 查看 Baseline — `GET /benchmark-email/baselines`

**用途**：查看某个 `(company, role)` 当前存储的 baseline，以及近 5 条变更历史。

### 查询参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `companyId` | 是 | 公司 ID |
| `role` | 是 | `COMPANY_ADMIN` / `PORTFOLIO_MANAGER` |
| `dataSource` | 否 | 限定数据源 |
| `benchmarkSource` | 否 | 限定 benchmark 来源 |

### 响应

```json
{
  "success": true,
  "data": {
    "companyId": "...",
    "role": "PORTFOLIO_MANAGER",
    "baselines": [
      {
        "metricId": "arr",
        "benchmarkSource": "INTERNAL_PEERS",
        "dataSource": "ACTUALS",
        "closedMonth": "2026-03",
        "percentile": 55.0,
        "percentileMarker": null,
        "ownValue": 11200000.0,
        "lastUpdatedRunId": "...",
        "lastUpdatedReason": "FIRE",
        "lastNotifiedAt": "2026-04-01T00:30:22Z",
        "history": [
          {
            "createdAt": "2026-04-01T00:30:22Z",
            "percentile": 55.0,
            "percentileMarker": null,
            "reason": "FIRE",
            "runId": "..."
          }
        ]
      }
    ]
  }
}
```

---

## 6. 删除 Baseline — `DELETE /benchmark-email/baselines`

> **生产环境返回 `403 Forbidden`**，仅在 dev / test / uat / stage 可调用。

**用途**：QA 反复验证首封场景；或 baseline 污染（如数据回滚）需清空后重新初始化。清空后，下次扫描会将该 `(company, role)` 按 `FIRST_FIRE` 处理。

### 查询参数

| 参数 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `companyId` | 是 | - | 公司 ID |
| `role` | 是 | - | `COMPANY_ADMIN` / `PORTFOLIO_MANAGER` |
| `deleteHistory` | 否 | `false` | 是否同时清空 `baseline_history` |

### 响应

```json
{
  "success": true,
  "data": {
    "deletedBaselineRows": 24,
    "deletedHistoryRows": 0
  }
}
```

### 错误

| 场景 | HTTP | 说明 |
|---|---|---|
| 生产环境调用 | 403 | `Delete baselines is disabled in prod` |

---

## 7. 预览邮件 — `POST /benchmark-email/preview`

> **当前为占位实现**，返回 subject + variables 与占位 HTML。完整渲染计划于后续迭代补齐。

### 请求体

| 字段 | 必填 | 说明 |
|---|---|---|
| `companyId` | 是 | 预览对象公司 |
| `role` | 是 | `COMPANY_ADMIN` / `PORTFOLIO_MANAGER` |
| `asOfDate` | 否 | 预览截止日期，默认当前 UTC |
| `sendTo` | 否 | 若提供，后续迭代会发送测试邮件；当前实现不发送 |

### 响应

```json
{
  "success": true,
  "data": {
    "subject": "Benchmarking Report preview for companyId=... role=PORTFOLIO_MANAGER asOf=2026-04-24",
    "html": "<p>Preview rendering is scheduled for a follow-up patch. ...</p>",
    "variables": {
      "companyId": "...",
      "role": "PORTFOLIO_MANAGER",
      "asOfDate": "2026-04-24",
      "sendTo": null
    },
    "sendStatus": null,
    "sendgridStatusCode": null,
    "emailId": null,
    "portfolioIdUsed": null
  }
}
```

---

## 枚举值字典

### `BenchmarkEmailRunPhaseEnum`

| 值 | 说明 |
|---|---|
| `DAILY` | 每日扫描（新 closed month、数据修订） |
| `MONTHLY_25TH` | 每月 25 日固定触发，不评估阈值 |

### `BenchmarkEmailTriggerTypeEnum`

| 值 | 说明 |
|---|---|
| `SCHEDULED` | Cron 自动触发 |
| `MANUAL` | 通过 API 1 手动触发 |

### `BenchmarkEmailRoleEnum`

| 值 | 说明 |
|---|---|
| `COMPANY_ADMIN` | 公司管理员。邮件只含本公司 6 项指标；每次触发必发 |
| `PORTFOLIO_MANAGER` | 投资组合经理。邮件按 portfolio 汇总多公司；看阈值 |

### `BenchmarkEmailDataSourceEnum`

| 值 | 说明 |
|---|---|
| `ACTUALS` | 实际数据（唯一参与阈值判定） |
| `COMMITTED_FORECAST` | 承诺预测（仅邮件展示） |
| `SYSTEM_GENERATED_FORECAST` | 系统生成预测（仅邮件展示） |

### `BenchmarkEmailBenchmarkSourceEnum`

| 值 | 说明 |
|---|---|
| `INTERNAL_PEERS` | 内部同行基准 |
| `KEYBANC` | KeyBanc 基准 |
| `HIGH_ALPHA` | High Alpha 基准 |
| `BENCHMARK_IT` | Benchmark IT 基准 |

### `BenchmarkEmailRowChangeTypeEnum`

| 值 | 条件 |
|---|---|
| `UNCHANGED` | baseline 与当前均为 NA，或值相等 |
| `MINOR_MOVE` | \|delta\| < 5 且未跨分位 |
| `MEANINGFUL_CHANGE` | \|delta\| ≥ 5 或跨 Q1/Q2/Q3/Q4 分位边界 |
| `VALUE_CHANGED_NA` | NA ↔ 有值的切换 |

### `BenchmarkEmailDecisionEnum`

| 值 | 说明 |
|---|---|
| `FIRST_FIRE` | 首封（baseline 为空，首次建立） |
| `FIRE` | 正常发送 |
| `SILENT` | PM 未达阈值；baseline 仍会静默更新；不发邮件 |
| `ERROR` | 该 (company, role) 处理过程中异常 |

### `BenchmarkEmailReasonEnum`（存于 `baseline.lastUpdatedReason`）

| 值 | 说明 |
|---|---|
| `FIRST_FIRE` | 首次建立 baseline |
| `FIRE` | 因阈值命中发邮件后更新 |
| `SILENT_NO_CHANGE` | 未变但 `MONTHLY_25TH` 仍更新 |
| `SILENT_BELOW_THRESHOLD` | PM 未达阈值，静默更新 |

### `sendStatus`（`send_log` 表）

| 值 | 说明 |
|---|---|
| `PENDING` | 记录已创建，SendGrid 调用进行中 |
| `SUCCESS` | SendGrid 返回 2xx |
| `FAILED` | SendGrid 返回非 2xx 或调用抛异常 |

### `percentileMarker` 取值

| 值 | 含义 |
|---|---|
| `null` | 精确值（如 P50 正好命中） |
| `~` | 线性插值（如 `~P62.5`） |
| `>P25` / `>P50` / `>P75` | 超出 benchmark 上界，以锚点前缀展示 |
| `<P25` / `<P50` / `<P75` / `<P100` | 超出 benchmark 下界 |

---

## 阈值规则（PM 发邮件判断逻辑）

PM 邮件判断仅看 **Actuals × 6 指标 × 4 benchmark** = 最多 24 个组合。Forecast 数据只展示在邮件里，不参与阈值评估。

任一组合满足以下任一条件即为"重大变化"：

- `|当前百分位 − baseline 百分位| ≥ 5`
- 跨分位边界（Q1/Q2/Q3/Q4，边界：`[0,25) / [25,50) / [50,75) / [75,100]`）
- NA ↔ 有值的切换（NA → Pxx 或 Pxx → NA）

聚合规则：

- **任一组合命中** → 整个 (company, PM) = `FIRE`，该公司进入 PM 邮件
- **全未命中** → `SILENT`，仅静默更新 baseline，不发邮件
- **首次** → `FIRST_FIRE`，直接发邮件并建立 baseline

## Admin 与 PM 的区别

| 维度 | Company Admin | Portfolio Manager |
|---|---|---|
| 触发事件 | 首封 / 新 closed month / 25 号 | 首封 / 新 closed month / 25 号 / 数据修订 |
| 阈值 | 不判，每次必发 | 判 24 组合阈值 |
| 邮件内容 | 本公司 6 指标固定 | Portfolio 下所有 FIRE/FIRST_FIRE 公司汇总 |
| baseline | 按 role 独立存储 | 按 role 独立存储 |
| 静默更新 | 无（always fire） | 未达阈值时仍更新 baseline |

---

## 排查指南

### "为什么这封邮件没发出去？"

1. **API 2** `GET /runs?from=...&to=...` 找到该日期的 run，确认 `status=COMPLETED`
2. **API 3** `GET /runs/{runId}?companyId=...&role=...` 查该 (company, role) 的 snapshots
3. 根据 snapshots 的 `decision` 判断：
   - `SILENT` → 未达阈值。逐行检查 `delta`、`crossedQuartile`、`rowChangeType`，对照阈值规则
   - `ERROR` → 看 `errorMessage`
   - `FIRE` / `FIRST_FIRE` 但 `emails[]` 对应 recipient 为 `FAILED` → 查 `errorMessage` 与 `sendgridStatusCode`
4. **API 4** `GET /sent-emails?companyId=...&status=FAILED` 筛选失败历史

### "为什么 PM 收不到邮件？"

- PM 收件逻辑依赖 `r_company_group` 表：若公司没有 `status=0`（Active）portfolio 归属，PM 无法定位
- **API 5** `GET /baselines?companyId=X&role=PORTFOLIO_MANAGER` 看 baseline 是否存在
- 若 baseline 为空 → 下次扫描会按首封处理；否则检查 snapshot 的 `decision`
- 检查 PM 用户在 `r_user_group` 中是否有对应 portfolio 的关联

### "想重测首封场景"

1. **API 6** `DELETE /baselines?companyId=X&role=Y&deleteHistory=true` 清空 baseline（仅非 prod）
2. **API 1** `POST /runs` 以 `DAILY` + MANUAL 触发
3. 观察 run 的 `firstFireCount` 应 > 0；查 **API 3** 确认 `decision=FIRST_FIRE`

### "想知道某封邮件具体包含哪些公司"

- **API 4** `GET /sent-emails?recipientEmail=...` 找到 `sendLogId`
- 响应中 `companyIdsInContent` 字段即为邮件正文包含的公司 ID 列表（PM 邮件有多值）

### "想看 baseline 的历史变动"

- **API 5** `GET /baselines?companyId=X&role=Y` 每条 baseline 自带近 5 条 `history`
- 更完整历史需查询后端日志 / 直连 `financial_benchmark_email_baseline_history` 表

### "Run 卡在 RUNNING 不动"

- Run 超 10 分钟仍为 `RUNNING` → 查服务端日志（`BenchmarkEmailOrchestratorImpl`）
- 系统重启可能导致异步任务中断；当前实现不自动恢复，需手动重触

---

## 相关表结构

参考 `deploy/upgrade_doc/sprint109/V4_benchmark-email-tables.sql`：

| 表 | 说明 |
|---|---|
| `financial_benchmark_email_run` | 每次 run 汇总（Phase / 状态 / 计数） |
| `financial_benchmark_email_run_snapshot` | 逐 (company × role × metric × benchmark × dataSource) 快照明细 |
| `financial_benchmark_email_baseline` | 当前 baseline（update-in-place） |
| `financial_benchmark_email_baseline_history` | baseline 变更历史（append-only） |
| `financial_benchmark_email_send_log` | 邮件发送日志（成功与失败） |

## 邮件模板

- `resources/templates/BenchmarkingReportCompanyAdmin.html`
- `resources/templates/BenchmarkingReportPortfolioManager.html`

## SwaggerUI

开发本地：`http://localhost:5213/web/swagger-ui/index.html` → 在标签区查找 **"Benchmark Email (Monthly)"**。

## 相关代码位置

| 类型 | 路径 |
|---|---|
| Controller | `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmarkemail/controller/BenchmarkEmailController.java` |
| Service（编排） | `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmarkemail/service/BenchmarkEmailOrchestratorImpl.java` |
| Service（baseline） | `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmarkemail/service/BaselineManager.java` |
| Scheduler | `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmarkemail/scheduler/BenchmarkEmailScheduleRegistrar.java` |
| 枚举 | `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmarkemail/enums/` |
| DDL | `deploy/upgrade_doc/sprint109/V4_benchmark-email-tables.sql` |
| 设计文档 | `docs/superpowers/specs/2026-04-24-monthly-benchmark-email-baseline-design.md` |
| 计划文档 | `docs/superpowers/plans/2026-04-24-monthly-benchmark-email.md` |

## 版本历史

| 日期 | 说明 |
|---|---|
| 2026-04-24 | 初版，覆盖 7 个管理 API 与枚举字典 |
