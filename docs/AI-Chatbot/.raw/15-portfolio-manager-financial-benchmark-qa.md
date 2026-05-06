---
gid: 1214081544026465
name: AI Chatbot - Portfolio Manager Financial & Benchmark Q&A
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026465
---

# AI Chatbot - Portfolio Manager Financial & Benchmark Q&A

Business Requirements

With the portfolio manager chat interface established, this story wires the portfolio manager chatbot to financial and benchmark data sources, enabling cross-company queries across all companies within the portfolio manager's access scope. This story must support queries that span multiple companies simultaneously.

The same data sources apply - the normalization table as the source of truth for financial actuals and forecasts, and the benchmark data layer for percentile positioning. Company profile metadata from Company Settings is also available as a data source for all companies within the portfolio manager's access scope. Implementation here must be capable of retrieving and synthesizing data across all companies the portfolio manager has access to in a single response. For example, a portfolio manager should be able to ask "which of my companies has the highest burn rate this month?" and receive a coherent answer that references multiple companies.

For MVP the chatbot is informational only - it answers questions and surfaces insights but does not take actions, update data, or generate formal reports.

Acceptance Criteria

    The chatbot can accurately answer natural language questions about financial performance for any individual company within the portfolio manager's access scope, using data from the normalization table.
    The chatbot can accurately answer cross-company natural language questions that span multiple companies simultaneously within the portfolio manager's access scope (e.g., "which company has the lowest gross margin?", "how many companies have a committed forecast?").
    The chatbot can accurately answer benchmark positioning questions for any individual company or across multiple companies within the portfolio manager's access scope.
    Portfolio manager data access is strictly enforced - the chatbot cannot retrieve data for companies outside the portfolio manager's access scope regardless of how a question is phrased.
    Company profile metadata from Company Settings is available as a data source for all companies within the portfolio manager's access scope.
    The chatbot does not fabricate or hallucinate financial figures - all responses are grounded in actual data.
    The chatbot clearly indicates when it cannot answer a question due to missing or unavailable data.

UX Design Considerations

    Cross-company responses should clearly attribute data to the relevant company by name so the portfolio manager can immediately understand which company a figure refers to.
    When the chatbot draws on forecast data, responses should distinguish between committed forecast and system-generated forecast.
    When the chatbot draws on benchmark data, responses should include benchmark source and context.
    If a portfolio manager asks about a company they do not have access to, the chatbot should respond gracefully - acknowledging the question but explaining access is not available, without revealing any data about that company.
    For cross-company queries that return a ranked or comparative result (e.g., "which company has the highest burn rate?"), consider formatting the response as a simple ranked list for readability rather than a paragraph.
