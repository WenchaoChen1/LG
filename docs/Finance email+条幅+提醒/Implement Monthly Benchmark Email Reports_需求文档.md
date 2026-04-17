# 月度基准更新邮件 - 需求文档

## 功能概述

系统每月自动生成基准更新邮件，向公司管理员和投资组合经理推送公司财务更新对基准百分位的影响，通过邮件清晰展示百分位变化、基准类型对比，帮助用户无需登录平台即可了解相对竞争地位的变化。

## 功能模块详解

### 1. 邮件触发机制

#### 1.1 新closed month提交触发

**含义**：
当公司首次产生新的closed month财务数据时触发邮件生成。
- 背景补充,closed month定义： 
        Financial Statements Settings中为Manual的公司，closed month是Financia Entry表中最后一个有Actuals数据的月份；
        Financial Statements Settings中为Automatic的公司，closed month以15号为界限，如果系统服务器时间过了15号，就是上个月（前提是Financial Entry表中上个月有Actuals数据，若没有就继续往历史月份找，找到有actuals数据的月份位置）,
        如果系统服务器时间没过15号，就是上上个月（前提是Financial Entry表中上个月有Actuals数据，若没有就继续往历史月份找，找到有actuals数据的月份位置）。

**触发时机**：
- 每日定时检测，有新closed month时

**发送对象**：
- Company Admin（公司管理员）：仅包含本公司的信息
- 该公司所在的Portfolio的Portfolio manager：接收投资组合内有重要变化的邮件汇总

#### 1.2 25号月度定期触发

**触发时机**：
- 每月 25 日自动触发

**发送对象**：
- Company Admin：仅包含本公司的信息
- Portfolio Manager：接收投资组合内有重要变化的邮件汇总

### 2.邮件内容范围

#### 2.1 Company Admin邮件内容范围：

**内容范围**：
- 仅包含该公司的信息
- 包含所有 6 个基准指标的详细数据

#### 2.2 Portfolio manager邮件内容范围：

- 包括该Potfolio下所有有重大变化的公司
- 仅展示有重大变化的指标

**重大变化定义**：

至少满足以下任一条件：
1. **百分位移动阈值**：任何指标的Actual数据百分位移动 ≥ 5 个点（包括 Internal Peers 和任何外部基准）
   - 示例："ARR Growth Rate moved from P58 → P63"（移动 5 个点，包含）
   - 示例："Gross Margin moved from P40 → P42"（移动 2 个点，不包含）

2. **分位数跨越**：任何指标的Actual数据跨越分位数边界（Q1 ↔ Q2 ↔ Q3 ↔ Q4 等）（Q1: P0 ≤ n < P25, Q2: P25 ≤ n < P50,  Q3: P50 ≤ n < P75, Q4: P75 ≤ n ≤ P100 )
   - 示例："Monthly Runway moved from P49 (Q2) → P51 (Q3)"
   - 示例："Rule of 40 moved from P74 (Q4) → P70 (Q4)"（无跨越，不包含）
---

### 3. 邮件模板内容结构

#### 3.1 发送给Company Admin的邮件模板

##### 3.1.2 内容结构

**标题**

- Benchmarking Report for [CompanyName] — [ClosedMonth Year]
  例如：Benchmarking Report for Card Medic — March 2026

**内容**

- 问候语：格式为 "Hello [CompanyAdminName]"
  - 示例："Hello Jacobo Vargas"

- 情况简介：Your latest financials for [CompanyName] have been updated through [ClosedMonth Year]. Benchmark movement reflects updated company financials. Below is a summary of how your company’s performance compares to both industry benchmarks and your peers in Looking Glass:
  - 示例：“Your latest financials for Card Medic have been updated through March 2026. Benchmark movement reflects updated company financials.Below is a summary of how your company’s performance compares to both industry benchmarks and your peers in Looking Glass:”

- 数据展示：### 4.指标内容板块详解
[指标名称]：ARR Growth Rate、 Gross Margin、 Monthly Net Burn Rate、 Monthly Runway、 Rule of 40、 Sales Efficiency Ratio（指标展示顺序按照该排序）

[数据类型]：Actual、Committed Forecast/System Generated Forecast
 Actual:[该指标真实值]例如：64%
 Internal Peers: [该指标百分位↑/↓/无标记] (moved up/down from [上个closed month百分位])/无  百分位上升举例：P63 ↑ (moved up from P58)
 KeyBanc 2026:[该指标百分位↑/↓/无标记] (moved up/down from [上个closed month百分位])/无  百分位不变举例： P55 
 High Alpha 2026: [该指标百分位↑/↓/无标记] (moved up/down from [上个closed month百分位])/无  百分位下降举例：P55 ↓ (moved down from P70)
 Benchmarkit.ai 2026: P55

