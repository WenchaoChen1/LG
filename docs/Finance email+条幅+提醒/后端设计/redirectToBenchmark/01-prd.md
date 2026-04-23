# Redirect to Benchmark Dashboard — 产品需求文档（PRD）

> 版本：v2.0 | 更新日期：2026-04-22
> 变更摘要：基于 `02-prd-review.md` 澄清 P0 问题后重写。范围收敛为**后端 only**（前端由前端自行实现）；补齐 SC/BR/AC 编号与权限、错误处理、数据定义章节。

---

## 一、功能目的

| 问题 | 解决方案 |
|------|----------|
| 用户完成财务数据提交后需要手动切换到 Benchmark 页面才能看到最新对比，流程断裂 | 后端记录公司 close_month 更新事件 → 前端拉取记录后决定是否展示条幅 → 用户点击后跳转到 Benchmark 页 |
| 公司其他成员对"有新财务数据可看 Benchmark"无感知 | 条幅对**非提交人**展示；用户点"关闭"后永久解除本次条幅；下次 close_month 再推进时重新生成 |

**范围**：
- ✅ 后端：数据表 2 张、接口 2 个（查询条幅、关闭条幅）、两处触发点接入（手动保存、QBO Accept Changes）
- ❌ 前端：不在本次交付范围

---

## 二、使用场景

### 角色总览

| 角色 | 本功能相关权限 |
|------|----------------|
| 有该公司访问权限的所有用户（含 Admin、Member、Viewer 等——不分角色细分） | 可查询条幅、可关闭条幅 |
| **提交人**（Submitter）：手动保存 Actuals 的登录用户 | 不看到自己触发的条幅 |

> 本功能不新增权限维度；"有公司权限" = "能看条幅" = "能关条幅"。权限由现有公司访问控制在上层（接口拦截 / 前端页面进入）兜底。

---

### SC-01：手动录入 Actuals 触发 close_month 更新

| 项目 | 说明 |
|------|------|
| **角色** | 任何拥有公司权限、在 FinancialEntry 页执行 Save 的用户 |
| **触发条件** | `FinanceManualDataService.save()` 成功提交一批 Actuals 数据，且本次保存后 `resolveCloseMonthDate(companyId)` 返回的日期**严格晚于**当前 `company_close_month_update.close_month`（即公司 close_month 实际前进） |
| **目标** | 让除提交人外的所有该公司成员在下次进入 `/Finance` 时看到条幅提示，并可点击跳转到 Benchmark |

**后端行为**（详见 BR-01）：
1. 保存成功后调用 `BenchmarkNotificationService.recordCloseMonthUpdate(companyId, submitterUserId, MANUAL)`
2. Service 内部依据 BR-01 决定是 INSERT、REPLACE 还是跳过

**预期结果**：
- `company_close_month_update` 表含唯一一条该公司记录，`submitter_user_id` = 当前用户 ID，`source` = `MANUAL`
- 原 `company_close_month_update_dismiss` 中所有属于该公司记录的历史 dismiss 已级联删除

---

### SC-02：QBO 自动同步后触发 close_month 更新

| 项目 | 说明 |
|------|------|
| **角色** | 系统自动（SQS 消息驱动，无登录用户上下文，`submitter_user_id` = null） |
| **触发条件** | `QuickbooksSyncService.processSync(companyId)` 执行 `syncAllReports` 并将 P&L / BalanceSheet / CloseDate 全部落库成功（方法未抛异常），且本次同步后 `resolveCompanyCloseMonth(companyId)` 严格晚于当前记录 |
| **目标** | 所有该公司成员在下次进入 `/Finance` 时看到条幅 |

**后端行为**：
1. `processSync` 成功路径末尾发布 `CloseMonthUpdatedEvent(companyId, null, QBO)`；监听器依 BR-01/BR-02 决定是否 REPLACE

> 说明：`acceptChanges` 是用户审批 QBO 差异的 UI 交互，不会导致新数据落库，因此**不是**本 SC 的触发点。

---

### SC-03：前端查询条幅（跨用户）

| 项目 | 说明 |
|------|------|
| **角色** | 任意登录用户 |
| **触发条件** | 前端进入 `/Finance` 页面时调用本接口 |
| **目标** | 告诉前端是否展示条幅 |

**后端行为**：详见 API-01。返回 `shouldShow=true` 的判定：存在该公司 record ∧ 当前用户 ≠ submitter_user_id ∧ 当前用户未对该 record 执行过 dismiss。

