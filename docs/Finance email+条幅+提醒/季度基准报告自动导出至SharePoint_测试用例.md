# 测试用例：季度基准报告自动导出至 SharePoint

- **需求来源**：`docs/Finance email+条幅+提醒/季度基准报告自动导出至SharePoint需求.md`
- **生成时间**：2026-04-23

---

## 需求清单

| #   | 需求类型 | 需求描述 |
|-----|----------|----------|
| R1  | 功能需求 | 每季度自动生成一次基准报告 |
| R2  | 业务规则 | 生成时机 = 季末的次月第一天（Q1 → 5/1、Q2 → 8/1、Q3 → 11/1、Q4 → 次年 2/1） |
| R3  | 业务规则 | 仅为拥有实际财务数据（Actuals）的公司生成报告；当季无 Actuals 的公司跳过，不生成报告 |
| R4  | 业务规则 | 使用报告生成时最新的最终化财务和基准数据 |
| R5  | UI 需求  | 报告含公司 Logo、公司名称、公司状态 |
| R6  | UI 需求  | 报告含公司简介（如有） |
| R7  | 数据需求 | Financial Entry 实际数据（Actuals）：从 closed month 往回推 12 个月 |
| R8  | 数据需求 | Committed Forecast：完整数据集，始终为最新版本 |
| R9  | 数据需求 | System Generated Forecast：完整数据集，始终为最新版本 |
| R10 | 业务规则 | ARR Growth Rate 公式：`ARR_Growth_quarter = (ARR_end_of_quarter - ARR_start_of_quarter) / ARR_start_of_quarter` |
| R11 | 边界条件 | ARR Growth 特殊处理：ARR_start = 0 → 0；ARR_start = NA → 0；ARR_start 为负 → 分母用绝对值 |
| R12 | 业务规则 | Gross Margin 公式：`Gross_Margin_quarter = Gross_Profit_q / Gross_Revenue_q`，分子分母为季度内月度求和 |
| R13 | 业务规则 | Monthly Net Burn Rate 公式：`Monthly_Net_Burn_quarter = [SUM(Net Income) - SUM(Capitalized R&D)] / 3` |
| R14 | 业务规则 | Monthly Runway 公式：`Monthly_Runway_quarter = Cash_at_quarter_end / Monthly_Net_Burn_quarter`，遵循 LG 前端 NA 显示逻辑 |
| R15 | 业务规则 | Rule of 40 公式：`Rule_of_40_quarter = (Net_Profit_Margin_q + MRR_YoY_Growth_Rate_q) × 100%`，各项为季度内月度求和 |
| R16 | 业务规则 | Sales Efficiency 公式：`Sales_Efficiency_quarter = (S&M_Expenses_q + S&M_Payroll_q) / New_MRR_LTM_q` |
| R17 | 边界条件 | 数据完整性：分母为 0 时记录并显示为 0（非 NULL） |
| R18 | 业务规则 | 分发流程顺序：生成→验证 Actuals→PDF 生成→SharePoint 上传→LG 文件夹下载→SME 通知→错误日志 |
| R19 | 功能需求 | 生成 PDF 格式报告 |
| R20 | 功能需求 | PDF 上传至 SharePoint 路径：`SharePoint / Investment Team / LG Benchmarks / [CompanyName]` |
| R21 | 功能需求 | 同时下载至 LG 应用内 `Documents - Company` 文件夹；若该公司文件夹不存在则创建 |
| R22 | 数据需求 | LG 应用内文件创建人记录为 `System` |
| R23 | UI 需求  | 文件命名格式：`[CompanyName]_Benchmark_Report_[Quarter]_[Year].pdf` |
| R24 | 功能需求 | 所有报告生成并成功上传 SharePoint 后，向 SME（Nico Carlson）发送一封汇总通知邮件 |
| R25 | 业务规则 | 通知触发点：所有报告生成后再发通知（一次批量汇总，不逐公司发送） |
| R26 | UI 需求  | 通知邮件内容说明基准报告已生成并可供审阅 |
| R27 | 业务规则 | 无需额外发送开发团队邮件通知（依赖后端日志） |
| R28 | 功能需求 | PDF 生成失败 → 记录错误日志 |
| R29 | 功能需求 | SharePoint 上传失败 → 记录错误日志 |
| R30 | 功能需求 | 后端日志完整记录各公司报告的成功/失败状态 |
| R31 | 数据需求 | 报告数据与报告生成时 LG 应用中显示的基准值一致 |
| R32 | 数据需求 | 报告中基准计算方式与 LG 基准模块所用方式相同 |

