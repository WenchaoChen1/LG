# 第 3 部分：公司端用户体验需求（Company User UI）

> 本部分包含 3 个面向 Company User / Company Admin 的 UI 类需求

---

## 1. AI Chatbot - 公司用户核心聊天界面（Company User Core Chat UI）

- **Asana ID**: 1214057483533662
- **LG 编号**: LG-1332
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533662

### 业务需求

Looking Glass 必须为公司端用户（包括 Company User 与 Company Admin 两个角色）提供一个对话式 AI 聊天界面，作为公司端平台内所有 AI Chatbot 交互的主要入口。本故事仅覆盖公司端 chatbot 体验的基础 UI 外壳与交互设计，不涉及数据集成、知识库连接、记忆文件访问以及聊天历史等内容——这些均在独立的依赖故事中处理，不在本故事范围内。

整个界面必须严格限定在公司上下文（company context）内。公司端用户无权查看 portfolio 层级信息、其他公司的信息，或任何 Golden Section 内部笔记与评估内容。整体的语调与界面定位应体现"始终在线的运营合伙人（always-on operating partner）"这一愿景——亲和、智能，并且从首次交互起即可立即提供价值。

### 验收标准

- 在公司的 Looking Glass 界面中，向 Company User 与 Company Admin 角色提供一个新的 "Ask AI" 标签、图标或等效入口。
- 用户在导航至 AI 后，应直接进入聊天体验。
- 欢迎页应展示一个清晰的标题，以及一组与公司业绩相关的建议提示卡片（suggested prompt cards），帮助用户快速上手。建议提示应覆盖财务表现、Benchmark 定位以及预测相关的问题。
- 显著位置展示输入栏，供用户输入自由形式的自然语言问题。
- 始终可见地提供 "New Chat" 按钮或控件，用户可随时开启全新对话。
- 界面严格限定在公司层级的上下文——portfolio 层级数据、其他公司的数据、Golden Section 内部内容均不可见、不可访问。
- 显著展示一项免责声明，表明回答由 AI 生成，仅供参考用途。
- 该界面在桌面端与平板端均可访问。
- 本故事不依赖任何数据集成类故事——它只是 UI 外壳。

### UX 设计要点

- 界面应给人以简洁、现代、亲和的感受，不应显得"技术化"。语调应体现"始终在线的运营合伙人"这一概念。
- 建议提示卡片应具体且可立即执行，围绕一名创始人真实会问的问题进行设计。避免使用 "Ask me anything" 这类泛化占位文案。
- 首次启动时保持界面简洁、不复杂——避免用大量控件让用户感到信息过载。

### 依赖与备注

- 本故事仅覆盖 UI 外壳层。数据集成、知识库连接、记忆文件访问、聊天历史均在独立的依赖故事中实现。
- 公司端用户严格隔离于 portfolio 数据与 Golden Section 内部内容。

---

## 2. AI Chatbot - 公司用户记忆文件访问界面（Company User Memory File Access UI）

- **Asana ID**: 1214147930023561
- **LG 编号**: LG-1333
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023561

### 业务需求

Company Admin 用户必须能够通过公司端聊天界面内的 Memory Settings 面板，查看 AI Chatbot 已经"了解到"的关于其公司的信息。该面板以可读、可搜索且只读的形式展示 Company Memory File（Layer 1a）的内容，让用户对 AI 用于个性化体验的上下文具有透明度。

Memory Settings 面板仅展示 Layer 1a 的内容——即 Company Memory File。Portfolio Admin Memory File（Layer 1b）在公司端界面的任何元素中都不应被引用、暴露或可访问。Company User 角色完全无权访问 Memory Settings 面板——该功能仅对 Company Admin 开放。

在 MVP 阶段，该面板为只读视图。用户可浏览并搜索记忆条目，但无法直接编辑、删除或新增条目。记忆文件按 Company Memory File 后端故事中所建立的系统驱动流程自动增长。

### 验收标准

- Company Memory File 是每家公司唯一的统一文件，并不按来源类型拆分为多个独立文件。文件中的每个条目都会带有一个来源标签（Source label，如 "Company Profile"、"Chat" 或 "Document"）以表明其来源。该标签仅用于展示与筛选——所有条目都存放在同一个文件中。
- Memory Settings 面板仅向 Company Admin 用户开放，可在公司端聊天界面内通过设置图标或二级菜单进入。
- Memory Settings 面板是 LG 内部的在线视图（in-app online view）。不提供将记忆文件下载或导出至用户本地机器的选项。
- 若后端将记忆条目以 Markdown 格式存储，则 UI 必须以整洁、可读的形式渲染其内容。
- Company User 角色无权访问 Memory Settings 面板。
- 面板仅展示 Company Memory File（Layer 1a）的条目——任何 Layer 1b 内容都不可见、不被引用、不可访问。
- 条目按时间倒序展示，并附带来源类型标签（如 "Company Profile"、"Chat"、"Document"）和时间戳。来源标签仅用于标识条目来源——不展示任何实际的聊天内容。
- 展示的条目是由 AI 提炼出的学习要点和摘要——并非聊天片段、对话日志或往期对话的逐字文本。完整的对话记录仅可通过独立的 Chat History 功能查看。
- 面板内提供搜索功能，便于定位特定的记忆条目。
- 全部访问均为只读——MVP 阶段不提供条目的编辑或删除能力。
- 面板顶部展示一段简短、通俗的说明文案（例如 "These are the key things your AI assistant has learned about your company over time. Full conversation history is available separately."，即"以下是你的 AI 助手在不断使用过程中了解到的关于公司的关键信息。完整的对话历史可在独立功能中查看。"）。

