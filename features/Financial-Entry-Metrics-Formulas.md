# Financial Entry 页面 — 指标业务逻辑公式

> 版本：v4.1
> 创建时间：2026-03-13
> 更新时间：2026-03-19
> 状态：已确认

---

## 本文目录 

- [1. 概述](#1-概述)（[1.1](#11-四种数据视图) 四种数据视图 · [1.2](#12-预测模式选择) 预测模式 · [1.3](#13-核心代码位置) 代码位置 · [1.4](#14-前端校验规则) 前端校验 · [1.5](#15-数据存储结构) 数据存储 · [1.6](#16-数据查询方式) 数据查询 · [1.7](#17-数据录入模式与-quickbooks-字段映射) QuickBooks 字段映射）
- [2. Health Metrics](#2-health-metrics健康指标)
- [3. P&L — 损益表](#3-pl--损益表)
- [4. Balance Sheet — 资产负债表](#4-balance-sheet--资产负债表)
- [5. 指标依赖关系图](#5-指标依赖关系图)
- [6. System Generated Forecast 中各 Rate 的来源说明](#6-system-generated-forecast-中各-rate-的来源说明)
- [7. Confidence Intervals 缩放规则汇总](#7-confidence-intervals-缩放规则汇总)
- [8. 补充说明](#8-补充说明)（[8.7](#87-同业公司peer-companies筛选逻辑) 同业公司筛选）
- [9. 全指标数据读取逻辑速查表](#9-全指标数据读取逻辑速查表)（[9.1](#91-原始输入指标直接读库) 原始输入 · [9.2](#92-计算指标getter-实时计算不落库) 计算指标 · [9.3](#93-service-层设值指标buildfidatalist-中计算不落库) Service 设值 · [9.4](#94-mrr-yoy-growth-rate-计算逻辑) MRR YoY · [9.5](#95-confidence-intervalsp05p50p95读取逻辑) CI 读取）
- [10. 公式公用逻辑与代码位置（跨文件）](#10-公式公用逻辑与代码位置跨文件)

---

## 1. 概述

Financial Entry 页面（路由 `/Finance?id=xxx`，Tab "Financial Statements"）展示公司的月度财务数据。页面左侧列出所有指标，按 **Health Metrics**、**P&L（损益表）**、**Balance Sheet（资产负债表）** 三大区域分组，共 35 个指标。

### 1.1 四种数据视图

页面右上角有**主类型下拉框**，可选择三种主数据类型；同时在 Compare 中可叠加显示其他类型及置信区间：


| 视图                            | 说明                       | 前端标识                                   | 选择方式                |
| ----------------------------- | ------------------------ | -------------------------------------- | ------------------- |
| **Financial Entry**           | 公司实际财务数据（历史已发生）          | `entry`                                | 主类型下拉框              |
| **Committed Forecast**        | 用户手动提交/编辑的预测数据           | `forecast`（type=MANUAL/"0"）            | 主类型下拉框 / Compare 叠加 |
| **System Generated Forecast** | 系统自动生成的 24 个月预测          | `system`（type=FORMULA/"1" 或 MODEL/"2"） | 主类型下拉框 / Compare 叠加 |
| **Confidence Intervals**      | AI 模型的置信区间 (p05/p50/p95) | 仅 MODEL/"2" 模式下有值                      | Compare 叠加（勾选框）     |


选择某个主类型后，每个指标在每个月下显示该类型的值；同时可通过 Compare 叠加其他类型进行对比，此时每个月下会显示多行子数据（包含 p05/p50/p95）。

### 1.2 预测模式选择

系统根据公司历史数据月数自动选择预测方法：


| calculateType | 条件           | 预测方式               | Projection Basis     |
| ------------- | ------------ | ------------------ | -------------------- |
| 1             | 历史数据 < 6 个月  | Formula（纯同业）       | `PEER_BASED_FORMULA` |
| 2             | 历史数据 6–23 个月 | Formula（自身 + 同业混合） | `HYBRID_FORMULA`     |
| 3             | 历史数据 ≥ 24 个月 | AI Model（Ensemble） | `ENSEMBLE_MODEL`     |


### 1.3 核心代码位置（供开发查阅，正文以表名、列名与业务逻辑为主）


| 文件                                                                | 职责                                          |
| ----------------------------------------------------------------- | ------------------------------------------- |
| `CIOaas-api/.../fi/contract/FiDataDto.java`                       | 各指标计算公式（getter 方法）                          |
| `CIOaas-api/.../fi/service/FiDataCalculateServiceImpl.java`       | ARR、Cash 预测、P05/P95 缩放等复杂计算                 |
| `CIOaas-api/.../fi/service/FinancialForecastDataServiceImpl.java` | System Forecast 主流程：Revenue/PL/BS 预测公式      |
| `CIOaas-api/.../fi/util/ProjectionBasisDecider.java`              | 预测基准选择逻辑                                    |
| `CIOaas-python/source/forecast/forecast_engine.py`                | AI 模型预测引擎（ETS/ARIMA/Momentum + Monte Carlo） |


### 1.4 前端校验规则


| 校验对象                       | 校验条件                                                                                                           | 失败表现                                                             | 代码位置                                               |
| -------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------- |
| Operating Expenses（`pl-9`） | OE(t) ≥ S&M Expenses(t) + S&M Payroll(t) + R&D Expenses(t) + R&D Payroll(t) + G&A Expenses(t) + G&A Payroll(t) | 红色提示文字 + 红色输入框边框 + Save 按钮禁用 + Accept as Committed Forecast 按钮禁用 | `FinanceTable.tsx` → `validateOperatingExpenses()` |


- 校验在用户编辑任一相关字段时实时触发，逐月独立校验
- 提示文案：*"Operating expenses must be greater than or equal to the total of all other combined expenses"*
- 仅在 Financial Entry 编辑模式下生效

### 1.5 数据存储结构

四种数据视图分别存储在以下两个表中，字段列名一致（均继承自 `FinanceManualDataAbstract`）：


| 视图                        | 存储表                          | 区分条件                                       | 实体类                        |
| ------------------------- | ---------------------------- | ------------------------------------------ | -------------------------- |
| Financial Entry           | `finance_manual_data`        | —                                          | `FinanceManualData`        |
| Committed Forecast        | `financial_forecast_current` | `type = '0'`（MANUAL）                       | `FinancialForecastCurrent` |
| System Generated Forecast | `financial_forecast_current` | `type = '1'`（FORMULA）或 `'2'`（MODEL）        | `FinancialForecastCurrent` |
| Confidence Intervals      | `financial_forecast_current` | `type = '2'`（MODEL），使用 `p05`/`p50`/`p95` 列 | `FinancialForecastCurrent` |


- **Revenue CI**：指 Revenue（Gross Revenue）的置信区间，即 **P05_Revenue(t)**、**P50_Revenue(t)**、**P95_Revenue(t)**。这三者**直接来自数据库**：表 `financial_forecast_current` 的列 `p05`/`p50`/`p95`（type=2），由预测服务写入，前端/API 展示时直接读取，不做计算。
- Confidence Intervals 仅 Revenue 和 Cash 有独立存储列：Revenue → `p05`/`p50`/`p95`，Cash → `p05_cash`/`p50_cash`/`p95_cash`（均为**读库**）。
- **其他指标**（COGS、OE、AR、AP 等）的 p05/p95 **不落库**：展示时用**已从库中读出的** Revenue CI 与 Forecast Revenue 算比例（`P05_Rev(t)/Forecast_Rev(t)` 等），再对对应指标的 Forecast 值做缩放，即“按 Revenue CI 比例缩放”（详见 7.2）。
- Long-Term Debt 和 Other Liabilities 的 CI 值为 null
- 各指标的具体列名见各指标小节视图表格的"数据存储"列
- 各表的详细结构、完整字段列表及读写流程，见独立文档：
  - [finance_manual_data 表文档](./finance_manual_data.md)
  - [financial_forecast_current 表文档](./financial_forecast_current.md)
  - [financial_growth_rate 表文档](./financial_growth_rate.md)

### 1.6 数据查询方式

Financial Entry 页面数据来源分为**手动模式（Manual）** 和**自动模式（Automatic）**，由 `company_quickbooks.mode` 字段决定：


| 模式        | mode 值      | 数据来源                                                | 存储位置                                  |
| --------- | ----------- | --------------------------------------------------- | ------------------------------------- |
| Manual    | `MANUAL`    | 用户手动录入 / QuickBooks 初始化导入                           | `finance_manual_data` 表               |
| Automatic | `AUTOMATIC` | 查询 Redshift 表（由 cio-bigdata 定时 ETL 从 QuickBooks 写入） | 已落库 Redshift，不写 `finance_manual_data` |


**查询逻辑：**

1. **Manual 模式**：按公司、版本号、日期范围从表 `finance_manual_data` 取数，同一日期有多条时取 `updated_at` 最新的一条，再做货币换算后返回。
2. **Automatic 模式**：通过 ETL 接口按公司与日期查 Redshift 表（`QuickbooksProfitAndLoss` / `QuickbooksBalanceSheet`，由 cio-bigdata 定时从 QuickBooks 写入），换算后返回，不写入表 `finance_manual_data`。

**公司从 Automatic 切换为 Manual 时**：系统将 Redshift 中的 QuickBooks 历史数据一次性写入表 `finance_manual_data`。

### 1.7 数据录入模式与 QuickBooks 字段映射

当数据来源为 QuickBooks 自动导入时，各字段的映射关系如下：

**P&L 指标映射（来自 `QuickbooksProfitAndLoss`）：**


| finance_manual_data 列 | QuickBooks 源字段  | 说明                  |
| --------------------- | --------------- | ------------------- |
| `gross_revenue`       | `TotalIncome`   | 总收入                 |
| `cogs`                | `Cogs`          | 销售成本                |
| `operating_expenses`  | `TotalExpenses` | 运营费用总额              |
| `sm_expenses_percent` | `SMExpense`     | S&M 费用              |
| `sm_payroll_percent`  | `SMPayroll`     | S&M 人员薪酬（按公司配置比例拆分） |
| `rd_expenses_percent` | `RDExpense`     | R&D 费用              |
| `rd_payroll_percent`  | `RDPayroll`     | R&D 人员薪酬（按公司配置比例拆分） |
| `ga_expenses_percent` | `GAExpense`     | G&A 费用              |
| `ga_payroll_percent`  | `GAPayroll`     | G&A 人员薪酬            |
| `other_expenses`      | `OtherIncome`   | 其他费用                |


**Balance Sheet 指标映射（来自 `QuickbooksBalanceSheet`）：**


| finance_manual_data 列 | QuickBooks 源字段       | 说明              |
| --------------------- | -------------------- | --------------- |
| `cash`                | `Cash`               | 现金              |
| `accounts_receivable` | `AccountsReceivable` | 应收账款            |
| `assets_other`        | `OtherAssets`        | 其他资产            |
| `capitalized_rd`      | `RdCapitalized`      | 当月 − 上月差值，负值取 0 |
| `accounts_payable`    | `AccountsPayable`    | 应付账款            |
| `long_term_debt`      | `LongTermDebt`       | 长期债务            |
| `liabilities_other`   | `OtherLiabilities`   | 其他负债            |


> **注意**：`miscellaneous_operating_expenses` 在 QuickBooks 导入时不直接映射，展示时用「运营费用减六项子费用/薪酬」计算得出。

---

## 2. Health Metrics（健康指标）

### 2.1 Net Profit Margin（净利润率）


| 属性  | 值          |
| --- | ---------- |
| ID  | `health-1` |
| 单位  | 百分比 (%)    |


**公式（月份 t）：**

```
Net Profit Margin(t) = Net Income(t) / Gross Revenue(t) × 100%
```

- 分子 `Net Income(t)` 和分母 `Gross Revenue(t)` 取**同一个月 t** 的数据；Net Income 的组成字段及对应表/列见 §3.19。
- Gross Revenue(t) = 0 或 null → 返回 0%

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                               | 数据存储            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------- |
| **Financial Entry**           | `Net Income(t) / Gross Revenue(t) × 100%`；Net Income 见 3.19，Gross Revenue 来自 `finance_manual_data`.`gross_revenue` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current`（type=0）中对应字段                                                               | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current`（type=1/2）中对应字段                                                             | 同上              |
| **Confidence Intervals**      | p05: `P05_NetIncome(t) / P05_Revenue(t)`；p50: = Forecast 值；p95: `P95_NetIncome(t) / P95_Revenue(t)`                | 同上              |


---

### 2.2 Rule of 40（40 法则）


| 属性  | 值          |
| --- | ---------- |
| ID  | `health-2` |
| 单位  | 百分比 (%)    |


**公式（月份 t）：**

```
Rule of 40(t) = MRR YoY Growth Rate(t) + Net Profit Margin(t)
```

- 两个子指标取**同一个月 t** 的数据；MRR YoY Growth Rate 输入来自 `finance_manual_data` / `financial_forecast_current` 的 `gross_revenue` 序列（见 §3.5），Net Profit Margin 输入见 §2.1。
- MRR YoY Growth Rate(t) 为 null → 按 0 处理
- 理想值 ≥ 40%

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                  | 数据存储            |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `MRR YoY Growth Rate(t) + Net Profit Margin(t)`；两个子指标均为 getter 实时计算（见 3.5、2.1）                                        | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current`（type=0）中对应字段                                                                  | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current`（type=1/2）中对应字段                                                                | 同上              |
| **Confidence Intervals**      | p05: `P05_GrowthRate(t) + P05_NetProfitMargin(t)`；p50: = Forecast 值；p95: `P95_GrowthRate(t) + P95_NetProfitMargin(t)` | 同上              |


---

## 3. P&L — 损益表

### 3.1 Gross Revenue（总收入）


| 属性     | 值              |
| ------ | -------------- |
| ID     | `pl-1`         |
| 单位     | 货币             |
| API 字段 | `grossRevenue` |


**公式（月份 t）：** 原始输入，无计算公式。

**四种数据视图下的值：**


| 视图                              | 计算方式                                              | 数据存储                                                   |
| ------------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际收入                                  | `finance_manual_data`.`gross_revenue`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入） | Redshift `QuickbooksProfitAndLoss`.`TotalIncome`       |
| **Committed Forecast**          | 用户手动输入月份 t 的预测收入值                                 | `financial_forecast_current`.`gross_revenue`, type=0   |
| **System Generated Forecast**   | 直接读取                                              | `financial_forecast_current`.`gross_revenue`, type=1/2 |
| **Confidence Intervals**        | 直接读取（仅 AI Model 模式有值，Formula 模式为 null）            | `financial_forecast_current`.`p05`/`p50`/`p95`, type=2 |


> **写入生成逻辑**：System Forecast 和 CI 的值如何计算并写入 `financial_forecast_current`，详见 [financial_forecast_current 表文档 — 3.1 gross_revenue](./financial_forecast_current.md#31-gross_revenue--预测总收入) 和 [3.18 p05/p50/p95](./financial_forecast_current.md#318-p05--p50--p95--revenue-置信区间)；Revenue 预测中使用的增长率和季节性因子数据来自 [financial_growth_rate 表文档](./financial_growth_rate.md)（同业筛选条件见本文 8.7）

---

### 3.2 ARR（年经常性收入）


| 属性  | 值      |
| --- | ------ |
| ID  | `pl-2` |
| 单位  | 货币     |


**公式（月份 t，按 Revenue Recognition 模式分三种）：**


| `revenueRecognition` 值 | 模式                     | 公式                                          | 计算步骤                                                       |
| ---------------------- | ---------------------- | ------------------------------------------- | ---------------------------------------------------------- |
| 1                      | Last Month             | `ARR(t) = MRR(t) × 12`                      | 直接取当月 MRR 乘以 12；若当月无 MRR 数据，返回 0                           |
| 2                      | Trailing Twelve Months | `ARR(t) = Average(MRR(t−11) ~ MRR(t)) × 12` | 取 `t−11` 到 `t` 共 12 个月的 MRR，求平均后 × 12；无数据月份的 MRR 视为 0 参与平均 |
| 3                      | Last Three Months      | `ARR(t) = Average(MRR(t−2) ~ MRR(t)) × 12`  | 取 `t−2` 到 `t` 共 3 个月的 MRR，求平均后 × 12；无数据月份的 MRR 视为 0 参与平均   |


- `revenueRecognition` 是公司级别的配置字段，来源：数据库 `company` 表的 `revenue_recognition` 列（`int4`，默认值 1）
- 仅 ARR 指标受 Revenue Recognition 模式影响，MRR、New MRR LTM、MRR YoY Growth Rate 等其他指标均直接使用当月 MRR 值，不涉及模式分支

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                           | 数据存储                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| **Financial Entry**           | 按上述 recognition 模式用 MRR 序列计算；MRR 来自表 `finance_manual_data` 列 `gross_revenue`；recognition 来自表 `company` 列 `revenue_recognition` | 不落库，buildFiDataList 设值 |
| **Committed Forecast**        | 同上公式；MRR 来自表 `financial_forecast_current` 列 `gross_revenue`（type=0）                                                            | 同上                     |
| **System Generated Forecast** | 同上公式；MRR 来自表 `financial_forecast_current` 列 `gross_revenue`（type=1/2）                                                          | 同上                     |
| **Confidence Intervals**      | p05/p95: 使用 P05/P95 缩放后的 MRR 序列按同公式计算（P05/P95 来自 `financial_forecast_current`.`p05`/`p95`，type=2）；p50: = Forecast ARR(t)       | 同上                     |


---

### 3.3 MRR（月经常性收入）


| 属性  | 值      |
| --- | ------ |
| ID  | `pl-3` |
| 单位  | 货币     |


**公式（月份 t）：**

```
MRR(t) = Gross Revenue(t)
```

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                        | 数据存储            |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `= Gross Revenue(t)`；来自 `finance_manual_data`.`gross_revenue`                                                               | 不落库，getter 实时计算 |
| **Committed Forecast**        | `= Gross Revenue(t)`；来自 `financial_forecast_current`.`gross_revenue`（type=0）                                                | 同上              |
| **System Generated Forecast** | `= Gross Revenue(t)`；来自 `financial_forecast_current`.`gross_revenue`（type=1/2）                                              | 同上              |
| **Confidence Intervals**      | p05: = `financial_forecast_current`.`p05`（type=2）；p50: = Forecast Revenue；p95: = `financial_forecast_current`.`p95`（type=2） | 同上              |


---

### 3.4 New MRR LTM（去年同期至今新增 MRR）


| 属性  | 值      |
| --- | ------ |
| ID  | `pl-4` |
| 单位  | 货币     |


**公式（月份 t）：**

```
New MRR LTM(t) = MRR(t) − MRR(t−12)
```

- `MRR(t−12)` = 12 个月前同月的 MRR，从同数据源中取 12 个月前对应日期的收入列
- 无去年同月数据 → MRR(t−12) 视为 0

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                  | 数据存储            |
| ----------------------------- | ------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `MRR(t) − MRR(t−12)`；MRR 来自 `finance_manual_data`.`gross_revenue`，t−12 取 12 个月前同日期记录  | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；MRR(t) 来自 `financial_forecast_current`.`gross_revenue`（type=0），MRR(t−12) 来自历史数据  | 同上              |
| **System Generated Forecast** | 同上公式；MRR(t) 来自 `financial_forecast_current`.`gross_revenue`（type=1/2）                 | 同上              |
| **Confidence Intervals**      | p05: `P05_MRR(t) − P05_MRR(t−12)`；p50: = Forecast 值；p95: `P95_MRR(t) − P95_MRR(t−12)` | 同上              |


---

### 3.5 MRR YoY Growth Rate（MRR 同比增长率）


| 属性  | 值       |
| --- | ------- |
| ID  | `pl-5`  |
| 单位  | 百分比 (%) |


**公式（月份 t，条件分支）：**


| 条件                                          | 公式                                             |
| ------------------------------------------- | ---------------------------------------------- |
| `lastMrr ≤ 0` 或 `MRR(t) ≤ 0` 或 `months ≤ 0` | N/A (null)                                     |
| 历史数据月数 `< 12`                               | `(MRR(t) / lastMrr) ^ (12 / months) − 1`（年化外推） |
| 历史数据月数 `≥ 12`                               | `MRR(t) / MRR(t−12) − 1`（直接同比）                 |


- `lastMrr`：历史 ≥ 12 个月时取 MRR(t−12)；不足 12 个月时取最早的非零 MRR
- `months`：月份 t 之前有数据的总月数

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                               | 数据存储            |
| ----------------------------- | ---------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | 按上述条件公式计算；MRR(t) 和 lastMrr 来自 `finance_manual_data`.`gross_revenue` 的当月和历史记录       | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；MRR(t) 来自 `financial_forecast_current`.`gross_revenue`（type=0），lastMrr 来自历史数据 | 同上              |
| **System Generated Forecast** | 同上公式；MRR(t) 来自 `financial_forecast_current`.`gross_revenue`（type=1/2）              | 同上              |
| **Confidence Intervals**      | p05/p95: 使用 P05/P95 缩放后的 MRR(t) 和对应 lastMrr 按同公式计算；p50: = Forecast 值               | 同上              |


---

### 3.6 COGS（销售成本）


| 属性     | 值      |
| ------ | ------ |
| ID     | `pl-6` |
| 单位     | 货币     |
| API 字段 | `cogs` |


**公式（月份 t）：** 原始输入，无计算公式。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                                                       | 数据存储                                          |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际 COGS                                                                                                                                        | `finance_manual_data`.`cogs`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                                                          | Redshift `QuickbooksProfitAndLoss`.`Cogs`     |
| **Committed Forecast**          | 用户手动输入月份 t 的预测 COGS                                                                                                                                        | `financial_forecast_current`.`cogs`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                                                       | `financial_forecast_current`.`cogs`, type=1/2 |
| **Confidence Intervals**        | `Forecast_COGS(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast COGS(t)；p95 同理按 P95 比例；P05/P95_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                      |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.2 cogs](./financial_forecast_current.md#32-cogs--预测销售成本)

---

### 3.7 Gross Profit（毛利润）


| 属性  | 值      |
| --- | ------ |
| ID  | `pl-7` |
| 单位  | 货币     |


**公式（月份 t）：**

```
Gross Profit(t) = MRR(t) − COGS(t)
```

- MRR(t) 和 COGS(t) 取**同一个月 t** 的数据
- COGS(t) 为 null → 返回 0

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                 | 数据存储            |
| ----------------------------- | ---------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `MRR(t) − COGS(t)`；MRR 来自 `finance_manual_data`.`gross_revenue`，COGS 来自 `finance_manual_data`.`cogs` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                 | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                               | 同上              |
| **Confidence Intervals**      | p05: `P05_MRR(t) − P05_COGS(t)`；p50: = Forecast 值；p95: `P95_MRR(t) − P95_COGS(t)`                    | 同上              |


---

### 3.8 Gross Margin（毛利率）


| 属性  | 值       |
| --- | ------- |
| ID  | `pl-8`  |
| 单位  | 百分比 (%) |


**公式（月份 t）：**

```
Gross Margin(t) = Gross Profit(t) / MRR(t) × 100%
```

- 分子和分母取**同一个月 t**
- MRR(t) = 0 → 返回 0%

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                      | 数据存储            |
| ----------------------------- | --------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `Gross Profit(t) / MRR(t) × 100%`；Gross Profit 和 MRR 均为 getter 实时计算（见 3.7、3.3），底层来自 `finance_manual_data` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                      | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                                    | 同上              |
| **Confidence Intervals**      | p05: `P05_GrossProfit(t) / P05_MRR(t)`；p50: = Forecast 值；p95: `P95_GrossProfit(t) / P95_MRR(t)`           | 同上              |


---

### 3.9 Operating Expenses（运营支出）


| 属性     | 值                   |
| ------ | ------------------- |
| ID     | `pl-9`              |
| 单位     | 货币                  |
| API 字段 | `operatingExpenses` |


**公式（月份 t）：**

```
Operating Expenses(t) = S&M Expenses(t) + S&M Payroll(t)
                      + R&D Expenses(t) + R&D Payroll(t)
                      + G&A Expenses(t) + G&A Payroll(t)
```

- 所有子项取**同一个月 t** 的数据

**前端校验（见 1.4）：** OE(t) ≥ 各子项之和（S&M Expenses + S&M Payroll + R&D Expenses + R&D Payroll + G&A Expenses + G&A Payroll），校验失败时 OE 输入框标红、Save 按钮禁用。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                        | 数据存储                                                        |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的 OE 总额，或由各实际子项汇总                                                                                                | `finance_manual_data`.`operating_expenses`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                           | Redshift `QuickbooksProfitAndLoss`.`TotalExpenses`          |
| **Committed Forecast**          | 用户手动输入月份 t 的 OE 总额，或由各 Committed 子项汇总                                                                                       | `financial_forecast_current`.`operating_expenses`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                        | `financial_forecast_current`.`operating_expenses`, type=1/2 |
| **Confidence Intervals**        | `Forecast_OE(t) × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                    |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.11 operating_expenses](./financial_forecast_current.md#311-operating_expenses--预测运营费用)

---

### 3.10 S&M Expenses（销售与市场费用）


| 属性     | 值                   |
| ------ | ------------------- |
| ID     | `pl-10`             |
| 单位     | 货币                  |
| API 字段 | `smExpensesPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                         | 数据存储                                                         |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                              | `finance_manual_data`.`sm_expenses_percent`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                            | Redshift `QuickbooksProfitAndLoss`.`SMExpense`               |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                              | `financial_forecast_current`.`sm_expenses_percent`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                         | `financial_forecast_current`.`sm_expenses_percent`, type=1/2 |
| **Confidence Intervals**        | `Forecast_S&M(t) × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                     |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.3 sm_expenses_percent](./financial_forecast_current.md#33-sm_expenses_percent--预测-sm-费用)

---

### 3.11 S&M Payroll（销售与市场人员薪酬）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `pl-11`            |
| 单位     | 货币                 |
| API 字段 | `smPayrollPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`sm_payroll_percent`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表，按 Payroll 比例配置拆分（cio-bigdata 定时 ETL 写入）                                                                  | Redshift `QuickbooksProfitAndLoss`.`SMPayroll`              |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`sm_payroll_percent`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                   | `financial_forecast_current`.`sm_payroll_percent`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                    |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.4 sm_payroll_percent](./financial_forecast_current.md#34-sm_payroll_percent--预测-sm-薪酬)

---

### 3.12 Sales Efficiency Ratio（销售效率比）


| 属性  | 值       |
| --- | ------- |
| ID  | `pl-12` |
| 单位  | 比率      |


**公式（月份 t）：**

```
Sales Efficiency Ratio(t) = (S&M Expenses(t) + S&M Payroll(t)) / New MRR LTM(t)
```

- 分子和分母取**同一个月 t** 的数据
- New MRR LTM(t) = 0 → 返回 0

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                                                       | 数据存储            |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `(S&M Exp(t) + S&M Pay(t)) / New MRR LTM(t)`；分子来自表 `finance_manual_data` 列 `sm_expenses_percent`、`sm_payroll_percent`，分母 New MRR LTM 为 getter 实时计算（见 §3.4） | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；分子来自表 `financial_forecast_current` 列 `sm_expenses_percent`、`sm_payroll_percent`（type=0）                                                               | 同上              |
| **System Generated Forecast** | 同上公式；分子来自表 `financial_forecast_current` 列 `sm_expenses_percent`、`sm_payroll_percent`（type=1/2）                                                             | 同上              |
| **Confidence Intervals**      | p05: `(P05_S&M(t) + P05_S&M_Pay(t)) / P05_NewMRR_LTM(t)`；p50: = Forecast 值；p95: 同理使用 P95 缩放值                                                               | 同上              |


---

### 3.13 R&D Expenses（研发费用）


| 属性     | 值                   |
| ------ | ------------------- |
| ID     | `pl-13`             |
| 单位     | 货币                  |
| API 字段 | `rdExpensesPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                         |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`rd_expenses_percent`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                      | Redshift `QuickbooksProfitAndLoss`.`RDExpense`               |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`rd_expenses_percent`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                   | `financial_forecast_current`.`rd_expenses_percent`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                     |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.5 rd_expenses_percent](./financial_forecast_current.md#35-rd_expenses_percent--预测-rd-费用)

---

### 3.14 R&D Payroll（研发人员薪酬）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `pl-14`            |
| 单位     | 货币                 |
| API 字段 | `rdPayrollPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`rd_payroll_percent`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表，按 Payroll 比例配置拆分（cio-bigdata 定时 ETL 写入）                                                                  | Redshift `QuickbooksProfitAndLoss`.`RDPayroll`              |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`rd_payroll_percent`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                   | `financial_forecast_current`.`rd_payroll_percent`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                    |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.6 rd_payroll_percent](./financial_forecast_current.md#36-rd_payroll_percent--预测-rd-薪酬)

---

### 3.15 G&A Expenses（管理费用）


| 属性     | 值                   |
| ------ | ------------------- |
| ID     | `pl-15`             |
| 单位     | 货币                  |
| API 字段 | `gaExpensesPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                         |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`ga_expenses_percent`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                      | Redshift `QuickbooksProfitAndLoss`.`GAExpense`               |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`ga_expenses_percent`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                   | `financial_forecast_current`.`ga_expenses_percent`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                     |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.7 ga_expenses_percent](./financial_forecast_current.md#37-ga_expenses_percent--预测-ga-费用)

---

### 3.16 G&A Payroll（管理人员薪酬）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `pl-16`            |
| 单位     | 货币                 |
| API 字段 | `gaPayrollPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`ga_payroll_percent`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                      | Redshift `QuickbooksProfitAndLoss`.`GAPayroll`              |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`ga_payroll_percent`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                   | `financial_forecast_current`.`ga_payroll_percent`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                    |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.8 ga_payroll_percent](./financial_forecast_current.md#38-ga_payroll_percent--预测-ga-薪酬)

---

### 3.17 Miscellaneous Operating Expenses（杂项运营支出）


| 属性     | 值                                |
| ------ | -------------------------------- |
| ID     | `pl-17`                          |
| 单位     | 货币                               |
| API 字段 | `miscellaneousOperatingExpenses` |


**公式（月份 t）：**

```
Misc OE(t) = Operating Expenses(t) − S&M Expenses(t) − S&M Payroll(t)
           − R&D Expenses(t) − R&D Payroll(t) − G&A Expenses(t) − G&A Payroll(t)
```

- 所有项取**同一个月 t** 的数据
- 若 `miscellaneousOperatingExpenses` 字段已有值（如 QuickBooks 自动导入），直接使用该值

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                                             | 数据存储                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| **Financial Entry (Manual)**    | 按上述公式用实际的月份 t 各子项做差                                                                                                                              | `finance_manual_data`.`miscellaneous_operating_expenses`                  |
| **Financial Entry (Automatic)** | getter 实时计算：OE − 各子项之和（不从 QB 映射，不落库）                                                                                                             | 不落库，getter 实时计算                                                           |
| **Committed Forecast**          | 按上述公式用 Committed 的月份 t 各子项做差                                                                                                                     | `financial_forecast_current`.`miscellaneous_operating_expenses`, type=0   |
| **System Generated Forecast**   | 按上述公式用 Forecast 的月份 t 各子项做差                                                                                                                      | `financial_forecast_current`.`miscellaneous_operating_expenses`, type=1/2 |
| **Confidence Intervals**        | p05: 缩放后 `P05_OE(t) − P05_各子项(t)`；p50: = Forecast Misc OE(t)；p95: 缩放后 `P95_OE(t) − P95_各子项(t)`；缩放公式 = `Forecast值 × (P_Rev(t) / Forecast_Rev(t))` | 不落库，实时计算                                                                  |


---

### 3.18 Other Expenses（其他支出）


| 属性     | 值               |
| ------ | --------------- |
| ID     | `pl-18`         |
| 单位     | 货币              |
| API 字段 | `otherExpenses` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                    |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`other_expenses`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                      | Redshift `QuickbooksProfitAndLoss`.`OtherIncome`        |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`other_expenses`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                   | `financial_forecast_current`.`other_expenses`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.9 other_expenses](./financial_forecast_current.md#39-other_expenses--预测其他费用)

---

### 3.19 Net Income（净利润）


| 属性  | 值       |
| --- | ------- |
| ID  | `pl-19` |
| 单位  | 货币      |


**公式（月份 t）：**

```
Net Income(t) = Gross Profit(t) − Operating Expenses(t) − Other Expenses(t)
```

展开：

```
Net Income(t) = Gross Revenue(t) − COGS(t) − Operating Expenses(t) − Other Expenses(t)
```

- 所有项取**同一个月 t** 的数据

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                                                                          | 数据存储            |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `Gross Profit(t) − OE(t) − Other Exp(t)`；Gross Profit 为 getter 计算（见 3.7），OE 来自 `finance_manual_data`.`operating_expenses`，Other Exp 来自 `finance_manual_data`.`other_expenses` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                                                                                          | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                                                                                                        | 同上              |
| **Confidence Intervals**      | p05: `P05_GrossProfit(t) − P05_OE(t) − P05_OtherExp(t)`；p50: = Forecast 值；p95: `P95_GrossProfit(t) − P95_OE(t) − P95_OtherExp(t)`                                             | 同上              |


---

### 3.20 Capitalized R&D (Monthly)（月度资本化研发支出）


| 属性     | 值               |
| ------ | --------------- |
| ID     | `pl-20`         |
| 单位     | 货币              |
| API 字段 | `capitalizedRd` |


**公式（月份 t）：** 原始输入。

QuickBooks 自动模式下：`Cap R&D(t) = −(RdCapitalized(t) − RdCapitalized(t−1))`，若结果 > 0 则取 0。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                    |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`capitalized_rd`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表后计算：`−(当月−上月)`，>0 取 0（cio-bigdata 定时 ETL 写入）                                                              | Redshift `QuickbooksBalanceSheet`.`RdCapitalized`       |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`capitalized_rd`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                   | `financial_forecast_current`.`capitalized_rd`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.10 capitalized_rd](./financial_forecast_current.md#310-capitalized_rd--预测月度资本化-rd)

---

### 3.21 Monthly Net Burn Rate（月净消耗率）


| 属性  | 值       |
| --- | ------- |
| ID  | `pl-21` |
| 单位  | 货币      |


**公式（月份 t）：**

```
Monthly Net Burn Rate(t) = Net Income(t) − Capitalized R&D Monthly(t)
```

- 两项取**同一个月 t** 的数据

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                          | 数据存储            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `Net Income(t) − Cap R&D(t)`；Net Income 为 getter 计算（见 3.19），Cap R&D 来自 `finance_manual_data`.`capitalized_rd` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                          | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                                        | 同上              |
| **Confidence Intervals**      | p05: `P05_NetIncome(t) − P05_CapR&D(t)`；p50: = Forecast 值；p95: `P95_NetIncome(t) − P95_CapR&D(t)`             | 同上              |


---

## 4. Balance Sheet — 资产负债表

### 4.1 Assets（总资产）


| 属性  | 值      |
| --- | ------ |
| ID  | `bs-1` |
| 单位  | 货币     |


**公式（月份 t）：**

```
Assets(t) = Cash(t) + Accounts Receivable(t) + Other Assets(t) + Capitalized R&D Total(t)
```

- 所有项取**同一个月 t** 的数据

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                                                                                                         | 数据存储            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------- |
| **Financial Entry**           | `Cash(t) + AR(t) + Other Assets(t) + Cap R&D Total(t)`；Cash 来自表 `finance_manual_data` 列 `cash`，AR 来自列 `accounts_receivable`，Other Assets 来自列 `assets_Other`，Cap R&D Total 为同列表内列 `capitalized_rd` 累加（见 §4.5） | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                                                                                                                         | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                                                                                                                                       | 同上              |
| **Confidence Intervals**      | p05: `P05_Cash(t) + P05_AR(t) + P05_OtherAssets(t) + P05_CapRD_Total(t)`；p50: = Forecast 值；p95: 同理使用 P95 缩放值                                                                                                 | 同上              |


---

### 4.2 Cash（现金）


| 属性     | 值      |
| ------ | ------ |
| ID     | `bs-2` |
| 单位     | 货币     |
| API 字段 | `cash` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                              | 数据存储                                                                  |
| ------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                   | `finance_manual_data`.`cash`                                          |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入） | Redshift `QuickbooksBalanceSheet`.`Cash`                              |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                   | `financial_forecast_current`.`cash`, type=0                           |
| **System Generated Forecast**   | 直接读取                                              | `financial_forecast_current`.`cash`, type=1/2                         |
| **Confidence Intervals**        | 直接读取                                              | `financial_forecast_current`.`p05_cash`/`p50_cash`/`p95_cash`, type=2 |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.15 cash](./financial_forecast_current.md#315-cash--预测现金) 和 [3.19 p05_cash/p50_cash/p95_cash](./financial_forecast_current.md#319-p05_cash--p50_cash--p95_cash--cash-置信区间)

---

### 4.3 Monthly Runway（月跑道）


| 属性  | 值      |
| --- | ------ |
| ID  | `bs-3` |
| 单位  | 月数（数值） |


**公式（月份 t，条件分支）：**


| 条件                                          | 结果          |
| ------------------------------------------- | ----------- |
| Cash(t) 为 null                              | N/A         |
| Monthly Net Burn Rate(t) = 0                | N/A         |
| `−(Cash(t) / Monthly Net Burn Rate(t)) > 0` | 显示该月数       |
| `−(Cash(t) / Monthly Net Burn Rate(t)) ≤ 0` | N/A（公司未在烧钱） |


- Cash(t) 和 Monthly Net Burn Rate(t) 取**同一个月 t**

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                                                     | 数据存储            |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `−(Cash(t) / Burn Rate(t))`，仅结果 > 0 时显示；Cash 来自表 `finance_manual_data` 列 `cash`，Burn Rate 为 getter 计算（见 §3.21，输入来自同表/同视图的 Net Income 与 `capitalized_rd`） | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；Cash 来自表 `financial_forecast_current` 列 `cash`（type=0），Burn Rate 同视图 getter                                                                         | 同上              |
| **System Generated Forecast** | 同上公式；Cash 来自表 `financial_forecast_current` 列 `cash`（type=1/2），Burn Rate 同视图 getter                                                                       | 同上              |
| **Confidence Intervals**      | p05: `−(P05_Cash(t) / P05_BurnRate(t))`，仅结果 > 0 时显示；p50: = Forecast 值；p95: 同理使用 P95 缩放值                                                                  | 同上              |


---

### 4.4 Accounts Receivable（应收账款）


| 属性     | 值                    |
| ------ | -------------------- |
| ID     | `bs-4`               |
| 单位     | 货币                   |
| API 字段 | `accountsReceivable` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                        | 数据存储                                                         |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                             | `finance_manual_data`.`accounts_receivable`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                           | Redshift `QuickbooksBalanceSheet`.`AccountsReceivable`       |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                             | `financial_forecast_current`.`accounts_receivable`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                        | `financial_forecast_current`.`accounts_receivable`, type=1/2 |
| **Confidence Intervals**        | `Forecast_AR(t) × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                     |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.12 accounts_receivable](./financial_forecast_current.md#312-accounts_receivable--预测应收账款)

---

### 4.5 Capitalized R&D (Total)（累计资本化研发）


| 属性  | 值      |
| --- | ------ |
| ID  | `bs-5` |
| 单位  | 货币     |


**公式（月份 t）：**

```
Capitalized R&D Total(t) = Σ Capitalized R&D Monthly(i)，i 从最早月份到月份 t
```

- 汇总截至月份 t（含）的所有 Capitalized R&D Monthly

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                              | 数据存储                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------- |
| **Financial Entry**           | `Σ Cap R&D Monthly(i), i ≤ t`；Cap R&D Monthly 来自 `finance_manual_data`.`capitalized_rd`，累加所有月份至 t | 不落库，buildFiDataList 设值 |
| **Committed Forecast**        | 同上公式；历史部分来自 `finance_manual_data`，预测部分来自 `financial_forecast_current`.`capitalized_rd`（type=0）    | 同上                     |
| **System Generated Forecast** | 同上公式；预测部分来自 `financial_forecast_current`.`capitalized_rd`（type=1/2）                               | 同上                     |
| **Confidence Intervals**      | p05: `Σ P05_CapR&D_Monthly(i), i ≤ t`；p50: = Forecast 值；p95: `Σ P95_CapR&D_Monthly(i), i ≤ t`     | 同上                     |


---

### 4.6 Other Assets（其他资产）


| 属性     | 值             |
| ------ | ------------- |
| ID     | `bs-6`        |
| 单位     | 货币            |
| API 字段 | `assetsOther` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                   | 数据存储                                                  |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                        | `finance_manual_data`.`assets_other`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                      | Redshift `QuickbooksBalanceSheet`.`OtherAssets`       |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                        | `financial_forecast_current`.`assets_other`, type=0   |
| **System Generated Forecast**   | 直接读取 **数据元**：表 `financial_forecast_current` 列 `assets_other`，type=1/2                                                  | `financial_forecast_current`.`assets_other`, type=1/2 |
| **Confidence Intervals**        | `Forecast值 × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                              |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.13 assets_Other](./financial_forecast_current.md#313-assets_other--预测其他资产)

---

### 4.7 Liabilities（总负债）


| 属性  | 值      |
| --- | ------ |
| ID  | `bs-7` |
| 单位  | 货币     |


**公式（月份 t）：**

```
Liabilities(t) = Accounts Payable(t) + Long-Term Debt(t) + Other Liabilities(t)
```

- 所有项取**同一个月 t** 的数据

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                                                                    | 数据存储            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| **Financial Entry**           | `AP(t) + LTD(t) + Other Liabilities(t)`；AP 来自 `finance_manual_data`.`accounts_payable`，LTD 来自 `long_term_debt`，Other Liabilities 来自 `liabilities_other` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                                                                    | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                                                                                  | 同上              |
| **Confidence Intervals**      | p05: = `P05_AP(t)`（LTD 和 OtherLiab 置为 null）；p50: = Forecast AP(t)（LTD/OtherLiab 同为 null）；p95: = `P95_AP(t)`                                             | 同上              |


**Confidence Intervals 说明：**

- p05/p95: 仅含缩放后的 `P_AP(t)`，Long-Term Debt 和 Other Liabilities 为 null（因其与 Revenue 无比例关系）
- p50: 同 System Forecast，但 LTD 和 Other Liabilities 同样置为 null

---

### 4.8 Accounts Payable（应付账款）


| 属性     | 值                 |
| ------ | ----------------- |
| ID     | `bs-8`            |
| 单位     | 货币                |
| API 字段 | `accountsPayable` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                                                                                                        | 数据存储                                                      |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                                                                                             | `finance_manual_data`.`accounts_payable`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入）                                                                           | Redshift `QuickbooksBalanceSheet`.`AccountsPayable`       |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                                                                                             | `financial_forecast_current`.`accounts_payable`, type=0   |
| **System Generated Forecast**   | 直接读取                                                                                                                        | `financial_forecast_current`.`accounts_payable`, type=1/2 |
| **Confidence Intervals**        | `Forecast_AP(t) × (P_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；P_Rev 来自 `financial_forecast_current`.`p05`/`p95`（type=2） | 不落库，实时计算                                                  |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.14 accounts_payable](./financial_forecast_current.md#314-accounts_payable--预测应付账款)

---

### 4.9 Long-Term Debt（长期债务）


| 属性     | 值              |
| ------ | -------------- |
| ID     | `bs-9`         |
| 单位     | 货币             |
| API 字段 | `longTermDebt` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                              | 数据存储                                                    |
| ------------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                   | `finance_manual_data`.`long_term_debt`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入） | Redshift `QuickbooksBalanceSheet`.`LongTermDebt`        |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                   | `financial_forecast_current`.`long_term_debt`, type=0   |
| **System Generated Forecast**   | 直接读取                                              | `financial_forecast_current`.`long_term_debt`, type=1/2 |
| **Confidence Intervals**        | p05/p50/p95: 均为 **null**（不参与置信区间计算）               | —                                                       |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.16 long_term_debt](./financial_forecast_current.md#316-long_term_debt--预测长期债务)

---

### 4.10 Other Liabilities（其他负债）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `bs-10`            |
| 单位     | 货币                 |
| API 字段 | `liabilitiesOther` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图                              | 计算方式                                              | 数据存储                                                       |
| ------------------------------- | ------------------------------------------------- | ---------------------------------------------------------- |
| **Financial Entry (Manual)**    | 用户手动录入月份 t 的实际值                                   | `finance_manual_data`.`liabilities_other`                  |
| **Financial Entry (Automatic)** | 查询 Redshift 表（cio-bigdata 定时 ETL 从 QuickBooks 写入） | Redshift `QuickbooksBalanceSheet`.`OtherLiabilities`       |
| **Committed Forecast**          | 用户手动输入月份 t 的预测值                                   | `financial_forecast_current`.`liabilities_other`, type=0   |
| **System Generated Forecast**   | 直接读取                                              | `financial_forecast_current`.`liabilities_other`, type=1/2 |


> **写入生成逻辑**：详见 [financial_forecast_current 表文档 — 3.17 liabilities_other](./financial_forecast_current.md#317-liabilities_other--预测其他负债)
> | **Confidence Intervals**        | p05/p50/p95: 均为 **null**（不参与置信区间计算）                                                                                           | —                                                          |

---

### 4.11 Debt/Assets Ratio（负债资产比）


| 属性  | 值       |
| --- | ------- |
| ID  | `bs-11` |
| 单位  | 比率      |


**公式（月份 t）：**

```
Debt/Assets Ratio(t) = Liabilities(t) / Assets(t)
```

- 分子和分母取**同一个月 t**
- Assets(t) = 0 → 返回 0

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                   | 数据存储            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------ | --------------- |
| **Financial Entry**           | `Liabilities(t) / Assets(t)`；Liabilities 和 Assets 均为 getter 实时计算（见 4.7、4.1），底层来自 `finance_manual_data` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                   | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                                 | 同上              |
| **Confidence Intervals**      | p05: `P05_Liabilities(t) / P05_Assets(t)`；p50: = Forecast 值；p95: `P95_Liabilities(t) / P95_Assets(t)`  | 同上              |


---

### 4.12 Equity（所有者权益）


| 属性  | 值       |
| --- | ------- |
| ID  | `bs-12` |
| 单位  | 货币      |


**公式（月份 t）：**

```
Equity(t) = Assets(t) − Liabilities(t)
```

- 两项取**同一个月 t** 的数据

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                   | 数据存储            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------ | --------------- |
| **Financial Entry**           | `Assets(t) − Liabilities(t)`；Assets 和 Liabilities 均为 getter 实时计算（见 4.1、4.7），底层来自 `finance_manual_data` | 不落库，getter 实时计算 |
| **Committed Forecast**        | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=0）                                                   | 同上              |
| **System Generated Forecast** | 同上公式；输入值来自 `financial_forecast_current` 对应字段（type=1/2）                                                 | 同上              |
| **Confidence Intervals**      | p05: `P05_Assets(t) − P05_Liabilities(t)`；p50: = Forecast 值；p95: `P95_Assets(t) − P95_Liabilities(t)`  | 同上              |


---

## 5. 指标依赖关系图

以下展示各指标之间的计算依赖关系（适用于所有四种数据视图，仅输入来源不同）：

```
Gross Revenue(t) (输入)
 ├── MRR(t) = Gross Revenue(t)
 │    ├── ARR(t) = f(MRR 序列, recognition)
 │    ├── New MRR LTM(t) = MRR(t) − MRR(t−12)
 │    │    ├── Sales Efficiency Ratio(t) = (S&M(t) + S&M Pay(t)) / New MRR LTM(t)
 │    │    └── MRR YoY Growth Rate(t) = f(MRR(t), lastMrr, months)
 │    │         └── Rule of 40(t) = Growth Rate(t) + Net Profit Margin(t)
 │    ├── Gross Profit(t) = MRR(t) − COGS(t)
 │    │    ├── Gross Margin(t) = Gross Profit(t) / MRR(t)
 │    │    └── Net Income(t) = Gross Profit(t) − OE(t) − Other Exp(t)
 │    │         ├── Net Profit Margin(t) = Net Income(t) / Revenue(t)
 │    │         └── Burn Rate(t) = Net Income(t) − Cap R&D(t)
 │    │              └── Monthly Runway(t) = −(Cash(t) / Burn Rate(t))
 │    └── (MRR(t) 同时影响 Gross Margin 分母)
 │
 COGS(t) ───────────────────┘ (参与 Gross Profit)
 │
 OE(t) = S&M(t) + S&M Pay(t) + R&D(t) + R&D Pay(t) + G&A(t) + G&A Pay(t)
 │ └── Misc OE(t) = OE(t) − 各子项之和
 │
 Other Expenses(t) ──────────┘ (参与 Net Income)
 │
 Cap R&D Monthly(t)
 │ ├── Cap R&D Total(t) = Σ Cap R&D Monthly(i), i ≤ t
 │ └── (参与 Burn Rate)
 │
 Cash(t) ─────── Assets(t) = Cash(t) + AR(t) + Other Assets(t) + Cap R&D Total(t)
 AR(t) ──────────┤
 Other Assets(t) ┘
 │
 Assets(t) ────── Debt/Assets Ratio(t) = Liabilities(t) / Assets(t)
 │                Equity(t) = Assets(t) − Liabilities(t)
 AP(t) ─────────┐
 LTD(t) ────────┤
 Other Liab(t) ─┘── Liabilities(t)
```

---

## 6. System Generated Forecast 中各 Rate 的来源说明

### 6.1 Rate 汇总表


| 指标              | Rate 字段                  | 自公司历史 ≥ 6 个月                        | 自公司历史 < 6 个月           |
| --------------- | ------------------------ | ----------------------------------- | ---------------------- |
| COGS            | `cogsRate`               | 自公司 COGS/Revenue 中位数                | 同业 rate 几何平均的中位数       |
| S&M Expenses    | `smExpensesRate`         | 自公司 S&M/Revenue 中位数                 | 同业 rate 几何平均的中位数       |
| S&M Payroll     | `smPayrollRate`          | 自公司 S&M Payroll/Revenue 中位数         | 同业 rate 几何平均的中位数       |
| R&D Expenses    | `rdExpensesRate`         | 自公司 R&D/Revenue 中位数                 | 同业 rate 几何平均的中位数       |
| R&D Payroll     | `rdPayrollRate`          | 自公司 R&D Payroll/Revenue 中位数         | 同业 rate 几何平均的中位数       |
| G&A Expenses    | `gaExpensesRate`         | 自公司 G&A/Revenue 中位数                 | 同业 rate 几何平均的中位数       |
| G&A Payroll     | `gaPayrollRate`          | 自公司 G&A Payroll/Revenue 中位数         | 同业 rate 几何平均的中位数       |
| Other Expenses  | `otherExpensesRate`      | 自公司 Other Exp/Revenue 中位数           | 同业 rate 几何平均的中位数       |
| Capitalized R&D | `capitalizedRdRate`      | 自公司 Cap R&D/Revenue 中位数             | 同业 rate 几何平均的中位数       |
| AR              | `accountsReceivableRate` | 自公司 AR/Revenue **算术平均值**            | 始终使用自公司数据（不足 3 个月返回 0） |
| Other Assets    | `assetsOtherRate`        | 自公司 OtherAssets/Revenue **算术平均值**   | 始终使用自公司数据（不足 3 个月返回 0） |
| AP              | `accountsPayableRate`    | 自公司 AP/(COGS+OE+OtherExp) **算术平均值** | 始终使用自公司数据（不足 3 个月返回 0） |


**AR / Other Assets / AP 为什么不使用同业数据：** 这三个 Balance Sheet 指标的 Projection Basis 固定为 `SELF_BASED_FORMULA`（仅使用自身历史数据），不参与同业对标。当自公司有效历史数据不足 3 个月时，rate 返回 0，预测值也为 0。

> 同业公司的筛选条件（公司类型、发展阶段、ARR 区间等）详见 8.7。

### 6.2 中位数的计算方法

**自公司中位数（历史 ≥ 6 个月时使用）：**

1. 收集自公司所有历史月份的 rate 值（如每月的 COGS/Revenue）
2. 过滤掉 null 值，得到有效值列表
3. 将列表**降序排序**
4. 若个数为奇数：取中间位置的值
5. 若个数为偶数：取中间两个值的平均值

```
示例：自公司有 8 个月的 cogsRate = [0.30, 0.25, 0.28, 0.32, 0.27, 0.31, 0.29, 0.26]
降序排序 → [0.32, 0.31, 0.30, 0.29, 0.28, 0.27, 0.26, 0.25]
偶数个，取第 4、第 5 个的平均 → (0.29 + 0.28) / 2 = 0.285
```

**同业 rate 几何平均的中位数（历史 < 6 个月时使用）：**

1. 对每家同业公司，收集该公司所有历史月份的 rate 值
2. 对每家公司的 rate 列表，计算**几何平均值**（见 6.3）
3. 将所有同业公司的几何平均值组成列表
4. 对该列表取**中位数**（方法同上：降序排序后取中间值）

```
示例：3 家同业公司
  公司 A 的几何平均 cogsRate = 0.28
  公司 B 的几何平均 cogsRate = 0.32
  公司 C 的几何平均 cogsRate = 0.25
降序排序 → [0.32, 0.28, 0.25]
奇数个，取中间值 → 0.28
```

### 6.3 几何平均值的计算方法

用于计算每家同业公司的 rate 代表值：

```
几何平均 = exp(Σ ln(rate_i + 1) / n) − 1
```

1. 将每个 rate 值加 1（`value = rate + 1`）
2. 若 `value = 0`（即 rate = -1），平滑处理为 `0.0001`
3. 对所有 `value` 取自然对数后求平均
4. 对平均值取指数还原
5. 结果减 1 得到几何平均 rate
6. 若负值个数为奇数，结果取负

### 6.4 算术平均值的计算方法

用于 AR / Other Assets / AP 的 rate 计算：

```
算术平均 = Σ rate_i / n （n 为非 null 值的个数）
```

1. 收集自公司所有历史月份的 rate 值
2. 过滤掉 null 值
3. 若有效值不足 **3 个月**，返回 0（数据不足，不做预测）
4. 否则求所有有效值的算术平均

---

## 7. Confidence Intervals 缩放规则汇总

### 7.1 缩放规则总表


| 指标类型                      | P05 计算                       | P50 计算                      | P95 计算                       |
| ------------------------- | ---------------------------- | --------------------------- | ---------------------------- |
| Revenue                   | Monte Carlo 5th percentile   | Monte Carlo 50th percentile | Monte Carlo 95th percentile  |
| COGS / Expenses / Cap R&D | `Forecast × (P05_Rev / Rev)` | = Forecast 值                | `Forecast × (P95_Rev / Rev)` |
| AR / Other Assets / AP    | `Forecast × (P05_Rev / Rev)` | = Forecast 值                | `Forecast × (P95_Rev / Rev)` |
| Cash                      | 按 P_Revenue 比例重推算递推          | = Forecast Cash             | 按 P_Revenue 比例重推算递推          |
| Long-Term Debt            | null                         | null                        | null                         |
| Other Liabilities         | null                         | null                        | null                         |
| 衍生指标                      | 基于缩放后输入自动计算                  | 基于 Forecast 值计算             | 基于缩放后输入自动计算                  |
| **适用条件**                  | 仅 AI Model (≥24 月)           | 仅 AI Model (≥24 月)          | 仅 AI Model (≥24 月)           |


### 7.2 为什么要按 Revenue 比例缩放

AI 模型（ETS + ARIMA + Momentum 集成）只对 **Revenue** 做 Monte Carlo 模拟产生 P05/P50/P95 区间。其他指标（COGS、各项 Expenses、AR、AP 等）并没有各自独立的 AI 预测模型。

在 System Generated Forecast 中，这些指标的预测公式本身就是 **Revenue 的线性函数**（`指标 = rate × Revenue`），即它们与 Revenue 天然成比例关系。因此，当 Revenue 在乐观/悲观场景下变化时，合理做法是让所有比例关联的指标按**同一缩放比例**变动：

```
缩放比例 rate = P_Revenue(t) / Forecast_Revenue(t)
```

这样做保证了：

- P05（悲观）场景：Revenue 下降 → 所有费用/资产/负债同比例下降 → 保持各项 rate 不变
- P95（乐观）场景：Revenue 上升 → 所有费用/资产/负债同比例上升 → 保持各项 rate 不变
- 各指标间的**比例结构**（如 Gross Margin、Net Profit Margin）在不同场景下保持一致

### 7.3 各指标的缩放逻辑详解

**按 Revenue 比例缩放的指标（共 12 个）：**

以 P05 为例，P95 同理：

```
rate = P05_Revenue(t) / Forecast_Revenue(t)

P05_COGS(t)            = Forecast_COGS(t)            × rate
P05_S&M Expenses(t)    = Forecast_S&M Expenses(t)    × rate
P05_S&M Payroll(t)     = Forecast_S&M Payroll(t)     × rate
P05_R&D Expenses(t)    = Forecast_R&D Expenses(t)    × rate
P05_R&D Payroll(t)     = Forecast_R&D Payroll(t)     × rate
P05_G&A Expenses(t)    = Forecast_G&A Expenses(t)    × rate
P05_G&A Payroll(t)     = Forecast_G&A Payroll(t)     × rate
P05_Other Expenses(t)  = Forecast_Other Expenses(t)  × rate
P05_Cap R&D(t)         = Forecast_Cap R&D(t)         × rate
P05_AR(t)              = Forecast_AR(t)              × rate
P05_Other Assets(t)    = Forecast_Other Assets(t)    × rate
P05_AP(t)              = Forecast_AP(t)              × rate
```

若 Forecast 值为 null，缩放后取 0。

**Cash — 为什么不直接缩放而是重新递推：**

Cash 的预测公式是一个**逐月递推**（`Cash(t) = Cash(t−1) + NetIncome − ΔAR − ΔAssets + ΔAP`），不是 Revenue 的简单比例。如果直接用 `rate` 缩放 Cash，会破坏递推的累积逻辑。因此 P05/P95 的 Cash 通过以下方式重新计算：

1. 将 Net Income、AR、Other Assets、AP 各自按 P_Revenue/Revenue 的比例调整
2. 用调整后的值**重新执行整个 Cash 递推链**
3. 每个月的 P_Cash 以上个月的 P_Cash 为起点，而非 Forecast Cash

```
P_dNetIncome(t) = (NetIncome(t) / Revenue(t)) × P_Revenue(t)
P_AR(t)         = (AR(t) / Revenue(t)) × P_Revenue(t)
P_AR(t−1)       = (AR(t−1) / Revenue(t−1)) × P_Revenue(t−1)
P_dAR(t)        = P_AR(t) − P_AR(t−1)
（Other Assets、AP 同理）

P_Cash(t) = P_Cash(t−1) + P_dNetIncome(t) − P_dAR(t) − P_dAssets(t) + P_dAP(t)
```

第 1 个预测月以 close month 的实际 Cash 为起点。

**Long-Term Debt / Other Liabilities — 为什么置为 null：**

这两个指标在 System Forecast 中使用的是**波动率复利公式**（`Value × (1 + Fluctuation)^n`），基于自身历史趋势外推，与 Revenue 没有比例关系。按 Revenue 比例缩放它们在业务上没有意义（长期债务不会因为收入乐观/悲观而同比变化），因此在 P05/P50/P95 中均置为 null，不参与置信区间展示。

**P50 — 为什么等于 Forecast 值：**

P50 是 Monte Carlo 模拟的第 50 百分位（中位数），与 Ensemble 点预测非常接近。系统直接使用 System Generated Forecast 的原始值作为 P50，不做任何缩放。Long-Term Debt 和 Other Liabilities 在 P50 中也置为 null，与 P05/P95 保持一致。

### 7.4 衍生指标在 P05/P50/P95 下的计算

缩放完成后，所有衍生指标（Gross Profit、Net Income、Assets、Equity 等）使用与 Financial Entry / System Forecast 完全相同的公式，基于缩放后的输入值自动推导：

```
P05_Gross Profit(t) = P05_MRR(t) − P05_COGS(t)
P05_Net Income(t)   = P05_Gross Profit(t) − P05_OE(t) − P05_Other Exp(t)
P05_Assets(t)       = P05_Cash(t) + P05_AR(t) + P05_Other Assets(t) + P05_Cap R&D Total(t)
P05_Liabilities(t)  = P05_AP(t)  （LTD 和 Other Liab 为 null，不参与求和）
P05_Equity(t)       = P05_Assets(t) − P05_Liabilities(t)
...
```

---

## 8. 补充说明

### 8.1 货币汇率处理

所有指标在标准化层面会乘以 FX Rate 进行货币转换：

- `Revenue = Gross Revenue × FX Rate`
- `OPEX = (各子项之和) × FX Rate`

### 8.2 数据来源


| 模式        | 说明                                 |
| --------- | ---------------------------------- |
| Manual    | 用户手动录入，存储在 `finance_manual_data` 表 |
| Automatic | QuickBooks 自动导入                    |


### 8.3 预测数据类型


| 枚举        | Code | 说明                            |
| --------- | ---- | ----------------------------- |
| `MANUAL`  | "0"  | 用户手动录入的预测（Committed Forecast） |
| `FORMULA` | "1"  | 系统公式计算的预测（历史 < 24 个月）         |
| `MODEL`   | "2"  | AI 模型生成的预测（历史 ≥ 24 个月）        |


### 8.4 Projection Basis（预测基准）


| 枚举                   | 说明        | 使用场景                                 |
| -------------------- | --------- | ------------------------------------ |
| `PEER_BASED_FORMULA` | 仅使用同业公司数据 | Revenue（<6 月）、PL 指标（<6 月）            |
| `HYBRID_FORMULA`     | 自身 + 同业混合 | Revenue（6–23 月）、PL 指标（6–23 月）        |
| `SELF_BASED_FORMULA` | 仅使用自身历史数据 | BS 指标、Long-Term Debt、PL 指标（≥6 月自有数据） |
| `ENSEMBLE_MODEL`     | AI 集成模型   | Revenue（≥24 月）                       |


### 8.5 预测触发时机

- 用户提交财务数据（`financialEntrySubmit`）后自动重新生成 24 个月预测
- 定时任务（`ScheduleProcessor`）按计划重新计算
- SQS 消息异步触发

### 8.6 前端特殊格式化


| 账户                                                                  | 格式        |
| ------------------------------------------------------------------- | --------- |
| Monthly Runway                                                      | 月数文本（非货币） |
| Net Profit Margin / Rule of 40 / MRR YoY Growth Rate / Gross Margin | 百分比       |


### 8.7 同业公司（Peer Companies）筛选逻辑

System Generated Forecast 中使用同业数据计算 `resultGrowthRate`、`seasonalFactor` 以及各项 rate（历史 < 6 月时），同业公司的获取逻辑如下：

**同业来源（二选一）：**


| 优先级 | 来源     | 条件                                          | 查询方式                                                                              |
| --- | ------ | ------------------------------------------- | --------------------------------------------------------------------------------- |
| 1   | 手动同业组  | 公司在 `r_colleague_company_group` 中且组内公司数 > 4 | 取组内所有公司的 `financial_growth_rate` 数据                                               |
| 2   | 系统自动匹配 | 上述条件不满足时                                    | 按表 `company`、`stage`、`r_company_stage` 筛选公司类型与阶段相同，再取表 `financial_growth_rate` 数据 |


**系统自动匹配的 SQL 筛选条件：**


| 条件     | 表/字段                                     | 说明                      |
| ------ | ---------------------------------------- | ----------------------- |
| 公司类型相同 | `company`.`company_type`                 | 与当前公司相同                 |
| 发展阶段相同 | `stage`.`phase`（通过 `r_company_stage` 关联） | 与当前公司相同                 |
| 会计方法相同 | `company`.`account_method`               | Accrual/Cash，默认 Accrual |
| 排除自身   | `company`.`company_id` ≠ 当前公司            | —                       |


**内存二次过滤：**


| 过滤条件            | 说明                                                                                   |
| --------------- | ------------------------------------------------------------------------------------ |
| 数据量 ≥ 6 个月      | `financial_growth_rate` 记录数                                                          |
| 公司活跃            | 系统内已参与识别的公司                                                                          |
| close month 有数据 | 当前公司 close month 对应月份有记录                                                             |
| ARR 区间一致        | 与当前公司同区间 （0: <1, 1: 1–250, 2: 250–1000, 3: 1000–5000, 4: 5000–20000, 5: ≥20000，单位：万） |
| 有连续正收入          | 最近 24 个月内有连续 6 个月正 Revenue                                                           |
| 异常值截断           | 若某 rate 大于平均值两倍，则按平均值截断                                                              |


**兜底逻辑：** 若最终满足条件的同业公司少于 3 家，则改为仅排除当前公司，使用全平台其他公司数据。

**同业数据存储位置：** 所有同业数据均来自 `financial_growth_rate` 表，该表按 `company_id` + `date` 存储每家公司每月的 Revenue、增长率和各项 rate。

---

## 9. 全指标数据读取逻辑速查表

下表说明每个指标在四种视图下，数据**从哪里读取、如何计算**。

- **直接读库**：直接从数据库表字段取值，不经过公式计算
- **getter 计算**：展示时按公式用当前行的各列实时算出的值，不落库
- **buildFiDataList 设值**：在组装列表时按规则（如 MRR 序列、累加）算出的值填入，不落库

各指标在四种视图下的**数据元（表与列）**已写在第 2～4 节各小节的「四种数据视图下的值」表格的「数据存储」列中；公用公式逻辑与代码位置见 [第 10 节](#10-公式公用逻辑与代码位置跨文件)。

### 9.1 原始输入指标（直接读库）

以下指标在各视图下均为**直接读库**，区别在于读取的表/数据源和 type 条件不同。

**Financial Entry 视图的两种数据来源模式**（由 `company_quickbooks.mode` 决定）：


| 模式            | `mode` 值    | 查询入口                                                  | 数据来源                                             | 是否落库                                  |
| ------------- | ----------- | ----------------------------------------------------- | ------------------------------------------------ | ------------------------------------- |
| **Manual**    | `MANUAL`    | 按公司与日期范围从表 `finance_manual_data` 取数，同日期多条取最新一条，再做货币换算 | PostgreSQL 表 `finance_manual_data`               | 已落库，直接读取                              |
| **Automatic** | `AUTOMATIC` | 通过 ETL 接口按公司与日期查 Redshift 表，返回后做货币换算                  | Redshift 表（由 cio-bigdata 定时 ETL 从 QuickBooks 写入） | 已落库 Redshift，不写 `finance_manual_data` |


> **模式切换**：从 Automatic 改为 Manual 时，系统将 Redshift 中的 QuickBooks 历史数据一次性写入表 `finance_manual_data`。

**两种模式的数据流对比：**

- **Manual**：用户在前端录入 → 写入表 `finance_manual_data` → 查询时按公司与日期从该表取数，同日期多条取最新一条，再做货币换算后展示。
- **Automatic**：QuickBooks 经 cio-bigdata 定时 ETL 写入 Redshift 表（`QuickbooksProfitAndLoss` / `QuickbooksBalanceSheet`）→ 查询时通过 ETL 接口按公司与日期从 Redshift 取数，换算后展示，不写入 `finance_manual_data`。

> 各指标在 Manual / Automatic 模式下的具体数据来源字段和存储位置，已整合至第 2–4 节每个指标的"四种数据视图下的值"表格中（Financial Entry (Manual) 和 Financial Entry (Automatic) 行）。

### 9.2 计算指标（getter 实时计算，不落库）

以下指标**不单独存表**，在读取时按公式用当前行的各列实时计算。四种视图使用同一套公式，区别仅在于参与计算的数值来自哪张表（见下方数据元）。

**数据元（输入字段对应的数据库来源）**：  

- **Financial Entry 视图**：表中「输入字段」均来自表 `finance_manual_data` 的同名列（Manual 模式），或 Redshift QuickBooks 映射字段（Automatic 模式），见 [§1.7](#17-数据录入模式与-quickbooks-字段映射)。  
- **Committed Forecast / System Generated Forecast 视图**：输入字段来自表 `financial_forecast_current` 的同名列（type=0 或 type=1/2）。  
- **Confidence Intervals**：P05/P95 为缩放后值，P50 与 Forecast 一致；Revenue/Cash 的 P05/P50/P95 来自 `financial_forecast_current`.`p05`/`p50`/`p95`、`p05_cash`/`p50_cash`/`p95_cash`（type=2）。


| 指标                             | 计算公式                            | 输入字段                                                                | 特殊处理                       |
| ------------------------------ | ------------------------------- | ------------------------------------------------------------------- | -------------------------- |
| MRR (pl-3)                     | `= grossRevenue`                | `grossRevenue`                                                      | grossRevenue 为 null → 返回 0 |
| New MRR LTM (pl-4)             | 当月 MRR − 12 个月前 MRR             | 列 `grossRevenue`、12 个月前同列                                           | 无 12 个月前数据时按 0 处理          |
| Gross Profit (pl-7)            | 当月收入 − 当月 COGS                  | 列 `grossRevenue`, `cogs`                                            | cogs 为空 → 返回 0             |
| Gross Margin (pl-8)            | 毛利润 ÷ 当月收入                      | 列 `grossRevenue`, `cogs`                                            | 收入 = 0 → 返回 0              |
| Net Income (pl-19)             | 毛利润 − 运营费用 − 其他费用               | 列 `grossRevenue`, `cogs`, `operatingExpenses`, `otherExpenses`      | 空字段按 0 处理                  |
| Net Profit Margin (health-1)   | 净利润 ÷ 当月收入                      | 同 Net Income + 列 `grossRevenue`                                     | 收入 = 0 或空 → 返回 0           |
| Monthly Net Burn Rate (pl-21)  | 净利润 − 当月资本化 R&D                 | 同 Net Income + 列 `capitalizedRd`                                    | 资本化 R&D 为空 → 按 0 处理        |
| Misc OE (pl-17)                | 若本列已有值则用本列；否则 = 运营费用 − 六项子费用/薪酬 | 列 `operatingExpenses` 和 6 项子指标列                                     | 各项空 → 按 0 处理               |
| Sales Efficiency Ratio (pl-12) | (S&M 费用 + S&M 薪酬) ÷ New MRR LTM | 列 `smExpensesPercent`, `smPayrollPercent`，及 12 个月前收入、当月收入           | New MRR LTM = 0 → 返回 0     |
| Assets (bs-1)                  | 现金 + 应收账款 + 其他资产 + 累计资本化 R&D    | 列 `cash`, `accountsReceivable`, `assetsOther`, 及累计 `capitalized_rd` | 各项空 → 按 0 处理               |
| Liabilities (bs-7)             | 应付账款 + 长期债务 + 其他负债              | 列 `accountsPayable`, `longTermDebt`, `liabilitiesOther`             | 各项空 → 按 0 处理               |
| Debt/Assets Ratio (bs-11)      | 总负债 ÷ 总资产                       | 同 Assets + Liabilities                                              | 总资产 = 0 → 返回 0             |
| Equity (bs-12)                 | 总资产 − 总负债                       | 同 Assets + Liabilities                                              | —                          |
| Monthly Runway (bs-3)          | −(现金 ÷ 月净消耗率)，仅结果 > 0 时显示       | 列 `cash`，及月净消耗率（见上）                                                 | 消耗率=0 或结果≤0 → 不显示          |
| Rule of 40 (health-2)          | MRR 同比增长率 + 净利润率                | 同 Growth Rate + Net Profit Margin 所用列                               | Growth Rate 为空 → 按 0 处理    |


### 9.3 Service 层设值指标（buildFiDataList 中计算，不落库）

以下字段在组装列表时，根据同一数据列表按规则计算后填入，不落库。


| 字段                   | 计算逻辑                                                                                        | 数据来源                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `arr`                | recognition=1：`当月MRR × 12`；recognition=2：`最近12个月MRR平均 × 12`；recognition=3：`最近3个月MRR平均 × 12` | 同一数据列表中的 `grossRevenue`（即 MRR），`recognition` 来自 `company.revenue_recognition` |
| `lastYearMrr`        | 取 `date − 12个月` 那条记录的 `getMrr()`                                                            | 同一数据列表中 12 个月前的 `grossRevenue`，无则返回 0                                         |
| `lastMrr`            | 历史 ≥ 12 月：取 12 个月前的 MRR；历史 < 12 月：取第一个非零 MRR                                                | 同一数据列表中的历史 `grossRevenue`                                                     |
| `lastMrrMonths`      | 日期早于当前月的记录总数                                                                                | 同一数据列表的记录计数                                                                   |
| `capitalizedRdTotal` | 所有 `date ≤ 当前月` 的 `capitalizedRd` 之和                                                        | 同一数据列表中的 `capitalized_rd` 字段累加                                                |


### 9.4 MRR YoY Growth Rate 计算逻辑

由于此指标逻辑较复杂，单独列出：

```
输入：当月 MRR（即收入列）、lastMrr、lastMrrMonths（历史月数）

条件判断：
├── lastMrr ≤ 0 或 MRR ≤ 0 或 lastMrrMonths ≤ 0 → 返回 null
├── lastMrrMonths < 12 → 返回 (MRR / lastMrr) ^ (12 / lastMrrMonths) − 1（年化外推）
└── lastMrrMonths ≥ 12 → 返回 MRR / lastMrr − 1（直接同比）
```

### 9.5 Confidence Intervals（P05/P50/P95）读取逻辑


| 指标                      | P05                                                             | P50                                                             | P95                                                             |
| ----------------------- | --------------------------------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------- |
| Revenue                 | **直接读库**：`financial_forecast_current`.`p05` WHERE type='2'      | **直接读库**：`financial_forecast_current`.`p50` WHERE type='2'      | **直接读库**：`financial_forecast_current`.`p95` WHERE type='2'      |
| Cash                    | **直接读库**：`financial_forecast_current`.`p05_cash` WHERE type='2' | **直接读库**：`financial_forecast_current`.`p50_cash` WHERE type='2' | **直接读库**：`financial_forecast_current`.`p95_cash` WHERE type='2' |
| 其他指标                    | **实时计算**：`Forecast值 × (P05_Revenue / Forecast_Revenue)`         | = Forecast 值                                                    | **实时计算**：`Forecast值 × (P95_Revenue / Forecast_Revenue)`         |
| LTD / Other Liabilities | null                                                            | null                                                            | null                                                            |


---

## 10. 公式公用逻辑与代码位置（跨文件）

以下逻辑在多个指标或表中复用，统一说明定义所在文档与代码位置，便于跨文件查阅。


| 公用逻辑                                | 使用位置                                                                                  | 定义所在文档与章节                                                                                                                                                                                                                                     |
| ----------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **rate 计算（分子÷分母）**                  | 表 `financial_growth_rate` 所有 rate 列（如 `cogs_rate`、`sm_expenses_rate` 等）               | [financial_growth_rate — 第 4 节](./financial_growth_rate.md#4-rate-的计算方式分子分母)                                                                                                                                                                  |
| **复合月增长率**                          | 表 `financial_growth_rate` 列 `growth_rate`                                             | [financial_growth_rate — 3.2](./financial_growth_rate.md#32-growth_rate--月度增长率)                                                                                                                                                               |
| **P&L rate 取值**（自公司中位数 / 同业几何平均中位数） | 表 `financial_forecast_current` 3.2～3.10 各列（cogs、sm_expenses_percent、…、capitalized_rd） | 本文档 [第 6 节](./Financial-Entry-Metrics-Formulas.md#6-system-generated-forecast-中各-rate-的来源说明)、[financial_forecast_current — 第 4 节](./financial_forecast_current.md#4-pl-rate-取值逻辑汇总)                                                           |
| **同业公司筛选**                          | resultGrowthRate、seasonalFactor、P&L rate（历史 < 6 月）                                    | 本文档 [8.7](./Financial-Entry-Metrics-Formulas.md#87-同业公司peer-companies筛选逻辑)、[financial_growth_rate — 6.3](./financial_growth_rate.md#63-同业公司筛选)、[financial_forecast_current — 3.1 下方](./financial_forecast_current.md#31-gross_revenue--预测总收入) |
| **几何平均 / 中位数**（列表 → 单值）             | resultGrowthRate、seasonalFactor、P&L 同业 rate                                           | 本文档 [6.2、6.3](./Financial-Entry-Metrics-Formulas.md#62-中位数的计算方法)                                                                                                                                                                              |
| **Cash 递推公式**                       | 表 `financial_forecast_current` 列 `cash`、`p05_cash`/`p95_cash`                         | [financial_forecast_current — 3.15、3.19](./financial_forecast_current.md#315-cash--预测现金)                                                                                                                                                      |
| **LTD / Other Liabilities 波动率外推**   | 表 `financial_forecast_current` 列 `long_term_debt`、`liabilities_other`                 | [financial_forecast_current — 3.16、3.17](./financial_forecast_current.md#316-long_term_debt--预测长期债务)                                                                                                                                          |


- **数据元**：上述各逻辑的输入字段，凡来自「自公司历史」的，均对应表 `financial_growth_rate` 或 `finance_manual_data` 的相应列；凡来自「同业」的，均来自 `financial_growth_rate`（同业公司集合见 8.7）。