---

## 测试用例

### 一、报告生成调度与覆盖范围

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | Q1 报告在 5 月 1 日触发生成 | 系统服务器时间 2026-05-01 00:00；已进入 5 月 | 定时任务按计划运行 | 系统触发 Q1 2026 季度基准报告生成流程，为所有符合条件的公司生成报告 |
| TC-002 | Q2 报告在 8 月 1 日触发生成 | 系统服务器时间 2026-08-01 | 任务运行 | 触发 Q2 2026 报告生成 |
| TC-003 | Q3 报告在 11 月 1 日触发生成 | 系统服务器时间 2026-11-01 | 任务运行 | 触发 Q3 2026 报告生成 |
| TC-004 | Q4 报告在次年 2 月 1 日触发生成 | 系统服务器时间 2027-02-01 | 任务运行 | 触发 Q4 2026 报告生成 |
| TC-005 | 非季末次月 1 日不触发 | 系统服务器时间 2026-06-01 | 任务运行 | 不触发季度报告生成 |
| TC-006 | 每季度仅生成一次 | 2026-05-01 报告已生成；2026-05-02 任务再次被触发 | 再次运行任务 | 系统不重复生成 Q1 2026 报告 |
| TC-007 | 有 Actuals 的公司生成报告 | Company A 在 Q1 有 Actuals 数据 | 2026-05-01 任务运行 | 为 Company A 生成 Q1 2026 PDF 报告 |
| TC-008 | 无 Actuals 的公司跳过 | Company B 在 Q1 没有任何 Actuals 数据 | 2026-05-01 任务运行 | 不为 Company B 生成报告；后端日志记录"跳过 - 无 Actuals 数据" |
| TC-009 | 当季部分月份有 Actuals 的公司生成报告 | Company C 在 Q1 仅 3 月有 Actuals，1/2 月无数据 | 任务运行 | 为 Company C 生成报告（只要当季有任一 Actuals 即生成） |
| TC-010 | 使用最新最终化财务与基准数据 | 2026-04-30 23:59 公司 A 财务数据被修订 | 2026-05-01 任务运行读取数据 | 报告使用 2026-04-30 23:59 修订后的最新数据 |

### 二、财务绩效快照内容

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-011 | 报告包含公司 Logo、名称、状态 | Company A 已上传 Logo，名称 = SocialLadder，状态 = Active | 查看生成的 PDF 首页 | 展示 Logo、`SocialLadder`、状态 `Active` |
| TC-012 | 无 Logo 时仍生成报告 | Company B 未上传 Logo | 查看 PDF | Logo 位置空白或使用默认占位，不阻塞报告生成 |
| TC-013 | 公司简介存在时展示 | Company A Company Overview 有 `Company Introduction` 文本 | 查看 PDF | 展示完整公司简介文本 |
| TC-014 | 公司简介缺失时不展示且不阻塞 | Company B 无公司简介 | 查看 PDF | 不显示公司简介段落；报告其他部分正常 |
| TC-015 | Actuals 范围为 closed month 往回推 12 个月 | closed month = 2026-03；Financial Entry 2025-04 ~ 2026-03 均有数据 | 查看 PDF 的 Actuals 明细 | 展示从 2025-04 到 2026-03 共 12 个月的 Actuals 数据 |
| TC-016 | Committed Forecast 完整数据集最新版 | Company A 有 Committed Forecast 数据 2026-04 ~ 2027-12 | 查看 PDF | 完整展示 CF 所有月份，使用最新版本数据 |
| TC-017 | System Generated Forecast 完整数据集最新版 | Company A 有 SGF 数据 | 查看 PDF | 完整展示 SGF 所有月份，使用最新版本数据 |
| TC-018 | 报告含季度关键指标基准信息 | Company A Q1 2026 六项指标均可计算 | 查看 PDF 基准指标板块 | 展示全部 6 个季度基准指标及其计算结果 |

