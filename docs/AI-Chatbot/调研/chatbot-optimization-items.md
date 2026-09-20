# AI Chatbot 优化项

> 关联文档: [现状优化调研结论](./agent-optimization-findings.md) · [外部设计引进调研](./external-design-adoption.md) · [调研任务书](./agent-optimization-research-brief.md) · [设计文档](../设计/design-doc.md)

> 产出日期: 2026-09-17
> 本文件把两份调研的优化项合并为一份，**按收益由高到低排列**。基线实测数据与一页结论见原两份文档。
> 拍板前提：**不换模型 / 不做模型分级路由**；评测集已定为折中版（15~20 条、只标槽位）；分层规范与产品语义可被挑战，但须写明用户侧影响与迁移代价。

---

## 节点现状

    START → input_guard      haiku   输入合规审核（fail-closed，最多 3 次尝试）
          → init             haiku   语言检测 ∥ 聊天历史 5 条 ∥ 公司列表 / portfolio 全集 / 用户信息（并发）
          → file_gate        haiku   仅有附件时：判"本轮是否需要文件内容" + 等向量化就绪（整批共享 120s 截止）
          → rewrite          sonnet  ReAct（reasoning_effort=low，绑 get_companies + get_current_user，递归上限 7）
          → retrieve_tool    sonnet  ReAct chatbot主节点：取数 + 成文合并（_MAX_ITERS=6 / recursion_limit=13）
          → disclaimer       —       确定性选文案；仅非英文时 haiku 翻译（带进程内缓存）
          → END
      generate_title         haiku   不挂图，与整张图 asyncio 并发（LangGraph 超步 barrier 限制）

---

## 1. 按「功能该不该占一个节点」重构图 ｜ 收益 L / 成本 S~M

**判据**（从 open_deep_research 的图结构 + LangChain middleware 的分工反推）：一段功能值得独占一个图节点，当且仅当它满足三者之一——

| # | 判据 | 说明 |
|---|---|---|
| ① | **它的产出决定图接下来走哪条路** | 即条件边的判断依据 |
| ② | **必须等多条并行分支都跑完才能继续** | 多路并行各自执行，在这里汇合 |
| ③ | ~~是崩溃恢复的存档点~~ | ⚠️ **对我们不适用**——我们没有 checkpointer（已明确不引进），图状态不落盘，"恢复边界"在我们的图里不存在 |

不满足的横切关注点，框架一律放进 middleware 钩子（`before_agent` / `before_model` / `wrap_model_call` / `wrap_tool_call` / `after_model` / `after_agent`，1.2.18 已具备）。

**所以落到我们这里，节点只有两种正当理由：决定走哪条路，或者等多条并行分支汇合。**

**为什么这不是洁癖**：LangGraph 超步是 barrier 语义——**每加一个节点 = 一道强制串行栅栏**。我们自己已经踩到过（`generate_title` 正因此只能挂在图外与整图 asyncio 并发）。在延迟敏感的单轮问答里，节点数是负债不是结构清晰度。

按此判据回看六个节点：

| 节点 | 判定 | 处置 |
|---|---|---|
| `input_guard` | **不合格**——唯一出口是"放行或中止"，没有真正分支语义，是典型横切关注点 | **出图**，与主链并发（见下） |
| `init` | **不合格**——纯 IO 预取 + 一次 haiku 语言检测 | IO 请求应**一进图就立即发出**（与 `input_guard` 同时起跑），而不是等它放行；语言检测**会话级缓存、只首轮检测** |
| `file_gate` | **半合格**——是真分支（有无附件），但目前是无条件边靠节点内 early-return 跳过 | 改成**条件边**，无附件轮次连这道栅栏都不经过 |
| `rewrite` | 合格（引入 §3 后是真正的分支点） | 保留 |
| `retrieve_tool` | 合格（主体） | 保留 |
| `disclaimer` | **不合格**——确定性选文案 | 降为 retrieve 后的后处理函数或 `after_agent` 钩子 |

**改造后的节点形态**（对照开头的「节点现状」）：

    START ─┬→ input_guard    haiku   出图，与主链并发；在 retrieve 入口 join，违规则短路到 END
           │                         （不再占节点，改为图外并发任务）
           ├→ IO 预取        —       公司列表 / portfolio / 用户信息 / 聊天历史 5 条，一进图即发
           ├→ 语言检测       haiku   会话级缓存，只首轮检测（后续轮直接复用 thread 上的值）
           │
           └→ file_gate      haiku   ← 条件边：仅有附件的轮次才进这一格
                  ↓
              rewrite        sonnet  分路点（引入 §3 后：先答 / 真歧义才反问）
                  ↓
              retrieve_tool  sonnet  主体：取数 + 成文合并
                  ↓
              disclaimer     —       降为后处理函数 / after_agent 钩子，不再占节点
                  ↓
                 END
      generate_title         haiku   不变，仍挂图外与整图并发

**净效果**：稳态（无附件）路径从「6 节点串行、首 token 前 4 次 LLM 往返」收敛到「**2 节点、首 token 前 1 次 LLM 往返**」——只剩 `rewrite`（分路）和 `retrieve_tool`（主体）两格，其余全部出图并发或降为钩子。不依赖任何新框架能力。

### 1.1 问题合规检查（`input_guard`）如何并发化

