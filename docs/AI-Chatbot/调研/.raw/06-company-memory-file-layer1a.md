---
gid: 1214057483533664
name: Company Memory File - Layer 1a Backend (Company User Context)
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533664
---

# Company Memory File - Layer 1a Backend (Company User Context)

Business Requirements

The AI chatbot requires a persistent, private memory file for each company that captures context appropriate for company-side users to see and benefit from. This is the first of two distinct backend memory file stories - Layer 1a covers the Company Memory File, which stores company-specific context that is visible to both Company Admin users and portfolio managers. Layer 1b covers the Portfolio Admin Memory File, which stores internal GS context visible only to portfolio managers.

The Company Memory File is strictly private to each individual company - it is never shared across companies and no content from it ever flows into the shared GS Knowledge Base (Layer 2). Its purpose is to give the chatbot a continuously growing, company-specific intelligence layer that makes every response more accurate and relevant over time for both company-side users and portfolio managers interacting with that company.

The Company Memory File is populated from three sources:
    1. The first is the company's existing metadata in Looking Glass. Company Settings data including company name, description, company type, industry(populated in description), stage, and any other structured profile fields. This gives the chatbot a meaningful baseline understanding of the company from the very first conversation.
    2. The second source is company-side chat conversations. At the end of each conversation session (triggered by session end or a defined period of user inactivity), the system runs an AI-driven post-conversation extraction pass that identifies and saves only information that is meaningfully worth remembering. This includes:
        - Facts the user stated about their company not already in LG
        - Corrections or clarifications to existing LG data
        - Strategic context that would improve future response relevance.
        - Full verbatim transcripts are not stored - those are handled separately by the chat history feature. Generic questions, transactional exchanges, and information already accurately captured in LG data are explicitly excluded.
    3. The third source is documents uploaded by company-side users within the chat. When a document is uploaded, two parallel processes occur: the document is RAG-indexed for dynamic retrieval in current and future sessions, and the system auto-generates a high-level summary of key company-relevant learnings saved as a memory entry. Both the RAG index and the summary are strictly scoped to this company's Layer 1a file and do not flow into Layer 1b or Layer 2.

Acceptance Criteria

Initialization
    A Company Memory File (Layer 1a) store is automatically created for each company (perhaps at the first use of the chatbot?)
    The memory file is automatically initialized with all available Company Settings metadata: company name, description, company type, industry, stage, and any other structured profile fields present in LG.
    When any Company Settings field is updated by a user, the corresponding memory file entry is updated automatically.
    NOTE: When the consultative onboarding epic is introduced the Company Memory File will need to be initialized during that workflow

Chat Conversation Learning
    The learning trigger is end-of-session or a defined period of user inactivity (TBD)
    At session end, the system runs an AI-driven extraction pass saving only meaningful, company-relevant information from the conversation.
    Qualifying content: facts the user stated about their company not already in LG, corrections or clarifications to existing LG data, and strategic context that would improve future response relevance.
    Excluded content: full verbatim chat transcripts, generic informational questions, transactional exchanges, and information already accurately captured in the company's existing LG data.
    Full chat transcripts are not stored in the memory file - they are handled separately by the chat history feature.

Document Upload Learning
    When a company-side user uploads a document in chat, two parallel processes are triggered: (1) the document is RAG-indexed for dynamic retrieval in current and future sessions, and (2) the system auto-generates a high-level summary of key company-relevant learnings saved as a Layer 1a memory entry.
    Both the RAG index and the memory summary are strictly scoped to this company's Layer 1a file - they do not flow into the Portfolio Admin Memory File (Layer 1b) or the GS Knowledge Base (Layer 2).
    Document Uploads are covered in story 1214057483533666

Data Isolation & Access Control
    No Company Memory File content from one company is accessible to any other company under any circumstances.
    No content from the Company Memory File flows into Layer 2 (GS Knowledge Base) under any circumstances.
    Memory file entries are stored with metadata including source type (company profile, chat extraction, document summary) and timestamp.
    The architecture supports read-only access for Company Admin users (their own company only) and read-only access for Portfolio Managers (all companies within their access scope) - UI implementation is covered in separate stories.

UX Design Considerations

    This is a backend and data architecture story - there is no user-facing UI in scope here.
