# Benchmark 基准测试功能需求文档							
							
**文档版本：** 2.0（已审核更新）							
**更新日期：** 2026年3月25日							
**产品模块：** Finance（财务模块）							
**功能名称：** Benchmark（基准测试）							
							
---							
							
## 一、产品概述							
							
### 1.1 功能定义							
Benchmark是Looking Glass（LG）系统中的一个核心财务分析功能，用于帮助用户将其财务指标与行业同行和第三方基准平台进行对标比较，提供百分位排名、趋势分析和综合评分等多维度的对标洞察。							
							
### 1.2 产品目标							
	用于帮助用户将其财务指标与行业同行和第三方基准平台进行对标比较，提供百分位排名、趋势分析和综合评分等多维度的对标洞察。					
							
---							
							
## 二、功能架构							
							
### 2.1 系统位置							
**导航路径：** Finance 模块 → Benchmarking Tab							
**同级菜单：** Overview、Financial Statements、Performance							
							
### 2.2 主要功能板块							
1. **筛选条件区域** - 用户交互入口							
2. **Overall Benchmark Score Card** - 综合评分展示							
3. **指标板块Card** - 分类指标展示（Snapshot 和 Trend 视图）							
4. **Metrics Summary** - 雷达图汇总							
							
---							
							
## 三、完整业务流程							
							
### 3.1 用户使用流程							
							
```							
用户进入Benchmark页面							
    ↓							
查看默认参数配置							
    ├─ 时间范围：最后一个有Actual数据的月份（新建公司则为当前月）							手动情况是最后一个有数据月份，自动情况下，15号之前用上上个月，15号之后用上个月
"    ├─ 默认筛选：VIEW=Snapshot, FILTER=ALL, DATA=Actuals, BENCHMARK=Internal Peers"							
    └─ 若无同行，自动回退到LG平台基准							
    ↓							
选择筛选条件							
    ├─ VIEW：选择 Snapshot（快照）或 Trend（趋势）							
    ├─ FILTER：选择指标分类（ALL、GROWTH、EFFICIENCY、MARGINS、CAPITAL）							
    │         ALL与其他选项互斥，选中ALL后如果选择其他选项，ALL就自动取消勾选，其他选项可同时选中							
    ├─ DATA：选择数据类型（Actuals、Committed Forecast、System Generated Forecast）					
    └─ BENCHMARK：选择基准来源（可多选）							
    ↓							
系统实时计算并展示							
    ├─ Overall Benchmark Score 更新（各板块分数的平均值）							
    ├─ 各维度的点位位置更新（每个维度所有指标的平均值）							
    ├─ 分布条和可视化刷新							
    └─ Metrics Summary 雷达图重绘							
    ↓							
用户进行数据钻取							
    ├─ 悬停点位查看Tooltip详情							
    ├─ 展开/收起指标板块							
    ├─ 查看单个指标详情							
    └─ 对比不同数据源的百分位							
    ↓							
用户完成分析							
    └─ 导出报告或截图（可选）							
```							
							
### 3.2 FILTER 与指标板块的对应关系							
							
| FILTER 选项 | 对应板块 | 包含指标 |							
|-------------|---------|---------|							
| GROWTH | Revenue & Growth | ARR Growth Rate |							
| EFFICIENCY | Profitability & Efficiency | Gross Margin |						
| MARGINS | Burn & Runway | Monthly Net Burn Rate, Monthly Runway |							
| CAPITAL | Capital Efficiency | Rule of 40, Sales Efficiency Ratio |							
| ALL | 所有板块 | 所有6个指标 |							
							
---							
							
## 四、功能详细描述							
							
### 4.1 页面布局和交互区域							
							
#### 4.1.1 页面标题和说明区域							
**位置**：页面顶部							
**内容**：							
- 标题："Benchmarking"							
- 说明文字（英文）：							
  ```							
  "Benchmark values are normalized for comparability.							
   Industry calculations may differ from Looking Glass metrics.							
   Use for directional context only."							
  ```							
							
#### 4.1.2 筛选条件区域（Filter Card）							
**位置**：页面上方，4个筛选卡片横排排列							
**组成部分**：							
							
