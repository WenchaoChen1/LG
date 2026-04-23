# 季度基准报告自动导出至 SharePoint — 设计文档（Design Spec）

> **需求源**：`E:\LG_Benchmark\季度基准报告自动导出至SharePoint需求.md`
> **前置调研**：`CIOaas-api/.claude/doc/features/quarterly-benchmark-report-sharepoint-investigation.md`
> **实现仓库**：`CIOaas-api`（主）、`CIOaas-web`（无 UI 变更）
> **设计日期**：2026-04-22
> **状态**：待用户评审 → 评审通过后进入 `writing-plans`

---

## 一、目标与非目标

### 目标
1. 每季度自动为"有 Actuals 数据的公司"生成基准报告 PDF。
2. 把 PDF 三处落地：**SharePoint 指定路径**、**LG 应用内 Documents - Company 文件夹**、**S3（审计留存）**。
3. SME（Nico）邮件通知：成功批次汇总一封 + 失败公司各一封。
4. 提供管理端 API 供运营按需重跑单公司 / 整个季度。

### 非目标（本期不做）
- 生成 "一页投资摘要"（SME 下游流程，独立项目）。
- PDF 设计的重新视觉设计（沿用现有 `PortfolioDetailViewPdf.html` 风格）。
- 多租户 SharePoint 支持（当前仅 GS 的单一 tenant）。

---

## 二、决策记录（用户已在 brainstorming 中确认）

| # | 议题 | 决策 | 影响 |
|---|------|------|------|
| 1 | 执行时点 | **季末 +1 个月**，cron `0 2 1 2,5,8,11 ? *`（UTC） | Q1 报告在 5/1 生成；给财务留 30 天关账窗口 |
| 2 | 邮件触发 | **混合**：成功汇总一封 + 失败各一封 | 降低 Nico 收件疲劳 + 失败即时排错 |
| 3 | LG 落地位置 | 新建 **Category `"Benchmark Report"`** 挂在现有 `folder="Company"` 下 | 增量 SQL 一行种子数据；前端自动出现 |
| 4 | 失败重试 | 单公司内 **重试 3 次**（指数退避 10s / 30s / 90s） | 屏蔽网络抖动；仍失败进入失败邮件分支 |
| 5 | 手动触发 + 批次状态 | 提供 `POST /benchmark/report/run`（支持 companyId / period）+ 批次状态 `RUNNING / COMPLETED / PARTIAL / FAILED` | 运营可按需补跑；dashboard 能看出部分失败 |
| 6 | 版本策略 | SharePoint **覆盖**；LG Documents **保留所有版本**（每次新 Document 行 + 新 S3 对象） | 对外只见最新；内部可审计历次生成 |
| 7 | SME 邮箱配置 | 存 **`system_config` 表**（key/value，admin 可改） | 不需发布；Nico 离职可即时切换 |

### 决策记录（设计阶段由 Claude 自动选定）

| # | 议题 | 候选方案 | 选择 | 理由 |
|---|------|----------|------|------|
| A1 | SharePoint 客户端 | Microsoft Graph SDK / 原生 HTTP + MSAL4J | **Graph SDK** | 自动 upload session、token 刷新、重试；依赖体积可接受 |
| A2 | 批次执行模型 | 单任务循环 / SQS fan-out | **SQS fan-out** | 与 `SaveCompanyQuickbooksDataEveryday` 一致；天然并行 + 每消息自动重试 |
| A3 | PDF 生成位置 | 进程内 openhtmltopdf / AWS Lambda | **进程内** | 复用 `FinancialPdfService`；当前公司量（<200）无压力 |

---

## 三、架构总览

