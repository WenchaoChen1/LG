# Playbook 召回优化 手工测试用例（优化项 A / B / C / D-1 / E）

> 关联文档：
> - 本轮改动的权威设计：[../开发设计/playbook-recall-optimization-dev-design.md](../开发设计/playbook-recall-optimization-dev-design.md)（A=§3、B=§4、C=§5、D=§6、E=§7）
> - 现行检索链路：[../开发设计/playbook-chatbot-integration-dev-design.md](../开发设计/playbook-chatbot-integration-dev-design.md)（§3.1 profile 配方 / §5 检索四阶段）
> - 工具入参与返回契约：`../../../python/CIOaas-python/docs/AI-Chatbot/chatbot-tools-v2-interface.md`（自动生成）
>
> 阶段：⑦ 测试用例 ｜ 日期：2026-08-11（v5 发布 + 聊天页八题实测后大幅修订 2026-08-12；**同日按 §0.3.2 结论把覆盖阈值 0.45 上调 0.50**）｜ 端：Python（CIOaas-python）+ 前端聊天页
>
> 范围：**只覆盖本轮五项改动**（低置信短路 / 阶段并发 / 双检索词 / 每问一向量 / 精排），
> 不重复 playbook 既有功能（crawl / ingest / activate / 审核页）的用例。
> 文档里每一个**带数字的预期**都是 2026-08-11 / 08-12 **实测得到的**，不是推断——若你测出不同的
> 数字，先怀疑环境（版本、开关、库数据），再怀疑代码。⚠️ **务必分清两种口径**：脚本口径（把
> 用户原话直接喂进检索）与**线上口径**（模型改写的问句 + 它自造的术语路），两者分数差一个
> 数量级，混用会得出完全错误的结论——§0.3 就是这么翻过一次案的。
> 少数"预期"是行为约定而非数值（如 §2.5 逼模型一轮多查、TC-12 的话术红线），已在各处注明。

---

## 0. ⚠️ 测试前必读

### 0.1 版本现状（v5 已于 2026-08-12 11:30 发布）

| 版本 | 状态 | 分段构成 | 说明 |
|---|---|---|---|
| **v5** | **ACTIVE**（线上/UI 读的就是它） | profile 63 + **question 315** + body 276 = 654 | D-1 产出，**已发布** |
| v2 | ARCHIVED | profile 63 + body 276 | **没有问法向量**，即 D-1 之前的库；行一条没删，仍可按版本测 |
| v1 / v3 / v4 | ARCHIVED / DRAFT | — | 历史版本，本文档不涉及 |

**所以 §2 / §3 里标【V5】的用例现在可以直接在聊天页做**，不需要任何额外准备。
发布后已核实（不传 version 走 ACTIVE 路径）：board 问题命中 `board-of-directors` 0.646、
`account-management-process` 经 rerank 排第 2、库外的 printer 问题仍 `coverage=low` 0.264
—— **D-1 + A + E 三项都在线上生效**。

标【V2】或【V2 + V5】的用例（TC-03 / TC-04）走 §5.3 的脚本按版本测：playbook 检索**没有
HTTP 端点**（十个维护端点里没有 search；通用 `POST /api/ai/rag/recall` 已把 PLAYBOOK 空间
排除），而聊天工具永远读 ACTIVE，所以"读 ARCHIVED 版本"只能从 service 直调。

> **回滚**：`POST /api/ai/rag/playbook/versions/2/activate` 即可切回，v2 的 339 条分段一行没动，
> 零向量操作、毫秒级。

### 0.2 发布 v5 前后的对照（当初为什么这一步是前提）

同一批问题在两个版本上的 top-1 相似度（关 rerank 实测）：

| 问法形态 | 例子 | v2 top-1 | v5 top-1 | v2 上的结果 |
|---|---|---|---|---|
| **书面问法**（≈ 索引里的 Key questions 原文） | `How do I build an accurate cash flow forecast?` | 0.722 | 1.000 | 正常命中 |
| | `When should I form a board of directors?` | 0.705 | 1.000 | 正常命中 |
| | `What should my account management process cover?` | 0.767 | 1.000 | 正常命中 |
| **口语化问法**（真实用户就是这么问的） | `what should the board see every month` | **0.415** | 0.646 | **被短路** |
| | `how many months of runway do we have left` | **0.335** | 0.536 | **被短路** |
| | `our deals stall halfway through, where should we look` | **0.360** | 0.597 | **被短路** |
| | `who owns the customer relationship after the deal closes` | **0.443** | 0.485 | **被短路** |

**结论有两层，都要知道**：

1. **在 v2 上，用户随口问的问题几乎全部低于覆盖阈值 → 被优化项 A 短路 → 一本手册都不返回。**
   这就是为什么发布 v5 之前，"检索质量"测试得到的几乎只有"库里没有这个主题"，C / E / F1 的效果
   一个都测不出来。**现在 v5 已发布，这一段只作为对照留档。**
2. **优化项 A 的阈值与 D-1 是耦合的**：0.45 是按**改造前**的分数分布定的（那次"确实没覆盖"
   的全场最高 0.442），而改造前**合法的口语化命中也落在 0.33~0.44** —— A 会把它们一起吃掉。
   D-1 把合法口语化命中抬起来之后，阈值才站得住；**阈值也随之在 2026-08-12 上调到 0.50**（依据
   见 §0.3.2，那是线上口径的实测）。
   > ⚠️ 这一条是本轮测试发现的、**设计文档两节都没预料到的耦合**：若日后回滚到 v2，
   > **A 的阈值必须一起往下调**（0.50 在 v2 上会把 8 条口语化问题里的 7 条全吃掉），
   > 否则口语化问题会被整片吃掉。

⚠️ v5 上书面问法的 **1.000 是逐字命中**（问法原文成了独立一行 chunk），这也是评测脚本报
r@1 99.7% 的原因，**那个分数是泄漏、不是质量**。判断真实水平要用口语化问法（本文档给的就是）。

### 0.3 ⚠️ 阈值：用户原话口径下重叠，**线上真实口径下可分**

> ✅ **本节结论已落地：阈值 0.45 → 0.50（2026-08-12，`playbook_service.COVERAGE_THRESHOLD` 一行常量）。**
> 采纳的是 §0.3.3 的候选方案 1；方案 2（rerank 分作覆盖信号）与方案 3（D-2）**均未做**。
> 下文各处"现阈值"一律指 0.50，写着 0.45 的地方都已标明是**旧阈值 / 历史判定**。
>
> **本节 2026-08-12 经聊天页实测大幅修正。** 下面 §0.3.1 那张表（17 个问题）测的是
> **把用户原话直接喂进检索**，而线上进检索的从来不是原话——模型会先把它改写成正式问句、
> 再补一路术语。两种口径的分数差到一个数量级，据前者做的判断几乎全部不成立。
> **先看 §0.3.2 的线上口径结论，§0.3.1 只作为"为什么不能用原话口径定阈值"的反例留档。**

#### 0.3.1 原话口径（❌ 已知口径错误，留档）

用 §5.3 的脚本在 **v5** 上跑了 17 个问题（8 条合法 + 9 条库外），按 top-1 分数排序：

