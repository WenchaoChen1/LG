# Benchmark 通知更新 - 后端实施计划

> **对 agentic workers：** 用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐条执行。步骤用 `- [ ]` checkbox。
>
> **对应设计文档：** `docs/benchmark-notify-update/design.md`

**目标：** 实现工作流 2.1 残留后端补丁 + 工作流 2.2 LG 内部基准变化监测后端，不动前端。

**架构：** 两张新表 + 两条触发路径（启动补发 + 月度定时）+ 手动重跑接口；复用现有 `InternalPercentileCalculator` / `PeerGroupResolver` / `UserService` / `EmailService` / `BenchmarkNotifyAlertService`。

**Tech Stack：** Java 17、Spring Boot 3.3、JPA、PostgreSQL、Thymeleaf、MapStruct、JUnit 5、Mockito。

**git 约定：** 所有 commit 在 `CIOaas-api/` 子目录内执行（它是独立仓库）。Commit message 使用中文简述 + 英文前缀 `feat/fix/refactor/test`。

---

## 前置步骤

- [ ] **步骤 0.1：进入后端仓库目录**

```bash
cd CIOaas-api
git status
```

预期：工作区干净，当前 branch 是功能开发分支。

- [ ] **步骤 0.2：创建功能分支**

```bash
git checkout -b feature/benchmark-notify-update
```

- [ ] **步骤 0.3：读懂复用点**

先读以下文件搞清楚签名和数据流（不要跳过）：
- `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/engine/InternalPercentileCalculator.java` — 输入/输出
- `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/engine/PeerGroupResolver.java` — 入参 `Invite` 而非 `Company`
- `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/service/ColleagueCompanyServiceImpl.java` 里 `latestCurrentData.getDate()` 的 closed_month 逻辑
- `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/service/BenchmarkEntryServiceImpl.java` 里 `sendEmail()` 已有的 Context 变量和 URL 编码
- `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/enums/MetricEnum.java` — 6 个指标的 enum 值

预期：能口头说出每个组件的输入输出。

---

## 阶段 A — 2.1 残留补丁

### Task A1：新增 EmailTypeEnum 两个枚举值

**Files：**
- Modify: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/enums/EmailTypeEnum.java`

- [ ] **A1.1：阅读现有 EmailTypeEnum**

读文件了解枚举结构（是否带 code/描述字段）。

- [ ] **A1.2：追加两个枚举值**

按现有枚举的字段签名，在枚举列表末尾追加（不破坏现有顺序）：

```java
BENCHMARK_ENTRY_UPDATE,          // 2.1 Benchmark Entry 新增 platform-edition 时发
BENCHMARK_POSITION_UPDATE        // 2.2 LG 内部基准变化 + 首次补发 时发
```

若枚举包含构造器字段（如 code、name），按既有模板填值。

- [ ] **A1.3：编译检查**

```bash
mvn -pl gstdev-cioaas-web compile -q
```

预期：BUILD SUCCESS。

- [ ] **A1.4：commit**

```bash
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/enums/EmailTypeEnum.java
git commit -m "feat: 新增 BENCHMARK_ENTRY_UPDATE / BENCHMARK_POSITION_UPDATE 邮件类型枚举"
```

---

### Task A2：新建 2.1 邮件模板 BenchmarkEntryUpdate.html

**Files：**
- Create: `gstdev-cioaas-web/src/main/resources/templates/BenchmarkEntryUpdate.html`

- [ ] **A2.1：参考既有模板结构**

读 `gstdev-cioaas-web/src/main/resources/templates/SimpleEmailTemplate.html` 或 `UnifiedMailTemplate.html` 了解现有 Thymeleaf 片段风格（head、body、按钮区）。

- [ ] **A2.2：新建模板**

内容按需求文档 2.1 的正文：

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head>
  <meta charset="UTF-8"/>
  <title>New Benchmark Survey Update</title>
</head>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
  <p>Hello <span th:text="${username}">User</span>,</p>
  <p>
    We've added a new industry benchmark survey
    (<span th:text="${platform}">Platform</span> — <span th:text="${edition}">Edition</span>)
    therefore benchmark comparisons for <span th:text="${orgDisplay}">Org</span>
    now reflect the latest survey year.
  </p>
  <p>
    As a result, you may notice changes in your company's relative positioning
    due to the updated benchmark data.
  </p>
  <p>
    If you have any questions or would like help interpreting these changes,
    feel free to reach out.
  </p>
  <p style="margin-top: 24px;">
    <a th:href="${url}" style="display:inline-block;padding:10px 18px;background:#FAAD14;color:#fff;text-decoration:none;border-radius:4px;">View Benchmark</a>
  </p>
</body>
</html>
```

- [ ] **A2.3：commit**

```bash
git add gstdev-cioaas-web/src/main/resources/templates/BenchmarkEntryUpdate.html
git commit -m "feat: 新增 2.1 Benchmark Entry Update 邮件模板"
```

---

### Task A3：BenchmarkEntryServiceImpl 切换到新模板 + 新邮件类型

**Files：**
- Modify: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/service/BenchmarkEntryServiceImpl.java` 的 `sendEmail(...)` 方法

- [ ] **A3.1：替换 EmailType 和模板名**

把 `sendEmail` 方法末尾这行：

```java
Pair<Boolean, String> sendResult = emailService.sendEmail(email, context, SimpleEmailUtil.TEMPLATE_NAME,
  EmailTypeEnum.FORECAST_AUTO_FILL_ALERT);
```

改为：

```java
Pair<Boolean, String> sendResult = emailService.sendEmail(email, context, "BenchmarkEntryUpdate",
  EmailTypeEnum.BENCHMARK_ENTRY_UPDATE);
```

同时清理不再需要的 `SimpleEmailUtil.TITLE_WITH_HTML_TAG` / `SimpleEmailUtil.CONTENT_WITH_HTML_TAG` / `SimpleEmailUtil.BUTTON_TEXT` / `SimpleEmailUtil.BUTTON_URL` 变量注入——因为新模板用 `username / platform / edition / orgDisplay / url` 这五个明确变量，不再依赖通用模板。

保留的 context 变量：

```java
context.setVariable("username", user.getDisplayName());
context.setVariable("platform", platform);
context.setVariable("edition", edition);
context.setVariable("orgDisplay", orgDisplay);
context.setVariable("url", fullUrl);
```

删掉 `SimpleEmailUtil.*` 相关变量设置。

- [ ] **A3.2：编译检查**

```bash
mvn -pl gstdev-cioaas-web compile -q
```

预期：BUILD SUCCESS。

- [ ] **A3.3：commit**

```bash
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/service/BenchmarkEntryServiceImpl.java
git commit -m "refactor: BenchmarkEntryServiceImpl 改用专属邮件模板与 BENCHMARK_ENTRY_UPDATE 类型（G5）"
```

---

### Task A4：UserService 新增单点权限判定方法 canAccessCompany

**Files：**
- Modify: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/service/UserService.java`
- Modify: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/service/UserServiceImpl.java`

- [ ] **A4.1：定位现有"可见公司"查询逻辑**

先 grep 现有代码找 "能列出用户可见公司"的方法：

```bash
grep -n "getCompanyIdsByUser\|findVisibleCompanies\|getUserCompanies" \
  gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/service/
```

目标：找到能返回"某用户下所有可见 companyId"的方法；若没有，则基于 portfolio/role 表结构新建。

- [ ] **A4.2：在 UserService 接口追加两个方法**

```java
/**
 * 判断用户是否仍对该公司具有访问权限。
 * 用于 company 场景的横幅权限过滤（G3）。
 */
boolean canAccessCompany(String userId, String companyId);

/**
 * 判断用户在该 companyGroup（portfolio）下是否仍有 >=1 家可见公司。
 * 用于 portfolio 场景的横幅权限过滤（G3）。
 */
boolean hasVisibleCompanyUnderGroup(String userId, String companyGroupId);
```

- [ ] **A4.3：在 UserServiceImpl 实现**

```java
@Override
@Transactional(readOnly = true)
public boolean canAccessCompany(String userId, String companyId) {
  if (userId == null || companyId == null) return false;
  // 复用 A4.1 定位到的既有"用户可见公司"查询；这里写一条显式 count
  return userCompanyRepository.countByUserIdAndCompanyId(userId, companyId) > 0;
}

