# 需求文档：GS Knowledge Base — Layer 2 摄取与管理

## 一、业务背景与目标

AI Chatbot 的两层知识架构依赖于一个 **已填充、可查询的 Golden Section 知识库（Layer 2 共享资源）**。

- **Layer 1（公司专属记忆文件）**：由用户活动自动构建；
- **Layer 2（GS 知识库）**：必须由 Golden Section **内部显式填充**；
- MVP 范围：本层内容为 Golden Section 已有的 **Playbook 与最佳实践框架**——即 GS 在长期运营中沉淀的全部运营与战略知识。

### Hosting 策略决策

此前已完成研究任务以判断：**将 GS Playbook 托管在公开外部网站，是否能带来 GEO（Generative Engine Optimization）可见性收益**——即 AI Chatbot 访问外部站点回答问题，是否会提升该站点在其他 AI 模型对话中的权威性或可见性。

**研究结论**：**外部托管不产生 GEO 收益**。AI 模型不会因为在会话中接收内容就学习该网站或提升其权威性。
**决策**：采用 **Option B**——将外部站点中所有现有的 GS Playbook 内容 **复制至 Looking Glass 内部一个受管的结构化文档存储**，作为 GS 知识库的来源。

外部参考站点：https://www.goldensection.com/vertical-saas-playbooks

### 本故事范围

- 摄取 markdown 文件及任何配套文档，使 AI Chatbot 可对其进行查询；
- 提供 **面向内部授权用户（Super Admin 与 PGM）** 的内部管理工具，用于随时间持续管理与更新内容；
- 结果是一个 **常驻、可搜索的知识层**，所有 Chatbot 用户（Company 侧、Portfolio Manager 侧）均可借助其获得战略指导，**而无需看到原始文档本身，也不需知道知识库的结构细节**。

### 与 Layer 1 的关系

- GS 知识库与任何单个公司的 Layer 1 记忆文件 **完全分离**；
- 在当前 **单租户实现** 下，它是一个 **全局共享资源**——平台上所有公司的所有用户看到的内容相同；
- 它 **不包含** 任何公司专属数据、财务信息、组合公司或创始人识别信息；
- 其唯一目的：通过 Chatbot 以自然对话方式，**访问 GS 集体的运营与战略知识**。

### MVP 范围与权限边界

- MVP 仅覆盖 **现有 Playbook 内容的摄取与查询**；
- **由 LLM 自动从 Portfolio Management 对话中检测知识库更新——明确为 MVP 之后（post-MVP）**；
- 当前阶段，需 **由授权用户手动上传或更新**；
- 知识库编辑授权角色：**Portfolio Group Manager（PGM）及以上**；**更低角色无权修改 Playbook 内容**。

### 架构注意事项（面向开发团队）

- 未来 Looking Glass 商业化、销售给外部 Equity Firm 时，**每个 firm（租户）需要其独立的、完全与其他租户隔离的知识库**；
- 当前单租户共享 GS 知识库适用于 MVP；
- **架构设计须为按租户的知识库隔离做好准备**，以便未来支持多租户时无需大规模重构；
- **不得** 以"全局唯一知识库永远是唯一结构"作为前提构建 Layer 2。

---

## 二、功能需求（Acceptance Criteria）

### 2.1 内容摄取（Content Ingestion）

- 一个租户的 Playbook（Layer 2）内容由 **授权用户（PGM / Super Admin）** 通过 **Manage Playbook 界面上传 markdown 文件** 填充；**后端不抓取（scrape）任何外部网站**；
- 上传的 markdown 内容被 **解析、处理并索引** 到可查询的存储中，供 Chatbot 检索；
- 摄取的内容作为 **该租户的 Layer 2 知识库** 存储与索引，**该租户内所有 Chatbot 用户均可访问**，不论其所属公司或角色；
- GS 知识库 **在数据与架构层面与任何公司的 Layer 1 记忆文件完全分离**——**不存在任何路径** 能使 Layer 2 内容变成公司专属，或反之；
- Layer 2 中 **绝不存储** 任何公司识别信息、财务数据或创始人专属上下文；
- **完整的初始 GS Playbook 内容必须作为验收测试的一部分被摄取并验证**。

### 2.2 内容管理（Content Management，按租户）

