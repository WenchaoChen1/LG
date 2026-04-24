# 月度基准邮件（基准线管理版）· 技术设计

> 产出日期：2026-04-24
> 来源需求：`Implement Monthly Benchmark Email Reports_需求文档.md` + 用户补充描述（百分位变化基准线管理）
> 范围：后端实现 + 给前端/QA 的对接文档
> 关联：本设计与既有 `fi/benchmark/position/` 模块并存且互不感知

---

## 一、总览

### 1.1 业务目标

系统定期生成"基准位置变动"邮件，向两类收件人推送百分位变化：

- **Company Admin**：每次触发必收一封邮件，展示公司全量 6 指标 × 4 基准 × 3 数据类型的当前百分位与相对上次邮件的移动。
- **Portfolio Manager**：每次触发判定所在 Portfolio 下各公司是否有重大变化，只有有重大变化的公司才进入邮件，邮件按公司汇总展示达阈值的指标。

### 1.2 核心变化（相对既有 `fi/benchmark/position/` 的旧方案）

- 百分位变化 = **触发时当前 closed month 实时百分位** − **系统预存的基准百分位**；基准来自上次邮件触发或上次静默更新，**不再以"上个 closed month 的百分位"实时反算**。
- 新增独立模块 `fi/benchmarkemail/`，独立表结构，不共享旧 `fi/benchmark/position/` 的任何状态。
- 覆盖 6 指标 × 4 基准（Internal Peers / KeyBanc / High Alpha / Benchmarkit.ai）× 3 数据类型（Actuals / Committed Forecast / System Generated Forecast）= 最多 72 行/公司/角色。
- 阈值判定仅看 Actuals × 6 指标 × 4 基准 = 最多 24 组合；Forecast 不参与阈值判定但参与邮件展示。
- Baseline 按**角色**分开维护；Company Admin 与 Portfolio Manager 的基准相互独立。

### 1.3 非功能目标

| 项 | 目标 |
|---|---|
| 一次 DAILY run 计算耗时（1000 公司） | ≤ 15 min |
| 一次 run 邮件发送耗时 | ≤ 25 min |
| 单元测试覆盖率 | ≥ 80% |
| 并发 | 单 run 内 `processCompanyRole` 并行；SendGrid 串行 |

---

## 二、模块架构

### 2.1 包结构

```
CIOaas-api/gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmarkemail/
  ├── domain/
  │     ├── FinancialBenchmarkEmailRun.java
  │     ├── FinancialBenchmarkEmailRunSnapshot.java
  │     ├── FinancialBenchmarkEmailBaseline.java
  │     ├── FinancialBenchmarkEmailBaselineHistory.java
  │     └── FinancialBenchmarkEmailSendLog.java
  ├── repository/
  │     ├── BenchmarkEmailRunRepository.java
  │     ├── BenchmarkEmailRunSnapshotRepository.java
  │     ├── BenchmarkEmailBaselineRepository.java
  │     ├── BenchmarkEmailBaselineHistoryRepository.java
  │     └── BenchmarkEmailSendLogRepository.java
  ├── enums/
  │     ├── BenchmarkEmailRunPhaseEnum.java         (DAILY / MONTHLY_25TH)
  │     ├── BenchmarkEmailTriggerTypeEnum.java      (SCHEDULED / MANUAL)
  │     ├── BenchmarkEmailRoleEnum.java             (COMPANY_ADMIN / PORTFOLIO_MANAGER)
  │     ├── BenchmarkEmailDataSourceEnum.java       (ACTUALS / COMMITTED_FORECAST / SYSTEM_GENERATED_FORECAST)
  │     ├── BenchmarkEmailBenchmarkSourceEnum.java  (INTERNAL_PEERS / KEYBANC / HIGH_ALPHA / BENCHMARK_IT)
  │     ├── BenchmarkEmailRowChangeTypeEnum.java    (UNCHANGED / MINOR_MOVE / MEANINGFUL_CHANGE / VALUE_CHANGED_NA)
  │     └── BenchmarkEmailDecisionEnum.java         (FIRST_FIRE / FIRE / SILENT / ERROR)
  ├── service/
  │     ├── BenchmarkEmailOrchestrator.java                (接口)
  │     ├── BenchmarkEmailOrchestratorImpl.java
  │     ├── MonthlyEmailSnapshotBuilder.java
  │     ├── EmailDiffEvaluator.java
  │     ├── BaselineManager.java
  │     ├── CompanyAdminEmailComposer.java
  │     ├── PortfolioManagerEmailComposer.java
  │     ├── RecipientResolver.java
  │     └── EmailContentFormatter.java
  ├── controller/
  │     └── BenchmarkEmailController.java
  ├── scheduler/
  │     └── BenchmarkEmailScheduleRegistrar.java           (沿用现有 scheduler 模块注册)
  ├── vo/
  │     ├── request/ RunRequest.java · PreviewRequest.java · DeleteBaselineRequest.java
  │     └── response/ RunCreatedDto.java · RunSummaryDto.java · RunDetailDto.java · BaselineDto.java · SendLogDto.java · PreviewResponse.java
  └── util/
        └── QuartileUtil.java
```

### 2.2 依赖关系

