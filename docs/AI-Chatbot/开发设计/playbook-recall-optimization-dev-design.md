# Playbook 召回优化开发设计（多向量问法 + 形态对齐 + 低置信短路）

> 关联文档：
> - 现行实现（先读）：[./playbook-chatbot-integration-dev-design.md](./playbook-chatbot-integration-dev-design.md)（v2，2026-07-29；§3.1 profile 配方、§5 检索链路、§13 后续）
> - 管理页设计：[../../superpowers/specs/2026-08-03-playbook-manage-design.md](../../superpowers/specs/2026-08-03-playbook-manage-design.md)
> - 台账（本文多处引用）：`../../../python/CIOaas-python/docs/待优化项.md` 第 20 / 21 / 41 / 42 条
>
> 阶段：⑤ 开发设计 ｜ 版本：v1 ｜ 日期：2026-08-10 ｜ 状态：**待评审** ｜ 端：Python（CIOaas-python）
>
> 本文只讲**优化**，不重述现状。所有"现状如何"一律指向 v2 设计文档，不复制。

---

## 1. 现状基线（散落各处的实测数字，汇总一处）

后面每一项优化都拿这张表当判断依据。**没有新测量，全部来自既有留档。**

| 指标 | 实测值 | 出处 / 口径 |
|---|---|---|
| 路由准确率 r@1 | **89.5%**（282/315） | 台账 §21，2026-07-31，v1 sonnet5，315 题，`route()` 口径。**是上界**——questions 原文在被检索文本里 |
| r@3 / r@5 / MRR | 96.5% / 99.4% / 0.934 | 同上 |
| 完全召不回 | 2 条 | 同上 |
| 图扩展的必要性 | **56.2%** 的 `depends_on` 前置项纯向量 top-5 召不到 | v2 §2 |
| 数据规模 | 63 节点 / 339 chunk（profile 63 + body 276） | v2 §11 步骤 6，四次 ingest 一致 |
| **questions 密度** | **正好 5.0 条/本**（315 / 63） | 2026-08-10 查库（version=2）。⚠️ v2 §3.1 写的"平均 2.5 条"是**源站改版前**（157/64）的值，已过时 |
| **profile 长度** | 平均 **450** 字符（样例 486 字符 / 93 token / 1536 维） | 同上。v2 §3.1 写的"约 275 字符"同样是改版前的值 |
| body 长度 | 平均 **1142** 字符/段（276 段，切分口径 1400/150） | 同上 |
| profile 精扫 | **0.099 ms** | v2 §4.3 |
| route 全流程 | **~7 ms/次**（315 次 2.2s） | 台账 §21 |
| query embedding | **~55 ms/次**（315 条 17.3s） | 台账 §21 |
| 单轮 context 峰值 | **52769 字符 ≈ 13000 token**（模型自主调 4 次） | 台账 §41 |
| 概念性主题得分 | 全场最高仅 0.442；`board-of-directors` 第 9（0.342） | 台账 §42 |
| 同一问题换问句形式 | `board-of-directors` 升到第 2（0.367） | 台账 §42 |
| ingest 成本 / 耗时 | opus5 $0.21 / 143s（关系推断 76s + 63 次 embedding 64s） | v2 §7.1.1、管理页设计 §2.2 |
| 全量重嵌成本 | 387 chunk ≈ $0.003 | v2 §13 |

**从这张表直接读出三个结论**，它们决定了本文的取舍：

1. **向量检索不是瓶颈**：0.099 ms vs 55 ms 的 embedding 往返，差 550 倍。任何针对索引/量化/向量库的优化都是负收益（§9）。
2. **成本不在 embedding**：单次 $0.00002，ingest 一年跑不到 10 次。成本在**灌进对话的 13k token**。
3. **准确率的空间在 profile 配方与召回形态**，不在检索引擎。

---

## 2. ⚠️ 前提：先把回归基线拿回来

> ✅ **已完成（2026-08-10）**。台账 §20 原记「2026-07-31 决策不做」已推翻并更新——本文 §5 / §6 / §7
> 三项恰好全部落在它的防护范围内，盲改的风险高于重写成本。