@Override
@Transactional(readOnly = true)
public boolean hasVisibleCompanyUnderGroup(String userId, String companyGroupId) {
  if (userId == null || companyGroupId == null) return false;
  return userCompanyRepository.countByUserIdAndCompanyGroupId(userId, companyGroupId) > 0;
}
```

若 `userCompanyRepository`（或等价 repo）不存在对应 count 方法，在对应 Repository 接口里追加：

```java
long countByUserIdAndCompanyId(String userId, String companyId);
long countByUserIdAndCompanyGroupId(String userId, String companyGroupId);
```

若项目用 role/portfolio 关系而非直接 user_company 表，按实际关系模型改写（例如 portfolio manager → portfolio → companies 的三段 join）。

- [ ] **A4.4：编译 + 提交**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/service/UserService.java \
        gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/service/UserServiceImpl.java
git commit -m "feat: UserService 新增 canAccessCompany / hasVisibleCompanyUnderGroup 用于横幅权限过滤"
```

---

### Task A5：BenchmarkNotifyAlertServiceImpl.getNotifyAlert 加权限过滤

**Files：**
- Modify: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/service/BenchmarkNotifyAlertServiceImpl.java`

- [ ] **A5.1：注入 UserService**

类头部追加：

```java
@Resource
private com.gstdev.cioaas.web.system.service.UserService userService;
```

- [ ] **A5.2：在 getNotifyAlert 返回前追加权限校验**

在 `return mapper.toDto(entity);` 之前插入：

```java
// G3: 权限过期则不返回横幅
Integer type = entity.getNotifyType();
String requesterUserId = entity.getUserId();
boolean authorized;
if (BenchmarkNotifyAlertEnum.ENTRY_UPDATE_PORTFOLIO_ADMIN.getCode().equals(type)
    || BenchmarkNotifyAlertEnum.POSITION_UPDATE_PORTFOLIO_ADMIN.getCode().equals(type)) {
  // portfolio 场景：校验用户在该 companyGroup 下仍有 >=1 家可见公司
  authorized = userService.hasVisibleCompanyUnderGroup(requesterUserId, entity.getCompanyGroupId());
} else {
  // company 场景：校验对目标 companyId 仍有访问权限
  authorized = userService.canAccessCompany(requesterUserId, entity.getCompanyId());
}
if (!authorized) {
  return null;
}
```

> 说明：`hasVisibleCompanyUnderGroup` 是配套新增方法，在 A4 中一并实现（若未实现则本步骤连带补齐）。

- [ ] **A5.3：commit**

```bash
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/service/BenchmarkNotifyAlertServiceImpl.java
git commit -m "feat: getNotifyAlert 加权限过滤，失权用户不返回横幅（G3）"
```

---

## 阶段 B — 2.2 数据模型与枚举

### Task B1：新建 BenchmarkPositionTriggerReasonEnum

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/enums/BenchmarkPositionTriggerReasonEnum.java`

- [ ] **B1.1：按设计 § 5 定义枚举**

```java
package com.gstdev.cioaas.web.fi.enums;

public enum BenchmarkPositionTriggerReasonEnum {
  // 写 baseline + 发邮件
  INITIAL_FIRE,
  SOURCE_FLIPPED,
  PEER_DRIVEN_SHIFT,
  VALUE_AND_PEER_SHIFT,
  // 写 baseline 但不发邮件
  SILENT_NEW_MONTH,
  SILENT_REVISED,
  SILENT_BELOW_THRESHOLD,
  // 既不写 baseline 也不发邮件
  SKIP_NO_DATA;

  public boolean fires() {
    return this == INITIAL_FIRE || this == SOURCE_FLIPPED
        || this == PEER_DRIVEN_SHIFT || this == VALUE_AND_PEER_SHIFT;
  }

  public boolean writesBaseline() {
    return this != SKIP_NO_DATA;
  }
}
```

- [ ] **B1.2：编译 + commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/enums/BenchmarkPositionTriggerReasonEnum.java
git commit -m "feat: 新增 BenchmarkPositionTriggerReasonEnum 决策枚举"
```

---

### Task B2：三张表的 DDL SQL 文档

**Files：**
- Create: `CIOaas-api/gstdev-cioaas-web/src/main/resources/db/ddl/benchmark-position-monitor.sql`

> 项目未使用 Flyway，DDL 以文档形式存放，由 DBA / 运维手动执行（或 JPA `ddl-auto=update` 自动建表——需向项目 owner 确认）。

- [ ] **B2.1：新建 DDL 文件**

```sql
-- Benchmark Position Monitor - 基线历史表
CREATE TABLE IF NOT EXISTS financial_benchmark_position_baseline (
  id                 VARCHAR(36)  PRIMARY KEY,
  company_id         VARCHAR(36)  NOT NULL,
  metric_id          VARCHAR(64)  NOT NULL,
  closed_month       DATE         NOT NULL,
  percentile         NUMERIC(6,2) NOT NULL,
  benchmark_source   VARCHAR(16)  NOT NULL,
  own_value          NUMERIC(20,6),
  peer_snapshot      JSONB,
  trigger_reason     VARCHAR(32)  NOT NULL,
  notified           BOOLEAN      NOT NULL,
  run_id             VARCHAR(36),
  created_at         TIMESTAMP    NOT NULL DEFAULT NOW(),
  created_by         VARCHAR(36),
  updated_at         TIMESTAMP,
  updated_by         VARCHAR(36)
);
CREATE INDEX IF NOT EXISTS idx_baseline_company_metric_ct
  ON financial_benchmark_position_baseline(company_id, metric_id, created_at DESC);

-- Benchmark Position Monitor - 运行快照表
CREATE TABLE IF NOT EXISTS financial_benchmark_position_run_snapshot (
  id                 VARCHAR(36)  PRIMARY KEY,
  run_id             VARCHAR(36)  NOT NULL,
  company_id         VARCHAR(36)  NOT NULL,
  metric_id          VARCHAR(64)  NOT NULL,
  closed_month       DATE,
  percentile         NUMERIC(6,2),
  benchmark_source   VARCHAR(16),
  own_value          NUMERIC(20,6),
  peer_snapshot      JSONB,
  diff_decision      VARCHAR(32),
  diff_delta         NUMERIC(6,2),
  error_message      TEXT,
  created_at         TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_snapshot_run
  ON financial_benchmark_position_run_snapshot(run_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_company_metric
  ON financial_benchmark_position_run_snapshot(company_id, metric_id);

-- Benchmark Position Monitor - 跑批总控表
CREATE TABLE IF NOT EXISTS financial_benchmark_position_run (
  id                 VARCHAR(36)  PRIMARY KEY,
  run_trigger_time   TIMESTAMP    NOT NULL,
  phase              VARCHAR(16)  NOT NULL,
  company_count      INT,
  fired_count        INT,
  silent_count       INT,
  error_message      TEXT,
  created_at         TIMESTAMP    NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMP
);
```

- [ ] **B2.2：commit**

```bash
git add gstdev-cioaas-web/src/main/resources/db/ddl/benchmark-position-monitor.sql
git commit -m "feat: 新增 Position Monitor 三张表 DDL"
```

---

### Task B3：三个 JPA 实体

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/domain/FinancialBenchmarkPositionBaseline.java`
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/domain/FinancialBenchmarkPositionRunSnapshot.java`
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/domain/FinancialBenchmarkPositionRun.java`

- [ ] **B3.1：FinancialBenchmarkPositionBaseline 实体**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.domain;

import com.gstdev.cioaas.common.persistence.AbstractCustomEntity;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UuidGenerator;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.LocalDate;

@Getter
@Setter
@Entity
@Table(name = "financial_benchmark_position_baseline")
public class FinancialBenchmarkPositionBaseline extends AbstractCustomEntity {
  @Id
  @UuidGenerator
  @Column(name = "id", length = 36)
  private String id;

  @Column(name = "company_id", length = 36, nullable = false)
  private String companyId;

  @Column(name = "metric_id", length = 64, nullable = false)
  private String metricId;

  @Column(name = "closed_month", nullable = false)
  private LocalDate closedMonth;

  @Column(name = "percentile", precision = 6, scale = 2, nullable = false)
  private BigDecimal percentile;

  @Column(name = "benchmark_source", length = 16, nullable = false)
  private String benchmarkSource;

  @Column(name = "own_value", precision = 20, scale = 6)
  private BigDecimal ownValue;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "peer_snapshot", columnDefinition = "jsonb")
  private String peerSnapshot;   // 存 JSON 字符串

  @Column(name = "trigger_reason", length = 32, nullable = false)
  private String triggerReason;

  @Column(name = "notified", nullable = false)
  private Boolean notified;

  @Column(name = "run_id", length = 36)
  private String runId;
}
```

- [ ] **B3.2：FinancialBenchmarkPositionRunSnapshot 实体**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UuidGenerator;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

@Getter
@Setter
@Entity
@Table(name = "financial_benchmark_position_run_snapshot")
public class FinancialBenchmarkPositionRunSnapshot {
  @Id
  @UuidGenerator
  @Column(name = "id", length = 36)
  private String id;

  @Column(name = "run_id", length = 36, nullable = false)
  private String runId;

  @Column(name = "company_id", length = 36, nullable = false)
  private String companyId;

  @Column(name = "metric_id", length = 64, nullable = false)
  private String metricId;

  @Column(name = "closed_month")
  private LocalDate closedMonth;

  @Column(name = "percentile", precision = 6, scale = 2)
  private BigDecimal percentile;

  @Column(name = "benchmark_source", length = 16)
  private String benchmarkSource;

  @Column(name = "own_value", precision = 20, scale = 6)
  private BigDecimal ownValue;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "peer_snapshot", columnDefinition = "jsonb")
  private String peerSnapshot;

  @Column(name = "diff_decision", length = 32)
  private String diffDecision;

  @Column(name = "diff_delta", precision = 6, scale = 2)
  private BigDecimal diffDelta;

  @Column(name = "error_message", columnDefinition = "text")
  private String errorMessage;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  @PrePersist
  void onCreate() {
    if (createdAt == null) createdAt = Instant.now();
  }
}
```

- [ ] **B3.3：FinancialBenchmarkPositionRun 实体**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.domain;

import com.gstdev.cioaas.common.persistence.AbstractCustomEntity;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.UuidGenerator;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "financial_benchmark_position_run")
public class FinancialBenchmarkPositionRun extends AbstractCustomEntity {
  @Id
  @UuidGenerator
  @Column(name = "id", length = 36)
  private String id;