```
Scheduler / Controller
    │
    └─→ BenchmarkEmailOrchestratorImpl
            ├─→ RecipientResolver        ──→ UserService
            ├─→ MonthlyEmailSnapshotBuilder
            │     ├─→ ClosedMonthResolver          (复用 fi.benchmark.position.service)
            │     ├─→ PeerGroupResolver            (复用 fi.benchmark.engine)
            │     ├─→ MetricExtractor              (复用 fi.benchmark.engine)
            │     ├─→ InternalPercentileCalculator (复用 fi.benchmark.engine)
            │     ├─→ ExternalBenchmarkMatcher     (复用 fi.benchmark.engine)
            │     └─→ ExternalPercentileCalculator (复用 fi.benchmark.engine)
            ├─→ BaselineManager ──→ BaselineRepository + BaselineHistoryRepository
            ├─→ EmailDiffEvaluator        (纯函数)
            ├─→ CompanyAdminEmailComposer
            │     ├─→ EmailContentFormatter
            │     └─→ EmailService (SendGrid)
            ├─→ PortfolioManagerEmailComposer
            │     ├─→ EmailContentFormatter
            │     └─→ EmailService (SendGrid)
            └─→ RunSnapshot / SendLog repositories
```

### 2.3 与旧 `fi/benchmark/position/` 的隔离

- 数据层：两套 baseline 表独立（`financial_benchmark_position_baseline` vs `financial_benchmark_email_baseline`），无外键或共享数据。
- 代码层：新模块不修改旧类；仅通过 `@Component` 注入方式复用 `ClosedMonthResolver` 与 `fi.benchmark.engine.*`。
- 调度层：新旧模块各自注册独立调度任务，彼此不感知。

---

## 三、数据模型

### 3.1 表 `financial_benchmark_email_run`

一次调度 run 的汇总记录。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(36) PK | UUID |
| run_trigger_time | timestamp | 触发时刻（UTC） |
| phase | varchar(16) | `DAILY` / `MONTHLY_25TH` |
| trigger_type | varchar(16) | `SCHEDULED` / `MANUAL` |
| run_date | date | 调度当天日期（UTC），用于幂等 |
| status | varchar(16) | `RUNNING` / `COMPLETED` / `FAILED` |
| admin_fired_count | int | 本 run 发给 Company Admin 的邮件数 |
| pm_fired_count | int | 发给 Portfolio Manager 的邮件数 |
| silent_updated_count | int | PM 静默更新 baseline 的行数 |
| first_fire_count | int | 首封判定的 (company, role) 数 |
| error_message | text | 顶层错误信息（可空） |
| created_at, created_by, updated_at, updated_by | 审计 | 继承 `AbstractCustomEntity` |

**索引 / 唯一键**
- 唯一：`(phase, run_date, trigger_type)` — `SCHEDULED` 幂等；`MANUAL` 不冲突
- 普通：`(run_trigger_time DESC)`、`(status)`

### 3.2 表 `financial_benchmark_email_run_snapshot`

run 内逐 (company × role × metric × benchmarkSource × dataSource) 的快照明细，**仅用于审计与调试**（diff 对比不读此表）。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(36) PK | UUID |
| run_id | varchar(36) | → `financial_benchmark_email_run.id` |
| company_id | varchar(36) | |
| role | varchar(24) | `COMPANY_ADMIN` / `PORTFOLIO_MANAGER` |
| metric_id | varchar(64) | |
| benchmark_source | varchar(16) | |
| data_source | varchar(24) | |
| closed_month | date | 本次解析出的 cm |
| own_value | numeric(20,6) | 公司原始指标值，可空 |
| percentile | numeric(6,2) | 本次计算百分位（用于阈值判定），可空（NA） |
| percentile_marker | varchar(8) | 展示标记：`NULL` / `~` / `>P25` / `>P50` / `>P75` / `<P25` / `<P50` / `<P75` / `<P100` |
| baseline_percentile | numeric(6,2) | 对比时 baseline 的百分位，可空 |
| baseline_marker | varchar(8) | 同上 |
| delta | numeric(6,2) | 百分位绝对差 |
| crossed_quartile | boolean | 是否跨分位边界 |
| row_change_type | varchar(24) | `UNCHANGED` / `MINOR_MOVE` / `MEANINGFUL_CHANGE` / `VALUE_CHANGED_NA` |
| decision | varchar(24) | 公司 × role 级别决策：`FIRST_FIRE` / `FIRE` / `SILENT` / `ERROR` |
| contributes_to_email | boolean | 本行是否进入邮件展示 |
| error_message | text | 本行异常 |
| created_at | timestamp | |

**索引**
- `(run_id)`、`(company_id, role)`、`(decision)`、`(run_id, company_id, role)`

### 3.3 表 `financial_benchmark_email_baseline`

核心状态表，`update-in-place`，每个 (company, role, metric, benchmarkSource, dataSource) 一行。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(36) PK | UUID |
| company_id | varchar(36) | |
| role | varchar(24) | |
| metric_id | varchar(64) | |
| benchmark_source | varchar(16) | |
| data_source | varchar(24) | |
| closed_month | date | 本 baseline 对应的 cm |
| percentile | numeric(6,2) | 基准百分位（用于计算），NULL 表示 NA |
| percentile_marker | varchar(8) | 展示标记（详见 §6.4），NULL 表示精确值 |
| own_value | numeric(20,6) | 当时的公司原始值（供 preview/审计） |
| last_updated_run_id | varchar(36) | 最近一次更新它的 runId |
| last_updated_reason | varchar(24) | `FIRST_FIRE` / `FIRE` / `SILENT_NO_CHANGE` / `SILENT_BELOW_THRESHOLD` |
| last_notified_at | timestamp | 上次因本 baseline 发邮件的时刻，未邮件触发时为 NULL |
| created_at, updated_at | 审计 | |

**索引 / 唯一键**
- 唯一：`(company_id, role, metric_id, benchmark_source, data_source)`
- 普通：`(company_id, role)`（整块读取时用）

**存储量估算**：1000 公司 × 2 角色 × 6 指标 × 4 基准 × 3 数据类型 = 144 000 行上限。

### 3.4 表 `financial_benchmark_email_baseline_history`

