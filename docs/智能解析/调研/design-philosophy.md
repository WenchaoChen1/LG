# OCR Agent 设计理念

> **定位**: 这不是一份技术实现文档，而是一份**设计宣言** — 解释每一个决策背后的"为什么"。
> **读者**: 工程团队、产品负责人、以及未来加入第二个 Agent 时想知道"为什么这样做"的人。
> **关联文档**: [技术设计](./technical-design.md) · [需求分析](./requirement-analysis.md) · [代码示例](./code-examples.md)

---

## 一、核心论点

**财务数据太重要了，不能全自动处理；但又太繁琐，不能全手工录入。OCR Agent 存在于这两个极端之间的精确位置。**

这个系统不是"一个帮你处理文档的 AI"。它是一个**结构化工作流**：AI 处理苦力活（提取、分类），人类处理判断（审核、纠正、确认）。所有架构决策都源自这个分工。

---

## 二、六项设计原则

### 原则 1：确定性优先于智能

> 当问题空间有界时，优先使用确定性、可审计的逻辑，而非 AI。

**为什么在财务数据场景下这很重要：**

- 财务分类遵循规则。"Accounts Receivable" 永远映射到 AR。用 LLM 做这件事就像用神经网络做加法 — 技术上可行，但不必要地昂贵且不可预测。
- 审计人员需要追溯每一个映射决策。"关键词匹配了 Priority 1 的 AP 规则"是可审计的。"Claude 觉得它像 AP"是不可审计的。

**在架构中的体现 — 三层映射引擎：**

```
Layer 1: 规则引擎 (关键词+优先级)    覆盖 ~60%    零成本    完全可审计
Layer 2: 公司记忆 (DB 查询)          覆盖 ~25%    零成本    完全可审计
Layer 3: LLM 推理 (Claude Sonnet)    覆盖 ~15%    有成本    部分可审计
```

85% 的行项**不需要任何 AI 调用**。LLM 只处理规则和记忆都覆盖不了的长尾。

**直接解决的问题：**

需求中 `hosting`/`cloud`/`server` 同时出现在 COGS 和 R&D 关键词列表中（原始需求的 P0 问题）。这不是 LLM 判断的问题 — 这是一个确定性规则：检查公司是否为 SaaS（从 company 元数据），走对应的优先级分支。元数据缺失？标记 LOW confidence 交给人审核，而不是让 AI 猜。

同理，Payroll 无部门上下文时**不应**静默默认为 G&A Payroll。将无上下文的 Payroll 默认归入 G&A 会系统性地扭曲 Benchmark 中的部门薪酬分布（经财务领域审查确认）。正确做法：标记 LOW confidence + 要求用户审核，让人类根据实际上下文判断归属部门。

**接受的 trade-off：** 规则引擎无法覆盖新出现的财务术语。没关系 — 新术语正是 LLM 推理的价值所在，也正是最需要人工审核的场景。

---

### 原则 2：Agent 拥有自己的边界

> Agent 是自包含的单元：自己的状态、自己的记忆、自己的模型选择、自己的失败模式。Agent 之间没有共享可变状态。

**为什么这很重要：**

- OCR Agent 是第一个 Agent，但 Chat Agent 和 RAG Agent 已在路线图上。如果第一个 Agent 泄漏了抽象边界，后续每个 Agent 都会继承这笔技术债。
- 财务处理 session 可能持续几分钟到几小时（用户上传、离开、回来审核）。Agent 必须独立管理自己的生命周期。

**在架构中的体现：**

| 边界 | 实现 | 解决的问题 |
|------|------|-----------|
| **状态** | LangGraph checkpoint → PostgreSQL | 用户关浏览器后可恢复（解决 P1 错误恢复问题） |
| **记忆** | `ai_ocr_*` 表前缀隔离 | Chat Agent 来了用 `ai_chat_*`，互不干扰 |
| **模型** | OCR Agent 自己选 Gemini Flash/Claude | Chat Agent 可以用 GPT-4o，互不关心 |
| **接口** | 5 个标准 Tool | 今天前端调，明天 Orchestrator 调，零重构 |

**核心洞察：**

> "框架从具体 Agent 中长出来，而不是先造框架再往里填 Agent。"

