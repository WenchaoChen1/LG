# 卡死任务定时清扫 — 开发设计

> 关联文档: [Fireflies 开发设计](../../Fireflies%20转录接入/开发设计/dev-design-doc.md)（P1「卡死兜底」、7 #Q12 #Q13 #Q30）· [Fireflies 代码示例第 4 节](../../Fireflies%20转录接入/开发设计/code-examples.md) · [智能解析系统架构](../../智能解析/调研/system-architecture.md) · [代码示例（SQL / DDL / 消息）](./code-examples.md)
>
> **本文范围**：定时扫出卡死的 Fireflies 会议处理与 AI 财务提取任务并收尾。与 Fireflies 一起上线（Fireflies 7 #Q12）。第 7 节各项已于 2026-10-30 拍板。

## 1. 范围

### 1.1 清扫接手的情况

被打断（进程被杀、发版 30 秒关停、OOM、未接住的异常）后没有任何代码会再推它一把，是这里所有情况的共同点；清扫只做收尾，**不调大模型**。

| 编号 | 业务 | 卡在哪 | 怎么进来 | 现在的结局 | 清扫动作 |
|---|---|---|---|---|---|
| F1 | Fireflies | 首轮 P1 `processing_stage` 停在 `IDENTIFYING` / `EXTRACTING` | 连续 3 次没跑完（消息进死信）、消费者停摆超过 4 天（消息过期） | 永久处理中、不进列表；Java 再发消息会被当重复删掉（`meeting_pipeline_service.py` `_claim_meeting`：首次收到且已有行 → `SKIPPED_DUPLICATE`） | 按失败收尾、转 Pending 交管理员：卡在提取中按 6.11 作废；卡在识别中不调大模型补完识别（P8 / P1 按失败计） |
| F2 | Fireflies | 已投递（`dispatched_at` 非空）但 Python 没有 P1 行 | 消息解析失败被删、建行失败 3 次进死信、消费者停摆超过 4 天 | 永久不处理；Java 只补投 `dispatched_at IS NULL` 的行 | Java 补投一次（`redispatched_at` 记一次上限）；没有 P1 行就没有可给管理员看的东西 |
| F3 | Fireflies | 非首轮提取 `extraction_status = RUNNING` | Start Extraction / 自动路由提取被打断 | 整场写操作被挡、Start Extraction 不可点；自动路由重投因已有进行中的提取不再匹配 | 按设计 6.11 作废，会议转 Pending（待识别 · 提取失败），Start Extraction 恢复可点 |
| F4 | Fireflies | P2 `testimony_backfill_status = RUNNING` | API-23 应用后补抽 / API-29 Retry 被打断 | 页面没有出口（能清空它的操作自己也被挡） | 置 `FAILED`，页面出现 Retry |
| F5 | Fireflies | P7 `projection_status = PENDING` | 进程内的退避重试随进程消失；正文卡住时摘要行也一直 `PENDING` | API-23 跳过 `PENDING`，已授权内容一直不上线 / 应下线的一直在线 | 认领后按行当前状态重推（Fireflies 7 #Q30） |
| F6 | Fireflies | 应下线却没下成的 RAG 条目 | （一）已删 / 未授权、下线重试用尽停在 `FAILED`；（二）改正文后撤旧条目重试用尽；（三）写了条目与登记行、回写 `file_id` 前被杀 | 已删、未授权内容继续被召回 | （一）按行下线；（二）（三）按 `file_id` 删条目、软删登记行 |
| F7 | Fireflies | 先提交、后推送的写操作（**新发现**） | API-22 Start Extraction 软删、API-23 改 Unknown / 取消授权 / 上线、API-24 改内容：事务里没置 `PENDING`，提交后、推送前被杀 | 行停在 `ONLINE`（已删 / 未授权 / 内容已改）或 `NONE`（应上线），F5、F6 都捞不到 | 在 Fireflies 这几个事务里补 `mark_pending`，归入 F5（第 4.7 节） |
| E1 | AI 财务提取 | 任务 `PROCESSING` | 进程被杀；恢复本身失败（`_recover_claimed_task` 写库失败只记日志） | 永久 `PROCESSING`；重投被 `_check_task_status` 判在途后删消息；前端每 5 秒轮询、无上限 | 未处理完的文件置 `FILE_FAILED`，任务一律置 `FAILED`；不重投 |
| E2 | AI 财务提取 | 任务 `UPLOAD_COMPLETE` | Java 发 SQS 失败（只记日志）、提交与发送之间崩溃、消息解析失败、消费者没起、领取前抛异常 3 次 | 永久 `UPLOAD_COMPLETE`，增量上传被拒 | **不扫**（第 1.2 节） |