  @Column(name = "run_trigger_time", nullable = false)
  private Instant runTriggerTime;

  @Column(name = "phase", length = 16, nullable = false)
  private String phase;   // SNAPSHOT | DIFF | COMPLETED | FAILED

  @Column(name = "company_count")
  private Integer companyCount;

  @Column(name = "fired_count")
  private Integer firedCount;

  @Column(name = "silent_count")
  private Integer silentCount;

  @Column(name = "error_message", columnDefinition = "text")
  private String errorMessage;
}
```

- [ ] **B3.4：commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/domain/
git commit -m "feat: Position Monitor 三张表的 JPA 实体"
```

---

### Task B4：三个 Repository

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/repository/BenchmarkPositionBaselineRepository.java`
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/repository/BenchmarkPositionRunSnapshotRepository.java`
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/repository/BenchmarkPositionRunRepository.java`

- [ ] **B4.1：Baseline Repository**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.repository;

import com.gstdev.cioaas.web.fi.benchmark.position.domain.FinancialBenchmarkPositionBaseline;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface BenchmarkPositionBaselineRepository
    extends JpaRepository<FinancialBenchmarkPositionBaseline, String> {

  Optional<FinancialBenchmarkPositionBaseline>
    findTopByCompanyIdAndMetricIdOrderByCreatedAtDesc(String companyId, String metricId);

  boolean existsByCompanyIdAndMetricId(String companyId, String metricId);
}
```

- [ ] **B4.2：RunSnapshot Repository**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.repository;

import com.gstdev.cioaas.web.fi.benchmark.position.domain.FinancialBenchmarkPositionRunSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface BenchmarkPositionRunSnapshotRepository
    extends JpaRepository<FinancialBenchmarkPositionRunSnapshot, String> {

  List<FinancialBenchmarkPositionRunSnapshot> findAllByRunId(String runId);
}
```

- [ ] **B4.3：Run Repository**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.repository;

import com.gstdev.cioaas.web.fi.benchmark.position.domain.FinancialBenchmarkPositionRun;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BenchmarkPositionRunRepository
    extends JpaRepository<FinancialBenchmarkPositionRun, String> {
}
```

- [ ] **B4.4：commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/repository/
git commit -m "feat: Position Monitor 三个 JPA Repository"
```

---

### Task B5：新建 2.2 邮件模板 BenchmarkPositionUpdate.html

**Files：**
- Create: `gstdev-cioaas-web/src/main/resources/templates/BenchmarkPositionUpdate.html`

- [ ] **B5.1：新建模板**

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head>
  <meta charset="UTF-8"/>
  <title>Update to Benchmark Positioning</title>
</head>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
  <p>Hello <span th:text="${username}">User</span>,</p>
  <p>You may notice a change in your company's benchmark positioning.</p>
  <p>
    This shift is due to updates in the benchmark reference data, which can affect
    how companies are ranked relative to one another. It reflects movement within
    the cohort, not changes in your company's financial performance.
  </p>
  <p style="margin-top: 24px;">
    <a th:href="${url}" style="display:inline-block;padding:10px 18px;background:#FAAD14;color:#fff;text-decoration:none;border-radius:4px;">View Benchmark</a>
  </p>
</body>
</html>
```

- [ ] **B5.2：commit**

```bash
git add gstdev-cioaas-web/src/main/resources/templates/BenchmarkPositionUpdate.html
git commit -m "feat: 新增 Benchmark Position Update 邮件模板"
```

---

## 阶段 C — 2.2 纯函数组件（TDD）

### Task C1：PeerDiffUtil（JSON 对比工具）

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/util/PeerDiffUtil.java`
- Create: `gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/util/PeerDiffUtilTest.java`

- [ ] **C1.1：先写失败测试**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.util;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class PeerDiffUtilTest {
  @Test
  void bothNull_returnsFalse() {
    assertFalse(PeerDiffUtil.peerChanged(null, null));
  }

  @Test
  void setDiffers_returnsTrue() {
    String a = "[{\"companyId\":\"c1\",\"value\":10}]";
    String b = "[{\"companyId\":\"c2\",\"value\":10}]";
    assertTrue(PeerDiffUtil.peerChanged(a, b));
  }

  @Test
  void valuesDiffer_returnsTrue() {
    String a = "[{\"companyId\":\"c1\",\"value\":10}]";
    String b = "[{\"companyId\":\"c1\",\"value\":20}]";
    assertTrue(PeerDiffUtil.peerChanged(a, b));
  }

  @Test
  void sameContentDifferentOrder_returnsFalse() {
    String a = "[{\"companyId\":\"c1\",\"value\":10},{\"companyId\":\"c2\",\"value\":20}]";
    String b = "[{\"companyId\":\"c2\",\"value\":20},{\"companyId\":\"c1\",\"value\":10}]";
    assertFalse(PeerDiffUtil.peerChanged(a, b));
  }
}
```

- [ ] **C1.2：运行测试验证失败**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=PeerDiffUtilTest -q
```

预期：FAIL（类不存在）。

- [ ] **C1.3：实现 PeerDiffUtil**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.util;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.util.*;

public final class PeerDiffUtil {
  private static final ObjectMapper MAPPER = new ObjectMapper();

  private PeerDiffUtil() {}

  public static boolean peerChanged(String snapshotA, String snapshotB) {
    Map<String, BigDecimal> a = parse(snapshotA);
    Map<String, BigDecimal> b = parse(snapshotB);
    if (!a.keySet().equals(b.keySet())) return true;
    for (var entry : a.entrySet()) {
      BigDecimal va = entry.getValue();
      BigDecimal vb = b.get(entry.getKey());
      if (va == null && vb == null) continue;
      if (va == null || vb == null) return true;
      if (va.compareTo(vb) != 0) return true;
    }
    return false;
  }

  private static Map<String, BigDecimal> parse(String json) {
    if (json == null || json.isBlank()) return Collections.emptyMap();
    try {
      List<Map<String, Object>> list = MAPPER.readValue(json, new TypeReference<>() {});
      Map<String, BigDecimal> m = new HashMap<>();
      for (Map<String, Object> row : list) {
        String id = Objects.toString(row.get("companyId"), null);
        if (id == null) continue;
        Object v = row.get("value");
        m.put(id, v == null ? null : new BigDecimal(v.toString()));
      }
      return m;
    } catch (Exception e) {
      throw new IllegalArgumentException("Invalid peer_snapshot JSON: " + json, e);
    }
  }
}
```

- [ ] **C1.4：运行测试验证通过**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=PeerDiffUtilTest -q
```

预期：4 tests pass。

- [ ] **C1.5：commit**

```bash
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/util/PeerDiffUtil.java \
        gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/util/PeerDiffUtilTest.java
git commit -m "feat: PeerDiffUtil 对比两次 peer 快照是否变更"
```

---

### Task C2：DiffEvaluator（决策逻辑）

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/DiffEvaluator.java`
- Create: `gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/service/DiffEvaluatorTest.java`

- [ ] **C2.1：定义输入输出 record**

在 `position/service/` 目录下先新增辅助类型：

```java
// SnapshotInput.java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import java.math.BigDecimal;
import java.time.LocalDate;

public record SnapshotInput(
    String companyId,
    String metricId,
    LocalDate closedMonth,
    BigDecimal percentile,
    String benchmarkSource,
    BigDecimal ownValue,
    String peerSnapshot
) {}
```

