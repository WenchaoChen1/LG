# Redirect to Benchmark Dashboard — 技术设计文档（TDD）

> v1.0 | 2026-04-22 | 关联需求：`01-prd.md`（v2.0）、`02-prd-review.md`
> 范围：**后端 only**（Java / Spring Boot 3.3，模块 `gstdev-cioaas-web`）

## 一、做什么 & 怎么做

**需求**：公司 close_month 前进时落一条通知记录；前端据此决定是否展示条幅；用户可关闭条幅；下次 close_month 再前进时重生成。

**方案**：两张新表（`company_close_month_update` / `company_close_month_update_dismiss`）+ 2 个接口 + 1 个内部服务，在手动保存与 QBO Accept 两个现有服务方法的**事务提交后**发布 Spring 事件触发。

**改动范围**：

| 模块 | 改动 | 类型 |
|------|------|------|
| `fi/domain/CompanyCloseMonthUpdate.java` | 新增 | 新文件 |
| `fi/domain/CompanyCloseMonthUpdateDismiss.java` | 新增 | 新文件 |
| `fi/repository/CompanyCloseMonthUpdateRepository.java` | 新增 | 新文件 |
| `fi/repository/CompanyCloseMonthUpdateDismissRepository.java` | 新增 | 新文件 |
| `fi/service/BenchmarkNotificationService.java` + `Impl` | 新增 | 新文件 |
| `fi/event/CloseMonthUpdatedEvent.java` + listener | 新增 | 新文件 |
| `fi/controller/BenchmarkNotificationController.java` | 新增 | 新文件 |
| `fi/contract/benchmarkNotification/*` | 新增 | DTO/Request/Response |
| `fi/mapper/BenchmarkNotificationMapper.java` | 新增 | MapStruct |
| `fi/service/FinanceManualDataServiceImpl.save()` | 追加 1 行事件发布 | **改动** |
| `quickbooks/application/service/QuickbooksSyncService.processSync()` | 追加 1 行事件发布 + 字段 | **改动** |
| DDL 迁移脚本 | 新增 2 表 | 新文件 |

---

## 二、接口设计

> 完整字段表见 `api-documentation.md`。基础路径 `/web`（Context-path），下列路径均为 Controller 级相对路径。

### API-01：查询条幅

`GET /benchmark-notification/banner`

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyId | String (UUID) | Y | Query 参数 |

**返回结构**（`Result<BenchmarkNotificationBannerResponse>`）：

```
{
  shouldShow: boolean — 是否展示条幅
  recordId:   String  — 条幅记录 ID；shouldShow=false 时可为 null
  closeMonth: String  — "yyyy-MM-dd"；shouldShow=false 时可为 null
  message:    String  — 条幅文案（BR-03 固定文本）；shouldShow=false 时可为 null
  source:     String  — MANUAL | QBO；shouldShow=false 时可为 null
}
```

**判定规则**（见 §四 4.3）：record 不存在 / 当前用户 = submitter / 已 dismiss → `shouldShow=false`；否则 `true`。

**错误情况**：
- `companyId` 为空或格式错误 → 400 `BadRequestException`
- `companyId` 对应公司不存在 → 400 `EntityNotFoundException`
- 未登录 → 401（Security 层）

### API-02：关闭条幅

`POST /benchmark-notification/dismiss`

**Body**（`CompanyCloseMonthUpdateDismissRequest`）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| companyId | String (UUID) | Y | — |

**返回结构**：`Result<Void>`（success / message）

**幂等语义**（BR-07）：已存在 `(record_id, user_id)` 时直接返回 success，不重复插入。

**错误情况**：
- `companyId` 非法 → 400
- 该公司当前无 notification record（无可关闭）→ 400 `"No active benchmark notification to dismiss"`；不降级为 success，便于前端检测不一致状态
- 未登录 → 401

---

## 三、数据设计

### 新建表

