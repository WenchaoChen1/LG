# SQS & Scheduler 模块代码审查报告

**审查日期**: 2026-03-25
**审查范围**: `sqs/` 和 `scheduler/` 两个模块的全部 Java 源码
**审查标准**: 安全性、设计合理性、错误处理、代码质量、潜在 Bug

---

## 一、严重问题（需尽快修复）

### 1.1 [BUG] ScheduleProcessor 生产代码使用 MockHttpServletRequest

**文件**: `scheduler/service/ScheduleProcessor.java:223-226`
```java
case SaveCompanyQuickbooksDataEveryday:
    MockHttpServletRequest request = new MockHttpServletRequest();
    ServletRequestAttributes attributes = new ServletRequestAttributes(request);
    RequestContextHolder.setRequestAttributes(attributes, true);
    quickbooksService.companyDataEveryday("", null);
    User user = new User();
    user.setId(SchedulerConstants.DEFAULT_SYSTEM_USER_ID);
    user.setCurrency(SchedulerConstants.DEFAULT_CURRENCY);
    quickbooksService.companyDataEveryday("", user);
```

**问题**:
1. `MockHttpServletRequest` 是 `spring-test` 的类，出现在生产代码中是严重的设计缺陷。意味着生产运行时依赖 test scope 的 jar（如果 pom 中 scope 不是 compile 则运行时会 ClassNotFoundException）
2. `companyDataEveryday` 被调用了**两次** —— 第一次传 `null` user，第二次传一个伪造的 User。第一次调用如果依赖 user 会抛异常或产生脏数据；如果不依赖 user 则是冗余调用
3. 底层 service 不应强依赖 `HttpServletRequest`，应重构为不依赖 HTTP 上下文

**建议**: 重构 `QuickbooksService.companyDataEveryday()` 接口，去除对 `HttpServletRequest` 的隐式依赖。移除 MockHttpServletRequest。修复双重调用。

---

### 1.2 [BUG] sendMessage 静默丢消息

**文件**: `sqs/service/SQSServiceImpl.java:137-140`
```java
if (!checkQueueExist(queueName)) {
    log.error("Cannot send message — queue does not exist: {}", queueName);
    return;  // 消息被静默丢弃，调用方不知情
}
```

**问题**: 当队列不存在时，方法只 log.error 然后 return。调用方没有任何反馈（不抛异常、不返回 false），消息被静默丢弃。在业务流程中这可能导致数据不一致。

**建议**: 抛出业务异常（如 `SqsException`），让调用方决定如何处理。

---

### 1.3 [安全] AWS 凭证使用方式不当

**文件**:
- `sqs/config/SqsAutoConfiguration.java:34-35`
- `scheduler/config/ScheduleAutoConfiguration.java:38-39`

```java
AwsBasicCredentials.create(queueProperties.getAccessKey(), queueProperties.getSecretKey())
```

**问题**: 两个模块都使用 `StaticCredentialsProvider` + `AwsBasicCredentials` 硬编码凭证方式。在 AWS EC2/ECS 部署环境中应使用 IAM Role + `DefaultCredentialsProvider` 链，避免在配置中传递 AccessKey/SecretKey。

**建议**: 部署在 AWS 时改用 `DefaultCredentialsProvider.create()`，仅在本地开发时通过环境变量或 profile fallback 到 static credentials。

---

## 二、设计问题（影响可维护性）

### 2.1 ScheduleProcessor 是 God Class

**文件**: `scheduler/service/ScheduleProcessor.java`

注入了 **10 个 `@Lazy @Resource` 业务 Service**（CompanyQuickbooksService、QuickbooksService、CompanyService、CurrencyService、FinancialGrowthRateService 等），并通过一个 270 行的 `switch` 分发到各个 Service。

**问题**:
- 违反单一职责原则 —— 一个类知道所有业务域的细节
- 添加新的 schedule type 需要修改此文件（违反开闭原则）
- 长 switch 可读性差，容易遗漏新枚举值

**建议**: 使用策略模式。每个 schedule type 实现一个 `ScheduleHandler` 接口，注册到 Map 中按 type 分发。类似 `MessageProcessor` 的设计，但粒度更细。

---

### 2.2 initFixedSchedulerBean 返回 dummy String

