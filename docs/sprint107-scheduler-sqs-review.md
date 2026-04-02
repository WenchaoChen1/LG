# Sprint 107 — Scheduler + SQS 模块重构审查报告

> **审查时间**：2026-03-25
> **审查范围**：`CIOaas-api` 仓库 `sprint/sprint107` 分支中 scheduler 和 sqs 模块的全部变更
> **对比基线**：`sprint/sprint106`（公共祖先 `24bab765d`）→ HEAD `134276ef4`
> **变更统计**：15 个文件，+561 / -787 行（净减少 226 行）

---

## 一、变更概览

### Scheduler 模块（3 个文件变更）

| 文件 | 变更摘要 |
|------|----------|
| `ScheduleProcessor.java` | 重构 `initFixedScheduler()`：新增 `cleanupStaleFixedSchedulers()` 基于 AWS 实际状态清理过期调度；移除 `scheduleProperties.getSchedulerEnable()` 全局开关检查 |
| `SchedulerService.java` | 接口新增 `listScheduleNamesByGroup()` 方法 |
| `SchedulerServiceImpl.java` | 实现 `listScheduleNamesByGroup()`（自动分页）；移除全局开关检查 |

### SQS 模块（12 个文件变更）

| 文件 | 变更摘要 |
|------|----------|
| `SQSMessageListener.java` | **核心重构**：从 634 行精简至 367 行（-42%）。职责下沉到 `QueueMessageLogService`；引入 DLQ 策略（`approximateReceiveCount >= MAX_RECEIVE_COUNT`）；新增 visibility timeout 自动续期机制 |
| `SqsMessageLogController.java` | **新增**：消息日志 CRUD REST 接口（GET 分页列表、GET 详情、DELETE） |
| `QueueMessageLog.java` | 域对象重构：新增 `sqsMessageId`、`messageBusinessType`、`companyId`、`isDlq`、`errorInfo` 字段；`messageType` 从 INTEGER 改为 VARCHAR（SEND/CONSUME） |
| `QueueMessageLogService.java` | 接口重设计：改为 `recordSent()`、`recordProcessed()`、`recordFailed()` 三个语义方法 + CRUD |
| `QueueMessageLogServiceImpl.java` | 全部方法使用 `Propagation.REQUIRES_NEW` 独立事务；append-only INSERT 模型替代旧版的创建-更新双步模型 |
| `SQSServiceImpl.java` | 精简 `sendMessage()`；移除 `batchId` 生成；`recordSentLog()` 委托给 `QueueMessageLogService` |
| `SqsErrorJsonBuilder.java` | **新增**：结构化异常 JSON 构建工具（exceptionType / message / cause / context / stackTrace） |
| `InitSqsQueueEnum.java` | `visibilityTimeout` 从 3600 改为 600；移除旧枚举值 |
| `SqsMessageStatus.java` | **新增**：替代旧 `MessageQueueStatus`，状态码 0=SENT / 2=PROCESSED / 3=FAILED |
| `MessageQueueStatus.java` | **已删除** |
| `MessageQueueType.java` | **已删除** |
| `QueueMessageLogRepository.java` | 简化为标准 JPA CRUD，移除旧版 `@Query(nativeQuery=true)` |

### SQL 迁移脚本（1 个文件）

| 文件 | 变更摘要 |
|------|----------|
| `deploy/upgrade_doc/sprint106/update_sqs_log_tables.sql` | `queue_message_log` 表结构变更 + DROP `forecast_failure_log` 表 |

---

## 二、做得好的地方

### 1. SQSMessageListener 职责拆分方向正确

旧版将日志记录（`logMessageReceipt`、`logMessageFailure`、`updateMessageLogStatus`）、用户上下文获取（`getUserIdSafely`）、复杂 JSON 解析回退等全部堆砌在 Listener 中。新版将这些职责干净地下沉到 `QueueMessageLogService` 的 `recordSent` / `recordProcessed` / `recordFailed` 三个语义明确的方法，Listener 只负责消息接收、路由和重试控制。

**收益**：Listener 从 634 行减到 367 行，可读性和可测试性大幅提升。

