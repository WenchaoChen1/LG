# 第 2 部分：Memory 与知识库类需求（Memory & Knowledge Base）

> 本部分包含 4 个 Memory File 和 Knowledge Base 后端能力需求

---

## 1. Company Memory File - Layer 1a 后端（公司用户上下文）

- **Asana ID**: 1214057483533664
- **LG 编号**: LG-1329
- **状态**: Needs Sizing（Working Status = Not Started，T-Shirt = L，Priority = High，Type = User Story）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533664

### 业务需求

AI chatbot 需要为每个公司维护一份持久化、私有的 Memory File，用于记录适合公司侧用户查看并从中受益的上下文信息。本需求是两个独立的后端 Memory File 故事中的第一个 —— Layer 1a 涵盖 Company Memory File，用于存储既对 Company Admin 用户可见、又对 Portfolio Manager 可见的公司专属上下文。Layer 1b 则涵盖 Portfolio Admin Memory File，用于存储仅对 Portfolio Manager 可见的内部 GS 上下文。

Company Memory File 严格隔离于每一家具体公司之间 —— 永远不会跨公司共享，且其中任何内容都不会流入共享的 GS Knowledge Base（Layer 2）。其目的是为 chatbot 提供一个不断扩充、公司专属的智能层，使每一次回复对该公司的公司侧用户和与该公司交互的 Portfolio Manager 而言，都能随时间推移愈发精准、相关。

Company Memory File 由以下三个来源填充：

1. **第一来源**：公司在 Looking Glass 中已有的元数据。Company Settings 数据，包括 company name、description、company type、industry（在 description 中填写）、stage 以及任何其他结构化的资料字段。这为 chatbot 在第一次对话开始时就提供了一个对该公司有意义的基线认知。
2. **第二来源**：公司侧的聊天对话内容。在每个会话结束时（由会话结束事件或用户在指定时长内未活动而触发），系统会运行一次 AI 驱动的对话后抽取流程，仅识别并保存确实值得记忆的信息，包括：
   - 用户陈述的、Looking Glass 中尚未记录的关于其公司的事实
   - 对 Looking Glass 中既有数据的更正或澄清
   - 有助于提升未来回复相关性的战略性上下文
   - 不会保存完整的逐字对话记录 —— 这部分由独立的 chat history 功能处理。一般性问题、事务性交流以及 Looking Glass 中已准确记录的信息会被明确排除在外。
3. **第三来源**：公司侧用户在聊天中上传的文档。当上传文档时会并行触发两个流程：文档被进行 RAG 索引以便在当前及未来会话中可被动态检索；同时系统自动生成一份关于公司相关关键学习点的高层级摘要，作为一条 memory entry 保存。RAG 索引和摘要均严格限定在该公司的 Layer 1a 文件范围内，不会流入 Layer 1b 或 Layer 2。

### 验收标准

**初始化（Initialization）**

- 系统会自动为每家公司创建一个 Company Memory File（Layer 1a）存储（可能在首次使用 chatbot 时触发？）。
- Memory File 自动以所有可用的 Company Settings 元数据进行初始化：company name、description、company type、industry、stage 以及 Looking Glass 中存在的任何其他结构化资料字段。
- 当用户更新任何 Company Settings 字段时，对应的 memory file 条目会自动同步更新。
- 注意：当后续引入 consultative onboarding epic 时，Company Memory File 需要在该工作流中完成初始化。

**对话学习（Chat Conversation Learning）**

- 学习触发条件为会话结束（end-of-session）或用户在指定时长内未活动（具体时长 TBD）。
- 在会话结束时，系统运行一次 AI 驱动的抽取流程，仅保存对话中有意义、与公司相关的信息。
- 合格内容：用户陈述的、Looking Glass 中尚未记录的关于其公司的事实；对 Looking Glass 既有数据的更正或澄清；有助于提升未来回复相关性的战略性上下文。
- 排除内容：完整逐字对话记录、一般性资讯类问题、事务性交流，以及该公司在 Looking Glass 中已准确记录的信息。
- 完整对话记录不存储于 Memory File —— 该部分由独立的 chat history 功能处理。

**文档上传学习（Document Upload Learning）**

- 当公司侧用户在聊天中上传文档时，会并行触发两个流程：(1) 文档被进行 RAG 索引以便在当前及未来会话中可被动态检索；(2) 系统自动生成一份关于公司相关关键学习点的高层级摘要，作为 Layer 1a memory entry 保存。
- RAG 索引和 memory 摘要均严格限定在该公司的 Layer 1a 文件范围 —— 不会流入 Portfolio Admin Memory File（Layer 1b）或 GS Knowledge Base（Layer 2）。
- 文档上传由故事 1214057483533666 覆盖。

