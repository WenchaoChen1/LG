# financial_growth_rate 表 — 字段存入逻辑详解

> 版本：v2.0
> 创建时间：2026-03-19
> 关联文档：[Financial Entry 指标公式](./Financial-Entry-Metrics-Formulas.md) · [financial_forecast_current 表](./financial_forecast_current.md) · [finance_manual_data 表](./finance_manual_data.md)

---

## 1. 表概述

| 属性 | 值 |
|------|-----|
| 表名 | `financial_growth_rate` |
| 实体类 | `FinancialGrowthRate` → `AbstractCustomEntity` |
| 数据粒度 | 一条记录 = 一个公司 + 一个月份 |
| 用途 | 中间计算表，存储每月增长率和各指标/收入比率，供预测使用 |
| 写入方式 | 先删后插（`deleteAllByCompanyId` + `saveAll`），每次全量重建 |

---

## 2. 存入场景总览

本表只有 **1 个存入场景**，由代码自动计算生成，无用户输入：

| 场景 | 触发方式 | 代码入口 |
|------|---------|---------|
| **系统自动计算** | ① 用户提交财务数据后自动触发；② 每日定时任务（23:00） | 按公司重算并写回本表 |

**数据来源**：所有字段均从 `finance_manual_data` 表（或 Automatic 模式下从 Redshift QuickBooks）查询得到的 `FiDataDto` 计算而来。  
**数据元**：Manual 模式下各字段来自表 `finance_manual_data` 同名列（见 [finance_manual_data 表 — 第 3 节](./finance_manual_data.md#3-每个字段的存入逻辑)）；Automatic 模式下为 Redshift QuickBooks 映射，具体表与列名见 [Financial Entry 指标公式 — 1.7](./Financial-Entry-Metrics-Formulas.md#17-数据录入模式与-quickbooks-字段映射)。

**前置条件**：需要至少 2 个月的有效财务数据（`fiDataList.size() >= 2`），否则跳过不更新。

---

## 3. 每个字段的存入逻辑

### 3.1 `revenue` — 月度收入

| 数据来源 | 业务公式 |
|---------|---------|
| 表 `finance_manual_data` 列 `gross_revenue`（来自上游当月收入） | **直接赋值**：将当月收入写入本表列 `revenue` |

> 若 `grossRevenue` 为 null 则跳过该月，不生成记录。

### 3.2 `growth_rate` — 月度增长率

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询当前月和前月的 `finance_manual_data.gross_revenue` | 由 `calculateGrowthRate(fiDataList, currentIndex)` 计算 |

**数据元**：当前月与前一个有效月的 Revenue 来自表 `finance_manual_data` 列 `gross_revenue`，按 `company_id`、`date` 排序后取当前月及向前第一个 `gross_revenue ≥ 0` 的月份。

**计算逻辑：**

```
输入：当前月 grossRevenue（currentRevenue），前一个有效月 grossRevenue（previousRevenue）

条件：
├── 是第一条数据（无前月）→ null
├── currentRevenue < 0 → null
├── 向前找不到 grossRevenue ≥ 0 的月份 → null
├── previousRevenue = 0 → 0
├── 与前月相邻（间隔 1 月）
│   └── = (currentRevenue − previousRevenue) / previousRevenue
└── 与前月不相邻（间隔 N 月）
    └── = (currentRevenue / previousRevenue) ^ (1/N) − 1（复合月增长率）
```

> "前一个有效月"指从当前月向前查找，第一个 `grossRevenue ≥ 0` 的月份。

### 3.3 `cogs_rate` — COGS / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `cogs` 和 `gross_revenue` | `= calculateRate(cogs, grossRevenue)` |

### 3.4 `sm_expenses_rate` — S&M Expenses / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `sm_expenses_percent` 和 `gross_revenue` | `= calculateRate(sm_expenses_percent, grossRevenue)` |

### 3.5 `sm_payroll_rate` — S&M Payroll / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `sm_payroll_percent` 和 `gross_revenue` | `= calculateRate(sm_payroll_percent, grossRevenue)` |

### 3.6 `rd_expenses_rate` — R&D Expenses / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `rd_expenses_percent` 和 `gross_revenue` | `= calculateRate(rd_expenses_percent, grossRevenue)` |

### 3.7 `rd_payroll_rate` — R&D Payroll / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `rd_payroll_percent` 和 `gross_revenue` | `= calculateRate(rd_payroll_percent, grossRevenue)` |

### 3.8 `ga_expenses_rate` — G&A Expenses / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `ga_expenses_percent` 和 `gross_revenue` | `= calculateRate(ga_expenses_percent, grossRevenue)` |

### 3.9 `ga_payroll_rate` — G&A Payroll / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `ga_payroll_percent` 和 `gross_revenue` | `= calculateRate(ga_payroll_percent, grossRevenue)` |

### 3.10 `other_expenses_rate` — Other Expenses / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `other_expenses` 和 `gross_revenue` | `= calculateRate(other_expenses, grossRevenue)` |

### 3.11 `operating_expenses` — Operating Expenses / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `operating_expenses` 和 `gross_revenue` | `= calculateRate(operating_expenses, grossRevenue)` |

> 此字段存的是 rate（OE/Revenue），不是 OE 原始金额。字段名容易混淆。

### 3.12 `capitalized_rd_rate` — Cap R&D / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `capitalized_rd` 和 `gross_revenue` | `= calculateRate(capitalized_rd, grossRevenue)` |

### 3.13 `accounts_receivable_rate` — AR / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `accounts_receivable` 和 `gross_revenue` | `= calculateRate(accounts_receivable, grossRevenue)` |

### 3.14 `assets_Other_rate` — Other Assets / Revenue

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `assets_Other` 和 `gross_revenue` | `= calculateRate(assets_Other, grossRevenue)` |

### 3.15 `accounts_payable_rate` — AP / (COGS + OE + OtherExpenses)

| 数据来源 | 业务公式 |
|---------|---------|
| 数据库查询 `finance_manual_data` 的 `accounts_payable`、`cogs`、`operating_expenses`、`other_expenses` | `= calculateRate(accounts_payable, cogs + operating_expenses + other_expenses)` |

> **AP 的分母不是 Revenue**，而是 `cogs + operating_expenses + other_expenses`。这是唯一一个分母不同的字段。

---

## 4. rate 的计算方式（分子÷分母）

所有 rate 字段均为「分子 ÷ 分母」后写入本表对应列：

- **数据来源**：分子、分母均来自当月的上游数据（表 `finance_manual_data` 或 Redshift 的对应列，如 `cogs`、`gross_revenue` 等）。
- **规则**：分子为空则不写本列；分母为负不写；分母为 0 则写 0；否则写分子除以分母的结果，保留 10 位小数、四舍五入。  
> **公用逻辑**：预测时读取的是本表已写入的 rate 列，中位数/几何平均等聚合逻辑见 [Financial Entry 指标公式 — 第 6、10 节](./Financial-Entry-Metrics-Formulas.md#6-system-generated-forecast-中各-rate-的来源说明)。

---

## 5. 数据生成完整流程

1. 查表 `company_quickbooks` 得到该公司模式（Manual / Automatic）。
2. 确定截止日期：Manual 为当月初；Automatic 为当月 15 日前用前两月初、否则前一月初。
3. 查表 `finance_manual_data` 取该公司最新版本号。
4. 按公司与日期范围取上游数据：Manual 查表 `finance_manual_data`，Automatic 查 Redshift QuickBooks 表。
5. 若不足 2 条则本表不更新。
6. 按日期排序，逐月：跳过当月收入为空的月份；当月收入写入本表 `revenue`；增长率按 §3.2 计算写入 `growth_rate`；各 rate 按 §4 计算写入对应列。
7. 删除该公司在本表的旧数据，再批量写入新数据。

> **跨文件**：本表写入结果被 [financial_forecast_current](./financial_forecast_current.md) 预测逻辑与 [Financial Entry 指标公式](./Financial-Entry-Metrics-Formulas.md) 第 6、8.7、10 节引用。

---

## 6. 在预测中如何被使用

### 6.1 决定预测模式

按公司与最近 24 月、close month 从本表取记录数：≥24 条用 AI 模型（type='2'）；6～23 条用公式混合模式（type='1'）；<6 条用公式纯同业模式（type='1'）。

### 6.2 各字段的使用方式

| 字段 | 使用场景 | 说明 |
|------|---------|------|
| `revenue` | AI 模型输入、季节性因子计算 | 作为 Python 预测引擎的 `historical_data`；计算同业月平均用 |
| `growth_rate` | Revenue 增长率预测 | 自身或同业的 growth_rate 做几何平均/中位数 |
| `cogs_rate` ~ `capitalized_rd_rate` | P&L 各项预测 | `rate × Revenue_forecast` |
| `accounts_receivable_rate` | AR 预测 | `avg(rate) × Revenue_forecast`（仅自公司） |
| `assets_Other_rate` | Other Assets 预测 | `avg(rate) × Revenue_forecast`（仅自公司） |
| `accounts_payable_rate` | AP 预测 | `avg(rate) × (COGS + OE + OtherExp)_forecast`（仅自公司） |

### 6.3 同业公司筛选

查询同业公司 growth rate 数据时，通过 `findAllColleagueCompanyData(companyId, companyType, stage, accountMethod)` 筛选，主要步骤：按公司类型、发展阶段、会计方法匹配 → 剔除数据不足或 close month 无数据的公司 → ARR 区间一致 → 最近 24 月内连续 6 月正收入 → 异常值截断 → 不足 3 家时 fallback 全平台。

**数据元**：公司类型/阶段/会计方法来自表 `company`、`r_company_stage`、`stage`；ARR 来自 `FiDataDto`（即 `finance_manual_data`.`gross_revenue` 等）；rate 与收入来自表 `financial_growth_rate`。

> **公用逻辑**：完整筛选条件、内存过滤与兜底规则见 [Financial Entry 指标公式 — 8.7](./Financial-Entry-Metrics-Formulas.md#87-同业公司peer-companies筛选逻辑)。

---

## 7. 代码位置索引

| 类型 | 文件路径 |
|------|---------|
| 实体类 | `gstdev-cioaas-web/.../fi/domain/FinancialGrowthRate.java` |
| Repository | `gstdev-cioaas-web/.../fi/repository/FinancialGrowthRateRepository.java` |
| Service 实现 | `gstdev-cioaas-web/.../fi/service/FinancialGrowthRateServiceImpl.java` |
| 写入触发 | `gstdev-cioaas-web/.../fi/service/FinancialStatementServiceImpl.java` |
| 预测中使用 | `gstdev-cioaas-web/.../fi/service/FinancialForecastDataServiceImpl.java` |
| 异常值处理 | `gstdev-cioaas-web/.../fi/util/FinancialRateSums.java` |
