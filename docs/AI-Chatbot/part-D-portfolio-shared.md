# 第 4 部分：Portfolio 端 UI 与共享功能需求（Portfolio Manager UI & Shared Features）

> 本部分包含 5 个面向 Portfolio Manager 的 UI 类需求和所有用户共享的功能需求

---

## 1. AI Chatbot - Portfolio Manager 核心聊天界面（Portfolio Manager Core Chat UI）

- **Asana ID**: 1214057483533663
- **状态**: ⏳ 待开发
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533663

### 业务需求

Looking Glass 必须为 Portfolio Manager 和 Admin 角色提供一个独立的 AI 聊天界面，该界面与 Company 端界面完全隔离。本任务仅覆盖 Portfolio Manager 聊天体验的基础 UI 外壳与交互设计。数据集成、知识库连接、Memory File 访问以及聊天历史等内容由其他独立的依赖任务进行覆盖。

Portfolio Manager 界面必须在框架结构、建议提示语以及整体定位上与 Company 端界面有清晰的区分。Company 端界面聚焦于单一公司的业绩表现，而 Portfolio Manager 界面则围绕投资组合层面的可视化、跨公司洞察以及与创始人的运营合伙人（operating partner）关系来组织。语言风格和视觉框架应当体现"始终在线的运营合伙人（always-on operating partner）"这一核心理念。

### 验收标准

- 在 Admin Portal 中，Admin 与 Portfolio Manager 角色可访问一个独立的 AI 聊天界面，该界面在框架结构、布局以及建议提示语上与 Company 端界面有清晰区分。
- 用户登录后直接进入聊天体验。
- 欢迎页（welcome screen）展示一条以投资组合为导向的标题语，以及一组反映 Portfolio Manager 真实工作流的建议提示卡片（例如："哪些公司在 burn rate 上表现不佳？"、"投资组合在 ARR 增长方面的趋势如何？"、"GS 对提升销售效率有哪些建议？"）。
- 显著位置展示输入栏，供用户键入自由形式的自然语言问题。
- "New Chat" 按钮或控件始终清晰可见、可访问。
- 显示明显的免责声明（disclaimer），指出回复内容由 AI 生成，仅供信息参考使用。
- 界面在桌面端和平板端均可访问。
- 本任务不依赖任何数据集成类任务——仅为 UI 外壳。

### UX 设计要点

- 欢迎页的文案必须明确以投资组合为导向，不得复用 Company 端界面的框架。可考虑采用与 operating partner 愿景一致的标题文案，例如 "Your AI Operating Partner"。
- 建议提示卡片应当反映 Portfolio Manager 的真实工作流——识别异常表现的公司、跨公司监控趋势，以及理解哪些公司需要重点关注。
- 首次启动时保持界面简洁、避免复杂——不要用过多控件让用户产生压迫感。

### 依赖与备注

- 本任务仅为 UI 外壳层，不包含任何数据集成、知识库连接、Memory File 访问或聊天历史功能。
- 上述附加功能由其他依赖任务独立交付。

---

## 2. AI Chatbot - Portfolio Manager Memory File 访问 UI（Portfolio Manager Memory File Access UI）

- **Asana ID**: 1214081544026466
- **状态**: ⏳ 待开发
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026466

### 业务需求

Portfolio Manager 必须能够通过 Portfolio Manager 聊天界面中的 Memory Settings 面板，查看其访问范围内所有公司的 Memory File。与 Company 端 Memory Settings 面板仅展示 Company Memory File 不同，Portfolio Manager 面板需为每家公司同时提供 Company Memory File（Layer 1a）与 Portfolio Admin Memory File（Layer 1b）的可见性，并以清晰的视觉差异区分两者。

