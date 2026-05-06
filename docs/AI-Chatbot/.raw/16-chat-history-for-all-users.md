---
gid: 1214081544026468
name: AI Chatbot - Chat History for All Users
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026468
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

UX Design Considerations

    The chat history panel should feel like a natural secondary feature - accessible but not dominant. A collapsible sidebar or slide-in panel works well and avoids cluttering the main chat area.
    Grouping by recency (Today, Yesterday, Last Week) is a familiar pattern from consumer chat applications and makes it easy for users to find recent conversations quickly.
    Each conversation entry in the history panel should display a short auto-generated title or the first few words of the opening message so the user can identify the topic at a glance without opening it.
    When a user returns to a past conversation, the prior messages should be clearly displayed in the chat thread before the new input bar, giving the user full context before they continue.
    The transition between starting a new chat and browsing history should be smooth - the "New Chat" button should always be clearly visible even when the history panel is open.
