# Monthly Benchmark Email 5 步自测 cheatsheet

> 完整流程见 `monthly-benchmark-email-selftest.md`，本文档是日常反复跑的快捷版。
> 需要：`<COMPANY_ID>`、有 Active Admin、Active PM 关联、当前月有 Actuals 数据。

```bash
export TOKEN="<your_admin_bearer>"
export BASE="http://localhost:5213/web"
export COMPANY_ID="<company_id>"
```

---

## Step 1：复位（让该公司回到 FIRST_FIRE 状态）

```bash
curl -X DELETE "$BASE/benchmark-email/baselines?companyId=$COMPANY_ID&role=COMPANY_ADMIN&deleteHistory=true" -H "Authorization: Bearer $TOKEN"
curl -X DELETE "$BASE/benchmark-email/baselines?companyId=$COMPANY_ID&role=PORTFOLIO_MANAGER&deleteHistory=true" -H "Authorization: Bearer $TOKEN"
```

✅ 预期：每条返回 `{deletedBaselineRows: 72, deletedHistoryRows: <非0>}`（首次跑可能 0/0）。
> 2026-04-29 修复：之前 `deletedHistoryRows` 一直是 0，现在会返回真实计数。

---

## Step 2：诊断 + 预览邮件（不发不写）

```bash
curl -X POST "$BASE/benchmark-email/preview" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"companyId\":\"$COMPANY_ID\",\"role\":\"COMPANY_ADMIN\"}" | jq .data
```

✅ 预期 `data.diagnostic`：
- `closedMonth`：能解析出的最近 closed month（**null 说明公司没有 Actuals**）
- `eventType`：`FIRST_FIRE`（因为 step 1 清空了 baseline）
- `expectedDecision`：`FIRST_FIRE`
- `recipientCount` ≥ 1，`recipientEmails` 含真实 Admin
- `data.html`：完整邮件 HTML（可保存为文件浏览器打开看效果）

```bash
curl -X POST "$BASE/benchmark-email/preview" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"companyId\":\"$COMPANY_ID\",\"role\":\"COMPANY_ADMIN\"}" | jq -r '.data.html' > /tmp/preview.html
open /tmp/preview.html  # mac；Windows 用 start
```

---

## Step 3：发到测试邮箱（可选，只走 SendGrid 不写 baseline）

```bash
curl -X POST "$BASE/benchmark-email/preview" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{
    \"companyId\":\"$COMPANY_ID\",
    \"role\":\"COMPANY_ADMIN\",
    \"sendTo\":\"dev-me@whalesongproduct.com\"
  }" | jq .data
```

✅ 预期 `data.sendStatus = "SUCCESS"`（stage/uat 注意收件人需在白名单）。

---

## Step 4：真跑一次完整 run（写 baseline + 真发）

```bash
RUN_ID=$(curl -s -X POST "$BASE/benchmark-email/runs" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"phase\":\"DAILY\",\"targetCompanyIds\":[\"$COMPANY_ID\"]}" | jq -r '.data.runId')
echo "RUN_ID=$RUN_ID"
sleep 15
```

```bash
# 总览
curl -s "$BASE/benchmark-email/runs/$RUN_ID" -H "Authorization: Bearer $TOKEN" | jq '.data.run'
```

✅ 预期：
- `firstFireCount=2`（Admin + PM 各一；2026-04-29 修复后多 portfolio 公司也只计 1 次/角色）
- `adminFiredCount ≥ 1`，`pmFiredCount ≥ 1`
- `silentUpdatedCount=0`（首封无静默）
- `status=COMPLETED`

```sql
-- 验证 last_notified_at 已写入（2026-04-29 修复）
SELECT role, last_updated_reason, last_notified_at
  FROM financial_benchmark_email_baseline
 WHERE company_id='<COMPANY_ID>' LIMIT 5;
-- 期望：last_notified_at 非 null（因为首封是 FIRE 类）
```

```bash
# 邮件投递结果
curl -s "$BASE/benchmark-email/sent-emails?companyId=$COMPANY_ID&size=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.content[] | {role, recipient_email: .recipientEmail, send_status: .sendStatus, error: .errorMessage}'
```

---

## Step 5：第二次跑（验证 Admin 必发 + PM 静默）

