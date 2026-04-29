# Monthly Benchmark Email 后端自测流程

> 模块：`fi/benchmarkemail/`
> 适用环境：dev / stage / uat（prod 会限制 DELETE API）
> 对接 API 文档见同目录 `monthly-benchmark-email-api.md`

---

## 0. 前置准备

### 0.1 数据库 DDL

应用 Sprint 110 的建表脚本（仅首次）：

```bash
psql "$DATABASE_URL" -f deploy/upgrade_doc/sprint109/V4_benchmark-email-tables.sql
```

验证 5 张表存在：

```sql
SELECT table_name FROM information_schema.tables
 WHERE table_name LIKE 'financial_benchmark_email_%';
-- 期望 5 行：
--   financial_benchmark_email_run
--   financial_benchmark_email_run_snapshot
--   financial_benchmark_email_baseline
--   financial_benchmark_email_baseline_history
--   financial_benchmark_email_send_log
```

### 0.2 测试账号 / 数据

准备以下数据（至少一组，用于跑通）：

| 需要 | SQL 验证 |
|---|---|
| ≥1 个 Active 公司 | `SELECT id, display_name FROM invite WHERE company_status='Active' LIMIT 5;` |
| 公司有 ≥1 个 CompanyAdmin（role_type=2 且 user.status!='4'） | 参考 `UserRepository.findAllCompanyAdmin` 的 SQL |
| 公司有 ≥1 个 Active 的 `r_company_group` 关联 | `SELECT company_id, company_group_id, status FROM r_company_group WHERE company_id='<ID>';` → status=0 |
| Portfolio 有 ≥1 个 PM（在 `r_portfolio_user`） | 参考 `UserRepository.findAllPortfolioManager` 的 SQL |
| 公司在 `financial_normalization_current` 有 ≥1 条 `data_type=0`（Actuals）月份 | `SELECT company_id, date, data_type FROM financial_normalization_current WHERE company_id='<ID>' AND data_type=0 ORDER BY date DESC LIMIT 5;` |

> **2026-04-29 修复**：以下 3 处行为已变化：
> 1. `DELETE /baselines` 现在返回真实 `deletedHistoryRows` 计数（之前永远 0）
> 2. `last_notified_at` 字段在 FIRE/FIRST_FIRE 时被写入（之前永远 NULL）
> 3. `silent_updated_count` / `first_fire_count` 不再因 PM portfolio fanout 翻倍

SendGrid 白名单（stage/uat）：确保测试邮箱在 `white_list_user` 表里，或用 `@qq.com` 结尾。

### 0.3 启动服务

```bash
cd CIOaas-api
set -a && source .env && set +a
mvn spring-boot:run -pl gstdev-cioaas-web
```

访问 `http://localhost:5213/web/swagger-ui/index.html`，确认 **Benchmark Email (Monthly)** 分组展示 7 个 API。

日志应出现：
- `BenchmarkEmailScheduleRegistrar` 被加载
- 当 cron 触发时会看到 `[benchmark-email] DAILY schedule fired`

### 0.4 获取管理员 Token

按项目现有 OAuth 流程登录，拿到 `Authorization: Bearer <token>`。后续 curl 全部带这个头。

---

## 1. 冒烟（Dry Run）— 验证无副作用

### 1.1 记录起点

```sql
SELECT COUNT(*) FROM financial_benchmark_email_run;                 -- 记为 R0
SELECT COUNT(*) FROM financial_benchmark_email_baseline;            -- 记为 B0
SELECT COUNT(*) FROM financial_benchmark_email_send_log;            -- 记为 L0
```

### 1.2 触发 dry run

```bash
curl -X POST http://localhost:5213/web/benchmark-email/runs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "phase": "DAILY",
    "dryRun": true,
    "targetCompanyIds": ["<COMPANY_ID>"]
  }'
```

记录 `data.runId` → `R_DRY`。

### 1.3 等待 3–10 秒后验证

```sql
-- run 应已 COMPLETED
SELECT id, status, admin_fired_count, pm_fired_count, silent_updated_count, first_fire_count
  FROM financial_benchmark_email_run WHERE id='<R_DRY>';
-- status=COMPLETED；counts 都应 = 0（dryRun 不写也不发）
```

