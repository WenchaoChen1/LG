---
gid: 1214081544026466
name: AI Chatbot - Portfolio Manager Memory File Access UI
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214081544026466
---

# AI Chatbot - Portfolio Manager Memory File Access UI

Business Requirements

Portfolio managers must be able to view the memory files of all companies within their access scope through a Memory Settings panel in the portfolio manager chat interface. Unlike the company-side Memory Settings panel which shows only the Company Memory File, the portfolio manager panel provides visibility into both the Company Memory File (Layer 1a) and the Portfolio Admin Memory File (Layer 1b) for each company, with clear visual distinction between them.

The Company Memory File section shows context that company admins can also see - profile data, learnings from company-side chat sessions, and summaries from company-uploaded documents. A clear label indicates this content is visible to company admins. The Portfolio Admin Memory File section shows internal GS context added through portfolio manager activity. This section carries a clear "Internal, not visible to company users" label so portfolio managers always understand what they are looking at. User roles with access to this are all admin roles, including Super Admin, PGM, and PM roles that have access to that company.

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

UX Design Considerations

    The Memory Settings panel for portfolio managers should make it easy to switch between companies, perhaps a company selector dropdown at the top of the panel
    The visual distinction between Layer 1a and Layer 1b sections must be immediately obvious - consider a tab-based layout, different section headers with distinct color treatments, or clear dividers with label badges.
    The "Internal - not visible to company users" label on the Layer 1b section should be consistently visible
    Display entries in a compact, scannable list format with expandable detail per entry.
    The search function should clearly indicate which file(s) are being searched, with an option to filter to one file or search both.
    Include a brief plain-language explanation at the top of the panel describing what the memory file contains and that access is read-only (e.g., "This is what your AI assistant has learned about this company. You can browse and search these memories but cannot edit them directly.").
