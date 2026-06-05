# 测试用例：Financial Statements 页面数据展示及操作

- **需求来源**：https://github.com/WenchaoChen1/LG/blob/master/docs/Cash%20%26%20OpEx/Financial%20Statements%E9%A1%B5%E9%9D%A2%E6%95%B0%E6%8D%AE%E5%B1%95%E7%A4%BA%E5%8F%8A%E6%93%8D%E4%BD%9C.md
- **生成时间**：2026-06-05

---

## 需求清单

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R1 | 功能需求 | Financial Statements 页面包含三个表，右上角下拉框可选择：Financial Entry（默认）、Committed Forecast、System Generated Forecast |
| R2 | 业务规则 | 全屏 + 年视图 → 展示当前年 12 个月数据 |
| R3 | 业务规则 | 全屏 + 季度视图 → 展示当前季度 3 个月数据 |
| R4 | 业务规则 | 非全屏 + 年视图 → 按屏宽展示当前年最后几个月（能展示几个展示几个） |
| R5 | 业务规则 | 非全屏 + 季度视图 → 屏宽仅可展示两月时优先展示当前月+后一月；手机屏宽仅显示当前月 |
| R6 | 业务规则 | FE 手动公司预测回显：closed month 及之前为真实数据；之后 N/A 月份用预测填充，逐月判断（有 Committed Forecast 优先用之，否则用 System Generated Forecast） |
| R7 | 业务规则 | FE 自动公司预测回显：日历月之后的月份用预测数据填充 |
| R8 | UI 需求 | 字体颜色：实际数据黑色；Committed Forecast 紫色；System Generated Forecast 紫色且带小图标 |
| R9 | 业务规则 | closed month 定义（Manual 公司）：FE 表中最后一个有 Actuals 数据的月份 |
| R10 | 业务规则 | closed month 定义（Automatic 公司）：以服务器时间 15 号为界，过 15 号=上个月，没过 15 号=上上个月；前提是上个月有 Actuals，若无则往历史月份回溯到有 Actuals 的月份 |
| R11 | 功能需求 | Edit 按钮为下拉设计，包含 Edit Financial Actuals 与 Edit Committed Forecast |
| R12 | 业务规则 | 显隐逻辑：按当前视图内是否存在可编辑数据类型，动态显示/隐藏对应选项 |
| R13 | 业务规则 | 置灰逻辑：当前视图下两类数据均不可编辑（如 QBO 公司 Actuals 不可编辑且仅有系统预测）时，Edit 总入口置灰 |
| R14 | UI 需求 | 进入编辑模式后，所有可编辑单元格数值以黑色字体显示，且不显示任何辅助图标 |
| R15 | 业务规则 | Edit Financial Actuals 仅手动公司才有此选项 |
| R16 | 业务规则 | Edit Financial Actuals 时间范围：仅当前日历月（不含）之前可编辑，日历月之后锁定置灰 |
| R17 | 业务规则 | √ 保存机制：修改后 √ 激活，必须手动点击 √ 数据才进缓存并显示 "Changes Saved" |
| R18 | 业务规则 | 提交确认：Submit 时若存在激活但未点击的 √，弹确认窗；未存入缓存（未点 √）的数据不会保存 |
| R19 | 业务规则 | 预测回填月编辑：保留预测值作底数，但不显示"比例分摊"/"Quick Fill"标签 |
| R20 | 业务规则 | 预测回填月数据转化：编辑并确认（点 √ 并提交）后，数据转为 Actuals 属性并持久化 |
| R21 | 业务规则 | 预测回填月独立性：手动编辑仅对当月生效，不产生波浪联动 |
| R22 | 业务规则 | Edit Committed Forecast 可编辑范围（手动公司）：当前日历月及之后的 CF 月份可编辑，其余置灰 |
| R23 | 业务规则 | Edit Committed Forecast 可编辑范围（自动公司）：当前日历月之后的 CF 月份可编辑，其余置灰 |
| R24 | 业务规则 | CF 保存逻辑：点 √+Submit 生成全新 CF 版本，由当前编辑月最新数据与上一版本其余月份合并；上一版本无数据的月份在新版本记为 N/A |
| R25 | UI 需求 | CF 提交成功后，数据在 View 模式显示为紫色字体 |
| R26 | 业务规则 | Cash 批量按钮应用数据类型及生效条件（FE-Edit Actuals / FE-Edit Committed Forecast / Committed Forecast-Edit / SGF/CF Accept as Committed Forecast） |
| R27 | 业务规则 | Committed Forecast-Edit：空年度初始按钮可见但点击不生效；某月输入数据并点 √ 入缓存后，再点按钮立即对该月生效 |
| R28 | 功能需求 | Set to Zero：将当前年度/季度预测范围内所有非 N/A 月份的 Cash 统一重置为 0 |
| R29 | 业务规则 | 一键归零强制逻辑：强制重置当期所有非 N/A 月份预测数据为 0，并清空所有 Quick Fill 标签，无论此前处于何种状态 |
| R30 | 计算公式 | Quick Fill 公式：Cash_{t+1} = Cash_t + Net_Income_{t+1} − ΔAR_{t+1} − ΔOther_Assets_{t+1} + ΔAP_{t+1} + ΔLong-term debt_{t+1}；按时间顺序对 Cash=0 或带 Quick Fill 标记的单元格计算填充 |
| R31 | 业务规则 | Quick Fill：月份 t 为 N/A（空值）时，公式中 Cash_t 及各 delta 均取 0 |
| R32 | 业务规则 | t 月数据类型选取：目标月要保存为哪种数据，t 月就用哪种数据（如目标为 Actuals 则 t 月用 Actuals 实际值），不会用 N/A |
| R33 | 业务规则 | 汇率换算：可能涉及汇率（P&L 与 B/S 取不同汇率），原始数据计算后再按计算月汇率转换，可能不等于页面显示值直接计算的结果 |
| R34 | 业务规则 | 非可填充月弹框："Manually Modified Months Detected"，列出手动录入 Cash 的月份，提示将保留这些月、仅计算 set to zero 或已标记 Quick Fill 的月份，含 Cancel / Proceed with Quick Fill 两按钮 |
| R35 | 业务规则 | 批量 Quick Fill 波浪：自首个可填充月开始向后延伸至首个不可填充月；后续仍有可填充区间则开启下一轮波浪；跨年/跨季可推至次年/次季则持续影响至不可填充月结束，不再有下一波浪 |
| R36 | 业务规则 | 手动编辑触发波浪：前提为手动修改了属于 Cash 公式变量的数据，且其紧后月份已标记 Quick Fill；满足则自动推送到后续连续 Quick Fill 月份重算 |
| R37 | 业务规则 | 手动编辑波浪中断即止：遇第一个非 Quick Fill 月份终止；即使中断点之后仍有 Quick Fill 标记也不跳过去影响 |
| R38 | 业务规则 | 手动编辑波浪跨期：若已延伸至次年/次季，则继续跨期传递，直至首个不可填充月或非 Quick Fill 月 |
| R39 | 业务规则 | 点 √ 触发波浪后续 √ 状态处理：后续 Quick Fill 月无激活 √ → 页面更新；√ 已激活且 cash 未被手动编辑 → cash 仅后台缓存、√ 不变 Changes Saved、页面 cash 更新、其他手动编辑维持未提交；√ 已激活且 cash 已被手动编辑 → cash 仅后台缓存、√ 不变、页面 cash 不更新 |
| R40 | 业务规则 | 批量操作 √ 未激活月：自动激活 √ 并缓存数据，状态更新为 "Changes Saved" |
| R41 | 业务规则 | 批量操作 √ 已激活月：仅后台缓存涉及指标，不自动跳 Changes Saved、√ 保持未点；用户手动勾 √ 并提交则保存手输数据，直接提交则手动编辑失效、保存批量缓存数据 |
| R42 | 业务规则 | √ 激活原因为 cash 本身/含 cash（与 Quick Fill 目标直接冲突）：页面维持手动 cash 值，Quick Fill 结果仅入后台缓存不回显 |
| R43 | 业务规则 | √ 激活原因为 cash 以外指标（无直接冲突）：Quick Fill 的 cash 值回显页面、后台同步缓存，√ 维持激活不自动变 Changes Saved |
| R44 | 业务规则 | 间隙处理（N/A）：Cash 及所有 Deltas 视为 0，计算不中断，继续推进至下一个含数据月份 |
| R45 | 业务规则 | 尾部终止：预测期内后续所有月份均为 N/A，则公式停止应用 |
| R46 | 业务规则 | 逻辑断点（[Manual] 标记中断）：某月标记 [Manual] 则级联链在此中断，该月及之后所有月份不受影响 |
| R47 | 业务规则 | 起始点设定：某月点击 √ 进缓存后，该月期末现金余额自动成为下一月计算的强制性期初现金余额 |
| R48 | 业务规则 | 预测版本生成（Cash）：年度内任意月份 Cash 数值或状态标签（手动输入 vs 快速填充）发生任何变动，正式提交时必须生成新"已确认预测"版本 |
| R49 | 业务规则 | Distribute 应用数据类型与生效条件（同 Cash 各场景；CF-Edit 空年度勾选无变化，某月输入并点 √ 入缓存后再次勾选才生效） |
| R50 | 功能需求 | Distribute 勾选后输入运营费用总额，系统按比例自动分配至 6 指标（S&M Expenses、S&M Payroll、R&D Expenses、R&D Payroll、G&A Expenses、G&A Payroll）；这 6 指标变为实时计算、不再存数据库，edit 模式置灰不可手动编辑 |
| R51 | 计算公式 | 分配比例：以 closed month 为基准向前追溯连续 6 个月的算术平均值作为分配依据；0 视为有效输入，N/A 视为无效 |
| R52 | 计算公式 | 峰值阈值：从 closed month 向前追溯最近连续 6 个月，计算其月度环比绝对变化值的算术平均数，spikeThreshold = 2 × avgAbsMoM；超过峰值则剔除该值、用平均数代替 |
| R53 | 业务规则 | 数据不足时：优先使用同行数据，其次 LG 平台基准数据，皆无则平均分配 |
| R54 | 业务规则 | Distribute 勾选后 √ 状态处理（同批量操作 √ 逻辑） |
| R55 | 业务规则 | Distribute 取消选中：子项数据由"实时计算值"恢复为"静态值"并保留最后一次计算值；字段重新启用可手动编辑；数值先入缓存，点 Submit/Accept 后正式入库 |
| R56 | 业务规则 | 预测版本生成（Distribute）：committed forecast 任意月份 Distribute 状态标签变动，正式提交时生成新 committed forecast 版本 |
| R57 | 功能需求 | Compare 下拉含 Committed Forecast、System Generated Forecast、Confidence Intervals，选中类型展示在 Actuals 数据下方 |
| R58 | UI 需求 | Compare 展示样式：Committed Forecast 紫色字体；System Generated Forecast 紫色加图标；Confidence Intervals 在 SGF 下方显示 25%/50%/75% 百分位数据 |
| R59 | 业务规则 | Actuals 数据更新影响页面：Benchmarking（实时）、Company overview（实时）、Portfolio list（每日定时）、Normalization Tracing（每日定时）、System generated forecast（实时）、Performance tab（实时）、Peer Group Management（实时，可能影响）、Financial Metrics Tracing（实时） |
| R60 | 业务规则 | Committed forecast 数据更新影响页面：Benchmarking（实时）、Normalization Tracing（每日定时）、Performance tab（实时） |
| R61 | 业务规则 | System generated forecast 数据更新影响页面：Benchmarking（实时）、Financial Metrics Tracing（实时） |
| R62 | 功能需求 | Committed Forecast 表默认展示最新版本当前年/季 CF 数据（来源：接受 SGF 为 CF / 手动添加）；右上角 View History 进入历史列表，查看所有版本历史及当前版本信息 |
| R63 | 功能需求 | Committed Forecast 表可编辑，点 Edit 进编辑模式，编辑并保存后生成新版本 CF |
| R64 | 功能需求 | System Generated Forecast 表默认展示最新版本当前年/季 SGF 数据，可被接受为 CF；点 Accept 进编辑模式，可修改或无需修改直接提交，成为承诺预测 |
| R65 | 业务规则 | System Generated Forecast 表不可直接进行新增与编辑 |

