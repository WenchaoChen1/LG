# OCR Agent 系统架构

> **关联文档**: [设计理念](./design-philosophy.md) · [需求分析](./requirement-analysis.md) · [Java 端设计](./java-design.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md)

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
| **状态** | AI 处理状态由 LangGraph checkpoint 管理；task 生命周期由 Java 端 `doc_parse_task`/`doc_parse_file` 管理 |
| **记忆** | 独立管理公司映射记忆（PostgreSQL + pg_trgm，无向量数据库） |
| **接口** | 通过 Tool 协议暴露能力，不暴露内部实现 |
| **模型** | 独立决定用哪个 AI 模型（Gemini Flash 提取 / Claude 映射） |
| **数据** | 只读写自己的 `ai_ocr_*` 提取/映射表 + `mapping_memory`，上传元数据由 Java 管理（`doc_parse_*`），写入 LG 通过标准 Writer 接口 |

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

## 4. 整体数据流与职责边界

### 4.1 数据流图

```
用户                    Java (CIOaas-api)              SQS                Python (CIOaas-python)
────                   ─────────────────              ───                ──────────────────────

上传文件 ───────────→  ① 校验文件 (MIME+大小)
                       ② 存入 S3
                       ③ 写入 doc_parse_task 表
                       ④ 发送 SQS 消息 ──────────→  ocr-extract-queue
                       ⑤ 返回 202 {taskId}                              ⑥ 消费消息
                                                                        ⑦ 从 S3 下载文件
                                                                        ⑧ AI 提取 + 映射
                                                                        ⑨ 结果写入 ai_ocr_* 表
前端轮询状态 ────────→  ⑩ 查询 task 状态         ←── ocr-result-queue ←─ ⑪ 发送完成消息
                       ⑫ 更新 task 状态
                       ⑬ 返回提取结果
                       
用户审核编辑 ────────→  ⑭ 保存编辑内容

用户点击 Verify ─────→  ⑭a 计算 Verify Data Summary（源文件数/映射类型数/映射账户数）
                       ⑭b 与 fi_* 对比检测冲突
                       ⑭c 返回冲突列表给前端

用户逐个解决冲突 ────→  ⑭d 选择 Overwrite 或 Skip（Cancel 已移除）
                       ⑭e 可选填写 note，否则系统自动生成默认 note
                       ⑭f 保存到 doc_parse_conflict_note（支持 thread）

用户确认提交 ────────→  ⑮ 写入 fi_* 财务表（整体事务，部分失败全部 rollback）
                       ⑯ 触发下游 Normalization
                       ⑯a 新闭月邮件通知（若有新 period）
                       ⑯b 源文件记录到 Company Documents（无论是否提取到账户）
                       ⑰ 发送记忆学习消息 ────→  ocr-memory-learn-queue
                                                                        ⑱ 消费消息
                                                                        ⑲ 对比原始映射 vs 最终确认
                                                                        ⑳ 只存差异到 mapping_memory
```

**核心原则**: Java 管生命周期（上传、状态、确认），Python 管 AI 处理（提取、映射、记忆）。通过 SQS 解耦，互不直接调用。
**记忆学习**: 在 Java 成功写入 fi_* 后触发（不是审核时），Python 对比 AI 原始建议 vs 用户最终确认，只有被用户修正过的映射才存入记忆。

> **关于 OOE 净值计算的归属**：
> OCR Agent 不计算 OOE = expense - income 的净值。Python 端只把行项分别映射为 `other_income` 或 `other_expense` 原始字段，写入 `ai_ocr_mapping_result`。Java 端 `commit_to_lg` 写入 `fi_*` 表时也按原始字段写入。OOE 净值计算由下游标准化（Normalization）引擎在读取时计算（live computed metric），不在 OCR Agent 范围内。

### 4.2 职责边界表