| top-1 | 问题 | 库里有对应手册？ | A 的判定 | 对不对 |
|---|---|---|---|---|
| 0.680 | how should we decide what to charge for each tier | 有（pricing-matrix） | 命中 | ✅ |
| 0.646 | what should the board see every month | 有（board-of-directors） | 命中 | ✅ |
| 0.597 | our deals stall halfway through… | 有（pipeline-management-and-review） | 命中 | ✅ |
| 0.536 | how many months of runway do we have left | 有（cash-flow-forecast） | 命中 | ✅ |
| 0.506 | which customers look like they are about to leave us | 有（churn-identification-process） | 命中 | ✅ |
| ← **现阈值 0.50**（2026-08-12 上调） |  |  |  |  |
| 0.485 | who owns the customer relationship after the deal closes | 有（account-management-process） | 命中（但排错了，靠 E 救） | ⚠️ |
| **0.484** | what's our office lease renewal process | **没有** | 命中 contract-register | **❌ 放过了** |
| **0.465** | how do we run our employee 401k plan | **没有** | 命中 employee-agreement | **❌ 放过了** |
| **0.465** | how do I renew my passport | **没有** | 命中 license-register | **❌ 放过了** |
| ← 旧阈值 0.45 |  |  |  |  |
| **0.444** | we need to plan next year spending | **有**（budget-creation） | **短路** | **❌ 误杀** |
| **0.395** | we want a one page view of our key numbers | **有**（kpi-dashboard-creation） | **短路** | **❌ 误杀** |
| 0.360 | how should we pick a coffee supplier for the office | 没有 | 短路 | ✅ |
| 0.310 | which laptop should I buy for my new designer | 没有 | 短路 | ✅ |
| 0.286 | what should we serve at the company holiday party | 没有 | 短路 | ✅ |
| 0.264 | how do I fix the printer on the second floor | 没有 | 短路 | ✅ |
| 0.259 | how do we set up the office wifi | 没有 | 短路 | ✅ |
| 0.223 | what's the weather going to be like next week | 没有 | 短路 | ✅ |

「A 的判定 / 对不对」两列是**按旧阈值 0.45** 判的：这个口径下 0.395~0.484 是重叠区间，
"误杀 2 个 + 放过 3 个"，看起来调阈值两头都得罪。**这个结论已被 §0.3.2 推翻**——它的前提
（用户原话就是检索词）是错的。

⚠️ 顺带说明**换成 0.50 后这张表会怎么变**（仍是原话口径，仅供理解上调的代价）：0.485 / 0.484 /
0.465 / 0.465 四行一起落到线下 → **放过 3 个变 0 个，误杀 2 个变 3 个**（多误杀 0.485 那条
`account-management-process`）。看着更差，但**这正是"用原话口径评估阈值"的失真**：同一条问题
线上口径是 0.5804、稳稳在线上。别拿这张表反推阈值该定多少。

#### 0.3.2 ✅ 线上真实口径（聊天页实测，2026-08-12）

线上进检索的是**模型改写后的问句 + 它自己造的术语短语**，不是用户原话。八题实测（§2.1）：

| 问题（用户原话） | 原话口径 | **线上口径** | 命中 | 抬升 |
|---|---|---|---|---|
| which customers look like they are about to leave us | 0.506 | **0.7710** | churn-identification-process | +0.265 |
| how should we design a KPI dashboard…（换题后） | 0.395（原题） | **0.7600** | kpi-dashboard-creation | +0.365 |
| how should we decide what to charge for each tier | 0.680 | **0.7388** | pricing-matrix | +0.059 |
| what should the board see every month | 0.646 | **0.6628** | board-of-directors | +0.017 |
| our deals stall halfway through… | 0.597 | **0.6481** | pipeline-management-and-review | +0.051 |
| we need to plan next year spending | **0.444（被短路）** | **0.5980** | budget-creation | **+0.154** |
| who owns the customer relationship after the deal closes | 0.485 | **0.5804** | account-management-process | +0.095 |
| ── 合法问题下界 0.5804 ──────────────── |  |  |  |  |
| ── **空隙 0.49 ~ 0.58** ──────────────── |  |  |  |  |
| ── 库外问题上界 0.4854 ──────────────── |  |  |  |  |
| what's our office lease renewal process | 0.484 | 0.4854 | contract-register ❌ | +0.001 |
| **how do we run our employee 401k plan** | 0.465 | **0.4726**（真实模型产出） | employee-agreement ❌ | +0.008 |
| how do I renew my passport | 0.465 | 0.4676 | license-register ❌ | +0.003 |
| printer / wifi / weather / coffee / laptop / party | 0.22~0.36 | — | 短路 ✓ | — |

⚠️ **抬升的机制有一半是"巧合"，别当泛化能力**：实测三次看到模型改写后的问句**几乎逐字命中**
索引里的某条问法，分数直接冲到 0.93~0.99（`cash-flow-forecast` 0.9870、`pipeline-creation` 0.9327、
书面问法那组 1.000）。也就是说线上高分里，一部分来自"模型把口语整理成正式问句 → 恰好逼近源站
问法的措辞"这条链路，而不只是"问法向量覆盖面更广"。**换个措辞习惯不同的模型，这份收益可能缩水。**

**关键是不对称**：合法问题涨 0.02~0.37，库外问题只涨 0.001~0.008（**术语路对库外问题零贡献**——
`LEAST(两路)` 里始终是问句那一路更近）。说得通：合法问题能涨，是因为库里**真有**一条贴合的
问法在等它；库外问题涨不动，是因为怎么改措辞都只能攀在"沾边手册"的相似度天花板上。

于是两类之间出现 **0.4854 ~ 0.5804 的空隙**，从"重叠两难"变成"可分"：

```
合法（线上）  0.580  0.598  0.648  0.663  0.739  0.760  0.771     全部 ≥0.58
──────────────── ✅ 现阈值 0.50（2026-08-12 上调）────────────────
库外（线上）  0.4676  0.4726  0.4854                              全部 ≤0.49
──────────────── 旧阈值 0.45 ────────────────
库外远题      0.22 ~ 0.36
```

**取 0.50 而不是 0.52**：缝的下沿（库外上界 0.4854）只差 0.0146，而 rerank/embedding 都有
±0.005 量级的运行间抖动；0.50 离上沿 0.5804 有 0.08 的余量、离下沿有 0.015，是"先保不误杀"的
偏保守取法。要往 0.52 再走一步，得先有真实流量证明缝的下沿稳定（§6 第 1 条）。

**三条原判断随之作废**（都写在 §0.3.1 里，别再引用）：

1. ~~误杀 2 个合法问题~~ → **0 个**：0.444 那条被 C 抬到 0.598；0.395 那条**是题目本身有歧义**
   （"想看我们的关键数字"是取数请求，模型确实去取了真实财务数据、压根没调 playbook。问法改成
   "how should we design a KPI dashboard…"后同一手册轻松拿 0.75）。
   > ⚠️ 连带作废：§0.3.1 说 0.395 证明"问法覆盖面不足、是 D-2 的目标案例"——**D-2 因此
   > 失去了唯一的实测依据**。
2. ~~调阈值两头都得罪~~ → **可以单向调高**（0.50~0.52 不误杀任何合法问题、拦掉那三条库外）。
3. **"放过"的代价是浪费、不是答错**：401k 实测 A 没拦住（0.4726），但模型拿到三本手册摘录后
   自己判断"这些跟 401k 无关"，如实答"知识库和方法论库都没有这个主题、不猜"。代价是白灌
   约 3×1100 字符摘录 + $0.0025 rerank + 约 1.5 秒。⚠️ 这是 sonnet 的表现，**换更弱的模型
   未必兜得住**，且白灌摘录本身就违背 A 立项时"省 context"的目标。