append-only，用于追溯 baseline 的每次变更。**只在 baseline 的 `percentile`/`percentile_marker` 发生变化时插入一行**，避免每日膨胀。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(36) PK | UUID |
| baseline_id | varchar(36) | → baseline 表 id |
| company_id | varchar(36) | 冗余 |
| role | varchar(24) | 冗余 |
| metric_id | varchar(64) | 冗余 |
| benchmark_source | varchar(16) | 冗余 |
| data_source | varchar(24) | 冗余 |
| closed_month | date | 此版本对应 cm |
| percentile | numeric(6,2) | 此版本百分位 |
| percentile_marker | varchar(8) | 展示标记（详见 §6.4） |
| own_value | numeric(20,6) | 此版本原始值 |
| run_id | varchar(36) | 产生此版本的 runId |
| reason | varchar(24) | `FIRST_FIRE` / `FIRE` / `SILENT_NO_CHANGE` / `SILENT_BELOW_THRESHOLD` |
| created_at | timestamp | |

**索引**
- `(baseline_id, created_at DESC)`、`(company_id, role)`、`(run_id)`

### 3.5 表 `financial_benchmark_email_send_log`

一次邮件发送的记录，与 `system.email` 表关联。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(36) PK | UUID |
| run_id | varchar(36) | |
| email_id | varchar(36) | → `system.email.id`（SendGrid 详情存那边） |
| role | varchar(24) | |
| recipient_user_id | varchar(36) | |
| recipient_email | varchar(128) | |
| company_id | varchar(36) | Admin 为所在公司，PM 为 NULL |
| portfolio_id | varchar(36) | PM 为所在 portfolio，Admin 为 NULL |
| company_ids_in_content | text | PM 邮件纳入的公司 id JSON 数组，Admin 为 NULL |
| is_first_fire | boolean | 是否首封 |
| send_status | varchar(16) | `PENDING` / `SUCCESS` / `FAILED` |
| sendgrid_status_code | int | SendGrid 返回码 |
| error_message | text | 失败原因 |
| created_at | timestamp | |

**索引**
- `(run_id)`、`(recipient_user_id, created_at DESC)`、`(company_id, created_at DESC)`、`(send_status)`

### 3.6 Flyway 脚本

```
CIOaas-api/gstdev-cioaas-web/src/main/resources/db/migration/
  V{next}__create_benchmark_email_tables.sql
```

内含 5 张表 DDL + 索引。不改任何旧表。不做存量数据 catch-up。

---

## 四、调度与触发流

### 4.1 调度注册

沿用现有 `scheduler` 模块注册两条固定规则，不使用 Spring `@Scheduled`：

| 任务 | Cron（UTC） | Phase |
|---|---|---|
| 每日扫描 | `0 30 0 * * *` | `DAILY` |
| 每月 25 号 | `0 45 0 25 * *` | `MONTHLY_25TH` |

两条触发互相独立，若同一天同一公司既有"新 closed month"又恰逢 25 号，可能收到两封邮件（用户在 Q4 已确认）。

### 4.2 幂等

```
定时触发：INSERT INTO run (phase, run_date, trigger_type='SCHEDULED', ...)
            ON CONFLICT (phase, run_date, trigger_type) DO NOTHING
          冲突时本节点直接返回，另一节点继续执行
手动触发：trigger_type='MANUAL'，不参与唯一约束，可重复
```

### 4.3 Orchestrator 主流程

```
Orchestrator.run(phase, triggerType, asOfDate?, targetCompanyIds?)
  1. 创建 run 行（status=RUNNING）
  2. 拉取候选公司：
       targetCompanyIds 非空 → 按 ID 过滤
       否则 → companyService.findActiveCompaniesInAnyPortfolio()
  3. 对每家 company × role ∈ {COMPANY_ADMIN, PORTFOLIO_MANAGER}：
       processCompanyRole(run, company, role, phase, asOfDate)
  4. 聚合与发送（见 4.5）
  5. 更新 run 汇总 counts 与 status
```

### 4.4 processCompanyRole 细节

```
processCompanyRole(run, company, role, phase, asOfDate):
  cm_now = ClosedMonthResolver.resolve(company.id, asOfDate ?? today)
  若 cm_now == null:
      写 run_snapshot 占位行 decision=ERROR, error_message="cm unresolved"
      return

  baselineMap = BaselineManager.loadAll(company.id, role)   // 72 行或空

  eventType =
      baselineMap.isEmpty()                         ? FIRST_FIRE      :
      phase == MONTHLY_25TH                         ? MONTHLY_25TH    :
      maxClosedMonth(baselineMap).isBefore(cm_now)  ? NEW_CLOSED_MONTH :
                                                      DATA_REVISION

  // Admin 跳过数据修订
  if role == COMPANY_ADMIN && eventType == DATA_REVISION: return

  snapshot = MonthlyEmailSnapshotBuilder.buildFor(company, cm_now)   // 最多 72 行

  outcomes = []
  for row in snapshot:
      base = baselineMap[row.key()]
      d = EmailDiffEvaluator.evaluateRow(base, row, row.dataSource)
      outcomes.add( RowOutcome(row, base, d) )

  companyDecision =
      eventType == FIRST_FIRE                             ? FIRST_FIRE :
      role == COMPANY_ADMIN                                ? FIRE        :
      outcomes.anyMatch(d.contributesToAlert)              ? FIRE        :
                                                              SILENT

  SnapshotWriter.writeAll(run.id, company, role, cm_now, outcomes, companyDecision)

  run.accumulate( ProcessedResult(company, role, companyDecision, eventType,
                                  outcomes, cm_now) )
```

### 4.5 聚合与发送