```sql
-- baseline 总行数不应增加
SELECT COUNT(*) FROM financial_benchmark_email_baseline;            -- 应 = B0
-- send log 不应增加
SELECT COUNT(*) FROM financial_benchmark_email_send_log;            -- 应 = L0
-- 但 run_snapshot 会有数据用于调试
SELECT COUNT(*) FROM financial_benchmark_email_run_snapshot WHERE run_id='<R_DRY>';
-- 非 0（最多 2 角色 × 72 行 = 144 行）
```

### 1.4 API 查看明细

```bash
curl -s "http://localhost:5213/web/benchmark-email/runs/<R_DRY>?role=COMPANY_ADMIN" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.snapshots | length'
# 期望 ≤ 72
```

**通过条件**：`run.status=COMPLETED`，baseline / send_log 不变，run_snapshot 有数据。

---

## 2. 首封路径（FIRST_FIRE）

### 2.1 清空目标公司的 baseline

```bash
curl -X DELETE "http://localhost:5213/web/benchmark-email/baselines?companyId=<COMPANY_ID>&role=COMPANY_ADMIN&deleteHistory=true" \
  -H "Authorization: Bearer $TOKEN"
curl -X DELETE "http://localhost:5213/web/benchmark-email/baselines?companyId=<COMPANY_ID>&role=PORTFOLIO_MANAGER&deleteHistory=true" \
  -H "Authorization: Bearer $TOKEN"
```

### 2.2 MANUAL DAILY 触发

```bash
curl -X POST http://localhost:5213/web/benchmark-email/runs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "phase": "DAILY",
    "targetCompanyIds": ["<COMPANY_ID>"]
  }'
```

记录 `data.runId` → `R_FIRST`。

### 2.3 等待 10-30 秒后验证

**API 验证**：

```bash
curl -s "http://localhost:5213/web/benchmark-email/runs/<R_FIRST>" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.run'
```

期望：
- `status`：`COMPLETED`
- `firstFireCount`：≥ 1（每个角色独立计 1）
- `adminFiredCount`：≥ 1（至少 1 个 Admin 收件人）
- `pmFiredCount`：≥ 1（至少 1 个 PM 收件人；前提是 `r_company_group` 有关联）
- `silentUpdatedCount`：0（首封无 SILENT）

**SQL 验证**：

```sql
-- baseline 按 role 各 72 行 = 144 行
SELECT role, COUNT(*) FROM financial_benchmark_email_baseline
 WHERE company_id='<COMPANY_ID>' GROUP BY role;
-- 期望：COMPANY_ADMIN=72 / PORTFOLIO_MANAGER=72

-- 每行都有一条 history
SELECT role, COUNT(*) FROM financial_benchmark_email_baseline_history
 WHERE company_id='<COMPANY_ID>' AND run_id='<R_FIRST>' GROUP BY role;
-- 期望：COMPANY_ADMIN=72 / PORTFOLIO_MANAGER=72

-- send log SUCCESS
SELECT role, send_status, COUNT(*) FROM financial_benchmark_email_send_log
 WHERE run_id='<R_FIRST>' GROUP BY role, send_status;
-- 期望：全部 SUCCESS；若 FAILED 检查 error_message
```

**邮箱验证**：
- Admin 收件箱：标题 `Benchmarking Report for <companyName> — <Month YYYY>`；内容含 6 个指标卡，所有 Internal Peers 行**没有** "moved from"
- PM 收件箱：标题 `Your Benchmarking Summarized Report is Ready`；顶部 `Companies with Meaningful Benchmark Changes` 列表里有该公司；公司 section 展示全 6 指标，**没有** "moved from"

**通过条件**：以上 API / SQL / 邮件三方一致。

---

## 3. 正常路径（FIRE / SILENT）— 第二次触发

在 Step 2 之后立即（未改数据）再跑一次：

```bash
curl -X POST http://localhost:5213/web/benchmark-email/runs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"phase": "DAILY", "targetCompanyIds": ["<COMPANY_ID>"]}'
```

记录 `R_SECOND`。等待完成。

**期望**：
- `adminFiredCount` ≥ 1（Admin 必发，即便 delta=0）
- `pmFiredCount` = 0（所有组合 delta=0，不达阈值，SILENT）
- `silentUpdatedCount` ≥ 72（PM 静默更新）
- `firstFireCount` = 0（baseline 已存在）

