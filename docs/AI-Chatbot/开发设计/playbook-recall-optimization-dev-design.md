# Playbook 召回优化开发设计（多向量问法 + 形态对齐 + 低置信短路）

> 关联文档：
> - 现行实现（先读）：[./playbook-chatbot-integration-dev-design.md](./playbook-chatbot-integration-dev-design.md)（v2，2026-07-29；§3.1 profile 配方、§5 检索链路、§13 后续）
> - 管理页设计：[../../superpowers/specs/2026-08-03-playbook-manage-design.md](../../superpowers/specs/2026-08-03-playbook-manage-design.md)
> - 台账（本文多处引用）：`../../../python/CIOaas-python/docs/待优化项.md` 的四条：「playbook 召回评测脚本」「多轮检索累计灌给模型 5 万字符」「概念性主题召回弱 + 内容覆盖缺口」「ingest 缺“字段级静默变空”校验」（**按标题引用，不按行号**——台账插入新条目会让行号整体平移）
>
> 阶段：⑤ 开发设计 ｜ 版本：**v3** ｜ 日期：2026-08-24 ｜ 状态：**待评审** ｜ 端：Python（CIOaas-python）
>
> v3 相对 v2（2026-08-24，无泄漏金标落地 + 三视角审查后修订）：§2 的「⏳ 仍待做：另建一套无泄漏
> 金标」**已完成**，并记下与本文原方案的两处偏离（正文读库不读预研快照 / 出题量按正文长度分配）；
> §1 基线表新增无泄漏口径与 `usable@3` 两行，并标注**旧口径（库里 questions）在 version=5 上已
> 饱和到 r@3 100%、此后不可再用**；§2 补「结论怎么读」——本套金标只覆盖正文细节题、单路、无
> rerank，**不等于"真实水平"**（三处偏差已实测量化）；实证更正 Jaccard 泄漏闸门是兜底而非主力
> （三次运行零触发）；记录一个待 A/B 的发现：去掉 HyPE 问法分段分数反而更好。
>
> v2 相对 v1（同日自审后修订）：查库发现 body 第一段已不是元数据块，阶段 3"第一段固定带"的理由失效——但效果未必变差，已定**保留现状**（§11 议题 7），连带的校验缺口转台账；
> 明确 C 改 `route()` 签名需与评测脚本同提交、D 改内部则不需要；A 的短路路径**仍须记录召回**；
> B 收益下调到 <5% 并移出排期主线；D 拆成"先拆现有 5 条（零 LLM 成本）/ 后扩写"两步；
> 补预算跨 seed 先到先得这个潜在缺陷；生产口径改以 r@3 为主（`default_top_k=3`）。
>
> 本文只讲**优化**，不重述现状。所有"现状如何"一律指向 v2 设计文档，不复制。

---

## 1. 现状基线（散落各处的实测数字，汇总一处）

后面每一项优化都拿这张表当判断依据。**没有新测量，全部来自既有留档。**

| 指标 | 实测值 | 出处 / 口径 |
|---|---|---|
| **生产相关指标 r@3（旧口径）** | **96.5%**（304/315）→ **已饱和 100%** | ⚠️ 生产 `default_top_k=3`，所以"对的手册在不在 3 个 seed 里"才是生产口径。评测脚本按 top_k=5 跑，r@5 只作参考。**⚠️ 2026-08-24 复测：version=5 上此口径已到 r@1 99.7% / r@3 100%**（`d1-v5.json` 快照即已如此）——D-1 之后每条 questions 各自是一行 `chunk_kind='question'` 向量，拿它检索等于精确匹配自己。**该口径此后既测不出改进也测不出中等退化，已不可用**，改用下面的无泄漏口径 |
| **无泄漏口径 r@3** | **82.6%**（247/299） | 2026-08-24，version=5，`golden-leakfree-v5.json`（正文出题，299 题）。**只覆盖"正文细节题"、单路检索、无 rerank**，读法见 §2。同批：r@1 64.2% / r@5 87.3% / MRR@5 0.738 / 完全召不回 38 条 |
| **usable@3（新增）** | **75.6%**（226/299） | 同上。= 排进前三**且** top1 ≥ `COVERAGE_THRESHOLD`(0.50)。33 题（11%）检索找到了但线上会短路成"库里没这主题"——**只看 r@3 会系统性高估用户可见质量** |
| 路由准确率 r@1 | **89.5%**（282/315） | 台账「playbook 召回评测脚本」条，2026-07-31，v1 sonnet5，315 题，`route()` 口径。**是上界**——questions 原文在被检索文本里。r@1 的真实意义不是"准不准"，而是**排第几决定能分到多少正文预算**（见 §8 的预算不公） |
| r@5 / MRR@5 | 99.4%（313） / 0.934 | 同上 |
| 完全召不回 | 2 条 | 同上 |
| 图扩展的必要性 | **56.2%** 的 `depends_on` 前置项纯向量 top-5 召不到 | v2 §2 |
| 数据规模 | 63 节点 / 339 chunk（profile 63 + body 276） | v2 §11 步骤 6，四次 ingest 一致 |
| **questions 密度** | **正好 5.0 条/本**（315 / 63） | 2026-08-10 查库（version=2）。⚠️ v2 §3.1 写的"平均 2.5 条"是**源站改版前**（157/64）的值，已过时 |
| **profile 长度** | 平均 **450** 字符（样例 486 字符 / 93 token / 1536 维） | 同上。v2 §3.1 写的"约 275 字符"同样是改版前的值 |
| body 长度 | 平均 **1142** 字符/段（276 段，切分口径 1400/150） | 同上 |
| profile 精扫 | **0.099 ms** | v2 §4.3 |
| route 全流程 | **~7 ms/次**（315 次 2.2s） | 台账「playbook 召回评测脚本」条 |
| query embedding | **~55 ms/次**（315 条 17.3s） | 台账「playbook 召回评测脚本」条 |
| 单轮 context 峰值 | **52769 字符 ≈ 13000 token**（模型自主调 4 次） | 台账「多轮检索累计灌给模型 5 万字符」条 |
| 概念性主题得分 | 全场最高仅 0.442；`board-of-directors` 第 9（0.342） | 台账「概念性主题召回弱 + 内容覆盖缺口」条 |
| 同一问题换问句形式 | `board-of-directors` 升到第 2（0.367） | 台账「概念性主题召回弱 + 内容覆盖缺口」条 |
| ingest 成本 / 耗时 | opus5 $0.21 / 143s（关系推断 76s + 63 次 embedding 64s） | v2 §7.1.1、管理页设计 §2.2 |
| 全量重嵌成本 | 387 chunk ≈ $0.003 | v2 §13 |