这不是一句空话。这是对"先搭多智能体框架"这个常见错误的明确拒绝。你无法为不存在的 Agent 设计编排层 — 你会猜错抽象。

**接受的 trade-off：** 严格的边界意味着我们不能做跨 Agent 优化（比如 Chat Agent 理论上可以复用 OCR Agent 的上下文）。我们接受这一点，因为过早的 Agent 耦合比轻微的上下文冗余代价高得多。

---

### 原则 3：AI 成本是产品决策，不是事后优化

> 每一次 LLM 调用都必须有成本正当性。架构应让"无需 AI"的路径最快最便宜。

**为什么这很重要：**

- 单次上传估算 ~$0.02（10 页 PDF，~80 行数据）。听起来很小，但 500 家 portfolio 公司每月上传 = $10/月的提取成本，且随文档量线性增长。
- 更重要的是：每次 LLM 调用都增加延迟、不确定性和故障点。减少调用不仅是成本问题 — 是可靠性问题。

**在架构中的体现 — 模型路由策略：**

```
任务               模型                成本           理由
──────────────────────────────────────────────────────────
文档提取(页→表)    Gemini 2.5 Flash    $0.15/1M      视觉任务，速度 > 深度推理
文档类型识别       Gemini 2.5 Flash    $0.15/1M      有界分类，不需要开放推理
账户映射(LLM层)    Claude Sonnet 4     $3.00/1M      需要财务推理和上下文判断
Embedding          text-embedding-3    $0.02/1M      商品化操作
```

三层映射意味着 85% 的行从不触及 LLM。剩余 15% 走 LLM 的也通过批量处理（一次 API 调用处理多行）进一步降低成本。

**接受的 trade-off：** 我们用 OpenRouter 作中间层，增加了微小的成本溢价。我们接受这一点，因为无需改代码即可切换模型的能力（比如 Google 涨价或 Anthropic 发布更便宜的模型）比微小的成本增加更有价值。

---

### 原则 4：人工审核不可协商

> 没有任何财务数据可以绕过人工确认直接进入 LG 数据库。系统提议，人类裁决。

**为什么这很重要：**

- 这是用于投资决策的财务数据。Revenue 或 COGS 中的一个错误数字会级联到错误的 Benchmark、错误的 Forecast、以及可能错误的投资建议。
- LG 已有的标准化管道（Normalization → Benchmark → Forecast）意味着 OCR 输入的坏数据会**毒化所有下游输出**。

**在架构中的体现：**

LangGraph 状态机中有一个显式的 `REVIEW` 状态。系统**不能**从 REVIEW 转换到 COMMIT 而不经过用户操作。这不是 UI 便利 — 这是状态机层面的架构不变量。

```
... → VALIDATE → REVIEW → COMMIT
                    ↑
              人工操作是唯一
              从 REVIEW 出去的路
```

**并排审核页面是故意设计为最复杂的前端组件：**

- 左面板：原始文档（事实）
- 右面板：AI 提取结果（声明）
- 用户的工作：验证声明是否符合事实

每个映射结果都带 `source` 字段（`RULE_ENGINE` / `COMPANY_MEMORY` / `LLM`）和 `confidence` 字段。这不是调试工具 — 这是面向用户的**信任信号**，帮助审核者分配注意力：
- RULE_ENGINE + HIGH → 看一眼
- LLM + LOW → 仔细检查

**验证是分层的（解决原始需求"验证太弱"的 P2 问题）：**

| 验证层 | 行为 | 示例 |
|--------|------|------|
| 硬验证（阻止提交） | 三要素必须完整 | Account Name / Value / Month |
| 软警告（提醒不阻止） | 财务逻辑检查 | BS 不平衡、P&L 加总不符、重复周期、币种冲突 |
| 用户清理 | 删除噪音行/列 | 系统信任人类对"什么是噪音"的判断 |

**接受的 trade-off：** 完整的人工审核增加了工作流时间。10 页 PDF / 80 行数据可能需要 10-15 分钟审核。我们接受这一点，因为替代方案（自动提交 + 事后纠正）对财务数据来说风险太大。

---

### 原则 5：记忆优于训练

> 系统通过积累记忆（示例、修正、模式）改进，而不是通过模型训练或微调。

**为什么这很重要：**