### 1.2 不做

- **读时判超时**（打开详情页、点按钮时判）：Fireflies 7 #Q12 已定由清扫统一做。
- **Java `ff_connection_configuration.sync_started_at` 残留**：下一次抢占超过 60 分钟即接管（`FfConnectionConfigurationRepository`），影响只是当天跳过该租户。
- **自动路由的公司变更消息进死信**：不卡页面，只是少一次自动路由。
- **`dispatched_at` 为空、租户已断开 / key 被删的会议**：不补投；重新连接后每日拉取会补投（`FfSyncServiceImpl` 只拉 CONNECTED 且有 key 的租户）。
- **AI 财务提取重新提取**：见第 5.1 节「不重投」。
- **AI 财务提取卡在 `UPLOAD_COMPLETE`（E2）**（用户决定 2026-10-30）：扫与不扫对用户没有实际区别。
  - 没人领的任务只能按等待时长判，时限至少 2 小时，那时用户早已离开页面，而离开后本来就回不到这个任务。
  - 重新上传会新建任务，不受卡住的任务影响。
  - 反过来，消费者停摆几小时后恢复时，排队的消息还能把它处理完；扫成 `FAILED` 反而断了这条路。

## 2. 调度与链路

### 2.1 方案（第 7 节 #1）

| 方案 | 做法 | 结论 |
|---|---|---|
| **A1 已定** | Java EventBridge 固定定时 → `scheduler-queue` → `ScheduleProcessor` 做 F2、再往新队列投一条清扫消息 → Python 消费者执行其余各类 | 与 `FirefliesDailyPull` 同一条链路；SQS 竞争消费、多实例不用加锁；重试 / 心跳 / Java 执行记录（`schedule_config`、`queue_message_log`）现成；F2 的补投必须在 Java（只有 Java 发 SQS），天然有挂点 |
| C 不选 | Python lifespan 里起 asyncio 周期循环 + Redis `SET NX EX` 选主 | 只改 Python、最快；但要新造周期任务框架和锁，每个 Pod 及连着共享库的本地进程都参与；F2 仍要 Java 另起定时 |
| A2 否 | Java 定时 → 内网直连 Python HTTP（ERL 式） | 定时线程没有用户 token，要开豁免路径，有暴露风险；同步占 Java 线程、异步则失败不可见 |
| B 否 | EventBridge 直投 Python 队列 | Java `cleanupStaleFixedSchedulers` 会删掉分组里不在枚举的定时；要改 Java 定时代码支持按任务指定目标队列，反而更绕 |

### 2.2 链路（A1）

```
EventBridge  StuckTaskSweep  cron(0/15 * * * ? *)
   │  {"messageType":"Scheduler","schedulerType":"StuckTaskSweep"}
   ▼
scheduler-queue ──► Java ScheduleProcessor.processMessage  case StuckTaskSweep
                      1. ffSyncService.redispatchLostMeetings()      ← F2（Java 表 + 发 fireflies-meeting-queue）
                      2. sqsService.send(stuck-task-sweep-queue, StuckTaskSweep 消息)
                                     │
                                     ▼
                    Python consumer/sweep/（在途上限 1，复用心跳）
                      stuck_sweep handler 平铺调用：
                        E1 → F5 → F6(一) → F3 → F4 → F1 → F6(二)(三)
```

- **频率**：每 15 分钟（写在枚举里）。
- **新队列** `stuck-task-sweep-queue`（Java `InitSqsQueueEnum` 建、Python 消费、Java 不监听，同 Fireflies 两条队列）：可见性超时 600 秒（= Python 心跳续期值）；**保留期 900 秒**——清扫消息过了一轮就没用，Python 停摆几天后恢复时不会一口气补跑几百轮；`maxReceiveCount` 3 沿用。
- **消息体**：Java `SqsMessage` 公共字段（`messageType = StuckTaskSweep`、`queueName`、`sendTime`、`uuid`），无业务字段。
- **Python handler 一律删消息**：某一类抛异常只记 ERROR、继续下一类；整轮失败不重投，等下一轮。

### 2.3 每轮执行与隔离

