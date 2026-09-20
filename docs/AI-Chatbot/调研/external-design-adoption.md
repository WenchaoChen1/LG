# AI Chatbot 外部设计引进调研

> 关联文档: [现状优化调研结论](./agent-optimization-findings.md) · [调研任务书](./agent-optimization-research-brief.md) · [设计文档](../设计/design-doc.md)

> 产出日期: 2026-09-17
> **与 `agent-optimization-findings.md` 的分工**：那一份是「在现状里找优化」，本份是「**从外部成熟项目引进设计**」——允许全新、允许与现状冲突、允许大改。
> 方法：四维度并行调研（编排与图结构 / 上下文与记忆 / 检索与工具 / 交互与产品形态），每维度限量约 12 次外部检索，全部标注来源与可信度。
> 拍板前提：**不换模型 / 不做模型分级路由**（业务决定，全程未据此作答）；评测集从"禁止"放宽为"可讨论"；分层规范与产品语义**均可被挑战**，但须写明用户侧影响与迁移代价。

---

## 0. 一页结论

**引进（按建议顺序）**

| # | 设计 | 收益/成本 | 一句话 |
|---|---|---|---|
| 1 | **按「节点该不该占一格」重构图** | L / S~M | 稳态路径从「6 节点、首 token 前 4 次 LLM 往返」收敛到「2 节点、1 次往返」 |
| 2 | **阶段进度帧**（guard/init/rewrite 各发一帧） | L / S~M | 干掉开头 7.2s 纯 spinner；实测 spinner ≈ 无反馈 |
| 3 | **取数条件可见可改** | L / M | 把系统猜的公司/期间/指标/数据类型摆在答案上方、每项可点改；只在真歧义时才反问 |
| ~~4~~ | ~~数字级确定性溯源~~（前端角标 + 来源卡） | L / M | ⚠️ **优先级后置（2026-09-17）**：改动面大（二期前端 400–600 行），而**问题规模未知**——没人报过数字错，`ungrounded_number_count` 也还不存在。<br>**先做另一份报告的 P2-3（数值接地探针，成本 S、前端零改动、可离线回算）拿到占比，再决定这条要不要做。** 详见 §1.4 |
| 5 | **`ContextEditingMiddleware` 裁剪工具结果** | M / S | langchain 1.2.18 自带；阻塞点已排除（见 §3）。⚠️ 须等缓存修复收益落袋后再上 |
| ~~6~~ | ~~会话锚点程序化注入~~ | — | ⚠️ **降为条件项**：四个信号都显示我们没有多轮指代问题（线程 80% ≤3 轮、唯一深度会话零指代、指代提问 1.5%、`get_chat_history` 0 调用）。等生产数据证实后再做 |
| 7 | **后台完成通知** | M / S | 整轮最长 204.6s，已进入「用户会切走」区间，而生成完了没人告诉他 |

**不引进（均有具体理由，见 §4）**：子 agent / 多智能体 · reflection 自我纠错节点 · TodoWrite 计划节点 · `interrupt()` 做反问 · checkpointer · LLM 滚动摘要 · Mem0/LangMem 自动事实抽取 · 自建图记忆 · Tool Search / defer_loading · `LLMToolSelectorMiddleware` · MCP code execution · 拆成「取数 agent + 成文 agent」 · 检索侧改动（BM25 升级 / rerank，前提不成立）· **动态预算写进提示词** · 原始思维链可视 · Canvas/Artifact 可编辑答案 · 阻塞式澄清做默认

---

## 1. 最值得引进的设计

### 1.1 按「节点该不该占一格」重构图 ★ 本轮最大单项收益

**判据**（从 open_deep_research 的图结构 + LangChain middleware 的分工反推）：一个节点值得占据图上一格，当且仅当它满足三者之一——**制造分支点** / **制造扇出扇入 barrier** / **是持久化恢复边界**。不满足的横切关注点，框架一律放进 middleware 钩子（`before_agent` / `before_model` / `wrap_model_call` / `wrap_tool_call` / `after_model` / `after_agent`，1.2.18 已具备）。

**为什么这不是洁癖**：LangGraph 超步是 barrier 语义——**每加一个节点 = 一道强制串行栅栏**。我们自己已经踩到过（`generate_title` 正因此只能挂在图外与整图 asyncio 并发）。在延迟敏感的单轮问答里，节点数是负债不是结构清晰度。

按此判据回看六个节点：

| 节点 | 判定 | 处置 |
|---|---|---|
| `input_guard` | **不合格**——唯一出口是"放行或中止"，没有真正分支语义，是典型横切关注点 | **出图**，与主链并发（见 1.1.1） |
| `init` | **不合格**——纯 IO 预取 + 一次 haiku 语言检测 | IO 部分应在**请求进来第一毫秒就 fire**（与 guard 同时起跑），而不是等 guard 放行；语言检测**会话级缓存、只首轮检测** |
| `file_gate` | **半合格**——是真分支（有无附件），但目前是无条件边靠节点内 early-return 跳过 | 改成**条件边**，无附件轮次连这道栅栏都不经过 |
| `rewrite` | 合格（引入 1.3 后是真正的分支点） | 保留 |
| `retrieve_tool` | 合格（主体） | 保留 |
| `disclaimer` | **不合格**——确定性选文案 | 降为 retrieve 后的后处理函数或 `after_agent` 钩子 |

