---
asana_gid: 1214147930023560
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023560
asana_section: LG Backlog  / Backlog
asana_status: Prioritization Complete
asana_working_status: Not Started
asana_modified_at: 2026-05-09T00:04:53.327Z
lg_ticket: LG-1330
type: 
story_points: 
t_shirt: M
priority: High
completed: False
---

# Company Memory File - Layer 1b Backend (Portfolio Admin Context)

Business Requirements

This story covers the second distinct memory file per company - the Portfolio Admin Memory File. Unlike the Company Memory File (Layer 1a in story https://app.asana.com/1/1170332106480422/task/1214057483533664), which is visible to both company-side users and portfolio managers, the Portfolio Admin Memory File is strictly internal and visible only to Portfolio Manager and Admin roles. It is never accessible to company-side users under any circumstances - not through the UI, not through the Memory Settings panel, and not through chat prompts regardless of how they are worded.
The purpose of the Portfolio Admin Memory File is to give portfolio managers a private context layer for each company where they can accumulate internal GS knowledge, assessments, and strategic notes about that company without any risk of those insights being exposed to the company itself. This enables portfolio managers to have richer, more contextually informed AI conversations about a company without being constrained by what is appropriate for the founder to see.
The Portfolio Admin Memory File is populated exclusively from portfolio manager chat sessions. When a portfolio manager is chatting about a specific company, content that the AI extracts from that conversation as meaningful and worth remembering is routed to that company's Portfolio Admin Memory File, not the Company Memory File. The same end-of-session extraction logic and quality threshold applies - only genuinely useful, company-relevant learnings are saved, not full transcripts or transactional exchanges. Documents uploaded by portfolio managers in the context of a specific company are also RAG-indexed and summarized into the Portfolio Admin Memory File.
The AI model draws on both Layer 1a and Layer 1b when generating responses for portfolio managers - synthesizing context from both files invisibly. However the system must be constrained at the architecture level so that it never surfaces Layer 1b content to company-side users, even if a company user constructs a carefully worded prompt attempting to extract it. The existence of the Portfolio Admin Memory File must never be confirmed or revealed to company-side users through any system response.

Acceptance Criteria

Initialization
    A Portfolio Admin Memory File (Layer 1b) store is automatically created for each company upon first initialization of the AI chatbot for that company.
    The Layer 1b file is entirely separate from the Layer 1a file at the data layer - they are never merged, combined, or co-mingled.
    The Layer 1b file is company-scoped and portfolio-agnostic. A single Layer 1b file exists per company, regardless of how many portfolios that company belongs to or how many Portfolio Portal users have access to it. All Portfolio Portal users with access to a given company share the same Layer 1b file for that company — contributions from any authorized user's chat sessions are written to the same file, and all authorized users query from the same file when the AI generates responses.
Population from Portfolio Manager Chat Sessions
    Content extracted from portfolio manager chat sessions about a specific company is routed to that company's Layer 1b file, not Layer 1a.
    The learning trigger mirrors Layer 1a - end-of-session or a defined period of user inactivity.
    The same extraction quality rules apply: only meaningful, company-relevant learnings are saved. Full verbatim transcripts, generic questions, and transactional exchanges are excluded.
    Documents uploaded by portfolio managers in the context of a specific company are RAG-indexed and summarized into Layer 1b, not Layer 1a.
Context Querying for Portfolio Managers
    For portfolio manager users, the AI queries both Layer 1a and Layer 1b when generating responses about a specific company, synthesizing context from both files invisibly.
    The AI never surfaces Layer 1b content in any response to a company-side user 
Security & Access Control
    Layer 1b content is never accessible to Company User or Company Admin roles through any mechanism - UI, chat response, or prompt.
    Prompt injection protections are implemented and enforced at the architecture level, preventing company-side users from extracting Layer 1b content regardless of how a chat prompt is worded.
    The existence of the Portfolio Admin Memory File must never be referenced or revealed to company-side users through any system response or UI element.
    No Layer 1b content from one company is accessible to any other company under any circumstances.
    No content from Layer 1b flows into Layer 2 (GS Knowledge Base) under any circumstances.
    Memory file entries are stored with metadata including source type (chat extraction, document summary) and timestamp.
    The architecture supports read-only access for Portfolio Manager and Admin roles only - UI implementation is covered in a separate story.

UX Design Considerations

    This is a backend and data architecture story — no user-facing UI is in scope.

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-04-27 · Liang Chunru**：当前设计 Layer 1b 每公司一个文件。如果一家公司同属一名 PM 的多个 portfolio，那么 Layer 1b 还是同一个？多个 PM 是否共享同一公司的 Layer 1b？
- **2026-04-27 · Karen Arnoldi**：好问题，我和 Dougal 确认下。
- **2026-05-01 · Karen Arnoldi**：Dougal 已确认：理解正确——Layer 1b 不按 portfolio 区分，是公司专属并被所有可访问该公司的 PM 共享。
- **2026-05-06 · Liang Chunru**：已更新 AC 反映 Layer 1b 共享细节。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

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

