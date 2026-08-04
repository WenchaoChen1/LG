# 邮件发送统一 SQS 化 · 设计文档

> 起草日期：2026-07-31 ｜ 当前版本 **v3**（并入两轮后端设计评审 + 两轮自查，修订记录见附录）
> 涉及仓库：`CIOaas-api`（查证分支 `uat` @ `3d5a2dbf0`）
> 目标链路：`业务处 → SQS → EmailProcessor → 业务处组装 → 统一发送`

---

## 一、背景与出发点

需求原始描述三条，均涉及季度基准报告导出 SharePoint、基准参考数据更新用户通知、月度基准更新邮件：

1. 删除 benchmarkemail 相关的、通过 API 调用的测试方法
2. benchmarkemail 相关的都改成 SQS 触发
3. email 增加一个处理器类，以后所有邮件发送为 `sqs → email processor → 业务处 → 发送`

### 1.1 与现状对齐

**第 1 条已完成，工作量为零。** 提交 `8b6deebe7`（2026-06-03，"benchmark: SQS-only triggering with company scope; drop HTTP endpoints"）一次删除 4 个 controller、-1338 行，已进入全部分支：

| 已删除 | 覆盖功能 |
|---|---|
| `BenchmarkEmailController` + `BenchmarkEmailPreviewService` + 5 个 VO | 月度基准邮件 |
| `BenchmarkNotifyTestController`（261 行） | 参考数据更新通知（`seed` / `seed-pair` / `clear` / `trigger-monthly`） |
| `BenchmarkPositionMonitorController` | 参考数据更新通知（`rerun-first-time` / `rerun-diff`） |
| `BenchmarkReportController` | 季度报告 |

反查：现存四个 `Benchmark*Controller` 中无任何**触发跑批 / 自测**用途的端点；`src/test` 下无 MockMvc / SpringBootTest，benchmark 测试全为纯 Mockito 单测。

注意它们并非全是只读——`BenchmarkController` 有 `@PostMapping("/details")`、`@PutMapping("/details/{detailId}")`、`@DeleteMapping("/details/{detailId}")`、`@PutMapping("/metrics/{metricId}/formula")`。这些是 Benchmark Entry 的正常业务写接口，**且 POST/PUT `/details` 正是 `BENCHMARK_ENTRY_UPDATE` 邮件的唯一触发源**（`BenchmarkEntryServiceImpl.addDetail:141` / `updateDetail:169`），与本设计直接相关，不属于"应删除的测试方法"。

**残留在文档而非代码**：`docs/benchmark-notify-update/self-test-guide.md` 通篇教人 curl 已删接口；`docs/Benchmark/manual-trigger-via-sqs.md:302` 仍推荐 `POST /benchmark-email/preview`。收尾任务包含同步这两份。

**第 2 条的定时触发已完成**，三个功能的定时入口均由 `ScheduleProcessor.processMessage`（`scheduler/service/ScheduleProcessor.java:283-302`）分发：

| 功能 | scheduler-queue 类型 | 二级队列 |
|---|---|---|
| 季度报告 | `QuarterlyBenchmarkReport` | `benchmark-report-queue`，per-company 扇出 |
| 参考数据更新通知 | `BenchmarkPositionMonitor` | 无二级队列，进程内跑 |
| 月度基准邮件 | `BenchmarkEmailDaily` | `benchmark-email-queue`，两阶段扇出 |

仍不走 SQS 的三个入口（均属"参考数据更新通知"，属**业务触发**而非邮件发送，处置见 §六决策 2）：

| 入口 | 位置 | 触发方式 |
|---|---|---|
| 应用启动首次补发 | `BenchmarkPositionInitializer:31` | `ApplicationReadyEvent` → `catchupExecutor` |
| 标准化完成后刷 baseline | `BenchmarkBaselineRefreshListener:42` | `@TransactionalEventListener(AFTER_COMMIT)` → `catchupExecutor` |
| 外部基准数据保存 | `BenchmarkEntryServiceImpl:141,169` | HTTP 线程 → `ioExecutor` → `notifyExecutor`（两层异步） |

**第 3 条是本设计的全部内容。**

### 1.2 邮件发送现状

五个调用点各自直连 `EmailServiceImpl.sendEmail()`（`system/service/EmailServiceImpl.java:104`），无队列、无去重：

| 调用点 | 线程 | 内容来源 |
|---|---|---|
| `BenchmarkReportEmailService` | worker / finalizer 线程同步 | `run` + `records` 内存对象 |
| `PositionNotifier.sendOne:271` | `notifyExecutor` fire-and-forget，队列满即丢（`:180-199`） | 内存 `UserEmailDto` + 公司名 |
| `BenchmarkEntryServiceImpl:403` | `ioExecutor` → `notifyExecutor`（`:141/169` → `:225/253`） | 入参 `platform` / `edition` |
| `CompanyAdminEmailComposer:70` | benchmark-email-queue worker 同步 | worker 内存 `ProcessedResult` |
| `PortfolioManagerEmailComposer:84` | 同上 | **从 `run_snapshot` 重建**（`BenchmarkEmailPortfolioWorker:138,168`） |

去重能力已于 `deploy/upgrade_doc/sprint109/V9_benchmark-email-cleanup.sql` 移除（`DROP TABLE financial_benchmark_email_send_log`），原文理由："与 `system.email` 表重复，dedup 价值不及维护成本，SQS 重投极小窗口的双发风险已被业务接受"。

---

## 二、目标形态

```
业务处 ──EmailDispatcher.enqueue(cmd)──▶ email-queue
   (TransactionSynchronization.afterCommit 才真正投递；逐条 try-catch)
                                            │
                                            ▼
                        EmailSendSqsHandler  implements MessageProcessor
                          ① 解析 payload，显式字段断言
                          ② dedupKey 探针：已有成功行 ⇒ ack 跳过
                          ③ EmailComposerRegistry.get(composerType) → Composer.compose(cmd)
                          ④ 组装失败：业务已失效 ⇒ NonRetryableException（warn+记账+ack）
                                      查库故障   ⇒ 普通异常（SQS 重试）
                          ⑤ emailService.sendEmail(...)   ← 唯一发送出口
                          ⑥ 返回 false：白名单拒绝 ⇒ NonRetryableException
                                        IO 故障   ⇒ 普通异常（SQS 重试）
```

不变量：`MessageProcessor` / `MessageProcessorManager` 机制不改，新 handler 按既有方式注册（`sqs/service/MessageProcessorManager.java:28`，现有 11 个实现）。

### 2.1 消息契约选型

采用**轻量指令**：消息只带路由键 + bizKey + 收件人，由 processor 回调业务 Composer 查库组装。放弃"完整渲染结果入队"，因其与需求的 `processor → 业务处` 顺序相反，且 context 内含大段 HTML 会撑大消息体。