**首跑结果逐位复现台账 §21 的留档基线**，说明脚本口径与当初那次测量一致：

| 指标 | 本次（version=2，315 题） | 台账 §21 留档（2026-07-31，v1） |
|---|---|---|
| r@1 | **89.5%**（282/315） | 89.5%（282/315） |
| r@3 / r@5 | 96.5%（304） / 99.4%（313） | 96.5% / 99.4% |
| MRR@5 | **0.934** | 0.934 |
| 完全召不回 | 2 条 | 2 条 |
| 耗时 | embedding 18.5s（并发 8）/ route 2.7s | 17.3s / 2.2s |

基线快照：`scripts/data/playbook/baseline-v2.json`（含 `rankByQuestion` 逐题排名，供 `--baseline` 定位退化题）。

两条召不回都是金标侧问题、不是检索故障：`saas-metrics` ←「What's the magic number for sales
efficiency?」（top1 相似度 0.673，命中的是 sales-efficiency 系手册，检索反而更合理）；
`sales-funnel-creation` ←「What bottlenecks matter most to focus on?」（问句本身过于笼统，top1 仅 0.387）。

实现要点（对齐台账 §21 的五条）：

```
scripts/eval_playbook_recall.py    ← 已实现（2026-08-10）
  金标取自 ai_rag_playbook.list_by_version(version) 的 questions
    ⚠️ 不是 scripts/data/playbook/playbooks_data.json —— 那是预研快照
       （64 节点 / 157 questions），与当前源站版本不同源，用它会把"源站改版"
       混进"配方改动"的差值里
  → PlaybookRepository 取 ACTIVE（或 --version）版本的 entry_ids
  → 并发 embed_query（网络往返约 55ms/次）→ 单 session 顺序调 processor.route(top_k=5)
  → 输出 r@1 / r@3 / r@5 / MRR@5 / 召不回明细
  → --save 存快照，--baseline 比差值并**列出退化到第几名的具体题目**
不进 CI（需 API key + DB）
```

⚠️ 每次运行向 `ai_llm_call_log` 写 N 行 `call_purpose='rag_query'`（`embed_query` 的固定值，
与线上查询在 purpose 上无法区分）。脚本报告末尾打印运行时间窗，需从成本统计剔除时按该时间窗过滤。

### ⏳ 仍待做：另建一套无泄漏金标

v2 §13 已指出必要性：现有 315 题就是 profile 里那批 questions 本身，是**上界**（让它找自己）。
优化项 D（HyPE 扩写问法）会**放大**这个泄漏面，届时旧金标的相对可比性也会失效。

改法：用 `playbooks_bodies.json` 的**正文**让 haiku 出题（正文不在 profile 被检索文本内），
脚本加 `--golden <file>` 支持外部金标文件。两套并用——旧套测相对变化（与 89.5% 同口径可比），
新套测真实水平。

> **这一步是优化项 D 的硬前提**（§6 风险 3）；§5 / §7 用现有金标即可验收。

---

## 3. 优化项 A：低置信度显式短路 🟢 无需基线

### 问题

台账 §41 记录：一次提问模型自主调 `search_playbooks` **4 次**（换 4 种检索词），累计 52769 字符 ≈ 13000 token，其中第 2 次的结果基本没被答案使用。触发条件是 §42 说的**相似度普遍低（0.32–0.44）时模型不满意就换措辞重试**。

而 §42 同时确认：那次库里**确实没有**"董事会月报"这个主题（全场最高 0.442），属**内容覆盖缺口，不是检索故障**。

现在的行为是：照常返回 0.34 分的手册摘录 → 模型要么拿它硬答，要么换措辞再来一次。两种都是坏结果。

### 改法

`playbook_service.search()` 在阶段 1 之后判断 top-1 相似度：

```
top1_similarity < COVERAGE_THRESHOLD（建议 0.45）
  → 不走阶段 2 / 阶段 3，不返回任何摘录
  → 返回 {ok: true, coverage: "low", topSimilarity: 0.34,
          note: "库中没有覆盖该主题的方法论手册。请基于通用知识回答，
                 不要换检索词重试。"}
```