```bash
RUN_ID2=$(curl -s -X POST "$BASE/benchmark-email/runs" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"phase\":\"DAILY\",\"targetCompanyIds\":[\"$COMPANY_ID\"]}" | jq -r '.data.runId')
sleep 15
curl -s "$BASE/benchmark-email/runs/$RUN_ID2" -H "Authorization: Bearer $TOKEN" | jq '.data.run'
```

✅ 预期：
- `adminFiredCount ≥ 1`（Admin 仍必发）
- `pmFiredCount=0`（数据没变 → 全部 SILENT）
- `silentUpdatedCount`：每个 (公司, 角色) 计 1 次（2026-04-29 修复前会被 PM portfolio fanout 重复累加）
- `firstFireCount=0`

```sql
-- 验证 last_notified_at 在 SILENT 时不更新（2026-04-29 修复）
SELECT role, last_updated_reason, last_notified_at
  FROM financial_benchmark_email_baseline
 WHERE company_id='<COMPANY_ID>'
   AND role='PORTFOLIO_MANAGER'
 LIMIT 5;
-- 期望：last_updated_reason='SILENT_NO_CHANGE'，last_notified_at 仍是 step 4 的旧时刻（不被覆盖）
```

---

## 故障速查

| 现象 | 检查 |
|---|---|
| Step 2 `closedMonth=null` | 公司没有 Actuals，先确认 `financial_normalization_current` 有 `data_type=0` 的数据 |
| Step 2 `recipientCount=0` | `findAllCompanyAdmin` 找不到 → 检查用户表 role 关联（必须有名为 'Company Admin' 的角色） |
| Step 2 `eventType=DATA_REVISION` 但你期望 `NEW_CLOSED_MONTH` | baseline.closed_month 还停在当前月；查 `SELECT MAX(closed_month) FROM financial_benchmark_email_baseline WHERE company_id='X' AND role='Y';` |
| Step 3 sendStatus=FAILED | 看 `errorMessage`：常见 SendGrid 白名单 / Key 错 |
| Step 4 `adminFiredCount=0` 但 `firstFireCount>0` | 看 `sent-emails?status=FAILED`，找投递失败原因 |
| Step 4 `pmFiredCount=0` 即便 FIRST_FIRE | 检查 `r_company_group` 是否有 `status=0` 的关联 |

---

## 一键脚本（save as `selftest.sh`）

```bash
#!/usr/bin/env bash
set -e
COMPANY_ID="${1:?usage: $0 <COMPANY_ID> [TOKEN]}"
TOKEN="${2:-$TOKEN}"
BASE="${BASE:-http://localhost:5213/web}"

echo "[1/5] resetting baseline..."
curl -s -X DELETE "$BASE/benchmark-email/baselines?companyId=$COMPANY_ID&role=COMPANY_ADMIN&deleteHistory=true" -H "Authorization: Bearer $TOKEN" >/dev/null
curl -s -X DELETE "$BASE/benchmark-email/baselines?companyId=$COMPANY_ID&role=PORTFOLIO_MANAGER&deleteHistory=true" -H "Authorization: Bearer $TOKEN" >/dev/null

echo "[2/5] preview admin email..."
curl -s -X POST "$BASE/benchmark-email/preview" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"companyId\":\"$COMPANY_ID\",\"role\":\"COMPANY_ADMIN\"}" | jq '.data.diagnostic'

echo "[3/5] triggering full DAILY run..."
RUN_ID=$(curl -s -X POST "$BASE/benchmark-email/runs" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"phase\":\"DAILY\",\"targetCompanyIds\":[\"$COMPANY_ID\"]}" | jq -r '.data.runId')
echo "  RUN_ID=$RUN_ID"
echo "  waiting 20s for async run to complete..."
sleep 20

echo "[4/5] run summary:"
curl -s "$BASE/benchmark-email/runs/$RUN_ID" -H "Authorization: Bearer $TOKEN" | jq '.data.run'

echo "[5/5] send log:"
curl -s "$BASE/benchmark-email/sent-emails?companyId=$COMPANY_ID" -H "Authorization: Bearer $TOKEN" | jq '.data.content[] | {role, recipient_email: .recipientEmail, status: .sendStatus, error: .errorMessage}'
```

Usage: `./selftest.sh <COMPANY_ID> $TOKEN`