**业界做法**：OpenAI Agents SDK 官方文档里，input guardrail **默认就与 agent 并行执行**（原文 *"This provides the best latency since both start at the same time"*）；阻塞模式是**可选项**，其用途写的是 *"ideal for cost optimization and when you want to avoid potential side effects from tool calls"*（省钱 / 防工具副作用）。

即：**"审核必须串在最前"不是行业惯例，并行才是默认。**

**做法**：`input_guard` 与 `init` / `file_gate` / `rewrite` 并发，**在 retrieve 入口 join**。

- TTFT = `max(input_guard, 前置三步)` + retrieve 首 token
- **泄漏风险为零**——join 点在任何用户可见 token 之前，被拦截时前端什么都没收到
- 改动：`build.py` 两条边

### 1.2 TTFT 能压到多少

**现状**：`input_guard 2.0 → init 2.0 → rewrite 5.2 → retrieve TTFB 7.2 = 16.4s`

| 阶段                      | 算法 | TTFT | 相对现状 |
|-------------------------|---|---|---|
| **上面重构后**               | `max(2.0, 0.1) + 5.2 + 7.2` | **14.4s** | **−2.0s** |
| **再叠加 §6 rewrite 去工具化** | `2.0 + (5.2 → 1.7~3.2) + 7.2` | **11.0~12.4s** | **−4.0~5.4s** |

⚠️ **本节只省 2.0s，不是 3.9s**——两项并发**不叠加**。`init` 的 2.0s 被拆解后其实只剩 `detect_language` 那一次 haiku 调用（Java IO 已被 `company_service` 的 5 分钟缓存吃掉），把它的 await 后移到 retrieve 入口后 init 降到 ~0.1s；但 `max(input_guard, 其余)` 仍被 `input_guard` 的 2.0s 卡住——**省下的那 1.9s 被它吃掉了**。调研初稿把两项相加得出"省 3.5–4.0s"，是重复计算。

**要再往下压，只能动 `rewrite`（§6）与 `retrieve` 的首 token（7.2s，模型自身延迟，本轮无解）。**

---

## 2. 知识库检索改为结构化前置预检 ｜ **需求达成（非收益项）** / 成本 M

> **不是优化，补一个没被满足的需求。**
> 
> 产品要求是**每轮必查知识库**（提示词里写的就是无条件必做、逐条堵死三个跳过借口），而实测只有 **66.7%** 的轮次真的查了。剩下那三分之一的答案**没看过用户上传的文档就生成了**——用户可能拿到"我没有这方面的信息"，而文档里明明写着。
> 所以它的价值不是"更快 / 更省 / 更准"，而是**把 66.7% 抬到 100%，让系统做到它声称在做的事**。放在本清单第 2 位是因为紧迫性，不是因为收益量级。

**为什么加措辞没用**：这已经是提示词里全文措辞最强的一条硬命令，**修了两次提示词才把覆盖率从 30.6% 拉到 66.7%，仍未到 100%**。问题不在措辞而在机制——**软约束换不来确定性**。

**落地**：进入 agent 前进程内直调一次 `search_service.recall`，结果作为**预置 ToolMessage 注入**；工具仍保留绑定（模型可用更好的检索词再查一次）；`_RULES` 检索段大幅缩短（约 20 行）。

**为什么不照搬业界的"让 agent 自决检索"**：2025 自适应检索共识优化的是"省掉无用检索的开销"，而我们的知识库检索是**进程内直调、空结果零代价**（均返回 2,585 字符，最小的工具之一）。它优化的变量在我们这里 ≈0，牺牲的变量（漏检）是我们的首要风险。照搬会把事做反。

**风险**：预检词质量可能低于模型自造词。缓解：保留工具绑定 + 监控"预检之外的主动再查次数"；若偏高则改用"原问 + 补全版"各查一次取并集。

---

## 3. 取数条件可见可改 ｜ 收益 L / 成本 M~L（风险高）

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
1. rewrite 输出结构化 assumption（company / period / metric + confidence），随 §4 的 stage 帧一起发；
2. 前端渲染成**可点条件栏**，点击改值 → **复用现有 fork 链路**重问（不用新接口）；
3. **只在硬歧义**（多公司名命中、期间无法解析）时才升级为阻塞式选择题，**带默认选中项、一次为限**；
4. 条件栏只在"本轮推断与上轮不同"或低置信度时展开，否则每轮都出会变噪声。

**副产品**：定点纠错不必单做——用户纠错的绝大多数就是"公司/期间/口径认错了"，改条件即可。

### 3.1 ⚠️ 真实成本：`rewrite` 目前没有结构化输出

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

⚠️ **与 §6 共享同一个前置改造** —— 两条不是独立建议，改一次两条都拿到。

---

## 4. 阶段进度帧：干掉开头 7.2s 空白 ｜ 收益 L（体感）/ 成本 S~M

**硬证据**（本轮最强的一条用户实验）：CUI'25（arXiv 2507.22352）N=54 受控实验，延迟 1.5/4.0/6.5s 三档 × 无反馈 / 旋转图标+音效 / 自然填充语——**自然填充在 4s 档 p<0.01、6.5s 档 p<0.0001 显著改善感知响应时间；** 而纯旋转图标相对无反馈没有显著改善。 **结论"延迟 >4s 显著劣化体验"** 。

**即我们现在的 spinner 约等于没有**，而开头正好是 7.2s 纯 spinner、84% 的轮次 TTFT >10s。

