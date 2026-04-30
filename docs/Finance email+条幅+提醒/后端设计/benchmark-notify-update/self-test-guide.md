# Benchmark 通知 - 自测流程指南

> 覆盖需求 `Notify Users When Benchmark Reference Data Is Updated_需求文档.md` 的 2.1 外部基准更新 + 2.2 内部位置变化两个工作流。
> **配套 Self-Test 接口**：`/benchmark/notify-alerts/test/*` —— 见 § 2

---

## 0. 端 / 角色 / 横幅类型 总览

### 0.1 两个 Portal

| Portal | URL（示例） | 谁登 |
|--------|------------|------|
| **管理端**（Admin portal） | `https://admin-test.lgpi.io/` | Portfolio Manager（PM）、Group Manager / Admin（拥有 `seeAllPortfolio` 菜单权限） |
| **公司端**（Company portal） | `https://app-test.lgpi.io/` | Company Admin、Company User |

### 0.2 横幅 5 种 notifyType

| Code | 枚举名 | 出现位置 | 谁能看到 |
|------|--------|---------|---------|
| **1** | `ENTRY_UPDATE_COMPANY` | 公司端 - company benchmarking tab | Company Admin + Company User |
| **2** | `ENTRY_UPDATE_PORTFOLIO_ADMIN` | 管理端 - portfolio benchmarking tab | PM + Admin |
| **3** | `POSITION_UPDATE_COMPANY` | 公司端 - company benchmarking tab | **仅 Company Admin** |
| **4** | `POSITION_UPDATE_PORTFOLIO_ADMIN` | 管理端 - portfolio benchmarking tab | PM + Admin |
| **5** | `POSITION_UPDATE_PORTFOLIO_COMPANY` | **管理端 - company benchmarking tab**（admin/PM 看具体公司） | PM + Admin |

### 0.3 角色 × 工作流 × 横幅 矩阵

| 角色 | 2.1 外部更新 | 2.2 位置变化 |
|------|------------|------------|
| **PM** | 邮件 ✓<br>type=2（管理端 portfolio tab） | 邮件 ✓<br>type=4（管理端 portfolio tab）<br>type=5（管理端 company tab） |
| **Admin / Group Manager** | 邮件 ✗<br>type=2（管理端 portfolio tab） | 邮件 ✗<br>type=4（管理端 portfolio tab）<br>type=5（管理端 company tab） |
| **Company Admin** | 邮件 ✓（多公司多封）<br>type=1（公司端 company tab） | 邮件 ✓<br>type=3（公司端 company tab） |
| **Company User** | 邮件 ✗<br>type=1（公司端 company tab） | 邮件 ✗<br>**横幅 ✗**（需求只点 Company Admin） |

---

### 0.4 10 分钟快速冒烟

如果只想快速确认整条链路通：

```bash
# 1. 启动服务（启动钩子异步触发首次补发）
mvn spring-boot:run -pl gstdev-cioaas-web

# 2. 等启动日志出现 "Benchmark Position first-time catchup completed"

# 3. 检查首次补发是否生效
psql -c "SELECT trigger_reason, COUNT(*) FROM financial_benchmark_position_baseline GROUP BY trigger_reason;"
# 期望：INITIAL_FIRE 行数 = 合格公司数 × ≤6 指标

# 4. 检查邮件触发
psql -c "SELECT email_type, COUNT(*) FROM email WHERE created_at > NOW() - INTERVAL '5 minutes' GROUP BY email_type;"
# 期望：BENCHMARK_POSITION_UPDATE 行数 > 0

# 5. 用 Company Admin 身份拉横幅
curl "$HOST/benchmark/notify-alerts?userId=$U_COMPANY_ADMIN&companyId=$COMPANY_ID" -H "Authorization: Bearer $TOKEN"
# 期望：data 数组里有 type=3 行

# 6. 自测端点造一对横幅，验证前端能拉到
curl -X POST "$HOST/benchmark/notify-alerts/test/seed-pair?userId=$U_COMPANY_ADMIN&companyId=$COMPANY_ID" -H "Authorization: Bearer $TOKEN"
curl "$HOST/benchmark/notify-alerts?userId=$U_COMPANY_ADMIN&companyId=$COMPANY_ID" -H "Authorization: Bearer $TOKEN"
# 期望：data 数组 2 条（type=1 + type=3）

# 通过即可进入完整自测；不通过先看 § 7 排错
```

---

## 1. 前置准备

### 1.1 启动服务

```bash
cd CIOaas-api
set -a && source .env && set +a
mvn spring-boot:run -pl gstdev-cioaas-web
```

观察日志：
```
Benchmark Position first-time catchup scheduling, eventTime=...
... (异步)
Benchmark Position first-time catchup completed
```

### 1.2 准备测试账号

```sql
-- Company portal 用户
SELECT u.user_id, u.email, u.role_type, u.company_id, c.company_name
FROM "user" u
JOIN company c ON c.company_id = u.company_id
WHERE u.is_deleted = FALSE AND u.status != 4
  AND u.role_type IN ('2', '4')   -- 2=Company Admin, 4=Company User
LIMIT 10;

-- Portfolio Manager（无 seeAllPortfolio）
SELECT u.user_id, u.email, pu.company_group_id, cg.name AS portfolio_name
FROM "user" u
JOIN r_user_role ur ON ur.user_id = u.user_id
JOIN role r ON r.id = ur.role_id
JOIN r_portfolio_user pu ON pu.user_id = u.user_id
JOIN company_group cg ON cg.company_group_id = pu.company_group_id
WHERE u.is_deleted = FALSE AND u.status != 4
  AND r.is_deleted = FALSE
  AND r.role_type = 'organization'
  AND NOT EXISTS (
    SELECT 1 FROM r_role_menu rm
    JOIN menu m ON m.id = rm.menu_id
    WHERE m.code = 'seeAllPortfolio' AND r.id = rm.role_id
  )
LIMIT 5;

-- Admin / Group Manager（拥有 seeAllPortfolio 菜单权限）
SELECT DISTINCT u.user_id, u.email
FROM "user" u
JOIN r_user_role ur ON ur.user_id = u.user_id
JOIN r_role_menu rm ON rm.role_id = ur.role_id
JOIN menu m ON m.id = rm.menu_id
WHERE m.code = 'seeAllPortfolio' AND u.is_deleted = FALSE AND u.status != 4
LIMIT 3;
```

