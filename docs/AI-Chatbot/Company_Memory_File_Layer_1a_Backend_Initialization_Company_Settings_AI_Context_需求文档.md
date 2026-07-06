# 需求文档：Company Memory File Layer 1a Backend – Initialization & Company Settings AI Context

## 一、业务背景与目标

本故事覆盖两件事：
1. 为每家公司**创建 Layer 1a Memory 文件**（不做初始 seeding）；
2. 将 **Company Settings** 数据作为 **AI 运行时上下文（runtime context）** 接入 AI Chatbot。

即：Company Settings 中的字段（Company Name、Overview、Business Model、Industry、Stage、Type、Status 及其他 Profile 字段）**仅在运行时喂给 AI 用于生成回复**，**不写入 Layer 1a Memory 文件**，也**不通过 Memory 文件展示给任何用户**。当 Company Settings 字段更新时，AI 的上下文自动反映最新值，但 Memory 文件不会为此新增或更新任何条目。

对公司端用户隐藏的字段（**Company Type、Company Status**）不得通过任何方式（包括 AI 回复）暴露给公司端用户。

> Note：未来 consultative onboarding epic 建成后，如果公司实体是在 onboarding 阶段创建的，Layer 1a Memory 文件的初始化可能需要在该 onboarding 流程中完成，因为届时可能会获取到 Company Settings 结构化字段之外的公司信息。

---

## 二、范围与边界

### 2.1 本故事范围内
- Layer 1a Memory 文件的**创建**（存量 backfill + 新建公司即时创建）。
- Company Settings **作为 AI 运行时上下文**的接入与更新联动。
- 通过 Company URL 抓取公司网站，形成结构化理解，作为 AI 运行时上下文。
- 支撑后续 UI 故事所依赖的访问控制架构。

### 2.2 明确不在本故事范围内
- **不做 Memory 文件初始 seeding**：Company Settings 数据不写入 Layer 1a Memory 文件。
- **无用户可见 UI**：本故事为后端与数据架构，不含前端展示。
- Chat 抽取内容写入 Memory（属其他故事/后续版本）。

---

## 三、功能需求（验收标准）

### 3.1 Layer 1a Memory 文件的创建
1. **存量 backfill**：功能上线时，为**所有已存在的公司**自动创建一份 Layer 1a Memory 文件。
2. **增量创建**：上线之后，**新建公司时**在公司创建的同一时刻自动创建其 Layer 1a Memory 文件。
3. 创建过程**不需要用户任何配置**，系统自动执行。
4. **不做 seeding**：创建时不将 Company Settings 数据写入该 Memory 文件。

### 3.2 Company Settings 作为 AI 运行时上下文
Company Settings 中以下字段**仅作为 AI 的运行时上下文**提供，不写入 Memory 文件、不通过 Memory 文件暴露给任何用户：

| 字段 | 说明 |
|---|---|
| Company Name | 公司名称 |
| Company Overview | 公司概览 |
| Business Model | 从 Company Overview 中抽取 |
| Industry | 从 Company Overview 中抽取 |
| Stage | 公司阶段 |
| **Type** | 仅作 AI 上下文；**在 AI 回复中不得向公司端用户透露** |
| **Company Status** | 仅作 AI 上下文；**在 AI 回复中不得向公司端用户透露** |
| Company URL | 触发网站抓取；抓取所得作为运行时上下文 |

### 3.3 Company URL 网站抓取
1. **初始化时抓取**：在初始化阶段，AI 抓取公司网站，用于形成对公司的理解。
2. **抓取范围**：**覆盖网站的所有页面**，而不仅是首页。
3. **抽取维度**：按与 Layer 1a chat-derived memory 相同的类别维度进行抽取，例如：
   - Company Facts（公司事实）
   - ICP（理想客户画像）
   - Competitive Landscape（竞争格局）
   - Value Proposition（价值主张）
   - Business & Pricing Model（商业与定价模式）
   - 等
4. **形成结构化理解**：抽取产物为结构化理解，**不存储网页原始内容**。
5. **仅作运行时上下文**：抓取所得**不写入 Memory 文件**，仅在运行时提供给 AI。
6. **触发条件**：
   - 初始化时触发一次；
   - 每当 Company Settings 中的 **Company URL 字段被新增、修改或移除**时重新触发抓取；
   - 系统还需**主动监控网站内容变更**，并在网站内容变化时自动更新（auto-update）。

### 3.4 AI 使用逻辑
- AI 使用 Company Settings 字段值 + URL 抓取形成的结构化理解，作为**响应生成的上下文（context）**。
- AI 使用的是"理解"，而不仅是原始数据本身。
- 上述内容**运行时使用，不持久化**为 Memory 文件条目。

### 3.5 Company Settings 变更联动
- 当任何 Company Settings 字段被用户更新：
  - **AI 上下文中该字段的值自动更新为最新值**；
  - **不会**在 Memory 文件中新建或更新任何对应条目（Company Settings 从不被存入 Memory 文件）。

### 3.6 敏感字段暴露控制
- **Company Type** 与 **Company Status** 对公司端用户在 UI 中不可见；
- AI 在其对公司端用户的回复中**也不得**透露这两个字段的取值或存在。

### 3.7 访问控制架构支撑
- 架构层需支撑后续依赖 UI 故事所需的访问控制模型：
  - **Company Admin**：只读访问其**本公司**的 Layer 1a。
  - **Portfolio Manager**：只读访问其**权限范围内的公司**的 Layer 1a。

### 3.8 未来扩展（说明，不在本故事实现范围）
- 当 consultative onboarding epic 上线后，Company Memory File 需要在 onboarding 工作流中完成初始化。本故事不实现该工作流，仅需注意架构上不阻碍未来演进。

---

## 四、UX 设计说明
- 本故事为**后端与数据架构**，**无用户可见 UI**。

---

## 五、业务闭环说明
1. **文件创建闭环**：上线时对存量公司统一创建 Layer 1a 文件（backfill）；上线后新建公司在创建时刻自动创建 Layer 1a 文件，无需用户配置。
2. **上下文构建闭环**：AI 初始化时读取 Company Settings 字段 + 抓取公司 URL 的全站内容 → 抽取结构化理解 → 组装为运行时上下文。
3. **变更同步闭环**：Company Settings 字段变更 → AI 上下文自动更新为新值；Company URL 变更或网站内容变更 → 自动重新抓取并刷新上下文；Memory 文件不因此产生或更新任何条目。
4. **数据隔离闭环**：Company Settings 数据仅作运行时上下文使用，永不写入 Memory 文件，永不通过 Memory 文件暴露给用户；Company Type 与 Company Status 在面向公司端用户的 AI 回复中始终被隐藏。
5. **权限支撑闭环**：底层架构预留 Company Admin（本公司只读）与 Portfolio Manager（权限范围内公司只读）两类访问路径，供后续依赖 UI 故事直接使用。
