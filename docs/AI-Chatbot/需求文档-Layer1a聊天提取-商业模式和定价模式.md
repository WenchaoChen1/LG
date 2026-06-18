# 需求文档：Company Memory File Layer 1a 后端 — 聊天信息提取：商业模式与定价模式

**来源任务**：[Asana LG-1425](https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1215298512189418)

**UI 需求**：无（纯后端 / 数据架构 Story）

---

## 一、背景与业务目标

本需求覆盖从公司侧（Company-side）聊天对话中，**实时、增量式**地提取**商业模式（Business Model）与定价模式（Pricing Model）上下文**。理解一家公司**如何赚钱**以及**如何为产品定价**，是后续 AI 与该创始人开展每一次战略对话的**基础性上下文**。

- 一家正在从服务模式转向 SaaS 模式的公司，或正在从按席位定价转向按用量定价的公司，所处的运营语境与一家具有稳定既有模式的公司**根本不同**。
- AI 必须**智能地将这种上下文带入后续对话**。

### 商业模式（Business Model）上下文
- 包含公司创造收入的根本结构：**SaaS、Marketplace、Services、Hybrid 模型**，或创始人描述的其他任何结构。

### 定价模式（Pricing Model）细节
- 包含产品的销售与计费方式：**按席位（seat-based）、按用量（usage-based）、按价值（value-based）、软件捆绑服务（services bundled with software）、按交易（transaction-based）**，或对话中提及的其他任何定价机制。

二者皆为**长期持久（long-lived, staying-power）**的信息，**在数月乃至数年的对话中持续相关**，正是一位 Portfolio Manager 会从一次会议带到下一次会议的那种上下文。

### 模式转型（Model Transition）的识别
- 系统必须识别并提取**商业或定价模式正在变化或转型**的情况。
  - 例：创始人说"我们正从项目制计费转向订阅制循环收费。"
- 这是**关键战略上下文**，将影响 AI 后续如何解读财务指标、对标基准与增长轨迹。
- 模式转型用于**更新已有条目**，**而非**创建相互冲突的重复条目。

### 提取节奏
- 提取为**实时、增量式**：在**每条用户消息与 AI 回复交互**发生时即评估并提取合格信息，**在上下文完整可用时立即处理**，不等待会话结束或闲置期。
- 提取处理**异步运行**，**不阻塞或延迟** AI 回复的下发。

---

## 二、功能需求

### 1. 提取触发机制（Extraction Trigger）
- 提取为**实时、增量式**：在每次消息交互时评估。
- **异步处理**，不阻塞 AI 回复的下发。

### 2. 商业模式提取（Business Model Extraction）

- 系统在对话中浮现商业模式上下文时，正确识别并提取，包括但不限于：
  - **SaaS**
  - **Marketplace**
  - **Services**
  - **Hybrid**
  - **Transactional**
  - **Platform**

- 商业模式描述以 **Layer 1a 记忆条目**形式存储，包含：
  - **Source Type**：chat extraction
  - **Timestamp**：时间戳

- 关于商业模式**演变或转型**的陈述，提取后**更新已有的商业模式记忆条目**，使其反映最新理解。

- **泛泛或模糊的陈述**（未能清晰描述商业模式的）**不予提取**。

### 3. 定价模式提取（Pricing Model Extraction）

- 系统在对话中提及定价模式细节时，正确识别并提取，包括但不限于：
  - **按席位（Seat-based）**
  - **按用量（Usage-based）**
  - **按价值（Value-based）**
  - **软件捆绑服务（Services bundled with software）**
  - **交易费（Transaction fees）**
  - **Freemium**

- 定价模式细节以 **Layer 1a 记忆条目**形式存储，包含：
  - **Source Type**：chat extraction
  - **Timestamp**：时间戳

- 定价模式的**转型或变更**提取后用于**更新已有的定价模式记忆条目**。

- 创始人提及的**量化定价细节**（例如近似价格点、合同金额等）在提供时予以提取，作为未来战略对话的有用上下文。

### 4. 冲突与更新处理（Conflict and Update Handling）
- 当新信息更新或取代了先前的战略上下文条目时，**更新原条目**以反映当前理解。
- **任何战略上下文的最新版本始终作为权威版本。**

### 5. 性能与错误处理（Performance and Error Handling）
- 提取失败**写入日志**，不向用户暴露任何错误。
- 即使某次提取事件失败，**Chatbot 仍正常工作**。

---