---

## 测试用例

### 一、页面结构与表切换

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 默认进入 Financial Entry 表 | 已登录并进入 Financial Statements 页面 | 进入页面，观察右上角下拉框及当前展示的表 | 下拉框默认选中 Financial Entry，页面展示 Financial Entry 表数据 |
| TC-002 | 下拉框包含三个表选项 | 在 Financial Statements 页面 | 点击右上角下拉框，展开选项列表 | 列表包含且仅包含三项：Financial Entry、Committed Forecast、System Generated Forecast |
| TC-003 | 切换至 Committed Forecast 表 | 当前在 Financial Entry 表 | 展开下拉框，选择 Committed Forecast | 页面切换为 Committed Forecast 表，展示对应数据 |
| TC-004 | 切换至 System Generated Forecast 表 | 当前在 Committed Forecast 表 | 展开下拉框，选择 System Generated Forecast | 页面切换为 System Generated Forecast 表，展示对应数据 |
| TC-005 | 切回 Financial Entry 表 | 当前在 System Generated Forecast 表 | 展开下拉框，选择 Financial Entry | 页面切回 Financial Entry 表，展示对应数据 |

### 二、视图展示规则（三表通用）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-006 | 全屏+年视图展示当前年 12 个月 | Company Settings 视图=年视图；浏览器全屏；当前年 2026 | 全屏打开 Financial Statements 页面 | 表格展示 2026 年 1 月至 12 月共 12 个月数据 |
| TC-007 | 全屏+季度视图展示当前季度 3 个月 | Company Settings 视图=季度视图；浏览器全屏；当前为 Q2（2026-06） | 全屏打开页面 | 表格展示当前季度 3 个月（2026 年 4、5、6 月）数据 |
| TC-008 | 非全屏+年视图按屏宽展示最后几个月 | 视图=年视图；窗口缩小至仅可容纳 3 列 | 缩小窗口至非全屏，观察展示月份 | 仅展示当前年最后 3 个月（10、11、12 月）；继续拉宽可展示更多月份 |
| TC-009 | 非全屏+季度视图仅容两列优先当前月+后一月 | 视图=季度视图；当前月 2026-05；窗口仅可容纳 2 列 | 调整窗口至仅可展示两个月 | 展示当前月（5 月）与后一月（6 月） |
| TC-010 | 手机屏宽季度视图仅显示当前月 | 视图=季度视图；当前月 2026-05；手机屏宽 | 在手机屏宽下打开页面 | 仅显示当前月（5 月）一列 |
| TC-011 | 视图设置切换实时刷新展示 | 在 Financial Statements 页面，视图=年视图 | 前往 Company Settings 将视图改为季度视图，返回页面 | 页面展示由 12 个月切换为当前季度 3 个月 |

