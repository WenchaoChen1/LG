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

Financial Entry为数据混合表，多数情况下会包含不同的数据类型，保证数据衔接，便于用户查看。

- closed month及之前月数据为真实数据。closed month之后数据为N/A的月份用预测数据填充，有committed forecast数据则优先使用Committed forecast,没有则使用system generated forecast数据（逐月判断）。（自动公司，closed month 后的月份会存在有拉取的数据的情况，所以不能简单定义为closed month后的月份用预测数据填充，必须是closed month之后的NA月才能用预测数据填充。实际数据为黑色字体，committed forecast数据为紫色字体，system generated forecast数据为紫色字体且带有小图标。

 - closed month定义： Financial Statements Settings中为Manual的公司，closed month是Financia Entry表中最后一个有Actuals数据的月份； Financial Statements Settings中为Automatic的公司，closed month以15号为界限，如果系统服务器时间过了15号，就是上个月（前提是Financial Entry表中上个月有Actuals数据，若没有就继续往历史月份找，找到有Actuals数据的月份位置）, 如果系统服务器时间没过15号，就是上上个月（前提是Financial Entry表中上个月有Actuals数据，若没有就继续往历史月份找，找到有Actuals数据的月份位置）。

**数据新增与编辑**

根据上述内容，Financial Entry为数据混合表。下面是Financial Entry 编辑逻辑规范
- 编辑入口与权限控制
  - 交互形式：Edit 按钮采用下拉设计，包含 Edit Financial Actuals 和 Edit Committed Forecast。
  - 显隐逻辑：系统根据当前视图（年度/季度）内是否存在可编辑的数据类型，动态显示或隐藏对应选项。
  - 置灰逻辑：若当前视图下两类数据均不可编辑（例如：QBO公司Actuals不可编辑，且仅有系统预测），则 Edit 总入口置灰。
  - 视觉规范：进入编辑模式后，所有可编辑单元格的数值均以黑色字体显示，且不显示任何辅助图标。
- Edit Financial Actuals（只有手动公司才有这个选项）
  - 时间范围限制：仅限当前日历月（不含）之前的月份可编辑；日历月之后的月份锁定置灰。
  - 数据保存机制（√ 逻辑）：
      - 缓存触发：手动修改数据后“√”图标激活。用户必须手动点击“√”，数据方可进入缓存并显示为“Changes Saved”。
      - 提交确认：点击 Submit 时，若存在激活但未点击的“√”，系统将弹出确认窗。未存入缓存（未点√）的数据将不会被保存。
  - 预测回填月的特殊逻辑：
    - 状态展示：若 Actuals 月份被预测数据（承诺/系统/混合预测）填充，编辑时保留该预测值作为底数，但不显示“比例分摊”或“Quick Fill”标签。
    - 数据转化：编辑并确认（点√并提交）预测回填月的数据后，该数据将转换为 Actuals 属性并持久化保存。
    - 独立性：手动编辑预测回填月仅对当月生效，不会对其他月份产生联动影响（无波浪影响）。
- Edit Committed Forecast（承诺预测编辑模式）
  - 可编辑范围：
    - 手动公司 ：当前日历月及之后的 Committed Forecast 月份可编辑，其余置灰。
    - 自动公司 ：当前日历月之后的 Committed Forecast 月份可编辑，其余置灰。
  - 版本控制与呈现：
  - 保存逻辑：用户编辑单元格并完成“点击√ + 点击 Submit”的操作后，系统将生成一个全新的 Committed Forecast 版本。该版本由当前编辑月的最新数据与该年度上一版本中其余月份的数据合并而成。若上一版本中其他月份没有数据，则在合并后的新版本中，这些月份将记录为 N/A。
  - 视觉反馈：提交成功后，该数据在 View 模式下显示为紫色字体。

**Cash的一键功能**

- 功能UI截图
<img width="714" height="112" alt="image" src="https://github.com/user-attachments/assets/55605c44-61c6-413a-b864-46d7e7e709d1" />

- 应用点
1. 应用数据类型：
   - FE - Edit Actuals: 只要预测数据（承诺预测或系统预测）尚未被正式转化为 Actuals 数据，Cash 的两个批量操作按钮均可对这些预测回填月生效（按业务逻辑执行），用于快速调整预测值。
   - FE - Edit committed forecast: 存在已有的承诺预测数据（Committed Forecast）时，批量操作按钮才可对相应月份生效。
   - Committed Forecast - Edit: 只要承诺预测表或当前编辑缓存中存在数据，批量操作按钮就可对对应月份生效（按业务逻辑执行）。比如某年度（如 2027 年）初始数据全为空，批量操作按钮初始虽可见但是点击不生效。一旦用户为某月（如 1 月）手动输入数据并点击“√”存入缓存，再次点击批量操作按钮，比如Set to Zero,将立即对该月按逻辑执行。
   - Committed Forecast - Accept as Committed Forecast时
   - System Generated Forecast - Accept as Committed Forecast时