| 筛选项 | 选项 | 选择模式 | 颜色反馈 | 说明 |							
|--------|------|--------|---------|------|							
| **VIEW** | Snapshot, Trend | 单选 | 蓝色点亮 | Snapshot：快照视图展示百分位；Trend：趋势视图展示用户选定的时间范围折线 |						
| **FILTER** | ALL, GROWTH, EFFICIENCY, MARGINS, CAPITAL | 多选（ALL为总和） | 蓝色点亮 | ALL选中时其他自动选中，取消ALL时其他自动清空；决定显示哪个板块的数据 |							
| **DATA** | Actuals, Committed Forecast, System Generated Forecast | 多选 | 黄色点亮 | Actuals：历史实际数据；Committed/System Generated：预测数据；多选时显示多个维度 |						
| **BENCHMARK** | Internal Peers, KeyBanc, High Alpha, Benchmark.it | 多选 | 黄色点亮 | 基准数据来源；最多4个；与DATA组合形成最多12个维度 |						
							
**特殊处理**：							
- 当公司无同行匹配时，显示提示：							
  ```							
  "Peer Fallback: No direct peer group found for this company.							
   Benchmarking against all active companies in Looking Glass."							
  ```							
							
#### 4.1.3 日历选择区域							
**位置**：筛选卡片下方或右侧							
**默认值**：最后一个有Actual数据的月份（新建公司则为当前日历月）							
**功能**：用户可选择不同月份查看对标数据							
							
#### 4.1.4 Overall Benchmark Score Card（综合评分卡）							
**位置**：筛选条件下方，独占一行							
**组成部分**：							
							
1. **百分位显示**							
   - 数值形式：**51%ile**（例如）							
   - 计算方法：四个板块分数的算术平均值							
   - **板块分数 = 该板块所有有效指标百分位的算术平均**							
							
2. **进度条（Bar）**							
   - 起点：0%，终点：100%							
   - 长度：占卡片宽度的60-70%							
   - 颜色规则（根据 Overall Score 的百分位 n）：							
     ```							
     0 ≤ n < 25%   → 红色（Bottom Quartile）							
     25 ≤ n < 50%  → 粉色（Lower Middle Quartile）							
     50 ≤ n < 75%  → 黄色（Upper Middle Quartile）							
     75 ≤ n ≤ 100% → 绿色（Top Quartile）							
     ```							
							
3. **进度条点位（Benchmark Points）**							
   - **每个点位代表一个维度组合（DATA×BENCHMARK）内所有指标的平均百分位**							
   - 最多12个点位（3种数据类型 × 4种基准源 = 12 种维度）							
   - 点位颜色见UI图例							
   - **交互**：鼠标悬停显示Tooltip							
     ```							
     Tooltip内容（两行）：							
     第一行：维度标识（例如"Actuals - Internal Peers"）							
     第二行：该维度所有指标的平均百分位（例如"P45"或"~P64"）							
     ```							
   - **特殊处理**：若多个点位完全重合，打包展示所有重合点位信息，点位展示顺序按下面Data-Benchmark展示排序来展示。比如Actuals - Internal Peers和Committed Forecasts - Internal Peers重合，那点位就按Actuals - Internal Peers显示（颜色和形状），悬浮的时候打包展示							
							
4. **右上角信息提示**							
   - 显示内容（选择其一）：[6] Metrics - [Top Quartile]							
     ```							
     "X-Top Quartile" X代表metric的数量							
     "X-Upper Middle Quartile"							
     "X-Lower Middle Quartile"							
     "X-Bottom Quartile"							
     ```							
   - **特殊提示**（当存在特殊计算时）：							
     ```							
     "Includes estimated percentiles (interpolated values used/boundary values used/interpolated values used & boundary values used)"							
     ```							
							
---							
							
### 4.2 指标板块区域（Metrics Cards）							
							
#### 4.2.1 Snapshot 视图指标板块							
							
**板块类型**：4个固定板块							
```							
1. Revenue & Growth（收入增长）- 对应 FILTER 的 GROWTH							
2. Profitability & Efficiency（盈利能力&效率）- 对应 FILTER 的 EFFICIENCY							
3. Burn & Runway（现金消耗&跑道）- 对应 FILTER 的 MARGINS							
4. Capital Efficiency（资本效率）- 对应 FILTER 的 CAPITAL							
```							
							