阈值 0.45 的来历：§42 那次"确实没覆盖"的全场最高分是 0.442；而正常命中的例子（`churn-identification-process` 0.682）远在其上。**上线后按台账 §21 的方式抽一批真实 query 校准一次**，不要当固定常量。

### 收益

| 维度 | 效果 |
|---|---|
| 成本 | 那次四连问的第 2/3/4 次被掐掉，单轮 52769 → ~13000 字符 |
| 准确率 | 模型不再拿 0.34 的手册硬答——这正是 v2 §7.1 那个 Sales Efficiency Ratio 反向定义错误的同类温床 |
| 可观测 | `coverage: low` 落日志后，**可以直接统计内容覆盖缺口**，作为"该补哪些手册"的输入 |

### 为什么不需要基线

它改的是"**没有好结果时的行为**"，不动排序口径与 profile 配方。回归风险只在阈值定太高（把正常命中掐掉）——用 315 题金标跑一遍看有多少条 top-1 分数低于阈值即可确认，不需要完整评测脚本。

---

## 4. 优化项 B：阶段 2 与阶段 3 并发 🟢 无需基线

### 问题

v2 §5 的链路是阶段 1 →（串行）阶段 2 →（串行）阶段 3。但看依赖关系：

| 阶段 | 库 | 输入 | 依赖谁 |
|---|---|---|---|
| 2 映射 + 图扩展 | 业务库 | seed 的 entry_id | **只依赖阶段 1** |
| 3 取正文 | 向量库 | seed 的 entry_id | **只依赖阶段 1** |

**两者之间没有依赖**——阶段 3 取的是 seed 自己的 body，扩展节点本来就不取正文（v2 §5 明写"扩展节点只给简介"）。串行是实现顺序的历史产物，不是数据依赖。

### 改法

`playbook_service.search()` 里把两个 `await` 合成一个 `asyncio.gather`。两者已各自在 `asyncio.to_thread` 里（v2 §14.3 的事件循环阻塞修正），并发是安全的；注意它们用**两个不同的 session**（业务库 / 向量库），本来就不共享事务。

### 收益

省一次串行往返（递归 CTE 实测在毫秒级，但跨库时网络往返是实打实的）。改动约 10 行，无口径变化。

---

## 5. 优化项 C：检索词形态与索引形态对齐 🟡 需基线

### 问题：两处口径互相矛盾

| 位置 | 现状 |
|---|---|
| 索引侧（`PROFILE_TEMPLATE`） | 嵌的是 **`Key questions:` 问句**，v2 §3.1 明确说这是把匹配变成 **query↔query** 的核心技巧 |
| 查询侧（`search_playbooks` docstring） | 要求"**陈述式关键词**、不要整句照抄"（v2 §5，与 `search_knowledge_base` 同口径） |

索引侧存的是问句，却要求模型给陈述式短语——**自己把 query↔query 打回成 query↔陈述式**。

台账 §42 的实测正好是这条的证据：同一个意思，`board-of-directors` 在陈述式检索词下排第 9（0.342），换成问句 `what should the board see every month` 升到第 2（0.367）。§42 把差异归因于"模型加了原问题没有的词"，那是一部分；**另一部分就是形态**。

### 改法（两选一，推荐 B）

**A. 改 docstring**：把"陈述式关键词"改成"一句用户口吻的问句"。一行改动。代价是与 `search_knowledge_base` 口径分叉——**这个分叉是对的**（两个工具的索引形态本就不同），但要在 docstring 里写明理由，否则下一个人会来"统一"掉。

**B. 双检索词（推荐）**：工具签名从 `query: str` 改为接受两个字段：

```
question: str   # 用户口吻的问句，如 "what should the board see every month"
keywords: str   # 术语短语，如 "board reporting monthly metrics"（可空）
```

各 embed 一次，在 `search_profile` 里对同一 entry 取 `MIN(distance)`（两路谁近算谁）。

- 成本：多一次 embedding（+55 ms、+$0.00002/次）
- 好处：不赌哪种形态更好，两种都覆盖；术语型问题（"ARR schedule 怎么做"）走 keywords 路，概念型问题走 question 路
- ⚠️ 与优化项 D（HyPE）叠加后收益更大——索引侧问句密度提高，question 路的命中面同步扩大

