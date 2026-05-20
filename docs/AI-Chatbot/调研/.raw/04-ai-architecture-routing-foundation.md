---
asana_gid: 1214057483533668
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533668
asana_section: LG Backlog  / Prioritized
asana_status: Product Review
asana_working_status: In Progress
asana_modified_at: 2026-05-11T15:04:38.559Z
lg_ticket: LG-1328
type: Technical Task
story_points: 13
t_shirt: L
priority: High
completed: False
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

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-05-05 · Karen Arnoldi**：请关注本 story 关于 LG 未来商业化的更新——从单租户到多租户架构所需的考虑。
- **2026-05-06 · Liang Chunru**：已在 story 中加入 Layer 1b 实现为 single shared store per company 的说明。
- **2026-05-06 · Karen Arnoldi**：抱歉我说得不够具体——我指的是 Layer 2 需要按 tenant 隔离。初期 LG 只有一个 tenant（Golden Section），未来商业化后多 tenant，每家 equity firm 拥有自己的 private Layer 2 知识库。
- **2026-05-07 · Liang Chunru**：完全理解。Karen 之前提到两个更新：Layer 2 按 tenant 隔离；Layer 1b 是公司级文件（admin portal 所有 accessible 用户共享）。我已更新相关 stories 覆盖 Layer 1b 细节。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 4. AI 架构与模型路由基础设施（AI Architecture & Model Routing Foundation，技术 Story）

- **Asana ID**: 1214057483533668
- **LG 编号**: LG-1328
- **状态**: Product Review（Working Status = In Progress，Story Points = 13，T-Shirt = L，Priority = High）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533668

### 业务需求

AI 聊天机器人必须构建在一个灵活的技术架构之上，该架构需明确支持双层知识模型（two-layer knowledge model）与双文件记忆架构（two-file memory architecture），允许在不同任务类型下使用不同的 AI 模型，支持服务商切换，并随着用量增长有效控制成本。这是一个基础性技术 story，没有直接面向用户的 UI，是所有其他 AI 聊天机器人 story 的前置条件。

架构必须将"各知识层之间的隔离"作为核心设计原则进行实现与强制：

- **Layer 1a（Company Memory File，公司记忆文件）**：每个公司私有，对公司侧用户（company-side users）和 portfolio managers 均可见
- **Layer 1b（Portfolio Admin Memory File，组合管理员记忆文件）**：同样按公司私有，但仅对 portfolio managers 及以上角色可见；必须在架构层面强制对公司侧用户完全不可访问
- **Layer 2（Knowledge Base，知识库）**：包含组织的 playbooks 和最佳实践框架，对该组织内的所有用户可访问。任何层的内容都不会流入另一层；Layer 1b 的任何内容都不会通过任何机制呈现给公司侧用户。MVP 阶段，Layer 2 即为 GS playbooks。

在为公司侧用户生成响应时，AI 仅查询 Layer 1a 与 Layer 2。在为 portfolio manager 用户生成响应时，AI 查询 Layer 1a、Layer 1b 与 Layer 2，无感地综合所有可用层的上下文。路由逻辑必须在查询时正确识别用户角色，以确定该次响应可用的层。

Layer 2 的一项关键架构要求是：必须从一开始就设计为 tenant-scoped resource（按租户隔离的资源），而非单一全局共享存储。MVP 阶段，Looking Glass 作为单租户运行，GS 是唯一组织，因此 Layer 2 解析为单一的 GS 知识库。但当 LG 商业化、对外销售给各 equity firm（股权投资公司）时，每家公司将需要其完全独立的知识库，与所有其他租户隔离。某家公司的专有 playbooks 和方法论在任何情况下都不得被其他租户访问或可见。架构必须支持该 per-tenant 隔离模型，且引入多租户时不需要进行重大重构。因此，Layer 2 应从第一天起就实现为 tenant-scoped 存储 —— 当前解析至 GS 租户的知识库，但结构上要保证：基于已认证用户所属的组织，路由层可在不同租户的知识库之间无缝切换。

不存在租户之间共享或继承知识库的产品功能规划。GS 知识库仅是 GS 租户的资源，并不是面向所有未来租户的默认基础层。路由层在解析 Layer 2 查询时绝不能跨越租户边界。

值得为架构感知预留的一种潜在未来例外是：一个跨投资组合的、剥离了识别信息的匿名化共享市场情报层（shared anonymized cross-portfolio market intelligence layer），未来可能作为可选的 opt-in（用户主动选择启用）资源跨租户提供。这一点明确属于 MVP 之后的范畴，当前不应实现，但架构不应使其后续无法添加。

所有 MVP 数据源必须明确覆盖：

- 财务问答与基准对比的真实数据来源是 normalization table（标准化表）
- Company Settings 中的公司档案元数据提供结构化上下文
- Layer 1a 与 Layer 1b 各自实现为独立的 per-company 存储
- Layer 2 知识库实现为 tenant-scoped 存储

MVP 阶段不引入除上述以外的任何外部数据源。

