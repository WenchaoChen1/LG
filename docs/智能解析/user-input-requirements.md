# OCR 智能解析 — 用户输入需求清单

> **本文档定位**: 完整记录用户在多轮对话中口头/文字输入的需求与约束，作为技术方案设计的**唯一权威输入源**。技术方案（system-architecture / java-design / python-design / frontend-design / database-schema / code-examples）必须可追溯到本文档某一条要求。
>
> **维护规则**: 用户每次新增/修改要求时，本文档必须更新；技术文档随后调整。**禁止技术文档先行**。
>
> **当前版本**: 2026-05-06
> **关联文档**: [需求分析](./调研/requirement-analysis.md)（Asana 业务需求）·  [系统架构](./调研/system-architecture.md)（技术契约）

---

## 0. 文档范围说明

本文档**只记录用户的直接输入**，不包含：
- Asana EPIC 的业务需求（已在 [requirement-analysis.md](./调研/requirement-analysis.md) 中维护）
- 团队成员（Tingting/PM）维护的需求文档（独立的 `Manual_Uploads_with_OCR_需求文档.md`）
- 我（架构师）自己推导的设计决策

**两类输入区分:**
- 🟢 **业务需求补充**: 对 Asana EPIC 的额外业务约束（如"4 步流程"）
- 🔵 **技术约束**: 对实现方式的明确要求（如"Python 跨域写权限例外清单"）

---

## 1. 表设计要求（2026-04-某日，更早会话）

> 输入原文: "1.表名前缀为ai_ocr_** 2.需要有每个表名的描述 3.在文件开始要有一个简介 关于和这个表设计的 几个表 每个表分别是做什么的"

🔵 **R-1.1 表前缀统一**: 所有 OCR Agent 拥有的表必须以 `ai_ocr_` 为前缀，包括之前命名为 `doc_parse_*`（Java 拥有）和 `mapping_memory*`（Python 拥有）的表。

🔵 **R-1.2 每张表必须有独立的"用途"描述段**: 不接受仅靠 DDL 注释。`### N.M ai_ocr_xxx` 标题下必须有一段独立段落说明"做什么"。

🔵 **R-1.3 文件开头必须有 Schema Overview**: 列出所有表 + 每张表的用途简介，便于读者快速建立全局认知。

**对应技术输出位置**: [database-schema.md "表清单总览"](./调研/database-schema.md) + 每张表的 `**用途**:` 段落

---

## 2. Java/Python 边界要求（2026-05-06）

> 输入原文:
> "文件上传 和校验报错都走java 其他的走python
> java调用python使用队列
>   1.进行文件解析任务的处理
>   2.进行最后保存的记忆处理
> 记忆处理需要有日志"

🔵 **R-2.1 文件上传归属 Java**: 文件接收、S3 写入由 Java 执行。

🔵 **R-2.2 校验报错归属 Java**: 文件类型/大小/格式/重名等校验失败 + 任何用户可见的错误信息**必须由 Java 生成或转换**。Python 不直接面向用户。

🔵 **R-2.3 其他业务逻辑归属 Python**: AI 文件解析、AI 映射、相似度检测、记忆学习等"AI 智能"逻辑都由 Python 执行。

🔵 **R-2.4 Java→Python 仅通过队列**: 严禁 HTTP 同步/异步调用。Python 不暴露 HTTP 端点给 Java。

🔵 **R-2.5 两个核心 SQS 触发场景**:
- **场景 A**: Java 触发 Python 进行**文件解析任务**
- **场景 B**: Java 触发 Python 进行**最后保存的记忆处理**（commit 后）

🔵 **R-2.6 记忆处理必须有日志**: 这是一个独立的强制约束（说明用户高度关心记忆变更的可追溯性）。