### 验收

315 题金标（问句形式）跑 A/B/现状三组对照。**注意金标本身是问句改写来的**，会天然偏向问句路——所以必须同时用 §2 那套"由正文出题"的新金标交叉验证，否则测出来的是自证。

---

## 6. 优化项 D：问法多向量化（HyPE）🟡 需基线 ｜ **本文的主项**

### 问题：拼接 = 求平均，而 v2 §13 的方案会放大它

现在一条 profile = `title (category). description Key questions: q1 … q5` 拼成平均 450 字符，过**一次** embedding。这条向量表达的是四部分的**加权平均**。

v2 §13 计划"用 LLM 给每条 playbook 扩写到 8–10 条问法后**重嵌 profile**"，并判断"成本极低、见效可能最直接"。**成本判断是对的，但机制上有风险**：

> questions 从**现有 5 条**扩到 8~10 条塞进**同一条文本**后，每条问法在向量里的权重从约 1/5 降到约 1/10，还要与 title + description 抢表达。覆盖的问法变多，但每条匹配得更弱。**净效果可正可负，且正好是"5–10% 的退化人工测不出来"那一档。**

⚠️ 源站改版后 questions 已经从 2.5 条涨到 **5.0 条/本**（§1），这件事对本项的判断有两个方向的影响：
一是"扩写"的增量空间缩小了（2.5→10 是 4 倍，5→10 只有 2 倍）；二是**稀释已经在发生** ——
450 字符里挤着 5 条问法求平均，v2 §3.1 当初"2.5 条覆盖面窄"的诊断现在应换成"5 条互相稀释"。
所以本项的重点从"扩写更多问法"转向**先把现有 5 条拆成独立向量**，扩写是第二步。

### GitHub 上的成熟做法：HyPE（每问一向量）

