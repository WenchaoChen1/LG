# Quickbooks 模块代码审查报告

**审查日期：** 2026-04-13  
**审查范围：** `gstdev-cioaas-web/.../quickbooks/` 全模块  
**参考文档：** QBO Dashboard & Log 功能文档 (1).pdf  
**审查员：** Claude Code  

---

## 总体结论：🔴 阻止合并

发现 1 个 CRITICAL 安全问题（OAuth 凭据明文写入 S3），需要立即修复后才可合并。

---

## 问题清单

### 🔴 CRITICAL — 安全漏洞，阻止合并

#### C-1：OAuth Token 明文写入 S3

**文件：** `infrastructure/client/QuickbooksApiClient.java:73,98`  
**描述：** `refreshToken()` 方法将原始 `refreshToken` 明文放入 `s3Data` Map 并上传至 S3。Token 刷新成功后，响应体（含 `access_token`、`refresh_token`）同样被记录在 `s3Data` 中，最终以 `token_refresh.json` 形式持久化到 S3 Bucket。

```java
// 第 73 行 — 凭据明文进入要上传的 Map
s3Data.put("refreshToken", refreshToken);
// 第 89 行 — responseBody 包含新 access_token + refresh_token
s3Data.put("responseBody", body);
// 第 98 行 — 整体 JSON 存入 result，后续 uploadToS3 写 S3
result.setS3TokenJson(JSON.toJSONString(s3Data));
```

**风险：** 任何有 S3 读取权限的人员均可获取有效 OAuth 凭据，可直接调用 QBO API 读取企业财务数据。  
**修复方案：** 上传前从 `s3Data` 中删除 `refreshToken` 和 `responseBody`，仅保留 `requestUrl`、`responseStatus`、`error` 等非敏感诊断字段。

---

### 🟠 HIGH — Bug / 重大质量问题

#### H-1：`quickbooksTokenExpiredReminderNew()` 正常连接会提前锁死通知标志 ✅ 已修复

**文件：** `fi/service/FinancialSettingServiceImpl.java`  
**描述：** 调用方对 `tokenValid` 有正确的判断，不会向正常公司发送错误邮件。但原代码在 `if/else if` 均不满足时（token 正常、非刚重连），仍会无条件执行末尾的 `hadSendEmail=true` 更新。这导致：若调度器在 token 失效前运行过一次，`hadSendEmail` 已被置为 `true`；之后 `markTokenRefreshFailure()` 不会重置该标志，调度器将永远查不到该公司，**断连通知邮件无法发出**。

**修复方案：** 在 `else` 分支添加 `continue`，仅在实际发送邮件后才更新标志：

```java
} else {
    continue; // 正常连接跳过，保持 hadSendEmail=false，确保后续失效时仍可被调度
}
```

**状态：** ✅ 已修复

---

#### H-2：`setAccount()` 未校验空列表，存在 NPE 风险

**文件：** `application/service/QuickbooksServiceImpl.java:144-146`  
**描述：** `setAccount()` 直接调用 `quickbooksCategoryAccountList.get(0)` 提取 `type` 和 `companyId`，若前端传入空列表将抛出 `IndexOutOfBoundsException`，且未做任何空检查或错误提示。

```java
public Result<Object> setAccount(List<QuickbooksCategoryAccount> quickbooksCategoryAccountList) {
    String type = quickbooksCategoryAccountList.get(0).getType(); // NPE 风险
    String companyId = quickbooksCategoryAccountList.get(0).getCompanyId();
```

**修复方案：** 在方法入口增加 `if (CollUtil.isEmpty(quickbooksCategoryAccountList)) return Result.fail("...")` 校验。

---

#### H-3：`processSync()` / `processMapping()` 未处理连接为 null 的情况

**文件：** `application/service/QuickbooksSyncService.java:87-88, 69-70`  
**描述：** `getQuickbooksConnection(companyId)` 返回的 `qb` 可能为 null（连接记录不存在），但代码直接调用 `qb.getRefreshToken()` 和 `qb.getRealmId()`，必然抛出 NPE。该场景在手动断联后可能发生。

```java
public void processSync(String companyId) {
    QuickbooksConnectionDto qb = quickbooksService.getQuickbooksConnection(companyId);
    // qb 可能为 null，以下代码直接 NPE
    syncAllReports(new TokenState(null, qb.getRefreshToken()), ...);
```

**修复方案：** 在使用 `qb` 之前添加 null 检查，若为 null 则记录错误日志并直接返回。

---

#### H-4：`getConnections()` 全量加载日志，存在性能风险

**文件：** `application/service/QuickbooksLogsServiceImpl.java:118-121`  
**描述：** `getConnections()` 通过 `findAllByCompanyIdInAndActionInAndShowToUserIsTrueOrderByCreatedAtDesc` 加载**所有公司**的**全部**匹配日志记录到内存，再在 Java 侧做 `.limit(5)` 截断。对于日志量大的 Portfolio 而言，可能一次性加载数万条记录。Repository 中已有 `findTop5ByCompanyId...` 方法，但未被使用。

