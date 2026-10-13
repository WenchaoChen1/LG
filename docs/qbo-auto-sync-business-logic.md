# QBO 连接与自动数据拉取 — 业务逻辑文档

> 范围：**自动模式（Automatic）** 下，从用户点击连接到数据入库的完整链路，以及入库后的下游使用。
>
> 按代码现状整理（2026-10-13，Java `sprint121`）。旧版描述的 ETL 服务 + Redshift + 每公司 EventBridge 调度已下线：QBO 数据已迁回 PostgreSQL，由 Java Web 服务自己调 QBO API。
>
> 关联文档：[QBO Dashboard & Log 测试用例](./Quickbooks%20连接+定时拉取%20log+同步规则/QBO%20Dashboard%20&%20Log_测试用例.md)

---

## 1. 流程总览

```
公司设置 Finance 页签切到 Automatic → 点击连接
  → OAuth 授权（Intuit）
  → OAuth Callback：换取 Token、保存连接 → 发 SQS「Mapping」消息
  → 只拉科目表（AccountList）→ 用户在 /financeSetting 做科目映射
  → 保存映射 → 发 SQS「Sync」消息 → 全量同步（科目表 + 利润表 + 资产负债表 + 关账日期）→ 写入 PostgreSQL
  → 每天定时全量同步一次
  → 同步成功后：重建标准化数据 → Benchmark / 增长率 / 预测等下游刷新
```

所有拉取都在 `gstdev-cioaas-web` 进程内完成：SQS 只用于异步解耦，不经过其他服务。

---

## 2. OAuth 连接流程

### 2.1 前置：选择 Automatic 模式

| 项目 | 说明 |
|------|------|
| 页面 | `/companySetting` → Finance 页签 → Edit Entry Setting（管理端与公司端共用同一页面） |
| 接口 | `POST /companyQuickbooks/conversionMode` |
| 提示 | 切到 Automatic 前须勾选确认：手工数据会被覆盖，QBO 中没有数据的月份显示为 0 |

模式切换的数据影响见 §7。

### 2.2 发起授权

| 项目 | 说明 |
|------|------|
| 接口 | `GET /companyQuickbooks/connect?companyId=`（只记 `CLICK_CONNECT_QBO` 日志）→ 前端整页跳转 `GET /companyQuickbooks/authorization?companyId=&roleType=&userId=` |
| Controller | `FinancialSettingController`（`@RequestMapping("/companyQuickbooks")`） |
| Service | `FinancialSettingServiceImpl.authorization()` |

处理逻辑：
1. 用 `cio.quickbooks.clientId / clientSecret / environment` 构建 Intuit SDK 的 `OAuth2Config`。`environment=SANDBOX` 时连沙箱，其他值连生产。
2. 授权范围：`Scope.Accounting`。
3. `state = companyId + "," + roleType + "," + userId`，回调时据此恢复上下文。
4. 302 重定向到 Intuit 授权页。

### 2.3 OAuth Callback

| 项目 | 说明 |
|------|------|
| 接口 | `GET /companyQuickbooks?code=&realmId=&state=`（`@AnonymousAccess`） |
| Service | `FinancialSettingServiceImpl.findById()` |

处理逻辑：
1. 解析 `state`，得到 `companyId`、`roleType`、`userId`。`code` 或 `realmId` 为空时记 `CONNECT_QBO_FAILED` 并跳回公司设置页。
2. **换取 Token**：`OAuth2PlatformClient.retrieveBearerTokens(code, redirectUri)`。
3. **换了 QBO 公司**（新 `realmId` 与原来的不同）：清空科目映射和全部 QBO 数据表。
4. 更新 `company_quickbooks`：
   - `realmId`、`refreshToken`、`status="success"`、`isFirst=true`
   - 首次连接时 Payroll 拆分比例取默认值 S&M 34 / G&A 33 / R&D 33
5. 记录 `CONNECT_QBO_SUCCESS` 日志。
6. 保存 `quickbooks_connection`（access / refresh token，`token_valid=true`），并把 Token 响应备份到 S3。
7. **发 SQS Mapping 消息**：只拉科目表，供用户映射。
8. 重定向到前端 `/financeSetting?id={companyId}&stepType=Expenses&tableType=1`，进入科目映射向导。