```
┌─────────────────────────────┐
│ AWS EventBridge Scheduler   │  cron 0 2 1 2,5,8,11 ? *
│ FixedSchedule:              │
│   QuarterlyBenchmarkReport  │
└────────────┬────────────────┘
             │ SQS Message
             ▼
┌─────────────────────────────┐
│ ScheduleProcessor.          │  (新增 case 分支)
│ processMessage()            │
└────────────┬────────────────┘
             │ 调用
             ▼
┌─────────────────────────────┐      ┌──────────────────────────┐
│ BenchmarkReportService.     │─────▶│ BenchmarkReportPlanner   │
│ runQuarterlyBatch(period)   │      │ - 筛选有 Actuals 的公司  │
└─────────────────────────────┘      │ - 创建 Run 记录          │
                                     │ - 发 N 条 SQS 消息       │
                                     └────────┬─────────────────┘
                                              │
                                              │ (每公司一条)
                                              ▼
                                     ┌──────────────────────────┐
                                     │ BenchmarkReportWorker    │
                                     │ (SQS 消费)               │
                                     │  1. 构建 PDF 数据        │
                                     │  2. 渲染 PDF             │
                                     │  3. 上传 S3 / SP / LG    │
                                     │  4. 更新 Record 状态     │
                                     │  5. 失败立即发邮件       │
                                     └────────┬─────────────────┘
                                              │
                                              ▼
                                     ┌──────────────────────────┐
                                     │ BenchmarkReportFinalizer │
                                     │ (Run 完成事件触发)       │
                                     │  - 聚合成功清单          │
                                     │  - 发成功汇总邮件        │
                                     │  - 设置 Run 终态         │
                                     └──────────────────────────┘
```

---

## 四、领域模型与模块划分

### 4.1 新包 `fi/benchmarkreport/`

```
fi/benchmarkreport/
  controller/
    BenchmarkReportController.java        # 管理端 API：手动触发 / 查询状态
  service/
    BenchmarkReportService.java           # 入口接口
    BenchmarkReportServiceImpl.java       # 编排：准备批次、触发、汇总
    BenchmarkReportPlanner.java           # 筛选公司 + 创建 Run + 发 SQS
    BenchmarkReportWorker.java            # SQS 消费者：处理单公司
    BenchmarkReportFinalizer.java         # 批次完结汇总邮件
    QuarterlyMetricCalculator.java        # 6 个季度指标公式（需求 §3.2.2）
    BenchmarkReportPdfBuilder.java        # 组装 FinancialPdfData + 额外季度指标 → PDF bytes
    BenchmarkReportDispatcher.java        # 统一封装"上传 SP + 存 S3 + 建 LG Document"
  domain/
    BenchmarkReportRun.java               # 批次（期次、开始/结束、状态）
    BenchmarkReportRecord.java            # 单公司结果
  repository/
    BenchmarkReportRunRepository.java
    BenchmarkReportRecordRepository.java
  enums/
    BenchmarkReportRunStatusEnum.java     # RUNNING / COMPLETED / PARTIAL / FAILED
    BenchmarkReportRecordStatusEnum.java  # PENDING / SUCCESS / FAILED / RETRYING
    BenchmarkReportPeriodEnum.java        # Q1/Q2/Q3/Q4 工具方法
  contract/
    BenchmarkReportRunDto.java
    BenchmarkReportTriggerInput.java      # {companyId?, period?}
  properties/
    BenchmarkReportProperties.java        # @ConfigurationProperties("cio.benchmark-report")
```

### 4.2 新包 `storage/sharepoint/`

```
storage/sharepoint/
  SharePointClient.java                   # 接口
  GraphSharePointClient.java              # 实现（微软 Graph SDK）
  properties/SharePointProperties.java    # @ConfigurationProperties("cio.sharepoint")
  config/SharePointConfig.java            # GraphServiceClient Bean
  exception/SharePointException.java
```

放在 `storage/` 与 `AbstractStorage`（S3）并列，保持"外部存储"分层一致。

### 4.3 调度接入点

- `scheduler/enums/FixedScheduleTypeEnum.java` 新增：
  ```java
  QuarterlyBenchmarkReport("QuarterlyBenchmarkReport", "cron(0 2 1 2,5,8,11 ? *)")
  ```
- `scheduler/service/ScheduleProcessor.processMessage()` 新增 switch case，调用 `benchmarkReportService.runQuarterlyBatch(currentPeriod())`。
- 应用启动 `initFixedScheduler()` 自动把该 cron 同步到 AWS EventBridge Scheduler，无需人工建调度。

---

## 五、数据模型（DDL）