### 2. DLQ 策略显著改进

旧版对所有失败一律重置 visibility timeout 立即重试，无法区分中间重试与最终重试。新版引入明确的三段式策略：

```
成功  → recordProcessed(isDlq=false)，删除消息
失败且 receiveCount < MAX → recordFailed(isDlq=false)，重置 visibility → SQS 立即重试
失败且 receiveCount >= MAX → recordFailed(isDlq=true)，不重置 visibility → SQS 自然移入 DLQ
```

每次重试都产生独立的 FAILED 日志行，完整追踪消息的重试历史。

### 3. 日志服务独立事务保障

`QueueMessageLogServiceImpl` 所有 `record*` 方法使用 `@Transactional(propagation = Propagation.REQUIRES_NEW)`，确保日志写入在独立事务中完成，不受业务事务回滚影响。这解决了旧版中日志与业务事务绑定、业务回滚导致日志也丢失的问题。

### 4. Scheduler 清理逻辑改为基于 AWS 实际状态

`cleanupStaleFixedSchedulers()` 旧版只看 DB 中的 FIXED 类型 ScheduleConfig，新版改为：
1. 从 AWS `ListSchedules` 获取全量调度名称
2. 排除 `FixedScheduleTypeEnum` 中定义的有效固定调度
3. 排除 DB 中标记为 DYNAMIC 的动态调度
4. 剩余的即为需要清理的"孤儿"调度

同时加了 `try-catch` 保护——AWS 不可用时跳过清理，不阻塞启动流程。

### 5. SqsErrorJsonBuilder 结构化错误信息

将异常序列化为结构化 JSON：

```json
{
  "exceptionType": "java.lang.RuntimeException",
  "message": "Something went wrong",
  "cause": "java.sql.SQLException: Connection refused",
  "context": { "messageId": "abc-123", "queue": "forecast-queue" },
  "stackTrace": ["com.example.Service.method(Service.java:100)", "... 12 more"]
}
```

比旧版的纯文本拼接更利于后续查询和分析。`stackTrace` 限制 15 帧，防止字段膨胀。

### 6. 旧枚举清理完整

`MessageQueueStatus`、`MessageQueueType`、`ForecastFailureLogService`、`ForecastFailureLogRepository`、`ForecastFailureLog` 在 Java 源码中已无任何残留引用。清理干净彻底。

### 7. fi 模块"静默失败"改为"异常上抛"

旧版 `FinancialNormalizedServiceImpl.processMessage` 对 JSON 解析失败、companyId 为空等情况只 `log + return`，导致消息被静默消费，错误不可追踪。新版统一抛出异常，由 Listener 层统一记录失败日志、控制重试和 DLQ 策略。

---

## 三、问题清单

---

### C-1. SQL 迁移脚本遗漏 `message_type` VARCHAR 列 [Critical]

**严重等级**：Critical — 会导致运行时数据库写入失败

**问题定位**

`deploy/upgrade_doc/sprint106/update_sqs_log_tables.sql` 第 16 行：

```sql
-- Step 1: Drop old INTEGER message_type (0=SEND / 1=RECEIVE).
ALTER TABLE queue_message_log DROP COLUMN IF EXISTS message_type;
```

Step 2 第 22 行再次确认删除：

```sql
ALTER TABLE queue_message_log DROP COLUMN IF EXISTS message_type;
```

Step 3（第 28-38 行）添加了 `message_business_type`、`company_id`、`is_dlq`、`error_info` 四个新列，**但没有将 `message_type` 作为 VARCHAR 类型重新添加回来**。

**影响分析**

JPA 实体 `QueueMessageLog.java:49` 声明了该列：

```java
@Column(name = "message_type")
private String messageType;
```

`QueueMessageLogServiceImpl.java` 的三个核心方法都会写入该字段：

| 方法 | 行号 | 写入值 |
|------|------|--------|
| `recordSent()` | 第 55 行 | `entry.setMessageType("SEND")` |
| `recordProcessed()` | 第 76 行 | `entry.setMessageType("CONSUME")` |
| `recordFailed()` | 第 96 行 | `entry.setMessageType("CONSUME")` |

