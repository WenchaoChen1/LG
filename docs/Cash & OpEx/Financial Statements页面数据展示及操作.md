# Financial Statements页面数据展示及操作

## 1. Financial Statements页面包含三个表,可从右上角下拉框选择

- Financial Entry(默认表）

- Committed Forecast

- System Generated Forecast

## 2.逐表解释：

### 2.1 Financial Entry(默认表，混合表)

**视图**

- 全屏状态下，若company settings中设置的视图为年视图，展示当前年12月数据；若设置的季度视图，则展示当前季度3个月的数据

- 非全屏状态下，若company settings中设置的视图为年视图，展示当前年最后几个月的数据，根据屏宽，能展示几个展示几个；若设置的季度视图，如屏宽仅可展示两个月，优先展示当前月和后一月，手机屏宽时仅显示当前月。

**数据展示**

Financial Entry为数据混合表，多数情况下会包含不同的数据类型，保证整年的数据衔接，以供用户审阅参考

- closed month及之前月数据为真实数据。若无真实数据，则无真实数据的月份使用预测数据填充，若有committed forecast数据则使用committed forecast，若无则使用system generated forecast数据。实际数据为黑色字体，committed forecast数据为紫色字体，system generated forecast数据为紫色字体且带有小图标。

 - closed month定义： Financial Statements Settings中为Manual的公司，closed month是Financia Entry表中最后一个有Actuals数据的月份； Financial Statements Settings中为Automatic的公司，closed month以15号为界限，如果系统服务器时间过了15号，就是上个月（前提是Financial Entry表中上个月有Actuals数据，若没有就继续往历史月份找，找到有Actuals数据的月份位置）, 如果系统服务器时间没过15号，就是上上个月（前提是Financial Entry表中上个月有Actuals数据，若没有就继续往历史月份找，找到有Actuals数据的月份位置）。

- closed month之后的数据为预测数据，有committed forecast数据则优先使用Committed forecast,没有则使用system generated forecast数据

**数据新增与编辑**

Financial Entry为数据混合表，多数情况下会包含不同的数据类型，所以Edit功能按钮是下拉按钮，包含当前表中可编辑的数据类型，如Actuals，Committed Forecast

- 点击Edit下拉按钮，选择Actual，进入编辑状态，仅closed month及之前月可编辑，closed month之后月置灰，不可编辑。若closed month被预测数据填充，则编辑状态下带着预测数据，呈现可编辑状态，而不是置空，用户若点击Cancel退出，预测数据填充的月份依旧显示预测数据；用户若编辑了任意一个可编辑单元格并点击对钩保存后点击了提交，则该月数据变为Actuals黑色字体

- 若表格含有Committed forecast数据，点击Edit下拉按钮，选择Committed forecast，进入编辑状态，仅closed month之后月可编辑，closed month及之前月置灰，不可编辑。用户若编辑了任意一个可编辑单元格并点击对钩保存后点击了提交，则该数据被保存为该月的最新版本Committed Forecast 数据，字体颜色为紫色。

**Cash quick-fill功能说明**：

- 仅对Committed Forecast数据可用（Financial Entry页面的committed forecast数据或committed forecast页面数据）。使用“设为零”（Set to Zero）批量操作按钮，将当前年度或当前季度的预测期内所有包含数据的月份，其对应的现金数值统一重置为 0。使用“快速填充”（Quick-Fill）批量操作按钮，对当前年度或当前季度的预测期内符合以下条件的现金单元格进行计算填充：

 - 1. 当前数值为 0 的单元格（无论其此前状态是 [手动输入] 还是 [快速填充]），

 - 2. 已带有“快速填充”标记的单元格。
- 系统将依据公式 `Cash_{t+1} = Cash_t + Net_Income_{t+1} − ΔAR_{t+1} − ΔOther_Assets_{t+1} + ΔAP_{t+1}`，按时间顺序（例如，从 1 月至 12 月）逐月进行计算填充。如果月份 t 的数据为 NA（不可用），则公式中的 Cash_t（现金余额）及各项增量（deltas）将均等于 0。
- 使用批量操作按钮时，受影响月份的状态将自动设置为“已勾选”（即已缓存）。系统会根据用户是否曾手动点击“√”符号，调整其行为逻辑，以此尊重用户的操作意图：

- 两种情景：

  - 若未进行过手动“√”操作：

 系统将自动为所有相关月份点击“√”符号。

 相应的数据将被缓存。
 
   - 若已进行过手动“√”操作：

 系统将仅缓存当前批量操作所涉及的特定指标数据。

 该月份的其他所有指标数据将保持不变。

 “√”符号的状态将保持为未点击。

 在系统后台，这些月份将被自动标记为“手动录入”或“快速填充”状态。

- 系统通过一种“瀑布流式”的重算机制，确保整个时间轴上的数据逻辑保持一致。

正向触发机制：对任一月份所做的任何更改（无论是通过手动编辑还是批量操作），都将触发其后所有被标记为“快速填充”状态的月份进行逐一重新计算。

- 逻辑断点（[Manual] 标记中断）：

如果某一月份被标记为 [Manual]（手动录入）状态，则级联更新链条将在此处中断。

情景示例：若修改了五月份的数据，六月份（处于“快速填充”状态）的数据将随之更新；但若七月份被标记为 [Manual] 状态，则七月份及其之后的所有月份数据将不受五月份数据更新的影响，保持不变。

- 起始点设定：一旦某一月份被标记为“已勾选”（Checked）状态，该月份的期末现金余额将自动成为下一月份计算时的强制性期初现金余额。

**Distribute operating expenses using historical percentages功能**

- 仅对Committed Forecast数据可用（Financial Entry页面的committed forecast数据或committed forecast页面数据）。勾选该选项后，用户可以输入运营费用的总额，系统根据比例自动将总额分配至S&M Expenses，S&M Payroll，Sales Efficiency Ratio，R&D Expenses，R&D Payroll，G&A Expenses，G&A Payroll。分配比例计算规则如下：

- 系统以closed month为基准（向前追溯），计算此前连续 6 个月的算术平均值作为分配依据。 0 被视为有效输入，'N/A' 输入则视为无效。

峰值阈值（Spike Threshold）：从Closed Month开始向前追溯，确定最近的连续六个月份；计算这六个月份间“月度环比绝对变化值”的算术平均数，并将峰值阈值（spikeThreshold）设定为该平均数的 2 倍（即 2 × avgAbsMoM）。

如果数据不足，系统将优先使用同行数据，其次使用投资组合基准数据，若两者皆无，则进行平均分配。

- 勾选该选项后，系统会自动点击“√”以将数据暂存至缓存中；该数据分配功能会尊重用户的意图，根据用户是否已手动点击过“√”来调整其行为逻辑：

- 两种情景：

  - 若未进行手动“√”操作：

 系统将自动为所有相关月份点击“√”。

 相应的数据将被缓存。

  - 若已进行手动“√”操作：

 系统将仅缓存当前批量处理的特定指标数据。

 该月份内的所有其他指标数据将保持不变（不受影响）。

 “√”状态保持不变（即未被自动点击）。

对于介于“closed month”与“当前日历月份”之间的月份（这些月份的数据由“已确认预测”[Committed Forecast] 进行回填），分配操作将以预测的运营费用（OpEx）为基准；分配完成后，相关数据将被缓存并视为“财务实际值”（Financial Actuals）。

- 取消选中时：

子项目的数据状态将从“实时计算值”（Computed Live）恢复为“静态值”（Static Values），并保留最后一次计算所得的数值。

手动覆盖（Manual Override）：相关字段将重新启用，允许用户进行手动编辑。

数据持久化：取消选中时，数值将首先被保存至缓存中；当用户点击“提交/接受”（Submit/Accept）按钮时，数值将按序正式保存至数据库中。

版本控制：若取消勾选该切换开关并执行提交操作，系统将触发生成一个新的“已确认预测”版本。

**数据对比**

- Compare下拉选项包括Committed Forecast, System Generated Forecast, Confidence Intervals。选中的数据类型会展示在Actuals数据下，Committed Forecast为紫色字体, System Generated Forecast为紫色字体加图标, Confidence Intervals在System Generated Forecast下方显示System Generated Forecast 数据25%，50%，75%百分位的数据。

### 2.2 Committed Forecast表

**视图**

- 全屏状态下，若company settings中设置的视图为年视图，展示当前年12月数据；若设置的季度视图，则展示当前季度3个月的数据

- 非全屏状态下，若company settings中设置的视图为年视图，展示当前年最后几个月的数据，根据屏宽，能展示几个展示几个；若设置的季度视图，如屏宽仅可展示两个月，优先展示当前月和后一月，手机屏宽时仅显示当前月。

**数据展示**

Committed Forecast 表默认展示的是最新版本的当前年/季度的承诺预测数据，数据来源有两种，一是接受system generated forecast为Committed forecast,二是手动添加的承诺预测数据。右上角有View History按钮，点击进入Committed Forecast History列表，可以看到committed forecast所有版本历史记录及当前版本信息

**数据新增与编辑**

Committed forecast 表可编辑，点击Edit按钮可以进入编辑模式，编辑且保存完后，生成新版本的committed forecast数据。

**备注**

Cash quick-fill与Distribute operating expenses using historical percentages功能同2.1中功能说明

### 2.3 System Generated Forecast表

**视图**

- 全屏状态下，若company settings中设置的视图为年视图，展示当前年12月数据；若设置的季度视图，则展示当前季度3个月的数据

- 非全屏状态下，若company settings中设置的视图为年视图，展示当前年最后几个月的数据，根据屏宽，能展示几个展示几个；若设置的季度视图，如屏宽仅可展示两个月，优先展示当前月和后一月，手机屏宽时仅显示当前月。

**数据展示**

System Generated Forecast 表默认展示的是最新版本的当前年/季度的系统生成预测数据，此数据可被接受为承诺预测，点击Accept进入编辑模式，若需要修改则进行修改，如无需修改则可提交数据，成为承诺预测。

**数据新增与编辑**

该表不可直接进行新增与编辑
