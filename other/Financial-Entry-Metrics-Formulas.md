# Financial Entry 页面 — 指标业务逻辑公式

> 版本：v4.0
> 创建时间：2026-03-13
> 更新时间：2026-03-13
> 状态：已确认

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


### 1.3 核心代码位置


| 文件                                                                | 职责                                          |
| ----------------------------------------------------------------- | ------------------------------------------- |
| `CIOaas-api/.../fi/contract/FiDataDto.java`                       | 各指标计算公式（getter 方法）                          |
| `CIOaas-api/.../fi/service/FiDataCalculateServiceImpl.java`       | ARR、Cash 预测、P05/P95 缩放等复杂计算                 |
| `CIOaas-api/.../fi/service/FinancialForecastDataServiceImpl.java` | System Forecast 主流程：Revenue/PL/BS 预测公式      |
| `CIOaas-api/.../fi/util/ProjectionBasisDecider.java`              | 预测基准选择逻辑                                    |
| `CIOaas-python/source/forecast/forecast_engine.py`                | AI 模型预测引擎（ETS/ARIMA/Momentum + Monte Carlo） |


### 1.4 前端校验规则

| 校验对象 | 校验条件 | 失败表现 | 代码位置 |
|----------|----------|----------|----------|
| Operating Expenses（`pl-9`） | OE(t) ≥ S&M Expenses(t) + S&M Payroll(t) + R&D Expenses(t) + R&D Payroll(t) + G&A Expenses(t) + G&A Payroll(t) | 红色提示文字 + 红色输入框边框 + Save 按钮禁用 + Accept as Committed Forecast 按钮禁用 | `FinanceTable.tsx` → `validateOperatingExpenses()` |

- 校验在用户编辑任一相关字段时实时触发，逐月独立校验
- 提示文案：*"Operating expenses must be greater than or equal to the total of all other combined expenses"*
- 仅在 Financial Entry 编辑模式下生效

### 1.5 数据存储结构

四种数据视图分别存储在以下两个表中，字段列名一致（均继承自 `FinanceManualDataAbstract`）：

| 视图 | 存储表 | 区分条件 | 实体类 |
|------|--------|----------|--------|
| Financial Entry | `finance_manual_data` | — | `FinanceManualData` |
| Committed Forecast | `financial_forecast_current` | `type = '0'`（MANUAL） | `FinancialForecastCurrent` |
| System Generated Forecast | `financial_forecast_current` | `type = '1'`（FORMULA）或 `'2'`（MODEL） | `FinancialForecastCurrent` |
| Confidence Intervals | `financial_forecast_current` | `type = '2'`（MODEL），使用 `p05`/`p50`/`p95` 列 | `FinancialForecastCurrent` |

- **Revenue CI**：指 Revenue（Gross Revenue）的置信区间，即 **P05_Revenue(t)**、**P50_Revenue(t)**、**P95_Revenue(t)**。这三者**直接来自数据库**：表 `financial_forecast_current` 的列 `p05`/`p50`/`p95`（type=2），由预测服务写入，前端/API 展示时直接读取，不做计算。
- Confidence Intervals 仅 Revenue 和 Cash 有独立存储列：Revenue → `p05`/`p50`/`p95`，Cash → `p05_cash`/`p50_cash`/`p95_cash`（均为**读库**）。
- **其他指标**（COGS、OE、AR、AP 等）的 p05/p95 **不落库**：展示时用**已从库中读出的** Revenue CI 与 Forecast Revenue 算比例（`P05_Rev(t)/Forecast_Rev(t)` 等），再对对应指标的 Forecast 值做缩放，即“按 Revenue CI 比例缩放”（详见 7.2）。
- Long-Term Debt 和 Other Liabilities 的 CI 值为 null
- 各指标的具体列名见各指标小节视图表格的"数据存储"列

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

- 分子 `Net Income(t)` 和分母 `Gross Revenue(t)` 取**同一个月 t** 的数据
- Gross Revenue(t) = 0 或 null → 返回 0%

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                                             |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Financial Entry**           | 使用实际录入的 Net Income(t) 和 Gross Revenue(t)，按上述公式计算                                                                 |
| **Committed Forecast**        | 使用 Committed 的 Net Income(t) 和 Gross Revenue(t)，按上述公式计算                                                          |
| **System Generated Forecast** | 使用 System Forecast 的 Net Income(t) 和 Gross Revenue(t)，按上述公式计算                                                    |
| **Confidence Intervals**      | p05: P05 缩放后的 Net Income(t) / P05 Revenue(t)；p50: 同 System Forecast；p95: P95 缩放后的 Net Income(t) / P95 Revenue(t) |


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

