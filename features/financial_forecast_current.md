# financial_forecast_current 表 — 字段存入逻辑详解

> 版本：v2.0
> 创建时间：2026-03-19
> 关联文档：[Financial Entry 指标公式](./Financial-Entry-Metrics-Formulas.md)

---

## 1. 表概述

| 属性 | 值 |
|------|-----|
| 表名 | `financial_forecast_current` |
| 实体类 | `FinancialForecastCurrent` → `FinanceManualDataAbstract` → `AbstractCustomEntity` |
| 数据粒度 | 一条记录 = 一个公司 + 一个月份 + 一个 type |
| 用途 | 存储 Committed Forecast、System Generated Forecast、Confidence Intervals |

---

## 2. 存入场景总览

本表有 **3 个存入场景**，通过 `type` 字段区分：

| 场景 | type | 触发方式 | 数据来源 |
|------|------|---------|---------|
| **场景 A：Committed Forecast** | `"0"` (MANUAL) | 用户手动提交预测 / Accept as Committed | 前端用户输入 或 复制 System Forecast |
| **场景 B：System Forecast（公式模式）** | `"1"` (FORMULA) | `financialEntrySubmit` 后自动触发 / 每日定时任务 | 数据库查询 `financial_growth_rate` 计算 |
| **场景 C：System Forecast（AI 模型模式）** | `"2"` (MODEL) | 同场景 B | CIOaas-python AI 预测 + 数据库 rate 计算 |

**写入方法**（三个场景共用）：先删除该公司、该日期范围、该 type 的旧数据，再批量写入新数据；同时写入历史表 `financial_forecast_history`。

---

## 3. 每个字段的存入逻辑

### 3.1 `gross_revenue` — 预测总收入

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B (FORMULA)** | 数据库查询：`financial_growth_rate` 表（当前公司 + 同业公司）+ `finance_manual_data`（revenueBase） | `revenueBase × (1 + resultGrowthRate) ^ diffMonth × seasonalFactor`（详见下方公式说明） |
| **场景 C (MODEL)** | CIOaas-python API 返回的 `Ensemble` 预测值 | Python 端 `ETS + ARIMA + Momentum` 加权集成，输入为 `financial_growth_rate.revenue` 最近 24 月数据 |

**场景 B 各参数说明：**

| 参数 | 含义 | 公式 | 数据来源 |
| --- | --- | --- | --- |
| `revenueBase` | close month 的实际 Revenue | 直接读取 | `finance_manual_data`.`gross_revenue`；<br>取当前公司 close month 对应日期的记录，<br>若同一日期有多条则取 `updated_at` 最新的一条 |
| `diffMonth(t)` | close month 到预测月份 t 的月数差 | `abs(年×12+月 之差)` | 纯日期计算，不查库 |
| `resultGrowthRate` | 复合月增长率 | **type=1**：`median(geometricMean(peer_i))`<br>**type=2**：`(同业中位数 + 自公司算术平均) / 2` | `financial_growth_rate`.`growth_rate`；<br>取同业公司（筛选条件见下方「同业公司获取逻辑」）中 `growth_rate` 不为空的记录，<br>对每家公司的 `growth_rate` 取几何平均后，再对所有公司取中位数；<br>type=2 时还需取当前公司自身的 `growth_rate` 求算术平均 |
| `seasonalFactor(t)` | 目标月份的季节性调整系数 | `geometricMean(targetMonthAvg_i / yearAvg_i)`；<br>无同业数据时 = 1 | `financial_growth_rate`.`revenue`；<br>取同业公司（筛选条件见下方）中 revenue ≥ 0 的记录，按日期中的月份分组：<br>targetMonthAvg = 目标月份（如 03 月）各年 Revenue 的平均值，<br>yearAvg = 该公司所有月 Revenue 的平均值；<br>对所有同业公司的 targetMonthAvg / yearAvg 取几何平均 |

**权重说明（resultGrowthRate，type=2）：**  
当 `calculateType=2`（当前公司在 `financial_growth_rate` 中有效月数 ≥ 6）时，复合月增长率采用**自身与同业各占 50%** 的加权：  
`resultGrowthRate = (同业 growth_rate 中位数 + 自公司 growth_rate 算术平均) / 2`。即同业中位数与自公司算术平均**等权**，各 50%。

