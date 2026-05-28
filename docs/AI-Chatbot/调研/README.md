# AI Chatbot 需求总览（EPIC: AI Chatbot）

> 本文档是 Looking Glass（LG）平台 AI Chatbot 史诗（Epic）的中文需求汇总索引。
> 数据来源：Asana Workspace `Golden Section` → `EPIC: AI Chatbot`（gid: 1211653019675507）。
> 拉取时间：**2026-05-22**（上一次：2026-05-12）。
>
> **本轮变更摘要（2026-05-12 → 2026-05-22）**
> - EPIC 子任务数 **18 → 28**（净增 11 个，3 个旧 ticket 被搬到 PARKING LOT）。
> - **核心改动 1**：原 LG-1329（Layer 1a Backend）被拆分为 **8 个**独立 User Story（Init + Document Upload Processing + 6 个 Chat Extraction 子类）。
> - **核心改动 2**：原 LG-1330（Layer 1b Backend）被拆分为 **2 个**（Init & Architecture + Chat Extraction & Document Upload Processing）。
> - **核心改动 3**：原 LG-1340（Document Upload for Chat Analysis）被拆分为 **2 个**（Company Portal 版 + Portfolio Admin 版）。
> - **新增 Research**：LG-1385 _Layer 1b Chat Content - Company Association and Memory Binding Logic_。
> - **抽取触发器变更**：从「session-end / inactivity」改为「**real-time incremental at each message exchange, processing asynchronously**」（采纳 wenchao 2026-05-15 建议，避免长会话历史压缩导致信息丢失）。
> - **LG-1381 AI Model Hosting Strategy**：状态由 _Needs Sizing_ → **Product Review (In Progress)**，T-Shirt = M。
> - **LG-1327 / LG-1328**：状态前进至 _Ready for Design_ / _Product Approved_，均进入 Sprint (On-Deck)。
> - 原 LG-1329 / LG-1330 / LG-1340 整体迁入新 EPIC「**Epic: Original AI Chatbot prior to split**」（gid: 1214953638396810，状态 PARKING LOT）作为历史留存，不再独立排期。

---

## 1. Epic 概述

**EPIC: AI Chatbot** 当前包含 **28 个子任务**，目标是在 Looking Glass 平台中构建一个面向公司端用户和 Portfolio 端用户的对话式 AI 助手，支持：

- **双层知识架构**：Layer 1（公司专属 Memory File，分 1a 与 1b 两份）+ Layer 2（GS Knowledge Base / 组织级 playbooks）。
- **基于角色的访问隔离**：Company User / Company Admin 仅可访问 Layer 1a 与 Layer 2；Portfolio Manager / PGM / Admin 可同时访问 Layer 1a、Layer 1b 与 Layer 2。
- **数据接入与回答**：以 Normalization Table 为财务数据可信源，支持公司内单公司问答和 Portfolio 端跨公司问答。
- **基础能力**：聊天历史（Chat History）、文档上传（Document Upload，含 RAG 索引）、Memory Settings 面板。
- **租户扩展性**：所有 Layer 2 资源按 tenant-scoped 设计，便于未来商业化为多租户。

---

## 2. 文档结构

### 2.1 需求文档（按主题分 4 个分册）

| 分册 | 主题 | 任务数 | 文档链接 |
|------|------|------|------|
| Part A | 基础与研究类（Foundation & Research） | 7 | [part-A-foundation.md](./part-A-foundation.md) |
| Part B | Memory 与知识库类（Memory & Knowledge Base） | 12 | [part-B-memory-kb.md](./part-B-memory-kb.md) |
| Part C | 公司端用户体验（Company User UI） | 3 | [part-C-company-ui.md](./part-C-company-ui.md) |
| Part D | Portfolio 端 UI 与共享功能 | 6 | [part-D-portfolio-shared.md](./part-D-portfolio-shared.md) |

### 2.2 总体需求（看一份就够）