**SQL 验证**：

```sql
-- Admin 相关 decision
SELECT decision, COUNT(*) FROM financial_benchmark_email_run_snapshot
 WHERE run_id='<R_SECOND>' AND role='COMPANY_ADMIN' GROUP BY decision;
-- 期望：FIRE=72

-- PM 相关 decision
SELECT decision, COUNT(*) FROM financial_benchmark_email_run_snapshot
 WHERE run_id='<R_SECOND>' AND role='PORTFOLIO_MANAGER' GROUP BY decision;
-- 期望：SILENT=72（若无数据变化）

-- history 不应增加（同值 upsert 跳过 history）
SELECT COUNT(*) FROM financial_benchmark_email_baseline_history
 WHERE run_id='<R_SECOND>';
-- 期望：0（全部与上次相同）
```

**邮件**：只有 Admin 一封，PM 无邮件；Admin 邮件里的百分位"moved from"数值应该等于当前值（delta=0）。

---

## 4. 阈值命中（PM FIRE）

### 4.1 人为改动一个指标数据

在 SQL 客户端选一个指标（如 ARR），修改该月的 Actuals 值使百分位移动 ≥ 5 点：

```sql
-- 查原值
SELECT arr, grossMargin, ruleOf40, monthlyNetBurnRate
  FROM financial_normalization_current
 WHERE company_id='<COMPANY_ID>' AND data_type=0
 ORDER BY date DESC LIMIT 1;

-- 备份后大幅改动（示例：把 Gross Margin 拉高 30%）
UPDATE financial_normalization_current
   SET gross_margin = gross_margin + 30
 WHERE company_id='<COMPANY_ID>' AND data_type=0
   AND date = (SELECT MAX(date) FROM financial_normalization_current
                WHERE company_id='<COMPANY_ID>' AND data_type=0);
```

（测试结束后记得回滚。）

### 4.2 再触发一次 DAILY

```bash
curl -X POST http://localhost:5213/web/benchmark-email/runs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"phase": "DAILY", "targetCompanyIds": ["<COMPANY_ID>"]}'
```

记录 `R_FIRE`。

### 4.3 验证

```sql
SELECT decision, COUNT(*) FROM financial_benchmark_email_run_snapshot
 WHERE run_id='<R_FIRE>' AND role='PORTFOLIO_MANAGER' GROUP BY decision;
-- 期望：FIRE 出现（至少 Gross Margin × Internal Peers × Actuals 行）

SELECT metric_id, benchmark_source, data_source, baseline_percentile, percentile, delta,
       row_change_type, contributes_to_email
  FROM financial_benchmark_email_run_snapshot
 WHERE run_id='<R_FIRE>' AND role='PORTFOLIO_MANAGER'
   AND metric_id='met-gross-margin' AND data_source='ACTUALS';
-- 期望：Internal Peers 行 row_change_type=MEANINGFUL_CHANGE，contributes_to_email=true
```

**邮件**：PM 收件箱新一封邮件，`Companies with Meaningful Benchmark Changes` 列有本公司，公司 section **只列 Gross Margin**（或其他达阈值的指标），每行含 "↑ (moved up from ...)" 或 "↓ (moved down from ...)"。

---

## 5. NA ↔ 值 变化

### 5.1 构造 NA→有值

```sql
-- 选一个 CF（data_type=1）从无到有的场景
-- 方法 A：原本 CF 无数据 → 新增一条
INSERT INTO financial_normalization_current (...) VALUES (...);

-- 或方法 B：目标公司本来没有 Committed Forecast，现在添加
```

### 5.2 触发 DAILY 看邮件

期望邮件中该指标的 Committed Forecast 行展示为首次出现的百分位（无 "moved from"；展示规则：`P63`、无箭头）。

### 5.3 构造值→NA

把前面的 CF 数据删除，再触发；期望展示 `N/A (previously Pxx)`。

---

## 6. MONTHLY_25TH 强制触发

```bash
curl -X POST http://localhost:5213/web/benchmark-email/runs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"phase": "MONTHLY_25TH", "targetCompanyIds": ["<COMPANY_ID>"]}'
```

### 验证