**从这张表直接读出三个结论**，它们决定了本文的取舍：

1. **向量检索不是瓶颈**：0.099 ms vs 55 ms 的 embedding 往返，差 550 倍。任何针对索引/量化/向量库的优化都是负收益（§9）。
2. **成本不在 embedding**：单次 $0.00002，ingest 一年跑不到 10 次。成本在**灌进对话的 13k token**。
3. **准确率的空间在 profile 配方与召回形态**，不在检索引擎。

---

## 2. ⚠️ 前提：先把回归基线拿回来

> ✅ **已完成（2026-08-10）**。台账「playbook 召回评测脚本」条原记「2026-07-31 决策不做」已推翻并更新——本文 §5 / §6 / §7
> 三项恰好全部落在它的防护范围内，盲改的风险高于重写成本。

**首跑结果逐位复现台账「playbook 召回评测脚本」条的留档基线**，说明脚本口径与当初那次测量一致：

| 指标 | 本次（version=2，315 题） | 台账「playbook 召回评测脚本」条留档（2026-07-31，v1） |
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

实现要点（对齐台账「playbook 召回评测脚本」条的五条）：

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

### ✅ 已完成（2026-08-24）：另建一套无泄漏金标问题

v2 §13 指出的必要性已被证实、且比预期更急：D-1（HyPE）上线后旧金标**不是变弱而是彻底饱和**
——version=5 上 r@1 99.7% / r@3 **100%**（每条 questions 各自是一行 `question` 分段，检索它
等于精确匹配自己）。旧口径此后测不出任何改进、也测不出中等退化。

**产出**

| 文件 | 内容 |
|---|---|
| `scripts/gen_playbook_golden.py` | 出题脚本（正文出题 + 六道过滤闸门 + 泄漏度自证） |
| `scripts/data/playbook/golden-leakfree-v5.json` | 299 题金标（63 本，标签存 **pid** 不存 entry_id，故跨版本可用） |
| `scripts/data/playbook/baseline-leakfree-v5.json` | 对应基线快照（含逐题排名 + `topPids` 归因字段） |
| `scripts/eval_playbook_recall.py` | 新增 `--golden`、`usable@3`、McNemar 配对显著性、口径指纹校验 |

**⚠️ 与本文原方案的两处偏离（照实现为准，别按本文旧文字重做）**

1. **正文取自库里指定版本的 body 分段，不是 `playbooks_bodies.json`**。那份是预研快照
   （64 节点 / 旧源站版本），拿它出题会问到库里已经没有的内容、被记成"召回失败"，等于把
   "源站改版"混进检索质量的差值里。改读库后出题与被检索内容**同源**。
2. **出题量按正文长度分配**（<1500 字符只出 3 条）。6 本短正文硬凑 5 条会产出同义或空洞题
   （实测占全集 9.6%，最短的 `p-and-l-explained` 只有 317 字符）。故题数 299 而非 315。

**结论怎么读（重要，2026-08-24 方法学审查）**

这套金标是一套合格的**「阶段 1 profile 路由 · 单路 · 无 rerank · 正文细节题」回归基线**，
**不能**被读成"Playbook 检索的真实水平 82.6%"。三处已实测的偏差，方向相反、不互相抵消：

| 偏差源 | 方向 | 实测量级 |
|---|---|---|
| 标签歧义（≥2 本都能合理回答，只算一本对） | 压低 | 人工抽样 32%(9/28)；全量代理指标 23.6%。**故只看 r@3 / MRR，别拿 r@1 做决策**（r@1 里约 10pp 是标签噪声） |
| 评测缺线上后两级（线上是双路检索词 + top-10 rerank） | 压低 | r@10 = 94.9%；"完全召不回"里约一半落在 rank 6~10 = 线上 rerank 候选池内。同口径放宽上限约 **93~95%** |
| 题型只采难尾（提示词刻意排除"整本级"问法，而那是线上主流） | 压低 | 真实日志问句 top1 相似度 0.72~0.99，本金标均值 0.612；合成的整本级问句 r@3 100%。**这套题保护不了线上主路** |
| 残余语义泄漏（词面 Jaccard 抓不到的同义改写） | 抬高 | 13 条余弦 ≥0.75（最高 0.873，其 Jaccard 仅 0.29）；剔除后 r@3 只降 0.25pp |
| 忽略线上 `COVERAGE_THRESHOLD` 短路 | 抬高（当"可用率"读） | 见 §1 的 `usable@3` = 75.6%，比 r@3 低 7pp |

**怎么用**：固定同一份金标文件、改动前后各跑一次走**配对**口径（脚本已打印 McNemar 的 b/c
与 p 值）。判据：**净变化 <3pp 一律当噪声；≥4pp 且变差的题不成簇，才认**。换一套重新出的题
之间差 ±5.7pp 都在噪声内（实测同 20 本三次独立出题，r@3 极差 3pp，而题目本身换掉了三分之一）。

**⚠️ Jaccard 闸门是兜底、不是主力**（实证更正）：`_MAX_JACCARD_VS_INDEXED = 0.55` 在三次独立
运行里**一次都没触发**。真正拦住泄漏的是提示词把该本 5 条索引问法交给模型并禁止同义改写；
词面度量抓不到同义改写。要让"无泄漏"从口号变成可审计，需把闸门换成 embedding 相似度
（≥0.80 判泄漏），见下方仍待做清单。