**净效果**：稳态（无附件）路径从「6 节点串行、首 token 前 4 次 LLM 往返」收敛到「**2 节点、首 token 前 1 次 LLM 往返**」。不依赖任何新框架能力。

#### 1.1.1 问题合规检查（`input_guard`）如何并发化

OpenAI Agents SDK 官方文档：input guardrail **默认与 agent 并行执行**（原文 *"This provides the best latency since both start at the same time"*）；阻塞模式是**可选项**，其用途被明确写为 *"ideal for cost optimization and when you want to avoid potential side effects from tool calls"* ——即省钱/防副作用，**不是**防内容泄漏。

**做法**：`input_guard` 与 `init` / `file_gate` / `rewrite` 并发，**在 retrieve 入口 join**。

- TTFT = `max(input_guard, 前置三步)` + retrieve 首 token
- **泄漏风险为零**——join 点在任何用户可见 token 之前，被拦截时前端什么都没收到
- 改动：`build.py` 两条边

**实测：并发后它的耗时会被完全吸收**（76 轮，`ai_llm_call_log` 按 trace 聚合）

| | `input_guard` | 前置三步（`detect_language` + `file_gate` + `rewrite`） |
|---|---|---|
| 平均 | **1,991 ms** | **8,115 ms** |
| 最大 | 3,952 ms | 68,764 ms |
| **它更慢的轮次** | **0 / 76** | |

一次都没有。所以并发之后它那 2 秒**完全藏进后面那 8 秒里**，`max()` 取的恒是前置三步——这一跳等于被彻底摘掉，无需任何额外机制。

### 1.2 阶段进度帧：干掉开头 7.2s 空白

**硬证据**（本轮最强的一条用户实验）：CUI'25（arXiv 2507.22352）N=54 受控实验，延迟 1.5/4.0/6.5s 三档 × 无反馈 / 旋转图标+音效 / 自然填充语——**自然填充在 4s 档 p<0.01、6.5s 档 p<0.0001 显著改善感知响应时间；而纯旋转图标相对无反馈没有显著改善**。结论"延迟 >4s 显著劣化体验"。

**即我们现在的 spinner 约等于没有**，而开头正好是 7.2s 纯 spinner、84% 的轮次 TTFT >10s。

另一篇 arXiv 2602.15569（N=45 受控混合方法）对比"播报计划步骤 / 播报中间结果 / 静默只给终答"：中间反馈**显著提升感知速度、信任、UX 并降低任务负荷**，跨任务复杂度稳定；访谈要求**冗长度自适应**（初期高透明建信任，熟了要收敛）。

**落地**：后端在 guard / init / rewrite 各发一帧 `stage` 事件，rewrite 完成时把改写后的问题当 label 发出——**这一步天然就是"计划"**。前端把 `ToolStepsCard` 扩成统一进度卡收纳 stage + tool_step，默认折叠一行。

> **`stage` 帧**：新增一种 custom 帧（与现有 `answer_delta` / `answer_reset` / `tool_step` / `disclaimer` 并列），用来播报**取数之前的节点进度**。字段与 `tool_step` 同构（`step_id` / `status` / `label`），**不落库、只直播**，历史回放里不出现。

**必须注意**：不能新增第二种卡片与 tool_step 并列，会噪——两类帧进同一张进度卡。后端 S（三处 emit + 一个 FrameKind 值），前端 M（`messageReducer` + `ToolStepsCard` + `MessageBubble`，约 200–300 行）。

### 1.3 取数条件可见可改

**一句话**：用户问 *"How's our revenue doing?"*，`rewrite` 在背后悄悄定了四件事——**哪家公司、哪个期间、哪个指标、实际值还是预测值**——然后直接拿去取数。用户全程不知道系统认成了什么；猜错了他拿到的是**一个格式正确、数字也正确、但答的是另一个问题**的答案，而且很可能发现不了。

这条建议就是把这四个值摆到答案上方、**每项可点改**：

```
┌────────────────────────────────────────────────────┐
│  LGPI ▾    FY2025 Q3 ▾    Revenue ▾    Actuals ▾   │  ← 本轮取数条件
└────────────────────────────────────────────────────┘

Revenue for Q3 was $4.2M, up 12% from Q2.
```

点任一项改值 → **走已有的 fork 链路重问**（不需要新接口，与"编辑问题重问"同一条路）。

**为什么不是"让它学会反问"**：arXiv 2605.25284 实测——LLM 被问时能识别 60–80% 的歧义，但在真实作答场景里**只有 0–5% 会主动澄清，带检索上下文后近 0%**。我们的 `rewrite` 正是"带检索上下文强行推断"这一档，所以**"从不反问"是结构性可预期的，不是提示词写得不好**——靠加措辞改不动它。

**为什么不做阻塞式反问**：TTFT 已 16.4s，**阻塞式反问 = 一轮变两轮 = 32s 起步**。所以默认走"先答 + 条件可改"，只把真歧义留给阻塞式。