固有代价：重试时重新查库组装，业务数据若变化内容可能不同。§四逐点评估，其中月度邮件有硬约束（约束 A）。

---

## 三、新增构件

### 3.1 路由键：新增 `EmailComposerTypeEnum`（不能复用 `EmailTypeEnum`）

**`EmailTypeEnum` 不能作路由键。** 实测三个调用点共用同一个值：

| 位置 | 枚举 |
|---|---|
| `CompanyAdminEmailComposer.java:71` | `BENCHMARK_POSITION_UPDATE` |
| `PortfolioManagerEmailComposer.java:85` | `BENCHMARK_POSITION_UPDATE` |
| `PositionNotifier.java:272` | `BENCHMARK_POSITION_UPDATE` |

三个实现撞一个 key，注册表 `@PostConstruct` 会直接崩。且 `EmailTypeEnum` 自身有历史重复 index（`SUPER_ADMIN_WELCOME` 与 `NOTIFY_USER` 同为 6），本就不适合当唯一键。

```java
// 落位：gstdev-cioaas-common/.../common/enums/EmailComposerTypeEnum.java
public enum EmailComposerTypeEnum {
  BENCHMARK_MONTHLY_COMPANY_ADMIN,
  BENCHMARK_MONTHLY_PORTFOLIO_MANAGER,
  BENCHMARK_POSITION_UPDATE,
  BENCHMARK_ENTRY_UPDATE,
  BENCHMARK_REPORT_SUCCESS_SUMMARY
}
```

> **实现期更新**：最终只落地 **5 个值**，未建 `BENCHMARK_REPORT_FAILURE`。原因：`BenchmarkReportEmailService.sendFailureNotification` 实测全仓无调用方，属于 `8b6deebe7` 遗留的死代码，已在 Task 6 随迁移一并删除，未给它分配 composer type。§四的表格与"拆成两个 Composer 类"的推论已同步修正为单个 Composer。

**必须放 `gstdev-cioaas-common`，不能放 `system/enums/`。** 实现方（`fi` 域的各 Composer）要引用它作为 `supportedType()` 的返回类型，若放在 `system` 域下就构成跨域引用对方 `enums`——`architecture.md §1.1` 明确禁止，并规定"跨业务域通用的枚举放 `gstdev-cioaas-common`"。同域的 `SqsMessageType`、`EmailTypeEnum` 也都在 common，落位一致。

`EmailTypeEnum` 保持原职责（渲染分类 + 落 `email.email_type`），由各 Composer 通过 `ComposedEmail.emailType` 回传给 handler。

### 3.2 消息契约

**必须继承 `SqsMessage`**（`common/sqs/dto/SqsMessage.java`）。`SQSServiceImpl:128` 的签名是 `<T extends SqsMessage> void sendMessage(...)`，仓库内 13 个 payload 类一律 `extends SqsMessage` + `@Data @EqualsAndHashCode(callSuper = true)`。裸 POJO 编译不过，也拿不到 `batchId` / `queueName`。

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class EmailSendSqsMessage extends SqsMessage {
  // messageType（固定 "EmailSend"）、batchId、queueName 由基类提供
  private String composerType;           // EmailComposerTypeEnum.name()，路由键
  private String companyId;              // 顶层字段，供 listener 记账，见下
  private Map<String, String> bizKey;    // 业务定位键，值一律为字符串
  private String recipientUserId;        // 站内收件人；与 recipientEmail 二选一
  private String recipientEmail;         // 无 user 记录的收件人（如配置的 SME 邮箱）
  private String dedupKey;               // 由 EmailDispatcher 统一生成，见 §五
}
```

**`companyId` 必须是顶层字段。** `SQSMessageListener:291 extractCompanyId` 从消息体顶层读它，不带则 `queue_message_log.company_id` 对所有邮件消息恒为 NULL。`BenchmarkEmailCompanySqsMessage:24` 的注释专门说明该字段是"为让 listener 能记日志而逐字携带"，沿用同一做法。

**`bizKey` 的值一律为字符串**，需要传集合时用逗号分隔由 Composer 自行 split，不引入嵌套 JSON。

**两个收件人字段二选一，不是可选增强。** `BenchmarkReportEmailService` 的收件人来自配置项 `cio.benchmark-report.sme-email`（`properties.getSmeEmail()`），系统内无对应 user 记录，`recipientUserId` 无法表达。handler 断言"恰有一个非空"，否则抛 `NonRetryableException`。

配套注册：

| 位置 | 改动 |
|---|---|
| `common/sqs/enums/SqsMessageType.java` | `+ EmailSend("EmailSend")` |
| `common/sqs/enums/InitSqsQueueEnum.java` | `+ EmailQueue("email-queue", false, 345600, 180, 0, 3, 0)` |
| `sqs/listener/SQSMessageListener.java` | `+ @SqsListener` 监听 `email-queue` |

`visibilityTimeout=180s`（与 `benchmark-email-queue` 一致）。**不能按"单封邮件 = 组装秒级 + SendGrid 15s"取 60s**：`SQSMessageListener.onBatch:177-181` 是 `for` 循环**串行**处理批内每条消息，而续期任务 `scheduleVisibilityTimeoutExtension` 在 `onMessage` 内针对**当前**消息注册，批内排在后面的消息在等待期间没有续期保护。批大小 10 × 最坏 15s 即 150s，60s 会导致后段消息在处理前就重新可见、被重复投递。180s 覆盖该窗口。

`SQSMessageListener:363` 的续期间隔是 `max(vt/2, 30)`，vt=180 时每 90s 续期一次。

### 3.3 业务侧统一接口

```java
public interface EmailComposer {
  EmailComposerTypeEnum supportedType();

  /**
   * 仅凭 bizKey 重建邮件内容。
   * 业务已确定失效（run 被删 / 公司已 Exited / 收件人已注销）→ 抛 NonRetryableException；
   * 查库故障、数据暂时读不到（见约束 A2）→ 抛普通异常，交给 SQS 重试。
   * 不使用 null 返回值表达失效。
   */
  ComposedEmail compose(EmailSendSqsMessage cmd);
}

public record ComposedEmail(String senderEmail, String receiverEmail, String subject,
                            String operator, String companyId, EmailTypeEnum emailType,
                            Context context, String templateName,
                            List<Attachments> attachments) {}