```java
// BaselineInput.java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import java.math.BigDecimal;
import java.time.LocalDate;

public record BaselineInput(
    LocalDate closedMonth,
    BigDecimal percentile,
    String benchmarkSource,
    BigDecimal ownValue,
    String peerSnapshot
) {}
```

```java
// DiffDecision.java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.gstdev.cioaas.web.fi.enums.BenchmarkPositionTriggerReasonEnum;
import java.math.BigDecimal;

public record DiffDecision(
    BenchmarkPositionTriggerReasonEnum reason,
    BigDecimal delta
) {}
```

- [ ] **C2.2：写失败测试**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.gstdev.cioaas.web.fi.enums.BenchmarkPositionTriggerReasonEnum;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.*;

class DiffEvaluatorTest {
  private final DiffEvaluator evaluator = new DiffEvaluator();

  private static final LocalDate M = LocalDate.of(2026, 3, 1);
  private static final String PEER_A = "[{\"companyId\":\"c1\",\"value\":10}]";
  private static final String PEER_B = "[{\"companyId\":\"c1\",\"value\":20}]";

  @Test
  void sourceFlipped_fires() {
    var baseline = new BaselineInput(M, bd("50"), "PLATFORM", bd("100"), PEER_A);
    var snapshot = new SnapshotInput("co", "m", M, bd("50"), "PEER", bd("100"), PEER_A);
    var d = evaluator.evaluate(baseline, snapshot);
    assertEquals(BenchmarkPositionTriggerReasonEnum.SOURCE_FLIPPED, d.reason());
  }

  @Test
  void peerDrivenShift_ownValueUnchanged_peerChanged_percentileDelta10_fires() {
    var baseline = new BaselineInput(M, bd("20"), "PEER", bd("100"), PEER_A);
    var snapshot = new SnapshotInput("co", "m", M, bd("30"), "PEER", bd("100"), PEER_B);
    var d = evaluator.evaluate(baseline, snapshot);
    assertEquals(BenchmarkPositionTriggerReasonEnum.PEER_DRIVEN_SHIFT, d.reason());
    assertEquals(0, bd("10").compareTo(d.delta()));
  }

  @Test
  void valueAndPeerShift_bothChanged_fires() {
    var baseline = new BaselineInput(M, bd("20"), "PEER", bd("100"), PEER_A);
    var snapshot = new SnapshotInput("co", "m", M, bd("35"), "PEER", bd("120"), PEER_B);
    var d = evaluator.evaluate(baseline, snapshot);
    assertEquals(BenchmarkPositionTriggerReasonEnum.VALUE_AND_PEER_SHIFT, d.reason());
  }

  @Test
  void valueRevised_peerUnchanged_silent() {
    var baseline = new BaselineInput(M, bd("20"), "PEER", bd("100"), PEER_A);
    var snapshot = new SnapshotInput("co", "m", M, bd("40"), "PEER", bd("120"), PEER_A);
    var d = evaluator.evaluate(baseline, snapshot);
    assertEquals(BenchmarkPositionTriggerReasonEnum.SILENT_REVISED, d.reason());
  }

  @Test
  void newClosedMonth_silent() {
    var baseline = new BaselineInput(LocalDate.of(2026, 2, 1), bd("20"), "PEER", bd("100"), PEER_A);
    var snapshot = new SnapshotInput("co", "m", M, bd("40"), "PEER", bd("120"), PEER_B);
    var d = evaluator.evaluate(baseline, snapshot);
    assertEquals(BenchmarkPositionTriggerReasonEnum.SILENT_NEW_MONTH, d.reason());
  }

  @Test
  void belowThreshold_silent() {
    var baseline = new BaselineInput(M, bd("20"), "PEER", bd("100"), PEER_A);
    var snapshot = new SnapshotInput("co", "m", M, bd("25"), "PEER", bd("100"), PEER_B);
    var d = evaluator.evaluate(baseline, snapshot);
    assertEquals(BenchmarkPositionTriggerReasonEnum.SILENT_BELOW_THRESHOLD, d.reason());
  }

  private static BigDecimal bd(String s) { return new BigDecimal(s); }
}
```

- [ ] **C2.3：运行测试验证失败**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=DiffEvaluatorTest -q
```

- [ ] **C2.4：实现 DiffEvaluator**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.gstdev.cioaas.web.fi.benchmark.position.util.PeerDiffUtil;
import com.gstdev.cioaas.web.fi.enums.BenchmarkPositionTriggerReasonEnum;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.Objects;

@Component
public class DiffEvaluator {
  private static final BigDecimal THRESHOLD = new BigDecimal("10");

  public DiffDecision evaluate(BaselineInput baseline, SnapshotInput snapshot) {
    // 新 closed_month
    if (baseline.closedMonth() != null && snapshot.closedMonth() != null
        && baseline.closedMonth().isBefore(snapshot.closedMonth())) {
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.SILENT_NEW_MONTH, null);
    }

    // 基准源切换
    if (!Objects.equals(baseline.benchmarkSource(), snapshot.benchmarkSource())) {
      BigDecimal delta = absDelta(baseline.percentile(), snapshot.percentile());
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.SOURCE_FLIPPED, delta);
    }

    BigDecimal delta = absDelta(baseline.percentile(), snapshot.percentile());
    boolean peerChanged = PeerDiffUtil.peerChanged(baseline.peerSnapshot(), snapshot.peerSnapshot());
    boolean ownChanged = !Objects.equals(
        baseline.ownValue() == null ? null : baseline.ownValue().stripTrailingZeros(),
        snapshot.ownValue() == null ? null : snapshot.ownValue().stripTrailingZeros());

    boolean breached = delta != null && delta.compareTo(THRESHOLD) >= 0;

    if (!peerChanged && ownChanged) {
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.SILENT_REVISED, delta);
    }
    if (peerChanged && !breached) {
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.SILENT_BELOW_THRESHOLD, delta);
    }
    if (peerChanged && breached && !ownChanged) {
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.PEER_DRIVEN_SHIFT, delta);
    }
    if (peerChanged && breached && ownChanged) {
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.VALUE_AND_PEER_SHIFT, delta);
    }
    return new DiffDecision(BenchmarkPositionTriggerReasonEnum.SILENT_BELOW_THRESHOLD, delta);
  }

  private BigDecimal absDelta(BigDecimal a, BigDecimal b) {
    if (a == null || b == null) return null;
    return a.subtract(b).abs();
  }
}
```

- [ ] **C2.5：运行测试验证通过 + commit**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=DiffEvaluatorTest -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/ \
        gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/service/DiffEvaluatorTest.java
git commit -m "feat: DiffEvaluator 决策引擎 + 单测"
```

---

### Task C3：FirstTimeDecider

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/FirstTimeDecider.java`
- Create: `gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/service/FirstTimeDeciderTest.java`

- [ ] **C3.1：写失败测试**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.gstdev.cioaas.web.fi.enums.BenchmarkPositionTriggerReasonEnum;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;

class FirstTimeDeciderTest {
  private final FirstTimeDecider decider = new FirstTimeDecider();

  @Test
  void validSnapshot_fires() {
    var snap = new SnapshotInput("c", "m", LocalDate.now(),
        new BigDecimal("50"), "PEER", new BigDecimal("1"),
        "[{\"companyId\":\"p1\",\"value\":10}]");
    assertEquals(BenchmarkPositionTriggerReasonEnum.INITIAL_FIRE,
        decider.decide(snap).reason());
  }

  @Test
  void nullPercentile_skip() {
    var snap = new SnapshotInput("c", "m", LocalDate.now(),
        null, null, null, null);
    assertEquals(BenchmarkPositionTriggerReasonEnum.SKIP_NO_DATA,
        decider.decide(snap).reason());
  }

  @Test
  void emptyPeerSnapshot_skip() {
    var snap = new SnapshotInput("c", "m", LocalDate.now(),
        new BigDecimal("50"), "PEER", new BigDecimal("1"), "[]");
    assertEquals(BenchmarkPositionTriggerReasonEnum.SKIP_NO_DATA,
        decider.decide(snap).reason());
  }
}
```

- [ ] **C3.2：实现 FirstTimeDecider**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.gstdev.cioaas.web.fi.enums.BenchmarkPositionTriggerReasonEnum;
import org.springframework.stereotype.Component;

@Component
public class FirstTimeDecider {
  public DiffDecision decide(SnapshotInput snap) {
    if (snap.percentile() == null) {
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.SKIP_NO_DATA, null);
    }
    String peer = snap.peerSnapshot();
    if (peer == null || peer.isBlank() || peer.trim().equals("[]")) {
      return new DiffDecision(BenchmarkPositionTriggerReasonEnum.SKIP_NO_DATA, null);
    }
    return new DiffDecision(BenchmarkPositionTriggerReasonEnum.INITIAL_FIRE, null);
  }
}
```

- [ ] **C3.3：运行测试 + commit**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=FirstTimeDeciderTest -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/FirstTimeDecider.java \
        gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/service/FirstTimeDeciderTest.java
git commit -m "feat: FirstTimeDecider 首次判定组件 + 单测"
```