---

### SC-04：用户关闭条幅

| 项目 | 说明 |
|------|------|
| **角色** | 任意已看到条幅的用户 |
| **触发条件** | 用户点击条幅"关闭" |
| **目标** | 本次 close_month 更新周期内不再对该用户显示条幅，直到下一个 close_month 推进 |

**后端行为**：详见 API-02。插入一条 `company_close_month_update_dismiss` 记录；已存在时幂等跳过。

---

## 三、功能模块

### 模块 1：Benchmark Notification 服务

| 元素 | 内容 | 行为 |
|------|------|------|
| `BenchmarkNotificationService.recordCloseMonthUpdate(companyId, submitterUserId, source)` | 核心触发方法 | 比对新旧 close_month；前进则 REPLACE（级联清 dismiss）；相等或不前进则跳过 |
| `BenchmarkNotificationService.queryBanner(companyId, currentUserId)` | 查询条幅 | 返回 `BenchmarkNotificationBannerDto` |
| `BenchmarkNotificationService.dismissBanner(companyId, currentUserId)` | 关闭条幅 | 插入 dismiss（幂等） |

### 模块 2：触发点接入

- **触发点 A — 手动保存**：在 `FinanceManualDataServiceImpl.save()` 成功返回前发布事件
- **触发点 B — QBO 自动同步**：在 `QuickbooksSyncService.processSync()` 成功路径发布事件

---

## 四、操作流程与反馈

### 4.1 手动保存触发（SC-01）

```text
用户 FinancialEntry → Save
    └── FinanceManualDataService.save() 成功
        └── BenchmarkNotificationService.recordCloseMonthUpdate(companyId, userId, MANUAL)
            ├── newDate = resolveCloseMonthDate(companyId)
            ├── oldRecord = 查询 company_close_month_update WHERE company_id = ?
            ├── 判断：
            │   ├── oldRecord 为 null → INSERT 新记录
            │   ├── newDate > oldRecord.close_month → 级联删除 dismiss + 删除 oldRecord + INSERT
            │   ├── newDate == oldRecord.close_month → 跳过（不重置 dismiss）
            │   └── newDate < oldRecord.close_month → 记 warn 日志并跳过（异常态，理论不发生）
            └── （异常不影响主流程，详见 BR-08）
```

### 4.2 QBO 自动同步触发（SC-02）

同 4.1，仅参数不同：`submitterUserId = null`、`source = QBO`。

### 4.3 前端查询与关闭（SC-03 / SC-04）

```text
前端进入 /Finance
    └── GET /benchmark-notification/banner?companyId=xxx
        ├── 查 record → 不存在 → {shouldShow:false}
        ├── record.submitter_user_id == currentUserId → {shouldShow:false}
        ├── 存在 dismiss(recordId, currentUserId) → {shouldShow:false}
        └── 其余 → {shouldShow:true, message, closeMonth, recordId}

用户点关闭
    └── POST /benchmark-notification/dismiss
        ├── body: {companyId}
        └── 查 record → 幂等 INSERT dismiss → 成功
```

---

## 五、页面内容

> **范围外**：页面 UI、布局、文案渲染由前端负责。本 PRD 仅规定条幅**文本内容**（BR-03），前端按需显示。

---

## 六、字段内容与字段限制

### 6.1 实体字段定义

| 实体 | 字段 | 类型 | 允许空 | 说明 |
|------|------|------|--------|------|
| company_close_month_update | id | VARCHAR(36) PK | N | UUID |
| company_close_month_update | company_id | VARCHAR(36) **UNIQUE** | N | 公司 ID；唯一约束保证每家公司最多 1 条 |
| company_close_month_update | close_month | DATE | N | 本次推进到的 close_month（取自 `resolveCloseMonthDate`） |
| company_close_month_update | submitter_user_id | VARCHAR(36) | Y | 手动触发时 = 提交人 ID；QBO 触发时 = null |
| company_close_month_update | source | VARCHAR(16) | N | 枚举：`MANUAL` / `QBO` |
| company_close_month_update | created_at/by, updated_at/by | 审计字段 | N | 继承 `AbstractCustomEntity` |
| company_close_month_update_dismiss | id | VARCHAR(36) PK | N | UUID |
| company_close_month_update_dismiss | record_id | VARCHAR(36) FK | N | 指向 record.id；外键 ON DELETE CASCADE |
| company_close_month_update_dismiss | user_id | VARCHAR(36) | N | 关闭条幅的用户 |
| company_close_month_update_dismiss | created_at/by, updated_at/by | 审计字段 | N | 继承 `AbstractCustomEntity` |