### 5.1 批次表 `benchmark_report_run`
```sql
CREATE TABLE benchmark_report_run (
    id                  VARCHAR(32)  PRIMARY KEY,     -- UUID
    period              VARCHAR(10)  NOT NULL,        -- "2026Q1"
    trigger_type        VARCHAR(16)  NOT NULL,        -- AUTO / MANUAL
    triggered_by        VARCHAR(32),                  -- 手动时为 userId；自动时为 "system"
    total_companies     INTEGER      NOT NULL DEFAULT 0,
    success_count       INTEGER      NOT NULL DEFAULT 0,
    failed_count        INTEGER      NOT NULL DEFAULT 0,
    status              VARCHAR(16)  NOT NULL,        -- RUNNING / COMPLETED / PARTIAL / FAILED
    started_at          TIMESTAMP    NOT NULL,
    completed_at        TIMESTAMP,
    created_at          TIMESTAMP    NOT NULL,
    created_by          VARCHAR(32)  NOT NULL,
    updated_at          TIMESTAMP    NOT NULL,
    updated_by          VARCHAR(32)  NOT NULL
);
CREATE INDEX idx_bm_report_run_period ON benchmark_report_run(period);
```

### 5.2 明细表 `benchmark_report_record`
```sql
CREATE TABLE benchmark_report_record (
    id                  VARCHAR(32)  PRIMARY KEY,
    run_id              VARCHAR(32)  NOT NULL REFERENCES benchmark_report_run(id),
    company_id          VARCHAR(32)  NOT NULL,
    company_name        VARCHAR(255) NOT NULL,        -- 冗余，便于审计
    period              VARCHAR(10)  NOT NULL,        -- "2026Q1"
    status              VARCHAR(16)  NOT NULL,        -- PENDING / SUCCESS / FAILED / RETRYING
    attempt_count       INTEGER      NOT NULL DEFAULT 0,
    pdf_file_id         VARCHAR(32),                  -- 关联 file_object (S3)
    lg_document_id      VARCHAR(32),                  -- 关联 document 表
    sharepoint_url      VARCHAR(1024),                -- SP 文件 web url
    error_message       TEXT,
    started_at          TIMESTAMP,
    completed_at        TIMESTAMP,
    created_at          TIMESTAMP    NOT NULL,
    updated_at          TIMESTAMP    NOT NULL
);
CREATE INDEX idx_bm_report_record_run ON benchmark_report_record(run_id);
CREATE INDEX idx_bm_report_record_company_period ON benchmark_report_record(company_id, period);
```

### 5.3 种子数据：`CompanyDocumentationCategory`
```sql
INSERT INTO company_documentation_category (id, folder_id, name, show_order, created_at, created_by, updated_at, updated_by)
VALUES ('Benchmark Report', 'Company', 'Benchmark Report', 99, NOW(), '1', NOW(), '1');
```

### 5.4 `system_config` 表新增行（表已存在则复用；若不存在本期建最小表）
```sql
INSERT INTO system_config (config_key, config_value, description, created_at, updated_at)
VALUES ('benchmark_report.sme_email', 'nico.carlson@<domain>', '季度基准报告 SME 收件人', NOW(), NOW());
```
> 若 `system_config` 表当前不存在，本需求**不引入**；改为在 `BenchmarkReportProperties` 用 Nacos 配置 + 启动时把初始值 upsert 到新表。由实现阶段根据现状决定（见 §十四）。

---

## 六、外部集成：SharePoint（Microsoft Graph）

### 6.1 认证方式
- **App-only (Client Credentials)** via `com.azure.identity.ClientSecretCredential`
- Azure AD App Registration 需要的权限（Application permissions）：
  - `Sites.ReadWrite.All` 或 `Sites.Selected`（后者更安全，需 tenant 管理员把指定 site 授权给 App）
  - `Files.ReadWrite.All`
- Secret 存 Nacos 加密：`cio.sharepoint.tenant-id / client-id / client-secret`

### 6.2 配置结构（`SharePointProperties`）
```yaml
cio:
  sharepoint:
    tenant-id: "xxx"
    client-id: "xxx"
    client-secret: "xxx"
    site-id: "<gs-tenant.sharepoint.com,xxx,xxx>"
    drive-id: "<drive-id>"
    root-path: "Investment Team/LG Benchmarks"   # 可覆盖
    upload-timeout-seconds: 60
```