另一篇 arXiv 2602.15569（N=45 受控混合方法）对比"播报计划步骤 / 播报中间结果 / 静默只给终答"：中间反馈**显著提升感知速度、信任、UX 并降低任务负荷**，跨任务复杂度稳定；访谈要求**冗长度自适应**（初期高透明建信任，熟了要收敛）。

**落地**：后端在 guard / init / rewrite 各发一帧 `stage` 事件，rewrite 完成时把改写后的问题当 label 发出——**这一步天然就是"计划"**。前端把 `ToolStepsCard` 扩成统一进度卡收纳 stage + tool_step，默认折叠一行。

> **`stage` 帧**：新增一种 custom 帧（与现有 `answer_delta` / `answer_reset` / `tool_step` / `disclaimer` 并列），用来播报**取数之前的节点进度**。字段与 `tool_step` 同构（`step_id` / `status` / `label`），**不落库、只直播**，历史回放里不出现。

**必须注意**：不能新增第二种卡片与 tool_step 并列，会噪——两类帧进同一张进度卡。后端 S（三处 emit + 一个 FrameKind 值），前端 M（`messageReducer` + `ToolStepsCard` + `MessageBubble`，约 200–300 行）。

---

## 5. `session_id` 粘性路由 ｜ 收益 成本 −33% / 成本 S

缓存是**端点本地的**（sonnet-5 / opus-5 在 OpenRouter 有 10 / 11 个上游端点）。OpenRouter 有隐式粘性、但**滞后触发**——不设 `session_id` 时要先观察到一次命中才开始粘，于是每条会话都要先耗掉一个冷启动窗口。retrieve 每轮 2.70 次调用，**轮内命中确定存在**，粘性是它能否落袋的前提。

> **先纠正一个容易夸大的说法**：OpenRouter **默认就有隐式粘性**，不是每次调用都在 10~11 个端点里随机乱跳。但它是**滞后触发**的——不设 `session_id` 时，系统"只在检测到缓存命中之后"才开始粘。而要产生命中，就得先偶然落回写入缓存的那个端点。
> 所以缺口不是"全程乱跳"，而是每条会话开头的**冷启动窗口**：这期间的请求可能反复写入不同端点、各付一次 1.25× 写入费，直到偶然命中一次才粘住。设 `session_id` 的价值就是把粘性从"命中之后"提前到"**任意一次成功请求之后**"，消掉这个窗口。
> 在我们的量级上这并非小事——retrieve 每轮平均只有 **2.70 次**调用，冷启动哪怕只浪费 1 次，占比就已经很高。

| 项 | 内容 |
|---|---|
| 参数 | 请求体顶层 `session_id`，或 HTTP 头 `x-session-id`（≤256 字符） |
| 生效时机 | 设了就在**任意一次成功请求后**生效，不用等观察到缓存命中 |
| 过期 | **10 分钟**无活动，每次成功请求重置 |
| 故障切换 | 官方原文：*"If the sticky provider becomes unavailable, OpenRouter automatically falls back to the next-best provider."* |


**取值**：用 `thread_id`——同一会话的所有轮次粘同一端点。

**做法**：给 `TextRequest` 加一等字段，`create_agent` / `DBRouterChatModel` 加同名参数透传，由 openai_compat 翻成 wire 格式。与 `reasoning_effort` 完全同构，有现成样板可抄。

**⚠️ 风险：两个时间窗错配**。粘性会话 **10 分钟**无活动过期，而 Anthropic 缓存 TTL 默认 **5 分钟**。轮内稳赚；跨轮取决于用户思考打字的间隔；若同时上 **1h TTL**，10 分钟的粘性窗口**反而成为新短板**。两项要一起评估。

### 5.1 缓存修复的其余子项（有先后，不要并列做）

| 措施 | 对轮内命中（−33%） | 对跨轮复用（−72%） |
|---|---|---|
| ① `session_id` 粘性路由（本节） | ✅ **必需** | ✅ 必需 |
| ② rewrite 开 `cache_system` | ❌ **几乎无收益，且做完 §6 后变净亏** | ⚠️ 取决于提问间隔，未知 |
| ③ system 断点 1h TTL | ❌ 无关 | ✅ **必需**（5 分钟 TTL 下跨轮基本不可能） |
| ④ 系统提示拆稳定块 + 易变尾 | ❌ **无贡献** | ✅ 有贡献 |

**② 已降为条件项**，理由是实测账算不过来：rewrite 每轮调用数 **1 次 = 48 轮（73%）**、2 次 = 17、3 次 = 1。73% 的轮次只调一次，**根本不存在轮内复用**。按写 1.25× / 读 0.1×、前缀 ~10,030 token 折算，净收益仅 **0.7%**；rewrite 只占总成本 11.9%，折算到全局约 **0.08%**。且与 §6 直接冲突——去工具化后恒定 1 次调用，届时**该节点成本将上涨约 22%**。

**为什么 ④ 对轮内没用**：一轮内那 2.70 次调用，`end_type` / `use_playbook` / `question_language` / 日期**四个变量全是常量**，同一轮的所有调用共享**一模一样**的系统提示。

**碎片化的真实规模**：同时存活的缓存条目原为 `end_type(2) × use_playbook(2) × 语言(N)`，**但产品决定后续 playbook 一直放开**，故降为 **`end_type(2) × 语言(N)`**——碎片直接砍半，且工具集变成完全静态。
⚠️ **不要写成"× 天数"**——缓存 TTL 只有 5 分钟 / 1 小时，条目活不过一天，日期因子**不产生任何碎片**。

