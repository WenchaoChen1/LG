# finance_manual_data 表 — 字段存入逻辑详解

> 版本：v2.0
> 创建时间：2026-03-19
> 关联文档：[Financial Entry 指标公式](./Financial-Entry-Metrics-Formulas.md)

---

## 1. 表概述


| 属性   | 值                                                                          |
| ---- | -------------------------------------------------------------------------- |
| 表名   | `finance_manual_data`                                                      |
| 实体类  | `FinanceManualData` → `FinanceManualDataAbstract` → `AbstractCustomEntity` |
| 数据粒度 | 一条记录 = 一个公司 + 一个月份 + 一个版本                                                  |
| 用途   | 存储 Financial Entry（公司实际/历史财务数据）                                            |


---

## 2. 存入场景总览

本表有 **2 个存入场景**：


| 场景                     | 触发方式                            | 数据来源                               | 代码入口                     |
| ---------------------- | ------------------------------- | ---------------------------------- | ------------------------ |
| **场景 A：用户手动录入**        | 用户在前端 Financial Entry 页面填写数据并提交 | 前端用户输入的各指标值                        | 提交后由系统写入本表               |
| **场景 B：QuickBooks 导入** | 公司从 Automatic 模式切换为 Manual 模式   | Redshift 中的 QuickBooks 损益表与资产负债表数据 | 切换时由系统一次性从 Redshift 写入本表 |


> **注意**：场景 A 中数据先暂存到 `finance_manual_data_temp` 表（state='0'），Submit 后才写入 `finance_manual_data` 正式表。  
> 场景 B 各字段对应的 Redshift 表与列名详见 [Financial-Entry-Metrics-Formulas 1.7](./Financial-Entry-Metrics-Formulas.md#17-数据录入模式与-quickbooks-字段映射)。

---

## 3. 每个字段的存入逻辑

### 3.1 P&L（损益表）字段

#### `gross_revenue` — 总收入


| 存入场景           | 数据来源                                                 | 业务逻辑                         |
| -------------- | ---------------------------------------------------- | ---------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="Gross Revenue"].data`       | 直接存入，无计算                     |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `TotalIncome` | 将该列转为数值后写入本表 `gross_revenue` |


#### `cogs` — 销售成本


| 存入场景           | 数据来源                                          | 业务逻辑                |
| -------------- | --------------------------------------------- | ------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="COGS"].data`         | 直接存入，无计算            |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `Cogs` | 将该列转为数值后写入本表 `cogs` |


#### `operating_expenses` — 运营费用


| 存入场景                    | 数据来源                                                   | 业务逻辑                                                                                                               |
| ----------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| **场景 A：手动录入**           | 前端用户输入，JSON 字段 `PL[text="Operating Expenses"].data`    | 直接存入用户输入的 OE 值                                                                                                     |
| **场景 A-auto：OE 子项自动拆分** | 用户输入 OE 总额 + 开启自动拆分开关                                  | OE 本身直接存入；同时**反向拆分**为 6 个子项（S&M/R&D/G&A 的 Expenses+Payroll），按历史 rate 比例分配。详见 [§4.1](#41-operating-expenses-子项自动拆分) |
| **场景 B：QB 导入**          | Redshift 表 `QuickbooksProfitAndLoss` 列 `TotalExpenses` | 将该列转为数值后写入本表 `operating_expenses`                                                                                  |


#### `sm_expenses_percent` — S&M 费用


| 存入场景           | 数据来源                                               | 业务逻辑                               |
| -------------- | -------------------------------------------------- | ---------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="S&M Expenses"].data`      | 直接存入，无计算                           |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `SMExpense` | 将该列转为数值后写入本表 `sm_expenses_percent` |


#### `sm_payroll_percent` — S&M 薪酬


| 存入场景           | 数据来源                                                                                     | 业务逻辑                              |
| -------------- | ---------------------------------------------------------------------------------------- | --------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="S&M Payroll"].data`                                             | 直接存入，无计算                          |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `SMPayroll`，表 `company_quickbooks` 的 Payroll 比例配置 | 按比例配置拆分后写入本表 `sm_payroll_percent` |


#### `rd_expenses_percent` — R&D 费用


