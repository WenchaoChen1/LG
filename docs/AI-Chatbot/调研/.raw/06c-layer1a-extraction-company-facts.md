---
asana_id: 1214953638826103
lg_id: LG-1391
title: Company Memory File Layer 1a Backend - Chat Extraction Company Facts & Data Corrections
status: Needs Sizing
working_status: Not Started
section: Backlog
section_in_epic: EPIC: AI Chatbot (1211653019675507)
priority: High
type: User Story
ui_needed: false
due_on: 2026-05-22
created_at: 2026-05-20
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1329 (Chat Extraction broad prompt)
extraction_category: Company Facts & Data Corrections
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826103
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the real-time incremental extraction of the first content grouping from company-side chat conversations: factual statements about the company that are not already captured in LG's structured data, and corrections or clarifications the user makes to existing LG data.

1. **Company facts** captures information a founder shares conversationally that has no corresponding structured field in Looking Glass. Examples: "we just signed our first enterprise customer", "we are the only provider focused on mid-market healthcare", team size/structure changes, recent fundraising or strategic shifts.
2. **Data corrections** captures instances where a founder indicates that a value stored in LG is incorrect or outdated. For example: "that revenue figure for March is wrong, it should be $1.1M". **Corrections stored in the memory file do not trigger any downstream updates to financial data, the normalization table, forecasts, or any other LG data structures.**

Both content types are extracted in real time at the point of conversation — the system evaluates each user message and AI response exchange as it occurs.

### Acceptance Criteria

**Extraction Trigger**
- Extraction is real-time and incremental — evaluates each user message and AI response exchange as it occurs
- Extraction processing runs asynchronously, does not block AI response delivery
- Only the most recent exchange is evaluated; full conversation history is not re-processed

**Company Facts Extraction**
- Correctly identifies and extracts factual statements not already captured in LG structured data
- Extracted facts stored as Layer 1a memory entries with source type (chat extraction) + timestamp
- Generic informational questions, transactional exchanges, opinion-based statements correctly excluded
- Information already accurately captured in LG structured data not re-extracted

**Data Corrections Extraction**
- Correctly identifies when a user indicates an LG stored value is incorrect/outdated
- Corrections stored with source type, timestamp, and context to identify which data point + the corrected value
- **Storing a correction does not trigger updates to financial data / Normalization Table / forecasts / any other LG data structures**
- AI can reference the stored correction when answering future questions about that data point

**Conflict & Update Handling**
- New extraction contradicting/materially updating existing entry → existing entry updated to latest
- Duplicate extraction of stored info prevented

**Performance & Error Handling**
- Failed extraction logged without surfacing error to user
- Chatbot continues working if individual extraction fails

### UX Design Considerations

- Backend and data architecture story — no user-facing UI in scope.

## Asana 业务评论

仅含 sizing 提醒 bot 评论；无业务讨论。

## 中文整理

详见 [part-B-memory-kb.md § A.3](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 评论提议从原 LG-1329（含 9 类抽取内容）拆出"Company Facts & Data Corrections"为独立 User Story。
