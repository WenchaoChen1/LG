# 需求文档：季度基准报告自动导出至SharePoint

## 一、功能概述

系统需要自动生成并导出季度基准报告（PDF格式），将报告传送至指定的SharePoint位置供投资团队使用。该自动化流程旨在提供一致、及时的基准快照，支持投资团队的投资组合监控和季度报告工作流程。

---

## 二、业务目标


- 自动化季度基准报告生成，减少手动工作
- 确保报告的一致性和及时性
- 为投资团队提供标准化的基准快照
- 支持下游流程（生成单页投资摘要）

---

## 三、核心功能需求

### 3.1 报告自动生成

| 需求项 | 描述 |
|--------|------|
| **生成频率** | 每季度自动生成一次 |
| **生成时机** | 季末的第二个月第一天（如Q1报告在5月1日生成） |
| **覆盖范围** | 仅为拥有实际财务数据的公司生成报告 |
| **数据时点** | 使用报告生成时最新的最终化财务和基准数据 |

### 3.2 报告内容结构

#### 3.2.1 财务绩效快照
- **数据来源：** Company Overview、Financial Entry
- **数据范围：**
  - 公司logo，公司名称，公司状态
  - 公司简介（如有）
  - Financial Entry实际数据（Actuals）：从closed month往回推12个月
  - 已承诺预测（Committed Forecast）：完整数据集，始终为最新版本
  - 系统生成预测（System Generated Forecast）：完整数据集，始终为最新版本
  - 季度关键指标基准信息 计算方法详见3.2.2

#### 3.2.2 基准关键指标（基于实际数据）

**1. ARR Growth Rate**
- 计算方法：季度基准法
- 公式：`ARR_Growth_quarter = (ARR_end_of_quarter - ARR_start_of_quarter) / ARR_start_of_quarter`
- 特殊处理：
  - 若 ARR_start_of_quarter = 0，则 ARR_Growth_quarter = 0
  - 若 ARR_start_of_quarter = NA，则 ARR_Growth_quarter = 0
  - ARR_start_of_quarter如果为负，分母ARR_start_of_quarter就用绝对值

**2. Gross Margin**
- 计算方法：季度基准法，对季度总额进行收入加权
- 公式：`Gross_Margin_quarter = Gross_Profit_q / Gross_Revenue_q`
- 说明：Gross_Revenue_q = 季度内月度总收入之和；Gross_Profit_q = 季度内月度毛利之和

**3. Monthly Net Burn Rate**
- 计算方法：汇总季度成分后除以3得出代表性月度烧钱率
- 公式：`Monthly_Net_Burn_quarter = [SUM(Net Income) - SUM(Capitalized R&D)] / 3`

**4. Monthly Runway**
- 计算方法：季度末现金除以季度导出的月度烧钱率
- 公式：`Monthly_Runway_quarter = -（ Cash_at_quarter_end / Monthly_Net_Burn_quarter）`
- 说明：遵循LG前端表格中的相同显示逻辑（NA场景）

**5. Rule of 40**
- 计算方法：结合增长指标和从季度总额计算的盈利率
- 公式：`Rule_of_40_quarter = (Net_Profit_Margin_q + MRR_YoY_Growth_Rate_q) × 100%`
- 说明：Net_Profit_Margin_q = 季度内月度净利润率之和；MRR_YoY_q = 季度内月度MRR同比增长率之和

**6. Sales Efficiency**
- 计算方法：使用季度总额计算新收入和S&M支出，通过总额计算效率（收入或支出加权）
- 公式：`Sales_Efficiency_quarter = (S&M_Expenses_q + S&M_Payroll_q) / New_MRR_LTM_q`
- 说明：
  - S&M_Expenses_q = 季度内月度S&M支出之和
  - S&M_Payroll_q = 季度内月度S&M薪酬之和
  - New_MRR_LTM_q = 季度内月度新增MRR(最近12个月)之和

**数据完整性处理：** 分母为0时，记录并显示为0而非NULL

---

## 四、数据流和系统集成

### 4.1 数据来源
- 公司财务数据：LG应用基准模块中的数据
- 基准数据：LG应用中的基准定位信息
- 存储地点：GS内部系统和LG应用

### 4.2 报告分发流程

```
报告生成（季末的第二个月的第一天）
    ↓
验证公司生成报告的这个季度是否有实际数据（Actuals）
    ├→ 无数据：停止，不生成报告
    └→ 有数据：继续
    ↓
生成PDF报告
    ↓
上传至SharePoint位置
    ├→ SharePoint / Investment Team / LG Benchmarks / [CompanyName]
    └→ 同时下载至LG中的Documents - Company文件夹，如果没有公司文件夹，需要创建文件夹
    ↓
向SME发送通知邮件
    ├→ 通知人：Nico Carlson
    └→ 触发点：所有报告生成后再发通知
    ↓
错误处理
    ├→ PDF生成失败：记录错误日志
    ├→ SharePoint上传失败：记录错误日志
    └→ 后端日志完整记录各公司的成功/失败状态
```

---

## 五、文件命名和存储

### 5.1 文件命名规范
格式：`[CompanyName]_Benchmark_Report_[Quarter]_[Year].pdf`

示例：`SocialLadder_Benchmark_Report_Q1_2026.pdf`

### 5.2 存储位置
- **SharePoint路径：** `SharePoint / Investment Team / LG Benchmarks / [CompanyName]`
- **LG应用内：** `Documents - Company`文件夹，创建人是System

---

## 六、通知机制

### 6.1 SME邮件通知
- **触发条件：** 所有报告生成并成功上传至SharePoint后立即发送
- **收件人：** Nico Carlson（指定SME）
- **通知内容：** 基准报告已生成并可供审阅
- **目的：** 允许SME审阅报告，触发下游的一页投资摘要生成流程

### 6.2 错误处理通知
- **不需要额外的开发团队邮件通知**（后端日志将完整记录各公司报告的成功或失败情况）

---

## 七、数据完整性和校验

- 报告数据必须与报告生成时LG应用中显示的基准值一致
- 报告中的基准计算方式应与LG基准模块使用的方式相同
- 所有指标计算遵循上述公式，确保数据准确性

---



