---
asana_gid: 1214081544026464
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026464
asana_section: LG Backlog  / Backlog
asana_status: Prioritization In Progress 
asana_working_status: Not Started
asana_modified_at: 2026-05-11T03:06:12.985Z
lg_ticket: LG-1334
type: 
story_points: 
t_shirt: L
priority: 
completed: False
---

# AI Chatbot - Company User Financial & Benchmark Q&A

Business Requirements

With the core chat interface established in story https://app.asana.com/1/1170332106480422/task/1214057483533662, this story wires the company-side chatbot to the financial and benchmark data sources that power its responses. It enables company users to ask natural language questions about their company's financial performance and benchmark positioning and receive accurate, grounded answers drawn directly from Looking Glass data.
The agreed source of truth for all financial data is the normalization table, which contains normalized actuals, committed forecast, and system-generated forecast data for each company, and benchmark data. This covers all financial Q&A scenarios the chatbot needs to handle - historical performance questions, forecast questions, comparisons between actuals and forecast, and benchmarking questions such as percentile positioning.
The chatbot must retrieve relevant data from these sources and ground its responses in real company data. All data access is scoped strictly to the company the user belongs to - the chatbot cannot retrieve or reference financial or benchmark data from any other company. 
For MVP the chatbot is informational only - it answers questions and surfaces insights but does not take actions, update data, or generate formal reports.

Acceptance Criteria

    The chatbot can accurately answer natural language questions about the company's financial performance using data from the normalization table, including historical actuals, committed forecast, and system-generated forecast.
    The chatbot can accurately answer natural language questions about the company's benchmark positioning using data from the benchmark data layer, including percentile positioning relative to internal peers and external industry benchmarks.
    All financial and benchmark data retrieval is strictly scoped to the company the logged-in user belongs to - no cross-company data access is possible.
    The chatbot response clearly indicates when it cannot answer a question due to missing or unavailable data (e.g., no committed forecast exists for the company).
    The chatbot does not fabricate or hallucinate financial figures - responses are grounded in actual data from the normalization table and benchmark layer.
    Company profile metadata from Company Settings is also available as a data source to provide company context in responses.
    Response Formatting
        When the AI response contains structured data — financial metrics, benchmark comparisons, rankings, or time-series data — the response is rendered in a visual format rather than plain prose. Supported formats include tables and charts. The system selects the most appropriate format based on the data type: time-series data defaults to a line chart; side-by-side comparisons and rankings default to a table, and etc.
        When a response is rendered as a chart, a chart type toggle is displayed allowing the user to switch between contextually appropriate chart types (e.g., line chart, bar chart, pie chart) without re-querying the AI. Only chart types suitable for the current data are shown.
        For responses that contain multiple distinct sections or substantial content, the AI structures the response in a report-style format with a clear title, section headers, and organized content blocks, rather than a continuous block of prose text.
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices

UX Design Considerations

    Users should never need to think about which data source is powering a response - the data integration is entirely invisible. The experience from the user's perspective is simply asking a question and receiving a clear, accurate answer.
    When the chatbot draws on forecast data, responses should clearly distinguish between committed forecast and system-generated forecast so users understand the source of the projection.
    When the chatbot draws on benchmark data, responses should include the benchmark source and context (e.g., "Based on the KeyBanc 2024 SaaS Survey, your ARR growth rate is in the 45th percentile") so users understand what they are being compared against.
    If data is missing or incomplete, the chatbot's response should be helpful rather than just stating it cannot answer - where possible it should explain what data would be needed (e.g., "I don't see a committed forecast for your company yet. You can add one in the Financial Statements section.").
    https://preview--visual-link.lovable.app/?__lovable_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicDBNRFhwMWRlMWZra09sd3VSWm5OMTJMTXI4MiIsInByb2plY3RfaWQiOiI5MzE5YmRkOC1lYWI4LTQ1NGQtYTdjYi00NDk5ZGY4NjY5NmUiLCJhY2Nlc3NfdHlwZSI6InByb2plY3QiLCJpc3MiOiJsb3ZhYmxlLWFwaSIsInN1YiI6IjkzMTliZGQ4LWVhYjgtNDU0ZC1hN2NiLTQ0OTlkZjg2Njk2ZSIsImF1ZCI6WyJsb3ZhYmxlLWFwcCJdLCJleHAiOjE3NzkwNzMxNjYsIm5iZiI6MTc3ODQ2ODM2NiwiaWF0IjoxNzc4NDY4MzY2fQ.gW_tv-Ib9EQ2jWK1JTxIEHGZlfTBtBFNuR11T_OUpZRctsBSphncA-lPNIb7rfR04HE1MIQ1qid2Bbt1aEnX-WzifmIZUPuhZI_LTTOGKjuj59mLbNlyElUpMTx75el2QxAIZYhmnOXUav-KXgjTO6YoVYTNRJmNA2UbTl6G0beYA_peegcr_AUMWIP1dqdh0U5IbHNaA2z3vsrWsER6ZSmW-BPMk9fgGuk4LbvkielCUNwvZMVhKwMn-_RkpABY_YTcJ1MHUh7HKXrUuWvSfeWAH6vtccbGlFZc_pC_5KIKMMERmIlM9cNJneiis6AGbJhkggKuCwbPKFMlLHe_ds-rMR4c9Vl1u4JqxPdTtqT0uT0kZMYLeVT8vU_8KBBy8FBEAleBwydi-wP0vGeuybNm9j2tH8wwXAHIs_koSaX3rU4ToODgVnl-hLMY_OWagzffB40Fz7HzAL7effLmjJo_CDPEZhmYlGVa3cRBnRnZnPJX-1AM_hg03F6IlEkSu8WJJHuewKLR79OfIME1MZiIN8EEhA99Hfsn4r4qSqnrIi9SnFuhp3nDvu9MWzZrYRG0DwwMPeoaiz-kxznqqdF5-Aq8UBF9noNwyhb5Ti8vekG7ySns_rXfFdyWxo-MgIbYgc8x1GKpT4dC19pxaiclJOZt7cs3sxmf-CwVE_A

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