**唯一索引**：`company_close_month_update_dismiss.(record_id, user_id)`

### 6.2 输入校验

| 规则 | 说明 |
|------|------|
| companyId 必填、格式为 UUID、存在于 `company` 表 | 否则 400 BadRequest |
| currentUserId 来自 `SecurityUtils.getUserId()` | 未登录由 security 拦截 |

---

## 七、业务规则

| 序号 | 规则 | 内容 |
|------|------|------|
| **BR-01** | close_month 推进判定 | `resolveCloseMonthDate(companyId)` 严格晚于 `company_close_month_update.close_month` 才触发 REPLACE；相等或更早跳过 |
| **BR-02** | 级联清理 | REPLACE 时先删除该公司现有 record（含 FK 级联删除所有 dismiss），再 INSERT 新 record。用事务保证原子性 |
| **BR-03** | 条幅文本内容 | 固定字符串：`"Benchmark Data Updated. Benchmark results for have been updated based on the latest financial data."` — 由 API-01 返回给前端；后期如需 i18n 或补公司名，另开工单 |
| **BR-04** | 提交人豁免 | 手动路径：record.submitter_user_id = 当前用户 ID；API-01 查询时若 currentUserId == submitter_user_id 则 shouldShow=false |
| **BR-05** | QBO 不豁免任何人 | QBO 路径的 submitter_user_id = null；所有人都可能看到条幅 |
| **BR-06** | Dismiss 作用域 | 绑定到当前 record.id；record 被 REPLACE 时该条 dismiss 随之级联删除，用户下一次更新会再次看到条幅 |
| **BR-07** | Dismiss 幂等 | 同一用户对同一 record 多次调用 API-02，返回成功但仅保留 1 条 dismiss 记录（依赖唯一索引） |
| **BR-08** | 触发调用不阻塞主流程 | 触发点 A/B 的 `recordCloseMonthUpdate` 异常不得让 `save()` / `processSync()` 整体失败：监听器内 `try-catch` 并记 error 日志，主流程照常返回成功 |
| **BR-09** | 不跨公司泄漏 | API-02 以 companyId 反查 record；不允许前端直接传 recordId（防止构造跨公司 dismiss） |
| **BR-10** | 触发连接器白名单 | 初版仅 `MANUAL` 与 `QBO` 两类来源；新接入连接器默认**不**触发，需显式接入 |

---

## 八、错误处理与边界情况

| 场景 | 触发条件 | 系统行为 | 返回 |
|------|----------|----------|------|
| companyId 为空或不存在 | API-01 / API-02 入参非法 | Service 抛 `BadRequestException` / `EntityNotFoundException` | 由 `GlobalExceptionHandler` 统一包 `Result.fail` |
| 用户未登录 | Security 层拦截 | 无需 Service 判断 | 401 |
| 公司无 close_month 数据（`resolveCloseMonthDate` 返回 null） | 触发点调用时 | 跳过记录，不报错 | 无副作用 |
| 相同 close_month 重复触发（如同月多次保存） | newDate == oldRecord.close_month | 跳过（详见 BR-01） | 无副作用；dismiss 不重置 |
| close_month 回退（数据修正） | newDate < oldRecord.close_month | warn 日志，跳过 | 无副作用 |
| 并发触发（手动 + QBO 秒级内） | 两路径先后命中 | 依赖 `UNIQUE(company_id)` 与事务：后者若 close_month 相同则跳过；不同则正常 REPLACE | 最终一致 |
| 用户被删后查询条幅 | submitter_user_id 指向已删除用户 | 按字符串比较仍然生效；不连表校验 | 正常返回 |

---

## 九、权限矩阵

| 操作 | 有该公司权限的任意用户 | 无权限用户 |
|------|------------------------|------------|
| 触发点调用（内部） | — | — |
| API-01 查询条幅 | ✅ 允许（shouldShow 由 BR-04/06 决定） | ❌ 上游公司权限校验拦截 |
| API-02 关闭条幅 | ✅ 允许 | ❌ 上游公司权限校验拦截 |

> 本功能**不**引入独立权限点；复用前端页面进入 `/Finance` 所需的公司访问权限。