**顺带发现（值得单独 A/B，本文不下结论）**：在这套金标上**去掉 HyPE 的 question 分段、只留
profile 名片，分数反而更好**——r@1 70.6%（+7.0pp）/ r@3 85.6%（+1.3pp）/ MRR 0.784（+0.041），
且在整本级问句上不差。旧金标看不到这一点，因为它已被 HyPE 打到饱和。

### ⏳ 仍待做（本项的剩余缺口，按性价比排序）

1. **多标签标注**：把金标结构从 `pid` 改成 `acceptable_pids[]`，优先处理代理指标里 74 条
   "对手本 body 相似度差距 ≤0.05" 的题。做完 r@1 才有意义（预计升 8~10pp，且是真实的）。
2. **补"整本级 / 真实流量"分层**：63 条整本级问句 + `ai_rag_search_log` 里真实 CHATBOT 检索词
   （现有 58 条，英文 playbook 类约 20 条可直接手标）。**理由：线上主路目前一条题都没覆盖**，
   任何"要不要保留 HyPE 问法分段"这类决策只看难尾会做反。
3. **把线上后两级接进评测**：双路检索词（keywords 由同一出题步骤产出，避免评测自拟）+ rerank
   top-10 → top-3。不做的话 r@10 与 r@5 之间那 7pp 永远算在"检索失败"头上。
4. **泄漏闸门换 embedding**（≥0.80 判泄漏），并把 `restates-title` 扩成"含任何一本手册的完整
   标题即丢"——后者已实现（`names-other-playbook`，实跑拦下 4 条）。

> **这一步是优化项 D-2 的硬前提**（§6 风险 3）：D-2 扩写问法会进一步放大旧口径的泄漏面，
> 必须用本套金标验收。§5 / §7 当时用旧金标验收无误，但**此后不可再用旧口径**（已饱和）。

---

## 3. 优化项 A：低置信度显式短路 🟢 无需基线

### 问题

台账「多轮检索累计灌给模型 5 万字符」条记录：一次提问模型自主调 `search_playbooks` **4 次**（换 4 种检索词），累计 52769 字符 ≈ 13000 token，其中第 2 次的结果基本没被答案使用。触发条件是「概念性主题召回弱」那条说的**相似度普遍低（0.32–0.44）时模型不满意就换措辞重试**。

而同一条台账记录同时确认：那次库里**确实没有**"董事会月报"这个主题（全场最高 0.442），属**内容覆盖缺口，不是检索故障**。

现在的行为是：照常返回 0.34 分的手册摘录 → 模型要么拿它硬答，要么换措辞再来一次。两种都是坏结果。

### 改法

`playbook_service.search()` 在阶段 1 之后判断 top-1 相似度：

```
top1_similarity < COVERAGE_THRESHOLD（上线值 0.45 → 2026-08-12 校准为 0.50）
  → 仍调 _fire_usage_record(route_hits=实际命中)      ← ⚠️ 不可跳过，见下
  → 不走阶段 2 / 阶段 3，不返回任何摘录
  → 返回 {ok: true, coverage: "low", topSimilarity: 0.34,
          note: "库中没有覆盖该主题的方法论手册。请基于通用知识回答，
                 不要换检索词重试。"}
```

⚠️ **短路路径必须仍调 `_fire_usage_record`**。它的 docstring 明确要求"只要真跑过向量检索就记，
无命中也记——问了但没匹配上正是拿来调 profile 问法的信号"。顺手绕过记录会同时丢两样：本项
自己承诺的"覆盖缺口可统计"，以及现有的低分命中统计。短路只跳过阶段 2/3，**不跳过记录**。

顺带：短路同时省掉阶段 2 的 5 条 SQL + 阶段 3 的 1 条，虽然本地库这几毫秒不是重点。

阈值 0.45 的来历：「概念性主题召回弱」那次"确实没覆盖"的全场最高分是 0.442；而正常命中的例子（`churn-identification-process` 0.682）远在其上。**上线后按台账「playbook 召回评测脚本」条的方式抽一批真实 query 校准一次**，不要当固定常量。

> ✅ **已校准一次：0.45 → 0.50（2026-08-12）**。依据是 v5 发布后在聊天页跑的 10 题**线上口径**实测（模型改写后的问句 + C 的术语路，两路取 MIN）：库里真有对应手册的 7 题全部 ≥0.5804，库里没有的 3 题全部 ≤0.4854，中间空出 0.49~0.58 一道缝，取 0.50 落在缝里偏下留抖动余量。
>
> ⚠️ **这次校准同时暴露了本节埋的一个方法论坑**：0.45 是按"把用户原话直接喂进检索"的分数分布定的，而线上进检索的从来不是原话。两种口径分数差到一个数量级（同一问题 0.444 → 0.598），按原话口径会得出"合法与库外区间重叠、调阈值两头都得罪"的错结论。**再校准时口径必须是线上口径**（读 `ai_llm_tool_call_log` 里模型实际传的 question/keywords），详见测试用例文档 §0.3。

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

⚠️ **组装必须留在 `gather` 之后**：阶段 2 的产出按 **pid** 组织、阶段 3 的产出按 **entry_id** 分组，
拼 `hit.excerpts` 要靠阶段 2 给的 `pid_to_entry` 映射。查询无依赖，**组装期有依赖**。

### 收益：很小，定性为"顺手做掉的代码整洁"

按实测重算：阶段 2 是 **5 条 SQL**（映射 / 递归 CTE / feeds 反查 / 扩展节点属性 / entry 标题），
阶段 3 是 1 条，都打本地 PG，加起来十几毫秒；而同一次调用的 embedding 是 **470 ms**
（2026-08-10 评测实测，并发 8 下的单次墙钟）。**并发省下的占全链路不到 5%。**

