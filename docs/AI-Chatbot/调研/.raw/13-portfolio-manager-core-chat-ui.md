---
asana_gid: 1214057483533663
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533663
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:10:24.916Z
lg_ticket: LG-1335
type: 
story_points: 
t_shirt: L
priority: 
completed: False
---

# AI Chatbot - Portfolio Manager Core Chat UI

Business Requirements

Looking Glass must provide a separate AI chat interface for portfolio manager and admin users that is entirely distinct from the company-side interface. This story covers the foundational UI shell and interaction design of the portfolio manager chatbot experience only. Data integration, knowledge base connectivity, memory file access, and chat history are covered in separate dependent stories.
The portfolio manager interface must be clearly differentiated from the company-side interface in its framing, suggested prompts, and overall orientation. Where the company-side interface is focused on a single company's performance, the portfolio manager interface is oriented around portfolio-wide visibility, cross-company insight, and the operating partner relationship with founders. The language and visual framing should reflect the always-on operating partner concept.

Acceptance Criteria

    A separate AI chat interface is accessible to Admin and Portfolio Manager roles in the admin portal, clearly distinct from the company-side interface in framing, layout, and suggested prompts.
    Users are taken directly into the chat experience.
    The welcome screen displays a portfolio-oriented headline and a set of suggested prompt cards reflecting real portfolio manager workflows: (e.g., "Which companies are underperforming on burn rate?", "How is the portfolio trending on ARR growth?", "What does GS recommend for improving sales efficiency?").
        Headline: Always-on intelligence for your entire portfolio.
        Default Static Prompts
            Risks: Which companies are underperforming this month?
            Portfolio: How is the portfolio trending on ARR growth over the last quarter?
            Benchmarks: Which companies have the strongest benchmark positioning rightnow?
            Forecasts: Which companies are falling behind in their committed forecasts?
            Company: Which companies are falling behind in their committed forecasts?
            Strategy: What does GS recommend for improving sales efficiency?
    An input bar is prominently displayed for users to type free-form natural language questions.
    A "New Chat" button or control is clearly accessible at all times.
    A visible disclaimer is displayed indicating that responses are AI-generated and should be used for informational purposes.
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices

UX Design Considerations

    The welcome screen language must be clearly portfolio-oriented and must not reuse the framing from the company-side interface. Consider language aligned with the operating partner vision, such as "Your AI Operating Partner" as a headline.
    Suggested prompt cards should reflect the real workflow of a portfolio manager - identifying outliers, monitoring trends across companies, and understanding which companies need attention.
    Keep the interface clean and not complex at first launch - avoid overwhelming the user with controls. 
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

https://app.asana.com/app/asana/-/get_asset?asset_id=1214687052273907

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-05-07 · Liang Chunru**：需要更多细节：(1) Default Suggested Prompts——welcome 页 6 个卡片有 category label 和具体问题，需 finalize 默认 prompts；(2) Welcome Page Prompt 更新逻辑：用户长期使用后 prompt 是否要反映用法？什么驱动更新？何时触发？(3) In-Conversation Follow-Up Prompts：原型中 AI 回复后会显示 follow-up 建议，MVP 需要吗？多少个？
- **2026-05-07 · Karen Arnoldi**：(1) 默认 prompts 我和 Dougal review 后告诉你；(2) Prompt 更新是 post MVP——MVP memory file 刚开始积累，行为数据不足；(3) Follow-up prompts 也是 post MVP，属 engagement enhancement 而非基础能力。
- **2026-05-08 · Liang Chunru**：几个澄清：(1) Data Corrections (Normalization Table)：用户给出 correction（如'2025 年 7 月 ARR 实际是 X'）时，memory 只在该数据点被直接查询时应用 correction，不传播到 forecasting/live-computing/benchmark percentile 等下游；post-MVP 可考虑 AI 主动 prompt 用户更新 LG 数据；(2) Conflict Resolution（Memory vs Tenant KB）：surfaces all relevant info 而非偏向某一源（例如用户打开 Playbook toggle 但未指定 playbook 时）；(3) Conflict Resolution（Memory 内部）：新版本胜出。
- **2026-05-08 · Karen Arnoldi**：请 review 5/8 BR 会议——Dougal 详细讨论了 chatbot。默认 prompts 已加在附件中。(1) Data Corrections：不需要传播到下游，post MVP 再考虑；(2) Conflict Resolution KB vs Memory：surfaces all relevant；AI 应始终用公司 memory 过滤 KB 响应（generic playbook 适应该公司情境），这应影响 RAG query 结构；(3) Memory 内部：用最新。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 1. AI Chatbot - Portfolio Manager 核心聊天界面（Portfolio Manager Core Chat UI）

- **Asana ID**: 1214057483533663
- **LG 编号**: LG-1335
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = L）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533663

### 业务需求

Looking Glass 必须为 Portfolio Manager 和 Admin 角色提供一个独立的 AI 聊天界面，该界面与 Company 端界面完全隔离。本任务仅覆盖 Portfolio Manager 聊天体验的基础 UI 外壳与交互设计。数据集成、知识库连接、Memory File 访问以及聊天历史等内容由其他独立的依赖任务进行覆盖。

Portfolio Manager 界面必须在框架结构、建议提示语以及整体定位上与 Company 端界面有清晰的区分。Company 端界面聚焦于单一公司的业绩表现，而 Portfolio Manager 界面则围绕投资组合层面的可视化、跨公司洞察以及与创始人的运营合伙人（operating partner）关系来组织。语言风格和视觉框架应当体现"始终在线的运营合伙人（always-on operating partner）"这一核心理念。

### 验收标准

- 在 Admin Portal 中，Admin 与 Portfolio Manager 角色可访问一个独立的 AI 聊天界面，该界面在框架结构、布局以及建议提示语上与 Company 端界面有清晰区分。
- 用户登录后直接进入聊天体验。
- 欢迎页（welcome screen）展示一条以投资组合为导向的标题语，以及一组反映 Portfolio Manager 真实工作流的建议提示卡片（例如："哪些公司在 burn rate 上表现不佳？"、"投资组合在 ARR 增长方面的趋势如何？"、"GS 对提升销售效率有哪些建议？"）。
- 显著位置展示输入栏，供用户键入自由形式的自然语言问题。
- "New Chat" 按钮或控件始终清晰可见、可访问。
- 显示明显的免责声明（disclaimer），指出回复内容由 AI 生成，仅供信息参考使用。
- 界面在桌面端和平板端均可访问。
- 本任务不依赖任何数据集成类任务——仅为 UI 外壳。

### UX 设计要点

- 欢迎页的文案必须明确以投资组合为导向，不得复用 Company 端界面的框架。可考虑采用与 operating partner 愿景一致的标题文案，例如 "Your AI Operating Partner"。
- 建议提示卡片应当反映 Portfolio Manager 的真实工作流——识别异常表现的公司、跨公司监控趋势，以及理解哪些公司需要重点关注。
- 首次启动时保持界面简洁、避免复杂——不要用过多控件让用户产生压迫感。

### 依赖与备注

- 本任务仅为 UI 外壳层，不包含任何数据集成、知识库连接、Memory File 访问或聊天历史功能。
- 上述附加功能由其他依赖任务独立交付。

---

