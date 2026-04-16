# 测试用例：Benchmark Portfolio Intelligence

- **需求来源**：https://github.com/WenchaoChen1/LG/blob/d8d4496c382a4489df2a1eec83f25bb0c98e5603/Functional%20documentation/Portfolio%20Intelligence/%E9%9C%80%E6%B1%82/Benchmark%20Portfolio%20Intelligence_%E9%9C%80%E6%B1%82%E6%96%87%E6%A1%A3.md
- **生成时间**：2026-04-16

---

## 需求清单

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R1 | 功能需求 | 用户从 Portfolio Intelligence 模块中点击 "Benchmarking" 标签进入 Benchmarking 页面 |
| R2 | UI 需求 | 页面顶部展示标题 "Benchmark" 和说明文字："Benchmark values are normalized for comparability. Industry calculations may differ from Looking Glass metrics. Use for directional context only." |
| R3 | 功能需求 | Companies 筛选器为多选下拉列表，必须至少选择一个公司才能展示数据；未选择时显示空状态 "To begin select a company" |
| R4 | 业务规则 | Companies 筛选器中，状态为 Exit 或 Shut down 的公司在列表中置灰且不可选择 |
| R5 | 功能需求 | Companies 筛选器选择/取消公司时，页面数据实时更新；取消全部公司则返回空状态 |
| R6 | 功能需求 | View 筛选器为单选按钮，可选 Snapshot 和 Trend，默认 Snapshot |
| R7 | 业务规则 | 切换 View 时其他筛选条件保持不变，仅改变展示方式和日期选择器数量 |
| R8 | 功能需求 | Filter（指标分类）筛选器为多选标签，可选 All/Growth/Efficiency/Margins/Capital，默认 All |
| R9 | 业务规则 | Filter 中 "All" 与其他分类选项互斥：选 All 则其他取消，选其他则 All 取消 |
| R10 | 数据需求 | Filter 各选项对应指标：Growth→ARR Growth Rate；Efficiency→Gross Margin；Margins→Monthly Net Burn Rate, Monthly Runway；Capital→Rule of 40, Sales Efficiency Ratio；All→全部6个指标 |
| R11 | 功能需求 | Data（数据类型）筛选器为多选标签，可选 Actuals/Committed Forecast/System Generated Forecast，默认 Actuals |
| R12 | 业务规则 | 若某公司无 Committed Forecast 或 System Generated Forecast 数据，该数据类型的对标值显示 "N/A" |
| R13 | 功能需求 | Benchmark 筛选器为多选复选框，可选 Internal Peers/KeyBanc/High Alpha/Benchmarkit，默认 Internal Peers |
| R14 | 功能需求 | Snapshot 视图下日期选择器为单月选择，默认当前月份 |
| R15 | 功能需求 | Trend 视图下日期选择器为月份范围选择（开始月份和结束月份），两者必须不同，默认6个月（当前月份及之前5个月） |
| R16 | UI 需求 | Snapshot 视图以表格形式按公司分组展示，每页最多十家公司，支持分页 |
| R17 | UI 需求 | Snapshot 表格行内黑色字体为 Actuals 值，紫色字体为 Committed Forecast 值，紫色带标记字体为 System Generated Forecast 值，显示行数取决于 Data 筛选器选择 |
| R18 | 业务规则 | Snapshot 表格 Benchmark 列按固定顺序展示：Internal Peers → KeyBanc → High Alpha → Benchmarkit，外部基准需显示 benchmark-edition |
| R19 | 功能需求 | Snapshot 表格 Benchmark 列 Tooltip 展示已选指标的已选数据类型的所有百分位及百分位对应的实际值 |
| R20 | 业务规则 | Overall benchmark score 为该行所有指标列百分位的算术平均值，N/A 不参与计算，显示格式如 "35%ile" |
| R21 | UI 需求 | Snapshot 表格列结构：公司名(含Logo) → Benchmark → Overall Score → 指标列(每列含百分位和实际值两小列)，指标列按固定顺序：ARR Growth Rate → Gross Margin → Monthly Net Burn Rate → Monthly Runway → Rule of 40 → Sales Efficiency Ratio |
| R22 | 业务规则 | Internal Peers 百分位计算采用 Nearest Rank 法：P_target = ((R-1)/(N-1))×100，N=1时P=P100，结果四舍五入取整 |
| R23 | 业务规则 | 同行匹配需同时满足6个维度：公司类型相同、阶段相同、会计方法相同、ARR 规模相同（5个区间）、数据质量合格、排除 Exit/Shut Down/Inactive 公司 |
| R24 | 业务规则 | 同行数据质量规则：Actual 从 closed month 往前24个月内连续6个月非负 gross revenue；Forecast 从最后有预测数据的月往前24个月内连续6个月非负 gross revenue |
| R25 | 业务规则 | 有效同行 < 3 家时回退到全平台基准，显示 Peer Fallback 提示 |
| R26 | 业务规则 | 外部基准采用线性插值法：~P = P_low + (P_high - P_low) × (d - d_low) / (d_high - d_low)，结果以 "~" 前缀表示估算 |
| R27 | 业务规则 | 外部基准超范围处理：超出范围用 ">" 或 "<" 表示（如 >P75 或 <P25），汇总计算时使用边界值 |
| R28 | 业务规则 | 外部基准百分位不齐全时的展示与计算规则：大于某百分位展示 ">" 并用下一档计算，小于某百分位展示 "<" 并用上一档计算 |
| R29 | 功能需求 | Trend 视图以折线图展示，每个指标一个卡片，卡片有展开/收起按钮（▲ ▼），默认展开 |
| R30 | UI 需求 | Trend 折线图标题格式：[Data Type] - [Benchmark Source]，如 "Actuals - Internal Peers" |
| R31 | UI 需求 | Trend 折线图 Y 轴标记 P0/P25/P50/P75/P100，X 轴显示月份标签（如 "DEC 2023"） |
| R32 | 功能需求 | Trend 折线图中每家公司使用不同颜色区分，Legend 位于图表下方，点击 Legend 可显示/隐藏对应折线 |
| R33 | 功能需求 | Trend 折线图鼠标 Hover 数据点显示所有公司在该月份的百分位值和百分位对应的数值 |
| R34 | 业务规则 | Trend 视图某公司某月无数据时展示最低点 P0 |
| R35 | 业务规则 | Trend 模式折线图展示排序：按 Benchmark 优先排序（Internal Peers → KeyBanc → High Alpha → Benchmarkit），Data 次序（Actuals → Committed Forecast → System Generated Forecast），横向排列；公司图例按字母 a-z 排序 |
| R36 | 数据需求 | 数据格式：百分位取整，货币值无缩写两位小数，有缩写单位一位小数，无缩写单位数值默认两位小数 |
| R37 | 业务规则 | 外部基准数据匹配时应对应正确年份的相同 ARR Segment Value 范围的百分位 |
| R38 | 业务规则 | 同行 ARR 规模匹配的5个区间：[$1,$250K)、[$250K,$1M)、[$1M,$5M)、[$5M,$20M]、($20M,+∞)，Actual 用历史实际 ARR，Forecast 用对应 Forecast ARR |

