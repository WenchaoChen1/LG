# AI Chatbot 总体需求

> 本文档基于 EPIC: AI Chatbot 下 18 个 Asana 子任务（LG-1311 / LG-1326 ~ LG-1340 / LG-1381）的最新 Notes + 业务讨论评论，提炼出一份"看一份就够"的整体需求总览。详细 AC 见各任务 `.raw/*.md` 与 `part-*.md`。
>
> 拉取时间：2026-05-12

---

## 1. 一句话目标

为 Looking Glass 构建一个**双角色（Company / Portfolio）、双层知识、租户隔离**的对话式 AI 助手，让创始人与投资团队都能用自然语言访问公司业绩、Benchmark 与 GS Playbook，并通过 Memory File 让 AI 在每次会话中越用越懂这家公司。

---

## 2. 角色矩阵

| 角色 | 入口 | Layer 1a（Company Memory File） | Layer 1b（Portfolio Admin Memory File） | Layer 2（GS Knowledge Base） |
|------|------|--------------------------------|----------------------------------------|------------------------------|
| Company User | 公司端 Ask AI tab | ✅ 仅 chat 可读 + 仅可见**自己上传**的文件 | ❌ 任何方式都不可访问 | ✅ 通过 Playbook toggle |
| Company Admin（Founder） | 公司端 Ask AI tab | ✅ 完整只读 Memory Settings 面板 + 可见**全公司**上传文件 | ❌ 任何方式都不可访问 | ✅ 通过 Playbook toggle |
| Portfolio Manager (PM) | Admin Portal Ask AI tab | ✅ 跨可访问公司只读 | ✅ 同 Layer 1a 范围只读 | ✅ |
| Portfolio Group Manager (PGM) | Admin Portal Ask AI tab | ✅ | ✅ | ✅ + **可管理 Playbook** |
| Super Admin | Admin Portal | ✅ | ✅ | ✅ + **可管理 Playbook** |

---

## 3. 知识架构（Knowledge Architecture）

### 3.1 三层定义

| 层 | 内容来源 | 存储粒度 | 写入触发 |
|---|---------|---------|---------|
| **Layer 1a — Company Memory File** | 公司 Settings 元数据 + 公司侧 chat 会话抽取 + 公司侧上传文档摘要 | **per Company**（每公司一份） | (1) 公司首次启用 chatbot；(2) Settings 修改；(3) chat session 结束 AI extraction pass；(4) 文档上传完成 |
| **Layer 1b — Portfolio Admin Memory File** | Portfolio 侧 chat 抽取 + Portfolio 侧上传文档摘要 | **per Company**（每公司一份，**所有可访问 PM/PGM 共享同一份**，不按 portfolio 区分） | (1) PM/PGM chat 结束 extraction；(2) PM/PGM 上传文档 |
| **Layer 2 — GS Knowledge Base** | GS 内部 playbooks（如 SaaS playbook 等） | **per Tenant**（架构上必须 tenant-scoped；MVP 仅 GS 一个 tenant） | Super Admin / PGM 通过 in-app UI 编辑（MVP 仅手动；Post-MVP 由 AI 半自动 + Admin review） |

### 3.2 隔离硬约束

- **任何层的内容都不允许流入另一层**
- **Layer 1b 内容在任何措辞下都不得对公司侧用户暴露**（架构级别约束，不只是 prompt 级别）
- **Layer 2 不跨 tenant**：未来商业化后每家 equity firm 各自独立 Layer 2，互不可见
- 一种 Post-MVP 例外（架构需预留扩展点而不实现）：匿名化跨 portfolio 的市场情报层，用户主动 opt-in 才可用

### 3.3 Memory File 抽取规则（写入 Layer 1a / 1b）

**何时抽取**：会话结束事件 或 用户在指定时长内未活动（具体时长 TBD）

**什么值得保存**（AI 自己判断的 broad extraction prompt 即可，不需硬编码所有类别；以下为指导性类别，来自 5/8 BR 会议）：
- People & Org Structure（人员与组织架构）
- ICP（Ideal Customer Profile）
- Competitors（竞争对手）
- Porter's Five Forces 框架
- Founder Psychographic / Personality（创始人画像）
- Strategic Challenges with Staying Power（持续战略挑战）
- Value Proposition & ROI（价值主张与投资回报）
- Pricing Model（定价模型）
- 用户陈述的、LG Settings 中尚未的公司事实
- 对 LG 既有数据的修正或澄清
- 战略性上下文（如"现在最大挑战是 sales efficiency"）

