---
asana_id: 1214953638826120
lg_id: LG-1399
title: AI Chatbot - Document Upload for Chat Analysis (Portfolio Admin)
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1340 (AI Chatbot - Document Upload for Chat Analysis)
depends_on_research: LG-1385 (Layer 1b Chat Content - Company Association)
related: LG-1400 (Document Upload Company Portal), LG-1398 (Layer 1b Chat Extr & Doc Upload)
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826120
note_1: TBD if the PA user is scoped to the Portfolio level or Global level
note_2: Potential updates needed after completion of LG-1385
---

## English Notes（Asana 原文）

**NOTE 1**: TBD if the PA user is scoped to the Portfolio level or Global level
**NOTE 2**: Potential updates needed after the completion of [LG-1385](https://app.asana.com/1/1170332106480422/task/1214913562391163)

### Business Requirements

Portfolio managers must be able to upload documents within the admin portal AI chatbot interface. This enables users to share information with the chatbot that is not yet in Looking Glass.

Uploaded documents are not imported into Looking Glass or processed by the financial data pipeline. Two-part process: (1) RAG indexing; (2) auto-generated summary saved to appropriate memory layer.

**Unlike company-side uploads where the company context is always implicit, portfolio manager uploads require a company association step before the document can be processed into a company's Layer 1b memory file.** The AI will attempt to infer which company the document relates to based on conversation context and surface a confirmation prompt. If the AI cannot make a confident determination, the portfolio manager is prompted to manually select the company. If no company is selected, the document is NOT stored in any Layer 1b memory file but remains accessible as a file within that chat session.

All uploaded documents are strictly scoped to the company in which they are uploaded. They are never accessible to other companies and do not feed into the GS Knowledge Base (Layer 2) under any circumstances.

MVP supported file types: PDF, Word (.docx), Excel (.xlsx, .xls), CSV, .txt.

### Acceptance Criteria

**Upload Functionality**
- Users can upload via attachment button
- Supported file types same as LG-1400
- Acknowledgment after upload
- RAG indexing
- Auto-generated summary saved to appropriate memory layer
- Accurate Q&A on content in current and future sessions
- **Multiple files in single session — each triggers its own company association confirmation**
- Inline errors for unsupported type / file size limit
- Desktop and mobile

**Memory Layer Routing (核心差异)**
- After upload AI attempts to infer which company the document relates to based on conversation context
- System surfaces confirmation prompt to portfolio manager showing inferred company, asking for confirmation before processing
- PM confirms inferred company → document RAG-indexed + summary stored in that company's **Layer 1b** memory file
- PM selects different company → document processed for manually selected company
- PM doesn't select or dismisses prompt → document NOT stored in any Layer 1b memory file — exists only as file in current chat session and is so indicated to user
- Confirmation prompt clearly indicates which memory layer document will be stored in ("This document will be added to [Company Name]'s internal GS memory")
- Layer 1b uploaded documents do not feed into Layer 2 (GS Knowledge Base) under any circumstances

**Knowledge Base Panel - File Visibility**
- Knowledge Base section in chat interface displays all documents uploaded in company context
- List view: file name / type / upload date / uploader name; per-file download; **NO in-app preview for MVP**
- File visibility role-scoped:
  - **Portfolio Manager / Admin**: sees all Layer 1a uploaded files for all companies within their access scope, and all Layer 1b uploaded files for those same companies
  - Layer 1a and Layer 1b files **visually grouped and clearly labeled**: "Company Documents" (Layer 1a) vs "Internal GS Documents - not visible to company users" (Layer 1b)

### UX Design Considerations

- Upload action lightweight and natural
- File chip/badge in chat thread
- Acknowledgment includes suggested first action
- Subtle note that document saved for future reference
- File size/type errors inline
- Knowledge Base section: clear visual grouping/labels distinguishing "Company Documents" (Layer 1a) / "Internal GS Documents" (Layer 1b - PM only) / "GS Playbook" (Layer 2 - PM only)
- Layer 1b grouping label understated but clearly informative: "Internal GS Documents - not visible to company users"
- Empty state friendly and instructive

## Asana 业务评论

仅含 sizing 提醒 bot 评论（3 条）；无业务讨论。

## 中文整理

详见 [part-D-portfolio-shared.md § 6](../part-D-portfolio-shared.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1340 拆出 **Portfolio Admin 上传流程**为独立 User Story（与 LG-1400 Company Portal 上传流程解耦）。核心差异：**需要 AI 推断公司 + PM confirmation prompt**；归属逻辑细节依赖 LG-1385 Research 输出。Karen 5/18 同意。