### 三、基准指标 - ARR Growth Rate

公式：`ARR_Growth_quarter = (ARR_end_of_quarter - ARR_start_of_quarter) / ARR_start_of_quarter`

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-019 | 正常数据计算 ARR Growth | ARR_start = 100万，ARR_end = 130万 | 查看报告 ARR Growth | 显示 30%（计算：(130-100)/100 = 0.30） |
| TC-020 | ARR_start = 0 特殊处理 | ARR_start = 0，ARR_end = 100万 | 查看报告 | 显示 0（按特殊规则置 0） |
| TC-021 | ARR_start = NA 特殊处理 | ARR_start = NA，ARR_end = 100万 | 查看报告 | 显示 0 |
| TC-022 | ARR_start 为负值分母用绝对值 | ARR_start = -50万，ARR_end = 50万 | 查看报告 | 显示 200%（计算：(50-(-50))/|-50| = 100/50 = 2.0 = 200%） |
| TC-023 | ARR 下降的情况 | ARR_start = 100万，ARR_end = 80万 | 查看报告 | 显示 -20%（计算：(80-100)/100 = -0.20） |
| TC-024 | ARR_end = ARR_start 增长率为 0 | ARR_start = ARR_end = 100万 | 查看报告 | 显示 0%（计算：0/100 = 0） |

### 四、基准指标 - Gross Margin

公式：`Gross_Margin_quarter = Gross_Profit_q / Gross_Revenue_q`（分子分母为季度内月度求和）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-025 | 正常数据计算 Gross Margin | Q1 三月毛利 20/30/50 万，收入 50/60/90 万；Profit_q = 100 万，Revenue_q = 200 万 | 查看报告 Gross Margin | 显示 50%（计算：100/200 = 0.5） |
| TC-026 | 分母 Gross_Revenue_q = 0 显示 0 | Q1 三月收入均为 0；毛利 10 万 | 查看报告 | 显示 0（遵循 R17 分母为 0 规则） |
| TC-027 | 某月缺失数据仍按现有月份求和 | Q1 仅 2/3 月有数据，1 月无数据 | 查看报告 | Profit_q/Revenue_q 按 2、3 月求和计算，不阻塞 |

### 五、基准指标 - Monthly Net Burn Rate

公式：`Monthly_Net_Burn_quarter = [SUM(Net Income) - SUM(Capitalized R&D)] / 3`

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-028 | 正常数据计算 Monthly Net Burn | Q1 三月 Net Income = -30/-30/-30 万；Capitalized R&D = 3/3/3 万 | 查看报告 | 显示 -31 万（计算：[(-90) - 9]/3 = -99/3 = -33，修正：[SUM(-90) - SUM(9)]/3 = -99/3 = -33；显示 -33 万） |
| TC-029 | Capitalized R&D = 0 场景 | Q1 Net Income SUM = -60 万；Capitalized R&D SUM = 0 | 查看报告 | 显示 -20 万（计算：(-60 - 0)/3 = -20） |
| TC-030 | Net Income 为正不烧钱场景 | Q1 Net Income SUM = +30 万；Capitalized R&D SUM = 3 万 | 查看报告 | 显示 9 万（计算：(30 - 3)/3 = 9） |

### 六、基准指标 - Monthly Runway

公式：`Monthly_Runway_quarter = Cash_at_quarter_end / Monthly_Net_Burn_quarter`

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-031 | 正常数据计算 Monthly Runway | Cash_at_quarter_end = 600 万；Monthly_Net_Burn_quarter = 20 万（绝对值） | 查看报告 | 显示 30（计算：600/20 = 30 个月） |
| TC-032 | 烧钱率为 0（分母=0）按前端 NA 逻辑 | Monthly_Net_Burn_quarter = 0 | 查看报告 | 按 LG 前端表格 NA 场景显示（例如 NA 或 ∞，与前端一致） |
| TC-033 | 烧钱率为正（盈利）按前端 NA 逻辑 | Monthly_Net_Burn_quarter > 0（非烧钱） | 查看报告 | 与 LG 前端表格在该场景下的显示一致 |
| TC-034 | 季度末现金为 0 | Cash_at_quarter_end = 0；Monthly_Net_Burn_quarter = -20 万 | 查看报告 | 显示 0（计算：0/(-20) = 0） |