**对应技术输出位置**: [system-architecture.md §0 职责边界声明](./调研/system-architecture.md#0-职责边界声明顶层规则)

---

## 3. 4 步流程定义（2026-05-06）

> 输入原文:
> "我们项目流程分
> 1.文件上传  java
> 2.文件上传完成使用sqs触发python进行解析返回结构数据 返回前端 同时存入数据库
> 3.数据校验 java  校验前后数据要留存记录log
> 4.数据保存 java 完成后sqs  到python 进行记忆的保存更新工作
> 这个流程所有的状态记录log"

🟢 **R-3.1 流程必须以 4 步抽象呈现**: 这是用户对产品的理解粒度。系统架构文档的最高抽象必须是 4 步，更细的子步骤（如 5a/5b/5c）作为详细设计层。

🟢 **R-3.2 4 步流程的具体职责**:

| # | 步骤 | 主体 | 关键动作 |
|---|------|------|---------|
| 1 | **文件上传** | Java | 接收 + 校验 + S3 |
| 2 | **文件解析** | Java SQS → Python → Java DB | Java 入队 → Python 解析 → 返回结构数据 → 写入 DB → 前端可见 |
| 3 | **数据校验** | Java | 用户在前端做的所有审核/编辑/汇总查看/冲突解决 |
| 4 | **数据保存** | Java commit + Java SQS → Python 记忆 | Java 写 fi_* → 完成后通知 Python 学习记忆 |

🔵 **R-3.3 校验前后数据要留 log**:（针对第 3 步 "数据校验"）
- "校验前数据" = AI 原始提取数据 + AI 原始映射建议
- "校验后数据" = 用户最终确认数据
- 两者都必须**持久化为 log 记录**，不能只保留当前状态

🔵 **R-3.4 整个流程所有状态记录 log**: 4 步流程中的**每一次状态变更**都必须有日志，不能依赖单一字段（如 task.status 当前值）。需要有完整的状态变更历史。

**对应技术输出位置**:
- [system-architecture.md §0.0 项目核心流程（4 步抽象）](./调研/system-architecture.md#00-项目核心流程4-步抽象)
- [system-architecture.md §0.6 全流程状态必须留 log](./调研/system-architecture.md#06-关键规则全流程状态必须留-log)
- [database-schema.md §2.9 ai_ocr_task_state_log](./调研/database-schema.md#29-ai_ocr_task_state_log2026-05-06-新增)

---

## 4. 当前迭代要求（2026-05-06，本次对话）

> 输入原文: "teams agent 头脑风暴理解需求  理解我的要求  我的要求（输入的问题）单独列一个文档  然后在优化技术方案  删除没有意义的变更  java pytohn要提现每个接口或者sqs消费时做什么的"

🔵 **R-4.1 用户输入需求独立成文**: 即本文档。技术方案不能与用户输入混在一起。

🔵 **R-4.2 多 agent 团队头脑风暴**: 在执行技术修改前，先用多视角 agent 团队讨论"我到底要的是什么"，避免我（架构师）误解用户意图。

🔵 **R-4.3 优化技术方案**: 基于头脑风暴的真实理解，重新审视已有的技术文档，做必要的优化。

🔵 **R-4.4 删除无意义变更**: 之前迭代中可能产生了一些与用户真实需求脱节的"过度设计"或"重复设计"，需要识别并删除。可疑候选：
- 与 4 步流程模型冗余的细分（如某些状态、某些表、某些 API 路径）
- 多个文档同一概念的重复表述（应在单一权威位置定义，他处引用）
- 没有对应到任何用户输入或 Asana 业务需求的设计决策

🔵 **R-4.5 Java/Python 每个接口/消费者必须显式列出"做什么"**:
- **java-design.md**: 每个 REST 端点（含 Controller 方法名、URL、HTTP method、请求/响应 DTO、做什么的一句话说明）
- **java-design.md**: 每个 SQS 生产者（生产到哪个队列、什么时机、消息内容、做什么）
- **python-design.md**: 每个 SQS 消费者（消费哪个队列、消费后做什么、写哪些表、上报什么消息回 Java）
- 形式：表格化（不接受散文式描述）

---

## 5. 可追溯性矩阵

| 需求条目 | 类型 | 当前状态 | 技术文档落地位置 |
|---------|------|---------|----------------|
| R-1.1 表前缀统一 | 🔵 | ✅ 已实现 | `database-schema.md` 全文重命名 |
| R-1.2 每表用途段 | 🔵 | ✅ 已实现 | `database-schema.md` 各 §2.x §3.x |
| R-1.3 Schema Overview | 🔵 | ✅ 已实现 | `database-schema.md` 顶部 |
| R-2.1 上传归属 Java | 🔵 | ✅ 已实现 | `system-architecture.md` §0.1 |
| R-2.2 校验报错 Java | 🔵 | ✅ 已实现 | `system-architecture.md` §0.3 |
| R-2.3 其他归 Python | 🔵 | ⚠️ **范围已收敛**：限定为 AI 智能逻辑（OCR/AI 映射/相似度/记忆学习），冲突检测/Mapping Summary/fi_* 写入归 Java（多 agent 共识，详见 §6 Q-1） | `system-architecture.md` §0.1 |
| R-2.4 仅 SQS 通信 | 🔵 | ✅ 已实现 | `system-architecture.md` §0.2 |
| R-2.5 两个 SQS 场景 | 🔵 | ✅ 已收敛为 2 个核心场景（`ocr-extract-queue` 用 `mode` 字段区分 FULL_EXTRACT/REMAP_ONLY；`ocr-memory-learn-queue` 独立）+ 1 个辅助队列（`ocr-similarity-check-queue`，不在用户原始 2 场景内但已明确标注） | `system-architecture.md` §0.2 |
| R-2.6 记忆处理日志 | 🔵 | ✅ 已实现（双层：决策日志 + 变更明细 + 进度回传） | `system-architecture.md` §0.4 |
| R-3.1 4 步流程抽象 | 🟢 | ✅ 已实现 | `system-architecture.md` §0.0 |
| R-3.2 各步职责 | 🟢 | ✅ 已实现 | `system-architecture.md` §0.0 表格 |
| R-3.3 校验前后留 log | 🔵 | ⚠️ **设计已优化**：不冗余存 snapshot JSONB，改为通过 `mapping_snapshot_hash` 关联到原表（`ai_ocr_extracted_row` + `ai_ocr_mapping_result.original_ai_suggestion`）按需还原（多 agent 共识，详见 §6 Q-4） | `system-architecture.md` §0.6 + `database-schema.md` §2.9 |
| R-3.4 全流程状态 log | 🔵 | ✅ 已实现 | `database-schema.md` §2.9 ai_ocr_task_state_log |
| R-4.1 用户输入独立成文 | 🔵 | ✅ 当前文档 | 本文档 |
| R-4.2 多 agent 头脑风暴 | 🔵 | ✅ 4 视角已完成（PM / Java / Python / 简化评审）| 详见 §6 共识矩阵 |
| R-4.3 优化技术方案 | 🔵 | ✅ 已执行（system-architecture / database-schema 已落地清理） | 详见 §6 共识矩阵 |
| R-4.4 删除无意义变更 | 🔵 | ✅ 已执行：删 `ocr-remap-queue` / 删 `snapshot_data` / 删 `ai_ocr_extraction_skip_log` / 删 `ai_ocr_notification` | `system-architecture.md` v1.5 + `database-schema.md` §6 |
| R-4.5 接口/消费者显式 | 🔵 | 🟡 进行中（派 agent 更新 java-design.md + python-design.md） | `java-design.md` + `python-design.md` |

---

## 6. 待澄清/可能误解的点

以下是我（架构师）在执行过程中可能误解用户意图的点，需要头脑风暴 agent 团队复查：

### Q-1: "其他的走 Python" 范围

用户说"其他的走 Python"，我理解为"AI 智能"逻辑（OCR 提取、AI 映射、相似度、记忆学习）。但当前系统中 Java 还做了：
- Mapping Summary 计算（5a）
- 冲突检测（5b）
- 写入 fi_*（5c）

这些是否符合用户预期？还是用户希望连冲突检测都丢给 Python？

**当前判断**：
- 冲突检测 = SQL 查询比对，**不是 AI**，归 Java 合理
- Mapping Summary = 数据聚合，**不是 AI**，归 Java 合理
- 写入 fi_* = 财务数据写入，**事务边界，必须 Java**

### Q-2: 第 3 个 SQS 出口队列 `ocr-remap-queue` 是否合理？

用户只说了 2 个场景（解析 + 记忆），但当前架构有 3 个出口队列：
- `ocr-extract-queue`（场景 A）
- `ocr-memory-learn-queue`（场景 B）
- `ocr-remap-queue`（**多出来的**，用于"步骤导航变更后重新映射"）

**疑点**: `ocr-remap-queue` 是否可以合并到 `ocr-extract-queue`（用消息字段区分"全量提取"还是"仅重映射"）？或者是否真的需要这个能力？

如果用户实际想要的是"用户改了之后从 Step 2 重新跑"，那 remap-queue 是合理的；如果用户想要"改了之后只是重新做冲突检测"，那 remap-queue 不需要存在。

### Q-3: state_log 是否过度设计？

R-3.4 说"所有状态记录 log"。我加了 `ai_ocr_task_state_log` 总日志表 + 25+ event_type 枚举。但已存在的 `ai_ocr_notification`、`ai_ocr_commit_audit`、`ai_ocr_memory_learn_log`、`ai_ocr_mapping_change_log`、`ai_ocr_extraction_skip_log` 已分别覆盖部分日志需求。

**疑点**: 是用户真的需要一张"总日志表"，还是多个分专项日志表已够？

### Q-4: snapshot_data JSONB 字段是否过度设计？

R-3.3 要求"校验前后数据要留 log"。我用 `ai_ocr_task_state_log.snapshot_data` JSONB 存这些快照。但：
- 校验前的数据已经在 `ai_ocr_extracted_*` + `ai_ocr_mapping_result.original_ai_suggestion` 中
- 校验后的数据是 `ai_ocr_extracted_*` 当前值 + `ai_ocr_mapping_result.lg_category`

**疑点**: 是否只需要在 state_log 里记录"事件发生 + 时间 + 触发者"，而把 before/after 数据放在原始表 + `original_*` 字段中即可？避免双倍存储 + 同步麻烦。

---

## 7. 变更历史

| 日期 | 变更 |
|------|------|
| 2026-05-06 | 初版：整理 4 轮用户输入（表设计要求 / 边界要求 / 4 步流程 / 头脑风暴指令）+ 可追溯性矩阵 + 4 个待澄清点 |