### 三、Financial Entry 数据展示与预测回显

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-012 | 手动公司预测回显-优先 Committed Forecast | 手动公司；closed month=2026-03；4 月有 Committed Forecast 也有 SGF | 查看 FE 表 4 月 Cash 数据 | 4 月显示 Committed Forecast 值，紫色字体 |
| TC-013 | 手动公司预测回显-无 CF 用 SGF | 手动公司；closed month=2026-03；5 月无 Committed Forecast、有 SGF | 查看 FE 表 5 月数据 | 5 月显示 System Generated Forecast 值，紫色字体且带小图标 |
| TC-014 | 手动公司逐月判断混合回显 | 手动公司；closed month=2026-03；4 月有 CF、5 月仅 SGF | 查看 FE 表 4、5 月数据 | 4 月显示 CF（紫色无图标），5 月显示 SGF（紫色带图标），逐月独立判断 |
| TC-015 | 手动公司 closed month 及之前为真实数据 | 手动公司；closed month=2026-03 | 查看 1、2、3 月数据 | 1、2、3 月均显示真实 Actuals 数据，黑色字体 |
| TC-016 | 自动公司日历月后用预测填充 | 自动公司；当前日历月 2026-06 | 查看 7-12 月数据 | 7-12 月用预测数据填充（按 CF 优先、SGF 次之回显），紫色显示 |
| TC-017 | 实际数据黑色字体校验 | FE 表存在 Actuals 月份 | 观察 Actuals 月份字体颜色 | Actuals 数据显示为黑色字体，无图标 |
| TC-018 | Committed Forecast 紫色字体校验 | FE 表存在 CF 回填月 | 观察 CF 回填月字体 | 显示紫色字体，无图标 |
| TC-019 | System Generated Forecast 紫色带图标校验 | FE 表存在 SGF 回填月 | 观察 SGF 回填月字体与图标 | 显示紫色字体且带小图标 |

### 四、closed month 定义

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-020 | 手动公司 closed month 取最后一个 Actuals 月 | Manual 公司；FE 表 1-3 月有 Actuals，4 月起无 | 查看系统判定的 closed month | closed month = 2026-03（最后一个有 Actuals 的月份） |
| TC-021 | 自动公司过 15 号取上个月 | Automatic 公司；服务器时间 2026-06-20；5 月有 Actuals | 查看 closed month | closed month = 2026-05（上个月） |
| TC-022 | 自动公司未过 15 号取上上个月 | Automatic 公司；服务器时间 2026-06-10；上个月有 Actuals | 查看 closed month | closed month = 2026-04（上上个月） |
| TC-023 | 自动公司上个月无 Actuals 向历史回溯 | Automatic 公司；服务器时间 2026-06-20；5 月无 Actuals，4 月有 Actuals | 查看 closed month | 系统回溯至 2026-04（最近一个有 Actuals 的月份） |
| TC-024 | 自动公司连续多月无 Actuals 持续回溯 | Automatic 公司；服务器时间 2026-06-20；5、4 月均无 Actuals，3 月有 | 查看 closed month | 系统回溯至 2026-03 |

### 五、Financial Entry 编辑入口与权限控制

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-025 | Edit 按钮为下拉设计 | 手动公司；FE 表存在可编辑数据 | 点击 Edit 按钮 | 弹出下拉，包含 Edit Financial Actuals 与 Edit Committed Forecast 两项 |
| TC-026 | 显隐逻辑-仅有可编辑 Actuals | 手动公司；当前视图内存在可编辑 Actuals，无可编辑 CF | 点击 Edit 按钮查看下拉 | 仅显示 Edit Financial Actuals，隐藏 Edit Committed Forecast |
| TC-027 | 显隐逻辑-仅有可编辑 CF | 当前视图内仅存在可编辑 Committed Forecast | 点击 Edit 按钮查看下拉 | 仅显示 Edit Committed Forecast，隐藏 Edit Financial Actuals |
| TC-028 | 置灰逻辑-两类均不可编辑 | QBO（自动）公司；Actuals 不可编辑，且当前视图仅有系统预测 | 观察 Edit 总入口 | Edit 总入口置灰，不可点击 |
| TC-029 | 编辑模式单元格黑色字体无图标 | 进入任一编辑模式 | 进入编辑模式，观察可编辑单元格 | 所有可编辑单元格数值以黑色字体显示，不显示任何辅助图标 |

