---
asana_gid: 1214081544026467
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026467
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:20:37.752Z
lg_ticket: LG-1338
type: 
story_points: 
t_shirt: L
priority: 
completed: False
---

# AI Chatbot - GS Knowledge Base Access for All Users (Layer 2)

Business Requirements

With the Knowledge Base ingested and indexed in story https://app.asana.com/1/1170332106480422/task/1214057483533665, this story integrates the Layer 2 knowledge source into the chatbot experience for all user roles, both company-side users (Company User and Company Admin) and Portfolio Manager and Portfolio Group Manager users. It enables any user to ask questions that draw on the organization's playbooks and best practice frameworks and receive contextually relevant guidance in a natural, conversational way.
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
Mobile Responsiveness
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices


UX Design Considerations

    The knowledge base should feel like a knowledgeable advisor the user can tap into, not a search tool or document library. Prompt framing like "What would GS recommend for..." is more inviting than "Search GS playbooks for..."
    The knowledge base is clearly surfaced in both the company-side and portfolio manager chat interfaces, at minimum through a suggested prompt card on each welcome screen signaling that organizational guidance is available (e.g., "What does GS recommend for companies at my stage?").
    The suggested prompt wording is tailored per audience - founder-facing prompts frame the knowledge base as strategic guidance for their company; portfolio manager prompts frame it as portfolio management best practices.
    Layer 2 content can be viewed and managed by Portfolio Group Manager role and above. is strictly read-only through the chatbot interface - no user can modify, add to, or remove knowledge base content through chat.
    Attribution (e.g., "Based on GS best practices") should be subtle - a small label or italicized note at the end of a response rather than a prominent disclaimer that interrupts the conversational flow.
    The entire Layer 2 concept is invisible to users - they simply experience the chatbot giving them relevant, informed organizational guidance when they ask for it.
    In a future multi-tenant context, the attribution label should dynamically reference the firm's own identity rather than "GS" — e.g., "Based on [Firm Name] best practices." The attribution language should be designed to be configurable per tenant rather than hard-coded as "GS."
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

https://app.asana.com/app/asana/-/get_asset?asset_id=1214687052273911




https://app.asana.com/app/asana/-/get_asset?asset_id=1214687052273913

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

_本任务暂无业务相关评论（仅系统消息）。_

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 4. AI Chatbot - 所有用户的 GS Knowledge Base 访问（Layer 2）

- **Asana ID**: 1214081544026467
- **LG 编号**: LG-1338
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = L）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026467

### 业务需求

在 Knowledge Base 完成摄取与索引后，本需求负责将 Layer 2 知识源接入 chatbot 体验，覆盖所有用户角色 —— 公司侧用户（Company User 与 Company Admin）以及 Portfolio Manager 与 Portfolio Group Manager 用户。它使任何用户都可以提出基于组织 playbooks 与 best practice frameworks 的问题，并以自然、对话式的方式获得上下文相关的指引。

在 MVP 阶段，Looking Glass 作为单租户系统运行，唯一的组织即 Golden Section。MVP 中的 Layer 2 知识库由 GS 的 playbooks 与 best practice frameworks 构成，作为一份由内部管理的 markdown 文件托管。Layer 2 是一个共享资源，其内容对平台上所有公司的所有用户而言都相同。然而，本需求在实现时必须明确将 Looking Glass 未来的多租户商业化纳入考量。当 LG 销售给外部 equity firms 时，每家公司（每个 tenant）都将需要其专属、独立的知识库，与其他 tenants 完全隔离。某家 firm 的知识库将包含其自己的专有 playbooks、方法论与最佳实践，不与任何其他 tenant 共享或被其访问。GS 知识库不会成为对所有 tenants 可用的永久全局层 —— 每家 firm 都基于自身的知识库独立运作。**没有**任何已规划的产品功能会让 tenants 自动继承或访问 GS 的 playbooks。在最早的几家商业合作伙伴中，GS 可能会以非正式的运营 workaround 的方式与他们分享 playbooks 以协助起步，但这并不会作为一项产品功能内建到系统中。

需要从架构上预留一种未来可能的例外：一个跨 portfolio 的、剥离了识别信息的共享匿名化市场情报层（基于 Fireflies 对话数据构建），未来或许会作为可选 opt-in 资源在 tenants 之间提供。这一能力**坚定属于 post-MVP**，当前不应构建，但架构上不应使其在未来无法添加。

