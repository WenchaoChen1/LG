---
gid: 1214081544026464
name: AI Chatbot - Company User Financial & Benchmark Q&A
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026464
---

# AI Chatbot - Company User Financial & Benchmark Q&A

Business Requirements

With the core chat interface established, this story wires the company-side chatbot to the financial and benchmark data sources that power its responses. It enables company users to ask natural language questions about their company's financial performance and benchmark positioning and receive accurate, grounded answers drawn directly from Looking Glass data.

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

UX Design Considerations

    Users should never need to think about which data source is powering a response - the data integration is entirely invisible. The experience from the user's perspective is simply asking a question and receiving a clear, accurate answer.
    When the chatbot draws on forecast data, responses should clearly distinguish between committed forecast and system-generated forecast so users understand the source of the projection.
    When the chatbot draws on benchmark data, responses should include the benchmark source and context (e.g., "Based on the KeyBanc 2024 SaaS Survey, your ARR growth rate is in the 45th percentile") so users understand what they are being compared against.
    If data is missing or incomplete, the chatbot's response should be helpful rather than just stating it cannot answer - where possible it should explain what data would be needed (e.g., "I don't see a committed forecast for your company yet. You can add one in the Financial Statements section.").
