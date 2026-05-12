---
gid: 1213876002981172
name: Research AI Models for Chatbot Use
completed: true
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1213876002981172
---

# Research AI Models for Chatbot Use

Business Requirements

Evaluate and recommend the optimal LLM strategy for the LG AI Assistant MVP, aligned with the following business goals and scope:
    Conversational analytics over structured + unstructured company data
    Persistent memory per company
    Playbook ingestion
    Cost-efficient scaling
    Enterprise-grade security and data handling
    Transcript (Fireflies) ingestion (post MVP)

We are building an AI assistant that:
    Answers questions about company performance (forecasts, plans, benchmarks)
    Maintains per-company memory
    Ingests internal playbooks
    Ingests meeting transcripts to add to the company memory(post MVP)
    May require different model capabilities per task
The system may need to support a multi-model architecture IF DETERMINED, allowing:
    Swapping providers (e.g., OpenAI, Anthropic, open-source)
    Using different models for different workloads (cost vs quality tradeoffs)


Acceptance Criteria

1. Model Providers to Evaluate
At minimum include:
    OpenAI (GPT family)
    Anthropic (Claude family)
    Open-source models (e.g., LLaMA, Mistral, Mixtral, etc.)
Optional:
    Google Gemini
    Other emerging enterprise models
2. Evaluation Criteria
A. Capability Fit (MOST IMPORTANT)
Assess how well each model supports:
    Conversational Q&A over structured + unstructured data (RAG)
    Long-context reasoning (forecasts, transcripts, memory)
    Instruction following & consistency
    Tool use / function calling
    Summarization & insight generation
Note:
    Some models prioritize multimodal + product flexibility 
    Others emphasize reasoning depth + long context 
B. Cost & Performance
    Cost per token (input/output)
    Latency / response time
    Cost optimization strategies (model tiering)
    Feasibility of:
        Cheap models for preprocessing
        Premium models for final responses
C. Integration
    API quality and flexibility
    SDK/tooling ecosystem maturity
    Ease of:
        RAG implementation
        Memory systems
        Multi-model orchestration
D. Security & Compliance
Evaluate:
    Data privacy guarantees
    Data retention policies
    Risks of handling sensitive portfolio data
E. Reliability & Stability
    Model versioning / deprecations
    Uptime / SLA considerations
    Backward compatibility risks
F. Scalability & Architecture Fit
    Multi-model orchestration feasibility
    Routing strategies (task-based model selection)


Research Output - Written report including:

1. Pros & Cons by Model
For Each:
    Strengths aligned to LG use case
    Weaknesses / limitations
    Best-fit roles in system (e.g., reasoning vs summarization)
2. Recommended Architecture
Must include:
A. Single vs Multi-Model Recommendation
    Should we:
        Start single-model?
        Or design multi-model from day 1?
B. Proposed Model Roles (Example)
    "Heavy reasoning" model
    "Cheap processing" model
    "Memory summarization" model
3. Security & Risk Assessment
Identify:
    Data exposure risks
    Vendor dependency risks
    Model hallucination risks
    Cost overrun risks
4. Constraints & Dependencies
Examples:
    Infra requirements (for open-source hosting)
    Vendor contracts / pricing tiers
    Latency constraints
    Data pipeline readiness (RAG dependency)
5. Final Recommendation (Executive Summary)
Provide:
    Clear recommendation of:
        Model(s) to use for MVP
        Why (tied to business goals)
    Suggested evolution path (post-MVP)


Key Considerations

    Do NOT assume a single-model solution is sufficient
    Optimize for cost vs quality tradeoff
    Ensure future flexibility (avoid lock-in)
    Prioritize enterprise-safe architecture


Success Criteria

This research is successful if:
    The PO can confidently decide:
        Which model(s) to use for MVP
        Whether to adopt a multi-model architecture
    Engineering understands:
        Architecture implications
        Cost tradeoffs
        Security considerations

Lovable Prototype: (link omitted - see Asana)
(Top nav → Ask AI tab)
