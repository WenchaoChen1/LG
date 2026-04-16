# EPIC: Manual Uploads with OCR — 技术设计文档

> **Asana EPIC**: [Manual Uploads with OCR](https://app.asana.com/1/1170332106480422/project/1202050347057533/task/1210456521366357)
> **状态**: 技术方案设计
> **创建日期**: 2026-04-16
> **代码示例**: [code-examples.md](./code-examples.md)

---

## 1. 需求概述

### 1.1 一句话描述

用户无需集成 QuickBooks 等系统，直接上传 PDF/Excel/图片等财务文件，系统通过 AI Vision 自动提取、分类、映射财务数据，用户在线审核确认后写入 Looking Glass 数据库。

### 1.2 业务目标

| 目标 | 说明 |
|------|------|
| 扩大可服务市场 | 覆盖没有 QuickBooks 等集成的公司 |
| 降低入驻门槛 | 早期创业公司无需技术集成即可使用 |
| 非技术用户参与 | 上传原始文件即可获取财务洞察 |

### 1.3 核心工作流

```
① 上传文件 → ② 数据提取(AI Vision/Excel) → ③ AI 账户映射 → ④ 并排审核编辑 → ⑤ 写入 LG → ⑥ 系统持续学习
```

### 1.4 子任务清单

| # | 子任务 | 负责人 | 核心内容 |
|---|--------|--------|----------|
| 1 | Allow Users to upload a financial document | Jesús H Peralta | PDF/Excel/CSV/图片上传，单文件 ≤20MB，批量 ≤100MB |
| 2 | Extraction of Financial Data - AI + OCR | Jesús H Peralta | AI Vision 提取扫描 PDF/图片中的财务表格 |
| 3 | Extraction of Financial Data - Excel | Jesús H Peralta | 直接解析 Excel/CSV 表格，处理合并单元格 |
| 4 | Add AI-Assisted Account Mapping Suggestions | Liang Chunru | AI 自动映射到 LG 标准财务分类（19 类） |
| 5 | Side-by-Side Review & Inline Editing | Jesús H Peralta | 并排审核 + 内联编辑 + Raw/Standardized 视图 |
| 6 | Write data to LG Schema | Jesús H Peralta | 冲突检测 + Overwrite/Skip/Cancel + 审计日志 |
| 7 | Add Note Field to Data Validation | Jesús H Peralta | 冲突解决时添加备注（≤2000 字） |
| 8 | System Learning and Continuous Improvement | Liang Chunru | 保存并复用公司级映射记忆 |

---

## 2. 架构定位：Multi-Agent 体系中的 OCR Agent

### 2.1 核心定位

OCR 文档解析是一个**独立的智能体（Agent）**，未来作为多智能体系统的一部分。

```
                    ┌──────────────────────────┐
                    │    Orchestrator Agent     │  ← 未来：统一调度层
                    │   (LangGraph Supervisor)  │
                    └───┬───┬───┬───┬───┬──────┘
                        │   │   │   │   │
              ┌─────────┘   │   │   │   └──────────┐
              ▼             ▼   ▼   ▼              ▼
       ┌──────────┐  ┌────────┐ ┌────────┐  ┌──────────┐
       │OCR Agent │  │Chat    │ │RAG     │  │Analysis  │  ...更多
       │ ★当前★   │  │Agent   │ │Agent   │  │Agent     │
       │          │  │(对话)  │ │(搜索)  │  │(分析)    │
       └──────────┘  └────────┘ └────────┘  └──────────┘
            │
   独立状态、独立记忆、
   标准化 Tool 接口
```

### 2.2 Agent 自治边界

| 维度 | OCR Agent 的边界 |
|------|------------------|
| **状态** | 独立管理 upload session 生命周期（LangGraph checkpoint） |
| **记忆** | 独立管理公司映射记忆（PostgreSQL + pg_trgm，无向量数据库） |
| **接口** | 通过 Tool 协议暴露能力，不暴露内部实现 |
| **模型** | 独立决定用哪个 AI 模型（Gemini Flash 提取 / Claude 映射） |
| **数据** | 只读写自己的表（`ai_ocr_*`），写入 LG 通过标准 Writer 接口 |

### 2.3 Agent Tool 接口定义

OCR Agent 对外暴露 5 个 Tool，调用方可以是前端 REST API 或未来的 Orchestrator：

```
Tool 1: upload_and_extract
  描述: 上传财务文件并触发 AI 提取
  Input:  { files: File[], company_id: int }
  Output: { session_id: str, status: str }

Tool 2: get_session_status
  描述: 查询提取/映射进度
  Input:  { session_id: str }
  Output: { status, progress_pct, tables: ExtractedTable[], mappings: MappingResult[] }

Tool 3: update_review
  描述: 提交用户审核编辑（行编辑、映射修改、删除噪音）
  Input:  { session_id: str, edits: RowEdit[], mapping_overrides: MappingOverride[] }
  Output: { success: bool, validation_errors: str[] }

Tool 4: commit_to_lg
  描述: 验证并写入 LG 数据库
  Input:  { session_id: str, conflict_resolutions: Resolution[], notes: Note[] }
  Output: { success: bool, written_periods: str[], conflicts: Conflict[] }

Tool 5: query_mapping_memory
  描述: 查询公司映射记忆（供其他 Agent 参考）
  Input:  { company_id: int, labels: str[] }
  Output: { matches: MappingMemory[] }
```

### 2.4 设计原则

**"框架从具体 Agent 中长出来，而不是先造框架再填 Agent"**

```
Phase 1 (当前): 先做 OCR Agent，按 Tool 接口标准
                     │
                     ▼  真实数据验证提取质量、映射准确率
Phase 2: 第二个 Agent（Chat/RAG）上线
                     │
                     ▼  沉淀出真正的 Agent 通信需求
Phase 3: Orchestrator 自然浮现
```

LangGraph 的天然优势：OCR Agent 本身就是一个 `CompiledGraph`，未来直接作为 Supervisor 的一个 node，**零重构**：

```
现在:  ocr_graph = StateGraph(...).compile()     # 独立运行
未来:  supervisor.add_node("ocr", ocr_graph)     # 当节点塞进去
```

---

## 3. 技术选型

### 3.1 整体技术栈

| 层级 | 选型 | 理由 |
|------|------|------|
| **前端** | React + Ant Design Pro + dva | 与现有 CIOaas-web 一致 |
| **API 网关** | CIOaas-api (Spring Cloud Gateway) | 已有路由转发，加 `/api/v1/ocr/**` |
| **业务后端** | CIOaas-python (FastAPI) | 已有 AI 集成能力，Python 生态最适合 |
| **工作流编排** | LangGraph | 显式状态图，可持久化断点续跑，未来扩展 Agent/RAG |
| **结构化输出** | Instructor + Pydantic | LLM 输出强制类型安全，自动重试验证 |
| **模型路由** | OpenRouter | 多模型按需切换，避免供应商锁定 |
| **文档预处理** | Unstructured.io | 开源，PDF/Excel/Image 全格式支持 |
| **向量检索（RAG 阶段）** | PostgreSQL + pgvector | 与现有 DB 统一，无额外组件（OCR 阶段不使用，延迟到 RAG 阶段） |
| **文件存储** | AWS S3 (SSE 加密) | 已有基础设施 |
| **RAG（未来）** | pgvector + 自定义 pipeline | 文档问答、知识库检索（自写 chunking/embedding/recall/re-ranking，不用 Bedrock KB） |

### 3.2 AI 框架选型决策

#### 为什么选 LangGraph 而不是 LangChain

| 维度 | LangChain (legacy chains) | LangGraph |
|------|--------------------------|-----------|
| 编排模式 | 隐式链式调用 | **显式状态图（Graph）** |
| 调试 | 抽象层深，难以定位 | **每个节点可独立测试** |
| 状态管理 | 需外部存储 | **内置 PostgreSQL checkpoint** |
| 可视化 | 无 | **自动生成流程图** |
| 稳定性 | API 频繁 breaking change | 独立包，相对稳定 |
| 适合场景 | 简单 prompt chain | **状态机、Agent、多步工作流** |

**当前场景**: OCR Pipeline 本身就是多步状态机（上传→提取→映射→审核→写入），LangGraph 的状态图是天然匹配。

**未来扩展**: 对话式 AI、RAG 搜索、Agent 工具调用 — 都是 LangGraph 的核心场景，统一范式。

#### 为什么用 Instructor 而不是 LangChain 的 Output Parser

| 维度 | LangChain Output Parser | Instructor + Pydantic |
|------|------------------------|----------------------|
| 类型安全 | 运行时解析，可能失败 | **编译期验证，Pydantic 强制** |
| 自动重试 | 需手动实现 | **内置 max_retries** |
| 模型兼容 | LangChain 生态内 | **兼容任何 OpenAI 兼容 API** |
| 代码量 | 多 | **少 60%** |
| 学习曲线 | 需理解 Chain 生态 | **只需会 Pydantic** |

#### 为什么用 OpenRouter 做模型路由

| 优势 | 说明 |
|------|------|
| 多模型切换 | 同一个 API 访问 Gemini/Claude/GPT — 按任务选最优模型 |
| 成本优化 | 提取用便宜模型（Gemini Flash），映射用强模型（Claude） |
| 无供应商锁定 | 某家 API 故障可秒级切换 |
| OpenAI SDK 兼容 | Instructor/LangGraph 直接对接，零适配成本 |
| 统一计费 | 一个 API key 管理所有模型消耗 |

#### AI Vision 替代传统 OCR（eSapiens）的理由

| 维度 | 传统 OCR (eSapiens) | AI Vision (Gemini/Claude) |
|------|---------------------|--------------------------|
| 表格识别 | 规则 + ML | **LLM 视觉理解** |
| 无边框表格 | 差 | **好** |
| 理解上下文 | 不能（纯文字提取） | **能**（知道 Revenue 是收入） |
| 格式标准化 | 需大量后处理 | **Pydantic 直接输出结构化** |
| 持续改进 | 需重训模型 | **Few-shot 即时生效** |
| 供应商风险 | 依赖单一供应商 | OpenRouter 可切换模型 |
| 成本（10 页 PDF） | ~$0.10-0.50 | **~$0.01（Gemini Flash）** |

### 3.3 模型路由策略

按任务类型和复杂度选择模型，平衡成本与质量:

```
任务类型          复杂度     模型                    成本 (1M tokens)
─────────────────────────────────────────────────────────────────
文档提取          低/中      Gemini 2.5 Flash        $0.15
文档提取          高(复杂)   Claude Sonnet 4         $3.00
文档类型识别      任意       Gemini 2.5 Flash        $0.15
账户映射(LLM层)   中/高      Claude Sonnet 4         $3.00
Embedding(RAG阶段) 任意       text-embedding-3-small  $0.02
```

**单次典型上传成本估算**（10 页 PDF，~80 行数据）:

| 步骤 | 模型 | 预估成本 |
|------|------|----------|
| 提取 10 页 | Gemini Flash | ~$0.01 |
| 文档分类 | Gemini Flash | ~$0.001 |
| 映射（~12 行走 LLM） | Claude Sonnet | ~$0.01 |
| **总计** | | **~$0.02** |

---

## 4. 系统架构

### 4.1 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│                     CIOaas-web (React)                        │
│   UploadPage → ExtractingPage → ReviewPage → ConfirmPage     │
│        ↕              ↕              ↕            ↕          │
│     Tool 1        Tool 2         Tool 3       Tool 4         │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST API (= Agent Tool 协议)
┌───────────────────────────┴──────────────────────────────────┐
│                   CIOaas-api (Java Gateway)                   │
│               路由转发 /api/v1/ocr/** → Python                │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ OCR Agent 边界 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
│                                                              │
│  Tool 接口层 (5 个标准 Tool)                                  │
│  ┌────────────┬───────────┬────────────┬──────────┬───────┐  │
│  │upload_and_ │get_session│update_     │commit_to_│query_ │  │
│  │extract     │_status    │review      │lg        │memory │  │
│  └─────┬──────┴─────┬─────┴──────┬─────┴────┬─────┴───────┘  │
│        ▼            ▼            ▼          ▼                │
│  ┌─────────────────────────────────────────────────────┐     │
│  │          LangGraph Pipeline (状态图)                 │     │
│  │                                                     │     │
│  │  [Preprocess] → [Extract] → [Map] → [Validate]     │     │
│  │       │             │          │          │         │     │
│  │  Unstructured   Instructor  三层映射   冲突检测      │     │
│  │                 + OpenRouter  引擎                   │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  Agent 记忆层                                                │
│  ┌────────────────────────────────────────┐                   │
│  │ 公司映射记忆 (PostgreSQL + pg_trgm)     │                   │
│  │ 精确匹配 + trigram 模糊匹配             │                   │
│  │ 同行业频率 SQL 查询（跨公司模式）        │                   │
│  └────────────────────────────────────────┘                   │
│                                                              │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘

共享基础设施（未来其他 Agent 也使用）
┌──────────┐  ┌──────────────┐  ┌─────────────┐
│   S3     │  │  OpenRouter  │  │ PostgreSQL  │
│ (文件)   │  │  (AI 模型)   │  │(业务+ckpt)  │
└──────────┘  └──────────────┘  └─────────────┘
                                  ↑ RAG 阶段将启用 pgvector 扩展
```

**架构分层说明**:
- **Tool 接口层**: OCR Agent 对外暴露的 5 个标准 Tool，当前前端调用，未来 Orchestrator/其他 Agent 也通过同一接口调用
- **Pipeline 层**: LangGraph 状态图，Agent 的核心逻辑
- **记忆层**: Agent 独立管理的持久化记忆（仅 PostgreSQL + pg_trgm，OCR 阶段不使用向量数据库）
- **共享基础设施**: PostgreSQL/S3/OpenRouter 等，所有 Agent 复用但数据隔离（表前缀区分）

### 4.2 Pipeline 状态机

```
UPLOAD ──→ PREPROCESS ──→ EXTRACT ──→ MAP ──→ VALIDATE ──→ REVIEW ──→ COMMIT
  │            │              │         │         │           │          │
  ↓            ↓              ↓         ↓         ↓           ↓          ↓
FAILED      FAILED         FAILED   FAILED   ┌─CONFLICT   (用户      FAILED
                                              │  RESOLVE    编辑)
                                              ↓
                                           用户选择
                                        Overwrite/Skip/Cancel
```

**LangGraph 状态图的优势**:
- 每个节点独立运行、独立测试
- 状态自动持久化到 PostgreSQL — 用户关浏览器后可恢复
- 任何节点失败都可从上一个 checkpoint 重试
- `langgraph.visualize()` 自动生成可视化流程图

### 4.3 LangGraph 节点职责

| 节点 | 输入 | 输出 | 依赖组件 |
|------|------|------|----------|
| **Preprocess** | 上传的原始文件 | 标准化的图片/JSON | Unstructured.io, pdf2image |
| **Extract** | 图片/JSON | `ExtractedTable[]` (Pydantic) | Instructor + OpenRouter (Gemini Flash) |
| **Map** | `ExtractedTable[]` | `MappingResult[]` | 三层映射引擎 |
| **Validate** | 提取数据 + 映射结果 | 错误列表 + 冲突列表 | PostgreSQL (已有数据对比) |

**条件路由**:
- Validate 通过 → END（进入前端审核）
- 有阻塞错误 → 返回错误信息
- 有数据冲突 → 进入冲突解决流程

---

## 5. AI 提取引擎

### 5.1 提取流程

```
原始文件
  │
  ├── PDF/图片 ──→ Unstructured.io ──→ 每页转为 Base64 图片
  │                                         │
  │                                   Gemini Flash (Vision)
  │                                   + Instructor (Pydantic)
  │                                         │
  │                                   ExtractedTable 结构化输出
  │
  └── Excel/CSV ──→ openpyxl/pandas 解析
                          │
                    处理合并单元格、公式求值
                          │
                    转换为同一 ExtractedTable 结构
                          ↓
                    ┌──────────────────────┐
                    │  统一的 Pydantic 模型  │
                    │  ExtractedTable       │
                    │  ├── document_type    │
                    │  ├── currency         │
                    │  ├── reporting_periods│
                    │  └── rows[]           │
                    │       ├── label       │
                    │       ├── values{}    │
                    │       ├── is_header   │
                    │       └── is_total    │
                    └──────────────────────┘
```

**关键设计**: PDF/图片和 Excel 两条路径最终输出**完全相同的 Pydantic 结构**，下游映射和审核逻辑无需区分数据来源。

### 5.2 Instructor + Pydantic 的价值

```
传统 OCR 流程:
  OCR 引擎 → 原始文本 → 正则/规则解析 → 表格结构 → 验证修正 → JSON
  (5 步，每步都可能出错，需要大量胶水代码)

AI Vision + Instructor 流程:
  Vision 模型 → Pydantic 结构化输出 → 自动验证（不符合自动重试）
  (1 步，类型安全，自动重试)
```

Instructor 的 `max_retries=3` 机制: 如果模型输出不符合 Pydantic schema（字段缺失、类型错误），自动将验证错误反馈给模型重新生成，无需人工干预。

### 5.3 文档类型识别

三类信号加权评分，每种信号独立贡献分数:

```
信号类型            权重    示例
────────────────────────────────────────────────────────
Sheet Name 关键词    3      "P&L" / "Balance Sheet" / "Cash Flow"
Row Label 模式       2/项   Revenue, COGS, EBITDA → P&L 指标
结构线索             4-5    Assets = Liabilities + Equity → Balance Sheet

评分阈值:
  ≥ 8 分 → HIGH confidence
  ≥ 4 分 → MEDIUM confidence
  ≥ 2 分 → LOW confidence
  < 2 分 → "MISC"（标记用户确认）
```

---

## 6. AI 映射引擎（三层架构）

### 6.1 架构总览

```
待映射行项
    │
    ▼
┌───────────────────────────────────────┐
│  Layer 1: 规则引擎 (Keywords)          │  覆盖 ~60%
│  零成本，毫秒级，完全确定性            │  零 AI 调用
│  按优先级排序解决关键词冲突            │
├───────────────────────────────────────┤
│         ↓ 未匹配的行项                 │
├───────────────────────────────────────┤
│  Layer 2: 公司记忆 (DB 匹配)          │  覆盖 ~25%
│  精确匹配 + trigram 模糊匹配           │  零 AI 调用
│  基于该公司历史上确认过的映射          │
├───────────────────────────────────────┤
│         ↓ 仍未匹配的行项               │
├───────────────────────────────────────┤
│  Layer 3: LLM 推理 (Claude Sonnet)    │  覆盖 ~15%
│  Few-Shot 动态注入（公司+全局记忆）     │  唯一产生 AI 成本的层
│  Instructor 强制结构化输出             │
│  批量处理减少 API 调用                 │
└───────────────────────────────────────┘
    │
    ▼
MappingResult (category + confidence + source + reasoning)
```

**为什么三层而不是全用 LLM？**

| 方案 | 成本 | 延迟 | 可预测性 |
|------|------|------|----------|
| 全 LLM | 高（每行都调 API） | 高 | 低（LLM 可能不一致） |
| 全规则引擎 | 零 | 零 | 高但覆盖率不足 |
| **三层混合** | **低（仅 15% 走 LLM）** | **低** | **高（确定性优先）** |

### 6.2 Layer 1: 规则引擎 — 优先级体系

规则引擎的核心挑战是**关键词冲突**（如 `hosting` 同时出现在 COGS 和 R&D）。通过 5 级优先级解决:

```
Priority 1（最精确 — 专有名词匹配）
  ├── R&D Capitalized: "capitalized r&d", "amortization of software"
  ├── Accounts Payable: "accounts payable", "a/p"
  ├── Accounts Receivable: "accounts receivable", "a/r"
  └── Long Term Debt: "long term debt", "convertible note"

Priority 2（需上下文 — Payroll 部门识别）
  ├── S&M Payroll: payroll 关键词 + sales/marketing 上下文
  └── R&D Payroll: payroll 关键词 + r&d/engineering 上下文

Priority 3（兜底分类）
  ├── Payroll UNMAPPED: payroll 关键词，无部门上下文 → 标记 UNMAPPED (LOW confidence)，需用户审核
  └── COGS: "cost of goods", "materials"（排除 R&D 关键词）

Priority 4（费用大类）
  ├── Revenue: "revenue", "sales", "income"（排除 "cost of"）
  ├── S&M Expenses: "marketing", "advertising", "commission"
  ├── R&D Expenses: "research", "development", "engineering"
  └── G&A Expenses: "g&a", "rent", "legal", "accounting"

Priority 5（Balance Sheet 兜底）
  └── Cash: "cash", "bank", "savings"
```

**匹配逻辑**:
- 从 Priority 1 开始逐级匹配
- 每条规则有 `negative_keywords`（排除词）防止误匹配
- 需要 `requires_context` 的规则会检查行标签和 section header
- 首个匹配即停止 → 高优先级总是胜出

**置信度映射**:
- Priority 1-2 → HIGH
- Priority 3-4 → MEDIUM
- Priority 5 → LOW

### 6.3 Layer 2: 公司记忆 — 精确+模糊匹配

```
用户确认映射
    │
    ▼ 保存到 company_mapping_memory 表
    │
未来同公司上传
    │
    ├── 精确匹配: "AWS Infrastructure" = "AWS Infrastructure" → HIGH
    │
    └── 模糊匹配: "AWS Infra Costs" ≈ "AWS Infrastructure" (相似度 > 0.6) → MEDIUM
        (PostgreSQL pg_trgm 扩展提供 trigram 相似度计算)
```

**记忆质量控制**:
- `frequency` 字段: 被确认次数 — frequency < 3 的标记为 provisional
- `last_used_at` 字段: 12 个月未使用的自动归档
- 用户覆盖时以最新决策为准

### 6.4 Layer 3: LLM 推理 — Few-Shot 动态注入

```
┌─────────────────────────────────────────────┐
│               LLM Prompt 构成                │
│                                             │
│  System Prompt (固定)                        │
│  ├── 19 个 LG 分类定义                      │
│  ├── 映射规则（Payroll 处理、OI/OE 分类等）   │
│  └── 输出格式要求（JSON + reasoning）        │
│                                             │
│  Few-Shot Examples (动态注入)                │
│  ├── 公司记忆: 最相关的 ≤20 条历史映射       │  ← Layer 2 DB 查询 (pg_trgm)
│  └── 同行业记忆: 跨公司高频映射 ≤10 条       │  ← 同行业频率 SQL 查询
│                                             │
│  User Prompt                                │
│  ├── Company context (industry)             │
│  ├── Document type                          │
│  ├── Section header                         │
│  └── 待映射行项列表 (JSON)                   │
└─────────────────────────────────────────────┘
```

**Few-Shot 比 Fine-tuning 的优势**:

| 维度 | Few-Shot 动态注入 | Fine-tuning |
|------|-------------------|-------------|
| 反馈生效时间 | **即时** | 需重新训练（小时/天） |
| 成本 | prompt 多几百 token | GPU 训练 + 模型托管 |
| 可审计 | **完全透明** — 知道用了哪些案例 | 黑盒 |
| 回滚 | 删除错误记忆即可 | 需回退模型版本 |
| 多公司隔离 | **天然隔离** | 需多个 adapter |

**LLM Prompt 关键设计决策**:

| 决策 | 理由 |
|------|------|
| System prompt 列出全部 19 个分类 | 防止 LLM 幻觉出不存在的分类 |
| 传入 `document_type` | Balance Sheet 的 "Revenue" 可能是 "Deferred Revenue"（负债） |
| 传入 `section_header` | "R&D" section 下的 "Salary" → R&D Payroll |
| 传入 `industry` | SaaS 的 "hosting" → COGS；制造业 → G&A |
| 批量处理 | 减少 API 调用，LLM 可利用同文档上下文 |
| 要求 `reasoning` | 审计追溯 + 用户审核参考 |

### 6.5 完整映射规则（财务 SME Nico Carlson 已确认）

#### Income Statement (P&L) 分类

| LG 分类 | 关键词 | 排除词 | 特殊规则 |
|---------|--------|--------|----------|
| **Revenue** | sales, revenue, income, fees, subscriptions, gross receipts | cost of, expense, other income, deferred | refund/returns/contra → 仍为 Revenue 但标负值 |
| **COGS** | cogs, cost of goods, cost of revenue, materials, inventory, direct labor, supplies used, fulfillment, shipping, freight, delivery | research, development | hosting/cloud/server → **SaaS 公司归 COGS，非 SaaS 归 R&D** |
| **S&M Expenses** | marketing, advertising, promotion, campaign, commission, customer acquisition, lead generation, trade show, sponsorship, customer success, merchant fees | payroll, salary | |
| **R&D Expenses** | research, development, r&d, engineering, product development, software development, technical consulting, qa, devops | payroll, salary, capitalized | |
| **G&A Expenses** | general and administrative, g&a, overhead, rent, lease, utilities, legal, audit, accounting, insurance, hr, recruiting | payroll, salary | |
| **S&M Payroll** | wages, salary, payroll, compensation, benefits | | 需 sales/marketing/s&m 上下文 |
| **R&D Payroll** | wages, salary, payroll, compensation, benefits | | 需 r&d/research/engineering 上下文 |
| **G&A Payroll** | wages, salary, payroll, compensation, benefits, payroll taxes | | 需 g&a/general/admin/office 上下文 |
| *(Payroll UNMAPPED)* | wages, salary, payroll, compensation, benefits | | **无部门上下文时**: 标记为 UNMAPPED，confidence = LOW，需用户审核确认部门 |
| **Other Income** | other income, interest income, gain on sale, miscellaneous income | | 单独分类，不与 Other Expense 互抵；互抵在下游 normalization engine 执行 |
| **Other Expense** | other expense, interest expense, loss on sale, miscellaneous expense | | 单独分类，不与 Other Income 互抵；互抵在下游 normalization engine 执行 |

#### Balance Sheet 分类

| LG 分类 | 关键词 | 特殊规则 |
|---------|--------|----------|
| **Cash** | cash, bank, checking, savings, cash equivalents, money market, treasury | |
| **Accounts Receivable** | accounts receivable, a/r, receivables, trade receivables, unbilled revenue | |
| **R&D Capitalized** | capitalized r&d, capitalized research, capitalized development, internal-use software, amortization of software, amortization of intangibles | **需双重信号**: (资本化 + R&D 上下文) 或 (摊销关键词) |
| **Other Assets** | | 被识别为 Asset 但不属于 Cash/AR/R&D Capitalized 的兜底 |
| **Accounts Payable** | accounts payable, a/p, payables, trade payables | |
| **Short Term Debt** | short term debt, current portion, line of credit | 仅限短期上下文；排除 "long term" |
| **Long Term Debt** | long term debt, loan, note payable, term loan, convertible note, venture debt, credit facility, revolving | 排除 "short term" |
| **Other Liabilities** | | 被识别为 Liability 但不属于 AP/Short Term Debt/Long Term Debt 的兜底 |
| **Equity** | equity, stockholders equity, shareholders equity, retained earnings, common stock, additional paid-in capital | |

#### Cash Flow Statement 处理

> **注意**: Cash Flow Statement 行项会被 AI 提取并保存为原始数据（raw data），但**不进行 LG 分类映射**。CF 数据保留供参考和未来分析，但不纳入上述 P&L / Balance Sheet 分类体系。提取时 `document_type` 标记为 `cash_flow_statement`，映射阶段跳过这些行项。

---

## 7. 持续学习系统

持续学习系统使 OCR Agent 能够从用户审核反馈中不断改进映射准确率：

- **两层记忆架构**: 通用层（~500 条种子数据，所有公司共享）+ 公司层（每公司最多 5,000 条，用户确认时自动学习）
- **学习闭环**: 第 1 次上传走 LLM → 用户确认 → 保存记忆 → 第 2 次上传同标签直接命中，零 LLM 调用
- **跨公司经验共享**: 同行业高频映射通过 SQL 聚合查询注入 Few-Shot（OCR 阶段不使用向量数据库）
- **信任提升**: 记忆从 `is_trusted=FALSE` 提升到 `TRUE` 需满足确认次数阈值
- **冲突解决**: 用户修正与已有记忆矛盾时，旧记忆归档，新映射需重新达到信任阈值
- **版本管理**: 双轨版本控制（`core_engine_version` + `company_memory_version`），确保审计追溯
- **质量控制**: `frequency < 3` 标记 provisional 不参与 Few-Shot；TTL 12 个月自动归档

> **完整设计**: 记忆系统的两层架构、查询策略、信任提升规则、冲突解决机制、种子数据、生命周期管理和审计设计见 [system-architecture.md](./system-architecture.md) 第 6 章。

---

## 8. 前端设计

### 8.1 页面路由

所有页面挂载在 `/financial` 路由前缀下，通过 `sessionId` 串联完整流程：

```
路由                                  组件               说明
────────────────────────────────────────────────────────────────────────────
/financial/upload                    UploadPage          Step 1: 文件上传 + 队列管理
/financial/upload/:sessionId         ProcessingPage      Step 2: AI 提取进度（自动跳转）
/financial/review/:sessionId         ReviewPage          Step 3: 并排审核 + 内联编辑（核心页面）
/financial/confirm/:sessionId        ConfirmPage         Step 4+5: 冲突解决 + 最终提交
```

**UmiJS 路由配置** (`config/routes.ts`):

```typescript
{
  path: '/financial',
  routes: [
    {
      path: '/financial/upload',
      component: './Financial/Upload/UploadPage',
      name: 'financial-upload',
    },
    {
      path: '/financial/upload/:sessionId',
      component: './Financial/Upload/ProcessingPage',
      name: 'financial-processing',
    },
    {
      path: '/financial/review/:sessionId',
      component: './Financial/Review/ReviewPage',
      name: 'financial-review',
    },
    {
      path: '/financial/confirm/:sessionId',
      component: './Financial/Confirm/ConfirmPage',
      name: 'financial-confirm',
    },
  ],
}
```

**导航守卫**:
- `ProcessingPage`: 如果 session 状态已是 `COMPLETED`，直接 `history.replace` 到 ReviewPage
- `ReviewPage`: 如果 session 状态不是 `COMPLETED`，重定向回 ProcessingPage
- `ConfirmPage`: 如果存在未通过的硬验证，重定向回 ReviewPage 并显示错误提示

### 8.2 组件层级

#### UploadPage

```
UploadPage
  ├── UploadZone
  │     拖拽区域 + 文件选择按钮
  │     支持格式提示: PDF, Excel (.xlsx/.xls), CSV, 图片 (PNG/JPG)
  │     单文件 ≤ 20MB，批量 ≤ 100MB
  │
  ├── FileQueue
  │     └── FileQueueItem (每个上传文件)
  │           ├── 文件图标 (根据 MIME 类型)
  │           ├── 文件名 + 文件大小
  │           ├── 文件类型标签 (PDF / Excel / CSV / Image)
  │           ├── 进度条 (antd Progress, 上传中显示百分比)
  │           ├── 状态徽章 (Pending / Uploading / Completed / Error)
  │           └── 删除按钮 (上传完成前可移除)
  │
  └── BatchActions
        ├── Upload All 按钮 (primary, 触发批量上传)
        └── Clear All 按钮 (danger-link, 清空队列)
```

**UploadZone 组件行为**:
- 使用 antd `Upload.Dragger` 作为基础，自定义样式
- 拖拽时高亮边框变为 `primary` 色
- 客户端预校验：文件类型（MIME + 扩展名双检）、单文件大小、总大小
- 校验失败立即在 FileQueueItem 上显示 Error 状态 + 原因文案
- 重复文件检测（同名 + 同大小），提示用户确认是否重复上传

#### ProcessingPage

```
ProcessingPage
  ├── SessionHeader
  │     上传会话 ID + 文件数量摘要
  │
  ├── ProcessingStatus
  │     ├── 整体进度条 (总百分比)
  │     ├── 当前步骤描述
  │     │     PENDING    → "排队等待处理..."
  │     │     PROCESSING → "正在进行 AI 提取... (已完成 45%)"
  │     │     COMPLETED  → "提取完成，正在跳转..." (自动 redirect)
  │     │     FAILED     → "处理失败"
  │     └── 文件级进度列表
  │           └── FileProcessItem (每个文件: 名称 + 状态 + 进度)
  │
  └── ErrorActions (仅 FAILED 时显示)
        ├── RetryButton (重新触发提取)
        └── BackButton (返回上传页重新上传)
```

#### ReviewPage（核心页面）

```
ReviewPage
  ├── TableSelector
  │     antd Tabs 组件
  │     Tab 1: "Income Statement (2024_PnL.pdf)" / Tab 2: "Balance Sheet (BS.xlsx)" / ...
  │     每个 Tab 显示: 表名 + 来源文件名 + 置信度汇总 (✓ 12 / ⚠ 5 / ✗ 2)
  │
  ├── SplitView (antd Row + Col, 可拖拽分割线, 默认 50/50)
  │     │
  │     ├── SourcePanel（左侧 — 原始文档）
  │     │     ├── PDFViewer
  │     │     │     react-pdf 渲染
  │     │     │     页码导航: 上一页 / 下一页 / 页码输入跳转
  │     │     │     缩放控制: 放大 / 缩小 / 适应宽度
  │     │     │     当前高亮区域标记 (对应右侧选中行的源位置)
  │     │     │
  │     │     └── ExcelPreview
  │     │           antd Table 只读渲染
  │     │           Sheet 切换标签页 (多 sheet 时)
  │     │           高亮行 (对应右侧选中行的源单元格)
  │     │           合并单元格正确渲染 (colSpan/rowSpan)
  │     │
  │     └── DataPanel（右侧 — 提取数据）
  │           ├── ViewToggle
  │           │     antd Radio.Group: [Raw] [Standardized]
  │           │     Raw: 显示 AI 提取的原始行标签和值
  │           │     Standardized: 显示映射后的 LG 分类、标准化数值
  │           │
  │           ├── EditableTable
  │           │     基于 react-window FixedSizeList 虚拟滚动
  │           │     列定义:
  │           │       - Row #（行号，只读）
  │           │       - Account Label（Raw 视图）/ LG Category（Standardized 视图）
  │           │       - 各月份/期间列（动态，从 reporting_periods 生成）
  │           │       - Confidence（置信度徽章）
  │           │       - Actions（删除行按钮）
  │           │     │
  │           │     ├── EditableCell
  │           │     │     默认: 纯文本渲染 (<span>)
  │           │     │     双击: 切换为 <Input> 受控模式
  │           │     │     失焦/回车: 保存编辑，切回文本
  │           │     │     修改后的单元格左上角显示蓝色三角标记
  │           │     │
  │           │     ├── CategoryDropdown
  │           │     │     仅 Standardized 视图可见
  │           │     │     antd Select, 19 个 LG 分类选项 + 分组:
  │           │     │       Income Statement: Revenue, COGS, S&M Expenses, R&D Expenses,
  │           │     │         G&A Expenses, S&M Payroll, R&D Payroll, G&A Payroll,
  │           │     │         Other Income, Other Expense
  │           │     │       Balance Sheet: Cash, Accounts Receivable, R&D Capitalized,
  │           │     │         Other Assets, Accounts Payable, Short Term Debt,
  │           │     │         Long Term Debt, Other Liabilities, Equity
  │           │     │     选择后立即标记为 user_override, confidence 变为 HIGH
  │           │     │
  │           │     └── ConfidenceBadge
  │           │           ✓ HIGH   — 绿色 Tag (antd Tag color="success")
  │           │           ⚠ MEDIUM — 橙色 Tag (antd Tag color="warning")
  │           │           ✗ UNMAPPED — 红色 Tag (antd Tag color="error")
  │           │           点击展开 Tooltip: 显示 mapping source + reasoning
  │           │
  │           └── ValidationBar (固定在 DataPanel 底部)
  │                 错误计数: "3 errors" (红色) + 警告计数: "5 warnings" (橙色)
  │                 点击展开详细列表，每条可点击定位到对应行
  │
  └── ActionBar (固定在页面底部)
        ├── Previous 按钮 (返回 ProcessingPage 或 UploadPage)
        ├── Save Draft 按钮 (手动触发保存，通常自动保存已覆盖)
        └── Next: Confirm 按钮 (primary, 触发硬验证后跳转 ConfirmPage)
```

**SplitView 分割线交互**:
- 默认 50/50 比例
- 鼠标拖拽分割线调整比例，最小 30%，最大 70%
- 双击分割线恢复 50/50
- 比例存储在 `localStorage` 中，刷新后保持

#### ConfirmPage

```
ConfirmPage
  ├── WriteSummary
  │     信息卡片列表:
  │     ├── 待写入表数量 (e.g. "2 tables")
  │     ├── 时间范围 (e.g. "Jan 2024 - Dec 2024")
  │     ├── 数据类型 (Historical / Forecast / Mixed)
  │     ├── 总行数统计
  │     └── 修改摘要 (用户编辑 N 行, 映射覆盖 M 条)
  │
  ├── ConflictList (仅冲突检测到时显示)
  │     ├── 冲突摘要: "发现 N 条与已有数据的冲突"
  │     └── ConflictItem (每条冲突)
  │           ├── 冲突位置: Table / Account / Period
  │           ├── 对比展示:
  │           │     已有值: $1,234,567 (source: QuickBooks, date: 2024-01-15)
  │           │     新值:   $1,234,890 (source: 当前上传)
  │           ├── 解决方案: antd Radio.Group
  │           │     ○ Overwrite (用新值覆盖)
  │           │     ○ Skip (保留已有值)
  │           │     ○ Cancel (从本次提交中移除此行)
  │           └── Note 字段: antd TextArea (≤ 2000 字, 可选)
  │                 placeholder: "说明覆盖原因..."
  │
  └── CommitButton
        antd Button type="primary" size="large"
        无冲突时: "Confirm & Write to LG"
        有冲突时: 所有冲突项必须选择解决方案后才可点击
        点击后: Loading 状态 → 成功跳转到 Success 页 / 失败显示错误
```

### 8.3 dva Model 设计

#### State 接口定义

```typescript
/** 上传文件项 */
interface UploadFileItem {
  uid: string;                    // 前端唯一标识
  fileId?: string;                // 后端返回的文件 ID
  fileName: string;
  fileType: 'pdf' | 'excel' | 'csv' | 'image';
  fileSize: number;               // bytes
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;               // 0-100
  errorMessage?: string;
  originFile: File;               // 原始 File 对象（不持久化）
}

/** 提取的表格 */
interface ExtractedTable {
  tableId: string;
  fileName: string;               // 来源文件名
  documentType: 'income_statement' | 'balance_sheet' | 'cash_flow_statement' | 'misc';
  docTypeConfidence: 'HIGH' | 'MEDIUM' | 'LOW';
  currency: string;
  reportingPeriods: string[];     // e.g. ["2024-01", "2024-02", ...]
  rows: ExtractedRow[];
}

/** 提取的行 */
interface ExtractedRow {
  rowId: string;
  accountLabel: string;           // 原始标签
  values: Record<string, number | null>;  // period → value
  isHeader: boolean;
  isTotal: boolean;
  sectionHeader?: string;         // 所属段落标题
  sourcePageNumber?: number;      // PDF 页码（用于左侧定位）
  sourceRowIndex?: number;        // Excel 行号（用于左侧高亮）
}

/** 映射结果 */
interface MappingResult {
  rowId: string;
  lgCategory: string;             // 19 个 LG 分类之一
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNMAPPED';
  source: 'rule_engine' | 'company_memory' | 'llm' | 'user_override';
  reasoning: string;
  originalAiSuggestion?: string;  // 用户覆盖前的原始建议
}

/** 用户编辑记录 */
interface RowEdit {
  rowId: string;
  field: string;                  // 'accountLabel' | period key
  oldValue: string | number | null;
  newValue: string | number | null;
}

/** 映射覆盖记录 */
interface MappingOverride {
  rowId: string;
  oldCategory: string;
  newCategory: string;
}

/** 冲突项 */
interface ConflictItem {
  conflictId: string;
  tableId: string;
  accountLabel: string;
  period: string;
  existingValue: number;
  existingSource: string;         // e.g. "QuickBooks"
  existingDate: string;           // 写入时间
  newValue: number;
  resolution?: 'overwrite' | 'skip' | 'cancel';
  note?: string;
}

/** 会话状态 */
interface SessionStatus {
  sessionId: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress: number;               // 0-100
  errorMessage?: string;
}

/** 验证错误 */
interface ValidationError {
  rowId: string;
  tableId: string;
  tableName: string;
  fileName: string;
  rowIndex: number;
  field: string;
  message: string;
}

/** 验证警告 */
interface ValidationWarning {
  rowId: string;
  tableId: string;
  field: string;
  message: string;
}

/** dva model state */
interface FinancialUploadModelState {
  // Upload
  fileList: UploadFileItem[];
  sessionId: string | null;

  // Processing
  sessionStatus: SessionStatus | null;
  pollingTimer: ReturnType<typeof setInterval> | null;  // 内部使用，不持久化

  // Review
  extractedTables: ExtractedTable[];
  mappingResults: Record<string, MappingResult>;  // rowId → MappingResult
  activeTableId: string | null;
  viewMode: 'raw' | 'standardized';
  editedRows: RowEdit[];
  mappingOverrides: MappingOverride[];
  selectedRowId: string | null;
  validationErrors: ValidationError[];
  validationWarnings: ValidationWarning[];

  // Auto-save
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  hasUnsavedChanges: boolean;

  // Confirm
  conflicts: ConflictItem[];
  commitStatus: 'idle' | 'committing' | 'success' | 'error';
  commitErrorMessage?: string;
}
```

#### Key Reducers

```typescript
reducers: {
  /** 设置文件列表（添加/移除文件） */
  setFileList(state, { payload }: { payload: UploadFileItem[] }) {
    return { ...state, fileList: payload };
  },

  /** 更新单个文件的上传进度 */
  updateUploadProgress(state, { payload }: { payload: { uid: string; progress: number; status?: string } }) {
    return {
      ...state,
      fileList: state.fileList.map(f =>
        f.uid === payload.uid
          ? { ...f, progress: payload.progress, ...(payload.status && { status: payload.status }) }
          : f
      ),
    };
  },

  /** 设置 AI 提取结果 */
  setExtractedTables(state, { payload }: { payload: { tables: ExtractedTable[]; mappings: Record<string, MappingResult> } }) {
    return {
      ...state,
      extractedTables: payload.tables,
      mappingResults: payload.mappings,
      activeTableId: payload.tables[0]?.tableId ?? null,
    };
  },

  /** 更新行数据（内联编辑） */
  updateRow(state, { payload }: { payload: RowEdit }) {
    const { rowId, field, oldValue, newValue } = payload;
    return {
      ...state,
      extractedTables: state.extractedTables.map(table => ({
        ...table,
        rows: table.rows.map(row =>
          row.rowId === rowId
            ? {
                ...row,
                ...(field === 'accountLabel'
                  ? { accountLabel: newValue as string }
                  : { values: { ...row.values, [field]: newValue as number } }),
              }
            : row
        ),
      })),
      editedRows: [...state.editedRows, payload],
      hasUnsavedChanges: true,
      saveStatus: 'idle' as const,
    };
  },

  /** 覆盖映射分类 */
  overrideMapping(state, { payload }: { payload: MappingOverride }) {
    return {
      ...state,
      mappingResults: {
        ...state.mappingResults,
        [payload.rowId]: {
          ...state.mappingResults[payload.rowId],
          lgCategory: payload.newCategory,
          confidence: 'HIGH',
          source: 'user_override',
          originalAiSuggestion: state.mappingResults[payload.rowId]?.lgCategory,
        },
      },
      mappingOverrides: [...state.mappingOverrides, payload],
      hasUnsavedChanges: true,
      saveStatus: 'idle' as const,
    };
  },

  /** 设置冲突解决方案 */
  setConflictResolution(state, { payload }: { payload: { conflictId: string; resolution: string; note?: string } }) {
    return {
      ...state,
      conflicts: state.conflicts.map(c =>
        c.conflictId === payload.conflictId
          ? { ...c, resolution: payload.resolution, note: payload.note }
          : c
      ),
    };
  },

  /** 设置会话状态（轮询更新） */
  setSessionStatus(state, { payload }: { payload: SessionStatus }) {
    return { ...state, sessionStatus: payload };
  },

  /** 设置保存状态 */
  setSaveStatus(state, { payload }: { payload: 'idle' | 'saving' | 'saved' | 'error' }) {
    return {
      ...state,
      saveStatus: payload,
      hasUnsavedChanges: payload === 'saved' ? false : state.hasUnsavedChanges,
    };
  },

  /** 切换视图模式 */
  setViewMode(state, { payload }: { payload: 'raw' | 'standardized' }) {
    return { ...state, viewMode: payload };
  },

  /** 选中行（触发左侧定位） */
  setSelectedRow(state, { payload }: { payload: string | null }) {
    return { ...state, selectedRowId: payload };
  },

  /** 删除行 */
  removeRow(state, { payload }: { payload: { tableId: string; rowId: string } }) {
    return {
      ...state,
      extractedTables: state.extractedTables.map(table =>
        table.tableId === payload.tableId
          ? { ...table, rows: table.rows.filter(r => r.rowId !== payload.rowId) }
          : table
      ),
      hasUnsavedChanges: true,
    };
  },

  /** 重置状态（离开页面时清理） */
  resetState() {
    return initialState;
  },
}
```

#### Key Effects

```typescript
effects: {
  /** 上传文件（multipart） */
  *uploadFiles({ payload }: { payload: { companyId: number } }, { call, put, select }) {
    const fileList: UploadFileItem[] = yield select(state => state.financialUpload.fileList);
    const pendingFiles = fileList.filter(f => f.status === 'pending');

    // Step 1: 创建会话
    const { sessionId } = yield call(createSession, { companyId: payload.companyId });
    yield put({ type: 'setState', payload: { sessionId } });

    // Step 2: 逐文件上传（并行最多 3 个）
    for (const file of pendingFiles) {
      yield put({ type: 'updateUploadProgress', payload: { uid: file.uid, progress: 0, status: 'uploading' } });
      try {
        const formData = new FormData();
        formData.append('file', file.originFile);
        const { fileId } = yield call(uploadFile, sessionId, formData, (progress: number) => {
          // onUploadProgress callback → dispatch updateUploadProgress
        });
        yield put({ type: 'updateUploadProgress', payload: { uid: file.uid, progress: 100, status: 'completed', fileId } });
      } catch (error) {
        yield put({ type: 'updateUploadProgress', payload: { uid: file.uid, status: 'error', errorMessage: error.message } });
      }
    }

    // Step 3: 触发 AI 提取
    yield call(triggerExtraction, sessionId);

    // Step 4: 跳转到 ProcessingPage
    history.push(`/financial/upload/${sessionId}`);
  },

  /** 轮询提取状态（2s 间隔） */
  *pollStatus({ payload }: { payload: { sessionId: string } }, { call, put }) {
    const POLL_INTERVAL = 2000;
    const MAX_POLLS = 150; // 最多 5 分钟
    let pollCount = 0;

    while (pollCount < MAX_POLLS) {
      const status: SessionStatus = yield call(getSessionStatus, payload.sessionId);
      yield put({ type: 'setSessionStatus', payload: status });

      if (status.status === 'COMPLETED') {
        // 提取完成，加载结果并跳转
        yield put({ type: 'fetchResult', payload: { sessionId: payload.sessionId } });
        history.replace(`/financial/review/${payload.sessionId}`);
        return;
      }

      if (status.status === 'FAILED') {
        // 失败，停止轮询，显示错误
        return;
      }

      // 等待 2s 再轮询
      yield call(delay, POLL_INTERVAL);
      pollCount += 1;
    }

    // 超时处理
    yield put({
      type: 'setSessionStatus',
      payload: { sessionId: payload.sessionId, status: 'FAILED', progress: 0, errorMessage: '处理超时，请重试' },
    });
  },

  /** 获取提取结果 */
  *fetchResult({ payload }: { payload: { sessionId: string } }, { call, put }) {
    const { tables, mappings } = yield call(getSessionResult, payload.sessionId);
    yield put({ type: 'setExtractedTables', payload: { tables, mappings } });
  },

  /** 提交审核编辑（自动保存） */
  *submitReview(_, { call, put, select }) {
    yield put({ type: 'setSaveStatus', payload: 'saving' });
    try {
      const { sessionId, editedRows, mappingOverrides } = yield select(state => state.financialUpload);
      yield call(updateReview, sessionId, { edits: editedRows, mapping_overrides: mappingOverrides });
      yield put({ type: 'setSaveStatus', payload: 'saved' });
      // 清空已保存的编辑队列
      yield put({ type: 'setState', payload: { editedRows: [], mappingOverrides: [] } });
    } catch (error) {
      yield put({ type: 'setSaveStatus', payload: 'error' });
    }
  },

  /** 提交写入 LG */
  *commitToLG(_, { call, put, select }) {
    yield put({ type: 'setState', payload: { commitStatus: 'committing' } });
    try {
      const { sessionId, conflicts } = yield select(state => state.financialUpload);
      const resolutions = conflicts
        .filter(c => c.resolution)
        .map(c => ({ conflictId: c.conflictId, resolution: c.resolution, note: c.note }));
      const result = yield call(commitToLG, sessionId, { conflict_resolutions: resolutions });
      if (result.success) {
        yield put({ type: 'setState', payload: { commitStatus: 'success' } });
        message.success(`成功写入 ${result.written_periods.length} 个期间的数据`);
      } else {
        // 返回新冲突（首次提交时检测到的）
        yield put({ type: 'setState', payload: { conflicts: result.conflicts, commitStatus: 'idle' } });
      }
    } catch (error) {
      yield put({ type: 'setState', payload: { commitStatus: 'error', commitErrorMessage: error.message } });
    }
  },
}
```

#### Subscriptions

```typescript
subscriptions: {
  /** 路由变化时清理轮询和重置状态 */
  routeChange({ dispatch, history }) {
    return history.listen(({ pathname }) => {
      // 离开 financial 路由时完全重置
      if (!pathname.startsWith('/financial')) {
        dispatch({ type: 'resetState' });
      }
      // 离开 ProcessingPage 时停止轮询
      if (!pathname.includes('/financial/upload/')) {
        dispatch({ type: 'stopPolling' });
      }
    });
  },
}
```

### 8.4 关键交互流程

#### 上传流程

```
用户拖拽/选择文件
  │
  ├── 客户端预校验
  │     ├── 文件类型检查: MIME type + 扩展名
  │     │     允许: application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
  │     │           application/vnd.ms-excel, text/csv, image/png, image/jpeg
  │     ├── 单文件大小: ≤ 20MB
  │     ├── 批量总大小: ≤ 100MB
  │     └── 校验失败 → FileQueueItem 立即显示 Error + 原因
  │
  ├── 文件加入 FileQueue (status: pending)
  │     显示: 文件名、类型图标、大小、Pending 徽章
  │
  ├── 用户点击 "Upload All"
  │     ├── POST /api/v1/ocr/sessions → 获取 sessionId
  │     ├── 逐文件 POST /api/v1/ocr/sessions/{id}/files (multipart)
  │     │     onUploadProgress → 实时更新进度条百分比
  │     │     成功 → status: completed, 绿色 ✓
  │     │     失败 → status: error, 红色 ✗, 显示重试按钮
  │     ├── 全部上传完成 → POST /api/v1/ocr/sessions/{id}/extract
  │     └── 自动跳转 → /financial/upload/:sessionId (ProcessingPage)
  │
  └── ProcessingPage 开始轮询
        GET /api/v1/ocr/sessions/{id}/status (每 2s)
```

#### 审核流程

```
ReviewPage 加载
  │
  ├── 获取提取结果 → 渲染 TableSelector + 第一个表格
  │
  ├── 点击表格行 (单击)
  │     ├── 设置 selectedRowId → 高亮右侧行
  │     ├── SourcePanel 联动:
  │     │     PDF: react-pdf 跳转到 row.sourcePageNumber 页
  │     │     Excel: 滚动到 row.sourceRowIndex 行并高亮
  │     └── ConfidenceBadge tooltip 显示 mapping reasoning
  │
  ├── 双击单元格 (数值/标签)
  │     ├── EditableCell 切换为 <Input> (受控模式)
  │     ├── 用户编辑 → 回车或失焦
  │     ├── dispatch updateRow → state 更新 + hasUnsavedChanges = true
  │     └── 触发 debounced submitReview (500ms)
  │
  ├── 修改分类 (Standardized 视图)
  │     ├── 点击 CategoryDropdown → antd Select 展开
  │     ├── 分组显示 19 个 LG 分类
  │     ├── 选择 → dispatch overrideMapping
  │     │     source 变为 'user_override'
  │     │     confidence 变为 'HIGH'
  │     │     ConfidenceBadge 变绿
  │     └── 触发 debounced submitReview (500ms)
  │
  ├── 切换 Raw ↔ Standardized 视图
  │     ├── dispatch setViewMode
  │     ├── 表格列定义切换（标签列 vs 分类列）
  │     └── 已有编辑保留（editedRows 和 mappingOverrides 不受影响）
  │
  └── 点击 "Next: Confirm"
        ├── 执行硬验证:
        │     1. Account Name 不为空
        │     2. Value 必须是数值
        │     3. Month 不为空且不是 "Unidentified"
        ├── 验证失败 → 显示精确错误:
        │     "2024_PnL.pdf → Table 1 → Row 5: Account Name is empty"
        │     点击错误可跳转到对应行
        └── 验证通过 → POST /api/v1/ocr/sessions/{id}/validate
              ├── 无冲突 → 跳转 ConfirmPage (conflicts = [])
              └── 有冲突 → 跳转 ConfirmPage (conflicts 填充)
```

**噪音数据清除**: 用户可通过右键菜单或行尾操作按钮执行 Remove Row / Remove Column，清除 AI 误提取的噪音数据后重新通过硬验证。

### 8.5 轮询状态管理

```
ProcessingPage mounted
  │
  ▼
开始轮询: GET /api/v1/ocr/sessions/{id}/status (每 2s)
  │
  ├── status = PENDING
  │     UI: 显示 "排队等待处理..."
  │     进度条: 不确定模式 (antd Progress status="active" 无百分比)
  │     继续轮询
  │
  ├── status = PROCESSING
  │     UI: 显示 "正在进行 AI 提取..."
  │     进度条: 显示 progress% (服务端返回的实际进度)
  │     文件级状态: 每个文件显示独立进度
  │     继续轮询
  │
  ├── status = COMPLETED
  │     UI: 显示 "提取完成，正在跳转..."
  │     进度条: 100%, 绿色
  │     ★ 停止轮询 (clearInterval)
  │     ★ 加载提取结果 (fetchResult effect)
  │     ★ history.replace → /financial/review/:sessionId
  │
  └── status = FAILED
        UI: 显示错误信息 (errorMessage 来自服务端)
        进度条: 红色
        ★ 停止轮询 (clearInterval)
        ★ 显示操作按钮:
            [重试] → POST /api/v1/ocr/sessions/{id}/extract → 重新开始轮询
            [返回] → history.push('/financial/upload')

超时保护:
  最大轮询次数 = 150 (2s × 150 = 5 分钟)
  超时 → 视同 FAILED，显示 "处理超时，请重试"

清理机制:
  ├── 组件 unmount → useEffect cleanup → clearInterval
  ├── 路由离开 → dva subscription → dispatch stopPolling
  └── 浏览器关闭 → 服务端 LangGraph checkpoint 保存状态
        用户重新访问同一 URL → 恢复到最近状态
```

### 8.6 大表格性能

目标: 流畅支持 1000+ 行表格，无卡顿。

**虚拟滚动方案**:

```
react-window FixedSizeList
  ├── 行高: 40px (固定)
  ├── 可视区域: 视口高度 / 40 ≈ 15-20 行
  ├── overscanCount: 10 (上下各预渲染 10 行)
  ├── 实际 DOM 节点: 30-40 个 (而非 1000+)
  └── 滚动时只替换内容，不创建/销毁 DOM
```

**EditableCell 性能优化**:

```
非激活状态 (99% 的时间):
  渲染: <span className="cell-text">{value}</span>
  零事件监听，零受控 state

激活状态 (双击时):
  渲染: <Input value={editValue} onChange={...} onBlur={...} onPressEnter={...} />
  仅当前单元格使用受控模式

切换机制:
  双击 → setActiveCellId(cellKey) → 仅 1 个单元格重渲染
  失焦 → setActiveCellId(null) → 恢复纯文本
```

**额外优化**:
- `React.memo` 包裹 `EditableCell`、`ConfidenceBadge`、`CategoryDropdown`
- `useMemo` 缓存列定义（仅 viewMode 或 reportingPeriods 变化时重算）
- 映射结果 (`mappingResults`) 使用 `rowId` 索引的 `Record`，O(1) 查找
- 避免在滚动事件中触发 state 更新

### 8.7 自动保存

**触发机制**:

```
用户编辑操作 (updateRow / overrideMapping / removeRow)
  │
  ▼
hasUnsavedChanges = true
  │
  ▼
debounce 500ms (lodash.debounce)
  │ (500ms 内的连续编辑合并为一次请求)
  │
  ▼
dispatch submitReview effect
  │
  ├── saveStatus = 'saving'
  │     UI: ActionBar 显示 "Saving..." + 旋转图标
  │
  ├── PATCH /api/v1/ocr/sessions/{id}/review
  │     请求体: 仅发送自上次保存以来的增量 diff
  │     {
  │       edits: RowEdit[],           // 新增的行编辑
  │       mapping_overrides: MappingOverride[]  // 新增的映射覆盖
  │     }
  │
  ├── 成功:
  │     saveStatus = 'saved'
  │     hasUnsavedChanges = false
  │     清空 editedRows/mappingOverrides 队列
  │     UI: ActionBar 显示 "All changes saved" + 绿色 ✓ (3s 后淡出)
  │
  └── 失败:
        saveStatus = 'error'
        hasUnsavedChanges = true (保留，下次重试)
        UI: ActionBar 显示 "Save failed — retry" + 红色 ✗
        点击 "retry" → 立即触发 submitReview
```

**浏览器关闭保护**:

```typescript
// ReviewPage 中注册 beforeunload
useEffect(() => {
  const handler = (e: BeforeUnloadEvent) => {
    if (hasUnsavedChanges) {
      e.preventDefault();
      e.returnValue = ''; // 浏览器标准：显示离开确认对话框
    }
  };
  window.addEventListener('beforeunload', handler);
  return () => window.removeEventListener('beforeunload', handler);
}, [hasUnsavedChanges]);
```

**路由离开保护**:

```typescript
// UmiJS Prompt 组件
<Prompt
  when={hasUnsavedChanges}
  message="有未保存的更改，确定要离开吗？"
/>
```

### 8.8 Mobile 策略

| 页面 | Mobile 策略 | 实现方式 |
|------|------------|----------|
| **UploadPage** | 完全响应式 | 隐藏拖拽区域，仅保留文件选择按钮；FileQueue 纵向堆叠；BatchActions 全宽按钮 |
| **ProcessingPage** | 完全响应式 | 进度条自适应宽度；文件列表纵向堆叠 |
| **ReviewPage** | Desktop Only | 检测视口宽度 < 1024px 时显示全屏提示页 |
| **ConfirmPage** | 完全响应式 | WriteSummary 卡片纵向堆叠；ConflictItem 改为纵向对比布局 |

**ReviewPage Desktop Only 实现**:

```typescript
// ReviewPage.tsx
const ReviewPage: React.FC = () => {
  const isDesktop = useMedia('(min-width: 1024px)');

  if (!isDesktop) {
    return (
      <Result
        icon={<DesktopOutlined style={{ color: '#999' }} />}
        title="请使用桌面浏览器进行数据审核"
        subTitle="并排审核和内联编辑功能需要更大的屏幕空间。请在宽度 ≥ 1024px 的桌面浏览器中打开此页面。"
        extra={
          <Button type="primary" onClick={() => history.push('/financial/upload')}>
            返回上传页
          </Button>
        }
      />
    );
  }

  return <ReviewPageContent />;
};
```

**响应式断点** (与现有 Ant Design Pro 保持一致):

| 断点 | 宽度 | 适用设备 |
|------|------|----------|
| xs | < 576px | 手机竖屏 |
| sm | >= 576px | 手机横屏 |
| md | >= 768px | 平板 |
| lg | >= 992px | 小桌面 |
| xl | >= 1200px | 标准桌面 |
| xxl | >= 1600px | 大屏 |

### 8.9 硬验证规则（ReviewPage → ConfirmPage 前置条件）

三要素必须完整:
1. **Account Name** — 不为空
2. **Value** — 必须是数值
3. **Month** — 不为空且不是 "Unidentified"

不满足时精确提示: `"2024_PnL.pdf" → Table 1 → Row 5: Account Name is empty`

用户可通过 Remove Row / Remove Column 清除噪音数据后通过验证。

---

## 9. API 设计

### 9.1 接口列表

```
Upload 阶段:
  POST   /api/v1/ocr/sessions                        创建上传会话
  POST   /api/v1/ocr/sessions/{id}/files              上传文件 (multipart)
  DELETE /api/v1/ocr/sessions/{id}/files/{fileId}      删除队列中文件
  POST   /api/v1/ocr/sessions/{id}/extract             触发 AI 提取

状态查询:
  GET    /api/v1/ocr/sessions/{id}/status              会话状态（轮询）
  GET    /api/v1/ocr/sessions/{id}/tables              提取的表格列表
  GET    /api/v1/ocr/tables/{tableId}/rows             表格行数据

审核编辑:
  PATCH  /api/v1/ocr/tables/{tableId}/rows/{rowId}            编辑行数据
  PATCH  /api/v1/ocr/tables/{tableId}/rows/{rowId}/mapping    修改映射
  DELETE /api/v1/ocr/tables/{tableId}/rows/{rowId}            删除噪音行
  DELETE /api/v1/ocr/tables/{tableId}/columns/{colKey}        删除噪音列

提交:
  POST   /api/v1/ocr/sessions/{id}/validate            验证 + 冲突检测
  POST   /api/v1/ocr/sessions/{id}/resolve              提交冲突解决方案
  POST   /api/v1/ocr/sessions/{id}/commit               写入 LG
```

### 9.2 Gateway 路由

在 CIOaas-api Gateway 添加路由:

```
/api/v1/ocr/** → http://cioaas-python:8090 (StripPrefix=0)
```

---

## 10. 数据模型

### 10.1 核心表

| 表 | 职责 | 关键字段 |
|----|------|----------|
| `ai_ocr_upload_session` | 一次上传会话 | company_id, status, uploaded_by |
| `ai_ocr_uploaded_file` | 单个上传文件 | session_id, filename, file_type, s3_key, status |
| `ai_ocr_extracted_table` | 提取的一张表 | file_id, document_type, doc_type_confidence, currency |
| `ai_ocr_extracted_row` | 提取的一行 | table_id, account_label, values(JSONB), section_header |
| `ai_ocr_mapping_result` | AI 映射结果 | row_id, lg_category, confidence, source, reasoning |
| `ai_ocr_company_mapping_memory` | 公司映射记忆 | company_id, account_label_pattern, lg_category, frequency |
| `ai_ocr_conflict_record` | 冲突解决记录 | session_id, resolution, user_note |

> **RAG 阶段**: 将新增 `rag_chunks` 表用于向量存储（pgvector），支持知识库检索和语义匹配。OCR 阶段不需要向量表。

完整 DDL 和索引设计见 [code-examples.md](./code-examples.md)。

### 10.2 关键索引

| 索引 | 类型 | 用途 |
|------|------|------|
| `idx_mapping_memory_label_trgm` | GIN (pg_trgm) | 公司记忆模糊匹配 |
| `idx_mapping_memory_industry` | B-tree (company.industry) | 同行业频率查询 |
| `idx_financial_data_conflict` | B-tree 复合索引 | 冲突检测快速查询 |

> **RAG 阶段**: 将新增 `idx_rag_chunks_hnsw` (HNSW, pgvector) 用于向量近似搜索。

---

## 11. 安全设计

| 层面 | 措施 |
|------|------|
| **文件安全** | `python-magic` 校验真实 MIME（不信任扩展名），Excel 用 `defusedxml` 防 XXE |
| **LLM 注入防御** | 用户文件名/行标签传入 LLM 前 sanitize（过滤 "ignore previous" 等） |
| **S3 存储** | Pre-signed URL (15 分钟有效)，SSE-S3 加密，bucket 禁止公开 |
| **权限** | Gateway JWT 校验 + Python 端二次校验 company_id 归属 |
| **数据驻留** | OpenRouter 数据政策: 不用于训练，但文件经过第三方需用户知情同意 |
| **审计** | MappingResult 保留 original_ai_suggestion + source，全流程时间戳 |

---

## 12. 边界情况

| 场景 | 处理方案 |
|------|----------|
| 同一行匹配多个分类 | 优先级排序，最精确的匹配胜出 |
| "Cloud Hosting" COGS vs R&D | 传入 company industry: SaaS → COGS，其他 → R&D |
| Payroll 无部门上下文 | 标记为 UNMAPPED，confidence = LOW，需用户审核确认部门归属 |
| 多页 PDF 含多种报表 | 按页分组独立识别 document_type |
| Excel 合并单元格 | openpyxl unmerge，填充值到子单元格 |
| 数值格式混乱 | 正则: `(1,234)` → `-1234`，逗号去除 |
| 用户中途关浏览器 | LangGraph checkpoint 自动恢复 |
| OCR 质量极差 | 提取行数 < 3 或数值识别率 < 50% → 建议重传 |
| 同公司同月已有数据 | 冲突检测 → Overwrite/Skip/Cancel |
| Balance Sheet 不平衡 | Soft warning（不阻止提交） |
| Other Income / Other Expense | 映射阶段分别归类为 Other Income 或 Other Expense，不互抵；互抵（OOE = expense - income）在下游 normalization engine 执行 |

---

## 13. 性能优化

| 项目 | 方案 |
|------|------|
| AI 提取延迟 (10 页 ~10-15s) | LangGraph 异步节点 + 前端进度轮询 |
| 大文件上传 | 分片上传 (chunk) + 断点续传 |
| 映射 LLM 调用 | 三层架构仅 ~15% 走 LLM；批量处理 |
| 公司记忆查询 | pg_trgm GIN 索引 |
| 同行业模式查询 | B-tree 索引 + SQL 聚合 |
| 前端大表格 | react-window 虚拟滚动 |
| 自动保存 | debounce 500ms，只发 diff |
| 断点续跑 | LangGraph PostgreSQL checkpoint |

---

## 14. 待确认问题

| # | 问题 | 阻塞级别 |
|---|------|----------|
| 1 | ~~OOE 作为计算指标 vs 映射目标~~ **已解决**: 映射阶段分别归类为 Other Income / Other Expense，互抵在 normalization engine 执行 | ~~P0~~ Done |
| 2 | hosting/cloud/server 默认归类？公司 industry 从哪获取？ | P1 |
| 3 | 多类型混合 PDF 用户分别上传还是系统切分？ | P1 |
| 4 | OpenRouter 数据安全政策是否满足合规？ | P1 |
| 5 | 已上传文件的删除/覆盖权限？ | P2 |
| 6 | Mobile 审核页面改为 Desktop Only？ | P2 |

---

## 15. 开发分期

| 阶段 | 范围 | 估算 |
|------|------|------|
| **Phase 1 (MVP)** | Upload + Excel 提取 (Instructor) + 规则引擎映射 + 简单审核 + 写入 LG | 3 sprint |
| **Phase 2** | AI Vision 提取 (Gemini Flash) + 并排审核 + 内联编辑 + 冲突检测 | 2 sprint |
| **Phase 3** | LLM 映射 + 公司记忆 (pg_trgm) + 同行业频率查询 + Note 字段 | 2 sprint |
| **Phase 4** | 持续学习闭环 + 性能优化 + 安全加固 | 1 sprint |

**为什么 Excel 先于 AI Vision？** Excel 提取是确定性的（直接读表格），AI Vision 有不确定性。先做 Excel 可验证整个 Pipeline（映射→审核→写入），再接入 Vision 只是换 Extract 节点的实现。

---

## 16. Multi-Agent 演进路线

### 16.1 三阶段演进

```
Phase 1 (当前)                 Phase 2                      Phase 3
──────────────                ───────────                  ───────────
OCR Agent 独立运行             + Chat Agent                 + Orchestrator
                              + RAG Agent
                                                           
┌──────────┐                  ┌──────────┐                ┌──────────────────┐
│OCR Agent │                  │OCR Agent │                │  Supervisor      │
│          │                  ├──────────┤                │  Agent           │
│ Tool 1-5 │                  │Chat Agent│                │                  │
│ 前端直调  │                  │  调用     │                │  ┌────┐ ┌────┐  │
│          │                  │  OCR Tool │                │  │OCR │ │Chat│  │
└──────────┘                  ├──────────┤                │  └────┘ └────┘  │
                              │RAG Agent │                │  ┌────┐ ┌────┐  │
                              │ LlamaIdx │                │  │RAG │ │... │  │
                              └──────────┘                │  └────┘ └────┘  │
                                                          └──────────────────┘

前端 ──REST──→ OCR Agent     Chat: "解析这个文件"          用户意图 → 路由 → Agent
                               → 调用 OCR Tool              统一入口，统一上下文
```

### 16.2 各阶段复用关系

| 组件 | Phase 1 (OCR) | Phase 2 (+Chat/RAG) | Phase 3 (+Orchestrator) |
|------|--------------|---------------------|------------------------|
| **LangGraph** | OCR Pipeline 状态图 | Chat Agent 状态图 | Supervisor 状态图 |
| **Instructor** | 提取/映射结构化输出 | 对话结构化输出 | 不变 |
| **OpenRouter** | Gemini Flash + Claude | + 对话模型 | 不变 |
| **pgvector** | 不启用（OCR 用 pg_trgm + SQL） | RAG 知识向量（在现有 RDS PostgreSQL 上启用） | 不变 |
| **PostgreSQL** | 业务数据 + checkpoint | + Chat 历史 | + 统一 session |
| **RAG 检索** | 不启用 | 自定义检索 pipeline（用户自写 chunking, embedding, recall, re-ranking） | 不变 |
| **Tool 接口** | 前端 REST 调用 | Agent 间调用 | Orchestrator 调用 |

**核心价值**: 每个 Phase 新增的 Agent 是**增量添加**，已有 Agent 和基础设施**零修改**。

### 16.3 Agent 间通信模式

```
Phase 2 — 直接调用（Agent-to-Agent）:

  Chat Agent 收到: "帮我解析上传的财务文件"
       │
       ▼ 识别意图 → 需要 OCR 能力
       │
       ▼ 调用 OCR Agent 的 upload_and_extract Tool
       │
       ▼ 轮询 get_session_status Tool
       │
       ▼ 返回提取结果给用户

Phase 3 — Supervisor 路由:

  用户输入: "解析这个 PDF 然后对比去年数据"
       │
       ▼ Supervisor 分解为两步
       │
       ├─ Step 1: OCR Agent.upload_and_extract
       │
       └─ Step 2: Analysis Agent.compare_periods
              (输入来自 Step 1 的输出)
```

### 16.4 共享基础设施

所有 Agent 共享但互不干扰的基础设施:

```
┌─────────────────────────────────────────────────────────┐
│                    共享基础设施层                          │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ PostgreSQL  │  │  OpenRouter  │  │    AWS S3     │  │
│  │ (AWS RDS)   │  │              │  │               │  │
│  │ ai_ocr_* 表 │  │ 模型路由     │  │ 文件存储      │  │
│  │ ai_chat_* 表│  │ 统一 API key │  │ 统一 bucket   │  │
│  │ rag_chunks  │  │              │  │               │  │
│  │ pgvector*   │  │              │  │               │  │
│  │ checkpoint  │  │              │  │               │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘

每个 Agent 的数据通过表前缀隔离（ai_ocr_* / ai_chat_* / ai_rag_*）
LangGraph checkpoint 按 thread_id 隔离（每个 Agent session 独立）

* pgvector 在 RAG 阶段启用，运行于现有 AWS RDS PostgreSQL 上（AWS 托管，零额外基础设施）
* RAG 使用自定义检索 pipeline（自写 chunking → embedding → recall → re-ranking），不使用 Bedrock Knowledge Bases
* rag_chunks 表: 存储文档分块 + 向量（pgvector），供 RAG Agent 语义检索
```

---

## 17. 依赖清单

```
# 编排层
langgraph>=0.3.0
langgraph-checkpoint-postgres>=2.0.0

# 结构化输出
instructor>=1.7.0
pydantic>=2.9.0

# 模型访问
openai>=1.50.0              # OpenRouter 兼容 SDK

# 文档处理
unstructured[pdf,xlsx]>=0.16.0
pdf2image>=1.17.0
Pillow>=10.0.0
openpyxl>=3.1.0

# 安全
python-magic>=0.4.27
defusedxml>=0.7.1

# RAG 阶段（Phase 2+ 启用）
# pgvector>=0.3.0                                # 向量搜索（RAG 阶段启用，OCR 阶段不需要）
# openai>=1.50.0                                 # text-embedding-3-small（RAG embedding 用）
# 自定义检索 pipeline: chunking → embedding → recall → re-ranking
```
