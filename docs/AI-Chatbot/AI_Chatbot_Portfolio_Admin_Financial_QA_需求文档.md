# AI Chatbot - Portfolio Admin Financial Q&A 需求文档

---

## 一、概述

在公司侧的 Financial Q&A 与 Benchmark Q&A 已建立起单公司问答的数据检索与响应模式的基础上，本需求将该能力延伸至 Portfolio Admin（组合管理员）侧。使 Portfolio Manager 与 Portfolio Admin 能够通过自然语言提问，跨其组合内的多家公司进行查询，获得跨公司的财务表现与基准（Benchmark）定位视图 —— 这是公司侧用户无法获得的能力。

本需求与公司侧 Q&A 的核心区别在于**数据范围（Scope）**：公司侧用户始终限定在自身公司数据；Portfolio Admin 可对其在组合内有权访问的所有公司发起跨公司查询。

## 二、数据源与范围

- 数据来源：与公司侧一致的 **normalization table** 与 **benchmark 数据层**，并在其上新增**跨公司聚合与对比逻辑**。
- 数据权限：所有数据访问严格限定于当前登录 Portfolio Admin 有权访问的公司范围，**绝不检索或引用其权限外公司的数据**。
- 透明度：Chatbot 必须对比较范围保持透明，明确说明分析中包含了多少家公司，以及是否有公司因数据缺失被排除。

## 三、MVP 范围与依赖

- MVP 为**信息型**能力：只回答问题、提供洞察，**不执行操作、不更新数据、不生成正式报告**。
- **不在 MVP 范围内**：Forecast Reliability Assessment（预测可靠性评估）类问题 —— 该类问题需要访问历史预测版本而非仅最新版本，是否扩展数据层以支持历史预测版本查询待另行评估。
- **依赖前置**：本 Story 依赖公司侧两个 Q&A Story 已完成：
  - AI Chatbot - Company User Financial Q&A (Normalization Data)
  - AI Chatbot - Company User Benchmark Q&A

  跨公司的检索与响应模式直接构建于以上单公司基础之上。

## 四、验收标准

### 1. 数据检索与范围（Data Retrieval & Scope）

- Chatbot 能基于 normalization table 与 benchmark 数据层，准确回答跨越当前 Portfolio Admin 权限范围内多家公司的自然语言问题。
- 所有数据检索严格限定在当前登录 Portfolio Admin 有权访问的公司 —— 权限外公司的数据**永不**被检索或引用。
- Chatbot 对跨公司分析的范围保持透明，包括包含了多少家公司、是否有公司因缺失或不完整数据被排除。
- Chatbot **不可**编造或幻觉化任何财务或基准数值 —— 所有回答必须基于真实数据。
- 响应中的财务数值需标注其数据类型：**actuals（实际值）、committed forecast（承诺预测）、system-generated forecast（系统生成预测）**，让 Portfolio Admin 能识别每个数字是已报告结果还是预测。
- 当响应引用基准数据时，需说明**基准来源（source）**、**版本（edition，若有）**及**对标群体（peer set）**。

### 2. 跨公司 Q&A 能力

- **排名**：能按指定指标（如 ARR 增长率、毛利率、销售效率）对组合内公司排名，并返回带支撑数据的排序结果。
- **顶部/底部识别**：能基于一个或多个指标识别组合内的 top performers 与 bottom performers，并解释排名依据。
- **单公司 vs 组合对比**：能将某一家指定公司的表现与组合平均值或组合内定义的对标群体进行对比。
- **组合级趋势**：能揭示组合层面的趋势，例如哪些指标在多家组合公司中普遍改善或恶化。
- **财务 + 基准结合**：能回答同时结合财务表现与基准定位的问题，例如：哪些公司在某个指标上相对**组合平均**及**外部基准**都表现不佳。

### 3. 缺失与不可用数据

- 当因数据缺失或不可用而无法回答问题时，Chatbot 需明确说明缺失内容。
- 若跨公司问题因部分公司缺少相关数据而无法完整回答时，Chatbot 需基于可用数据作答，并**明确说明有多少家公司被纳入、多少家被排除**。

### 4. 兜底处理（Fallback Handling）

- **无意义/不可解析输入**：Chatbot 表明不确定用户意图，并给出与组合管理相关的具体示例问题（例："Try asking about your top performing companies by ARR growth, or which companies are below benchmark on gross margin."）。
- **越权公司查询**：当 Portfolio Admin 询问其无权访问的公司时，AI 返回的响应**不区分"无权限"与"不存在"**，且不泄露任何公司数据或该公司是否存在。

### 5. 响应格式化（Response Formatting）

- 当 AI 响应包含结构化数据、排名、对比或组合层指标时，需以**可视化格式**渲染，而非纯文字：
  - 排名和对比 → 默认使用**表格**。
  - 时间序列或趋势数据 → 默认使用**折线图或柱状图**。
- 当响应以图表渲染时，需提供**图表类型切换（chart type toggle）**，允许用户在上下文合适的图表类型间切换，**无需重新向 AI 发起查询**。
- 对于包含多个明显区块或大量内容的响应，AI 需以**报告式（report-style）**结构组织：清晰的标题、章节标题及有组织的内容块。
- 功能需**移动端响应式**，在桌面端与移动端均可完整使用。

