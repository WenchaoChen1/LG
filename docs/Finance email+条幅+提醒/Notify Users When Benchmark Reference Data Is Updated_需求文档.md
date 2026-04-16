# 基准参考数据更新用户通知 - 需求文档

## 功能概述

当外部行业基准或LG基准发生重要性变化时，系统通过邮件和应用内横幅通知用户，保证信息透明度和用户信任。

---

## 详细说明

### 使用流程

#### 2.1 行业基准更新工作流

1. **管理员填写新行业基准版本**

2. **系统触发通知流程**
   - Benchmark Entry中同个平台的Edition有更新（例如KeyBanc平台目前有2023、2024、2025三个Edition,添加该平台的2026Edition,则触发；添加三个平台的新Edition，则触发三次）
   - Benchmark Entry中添加了新的平台（目前是三个平台，KeyBanc, High Alpha, Benchmarkit，若有新平台则触发通知）
   - 触发机制为实时触发，满足以上任何一条就直接触发邮件和横幅

3. **横幅提示**
   - Portfolio manager首次登录，会在portfolio benchmarking tab页面和company benchmarking tab页面提示；
   - Company Admin首次登录，会在company benchmarking tab页面提示。
   - 提示词例如：New benchmark data available. Benchmark comparisons now reflect the latest survey (KeyBanc SaaS Survey — 2026). Your relative positioning may change as a result. 括号内容是更新的 Benchmark Entry中的platform-Edition，若多个平台版本有更新的话，用逗号间隔开，显示在同一个横幅中。
   - 用户可关闭横幅。若不关闭，则一直显示。

4. **邮件提示**
   - 满足出发条件后Portfolio manager和Company Admin都会收到提示邮件
   - 邮件内容例如：
   标题: New Benchmark Survey Update
   正文：“Hello Jacobo Vargas,
         We’ve added a new industry benchmark survey (KeyBanc SaaS Survey — 2026) therefore benchmark comparisons now reflect the latest survey year.
         As a result, you may notice changes in your company’s relative positioning due to the updated benchmark data.
         If you have any questions or would like help interpreting these changes, feel free to reach out.”
         - 括号内容是更新的Benchmark Entry中的platform-Edition. 人名为实际接收人
    - 超链接：View Benchmark,点击进入Looking Glass系统，若未登录，则跳转至登录页面；若已登录，则跳转至portfolio benchmarking tab页面(portfolio portal角色)/company benchmarking tab页面(Company Admin角色)
    - 超链接跳转的异常处理: 若portfolio portal人员不再有对应公司的访问权限，则页面横幅不显示

#### 2.2 LG内部基准变化监测工作流

1. **触发条件**
   - closed month月份的任意指标的百分位计算由平台基准变为同行基准或由同行基准变为平台基准
   - closed month月份的任意指标值未改变但该指标actual对internal peer百分位变化超过10（如由P10变为P20)，该变化是由于内部基准变化导致（同行公司财务数据变化、同行公司变化）
   - closed month月份任意指标值变化且其同行公司/同行公司数据也变化导致的指标actual对internal peer百分位变化超过10
   - 指标：ARR Growth Rate、 Gross Margin、 Monthly Net Burn Rate、 Monthly Runway、 Rule of 40、 Sales Efficiency Ratio

2. **横幅提示**
   - Portfolio manager或其他有该公司权限的人首次登录，会在portfolio benchmarking tab页面提示；
   - Company Admin首次登录，会在company benchmarking tab页面提示。
   - 提示词例如：Benchmark positioning updated. Your company’s placement may have shifted due to changes in benchmark data, not your financial performance.
   - 用户可关闭横幅。若不关闭，则一直显示。

3. **邮件提示**
   - 满足触发条件后Portfolio manager或其他有该公司权限的人和Company Admin都会收到提示邮件
   - 邮件内容例如：
   标题: Update to Benchmark Positioning
   正文：“Hello Jacobo Vargas,
        You may notice a change in your company’s benchmark positioning.
        This shift is due to updates in the benchmark reference data, which can affect how companies are ranked relative to one another. It reflects movement within the cohort, not changes in your company’s financial performance.”
        - 人名为实际接收人，Portfolio manager或其他有该公司权限的人/Company Admin
    - 超链接：View Benchmark,点击进入Looking Glass系统，若未登录，则跳转至登录页面；若已登录，则跳转至portfolio benchmarking tab页面(portfolio portfolio角色)/company benchmarking tab页面(Company Admin角色)
    - 超链接跳转的异常处理: 若portfolio portal人员不再有对应公司的访问权限，则页面横幅不显示

4. **监测频率**
   - 每天定时检测

5. **监测数据类型**
   - Actuals数据
---

### 特殊情况说明

公司状态为Exited和Shut down的,未绑定portfolio的不进行监测

---