### 七、基准指标 - Rule of 40

公式：`Rule_of_40_quarter = (Net_Profit_Margin_q + MRR_YoY_Growth_Rate_q) × 100%`

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-035 | 正常数据计算 Rule of 40 | Q1 三月 Net_Profit_Margin 之和 = 0.15；MRR_YoY 之和 = 0.30 | 查看报告 | 显示 45%（计算：(0.15 + 0.30)×100% = 45%） |
| TC-036 | Net Profit Margin 为负的情况 | 之和 = -0.10；MRR_YoY 之和 = 0.50 | 查看报告 | 显示 40%（计算：(-0.10 + 0.50)×100% = 40%） |
| TC-037 | MRR_YoY 为 0 的情况 | Net_Profit_Margin 之和 = 0.20；MRR_YoY 之和 = 0 | 查看报告 | 显示 20% |

### 八、基准指标 - Sales Efficiency

公式：`Sales_Efficiency_quarter = (S&M_Expenses_q + S&M_Payroll_q) / New_MRR_LTM_q`

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-038 | 正常数据计算 Sales Efficiency | S&M_Expenses_q = 30 万；S&M_Payroll_q = 20 万；New_MRR_LTM_q = 100 万 | 查看报告 | 显示 0.5（计算：(30+20)/100 = 0.5） |
| TC-039 | 分母 New_MRR_LTM_q = 0 显示 0 | New_MRR_LTM_q = 0；S&M 合计 = 50 万 | 查看报告 | 显示 0（遵循 R17 分母为 0 规则） |
| TC-040 | S&M 合计为 0 | S&M 合计 = 0；New_MRR_LTM_q = 100 万 | 查看报告 | 显示 0 |

### 九、数据完整性处理

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-041 | 分母为 0 各指标统一显示 0 | 造数使得 ARR_start=0、Gross_Revenue_q=0、New_MRR_LTM_q=0 | 查看报告 | 对应指标均显示 0，不显示 NULL/null/空字符串/错误 |
| TC-042 | 字段缺失不阻塞报告生成 | 某公司某指标上游字段为 NA | 生成报告 | 报告仍正常生成；该指标按规则处理，不抛出异常 |

### 十、PDF 生成与文件命名

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-043 | 输出文件为 PDF 格式 | 公司 A Q1 报告生成 | 查看生成文件 | 文件扩展名为 `.pdf`，可被 PDF 阅读器打开 |
| TC-044 | 文件命名格式标准 | CompanyName = SocialLadder，Q1 2026 | 查看文件名 | 文件名为 `SocialLadder_Benchmark_Report_Q1_2026.pdf` |
| TC-045 | Q2 文件名 | Company X，Q2 2026 | 查看文件名 | `X_Benchmark_Report_Q2_2026.pdf` |
| TC-046 | Q4 文件名按季度而非生成月命名 | Company X，Q4 2026 报告在 2027-02-01 生成 | 查看文件名 | `X_Benchmark_Report_Q4_2026.pdf`（季度为 Q4、年份为 2026，不是 2027） |
| TC-047 | 含空格/特殊字符的公司名 | CompanyName = `Card Medic` | 查看文件名 | 命名符合规范（按需求原文格式处理空格，如保留为 `Card Medic_Benchmark_Report_Q1_2026.pdf`） |