---

### Task C4：ClosedMonthResolver

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/ClosedMonthResolver.java`
- Create: `gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/service/ClosedMonthResolverTest.java`

- [ ] **C4.1：定位现有推导**

先读 `ColleagueCompanyServiceImpl.java` 里 `latestCurrentData.getDate()` 附近代码，确认 Manual/Automatic 的分支逻辑。

- [ ] **C4.2：实现 ClosedMonthResolver**

签名：

```java
public LocalDate resolve(String companyId, LocalDate referenceDate);
```

需求 2.2 描述的规则：
- Manual 公司：取 FinancialEntry 表中最后一个有 Actuals 的月份（如 `2026-03-01`）
- Automatic 公司：referenceDate 过了 15 号 → 上月（若无 actuals 继续回溯）；没过 15 号 → 上上月（同回溯）

实现时依赖 `FinancialSettingService` 判断 company 是 Manual / Automatic，然后查 `FinancialEntryRepository` 找有 actuals 的最后月份。

- [ ] **C4.3：写单测**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ClosedMonthResolverTest {

  @Mock private com.gstdev.cioaas.web.fi.service.FinancialSettingService settingService;
  @Mock private com.gstdev.cioaas.web.fi.repository.FinancialEntryRepository entryRepo;

  @InjectMocks private ClosedMonthResolver resolver;

  @Test
  void manualCompany_returnsLastActualsMonth() {
    when(settingService.isAutomatic("C1")).thenReturn(false);
    when(entryRepo.findLastActualsMonth("C1")).thenReturn(LocalDate.of(2026, 3, 1));
    LocalDate r = resolver.resolve("C1", LocalDate.of(2026, 4, 23));
    assertEquals(LocalDate.of(2026, 3, 1), r);
  }

  @Test
  void automaticPast15th_returnsPreviousMonth() {
    when(settingService.isAutomatic("C2")).thenReturn(true);
    when(entryRepo.hasActualsOn("C2", LocalDate.of(2026, 3, 1))).thenReturn(true);
    LocalDate r = resolver.resolve("C2", LocalDate.of(2026, 4, 20));
    assertEquals(LocalDate.of(2026, 3, 1), r);
  }

  @Test
  void automaticBefore15th_returnsMonthBeforePrevious() {
    when(settingService.isAutomatic("C3")).thenReturn(true);
    when(entryRepo.hasActualsOn("C3", LocalDate.of(2026, 2, 1))).thenReturn(true);
    LocalDate r = resolver.resolve("C3", LocalDate.of(2026, 4, 10));
    assertEquals(LocalDate.of(2026, 2, 1), r);
  }

  @Test
  void automaticNoActualsCurrentMonth_walksBack() {
    when(settingService.isAutomatic("C4")).thenReturn(true);
    when(entryRepo.hasActualsOn("C4", LocalDate.of(2026, 3, 1))).thenReturn(false);
    when(entryRepo.hasActualsOn("C4", LocalDate.of(2026, 2, 1))).thenReturn(false);
    when(entryRepo.hasActualsOn("C4", LocalDate.of(2026, 1, 1))).thenReturn(true);
    LocalDate r = resolver.resolve("C4", LocalDate.of(2026, 4, 20));
    assertEquals(LocalDate.of(2026, 1, 1), r);
  }

  @Test
  void manualNoActualsAtAll_returnsNull() {
    when(settingService.isAutomatic("C5")).thenReturn(false);
    when(entryRepo.findLastActualsMonth("C5")).thenReturn(null);
    assertNull(resolver.resolve("C5", LocalDate.of(2026, 4, 20)));
  }

  @Test
  void nullCompanyId_returnsNull() {
    assertNull(resolver.resolve(null, LocalDate.now()));
  }
}
```

> 如果 `FinancialSettingService` / `FinancialEntryRepository` 的实际方法名不匹配（如不是 `isAutomatic` / `hasActualsOn` / `findLastActualsMonth`），实施时同步调整测试和 resolver 实现。

- [ ] **C4.4：commit**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=ClosedMonthResolverTest -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/ClosedMonthResolver.java \
        gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/service/ClosedMonthResolverTest.java
git commit -m "feat: ClosedMonthResolver 推导 Manual/Automatic 公司的 closed_month + 单测"
```

---

## 阶段 D — 编排与集成组件

### Task D1：SnapshotBuilder（算 percentile + peer 快照）

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/SnapshotBuilder.java`

- [ ] **D1.1：定位"给定 (companyId, metricId, month) → (ownValue, peerValues, isReverse)"已有路径**

grep `InternalPercentileCalculator` 现有调用点（很可能在 `BenchmarkingServiceImpl` 或 `BenchmarkRawDataService`）。目标：复用同一条数据路径获取 peerValues，不要手写 SQL。

- [ ] **D1.2：实现 SnapshotBuilder**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gstdev.cioaas.web.fi.benchmark.engine.InternalPercentileCalculator;
import com.gstdev.cioaas.web.fi.benchmark.engine.InternalPercentileResult;
import com.gstdev.cioaas.web.fi.benchmark.engine.PeerGroupResolver;
import com.gstdev.cioaas.web.fi.enums.DataSourceEnum;
import com.gstdev.cioaas.web.fi.enums.MetricEnum;
import com.gstdev.cioaas.web.system.domain.Invite;
import com.gstdev.cioaas.web.system.service.CompanyService;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class SnapshotBuilder {
  private static final ObjectMapper MAPPER = new ObjectMapper();

  @Resource private PeerGroupResolver peerGroupResolver;
  @Resource private InternalPercentileCalculator percentileCalculator;
  @Resource private CompanyService companyService;
  @Resource private MetricValueLoader metricValueLoader;   // D1.3 新增

  public SnapshotInput buildFor(String companyId, String metricId, LocalDate closedMonth) {
    Invite company = companyService.findInviteById(companyId);
    if (company == null) {
      throw new IllegalStateException("Invite not found for companyId=" + companyId);
    }
    String monthStr = closedMonth.toString().substring(0, 7);   // YYYY-MM
    var peerResult = peerGroupResolver.resolve(company, monthStr, DataSourceEnum.ACTUALS);
    List<String> peerIds = peerResult.getPeerIds() == null ? List.of() : peerResult.getPeerIds();

    BigDecimal ownValue = metricValueLoader.load(companyId, metricId, closedMonth);

    List<Map<String, Object>> peerRows = new ArrayList<>();
    List<BigDecimal> peerValues = new ArrayList<>();
    for (String pid : peerIds) {
      BigDecimal v = metricValueLoader.load(pid, metricId, closedMonth);
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("companyId", pid);
      row.put("value", v);
      peerRows.add(row);
      if (v != null) peerValues.add(v);
    }

    MetricEnum metric = MetricEnum.fromMetricId(metricId);
    boolean isReverse = isReversePercentile(metric);
    String source = peerValues.isEmpty() ? "PLATFORM" : "PEER";

    InternalPercentileResult result = null;
    if (ownValue != null && !peerValues.isEmpty()) {
      result = percentileCalculator.calculate(ownValue, peerValues, isReverse);
    }
    BigDecimal percentile = (result == null || result.getPercentile() == null)
        ? null
        : BigDecimal.valueOf(result.getPercentile()).setScale(2, java.math.RoundingMode.HALF_UP);

    String peerSnapshot;
    try {
      peerSnapshot = MAPPER.writeValueAsString(peerRows);
    } catch (Exception e) {
      log.warn("Failed to serialize peer snapshot, fallback to []", e);
      peerSnapshot = "[]";
    }

    return new SnapshotInput(companyId, metricId, closedMonth,
        percentile, source, ownValue, peerSnapshot);
  }

  /**
   * 判断该指标是否"越小越好"——参考 InternalPercentileCalculator 既有调用点的推导。
   * 当前 6 个指标里，Monthly Net Burn Rate 是越小越好；其余越大越好。
   */
  static boolean isReversePercentile(MetricEnum metric) {
    if (metric == null) return false;
    return metric == MetricEnum.MONTHLY_NET_BURN_RATE;
  }
}
```

- [ ] **D1.3：新建 `MetricValueLoader`**

新文件 `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/MetricValueLoader.java`：

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.gstdev.cioaas.web.fi.benchmark.engine.InternalPercentileCalculator;  // 参考其调用点
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 包装项目既有的"给定 (companyId, metricId, month) 返回该指标值"查询。
 *
 * 实施步骤：
 *  1. grep 项目中 {@link InternalPercentileCalculator} 的调用点
 *     （通常在 BenchmarkingServiceImpl / PortfolioBenchmarkServiceImpl）；
 *  2. 看它如何组织 targetValue + peerValues 的查询——把同样的路径抽出来；
 *  3. 此处只是一个薄 wrapper，不新写 SQL。
 */
@Component
public class MetricValueLoader {

  // 实施阶段：按既有计算路径 @Resource 注入对应的 repository / service，
  // 完成 load() 方法。示例（按项目实际 API 调整）：
  //   @Resource private FinancialNormalizedService normalizedService;
  //   return normalizedService.getMetricValue(companyId, metricId, month);

  public BigDecimal load(String companyId, String metricId, LocalDate month) {
    throw new UnsupportedOperationException(
        "实施阶段按 InternalPercentileCalculator 既有调用路径补齐，不新写 SQL");
  }
}
```

