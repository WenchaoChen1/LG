---
gid: 1214057483533667
name: Company Profile Expansion - Enhanced Description
completed: false
permalink_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533667
---

# Company Profile Expansion - Enhanced Description

Business Requirements

The AI chatbot's company memory file (Layer 1) is initialized with the company's existing metadata from Looking Glass. To ensure the chatbot has a meaningful baseline understanding of each company from day one, that metadata needs to be as complete and useful as possible. Looking Glass already captures company type and stage in Company Settings, so those fields are available to the memory file without any additional work.

However, the existing company description field is insufficient - it is limited in scope and character length, making it too shallow to give the chatbot a genuinely useful picture of what the company does. Since there is no industry field, which provides more specific market context, this should be added to the default prompt text in the description field. Together, an expanded description and a specific industry designation give the chatbot a much richer starting point for every conversation, reducing the need for users to re-explain their business context from scratch.

This story adds an industry field to Company Settings and expands the character limit and default guidance to include industry for the company description field. This will feed directly into the company's Layer 1 memory file at chatbot initialization and are updated in the memory file whenever the user makes changes.

Acceptance Criteria

    The existing Company Overview field default prompt is updated to specifically mention the inclusion of company industry
    The existing company description field is expanded to support a significantly higher character limit, sufficient to allow a meaningful multi-sentence description of the company. (Character limit TBD - need dev input)
    Additional helper text or a placeholder is added to the description field to guide users on what to include (e.g., "Describe what your company does, who your customers are, and what makes you unique.").
    The updated and expanded company description are automatically included in the company's Layer 1 memory file when the AI chatbot is first initialized for that company.
    When the field is updated by a user, the memory file is updated to reflect the change.

UX Design Considerations

    Frame the expanded description field with a label or helper text that connects it to the AI chatbot: something like "Help your AI assistant understand your business" makes the purpose immediately clear to users.
    Include industry in helper text or as secondary helper text
    For the expanded description field, consider showing a character count indicator so users know how much space they have.
    Prototype: https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=12659-18116&t=KHCzpckmM4pYfdQF-1
    Asset: https://app.asana.com/app/asana/-/get_asset?asset_id=1214224205484917
