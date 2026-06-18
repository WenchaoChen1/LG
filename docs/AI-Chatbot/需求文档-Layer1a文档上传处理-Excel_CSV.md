# 需求文档：Company Memory File Layer 1a 后端 — 文档上传处理（Excel & CSV）

## 一、业务背景与目标

本故事覆盖 **Company 端用户在聊天界面中上传的结构化数据文件格式** 的后端处理，具体为：
- Excel 文件（.xlsx、.xls）
- CSV 文件（.csv）

并将其内容存储到 **Layer 1a 记忆文件** 中。

由于此类文档包含 **结构化的表格数据**，必须采用 **针对表格型财务与运营数据的读取、解释与摘要做优化** 的处理方式，而 **不是** 像对叙述性文本那样从中提取语义。

### 典型使用场景

在 AI Chatbot 场景中，此类文件最常见的使用情境包括：
- 尚未录入 LG 的财务表（historical actuals、forecasts、operating models）；
- KPI 跟踪表；
- Pipeline 与营收数据导出；
- 创始人希望 AI 能引用与分析的其他运营数据。

由于这些文件常包含 **敏感的财务与运营数据**，处理流水线必须 **正确识别数据结构、理解其含义、提取有意义的上下文**，**不得错误解读 列头、合并单元格或非标准电子表格布局**。

### 上传时的两个并行流程

当 Company 端用户上传 Excel 或 CSV 时，系统须并行执行：

1. **RAG 索引（RAG Indexing）**
   - 文件完整内容被处理并索引到 **Layer 1a 向量库**；
   - 在当前及未来所有聊天会话中可动态查询。

2. **记忆摘要（Memory Summarization）**
   - 系统自动从文件内容中生成关于公司相关学习内容的高层级摘要；
   - 摘要作为一条 Layer 1a 记忆条目保存。

### 查询时的检索机制

- **RAG 是主要检索机制**；
- 查询直接命中 RAG 索引中的完整文件内容，**不命中摘要**；
- 摘要仅作为辅助上下文，帮助 AI 定位相关文档与构成回答；**不会对 RAG 检索做门控或过滤**；
- 原因：摘要无法覆盖文件全部内容；若必须先命中摘要再深入文件，会导致未捕获内容静默不可访问；
- 所有检索均直接经过 RAG，摘要在其旁提供附加上下文。

### 结构化数据摘要的范围（重要约束）

对结构化数据文件的记忆摘要 **被有意约束（intentionally constrained）**：
- 摘要只 **记录文件包含什么（what the file contains）**，**不分析其含义（not what it means analytically）**；
- 对 Excel / CSV：
  - 摘要捕获 **文件覆盖的时间区间（time period covered，如适用）**；
  - 摘要捕获 **数据类别或指标（data categories or metrics present）**；
  - 摘要捕获 **帮助 AI 理解"该文件是什么、何时应被检索"的高层级结构性上下文**。
- **Trend analysis、cost structure analysis 及任何分析性派生（analytical derivations）**，**显式不在摘要阶段执行**；
- 这些分析性工作 **发生在查询时**——用户提问时 AI 通过 RAG 检索相关数据进行推理。

此约束让摘要范围保持 **干净、一致、可实现**。

### 非财务文件处理

- Excel 和 CSV 上传 **不限于财务文件**；
- 非财务结构化文件（如客户名单、产品目录、KPI 跟踪表、Pipeline 数据）**同样被索引与摘要**；
- 理由：**AI 对公司的理解应通过用户选择分享的任何内容得到丰富**；
- 对非财务文件：**同样适用 RAG 为主的检索模型**，摘要也只 **记录文件内容、不做分析**。

### 与财务数据管线的隔离

- 通过 AI Chatbot 界面上传的文档 **不会导入 Looking Glass，也不会被财务数据管线处理**；
- 它们 **仅用于通过记忆文件丰富 AI 对该公司的上下文理解**；
- 创始人通过 Chatbot 上传财务表 = **请 AI 学习它**，**不是请 LG 将其作为财务数据摄取**。

### 数据隔离

- 上传的 Excel / CSV 衍生的所有内容 **严格限定在源公司的 Layer 1a 记忆文件**；
- 在 **任何情况下** 都 **不会** 流入 Layer 1b、GS Knowledge Base（Layer 2）或 LG 财务数据管线。

---

## 二、功能需求（Acceptance Criteria）

### 2.1 支持的文件类型（Supported File Types）
- 本故事仅覆盖以下文件类型的处理：
  - Excel（.xlsx、.xls）
  - CSV（.csv）
- **PDF（.pdf）、Word（.docx）和纯文本（.txt）由另一独立 Story 覆盖**，不在本范围内。