### 十一、SharePoint 上传与 LG 应用内存储

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-048 | 上传至 SharePoint 正确路径 | Company A Q1 报告生成成功 | 查看 SharePoint | 文件存储于 `SharePoint / Investment Team / LG Benchmarks / Company A` |
| TC-049 | 多公司上传至各自子文件夹 | Company A、Company B 均生成 | 查看 SharePoint | 两个文件分别落在 `.../LG Benchmarks/Company A` 与 `.../LG Benchmarks/Company B` |
| TC-050 | LG 应用内下载至 Documents - Company 文件夹 | Company A 在 LG 应用内已有 `Documents - Company` 公司文件夹 | 查看 LG 应用 | 报告 PDF 出现在 Company A 的 `Documents - Company` 文件夹下 |
| TC-051 | 公司文件夹不存在时自动创建 | Company B 在 LG 应用内无公司文件夹 | 报告生成流程执行 | 系统自动创建 Company B 文件夹后再下载 PDF 进入 |
| TC-052 | LG 应用内文件创建人为 System | 任意公司报告下载入 LG 应用后 | 查看文件属性 | 创建人字段 = `System` |
| TC-053 | SharePoint 与 LG 应用内文件一致 | Company A Q1 报告已成功上传与下载 | 对比两处文件 | 文件名、文件内容（字节级）完全一致 |

### 十二、SME 邮件通知

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-054 | 所有报告完成后发送汇总邮件 | Q1 生成涉及 10 家公司，全部成功上传 SharePoint | 观察邮件发送 | 向 Nico Carlson 发送 1 封汇总通知邮件 |
| TC-055 | 收件人固定 | 任意季度触发 | 查看邮件 To | 仅 `Nico Carlson` |
| TC-056 | 邮件内容说明报告已可审阅 | 收到邮件 | 查看正文 | 正文包含"基准报告已生成并可供审阅"等同等含义的文案 |
| TC-057 | 部分公司上传失败时依然发通知 | 10 家公司中 2 家 SharePoint 上传失败，8 家成功 | 观察邮件 | 仍向 Nico Carlson 发送汇总通知，通知正文体现成功/失败概况（依需求以后端日志为准，至少通知不被阻塞） |
| TC-058 | 每季度仅发一封 SME 邮件 | Q1 流程完毕 | 观察邮件数量 | Nico Carlson 当季度仅收到 1 封 SME 通知邮件 |
| TC-059 | 不逐公司发送邮件 | Q1 涉及 10 家公司 | 观察 Nico Carlson 邮箱 | 不存在 10 封对应各公司的邮件，仅 1 封汇总 |
| TC-060 | 不向开发团队发送通知邮件 | 任意运行 | 观察开发团队邮箱 | 无系统通知邮件 |

### 十三、错误处理与日志

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-061 | PDF 生成失败记录日志 | 模拟 Company A PDF 生成抛异常 | 运行任务并查看后端日志 | 日志记录 Company A PDF 生成失败，包含时间戳、公司名、错误信息 |
| TC-062 | SharePoint 上传失败记录日志 | 模拟 Company B SharePoint 上传失败（权限/网络） | 查看后端日志 | 日志记录 Company B 上传失败 |
| TC-063 | 成功公司日志记录 | Company C 报告生成并上传成功 | 查看日志 | 日志记录 Company C 成功状态，含上传路径 |
| TC-064 | 批量运行含成功与失败的公司状态完整 | 一批次 5 家公司：3 家成功、1 家 PDF 失败、1 家上传失败 | 查看日志 | 5 家公司均有独立状态记录，状态准确 |
| TC-065 | 单家失败不影响其他公司继续生成 | Company A 失败 | 观察其他公司 | Company B、C、D... 正常生成并上传 |
| TC-066 | 失败公司 SharePoint 无部分文件 | Company A PDF 生成失败 | 查看 SharePoint | Company A 路径下无 Q1 2026 文件（避免上传空/损坏文件） |

### 十四、数据一致性

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-067 | 报告数据与 LG 应用基准展示一致 | 2026-05-01 触发生成 Company A Q1 报告 | 对比 PDF 与 LG 应用基准模块同时刻的展示 | 公司 A 的六项指标值与 LG 应用中显示值一致 |
| TC-068 | 报告基准计算方式与 LG 模块一致 | 同 TC-067 | 对比计算逻辑与中间量 | 报告与 LG 模块使用相同的月度汇总口径（季度求和方式、季度末快照方式） |
| TC-069 | 报告生成后上游修订不影响已生成报告 | 2026-05-01 报告生成后；2026-05-02 Company A 2026-Q1 数据被修订 | 查看已存 PDF | 已上传 SharePoint/LG 内的 PDF 内容不变；若需反映修订，需下季度或人工重新触发 |
| TC-070 | 季度边界月份的 Actuals 正确归属 | 某月数据在系统里被修正跨季度（如 3 月数据在 4 月修订） | 5/1 生成 Q1 报告 | 3 月数据归入 Q1；不影响 Q2 |

