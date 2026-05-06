---
gid: 1214057483533666
name: AI Chatbot - Document Upload for Chat Analysis
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533666
---

# AI Chatbot - Document Upload for Chat Analysis

Business Requirements

Users must be able to upload documents directly within the AI chatbot interface to provide additional context for their conversations. This enables users to share information with the chatbot that is not yet in Looking Glass, for example, a financial spreadsheet with data not yet entered into the system, or a meeting transcript they want the chatbot to summarize or extract insights from.

Uploaded documents are not imported into Looking Glass or processed by the financial data pipeline. They are handled through a two-part process. First, the document is processed and indexed via RAG (retrieval-augmented generation), making its full content dynamically queryable during the current and all future chat sessions. This means the AI can retrieve specific, relevant sections of the document in response to user questions. Second, the system auto-generates a high-level summary of key company-relevant learnings from the document and saves that summary to the company's Layer 1 memory file. This ensures that the most important things learned from the document persist as context even in future conversations that do not explicitly reference the original file.

All uploaded documents are strictly scoped to the company in which they are uploaded. They are never accessible to other companies and do not feed into the shared GS Knowledge Base (Layer 2) under any circumstances.

For MVP, supported file types cover the primary use cases: PDFs and Word documents for reports and financial files, Excel and CSV files for structured data, and plain text files (.txt) for exported meeting transcripts such as those from Fireflies.

Acceptance Criteria

    Users can upload a file directly from the chat input bar using an attachment button - available to both company-side and portfolio users.
    Supported file types for MVP: PDF, Word (.docx), Excel (.xlsx, .xls), CSV, and plain text (.txt).
    After upload, the chatbot acknowledges the document and confirms it is ready to be referenced (e.g., "I've received your file. You can now ask me questions about it.").
    The uploaded document is processed and indexed via RAG, making its full content dynamically retrievable in the current and all future chat sessions.
    The system automatically generates a high-level summary of key company-relevant learnings from the document and saves that summary to the company's Layer 1 memory file immediately upon upload.
    The chatbot can accurately answer questions about the content of the uploaded document both immediately after upload and in future sessions.
    All uploaded documents and derived content are strictly scoped to the originating company's Layer 1 context, they are never shared with other companies and do not feed into the GS Knowledge Base (Layer 2).
    Users can upload multiple files within a single conversation session.
    If an unsupported file type is uploaded, the system displays a clear inline error message indicating which file types are supported.
    File size limits are enforced with a clear inline message if a file exceeds the limit.
    A dedicated Knowledge Base section in the chat interface displays all documents uploaded during sessions, including the GS Playbook (Layer 2) for authorized users. Documents are shown in a list view with file name, type, upload date, and uploader, supporting download only (no in-app preview for MVP). Visibility is role-based: company-side users see only their own company's documents and cannot access the GS Playbook, while portfolio managers and admins see all documents within their scope.

UX Design Considerations

    The upload action should feel lightweight and natural - a simple attachment icon within the chat input bar, consistent with familiar messaging app patterns. Users should not feel like they are doing something complex or technical.
    After upload, display a small file chip or badge in the chat thread confirming what was uploaded (file name and type).
    The chatbot's acknowledgment message after upload should include a suggested first action to help the user get started (e.g., "Would you like me to summarize this document, or do you have a specific question about it?").
    Include a subtle note in the acknowledgment that the document has been saved for future reference (e.g., "This file has also been added to your company's memory so I can reference it in future conversations.").
    File size or type errors should appear inline in the chat, not as a disruptive modal or system alert.
    The Knowledge Base section should be accessible as a secondary panel or tab within the chat interface, distinct from the main conversation thread. Present uploaded files in a clean list format showing file name, type, and upload date. Download should be a simple icon action per row. Since the GS Playbook and user-uploaded files live in the same section, use clear visual grouping or labels to distinguish between "Uploaded Documents" and "GS Playbook." Do not surface the Knowledge Base section if no documents have been uploaded and no Playbook is loaded - show an appropriate empty state instead.