记下 5 个测试身份：

| 简称 | userId | 关键关联 |
|------|--------|---------|
| `U_COMPANY_ADMIN` | `<复制>` | + `companyId = <复制>` |
| `U_COMPANY_USER` | `<复制>` | + `companyId = <复制>` |
| `U_PM` | `<复制>` | + 至少一个 `groupId = <复制>` |
| `U_ADMIN` | `<复制>` | 有 seeAllPortfolio |
| `TOKEN` | `<浏览器 dev tools 拷贝>` | Bearer token |

约定：

```bash
HOST=http://localhost:5213/web
TOKEN="<bearer>"
```

### 1.3 一键重置脚本

自测频繁切换场景时，用这段 SQL 清干净状态（不需要重启服务）：

```sql
BEGIN;
-- 清掉所有 baseline / run / snapshot / alert / 邮件流水（按需选删）
TRUNCATE financial_benchmark_position_baseline;
TRUNCATE financial_benchmark_position_run_snapshot;
TRUNCATE financial_benchmark_position_run;
TRUNCATE financial_benchmark_notify_alert;

-- 可选：把测试期间发的邮件流水也清掉
DELETE FROM email
WHERE email_type IN ('BENCHMARK_POSITION_UPDATE', 'BENCHMARK_ENTRY_UPDATE')
  AND created_at > NOW() - INTERVAL '1 day';
COMMIT;
```

清完之后调一次：
```bash
curl -X POST "$HOST/benchmark/position-monitor/rerun-first-time" -H "Authorization: Bearer $TOKEN"
```
就回到了"全新数据库"状态，可重新开测。

---

## 2. Self-Test 接口

| 端点 | 用途 |
|------|------|
| `POST /benchmark/notify-alerts/test/seed` | 落一条具体 type 的 alert，覆盖同 key 已有行 |
| `POST /benchmark/notify-alerts/test/seed-pair` | 一次造一对（外部更新 + 位置变化）alert |
| `DELETE /benchmark/notify-alerts/test/clear?userId=...` | 清掉某用户全部 alert |
| `POST /benchmark/notify-alerts/test/trigger-monthly` | **手动跑一次月度任务**（Phase 1 SNAPSHOT + Phase 2 DIFF），返回新 runId。免去等 25 号 cron。 |

### 2.1 `/seed` 参数

| Param | 必填 | 说明 |
|-------|------|------|
| `userId` | ✓ | 目标用户 |
| `companyId` 或 `companyGroupId` | 二选一 | 公司视角传前者；portfolio 视角传后者 |
| `notifyType` | ✓ | 1 / 2 / 3 / 4 / 5 |
| `content` | 否 | 不传时按 type 自动填默认值（type=1/2 → "KeyBanc — 2026"，其它空字符串） |

### 2.2 `/seed-pair` 参数

| Param | 必填 | 说明 |
|-------|------|------|
| `userId` | ✓ | |
| `companyId` 或 `companyGroupId` | 二选一 | 决定造的是公司端的 (1, 3) 还是管理端的 (2, 4) |
| `entryContent` | 否 | 默认 `"KeyBanc — 2026, HighAlpha — 2027"` |

**注意**：`/seed-pair` 只覆盖经典的 4 种类型。type=5（管理端 company tab）需要显式调 `/seed?notifyType=5&companyId=X`。

---

## 3. 标准联调流程

### 流程 A — 公司端用户（Company Admin）

```bash
# Step 1：造 2.1 + 2.2 横幅
curl -X POST "$HOST/benchmark/notify-alerts/test/seed-pair?userId=$U_COMPANY_ADMIN&companyId=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"

# Step 2：以 Company Admin 身份登录公司端，进入 company benchmarking tab
# Step 3：前端调
curl "$HOST/benchmark/notify-alerts?userId=$U_COMPANY_ADMIN&companyId=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
# → 数组 2 条：notifyType=1 + notifyType=3
```

期望前端展示：
- type=1 横幅文案：`New benchmark data available. ... (KeyBanc — 2026, HighAlpha — 2027).`
- type=3 横幅文案：`Benchmark positioning updated. ...`

### 流程 B — 公司端用户（Company User）—— 验证 2.2 排除

```bash
# 给 Company User 造 type=1（应该有）+ type=3（按需求**不应该有**，但通过 self-test 强造一条）
curl -X POST "$HOST/benchmark/notify-alerts/test/seed?userId=$U_COMPANY_USER&companyId=$COMPANY_ID&notifyType=1" \
  -H "Authorization: Bearer $TOKEN"

# 拉接口：应该看到 type=1
curl "$HOST/benchmark/notify-alerts?userId=$U_COMPANY_USER&companyId=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**真实业务**中 Company User **不会**收到 type=3——因为 `PositionNotifier` 的 type=3 只写给 `companyAdmins`。这条规则需要通过端到端流程验证（见 § 5.2）。

### 流程 C — 管理端 Portfolio Manager

```bash
# Portfolio 视角：造 2.1 + 2.2 portfolio tab 横幅
curl -X POST "$HOST/benchmark/notify-alerts/test/seed-pair?userId=$U_PM&companyGroupId=$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN"

# 拉 portfolio tab 接口
curl "$HOST/benchmark/notify-alerts?userId=$U_PM&companyGroupId=$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN"
# → 数组 2 条：type=2 + type=4
```

```bash
# Company tab：手工造一条 type=5（admin/PM 在管理端看具体公司时显示）
curl -X POST "$HOST/benchmark/notify-alerts/test/seed?userId=$U_PM&companyId=$COMPANY_ID&notifyType=5" \
  -H "Authorization: Bearer $TOKEN"

# 验证 PM 进具体公司的 company benchmarking tab 时能看到
curl "$HOST/benchmark/notify-alerts?userId=$U_PM&companyId=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
# 期望：数组 1 条（type=5）— 前提是 COMPANY_ID 在 PM 的某个 portfolio 下，G3 才放行
```

### 流程 D — 管理端 Admin / Group Manager

```bash
# Portfolio 视角
curl -X POST "$HOST/benchmark/notify-alerts/test/seed-pair?userId=$U_ADMIN&companyGroupId=$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN"

