---
gid: 1214147930023560
name: Company Memory File - Layer 1b Backend (Portfolio Admin Context)
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023560
---

# Company Memory File - Layer 1b Backend (Portfolio Admin Context)

Business Requirements

This story covers the second distinct memory file per company - the Portfolio Admin Memory File. Unlike the Company Memory File (Layer 1a), which is visible to both company-side users and portfolio managers, the Portfolio Admin Memory File is strictly internal and visible only to Portfolio Manager and Admin roles. It is never accessible to company-side users under any circumstances - not through the UI, not through the Memory Settings panel, and not through chat prompts regardless of how they are worded.

The purpose of the Portfolio Admin Memory File is to give portfolio managers a private context layer for each company where they can accumulate internal GS knowledge, assessments, and strategic notes about that company without any risk of those insights being exposed to the company itself. This enables portfolio managers to have richer, more contextually informed AI conversations about a company without being constrained by what is appropriate for the founder to see.

The Portfolio Admin Memory File is populated exclusively from portfolio manager chat sessions. When a portfolio manager is chatting about a specific company, content that the AI extracts from that conversation as meaningful and worth remembering is routed to that company's Portfolio Admin Memory File, not the Company Memory File. The same end-of-session extraction logic and quality threshold applies - only genuinely useful, company-relevant learnings are saved, not full transcripts or transactional exchanges. Documents uploaded by portfolio managers in the context of a specific company are also RAG-indexed and summarized into the Portfolio Admin Memory File.

The AI model draws on both Layer 1a and Layer 1b when generating responses for portfolio managers - synthesizing context from both files invisibly. However the system must be constrained at the architecture level so that it never surfaces Layer 1b content to company-side users, even if a company user constructs a carefully worded prompt attempting to extract it. The existence of the Portfolio Admin Memory File must never be confirmed or revealed to company-side users through any system response.

Acceptance Criteria

Initialization
    A Portfolio Admin Memory File (Layer 1b) store is automatically created for each company upon first initialization of the AI chatbot for that company.
    The Layer 1b file is entirely separate from the Layer 1a file at the data layer - they are never merged, combined, or co-mingled.
    The Layer 1b file is company-scoped and portfolio-agnostic. A single Layer 1b file exists per company, regardless of how many portfolios that company belongs to or how many Portfolio Portal users have access to it. All Portfolio Portal users with access to a given company share the same Layer 1b file for that company — contributions from any authorized user's chat sessions are written to the same file, and all authorized users query from the same file when the AI generates responses.

Population from Portfolio Manager Chat Sessions
    Content extracted from portfolio manager chat sessions about a specific company is routed to that company's Layer 1b file, not Layer 1a.
    The learning trigger mirrors Layer 1a - end-of-session or a defined period of user inactivity.
    The same extraction quality rules apply: only meaningful, company-relevant learnings are saved. Full verbatim transcripts, generic questions, and transactional exchanges are excluded.
    Documents uploaded by portfolio managers in the context of a specific company are RAG-indexed and summarized into Layer 1b, not Layer 1a.

Context Querying for Portfolio Managers
    For portfolio manager users, the AI queries both Layer 1a and Layer 1b when generating responses about a specific company, synthesizing context from both files invisibly.
    The AI never surfaces Layer 1b content in any response to a company-side user

Security & Access Control
    Layer 1b content is never accessible to Company User or Company Admin roles through any mechanism - UI, chat response, or prompt.
    Prompt injection protections are implemented and enforced at the architecture level, preventing company-side users from extracting Layer 1b content regardless of how a chat prompt is worded.
    The existence of the Portfolio Admin Memory File must never be referenced or revealed to company-side users through any system response or UI element.
    No Layer 1b content from one company is accessible to any other company under any circumstances.
    No content from Layer 1b flows into Layer 2 (GS Knowledge Base) under any circumstances.
    Memory file entries are stored with metadata including source type (chat extraction, document summary) and timestamp.
    The architecture supports read-only access for Portfolio Manager and Admin roles only - UI implementation is covered in a separate story.

UX Design Considerations

    This is a backend and data architecture story — no user-facing UI is in scope.