```
aggregateAndSend(run, results):
  // ── baseline 先独立事务写入 ──
  @Transactional
  for r in results where r.companyDecision in {FIRST_FIRE, FIRE, SILENT}:
      BaselineManager.upsertAll(r)       // 写 baseline + 按需写 history

  // ── Admin 邮件 ──
  for r in results where r.role == COMPANY_ADMIN and r.companyDecision in {FIRST_FIRE, FIRE}:
      recipients = RecipientResolver.companyAdminsOf(r.companyId)
      for u in recipients:
          sendLogId = writePendingSendLog(run.id, r, u)
          html = CompanyAdminEmailComposer.compose(r, u)
          result = EmailService.sendEmail(...)
          updateSendLog(sendLogId, result)

  // ── PM 汇总邮件 ──
  // 每家公司的 FIRST_FIRE / FIRE / SILENT 由 §4.4 决定；SILENT 不进邮件
  firedByPortfolio = groupByPortfolio(results.filter(r.role==PM && r.companyDecision in {FIRST_FIRE, FIRE}))
  for (portfolio, companyResults) in firedByPortfolio:
      recipients = RecipientResolver.portfolioManagersOf(portfolio)
      for pm in recipients:
          sendLogId = writePendingSendLog(run.id, portfolio, pm)
          // Composer 内部按每家公司的 companyDecision 独立渲染：
          //   FIRST_FIRE → 全 6 指标、无 moved from
          //   FIRE       → 仅达阈值指标、带 moved from
          html = PortfolioManagerEmailComposer.compose(portfolio, companyResults, pm)
          result = EmailService.sendEmail(...)
          updateSendLog(sendLogId, result)
```

**关键不变式**：
- baseline 写入与 SendGrid 调用**解耦**——SendGrid 失败不回滚 baseline，失败通过 `send_log` 追溯（用户在 Q11③④ 已确认）。
- 同一人兼任 CompanyAdmin + PM 时，分别接收两封邮件（各自角色视角）。

### 4.6 事件分类真值表

| role | eventType | Actuals 24 组合有变化? | decision | 写 baseline? | 发邮件? |
|---|---|---|---|---|---|
| COMPANY_ADMIN | FIRST_FIRE | — | FIRST_FIRE | ✅ | ✅ |
| COMPANY_ADMIN | NEW_CLOSED_MONTH | — | FIRE | ✅ | ✅ |
| COMPANY_ADMIN | MONTHLY_25TH | — | FIRE | ✅ | ✅ |
| COMPANY_ADMIN | DATA_REVISION | — | 跳过 | ❌ | ❌ |
| PORTFOLIO_MANAGER | FIRST_FIRE | — | FIRST_FIRE | ✅ | ✅（所有公司全 6 指标） |
| PORTFOLIO_MANAGER | NEW_CLOSED_MONTH / MONTHLY_25TH | 是 | FIRE | ✅ | ✅（仅该公司达阈值指标） |
| PORTFOLIO_MANAGER | NEW_CLOSED_MONTH / MONTHLY_25TH | 否 | SILENT | ✅ | ❌ |
| PORTFOLIO_MANAGER | DATA_REVISION | 是 | FIRE | ✅ | ✅ |
| PORTFOLIO_MANAGER | DATA_REVISION | 否 | SILENT | ✅ | ❌ |

---

## 五、Diff 引擎

### 5.1 QuartileUtil

```
Q1: [0,   25)        P0  … P24.99
Q2: [25,  50)        P25 … P49.99
Q3: [50,  75)        P50 … P74.99
Q4: [75, 100]        P75 … P100
NA: 不归属任何 Q
```

```java
public static int quartileOf(BigDecimal p) {
    if (p == null) return -1;
    double v = p.doubleValue();
    if (v < 25) return 1;
    if (v < 50) return 2;
    if (v < 75) return 3;
    return 4;
}

public static boolean crossedQuartile(BigDecimal a, BigDecimal b) {
    int qa = quartileOf(a), qb = quartileOf(b);
    return qa != -1 && qb != -1 && qa != qb;
}
```

### 5.2 EmailDiffEvaluator

```java
@Component
public class EmailDiffEvaluator {

    private static final BigDecimal THRESHOLD = new BigDecimal("5");

    public RowDecision evaluateRow(Baseline baseline,
                                   SnapshotRow snapshot,
                                   BenchmarkEmailDataSourceEnum dataSource) {
        BigDecimal baseP = baseline == null ? null : baseline.getPercentile();
        BigDecimal nowP  = snapshot.getPercentile();

        // 双端 NA：无变化，不参与阈值
        if (baseP == null && nowP == null) {
            return new RowDecision(RowChangeType.UNCHANGED, null, false);
        }

        // 单端 NA：算重大变化；contributesToAlert 仅对 ACTUALS 为 true
        if (baseP == null || nowP == null) {
            boolean contributes = (dataSource == ACTUALS);
            return new RowDecision(RowChangeType.VALUE_CHANGED_NA, null, contributes);
        }

        BigDecimal delta = nowP.subtract(baseP).abs();
        boolean crossed = QuartileUtil.crossedQuartile(baseP, nowP);
        boolean movedEnough = delta.compareTo(THRESHOLD) >= 0;
        boolean contributes = (dataSource == ACTUALS) && (movedEnough || crossed);

        RowChangeType type =
            contributes                ? RowChangeType.MEANINGFUL_CHANGE :
            delta.signum() == 0        ? RowChangeType.UNCHANGED         :
                                          RowChangeType.MINOR_MOVE;
        return new RowDecision(type, delta, contributes);
    }
}
```

### 5.3 规则一览

| 本次 percentile | baseline percentile | 结果 | contributesToAlert（仅 ACTUALS） |
|---|---|---|---|
| NA | NA | UNCHANGED | false |
| 有值 | NA 或行不存在 | VALUE_CHANGED_NA | true |
| NA | 有值 | VALUE_CHANGED_NA | true |
| 有值 A | 有值 B，\|A−B\|≥5 或 跨 Q | MEANINGFUL_CHANGE | true |
| 有值 A | 有值 B，0<\|A−B\|<5 且不跨 Q | MINOR_MOVE | false |
| 有值 A | 有值 A | UNCHANGED | false |

