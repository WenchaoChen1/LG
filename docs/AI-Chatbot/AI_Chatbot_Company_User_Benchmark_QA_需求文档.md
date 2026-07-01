# 需求文档：AI Chatbot - 公司用户 Benchmark 问答

---

## 1. 背景与目标

本需求是 "Company User Financial Q&A (Normalization Data)" 故事的姊妹需求，用于将公司侧（Company User）AI Chatbot 的能力扩展到 **Benchmark（对标）问答场景**。

- 归一化（Normalization）故事负责回答"公司自身财务表现"类问题。
- 本故事负责将 Chatbot 接入 **Benchmark 数据层**，回答"我公司相对同行与行业基准的对比表现"类问题。

MVP 范围：Chatbot **仅提供信息类问答与洞察**，不执行动作、不修改数据、不生成正式报告。Benchmark 回答只作为**方向性参考**呈现。

---

## 2. 业务逻辑闭环

```
用户提问 (自然语言)
   │
   ▼
判断意图与作用域 (仅限当前登录用户所属公司)
   │
   ├── 输入无法识别 ─► 返回"不确定 + 示例问题"提示
   ├── 询问他公司  ─► 返回统一模糊回应，不透露公司存在与否
   │
   ▼
从 Benchmark 数据层检索数据
   │
   ├── 数据可用 ─► 判断是否需要 Peer Fallback
   │                └── 无直接内部同行组时，改与"所有活跃公司"对比，并显式说明
   │
   ├── 数据缺失 ─► 说明缺失内容 + 需补充哪些数据
   │
   ▼
生成回答：基于真实数据，不臆造数值
   │
   ├── 附带 Benchmark 来源与版本 (如 KeyBanc — 2025)
   ├── 附带同行集说明 (Internal Peers / 全体活跃公司)
   ├── 附带方向性提示语 (归一化/行业口径差异声明)
   │
   ▼
按内容形态选择渲染格式
   │
   ├── 结构化数据/对比/排名/百分位 ─► 表格或图表
   │      └── 图表时显示"图表类型切换"（仅列出适配当前数据的类型，切换不重查）
   ├── 多板块/长内容 ─► 报告式结构 (标题 + 分节)
   ├── 其他 ─► 常规文本
   │
   ▼
在桌面端与移动端一致呈现（响应式）
```

---

## 3. 功能需求

### 3.1 数据检索与准确性

1. Chatbot 可基于 Benchmark 数据层准确回答自然语言问题，涵盖：
   - 相对**内部同行(Internal Peers)** 的百分位定位；
   - 相对**外部行业基准 (如 KeyBanc)** 的百分位定位。
2. Chatbot **禁止编造或幻觉** Benchmark 数值，所有数值必须来源于 Benchmark 数据层。
3. Benchmark 数据检索**严格限定于当前登录用户所属公司**，不可跨公司访问。
4. 当回答中包含 Benchmark 数值时，必须附带声明：
   *"Benchmark values are normalized for comparability. Industry calculations may differ from Looking Glass metrics. Use for directional context only."*

### 3.2 数据来源与同行集归属

1. 引用 Benchmark 数据时，回答需注明**基准来源与版本**（如可能，含 edition）。示例：`internal peers` 或 `KeyBanc — 2025`。
2. 当因公司无直接内部同行组、触发 Peer Fallback 时，需明确告知："比较对象为全体活跃公司，而非直接同行组"。

### 3.3 数据缺失与不可用

1. 因 Benchmark 数据缺失或不可用而无法回答时，必须**明确指出**并**说明缺失了哪些数据**。
2. 回答需具备帮助性：在数据不完整时，尽可能说明"需要补充哪些数据才能回答"，而不是简单拒答。

### 3.4 Fallback 处理

1. **不可理解 / 无意义输入**（例："123"）：Chatbot 需表明"不清楚用户想问什么"，并**给出具体示例问题**引导，例如：
   *"I'm not sure what you'd like to know. Try asking about your benchmark percentile on growth rate, gross margin, or sales efficiency."*
2. **跨越权限或不存在的公司查询**：统一返回一句**不区分"无权限"与"不存在"**的回复，不透露任何公司数据与存在性，例如：
   *"I can't find that company or you don't have access to it."*

### 3.5 回答呈现与格式化

1. 当回答内容涉及结构化 Benchmark 数据、对比、排名、百分位时，**必须以可视化形式呈现**（表格或图表），而非纯文本段落。
   - 侧对比 (side-by-side) 与排名场景**默认使用表格**。
2. 图表呈现时，需提供**图表类型切换**控件：
   - 仅显示与当前数据适配的图表类型；
   - 切换类型**不重新调用 AI**。
3. 若回答包含多个独立板块或大量内容，需采用**报告式结构**：包含清晰标题、分节标题、结构化内容块，避免大段散文。
4. 该功能须**响应式**，在桌面端与移动端均可完整使用。

