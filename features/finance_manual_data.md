# finance_manual_data 表 — 字段存入逻辑详解

> 版本：v2.0
> 创建时间：2026-03-19
> 关联文档：[Financial Entry 指标公式](./Financial-Entry-Metrics-Formulas.md)

---

## 1. 表概述

| 属性 | 值 | 
|------|-----|
| 表名 | `finance_manual_data` |
| 实体类 | `FinanceManualData` → `FinanceManualDataAbstract` → `AbstractCustomEntity` |
| 数据粒度 | 一条记录 = 一个公司 + 一个月份 + 一个版本 |
| 用途 | 存储 Financial Entry（公司实际/历史财务数据） |

---

## 2. 存入场景总览

本表有 **2 个存入场景**：

| 场景 | 触发方式 | 数据来源 | 代码入口 |
|------|---------|---------|---------|
| **场景 A：用户手动录入** | 用户在前端 Financial Entry 页面填写数据并提交 | 前端用户输入的各指标值 | 提交后由系统写入本表 |
| **场景 B：QuickBooks 导入** | 公司从 Automatic 模式切换为 Manual 模式 | Redshift 中的 QuickBooks 损益表与资产负债表数据 | 切换时由系统一次性从 Redshift 写入本表 |

> **注意**：场景 A 中数据先暂存到 `finance_manual_data_temp` 表（state='0'），Submit 后才写入 `finance_manual_data` 正式表。  
> 场景 B 各字段对应的 Redshift 表与列名详见 [Financial-Entry-Metrics-Formulas 1.7](./Financial-Entry-Metrics-Formulas.md#17-数据录入模式与-quickbooks-字段映射)。

---

## 3. 每个字段的存入逻辑

### 3.1 P&L（损益表）字段

#### `gross_revenue` — 总收入

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="Gross Revenue"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `TotalIncome` | 将该列转为数值后写入本表 `gross_revenue` |

#### `cogs` — 销售成本

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="COGS"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `Cogs` | 将该列转为数值后写入本表 `cogs` |

#### `operating_expenses` — 运营费用

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="Operating Expenses"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `TotalExpenses` | 将该列转为数值后写入本表 `operating_expenses` |

#### `sm_expenses_percent` — S&M 费用

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="S&M Expenses"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `SMExpense` | 将该列转为数值后写入本表 `sm_expenses_percent` |

#### `sm_payroll_percent` — S&M 薪酬

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="S&M Payroll"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `SMPayroll`，表 `company_quickbooks` 的 Payroll 比例配置 | 按比例配置拆分后写入本表 `sm_payroll_percent` |

#### `rd_expenses_percent` — R&D 费用

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="R&D Expenses"].data` | 若为空则补 0 后存入 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `RDExpense` | 将该列转为数值后写入本表 `rd_expenses_percent` |

#### `rd_payroll_percent` — R&D 薪酬

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="R&D Payroll"].data` | 若为空则补 0 后存入 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `RDPayroll`，表 `company_quickbooks` 的 Payroll 比例配置 | 按比例配置拆分后写入本表 `rd_payroll_percent` |

#### `ga_expenses_percent` — G&A 费用

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="G&A Expenses"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `GAExpense` | 将该列转为数值后写入本表 `ga_expenses_percent` |

#### `ga_payroll_percent` — G&A 薪酬

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="G&A Payroll"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `GAPayroll` | 将该列转为数值后写入本表 `ga_payroll_percent` |