## 测试用例

### 一、页面导航与标题

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 导航至 Benchmarking 页面 | 已登录系统，拥有管理员权限 | 进入 Portfolio Intelligence 模块 | Portfolio Intelligence 模块加载成功 |
| | | | 找到并点击 "Benchmarking" 标签 | 进入 Benchmarking 页面，页面加载成功 |
| TC-002 | 页面标题和说明文字展示 | 已进入 Benchmarking 页面 | 查看页面顶部标题区域 | 显示标题 "Benchmark" |
| | | | 查看标题下方说明文字 | 显示 "Benchmark values are normalized for comparability. Industry calculations may differ from Looking Glass metrics. Use for directional context only." |

### 二、Companies 筛选器

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-003 | 初始空状态展示 | 已进入 Benchmarking 页面，未选择任何公司 | 查看主内容区域 | 显示空状态提示 "To begin select a company" |
| TC-004 | Companies 下拉列表展示 | 已进入 Benchmarking 页面，当前 Portfolio 下有公司 A(Active)、B(Active)、C(Exit)、D(Shut down) | 点击 Companies 筛选器打开下拉列表 | 显示 Portfolio 下所有公司列表 |
| | | | 查看公司 A 和公司 B 的状态 | 公司 A 和 B 可正常选择，未置灰 |
| | | | 查看公司 C（Exit 状态）的显示 | 公司 C 在列表中显示为置灰状态 |
| | | | 尝试点击公司 C | 无法选中公司 C |
| | | | 查看公司 D（Shut down 状态）的显示 | 公司 D 在列表中显示为置灰状态 |
| | | | 尝试点击公司 D | 无法选中公司 D |
| TC-005 | 选择单个公司后数据展示 | 已进入 Benchmarking 页面，当前为空状态 | 在 Companies 筛选器中选择公司 A | 空状态消失，页面展示公司 A 的对标数据 |
| TC-006 | 选择多个公司后数据展示 | 已选择公司 A | 在 Companies 筛选器中追加选择公司 B | 页面实时更新，展示公司 A 和公司 B 的对标数据 |
| TC-007 | 取消部分公司选择 | 已选择公司 A 和公司 B | 在 Companies 筛选器中取消选择公司 B | 页面实时更新，仅展示公司 A 的对标数据 |
| TC-008 | 取消全部公司选择回到空状态 | 已选择公司 A | 在 Companies 筛选器中取消选择公司 A | 页面返回空状态，显示 "To begin select a company" |

### 三、View 筛选器

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-009 | View 默认值验证 | 已进入 Benchmarking 页面 | 查看 View 筛选器 | Snapshot 为默认选中状态 |
| TC-010 | 切换到 Trend 视图 | VIEW=Snapshot，已选择至少一家公司 | 点击 Trend 按钮 | 页面布局切换为折线图展示，View 高亮切换到 Trend |
| | | | 查看日期选择器 | 日期选择器由单月切换为月份范围选择（显示开始月份和结束月份） |
| | | | 查看其他筛选条件（Filter/Data/Benchmark） | 其他筛选条件保持切换前的选择不变 |
| TC-011 | 从 Trend 切换回 Snapshot | VIEW=Trend，已选择至少一家公司 | 点击 Snapshot 按钮 | 页面布局切换为表格展示，View 高亮切换到 Snapshot |
| | | | 查看日期选择器 | 日期选择器由月份范围切换为单月选择 |
| | | | 查看其他筛选条件（Filter/Data/Benchmark） | 其他筛选条件保持切换前的选择不变 |

