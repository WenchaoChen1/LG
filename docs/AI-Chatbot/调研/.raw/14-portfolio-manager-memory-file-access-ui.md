---
asana_gid: 1214081544026466
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026466
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:12:05.417Z
lg_ticket: LG-1336
type: 
story_points: 
t_shirt: M
priority: 
completed: False
---

# AI Chatbot - Portfolio Manager Memory File Access UI

Business Requirements

Portfolio managers must be able to view the memory files of all companies within their access scope through a Memory Settings panel in the portfolio manager chat interface. Unlike the company-side Memory Settings panel which shows only the Company Memory File, the portfolio manager panel provides visibility into both the Company Memory File (Layer 1a) and the Portfolio Admin Memory File (Layer 1b) for each company, with clear visual distinction between them.
The Company Memory File section shows context that company admins can also see - profile data, learnings from company-side chat sessions, and summaries from company-uploaded documents. A clear label indicates this content is visible to company admins. The Portfolio Admin Memory File section shows internal GS context added through portfolio manager activity. This section carries a clear "Internal, not visible to company users" label so portfolio managers always understand what they are looking at. User roles with access to this are all admin roles, including Super Admin, PGM, and PM roles that have access to that company
Both views are strictly read-only in MVP. Portfolio managers cannot directly edit or delete memory entries through the UI. They can browse and search entries across both files for any company within their access scope.

Acceptance Criteria

    A Memory Settings panel is accessible to Admin roles within the portfolio manager chat interface. Admin roles = Super Admin, PGM, PM
    The panel includes a company selector dropdown allowing the portfolio manager to select which company's memory files to view, scoped to companies within their access scope only.
    The panel displays both the Company Memory File (Layer 1a) and the Portfolio Admin Memory File (Layer 1b) for the selected company, with clear and immediate visual distinction between the two sections.
    The Company Memory File section is labeled to indicate it is visible to company admins (e.g., "Shared with Company Admins").
    The Portfolio Admin Memory File section is labeled to indicate it is internal only (e.g., "Internal GS Memory, not visible to company users").
    Memory entries within each section are displayed in reverse chronological order with source label (company profile, chat extraction, document summary) and timestamp.
    A search function is available, searchable across both files or filtered to one file.
    All access is read-only - no editing or deletion of entries is available in MVP.
    PGM and PM users can only access memory files for companies within their own access scope - memory files for companies outside their scope are not visible or accessible.
    A brief plain-language explanation is displayed at the top of the panel (e.g., "Company Memory is shared with company admins. Internal GS Memory is visible to GS team only.").
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices

UX Design Considerations

    The Memory Settings panel for portfolio managers should make it easy to switch between companies, perhaps a company selector dropdown at the top of the panel
    The visual distinction between Layer 1a and Layer 1b sections must be immediately obvious - consider a tab-based layout, different section headers with distinct color treatments, or clear dividers with label badges.
    The "Internal - not visible to company users" label on the Layer 1b section should be consistently visible
    Display entries in a compact, scannable list format with expandable detail per entry. 
    The search function should clearly indicate which file(s) are being searched, with an option to filter to one file or search both.
    Include a brief plain-language explanation at the top of the panel describing what the memory file contains and that access is read-only (e.g., "This is what your AI assistant has learned about this company. You can browse and search these memories but cannot edit them directly.").
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

https://app.asana.com/app/asana/-/get_asset?asset_id=1214687052273909

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-04-27 · Liang Chunru**：需要 memory file type filter（Company Memory File、Portfolio Admin Memory File）吗？
- **2026-04-27 · Karen Arnoldi**：需要。具体用 tabs/dropdown/radio 等可在设计时 finalize。
- **2026-04-28 · Liang Chunru**：角色定义澄清：当前 ticket 用'Portfolio Manager'和'Admin'，但系统现在配置为 PM/PGM/Super Admin。'Admin'是否覆盖所有 admin 端非 PM 角色（含未来）？2 项区分：(1) Layer 1b 贡献——doc 称'仅由 PM chat sessions populate'；(2) Layer 2 管理——'Admin'可管理 Playbook。我理解你想塑造的功能形态：Layer 1b 与公司绑定（任何 admin 端用户 chat 公司时存入 Layer 1b）；任何可访问公司的 admin 端用户可使用该公司 Layer 1b。
- **2026-04-28 · Karen Arnoldi**：理解大致正确，我和 Dougal 确认下。要点：是否一个 admin 的 chat 内容应对其他 admin 私有？
- **2026-05-01 · Karen Arnoldi**：Dougal 已确认：理解正确——Layer 1b 与公司绑定，任何 PGM/PM 用户访问该公司时，他们的 chat/meaningful items 保存到同一 memory file。Layer 2 编辑权限（playbook 管理）给 Super Admin 或 PGM 用户。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 2. AI Chatbot - Portfolio Manager Memory File 访问 UI（Portfolio Manager Memory File Access UI）