| 职责 | Java (CIOaas-api) | Python (CIOaas-python) |
|------|-------------------|----------------------|
| 文件上传 + S3 存储 | **Owner** | — |
| 文件校验 (MIME/大小/恶意文件) | **Owner**（上传时，S3 写入前） | — |
| Task 生命周期管理 | **Owner**（创建、状态跟踪） | 通过 SQS 回调更新状态 |
| SQS 消息生产 (extract) | **Owner** | — |
| SQS 消息消费 (extract) | — | **Owner** (aioboto3) |
| S3 文件下载用于处理 | — | **Owner**（按 s3Key 只读） |
| AI 提取 + 映射 | — | **Owner** |
| 提取结果存储 (ai_ocr_* 表) | 只读 | **Owner** |
| SQS 结果回调 (result) | **消费**（更新 task 状态） | **生产** |
| 用户审核数据服务 | **Owner**（读取 + 返回前端） | — |
| 最终确认写入 fi_* 表 | **Owner** | — |
| 认证 + 授权 | **Owner** | —（信任 SQS 消息来源） |
| 映射记忆管理 | — | **Owner** |

> Java 端模块详细设计见 [java-design.md](./java-design.md)。Python 端 AI 处理详细设计见 [python-design.md](./python-design.md)。

### 4.3 总体架构图

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

> 前端页面详细设计见 [frontend-design.md](./frontend-design.md)。

### 4.4 Pipeline 状态机

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

**LangGraph 节点职责**:

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

> Python 端 Pipeline 各节点实现详见 [python-design.md](./python-design.md)。

---

## 5. SQS 消息设计

### 5.1 队列拓扑

```
Java (Producer)                                Python (Consumer)
──────────────                                 ──────────────────

  ① OcrSqsProducer ──→ ocr-extract-queue ──→ SQS Consumer (aioboto3)
                                                      │ AI 提取+映射
  ② OcrResultProcessor ←── ocr-result-queue ←─────────┘ 返回结果
  
  ③ MemoryLearnProducer ──→ ocr-memory-learn-queue ──→ Memory Consumer
     (fi_* 写入成功后触发)                                │ 对比映射差异
                                                         │ 存入 mapping_memory
  
  共享: dlq-queue（三个队列都 redrive 到这里）
```

**三条队列分工**:
- `ocr-extract-queue`: 触发 AI 提取（上传后）
- `ocr-result-queue`: 返回提取结果（处理完成后）
- `ocr-memory-learn-queue`: 触发记忆学习（fi_* 写入成功后）

**一条消息对应一个文件**（不是一个 session）。原因：独立重试、天然并发、部分失败隔离。

### 5.2 消息 Schema

**Java → Python (ocr-extract-queue)**

```json
{
  "messageType": "OcrExtract",
  "queueName": "ocr-extract-queue",
  "batchId": "uuid",
  "sendTime": "2026-04-16T10:00:00Z",
  "uuid": "msg-uuid",
  "sessionId": "session-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "s3Bucket": "lg-prod-files",
  "s3Key": "ocr-uploads/123/session-uuid/file-uuid/2024_PnL.pdf",
  "filename": "2024_PnL.pdf",
  "contentType": "application/pdf",
  "fileSize": 2048576,
  "uploadedBy": "user-uuid",
  "callbackMeta": {
    "totalFiles": 3,
    "fileIndex": 1
  }
}
```

**Python → Java (ocr-result-queue)**

```json
{
  "messageType": "OcrResult",
  "queueName": "ocr-result-queue",
  "batchId": "uuid",
  "sendTime": "2026-04-16T10:00:15Z",
  "uuid": "msg-uuid",
  "sessionId": "session-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "status": "completed",
  "extractedTableCount": 2,
  "totalRows": 47,
  "processingTimeMs": 12340,
  "error": null
}
```

**Java → Python (ocr-memory-learn-queue)** — fi_* 写入成功后触发

```json
{
  "messageType": "OcrMemoryLearn",
  "queueName": "ocr-memory-learn-queue",
  "uuid": "msg-uuid",
  "sendTime": "2026-04-16T10:05:00Z",
  "taskId": "task-uuid",
  "fileId": "file-uuid",
  "companyId": "123",
  "mappingComparisons": [
    {
      "accountLabel": "AWS Infrastructure",
      "originalAiCategory": "R&D Expenses",
      "confirmedCategory": "COGS",
      "wasOverridden": true
    },
    {
      "accountLabel": "Total Revenue",
      "originalAiCategory": "Revenue",
      "confirmedCategory": "Revenue",
      "wasOverridden": false
    }
  ]
}
```

