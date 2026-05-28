---
asana_id: 1214953638826107
lg_id: LG-1395
title: Company Memory File Layer 1a Backend - Chat Extraction Strategic Context and Challenges
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1329
extraction_category: Strategic Context and Challenges
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826107
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the real-time incremental extraction of **strategic context** from company-side chat conversations — including business/pricing model details, value proposition and ROI story relative to ICP, **strategic challenges with staying power**, and key people in the organization and their roles.

Strategic context is information a portfolio manager or investor would most want to remember from one meeting to the next. The critical distinction is between **staying power** and **transience**:
- ✅ Pricing model is staying-power information — relevant for months/years
- ❌ Specific deal closed last Tuesday is transient — not worth long-term memory

**People and organizational context**: as founders reference team members ("get with our Head of Sales", "our CTO built our entire data pipeline"), AI extracts name + role + organizational relevance. Allows AI to reference the right people in future strategic suggestions.

### Acceptance Criteria

**Extraction Trigger**: Real-time, incremental, async.

**Business and Pricing Model Extraction**
- Business model context (SaaS, marketplace, services, hybrid, etc.)
- Pricing model details (seat-based, usage-based, value-based, services + software, etc.)
- Transitions/changes → update existing entries

**Value Proposition and ROI Story Extraction**
- Value proposition relative to ICP (problem solved, why customers pay, outcomes delivered)
- ROI stories and quantified customer outcomes ("our customers typically save 40% on processing costs")

**Strategic Challenges Extraction**
- Strategic challenges **with staying power** — relevant across multiple sessions, persistent pattern (not one-time event)
- Examples: sustained sales efficiency problem, GTM motion not working with specific ICP, PMF challenge in new segment
- **Transient specifics that will not be relevant in 3-6 months explicitly EXCLUDED** — store the pattern, not the instance
- Founder indicates prior challenge resolved → entry updated to current status

**People and Organizational Context Extraction**
- Key people with name + role + organizational relevance
- Organizational context for specific/actionable recommendations ("VP of Sales owns all enterprise deals", "Head of Finance is building out our financial model")
- Individual employee names without strategic context (e.g., customer success rep mentioned in passing) NOT extracted unless organizational significance

**Conflict & Update Handling**: 同 LG-1391。

**Performance & Error Handling**: 同 LG-1391。

### UX Design Considerations

- Backend story — no UI.

## Asana 业务评论

仅含 sizing 提醒 bot 评论。

## 中文整理

详见 [part-B-memory-kb.md § A.7](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1329 拆出"Strategic Context & Challenges"为独立 User Story。涵盖 5/8 Dougal BR meeting 中 4 类内容：Business/Pricing Model、Value Prop & ROI、Strategic Challenges with Staying Power、People & Org Structure。