Company Memory File 区域展示 Company Admin 也能看到的上下文——包括 Profile 数据、Company 端聊天会话中提取的 learnings，以及 Company 上传文档的摘要。该区域需附带清晰标签，标明该内容对 Company Admin 可见。Portfolio Admin Memory File 区域展示通过 Portfolio Manager 活动添加的内部 GS 上下文。该区域必须附带清晰的"Internal, not visible to company users"（内部使用，对公司用户不可见）标签，使 Portfolio Manager 始终明确自己所查看内容的归属。能够访问该面板的用户角色为所有 Admin 角色，包括 Super Admin、PGM 以及对该公司有访问权限的 PM 角色。

在 MVP 阶段，两个视图均严格为只读（read-only）。Portfolio Manager 不能通过 UI 直接编辑或删除 Memory 条目。他们可以浏览并搜索其访问范围内任意公司的两类文件中的条目。

### 验收标准

- Memory Settings 面板可在 Portfolio Manager 聊天界面中由 Admin 角色访问。Admin 角色 = Super Admin、PGM、PM。
- 面板包含一个公司选择器下拉框（company selector dropdown），允许 Portfolio Manager 选择要查看的公司 Memory File，作用域严格限定于其访问范围内的公司。
- 面板针对所选公司同时展示 Company Memory File（Layer 1a）和 Portfolio Admin Memory File（Layer 1b），两者之间需有清晰、立即可辨的视觉区分。
- Company Memory File 区域附带标签，标明该内容对 Company Admin 可见（例如 "Shared with Company Admins"）。
- Portfolio Admin Memory File 区域附带标签，标明该内容仅供内部使用（例如 "Internal GS Memory, not visible to company users"）。
- 各区域中的 Memory 条目按倒序时间顺序（reverse chronological order）展示，并附带来源标签（company profile、chat extraction、document summary）和时间戳。
- 提供搜索功能，可同时搜索两个文件，或筛选至单一文件。
- 所有访问均为只读——MVP 阶段不提供条目的编辑或删除功能。
- PGM 与 PM 用户仅能访问其自身访问范围内公司的 Memory File——超出其访问范围的公司 Memory File 既不可见也不可访问。
- 面板顶部展示一段简短的通俗语言说明（例如："Company Memory is shared with company admins. Internal GS Memory is visible to GS team only."）。

### UX 设计要点

- Portfolio Manager 的 Memory Settings 面板应使切换不同公司变得便捷，可在面板顶部设置公司选择器下拉框。
- Layer 1a 与 Layer 1b 区域之间的视觉区分必须立即可辨——可考虑采用基于 Tab 的布局、配以不同颜色处理的不同区域标题，或使用清晰分隔线配合标签徽章（label badges）。
- Layer 1b 区域上的 "Internal - not visible to company users" 标签应保持持续可见。
- 以紧凑、易扫读的列表格式展示条目，每个条目可展开查看详情。
- 搜索功能应清晰指示当前正在搜索的文件，并提供筛选至单一文件或同时搜索两者的选项。
- 在面板顶部包含一段简短的通俗语言说明，描述 Memory File 的内容以及访问权限为只读（例如："This is what your AI assistant has learned about this company. You can browse and search these memories but cannot edit them directly."）。

### 依赖与备注

- 依赖：Portfolio Manager Core Chat UI（任务 1）作为 UI 外壳基础。
- MVP 阶段严格为只读，不支持编辑或删除条目。
- 数据访问严格按 PGM 与 PM 的访问范围进行作用域控制。

---

## 3. AI Chatbot - Portfolio Manager 财务与 Benchmark 问答（Portfolio Manager Financial & Benchmark Q&A）

- **Asana ID**: 1214081544026465
- **状态**: ⏳ 待开发
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026465

### 业务需求

在 Portfolio Manager 聊天界面建立后，本任务将 Portfolio Manager Chatbot 接入财务数据源与 Benchmark 数据源，使其能够对 Portfolio Manager 访问范围内的所有公司进行跨公司查询。本任务必须支持同时跨多家公司的查询。

