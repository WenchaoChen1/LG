---
gid: 1214057483533663
name: AI Chatbot - Portfolio Manager Core Chat UI
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533663
---

# AI Chatbot - Portfolio Manager Core Chat UI

Business Requirements

Looking Glass must provide a separate AI chat interface for portfolio manager and admin users that is entirely distinct from the company-side interface. This story covers the foundational UI shell and interaction design of the portfolio manager chatbot experience only. Data integration, knowledge base connectivity, memory file access, and chat history are covered in separate dependent stories.

The portfolio manager interface must be clearly differentiated from the company-side interface in its framing, suggested prompts, and overall orientation. Where the company-side interface is focused on a single company's performance, the portfolio manager interface is oriented around portfolio-wide visibility, cross-company insight, and the operating partner relationship with founders. The language and visual framing should reflect the always-on operating partner concept.

Acceptance Criteria

    A separate AI chat interface is accessible to Admin and Portfolio Manager roles in the admin portal, clearly distinct from the company-side interface in framing, layout, and suggested prompts.
    Users are taken directly into the chat experience.
    The welcome screen displays a portfolio-oriented headline and a set of suggested prompt cards reflecting real portfolio manager workflows (e.g., "Which companies are underperforming on burn rate?", "How is the portfolio trending on ARR growth?", "What does GS recommend for improving sales efficiency?").
    An input bar is prominently displayed for users to type free-form natural language questions.
    A "New Chat" button or control is clearly accessible at all times.
    A visible disclaimer is displayed indicating that responses are AI-generated and should be used for informational purposes.
    The interface is accessible on desktop and tablet.
    This story has no dependency on data integration stories - it is the UI shell only.

UX Design Considerations

    The welcome screen language must be clearly portfolio-oriented and must not reuse the framing from the company-side interface. Consider language aligned with the operating partner vision, such as "Your AI Operating Partner" as a headline.
    Suggested prompt cards should reflect the real workflow of a portfolio manager - identifying outliers, monitoring trends across companies, and understanding which companies need attention.
    Keep the interface clean and not complex at first launch - avoid overwhelming the user with controls.
