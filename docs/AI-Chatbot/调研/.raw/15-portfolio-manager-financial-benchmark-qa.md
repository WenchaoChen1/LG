---
asana_gid: 1214081544026465
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026465
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:12:49.839Z
lg_ticket: LG-1337
type: 
story_points: 
t_shirt: L
priority: 
completed: False
---

# AI Chatbot - Portfolio Manager Financial & Benchmark Q&A

Business Requirements

With the portfolio manager chat interface established in story https://app.asana.com/1/1170332106480422/task/1214057483533663, this story wires the portfolio manager chatbot to financial and benchmark data sources, enabling cross-company queries across all companies within the portfolio manager's access scope. This story must support queries that span multiple companies simultaneously.
The same data sources apply - the normalization table as the source of truth for financial actuals and forecasts, and the benchmark data layer for percentile positioning. Company profile metadata from Company Settings is also available as a data source for all companies within the portfolio manager's access scope.  Implementation here must be capable of retrieving and synthesizing data across all companies the portfolio manager has access to in a single response. For example, a portfolio manager should be able to ask "which of my companies has the highest burn rate this month?" and receive a coherent answer that references multiple companies.
For MVP the chatbot is informational only - it answers questions and surfaces insights but does not take actions, update data, or generate formal reports.

Acceptance Criteria

    The chatbot can accurately answer natural language questions about financial performance for any individual company within the portfolio manager's access scope, using data from the normalization table.
    The chatbot can accurately answer cross-company natural language questions that span multiple companies simultaneously within the portfolio manager's access scope (e.g., "which company has the lowest gross margin?", "how many companies have a committed forecast?").
    The chatbot can accurately answer benchmark positioning questions for any individual company or across multiple companies within the portfolio manager's access scope.
    Portfolio manager data access is strictly enforced - the chatbot cannot retrieve data for companies outside the portfolio manager's access scope regardless of how a question is phrased.
    Company profile metadata from Company Settings is available as a data source for all companies within the portfolio manager's access scope.
    The chatbot does not fabricate or hallucinate financial figures - all responses are grounded in actual data.
    The chatbot clearly indicates when it cannot answer a question due to missing or unavailable data.
    Response Formatting
        When the AI response contains structured data — financial metrics, benchmark comparisons, rankings, or time-series data — the response is rendered in a visual format rather than plain prose. Supported formats include tables and charts. The system selects the most appropriate format based on the data type: time-series data defaults to a line chart; side-by-side comparisons and rankings default to a table, and etc.
        When a response is rendered as a chart, a chart type toggle is displayed allowing the user to switch between contextually appropriate chart types (e.g., line chart, bar chart, pie chart) without re-querying the AI. Only chart types suitable for the current data are shown.
        For responses that contain multiple distinct sections or substantial content, the AI structures the response in a report-style format with a clear title, section headers, and organized content blocks, rather than a continuous block of prose text.
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices


UX Design Considerations

    Cross-company responses should clearly attribute data to the relevant company by name so the portfolio manager can immediately understand which company a figure refers to.
    When the chatbot draws on forecast data, responses should distinguish between committed forecast and system-generated forecast.
    When the chatbot draws on benchmark data, responses should include benchmark source and context.
    If a portfolio manager asks about a company they do not have access to, the chatbot should respond gracefully - acknowledging the question but explaining access is not available, without revealing any data about that company.
    For cross-company queries that return a ranked or comparative result (e.g., "which company has the highest burn rate?"), consider formatting the response as a simple ranked list for readability rather than a paragraph.
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

_本任务暂无业务相关评论（仅系统消息）。_

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 3. AI Chatbot - Portfolio Manager 财务与 Benchmark 问答（Portfolio Manager Financial & Benchmark Q&A）

- **Asana ID**: 1214081544026465
- **LG 编号**: LG-1337
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = L）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026465

### 业务需求

在 Portfolio Manager 聊天界面建立后，本任务将 Portfolio Manager Chatbot 接入财务数据源与 Benchmark 数据源，使其能够对 Portfolio Manager 访问范围内的所有公司进行跨公司查询。本任务必须支持同时跨多家公司的查询。

数据源沿用相同的体系——以 Normalization Table 作为财务实际值（actuals）与预测值（forecasts）的唯一可信来源（source of truth），以 Benchmark 数据层作为百分位定位（percentile positioning）的依据。Company Settings 中的公司 Profile 元数据（profile metadata）也作为数据源对 Portfolio Manager 访问范围内的所有公司开放。本次实现必须能够在单次响应中检索并综合 Portfolio Manager 有权访问的所有公司数据。例如，Portfolio Manager 应能够提问："which of my companies has the highest burn rate this month?"（本月我哪家公司 burn rate 最高？），并收到一个引用多家公司、连贯一致的答复。

在 MVP 阶段，Chatbot 仅作为信息工具（informational only）——它回答问题并呈现洞察，但不执行任何操作、不更新数据，也不生成正式报告。

### 验收标准

- Chatbot 能够准确回答关于 Portfolio Manager 访问范围内任一单家公司财务表现的自然语言问题，数据来源为 Normalization Table。
- Chatbot 能够准确回答跨公司的自然语言问题，覆盖 Portfolio Manager 访问范围内同时涉及多家公司的查询（例如："哪家公司的 gross margin 最低？"、"有多少公司提交了 committed forecast？"）。
- Chatbot 能够准确回答 Portfolio Manager 访问范围内任一单家公司或跨多家公司的 Benchmark 定位问题。
- Portfolio Manager 的数据访问范围被严格强制执行——无论问题如何措辞，Chatbot 都不能检索 Portfolio Manager 访问范围之外公司的任何数据。
- Company Settings 中的公司 Profile 元数据作为数据源对 Portfolio Manager 访问范围内的所有公司开放。
- Chatbot 不会编造（fabricate）或臆造（hallucinate）财务数字——所有回复均基于真实数据。
- 当因数据缺失或不可用导致 Chatbot 无法回答问题时，必须清晰说明这一情况。

### UX 设计要点

- 跨公司响应应清晰地按公司名称归属数据，使 Portfolio Manager 能立即理解某个数字所对应的公司。
- 当 Chatbot 引用预测数据时，回复应区分 committed forecast 与 system-generated forecast。
- 当 Chatbot 引用 Benchmark 数据时，回复应包含 Benchmark 来源与上下文。
- 如果 Portfolio Manager 询问其无访问权限的公司，Chatbot 应妥善地回应——确认收到该问题，但说明无访问权限，且不能透露该公司的任何数据。
- 对于返回排名或对比结果的跨公司查询（例如："哪家公司的 burn rate 最高？"），可考虑将响应格式化为简洁的排名列表以提升可读性，而不是大段段落文字。

### 依赖与备注

- 依赖：Portfolio Manager Core Chat UI（任务 1）作为 UI 外壳。
- 数据源：Normalization Table（财务实际值与预测值）、Benchmark 数据层（百分位定位）、Company Settings（公司 Profile 元数据）。
- MVP 范围：仅信息性问答；不执行操作、不更新数据、不生成正式报告。

---