**什么不保存**：generic 问题（如"什么是 gross margin"）、transactional 交流（如"再说一遍"）、LG 已准确记录的内容、完整 verbatim chat（已有独立 Chat History 功能）

### 3.4 冲突解决

- **Memory File 内部冲突**：用最新（latest wins）
- **Memory File vs Layer 2 冲突**：surfaces all relevant，不静默偏向某一源；AI 应用公司 memory 上下文过滤 KB 响应（让 generic playbook 适应该公司情境）
- **Normalization Table 数据 correction**：仅在该数据点被直接查询时应用 correction，**不传播到下游**（forecasting、live computing、benchmark percentile 不修改）；Post-MVP 可考虑 AI 主动 prompt 用户去 LG 内更新

---

## 4. 模型与编排架构（Model Routing & Orchestration）

### 4.1 推荐方案（已 UAT Passed：LG-1311）

- **路由层**：OpenRouter
- **架构**：Multi-agent，按任务类型自动分配 agent（一场景一 agent）
- **模型分级**：轻量模型做预处理 / 简单检索；高端模型做复杂推理 / 综合
- **用户对模型完全无感**（没有切换控件）

### 4.2 待 LG-1381 决策（新研究任务，Backlog Needs Sizing）

- 会话隔离与平台风险：内容审核触发对其他用户 / 整个 LG 平台 API 接入的影响
- 自托管私有模型评估：垂直商业场景下私有部署的 TCO 与可控性收益
- 当前 OpenRouter 架构必须**预留切换到私有托管的扩展点**，避免未来迁移时产生不可逆设计债

### 4.3 安全防护

- Prompt Injection 防护在架构层强制，对所有用户角色生效
- 模型服务商不得超出回复所需地记录或保留敏感公司数据
- Skills 明确不在 MVP，架构无需为其适配但 Post-MVP 需考量

---

## 5. 数据源（MVP 全部）

| 数据源 | 用途 | 真实源 |
|--------|------|--------|
| Normalization Table（actuals + committed forecast + system-generated forecast + benchmarks） | 财务 / Benchmark Q&A 唯一可信源 | Java 业务库 `fi_*` 表 |
| Company Settings 元数据（name / description / industry / stage / company_type） | Layer 1a 初始化、对话上下文 | Java 业务库 |
| Layer 1a / 1b Memory File | 公司专属上下文 | Python 自有表 |
| Layer 2 GS Knowledge Base | 通用 playbook | Python 自有表 |

**MVP 范围内不引入任何其他数据源。**

---

## 6. 公司端 UI（Company Portal）

### 6.1 入口与定位（LG-1332）
- 在 Company Portal 加 **Ask AI** 标签 / 图标 / 等效入口
- 用户进入后**直接进入聊天体验**
- 严格限定公司上下文：**不可见**任何 portfolio 数据、其他公司数据、GS 内部内容
- 语气：始终在线的运营合伙人（always-on operating partner）

### 6.2 欢迎页 & 输入
- 标题 + suggested prompt 卡片（覆盖财务表现 / Benchmark 定位 / 预测）
- 自由文本输入栏 + 始终可见的 **New Chat**
- AI 回复底部显著的"内容由 AI 生成仅供参考"免责声明

### 6.3 Memory Settings 面板（LG-1333）
- 仅 Company Admin 可访问
- 一家公司**只有一个 memory file**，按 source 标签（profile / chat / document）区分
- **在线 markdown 渲染**，read-only（不下载——下载会立即过时）
- 必须支持 Memory File type filter（Layer 1a / Layer 1b，对公司端隐藏 Layer 1b）

### 6.4 财务 & Benchmark Q&A（LG-1334）
- 基于 Normalization Table 直查
- 支持 actuals / committed forecast / system forecast / benchmarks 自然语言追问
- 缺数据时给出补全引导（如"请在 Financial Entry 录入"）

---

## 7. Portfolio Portal UI（Admin Portal）