# Admin 也能看 type=5（即使他不在 r_portfolio_user 里——seeAllPortfolio 短路放行）
curl -X POST "$HOST/benchmark/notify-alerts/test/seed?userId=$U_ADMIN&companyId=$COMPANY_ID&notifyType=5" \
  -H "Authorization: Bearer $TOKEN"

# 拉 portfolio tab
curl "$HOST/benchmark/notify-alerts?userId=$U_ADMIN&companyGroupId=$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN"
# → 2 条 (type=2 + type=4)

# 拉 company tab
curl "$HOST/benchmark/notify-alerts?userId=$U_ADMIN&companyId=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
# → 1 条 (type=5)
```

### 流程 E — 关闭横幅独立性

PM 或 Admin 在 portfolio tab dismiss type=4：

```bash
curl -X DELETE "$HOST/benchmark/notify-alerts/dismiss/<type=4 的 id>" \
  -H "Authorization: Bearer $TOKEN"
```

切到 company tab 拉接口：

```bash
curl "$HOST/benchmark/notify-alerts?userId=$U_PM&companyId=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
# → 仍能看到 type=5（关闭一个 tab 的横幅不影响另一个 tab）
```

### 流程 F — 清理

```bash
curl -X DELETE "$HOST/benchmark/notify-alerts/test/clear?userId=$U_COMPANY_ADMIN" -H "Authorization: Bearer $TOKEN"
curl -X DELETE "$HOST/benchmark/notify-alerts/test/clear?userId=$U_COMPANY_USER"  -H "Authorization: Bearer $TOKEN"
curl -X DELETE "$HOST/benchmark/notify-alerts/test/clear?userId=$U_PM"            -H "Authorization: Bearer $TOKEN"
curl -X DELETE "$HOST/benchmark/notify-alerts/test/clear?userId=$U_ADMIN"         -H "Authorization: Bearer $TOKEN"
```

---

## 4. G3 权限失效场景

### 4.1 Portfolio 失权

PM 原管理 P，模拟移除：

```sql
DELETE FROM r_portfolio_user WHERE user_id = '$U_PM' AND company_group_id = '$GROUP_ID';
```

```bash
# PM 拉 portfolio tab → 期望空数组（type=2/4 行被 G3 过滤）
curl "$HOST/benchmark/notify-alerts?userId=$U_PM&companyGroupId=$GROUP_ID" \
  -H "Authorization: Bearer $TOKEN"

# PM 拉 company tab → 期望空数组（type=5 也被 G3 过滤——失去 portfolio 间接路径）
curl "$HOST/benchmark/notify-alerts?userId=$U_PM&companyId=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
```

恢复：
```sql
INSERT INTO r_portfolio_user (user_id, company_group_id) VALUES ('$U_PM', '$GROUP_ID');
```

### 4.2 Company 失权

Company Admin user.company_id 字段被改成别的：

```sql
UPDATE "user" SET company_id = 'other-company-id' WHERE user_id = '$U_COMPANY_ADMIN';
```

```bash
curl "$HOST/benchmark/notify-alerts?userId=$U_COMPANY_ADMIN&companyId=$ORIGINAL_COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
# → 空数组（type=1/3 行被 G3 过滤）
```

### 4.3 Admin 跨边界看一切（验证短路）

Admin 即使没在 r_portfolio_user 里和某 portfolio 关联，也能看到该 portfolio 的横幅：

```bash
# 给 Admin 造一个他没绑定的 portfolio 的横幅
curl -X POST "$HOST/benchmark/notify-alerts/test/seed?userId=$U_ADMIN&companyGroupId=$ORPHAN_GROUP_ID&notifyType=4" \
  -H "Authorization: Bearer $TOKEN"

# 拉接口
curl "$HOST/benchmark/notify-alerts?userId=$U_ADMIN&companyGroupId=$ORPHAN_GROUP_ID" \
  -H "Authorization: Bearer $TOKEN"
# → 1 条（admin 短路放行）
```

---

## 5. 真实业务流验证（不依赖 self-test 接口）

### 5.1 验证 2.1 真实触发链路

用 admin 账号在 Benchmark Entry 页面**新增全新 platform-edition**（如 KeyBanc-2099），保存。

```sql
-- 横幅
SELECT user_id, notify_type, content, created_at
FROM financial_benchmark_notify_alert
WHERE notify_type IN (1, 2)
ORDER BY created_at DESC LIMIT 20;
-- 期望：每个 admin/PM 一条 type=2；每个 companyAdmin/companyUser 一条 type=1

-- 邮件
SELECT subject, receiver_email, email_type, created_at
FROM email
WHERE email_type = 'BENCHMARK_ENTRY_UPDATE'
ORDER BY created_at DESC LIMIT 20;
-- 期望：标题 "New Benchmark Survey Update"；收件人为 PM + Company Admin
-- 邮件正文检查：包含 "for {orgDisplay}" 段（公司名 / portfolio 名）
```

### 5.2 验证 2.2 真实触发链路

启动时已自动触发；也可手动调：

```bash
curl -X POST "$HOST/benchmark/position-monitor/rerun-first-time" \
  -H "Authorization: Bearer $TOKEN"
```

```sql
-- 基线
SELECT company_id, metric_id, trigger_reason, notified, created_at
FROM financial_benchmark_position_baseline
ORDER BY created_at DESC LIMIT 30;
-- 首次跑全部应是 INITIAL_FIRE，notified=true

-- 横幅
SELECT user_id, notify_type, company_id, company_group_id, created_at
FROM financial_benchmark_notify_alert
WHERE notify_type IN (3, 4, 5)
ORDER BY created_at DESC LIMIT 30;
-- 期望分布：
--   type=3 → 仅 companyAdmin（不含 companyUser）
--   type=4 → PM + Admin × 各自 portfolio
--   type=5 → PM + Admin × 该 portfolio 下每个 fire 的公司

