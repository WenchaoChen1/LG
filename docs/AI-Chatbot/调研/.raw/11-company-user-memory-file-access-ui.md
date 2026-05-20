---
asana_gid: 1214147930023561
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023561
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:05:07.487Z
lg_ticket: LG-1333
type: 
story_points: 
t_shirt: M
priority: 
completed: False
---

# AI Chatbot - Company User Memory File Access UI

Business Requirements

Company Admin users must be able to view what the AI chatbot has learned about their company through a Memory Settings panel accessible within the company-side chat interface. This panel surfaces the contents of the Company Memory File (Layer 1a) in a readable, searchable, read-only format, giving users transparency into the context the AI is using to personalize their experience.
The Memory Settings panel displays only Layer 1a content - the Company Memory File. The Portfolio Admin Memory File (Layer 1b) is never referenced, revealed, or accessible through any element of the company-side interface. Company User role does not have access to the Memory Settings panel at all - it is available to Company Admin only.
This is a read-only view in MVP. Users can browse and search memory entries but cannot edit, delete, or add entries directly. The memory file grows automatically through system-driven processes as established in story https://app.asana.com/1/1170332106480422/task/1214057483533664.

Acceptance Criteria

    The Company Memory File is a single unified file per company. It is not structured as separate files per source type. Each entry within the file is tagged with a source label ("Company Profile," "Chat," or "Document") to indicate its origin. This tagging is for display and filtering purposes only — all entries live within one file.
    A Memory Settings panel is accessible to Company Admin users only within the company-side chat interface, accessible via a settings icon or secondary menu.
    The Memory Settings panel is an in-app online view within LG. There is no option to download or export the memory file to a user's local machine.
    If memory file entries are stored in markdown format on the backend, the UI must render the content in a clean, readable presentation
    Company User role does not have access to the Memory Settings panel.
    The panel displays only Company Memory File (Layer 1a) entries - no Layer 1b content is ever visible, referenced, or accessible.
    Entries are displayed in reverse chronological order with a source type label (e.g., "Company Profile," "Chat," "Document") and a timestamp. Source labels indicate origin only - no actual chat content is displayed.
    Entries displayed are distilled learnings and summaries extracted by the AI - not chat excerpts, conversation logs, or verbatim text from past conversations. Full conversation records are accessible only through the separate Chat History feature in story https://app.asana.com/1/1170332106480422/task/1214081544026468.
    A search function is available within the panel to locate specific memory entries.
    All access is read-only - no editing or deletion of entries is available in MVP.
    A brief plain-language explanation is displayed at the top of the panel (e.g., "These are the key things your AI assistant has learned about your company over time. Full conversation history is available separately.").
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices

UX Design Considerations

    The Memory Settings panel should feel like a background feature the user can explore, accessible via a secondary menu or settings icon, not a prominent navigation element.
    Use a compact list format with expandable detail per entry. Source labels should be visually distinct - consider small color-coded badges or icons for "Company Profile," "Chat," and "Document."
    The panel must never display any label, section header, or UI element that hints at the existence of a separate internal GS memory layer.
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

https://app.asana.com/app/asana/-/get_asset?asset_id=1214687052273903

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-04-28 · Liang Chunru**：Memory file 是否按 source 分多个文件（一个 Company Profile、一个 Chat、一个 Document）？只读是下载到本地还是 LG 内在线浏览？markdown 格式还有效吗？
- **2026-04-28 · Karen Arnoldi**：一家公司只有一个 memory file，按 source 标签区分（profile/chat/document）。在线浏览（不下载——memory 是活的、持续更新，下载会立即过时）。markdown 存储 OK 只要 UI 渲染用户友好。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 2. AI Chatbot - 公司用户记忆文件访问界面（Company User Memory File Access UI）

- **Asana ID**: 1214147930023561
- **LG 编号**: LG-1333
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023561

### 业务需求

Company Admin 用户必须能够通过公司端聊天界面内的 Memory Settings 面板，查看 AI Chatbot 已经"了解到"的关于其公司的信息。该面板以可读、可搜索且只读的形式展示 Company Memory File（Layer 1a）的内容，让用户对 AI 用于个性化体验的上下文具有透明度。

Memory Settings 面板仅展示 Layer 1a 的内容——即 Company Memory File。Portfolio Admin Memory File（Layer 1b）在公司端界面的任何元素中都不应被引用、暴露或可访问。Company User 角色完全无权访问 Memory Settings 面板——该功能仅对 Company Admin 开放。

在 MVP 阶段，该面板为只读视图。用户可浏览并搜索记忆条目，但无法直接编辑、删除或新增条目。记忆文件按 Company Memory File 后端故事中所建立的系统驱动流程自动增长。

### 验收标准

- Company Memory File 是每家公司唯一的统一文件，并不按来源类型拆分为多个独立文件。文件中的每个条目都会带有一个来源标签（Source label，如 "Company Profile"、"Chat" 或 "Document"）以表明其来源。该标签仅用于展示与筛选——所有条目都存放在同一个文件中。
- Memory Settings 面板仅向 Company Admin 用户开放，可在公司端聊天界面内通过设置图标或二级菜单进入。
- Memory Settings 面板是 LG 内部的在线视图（in-app online view）。不提供将记忆文件下载或导出至用户本地机器的选项。
- 若后端将记忆条目以 Markdown 格式存储，则 UI 必须以整洁、可读的形式渲染其内容。
- Company User 角色无权访问 Memory Settings 面板。
- 面板仅展示 Company Memory File（Layer 1a）的条目——任何 Layer 1b 内容都不可见、不被引用、不可访问。
- 条目按时间倒序展示，并附带来源类型标签（如 "Company Profile"、"Chat"、"Document"）和时间戳。来源标签仅用于标识条目来源——不展示任何实际的聊天内容。
- 展示的条目是由 AI 提炼出的学习要点和摘要——并非聊天片段、对话日志或往期对话的逐字文本。完整的对话记录仅可通过独立的 Chat History 功能查看。
- 面板内提供搜索功能，便于定位特定的记忆条目。
- 全部访问均为只读——MVP 阶段不提供条目的编辑或删除能力。
- 面板顶部展示一段简短、通俗的说明文案（例如 "These are the key things your AI assistant has learned about your company over time. Full conversation history is available separately."，即"以下是你的 AI 助手在不断使用过程中了解到的关于公司的关键信息。完整的对话历史可在独立功能中查看。"）。

### UX 设计要点

- Memory Settings 面板应是一个"背景式"功能，用户可主动探索访问；通过二级菜单或设置图标进入即可，不应作为主导航元素之一。
- 使用紧凑的列表式布局，每个条目支持展开查看详情。来源标签应在视觉上有所区分——可考虑为 "Company Profile"、"Chat" 与 "Document" 使用小型的彩色徽章或图标。
- 面板内绝不可出现任何标签、章节标题或 UI 元素，暗示存在独立的 Golden Section 内部记忆层。

### 依赖与备注

- 该面板严格隔离 Layer 1a 与 Layer 1b：公司端不得以任何形式暴露 Portfolio Admin Memory File。
- MVP 阶段为只读模式；记忆条目通过 Company Memory File 后端故事中的系统驱动流程自动产生与维护。
- 完整对话记录由独立的 Chat History 功能负责，不与本面板混合。

---