- **顺序**：E1 先（用户在页面等着）；F5 先于 F6(一)（先推卡住的行，免得同一行被两类处理）；F3 让页面恢复可操作；F1 放后面；F6(二)(三) 最后，避免误删本轮 F5 刚写的条目（另有 60 分钟时限保护）。
- **每类每轮最多处理 200 项**（常量），按卡住时间升序；剩下的下一轮接着做。
- **每项一个事务**，一项失败记 ERROR、不影响同类其他项。
- **同步数据库操作放 `asyncio.to_thread`**，不卡事件循环（`financial_forecast/CLAUDE.md` 记过探针超时事故）。

### 2.4 多实例与幂等

调度层面只保证「通常只有一个实例在扫」：EventBridge 与 SQS 都是至少一次投递，一轮扫得比 15 分钟还久时前后两轮也会重叠。**真正的防线是逐项条件更新**——扫到的时间戳 / 状态作为凭证，0 行即已被别人处理，跳过：

| 类 | 凭证 |
|---|---|
| F1 | 卡在提取中：复用 `_persist_void` 核对（同 F3，另核对 `processing_started_at`）；卡在识别中：先 `claim_processing` 把凭证从扫到的值条件更新为本次时间，最终事务再核对 |
| F2 | `UPDATE … WHERE dispatched_at = <扫到的值> AND redispatched_at IS NULL`（先认领再发送） |
| F3 | 复用 `_persist_void`：锁 P1 行 + `_holds_credential` 核对 `RUNNING` 与 `extraction_started_at` |
| F4 | `UPDATE … WHERE testimony_backfill_status = 'RUNNING' AND updated_at = <扫到的值>` |
| F5 | 认领 `UPDATE … SET updated_by = '1' WHERE projection_status = 'PENDING' AND updated_at = <扫到的值>`（触发器刷新 `updated_at`） |
| F6 | 下线 / 删条目本身幂等 |
| E1 | 锁任务行 `FOR UPDATE`，核对 `status = PROCESSING` 与 `updated_at` 仍是扫到的值（进程还活着时心跳会刷新它，核对不上即跳过） |

### 2.5 手动触发、本地与发版

- **test 环境走整条链路**：往 `lg-non-prod-test-scheduler-queue` 投 `{"messageType":"Scheduler","schedulerType":"StuckTaskSweep"}`（做法同 `docs/Finance email+条幅+提醒/2026-08-03-邮件发送SQS化-自测手册.md`）。
- **只测 Python**：直接往 `<前缀>stuck-task-sweep-queue` 投清扫消息（见 code-examples 第 3 节）。
- **本地**：本地 Java 保持 `cio.scheduler.scheduler-enable = false`（打开会改写、删除共享分组里的定时）；用上面的手动投递。
- **发版顺序**：Java 先（启动时建队列、建定时），Python 后；Python 只在启动时解析一次队列 URL，先发的话要等它下次重启才开始消费。
- **IAM**：确认 Python 所用凭证对新队列有 Receive / Delete / ChangeMessageVisibility / GetQueueUrl 权限（按队列 ARN 列举的策略要补）。

## 3. 卡死时限

写死为常量、**不作环境变量**（与 2026-10-30 对重试次数的决定一致）；删掉目前没人读的 `FIREFLIES_STUCK_TIMEOUT_MINUTES`（`common/config/fireflies.py`、`.env_example`、`env-update.txt` sprint122 段）。

| 类 | 判卡死的列 | 正常最坏耗时 | 时限 |
|---|---|---|---|
| F1 | P1 `processing_started_at`（本次尝试开始） | P8 + P1 串行，P2~P7 并行，加压缩 ≈ 69 分钟 | 120 分钟 |
| F2 | `ff_meeting_meta_info.dispatched_at` | 首次连接回溯 14 天时积压可达数小时 | 30 分钟，**且** `fireflies-meeting-queue` 可见 + 在途消息数为 0（否则本轮跳过 F2） |
| F3 | P1 `extraction_started_at` | Start Extraction ≈ 49 分钟，自动路由 ≈ 29 分钟 | 120 分钟 |
| F4 | P2 `updated_at` | 单人 ≈ 21 分钟；API-23 多人补抽串行排队 | 120 分钟 |
| F5、F6(一) | P7 `updated_at` | 一次推送几分钟（向量化） | 60 分钟 |
| F6(二)(三) | 登记行 `created_at` | 上线写登记行到回写 `file_id` 之间几分钟 | 60 分钟 |
| E1 | 任务 `updated_at`（心跳每 120 秒刷新，第 5.3 节） | 与任务大小无关 | 15 分钟 |