```

`senderEmail` 必须在契约里：现有调用点行为不一致——`PositionNotifier:217` 与 `BenchmarkReportEmailService:102` 显式 `setSenderEmail`，`BenchmarkEntryServiceImpl:376` 不设而依赖 `EmailServiceImpl:134-136` 的兜底。留给兜底会让"发件人是谁"取决于调用点是否记得设，契约里明确要求它更可靠（允许传 null 表示沿用默认）。

**`context` 里只允许放已物化的值（String / 数值 / 值对象 record）**，禁止放 JPA 实体或其惰性集合。原因见 §四约束 E。

**不用 `null` 表达失效，改抛 `NonRetryableException`。** 项目已有成熟约定（`SQSMessageListener:264-268`）：该异常 → `log.warn` + `queueMessageLogService.recordFailed(..., errorJson)` + 正常 ack，不进 DLQ、不产 Sentry event。`null` 语义会绕过 `queue_message_log`，让"业务失效"没有任何落库痕迹，且平白引入"null 与异常语义被混淆"的风险。

**`ComposedEmail` 不持有 `Email` JPA 实体。** 改为携带构造 `Email` 所需的字段，由 handler 组装实体。避免把 `system` 域实体升级为跨域公开契约的返回类型。

`EmailComposerRegistry` 用 `@Resource List<EmailComposer>` + `@PostConstruct` 建 `Map<EmailComposerTypeEnum, EmailComposer>`，重复注册直接抛异常快速失败。

### 3.4 发送结果处理（`EmailServiceImpl` 需一行改动）

`EmailServiceImpl.sendEmail` 返回 `Pair<Boolean,String>` 且**两条 false 路径都不抛异常**：

| 路径 | 性质 |
|---|---|
| `:114` 白名单拒绝（仅当 `environment` 为 **`stage`** 或 **`uat`**，见 `:105`；`test` / `prod` 不走此分支） | 永久性，不可重试 |
| `:193-196` `catch (IOException) { log.error; return Pair.of(false, ...) }` | SendGrid 故障，可重试 |

handler 必须区分二者，否则：忽略返回值 → SendGrid 故障静默 ack、邮件永久丢失（**比现状差**，现状至少留 `log.error` 和一行 status=0 的 `email` 记录）；一律抛 → stage / uat 环境的白名单拒绝会重试 3 次进 DLQ，把这两个环境的 DLQ 灌满噪声。

原计划"`EmailServiceImpl` 一行不改"在此处必须让步。**最小改动**：`:114` 的返回值是拼接串（`"Target user is not whitelisted for " + environment + " environment. ..."`），把其中的固定前缀提取为 `public static final String MSG_NOT_WHITELISTED_PREFIX = "Target user is not whitelisted for "`，handler 用 `startsWith(MSG_NOT_WHITELISTED_PREFIX)` 判定。仅提取常量，不动逻辑与文案。

### 3.5 入队门面

```java
/** 业务侧入参：不含 dedupKey / messageType，二者由 Dispatcher 补齐 */
@Data
@Builder
public class EmailSendCommand {
  private EmailComposerTypeEnum composerType;
  private String companyId;                 // 可空；用于 queue_message_log 记账
  private Map<String, String> bizKey;
  private String recipientUserId;           // 与 recipientEmail 二选一
  private String recipientEmail;
}

@Service
public class EmailDispatcher {
  /** 在 TransactionSynchronization.afterCommit 内投递；无事务上下文时直接投递 */
  public void enqueue(EmailSendCommand cmd);
}
```

`EmailDispatcher` 负责：校验收件人二选一 → 生成 `dedupKey`（§五规则）→ 组装 `EmailSendSqsMessage`（补 `messageType="EmailSend"`）→ afterCommit 投递。

**afterCommit 是强制的**：业务在事务内调 `enqueue`，若立即投递而事务随后回滚，会发出一封描述不存在状态的邮件。同模式见 `BenchmarkEmailPlanner:171-183`。

### 投递失败的可观测性 —— 已知缺口，非闭环

现状下无论 SendGrid 成败，`EmailServiceImpl:182` 都会先落一行 `email`（失败行 status=0）可审计。改造后若 SQS 投递失败，邮件既没进队列也没有 `email` 行。

**在 `EmailDispatcher` 里加 try-catch 解决不了这个问题。** 实测 `SQSServiceImpl.sendMessageToSqs:182-189` 把所有异常 `catch → log.error → return null`，`sendMessage:139-143` 拿到 null 后只再 `log.error` 然后正常返回 `void`。调用方**既拿不到异常也拿不到返回值**。此前援引 `BenchmarkEmailPlanner:190-212` 作为同模式是不成立的——它之所以有效，是因为它另有 DB 侧兜底（把 record 标 FAILED + reconcile tick 重新推进），不是靠 try-catch。

三个选项：

| 方案 | 代价 |
|---|---|
| A. 依赖既有 `log.error` + Sentry 告警 | 零改动。项目已接 Sentry 且 ERROR 级别上报，`"Failed to send message to SQS queue: {}"` 会成为 event。缺点：只有告警没有可重放的记录，需人工从日志捞回 |
| B. 给 `SQSService` 增加一个抛异常或返回 messageId 的重载 | 改公共组件，影响面需评估，但能让 Dispatcher 真正兜底 |
| C. 入队前先落一行 `email`（status=0）作为待发痕迹 | 与 §5.1 的探针语义冲突（探针会把它判为"需发送"，正确；但 handler 发送时要复用该行而非新插，等于回到"改 `EmailServiceImpl` 持久化逻辑"） |

**本设计取 A**，并如实记录这是缺口：SQS 长时间不可用时，该窗口内的邮件会丢失且只在日志/Sentry 留痕。若上线后该场景真实发生过，再按 B 补强。

`dedupKey` 由 `EmailDispatcher` 统一生成，业务侧只传结构化 bizKey，避免各 Composer 自由拼接导致格式漂移。

### 3.6 包结构落位

跟随 `system` 域现有结构（该域整体为老结构，非 DDD 四层，见 §七）：

```
system/
├── service/
│   ├── EmailService.java / EmailServiceImpl.java   [仅提取一个常量，见 §3.4]
│   └── email/
│       ├── EmailDispatcher.java                    [NEW]
│       ├── EmailComposer.java                      [NEW]
│       ├── EmailComposerRegistry.java              [NEW]
│       └── EmailSendSqsHandler.java                [NEW]
└── contract/email/
    ├── EmailSendSqsMessage.java                    [NEW]
    ├── EmailSendCommand.java                       [NEW]
    └── ComposedEmail.java                          [NEW]