2. 应用方式：
- Set to Zero批量操作按钮，可将当前年度或当前季度预测范围内所有非N/A数据的月份的Cash数值统一重置为 0。
- 使用Quick-Fill批量操作按钮，依据公式`Cash_{t+1} = Cash_t + Net\_Income_{t+1} − \Delta AR_{t+1} − \Delta Other\_Assets_{t+1} + \Delta AP_{t+1} ` ，按时间顺序（例如，从 1 月至 12 月）对当前年度或当前季度预测中Cash数值为 0 或带有“快速填充”标记的单元格进行自动计算与填充。如果月份 t 的数值为 N/A（空值），则公式中的 Cash_t 和各项增量（delta）将等于 0。
   - 若2025年12月为实际数据，2026年1月份为预测数据，如果在2026年edit financial actuals模式下，点击Set to Zero后，再点击Quick Fill, 计算2026年1月份cash的时候，Cash_t用2025年12月份的实际数据。所以逻辑为：要把目标月保存为哪种数据，t月就用哪种数据，没有用N/A。
- 注意：该功能可能会涉及汇率换算，因为涉及到不同月且P&L和B&S取的不同的汇率，他们的原始数据计算后再根据计算月的汇率转换可能会不等于页面显示值直接计算得到的数据
- 波浪式影响：在年度或季度视图中，点击 Quick Fill 将触发波浪式级联影响。该影响自首个可填充月份开始，向后延伸直至遭遇首个不可填充月份为止。若后续仍存在可填充区间，则开启下一轮波浪，依此类推。在跨年/跨季度中，若波浪影响可以推至次年/次季度，则一直影响，至不可填充月结束，不会再有下一个波浪。
- 手动编辑触发的波浪联动逻辑 (Ripple Effect via Manual Edit)：在 FE - Edit Committed Forecast、Committed Forecast - Edit 以及 Accept as Committed Forecast（系统生成转承诺）等模式下，波浪影响的触发逻辑如下：
  - 触发前提：
    - 用户手动修改了某月份的数据。
    - 被修改的数据属于 Cash Quick Fill 计算公式的变量。
    - 该月份的紧后月份已被标记为 Quick Fill 状态。
  - 级联机制：
    - 联动开启：一旦满足上述条件，手动修改产生的影响将如同“波浪”一般，自动推送到后续连续标记为 Quick Fill 的月份中，并重新计算它们的数据。
    - 中断即止：这种联动具有“一次性”特征。波浪会沿着 Quick Fill 链条持续传递，但一旦遭遇第一个非 Quick Fill 月份（联动中断），该波浪即刻终止。
    - 无后续波浪：即使在该中断点之后的更远月份仍存在 Quick Fill 标记，手动编辑引发的波浪也不会跳过中断点去影响那些月份。
    - 跨期规则：若此联动影响已延伸至次年或次季度，波浪将继续跨期传递，直至遇到首个不可填充月份或非 Quick Fill 月份为止。

3.使用批量操作时，受影响月份通常会自动标记为“Changes Saved”。但为尊重用户的操作意图，系统会根据 “√”按钮是否已被激活（即是否有未提交的手动编辑） 调整逻辑：
- 若该月“√”未被激活（无手动编辑）： 系统将自动激活“√”符号并缓存数据，状态更新为“Changes Saved”。
- 若该月“√”已被激活（已有手动编辑）： 系统仅对批量操作涉及的特定指标进行后台缓存，该月状态不自动跳转为“Changes Saved”，且“√”保持未点击状态。此时若用户手动勾选“√”并提交，则保存手输数据；若直接提交，则手动编辑失效，系统最终保存批量操作生成的缓存数据。
“一键归零”强制逻辑：一旦触发，系统将强制重置当期所有非 N/A 月份的预测数据为 0，并清空所有 [快速填充] 标签，无论该月份此前处于何种状态。