-- 邮件
SELECT subject, receiver_email, email_type, created_at
FROM email
WHERE email_type = 'BENCHMARK_POSITION_UPDATE'
ORDER BY created_at DESC LIMIT 20;
-- 标题 "Update to Benchmark Positioning"
-- 收件人为 PM + Company Admin（Admin / Company User 都不在）
```

### 5.3 验证 2.2 触发分支 → 邮件链路（端到端）

`DiffEvaluator` 6 种 decision，其中 4 种 fire 邮件、2 种 silent。下面给每种场景一份**可执行 recipe**（SQL 准备 → 触发 → 三表验证）。

**通用准备**：先有一次完整跑批的 baseline + run + snapshot 数据：

```bash
# 如果是全新数据库，先建 baseline
curl -X POST "$HOST/benchmark/position-monitor/rerun-first-time" -H "Authorization: Bearer $TOKEN"

# 然后手动跑一次月度，得到 run + snapshot
curl -X POST "$HOST/benchmark/notify-alerts/test/trigger-monthly" -H "Authorization: Bearer $TOKEN"
# 返回 { "data": "<RUN_ID>", ... } —— 记下 RUN_ID
```

挑一个测试用 (company, metric)：
```sql
SELECT company_id, metric_id, percentile, benchmark_source, own_value
FROM financial_benchmark_position_baseline
ORDER BY created_at DESC LIMIT 5;
```
任选一行，记下 `companyId` 和 `metricId`，下面用 `$C_TEST` / `$M_TEST` 代指。

---

#### Recipe 5.3.A：`INITIAL_FIRE`（fire 邮件）

**条件**：baseline 不存在 + 能算出 percentile（peer 集合非空）。

```sql
-- 1. 删除该 (company, metric) 的所有 baseline 行
DELETE FROM financial_benchmark_position_baseline
WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST';

-- 2. 记下 trigger 前 email 表当前最大 created_at（基线时间）
SELECT MAX(created_at) FROM email WHERE email_type = 'BENCHMARK_POSITION_UPDATE';
```

```bash
# 3. 触发月度跑批（会重新建 baseline + 跑 diff）
curl -X POST "$HOST/benchmark/notify-alerts/test/trigger-monthly" -H "Authorization: Bearer $TOKEN"
# 返回新 runId，记下为 $RID
```

```sql
-- 4. snapshot 表的 decision 应该是 INITIAL_FIRE
SELECT diff_decision, diff_delta, percentile, benchmark_source
FROM financial_benchmark_position_run_snapshot
WHERE run_id = '$RID' AND company_id = '$C_TEST' AND metric_id = '$M_TEST';
-- 期望：diff_decision = 'INITIAL_FIRE', diff_delta = NULL

-- 5. baseline 表新增了一行
SELECT trigger_reason, notified, created_at
FROM financial_benchmark_position_baseline
WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
ORDER BY created_at DESC LIMIT 3;
-- 期望：trigger_reason = 'INITIAL_FIRE', notified = true

-- 6. email 表新增邮件
SELECT subject, receiver_email, created_at FROM email
WHERE email_type = 'BENCHMARK_POSITION_UPDATE'
  AND created_at > '<步骤 2 记的 baseline 时间>'
ORDER BY created_at DESC;
-- 期望：标题 "Update to Benchmark Positioning"，收件人含该公司 Company Admin + 管该公司 portfolio 的 PM

-- 7. alert 表新增横幅（每个 fire 公司 → admins/PM 写 type=4 + type=5；该公司 Company Admin 写 type=3）
SELECT user_id, notify_type, company_id, company_group_id, created_at FROM financial_benchmark_notify_alert
WHERE created_at > '<步骤 2 记的 baseline 时间>'
ORDER BY created_at DESC LIMIT 30;
```

---

#### Recipe 5.3.B：`SOURCE_FLIPPED`（fire 邮件）

**条件**：baseline.benchmark_source ≠ snapshot.benchmark_source（PLATFORM ↔ PEER 切换）。

`rerun-diff` 在重跑 Phase 2 时，会拿当前最新 baseline 与 snapshot 做对比。所以**篡改 baseline 让它和 snapshot 不一致**就能触发对应分支。

```sql
-- 1. 看下当前 baseline 和 snapshot 的 benchmark_source
SELECT 'baseline' AS src, percentile, benchmark_source FROM financial_benchmark_position_baseline
WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
ORDER BY created_at DESC LIMIT 1
UNION ALL
SELECT 'snapshot', percentile, benchmark_source FROM financial_benchmark_position_run_snapshot
WHERE run_id = '$RID' AND company_id = '$C_TEST' AND metric_id = '$M_TEST';

-- 2. 把 baseline 的 benchmark_source 改成相反值
-- 假设当前 snapshot.benchmark_source = 'PEER'，把 baseline 改成 'PLATFORM'
UPDATE financial_benchmark_position_baseline
SET benchmark_source = 'PLATFORM'  -- 或 'PEER'，按上面查出的 snapshot 取相反值
WHERE id = (
  SELECT id FROM financial_benchmark_position_baseline
  WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
  ORDER BY created_at DESC LIMIT 1
);

-- 3. 记 baseline email 时间
SELECT MAX(created_at) AS t FROM email WHERE email_type = 'BENCHMARK_POSITION_UPDATE';
```

```bash
# 4. 重跑 Phase 2 决策（不需要 trigger-monthly，因为 snapshot 没变）
curl -X POST "$HOST/benchmark/position-monitor/rerun-diff/$RID" -H "Authorization: Bearer $TOKEN"
```

```sql
-- 5. 验证 decision、新 baseline 行、新邮件、新横幅（同 5.3.A 步骤 4-7）
-- 期望：snapshot.diff_decision = 'SOURCE_FLIPPED'
--       baseline 多一行，trigger_reason = 'SOURCE_FLIPPED', notified = true
--       email 表多一批 BENCHMARK_POSITION_UPDATE
```

---

#### Recipe 5.3.C：`PEER_DRIVEN_SHIFT`（fire 邮件）

**条件**：own_value 不变 + peer_snapshot 变了 + |Δpercentile| ≥ 10。

```sql
-- 1. 篡改 baseline：percentile 改到与 snapshot 相差 ≥10，own_value 保持原值，peer_snapshot 改成不同 JSON
UPDATE financial_benchmark_position_baseline
SET
  percentile = (
    SELECT CASE WHEN s.percentile >= 60 THEN s.percentile - 20 ELSE s.percentile + 20 END
    FROM financial_benchmark_position_run_snapshot s
    WHERE s.run_id = '$RID' AND s.company_id = '$C_TEST' AND s.metric_id = '$M_TEST'
  ),
  -- own_value 保持当前 baseline 自己的值（不变 → ownChanged=false）
  -- 改 peer_snapshot 成"假装变过"的内容
  peer_snapshot = '[{"companyId":"FAKE_PEER_FOR_TEST","value":99.99}]'
