---
asana_id: 1214913562391185
lg_id: LG-1390
title: Company Memory File Layer 1a Backend - Initialization & Company Settings Seeding
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
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214913562391185
---

## English Notes（Asana 原文）

### Business Requirements

This story covers the creation and initial seeding of the Layer 1a memory file for each company. When the AI chatbot is first initialized for a company, the system must automatically create the company's Layer 1a store and populate it with all available structured data from Company Settings, including company name, description, business model, sector, industry, stage, and any other profile fields present in LG. This gives the AI a meaningful baseline understanding of the company from the very first conversation without any user input required. When Company Settings fields are subsequently updated, the memory file must be updated to reflect those changes automatically.

_Note: When the consultative onboarding epic is built, it is possible that the seeding of the layer1a memory file for the company will need to occur during onboarding IF the company entity is created at that time as there might be additional information about the company that is provided outside of the LG structured fields in Company Settings._

### Acceptance Criteria

- A Layer 1a memory file is automatically created for each company upon first initialization of the AI chatbot for that company
- The memory file is automatically seeded at initialization with all available Company Settings metadata: company name, description, business model, sector, stage, URL, and any other structured profile fields present in LG
- **The AI chatbot creates the memory file with understandings learned from the profile fields, not just storage of the data itself**. IE, the chatbot uses the URL field to "scrape" or learn about the company from the website.
- When any Company Settings field is updated by a user, the corresponding Layer 1a memory entry is automatically updated
- No user configuration is required to activate the memory file - it operates automatically
- The architecture supports the access control model required by dependent UI stories: Company Admin read-only access to their own company's Layer 1a, and Portfolio Manager read-only access to Layer 1a for companies within their access scope
- **NOTE: When the consultative onboarding epic is introduced the Company Memory File will need to be initialized during that workflow**

### UX Design Considerations

- This is a backend and data architecture story - there is no user-facing UI in scope here.

## Asana 业务评论

仅含 sizing 提醒 bot 评论；无业务讨论。

## 中文整理

详见 [part-B-memory-kb.md § A.1](../part-B-memory-kb.md)。

## 拆分背景

由 Liang Chunru 2026-05-18 评论提议从原 LG-1329 拆出（覆盖"Initialization"语义）。Karen Arnoldi 2026-05-18 同意拆分。