**文件**: `scheduler/config/ScheduleAutoConfiguration.java:53-58`
```java
@Bean
@DependsOn("sqsMessageListener")
public String initFixedSchedulerBean() {
    scheduleProcessor.initFixedScheduler();
    return "fixedSchedulerInitialized";
}
```

**问题**: 用 `@Bean` 注册一个 String 常量只为触发初始化逻辑，是 Spring 反模式。会污染 BeanFactory（一个 String bean 会被其他地方意外注入）。

**建议**: 改用 `@EventListener(ApplicationReadyEvent.class)` 或实现 `SmartLifecycle` 接口。

---

### 2.3 sendMessage 重复查询队列 URL

**文件**: `sqs/service/SQSServiceImpl.java:128-142`

```java
// 第一次: checkQueueExist → getQueueUrl (网络调用)
if (!checkQueueExist(queueName)) { ... }
// 第二次: sendMessageToSqs → getQueueUrl (又一次网络调用)
String sqsMessageId = sendMessageToSqs(queueName, messageJson, groupId, delaySeconds);
```

**问题**: 每次发送消息都会调用 2 次 `getQueueUrl`（AWS API 调用），造成不必要的延迟和 API 配额消耗。

**建议**: 将 `getQueueUrl` 结果缓存（queue URL 在运行期内不会变化），或合并为一次调用。

---

### 2.4 extractCompanyId 重复实现

**文件**:
- `sqs/listener/SQSMessageListener.java:274-279`
- `sqs/service/SQSServiceImpl.java:160-166`

两处代码完全相同:
```java
private static String extractCompanyId(String messageBody) {
    try {
        return cn.hutool.json.JSONUtil.parseObj(messageBody).getStr("companyId");
    } catch (Exception e) {
        return null;
    }
}
```

**建议**: 提取到 `SQSUtils` 工具类中。

---

### 2.5 定时任务时间冲突

**文件**: `scheduler/enums/FixedScheduleTypeEnum.java`

| 时间 (UTC) | 同时执行的任务 |
|------------|-------------|
| **每天 00:00** | `CheckCurrencyRate` + `Build24MonthsForecastData` |
| **每天 01:00** | `SaveAllCompanyScore` + `FinancialNormalizationScheduler` + `CheckAutoFillCommittedForecast` + `LoadCurrencyRate` |

**问题**: 多个重量级任务堆积在同一时间段启动（尤其是 01:00 有 4 个任务），可能造成数据库连接池压力、CPU 飙升、或 SQS 消费线程饱和。

**建议**: 错开任务时间。例如 `SaveAllCompanyScore` 01:00、`FinancialNormalizationScheduler` 01:30、`CheckAutoFillCommittedForecast` 02:00。

---

## 三、错误处理问题

### 3.1 getQueueUrl 静默吞异常

**文件**: `sqs/service/SQSServiceImpl.java:432-442`
```java
public String getQueueUrl(String queueName) {
    try { ... }
    catch (Exception e) {
        return null;  // 无任何日志
    }
}
```

**问题**: 所有异常（网络超时、权限不足、SDK 错误等）都被静默吞掉返回 null。调用方无法区分"队列不存在"和"AWS 暂时不可用"。

**建议**: 区分 `QueueDoesNotExistException`（返回 null）和其他异常（log + 抛出或返回特殊值）。

---

### 3.2 initSqsQueues 用 log.info 记录创建失败

**文件**: `sqs/service/SQSServiceImpl.java:83-85`
```java
} catch (Exception ex) {
    log.info("Queue creation failed: {}, eventTime={}", queueName, Instant.now());
    // 异常被吞没，没有 log.error(ex)
}
```

**问题**: 队列创建失败是严重事件，但只用 `log.info` 记录且没有打印堆栈。生产环境中如果队列创建失败，很难从 info 日志中发现问题。

**建议**: 改为 `log.error("Queue creation failed: {}", queueName, ex)`。

---

### 3.3 SchedulerServiceImpl 日志级别混乱

**文件**: `scheduler/service/SchedulerServiceImpl.java`