### 7.1 入口与定位（LG-1335）
- Admin Portal 内一个**独立**的 Ask AI 入口（与 Company 端隔离）
- 欢迎页面以投资组合为导向（如"哪些公司在 burn rate 上表现不佳"、"投资组合在 ARR 增长方面的趋势"）
- 标题可参考 "Your AI Operating Partner"
- **默认 prompts 由 Dougal 在 5/8 BR 会议确认**（已附图见 task notes）
- Welcome Page Prompt 更新逻辑 / In-conversation follow-up prompts 均**Post-MVP**

### 7.2 Memory Settings 面板（LG-1336）
- 同公司端面板但额外加 Layer 1b 视图
- Memory File type filter 实现形式（tabs / dropdown / radio）设计阶段 finalize

### 7.3 跨公司财务 Q&A（LG-1337）
- 支持跨公司聚合（"我可访问的所有公司中 sales efficiency 最差的前 5 家"）
- ACL 严格按用户的 `accessible_companies` 过滤

---

## 8. 全用户共享功能

### 8.1 Chat History（LG-1339）
- 按用户隔离，read-only
- 前端按 Today / Yesterday / Last Week 分组
- **Rename / Delete 是 Post-MVP**

### 8.2 文档上传（LG-1340）
- 入口：聊天框附件按钮
- **上传通道由 Java 维护**（复用现有上传 API，加 `scene` 字段标识 AI Chatbot 用途）
- 上传成功后：Java 落 S3 + 写元数据 + 发 SQS 事件给 Python
- Python 收到事件：拉文件 → chunk → 嵌入 → 写 `document_chunks` + 自动摘要写入对应层 Memory File（公司侧 → Layer 1a；PM 侧 → Layer 1b）
- 文件列表 UI **合并到 Knowledge Base section**（与 GS Playbook 同区，按角色控制可见性）：
  - Company User：仅自己上传
  - Company Admin：全公司 Layer 1a
  - PM / PGM / Super Admin：跨可访问公司 Layer 1a + Layer 1b
- 支持 list view 与下载，**不强求在线预览**
- Layer 2 / Playbook 内容若被 admin 删除或替换：chat 中的 Playbook toggle 自动隐藏（LG-1331）

---

## 9. 服务边界

| 维度 | Java（CIOaas-api） | Python（CIOaas-python） |
|------|--------------------|--------------------------|
| 文件上传与 S3 落盘 | ✅ 唯一通道（复用现有上传接口加 `scene`） | ❌ |
| Normalization / Benchmark / Company Settings / ACL | ✅ 写 | ✅ **PG 只读账号 `cioaas_ai_ro` 直读**，不走 REST |
| AI 编排 / RAG / Memory / Chat History / Layer 2 ingestion | ❌ | ✅ |
| 业务状态变更通知 | ✅ 发 SQS 事件 | ✅ 消费 SQS（`file.uploaded` / `company.settings.updated` / `user.acl.updated` / `company.created`） |
| JWT 验签 | ✅ | ✅（共用密钥，不回调 Java `/me`） |

详见 `python-java-integration.md`。

---

## 10. MVP 范围 vs Post-MVP

### ✅ MVP（必须做）

1. 双层知识架构（Layer 1a + Layer 1b + Layer 2）后端 + 基础访问
2. 公司端 / Portfolio 端两套独立核心 chat UI
3. Memory Settings 只读面板（Company Admin / Portfolio 端两套）
4. 财务与 Benchmark 自然语言问答（含跨公司）
5. Chat History（read-only，按用户隔离）
6. 文档上传（含 RAG 索引 + Layer 1 memory 摘要）+ Knowledge Base section 文件列表
7. Layer 2 admin 上传 / 编辑 / 删除（手动 + in-app UI）
8. OpenRouter 多模型路由 + 多 Agent 架构
9. Prompt Injection 防护
10. Company Profile Expansion（description 扩容 + industry 默认提示，LG-1327）

### ❌ Post-MVP（明确排除）

- Skills / Report Builder（已估约 2 周，由 Karen 决策何时加入）
- LLM 从对话自动识别 KB 更新 + Admin review 流程
- Fireflies 转录摄取至 Memory File（含 Fireflies ↔ LG 同步）
- Chat History rename / delete
- 跨 portfolio 匿名化市场情报层（基于 Fireflies）
- 多租户商业化（架构必须 day-1 预留扩展性，但功能 Post-MVP）
- AI 主动公司评分 / workflow / task 触发
- AI 主动从对话推送 LG 数据更正回 LG 业务表
- Welcome Page Prompt 个性化更新
- In-conversation follow-up prompts
- Data Correction 传播至下游（forecast / benchmark percentile 等）

