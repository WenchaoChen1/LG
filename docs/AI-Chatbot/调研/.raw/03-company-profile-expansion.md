---
asana_gid: 1214057483533667
asana_url: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533667
asana_section: LG Backlog  / Prioritized
asana_status: Product Review
asana_working_status: In Progress
asana_modified_at: 2026-05-07T07:09:52.730Z
lg_ticket: LG-1327
type: User Story
story_points: 2
t_shirt: M
priority: High
completed: False
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
    Feature should be mobile responsive so that it is fully functional on both desktop and mobile devices

UX Design Considerations

    Frame the expanded description field with a label or helper text that connects it to the AI chatbot: something like "Help your AI assistant understand your business" makes the purpose immediately clear to users.
    Include industry in helper text or as secondary helper text
    For the expanded description field, consider showing a character count indicator so users know how much space they have.
    https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=12659-18116&t=KHCzpckmM4pYfdQF-1
    Prototype

https://app.asana.com/app/asana/-/get_asset?asset_id=1214224205484917

---

## Asana 业务讨论（Comments）

> 仅保留业务相关讨论。系统消息（assignee/status 变更等）已过滤。

- **2026-04-30 · Liang Chunru**：Prototype 截图已加到 ticket。一旦 Shue 拿到 edit access 会提供 Figma 设计链接。

---

## 中文版需求整理

> 内容与 `part-*.md` 中同章节保持一致；如有冲突，以 `part-*.md` 为准。

## 3. 公司档案扩展 —— 增强描述（Company Profile Expansion - Enhanced Description）

- **Asana ID**: 1214057483533667
- **LG 编号**: LG-1327
- **状态**: Product Review（Working Status = In Progress，Story Points = 2，T-Shirt = M，Priority = High）
- **最近修改**: 2026-05-07
- **Asana 链接**: https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214057483533667

### 业务需求

AI 聊天机器人的公司 Memory File（Layer 1，公司记忆文件）会以 Looking Glass 中现有的公司元数据进行初始化。为确保聊天机器人从第一天起就对每个公司具备有意义的基础理解，这些元数据应尽可能完整且有用。Looking Glass 已在 Company Settings 中记录了公司的 type 与 stage（公司类型与阶段），因此这两个字段可直接进入 Memory File，无需额外工作。

但是，现有的公司 description 字段不足以使用 —— 该字段在内容范围与字符长度上都受限，过于浅薄，无法让聊天机器人真正了解公司在做什么。由于目前不存在 industry（行业）字段（行业能提供更具体的市场上下文），因此应将 industry 添加到 description 字段的默认提示文本中。一段扩展后的 description 加上明确的 industry 字段，可在每次对话中为聊天机器人提供更加丰富的起点，避免用户每次都需要从零开始重新解释自身业务背景。

本 story 的内容是：在 Company Settings 中新增 industry 字段，并扩大 description 字段的字符上限及默认指引文案以将 industry 纳入。这些信息会在聊天机器人初始化时直接进入公司的 Layer 1 Memory File，并在用户每次修改时同步更新到 Memory File 中。

### 验收标准

- 现有 Company Overview 字段的默认提示文案需更新，明确提及包含公司 industry
- 现有公司 description 字段的字符上限需大幅提升，足以容纳一段有意义、多句的公司描述（具体字符上限 TBD —— 需开发评估输入）
- 在 description 字段中增加辅助说明文本或占位符（placeholder），引导用户填写要点（例如："Describe what your company does, who your customers are, and what makes you unique."（描述你的公司做什么、客户是谁，以及独特之处是什么））
- 当 AI 聊天机器人首次为该公司初始化时，更新后的扩展 description 自动写入该公司的 Layer 1 Memory File
- 当用户更新该字段时，Memory File 会同步更新以反映变更

### UX 设计要点

- 通过标签或辅助文本将扩展后的 description 字段与 AI 聊天机器人关联起来，例如使用 "Help your AI assistant understand your business"（帮助你的 AI 助手了解你的业务）这样的措辞，使用途对用户一目了然
- 在辅助文本或二级辅助文本中包含 industry 提示
- 对扩展后的 description 字段，建议显示字符计数指示器，让用户了解还剩多少可用空间
- Prototype（原型）：https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=12659-18116&t=KHCzpckmM4pYfdQF-1
- Asset：https://app.asana.com/app/asana/-/get_asset?asset_id=1214224205484917

### 依赖与备注

- 该 story 直接喂入 Layer 1 Memory File 初始化流程
- 字符上限的最终值需开发团队评估后确定

---

