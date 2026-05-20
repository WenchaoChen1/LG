---
asana_gid: 1214147930023558
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023558
asana_section: LG Backlog  / Sprint (On-Deck)
asana_status: Product Approved
asana_working_status: 
asana_modified_at: 2026-05-11T03:20:15.539Z
lg_ticket: LG-1326
type: Research task
story_points: 8
t_shirt: M
priority: High
completed: False
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

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-04-27 · Liang Chunru**：GS Playbook hosting 研究结论：GEO Impact - LG AI chatbot 在私有 RAG session 中访问 GS 公开网站，不会对该网站的 GEO 可见性贡献。AI 模型不会因 retrieval 而'学习'或提升站点权威。建议 Option B（Internal Management Only）。如需提升 GS Playbook 站 GEO，可在未来 marketing 主导的工单处理。
- **2026-05-06 · Karen Arnoldi**：确认 dev team 度假后继续 research，提交 Product Review。
- **2026-05-07 · Liang Chunru**：Wenchao 已给方案：首选格式 = Structured document store；更新机制 = 通过 LG 内专门页面管理 playbook 内容（用户直接在 UI 维护，无需替换文件）；工作量：(a) 一次性迁移现有 GS playbook 到内部格式 = 5 points (2-3 days，本来就需要)；(b) In-app playbook 管理 UI = 5 points。dev team 建议把管理 UI 含进 MVP。
- **2026-05-07 · Karen Arnoldi**：Research complete，可以 close ticket。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

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