gstdev-cioaas-common/.../common/
├── enums/EmailComposerTypeEnum.java                [NEW]  ← 跨域共享内核，见 §3.1
└── sqs/enums/{SqsMessageType, InitSqsQueueEnum}.java      [改]
```

---

## 四、五个调用点的改造

五处全部可仅凭 bizKey 重建，轻量指令方案成立。

| 调用点 | composerType | bizKey | 重建来源 |
|---|---|---|---|
| `PortfolioManagerEmailComposer` | `BENCHMARK_MONTHLY_PORTFOLIO_MANAGER` | `{runId, portfolioId}` | 已有 `reconstructResults()` 从 `run_snapshot` + `external_editions` 重建 |
| `CompanyAdminEmailComposer` | `BENCHMARK_MONTHLY_COMPANY_ADMIN` | `{runId, companyId}` | 需新增"按 companyId 从 `run_snapshot` 重建" |
| `PositionNotifier` | `BENCHMARK_POSITION_UPDATE` | `{runId}` 或 `{companyIds}` | 月度批走 runId；catchup 支线走 companyIds |
| `BenchmarkReportEmailService` | `BENCHMARK_REPORT_SUCCESS_SUMMARY`<br>（**单个 Composer**，见下） | `{runId}` | `financial_benchmark_report_record` 按 runId + status 重查；收件人走 `recipientEmail` |
| `BenchmarkEntryServiceImpl:361` | `BENCHMARK_ENTRY_UPDATE`<br>（一个类，内部按 bizKey 分支） | CA：`{platform, edition, orgId}`<br>PM：`{platform, edition, parentId}` | 入参 + 按收件人现查 |

**`supportedType()` 返回单个枚举，一个 Composer 类只能绑一种 composerType。**

> **实现期修正**：本节原本据此推论"`BenchmarkReportEmailService` 的 `sendSuccessSummary` / `sendFailureNotification` 必须拆成两个 Composer 类"。实际不需要拆——`sendFailureNotification` 实测全仓无调用方，是 `8b6deebe7` 删除 controller 后遗留的死代码，Task 6 已连同 `BenchmarkReportWorker` 里那个从未使用的注入一并删除。因此该服务只剩汇总邮件一条路径、只需一个 Composer，与 §3.1 的 5 值枚举一致。

反之 `BENCHMARK_ENTRY_UPDATE` 的 CA / PM 两种收件人共用同一个渲染逻辑，保持**一个** Composer 类、内部按 bizKey 带 `org` 还是 `parent` 分支即可——这也是实际落地的形态。

### 约束 A：月度邮件的两个数据竞态

**A1 — Admin 邮件重建只读 `run_snapshot`，绝不重算 diff。**

`BenchmarkEmailCompanyWorker:265-270` 有被注释标为 CRITICAL 的顺序：`sendAdminEmails` 先于 `writeBaselines`。理由（`:249-258`）：重试时 baseline 若已推进，diff 全变 UNCHANGED，PM 决策从 FIRE 翻成 SILENT，Stage 2 扇出漏掉该公司。异步化后该顺序失效——processor 消费时 baseline 已推进。规避方式是 Composer 只读 `run_snapshot`（快照在 baseline 之前已持久化）。此约束必须写入代码注释。

附带修正一处源码注释的事实错误：该段注释写 "after all Admin sends **succeed**"，但 `sendAdminEmails`（`:296-308`）把 per-recipient 失败吞掉只 `log.warn`，并不阻止 `writeBaselines`。现状比注释宣称的更弱，异步化不会让它更差。

**A2 — snapshot 的 pre-DELETE 窗口（异步化引入的新竞态）。**

`BenchmarkEmailCompanyWorker` 在 **4 处**调 `deleteSnapshotRowsForCompany(runId, companyId)`（`:154` `:164` `:171` `:178`）——Worker 被 SQS 重投时先删后重建 snapshot。异步化后 email 消息只带 `{runId, companyId}`，消费时若撞上 Stage-1 重试的删除窗口，Composer 会读到 0 行。

**处置：Composer 读不到 snapshot 行时抛普通异常（可重试），绝不当作"业务失效"。** 这正是 §3.3 弃用 `null` 语义的直接收益——若沿用 null 表达失效，这里会静默 ack、邮件永久丢失。可选的进一步加固：把 email 消息延迟到 Stage-1 record 落终态后再投。

### 约束 B：收件人展开放在业务侧（入队前）

一个收件人一条消息，否则重试会重发给所有人。

`BENCHMARK_ENTRY_UPDATE` 的 bizKey **必须带组织维度**。实测 `BenchmarkEntryServiceImpl:221-267`：Company Admin 按 **(admin × 公司)** 各一封（同一用户是 2 家公司的 CA 就 2 封，`orgName` / `buttonUrl` 都不同）；PM 按 **(userId, parentId=organizationId)** 分组一封。只带 `{platform, edition}` 无法定位是哪一封，dedupKey 也会把两封合法邮件塌成一封 → 静默丢件。

`PositionNotifier` 的 `{companyIds}` 形态：100 个 UUID ≈ 3.6KB，SQS 上限 256KB。`runFirstTimeCatchup`（`BenchmarkPositionMonitorServiceImpl:181`）是唯一可能大批量的路径，且**不能改用 `{runId}`**——它虽在 `:128` 调 `acquireRun()`，但 run 在 `:146` 即标 COMPLETED 释放、仅作占位锁，`processOneCompanyCatchup:200-214` 只写 baseline **不写 `run_snapshot`**。该路径应在业务侧先聚合完整 fired 集合、再展开收件人，每条消息只带该收件人相关的公司子集。对比：月度批（`:115`）的 fired 来自 `phase2Diff`，结果落在 `position_run_snapshot.diff_decision`，`{runId}` 形态成立。

### 约束 C：事务边界

- `compose()` 标 `@Transactional(readOnly = true)`
- **探针与 `sendEmail` 必须在无外层写事务下执行**。若 handler 开写事务包住 `sendEmail`，`EmailServiceImpl` 的两次 `save`（`:182` `:191`）会被卷入，SendGrid 的 15s socket 超时期间持有 DB 连接——正是 CloseMonth listener 连接占用事故的形状。

### 约束 E：`Context` 必须只装已物化的值

约束 C 规定 `compose()` 走 `@Transactional(readOnly = true)`，但**模板渲染发生在该事务之外**——`templateEngine.process(templateName, context)` 在 `EmailServiceImpl:166`，此时 compose 的事务早已关闭。若 Composer 把 JPA 实体或其惰性集合塞进 `Context`，渲染时触发懒加载会抛 `LazyInitializationException`；SQS 线程没有 OSIV 兜底，不像 HTTP 请求那样有 session 存活到视图渲染。

因此 `ComposedEmail.context` 里只允许放 String / 数值 / 值对象 record（现有实践已符合，例如 `BenchmarkReportEmailService.SummaryRow` 就是纯值对象）。Composer 在只读事务内必须把需要的字段全部取出并转成值对象，不得把实体透传出去。

### 约束 D：查询放大

"一收件人一消息"下，`PositionNotifier` 场景每封邮件都要独立重跑 portfolio 映射 + 用户 + 公司名解析；现状是批量查完再扇出。月度批 N 公司 × M 收件人会把查询量放大一个量级。先接受，上线后按 `email-queue` 消费耗时决定是否加缓存。

---

## 五、数据库变更

```sql
-- 1) 加列（Email 实体同步加 dedupKey 字段）
ALTER TABLE email ADD COLUMN dedup_key varchar(128);
COMMENT ON COLUMN email.dedup_key IS '邮件去重键：{composerType}:{业务标识的SHA-256前32位}，由 EmailDispatcher 生成；历史行为 NULL';