`NirDiamant/RAG_Techniques` 有独立一篇 [HyPE (Hypothetical Prompt Embeddings)](https://github.com/NirDiamant/RAG_Techniques/blob/main/all_rag_techniques/HyPE_Hypothetical_Prompt_Embeddings.ipynb)：索引期为每个 chunk 生成多条假设性问题，**每条问题各自成一个向量、都指向同一个宿主 chunk**，检索时命中问题向量后回指宿主。它与 v2 §3.1 的洞察同源，区别只在**不做平均**。

同一思路的其他实现：
- `blackhaiyu-sudo/specrag`：`query_hints` 独立成 `agent_hint_bundle` 向量，另有 `feedback_hint` 承接用户反馈沉淀的新问法
- `castorini/docTTTTTquery`（doc2query）：给文档预生成查询以扩充检索面
- 微软 Nissist（arXiv 2402.17531）：节点用 `intent` 而非正文参与匹配，做 intent↔intent

### 改法（不动表结构、不动共用代码）

`chunk_kind` 是 rag 的跨业务约定（v2 决策 D5），**加第三个取值**即可：

| 文件 | 改动 |
|---|---|
| `playbook/models.py` | 加 `CHUNK_KIND_QUESTION = "question"` |
| `playbook/playbook_processor.py` | 新增 `inject_questions(questions: list[str], seq_start: int)`，每条问法产出一个 `ChunkResult`（`chunk_kind='question'`）。⚠️ **profile 文本原样保留**（仍含现有 5 条原问法）——这样出问题可以只停查询侧过滤条件回滚，不用重灌数据 |
| `playbook/repository.py` | `search_profile` 过滤从 `= 'profile'` 改为 `IN ('profile','question')`，并在 SQL 里按 `entry_id` 分组取 `MIN(distance)`（**max-pool 回节点**）。阶段 1 对外契约（返回 top_k 个互不相同的 playbook）**一个字不变** |
| `playbook_service._write_version` | 每节点多写 N 条 chunk；`node_count` 语义不变（仍是节点数，不是 chunk 数） |
| `activate` 完整性校验 | `count_entries_with_profile` **保持只看 profile**——问法可以缺，profile 不能缺 |
| 扩写问法 | ingest 期一次 LLM 调用（haiku，批量），产物写进 `ai_rag_playbook.questions`，与 profile 文本里那 5 条**同源不同用**：短列表进 profile 文本，全量进 question chunk |

### `RouteHit.chunk_id` 的语义变化（顺带的好处）

命中问法时 `chunk_id` 指向那条 question chunk，`hit_count` 累加到它身上。于是：

> **哪条问法真的被用户命中过，直接查 `hit_count` 就知道** —— 这是后续删减/继续扩写问法的唯一客观依据，也是 specrag `feedback_hint` 那套反馈闭环的起点。

### 成本

| 项 | 量 |
|---|---|
| 扩写 LLM | 63 节点一次批量调用（haiku）≈ $0.05 |
| embedding | 63 × 8 ≈ 504 条 ≈ $0.004 |
| 行数 | 339 → 843（向量库 +约 3 MB / 版本） |
| 阶段 1 精扫 | 63 行 → 约 570 行，**0.099 ms → 约 0.9 ms**（相对 55 ms embedding 可忽略） |
| ingest 耗时 | +504 次 embedding，按现有 63 次 64s 推算约 +8 分钟 ⚠️ 见风险 |

### ⚠️ 风险与缓解

1. **ingest 耗时翻几倍**（143s → 约 10 分钟）。管理页设计已把 ingest 改异步 + 轮询（决策 5），机制上撑得住，但前端进度文案（§4 的时序表）要同步更新。**embedding 应批量提交而非逐条**，能压回 2~3 分钟。
2. **问法质量差会引入噪声**：LLM 可能生成与手册无关或彼此高度重复的问法。缓解：先只对 §42 记录的那批**概念性/总论型手册**（约 20 本）做，跑一次对照再决定是否铺开。
3. **金标泄漏面扩大**（v2 §13 已预警）：扩写后的问法若来自原 questions，泄漏更重。所以 §2 那套"由正文出题"的新金标是**本项的硬前提**，不是可选项。

---

## 7. 优化项 E：路由后加一层重排 🟡 需基线

### 问题

台账 §42：概念性/总论型手册在词面上竞争不过术语密集手册——问"董事会每月一页数据"，前 6 名被 kpi / sales-metrics / support-metrics / saas-metrics / sales-efficiency 各种 metrics 手册挤满。这是 bi-encoder 的固有偏置（对术语共现敏感），**HyPE 能缓解但消不掉**。

### 两个方案

**E1（先试）：Cohere rerank，top-10 → top-3**
`llm_db_router.rerank`（Cohere）已可用、playbook 链路未接（v2 §13）。改动：`route(top_k=10)` → rerank → 取 3 个 seed。延迟约 +100 ms，成本每次约 $0.001。

**E2（备选）：LLM 选，Nissist 模式**
你们的库只有 63 本手册、每条 profile 平均 450 字符——**整个目录约 5.4k token，小到可以直接塞进 prompt**。这是"手册数量少"带来的、大多数 RAG 系统没有的机会。

Nissist 的做法正是"先用传统方法粗召回多个节点，再用 LLM 选最相关的"。对应到这里：向量 top-10（约 1.2k token）交给 haiku 选 3 并给理由，延迟 +0.3~0.6 s、成本约 $0.001/次。

**建议先做 E1**：延迟只有 E2 的 1/5，且不引入新的 prompt 需要维护。E1 量化后不达预期再评估 E2。

⚠️ 与优化项 A 的联动：短路发生在阶段 1 之后、rerank 之前，低置信度 query 不进 rerank，所以不会为"库里没有"的问题额外付钱。

---

## 8. 优化项 F：跨调用 pid 去重 🟢 无需基线

台账 §41 已正确指出**不能靠降 top_k 解决**（排第 3 的 `kpi-dashboard-creation` 恰是唯一带 `inputs` 的那本，降到 2 就丢了核心价值），该控的是**累计量**。

### 改法

per-turn 状态放 LangGraph `ChatState` 加一个 `playbook_seen_pids: set[str]`，工具执行层读写：

```
第 2 次及以后命中同一 pid
  → 不重复灌 body 摘录（约 4200 字符）
  → 只回一行 "已在上文提供：cash-flow-forecast（Executive）"
```

扩展节点的简介同理去重。按 §41 那次实测的重叠情况估计能省 20~30%。

⚠️ 与优化项 A 叠加后，那次 52769 字符的四连问预计降到 10000 字符量级。

---

## 9. 明确不做（避免把力气花在无效优化上）

| 不做 | 理由 |
|---|---|
| HNSW 调参 / `hnsw.ef_search` | 阶段 1 精扫 0.099 ms，HNSW 现在根本不参与（v2 §4.3 已说明），调它没有对象 |
| `halfvec` / int8 / 二值量化 | 优化的是 0.099 ms 里的一部分。63~570 行的数据量，收益为负（净增复杂度） |
| Matryoshka 降维 | 同上；且 `SYSTEM_SEEDS` 里 embedding 维度写死、改动要迁移 chunk 表向量列 |
| 换 Qdrant / Milvus / 上 ES | 同上。且 v2 §14.3 已把"PLAYBOOK 空间拒绝非默认 PG"写进 `create_space`，那是有原因的（写 ES、读默认库 = 数据完好但一条都查不到） |
| ColBERT / late interaction 多向量 | 需要换 embedding 栈 + 换存储格式，收益全在"长文档精排"，与 450 字符的 profile 路由无关 |
| 把 body 也拉进路由 | 两段式（profile 路由 / body 细节）是 v2 决策 D4 的既定结论，不重开 |
| query embedding 缓存 | 模型每次自拟检索词、措辞都不同，命中率接近 0 |
| 图数据库 | 关系已用三个 JSONB 列 + 递归 CTE 跑通（v2 决策 D19），无图算法需求 |

---

## 10. 排期与依赖

```
0. 评测基线（半天）─────┬──> 5. 形态对齐 C（半天）
   scripts/eval_...     ├──> 6. HyPE D（1~2 天）  ← 主项
   + 正文出题新金标      └──> 7. rerank E1（半天）

无依赖，可立刻做：
1. 低置信短路 A（1 小时）  ← 单项 ROI 最高
2. 阶段 2/3 并发 B（1 小时）
3. pid 去重 F（半天）
```

| 序 | 项 | 成本 | 主要收益 | 需基线 |
|---|---|---|---|---|
| 1 | A 低置信短路 | 1h | context −60%，不再硬答，顺带产出覆盖缺口清单 | 否 |
| 2 | B 阶段并发 | 1h | 省一次串行往返 | 否 |
| 3 | F pid 去重 | 0.5d | context 再 −20~30% | 否 |
| 4 | 0 评测基线 | 0.5d | 后续可验收 | — |
| 5 | C 形态对齐 | 0.5d | 修掉 query↔索引 形态错配 | 是 |
| 6 | D HyPE | 1~2d | **路由准确率的主要增量** | 是 |
| 7 | E1 rerank | 0.5d | 概念性主题 | 是 |

---

## 11. 待确认

| # | 议题 | 选项 |
|---|---|---|
| 1 | 优化项 C 走 A（改 docstring）还是 B（双检索词） | B 更稳但改工具签名，需同步 `search_playbooks` 的 VO 与提示词 |
| 2 | 优化项 D 的扩写问法数量与范围 | 全量 63 本 × 8~10 条，还是先做 20 本概念型试点 |
| 3 | 优化项 D 的问法是否进 `ai_rag_playbook.questions` 列 | 进列 = 审核页可见可改（管理页设计的节点表格已有 questions 列）；不进 = 只作为 chunk 存在、审核看不到 |
| 4 | 优化项 A 的阈值 0.45 | 是否先按 315 题金标跑一遍分布再定 |
| 5 | 优化项 E 走 E1（Cohere rerank）还是 E2（LLM 选） | 延迟 +100ms vs +0.5s；E2 对概念性主题理论上更强 |
| 6 | 评测脚本是否恢复（台账 §20 曾决策不做） | 不恢复则 C / D / E 只能人工验收，5~10% 退化测不出 |
