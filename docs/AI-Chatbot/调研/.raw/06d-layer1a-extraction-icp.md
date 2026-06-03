---
asana_id: 1214953638826104
lg_id: LG-1392
title: Company Memory File Layer 1a Backend - Chat Extraction ICP and Customer Profile
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
split_from: LG-1329
extraction_category: ICP and Customer Profile
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826104
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the real-time incremental extraction of Ideal Customer Profile (ICP) and customer-related context from company-side chat conversations. The system should build out the ICP profile **incrementally** across conversations rather than expecting founders to provide it all at once. As founders discuss their customers, deals, churn, expansions, and go-to-market approaches, the AI extracts and accumulates relevant signals about customer characteristics, buying behavior, and ICP definition. This includes:

- Primary ICP description (industry, size, role, pain point)
- Multiple ICPs and what distinguishes them
- Churn patterns tied to specific customer segments (stored as the **strategic pattern**, e.g., "seasonal churn from SMB ICP", not individual customer names or events)
- Context about how the ICP is evolving or changing over time

### Acceptance Criteria

**Extraction Trigger**: Real-time and incremental, async, non-blocking.

**ICP Extraction**
- Correctly identifies and extracts primary ICP descriptions (industry, company size, buyer role, core pain point)
- Multiple distinct ICPs → each stored as separate memory entry with distinguishing context
- Statements about ICP evolving/changing → update existing ICP entry to current understanding
- Extract contextual info about the value the product delivers to each ICP (ROI story, key benefits, differentiation) when surfaced

**Customer Pattern Extraction**
- Churn patterns tied to customer segments/ICPs extracted as strategic patterns ("seasonal churn from SMB customers", "enterprise ICP showing lower churn than expected")
- **Individual customer names, specific deal outcomes, and one-time customer events explicitly EXCLUDED**
- Customer success patterns ("enterprise customers consistently expand after 6 months") extracted when mentioned

**Conflict & Update Handling**
- ICP changed/evolved → update existing ICP memory entry (not duplicate)
- Latest ICP description always treated as authoritative

**Performance & Error Handling**
- Failed extraction logged without surfacing to user
- Chatbot continues working if extraction fails

### UX Design Considerations

- Backend story — no UI in scope.

## Asana 业务评论

仅含 sizing 提醒 bot 评论。

## 中文整理

详见 [part-B-memory-kb.md § A.4](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议拆出 ICP 抽取为独立 User Story（属于原 LG-1329 中 5/8 BR meeting Dougal 提出的 8 类内容之一）。