**Python 记忆学习逻辑**:
- 只处理 `wasOverridden: true` 的条目
- `wasOverridden: false` 的忽略（AI 猜对了，不需要存记忆）
- 对比 `originalAiCategory` vs `confirmedCategory`，将修正存入 `mapping_memory`
- 如果已有同公司同标签的记忆，更新 `confirm_count` + `normalized_category`

### 5.3 队列配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `visibilityTimeout` | 300s (5 分钟) | 50 页 PDF 处理需要 ~60s，留足余量 |
| `maxReceiveCount` | 3 | 3 次重试后进 DLQ |
| `messageRetentionPeriod` | 345600s (4 天) | 与现有队列一致 |
| DLQ | 共享 `dlq-queue` | 通过 `messageType=OcrExtract` 区分 |

### 5.4 错误处理

| 场景 | 处理方式 |
|------|----------|
| Python 处理中崩溃 | 消息不可见超时后重新出现，SQS 自然重试 |
| AI 模型超时 | Python 捕获异常，发送 `status=failed` 结果消息 |
| 瞬态故障（S3 读取、网络） | SQS 重试（最多 3 次，指数退避） |
| 所有重试耗尽 | 进 DLQ，Java 通过 `QueueMessageLog.isDlq=true` 追踪 |
| 结果消息发送失败 | Python 通过 SQS 回调通知 Java 更新状态；Java 轮询时 fallback 查 Python 表 |
| 上传文件重名（同 company_id + 同 file_hash） | Java 在 `DocParseServiceImpl.upload()` 中拒绝，返回 HTTP 409 + 错误码 `DUPLICATE_NAME`，不发 SQS 消息 |

> Java 端 SQS 生产/消费实现详见 [java-design.md](./java-design.md)。Python 端 SQS 消费/生产实现详见 [python-design.md](./python-design.md)。

---

## 6. API 设计

### 6.1 接口列表

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

### 6.2 Gateway 路由

在 CIOaas-api Gateway 添加路由:

```
/api/v1/ocr/** → http://cioaas-python:8090 (StripPrefix=0)
```

> Java 端 API 端点实现详见 [java-design.md](./java-design.md)。Python 端 API 端点实现详见 [python-design.md](./python-design.md)。前端 API 调用与状态管理详见 [frontend-design.md](./frontend-design.md)。

---

## 7. 数据模型与表归属

### 7.1 表归属总览

**Java 拥有的表（CIOaas-api `docparse` 包管理）**:

| 表 | 用途 |
|----|------|
| `doc_parse_task` | Task 生命周期：company_id, uploaded_by, session_id, status, total_files, completed_files |
| `doc_parse_file` | 上传文件记录：task_id, filename, file_type, file_size, s3_bucket, s3_key, status |
| `file_objects` (现有) | S3 文件记录，复用 storage 模块 |
| `fi_*` (现有) | 最终确认的财务数据 |

**Python 拥有的表（CIOaas-python 管理）**:

| 表 | 用途 |
|----|------|
| `ai_ocr_extracted_table` | 提取的表格结构 |
| `ai_ocr_extracted_row` | 提取的行数据 |
| `ai_ocr_mapping_result` | AI 映射结果 |
| `ai_ocr_conflict_record` | 冲突检测结果 |
| `mapping_memory` | 两层映射记忆（通用+公司） |
| `mapping_memory_audit` | 记忆变更审计日志 |

> **RAG 阶段**: 将新增 `rag_chunks` 表用于向量存储（pgvector），支持知识库检索和语义匹配。OCR 阶段不需要向量表。

### 7.2 数据库隔离

| 角色 | 权限 |
|------|------|
| `java_app` | 完全访问 Java 拥有的表 + `SELECT` 权限访问 Python 表 |
| `python_worker` | 完全访问 Python 拥有的表 + `SELECT` 权限访问 `doc_parse_task`、`doc_parse_file`（查状态） + 零权限访问 `fi_*` 表 |

### 7.3 详细 DDL

完整 DDL、索引设计和关键索引见 [code-examples.md](./code-examples.md)。

**关键索引**:

| 索引 | 类型 | 用途 |
|------|------|------|
| `idx_mapping_memory_term_trgm` | GIN (pg_trgm) | 映射记忆模糊匹配 |
| `idx_mapping_memory_industry` | B-tree (company.industry) | 同行业频率查询 |
| `idx_financial_data_conflict` | B-tree 复合索引 | 冲突检测快速查询 |