⚠️ **阈值已按此上调 0.50，但支撑它的证据仍然薄**，三条限制照旧成立、**上线后要接着盯**：
① 合法 7 条 + 库外 3 条，只有 10 个点撑着那道 0.095 的缝；② 库外三条里只有 401k 是真实模型产出，
另两条的 question/keywords 是按 6 个真实样本**人工仿写**的（401k 仿写 0.4760 vs 实测 0.4726，
误差 0.003，模式可信但毕竟不是原件）；③ 上调必然牺牲"库里只有远房相关手册、给个参考也比不给好"
的场景——**这是产品取舍**，若产品认为"宁可给个沾边的"，把常量调回去即可（一行）。
按 §6 第 1 条继续采真实流量：**重点是落在 0.49~0.58 这道缝里的 query**，它们决定阈值往哪边动。

### 0.3.3 那要靠什么拦？—— 三条候选方案与各自代价

先排除一个直觉：**rerank 拦不住**。实测 §2.4 那三条库外问题开了精排后照样各返回 3 本手册，
只是换了个"沾边的"排第一（`vendor-contract-register` 顶掉 `contract-register` / `license-register`）
—— 因为 `_rerank_seeds` 永远返回 top_k，**cross-encoder 在我们的接线里没有"都不相关"这个出口**。

但**它给的相关性分本身是个远好于向量分的信号**。跨阈值两侧各取三条实测
（`--set signal --versions 5 --coverage-signal`，2026-08-12）：

| 类型 | 向量 top-1 | **rerank 最高分** | rerank 选的第一名 |
|---|---|---|---|
| 库里有 · plan next year spending | **0.444**（被 A 误杀） | **0.8023** | ✅ `budget-creation` |
| 库里有 · one page view of key numbers | **0.395**（被 A 误杀） | **0.7384** | ✅ `kpi-dashboard-creation` |
| 库里没有 · office lease renewal | **0.484**（越阈） | 0.5289 | vendor-contract-register |
| 库里有 · months of runway | 0.536 | 0.5211 | ✅ cash-flow-forecast |
| 库里没有 · employee 401k plan | **0.465**（越阈） | 0.4471 | employee-agreement |
| 库里没有 · fix the printer | 0.264 | 0.3753 | support-ticket-system |

**两个被 A 误杀的合法问题，rerank 分是全场最高的两名（0.80 / 0.74），而且都选对了手册**——
cross-encoder 知道这两个主题库里有，bi-encoder 不知道。分层对比：

```
向量分排序：  0.536有  0.484没  0.465没  0.444有  0.395有  0.264没   ← 交错严重
rerank 排序： 0.802有  0.738有  0.529没  0.521有  0.447没  0.375没   ← 只有一处交错
```

同一批 6 条（**原话口径**）：**向量阈值 0.45 → 2 误杀 + 2 放过；上调 0.50 → 2 误杀 + 0 放过；
rerank 阈值取 0.60 → 1 误杀 + 0 放过。**（上调只治"放过"、治不了这两条误杀——但那两条误杀
在线上口径下并不存在，见 §0.3.2 第 1 条。）

**优先级按 2026-08-12 的线上口径实测重排**（此前的排序基于已作废的原话口径）：

| 优先级 | 候选方案 | 效果 | 代价 |
|---|---|---|---|
| ~~**1**~~ | ✅ **已做（2026-08-12）：把向量阈值从 0.45 提到 0.50** | §0.3.2 实测：不误杀任何合法问题（下界 0.5804），拦掉那三条库外（上界 0.4854） | **改一行常量**；牺牲"远房相关手册也有点参考价值"的场景 |
| 2 | 改用 rerank 分作覆盖信号 | 本节样本上分层更好 | 必要性**已大幅下降**（向量分在线上口径下已够分）；且要把 A 的短路移到 rerank 之后，与设计 §7「不为库里没有的问题付钱」直接冲突，库外问题也要付 $0.0025 + 约 1.7s |
| 3 | D-2（LLM 扩写问法） | 覆盖更多表达 | ingest +95s、审核负担、需先建无泄漏金标；**唯一的实测依据（0.395）已被证伪**——那条是题目歧义、不是问法覆盖面不足 |

⚠️ **方案 2 / 3 别急着做**（方案 1 已做，它只改一行常量、可随时回退，所以不受下列理由约束；
方案 2 要改短路时序 + 库外问题也付费，方案 3 要重跑 ingest + 重建金标，都是不可轻易回退的），
四个理由：

1. **只有 6 个样本，且已有一处交错**：合法的 `runway` 只有 0.5211，而库外的 `office lease` 是
   0.5289 —— **库外的反而更高**。rerank 分也不是干净的分隔器，只是比向量分好。
2. 这些问题全是**人工构造**的（§0.3.1 的 17 条 + 本节 6 条），不是真实流量。按 §6 第 1 条把真实
   query 攒够再决策。
3. rerank 分有 **±0.005 量级的运行间抖动**（printer 两次跑出 0.3790 / 0.3753），定阈值时别抠小数点。
4. **本节这张表也是原话口径**（`--coverage-signal` 直接喂原话）。线上口径下 rerank 分会怎么变，
   还没测——所以方案 2 的"分层更好"这个论据同样有口径问题，别拿它对比方案 1。

### 0.4 前端开关

前端 `+` 菜单的 **Playbook 开关必须打开**（per-turn、opt-in）。关着的话取数轨**不绑定**
`search_playbooks`，模型看不见它，会直接用通用知识回答——很容易误判成"检索坏了"。

---

## 1. 用例 × 版本 速查表

**v5 已是 ACTIVE**，所以下表【V5】= 直接开聊天页测，不需要任何准备。

| 用例 | 测什么 | 版本 | 怎么做 |
|---|---|---|---|
| TC-01 | A 低置信短路：库外主题 | **V5** | ✅ 聊天页 |
| TC-02 | A 短路仍写召回记录 | **V5** | ✅ 聊天页 + 一条 SQL |
| TC-03 | A 阈值与 D-1 的耦合（v2/v5 对照） | **V2 + V5** | ⚠️ §5.3 脚本（v2 已 ARCHIVED，只能脚本读） |
| TC-04 | D-1 口语化问法能不能召回 | **V2 + V5** 对照 | ⚠️ 同上 |
| TC-05 | D-1 数据完整性（654 段） | **V5** | ❌ 纯 SQL |
| TC-06 | D-1 观测红利：哪条问法被命中 | **V5** | ❌ 纯 SQL |
| TC-07 | E 精排改善概念型/意图型问题 | **V5** | ✅ 聊天页（关开关需重启，见用例） |
| TC-08 | E 精排不污染前置项（铁律） | **V5** | ✅ 聊天页 |
| TC-09 | E 失败降级 | **任一** | ⚠️ 需改配置模拟 |
| TC-10 | C 模型是否真填 `keywords` | **任一** | ✅ 聊天页 + 看日志 |
| TC-11 | F1 同一轮不重复灌正文 | **V5** | ✅ 聊天页 |
| TC-12 | 工具契约红线（不冒充客户资料 / 不吐 pid） | **V5** | ✅ 聊天页 |
| TC-13 | 延迟观感（非缺陷确认） | **V5** | ✅ 聊天页 |