### 四、Filter（指标分类）筛选器

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-012 | Filter 默认值验证 | 已进入 Benchmarking 页面 | 查看 Filter 筛选器 | "All" 为默认选中高亮状态 |
| TC-013 | 选择 All 时的指标展示 | FILTER=All，已选择公司，VIEW=Snapshot | 查看表格指标列 | 展示全部6个指标列：ARR Growth Rate、Gross Margin、Monthly Net Burn Rate、Monthly Runway、Rule of 40、Sales Efficiency Ratio |
| TC-014 | 选择单个分类 Growth | FILTER=All | 点击 "Growth" 标签 | "All" 自动取消高亮，"Growth" 高亮选中 |
| | | | 查看表格指标列 | 仅展示 ARR Growth Rate 指标列 |
| TC-015 | 选择单个分类 Efficiency | FILTER=All | 点击 "Efficiency" 标签 | "All" 自动取消高亮，"Efficiency" 高亮选中 |
| | | | 查看表格指标列 | 仅展示 Gross Margin 指标列 |
| TC-016 | 选择单个分类 Margins | FILTER=All | 点击 "Margins" 标签 | "All" 自动取消高亮，"Margins" 高亮选中 |
| | | | 查看表格指标列 | 展示 Monthly Net Burn Rate 和 Monthly Runway 两个指标列 |
| TC-017 | 选择单个分类 Capital | FILTER=All | 点击 "Capital" 标签 | "All" 自动取消高亮，"Capital" 高亮选中 |
| | | | 查看表格指标列 | 展示 Rule of 40 和 Sales Efficiency Ratio 两个指标列 |
| TC-018 | 多选分类组合 | FILTER=Growth 已选中 | 点击 "Efficiency" 标签 | "Growth" 和 "Efficiency" 同时高亮选中，"All" 未选中 |
| | | | 查看表格指标列 | 展示 ARR Growth Rate 和 Gross Margin 两个指标列 |
| TC-019 | 选中多个分类后切回 All | FILTER=Growth 和 Efficiency 已选中 | 点击 "All" 标签 | "Growth" 和 "Efficiency" 自动取消高亮，"All" 高亮选中 |
| | | | 查看表格指标列 | 展示全部6个指标列 |
| TC-020 | 取消已选分类 | FILTER=Growth 已选中 | 再次点击 "Growth" 标签取消选中 | "Growth" 取消高亮 |
| TC-021 | 全选4个子分类等价 All | FILTER 无选中 | 依次点击 Growth、Efficiency、Margins、Capital | 4个子分类全部高亮选中 |
| | | | 查看表格指标列 | 展示全部6个指标列（等效于 All） |

### 五、Data（数据类型）筛选器

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-022 | Data 默认值验证 | 已进入 Benchmarking 页面 | 查看 Data 筛选器 | "Actuals" 为默认选中高亮状态 |
| TC-023 | 选择 Actuals 数据展示 | DATA=Actuals，已选择公司，VIEW=Snapshot | 查看表格中数据行 | 每家公司展示一行黑色字体的 Actuals 数据 |
| TC-024 | 多选 Committed Forecast | DATA=Actuals 已选中 | 点击 "Committed Forecast" 标签 | "Actuals" 和 "Committed Forecast" 同时高亮选中 |
| | | | 查看表格中数据行 | 每家公司展示两行数据：黑色字体为 Actuals，紫色字体为 Committed Forecast |
| TC-025 | 多选全部三种数据类型 | DATA=Actuals 已选中 | 依次点击 "Committed Forecast" 和 "System Generated Forecast" | 三个数据类型全部高亮选中 |
| | | | 查看表格中数据行 | 每家公司展示三行：黑色=Actuals、紫色=Committed Forecast、紫色带标记=System Generated Forecast |
| TC-026 | 取消某数据类型 | DATA=Actuals 和 Committed Forecast 已选中 | 点击 "Committed Forecast" 取消选中 | "Committed Forecast" 取消高亮，仅 "Actuals" 保持选中 |
| | | | 查看表格中数据行 | 仅展示 Actuals 数据行 |
| TC-027 | 公司无 Committed Forecast 数据时的 N/A 展示 | 公司 A 无 Committed Forecast 数据，DATA 已选 Committed Forecast | 查看公司 A 对应的 Committed Forecast 行 | 对标值显示 "N/A" |
| TC-028 | 公司无 System Generated Forecast 数据时的 N/A 展示 | 公司 A 无 System Generated Forecast 数据，DATA 已选 System Generated Forecast | 查看公司 A 对应的 System Generated Forecast 行 | 对标值显示 "N/A" |

### 六、Benchmark 筛选器

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-029 | Benchmark 默认值验证 | 已进入 Benchmarking 页面 | 查看 Benchmark 筛选器 | "Internal Peers" 为默认勾选状态 |
| TC-030 | 勾选多个 Benchmark | BENCHMARK=Internal Peers 已勾选 | 勾选 "KeyBanc" 复选框 | "Internal Peers" 和 "KeyBanc" 同时勾选 |
| | | | 查看表格 Benchmark 列 | 展示 Internal Peers 和 KeyBanc 两组对标数据 |
| TC-031 | 勾选全部 Benchmark | BENCHMARK=Internal Peers 已勾选 | 依次勾选 KeyBanc、High Alpha、Benchmarkit | 四个 Benchmark 全部勾选 |
| | | | 查看表格 Benchmark 列 | 按顺序展示：Internal Peers → KeyBanc → High Alpha → Benchmarkit |
| TC-032 | 取消勾选 Benchmark | BENCHMARK=Internal Peers 和 KeyBanc 已勾选 | 取消勾选 "Internal Peers" | 仅 "KeyBanc" 保持勾选 |
| | | | 查看表格 Benchmark 列 | 仅展示 KeyBanc 对标数据 |
| TC-033 | 外部基准显示 benchmark-edition | BENCHMARK=KeyBanc 已勾选，VIEW=Snapshot | 查看表格 Benchmark 列中 KeyBanc 行 | 显示 KeyBanc 对标数据及其 benchmark-edition 信息 |

