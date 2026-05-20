---
asana_gid: 1214081544026468
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026468
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:22:54.553Z
lg_ticket: LG-1339
type: 
story_points: 
t_shirt: M
priority: 
completed: False
---

# AI Chatbot - Chat History for All Users

Business Requirements

The AI chatbot must preserve and display the history of past conversations for all user roles - Company User, Company Admin, Portfolio users. Chat history allows users to return to previous conversations, review past responses, and continue a prior line of questioning without having to repeat context. It is a separate and distinct feature from the memory file - chat history is the full, readable log of past conversations, while the memory file is the distilled intelligence the AI extracts from those conversations to improve future responses.
Each user's chat history is scoped to their own conversations only. A Company Admin cannot see the chat history of another user within the same company, and a portfolio user cannot see the chat history of any company-side user. Chat history is entirely personal to the individual user who had the conversation.
For MVP, chat history is read-only - users can browse and return to previous conversations but cannot edit, rename, or delete them. The ability to manage chat history (renaming conversations, deleting entries) is post-MVP scope.

Acceptance Criteria

    Chat history is for all user roles: Company User, Company Admin, Portfolio users (PGM and PM)
    Past conversations are accessible through a chat history panel within the chatbot interface, available in both the company-side and portfolio manager interfaces.
    Conversations in the chat history panel are grouped by recency (e.g., Today, Yesterday, Last Week, Older).
    Users can click on any past conversation in the chat history panel to open and review the full conversation.
    Users can continue a past conversation by selecting it from the chat history panel and sending a new message - the AI retains the context of the prior conversation when continuing.
    Chat history is scoped strictly to the individual logged-in user - users cannot view the chat history of any other user regardless of role.
    The chat history panel is accessible from the main chat interface in both the company-side and portfolio manager interfaces via a clearly visible control (e.g., a history icon or sidebar toggle).
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices

UX Design Considerations

    The chat history panel should feel like a natural secondary feature - accessible but not dominant. A collapsible sidebar or slide-in panel works well and avoids cluttering the main chat area.
    Grouping by recency (Today, Yesterday, Last Week) is a familiar pattern from consumer chat applications and makes it easy for users to find recent conversations quickly.
    Each conversation entry in the history panel should display a short auto-generated title or the first few words of the opening message so the user can identify the topic at a glance without opening it.
    When a user returns to a past conversation, the prior messages should be clearly displayed in the chat thread before the new input bar, giving the user full context before they continue.
    The transition between starting a new chat and browsing history should be smooth - the "New Chat" button should always be clearly visible even when the history panel is open.
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

https://app.asana.com/app/asana/-/get_asset?asset_id=1214687052273917

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

_本任务暂无业务相关评论（仅系统消息）。_

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 4. AI Chatbot - 所有用户的聊天历史（Chat History for All Users）

- **Asana ID**: 1214081544026468
- **LG 编号**: LG-1339
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = M）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026468

### 业务需求

AI Chatbot 必须为所有用户角色——Company User、Company Admin、Portfolio 用户——保存并展示历史会话记录。聊天历史允许用户回到先前的对话、回顾过往的回复，并继续此前的提问线索而无需重复上下文。它是与 Memory File 完全独立、彼此区分的功能——聊天历史是过往对话的完整、可读日志（full, readable log），而 Memory File 是 AI 从这些对话中提炼出来、用于改善未来回复的精炼智能（distilled intelligence）。

每位用户的聊天历史的作用域仅限于其本人的对话。Company Admin 不能查看同一公司内其他用户的聊天历史，Portfolio 用户也不能查看任何 Company 端用户的聊天历史。聊天历史完全归属于产生该对话的个人用户。

在 MVP 阶段，聊天历史为只读（read-only）——用户可浏览并回到过往对话，但不能编辑、重命名或删除。管理聊天历史的能力（重命名对话、删除条目）属于 post-MVP 范围。

### 验收标准

- 聊天历史适用于所有用户角色：Company User、Company Admin、Portfolio 用户（PGM 与 PM）。
- 过往对话可通过 Chatbot 界面内的聊天历史面板访问，该面板在 Company 端与 Portfolio Manager 端界面均可用。
- 聊天历史面板中的对话按近期程度分组（例如：Today、Yesterday、Last Week、Older）。
- 用户可点击聊天历史面板中的任意过往对话，打开并查看完整对话内容。
- 用户可通过从聊天历史面板中选择某次对话并发送新消息来继续过往对话——继续对话时 AI 保留先前对话的上下文。
- 聊天历史的作用域严格限于当前登录的个人用户——无论角色如何，用户都不能查看其他任何用户的聊天历史。
- 聊天历史面板可通过清晰可见的控件（例如：history 图标或 sidebar 切换按钮）从主聊天界面访问，Company 端和 Portfolio Manager 端界面均如此。

### UX 设计要点

- 聊天历史面板应给人以自然的辅助功能（secondary feature）感——可访问但不喧宾夺主。可折叠的 sidebar 或滑入式面板（slide-in panel）效果较好，能避免对主聊天区造成视觉干扰。
- 按近期程度分组（Today、Yesterday、Last Week）是消费级聊天应用中常见的模式，便于用户快速找到近期对话。
- 历史面板中的每个对话条目应展示一段自动生成的简短标题，或者展示开场消息的前几个词，使用户无需打开即可一眼识别话题。
- 当用户回到过往对话时，先前的消息应在新的输入栏之前清晰展示在对话线程中，让用户在继续提问之前获得完整上下文。
- 在"开始新对话"与"浏览历史"之间的过渡应顺滑——即使在历史面板打开时，"New Chat" 按钮也应始终保持清晰可见。

### 依赖与备注

- 适用范围：Company 端聊天界面和 Portfolio Manager 端聊天界面。
- MVP 阶段为只读——不支持重命名或删除对话。
- 重命名、删除等管理能力属于 post-MVP 范围。

---