### UX 设计要点

- Memory Settings 面板应是一个"背景式"功能，用户可主动探索访问；通过二级菜单或设置图标进入即可，不应作为主导航元素之一。
- 使用紧凑的列表式布局，每个条目支持展开查看详情。来源标签应在视觉上有所区分——可考虑为 "Company Profile"、"Chat" 与 "Document" 使用小型的彩色徽章或图标。
- 面板内绝不可出现任何标签、章节标题或 UI 元素，暗示存在独立的 Golden Section 内部记忆层。

### 依赖与备注

- 该面板严格隔离 Layer 1a 与 Layer 1b：公司端不得以任何形式暴露 Portfolio Admin Memory File。
- MVP 阶段为只读模式；记忆条目通过 Company Memory File 后端故事中的系统驱动流程自动产生与维护。
- 完整对话记录由独立的 Chat History 功能负责，不与本面板混合。

---

## 3. AI Chatbot - 公司用户财务与 Benchmark 问答（Company User Financial & Benchmark Q&A）

- **Asana ID**: 1214081544026464
- **LG 编号**: LG-1334
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = L）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026464

### 业务需求

在核心聊天界面已经搭建完成的基础上，本故事将公司端 chatbot 与驱动其回答的财务与 Benchmark 数据源进行对接。该能力使公司端用户能够以自然语言提问其公司财务表现与 Benchmark 定位相关的问题，并获得直接基于 Looking Glass 数据的、准确且有据可依的回答。

所有财务数据已统一约定以 Normalization Table 为唯一可信源（source of truth）：该表包含每家公司的标准化实际值（normalized actuals）、Committed Forecast（已承诺预测）、System-Generated Forecast（系统生成预测）数据，以及 Benchmark 数据。这覆盖了 chatbot 需要处理的全部财务问答场景——历史业绩问题、预测问题、实际值与预测值的对比，以及如百分位排名等 Benchmark 类问题。

Chatbot 必须从这些数据源中检索相关数据，并将其回答完全建立在公司真实数据之上。所有数据访问严格限定在用户所属的公司——chatbot 不可检索或引用任何其他公司的财务或 Benchmark 数据。

在 MVP 阶段，chatbot 仅作为信息性工具——它回答问题、揭示洞察，但不执行操作、不更新数据，也不生成正式报告。

### 验收标准

- Chatbot 能够基于 Normalization Table 中的数据，准确回答关于公司财务表现的自然语言问题，包括历史 actuals、Committed Forecast 与 System-Generated Forecast。
- Chatbot 能够基于 Benchmark 数据层中的数据，准确回答关于公司 Benchmark 定位的自然语言问题，包括相对于内部同行（internal peers）与外部行业 Benchmark 的百分位定位。
- 所有财务与 Benchmark 数据检索严格限定在登录用户所属的公司——不可能进行跨公司数据访问。
- 当因数据缺失或不可用而无法回答某个问题时（例如该公司尚未存在 Committed Forecast），chatbot 的回答必须清晰地予以说明。
- Chatbot 不得编造或臆造（hallucinate）财务数字——所有回答必须基于 Normalization Table 与 Benchmark 层中的真实数据。
- 同时将来自 Company Settings 的公司画像元数据作为可用的数据源，为回答提供公司上下文。

### UX 设计要点

- 用户永远不需要去思考某条回答是由哪个数据源驱动的——数据集成对用户而言完全不可见。从用户视角看，体验只是简单的"提问—得到清晰、准确的回答"。
- 当 chatbot 引用预测数据时，回答应清晰区分 Committed Forecast 与 System-Generated Forecast，让用户理解该预测的来源。
- 当 chatbot 引用 Benchmark 数据时，回答应包含 Benchmark 来源与上下文（例如 "Based on the KeyBanc 2024 SaaS Survey, your ARR growth rate is in the 45th percentile"，即"基于 KeyBanc 2024 SaaS Survey，你的 ARR 增长率位于第 45 百分位"），使用户清楚自己在与什么标准进行比较。
- 当数据缺失或不完整时，chatbot 的回答应做到"有帮助"而非仅仅声明无法回答——在可能的情况下应说明需要哪些数据（例如 "I don't see a committed forecast for your company yet. You can add one in the Financial Statements section."，即"我目前没有看到贵公司的 Committed Forecast。你可以在 Financial Statements 模块中添加一份。"）。

### 依赖与备注

- 数据源以 Normalization Table 为唯一可信源，覆盖 actuals、Committed Forecast、System-Generated Forecast 与 Benchmark 数据。
- Company Settings 中的公司画像元数据作为辅助上下文数据源。
- MVP 阶段 chatbot 仅做信息性问答，不执行写操作、不更新数据、不生成正式报告。
- 严格的公司级范围隔离（per-company scoping）：禁止任何形式的跨公司数据访问。
- 强约束：禁止 hallucinate 财务数字；缺失数据时给出友好且可指引下一步的回答。
