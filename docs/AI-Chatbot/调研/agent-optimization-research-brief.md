# AI Chatbot Agent 优化调研任务书

> 关联文档: [设计文档](../设计/design-doc.md) · [ReAct 编排设计](../设计/react-orchestrator-design.md) · [开发设计](../开发设计/dev-design-doc.md)
> 代码侧参考（CIOaas-python 仓库）: `docs/AI-Chatbot/实现与业务流转.md` · `source/ai/CLAUDE.md` · `source/chatbot/CLAUDE.md`

> 创建日期: 2026-09-16 · 状态: 待执行 deep search
> 本文件是**调研任务书**（deep search 的输入），不是调研结论。结论产出后另存为 `agent-optimization-findings.md`。

---

## 0. 一句话目标

在不牺牲回答可信度的前提下，为现有 LangGraph `create_agent` 聊天智能体找出**可落地**的优化点，量化预期收益与实施成本。

**四个维度的优先级（已拍板）**：

```
回答准确率  >  首 token 延迟 / 端到端时延  >  单轮成本  >  并发与稳定性
```

---

## 0.5 研究方法与证据标准（强制）

本调研**必须先做外部检索再下结论**，不得只凭模型内部知识作答——执行者的知识截止早于本文创建日期，而 agent 领域数月即可翻篇（本仓库自己就有先例：excel 轨"不给工具"的判断后来被实测推翻）。§8 的检索关键词是起点而非上限。

| # | 规则 | 理由 |
|---|---|---|
| 1 | 每条建议标注来源类型：`外部材料` / `本仓库分析` / `两者结合` | 让读者知道哪些结论可以回原文复核 |
| 2 | 引用 LangGraph / LangChain 材料时，**必须核对其针对的版本**与本仓库 `pyproject.toml` 锁定版本是否一致，不一致要明说 | `create_agent` 这个 API 仍在演进，网上大量材料写的是 `create_react_agent` 等旧形态，对我们不适用 |
| 3 | 无日期、无数据来源的博客结论只能进「普遍经验」档，**不得**当作实测证据。可信度排序：官方文档 > 论文 > 带数据的工程博客 > 社区经验 | 这个领域的营销与复述内容占比很高 |
| 4 | 检索不到可靠材料的问题，直接写「未找到可靠外部证据」并说明检索过哪些方向 | 宁可空着，也不要用通用套话填充 |
| 5 | 优先 2025 年以后的材料；更早的只在讲原理（而非具体 API）时可用 | 同上：框架与模型行为变化快 |

**抓取失败**（付费墙 / 需登录 / robots 拦截）要如实记录，不得凭标题或搜索摘要推断正文内容。

---

## 1. 拍板结论（直接约束调研范围）

| # | 议题 | 结论 | 对调研的影响 |
|---|---|---|---|
| 1 | 四维度优先级 | 准确率 > 延迟 > 成本 > 并发 | 报告按此顺序组织；冲突时优先保准确率 |
| 2 | 线上基线数据 | **可经 postgres MCP 直查本地库** | 调研前先跑基线查询（见 §2.4），结论必须落在真实分布上，不接受"一般来说" |
| 3 | 换模型 / 模型分级路由 | **不考虑** | 所有"把某节点降级到小模型""按难度路由"类建议**移出范围**；优化只能来自链路结构、提示词、工具契约、缓存、工程手段 |
| 4 | 离线评测集投入 | **不投入** | 所有准确率类建议必须给出**不依赖评测集**的验证方式（人工抽查样本、契约测试、线上指标对比）；不接受"需先建 benchmark 才能验证"的建议 |
| 5 | kb / combo 两条不可达智能体轨 | **视为可砍——方案不必考虑对它们的影响** | 优化方案只对 standard 轨负责；kb/combo 既不构成约束，也不必为兼容它们做妥协。砍除动作本身另行确认（见 §3.1） |

---

## 2. 现状基线（调研的事实起点）

### 2.1 实际拓扑与串行 LLM 跳数