| 文档 | 范围 | 链接 |
|------|------|------|
| **总体需求** | 28 个任务的核心需求汇总：角色矩阵、知识架构、模型路由、数据源、UI 总览、MVP/Post-MVP 范围、Open Questions | [overall-requirements.md](./overall-requirements.md) |

### 2.3 技术方案

| 文档 | 范围 | 链接 |
|------|------|------|
| LangGraph 技术方案 | 整体架构、状态模型、节点 / 边、检索层、工具调用、Memory 抽取、Checkpointer、安全 4 层防护、PG schema、部署、实施路线、关键代码骨架 | [langgraph-technical-design.md](./langgraph-technical-design.md) |
| Python ↔ Java 集成边界 | Java 仅负责文件上传通道；其他业务数据由 Python 直读 PG + SQS 事件；服务边界、缓存、失败降级、对账 | [python-java-integration.md](./python-java-integration.md) |

> **服务边界一句话**：所有 AI Chatbot 功能由 Python 服务承担；需要业务数据时通过 Java REST 接口拉取，Python 不直连 Java 业务库。

**双语原始内容**保存在 `.raw/` 子目录，每份含三段：
1. YAML 头（Asana 元数据）
2. **英文原文**（Asana notes 原文）
3. **Asana 业务讨论**（过滤后的 comments，按时间倒序）
4. **中文版需求整理**（从对应 part-*.md 抽取，保持一致）

> 旧版（拆分前）的 LG-1329 / LG-1330 / LG-1340 原始内容已归档至 `.raw/.archive/` 子目录，保留供历史追溯。

---

## 3. 全部 28 个需求清单（按 Part 分组）

> 状态字段以 Asana **LG Status** 为主，若在 Sprint 内则用 **Working Status** 补充；T-Shirt 为 Sizing 字段；最近修改取自 Asana `modified_at`。

### Part A：基础与研究类（Foundation & Research）— 7 个

| # | LG | 任务名称 | LG Status | Working | T-Shirt | Modified | Asana ID |
|---|---|---------|----------|---------|---------|---------|----------|
| 1 | LG-1311 | Research AI Models for Chatbot Use | ✅ UAT Passed | Complete | M (8) | 2026-04-27 | 1213876002981172 |
| 2 | LG-1326 | Research: GS Playbook Hosting Strategy | Product Approved (Sprint On-Deck) | — | M (8) | 2026-05-11 | 1214147930023558 |
| 3 | LG-1327 | Company Profile Expansion - Enhanced Description | **Ready for Design (Sprint On-Deck)** ⬆️ | Not Started | M (2) | 2026-05-20 | 1214057483533667 |
| 4 | LG-1328 | AI Architecture & Model Routing Foundation | **Product Approved (Sprint On-Deck)** ⬆️ | — | L (13) | 2026-05-20 | 1214057483533668 |
| 5 | —     | AI Chatbot - Skills/Report Builder | — (Post-MVP) | — | — | 2026-04-17 | 1214110731636985 |
| 6 | LG-1381 | AI Model Hosting Strategy | **Product Review** ⬆️ | **In Progress** ⬆️ | M (3) | 2026-05-21 | 1214717456780780 |
| 7 | **LG-1385** | **Research: Layer 1b Chat Content - Company Association and Memory Binding Logic（新增）** | Needs Sizing | Not Started | — | 2026-05-21 | 1214913562391163 |

### Part B：Memory 与知识库类（Memory & Knowledge Base）— 12 个

**Layer 1a Backend（公司 Memory File 后端，由旧 LG-1329 拆分而来）— 8 个**