单次提示词最坏 ≈ 20 分钟（4 次尝试 × 300 秒 + 退避）。时限判错的后果都是「白跑一次」而不是数据错：老进程落库前都会核对凭证、核对不上即丢弃（E1 的核对在第 5.2 节补上）。

## 4. Fireflies

所有清扫写入 `updated_by` / `operator` 用 `SYSTEM_USER_ID`。每处理一项写一条 P8 审计 `SWEEP`（`after_value`：`category`、扫到的时间戳、动作结果）；复用函数自带的审计照写。

### 4.1 F1 首轮卡在处理中

- **判定**：`processing_stage <> 'DONE' AND processing_started_at < now() - 120 分钟`。
- **原则**（用户决定 2026-10-30）：生产环境不频繁发版，连续 3 次没跑完的会议多半一直处理不了，按失败收尾、转 Pending 交管理员手动处理，**不补投重跑**。
- **卡在 `EXTRACTING`**：识别已落库，提取为 `RUNNING` / `AUTO`。
  - 复用 `_persist_void`：`trigger = AUTO`，带扫到的 `processing_started_at` 与 `extraction_started_at`。
  - 结果与首轮提取大模型最终失败走同一个出口：`VOIDED`、Pending + TO_IDENTIFY、`DONE`。
  - 首轮提取的产出只在最终事务落库，没有半截行要清。
  - 页面显示 Pending（待识别 · 提取失败），管理员核对后点 Start Extraction。
- **卡在 `IDENTIFYING`**：识别结果在最后一个事务里一次写入，卡住时 P2 / P3 / P4 都还没有。清扫**不调大模型补完识别**：
  1. 用 `claim_processing` 把凭证条件更新为本次时间。老进程若还活着，落库时凭证不符、结果被丢弃。
  2. 只跑识别的规则部分：参会人匹配链 ①~④、说话人按姓名绑定、名册姓名匹配、专家补充、类型判定、公司归属裁决。P8 / P1 不调用，按调用失败计。
  3. 一个事务完成：核对新凭证、`_delete_outputs` 清残留、写 P2 / P3 / P4 与识别结论、置 `DONE`、记 IDENTIFY 审计（`after_value` 注明由清扫收尾）。
  - 结论沿用现有 `_decide`：P1 失败 → `QUALITY_CHECK_FAILED` → Pending + TO_IDENTIFY。转录为空仍判 `NO_SUBSTANCE`（Invalid，不进列表）。
  - 页面显示 Pending（待识别 · 识别失败）：规则认得出的参会人照常显示，认不出的标为未识别。管理员补齐后点 Start Extraction。
  - `QUALITY_CHECK_FAILED` 会让提取前补跑 P1（Fireflies 开发设计 7 #Q50），自动路由也不碰它（`auto_route_service` 排除该结果）。
- **规则部分本身出错**（代码缺陷）：清扫每轮同样失败、记 ERROR，靠修代码解决。
- **与 Q13 的关系**：这是 Q13「首轮跑完才进列表」的例外：连续 3 次没跑完由清扫按失败收尾，与大模型最终失败一样进 Pending。需回写 Fireflies 开发设计 7 #Q13。
- **新增**：
  - `identification_service.finish_interrupted_identification(meeting_id, processing_started_at) -> bool`：把 `identify_meeting` 的规则步骤抽出来两处共用；最终事务带 `_delete_outputs` 与置 `DONE`。
  - `extraction_service.void_stuck_extraction(...)`：与 F3 共用（第 4.3 节）。

### 4.2 F2 已投递却没有 P1 行（Java）

- **判定**：`dispatched_at < now() - 30 分钟 AND redispatched_at IS NULL AND NOT EXISTS ai_ff_meeting_state`，组织未删；且 `fireflies-meeting-queue` 的 `ApproximateNumberOfMessages + ApproximateNumberOfMessagesNotVisible = 0`，不为 0 时整类跳过本轮（积压中的消息还没轮到，不算丢）。
- **动作**：先认领 `UPDATE ff_meeting_meta_info SET dispatched_at = now(), redispatched_at = now() WHERE id = ? AND dispatched_at = <扫到的值> AND redispatched_at IS NULL`，1 行才发送；发送复用 `toMessage` + `sendMessageReturningId`。发送失败只记 ERROR（已认领，不再补投；人工按 Fireflies code-examples 第 4 节应急，把 `redispatched_at`、`dispatched_at` 置空）。误报的补投由 Python 去重（唯一键 + `receive_count` 分支），无害。补投后首轮若又卡住，归 F1 按失败收尾。
- **新增**：
  - 表列 `ff_meeting_meta_info.redispatched_at`（第 6 节）。
  - `FfSyncService.redispatchLostMeetings()`；`toMessage` 由 private 改为包内可用。
  - `SQSService` 加取队列深度的方法（`GetQueueAttributes`）。
  - 读 `ai_ff_meeting_state` 走已有的只读原生 SQL 仓储（`FfPythonTableReadRepositoryImpl` 先例）。