**每个板块的组成**：							
							
1. **板块标题行**							
   - 板块名称（加粗）							
   - 板块百分位排名（右对齐）							
   - 板块进度条（颜色规则同Overall Score）							
							
2. **板块进度条**							
   - **注意：各板块的进度条不显示维度点位，仅显示该板块的平均百分位**							
   - 颜色根据板块百分位显示							
							
3. **单个指标展示**（每个板块下的指标）							
   - **指标名称**：对应指标英文名	
   -  Actual、Committed Forecast、 System Generated Forecast的实际值，实际值均取于Normalization Tracing的对应值，不做任何加工，确保两个页面的值是一样的					
   - **分布条**：							
     - 形式：水平彩色条形图							
     - 颜色：根据该指标在当前维度下的百分位进度条上色							
     - 长度：代表相对位置							
"     -各指标名称悬停内容：指标内容，右侧加指标标签（Guess/Exact），指标公式，Segment,Source。
指标公式在下面各指标信息中包含"							
							
   - **百分位数值**：							
     - 精确百分位：P45（例如）							
     - 估算百分位：~P64（使用了线性插值）							
     - 超范围标记：>P75 或 <P25							
							
   - **交互**：鼠标悬停显示详细Tooltip							
     ```							
     Tooltip显示内容：							
     - 指标名称							
     - 数据类型（DATA）							
     - 基准来源（BENCHMARK）							
     - 百分位数值							
     - 同行规模（例如"Peer Count: 45"）							
     ```							
							
   - **无数据处理**：							
"     - 指标无数据时：显示灰色空白进度条，对应的数据数值显示NA
      - 基准无数据时：显示灰色空白进度条，进度条名称基准后面加（N/A)。例如：Actual-Internal Peers（N/A)
"							
     - 整个板块无数据时：显示"N/A"							
							
4. **板块展开/收起**							
   - 点击板块标题可展开/收起该板块							
"   - 默认初试化卡片展开状态，指标是收起状态
"							
   - 版块默认展开：显示版块的名称，百分位和进度条；板块内每个指标默认展示一个DATA-BENCHMARK分布条，如果一个指标存在多个分布条，那就显示Show All按钮，点击显示算不分布条，按钮变为Hide。							
   - 版块收起，只显示版块的名称，百分位和进度条							
							
**Snapshot 视图中的 FILTER 行为**：							
- 选择 FILTER=GROWTH 时，页面仅显示 Revenue & Growth 板块的指标							
- 选择 FILTER=ALL 时，显示全部 4 个板块							
- 其他 FILTER 选项同理							
"- Data-Benchmark展示排序：按 Benchmark 优先排序，先展示第一个 Benchmark 对所有选中 Data 的数据，然后是第二个 Benchmark 对所有选中 Data 的数据，依此类推。
Benchmark 顺序：Internal Peers → KeyBanc → High Alpha → Benchmark.ai
Data 顺序：Actuals → Committed Forecast → System Generated Forecast
"							
#### 4.2.2 Trend 视图指标板块							
							
**核心特点**：显示用户自定义时间范围内的历史趋势							
							
**数据时间范围**：							
- 用户自定义选择时间范围，日历的开始月份和结束月份不能是同一个月（默认6个月，从closed month 往前数6个月）							
- 若公司历史数据不足 6 个月，点到P0，悬浮tooltip的时候百分位和数值都对应NA							
							
**展示方式**：							
							
1. **4 个固定板块结构**（同 Snapshot）							
   - 各板块仍按相同分组展示							
							
2. **每个板块下的指标折线图**							
   - 横坐标：月份（实际有数据的月份数）							
   - 纵坐标：百分位排名（0-100%ile）							
   - 线条数量：根据选中的 DATA 和 BENCHMARK，最多 12 条折线							
   - 线条颜色：与 Snapshot 中的颜色编码一致							