→ **施工顺序：① 先上（拿轮内），③ 再上（开跨轮），④ 最后。**
→ **凡是改系统提示词的动作，合并成一批上线**：改任一字节即整体击穿缓存前缀，④ 与 §2 的检索规则缩短都属此列，分次做就击穿多次。

---

## 6. rewrite 去工具化 + 公司槽位程序化 ｜ 收益 省 2–3.5s + 消三类错误 / 成本 M~L

rewrite 独占 TTFT 的 **32%**，而它 70% 的篇幅在做三件**真值在数据库里**的事；`init` 早已加载公司清单、`company_cache` 存的就是含 `close_month` 的全字段 record。仓库**已有做对了的样板**（`company_infer_prompt` 的序号式：模型不接触也不产出 company id，id 只能由服务端按序号回查候选清单得到，**杜绝编造**）。

**三个槽位分开处置，判据是"这个槽位的真值在不在数据库里"**：

| 槽位 | 处置 | 理由 |
|---|---|---|
| `close_month` | **完全程序化**，模型不参与 | 纯 DB 字段。现在用 ~15 行自然语言（"严禁用日历当月冒充"…）去约束一个可以直接查出来的值 |
| 公司 | 程序化候选 + 模型选序号 | 唯一命中直接绑定、根本不问模型；多命中才给 top-5 编号 |
| 指标 / 数据类型 | 保持宽松匹配 | 是枚举不是实体，候选生成就是全集、没有缩小作用 |

**消除三类错误**：上游派活（有实测故障记录，答案前 35% 是没人要的表格）、模型编造/挑错 company id、日历月冒充 close month。

⚠️ **与 §3 共享同一个前置改造**（rewrite 输出契约结构化，见 §3.1）——两条不是独立建议。
⚠️ rag 的 `COVERAGE_THRESHOLD`(0.50) 是**按 sonnet 改写后的措辞分布校准的**，改写形态一变要重校。**失败表现是静默的**：合法问题成片 `coverage=low` 而代码不报任何异常。**必须同批验证。**

---

## 7. 补两处埋点 ｜ 验收前提（本身不产生收益）/ 成本 S

`ttft_ms` 今天**没有任何一列直接存**，只能跨两表 + `DISTINCT ON` 拼且只得下界——**没它无法验收 §1**；`cache_write_tokens` 被丢弃导致**分不清"没写入"与"写了没读到"**——**没它无法验收 §5**。

| # | 改动 | 落点 | 成本 |
|---|---|---|---|
| 7-1 | **把「每轮对话只有一个值」的指标写进 `ai_trace.attributes`**（该 JSONB 列已存在且基本空着）：`ttft_ms` 首 token 耗时 / `tool_call_count` 本轮工具调用次数 / `budget_exhausted` 是否撞上轮次上限 / `merged_count` 去重合并次数 / `turn_superseded` 是否被新轮取代 / `agent_mode`。<br>这些值既不属于某一次 LLM 调用（放不进 `ai_llm_call_log`）、也不属于整个会话（放不进 `ai_chatbot_thread`），正好落在一轮对话这一层——而一条 `ai_trace`（`name='chatbot.chat'`）就是一轮 | `sse_provider.py` 的 `_traced_turn`、`retrieval_agent.py` 收尾 | S（**零 DDL**） |
| 7-2 | 补 `usage_cache_write_tokens` 列 | `kernel/openai_compat/usage_extract.py` → DTO/model → 一次人工迁移 | S（唯一需 DDL） |
| 7-3 | 固化 5 条健康指标 SQL（仅系统/模型行为类：工具分布漂移 / `result_char_count` 异常 / `finish_reason` 分布 / 缓存命中 / 每轮调用数分布） | 新增 `sql/analytics/chatbot_health.sql` | S |

---

## 8. `get_current_user` 解绑 + 数据程序化注入系统提示 ｜ 收益 省 ~830 tok/次 × 248 次 / 成本 S

读实现可见它**不发任何请求**——`snap = runtime.context.current_user`，数据在 `init` 节点早就取进上下文了。我们花 830 token 的 schema，让模型"调一个工具"去取**本进程已经持有**的数据。

正确做法是把这份数据程序化拼进系统提示的一个 3~5 行「当前用户」小段（姓名 / 角色 / 组织 / 可访问 portfolio 列表），工具从 retrieve 轨绑定中移除。这同时消除一个"可选但永不选"的干扰项（实测 **0 调用**）。

⚠️ 解绑后若将来管理端出现"我有哪些组合"类问题，需确保注入段里确实带了 portfolio 列表。

---

## 9. benchmark timeout 收紧 + 返回体大小埋点 ｜ 收益 P95 成本与时延封顶 / 成本 S

`get_benchmark_data` 平均 6,573 ms / 最长 12,180 ms，而 `lgpi_api/_http.py` 的 `DEFAULT_TIMEOUT = 30.0` 对所有 Java 调用一刀切、各工具无覆盖——最坏情况单个工具能吃掉 30s，而整轮已经平均 39.4s。

单次返回最大 **78,082 字符**（≈20k+ token），是 Anthropic 自家 Claude Code 默认工具响应上限（25,000 token）的约 3 倍。它造成的是**准确率损害、不只是成本**：① 同批并行调用里，巨型返回会占满注意力，兄弟结果被稀释；② 把系统提示里的真实性红线推到最远，正好落在 lost-in-the-middle 的最差位置。