如果 Hibernate `ddl-auto` 配置为 `none` 或 `validate`（生产环境通常如此），执行此迁移脚本后，INSERT 操作会因 `message_type` 列不存在而抛出 `PSQLException`，**所有 SQS 消息日志记录都会失败**。

虽然 `QueueMessageLogServiceImpl` 的 `record*` 方法内部 catch 了异常不会中断业务流程，但这意味着**所有日志记录都会静默失败**——失去了整个消息日志审计能力。

**修复建议**

在 `update_sqs_log_tables.sql` Step 3 末尾增加：

```sql
-- message_type 从旧的 INTEGER(0=SEND/1=RECEIVE) 改为 VARCHAR(SEND/CONSUME)
ALTER TABLE queue_message_log
    ADD COLUMN IF NOT EXISTS message_type VARCHAR(20);
```

在 Step 4 增加列注释：

```sql
COMMENT ON COLUMN queue_message_log.message_type
    IS 'Pipeline stage: SEND (produced by send side) or CONSUME (produced by consume side)';
```

---

### I-1. SqsMessageLogController 分页参数无上限校验 [Important]

**严重等级**：Important — 可能导致数据库和网络性能问题

**问题定位**

`SqsMessageLogController.java` 第 25-29 行：

```java
public Result<Page<QueueMessageLog>> list(
    @RequestParam(defaultValue = "0") int page,
    @RequestParam(defaultValue = "20") int size) {
  PageRequest pageRequest = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "sentAt"));
  return Result.success(queueMessageLogService.findAll(pageRequest));
}
```

`size` 参数默认值为 20，但没有上限约束。调用方可以传入 `size=100000`，导致：
- 单次查询从 `queue_message_log` 表拉取海量数据
- `messageContent`（TEXT 类型，存储完整消息 JSON）和 `errorInfo`（TEXT 类型，存储完整异常信息）会被全部序列化
- 给数据库、JVM 内存和网络带宽造成严重压力

**修复建议**

**方案 A — Bean Validation 注解（推荐）**：

```java
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;

@Validated  // 需要在类级别添加
@Tag(name = "SQS: Message log")
@RestController
@RequestMapping("/sqs/messageLogs")
public class SqsMessageLogController {

  @GetMapping
  @Operation(summary = "List SQS message logs (paginated)")
  public Result<Page<QueueMessageLog>> list(
      @RequestParam(defaultValue = "0") @Min(0) int page,
      @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
    PageRequest pageRequest = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "sentAt"));
    return Result.success(queueMessageLogService.findAll(pageRequest));
  }
}
```

**方案 B — 代码内截断（更简单，无需引入额外注解依赖）**：

```java
public Result<Page<QueueMessageLog>> list(
    @RequestParam(defaultValue = "0") int page,
    @RequestParam(defaultValue = "20") int size) {
  size = Math.min(Math.max(size, 1), 100);
  page = Math.max(page, 0);
  PageRequest pageRequest = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "sentAt"));
  return Result.success(queueMessageLogService.findAll(pageRequest));
}
```

---

### I-2. DELETE 接口缺少权限控制 [Important]

**严重等级**：Important — 审计数据安全风险

**问题定位**

`SqsMessageLogController.java` 第 40-45 行：

```java
@DeleteMapping("/{id}")
@Operation(summary = "Delete SQS message log by ID")
public Result<Object> delete(@PathVariable String id) {
  queueMessageLogService.deleteById(id);
  return Result.success(null);
}
```

SQS 消息日志是**审计数据**，记录了每条消息的完整生命周期（发送 → 处理/失败 → DLQ）。当前该接口：
- 没有任何 `@PreAuthorize` 或角色检查
- 任何已认证用户都可以删除任意消息日志
- 删除后无法恢复，会破坏审计链的完整性

**修复建议**

**方案 A — 移除 DELETE 接口（推荐）**

审计日志应遵循"只增不删"原则，历史数据由 DBA 或定时任务按保留策略清理：

```java
// 删除整个 delete 方法和 QueueMessageLogService/Impl 中的 deleteById 方法
```