WHERE id = (
  SELECT id FROM financial_benchmark_position_baseline
  WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
  ORDER BY created_at DESC LIMIT 1
);

-- 2. 确保 baseline.own_value = snapshot.own_value（防止误判 VALUE_AND_PEER_SHIFT）
UPDATE financial_benchmark_position_baseline
SET own_value = (
  SELECT own_value FROM financial_benchmark_position_run_snapshot
  WHERE run_id = '$RID' AND company_id = '$C_TEST' AND metric_id = '$M_TEST'
)
WHERE id = (
  SELECT id FROM financial_benchmark_position_baseline
  WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
  ORDER BY created_at DESC LIMIT 1
);

SELECT MAX(created_at) AS t FROM email WHERE email_type = 'BENCHMARK_POSITION_UPDATE';
```

```bash
curl -X POST "$HOST/benchmark/position-monitor/rerun-diff/$RID" -H "Authorization: Bearer $TOKEN"
```

```sql
-- 验证：snapshot.diff_decision = 'PEER_DRIVEN_SHIFT'，diff_delta ≥ 10，新 baseline + 邮件 + 横幅
```

---

#### Recipe 5.3.D：`VALUE_AND_PEER_SHIFT`（fire 邮件）

**条件**：own_value 变 + peer_snapshot 变 + |Δpercentile| ≥ 10。

```sql
-- 同 5.3.C，但 own_value 也改成不同的值（任意非 snapshot.own_value 的数）
UPDATE financial_benchmark_position_baseline
SET
  percentile = (
    SELECT CASE WHEN s.percentile >= 60 THEN s.percentile - 20 ELSE s.percentile + 20 END
    FROM financial_benchmark_position_run_snapshot s
    WHERE s.run_id = '$RID' AND s.company_id = '$C_TEST' AND s.metric_id = '$M_TEST'
  ),
  own_value = COALESCE(own_value, 0) + 999999,  -- 强制 own_value 不同
  peer_snapshot = '[{"companyId":"FAKE_PEER_FOR_TEST","value":99.99}]'
WHERE id = (
  SELECT id FROM financial_benchmark_position_baseline
  WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
  ORDER BY created_at DESC LIMIT 1
);
```

```bash
curl -X POST "$HOST/benchmark/position-monitor/rerun-diff/$RID" -H "Authorization: Bearer $TOKEN"
```

期望：`diff_decision = 'VALUE_AND_PEER_SHIFT'`，新 baseline + 邮件 + 横幅。

---

#### Recipe 5.3.E：`SILENT_NEW_MONTH`（不发邮件）

**条件**：baseline.closed_month < snapshot.closed_month。

```sql
UPDATE financial_benchmark_position_baseline
SET closed_month = closed_month - INTERVAL '1 month'
WHERE id = (
  SELECT id FROM financial_benchmark_position_baseline
  WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
  ORDER BY created_at DESC LIMIT 1
);

SELECT MAX(created_at) AS t FROM email WHERE email_type = 'BENCHMARK_POSITION_UPDATE';
```

```bash
curl -X POST "$HOST/benchmark/position-monitor/rerun-diff/$RID" -H "Authorization: Bearer $TOKEN"
```

期望：
- `diff_decision = 'SILENT_NEW_MONTH'`
- 新 baseline 行写入，但 `notified = false`
- **email 表无新增**
- alert 表无新增

---

#### Recipe 5.3.F：`SILENT_REVISED`（不发邮件）

**条件**：own_value 变了 + peer_snapshot **没变** + 不满足任何 fire 条件。

```sql
-- own_value 改成不同值；peer_snapshot 保持和 snapshot 一致；percentile 也保持小幅差异（< 10 或不变）
UPDATE financial_benchmark_position_baseline
SET
  own_value = COALESCE(own_value, 0) + 100,
  peer_snapshot = (
    SELECT peer_snapshot FROM financial_benchmark_position_run_snapshot
    WHERE run_id = '$RID' AND company_id = '$C_TEST' AND metric_id = '$M_TEST'
  )
WHERE id = (
  SELECT id FROM financial_benchmark_position_baseline
  WHERE company_id = '$C_TEST' AND metric_id = '$M_TEST'
  ORDER BY created_at DESC LIMIT 1
);
```

```bash
curl -X POST "$HOST/benchmark/position-monitor/rerun-diff/$RID" -H "Authorization: Bearer $TOKEN"
```

期望：`diff_decision = 'SILENT_REVISED'`，新 baseline 行 `notified = false`，**email 表无新增**。

---

#### 一键查看本轮 run 的所有 decision 分布

```sql
SELECT diff_decision, COUNT(*) FROM financial_benchmark_position_run_snapshot
WHERE run_id = '$RID' GROUP BY diff_decision ORDER BY COUNT(*) DESC;
```

### 5.4 验证 closed_month 推导

```sql
-- 找一个 Manual 公司（financial_setting 里 mode='Manual'）
SELECT company_id FROM company_quickbooks WHERE mode = 'Manual' LIMIT 5;

-- 看它最后一个有 actuals 的月份
SELECT date FROM financial_normalization_current
WHERE company_id = '<companyId>' AND data_type = 0
ORDER BY date DESC LIMIT 5;
```

启动 catchup 后看 baseline.closed_month 是否等于上面查到的最大月份。

Automatic 公司：根据当前日期是否过 15 号，期望 closed_month = 上月 / 上上月（往前回溯到第一个有 actuals 的月份）。

### 5.5 验证排除条件

```sql
-- Exited / Shut down 公司不在 baseline 表
SELECT b.* FROM financial_benchmark_position_baseline b
JOIN company c ON c.company_id = b.company_id
WHERE c.company_status IN (1, 6);
-- 期望：0 行

