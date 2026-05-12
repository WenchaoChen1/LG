# AI Chatbot 需求总览（EPIC: AI Chatbot）

> 本文档是 Looking Glass（LG）平台 AI Chatbot 史诗（Epic）的中文需求汇总索引。
> 数据来源：Asana Workspace `Golden Section` → `EPIC: AI Chatbot`（gid: 1211653019675507）。
> 拉取时间：2026-05-06。

---

## 1. Epic 概述

**EPIC: AI Chatbot** 包含 **17 个子任务**（其中 1 个已完成、16 个待开发），目标是在 Looking Glass 平台中构建一个面向公司端用户和 Portfolio 端用户的对话式 AI 助手，支持：

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
| Part A | 基础与研究类（Foundation & Research） | 5 | [part-A-foundation.md](./part-A-foundation.md) |
| Part B | Memory 与知识库类（Memory & Knowledge Base） | 4 | [part-B-memory-kb.md](./part-B-memory-kb.md) |
| Part C | 公司端用户体验（Company User UI） | 3 | [part-C-company-ui.md](./part-C-company-ui.md) |
| Part D | Portfolio 端 UI 与共享功能 | 5 | [part-D-portfolio-shared.md](./part-D-portfolio-shared.md) |

### 2.2 技术方案

| 文档 | 范围 | 链接 |
|------|------|------|
| LangGraph 技术方案 | 整体架构、状态模型、节点 / 边、检索层、工具调用、Memory 抽取、Checkpointer、安全 4 层防护、PG schema、部署、实施路线、关键代码骨架 | [langgraph-technical-design.md](./langgraph-technical-design.md) |
| Python ↔ Java 集成边界 | 服务边界、数据归属、Java 需暴露的接口清单、事件 / Webhook、鉴权传递、缓存策略、失败降级、对账 | [python-java-integration.md](./python-java-integration.md) |

> **服务边界一句话**：所有 AI Chatbot 功能由 Python 服务承担；需要业务数据时通过 Java REST 接口拉取，Python 不直连 Java 业务库。

英文原始内容（Asana 拉取的原文）保存在 `.raw/` 子目录，文件名 `01-...md` 至 `17-...md`。

---

## 3. 全部 17 个需求清单（按 Part 分组）

### Part A：基础与研究类（Foundation & Research）

| # | 任务名称 | 状态 | Asana ID |
|---|----------|------|----------|
| 1 | Research AI Models for Chatbot Use（聊天机器人 AI 模型评估） | ✅ 已完成 | 1213876002981172 |
| 2 | Research: GS Playbook Hosting Strategy（GS Playbook 托管策略调研） | ⏳ 待开发 | 1214147930023558 |
| 3 | Company Profile Expansion - Enhanced Description（公司资料字段扩展） | ⏳ 待开发 | 1214057483533667 |
| 4 | AI Architecture & Model Routing Foundation（AI 架构与模型路由基础） | ⏳ 待开发 | 1214057483533668 |
| 5 | AI Chatbot - Skills/Report Builder（Post-MVP 技能与报表生成） | ⏳ 待开发 | 1214110731636985 |

### Part B：Memory 与知识库类（Memory & Knowledge Base）

| # | 任务名称 | 状态 | Asana ID |
|---|----------|------|----------|
| 1 | Company Memory File - Layer 1a Backend（公司用户上下文） | ⏳ 待开发 | 1214057483533664 |
| 2 | Company Memory File - Layer 1b Backend（Portfolio Admin 上下文） | ⏳ 待开发 | 1214147930023560 |
| 3 | GS Knowledge Base - Layer 2 Ingestion & Management（Layer 2 摄取与管理） | ⏳ 待开发 | 1214057483533665 |
| 4 | GS Knowledge Base Access for All Users（Layer 2 全用户访问） | ⏳ 待开发 | 1214081544026467 |

### Part C：公司端用户体验（Company User UI）

| # | 任务名称 | 状态 | Asana ID |
|---|----------|------|----------|
| 1 | Company User Core Chat UI（公司端核心聊天界面） | ⏳ 待开发 | 1214057483533662 |
| 2 | Company User Memory File Access UI（公司端 Memory Settings 面板） | ⏳ 待开发 | 1214147930023561 |
| 3 | Company User Financial & Benchmark Q&A（公司端财务与 Benchmark 问答） | ⏳ 待开发 | 1214081544026464 |

### Part D：Portfolio 端 UI 与共享功能

| # | 任务名称 | 状态 | Asana ID |
|---|----------|------|----------|
| 1 | Portfolio Manager Core Chat UI（Portfolio 端核心聊天界面） | ⏳ 待开发 | 1214057483533663 |
| 2 | Portfolio Manager Memory File Access UI（Portfolio 端 Memory Settings 面板） | ⏳ 待开发 | 1214081544026466 |
| 3 | Portfolio Manager Financial & Benchmark Q&A（Portfolio 端跨公司问答） | ⏳ 待开发 | 1214081544026465 |
| 4 | Chat History for All Users（所有用户的聊天历史） | ⏳ 待开发 | 1214081544026468 |
| 5 | Document Upload for Chat Analysis（聊天分析的文档上传） | ⏳ 待开发 | 1214057483533666 |

