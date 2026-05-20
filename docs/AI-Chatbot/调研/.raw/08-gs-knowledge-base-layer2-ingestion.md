---
asana_gid: 1214057483533665
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533665
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-08T01:36:01.454Z
lg_ticket: LG-1331
type: 
story_points: 
t_shirt: M
priority: 
completed: False
---

# GS Knowledge Base - Layer 2 Ingestion & Management

Business Requirements

The AI chatbot's two-layer knowledge architecture depends on the existence of a populated, queryable Golden Section Knowledge Base as its Layer 2 shared resource. Unlike the company-specific memory file (Layer 1), which is built automatically from user activity, Layer 2 must be explicitly populated by Golden Section internally. For MVP, this layer consists of Golden Section's existing playbooks and best practice frameworks - the full body of GS operational and strategic knowledge that has been developed over time.
A research task (https://app.asana.com/1/1170332106480422/task/1214147930023558) was completed to determine whether hosting the GS playbooks on a publicly accessible external website would provide Generative Engine Optimization (GEO) visibility benefits, specifically, whether the AI chatbot accessing an external site to answer user questions would increase that site's authority or visibility in other AI model conversations. The research confirmed that there is no GEO benefit to external hosting. AI models do not learn from or increase the authority of a site simply by receiving content during a session. As a result, the decision has been made to proceed with Option B: copy all existing GS playbook content from the external site into a single managed structured document store within Looking Glass. This is the source for the GS Knowledge Base going forward.
This story covers the technical work required to ingest that markdown file and any supporting documents into a format that the AI chatbot can query as well as the internal-facing tooling needed for authorized GS users(Super Admins and PGMs) to manage and update that content over time. The result is a living, searchable knowledge layer that all chatbot users, both company-side and portfolio managers, can draw on for strategic guidance, without ever seeing the raw documents themselves or knowing the specifics of how the knowledge base is structured.
The GS Knowledge Base is completely separate from any individual company's Layer 1 memory file. It is a global shared resource for the current single-tenant implementation, meaning its contents are the same for all users across all companies on the platform. It does not contain any company-specific data, financial information, or identifying details about any portfolio company or founder. Its sole purpose is to make GS's collective operational and strategic knowledge accessible through the chatbot in a natural, conversational way.
For MVP, the scope is limited to ingestion and querying of the existing playbook content. The process of the LLM automatically detecting knowledge base updates from portfolio management conversations is explicitly post-MVP. For now, an authorized user must manually upload or update content in the knowledge base when changes are needed. The authorized role for editing the knowledge base is Portfolio Group Manager and above - lower roles do not have access to modify playbook content.
Important architectural note for the dev team: In the future, when Looking Glass is commercialized and sold to external equity firms, each firm (tenant) will require its own independent knowledge base - completely isolated from other tenants' knowledge bases. The current single shared GS Knowledge Base is appropriate for the MVP single-tenant implementation, but the architecture should be designed with per-tenant knowledge base isolation in mind so that multi-tenancy can be supported without significant rearchitecting. Do not build Layer 2 in a way that assumes a single global knowledge base will always be the only structure.

For reference the external website is: https://www.goldensection.com/vertical-saas-playbooks

Acceptance Criteria

Content Ingestion
    All existing GS playbook content is copied from the external GS website into a single managed internal markdown file as the source for Layer 2.
    A backend ingestion pipeline is implemented that accepts playbook documents in common formats (PDF, Word .docx, and markdown .md at minimum) and processes them into a queryable store for retrieval.
    All ingested content is stored and indexed as part of the shared GS Knowledge Base (Layer 2), accessible to all chatbot users regardless of company or role.
    The GS Knowledge Base is entirely separate from any company's Layer 1 memory file at the data and architecture level - there is no path by which Layer 2 content can become company-specific or vice versa.
    No company-identifying information, financial data, or founder-specific context is ever stored in Layer 2.
    An initial complete set of GS playbook content is ingested and validated as part of acceptance testing 
Content Management
    An internal admin interface or process is provided for authorized users to upload new content, update the markdown file, or remove documents from the knowledge base.
    Access to upload, edit, or remove knowledge base content is restricted to Portfolio Group Manager role and above. Lower roles cannot modify the knowledge base.
    A dedicated Knowledge Base management page is accessible within the admin portal to authorized users (PGM and Super Admin roles only). The page displays a list of all content currently in the knowledge base. It shows: document title, format (markdown), upload date, and last updated date. Authorized users can perform the following actions from this page:
        Edit: Modify its content inline
        Upload: upload a new document (markdown file) to replace the existing knowledge base
        Delete: remove the existing document (requires confirmation before deletion is executed)
    When content is uploaded or updated, the knowledge base is automatically re-indexed so that new or changed content is immediately available for queries.
    When content is removed from the knowledge base, it is no longer retrievable in chatbot responses.
    A simple status indicator is available in the admin interface showing when the knowledge base was last updated and how many documents are currently indexed.
Chatbot Query Behavior
    The chatbot can accurately retrieve and reference relevant sections of ingested playbook content in response to user questions about strategy, best practices, or GS guidance.
    Responses drawing on Layer 2 content do not expose raw document text verbatim - the AI synthesizes and summarizes the relevant guidance in conversational language.
Future Multi-Tenancy Compatibility
    The Layer 2 architecture is designed to support per-tenant knowledge base isolation in the future, allowing each external equity firm to have their own independent knowledge base when multi-tenancy is implemented.


UX Design Considerations

    Company users and portfolio managers have no direct visibility into the knowledge base documents themselves - they interact with the knowledge base only through the chatbot's natural language responses. There is no "browse playbooks" UI for MVP.
    The internal admin interface for uploading and managing playbook content does not need to be consumer-grade for MVP - it should be functional and reliable. A simple interface with document listing, status indicators, upload capability, and delete functionality is sufficient.
    For the chatbot-facing side, when a response draws heavily on GS playbook content a subtle attribution such as "Based on GS best practices" is appropriate so users understand the source of the guidance, without exposing the specific document name or contents.
    The markdown file format is preferred as the primary content management format because it is human-readable, lightweight, easy for both humans and the AI to process, and straightforward to version and update over time.

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-04-27 · Liang Chunru**：'When a document is uploaded or updated': update 是指替换现有 playbook（因为 MVP 不支持 edit）？如果无 playbook 文件，则 chat 页面 Playbook toggle 隐藏？
- **2026-04-27 · Karen Arnoldi**：对，确认。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 3. GS Knowledge Base - Layer 2 摄取与管理（Layer 2 Ingestion & Management）

- **Asana ID**: 1214057483533665
- **LG 编号**: LG-1331
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-08
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533665

### 业务需求

AI chatbot 的双层知识架构依赖于一个已被填充、可被查询的 Golden Section Knowledge Base 作为 Layer 2 共享资源。与 Layer 1（公司专属 Memory File）由用户活动自动构建不同，Layer 2 必须由 Golden Section 内部显式地填充。在 MVP 阶段，该层由 Golden Section 已有的 playbooks 和 best practice frameworks 构成 —— 即长期沉淀下来的 GS 全部运营与战略知识。

我们已完成一项调研，用于判断将 GS playbooks 托管在公开可访问的外部网站是否能带来 Generative Engine Optimization（GEO）方面的可见性收益 —— 具体而言，AI chatbot 在会话中访问外部站点以回答用户问题，是否会提升该站点在其他 AI 模型对话中的权威性或可见度。结论是：外部托管不会带来 GEO 收益。AI 模型并不会因为在会话中接收某站点内容就从中学习或提升该站点的权威性。基于此，决定采用 Option B：将外部站点上的所有现有 GS playbook 内容复制进 Looking Glass 内部由我们管理的单一 markdown 文件。该文件即为 GS Knowledge Base 后续的内容来源。

本需求覆盖以下技术工作：(1) 将该 markdown 文件及任何配套文档摄取（ingest）为 AI chatbot 可查询的格式；(2) 为授权 GS 用户（Super Admins 与 PGMs）提供面向内部的工具能力，以便其在后续持续管理与更新内容。最终交付一个不断演进、可被检索的知识层，使所有 chatbot 用户（公司侧与 Portfolio Manager 双方）都能从中获取战略指引，但用户既不会直接看到原始文档，也不会知晓该 Knowledge Base 的具体结构。

GS Knowledge Base 与任何单家公司的 Layer 1 Memory File 完全隔离。在当前的单租户实现中，它是一个全局共享资源 —— 即对平台上所有公司、所有用户而言其内容都相同。它不包含任何公司专属数据、财务信息或关于任何 portfolio 公司或创始人的可识别信息。其唯一目的是通过 chatbot 以自然、对话式的方式，让用户可以访问到 GS 的集体运营与战略知识。

在 MVP 阶段，范围仅限于现有 playbook 内容的摄取与查询。LLM 自动从 portfolio 管理对话中识别知识库更新的能力，明确属于 post-MVP 范畴。当前阶段，当内容需要变更时，必须由授权用户手动上传或更新知识库。可编辑知识库的授权角色为 Portfolio Group Manager 及以上 —— 更低权限的角色无权修改 playbook 内容。

**给开发团队的重要架构提示**：未来当 Looking Glass 商业化并销售给外部 equity firms 时，每家公司（每个 tenant）都将需要其专属的、独立的知识库 —— 与其他 tenants 的知识库完全隔离。当前的单一共享 GS Knowledge Base 适用于 MVP 单租户实现，但在架构设计上应预留 per-tenant 知识库隔离的考量，使后续无需大规模重构即可支持多租户。**不要**以"将永远只有一个全局知识库"的假设来构建 Layer 2。

参考：外部站点为 https://www.goldensection.com/vertical-saas-playbooks

### 验收标准

**内容摄取（Content Ingestion）**

- 将外部 GS 网站上的所有现有 playbook 内容复制进一份由内部管理的 markdown 文件，作为 Layer 2 的内容来源。
- 实现一个后端摄取流水线，能够接收常见格式的 playbook 文档（至少支持 PDF、Word .docx 与 markdown .md），并将其处理为可被检索的查询存储。
- 所有摄取的内容作为共享的 GS Knowledge Base（Layer 2）的一部分被存储与索引，对所有 chatbot 用户开放，不论其所属公司或角色。
- GS Knowledge Base 与任何公司的 Layer 1 Memory File 在数据与架构层完全隔离 —— 不存在任何路径会让 Layer 2 的内容变成公司专属，反之亦然。
- 任何能识别公司的标识信息、财务数据或与创始人相关的上下文，永远不会存入 Layer 2。
- 一组完整的初始 GS playbook 内容会被摄取，并作为本故事验收测试的一部分被验证。

**内容管理（Content Management）**

- 提供一个面向内部的管理界面或流程，使授权用户能够上传新内容、更新 markdown 文件，或从知识库中移除文档。
- 上传、编辑或移除知识库内容的权限仅限 Portfolio Group Manager 角色及以上。更低权限的角色不能修改知识库。
- 当内容被上传或更新时，知识库会自动重新索引，使新增或变更的内容立即可被查询。
- 当内容从知识库中移除后，将不再在 chatbot 回复中被检索到。
- 管理界面提供一个简洁的状态指示器，展示知识库最近一次更新的时间以及当前已索引的文档数量。

**Chatbot 查询行为（Chatbot Query Behavior）**

- chatbot 能在用户询问战略、最佳实践或 GS 指引相关问题时，准确检索并引用已摄取 playbook 内容中的相关章节。
- 借助 Layer 2 内容生成的回复不会逐字暴露原始文档文本 —— AI 会以对话式语言对相关指引进行综合与摘要。

**未来多租户兼容性（Future Multi-Tenancy Compatibility）**

- Layer 2 架构在设计上支持未来的 per-tenant 知识库隔离，使每家外部 equity firm 在多租户实现后能够拥有其独立的知识库。

### UX 设计要点

- 公司侧用户和 Portfolio Manager 都不会直接看到知识库文档本身 —— 他们只通过 chatbot 的自然语言回复与知识库交互。MVP 阶段没有"浏览 playbooks"的 UI。
- 用于上传与管理 playbook 内容的内部管理界面在 MVP 阶段不需要做到消费级精致 —— 只需可用、可靠。一个具备文档列表、状态指示器、上传能力与删除功能的简洁界面即可。
- 在面向 chatbot 用户侧，当某条回复大量引用了 GS playbook 内容时，加上一个不显眼的归属标识是合适的，例如 "Based on GS best practices"，让用户理解指引的来源，但不暴露具体的文档名或内容。
- 推荐采用 markdown 文件作为主要的内容管理格式，因为它对人类可读、轻量、便于人和 AI 处理，并且易于进行版本管理和持续更新。

**额外验收标准（RAG 细节，Additional Acceptance Criteria - RAG specifics）**

- 实现一个后端摄取流水线，能够接收常见格式的 playbook 文档（至少支持 PDF、Word .docx 与 markdown .md），并将其处理为可供 RAG 检索的 vector store。
- 知识库摄取流水线必须与 "AI Architecture & Model Routing Foundation" 故事中所建立的 RAG 架构兼容。
- 一组初始的 GS playbooks 会被摄取，并作为本故事验收测试的一部分被验证 —— 知识库在上线时不能为空。

### 依赖与备注

- 依赖前置故事 "AI Architecture & Model Routing Foundation"（用于 RAG 架构）。
- 内容编辑权限：Portfolio Group Manager 及以上。
- LLM 自动从对话中识别知识库更新的能力为 post-MVP，本故事不构建。
- 架构必须为 per-tenant 知识库隔离做预留，避免后续大规模重构。

---