_本任务暂无业务相关评论（仅系统消息）。_

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 3. AI Chatbot - 公司用户财务与 Benchmark 问答（Company User Financial & Benchmark Q&A）

- **Asana ID**: 1214081544026464
- **LG 编号**: LG-1334
- **状态**: Prioritization In Progress（Working Status = Not Started，T-Shirt = L）
- **最近修改**: 2026-05-11
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026464

### 业务需求

在核心聊天界面已经搭建完成的基础上，本故事将公司端 chatbot 与驱动其回答的财务与 Benchmark 数据源进行对接。该能力使公司端用户能够以自然语言提问其公司财务表现与 Benchmark 定位相关的问题，并获得直接基于 Looking Glass 数据的、准确且有据可依的回答。

所有财务数据已统一约定以 Normalization Table 为唯一可信源（source of truth）：该表包含每家公司的标准化实际值（normalized actuals）、Committed Forecast（已承诺预测）、System-Generated Forecast（系统生成预测）数据，以及 Benchmark 数据。这覆盖了 chatbot 需要处理的全部财务问答场景——历史业绩问题、预测问题、实际值与预测值的对比，以及如百分位排名等 Benchmark 类问题。

Chatbot 必须从这些数据源中检索相关数据，并将其回答完全建立在公司真实数据之上。所有数据访问严格限定在用户所属的公司——chatbot 不可检索或引用任何其他公司的财务或 Benchmark 数据。

在 MVP 阶段，chatbot 仅作为信息性工具——它回答问题、揭示洞察，但不执行操作、不更新数据，也不生成正式报告。

### 验收标准

- Chatbot 能够基于 Normalization Table 中的数据，准确回答关于公司财务表现的自然语言问题，包括历史 actuals、Committed Forecast 与 System-Generated Forecast。
- Chatbot 能够基于 Benchmark 数据层中的数据，准确回答关于公司 Benchmark 定位的自然语言问题，包括相对于内部同行（internal peers）与外部行业 Benchmark 的百分位定位。
- 所有财务与 Benchmark 数据检索严格限定在登录用户所属的公司——不可能进行跨公司数据访问。
- 当因数据缺失或不可用而无法回答某个问题时（例如该公司尚未存在 Committed Forecast），chatbot 的回答必须清晰地予以说明。
- Chatbot 不得编造或臆造（hallucinate）财务数字——所有回答必须基于 Normalization Table 与 Benchmark 层中的真实数据。
- 同时将来自 Company Settings 的公司画像元数据作为可用的数据源，为回答提供公司上下文。

### UX 设计要点

- 用户永远不需要去思考某条回答是由哪个数据源驱动的——数据集成对用户而言完全不可见。从用户视角看，体验只是简单的"提问—得到清晰、准确的回答"。
- 当 chatbot 引用预测数据时，回答应清晰区分 Committed Forecast 与 System-Generated Forecast，让用户理解该预测的来源。
- 当 chatbot 引用 Benchmark 数据时，回答应包含 Benchmark 来源与上下文（例如 "Based on the KeyBanc 2024 SaaS Survey, your ARR growth rate is in the 45th percentile"，即"基于 KeyBanc 2024 SaaS Survey，你的 ARR 增长率位于第 45 百分位"），使用户清楚自己在与什么标准进行比较。
- 当数据缺失或不完整时，chatbot 的回答应做到"有帮助"而非仅仅声明无法回答——在可能的情况下应说明需要哪些数据（例如 "I don't see a committed forecast for your company yet. You can add one in the Financial Statements section."，即"我目前没有看到贵公司的 Committed Forecast。你可以在 Financial Statements 模块中添加一份。"）。

### 依赖与备注

- 数据源以 Normalization Table 为唯一可信源，覆盖 actuals、Committed Forecast、System-Generated Forecast 与 Benchmark 数据。
- Company Settings 中的公司画像元数据作为辅助上下文数据源。
- MVP 阶段 chatbot 仅做信息性问答，不执行写操作、不更新数据、不生成正式报告。
- 严格的公司级范围隔离（per-company scoping）：禁止任何形式的跨公司数据访问。
- 强约束：禁止 hallucinate 财务数字；缺失数据时给出友好且可指引下一步的回答。