### 六、Edit Financial Actuals

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-030 | 仅手动公司有该选项 | 自动公司 | 点击 Edit 按钮查看下拉 | 下拉中不出现 Edit Financial Actuals 选项 |
| TC-031 | 时间范围-日历月前可编辑 | 手动公司；当前日历月 2026-06；进入 Edit Financial Actuals | 点击 5 月 Actuals 单元格 | 5 月单元格可编辑 |
| TC-032 | 时间范围-日历月及之后置灰 | 同上 | 点击 6 月及 7 月 Actuals 单元格 | 6 月（当前日历月）及之后月份锁定置灰，不可编辑 |
| TC-033 | √ 保存机制-修改后 √ 激活 | 在 Edit Financial Actuals 模式 | 修改 5 月某指标数值 | 该月 √ 图标激活（高亮可点击） |
| TC-034 | √ 保存机制-点 √ 进缓存显示 Changes Saved | 已修改 5 月数据，√ 已激活 | 点击 5 月 √ | 数据进入缓存，该月状态显示 "Changes Saved" |
| TC-035 | 提交确认-存在未点 √ 弹窗 | 修改 5 月数据但未点击 √（√ 激活态） | 点击 Submit | 弹出确认窗，提示存在未存缓存的修改 |
| TC-036 | 提交确认-未点 √ 数据不保存 | 同上，弹出确认窗 | 在确认窗中确认提交 | 未点 √ 的 5 月修改不被保存，恢复原值 |
| TC-037 | 预测回填月编辑保留预测值作底数 | 手动公司；3 月为预测回填月（被 CF 填充）且早于日历月，进入 Edit Financial Actuals | 进入编辑，查看 3 月单元格 | 单元格保留原预测值作为底数，且不显示"比例分摊"/"Quick Fill"标签 |
| TC-038 | 预测回填月编辑确认后转为 Actuals | 同上 | 编辑 3 月数值，点 √，点 Submit | 3 月数据转换为 Actuals 属性并持久化保存，字体变为黑色 |
| TC-039 | 预测回填月独立性无波浪 | 3 月为预测回填月，4-6 月为 Quick Fill 月 | 手动编辑 3 月 Cash，点 √ | 仅 3 月当月生效，4-6 月数据不受影响（无波浪联动） |

### 七、Edit Committed Forecast

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-040 | 手动公司可编辑范围 | 手动公司；当前日历月 2026-06；进入 Edit Committed Forecast | 点击 6 月、7 月 CF 单元格；再点击 5 月 | 6 月（当前日历月）及之后可编辑；5 月及之前置灰 |
| TC-041 | 自动公司可编辑范围 | 自动公司；当前日历月 2026-06；进入 Edit Committed Forecast | 点击 6 月、7 月 CF 单元格 | 6 月（当前日历月）置灰，7 月及之后可编辑 |
| TC-042 | CF 保存生成新版本-当前月数据合并上版其余月 | 手动公司；CF 上一版本含 6-12 月数据，进入 Edit Committed Forecast | 修改 7 月 CF，点 √，点 Submit | 生成全新 CF 版本：7 月为最新数据，其余 6、8-12 月沿用上一版本数据 |
| TC-043 | CF 保存-上版无数据月记为 N/A | 上一版本仅 7 月有数据，8-12 月无数据；进入编辑 | 修改 7 月 CF，点 √，点 Submit | 新版本 7 月为最新值，8-12 月记录为 N/A |
| TC-044 | CF 提交后 View 模式紫色字体 | 完成一次 CF 编辑提交 | 退出编辑，回到 View 模式查看刚提交月份 | 该数据显示为紫色字体 |

### 八、Cash 一键功能：应用条件与 Set to Zero

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-045 | FE-Edit Actuals 对未转化预测回填月生效 | FE-Edit Actuals 模式；存在未转为 Actuals 的预测回填月 | 点击 Cash 批量操作按钮（Set to Zero / Quick Fill） | 批量操作对预测回填月按业务逻辑生效 |
| TC-046 | FE-Edit Committed Forecast 需存在 CF 数据才生效 | FE-Edit Committed Forecast 模式；对应月份存在已有 CF 数据 | 点击 Cash 批量操作按钮 | 仅对存在 CF 数据的月份生效 |
| TC-047 | Committed Forecast-Edit 空年度按钮可见不生效 | Committed Forecast 表 Edit 模式；2027 年度初始数据全为空 | 点击 Set to Zero 按钮 | 按钮可见但点击不产生任何变化 |
| TC-048 | Committed Forecast-Edit 输入并点 √ 后生效 | 同上 | 为 1 月手动输入数据并点击 √，再点击 Set to Zero | 立即对 1 月按逻辑执行（Cash 置 0） |
| TC-049 | Accept as Committed Forecast 场景按钮生效 | SGF 表点 Accept 进入编辑 / CF 表 Accept 场景 | 点击 Cash 批量操作按钮 | 批量操作在 Accept 编辑态下对相应月份生效 |
| TC-050 | Set to Zero 重置当前年所有非 N/A 月 | 年视图；预测范围 1-12 月，其中 6 月为 N/A | 点击 Set to Zero | 除 6 月（N/A）外所有月份 Cash 重置为 0，6 月保持 N/A |
| TC-051 | Set to Zero 重置当前季度范围 | 季度视图（Q2：4-6 月）；均有数据 | 点击 Set to Zero | 4、5、6 月 Cash 全部重置为 0 |
| TC-052 | 一键归零清空 Quick Fill 标签 | 预测月含手动月、Quick Fill 月、普通月 | 点击 Set to Zero | 当期所有非 N/A 月份 Cash 强制重置为 0，所有 Quick Fill 标签被清空，无论此前状态 |

