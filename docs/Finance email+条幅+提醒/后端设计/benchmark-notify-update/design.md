# Benchmark 参考数据更新通知 - 后端技术设计

> 对应 PRD：`Notify Users When Benchmark Reference Data Is Updated_需求文档.md`
> 范围：后端。涵盖工作流 2.1（外部行业基准更新）残留补丁与工作流 2.2（LG 内部基准变化监测）从零实现。
> 不包含：任何前端改动。

---

## 1. 背景与目标

### 1.1 两个独立工作流

| 工作流 | 触发点 | 当前实现状态 |
|--------|--------|-------------|
| **2.1 外部行业基准更新** | 管理员在 Benchmark Entry 新增 platform-edition | 后端 80% 已实现，残留两个补丁 |
| **2.2 LG 内部基准变化监测** | 每月 25 号定时监测 + 应用启动时补发 | 完全未实现，需要新建表、新服务、新调度任务 |

### 1.2 本次后端交付范围

- 2.1 **G5** — 将借用的 `EmailTypeEnum.FORECAST_AUTO_FILL_ALERT` 替换为专属 `BENCHMARK_ENTRY_UPDATE`，并提供专属邮件模板。
- 2.1 **G3** — `GET /benchmark/notify-alerts` 查询时按当前用户访问权限过滤。
- 2.2 **全量实现** — 调度 + 两阶段执行 + 基线历史 + 首次发送 + 邮件 + 横幅 + 手动重跑接口。

---

## 2. 复用的既有能力

| 能力 | 位置 | 用途 |
|------|------|------|
| 内/外部 percentile 计算 | `fi/benchmark/engine/InternalPercentileCalculator`、`ExternalPercentileCalculator` | Phase 1 算当期 percentile |
| peer 集合解析 | `fi/benchmark/engine/PeerGroupResolver` | Phase 1 列出 peer 公司 |
| benchmark source 枚举 | `fi/enums/BenchmarkSourceEnum` | 判断 PLATFORM / PEER 切换 |
| closed_month 推导 | `fi/service/FinancialForecastDataServiceImpl`（参考其规则） | Manual / Automatic 公司的 closed_month 计算 |
| 用户查询 | `system/service/UserService#getAllCompanyAdmin / getAllPortfolioManager / getAllAdminWithPortfolio / getAllCompanyUser` | 收件人与 alert 对象 |
| 邮件发送 | `system/service/EmailService#sendEmail` | Thymeleaf 模板驱动 |
| 横幅写入 | `fi/service/BenchmarkNotifyAlertService#save` | 现有 enum 值 3/4/5 复用 |
| 调度器 | `scheduler/enums/FixedScheduleTypeEnum` + `scheduler/service/ScheduleProcessor` | 添加一条 cron 项 |

---

## 3. 数据模型

### 3.1 基线历史表

```sql
CREATE TABLE financial_benchmark_position_baseline (
  id                 VARCHAR(36)  PRIMARY KEY,
  company_id         VARCHAR(36)  NOT NULL,
  metric_id          VARCHAR(64)  NOT NULL,
  closed_month       DATE         NOT NULL,             -- 月份用每月 1 号表示
  percentile         NUMERIC(6,2) NOT NULL,
  benchmark_source   VARCHAR(16)  NOT NULL,             -- 'PLATFORM' | 'PEER'
  own_value          NUMERIC(20,6),
  peer_snapshot      JSONB,                             -- [{"companyId":"x","value":1.23}, ...]
  trigger_reason     VARCHAR(32)  NOT NULL,             -- 见 § 5 决策枚举
  notified           BOOLEAN      NOT NULL,             -- 是否发了邮件
  run_id             VARCHAR(36),                       -- Path A 时为 NULL，Path B 关联 run
  created_at         TIMESTAMP    NOT NULL,
  created_by         VARCHAR(36),
  updated_at         TIMESTAMP,
  updated_by         VARCHAR(36)
);
CREATE INDEX idx_baseline_company_metric_ct
  ON financial_benchmark_position_baseline(company_id, metric_id, created_at DESC);
```