### 4.3 F3 非首轮提取卡在 RUNNING

- **判定**：`extraction_status = 'RUNNING' AND processing_stage = 'DONE' AND extraction_started_at < now() - 120 分钟`。
- **动作**：复用 `extraction_service._persist_void`（锁 P1 行 + `_holds_credential` 核对，等价于条件更新）：作废 → `VOIDED`、会议 Pending + TO_IDENTIFY、EXTRACT 审计；改状态列触发器刷新 `updated_at`，已打开的页面再提交会提示过期。
- **新增**：公开包装 `extraction_service.void_stuck_extraction(meeting_id, extraction_trigger, extraction_started_at, processing_started_at=None) -> bool`（同步函数，清扫用 `to_thread` 调；F1 卡在提取中时传 `AUTO` 与 `processing_started_at`）。
- **顺带修（设计自补）**：Start Extraction 里「改判前补跑 P1」的落库 `identification_service._persist_rerun` 不核对任何凭证，作废后迟到的补跑仍会写 P4、新采纳公司。改为落库前锁 P1 行、核对 `extraction_status = RUNNING` 且 `extraction_started_at` 仍是本次的值，核对不上丢弃（同 `_holds_credential`）。
- 自动路由的提取被作废后，会议已采纳公司、不再是自动路由候选，需管理员 Start Extraction（与大模型最终失败同口径）。

### 4.4 F4 证词补抽卡在 RUNNING

- **判定**：P2 `testimony_backfill_status = 'RUNNING' AND updated_at < now() - 120 分钟`。
- **动作**：一个事务，先锁 P1 行再处理参会人行（与正常流程锁顺序一致）：条件更新为 `FAILED`；`state_repo.touch` 刷新 P1；写 `SWEEP` 审计（target 为参会人）。页面出现 Retry（API-29 只接受 `FAILED`）。
- **新增**：`extraction_service.fail_stuck_backfill(meeting_id, participant_id, updated_at) -> bool`。不复用 `_finish_backfill`：它要的 `_BackfillContext` 会读整场转录。
- **并发**：老进程的补抽落库前核对 `RUNNING`（`_replace_testimony` / `_finish_backfill`），被置 `FAILED` 后结果丢弃；置 `FAILED` 后用户点 Retry 与老补抽并存时先提交者生效、后者看到状态已清空而丢弃。

### 4.5 F5 投影卡在 PENDING

- **判定**：P7 `projection_status = 'PENDING' AND updated_at < now() - 60 分钟`（走 `idx_ai_ff_routing_row_projection`）。
- **动作**：
  1. 逐行认领（第 2.4 节）。**不认领不行**：`_begin_push` 对已是 `PENDING`、`updated_by` 已是系统用户的行是同值赋值，ORM 不发 UPDATE、`updated_at` 不刷新，下一轮会再次捡到正在推的同一行。
  2. 认领成功的行按会议分组，**同一（去向, 公司）的正文行与摘要行放进同一批**，调 `projection_service.project_rows_online(row_ids, triggered_by=None)`：它按行当前状态推（上线 / 改内容 / 下线 / 置 `NONE`，摘要行分流到「只替换摘要」），不只是上线。
  3. 会议仍有 TO_CONFIRM_EXPERT（整场不投影，规则由调用方把关）：要下线的行照推；要上线的行置回 `NONE`，等 Confirm & Apply 再推。
- **失败计数**：不另计。推送失败走投影服务自己的退避重试与 `_MAX_ATTEMPTS`，用尽置 `FAILED`。

### 4.6 F6 应下线却没下成的 RAG 条目