**方案**：
1. rewrite 输出结构化 assumption（company / period / metric + confidence），随 1.2 的 stage 帧一起发；
2. 前端渲染成**可点条件栏**，点击改值 → **复用现有 fork 链路**重问（不用新接口）；
3. **只在硬歧义**（多公司名命中、期间无法解析）时才升级为阻塞式选择题，**带默认选中项、一次为限**；
4. 条件栏只在"本轮推断与上轮不同"或低置信度时展开，否则每轮都出会变噪声。

**副产品**：定点纠错不必单做——用户纠错的绝大多数就是"公司/期间/口径认错了"，改条件即可。

#### ⚠️ 真实成本：`rewrite` 目前没有结构化输出

方案第 1 条不是"给 rewrite 加个字段"——**它现在根本没有字段**。产物是一个字符串：

```python
rewritten = _extract_rewritten(result)
if not rewritten or rewritten == question:
    return {}
return {"rewritten_question": rewritten}
```

公司名、月份、指标全揉在一句自然语言里，**从未以字段形式存在过**。"rewrite 在做槽位解析"是**提示词层面的描述，不是数据层面的事实**。

所以本条要做的是**把 rewrite 的输出契约从字符串改成结构化对象**：

| 要改的 | |
|---|---|
| 输出契约 | 字符串 → 结构化（`ToolStrategy` 或 `ProviderStrategy`，1.2.18 两种都有） |
| 下游 | `retrieval_agent` 现在拿 `rewritten_question` 拼进 `current_q`，要改成消费字段 |
| 提示词 | `rewrite_prompt.py`（139 行）+ **`rewrite_scenarios.py` 11,782 字符 / 4 个业务场景剧本** |
| `ChatState` | 加字段 |

**最硬的骨头是 `rewrite_scenarios.py`**——它的 4 个场景**输出的是取数编排指令，不是槽位**：

> 场景二 · 跨公司 Benchmark 排名
> close_month 相同的公司合并为一次取数，不同 close_month 分次取…
> **绝不**把不同 close_month 的公司并进同一次取数；**绝不**为了并成一次而把月份撑成跨月区间——

这种"怎么分批取数"的指令**塞不进 `{company, period, metric}` 这类扁平槽位**。要么槽位里留一个自由文本字段承接它（那就退化回现在的形态），要么把 4 个剧本重新设计。**这是本条从 M 涨到 L 的唯一变量。**

⚠️ 后端要真能吐出置信度，否则退化成装饰。

### 1.4 数字级确定性溯源（红线场景）— ⚠️ 优先级后置

> **为什么后置（2026-09-17）**：它解决的问题是**答案里的数字不可验证、出错不可定位**——取错公司/期间/口径、模型编数、模型自己算错，这三类**全是静默错误**（格式正确、看起来专业、用户发现不了）。结构上这个缺口真实存在。
>
> **但问题规模未知**：没人报过数字错，`ungrounded_number_count` 探针也还不存在。在不知道问题有多大的情况下先付 400–600 行前端，不划算。
>
> **正确顺序**：先做另一份报告的 **P2-3 数值接地探针**（同一套机制的便宜一半：成本 S、单文件、前端零改动、**可对历史 71 条消息离线回算拿到基线**）。拿到 ungrounded 占比后——
> - 接近 0 → "编数字"不是问题，本条二期可继续缓；
> - 有明显占比 → 本条变刚需，且手里已有具体案例。
>
> **P2-3 是本条的定价依据。** 两条已一并后置。

**核心判断：数字不要走模型生成的 citation。**

Anthropic 的 `search_result` content block（原生 citation，`cited_text` 不计 output token，`langchain_anthropic 1.4.7` 已能解析回程 annotation）适合**文本片段**引用——它的最小可引用单位是一个 text block。而我们的数字来自 Java 网关的结构化取数，不是文档片段。

**对数字的正确做法是在数据层做确定性溯源**：
- **Python 侧**（不是模型）维护坐标 → 来源描述（表/期间/口径/取数时间）的映射；
- 前端按坐标挂角标，点开显示来源卡。

**前提修正（2026-09-17 实测，两处，均使这条更划算）**

**① 不需要给每个数值加 `ref` 字段——坐标已经在返回结构里。** 实测 `get_financials` 的返回本身就是四层嵌套：

```json
{"companies": [{"company_id": "d5a26a9a-…", "currency": "USD",
  "metrics": {"Monthly Runway": {"2026-02": {"Actuals": "N/A (…)"}}}}]}
```

即 `company_id → metric → month → data_type → value`，**JSON 路径本身就唯一标识了每个数值**。研究员说的"改各取数工具的返回 envelope 加 ref"这一步可以省掉 → 成本从 **M~L 降到 M**（前端占大头）。

**② 研究员漏了一个环节：谁把正文里的数字对应到坐标。** 它的核心论点是「模型全程不参与引用生成，所以引用不可能被编造」，但没说清映射由谁建立。只有两条路：

| 方案 | 后果 |
|---|---|
| 模型在正文里写 `[[v:FIN:…]]` 标记 | **核心论点直接崩塌**——模型在生成引用，就能标错 |
| **Python 按值匹配**：抽出正文数字，去工具返回的数值集合里找精确匹配，命中则挂坐标 | 确定性，论点成立 |

必须走第二条。而它与另一份报告的 **A5「程序化数值接地校验」是同一套机制**（都是"抽正文数字 → 比对工具返回集合"），应**合并为一个实现**：