- 两个子指标取**同一个月 t** 的数据
- MRR YoY Growth Rate(t) 为 null → 按 0 处理
- 理想值 ≥ 40%

**四种数据视图下的值：**


| 视图                            | 计算方式                                                                                         |
| ----------------------------- | -------------------------------------------------------------------------------------------- |
| **Financial Entry**           | 使用实际的 MRR YoY Growth Rate(t) + Net Profit Margin(t)                                          |
| **Committed Forecast**        | 使用 Committed 的 MRR YoY Growth Rate(t) + Net Profit Margin(t)                                 |
| **System Generated Forecast** | 使用 System Forecast 的 MRR YoY Growth Rate(t) + Net Profit Margin(t)                           |
| **Confidence Intervals**      | p05: P05 的 Growth Rate(t) + P05 的 Net Profit Margin(t)；p50: 同 System Forecast；p95: P95 的各值相加 |


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


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际收入，或从 QuickBooks 自动导入（`TotalIncome`） | `finance_manual_data`.`gross_revenue` |
| **Committed Forecast** | 用户手动输入月份 t 的预测收入值 | `financial_forecast_current`.`gross_revenue`, type=0 |
| **System Generated Forecast** | Formula 模式：复合增长 × 季节性因子；AI Model 模式：Ensemble 加权集成（见下方公式说明） | `financial_forecast_current`.`gross_revenue`, type=1/2 |
| **Confidence Intervals** | Monte Carlo 模拟的 p05/p50/p95 百分位值；仅 AI Model 模式有值，Formula 模式为 N/A（见下方公式说明） | `financial_forecast_current`.`p05`/`p50`/`p95`, type=2 |

**System Generated Forecast 公式说明：**

**Formula 模式**（calculateType = 1 或 2）：

```
Revenue(t) = revenueBase × (1 + resultGrowthRate) ^ diffMonth(t) × seasonalFactor(t)
```

- `revenueBase` = close month 的 Revenue
- `diffMonth(t)` = close month 到月份 t 的月数差
- `resultGrowthRate` = calculateType=1 时取同业增长率中位数；calculateType=2 时取 (同业中位数 + 自身平均) / 2
- `seasonalFactor` = 同业目标月均值/年均值的几何平均

**AI Model 模式**（calculateType = 3）：

```
Ensemble(t) = w_ETS × ETS(t) + w_ARIMA × ARIMA(t) + w_Momentum × Momentum(t)
```

- 权重 `w` = 各模型拟合 RMSE 倒数归一化

**Confidence Intervals 公式说明：**

```
simulation(t) = Ensemble(t) + N(0, std(历史数据))
```

- Monte Carlo 1000 次模拟，取 p05 = `percentile(模拟, 5)`，p50 = `percentile(模拟, 50)`，p95 = `percentile(模拟, 95)`


---

### 3.2 ARR（年经常性收入）


| 属性  | 值      |
| --- | ------ |
| ID  | `pl-2` |
| 单位  | 货币     |


**公式（月份 t，按 Revenue Recognition 模式分三种）：**


| `revenueRecognition` 值 | 模式 | 公式 | 计算步骤 |
|---|---|---|---|
| 1 | Last Month | `ARR(t) = MRR(t) × 12` | 直接取当月 MRR 乘以 12；若当月无 MRR 数据，返回 0 |
| 2 | Trailing Twelve Months | `ARR(t) = Average(MRR(t−11) ~ MRR(t)) × 12` | 取 `t−11` 到 `t` 共 12 个月的 MRR，求平均后 × 12；无数据月份的 MRR 视为 0 参与平均 |
| 3 | Last Three Months | `ARR(t) = Average(MRR(t−2) ~ MRR(t)) × 12` | 取 `t−2` 到 `t` 共 3 个月的 MRR，求平均后 × 12；无数据月份的 MRR 视为 0 参与平均 |

- `revenueRecognition` 是公司级别的配置字段，来源：数据库 `company` 表的 `revenue_recognition` 列（`int4`，默认值 1）
- 仅 ARR 指标受 Revenue Recognition 模式影响，MRR、New MRR LTM、MRR YoY Growth Rate 等其他指标均直接使用当月 MRR 值，不涉及模式分支