```
START → input_guard      haiku   输入合规审核（fail-closed，最多 3 次尝试）
      → init             haiku   语言检测 ∥ 历史 5 条 ∥ 公司列表 / portfolio 全集 / 用户信息（并发）
      → file_gate        haiku   仅有附件时：判"本轮是否需要文件内容" + 等向量化就绪（整批共享 120s 截止）
      → rewrite          sonnet  ReAct（reasoning_effort=low，绑 get_companies + get_current_user，递归上限 7）
      → retrieve_tool    sonnet  ReAct 取数 + 成文合并（_MAX_ITERS=6 / recursion_limit=13）
      → disclaimer       —       确定性选文案；仅非英文时 haiku 翻译（带进程内缓存）
      → END
generate_title           haiku   不挂图，与整张图 asyncio 并发（LangGraph 超步 barrier 限制）
```

> **关键事实**：用户看到第一个答案 token 之前，**串行经过 3～4 次 LLM 往返**（审核 → [文件门控] → 重写 → 取数首轮）。这是 TTFT 调研的主战场。

### 2.2 与直觉描述的三处出入（校正后的基线）

| 直觉描述 | 实际实现 | 影响 |
|---|---|---|
| "聊天文件处理"节点提取文件内容并入 RAG | **入库不在图内**——附件提取 + 入 RAG 在图之前由 `sse_provider` → `chat_attachment_service` 四步跨模块编排完成；图内 `file_gate` 只做 need 判定 + **等就绪** | 文件轨瓶颈在"等"不在"提取"，优化方向完全不同 |
| 免责说明是"补"的一步 | 确定性节点，仅非英文才调 haiku 翻译且有缓存 | 已接近零成本，非优化重点 |
| 重写"通过工具获取公司信息" | 是**独立的 sonnet ReAct 往返**（不是一次普通补全） | TTFT 的主要嫌疑之一 |

### 2.3 已量化的数据

| 项 | 数值 | 来源 |
|---|---|---|
| retrieve 轨工具调用次数 | 256 轮实测平均 **2.82 次**，80% ≤ 3 次 | `source/ai/CLAUDE.md` 实测记录 |
| 取数轨系统提示词体积 | `retrieval_agent_prompt.py` **337 行 / ~39KB** | 实测 |
| 最长工具 docstring | `get_benchmark_data` 75 行、`get_financials` 54 行（含 31 项指标目录） | 实测 |
| 历史窗口 | 最近 **5** 条 + `get_chat_history` 工具按需回看 | 近期改动 |
| Prompt 缓存 | OpenRouter **两个断点**（system + 末条消息），已接线 | `retrieval_agent.py` |
| standard 轨绑定工具 | **10 个**（playbook 开关关闭时 9 个） | `TOOL_REGISTRY_V2` |

### 2.4 基线数据待取（经 postgres MCP，调研前执行）

调研开始前必须先把下列分布拉出来，作为所有建议的收益估算底数：

| 指标 | 数据源 | 用途 |
|---|---|---|
| 每节点耗时分布（P50/P95） | `ai_trace` + span | 定位真实瓶颈节点，验证"3 跳串行"的实际占比 |
| TTFT 分布 | `ai_trace` span 时间戳（turn 开始 → 首个 answer_delta） | 延迟优化的基线 |
| 每轮 token 数（输入/输出/缓存命中） | `ai_llm_call_log` | 成本基线 + **缓存命中率**（C1 的关键，目前未知） |
| 工具调用次数 / 工具分布 / 失败率 | `ai_llm_tool_call_log` | 验证 2.82 次是否仍成立；找出高频与高失败工具 |
| 每轮成本分布 | `ai_llm_call_log` 成本列 | 成本优化排序 |
| 消息状态分布（success/partial/failed） | `ai_chatbot_message` | 稳定性基线 |
| 提问语言分布 | `ai_chatbot_message` / trace 属性 | 决定"中文提示词 + 多语言回答"这条的权重 |

### 2.5 已知技术债（调研需兼容的既有状况）

- **指标名 4 处平行维护**：工具 docstring / 取数提示词 / 重写提示词 / benchmark 枚举，无一致性校验。
- **`file_gate` 整批共享单一截止时间**：大 PDF 拖慢同批小文件。
- **kb / combo 轨前端不可达**：无模式选择器，斜杠命令已拆除，仅 API 直调可及。

---

## 3. 立即可做（无需调研，已定位）

### 3.1 评估砍除 kb / combo 两条轨

