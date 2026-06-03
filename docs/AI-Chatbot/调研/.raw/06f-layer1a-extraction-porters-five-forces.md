---
asana_id: 1214953638826106
lg_id: LG-1394
title: Company Memory File Layer 1a Backend - Chat Extraction Porter's Five Forces Profile
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1329
extraction_category: Porter's Five Forces Profile
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826106
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the real-time incremental extraction of Porter's Five Forces signals from company-side chat conversations, progressively building out a structured competitive environment profile for each company over time.

The 5 forces shaping competitive intensity and industry attractiveness:
1. **Competitive Rivalry**
2. **Threat of New Entrants**
3. **Bargaining Power of Buyers**
4. **Bargaining Power of Suppliers**
5. **Threat of Substitutes**

The profile is **not collected through a structured intake form**. Instead built incrementally as founders naturally share relevant context across many conversations:
- Discussing customer contract lengths and switching costs → buyer power
- Discussing cloud infrastructure dependencies → supplier power
- Discussing how hard it is for new startups to compete with their regulatory approvals → barrier-to-entry signals

Partial coverage (2-3 forces) gives the AI meaningful context. Treat profile as long-lived, continuously refined memory structure.

### Acceptance Criteria

**Extraction Trigger**: Real-time, incremental, async.

**Five Forces Extraction**
- Correctly identifies/extracts signals relevant to each of 5 forces:
  - **Competitive Rivalry**: intensity of competition, number/aggressiveness of competitors, market growth rate, product differentiation
  - **Threat of New Entrants**: barriers to entry (regulatory approvals, network effects, patents, capital requirements), perception of new threats
  - **Bargaining Power of Buyers**: customer price sensitivity, switching ease, revenue concentration risk, customer leverage
  - **Bargaining Power of Suppliers**: key technology/vendor dependencies, risks, switching ease
  - **Threat of Substitutes**: non-direct alternatives, risk of category disruption
- Each signal mapped to correct force, stored as Layer 1a memory entry with source type, timestamp, force category
- Single turn with multiple force signals → each extracted under appropriate force category

**Profile Refinement**
- New info updates/contradicts existing entry → updated to latest
- Long-lived structure; partial coverage valid from first extraction

**Performance & Error Handling**: 同 LG-1391。

### UX Design Considerations

- Backend story — no UI.

## Asana 业务评论

仅含 sizing 提醒 bot 评论。

## 中文整理

详见 [part-B-memory-kb.md § A.6](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1329 拆出 Porter's Five Forces 框架抽取为独立 User Story（属于 5/8 Dougal BR meeting 中 8 类内容之一）。
