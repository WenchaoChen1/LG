---
asana_id: 1214953638826116
lg_id: LG-1398
title: Company Memory File Layer 1b Backend - Chat Extraction & Document Upload Processing (Portfolio Admin)
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1330
depends_on_research: LG-1385 (Layer 1b Chat Content - Company Association)
related: LG-1399 (Document Upload Portfolio Admin)
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826116
note_1: TBD if the PA user is scoped to the Portfolio level or Global level
note_2: Potential updates needed after completion of LG-1385
---

## English Notes（Asana 原文）

**NOTE 1**: TBD if the PA user is scoped to the Portfolio level or Global level
**NOTE 2**: Potential updates needed after the completion of [LG-1385](https://app.asana.com/1/1170332106480422/task/1214913562391163)

### Business Requirements

This story covers the population of the Layer 1b memory file from portfolio manager chat sessions and document uploads. Content extracted from portfolio manager chat sessions about a specific company is routed to that company's Layer 1b file following the **same real time extraction approach used in Layer 1a**, with the same content type groupings applicable. The same extraction quality rules apply — only meaningful, company-relevant learnings are saved. The same content types excluded from Layer 1a extraction are also excluded here.

For **document uploads** by portfolio managers, the company association logic established in the Document Upload story applies: the AI infers the likely company from conversation context and surfaces a confirmation prompt. If confirmed, the document is RAG-indexed and summarized into the identified company's Layer 1b file. If no company is selected, the document is treated as a session-only file and not stored in any Layer 1b memory.

### Acceptance Criteria

- **This story depends on the research ticket LG-1385 being complete before AC is finalized**
- Content extracted from portfolio manager chat sessions routed to correct company's Layer 1b file based on approach defined in research output
- Real time extraction trigger and quality rules **mirror those defined for Layer 1a**
- Same content type groupings from Layer 1a apply to Layer 1b extraction
- For PM document uploads: AI infers likely company from conversation context and displays confirmation prompt before processing
- PM confirms inferred company → document RAG-indexed + summary stored in that company's Layer 1b file
- PM selects different company than AI inferred → document processed for manually selected company
- PM dismisses prompt without selection → document NOT stored in any Layer 1b memory file — exists only as a file in current chat session
- Multi-company sessions handled correctly — learnings from single session may be distributed across multiple companies' Layer 1b files based on attribution logic from research output

### UX Design Considerations

- Backend and data architecture story — no user-facing UI in scope (UI covered by LG-1399 + LG-1336).

## Asana 业务评论

仅含 sizing 提醒 bot 评论。

## 中文整理

详见 [part-B-memory-kb.md § B.2](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1330 拆出"Chat Extraction & Document Upload Processing"为独立 User Story（与 LG-1397 Init 解耦），且明确依赖 Research LG-1385 完成后才能 finalize AC。Karen 5/18 同意。