同时从 `QueueMessageLogService` 接口中移除 `deleteById(String id)` 方法声明，从 `QueueMessageLogServiceImpl` 中移除对应实现。

**方案 B — 添加管理员权限保护**

如果确实需要保留删除能力（例如 GDPR 合规需要）：

```java
import org.springframework.security.access.prepost.PreAuthorize;

@PreAuthorize("hasRole('ADMIN')")
@DeleteMapping("/{id}")
@Operation(summary = "Delete SQS message log by ID (admin only)")
public Result<Object> delete(@PathVariable String id) {
  queueMessageLogService.deleteById(id);
  return Result.success(null);
}
```

---

### I-3. MAX_RECEIVE_COUNT 硬编码与 InitSqsQueueEnum 分散管理 [Important]

**严重等级**：Important — 潜在的配置不一致风险

**问题定位**

同一个概念（SQS redrive policy 的 maxReceiveCount）在三处独立定义：

| 位置 | 文件:行号 | 值 | 用途 |
|------|-----------|-----|------|
| Listener 常量 | `SQSMessageListener.java:90` | `MAX_RECEIVE_COUNT = 3` | 判断 `isDlq` 标记 |
| 枚举定义 | `InitSqsQueueEnum.java:22-28` | 各队列 `maxReceiveCount = 3` | 创建新队列时的参数 |
| DLQ 初始化 | `SQSServiceImpl.java:90` | `setMaxReceiveCount(3)` | 配置 redrive policy |

**风险场景**：如果将来将 `InitSqsQueueEnum` 中某个队列的 `maxReceiveCount` 改为 5，但忘记同步修改 `SQSMessageListener` 中的 `MAX_RECEIVE_COUNT`，会出现：
- SQS 实际允许 5 次重试才移入 DLQ
- 但 Listener 在第 3 次就标记 `isDlq = true`，产生误导性日志
- 第 3、4 次重试的日志显示 `isDlq = true` 但消息并未真正进入 DLQ

**修复建议**

**方案 A — 统一从 InitSqsQueueEnum 获取（推荐）**

在 `SQSMessageListener` 中移除硬编码常量，改为根据队列名动态获取：

```java
// 移除：private static final int MAX_RECEIVE_COUNT = 3;

// 新增方法
private int getMaxReceiveCount(String queueName) {
  for (InitSqsQueueEnum queueEnum : InitSqsQueueEnum.values()) {
    if (queueName != null && queueName.endsWith(queueEnum.getQueueName())) {
      return queueEnum.getMaxReceiveCount();
    }
  }
  return 3; // 兜底默认值
}
```

将 `handleMessage` 第 195 行和 `processMessage` 第 252 行中的 `MAX_RECEIVE_COUNT` 替换为 `getMaxReceiveCount(queueName)`。

同时修复 `SQSServiceImpl.initDlq()` 第 90 行的硬编码：

```java
// 旧：setDeadLetterQueueRequest.setMaxReceiveCount(3);
// 新：从枚举获取
setDeadLetterQueueRequest.setMaxReceiveCount(queueEnum.getMaxReceiveCount());
```

**方案 B — 提取为共享常量**

如果所有队列的 `maxReceiveCount` 确认永远相同，可以将其提取为 `SchedulerConstants` 或 `SqsConstants` 中的公共常量：

```java
public final class SqsConstants {
  public static final int DEFAULT_MAX_RECEIVE_COUNT = 3;
  private SqsConstants() {}
}
```

三处统一引用该常量。

---

### I-4. 预测失败"不重试"策略被静默移除 [Important]

**严重等级**：Important — 行为变更需要明确确认

**问题定位**

旧版 `FinancialForecastDataServiceImpl.processMessage` 中有明确的设计决策：

```java
// 旧版逻辑（已移除）
catch (Exception e) {
  TransactionAspectSupport.currentTransactionStatus().setRollbackOnly();
  // 注释说明："treat message as consumed to prevent SQS retry,
  //           because a confirmed-failing forecast will not succeed on retry"
  // 不重抛异常 → SQS 认为消息已成功消费 → 不重试
}
```

新版移除了这个逻辑，异常自然上抛。这导致：