### 九、Cash Quick Fill：公式与计算

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-053 | Quick Fill 公式单月计算验证 | 预测 1 月 Cash 标记 Quick Fill；t（上月）Cash_t=100；1 月 Net_Income=50, ΔAR=10, ΔOther_Assets=5, ΔAP=8, ΔLong-term debt=20 | 点击 Quick Fill | 1 月 Cash = 100 + 50 − 10 − 5 + 8 + 20 = **163** |
| TC-054 | Quick Fill 多月按时间顺序级联 | 续上：2 月 Quick Fill；2 月 Net_Income=40, ΔAR=5, ΔOther_Assets=2, ΔAP=3, ΔLong-term debt=0 | 点击 Quick Fill | 1 月=163；2 月 Cash = 163 + 40 − 5 − 2 + 3 + 0 = **199** |
| TC-055 | Quick Fill 仅作用于 Cash=0 或 Quick Fill 标记月 | 1 月手动 Cash=120（手动月），2 月 Cash=0 | 点击 Quick Fill | 1 月保持 120 不变，仅 2 月被计算填充 |
| TC-056 | t 月用实际数据作期初（Edit Actuals 场景） | 2025-12 为 Actuals Cash=100；2026 年 Edit Financial Actuals 模式；2026-01 Quick Fill | 先点 Set to Zero 再点 Quick Fill，计算 1 月 | 计算 1 月时 Cash_t 取 2025-12 的 Actuals 实际值 100，而非 N/A |
| TC-057 | t 月数据类型随目标月类型选取 | 目标 1 月保存为 CF；t 月（上月）同时有 Actuals 与 CF | 在 CF 编辑模式点 Quick Fill | 计算 1 月时 t 月取 CF 数据（目标保存为哪种就用哪种），不取 N/A |
| TC-058 | 非可填充月触发提示弹框 | 预测月中 3 月、7 月为手动录入 Cash，其余为 0/Quick Fill | 点击 Quick Fill | 弹出 "Manually Modified Months Detected" 弹框，列出 3 月、7 月，提示将保留手动月、仅计算 set to zero / Quick Fill 月，含 Cancel 与 Proceed with Quick Fill 两按钮 |
| TC-059 | 弹框 Cancel 取消操作 | 续上，弹框已出现 | 点击 Cancel | 关闭弹框，不执行 Quick Fill，数据无变化 |
| TC-060 | 弹框 Proceed 保留手动月只算其余 | 续上，弹框已出现 | 点击 Proceed with Quick Fill | 3 月、7 月手动值保留，其余 set to zero / Quick Fill 标记月被计算填充 |
| TC-061 | 汇率换算导致页面直算值与系统值不符 | 预测月涉及不同月汇率，P&L 与 B/S 取不同汇率 | 用页面显示值手工套公式计算，与系统 Quick Fill 结果对比 | 系统按原始数据计算后再按计算月汇率换算，结果可能不等于用页面显示值直接计算的数值（允许差异，以系统换算为准） |

### 十、Cash Quick Fill：波浪影响

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-062 | 批量 Quick Fill 波浪至首个不可填充月 | 年视图；1-5 月可填充，6 月不可填充，7-12 月可填充 | 点击 Quick Fill | 第一轮波浪自 1 月推进至 5 月（遇 6 月停止）；6 月之后存在可填充区间，开启下一轮波浪填充 7-12 月 |
| TC-063 | 批量 Quick Fill 跨年持续传递 | 季度视图跨年；波浪可推至次年 | 点击 Quick Fill | 波浪跨年持续影响至首个不可填充月结束，且跨期后不再开启新的下一轮波浪 |
| TC-064 | 手动编辑触发波浪前提满足 | CF-Edit 模式；5 月紧后 6 月已标记 Quick Fill | 手动修改 5 月 Net_Income（公式变量），点 √ | 波浪触发，6 月及后续连续 Quick Fill 月 Cash 重算 |
| TC-065 | 手动编辑非公式变量不触发波浪 | 5 月紧后 6 月为 Quick Fill | 手动修改 5 月某非公式变量指标，点 √ | 不触发波浪，6 月数据不变 |
| TC-066 | 手动编辑紧后月非 Quick Fill 不触发 | 5 月紧后 6 月为手动月（非 Quick Fill） | 手动修改 5 月公式变量，点 √ | 不触发波浪 |
| TC-067 | 手动编辑波浪遇非 Quick Fill 月中断 | 5 月后 6、7 月 Quick Fill，8 月非 Quick Fill，9 月 Quick Fill | 手动修改 5 月公式变量，点 √ | 波浪重算 6、7 月，到 8 月中断；9 月即便是 Quick Fill 也不被影响 |
| TC-068 | 手动编辑波浪跨期传递 | 5 月后至次年连续 Quick Fill，次年某月不可填充 | 手动修改 5 月公式变量，点 √ | 波浪跨期持续传递至首个不可填充/非 Quick Fill 月为止 |
| TC-069 | 点 √ 后续 Quick Fill 月无激活 √ 页面更新 | 5 月点 √ 触发波浪；6-12 月 Quick Fill 且无激活 √ | 点击 5 月 √ | 6-12 月 Cash 在页面上更新 |
| TC-070 | 后续 √ 已激活但 cash 未手动编辑 | 5 月点 √ 触发；6-12 月 Quick Fill，√ 已激活（仅编辑了 revenue，cash 未手动改） | 点击 5 月 √ | 6-12 月 cash 仅后台缓存，√ 不自动变 Changes Saved，页面 cash 值更新，其他指标手动编辑维持未提交 |
| TC-071 | 后续 √ 已激活且 cash 已手动编辑 | 6-12 月 Quick Fill，√ 已激活且 cash 被手动编辑 | 点击 5 月 √ 触发波浪 | 6-12 月 cash 仅后台缓存，√ 不自动变 Changes Saved，页面 cash 值不更新 |
| TC-072 | 综合示例-5 月 √ 触发 6-12 月波浪 | FE-Edit CF；5-12 月 cash 已应用 Quick Fill；手动编辑 5-12 月 revenue，√ 均激活 | 点击 5 月 √ | 5 月 cash 与 revenue 存缓存、状态 Changes Saved；6-12 月 cash 页面更新但仅后台缓存、√ 不变 Changes Saved（revenue 手动编辑未提交） |