```sql
-- TBL-01: company_close_month_update
CREATE TABLE company_close_month_update (
  id                 VARCHAR(36)  NOT NULL,
  company_id         VARCHAR(36)  NOT NULL,
  close_month        DATE         NOT NULL,
  submitter_user_id  VARCHAR(36)  NULL,
  source             VARCHAR(16)  NOT NULL,
  created_at         TIMESTAMP    NOT NULL,
  created_by         VARCHAR(36)  NULL,
  updated_at         TIMESTAMP    NOT NULL,
  updated_by         VARCHAR(36)  NULL,
  CONSTRAINT pk_company_close_month_update PRIMARY KEY (id),
  CONSTRAINT uk_company_close_month_update_company UNIQUE (company_id)
);
COMMENT ON TABLE company_close_month_update IS 'Close month 推进后产生的公司级条幅记录，每家公司最多一条';
COMMENT ON COLUMN company_close_month_update.close_month IS '当前 close_month（resolveCloseMonthDate 返回的月首日）';
COMMENT ON COLUMN company_close_month_update.submitter_user_id IS '手动触发时 = 提交人 userId；QBO 触发时为 null';
COMMENT ON COLUMN company_close_month_update.source IS 'MANUAL | QBO';

-- TBL-02: company_close_month_update_dismiss
CREATE TABLE company_close_month_update_dismiss (
  id          VARCHAR(36) NOT NULL,
  record_id   VARCHAR(36) NOT NULL,
  user_id     VARCHAR(36) NOT NULL,
  created_at  TIMESTAMP   NOT NULL,
  created_by  VARCHAR(36) NULL,
  updated_at  TIMESTAMP   NOT NULL,
  updated_by  VARCHAR(36) NULL,
  CONSTRAINT pk_company_close_month_update_dismiss PRIMARY KEY (id),
  CONSTRAINT uk_company_close_month_update_dismiss UNIQUE (record_id, user_id),
  CONSTRAINT fk_company_close_month_update_dismiss_record
    FOREIGN KEY (record_id)
    REFERENCES company_close_month_update(id)
    ON DELETE CASCADE
);
CREATE INDEX idx_company_close_month_update_dismiss_user ON company_close_month_update_dismiss(user_id);
COMMENT ON TABLE company_close_month_update_dismiss IS '用户对某次条幅记录的关闭动作';
```

> 不加 `is_deleted`：本功能需要"硬删除 + FK 级联"语义；软删除会破坏 BR-02/BR-06 的级联清理。

**复用已有表**：

| 表名 | 用途 |
|------|------|
| `company` | `company_id` 外键来源（业务验证，非 DB FK） |
| `user` | `submitter_user_id` / `user_id` 业务引用（非 DB FK，允许用户删除后孤儿） |

---

## 四、核心逻辑

### 4.1 触发点接入（SC-01 / SC-02）

**改动策略**：不在 save() / processSync() 里直接调用 Notification 服务，而是发布 Spring 事件，由 `@TransactionalEventListener(phase = AFTER_COMMIT, fallbackExecution = true)` 监听。这样保证：

- 主事务**提交成功后**才触发记录（避免主 rollback 时留下孤儿记录）
- Listener 异常不回卷主事务（天然满足 BR-08）
- Listener 内部 try-catch 兜底，错误只记日志

**改动 1**：`FinanceManualDataServiceImpl.save()` 返回前追加：
```java
eventPublisher.publishEvent(new CloseMonthUpdatedEvent(
    financeManualDataSaveInput.getCompanyId(),
    SecurityUtils.getUserId(),
    CloseMonthUpdateSource.MANUAL));
```

**改动 2**：`QuickbooksSyncService.processSync()` 成功路径（`syncAllReports` 返回、`updateSyncStatus("success")` 之后）追加：
```java
eventPublisher.publishEvent(new CloseMonthUpdatedEvent(
    companyId,
    null,
    CloseMonthUpdateSource.QBO));
```

> `acceptChanges` 是用户审批 QBO 差异的 UI 操作，不落数据，**不是**本功能触发点。

**Listener**：`CloseMonthUpdatedEventListener`

```
@TransactionalEventListener(phase = AFTER_COMMIT, fallbackExecution = true)
onEvent(event):
    try:
        benchmarkNotificationService.recordCloseMonthUpdate(
            event.companyId, event.submitterUserId, event.source)
    catch (Exception e):
        log.error("recordCloseMonthUpdate failed, companyId={}", event.companyId, e)
        // 不抛出；BR-08
```

### 4.2 `recordCloseMonthUpdate` 核心流程（BR-01 / BR-02 / BR-05）

标注：`@Transactional(propagation = REQUIRES_NEW)` — 使用独立事务，避免被未提交的外部上下文影响。

```
recordCloseMonthUpdate(companyId, submitterUserId, source):
    1. newDate = colleagueCompanyService.resolveCloseMonthDate(companyId)
       └── newDate == null → log info("no close month"), return

    2. old = recordRepo.findByCompanyId(companyId)

    3. 判断：
       ├── old == null:
       │     INSERT new record(companyId, newDate, submitterUserId, source)
       ├── newDate > old.close_month:
       │     recordRepo.delete(old)          -- FK CASCADE 清所有 dismiss
       │     recordRepo.flush()              -- 避免唯一键冲突
       │     INSERT new record(...)
       ├── newDate == old.close_month:
       │     log info("same close_month, skip")
       └── newDate < old.close_month:
             log warn("close_month regressed: new={} old={}")

    4. 捕获 DataIntegrityViolationException（并发竞争）:
       重新调 findByCompanyId 并再次走步骤 3
```

### 4.3 `queryBanner` 判定（API-01 / BR-04 / BR-06）

```
queryBanner(companyId, currentUserId):
    1. 校验 companyId 合法
    2. record = recordRepo.findByCompanyId(companyId)
       └── 为 null → return {shouldShow:false}
    3. record.submitter_user_id == currentUserId → return {shouldShow:false}
    4. exists = dismissRepo.existsByRecordIdAndUserId(record.id, currentUserId)
       └── true → return {shouldShow:false}
    5. return {shouldShow:true, recordId, closeMonth, message=BR-03 常量, source}
```