-- 未绑定 portfolio 的公司不在 baseline 表
SELECT b.* FROM financial_benchmark_position_baseline b
LEFT JOIN r_company_group rcg ON rcg.company_id = b.company_id AND rcg.status = 0
WHERE rcg.company_id IS NULL;
-- 期望：0 行
```

### 5.6 验证 rerun-diff 重发

```bash
RUN_ID=<最近 runId>
curl -X POST "$HOST/benchmark/position-monitor/rerun-diff/$RUN_ID" \
  -H "Authorization: Bearer $TOKEN"
```

```sql
-- snapshot 的 diff_decision 重新填充
SELECT diff_decision, COUNT(*) FROM financial_benchmark_position_run_snapshot
WHERE run_id = '<RUN_ID>' GROUP BY diff_decision;

-- email 表多了一批新行
SELECT COUNT(*) FROM email WHERE email_type = 'BENCHMARK_POSITION_UPDATE'
AND created_at > NOW() - INTERVAL '5 minutes';
```

---

### 5.7 验证邮件细节（收件人粒度 + 正文）

#### 5.7.1 收件人对照矩阵

触发 2.1（前端新增 KeyBanc-2099）或 2.2（trigger-monthly）后，执行：

```sql
-- 同一封邮件应只对应一个 receiver_email
SELECT receiver_email, COUNT(*) AS n
FROM email
WHERE email_type IN ('BENCHMARK_ENTRY_UPDATE', 'BENCHMARK_POSITION_UPDATE')
  AND created_at > NOW() - INTERVAL '10 minutes'
GROUP BY receiver_email
ORDER BY n DESC;
```

**期望分布**：

| 收件人角色 | 应该收到几封 | 验证 |
|----------|-----------|------|
| Company Admin 管 N 家公司 | N 封（每家一封）| 同一邮箱出现 N 次 |
| PM 在 1 个组织管 M 个 portfolio | 1 封 | 同一邮箱出现 1 次 |
| PM 在 K 个组织各管若干 portfolio | K 封 | 同一邮箱出现 K 次 |
| Admin / Group Manager | **0 封**（不发邮件）| 不应出现 |
| Company User | **0 封**（不发邮件）| 不应出现 |

```sql
-- 反向验证：管理员（有 seeAllPortfolio）不应收到邮件
SELECT u.email FROM email e
JOIN "user" u ON u.email = e.receiver_email
JOIN r_user_role ur ON ur.user_id = u.user_id
JOIN r_role_menu rm ON rm.role_id = ur.role_id
JOIN menu m ON m.id = rm.menu_id
WHERE m.code = 'seeAllPortfolio'
  AND e.email_type IN ('BENCHMARK_ENTRY_UPDATE', 'BENCHMARK_POSITION_UPDATE')
  AND e.created_at > NOW() - INTERVAL '10 minutes';
-- 期望：0 行
```

#### 5.7.2 验证 2.1 邮件正文含 `for {orgDisplay}` 段

新增一个全新 platform-edition 后，**手动检查邮件 HTML 内容**（看 SendGrid 控制台或本地 SMTP debug 服务器）：

- Company Admin 邮件应包含：`benchmark comparisons **for Acme Inc.** now reflect the latest survey year`
- PM（管单 portfolio）应包含：`benchmark comparisons **for Apex Fund** now reflect ...`
- PM（管同组织多 portfolio）应包含：`benchmark comparisons **for Apex Fund / Beta Fund** now reflect ...`（用 ` / ` 分隔）

如果项目有邮件 HTML 落表保留，可以这样查：

```sql
-- 假设 email 表有 content / html 字段（按项目实际字段名）
SELECT receiver_email, content
FROM email
WHERE email_type = 'BENCHMARK_ENTRY_UPDATE'
ORDER BY created_at DESC LIMIT 5;
-- grep "for " 关键字
```

---

### 5.8 验证 2.1 多 platform-edition 合并到同一横幅

需求：多个平台版本同时有更新，应合并到**同一横幅**，content 用 `, ` 分隔。

```sql
-- 触发前看现状
SELECT user_id, content FROM financial_benchmark_notify_alert
WHERE notify_type IN (1, 2) ORDER BY user_id LIMIT 5;
```

```bash
# 步骤 1：依次新增 2 个全新 platform-edition（前端或 API）
# 第 1 个：KeyBanc-2099
# 第 2 个：HighAlpha-2099
# 间隔几秒确保异步线程不冲突
```

```sql
-- 步骤 2：验证每个用户的同 (user, scope, type) 行 content 已合并
SELECT user_id, notify_type, content, updated_at
FROM financial_benchmark_notify_alert
WHERE notify_type IN (1, 2)
  AND updated_at > NOW() - INTERVAL '5 minutes'
ORDER BY user_id;
-- 期望：同一行 content 类似 "KeyBanc — 2099, HighAlpha — 2099"，没有重复出现两行

