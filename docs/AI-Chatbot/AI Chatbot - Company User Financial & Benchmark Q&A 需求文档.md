# AI Chatbot - Company User Financial & Benchmark Q&A 需求文档

## 一、功能概述

本需求是在已建立的核心聊天界面（Core Chat UI）基础上，将公司侧（company-side）聊天机器人与财务和基准数据源对接，使其响应具备数据来源。该功能让公司用户能用自然语言询问关于本公司财务表现和基准定位的问题，并获得直接来自 Looking Glass 数据的、准确且有依据的答案。

**MVP 定位**：聊天机器人仅为信息型（informational only）——只回答问题、呈现洞察；**不执行操作、不更新数据、不生成正式报告**。

---

## 二、数据源（Source of Truth）

### 2.1 财务和基准数据
**唯一真实数据来源**：normalization table（标准化数据表），包含每家公司的：
- Normalized actuals（标准化实际数据）
- Committed forecast（承诺预测）
- System-generated forecast（系统生成预测）
- Benchmark data（基准数据）

该数据源覆盖所有聊天机器人需处理的财务 Q&A 场景：
- 历史业绩问题
- 预测问题
- 实际值与预测值之间的对比
- 基准类问题（如百分位定位）

### 2.2 公司元数据
**Company Settings 的公司元数据**可作为数据源，为响应提供公司上下文。

---

## 三、用户范围与数据访问

- 所有财务和基准数据检索**严格限定**于已登录用户所属的公司。
- **不可能进行跨公司数据访问**。
- 聊天机器人无法检索或引用任何其他公司的财务或基准数据。

---

## 四、验收标准（Acceptance Criteria）

### 4.1 财务 Q&A 准确性
聊天机器人能够使用自然语言基于 normalization table 中的数据（历史 actuals、committed forecast、system-generated forecast）准确回答关于公司财务表现

### 4.2 基准 Q&A 准确性
聊天机器人能够使用自然语言基于 benchmark 数据层准确回答关于公司基准定位的问题，包括相对于 internal peers 和外部行业基准的百分位定位。

### 4.3 数据访问范围
所有财务和基准数据检索严格限定于已登录用户所属公司——不可能进行跨公司数据访问。

### 4.4 数据缺失的明确提示
当聊天机器人因数据缺失或不可用而无法回答某问题时，响应必须**清楚指出哪些数据缺失**。

**示例**：若用户要求将 actuals 与 committed forecast 进行对比，但不存在 committed forecast 时，响应需说明因为尚未录入 committed forecast，因此无法进行该对比。

### 4.5 无法回答时的回退响应
聊天机器人需为其无法有意义地回答的问题提供恰当的回退响应：

| 场景 | 行为 |
|------|------|
| **无意义/不可理解输入**（如 "123"） | 表明不确定用户意图，并提供具体的示例问题进行引导。<br>示例文案："I'm not sure what you'd like to know. Try asking about your ARR growth, EBITDA margin, cash runway, or benchmark comparison." |
| **询问无访问权限或无法在其范围内匹配到的公司** | AI 返回**单一响应**，**不区分**"无访问权限"与"找不到"，且**不暴露任何公司数据或公司是否存在**。<br>示例文案："I can't find that company or you don't have access to it." |

### 4.6 禁止虚构（No Hallucination）
聊天机器人**不得**虚构或编造财务数字——所有响应必须以 normalization table 和 benchmark layer 中的实际数据为依据。

### 4.7 数据类型标注
响应中的财务数字需用其数据类型**进行标注**——actuals、committed forecast 或 system-generated forecast——以便用户分辨该数字是已报告的结果还是预测，以及是哪种类型的预测。

### 4.8 标准化免责声明
当响应包含基准或财务数字时，需传达：
> "Benchmark values are normalized for comparability. Industry calculations may differ from Looking Glass metrics. Use for directional context only."

### 4.9 基准来源与同行集说明
当响应基于基准数据时，需说明：
- 所基于的 benchmark source（**source 和 edition** 若有，例如 internal peers、KeyBanc - 2025）
- 同行集（peer set）