- **（一）**：`projection_status = 'FAILED' AND file_id IS NOT NULL AND (deleted OR NOT authorized) AND updated_at < now() - 60 分钟` → `projection_service.project_rows_offline(row_ids, triggered_by=None)`。
  - **不能直接按 `file_id` 删**：知识库摘要行与正文行共用 `file_id`，按 `file_id` 删会连正文条目一起撤掉。
  - 摘要行 `FAILED`、正文行已删但仍挂 `file_id` 时，把正文行放进同一批，否则 `_begin_summary_sync` 返回 None、每轮空转。
  - 60 分钟节流：RAG 长期故障时每小时最多重试一轮。
- **（二）（三）**：不被任何 P7 行引用的 Fireflies 登记行（`business_type IN ('FIREFLIES','FIREFLIES_TESTIMONY','FIREFLIES_CROSS_COMPANY')`、未删、`created_at < now() - 60 分钟`）→ `get_ingest_service().delete_entries_by_file_id(file_id=…, user_id=SYSTEM_USER_ID)`（幂等，连带删切片与登记行）。
  - 返回 0（条目已不在、登记行还在）时兜底软删登记行，否则每轮重复命中。**新增** `file_registry.soft_delete_by_file_id(file_id)`。
  - 第四种孤儿（建了条目、还没写登记行就被杀）：没有向量化、召不回，只是垃圾行，查不到也不处理。

### 4.7 F7 先提交、后推送（在 Fireflies 里修）

`projection_service.mark_pending` 目前只由提取（1-P3）与证词补抽调用。下列事务也改为在同一事务里对要推的行调 `mark_pending`，被打断后统一由 F5 接手：

| 接口 | 事务 | 提交后的推送 |
|---|---|---|
| API-22 Start Extraction | 整场软删 P7 行 | `offline_meeting` |
| API-23 Confirm & Apply | 改 Unknown 整场软删、取消授权、授权上线 | `offline_meeting` / `project_rows_offline` / 后台 `project_rows_online` |
| API-24 改内容 | 改 P7 行内容 | 后台 `project_rows_online` |

- `mark_pending` 跳过摘要行、对无动作的行不改（已删且无 `file_id` 的行 `_derive_action` 为无动作），可直接用。
- API-23 的上线列表按 `NONE` / `FAILED` 选，必须在 `mark_pending` 之前算出。
- `_list_rows_to_offline` 若按状态过滤，要把 `PENDING` 算进去（开发时核对）。

## 5. AI 财务提取

### 5.1 E1 收尾动作

**判定**：`status = 'PROCESSING' AND NOT deleted AND updated_at < now() - 15 分钟`（走已有部分索引 `(status, updated_at) WHERE status NOT IN 终态`）。

**动作**：一个事务，依次：
1. 锁任务行 `FOR UPDATE`，核对 `status` 与 `updated_at` 仍是扫到的值，否则跳过。
2. 文件：
   - `PROCESSING` 的文件按 `settle_stuck_file_claims(give_up=True)` 的口径置 `FILE_FAILED`，软删有残留的明细行与 source_total；
   - 未删的 `UPLOADED` 文件置 `FILE_FAILED`。
   - 文案用现成的 `_ERR_INTERRUPTED`。
3. 任务一律置 `FAILED`（用户决定 2026-10-30）：增量上传第二批时卡住，第一批已解析的数据也随任务失败不再可用，用户整体重新上传；不按「有 `REVIEW_READY` 文件回 `REVIEWING`」区分。已是 `REVIEW_READY` 的文件不动。
4. 写 state_log：`event_type = 'ERROR'`，`triggered_by = 'scheduler'`，`error_detail` = "PROCESSING since <时间>, swept after <N> min"。
5. WARNING 日志。

**新增**：`extract_financial.sweep_stuck_task(task_id, expected_updated_at) -> bool`。单事务，内部复用上述函数的条件更新，不调它们各自的提交；第 2、3 步抽成一个函数，与第 5.4 节共用。

**不重投（第 7 节 #3）**，理由：
- 硬崩多源于发版或 OOM，OOM 类「毒文件」重投会再次打死进程、连带同进程的其他任务；
- 新消息的接收次数从 1 重新算，没有持久化计数就会无限循环；
- 用户离开页面后回不到这个任务（只靠本标签页 sessionStorage）；
- 重新上传成本低：失败任务点 Re-upload 会新建任务，不复用卡住的那个（`resolveOrCreateTask` 无 taskId 即新建）。

**用户看到的**：前端轮询拿到 `FAILED` 即停，弹 File Processing Errors（只列文件名），点 Re-upload 新建任务重传。前端不改。