**四种数据视图下的值：**


| 视图                            | 计算方式                                       |
| ----------------------------- | ------------------------------------------ |
| **Financial Entry**           | 使用实际的 MRR 序列，按上述模式计算 ARR(t)                |
| **Committed Forecast**        | 使用 Committed 的 MRR 序列，按上述模式计算 ARR(t)       |
| **System Generated Forecast** | 使用 System Forecast 的 MRR 序列，按上述模式计算 ARR(t) |
| **Confidence Intervals**      | p05/p50/p95: 各自使用对应缩放后的 MRR 序列计算 ARR(t)    |


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


| 视图                            | 计算方式                                                                   |
| ----------------------------- | ---------------------------------------------------------------------- |
| **Financial Entry**           | = 实际录入的 Gross Revenue(t)                                               |
| **Committed Forecast**        | = Committed 的 Gross Revenue(t)                                         |
| **System Generated Forecast** | = System Forecast 的 Gross Revenue(t)                                   |
| **Confidence Intervals**      | p05: = P05 Revenue(t)；p50: = Forecast Revenue(t)；p95: = P95 Revenue(t) |


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

- `MRR(t−12)` = 12 个月前同月的 MRR，通过 `getLastYearMrrByDate()` 获取
- 无去年同月数据 → MRR(t−12) 视为 0

**四种数据视图下的值：**


| 视图                            | 计算方式                                          |
| ----------------------------- | --------------------------------------------- |
| **Financial Entry**           | 使用实际的 MRR(t) 与实际 MRR(t−12) 做差                 |
| **Committed Forecast**        | 使用 Committed 的 MRR(t) 与历史 MRR(t−12) 做差        |
| **System Generated Forecast** | 使用 System Forecast 的 MRR(t) 与对应的 MRR(t−12) 做差 |
| **Confidence Intervals**      | p05/p50/p95: 各自使用缩放后的 MRR(t) 与对应 MRR(t−12) 做差 |


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


| 视图                            | 计算方式                                             |
| ----------------------------- | ------------------------------------------------ |
| **Financial Entry**           | 使用实际 MRR(t) 和历史 MRR 序列，按上述条件公式计算                 |
| **Committed Forecast**        | 使用 Committed 的 MRR(t) 和历史 MRR 序列，按上述条件公式计算       |
| **System Generated Forecast** | 使用 System Forecast 的 MRR(t) 和完整 MRR 序列，按上述条件公式计算 |
| **Confidence Intervals**      | p05/p50/p95: 各自使用缩放后的 MRR(t) 和对应序列计算             |


---

### 3.6 COGS（销售成本）


| 属性     | 值      |
| ------ | ------ |
| ID     | `pl-6` |
| 单位     | 货币     |
| API 字段 | `cogs` |