数据源沿用相同的体系——以 Normalization Table 作为财务实际值（actuals）与预测值（forecasts）的唯一可信来源（source of truth），以 Benchmark 数据层作为百分位定位（percentile positioning）的依据。Company Settings 中的公司 Profile 元数据（profile metadata）也作为数据源对 Portfolio Manager 访问范围内的所有公司开放。本次实现必须能够在单次响应中检索并综合 Portfolio Manager 有权访问的所有公司数据。例如，Portfolio Manager 应能够提问："which of my companies has the highest burn rate this month?"（本月我哪家公司 burn rate 最高？），并收到一个引用多家公司、连贯一致的答复。

在 MVP 阶段，Chatbot 仅作为信息工具（informational only）——它回答问题并呈现洞察，但不执行任何操作、不更新数据，也不生成正式报告。

### 验收标准

- Chatbot 能够准确回答关于 Portfolio Manager 访问范围内任一单家公司财务表现的自然语言问题，数据来源为 Normalization Table。
- Chatbot 能够准确回答跨公司的自然语言问题，覆盖 Portfolio Manager 访问范围内同时涉及多家公司的查询（例如："哪家公司的 gross margin 最低？"、"有多少公司提交了 committed forecast？"）。
- Chatbot 能够准确回答 Portfolio Manager 访问范围内任一单家公司或跨多家公司的 Benchmark 定位问题。
- Portfolio Manager 的数据访问范围被严格强制执行——无论问题如何措辞，Chatbot 都不能检索 Portfolio Manager 访问范围之外公司的任何数据。
- Company Settings 中的公司 Profile 元数据作为数据源对 Portfolio Manager 访问范围内的所有公司开放。
- Chatbot 不会编造（fabricate）或臆造（hallucinate）财务数字——所有回复均基于真实数据。
- 当因数据缺失或不可用导致 Chatbot 无法回答问题时，必须清晰说明这一情况。

### UX 设计要点

- 跨公司响应应清晰地按公司名称归属数据，使 Portfolio Manager 能立即理解某个数字所对应的公司。
- 当 Chatbot 引用预测数据时，回复应区分 committed forecast 与 system-generated forecast。
- 当 Chatbot 引用 Benchmark 数据时，回复应包含 Benchmark 来源与上下文。
- 如果 Portfolio Manager 询问其无访问权限的公司，Chatbot 应妥善地回应——确认收到该问题，但说明无访问权限，且不能透露该公司的任何数据。
- 对于返回排名或对比结果的跨公司查询（例如："哪家公司的 burn rate 最高？"），可考虑将响应格式化为简洁的排名列表以提升可读性，而不是大段段落文字。

### 依赖与备注

- 依赖：Portfolio Manager Core Chat UI（任务 1）作为 UI 外壳。
- 数据源：Normalization Table（财务实际值与预测值）、Benchmark 数据层（百分位定位）、Company Settings（公司 Profile 元数据）。
- MVP 范围：仅信息性问答；不执行操作、不更新数据、不生成正式报告。

---

## 4. AI Chatbot - 所有用户的聊天历史（Chat History for All Users）

- **Asana ID**: 1214081544026468
- **状态**: ⏳ 待开发
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026468

### 业务需求

AI Chatbot 必须为所有用户角色——Company User、Company Admin、Portfolio 用户——保存并展示历史会话记录。聊天历史允许用户回到先前的对话、回顾过往的回复，并继续此前的提问线索而无需重复上下文。它是与 Memory File 完全独立、彼此区分的功能——聊天历史是过往对话的完整、可读日志（full, readable log），而 Memory File 是 AI 从这些对话中提炼出来、用于改善未来回复的精炼智能（distilled intelligence）。

每位用户的聊天历史的作用域仅限于其本人的对话。Company Admin 不能查看同一公司内其他用户的聊天历史，Portfolio 用户也不能查看任何 Company 端用户的聊天历史。聊天历史完全归属于产生该对话的个人用户。

