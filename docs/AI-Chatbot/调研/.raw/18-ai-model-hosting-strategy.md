---
asana_gid: 1214717456780780
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214717456780780
asana_section: LG Backlog  / Backlog
asana_status: Needs Sizing
asana_working_status: Not Started
asana_modified_at: 2026-05-11T15:11:40.236Z
lg_ticket: LG-1381
type: Research task
story_points: 
t_shirt: 
priority: High
completed: False
---

# AI Model Hosting Strategy

Business Requirements

The AI chatbot epic is currently planned to be architected around a third-party API routing layer (OpenRouter) that connects to external model providers such as Anthropic's Claude. While this approach is appropriate for MVP and provides the cost optimization and model routing flexibility required, a concern was raised that warrants investigation before the architecture is finalized and development begins in earnest.
The concern has two related dimensions:
    The first is session isolation and platform risk. When using a shared third-party API, the question is whether one user's session being flagged, restricted, or shut down by the model provider's content moderation system could have any impact on the platform for other users. For example, if a founder asks a question that trips a content filter, even innocently, such as asking about competitive displacement tactics or aggressive pricing strategies, the model might refuse to respond or in extreme cases flag the session. In a consumer-facing application built on an enterprise API, it is critical to understand whether that response is session-scoped (affecting only that user's current interaction) or whether it could affect the platform's API access more broadly. Additionally the team should understand what liability Looking Glass carries as the platform operator when a user's chat session triggers a content moderation event, and what recourse exists.
    The second dimension is the long-term strategic question of whether hosting a model behind Looking Glass's own firewall, rather than routing through a third-party API, makes sense given the product's narrow, focused vertical use case. A self-hosted or private model deployment would give the team greater control over content policies, response behavior, and the user experience in ways that are particularly relevant for a business-focused vertical application where founders may regularly ask questions about competitive strategy, pricing, contract negotiation, and other topics that generic public models may handle inconsistently. A private deployment would also eliminate the risk of the model's content policies becoming more restrictive over time in ways that could interfere with legitimate business conversations. Additionally it may provide more predictable token cost management as the user base scales.
 
The team should understand the risk landscape and ensure the current architecture does not foreclose a future path to private model hosting if the commercial and risk shifts. If any architectural decisions need to be made differently in the current MVP architecture to accommodate a future transition to private hosting, those should be identified and flagged now rather than discovered during a future migration.
 

Acceptance Criteria

Session Isolation Research
    The team researches and documents a clear answer to the following question: 
        When using an enterprise API agreement with the chosen model provider (OpenRouter/Anthropic), is content moderation enforced at the individual session level or at the API key or account level? 
        Specifically, can one user's session being flagged or shut down affect the platform's API access or other users' sessions?
    The research documents what happens technically and operationally when a user's message triggers a content moderation event - what response does the API return, what is logged, and what if any notification or action is taken at the account level?
    The research documents what liability Looking Glass carries as the platform operator when a user's chat session triggers a content moderation event with a third-party model provider.
    The research identifies whether there are enterprise API agreement terms available from Anthropic or OpenRouter that provide stronger session isolation guarantees or clearer liability protections than the standard API terms.
    A clear recommendation is provided: based on the findings, is the current architecture adequately protected against cross-session contamination from content moderation events, or are additional safeguards needed?
Private Model Hosting Feasibility
    The team researches and documents the current landscape of options for hosting a model privately behind Looking Glass's own firewall, including self-hosted open source models, private cloud deployments of commercial models, and any other relevant approaches.
    For each option identified, the research documents: estimated infrastructure cost, technical complexity of implementation, quality comparison to the current API approach, ability to update the model over time, and level of control over content policies and response behavior.
    The research identifies whether any architectural decisions in the current story https://app.asana.com/1/1170332106480422/task/1214057483533668 would need to be made differently today to support a future transition to private hosting without significant rearchitecting. If any such decisions exist they should be flagged as specific recommendations to the architecture story.
    A clear recommendation is provided: given the current stage of the product and the identified risks, should LG continue with the third-party API approach for MVP and near-term production, or does the risk/benefit analysis suggest accelerating a move toward private hosting?
Content Moderation Layer
    The team investigates whether a lightweight content moderation or intent classification layer can be introduced between the user's input and the model API call, acting as a first-pass filter that catches obviously problematic inputs before they reach the model provider, reducing the risk of triggering external content moderation while preserving the user experience.
    The research documents the effort, cost, and technical approach for implementing such a layer if recommended.
    The research identifies whether this is something that should be built into the MVP architecture story now or added as a separate story in a future sprint.
Output & Recommendation
    The research output is documented in a format that can be shared with the product owner if needed (Dougal Cameron) as a brief summary, covering the key findings and recommendations for each of the three areas above.
    The product team can use this output to make a final decision on whether any changes are needed to the AI Architecture & Model Routing Foundation story before development begins.

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

_本任务暂无业务相关评论（仅系统消息）。_

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

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