-- 反向验证：同 (user, scope, type) 不应出现 2 条独立行
SELECT user_id, company_id, company_group_id, notify_type, COUNT(*) AS n
FROM financial_benchmark_notify_alert
WHERE notify_type IN (1, 2)
GROUP BY user_id, company_id, company_group_id, notify_type
HAVING COUNT(*) > 1;
-- 期望：0 行
```

**冪等验证**：再触发一次同样的 KeyBanc-2099（同样 platform-edition），content **不应重复追加** —— `mergeAlertContent` 检测 `existing.contains(newEntry)` 后跳过。

---

### 5.9 验证 AWS EventBridge cron 注册

启动后第一次跑了 `initFixedScheduler()`，会把 `BenchmarkPositionMonitor` 推到 AWS EventBridge。验证：

#### 9a. 看启动日志
```
Fixed schedule created: BenchmarkPositionMonitor   ← 第一次启动
Fixed schedule synced: BenchmarkPositionMonitor    ← 后续启动
```

#### 9b. 看 schedule_config 表

```sql
SELECT schedule_name, schedule_type, source_type, schedule_expression, deleted, last_execution_time
FROM schedule_config
WHERE schedule_name LIKE '%BenchmarkPositionMonitor%';
-- 期望：1 行；schedule_expression = 'cron(0 6 25 * ? *)'；deleted=false
```

#### 9c. 看 AWS Console（如有访问权限）

EventBridge → Schedules，找名字带 `BenchmarkPositionMonitor` 的项目，确认：
- State: ENABLED
- Cron: `0 6 25 * ? *`
- Target: 项目用的 SQS 队列 ARN

---

### 5.10 边界场景

#### 10a. peer 集合空 → 跳过该 (company, metric)

某些公司可能算不出 peer（或 peer 数据全空）。`FirstTimeDecider` 会判 `SKIP_NO_DATA`：

```sql
-- 找出哪些 (company, metric) 跳过了
SELECT company_id, metric_id, error_message
FROM financial_benchmark_position_run_snapshot
WHERE run_id = '<RID>' AND diff_decision = 'SKIP_NO_DATA';
```

期望：这些行的 `peer_snapshot` 为空字符串或 `[]`，**baseline 表不应有对应新行**（FirstTimeDecider 不写 baseline）。

#### 10b. closed_month 推导失败 → 跳过该公司全部指标

Manual 公司若没有任何 actuals 数据，`ClosedMonthResolver.resolve` 返回 null。`runMonthlyCheck` 在 Phase 1 给该公司 6 个 metric 都写一行 snapshot 但 `error_message="closed_month 推导失败"`：

```sql
SELECT company_id, COUNT(*) AS skip_count
FROM financial_benchmark_position_run_snapshot
WHERE run_id = '<RID>'
  AND error_message LIKE 'closed_month%'
GROUP BY company_id;
```

#### 10c. 单 metric 算 percentile 异常但其他正常

修改某 peer 公司的 `financial_normalization_current.arr_growth_rate` 为非数字字符串（强制异常）。re-run，验证：
- 该公司其他 5 个 metric 正常
- 仅 ARR_GROWTH_RATE 这一行 `error_message` 非空
- 其他 5 个 metric 走正常 decision 流程

```sql
SELECT metric_id, diff_decision, error_message
FROM financial_benchmark_position_run_snapshot
WHERE run_id = '<RID>' AND company_id = '<被破坏的 company>'
ORDER BY metric_id;
```

#### 10d. percentile 算出来是 null

发生在 ownValue=null 或 peerValues 全 null 的情况：
```sql
SELECT company_id, metric_id, percentile, own_value, peer_snapshot
FROM financial_benchmark_position_run_snapshot
WHERE run_id = '<RID>' AND percentile IS NULL;
```
期望：这些行 `diff_decision = 'SKIP_NO_DATA'`，无 baseline / 邮件 / 横幅触发。

---

### 5.11 关键日志检查点

启动 + 月度跑批应能在日志里看到这些行（grep 用）：

| 阶段 | 日志关键字 | 期望出现位置 |
|------|----------|------------|
| 启动 schedule 同步 | `Fixed schedule created/synced: BenchmarkPositionMonitor` | 启动后 30s 内 |
| 启动首次补发开始 | `Benchmark Position first-time catchup scheduling` | ApplicationReadyEvent 后 |
| 启动首次补发完成 | `Benchmark Position first-time catchup completed` | 异步完成后 |
| 启动首次补发失败 | `Benchmark Position first-time catchup failed` | 异常时（应 0 次）|
| Phase 1 单公司失败 | `Phase 1 failure companyId=... metricId=...` | 单条数据异常时 |
| closed_month 推导失败 | `resolve closed_month failed: <companyId>` | Manual 公司无 actuals |
| snapshot 构建失败 | `snapshot build failed cid=... mid=...` | percentile 路径异常 |
| 邮件发送失败 | `Send position-update email failed` 或 `Send email failed:` | SendGrid 异常 |
| 邮件类型 | 落 email 表的 email_type 字段 | `BENCHMARK_POSITION_UPDATE` / `BENCHMARK_ENTRY_UPDATE` |

错误状态聚合查询：
```sql
-- 全表错误
SELECT error_message, COUNT(*) FROM financial_benchmark_position_run_snapshot
WHERE error_message IS NOT NULL GROUP BY error_message;