---

## 4. 关键架构概念速览

| 概念 | 含义 | 可见性 |
|------|------|--------|
| **Layer 1a** | Company Memory File（公司专属 Memory File） | Company User / Admin + Portfolio 端均可见 |
| **Layer 1b** | Portfolio Admin Memory File（GS 内部上下文） | 仅 Portfolio Manager / PGM / Admin 可见，**绝不可被公司端用户访问** |
| **Layer 2** | GS Knowledge Base（组织级 playbooks） | 全员只读访问（按 tenant 隔离） |
| **Normalization Table** | 财务数据唯一可信源（actuals、committed forecast、system-generated forecast、benchmarks） | — |
| **RAG** | Retrieval-Augmented Generation（检索增强生成） | 用于文档上传后的索引与查询 |
| **OpenRouter** | 模型路由层（多模型架构） | 后端实现，对用户不可见 |
| **Tenant-Scoped** | 按租户隔离的资源 | Layer 2 必须从 day 1 即按此设计 |

---

## 5. 角色与权限矩阵

| 角色 | Layer 1a | Layer 1b | Layer 2 | 编辑 KB |
|------|---------|---------|---------|---------|
| Company User | ❌（无 Memory Settings 面板） | ❌ | ✅（聊天回复） | ❌ |
| Company Admin | ✅（只读） | ❌ | ✅（聊天回复） | ❌ |
| Portfolio Manager (PM) | ✅（只读，访问范围内） | ✅（只读，访问范围内） | ✅（聊天回复） | ❌ |
| Portfolio Group Manager (PGM) | ✅（只读，访问范围内） | ✅（只读，访问范围内） | ✅（聊天回复） | ✅ |
| Super Admin | ✅ | ✅ | ✅ | ✅ |

---

## 6. MVP 范围明确说明

**MVP 范围内**：
- 双层知识架构（Layer 1a + Layer 1b + Layer 2）的后端与基础访问能力
- 公司端 / Portfolio 端两个独立的核心 chat UI
- Memory Settings 只读面板（Company Admin / Portfolio 端两套）
- 财务与 Benchmark 自然语言问答（含跨公司）
- 聊天历史（read-only，按用户隔离）
- 文档上传（RAG 索引 + Layer 1 Memory File 摘要）
- Layer 2 admin 上传 / 编辑 / 删除（手动）
- OpenRouter 多模型路由 + 多 Agent 架构
- Prompt injection 防护

**Post-MVP 范围**：
- Skills / Report Builder
- LLM 自动从对话识别 KB 更新（带 Admin review 流程）
- Fireflies 转录摄取至 Memory File
- Chat History 重命名 / 删除
- 跨 tenant 匿名化市场情报层（基于 Fireflies）
- 多租户商业化（架构必须从 day 1 预留扩展性）

---

## 7. 文件目录结构

```
D:/github-code/LG/docs/AI-Chatbot/
├── README.md                          ← 本文件（中文索引）
├── part-A-foundation.md               ← 基础与研究类（5 个需求）
├── part-B-memory-kb.md                ← Memory 与知识库类（4 个需求）
├── part-C-company-ui.md               ← 公司端 UI（3 个需求）
├── part-D-portfolio-shared.md         ← Portfolio 端 UI 与共享功能（5 个需求）
├── langgraph-technical-design.md      ← LangGraph 技术方案
├── python-java-integration.md         ← Python ↔ Java 集成边界
└── .raw/                              ← Asana 原始英文需求（17 份）
    ├── 01-research-ai-models.md
    ├── 02-research-gs-playbook-hosting.md
    ├── 03-company-profile-expansion.md
    ├── 04-ai-architecture-routing-foundation.md
    ├── 05-skills-report-builder.md
    ├── 06-company-memory-file-layer1a.md
    ├── 07-company-memory-file-layer1b.md
    ├── 08-gs-knowledge-base-layer2-ingestion.md
    ├── 09-gs-knowledge-base-layer2-access.md
    ├── 10-company-user-core-chat-ui.md
    ├── 11-company-user-memory-file-access-ui.md
    ├── 12-company-user-financial-benchmark-qa.md
    ├── 13-portfolio-manager-core-chat-ui.md
    ├── 14-portfolio-manager-memory-file-access-ui.md
    ├── 15-portfolio-manager-financial-benchmark-qa.md
    ├── 16-chat-history-for-all-users.md
    └── 17-document-upload-for-chat-analysis.md
```

---

## 8. Asana 链接

- **Epic 主页面**：https://app.asana.com/0/1170332106480422/1211653019675507
- **Workspace**：Golden Section (1170332106480422)

每个需求的 Asana 链接已在对应分册文档中标注。
