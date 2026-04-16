# 测试用例：Benchmark 基准测试功能

- **需求来源**：E:\lg\benchmark\Benchmark company功能需求文档_v2.md
- **生成时间**：2026-04-08

---

## 需求清单

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R1 | UI 需求 | 页面标题显示"Benchmarking"，下方显示三行英文说明文字 |
| R2 | 功能需求 | 导航路径：Finance 模块 → Benchmarking Tab，同级菜单包含 Overview、Financial Statements、Performance |
| R3 | 功能需求 | VIEW 筛选卡片：单选，选项为 Snapshot 和 Trend，选中项蓝色点亮，默认 Snapshot |
| R4 | 业务规则 | FILTER 筛选卡片：多选，选项为 ALL/GROWTH/EFFICIENCY/MARGINS/CAPITAL；ALL 与其他选项互斥（选中 ALL 后选其他则 ALL 自动取消，其他选项可同时选中）；默认 ALL；蓝色点亮 |
| R5 | 功能需求 | DATA 筛选卡片：多选，选项为 Actuals/Committed Forecast/System Generated Forecast；选中项黄色点亮；默认 Actuals |
| R6 | 功能需求 | BENCHMARK 筛选卡片：多选，选项为 Internal Peers/KeyBanc/High Alpha/Benchmark.it；最多 4 个；选中项黄色点亮；默认 Internal Peers |
| R7 | 业务规则 | 无同行匹配时显示 Peer Fallback 提示信息，自动回退到 LG 平台基准 |
| R8 | 功能需求 | 日历选择区域：默认为最后一个有 Actual 数据的月份；新建公司默认当前日历月；用户可选择不同月份 |
| R9 | 功能需求 | Overall Benchmark Score Card 显示百分位数值（如 51%ile），计算方法为四个板块所有维度百分位的算术平均值 |
| R10 | UI 需求 | Overall Score 进度条颜色规则：0≤n<25% 红色，25≤n<50% 粉色，50≤n<75% 黄色，75≤n≤100% 绿色；超范围时按相邻基准点位颜色填充 |
| R11 | 功能需求 | 进度条点位：每个点位代表一个 DATA×BENCHMARK 维度内所有指标的平均百分位，最多 12 个点位 |
| R12 | 功能需求 | 点位 Tooltip：鼠标悬停显示第一行维度标识、第二行平均百分位（P值或~P值） |
| R13 | 业务规则 | 多个点位完全重合时打包展示，按 Data-Benchmark 排序显示，点位外观按排序第一个维度显示 |
| R14 | UI 需求 | 右上角信息提示：显示 "[X] Metrics - [Quartile 名称]"，X 为 metric 数量 |
| R15 | UI 需求 | 存在特殊计算时显示提示："Includes estimated percentiles (interpolated values used/boundary values used/interpolated values & boundary values used)" |
| R16 | 功能需求 | Snapshot 视图包含 4 个固定板块：Revenue & Growth、Profitability & Efficiency、Burn & Runway、Capital Efficiency |
| R17 | UI 需求 | 每个板块标题行包含：板块名称（加粗）、百分位排名（右对齐）、进度条（颜色规则同 Overall Score） |
| R18 | 业务规则 | 板块进度条不显示维度点位，仅显示该板块的平均百分位 |
| R19 | 功能需求 | 单个指标展示：指标名称、实际值（取自 Normalization Tracing）、分布条（水平彩色条形图）、百分位数值（精确 P45/估算 ~P64/超范围 >P75 或 <P25） |
| R20 | 功能需求 | 指标名称悬停显示：LG 指标名称和公式，各 Benchmark 对应的 Metric Name、Definition、Segment 信息、Best Guess、Platform-Edition |
| R21 | 功能需求 | 指标分布条 Tooltip：显示指标名称、数据类型、基准来源 |
| R22 | 业务规则 | 无数据处理：指标无数据显示灰色空白进度条+NA；基准无数据显示灰色空白进度条+名称后加(N/A)；整个板块无数据显示"N/A" |
| R23 | 功能需求 | 板块展开/收起：点击板块标题可展开/收起；默认卡片展开、指标收起状态 |
| R24 | 功能需求 | Show All/Hide 按钮：一个指标有多个分布条时显示 Show All 按钮，点击显示全部分布条后按钮变为 Hide |
| R25 | 业务规则 | FILTER 与板块对应关系：GROWTH→Revenue & Growth，EFFICIENCY→Profitability & Efficiency，MARGINS→Burn & Runway，CAPITAL→Capital Efficiency，ALL→所有板块 |
| R26 | 业务规则 | Data-Benchmark 展示排序：Benchmark 优先（Internal Peers→KeyBanc→High Alpha→Benchmark.it），Data 次之（Actuals→Committed Forecast→System Generated Forecast） |
| R27 | 功能需求 | Trend 视图：用户自定义时间范围，开始和结束月份不能是同一个月，默认从 closed month 往前 6 个月 |
| R28 | 功能需求 | Trend 视图折线图：横坐标月份、纵坐标百分位 0-100%ile；最多 12 条折线；颜色与 Snapshot 一致 |
| R29 | 业务规则 | Trend 视图 NA 处理：月份百分位为 NA 时折线点落到 P0，悬浮 Tooltip 显示 NA |
| R30 | 业务规则 | Trend 视图超范围处理：>P75 折线点落在 P100，<P25 折线点落在 P0 |
| R31 | 功能需求 | Trend 视图交互：悬停月份显示竖向网格线和所有交集点百分位；悬停折线点高亮该线并显示详情 |
| R32 | UI 需求 | 雷达图结构：中心 P0，同心圆 P25/P50/P75/P100，6 个角度对应 6 个指标，最多 12 条线 |
| R33 | 业务规则 | 雷达图 Snapshot 模式：数据范围为单月，每个角的值=选定月份百分位 |
| R34 | 业务规则 | 雷达图 Trend 模式：数据范围为用户选择的连续月份，计算方式为所有月度百分位的算术平均 |
| R35 | 功能需求 | 雷达图图例：方便用户控制网的显隐，排序与 Data-Benchmark 展示排序一致 |
| R36 | 功能需求 | 雷达图交互：悬浮指标轴线时显示该指标所有 Data-Benchmark 组合的百分位详情和指标名称 |
| R37 | 数据需求 | ARR Growth Rate 公式：(ARR_t - ARR_(t-1)) / ARR_(t-1)，正向指标 |
| R38 | 数据需求 | Gross Margin 公式：(Gross Profit / Gross Revenue) × 100%，正向指标，取值 0%-100% |
| R39 | 数据需求 | Monthly Net Burn Rate 公式：Net Income - Capitalized R&D (Monthly)，正向指标，升序排序 |
| R40 | 数据需求 | Monthly Runway 公式：-(Cash / Monthly Net Burn Rate)，正向指标，含 Cash/Burn 各组合情况处理 |
| R41 | 数据需求 | Rule of 40 公式：(Net Profit Margin + MRR YoY Growth Rate) × 100%，正向指标 |
| R42 | 数据需求 | Sales Efficiency Ratio 公式：(S&M Expenses + S&M Payroll) / New MRR LTM，反向指标 |
| R43 | 业务规则 | Internal Peer 百分位计算：最近排名百分位法，标准竞争排名，公式 P=((R-1)/(N-1))×100% |
| R44 | 边界条件 | N=1 时百分位=100；所有同行指标完全相同时不显示百分位，不计入汇总 |
| R45 | 业务规则 | 外部平台基准：精确匹配显示精确百分位；区间内使用线性插值（显示~P）；超范围显示>P或<P并用边界值计算 |
| R46 | 业务规则 | 外部平台超范围详细规则：>P25 计算用 P50，>P50 计算用 P75，>P75 计算用 P100，<P25 计算用 P0，<P50 计算用 P25，<P75 计算用 P50 |
| R47 | 业务规则 | P50 特殊规则：仅有中位数时，高于→P75，低于→P25，等于→P50 |
| R48 | 业务规则 | 同行匹配五维度：公司类型、公司阶段、会计方法（必填）、ARR 规模（含前不含后区间规则）、数据质量（至少 3 家同行，24 个月内连续 6 个月非负 gross revenue） |
| R49 | 业务规则 | 同行回退规则：同行<4 个时回退到 LG 平台基准并显示 Peer Fallback；≥4 个时显示"Peer Count: X" |
| R50 | 业务规则 | DATA 类型与同行：使用同行对应 DATA 类型数据；若同行无该 DATA 数据则排除；Forecast 选外部基准时用预测数据对实际基准 |
| R51 | 业务规则 | 排除条件：Exited/Shut Down/Inactive 状态公司不参与同行计算 |
| R52 | 数据需求 | 板块分数=板块内所有有效指标百分位的算术平均；Overall Score=四个板块分数的算术平均 |
| R53 | 数据需求 | 维度分数=该 DATA-BENCHMARK 维度下所有指标百分位的算术平均 |
| R54 | 业务规则 | 指标缺失时：排除该指标，分母减 1；整个板块无数据时该板块=N/A，不计入 Overall Score |
| R55 | 业务规则 | Forecast 内部同行基准：用预测 ARR 找同行；无同行预测数据时降级到所有活跃 LG 企业的 Actual |
| R56 | 功能需求 | 新建公司处理：日期默认当前日历月，仅显示 Forecast 数据，Actuals 不可选或灰色 |
| R57 | UI 需求 | 颜色编码：红色#FF4444(0-25%)、粉色#FF88BB(25-50%)、黄色#FFBB44(50-75%)、绿色#44BB44(75-100%)、灰色#CCCCCC(N/A)；选中状态：VIEW/FILTER 蓝色#2196F3，DATA/BENCHMARK 黄色#FFC107 |
| R58 | 业务规则 | Actual 数据默认月份：手动数据取最后有数据月份；自动数据 15 号之前用上上月，15 号之后用上月 |