**同业公司获取逻辑**：来源（手动同业组或系统自动匹配）、内存过滤条件与兜底规则详见 [Financial Entry 指标公式 — 8.7 同业公司筛选](./Financial-Entry-Metrics-Formulas.md#87-同业公司peer-companies筛选逻辑) 与 [financial_growth_rate — 6.3 同业公司筛选](./financial_growth_rate.md#63-同业公司筛选)。

**场景 C 各参数说明：**

| 参数 | 含义 | 公式 | 数据来源 |
| --- | --- | --- | --- |
| 输入数据 | 最近 24 个月的月度 Revenue 序列 | 直接读取，传入预测引擎 | `financial_growth_rate`.`revenue`；取当前公司从 close month 往前 24 个月的记录，按日期升序排列 |
| ETS | 指数平滑模型预测值 | 指数平滑拟合后外推 24 个月 | CIOaas-python 预测引擎内存计算，不落库 |
| ARIMA | SARIMAX 模型预测值 | SARIMAX 拟合后外推 24 个月 | 同上 |
| Momentum | 动量线性外推预测值 | `forecast[i] = last_value + (i+1) × mean(最后 3 个差分)` | 同上 |
| `w_i` | 模型权重 | `(1/RMSE_i) / Σ(1/RMSE_j)`；所有 RMSE 极小时均分 1/3 | 内存计算，不落库 |

调用流程：Java 端从 `financial_growth_rate` 取 24 个月 Revenue → 调用 CIOaas-python 预测接口 → 返回 Ensemble 值 → 写入本表 `gross_revenue`

### 3.2 `cogs` — 预测销售成本

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `cogs_rate` | `cogsRate × gross_revenue(预测值)` |

**数据元**：cogsRate 来自表 `financial_growth_rate` 列 `cogs_rate`。  
**rate 取值**：自公司有效条数 ≥ 6 取自公司中位数，否则取同业几何平均的中位数，详见 [§4 P&L Rate 取值逻辑汇总](#4-pl-rate-取值逻辑汇总)。

### 3.3 `sm_expenses_percent` — 预测 S&M 费用

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `sm_expenses_rate` | `smExpensesRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `sm_expenses_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.4 `sm_payroll_percent` — 预测 S&M 薪酬

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `sm_payroll_rate` | `smPayrollRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `sm_payroll_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.5 `rd_expenses_percent` — 预测 R&D 费用

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `rd_expenses_rate` | `rdExpensesRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `rd_expenses_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.6 `rd_payroll_percent` — 预测 R&D 薪酬

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `rd_payroll_rate` | `rdPayrollRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `rd_payroll_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.7 `ga_expenses_percent` — 预测 G&A 费用

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `ga_expenses_rate` | `gaExpensesRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `ga_expenses_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.8 `ga_payroll_percent` — 预测 G&A 薪酬

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `ga_payroll_rate` | `gaPayrollRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `ga_payroll_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.9 `other_expenses` — 预测其他费用

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `other_expenses_rate` | `otherExpensesRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `other_expenses_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.10 `capitalized_rd` — 预测月度资本化 R&D

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询表 `financial_growth_rate` 列 `capitalized_rd_rate` | `capitalizedRdRate × gross_revenue(预测值)` |

**rate 取值**：同 cogs，列名 `capitalized_rd_rate`，详见 [§4](#4-pl-rate-取值逻辑汇总)。

### 3.11 `operating_expenses` — 预测运营费用

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 由上述 6 项计算得出 | `= sm_expenses + sm_payroll + rd_expenses + rd_payroll + ga_expenses + ga_payroll`（不独立使用 rate） |

### 3.12 `accounts_receivable` — 预测应收账款

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询**仅自公司** `financial_growth_rate.accounts_receivable_rate` | `avg(accounts_receivable_rate) × gross_revenue(预测值)`（算术平均，有效月 < 3 则返回 0） |

> AR 不使用同业数据，Projection Basis 固定为 `SELF_BASED_FORMULA`。  
> **数据元**：`accounts_receivable_rate` 来自表 `financial_growth_rate` 列 `accounts_receivable_rate`（该 rate 由 [financial_growth_rate 表](./financial_growth_rate.md) 从 `finance_manual_data`.`accounts_receivable` 与 `gross_revenue` 计算得出）。

### 3.13 `assets_Other` — 预测其他资产

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询**仅自公司** `financial_growth_rate.assets_Other_rate` | `avg(assets_Other_rate) × gross_revenue(预测值)`（算术平均，有效月 < 3 则返回 0）<br>**数据元**：`assets_Other_rate` 来自表 `financial_growth_rate` 列 `assets_Other_rate`（由 [financial_growth_rate — 3.14](./financial_growth_rate.md#314-assets_other_rate--other-assets--revenue) 从 `finance_manual_data`.`assets_Other` 与 `gross_revenue` 计算） |

### 3.14 `accounts_payable` — 预测应付账款

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询**仅自公司** `financial_growth_rate.accounts_payable_rate` | `avg(accounts_payable_rate) × (预测COGS + 预测OE + 预测OtherExpenses)`（算术平均，有效月 < 3 则返回 0） |

> AP 的 rate 分母是 `COGS + OE + OtherExpenses`，不是 Revenue。  
> **数据元**：`accounts_payable_rate` 来自表 `financial_growth_rate` 列 `accounts_payable_rate`（分母为 `finance_manual_data` 的 cogs + operating_expenses + other_expenses，见 [financial_growth_rate — 3.15](./financial_growth_rate.md#315-accounts_payable_rate--ap--cogs--oe--otherexpenses)）。

### 3.15 `cash` — 预测现金

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询 `finance_manual_data`（close month Cash）+ 本表各预测字段 | `Cash(t) = Cash(t−1) + NetIncome(t) − ΔAR(t) − ΔOtherAssets(t) + ΔAP(t)`（逐月递推） |

**递推公式详解：**

| 参数 | 含义 | 公式 | 数据来源 |
| --- | --- | --- | --- |
| `Cash(0)` | 递推起点 | 直接读取 close month 实际 Cash | `finance_manual_data`.`cash`；<br>取当前公司 close month 对应日期的记录（数据元：同上表列） |
| `NetIncome(t)` | 月份 t 的预测净利润 | `= Gross Revenue(t) − COGS(t) − OE(t) − Other Expenses(t)` | 本表同月各预测字段计算得出 |
| `ΔAR(t)` | 应收账款变动量 | `= AR(t) − AR(t−1)` | 本表当月和上月的 `accounts_receivable` |
| `ΔOtherAssets(t)` | 其他资产变动量 | `= OtherAssets(t) − OtherAssets(t−1)` | 本表当月和上月的 `assets_other` |
| `ΔAP(t)` | 应付账款变动量 | `= AP(t) − AP(t−1)` | 本表当月和上月的 `accounts_payable` |

> 第 1 个预测月以 close month 的实际 Cash 为起点，后续每月在前一月预测 Cash 基础上递推。

### 3.16 `long_term_debt` — 预测长期债务

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询 `finance_manual_data`（close month 和 close month−1 的 `long_term_debt`） | 波动率复利外推（见下方公式说明） |

**波动率外推公式详解：**

| 参数 | 含义 | 公式 | 数据来源 |
| --- | --- | --- | --- |
| `Fluctuation` | 最近两个月的变动率 | `(LTD_closeMonth − LTD_closeMonth−1) / LTD_closeMonth−1`；若 \|Fluctuation\| < 10% 则取 0（视为无显著变动） | `finance_manual_data`.`long_term_debt`；取 close month 和 close month − 1 月的记录 |
| 首月预测值 | 第 1 个预测月的 LTD | `LTD_closeMonth × (1 + Fluctuation) ^ n`；n = close month 到首个预测月的月数差 | 同上 |
| 后续预测值 | 第 2~24 个预测月的 LTD | `LTD(t) = LTD(t−1) × (1 + Fluctuation)` | 逐月递推 |

### 3.17 `liabilities_other` — 预测其他负债

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 前端用户输入 | 直接存入 |
| **场景 B/C** | 数据库查询 `finance_manual_data`（close month 和 close month−1 的 `liabilities_other`） | 波动率复利外推，逻辑同 `long_term_debt`（见 3.16），初始值取 `finance_manual_data`.`liabilities_other` |

### 3.18 `p05` / `p50` / `p95` — Revenue 置信区间

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 不写入 | null |
| **场景 B (FORMULA)** | 不写入 | null |
| **场景 C (MODEL)** | CIOaas-python API 返回 | `simulation(t) = Ensemble(t) + N(0, noise_std)`，1000 次 Monte Carlo 模拟后取百分位值 |

**场景 C 各参数说明：**

| 参数 | 含义 | 公式 | 数据来源 |
| --- | --- | --- | --- |
| `noise_std` | 历史 Revenue 的波动幅度 | 24 个月历史 Revenue 的总体标准差 | 同 AI Model 的输入数据（`financial_growth_rate`.`revenue`），内存计算 |
| 模拟次数 | Monte Carlo 模拟轮数 | 固定 1000 次 | 固定值 |
| p05 | 悲观预测值 | `percentile(1000 次模拟结果, 5)` | 预测引擎计算后返回 |
| p50 | 中位预测值 | `percentile(1000 次模拟结果, 50)` | 同上 |
| p95 | 乐观预测值 | `percentile(1000 次模拟结果, 95)` | 同上 |

### 3.19 `p05_cash` / `p50_cash` / `p95_cash` — Cash 置信区间

| 存入场景 | 数据来源 | 业务公式 |
|---------|---------|---------|
| **场景 A** | 不写入 | null |
| **场景 B (FORMULA)** | 不写入 | null |
| **场景 C (MODEL)** | 本表各预测字段 + p05/p95 Revenue | `P_Cash(t) = P_Cash(t−1) + P_dNetIncome(t) − P_dAR(t) − P_dAssets(t) + P_dAP(t)`（各组件按 Revenue CI 比例缩放后重新递推） |

**CI Cash 递推各参数说明：**

| 参数 | 含义 | 公式 | 数据来源 |
| --- | --- | --- | --- |
| `P_Cash(0)` | 递推起点 | = close month 实际 Cash（同 Forecast Cash 起点） | `finance_manual_data`.`cash` |
| `P_dNetIncome(t)` | 缩放后净利润 | `(NetIncome(t) / Revenue(t)) × P_Revenue(t)` | NetIncome 和 Revenue 取本表同月 Forecast 值，P_Revenue 取本表 `p05` 或 `p95` |
| `P_dAR(t)` | 缩放后 AR 变动 | `P_AR(t) − P_AR(t−1)`；`P_AR(t) = (AR(t) / Revenue(t)) × P_Revenue(t)` | 同上 |
| `P_dAssets(t)` | 缩放后 Other Assets 变动 | 同理按 Revenue 比例缩放后做差 | 同上 |
| `P_dAP(t)` | 缩放后 AP 变动 | 同理按 Revenue 比例缩放后做差 | 同上 |
| `p50_cash` | 中位 Cash 预测 | `= cash`（等于 Forecast Cash 值） | 直接取本表 `cash` 字段 |

---

## 4. P&L Rate 取值逻辑汇总

场景 B/C 中 P&L 各项的 rate 统一通过 `calculatePropertyMedian` 方法取得：

```
输入：当前公司的 financial_growth_rate 列表 + 同业公司的 financial_growth_rate 列表

逻辑：
├── 自公司该 rate 的非 null 值 ≥ 6 条
│   └── 取自公司所有值的中位数（降序排列取中间值）
│
└── 自公司该 rate 的非 null 值 < 6 条
    ├── 对每家同业公司：取该 rate 所有值的几何平均
    ├── 收集所有同业的几何平均值
    └── 取这些几何平均值的中位数
    └── 若无同业数据 → 返回 0
```

**数据元**：上述「rate」均来自表 `financial_growth_rate` 的对应列（如 `cogs_rate`、`sm_expenses_rate` 等），该表由 [financial_growth_rate 表文档](./financial_growth_rate.md) 从 `finance_manual_data`（或 Redshift）计算写入。

> **公用逻辑**：中位数与几何平均的**计算步骤**见 [Financial Entry 指标公式 — 6.2、6.3](./Financial-Entry-Metrics-Formulas.md#62-中位数的计算方法)；同业公司筛选见 [8.7](./Financial-Entry-Metrics-Formulas.md#87-同业公司peer-companies筛选逻辑)。

---

## 5. 代码位置索引

| 类型 | 文件路径 |
|------|---------|
| 实体类 | `gstdev-cioaas-web/.../fi/domain/FinancialForecastCurrent.java` |
| Repository | `gstdev-cioaas-web/.../fi/repository/FinancialForecastCurrentRepository.java` |
| Service（预测生成+保存） | `gstdev-cioaas-web/.../fi/service/FinancialForecastDataServiceImpl.java` |
| Service（Cash/CI 计算） | `gstdev-cioaas-web/.../fi/service/FiDataCalculateServiceImpl.java` |
| Service（Committed） | `gstdev-cioaas-web/.../fi/service/FinancialForecastHistoryServiceImpl.java` |
| Python 预测引擎 | `CIOaas-python/source/forecast/forecast_engine.py` |

> **跨文件**：Cash 递推、LTD/Other Liabilities 波动率外推、P&L rate 取值等公用逻辑的集中说明见 [Financial Entry 指标公式 — 第 10 节](./Financial-Entry-Metrics-Formulas.md#10-公式公用逻辑与代码位置跨文件)。