提供一个 **内部 admin 界面/流程**，供授权用户：
- 上传新内容；
- 更新 markdown 文件；
- 从知识库中移除文档。

> **说明**：该页面与 chat-attachments 文件列表（Company Documents / Internal GS Documents）共享；该列表由另一关联 Story（参见 Asana 任务 1214953638826120）覆盖；**本故事仅覆盖按租户的 Playbook 部分**。

#### 2.2.1 Playbook 管理（Playbook Management，按租户）

**租户选择器（Tenant Selector）**
- 若用户仅可访问一个租户：**不显示选择器**，页面默认指向该租户；
- 若用户可访问多个租户：**显示租户选择器**，默认选中用户的 home（登录）租户；
- 所选租户决定 "Manage Playbook" 应用于哪个租户。

**每个租户至多一个 Playbook 文件。** "Manage Playbook" 打开当前所选租户的 Playbook。

**无 Playbook 时**
- 点击 "Manage Playbook" 打开 **上传窗口**：
  - 支持 **拖拽（drag-and-drop）或点击上传**；
  - 支持文件格式：**.md / .markdown**；
  - 单文件 **上限 5 MB**。

**已存在 Playbook 时**
- 点击 "Manage Playbook" 打开 **Playbook Viewer**：
  - 只读渲染视图，展示 Playbook 内容；
  - 展示元数据：**Upload date（上传日期）**、**Last updated date（最近更新日期）**。

**Viewer 顶部操作（Top Controls）**
- **Import Markdown（下拉菜单）**
- **Edit（编辑）**
- **Close（关闭）**

**Import Markdown 下拉中的两个操作：**

1. **Import New File（导入新文件）**
   - 打开文件选择器上传一个 markdown 文件；
   - **import = replace**：完全替换当前 Playbook；
   - 替换前显示确认对话框：
     - **Title**：`Import New Markdown File?`
     - **Body**：`The current playbook content will be replaced with content from the new markdown file. You can upload a new file at any time, but the current content will no longer be available.`
     - **Actions**：`Cancel` / `Import & Replace`

2. **Delete File（删除文件）**
   - 永久删除 Playbook；
   - 删除前显示确认对话框：
     - **Title**：`Delete Markdown File?`
     - **Body**：`This action will permanently delete the markdown file and its associated content. This action cannot be undone.`
     - **Actions**：`Cancel` / `Delete`
   - 删除后，该租户处于 **无 Playbook 状态**，"Manage Playbook" 回到上传初始态。

**Editor Save 状态**
- 若内容被清空，**Save 按钮禁用（置灰）**；
- **仅当存在内容时 Save 启用**；
- 编辑结果以 **markdown 格式** 回写保存，保持 markdown 作为 **唯一来源格式（single source format）**。

**保存 / 成功导入后**
- Playbook 被 **重新索引**，更新后的内容 **立即可查询**；
- **Last updated date** 相应刷新。

**内容上传 / 更新时**
- 知识库 **自动重新索引**，新内容或变更内容 **立即可用于查询**。

**内容被移除时**
- 该内容在 Chatbot 回复中 **不再可检索**。

#### 2.2.2 Admin 界面状态指示器
- 在 admin 界面提供简单的 **状态指示器**，展示：
  - 知识库 **最近一次更新时间**；
  - **当前索引的文档数量**。

### 2.3 Chatbot 查询行为（Chatbot Query Behavior）
- Chatbot 能够在用户提出关于战略、最佳实践或 GS 指导的问题时，**准确检索并引用** 已摄取的 Playbook 内容；
- **不得逐字暴露原始文档文本**——AI 需 **以会话语言对相关指导进行综合与摘要**。

### 2.4 未来多租户兼容（Future Multi-Tenancy Compatibility）
- Layer 2 架构设计 **必须支持未来按租户的知识库隔离**；
- 待多租户实现时，每个外部 Equity Firm 都可拥有 **独立的知识库**。



---

## 三、范围之外（明确不在 MVP 内）

- **LLM 自动从 Portfolio Management 对话中检测知识库更新**（明确为 post-MVP）；
- 任何"浏览 Playbook"的对外用户 UI；
- 后端自动抓取外部网站（明确禁止）；
- 共享文件列表（Company Documents / Internal GS Documents）由另一关联 Story 覆盖，**本故事仅含按租户的 Playbook 管理**。

---