---

## 六、Snapshot 构建

### 6.1 MonthlyEmailSnapshotBuilder

对一家公司一次性构建 72 行 (metric × benchmarkSource × dataSource) 快照：

```java
public SnapshotBundle buildFor(Invite company, LocalDate closedMonth) {
    String monthStr = String.format("%04d-%02d", closedMonth.getYear(), closedMonth.getMonthValue());
    SnapshotBundle bundle = new SnapshotBundle(company.getId(), closedMonth);

    for (BenchmarkEmailDataSourceEnum ds : DATA_SOURCES) {
        DataSourceEnum engineDs = toEngineDataSource(ds);
        PeerGroupResult peerResult = peerGroupResolver.resolve(company, monthStr, engineDs);

        for (MetricEnum metric : MONITORED_METRICS) {
            BigDecimal ownValue = metricValueLoader.load(company.id, metric.metricId, closedMonth, engineDs);
            List<BigDecimal> peerValues = loadPeerValues(peerResult.peerIds, metric.metricId, closedMonth, engineDs);

            // Internal Peers
            BigDecimal internalP = computeInternalPercentile(ownValue, peerValues, metric);
            bundle.put(metric, INTERNAL_PEERS, ds, ownValue, internalP, null);

            // 3 家外部基准
            int benchmarkYear = closedMonth.getYear();
            BigDecimal companyArr = metricValueLoader.loadArr(company.id, closedMonth, engineDs);
            for (ExternalPlatform platform : EXTERNAL_PLATFORMS) {
                BenchmarkDetail detail = externalBenchmarkMatcher.match(metric, platform, benchmarkYear, companyArr);
                ExternalPercentileResult er = (detail == null) ? ExternalPercentileResult.NA
                    : externalPercentileCalculator.calculate(ownValue, detail, metric);
                bundle.put(metric, platform.toBenchmarkSource(), ds,
                           ownValue, er.percentile(), er.marker());
            }
        }
    }
    return bundle;
}
```

### 6.2 缓存（单 run 内）

| 缓存 | 键 | 值 |
|---|---|---|
| peerGroupCache | `(companyId, month, dataSource)` | `PeerGroupResult` |
| peerValuesCache | `(peerGroupSignature, metricId, month, dataSource)` | `List<BigDecimal>` |
| externalBenchmarkCache | `(metricId, platform, year, arrBucket)` | `BenchmarkDetail` |

缓存 scope 限定单次 run，避免跨 run 污染。

### 6.3 外部基准 year/edition

直接复用 `ExternalBenchmarkMatcher` 的现有匹配逻辑（含 year + segmentType=ARR + segmentValue 匹配 + 回退）。

### 6.4 百分位展示标记（marker）

marker 字段存"展示层前缀"，由 `ExternalPercentileCalculator` 原样透传；percentile 字段始终存"用于阈值判定和计算的数值"。

| 来源 | 场景 | marker | percentile（计算用） | 邮件展示示例 |
|---|---|---|---|---|
| Internal Peers | 精确排名 | `NULL` | 精确值 | `P63` |
| External | 精确匹配 | `NULL` | 精确值 | `P55` |
| External | 线性插值 | `~` | 插值后精确值 62.5 | `~P62.5` |
| External | 超上界（完整 P25/50/75） | `>P75` | 边界值 100 | `>P75` |
| External | 超下界（完整 P25/50/75） | `<P25` | 边界值 0 | `<P25` |
| External | 仅部分 P 值可用（PRD §6.1.2 规则 4） | `>P25` / `>P50` / `<P50` / `<P75` / `<P100` 等 | 按 PRD §6.1.2 规则 4 取相邻锚点 | 原样 |
| NA | 无数据 | `NULL` | `NULL` | `N/A` |

**阈值判定**：只用 `percentile` 数值字段比较；`marker` 不参与判定。例如 `marker='>P75', percentile=100` → `marker='>P75', percentile=100` 的前后对比 delta=0，不触发阈值（即使公司 own_value 变化了但仍在 >P75 范围内，符合"汇总使用边界值"的 PRD 语义）。

---

## 七、邮件模板与 Composer

### 7.1 Thymeleaf 模板位置

```
CIOaas-api/gstdev-cioaas-web/src/main/resources/templates/
  ├── BenchmarkingReportCompanyAdmin.html
  └── BenchmarkingReportPortfolioManager.html
```

### 7.2 Company Admin 模板

**标题**：`Benchmarking Report for ${companyName} — ${closedMonthDisplay}`
例：`Benchmarking Report for Card Medic — March 2026`

**正文骨架**：

```
Hello ${adminDisplayName}

Your latest financials for ${companyName} have been updated through ${closedMonthDisplay}.
Benchmark movement reflects updated company financials. Below is a summary of how
your company's performance compares to both industry benchmarks and your peers in
Looking Glass:

── 6 指标板块，固定顺序 ──
ARR Growth Rate
  Actuals
    Actual: 64%
    Internal Peers: P63 ↑ (moved up from P58)
    KeyBanc 2026: P55
    High Alpha 2026: P55 ↓ (moved down from P70)
    Benchmarkit.ai 2026: P55
  Committed Forecast             (若有)
    Committed Forecast: 64%
    Internal Peers: P58
    KeyBanc 2026: ~P62.5         ← marker='~'
    High Alpha 2026: P52
    Benchmarkit.ai 2026: >P75    ← marker='>P75'
  System Generated Forecast      (若无 CF 才展示)
    ...

Gross Margin ... Monthly Net Burn Rate ... Monthly Runway ...
Rule of 40 ... Sales Efficiency Ratio

[View in Looking Glass]  → /Finance?params=<Base64(companyId + active=5 + userId)>
```

