# 第 1 部分：基础与研究类需求（Foundation & Research）

> 本部分包含 **6** 个基础研究和架构类需求（含 2026-05-12 拉取新增的 LG-1381 AI Model Hosting Strategy）

---

## 1. 研究：用于聊天机器人的 AI 模型评估（Research AI Models for Chatbot Use）

- **Asana ID**: 1213876002981172
- **状态**: ✅ 已完成
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1213876002981172

### 业务需求

针对 LG AI Assistant MVP 评估并推荐最优的 LLM（大语言模型）策略，使其与以下业务目标和范围保持一致：

- 在结构化与非结构化的公司数据之上进行对话式分析
- 按公司维度的持久化记忆（Persistent memory per company）
- Playbook（行动手册）摄取
- 具备成本效率的可扩展性
- 企业级安全与数据处理能力
- 会议转录（Fireflies）摄取（MVP 之后）

我们正在构建的 AI 助手需要：

- 回答关于公司经营表现的问题（forecasts、plans、benchmarks）
- 维护按公司维度的记忆
- 摄取内部 playbooks
- 摄取会议转录并补充至公司记忆中（MVP 之后）
- 不同任务可能需要不同的模型能力

如经评估有必要，系统应支持多模型架构（multi-model architecture），以便：

- 切换服务商（如 OpenAI、Anthropic、开源模型）
- 针对不同工作负载使用不同模型（在成本与质量之间权衡）

### 验收标准

#### 1. 待评估的模型服务商

至少应包含：

- OpenAI（GPT 系列）
- Anthropic（Claude 系列）
- 开源模型（如 LLaMA、Mistral、Mixtral 等）

可选评估：

- Google Gemini
- 其他新兴的企业级模型

#### 2. 评估维度

**A. 能力契合度（最重要）**

评估每个模型对以下能力的支持程度：

- 在结构化与非结构化数据之上的对话式问答（RAG）
- 长上下文推理（forecasts、transcripts、memory）
- 指令遵从性与一致性
- 工具调用 / 函数调用（Tool use / function calling）
- 摘要生成与洞察生成

说明：

- 部分模型更强调多模态与产品灵活性
- 部分模型更强调推理深度与长上下文能力

**B. 成本与性能**

- 单 token 成本（输入 / 输出）
- 延迟 / 响应时长
- 成本优化策略（模型分层 model tiering）
- 可行性评估：
  - 用低成本模型做预处理
  - 用高端模型生成最终回复

**C. 集成能力**

- API 质量与灵活性
- SDK / 工具生态成熟度
- 实施难度：
  - RAG 的实施
  - 记忆系统
  - 多模型编排（Multi-model orchestration）

**D. 安全与合规**

需评估：

- 数据隐私保障
- 数据保留策略
- 处理敏感投资组合数据的风险

**E. 可靠性与稳定性**

- 模型版本管理 / 弃用情况
- 在线时长 / SLA 相关考量
- 向后兼容风险

**F. 可扩展性与架构契合度**

- 多模型编排的可行性
- 路由策略（基于任务类型的模型选择）

#### 研究产出 —— 书面报告，包含：

**1. 各模型的优劣分析**

针对每个模型说明：

- 与 LG 用例契合的优势
- 弱点 / 局限
- 在系统中最适合扮演的角色（如 reasoning 与 summarization）

**2. 推荐架构**

必须包含：

**A. 单模型 vs 多模型推荐**

需明确：

- 是从单模型起步？
- 还是从第一天起就设计为多模型？

**B. 建议的模型角色（示例）**

- "重度推理（Heavy reasoning）"模型
- "低成本处理（Cheap processing）"模型
- "记忆摘要（Memory summarization）"模型

**3. 安全与风险评估**

需识别：

- 数据暴露风险
- 服务商依赖风险
- 模型幻觉（hallucination）风险
- 成本超支风险

**4. 约束与依赖**

例如：

- 基础设施需求（针对开源模型自托管）
- 服务商合同 / 价格分级
- 延迟约束
- 数据管道就绪度（RAG 的依赖项）

**5. 最终推荐（Executive Summary）**

需提供：

- 明确的推荐结论：
  - MVP 中使用哪个 / 哪些模型
  - 原因（与业务目标挂钩）
- 建议的演进路径（MVP 之后）

### 关键考量点

- 不可默认假设单模型方案就足够
- 在成本与质量之间做权衡优化
- 保证未来的灵活性（避免厂商锁定）
- 优先保障企业级安全的架构

### 成功标准

本研究若达成以下条件即视为成功：

- PO 能够自信地决策：
  - MVP 中使用哪个 / 哪些模型
  - 是否采用多模型架构
- 工程团队充分理解：
  - 架构层面的影响
  - 成本权衡
  - 安全考量