### 6.3 `SharePointClient` 接口
```java
public interface SharePointClient {
  /** 幂等：路径已存在则忽略。返回 folder 的 itemId。 */
  String ensureFolder(String path);

  /** 小文件（<4MB）PUT；大文件走 upload session。同名覆盖。返回 web url。 */
  String uploadFile(String parentPath, String fileName, byte[] content, String contentType);
}
```

### 6.4 错误分类
| Graph 返回 | 含义 | Worker 处理 |
|-----------|------|-------------|
| 401 Unauthorized | token 过期 | SDK 自动刷新；仍失败走 retry |
| 403 Forbidden | 权限不足 | 记 FAILED + alert 邮件 |
| 409 Conflict | 目录已存在 | 幂等忽略 |
| 429 Throttled | 超配额 | 按 Retry-After 头延迟重试 |
| 5xx | Graph 服务异常 | 指数退避重试 |

---

## 七、核心流程细节

### 7.1 批次规划（`BenchmarkReportPlanner`）
```
1. 计算 period：当前日期反推上一季度（如 2026-05-01 执行 → period = "2026Q1"）
2. 查询有 Actuals 的公司：
   - 遍历 active companies
   - 对每家调 FiDataCalculateService.getLatestOfficialData(...)
   - 该公司 period 内任一月份存在 Actuals → 入选
3. 创建 BenchmarkReportRun（status=RUNNING, total_companies=N）
4. 批量创建 N 条 BenchmarkReportRecord（status=PENDING）
5. 对每家发 SQS 消息到 BenchmarkReportQueue：
   { "runId": "...", "recordId": "...", "companyId": "...", "period": "2026Q1" }
6. 如果 N=0 → Run 直接 COMPLETED，不发任何消息
```

### 7.2 单公司处理（`BenchmarkReportWorker`）
```
onMessage(msg):
  record = loadRecord(msg.recordId)
  if record.status in (SUCCESS, FAILED) → 幂等跳过

  for attempt in 1..3:
    record.attempt_count = attempt
    record.status = attempt==1 ? PENDING : RETRYING
    try:
      pdfData = BenchmarkReportPdfBuilder.build(companyId, period)
      pdfBytes = renderPdf(pdfData)
      fileObject = fileService.uploadBytes(pdfBytes, fileName, "application/pdf")
      spUrl = sharePointClient.uploadFile(targetPath, fileName, pdfBytes, "application/pdf")
      documentId = createLgDocument(companyId, fileObject.id, fileName)
      record.status = SUCCESS
      record.pdf_file_id = fileObject.id
      record.lg_document_id = documentId
      record.sharepoint_url = spUrl
      break
    except retryable e:
      if attempt < 3: sleep(backoff[attempt]); continue
      record.status = FAILED
      record.error_message = e.message
      emailService.sendFailureNotification(record, e)
      break
    except non-retryable e:
      record.status = FAILED; emailService.sendFailure...; break

  saveRecord(record)
  checkRunCompletion(record.run_id)  // 若 success+failed == total → 触发 Finalizer
```

重试退避：`[10s, 30s, 90s]`，可重试异常白名单（超时、429、5xx）；非可重试（403、数据缺失等）直接失败。

### 7.3 PDF 数据组装（`BenchmarkReportPdfBuilder`）
```java
public class BenchmarkReportPdfBuilder {
  public FinancialPdfData build(String companyId, String period) {
    // 1. 公司基础信息（沿用 FinancialPdfService 已有逻辑）
    // 2. Actuals：close_month 往回推 12 个月
    // 3. Committed Forecast：FinancialForecastHistoryService.getLatestVersion
    // 4. System Forecast：FinancialForecastDataService 最新结果
    // 5. 季度基准指标：QuarterlyMetricCalculator.compute(companyId, period)
    //    → 填充 FinancialPdfData.quarterlyBenchmarks（新增字段）
    return data;
  }
}
```

**复用策略**：不改 `FinancialPdfService`；扩展 `FinancialPdfData` 添加 `quarterlyBenchmarks` 字段（季度 6 项指标），新模板 `templates/BenchmarkReportPdf.html` 引用。

### 7.4 季度指标计算（`QuarterlyMetricCalculator`）
严格按需求 §3.2.2 的 6 个公式实现，纯函数，输入月度数据输出季度值：