### 七、日期选择器

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-034 | Snapshot 日期选择器默认值 | VIEW=Snapshot | 查看日期选择器 | 显示为单月选择器，默认选中当前月份（2026年4月） |
| TC-035 | Snapshot 切换月份 | VIEW=Snapshot，日期为当前月份 | 在日期选择器中选择上个月（2026年3月） | 日期切换为2026年3月，页面数据刷新为该月数据 |
| TC-036 | Trend 日期选择器默认值 | VIEW=Trend | 查看日期选择器 | 显示为两个月份选择器（开始月份和结束月份），默认范围为2025年11月至2026年4月（共6个月） |
| TC-037 | Trend 修改日期范围 | VIEW=Trend，日期默认 | 将开始月份改为2025年8月 | 日期范围更新为2025年8月至2026年4月，折线图数据刷新 |
| TC-038 | Trend 开始和结束月份不能相同 | VIEW=Trend | 将开始月份和结束月份设为同一月（2026年4月） | 系统阻止设置或提示错误，开始月份和结束月份必须不同 |
| TC-039 | 视图切换时日期选择器联动 | VIEW=Snapshot，日期为2026年3月 | 切换到 Trend 视图 | 日期选择器变为月份范围选择，默认显示6个月范围 |
| | | | 切换回 Snapshot 视图 | 日期选择器恢复为单月选择 |

### 八、Snapshot 视图 - 表格结构

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-040 | 表格列结构验证 | VIEW=Snapshot，FILTER=All，已选公司 A，BENCHMARK=Internal Peers | 查看表格列头 | 列顺序为：公司名 → Benchmark → Overall Score → ARR Growth Rate → Gross Margin → Monthly Net Burn Rate → Monthly Runway → Rule of 40 → Sales Efficiency Ratio |
| | | | 查看指标列内部 | 每个指标列包含百分位和实际值两个子列 |
| TC-041 | 公司名列含 Logo | VIEW=Snapshot，已选公司 A | 查看表格第一列 | 显示公司名称及其 Logo |
| TC-042 | 表格分页 - 不足10家 | VIEW=Snapshot，已选5家公司 | 查看表格 | 5家公司全部显示在一页内，无分页控件或分页控件显示为第1页 |
| TC-043 | 表格分页 - 恰好10家 | VIEW=Snapshot，已选10家公司 | 查看表格 | 10家公司全部显示在一页内 |
| TC-044 | 表格分页 - 超过10家 | VIEW=Snapshot，已选15家公司 | 查看表格第一页 | 第一页展示10家公司 |
| | | | 点击下一页 | 第二页展示剩余5家公司 |
| TC-045 | Actuals/Committed/System 字体颜色区分 | VIEW=Snapshot，DATA=Actuals+Committed Forecast+System Generated Forecast | 查看表格中某公司的数据行 | Actuals 行为黑色字体，Committed Forecast 行为紫色字体，System Generated Forecast 行为紫色带标记字体 |
| TC-046 | Benchmark 列展示顺序 | VIEW=Snapshot，BENCHMARK=全部四个已勾选 | 查看某公司的 Benchmark 列 | 按顺序展示：Internal Peers → KeyBanc → High Alpha → Benchmarkit |
| TC-047 | Benchmark 列 Tooltip 内容 | VIEW=Snapshot，FILTER=All，DATA=Actuals+Committed Forecast，BENCHMARK=Internal Peers | 将鼠标悬停在某公司的 Internal Peers Benchmark 列上 | 显示 Tooltip，包含所有6个指标名称，以及每个指标对应 Actuals 和 Committed Forecast 的百分位和百分位实际值 |
| TC-048 | 指标列按固定顺序展示 | VIEW=Snapshot，FILTER=All | 查看表格指标列顺序 | 按顺序展示：ARR Growth Rate → Gross Margin → Monthly Net Burn Rate → Monthly Runway → Rule of 40 → Sales Efficiency Ratio |

### 九、Overall Benchmark Score 计算

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-049 | Overall Score 正常计算 | VIEW=Snapshot，FILTER=All，公司 A 各指标百分位分别为：ARR Growth Rate=P60, Gross Margin=P40, Net Burn Rate=P50, Monthly Runway=P70, Rule of 40=P30, Sales Efficiency=P50 | 查看公司 A 的 Overall benchmark score | 显示 "50%ile"（计算：(60+40+50+70+30+50)/6=50） |
| TC-050 | Overall Score 含 N/A 时排除计算 | VIEW=Snapshot，FILTER=All，公司 A 各指标百分位为：P60, P40, N/A, P70, N/A, P50 | 查看公司 A 的 Overall benchmark score | 显示 "55%ile"（计算：(60+40+70+50)/4=55，N/A 不参与计算） |
| TC-051 | Overall Score 全部 N/A | VIEW=Snapshot，FILTER=All，公司 A 所有指标百分位均为 N/A | 查看公司 A 的 Overall benchmark score | 显示 "N/A"（无有效百分位参与计算） |
| TC-052 | Overall Score 仅选部分指标 | VIEW=Snapshot，FILTER=Growth+Efficiency，公司 A：ARR Growth Rate=P80, Gross Margin=P60 | 查看公司 A 的 Overall benchmark score | 显示 "70%ile"（计算：(80+60)/2=70） |
| TC-053 | Overall Score 显示格式 | VIEW=Snapshot，公司 A Overall Score 计算结果为 35 | 查看公司 A 的 Overall benchmark score 显示 | 显示 "35%ile" |