| 场景 | 旧版行为 | 新版行为 |
|------|---------|---------|
| 预测因数据缺失失败（确定性） | 消息被消费，不重试 | 重试 3 次，每次执行完整计算，最终进 DLQ |
| 预测因网络超时失败（瞬态） | 消息被消费，不重试（损失重试机会） | 重试 3 次，可能恢复 |

**影响分析**：
- **正面**：瞬态失败现在有了重试机会，之前是被一刀切地静默消费了
- **负面**：确定性失败（如某公司缺少必要的财务数据）会白白重试 3 次，每次都执行完整的 `buildForecastDataForCompanyById` 计算（涉及多次数据库查询和复杂业务逻辑），产生不必要的性能开销

**修复建议**

**如果确认这是有意变更** — 无需修改代码，但应在 commit message 或 PR 描述中明确记录：

> "移除了预测失败不重试的策略。所有消息处理失败都走统一的重试+DLQ 流程，牺牲确定性失败的少量重复计算开销，换取瞬态失败的重试恢复能力。"

**如果需要区分处理** — 引入自定义异常：

```java
// 新增异常类
package com.gstdev.cioaas.web.sqs.exception;

public class NonRetryableProcessingException extends RuntimeException {
  public NonRetryableProcessingException(String message) {
    super(message);
  }
  public NonRetryableProcessingException(String message, Throwable cause) {
    super(message, cause);
  }
}
```

在 `FinancialForecastDataServiceImpl.processMessage` 中区分使用：

```java
@Override
public void processMessage(String message, String messageType, String schedulerType) {
  String companyId = extractCompanyId(message);
  if (StringUtils.isBlank(companyId)) {
    // 确定性失败：companyId 缺失，重试也不会成功
    throw new NonRetryableProcessingException("companyId is blank in message");
  }
  try {
    buildForecastDataForCompanyById(companyId);
  } catch (DataNotFoundException e) {
    // 确定性失败：数据不存在
    throw new NonRetryableProcessingException("Forecast data missing for company: " + companyId, e);
  }
  // 其他异常自然上抛，走正常重试流程
}
```

在 `SQSMessageListener.processMessage` 中对 `NonRetryableProcessingException` 特殊处理：

```java
private void processMessage(String messageId, String messageBody, String queueName, int approximateReceiveCount) {
  String messageType = null;
  try {
    // ... 正常处理逻辑 ...
    queueMessageLogService.recordProcessed(messageId, messageBody, queueName, messageType, companyId, false);

  } catch (NonRetryableProcessingException e) {
    // 确定性失败：直接标记为最终失败，不走重试
    log.warn("Non-retryable failure, marking as DLQ: messageId={}, queue={}", messageId, queueName, e);
    String errorJson = SqsErrorJsonBuilder.build(e, context);
    String companyId = extractCompanyId(messageBody);
    queueMessageLogService.recordFailed(messageId, messageBody, queueName, messageType, companyId, true, errorJson);
    // 不重抛 → 消息被删除，不重试

  } catch (Exception e) {
    // 瞬态失败：正常重试流程
    log.error("Failed to process message: messageId={}, queue={}", messageId, queueName, e);
    // ... 现有的重试逻辑 ...
    throw e; // 或 throw new RuntimeException(...)
  }
}
```

---

### I-5. `scheduleProperties.getSchedulerEnable()` 全局开关被完全移除 [Important]

**严重等级**：Important — 需要确认是否为有意决策

**问题定位**

`ScheduleProperties.java` 第 37 行仍然保留了 `schedulerEnable` 属性定义：

```java
/**
 * Enable AWS EventBridge Scheduler
 * Default: false
 */
private Boolean schedulerEnable = false;
```

但新版代码中**没有任何位置读取**这个值。旧版在以下位置使用它作为全局开关：

| 位置 | 旧版行为 |
|------|---------|
| `ScheduleProcessor.initFixedScheduler()` | `schedulerEnable == false` 时跳过整个初始化 |
| `SchedulerServiceImpl.isInvalidCreateSchedulerParam()` | `schedulerEnable == false` 时拦截所有创建请求 |
| `SchedulerServiceImpl.updateSchedule()` | `schedulerEnable == false` 时阻止更新 |
| `SchedulerServiceImpl.deleteSchedule()` | `schedulerEnable == false` 时阻止删除 |
| `FinancialForecastHistoryServiceImpl.checkAndRepairAutoFillSchedules()` | `schedulerEnable == false` 时跳过检查修复 |