在 MVP 阶段，聊天历史为只读（read-only）——用户可浏览并回到过往对话，但不能编辑、重命名或删除。管理聊天历史的能力（重命名对话、删除条目）属于 post-MVP 范围。

### 验收标准

- 聊天历史适用于所有用户角色：Company User、Company Admin、Portfolio 用户（PGM 与 PM）。
- 过往对话可通过 Chatbot 界面内的聊天历史面板访问，该面板在 Company 端与 Portfolio Manager 端界面均可用。
- 聊天历史面板中的对话按近期程度分组（例如：Today、Yesterday、Last Week、Older）。
- 用户可点击聊天历史面板中的任意过往对话，打开并查看完整对话内容。
- 用户可通过从聊天历史面板中选择某次对话并发送新消息来继续过往对话——继续对话时 AI 保留先前对话的上下文。
- 聊天历史的作用域严格限于当前登录的个人用户——无论角色如何，用户都不能查看其他任何用户的聊天历史。
- 聊天历史面板可通过清晰可见的控件（例如：history 图标或 sidebar 切换按钮）从主聊天界面访问，Company 端和 Portfolio Manager 端界面均如此。

### UX 设计要点

- 聊天历史面板应给人以自然的辅助功能（secondary feature）感——可访问但不喧宾夺主。可折叠的 sidebar 或滑入式面板（slide-in panel）效果较好，能避免对主聊天区造成视觉干扰。
- 按近期程度分组（Today、Yesterday、Last Week）是消费级聊天应用中常见的模式，便于用户快速找到近期对话。
- 历史面板中的每个对话条目应展示一段自动生成的简短标题，或者展示开场消息的前几个词，使用户无需打开即可一眼识别话题。
- 当用户回到过往对话时，先前的消息应在新的输入栏之前清晰展示在对话线程中，让用户在继续提问之前获得完整上下文。
- 在"开始新对话"与"浏览历史"之间的过渡应顺滑——即使在历史面板打开时，"New Chat" 按钮也应始终保持清晰可见。

### 依赖与备注

- 适用范围：Company 端聊天界面和 Portfolio Manager 端聊天界面。
- MVP 阶段为只读——不支持重命名或删除对话。
- 重命名、删除等管理能力属于 post-MVP 范围。

---

## 5. AI Chatbot - 用于聊天分析的文档上传（Document Upload for Chat Analysis）

- **Asana ID**: 1214057483533666
- **状态**: ⏳ 待开发
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533666

### 业务需求

用户必须能够直接在 AI Chatbot 界面中上传文档，为对话提供额外的上下文。这使得用户能够将尚未录入 Looking Glass 的信息分享给 Chatbot，例如某份尚未录入系统的财务电子表格，或者一份希望 Chatbot 进行总结或提取洞察的会议转录文本。

上传的文档不会导入 Looking Glass，也不会进入财务数据流水线（financial data pipeline）。它们通过两步流程进行处理。第一步，文档通过 RAG（retrieval-augmented generation，检索增强生成）进行处理与建立索引，使其完整内容在当前会话以及所有未来的聊天会话中可被动态查询。这意味着 AI 可根据用户提问检索文档中具体、相关的段落。第二步，系统会从文档中自动生成一份与公司相关的关键 learnings 的高层摘要（high-level summary），并将该摘要保存至该公司的 Layer 1 Memory File。这确保了从文档中习得的最重要内容能够作为上下文持续存在，即使在未来不再显式引用原文件的对话中亦然。

所有上传的文档严格作用于其上传时所属的公司。它们绝不可被其他公司访问，也在任何情况下都不会进入共享的 GS Knowledge Base（Layer 2）。

MVP 阶段支持的文件类型覆盖主要使用场景：用于报告与财务文件的 PDF 和 Word 文档、用于结构化数据的 Excel 与 CSV 文件，以及用于导出会议转录（如 Fireflies 导出）的纯文本文件（.txt）。

