# 需求文档：公司档案扩展 — 描述字段增强

**来源任务**：Company Profile Expansion - Enhanced Description
**Asana 链接**：https://app.asana.com/1/1170332106480422/project/1215698870864641/task/1214057483533667
**适用模块**：Company Settings（公司设置） — Company Overview / Company Description；AI Chatbot Layer 1 Memory File
**Figma 设计稿**：https://www.figma.com/design/QBhTPAljVPx673QWVrvfGw/2026---Portfolio-Portal?node-id=12659-18132

---

## 一、背景与问题

AI Chatbot 的公司记忆文件（**Layer 1**）由 Looking Glass 中已有的公司元数据初始化。为了让 Chatbot 从第一天起就对每家公司有有意义的基础理解，这份元数据必须**足够完整且有用**。

现状盘点：
- Looking Glass 的 Company Settings 已经记录了 **公司类型（type）** 和 **阶段（stage）** —— 这些字段无需额外开发即可写入记忆文件；
- **现有"公司描述（Company Description）"字段不够用**：
  - 范围有限、字符上限低；
  - 无法承载一段真正有用的、关于公司业务的描述；
- **没有 industry（行业）字段**——而 industry 能提供更具体的市场上下文；
- 因此应：
  - 在 **Company Description 字段的默认提示文案**中明确建议用户写入 industry；
  - 扩展该字段的字符上限。

更丰富的描述 + 具体的行业说明，能给 Chatbot 每次对话提供更扎实的起点，**降低用户每次重新解释业务背景的负担**。

---

## 二、解决方案概述

本需求做两件事：
1. **将 industry 通过描述字段引入**——在 Company Description 字段的**默认提示文案**中明确建议用户写入公司行业；
2. **扩展 Company Description 字段**——提升字符上限，并加入引导性 helper text / placeholder，帮助用户写出对 Chatbot 真正有用的描述。

这些内容会：
- 在 AI Chatbot 为该公司**首次初始化**时，自动写入 Layer 1 记忆文件；
- 用户**修改字段时**，记忆文件**同步更新**。

---

## 三、功能描述

### 3.1 Company Overview 默认提示文案更新
- 现有 Company Overview 字段的默认提示文案进行更新，**明确提到要包含公司行业（industry）**。

### 3.2 Company Description 字段扩展
- 公司描述字段的**字符上限显著提高**，足够支持一段有意义的、多句子的公司描述（具体上限待开发输入确认）；
- 新增 **helper text 或 placeholder**，引导用户填写哪些内容，示例：
  
  > "Describe what your company does, who your customers are, and what makes you unique."

### 3.3 Layer 1 记忆文件同步
- AI Chatbot 为该公司**首次初始化**时，更新与扩展后的公司描述**自动写入** Layer 1 记忆文件；
- 用户后续在 Company Settings 中**更新该字段**时，记忆文件**反映该修改**。

### 3.4 移动端响应式
- 功能需为移动端响应式，桌面端与移动端均完全可用。

---

## 四、操作流程

### 4.1 用户编辑（用户 → Company Settings）
1. 用户进入 Company Settings；
2. 看到 Company Description 字段：
   - 字段附 helper text 或 placeholder 指导内容（包含 industry 与示例性建议）；
   - 字段支持显著更高的字符上限；
   - 字段周围标签或 helper text 把目的与 AI Chatbot 关联起来（例如 "Help your AI assistant understand your business"）；
   - 可显示字符计数指示器，让用户了解还剩多少空间；
3. 用户填写或更新描述（建议包含公司行业）；
4. 保存。

### 4.2 AI Chatbot 初始化（系统）
5. 当 AI Chatbot **首次**为该公司初始化时，系统读取 Company Settings 中的字段（类型、阶段、扩展后的公司描述）；
6. 将扩展后的公司描述写入该公司的 **Layer 1 记忆文件**。

### 4.3 用户后续修改 → 记忆文件同步（系统）
7. 用户更新 Company Description 字段并保存；
8. 系统将更新内容同步至 Layer 1 记忆文件，保持记忆与设置一致。

---