> **RAG 阶段**: 将新增 `idx_rag_chunks_hnsw` (HNSW, pgvector) 用于向量近似搜索。

> Java 端表 Entity/Repository 设计详见 [java-design.md](./java-design.md)。Python 端表 SQLAlchemy Model 设计详见 [python-design.md](./python-design.md)。

---

## 8. 安全设计

### 8.1 现有代码中发现的安全问题（必须修复）

| 问题 | 严重级别 | 位置 | 修复方案 |
|------|---------|------|----------|
| 上传端点 `@AnonymousAccess` 无认证 | **CRITICAL** | `FileController.java` | 移除 `@AnonymousAccess`，加 JWT 认证 |
| 无 MIME 类型校验就写入 S3 | HIGH | `FileServiceImpl.java` | 上传时校验扩展名 + magic bytes |
| SQS 消息无签名 | HIGH | `SqsMessage.java` | 加 HMAC-SHA256 签名字段 |
| 静态 IAM 密钥而非实例角色 | HIGH | `S3AutoConfiguration.java` | 改为 EC2/ECS 实例角色 |
| 跨服务 DB 无角色隔离 | HIGH | 数据库配置 | 分 `java_app` / `python_worker` 角色 |
| SQS 消息中 companyId 未做归属校验 | HIGH | `SQSMessageListener.java` | 消费前校验 file → company 归属 |
| Python `file_url` 接受任意 URL (SSRF) | MEDIUM | `routes.py` | 限制为 S3 域名白名单 |
| 财务数据发送到外部 LLM | MEDIUM | `langchain_service.py` | 确认 OpenRouter DPA + 脱敏公司标识 |

### 8.2 S3 权限划分

```
Java IAM Role:
  s3:PutObject  → ocr-uploads/*    (写)
  s3:GetObject  → ocr-uploads/*    (读)
  sqs:SendMessage → ocr-extract-queue

Python IAM Role:
  s3:GetObject  → ocr-uploads/*    (只读)
  sqs:ReceiveMessage → ocr-extract-queue
  sqs:DeleteMessage  → ocr-extract-queue
  sqs:SendMessage    → ocr-result-queue
```

S3 key 按公司隔离：`ocr-uploads/{companyId}/{sessionId}/{fileId}/filename`

### 8.3 各层安全措施

| 层面 | 措施 |
|------|------|
| **文件安全** | `python-magic` 校验真实 MIME（不信任扩展名），Excel 用 `defusedxml` 防 XXE |
| **LLM 注入防御** | 用户文件名/行标签传入 LLM 前 sanitize（过滤 "ignore previous" 等） |
| **S3 存储** | Pre-signed URL (15 分钟有效)，SSE-S3 加密，bucket 禁止公开 |
| **权限** | Gateway JWT 校验 + Python 端二次校验 company_id 归属 |
| **数据驻留** | OpenRouter 数据政策: 不用于训练，但文件经过第三方需用户知情同意 |
| **审计** | MappingResult 保留 original_ai_suggestion + source，全流程时间戳 |

> Java 端安全实现（JWT、MIME 校验）详见 [java-design.md](./java-design.md)。Python 端安全实现（文件校验、LLM 注入防御）详见 [python-design.md](./python-design.md)。

### 8.4 文件留存策略

| 阶段 | 留存位置 | 时长 | 说明 |
|------|---------|------|------|
| 上传后 ~ 提交前 | S3 (Standard) | 直到 task 状态 = COMPLETED | 用户审核期间需快速访问 |
| 提交后 ~ 90 天 | S3 (Standard) | 90 天 | 备查、撤销等场景 |
| 90 天 ~ 180 天 | S3 (Glacier) | 90 天 | 归档存储，访问需 3-5 小时 |
| 180 天后 | 删除 | — | 法规合规，可通过配置延长 |

**配置参数**（在 `DocParseProperties` 中）：
- `retention.standard.days` = 90
- `retention.glacier.days` = 90
- `retention.delete.after.days` = 180

**例外**：被冲突解决标记为 `OVERWRITE` 的旧版本数据，关联的源文件保留时间延长至 365 天（用于审计追溯）。

### 8.5 跨公司数据访问控制（Row-Level Security）