- 命中 → 挂溯源角标（本条）
- 未命中 → 计入 `ungrounded_number_count` 探针（A5）

⚠️ 待定规则：两个工具返回了同一个值时挂哪个坐标。

**模型全程不参与引用生成，所以引用不可能被编造。** 这与我们"派生计算全在 Python 侧、模型只拿成品数值"的既有原则是同一思路的延伸。

**两条轨分开，不要用一套机制**：知识库/playbook 的文本型回答适合用原生 `search_result` citation；数字轨用 ref。

**呈现形态**（眼动实验 PMC13513764，N=23，四版式各看 60s）：卡片列表首次注视最快 **0.96s** vs 裸链接 15.65s（p<0.001），但**主观最偏好的是行内组件**，作者结论"注意力 ≠ 偏好"；四版式在信任度评分上**无显著差异**（p>0.49）。
→ **行内轻标记 + 点开展开卡片**，兼顾偏好与可发现性。

**效果证据**（UIST'26 Attribution Gradients，arXiv 2510.00361，N=20 组内）：首次抵达来源快 48s（103s vs 152s）、打开来源数 3.5×、修订质量 3.65 vs 2.35（p<0.01）、多补 35% 事实（p=.03），且**该组 0 引入错误、对照组 5 个**。
**反面**：arXiv 2604.15326 报告各平台引用 hover/click 均 <25%（ChatGPT ~22% hover / 12% click），满意度仍 >4.0——"有引用就信，不点开"。

**分两期**：
- 一期（成本 S）：**工具卡不折叠 + 卡内显示参数与返回摘要**——已能让用户核对口径；
- 二期（成本 L）：数字级绑定，需新行内语法 + `parseChartFences` 同款历史回放解析，前端 400–600 行。

⚠️ **标错比不标更糟**（会制造虚假可信）。只标直接取自工具返回的数，LLM 二次计算的（增长率等）不标或标为"基于 A、B 计算"。
⚠️ 来源等级要区分：我们有 `fi_*` 实数、benchmark 同行组数据、预测数据三类，混在一句话里不区分是真实的误导风险——`ref` 里带 `source_class`，前端用不同颜色角标。

### 1.5 `ContextEditingMiddleware` 裁剪工具结果（阻塞点已排除）

`langchain 1.2.18` **自带** `ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger, keep, clear_at_least, clear_tool_inputs, exclude_tools, placeholder)])`，等价于 Anthropic 服务端的 `clear_tool_uses_20250919`，落点就是 `retrieval_agent.py` 已有的 `middleware=[mw]` 加一项。

Anthropic 官方 cookbook 同一任务实测：无管理峰值 335,279 token → 仅开清除 **173,137 token（-48%）**。

**两个研究员标为阻塞点的问题已排除**：他们都要求先确认"工具步骤卡片是不是从 messages 回读渲染的"。实测——卡片是**直播态专有**（`messageReducer.ts` 的 `steps` 由 `tool_step` 事件流式累积），而历史回放的 `parseChartFences.ts` **只解析 ```chart 与 ```disclaimer 两种围栏**，卡片根本不从消息回读。所以裁剪模型侧的工具结果**不影响卡片**。

**配置要点**：
- `trigger` 默认 100,000 token，对我们（单次输入均 28k）**永不触发**，必须降到 ~45k；
- ⚠️ **与缓存冲突**：清理会改写 message 前缀 → `cache_conversation` 断点失效（Anthropic 官方："Tool result clearing invalidates cached prompt prefixes"）。必须配 `clear_at_least` 保证"清得够多才值得重写缓存"，且**在缓存修复（另一份报告的 #4）收益落袋之后再上**；
- ⚠️ **数字红线**：清掉后模型若要复算会重新调工具，数字可能与前文不一致。缓解是清除时保留一份"数值摘要"（value + ref，几十 token）而非纯占位符——`ContextEdit` 是 Protocol，可自定义实现。**绝不让 LLM 摘要数字。**

### 1.6 会话锚点程序化注入

`get_chat_history` 实测 **0 调用**，业界共识与之一致：**低显著性的按需回看工具不会被调用**——ReAct 里模型只在"明显缺信息"时才调工具，而**指代缺失它感知不到，它会直接猜**。

Manus 的 recitation（把当前目标反复复述到上下文末尾，"把全局计划推进模型最近的注意力范围"）与 Anthropic 的混合策略（少量高价值信息**预先直接塞进去**，其余才按需取）是同一件事的两半——**两家都不指望模型自己想起来去查**。

**落地**：graph state 里维护一个**程序化**（非 LLM 抽取）的 `session_anchor`：当前 company_id/name、period、currency、口径、上一次成功工具调用的参数。**由工具调用参数回填**，渲染成 10 行以内注入到**消息末尾**（靠近最后一个缓存断点，本来就是每轮变的部分，不击穿前缀），同时喂给 `rewrite_node`。

⚠️ **只从已成功执行的工具参数回填，不从用户自然语言猜**——锚点自己写错会污染每一轮。
⚠️ 锚点必须在答案里**可被用户看到并纠正**（正好由 1.3 的条件栏承担），否则沉默的错锚比失锚更糟。

**财务场景失锚的代价不是"答偏"，是"答了另一家公司/另一个期间的正确数字"**——最难被用户发现的那类错。

