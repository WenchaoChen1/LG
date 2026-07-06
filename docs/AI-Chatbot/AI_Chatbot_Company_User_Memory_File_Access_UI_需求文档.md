# 需求文档：AI Chatbot – 公司用户 Memory 文件访问 UI

## 一、业务背景与目标

Company Admin 用户需要能够查看 AI Chatbot 学习到的关于其公司的内容。系统通过在公司端聊天界面中提供一个 **Memory Settings（记忆设置）面板**，以可读、可搜索、只读的方式展示 **Company Memory File（Layer 1a）** 的内容，帮助用户透明地了解 AI 用于个性化服务时所依赖的上下文。

---

## 二、范围与边界

### 2.1 面板展示内容范围
- 仅展示 **Layer 1a（Company Memory File）** 内容。
- **Layer 1b（Portfolio Admin Memory File）** 永远不得在公司端界面的任何元素中被引用、显示或访问。
- MVP 阶段，Layer 1a 仅包含**公司上传文档的摘要（Document Summary）**。
- **不包含**：聊天抽取内容（Chat-based memory extraction，规划为 MVP 后续版本）。
- **不存储且不展示**：Company Settings 数据、公司 URL 抓取生成的理解——这些数据仅作为 AI 的运行时上下文使用，不写入 Memory 文件，也不在面板中向任何用户（包括 Company Admin）展示。
- 对公司端用户隐藏的 Company Settings 字段（**Company Type、Company Status**），不得通过任何方式（包括 AI 回复）暴露给公司端用户。

### 2.2 权限范围
- **Company Admin**：可访问 Memory Settings 面板。
- **Company User**：**无权访问**该面板。

### 2.3 操作范围（MVP）
- **只读**：用户可浏览、搜索记忆条目；不可编辑、删除、新增。
- Memory 文件通过系统自动化流程增长（依据故事 `Company Memory File - Layer 1a Backend`，任务 ID 1214057483533664）。
- **不支持**将 Memory 文件下载/导出到本地。

---

## 三、功能需求（验收标准）

### 3.1 入口与访问
1. Memory Settings 面板作为**次要功能**，通过公司端聊天界面中的**设置图标或次级菜单**打开，不作为主导航的显要入口。
2. 面板为 LG 系统内的**在线视图**，无下载/导出功能。
3. 仅 Company Admin 可见此入口；Company User 无入口、无访问权限。

### 3.2 文件结构
1. Company Memory File 为**每家公司一份的统一单文件**，不按来源类型拆分文件。
2. 文件内每条条目都带有**来源标签（source label）**，MVP 仅有 "Document Summary" 一种。该标签仅用于显示与筛选，不改变底层单文件结构。

### 3.3 列表视图
1. 条目按**倒序时间**（reverse chronological）排列。
2. 每条条目显示：**来源类型标签**（MVP 仅 "Document"）+ **时间戳**。
3. 采用**紧凑列表 + 可展开详情**的形式；来源标签需视觉上有区分度（如小型彩色徽章或图标）。
4. 若后端以 markdown 格式存储条目，前端必须将其渲染为**整洁可读**的呈现。
5. 面板顶部固定展示一段简短说明文本：
   
   > "This is what your AI assistant has learned about your company. Access is read-only."

### 3.4 搜索
1. 面板顶部提供搜索框，占位符文案为 `"Search memories…"`。
2. 搜索范围：**所有 Memory 条目的完整内容/文本**（而不仅仅是列表中可能被截断的可见文本）。

### 3.5 Memory Detail 详情视图
1. 点击列表中的一条 Memory 条目，打开 Memory Detail 视图。
2. 详情视图头部与列表行保持一致，包含：**内容类型标签（"Document Summary"）** + **时间戳**。
3. **Document Summary 详情内容**：
   - 来源文件名（source file name）
   - 摘要文本（summary text）
   - 头部显示 "Document Summary" 标签与时间戳。

### 3.6 只读约束
- 所有访问在 MVP 中均为只读，无编辑与删除入口。

### 3.7 内部结构隐藏
- 面板中**不得**出现任何暗示存在独立内部 GS memory 层的标签、分区标题或 UI 元素。

### 3.8 响应式
- 功能需**移动端响应式**，在桌面端与移动端均完整可用。

---

## 四、业务闭环说明
1. 后台通过系统流程（见 Layer 1a Backend 故事）将公司上传文档的摘要写入 Company Memory File。
2. Company Admin 通过聊天界面的次级入口打开 Memory Settings 面板。
3. 面板拉取 Layer 1a 中当前公司的全部条目 → 倒序展示 → 展示统一说明文案与搜索框。
4. Admin 通过搜索快速定位条目 → 点击进入 Detail 视图查看完整摘要与源文件名。
5. Admin 全程只读浏览，无法修改；不感知 Layer 1b 与 Company Settings 相关数据；不涉及导出。
6. Company User 尝试访问时，无入口且无权限进入面板，完成权限闭环。