多处对同一事件同时输出 info + error 两行日志：
```java
// createSchedule 失败 (line 52-53)
log.info("Schedule creation failed: ...");
log.error("Failed to create schedule in AWS EventBridge: ...", e);

// updateSchedule 失败 (line 272-273)
log.info("Schedule update failed: ...");
log.error("Failed to update schedule: ...", exception);

// deleteSchedule 失败 (line 306-307)
log.info("Schedule deletion failed: ...");
log.error("Failed to delete schedule from AWS EventBridge: ...", exception);
```

**问题**: 同一个失败事件输出两行不同级别的日志，`log.info` 行多余且误导（info 通常表示正常流程）。

**建议**: 只保留 `log.error`，移除 `log.info` 行。

---

### 3.4 updateSchedule 缺少补偿事务

**文件**: `scheduler/service/SchedulerServiceImpl.java:277-287`

```java
// AWS 更新成功后，DB 写入失败时
if (StringUtils.isNotBlank(schedulerArn)) {
    try {
        transactionTemplate.execute(status -> { ... });
    } catch (Exception e) {
        log.error("Failed to update schedule config...");
        throw e;  // 但 AWS 侧已经更新了，没有回滚
    }
}
```

**对比** `createSchedule` 有补偿逻辑（DB 失败则删除 AWS schedule），但 `updateSchedule` 没有。DB 失败后 AWS 侧的修改不会被回滚，导致 AWS 和 DB 状态不一致。

**建议**: 添加补偿逻辑：DB 失败时用旧的 `scheduleResponse` 恢复 AWS schedule。

---

### 3.5 switch default 静默跳过

**文件**: `scheduler/service/ScheduleProcessor.java:269-270`
```java
default:
    break;
```

**问题**: 如果新增 `FixedScheduleTypeEnum` 枚举值但忘记更新 switch，消息会被静默消费（标记为成功）但不执行任何业务逻辑。

**建议**: 改为 `throw new IllegalStateException("Unhandled schedule type: " + scheduleTypeEnum)`。

---

## 四、代码质量问题

### 4.1 每次启动都删除 FIFO 队列

**文件**: `sqs/service/SQSServiceImpl.java:54`
```java
deleteQueue(queueName + ".fifo");
```

**问题**: 每次应用启动都尝试删除所有队列的 FIFO 版本。这是遗留迁移代码（从 FIFO 迁移到 STANDARD），但每次启动都执行，产生不必要的 AWS API 调用和日志噪音。

**建议**: 如果迁移已完成，移除此代码。如果仍需要，加一个 feature flag 控制。

---

### 4.2 destroy() 中硬编码 Thread.sleep

**文件**:
- `sqs/config/SqsAutoConfiguration.java:55` — `Thread.sleep(5000)`
- `sqs/listener/SQSMessageListener.java:169` — `Thread.sleep(5000)`

**问题**: 总共 10 秒的硬编码 sleep（两处各 5 秒），延长了应用关闭时间。没有实际的条件判断，纯粹是"等一会儿希望异步操作结束"。

**建议**: 使用 `CountDownLatch` 或 `CompletableFuture` 等待实际操作完成，或至少减少等待时间。

---

### 4.3 getQueueArn 过度查询

**文件**: `sqs/service/SQSServiceImpl.java:449-453`
```java
public String getQueueArn(String queueName) {
    QueueInfo queueInfo = getQueue(queueName);  // 查询 ALL 属性
    return queueInfo.getQueueArn();
}
```

**问题**: `getQueue()` 请求了 `QueueAttributeName.ALL`（所有属性），但 `getQueueArn()` 只需要 ARN。

**建议**: 单独实现，只请求 `QueueAttributeName.QUEUE_ARN`。

---

### 4.4 getVisibilityTimeout / getMaxReceiveCount 线性遍历

**文件**: `sqs/listener/SQSMessageListener.java:296-318`

每次处理消息都遍历 `InitSqsQueueEnum.values()` 来查找配置。消息量大时，这是不必要的开销。

**建议**: 在 `initListener()` 时构建 `Map<String, Integer>` 缓存。

---

### 4.5 重复的 groupName 空值处理

**文件**: `scheduler/service/SchedulerServiceImpl.java`

以下代码在 5 个方法中重复出现：
```java
StringUtils.isNotBlank(scheduleProperties.getGroupName()) ? scheduleProperties.getGroupName() : null
```