---

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1  | 每季度生成一次 | ✅ 已覆盖 | TC-001~TC-004, TC-006 | |
| R2  | 生成时机（季末次月 1 日） | ✅ 已覆盖 | TC-001~TC-005 | Q1/Q2/Q3/Q4 全覆盖 |
| R3  | 仅为有 Actuals 的公司生成 | ✅ 已覆盖 | TC-007, TC-008, TC-009 | |
| R4  | 使用最新最终化数据 | ✅ 已覆盖 | TC-010 | |
| R5  | Logo、名称、状态 | ✅ 已覆盖 | TC-011, TC-012 | |
| R6  | 公司简介（如有） | ✅ 已覆盖 | TC-013, TC-014 | |
| R7  | Actuals 从 closed month 往回推 12 月 | ✅ 已覆盖 | TC-015 | |
| R8  | Committed Forecast 完整数据 | ✅ 已覆盖 | TC-016 | |
| R9  | System Generated Forecast 完整数据 | ✅ 已覆盖 | TC-017 | |
| R10 | ARR Growth Rate 公式 | ✅ 已覆盖 | TC-019, TC-023, TC-024 | 含公式计算验证 |
| R11 | ARR Growth 特殊处理（0/NA/负） | ✅ 已覆盖 | TC-020, TC-021, TC-022 | |
| R12 | Gross Margin 公式 | ✅ 已覆盖 | TC-025, TC-027 | |
| R13 | Monthly Net Burn Rate 公式 | ✅ 已覆盖 | TC-028, TC-029, TC-030 | |
| R14 | Monthly Runway 公式与 NA 逻辑 | ✅ 已覆盖 | TC-031, TC-032, TC-033, TC-034 | |
| R15 | Rule of 40 公式 | ✅ 已覆盖 | TC-035, TC-036, TC-037 | |
| R16 | Sales Efficiency 公式 | ✅ 已覆盖 | TC-038, TC-039, TC-040 | |
| R17 | 分母为 0 显示 0 而非 NULL | ✅ 已覆盖 | TC-026, TC-039, TC-041 | |
| R18 | 分发流程顺序 | ✅ 已覆盖 | TC-043~TC-054, TC-061~TC-066 | 各环节按序覆盖 |
| R19 | PDF 格式 | ✅ 已覆盖 | TC-043 | |
| R20 | SharePoint 路径 | ✅ 已覆盖 | TC-048, TC-049 | |
| R21 | LG 应用内下载与文件夹创建 | ✅ 已覆盖 | TC-050, TC-051 | |
| R22 | 创建人 = System | ✅ 已覆盖 | TC-052 | |
| R23 | 文件命名格式 | ✅ 已覆盖 | TC-044~TC-047 | 含 Q4 跨年、特殊公司名 |
| R24 | 所有报告成功后发 SME 邮件 | ✅ 已覆盖 | TC-054, TC-055, TC-056 | |
| R25 | 触发点：批量汇总一次发 | ✅ 已覆盖 | TC-058, TC-059 | |
| R26 | 邮件内容 | ✅ 已覆盖 | TC-056 | |
| R27 | 不发开发团队邮件 | ✅ 已覆盖 | TC-060 | |
| R28 | PDF 失败记录日志 | ✅ 已覆盖 | TC-061, TC-066 | |
| R29 | SharePoint 上传失败记录日志 | ✅ 已覆盖 | TC-062 | |
| R30 | 后端日志完整记录成功/失败 | ✅ 已覆盖 | TC-063, TC-064, TC-065 | |
| R31 | 报告数据与 LG 应用一致 | ✅ 已覆盖 | TC-067, TC-069, TC-070 | |
| R32 | 计算方式与 LG 基准模块一致 | ✅ 已覆盖 | TC-068 | |

**覆盖率：100%**（32/32 需求全部已覆盖）