取最新一条用 `findTopByCompanyIdAndMetricIdOrderByCreatedAtDesc(...)`。旧行不删不改，留作追溯。

### 3.2 运行快照表

```sql
CREATE TABLE financial_benchmark_position_run_snapshot (
  id                 VARCHAR(36)  PRIMARY KEY,
  run_id             VARCHAR(36)  NOT NULL,
  company_id         VARCHAR(36)  NOT NULL,
  metric_id          VARCHAR(64)  NOT NULL,
  closed_month       DATE,
  percentile         NUMERIC(6,2),
  benchmark_source   VARCHAR(16),
  own_value          NUMERIC(20,6),
  peer_snapshot      JSONB,
  diff_decision      VARCHAR(32),                       -- 见 § 5 决策枚举
  diff_delta         NUMERIC(6,2),                      -- |current_percentile - baseline_percentile|
  error_message      TEXT,
  created_at         TIMESTAMP    NOT NULL
);
CREATE INDEX idx_snapshot_run          ON financial_benchmark_position_run_snapshot(run_id);
CREATE INDEX idx_snapshot_company_metric
  ON financial_benchmark_position_run_snapshot(company_id, metric_id);
```

Phase 1 行写入时 `diff_decision` 暂空，Phase 2 回填。

### 3.3 跑批总控表

```sql
CREATE TABLE financial_benchmark_position_run (
  id                 VARCHAR(36)  PRIMARY KEY,
  run_trigger_time   TIMESTAMP    NOT NULL,
  phase              VARCHAR(16)  NOT NULL,             -- SNAPSHOT | DIFF | COMPLETED | FAILED
  company_count      INT,
  fired_count        INT,
  silent_count       INT,
  error_message      TEXT,
  created_at         TIMESTAMP    NOT NULL,
  updated_at         TIMESTAMP
);
```

---

## 4. 调度与触发

### 4.1 月度定时任务（Path B）

`FixedScheduleTypeEnum` 追加：

```java
BenchmarkPositionMonitor("BenchmarkPositionMonitor", "cron(0 6 25 * ? *)")
```

选 06:00 UTC 的原因：现有 fixed schedule 集中在 00–03 和 22–23，06 点是空窗。

`ScheduleProcessor.processMessage` switch 增加：

```java
case BenchmarkPositionMonitor:
    benchmarkPositionMonitorService.runMonthlyCheck();
    break;
```

### 4.2 启动时补发任务（Path A）

```java
@Component
public class BenchmarkPositionInitializer {
  @EventListener(ApplicationReadyEvent.class)
  public void onStartup() {
    CompletableFuture.runAsync(
      () -> benchmarkPositionMonitorService.runFirstTimeCatchup(),
      ioExecutor
    );
  }
}
```

和现有 `initFixedScheduler()` 使用同一个 `ApplicationReadyEvent` 和 `ioExecutor`。

### 4.3 手动重跑接口

```
POST /benchmark/position-monitor/rerun-diff/{runId}
  - 语义 (b)：重跑 DIFF 决策并重发邮件，完整复现。
  - 实现：清空该 runId 下所有 snapshot 行的 diff_decision/diff_delta，按原逻辑重新跑 Phase 2。
  - baseline 表允许再插一批新行（历史表设计使然），邮件重发。

POST /benchmark/position-monitor/rerun-first-time
  - 语义：重新触发 Path A（查 active 公司、未建过 baseline 的 (company, metric) 对）。
  - 允许 SME 在修数据后手动补发。
```

---

## 5. 决策枚举

