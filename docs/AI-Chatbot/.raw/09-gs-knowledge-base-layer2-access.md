---
gid: 1214081544026467
name: AI Chatbot - GS Knowledge Base Access for All Users (Layer 2)
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026467
---

# AI Chatbot - GS Knowledge Base Access for All Users (Layer 2)

Business Requirements

With the Knowledge Base ingested and indexed, this story integrates the Layer 2 knowledge source into the chatbot experience for all user roles, both company-side users (Company User and Company Admin) and Portfolio Manager and Portfolio Group Manager users. It enables any user to ask questions that draw on the organization's playbooks and best practice frameworks and receive contextually relevant guidance in a natural, conversational way.

For MVP, Looking Glass operates as a single-tenant system with Golden Section as the only organization. The Layer 2 knowledge base for MVP consists of GS's playbooks and best practice frameworks, hosted internally as a managed markdown file. Layer 2 functions as a shared resource whose content is the same for all users across all companies on the platform. However, this story must be built with the future multi-tenant commercialization of Looking Glass explicitly in mind. When LG is sold to external equity firms, each firm (tenant) will require its own independent knowledge base, completely isolated from other tenants. A firm's knowledge base will contain that firm's own proprietary playbooks, methodologies, and best practices. It will not be shared with or accessible to any other tenant. The GS knowledge base will not be a permanent global layer available to all tenants, each firm stands on its own knowledge base. There is no planned product feature where tenants automatically inherit or access GS's playbooks. For the first few early commercial partners, GS may share their playbooks informally as an operational workaround to help those firms get started, but this is not a feature to build into the system.

There is one potential future exception worth noting for architectural awareness: a shared anonymized cross-portfolio market intelligence layer, built from Fireflies conversation data stripped of identifying information, may eventually be offered as an optional opt-in resource across tenants. This is firmly post-MVP and should not be built now, but the architecture should not make it impossible to add later.

The practical implication for this story is that the integration and chatbot access layer for Layer 2 must be built to be tenant-scoped, meaning the system queries the knowledge base associated with the current user's organization, not a single hard-coded global knowledge base. For MVP this resolves to the single GS knowledge base since there is only one tenant. But the implementation should treat Layer 2 as a tenant-scoped resource from the start so that when multi-tenancy is introduced, each firm's knowledge base can be substituted without rearchitecting the chatbot access layer.

Acceptance Criteria

Chatbot Query Integration
    The chatbot can retrieve and synthesize relevant content from the Layer 2 knowledge base in response to user questions about strategy, best practices, and organizational guidance, available to all user roles.
    Layer 2 store is a queryable source for both the company-side and portfolio manager chatbot interfaces.
    Responses that draw on Layer 2 content include a subtle attribution (e.g., "Based on GS best practices") so users understand where the guidance comes from.
    The chatbot does not return raw playbook document text verbatim - responses are always synthesized into natural conversational language.
    Layer 2 content is entirely separate from any company's Layer 1 memory file - no content flows between layers in either direction.
    Access to Layer 2 is available to all user roles: Company User, Company Admin, Portfolio Manager, Portfolio Group Manager, and Admin.

Tenant-Scoped Architecture
    The Layer 2 is scoped to the knowledge base associated with the current user's organization (tenant) - the system does not query a single hard-coded global knowledge base.
    For MVP, this resolves to the single GS knowledge base since there is only one tenant. The implementation must be structured so that a different organization's knowledge base can be substituted per tenant when multi-tenancy is introduced without requiring rearchitecting of the chatbot access layer.
    No hard-coded assumptions about a single global knowledge base should be introduced that would prevent per-tenant knowledge base isolation in the future.
    The architecture explicitly does not include any feature for tenants to automatically inherit or access the GS knowledge base, the GS knowledge base is a GS-tenant resource only.

UX Design Considerations

    The knowledge base should feel like a knowledgeable advisor the user can tap into, not a search tool or document library. Prompt framing like "What would GS recommend for..." is more inviting than "Search GS playbooks for..."
    The knowledge base is clearly surfaced in both the company-side and portfolio manager chat interfaces, at minimum through a suggested prompt card on each welcome screen signaling that organizational guidance is available (e.g., "What does GS recommend for companies at my stage?").
    The suggested prompt wording is tailored per audience - founder-facing prompts frame the knowledge base as strategic guidance for their company; portfolio manager prompts frame it as portfolio management best practices.
    Layer 2 content is strictly read-only through the chatbot interface - no user can modify, add to, or remove knowledge base content through chat.
    Attribution (e.g., "Based on GS best practices") should be subtle - a small label or italicized note at the end of a response rather than a prominent disclaimer that interrupts the conversational flow.
    The entire Layer 2 concept is invisible to users - they simply experience the chatbot giving them relevant, informed organizational guidance when they ask for it.
    In a future multi-tenant context, the attribution label should dynamically reference the firm's own identity rather than "GS" — e.g., "Based on [Firm Name] best practices." The attribution language should be designed to be configurable per tenant rather than hard-coded as "GS."