-- 2) 普通索引（非唯一，理由见 §5.1）
CREATE INDEX CONCURRENTLY idx_email_dedup_key ON email(dedup_key) WHERE dedup_key IS NOT NULL;
```

### dedupKey 用哈希，不用明文拼接

初版设计为明文拼接 `{composerType}:{bizKey有序拼接}:{收件人标识}`，并声称"前提是 bizKey 只放有界字段"。**它举的例子自身就超界**：`FinancialBenchmarkEntry` 实测 `platform` 为 `length=50`、`edition` 为 `length=200`（`fi/domain/FinancialBenchmarkEntry.java:25-29`），于是

```
BENCHMARK_ENTRY_UPDATE:platform=<50>:edition=<200>:org=<36>:uid=<36>   →  最坏约 373 字符
```

超过 `varchar(255)`。后果不是"截断"而是**邮件彻底发不出**：`emailRepository.save`（`EmailServiceImpl:182`）会抛 `value too long for type character varying(255)`，且这是**抛异常**而非返回 `Pair.of(false, ...)`，所以不走 §3.4 的两分支处理，而是直接冒泡 → SQS 重试 3 次 → 进 DLQ。

改为定长哈希：

```
dedupKey = {composerType} + ":" + sha256Hex(canonical).substring(0, 32)