| 维度 | Fine-tuning | 记忆（Few-Shot 注入） |
|------|-------------|---------------------|
| 反馈生效 | 小时/天（需重训） | **即时**（下次上传就用） |
| 成本 | GPU 训练 + 模型托管 | Prompt 多几百 token |
| 可审计 | 黑盒（不知道学了什么） | **完全透明**（知道用了哪些案例） |
| 回滚 | 回退模型版本 | **删除错误记忆即可** |
| 多公司隔离 | 需要多个 adapter | **天然隔离**（按 company_id 查询） |

**在架构中的体现 — 直接解决"持续学习 story 太空泛"的 P2 问题：**

把原始需求中的"incremental learning"和"new document recognition"**重新定义**为：

```
写入路径（用户确认映射后）：
  1. 写入 ai_ocr_company_mapping_memory → 精确标签到分类的关联（DB）

读取路径（下次上传时）：
  1. Layer 2 查 DB → 精确匹配 / trigram 模糊匹配（零 LLM 调用）
  2. Layer 3 查同行业 SQL 频率统计 → 注入到 LLM prompt 的 Few-Shot 示例（非向量检索）

学习闭环：
  第 1 次上传: "AWS Infrastructure" → LLM 推理 → COGS (MEDIUM) → 用户确认 → 存记忆
  第 2 次上传: "AWS Infrastructure" → DB 精确匹配 → COGS (HIGH) → 零 LLM 调用
  第 3 次上传(不同公司): "Cloud Infra" → 同行业 SQL 频率查询 → 注入 Few-Shot → LLM 推理更准
```

**记忆质量控制：**

| 风险 | 防御 |
|------|------|
| 错误记忆污染 | `frequency < 3` 的标记 provisional，不参与 Few-Shot |
| 记忆膨胀 | TTL 12 个月，未使用的自动归档 |
| Few-Shot 过长 | 限制 ≤ 20 条公司记忆 + ≤ 10 条全局记忆 |
| 公司间泄漏 | DB 按 company_id 隔离；跨公司查询只返回 lg_category，不暴露原始 label |

**版本追踪是双轨的：**
- `core_engine_version`（如 "v1.3"）：通用规则变更
- `company_memory_version`（如 "mem-abc123"）：公司记忆快照 hash

这使得可以回答：*"6 个月前处理这个文档时，用的什么规则和什么记忆？"*

**接受的 trade-off：** Few-Shot 注入增加了 prompt 长度（和成本），而 fine-tuned 模型可以"天生就知道"。我们接受这一点，因为在财务场景下，透明度（知道哪些案例影响了映射）比边际成本节省更重要。

---

### 原则 6：为今天的 Agent 构建，为明天的系统留接口

> 不要构建多智能体框架。构建一个优秀的 Agent，用干净的接口让框架自然浮现。

**为什么这很重要：**

- LG 路线图包含 Chat Agent、RAG Agent、Analysis Agent。很诱人想现在就设计"Agent 编排层"。
- 但你不能为不存在的 Agent 设计编排层。你会猜错抽象。

**在架构中的体现 — 三阶段演进：**

```
Phase 1（当前）               Phase 2                    Phase 3
────────────                 ──────────                 ──────────
OCR Agent 独立运行            + Chat Agent               + Orchestrator
前端直接调用 Tool 接口        Chat Agent 调用 OCR Tool    Supervisor 路由到各 Agent
                              + RAG Agent
                              pgvector + 自建检索管道
```

**LangGraph 是天然的"从 Agent 到 Multi-Agent"桥梁：**

```python
# 现在：OCR Agent 独立编译运行
ocr_graph = StateGraph(OCRPipelineState)
ocr_graph.add_node("extract", extract_node)
ocr_graph.add_node("map", map_node)
ocr_app = ocr_graph.compile()

# 未来：直接塞进 Supervisor 当一个节点
supervisor = StateGraph(SupervisorState)
supervisor.add_node("ocr", ocr_app)      # ← 零重构
supervisor.add_node("chat", chat_app)
supervisor.add_node("rag", rag_app)
```

**共享基础设施按约定隔离：**