当因为公司没有直接同行组而**应用了 peer fallback 对 Internal Peer 进行回退**时，响应需指明该比较是针对**所有活跃公司**（all active companies）进行的，而非针对直接同行组。

---

## 五、响应格式化（Response Formatting）

### 5.1 结构化数据可视化
当 AI 响应包含**结构化数据**（财务指标、基准对比、排名或时间序列数据）时，响应需以**可视化格式**渲染而非纯文本。

**支持格式**：表格（tables）、图表（charts）。

**系统按数据类型自动选择最适合的格式**：
- 时间序列数据 → 默认 line chart（折线图）
- 并排对比和排名 → 默认 table（表格）
- 等等

### 5.2 图表类型切换（Chart Type Toggle）
当响应以图表呈现时，需提供**图表类型切换控件**，允许用户在**与当前数据上下文相适配**的图表类型之间切换（如 line chart、bar chart、pie chart）——**无需重新查询 AI**。

仅展示对当前数据合适的图表类型。

### 5.3 报告式结构化（Report-Style Format）
对于包含**多个不同区块**或大量内容的响应，AI 需将响应组织为**报告式格式**：
- 清晰的标题
- 区块标题（section headers）
- 有组织的内容块

而非连续的纯文本段落。

---

## 六、业务逻辑闭环

```
用户在 Ask Goldie 输入自然语言问题
    ↓
系统识别用户身份及其所属公司（限定数据访问范围）
    ↓
AI 解析问题意图，确定所需数据：
    ├─ 财务问题 → 标准化的 actuals / committed forecast / system-generated forecast
    ├─ 基准问题 → benchmark data layer（internal peers / 外部基准）
    └─ 公司上下文 → Company Settings 元数据
    ↓
从 normalization table（USD 标准化数据）和 benchmark layer 检索数据
    ├─ 严格限定本公司范围
    └─ 不调用任何其他公司数据
    ↓
判断数据可用性：
    ├─ 数据存在 → 进入响应生成
    ├─ 数据缺失 → 进入"数据缺失"回退路径（指明缺失内容 + 引导用户在哪里录入）
    ├─ 询问其他公司 → 返回"找不到或无访问权限"统一文案
    └─ 输入无意义 → 返回示例问题引导文案
    ↓
生成响应：
    ├─ 财务数字必须标注数据类型（actuals / committed forecast / system-generated forecast）
    ├─ 基准数字必须附带 benchmark source + edition + peer set
    ├─ 若触发 Internal Peer Fallback，需说明对比对象为所有活跃公司
    └─ 包含标准化免责声明（"Benchmark values are normalized for comparability..."）
    ↓
响应格式化：
    ├─ 时间序列 → line chart（默认）+ 可切换图表类型
    ├─ 排名 / 对比 → 表格
    ├─ 多区块 / 大量内容 → 报告式结构（标题 + section headers + 内容块）
    └─ 简单回答 → 自然语言
    ↓
返回用户（桌面端 / 移动端均完全可用）
    ↓
用户可继续追问；所有数字均有据可依，不虚构、不跨公司
```

---

## 九、关键边界条件汇总

| 边界场景 | 处理方式 |
|---|---|
| 用户问其他公司数据 | 返回 "I can't find that company or you don't have access to it."，**不区分**无权限和不存在 |
| 用户输入无意义字符串（如 "123"） | 返回不确定意图说明，并附带具体示例问题（ARR growth、EBITDA margin、cash runway、benchmark comparison 等） |
| 用户请求对比但无 committed forecast | 明确说明"没有 committed forecast 因此无法对比"，并提示在 Financial Statements 中可录入 |
| 公司无直接同行（Peer Fallback） | 响应明确指出对比对象为所有活跃公司，而非直接同行组 |
| 用户本币 ≠ USD | 仍返回标准化 USD 数值，与 Financial Statements 视图不一致是预期；可附简短免责声明 |
| AI 不得虚构数字 | 所有数字必须来自 normalization table / benchmark layer |
| MVP 不支持的能力 | 不执行写操作、不更新数据、不生成正式报告 |