-- 该 run 的整体状态
SELECT phase, company_count, fired_count, silent_count, error_message
FROM financial_benchmark_position_run
WHERE id = '<RID>';
-- 期望：phase = 'COMPLETED'，error_message = NULL
```

---

## 6. 端到端测试矩阵（更新版）

| # | 场景 | 步骤 | 期望 |
|---|------|------|------|
| **C1** | Company Admin 公司端拿全部 | seed-pair (companyId) → GET company tab | 数组 2 条 (1+3) |
| **C2** | Company User 公司端 — 仅 2.1 | 真实触发 2.1 → C-User 拉 GET | 仅 1 条 (type=1)；type=3 不写 |
| **C3** | Company Admin dismiss type=3 后再拉 | seed → dismiss → GET | 数组只剩 type=1 |
| **P1** | PM 管理端 portfolio tab | seed-pair (groupId) → GET portfolio tab | 数组 2 条 (2+4) |
| **P2** | PM 管理端 company tab — 含 type=5 | seed type=5 + GET company tab | 数组 1 条 (type=5) |
| **A1** | Admin 跨 portfolio | seed (admin × ORPHAN_GROUP) → GET | 1 条（admin 短路放行） |
| **A2** | Admin 看任何公司 type=5 | seed type=5 (admin × any companyId) → GET | 1 条 |
| **G1** | PM 失去 portfolio 绑定 | DELETE r_portfolio_user → GET | 空数组 |
| **G2** | Company Admin user.company_id 改了 | UPDATE → GET | 空数组 |
| **G3** | PM 通过 portfolio 间接访问 company | seed type=5 (PM × COMPANY_ID, COMPANY_ID 在 PM 的 portfolio 下) → GET | 1 条（走 portfolio 路径放行）|
| **V1** | 缺 scope 参数 | GET 不带 companyId / companyGroupId | 400 |
| **V2** | 单 type 过滤 | GET 加 notifyType=4 | 仅 type=4 |
| **E1** | 真实 2.1 触发 | 前端新增 platform-edition | 邮件 + 横幅按角色矩阵分发 |
| **E2** | 真实 2.2 触发 | 启动 / rerun-first-time | 邮件 + 横幅按角色矩阵分发 + baseline 表行 |
| **E3** | 真实 2.2 邮件正文 | 5.1 SQL 检查 email 表 | 含 "for {orgDisplay}"（PM 列出多 portfolio，Company Admin 列出公司名） |
| **E4** | 2.2 Company User 不收 | 5.2 SQL 检查 alert 表 | 没有 user_id=companyUser AND notify_type=3 的行 |
| **E5** | 2.2 Admin 收 type=5 | 5.2 SQL 检查 alert 表 | 有 user_id=admin AND notify_type=5 的行（每 fired 公司一条） |
| **R1** | rerun-diff | 调接口 | snapshot diff_decision 重写 + 邮件重发 |
| **F1** | INITIAL_FIRE 端到端 | § 5.3.A | snapshot=INITIAL_FIRE + baseline 新行 + email + alert |
| **F2** | SOURCE_FLIPPED 端到端 | § 5.3.B | snapshot=SOURCE_FLIPPED + email + alert |
| **F3** | PEER_DRIVEN_SHIFT 端到端 | § 5.3.C | snapshot=PEER_DRIVEN_SHIFT + Δp≥10 + email + alert |
| **F4** | VALUE_AND_PEER_SHIFT 端到端 | § 5.3.D | snapshot=VALUE_AND_PEER_SHIFT + email + alert |
| **F5** | SILENT_NEW_MONTH 静默 | § 5.3.E | snapshot=SILENT_NEW_MONTH + baseline 新行 notified=false + **无新邮件** |
| **F6** | SILENT_REVISED 静默 | § 5.3.F | snapshot=SILENT_REVISED + baseline 新行 notified=false + **无新邮件** |
| **M1** | 多 platform-edition 合并 | § 5.8 | 同 (user, scope, type) 仅一行，content 用 `, ` 拼 |
| **M2** | 重复 edition 不重复追加 | § 5.8 末段 | 第二次触发同 platform-edition 后 content 不变 |
| **S1** | scheduler 注册 | § 5.9 启动日志 + schedule_config | 1 行 deleted=false 的 BenchmarkPositionMonitor |
| **B1** | peer 集合空 | § 5.10a | snapshot=SKIP_NO_DATA，无 baseline/邮件/横幅 |
| **B2** | closed_month 算不出 | § 5.10b | snapshot.error_message 非空，跳过 |
| **B3** | 单 metric 异常不影响其他 | § 5.10c | 仅异常 metric 行 error_message，其他正常决策 |
| **B4** | percentile = null | § 5.10d | snapshot=SKIP_NO_DATA |
| **L1** | 关键日志齐全 | § 5.11 grep | 启动/异步/失败 4 类日志按需出现 |
| **EM1** | 收件人粒度（每公司一封 / 每组织一封） | § 5.7.1 | 同邮箱出现次数符合表格 |
| **EM2** | Admin / Company User 不收邮件 | § 5.7.1 反向查询 | 0 行 |
| **EM3** | 2.1 邮件正文含 `for {orgDisplay}` | § 5.7.2 | 邮件 HTML 含 `for Acme Inc.` 等 |
| **CL1** | 清理 | clear?userId 或 § 1.3 重置脚本 | 行数 > 0，再 GET 返回空 |

---

## 7. 排错速查

| 现象 | 排查 |
|------|------|
| `/seed-pair` 200 但 GET 拿不到 | G3 拦截：检查 PM 是否在 r_portfolio_user 里；admin 检查是否真的有 seeAllPortfolio 菜单（用 `findAllAdminWithPortfolio` SQL 验证） |
| Admin 看不到 type=4/5 | 确认该 admin 在 `findAllAdminUserWithPortfolio` 返回里；该方法是 role_type=1 CROSS JOIN ALL portfolios，所以应该都能看到 |
| Company User 看到了 type=3 | 是手工造的还是真实触发？真实触发不会写给 companyUser；如果真实触发写了，是 bug——查 PositionNotifier.notify 的 type=3 分支是否漏掉了 companyUsers 排除逻辑 |
| 邮件发了 admin | 是 bug——查 PositionNotifier.notify 的邮件分支，不应该包含 admin 列表 |
| PM 一次月度 run 收到多封同内容邮件 | 检查 `pmGroups` groupBy 维度，应该是 `(userId, parentId)`，不是 portfolioId |
| baseline 表有 Exited 公司 | 检查 `findActiveCompaniesInAnyPortfolio` SQL，确认 `company_status NOT IN (1, 6)` |
| 跨月没触发 SILENT_NEW_MONTH | 检查 baseline.closed_month 是否真的在 snapshot.closed_month 之前；DiffEvaluator 用 isBefore 判断 |

---

## 8. 已知非关键冗余

`getAllAdminWithPortfolio` SQL 是 `role_type=1 CROSS JOIN ALL company_group`——把 PM 也包进来了 × 全部 portfolio。`PositionNotifier` 写横幅时 PM 既走 `portfolioManagers` 路径又走 `admins` 路径，会写一些 PM 不管理的 portfolio 的 type=4/5 行，**但 G3 在读时按 r_portfolio_user 过滤掉**——前端永远看正确。代价是 alert 表多写若干行（量级与 PM 数 × 全部 portfolio 数成正比）。

要彻底清理：新增"纯 group manager"（剔除 PM）查询方法，PositionNotifier 用它替换 admins 集合。当前先不做，标记为后续优化。

---

## 9. 上线前

- `/benchmark/notify-alerts/test/*` 自测接口在生产环境**应评估屏蔽**：可加 `@Profile("dev,test")` 注解，或路径白名单 / 单独鉴权。
- 真实业务路径（启动 catchup、月度 cron、save 合并）保持原幂等语义。
