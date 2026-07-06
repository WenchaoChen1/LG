# 需求文档：AI Chatbot – Portfolio Manager Memory 文件访问 UI

---

## 一、业务背景与目标

Portfolio Manager 需要能够通过 Portfolio Manager 端聊天界面的 **Memory Settings 面板**，查看其权限范围内**所有公司**的 Memory 文件。

与公司端只展示 Company Memory File 的面板不同，Portfolio Manager 端面板需同时提供每家公司的：

- **Company Memory File（Layer 1a）**：与 Company Admin 共享的记忆，仅包含**公司上传文档的摘要**（Company Settings 与 Company URL 抓取所得的理解不进入 Memory 文件，仅作为 AI 运行时上下文使用，不通过 Memory 文件向任何角色暴露，包括 Portfolio Admin）。使用标签 **"Company Memory — shared with Company Admins"** 明示对 Company Admin 可见。
- **Portfolio Admin Memory File（Layer 1b）**：由 Portfolio Manager 活动写入的内部 GS 上下文。使用标签 **"Portfolio Memory — visible to Portfolio Admins only"** 明示仅 Portfolio Admin 可见。

两者在 UI 上必须清晰、即时地视觉区分。

**MVP 说明**：
- Chat-based memory extraction 不在 MVP 内（post-MVP）。
- MVP 阶段 Layer 1a 与 Layer 1b **均仅包含 Document Summary（文档摘要）**。
- Company Settings 数据与 Company URL 抓取所得的理解**仅为 AI 运行时上下文**，不存入 Memory 文件，不通过 Memory 文件展示给任何角色（包括 Portfolio Admin）。
- MVP 中两个视图**严格只读**，Portfolio Manager 不能通过 UI 编辑或删除条目。

---

## 二、范围与边界

### 2.1 使用角色
可访问此 Memory Settings 面板的 Admin 角色：**Super Admin、PGM、PM**（对该公司有访问权限的角色）。

### 2.2 权限范围
- PGM 与 PM 用户**只能访问其自身权限范围内公司**的 Memory 文件；范围外公司不可见、不可访问。
- Super Admin 可访问其权限范围内所有公司。

### 2.3 操作范围（MVP）
- 只读浏览与搜索；无编辑、删除、新增能力。
- 无下载/导出。

---

## 三、功能需求（验收标准）

### 3.1 入口与访问
1. Memory Settings 面板嵌入在 Portfolio Manager 端聊天界面内，仅 Admin 角色（Super Admin、PGM、PM）可访问。

### 3.2 公司选择器
1. 面板顶部提供**公司选择器下拉框**，用于选择要查看哪家公司的 Memory 文件。
2. 下拉列表**仅包含**当前用户权限范围内的公司。

### 3.3 双文件展示与视觉区分
1. 选定公司后，面板**同屏展示两个部分**：
   - Company Memory（Layer 1a）
   - Portfolio Memory（Layer 1b）
2. 两个部分之间须有**清晰、即时**的视觉区分（如 Tab 布局、不同色系区块标题，或带标签徽章的清晰分隔线）。
3. Portfolio Memory 区块标题固定为 **"Portfolio Memory"**；不再使用逐区块的"who can see this"指示器标签，可见性说明由顶部单行说明统一承载（见 3.4）。

### 3.4 顶部单行访问与可见性说明
面板顶部展示**单行**、纯文字说明：
> "This is what your AI assistant has learned about your company. Access is read-only. Company Memory is shared with Company Admins. Portfolio Memory is visible to Portfolio Admins only."

### 3.5 列表视图
1. 每个区块内条目按**倒序时间**（reverse chronological）排列。
2. 每个条目行在**正文下方 + 时间戳旁**展示以下**标签组**：
   - **Memory-type 标签**："Portfolio Memory"（Company Memory 区块下的条目沿区块归属；见 3.7 Detail 视图中 Memory-type 标签允许取值 "Company Memory" 或 "Portfolio Memory"）
   - **Content-type 标签**："Document Summary"（"Company Profile" 为 post-MVP，MVP 不出现——见 3.8）
3. 采用**紧凑、可扫描的列表 + 可展开详情**布局。

### 3.6 搜索
1. 面板提供搜索功能，支持：
   - **跨两个文件同时搜索**；或
   - **过滤到某一个文件内**搜索。
2. 搜索 UI 需清晰指示当前正搜索哪个（些）文件。

### 3.7 过滤器
面板提供两个**互相独立**的下拉过滤器：
1. **Type 过滤器**：按 content-type 过滤。
2. **Files 过滤器**：值为 **"All Files" / "Company Memory" / "Portfolio Memory"**，用于按条目所属文件过滤。
3. 两个维度独立生效：Type 按内容类型过滤；Files 按归属文件过滤。

### 3.8 MVP Content-type 标签范围
- MVP 阶段 content-type 标签**仅限 "Document Summary"** 一种。
- **Company Profile 不是 MVP 中的存储条目类型**（Company Settings 与 URL-derived 理解仅为 AI 上下文，不入库）。
- Chat-extraction 分类标签（Pricing Model、Value Proposition & ROI、Strategic Challenges、ICP、Competitors、Porter's Five Forces、Founder DISC 等）为 post-MVP，**MVP 列表与过滤器中不得出现**。

### 3.9 Memory Detail 详情视图
1. 点击条目打开 Memory Detail 视图。
2. 详情视图的**标题下方**展示与列表行**完全一致**的标签组：
   - Memory-type 标签："Company Memory" 或 "Portfolio Memory"
   - Content-type 标签："Document Summary"
   - 时间戳
3. **Document Summary 详情内容**：
   - **来源文件名**（source file name）
   - **摘要文本**（summary text）
   - 头部展示 "Portfolio Memory"（或 "Company Memory"）+ "Document Summary" 两个标签，以及时间戳。

### 3.10 只读约束
- MVP 中不提供编辑、删除入口，全部只读。

### 3.11 权限隔离
- PGM 与 PM 用户对权限范围**之外**公司的 Memory 文件不可见、不可访问、不可搜索。

### 3.12 响应式
- 功能需**移动端响应式**，桌面端与移动端均完整可用。

---

## 四、业务闭环说明
1. 后台按 Layer 1a Backend 与 Layer 1b Backend 故事产出各公司的 Memory 文件（MVP 阶段两层均只含 Document Summary）。
2. Admin 角色（Super Admin / PGM / PM）进入 Portfolio Manager 聊天界面，打开 Memory Settings 面板。
3. 通过顶部**公司选择器**从其权限范围内选择一家公司 → 系统同屏展示该公司的 Company Memory（Layer 1a）与 Portfolio Memory（Layer 1b），并给出顶部统一的访问与可见性说明。
4. 用户可通过 **Type + Files 双维过滤**与**跨/单文件搜索**快速定位条目。
5. 点击任意条目进入 Detail 视图，查看 Document Summary 的源文件名与摘要文本；标签与时间戳与列表行保持一致。
6. 全程只读；权限范围外的公司在选择器与搜索中均不可见，Memory 内部结构（GS 内部含义）不通过任何逐区块指示器暴露，可见性认知由顶部单行说明统一承载，完成访问与权限闭环。
