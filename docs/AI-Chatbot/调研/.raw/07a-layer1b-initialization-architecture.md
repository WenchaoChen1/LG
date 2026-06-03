---
asana_id: 1214953638826115
lg_id: LG-1397
title: Company Memory File Layer 1b Backend - Initialization & Architecture (Portfolio Admin)
status: Needs Sizing
section: Backlog
priority: High
type: User Story
ui_needed: false
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
split_from: LG-1330 (Company Memory File - Layer 1b Backend)
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214953638826115
note: TBD if the PA user is scoped to the Portfolio level or Global level
---

## English Notes（Asana 原文）

**NOTE: TBD if the PA user is scoped to the Portfolio level or Global level**

### Business Requirements

This story covers the creation of the Layer 1b memory file per company and the foundational architecture that enforces its separation from Layer 1a and its restriction to portfolio manager access only. A Layer 1b store must be created for each company upon first chatbot initialization, entirely separate from the Layer 1a file at the data layer. The two files are never merged, combined, or co-mingled.

Layer 1b is **never accessible** to company-side users through any mechanism — not through the UI, not through chat responses, and not through prompt injection regardless of how a prompt is worded.

### Acceptance Criteria

- A Layer 1b memory file is automatically created for each company upon first initialization of the AI chatbot for that company by the Portfolio Admin user
- Layer 1a and Layer 1b are stored and managed as entirely separate data structures — never merged or co-mingled at the data layer
- Layer 1b is queryable only by Portfolio Manager and Admin roles — never queryable by Company User or Company Admin roles under any circumstances
- The AI model is constrained at the **architecture level** to prevent surfacing Layer 1b content to company-side users regardless of how a chat prompt is worded
- Company-side users receive a **neutral non-revealing response** if they attempt to extract Layer 1b content — the response does not confirm or deny the existence of Layer 1b
- No Layer 1b content flows into Layer 2 (GS Knowledge Base) under any circumstances
- No Layer 1b content from one company is accessible to any other company
- Memory entries stored with source type and timestamp metadata
- Architecture supports read-only access for Portfolio Manager and Admin roles via Memory Settings UI stories

### UX Design Considerations

- Backend and data architecture story — no user-facing UI in scope.

## Asana 业务评论

仅含 sizing 提醒 bot 评论。

## 中文整理

详见 [part-B-memory-kb.md § B.1](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 提议从原 LG-1330 拆出 Init & Architecture 为独立 User Story（与 LG-1398 chat extr & doc upload 解耦）。Karen 5/18 同意。