所有指标依次排列展示，每个指标包含不同数据类型，依次排列展示，Actual数据一定展示，预测数据优先Committed Forecast数据，若无Committed Forecast数据，则展示System Generated Forecast数据，如两种预测都没有，则不显示预测。

#### 3.2  Portfolio manager多公司邮件模板

**应用场景**
- 新closed month时Portfolio manager
- 每月25号，发送给Portfolio manager

**标题**

- Your Benchmarking Summarized Report is Ready

**内容**

- 问候语：Hello [PortfolioManagerName]
  - 示例：Hello Jacobo Vargas

- 情况简介：Your latest financials for [PortfolioName] have been updated. Benchmark movement reflects updated company financials. Below is a summary of companies with meaningful changes in benchmark positioning based on the latest financial updates.

  - 示例：Your latest financials for GSV Fund III have been updated. Benchmark movement reflects updated company financials.
Below is a summary of companies with meaningful changes in benchmark positioning based on the latest financial updates.

- 重要变化公司清单：
 Companies with Meaningful Benchmark Changes
 [CompanyName]
 [CompanyName]
 [CompanyName]
 - 例如：Companies with Meaningful Benchmark Changes
        Accelerist
        Brokerage Engine LLC
        FreightTrain

- 公司名称（英文按照A-Z顺序，中文按照首字母A-Z顺序。先排英文，再排中文）

- 数据展示：### 4.指标内容板块详解
- 内容范围：详见2.2
[指标名称]：ARR Growth Rate、 Gross Margin、 Monthly Net Burn Rate、 Monthly Runway、 Rule of 40、 Sales Efficiency Ratio（指标展示顺序按照该排序）

[数据类型]：Actual、Committed Forecast/System Generated Forecast
 Actual:[该指标真实值]例如：64%
 Internal Peers: [该指标百分位↑/↓/无标记] (moved up/down from [上个closed month百分位])/无  百分位上升举例：P63 ↑ (moved up from P58)
 KeyBanc 2026:[该指标百分位↑/↓/无标记] (moved up/down from [上个closed month百分位])/无  百分位不变举例： P55 
 High Alpha 2026: [该指标百分位↑/↓/无标记] (moved up/down from [上个closed month百分位])/无  百分位下降举例：P55 ↓ (moved down from P70)
 Benchmarkit.ai 2026: P55

所有指标依次排列展示，每个指标包含不同数据类型，依次排列展示，Actual数据一定展示，预测数据优先Committed Forecast数据，若无Committed Forecast数据，则展示System Generated Forecast数据，如两种预测都没有，则不显示预测。


### 4.指标内容板块详解

**指标列表**：

6 个指标按以下顺序展示，每个指标占一个板块（发送给Portfolio manager的邮件仅包含有重大变化的指标，指标顺序及内容如下）：

1. ARR Growth Rate
2. Gross Margin
3. Monthly Net Burn Rate
4. Monthly Runway
5. Rule of 40
6. Sales Efficiency Ratio

**每个指标的展示内容**：

**指标标题**：
- 指标名称（如 "ARR Growth Rate"）

**Actuals 数据行**：
- 包含：
  - 文本"Actuals"
  - 实际财务指标值
  - 内部同行百分位信息：
    - 百分位值（如"P72"）
    - 移动方向（↑ 上升 / ↓ 下降 / 无变）
    - 移动幅度（如"moved up from P68"）
  - 外部基准信息：
    - 基准名称 + edition（如"KeyBanc 2026"）
    - 该基准的百分位值（如"P70"）
    - 移动信息（如"moved up from P70" 或 无）
  - High Alpha 基准信息（如有）
  - Benchmarkit.ai 基准信息（如有）

**示例（ARR Growth Rate）**：
```
ARR Growth Rate
Actuals
Actual: 64%
Internal Peers: P63 ↑ (moved up from P58)
KeyBanc 2026: P55 
High Alpha 2026: P55 ↓ (moved down from P70)
Benchmark.it 2026: P55

```

**Committed Forecast 数据行**（如果有）：
- 仅当公司有 Committed Forecast 数据时才显示

**示例（ARR Growth Rate）**：
```
Committed Forecast
Committed Forecast: 64%
Internal Peers: P58
KeyBanc 2026: P55 
High Alpha 2026: P52
Benchmark.it 2026: P55
```
**System Generated Forecast 数据行**（如果无 Committed Forecast）：
- 仅当公司无 Committed Forecast 但有 System Generated Forecast 时才显示

**示例（ARR Growth Rate）**：
```
System Generated Forecast
System Generated Forecast: 64%
Internal Peers: P58
KeyBanc 2026: P55 
High Alpha 2026: P52
Benchmark.it 2026: P55
```

**数据来源**：
- 实际值：来自标准化财务数据（Normalization Tracing）
- 百分位：由百分位计算引擎生成
  - 内部同行：Nearest Rank 法计算
  - 外部基准：线性插值法计算
- 百分位移动：与上一个closed month对比计算
---