### 4.4 `dismissBanner` 幂等插入（API-02 / BR-07 / BR-09）

```
dismissBanner(companyId, currentUserId):
    1. record = recordRepo.findByCompanyId(companyId)
       └── 为 null → 抛 BadRequestException("No active benchmark notification to dismiss")
    2. if dismissRepo.existsByRecordIdAndUserId(record.id, currentUserId):
         return success  -- 幂等
    3. try:
         dismissRepo.save(new CompanyCloseMonthUpdateDismiss(record.id, currentUserId))
       catch DataIntegrityViolationException:
         return success  -- 并发竞争落到唯一索引，视为幂等成功
```

**BR-09 说明**：API-02 仅接受 `companyId`，不接受 `recordId`。后端根据 companyId 反查 record 后再写 dismiss，杜绝跨公司构造。

---

## 五、风险 & 待定

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| R1 | `QuickbooksSyncService.processSync` 不带 `@Transactional`，全程由 `transactionTemplate.executeWithoutResult` 分段提交 | AFTER_COMMIT listener 在无 tx 场景需 `fallbackExecution = true` | 已在 listener 上启用 `fallbackExecution = true`；发布点放在方法末尾，异常会向上抛（不会触发事件） |
| R2 | `processSync` 成功后调 `resolveCompanyCloseMonth`，其内部依赖 FiData；QBO 刚落的数据到 FiData 的衍生路径可能还有异步/二次计算 | close_month 可能尚未"前进"，listener 会无 op | 先按现状集成；若发现 QBO 触发漏报，可在 QBO 数据归一化完成的步骤末尾再发一次事件 |
| R3 | `@TransactionalEventListener` 默认同步执行 listener，在外层事务提交后调用。若后续想改为异步（`@Async`）需加线程上下文配置（`SecurityContextHolder` 的 `MODE_INHERITABLETHREADLOCAL`） | 异步化可能丢登录上下文；当前同步即可 | 一期同步，不加 `@Async` |
| R4 | `resolveCloseMonthDate` 依赖 `ColleagueCompanyService`；是否存在循环依赖（benchmark 服务 → colleague 服务 → fi 数据）需实现时确认 | 构造失败 | 实现时先写冒烟测试验证 |
| R5 | 条幅文案 BR-03 为用户定稿但仍有"for have been"语法空档 | 非功能风险 | 代码里以常量方式暴露 `BenchmarkNotificationMessages.DEFAULT_BANNER`，日后 i18n 改造成本低 |
| R6 | `user_id` 无 FK 约束；若已删除用户仍在 dismiss 中 | 孤儿数据 | 不阻断本期；后续由用户清理 job 统一处理 |
| R7 | 同一 close_month 月内多次保存不重置 dismiss — 对"用户希望再次被提示"场景不友好 | 产品风险极小 | 与用户确认（Q-C 已确认接受） |

---

## 六、工作量

| 任务 | 大小 | 依赖 |
|------|------|------|
| 数据表迁移脚本（V{next}__benchmark_notification.sql） | S | — |
| Domain + Repository | S | 迁移脚本 |
| `BenchmarkNotificationService` + `Impl` + 单元测试 | M | Domain / Repo |
| Event 定义 + `TransactionalEventListener` | S | Service |
| `FinanceManualDataServiceImpl.save` 接入事件 | S | Event |
| `QuickbooksSyncService.processSync` 接入事件 | S | Event |
| Controller + Request/Response + Mapper | S | Service |
| 集成测试：手动 save / QBO accept 两条链路端到端 | M | 上述全部 |
| 回归：`/financeManualData`、QBO SQS 同步链路行为不变 | S | — |
| **合计** | ≈ 2-3 人日 | — |

---

## 七、自检清单

- [x] PRD SC-01/02/03/04 全部对应设计：触发链路（§四 4.1）、API-01（§四 4.3）、API-02（§四 4.4）
- [x] BR-01~BR-10 全部映射：§四 4.2（BR-01/02/05/08）、§四 4.3（BR-04/06）、§四 4.4（BR-07/09）、§三（BR-10 隐式——未对 QBO/MANUAL 之外的 source 开口）、§四 4.1（BR-08 经 TransactionalEventListener + try-catch）
- [x] DDL 字段含 UUID 主键 + 4 审计字段；不加 `is_deleted`（有意）
- [x] API-01/02 路径、方法、参数、返回结构、错误码齐全
- [x] 无「视情况」「按需」描述
- [x] 主文档 ≤ 300 行
- [x] API-xx / TBL-xx 编号连续唯一
- [x] 后端命名符合 `backend-java.md`：`*Service`/`*ServiceImpl`、`@Resource`、`Result<T>`、`AbstractCustomEntity`、`@UuidGenerator`、MapStruct