### 2.4 断开连接

- 接口：`POST /companyQuickbooks/disconnect`。
- 效果：`company_quickbooks.status="fail"`，清空 `payrollConfig`，删除 `quickbooks_connection`，记 `CLICK_DISCONNECT_QBO` 日志。
- 断开后每日同步不再处理该公司。

---

## 3. 科目映射（Account → Category）

QBO 的科目名每家公司都不一样，必须靠映射才能算出各类费用、现金等指标。

| 接口（`QuickbooksController`，`/quickbooks`） | 用途 |
|------|------|
| `GET /accountList?companyId=&accountType=Expenses\|Asset` | 已拉取的科目、当前归类、`mapping_status`；前端在导入期间每 60 秒轮询一次 |
| `GET /getCategory?type=` | 分类下拉选项 |
| `POST /setAccount` | 整体替换该类型的映射，返回没有分到科目的分类；**保存后发 SQS Sync 消息** |
| `GET /getCompanyAccount` | 按分类分组的映射结果，显示在 Finance 页签 |

分类（`quickbooks_category`，数据在库里，仓库 SQL 未种子化）：

| type | 分类 |
|------|------|
| Expenses | Payroll Expenses、S&M Expenses、R&D Expenses、G&A Expenses、Other Expenses |
| Asset | Cash、R&D (Capitalized) |

前端校验：每个费用科目都必须归类，至少一个资产科目归到 Cash。

向导分三步：导入数据 → 分配费用科目 → 分配资产科目。

`accountType` 的取值范围：
- Expenses：QBO 科目类型为 Expenses 的科目。
- Asset：应收、其他流动资产、银行、固定资产、其他资产。

---

## 4. 触发与调度（SQS）

### 4.1 触发时机

| 触发 | 发送的消息 |
|------|-----------|
| OAuth 回调成功 | Mapping |
| 保存科目映射（`/quickbooks/setAccount`） | Sync |
| 修改 Payroll 科目（`/companyQuickbooks/updatePayroll`，前端目前无入口） | Sync |
| 手动刷新（`GET /companyQuickbooks/refresh`，前端入口是 Company Overview 的 "Books Are Past Due" 弹窗） | Mapping + Sync |
| 每日定时 `QuickbooksSync`，`cron(0 3 * * ? *)`，调度默认时区 UTC | 每家符合条件的公司一条 Sync |

每日定时只处理同时满足以下条件的公司：
- `company_quickbooks.mode='Automatic'`
- `status='success'`
- 公司处于活跃状态

> 状态变成 `Invalid` 的公司**不会**被每日同步拉取，直到用户手动刷新或重新连接（见 §6）。

### 4.2 队列与消费

| 消息 | 队列 | 消费者 | 执行 |
|------|------|--------|------|
| `messageType=QuickbooksMapping` | `quickbooks-mapping-queue` | `QuickbooksMappingProcessor` | `QuickbooksSyncService.processMapping()` |
| `messageType=QuickbooksSync` | `quickbooks-scheduler-queue` | `QuickbooksSyncProcessor` | `QuickbooksSyncService.processSync()` |

- 监听入口：`SQSMessageListener`；按 `messageType` 路由到对应的 Processor。
- 消息体：`QuickbooksSyncMessageDto`（`companyId`、`realmId`、`queueName`）。
- 发送方：`QuickbooksSqsProcessor`（`sendMappingMessage` / `sendSyncMessage` / `syncAllQuickbooksData`）。

---

## 5. 数据同步

### 5.1 HTTP 客户端与 Token

客户端是 `QuickbooksApiClient`：Apache HttpClient，超时 60 秒。