## 测试用例

### 一、页面标题与导航

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 页面导航路径验证 | 已登录 LG 系统 | 点击 Finance 模块 | 进入 Finance 模块页面 |
| | | | 查看顶部 Tab 栏 | 显示 Overview、Financial Statements、Performance、Benchmarking 四个 Tab |
| | | | 点击 Benchmarking Tab | 进入 Benchmark 页面 |
| TC-002 | 页面标题和说明文字展示 | 已进入 Benchmark 页面 | 查看页面顶部标题 | 显示标题"Benchmarking" |
| | | | 查看标题下方说明文字 | 显示三行英文说明："Benchmark values are normalized for comparability."、"Industry calculations may differ from Looking Glass metrics."、"Use for directional context only." |

### 二、VIEW 筛选卡片

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-003 | VIEW 默认状态 | 已进入 Benchmark 页面 | 查看 VIEW 筛选卡片 | Snapshot 默认选中，蓝色(#2196F3)点亮；Trend 未选中 |
| TC-004 | 切换 VIEW 到 Trend | VIEW=Snapshot | 点击 Trend 选项 | Trend 蓝色点亮，Snapshot 取消高亮；页面切换为 Trend 视图，显示折线图 |
| TC-005 | 从 Trend 切回 Snapshot | VIEW=Trend | 点击 Snapshot 选项 | Snapshot 蓝色点亮，Trend 取消高亮；页面切换为 Snapshot 视图，显示分布条 |
| TC-006 | VIEW 单选互斥验证 | VIEW=Snapshot | 点击 Trend 选项 | 仅 Trend 选中，Snapshot 自动取消，不可同时选中两个 |

### 三、FILTER 筛选卡片

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-007 | FILTER 默认状态 | 已进入 Benchmark 页面 | 查看 FILTER 筛选卡片 | ALL 默认选中且蓝色(#2196F3)点亮；其他选项未选中 |
| TC-008 | ALL 与其他选项互斥-选其他取消 ALL | FILTER=ALL | 点击 GROWTH 选项 | GROWTH 蓝色点亮，ALL 自动取消选中；页面仅显示 Revenue & Growth 板块 |
| TC-009 | 多选非 ALL 选项 | FILTER=GROWTH 已选中 | 点击 EFFICIENCY 选项 | GROWTH 和 EFFICIENCY 同时蓝色点亮；页面显示 Revenue & Growth 和 Profitability & Efficiency 两个板块 |
| TC-010 | 三选非 ALL 选项 | FILTER=GROWTH+EFFICIENCY 已选中 | 点击 MARGINS 选项 | GROWTH、EFFICIENCY、MARGINS 同时蓝色点亮；页面显示对应三个板块 |
| TC-011 | 全选四个非 ALL 选项 | FILTER=GROWTH+EFFICIENCY+MARGINS 已选中 | 点击 CAPITAL 选项 | 四个非 ALL 选项全部选中且蓝色点亮；页面显示全部四个板块 |
| TC-012 | 重新选中 ALL | FILTER=GROWTH+EFFICIENCY 已选中 | 点击 ALL 选项 | ALL 蓝色点亮，GROWTH 和 EFFICIENCY 自动取消选中；页面显示全部四个板块 |
| TC-013 | 取消单个非 ALL 选项 | FILTER=GROWTH+EFFICIENCY 已选中 | 点击 GROWTH 取消选中 | GROWTH 取消高亮，仅 EFFICIENCY 保持选中；页面仅显示 Profitability & Efficiency 板块 |
| TC-014 | FILTER 选项与板块对应-GROWTH | FILTER=ALL | 点击 GROWTH 选项 | 仅显示 Revenue & Growth 板块，包含 ARR Growth Rate 指标 |
| TC-015 | FILTER 选项与板块对应-EFFICIENCY | FILTER=ALL | 点击 EFFICIENCY 选项 | 仅显示 Profitability & Efficiency 板块，包含 Gross Margin 指标 |
| TC-016 | FILTER 选项与板块对应-MARGINS | FILTER=ALL | 点击 MARGINS 选项 | 仅显示 Burn & Runway 板块，包含 Monthly Net Burn Rate 和 Monthly Runway 指标 |
| TC-017 | FILTER 选项与板块对应-CAPITAL | FILTER=ALL | 点击 CAPITAL 选项 | 仅显示 Capital Efficiency 板块，包含 Rule of 40 和 Sales Efficiency Ratio 指标 |
| TC-018 | FILTER 联动-Overall Score 同步刷新 | FILTER=ALL | 点击 GROWTH 选项 | Overall Benchmark Score 重新计算，仅基于 Revenue & Growth 板块的数据 |

### 四、DATA 筛选卡片

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-019 | DATA 默认状态 | 已进入 Benchmark 页面 | 查看 DATA 筛选卡片 | Actuals 默认选中且黄色(#FFC107)点亮 |
| TC-020 | 选中 Committed Forecast | DATA=Actuals | 点击 Committed Forecast | Committed Forecast 黄色点亮，Actuals 保持选中（多选）；维度点位数量增加 |
| TC-021 | 选中 System Generated Forecast | DATA=Actuals | 点击 System Generated Forecast | System Generated Forecast 黄色点亮，Actuals 保持选中；维度点位数量增加 |
| TC-022 | DATA 全选三个选项 | DATA=Actuals | 依次点击 Committed Forecast 和 System Generated Forecast | 三个选项同时黄色点亮；进度条上维度点位数量=3×已选 BENCHMARK 数量 |
| TC-023 | 取消选中某个 DATA 选项 | DATA=Actuals+Committed Forecast 已选中 | 点击 Committed Forecast 取消选中 | Committed Forecast 取消高亮；对应维度点位消失；Overall Score 重新计算 |
| TC-024 | DATA 变更联动刷新 | DATA=Actuals, BENCHMARK=Internal Peers | 点击 Committed Forecast 选中 | Overall Score 更新；各板块分布条增加 Committed Forecast 维度；雷达图增加对应折线 |

### 五、BENCHMARK 筛选卡片

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-025 | BENCHMARK 默认状态 | 已进入 Benchmark 页面 | 查看 BENCHMARK 筛选卡片 | Internal Peers 默认选中且黄色(#FFC107)点亮 |
| TC-026 | 选中 KeyBanc | BENCHMARK=Internal Peers | 点击 KeyBanc | KeyBanc 黄色点亮，Internal Peers 保持选中；维度点位数量增加 |
| TC-027 | 全选四个 BENCHMARK | BENCHMARK=Internal Peers | 依次点击 KeyBanc、High Alpha、Benchmark.it | 四个选项全部黄色点亮；进度条上维度点位数量=已选 DATA 数量×4 |
| TC-028 | 取消选中某个 BENCHMARK | BENCHMARK=Internal Peers+KeyBanc 已选中 | 点击 KeyBanc 取消选中 | KeyBanc 取消高亮；对应维度点位消失；Overall Score 重新计算 |
| TC-029 | BENCHMARK 变更联动刷新 | DATA=Actuals, BENCHMARK=Internal Peers | 点击 High Alpha 选中 | Overall Score 更新；各板块分布条增加 High Alpha 维度；雷达图增加对应折线 |
| TC-030 | 最大维度组合验证 | DATA 全选三项，BENCHMARK 全选四项 | 查看 Overall Score 进度条 | 显示最多 12 个维度点位（3×4=12），各点位颜色与图例一致 |

### 六、Data-Benchmark 展示排序

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-031 | 分布条排序验证 | DATA=Actuals+Committed Forecast, BENCHMARK=Internal Peers+KeyBanc, VIEW=Snapshot | 展开任一板块查看指标分布条排序 | 排序为：Internal Peers-Actuals → Internal Peers-Committed Forecast → KeyBanc-Actuals → KeyBanc-Committed Forecast（Benchmark 优先） |
| TC-032 | Trend 折线图图例排序 | DATA=Actuals+Committed Forecast, BENCHMARK=Internal Peers+KeyBanc, VIEW=Trend | 查看折线图图例排序 | 图例排序与 TC-031 一致：Internal Peers 优先，Data 次之 |
| TC-033 | 雷达图图例排序 | DATA=Actuals+Committed Forecast, BENCHMARK=Internal Peers+KeyBanc | 查看雷达图图例排序 | 图例排序与 TC-031 一致 |

### 七、日历选择

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-034 | 日历默认月份-手动数据 | 公司有手动 Actual 数据，最后有数据月份为 2026-02 | 进入 Benchmark 页面，查看日历选择 | 默认选中 2026-02 |
| TC-035 | 日历默认月份-自动数据15号前 | 公司有自动 Actual 数据，当前日期为月 15 号之前 | 进入 Benchmark 页面，查看日历选择 | 默认选中上上个月 |
| TC-036 | 日历默认月份-自动数据15号后 | 公司有自动 Actual 数据，当前日期为月 15 号之后 | 进入 Benchmark 页面，查看日历选择 | 默认选中上个月 |
| TC-037 | 日历默认月份-新建公司 | 公司为新建公司，无历史 Actual 数据 | 进入 Benchmark 页面，查看日历选择 | 默认选中当前日历月 |
| TC-038 | 切换日历月份联动刷新 | 已进入 Benchmark 页面，日历=2026-02 | 选择日历月份为 2026-01 | Overall Score 重新计算；各板块指标数据更新为 2026-01 的数据；雷达图重绘 |

### 八、Overall Benchmark Score Card

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-039 | Overall Score 百分位显示格式 | 已进入 Benchmark 页面，有完整数据 | 查看 Overall Benchmark Score Card | 显示百分位数值，格式为"XX%ile"（如 51%ile） |
| TC-040 | Overall Score 计算验证 | 四个板块分数分别为：Revenue & Growth=P60, Profitability & Efficiency=P50, Burn & Runway=P40, Capital Efficiency=P70 | 查看 Overall Score | 显示 55%ile（计算：(60+50+40+70)/4=55） |
| TC-041 | 进度条颜色-Bottom Quartile | Overall Score=P20 | 查看进度条颜色 | 进度条显示红色(#FF4444)，0≤20<25 属于 Bottom Quartile |
| TC-042 | 进度条颜色-Lower Middle Quartile | Overall Score=P35 | 查看进度条颜色 | 进度条显示粉色(#FF88BB)，25≤35<50 属于 Lower Middle Quartile |
| TC-043 | 进度条颜色-Upper Middle Quartile | Overall Score=P60 | 查看进度条颜色 | 进度条显示黄色(#FFBB44)，50≤60<75 属于 Upper Middle Quartile |
| TC-044 | 进度条颜色-Top Quartile | Overall Score=P80 | 查看进度条颜色 | 进度条显示绿色(#44BB44)，75≤80≤100 属于 Top Quartile |
| TC-045 | 进度条颜色-边界值25% | Overall Score=P25 | 查看进度条颜色 | 进度条显示粉色(#FF88BB)，25≤25<50 |
| TC-046 | 进度条颜色-边界值50% | Overall Score=P50 | 查看进度条颜色 | 进度条显示黄色(#FFBB44)，50≤50<75 |
| TC-047 | 进度条颜色-边界值75% | Overall Score=P75 | 查看进度条颜色 | 进度条显示绿色(#44BB44)，75≤75≤100 |
| TC-048 | 进度条颜色-边界值0% | Overall Score=P0 | 查看进度条颜色 | 进度条显示红色(#FF4444)，0≤0<25 |
| TC-049 | 进度条颜色-边界值100% | Overall Score=P100 | 查看进度条颜色 | 进度条显示绿色(#44BB44)，75≤100≤100 |
| TC-050 | 进度条超范围颜色处理 | 某维度百分位>P75 | 查看进度条颜色 | 该维度超范围部分按 P100 基准点位颜色填充（绿色） |
| TC-051 | 进度条超范围颜色-低于P25 | 某维度百分位<P25 | 查看进度条颜色 | 该维度超范围部分按 P0 基准点位颜色填充（红色） |
| TC-052 | 点位 Tooltip 验证 | DATA=Actuals, BENCHMARK=Internal Peers | 鼠标悬停 Overall Score 进度条上的点位 | Tooltip 第一行显示"Actuals - Internal Peers"，第二行显示该维度所有指标的平均百分位（如"P52"或"~P64"） |
| TC-053 | 多点位重合打包展示 | Actuals-Internal Peers 和 Committed Forecast-Internal Peers 百分位完全相同 | 鼠标悬停重合点位 | 点位外观按 Actuals-Internal Peers 显示；Tooltip 打包展示两个维度信息，按排序规则显示 |
| TC-054 | 右上角 Quartile 信息提示 | Overall Score=P80，共 6 个指标 | 查看 Overall Score Card 右上角 | 显示"6 Metrics - Top Quartile" |
| TC-055 | 右上角信息提示-含插值 | 存在使用线性插值估算的百分位 | 查看右上角提示 | 显示"Includes estimated percentiles (interpolated values used)" |
| TC-056 | 右上角信息提示-含边界值 | 存在超范围使用边界值的百分位 | 查看右上角提示 | 显示"Includes estimated percentiles (boundary values used)" |
| TC-057 | 右上角信息提示-含插值和边界值 | 同时存在插值和边界值的百分位 | 查看右上角提示 | 显示"Includes estimated percentiles (interpolated values & boundary values used)" |

### 九、指标板块-Snapshot 视图

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-058 | 四个固定板块展示 | VIEW=Snapshot, FILTER=ALL | 查看指标板块区域 | 依次显示四个板块：Revenue & Growth、Profitability & Efficiency、Burn & Runway、Capital Efficiency |
| TC-059 | 板块标题行信息 | VIEW=Snapshot, FILTER=ALL | 查看任一板块标题行 | 显示加粗的板块名称；右对齐显示板块百分位排名；显示颜色进度条 |
| TC-060 | 板块进度条不显示维度点位 | VIEW=Snapshot, FILTER=ALL | 查看板块进度条 | 进度条仅显示该板块的平均百分位颜色填充，不显示维度点位（与 Overall Score 进度条不同） |
| TC-061 | 板块分数计算验证 | Burn & Runway 板块：Monthly Net Burn Rate=P55，Monthly Runway=P45 | 查看 Burn & Runway 板块百分位 | 显示 P50（计算：(55+45)/2=50） |
| TC-062 | 板块默认展开/收起状态 | VIEW=Snapshot, FILTER=ALL | 查看板块初始状态 | 卡片（板块）默认展开，显示板块名称、百分位和进度条；板块内指标默认收起状态（每个指标仅显示一个 DATA-BENCHMARK 分布条） |
| TC-063 | 板块收起操作 | 板块当前为展开状态 | 点击板块标题 | 板块收起，仅显示板块名称、百分位和进度条；指标区域隐藏 |
| TC-064 | 板块展开操作 | 板块当前为收起状态 | 点击板块标题 | 板块展开，显示板块名称、百分位、进度条及板块下所有指标 |
| TC-065 | Show All 按钮展示 | 某指标存在多个 DATA-BENCHMARK 分布条（如 Actuals-Internal Peers 和 Actuals-KeyBanc） | 查看该指标 | 默认显示一个分布条，并显示"Show All"按钮 |
| TC-066 | 点击 Show All 展示全部分布条 | 指标显示 Show All 按钮 | 点击 Show All 按钮 | 显示该指标所有维度的分布条；按钮文字变为"Hide" |
| TC-067 | 点击 Hide 收起分布条 | 指标已展开全部分布条，按钮显示 Hide | 点击 Hide 按钮 | 分布条收起为默认单条显示；按钮文字变回"Show All" |
| TC-068 | 指标名称和实际值展示 | VIEW=Snapshot, FILTER=ALL, DATA=Actuals | 查看 Revenue & Growth 板块下的 ARR Growth Rate 指标 | 显示指标名称"ARR Growth Rate"；显示 Actual 实际值（取自 Normalization Tracing 页面对应值） |
| TC-069 | 指标分布条展示 | VIEW=Snapshot, DATA=Actuals, BENCHMARK=Internal Peers | 查看某指标的分布条 | 显示水平彩色条形图，颜色根据该指标当前维度下的百分位进度条上色（颜色规则同 Overall Score） |
| TC-070 | 百分位精确值展示 | 指标值精确匹配某百分位 | 查看该指标百分位 | 显示精确百分位，如"P45" |
| TC-071 | 百分位估算值展示 | 指标值通过线性插值估算 | 查看该指标百分位 | 显示估算百分位，如"~P64"（波浪线表示估算） |
| TC-072 | 百分位超范围展示-高于 | 指标值超出基准上限 | 查看该指标百分位 | 显示">P75"（高于最高基准值） |
| TC-073 | 百分位超范围展示-低于 | 指标值低于基准下限 | 查看该指标百分位 | 显示"<P25"（低于最低基准值） |
| TC-074 | 指标名称悬停-详情信息 | VIEW=Snapshot, BENCHMARK=Internal Peers+KeyBanc | 鼠标悬停某指标名称 | 显示 LG 指标名称和对应 LG 公式；显示各 Benchmark 对应的 Metric Name、Definition、Segment Type+Segment Value、Best Guess、Platform-Edition |
| TC-075 | 指标分布条 Tooltip | VIEW=Snapshot, DATA=Actuals, BENCHMARK=Internal Peers | 鼠标悬停某指标分布条 | Tooltip 显示：指标名称、数据类型(Actuals)、基准来源(Internal Peers)、百分位值、Peer Count |
| TC-076 | 指标无数据处理 | 某指标无 Actual 数据 | 查看该指标分布条 | 显示灰色(#CCCCCC)空白进度条；对应数据数值显示"NA" |
| TC-077 | 基准无数据处理 | 某指标在 Internal Peers 基准下无数据 | 查看该指标分布条 | 显示灰色空白进度条；进度条名称基准后面加"(N/A)"，如"Actual-Internal Peers(N/A)" |
| TC-078 | 整个板块无数据处理 | 某板块所有指标均无数据 | 查看该板块 | 板块显示"N/A"；该板块不计入 Overall Score |

### 十、指标板块-Trend 视图

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-079 | Trend 视图默认时间范围 | VIEW=Trend | 查看日历时间范围 | 默认从 closed month 往前 6 个月 |
| TC-080 | Trend 起止月份不可相同 | VIEW=Trend | 尝试将开始月份和结束月份设为同一个月 | 系统不允许选择，提示起止月份不能相同 |
| TC-081 | Trend 折线图基本结构 | VIEW=Trend, DATA=Actuals, BENCHMARK=Internal Peers | 查看某板块下的指标折线图 | 横坐标为月份（实际有数据的月份数），纵坐标为百分位 0-100%ile；显示 1 条折线 |
| TC-082 | Trend 折线图多维度 | VIEW=Trend, DATA=Actuals+Committed Forecast, BENCHMARK=Internal Peers+KeyBanc | 查看某板块下的指标折线图 | 显示 4 条折线（2×2=4）；线条颜色与 Snapshot 中颜色编码一致 |
| TC-083 | Trend 最大折线数 | VIEW=Trend, DATA 全选 3 项, BENCHMARK 全选 4 项 | 查看某指标折线图 | 最多显示 12 条折线（3×4=12） |
| TC-084 | Trend NA 百分位处理 | VIEW=Trend，某月份指标百分位为 NA | 查看该月份的折线点 | 折线点落到 P0 位置（纵坐标=0） |
| | | | 鼠标悬停该折线点 | Tooltip 显示百分位为"NA"（非 P0） |
| TC-085 | Trend 超范围处理->P75 | VIEW=Trend，某月份百分位>P75 | 查看该月份的折线点 | 折线点纵坐标落在 P100 位置 |
| TC-086 | Trend 超范围处理-<P25 | VIEW=Trend，某月份百分位<P25 | 查看该月份的折线点 | 折线点纵坐标落在 P0 位置 |
| TC-087 | Trend 悬停月份-竖向网格线 | VIEW=Trend | 鼠标悬停在折线图某月份 | 显示竖向网格线 |
| | | | 查看 Tooltip | Tooltip 显示：月份标签，及该月份所有交集点的"DATA-BENCHMARK"组合及其百分位值 |
| TC-088 | Trend 悬停折线点 | VIEW=Trend | 鼠标悬停某条折线上的点 | 该折线高亮；显示该点详细信息（月份、DATA-BENCHMARK 组合、百分位值） |
| TC-089 | Trend FILTER 行为 | VIEW=Trend, FILTER=GROWTH | 查看 Trend 视图 | 仅显示 Revenue & Growth 板块的指标折线图；其他板块不显示 |

### 十一、Metrics Summary 雷达图

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-090 | 雷达图基本结构 | 已进入 Benchmark 页面 | 查看页面底部 Metrics Summary 雷达图 | 固定六边形雷达图；中心点为 P0；同心圆分别为 P25、P50、P75、P100；6 个角度分别对应 6 个指标 |
| TC-091 | 雷达图六个指标角度 | 已进入 Benchmark 页面 | 查看雷达图各轴标签 | 6 个角度分别为：ARR Growth Rate、Gross Margin、Monthly Net Burn Rate、Monthly Runway、Rule of 40、Sales Efficiency Ratio |
| TC-092 | 雷达图 Snapshot 模式-单月数据 | VIEW=Snapshot, DATA=Actuals, BENCHMARK=Internal Peers | 查看雷达图 | 显示 1 条折线；每个角的值=选定月份该指标的百分位 |
| TC-093 | 雷达图 Trend 模式-月份平均 | VIEW=Trend, DATA=Actuals, BENCHMARK=Internal Peers, 选定 6 个月时间范围 | 查看雷达图 | 显示 1 条折线；每个角的值=该指标在所有选定月份百分位的算术平均 |
| TC-094 | 雷达图多维度线条 | DATA=Actuals+Committed Forecast, BENCHMARK=Internal Peers+KeyBanc | 查看雷达图 | 显示 4 条折线（2×2=4）；颜色与 Snapshot/Trend 中一致 |
| TC-095 | 雷达图最大线条数 | DATA 全选 3 项, BENCHMARK 全选 4 项 | 查看雷达图 | 最多显示 12 条折线 |
| TC-096 | 雷达图图例功能 | DATA=Actuals+Committed Forecast, BENCHMARK=Internal Peers | 查看雷达图图例 | 显示图例项，排序与 Data-Benchmark 展示排序一致 |
| | | | 点击图例项隐藏某条折线 | 对应折线从雷达图上消失 |
| | | | 再次点击图例项恢复 | 对应折线重新显示 |
| TC-097 | 雷达图交互-悬浮指标轴线 | DATA=Actuals, BENCHMARK=Internal Peers+KeyBanc | 鼠标悬浮雷达图某指标轴线 | Tooltip 显示该指标名称及所有 Data-Benchmark 组合的百分位详情（DATA、BENCHMARK、百分位值如 P45/~P64/>P75） |
| TC-098 | 雷达图在两种视图中均展示 | VIEW=Snapshot | 查看页面底部 | 显示 Metrics Summary 雷达图 |
| | | | 切换 VIEW 为 Trend | 页面底部仍显示 Metrics Summary 雷达图 |

### 十二、百分位计算-Internal Peer

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-099 | Internal Peer 百分位公式验证 | BENCHMARK=Internal Peers；同行 5 家公司，目标公司 ARR Growth Rate 排名第 3（升序） | 查看 ARR Growth Rate 百分位 | 显示 P50（计算：((3-1)/(5-1))×100%=50%） |
| TC-100 | 标准竞争排名-相同数值 | 同行 5 家，其中 2 家 ARR Growth Rate 相同且排名并列第 2 | 查看两家公司的百分位 | 两家公司显示相同百分位 P25（计算：((2-1)/(5-1))×100%=25%）；下一家排名为第 4 |
| TC-101 | N=1 特殊情况 | 仅目标公司 1 家（无同行） | 查看百分位 | 百分位=100（P100） |
| TC-102 | 所有同行指标完全相同 | 同行 5 家公司某指标值完全相同 | 查看该指标 | 不显示百分位；该指标不计入 Metric Summary 和 Overall Score |
| TC-103 | 正向指标升序排序验证 | 同行 4 家 ARR Growth Rate 分别为 10%、20%、30%、40%，目标公司=30% | 查看 ARR Growth Rate 百分位 | 目标公司排名第 3；百分位 P67（计算：((3-1)/(4-1))×100%≈66.7%） |
| TC-104 | Monthly Net Burn Rate 升序排序 | 同行 4 家 Monthly Net Burn Rate 分别为 -100K、-80K、-50K、-20K，目标公司=-80K | 查看 Monthly Net Burn Rate 百分位 | 目标公司排名第 2（升序排序，数值小排名靠前）；百分位 P33（计算：((2-1)/(4-1))×100%≈33.3%） |
| TC-105 | Sales Efficiency Ratio 反向指标 | 同行 4 家 Sales Efficiency Ratio 分别为 2.0、3.0、4.0、5.0，目标公司=3.0（反向指标，数值越低越好） | 查看 Sales Efficiency Ratio 百分位 | 反向指标按相应排序方式处理，目标公司得到合理百分位排名 |

### 十三、百分位计算-外部平台基准

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-106 | 精确匹配百分位 | BENCHMARK=KeyBanc；KeyBanc 提供 P25=20%, P50=35%, P75=50%；公司 Gross Margin=35% | 查看 Gross Margin 百分位 | 显示精确百分位"P50"（公司值精确等于 P50 值） |
| TC-107 | 线性插值百分位验证 | BENCHMARK=KeyBanc；P50=30%, P75=40%；公司值=35% | 查看该指标百分位 | 显示"~P63"（计算：~P=50+(75-50)×(35-30)/(40-30)=62.5，四舍五入≈63） |
| TC-108 | 线性插值-P25到P50区间 | BENCHMARK=KeyBanc；P25=10%, P50=30%；公司值=20% | 查看该指标百分位 | 显示"~P38"（计算：~P=25+(50-25)×(20-10)/(30-10)=37.5，四舍五入≈38） |
| TC-109 | 超范围->P75 | BENCHMARK=KeyBanc；P75=50%；公司值=60% | 查看该指标百分位 | 显示">P75"；汇总计算时使用 P100 |
| TC-110 | 超范围-<P25 | BENCHMARK=KeyBanc；P25=20%；公司值=10% | 查看该指标百分位 | 显示"<P25"；汇总计算时使用 P0 |
| TC-111 | 超范围详细规则->P25 | BENCHMARK=某外部平台；公司值>P25 但<P50 | 查看百分位展示和计算 | 展示">P25"；汇总计算时使用 P50 |
| TC-112 | 超范围详细规则->P50 | BENCHMARK=某外部平台；公司值>P50 但<P75 | 查看百分位展示和计算 | 展示">P50"；汇总计算时使用 P75 |
| TC-113 | 超范围详细规则-<P50 | BENCHMARK=某外部平台；公司值<P50 但>P25 | 查看百分位展示和计算 | 展示"<P50"；汇总计算时使用 P25 |
| TC-114 | 超范围详细规则-<P75 | BENCHMARK=某外部平台；公司值<P75 但>P50 | 查看百分位展示和计算 | 展示"<P75"；汇总计算时使用 P50 |
| TC-115 | P50 特殊规则-高于中位数 | BENCHMARK=某平台仅提供 P50=30%；公司值=40% | 查看该指标百分位 | 汇总计算时使用 P75 |
| TC-116 | P50 特殊规则-低于中位数 | BENCHMARK=某平台仅提供 P50=30%；公司值=20% | 查看该指标百分位 | 汇总计算时使用 P25 |
| TC-117 | P50 特殊规则-等于中位数 | BENCHMARK=某平台仅提供 P50=30%；公司值=30% | 查看该指标百分位 | 汇总计算时使用 P50 |
| TC-118 | 外部基准数据匹配-Segment | BENCHMARK=KeyBanc；Benchmark Entry 中有多个 Segment（不同年份和 ARR 范围） | 查看指标百分位 | 系统匹配正确年份（FY Period）和相同 Segment Value（ARR 范围）的百分位数据 |

### 十四、指标公式验证

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-119 | ARR Growth Rate 计算 | ARR_t=1,200,000, ARR_(t-1)=1,000,000 | 查看 ARR Growth Rate 值 | 显示 20%（计算：(1,200,000-1,000,000)/1,000,000=0.2=20%） |
| TC-120 | Gross Margin 计算 | Gross Profit=700,000, Gross Revenue=1,000,000 | 查看 Gross Margin 值 | 显示 70%（计算：700,000/1,000,000×100%=70%） |
| TC-121 | Monthly Net Burn Rate 计算 | Net Income=-200,000, Capitalized R&D=50,000 | 查看 Monthly Net Burn Rate 值 | 显示 -250,000（计算：-200,000-50,000=-250,000） |
| TC-122 | Monthly Runway 正常计算 | Cash=3,000,000, Monthly Net Burn Rate=-150,000（Cash≥0, Burn<0） | 查看 Monthly Runway 值 | 显示 20 个月（计算：-(3,000,000/(-150,000))=20） |
| TC-123 | Monthly Runway-Cash≥0,Burn>0 | Cash=1,000,000, Monthly Net Burn Rate=50,000（盈利且有现金） | 查看 Monthly Runway 值 | 显示"N/A"，排名 Top Rank |
| TC-124 | Monthly Runway-Cash≥0,Burn=0 | Cash=500,000, Monthly Net Burn Rate=0（盈亏平衡） | 查看 Monthly Runway 值 | 显示"N/A"，排名 Top Rank |
| TC-125 | Monthly Runway-Cash<0,Burn=0 | Cash=-100,000, Monthly Net Burn Rate=0 | 查看 Monthly Runway 值 | 显示"N/A"，排名 P0 |
| TC-126 | Monthly Runway-Cash<0,Burn<0 | Cash=-100,000, Monthly Net Burn Rate=-50,000 | 查看 Monthly Runway 值 | 显示"N/A"，排名 Bottom Rank |
| TC-127 | Monthly Runway-Cash=0,Burn<0 | Cash=0, Monthly Net Burn Rate=-100,000 | 查看 Monthly Runway 值 | 正常计算 Runway=0，进入排名（Runway=-(0/(-100,000))=0） |
| TC-128 | Monthly Runway-Cash=0,Burn=0 | Cash=0, Monthly Net Burn Rate=0 | 查看 Monthly Runway 值 | 显示"N/A"，排名 Top Rank |
| TC-129 | Rule of 40 计算 | Net Profit Margin=15%, MRR YoY Growth Rate=30% | 查看 Rule of 40 值 | 显示 45%（计算：(15%+30%)×100%=45%），超过 40% 理想标准 |
| TC-130 | Sales Efficiency Ratio 计算 | S&M Expenses=200,000, S&M Payroll=100,000, New MRR LTM=60,000 | 查看 Sales Efficiency Ratio 值 | 显示 5.0（计算：(200,000+100,000)/60,000=5.0） |

### 十五、同行匹配与回退

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-131 | 同行匹配五维度 | 目标公司：SaaS、Series B、权责发生制、ARR=$3M、数据质量合格 | 进入 Benchmark 页面，BENCHMARK=Internal Peers | 系统匹配同类型、同阶段、同会计方法、同 ARR 区间([$1M,$5M))、数据质量合格的同行 |
| TC-132 | ARR 区间-含前不含后 | 目标公司 ARR=$250,000（恰好等于区间边界） | 查看同行匹配 | 匹配 [$250K, $1M) 区间（包含$250K） |
| TC-133 | ARR 区间-上限不包含 | 目标公司 ARR=$999,999（接近但不到$1M） | 查看同行匹配 | 匹配 [$250K, $1M) 区间（不包含$1M） |
| TC-134 | ARR 区间-$5M到$20M含两端 | 目标公司 ARR=$20,000,000 | 查看同行匹配 | 匹配 [$5M, $20M] 区间（包含$20M） |
| TC-135 | ARR 区间-$20M以上 | 目标公司 ARR=$25,000,000 | 查看同行匹配 | 匹配 ($20M, +∞) 区间 |
| TC-136 | 同行回退-不足4个 | 同行公司仅 3 个 | 进入 Benchmark 页面 | 自动回退到 LG 平台基准（所有活跃公司）；显示 Peer Fallback 提示："Peer Fallback: No direct peer group found for this company. Benchmarking against all active companies in Looking Glass." |
| TC-137 | 同行回退-无符合条件 | 无任何符合条件的同行 | 进入 Benchmark 页面 | 同 TC-136，回退到 LG 平台基准并显示 Peer Fallback 提示 |
| TC-138 | 有效同行显示 Peer Count | 同行公司 ≥ 4 个，如 10 个 | 查看页面 | 显示"Peer Count: 10" |
| TC-139 | 排除条件-Exited 公司 | 某同行公司状态为 Exited | 查看同行计算 | 该公司不参与同行计算，不出现在 Peer Count 中 |
| TC-140 | 排除条件-Shut Down 公司 | 某同行公司状态为 Shut Down | 查看同行计算 | 该公司不参与同行计算 |
| TC-141 | 排除条件-Inactive 公司 | 某同行公司状态为 Inactive | 查看同行计算 | 该公司不参与同行计算 |
| TC-142 | 数据质量要求 | 某同行公司在 24 个月内无连续 6 个月非负 gross revenue | 查看同行匹配 | 该公司不符合数据质量要求，被排除在同行之外 |
| TC-143 | DATA 类型与同行-Committed Forecast | DATA=Committed Forecast, BENCHMARK=Internal Peers | 查看百分位 | 系统使用同行的 Committed Forecast 数据进行计算 |
| TC-144 | 同行无对应 DATA 类型数据 | DATA=Committed Forecast，某同行无 Committed Forecast 数据 | 查看百分位 | 该同行在 Committed Forecast 维度下被排除；Peer Count 可能与 Actuals 不同 |
| TC-145 | Forecast 对标外部基准 | DATA=Committed Forecast, BENCHMARK=KeyBanc | 查看百分位 | 用公司预测值与 KeyBanc 历史实际基准数据进行对标 |
| TC-146 | Forecast 内部同行-有预测数据 | DATA=Committed Forecast, BENCHMARK=Internal Peers，同行有预测数据 | 查看百分位 | 用预测 ARR 匹配同行，Forecast vs Forecast 对标 |
| TC-147 | Forecast 内部同行-无预测数据降级 | DATA=Committed Forecast, BENCHMARK=Internal Peers，无同行预测数据 | 查看百分位 | 降级到所有活跃 LG 企业的 Actual 数据进行对标 |

### 十六、权重计算与缺失处理

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-148 | 维度分数计算验证 | 维度"Actuals-Internal Peers"下 6 个指标百分位：P50、P55、P60、P65、P45、P40 | 查看该维度的 Overall Score 点位 | 显示 P53（计算：(50+55+60+65+45+40)/6≈52.5，四舍五入≈53） |
| TC-149 | 板块分数-含缺失指标 | Capital Efficiency 板块：Rule of 40=P60，Sales Efficiency Ratio 无数据 | 查看 Capital Efficiency 板块分数 | 显示 P60（仅 1 个有效指标，分母=1：60/1=60） |
| TC-150 | Overall Score-含缺失板块 | Revenue & Growth=P60, Profitability & Efficiency=P50, Burn & Runway=N/A, Capital Efficiency=P70 | 查看 Overall Score | 显示 P60（N/A 板块不计入，(60+50+70)/3=60） |
| TC-151 | 指标缺失-分母减1 | Burn & Runway 板块仅 Monthly Net Burn Rate=P55 有数据，Monthly Runway 无数据 | 查看 Burn & Runway 板块分数 | 显示 P55（分母减 1，55/1=55） |
| TC-152 | 所有板块均无数据 | 所有 6 个指标均无数据 | 查看 Overall Score | 显示"N/A" |

### 十七、新建公司处理

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-153 | 新建公司日期默认值 | 公司为新建公司，无历史 Actual 数据 | 进入 Benchmark 页面 | 日历默认选中当前日历月 |
| TC-154 | 新建公司-Actuals 不可选 | 公司为新建公司 | 查看 DATA 筛选卡片 | Actuals 选项不可选或显示为灰色 |
| TC-155 | 新建公司-仅显示 Forecast | 公司为新建公司 | 查看 DATA 筛选卡片 | 仅可选 Committed Forecast 和 System Generated Forecast |

### 十八、颜色编码与视觉一致性

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-156 | 百分位颜色-红色 | 某指标百分位=P10 | 查看该指标分布条颜色 | 红色(#FF4444)，0≤10<25 |
| TC-157 | 百分位颜色-粉色 | 某指标百分位=P35 | 查看该指标分布条颜色 | 粉色(#FF88BB)，25≤35<50 |
| TC-158 | 百分位颜色-黄色 | 某指标百分位=P60 | 查看该指标分布条颜色 | 黄色(#FFBB44)，50≤60<75 |
| TC-159 | 百分位颜色-绿色 | 某指标百分位=P85 | 查看该指标分布条颜色 | 绿色(#44BB44)，75≤85≤100 |
| TC-160 | 百分位颜色-灰色 N/A | 某指标无数据 | 查看该指标分布条颜色 | 灰色(#CCCCCC) |
| TC-161 | 选中状态颜色-VIEW/FILTER | VIEW=Snapshot, FILTER=GROWTH | 查看选中项颜色 | 选中项均为蓝色(#2196F3)点亮 |
| TC-162 | 选中状态颜色-DATA/BENCHMARK | DATA=Actuals, BENCHMARK=Internal Peers | 查看选中项颜色 | 选中项均为黄色(#FFC107)点亮 |
| TC-163 | Snapshot与Trend颜色一致性 | DATA=Actuals+Committed Forecast, BENCHMARK=Internal Peers | 记录 Snapshot 视图中各维度颜色 | 切换到 Trend 视图后，折线颜色与 Snapshot 中对应维度颜色一致 |
| TC-164 | 板块进度条颜色与Overall一致 | Revenue & Growth 板块百分位=P80 | 查看板块进度条颜色 | 绿色(#44BB44)，颜色规则与 Overall Score 进度条一致 |

### 十九、多条件联动与综合场景

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-165 | 多筛选条件同时变更 | VIEW=Snapshot, FILTER=ALL, DATA=Actuals, BENCHMARK=Internal Peers | 依次点击：Trend、GROWTH、Committed Forecast、KeyBanc | 页面切换为 Trend 视图；仅显示 Revenue & Growth 折线图；折线包含 Actuals-Internal Peers、Actuals-KeyBanc、Committed Forecast-Internal Peers、Committed Forecast-KeyBanc 四条 |
| TC-166 | 筛选变更后雷达图同步刷新 | VIEW=Snapshot, FILTER=ALL | 点击 FILTER 中 GROWTH 选项 | 雷达图数据同步更新，仅反映 Revenue & Growth 相关指标的变化 |
| TC-167 | 日历变更后全局刷新 | 日历=2026-02 | 切换日历到 2026-01 | Overall Score 更新；所有板块指标更新；雷达图重绘；所有百分位重新计算 |
| TC-168 | Forecast 预测ARR找同行 | DATA=Committed Forecast, BENCHMARK=Internal Peers | 查看同行匹配 | 使用预测 ARR（以最后一个有预测数据月份为基准）匹配同行 ARR 区间 |

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1 | 页面标题"Benchmarking"及三行说明文字 | ✅ 已覆盖 | TC-002 | |
| R2 | 导航路径 Finance → Benchmarking Tab | ✅ 已覆盖 | TC-001 | |
| R3 | VIEW 筛选卡片单选、蓝色点亮、默认 Snapshot | ✅ 已覆盖 | TC-003, TC-004, TC-005, TC-006 | |
| R4 | FILTER 多选、ALL 互斥规则、蓝色点亮 | ✅ 已覆盖 | TC-007~TC-018 | |
| R5 | DATA 多选、黄色点亮、默认 Actuals | ✅ 已覆盖 | TC-019~TC-024 | |
| R6 | BENCHMARK 多选、最多4个、黄色点亮 | ✅ 已覆盖 | TC-025~TC-030 | |
| R7 | 无同行匹配时 Peer Fallback 提示 | ✅ 已覆盖 | TC-136, TC-137 | |
| R8 | 日历选择默认值及功能 | ✅ 已覆盖 | TC-034~TC-038 | |
| R9 | Overall Score 百分位显示及计算 | ✅ 已覆盖 | TC-039, TC-040 | |
| R10 | Overall Score 进度条颜色规则 | ✅ 已覆盖 | TC-041~TC-051 | |
| R11 | 进度条点位（最多12个） | ✅ 已覆盖 | TC-030, TC-052 | |
| R12 | 点位 Tooltip 交互 | ✅ 已覆盖 | TC-052 | |
| R13 | 多点位重合打包展示 | ✅ 已覆盖 | TC-053 | |
| R14 | 右上角 Quartile 信息提示 | ✅ 已覆盖 | TC-054 | |
| R15 | 特殊计算提示文字 | ✅ 已覆盖 | TC-055, TC-056, TC-057 | |
| R16 | Snapshot 四个固定板块 | ✅ 已覆盖 | TC-058 | |
| R17 | 板块标题行信息 | ✅ 已覆盖 | TC-059 | |
| R18 | 板块进度条不显示维度点位 | ✅ 已覆盖 | TC-060 | |
| R19 | 单个指标展示（名称、实际值、分布条、百分位） | ✅ 已覆盖 | TC-068~TC-073 | |
| R20 | 指标名称悬停详情 | ✅ 已覆盖 | TC-074 | |
| R21 | 指标分布条 Tooltip | ✅ 已覆盖 | TC-075 | |
| R22 | 无数据处理（指标/基准/板块） | ✅ 已覆盖 | TC-076, TC-077, TC-078 | |
| R23 | 板块展开/收起功能 | ✅ 已覆盖 | TC-062, TC-063, TC-064 | |
| R24 | Show All/Hide 按钮 | ✅ 已覆盖 | TC-065, TC-066, TC-067 | |
| R25 | FILTER 与板块对应关系 | ✅ 已覆盖 | TC-014~TC-017 | |
| R26 | Data-Benchmark 展示排序 | ✅ 已覆盖 | TC-031, TC-032, TC-033 | |
| R27 | Trend 时间范围（不可同月，默认6个月） | ✅ 已覆盖 | TC-079, TC-080 | |
| R28 | Trend 折线图展示 | ✅ 已覆盖 | TC-081, TC-082, TC-083 | |
| R29 | Trend NA 百分位处理 | ✅ 已覆盖 | TC-084 | |
| R30 | Trend 超范围折线处理 | ✅ 已覆盖 | TC-085, TC-086 | |
| R31 | Trend 交互（网格线、Tooltip） | ✅ 已覆盖 | TC-087, TC-088 | |
| R32 | 雷达图结构 | ✅ 已覆盖 | TC-090, TC-091 | |
| R33 | 雷达图 Snapshot 模式 | ✅ 已覆盖 | TC-092 | |
| R34 | 雷达图 Trend 模式（月份平均） | ✅ 已覆盖 | TC-093 | |
| R35 | 雷达图图例（显隐控制） | ✅ 已覆盖 | TC-096 | |
| R36 | 雷达图交互（悬浮轴线） | ✅ 已覆盖 | TC-097 | |
| R37 | ARR Growth Rate 公式 | ✅ 已覆盖 | TC-119 | |
| R38 | Gross Margin 公式 | ✅ 已覆盖 | TC-120 | |
| R39 | Monthly Net Burn Rate 公式 | ✅ 已覆盖 | TC-121 | |
| R40 | Monthly Runway 公式及各 Cash/Burn 组合 | ✅ 已覆盖 | TC-122~TC-128 | |
| R41 | Rule of 40 公式 | ✅ 已覆盖 | TC-129 | |
| R42 | Sales Efficiency Ratio 公式 | ✅ 已覆盖 | TC-130 | |
| R43 | Internal Peer 百分位计算方法 | ✅ 已覆盖 | TC-099, TC-100, TC-103, TC-104 | |
| R44 | N=1 及所有同行相同的特殊情况 | ✅ 已覆盖 | TC-101, TC-102 | |
| R45 | 外部平台基准（精确/插值/超范围） | ✅ 已覆盖 | TC-106~TC-110 | |
| R46 | 超范围详细规则 | ✅ 已覆盖 | TC-111~TC-114 | |
| R47 | P50 特殊规则 | ✅ 已覆盖 | TC-115, TC-116, TC-117 | |
| R48 | 同行匹配五维度及 ARR 区间 | ✅ 已覆盖 | TC-131~TC-135, TC-142 | |
| R49 | 同行回退规则 | ✅ 已覆盖 | TC-136, TC-137, TC-138 | |
| R50 | DATA 类型与同行关系 | ✅ 已覆盖 | TC-143, TC-144, TC-145 | |
| R51 | 排除条件（Exited/Shut Down/Inactive） | ✅ 已覆盖 | TC-139, TC-140, TC-141 | |
| R52 | 板块分数和 Overall Score 计算 | ✅ 已覆盖 | TC-040, TC-061 | |
| R53 | 维度分数计算 | ✅ 已覆盖 | TC-148 | |
| R54 | 指标缺失时处理 | ✅ 已覆盖 | TC-149, TC-150, TC-151, TC-152 | |
| R55 | Forecast 内部同行基准及降级 | ✅ 已覆盖 | TC-146, TC-147, TC-168 | |
| R56 | 新建公司处理 | ✅ 已覆盖 | TC-153, TC-154, TC-155 | |
| R57 | 颜色编码规范 | ✅ 已覆盖 | TC-156~TC-164 | |
| R58 | Actual 数据默认月份规则 | ✅ 已覆盖 | TC-034, TC-035, TC-036 | |

**覆盖率：100%**（58/58 需求全部已覆盖）