#### ⚠️ 前提修正（2026-09-17 实测）：本条降为条件项

研究员的论点是"第 6 轮以后指代必然失锚"。**四个独立信号都不支持这个前提**：

| 信号 | 实测 |
|---|---|
| 线程深度 | 25 个线程里 **80% ≤3 轮**，只有 2 个超过 5 轮（即历史窗口边界） |
| 唯一的深度会话（12 轮 / 2026-08-12 / 公司端） | **零指代**。12 个问题全自包含，且全是方法论问题（"what should the board see every month"、"how do we run our 401k plan"）——明显是 playbook 检索的测试会话 |
| 指代类关键词命中 | 68 条 user 消息里 **1 条（1.5%）** |
| `get_chat_history` 调用 | **0 次** |

**但这既不能证实也不能否证**：线程深度与提问方式都是**用户行为**，开发库里的"用户"就是开发者，而那 12 轮明显是刻意构造的测试用例。

→ **处置：降为条件项。** 前提是生产数据显示指代类提问确实存在（用下面这条查询）。在那之前做它，是为一个未经证实的问题建设施。

```sql
-- 指代类提问占比 + 线程深度分布，两条都要看
SELECT count(*) AS total,
       count(*) FILTER (WHERE content ~* '之前|上面|刚才|前面那条|上一条|translate|summari[sz]e') AS referential
FROM ai_chatbot_message WHERE role='user';

SELECT turns, count(*) AS threads FROM (
  SELECT thread_id, count(*) AS turns FROM ai_chatbot_message WHERE role='user' GROUP BY thread_id
) s GROUP BY turns ORDER BY turns;
```

### 1.7 后台完成通知

- **后台完成通知**（加法）：我们的续流/partial 语义**比多数对话产品完整**，唯一缺口是——用户切走之后生成完了没人告诉他。整轮平均 39.4s、最长 204.6s，已进入"用户会切走"的时长区间。后端流终止时写一条轻量通知，前端会话条目加"已完成"圆点。收益 M / 成本 S。

---

## 2. 与我们现有做法直接冲突的一条原则

**Manus：工具不要按轮动态增删。** 每轮换前缀 = 每轮 cache miss，省下的 token 不够赔缓存写入（Claude 缓存/未缓存输入价差 10×）。

这条**直接否决**一整类流行做法：按轮动态裁剪工具集、LLM tool selector、把记忆片段拼进 system prompt。

**我们唯一在这么做的地方**：`_tools_for_turn(end_type, use_playbook)` 在 playbook 开关关闭时不绑 `search_playbooks`。
（`end_type` 那一维目前**不产生差异**——`TOOL_REGISTRY_V2` 里当前没有任何工具声明 `end_types`，两端绑的是同一套。）

### ✅ 冲突将自动消失

**客户需求变更：playbook 后续一直放开。** 即 `use_playbook` 恒为 True，不再随轮变化。连带三个结果：

| | 变化 |
|---|---|
| **工具集** | 变成**完全静态** —— Manus 这条原则的冲突**彻底消失**，不需要任何调和手段 |
| **`_tools_for_turn`** | playbook 分支可直接删掉 |
| **系统提示词碎片** | `_PLAYBOOK_RULES` 不再是条件段，碎片因子从 `end_type(2) × use_playbook(2) × 语言(N)` 降到 **`end_type(2) × 语言(N)`**——直接砍半（另一份报告 §3.0 的缓存碎片化分析需同步） |

**保留的原则**（供日后参考）：**永久删掉冗余工具可以，按轮动态增删不行。** 将来若要禁用某工具，不删 schema，改在中间件里拦截或在提示词里声明不可用，保住 schema 字节稳定。

---

## 3. 调研过程中实测到的新数据

| 项 | 实测 | 意义 |
|---|---|---|
| **单公司知识库语料** | 最大一家 17 篇 / 353,421 字符 ≈ **88,355 token**；其余三家 3,525 / 741 / 741 | Anthropic 明说**知识库 <20 万 token（约 500 页）时直接塞进 prompt、不需要 RAG**。最大的一家只到阈值的 44%。⚠️ **开发库，必须去生产复查**——若生产上多数公司也在阈值下，整套检索优化的前提就变了 |
| **崩溃恢复的真实判据** | trace 终态 RUNNING = **2/94 ≈ 2.1%** | 编排组原判据是"无 assistant 消息占比 24.5%"，但拆开后其中 **20 条终态是 SUCCESS**（图正常跑完）——崩溃恢复对它们毫无作用。正确指标是 RUNNING，实测 2.1% 且疑似开发者 Ctrl+C → **不引入 checkpointer** |
| **"SUCCESS 却无消息"异常** | 20 条全在 **2026-07-20~21 两天**内、连 user 消息都没有、但都有 retrieve 调用；全部 139 条消息都带 trace_id、最早 07-21 | **数据起始期的口径问题，不是数据丢失、也不是重叠轮次频繁**。之后再未出现 |
| **工具卡片是否从消息回读** | **否**——直播态专有 | 解除了 1.6 的阻塞点 |

---

## 4. 明确不引进