### 十一、批量操作 √ 状态处理

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-073 | √ 未激活月批量操作自动 Changes Saved | 某月 √ 未激活（无手动编辑） | 点击批量操作按钮（如 Quick Fill） | 系统自动激活 √ 并缓存数据，状态更新为 "Changes Saved" |
| TC-074 | √ 已激活月批量操作不自动 Changes Saved | 某月 √ 已激活（有手动编辑） | 点击批量操作按钮 | 仅对批量涉及指标后台缓存，状态不自动跳 Changes Saved，√ 保持未点 |
| TC-075 | √ 已激活月手动勾 √ 提交保存手输 | 续上 | 手动勾选该月 √ 并提交 | 保存用户手输数据 |
| TC-076 | √ 已激活月直接提交保存批量缓存 | 续 TC-074 | 不勾 √ 直接提交 | 手动编辑失效，最终保存批量操作生成的缓存数据 |
| TC-077 | √ 因 cash 本身激活-冲突维持手动值 | √ 激活原因是手动编辑了 cash 本身（如改为 0） | 点击 Quick Fill | 页面维持用户手动 cash 值，Quick Fill 计算结果仅入后台缓存不回显 |
| TC-078 | √ 因非 cash 指标激活-回显 Quick Fill 值 | √ 激活原因是手动编辑了 revenue 等非 cash 指标 | 点击 Quick Fill | Quick Fill 计算的 cash 值回显页面，后台同步缓存，√ 维持激活不自动 Changes Saved |
| TC-079 | 综合示例-6 月改 cash、7-12 月改 revenue | FE-Edit CF；5-12 月 cash 已 Quick Fill；5-12 月 revenue 及 6 月 cash 均手动编辑，√ 全激活 | 点击 Quick Fill | 5-12 月 √ 均不自动变 Changes Saved；6 月 cash 页面维持手动值（如 0）、Quick Fill 结果入后台缓存；7-12 月（仅改 revenue）Quick Fill 的 cash 回显页面、后台缓存、√ 维持激活 |

### 十二、Quick Fill 边缘情况与终止规则

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-080 | N/A 间隙不中断计算 | 1 月有数据，2 月 N/A，3 月可填充 | 点击 Quick Fill | 2 月 Cash 及各 Delta 视为 0，计算不中断；3 月以 2 月（视为 0）为期初继续计算 |
| TC-081 | 尾部全 N/A 公式停止 | 1-3 月可填充，4-12 月全 N/A | 点击 Quick Fill | 计算到 3 月后，因后续全 N/A，公式停止应用 |
| TC-082 | [Manual] 标记中断级联 | 5 月修改公式变量；6 月 Quick Fill；7 月 [Manual] | 手动修改 5 月数据并触发波浪 | 6 月数据更新；7 月（[Manual]）及之后所有月份不受影响、保持不变 |
| TC-083 | 起始点设定-点 √ 后期末成为下月期初 | 1 月计算完成并点击 √ 进缓存 | 计算 2 月 Cash | 1 月期末现金余额自动成为 2 月计算的强制期初现金余额 |

### 十三、预测版本生成机制

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-084 | Cash 数值变动提交生成新版本 | CF 编辑模式；修改某月 Cash 数值 | 点 √ 并 Submit | 系统生成一个新的"已确认预测"版本 |
| TC-085 | Cash 状态标签变动提交生成新版本 | 某月状态标签由"手动输入"变为"快速填充"（或反向） | 提交 | 系统生成新"已确认预测"版本 |
| TC-086 | Cash 无任何变动不生成新版本 | 进入编辑但未做任何 Cash 数值/标签变动 | 直接提交 | 不生成新版本 |

### 十四、Distribute operating expenses using historical percentages

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-087 | FE-Edit Actuals 对未转化预测回填月生效 | FE-Edit Actuals 模式；存在未转 Actuals 的预测回填月 | 勾选 Distribute 选项 | 功能对预测回填月按业务逻辑生效 |
| TC-088 | FE-Edit CF 需存在 CF 数据才生效 | FE-Edit Committed Forecast 模式；对应月存在 CF 数据 | 勾选 Distribute 选项 | 仅对存在 CF 数据的月份生效 |
| TC-089 | CF-Edit 空年度勾选无变化 | Committed Forecast Edit 模式；2027 年度数据全空 | 勾选 Distribute 选项 | 勾选后数据无任何变化 |
| TC-090 | CF-Edit 输入并点 √ 后勾选生效 | 续上 | 为 1 月输入数据点 √ 入缓存，再次成功勾选 Distribute | 立即对 1 月按逻辑执行分配 |
| TC-091 | 输入总额按比例分配至 6 指标 | closed month=2025-12；前 6 月平均：S&M Exp=300, S&M Pay=200, R&D Exp=150, R&D Pay=250, G&A Exp=50, G&A Pay=50（合计 1000，比例 30/20/15/25/5/5%） | 勾选 Distribute，输入运营费用总额 2000 | 分配结果：S&M Exp=600、S&M Pay=400、R&D Exp=300、R&D Pay=500、G&A Exp=100、G&A Pay=100 |
| TC-092 | 6 指标变实时计算不存库且置灰 | 已勾选 Distribute 并完成分配 | 在 edit 模式查看 6 个子指标单元格 | 6 指标变为实时计算、不再存数据库；edit 模式置灰，不可手动编辑 |
| TC-093 | 分配比例-连续 6 月算术平均 | closed month=2025-12；S&M Exp 7-12 月为 100,110,120,130,140,150 | 触发分配，查看 S&M Exp 平均基数 | 以向前连续 6 个月算术平均 =（100+110+120+130+140+150)/6=125 作为该指标分配依据 |
| TC-094 | 0 视为有效输入参与平均 | 某指标 6 个月中含一个月为 0 | 触发分配 | 0 作为有效值纳入算术平均计算 |
| TC-095 | N/A 视为无效不参与 | 某指标 6 个月中含一个月为 N/A | 触发分配 | N/A 视为无效，不纳入平均计算 |
| TC-096 | 峰值阈值剔除异常值 | 某指标 6 月值=100,110,105,300,115,120；MoM 绝对变化=10,5,195,185,5，avgAbsMoM=(10+5+195+185+5)/5=80，spikeThreshold=2×80=160 | 触发分配 | 超过阈值 160 的变化（195、185）对应的峰值 300 被剔除，用平均数代替后再计算分配比例 |
| TC-097 | 数据不足优先同行数据 | 该公司历史数据不足 6 个月，存在同行数据 | 触发分配 | 系统优先使用同行数据作为分配依据 |
| TC-098 | 数据不足无同行用 LG 基准 | 历史不足且无同行数据，有 LG 平台基准 | 触发分配 | 使用 LG 平台基准数据 |
| TC-099 | 数据不足两者皆无平均分配 | 历史不足、无同行、无 LG 基准 | 触发分配，输入总额 1200 | 6 个指标平均分配，各 200 |
| TC-100 | Distribute 勾选 √ 未激活月自动 Changes Saved | 某月 √ 未激活 | 勾选 Distribute | 自动激活 √ 并缓存，状态 "Changes Saved" |
| TC-101 | Distribute 勾选 √ 已激活月不自动跳转 | 某月 √ 已激活（有手动编辑） | 勾选 Distribute | 仅对涉及指标后台缓存，状态不自动跳 Changes Saved，√ 保持未点；手动勾 √ 提交保存手输，直接提交则手动编辑失效保存 Distribute 缓存 |
| TC-102 | 取消选中恢复静态值保留最后计算值 | 已勾选 Distribute 并完成分配 | 取消勾选 Distribute | 6 子项由"实时计算值"恢复为"静态值"，保留最后一次计算所得数值 |
| TC-103 | 取消选中字段重新可编辑 | 续上 | 点击某子项单元格 | 字段重新启用，允许手动编辑 |
| TC-104 | 取消选中先缓存提交后入库 | 续上，已取消勾选 | 点击 Submit/Accept | 数值先入缓存，提交后按序正式保存至数据库 |
| TC-105 | Distribute 状态变动生成新 CF 版本 | CF 模式；某月 Distribute 状态标签发生变动 | 正式提交 | 系统生成新的 committed forecast 版本 |