"   -折线图的展示有Percentile和Amount两个选项,如果选择Amount,则纵坐标按照实际值划分展示"							
3. **交互和Tooltip**							
   - 鼠标悬停在某个月份：显示竖向网格线							
   - Tooltip 内容：该月份所有交集点的百分位排名							
     ```							
     Tooltip显示：							
     - 月份标签							
     - 所有交集点的"DATA-BENCHMARK"组合及其百分位值							
     ```							
   - 鼠标悬停在折线点：高亮该线，显示该点详细信息							
							
4. **Trend 视图中的 FILTER 行为**							
   - 同 Snapshot 一致，仅显示对应板块的指标折线图							
							
---							
							
### 4.3 Metrics Summary 雷达图							
							
**位置**：页面底部（Snapshot 和 Trend 视图中都显示）							
**组成部分**：							
							
1. **雷达图结构**							
   - 中心点：0%（表示最低百分位）							
"   - 同心圆：25%, 50%, 75%, 100%"							
   - 角度数：6 个（对应 6 个关键指标）							
   - 线条数：最多 12 条（根据 DATA×BENCHMARK 组合）							
   - 图表类型：固定六边形雷达图（6个指标维度）							
"   - Snapshot 模式： 数据范围： 单月
计算方式： 每个角的值 = 该指标在各月的算术平均"		
-雷达图加图例，方便用户决定网的显隐					
"   

- Trend 模式： 
数据范围： 用户选择的连续月份
计算方式：
月份平均：所有月度平均值的算术平均
"							
							
2. **指标角度**							
   - ARR Growth Rate							
   - Gross Margin							
   - Monthly Net Burn Rate							
   - Monthly Runway							
   - Rule of 40							
   - Sales Efficiency Ratio							
							
3. **交互**							
"   - 鼠标悬浮在指标轴线上时，显示该指标所有 Data-Benchmark 组合的百分位详情
"							
     ```							
     Tooltip内容：							
     - 数据类型（DATA）							
     - 基准来源（BENCHMARK）							
     - 百分位数值（P45或~P64或>P75）							
     ```							
							
---							
							
## 五、核心指标和公式							
							
### 5.1 指标定义和计算公式							
							
#### 5.1.1 ARR Growth Rate（年度经常性收入增长率）							
```							
公式：ARR Growth Rate_t = (ARR_t - ARR_(t-1)) / ARR_(t-1)							
说明：衡量公司的收入增速							
方向：正向指标（数值越高，百分位排名越高）							
```							
							
#### 5.1.2 Gross Margin（毛利率）							
```							
公式：Gross Margin = (Gross Profit / Gross Revenue) × 100%							
说明：衡量公司销售商品后的盈利能力							
取值范围：0% 至 100%							
方向：正向指标							
```							
							
#### 5.1.3 Monthly Net Burn Rate（月度净现金消耗率）							
```							
公式：Monthly Net Burn Rate = Net Income - Capitalized R&D (Monthly)							
说明：衡量公司每月实际消耗的现金							
方向：正向指标							
排序方式：正向排序（按数值大小从小到大排序，数值小的排名靠前，百分位更高）							
```							
							
#### 5.1.4 Monthly Runway（现金跑道）							
```							
公式：Monthly Runway = - (Cash / Monthly Net Burn Rate)							
说明：基于现有现金和月度消耗速率，公司能坚持的月份数							
方向：正向指标（数值越高越好）							
当cash或Monthly Burn Rate其中一个为负数并且另一个为0的时候，也显示NA值，排名也最差，得P0。
							
N/A 处理规则（N/A是正常值）：							
┌─────────────────────────────────────────────────────┐							
│ N/A 公司的排名分类                                      │							
├─────────────────────────────────────────────────────┤							
│ 1. Top Rank                                         │							
│    条件：Cash ≥ 0 且 Net Burn ≥ 0                  │							
│    含义：盈利且有现金储备，不存在破产风险               │							
│    排名：最高（100%ile）                            │							
│                                                     │							
│ 2. Bottom Rank                                      │							
│    条件：Cash < 0 且 Net Burn < 0                  │							
│    含义：现金为负（无溶性）且持续亏损                   │							
│    排名：最低（0%ile）                              │						     │							
└─────────────────────────────────────────────────────┘							
```							
							
#### 5.1.5 Rule of 40（40法则）							
```							
公式：Rule of 40 = (Net Profit Margin + MRR YoY Growth Rate) × 100%							
说明：衡量公司增长与盈利的平衡							
评价标准：理想情况下应超过 40%							
方向：正向指标							
```							
							
