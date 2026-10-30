# 卡死任务定时清扫 — 代码示例

> 关联文档: [开发设计](./dev-design-doc.md) · [Fireflies 代码示例第 4 节（人工应急）](../../Fireflies%20转录接入/开发设计/code-examples.md)

## 1. 扫描与认领 SQL

时限按开发设计第 3 节；每类 `LIMIT 200`，按卡住时间升序。扫描只读，逐项处理时再用「认领 / 条件更新」核对凭证，0 行即已被别人处理、跳过。

### 1.1 Fireflies

```sql
-- F1 首轮卡在处理中（EXTRACTING 走作废；IDENTIFYING 走不调大模型的识别收尾）
SELECT meeting_id, processing_stage, processing_started_at, extraction_started_at
FROM ai_ff_meeting_state
WHERE processing_stage <> 'DONE'
  AND processing_started_at < now() - interval '120 minutes'
ORDER BY processing_started_at
LIMIT 200;

-- F1 卡在 IDENTIFYING：先认领凭证（即 claim_processing），0 行跳过；之后的最终事务核对 :new_started_at
UPDATE ai_ff_meeting_state
SET processing_started_at = :new_started_at, updated_by = '1'
WHERE meeting_id = :meeting_id
  AND processing_stage = 'IDENTIFYING'
  AND processing_started_at = :scanned_processing_started_at;

-- F3 非首轮提取卡在 RUNNING（收尾复用 _persist_void，凭证由它核对）
SELECT meeting_id, extraction_trigger, extraction_started_at
FROM ai_ff_meeting_state
WHERE extraction_status = 'RUNNING'
  AND processing_stage = 'DONE'
  AND extraction_started_at < now() - interval '120 minutes'
ORDER BY extraction_started_at
LIMIT 200;

-- F4 证词补抽卡在 RUNNING
SELECT meeting_id, id AS participant_id, updated_at
FROM ai_ff_meeting_participant
WHERE testimony_backfill_status = 'RUNNING'
  AND updated_at < now() - interval '120 minutes'
ORDER BY updated_at
LIMIT 200;

-- F4 收尾（先锁 P1 行，再更新参会人行）
UPDATE ai_ff_meeting_participant
SET testimony_backfill_status = 'FAILED', updated_by = '1'
WHERE id = :participant_id
  AND testimony_backfill_status = 'RUNNING'
  AND updated_at = :scanned_updated_at;

-- F5 投影卡在 PENDING（走 idx_ai_ff_routing_row_projection）
SELECT id AS row_id, meeting_id, destination, output_type, company_id, updated_at
FROM ai_ff_routing_row
WHERE projection_status = 'PENDING'
  AND updated_at < now() - interval '60 minutes'
ORDER BY updated_at
LIMIT 200;

-- F5 认领：触发器无条件把 updated_at 刷成 now()，既是多实例认领，也让下一轮不再捡到
UPDATE ai_ff_routing_row
SET updated_by = '1'
WHERE id = :row_id
  AND projection_status = 'PENDING'
  AND updated_at = :scanned_updated_at;

-- F6(一) 已删 / 未授权、下线重试用尽（收尾调 project_rows_offline，不按 file_id 直接删）
SELECT id AS row_id, meeting_id, destination, output_type, company_id, file_id
FROM ai_ff_routing_row
WHERE projection_status = 'FAILED'
  AND file_id IS NOT NULL
  AND (deleted OR NOT authorized)
  AND updated_at < now() - interval '60 minutes'
ORDER BY updated_at
LIMIT 200;

-- F6(二)(三) 不被任何 P7 行引用的 Fireflies 登记行（收尾调 delete_entries_by_file_id，返回 0 再软删登记行）
SELECT r.file_id, r.business_type, r.organization_id, r.created_at
FROM ai_file_registry r
WHERE r.business_type IN ('FIREFLIES', 'FIREFLIES_TESTIMONY', 'FIREFLIES_CROSS_COMPANY')
  AND NOT r.deleted
  AND r.created_at < now() - interval '60 minutes'
  AND NOT EXISTS (SELECT 1 FROM ai_ff_routing_row w WHERE w.file_id = r.file_id)
ORDER BY r.created_at
LIMIT 200;
```

### 1.2 Fireflies F2（Java）

```sql
-- 前置：fireflies-meeting-queue 的 ApproximateNumberOfMessages + ApproximateNumberOfMessagesNotVisible = 0，
-- 否则本轮跳过 F2（积压中的消息还没轮到）
SELECT m.id, m.organization_id, m.fireflies_id, m.dispatched_at
FROM ff_meeting_meta_info m
WHERE m.dispatched_at < now() - interval '30 minutes'
  AND m.redispatched_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM ai_ff_meeting_state s WHERE s.meeting_id = m.id)
  -- 组织未删：按 FfSyncServiceImpl 现有的租户过滤口径
ORDER BY m.dispatched_at
LIMIT 200;

-- 认领后才发送：1 行 = 本实例发；0 行 = 已被别的实例处理
UPDATE ff_meeting_meta_info
SET dispatched_at = now(), redispatched_at = now()
WHERE id = :id
  AND dispatched_at = :scanned_dispatched_at
  AND redispatched_at IS NULL;
```