对本需求的实际影响是：Layer 2 的接入与 chatbot 访问层必须按 tenant-scoped 设计 —— 即系统应查询当前用户所属组织对应的知识库，而不是一个硬编码的全局知识库。在 MVP 阶段，由于只有一个 tenant，这会解析到单一的 GS 知识库；但实现上从一开始就应将 Layer 2 视为 tenant-scoped 资源，使得多租户引入后，每家 firm 的知识库都可以被替换进来，而无需对 chatbot 访问层做架构性重构。

### 验收标准

**Chatbot 查询接入（Chatbot Query Integration）**

- chatbot 能从 Layer 2 知识库检索并综合相关内容，用以回应用户关于战略、最佳实践与组织指引的问题，对所有用户角色可用。
- Layer 2 存储是一个可被查询的来源，公司侧 chatbot 界面与 Portfolio Manager chatbot 界面均可调用。
- 引用了 Layer 2 内容的回复包含一个不显眼的归属标识（例如 "Based on GS best practices"），让用户理解指引的来源。
- chatbot 不会逐字返回原始 playbook 文档的文本 —— 回复始终以自然对话式语言进行综合表达。
- Layer 2 内容与任何公司的 Layer 1 Memory File 完全隔离 —— 任一方向的内容都不会跨层流动。
- Layer 2 对所有用户角色开放：Company User、Company Admin、Portfolio Manager、Portfolio Group Manager 与 Admin。

**Tenant-Scoped 架构（Tenant-Scoped Architecture）**

- Layer 2 范围限定为当前用户所属组织（tenant）对应的知识库 —— 系统不查询单一的硬编码全局知识库。
- 在 MVP 阶段，由于只有一个 tenant，这会解析到单一的 GS 知识库。实现必须采取这样的结构：当多租户引入时，可按 tenant 替换为不同组织的知识库，而无需对 chatbot 访问层进行架构性重构。
- 不引入任何会阻碍未来 per-tenant 知识库隔离的、关于"单一全局知识库"的硬编码假设。
- 架构明确**不**包含任何让 tenants 自动继承或访问 GS 知识库的特性，GS 知识库仅作为 GS 自身 tenant 的资源。

### UX 设计要点

- 知识库的体感应像一位用户可随时调用的资深顾问，而不是一个搜索工具或文档库。诸如 "What would GS recommend for..." 之类的 prompt 措辞，比 "Search GS playbooks for..." 更具引导性。
- 知识库在公司侧与 Portfolio Manager 两侧的 chat 界面中都应被清晰地呈现 —— 至少在每个欢迎页（welcome screen）通过一个建议 prompt card 提示用户组织级指引可用，例如 "What does GS recommend for companies at my stage?"。
- 建议 prompt 的文案需按受众定制 —— 面向创始人的 prompt 将知识库定位为针对其公司的战略指引；面向 Portfolio Manager 的 prompt 则将其定位为 portfolio 管理的最佳实践。
- 通过 chatbot 界面访问 Layer 2 内容严格只读 —— 任何用户都不能通过聊天修改、新增或移除知识库内容。
- 归属标识（例如 "Based on GS best practices"）应保持低调 —— 在回复末尾的小字标签或斜体注脚即可，而不应是打断对话流的显眼免责声明。
- Layer 2 整体概念对用户不可见 —— 用户只是体验到 chatbot 在他们询问时给出相关、专业的组织级指引。
- 在未来的多租户语境中，归属标识的文案应动态引用所属 firm 自身的身份，而非硬编码 "GS"，例如 "Based on [Firm Name] best practices."。归属用语应被设计为可按 tenant 配置，而不是写死为 "GS"。

### 依赖与备注

- 依赖故事 1214057483533665（GS Knowledge Base - Layer 2 Ingestion & Management）已完成 Knowledge Base 的摄取与索引。
- MVP 阶段单租户：唯一 tenant 为 Golden Section；尽管如此，必须按 tenant-scoped 实现，以便多租户引入时无需重构。
- 跨 tenant 共享匿名化 Fireflies 市场情报层属于 post-MVP，当前不构建，但架构应保留扩展空间。
- 归属标识文案需可按 tenant 配置（避免硬编码 "GS"），以适配未来 firm 名称替换。