- Admin：必发（同 DAILY）
- PM：走阈值判定（同 DAILY）
- SQL：`SELECT phase FROM financial_benchmark_email_run WHERE id='<ID>';` = `MONTHLY_25TH`

---

## 7. SCHEDULED 幂等

### 7.1 模拟 cron 两次同日触发

需要调用 `createRun` 时显式传 `triggerType=SCHEDULED`。当前 API 只支持 MANUAL 触发，可直接观察真正的 cron 行为：

- 直接在 stage 等一天的 UTC 00:30 / 00:45
- **或**临时修改 `BenchmarkEmailScheduleRegistrar` 把 cron 改成近期时间，启动服务后手动让它跑两次（测完记得还原）

### 7.2 验证

```sql
-- 同一天 phase=DAILY 只应 1 条 SCHEDULED
SELECT COUNT(*) FROM financial_benchmark_email_run
 WHERE phase='DAILY' AND trigger_type='SCHEDULED' AND run_date=CURRENT_DATE;
-- 期望：1
```

---

## 8. 同一人身兼 Admin + PM

找一个既是 Company Admin 又是 Portfolio Manager 的用户，触发后验证该邮箱收到 **2 封** 邮件：
1. Admin 视角（本公司 6 指标固定）
2. PM 视角（portfolio 汇总）

```sql
SELECT role, subject, recipient_email FROM financial_benchmark_email_send_log s
  JOIN email e ON e.id = s.email_id
 WHERE s.recipient_email='<user_email>' AND s.run_id='<R_ID>';
-- 期望 2 行，subject 分别对应两种模板
```

---

## 9. 生产禁用 DELETE

在 prod 环境：

```bash
curl -X DELETE "http://<prod>/web/benchmark-email/baselines?companyId=X&role=COMPANY_ADMIN" \
  -H "Authorization: Bearer $TOKEN" -i | head -1
# 期望：HTTP/1.1 403 Forbidden
```

---

## 10. 失败场景验证

### 10.1 SendGrid 失败

临时把 `cio.email.sendgrid.apiKey` 改为无效值 → 触发 run → 观察：

```sql
SELECT send_status, sendgrid_status_code, error_message
  FROM financial_benchmark_email_send_log WHERE run_id='<R_ID>';
-- 期望：FAILED，error_message 有 SendGrid 错误
```

但 baseline **仍应入库**（事务解耦）：

```sql
SELECT COUNT(*) FROM financial_benchmark_email_baseline WHERE last_updated_run_id='<R_ID>';
-- > 0
```

### 10.2 cm_now 解析失败

选一个没有 `data_type=0` Actuals 行的公司触发：

```sql
-- run_snapshot 的 decision=ERROR，error_message='cm_now null (no Actuals)'
SELECT company_id, role, decision, error_message
  FROM financial_benchmark_email_run_snapshot
 WHERE run_id='<R_ID>' AND decision='ERROR';
```

---

## 11. 管理 API 全面覆盖

列表 / 查询 API：

```bash
# 列出最近 10 条 run
curl -s "http://localhost:5213/web/benchmark-email/runs?size=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.content[] | {id: .runId, phase, status}'

# 按 company+role 过滤 run 明细
curl -s "http://localhost:5213/web/benchmark-email/runs/<R_ID>?companyId=X&role=PORTFOLIO_MANAGER" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.snapshots | length'

# 查某收件人的历史
curl -s "http://localhost:5213/web/benchmark-email/sent-emails?recipientEmail=dev@test.com&size=20" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.content'

# 查 baseline（含最近 5 条 history）
curl -s "http://localhost:5213/web/benchmark-email/baselines?companyId=X&role=COMPANY_ADMIN" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.baselines[0]'
```

---

## 12. 回归 / 清理

测试完成后清理：