**公式（月份 t）：** 原始输入，无计算公式。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际 COGS，或从 QuickBooks 导入（`Cogs`） | `finance_manual_data`.`cogs` |
| **Committed Forecast** | 用户手动输入月份 t 的预测 COGS | `financial_forecast_current`.`cogs`, type=0 |
| **System Generated Forecast** | `COGS(t) = cogsRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`cogs`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_COGS(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `cogsRate` = 自公司历史 COGS/Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

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


| 视图                            | 计算方式                                                                               |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| **Financial Entry**           | 实际 MRR(t) − 实际 COGS(t)                                                             |
| **Committed Forecast**        | Committed MRR(t) − Committed COGS(t)                                               |
| **System Generated Forecast** | Forecast MRR(t) − Forecast COGS(t)                                                 |
| **Confidence Intervals**      | p05: P05_MRR(t) − P05_COGS(t)；p50: 同 System Forecast；p95: P95_MRR(t) − P95_COGS(t) |


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


| 视图                            | 计算方式                                                                      |
| ----------------------------- | ------------------------------------------------------------------------- |
| **Financial Entry**           | 实际 Gross Profit(t) / 实际 MRR(t)                                            |
| **Committed Forecast**        | Committed Gross Profit(t) / Committed MRR(t)                              |
| **System Generated Forecast** | Forecast Gross Profit(t) / Forecast MRR(t)                                |
| **Confidence Intervals**      | p05: P05 Gross Profit(t) / P05 MRR(t)；p50: 同 System Forecast；p95: P95 值同理 |


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


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的 OE 总额，或由各实际子项汇总 | `finance_manual_data`.`operating_expenses` |
| **Committed Forecast** | 用户手动输入月份 t 的 OE 总额，或由各 Committed 子项汇总 | `financial_forecast_current`.`operating_expenses`, type=0 |
| **System Generated Forecast** | 各子项分别用 `rate × Revenue_forecast(t)` 计算后汇总（见 3.10–3.16） | `financial_forecast_current`.`operating_expenses`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_OE(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast OE(t)；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

---

### 3.10 S&M Expenses（销售与市场费用）


| 属性     | 值                   |
| ------ | ------------------- |
| ID     | `pl-10`             |
| 单位     | 货币                  |
| API 字段 | `smExpensesPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`SmExpense`） | `finance_manual_data`.`sm_expenses_percent` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`sm_expenses_percent`, type=0 |
| **System Generated Forecast** | `S&M Expenses(t) = smExpensesRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`sm_expenses_percent`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_S&M(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `smExpensesRate` = 自公司历史 S&M/Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

---

### 3.11 S&M Payroll（销售与市场人员薪酬）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `pl-11`            |
| 单位     | 货币                 |
| API 字段 | `smPayrollPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`SMPayroll`） | `finance_manual_data`.`sm_payroll_percent` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`sm_payroll_percent`, type=0 |
| **System Generated Forecast** | `S&M Payroll(t) = smPayrollRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`sm_payroll_percent`, type=1/2 |
| **Confidence Intervals** | p05/p95: 按 Revenue 比例缩放；p50: = Forecast 值 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `smPayrollRate` = 自公司历史 S&M Payroll / Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

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


| 视图                            | 计算方式                                                                     |
| ----------------------------- | ------------------------------------------------------------------------ |
| **Financial Entry**           | (实际 S&M(t) + 实际 S&M Payroll(t)) / 实际 New MRR LTM(t)                      |
| **Committed Forecast**        | (Committed S&M(t) + Committed S&M Payroll(t)) / Committed New MRR LTM(t) |
| **System Generated Forecast** | (Forecast S&M(t) + Forecast S&M Payroll(t)) / Forecast New MRR LTM(t)    |
| **Confidence Intervals**      | p05/p50/p95: 各自使用缩放后的值按公式计算                                              |


---

### 3.13 R&D Expenses（研发费用）


| 属性     | 值                   |
| ------ | ------------------- |
| ID     | `pl-13`             |
| 单位     | 货币                  |
| API 字段 | `rdExpensesPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`RdExpense`） | `finance_manual_data`.`rd_expenses_percent` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`rd_expenses_percent`, type=0 |
| **System Generated Forecast** | `R&D Expenses(t) = rdExpensesRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`rd_expenses_percent`, type=1/2 |
| **Confidence Intervals** | p05/p95: 按 Revenue 比例缩放；p50: = Forecast 值 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `rdExpensesRate` = 自公司历史 R&D Expenses / Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

---

### 3.14 R&D Payroll（研发人员薪酬）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `pl-14`            |
| 单位     | 货币                 |
| API 字段 | `rdPayrollPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`RDPayroll`） | `finance_manual_data`.`rd_payroll_percent` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`rd_payroll_percent`, type=0 |
| **System Generated Forecast** | `R&D Payroll(t) = rdPayrollRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`rd_payroll_percent`, type=1/2 |
| **Confidence Intervals** | p05/p95: 按 Revenue 比例缩放；p50: = Forecast 值 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `rdPayrollRate` = 自公司历史 R&D Payroll / Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

---

### 3.15 G&A Expenses（管理费用）


| 属性     | 值                   |
| ------ | ------------------- |
| ID     | `pl-15`             |
| 单位     | 货币                  |
| API 字段 | `gaExpensesPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`GaExpense`） | `finance_manual_data`.`ga_expenses_percent` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`ga_expenses_percent`, type=0 |
| **System Generated Forecast** | `G&A Expenses(t) = gaExpensesRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`ga_expenses_percent`, type=1/2 |
| **Confidence Intervals** | p05/p95: 按 Revenue 比例缩放；p50: = Forecast 值 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `gaExpensesRate` = 自公司历史 G&A Expenses / Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

---

### 3.16 G&A Payroll（管理人员薪酬）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `pl-16`            |
| 单位     | 货币                 |
| API 字段 | `gaPayrollPercent` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`GAPayroll`） | `finance_manual_data`.`ga_payroll_percent` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`ga_payroll_percent`, type=0 |
| **System Generated Forecast** | `G&A Payroll(t) = gaPayrollRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`ga_payroll_percent`, type=1/2 |
| **Confidence Intervals** | p05/p95: 按 Revenue 比例缩放；p50: = Forecast 值 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `gaPayrollRate` = 自公司历史 G&A Payroll / Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