### 十五、数据对比 Compare

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-106 | Compare 下拉选项完整 | FE 表 View 模式 | 点击 Compare 下拉 | 包含 Committed Forecast、System Generated Forecast、Confidence Intervals 三项 |
| TC-107 | Compare-Committed Forecast 紫色展示 | FE 表 | Compare 选择 Committed Forecast | CF 数据展示在 Actuals 数据下方，紫色字体 |
| TC-108 | Compare-System Generated Forecast 紫色带图标 | FE 表 | Compare 选择 System Generated Forecast | SGF 数据展示在 Actuals 下方，紫色字体加图标 |
| TC-109 | Compare-Confidence Intervals 百分位展示 | FE 表 | Compare 选择 Confidence Intervals | 在 SGF 下方显示 SGF 数据的 25%、50%、75% 百分位数据 |
| TC-110 | Compare 多选组合展示 | FE 表 | Compare 同时选中 CF 与 SGF | Actuals 下方同时展示 CF（紫色）与 SGF（紫色带图标）两行数据 |
| TC-111 | Compare 取消选中移除对比行 | 已选中 Committed Forecast | 取消勾选 Committed Forecast | Actuals 下方移除 CF 对比行 |

### 十六、数据更新影响页面

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-112 | Actuals 更新实时影响页面 | 在 FE 表更新某月 Actuals 数据并提交 | 提交后查看 Benchmarking、Company overview、System generated forecast、Performance tab、Financial Metrics Tracing、Peer Group Management | 上述页面实时反映 Actuals 变更 |
| TC-113 | Actuals 更新每日定时影响页面 | 同上提交 Actuals | 次日定时任务后查看 Portfolio list、Normalization Tracing | 两页面在每日定时刷新后反映变更 |
| TC-114 | Committed Forecast 更新影响页面 | 更新 CF 数据并提交 | 查看 Benchmarking（实时）、Performance tab（实时）、Normalization Tracing（每日定时） | Benchmarking、Performance tab 实时刷新；Normalization Tracing 每日定时刷新 |
| TC-115 | System Generated Forecast 更新影响页面 | SGF 数据更新 | 查看 Benchmarking、Financial Metrics Tracing | 两页面实时反映 SGF 变更 |

### 十七、Committed Forecast 表

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-116 | 默认展示最新版本当前年/季 CF | 切换至 Committed Forecast 表 | 查看默认展示数据 | 展示最新版本的当前年/季度承诺预测数据 |
| TC-117 | CF 数据来源-接受 SGF | SGF 表已 Accept 某数据为 CF | 查看 CF 表 | CF 表包含由 SGF 接受而来的数据 |
| TC-118 | CF 数据来源-手动添加 | 手动添加过 CF 数据 | 查看 CF 表 | CF 表包含手动添加的承诺预测数据 |
| TC-119 | View History 查看版本历史 | CF 表存在多个版本 | 点击右上角 View History | 进入 Committed Forecast History 列表，可看到所有版本历史记录及当前版本信息 |
| TC-120 | CF 表编辑生成新版本 | CF 表 | 点击 Edit 进入编辑模式，修改数据并保存 | 保存后生成新版本 CF |
| TC-121 | CF 表 Cash Quick Fill 功能一致 | CF 表 Edit 模式 | 使用 Cash 的 Set to Zero / Quick Fill | 行为与 Financial Entry 中 Cash 一键功能一致 |
| TC-122 | CF 表 Distribute 功能一致 | CF 表 Edit 模式 | 使用 Distribute operating expenses 功能 | 行为与 Financial Entry 中 Distribute 功能一致 |

### 十八、System Generated Forecast 表

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-123 | 默认展示最新版本当前年/季 SGF | 切换至 System Generated Forecast 表 | 查看默认展示数据 | 展示最新版本的当前年/季度系统生成预测数据 |
| TC-124 | SGF 不可直接新增编辑 | SGF 表 View 模式 | 尝试直接点击单元格编辑 | 单元格不可直接新增或编辑 |
| TC-125 | Accept 进入编辑模式 | SGF 表 | 点击 Accept | 进入编辑模式 |
| TC-126 | Accept 修改后提交成为 CF | SGF Accept 编辑模式 | 修改部分数据，点击提交 | 数据成为承诺预测，写入 Committed Forecast |
| TC-127 | Accept 无修改直接提交成为 CF | SGF Accept 编辑模式 | 不修改，直接提交 | 原 SGF 数据直接成为承诺预测 |