4.边缘情况与终止规则：
- 间隙处理（N/A）：如果某个月份不含数据（显示为 N/A），系统会将“Cash”及所有“增量”（Deltas）均视为 0。计算过程不会中断，而是继续推进至下一个包含数据的月份。
- 尾部终止：若预测期内后续所有月份均显示为 N/A，则公式将停止应用。
- 逻辑断点（[Manual] 标记中断）：
  如果某一月份被标记为 [Manual]（手动录入）状态，则级联更新链条将在此处中断。
  情景示例：若手动修改了五月份的数据，且被修改的数据属于 Cash Quick Fill 计算公式的变量，六月份（处于“快速填充”状态）的数据将随之更新；但若七月份被标记为 [Manual] 状态，则七月份及其之后的所有月份数据将不受五月份数据更新的影响，保持不变。
- 起始点设定：一旦某一月份点击了“√”按钮进了缓存，该月份的期末现金余额将自动成为下一月份计算时的强制性期初现金余额。

5.预测版本生成机制：一旦某年度内任意月份的Cash数值或状态标签（“手动输入” vs. “快速填充”）发生任何变动，在正式提交时，系统必须触发生成一个新的“已确认预测”版本。

**Distribute operating expenses using historical percentages功能**
<img width="1126" height="215" alt="image" src="https://github.com/user-attachments/assets/10db30d0-2c24-4ede-a2b8-30b4b295238d" />

1. 应用数据类型：
   - FE - Edit Actuals: 只要预测数据（承诺预测或系统预测）尚未被正式转化为 Actuals 数据，Distribute operating expenses using historical percentages功能均可对这些预测回填月生效（按业务逻辑执行），用于快速调整预测值。
   - FE - Edit committed forecast: 存在已有的承诺预测数据（Committed Forecast）时，Distribute operating expenses using historical percentages功能才可对相应月份生效。
   - Committed Forecast - Edit: 只要承诺预测表或当前编辑缓存中存在数据，Distribute operating expenses using historical percentages功能就可对对应月份生效（按业务逻辑执行）。比如某年度（如 2027 年）初始数据全为空，Distribute operating expenses using historical percentages功能初始虽可见但是勾选后数据并没有任何变化。一旦用户为某月（如 1 月）手动输入数据并点击“√”存入缓存，再次成功勾选，将立即对该月按逻辑执行。
   - Committed Forecast - Accept as Committed Forecast时
   - System Generated Forecast - Accept as Committed Forecast时

2.勾选该选项后，用户可以输入运营费用的总额，系统根据比例自动将总额分配至S&M Expenses，S&M Payroll，R&D Expenses，R&D Payroll，G&A Expenses，G&A Payroll，且这些月份的这6个指标变为实时计算的指标，不再存入数据库，在edit模式，这些指标置灰显示，不可手动编辑。分配比例计算规则如下：

- 系统以closed month为基准（向前追溯），计算此前连续 6 个月的算术平均值作为分配依据。 0 被视为有效输入，'N/A' 输入则视为无效。
  - 峰值阈值（Spike Threshold）：从Closed Month开始向前追溯，确定最近的连续六个月份；计算这六个月份间“月度环比绝对变化值”的算术平均数，并将峰值阈值（spikeThreshold）设定为该平均数的 2 倍（即 2 × avgAbsMoM）。若超过峰值，则剔除该值，使用平均数代替。
  - 如果数据不足，系统将优先使用同行数据，其次使用LG平台基准数据，若两者皆无，则进行平均分配。

- 勾选该选项后，受影响月份通常会自动标记为“Changes Saved”。但为尊重用户的操作意图，系统会根据 月份的“√”是否已被激活（即是否有未提交的手动编辑） 调整逻辑：
- 若该月“√”未被激活（无手动编辑）： 系统将自动激活“√”符号并缓存数据，状态更新为“Changes Saved”。
- 若该月“√”已被激活（已有手动编辑）： 系统仅对Distribute operating expenses using historical percentages涉及的特定指标进行后台缓存，该月状态不自动跳转为“Changes Saved”，且“√”保持未点击状态。此时若用户手动勾选“√”并提交，则保存手输数据；若直接提交，则手动编辑失效，系统最终保存Distribute operating expenses using historical percentages操作生成的缓存数据。

- 取消选中时：

  - 子项目的数据状态将从“实时计算值”（Computed Live）恢复为“静态值”（Static Values），并保留最后一次计算所得的数值。

  - 手动覆盖（Manual Override）：相关字段将重新启用，允许用户进行手动编辑。

  - 数据持久化：取消选中时，数值将首先被保存至缓存中；当用户点击“提交/接受”（Submit/Accept）按钮时，数值将按序正式保存至数据库中。

  - 预测版本生成机制：一旦某年度内committed forecast任意月份的Distribute operating expenses using historical percentages状态标签发生任何变动，在正式提交时，系统必须触发生成一个新的“committed forecast”版本。

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