**一句话记法**：**只有"与旧库对照"那两条（TC-03 / TC-04）要走脚本，其余直接在聊天页测。**

### 1.1 发布后要盯什么（2026-08-12 聊天页实测后改写）

> 这一节原本列了"两类线上可见错误"（合法问题被误判成库里没有 / 库外问题被沾边手册硬答），
> 依据是 §0.3.1 的原话口径。**八题实测把两条都推翻了**，原文已删——留这句话是为了让看过旧版
> 的人知道结论变了。

| 要盯的 | 现状（实测） | 怎么处理 |
|---|---|---|
| **合法问题被误判成"库里没有"** | **未发生**（阈值 0.45 时代的实测）。七题线上分数 0.58~0.77；**阈值上调 0.50 后余量从 0.13 缩到 0.08**，Q4（0.5804）是离线最近的一条 | 这是上调阈值后**最该盯的一项**：真碰到了按 §6 第 1 条记**原文 + 线上 top1**（用 §5.4 脚本读）；连着出现两三条就把常量调回 0.45~0.48 |
| **库外问题被沾边手册硬答** | 阈值 0.45 时**A 确实没拦住**（401k 0.4726 越阈），靠模型自己兜住、如实答"库里没有"；**0.50 之后这三条应当都被短路了** | 复测那三条（§2.4）确认变成 `coverage=low`；若仍有沾边手册被硬答，记账（详见 §8 第 9 条） |
| **rerank 反而把正确手册压下去** | **已发生**：Q4 上 `account-management-process` 本来是第 1（0.5804），rerank 把 `contract-playbook`（0.4687）顶到第 1 | 用 `--isolate` 逐题记胜负（§6 第 3 条）。这是目前**唯一收益不明**的一项 |
| **模型压根不调 playbook** | **已发生**：取数意味明显的问题会被路由到 `get_companies` / `get_financials` | 正确行为。但核对时要确认脚本读到的是本轮记录（§5.4 的 ⚠️） |

**阈值已在 2026-08-12 从 0.45 调到 0.50**（§0.3 的候选方案 1，一行常量、可随时回退）；
**别再自行往上调、别关 rerank**——两件事都要等 §6 那三份数据攒够。

---

## 2. 测试问题清单（直接复制去问）

### 2.1 口语化问法 —— 主力测试集【V5】

这组是**真实用户口吻**，也是本轮所有改动的价值所在。**"线上实测"列是 2026-08-12 在聊天页
真问一遍的结果**（模型改写 + 术语路 + rerank 全在内），照它对；旁边两列是脚本口径的对照，
说明"拿原话直接检索"低估了多少。

> ⚠️ **选题准则（两次踩坑总结出来的，加题前先过一遍）**：
> **问"这件事该怎么做"才会走 playbook；问"我们的数字是多少"会被路由到取数工具。**
> 判据是主语与诉求——"**我们**还剩几个月现金"、"想看**我们的**关键数字"问的是自家数值，
> 模型会去调 `get_companies` / `get_financials`，**压根不碰 `search_playbooks`**（实测两次，
> 见下表 Q2 与原 Q7）。这种题**测不到本轮任何改动**，而且不看工具清单还会误以为测过了。

| # | 问题（照抄去问） | v2 原话 | v5 原话 | **v5 线上实测** |
|---|---|---|---|---|
| Q1 | `what should the board see every month` | 短路 0.415 | 0.646 | **0.6628 ✓ board-of-directors** ← 设计 §5 招牌案例（旧库排第 9） |
| **Q2** | ~~`how many months of runway do we have left`~~ **无效题**（取数请求）：实测走 `get_companies`×2 + `get_financials`，**playbook×0** | 短路 0.335 | 0.536 | — |
| Q2′ | `how should we forecast our cash runway` | — | 0.5+ | 待测 |
| Q3 | `our deals stall halfway through, where should we look` | 短路 0.360 | 0.597 | **0.6481 ✓ pipeline-management-and-review**；`sales-funnel-creation` 靠 E 进第 2 |
| Q4 | `who owns the customer relationship after the deal closes` | 短路 0.443 | 0.485（**阈值 0.50 后也短路**） | **0.5804 ✓ account-management-process**（rerank 把它压到第 2，见 TC-07） |
| Q5 | `which customers look like they are about to leave us` | 短路 0.338 | 0.506 | **0.7710 ✓ churn-identification-process** |
| Q6 | `we need to plan next year spending` | 短路 0.401 | **短路 0.444** | **0.5980 ✓ budget-creation** ← 原话口径下被误杀，线上没有 |
| **Q7** | ~~`we want a one page view of our key numbers`~~ **已换题**，见下 | 短路 0.375 | 短路 0.395 | — |
| Q7′ | `how should we design a KPI dashboard for the leadership team` | — | 0.7466 | **0.7600 ✓ kpi-dashboard-creation** |
| Q8 | `how should we decide what to charge for each tier` | 0.562 | 0.680 | **0.7388 ✓ pricing-matrix** |

**七题（Q1/Q3/Q4/Q5/Q6/Q7′/Q8）全部命中预期手册，线上分数 0.58~0.77，零短路。**
这是 D-1 的核心收益证据（比金标那个 +10.2pt 可信——后者是逐字泄漏）。

⚠️ **三条使用须知**：

1. **Q1 / Q2 不能用来验 C（TC-10）**：它们的主题恰好就是我写在工具 docstring 里的两个
   `keywords` 示例（`board reporting monthly metrics` / `cash flow forecast runway model`），
   模型会**逐字照抄示例**——Q1 与 Q20 第 1 次调用实测都是原样抄的。验 C 要看 Q3~Q8
   （那些主题不在示例里，实测模型全部自造了术语短语）。
2. **原 Q7 与 Q2 都被换掉了，同一个原因**：字面是**取数请求**而不是方法论请求。实测模型据此去调
   `get_companies` / `get_financials`（原 Q7 还生成了一份真实财务概览）、**压根没调
   `search_playbooks`**。**模型的判断比原题的期望更对**——是题目错了，不是模型错了。
   → 这也是 §0.3.1 那个"0.395 = 问法覆盖面不足"结论被推翻的原因：问法一改明确，同一手册就是 0.75。
3. **核对时必须看"这一轮调了哪些工具"**，不能只看最近一次 playbook 调用——上面两道无效题都会让
   `--nth 1` 读到**上一题的记录**，看起来像测过了。§5.4 的脚本会打时间戳与 question，对不上就是没调。
4. ⚠️ **「v5 原话」那一列在阈值 0.50 下会多两条短路**：Q4（0.485）与 Q5（0.506，只高出阈值 0.006）
   —— 前者变短路、后者贴着线。**这只影响 §5.3 的脚本（原话口径）**，聊天页不受影响（两题线上
   分别是 0.5804 / 0.7710）。拿脚本跑 §2.1 时别把这个当回归。

### 2.2 书面问法 —— 只用于 v2/v5 对照【V2 + V5】

| # | 问题 | v2 | v5 |
|---|---|---|---|
| Q9 | `How do I build an accurate cash flow forecast?` | 0.722 命中 | 1.000 命中 |
| Q10 | `When should I form a board of directors?` | 0.705 命中 | 1.000 命中 |

### 2.3 库外主题 —— 验短路【V5】