### 十、Internal Peers 百分位计算（Nearest Rank 法）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-054 | 正常百分位计算 - 5家同行 | BENCHMARK=Internal Peers，某指标同行5家公司排序后值为[10, 20, 30, 40, 50]，公司 A 值=30，排名 R=3 | 查看公司 A 该指标的百分位 | 显示 P50（计算：P=((3-1)/(5-1))×100=50） |
| TC-055 | 百分位计算 - 排名第1（最低） | BENCHMARK=Internal Peers，同行5家，公司 A 值最低排名 R=1 | 查看公司 A 该指标的百分位 | 显示 P0（计算：P=((1-1)/(5-1))×100=0） |
| TC-056 | 百分位计算 - 排名最高 | BENCHMARK=Internal Peers，同行5家，公司 A 值最高排名 R=5 | 查看公司 A 该指标的百分位 | 显示 P100（计算：P=((5-1)/(5-1))×100=100） |
| TC-057 | 百分位计算 - 四舍五入 | BENCHMARK=Internal Peers，同行6家，公司 A 排名 R=2 | 查看公司 A 该指标的百分位 | 显示 P20（计算：P=((2-1)/(6-1))×100=20） |
| TC-058 | 百分位计算 - 需四舍五入取整 | BENCHMARK=Internal Peers，同行7家，公司 A 排名 R=3 | 查看公司 A 该指标的百分位 | 显示 P33（计算：P=((3-1)/(7-1))×100=33.33，四舍五入=33） |
| TC-059 | 百分位计算 - N=1（仅自身） | BENCHMARK=Internal Peers，同行仅1家公司 | 查看公司 A 该指标的百分位 | 显示 P100（N=1时，P=P100） |
| TC-060 | 根据百分位反算排名 | BENCHMARK=Internal Peers，同行10家，目标百分位 P=25 | 验证 P25 对应的值 | R=((25×(10-1))/100)+1=3.25，四舍五入=3，取排序列表第3位的值 |
| TC-061 | 反算排名 - P50 | BENCHMARK=Internal Peers，同行10家，目标百分位 P=50 | 验证 P50 对应的值 | R=((50×9)/100)+1=5.5，四舍五入=6，取排序列表第6位的值 |
| TC-062 | 反算排名 - P75 | BENCHMARK=Internal Peers，同行10家，目标百分位 P=75 | 验证 P75 对应的值 | R=((75×9)/100)+1=7.75，四舍五入=8，取排序列表第8位的值 |

### 十一、同行匹配规则

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-063 | 使用绑定同行组 | 公司 A 在 Peer Group Management 中已绑定有效同行组（含公司 B、C、D） | 查看公司 A 的 Internal Peers 对标数据 | 使用绑定的同行组数据（公司 B、C、D）进行计算 |
| TC-064 | 绑定同行组无效时系统自动匹配 | 公司 A 绑定的同行组无效 | 查看公司 A 的 Internal Peers 对标数据 | 系统自动按6维度匹配规则寻找同行 |
| TC-065 | 无绑定时系统自动匹配 | 公司 A 未绑定同行组 | 查看公司 A 的 Internal Peers 对标数据 | 系统自动按6维度匹配规则寻找同行 |
| TC-066 | 匹配维度 - 公司类型相同 | 公司 A Type=SaaS，系统自动匹配 | 查看匹配的同行列表 | 仅包含 Type=SaaS 的公司，不含其他类型 |
| TC-067 | 匹配维度 - 公司阶段相同 | 公司 A Stage=Growth，系统自动匹配 | 查看匹配的同行列表 | 仅包含 Stage=Growth 的公司 |
| TC-068 | 匹配维度 - 会计方法相同 | 公司 A 会计方法=权责发生制，系统自动匹配 | 查看匹配的同行列表 | 仅包含会计方法=权责发生制的公司 |
| TC-069 | ARR 区间匹配 - [$1, $250K) | 公司 A 当月 ARR=$100K，DATA=Actuals | 查看匹配的同行列表 | 仅包含 ARR 在 [$1, $250K) 范围内的公司 |
| TC-070 | ARR 区间边界 - $250K 归属 | 公司 A 当月 ARR=$250K | 查看匹配的同行列表 | 匹配 [$250K, $1M) 区间的同行（$250K 包含在此区间） |
| TC-071 | ARR 区间边界 - $1M 归属 | 公司 A 当月 ARR=$1M | 查看匹配的同行列表 | 匹配 [$1M, $5M) 区间的同行（$1M 包含在此区间） |
| TC-072 | ARR 区间边界 - $5M 归属 | 公司 A 当月 ARR=$5M | 查看匹配的同行列表 | 匹配 [$5M, $20M] 区间的同行（$5M 包含在此区间） |
| TC-073 | ARR 区间边界 - $20M 归属 | 公司 A 当月 ARR=$20M | 查看匹配的同行列表 | 匹配 [$5M, $20M] 区间的同行（$20M 包含在此区间） |
| TC-074 | ARR 区间 - $20M 以上 | 公司 A 当月 ARR=$25M | 查看匹配的同行列表 | 匹配 ($20M, +∞) 区间的同行 |
| TC-075 | ARR 数据来源 - Forecast 用对应 Forecast ARR | DATA=Committed Forecast，公司 A Committed Forecast ARR=$3M | 查看匹配的同行列表 | 按 Committed Forecast ARR 值 $3M 匹配 [$1M, $5M) 区间 |
| TC-076 | 排除 Exit 状态公司 | 同行候选中有 Exit 状态公司 X | 查看匹配的同行列表 | 公司 X 不在同行列表中 |
| TC-077 | 排除 Shut Down 状态公司 | 同行候选中有 Shut Down 状态公司 Y | 查看匹配的同行列表 | 公司 Y 不在同行列表中 |
| TC-078 | 排除 Inactive 状态公司 | 同行候选中有 Inactive 状态公司 Z | 查看匹配的同行列表 | 公司 Z 不在同行列表中 |
| TC-079 | 数据质量 - Actual 有效（连续6月非负 gross revenue） | DATA=Actuals，closed month=2026-04，某同行公司2024年5月至2026年4月范围内有连续6个月非负 gross revenue | 验证该同行公司是否纳入计算 | 该公司数据有效，纳入同行计算 |
| TC-080 | 数据质量 - Actual 无效（无连续6月非负） | DATA=Actuals，closed month=2026-04，某同行公司在24个月内无任何连续6个月非负 gross revenue | 验证该同行公司是否纳入计算 | 该公司数据无效，排除在同行计算外 |
| TC-081 | 数据质量 - Forecast 有效 | DATA=Committed Forecast，某同行公司最后有预测数据的月往前24个月内有连续6个月非负 gross revenue | 验证该同行公司是否纳入计算 | 该公司数据有效，纳入同行计算 |
| TC-082 | 有效同行不足3家 - Peer Fallback | 系统自动匹配后仅找到2家有效同行 | 查看公司 A 的 Internal Peers 对标数据 | 回退到全平台基准数据，页面显示 "Peer Fallback" 提示 |
| TC-083 | 有效同行恰好3家 | 系统自动匹配后找到恰好3家有效同行 | 查看公司 A 的 Internal Peers 对标数据 | 使用3家同行数据正常计算百分位，不触发 Peer Fallback |