对于上传文档，架构必须根据上传用户的角色，将处理后的内容正确路由到对应的 Memory File：公司侧上传 → Layer 1a；portfolio manager 上传 → Layer 1b。会话结束时（end-of-session）的提取管线同样需根据用户角色将提取的学习内容路由到正确的层；在 portfolio manager 同时讨论多家公司的会话场景下，必须正确将各公司的学习内容路由到对应公司的 Layer 1b 文件。

基于已完成的研究任务，推荐的模型路由方案为：以 OpenRouter 作为路由层，采用多智能体架构（multi-agent architecture），按任务类型自动分配 agent。用户对模型选择无任何可见性或控制权。轻量模型处理预处理与简单检索；更强能力的模型则保留用于复杂推理与综合任务。

### 验收标准

#### 双层记忆架构（Two-Layer Memory Architecture）

- Layer 1a（Company Memory File）和 Layer 1b（Portfolio Admin Memory File）实现为每家公司各自独立的存储
- Layer 1a 可由公司侧用户和 portfolio admin 用户（pgm 即 Portfolio Group Manager 与 pm 即 Portfolio Manager）针对各自所属公司进行查询
- Layer 1b 仅可由 Portfolio Admin 角色查询 —— 在任何情况下均不可由 Company User 或 Company Admin 角色查询
- AI 模型在架构层面被约束，无论 chat prompt 如何措辞，都不得将 Layer 1b 内容呈现给公司侧用户
- 任何层的内容在任何情况下都不得流入另一层
- Layer 1b 实现为每家公司单一共享存储。所有有权访问该公司的 Portfolio Manager 与 Admin 用户读写同一份 Layer 1b 文件。Layer 1b 内部不做按用户或按 portfolio 的分区 —— 该存储仅按公司隔离。架构必须支持来自多个授权用户对同一公司 Layer 1b 文件的并发写入，且不出现数据丢失或冲突

#### 基于角色的层级路由（Role-Based Layer Routing）

- 在查询时，系统识别已登录用户的角色，并据此确定该次响应可用的层：公司侧用户仅可访问 Layer 1a 与 Layer 2；portfolio 用户可访问 Layer 1a、Layer 1b 与 Layer 2
- 文档上传根据上传用户的角色路由到正确的层：公司侧上传 → Layer 1a；portfolio 上传 → Layer 1b
- 会话结束时的提取管线根据会话用户的角色将学习内容正确路由到对应层
- 对于 portfolio 用户讨论多家公司的会话，提取管线正确识别所讨论的每家公司，并将学习内容路由到对应公司的 Layer 1b 文件

#### Layer 2 —— 按租户隔离的知识库架构（Tenant-Scoped Knowledge Base Architecture）

- Layer 2 实现为 tenant-scoped 存储 —— 系统基于已认证用户所属的组织（tenant）来解析待查询的正确知识库，而非硬编码的全局引用
- MVP 阶段，由于只有一个租户，故解析至唯一的 GS 租户知识库。实现结构必须保证：在引入多租户时，可按组织替换为不同租户的知识库，而无需对路由层进行重构
- 架构中的任何位置都不得引入"存在单一全局 Layer 2 知识库"的硬编码假设
- 路由层在解析 Layer 2 查询时绝不跨越租户边界 —— 一个租户组织中的用户在任何情况下都不能查询或访问另一个租户的知识库
- 架构层面不支持跨租户的知识库共享或继承 —— 每个租户的知识库均完全隔离。GS 知识库仅是 GS 租户的资源

#### 所有 MVP 数据源（All MVP Data Sources）

MVP 数据源包含以下内容：

- normalization table（标准化表，含 actuals、committed forecast、system-generated forecast、benchmarks）
- 来自 Company Settings 的公司档案元数据
- Layer 1a Memory File（按公司隔离的存储）
- Layer 1b Memory File（按公司隔离的存储，仅 portfolio admin 可访问）
- Layer 2 Knowledge Base(按租户隔离的存储)

#### 模型路由（Model Routing）

- 集成 OpenRouter（或研究产出推荐的模型路由层）作为 AI 模型路由层
- 实现 multi-agent 架构，按任务类型分配 agent
- 落实成本优化 —— 轻量模型处理预处理与简单检索；更强能力的模型保留用于复杂推理

#### 安全（Security）

- 在架构层面对所有用户角色实施并强制执行 prompt injection（提示词注入）防护
- 传递给 AI 模型服务商的敏感公司数据按研究任务中的安全要求处理 —— 模型服务商不得以超出回复所需的方式记录或保留任何敏感数据
- Skills 功能明确不在 MVP 范围内 —— 当前阶段架构无需为之做适配，但应在 MVP 之后进行考量
- 除上述列举之外的外部数据源不在 MVP 范围内

### UX 设计要点

- 这是一个后端与基础设施 story —— 不需要直接面向用户的 UI

### 依赖与备注

- 本 story 是所有其他 AI 聊天机器人 story 的前置条件
- 推荐方案：OpenRouter + multi-agent architecture（基于已完成的研究任务结论）
- 跨租户匿名化市场情报层为 post-MVP 的潜在演进方向，当前不构建，但架构不得阻断
- Skills 功能为 post-MVP，本阶段不予适配

---