真正显现价值的场景有两个：业务库与向量库分离到不同实例（跨网络 RTT）、或 `depends_on` 关系
规模长大让递归 CTE 变慢。**所以本项排在末尾**，等哪次动 `search()` 时顺手改，不单独排期。

---

## 5. 优化项 C：检索词形态与索引形态对齐 🟡 需基线

### 问题：两处口径互相矛盾

| 位置 | 现状 |
|---|---|
| 索引侧（`PROFILE_TEMPLATE`） | 嵌的是 **`Key questions:` 问句**，v2 §3.1 明确说这是把匹配变成 **query↔query** 的核心技巧 |
| 查询侧（`search_playbooks` docstring） | 要求"**陈述式关键词**、不要整句照抄"（v2 §5，与 `search_knowledge_base` 同口径） |

索引侧存的是问句，却要求模型给陈述式短语——**自己把 query↔query 打回成 query↔陈述式**。

台账「概念性主题召回弱 + 内容覆盖缺口」条的实测正好是这条的证据：同一个意思，`board-of-directors` 在陈述式检索词下排第 9（0.342），换成问句 `what should the board see every month` 升到第 2（0.367）。那条台账把差异归因于"模型加了原问题没有的词"，那是一部分；**另一部分就是形态**。

### 改法：双检索词（已定）

工具签名从 `query: str` 改为接受两个字段：

```
question: str   # 用户口吻的问句，如 "what should the board see every month"
keywords: str   # 术语短语，如 "board reporting monthly metrics"（可空）
```

各 embed 一次，在 `search_profile` 里对同一 entry 取 `MIN(distance)`（两路谁近算谁）。

- 成本：多一次 embedding（+55 ms、+$0.00002/次）
- 好处：**不赌哪种形态更好，两种都覆盖** —— 术语型问题（"ARR schedule 怎么做"）走 keywords 路，概念型问题走 question 路
- `keywords` 留空时退化为单路，等价于只改口径，所以**灰度成本为零**：先只在提示词里教模型填 `question`，观察一段再要求两个都填
- ⚠️ 与优化项 D（HyPE）叠加后收益更大——索引侧问句密度提高，question 路的命中面同步扩大

改动落点：`search_playbooks_tool` 的签名与 docstring、`playbook_service.search()` 的入参、
`PlaybookProcessor.route()` 的 `query_vector` → 两路、`PlaybookChunkRepository.search_profile`
的距离取 `LEAST(两路)`。

### ⚠️ 本项改 `route()` 签名，评测脚本必须同一提交内同步改

§2 立的规矩是"**必须调 `processor.route()`**"以保证口径一致。本项要给 `route()` 加第二路
`query_vector`——**脚本不跟着改，跑出来的还是旧单路结果**，会把"C 没生效"误判成"C 没用"。

两类改动的验收流程不同，别混：

| 改动类型 | 例 | 脚本要不要动 |
|---|---|---|
| 改 `route()` **签名/入参** | 本项（双检索词） | **要**，同一提交内改 |
| 改 `search_profile` **内部实现** | 优化项 D（HyPE） | 不用，脚本自动走新逻辑（口径天然一致） |

### 验收

315 题金标（问句形式）跑**改动前 / 改动后**两组对照。⚠️ **注意金标本身是问句改写来的**，会天然偏向 question 路——单看这套金标一定"变好"，那是自证不是证据。所以必须同时用 §2 那套"由正文出题"的新金标交叉验证；两套结论一致才算数。

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

### 改法

**"一个向量" = "一行 chunk"** ——`ai_rag_playbook_chunk` 一行就是一段文本加一个 `VECTOR(1536)`，
所以"每问一向量"就是每条问法写一行。`chunk_kind` 是 rag 的跨业务约定（v2 决策 D5），加第三个取值即可。

#### 数据模型：新增 `expanded_questions` 列（议题 3 已定方案 3）

```sql
-- sql/migrations/business/V0NN__playbook_expanded_questions.sql
ALTER TABLE ai_rag_playbook
  ADD COLUMN IF NOT EXISTS expanded_questions JSONB NOT NULL DEFAULT '[]'::jsonb;
COMMENT ON COLUMN ai_rag_playbook.expanded_questions IS
  'LLM-expanded question variants (one vector per item in ai_rag_playbook_chunk, chunk_kind=question); source-site questions stay in the questions column';
```

**为什么不复用 `questions` 列**：那一列现在同时喂四处——`inject_profile` 拼 profile 文本、
审核页节点表格、`_attr_changes` 逐字段 diff、`_compute_diff` 的 attrs 指纹。把扩写塞进去会
①**把 8~10 条全拼进 profile 文本**，正好触发本项要消灭的稀释；②让 diff 分不清"源站改了问法"
（改版信号）和"LLM 又抖了一次"（噪声）。分两列后 `questions` 的四个消费点**一个字不用改**。

这与关系（`depends_on`/`feeds`/`refers_to`）完全同构：同样是 LLM 产物、同样逐次不同、同样没有
客观金标、同样以人工审 diff 为唯一闸门 —— 所以照抄它"独立列 + diff 单独一段 + 审核页可编辑"
这套现成机制，不新建任何东西。

