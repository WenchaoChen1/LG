---
gid: 1214057483533668
name: AI Architecture & Model Routing Foundation (Technical Story)
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533668
---

# AI Architecture & Model Routing Foundation (Technical Story)

Business Requirements

The AI chatbot must be built on a flexible technical architecture that explicitly supports the two-layer knowledge model and the two-file memory architecture, allows different AI models to be used for different types of tasks, enables provider swapping, and manages costs effectively as usage scales. This is a foundational technical story with no direct user-facing UI and is a prerequisite for all other AI chatbot stories.

The architecture must implement and enforce the separation between all knowledge layers as a core design principle.
    Layer 1a, the Company Memory File: is private per company and visible to both company-side users and portfolio managers.
    Layer 1b, the Portfolio Admin Memory File: is also private per company but visible only to portfolio managers and above; it must be enforced as completely inaccessible to company-side users at the architecture level.
    Layer 2, the Knowledge Base: contains the organization's playbooks and best practice frameworks and is accessible to all users within that organization. No content from any layer flows into another layer, and no content from Layer 1b is ever surfaced to company-side users through any mechanism. For MVP this is GS playbooks

When generating responses for company-side users, the AI queries only Layer 1a and Layer 2. When generating responses for portfolio manager users, the AI queries Layer 1a, Layer 1b, and Layer 2, synthesizing context from all applicable layers invisibly. The routing logic must correctly identify the user's role at query time to determine which layers are available for that response.

A critical architectural requirement for Layer 2 is that it must be designed as a tenant-scoped resource from the outset, not a single global shared store. For MVP, Looking Glass operates as a single tenant with GS as the only organization, so Layer 2 resolves to a single GS knowledge base. However, when LG is commercialized and sold to external equity firms, each firm will require its own completely independent knowledge base, isolated from all other tenants. A firm's proprietary playbooks and methodologies must never be accessible to or visible by any other tenant under any circumstances. The architecture must support this per-tenant isolation model without requiring significant rearchitecting when multi-tenancy is introduced. Layer 2 should therefore be implemented as a tenant-scoped store from day one, currently resolving to the GS tenant's knowledge base, but structured so that a different tenant's knowledge base can be substituted cleanly by the routing layer based on the authenticated user's organization.

There is no planned product feature where tenants share or inherit knowledge bases from other tenants. The GS knowledge base is a GS-tenant resource only, it is not a default base layer available to all future tenants. The routing layer must never cross tenant boundaries when resolving a Layer 2 query.

There is one potential future exception worth noting for architectural awareness: a shared anonymized cross-portfolio market intelligence layer, stripped of identifying information, may eventually be offered as an optional opt-in resource across tenants. This is firmly post-MVP and should not be built now, but the architecture should not make it impossible to add later.

All MVP data sources must be covered clearly. For financial Q&A and benchmarking, the agreed source of truth is the normalization table. Company profile metadata from Company Settings provides structured context. Layer 1a and Layer 1b are each implemented as separate per-company stores. The Layer 2 Knowledge Base is implemented as a tenant-scoped store. No other external data sources are in scope for MVP.

For uploaded documents, the architecture must correctly route processed content to the appropriate memory file based on the role of the uploading user - company-side uploads go to Layer 1a; portfolio manager uploads go to Layer 1b. The end-of-session extraction pipeline must similarly route extracted learnings to the correct layer based on user role and correctly handle sessions where a portfolio manager discusses multiple companies, routing learnings to the appropriate company's Layer 1b file.

Based on the completed research task, the recommended model routing approach is OpenRouter as the routing layer with a multi-agent architecture where agents are assigned automatically based on task type. Users have no visibility into or control over model selection. Lighter models handle preprocessing and simple retrieval; more capable models are reserved for complex reasoning and synthesis.

Acceptance Criteria

Two-Layer Memory Architecture
    Layer 1a (Company Memory File) and Layer 1b (Portfolio Admin Memory File) are implemented as separate stores per company.
    Layer 1a is queryable by both company-side users and portfolio admin users (pgm and pm) for their respective companies.
    Layer 1b is queryable only by Portfolio Admin roles — it is never queryable by Company User or Company Admin roles under any circumstances.
    The AI model is constrained at the architecture level to prevent surfacing Layer 1b content to company-side users regardless of how a chat prompt is worded.
    No content from any layer flows into another layer under any circumstances.
    Layer 1b is implemented as a single shared store per company. All Portfolio Manager and Admin users with access to a given company read from and write to the same Layer 1b file for that company. There is no per-user or per-portfolio partitioning within Layer 1b — the store is company-scoped only. The architecture must support concurrent writes from multiple authorized users to the same company's Layer 1b file without data loss or conflict.

Role-Based Layer Routing
    At query time, the system identifies the role of the logged-in user and determines which layers are available for that response: company-side users access Layer 1a and Layer 2 only; portfolio users access Layer 1a, Layer 1b, and Layer 2.
    Document uploads are routed to the correct layer based on the uploading user's role: company-side uploads to Layer 1a, portfolio uploads to Layer 1b.
    End-of-session extraction correctly routes learnings to the appropriate layer based on the session user's role.
    For portfolio user sessions discussing multiple companies, the extraction pipeline correctly identifies each company discussed and routes learnings to the appropriate company's Layer 1b file.

Layer 2 — Tenant-Scoped Knowledge Base Architecture
    Layer 2 is implemented as a tenant-scoped store - the system resolves the correct knowledge base to query based on the authenticated user's organization (tenant), not a hard-coded global reference.
    For MVP, this resolves to the single GS tenant's knowledge base since there is only one tenant. The implementation must be structured so that a different tenant's knowledge base can be substituted per organization when multi-tenancy is introduced without rearchitecting the routing layer.
    No hard-coded assumptions about a single global Layer 2 knowledge base are introduced anywhere in the architecture.
    The routing layer never crosses tenant boundaries when resolving a Layer 2 query - a user from one tenant organization can never query or access another tenant's knowledge base under any circumstances.
    There is no architecture support for cross-tenant knowledge base sharing or inheritance - each tenant's knowledge base is fully isolated. The GS knowledge base is a GS-tenant resource only.

All MVP Data Sources
    The following are MVP data sources: the normalization table (actuals, committed forecast, system-generated forecast, benchmarks), company profile metadata from Company Settings, Layer 1a memory file (per-company store), Layer 1b memory file (per-company store, portfolio admin access only), and Layer 2 Knowledge Base (tenant-scoped store).

Model Routing
    OpenRouter (or the model routing layer recommended by the research output) is integrated as the AI model routing layer.
    A multi-agent architecture is implemented with agents assigned per task type.
    Cost optimization is implemented - lighter models handle preprocessing and simple retrieval; more capable models are reserved for complex reasoning.

Security
    Prompt injection protections are implemented and enforced at the architecture level across all user roles.
    Sensitive company data passed to AI model providers is handled per the security requirements in the research task - no sensitive data is logged or retained by the model provider beyond what is required for the response.
    Skills functionality is explicitly out of scope for MVP - the architecture does not need to account for it at this stage but should consider it post-MVP.
    No external data sources beyond those listed above are in scope for MVP.

UX Design Considerations

    This is a backend and infrastructure story - no direct user-facing UI is required.