**行数据展示规则**：
- 指标顺序固定：ARR Growth Rate / Gross Margin / Monthly Net Burn Rate / Monthly Runway / Rule of 40 / Sales Efficiency Ratio
- Forecast 行选择：Committed Forecast 优先；无 CF 才展示 System Generated Forecast；两者都无则省略该 dataSource 行
- 基准顺序：Internal Peers → KeyBanc → High Alpha → Benchmarkit.ai
- 首封（FIRST_FIRE）：无 `moved from` 文案，仅显示当前百分位

### 7.3 Portfolio Manager 模板

**标题**：`Your Benchmarking Summarized Report is Ready`

**正文骨架（统一，不区分首封/非首封的整体形态）**：

```
Hello ${pmDisplayName}

Your latest financials for ${portfolioName} have been updated.
Benchmark movement reflects updated company financials. Below is a summary of
companies with meaningful changes in benchmark positioning based on the latest
financial updates.

Companies with Meaningful Benchmark Changes
  ${company1Name}      ← 按英文 A-Z、中文首字母 A-Z；英文在前
  ${company2Name}
  ${company3Name}

── 每家公司一个 section（按上述排序）──

${companyName}
  [该公司的展示指标 — 依该公司 companyDecision 决定，见 §7.4]
    Actuals
      Actual: <value>
      Internal Peers: <formatted>
      KeyBanc 2026: <formatted>
      High Alpha 2026: <formatted>
      Benchmarkit.ai 2026: <formatted>
    Committed Forecast (若有)
      ...
    System Generated Forecast (若无 CF 才展示)
      ...

[View in Looking Glass]  → /company?params=<Base64(portfolioId + active=5 + userId + organizationId)>
```

**每家公司 section 的渲染规则（由该公司的 companyDecision 决定）**：
- `FIRST_FIRE`（该公司的 PM baseline 不存在）：展示全 6 指标；所有行**无** `moved from` 文案
- `FIRE`（该公司本次达阈值）：仅展示"在任一基准下 Actuals 行 contributesToAlert=true"的指标；指标被选中后，该指标的 4 基准 × (Actuals + Committed Forecast/SGF) 全部展示；所有行**带** `moved from` 文案
- `SILENT`：该公司不进入邮件

**混合场景示例**：portfolio 下公司 A 是首次加入（FIRST_FIRE，展示全 6 指标）、公司 B 本次 ARR Growth Rate 达阈值（FIRE，仅展示 ARR Growth Rate 指标）、公司 C 无变化（SILENT，不进邮件）。邮件里出现 A + B 两家公司，各自按自己的渲染规则展示。

### 7.4 "哪些指标/哪些行进入邮件" 规则

| role | companyDecision | 该公司进入邮件的行 |
|---|---|---|
| COMPANY_ADMIN | FIRST_FIRE | 全 72 行（6 指标 × 4 基准 × 3 dataSource，Forecast 行按 Committed > SGF 择一）；**无 moved from** 文案 |
| COMPANY_ADMIN | FIRE | 全 72 行；带 moved from |
| PORTFOLIO_MANAGER | FIRST_FIRE | 该公司的全 72 行；**无 moved from** |
| PORTFOLIO_MANAGER | FIRE | 仅 "该指标在任一基准的 ACTUALS 行 contributesToAlert=true" 的指标；指标选中后该指标下的 4 基准 × 3 dataSource 全部展示（保持卡片结构完整）；带 moved from |
| PORTFOLIO_MANAGER | SILENT | 该公司不进入邮件 |

每家公司独立判定 companyDecision，一封 PM 邮件内可混合 FIRST_FIRE 和 FIRE 两种公司 section。

### 7.5 EmailContentFormatter 规则

```java
formatPercentile(BigDecimal p, String marker):
  if p == null: return "N/A"
  if marker != null and marker.startsWith(">") or marker.startsWith("<"):
      return marker                         // 直接返回 ">P75" / "<P25" / ">P25" 等
  if marker == "~":
      return "~P" + stripTrailingZeros(p)   // "~P62.5"
  return "P" + stripTrailingZeros(p)        // 精确值 "P63"

formatPercentileWithMovement(curr, currMarker, base, baseMarker, isFirstFire, dataSource):
  currText = formatPercentile(curr, currMarker)
  if isFirstFire:                return currText
  if curr == null && base == null:   return currText
  if base == null && curr != null:   return currText     // 首次有值，不展示 moved
  if curr == null && base != null:   return currText + " (previously " + formatPercentile(base, baseMarker) + ")"
  cmp = curr.compareTo(base)
  if cmp == 0:                       return currText
  arrow = cmp > 0 ? "↑" : "↓"
  verb  = cmp > 0 ? "up" : "down"
  return currText + " " + arrow + " (moved " + verb + " from " + formatPercentile(base, baseMarker) + ")"
```

Forecast 行也走 `formatPercentileWithMovement`，展示 moved from。

### 7.6 超范围标记的具体输出

`ExternalPercentileCalculator` 返回的 marker 原样透传：可为 `>P75` / `<P25` / `>P25` / `>P50` / `<P50` / `<P75` / `<P100` 等（见 §6.4 表）。本模块不做简化或合并。baseline / run_snapshot / history 三张表的 marker 字段均为 varchar(8)，足够容纳所有形式。

---

## 八、管理 API

**路由前缀**：`/benchmark-email`
**权限**：沿用系统管理员鉴权
**响应壳**：统一 `Result<T>`

### 8.1 POST `/benchmark-email/runs` — 手动触发 run