```sql
-- 删除本次测试产生的 run 和相关行
DELETE FROM financial_benchmark_email_send_log WHERE run_id IN ('<R_DRY>','<R_FIRST>','<R_SECOND>','<R_FIRE>','<R_ID>');
DELETE FROM financial_benchmark_email_baseline_history WHERE run_id IN ('<R_DRY>','<R_FIRST>','<R_SECOND>','<R_FIRE>','<R_ID>');
DELETE FROM financial_benchmark_email_run_snapshot WHERE run_id IN ('<R_DRY>','<R_FIRST>','<R_SECOND>','<R_FIRE>','<R_ID>');
DELETE FROM financial_benchmark_email_run WHERE id IN ('<R_DRY>','<R_FIRST>','<R_SECOND>','<R_FIRE>','<R_ID>');

-- 删除测试 baseline
DELETE FROM financial_benchmark_email_baseline WHERE company_id='<COMPANY_ID>';
DELETE FROM financial_benchmark_email_baseline_history WHERE company_id='<COMPANY_ID>';

-- 回滚人工改过的 normalization 数据（Step 4.1）
-- 按你当时备份的原值
```

---

## 通过标准 Checklist

| # | 场景 | 通过条件 |
|---|---|---|
| 1 | Dry run | status=COMPLETED，counts=0，baseline/send_log 不变 |
| 2 | 首封 FIRST_FIRE | baseline 2×72 行，history 2×72 行，Admin+PM 各收 1 封无 "moved from" |
| 3 | 第二次 FIRE/SILENT | Admin 必发，PM 静默（silent_updated_count≥72），history 不增加 |
| 4 | 阈值 FIRE | PM 邮件出现，只列达阈值指标，有 "moved from" |
| 5 | NA↔值 | 邮件展示 `N/A` / `previously Pxx` |
| 6 | MONTHLY_25TH | phase=MONTHLY_25TH，Admin/PM 行为同 DAILY |
| 7 | SCHEDULED 幂等 | 同日同 phase 只 1 条 SCHEDULED run |
| 8 | 兼职双角色 | 同邮箱收 2 封（Admin + PM） |
| 9 | Prod 禁用 DELETE | 403 |
| 10 | 失败不回滚 baseline | send_log FAILED，baseline 仍入库 |
| 11 | 管理 API | 所有过滤参数按预期生效 |

---

## 常见问题快查

| 症状 | 原因 | 查法 |
|---|---|---|
| 邮件没到但 run COMPLETED | SendGrid 白名单 / API key / 白名单邮箱 | `SELECT send_status, error_message FROM financial_benchmark_email_send_log WHERE run_id='<ID>'` |
| PM 全员 SILENT 但数据明明变了 | baseline 里的 closed_month 还没推进 | `SELECT closed_month FROM financial_benchmark_email_baseline WHERE company_id='X' AND role='PORTFOLIO_MANAGER' LIMIT 1;` vs 当前 `cm_now` |
| PM 没收邮件但 FIRE 有 | 公司在 `r_company_group` 没有 status=0 的 Active 归属 | `SELECT * FROM r_company_group WHERE company_id='X';` |
| cm_now null | 公司没有 Actuals 行 | `SELECT MAX(date) FROM financial_normalization_current WHERE company_id='X' AND data_type=0;` |
| 首封触发不了 | baseline 已存在 | `SELECT COUNT(*) FROM financial_benchmark_email_baseline WHERE company_id='X' AND role='Y';` → 0 才会 FIRST_FIRE |
| SCHEDULED 二次触发没拒绝 | 先前用 MANUAL 跑过 — MANUAL 不受幂等约束 | 按 `trigger_type` 单独过滤查询 |

---

## 单元测试（已提交，跑一次确认环境）

```bash
export JAVA_HOME="/c/Program Files/Java/jdk-17.0.2"
mvn -pl gstdev-cioaas-web test -Dtest='QuartileUtilTest,EmailDiffEvaluatorTest,EmailContentFormatterTest,MonthlyEmailSnapshotBuilderTest'
# 期望：Tests run: 27, Failures: 0, Errors: 0, Skipped: 0
```

覆盖：
- `QuartileUtil`：5 tests（分位边界 + 跨分位 + NA）
- `EmailDiffEvaluator`：9 tests（双 NA / 单 NA / Δ<5 / Δ=5 / Δ>5 / 跨 Q / Actuals vs Forecast）
- `EmailContentFormatter`：12 tests（精确 / 插值 / 边界 marker / NA / 首封 / 移动方向 / 历史回归 NA）
- `MonthlyEmailSnapshotBuilder`：1 smoke test

纯单元层面无 DB 依赖。DB 相关的行为靠上面的手工自测流程覆盖。