| # | LG | 任务名称 | LG Status | Working | T-Shirt | Modified | Asana ID |
|---|---|---------|----------|---------|---------|---------|----------|
| B-1 | **LG-1390** | Layer 1a Backend - Initialization & Company Settings Seeding | Needs Sizing | Not Started | — | 2026-05-21 | 1214913562391185 |
| B-2 | **LG-1388** | Layer 1a Backend - Document Upload Processing | Needs Sizing | Not Started | — | 2026-05-21 | 1214913562391187 |
| B-3 | **LG-1391** | Layer 1a Backend - Chat Extraction: Company Facts & Data Corrections | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826103 |
| B-4 | **LG-1392** | Layer 1a Backend - Chat Extraction: ICP and Customer Profile | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826104 |
| B-5 | **LG-1393** | Layer 1a Backend - Chat Extraction: Competitive Landscape | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826105 |
| B-6 | **LG-1394** | Layer 1a Backend - Chat Extraction: Porter's Five Forces Profile | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826106 |
| B-7 | **LG-1395** | Layer 1a Backend - Chat Extraction: Strategic Context and Challenges | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826107 |
| B-8 | **LG-1396** | Layer 1a Backend - Chat Extraction: Founder Profile | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826108 |

**Layer 1b Backend（Portfolio Admin Memory File 后端，由旧 LG-1330 拆分而来）— 2 个**

| # | LG | 任务名称 | LG Status | Working | T-Shirt | Modified | Asana ID |
|---|---|---------|----------|---------|---------|---------|----------|
| B-9  | **LG-1397** | Layer 1b Backend - Initialization & Architecture (Portfolio Admin) | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826115 |
| B-10 | **LG-1398** | Layer 1b Backend - Chat Extraction & Document Upload Processing (Portfolio Admin) | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826116 |

**Layer 2 GS Knowledge Base — 2 个**

| # | LG | 任务名称 | LG Status | Working | T-Shirt | Modified | Asana ID |
|---|---|---------|----------|---------|---------|---------|----------|
| B-11 | LG-1331 | GS Knowledge Base - Layer 2 Ingestion & Management | Prioritization In Progress | Not Started | M | 2026-05-20 | 1214057483533665 |
| B-12 | LG-1338 | AI Chatbot - GS Knowledge Base Access for All Users（Layer 2） | Prioritization In Progress | Not Started | L | 2026-05-15 | 1214081544026467 |

### Part C：公司端用户体验（Company User UI）— 3 个

| # | LG | 任务名称 | LG Status | Working | T-Shirt | Modified | Asana ID |
|---|---|---------|----------|---------|---------|---------|----------|
| C-1 | LG-1332 | Company User Core Chat UI | Prioritized | Not Started | M | 2026-05-20 | 1214057483533662 |
| C-2 | LG-1333 | Company User Memory File Access UI | Prioritized | Not Started | M | 2026-05-20 | 1214147930023561 |
| C-3 | LG-1334 | Company User Financial & Benchmark Q&A | Prioritized | Not Started | L | 2026-05-20 | 1214081544026464 |

### Part D：Portfolio 端 UI 与共享功能 — 6 个

| # | LG | 任务名称 | LG Status | Working | T-Shirt | Modified | Asana ID |
|---|---|---------|----------|---------|---------|---------|----------|
| D-1 | LG-1335 | Portfolio Manager Core Chat UI | Prioritization In Progress | Not Started | L | 2026-05-15 | 1214057483533663 |
| D-2 | LG-1336 | Portfolio Manager Memory File Access UI | Prioritization In Progress | Not Started | M | 2026-05-15 | 1214081544026466 |
| D-3 | LG-1337 | Portfolio Manager Financial & Benchmark Q&A | Prioritization In Progress | Not Started | L | 2026-05-15 | 1214081544026465 |
| D-4 | LG-1339 | Chat History for All Users | Prioritization In Progress | Not Started | M | 2026-05-15 | 1214081544026468 |
| D-5 | **LG-1400** | AI Chatbot - Document Upload for Chat Analysis (Company Portal)（拆出） | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826119 |
| D-6 | **LG-1399** | AI Chatbot - Document Upload for Chat Analysis (Portfolio Admin)（拆出） | Needs Sizing | Not Started | — | 2026-05-21 | 1214953638826120 |

---

## 4. 已 parking 的旧 ticket（历史归档）