| 项目 | 说明 |
|------|------|
| Base URL | 沙箱 `https://sandbox-quickbooks.api.intuit.com`，生产 `https://quickbooks.api.intuit.com` |
| 认证 | `Authorization: Bearer {accessToken}`，取 `quickbooks_connection` 中保存的 access token |
| Token 刷新 | `POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`，Basic Auth（`Base64(clientId:clientSecret)`），参数 `grant_type=refresh_token` |
| 刷新时机 | **按需刷新**：同步前不预先刷新。5xx、429、网络异常/超时属瞬时错误，**不刷新 token**，同 token 等 2s 再试 1 次（QBO 队列可见性超时 120s，单次调用不能比旧路径更久），仍失败即本次同步失败（照旧置 `Invalid`）；401 及其余 4xx 刷新一次 token 后重试一次（重试中遇瞬时错误同样再试 1 次，不再二次刷新）。刷新 token 接口本身无重试 |

刷新成功：
- 新 Token 立即写回 `quickbooks_connection`（`token_valid=true`），`company_quickbooks.status="success"`。
- 记 `REFRESH_TOKEN_BEGIN/END` 日志。
- 备份到 S3。

刷新失败：
- `company_quickbooks.status="Invalid"`，`quickbooks_connection.token_valid=false`。
- 记失败日志，本次同步中止。

### 5.2 processMapping（只拉科目）

1. `quickbooks_connection.mapping_status = mapping_processing`。
2. 拉 `GET /v3/company/{realmId}/reports/AccountList`。
3. 用已有映射重建 `quickbooks_category_account`：
   - 按科目名匹配；
   - 用科目名后缀（`:` 之后的部分）回填科目编号。
4. 结果：
   - 成功：`mapping_status=success`，`company_quickbooks.status=success`。
   - 失败：`mapping_status=fail`，`company_quickbooks.status=Invalid`。

### 5.3 processSync（全量同步）

`sync_status = sync_processing`，然后依次执行：

| # | QBO 接口 | 解析出的内容 | 写入表 |
|---|---------|-------------|--------|
| 1 | `GET .../reports/AccountList` | 科目编号、名称、类型、明细类型、余额 | `quickbooks_account_list_detail`、`quickbooks_category_account` |
| 2 | `GET .../reports/ProfitAndLoss?summarize_column_by=Month&start_date=&end_date=` | 每月 total_income、cogs、gross_profit、total_expenses、net_income；按费用映射汇总出 payroll、sm_expense、rd_expense、ga_expense、otherExpenses | `quickbooks_profit_and_loss` |
| 3 | `GET .../reports/BalanceSheet?summarize_column_by=Month&start_date=&end_date=` | 每月 assets（`TotalAssets` 合计）、liabilities（`Liabilities` 合计，不含权益；无该分组记 `0.00`，此字段无业务读方）；按分组代码取应收（`AR`）、应付（`AP`）、长期债务（`LongTermLiabilities`）、其他资产（`OtherCurrentAssets`，缺则 `FixedAssets`）、其他负债（`OtherCurrentLiabilities`），无已知代码时按分节标题文字兜底；按资产映射汇总出 cash、rd_capitalized | `quickbooks_balance_sheet` |
| 4 | 由 #2、#3 生成 | 同利润表、资产负债表，另带 `realm_id`、`pull_time` | `quickbooks_profit_and_loss_log`、`quickbooks_balance_sheet_log` |
| 5 | `GET .../query?query=select * from Preferences&minorversion=65`（XML） | 只取 `BookCloseDate`（账本关账日期） | `quickbooks_close_date` |

- **时间范围**：今年往前 4 年的 1 月 1 日 ~ 今年 12 月 31 日，按月分列（`QuickbooksApiClient.buildDateRange`）。
- **Other Expenses 的处理**：利润表里，Other Expenses 分类的合计会**覆盖** `other_income`，并从 `total_expenses` 中扣除。
- **响应格式（Reports API v2，2026-09-01 起唯一后端，2026-10-13 用沙箱实测）**：
  - P&L 列 = 科目列 + 每月一列 + 末列 `Total`（`MetaData` 只有 `ColKey=total`）；BS 无 `Total` 列。月份列按 `MetaData` 里有无 `StartDate`/`EndDate` 识别，不按位置。
  - 顶层分组：P&L 为 `Income`、`COGS`、`GrossProfit`、`Expenses`、`NetOperatingIncome`、`OtherExpenses`、`NetOtherIncome`、`NetIncome`；BS 为 `TotalAssets`、`TotalLiabilitiesAndEquity`。官方声明行顺序动态生成，一律按 `group` 取。
  - 父科目恒为嵌套分节：自身金额在 `Header`，子科目在 `Rows`，`Summary` 为两者合计；费用 / 资产映射只累加 `Header` 与 `Data` 行，不读 `Summary`，不会重复计数。
  - 无值单元格为 `""`，合计行为 `"0.00"`。