**建议**: 提取为 `private String getGroupName()` 方法，或在 `ScheduleProperties` 中处理。

---

### 4.6 visibilityTimeoutExtension 首次延迟为 0

**文件**: `sqs/listener/SQSMessageListener.java:355-356`
```java
ScheduledFuture<?> future = visibilityTimeoutExecutor.scheduleAtFixedRate(
    extensionTask, 0, extendIntervalSeconds, TimeUnit.SECONDS);
```

**问题**: `initialDelay = 0` 意味着消息刚接收就立即延长 visibility timeout，此时还没开始处理。虽然不会导致错误，但浪费一次 API 调用。

**建议**: 将 `initialDelay` 设为 `extendIntervalSeconds`（即到一半时间时才首次续期）。

---

## 五、问题汇总

| 编号 | 严重程度 | 类别 | 问题 | 位置 |
|------|---------|------|------|------|
| 1.1 | **严重** | Bug | MockHttpServletRequest 用于生产 + 双重调用 | ScheduleProcessor:223-230 |
| 1.2 | **严重** | Bug | sendMessage 静默丢消息 | SQSServiceImpl:137-140 |
| 1.3 | **严重** | 安全 | AWS 硬编码凭证 | SqsAutoConfiguration:34, ScheduleAutoConfiguration:38 |
| 2.1 | 中 | 设计 | ScheduleProcessor God Class | ScheduleProcessor 全文件 |
| 2.2 | 低 | 设计 | initFixedSchedulerBean 返回 dummy String | ScheduleAutoConfiguration:53-58 |
| 2.3 | 中 | 性能 | sendMessage 重复查询 queue URL | SQSServiceImpl:137+142 |
| 2.4 | 低 | 质量 | extractCompanyId 重复实现 | SQSMessageListener:274, SQSServiceImpl:160 |
| 2.5 | 中 | 设计 | 定时任务时间冲突 (01:00 堆积 4 个) | FixedScheduleTypeEnum |
| 3.1 | 中 | 错误处理 | getQueueUrl 静默吞异常 | SQSServiceImpl:432-442 |
| 3.2 | 中 | 错误处理 | initSqsQueues 用 info 记录失败 | SQSServiceImpl:83-85 |
| 3.3 | 低 | 质量 | SchedulerServiceImpl 日志级别混乱 | SchedulerServiceImpl 多处 |
| 3.4 | 中 | 错误处理 | updateSchedule 缺少补偿事务 | SchedulerServiceImpl:277-287 |
| 3.5 | 中 | Bug | switch default 静默跳过 | ScheduleProcessor:269-270 |
| 4.1 | 低 | 质量 | 每次启动删 FIFO 队列（遗留代码） | SQSServiceImpl:54 |
| 4.2 | 低 | 质量 | destroy() 硬编码 sleep 10s | SqsAutoConfiguration:55, SQSMessageListener:169 |
| 4.3 | 低 | 性能 | getQueueArn 查询所有属性 | SQSServiceImpl:449-453 |
| 4.4 | 低 | 性能 | 每次消息处理线性遍历枚举 | SQSMessageListener:296-318 |
| 4.5 | 低 | 质量 | groupName 空值处理重复 5 次 | SchedulerServiceImpl 多处 |
| 4.6 | 低 | 质量 | visibility 首次续期延迟为 0 | SQSMessageListener:355-356 |

---

## 六、正面评价

以下设计合理，值得保留：

1. **Per-Queue 隔离架构** — 每个队列独立线程池 + Semaphore，避免跨队列干扰
2. **背压机制** — 80% 暂停、50% 恢复的滞后策略，避免抖动
3. **REQUIRES_NEW 独立事务日志** — 确保日志不受业务事务回滚影响
4. **Visibility Timeout 续期** — 长任务不会被 SQS 误判为超时
5. **自然重试延迟** — 失败后不立即重试，等 visibility timeout 过期
6. **补偿事务** — createSchedule 中 DB 失败回滚 AWS（但 update 缺失）
7. **Structured Error JSON** — 错误日志结构化存储，便于排查
8. **Stale Schedule 清理** — 每次启动同步枚举与 AWS 状态