**分两步（第一步先做）**：
1. benchmark 单独收紧 timeout（30s → 10s）+ **把返回体大小埋进 span**；
2. 等分布数据出来后再定截断阈值，且**必须按结构裁剪**（按公司完整块，绝不切半个公司/半个月）+ **带引导式说明**（"已截断到 N 家 × M 月，要更早月份请缩小公司范围再调一次"），而不是裸 `truncated: true`。

⚠️ **多提总比少提好**：截断必须**显式告知模型被截断了**，否则模型会把"截断"当成"没数据"，直接踩幻觉红线。

---

## 10. 后台完成通知 ｜ 收益 M / 成本 S

我们的续流 / partial 语义**比多数对话产品完整**（生成与连接解耦、Redis 帧缓冲 + Last-Event-ID 重放、切会话/刷新续流、打断落 partial 并在历史里还原），**唯一缺口是**：用户离开这个会话之后，生成完了没人告诉他。整轮平均 39.4s、最长 204.6s，已进入「用户会切走」的时长区间。

**落地**：后端流终止时写一条轻量通知（可复用已有 SSE 网关，channel 级广播给该用户）；前端 `HistorySidebar` 的会话条目加一个「已完成」圆点 + 顶部一条 toast。前端 S（约 100 行），后端 S–M。

**风险**：多端登录时重复通知。

---

## 11. `file_gate` 的 haiku 判定与 `await_entries_ready` 并发 ｜ 收益 有附件轮省约 1.3s / 成本 S

核对后：题干设想的"逐文件就绪即放行"**已经实现**（`file_gate_node.py` 做的是逐文件三分 usable/pending/failed，注释写死"逐文件判，不看整批裁决"）。

**剩下的真缺口**：haiku 判定（1,272ms）**串在等待之前**——先问"需不需要文件"，得到 need=True 才开始 `await_entries_ready`。改为进入节点即 `asyncio.create_task(await_entries_ready(entry_ids))` 与 haiku 判定并发；need=False 则 cancel 等待（向量化本来就在后台继续，语义不变）。

⚠️ 落地前需确认 `ingest_service.await_entries_ready` 被 cancel 时不会中断后台入库。

---

## 12. 免责译文入代码 ｜ 收益 非英文轮省 1.8s 尾部延迟 + 一次 haiku 调用 / 成本 S

**现状**（比直觉多一层）：`disclaimer_node.py` 已有进程内缓存 `_translation_cache: dict[tuple[str, str], str]`，key 是 **`(语言, 英文原文)`** —— 这个 key 设计已自带失效：**改了英文文案，key 就变了，旧译文不会被命中，无需手动清空**。

**它的真实缺陷**：进程内，每次重启/发版全空，每个语言要重新翻一次。

**关键是最后一行**：译文入代码不是替代方案，是**在现有机制前面加一层常量表**。命中常量 → 零成本；未命中 → 走现在的逻辑，两套共存。

**预置范围**：常量表先补系统用户常用语言（3~4 种）的三段译文即可，未预置的语言自动回退到运行时翻译。

---
下面几项修改不建议，只留作记录
---

## 13. `ContextEditingMiddleware` 裁剪工具结果 ｜ 收益 M / 成本 S ｜ ⚠️ 与 §9 重叠，待定

`langchain 1.2.18` **自带** `ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger, keep, clear_at_least, clear_tool_inputs, exclude_tools, placeholder)])`，等价于 Anthropic 服务端的 `clear_tool_uses_20250919`，落点就是 `retrieval_agent.py` 已有的 `middleware=[mw]` 加一项。Anthropic 官方 cookbook 实测：无管理峰值 335,279 token → 仅开清除 **173,137 token（-48%）**。

**阻塞点已排除**：调研中两个研究员都要求先确认"工具步骤卡片是不是从 messages 回读渲染的"。实测——卡片是**直播态专有**（`messageReducer.ts` 的 `steps` 由 `tool_step` 事件流式累积），历史回放的 `parseChartFences.ts` **只解析 ```chart 与 ```disclaimer 两种围栏**，卡片根本不从消息回读。所以裁剪模型侧的工具结果**不影响卡片**。

### ⚠️ 但它在我们这里的适用性存疑（合并时发现，待拍板）

1. **设计意图对我们不成立**：它是为"上下文快满了"设计的。实测单次调用最大输入 **32,922 token**，Sonnet-5 窗口 200,000——我们在 **16%** 的位置。默认 `trigger=100,000` **永不触发**，要降到 ~45k 才有用。
2. **能省的只有 9.4%**：实测全部 retrieve 输入 6,879,397 token，假设零累积为 6,229,774，**累积重发仅占 9.4%**；且高度集中在尾部（最贵一轮单轮输入 424,997 token，占累积部分的三分之一）。中位数轮次能省的是个位数百分比。
3. **与 §5 冲突**：清理会**改写 message 前缀 → `cache_conversation` 断点失效**，下一跳重付 1.25× 写入（Anthropic 官方："Tool result clearing invalidates cached prompt prefixes"）。在 2.70 次调用/轮的规模上，缓存击穿很可能比省下的 token 更贵。
4. **尾部根因已有更直接的解法**：§9 的源头截断直接命中"单个工具返回太大"这个根因，且**不破坏缓存**。

