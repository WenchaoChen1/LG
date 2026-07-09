# 需求文档：公司记忆文件 Layer 1a 后端 —— 文档上传处理（PDF）

> Asana Task GID: 1215976758492506
> Task Name: Company Memory File Layer 1a Backend: Document Upload Processing - PDF

---

## 一、背景与业务描述

本需求覆盖公司侧（company-side）用户在聊天界面中上传的 PDF 文件（.pdf）后端处理流程，以及其在 Layer 1a 记忆文件中的存储实现。

PDF 文档以叙事性、散文式、自由格式的文本内容为主。创始人常见上传示例包括：

- 融资路演材料（Pitch Deck）
- 董事会会议纪要（Board Meeting Notes）
- 投资人更新（Investor Updates）
- 战略规划文档（Strategic Planning Documents）
- 公司概况或市场定位文档（Company Overview / Positioning Documents）

该文档格式适合 AI 驱动的摘要与上下文提取，其处理流水线核心是"读取、理解、并将文本内容提炼为有意义的记忆条目"。

---

## 二、业务逻辑闭环

当公司侧用户上传一份 PDF 文件时，后端须并行触发两个流程：

1. **RAG 索引（本故事覆盖范围）**
   - 对该文档的完整内容进行处理，并索引到 Layer 1a 中；
   - 使文档内容在当前及未来所有聊天会话中可被 AI 动态检索；
   - 用户提问相关问题时无需重新上传或重新引用原文档。

2. **记忆摘要（Memory Summarization）**
   - 由独立的共享故事（Asana Task 1215976758492505 —— Document Summary - Memory File 1a）负责实现，适用于所有支持的文件类型；
   - **本故事不覆盖摘要生成逻辑**。

**查询时（Query Time）的检索机制：**

- RAG 是主要检索机制；
- 用户提问涉及已上传文档时，查询直接命中 RAG 索引中的完整文档内容，**不经过摘要**；
- 记忆摘要仅作为辅助上下文，帮助 AI 定位相关文档，**不作为 RAG 检索的门控或过滤条件**。

---

## 三、范围界定

- **本故事仅覆盖**：PDF（.pdf）文件的后端处理；
- **Word（.docx）与纯文本（.txt）**：由 Asana Task 1215976758492504 覆盖；
- **Excel 与 CSV**：延后处理（Deferred）；
- **用户上传界面（UI）**：由 "Document Upload for Chat Analysis UI" 故事覆盖，不属本故事范围；
- 本故事仅覆盖**后端与数据架构**，无用户可见 UI 变更。

---

## 四、验收标准（Acceptance Criteria）

### 4.1 文件类型

- 仅处理 PDF 文件（.pdf）；Word、纯文本处理见对应关联故事，Excel、CSV 延后处理。

### 4.2 RAG 索引

- 当公司侧用户上传 PDF 时，文档的**完整内容**须被处理并索引到 Layer 1a；
- RAG 索引使完整文档内容在**当前及未来所有聊天会话**中对该公司可动态检索；
- RAG 索引须在上传后合理时间内完成 —— 目标为**典型文档大小 30 秒内**完成；
- **多页 PDF 文档须被完整索引** —— 在合理大小限制内，不因文档长度而截断或排除内容。

### 4.3 RAG 作为主要检索机制

- 查询时，检索直接经由 RAG 命中完整索引内容，**不经过摘要**；
- 记忆摘要仅作为辅助上下文与方向指引，不对 RAG 检索进行门控或过滤；
- 对上传 PDF 的查询，一律通过 RAG 索引直接回答，**无论摘要是否与查询相关**。

### 4.4 数据隔离

- RAG 索引及任何派生的记忆内容**严格限定**在原始上传公司的 Layer 1a 文件内；
- 文档内容在任何情况下**均不得**流入：
  - Layer 1b
  - GS Knowledge Base（Layer 2）
- 已处理的文档内容对平台上其他任何公司均不可访问。

### 4.5 错误处理与性能

- RAG 索引失败须记录日志以便排查，但**不得向终端用户暴露任何错误**；
- 文档处理失败时，聊天机器人须保持正常运行 —— 记忆更新失败不得阻塞聊天体验；
- 若文档过大、超出系统处理限制，须记录失败日志，并在聊天界面内向用户展示**优雅的内联提示消息**。

---

## 五、UX 设计说明

本故事为后端与数据架构故事，**无用户可见 UI 在范围内**。

---

## 六、关联故事

| 关联故事 | Asana Task GID | 关系 |
|---|---|---|
| Company Memory File Layer 1a Backend: Document Upload Processing - Word & Plain Text | 1215976758492504 | 平行故事（同层不同文件类型） |
| Document Summary - Memory File 1a | 1215976758492505 | 承担摘要生成，跨文件类型共享 |
| Document Upload for Chat Analysis UI | —— | 承担用户上传界面 |
