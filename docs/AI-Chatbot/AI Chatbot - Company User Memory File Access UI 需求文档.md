# AI Chatbot - Company User Memory File Access UI 需求文档

## 一、功能概述

Company Admin 用户必须能够通过 Company-side 聊天界面内的 **Memory Settings 面板**，查看 AI 聊天机器人对其公司所"学到"的内容。该面板以**可读、可搜索、只读**的形式呈现 **Company Memory File（Layer 1a）** 的内容，让用户能够透明地了解 AI 用以个性化体验的上下文。

**关键边界**：
- Memory Settings 面板**仅显示 Layer 1a（Company Memory File）内容**。
- **Portfolio Admin Memory File（Layer 1b）**绝不会通过 company-side 界面的任何元素被引用、暴露或访问。
- **Company User 角色完全无权访问** Memory Settings 面板——仅 Company Admin 可见。

**MVP 定位**：**只读视图**。用户可浏览和搜索 memory 条目，但不能直接编辑、删除或新增条目。Memory file 通过系统驱动的流程**自动增长**（机制由依赖故事 "Company Memory File - Layer 1a Backend" 建立）。

---

## 二、数据模型

### 2.1 Memory File 结构
- 每家公司**只有一个统一的 Memory File**。
- **不**按 source type 划分为多个独立文件（即不是每个公司有 Profile/Chat/Document 三个文件）。
- 每条 entry 内**打上 source 标签**以标明来源：
  - **Company Profile**
  - **Chat**
  - **Document**
- 标签**仅用于展示与筛选**——所有 entry 均存于同一个文件中。

### 2.2 Memory Entry 内容性质
- 显示的 entry 是 **AI 提炼的 learnings 和 summaries**。
- **不是** chat 节选、对话日志或过往对话的逐字文本。
- **Source 标签仅指示来源；不显示任何实际 chat 内容**。
- 完整的对话记录**只能**通过另一个独立故事 "AI Chatbot - Chat History for All Users" 中的 **Chat History 功能**访问。

### 2.3 存储格式
- 后端如以 markdown 格式存储 memory file 条目，UI 必须以**简洁可读**的方式渲染（不可直接展示原始 markdown 源码）。

---

## 三、用户范围与访问权限

| 角色 | Memory Settings 面板访问权限 |
|---|---|
| **Company Admin** | ✅ 可访问（唯一可见此面板的角色） |
| **Company User** | ❌ 完全无访问权限 |
| 任何 Portfolio 角色 | 不在本故事讨论范围（且 Layer 1b 内容绝不暴露给 company-side） |

---

## 四、验收标准（Acceptance Criteria）

### 4.1 单一统一文件 + 标签
Company Memory File 为**每家公司一个统一文件**，**不按 source type 拆分文件**。文件内每条 entry 通过 source 标签（"Company Profile"、"Chat" 或 "Document"）标明来源。**该标签仅用于展示与筛选**，所有 entry 均在同一文件中。

### 4.2 面板访问入口
Memory Settings 面板**仅 Company Admin** 可在 company-side 聊天界面内访问，入口为**设置图标或次级菜单**（settings icon or secondary menu）。

### 4.3 仅在线浏览，不可下载
Memory Settings 面板是 **LG 内的在线视图**（in-app online view）。**不提供**将 memory file 下载或导出到用户本地的功能。

### 4.4 Markdown 渲染
若 memory file 条目在后端以 markdown 格式存储，UI 必须以**简洁、可读的呈现方式**渲染其内容。

### 4.5 Company User 不可访问
Company User 角色对 Memory Settings 面板**没有任何访问权限**。

### 4.6 仅 Layer 1a 可见
面板**仅显示 Company Memory File（Layer 1a）** 条目——**Layer 1b 内容绝不可见、不被引用、不可访问**。

### 4.7 排序与展示
条目按**倒序时间顺序**（reverse chronological order）展示，每条 entry 同时显示：
- **Source 类型标签**（"Company Profile"、"Chat"、"Document"）
- **时间戳**

Source 标签**仅指示来源**——不展示任何实际 chat 内容。

### 4.8 展示提炼后的 learning，而非对话原文
展示的 entry 是 **AI 提炼的 learnings 和 summaries** —— 不是 chat 节选、conversation logs 或过往对话的逐字文本。完整对话记录仅可通过独立的 **Chat History** 功能访问。

### 4.9 搜索功能
面板内提供**搜索功能**，用于定位特定的 memory 条目。

### 4.10 只读
所有访问均为**只读**——MVP 不提供条目的编辑或删除功能。

### 4.11 顶部说明文案
面板顶部需展示一段简短的**通俗语言说明**。

**示例文案**：
> "These are the key things your AI assistant has learned about your company over time. Full conversation history is available separately."

### 4.12 移动端响应式
功能需为 mobile responsive，确保在桌面和移动设备上均完全可用。

---

## 五、业务逻辑闭环

```
Company Admin 用户在 Ask Goldie 聊天界面寻找 Memory Settings 入口
    ↓
通过设置图标 / 次级菜单（非主导航）进入 Memory Settings 面板
    ↓
权限校验：
    ├─ Company Admin → 允许进入面板
    └─ Company User / 其他角色 → 不可访问，无任何入口
    ↓
系统加载该公司的统一 Memory File（Layer 1a）
    ├─ 严格不加载 Layer 1b 内容
    └─ 严格不引用任何暗示 GS 内部 memory 层存在的元素
    ↓
面板顶部展示通俗语言说明
（"These are the key things your AI assistant has learned about your company over time.
   Full conversation history is available separately."）
    ↓
条目按倒序时间顺序渲染：
    ├─ 每条 entry 显示 source 标签（Company Profile / Chat / Document）+ 时间戳
    ├─ 内容为 AI 提炼的 learnings 与 summaries（不含 chat 原文）
    ├─ 若后端为 markdown 格式，UI 渲染为可读呈现
    └─ 紧凑列表，单条可展开查看详情
    ↓
用户可执行的操作（只读范围）：
    ├─ 浏览条目
    ├─ 通过搜索功能定位特定 entry
    └─ 通过 source 标签筛选（标签仅作展示与筛选用途）
    ↓
用户不可执行的操作（MVP 范围内禁止）：
    ├─ 编辑 entry
    ├─ 删除 entry
    ├─ 新增 entry（memory file 通过系统驱动流程自动增长）
    └─ 下载 / 导出 memory file 到本地
    ↓
若需查看完整对话原文，用户走独立功能：Chat History
    ↓
功能在桌面端与移动端均完全可用
```

