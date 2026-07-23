# 需求文档：AI Chatbot — 公司端用户核心聊天 UI

**来源任务**：AI Chatbot - Company User Core Chat UI
**Asana 链接**：https://app.asana.com/1/1170332106480422/project/1215698870864641/task/1214057483533662
**适用模块**：Looking Glass 公司端界面 — Ask Goldie 入口与聊天界面
**适用角色**：Company User、Company Admin
**Figma 设计稿**：https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=12659-18104

---

## 一、背景与范围

Looking Glass 需要为公司端用户（**Company User** 与 **Company Admin** 角色）提供一个对话式 AI 聊天界面，作为公司端平台中**所有 AI Chatbot 交互的主要入口**。

**本需求的范围**：
- 仅覆盖**公司端 Chatbot 体验的基础 UI 外壳与交互设计**；
- **不包含**：数据集成、知识库连接、记忆文件访问、聊天历史——这些由其他依赖任务覆盖。

**严格的上下文限制**：
- 界面严格限定在**公司上下文**之内；
- 公司端用户**无法看到**任何 portfolio 级别信息、其他公司信息或任何 Golden Section 内部备注或评估；

---

## 二、功能描述

### 2.1 入口标签（Entry Tab）
- 在公司的 Looking Glass 上方导航栏新增一个 **"Ask Goldie"** tab；
- Company User 和 Company Admin 角色可访问该tab；
- 用户进入 Ask Goldie tab后，**直接进入聊天体验**。

### 2.2 欢迎屏（Welcome Screen）
欢迎屏展示一个清晰的**标题**与一组围绕公司业绩的**建议提示卡片（Suggested Prompt Cards）**，帮助用户快速上手。

#### 标题
> **Always here, always in sync—your partner for every business move.**
>
> Ask questions about your company's financials, get insights, or generate reports.

#### 默认静态提示卡片（6 张）
| 类别 | 提示文案 |
|---|---|
| Financials | How is my revenue trending over the last 6 months? |
| Benchmarks | Which benchmark am I most out of line with compared to my peers? |
| Forecast | What does my system-generated forecast look like for the next 6 months? |
| Performance | What is my current ARR growth rate and how has it changed? |
| Risks | What areas of my business are showing signs of financial risk right now? |
| Strategy | What does GS recommend for companies at my stage of growth? |

> 提示主题需覆盖 **financial performance、benchmark positioning、forecast-related questions**。

#### 默认提示卡片的交互
- **可点击**：每张提示卡片均可点击；
- **悬停态**：悬停时卡片边框/外框高亮；
- **点击行为**：点击卡片**自动开启一个新对话**并发送该问题。

### 2.3 输入栏（Input Bar）

#### 显隐与一致性
- 输入栏在**欢迎屏**和**对话视图**均展示，外观与行为在两者间**保持一致**，供用户输入自由形式的自然语言问题。

#### Placeholder
- 文案："Type your question about company performance..."（灰色）；
- 用户开始输入后，placeholder 消失。

#### 高度自适应
- 随用户输入，输入框**高度扩展至最高 460px**；
- 达到上限后**不再增高**，只显示**正在输入的最新内容**（**不滚动**）。

#### Send 按钮状态
- **空输入**：Send 按钮**禁用**；
- **活跃状态（有文本，未在生成中）**：
  - Send 按钮高亮；
  - 用户输入时，输入框边框带有**轻微动态/脉动**效果。

#### 左下角图标 (+图标)
- 图标有**悬停态**；
- 点击图标弹出一个 **pop-up**，内含两个按钮（按钮的底层功能由其他任务覆盖，本任务**仅覆盖**图标、pop-up 及两个按钮的 UI）：
  - **Attachment**：含标签、图标及说明文案 "Uploaded files saved to memory for future reference."；
  - **Playbook**：含标签、图标及说明文案 "Use your Playbook as a knowledge source." 附带一个**开关**用于打开/关闭 Playbook。

### 2.4 对话视图（Conversational View）

#### 新建对话
- "New Chat" 按钮或控件**始终可访问**，允许用户开启新对话。

#### 进入对话
- 用户发送消息后（无论是手动输入还是点击建议提示卡片），**欢迎屏被对话视图替换**。

#### 消息对齐与样式
- **用户消息**：**右对齐**，**浅橙色气泡**；
- **AI 回复**：**左对齐**；
- 每条消息显示**时间戳**。

#### AI 回复格式
- AI 回复支持 **Markdown 渲染**——包括**加粗、列表、表格、链接**。

#### 生成中状态（Response-in-progress）
- 生成期间显示：
  - **"[实时秒数计数] thinking"**；
  - 加载指示器；
  - Send 按钮变为 **Pause 按钮**。
  - 消息编辑按钮隐藏，仅显示复制按钮
- 用户在生成中点击 **Pause/Stop**，行为根据阶段不同：
  - **在 thinking 阶段被中断（尚未流式输出任何内容）**：
    - 停止生成；
    - 不显示响应体，附明确"已停止"指示（例如 "Response stopped"）；
    - **用户消息保留**在聊天历史；**AI 响应不保存**（无内容可留）；
    - Pause 按钮恢复为 Send。
  - **在 streaming 阶段被中断（已显示部分内容）**：
    - 停止生成；
    - **部分内容保留**，附明确"已停止"指示（例如 "Response stopped"）；
    - **用户消息与部分响应都保留**在聊天历史；
    - Pause 按钮恢复为 Send。

#### 错误态
- **消息发送失败**：显示错误信息 "Your message didn't send. Please check your connection and try again."，并提供**重试**选项；
- **响应生成失败或超时**：显示错误信息 "Something went wrong generating a response. Please try again."，并提供**重试**选项。

#### 单条消息操作
- AI 回复**没有**单条消息操作。

#### 输入栏持久性
- 输入栏在整段对话中**固定在底部/始终可访问**。

#### 滚动行为
- 对话增长时，旧消息向上滚动；视图**自动滚动到最新消息**。

#### 上下文限制
- 界面严格限定在**公司级上下文**；
- 公司端用户**不可见、不可访问**任何 portfolio 级数据、其他公司数据或 GS 内部内容。

#### AI 生成声明
- 显示可见的免责声明：
  > "AI-generated results. Please review for accuracy before finalizing."
  说明回复由 AI 生成、仅供信息参考。

#### AI 思考或流式输出期间切换对话

- 如果用户在 AI 仍在思考或流式输出回复时切换到另一场对话：
  正在进行的生成任务不会丢失——它会在服务器端继续进行，并保存到发起该任务的对话中。用户此时只是在查看另一场对话。
  当用户返回原对话时，会看到已完成（或仍在流式输出）的回复。
  输入栏/发送状态是针对单场对话的：切换离开不会取消生成任务，而新打开的对话会显示其自身的状态（空闲，或其自身的正在进行的回复）。                   

#### 移动端响应式

- 功能需为移动端响应式，桌面端与移动端均完全可用。

---