⚠️ **选题比想象的难**：D-1 之后分数整体抬高，"沾点边"的问题会攀上相邻手册越过阈值。
下面这批**实测在 v5 上 ≤0.36**，离阈值（0.50，旧 0.45）都很远，可放心用：

| # | 问题 | v5 实测 top-1 |
|---|---|---|
| Q11 | `how should we pick a coffee supplier for the office` | 0.360 ✓ 短路 |
| Q12 | `which laptop should I buy for my new designer` | 0.310 ✓ 短路 |
| Q13 | `what should we serve at the company holiday party` | 0.286 ✓ 短路 |
| Q14 | `how do I fix the printer on the second floor` | 0.264 ✓ 短路 |
| Q15 | `how do we set up the office wifi` | 0.259 ✓ 短路 |
| Q16 | `what's the weather going to be like next week` | 0.223 ✓ 短路 |

### 2.4 near-miss —— **离阈值最近的库外样本**，阈值余量的观测点【V5】

这三条**库里确实没有**。它们越过了**旧阈值 0.45**、被当成命中（那是 §0.3.1 那张重叠区间表的证据，
也是 0.45→0.50 上调的直接动因）；**阈值上调 0.50 后它们应当全部短路**——所以现在这三条的角色变了：

- **上调后的验收用例**：三条都应 `coverage=low`。⚠️ 但要注意**口径**——0.484/0.465/0.465 是原话
  口径（§5.3 脚本）的分数，聊天页问同样的话线上分数是 0.4854/0.4726/0.4676，**两个口径都低于 0.50**，
  所以两边都该短路。
- **阈值余量的哨兵**：它们是离阈值最近的库外样本。哪天某条又冒到 0.50 以上，就是"余量吃光"的
  最早信号——比跑一遍 §2.3 那六条远题灵敏得多。

| # | 问题 | 原话口径 | 线上口径 | 原来命中了谁（旧阈值 0.45 下） |
|---|---|---|---|---|
| Q17 | `what's our office lease renewal process` | 0.484 | 0.4854 | `contract-register`（lease ≈ contract，沾边） |
| Q18 | `how do we run our employee 401k plan` | 0.465 | 0.4726 | `employee-agreement`（HR 沾边） |
| Q19 | `how do I renew my passport` | 0.465 | 0.4676 | `license-register`（renew/register 沾边） |

### 2.5 多主题 —— 逼模型一轮多查【V5】

| # | 问题 | 用途 |
|---|---|---|
| Q20 | `how do we do cash flow forecasting, and while you're at it how should we build the budget?` | TC-11（F1 去重）：两个主题相关、命中会重叠 |
| Q21 | `compare how we should run our sales pipeline versus our customer onboarding` | TC-10（C）：看两次调用的 `keywords` 是否都填了 |

---

## 3. 功能用例

> 通用前置条件（下列每条都适用，不再重复）：
> ① **ACTIVE = v5**（已于 2026-08-12 发布；若被回滚请见 §0.1）；② 前端 `+` 菜单 Playbook 开关**已打开**；
> ③ 能看到服务日志（`/logs/*.log`）与业务库 / 向量库。

### TC-01 低置信短路：库里没有的主题不硬答【V5】

- **前置**：同上
- **步骤**：新建会话，问 **§2.3 里任意一条**（推荐 Q14 `how do I fix the printer on the second floor`，
  实测 0.264，离阈值最远、最稳）
- **预期**：
  1. 答案基于通用知识，并**明确说明方法论库里没有这个主题**
  2. 答案里**不出现**任何手册标题 / 摘录
  3. 模型**只查一次**——不换措辞重试
- **证实**：`grep "search_playbooks" /logs/*.log | tail -5`
  - 出现 `coverage=low`，且 `search_playbooks 被调用` 在本轮**只有一条**
- ⚠️ **§2.4 的 near-miss 三条（401k / lease / passport）现在也该短路了**（阈值 0.50 > 它们的
  0.4676~0.4854），但**别拿它们当本条的主用例**：它们离阈值只有 0.015~0.03，一旦库或模型改版就
  可能重新冒头，测出"没短路"会让人误判成 A 坏了。**主用例用 §2.3 的远题（0.22~0.36）**；
  那三条按 §2.4 单独作"阈值余量哨兵"跑

### TC-02 短路仍写召回记录（本项核心承诺，最容易被改坏）【V5】

- **前置**：紧接 TC-01，记下时间
- **步骤**：查 `ai_rag_search_log`（SQL 见 §4）
- **预期**：**多出一行**，`query` 是你刚问的那句、`hit_count` 记的是实际低分命中数
- **为什么重要**：绕过这条记录会同时丢掉"内容覆盖缺口可统计"（该补哪些手册的唯一输入）与
  既有的低分命中统计——而这两件事外表上都看不出来

### TC-03 A 的阈值与 D-1 耦合（对照）【V2 + V5】

- **前置**：走 §5.3 的脚本（v2 已 ARCHIVED，聊天页读不到它）
- **步骤**：`python scripts/compare_playbook_versions.py`（缺省就是 v2 vs v5、口语化问法、关 rerank）
- **预期**（**阈值 0.50 口径**，2026-08-12 上调后）：v2 上 **7/8 短路**（只有 Q8 0.562 命中）、
  v5 上短路降到 **3/8**（Q4 0.485 / Q6 0.444 / Q7 0.395）
  - ⚠️ 阈值 0.45 时代这一行是 **2/8 短路**（Q6/Q7）。多出来的 Q4 是上调阈值的直接后果，
    **不是回归**——同一条问题线上口径 0.5804、不受影响
- **判读**：这不是 bug。它证明两件事：① 在**未发布 v5** 的库上，A 会吃掉合法的口语化命中
  （阈值当初是按改造前的分数分布定的）；② **原话口径下阈值永远不完美**，见 §0.3.1 的重叠区间——
  而线上口径下可分（§0.3.2），这也是阈值最终定在 0.50 的依据

### TC-04 D-1：口语化问法能不能召回【V2 + V5】

- **前置**：同 TC-03
- **步骤**：同上（脚本一次跑完 §2.1 全部 8 条 × 两个版本）
- **预期**（**实测基线，照它对**；分数是原话口径，判定按现阈值 **0.50**）：
  - v2：8 条中 **7 条短路**，只有 Q8（pricing）以 0.562 命中
  - v5：**5 条正确命中第一**（Q1 0.646 / Q2 0.536 / Q3 0.597 / Q5 0.506 / Q8 0.680）、
    **3 条短路**（Q4 0.485 / Q6 0.444 / Q7 0.395，原因见 §0.3，**不是缺陷**）
  - ⚠️ **两处与旧版预期不同，都是阈值 0.45→0.50 带来的，不是回归**：① Q4 从"命中但排错（靠 E 救）"
    变成短路；② Q5 只高出阈值 **0.006**，抖动可能让它偶尔翻到短路侧。两题的线上分数分别是
    0.5804 / 0.7710，聊天页不受影响
- **注意**：**不要**用 §2.2 的书面问法评价 D-1——那些在 v5 上是逐字命中（1.000），测的是泄漏

### TC-05 D-1 数据完整性【V5，纯 SQL】

- **前置**：无（纯查库）
- **步骤**：跑 §4 的"版本分段构成"SQL
- **预期**：`profile 63 / question 315 / body 276`，合计 **654**；随机抽 3 条 question 分段，
  `content` 是**裸问法**（不含 `(category).` 前缀、不含 `Key questions:`）