### 十二、外部基准百分位计算（线性插值法）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-084 | 线性插值 - 值在 P50 和 P75 之间 | BENCHMARK=KeyBanc，某指标 P50=30%, P75=40%，公司 A 实际值=35% | 查看公司 A 该指标的百分位 | 显示 "~P63"（计算：~P=50+(75-50)×(35-30)/(40-30)=62.5，四舍五入=63，波浪线表示估算） |
| TC-085 | 线性插值 - 值在 P25 和 P50 之间 | BENCHMARK=KeyBanc，某指标 P25=10%, P50=30%，公司 A 实际值=20% | 查看公司 A 该指标的百分位 | 显示 "~P38"（计算：~P=25+(50-25)×(20-10)/(30-10)=37.5，四舍五入=38） |
| TC-086 | 精确匹配百分位 | BENCHMARK=KeyBanc，某指标 P50=30%，公司 A 实际值=30% | 查看公司 A 该指标的百分位 | 显示 "P50"（精确匹配，无波浪线） |
| TC-087 | 精确匹配 P25 | BENCHMARK=High Alpha，某指标 P25=15%，公司 A 实际值=15% | 查看公司 A 该指标的百分位 | 显示 "P25" |
| TC-088 | 精确匹配 P75 | BENCHMARK=Benchmarkit，某指标 P75=60%，公司 A 实际值=60% | 查看公司 A 该指标的百分位 | 显示 "P75" |
| TC-089 | 超范围 - 大于 P75 | BENCHMARK=KeyBanc，某指标 P75=40%，公司 A 实际值=50% | 查看公司 A 该指标的百分位 | 显示 ">P75" |
| TC-090 | 超范围 - 小于 P25 | BENCHMARK=KeyBanc，某指标 P25=10%，公司 A 实际值=5% | 查看公司 A 该指标的百分位 | 显示 "<P25" |
| TC-091 | 超范围值在 Overall Score 中用边界值计算 | BENCHMARK=KeyBanc，某公司两个指标百分位分别为 >P75 和 P50 | 查看该公司 Overall benchmark score | 使用 P75（边界值）和 P50 计算平均值，显示 "63%ile"（计算：(75+50)/2=62.5，四舍五入=63） |
| TC-092 | 百分位不齐全 - 仅有 P25 且大于 P25 | BENCHMARK=KeyBanc，某指标仅有 P25=20%，公司 A 值=30% | 查看公司 A 该指标的百分位 | 显示 ">P25"，计算时用 P50 |
| TC-093 | 百分位不齐全 - 仅有 P50 且大于 P50 | BENCHMARK=KeyBanc，某指标仅有 P50=30%，公司 A 值=40% | 查看公司 A 该指标的百分位 | 显示 ">P50"，计算时用 P75 |
| TC-094 | 百分位不齐全 - 仅有 P75 且大于 P75 | BENCHMARK=KeyBanc，某指标仅有 P75=50%，公司 A 值=60% | 查看公司 A 该指标的百分位 | 显示 ">P75"，计算时用 P100 |
| TC-095 | 百分位不齐全 - 仅有 P25 且小于 P25 | BENCHMARK=KeyBanc，某指标仅有 P25=20%，公司 A 值=10% | 查看公司 A 该指标的百分位 | 显示 "<P25"，计算时用 P0 |
| TC-096 | 百分位不齐全 - 仅有 P50 且小于 P50 | BENCHMARK=KeyBanc，某指标仅有 P50=30%，公司 A 值=20% | 查看公司 A 该指标的百分位 | 显示 "<P50"，计算时用 P25 |
| TC-097 | 百分位不齐全 - 仅有 P75 且小于 P75 | BENCHMARK=KeyBanc，某指标仅有 P75=50%，公司 A 值=40% | 查看公司 A 该指标的百分位 | 显示 "<P75"，计算时用 P50 |
| TC-098 | 外部基准匹配正确年份和 ARR 区间 | BENCHMARK=KeyBanc，公司 A ARR 在 [$1M,$5M) 区间，查看2025年数据 | 查看公司 A 的 KeyBanc 百分位 | 使用 KeyBanc 数据中 FY=2025、Segment Value 为 $1M-$5M 范围的百分位数据进行匹配 |