```java
public enum BenchmarkPositionTriggerReasonEnum {
  // 写入 baseline + 发邮件的
  INITIAL_FIRE,                 // 首次，baseline=null 且可算 percentile
  SOURCE_FLIPPED,               // PLATFORM ↔ PEER 切换
  PEER_DRIVEN_SHIFT,            // own_value 不变 & |Δp|≥10 & peer 变了
  VALUE_AND_PEER_SHIFT,         // own_value 变 & |Δp|≥10 & peer 变了

  // 写入 baseline 但不发邮件
  SILENT_NEW_MONTH,             // baseline.closed_month < snapshot.closed_month
  SILENT_REVISED,               // 同月 own_value 变了但不满足 fire
  SILENT_BELOW_THRESHOLD,       // peer 变了但 |Δp|<10

  // 既不写 baseline 也不发邮件
  SKIP_NO_DATA                  // percentile 算不出
}
```

---

## 6. 执行流程

### 6.1 Phase 1 — SNAPSHOT（月度任务）

```
1. 创建 Run 行，phase=SNAPSHOT
2. 列出合格公司：status ∉ {Exited, Shut down} 且绑定了 portfolio
3. for each company:
     推导 closed_month（Manual / Automatic 规则）
     for each metric ∈ 6 指标:
        try:
          通过 PeerGroupResolver + InternalPercentileCalculator 算
            (percentile, benchmarkSource, ownValue, peerList)
          INSERT run_snapshot（diff_decision 空）
        catch:
          INSERT run_snapshot（error_message 填异常，diff_decision 暂空）
4. run.phase = DIFF
```

### 6.2 Phase 2 — DIFF（月度任务 / Path A 复用决策）

```
1. 按 company 分组遍历 snapshot：
     for each (company, metric) 行:
        if snapshot.error_message 非空:
          decision = SKIP_NO_DATA; 不建 baseline; continue
        baseline = findLatest(company, metric)
        decision = FirstTimeDecider(baseline, snapshot) if baseline==null
                 else DiffEvaluator(baseline, snapshot)
        UPDATE snapshot.diff_decision, diff_delta
        if decision writes baseline:
          INSERT baseline（notified=decision.fire）
        if decision.fire:
          标记 fire，暂不发邮件
2. 把所有 fire 标记按 (公司) 聚合 → 调 PositionNotifier
   - PositionNotifier 按收件人维度再聚合：
       * Company Admin：每公司一封
       * Portfolio Manager：按 (userId, organizationId) 分组，一封列出所有 fire 的 portfolio 名
   - 每封邮件发完，调 BenchmarkNotifyAlertService.save 写 alert（notifyType=3/4/5）
3. run.phase = COMPLETED，fired_count/silent_count 回填
```

### 6.3 Path A — 启动补发

```
runFirstTimeCatchup():
  列出合格公司
  for each company × 6 metrics:
     baseline = findLatest(company, metric)
     if baseline != null: continue       # 已发过首次或已进入月度监测
     compute snapshot（不落 run_snapshot 表，Path A 不建 run 行）
     decision = FirstTimeDecider(null, snapshot)
        → 可算出 percentile & peer 非空 → INITIAL_FIRE
        → 否则 → SKIP_NO_DATA（不建 baseline，下次机会再试）
     如 INITIAL_FIRE：
        INSERT baseline（notified=true，run_id=NULL）
        标记 fire
  按收件人聚合发邮件 + 写 alert
```

### 6.4 并发与幂等

- 双路径共用一把逻辑锁（基于 baseline 存在性判断），天然幂等：Path A 二次重启看见 baseline 已存在直接 skip。
- 单次 Path A 跑批过程中允许与 Path B 并行（极端情况下），都通过 `findLatest(...)` + 事务写入保证一致。
- Phase 1 单公司失败只记录 `error_message`，不影响其他公司。

---

## 7. 通知模块

### 7.1 邮件模板

新增 Thymeleaf 模板：

- `templates/mail/BenchmarkEntryUpdate.html`（2.1 使用）
- `templates/mail/BenchmarkPositionUpdate.html`（2.2 和 Path A 使用）

`BenchmarkPositionUpdate.html` 文本固定为需求中的版本：

