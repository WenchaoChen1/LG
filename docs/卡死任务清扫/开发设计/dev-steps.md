# 卡死任务定时清扫 开发步骤

> 关联文档: [开发设计](./dev-design-doc.md) · [代码示例](./code-examples.md)
>
> DDL 已并入 Java `V1__ff_init.sql` 与 Python `V034`（Java `fc7d26df3`、Python `e72971c8`），不再单列步骤。两端都在 `sprint122` 分支；前端不改。

| # | 层 | 步骤 | 范围（端 / 主要文件） | 设计依据 | 依赖 | 完成标准 | 状态 |
|---|---|---|---|---|---|---|---|
| 1 | 点 | F7 三个接口保存时标 PENDING | Python：`fireflies/.../summary_record_service.py`（API-22 Start Extraction 软删、API-23 改 Unknown / 取消授权 / 授权上线、API-24 改内容的事务里调 `mark_pending`；API-23 上线列表在标记前算出） | 开发设计 4.7 | — | 单测：三个接口提交后、推送前抛异常，行停在 `PENDING`；正常路径推送结果不变 | 已完成 Python `2ea8dfe2` |
| 2 | 点 | AI 提取：E1 收尾函数 + 防迟到 worker 复活 | Python：`lg/db/service/extract_financial.py`（`sweep_stuck_task`、E1 扫描查询；`mark_task_processing` / `finalize_task` 改条件写）、`ai/agent/financial_extract_graph/nodes/save_to_db_node.py`（文件结果条件写、0 行整体回滚）、`consumer/handlers.py`（第 3 次放弃改调同一收尾） | 5.1、5.2、5.4 | — | 单测：收尾后文件 / 任务状态与 state_log；凭证不符跳过；迟到 worker 的三处写回被拒；第 3 次放弃时 `UPLOADED` 文件也置失败 | 已完成 Python `2ea8dfe2` |
| 3 | 点 | AI 提取：心跳刷新任务时间 | Python：`consumer/heartbeat.py`（可选回调）、`consumer/poller.py`（提取消费者传入刷新 `updated_at` 的回调） | 5.3 | — | 单测：每次心跳调用回调；回调失败只记日志、不影响续可见性 | 已完成 Python `2ea8dfe2` |
| 4 | 点 | Fireflies 逐项处理函数 F3~F6 | Python：`extraction_service.py`（`void_stuck_extraction`、`fail_stuck_backfill`）、`routing_row_repository`（F5 认领）、`lg/db/service/file_registry.py`（`soft_delete_by_file_id`）、`fireflies/domain/enums.py`（审计 `SWEEP`） | 4.3~4.6 | — | 单测：每个函数「凭证对 → 处理」「凭证不符 → 跳过」 | 已完成 Python `2ea8dfe2` |
| 5 | 点 | F1 收尾：中断识别补完 + 补跑 P1 核对凭证 | Python：`meeting_pipeline_service.py`（入口 `finish_interrupted_identification`：抢凭证、重置、清残留）、`identification_service.py`（抽出规则步骤、`finish_identification_by_rules`；补跑 P1 用调用方的提取凭证核对，丢弃时提取直接返回 DISCARDED） | 4.1、4.3「顺带修」 | — | 单测：卡在识别中 → Pending + `QUALITY_CHECK_FAILED`、`DONE`，参会人按规则落库；空转录 → `NO_SUBSTANCE`；作废后迟到的补跑被丢弃 | 已完成 Python `2ea8dfe2` |
| 6 | 点 | Java：F2 补投丢失的会议 | Java：`FfSyncService.redispatchLostMeetings`、实体 `redispatchedAt`、`SQSService` 取队列深度、读 `ai_ff_meeting_state`（只读原生 SQL 仓储） | 4.2 | — | 单测：队列不空整类跳过；认领 1 行才发送；`redispatched_at` 非空不再补投 | 已完成 Java `35ec04c31` |
| 7 | 线 | Fireflies 清扫编排 | Python：新建 `fireflies/application/service/stuck_sweep_service.py`（各类扫描、顺序、每类 200、逐项事务、`SWEEP` 审计、时限常量）。`FIREFLIES_STUCK_TIMEOUT_MINUTES` 已随第一轮删除 | 2.3、2.4、3、4 | 4、5 | 单测：每类扫描条件与时限；一项抛异常不影响同类其他项 | 已完成 Python `7f5ed527` |
| 8 | 面 | Java：定时任务 + 新队列 + 发清扫消息 | Java：`FixedScheduleTypeEnum.StuckTaskSweep`、`ScheduleProcessor` 加 case（先 F2 再发消息）、`InitSqsQueueEnum.StuckTaskSweepQueue`（可见性 600、保留 900）、`SqsMessageType`、消息 DTO | 2.2 | 6 | 单测：case 平铺调用 F2 与发消息；F2 抛异常仍发清扫消息 | 已完成 Java `670899bda` |
| 9 | 面 | Python：清扫消费者 | Python：新建 `consumer/sweep/`（messages / handlers / poller / lifecycle，在途 1、一律删消息；保留期 900 秒可能早于一轮结束，删消息失败记 WARNING）、`combined_lifespan` 接入、`tests/consumer/learn/test_main_wiring.py`、每轮 INFO 汇总日志（不写 `ai_trace`，用户决定 2026-11-02） | 2.2、2.3、9 | 2、7、8（消息契约） | 单测：handler 按 E1 → F5 → F6(一) → F3 → F4 → F1 → F6(二)(三) 调用、某类抛异常继续下一类；装配测试通过 | 已完成 Python `0f4a8d26` |
| 10 | 面 | 本地联调 | 本地造各类卡死数据，按 code-examples 第 3 节手动投消息 | 2.5 | 1~9 | 每类收尾结果符合设计；审计 / 日志留痕 | 已完成（2026-11-02 本地联调 Python；2026-11-03 本地补验 Java F2 与发清扫消息；EventBridge 建定时、Java 建队列留 test 环境验证） |

