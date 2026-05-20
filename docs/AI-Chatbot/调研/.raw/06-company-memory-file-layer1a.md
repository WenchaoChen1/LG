---
asana_gid: 1214057483533664
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533664
asana_section: LG Backlog  / Backlog
asana_status: Needs Sizing
asana_working_status: Not Started
asana_modified_at: 2026-05-11T14:15:08.870Z
lg_ticket: LG-1329
type: User Story
story_points: 
t_shirt: L
priority: High
completed: False
---

# Company Memory File - Layer 1a Backend (Company User Context)

Business Requirements

The AI chatbot requires a persistent, private memory file for each company that captures context appropriate for company-side users to see and benefit from. This is the first of two distinct backend memory file stories - Layer 1a covers the Company Memory File, which stores company-specific context that is visible to both Company Admin users and portfolio managers. Layer 1b (https://app.asana.com/1/1170332106480422/task/1214147930023560) covers the Portfolio Admin Memory File, which stores internal GS context visible only to portfolio managers.
The Company Memory File is strictly private to each individual company - it is never shared across companies and no content from it ever flows into the shared GS Knowledge Base (Layer 2). Its purpose is to give the chatbot a continuously growing, company-specific intelligence layer that makes every response more accurate and relevant over time for both company-side users and portfolio managers interacting with that company.
The Company Memory File is populated from the three sources below. The memory file does not need to be complete from day one - it builds incrementally as conversations happen.
    The first is the company's existing metadata in Looking Glass. Company Settings data including company name, description, company type, industry(populated in description), stage, and any other structured profile fields. This gives the chatbot a meaningful baseline understanding of the company from the very first conversation. 
    The second source is company-side chat conversations. At the end of each conversation session (triggered by session end or a defined period of user inactivity), the system runs an AI-driven post-conversation extraction pass that identifies and saves only information that is meaningfully worth remembering. This includes:
        Facts the user stated about their company not already in LG
        Corrections or clarifications to existing LG data. Corrections to LG financial data mentioned in chat are NOT propagated to financial data downstream in MVP - they may be stored as context only
        Strategic context that would improve future response relevance.
        People and org structure - who the key people are in the organization, their roles, and their relevance to specific areas of the business. As users chat about strategies and reference team members, those associations should be stored so the AI can reference the right person in future conversations.
        ICP (Ideal Customer Profile) - a clear, specific description of the company's target customer(s), including if there are multiple ICPs. This should be built up from chat conversations over time.
        Competitors - which competitors the company is selling against, and the relative strengths and weaknesses of those competitors as described by the user.
        Founder psychographic/personality profile - the AI should pick up on nuances about the user's leadership style, personality type, and behavioral tendencies (e.g., conflict avoidant, communication style, decision-making approach) to inform how the AI frames responses. 
        Strategic challenges with staying power - things like a churn problem tied to a specific ICP, a pricing challenge, a go-to-market issue. The key distinction is: store the strategic pattern, not the transient specifics. For example, store "company has seasonal churn with their new ICP" not "XYZ Corp churned in March." The memory should contain what a portfolio manager would want to remember and ask about next time they meet with a founder user.
        Value proposition and ROI - a specific description of the product's value prop and ROI story relative to each ICP.
        Pricing model - seat-based, usage-based, value-based, services + software, etc. 
        Porter's Five Forces framework - as the user chats, the AI should build out a Porter's Five Forces profile of the company as:
            Competitive Rivalry - who are the main competitors, how the company differentiates, the user's view of their competitive moat, and how intense competition is in their market
            Threat of New Entrants - what barriers protect the company, whether the user sees new competitive threats emerging, and what makes the market hard or easy to enter
            Bargaining Power of Buyers - customer price sensitivity, switching ease, revenue concentration risk, and how much leverage their customers have in negotiations
            Bargaining Power of Suppliers - key technology or vendor dependencies, risks tied to specific supplier relationships, and how easily those dependencies could be replaced
            Threat of Substitutes - what non-direct alternatives customers might consider, and whether the company's category faces disruption from fundamentally different approaches
        What is not stored:
            Full verbatim transcripts are not stored - those are handled separately by the chat history feature(story https://app.asana.com/1/1170332106480422/task/1214081544026468). 
            Generic questions, transactional exchanges, and information already accurately captured in LG data are explicitly excluded. 
    The third source is documents uploaded by company-side users within the chat. When a document is uploaded, two parallel processes occur: the document is RAG-indexed for dynamic retrieval in current and future sessions, and the system auto-generates a high-level summary of key company-relevant learnings saved as a memory entry. Both the RAG index and the summary are strictly scoped to this company's Layer 1a file and do not flow into Layer 1b or Layer 2.


Acceptance Criteria

Initialization
    A Company Memory File (Layer 1a) store is automatically created for each company(perhaps at the first use of the chatbot?)
    The memory file is automatically initialized with all available Company Settings metadata: company name, description (Company Overview), company type, industry, stage, and any other structured profile fields present in LG.
    When any Company Settings field mentioned above is updated by a user, the corresponding memory file entry is updated automatically.
    NOTE: When the consultative onboarding epic is introduced the Company Memory File will need to be initialized during that workflow
Chat Conversation Learning
    The learning trigger is end-of-session or a defined period of user inactivity (TBD)
    At session end, the system runs an AI-driven extraction pass saving only meaningful, company-relevant information from the conversation.
        Qualifying content
            facts the user stated about their company not already in LG: It includes anything factual the user says about their company during a chat conversation that is not already captured anywhere in LG structured fields which are those found in Company Settings metadata
            corrections or clarifications to existing LG data, namely to data in Normalization Table
            strategic context that would improve future response relevance: Layer 1a storing company-specific context about their particular company (their strategies, challenges, priorities, and goals) as expressed by the users interacting with the chatbot about that company, without cross-checking Layer 2.
    Excluded content: full verbatim chat transcripts, generic informational questions, transactional exchanges, and information already accurately captured in the company's existing LG data.
    Full chat transcripts are not stored in the memory file - they are handled separately by the chat history feature.
Document Upload Learning
    When a company-side user uploads a document in chat, two parallel processes are triggered: (1) the document is RAG-indexed for dynamic retrieval in current and future sessions, and (2) the system auto-generates a high-level summary of key company-relevant learnings saved as a Layer 1a memory entry.
    Both the RAG index and the memory summary are strictly scoped to this company's Layer 1a file - they do not flow into the Portfolio Admin Memory File (Layer 1b) or the GS Knowledge Base (Layer 2).
    Document Uploads are covered in story https://app.asana.com/1/1170332106480422/task/1214057483533666
Data Isolation & Access Control
    No Company Memory File content from one company is accessible to any other company under any circumstances.
    No content from the Company Memory File flows into Layer 2 (GS Knowledge Base) under any circumstances.
    Memory file entries are stored with metadata including source type (company profile, chat extraction, document summary) and timestamp.
    The architecture supports read-only access for Company Admin users (their own company only) and read-only access for Portfolio Managers (all companies within their access scope) - UI implementation is covered in separate stories.


UX Design Considerations

    This is a backend and data architecture story - there is no user-facing UI in scope here.

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-05-07 · Liang Chunru**：请确认 memory file 3 类内容理解：(1)'用户陈述的、LG 中尚未的公司事实'——理解为 Settings 页中的 company metadata，对吗？(2)'对既有 LG 数据的修正/澄清'——理解为对 normalization table 数据的修正，对吗？(3)'战略性上下文'——AI 是否需要先在 tenant 知识库 cross-check 内容是否已存在再存？还是直接存？另外：AI 查询整个 memory file 与全部上传文档（无视贡献者），那么上传文件 UI 页面是否也应展示同公司所有用户的上传？还是按角色隔离（Company User 仅自己，Company Admin 全公司，PM 跨可访问公司）？
- **2026-05-07 · Karen Arnoldi**：(1) 正确——任何用户在 chat 中陈述的、不在 LG Settings metadata 中的事实；(2) 正确；(3) 直接存，不 cross-check Layer 2。两者独立：Layer 1a 存公司专属上下文（策略、挑战、优先级、目标），Layer 2 存组织通用 playbook & best practice。上传文件 UI 可见性应按角色：Company User 仅自己；Company Admin 全公司 Layer 1a；PM/Admin Portal 跨可访问公司 Layer 1a + Layer 1b。
- **2026-05-08 · Karen Arnoldi**：请 review 5/8 BR 会议——Dougal 描述了更丰富的 memory 内容应当涵盖。team 不需硬编码每个类别，可用 broad extraction prompt 让 AI 有机构建。已在 story requirements 中列出指导性类别：People & org structure、ICP（Ideal Customer Profile）、Competitors、Porter's Five Forces 框架、Founder psychographic/personality、Strategic challenges with staying power、Value proposition & ROI、Pricing model。
- **2026-05-11 · Liang Chunru**：Review 了最新需求更新，需与 dev team 进一步对齐，暂时把状态 revert 到 Needs Sizing。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 1. Company Memory File - Layer 1a 后端（公司用户上下文）

- **Asana ID**: 1214057483533664
- **LG 编号**: LG-1329
- **状态**: Needs Sizing（Working Status = Not Started，T-Shirt = L，Priority = High，Type = User Story）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533664

### 业务需求

AI chatbot 需要为每个公司维护一份持久化、私有的 Memory File，用于记录适合公司侧用户查看并从中受益的上下文信息。本需求是两个独立的后端 Memory File 故事中的第一个 —— Layer 1a 涵盖 Company Memory File，用于存储既对 Company Admin 用户可见、又对 Portfolio Manager 可见的公司专属上下文。Layer 1b 则涵盖 Portfolio Admin Memory File，用于存储仅对 Portfolio Manager 可见的内部 GS 上下文。

Company Memory File 严格隔离于每一家具体公司之间 —— 永远不会跨公司共享，且其中任何内容都不会流入共享的 GS Knowledge Base（Layer 2）。其目的是为 chatbot 提供一个不断扩充、公司专属的智能层，使每一次回复对该公司的公司侧用户和与该公司交互的 Portfolio Manager 而言，都能随时间推移愈发精准、相关。

Company Memory File 由以下三个来源填充：

1. **第一来源**：公司在 Looking Glass 中已有的元数据。Company Settings 数据，包括 company name、description、company type、industry（在 description 中填写）、stage 以及任何其他结构化的资料字段。这为 chatbot 在第一次对话开始时就提供了一个对该公司有意义的基线认知。
2. **第二来源**：公司侧的聊天对话内容。在每个会话结束时（由会话结束事件或用户在指定时长内未活动而触发），系统会运行一次 AI 驱动的对话后抽取流程，仅识别并保存确实值得记忆的信息，包括：
   - 用户陈述的、Looking Glass 中尚未记录的关于其公司的事实
   - 对 Looking Glass 中既有数据的更正或澄清
   - 有助于提升未来回复相关性的战略性上下文
   - 不会保存完整的逐字对话记录 —— 这部分由独立的 chat history 功能处理。一般性问题、事务性交流以及 Looking Glass 中已准确记录的信息会被明确排除在外。
3. **第三来源**：公司侧用户在聊天中上传的文档。当上传文档时会并行触发两个流程：文档被进行 RAG 索引以便在当前及未来会话中可被动态检索；同时系统自动生成一份关于公司相关关键学习点的高层级摘要，作为一条 memory entry 保存。RAG 索引和摘要均严格限定在该公司的 Layer 1a 文件范围内，不会流入 Layer 1b 或 Layer 2。

### 验收标准

**初始化（Initialization）**

- 系统会自动为每家公司创建一个 Company Memory File（Layer 1a）存储（可能在首次使用 chatbot 时触发？）。
- Memory File 自动以所有可用的 Company Settings 元数据进行初始化：company name、description、company type、industry、stage 以及 Looking Glass 中存在的任何其他结构化资料字段。
- 当用户更新任何 Company Settings 字段时，对应的 memory file 条目会自动同步更新。
- 注意：当后续引入 consultative onboarding epic 时，Company Memory File 需要在该工作流中完成初始化。

**对话学习（Chat Conversation Learning）**

- 学习触发条件为会话结束（end-of-session）或用户在指定时长内未活动（具体时长 TBD）。
- 在会话结束时，系统运行一次 AI 驱动的抽取流程，仅保存对话中有意义、与公司相关的信息。
- 合格内容：用户陈述的、Looking Glass 中尚未记录的关于其公司的事实；对 Looking Glass 既有数据的更正或澄清；有助于提升未来回复相关性的战略性上下文。
- 排除内容：完整逐字对话记录、一般性资讯类问题、事务性交流，以及该公司在 Looking Glass 中已准确记录的信息。
- 完整对话记录不存储于 Memory File —— 该部分由独立的 chat history 功能处理。

**文档上传学习（Document Upload Learning）**

- 当公司侧用户在聊天中上传文档时，会并行触发两个流程：(1) 文档被进行 RAG 索引以便在当前及未来会话中可被动态检索；(2) 系统自动生成一份关于公司相关关键学习点的高层级摘要，作为 Layer 1a memory entry 保存。
- RAG 索引和 memory 摘要均严格限定在该公司的 Layer 1a 文件范围 —— 不会流入 Portfolio Admin Memory File（Layer 1b）或 GS Knowledge Base（Layer 2）。
- 文档上传由故事 1214057483533666 覆盖。

**数据隔离与访问控制（Data Isolation & Access Control）**

- 在任何情况下，一家公司的 Company Memory File 内容都不可被任何其他公司访问。
- 在任何情况下，Company Memory File 中的内容都不会流入 Layer 2（GS Knowledge Base）。
- Memory file 条目存储时附带元数据，包括来源类型（公司资料、对话抽取、文档摘要）和时间戳。
- 架构层面支持 Company Admin 用户对其自身公司只读访问，以及 Portfolio Manager 对其访问范围内的所有公司只读访问 —— UI 层实现由独立的故事覆盖。

### UX 设计要点

- 这是一个后端与数据架构故事 —— 此范围内不包含面向用户的 UI。

### 依赖与备注

- 文档上传相关需求由 Asana 故事 1214057483533666 覆盖。
- 后续引入 consultative onboarding epic 时，需要在 onboarding 工作流中加入 Memory File 的初始化逻辑。
- UI 层（Company Admin 与 Portfolio Manager 对 Memory File 的只读访问界面）由独立故事覆盖。

---