### 4.1 编排
- **动态预算写进提示词**（2026-09-17 移出引进清单）：Anthropic 的 effort scaling 是让编排者按复杂度显式分配预算（*"Simple fact-finding: 3-10 tool calls; direct comparisons: 10-15 calls each"*）。**但我们没有这个问题**——实测每轮 retrieve 调用数分布 `1→7轮 / 2→38 / 3→32 / 4→9 / 5→4 / 6→1 / 7→1`，均值 2.70、**众数就是 2（需要取数的物理下限：1 轮工具 + 1 轮成文）**；**49% 的轮次压缩空间为零**；预算耗尽触发率 ≤1.1%。模型很克制，没有在乱兜圈子。
  另两条理由：① 剩下 35% 的 3 次调用轮**没有任何证据表明本可以 2 次搞定**（很可能是真的需要再取一次数）；② 它是**提示词驱动的软约束**，而本报告自己的总纲刚说过"靠提示词只能逼近、不能保证"（知识库那条无条件命令实测只到 66.7%）。
  **删掉的代价为零**：若将来真要控均值，1.3 的结构化槽位一落地，取数轮次就是程序化可推算的（按 `close_month` 分组即可算出需要几次），**enabler 在 1.3 里、不在这一条里**。
- **子 agent / 多智能体**：Anthropic 自己给的反向判据——*"需要共享上下文、agent 间依赖多的领域不适合"*、*"multi-agent 约 15× token"*。我们 84% 的轮次 ≤3 次 LLM 调用、**没有可并行分解的宽度**，且取数强依赖共享上下文（公司 ACL、期间口径、已归一的指标名），正好落在"不适合"那一类。
- **reflection / self-critique / verifier 节点**：最常被推荐、最经不起查。Huang et al.（ICLR 2024，arXiv 2310.01798）测的正是我们这种"无 ground truth 的内在纠错"——GSM8K 上改对 7.6% 的同时**把 8.8% 本来对的改错了**，净负。加一个 verifier = 每轮多一次完整往返（TTFT 已 16.4s），换一个期望值为负的修正率。
  **例外**：确定性校验（数字是否出现在工具返回的 JSON 里）值得做——但那是**代码不是 LLM 节点**，不加延迟。
- **TodoWrite / 显式计划节点**：`write_todos` 面向长程任务的连贯性与外置记忆；我们是 2.70 步的单轮问答，没有"长程"可言。（`middleware/todo.py` 在 1.2.18 已装，是"不用"不是"不能用"。）
- **`interrupt()` 做澄清反问**：强依赖 checkpointer（我们没有）。我们本来就是多轮聊天形态，"提前 END + 一条普通 assistant 消息"能拿 95% 的效果、0 基础设施成本。
- **checkpointer**：见 §3。

### 4.2 记忆
- **LLM 滚动摘要压历史**：历史仅占 2.6%（761 token），压缩收益近零；且"摘要合并"是 arXiv 2605.17830 点名的污染机制之一，**财务数字过一次 LLM 摘要就可能失真**。
- **Mem0 / LangMem 式自动事实抽取**：漂亮数字（LoCoMo 上 token −90%+、p95 延迟 −91%）全部来自**闲聊型长对话**基准，与"一个数字错了就是事故"的财务问答不可迁移；LangMem PyPI 停在 0.0.30（2025-10），维护信号弱。
- **自建全量图记忆（Zep/Graphiti）**：我们的权威事实源就是 PG 业务库，再建一份 LLM 抽取的事实副本 = **制造一个会漂移的第二真相**。只借它的"双时间 + 出处"思想，不引架构。
- **跨会话事实记忆**：arXiv 2605.17830（8 种记忆架构纵向评测）——**良性使用下记忆越长违规率越高**，广检索型升到 0.30–0.50，带 recency bias 的维持 0.10–0.20；五类违规里对我们最致命的是"与既有事实矛盾"和"旧信息压过修正"。
  → 若要做跨会话记忆，**只做偏好/口径层，不做事实层**：只允许写展示偏好、口径偏好、常用公司期间、称谓四类，**禁止写任何数值**；且记忆命中**只能影响检索参数与呈现格式，不得进入答案的数字部分**。这一层收益是纯体验、不是正确性，优先级低于 1.1–1.8。

