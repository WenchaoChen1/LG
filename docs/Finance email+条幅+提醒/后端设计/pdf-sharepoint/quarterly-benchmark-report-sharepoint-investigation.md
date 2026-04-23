# 季度基准报告自动导出至 SharePoint — 实现调研

> 源需求文档：`E:\LG_Benchmark\季度基准报告自动导出至SharePoint需求.md`
> 调研范围：`CIOaas-api`（后端实现为主）、`CIOaas-web`（无 UI 变更，仅可能追加下载入口）
> 调研日期：2026-04-22

---

## 一、现状概览（可复用能力）

| 能力 | 现有资产 | 可复用度 |
|------|----------|----------|
| PDF 生成 | `fi/service/FinancialPdfService`（openhtmltopdf + Thymeleaf，已在 `PortfolioDetailViewPdf.html` 等模板落地） | ★★★★★ 直接复用引擎 |
| 基准指标计算 | `fi/service/BenchmarkingServiceImpl` + `fi/benchmark/engine/*`（MetricExtractor、PeerGroupResolver） | ★★★★☆ 已有月度提取，**需新增季度聚合层** |
| Actuals / Committed Forecast / System Forecast 数据 | `FiDataCalculateServiceImpl.getLatestOfficialData(...)`、`FinancialForecastDataService`、`FinancialForecastHistoryService` | ★★★★★ |
| 定时调度 | `scheduler/` 模块，基于 **AWS EventBridge Scheduler + SQS**。`FixedScheduleTypeEnum` + `ScheduleProcessor.processMessage` 形成 “枚举 → cron → 分发” 管道 | ★★★★★ 新增一条枚举即可 |
| 对象存储 | `storage/` 模块，`AbstractStorage` + `FileServiceImpl.upload`（写 S3、入 `file_object` 表） | ★★★★★ |
| LG 应用内 “Documents-Company” 目录 | `system/` 模块的 `Document` + `CompanyDocumentationFolder`（folderId = `"Company"`） + `DocumentServiceImpl.savaDocument` | ★★★★☆ 需新增一个“Benchmark Report”分类或复用已有 Category |
| 邮件 | `system/service/EmailServiceImpl`（SendGrid + Thymeleaf 模板 + 附件支持） | ★★★★★ |
| 系统用户（作为 createdBy） | `FinancialConstants.SYSTEM_USER_ID = "1"`、`SYSTEM_USER_NAME = "System"` | ★★★★★ |
| SharePoint 集成 | **当前代码库零实现**（grep `sharepoint|msgraph|microsoft.graph` 均 0 命中） | ★☆☆☆☆ 需全新接入 |

---

## 二、关键技术缺口：SharePoint 上传

这是本需求**唯一需要全新打通的外部系统**，其余均可在现有 DDD 结构内扩展。

**推荐方案：Microsoft Graph API（Azure AD App Registration + Client Credentials 流）**

- 依赖：`com.microsoft.graph:microsoft-graph` + `com.azure:azure-identity`
- 上传 API：`PUT /sites/{site-id}/drives/{drive-id}/root:/Investment Team/LG Benchmarks/{CompanyName}/{fileName}:/content`（小文件 < 4MB）或创建 upload session（大文件）
- 目录自动创建：Graph 的 `createUploadSession` 对不存在的父目录不会自动建；需要 `PUT /drive/root:/Investment Team/LG Benchmarks/{CompanyName}:/` 并 body `{"folder":{}}`，遇 409 忽略
- 配置项（新增 `nacos` + `SharePointProperties`）：
  - `cio.sharepoint.tenant-id`、`client-id`、`client-secret`
  - `cio.sharepoint.site-id`、`drive-id`
  - `cio.sharepoint.root-path`（默认 `Investment Team/LG Benchmarks`）
- 备选：OAuth2 Delegated Flow（需存 refresh token，运维更重），不推荐。

---

## 三、建议落地结构（DDD 对齐）

### 3.1 新建领域包 `fi/benchmarkreport/`
```
fi/benchmarkreport/
  controller/BenchmarkReportController.java        # 手动触发 + 下载
  service/BenchmarkReportService.java              # 编排入口
  service/BenchmarkReportServiceImpl.java
  service/BenchmarkReportPdfBuilder.java           # 调 FinancialPdfService + 季度指标 → PDF bytes
  service/QuarterlyMetricCalculator.java           # 6 个季度基准指标（3.2.2）
  service/BenchmarkReportDispatcher.java           # 上传 SP + 落地 Documents + 发邮件
  domain/BenchmarkReportRun.java                   # 运行批次（期次、开始/结束时间、状态）
  domain/BenchmarkReportRecord.java                # 单公司结果（companyId、status、spUrl、fileId、errorMsg）
  repository/*
  contract/BenchmarkReportDto.java
```
> 参考 `benchmark-segment-split-ddl.sql` 已有的 benchmark 拆分风格。

