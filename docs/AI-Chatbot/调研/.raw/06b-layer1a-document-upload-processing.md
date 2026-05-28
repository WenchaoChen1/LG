---
asana_id: 1214913562391187
lg_id: LG-1388
title: Company Memory File Layer 1a Backend - Document Upload Processing
status: Needs Sizing
working_status: Not Started
section: Backlog
section_in_epic: EPIC: AI Chatbot (1211653019675507)
priority: High
type: User Story
ui_needed: false
due_on: 2026-05-21
created_at: 2026-05-19
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1329 (Company Memory File - Layer 1a Backend)
related: LG-1400 (Document Upload Company Portal)
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214913562391187
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the processing of documents uploaded by company-side users within the chat interface and their storage in the Layer 1a memory file. When a company-side user uploads a document, two parallel processes must occur: the document is RAG-indexed for dynamic retrieval in current and future sessions, and the system auto-generates a high-level summary of key company-relevant learnings from the document and saves that summary as a Layer 1a memory entry.

Uploaded documents and all derived content are strictly scoped to the originating company's Layer 1a memory file. They do not flow into Layer 1b or the GS Knowledge Base (Layer 2) under any circumstances.

### Acceptance Criteria

- When a company-side user uploads a document in chat, two parallel processes are triggered: RAG indexing of the full document for dynamic retrieval, and auto-generation of a high-level summary of key company-relevant learnings saved as a Layer 1a memory entry
- Both the RAG index and the memory summary are strictly scoped to the originating company's Layer 1a file
- Document content does not flow into Layer 1b or Layer 2 under any circumstances
- **Document RAG indexing completes within a reasonable time after upload - target within 30 seconds for typical document sizes**
- Memory entries from document processing are stored with source type (document summary), document name, and timestamp metadata
- Failed document processing is logged for investigation without surfacing any error to the end user - the chatbot continues to function normally if a memory update fails
- Document Uploads are covered in story [LG-1400 / LG-1399](https://app.asana.com/1/1170332106480422/task/1214057483533666)

### UX Design Considerations

- This is a backend and data architecture story - there is no user-facing UI in scope here.

## Asana 业务评论

仅含 sizing 提醒 bot 评论；无业务讨论。

## 中文整理

详见 [part-B-memory-kb.md § A.2](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 评论提议从原 LG-1329 拆出（覆盖"Document Upload"source 语义）。