| 指标 | 输入 | 分母为 0 处理 |
|------|------|---------------|
| ARR Growth Rate | ARR_start_of_quarter, ARR_end_of_quarter | start=0 或 NA → 0；start 为负 → 取 abs |
| Gross Margin | SUM(Gross_Profit_m), SUM(Gross_Revenue_m) | 分母 0 → 0 |
| Monthly Net Burn | SUM(NetIncome_m), SUM(CapRD_m) | n/a |
| Monthly Runway | Cash_end, Monthly_Net_Burn | 负数烧钱 → NA（沿用 LG 前端显示逻辑） |
| Rule of 40 | SUM(NetProfitMargin_m), SUM(MRR_YoY_m) | n/a |
| Sales Efficiency | SUM(S&M_Expenses_m + Payroll_m), SUM(NewMRR_LTM_m) | 分母 0 → 0 |

数据源统一从 `FinancialNormalizationCurrent` 读（月度），与 `BenchmarkingServiceImpl` 保持一致；季度聚合只在本计算器内做，不污染原有月度引擎。

### 7.5 文件命名
```
[SanitizedCompanyName]_Benchmark_Report_[Quarter]_[Year].pdf
例：SocialLadder_Benchmark_Report_Q1_2026.pdf
```
公司名清洗：`[^A-Za-z0-9_.-]` → `_`，截断 60 字符。

### 7.6 存储落地（`BenchmarkReportDispatcher`）
| 目标 | 实现 | 版本策略 |
|------|------|----------|
| **S3（审计）** | 扩展 `FileServiceImpl` 加 `upload(byte[], fileName, contentType)` 重载，写 `file_object` 表 | 每次新 object（key 带日期前缀 + UUID，天然不冲突） |
| **SharePoint** | `SharePointClient.ensureFolder("Investment Team/LG Benchmarks/{CompanyName}")` + `uploadFile(...)` 同名覆盖 | **覆盖** |
| **LG Documents** | `new Document(invite=company, type=1, folder=<Company folder>, fileId=<S3 fileId>, createdBy="1", categoryId="Benchmark Report")` → `documentService.savaDocument` | **保留所有版本**（每次新 Document 行） |

### 7.7 邮件通知

**失败邮件（每公司一封，立即发）**：
- Subject: `[LG] Benchmark Report generation failed: {CompanyName} {Period}`
- Body: 公司名、期次、重试次数、错误摘要、Run ID
- 收件人：`system_config.benchmark_report.sme_email`

**成功汇总邮件（批次完结一封）**：
- Subject: `[LG] Benchmark Reports ready: {Period} ({N} companies)`
- Body: 期次、成功公司列表（带 SharePoint 链接）、失败公司数量（详情引用前面的单封邮件）
- 触发点：`BenchmarkReportFinalizer` 监听 Run status 变化（success+failed == total）
- 收件人：同上

两类模板都新建 Thymeleaf 文件：
- `templates/email/BenchmarkReportSuccessSummary.html`
- `templates/email/BenchmarkReportFailure.html`

`EmailTypeEnum` 新增两条：
```java
BENCHMARK_REPORT_SUCCESS_SUMMARY("BenchmarkReportSuccessSummary", "Benchmark Reports Ready"),
BENCHMARK_REPORT_FAILURE("BenchmarkReportFailure", "Benchmark Report Failed"),
```

---

## 八、管理端 API

### 8.1 手动触发
```
POST /benchmark/report/run
Body: { "companyId": "optional", "period": "optional, e.g. 2026Q1" }
```
- `companyId` + `period` 都传：单公司单期次重跑（新建 Run，single-record）
- 只传 `period`：整个季度重跑（按 Planner 逻辑重新筛选）
- 都不传：按当前时间反推上一季度，作为默认期次

权限：`SUPER_ADMIN` (roleType=0 或 1，按现有 `RoleTypeEnum`)。

### 8.2 查询批次状态
```
GET /benchmark/report/runs?period=2026Q1&page=0&size=20
GET /benchmark/report/runs/{runId}
GET /benchmark/report/runs/{runId}/records
```
返回 Run + Record 列表，含 SP 链接。供运营 dashboard 使用（本期不建前端页，仅 API）。

---

## 九、错误处理与日志