> 这个 class 的真正实现需要在实施阶段通过 grep `InternalPercentileCalculator` / `percentileCalculator.calculate` 的调用点来确认——本 plan 留空壳以保持 `SnapshotBuilder` 编译通过。最终提交前必须替换掉 `throw`。

- [ ] **D1.3：编译 + commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/SnapshotBuilder.java
git commit -m "feat: SnapshotBuilder 复用 PeerGroupResolver + InternalPercentileCalculator 生成当期快照"
```

---

### Task D2：PositionNotifier（邮件 + 横幅聚合发送）

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/PositionNotifier.java`

- [ ] **D2.1：构造器注入依赖**

```java
@Component
@Slf4j
public class PositionNotifier {
  @Resource private UserService userService;
  @Resource private EmailService emailService;
  @Resource private BenchmarkNotifyAlertService alertService;
  @Value("${email.sender_email:noreply@lookingglass.io}") private String senderEmail;
}
```

- [ ] **D2.2：实现 notify(Set<String> firedCompanyIds)**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

import com.gstdev.cioaas.common.utils.SimpleEmailUtil;
import com.gstdev.cioaas.web.fi.contract.benchmarkNotify.BenchmarkNotifyAlertSaveInput;
import com.gstdev.cioaas.web.fi.enums.BenchmarkNotifyAlertEnum;
import com.gstdev.cioaas.web.fi.service.BenchmarkNotifyAlertService;
import com.gstdev.cioaas.web.fi.util.Pair;
import com.gstdev.cioaas.web.system.contract.user.UserEmailDto;
import com.gstdev.cioaas.web.system.domain.Email;
import com.gstdev.cioaas.web.system.enums.EmailTypeEnum;
import com.gstdev.cioaas.web.system.service.EmailService;
import com.gstdev.cioaas.web.system.service.UserService;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.thymeleaf.context.Context;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class PositionNotifier {
  private static final String ROLE_TYPE_PORTFOLIO = "1";
  private static final String ROLE_TYPE_COMPANY = "2";
  private static final String URL_FINANCE_BENCHMARK = "/Finance?params=";
  private static final String URL_COMPANY_BENCHMARK = "/company?params=";
  private static final String TEMPLATE = "BenchmarkPositionUpdate";

  @Resource private UserService userService;
  @Resource private EmailService emailService;
  @Resource private BenchmarkNotifyAlertService alertService;

  @Value("${email.sender_email:noreply@lookingglass.io}")
  private String senderEmail;

  public void notify(Set<String> firedCompanyIds) {
    if (firedCompanyIds == null || firedCompanyIds.isEmpty()) return;

    List<UserEmailDto> companyAdmins = userService.getAllCompanyAdmin().stream()
        .filter(u -> firedCompanyIds.contains(u.getOrgId())).collect(Collectors.toList());
    List<UserEmailDto> portfolioManagers = userService.getAllPortfolioManager().stream()
        .filter(u -> firedCompanyIds.contains(u.getOrgId())).collect(Collectors.toList());
    // 横幅：所有 admin / company user 也要入 alert（与 2.1 一致）
    List<UserEmailDto> allAdmin = userService.getAllAdminWithPortfolio().stream()
        .filter(u -> firedCompanyIds.contains(u.getOrgId())).collect(Collectors.toList());
    List<UserEmailDto> companyUsers = userService.getAllCompanyUser().stream()
        .filter(u -> firedCompanyIds.contains(u.getOrgId())).collect(Collectors.toList());

    // Company Admin：每公司一封
    companyAdmins.forEach(this::sendOne);

    // Portfolio Manager：按 (userId, parentId) 分组，一封列所有 portfolio 名
    Map<String, List<UserEmailDto>> pmGroups = portfolioManagers.stream()
        .collect(Collectors.groupingBy(u -> u.getId() + "||" + Objects.toString(u.getParentId(), "")));
    pmGroups.forEach((k, rows) -> sendOne(rows.get(0)));

    // 横幅写入
    Stream.of(companyAdmins, portfolioManagers, allAdmin, companyUsers)
        .flatMap(List::stream)
        .forEach(this::saveAlert);
  }

  private void sendOne(UserEmailDto user) {
    String fullUrl;
    if (ROLE_TYPE_COMPANY.equals(user.getRoleType())) {
      String param = String.format("companyId=%s&active=5&userId=%s", user.getOrgId(), user.getId());
      fullUrl = URL_FINANCE_BENCHMARK + Base64.getEncoder().encodeToString(param.getBytes(StandardCharsets.UTF_8));
    } else {
      String param = String.format("portfolioId=%s&active=5&userId=%s&organizationId=%s",
          user.getOrgId(), user.getId(), user.getParentId());
      fullUrl = URL_COMPANY_BENCHMARK + Base64.getEncoder().encodeToString(param.getBytes(StandardCharsets.UTF_8));
    }

    Email email = new Email();
    email.setSenderEmail(senderEmail);
    email.setReceiverEmail(user.getEmail());
    email.setOperator(user.getDisplayName());
    email.setSubject("Update to Benchmark Positioning");

    Context ctx = new Context();
    ctx.setVariable("username", user.getDisplayName());
    ctx.setVariable("url", fullUrl);

    Pair<Boolean, String> res = emailService.sendEmail(email, ctx, TEMPLATE,
        EmailTypeEnum.BENCHMARK_POSITION_UPDATE);
    if (Boolean.FALSE.equals(res.getFirst())) {
      log.error("Send position-update email failed: user={} err={}", user.getId(), res.getSecond());
    }
  }

  private void saveAlert(UserEmailDto user) {
    int notifyType;
    String companyId = "";
    String companyGroupId = "";
    if (ROLE_TYPE_PORTFOLIO.equals(user.getRoleType())) {
      notifyType = BenchmarkNotifyAlertEnum.POSITION_UPDATE_PORTFOLIO_ADMIN.getCode();
      companyGroupId = user.getOrgId();
    } else {
      notifyType = BenchmarkNotifyAlertEnum.POSITION_UPDATE_COMPANY.getCode();
      companyId = user.getOrgId();
    }
    BenchmarkNotifyAlertSaveInput input = BenchmarkNotifyAlertSaveInput.builder()
        .userId(user.getId())
        .companyId(companyId)
        .companyGroupId(companyGroupId)
        .notifyType(notifyType)
        .content("")
        .build();
    alertService.save(input);
  }
}
```

> 说明：POSITION_UPDATE_PORTFOLIO_COMPANY(5) 这个 enum 在当前 notifier 里暂未使用——如果需求明确"某角色看 portfolio 视角时用 5"，实施阶段对照 2.1 的 `saveAlert` 逻辑再调整；目前按"portfolio → 4、company → 3"的二分简化处理。

- [ ] **D2.3：commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/PositionNotifier.java
git commit -m "feat: PositionNotifier 聚合邮件与横幅发送"
```

---

### Task D3：BenchmarkPositionMonitorService 接口 + 实现

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/BenchmarkPositionMonitorService.java`
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/BenchmarkPositionMonitorServiceImpl.java`

- [ ] **D3.1：接口**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.service;

public interface BenchmarkPositionMonitorService {
  String runMonthlyCheck();          // 返回 runId
  void runFirstTimeCatchup();        // Path A
  void rerunDiff(String runId);      // 手动重跑
}
```

- [ ] **D3.2：实现类骨架**

```java
@Service
@Slf4j
public class BenchmarkPositionMonitorServiceImpl implements BenchmarkPositionMonitorService {

  private static final List<MetricEnum> MONITORED = List.of(
      MetricEnum.ARR_GROWTH_RATE, MetricEnum.GROSS_MARGIN,
      MetricEnum.MONTHLY_NET_BURN_RATE, MetricEnum.MONTHLY_RUNWAY,
      MetricEnum.RULE_OF_40, MetricEnum.SALES_EFFICIENCY_RATIO);