#### `miscellaneous_operating_expenses` — 杂项运营费用

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 由系统按公式计算（非前端直接输入） | 运营费用减掉六项子费用/薪酬后写入本表 `miscellaneous_operating_expenses`<br>**数据元**：等式右侧均来自本表 `finance_manual_data` 同名字段 |
| **场景 B：QB 导入** | 不写入 | 本列存为 **null**；展示时用「运营费用减六项子项」公式实时计算<br>**数据元**：公式输入来自 Redshift 表 `QuickbooksProfitAndLoss` 列 `TotalExpenses` 及各子项对应列，具体列名见 [Financial Entry 指标公式 — 1.7](./Financial-Entry-Metrics-Formulas.md#17-数据录入模式与-quickbooks-字段映射) |

#### `other_expenses` — 其他费用

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="Other Expenses"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `OtherIncome` | 将该列转为数值后写入本表 `other_expenses` |

#### `capitalized_rd` — 月度资本化 R&D

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `PL[text="Capitalized R&D (Monthly)"].data` | 若为空则补 0 后存入 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `RdCapitalized`（当月与上月） | 用「上月减当月」得到变动值，若结果大于 0 则按 0 写入本表 `capitalized_rd` |

### 3.2 Balance Sheet（资产负债表）字段

#### `cash` — 现金

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `BS[text="Cash"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `Cash` | 将该列转为数值后写入本表 `cash` |

#### `accounts_receivable` — 应收账款

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `BS[text="Accounts Receivable"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `AccountsReceivable` | 将该列转为数值后写入本表 `accounts_receivable` |

#### `assets_Other` — 其他资产

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `BS[text="Other Assets"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `OtherAssets` | 将该列转为数值后写入本表 `assets_Other` |

#### `accounts_payable` — 应付账款

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `BS[text="Accounts Payable"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `AccountsPayable` | 将该列转为数值后写入本表 `accounts_payable` |

#### `long_term_debt` — 长期债务

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `BS[text="Long-Term Debt"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `LongTermDebt` | 将该列转为数值后写入本表 `long_term_debt` |

#### `liabilities_other` — 其他负债

| 存入场景 | 数据来源 | 业务逻辑 |
|---------|---------|---------|
| **场景 A：手动录入** | 前端用户输入，JSON 字段 `BS[text="Other Liabilities"].data` | 直接存入，无计算 |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `OtherLiabilities` | 将该列转为数值后写入本表 `liabilities_other` |

### 3.3 元数据字段

#### `state` — 数据状态

| 存入场景 | 赋值逻辑 |
|---------|---------|
| **场景 A：手动录入** | 若公司设置了 `notificationUserId`（需 Founder 审核）：`state = '0'`（待审核）；否则：`state = null`（直接生效） |
| **场景 A：Founder 审核通过** | `companyUserSubmit()` 中 `state = null` |
| **场景 B：QB 导入** | 不设置 state，默认 null |

#### `version_at` — 版本时间

| 存入场景 | 赋值逻辑 |
|---------|---------|
| **场景 A：手动录入 Submit** | 无 `notificationUserId`：`= new Date().toInstant()`（当前时间）；<br>有 `notificationUserId`：沿用 `findMaxVersionAtByCompanyId` 的已有版本<br>**数据元**：版本号来自 `finance_manual_data.version_at` 聚合 |
| **场景 B：QB 导入** | `= new Date().toInstant()`，同一批数据共用同一个时间戳 |

#### `is_capitalize_rd` — 是否资本化 R&D

| 存入场景 | 赋值逻辑 |
|---------|---------|
| **场景 A：手动录入** | 固定设为 `true` |
| **场景 B：QB 导入** | `= (rdPayroll == 0 && RD 账户列表为空)`，即无 R&D Payroll 且无 RD 相关会计账户时为 true<br>**数据元**：rdPayroll 来自 Redshift/QuickBooks 映射；RD 账户列表来自公司/QuickBooks 配置 |

#### `currency` — 货币

| 存入场景 | 赋值逻辑 |
|---------|---------|
| **场景 A：手动录入** | 取 `company.currency`，若为空默认 `"USD"` |
| **场景 B：QB 导入** | 不单独设置，跟随公司配置 |

---

## 4. 存入后的下游影响

`finance_manual_data` 写入后，`financialEntrySubmit()` 依次触发以下操作：

```
finance_manual_data 写入完成
  │
  ├── 1. financialGrowthRateService.buildCompanyGrowthRate(companyId)
  │      → 重算 financial_growth_rate 表（先删后插）
  │
  ├── 2. financeForecastDataService.build24MonthsForecastData(companyId)
  │      → 发送 SQS 消息，异步重算 24 个月预测
  │      → 写入 financial_forecast_current 表
  │
  └── 3. financialNormalizedService.buildFinancialNormalizationForCompany(companyId)
         → 重算归一化数据
```

> **跨文件**：上述第 1、2 步的公式与数据来源详见 [financial_growth_rate 表](./financial_growth_rate.md)、[financial_forecast_current 表](./financial_forecast_current.md)。

---

## 5. 代码位置索引

| 类型 | 文件路径 |
|------|---------|
| 实体类 | `gstdev-cioaas-web/.../fi/domain/FinanceManualData.java` |
| 抽象父类 | `gstdev-cioaas-web/.../fi/domain/FinanceManualDataAbstract.java` |
| 前端 DTO（Raw） | `gstdev-cioaas-web/.../fi/contract/financeManualData/FinanceManualDataSaveInputRaw.java` |
| 前端 DTO（转换后） | `gstdev-cioaas-web/.../fi/contract/financeManualData/FinanceManualDataSaveInput.java` |
| 字段映射（text→field） | `gstdev-cioaas-web/.../fi/mapper/FinanceManualDataInputConverter.java` |
| Service（录入） | `gstdev-cioaas-web/.../fi/service/FinanceManualDataServiceImpl.java` |
| Service（提交） | `gstdev-cioaas-web/.../fi/service/FinancialStatementServiceImpl.java` |
| Service（QB 导入） | `gstdev-cioaas-web/.../fi/service/QuickbooksServiceImpl.java` |
| Repository | `gstdev-cioaas-web/.../fi/repository/FinanceManualDataRepository.java` |
