# 测试用例：导入时自动计算 OPEX 总额以避免校验报错

- **需求来源**：https://github.com/WenchaoChen1/LG/blob/master/docs/智能解析/需求文档-导入时自动计算OPEX总额.md
- **Asana 任务**：Auto-Calculate OPEX Total on Import to Prevent Validation Error（task/1215349591481274）
- **适用页面**：Financial Entry（财务录入）页、Committed Forecast（承诺预测）页 — 后端导入写入流程
- **生成时间**：2026-06-16

> 约定缩写（六个手动录入子项）：S&M Exp（S&M Expenses）、S&M Pay（S&M Payroll）、R&D Exp、R&D Pay、G&A Exp、G&A Pay。
> 核心公式：**OPEX = 写入后六个子项生效值之和 + 该月已有 Miscellaneous（持久化列）值**

---

---

## 测试用例

### 一、OPEX 计算公式与生效值判定（Actuals 路径）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-004 | 新月份导入全部六子项（公式基础验证） | 2026-07 为新月份无历史数据；导入 S&M Exp=100、S&M Pay=80、R&D Exp=120、R&D Pay=90、G&A Exp=60、G&A Pay=50 | 执行导入写入 | OPEX = (100+80+120+90+60+50) + 0 = **500**（misc 无历史取 0），与子项一起写入 |
| TC-005 | 新月份仅导入部分子项缺失视为 0 | 2026-07 为新月份无历史数据；仅导入 S&M Exp=100、R&D Exp=120 | 执行导入写入 | 未导入的四子项视为 0；OPEX = (100+0+120+0+0+0) + 0 = **220** |
| TC-006 | 已有月份无冲突未导入子项保留 DB 值 | 2026-06 已有数据：六子项 S&M Exp=100、S&M Pay=80、R&D Exp=120、R&D Pay=90、G&A Exp=60、G&A Pay=50，misc 持久化列=30；本次仅导入此前为空的项不存在冲突，导入 R&D Pay=95（原 90，用户确认更新无冲突），其余未导入 | 执行导入写入 | R&D Pay 生效=95，其余保留 DB 值；OPEX = (100+80+120+95+60+50) + 30 = **535** |
| TC-007 | 已有月份冲突用户选择覆盖 | 2026-06 已有 R&D Exp=120、misc 持久化列=30，其余子项 S&M Exp=100、S&M Pay=80、R&D Pay=90、G&A Exp=60、G&A Pay=50；导入 R&D Exp=200 与现值冲突 | 在冲突解决中选择"覆盖" | R&D Exp 生效=200（覆盖值）；OPEX = (100+80+200+90+60+50) + 30 = **610** |
| TC-008 | 已有月份冲突用户选择保留原值 | 同 TC-007，导入 R&D Exp=200 与现值 120 冲突 | 在冲突解决中选择"保留原值" | R&D Exp 生效=120（DB 值）；OPEX = (100+80+120+90+60+50) + 30 = **530** |
| TC-009 | 混合冲突逐项生效值判定 | 2026-06 已有六子项 S&M Exp=100、S&M Pay=80、R&D Exp=120、R&D Pay=90、G&A Exp=60、G&A Pay=50，misc=30；导入 S&M Exp=150（选覆盖）、R&D Exp=200（选保留）、G&A Pay 未导入 | 分别按选择解决冲突后执行写入 | 生效值：S&M Exp=150、R&D Exp=120、其余保留；OPEX = (150+80+120+90+60+50) + 30 = **580** |
| TC-010 | 公式含 Miscellaneous 完整验证 | 2026-06 已有 misc 持久化列=30；导入六子项之和为 500 | 执行导入写入 | OPEX = 500 + 30 = **530**，体现 Miscellaneous 计入公式 |


### 二、Committed Forecast 直存路径

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-017 | 直存路径不调冲突校验但仍计算 OPEX | Committed Forecast 导入，2026-06 已有数据；导入含 R&D Exp=200 与现值不同 | 执行直存导入 | 不调用冲突校验接口、直接保存；仍执行 OPEX 自动计算并写入正确总额 |
| TC-018 | 直存路径生效值=导入值未导入保留 DB | Committed Forecast，2026-06 已有六子项 S&M Exp=100、S&M Pay=80、R&D Exp=120、R&D Pay=90、G&A Exp=60、G&A Pay=50，misc=30；导入 S&M Exp=150、R&D Exp=200，其余未导入 | 执行直存导入 | 生效值：S&M Exp=150、R&D Exp=200，其余保留 DB；OPEX = (150+80+200+90+60+50) + 30 = **660** |
| TC-019 | 直存路径新月份缺失子项=0 | Committed Forecast，2026-10 新月份无历史；导入 S&M Exp=100、R&D Exp=120 | 执行直存导入 | 缺失子项=0、misc=0；OPEX = (100+0+120+0+0+0) + 0 = **220** |
| TC-020 | 直存路径含 Miscellaneous 完整公式验证 | Committed Forecast，2026-06 misc 持久化列=40；导入六子项之和=500 | 执行直存导入 | OPEX = 500 + 40 = **540** |
| TC-021 | 直存路径不含子项不重新计算 | Committed Forecast 导入不含任何六子项 | 执行直存导入 | 不重新计算 OPEX，按原流程直存，OPEX 字段不被修改 |


---