| 文件 | 改动 |
|---|---|
| 迁移 | `ai_rag_playbook` 加 `expanded_questions JSONB NOT NULL DEFAULT '[]'`（迁移号取当时最大 +1） |
| `domain/models/playbook_model.py` | 加对应列 |
| `playbook/models.py` | 加 `CHUNK_KIND_QUESTION = "question"` |
| `playbook/playbook_processor.py` | 新增 `inject_questions(questions, seq_start)`：`embed_documents(texts)` **一次批量**拿 N 个向量，逐条产出 `ChunkResult`，`content` 是**裸问法**（不拼 title/category/description——这才是"不做平均"的全部含义）。seq 接在 profile 之后。⚠️ **profile 文本与 `build_profile_text` 一个字不改** |
| `playbook/repository.py` | ① 过滤放宽到 `IN ('profile','question')`；② **必须先按 entry 折叠再取 top_k**，否则同一本手册的 profile 与 8 条问法会互相挤占名额（= 预研 387 条混合 chunk 那个坑）；③ 顺带只 select 需要的列，见下 |
| `playbook_service._write_version` | 扩写落 `expanded_questions` 列 + 多写 N 条 chunk；`node_count` 语义不变（仍是节点数） |
| `_compute_diff` / `_attr_changes` | `expanded_questions` **单独一段**，且**只报数量与新增/消失条数**，不逐条列出（缓解 a，见风险 5） |
| 审核页 | 节点表格加一列展示 `expanded_questions`；编辑走既有 `_require_draft` 闸门 |
| `activate` 完整性校验 | `count_entries_with_profile` **保持只看 profile**——问法可以缺，profile 不能缺 |
| 扩写问法 | ingest 期一次 LLM 批量调用（haiku），**全量 63 本**（议题 2 已定） |

#### 检索侧：max-pool 回 entry（PG 惯用写法）

```sql
SELECT * FROM (
  SELECT DISTINCT ON (entry_id)
         entry_id, id AS chunk_id, embedding <=> :qv AS dist
    FROM ai_rag_playbook_chunk
   WHERE entry_id = ANY(:entry_ids)
     AND metadata->>'chunk_kind' IN ('profile', 'question')
   ORDER BY entry_id, dist          -- 每个 entry 只留最近的那一条
) t
ORDER BY dist
LIMIT :top_k
```

折叠后 **top_k 行仍是 top_k 个互不相同的 playbook**，`route()` 对外契约不变。等价写法：
`ROW_NUMBER() OVER (PARTITION BY entry_id ORDER BY dist)` 筛 `rn=1`。

**取 `MIN` 而不是平均**：语义是"这本手册**有某一条问法**贴合用户问题"。改成平均等于把拼接稀释
从文本层搬到 SQL 层，问法越丰富越吃亏 —— 正是要消灭的东西。

#### ⚠️ 顺带必须修：别把 1536 维向量拉回来

现在 `search_profile` 是 `select(PlaybookChunk, distance)`，**整个 ORM 实体含 `embedding` 列**，
而 `route()` 只用 `entry_id` 与 `id`。63 行时每次拉回约 380 KB，扩到约 570 行就是约 3.4 MB，
一轮对话模型调 4 次即约 13 MB，纯浪费。改成 `select(PlaybookChunk.entry_id, PlaybookChunk.id, distance)`。
这条**现在就该改**，HyPE 之后是必须改。

#### 回滚只需一行

过滤条件从 `IN ('profile','question')` 改回 `= 'profile'` 即完全回到现状——question chunk 留在
库里查不到就等于不存在，**零数据迁移**。这也是"profile 文本原样保留"的用意。

### `RouteHit.chunk_id` 的语义变化（顺带的好处）

命中问法时 `chunk_id` 指向那条 question chunk，`hit_count` 累加到它身上。于是：

> **哪条问法真的被用户命中过，直接查 `hit_count` 就知道** —— 这是后续删减/继续扩写问法的唯一客观依据，也是 specrag `feedback_hint` 那套反馈闭环的起点。

### 分两步做，成本与验收方式完全不同

| | 第一步：只拆现有 5 条 | 第二步：扩写到 8~10 条 |
|---|---|---|
| 新增 chunk | 63 × 5 = **315 条**（339 → 654） | 63 × 8~10 = **504~630 条**（→ 843~969） |
| 数据来源 | 直接读 `questions` 列（源站那 5 条） | LLM 扩写 → 落 `expanded_questions` 列 |
| LLM 成本 | **0**——问法已在 `ai_rag_playbook.questions` 里 | 一次批量调用（haiku）≈ $0.05，**全量 63 本** |
| embedding 成本 | ≈ $0.003 | ≈ $0.005 |
| 验收金标 | **现有 315 题即可**（与 89.5% 同口径可比） | **必须先有 §2 那套无泄漏金标** |
| 阶段 1 精扫候选 | 63 → 约 380 行（约 0.6 ms） | → 约 570~700 行（约 0.9 ms） |
| ingest 额外耗时 | 批量提交约 **+60 s** | 约 **+95 s** |

**第一步是零 LLM 成本、零新金标依赖、可立即验收的**——这才是本项的主体。第二步是增量。

ingest 耗时的算法：现有 64 s 是 **339 个 chunk** 的总时间（每节点一次批量 `embed_documents`），
即约 0.19 s/chunk，不是 1 s/节点。所以第二步的 504 条约 +95 s，**不是 +8 分钟**。前提是
**批量提交而非逐条**——逐条会退化成 504 次往返。

`RouteHit.chunk_id` 会指向命中的那条 question chunk（见下），但阶段 1 的**对外契约不变**，
所以本项属于"改 `search_profile` 内部"，评测脚本不用动（对比 §5 的表）。

### ⚠️ 风险与缓解