前端无入口、斜杠命令已拆，两轨事实上只有 API 直调可及。砍除可减少：两个子包、一份 kb 提示词、三份图测试、combo 分诊的 haiku 调用，以及"三图共享 ChatState / 装配原语"带来的耦合。

方案无需考虑对 kb / combo 产生影响

**前置确认**：是否存在 API 直调方（外部集成 / 内部脚本）。

---

## 4. 调研问题清单

### A. 准确率（最高优先级）

- **A1 问题重写是否值得保留为独立 LLM 跳？** 业界在 agentic RAG 中对 query rewriting 的主流处置：独立前置 / 合并进主 agent 首轮 / 仅在检测到指代或省略时条件触发。三者的准确率-延迟权衡实测数据。
- **A2 中文提示词 + 跟随用户语言回答**对指令遵循率的影响；有无"提示词与输出语言一致"更优的证据。
- **A3 超长系统提示词（39KB）中规则的遵循衰减**：位置效应在当前长上下文模型上是否仍成立；规则该放头、放尾、还是下沉到工具级 docstring。
- **A4 工具描述写法对工具选择正确率的影响**：长 docstring vs 精简 + few-shot vs schema 内嵌枚举。何时该把枚举写死进 schema（我们 `get_financials` 刻意用宽松 `str` 以免滞后于 Java 侧）。
- **A5 数值类问答的防幻觉手段**：强制标注数据出处、结构化输出校验、程序化取数 + 模型只做编排（已部分采用）、事后 verifier。对财务数字场景性价比排序。
- **A6 知识库该不该"总是先检索"**：proactive retrieval 固定节点 vs 模型自决调用工具。我们现在靠提示词命令"先查库"，稳定性如何提升。
- **A7 单轮批量并行工具调用的失败模式**：参数串台、重复调用、部分失败如何呈现给模型而不误导。
- **A8 公司名 / 财务期间 / close month 这类槽位的消歧**：LLM 自由推断 vs 程序化候选匹配 + 模型选序号（我们在文件归属公司推断上已用序号式，取数轨未用）。

### B. 延迟 / TTFT

- **B1 输入审核能否与主链路并发 + 事后中断**？流式产品的输入审核惯例与风险（已产出内容如何撤回）。
- **B2 rewrite 跳能否消除或后移**？例如主 agent 首轮自行澄清、或用结构化输出的单次补全替代 ReAct、或用"公司名→ID"映射缓存消除为此调工具的需求。**注意：不得以"换小模型"作为答案（拍板 3）。**
- **B3 预热 / 推测执行**：审核与重写进行时预取高频上下文的收益（已有 5 分钟进程内缓存 + single-flight，还能推进多远）。
- **B4 感知延迟补偿**：真实 token 前先流出结构化步骤（已有 tool_step 卡片），业界还有哪些手段。
- **B5 慢工具的隔离**：单个慢工具（benchmark 大窗口）不拖垮整轮的做法；部分结果降级返回。
- **B6 `file_gate` 等就绪的替代设计**：逐文件就绪即放行 / 先答后补 / 异步通知。

### C. 成本

- **C1 Prompt caching 的正确用法与命中率诊断**：断点该放几个、放在哪；什么操作击穿（我们工具 schema 与系统提示词的变更频率）；缓存 TTL 与跨轮复用的经济性；**如何度量命中率**（§2.4 要先量出来）。
- **C2 工具返回体积控制**：字段裁剪、分页、摘要化；ReAct 循环内历史工具结果的累积压缩（平均 2.82 次、最坏 6 次）。
- **C3 历史窗口策略**：固定 5 条 + 按需回看工具 vs 滑窗摘要 vs 分层记忆，在成本/准确率上的对比。
- **C4 系统提示词瘦身方法论**：哪些内容该从系统提示词下沉到工具 docstring、哪些该变成程序化约束（31 项指标目录现塞在 docstring 里）。
- **C5 中间小调用的必要性审视**：审核、语言检测、文件门控、标题、免责翻译共 5 类小调用，哪些能合并、条件化或程序化替代（**不含换模型**）。

### D. 性能 / 稳定性