以下 3 个旧 ticket 已被拆分并迁出 EPIC: AI Chatbot；新 EPIC 「Epic: Original AI Chatbot prior to split」（gid: 1214953638396810，PARKING LOT 区段）作为历史容器保留：

| 旧 LG | 旧任务名 | 已被拆分为 |
|------|----------|------------|
| LG-1329 | Company Memory File - Layer 1a Backend (Company User Context) | LG-1388 / LG-1390 / LG-1391~1396（共 8 个新 ticket） |
| LG-1330 | Company Memory File - Layer 1b Backend (Portfolio Admin Context) | LG-1397 / LG-1398（共 2 个新 ticket） + LG-1385 Research |
| LG-1340 | AI Chatbot - Document Upload for Chat Analysis | LG-1400（Company Portal）+ LG-1399（Portfolio Admin） |

> 原 `.raw/06`、`.raw/07`、`.raw/17` 三份英文原文已搬至 `.raw/.archive/` 保留。

---

## 5. 关键架构概念速览

| 概念 | 含义 | 可见性 |
|------|------|--------|
| **Layer 1a** | Company Memory File（公司专属 Memory File） | Company User / Admin + Portfolio 端均可见 |
| **Layer 1b** | Portfolio Admin Memory File（GS 内部上下文） | 仅 Portfolio Manager / PGM / Admin 可见，**绝不可被公司端用户访问** |
| **Layer 2** | GS Knowledge Base（组织级 playbooks） | 全员只读访问（按 tenant 隔离） |
| **Normalization Table** | 财务数据唯一可信源（actuals、committed forecast、system-generated forecast、benchmarks） | — |
| **RAG** | Retrieval-Augmented Generation（检索增强生成） | 用于文档上传后的索引与查询 |
| **OpenRouter** | 模型路由层（多模型架构） | 后端实现，对用户不可见 |
| **Tenant-Scoped** | 按租户隔离的资源 | Layer 2 必须从 day 1 即按此设计 |
| **Real-time Incremental Extraction** | **新版**抽取触发器：在每条消息往返时实时异步抽取，不等会话结束 | Layer 1a + Layer 1b 共用 |

---

## 6. 角色与权限矩阵

| 角色 | Layer 1a | Layer 1b | Layer 2 | 编辑 KB |
|------|---------|---------|---------|---------|
| Company User | ❌（无 Memory Settings 面板） | ❌ | ✅（聊天回复） | ❌ |
| Company Admin | ✅（只读） | ❌ | ✅（聊天回复） | ❌ |
| Portfolio Manager (PM) | ✅（只读，访问范围内） | ✅（只读，访问范围内） | ✅（聊天回复） | ❌ |
| Portfolio Group Manager (PGM) | ✅（只读，访问范围内） | ✅（只读，访问范围内） | ✅（聊天回复） | ✅ |
| Super Admin | ✅ | ✅ | ✅ | ✅ |

---

## 7. MVP 范围明确说明

**MVP 范围内**：
- 双层知识架构（Layer 1a + Layer 1b + Layer 2）的后端与基础访问能力
- 公司端 / Portfolio 端两个独立的核心 chat UI
- Memory Settings 只读面板（Company Admin / Portfolio 端两套）
- 财务与 Benchmark 自然语言问答（含跨公司）
- 聊天历史（read-only，按用户隔离）
- 文档上传（**拆为 Company Portal 与 Portfolio Admin 两个独立 ticket**，含 RAG 索引 + Layer 1 Memory File 摘要）
- Layer 2 admin 上传 / 编辑 / 删除（手动）
- OpenRouter 多模型路由 + 多 Agent 架构
- Prompt injection 防护
- **Real-time incremental Memory File 抽取**（在 conversation in flight 期间增量抽取，非 end-of-session 触发）