- 解析逻辑在 `QuickbooksDataParser`，样例与单测见 Java `src/test/resources/quickbooks/`、`QuickbooksDataParserTest`。金额按 BigDecimal 精确累加，落库仍保持原文本格式（如 `"0.0"`、`"74.86"`）。
- **解析自检**（`checkProfitAndLoss` / `checkBalanceSheet`，`NoReportData=true` 时跳过）：
  - **阻断**：解析出的月份须从请求起始月起逐月连续、无重复，且至少覆盖到报表生成当月（`Header.Time`；未来月份可缺）；不满足 → 本次**不写**该报表及其 log 表（保留上次数据，旧 log 也不清理），记 error 日志；不抛异常、不改连接状态，次日定时同步自动重试。`sync_summary.json` 中对应计数（含 `*_log`）记为 `-1`；QBO Log 的 END 记录仍为成功（Connections 页据此判在线），但写明 "previous data kept for [...]"。
  - **只记录**（error 日志，进 Sentry——意味着格式漂移、需改代码）：`GrossProfit ≠ Income − COGS`、`TotalAssets ≠ TotalLiabilitiesAndEquity`（逐列，容差 0.01）、BS 顶层分组缺失而按位置兜底。
  - 月份列识别：`MetaData` 带 `StartDate`/`EndDate` 且 `ColKey` 不是 `total`。

成功后：
1. `sync_status=success`，`company_quickbooks.status=success`。
2. 摘要（各表行数）上传 S3，记 `AIRFLOW_DAILY_SCHEDULE_END`（成功）日志。
3. 发布 `CloseMonthUpdatedEvent(source=QBO)`，触发下游刷新（见 §8）。

失败：`sync_status=fail`，`company_quickbooks.status=Invalid`，记失败日志。

---

## 6. 状态与提醒

### 6.1 状态字段

| 字段 | 取值 | 变化 |
|------|------|------|
| `company_quickbooks.status` | `success` / `Invalid` / `fail` | 见下方说明 |
| `quickbooks_connection.mapping_status` | `mapping_processing` → `success` / `fail` | 每次 Mapping |
| `quickbooks_connection.sync_status` | `sync_processing` → `success` / `fail` | 每次 Sync |
| `quickbooks_connection.token_valid` | true / false | Token 刷新成功或失败 |

`company_quickbooks.status` 的变化：
- 变为 `success`：连接成功、同步或映射成功、Token 刷新成功。
- 变为 `Invalid`：同步或映射失败、Token 刷新失败。
- 变为 `fail`：断开连接、切回 Manual。

前端按状态显示横幅（Financial 页、Company Overview）：未连接、Token 过期、连接异常。Portfolio Companies 的 Connections 页签显示 Online / Offline / Manual。

### 6.2 Token 失效邮件

- 定时任务 `QuickbooksTokenExpiredReminder` 每 15 分钟执行一次，发给公司管理员，只发活跃公司。
- 每家公司每天最多发一封。

| 条件 | 邮件 |
|------|------|
| `token_valid=false` | "Reconnect {公司}'s Quickbooks Online Connection" |
| `token_invalid_to_valid=true`（重新连接时置位） | "{公司}'s Quickbooks Online Connection has been reestablished" |

发送后置 `had_send_email=true`。Token 刷新成功或失败都会重置该标记。

### 6.3 账本过期

- `quickbooks_close_date` 距今 ≥ 45 天时，Company Overview 提示 "Books Are Past Due"。
- 用户可以在该弹窗里手动刷新。

---

## 7. 模式切换的数据影响

入口：`FinancialSettingServiceImpl.conversionMode()`。