**Request**：
```json
{
  "phase": "DAILY",
  "dryRun": false,
  "targetCompanyIds": ["cmp-xxx"],
  "asOfDate": "2026-04-24"
}
```
- `phase`：`DAILY` / `MONTHLY_25TH`（必填）
- `dryRun`：true 时只计算写 run_snapshot，不写 baseline、不发邮件
- `targetCompanyIds`：不传 = 全量 eligibleCompanies
- `asOfDate`：不传 = 今天；调试用

**Response**：`Result<{ runId, status="RUNNING", triggerType="MANUAL" }>`

**行为**：立即返回 runId，实际执行在后台线程（`ThreadPoolTaskExecutor`）

**错误**：400（phase 非法 / companyId 不存在）

### 8.2 GET `/benchmark-email/runs` — 查 run 列表

**Query**：`page, size, phase, triggerType, status, from, to`

**Response**：`Result<Page<RunSummaryDto>>`

### 8.3 GET `/benchmark-email/runs/{runId}` — 查 run 明细

**Query**（可选过滤）：`companyId, role, decision`

**Response**：`Result<RunDetailDto>`，包含 run 汇总 + snapshots 列表 + 关联 emails

### 8.4 GET `/benchmark-email/sent-emails` — 查发送历史

**Query**：`recipientUserId, recipientEmail, companyId, status, from, to, page, size`

**Response**：`Result<Page<SendLogDto>>`

### 8.5 GET `/benchmark-email/baselines` — 查 baseline

**Query**（必填：`companyId, role`；可选：`dataSource, benchmarkSource`）

**Response**：`Result<BaselineDto>`，包含 baseline 行 + 最近 N 条 history（默认 N=5）

### 8.6 DELETE `/benchmark-email/baselines` — 清空 baseline

**Query**（必填：`companyId, role`；可选 `deleteHistory=false`）

**Response**：`Result<{ deletedBaselineRows, deletedHistoryRows }>`

**行为**：
- `prod` 环境直接 403（通过 `@Value("${cio.system.environment}")` 判定）
- 非 prod 环境正常执行；幂等

### 8.7 POST `/benchmark-email/preview` — 预览/测发

**Request**：
```json
{
  "companyId": "...",
  "role": "COMPANY_ADMIN",
  "asOfDate": "2026-04-24",
  "sendTo": "dev@example.com"
}
```

**Response**：
```json
{
  "success": true,
  "data": {
    "subject": "Benchmarking Report for Card Medic — March 2026",
    "html": "<html>...</html>",
    "variables": { /* thymeleaf context 回显 */ },
    "sendStatus": "SUCCESS",
    "sendgridStatusCode": 202,
    "emailId": "..."
  }
}
```

**行为**：
- 完全只读真实 baseline（不支持 overrideBaseline）
- 不写 run / run_snapshot / send_log / baseline
- 有 `sendTo` 时真发；否则仅返回 HTML
- PM 预览：portfolioId 从 company 自动推导（取该公司所在任一 portfolio），响应中回显使用的 portfolioId

---

## 九、错误处理

### 9.1 分层策略

| 失败粒度 | 处理 |
|---|---|
| 单行 percentile 计算异常 | run_snapshot 行 decision=ERROR + error_message；继续下一行；baseline 不更新 |
| 单 (company, role) 失败 | 写占位 ERROR 行，继续下一个 |
| 单封邮件 SendGrid 失败 | send_log.send_status=FAILED + sendgrid_status_code + error_message；baseline 不回滚；不自动重试 |
| run 整体致命异常 | run.status=FAILED + error_message；后续 run 不受影响 |

### 9.2 异常映射

| 异常 | HTTP |
|---|---|
| `DataNotFoundException` | 404 |
| `IllegalArgumentException` / `ServiceException` | 400 |
| prod 环境访问 `DELETE /baselines` | 403（`ForbiddenInProdException`） |
| SendGrid `IOException` | 不向上抛，写 send_log |

### 9.3 事务边界

- `writeBaselines(results)`：单事务，upsert baseline + 按需写 history
- `writePendingSendLog(...)`：单事务（short-lived）
- `EmailService.sendEmail(...)`：事务外（HTTP 调用）
- `updateSendLog(...)`：单事务（short-lived）

SendGrid 调用放事务外，避免长事务占用 DB 连接。

---

## 十、性能与并发

### 10.1 并发模型

- 单 run 内：`processCompanyRole` 用 `ThreadPoolTaskExecutor`（默认 10 线程）并行跑；引擎层缓存用 `ConcurrentHashMap`
- SendGrid 发送：顺序执行，避免触发外部限流
- 数据库写入：同公司同角色串行（避免行锁冲突）

### 10.2 批量加载

- 单次 run 启动时批量加载：eligibleCompanies、company→admin 映射、company→portfolio→PM 映射
- 每家公司 × dataSource 查询 `financial_normalization_current` 时用单条 SQL `WHERE (companyId IN (...)) AND date = ?`
- ExternalBenchmarkMatcher 结果按 (metric, platform, year, arrBucket) 缓存

### 10.3 性能目标

| 指标 | 目标（1000 公司场景） |
|---|---|
| 计算阶段总耗时 | ≤ 15 min |
| 邮件发送总耗时 | ≤ 25 min |
| 单 (company, role) 平均耗时 | ≤ 300 ms |

---

## 十一、测试策略

### 11.1 单元测试（JUnit 5 + Mockito）

| 类 | 覆盖要点 |
|---|---|
| `QuartileUtil` | P0/P25/P50/P75/P100 边界；NA；跨 Q |
| `EmailDiffEvaluator` | 双端 NA / 单端 NA / Δ<5 / Δ=5 / Δ>5 / 跨 Q / ACTUALS vs Forecast 的 contributesToAlert 差异 |
| `EmailContentFormatter` | 精确值 / marker=~ / marker=> / marker=< / NA / 首封无 moved / 首次出现 / 值→NA / NA→值 |
| `MonthlyEmailSnapshotBuilder` | 72 行组装；缓存命中；external 匹配失败返回 null |
| `BaselineManager` | upsert + 按需 history；NA 行也要写；变化才写 history |
| `BenchmarkEmailOrchestratorImpl` | 事件分类；Admin 跳过 DATA_REVISION；baselineMap empty → FIRST_FIRE |
| `RecipientResolver` | 公司无 Admin；PM 无邮箱；同一人兼 Admin+PM |