#### 5.1.6 Sales Efficiency Ratio（销售效率比）							
```							
公式：Sales Efficiency Ratio = (S&M Expenses + S&M Payroll) / New MRR LTM							
说明：市场销售投入相对于新增月度经常性收入的比例							
含义：每获得 $1 的新 MRR，需要花费多少美元在 S&M 上							
方向：反向指标（数值越低越好）							
```							
							
---							
							
## 六、百分位排名引擎需求							
							
### 6.1 百分位计算方法							
							
#### 6.1.1 Internal Peer（LG内部同行）							
							
**计算方法**：使用最近排名百分位法（Nearest Rank Percentile Method）							
							
**步骤**：							
							
1. **指标排序**							
   - 大部分指标按升序排序（数值小的排名靠前）							
   - Monthly Net Burn Rate 按升序排序（数值小=亏得少，排名靠前）							
   - 该排序方式称为"正向排序"							
							
2. **排名计算**							
   - 使用标准竞争排名（Standard Competition Ranking）							
   - 相同数值的公司分配相同排名，下一个公司排名往后跳							
							
3. **百分位公式**							
   ```							
   P_target = ((R - 1) / (N - 1)) × 100%							
							
   其中：							
   P_target = 目标公司的百分位排名							
   R = 目标公司在同行中的排名							
   N = 同行公司总数							
   ```							
							
4. **特殊情况**							
   ```							
   - 若 N = 1（只有目标公司）：百分位 = 100							
   - 若公司值相同：使用竞争排名，分配相同的百分位							
   - 若所有指标值完全相同：不显示百分位，不计入metric summary和Overall Score							
   ```							
							
"#### 6.1.2 外部平台基准（KeyBanc, High Alpha, Benchmark.it）"							
							
**数据来源**：Benchmark Entry 中用户输入的第三方数据
**数据对应**：Benchmark Entry 中的字段包含：Category，LG Metric Name，LG Formula，Platform，Edition，Metric Name，Definition，FY Period，Segment Type，Segment Value，P25，Median，P75，Data Type，Best Guess			 其中Segment Type是数据年份，Segment Value是ARR的范围，匹配时应对应正确年份的相同Segment Value范围的百分位。			
**百分位提供**：通常为 P25、P50、P75							
							
**特殊处理**：							
							
1. **精确百分位**：若指标值完全匹配，显示精确百分位（例如 P45）							
							
2. **插值处理**：							
   - 若指标值落在两个数据点之间，使用线性插值法估算							
   - 显示形式：~P56（波浪线表示估算）							
   - 汇总中注明："Includes estimated percentiles (interpolated values used)"							
"   -线性插入举例：~P62.556.  ~P=P_low + (P_high - P_low) * (d - d_low) / (d_high - d_low)     (例如P50=30%,P75=40%,d=35%;计算~P=50+(75-50)*(35-30)/(40-30)=62.5)"							
3. **超范围处理**：							
   - 若指标值超出基准范围，使用">"或"<"表示（如 >P75 或 <P25）							
   - 汇总计算时使用边界值（P75 或 P25）							
   - 汇总中注明："Includes estimated percentiles (boundary values used)"							
   -若大于P25，则展示＞P25，计算时用P50；大于P50，展示＞P50，计算时用P75；大于P75，展示＞P75，计算时用P100；若小于P25，则展示＜P25，计算时用P0；若小于P50，则展示＜P50，计算时用P25；若小于P75，则展示＜P75，计算时用P50；若小于P100，则展示＜P100，计算时用P75。							
4. **P50 特殊规则**：							
   - 若报告仅提供中位数（P50），在汇总计算时按以下规则取值：							
     ```							
     高于中位数 → 使用 P75（估计为 75%ile）							
     低于中位数 → 使用 P25（估计为 25%ile）							
     等于中位数 → 使用 P50（50%ile）							
     ```							
							
### 6.2 同行（Peer）定义和匹配规则							
							
#### 6.2.1 同行匹配属性							
							
同行基于以下四个维度定义（必须同时满足）：							
							