---

### 3.17 Miscellaneous Operating Expenses（杂项运营支出）


| 属性     | 值                                    |
| ------ | ------------------------------------ |
| ID     | `pl-17`                              |
| 单位     | 货币                                   |
| API 字段 | `miscellaneousOperatingExpenses`     |


**公式（月份 t）：**

```
Misc OE(t) = Operating Expenses(t) − S&M Expenses(t) − S&M Payroll(t)
           − R&D Expenses(t) − R&D Payroll(t) − G&A Expenses(t) − G&A Payroll(t)
```

- 所有项取**同一个月 t** 的数据
- 若 `miscellaneousOperatingExpenses` 字段已有值（如 QuickBooks 自动导入），直接使用该值

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 按上述公式用实际的月份 t 各子项做差；或 QuickBooks 直接导入 | `finance_manual_data`.`miscellaneous_operating_expenses` |
| **Committed Forecast** | 按上述公式用 Committed 的月份 t 各子项做差 | `financial_forecast_current`.`miscellaneous_operating_expenses`, type=0 |
| **System Generated Forecast** | 按上述公式用 Forecast 的月份 t 各子项做差 | `financial_forecast_current`.`miscellaneous_operating_expenses`, type=1/2 |
| **Confidence Intervals** | p05/p50/p95: 各自使用缩放后的 OE 和各子项做差 | 按 Revenue CI 缩放计算 |

---

### 3.18 Other Expenses（其他支出）


