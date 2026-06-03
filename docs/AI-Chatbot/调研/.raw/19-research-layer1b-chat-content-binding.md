---
asana_id: 1214913562391163
lg_id: LG-1385
title: Research - Layer 1b Chat Content - Company Association and Memory Binding Logic
status: Needs Sizing
section: Backlog
priority: High
type: Research task
ui_needed: false
due_on: 2026-05-20
created_at: 2026-05-18
modified_at: 2026-05-21
assignee: wenchao
parent_epic: EPIC: AI Chatbot
created_by_context: Karen Arnoldi 2026-05-18 created in response to Liang Chunru's proposal in LG-1330
informs: LG-1398 (Layer 1b Chat Extraction & Doc Upload), LG-1335 (PM Core Chat UI), LG-1336 (PM Memory Settings UI)
permalink: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214913562391163
---

## English Notes（Asana 原文）

### Business Requirements

When a portfolio manager is chatting with the AI chatbot, the system needs to extract meaningful learnings from those conversations and write them into the correct company's Layer 1b memory file. Unlike company-side users who are always chatting in the context of a single company, **portfolio managers may discuss multiple companies within a single conversation session**, asking about one company's ARR, switching to discuss another company's burn rate, and then making a comparative observation across both. This creates a challenge: how does the system reliably determine which parts of a conversation are about which company, so that extracted learnings are written into the correct company's Layer 1b memory file?

For **document uploads**, a confirmation prompt workflow has been defined where the AI infers the likely company and asks the portfolio manager to confirm before processing the document into Layer 1b. However for **chat-derived content extraction** which is the primary mechanism for building the Layer 1b memory file over time, a confirmation prompt after every message is NOT a viable user experience. The system needs a reliable, low-friction approach to company attribution that does not require the portfolio manager to constantly confirm which company they are talking about.

This research task is needed to evaluate the technical feasibility of AI-based company inference for chat content, identify the risks and failure modes, and propose a recommended approach before this logic is written into story acceptance criteria. Without this research, any AC written for Layer 1b chat extraction would be speculative and likely require significant revision during development.

### Acceptance Criteria

**Inference Approach Evaluation**
- Team researches and documents the feasibility of using AI-based inference to determine which company a segment of portfolio manager chat conversation is about, based on context signals such as company names mentioned, financial figures referenced, and conversational context
- Research identifies the confidence threshold approach — at what level of certainty should the system automatically attribute content to a company vs. surface a confirmation prompt to the user
- Research documents the failure modes — what types of conversations are most likely to produce incorrect or ambiguous company attribution, and how should the system handle those cases

**Proposed Technical Approach**
- Research proposes specific technical approach for how chat content is attributed to companies and written into Layer 1b, including whether attribution happens **in real time during conversation, at end of session during extraction pass, or through hybrid approach**
- Proposed approach includes recommendation on how to handle multi-company conversations where single extraction pass may need to split learnings across multiple companies' Layer 1b files
- Proposed approach addresses what happens when system cannot confidently attribute content to any company — whether content is discarded, stored in general PM-level context, or flagged for manual review

**Output**
- Research output documented in format that can inform the rewriting of Layer 1b acceptance criteria before development begins
- Product team can use this output to make final decisions on Layer 1b extraction approach and the **PM chat entry point scoping question**

### UX Design Considerations

- Research story — no UI in scope; output influences LG-1335 (PM Core Chat UI) and LG-1336 (PM Memory Settings UI) decisions.

## Asana 业务评论

- 2026-05-18 系统：sizing 提醒
- 2026-05-21 系统：This task is overdue — please check the dates and let us know if you're facing any blockers

## 中文整理

详见 [part-A-foundation.md § 7](../part-A-foundation.md)。

## 创建背景

Karen Arnoldi 在 2026-05-18 创建此 Research，回应 Liang Chunru 在 LG-1330 2026-05-18 评论中的具体建议：

> "For determining how chat content gets associated with a specific company and written into Layer 1b, we believe AI-based inference is the right direction but the approach needs more investigation before we can commit to a specification. We recommend opening a dedicated research ticket to evaluate feasibility before this is written into the AC."

Karen 2026-05-18 在 LG-1330 中评论："I created a research ticket for this [LG-1385]" — 即本 ticket。

## 下游影响

- **LG-1398**（Layer 1b Backend - Chat Extraction & Document Upload Processing）：AC 在本 Research 完成后才能 finalize
- **LG-1335 / LG-1336**：PM Chat Entry Point 决策（绑 portfolio 级 vs global 级，Liang 5/18 建议 vs Karen 5/18 顾虑）依赖本 Research 输出
- **LG-1399**（Document Upload Portfolio Admin）：confirmation prompt 工作流已采纳，但若 Research 输出影响 chat 抽取归属逻辑，可能反向调整 doc upload 的归属 UX