### 3.2 新建 SharePoint 客户端 `storage/sharepoint/`
```
storage/sharepoint/
  SharePointClient.java                             # 接口
  GraphSharePointClient.java                        # 实现（Microsoft Graph SDK）
  properties/SharePointProperties.java              # @ConfigurationProperties("cio.sharepoint")
  config/SharePointConfig.java                      # 构建 GraphServiceClient Bean
```
> 放在 `storage/` 下与 `AbstractStorage`（S3）并列，保持“外部存储”分层一致。

### 3.3 定时任务接入
- 在 `scheduler/enums/FixedScheduleTypeEnum.java` **新增一条枚举**：
  ```java
  QuarterlyBenchmarkReport("QuarterlyBenchmarkReport", "cron(0 2 1 1,4,7,10 ? *)")
  ```
  含义：每季度首月 1 日（Jan/Apr/Jul/Oct） 02:00 UTC 触发，与需求 “季末次月第一天” 一致。
- 在 `scheduler/service/ScheduleProcessor.processMessage` 的 switch 中追加 `case QuarterlyBenchmarkReport: benchmarkReportService.runQuarterlyBatch();`
- 应用启动时 `initFixedScheduler()` 自动把该 cron 同步到 AWS EventBridge Scheduler，**无需人工建调度**。

### 3.4 PDF 内容实现思路
- 复用 `FinancialPdfService.generateFinancialReportPdf(FinancialPdfData)` 的 openhtmltopdf 流水线；新建 Thymeleaf 模板 `templates/BenchmarkReportPdf.html`（参照 `PortfolioDetailViewPdf.html`）。
- **数据取数**（全部已有接口）：
  - Actuals 12 个月：`fiDataQueryService.getLatestOfficialData(...)` + `DateUtil.offsetMonth(-11)`（`FinancialPdfService` 已有同款片段）
  - Committed Forecast：`FinancialForecastHistoryService`（latest 版本）
  - System Forecast：`FinancialForecastDataService.build24MonthsForecastDataForAllCompany` 产出
  - 公司基础信息：`companyRepository` + `InviteService`（logo、status、description、currency）
- **6 个季度指标**（需求 3.2.2）在 `QuarterlyMetricCalculator` 中新增；分母为 0 返回 0（与需求约定一致）。**注意：** 现有 `FiDataCalculateServiceImpl` / `MetricEnum` 提供的是月度值，季度聚合需自行实现（SUM 3 个月值，再按公式合成），不要在月度引擎里硬改。

### 3.5 存储三处落地
| 目标 | 现有能力 | 实现点 |
|------|----------|--------|
| S3（审计留存） | `FileService.upload` 支持 `MultipartFile`；需要补一个 `upload(bytes, filename, contentType)` 重载或直接调 `AbstractStorage.putObject` | 扩展 `FileServiceImpl` |
| SharePoint | 新 `SharePointClient.upload(folderPath, fileName, bytes)` | 新写 |
| LG “Documents - Company” 文件夹 | `new Document()` + `type=1` + `folder=<Benchmark Report category>` + `invite=company` + `createdBy="1"` + `documentService.savaDocument(doc)` | 参考 `CompanyDocumentationServiceImpl.addDocuments` 第 140–152 行 |
> 需求原话 “如果没有公司文件夹需要创建” —— 在 `Document/Folder` 模型中 folder 是公司共享枚举（不按公司建），无需真正建库表文件夹；只要该 `Document` 写到目标 company 下即可。若业务真正要求 “分类名称=Benchmark Report”，需在 `CompanyDocumentationCategory` 新插入种子数据（增量 SQL）。

### 3.6 通知
- 新建邮件类型 `EmailTypeEnum.BENCHMARK_REPORT_GENERATED`
- 新建 Thymeleaf 模板 `templates/email/BenchmarkReportNotice.html`
- 收件人 `Nico Carlson` 的邮箱配置化：`cio.benchmark-report.sme-email`（避免硬编码）
- **触发时机**：需求 4.2 画的流程图里 “所有报告生成后再发通知”，但 6.1 又写 “任何单个报告生成并成功上传后立即发送”。**存在矛盾，建议 PRD 评审时确认**。倾向后者（per-company），与下游 “单页摘要” 流程解耦更自然。
- 错误日志：SendGrid 失败、SP 失败、PDF 失败都记录在 `BenchmarkReportRecord.status/errorMsg`，复用 `Slf4j log.error`（需求明确不发运维邮件）。