### 2.2 RAG 索引（RAG Indexing）
- 当 Company 端用户上传 Excel 或 CSV 时，**文件完整内容** 被处理并索引到 **Layer 1a**；
- RAG 索引使该公司在 **当前会话及未来所有会话** 中均可动态查询表格数据；
- RAG 索引需 **正确处理表格结构**，**保留行/列表头与对应值之间的关系**，使 AI 能准确回答如 **"what was revenue in March?"** 这样的问题；
- **多 Sheet 的 Excel 文件需完整索引**——**工作簿中所有 Sheet 都要处理**，不仅是第一个 Sheet；
- 索引流水线需 **优雅处理常见电子表格格式差异**：
  - 合并单元格（merged cells）；
  - 用作视觉分隔的空白行（blank rows used as visual separators）；
  - 小计与合计行（subtotal and total rows）；
  - 非标准的表头放置（non-standard header placements）。

### 2.3 RAG 作为主要检索机制（RAG as Primary Retrieval Mechanism）
- 查询时，**检索直接通过 RAG 命中索引中的完整文件内容**，**不经过摘要**；
- 记忆摘要仅作为辅助上下文与定位信息，**不会对 RAG 检索做门控或过滤**；
- 针对已上传文件的查询，**无论摘要是否与查询相关，都通过 RAG 索引直接答复**；
- 该机制确保 **不会因摘要的局限性而导致文件内容静默不可访问**。

### 2.4 记忆摘要 — 范围与方式（Memory Summarization - Scope and Approach）

- 与 RAG 索引并行，系统自动从上传文件中生成关于公司相关内容的摘要，作为 **Layer 1a 记忆条目** 保存，附带以下元数据：
  - **Source Type**：document summary
  - 原始文件名（original file name）
  - 文件类型（file type）
  - 上传时间戳（upload timestamp）

- **对结构化数据文件（Excel / CSV）**，摘要只记录 **文件包含什么，不分析其含义**。具体应捕获：
  - 整体覆盖的 **时间区间**（如适用）；
  - 当前的 **数据类别或指标**；
  - 帮助 AI 理解"该文件是什么、何时应被检索"的 **高层级结构性上下文**。

- **明确排除** 的内容：
  - **Trend analysis**；
  - **Cost structure analysis**；
  - **任何其他分析性派生**。
  - 这些工作 **发生在查询时通过 RAG 检索完成**。

- 摘要 **不尝试解读或派生数据洞见** —— **只描述数据的结构与内容**；

- 摘要中 **排除**：
  - 通用电子表格结构；
  - 空白行和空白列；
  - 格式化痕迹；
  - 无数据内容的单元格。

- 摘要应 **明确说明**：**该文件内容可在聊天中供 AI 引用，但未被导入 LG 财务数据**；

- **仅当文件完全不含任何与公司相关的内容时，才不生成记忆摘要**；
  - 此时该文件仍可通过 RAG 检索在聊天中访问；
  - 但 **不会出现在 Memory Settings 面板**；
  - **没有生成记忆摘要不是错误**，**不需要向用户发出通知**。

### 2.5 非财务文件处理（Non-Financial File Handling）
- RAG 索引与摘要流程 **适用于所有上传的 Excel 与 CSV 文件**，**无论内容是财务还是非财务**；
- 对非财务文件：
  - **同样适用 RAG 为主的检索模型**；
  - 摘要 **只记录文件包含的内容，不做分析**。
- **财务解析逻辑、账户映射、指标归一化（financial parsing logic / account mapping / metric normalization）**，**绝不应用于非财务文件**。

### 2.6 与财务数据管线的隔离（Financial Data Pipeline Isolation）
- 经本故事处理的 Excel / CSV 上传 **在任何情况下都不会被 Looking Glass 导入或被财务数据摄取管线处理**；
- 记忆摘要过程 **不触发任何财务数据归一化、映射或写操作**；
- 维持清晰的边界：
  - 通过 **AI Chatbot 上传的文档** = **仅用于记忆丰富（memory enrichment）**；
  - 通过 **Manual Upload OCR 功能上传的文档** = **用于财务数据摄取**。

### 2.7 数据隔离（Data Isolation）
- **RAG 索引** 与 **记忆摘要** 均 **严格限定在源公司的 Layer 1a 文件**；
- 文档内容及其派生的摘要在 **任何情况下** 都不会流入 Layer 1b 或 GS Knowledge Base（Layer 2）；
- 已处理的文档内容 **不可被平台上任何其他公司访问**。

### 2.8 错误处理与性能（Error Handling and Performance）
- RAG 索引或摘要生成失败时，**记录日志以备排查**，**不向终端用户暴露任何错误**；
- 即便某次文档处理步骤失败，**Chatbot 仍正常工作**；
- 当文件 **过大、密码保护或损坏** 无法处理时：
  - **记录失败日志**；
  - 用户在聊天界面收到一条 **优雅的内联提示信息（graceful inline message）**。
- **非标准分隔符 CSV**（分号、Tab 等）**优雅处理**——**系统在处理前尝试检测并应用正确的分隔符**。

---

## 四、范围之外

- 不包含 PDF、Word、纯文本文件的处理（由独立 Story 覆盖）；
- 不包含将内容导入 LG 财务数据管线的任何能力；
- 不包含将内容向 Layer 1b 或 Layer 2 流转的任何能力；
- 不包含摘要阶段的趋势 / 成本结构等分析性派生。

---