| 失败点 | 日志级别 | 动作 |
|--------|----------|------|
| Graph API token 获取失败 | ERROR | 整个 Run 置 FAILED；所有待处理 record 标 FAILED；单独一封"系统级"邮件 |
| 单公司 PDF 渲染异常 | ERROR | 记 Record.error_message；走重试 |
| SharePoint upload 失败（5xx/429） | WARN | 重试 |
| SharePoint upload 失败（403） | ERROR | 不重试；记录邮件 |
| S3 upload 失败 | ERROR | 重试；仍失败 FAILED |
| LG Document 写入失败 | WARN | 不回滚 SP/S3（已成功）；Record 仍标 SUCCESS 但 `error_message` 填写 "LG document insert failed: ..."（后续运营可批量补录） |
| SendGrid 失败 | WARN | 不阻塞 Record 成功状态 |

日志结构化（项目已有 `gstdev-cioaas-logging`），所有关键日志带 `runId + companyId + period + attempt` 四字段。

---

## 十、测试策略

### 10.1 单元测试
- `QuarterlyMetricCalculator`：6 个公式 × 4 组边界（正常、分母 0、负数 ARR_start、NA 月） = ~24 用例。纯函数，零依赖，必须覆盖 100%。
- `BenchmarkReportPlanner.selectEligibleCompanies`：mock 不同 Actuals 状态。
- 文件名 sanitize。

### 10.2 集成测试
- `BenchmarkReportWorker` 全流程：mock `SharePointClient` + 真实 PostgreSQL + Testcontainers。
- 重试逻辑：`SharePointClient` 注入 3 次抛 503，断言第 4 次成功。
- 幂等：同一 SQS 消息处理两次，断言只写一条 Document。

### 10.3 端到端（手动）
- Stage 环境真实跑一次 2026Q1，验证：
  - SP `Investment Team/LG Benchmarks/SocialLadder/SocialLadder_Benchmark_Report_Q1_2026.pdf` 存在且可下载
  - LG Documents 页能看到新分类 "Benchmark Report" 下的文件
  - Nico 邮箱收到预期邮件（stage 白名单需提前加）

---

## 十一、配置清单（Nacos）

```yaml
cio:
  sharepoint:
    tenant-id: "${SP_TENANT_ID}"
    client-id: "${SP_CLIENT_ID}"
    client-secret: "${SP_CLIENT_SECRET}"
    site-id: "${SP_SITE_ID}"
    drive-id: "${SP_DRIVE_ID}"
    root-path: "Investment Team/LG Benchmarks"
    upload-timeout-seconds: 60
  benchmark-report:
    enabled: true                 # kill switch
    retry-backoff-seconds: [10, 30, 90]
    sqs-queue-name: BenchmarkReportQueue  # 新建 SQS 队列
    planner-parallelism: 10       # 发消息并发
```

SQS 队列 `BenchmarkReportQueue` 需在 AWS 预先建好（建议由 infra 团队通过 Terraform 或运行时 `sqsService.createQueueIfAbsent` 处理 —— 项目已有类似自动化的 `InitSqsQueueEnum`）。

---

## 十二、回滚与灰度

- **Kill switch**：`cio.benchmark-report.enabled=false` → `ScheduleProcessor` 收到消息后直接跳过（不消费 SQS 避免积压）。
- **灰度策略**：首次上线时 `BenchmarkReportProperties.whitelist-company-ids` 只放 1-2 家测试公司，确认 SP 落地、邮件、PDF 都正常后移除白名单。
- **回滚**：禁用 kill switch；AWS Scheduler 改为 DISABLED；Document 表新增记录可保留（不影响旧功能）。

---

## 十三、工作量预估与拆分

建议 5 个 PR 顺序交付（每个都能独立 review & merge）：

| # | PR 主题 | 工作量 | 依赖 |
|---|---------|--------|------|
| 1 | SharePoint client + config + 冒烟测试 | 2d | Azure AD app 注册前置（运维） |
| 2 | `QuarterlyMetricCalculator` + 单测 | 2d | 无 |
| 3 | PDF builder + 模板 + 管理端 preview API | 2d | #2 |
| 4 | Planner/Worker/Finalizer + DDL + 邮件 + 手动 API | 4d | #1 #3 |
| 5 | 接入 `FixedScheduleTypeEnum` + E2E 冒烟 | 1d | #4 |

