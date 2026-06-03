---
asana_gid: 1214057483533666
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533666
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:22:04.409Z
lg_ticket: LG-1340
type: 
story_points: 
t_shirt: XL
priority: 
completed: False
---

# AI Chatbot - Document Upload for Chat Analysis

Business Requirements

Users must be able to upload documents directly within the AI chatbot interface to provide additional context for their conversations. This enables users to share information with the chatbot that is not yet in Looking Glass, for example, a financial spreadsheet with data not yet entered into the system, or a meeting transcript they want the chatbot to summarize or extract insights from.
Uploaded documents are not imported into Looking Glass or processed by the financial data pipeline. They are handled through a two-part process. First, the document is processed and indexed via RAG (retrieval-augmented generation), making its full content dynamically queryable during the current and all future chat sessions. Second, the system auto-generates a high-level summary of key company-relevant learnings from the document and saves that summary to the appropriate memory file layer. This ensures that the most important things learned from the document persist as context even in future conversations that do not explicitly reference the original file.
The memory layer that receives the document summary is determined by the role of the uploading user. Documents uploaded by company-side users (Company User or Company Admin) are stored in the company's Layer 1a memory file, the shared company context that is visible to both company users and portfolio managers. Documents uploaded by portfolio managers in the context of a specific company are stored in that company's Layer 1b memory file, the internal GS context layer that is visible only to portfolio managers and above and is never accessible to company-side users.
All uploaded documents are strictly scoped to the company in which they are uploaded. They are never accessible to other companies and do not feed into the GS Knowledge Base (Layer 2) under any circumstances.
For MVP, supported file types cover the primary use cases: PDFs and Word documents for reports and financial files, Excel and CSV files for structured data, and plain text files (.txt) for exported meeting transcripts such as those from Fireflies.


Acceptance Criteria

Upload Functionality
    Users can upload a file directly from the chat input bar using an attachment button - available to both company-side and portfolio manager users.
    Supported file types for MVP: PDF, Word (.docx), Excel (.xlsx, .xls), CSV, and plain text (.txt).
    After upload, the chatbot acknowledges the document and confirms it is ready to be referenced (e.g., "I've received your file. You can now ask me questions about it.").
    The uploaded document is processed and indexed via RAG, making its full content dynamically retrievable in the current and all future chat sessions.
    The system automatically generates a high-level summary of key company-relevant learnings from the document and saves that summary to the appropriate memory file layer immediately upon upload.
    The chatbot can accurately answer questions about the content of the uploaded document both immediately after upload and in future sessions.
    Users can upload multiple files within a single conversation session.
    If an unsupported file type is uploaded, the system displays a clear inline error message indicating which file types are supported.
    File size limits are enforced with a clear inline message if a file exceeds the limit.
    The feature is fully functional on both desktop and mobile devices.
Memory Layer Routing
    Documents uploaded by company-side users (Company User or Company Admin) are processed and stored in the company's Layer 1a memory file.
    Documents uploaded by portfolio managers in the context of a specific company are processed and stored in that company's Layer 1b memory file.
    Neither Layer 1a nor Layer 1b uploaded documents feed into the GS Knowledge Base (Layer 2) under any circumstances.
    Uploaded documents are never accessible to other companies regardless of which layer they are stored in.
    Memory layer routing is enforced automatically by the system based on the uploading user's role
Knowledge Base Panel - File Visibility
    A Knowledge Base section in the chat interface displays all documents uploaded within the company context. Documents are shown in a list view with file name, type, upload date, and uploader name. Download is supported per file (simple icon action per row). No in-app preview is required for MVP.
    File visibility in the Knowledge Base panel is role-scoped as follows:
        Company User: sees only files they personally uploaded. Files uploaded by other users within the same company are not visible, regardless of whether those files are stored in Layer 1a.
        Company Admin: sees all files uploaded by any user within their company that are stored in Layer 1a. Layer 1b files are never visible to any company-side user regardless of role.
        Portfolio Manager / Admin: sees all Layer 1a uploaded files for all companies within their access scope, and all Layer 1b uploaded files for those same companies. Layer 1a and Layer 1b files are visually grouped and clearly labeled so portfolio managers can immediately understand which files are visible to company users ("Company Documents") and which are internal only ("Internal GS Documents").

UX Design Considerations

    The upload action should feel lightweight and natural - a simple attachment icon within the chat input bar.
    After upload, display a small file chip or badge in the chat thread confirming what was uploaded (file name and type).
    The chatbot's acknowledgment message after upload should include a suggested first action to help the user get started (e.g., "Would you like me to summarize this document, or do you have a specific question about it?").
    Include a subtle note in the acknowledgment that the document has been saved for future reference (e.g., "This file has also been added to your company's memory so I can reference it in future conversations.") - the note should not reference which memory layer it went to.
    File size or type errors should appear inline in the chat, not as a disruptive modal or system alert.
    The Knowledge Base section should be accessible as a secondary panel or tab within the chat interface, distinct from the main conversation thread.
    Within the Knowledge Base panel, use clear visual grouping and labels to distinguish between "Company Documents" (Layer 1a), "Internal GS Documents" (Layer 1b - visible to portfolio managers only), and "GS Playbook" (Layer 2 - visible to portfolio managers only). Do not surface the Layer 1b or Layer 2 sections to company-side users at all - they should see only their own uploads or company uploads depending on their role.
    The Layer 1b grouping label should be understated but clearly informative for portfolio managers - e.g., "Internal GS Documents - not visible to company users" - so they always know what they are looking at.
    The empty state for the Knowledge Base panel should be friendly and instructive - e.g., "No documents uploaded yet. Upload a file in the chat to get started."
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

https://app.asana.com/app/asana/-/get_asset?asset_id=1214687052273915

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-04-27 · Liang Chunru**：是否需要 UI 内专门区域展示 chat 中上传的文件（list view，可下载但不在线查看）？建议合并到 Knowledge Base section（GS Playbook 也在其中），按角色控制可见性。
- **2026-04-27 · Karen Arnoldi**：Great idea，加入。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 5. AI Chatbot - 用于聊天分析的文档上传（Document Upload for Chat Analysis）

- **Asana ID**: 1214057483533666
- **LG 编号**: LG-1340
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = XL）
- **最近修改**: 2026-05-11
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

