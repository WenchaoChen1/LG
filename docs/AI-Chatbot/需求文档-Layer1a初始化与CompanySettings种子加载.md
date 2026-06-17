# 需求文档：Company Memory File Layer 1a 后端 — 初始化与 Company Settings 种子加载

**来源任务**：Company Memory File Layer 1a Backend - Initialization & Company Settings Seeding
**Asana 链接**：https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1214913562391185
**适用模块**：AI Chatbot Layer 1a 后端 — 公司记忆文件的创建与种子信息
**类型**：后端与数据架构需求（**无用户可见 UI**）

---

## 一、背景与范围

本需求覆盖每家公司的 **Layer 1a 记忆文件**的**创建**与**种子信息**。

当 AI Chatbot 为某家公司首次初始化时：
- 系统必须**自动创建**该公司的 Layer 1a 存储；
- 并使用 **Company Settings** 中所有可用的结构化数据**种子信息**，包括公司名称、描述、商业模式、行业、阶段以及 LG 中存在的其他公司档案字段。

这样可以让 AI 在与该公司的**第一次对话**之前就已经具备有意义的基线理解，**无需用户任何输入**。

当 Company Settings 字段在之后被更新时，记忆文件必须**自动同步**该变化。

**注**：当后续 consultative onboarding epic 上线时，若公司实体在 onboarding 期间被创建，Layer 1a 的**种子信息**可能需要在 onboarding 流程中完成（因为彼时可能会收集到 Company Settings 结构化字段之外的关于公司的附加信息）。

---

## 二、功能描述

### 2.1 记忆文件创建（自动）

- **功能上线时（Backfill）**：为**所有已存在的公司**自动创建并播种一份 Layer 1a 记忆文件；
- **上线后**：对于**每家新创建的公司**，在**公司创建之时**自动创建一份 Layer 1a 记忆文件；
- 整个机制**无需用户配置**即可生效，记忆文件**自动运行**。

### 2.2 初始化时的种子字段

初始化时，记忆文件用 Company Settings 中所有可用的元数据种子信息，**至少**包括以下字段：

| 字段 | 说明 |
|---|---|
| **Company Name** | 公司名称 |
| **Company Overview** | 公司综述 |
| **Business Model** | 从 Company Overview 中提取 |
| **Industry** | 从 Company Overview 中提取 |
| **Stage** | 公司阶段 |
| **Type** | 公司类型 |
| **Company Status** | 公司状态 |
| **URL Scraping（Company URL 字段）** | 见下方 2.3 |

### 2.3 URL Scraping（基于公司官网的学习）

- **初始化时**，AI 抓取（scrape）公司官网以学习公司情况；
- 抓取范围覆盖**官网的所有页面**，不仅仅是首页；
- AI 沿着与 **Layer 1a 聊天派生记忆所用相同的类别维度**提取信息，例如：
  - Company facts（公司事实）；
  - ICP；
  - Competitive landscape（竞争格局）；
  - Value proposition（价值主张）；
  - Business & pricing model（商业与定价模式）；
  - 等等；
- 抓取结果以**结构化理解**的形式存储，**不是**原始页面内容存储；
- **触发时机**：
  - 初始化时触发一次；
  - 当 Company Settings 中的 **Company URL** 字段被**新增、更新或删除**时**重新触发**；
  - 系统还需**主动监控官网内容变化**，并基于官网内容变化**自动更新**记忆。

### 2.4 学习 vs 存储（理解的本质）

- AI Chatbot **不是**简单地"存储字段值"——它是基于这些档案字段产生**理解**（understandings）后写入记忆文件；
- 例如，URL 字段并非作为字符串存储，而是被 Chatbot 用来**抓取/学习**公司情况。

### 2.5 字段更新的自动同步

- 当用户更新 Company Settings 中**任意字段**时，**对应的** Layer 1a 记忆条目**自动更新**；
- 记忆文件全程**自动运行**，无需用户配置或操作来激活。

### 2.6 访问控制（架构支持）

架构必须支持依赖 UI 需求所要求的访问控制模型：
- **Company Admin**：对**自己公司**的 Layer 1a 拥有**只读**访问权；
- **Portfolio Manager**：对**其访问范围内的所有公司**的 Layer 1a 拥有**只读**访问权。

---

## 三、数据来源

| 数据项 | 来源 |
|---|---|
| Company Name / Stage / Type / Status | Company Settings 既有字段（直接读取） |
| Company Overview | Company Settings 既有字段（直接读取） |
| Business Model | 由 Company Overview 提取派生 |
| Industry | 由 Company Overview 提取派生 |
| Company URL | Company Settings 既有字段 |
| 公司官网内容 | AI 抓取公司官网全部页面 |
| 官网衍生的类别化理解 | AI 基于抓取内容按 Layer 1a 类别维度结构化生成 |

---

## 四、范围边界

| 内容 | 是否在本需求内 |
|---|---|
| Layer 1a 记忆文件**首次创建** | ✅ 在 |
| 用 Company Settings 元数据**初始播种** | ✅ 在 |
| 公司官网抓取与基于变化的自动更新 | ✅ 在 |
| Company Settings 字段更新后的自动同步 | ✅ 在 |
| Backfill：为所有已有公司创建并播种 | ✅ 在 |
| 用户可见 UI | ❌ 不在（无 UI） |
| 聊天对话的实时增量提取 | ❌ 不在（由 Chat Extraction 系列需求处理） |
| 文档上传带来的记忆条目 | ❌ 不在（由 Document Upload 需求处理） |
| consultative onboarding 流程中的初始化 | ⏳ 注：未来该 epic 上线时需要在该流程中初始化 |

---