- **附加**：抽一个 entry 看 seq，应为 `body 0..n-1 → profile n → question n+1..n+m` 连续不重号

### TC-06 D-1 观测红利：哪条问法真被命中过【V5】

- **前置**：已完成 §2.1 若干提问
- **步骤**：跑 §4 的"问法命中"SQL
- **预期**：能列出 `hit_count > 0` 的具体问法文本
- **用途**：这是后续**删减 / 继续扩写问法（D-2）的唯一客观依据**

### TC-07 ⚠️ E 精排：**价值待重新评估**（C 落地后旧证据作废）【V5】

- **步骤**（不必改配置重启，用脚本做隔离——同一 question + keywords，只切 rerank）：
  ```bash
  uv run --no-sync python scripts/inspect_last_playbook_call.py --isolate   # ⚠️ +$0.0025
  ```
  在聊天页问完一题后立刻跑它：它会把模型这次实际发的两路检索词原样再跑一遍
  「关 rerank / 开 rerank」，末尾直接判读第 1 名有没有变。
- **预期**：**没有固定预期，这条要人工判胜负并记账**（§6 第 3 条）
- ⚠️ **为什么原来的预期被删掉了**：我原本拿 Q4 当 E 的最强证据——向量序把词面像的
  `buyer-persona` 排第 1、`account-management-process` 进不了前 3，rerank 把它救回第 2。
  **但那是 C 落地之前的对照。** C（双检索词）把向量侧修好之后，同一题的隔离实测是：

  ```
  关 rerank  #1 account-management-process  0.5804  ← 正确答案本来就在第 1
             #2 buyer-persona              0.5303
  开 rerank  #1 contract-playbook          0.4687  ← rerank 把它顶上来
             #2 account-management-process 0.5804  ← 正确答案被压到第 2
  ```

  **E 当初要治的病 C 已经治了，同一 case 上 E 现在是负作用。**
- **已有隔离样本（C 生效后，2026-08-12）：1 胜 1 负 3 平**
  - 胜：Q3 —— `sales-funnel-creation` 从进不了前 3 顶到第 2
  - 负：Q4 —— 见上
  - 平：Q1 / Q5 / Q8（第 1 名未变；Q8 第 2 名从 `application-code-and-front-end` 改善为 `saas-metrics`）
- **判读**：叠加 E 的实测代价（每次 **+1.4~2.1 秒**、**+$0.0025**），它是本轮五项里**唯一收益不明**
  的一项。**C 之前采的 E 胜负样本全部作废**（包括设计文档里那些），要按 §6 第 3 条重新采 ≥20 条。

### TC-08 E 铁律：精排不碰图扩展节点【V5】

- **步骤**：问 **Q2**（runway），展开答案里的"前置依赖"
- **预期**：前置链仍是结构序、内容合理，例如
  `cash-flow-forecast → budget-creation(d1) → define-the-mission(d2)`
- **为什么单列一条**：seed 是图扩展的**出发点**，选错会连带前置项全错、且错得"看起来有理有据"。
  另外 `define-the-mission` 这类节点与原问题语义极远，**任何相似度模型都会正确地判它不相关然后
  砍掉它**——而那恰恰是用户最需要知道的"你还得先做 X"。所以它必须仍然在

### TC-09 E 失败降级【任一版本】

- **步骤**：把 `.env` 的 `OPENROUTER_API_KEY` 临时改错（或断网），重启，问 Q4
- **预期**：**检索照常返回结果**（退回向量序），答案正常；日志出现
  `playbook rerank 失败，降级为向量序`；**不出现** "方法论库暂时不可用"
- **收尾**：记得把 key 改回来

### TC-10 C 模型是否真填 `keywords`【任一版本】

- **步骤**：问 **Q3~Q8**（⚠️ **不要用 Q1 / Q2**，见 §2.1 须知 1：它们的主题就是 docstring 里的
  两个示例，模型会逐字照抄，测不出泛化），每题问完跑：
  ```bash
  uv run --no-sync python scripts/inspect_last_playbook_call.py     # 免费，读库
  ```
- **预期**：`keywords` **有值**、是**术语短语**（2~7 个词、无问号）、且**不是 docstring 里的示例**
- **已实测（2026-08-12，6 次干净证据，全部自造）**：

  | 用户原话 | 模型造的 keywords |
  |---|---|
  | our deals stall halfway through… | `sales pipeline deal stall stage conversion` |
  | who owns the customer relationship… | `customer success handoff account ownership post-sale` |
  | which customers look like they are about to leave us | `customer health score churn risk early warning signals` |
  | we need to plan next year spending | `annual budget planning OPEX forecast` |
  | how should we design a KPI dashboard… | `KPI dashboard board reporting leadership metrics` |
  | how do we run our employee 401k plan | `401k retirement plan benefits administration` |
  | compare … sales pipeline versus … onboarding（**一轮两组**） | `customer onboarding process new customer` ＋ `sales pipeline stages management` |

- **判读**：这条测的是**提示词**而不是代码。`keywords` 留空是**合法降级**（退化为单路、不算 bug），
  但那样 C 就没生效。**一轮内问两个主题时两组术语互不串味**（Q21 实测）。
- ⚠️ **示例锚定：统计填空质量时要剔除撞 docstring 示例的主题。** 实测两次逐字照抄——Q1
  抄了 `board reporting monthly metrics`、Q20 第 1 次抄了 `cash flow forecast runway model`，
  两者都正是 docstring 里的示例。撞上了就只证明"会抄"，不证明"会造"。
- ⚠️ **想量化 C 的贡献，必须做隔离**——只看"kw 有值"证明不了它有用，因为模型**同时**还改写了问句，
  两个变量混在一起。唯一的办法是拿模型实际发的那段文本，只切 keywords 有无：

  ```python
  # 关 rerank、同一 question，只切 keywords（免费，只发 embedding）
  await svc.search(query=<模型的 question>, keywords="",  version=5, top_k=3)
  await svc.search(query=<模型的 question>, keywords=<模型的 keywords>, version=5, top_k=3)
  ```

  **实测两例**：
  - Q3：前两名分数一字不差，**第 3 名被术语路换掉**——`sales-compensation-plan` 0.5308 →
    `sales-funnel-creation` 0.5900（后者明显更贴题）。即 keywords 的作用是**把原本进不了前 3 的
    正确手册顶进来**，不是抬高已有名次。
  - Q6：改写贡献 +0.143（0.444 → 0.5870）、术语路再补 +0.011（→ 0.5980）。**主功是问句改写。**

### TC-11 F1 同一轮不重复灌正文【V5】✅ 已实测通过

- **步骤**：问 **Q20**（两个**相关**主题），使模型一轮内查两次
- **预期**：
  1. 答案里两个主题都答到了、内容完整
  2. 模型**不会**说第二本手册"没有内容"
  3. 第二次调用里**重复的手册** `excerpts` 为空 + `already_provided=true`；新手册正文照给
- **证实**：`uv run --no-sync python scripts/inspect_last_playbook_call.py`（打 `already_provided` 标记）
  或 `grep "search_playbooks 返回" /logs/*.log | tail -3`（看 `复用上文=N`）