## 并行建议

| 轮 | 步骤 | 说明 |
|---|---|---|
| 一 | 1～6 | 文件互不重叠（Python 5 组 + Java 1 组），6 个 agent 并行；审核、测试按轮做 |
| 二 | 7、8 | Python 编排与 Java 定时，互不依赖 |
| 三 | 9 | 接上两端 |
| 四 | 10 | 联调 |

## 本地联调记录（2026-11-02，步骤 10）

- 环境：本地库 `127.0.0.1:5432/lg_test`；队列 `lg-jerry-dev-stuck-task-sweep-queue`（手动建，属性同 Java）。只起 tracing → llm_tracking → sweep 三层 lifespan，未起整个应用。
- 结果：E1、F1（识别中 / 提取中）、F3、F4、F5、F6(一)、F6(二)(三) 全部按设计收尾；F1 识别收尾未调大模型（时间窗内只有 F5 的 2 条 embedding）；仍是 PROCESSING 的登记行未被当孤儿撤；各类计数与实际一致（联调时计数还写在 `ai_trace`，之后按用户决定改为只打 INFO 汇总日志）；消息已删；第二轮各类扫到 0。
- 未覆盖（单测已覆盖）：心跳续期（一轮 8 秒，不到 120 秒）、多实例凭证不符跳过。
- 待 test 环境验证：Java 定时 `StuckTaskSweep` 建出与触发、队列由 Java 建出（含死信转发）；F2 补投已于 2026-11-03 本地补验（见下节）。

## 本地补验记录（2026-11-03，Java F2）

- 做法：本地 Java 保持 `scheduler-enable = false`（不建定时），但照常监听 `lg-jerry-dev-scheduler-queue`。删掉一场已 `DONE` 会议（Tamar 会 `01M62AKNYSKS1FYR925QY5BRWR`）的 `ai_ff_meeting_state` 行，使它满足 F2 条件（投递早于 30 分钟、`redispatched_at` 为空、没有 P1 行、会议队列为 0），再往该队列手投与 EventBridge 同款的消息 `{"messageType":"Scheduler","schedulerType":"StuckTaskSweep","sendTime":…,"uuid":…}`。
- Java：`queue_message_log` 依次为发 `FirefliesMeeting`（补投）→ 发 `StuckTaskSweep` → 消费 `Scheduler` 成功，先 F2 再发清扫消息，同 2.2；`dispatched_at` 与 `redispatched_at` 同写为补投时间。
- Python：收到补投消息时没有 P1 行，按首轮建行并清掉旧的识别结果，按当前 Email Domain 与 Cheat Sheet 从头识别（2 人按 GS 域名、1 人按名册邮箱，未调 P8），判 GS → LP 后自动提取成功（`AUTO`），因 Cross-Company 行默认不放行转 Pending（待审核）。
- 清扫消息被消费、队列清空；本地没有卡死项，未写 `SWEEP` 审计。
