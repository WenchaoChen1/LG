---
asana_id: 1214953638826119
lg_id: LG-1400
title: AI Chatbot - Document Upload for Chat Analysis (Company Portal)
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1340 (AI Chatbot - Document Upload for Chat Analysis)
related: LG-1399 (Document Upload Portfolio Admin), LG-1388 (Layer 1a Document Upload Processing)
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826119
---

## English Notes（Asana 原文）

### Business Requirements

Company-side users must be able to upload documents directly within the company-facing AI chatbot interface to provide additional context for their conversations. This enables users to share information with the chatbot that is not yet in Looking Glass — for example, a financial spreadsheet with data not yet entered into the system, or a meeting transcript they want the chatbot to summarize or extract insights from.

Uploaded documents are NOT imported into Looking Glass or processed by the financial data pipeline. They are handled through a two-part process:
1. RAG indexing (full content dynamically queryable during current and all future chat sessions)
2. Auto-generated high-level summary saved to appropriate memory file layer

The memory layer that receives the document summary is determined by the role of the uploading user. **Company association for these uploads is always implicit** — company-side users are always in the context of their own company so **no confirmation prompt is needed**. All uploaded documents are strictly scoped to the company in which they are uploaded.

MVP supported file types: PDF, Word (.docx), Excel (.xlsx, .xls), CSV, plain text (.txt).

### Acceptance Criteria

**Upload Functionality**
- Users can upload a file directly from chat input bar via attachment button
- Supported file types for MVP: PDF, Word (.docx), Excel (.xlsx, .xls), CSV, .txt
- After upload, chatbot acknowledges and confirms it's ready ("I've received your file. You can now ask me questions about it.")
- Document is RAG-indexed for dynamic retrieval in current and future sessions
- System auto-generates high-level summary saved to appropriate memory file layer immediately upon upload
- Chatbot can accurately answer questions about content both immediately and in future sessions
- Multiple files within single session supported
- Unsupported file type → clear inline error message
- File size limit → clear inline message
- Works on desktop and mobile

**Memory Layer Routing**
- Documents uploaded by company-side users (Company User or Company Admin) → stored in company's **Layer 1a** memory file
- Uploaded documents do not feed into GS Knowledge Base (Layer 2) under any circumstances
- Uploaded documents never accessible to other companies regardless of layer
- Memory layer routing enforced automatically by system based on uploading user's role

**Knowledge Base Panel - File Visibility**
- Knowledge Base section in chat interface displays all documents uploaded in company context
- List view: file name / type / upload date / uploader name; per-file download; **NO in-app preview for MVP**
- File visibility role-scoped:
  - **Company User**: sees ONLY files they personally uploaded
  - **Company Admin**: sees all files uploaded by any user within their company stored in Layer 1a. **Layer 1b files NEVER visible to any company-side user regardless of role**

### UX Design Considerations

- Upload action lightweight and natural — simple attachment icon
- After upload: small file chip/badge in chat thread confirming what was uploaded
- Chatbot's acknowledgment includes suggested first action
- Subtle note in acknowledgment that document saved for future reference (does NOT reference which memory layer)
- File size/type errors inline in chat (not disruptive modal)
- Knowledge Base section as secondary panel/tab, distinct from main conversation thread
- Empty state friendly and instructive

## Asana 业务评论

仅含 sizing 提醒 bot 评论（3 条）；无业务讨论。

## 中文整理

详见 [part-D-portfolio-shared.md § 5](../part-D-portfolio-shared.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1340 拆出 **Company Portal 上传流程**为独立 User Story（与 LG-1399 Portfolio Admin 上传流程解耦）。核心差异：**Company Portal 公司归属隐式、无 confirmation prompt**。Karen 5/18 同意。