```
Subject: Update to Benchmark Positioning

Hello {username},
You may notice a change in your company's benchmark positioning.
This shift is due to updates in the benchmark reference data,
which can affect how companies are ranked relative to one another.
It reflects movement within the cohort, not changes in your company's
financial performance.

[View Benchmark]   ← 按钮
```

`BenchmarkEntryUpdate.html` 文本固定为需求中的 2.1 版本，把 `platform/edition/orgDisplay` 作为模板变量。

Deep-link 规则与 2.1 完全一致：
- Company Admin → `/Finance?params=<b64(companyId&active=5&userId)>`
- Portfolio Manager → `/company?params=<b64(portfolioId&active=5&userId&organizationId)>`

### 7.2 邮件类型枚举

`EmailTypeEnum` 追加：

```java
BENCHMARK_ENTRY_UPDATE,
BENCHMARK_POSITION_UPDATE
```

### 7.3 横幅写入（Position Update）

每封邮件对应一条 alert：

| 场景 | notifyType |
|------|-----------|
| Company Admin | `POSITION_UPDATE_COMPANY`(3) |
| Portfolio Manager（admin portal） | `POSITION_UPDATE_PORTFOLIO_ADMIN`(4) |
| Company Admin 在 portfolio 视角看 | `POSITION_UPDATE_PORTFOLIO_COMPANY`(5) |

`content` 留空字符串，前端按 notifyType 硬编码固定文案（需求中的 "Benchmark positioning updated..."）。

---

## 8. 2.1 残留补丁

### 8.1 G5 — 邮件模板切换

`BenchmarkEntryServiceImpl.sendEmail(...)` 当前用 `SimpleEmailUtil.TEMPLATE_NAME` + `FORECAST_AUTO_FILL_ALERT`。改为：

- 使用新模板 `BenchmarkEntryUpdate.html`
- `EmailTypeEnum.BENCHMARK_ENTRY_UPDATE`
- Context 变量：`username`、`platform`、`edition`、`orgDisplay`、`fullUrl`

### 8.2 G3 — 横幅权限过滤

`BenchmarkNotifyAlertServiceImpl.getNotifyAlert(criteria)` 返回前追加过滤：

```
若 notifyType 是 portfolio 角色（2 或 4）：
    校验当前用户在该 companyGroupId 下仍有 ≥1 家可见公司；否则返回 null。
若 notifyType 是 company 角色（1、3、5）：
    校验当前用户仍有该 companyId 的访问权限；否则返回 null。
```

"可见公司 / 访问权限"的判断：调研 `userService`/`companyService` 的既有方法（暂未确认具体方法名——实施阶段补上）。若无现成方法，新增一个 `UserService#canAccessCompany(userId, companyId)` 工具方法。

---

## 9. 新增 / 修改清单（概览）

```
CIOaas-api/gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/
├── fi/benchmark/position/                           # 新增目录
│   ├── domain/
│   │   ├── FinancialBenchmarkPositionBaseline.java
│   │   ├── FinancialBenchmarkPositionRun.java
│   │   └── FinancialBenchmarkPositionRunSnapshot.java
│   ├── repository/
│   │   ├── BenchmarkPositionBaselineRepository.java
│   │   ├── BenchmarkPositionRunRepository.java
│   │   └── BenchmarkPositionRunSnapshotRepository.java
│   ├── service/
│   │   ├── BenchmarkPositionMonitorService.java      # interface
│   │   ├── BenchmarkPositionMonitorServiceImpl.java
│   │   ├── SnapshotBuilder.java
│   │   ├── DiffEvaluator.java
│   │   ├── FirstTimeDecider.java
│   │   └── PositionNotifier.java
│   ├── startup/
│   │   └── BenchmarkPositionInitializer.java        # @EventListener
│   ├── controller/
│   │   └── BenchmarkPositionMonitorController.java  # rerun-diff / rerun-first-time
│   └── contract/
│       ├── PositionMonitorRunDto.java
│       └── RerunResultDto.java
├── fi/enums/
│   └── BenchmarkPositionTriggerReasonEnum.java      # 新增
├── fi/service/
│   ├── BenchmarkEntryServiceImpl.java               # 改：sendEmail 切 EmailType + 模板
│   └── BenchmarkNotifyAlertServiceImpl.java         # 改：getNotifyAlert 加权限过滤
├── scheduler/enums/FixedScheduleTypeEnum.java       # 改：追加 BenchmarkPositionMonitor
├── scheduler/service/ScheduleProcessor.java         # 改：switch case 新增
└── system/enums/EmailTypeEnum.java                  # 改：追加两个 enum 值

CIOaas-api/gstdev-cioaas-web/src/main/resources/
└── templates/mail/
    ├── BenchmarkEntryUpdate.html                    # 新增
    └── BenchmarkPositionUpdate.html                 # 新增

CIOaas-api/gstdev-cioaas-web/src/main/resources/db/migration/  # 如使用 Flyway
└── V<next>__benchmark_position_monitor.sql          # 新增三张表
```