| 切换 | 影响 |
|------|------|
| Automatic → Manual | ① 当前 QBO 利润表和资产负债表数据复制为 `finance_manual_data` 的新基础版本；② 删除 QBO 日志、数据变更记录、连接和全部 `quickbooks_*` 数据；③ 清理标准化 actuals 和增长率数据；④ 重建预测。`status` 变为 `fail` |
| Manual → Automatic | 写入一个空的手工数据新版本；清理同样的派生数据；随后走 OAuth 连接 |

---

## 8. 入库后的下游使用

Automatic 模式下，系统所有财务功能的数据来源都是 QBO 表。读取统一经过 `QuickbooksQueryService`。

### 8.1 实时换算（不落库）

- 入口：`FiDataCalculateServiceImpl.getFiDataBetweenDates()` 按 `company_quickbooks.mode` 选择数据源。
- P&L 与 BS 按月份（`start_date`）配对（`FiDataConverter.convert`），任一侧缺月只跳过该月，不会让后续月份错位；资本化研发的环比优先取上一自然月的 BS（P&L 与 BS 可能来自不同同步批次，如跨年窗口后移），该月不存在时退回上一条配对成功的月份。
- Automatic 时读 QBO 利润表和资产负债表，经 `FiDataConverter` 转成统一的 `FiDataDto`，再做币种换算：
  - 指标：收入、COGS、各类费用、现金、应收应付、债务、资本化研发；
  - Payroll 按 S&M / G&A / R&D 百分比拆分到三个部门。
- 使用方：
  - 财务报表（Financial 页）、公司概览、财务 PDF 导出；
  - 增长率（`financial_growth_rate`）→ 同行组资格（连续 6 个月收入非负）；
  - 24 个月系统预测。

### 8.2 同步成功后的事件链

监听器：`CloseMonthUpdatedEventListener`。

1. **同步执行**：重建该公司的财务标准化数据（`financial_normalization` / `financial_normalization_current`），完成后异步刷新 Benchmark 排位基线。
2. **同步执行**：关账月份前进时，写 `financial_company_close_month_update`，前端据此显示 "Benchmark Data Updated" 横幅，引导用户去 Benchmark。
3. **异步（SQS）**：依次重算增长率 → 同行组资格 → 24 个月预测。

标准化数据的使用方：
- Benchmark 引擎、Benchmark 报告 PDF；
- 关账月份判断（`ClosedMonthResolver`）；
- AI Chatbot 的财务摘要（`/financialNormalized/chatSummary`）和 close month。

### 8.3 每日快照

- 定时任务 `SaveCompanyQuickbooksDataEveryday`，`cron(0 2 * * ? *)`，按公司币种和 USD 各算一次。
- 内容：健康分和排名、ARR、Rule of 40、毛利率、现金、Burn、Runway 等，写入 `company_quickbooks_data`。
- 使用方：Portfolio Companies 列表、ERL 默认期间。
- **不调 QBO**，只读已入库的数据。

---

## 9. 数据存储

### 9.1 PostgreSQL

所有 `quickbooks_*` 表按 `company_id` 区分公司，带 `batch_id`；金额字段为 VARCHAR。

| 表 | 内容 | 写入方式 |
|----|------|---------|
| `company_quickbooks` | 模式、`realmId`、状态、Payroll 拆分比例、`view`（Quarterly / Annually，仅影响 Manual 模式的提醒周期） | 业务更新 |
| `quickbooks_connection` | access / refresh token、`token_valid`、邮件标记、`mapping_status`、`sync_status` | 业务更新 |
| `quickbooks_category` | 分类字典 | 手工维护 |
| `quickbooks_category_account` | 科目 → 分类映射 | 每次同步整体替换 |
| `quickbooks_account_list_detail` | 科目表 | 每次同步整体替换 |
| `quickbooks_profit_and_loss` | 利润表（月） | 每次同步整体替换 |
| `quickbooks_balance_sheet` | 资产负债表（月） | 每次同步整体替换 |
| `quickbooks_profit_and_loss_log` / `quickbooks_balance_sheet_log` | 带 `pull_time` 的拉取记录，用于"最近同步时间"和"是否有数据"判断 | 追加后只保留最新 batch |
| `quickbooks_close_date` | 账本关账日期 | 追加后只保留最新 batch |
| `quickbooks_logs` | 全链路操作日志，供 QBO Log 页面（`/companyQuickbooks/qboLogPage`）查看 | 追加 |
| `company_quickbooks_data` | 每日 KPI 快照（§8.3） | 每日重算 |