---

## 11. 18 个 Asana 任务索引（按 Part 分组）

| Part | LG 编号 | 任务 | 状态 | T-Shirt |
|------|---------|------|------|---------|
| A | LG-1311 | Research AI Models for Chatbot Use | UAT Passed | M (8) |
| A | LG-1326 | Research: GS Playbook Hosting Strategy | Product Approved (Sprint On-Deck) | M (8) |
| A | LG-1327 | Company Profile Expansion - Enhanced Description | Product Review (In Progress) | M (2) |
| A | LG-1328 | AI Architecture & Model Routing Foundation | Product Review (In Progress) | L (13) |
| A | — | AI Chatbot - Skills/Report Builder | Post-MVP | — |
| A | LG-1381 | AI Model Hosting Strategy（新增） | Needs Sizing | — |
| B | LG-1329 | Company Memory File - Layer 1a Backend | Needs Sizing | L |
| B | LG-1330 | Company Memory File - Layer 1b Backend | Prioritization Complete | M |
| B | LG-1331 | GS Knowledge Base - Layer 2 Ingestion & Management | Prioritization In Progress | M |
| B | LG-1338 | GS Knowledge Base Access for All Users（Layer 2） | Prioritization In Progress | L |
| C | LG-1332 | Company User Core Chat UI | Prioritization In Progress | M |
| C | LG-1333 | Company User Memory File Access UI | Prioritization In Progress | M |
| C | LG-1334 | Company User Financial & Benchmark Q&A | Prioritization In Progress | L |
| D | LG-1335 | Portfolio Manager Core Chat UI | Prioritization In Progress | L |
| D | LG-1336 | Portfolio Manager Memory File Access UI | Prioritization In Progress | M |
| D | LG-1337 | Portfolio Manager Financial & Benchmark Q&A | Prioritization In Progress | L |
| D | LG-1339 | Chat History for All Users | Prioritization In Progress | M |
| D | LG-1340 | Document Upload for Chat Analysis | Prioritization In Progress | XL |

---

## 12. 与本文档相关的其他文档

| 文档 | 用途 |
|------|------|
| `README.md` | 顶层索引 + 状态表 |
| `part-A-foundation.md` | Part A 基础与研究类详细 PRD |
| `part-B-memory-kb.md` | Part B Memory 与知识库类详细 PRD |
| `part-C-company-ui.md` | Part C 公司端 UI 详细 PRD |
| `part-D-portfolio-shared.md` | Part D Portfolio 端 UI 与共享功能详细 PRD |
| `.raw/01-18.md` | 每个任务的英文原文 + Asana 业务评论 + 中文版整理 |
| `langgraph-technical-design.md` | LangGraph 整体技术方案 |
| `python-java-integration.md` | Python ↔ Java 边界（Java 仅负责文件上传） |

---

## 13. 待澄清 / 待确认（Open Questions）

| # | 问题 | 来源 | 跟踪 |
|---|------|------|------|
| 1 | LG-1329 在 5/8 新增了 8 个 memory 类别后被 revert 到 Needs Sizing，需重新与 dev team 对齐 sizing | LG-1329 评论 | dev team |
| 2 | Memory file 大小上限是否需要硬限制？由 dev team 评估 | LG-1311 评论 | dev team |
| 3 | LG-1381 自托管模型评估结论将反向影响 LG-1328 架构（OpenRouter SDK 抽象层等） | LG-1381 业务背景 | LG-1381 完成后 review LG-1328 |
| 4 | 默认 Suggested Prompts 最终文案以 Dougal 5/8 BR 会议附件为准（已在 LG-1335 中附图） | LG-1335 评论 | 设计阶段对齐 |
| 5 | Memory File type filter UI 形式（tabs / dropdown / radio）在 LG-1333 / LG-1336 设计阶段 finalize | LG-1333 / LG-1336 评论 | 设计阶段 |
| 6 | 商业化（多租户）触发时机：Layer 2 切换到 tenant-scoped 实际部署的触发条件 | LG-1328 评论 | 商业化决策时 review |
