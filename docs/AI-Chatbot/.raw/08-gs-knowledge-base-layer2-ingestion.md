---
gid: 1214057483533665
name: GS Knowledge Base - Layer 2 Ingestion & Management
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533665
---

# GS Knowledge Base - Layer 2 Ingestion & Management

Business Requirements

The AI chatbot's two-layer knowledge architecture depends on the existence of a populated, queryable Golden Section Knowledge Base as its Layer 2 shared resource. Unlike the company-specific memory file (Layer 1), which is built automatically from user activity, Layer 2 must be explicitly populated by Golden Section internally. For MVP, this layer consists of Golden Section's existing playbooks and best practice frameworks - the full body of GS operational and strategic knowledge that has been developed over time.

A research task was completed to determine whether hosting the GS playbooks on a publicly accessible external website would provide Generative Engine Optimization (GEO) visibility benefits, specifically, whether the AI chatbot accessing an external site to answer user questions would increase that site's authority or visibility in other AI model conversations. The research confirmed that there is no GEO benefit to external hosting. AI models do not learn from or increase the authority of a site simply by receiving content during a session. As a result, the decision has been made to proceed with Option B: copy all existing GS playbook content from the external site into a single managed internal markdown file within Looking Glass. This is the source for the GS Knowledge Base going forward.

This story covers the technical work required to ingest that markdown file and any supporting documents into a format that the AI chatbot can query as well as the internal-facing tooling needed for authorized GS users (Super Admins and PGMs) to manage and update that content over time. The result is a living, searchable knowledge layer that all chatbot users, both company-side and portfolio managers, can draw on for strategic guidance, without ever seeing the raw documents themselves or knowing the specifics of how the knowledge base is structured.

The GS Knowledge Base is completely separate from any individual company's Layer 1 memory file. It is a global shared resource for the current single-tenant implementation, meaning its contents are the same for all users across all companies on the platform. It does not contain any company-specific data, financial information, or identifying details about any portfolio company or founder. Its sole purpose is to make GS's collective operational and strategic knowledge accessible through the chatbot in a natural, conversational way.

For MVP, the scope is limited to ingestion and querying of the existing playbook content. The process of the LLM automatically detecting knowledge base updates from portfolio management conversations is explicitly post-MVP. For now, an authorized user must manually upload or update content in the knowledge base when changes are needed. The authorized role for editing the knowledge base is Portfolio Group Manager and above - lower roles do not have access to modify playbook content.

Important architectural note for the dev team: In the future, when Looking Glass is commercialized and sold to external equity firms, each firm (tenant) will require its own independent knowledge base - completely isolated from other tenants' knowledge bases. The current single shared GS Knowledge Base is appropriate for the MVP single-tenant implementation, but the architecture should be designed with per-tenant knowledge base isolation in mind so that multi-tenancy can be supported without significant rearchitecting. Do not build Layer 2 in a way that assumes a single global knowledge base will always be the only structure.

For reference the external website is: https://www.goldensection.com/vertical-saas-playbooks

Acceptance Criteria

Content Ingestion
    All existing GS playbook content is copied from the external GS website into a single managed internal markdown file as the source for Layer 2.
    A backend ingestion pipeline is implemented that accepts playbook documents in common formats (PDF, Word .docx, and markdown .md at minimum) and processes them into a queryable store for retrieval.
    All ingested content is stored and indexed as part of the shared GS Knowledge Base (Layer 2), accessible to all chatbot users regardless of company or role.
    The GS Knowledge Base is entirely separate from any company's Layer 1 memory file at the data and architecture level - there is no path by which Layer 2 content can become company-specific or vice versa.
    No company-identifying information, financial data, or founder-specific context is ever stored in Layer 2.
    An initial complete set of GS playbook content is ingested and validated as part of acceptance testing

Content Management
    An internal admin interface or process is provided for authorized users to upload new content, update the markdown file, or remove documents from the knowledge base.
    Access to upload, edit, or remove knowledge base content is restricted to Portfolio Group Manager role and above. Lower roles cannot modify the knowledge base.
    When content is uploaded or updated, the knowledge base is automatically re-indexed so that new or changed content is immediately available for queries.
    When content is removed from the knowledge base, it is no longer retrievable in chatbot responses.
    A simple status indicator is available in the admin interface showing when the knowledge base was last updated and how many documents are currently indexed.

Chatbot Query Behavior
    The chatbot can accurately retrieve and reference relevant sections of ingested playbook content in response to user questions about strategy, best practices, or GS guidance.
    Responses drawing on Layer 2 content do not expose raw document text verbatim - the AI synthesizes and summarizes the relevant guidance in conversational language.

Future Multi-Tenancy Compatibility
    The Layer 2 architecture is designed to support per-tenant knowledge base isolation in the future, allowing each external equity firm to have their own independent knowledge base when multi-tenancy is implemented.

UX Design Considerations

    Company users and portfolio managers have no direct visibility into the knowledge base documents themselves - they interact with the knowledge base only through the chatbot's natural language responses. There is no "browse playbooks" UI for MVP.
    The internal admin interface for uploading and managing playbook content does not need to be consumer-grade for MVP - it should be functional and reliable. A simple interface with document listing, status indicators, upload capability, and delete functionality is sufficient.
    For the chatbot-facing side, when a response draws heavily on GS playbook content a subtle attribution such as "Based on GS best practices" is appropriate so users understand the source of the guidance, without exposing the specific document name or contents.
    The markdown file format is preferred as the primary content management format because it is human-readable, lightweight, easy for both humans and the AI to process, and straightforward to version and update over time.

Additional Acceptance Criteria (RAG specifics)

    A backend ingestion pipeline is implemented that accepts playbook documents in common formats (PDF, Word .docx, and markdown .md at minimum) and processes them into a queryable vector store for RAG retrieval.
    The knowledge base ingestion pipeline is compatible with the RAG architecture established in the AI Architecture & Model Routing Foundation story.
    An initial set of existing GS playbooks is ingested and validated as part of the acceptance testing for this story — the knowledge base must not be empty at launch.