### 5.2 防迟到的 worker 复活任务（设计自补，与清扫一起上）

时限判错时，老 worker 仍可能写回。改为条件写：
- `mark_task_processing`：只在 `status = 'UPLOAD_COMPLETE'` 时写（条件 UPDATE），0 行即退出。顺带修掉心跳失败时两个消费者并发领取同一任务、重复插入解析行。
- `finalize_task`：只在 `status = 'PROCESSING'` 时写。
- save_to_db 写文件结果：明细行插入与 `update_file_status` 同一事务，文件状态更新加 `WHERE status = 'PROCESSING'`，0 行整体回滚。否则被清扫置 `FILE_FAILED` 的文件会被改回 `REVIEW_READY`，而它的残留行已被软删，数据静默缺行。

### 5.3 存活信号：心跳刷新任务（第 7 节 #4）

在现有消息心跳里（每 120 秒续可见性），提取任务额外执行 `UPDATE ai_financial_extraction_task SET updated_at = now() WHERE id = ? AND status = 'PROCESSING'`。
- 好处：时限 15 分钟（固定时限方案要 120 分钟），与任务大小无关；PDF 没有页数上限、进程级大模型闸门排队也不限时，固定时限总有误杀长任务的可能。
- 代价：每 2 分钟每个在途任务多一次 UPDATE；心跳要加一个可选回调（只给提取消费者用）。
- 与 Fireflies「不存心跳」（Fireflies 设计第八章 #30）口径不同：Fireflies 是管理员后台处理，AI 提取是用户在页面盯着转圈。

### 5.4 `_recover_claimed_task` 第 3 次放弃时的文件收尾（设计自补）

第 3 次放弃置 `FAILED`（`consumer/handlers.py`）与清扫口径一致，保持不变。缺口只在文件：`settle_stuck_file_claims` 只处理 `PROCESSING` 文件，串行路径里还没开始的文件留在 `UPLOADED`，挂在 `FAILED` 任务下、前端显示成处理中占位。改为调用同一个 `sweep_stuck_task` 的收尾逻辑（第 5.1 节第 2、3 步）。

## 6. 数据库变更

测试环境还没发 sprint122，清扫的表结构**直接并入 Fireflies 的两份建表脚本**，不另开脚本（用户决定 2026-10-30）；执行时机随原脚本（先于两端发版）。

| 端 | 文件 | 变更 |
|---|---|---|
| Java | `deploy/upgrade_doc/sprint122/V1__ff_init.sql` | `ff_meeting_meta_info` 加 `redispatched_at TIMESTAMPTZ NULL`（清扫补投时间；非空即已补投过一次，不再补投） |
| Python | `sql/migrations/business/V034__sprint122_fireflies_init.sql` | 四个部分索引（见下），ORM `__table_args__` 同步声明（`ai_file_registry` 的 ORM 没有声明索引的惯例，不加） |

Python 部分索引，每个对应一类扫描：
- `ai_ff_meeting_state (processing_started_at) WHERE processing_stage <> 'DONE'` → F1
- `ai_ff_meeting_state (extraction_started_at) WHERE extraction_status = 'RUNNING'` → F3
- `ai_ff_meeting_participant (updated_at) WHERE testimony_backfill_status = 'RUNNING'` → F4
- `ai_file_registry (created_at) WHERE NOT deleted AND business_type IN ('FIREFLIES','FIREFLIES_TESTIMONY','FIREFLIES_CROSS_COMPANY')` → F6(二)(三)

F5、F6(一) 用已有的 `idx_ai_ff_routing_row_projection`，反查中间表用已有的 `idx_ai_ff_routing_row_file`；E1 用任务表已有的部分索引。P8 审计新增事件类型 `SWEEP`：`event_type` 是 VARCHAR(32)，只改枚举与列注释，不需要 DDL。DDL 见 code-examples 第 2 节。

## 7. 拍板记录