---

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1 | 页面含三表及下拉切换 | ✅ 已覆盖 | TC-001~TC-005 | |
| R2 | 全屏+年视图 12 月 | ✅ 已覆盖 | TC-006 | |
| R3 | 全屏+季度视图 3 月 | ✅ 已覆盖 | TC-007 | |
| R4 | 非全屏+年视图按屏宽 | ✅ 已覆盖 | TC-008 | |
| R5 | 非全屏+季度视图两列/手机 | ✅ 已覆盖 | TC-009, TC-010 | |
| R6 | 手动公司预测回显逐月判断 | ✅ 已覆盖 | TC-012~TC-015 | |
| R7 | 自动公司日历月后填充 | ✅ 已覆盖 | TC-016 | |
| R8 | 字体颜色规则 | ✅ 已覆盖 | TC-017~TC-019 | |
| R9 | closed month（Manual） | ✅ 已覆盖 | TC-020 | |
| R10 | closed month（Automatic） | ✅ 已覆盖 | TC-021~TC-024 | |
| R11 | Edit 下拉两选项 | ✅ 已覆盖 | TC-025 | |
| R12 | 显隐逻辑 | ✅ 已覆盖 | TC-026, TC-027 | |
| R13 | 置灰逻辑 | ✅ 已覆盖 | TC-028 | |
| R14 | 编辑模式黑色无图标 | ✅ 已覆盖 | TC-029 | |
| R15 | 仅手动公司有 Edit Actuals | ✅ 已覆盖 | TC-030 | |
| R16 | Edit Actuals 时间范围 | ✅ 已覆盖 | TC-031, TC-032 | |
| R17 | √ 保存机制 | ✅ 已覆盖 | TC-033, TC-034 | |
| R18 | 提交确认未点 √ | ✅ 已覆盖 | TC-035, TC-036 | |
| R19 | 预测回填月保留底数无标签 | ✅ 已覆盖 | TC-037 | |
| R20 | 预测回填月转 Actuals | ✅ 已覆盖 | TC-038 | |
| R21 | 预测回填月独立性 | ✅ 已覆盖 | TC-039 | |
| R22 | CF 可编辑范围（手动） | ✅ 已覆盖 | TC-040 | |
| R23 | CF 可编辑范围（自动） | ✅ 已覆盖 | TC-041 | |
| R24 | CF 保存合并生成新版本 | ✅ 已覆盖 | TC-042, TC-043 | |
| R25 | CF 提交后紫色字体 | ✅ 已覆盖 | TC-044 | |
| R26 | Cash 按钮应用类型与条件 | ✅ 已覆盖 | TC-045, TC-046, TC-049 | |
| R27 | CF-Edit 空年度按钮逻辑 | ✅ 已覆盖 | TC-047, TC-048 | |
| R28 | Set to Zero 重置非 N/A 月 | ✅ 已覆盖 | TC-050, TC-051 | |
| R29 | 一键归零强制清标签 | ✅ 已覆盖 | TC-052 | |
| R30 | Quick Fill 公式 | ✅ 已覆盖 | TC-053, TC-054, TC-055 | 含具体数据验证 |
| R31 | N/A 时取 0 | ✅ 已覆盖 | TC-080 | |
| R32 | t 月数据类型选取 | ✅ 已覆盖 | TC-056, TC-057 | |
| R33 | 汇率换算差异 | ✅ 已覆盖 | TC-061 | |
| R34 | 非可填充月弹框 | ✅ 已覆盖 | TC-058~TC-060 | |
| R35 | 批量 Quick Fill 波浪 | ✅ 已覆盖 | TC-062, TC-063 | |
| R36 | 手动编辑触发波浪前提 | ✅ 已覆盖 | TC-064~TC-066 | |
| R37 | 手动波浪中断即止 | ✅ 已覆盖 | TC-067 | |
| R38 | 手动波浪跨期 | ✅ 已覆盖 | TC-068 | |
| R39 | 点 √ 后续 √ 状态处理 | ✅ 已覆盖 | TC-069~TC-072 | |
| R40 | 批量 √ 未激活自动保存 | ✅ 已覆盖 | TC-073 | |
| R41 | 批量 √ 已激活逻辑 | ✅ 已覆盖 | TC-074~TC-076 | |
| R42 | cash 本身冲突维持手动值 | ✅ 已覆盖 | TC-077, TC-079 | |
| R43 | 非 cash 指标回显 Quick Fill | ✅ 已覆盖 | TC-078, TC-079 | |
| R44 | N/A 间隙不中断 | ✅ 已覆盖 | TC-080 | |
| R45 | 尾部全 N/A 终止 | ✅ 已覆盖 | TC-081 | |
| R46 | [Manual] 中断 | ✅ 已覆盖 | TC-082 | |
| R47 | 起始点期初设定 | ✅ 已覆盖 | TC-083 | |
| R48 | Cash 预测版本生成 | ✅ 已覆盖 | TC-084~TC-086 | |
| R49 | Distribute 应用类型与条件 | ✅ 已覆盖 | TC-087~TC-090 | |
| R50 | Distribute 总额分配 6 指标 | ✅ 已覆盖 | TC-091, TC-092 | 含具体数据验证 |
| R51 | 分配比例 6 月平均/0/N/A | ✅ 已覆盖 | TC-093~TC-095 | 含具体数据验证 |
| R52 | 峰值阈值剔除 | ✅ 已覆盖 | TC-096 | 含具体数据验证 |
| R53 | 数据不足回退策略 | ✅ 已覆盖 | TC-097~TC-099 | |
| R54 | Distribute √ 状态处理 | ✅ 已覆盖 | TC-100, TC-101 | |
| R55 | Distribute 取消选中 | ✅ 已覆盖 | TC-102~TC-104 | |
| R56 | Distribute 预测版本生成 | ✅ 已覆盖 | TC-105 | |
| R57 | Compare 下拉选项 | ✅ 已覆盖 | TC-106 | |
| R58 | Compare 展示样式 | ✅ 已覆盖 | TC-107~TC-109 | 多选/取消见 TC-110, TC-111 |
| R59 | Actuals 更新影响页面 | ✅ 已覆盖 | TC-112, TC-113 | |
| R60 | CF 更新影响页面 | ✅ 已覆盖 | TC-114 | |
| R61 | SGF 更新影响页面 | ✅ 已覆盖 | TC-115 | |
| R62 | CF 表展示与版本历史 | ✅ 已覆盖 | TC-116~TC-119 | |
| R63 | CF 表编辑生成新版本 | ✅ 已覆盖 | TC-120~TC-122 | |
| R64 | SGF 表 Accept 成为 CF | ✅ 已覆盖 | TC-123, TC-125~TC-127 | |
| R65 | SGF 表不可直接编辑 | ✅ 已覆盖 | TC-124 | |

**覆盖率：100%**（65/65 需求全部已覆盖）