---

## 四、数据有效性筛选（需求 3.1 / 4.2）

> “仅为拥有实际财务数据的公司生成报告”、“验证公司生成报告的这个季度是否有实际数据（Actuals）”

判定建议：
- 取报告对应的季度 3 个月，查询 `financial_normalization_current` 或 `company_quickbooks_data` 中任一月份 `data_source='ACTUALS'` 且 `close_month_date` 覆盖该季度。
- 可复用 `FiDataCalculateServiceImpl.getLatestOfficialData(...)`，如果返回空或其 `dDate` < 季末 → 跳过该公司。

---

## 五、调度期次语义对齐

需求 3.1 说 “Q1 报告在 5 月 1 日生成”，而一般语义 Q1 = Jan–Mar，次月 1 日 = 4/1；Q1 → 5/1 暗示 “季末 = 3 月末 → 5 月 1 日生成” 意味着是**季末所在月之后的次月**（= 季末 + 2 个月）。**再次建议在 PRD 评审时与业务确认**。
- 若按 “季末次月 1 日”（常规口径） → cron `cron(0 2 1 1,4,7,10 ? *)`
- 若按需求文字 Q1→5/1 → cron `cron(0 2 1 2,5,8,11 ? *)`

当前代码里 `BeginningOfMonthRemind` 是 `cron(0 0 1 * ? *)` 每月一号，可作为 cron 语法对照。

---

## 六、建议的开发顺序（5 个 PR，可独立交付）

1. **SharePoint 客户端 + 配置**（stub 可 mock，独立评审、独立接 Nacos secret）
2. **季度指标计算器** + 单元测试（纯函数，易验证需求 3.2.2 的 6 个公式）
3. **PDF 模板 + Builder**（可手动触发 API `/benchmark/report/preview?companyId=...`）
4. **BenchmarkReportService 编排 + 三处落地 + 邮件**（带 `BenchmarkReportRun/Record` DDL）
5. **接入 FixedScheduleTypeEnum** + E2E 冒烟

---

## 七、需求中仍需澄清的点

1. **邮件触发时机**：每公司成功后即发 vs 全量跑完后发一封 — §4.2 与 §6.1 描述冲突。
2. **季度语义**：Q1 报告在 5/1 还是 4/1 生成 — §3.1 文字与常规口径不一致。
3. **SME 收件人是否可配置**：是否允许配置成组；Nico 离职后如何交接。
4. **"Documents - Company 文件夹"** 是否需要新增一个分类（Category = “Benchmark Report”），还是归到已有某分类下。
5. **重跑 / 补跑策略**：失败公司是否需要第二天自动重试；是否允许运营手工点按季度重跑某公司（建议实现 `POST /benchmark/report/run` 管理端入口）。
6. **历史保留策略**：S3/SP 是否覆盖同名文件，还是按生成时间追加版本后缀。

---

## 八、风险点

| 风险 | 影响 | 缓解 |
|------|------|------|
| SharePoint 目录结构依赖租户配置 | 上线被 path 卡住 | 引入 `SharePointProperties.rootPath`，预生产跑 dry-run |
| 百家公司级批量生成 PDF 内存压力 | OOM / 超时 | 循环内单公司处理完立即释放 `byte[]`；必要时走 SQS 拆分消息到 `BenchmarkReportPerCompany` 枚举逐一处理（项目已有该模式：`SaveCompanyQuickbooksDataEveryday`） |
| 指标计算与前端展示不一致 | 需求 §7 红线 | 复用 `MetricExtractor` 取的原始月度值，只在外层做季度聚合；同时加入与 `BenchmarkingServiceImpl` 一致性快照测试 |
| SendGrid 白名单限制（stage/uat） | 测试环境邮件被吞 | `EmailServiceImpl` 已有 whitelist 逻辑，部署前把 Nico 加入白名单 |
| 公司名包含 `/ \ :` 等 SP 非法字符 | 上传失败 | 文件名 sanitize：`[^A-Za-z0-9_.-]` → `_` |

---

## 九、一句话结论

**项目已具备 PDF 生成、调度、存储、邮件、基准计算 90% 的基础设施**；本需求的实现重心是：
1) 新增 SharePoint/Graph 外部集成；
2) 在 `fi/benchmarkreport/` 新增一个领域薄层做**编排**；
3) 在 `FixedScheduleTypeEnum` 加一条 cron 让调度自动接入。

预计工作量：**后端 8–12 人日**，不含 SharePoint 租户/App 注册等运维协同。