### 依赖与备注

- Lovable Prototype：（链接见 Asana）
- 入口：顶部导航 → Ask AI 标签

---

## 2. 研究：GS Playbook 托管策略 —— 外部托管（GEO 视角）vs LG 内部托管（Research: GS Playbook Hosting Strategy - External (GEO) vs. Internal LG Management）

- **Asana ID**: 1214147930023558
- **LG 编号**: LG-1326
- **状态**: Product Approved（Sprint On-Deck，Story Points = 8，T-Shirt = M，Priority = High）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023558

### 业务需求

Golden Section（GS）的 playbooks 是 AI 聊天机器人 Layer 2 知识库的核心组成部分。在团队最终确定 playbooks 在 Looking Glass（LG）内的摄取与管理方式之前，必须先做一个基础性的托管决策：playbooks 应继续托管在 Golden Section 公开访问的外部网站上，还是应复制到 Looking Glass 内部、完全由内部管理？外部网站参考地址为：https://www.goldensection.com/vertical-saas-playbooks

这一决策不仅是技术问题，还潜在地涉及一个与 GEO（Generative Engine Optimization，生成式引擎优化）概念相关的市场曝光维度。GEO 是一种新兴实践，致力于优化内容，使其在用户与 Claude 或 ChatGPT 等 AI 模型交互时，能够作为受信赖的权威参考被引用 —— 可视作传统 SEO（Search Engine Optimization，搜索引擎优化）的 AI 等效形态。Dougal 提出了一种可能性：如果 GS playbooks 托管在公开访问的网站上，且 Looking Glass AI 聊天机器人在回答用户问题时访问该网站，由此产生的访问活动可能贡献于 GEO 可见性 —— 也就是说，GS playbook 内容可能开始作为推荐参考出现在与 Looking Glass 完全无关的其他 AI 对话中，从而以有机方式扩展 GS 的影响范围。

如果该 GEO 收益真实且具有实际意义，则首选方案是将 playbooks 保留在 GS 公开外部站点上，并仅在 Looking Glass 内部维护一份 markdown 格式的 changelog 文件，用于记录历次更新、新增与变更。AI 聊天机器人在回答问题时同时引用外部站点和内部 markdown 文件，外部站点作为主要来源，内部文件捕获专有的、持续演进的知识层。该方案避免了在 LG 内部重复管理完整的 playbook 内容，同时仍能让聊天机器人访问最新版本。

如果 GEO 收益不真实或可忽略不计，则更简单、更可控的方式是：将所有 playbook 内容复制到 Looking Glass 中，作为单一受管 markdown 文件（或等效的结构化形式），完全在内部处理。届时外部站点将不再是聊天机器人 playbook 的真实来源 —— LG 将取而代之。

研究团队需直接评估两种方案的技术可行性以及 GEO 这一问题，以便在 AI 聊天机器人 epic 中 playbook 摄取相关 story 开发之前，向 Dougal 提交清晰、有依据的推荐结论。

### 验收标准

#### GEO 研究

- 团队需研究并以书面方式清晰回答以下问题：当 Claude 或 ChatGPT 等语言模型在回答用户问题时访问公开托管的网站，是否会以任何具有实质意义的方式贡献于该网站的 GEO 可见性？也就是说，是否会让该网站更可能在与 Looking Glass 无关的其他 AI 对话中作为参考被引用？
- 研究需涵盖目前已知的 GEO 可见性最佳实践或机制，并确认托管位置（公开 URL vs. 内部文件）是否是相关因素之一。
- 给出明确推荐：将 playbooks 托管在 GS 公开站点上是否带来值得保留的 GEO 优势，还是不构成有意义的因素？

#### 方案 A —— 外部托管 + 内部 markdown changelog（如确认存在 GEO 收益）

- 团队评估聊天机器人同时引用外部公开 URL（GS playbooks 网站）与内部 markdown changelog 文件的技术可行性
- 团队识别该方案的限制、风险或复杂性，包括：从外部 URL 拉取的延迟、对外部站点可用性的依赖、版本控制挑战，以及合并外部内容与内部内容的复杂度
- 团队给出该双源方案的工作量估算

#### 方案 B —— 仅内部管理（如未确认存在 GEO 收益或收益可忽略）

- 团队评估将外部站点上现有的全部 GS playbook 内容复制到 Looking Glass 内部、作为单一受管文件或结构化格式所需的工作量
- 团队明确推荐的内部格式（如：单一 markdown 文件、结构化文档存储、wiki 风格的 CMS）
- 团队给出该方案的工作量估算

#### 最终推荐