1. **ingest 耗时**：批量提交时第一步 +60 s、第二步 +95 s（143 s → 约 5 分钟）。管理页设计已把 ingest 改异步 + 轮询（决策 5），机制上撑得住，但前端进度文案的时序表要同步更新。**若误写成逐条 embedding，会退化成 +8 分钟以上。**
2. **问法质量差会引入噪声**（仅第二步）：LLM 可能生成与手册无关或彼此高度重复的问法。**议题 2 已定全量 63 本**，所以不走"先做 20 本试点"那条缓解——质量把关改为**人工审 diff**（与关系推断同一套闸门：`expanded_questions` 在审核页可见、DRAFT 期可编辑、发布前必须过一遍）。
3. **金标泄漏面扩大**（v2 §13 已预警，**仅第二步**）：扩写后的问法若来自原 questions，泄漏更重。所以 §2 那套"由正文出题"的新金标是**第二步的硬前提**；第一步用现有金标即可。
4. **`entry.chunk_count` 会跳变**（5.4 → 10.4 → 13~15）。devSupport 文档页的"分段数"列会明显变大，属预期，但值得提前告知运维，别当成 ingest 出错。
5. **审核负担再加一份（已接受，缓解 a）**。管理页设计 §8 原话："关系是 LLM 推断产物、每次重新掷骰子——同模型同内容仅改一个标题词，关系重叠只有 27/54，**diff 每次都得真审**"。扩写问法会把这份负担再加一层：全量 63 本 × 8~10 条，每次 ingest 重扩，diff 里可能多出 500+ 条变化。**缓解 a（已定）：diff 里 `expanded_questions` 只报数量与新增/消失条数，要看细节点开单个 pid。** 审核量因此回到"63 节点 + 50 条关系 + 63 行问法计数"，可控。<br>⚠️ 曾考虑的另两条已否：**把扩写从 ingest 拆成独立端点**（ingest 不变慢，但多一个易忘的运维步骤，忘了会静默退化成只有 profile 路由、不报错——正是本设计一直在避免的那类失败）；**跨版本继承**（v2 决策 D2 明确一期不做，要动表结构）。

---

## 7. 优化项 E：路由后加一层重排 🟡 需基线

### 问题

台账「概念性主题召回弱 + 内容覆盖缺口」条：概念性/总论型手册在词面上竞争不过术语密集手册——问"董事会每月一页数据"，前 6 名被 kpi / sales-metrics / support-metrics / saas-metrics / sales-efficiency 各种 metrics 手册挤满。这是 bi-encoder 的固有偏置（对术语共现敏感），**HyPE 能缓解但消不掉**。

### 方案（已定）：OpenRouter 上的 `cohere/rerank-4-pro`，top-10 → top-3

```
阶段 1  route(top_k=10)                          →  10 个候选 playbook
          ↓
      【rerank(query, [10 条 profile 文本], top_n=3)】  →  截成 3 个 seed
          ↓
阶段 2  图扩展（前置 2 跳 / 输入源 1 跳）            ← rerank 不接触这一层
阶段 3  取 3 个 seed 的正文
```

#### 🚫 铁律：rerank **只作用于阶段 1 的候选，绝不碰图扩展出来的节点**

这条必须写死，因为"把扩展节点也一起重排、给模型一个统一排序"看起来非常合理，而它会
**静默清零图扩展的全部价值**：

扩展节点与用户问题的相似度**本来就低，这是定义性特征不是缺陷**。v2 §2 的实测就是这个意思——
**56.2% 的 `depends_on` 前置项纯向量 top-5 召不到**。用户问"怎么做现金流预测"，它的前置链是
`Cash Flow Forecast → Budget Creation → Define the Mission`，而 `Define the Mission` 与原问题
语义距离极远。**任何相似度模型都会正确地判定它不相关然后把它砍掉**——而那恰恰是用户最需要知道的
"你还得先做 X"。v2 §1 原话：「必须能查『做 X 前要先做什么』『谁依赖 X』——**这是结构查询，
语义相似度替代不了**」。

同源的两条一并写死：

| 该用什么 | 不该用什么 |
|---|---|
| 扩展节点排序用 `(depth, pid)` **结构序**（距离由近到远） | 不用相似度排——最近的前置会被"碰巧词面相似的远房节点"挤掉 |
| 扩展节点数量用 **depth 截断**（`depends_on` ≤2 跳、`feeds` 1 跳） | 不用相似度筛 |

| 项 | 值 | 来源 |
|---|---|---|
| provider / model id | `openrouter` / **`cohere/rerank-4-pro`** | ⚠️ 与 Cohere 原生名 `rerank-v4.0-pro` **不同名**，`Models` 符号库按 OpenRouter 口径登记 |
| 计费 | **$0.0025 / search**（一次调用一次计费，与文档数无关） | OpenRouter 模型页 |
| 上下文 | 33K | 同上。我们送 10 × 450 字符 ≈ 1.2K token，余量充足 |
| 端点 | `POST /api/v1/rerank` | 2026-08-11 实测：无 key 返 **401**（存在）；不存在的路径返 404（对照） |
| 请求/响应形状 | `{model, query, documents, top_n?}` → `results[{index, relevance_score}]` + `usage` | OpenRouter TS SDK 文档示例。**与 Cohere rerank 同构** |

#### 为什么走 OpenRouter 而不是已有的 Cohere 直连

代码里 rerank **已经是真实现、不是占位**：`kernel/cohere_native/rerank.py`（httpx REST）+ `vendors/cohere/rerank.py`
薄叶子自注册 `(COHERE, RERANK)` + `tests/llm/test_cohere_rerank.py`，默认模型 `rerank-v3.5`。但它是
**Cohere 直连**（`kernel/config.py._build_cohere_config`：api_key 取 `COHERE_API_KEY`、REST base_url 固定）。

| | OpenRouter（已定） | Cohere 直连 |
|---|---|---|
| API key | **已有 `OPENROUTER_API_KEY`** | 需另申请配 `COHERE_API_KEY` |
| 账单 | 与全部 chat / embedding 统一 | 多一个供应商 |
| 成本采集 | OpenRouter 惯例带内实报 → 可落 `cost_source=provider` | 拿不到实报，只能 `estimated` |
| 模型档位 | rerank-4-pro（2025-12 发布，实测优于 3.5） | 默认还是 rerank-v3.5 |
| 代码量 | 需加薄叶子 + config 分支（见下） | 零代码 |

换 API key 的成本比换模型档位的收益低，所以走 OpenRouter。

#### 落地：按 llm/CLAUDE.md 属"新增同协议厂商，零 SDK 代码"

因为 OpenRouter 的 rerank 就是 Cohere 的形状，**可直接复用 `CohereRerankClient`**，不新建协议族：