### 1.3 AI 财务提取

```sql
-- E1（走任务表已有部分索引 (status, updated_at) WHERE status NOT IN 终态；进程活着时心跳每 120 秒刷新 updated_at）
SELECT id AS task_id, status, updated_at
FROM ai_financial_extraction_task
WHERE NOT deleted
  AND status = 'PROCESSING'
  AND updated_at < now() - interval '15 minutes'
ORDER BY updated_at
LIMIT 200;

-- 收尾第 1 步：锁行复核，0 行即跳过
SELECT id FROM ai_financial_extraction_task
WHERE id = :task_id AND status = :scanned_status AND updated_at = :scanned_updated_at
FOR UPDATE;

-- 心跳刷新存活信号（每 120 秒，随消息心跳）
UPDATE ai_financial_extraction_task
SET updated_at = now()
WHERE id = :task_id AND status = 'PROCESSING';

-- 上线前用生产 state_log 校准正常耗时（分位数，单位分钟）
SELECT percentile_cont(ARRAY[0.5, 0.9, 0.99]) WITHIN GROUP (ORDER BY m), max(m)
FROM (
  SELECT extract(epoch FROM e.created_at - s.created_at) / 60 AS m
  FROM ai_financial_extraction_task_state_log s
  JOIN LATERAL (
    SELECT created_at FROM ai_financial_extraction_task_state_log e
    WHERE e.task_id = s.task_id AND e.created_at > s.created_at
      AND e.event_type IN ('EXTRACTION_COMPLETED', 'EXTRACTION_FAILED', 'ERROR')
    ORDER BY created_at LIMIT 1
  ) e ON true
  WHERE s.event_type = 'EXTRACTION_STARTED'
) t;
```

## 2. DDL

并入 Fireflies 的两份建表脚本（开发设计第 6 节）。已经跑过旧版脚本的库（各人本地）单独执行下面的语句即可，全部幂等。

### 2.1 Java `deploy/upgrade_doc/sprint122/V1__ff_init.sql`

```sql
-- 脚本里是建表语句中的一列；已建好表的库用 ALTER 补
ALTER TABLE ff_meeting_meta_info ADD COLUMN IF NOT EXISTS redispatched_at timestamptz;
COMMENT ON COLUMN ff_meeting_meta_info.redispatched_at IS
  'Time the stuck-task sweep re-sent this meeting to Python; non-null means the one allowed resend is used';
```

### 2.2 Python `sql/migrations/business/V034__sprint122_fireflies_init.sql`

```sql
CREATE INDEX IF NOT EXISTS idx_ai_ff_meeting_state_first_run_stuck
    ON ai_ff_meeting_state (processing_started_at) WHERE processing_stage <> 'DONE';
CREATE INDEX IF NOT EXISTS idx_ai_ff_meeting_state_extraction_running
    ON ai_ff_meeting_state (extraction_started_at) WHERE extraction_status = 'RUNNING';
CREATE INDEX IF NOT EXISTS idx_ai_ff_meeting_participant_backfill_running
    ON ai_ff_meeting_participant (updated_at) WHERE testimony_backfill_status = 'RUNNING';
CREATE INDEX IF NOT EXISTS idx_ai_file_registry_fireflies_created
    ON ai_file_registry (created_at)
    WHERE NOT deleted AND business_type IN ('FIREFLIES', 'FIREFLIES_TESTIMONY', 'FIREFLIES_CROSS_COMPANY');
```

## 3. 消息与手动触发

```jsonc
// Java → Python，stuck-task-sweep-queue（无业务字段）
{"messageType": "StuckTaskSweep", "queueName": "stuck-task-sweep-queue", "sendTime": "2026-10-30 08:15:00", "uuid": "…"}
```

```bash
# test 环境走整条链路（Java 先做 F2，再投清扫消息）
aws sqs send-message --queue-url <lg-non-prod-test-scheduler-queue 的 URL> \
  --message-body '{"messageType":"Scheduler","schedulerType":"StuckTaskSweep"}'

# 只测 Python（本地用自己的 SQS_NAME_PREFIX）
aws sqs send-message --queue-url <前缀>stuck-task-sweep-queue 的 URL \
  --message-body '{"messageType":"StuckTaskSweep","queueName":"stuck-task-sweep-queue","sendTime":"2026-10-30 08:15:00","uuid":"manual-1"}'
```
