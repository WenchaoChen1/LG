---
asana_id: 1214953638826105
lg_id: LG-1393
title: Company Memory File Layer 1a Backend - Chat Extraction Competitive Landscape
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1329
extraction_category: Competitive Landscape
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826105
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the real-time incremental extraction of competitive landscape information from company-side chat conversations. Understanding who a company competes against, how they differentiate, and what the relative strengths and weaknesses of competitors are gives the AI critical context for strategic conversations. Competitive information is gathered incrementally as founders naturally reference competitors in conversation — when discussing deals won or lost, when describing their positioning, when talking about pricing challenges, or when seeking advice on competitive displacement.

The system extracts:
- Names of key competitors
- Founder's characterization of those competitors' strengths and weaknesses relative to their own product
- Context about how competitive dynamics are shifting over time
- **Substitution threats** — alternative approaches customers might consider that are not direct competitors — extracted when mentioned, as they represent a distinct and important category of competitive risk.

Competitive information stored in the memory file reflects the **founder's perspective** and should be treated as such — it is the founder's view of the competitive landscape, not an objective market assessment.

### Acceptance Criteria

**Extraction Trigger**: Real-time, incremental, async.

**Competitor Extraction**
- Correctly identifies/extracts names of competitors referenced in conversation
- For each: extract context about strengths/weaknesses relative to founder's product
- Competitive positioning statements extracted ("we win on ease of use but lose on enterprise feature depth")
- Competitive dynamics changes extracted ("a new well-funded competitor entered the market last quarter")

**Substitution Threat Extraction**
- Correctly identifies references to substitution threats (e.g., "most of our prospects are currently using spreadsheets and internal tools")
- Substitution threats stored as **distinct category** from direct competitors

**Completeness & Updates**
- New info contradicting/materially updating prior entry → existing updated
- Competitive info attributed as reflecting founder's perspective in storage/retrieval

**Performance & Error Handling**: 同 LG-1391。

### UX Design Considerations

- Backend story — no UI.

## Asana 业务评论

仅含 sizing 提醒 bot 评论。

## 中文整理

详见 [part-B-memory-kb.md § A.5](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1329 拆出 Competitors 抽取为独立 User Story。