| 文件 | 改动 |
|---|---|
| `kernel/config.py` | 现在 `_build_cohere_config` 把 REST base_url **写死**。加一个 openrouter+rerank 分支（或把 base_url 参数化），api_key 取 `OPENROUTER_API_KEY` |
| `vendors/openrouter/rerank.py`（新） | 薄叶子：`register_kernel_client(Provider.OPENROUTER, Capability.RERANK, _build)`，`_build` 返回 `CohereRerankClient` |
| `model_registry/models.py` + `vendors/openrouter/models.py` | 登记 `cohere/rerank-4-pro` 常量与 `ModelSpec` |
| `infrastructure/pricing.py` | 补 rerank 价目。`pricing.py:78` 原本就留了口子："rerank 未定价（有意留空，非遗漏）……任一能力接入真实业务时在此补价目（**rerank 按 per-search**）" |
| `playbook_service.search()` | 阶段 1 取 top_k=10 → 调 rerank → 截 3 个 seed 后再进阶段 2/3 |

⚠️ **上线前必须拿 key 实调一次**确认三件事：请求体字段名逐字对得上、响应 `results[].index` 的语义
（是否为入参 documents 的下标）、以及**响应有没有带 `usage.cost`**（决定 `cost_source` 落 `provider`
还是 `estimated`）。这三条我只从文档与 SDK 示例推得，没有实调验证。

#### E2（LLM 从 top-10 里选 3）已否

曾考虑照 Nissist 的"粗召回 + LLM 选"：63 本手册的目录只有约 5.4k token，小到可以整份塞进 prompt。
但有了 rerank-4-pro 之后 E2 在三个维度上都不占优——延迟 +0.3~0.6 s vs +100 ms、要多维护一份
prompt、且 cross-encoder 本身就是为这件事训练的。**不做。**

#### 与其它项的联动

- **优化项 A（低置信短路）在 rerank 之前**：低置信 query 直接短路，不进 rerank，不为"库里没有"的问题付钱
- **A 还顺带压低 rerank 总成本**：$0.0025/次听起来小，但台账那次实测模型一轮自主调了 4 次 = **$0.01/轮**；A 把重试掐掉后回到 1~2 次
- **D（HyPE）先上更好**：rerank 的输入质量取决于 top-10 候选的质量，先把召回做准再重排，收益不重叠

#### ⚠️ 验收不能只看路由准确率：seed 是图扩展的起点，错误会被放大

rerank 选出的 3 个 seed 同时是阶段 2 图扩展的**出发点**，所以它的影响是双向放大的：

- **收益放大**：seed 更准 → 图扩展从对的节点出发 → 前置项 / 输入源跟着对
- **风险放大**：seed 选错 → 图扩展从错的节点出发 → **连带前置项全错**，而且错得"看起来有理有据"
  （带着依赖关系的错误答案比单纯召回错更有说服力，更难被用户察觉）

因此 rerank 的验收除了跑金标看 r@1/r@3，**必须抽查几个 case 确认前置项没变成无关内容**。

---

## 8. 优化项 F：跨调用 pid 去重 🟢 无需基线

台账「多轮检索累计灌给模型 5 万字符」条已正确指出**不能靠降 top_k 解决**（排第 3 的 `kpi-dashboard-creation` 恰是唯一带 `inputs` 的那本，降到 2 就丢了核心价值），该控的是**累计量**。

### 改法

per-turn 状态放 LangGraph `ChatState` 加一个 `playbook_seen_pids: set[str]`，工具执行层读写：

```
第 2 次及以后命中同一 pid
  → 不重复灌 body 摘录（约 4200 字符）
  → 只回一行 "已在上文提供：cash-flow-forecast（Executive）"
```

扩展节点的简介同理去重。按「多轮检索累计 5 万字符」那次实测的重叠情况估计能省 20~30%。

⚠️ 与优化项 A 叠加后，那次 52769 字符的四连问预计降到 10000 字符量级。

### 子项 F2：单次调用内的预算不公（顺手一起修）

上面治的是**跨调用累计**，还有一个**单次调用内**的分配问题：

```python
budget = _MAX_EXCERPT_CHARS      # 16000，在 for hit 循环【外面】初始化
for hit in hits:
    for text in excerpts.get(...):
        if budget - len(text) < 0: break
        budget -= len(text)
```

预算**跨 3 个 seed 共享、先到先得**。现在 3 × 3 × 1142 ≈ 10.3k 字符吃不满 16k，所以看不出来；
但某本手册的段偏长时，**排第一的 seed 会挤掉后面 seed 的正文**，排第 3 的只剩 title + 简介。

这条同时解释了 §1 里"r@1 的真实意义"：排第几不只影响模型的注意力，还**直接决定能不能分到
足额正文**。改法是把预算改成 per-seed（`16000 // len(hits)`），或给每个 seed 保底一段。

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
| 给 `metadata->>'chunk_kind'` 建 GIN 索引 | HyPE 后候选从 63 涨到约 570 行，会有人想加这个索引。v2 §4.3 已论证不必：`entry_id` 索引已把候选收窄到单版本几百行，在其上筛 chunk_kind 是内存过滤，0.9 ms 不值得为它加一个索引维护面 |

---

## 10. 排期与依赖

```
✅ 已完成                  0. 评测基线 + baseline-v2.json

现有金标即可验收 ─────────> D-1  HyPE 第一步：拆现有 5 条问法（零 LLM 成本）← 主项
                           C    检索词形态对齐（⚠️ 脚本同一提交内同步改）
                           E    rerank（openrouter / cohere/rerank-4-pro）

需先建无泄漏金标 ─────────> D-2  HyPE 第二步：扩写到 8~10 条   ← ✅ 金标已就绪（2026-08-24）

无依赖，可立刻做 ─────────> A    低置信短路（1h）← 单项 ROI 最高
                           F    pid 去重 + 预算不公（0.5d）

顺手做掉，不单独排期 ─────> B    阶段 2/3 并发（收益 <5%）
```