**Post-MVP 范围**：
- Skills / Report Builder
- LLM 自动从对话识别 KB 更新（带 Admin review 流程）
- Fireflies 转录摄取至 Memory File
- Chat History 重命名 / 删除
- 跨 tenant 匿名化市场情报层（基于 Fireflies）
- 多租户商业化（架构必须从 day 1 预留扩展性）

---

## 8. 文件目录结构

```
D:/github-code/LG/docs/AI-Chatbot/调研/
├── README.md                          ← 本文件（中文索引）
├── overall-requirements.md            ← 总体需求（一份看完）
├── part-A-foundation.md               ← 基础与研究类（7 个需求）
├── part-B-memory-kb.md                ← Memory 与知识库类（12 个需求）
├── part-C-company-ui.md               ← 公司端 UI（3 个需求）
├── part-D-portfolio-shared.md         ← Portfolio 端 UI 与共享功能（6 个需求）
├── langgraph-technical-design.md      ← LangGraph 技术方案
├── python-java-integration.md         ← Python ↔ Java 集成边界
└── .raw/                              ← Asana 原始英文需求
    ├── 01-research-ai-models.md                                    LG-1311
    ├── 02-research-gs-playbook-hosting.md                          LG-1326
    ├── 03-company-profile-expansion.md                             LG-1327
    ├── 04-ai-architecture-routing-foundation.md                    LG-1328
    ├── 05-skills-report-builder.md
    ├── 06a-layer1a-initialization.md                               LG-1390 (新)
    ├── 06b-layer1a-document-upload-processing.md                   LG-1388 (新)
    ├── 06c-layer1a-extraction-company-facts.md                     LG-1391 (新)
    ├── 06d-layer1a-extraction-icp.md                               LG-1392 (新)
    ├── 06e-layer1a-extraction-competitive-landscape.md             LG-1393 (新)
    ├── 06f-layer1a-extraction-porters-five-forces.md               LG-1394 (新)
    ├── 06g-layer1a-extraction-strategic-context.md                 LG-1395 (新)
    ├── 06h-layer1a-extraction-founder-profile.md                   LG-1396 (新)
    ├── 07a-layer1b-initialization-architecture.md                  LG-1397 (新)
    ├── 07b-layer1b-extraction-and-document-upload.md               LG-1398 (新)
    ├── 08-gs-knowledge-base-layer2-ingestion.md                    LG-1331
    ├── 09-gs-knowledge-base-layer2-access.md                       LG-1338
    ├── 10-company-user-core-chat-ui.md                             LG-1332
    ├── 11-company-user-memory-file-access-ui.md                    LG-1333
    ├── 12-company-user-financial-benchmark-qa.md                   LG-1334
    ├── 13-portfolio-manager-core-chat-ui.md                        LG-1335
    ├── 14-portfolio-manager-memory-file-access-ui.md               LG-1336
    ├── 15-portfolio-manager-financial-benchmark-qa.md              LG-1337
    ├── 16-chat-history-for-all-users.md                            LG-1339
    ├── 17a-document-upload-company-portal.md                       LG-1400 (新)
    ├── 17b-document-upload-portfolio-admin.md                      LG-1399 (新)
    ├── 18-ai-model-hosting-strategy.md                             LG-1381
    ├── 19-research-layer1b-chat-content-binding.md                 LG-1385 (新)
    └── .archive/                      ← 拆分前的旧版本（历史归档）
        ├── 06-company-memory-file-layer1a.md                       LG-1329 (旧，已拆)
        ├── 07-company-memory-file-layer1b.md                       LG-1330 (旧，已拆)
        └── 17-document-upload-for-chat-analysis.md                 LG-1340 (旧，已拆)
```

---

## 9. Asana 链接

- **Epic 主页面（活动）**：https://app.asana.com/0/1170332106480422/1211653019675507
- **Epic: Original AI Chatbot prior to split（历史 / PARKING LOT）**：https://app.asana.com/1/1170332106480422/project/1205775247746179/task/1214953638396810
- **Workspace**：Golden Section (1170332106480422)

每个需求的 Asana 链接已在对应分册文档中标注。