1. **公司类型**（如 SaaS、PaaS 等）							
2. **公司阶段**（融资阶段，如 Series A、Series B 等）							
3. **会计方法**（现金制 vs. 权责发生制）- **必填项**							
4. **ARR 规模（查看哪个月用哪个月的ARR）**（分为以下范围，包含前边界，不包含后边界）：							
   ```							
"   [$1, $250K)        → 包含 $1，不包含 $250K"							
"   [$250K, $1M)       → 包含 $250K，不包含 $1M"							
"   [$1M, $5M)         → 包含 $1M，不包含 $5M"							
"   [$5M, $20M)        → 包含 $5M，不包含 $20M"							
"   [$20M, +∞)         → 包含 $20M 及以上"							
   ```							
							
#### 6.2.2 同行回退规则							
							
| 情景 | 条件 | 处理 | UI 提示 |							
|------|------|------|--------|							
| 无符合条件的同行 | 找不到 4 个及以上同行 | 回退到 LG 平台基准 | Peer Fallback 提示 |							
| 同行不足4个 | 同行公司 < 4 个 | 回退到 LG 平台基准 | Peer Fallback 提示 |							
| 有效同行 | 同行公司 ≥ 4 个 | 使用该同行 | 显示"Peer Count: X" |							
							
#### 6.2.3 DATA 类型与同行的关系							
							
- 用户选择 DATA 类型时（如 Committed Forecast），系统在计算百分位时：							
  - 使用同行的对应 DATA 类型数据（如同行的 Committed Forecast）							
  - 若同行没有该 DATA 类型数据，该同行在该维度下被排除							
  - 不同维度可能有不同数量的有效同行（正常）							
"  -若用户选择Committed Forecast或System Generated Forecast,并选择KeyBanc或High Alpha或Benchmark.it基准时，计算时要用预测数据与已有基准数据计算百分位"							
### 6.3 排除条件							
							
以下状态的公司将被排除在同行计算之外：							
```							
#Exited						
#Shut Down							
#Inactive						
```							
							
### 6.4 权重计算							
							
#### 6.4.1 类别分数（Category Score / 板块分数）							
```							
板块分数 = 该板块所有有效指标的百分位数的算术平均							
							
示例：							
  Burn & Runway 板块包含 2 个指标：							
    - Monthly Net Burn Rate: P55							
    - Monthly Runway: P45							
  Burn & Runway 分数 = (55 + 45) / 2 = P50							
```							
							
#### 6.4.2 总体分数（Overall Score）							
```							
Overall Score = 四个板块分数的算术平均							
							
公式：							
Overall = (Revenue & Growth + Profitability & Efficiency + Burn & Runway + Capital Efficiency) / 4							
```							
							
#### 6.4.3 维度分数（Dimension Score）							
```							
维度分数 = 该维度（DATA-BENCHMARK）下所有指标百分位的算术平均							
							
示例：							
  维度"Actuals - Internal Peers"包含 6 个指标：							
    ARR Growth Rate: P50							
    Gross Margin: P55							
    Monthly Net Burn Rate: P60							
    Monthly Runway: P65							
    Rule of 40: P45							
    Sales Efficiency Ratio: P40							
  维度分数 = (50+55+60+65+45+40) / 6 = P52.5							
```							
							
#### 6.4.4 指标缺失时的处理							
							
- 若某个指标无数据，该指标在计算板块分数和维度分数时被排除							
- 原有分母减 1（只计算有数据的指标）							
- 若整个板块都无数据，该板块分数 = N/A，不计入 Overall Score 的分母				

### 6.4.5 Forecast 数据类型对标规则

| 对标场景 | 基准方式 | 说明 |
|---------|--------|------|
| **Forecast vs 外部基准** | Forecast vs Actual | 预测值与外部历史实际值对标（外部调研通常发布历史分布，不含预测） |
| **Forecast vs 内部同行** | Forecast vs Forecast | 当同行有预测数据时用预测对标当无同行预测数据时，降级到所有活跃LG企业的Actual |
| **多数据类型同时对标** | 多marker展示 | 同一分布条上显示CF、SF的多个marker |