**所有 task/file/mapping 相关的 API 必须在 service 层强制做归属校验，而不是仅依赖 controller 层的 JWT。**

#### 8.5.1 必须做归属校验的端点

| 端点 | 校验规则 |
|------|---------|
| `GET /docparse/tasks?status=in_progress` | `WHERE uploaded_by = :currentUser AND company_id = :currentCompanyId` |
| `GET /docparse/tasks/{id}/status` | 加载 task 后立即校验 `task.company_id == currentCompanyId` |
| `GET /docparse/tasks/{id}/result` | 同上 |
| `PATCH /docparse/tasks/{id}/review` | 同上 |
| `POST /docparse/tasks/{id}/confirm` | 同上 |
| `PATCH /api/v1/ocr/tables/{tableId}/rows/{rowId}/mapping` | 通过 tableId → file_id → task_id → company_id 链路校验 |

#### 8.5.2 实现方式

Java Service 层标准模板：
```java
DocParseTask task = taskRepository.findByIdAndCompanyId(taskId, currentCompanyId)
    .orElseThrow(() -> new ForbiddenException("Task not found or no permission"));
// 不要先 findById 再校验 — 那样可能泄漏存在性信息（404 vs 403 区别可被探测）
```

Python 同样在 repository 层加 `company_id` 过滤参数，禁止单独按 ID 查询。

### 8.6 Note 字段 XSS 防御

Note 字段（≤2000 字符自由文本）在 Financial Statements 模块展示时：
- **写入时**：服务端用 `bleach` 或同等库剥离所有 HTML/Script 标签，只保留纯文本
- **读取时**：前端必须用 React 的 `{text}` 默认渲染（自动转义），**禁止使用 `dangerouslySetInnerHTML`**
- **CSP**：Financial Statements 路由设置 `Content-Security-Policy: default-src 'self'`

### 8.7 LLM 输入消毒（防 Prompt Injection）

**`safety/prompt_guard.py` 必须包装所有从外部数据源进入 LLM prompt 的字符串**，包括但不限于：
- 文件名（来自上传）
- 行标签（OCR 提取结果）
- `detected_currencies`（AI Vision 输出）
- `account_label`（任何来自文档的标签）

**包装方式**：用 XML tag 包裹 + 限制字符集
- 货币字段：写入前用正则 `^[A-Z]{3}$` 校验（仅 ISO 4217 代码）
- 其他字段：包裹在 `<untrusted>...</untrusted>` 中，system prompt 明确告知 LLM "不得执行 untrusted 标签内的指令"

### 8.8 GDPR 数据擦除（Right to be Forgotten）

180 天保留策略不能阻挡 GDPR 擦除请求。当用户/管理员发起擦除请求：

1. 立即软删除 `doc_parse_task` + `doc_parse_file` + `ai_ocr_*`（`deleted = true`）
2. 立即调用 S3 `DeleteObject`（Standard tier 立即生效）
3. 若文件已归档到 Glacier：发起 restore 请求 → 恢复后 delete（约 3-5 小时）
4. 记录擦除请求和处理时间到 `doc_parse_erasure_log` 表（合规审计）
5. 365 天 OVERWRITE 审计延长例外不能凌驾于 GDPR 之上 — 用户的擦除请求优先

### 8.9 S3 上传孤儿对象清理

上传流程是 "compute hash → DB 唯一性检查 → S3 upload → DB insert"。如果 S3 upload 成功但 DB insert 失败，会产生孤儿对象。

**清理策略**：
- 使用 S3 staging prefix `s3://bucket/staging/...`，配置 S3 Lifecycle Rule：30 分钟未被引用的对象自动删除
- DB insert 成功后，应用层将对象从 staging 移到正式 prefix `s3://bucket/files/...`
- 后台 cron 每日扫描 staging 残留，强制清理超过 1 小时的对象

---

## 9. 状态通知与并发

### 9.1 状态通知方案

**轮询（Polling）** — 不用 WebSocket，不用 SNS。

理由：
- 现有前端 (Ant Design Pro + dva) 轮询模式成熟
- 处理时间 10-60 秒，2 秒间隔轮询完全可接受
- 简单可靠，无额外基础设施