**覆盖率目标：≥ 80%**

### 11.2 集成测试（SpringBootTest + TestContainers PostgreSQL）

- 端到端单 DAILY run：fixture 数据 → 跑一次 → 断言 baseline/run_snapshot/send_log
- 同日 SCHEDULED 冲突：第二次注册拒绝；MANUAL 正常
- 同日 MONTHLY_25TH + DAILY：两次 run 都跑，发两封邮件
- 首封 → 下一次扫描：baseline 存在，非 FIRST_FIRE，按阈值判定
- SendGrid 失败：`EmailService` mock 抛异常，baseline 仍成功入库，send_log FAILED

### 11.3 Mock 边界

- `EmailService.sendEmail` 默认 mock 返回 `Pair.of(true, "mocked")`
- 生产 SendGrid 走现有白名单机制（stage/uat 仅白名单+@qq.com）

---

## 十二、安全

- `POST /runs`、`DELETE /baselines`、`POST /preview` 需管理员鉴权
- `DELETE /baselines` 在 `prod` 环境硬禁用
- 邮件地址从 `UserEmailDto` 取，不接收外部传入
- `send_log.error_message` 不包含完整请求体或敏感字段

---

## 十三、可观测性

- 结构化日志（`logging` 模块）：run 起止 INFO；每 (company, role) 处理 DEBUG；异常 ERROR 带 runId
- Sentry：捕获 `orchestrator.executeRun` 未捕获异常
- 度量（如环境已接 Micrometer）：`benchmark_email.run.duration` / `benchmark_email.fired.count` / `benchmark_email.silent.count`

---

## 十四、部署与交付物

### 14.1 数据库迁移

- Flyway 脚本 `V{next}__create_benchmark_email_tables.sql`
- 不改旧表；不跑 catch-up；首次部署等定时器自然触发

### 14.2 代码交付

- 模块 `fi/benchmarkemail/`（完整结构见 §2.1）
- `ClosedMonthResolver` / `fi.benchmark.engine.*` 仅注入复用，不修改

### 14.3 文档交付

1. SpringDoc OpenAPI 注解 → `/swagger-ui`
2. Markdown 对接文档：`docs/Benchmark/monthly-benchmark-email-api.md`
   - 模块简介 + 业务流程图
   - 调度规则
   - 表结构说明
   - 7 个 API 的请求/响应示例（含错误码）
   - 邮件模板截图 / 样例
   - 典型排查路径（run → snapshot → send_log）

### 14.4 工作量估算

| 模块 | 人·日 |
|---|---|
| DDL + domain + repository + enums | 1 |
| MonthlyEmailSnapshotBuilder + 缓存 | 2 |
| EmailDiffEvaluator + QuartileUtil + 单测 | 1 |
| BaselineManager + history + 单测 | 1 |
| Orchestrator + 事件分类 + 并发 | 2 |
| Scheduler 集成 | 0.5 |
| 两个 Email Composer + 两套 Thymeleaf 模板 | 2 |
| EmailContentFormatter + marker + 单测 | 1 |
| 7 个 API controller + DTO + swagger | 2 |
| 集成测试 + fixture | 2 |
| Markdown 对接文档 | 1 |
| **合计** | **15.5** |

---

## 十五、决策清单（与用户逐一确认过的条目）

1. 新模块独立，不修改旧 `fi/benchmark/position/`
2. baseline 按 role 区分：`(company, metric, benchmarkSource, role, dataSource)` 五维
3. 3 种 dataSource 都存 baseline；**阈值判定仅看 Actuals**
4. 阈值 = 24 组合（6 × 4）任一达标；"达标" = \|Δ\|≥5 或 跨 Q1/Q2/Q3/Q4 或 NA↔有值
5. 首封判定 = `baselineMap.isEmpty()`
6. 对比方式：直接比百分位
7. Admin 触发：首封 / 新 closed month / 25 号；每次必发；不对"数据修订"触发
8. PM 触发：首封 / 新 closed month / 25 号 / 数据修订；按阈值判定 FIRE or SILENT
9. 同日两种触发独立发送，允许同一人同日两封
10. Admin 邮件：固定全 6 指标；PM 邮件按公司聚合，每家公司独立判定 FIRST_FIRE（全 6 指标、无 moved from）/ FIRE（仅达阈值指标、带 moved from）/ SILENT（不进邮件）
11. Forecast 行带 `moved from` 文案
12. 百分位展示支持 `~`/`>`/`<` 标记
13. 分位边界 `[0,25)/[25,50)/[50,75)/[75,100]`；P50→Q3；P75→Q4
14. 第三方平台匹配复用现有 engine
15. 调度 UTC 00:30 / 25 号 UTC 00:45；沿用现有 scheduler 模块
16. `(phase, run_date, trigger_type)` 唯一键保证 SCHEDULED 幂等；MANUAL 不受限
17. 失败不自动重试；baseline 独立事务入库；send_log 追溯
18. 同一人兼 Admin+PM 各发一封
19. 不做首次上线 catch-up
20. 所有 72 行都写 baseline（含 NA）；history 仅在 percentile/marker 变化时插入
21. `DELETE /baselines` 在 prod 禁用；`preview` 不支持 overrideBaseline
22. 文档：SpringDoc OpenAPI + `docs/Benchmark/monthly-benchmark-email-api.md`
