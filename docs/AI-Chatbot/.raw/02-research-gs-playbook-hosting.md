---
gid: 1214147930023558
name: Research - GS Playbook Hosting Strategy - External (GEO) vs. Internal LG Management
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023558
---

# Research: GS Playbook Hosting Strategy - External (GEO) vs. Internal LG Management

Business Requirements

Golden Section's playbooks are a core component of the AI chatbot's Layer 2 knowledge base. Before the team can finalize how playbooks are ingested and managed within Looking Glass, a foundational hosting decision must be made: should the playbooks remain hosted on Golden Section's publicly accessible external website, or should they be copied into Looking Glass and managed entirely internally?  For reference the external website is: https://www.goldensection.com/vertical-saas-playbooks

This decision is not purely a technical one, but has a potential marketing and visibility dimension tied to the Generative Engine Optimization (GEO) concept. GEO is the emerging practice of optimizing content so that it surfaces as a trusted, authoritative reference when users interact with AI models like Claude or ChatGPT, ie the AI equivalent of traditional Search Engine Optimization (SEO). Dougal has raised the possibility that if GS playbooks are hosted on a publicly accessible website and the Looking Glass AI chatbot accesses that site to answer user questions, the resulting activity might contribute to GEO visibility, meaning GS playbook content could begin appearing as a recommended reference in AI conversations that have nothing to do with Looking Glass at all, organically expanding GS's reach.

If this GEO benefit is real and meaningful, the preferred approach would be to keep the playbooks on the external public GS site and maintain only a markdown changelog file inside Looking Glass that captures updates, additions, and changes made over time. The AI chatbot would reference both the external site and the internal markdown file when answering questions, with the external site serving as the main source and the internal file capturing the proprietary evolving knowledge layer. This approach avoids duplicating or managing the full playbook content inside LG while still giving the chatbot access to the latest version.

If the GEO benefit is not real or is negligible, the simpler and more controllable approach is to copy all playbook content into Looking Glass as a single managed markdown file (or structured equivalent) and handle everything internally. The external site would no longer be the source of playbook truth for the chatbot - LG would be.

The research team should evaluate both the technical feasibility of each approach and the GEO question directly, so that a clear, informed recommendation can be made to Dougal before development of the playbook ingestion story of the AI chatbot epic begins

Acceptance Criteria

GEO Research
    The team researches and documents a clear answer to the following question: does a language model like Claude or ChatGPT accessing a publicly hosted website as part of answering user questions contribute in any meaningful way to that site's GEO visibility, i.e., does it make that site more likely to appear as a reference in other AI conversations disconnected from Looking Glass?
    The research includes any currently known best practices or mechanisms for achieving GEO visibility and whether hosting location (public URL vs. internal file) is a relevant factor.
    A clear recommendation is provided: does hosting playbooks externally on the GS public site provide a GEO advantage worth preserving, or is it not a meaningful factor?
Option A — External Hosting with Internal Markdown Changelog (if GEO benefit is confirmed)
    The team evaluates the technical feasibility of the chatbot referencing both an external public URL (the GS playbooks site) and an internal markdown changelog file simultaneously
    The team identifies any limitations, risks, or complications with this approach, including latency from external URL fetching, dependency on external site availability, version control challenges, and complexity of merging external and internal content.
    The team provides an effort estimate for implementing this dual-source approach
Option B — Internal Management Only (if GEO benefit is not confirmed or is negligible)
    The team evaluates the effort required to copy all existing GS playbook content from the external site into a single managed internal file or structured format within Looking Glass.
    The team identifies the preferred internal format (e.g., single markdown file, structured document store, wiki-style CMS).
    The team provides an effort estimate for this approach.
Final Recommendation
    The research output includes a clear recommendation of Option A or Option B with supporting rationale covering: GEO impact assessment, technical complexity, maintenance overhead over time, and alignment with the AI chatbot architecture.
    The recommendation should also address how playbook updates and admin editing would work under the recommended approach, as this feeds into the broader playbook management feature planned for the AI chatbot epic. NOTE:  For MVP, only admin editing is in scope. POST MVP scope includes the notion of AI making playbook updates (with Admin's ability to review and delete if desired)
    Dougal can use this recommendation to make a final decision and the product team can proceed with the definition of the playbook ingestion story of the AI chatbot epic