| 序 | 项 | 成本 | 主要收益 | 需基线 |
|---|---|---|---|---|
| 1 | **A 低置信短路** | 1h | context −60%，不再硬答，顺带产出覆盖缺口清单 | 否 |
| 2 | **F pid 去重 + 预算不公** | 0.5d | context 再 −20~30%；排第 3 的 seed 不再分不到正文 | 否 |
| 3 | **D-1 HyPE 拆现有 5 条** | 1d | **路由准确率的主要增量**，零 LLM 成本 | 现有金标够 |
| 4 | C 形态对齐 | 0.5d | 修掉 query↔索引 形态错配 | 现有金标够 |
| 5 | E rerank（`cohere/rerank-4-pro`） | 0.5d | 概念性主题；⚠️ 含 llm 模块加 openrouter+rerank 薄叶子 + config 分支 + pricing 补 per-search 价目 | 现有金标够 |
| 6 | ~~无泄漏金标（正文出题）~~ **✅ 2026-08-24 完成** | 0.5d（实际 ~1d，含三视角审查） | 解锁 D-2；给出无泄漏口径 r@3 82.6% / usable@3 75.6%（**不是"真实水平"**，读法见 §2） | — |
| 7 | D-2 HyPE 扩写问法 | 0.5d | 覆盖更多表达 | **要新金标** |
| — | B 阶段并发 | 1h | 收益 <5%，动 `search()` 时顺手 | 否 |

---

## 11. 待确认

| # | 议题 | 选项 |
|---|---|---|
| ~~1~~ | ~~优化项 C 走改 docstring 还是双检索词~~ | ✅ **已定：双检索词**（2026-08-10）。理由是不赌形态、两路都覆盖，且 `keywords` 留空即退化为单路、灰度成本为零。见 §5 |
| ~~2~~ | ~~优化项 D 的扩写范围~~ | ✅ **已定：全量 63 本**（2026-08-10）。§6 风险 2 里"先做 20 本概念型试点"的缓解方案随之作废——质量把关改为**全量扩写 + 人工审 diff**，与关系推断同一套闸门 |
| ~~3~~ | ~~优化项 D 的问法存哪~~ | ✅ **已定：新增 `expanded_questions` 列**（2026-08-10）。不复用 `questions`（它同时喂 profile 文本 / 审核页 / diff 逐字段 / attrs 指纹四处，混进去会稀释 profile 且让 diff 分不清源站改版与 LLM 噪声）；也不"只存向量库"（审核看不到，而问法质量正是本项主要风险）。审核负担用**缓解 a** 化解：diff 只报计数、不逐条列。见 §6 |
| ~~4~~ | ~~优化项 A 的阈值 0.45~~ | ✅ **已定：先按 0.45 上线，跑一段真实流量后再调**（2026-08-10）。不预先跑金标分布——金标是"让它找自己"的上界，它的分数分布比真实 query 高，拿它定阈值会定得偏高、把正常命中掐掉。改为上线后按 `coverage: low` 的日志回看真实分布。<br>✅ **已按此校准一次：0.45 → 0.50**（2026-08-12，v5 发布后 10 题线上口径实测，库里有的 ≥0.5804 / 库里没有的 ≤0.4854，取缝中偏下）。⚠️ 校准时又多一条口径要求：**必须用线上口径**（模型改写后的问句 + 术语路），拿用户原话直喂检索会得出相反结论，见 §3 与测试用例文档 §0.3 |
| ~~5~~ | ~~优化项 E 走 rerank 还是 LLM 选~~ | ✅ **已定：OpenRouter 上的 `cohere/rerank-4-pro`**（2026-08-11）。E2（LLM 选）已否——延迟高 3~6 倍、多维护一份 prompt、cross-encoder 本就是为这件事训练的。⚠️ 留一个待验证：请求体字段名 / `results[].index` 语义 / 响应有没有 `usage.cost`，**上线前拿 key 实调一次**（见 §7） |
| ~~6~~ | ~~评测脚本是否恢复~~ | ✅ **已定并完成**（2026-08-10），见 §2 |
| ~~8~~ | ~~无泄漏金标怎么建~~ | ✅ **已定并完成**（2026-08-24）。两处偏离本文原方案：**正文读库不读 `playbooks_bodies.json`**（那份是旧源站快照，会把"源站改版"混进差值）、**出题量按正文长度分配**（短正文只出 3 条，否则产同义题）。同时确认**旧口径已饱和**（r@3 100%），此后不可再用。详见 §2 |
| ~~7~~ | ~~阶段 3 的"第一段固定带"是否保留~~ | ✅ **已定：保留现状，本期不动**（2026-08-11），降级为观察项。<br>背景：`fetch_excerpts` 固定带 body 第一段，原理由是"它是 Players / Effort / Frequency 元数据块，等于用 0 成本换掉两个数据库列"。但 2026-08-10 查库，这几个关键词在 63 个 entry 的第一段里**全部 0/63**（`Initial Effort` 在全部 body 分段里也是 0/63），现在第一段是开篇散文——**理由失效，但效果未必变差**：开篇段是"这本手册解决什么问题"的主题铺垫，本身有价值。<br>⚠️ **纠正本文早先的一处不准确**：曾写"可用现有金标量化"，其实**量不到**——评测脚本只跑 `route()`（阶段 1），摸不到 `fetch_excerpts`（阶段 3）；且现有 315 题的答案是"哪本手册"，不是"哪一段"。真要量化需另出一套段落级金标 + 人工对比三种配置（保留 / 不固定 / 配额加到 4 段），属答案质量评测，成本远高于收益。<br>另两个选项各自的代价：**改成不固定** → 丢掉主题铺垫，模型可能只看到中段细节；**配额加到 4 段** → 每 seed 3.4k → 4.5k 字符、3 seed 约 13.7k，与优化项 A / F 压 context 的方向对冲。真要做，等 A / F 落地、context 降下来之后再评估。<br>这件事**不影响路由**（元数据块从不进 profile 文本），也不影响 `category` / `stage`（`_meta_field` 单独解析、都健在）；连带暴露的校验缺口已转台账「ingest 缺"字段级静默变空"校验」 |