**合计：~11 人日**（不含 Azure AD App 注册、SharePoint 站点授权、SendGrid 白名单等运维协同）。

---

## 十四、待实现阶段落地时再确认的小项

1. `system_config` 表当前是否已存在 —— 若无，走 Nacos 配置 + 建最小 kv 表，或直接用 Nacos（问题 6 的实现细节，不影响整体设计）。
2. SQS 队列创建方式（`InitSqsQueueEnum` vs 纯 Terraform）—— 跟随现有实践。
3. Azure AD App Registration 的权限型号（`Sites.Selected` 更安全但需 tenant admin 配合）—— 运维协商。
4. 公司 logo base64 大小 —— 若 PDF 尺寸过大（>10MB）考虑压缩或走 upload session。
5. Nico 离职后的 owner 切换策略 —— 由 admin UI 更新 `system_config` 即可，不需要代码变更。

---

## 十五、未纳入本期的潜在跟进项

- 基于 Record 状态做告警面板（Grafana / CloudWatch）。
- 支持除 Nico 外的多收件人（cc/bcc 列表）。
- 下游"单页投资摘要"自动触发（当前仍由 SME 手工启动）。
- 重跑超过 7 天的 Run 自动归档。
- PDF 内容 A/B 测试（新旧两版模板并行生成）。

---

## 附录 A：alternatives considered（架构级）

### A.1 SharePoint 接入
**候选 1（选中）**：Microsoft Graph SDK（`com.microsoft.graph:microsoft-graph` + `com.azure:azure-identity`）
- 优点：自动 token 刷新、upload session、分页、重试；维护成本低
- 缺点：依赖 ~20MB；封装较重

**候选 2**：原生 REST (OkHttp) + MSAL4J
- 优点：依赖轻；控制精细
- 缺点：手工实现 upload session（>4MB 必须）；token 刷新容易出 bug；人力成本高

### A.2 批次执行
**候选 1（选中）**：SQS fan-out（Planner 发 N 条 → Worker 并行消费）
- 优点：与 `SaveCompanyQuickbooksDataEveryday` 对齐；天然并行；每消息自动重试
- 缺点：需要新 SQS 队列和处理器

**候选 2**：单任务循环（Processor 直接 for-loop 全部公司）
- 优点：零新增基础设施
- 缺点：串行慢；一家卡住整批卡住；无自然重试边界

### A.3 PDF 渲染
**候选 1（选中）**：进程内 openhtmltopdf（复用 `FinancialPdfService`）
- 优点：零新增；一致的模板风格；debug 方便
- 缺点：峰值内存高（并发多家同渲染时）

**候选 2**：独立 Lambda + S3 pre-signed URL 回传
- 优点：CPU/内存独立伸缩
- 缺点：多一层部署；数据库/缓存访问复杂；当前公司量<200 完全不必要

---

## 附录 B：需求文档中的澄清结论汇总

需求原文的几处歧义，本设计的处理：

| 原文出处 | 歧义 | 本设计结论 |
|---------|------|-----------|
| §3.1 "Q1 报告在 5 月 1 日生成" | 4/1 还是 5/1？ | **5/1**（季末 +1 个月）— 与用户 Brainstorming 问题 1 确认 |
| §4.2 vs §6.1 邮件时机 | 批量 vs 逐家？ | **混合**：成功汇总 + 失败逐家 — Brainstorming 问题 2 |
| §5.2 "创建公司文件夹" | LG 内需要新建文件夹吗？ | 不建物理文件夹；新增 Category `Benchmark Report` 挂在 `Company` folder 下 — Brainstorming 问题 3 |
| §4.2 "错误处理" | 重试几次？ | 单公司内指数退避 3 次 — Brainstorming 问题 4 |
| 未明确 | 是否需要手动触发？ | 是，`POST /benchmark/report/run` — Brainstorming 问题 5 |
| §5.1 命名 | 重跑时覆盖否？ | SP 覆盖 + LG 保留全历史 — Brainstorming 问题 6 |
| §6.1 "Nico" | 如何配置？ | `system_config` kv — Brainstorming 问题 6 |