### 验收标准

- 用户可通过聊天输入栏上的附件按钮（attachment button）直接上传文件——Company 端和 Portfolio 端用户均可使用。
- MVP 支持的文件类型：PDF、Word（.docx）、Excel（.xlsx, .xls）、CSV、纯文本（.txt）。
- 上传完成后，Chatbot 确认收到文档并提示其已就绪可被引用（例如："I've received your file. You can now ask me questions about it."）。
- 上传的文档通过 RAG 进行处理与索引，使其完整内容在当前会话以及所有未来的聊天会话中均可动态检索。
- 系统在文档上传后立即自动生成一份与公司相关的关键 learnings 的高层摘要，并将该摘要保存至该公司的 Layer 1 Memory File。
- Chatbot 在文档上传后能够立即准确回答关于其内容的问题，并在未来会话中亦能准确回答。
- 所有上传的文档及衍生内容严格作用于其原始公司的 Layer 1 上下文，绝不与其他公司共享，也不会进入 GS Knowledge Base（Layer 2）。
- 用户可在单次会话中上传多个文件。
- 当上传不支持的文件类型时，系统在对话中显示清晰的内联错误消息（inline error message），指明支持的文件类型。
- 实施文件大小限制（file size limit），当文件超出限制时显示清晰的内联提示。
- 聊天界面中提供专门的 Knowledge Base 区域，展示会话期间上传的所有文档，并对授权用户展示 GS Playbook（Layer 2）。文档以列表视图（list view）呈现，包含文件名、类型、上传日期和上传者，仅支持下载（MVP 阶段不支持应用内预览）。可见性按角色控制：Company 端用户仅能查看其本公司的文档，且不能访问 GS Playbook；Portfolio Manager 与 Admin 则可查看其权限范围内的所有文档。

### UX 设计要点

- 上传操作应给人以轻量且自然的感觉——聊天输入栏内的简单附件图标（attachment icon），与常见消息类应用的交互模式保持一致。用户不应感到在做某种复杂或技术性的操作。
- 上传完成后，在对话线程中以小型文件 chip 或徽章（file chip / badge）确认已上传内容（文件名与类型）。
- Chatbot 上传后的确认消息应包含一条建议的首步操作（suggested first action），帮助用户开始使用（例如："Would you like me to summarize this document, or do you have a specific question about it?"）。
- 在确认消息中包含一条不张扬的提示（subtle note），告知文档已被保存以供将来参考（例如："This file has also been added to your company's memory so I can reference it in future conversations."）。
- 文件大小或类型错误应作为内联消息出现在对话中，而不是干扰用户的模态框（modal）或系统警告。
- Knowledge Base 区域应作为聊天界面内的辅助面板（secondary panel）或 Tab 进行访问，与主对话线程明确区分。以简洁的列表格式呈现已上传文件，显示文件名、类型和上传日期。下载应通过每行一个简单的图标操作（icon action）完成。由于 GS Playbook 与用户上传文件位于同一区域，应使用清晰的视觉分组或标签来区分 "Uploaded Documents" 与 "GS Playbook"。如果尚未上传任何文档且未加载 Playbook，则不应显示 Knowledge Base 区域——应展示合适的空状态（empty state）。

### 依赖与备注

- 处理流程：RAG 索引 + 自动生成 Layer 1 Memory File 摘要。
- 数据隔离：上传文档严格作用于源公司，绝不进入 GS Knowledge Base（Layer 2）。
- 适用界面：Company 端和 Portfolio Manager 端聊天界面均支持。
- 角色可见性：Company 端用户仅可见本公司文档，不能访问 GS Playbook；Portfolio Manager 与 Admin 可在其访问范围内查看所有文档。
- MVP 阶段：仅支持下载，不提供应用内预览（in-app preview）。