- **Asana ID**: 1214081544026466
- **LG 编号**: LG-1336
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026466

### 业务需求

Portfolio Manager 必须能够通过 Portfolio Manager 聊天界面中的 Memory Settings 面板，查看其访问范围内所有公司的 Memory File。与 Company 端 Memory Settings 面板仅展示 Company Memory File 不同，Portfolio Manager 面板需为每家公司同时提供 Company Memory File（Layer 1a）与 Portfolio Admin Memory File（Layer 1b）的可见性，并以清晰的视觉差异区分两者。

Company Memory File 区域展示 Company Admin 也能看到的上下文——包括 Profile 数据、Company 端聊天会话中提取的 learnings，以及 Company 上传文档的摘要。该区域需附带清晰标签，标明该内容对 Company Admin 可见。Portfolio Admin Memory File 区域展示通过 Portfolio Manager 活动添加的内部 GS 上下文。该区域必须附带清晰的"Internal, not visible to company users"（内部使用，对公司用户不可见）标签，使 Portfolio Manager 始终明确自己所查看内容的归属。能够访问该面板的用户角色为所有 Admin 角色，包括 Super Admin、PGM 以及对该公司有访问权限的 PM 角色。

在 MVP 阶段，两个视图均严格为只读（read-only）。Portfolio Manager 不能通过 UI 直接编辑或删除 Memory 条目。他们可以浏览并搜索其访问范围内任意公司的两类文件中的条目。

### 验收标准

- Memory Settings 面板可在 Portfolio Manager 聊天界面中由 Admin 角色访问。Admin 角色 = Super Admin、PGM、PM。
- 面板包含一个公司选择器下拉框（company selector dropdown），允许 Portfolio Manager 选择要查看的公司 Memory File，作用域严格限定于其访问范围内的公司。
- 面板针对所选公司同时展示 Company Memory File（Layer 1a）和 Portfolio Admin Memory File（Layer 1b），两者之间需有清晰、立即可辨的视觉区分。
- Company Memory File 区域附带标签，标明该内容对 Company Admin 可见（例如 "Shared with Company Admins"）。
- Portfolio Admin Memory File 区域附带标签，标明该内容仅供内部使用（例如 "Internal GS Memory, not visible to company users"）。
- 各区域中的 Memory 条目按倒序时间顺序（reverse chronological order）展示，并附带来源标签（company profile、chat extraction、document summary）和时间戳。
- 提供搜索功能，可同时搜索两个文件，或筛选至单一文件。
- 所有访问均为只读——MVP 阶段不提供条目的编辑或删除功能。
- PGM 与 PM 用户仅能访问其自身访问范围内公司的 Memory File——超出其访问范围的公司 Memory File 既不可见也不可访问。
- 面板顶部展示一段简短的通俗语言说明（例如："Company Memory is shared with company admins. Internal GS Memory is visible to GS team only."）。

### UX 设计要点

- Portfolio Manager 的 Memory Settings 面板应使切换不同公司变得便捷，可在面板顶部设置公司选择器下拉框。
- Layer 1a 与 Layer 1b 区域之间的视觉区分必须立即可辨——可考虑采用基于 Tab 的布局、配以不同颜色处理的不同区域标题，或使用清晰分隔线配合标签徽章（label badges）。
- Layer 1b 区域上的 "Internal - not visible to company users" 标签应保持持续可见。
- 以紧凑、易扫读的列表格式展示条目，每个条目可展开查看详情。
- 搜索功能应清晰指示当前正在搜索的文件，并提供筛选至单一文件或同时搜索两者的选项。
- 在面板顶部包含一段简短的通俗语言说明，描述 Memory File 的内容以及访问权限为只读（例如："This is what your AI assistant has learned about this company. You can browse and search these memories but cannot edit them directly."）。

### 依赖与备注

- 依赖：Portfolio Manager Core Chat UI（任务 1）作为 UI 外壳基础。
- MVP 阶段严格为只读，不支持编辑或删除条目。
- 数据访问严格按 PGM 与 PM 的访问范围进行作用域控制。

---