→ **待拍板**：是并进 §9（源头截断），还是保留为 §5 收益落袋后的二期项。

---

## 14. 数字级确定性溯源 ｜ ⚠️ 优先级后置

> **为什么后置**：它解决的问题是**答案里的数字不可验证、出错不可定位**——取错公司/期间/口径、模型编数、模型自己算错，这三类**全是静默错误**（格式正确、看起来专业、用户发现不了）。结构上这个缺口真实存在。
>
> **但问题规模未知**：没人报过数字错，`ungrounded_number_count` 探针也还不存在。在不知道问题有多大的情况下先付 400–600 行前端，不划算。
>
> **正确顺序**：先做下面 16.1 的**数值接地探针**（同一套机制的便宜一半：成本 S、单文件、前端零改动、**可对历史 71 条消息离线回算拿到基线**）。拿到 ungrounded 占比后——接近 0 则二期继续缓；有明显占比则本条变刚需且手里已有具体案例。

**核心判断：数字不要走模型生成的 citation。** Anthropic 的 `search_result` content block 适合**文本片段**引用（最小可引用单位是一个 text block），而我们的数字来自 Java 网关的结构化取数，不是文档片段。

**① 不需要给每个数值加 `ref` 字段——坐标已经在返回结构里。** 实测 `get_financials` 的返回本身就是四层嵌套：

```json
{"companies": [{"company_id": "d5a26a9a-…", "currency": "USD",
  "metrics": {"Monthly Runway": {"2026-02": {"Actuals": "N/A (…)"}}}}]}
```

即 `company_id → metric → month → data_type → value`，**JSON 路径本身就唯一标识了每个数值**。

**② 谁把正文里的数字对应到坐标**——核心论点是「模型全程不参与引用生成，所以引用不可能被编造」，所以**必须是 Python 按值匹配**（抽出正文数字，去工具返回的数值集合里找精确匹配），而**不能**让模型在正文里写 `[[v:FIN:…]]` 标记（那样模型就在生成引用，就能标错，论点直接崩塌）。

**呈现形态**（眼动实验 PMC13513764，N=23）：卡片列表首次注视最快 **0.96s** vs 裸链接 15.65s（p<0.001），但**主观最偏好的是行内组件**，作者结论"注意力 ≠ 偏好"；四版式在信任度评分上**无显著差异**（p>0.49）。→ **行内轻标记 + 点开展开卡片**。

**效果证据**（UIST'26 Attribution Gradients，arXiv 2510.00361，N=20 组内）：首次抵达来源快 48s、打开来源数 3.5×、修订质量 3.65 vs 2.35（p<0.01），且**该组 0 引入错误、对照组 5 个**。**反面**：arXiv 2604.15326 各平台引用点击率 <25%、满意度仍 >4.0。

**分两期**：一期（成本 S）工具卡不折叠 + 卡内显示参数与返回摘要；二期（成本 L）数字级绑定。

⚠️ **标错比不标更糟**（会制造虚假可信）。只标直接取自工具返回的数，LLM 二次计算的（增长率等）不标或标为"基于 A、B 计算"。
⚠️ 来源等级要区分：`fi_*` 实数、benchmark 同行组数据、预测数据三类混在一句话里不区分是真实的误导风险。

### 14.1 程序化数值接地校验（本条的定价依据）

从已收集的工具结果抽数值集合，校验答案中数值（±0.5% 容差），**只记不拦**，产出 `ungrounded_number_count`。成本 S、单文件、前端零改动，且**可对历史消息离线回算拿到基线**。

**为什么不拦截**：提示词**明确允许**模型做比较/排序/计数/简单聚合，也允许标注过的 AI 估算值；硬拦截会误杀这些合法输出（FinGround 报告对冲性措辞贡献了 52% 的误报）。

**为什么仍有价值**：它一次性给出**在没有评测集的前提下、可逐日观测的准确率代理指标**；纯离线计算，不加任何 LLM 跳、不影响 TTFT。

⚠️ 不要让这个指标变成 KPI——它是漂移探针，不是准确率的真值。

---

## 15. 会话锚点程序化注入 ｜ ⚠️ 降为条件项

`get_chat_history` 实测 **0 调用**，业界共识与之一致：**低显著性的按需回看工具不会被调用**——ReAct 里模型只在"明显缺信息"时才调工具，而**指代缺失它感知不到，它会直接猜**。

**落地**：graph state 里维护一个**程序化**（非 LLM 抽取）的 `session_anchor`：当前 company_id/name、period、currency、口径、上一次成功工具调用的参数。**由工具调用参数回填**，渲染成 10 行以内注入到**消息末尾**（靠近最后一个缓存断点，本来就是每轮变的部分，不击穿前缀），同时喂给 `rewrite_node`。

⚠️ **只从已成功执行的工具参数回填，不从用户自然语言猜**——锚点自己写错会污染每一轮。
⚠️ 锚点必须在答案里**可被用户看到并纠正**（正好由 §3 的条件栏承担），否则沉默的错锚比失锚更糟。

### ⚠️ 前提修正：四个信号都不支持

| 信号 | 实测 |
|---|---|
| 线程深度 | 25 个线程里 **80% ≤3 轮**，只有 2 个超过 5 轮（即历史窗口边界） |
| 唯一的深度会话（12 轮 / 2026-08-12 / 公司端） | **零指代**。12 个问题全自包含，且全是方法论问题——明显是 playbook 检索的测试会话 |
| 指代类关键词命中 | 68 条 user 消息里 **1 条（1.5%）** |
| `get_chat_history` 调用 | **0 次** |

