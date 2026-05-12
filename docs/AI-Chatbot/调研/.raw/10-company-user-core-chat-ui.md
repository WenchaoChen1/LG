---
gid: 1214057483533662
name: AI Chatbot - Company User Core Chat UI
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533662
---

# AI Chatbot - Company User Core Chat UI

Business Requirements

Looking Glass must provide a conversational AI chat interface accessible to company-side users, both Company User and Company Admin roles, that serves as the primary entry point for all AI chatbot interactions within the company-facing platform. This story covers the foundational UI shell and interaction design of the company-side chatbot experience only. Data integration, knowledge base connectivity, memory file access, and chat history are covered in separate dependent stories and are not in scope here.

The interface must be scoped strictly to the company context. Company-side users have no visibility into portfolio-level information, other companies, or any internal Golden Section notes or assessments. The overall tone and framing of the interface should reflect the vision of an always-on operating partner - approachable, intelligent, and immediately useful from the first interaction.

Acceptance Criteria

    A new "Ask AI" tab, icon, or equivalent entry point is accessible to Company User and Company Admin roles within the company's Looking Glass interface.
    Users are taken directly into the chat experience upon navigating to the AI
    The welcome screen displays a clear headline and a set of suggested prompt cards relevant to company performance to help users get started. Suggested prompts cover financial performance, benchmark positioning, and forecast-related questions.
    An input bar is prominently displayed for users to type free-form natural language questions.
    A "New Chat" button or control is clearly accessible at all times, allowing users to start a fresh conversation.
    The interface is scoped strictly to company-level context - no portfolio-level data, other company data, or internal GS content is visible or accessible to company-side users.
    A visible disclaimer is displayed indicating that responses are AI-generated and should be used for informational purposes.
    The interface is accessible on desktop and tablet.
    This story has no dependency on data integration stories - it is the UI shell only.

UX Design Considerations

    The interface should feel clean, modern, and approachable, not technical. The tone should reflect the always-on operating partner concept.
    Suggested prompt cards should be specific and immediately actionable, framed around real questions a founder would ask. Avoid generic placeholders like "Ask me anything."
    Keep the interface clean and not complex at first launch - avoid overwhelming the user with controls.