| 基础设施 | OCR Agent | Chat Agent（未来） | RAG Agent（未来） |
|----------|-----------|-------------------|-------------------|
| PostgreSQL | `ai_ocr_*` 表 | `ai_chat_*` 表 | `ai_rag_*` 表 |
| pgvector | — | — | 文档 embedding |
| OpenRouter | Gemini + Claude | 对话模型 | Embedding |
| LangGraph checkpoint | 按 thread_id 隔离 | 按 thread_id 隔离 | 按 thread_id 隔离 |

**接受的 trade-off：** 第二个 Agent 到来时，我们可能发现某些 Tool 接口定义不够好。我们接受这一点，因为重新设计一个 Tool 接口是一天的工作量；重新设计一个过早的编排框架是一个月的工作量。

---

## 三、原始需求问题与对应解决策略

| 问题 | 级别 | 对应原则 | 解决策略 |
|------|------|----------|----------|
| OOE 计算指标 vs 映射目标矛盾 | P0 | 原则 1 (确定性) | 写入 `other_income`/`other_expense` 独立字段，OOE 计算留给下游标准化引擎 |
| 关键词冲突 (hosting/cloud) | P0 | 原则 1 (确定性) | 5 级优先级规则引擎 + company industry 元数据 + LOW confidence 兜底 |
| 多页 PDF 切分规则缺失 | P1 | 原则 4 (人工审核) | AI Vision 按页独立分类，歧义页标 MISC，用户在审核中修正 |
| 错误恢复机制缺失 | P1 | 原则 2 (Agent 边界) | LangGraph checkpoint → PostgreSQL，每个状态转换都持久化 |
| 数据校验规则太弱 | P1 | 原则 4 (人工审核) | 硬验证（阻止） + 软警告（提醒） 两层分离 |
| 持续学习 story 太空泛 | P2 | 原则 5 (记忆 > 训练) | 重定义为公司记忆 + 同行业 SQL 频率查询 Few-Shot，不做模型训练 |
| 安全合规缺失 | P2 | 原则 2 (Agent 边界) | MIME 校验 + XXE 防御 + LLM 注入防护 + S3 加密 |
| 权限模型漏洞 | P2 | 原则 4 (人工审核) | Gateway JWT + Python 端 company_id 二次校验 + 审计日志 |
| Mobile 审核不现实 | P3 | 务实裁剪 | 上传页 Mobile，审核页 Desktop Only |
| 时间线不现实 | P3 | 原则 6 (渐进演进) | 4 Phase 分期，Excel MVP 先行验证 Pipeline |

---

## 四、关于关键技术选择的立场

### AI Vision 替代传统 OCR（eSapiens）

传统 OCR 提取字符。AI Vision **理解**文档。区别在于：
- 无边框表格：OCR 需要复杂的后处理规则 → Vision 直接理解
- Section 上下文："R&D" 段落下的 "Salary" → Vision 知道这是 R&D Payroll
- 数值格式：`(1,234)` = -1234 → Vision 理解财务惯例
- 多页上下文：跨页的表格 → Vision 可以关联

成本也是一边倒的：Gemini Flash 处理 10 页 ~$0.01，vs OCR 服务 $0.10-0.50，且质量更差。

我们不是反 OCR。如果 Vision 模型能力退化，OpenRouter 让我们秒级切换。如果新的专业财务 OCR 模型出现，我们可以把它接入 LangGraph Pipeline 的 Extract 节点。Pipeline 天然是模型无关的。

### Instructor + Pydantic 替代 LangChain Parser

传统 LLM 输出流程：调用模型 → 获取文本 → 解析文本 → 验证输出 → 处理解析错误。五步中三步可能静默失败。

Instructor 将其压缩为：用 Pydantic schema 调用模型 → 获取验证过的对象。验证失败时，Instructor 自动将验证错误信息反馈给模型重试。`max_retries=3` 意味着模型有三次机会产生有效输出。

对财务数据来说，"偶尔产生畸形 JSON"是不可接受的。

### pgvector 替代专用向量数据库（含 RAG 阶段立场）

ChromaDB 和 Pinecone 是更好的向量数据库。但我们不需要它们的优势。

**OCR 阶段（当前）：不使用向量数据库。** 映射记忆的检索用 `pg_trgm` + SQL 精确/模糊匹配即可覆盖。Few-Shot 示例通过同行业 SQL 频率查询获取，无需 embedding 检索。