```java
// 当前：全量加载，Java 内 limit
List<QuickbooksLogs> allLogs = quickbooksLogsRepository
    .findAllByCompanyIdInAndActionInAndShowToUserIsTrueOrderByCreatedAtDesc(companyIds, actionList);
// ...
List<QuickbooksLogs> top5 = companyLogs.stream().limit(5).toList();
```

**修复方案：** 为每家公司单独查询 Top 5（利用已有 Repository 方法），或在原查询中以 `LIMIT N * 公司数量` 进行数据库侧截断。

---

#### H-5：`getConnectionsPage()` 存在 N+1 查询问题

**文件：** `application/service/QuickbooksLogsServiceImpl.java:183-187`  
**描述：** 分页查询结果在 `page.map()` 回调中为每条日志单独调用 `userService.findByUserId()`，触发 N+1 查询。

```java
return page.map(log -> {
    // 每次循环都单独查一次用户
    User user = ObjectUtil.isEmpty(log.getCreatedBy()) ? null
        : userService.findByUserId(log.getCreatedBy());
```

**修复方案：** 先收集所有 `createdBy` 批量查用户，再 map 进结果（`getLogs()` 方法中已有正确做法，参照即可）。

---

### 🟡 MEDIUM — 可维护性 / 逻辑隐患

#### M-1：`conversionMode()` 中 if/else 注释与逻辑方向相反

**文件：** `application/service/QuickbooksLogsServiceImpl.java:241-248`  
**描述：** 注释 `// Manual to Auto` 出现在 action 为 `SWITCH_AUTO_TO_MANUAL` 的分支，注释与实际行为完全相反，极易引起维护时的误操作。

```java
if (companyQuickbooks.getMode().equals("Manual")) {// Manual to Auto  ← 注释错误
    quickbooksLogs.setAction(QBOLogEnum.SWITCH_AUTO_TO_MANUAL.getCode()); // 实际：Auto→Manual
} else {// Auto to Manual  ← 注释错误
    quickbooksLogs.setAction(QBOLogEnum.SWITCH_MANUAL_TO_AUTO.getCode()); // 实际：Manual→Auto
```

**修复方案：** 将注释改为 `// new mode is Manual → was Auto before → Auto to Manual` 和 `// new mode is Auto → was Manual before → Manual to Auto`。

---

#### M-2：`handleTokenRefreshFailed()` 写入误导性的 "BEGIN" 日志

**文件：** `application/service/QuickbooksSyncService.java:212-221`  
**描述：** Token 刷新已经失败，但 `handleTokenRefreshFailed()` 仍先写一条 `REFRESH_TOKEN_BEGIN status=true` 的成功日志，再写 `REFRESH_TOKEN_END status=false` 的失败日志。Dashboard 展示时用户会看到一条状态矛盾的"成功开始"记录。

**修复方案：** 仅在实际开始 Token 刷新时写 BEGIN 日志（位于 `callApi()`），失败回调中直接写 `REFRESH_TOKEN_END status=false`，不要重复写 BEGIN。

---

#### M-3：`updateQuickbooksConnection(QuickbooksConnectionDto)` 可能变成 INSERT

**文件：** `application/service/QuickbooksServiceImpl.java:235-239`  
**描述：** 该方法先查出连接确认存在，然后通过 Mapper 将 DTO 转换为新 Entity 再 `save()`。若 Mapper 未保留原始 Entity 的主键 `id`，JPA 会将其当作新记录插入，导致数据重复。

**修复方案：** 改为先查出现有 Entity，再直接 set 字段后 save，或确认 Mapper 正确映射 id 字段。

---

#### M-4：`QuickbooksConnection` 缺少审计字段，`sendEmailDate` 类型不规范

**文件：** `domain/entity/QuickbooksConnection.java`  
**描述：** 该 Entity 无 `createdAt` / `updatedAt`，与 `QuickbooksLogs` 的审计规范不一致。`sendEmailDate` 使用 `String` 而非 `Instant` / `LocalDate`，无法参与日期范围查询。

---

#### M-5：`getConnections()` 中无日志时的 status 默认值不准确

**文件：** `application/service/QuickbooksLogsServiceImpl.java:166`  
**描述：** 当某公司无可展示日志时，状态回退为 `"Manual"` 或 `"Offline"`；但若公司连接正常（mode = `"Automatic"`），此时返回 `"Offline"` 与实际状态不符，Dashboard 会误显红色。

```java
String status = !logList.isEmpty() ? ...
    : companyQuickbooks.getMode().equals("Manual") ? "Manual" : "Offline"; // Automatic 会错误显示 Offline
```

**修复方案：** 增加 `"Online"` 的回退分支：`mode 为 Automatic 且 tokenValid=true → "Online"`。

---

### 🟢 LOW — 风格 / 细节建议