### 4.3 检索与工具
- **Tool Search / 全量 `defer_loading`**：依赖侧**已就绪**（`langchain-core 1.4.8` 的 `@tool(extras={"defer_loading": True})`、`langchain_anthropic 1.4.7` 自动挂 beta header，零改造），但 Anthropic 自己的适用线是"≥10 个工具 / 定义 >10k token / 聚合多 MCP"，反面是"<10 个工具、每个请求都要用"。我们 10 个工具里 8 个高频，上它等于给主路径**多一次 LLM 往返**换 schema token——我们平均才 2.70 次调用/轮，比例上净亏。**工具数过 20 再开。**
- **`LLMToolSelectorMiddleware`**（1.2.18 内置）：同理，用一次额外 LLM 调用筛 10 个工具是负收益。
- **MCP code execution**（Anthropic 2025-11，宣称 token 降 50~98%）：需引入代码沙箱，且**与"取数必须经 Java 网关透传用户 token"的安全边界严重冲突**——沙箱里执行模型生成的代码去调带 token 的接口，等于把租户隔离的执行点交给模型。想要它的收益，用 1.7 拿到八成、风险为零。
- **拆成「取数 agent + 成文 agent」**：首字延迟翻倍 + 流式要重做 + 可打断落 partial 的语义要重定义，而 Anthropic 那 +90.2% 的增益来自 **breadth-first 研究型任务**，不是我们这种形态。真正该借的那一半是"中间检索垃圾不进主上下文"——用 1.7 零 agent 拆分就能拿到。
- **检索侧改动（BM25 升级 / rerank）**：⚠️ **研究员的前提不成立，已移出引进清单。** 它写的是"standard 轨**如果**目前是纯向量，第一件事就是加 BM25 混合"——它自己加了"如果"，说明未核实。实测 `Processor._gather_candidates`（`rag/infrastructure/processor/base.py:508`）**早已是向量 + 关键词并发两路 + RRF 融合**，不是纯向量。
  剩下的真实差距只是：关键词那一路用的是 **`ILIKE` / trigram**（`pg_store.py:201`），不是 BM25——差在词频权重、文档长度归一、词干/停用词。所以 Anthropic 那组 5.7%→2.9% 的收益我们**已经拿到了大部分**，剩下的是"第二路排序变好"这种增量，**无外部数据可估，且没有评测集根本量不出来**（研究员自己也说 1.9% vs 2.9% 人眼看不出）。
  另一个实施坑：PG 默认的 `english` 全文配置**对中文基本无效**，而我们的文档可能中英混排。
  → **等评测集之后再评估**；rerank 更在其后。

### 4.4 交互
- **原始思维链 / reasoning 流式可视**：CUI'25 的数据只支持"有**语义**的反馈优于无反馈"，人工填充（旋转图标+音效）相对无反馈**不显著**。财务场景暴露模型的中间推理，出错时反而摧毁信任。用 1.2 的结构化阶段即可，**不要透传 thinking**。
- **Canvas / Artifact 式可编辑答案**：财务问答是"读并核对"，不是"协作写作"。成本 L，找不到对应用户价值。
- **阻塞式澄清做默认**：见 1.4。
- **取消流式改整段输出 / 改造分支树 fork**：都是既有资产，撤掉是净损失；fork 在 1.4 落地后使用率应自然下降，先观察。

---

## 5. 待拍板

| # | 事项 | 影响 |
|---|---|---|
| ~~1~~ | ~~kb / combo 两个死包~~ | ✅ **已拍板（2026-09-17）：代码先不动、不用管，等合适时机再清理。** 后续方案只对 standard 轨负责，不必为兼容它们妥协 |
| ~~2~~ | ~~单公司语料是否普遍 <20 万 token~~ | ✅ **已拍板（2026-09-17）：文件只会越来越多，按"会超过阈值"规划。** 不必考虑"整库塞进 prompt"那条路。但建议仍把这条查询纳入健康指标，作为**语料增长的监控项**——若某公司逼近 20 万 token，需要重新评估分块与召回策略 |
| ~~3~~ | ~~评测集~~ | ✅ **已拍板（2026-09-17）：做折中版——先只标 15~20 条、且只标槽位**（公司 / 期间 / 指标 / 该不该查知识库），**不标答案内容**。约半天工作量，足够覆盖 1.3 的验证需求。<br>不标答案内容是关键：`temperature=0.3` 且数据实时变，答案原文无法比对；槽位是可机器比对的结构化事实。<br>1.4 二期（数字级绑定）与检索侧改动（见 §4）需要更大的标注集才能验证其量级，**等这 15~20 条跑顺后再评估要不要扩**。<br>1.1 / 1.2 / 1.5 可无评测集直接上（可回滚、不改语义）|

---

## 6. 诚实标注的证据空白

- **「首 token 前该允许几次 LLM 往返」没有任何公开基准或业界惯例数字。** 1.1 引用的外部材料只提供"guardrail 可并行"这一**机制性**证据，**没有**"几跳算多"的经验值。
  ✅ **但归因已用我们自己的数据核验完成，不再是推断**：各节点实测耗时（`input_guard` 1,991 / `detect_language` 1,983 / `file_gate` 1,272 / `rewrite` 5,216 / `retrieve` TTFB 7,160 ms）、TTFT 实测下界 16,390 ms（>10s 占 84%）、以及 `input_guard` 在 **0/76** 轮次里成为瓶颈——这三组数据共同支撑了 1.1 的收敛结论。所以 1.1 的**落点**有本地实证，只是"业界该有几跳"这个普适问题无外部答案。
- **澄清式反问的收益/代价没有公开量化数据。** open_deep_research 与 OpenAI Cookbook 都只给了"怎么做"和提示词规则，没给"反问后答案质量提升多少 / 用户流失多少"。1.4 必须灰度自测，**不能拿业界数字背书**。
- **数字型 citation 的效果数据不存在**——只有产品形态描述（cell-level citation、lineage、审计要求），没有可信的准确性/信任度实测。
- **财务/受监管领域的 agent 记忆**没有专门的公开工程实践，最接近的是 MedMemoryBench 与上述纵向安全论文，均为预印本。
- **「会话内上下文可见性」与「对话式答案定点纠错」的效果**均未找到可靠外部证据。

---

## 7. 参考来源