**RAG 阶段（未来）：使用 RDS PostgreSQL + pgvector，自建检索管道。** 不使用 Bedrock Knowledge Bases。原因：

| 维度 | Bedrock Knowledge Bases | pgvector + 自建管道 |
|------|------------------------|-------------------|
| 分块策略 | 固定/重叠分块，不可定制 | **完全控制**（按文档结构、表格边界、章节语义分块） |
| 召回路径 | 单路径向量检索 | **多路径**（向量检索 + 关键词 BM25 + 元数据过滤，混合召回） |
| Re-ranking | 不支持或有限支持 | **自定义 re-ranking**（Cross-encoder、业务规则加权） |
| 元数据过滤 | 基础过滤 | **精细过滤**（company_id、报表类型、fiscal_year、数据来源） |
| 调试透明度 | 黑盒，无法检查召回中间结果 | **完全透明**（每步可 log、可 trace、可 A/B 测试） |
| 基础设施 | 额外 AWS 服务 + 额外成本 | **零额外基础设施**（复用现有 RDS PostgreSQL） |

RAG 阶段**真正需要的**是事务一致性：文档 embedding 和业务元数据在同一个数据库事务中写入。pgvector（同一个 PostgreSQL 实例）天然支持，外部向量数据库需要分布式事务协调。RDS PostgreSQL 已由 AWS 托管，pgvector 扩展开箱即用，零额外运维。

自建管道的核心组件：自定义 chunking → embedding（OpenAI text-embedding-3）→ pgvector 存储 → 混合召回（向量 + BM25 + 元数据）→ Cross-encoder re-ranking → 上下文注入。每一层都可独立替换和调试。

如果未来有百万级 embedding 需要亚毫秒搜索，我们可以迁移。抽象边界（一个接收标签返回相似映射的函数）不变。

### LangGraph 替代"纯 FastAPI 端点"

合理的反对意见："OCR Pipeline 就是 5 个顺序步骤，为什么不用 FastAPI 端点 + 数据库状态列？"

因为 Pipeline **不是** 5 个顺序步骤。它是一个状态机：
- 条件分支（验证失败走不同路径）
- 人工暂停（Pipeline 在 REVIEW 停下来等用户）
- 故障恢复（任何节点失败需要从上一个成功节点恢复）
- 可组合性（Pipeline 未来变成更大状态图的一个节点）

你可以用 FastAPI + 状态列 + 大量 if/else 实现所有这些。你最终会得到一个自制的、未测试的、未文档化的状态机。或者你可以用 LangGraph，获得内置的可视化、持久化、恢复和可组合性。

LangGraph 的开销是一个依赖。自制状态机的开销是永远的维护。

---

## 五、我们明确不做的事

| 不做 | 原因 |
|------|------|
| 通用文档处理平台 | 只处理 LG 的 19 类财务报表。不做发票、合同、税表。范围蔓延会破坏所有优化。 |
| 实时系统 | 10 页 PDF 需要 10-15 秒。没关系。用户偶尔上传，不是每秒上传。优化到 5 秒以下的成本 10 倍于 UX 改善。 |
| AI-first 系统 | AI 是在规则失败时使用的。如果我们能写覆盖 100% 行项的规则，我们根本不会用 AI。AI 处理长尾，不是主角。 |
| 多智能体框架 | 我们在做一个 Agent。框架会在第二个 Agent 证明了什么通信模式是真正需要的之后浮现。 |

---

## 六、衡量成功的指标

| 指标 | 目标 | 为什么是这个数字 |
|------|------|-----------------|
| 规则引擎覆盖率 | ≥ 60% 行项 | 低于此，LLM 调用太多，成本和延迟飙升 |
| 公司记忆命中率（第 2 次+上传） | ≥ 80% | 低于此，学习系统没有在工作 |
| AI 成本/次上传 | < $0.05 | 高于此，规模化时单位经济不成立 |
| 审核到提交时间 | < 15 分钟 (10 页) | 高于此，手动录入更快，用户不会采用 |
| 映射准确率（AI 建议） | ≥ 90% (人工审核前) | 低于此，用户失去信任，什么都手动改 |
| Session 恢复率 | 100% (浏览器关闭后) | 任何数据丢失对财务工作流不可接受 |