**影响分析**：
- **本地开发环境**：如果开发者的 Nacos 配置中 `cio.scheduler.scheduler-enable=false`，旧版会跳过所有 AWS Scheduler 操作。新版会尝试连接 AWS，如果没有正确配置 AWS 凭证，启动时会在 `sqsInit()` 阶段打印大量错误日志（虽然被 catch 不会阻塞启动）
- **测试环境**：同上，可能产生非预期的 AWS Scheduler 调度
- **已有配置失效**：Nacos 中已配置 `cio.scheduler.scheduler-enable=false` 的环境，升级后该配置静默失效

**修复建议**

**如果仍需开关功能** — 在关键入口处恢复检查：

```java
// ScheduleProcessor.initFixedScheduler() 开头
public void initFixedScheduler() {
  if (!Boolean.TRUE.equals(scheduleProperties.getSchedulerEnable())) {
    log.info("Scheduler is disabled (cio.scheduler.scheduler-enable=false), skipping initialization");
    return;
  }
  // ... 原有逻辑
}

// SchedulerServiceImpl 的 create/update/delete 入口
@Override
public void createSchedule(ScheduleRequestInput request) {
  Objects.requireNonNull(request, "ScheduleRequestInput cannot be null");
  if (!Boolean.TRUE.equals(scheduleProperties.getSchedulerEnable())) {
    log.warn("Scheduler is disabled, ignoring createSchedule: {}", request.getName());
    return;
  }
  // ... 原有逻辑
}
```

**如果确认不再需要** — 清理残留配置：

1. 删除 `ScheduleProperties.java` 第 33-37 行的 `schedulerEnable` 字段和注释
2. 删除 Nacos 配置中心中各环境的 `cio.scheduler.scheduler-enable` 配置项
3. 通知团队该开关已废弃

---

## 四、改进建议（Suggestion）

---

### S-1. sendMessage 移除了 batchId 的设置

**文件**：`SQSServiceImpl.java:115-135`

旧版在 `sendMessage` 中会生成 `UUID.randomUUID().toString()` 作为 `batchId` 并设置到 `messageData` 中。新版完全移除了这一逻辑。

消费侧 `SQSMessageListener.parseMessage()` 第 273 行有兜底处理：

```java
if (sqsMessage.getBatchId() == null || sqsMessage.getBatchId().isEmpty()) {
  sqsMessage.setBatchId(messageId);
}
```

所以消费侧不会 NPE。但如果有其他系统或日志分析工具依赖 `batchId` 字段在发送阶段就存在（用于批次关联查询），可能会受到影响。

**建议**：确认下游是否有对发送侧 `batchId` 的依赖。如果没有，当前实现是合理的。

---

### S-2. visibilityTimeout 从 3600 → 600 对已有队列不生效

**文件**：`InitSqsQueueEnum.java` + `SQSServiceImpl.java:49-76`

`InitSqsQueueEnum` 将 `visibilityTimeout` 从 3600（1 小时）改为 600（10 分钟），与 `SQSMessageListener` 中的 visibility 续期机制配合（每 5 分钟延长到 10 分钟）。

但 `SQSServiceImpl.initSqsQueues()` 第 56-58 行对已存在的队列直接跳过：

```java
if (queueExist) {
  log.info("Queue already exists, skipping creation: {}", queueName);
  continue;
}
```

**影响**：已部署环境中队列的 `visibilityTimeout` 仍是旧值 3600。新的 visibility 续期机制虽然能正常工作（因为它直接调用 `ChangeMessageVisibility` 设置为 600），但队列级别的默认值仍然是旧值。

**建议**：如果需要在已有环境上统一，有两种方式：
1. 在 `initSqsQueues()` 中对已存在的队列增加 `SetQueueAttributes` 调用更新 `visibilityTimeout`
2. 通过 AWS 控制台手动修改各环境的队列属性