---

## 10. 测试策略

### 单元测试
| 测试类 | 覆盖点 |
|--------|--------|
| `FirstTimeDeciderTest` | baseline=null 的各形态 → INITIAL_FIRE / SKIP_NO_DATA |
| `DiffEvaluatorTest` | 决策枚举全覆盖（6 种 baseline 形态组合） |
| `PeerDiffUtilTest` | peer_snapshot 对比：集合变 / 值变 / 都变 / 未变 |
| `ClosedMonthResolverTest` | Manual / Automatic 跨 15 号 / 回溯 |
| `PositionNotifierTest` | Company Admin 一公司一封；PM 按 org 聚合 |

### 集成测试
| 测试类 | 覆盖点 |
|--------|--------|
| `BenchmarkPositionMonitorIT` | 种子数据 → `runMonthlyCheck()` → 断言三表行数、decision 分布、mock 邮件调用次数、alert 写入 |
| `BenchmarkPositionInitializerIT` | 启动 catch-up：已建 baseline 的 skip；未建且可算的 fire；不可算的 skip |
| `BenchmarkEntryUpdateEmailIT` | 2.1 切模板后邮件依然可达，Subject/正文符合 |
| `BenchmarkNotifyAlertPermissionIT` | G3 权限过滤：失权用户收不到横幅 |

### 边界与风险

| 场景 | 处理 |
|------|------|
| 公司 closed_month 算不出 | 当次 skip，不建 baseline |
| 同一公司多 portfolio 多 PM | 每 PM 各收一封 |
| PM 管多 portfolio 都 fire | 一封列出全部 portfolio 名 |
| Phase 1/2 间公司被删 | snapshot 可继续；发信找不到收件人跳过 |
| rerun-diff 重发邮件 | (b) 方案显式接受；baseline 新增历史行 |
| peer snapshot JSON 尺寸 | 6 指标 × 最多 50 同行 × ~100 字节 ≈ 50 KB，JSONB 可容忍 |

---

## 11. 未解决 / 实施阶段需确认

| # | 项 | 说明 |
|---|-----|------|
| U1 | `userService` 是否已有"单用户-单公司访问权限"判定方法 | 用于 G3 过滤；若无则新增 `canAccessCompany(userId, companyId)` |
| U2 | `InternalPercentileCalculator` 是否接受 `(companyId, metricId, month)` 入参 | 实施时查签名，如不支持需薄封装 |
| U3 | 项目是否启用 Flyway | 若否，走现有 DDL 管理方式 |
| U4 | percentile 精度 | 采用与既有 calculator 一致的类型（整数 0–100 或 BigDecimal）；实施阶段确认 |

---

## 12. 不做

- 不做前端横幅组件、API 客户端、dismiss 按钮、横幅文案渲染。
- 不在 FinancialEntry 编辑路径插钩子（"被修订的静默更新"在月度批里收敛）。
- 不为 2.2 单独做 SQS / worker 拓扑（YAGNI）。
- 不新建 first-email-sent 标志位（用 baseline 表存在性派生）。
