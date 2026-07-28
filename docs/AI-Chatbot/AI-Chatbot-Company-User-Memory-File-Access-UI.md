# 需求文档：AI Chatbot – Company User Memory File Access UI

## 1. 背景与目标

Company Admin 用户需要通过 Company 端聊天界面中的 Memory Settings 面板，查看 AI Chatbot 已经学习到的关于本公司的信息。该面板以只读、可搜索、可读性良好的方式呈现 Company Memory File（Layer 1a）的内容，让用户对 AI 用于个性化交互的上下文保持透明。

## 2. 角色与权限

- **Company Admin**：可访问 Memory Settings 面板（唯一入口角色）。
- **Company User**：无任何入口，完全不可访问该面板。
- **Layer 1b（Portfolio Admin Memory File）**：在 Company 端界面中永不引用、永不显示、永不可访问；面板中也不得出现任何暗示"另有一层内部 GS memory"存在的标签、分组标题或 UI 元素。

## 3. 数据范围（MVP）

- Memory File 为**每家公司一个统一文件**，非按来源分成多个文件。
- 文件中每条 Entry 通过 **Source Label** 标记来源，仅用于展示与过滤，所有条目仍存于同一份文件内。
- MVP 中 Layer 1a 仅包含：**公司已上传文档的摘要（Document Summary）**。
- Chat 提取内容属于 Post-MVP，不进入本次范围。
- **Company Settings 数据**（含 Company Type、Company Status 等对 company-portal 用户隐藏的字段）与**公司 URL 抓取衍生的理解**：仅作为运行时上下文提供给 AI，**不写入 Memory File，不在面板中呈现给任何用户**（包括 Company Admin）；AI 的对话回复中也不得泄露 Company Type、Company Status 等隐藏字段。

## 4. 功能需求

### 4.1 入口

- 面板入口位于 Company 端聊天界面内，通过 **settings 图标 / 二级菜单** 进入，作为背景性功能存在，不作为主导航元素。

### 4.2 顶部说明

- 面板顶部展示一句纯语言说明：
  
  > "This is what your AI assistant has learned about your company. Access is read-only."

### 4.3 列表视图

- Entries **按倒序时间（reverse chronological order）** 排列。
- 每条 Entry 显示：**Source Type Label**（MVP 仅 "Document"）+ **Timestamp**。
- 采用紧凑列表 + 可展开详情形式；Source Label 需具备视觉区分度（例如小型彩色徽章 / 图标）。
- 若后端 Memory File 以 Markdown 存储，前端 UI 必须以整洁、易读的方式渲染。

### 4.4 搜索

- 列表顶部提供搜索栏，占位符为 **"Search memories…"**。
- 搜索范围为所有 Entry 的 **完整内容 / 文本**，而非仅列表中可见（可能截断）的文本。

### 4.5 Memory Detail 视图

- 点击列表中任一 Entry 打开详情视图。
- 详情 Header 保留与列表行一致的 **Content-Type Tag（"Document Summary"）** 与 **Timestamp**。
- **Document Summary 详情** 展示：
  - 源文件名（source file name）
  - Summary 文本
  - Header 带 "Document Summary" 标签与 Timestamp

### 4.6 只读约束

- MVP 全程只读：用户不能编辑、删除或新增任何 Entry。
- Memory File 由后端系统流程自动持续增长（依赖 Story：Company Memory File - Layer 1a Backend (Company User Context)）。

### 4.7 导出限制

- 面板仅为 LG 内在线视图，**不提供下载 / 导出至本地** 的任何入口。原因：Memory File 为实时增长的持久上下文，下载得到的静态快照会立即过时，违背其"持续最新上下文"的目的。

### 4.8 响应式

- 功能须在桌面端与移动端均完整可用（Mobile Responsive）。

## 5. 业务逻辑闭环

1. **系统层**：Company 上传文档 → 后端处理生成 Document Summary → 自动写入该 Company 的统一 Memory File（Layer 1a），并打上 "Document Summary" 来源标签与时间戳。
2. **访问层**：Company Admin 在 Company 端聊天界面通过 settings 图标 / 二级菜单进入 Memory Settings 面板。
3. **展示层**：面板校验角色（仅 Company Admin 可见）→ 拉取当前公司的 Layer 1a 数据 → 按倒序时间渲染列表，每行显示 Source Label + Timestamp。
4. **交互层**：用户可通过顶部搜索栏对全量内容检索；点击任一条目进入 Detail 视图，查看文件名与完整摘要。
5. **只读闭环**：用户无法在 UI 中修改数据；Memory File 由后端自动更新，用户每次访问看到的均为当前最新版本。