---

## 十、集成与外部依赖

| 依赖 | 用途 | 失败处理 |
|------|------|----------|
| `ColleagueCompanyService.resolveCloseMonthDate(companyId)` | 计算当前 close_month | 返回 null 时触发点跳过，不报错 |
| `FinanceManualDataServiceImpl.save()` | 手动触发点 | 接入点：save 成功后调用新服务；异常不影响 save |
| `QuickbooksSyncService.processSync()` | QBO 触发点（SQS 消息驱动） | 同上 |
| `SecurityUtils.getUserId()` | 当前用户上下文 | 未登录抛 401 |

---

## 十一、非功能性需求

| 项目 | 要求 |
|------|------|
| 性能 | API-01 响应 p95 ≤ 100ms（单次查询最多 2 条记录） |
| 事务 | 触发点内部使用独立事务；主流程失败不触发，触发失败不回滚主流程（BR-08） |
| 并发 | `UNIQUE(company_id)` 保证最多 1 条；并发冲突由 DB 兜底，Service 捕获 `DataIntegrityViolationException` 并回退到更新流 |
| 日志 | 触发点调用、REPLACE 动作、异常全部记入 log；包含 companyId、newDate、oldDate、source、submitterUserId |
| 兼容性 | 不影响现有 `/financeManualData`、QBO SQS 同步链路的行为 |

---

## 十二、验收标准（可判定通过/失败）

- [ ] **AC-01**：SC-01 场景下，提交人用户 A 保存使 close_month 从 2026-02 推进到 2026-03 后，数据库存在一条 `company_close_month_update (company_id=C, close_month=2026-03-01, submitter_user_id=A, source=MANUAL)`；原有记录被删除
- [ ] **AC-02**：AC-01 后，用户 A 调 API-01 返回 `shouldShow=false`；用户 B（同公司有权限）调 API-01 返回 `shouldShow=true, closeMonth=2026-03, message=BR-03 文案`
- [ ] **AC-03**：用户 B 调 API-02 关闭后，再次调 API-01 返回 `shouldShow=false`；数据库 `company_close_month_update_dismiss` 新增 1 行；重复调 API-02 不产生多行
- [ ] **AC-04**：SC-02 场景（QBO accept），record.submitter_user_id = null；所有用户（包括点 Accept 的那位）首次调 API-01 都返回 `shouldShow=true`
- [ ] **AC-05**：SC-01 同一用户连续 2 次保存使 close_month 推进 2 次（2026-03 → 2026-04），旧 dismiss 记录在第二次推进时全部被级联删除；之前已 dismiss 的用户 B 第二次调 API-01 重新返回 `shouldShow=true`
- [ ] **AC-06**：同月再次保存（close_month 仍为 2026-03），record 不变、dismiss 不清；已 dismiss 用户 shouldShow 仍为 false（BR-01/BR-06）
- [ ] **AC-07**：`recordCloseMonthUpdate` 内部抛异常时，`FinanceManualDataService.save()` 返回成功，日志含 error 栈（BR-08）
- [ ] **AC-08**：API-01 入参 companyId 不存在时返回 400；未登录时 401（由 Security 层给出）
- [ ] **AC-09**：`resolveCloseMonthDate` 返回 null 时触发点静默跳过，无新记录产生、无异常抛出

---

## 十三、待确认事项（已全部澄清，归档）

| # | 问题 | 结论 |
|---|------|------|
| Q-A | record 唯一性 | `UNIQUE(company_id)`，REPLACE 时先 DELETE 后 INSERT，FK 级联清 dismiss |
| Q-B | 提交人豁免 | 方案 1：record.submitter_user_id 字段 |
| Q-C | Dismiss 作用域 | 绑定 record.id，随 record 删除级联失效 |
| Q-D | 触发点 | Spring 事件 + @TransactionalEventListener(AFTER_COMMIT, fallbackExecution=true)；手动路径 = FinanceManualDataService.save；QBO 路径 = QuickbooksSyncService.processSync |
| Q-E | 权限 | 复用公司访问权限（上游兜底），本接口不增加新校验 |
| Q-F | 审计/清理 | 含 `source` 字段；dismiss 跟随 record 级联清理 |
| 文案 | BR-03 | 采用用户给定原文，后续 i18n/变量化另议 |
| 前端 | — | 本次交付**不含**前端代码 |