DDL：Java 仓库 `deploy/upgrade_doc/sprint107/`（`V1__qbo_pg_tables.sql` 等）。

> `quickbooks_data_change` / `quickbooks_data_change_comments` 虽然名字带 quickbooks，但只给 **Manual** 模式用：对比手工数据的新旧版本，供管理员评论和接受。与 QBO 拉取无关。

### 9.2 S3（审计备份）

- 路径：`qbo/{companyId}/{processType}/{yyyyMMdd_HHmmss}/{batchId}_{文件名}`。
- 文件：`token_refresh.json`（刷新请求和响应）、`sync_summary.json`（各表行数）。
- OAuth 连接时的 Token 响应也会备份。
- 原始报表**不**备份。

---

## 10. 涉及的核心代码文件

Java `gstdev-cioaas-web`，包前缀 `com.gstdev.cioaas.web`：

| 文件 | 职责 |
|------|------|
| `fi/controller/FinancialSettingController.java` | `/companyQuickbooks`：连接、授权、回调、断开、刷新、模式切换、日志查询 |
| `fi/service/FinancialSettingServiceImpl.java` | OAuth（Intuit SDK）、断开、模式切换、Token 失效邮件、待同步公司列表 |
| `quickbooks/interfaces/controller/QuickbooksController.java` | `/quickbooks`：科目映射接口 |
| `quickbooks/application/service/QuickbooksServiceImpl.java` | 映射保存、连接和 Token 状态维护 |
| `quickbooks/infrastructure/processor/QuickbooksSqsProcessor.java` | 发送 Mapping / Sync 消息，每日批量投递 |
| `quickbooks/infrastructure/processor/QuickbooksMappingProcessor.java`、`QuickbooksSyncProcessor.java` | SQS 消费 |
| `quickbooks/application/service/QuickbooksSyncService.java` | 同步编排：拉取、解析、写库、状态、日志、S3、事件 |
| `quickbooks/infrastructure/client/QuickbooksApiClient.java` | HTTP 调用、Token 刷新、重试、Base URL、时间范围 |
| `quickbooks/infrastructure/client/QuickbooksDataParser.java` | 报表 JSON / XML 解析与分类汇总 |
| `quickbooks/application/service/QuickbooksDataWriteService.java` | PostgreSQL 写入（替换 / 追加 / 清理旧 batch） |
| `quickbooks/application/service/QuickbooksQueryService.java` | QBO 数据的统一读取入口（下游使用） |
| `fi/mapper/FiDataConverter.java` | QBO 数据 → `FiDataDto` |
| `fi/event/CloseMonthUpdatedEventListener.java` | 同步成功后的下游事件链 |

---

## 11. 日志 Action 枚举（`QBOLogEnum`）

| Action | code | 触发时机 |
|--------|------|---------|
| `CREATE_COMPANY_MANUAL` | 100 | 手动创建公司 |
| `SWITCH_MANUAL_TO_AUTO` / `SWITCH_AUTO_TO_MANUAL` | 101 / 102 | 模式切换 |
| `CLICK_CONNECT_QBO` | 200 | 点击连接 |
| `CONNECT_QBO_FAILED` / `CONNECT_QBO_SUCCESS` | 201 / 202 | OAuth 回调结果 |
| `CLICK_DISCONNECT_QBO` | 203 | 断开连接 |
| `AIRFLOW_DAILY_SCHEDULE_BEGIN` / `END` | 300 / 301 | Mapping / Sync 开始和结束（名字是历史遗留，现由 Java 执行） |
| `REFRESH_TOKEN_BEGIN` / `END` | 400 / 401 | Token 刷新 |

`SEND_TO_AIRFLOW`（204）已不再使用。