- **实测基线（2026-08-12，Q20）**：模型自己调了两次，命中重叠 2 本 →

  ```
  第 1 次  question='how do I build an accurate cash flow forecast?'
      cash-flow-forecast          0.9870  摘录3
      enterprise-sales-process    0.5958  摘录3
      accounts-receivable-process 0.4337  摘录3
  第 2 次  question='how should we build our budget?'
      budget-creation             0.5784  摘录3   ← 新手册，正文照给
      cash-flow-forecast          0.5274  摘录0   ← already_provided
      enterprise-sales-process    0.4516  摘录0   ← already_provided
  ```

  省下约 2×3 段 ≈ **6600 字符**；答案 4233 字、两个主题都答到了，**模型没被空 excerpts 干扰**。
- **说明**：模型一轮查几次由它自己决定，**逼不出来就换个跨度更大的问题**；这条不算失败。
  ⚠️ **两次命中不重叠时不会有 `already_provided`，那是正确行为**——实测 Q21
  （`compare … sales pipeline versus … customer onboarding`）两次命中的六本手册完全不重叠，
  去重自然不触发，别当缺陷。

### TC-12 工具契约红线【V5】

- **步骤**：问任意 §2.1 问题，逐字读答案
- **预期**（任一条不满足即缺陷）：
  1. **不出现** "贵公司的资料显示…" / "你们的文档里写…"——playbook 是第三方通用方法论，
     冒充客户自有资料**性质等同编造**
  2. **不出现** `pid`（如 `cash-flow-forecast`）与版本号等内部标识，用手册标题指代
  3. 服务故障时说"方法论库暂时不可用、稍后重试"，**不说**"没有找到相关内容"

### TC-13 延迟观感（确认为非缺陷）【V5】

- **步骤**：问任意 §2.1 问题，掐表看"Searching playbooks"卡片停留时间
- **预期**：约 **2 秒**（rerank 单步实测 1297~2530 ms，均值 1878 ms；不开 rerank 时全链路约 350 ms）
- **说明**：⚠️ 设计 §7 假设 rerank 只加 **+100 ms**，实测差 18 倍。**这是已知偏差、不是 bug**，
  但"值不值得为它多等 2 秒"是待定的产品决策（关掉只需把 `RERANK_ENABLED` 改 `False`）。
  测试时请按 §6 第 3 条记录主观胜负，供这个决策用

---

## 4. SQL 与日志抽验

```bash
# 一次看全本轮所有关键日志标记
grep -h "search_playbooks 被调用\|search_playbooks 返回\|playbook rerank\|coverage=low" /logs/*.log | tail -30
```

```sql
-- ① 版本分段构成（TC-05）：v5 应为 profile 63 / question 315 / body 276
select metadata->>'chunk_kind' as kind, count(*)
  from ai_rag_playbook_chunk
 where entry_id in (select entry_id from ai_rag_playbook where version = 5 and not deleted)
 group by 1 order by 1;

-- ② 抽验 question 分段是裸问法（TC-05）
select content from ai_rag_playbook_chunk
 where metadata->>'chunk_kind' = 'question'
   and entry_id in (select entry_id from ai_rag_playbook where version = 5 and not deleted)
 order by random() limit 5;

-- ③ 短路仍写召回（TC-02）
select created_at, query, hit_count, top_k
  from ai_rag_search_log order by created_at desc limit 5;

-- ④ 哪条问法真被命中过（TC-06，D-2 的输入）
select c.content, c.hit_count
  from ai_rag_playbook_chunk c
 where c.metadata->>'chunk_kind' = 'question' and c.hit_count > 0
 order by c.hit_count desc limit 20;

-- ⑤ rerank 成本与延迟（TC-13）：实测均值约 1878ms、$0.0025/次、cost_source=provider
select llm_model, count(*) calls, sum(cost_usd) usd,
       min(perf_elapsed_ms) min_ms, round(avg(perf_elapsed_ms)) avg_ms, max(perf_elapsed_ms) max_ms,
       max(cost_source) src
  from ai_llm_call_log where call_type = 'rerank' group by 1;

-- ⑥ 审核页数据（发布前的闸门，留作回归用）：expanded_questions 是否落齐 63 × 5
select count(*) rows, count(*) filter (where jsonb_array_length(expanded_questions) = 5) with_5
  from ai_rag_playbook where version = 5 and not deleted;
```

---

## 5. 不经聊天页也能测的三条路

### 5.1 纯 SQL 用例
TC-05 / TC-06 只查库，随时可做。

### 5.2 单测已覆盖、不必手工验
见 §7。

### 5.3 按版本对照脚本 `scripts/compare_playbook_versions.py`（TC-01 / TC-03 / TC-04 / TC-07 / TC-08）

**能按任意版本测**：`search(version=N)` 对 DRAFT / ARCHIVED 版本一样有效，不动 ACTIVE 指针。
v5 发布后它的主要用途是 **TC-03 / TC-04 里读 v2**（聊天页已读不到 ARCHIVED 版本）。
本文档里所有实测数字都是它跑出来的。

```bash
# 在 CIOaas-python 根目录。--no-sync 是为了不让 uv 顺手改 site-packages（踩过一次 .pyd 文件锁）
uv run --no-sync python scripts/compare_playbook_versions.py                 # v2 vs v5，口语化，关 rerank
uv run --no-sync python scripts/compare_playbook_versions.py --versions 5    # 只看 v5
uv run --no-sync python scripts/compare_playbook_versions.py --set formal    # 书面问法（≈索引原文）
uv run --no-sync python scripts/compare_playbook_versions.py --set offsite   # 库外主题（验短路）
uv run --no-sync python scripts/compare_playbook_versions.py --set near-miss # 离阈值最近的库外问题（阈值 0.50 后应全 LOW）
uv run --no-sync python scripts/compare_playbook_versions.py --rerank        # 开精排（⚠️ 每个命中 $0.0025）
uv run --no-sync python scripts/compare_playbook_versions.py --versions 5 --rerank --detail  # 带前置项

# 复现 §0.3.3 那张"覆盖信号"表（向量分 vs rerank 分；⚠️ 每题一次 rerank $0.0025）
uv run --no-sync python scripts/compare_playbook_versions.py --set signal --versions 5 --coverage-signal
```

输出标记：`✓` 期望手册排第一 ｜ `~` 在前 top_k 但不是第一 ｜ `✗` 不在前 top_k（库外问题则是"没被短路"）
｜ `短路` 被低置信短路。

> ⚠️ 它跑的是**完整 `search()`**，所以会往 `ai_rag_search_log` 与 `ai_llm_call_log` 写记录
> （召回记录是主流程的一部分，不为脚本关掉）。默认打 `user_id='manual-test'` 标记，
> 统计成本 / 分析真实 query 分布时按它过滤。
>
> 与 `eval_playbook_recall.py` 的分工：那个跑 315 题金标、只跑阶段 1 `route()`、出 r@k + MRR、
> 比回归基线；本脚本跑少量人写问题、走完整链路、看 seed 与短路、比版本。**别混用**。

⚠️ 本脚本喂的是**用户原话**，而线上进检索的是模型改写后的问句 + 术语路——**两种口径的分数
差一个数量级**（§0.3）。所以它适合"比版本 / 比开关"，**不适合据它定阈值**。要看线上口径，
用下面的 §5.4。

### 5.4 逐题核对脚本 `scripts/inspect_last_playbook_call.py`（聊天页每问一题后跑）

答案文本判断不了检索对没对（模型能拿通用知识编一段像样的方法论，看起来就像检索过）。
本脚本按 `trace_id` 把四处记录串起来读，**这才是线上口径的唯一来源**：

