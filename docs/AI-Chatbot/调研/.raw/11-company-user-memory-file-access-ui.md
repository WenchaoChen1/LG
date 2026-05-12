---
gid: 1214147930023561
name: AI Chatbot - Company User Memory File Access UI
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214147930023561
---

# AI Chatbot - Company User Memory File Access UI

Business Requirements

Company Admin users must be able to view what the AI chatbot has learned about their company through a Memory Settings panel accessible within the company-side chat interface. This panel surfaces the contents of the Company Memory File (Layer 1a) in a readable, searchable, read-only format, giving users transparency into the context the AI is using to personalize their experience.

The Memory Settings panel displays only Layer 1a content - the Company Memory File. The Portfolio Admin Memory File (Layer 1b) is never referenced, revealed, or accessible through any element of the company-side interface. Company User role does not have access to the Memory Settings panel at all - it is available to Company Admin only.

This is a read-only view in MVP. Users can browse and search memory entries but cannot edit, delete, or add entries directly. The memory file grows automatically through system-driven processes as established in the Company Memory File backend story.

Acceptance Criteria

    The Company Memory File is a single unified file per company. It is not structured as separate files per source type. Each entry within the file is tagged with a source label ("Company Profile," "Chat," or "Document") to indicate its origin. This tagging is for display and filtering purposes only — all entries live within one file.
    A Memory Settings panel is accessible to Company Admin users only within the company-side chat interface, accessible via a settings icon or secondary menu.
    The Memory Settings panel is an in-app online view within LG. There is no option to download or export the memory file to a user's local machine.
    If memory file entries are stored in markdown format on the backend, the UI must render the content in a clean, readable presentation
    Company User role does not have access to the Memory Settings panel.
    The panel displays only Company Memory File (Layer 1a) entries - no Layer 1b content is ever visible, referenced, or accessible.
    Entries are displayed in reverse chronological order with a source type label (e.g., "Company Profile," "Chat," "Document") and a timestamp. Source labels indicate origin only - no actual chat content is displayed.
    Entries displayed are distilled learnings and summaries extracted by the AI - not chat excerpts, conversation logs, or verbatim text from past conversations. Full conversation records are accessible only through the separate Chat History feature.
    A search function is available within the panel to locate specific memory entries.
    All access is read-only - no editing or deletion of entries is available in MVP.
    A brief plain-language explanation is displayed at the top of the panel (e.g., "These are the key things your AI assistant has learned about your company over time. Full conversation history is available separately.").

UX Design Considerations

    The Memory Settings panel should feel like a background feature the user can explore, accessible via a secondary menu or settings icon, not a prominent navigation element.
    Use a compact list format with expandable detail per entry. Source labels should be visually distinct - consider small color-coded badges or icons for "Company Profile," "Chat," and "Document."
    The panel must never display any label, section header, or UI element that hints at the existence of a separate internal GS memory layer.