| 存入场景           | 数据来源                                               | 业务逻辑                               |
| -------------- | -------------------------------------------------- | ---------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="R&D Expenses"].data`      | 若为空则补 0 后存入                        |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `RDExpense` | 将该列转为数值后写入本表 `rd_expenses_percent` |


#### `rd_payroll_percent` — R&D 薪酬


| 存入场景           | 数据来源                                                                                     | 业务逻辑                              |
| -------------- | ---------------------------------------------------------------------------------------- | --------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="R&D Payroll"].data`                                             | 若为空则补 0 后存入                       |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `RDPayroll`，表 `company_quickbooks` 的 Payroll 比例配置 | 按比例配置拆分后写入本表 `rd_payroll_percent` |


#### `ga_expenses_percent` — G&A 费用


| 存入场景           | 数据来源                                               | 业务逻辑                               |
| -------------- | -------------------------------------------------- | ---------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="G&A Expenses"].data`      | 直接存入，无计算                           |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `GAExpense` | 将该列转为数值后写入本表 `ga_expenses_percent` |


#### `ga_payroll_percent` — G&A 薪酬


| 存入场景           | 数据来源                                               | 业务逻辑                              |
| -------------- | -------------------------------------------------- | --------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="G&A Payroll"].data`       | 直接存入，无计算                          |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `GAPayroll` | 将该列转为数值后写入本表 `ga_payroll_percent` |


#### `miscellaneous_operating_expenses` — 杂项运营费用


| 存入场景           | 数据来源              | 业务逻辑                                                                                                                                                                                                                   |
| -------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **场景 A：手动录入**  | 由系统按公式计算（非前端直接输入） | 运营费用减掉六项子费用/薪酬后写入本表 `miscellaneous_operating_expenses` **数据元**：等式右侧均来自本表 `finance_manual_data` 同名字段                                                                                                                    |
| **场景 B：QB 导入** | 不写入               | 本列存为 **null**；展示时用「运营费用减六项子项」公式实时计算 **数据元**：公式输入来自 Redshift 表 `QuickbooksProfitAndLoss` 列 `TotalExpenses` 及各子项对应列，具体列名见 [Financial Entry 指标公式 — 1.7](./Financial-Entry-Metrics-Formulas.md#17-数据录入模式与-quickbooks-字段映射) |


#### `other_expenses` — 其他费用


| 存入场景           | 数据来源                                                 | 业务逻辑                          |
| -------------- | ---------------------------------------------------- | ----------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="Other Expenses"].data`      | 直接存入，无计算                      |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksProfitAndLoss` 列 `OtherIncome` | 将该列转为数值后写入本表 `other_expenses` |


#### `capitalized_rd` — 月度资本化 R&D


| 存入场景           | 数据来源                                                         | 业务逻辑                                             |
| -------------- | ------------------------------------------------------------ | ------------------------------------------------ |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `PL[text="Capitalized R&D (Monthly)"].data`   | 若为空则补 0 后存入                                      |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `RdCapitalized`（当月与上月） | 用「上月减当月」得到变动值，若结果大于 0 则按 0 写入本表 `capitalized_rd` |


### 3.2 Balance Sheet（资产负债表）字段

#### `cash` — 现金