- 研究产出包含明确的方案 A 或方案 B 推荐结论，附支持理由，覆盖：GEO 影响评估、技术复杂度、长期维护开销，以及与 AI 聊天机器人架构的契合度
- 推荐还应说明：在所推荐方案下，playbook 的更新和管理员编辑工作如何运行 —— 这将作为输入纳入 AI 聊天机器人 epic 中规划的更广泛的 playbook 管理功能。**注意**：MVP 范围内仅包含 admin 编辑功能；MVP 之后才纳入 AI 主动更新 playbook 的能力（管理员保留审阅权及在需要时删除的能力）
- Dougal 可基于该推荐做出最终决策，产品团队据此推进 AI 聊天机器人 epic 中 playbook 摄取 story 的定义工作

### 依赖与备注

- 决策必须先于 playbook 摄取 story 的开发进行
- 该决策直接影响 Layer 2 的实现方式
- MVP 阶段：仅 admin 可编辑；POST MVP 阶段：AI 可主动更新（admin 保留审核与删除权限）

---

## 3. 公司档案扩展 —— 增强描述（Company Profile Expansion - Enhanced Description）

- **Asana ID**: 1214057483533667
- **LG 编号**: LG-1327
- **状态**: Product Review（Working Status = In Progress，Story Points = 2，T-Shirt = M，Priority = High）
- **最近修改**: 2026-05-07
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533667

### 业务需求

AI 聊天机器人的公司 Memory File（Layer 1，公司记忆文件）会以 Looking Glass 中现有的公司元数据进行初始化。为确保聊天机器人从第一天起就对每个公司具备有意义的基础理解，这些元数据应尽可能完整且有用。Looking Glass 已在 Company Settings 中记录了公司的 type 与 stage（公司类型与阶段），因此这两个字段可直接进入 Memory File，无需额外工作。

但是，现有的公司 description 字段不足以使用 —— 该字段在内容范围与字符长度上都受限，过于浅薄，无法让聊天机器人真正了解公司在做什么。由于目前不存在 industry（行业）字段（行业能提供更具体的市场上下文），因此应将 industry 添加到 description 字段的默认提示文本中。一段扩展后的 description 加上明确的 industry 字段，可在每次对话中为聊天机器人提供更加丰富的起点，避免用户每次都需要从零开始重新解释自身业务背景。

本 story 的内容是：在 Company Settings 中新增 industry 字段，并扩大 description 字段的字符上限及默认指引文案以将 industry 纳入。这些信息会在聊天机器人初始化时直接进入公司的 Layer 1 Memory File，并在用户每次修改时同步更新到 Memory File 中。

### 验收标准

- 现有 Company Overview 字段的默认提示文案需更新，明确提及包含公司 industry
- 现有公司 description 字段的字符上限需大幅提升，足以容纳一段有意义、多句的公司描述（具体字符上限 TBD —— 需开发评估输入）
- 在 description 字段中增加辅助说明文本或占位符（placeholder），引导用户填写要点（例如："Describe what your company does, who your customers are, and what makes you unique."（描述你的公司做什么、客户是谁，以及独特之处是什么））
- 当 AI 聊天机器人首次为该公司初始化时，更新后的扩展 description 自动写入该公司的 Layer 1 Memory File
- 当用户更新该字段时，Memory File 会同步更新以反映变更

### UX 设计要点

- 通过标签或辅助文本将扩展后的 description 字段与 AI 聊天机器人关联起来，例如使用 "Help your AI assistant understand your business"（帮助你的 AI 助手了解你的业务）这样的措辞，使用途对用户一目了然
- 在辅助文本或二级辅助文本中包含 industry 提示
- 对扩展后的 description 字段，建议显示字符计数指示器，让用户了解还剩多少可用空间
- Prototype（原型）：https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=12659-18116&t=KHCzpckmM4pYfdQF-1
- Asset：https://app.asana.com/app/asana/-/get_asset?asset_id=1214224205484917

### 依赖与备注

- 该 story 直接喂入 Layer 1 Memory File 初始化流程
- 字符上限的最终值需开发团队评估后确定

---

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

## 5. AI 聊天机器人 —— Skills / Report Builder（AI Chatbot - Skills/Report Builder）

- **Asana ID**: 1214110731636985
- **LG 编号**: —（暂未分配）
- **状态**: 待定（无 LG Status；Post-MVP；最近修改 2026-04-17）
- **Asana 链接**: https://app.asana.com/1/1170332106480422/task/1214110731636985

### 业务需求

本 story 用于处理 skills 与报告生成过滤器（report generation filter），属于 post-MVP 范围。

### 验收标准

（原文未提供详细验收标准，待 post-MVP 阶段进一步细化）

### UX 设计要点

（原文未提供 UX 设计要点，待 post-MVP 阶段进一步细化）

### 依赖与备注

