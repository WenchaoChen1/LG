# AI Chatbot - Document Upload for Chat Analysis Knowledge Base（Company Portal）需求文档

## 一、需求背景

本 story 覆盖公司端聊天界面中的 Knowledge Base 面板——一个专门用于展示公司上下文中所有已上传文档的视图。它是上传交互 story（`task/1216219449500193`）的配套 story：上传交互 story 处理上传动作本身，本 story 完全聚焦于已上传文件的可见性、可发现性与管理。

Knowledge Base 面板为公司端用户提供一个持久、有组织的入口，能够访问所有为该公司上传并已建立索引的文档。用户无需记忆某个文件是在哪一次会话中上传的，即可从单一面板浏览、搜索和筛选所有已上传文件。随着已上传文档的数量增长，且用户需要确认聊天机器人已具备哪些上下文时，此面板的价值尤为突出。

Knowledge Base 面板内的文件可见性按角色范围隔离：
- Company User 仅能看到自己上传的文件，无法看到同公司内其他用户上传的文件。
- Company Admin 可看到本公司任意用户上传、存储在 Layer 1a 的所有文件。
- Layer 1b 文件对任何公司端用户永远不可见，无论其角色。

此范围隔离保证用户始终看到与自己相关且经过恰当过滤的视图，避免暴露他人上传的可能包含敏感信息的文件。

Knowledge Base 面板在 MVP 阶段为只读参考视图——用户可浏览、搜索、筛选和下载文件，但不可从该面板编辑文件元数据或重新处理文件。

## 二、适用范围

- 目标端：Company Portal（公司门户）。
- 用户角色：Company User、Company Admin。
- 版本：MVP。

## 三、功能需求

### 1. 面板入口与布局（Panel Access & Layout）

- Knowledge Base 面板作为公司端聊天界面内的一个次级面板或标签页可访问，与主对话线程明确区分。
- 面板以列表视图展示公司上下文中的所有已上传文档。
- 每一行展示以下信息：
  - 文件名（file name）
  - 文件类型（file type）
  - 「From chat」链接（回到该文件被上传时的原始会话）
  - 上传日期（upload date）
  - 上传者姓名（uploader name）
  - 文件大小（file size）
- 每行支持通过简单的图标操作下载该文件。MVP 不要求提供应用内预览。

### 2. 搜索与筛选（Search & Filter）

- 用户可按文件名进行搜索。
- File Type（单选）
新增 "All File Types" 选项
默认选中 "All File Types"，回显 "All File Types"
选择具体类型，回显该类型名称
- Uploader（多选）
默认全选，回显 "All Uploaders"
选择部分，回显 "Uploader" + 黄色圆形角标（白色数字显示已选数量）
全不选，视为全选，回显 "All Uploaders"
- Company（多选）
默认全选，回显 "All Companies"
选择部分，回显 "Company" + 黄色圆形角标（白色数字显示已选数量）
全不选，视为全选，回显 "All Companies"

### 3. 分页（Pagination）

- 当条目数量超过一页时，列表进行分页展示，并提供分页导航与每页条数选择器（page size selector）。
- 当所有条目可容纳在一页内时，不显示任何分页控件。

### 4. 基于角色的可见性（Role-Based Visibility）

- Company User：仅可见自己亲自上传的文件；同公司内其他用户上传的文件不可见，无论这些文件是否存储在 Layer 1a。
- Company Admin：可见本公司任意用户上传、存储在 Layer 1a 的所有文件。
- Layer 1b 文件永远不对任何公司端用户可见，无论角色。

### 5. 空状态（Empty State）

- 当尚未上传任何文档时，面板显示友好的空状态，例如：「No documents uploaded yet. Upload a file in the chat to get started.」