canonical = bizKey 按 key 字典序拼接 + "|" + (uid=<userId> 或 mail=<email>)
```

上限 = 最长枚举名 `BENCHMARK_MONTHLY_PORTFOLIO_MANAGER`（35） + 1 + 32 = **68 字符**，`varchar(128)` 有充足余量且与任何业务字段长度解耦。可读的 `canonical` 明文只进日志（`EmailDispatcher` 投递时 `log.info` 一次），不进列——排障时用日志里的明文反查 dedupKey。

哈希输入的三个 position 场景（都有天然一次性语义，不需要时间窗）：

| 场景 | canonical |
|---|---|
| 月度批（`:115`） | `run=<runId>\|uid=<userId>` |
| 启动首次补发（`:181`） | `first-catchup\|uid=<userId>` —— 该路径 gate 是 `baselineRepo.count() > 0` 即 skip，全生命周期只跑一次 |
| 静默刷 baseline 首封支线（`:282`） | `initial:cid=<companyId>\|uid=<userId>` —— 单公司，首封由 baseline 存在性保证幂等 |

`{companyIds}` 这类不定长值仍禁止进 canonical（哈希虽不受长度限制，但集合顺序不稳定会导致同一批算出不同 key）。

### 5.1 为什么是普通索引而不是唯一索引

初版设计为唯一索引，但与"命中且非 2xx → 重发"自相矛盾：`EmailServiceImpl:182` 保存的是 Composer 新建的实体（id 为 null → INSERT），同 `dedup_key` 再插一行必然违反唯一约束，重发这条分支物理上走不通。

三个选项——① 探针命中时复用旧行 UPDATE（要改 `EmailServiceImpl` 的持久化逻辑）；② 索引键改 `(dedup_key, status)`（两次失败 status 相同仍会冲突）；③ 普通索引 + 探针——**选 ③**。

理由：真正的重复来自 SQS 重投，而同一条消息的重投是**串行**的（visibility timeout 保证不会并发投递给两个消费者）。放弃唯一索引失去的只是"两个消费者同时探针都未命中"这个极窄竞态的兜底，代价远小于改动 `EmailServiceImpl` 持久化逻辑。

### 5.1.1 探针挡不住的那个窗口（实现期实测，修正本节初版的过度断言）

本节初版写的是"探针足以挡住"。**实测不成立**，需如实记录。`EmailServiceImpl` 的持久化是两次 save 夹着 SendGrid 调用：

```java
email = emailRepository.save(email);        // 第一次：status 未设，Email.status 是原始 int → 落 0
try {
  Response response = sendGrid.api(request);
  email.setStatus(response.getStatusCode());
  email = emailRepository.save(email);      // 第二次：只有这一次才写入 2xx
  return Pair.of(true, ...);
} catch (IOException ex) { ... }            // 只捕获 IOException
```

若**第二次 save 失败**（`DataAccessException`——DB 抖动、连接被回收），它不属于 `IOException`、不被捕获，会一路冒泡出 `sendEmail`、出 handler，触发 SQS 重投。而此时该 dedupKey 在 `email` 表里**只有一行 status=0**，探针 `existsByDedupKeyAndStatusBetween(key, 200, 299)` 必然未命中 → 邮件被第二次投递给 SendGrid，尽管它第一次已被接受。

净效果：探针把这个场景的重复从"最多 3 封"降到"恰好 2 封"，**没有消除**。而 §六决策 1 恰恰是用这个场景（"SendGrid 返回 202 之后的任何写库失败都会触发重投"）来论证去重的必要性——论证的方向没错，但"探针足以挡住"的结论过度了。

**附带推论**：`sendEmail` 只要 SendGrid **不抛异常**就返回 `Pair.of(true, ...)`，所以一个 SendGrid 4xx 会被存成 `status=400` 并被 handler 当作"已投递"正常 ack。因此上面探针决策里"命中但非 2xx → 重发"这条分支在生产中**实际不可达**：唯一能同时产生非 2xx 行与一次重投的，就是上述 status=0 的情形。

**处置：接受，不改代码。** 彻底关闭需要在 `EmailServiceImpl` 里把第二次 save 的失败也捕获掉（发已发出，不该因记账失败而重发），但那是本次明确划在范围外的共享代码。列入 §"仍未闭环 / 已接受的缺口"。

探针实现：`EmailRepository` 加 **`boolean existsByDedupKeyAndStatusBetween(String dedupKey, int from, int to)`**，以 `(dedupKey, 200, 299)` 调用；返回 true → ack 跳过；返回 false → 发送（新插一行，历史失败行保留作审计）。

**不能用 `findTopByDedupKeyOrderByCreatedAtDesc` 取最新一行再判 status。** 失败重发会不断新插行，若某次成功后又因其它原因插入了一行失败记录，"最新一行"就是失败的，探针会误判为需要重发 → 客户收到重复邮件。语义上要问的是"**是否曾经成功过**"，而不是"最后一次是否成功"，因此必须用 `exists` + 状态区间。

依赖的 `Email` 实体事实（已核对 `system/domain/Email.java`）：

- `Email extends AbstractAuditingEntity`，基类提供 `createdAt`（`Instant`），派生查询的排序字段成立。
- `status` 是**原始类型 `int`**，未发送 / 发送失败的行为 `0`（`EmailServiceImpl` 仅在 SendGrid 返回后才 `setStatus`），因此"非 2xx"天然涵盖 0。
- `body` 是 `nullable = false, length = 1000`。handler 组装 `Email` 时若不显式设 `body`，由 `EmailServiceImpl:131-133` 兜底填 `emailTypeEnum.getName()`——沿用现状即可，但不能设成空串以外的超长内容。

### 5.2 两个 DDL 执行风险

**唯一索引改普通索引后仍需 `CONCURRENTLY`**。`email` 是全站邮件流水表，只增不清理。`CREATE INDEX CONCURRENTLY` 不能在事务块内执行——这条要单独成段，若 runbook 把整个文件包在事务里需拆文件。上线前先查 `email` 表实际行数评估耗时。

**`Email` 实体加 `dedupKey` 会触发 ddl-auto 启动期 ALTER**。`deploy/cioaas-web.yml:43` / `-staging.yml:43` / `-prod.yml:43` 的 `ddl-auto` 全为 `update`，Hibernate 启动时会自动 `ALTER TABLE email ADD COLUMN`（抢 ACCESS EXCLUSIVE 锁，本项目有过锁放大器事故），且**不会**创建索引。正确顺序：**先执行 DDL、再部署带新字段的代码**——此时 ddl-auto 检测到列已存在不再 ALTER。§八落地顺序已按此排列。

### 5.3 迁移脚本落位（已定案）

**仓库无 Flyway / Liquibase**（全仓 grep 无命中）。`sprint114/README.md` 明确："只有 Python `scripts/migrate.py` 有 `schema_version` 记账，本仓库 runbook 只保留 Java 域表的迁移"——**没有任何运行器扫描 `upgrade_doc`，全靠人工执行**。目录本身也不连续（`sprint110` → `sprint112` → `113` → `114`，无 `sprint111` / `sprint115`）。

结论：新建 `deploy/upgrade_doc/sprint115/`，放 `V1__email_add_dedup_key.sql`，同步更新该目录 README 的 runbook，并在文档与发布单中标注**需人工执行**。

---

## 六、决策记录

### 决策 1：去重 —— 采纳 `email.dedup_key` + 普通索引 + 探针

理由：V9 删 `send_log` 的判断是"与 `email` 表重复"，在 `email` 表加一列顺着该判断走。不做的后果是双发窗口从"崩溃时亚秒级缝隙"扩大到"每次投递重试都重发"，`maxReceiveCount=3` 意味着客户最多连收 3 封；SendGrid 返回 202 之后的任何写库失败都会触发重投，这不是理论风险。

**此项仍为待确认决策**：若选择继续接受双发，则 §五整节与 §二步骤② 一并取消。

### 决策 2：需求 2 的三个非 SQS 入口，本次不动

它们是业务触发入口。改造后照样调 `EmailDispatcher.enqueue()`，邮件自动进 SQS，收益已经拿到。把业务触发本身也 SQS 化（尤其 position 链补 per-company 扇出——该链现为全量 N 公司 × M 指标在 `catchupExecutor` 进程内跑完，靠 DB 行级锁 `LOCK_KEY="position-monitor"` 互斥，见 `BenchmarkPositionMonitorServiceImpl:48`）规模接近月度邮件当初那次 SQS 化迁移，应独立立项。

---

## 七、规范符合性与已知张力

| 项 | 状态 |
|---|---|
| `SqsMessageType` / `InitSqsQueueEnum` 放 `gstdev-cioaas-common` | ✅ 符合 `architecture.md §1.1` 共享内核 |
| 契约类继承 `SqsMessage`、`contract/` 落位、`@Resource` 注入、注册机制 | ✅ 与既有 13 个 payload 类一致 |
| 复用 `NonRetryableException` 表达不可重试 | ✅ 与 `SQSMessageListener:264-268` 既有约定一致 |
| 新构件跟随 `system` 域老结构，未用 DDD 四层 | ⚠️ 偏离 `architecture.md §1`，建议接受 |

`system` 域整体仍是老结构（`service` / `domain` / `repository` / `contract`），`EmailService` / `Email` / `EmailRepository` / `EmailSendgridConfig` 全在其下。新增类单独用 DDD 四层会让同一能力出现两套结构。`ComposedEmail` 已改为不持有 `Email` 实体，跨域外溢问题相应缓解。若要纠正应作为 `system` 域整体 DDD 化的独立任务。**此项需确认是否接受。**

---

## 八、落地顺序

| 步 | 内容 | 说明 |
|---|---|---|
| **0** | **执行 DDL**（`sprint115/V1__email_add_dedup_key.sql`，人工） | 必须先于任何代码发版，规避 ddl-auto 启动期 ALTER |
| 1 | 基础设施：`EmailComposerTypeEnum` / `EmailSendSqsMessage` / `ComposedEmail` / `EmailComposer` / `EmailComposerRegistry` / `EmailSendSqsHandler` / `EmailDispatcher` / 队列注册 / `Email.dedupKey` / `EmailRepository.findTopByDedupKey...` / `EmailServiceImpl` 提取常量 | 此时无人调用，零风险 |
| 2 | 迁第一个：`BenchmarkReportEmailService` | 重建最简单、收件人是内部 SME、发错影响最小，用它验证整条链路 |
| 3 | 迁 `BenchmarkEntryServiceImpl` 与 `PositionNotifier` | |
| 4 | 最后迁月度邮件两个 Composer | 涉及约束 A1/A2，风险最高，放在链路已验证之后 |
| 5 | 收尾：同步 §1.1 的两份过期文档 | |

每步独立可上线，不需要特性开关。

---

## 九、风险

| 风险 | 缓解 |
|---|---|
| `EmailServiceImpl` 用 `SecurityUtils.getUserId()` 兜底填 `operator` 与 `companyId`；SQS 线程 ThreadLocal 为空 → `findByUserId(null)` 返回空 `User`（`UserServiceImpl:1131-1140`，不抛异常）→ **静默填空值** | handler 显式赋全 `operator` + `companyId`，绕开兜底分支；`operator` 为空时用 recipient 的 displayName 补 |
| 每封邮件白打一次 DB 空查（同一处 `findByUserId` 调用） | **无法由本设计消除**。该调用无条件执行，位于两个 `ObjectUtil.isEmpty` 判断**之前**，handler 填不填字段都会发生。要消除必须改 `EmailServiceImpl` 把查询挪进判断内部——超出本次范围，记为技术债。<br>（此条为第二轮复评 F-2 指出，v3 修订时漏并，Task 5 审查再次发现后补入） |
| `SQSMessageListener:275` 是无保护的 `throw (RuntimeException) e` 强转，Composer 抛受检异常会 `ClassCastException` 掩盖原因 | handler 内部把一切包成 RuntimeException 再上抛 |
| 已失权用户仍收到邮件（用户已被移出 portfolio / 公司，但消息已入队） | Composer 重建时校验收件人当前归属，失权则抛 `NonRetryableException` |
| SQS 消息不走 `@Valid` | handler 显式断言 `composerType` / `bizKey` / 收件人字段；日志只打 `userId` / `dedupKey`，不打邮箱（沿用 `PositionNotifier:274` 的既有做法） |
| `BenchmarkEntryServiceImpl:205` 的 `notifyLock`（`entry-update:{platform}:{edition}`）现覆盖整段发邮件，改造后只覆盖入队，持锁从分钟级降到毫秒级 | 重复触发的去重职责由 dedupKey 接手 |
| DLQ 里堆积邮件消息无人处理 | 与现有队列一致，依赖 DLQ 监控告警；本设计不新增 DLQ 消费逻辑 |
| 端到端时延增加 | 五处中四处本就异步（fire-and-forget / worker 线程 / 两层 executor），仅从"进程内异步"变为"跨消息异步"，换来可重试与去重 |

---

## 十、测试

单元测试（按项目约定仅本地跑、不入库）：

| 类 | 覆盖 |
|---|---|
| `EmailComposerRegistryTest` | 正常路由 / 未知 composerType / 重复注册启动失败 |
| `EmailSendSqsHandlerTest` | 字段断言（收件人二选一违反、composerType 缺失）/ 探针命中 2xx 跳过 / 命中非 2xx 重发 / compose 抛 `NonRetryableException` 走 ack / compose 抛普通异常上抛 / `sendEmail` 返回白名单拒绝 → `NonRetryableException` / 返回 IO 故障 → 上抛 / operator+companyId 兜底补值 |
| `EmailDispatcherTest` | 有事务时 afterCommit 才投递 / 无事务时直接投递 / 事务回滚不投递 / 投递抛异常时逐条 try-catch 且日志含 dedupKey |
| 各 `XxxEmailComposer` | 按 bizKey 重建成功 / 业务失效抛 `NonRetryableException` / **读不到 snapshot 抛普通异常**（约束 A2） |

集成验证（手工，test 环境）：往 `email-queue` 投一条 `BENCHMARK_REPORT_SUCCESS_SUMMARY` 消息，核对 `email` 表新增行、`dedup_key` 已填、`status` 为 2xx、`queue_message_log` 有记账；重复投同一条，核对无新增行。

---

## 十一、明确不做（YAGNI）

- 不做邮件模板管理 / 可视化编辑
- 不做发送速率限制、优先级队列、定时发送
- 不做 DLQ 自动重投入口
- 不改 `EmailServiceImpl` 的白名单、渲染、SendGrid 调用逻辑（仅提取一个常量，见 §3.4）
- 不迁移 `EmailTypeEnum` 中与本次三个功能无关的其余邮件类型；新链路建好后按需逐个迁入

---

## 十二、待确认事项

1. **去重**（§六决策 1）：采用 `email.dedup_key` + 普通索引 + 探针，还是继续接受双发？后者则删除 §五整节与 §二步骤②。
2. **包结构**（§七）：接受跟随 `system` 域老结构，还是要求新构件用 DDD 四层？
3. **`EmailServiceImpl` 的一行改动**（§3.4）：接受提取白名单拒绝文案的**前缀常量**（供 handler `startsWith` 判定），还是坚持零改动、由 handler 硬编码同一份字符串字面量（更脆弱，文案一改就静默失效）？

---

## 附录：修订记录

### v2（第一轮评审）

v1 经后端设计评审（`review-backend-design`）后修订：

| 类别 | 问题 | 处置 |
|---|---|---|
| 阻塞 | 三个 Composer 共用 `EmailTypeEnum.BENCHMARK_POSITION_UPDATE`，注册表启动即崩 | 新增 `EmailComposerTypeEnum` 作路由键（§3.1） |
| 阻塞 | 契约类未继承 `SqsMessage`，编译不过；且缺顶层 `companyId` | 改为 `extends SqsMessage` + 补 `companyId`（§3.2） |
| 阻塞 | `sendEmail` 返回 `Pair` 不抛异常，handler 无处理规则 | 定义两分支处理 + 提取常量（§3.4） |
| 高 | 唯一索引与"非 2xx 重发"物理矛盾 | 改普通索引 + 探针（§5.1） |
| 高 | snapshot pre-DELETE 竞态（4 处 `deleteSnapshotRowsForCompany`）会致邮件静默丢失 | 新增约束 A2；弃用 `null` 失效语义改抛异常（§3.3、§四） |
| 高 | `BENCHMARK_ENTRY_UPDATE` 的 bizKey 缺组织维度，会把多封合法邮件塌成一封 | bizKey 补 `orgId` / `parentId`（§四约束 B） |
| 高 | 事务边界未定义，`sendEmail` 可能在写事务内持连接 15s | 新增约束 C |
| 高 | `ddl-auto: update` 会启动期 ALTER；迁移落位标"待确认" | §5.2、§5.3 定案：无运行器、人工 runbook、新建 sprint115、DDL 提到第 0 步 |
| 中 | `null` 返回值绕过 `queue_message_log`，未复用 `NonRetryableException` | 全面改用异常语义（§3.3） |
| 中 | `enqueue` 在 afterCommit 抛异常则邮件无痕 | ~~逐条 try-catch + 日志含 dedupKey~~ —— **该处置无效，v3 已推翻**，见下 |
| 中 | `ComposedEmail` 持有 `Email` JPA 实体，把 system 域实体升级为跨域契约 | 改为携带字段，由 handler 组装实体（§3.3） |
| 事实错误 | v1 称 `BenchmarkEntryServiceImpl` 在"HTTP 保存线程内直接发邮件"，并据此宣称"HTTP 响应不再等 SendGrid"的收益 | 实测为 `ioExecutor` → `notifyExecutor` 两层异步（`:141/169` → `:225/253`）；该收益不存在，已删除并改写 §1.1、§1.2、§九 |
| 事实错误 | v1 称"全仓 controller 无任何 `send` 路径映射" | `UserController:363 @PostMapping("/sendEmailToReset")` 命中；结论方向不变，表述已收敛 |
| 事实错误 | v1 称 `runFirstTimeCatchup` "应优先复用其 run 走 `{runId}` 形态" | 实测其 run 仅作占位锁、`processOneCompanyCatchup` 不写 `run_snapshot`；已改为必须走 `{companyIds}`（§四约束 B） |

### v3（第二轮评审 + 自查）

| 类别 | 问题 | 处置 |
|---|---|---|
| P0 | **`dedup_key varchar(255)` 装不下**：`FinancialBenchmarkEntry.platform` 实测 `length=50`、`edition` `length=200`，`BENCHMARK_ENTRY_UPDATE` 的明文 dedupKey 最坏约 373 字符。且溢出时 `emailRepository.save` **抛异常**（非返回 `Pair.false`），绕过 §3.4 两分支处理 → 重试 3 次进 DLQ → 邮件彻底发不出。v2 还自称"前提是 bizKey 只放有界字段"，而它举的例子自身就超界 | 改为定长哈希 `{composerType}:{sha256前32位}`，上限 68 字符，列改 `varchar(128)`；明文只进日志（§五） |
| P1 | **`EmailDispatcher` 的兜底 try-catch 永不触发**：`SQSServiceImpl.sendMessageToSqs:182-189` 把所有异常 `catch → log → return null`，`sendMessage:139-143` 拿到 null 只 log 后正常返回 void，调用方既拿不到异常也拿不到返回值。v2 援引 `BenchmarkEmailPlanner:190-212` 是不成立的——后者靠 DB 侧兜底（标 record FAILED + reconcile tick），不是靠 try-catch | 如实降级为**已知缺口**，列出 A/B/C 三方案并取 A（依赖既有 `log.error` + Sentry 告警），不再宣称闭环（§3.5） |
| P1 | **`compose()` 只读事务与模板渲染位置冲突**：`templateEngine.process` 在 `EmailServiceImpl:166`，在 compose 事务关闭之后；`Context` 挂惰性代理即 `LazyInitializationException`，SQS 线程无 OSIV 兜底 | 新增约束 E：`Context` 只允许放已物化的值对象 |
| P2 | `visibilityTimeout=60s` 漏算 `onBatch:177-181` 的批内**串行**处理——续期任务只对当前消息注册，批内后续消息无保护，10 × 15s = 150s 会超时重投 | 提到 180s（与 `benchmark-email-queue` 一致） |
| P2 | 探针用 `findTopByDedupKeyOrderByCreatedAtDesc` 判最新一行 status，语义错误：成功后若再插入失败行会误判重发 | 改 `existsByDedupKeyAndStatusBetween(key, 200, 299)`——要问的是"是否曾成功"而非"最后一次是否成功" |
| P2 | `ComposedEmail` 缺 `senderEmail`；现有三个调用点行为不一致（两个显式设、一个靠兜底） | 契约里补上，允许 null 表示沿用默认 |
| 事实错误 | v2 称"现存四个 `Benchmark*Controller` 均为读取类接口" | **不成立**：`BenchmarkController` 有 POST/PUT/DELETE `/details` 与 PUT `/metrics/{id}/formula`，且 POST/PUT `/details` 正是 `BENCHMARK_ENTRY_UPDATE` 邮件的唯一触发源。已改写 §1.1 |
| 自查 | `EmailComposerTypeEnum` 放 `system/enums/` 构成跨域引用对方 enums，违反 `architecture.md §1.1` | 移到 `gstdev-cioaas-common`（§3.1、§3.6） |
| 自查 | `EmailSendCommand` 在 §3.5 被引用却从未定义 | 补完整定义 + Dispatcher 四步职责（§3.5） |
| 自查 | `supportedType()` 返回单个枚举，但 `BenchmarkReportEmailService` 被安排绑两个 composerType | 写明必须拆两个 Composer 类；`BENCHMARK_ENTRY_UPDATE` 的 CA/PM 反之共用一个类内部分支（§四） |
| 自查 | catchup 支线 dedupKey 写"收件人 + 时间窗"，时间窗从未定义 | 两条支线均有天然一次性语义，不需要时间窗，已给确切 canonical（§五） |
| 自查 | §3.4 称白名单拒绝影响 "test/uat" | 实测 `EmailServiceImpl:105` 是 `stage`\|\|`uat`，不含 test，已改正 |
| 自查 | §3.4 称提取"拒绝文案常量"用 `equals` 比对 | 该返回值是含 `environment` 的拼接串，`equals` 恒 false。已改为提取**前缀**常量 + `startsWith` 判定（第二轮评审独立指出了同一问题，其读到的是修改前的版本） |

### 仍未闭环 / 已接受的缺口

- **SQS 投递失败的邮件会丢失**，只在日志与 Sentry 留痕（§3.5 方案 A）。
- **去重探针挡不住"SendGrid 已接受但记账 save 失败"这一种重投**，该场景仍会重复投递一次（详见 §5.1.1）。彻底关闭需要改 `EmailServiceImpl` 的持久化异常处理，属本次范围外。
- **`email.status` 为 4xx 的行会被当作"已投递"** ——`sendEmail` 只在 SendGrid 抛异常时才返回 false，故 4xx 被正常 ack；探针的"非 2xx → 重发"分支因此在生产中不可达（同 §5.1.1）。
- **迁移后新出现的三处孤儿**（最终评审的聚合发现，均无害、未清理）：`notifyExecutor` 线程池在 `PositionNotifier` 与 `BenchmarkEntryServiceImpl` 都改为入队后已无任何提交方，但 `AsyncConfig` 仍定义该池；`EmailTypeEnum.BENCHMARK_REPORT_FAILURE` 的唯一生产者已随死代码删除；模板 `BenchmarkReportFailure.html` 随之失去渲染方。三者可在后续 sprint 一并清理。
- **查询放大**：一收件人一消息导致 `PositionNotifier` 场景重复查询，上线后按消费耗时决定是否加缓存（约束 D）。
- **`recipientEmail` 分支的收件人邮箱会随 messageBody 明文落 `queue_message_log`**。该分支只用于配置项里的内部 SME 邮箱，非客户 PII，接受。`recipientUserId` 分支不含邮箱。
- ~~第二轮评审提到 `renderPreview` / `PreviewOutput` 在两个 Composer 中已无调用方（死代码），本设计未核实，也未纳入范围；若属实应在 §八收尾步骤一并清理。~~ **实现期更新（Task 10）**：已核实属实——两者确无调用方，已在 Task 9 随迁移一并删除，此条闭环。
