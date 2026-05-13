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

- closed month之后数据为N/A的月份用预测数据填充，有committed forecast数据则优先使用Committed forecast,没有则使用system generated forecast数据。（自动公司，closed month 后的月份会存在有拉取的数据的情况，所以不能用预测数据填充）

**数据新增与编辑**

Financial Entry为数据混合表，多数情况下会包含不同的数据类型，所以Edit功能按钮是下拉按钮，包含当前视图下（年度12个月/季度3个月）可编辑的数据类型，如Actuals，Committed Forecast，若无可编辑数据，则Edit按钮置灰，可编辑的数据在编辑状态下均为黑色字体

- 点击Edit下拉按钮，选择Actual，进入编辑状态，仅closed month及之前月可编辑，closed month之后月置灰，不可编辑。若月份被预测数据填充，则编辑状态下带着预测数据，呈现可编辑状态，而不是置空，用户若点击Cancel退出，预测数据填充的月份依旧显示预测数据；用户若编辑了任意一个可编辑单元格并点击对钩保存后点击了提交，则该月数据变为Actuals黑色字体--且该月份之前若存在NA月，那这种NA月份在view模式下不会回显预测。（若7 8 9月份均为committed forecast月份，9月份填了Actual数据，7 8 月份置为N/A,而非继续用committed forecast填充）

- 若表格含有Committed forecast数据，点击Edit下拉按钮，选择Committed forecast，进入编辑状态，仅closed month之后用committed forecast数据填充的月可编辑，closed month及之前月置灰，不可编辑。用户若编辑了任意一个可编辑单元格并点击对钩保存后点击了提交，则该数据被保存为该月的最新版本Committed Forecast 数据，字体颜色为紫色。

- 当前月与closed month之间N/A月份用system generated forecast填充

**Cash的一键功能**

- 功能UI截图
<img width="714" height="112" alt="image" src="https://github.com/user-attachments/assets/55605c44-61c6-413a-b864-46d7e7e709d1" />

- 应用点
1. 应用数据类型：
   - FE - Edit Actuals: 存在承诺预测或系统预测；
   - FE - Edit committed forecast: 存在承诺预测
   - Committed Forecast - Edit: 存在承诺预测
   - Committed Forecast - Accept as Committed Forecast时
   - System Generated Forecast - Accept as Committed Forecast时

2. 应用方式：
- Set to Zero批量操作按钮，可将当前年度或当前季度预测范围内所有非N/A数据的月份的Cash数值统一重置为 0。
- 使用Quick-Fill批量操作按钮，依据公式`Cash_{t+1} = Cash_t + Net\_Income_{t+1} − \Delta AR_{t+1} − \Delta Other\_Assets_{t+1} + \Delta AP_{t+1} ` ，按时间顺序（例如，从 1 月至 12 月）对当前年度或当前季度预测中Cash数值为 0 或带有“快速填充”标记的单元格进行自动 计算与填充。如果月份 t 的数值为 N/A（空值），则公式中的 Cash_t 和各项增量（delta）将等于 0。
   - 若2025年12月为实际数据，2026年1月份为预测数据，Cash_t用2025年12月份的实际数据。编辑后为哪种数据，t月就用哪种数据，没有用N/A。
- 注意：该功能可能会涉及汇率换算，因为P&L和B&S取的不同的汇率，他们的原始数据计算后再根据计算月的汇率转换可能会不等于页面显示值直接计算得到的数据
- 波浪式影响：在本年度/季度视图中，点击quick fill,从第一个可填充月开始波浪式影响后月，到第一个不可填充月结束；从第二个可填充月开始波浪式影响后月，到第二个不可填充月结束，依此类推。在跨年/跨季度中，若波浪影响可以推至次年/次季度，则一直影响，至不可填充月结束，不会再有下一个波浪。

3.用批量操作按钮时，受影响月份的状态将自动设置为“已勾选”（即已缓存）。系统会根据用户是否曾手动点击“√”符号，调整其行为逻辑，以此尊重用户的操作意图：
- 两种情景：
  - 若无手动点击“√”的数据：
    系统将自动为所有相关月份点击“√”符号。
    相应的数据将被缓存。
  - 若有手动点击“√”的数据：
    系统将仅缓存当前批量操作所涉及的特定指标数据。
    该月份的其他所有指标数据将保持不变。
    “√”按钮的状态将保持为未点击，提交时若用户手动点击了“√”按钮，则手动输入数据将被保存；提交时若用户未点击“√”按钮，则自动填充数据将被保存。
- 当批量操作按钮“一键归零”被触发时，系统将强制对当前年度或季度内所有非N/A月份进行重新计算或重置，无论这些月份此前是否已被标记为 [手动] 或 [快速填充] 状态。标签也将全部清空重置

4.边缘情况与终止规则：
- 间隙处理（N/A）：如果某个月份不含数据（显示为 N/A），系统会将“Cash”及所有“增量”（Deltas）均视为 0。计算过程不会中断，而是继续推进至下一个包含数据的月份。
- 尾部终止：若预测期内后续所有月份均显示为 N/A，则公式将停止应用。
- 逻辑断点（[Manual] 标记中断）：
  如果某一月份被标记为 [Manual]（手动录入）状态，则级联更新链条将在此处中断。
  情景示例：若修改了五月份的数据，六月份（处于“快速填充”状态）的数据将随之更新；但若七月份被标记为 [Manual] 状态，则七月份及其之后的所有月份数据将不受五月份数据更新的影响，保持不变。