**数据隔离与访问控制（Data Isolation & Access Control）**

- 在任何情况下，一家公司的 Company Memory File 内容都不可被任何其他公司访问。
- 在任何情况下，Company Memory File 中的内容都不会流入 Layer 2（GS Knowledge Base）。
- Memory file 条目存储时附带元数据，包括来源类型（公司资料、对话抽取、文档摘要）和时间戳。
- 架构层面支持 Company Admin 用户对其自身公司只读访问，以及 Portfolio Manager 对其访问范围内的所有公司只读访问 —— UI 层实现由独立的故事覆盖。

### UX 设计要点

- 这是一个后端与数据架构故事 —— 此范围内不包含面向用户的 UI。

### 依赖与备注

- 文档上传相关需求由 Asana 故事 1214057483533666 覆盖。
- 后续引入 consultative onboarding epic 时，需要在 onboarding 工作流中加入 Memory File 的初始化逻辑。
- UI 层（Company Admin 与 Portfolio Manager 对 Memory File 的只读访问界面）由独立故事覆盖。

---

## 2. Company Memory File - Layer 1b 后端（Portfolio Admin 上下文）

- **Asana ID**: 1214147930023560
- **LG 编号**: LG-1330
- **状态**: Prioritization Complete（Working Status = Not Started，T-Shirt = M，Priority = High）
- **最近修改**: 2026-05-09
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023560

### 业务需求

本需求覆盖每家公司对应的第二份独立 Memory File —— Portfolio Admin Memory File。与 Company Memory File（Layer 1a）对公司侧用户和 Portfolio Manager 双方均可见不同，Portfolio Admin Memory File 严格属于内部数据，仅对 Portfolio Manager 与 Admin 角色可见。在任何情况下，公司侧用户都无法访问到它 —— 不论是通过 UI、Memory Settings 面板，还是通过任何措辞的聊天 prompt。

Portfolio Admin Memory File 的目的，是为 Portfolio Manager 提供针对每家公司的私有上下文层，使他们能在不向公司本身暴露任何洞察的前提下，沉淀关于该公司的内部 GS 知识、评估意见和战略性记录。这使得 Portfolio Manager 可以围绕某家公司展开更丰富、更具上下文的 AI 对话，而无需被"创始人是否应当看到这些信息"所束缚。

Portfolio Admin Memory File 仅由 Portfolio Manager 的聊天会话填充。当 Portfolio Manager 与 chatbot 围绕某家具体公司对话时，AI 从该对话中抽取出的、值得记忆的有意义内容，会被路由至该公司对应的 Portfolio Admin Memory File，而非 Company Memory File。它适用与 Layer 1a 相同的会话结束抽取逻辑和质量门槛 —— 仅保存真正有用、与公司相关的学习点，而不保存完整对话记录或事务性交流。Portfolio Manager 在某家具体公司上下文中上传的文档，也会被 RAG 索引并摘要进入 Portfolio Admin Memory File。

当为 Portfolio Manager 生成回复时，AI 模型会同时利用 Layer 1a 与 Layer 1b 的内容 —— 在用户无感知的情况下融合两份文件中的上下文。然而系统必须在架构层进行约束，确保它绝不会将 Layer 1b 的内容暴露给公司侧用户，即使公司用户精心构造措辞试图诱导模型披露也不行。系统的任何回复都不得向公司侧用户确认或暗示 Portfolio Admin Memory File 的存在。

### 验收标准

**初始化（Initialization）**

- 当 AI chatbot 首次为某家公司初始化时，系统自动为该公司创建一份 Portfolio Admin Memory File（Layer 1b）存储。
- Layer 1b 文件在数据层与 Layer 1a 文件完全分离 —— 永远不会被合并、组合或混杂。
- Layer 1b 文件以公司为粒度（company-scoped）、与 portfolio 无关（portfolio-agnostic）。每家公司只对应一份 Layer 1b 文件，无论该公司归属多少个 portfolio，也无论有多少 Portfolio Portal 用户拥有访问权。所有有权访问该公司的 Portfolio Portal 用户共享同一份 Layer 1b 文件 —— 任意被授权用户的聊天会话所产生的贡献都会写入同一份文件，所有被授权用户在 AI 生成回复时也都从该同一份文件查询。

**Portfolio Manager 聊天会话填充（Population from Portfolio Manager Chat Sessions）**

- 从 Portfolio Manager 聊天会话中抽取出的、关于某家具体公司的内容，会被路由到该公司的 Layer 1b 文件，而非 Layer 1a。
- 学习触发条件与 Layer 1a 一致 —— 会话结束或用户在指定时长内未活动。
- 适用相同的抽取质量规则：仅保存有意义、与公司相关的学习点。完整逐字对话记录、一般性问题和事务性交流被排除。
- Portfolio Manager 在某家具体公司上下文中上传的文档，会被 RAG 索引并摘要进入 Layer 1b，而非 Layer 1a。