---

### S-3. JPA 实体直接暴露在 API 响应中

**文件**：`SqsMessageLogController.java:25`

```java
public Result<Page<QueueMessageLog>> list(...)
```

`QueueMessageLog` 继承自 `AbstractCustomEntity`，序列化输出会包含：
- `createdAt`、`createdBy`、`updatedAt`、`updatedBy` 等审计字段
- `messageContent`（完整消息 JSON，可能含 `companyId`、财务数据等业务敏感信息）
- `errorInfo`（完整异常 stackTrace，含内部类名和行号，可能暴露系统架构信息）

**建议**：引入 DTO 层控制输出字段：

```java
@Data
public class QueueMessageLogDTO {
  private String id;
  private String sqsMessageId;
  private String sqsQueueName;
  private String messageBusinessType;
  private Integer messageStatus;
  private String messageType;
  private String companyId;
  private Boolean isDlq;
  private LocalDateTime createdAt;
  // 不暴露 messageContent 和 errorInfo 的完整内容
  // 或提供单独的详情接口按需获取
}
```

---

### S-4. SQL 脚本文件名放在 sprint106 目录下但服务于 sprint107 的代码变更

**文件**：`deploy/upgrade_doc/sprint106/update_sqs_log_tables.sql`

如果这是 sprint107 的功能变更对应的 DDL，脚本应放在 `sprint107` 目录下。如果确实是 sprint106 的遗留变更在 sprint107 中合并，则可以接受。

**建议**：根据实际情况将脚本移到正确的 sprint 目录。

---

## 五、安全性审查

| 维度 | 评估 | 说明 |
|------|------|------|
| SQL 注入 | **无风险** | 旧版 `@Query(nativeQuery=true)` 已移除，全部改为 JPA 标准 CRUD |
| 敏感信息泄露 | **低风险** | `SqsMessageLogController` 返回完整 `messageContent` 和 `errorInfo`（含 stackTrace），通过 GET 接口可读取。建议引入 DTO 控制输出 |
| 异常信息泄露 | **低风险** | `SqsErrorJsonBuilder` 将完整异常类名和 15 帧 stackTrace 存入 DB，不直接暴露给前端，但通过 GET 接口可间接获取 |
| 权限控制 | **需关注** | DELETE 接口无权限保护（见 I-2） |
| XSS | **无风险** | 后端 API，无 HTML 渲染 |
| SSRF | **无风险** | 队列 URL 由内部配置生成，不接受外部输入 |

---

## 六、总结

### 整体评价

这次重构的方向正确，代码质量有明显提升：

- **SQSMessageListener** 从臃肿的 634 行减到 367 行，职责清晰
- **日志模型** 从"创建-更新"双步改为 append-only INSERT，更简洁可靠
- **DLQ 策略** 从无差别重试改为三段式（成功 / 重试 / 最终 DLQ），可观测性大幅提升
- **代码净减 226 行**，在增加功能的同时减少了代码量

### 问题优先级

| 优先级 | 编号 | 一句话描述 | 建议修复时间 |
|--------|------|-----------|-------------|
| **Critical** | C-1 | SQL 脚本遗漏 `message_type` VARCHAR 列 | **合并前必须修复** |
| **Important** | I-1 | 分页参数无上限校验 | 合并前修复 |
| **Important** | I-2 | DELETE 接口无权限控制 | 合并前修复 |
| **Important** | I-3 | MAX_RECEIVE_COUNT 三处硬编码不统一 | 合并前修复 |
| **Important** | I-4 | 预测失败重试策略静默变更 | 合并前确认意图 |
| **Important** | I-5 | Scheduler 全局开关移除 | 合并前确认意图 |
| Suggestion | S-1 | batchId 移除确认下游依赖 | 下个 sprint |
| Suggestion | S-2 | 已有队列 visibilityTimeout 不会自动更新 | 部署时处理 |
| Suggestion | S-3 | JPA 实体直接暴露在 API 响应中 | 下个 sprint |
| Suggestion | S-4 | SQL 脚本目录归属确认 | 合并前确认 |