**一手厂商文档 / 工程博客（高可信，均已读正文）**
1. [Anthropic — Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — `response_format` concise/detailed（Slack 206→72 token）、Claude Code 25,000 token 响应上限、引导式截断、语义化标识符
2. [Anthropic — Tool search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) — `defer_loading` 机制、~55k→−85%、30~50 工具后选择准确率退化、适用/不适用清单
3. [Anthropic — Search results](https://platform.claude.com/docs/en/build-with-claude/search-results) — `search_result` 块形状、可从 tool_result 返回、`cited_text` 不计 output token、block 为最小引用单位
4. [Anthropic — Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) — top-20 失败率 5.7%/3.7%/2.9%/1.9%、rerank 延迟权衡、**<20 万 token 不必上 RAG**
5. [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — orchestrator-worker、+90.2%、agent 4× / multi-agent 15× token、effort scaling 规则、**不适用场景**
6. [Anthropic — Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing) + 官方 cookbook — `clear_tool_uses_20250919`、峰值 335,279→173,137 token（−48%）、"Tool result clearing invalidates cached prompt prefixes"
7. [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
8. [OpenAI Agents SDK — Guardrails](https://openai.github.io/openai-agents-python/guardrails/) — input guardrail 默认并行、阻塞模式的真实用途
9. [OpenAI Cookbook — Deep Research API with the Agents SDK](https://developers.openai.com/cookbook/) — Triage→Clarifier→Instruction Builder 管线、"Ask 2–3 clarifying questions"
10. [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) `deep_researcher.py` — `clarify_with_user` / `allow_clarification` / `Command(goto=END)`（一手源码）
11. [Manus — Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — KV-cache 命中率是最重要单一指标、10× 价差、append-only、**工具不要动态增删**、recitation
12. [OpenAI — Memory and new controls for ChatGPT](https://openai.com/index/memory-and-new-controls-for-chatgpt/) — saved memories / reference chat history 双层
13. LangGraph 官方 Stores / persistence 文档 — `BaseStore`/`PostgresStore`（独立于 checkpointer）、`interrupt()` 依赖持久层

**同行评议 / 预印本（含量化）**
14. Huang et al., *LLMs Cannot Self-Correct Reasoning Yet*, **ICLR 2024**, arXiv:2310.01798 — 内在自我纠错改对 7.6% / 改错 8.8%
15. CUI'25, *Mitigating Response Delays…*, arXiv:2507.22352 — **N=54**，自然填充 p<0.01 / p<0.0001，**旋转图标不显著**
16. arXiv:2602.15569, *"What Are You Doing?"* — **N=45**，中间反馈显著提升感知速度/信任/UX、降低任务负荷
17. UIST'26, *Attribution Gradients*, arXiv:2510.00361 — **N=20**，来源打开 3.5×、修订质量 3.65 vs 2.35、**0 引入错误 vs 对照组 5 个**
18. PMC13513764 眼动实验 — **N=23**，卡片首次注视 0.96s vs 裸链接 15.65s（p<0.001）、偏好行内、信任无显著差异（p>0.49）
19. arXiv:2605.25284, *Knowing but Not Showing* — 识别歧义 60–80%，**真实作答中仅 0–5% 主动澄清，带检索上下文后近 0%**
20. arXiv:2604.15326 — 各平台引用点击率 <25%、满意度仍 >4.0
21. arXiv:2605.17830 — 8 种记忆架构纵向安全评测，良性使用下记忆越长违规率越高（0.30–0.50 vs 0.10–0.20）
22. Zep, arXiv:2501.13956 — 双时间建模（valid / ingestion time）
23. Mem0, arXiv:2504.19413 / ECAI 2025 — 数字来自 LoCoMo，**外部效度受限**

**弱证据 / 仅作形态参考（已标注，未用于支撑量化结论）**
24. NN/g《Less Chat, More Answer》（n=9 定性）、《5 Dimensions of Site-Specific AI Chatbots》
25. Microsoft《Up to 40% better relevance… agentic retrieval engine》— 厂商自测，仅取"chat history 归一 + 子查询并行"的形态
26. 金融分析产品（Daloopa 等）的 cell-level citation 形态 — 产品观察
27. deepagents `write_todos` 社区 issue — 二手

**本地版本核对（最高可信，直接读 `.venv` 与 `uv.lock`）**
- langchain **1.2.18** / langchain-core **1.4.8** / langgraph **1.1.10** / langchain-anthropic **1.4.7** / langgraph-checkpoint 2.1.2（**无** checkpoint-postgres）
- ⚠️ **官网文档是 1.3.x 线**，多处 API 不通用（如 `ToolErrorMiddleware` 需 ≥1.3.14，本地不存在）
- 本地实际存在的 middleware：`tool_call_limit` / `model_call_limit` / `context_editing` / `human_in_the_loop` / `summarization` / `todo` / `pii` / `model_fallback` / `tool_selection` / `tool_retry`
- `langchain/agents/structured_output.py` — `ToolStrategy`（模型可不产出）vs `ProviderStrategy`（语法层强制）
- 前端：`messageReducer.ts`（286 行，block 联合类型）/ `ToolStepsCard.tsx`（62 行）/ `parseChartFences.ts`（77 行，**历史回放只认 ```chart 与 ```disclaimer 两种围栏**）