| 属性     | 值               |
| ------ | --------------- |
| ID     | `pl-18`         |
| 单位     | 货币              |
| API 字段 | `otherExpenses` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`OtherIncome`） | `finance_manual_data`.`other_expenses` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`other_expenses`, type=0 |
| **System Generated Forecast** | `Other Expenses(t) = otherExpensesRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`other_expenses`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_OtherExp(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `otherExpensesRate` = 自公司历史 Other Expenses / Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

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


| 视图                            | 计算方式                                                                 |
| ----------------------------- | -------------------------------------------------------------------- |
| **Financial Entry**           | 实际 Gross Profit(t) − 实际 OE(t) − 实际 Other Exp(t)                      |
| **Committed Forecast**        | Committed Gross Profit(t) − Committed OE(t) − Committed Other Exp(t) |
| **System Generated Forecast** | Forecast Gross Profit(t) − Forecast OE(t) − Forecast Other Exp(t)    |
| **Confidence Intervals**      | p05/p50/p95: 各自用缩放后的 Gross Profit(t)、OE(t)、Other Exp(t) 按公式计算        |


---

### 3.20 Capitalized R&D (Monthly)（月度资本化研发支出）


| 属性     | 值              |
| ------ | -------------- |
| ID     | `pl-20`        |
| 单位     | 货币             |
| API 字段 | `capitalizedRd` |


**公式（月份 t）：** 原始输入。

QuickBooks 自动模式下：`Cap R&D(t) = −(RdCapitalized(t) − RdCapitalized(t−1))`，若结果 > 0 则取 0。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或 QuickBooks 自动计算 | `finance_manual_data`.`capitalized_rd` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`capitalized_rd`, type=0 |
| **System Generated Forecast** | `Cap R&D(t) = capitalizedRdRate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`capitalized_rd`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_CapRD(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `capitalizedRdRate` = 自公司历史 Cap R&D / Revenue 的中位数（历史 ≥ 6 月）或同业 rate 中位数（历史 < 6 月）

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


| 视图                            | 计算方式                                               |
| ----------------------------- | -------------------------------------------------- |
| **Financial Entry**           | 实际 Net Income(t) − 实际 Cap R&D(t)                   |
| **Committed Forecast**        | Committed Net Income(t) − Committed Cap R&D(t)     |
| **System Generated Forecast** | Forecast Net Income(t) − Forecast Cap R&D(t)       |
| **Confidence Intervals**      | p05/p50/p95: 各自用缩放后的 Net Income(t) 和 Cap R&D(t) 做差 |


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


| 视图                            | 计算方式                     |
| ----------------------------- | ------------------------ |
| **Financial Entry**           | 实际各子项之和                  |
| **Committed Forecast**        | Committed 各子项之和          |
| **System Generated Forecast** | Forecast 各子项之和           |
| **Confidence Intervals**      | p05/p50/p95: 各自用缩放后的子项之和 |


---

### 4.2 Cash（现金）


| 属性     | 值      |
| ------ | ------ |
| ID     | `bs-2` |
| 单位     | 货币     |
| API 字段 | `cash` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`Cash`） | `finance_manual_data`.`cash` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`cash`, type=0 |
| **System Generated Forecast** | 基于 close month 实际 Cash 逐月递推，考虑 Net Income、AR、Other Assets、AP 的变动量（见下方公式说明） | `financial_forecast_current`.`cash`, type=1/2 |
| **Confidence Intervals** | p05/p95: 按 P Revenue 比例调整各组件后重新递推；p50: = Forecast Cash(t)（见下方公式说明） | `financial_forecast_current`.`p05_cash`/`p50_cash`/`p95_cash`, type=2 |

**System Generated Forecast 公式说明：**

```
Cash(t) = Cash(t−1) + Net Income(t) − ΔAR(t) − ΔOther Assets(t) + ΔAP(t)
```

- `ΔAR(t) = AR(t) − AR(t−1)`
- `ΔOther Assets(t) = OtherAssets(t) − OtherAssets(t−1)`
- `ΔAP(t) = AP(t) − AP(t−1)`
- 第 1 个预测月以 close month 的实际 Cash 为起点

**Confidence Intervals 公式说明：**

各组件按 Revenue 比例缩放后重新递推：

```
dNetIncome  = (NetIncome(t) / Rev(t)) × P_Rev(t)
curAR       = (AR(t) / Rev(t)) × P_Rev(t)
lastAR      = (AR(t−1) / Rev(t−1)) × P_Rev(t−1)
dAR         = curAR − lastAR
```

- Other Assets、AP 同理按比例缩放
- 缩放后按 `P_Cash(t) = P_Cash(t−1) + dNetIncome − dAR − dAssets + dAP` 递推

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


| 视图                            | 计算方式                                                 |
| ----------------------------- | ---------------------------------------------------- |
| **Financial Entry**           | 用实际 Cash(t) 和实际 Burn Rate(t) 按上述条件计算                 |
| **Committed Forecast**        | 用 Committed Cash(t) 和 Committed Burn Rate(t) 按上述条件计算 |
| **System Generated Forecast** | 用 Forecast Cash(t) 和 Forecast Burn Rate(t) 按上述条件计算   |
| **Confidence Intervals**      | p05/p50/p95: 各自用缩放后的 Cash(t) 和 Burn Rate(t) 计算       |


---

### 4.4 Accounts Receivable（应收账款）


| 属性     | 值                    |
| ------ | -------------------- |
| ID     | `bs-4`               |
| 单位     | 货币                   |
| API 字段 | `accountsReceivable` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`AccountsReceivable`） | `finance_manual_data`.`accounts_receivable` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`accounts_receivable`, type=0 |
| **System Generated Forecast** | `AR(t) = AR_Rate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`accounts_receivable`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_AR(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast AR(t)；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `AR_Rate` = 自公司历史 AR / Revenue 的平均值

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


| 视图                            | 计算方式                                       |
| ----------------------------- | ------------------------------------------ |
| **Financial Entry**           | 累加所有实际 Cap R&D Monthly 至月份 t               |
| **Committed Forecast**        | 累加历史 + Committed 的所有 Cap R&D Monthly 至月份 t |
| **System Generated Forecast** | 累加历史 + Forecast 的所有 Cap R&D Monthly 至月份 t  |
| **Confidence Intervals**      | p05/p50/p95: 各自累加缩放后的 Cap R&D Monthly 序列   |


---

### 4.6 Other Assets（其他资产）


| 属性     | 值             |
| ------ | ------------- |
| ID     | `bs-6`        |
| 单位     | 货币            |
| API 字段 | `assetsOther` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`OtherAssets`） | `finance_manual_data`.`assets_other` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`assets_other`, type=0 |
| **System Generated Forecast** | `Other Assets(t) = Assets_Other_Rate × Revenue_forecast(t)`（见下方公式说明） | `financial_forecast_current`.`assets_other`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_OtherAssets(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast 值；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `Assets_Other_Rate` = 自公司历史 Other Assets / Revenue 的平均值

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


| 视图 | 计算方式 |
|------|----------|
| **Financial Entry** | 实际各子项之和 |
| **Committed Forecast** | Committed 各子项之和 |
| **System Generated Forecast** | Forecast 各子项之和 |
| **Confidence Intervals** | Long-Term Debt 和 Other Liabilities 置为 null，仅 AP 参与缩放（见下方说明） |

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


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`AccountsPayable`） | `finance_manual_data`.`accounts_payable` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`accounts_payable`, type=0 |
| **System Generated Forecast** | `AP(t) = AP_Rate × (COGS(t) + OE(t) + Other Expenses(t))`（见下方公式说明） | `financial_forecast_current`.`accounts_payable`, type=1/2 |
| **Confidence Intervals** | p05: `Forecast_AP(t) × (P05_Rev(t) / Forecast_Rev(t))`；p50: = Forecast AP(t)；p95: 按 P95 比例缩放 | 按 Revenue CI 缩放计算 |

**System Generated Forecast 公式说明：**

- `AP_Rate` = 自公司历史 AP / (COGS + OE + Other Expenses) 的平均值

---

### 4.9 Long-Term Debt（长期债务）


| 属性     | 值              |
| ------ | -------------- |
| ID     | `bs-9`         |
| 单位     | 货币             |
| API 字段 | `longTermDebt` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`LongTermDebt`） | `finance_manual_data`.`long_term_debt` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`long_term_debt`, type=0 |
| **System Generated Forecast** | 波动率复利外推，基于最近两个月的变动率逐月递推（见下方公式说明） | `financial_forecast_current`.`long_term_debt`, type=1/2 |
| **Confidence Intervals** | p05/p50/p95: 均为 **null**（不参与置信区间计算） | — |

**System Generated Forecast 公式说明：**

```
Fluctuation = (LTD_closeMonth − LTD_closeMonth−1) / LTD_closeMonth−1
```

- 若 `|Fluctuation| < 10%`，则 Fluctuation 取 0（视为无显著变动）

```
首月：LTD(1) = LTD_closeMonth × (1 + Fluctuation) ^ n
后续：LTD(t) = LTD(t−1) × (1 + Fluctuation)
```

- `n` = close month 到首个预测月的月数差

---

### 4.10 Other Liabilities（其他负债）


| 属性     | 值                  |
| ------ | ------------------ |
| ID     | `bs-10`            |
| 单位     | 货币                 |
| API 字段 | `liabilitiesOther` |


**公式（月份 t）：** 原始输入。

**四种数据视图下的值：**


| 视图 | 计算方式 | 数据存储 |
|------|----------|----------|
| **Financial Entry** | 用户手动录入月份 t 的实际值，或从 QuickBooks 导入（`OtherLiabilities`） | `finance_manual_data`.`liabilities_other` |
| **Committed Forecast** | 用户手动输入月份 t 的预测值 | `financial_forecast_current`.`liabilities_other`, type=0 |
| **System Generated Forecast** | 波动率复利外推，逻辑同 Long-Term Debt（见 4.9 公式说明） | `financial_forecast_current`.`liabilities_other`, type=1/2 |
| **Confidence Intervals** | p05/p50/p95: 均为 **null**（不参与置信区间计算） | — |

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


| 视图                            | 计算方式                                            |
| ----------------------------- | ----------------------------------------------- |
| **Financial Entry**           | 实际 Liabilities(t) / 实际 Assets(t)                |
| **Committed Forecast**        | Committed Liabilities(t) / Committed Assets(t)  |
| **System Generated Forecast** | Forecast Liabilities(t) / Forecast Assets(t)    |
| **Confidence Intervals**      | p05/p50/p95: 各自用缩放后的 Liabilities(t) / Assets(t) |


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


| 视图                            | 计算方式                                            |
| ----------------------------- | ----------------------------------------------- |
| **Financial Entry**           | 实际 Assets(t) − 实际 Liabilities(t)                |
| **Committed Forecast**        | Committed Assets(t) − Committed Liabilities(t)  |
| **System Generated Forecast** | Forecast Assets(t) − Forecast Liabilities(t)    |
| **Confidence Intervals**      | p05/p50/p95: 各自用缩放后的 Assets(t) − Liabilities(t) |


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