- **D1** LangGraph `create_agent` 的递归上限与预算耗尽处理最佳实践（现 `_MAX_ITERS=6`，超限用已得结果收尾）。
- **D2** 同参并发工具调用去重的通用做法（我们自实现指纹 + inflight future；实测出现过 4 个逐字相同调用打爆上游到 504）。
- **D3** 流式 + SSE + 后台生成解耦架构的已知坑（已有 Redis 帧缓冲 + Last-Event-ID 重放）。
- **D4** 同会话重叠轮次的处理惯例（现用 Redis turn token 丢弃旧轮）。

### E. 验证与可观测（横切）

> **不建离线评测集**（拍板 4）。本节只问"在没有 benchmark 的前提下怎么验证改动没把事情弄坏"。

- **E1 轻量回归护栏**：提示词或工具 schema 改动后如何快速验证没退化。我们已有一批提示词**行为契约测试**（语言、数字格式、禁脚注、禁暴露内部机制、历史裁剪、playbook 开关等），这类"断言提示词渲染结果包含/不包含某规则"的做法能扩展到什么程度、业界还有哪些同类手段。
- **E2 线上指标替代离线评测**：用哪些可从 `ai_trace` / `ai_llm_call_log` / `ai_llm_tool_call_log` 直接算出的代理指标来判断准确率是否退化（如工具调用次数分布漂移、工具失败率、partial 率、重生成率、同问题重复提问率）。
- **E3 小样本人工抽查的工程化**：改动前后跑同一组固定问题并做 diff 对照的最简做法（不建标注集，只做可比对照）。
- **E4 埋点缺口**：为支撑上述对比，现有三张日志表还缺什么（尤其是 **prompt cache 命中率**，目前未知）。

---

## 5. 约束与不可变项（结论必须兼容）

1. **LLM 调用统一经 `llm_db_router`**，禁止业务侧直连 SDK；模型经 OpenRouter。
2. **取数一律经 Java 网关 `/api/web/*` 并透传用户 token**；唯二例外是 rag 知识库与 playbook 的进程内直调。租户隔离由 Redis 身份 + Java 侧负责。
3. **分层与落位规范**不可为优化而破坏：工具平铺 `ai/tools/`、一个 `@tool` 一个文件、提示词不得内联进 Python 业务代码。
4. **YAGNI 为项目强制原则**：方案要能直接映射成"改哪几个文件"，不接受预留扩展点式设计。
5. **产品语义保留**：流式、可打断（落 partial）、断流可续、分支树与 fork、工具步骤卡片、免责说明。
6. **不换模型、不做模型分级路由**（拍板 3）。

---

## 6. 明确排除范围

- 更换 LangGraph / LangChain 之外的 agent 框架。
- 自建模型、微调、本地推理。
- **更换模型或按难度分级路由**（拍板 3）。
- 前端渲染层优化（本轮只看 Python 侧）。
- RAG 向量库选型（pgvector 已定）；但**检索策略**（召回方式、rerank、两段式）在范围内。

---

## 7. 期望交付物

一份 markdown 报告，结构：

1. **执行摘要**：Top 5 建议，每条一句话 + 预期收益 + 实施成本（S/M/L）。
2. **按维度的候选清单**：每条含「问题 → 业界做法 → 对我们这套架构是否适用（含理由）→ 落地方式（改哪里）→ 验证方式 → 风险」。
3. **优先级矩阵**：收益 × 成本 四象限。
4. **不建议做的事**：看起来很美但对我们不适用的做法，及原因。这一节与推荐同等重要。
5. **参考来源**：带链接，标注日期与可信度（官方文档 / 论文 / 工程博客 / 社区经验）。

**质量要求**：优先引用 2025 年以后的材料；每条建议区分"有实测数据支撑"与"仅为普遍经验"；与我们现状冲突的建议要明说冲突点。

---

## 8. 检索关键词

```
LangGraph create_agent best practices / ReAct agent latency optimization
agentic RAG query rewriting necessity / conditional query rewriting
tool description design LLM tool selection accuracy
prompt caching cache breakpoints OpenRouter Anthropic cost optimization
long system prompt instruction following degradation position bias 2025
time to first token streaming agent perceived latency
input moderation concurrent with generation streaming interrupt
LLM-as-judge financial QA evaluation calibration
multi-tool parallel calls failure modes deduplication
conversation memory window vs summarization cost accuracy tradeoff
agent evaluation harness regression testing prompt changes
```

---