  @Resource private SnapshotBuilder snapshotBuilder;
  @Resource private DiffEvaluator diffEvaluator;
  @Resource private FirstTimeDecider firstTimeDecider;
  @Resource private PositionNotifier notifier;
  @Resource private ClosedMonthResolver closedMonthResolver;
  @Resource private CompanyService companyService;
  @Resource private BenchmarkPositionBaselineRepository baselineRepo;
  @Resource private BenchmarkPositionRunRepository runRepo;
  @Resource private BenchmarkPositionRunSnapshotRepository snapshotRepo;

  @Override
  public String runMonthlyCheck() {
    FinancialBenchmarkPositionRun run = new FinancialBenchmarkPositionRun();
    run.setRunTriggerTime(Instant.now());
    run.setPhase("SNAPSHOT");
    runRepo.save(run);

    List<Invite> companies = listEligibleCompanies();
    run.setCompanyCount(companies.size());
    runRepo.save(run);

    // Phase 1
    phase1Snapshot(run.getId(), companies);
    run.setPhase("DIFF");
    runRepo.save(run);

    // Phase 2
    Set<String> firedCompanies = phase2Diff(run.getId());
    notifier.notify(firedCompanies);

    run.setPhase("COMPLETED");
    // fired_count/silent_count 由 phase2Diff 回填到 run（或由 controller 汇总）
    runRepo.save(run);
    return run.getId();
  }

  @Override
  public void runFirstTimeCatchup() {
    List<Invite> companies = listEligibleCompanies();
    Set<String> firedCompanies = new HashSet<>();
    for (Invite c : companies) {
      LocalDate closedMonth = safelyResolveClosedMonth(c.getId());
      if (closedMonth == null) continue;
      for (MetricEnum metric : MONITORED) {
        if (baselineRepo.existsByCompanyIdAndMetricId(c.getId(), metric.getMetricId())) continue;
        SnapshotInput snap = safelyBuildSnapshot(c.getId(), metric.getMetricId(), closedMonth);
        if (snap == null) continue;
        DiffDecision d = firstTimeDecider.decide(snap);
        if (d.reason().writesBaseline()) saveBaseline(snap, d, null);
        if (d.reason().fires()) firedCompanies.add(c.getId());
      }
    }
    notifier.notify(firedCompanies);
  }

  @Override
  public void rerunDiff(String runId) {
    // 清空现有 snapshot 的 diff_decision/diff_delta
    snapshotRepo.findAllByRunId(runId).forEach(s -> {
      s.setDiffDecision(null);
      s.setDiffDelta(null);
    });
    Set<String> firedCompanies = phase2Diff(runId);
    notifier.notify(firedCompanies);
  }

  // --- 内部工具 ---

  private void phase1Snapshot(String runId, List<Invite> companies) {
    for (Invite c : companies) {
      LocalDate cm = safelyResolveClosedMonth(c.getId());
      for (MetricEnum metric : MONITORED) {
        var rs = new FinancialBenchmarkPositionRunSnapshot();
        rs.setRunId(runId);
        rs.setCompanyId(c.getId());
        rs.setMetricId(metric.getMetricId());
        rs.setClosedMonth(cm);
        try {
          if (cm != null) {
            SnapshotInput snap = snapshotBuilder.buildFor(c.getId(), metric.getMetricId(), cm);
            rs.setPercentile(snap.percentile());
            rs.setBenchmarkSource(snap.benchmarkSource());
            rs.setOwnValue(snap.ownValue());
            rs.setPeerSnapshot(snap.peerSnapshot());
          } else {
            rs.setErrorMessage("closed_month 推导失败");
          }
        } catch (Exception e) {
          rs.setErrorMessage(e.getClass().getSimpleName() + ": " + e.getMessage());
          log.error("Phase 1 failure companyId={} metricId={}", c.getId(), metric.getMetricId(), e);
        }
        snapshotRepo.save(rs);
      }
    }
  }

  private Set<String> phase2Diff(String runId) {
    Set<String> fired = new HashSet<>();
    for (var rs : snapshotRepo.findAllByRunId(runId)) {
      if (rs.getErrorMessage() != null) {
        rs.setDiffDecision(BenchmarkPositionTriggerReasonEnum.SKIP_NO_DATA.name());
        snapshotRepo.save(rs);
        continue;
      }
      SnapshotInput snap = toSnapshotInput(rs);
      var baselineOpt = baselineRepo.findTopByCompanyIdAndMetricIdOrderByCreatedAtDesc(
          rs.getCompanyId(), rs.getMetricId());

      DiffDecision d;
      if (baselineOpt.isEmpty()) {
        d = firstTimeDecider.decide(snap);
      } else {
        d = diffEvaluator.evaluate(toBaselineInput(baselineOpt.get()), snap);
      }
      rs.setDiffDecision(d.reason().name());
      rs.setDiffDelta(d.delta());
      snapshotRepo.save(rs);

      if (d.reason().writesBaseline()) saveBaseline(snap, d, runId);
      if (d.reason().fires()) fired.add(rs.getCompanyId());
    }
    return fired;
  }

  private void saveBaseline(SnapshotInput snap, DiffDecision d, String runId) {
    var b = new FinancialBenchmarkPositionBaseline();
    b.setCompanyId(snap.companyId());
    b.setMetricId(snap.metricId());
    b.setClosedMonth(snap.closedMonth());
    b.setPercentile(snap.percentile());
    b.setBenchmarkSource(snap.benchmarkSource());
    b.setOwnValue(snap.ownValue());
    b.setPeerSnapshot(snap.peerSnapshot());
    b.setTriggerReason(d.reason().name());
    b.setNotified(d.reason().fires());
    b.setRunId(runId);
    baselineRepo.save(b);
  }

  private List<Invite> listEligibleCompanies() {
    return companyService.findActiveCompaniesWithPortfolio();
    // 具体方法按 companyService 实际 API 调整；排除 Exited/Shut down + 必须有 portfolio
  }

  private LocalDate safelyResolveClosedMonth(String companyId) {
    try { return closedMonthResolver.resolve(companyId, LocalDate.now()); }
    catch (Exception e) { log.warn("resolve closed_month failed: {}", companyId, e); return null; }
  }

  private SnapshotInput safelyBuildSnapshot(String cid, String mid, LocalDate cm) {
    try { return snapshotBuilder.buildFor(cid, mid, cm); }
    catch (Exception e) { log.warn("snapshot build failed cid={} mid={}", cid, mid, e); return null; }
  }

  private SnapshotInput toSnapshotInput(FinancialBenchmarkPositionRunSnapshot rs) {
    return new SnapshotInput(rs.getCompanyId(), rs.getMetricId(), rs.getClosedMonth(),
        rs.getPercentile(), rs.getBenchmarkSource(), rs.getOwnValue(), rs.getPeerSnapshot());
  }

  private BaselineInput toBaselineInput(FinancialBenchmarkPositionBaseline b) {
    return new BaselineInput(b.getClosedMonth(), b.getPercentile(),
        b.getBenchmarkSource(), b.getOwnValue(), b.getPeerSnapshot());
  }
}
```

> 注：`companyService.findActiveCompaniesWithPortfolio()` 是规划中的新方法；若 `CompanyService` 没有，需在本任务里一并新增（复用现有查询过滤）。

- [ ] **D3.3：commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/BenchmarkPositionMonitorService.java \
        gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/service/BenchmarkPositionMonitorServiceImpl.java
git commit -m "feat: BenchmarkPositionMonitorService 编排 Phase 1/2 + 首次补发 + 重跑"
```

---

### Task D4：BenchmarkPositionInitializer 启动钩子

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/startup/BenchmarkPositionInitializer.java`

- [ ] **D4.1：新建类**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.startup;

import com.gstdev.cioaas.web.fi.benchmark.position.service.BenchmarkPositionMonitorService;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

@Slf4j
@Component
public class BenchmarkPositionInitializer {

  @Resource(name = "ioExecutor")
  private Executor ioExecutor;

  @Resource
  private BenchmarkPositionMonitorService monitorService;

  @EventListener(ApplicationReadyEvent.class)
  public void onStartup() {
    log.info("Benchmark Position first-time catchup scheduling, eventTime={}", Instant.now());
    CompletableFuture.runAsync(() -> {
      try {
        monitorService.runFirstTimeCatchup();
        log.info("Benchmark Position first-time catchup completed");
      } catch (Exception e) {
        log.error("Benchmark Position first-time catchup failed", e);
      }
    }, ioExecutor);
  }
}
```

- [ ] **D4.2：commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/startup/BenchmarkPositionInitializer.java
git commit -m "feat: 启动时异步触发 Benchmark Position 首次补发"
```

---

### Task D5：Controller（两个 rerun 接口）

**Files：**
- Create: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/controller/BenchmarkPositionMonitorController.java`

- [ ] **D5.1：新建 Controller**