| 存入场景                      | 数据来源                                         | 业务逻辑                                                                                                                                                                   |
| ------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **场景 A：手动录入**             | 前端用户输入，JSON 字段 `BS[text="Cash"].data`        | 直接存入                                                                                                                                                                   |
| **场景 A-auto：Cash 级联自动计算** | 用户修改某月 Cash + 指定级联范围                         | 当前月直接存入用户值；后续月份自动逐月递推：`Cash(t) = Cash(t−1) + NetIncome(t) − ΔAR(t) − ΔOtherAssets(t) + ΔAP(t)`，遇到用户手动输入 Cash 的月份（`isCalculateCash=false`）停止。详见 [§4.2](#42-cash-级联自动计算) |
| **场景 B：QB 导入**            | Redshift 表 `QuickbooksBalanceSheet` 列 `Cash` | 将该列转为数值后写入本表 `cash`                                                                                                                                                    |


#### `accounts_receivable` — 应收账款


| 存入场景           | 数据来源                                                       | 业务逻辑                               |
| -------------- | ---------------------------------------------------------- | ---------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `BS[text="Accounts Receivable"].data`       | 直接存入，无计算                           |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `AccountsReceivable` | 将该列转为数值后写入本表 `accounts_receivable` |


#### `assets_Other` — 其他资产


| 存入场景           | 数据来源                                                | 业务逻辑                        |
| -------------- | --------------------------------------------------- | --------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `BS[text="Other Assets"].data`       | 直接存入，无计算                    |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `OtherAssets` | 将该列转为数值后写入本表 `assets_Other` |


#### `accounts_payable` — 应付账款


| 存入场景           | 数据来源                                                    | 业务逻辑                            |
| -------------- | ------------------------------------------------------- | ------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `BS[text="Accounts Payable"].data`       | 直接存入，无计算                        |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `AccountsPayable` | 将该列转为数值后写入本表 `accounts_payable` |


#### `long_term_debt` — 长期债务


| 存入场景           | 数据来源                                                 | 业务逻辑                          |
| -------------- | ---------------------------------------------------- | ----------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `BS[text="Long-Term Debt"].data`      | 直接存入，无计算                      |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `LongTermDebt` | 将该列转为数值后写入本表 `long_term_debt` |


#### `liabilities_other` — 其他负债


| 存入场景           | 数据来源                                                     | 业务逻辑                             |
| -------------- | -------------------------------------------------------- | -------------------------------- |
| **场景 A：手动录入**  | 前端用户输入，JSON 字段 `BS[text="Other Liabilities"].data`       | 直接存入，无计算                         |
| **场景 B：QB 导入** | Redshift 表 `QuickbooksBalanceSheet` 列 `OtherLiabilities` | 将该列转为数值后写入本表 `liabilities_other` |


### 3.3 元数据字段

#### `state` — 数据状态


| 存入场景                  | 赋值逻辑                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------ |
| **场景 A：手动录入**         | 若公司设置了 `notificationUserId`（需 Founder 审核）：`state = '0'`（待审核）；否则：`state = null`（直接生效） |
| **场景 A：Founder 审核通过** | `companyUserSubmit()` 中 `state = null`                                               |
| **场景 B：QB 导入**        | 不设置 state，默认 null                                                                    |


#### `version_at` — 版本时间


| 存入场景                 | 赋值逻辑                                                                                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **场景 A：手动录入 Submit** | 无 `notificationUserId`：`= new Date().toInstant()`（当前时间）； 有 `notificationUserId`：沿用 `findMaxVersionAtByCompanyId` 的已有版本 **数据元**：版本号来自 `finance_manual_data.version_at` 聚合 |
| **场景 B：QB 导入**       | `= new Date().toInstant()`，同一批数据共用同一个时间戳                                                                                                                                 |


#### `is_capitalize_rd` — 是否资本化 R&D


| 存入场景           | 赋值逻辑                                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **场景 A：手动录入**  | 固定设为 `true`                                                                                                                                |
| **场景 B：QB 导入** | `= (rdPayroll == 0 && RD 账户列表为空)`，即无 R&D Payroll 且无 RD 相关会计账户时为 true **数据元**：rdPayroll 来自 Redshift/QuickBooks 映射；RD 账户列表来自公司/QuickBooks 配置 |


#### `currency` — 货币


| 存入场景           | 赋值逻辑                               |
| -------------- | ---------------------------------- |
| **场景 A：手动录入**  | 取 `company.currency`，若为空默认 `"USD"` |
| **场景 B：QB 导入** | 不单独设置，跟随公司配置                       |


---

## 4. 保存时的自动计算功能

前端编辑 Financial Entry 时，有两个可选的自动计算功能。每个功能有**两种触发方式**：


| 方式            | 触发时机                                  | 说明                       |
| ------------- | ------------------------------------- | ------------------------ |
| **单月保存时附带执行** | 用户点击某月列的 "Save Changes"               | 保存单月数据的同时，若条件满足则附带执行自动计算 |
| **独立操作**      | 用户勾选 OE 拆分复选框 / 点击 Cash Quick Fill 按钮 | 不保存数据，仅执行自动计算并刷新表格       |


两种方式最终调用相同的计算逻辑。所有计算结果先写入 `finance_manual_data_temp` 暂存表，不直接写入正式表，最终由 Submit 流程写入 `finance_manual_data` 正式表。

### 4.1 Operating Expenses 子项自动拆分

#### 4.1.1 前端交互

用户在 Financial Entry 表格的 **Operating Expenses** 行看到一个复选框：

> ☐ Distribute operating expenses using historical percentages

**操作流程**：

1. 用户输入 OE 总额
2. 勾选复选框 → 弹出确认对话框 "Distribute Operating Expenses?"
3. 用户点击 "Distribute" 确认 → 系统执行拆分
4. 拆分完成后，表格自动刷新，被计算的月份标记为 "Changes Saved"
5. 勾选生效后，6 个 OE 子项行（S&M Expenses、S&M Payroll、R&D Expenses、R&D Payroll、G&A Expenses、G&A Payroll）变为**禁止编辑**（灰色背景）

取消勾选时直接执行（无确认对话框），6 个子项行恢复可编辑。

#### 4.1.2 触发条件

**单月保存时**：若用户本次修改了 Operating Expenses 的值，且该月处于"自动拆分"勾选状态，则保存时自动执行拆分（仅对当月）。

**独立操作时**：用户勾选复选框即触发，对当前编辑范围内的所有月份执行拆分。

#### 4.1.3 计算逻辑

**目标**：用用户输入的 OE 总额，按历史比例**反向拆分**为 6 个子项。OE 本身不被重算，保存的仍是用户输入值。

**① rate 来源与 Fallback**

系统从 `financial_growth_rate` 表查询自公司历史数据，从最近月份向前查找**连续 6 个月 Revenue > 0** 的记录。"连续"要求每两个月之间间隔恰好 1 个月，遇到 Revenue ≤ 0 或日期不连续则清零重新计数。


| 场景            | 数据来源     | 说明                                      |
| ------------- | -------- | --------------------------------------- |
| 自公司找到连续 6 个月  | 自公司历史数据  | 用自公司的比率计算                               |
| 自公司找不到连续 6 个月 | 同业公司历史数据 | 对每家同业公司分别查找连续 6 个月并计算平均比率，再对所有同业公司取算术平均 |
| 自公司和同业均无数据    | —        | 使用均分初始值：每个子项 = 1/6                      |


**② 计算步骤**

1. **计算各子项在 OE 中的历史占比**：对 6 个月中的每一条记录，用 `financial_growth_rate` 表中该子项的 rate 值 ÷ OE 的 rate 值，得到该子项占 OE 的比例。跳过任一值为空的记录；OE 为 0 时该条比例记为 0。
2. **异常值处理**（最多 2 轮迭代）：计算所有比例值的算术平均值。若某条比例的绝对值超过平均值绝对值的 **2 倍**，将该条替换为当前平均值，然后重新计算。若本轮有替换且轮次不足 2 次，再执行一轮。
3. **拆分**：`子项金额 = OE × 该子项归一化后的比例`
4. **精度保护**：若拆分后 6 项之和因浮点精度略大于 OE，则再次等比缩放到 OE 总额。

> **注意**：OE 拆分不会重算 `miscellaneous_operating_expenses`。该字段在数据转换阶段由 `OE − 6 个子项之和` 计算，拆分在此之后执行，因此拆分后 miscellaneous 与实际差额可能不一致。

### 4.2 Cash 级联自动计算

#### 4.2.1 前端交互

Cash 级联由以下 UI 控制：


| 控件                 | 作用                                     |
| ------------------ | -------------------------------------- |
| **Cash 单元格编辑**     | 用户手动输入某月 Cash 值后保存，自动向后级联重算            |
| **Quick Fill 按钮**  | Cash 行标题旁的快捷按钮，用递推公式一次性填充所有可计算月份的 Cash |
| **Set to Zero 按钮** | Cash 行标题旁的快捷按钮，将所有月份的 Cash 设为 0        |


**每月 Cash 有两种状态**：

- **自动计算**（`isCalculateCash = true`）：该月 Cash 由公式推导，级联传播时会被重算
- **手动输入**（`isCalculateCash = false`）：该月 Cash 由用户手动填写，级联传播到此月时**停止**

**级联范围的结束日期**（`endDate`）由前端自动取表格**最后一列**的日期，不由用户手动选择。

#### 4.2.2 触发条件

**单月保存时**：若用户本次修改了 Cash 值，且结束日期存在，且当月不是最后一个月，则保存时自动执行级联重算。

**独立操作时**：用户点击 Quick Fill 或 Set to Zero 按钮即触发。

#### 4.2.3 计算逻辑

**① 数据准备**

1. 构建日期列表：从用户修改的当月到表格最后一列的月份（逐月，含两端）
2. 获取这些月份的已有数据（暂存数据**优先于**系统预测数据），按日期升序排列
3. 以日期列表的第一条记录作为递推起点

**② 递推公式**（与 System Forecast 的 Cash 递推公式一致）

```
Cash(t) = Cash(t−1) + NetIncome(t) − ΔAR(t) − ΔOtherAssets(t) + ΔAP(t)
```


| 分量              | 含义                                                 | 说明                                                                                                           |
| --------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Cash(t−1)       | 前一月现金余额                                            | 递推起点为用户修改的当月 Cash                                                                                            |
| NetIncome(t)    | 当月净利润 = Gross Revenue − COGS − OE − Other Expenses | **不含** Capitalized R&D（见 [financial_forecast_current §3.15](./financial_forecast_current.md#315-cash--预测现金)） |
| ΔAR(t)          | 应收账款变动 = AR(t) − AR(t−1)                           | 增加消耗现金                                                                                                       |
| ΔOtherAssets(t) | 其他资产变动 = OtherAssets(t) − OtherAssets(t−1)         | 增加消耗现金                                                                                                       |
| ΔAP(t)          | 应付账款变动 = AP(t) − AP(t−1)                           | 增加释放现金                                                                                                       |


> 所有空值按 0 参与计算。若前月 Cash 为空，该月 Cash 返回 0。

**③ 停止条件**

逐月向后递推时，若某月的 Cash 状态为"手动输入"（`isCalculateCash = false`），**立即停止**，不再向后传播。

**④ 返回与刷新**

系统返回所有被重算月份的日期列表。前端收到后重新加载数据、刷新表格，并将系统计算的月份（排除用户手动修改过的月份）标记为 "Changes Saved"。

#### 4.2.4 Financial Entry 与 Committed Forecast 的差异

Committed Forecast 编辑时也支持 Cash 级联，逻辑相同但有以下差异：


| 差异点    | Financial Entry            | Committed Forecast                                   |
| ------ | -------------------------- | ---------------------------------------------------- |
| 递推起点   | 日期列表从用户修改的当月开始             | 日期列表从用户修改的当月的**下一个月**开始                              |
| 起点数据来源 | 直接取日期列表第一条                 | 单独查询当月数据，暂存数据优先，不存在时取 `financial_forecast_current` 表 |
| 暂存表    | `finance_manual_data_temp` | `financial_forecast_cache`                           |


---

## 5. 存入后的下游影响（Submit 触发）

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

## 6. 代码位置索引


| 类型               | 文件路径                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------- |
| 实体类              | `gstdev-cioaas-web/.../fi/domain/FinanceManualData.java`                                 |
| 抽象父类             | `gstdev-cioaas-web/.../fi/domain/FinanceManualDataAbstract.java`                         |
| 前端 DTO（Raw）      | `gstdev-cioaas-web/.../fi/contract/financeManualData/FinanceManualDataSaveInputRaw.java` |
| 前端 DTO（转换后）      | `gstdev-cioaas-web/.../fi/contract/financeManualData/FinanceManualDataSaveInput.java`    |
| 字段映射（text→field） | `gstdev-cioaas-web/.../fi/mapper/FinanceManualDataInputConverter.java`                   |
| Service（录入）      | `gstdev-cioaas-web/.../fi/service/FinanceManualDataServiceImpl.java`                     |
| Service（提交）      | `gstdev-cioaas-web/.../fi/service/FinancialStatementServiceImpl.java`                    |
| Service（QB 导入）   | `gstdev-cioaas-web/.../fi/service/QuickbooksServiceImpl.java`                            |
| Repository       | `gstdev-cioaas-web/.../fi/repository/FinanceManualDataRepository.java`                   |