#### L-1：多处 catch 块使用 `log.info` 记录异常

**文件：** `QuickbooksController.java:32,44,55,68`；`QuickbooksServiceImpl.java:174,199,211`  
**描述：** Exception 被捕获后用 `log.info(e.getMessage(), e)` 记录，应改为 `log.error` 以便监控系统正确报警。

---

#### L-2：`FinancialSettingService` 字段注释残留

**文件：** `application/service/QuickbooksServiceImpl.java:56`  
**描述：** `// Changed from private to public for visibility` 是调试时遗留的注释，应删除。

---

#### L-3：Repository 中 `findTop5...` 方法未被使用

**文件：** `domain/repository/QuickbooksLogsRepository.java:17`  
**描述：** `findTop5ByCompanyIdAndActionInAndShowToUserIsTrueOrderByCreatedAtDesc` 存在但未使用，考虑与 H-4 的修复一并纳入。

---

#### L-4：`callApi()` 对所有非 200 响应均触发 Token 刷新

**文件：** `infrastructure/client/QuickbooksApiClient.java:135-143`  
**描述：** 404/500 等与认证无关的错误也会触发 Token 刷新，浪费刷新次数，也会导致与实际问题不相关的刷新日志。建议仅对 401 触发刷新逻辑。

---

## 功能需求符合性检查

| 需求项 | 实现状态 | 备注 |
|--------|----------|------|
| Dashboard 展示各公司 QBO 连接状态 | ✅ 已实现 | `getConnections()` |
| 点击展开查看详细日志（错误信息 + 时间戳 + 载荷） | ✅ 已实现 | `getConnectionsPage()` + `getLogs()` |
| 实时更新（无需手动刷新） | ⚠️ 未见实现 | 未发现 WebSocket / SSE 推送机制，需前端轮询或后端推送 |
| Token 失效时发送断连通知邮件 | ⚠️ 部分实现 | `hadSendEmail` 标志存在，但查询逻辑有 Bug（见 H-1） |
| 连接恢复时发送确认邮件 | ⚠️ 待确认 | `tokenInvalidToValid` 字段已设计，需确认邮件服务是否已完整实现 |
| 完整记录每次同步事件（状态/错误/载荷） | ✅ 已实现 | `writeLog()` + QBOLogEnum |
| 手动断联后重连同账号同公司不需重新配置匹配项 | ✅ 已实现 | `syncAccountMapping()` 读取现有 `catAccounts` 并复用 |
| 手动断联后重连换账号/换公司需重新配置 | ✅ 已实现 | 新 `companyId` / `realmId` 时账号映射会重建 |
| PGM/PM 权限控制 | ⚠️ 未见接口层注解 | Controller 上未发现 `@PreAuthorize` 权限校验 |

---

## 亮点

1. **`getConnections()` 已完整消除 N+1**：通过批量加载 `CompanyQuickbooks`、日志和用户信息，为 Portfolio 级别的 Dashboard 请求提供了良好的性能保障（仅 `getConnectionsPage` 存在 N+1 残留）。
2. **QBOLogEnum 设计清晰**：枚举覆盖完整操作链路（创建、连接、断联、模式切换、Token 刷新、同步），`getLabelByCode()` 为前端展示提供了友好标签。
3. **QuickbooksApiClient 的 Token 自动刷新重试机制**：一次失败后自动刷新 Token 并重试，对上层透明，设计合理。
4. **日志写入保护**：所有日志写入方法均有 try-catch 保护，避免日志失败影响主业务流程。
5. **TransactionTemplate 的使用**：Token 刷新成功/失败后的多步数据库操作通过 `transactionTemplate.executeWithoutResult` 封装在一个事务内，保证原子性。

---

## 修复优先级清单

- [ ] **C-1** 立即修复：从 S3 上传内容中删除 OAuth Token 明文字段
- [x] **H-1** ✅ 已修复：`else { continue; }` 确保只有实际发送邮件后才更新 `hadSendEmail` 标志
- [ ] **H-2** 修复 `setAccount()` 空列表入参校验
- [ ] **H-3** 修复 `processSync()` / `processMapping()` 的 null 检查
- [ ] **H-4** 优化 `getConnections()` 的日志加载策略（数据库侧 limit）
- [ ] **H-5** 修复 `getConnectionsPage()` N+1 查询
- [ ] **M-1** 修正 `conversionMode()` 中的错误注释
- [ ] **M-2** 修正 Token 刷新失败时的日志写入顺序
- [ ] **M-3** 确认 `updateQuickbooksConnection()` 的 Mapper 是否保留 id
- [ ] **M-4** 为 `QuickbooksConnection` 添加审计字段，修正 `sendEmailDate` 类型
- [ ] **M-5** 修复无日志时状态默认值逻辑
- [ ] **功能** 确认实时推送需求是否需后端 SSE/WebSocket 实现
- [ ] **功能** 确认 Controller 层权限注解（PGM/PM 限制）是否已在网关/过滤器层实现