**但这既不能证实也不能否证**：线程深度与提问方式都是**用户行为**，开发库里的"用户"就是开发者。

→ **前提是生产数据显示指代类提问确实存在**，在那之前做它是为一个未经证实的问题建设施。

```sql
SELECT count(*) AS total,
       count(*) FILTER (WHERE content ~* '之前|上面|刚才|前面那条|上一条|translate|summari[sz]e') AS referential
FROM ai_chatbot_message WHERE role='user';

SELECT turns, count(*) AS threads FROM (
  SELECT thread_id, count(*) AS turns FROM ai_chatbot_message WHERE role='user' GROUP BY thread_id
) s GROUP BY turns ORDER BY turns;
```

---

## 16. 孤儿流终结 ｜ ⚠️ 先观测、不要先修

调研初稿写的是「修每次滚动发布都会命中的用户可见挂死」，**这个说法夸大了**。要产生孤儿流必须同时满足三个条件：

1. 有流**正在生成**（进程在往 Redis 写帧）；
2. 进程**非优雅地**死掉——优雅关闭时 asyncio 会 cancel 任务，`finally` 照常执行、落 partial、终结帧照发。只有 SIGKILL / OOM / 宽限期到点被硬杀才会留下没有终结帧的残帧；
3. 且**有客户端正订阅着**这条流。

三者叠加，概率不高。

⚠️ **「实测 RUNNING 2/94 ≈ 2%」不能作为证据**——开发库里的重启是开发者自己按 Ctrl+C，属于"用户行为污染"那一类数据。

**唯一不能排除的情形**：轮次平均 39.4s、最长 204.6s，若容器 `stopGracePeriod` 是常见的 30s，则发布时**多数在跑的轮次都会被硬杀**。但部署配置本次**未核实**。

**结论：先观测，达到阈值再修。**

```sql
SELECT count(*) FROM ai_trace
WHERE name = 'chatbot.chat' AND status = 'RUNNING'
  AND started_at < now() - interval '10 minutes';
```

真要修时的方案仍然成立：`sse:alive:{id}` 短 TTL 生产者心跳（按秒节流续期）+ `/subscribe` 在「无新帧 + alive 消失 + 无终结帧」时以 error 关流。

---

## 17. 其余小项（视前面效果再评估）

- `get_benchmark_data` schema 按 Trace-Free+ 五模式瘦身（8,213 字符，占全部工具 schema 的 31%）——**先只删"返回描述"类冗余，观察一周**。⚠️ 它现在承载了"时间窗相同才能并一次""别为并成一次而撑大区间会超时"这类**踩过坑的约束**，属模式①②③的一律保留
- **尾部硬约束重述中间件**：在第一次工具返回之后的每次模型调用前，向消息尾部追加一段 ≤15 行的「本轮作答硬约束」清单（利用近因效应）。⚠️ 用常量引用而非手抄，避免变成第 5 处平行维护
- **指标名跨源一致性契约测试**：指标名现在 4 处平行维护（工具 docstring / 取数提示词 / 重写提示词 / benchmark 枚举），无一致性校验
- **提示词前缀稳定性快照测试**：对"渲染后的 system prompt + 全部工具 schema"取 hash 存进测试，变更即失败——把"击穿缓存"从一次无声的事故变成一次被审阅的动作
- **`_tools_for_turn` 的 playbook 分支清理**：playbook 一直放开后该分支已无意义，顺带删掉（工具集变成完全静态）
- kb / combo 两轨砍除 —— **已拍板：代码先不动，等合适时机再清理**

---

## 参考来源

