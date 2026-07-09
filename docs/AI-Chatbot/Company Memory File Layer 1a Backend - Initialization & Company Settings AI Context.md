# 需求文档：公司记忆文件 Layer 1a 后端 —— 初始化与 Company Settings AI 上下文

> Asana Task GID: 1214913562391185
> Task Name: Company Memory File Layer 1a Backend - Initialization & Company Settings AI Context

---

## 一、背景与业务描述

本需求覆盖两部分核心工作：

1. **为每家公司创建 Layer 1a 记忆文件并完成初始化**；
2. **将 Company Settings 数据接入 AI 作为运行时上下文（AI Runtime Context）**。

当 AI 聊天机器人首次为一家公司初始化时，系统须自动创建该公司的 Layer 1a 存储。同时，Company Settings 中的所有可用结构化字段（公司名称、公司概述、业务模式、行业、发展阶段、以及 LG 中存在的其他 profile 字段）须以**运行时上下文**方式提供给 AI，让 AI 从第一次对话起就具备对该公司有意义的基线认知，无需用户任何输入。

关键定位：

- Company Settings 数据（公司名称、概述、业务模式、行业、阶段、类型、状态、以及其他 profile 字段）**作为 AI 生成响应的运行时上下文**；
- Company Settings 数据**不写入** Layer 1a 记忆文件；
- Company Settings 数据**不通过记忆文件向任何用户展示**；
- 若 Company Settings 字段发生更新，更新后的值**反映在提供给 AI 的运行时上下文中**，**不**在记忆文件中创建或更新对应条目。

**敏感字段访问约束：**

- 对公司门户用户不可见的字段（**Company Type** 与 **Company Status**）**绝不允许**在 AI 响应中向公司侧用户暴露。

**关联规划提示：**

- 后续 consultative onboarding 史诗构建时，若公司实体在 onboarding 期间创建，则 Layer 1a 记忆文件的初始化可能需要在 onboarding 流程中完成，因为届时可能会引入 LG Company Settings 结构化字段之外的额外公司信息。

---

## 二、业务逻辑闭环

1. **初始化触发**
   - 功能上线时（Backfill）：为**所有已存在公司**自动创建并初始化 Layer 1a 记忆文件；
   - 上线后：**每新创建一家公司**时，自动创建该公司的 Layer 1a 记忆文件。

2. **上下文注入**
   - 将 Company Settings 中所有可用元数据作为**运行时上下文**提供给 AI；
   - 对 Company URL 字段执行网页抓取，形成结构化理解，同样作为**运行时上下文**注入。

3. **变更同步**
   - 当用户更新任一 Company Settings 字段时，AI 可用上下文中的对应值同步更新；
   - Company Settings 数据不落入记忆文件，因此不涉及记忆条目的写入或修改。

4. **访问控制底座**
   - 架构须支持后续依赖 UI 故事所需的访问控制模型：
     - **Company Admin**：只读访问本公司的 Layer 1a；
     - **Portfolio Manager**：只读访问其访问范围内所有公司的 Layer 1a。

---

## 三、验收标准（Acceptance Criteria）

### 3.1 记忆文件创建

- 功能上线时，为所有已存在公司自动创建并 seeding Layer 1a 记忆文件（backfill）；
- 上线后，每新建一家公司时，在**公司创建时刻**自动为其创建 Layer 1a 记忆文件。

### 3.2 Company Settings 作为运行时上下文

Company Settings 数据以**运行时上下文**方式提供给 AI，**不 seeding 进入记忆文件**。范围包括：

| 字段 | 说明 |
|---|---|
| Company Name | 公司名称 |
| Company Overview | 公司概述 |
| Business Model | 从 Company Overview 中抽取 |
| Industry | 从 Company Overview 中抽取 |
| Stage | 公司发展阶段 |
| Type | **额外约束**：绝不可在 AI 响应中向公司侧用户展示 |
| Company Status | **额外约束**：绝不可在 AI 响应中向公司侧用户展示 |

### 3.3 URL 抓取（Company URL 字段）

- **初始化时**，AI 抓取公司网站以了解公司，抓取范围**覆盖网站全部页面**，而非仅首页；
- AI 按 Layer 1a 中聊天派生记忆所使用的**相同分类维度**（如：company facts、ICP、竞争格局、价值主张、业务与定价模式等）抽取信息，形成**结构化理解**，而不是保存原始页面内容；
- 该结构化理解**仅作为运行时上下文**提供给 AI，**不写入**记忆文件；
- 抓取的触发条件：
  - 初始化时触发；
  - 每当 Company URL 字段**新增、更新或移除**时重新触发；
  - 系统须主动监测网站内容变化，并在变化时自动更新。

### 3.4 AI 的"理解"而非"存储"

- AI 聊天机器人生成的是**从 profile 字段中学到的理解**（例如通过 URL 字段抓取并学习网站内容），而不仅仅是原始数据的存储；
- AI 将 Company Settings profile 字段与 URL 派生的理解**共同作为运行时上下文**用于生成响应；
- 该"学到的理解"用于运行时，**不作为记忆文件条目持久化**。

### 3.5 Company Settings 字段更新

- 用户更新任一 Company Settings 字段时，更新后的值**反映在提供给 AI 的运行时上下文中**；
- **不**在记忆文件中创建或更新对应条目（Company Settings 不存入记忆文件）。

### 3.6 自动化

- 无需任何用户配置即可启用记忆文件功能，系统**自动运行**。

### 3.7 访问控制架构支持

- 架构须支持依赖 UI 故事所需的访问控制模型：
  - Company Admin 对本公司 Layer 1a 的只读访问；
  - Portfolio Manager 对其访问范围内公司 Layer 1a 的只读访问。

### 3.8 关联规划提示

- 当 consultative onboarding 史诗引入时，Company Memory File 须在该工作流中完成初始化。

---

## 四、UX 设计说明

本故事为**后端与数据架构**故事，**无用户可见 UI 在范围内**。