**面向 Portfolio Manager 的上下文查询（Context Querying for Portfolio Managers）**

- 对 Portfolio Manager 用户而言，AI 在生成针对某家具体公司的回复时，会同时查询 Layer 1a 与 Layer 1b，将两份文件的上下文以无感方式融合。
- AI 永远不会在面向公司侧用户的回复中暴露 Layer 1b 的内容。

**安全与访问控制（Security & Access Control）**

- Layer 1b 内容在任何机制下（UI、聊天回复或 prompt）均不可被 Company User 或 Company Admin 角色访问。
- 在架构层实现并强制执行 prompt injection 防护，使公司侧用户无法通过任意措辞的聊天 prompt 提取 Layer 1b 内容。
- 系统的任何回复或 UI 元素都不得向公司侧用户引用或揭示 Portfolio Admin Memory File 的存在。
- 在任何情况下，一家公司的 Layer 1b 内容都不可被任何其他公司访问。
- 在任何情况下，Layer 1b 中的内容都不会流入 Layer 2（GS Knowledge Base）。
- Memory file 条目存储时附带元数据，包括来源类型（对话抽取、文档摘要）和时间戳。
- 架构仅支持 Portfolio Manager 与 Admin 角色的只读访问 —— UI 层实现由独立故事覆盖。

### UX 设计要点

- 这是一个后端与数据架构故事 —— 此范围内不包含面向用户的 UI。

### 依赖与备注

- 与 Layer 1a（故事 1214057483533664）共用相同的会话结束抽取逻辑与质量门槛。
- prompt injection 防护必须在架构层实现，而不仅仅依赖回复模板的过滤。
- UI 层（Portfolio Manager / Admin 角色对 Layer 1b 的只读访问界面）由独立故事覆盖。

---

## 3. GS Knowledge Base - Layer 2 摄取与管理（Layer 2 Ingestion & Management）

- **Asana ID**: 1214057483533665
- **LG 编号**: LG-1331
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-08
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533665

### 业务需求

AI chatbot 的双层知识架构依赖于一个已被填充、可被查询的 Golden Section Knowledge Base 作为 Layer 2 共享资源。与 Layer 1（公司专属 Memory File）由用户活动自动构建不同，Layer 2 必须由 Golden Section 内部显式地填充。在 MVP 阶段，该层由 Golden Section 已有的 playbooks 和 best practice frameworks 构成 —— 即长期沉淀下来的 GS 全部运营与战略知识。

我们已完成一项调研，用于判断将 GS playbooks 托管在公开可访问的外部网站是否能带来 Generative Engine Optimization（GEO）方面的可见性收益 —— 具体而言，AI chatbot 在会话中访问外部站点以回答用户问题，是否会提升该站点在其他 AI 模型对话中的权威性或可见度。结论是：外部托管不会带来 GEO 收益。AI 模型并不会因为在会话中接收某站点内容就从中学习或提升该站点的权威性。基于此，决定采用 Option B：将外部站点上的所有现有 GS playbook 内容复制进 Looking Glass 内部由我们管理的单一 markdown 文件。该文件即为 GS Knowledge Base 后续的内容来源。

本需求覆盖以下技术工作：(1) 将该 markdown 文件及任何配套文档摄取（ingest）为 AI chatbot 可查询的格式；(2) 为授权 GS 用户（Super Admins 与 PGMs）提供面向内部的工具能力，以便其在后续持续管理与更新内容。最终交付一个不断演进、可被检索的知识层，使所有 chatbot 用户（公司侧与 Portfolio Manager 双方）都能从中获取战略指引，但用户既不会直接看到原始文档，也不会知晓该 Knowledge Base 的具体结构。

GS Knowledge Base 与任何单家公司的 Layer 1 Memory File 完全隔离。在当前的单租户实现中，它是一个全局共享资源 —— 即对平台上所有公司、所有用户而言其内容都相同。它不包含任何公司专属数据、财务信息或关于任何 portfolio 公司或创始人的可识别信息。其唯一目的是通过 chatbot 以自然、对话式的方式，让用户可以访问到 GS 的集体运营与战略知识。

在 MVP 阶段，范围仅限于现有 playbook 内容的摄取与查询。LLM 自动从 portfolio 管理对话中识别知识库更新的能力，明确属于 post-MVP 范畴。当前阶段，当内容需要变更时，必须由授权用户手动上传或更新知识库。可编辑知识库的授权角色为 Portfolio Group Manager 及以上 —— 更低权限的角色无权修改 playbook 内容。