```bash
uv run --no-sync python scripts/inspect_last_playbook_call.py            # 免费，只读库
uv run --no-sync python scripts/inspect_last_playbook_call.py --isolate  # 另跑 rerank 开/关对照，⚠️ +$0.0025
uv run --no-sync python scripts/inspect_last_playbook_call.py --nth 2    # 倒数第 2 次调用
```

| 它读什么 | 回答哪条用例 |
|---|---|
| `ai_llm_tool_call_log` 的 `tool_args` —— **模型实际传的 question / keywords** | TC-04 / **TC-10** |
| 工具返回的 seeds / coverage / 摘录数 / 前置项 | TC-04 / TC-08 / F1 |
| `ai_rag_search_log` | TC-02 |
| `ai_llm_call_log` 的 rerank 行（成本 / 耗时 / 候选数） | TC-07 / TC-13 |
| `ai_chatbot_message` 的答案，拿 63 个真 pid 逐一比对 | TC-12 |

> ⚠️ **一定要看"模型调了哪些工具"**：实测有一题（原 Q7）模型判定为取数请求、**压根没调
> `search_playbooks`**，而 `--nth 1` 读到的仍是上一题的记录——会让人误以为测过了。
> 脚本打的时间戳与 question 就是用来发现这种情况的，对不上就说明这轮没调。

---

## 6. 测试时请顺手攒三份数据（决定后续参数）

| # | 记什么 | 决定什么 |
|---|---|---|
| 1 | **线上口径**的 top1 分数（用 §5.4 脚本读，别用原话口径）：`coverage=low` 的真实 query 原文，**以及"没短路但库里其实没有"的那些** | A 的阈值**再校准**。设计明确**不拿金标定阈值**（金标分数偏高）。**阈值已按本轮 10 个点从 0.45 上调 0.50**（§0.3.2：合法 ≥0.5804 / 库外 ≤0.4854，缝在 0.49~0.58）。<br>接着采两类点：① **落在 0.49~0.58 缝里**的真实 query（决定阈值往 0.52 走还是退回）；② **新出现的 `coverage=low` 里"其实库里有"的**（上调后误杀的直接证据，连着两三条就调回 0.45~0.48） |
| 2 | 模型填 `keywords` 的比例与样例 | C 的提示词要不要改。**已有 6 次干净证据、全部自造**（TC-10）。⚠️ 统计时**剔除 Q1/Q2 那类撞 docstring 示例的主题**，否则填空率虚高 |
| 3 | rerank 开 / 关的**主观胜负**（≥20 条问题，用 `--isolate` 采） | "值不值得多等 1.4~2.1 秒 + $0.0025"。⚠️ **C 之前采的样本全部作废**（含设计文档里那些）——C 把向量侧修好后 E 的作用可能反转。C 之后已有 **1 胜 1 负 3 平**（TC-07） |

---

## 7. 手工测不出来的（别浪费时间，已有覆盖）

| 项 | 为什么测不出 | 已由什么保证 |
|---|---|---|
| **B 阶段 2/3 并发** | 省十几毫秒，肉眼与秒表都看不见 | 单测用**交叉等待**证明重叠执行（改回串行会死锁 → 红） |
| **F2 正文预算按 seed 均分** | 当前数据每轮约 10.3k 字符、闸门 16k，**吃不满就不触发** | 单测用超长段覆盖（含"每 seed 保底一段"） |
| **C 术语路的召回增益** | 金标只有问句形态，评测脚本只能走单路 | 只能靠真实流量（§6 第 2 条） |
| **D-1 的真实收益（量化）** | 金标就是那 315 条问法原文、现在**逐字命中**（相似度 1.000），r@1 99.7% 是泄漏 | 定性证据见 §0.2 与 §2.1 的口语化对照（v2 7/8 短路 → v5 5/8 命中第一）；**量化**需先建"由正文出题"的无泄漏金标（D-2 的前置） |
| **`search_profile` 的 SQL 形状**（折叠 / 只取三列 / 候选范围） | 错了不报错、只是静默变差 | 单测编译 SQL 后断言语句形状与绑定参数 |

---

## 8. 已知非缺陷（看到别报 bug）

1. **rerank 让每次 playbook 检索多约 2 秒**（TC-13）——已知偏差，产品决策待定。
2. **答案里手册的 `similarity` 与排序不同序**：rerank 只改名次，`similarity` 仍如实是向量余弦
   （那一列要落 `search_log` 与 `hit_count`，换量纲会让历史行不可比）。
3. **v5 上书面问法相似度恰好 1.000**：问法原文成了独立分段，属逐字命中（泄漏），不是算错。
4. **`entry.chunk_count` 从约 5.4 跳到 10.4**：每问一向量的预期结果，devSupport 文档页"分段数"
   变大属正常。
5. **v5 与 v2 的关系数不同**（54 → 47，diff 显示 +13 / −20）：关系由 LLM 每次重新推断，
   换模型或重跑都会重新掷骰子——这正是 activate 前必须人工审 diff 的原因。
6. **Q4 / Q6 / Q7 在 v5 上被短路**（原话口径 0.485 / 0.444 / 0.395）：**只在 §5.3 脚本的原话口径下
   发生**，聊天页三题线上分别是 0.5804 / 0.5980 / 0.7600（Q7 已换题）、全部命中。Q4 是阈值
   0.45→0.50 上调后新增的一条，**不是回归**，见 §0.3.1 末尾。
7. ~~**§2.4 那三条库外问题没被短路**~~：**阈值上调 0.50 后已不再是"非缺陷"，而是应当短路**
   （它们线上 0.4676~0.4854 全在阈值下）。现在反过来：**哪条又冒到 0.50 以上才是要记的信号**
   （阈值余量吃光），按 §6 第 1 条记录。
8. **rerank 永远拦不住库外问题**（无论阈值定多少）：`_rerank_seeds` 永远返回 top_k，
   cross-encoder 在当前接线里没有"都不相关"的出口——只要一个库外问题越过了 A 的阈值，
   开精排后照样返回 3 本手册，只是换个沾边的排第一。这是设计使然，不是 E 失效；能不能用它的
   **分数**当覆盖信号是另一件事，见 §0.3.3 方案 2（未做）。
9. **越阈的库外问题会白灌摘录，但模型通常自己会兜住**：401k 在**旧阈值 0.45** 下 A 没拦住
   （0.4726），模型拿到三本沾边手册的摘录后自己判断"这些跟 401k 无关"、如实答"知识库和方法论库
   都没有这个主题"。所以代价是**浪费**（约 3×1100 字符摘录 + $0.0025 + 约 1.5 秒），**不是答错**。
   ⚠️ 但这是 sonnet 的表现，换更弱的模型未必兜得住；且白灌摘录本身违背 A 立项时"省 context"的目标
   —— **这两条正是把阈值上调到 0.50 的动机**（0.50 之后 401k 应当被短路，模型连摘录都拿不到）。
   本条留档的意义：只要"越阈"这件事还可能发生（缝只有 0.095 宽），这个兜底行为就仍是最后一道防线。
10. **模型可能压根不调 `search_playbooks`**：取数意味明显的问题（如"想看我们的关键数字"）会被
   路由到 `get_companies` / `get_financials`。这是正确行为，不是 playbook 失效——但用 §5.4 脚本
   核对时要看时间戳/question 是否对得上本轮，否则会读到上一题的记录。
