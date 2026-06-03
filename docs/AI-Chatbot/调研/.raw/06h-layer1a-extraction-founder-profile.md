---
asana_id: 1214953638826108
lg_id: LG-1396
title: Company Memory File Layer 1a Backend - Chat Extraction Founder Profile
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1329
extraction_category: Founder Profile (psychographic / leadership)
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826108
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the real-time incremental extraction of founder psychographic and leadership profile signals from company-side chat conversations. Understanding how a founder thinks, communicates, and makes decisions gives the AI the ability to frame its responses in a way that is most effective for that specific person — not just accurate but genuinely useful given who is receiving the information.

Examples:
- A conflict-avoidant founder who tends to defer difficult conversations needs different framing than a direct, data-driven founder who wants unvarnished analysis.
- A founder who thinks visually benefits from different communication approaches than one who processes through detailed written frameworks.

The founder profile is built incrementally and **subtly** — picking up on signals naturally present in how the founder writes, what they ask about, how they respond to challenges, and what language they use. The profile is stored in Layer 1a and is **accessible to the company admin user** (can be reviewed and corrected, helping user improve chat experience).

**Important**: The founder profile in Layer 1a represents the AI's **observed characterization** based on conversation signals. Memory entry framed accordingly so if a founder views it, it reads as an **observed tendency** rather than a label (e.g., "tends to think through decisions by talking them out" rather than "extroverted decision-maker"). The portfolio manager's separate Layer 1b memory file may contain GS's own internal perspective on the founder which may differ (handled in separate story).

### Acceptance Criteria

**Extraction Trigger**: Real-time, incremental, async.

**Founder Profile Signal Extraction**
- Correctly identifies/extracts signals about founder's leadership style, communication preferences, decision-making tendencies when patterns emerge
- Qualifying signal types (open list): conflict avoidance vs directness, data-driven vs intuition-driven decision-making, communication style (concise vs exploratory), how they respond to challenges/difficult feedback, areas of strong conviction vs uncertainty
- Profile observations stored as observed tendencies with appropriate **hedging language** — NOT definitive labels (e.g., "appears to prefer data-driven framing when discussing financial performance" not "data-driven")
- **Single-message signals NOT sufficient** to create profile entry — requires pattern across multiple exchanges

**Profile Accessibility**
- Founder profile entries in Layer 1a accessible to Company Admin in Memory Settings read-only panel
- Profile entries displayed as observed tendencies rather than definitive assessments
- AI uses founder profile context to inform response framing (more direct framing for direct communicators, more exploratory framing for founders who think out loud)
- Portfolio manager's GS-internal perspective on founder lives separately in Layer 1b — **not the same** as Layer 1a founder profile

**Conflict & Update Handling**
- Signals over time suggest prior observation inaccurate/changed → entry updated to most current
- Most recent profile observations always treated as authoritative

**Performance & Error Handling**: 同 LG-1391。

### UX Design Considerations

- Backend story — no UI in scope here (UI surface in LG-1333 Company User Memory File Access UI).

## Asana 业务评论

仅含 sizing 提醒 bot 评论。

## 中文整理

详见 [part-B-memory-kb.md § A.8](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1329 拆出 Founder Profile（创始人画像）为独立 User Story。该类别在 5/8 Dougal BR meeting 中重点强调（涉及创始人心理画像 / leadership 风格的观察性建模）。