### 6.4.6 Forecast 内部同行基准计算
- **数据源**：同行企业预测ARR + 6个月连续有效数据验证（以最后一个有预测数据的月份为基准）
- **降级逻辑**：若无同行预测数据，降级到所有活跃LG企业的实际数据			
							
---							
							
## 七、特殊情况处理							
							
### 7.1 无同行情况							
**现象**：公司无法找到 4 个或以上的同行							
**处理**：							
1. 自动切换到 LG 平台基准（所有活跃公司）							
2. 在页面显示 Peer Fallback 提示信息							
3. 相关指标的百分位仍然正常计算和展示							
							
### 7.2 新建公司的默认值							
**现象**：公司为新建公司，无历史 Actual 数据							
**处理**：							
1. 日期默认为当前日历月							
2. 仅显示 Forecast 数据（Committed Forecast、System Generated Forecast）							
3. Actuals 不可选或显示为灰色							
							
### 7.3 数据不完整的指标							
**现象**：某个指标缺失或无有效数据							
**处理**：							
1. 该指标显示灰色空白进度条，不显示数值							
2. 在该板块的分数计算中排除该指标							
3. 在 Overall Score 的计算中排除该板块（若该板块全无数据）							
							
### 7.4 所有指标完全相同的情况							
**现象**：多个公司的所有指标值都完全相同							
**处理**：							
1. 分配相同的百分位值（如都是 50%ile）							
2. 不显示额外的"不同"标记							
3. 正常参与权重计算							
							
### 7.5 百分位超范围情况							
**现象**：公司指标值超出基准数据范围							
							
**处理**：							
- 高于最高值：显示 >P75，汇总计算使用 P75							
- 低于最低值：显示 <P25，汇总计算使用 P25							
- 汇总提示："Includes estimated percentiles (boundary values used)"							
							
---							
							
## 八、UI交互和操作反馈							
							
### 8.1 用户操作反馈规范							
							
| 操作 | 反馈方式 | 反馈内容 |							
|------|--------|---------|							
| 点击 VIEW 选项 | 即时 | 选中项蓝色点亮，页面从 Snapshot ? Trend 切换 |							
| 点击 FILTER 选项 | 即时 | 选中/取消项，板块内容实时更新；ALL 与其他选项互斥 |							
| 点击 DATA 选项 | 即时 | 选中项黄色点亮，维度点位数量更新 |							
| 点击 BENCHMARK 选项 | 即时 | 选中项黄色点亮，维度点位数量更新 |							
| 选择日历月份 | 即时 | Overall Score 和各指标数据重新计算并展示 |							
							
### 8.2 Tooltip 交互规范							
							
| 触发条件 | 显示内容 | 示例 |							
|---------|--------|------|							
| 鼠标悬停进度条点位（Overall Score） | 第一行：维度标识<br/>第二行：百分位值 | "Actuals - Internal Peers<br/>P52" |							
| 鼠标悬停指标分布条 | 指标名称、百分位值、同行规模 、具体的数值显示| "ARR Growth Rate<br/>P45<br/>Peer Count: 45<br/>Cohort Size" |							
| 鼠标悬停 Trend 折线点 | 月份和所有交集点信息 | "2026-03<br/>Actuals-Internal: P50<br/>Actuals-KeyBanc: P55" |							
| 鼠标悬停雷达图点位 | 指标名称、维度、百分位 | "Rule of 40<br/>Actuals-Internal Peers<br/>P62" |							
							
### 8.3 颜色编码规范							
							
**百分位等级与颜色对应**：							
```							
红色（#FF4444）    ← 0 ≤ n < 25%    Bottom Quartile							
粉色（#FF88BB）    ← 25 ≤ n < 50%   Lower Middle Quartile							
黄色（#FFBB44）    ← 50 ≤ n < 75%   Upper Middle Quartile							
绿色（#44BB44）    ← 75 ≤ n ≤ 100%  Top Quartile							
灰色（#CCCCCC）    ← N/A 或无数据							
```							
							
**选中状态颜色**：							
```							
蓝色点亮（#2196F3） ← VIEW、FILTER 筛选项被选中							
黄色点亮（#FFC107） ← DATA、BENCHMARK 筛选项被选中							
```							
							
---							
							
**文档更新日期**：2026年3月25日							
							
							
							
---							