**官方文档（最高可信，均已读正文）**
1. [Anthropic — Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — 4 断点上限；失效层级 `tools → system → messages`，改任一字节即整段失效；最小可缓存长度 Sonnet 5 = 1,024 / Opus 5 = 512 / **Haiku 4.5 = 4,096**；5m/1h TTL（**从请求开始计时**）；1.25x/2.0x/0.1x 计价
2. [Anthropic — Prompting best practices / Long context](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — *"Put longform data at the top… above your query, instructions, and examples"*；*"Queries at the end can improve response quality by up to 30 percent"*
3. [Anthropic — Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)（2025-09-11）— **Claude Code 默认工具返回上限 25,000 token**；`response_format` concise/detailed（Slack 206→72 token）；带引导的截断；返回语义化字段而非 UUID
4. [Anthropic — Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing) + 官方 cookbook — `clear_tool_uses_20250919`；峰值 335,279→173,137 token（−48%）；"Tool result clearing **invalidates cached prompt prefixes**"
5. [Anthropic — Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) — top-20 失败率 5.7%/3.7%/2.9%/1.9%；rerank 延迟权衡；**<20 万 token 不必上 RAG**
6. [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — orchestrator-worker、+90.2%、agent 4× / multi-agent 15× token、effort scaling 规则、**不适用场景**
7. [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
8. [OpenRouter — Prompt caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching) — Anthropic 系需显式 `cache_control`；`prompt_tokens_details.{cached_tokens, cache_write_tokens, cache_discount}`；**`session_id` / `x-session-id` 粘性路由**（≤256 字符、任意成功请求即生效、10 分钟无活动过期、粘住的端点不可用时自动 fallback）
   ⚠️ **查阅提示**：粘性路由**只写在本页，provider-routing 页完全没提**。只看后者会得出"OpenRouter 不支持会话亲和"的错误结论
9. [OpenRouter — Provider routing](https://openrouter.ai/docs/features/provider-routing) — 默认按价格负载均衡；`provider.order` / `sort` / `allow_fallbacks`
10. OpenRouter 实时 API `/models/anthropic/claude-sonnet-5/endpoints`（实查 2026-09-16/17）— sonnet-5 **10 个**上游端点 / opus-5 **11 个**；全部 `supports_implicit_caching=false`
11. [OpenAI Agents SDK — Guardrails](https://openai.github.io/openai-agents-python/guardrails/) — input guardrail 默认并行、阻塞模式的真实用途
12. [OpenAI Cookbook — Deep Research API with the Agents SDK](https://developers.openai.com/cookbook/) — Triage→Clarifier→Instruction Builder 管线
13. [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) `deep_researcher.py` — `clarify_with_user` / `allow_clarification` / `Command(goto=END)`（一手源码）
14. [Manus — Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — KV-cache 命中率是最重要单一指标、10× 价差、append-only、**工具不要动态增删**、recitation
15. [LangSmith — Double texting](https://docs.langchain.com/langsmith/double-texting) — *"It is not available in the LangGraph open source framework"*

**同行评议 / 预印本（含量化）**
16. Huang et al., *LLMs Cannot Self-Correct Reasoning Yet*, **ICLR 2024**, arXiv:2310.01798 — 内在自我纠错改对 7.6% / 改错 8.8%
17. CUI'25, *Mitigating Response Delays…*, arXiv:2507.22352 — **N=54**，自然填充 p<0.01 / p<0.0001，**旋转图标不显著**
18. arXiv:2602.15569, *"What Are You Doing?"* — **N=45**，中间反馈显著提升感知速度/信任/UX、降低任务负荷
19. UIST'26, *Attribution Gradients*, arXiv:2510.00361 — **N=20**，来源打开 3.5×、修订质量 3.65 vs 2.35、**0 引入错误 vs 对照组 5 个**
20. PMC13513764 眼动实验 — **N=23**，卡片首次注视 0.96s vs 裸链接 15.65s（p<0.001）、偏好行内、信任无显著差异（p>0.49）
21. arXiv:2605.25284, *Knowing but Not Showing* — 识别歧义 60–80%，**真实作答中仅 0–5% 主动澄清，带检索上下文后近 0%**
22. arXiv:2604.15326 — 各平台引用点击率 <25%、满意度仍 >4.0
23. arXiv:2605.17830 — 8 种记忆架构纵向安全评测，良性使用下记忆越长违规率越高（0.30–0.50 vs 0.10–0.20）
24. [FinGround](https://arxiv.org/html/2604.23588)（arXiv 2604.23588）— 通用检测器**漏掉 43% 计算类错误**；对冲措辞致 52% 误报；±0.5% 算术容差
25. [Trace-Free+：Learning to Rewrite Tool Descriptions](https://arxiv.org/html/2602.20426v2)（arXiv 2602.20426v2，Intuit AI Research，含 Claude Sonnet 4.5）— 五类接口模式；多步成功率 **33.5% → 44.6%**
26. [Chroma — Context Rot](https://www.trychroma.com/research/context-rot)（2025-07-14，18 个模型含 Claude 4）— 性能随输入长度单调下降；**Claude 系倾向保守弃答**
27. [The Complexity Trap: Simple Observation Masking…](https://arxiv.org/abs/2508.21433)（NeurIPS'25 workshop）— 观测遮蔽成本减半且 solve rate 匹配 LLM 摘要
28. [LLM as Entity Disambiguator](https://aclanthology.org/2025.acl-short.25.pdf)（ACL 2025 short）— 索引选择 + 0 弃权；无需微调达 SOTA
29. [RAGO](https://arxiv.org/abs/2503.14649) — 阶段编排值 **TTFT −55%**
30. [Ably — Resume tokens and last-event IDs for LLM streaming](https://ably.com/blog/resume-tokens-last-event-id-llm-streaming-reconnection)（2026-03-12）— 四类失败模式；成本估算

**弱证据 / 仅作形态参考（已标注，未用于支撑量化结论）**
31. NN/g《Less Chat, More Answer》（n=9 定性）、《5 Dimensions of Site-Specific AI Chatbots》
32. 金融分析产品（Daloopa 等）的 cell-level citation 形态 — 产品观察

**本地版本核对（最高可信，直接读 `.venv` 与 `uv.lock`）**
- langchain **1.2.18** / langchain-core **1.4.8** / langgraph **1.1.10** / langchain-anthropic **1.4.7** / langgraph-checkpoint 2.1.2（**无** checkpoint-postgres）
- ⚠️ **官网文档是 1.3.x 线**，多处 API 不通用（如 `ToolErrorMiddleware` 需 ≥1.3.14，本地不存在）
- 本地实际存在的 middleware：`tool_call_limit` / `model_call_limit` / `context_editing` / `human_in_the_loop` / `summarization` / `todo` / `pii` / `model_fallback` / `tool_selection` / `tool_retry`
- 前端：`messageReducer.ts`（286 行）/ `ToolStepsCard.tsx`（62 行）/ `parseChartFences.ts`（77 行，**历史回放只认 ```chart 与 ```disclaimer 两种围栏**）
