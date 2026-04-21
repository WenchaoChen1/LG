# Create Benchmark Comparison UI - Portfolio Intelligence 功能需求文档

## 功能概述

Portfolio Intelligence Benchmark Comparison UI 为管理员用户提供 Portfolio 级别的多公司财务指标对标分析工具，支持对标化的相对性能展示、多维度基准对比（内部同行、外部行业调查、预测数据）、以及 Snapshot 和 Trend 两种分析视图，帮助用户快速理解 Portfolio 内各公司相对于同行和行业的竞争位置。

---

## 目录

- [详细说明](#详细说明)
  - [使用流程](#使用流程)
  - [功能模块详解](#功能模块详解)
    - [页面总体布局](#页面总体布局)
    - [筛选条件区域](#筛选条件区域)
    - [快照视图 - 列表展示](#快照视图---列表展示)
    - [趋势视图 - 折线图展示](#趋势视图---折线图展示)
    - [指标卡片与详情展示](#指标卡片与详情展示)

---

## 详细说明

### 使用流程

**管理员用户使用 Portfolio Benchmark Comparison UI 的完整流程：**

1. **导航至 Portfolio Intelligence 的 Benchmarking 页面**
   - 从 Portfolio Intelligence 模块tab中，找到 "Benchmarking" 标签
   - 点击进入 Benchmarking 页面（新增标签页）

2. **选择要对标的公司**
   - 在"Companies"多选筛选器中，选择要对标的公司
   - 系统显示：公司状态为Exited或Shut down的置灰，不可选择
   - **特性**：系统初始状态显示空状态（需要用户先选择公司）

3. **配置对标维度与视图**
   - **选择视图**（View）：Snapshot 或 Trend
   - **选择指标分类**（Filter）：All、Growth、Efficiency、Margins、Capital
   - **选择数据类型**（Data）：Actuals、Committed Forecast、System Generated Forecast
   - **选择对标基准**（Benchmark）：Internal Peers、KeyBanc、High Alpha、Benchmarkit.ai

4. **选择时间范围**
   - **Snapshot 视图**：单个时间选择器，选择单个月份（默认当前月份）
   - **Trend 视图**：两个时间选择器，选择月份范围，默认6个月（当前月份及之前的5个月）
   - **时间选择器**： 视图转换时，选择器个数也要相应转换

5. **查看对标分析结果**
   - **Snapshot 视图**：按公司分组展示，每个指标显示公司值、百分位、对标值
   - **Trend 视图**：展示折线图，每条线代表一家公司，观察跨月趋势变化

---

### 功能模块详解

#### 页面总体布局

**页面结构**（从上到下）

1. **页面标题与说明区**（顶部）标题：Benchmarking 说明：Benchmark values are normalized for comparability. Industry calculations may differ from Looking Glass metrics. Use for directional context only.
2. **筛选条件区域**（上方）
3. **主内容区域**（中下方，根据视图不同展示不同内容）
   - Snapshot 视图：按公司分组的列表
   - Trend 视图：按指标分组的折线图

---

#### 筛选条件区域

**限制**
- Companies 筛选必须有用户选择才能展示数据（空状态显示）
- View 筛选会改变页面布局，需平稳切换
- 部分筛选的逻辑是互斥的（如 "All" 与其他分类互斥）

**区域说明**

##### 1. Companies 筛选器

**交互方式**：多选下拉列表，默认无选项

**限制**：
- 必须至少选择一个公司才能展示数据
- 未选择时显示空状态："To begin select a company"

**数据来源**：当前所在Portfolio 中的所有公司

**特殊处理**：
- 状态为Exited或Shut down的公司在列表中置灰

**交互规则**：
- 用户可随时修改选择，页面数据实时更新
- 若用户取消全部公司选择，页面返回空状态

##### 2. View 筛选器

**交互方式**：单选按钮,默认Snapshot

**限制**：
- 同时只能选择一种视图
- 切换视图时，其他筛选条件保持不变，仅改变展示方式

**可选值**：

1. **Snapshot（快照）**
   - 展示：单一月份的对标数据
   - 布局：按公司分组的列表视图
   - 日期选择：单月选择（日历选择器）
   
2. **Trend（趋势）**
   - 展示：多个月的对标数据变化趋势
   - 布局：按指标分组的折线图
   - 日期选择：月份范围选择（开始月份和结束月份，且两者必须不同）

**默认值**：Snapshot

**交互**：点击切换，切换时无需确认，直接改变页面布局

##### 3. Filter（指标分类）筛选器

**交互方式**：多选标签,默认All
**限制**：
- "All" 与其他分类选项互斥
- 若用户先选 "Growth"，再点击 "All"，则 "Growth" 自动取消
- 若用户先选 "All"，再点击任何其他分类，则 "All" 自动取消

**可选值及对应指标**：

| FILTER 选项 | 对应板块 | 包含指标 |                     
|-------------|---------|---------|                   
| GROWTH | Revenue & Growth | ARR Growth Rate |                   
| EFFICIENCY | Profitability & Efficiency | Gross Margin |                 
| MARGINS | Burn & Runway | Monthly Net Burn Rate, Monthly Runway |                    
| CAPITAL | Capital Efficiency | Rule of 40, Sales Efficiency Ratio |                     
| ALL | 所有板块 | 所有6个指标 |    

**默认值**：All


##### 4. Data（数据类型）筛选器

**交互方式**：多选标签,默认Actuals

**可选值**：

1. **Actuals**（实际数据）
   - 数据来源：已完成月度的Actual标准化财务数据，来自Normalization tracing模块

2. **Committed Forecast**（承诺预测）
   - 数据来源：标准化财务数据的Committed forecast数据，来自Normalization tracing模块

3. **System Generated Forecast**（系统生成预测）
   - 数据来源：标准化财务数据的System generated forecast数据，来自Normalization tracing模块
  
**默认值**：Actuals

**特殊处理**：
- 若某公司无 Committed Forecast 或 System Generated Forecast 数据，该数据类型的对标值显示 "N/A"

##### 5. Benchmark（对标基准）筛选器

**交互方式**：多选复选框，默认Internal Peers

**可选值**：

1. **Internal Peers**（内部同行）
   - 数据来源：LG 同行公司，同行判断方式在下方**同行（Peer）定义和匹配规则**   
   - 计算方法：Nearest Rank 百分位法

2. **KeyBanc**
   - 数据来源：Benchmark Entry 中输入的 KeyBanc 数据
   - 计算方法：线性插值百分位法

3. **High Alpha**
   - 数据来源：Benchmark Entry 中输入的 High Alpha 基准数据
   - 计算方法：线性插值百分位法

4. **Benchmarkit.ai**
   - 数据来源：Benchmark Entry 中输入的 Benchmarkit 数据
   - 计算方法：线性插值百分位法

**默认值**：Internal Peers

##### 6. 日期选择器

**限制**：
- Snapshot 视图：单月选择
- Trend 视图：月份范围选择（开始月份到结束月份，且两个月份必须不同）

**默认值**：
- Snapshot：当前月份
- Trend：默认6个月，当前月及当前月前数5个月

---

#### 快照视图 snapshot- 表格展示

##### 表格结构

**分页规则**：每页最多十家公司，可以分页

**表格行**：
- 每一大行代表一家公司
- 行内黑色字体是Actuals值，紫色字体是Committed Forecast值，紫色带标记的字体是System Generated Forecast的值，具体显示几行取决于DATA筛选器中选择的数据类型
- Benchmark按照以下顺序展示：Internal Peers → KeyBanc → High Alpha → Benchmarkit.ai

**表格列**：公司名 → Benchmark标识 → Overall Score → 指标列
- 第一列：公司名称（包括Logo）
- 第二列：Benchmark，根据勾选的benchmark展示，勾选几个显示几个，勾选外部基准时，要显示benchmark-edition（若找不到任何匹配的指标信息，则显示最新版本即可）。Benchmark Tooltip内容：已选指标的已选数据类型的所有百分位及百分位对应的实际值。Internal peer显示五个百分位点；外部基准固定显示三列（P25， P50， P75），有值的就显示对应值，没有值的就显示NA。如果某指标没有可对标的external benchmark指标，那三列都显示NA。提示：external benchmark因为没有录入预测数据，所以没有预测数据的基准点位信息，只会显示一行黑色数据，没有紫色数据
- 第三列：Overall benchmark score:显示为例如：35%ile，数据值为该行中4-N列所有列指标的板块百分位的算术平均值，百分位是N/A时不参与计算（与company benchmark一致）
- 后续列4-N列（指标列）：按 Filter 选项展示指标，每一列包含两小列，分别是该指标的百分位和实际值排序，
指标列按照以下顺序展示：
ARR Growth Rate
Gross Margin
Monthly Net Burn Rate
Monthly Runway
Rule of 40
Sales Efficiency Ratio

- 列数取决于用户选择的指标分类和对标基准数量
---

**计算逻辑 - 百分位计算**

**内部同行（Internal Peers）百分位计算**：

公式：P_target = ((R - 1) / (N - 1)) × 100

其中：                     
   P_target = 目标公司的百分位排名                     
   R = 目标公司在同行中的排名                     
   N = 同行公司总数  
   N=1时，P=P100
结果若非整数，则四舍五入取整

```
根据目标百分位数 (P) 计算排名 (R)
R = ((P * (N - 1))/100) + 1
P：目标百分位数（例如：25、50、75）。
N：同组公司总数。
R：在排序列表中的位置。
确定 R 值后，从已排序的指标列表中选取该位置对应的值。
注：如果计算得出的 R 值为小数，请采用标准四舍五入法（逢半进一）将其取整，以确定最终的整数排名。若有竞争排名情况，取不到相应排名，则显示N/A
```
补充：指标排序方向
| 指标 | 方向 | 说明 |
|------|------|------|
| ARR Growth Rate | 升序 |
| Gross Margin | 升序 |
| Monthly Net Burn Rate | 升序 | 
| Monthly Runway | 升序 | 
| Rule of 40 | 升序 |
| Sales Efficiency Ratio | 降序 | 

**同行（Peer）定义和匹配规则**                   
 - 若该公司在Peer Group Management中绑定了同行公司，且同行公司有效（是否有效已在Peer Group Management功能中做了判断，若无效会有无效提示），则使用绑定的同行公司数据；
 - 若无绑定公司，或绑定同行组数据无效，则系统按照匹配规则进行自动匹配，匹配规则见下面说明。若系统匹配也无有效同行数据，则回退到平台基准(以全平台公司为基准），显示Peer Fallback 提示

**同行匹配属性**                 
                     
同行基于以下六个维度定义（必须同时满足）：                     
                     
1. 公司类型相同（Company Settings中的Type）                    
2. 公司阶段相同（Company Settings中的Stage）                   
3. 会计方法相同（现金制 vs. 权责发生制）- 必填项                    
4. ARR 规模相同（查看哪个月用哪个月的ARR,Actual找历史实际值，Committed forecast/System generated forecast数据分别用Committed forecast/System generated forecast ARR）**：                                      
   [$1, $250K)        → 包含 $1，不包含 $250K"                   
   [$250K, $1M)       → 包含 $250K，不包含 $1M"                     
   [$1M, $5M)         → 包含 $1M，不包含 $5M"                    
   [$5M, $20M]        → 包含 $5M，包含 $20M"                    
   ($20M, +∞)         → $20M 及以上"
5. 数据质量符合以下规则
  - Actual数据时，从closed month开始往前数24个日历月内，连续六个月非负gross revenue，为有效数据公司，若有效同行 < 3 家，回退到全平台基准，显示 Peer Fallback 提示；
  - Committed forecast/System generated forecast数据时，从最后一个有预测数据的月份开始往前数24个日历月内，连续六个月非负gross revenue，为有效数据公司，若有效同行 < 3 家，回退到全平台基准，显示 Peer Fallback 提示。
6. 排除条件
以下状态的公司将被排除在同行计算之外：                                               
#Exited                     
#Shut Down                                   


**外部行业基准（KeyBanc / High Alpha / Benchmarkit）**：              
                     
**数据来源**：Benchmark Entry 中用户输入的第三方数据
**数据对应**：Benchmark Entry 中的字段包含：Category，LG Metric Name，LG Formula，Platform，Edition，Metric Name，Definition，FY Period，Segment Type，Segment Value，P25，Median，P75，Data Type，Best Guess        其中Segment Type是ARR，Segment Value是ARR的数值范围，匹配时应对应正确年份的相同Segment Value范围的百分位。        
**百分位提供**：通常为 P25、P50、P75                    
                     
**特殊处理**：                     
                     
1. **精确百分位**：若指标值完全匹配，显示精确百分位（例如 P45）                    
                     
2. **插值处理**：                     
   - 若指标值落在两个数据点之间，使用线性插值法估算                    
   - 显示形式：~P56（波浪线表示估算）                                     
    -线性插入举例：~P62.556.  ~P=P_low + (P_high - P_low) * (d - d_low) / (d_high - d_low)； P为百分位，d为实际数值 ; (例如P50(P_low)=30%(d_low),P75(P_high)=40%(d_low),d=35%;计算~P=50+(75-50)*(35-30)/(40-30)=62.5)                    
3. **超范围处理**：                    
   - 若指标值超出基准范围，使用">"或"<"表示（如 >P75 或 < P25）                     
   - 汇总计算时使用边界值（P75 或 P25）                                      
   - 若百分位点位不齐全，只有其中一或几个，无法确定具体百分位值所在范围时，大于P25，则展示＞P25，计算时用P50；大于P50，展示＞P50，计算时用P75；大于P75，展示＞P75，计算时用P100；小于P25，则展示＜P25，计算时用P0；小于P50，则展示＜P50，计算时用P25；小于P75，则展示＜P75，计算时用P50；小于P100，则展示＜P100，计算时用P75。                   


#### Trend视图 - 折线图展示

**含义**

Trend 视图以折线图的形式展示用户指定范围内（ 默认6 个月）的对标排名变化趋势，支持并列展示多个指标，每条线代表一家公司在某个 DATA-BENCHMARK 组合下的趋势，帮助用户观察相对位置的演变。

**区域说明**

##### 每个指标为一个卡片，卡片内图表并列显示，右上角有展开/收起按钮（▲ ▼），默认前两个卡片展开。
     - 卡片tooltip内容：
       指标名称
       该指标的计算方式；（LG系统公式）
       若选择了外部平台指标则继续展示：
       外部平台该指标名称， Best Guess/Exact/Inferred
       外部平台计算公式
       Segment: Segmenttype-Segment value
       Segment 2(如有）：Segmenttype-Segment value（图表时间段跨年可能会有多个segment）
       Source: KeyBanc SaaS Survey - 2024/ 2025（如有）

##### 数据-基准组合的折线图

**含义**：每个图表代表一个 DATA-BENCHMARK 组合（如 "Actuals - Internal Peers"），显示该组合下多家公司的趋势

**折线图标题**：
- 格式：`[Data Type] - [Benchmark Source]`
- 示例：`Actuals - Internal Peers`、`Committed Forecast - KeyBanc`
---

##### 折线图的坐标系

**纵轴（Y 轴）**：
- 标记：P0, P25, P50, P75, P100
- 含义：公司的对标百分位排名或相对位置

**横轴（X 轴）**：
- 显示月份标签（如 "DEC 2023", "JAN 2024", "FEB 2024"...）
- 时间范围：用户指定的范围（默认 6 个月）

---

##### 折线与公司标识

**含义**：每条折线代表一家公司在该 DATA-BENCHMARK 组合下的趋势

**折线特性**：
- **颜色**：每家公司使用不同颜色区分，颜色见UI图例，目前有30种颜色，超过30时颜色随机
  - 颜色与 Legend 对应

**Legend（图例）**：
- 位置：图表下方
- 内容：[公司名] 
- 示例：
 ● Company A    
- 交互：点击 Legend 项可显示/隐藏对应折线

**交互**：
- 鼠标 Hover 折线上的数据点：

 ```
对应月度和年份
Legend,第一家公司名称（按照先英文后中文，英文按A-Z，中文按拼音首字母A-Z排序),该月百分位和对应的实际值
Internal peer时：P0, P25, P50, P75, P100及对应的实际值；外部平台时：P25, P50, P75及其对应实际值，若无数据则显示N/A。Actual字体是白色，Committed Forecast字体是紫色，System Generated Forecast字体是加图标的紫色。提示：external benchmark因为没有录入预测数据，所以没有预测数据的基准点位信息，只会显示一行白色数据，没有紫色数据
后面所有公司以此类推，全部显示
```
##### 数据缺失处理

- 某家公司某个月份无数据，则展示最低点P0，tooltip展示N/A

**Data-Benchmark展示排序**（trend模式下折线图的展示排序）：
   - 按 Benchmark 优先排序，先展示第一个 Benchmark 对所有选中 Data 的数据，然后是第二个 Benchmark 对所有选中 Data 的数据，依此类推。
   - Benchmark 顺序：Internal Peers → KeyBanc → High Alpha → Benchmarkit.ai
   - Data 顺序：Actuals → Committed Forecast → System Generated Forecast
   - 横向排序，排完第一行排第二行
   - 公司图例先排英文再排中文，英文按照字母a-z排序，中文按照拼音首字母a-z排序。
---
#### 数据格式：百分位取整；货币值完整显示时保留两位小数，使用 K/B/M 缩写时保留一位小数；无单位数值默认保留两位小数。