```
前端                     Java                           Python
────                    ────                           ──────
POST /docparse/upload
                        → S3 + task(PENDING) + SQS
                        ← 202 {taskId}

GET /docparse/tasks/{id}/status  (每 2 秒)
                        → 查 doc_parse_task 表
                        ← {status: "processing", progress: 30%}

                        ← (SQS result 到达)
                        → 更新 task 状态 = completed

GET /docparse/tasks/{id}/status
                        ← {status: "completed"}

GET /docparse/tasks/{id}/result
                        → 查 ai_ocr_* 表
                        ← {tables: [...], mappings: [...]}
```

> 前端轮询实现（dva effect、超时保护、清理机制）详见 [frontend-design.md](./frontend-design.md)。

### 9.2 并发与扩展

| 场景 | 方案 |
|------|------|
| 100 文件同时上传 | 每文件一条 SQS 消息，SQS 自然处理背压 |
| Python 并发控制 | `asyncio.Semaphore(5)` — 每实例最多 5 个并发提取 |
| SQS 可见性超时 | 300s (5 分钟)，长时任务用心跳延长 |
| 横向扩展 | 加 Python 实例即可，SQS 自动分配消息 |
| 批量上传 UX | 前端按文件追踪状态，session 下所有文件 completed/failed 后聚合 |

---

## 10. 边界情况

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

## 11. 性能优化

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

> 前端性能优化（虚拟滚动、EditableCell、React.memo）详见 [frontend-design.md](./frontend-design.md)。Python 端性能优化（并发提取、模型路由）详见 [python-design.md](./python-design.md)。

---

## 12. 待确认问题

| # | 问题 | 阻塞级别 |
|---|------|----------|
| 1 | ~~OOE 作为计算指标 vs 映射目标~~ **已解决**: 映射阶段分别归类为 Other Income / Other Expense，互抵在 normalization engine 执行 | ~~P0~~ Done |
| 2 | hosting/cloud/server 默认归类？公司 industry 从哪获取？ | P1 |
| 3 | 多类型混合 PDF 用户分别上传还是系统切分？ | P1 |
| 4 | OpenRouter 数据安全政策是否满足合规？ | P1 |
| 5 | 已上传文件的删除/覆盖权限？ | P2 |
| 6 | Mobile 审核页面改为 Desktop Only？ | P2 |

---

## 13. 开发分期

| 阶段 | 范围 | 估算 |
|------|------|------|
| **Phase 1 (MVP)** | Upload + Excel 提取 (Instructor) + 规则引擎映射 + 简单审核 + 写入 LG | 3 sprint |
| **Phase 2** | AI Vision 提取 (Gemini Flash) + 并排审核 + 内联编辑 + 冲突检测 | 2 sprint |
| **Phase 3** | LLM 映射 + 公司记忆 (pg_trgm) + 同行业频率查询 + Note 字段 | 2 sprint |
| **Phase 4** | 持续学习闭环 + 性能优化 + 安全加固 | 1 sprint |

**为什么 Excel 先于 AI Vision？** Excel 提取是确定性的（直接读表格），AI Vision 有不确定性。先做 Excel 可验证整个 Pipeline（映射→审核→写入），再接入 Vision 只是换 Extract 节点的实现。

**各端分期细节**:

| Phase | Java 工作 | Python 工作 | 前端工作 |
|-------|-----------|-------------|----------|
| **1 (MVP)** | docparse 模块 + 上传 + SQS 生产 + 状态 API | SQS 消费 + Excel 直接解析 + 规则引擎映射 | 上传页 + 状态轮询 |
| **2** | 确认写入 fi_* + 冲突检测 API | AI Vision 提取 (PDF/图片) + LLM 映射 | 并排审核页 + 内联编辑 |
| **3** | 审核编辑 PATCH API | 记忆系统 + Few-Shot 注入 + 冲突解决 | 冲突解决页 + Note 字段 |
| **4** | 安全加固 (认证/IAM/DB 隔离) | 大文件优化 + 质量检测 + 性能调优 | Mobile 上传适配 |

> 各端分期实现详见 [java-design.md](./java-design.md)、[python-design.md](./python-design.md)、[frontend-design.md](./frontend-design.md)。

---

## 14. Multi-Agent 演进路线

### 14.1 三阶段演进

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

### 14.2 各阶段复用关系

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

### 14.3 Agent 间通信模式

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

### 14.4 共享基础设施

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

## 15. 依赖清单

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