### 十三、Trend 视图 - 折线图结构

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-099 | 每个指标一个卡片 | VIEW=Trend，FILTER=All，已选公司 | 查看 Trend 视图主内容区 | 展示6个指标卡片：ARR Growth Rate、Gross Margin、Monthly Net Burn Rate、Monthly Runway、Rule of 40、Sales Efficiency Ratio |
| TC-100 | 卡片默认展开 | VIEW=Trend | 查看各指标卡片的展开/收起状态 | 所有卡片默认展开，可见折线图内容 |
| TC-101 | 卡片收起操作 | VIEW=Trend，卡片默认展开 | 点击某指标卡片右上角的 ▲ 收起按钮 | 该卡片收起，折线图隐藏，仅显示卡片标题 |
| TC-102 | 卡片展开操作 | 某指标卡片已收起 | 点击该卡片右上角的 ▼ 展开按钮 | 该卡片展开，折线图重新显示 |
| TC-103 | 折线图标题格式 | VIEW=Trend，DATA=Actuals，BENCHMARK=Internal Peers | 查看折线图标题 | 显示 "Actuals - Internal Peers" |
| TC-104 | 多 Data-Benchmark 组合标题 | VIEW=Trend，DATA=Actuals+Committed Forecast，BENCHMARK=Internal Peers+KeyBanc | 查看各折线图标题 | 分别展示：Actuals - Internal Peers、Committed Forecast - Internal Peers、Actuals - KeyBanc、Committed Forecast - KeyBanc |
| TC-105 | Y 轴刻度 | VIEW=Trend | 查看折线图 Y 轴 | 标记 P0、P25、P50、P75、P100 |
| TC-106 | X 轴月份标签 | VIEW=Trend，日期范围为2025年11月至2026年4月 | 查看折线图 X 轴 | 显示月份标签：NOV 2025、DEC 2025、JAN 2026、FEB 2026、MAR 2026、APR 2026 |

### 十四、Trend 视图 - 折线与交互

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-107 | 不同公司使用不同颜色 | VIEW=Trend，已选公司 A 和公司 B | 查看折线图 | 公司 A 和公司 B 使用不同颜色的折线 |
| TC-108 | Legend 展示 | VIEW=Trend，已选公司 A 和公司 B | 查看折线图下方 Legend | 显示公司 A 和公司 B 的名称及对应颜色标识 |
| TC-109 | Legend 点击隐藏折线 | VIEW=Trend，已选公司 A 和公司 B | 点击 Legend 中公司 A 的图例项 | 公司 A 的折线隐藏，仅显示公司 B 的折线 |
| TC-110 | Legend 点击恢复折线 | 公司 A 折线已隐藏 | 再次点击 Legend 中公司 A 的图例项 | 公司 A 的折线重新显示 |
| TC-111 | Hover 数据点显示详情 | VIEW=Trend，已选公司 A 和公司 B | 鼠标悬停在某月份的数据点上 | 显示 Tooltip，包含所有公司在该月份的百分位值和百分位对应的数值 |
| TC-112 | 数据缺失时展示 P0 | VIEW=Trend，公司 A 在2026年2月无数据 | 查看公司 A 在2026年2月的折线位置 | 数据点显示在 Y 轴最低点 P0 位置 |
| TC-113 | 公司图例按字母排序 | VIEW=Trend，已选 Company C、Company A、Company B | 查看 Legend 排序 | 按字母 a-z 排序：Company A、Company B、Company C |

### 十五、Trend 视图 - 展示排序

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-114 | Benchmark 优先排序 | VIEW=Trend，DATA=Actuals+Committed Forecast，BENCHMARK=Internal Peers+KeyBanc | 查看折线图排列顺序 | 先展示 Internal Peers 的所有 Data 图表，再展示 KeyBanc 的所有 Data 图表。具体顺序：Actuals-Internal Peers → Committed Forecast-Internal Peers → Actuals-KeyBanc → Committed Forecast-KeyBanc |
| TC-115 | 全部 Benchmark 和 Data 组合排序 | VIEW=Trend，DATA=全部三种，BENCHMARK=全部四个 | 查看折线图排列顺序 | 横向排列，依次为：Actuals-Internal Peers → Committed Forecast-Internal Peers → System Generated Forecast-Internal Peers → Actuals-KeyBanc → ... → System Generated Forecast-Benchmarkit（共12个图表） |
| TC-116 | 横向排列换行 | VIEW=Trend，DATA=全部三种，BENCHMARK=全部四个 | 查看折线图布局 | 图表横向排列，排满一行后换到下一行 |

### 十六、数据格式

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-117 | 百分位取整 | 计算结果百分位为 62.5 | 查看百分位显示 | 显示为 P63（四舍五入取整） |
| TC-118 | 货币值无缩写两位小数 | 某指标实际值为 $1234567.891 且未使用缩写 | 查看数值显示 | 显示为 $1234567.89（两位小数） |
| TC-119 | 货币值有缩写一位小数 | 某指标实际值为 $1,234,567 且使用缩写显示 | 查看数值显示 | 显示为 $1.2M（一位小数） |
| TC-120 | 无缩写单位数值两位小数 | 某指标百分比值为 33.333% | 查看数值显示 | 显示为 33.33%（两位小数） |

### 十七、筛选联动与实时刷新

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-121 | 变更 Companies 后数据刷新 | VIEW=Snapshot，已选公司 A 展示数据 | 在 Companies 筛选器中追加选择公司 B | 表格实时更新，新增公司 B 的数据行 |
| TC-122 | 变更 Filter 后指标列刷新 | VIEW=Snapshot，FILTER=All（6列指标） | 将 Filter 切换为 Growth | 表格指标列实时更新为仅 ARR Growth Rate 一列 |
| TC-123 | 变更 Data 后数据行刷新 | VIEW=Snapshot，DATA=Actuals | 追加选择 Committed Forecast | 表格实时更新，每家公司新增 Committed Forecast 数据行 |
| TC-124 | 变更 Benchmark 后对标组刷新 | VIEW=Snapshot，BENCHMARK=Internal Peers | 追加勾选 KeyBanc | 表格实时更新，每家公司新增 KeyBanc 对标数据 |
| TC-125 | 变更日期后数据刷新 | VIEW=Snapshot，日期为2026年4月 | 切换日期为2026年3月 | 表格数据实时更新为2026年3月的对标数据 |
| TC-126 | Trend 视图下变更 Filter 后图表刷新 | VIEW=Trend，FILTER=All | 将 Filter 切换为 Growth | 折线图实时更新，仅展示 ARR Growth Rate 指标卡片 |
| TC-127 | 多筛选条件同时变更 | VIEW=Snapshot，FILTER=All，BENCHMARK=Internal Peers | 先切换 Filter 为 Growth，再勾选 KeyBanc | 每次变更后表格实时刷新，最终展示 Growth 指标在 Internal Peers 和 KeyBanc 下的对标数据 |

