# AI Chatbot - Document Upload for Chat Analysis（Company Portal）需求文档

## 一、需求背景

公司端用户须能够在公司端 AI 聊天机器人界面中直接上传文档，为对话提供额外上下文。这使用户可以将尚未录入 Looking Glass 的信息（例如尚未录入系统的财务电子表格，或希望聊天机器人总结/提取要点的会议记录）分享给聊天机器人。

上传的文档不会导入 Looking Glass，也不会进入财务数据管道。文档上传后：
- 文档通过 RAG（检索增强生成）处理并索引，其完整内容在当前及所有未来的会话中都可动态检索。
- 系统会自动生成该文档中关键、与公司相关学习要点的高层摘要，并保存到对应的记忆文件层，使从文档中学到的最重要内容作为上下文持续存在，即使未来会话不显式引用原始文件也可复用。记忆摘要的具体处理由配套后端 story（`task/1215976758492505`）负责。

文档摘要写入的记忆层由上传用户的角色决定。公司端上传的公司归属始终是隐式的——公司端用户始终位于自己公司的上下文中，无需确认提示。所有上传的文档严格限定在其上传所在的公司范围内，永远不会被其他公司访问；任何情况下都不会流入 GS Knowledge Base（Layer 2）。

MVP 阶段支持的文件类型覆盖主要用例：PDF 与 Word 文档（用于报告与叙述性内容），纯文本文件（`.txt`，用于诸如 Fireflies 导出的会议记录）。Excel 与 CSV 的支持推迟到 MVP 后。展示公司上下文中所有已上传文件的 Knowledge Base 面板由另一 story（`task/1216219449500194`）负责。

## 二、适用范围

- 目标端：Company Portal（公司门户）。
- 用户角色：Company User、Company Admin。
- 平台：桌面端与移动端，均需完整可用。

## 三、功能需求

### 1. 上传功能（Upload Functionality）

- 用户可通过聊天输入栏中的附件按钮直接上传文件。
- MVP 支持的文件类型：PDF、Word（`.docx`）、纯文本（`.txt`）。Excel 与 CSV 推迟至 MVP 后。
- 文件大小限制：单文件 20MB；整批 100MB。
- 上传的文档通过 RAG 处理并索引，其完整内容在当前及未来所有会话中均可动态检索。
- 聊天机器人在上传后立即以及未来的会话中，均能准确回答关于已上传文档内容的问题。
- 用户可在单个会话中上传多个文件。
- 当用户仅上传文档而不附带问题时，AI 主动提示：「I've reviewed the document. Would you like a summary, or do you have a specific question about it?」
- 功能须在桌面端与移动端均完整可用。

### 2. 文件 Chip 状态与操作（File Chip States & Actions）

- 每个已上传文件以 chip 形式展示，显示文件名、文件大小和当前状态。
- 状态流转：Uploading → Parsing → Ready。文件只有进入 Ready 状态后，才可用于提问。
- 上传/解析失败时，chip 显示简明失败状态（例如「Upload failed」/「Parsing failed」）；完整失败原因按下方「上传错误处理」规则展示。
- 每个 chip 都有移除（×）控件，鼠标悬停时显示。文件一旦进入上传队列，无论其状态如何都可移除：
  - 移除会将该文件从上传集合中剔除；
  - 若该文件仍在 Uploading 或 Parsing 状态，正在进行的处理将被取消。
- 在触摸/移动端（无悬停能力）上，移除（×）控件始终可见。
- 当已上传文件的 chips 超过输入区可视宽度时，出现左右导航箭头（‹ ›）以水平滚动。列表处于起始位置时左箭头禁用，处于末尾位置时右箭头禁用。

### 3. Send 按钮在有附件时的行为

- 只要还有任何文件处于 Uploading 或 Parsing（尚未 Ready）状态，Send 按钮即为禁用。
- 处于 Failed 状态的文件不会影响 Send 按钮——失败文件不阻塞发送。
- 一旦不存在仍在 Uploading 或 Parsing 的文件，Send 按钮按常规启用规则处理。
- 发送时，仅附加处于 Ready 状态的文件；处于 Failed 的文件自动被排除并从上传集合中移除。

### 4. 上传错误处理（Upload Error Handling）

- 错误展示位置按发生阶段区分：
  - 在文件进入上传队列前发生的错误（例如选择时因大小或不支持的类型被拒绝），以顶部内嵌横幅（inline banner）方式显示在聊天区域顶部，并显示完整原因；
  - 在文件进入队列后发生的错误，在该文件的 chip 上以简明失败状态显示，完整原因通过 hover/tooltip 呈现。
- 处理的错误类型与文案：
  - 单文件超大：「The uploaded file exceeds the maximum file size limit of 20MB. Please reduce the file size and upload again.」
  - 不支持的文件类型：「Failed to upload {File name}. Unsupported file type. Supported types: PDF, Word (.docx), and plain text (.txt).」
  - 文件损坏：「Failed to upload {File name}. File is corrupted.」
  - 合计大小超限：「Failed to upload {File name}. The combined size of your files exceeds the 100MB limit.」
  - 重复文件名：「Failed to upload {File name}. A file with this name already exists.」
  - 通用/其他失败：「Failed to upload {File name}.」

### 5. 记忆层路由（Memory Layer Routing）

- 公司端用户（Company User / Company Admin）上传的文档，被处理后存储到该公司的 Layer 1a 记忆文件。
- 已上传文档在任何情况下都不会流入 GS Knowledge Base（Layer 2）。
- 无论存放于哪一层，已上传文档永远不会被其他公司访问。
- 记忆层路由由系统基于上传用户角色自动执行、强制生效。

### 6. 文件处理模型（Knowledge Base、RAG 与 Memory 的关系）

- 通过聊天上传的所有文件都会被加入 Knowledge Base 并进行 RAG 索引。记忆摘要（Memory summarization）是独立且有条件的处理。
- 两个门槛——「公司归属」与「符合条件的公司相关内容」——只决定是否创建记忆摘要条目；不影响文件是否被加入 Knowledge Base 或进行 RAG 索引。
- 如果文件不包含值得存储的公司相关内容，则不生成记忆摘要；但该文件仍会被加入 Knowledge Base 并保持在聊天中可通过 RAG 检索。
- 可见性由权限决定，而非文件内容：RAG 检索权限等价于 Knowledge Base 可见性——能在 Knowledge Base 中看到某个文件的用户，才能在其对话中通过 RAG 检索到它；其他人则不能。