| # | 问题 | 结论 |
|---|---|---|
| 1 | 调度方式 | **已定 A1**（用户决定 2026-10-30）：Java 定时 + 新队列 + Python 消费（第 2.1 节）。C（Python 进程内循环 + Redis 锁）不选：F2 补投仍要 Java 另起定时，变成两个闹钟 |
| 2 | F1 首轮卡死怎么收尾 | **已定：按失败收尾、转 Pending 交管理员**（用户决定 2026-10-30：生产不频繁发版，一直处理不了的会议交管理员手动处理）。卡在识别中的不调大模型补完识别，走「识别失败」出口（第 4.1 节）。不选「删行交 Java 补投、从头重跑」 |
| 3 | AI 提取卡死：收尾还是重投 | **已定：收尾不重投，任务一律置 `FAILED`**（用户决定 2026-10-30；不考虑「第一批已解析回 `REVIEWING`」）。不选重投：要 Java 发消息、持久化次数上限，且有毒文件会反复打死进程 |
| 4 | AI 提取 `PROCESSING` 判卡死 | **已定：现有 SQS 心跳（`consumer/heartbeat.py`，默认每 120 秒）顺带刷新 `updated_at`，超过 15 分钟没刷新判卡死**（用户决定 2026-10-30，第 5.3 节）；进程死后约 15～30 分钟收尾。不选固定 120 分钟：最坏让用户盯着转圈 2 小时多，且会误杀跑得久的正常任务 |
| 5 | `UPLOAD_COMPLETE` 卡死是否一起扫 | **已定：不扫**（用户决定 2026-10-30）。扫与不扫对用户没有实际区别，理由见第 1.2 节 |
| 6 | F7 先提交后推送 | **已定：在 Fireflies API-22/23/24 事务里补 `mark_pending`，归入 F5**（用户决定 2026-10-30，第 4.7 节）。不选清扫增查：「内容改了没重推」从状态列看不出来，补不全 |
| 7 | 卡死时限 | **已定：按类写死常量（第 3 节），删 `FIREFLIES_STUCK_TIMEOUT_MINUTES`**（用户决定 2026-10-30）。不选环境变量：上线后基本不调，多维护六七个变量 |

## 8. 改动清单

**Java（`java/CIOaas-api`）**
- `FixedScheduleTypeEnum` 加 `StuckTaskSweep`；`ScheduleProcessor.processMessage` 加 case，平铺调用 F2 与发清扫消息。
- `InitSqsQueueEnum` 加 `StuckTaskSweepQueue`；`SqsMessageType` 加 `StuckTaskSweep`；消息 DTO 继承 `SqsMessage`。
- `FfSyncService.redispatchLostMeetings()`；`SQSService` 加取队列深度；`ff_meeting_meta_info` 实体加 `redispatchedAt`。
- 迁移：并入 `V1__ff_init.sql`（第 6 节）。

**Python（`python/CIOaas-python`）**
- `consumer/sweep/`（messages / handlers / poller / lifecycle，照 `consumer/CLAUDE.md` 模板），嵌进 `combined_lifespan`，更新 `tests/consumer/learn/test_main_wiring.py`；在途上限写死 1。
- `fireflies/application/service/stuck_sweep_service.py`：F1、F3~F6 的扫描与逐项处理，平铺；复用 / 新增第 4 节列的函数。
- `lg/db/service/extract_financial.py`：`sweep_stuck_task` 与扫描查询；第 5.2 节的条件写；`consumer/handlers.py` 第 3 次放弃改调同一收尾；心跳回调（第 5.3 节）。
- Fireflies 修复：F7 补 `mark_pending`；`_persist_rerun` 核对凭证。
- 删 `FIREFLIES_STUCK_TIMEOUT_MINUTES`（配置、`.env_example`、`env-update.txt`）；迁移并入 `V034`（第 6 节）；P8 审计枚举加 `SWEEP`。
- 每轮包一层 `start_trace(source=TraceSource.CRON)`，`finish_attributes` 记各类扫到 / 处理 / 跳过数。

**Web**：不改。

**单测**：每类至少一条「扫到 → 处理」、一条「凭证不符 → 跳过」；F7 三个接口在提交后、推送前抛异常时行停在 `PENDING`；E1 的迟到 worker 写回被拒。

## 9. 可观测与告警

- 每轮一行 `ai_trace`（`source = CRON`），各类计数在 `finish_attributes`。
- 逐项留痕：Fireflies P8 审计 `SWEEP`（加上复用函数自带的审计）；AI 提取 state_log `triggered_by = 'scheduler'`。
- 日志：每处理一项 WARNING（已收尾，不打扰 Sentry）；某一类或某一项处理抛异常 ERROR（进 Sentry）；Java F2 发送失败 ERROR。
- 「这轮到底跑没跑」：Java `schedule_config` 的 `last_execution_time` / `execution_count` 与 `queue_message_log`。整轮漏跑的监控（如 Sentry Crons）本期不做。
