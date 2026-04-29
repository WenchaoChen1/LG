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

---

## 2. Self-Test 接口

| 端点 | 用途 |
|------|------|
| `POST /benchmark/notify-alerts/test/seed` | 落一条具体 type 的 alert，覆盖同 key 已有行 |
| `POST /benchmark/notify-alerts/test/seed-pair` | 一次造一对（外部更新 + 位置变化）alert |
| `DELETE /benchmark/notify-alerts/test/clear?userId=...` | 清掉某用户全部 alert |

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

### 5.3 验证 2.2 触发分支

需要造一些数据让 `DiffEvaluator` 走不同分支。手动 SQL 修 baseline 表，再调 rerun-first-time（用 force=true）模拟。

| 场景 | 操作 | 期望 trigger_reason |
|------|-----|-----|
| 首次 | baseline 表清空，跑 rerun | `INITIAL_FIRE` |
| 平台↔同行切换 | UPDATE baseline.benchmark_source 改另一个值，跑月度 | `SOURCE_FLIPPED` |
| 值不变 + peer 变 + Δ≥10 | 改某 peer 公司同月 actuals，跑月度 | `PEER_DRIVEN_SHIFT` |
| 值变 + peer 变 + Δ≥10 | 改自己同月 actuals + peer，跑月度 | `VALUE_AND_PEER_SHIFT` |
| 新 closed_month | 新月份 actuals 入库，跑月度 | `SILENT_NEW_MONTH` |
| 数据修订 + 未达阈值 | 改自己同月 actuals 但小幅，跑月度 | `SILENT_REVISED` |

```sql
-- 验证决策落在 snapshot 表
SELECT company_id, metric_id, diff_decision, diff_delta, created_at
FROM financial_benchmark_position_run_snapshot
WHERE run_id = '<最新 runId>'
ORDER BY company_id, metric_id;
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
| **CL1** | 清理 | clear?userId | 行数 > 0，再 GET 返回空 |

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