**给开发团队的重要架构提示**：未来当 Looking Glass 商业化并销售给外部 equity firms 时，每家公司（每个 tenant）都将需要其专属的、独立的知识库 —— 与其他 tenants 的知识库完全隔离。当前的单一共享 GS Knowledge Base 适用于 MVP 单租户实现，但在架构设计上应预留 per-tenant 知识库隔离的考量，使后续无需大规模重构即可支持多租户。**不要**以"将永远只有一个全局知识库"的假设来构建 Layer 2。

参考：外部站点为 https://www.goldensection.com/vertical-saas-playbooks

### 验收标准

**内容摄取（Content Ingestion）**

- 将外部 GS 网站上的所有现有 playbook 内容复制进一份由内部管理的 markdown 文件，作为 Layer 2 的内容来源。
- 实现一个后端摄取流水线，能够接收常见格式的 playbook 文档（至少支持 PDF、Word .docx 与 markdown .md），并将其处理为可被检索的查询存储。
- 所有摄取的内容作为共享的 GS Knowledge Base（Layer 2）的一部分被存储与索引，对所有 chatbot 用户开放，不论其所属公司或角色。
- GS Knowledge Base 与任何公司的 Layer 1 Memory File 在数据与架构层完全隔离 —— 不存在任何路径会让 Layer 2 的内容变成公司专属，反之亦然。
- 任何能识别公司的标识信息、财务数据或与创始人相关的上下文，永远不会存入 Layer 2。
- 一组完整的初始 GS playbook 内容会被摄取，并作为本故事验收测试的一部分被验证。

**内容管理（Content Management）**

- 提供一个面向内部的管理界面或流程，使授权用户能够上传新内容、更新 markdown 文件，或从知识库中移除文档。
- 上传、编辑或移除知识库内容的权限仅限 Portfolio Group Manager 角色及以上。更低权限的角色不能修改知识库。
- 当内容被上传或更新时，知识库会自动重新索引，使新增或变更的内容立即可被查询。
- 当内容从知识库中移除后，将不再在 chatbot 回复中被检索到。
- 管理界面提供一个简洁的状态指示器，展示知识库最近一次更新的时间以及当前已索引的文档数量。

**Chatbot 查询行为（Chatbot Query Behavior）**

- chatbot 能在用户询问战略、最佳实践或 GS 指引相关问题时，准确检索并引用已摄取 playbook 内容中的相关章节。
- 借助 Layer 2 内容生成的回复不会逐字暴露原始文档文本 —— AI 会以对话式语言对相关指引进行综合与摘要。

**未来多租户兼容性（Future Multi-Tenancy Compatibility）**

- Layer 2 架构在设计上支持未来的 per-tenant 知识库隔离，使每家外部 equity firm 在多租户实现后能够拥有其独立的知识库。

### UX 设计要点

- 公司侧用户和 Portfolio Manager 都不会直接看到知识库文档本身 —— 他们只通过 chatbot 的自然语言回复与知识库交互。MVP 阶段没有"浏览 playbooks"的 UI。
- 用于上传与管理 playbook 内容的内部管理界面在 MVP 阶段不需要做到消费级精致 —— 只需可用、可靠。一个具备文档列表、状态指示器、上传能力与删除功能的简洁界面即可。
- 在面向 chatbot 用户侧，当某条回复大量引用了 GS playbook 内容时，加上一个不显眼的归属标识是合适的，例如 "Based on GS best practices"，让用户理解指引的来源，但不暴露具体的文档名或内容。
- 推荐采用 markdown 文件作为主要的内容管理格式，因为它对人类可读、轻量、便于人和 AI 处理，并且易于进行版本管理和持续更新。

**额外验收标准（RAG 细节，Additional Acceptance Criteria - RAG specifics）**

- 实现一个后端摄取流水线，能够接收常见格式的 playbook 文档（至少支持 PDF、Word .docx 与 markdown .md），并将其处理为可供 RAG 检索的 vector store。
- 知识库摄取流水线必须与 "AI Architecture & Model Routing Foundation" 故事中所建立的 RAG 架构兼容。
- 一组初始的 GS playbooks 会被摄取，并作为本故事验收测试的一部分被验证 —— 知识库在上线时不能为空。

### 依赖与备注

- 依赖前置故事 "AI Architecture & Model Routing Foundation"（用于 RAG 架构）。
- 内容编辑权限：Portfolio Group Manager 及以上。
- LLM 自动从对话中识别知识库更新的能力为 post-MVP，本故事不构建。
- 架构必须为 per-tenant 知识库隔离做预留，避免后续大规模重构。

---

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