---

## 需求追溯矩阵

| 需求编号 | 需求描述 | 覆盖状态 | 对应测试用例 | 备注 |
|---------|---------|---------|------------|------|
| R1 | 导航至 Benchmarking 页面 | ✅ 已覆盖 | TC-001 | |
| R2 | 页面标题和说明文字展示 | ✅ 已覆盖 | TC-002 | |
| R3 | Companies 筛选器多选、空状态 | ✅ 已覆盖 | TC-003, TC-004, TC-005 | |
| R4 | Exit/Shut down 公司置灰不可选 | ✅ 已覆盖 | TC-004 | |
| R5 | Companies 选择/取消实时更新 | ✅ 已覆盖 | TC-005, TC-006, TC-007, TC-008, TC-121 | |
| R6 | View 筛选器单选，默认 Snapshot | ✅ 已覆盖 | TC-009, TC-010, TC-011 | |
| R7 | 切换 View 保持筛选条件，日期选择器适配 | ✅ 已覆盖 | TC-010, TC-011, TC-039 | |
| R8 | Filter 多选标签，默认 All | ✅ 已覆盖 | TC-012, TC-013 | |
| R9 | Filter All 与其他互斥 | ✅ 已覆盖 | TC-014, TC-019, TC-020, TC-021 | |
| R10 | Filter 各选项对应指标映射 | ✅ 已覆盖 | TC-013, TC-014, TC-015, TC-016, TC-017, TC-018 | |
| R11 | Data 多选标签，默认 Actuals | ✅ 已覆盖 | TC-022, TC-023, TC-024, TC-025, TC-026 | |
| R12 | 公司无 Forecast 数据显示 N/A | ✅ 已覆盖 | TC-027, TC-028 | |
| R13 | Benchmark 多选复选框，默认 Internal Peers | ✅ 已覆盖 | TC-029, TC-030, TC-031, TC-032 | |
| R14 | Snapshot 日期选择器单月，默认当前月 | ✅ 已覆盖 | TC-034, TC-035 | |
| R15 | Trend 日期范围选择，不同月，默认6个月 | ✅ 已覆盖 | TC-036, TC-037, TC-038 | |
| R16 | Snapshot 表格分页，每页最多10家 | ✅ 已覆盖 | TC-042, TC-043, TC-044 | |
| R17 | Actuals/Committed/System 字体颜色区分 | ✅ 已覆盖 | TC-045 | |
| R18 | Benchmark 列展示顺序及 edition | ✅ 已覆盖 | TC-046, TC-033 | |
| R19 | Benchmark 列 Tooltip 内容 | ✅ 已覆盖 | TC-047 | |
| R20 | Overall Score 算术平均，N/A 排除 | ✅ 已覆盖 | TC-049, TC-050, TC-051, TC-052, TC-053 | |
| R21 | 表格列结构与指标列顺序 | ✅ 已覆盖 | TC-040, TC-041, TC-048 | |
| R22 | Internal Peers Nearest Rank 百分位计算 | ✅ 已覆盖 | TC-054, TC-055, TC-056, TC-057, TC-058, TC-059, TC-060, TC-061, TC-062 | |
| R23 | 同行匹配6维度规则 | ✅ 已覆盖 | TC-063, TC-064, TC-065, TC-066, TC-067, TC-068, TC-069, TC-076, TC-077, TC-078 | |
| R24 | 同行数据质量规则 | ✅ 已覆盖 | TC-079, TC-080, TC-081 | |
| R25 | 有效同行 < 3 家 Peer Fallback | ✅ 已覆盖 | TC-082, TC-083 | |
| R26 | 外部基准线性插值计算 | ✅ 已覆盖 | TC-084, TC-085, TC-086, TC-087, TC-088 | |
| R27 | 外部基准超范围处理 | ✅ 已覆盖 | TC-089, TC-090, TC-091 | |
| R28 | 外部基准百分位不齐全时处理 | ✅ 已覆盖 | TC-092, TC-093, TC-094, TC-095, TC-096, TC-097 | |
| R29 | Trend 指标卡片展开/收起 | ✅ 已覆盖 | TC-099, TC-100, TC-101, TC-102 | |
| R30 | Trend 折线图标题格式 | ✅ 已覆盖 | TC-103, TC-104 | |
| R31 | Trend 折线图坐标轴 | ✅ 已覆盖 | TC-105, TC-106 | |
| R32 | 折线颜色与 Legend | ✅ 已覆盖 | TC-107, TC-108, TC-109, TC-110 | |
| R33 | Hover 数据点显示详情 | ✅ 已覆盖 | TC-111 | |
| R34 | 数据缺失展示 P0 | ✅ 已覆盖 | TC-112 | |
| R35 | Trend 展示排序规则 | ✅ 已覆盖 | TC-114, TC-115, TC-116, TC-113 | |
| R36 | 数据格式规则 | ✅ 已覆盖 | TC-117, TC-118, TC-119, TC-120 | |
| R37 | 外部基准匹配正确年份和 ARR 区间 | ✅ 已覆盖 | TC-098 | |
| R38 | ARR 规模5个区间及数据来源 | ✅ 已覆盖 | TC-069, TC-070, TC-071, TC-072, TC-073, TC-074, TC-075 | |

**覆盖率：100%**（38/38 需求已覆盖）