- 起始点设定：一旦某一月份点击了“√”按钮进了缓存，该月份的期末现金余额将自动成为下一月份计算时的强制性期初现金余额。
  
5.版本生成机制：一旦现金数值或状态标签（“手动输入” vs. “快速填充”）发生任何变动，在正式提交时，系统必须触发生成一个新的“已确认预测”版本。

6. 特殊情况：
- 存在两种预测， 且承诺预测本身已使用quick fill，这个标签会被携带过来。比如26-01是系统预测，26-02和03是承诺预测，整个26年没有actuals数据。那在这个编辑模式下，如果手动更改01月份cash并点击√存入缓存且提交，01月数据变为actuals，02和03月不受影响；但如果手动编辑02月cash，并点击√存入缓存，03月的cash会同步更新（因为tag为quick-fill），且底部按钮变为changes saved，提交之后2月和3月都变成actuals。
- 同比（YoY）联动机制：若当前年度 12 月份的cash数据发生变动，且次年 1 月份的设置状态为“[快速填充]”，系统必须自动触发重算流程，并为次年生成一个新的版本，以反映更新后的期初余额。

**Distribute operating expenses using historical percentages功能**

1. 应用数据类型：
   - FE - Edit Actuals: 存在承诺预测或系统预测；
   - FE - Edit committed forecast: 存在承诺预测
   - Committed Forecast - Edit: 存在承诺预测
   - Committed Forecast - Accept as Committed Forecast时
   - System Generated Forecast - Accept as Committed Forecast时
  
2.勾选该选项后，用户可以输入运营费用的总额，系统根据比例自动将总额分配至S&M Expenses，S&M Payroll，R&D Expenses，R&D Payroll，G&A Expenses，G&A Payroll。分配比例计算规则如下：

- 系统以closed month为基准（向前追溯），计算此前连续 6 个月的算术平均值作为分配依据。 0 被视为有效输入，'N/A' 输入则视为无效。

峰值阈值（Spike Threshold）：从Closed Month开始向前追溯，确定最近的连续六个月份；计算这六个月份间“月度环比绝对变化值”的算术平均数，并将峰值阈值（spikeThreshold）设定为该平均数的 2 倍（即 2 × avgAbsMoM）。若超过峰值，则剔除该值，使用平均数代替

如果数据不足，系统将优先使用同行数据，其次使用LG平台基准数据，若两者皆无，则进行平均分配。

- 勾选该选项后，系统会自动点击“√”以将数据暂存至缓存中；该数据分配功能会尊重用户的意图，根据用户是否已手动点击过“√”来调整其行为逻辑：

- 两种情景：
  - 若无手动“√”的数据：
    系统将自动为所有相关月份点击“√”。
    相应的数据将被缓存。
  - 若有手动“√”的数据：
    系统将仅缓存当前批量处理所涉及的特定指标。
    该月份的其他所有指标将保持不变（不受影响）。
    “√”状态保持不变（即未被自动点击）。
    
- 使用自动分配功能后，未进行手动编辑的月份正常填充正常自动进缓存，手动编辑过的月份数据静默缓存，若最后提交时，用户手动点击了“√”，则使用手动填入的数据,若未点击“√”，则使用一键填充的值。

- 对于介于“closed month”与“当前日历月份”之间的月份（这些月份的数据由“已确认预测”[Committed Forecast] 进行回填），分配操作将以预测的运营费用（OpEx）为基准；分配完成后，相关数据将被缓存并视为“财务实际值”（Financial Actuals）。

- 取消选中时：

  - 子项目的数据状态将从“实时计算值”（Computed Live）恢复为“静态值”（Static Values），并保留最后一次计算所得的数值。

  - 手动覆盖（Manual Override）：相关字段将重新启用，允许用户进行手动编辑。

  - 数据持久化：取消选中时，数值将首先被保存至缓存中；当用户点击“提交/接受”（Submit/Accept）按钮时，数值将按序正式保存至数据库中。

  - 版本控制：若取消勾选该切换开关并执行提交操作，系统将触发生成一个新的“已确认预测”版本。

**数据对比**

- Compare下拉选项包括Committed Forecast, System Generated Forecast, Confidence Intervals。选中的数据类型会展示在Actuals数据下，Committed Forecast为紫色字体, System Generated Forecast为紫色字体加图标, Confidence Intervals在System Generated Forecast下方显示System Generated Forecast 数据25%，50%，75%百分位的数据。

**数据更新影响页面**
- Actuals数据更新：
  - Benchmarking 页面（实时）
  - Company overview 页面(实时）
  - Portfolio list（每日定时）
  - Normalization Tracing（每日定时）
  - System generated forecast（实时）
  - Performance tab（实时）
  - Peer Group Management（实时，可能会影响）
  - Financial Metrics Tracing（实时）

- Committed forecast数据更新：
  - Benchmarking 页面（实时）
  - Normalization Tracing（每日定时）
  - Performance tab（实时）

- System generated forecast数据更新：
  -  Benchmarking 页面（实时）
  -  Financial Metrics Tracing（实时）

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