- 该功能明确属于 post-MVP 范围，MVP 不实现
- 在 AI Architecture & Model Routing Foundation（任务 4）中已说明：MVP 架构不强制为 Skills 做适配，但需在 post-MVP 阶段统一考量
- 后续需补充：skills 体系的具体能力清单、report builder 的过滤器规则、用户角色与权限模型，以及与 Layer 1a/1b/Layer 2 的交互关系

---

## 6. AI 模型托管策略（AI Model Hosting Strategy）— 新增

- **Asana ID**: 1214717456780780
- **LG 编号**: LG-1381
- **状态**: Needs Sizing（Backlog，Priority = High，Type = Research task）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214717456780780

### 业务需求

AI 聊天机器人 epic 当前计划基于第三方 API 路由层（OpenRouter）连接到外部模型服务商（如 Anthropic Claude）。这一方案对 MVP 是合适的，并能提供所需的成本优化与模型路由灵活性，但在架构最终确定、开发正式启动之前，团队提出了一个需要先调研的关切。

该关切包含两个相关维度：

#### 1. 会话隔离与平台风险

在使用共享第三方 API 时，需要回答：一个用户的会话被模型服务商的内容审核系统标记、限制或关闭，是否会以任何方式影响平台上其他用户？例如：某位创始人提出了一个无意触发内容过滤器的问题（如询问竞品替换策略或激进定价策略），模型可能拒绝回复，极端情况下还可能标记该会话。在一个构建于 enterprise API 之上的面向用户应用中，必须明确：该响应是会话级别（仅影响该用户当前交互）还是会广泛影响平台的 API 接入？另外，当用户的聊天会话触发内容审核事件时，Looking Glass 作为平台运营方承担怎样的责任，有何救济渠道，也需要厘清。

#### 2. 长期策略：自托管模型

第二个维度是长期战略问题：考虑到产品聚焦于一个狭窄的垂直业务场景，将模型托管在 Looking Glass 自己的防火墙之内（而非通过第三方 API 路由）是否更合适。私有部署的自托管模型可让团队对内容策略、回复行为与用户体验拥有更大控制力 —— 这对一个聚焦商业场景的垂直应用尤为相关，因为创始人会频繁询问竞争策略、定价、合同谈判等通用公共模型处理可能不一致的话题。私有部署也消除了模型内容策略未来变得更受限以致干扰合法商业对话的风险，并可能在用户规模扩张时提供更可预测的 token 成本管理。

团队应理解风险全貌，确保当前架构不会阻断未来转向私有模型托管的路径。如果当前 MVP 架构中需要做出与未来私有托管兼容的特殊决策，应当现在就识别并标注出来，而不是在未来迁移时才发现。

### 验收标准

#### 会话隔离调研（Session Isolation Research）

- 团队需调研并以书面方式回答：当一个用户的会话被模型服务商内容审核系统标记、限制或关闭时，是否会以任何形式影响该 API key 的其他会话或整个 LG 平台
- 明确平台级 API 接入风险（speed-limit、quota、ban）的触发条件与边界
- 评估 Looking Glass 作为平台运营方在用户会话触发内容审核事件时承担的法律责任与商业责任
- 给出运营层面的应对建议（如：日志、用户教育、内容过滤前置等）

#### 私有/自托管模型调研（Private Hosting Research）

- 调研主流可选私有部署方案（如 LLaMA、Mistral、Mixtral 等开源模型）及其在 LG 垂直商业场景下的能力契合度
- 评估自托管的总拥有成本（TCO），包括基础设施、运维、监控、模型微调等
- 评估自托管在内容策略可控性、token 成本可预测性、数据隐私方面的具体收益
- 评估自托管的弊端：模型迭代滞后、运维负担、初始投入

#### 架构兼容性评估（Architecture Compatibility）

- 评估当前 MVP 架构（OpenRouter + 多 agent）是否预留了"未来切换到自托管模型"的扩展点
- 标注需要在 MVP 阶段就采取的"非阻断性"决策，避免未来迁移时出现不可逆的设计债

#### 最终推荐（Executive Recommendation）

- 给出明确推荐：MVP 阶段坚持 OpenRouter；何时（基于哪些触发条件，如用户数、合规要求、成本阈值等）应启动私有托管迁移
- 列出 MVP 阶段需要规避的架构决策（如：硬编码服务商 SDK、单一模型假设等）

### UX 设计要点

- 本任务为研究性 story，无直接 UI 影响

### 依赖与备注

- **依赖**：与 LG-1311 Research AI Models for Chatbot Use（已完成）的结论保持一致；本任务在其结论基础上进一步针对"托管位置"做评估
- **影响**：本任务的结论将影响 LG-1328 AI Architecture & Model Routing Foundation 的最终架构形态
- **优先级**：High（Backlog，待 Sizing）
- **范围**：研究产出 + 架构兼容性 checklist，不涉及代码实现