```java
package com.gstdev.cioaas.web.fi.benchmark.position.controller;

import com.gstdev.cioaas.common.web.Result;
import com.gstdev.cioaas.web.fi.benchmark.position.service.BenchmarkPositionMonitorService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

@Tag(name = "Benchmark: Position Monitor")
@RestController
@RequestMapping("/benchmark/position-monitor")
public class BenchmarkPositionMonitorController {

  @Resource
  private BenchmarkPositionMonitorService service;

  @Operation(summary = "Re-run the DIFF phase for a given runId (resend emails)")
  @PostMapping("/rerun-diff/{runId}")
  public Result<String> rerunDiff(@PathVariable String runId) {
    service.rerunDiff(runId);
    return Result.success("rerun dispatched");
  }

  @Operation(summary = "Re-run first-time catch-up for all unseeded (company, metric)")
  @PostMapping("/rerun-first-time")
  public Result<String> rerunFirstTime() {
    service.runFirstTimeCatchup();
    return Result.success("catchup dispatched");
  }
}
```

- [ ] **D5.2：commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/fi/benchmark/position/controller/BenchmarkPositionMonitorController.java
git commit -m "feat: Position Monitor 两个 rerun 接口"
```

---

## 阶段 E — 调度接入

### Task E1：FixedScheduleTypeEnum + ScheduleProcessor

**Files：**
- Modify: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/scheduler/enums/FixedScheduleTypeEnum.java`
- Modify: `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/scheduler/service/ScheduleProcessor.java`

- [ ] **E1.1：加 enum**

在 `FixedScheduleTypeEnum` 末尾（分号前）追加一行：

```java
BenchmarkPositionMonitor("BenchmarkPositionMonitor", "cron(0 6 25 * ? *)");
```

如果最后一项本来就以分号结尾，把分号移到新项之后。

- [ ] **E1.2：在 ScheduleProcessor 加依赖**

类头部：

```java
@Resource
@Lazy
private com.gstdev.cioaas.web.fi.benchmark.position.service.BenchmarkPositionMonitorService
    benchmarkPositionMonitorService;
```

- [ ] **E1.3：加 switch case**

在 `processMessage(...)` 的 switch 中紧接 `case QuarterlyBenchmarkReport:` 之后加：

```java
case BenchmarkPositionMonitor:
    benchmarkPositionMonitorService.runMonthlyCheck();
    break;
```

- [ ] **E1.4：编译 + commit**

```bash
mvn -pl gstdev-cioaas-web compile -q
git add gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/scheduler/enums/FixedScheduleTypeEnum.java \
        gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/scheduler/service/ScheduleProcessor.java
git commit -m "feat: 接入每月 25 号 06:00 UTC 的 BenchmarkPositionMonitor 定时任务"
```

---

## 阶段 F — 集成测试与收尾

### Task F1：Position Monitor 集成测试（关键路径）

**Files：**
- Create: `gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/BenchmarkPositionMonitorIT.java`

- [ ] **F1.1：编写 `@SpringBootTest` 集成测试**

覆盖 3 种场景：
1. 种子 1 家合格公司 + 6 指标，首次跑 `runMonthlyCheck` → 基线表写 ≤ 6 行，邮件 mock 被调用；
2. 已有 baseline 情况下，peer 数据不变 → `SILENT_*` decision 占主导，不发邮件；
3. 已有 baseline 情况下，人为改 peer 值触发 `PEER_DRIVEN_SHIFT` → 发邮件。

使用 `@MockBean` mock `EmailService` 和 `BenchmarkNotifyAlertService`（或直接 spy），断言调用次数。

- [ ] **F1.2：运行 + commit**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=BenchmarkPositionMonitorIT -q
git add gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/benchmark/position/BenchmarkPositionMonitorIT.java
git commit -m "test: BenchmarkPositionMonitor 集成测试覆盖 3 关键路径"
```

---

### Task F2：权限过滤 & 邮件切换集成测试

**Files：**
- Create: `gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/BenchmarkNotifyAlertPermissionIT.java`
- Create: `gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/BenchmarkEntryUpdateEmailIT.java`

- [ ] **F2.1：权限过滤 IT**

造一个 portfolio_admin 用户 + 一个他原本管理的 company_group，save 一条 `ENTRY_UPDATE_PORTFOLIO_ADMIN` alert；断开用户与该 group 的绑定（模拟失权）；调用 `getNotifyAlert` → 期望返回 null。

- [ ] **F2.2：邮件切换 IT**

用 mock `EmailService` 捕获调用参数，调用 `BenchmarkEntryServiceImpl.addDetail` 触发新 platform-edition；断言：
- `templateName == "BenchmarkEntryUpdate"`
- `emailType == BENCHMARK_ENTRY_UPDATE`
- Context 变量包含 username/platform/edition/orgDisplay/url

- [ ] **F2.3：运行 + commit**

```bash
mvn -pl gstdev-cioaas-web test -Dtest=BenchmarkNotifyAlertPermissionIT,BenchmarkEntryUpdateEmailIT -q
git add gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/BenchmarkNotifyAlertPermissionIT.java \
        gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/fi/BenchmarkEntryUpdateEmailIT.java
git commit -m "test: 2.1 权限过滤 + 邮件切换集成测试"
```

---

### Task F3：端到端冒烟

- [ ] **F3.1：完整构建**

```bash
mvn clean install -pl gstdev-cioaas-web -am -q
```

预期：BUILD SUCCESS，无测试失败。

- [ ] **F3.2：本地启动 web 服务（可选）**

```bash
set -a && source .env && set +a
mvn spring-boot:run -pl gstdev-cioaas-web
```

观察日志：`Benchmark Position first-time catchup scheduling` 日志出现 + 异步完成日志出现，`initFixedScheduler` 内 `BenchmarkPositionMonitor` 被创建或同步。

- [ ] **F3.3：手动调用两个重跑接口（冒烟）**

```bash
# 拿一个存在的 runId（先查数据库 financial_benchmark_position_run）
curl -X POST http://localhost:5213/web/benchmark/position-monitor/rerun-first-time -H "Authorization: Bearer <token>"
curl -X POST http://localhost:5213/web/benchmark/position-monitor/rerun-diff/<runId> -H "Authorization: Bearer <token>"
```

预期：HTTP 200，日志显示 notifier 被调用。

- [ ] **F3.4：push 分支**

```bash
git push -u origin feature/benchmark-notify-update
```

---

## 验收清单（对齐需求文档）

- [ ] 2.1 外部行业基准更新：邮件用新模板 + `BENCHMARK_ENTRY_UPDATE` 枚举
- [ ] 2.1 横幅：失权用户调用 `GET /benchmark/notify-alerts` 不返回
- [ ] 2.2 每月 25 号 06:00 UTC 定时执行
- [ ] 2.2 启动时异步补发首次邮件
- [ ] 2.2 决策枚举 8 种场景全覆盖
- [ ] 2.2 每公司一封邮件，PM 按 org 聚合
- [ ] 2.2 `rerun-diff/{runId}` 重跑 DIFF 并重发
- [ ] 2.2 `rerun-first-time` 手动补发
- [ ] Exited/Shut down / 未绑定 portfolio 的公司被排除
- [ ] 新增 3 张表 DDL 已归档到 `db/ddl/`

---

## 已知实施期需现场确认项

| 代号 | 事项 | 解决方式 |
|-----|-----|---------|
| U1 | `companyService` 获取合格公司列表的具体方法 | 实施 D3.2 时 grep 既有 "active && portfolio" 查询，复用；若无则新增一个 `findActiveCompaniesWithPortfolio()` |
| U2 | `MetricEnum` 是否携带 `isReverse` 字段 | 实施 D1.2 时读 `InternalPercentileCalculator` 现有调用点，模仿其推导 |
| U3 | 指标值（ownValue）按 (company, metric, month) 的查询路径 | 实施 D1.2 时依照 `BenchmarkingServiceImpl` 现行路径复用，不要新写 SQL |
| U4 | JPA `ddl-auto` 是否会自动建 3 张表 | 若自动创建成功，DDL 文件仅作归档；若否，运维按 `db/ddl/benchmark-position-monitor.sql` 手动执行 |
| U5 | `UserService` 既有"可见公司"查询方法 | 实施 A4.1 时 grep 确认；若无，按现有 role/portfolio 关系新写一条 JPA 查询 |

---

## 不做（YAGNI 锁定）

- 前端横幅组件、`dismiss` 按钮、`GET /benchmark/notify-alerts` 客户端调用——不在本次范围
- FinancialEntry 编辑路径的钩子——"被修订的静默更新"由月度批收敛
- SQS worker / 水平扩展拓扑——单机串行已足够
- first-email-sent 标志位——用 baseline 表存在性派生
