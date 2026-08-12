# Playbook 召回优化 手工测试用例（优化项 A / B / C / D-1 / E）

> 关联文档：
> - 本轮改动的权威设计：[../开发设计/playbook-recall-optimization-dev-design.md](../开发设计/playbook-recall-optimization-dev-design.md)（A=§3、B=§4、C=§5、D=§6、E=§7）
> - 现行检索链路：[../开发设计/playbook-chatbot-integration-dev-design.md](../开发设计/playbook-chatbot-integration-dev-design.md)（§3.1 profile 配方 / §5 检索四阶段）
> - 工具入参与返回契约：`../../../python/CIOaas-python/docs/AI-Chatbot/chatbot-tools-v2-interface.md`（自动生成）
>
> 阶段：⑦ 测试用例 ｜ 日期：2026-08-11 ｜ 端：Python（CIOaas-python）+ 前端聊天页
>
> 范围：**只覆盖本轮五项改动**（低置信短路 / 阶段并发 / 双检索词 / 每问一向量 / 精排），
> 不重复 playbook 既有功能（crawl / ingest / activate / 审核页）的用例。
> 文档里每一个**带数字的预期**（相似度、命中的手册、条数、耗时）都是 2026-08-11 **在本地库
> 实测得到的**，不是推断——若你测出不同的数字，先怀疑环境（版本、开关、库数据），再怀疑代码。
> 少数"预期"是行为约定而非数值（如 §2.5 逼模型一轮多查、TC-12 的话术红线），已在各处注明。

---

## 0. ⚠️ 测试前必读：不做这两步，绝大多数用例测不出东西

### 0.1 版本现状

| 版本 | 状态 | 分段构成 | 说明 |
|---|---|---|---|
| **v2** | **ACTIVE**（线上/UI 读的就是它） | profile 63 + body 276 | **没有问法向量**，即 D-1 之前的库 |
| **v5** | DRAFT | profile 63 + **question 315** + body 276 = 654 | D-1 产出，**未发布**（发布要人工审 diff） |

聊天工具 `search_playbooks` 永远读 **ACTIVE 版本**，而 playbook 检索**没有 HTTP 端点**
（十个维护端点里没有 search；通用 `POST /api/ai/rag/recall` 已把 PLAYBOOK 空间排除）。
所以"按版本测"只有两条路：

- **A 路（推荐）**：先在测试环境审 diff 再发布 v5 → 之后 UI 测的就是完整链路
  1. 打开 `/devSupport/rag/playbookManage` 看 v5 的 diff（预期：63 条 `questionChanges` 各 `0 → 5`、
     关系 +13 / −20、`changedPids` 为空）
  2. 确认无误后 `POST /api/ai/rag/playbook/versions/5/activate`
- **B 路（不动线上版本）**：用脚本按版本直调 service，见 §5.3

### 0.2 ⚠️ 为什么"必须先发布 v5"不是可选项（实测数据）

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

1. **在 v2 上，用户随口问的问题几乎全部低于覆盖阈值 0.45 → 被优化项 A 短路 → 一本手册都不返回。**
   所以在 v2 上做"检索质量"测试，得到的几乎只有"库里没有这个主题"，测不出 C / E / F1 的任何效果。
2. **优化项 A 的阈值 0.45 与 D-1 是耦合的**：0.45 是按**改造前**的分数分布定的（那次"确实没覆盖"
   的全场最高 0.442），而改造前**合法的口语化命中也落在 0.33~0.44** —— A 会把它们一起吃掉。
   D-1 把合法口语化命中抬到 0.49~0.65 之后，0.45 才是个安全阈值。
   > ⚠️ 这一条是本轮测试发现的、**设计文档两节都没预料到的耦合**：不要在未发布 v5 的库上按
   > 0.45 去评价 A，也不要据此调低阈值——先发布 v5。

⚠️ v5 上书面问法的 **1.000 是逐字命中**（问法原文成了独立一行 chunk），这也是评测脚本报
r@1 99.7% 的原因，**那个分数是泄漏、不是质量**。判断真实水平要用口语化问法（本文档给的就是）。

### 0.3 ⚠️ 实测发现：0.45 这个阈值在 HyPE 索引上分不开两类问题

用 §5.3 的脚本在 **v5** 上跑了 17 个问题（8 条合法 + 9 条库外），按 top-1 分数排序：

| top-1 | 问题 | 库里有对应手册？ | A 的判定 | 对不对 |
|---|---|---|---|---|
| 0.680 | how should we decide what to charge for each tier | 有（pricing-matrix） | 命中 | ✅ |
| 0.646 | what should the board see every month | 有（board-of-directors） | 命中 | ✅ |
| 0.597 | our deals stall halfway through… | 有（pipeline-management-and-review） | 命中 | ✅ |
| 0.536 | how many months of runway do we have left | 有（cash-flow-forecast） | 命中 | ✅ |
| 0.506 | which customers look like they are about to leave us | 有（churn-identification-process） | 命中 | ✅ |
| 0.485 | who owns the customer relationship after the deal closes | 有（account-management-process） | 命中（但排错了，靠 E 救） | ⚠️ |
| **0.484** | what's our office lease renewal process | **没有** | 命中 contract-register | **❌ 放过了** |
| **0.465** | how do we run our employee 401k plan | **没有** | 命中 employee-agreement | **❌ 放过了** |
| **0.465** | how do I renew my passport | **没有** | 命中 license-register | **❌ 放过了** |
| ← 0.45 阈值线 |  |  |  |  |
| **0.444** | we need to plan next year spending | **有**（budget-creation） | **短路** | **❌ 误杀** |
| **0.395** | we want a one page view of our key numbers | **有**（kpi-dashboard-creation） | **短路** | **❌ 误杀** |
| 0.360 | how should we pick a coffee supplier for the office | 没有 | 短路 | ✅ |
| 0.310 | which laptop should I buy for my new designer | 没有 | 短路 | ✅ |
| 0.286 | what should we serve at the company holiday party | 没有 | 短路 | ✅ |
| 0.264 | how do I fix the printer on the second floor | 没有 | 短路 | ✅ |
| 0.259 | how do we set up the office wifi | 没有 | 短路 | ✅ |
| 0.223 | what's the weather going to be like next week | 没有 | 短路 | ✅ |

**0.395 ~ 0.484 是重叠区间**：里面同时有合法问题（0.444 / 0.395）和库外问题（0.484 / 0.465 / 0.465）。
在 0.45 这个取值下 **误杀 2 个、放过 3 个**，而且**调阈值救不了**——往上抬会连 0.485 那个合法问题
一起砍掉（且短路发生在 rerank 之前，E 救不回来），往下压会放进更多库外问题。

两点判读，测试时请按这个理解，别当缺陷报：

1. **D-1 把分数整体抬高了，库外问题也一起抬**——"沾点边"的问题会攀上相邻手册越过阈值
   （401k → employee-agreement、lease renewal → contract-register、passport → license-register，
   语义上都算"沾边"，不算离谱，但 A 的职责是"库里没有覆盖该主题的手册"，这三条它没拦住）。
2. **调阈值大概率不是出路**：`kpi-dashboard-creation` 那条只有 0.395，是因为源站 5 条问法里没有
   任何一条接近"one page view of our key numbers"这种说法——这是**问法覆盖面**问题，阈值动
   哪边都是两害相权。候选方案见 §0.3.1。
   > ⚠️ 这与设计 §11 议题 4 的假设（"先按 0.45 上线、跑一段真实流量后再调"）**不一致**：
   > 本轮数据显示两类问题的分数区间重叠，单一全局阈值在 HyPE 索引上是钝器。**不要据此
   > 自行改阈值**，把数据攒够（§6 第 1 条）后一起决策。

### 0.3.1 那要靠什么拦？—— 三条候选方案与各自代价

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

同一批 6 条：**向量阈值 0.45 → 2 误杀 + 2 放过；rerank 阈值取 0.60 → 1 误杀 + 0 放过。**

| 候选方案 | 效果 | 代价 |
|---|---|---|
| 继续调向量阈值 | §0.3 的 17 样本证明两头都得罪 | 0 |
| **D-2（LLM 扩写问法）** | 直接治"问法没覆盖到"那类（0.395 那条）；**查询期零开销** | ingest +95s、审核负担、需先建无泄漏金标；**目前无任何实测支撑** |
| **改用 rerank 分作覆盖信号** | 本轮样本上分层明显更好，还顺带纠正名次 | **要把 A 的短路移到 rerank 之后**——与设计 §7「A 在 rerank 之前、不为库里没有的问题付钱」**直接冲突**；库外问题也要付 $0.0025 + 约 1.7s |

⚠️ **三条都别急着做**，两个理由：

1. **只有 6 个样本，且已有一处交错**：合法的 `runway` 只有 0.5211，而库外的 `office lease` 是
   0.5289 —— **库外的反而更高**。rerank 分也不是干净的分隔器，只是比向量分好。
2. 这些问题全是**人工构造**的（§0.3 的 17 条 + 本节 6 条），不是真实流量。按 §6 第 1 条把真实
   query 攒够再决策。
3. rerank 分有 **±0.005 量级的运行间抖动**（printer 两次跑出 0.3790 / 0.3753），定阈值时别抠小数点。

### 0.4 前端开关

前端 `+` 菜单的 **Playbook 开关必须打开**（per-turn、opt-in）。关着的话取数轨**不绑定**
`search_playbooks`，模型看不见它，会直接用通用知识回答——很容易误判成"检索坏了"。

---

## 1. 用例 × 版本 速查表

| 用例 | 测什么 | 版本 | 能否在 UI 做 |
|---|---|---|---|
| TC-01 | A 低置信短路：库外主题 | **V5**（发布后） | ✅ |
| TC-02 | A 短路仍写召回记录 | **V5** | ✅（+ 一条 SQL） |
| TC-03 | A 阈值与 D-1 的耦合（v2/v5 对照） | **V2 + V5** | ⚠️ 走 §5.3 脚本（无需 activate） |
| TC-04 | D-1 口语化问法能不能召回 | **V2 + V5** 对照 | ⚠️ 同上 |
| TC-05 | D-1 数据完整性（654 段） | **V5**（纯 SQL，无需发布） | ❌ SQL |
| TC-06 | D-1 观测红利：哪条问法被命中 | **V5** | ❌ SQL |
| TC-07 | E 精排改善概念型/意图型问题 | **V5** | ✅ |
| TC-08 | E 精排不污染前置项（铁律） | **V5** | ✅ |
| TC-09 | E 失败降级 | **任一** | ⚠️ 需改配置模拟 |
| TC-10 | C 模型是否真填 `keywords` | **任一**（看填空率）/ **V5**（看效果） | ✅ |
| TC-11 | F1 同一轮不重复灌正文 | **V5** | ✅ |
| TC-12 | 工具契约红线（不冒充客户资料 / 不吐 pid） | **V5** | ✅ |
| TC-13 | 延迟观感（非缺陷确认） | **V5** | ✅ |

**一句话记法**：**除了"A 与旧库的对照"（TC-03 / TC-04 需要 v2），其余全部在 v5 上测。**

---

## 2. 测试问题清单（直接复制去问）

### 2.1 口语化问法 —— 主力测试集【V5】

这组是**真实用户口吻**，也是本轮所有改动的价值所在。下表右两列是**实测基线**（关 rerank、
top_k=3、2026-08-11 跑 `--set colloquial`），照它对；**不是"应该达到"的目标值**。

| # | 问题 | v2 | v5（关 rerank） |
|---|---|---|---|
| Q1 | `what should the board see every month` | 短路 0.415 | **0.646 ✓ board-of-directors** ← 设计 §5 招牌案例（旧库排第 9） |
| Q2 | `how many months of runway do we have left` | 短路 0.335 | **0.536 ✓ cash-flow-forecast** |
| Q3 | `our deals stall halfway through, where should we look` | 短路 0.360 | **0.597 ✓ pipeline-management-and-review**；开 rerank 后 `sales-funnel-creation` 进前 3 |
| Q4 | `who owns the customer relationship after the deal closes` | 短路 0.443 | 0.485 **✗ buyer-persona**（期望的 `account-management-process` 不在前 3）→ **开 rerank 后升到第 2，这是 E 的最强证据** |
| Q5 | `which customers look like they are about to leave us` | 短路 0.338 | **0.506 ✓ churn-identification-process** |
| Q6 | `we need to plan next year spending` | 短路 0.401 | **短路 0.444** ⚠️ 差 0.006 被误杀（见 §0.3），**不是缺陷** |
| Q7 | `we want a one page view of our key numbers` | 短路 0.375 | **短路 0.395** ⚠️ 问法覆盖面不足（D-2 的目标案例），**不是缺陷** |
| Q8 | `how should we decide what to charge for each tier` | 0.562 ✓ pricing-matrix | **0.680 ✓ pricing-matrix** |

**合计：v2 8 条里 7 条短路；v5 短路降到 3 条、5 条正确命中第一。** 这是 D-1 的核心收益证据
（比金标那个 +10.2pt 可信——后者是逐字泄漏）。

### 2.2 书面问法 —— 只用于 v2/v5 对照【V2 + V5】

| # | 问题 | v2 | v5 |
|---|---|---|---|
| Q9 | `How do I build an accurate cash flow forecast?` | 0.722 命中 | 1.000 命中 |
| Q10 | `When should I form a board of directors?` | 0.705 命中 | 1.000 命中 |

### 2.3 库外主题 —— 验短路【V5】

⚠️ **选题比想象的难**：D-1 之后分数整体抬高，"沾点边"的问题会攀上相邻手册越过阈值。
下面这批是**实测在 v5 上仍 < 0.45** 的（可放心用）：

| # | 问题 | v5 实测 top-1 |
|---|---|---|
| Q11 | `how should we pick a coffee supplier for the office` | 0.360 ✓ 短路 |
| Q12 | `which laptop should I buy for my new designer` | 0.310 ✓ 短路 |
| Q13 | `what should we serve at the company holiday party` | 0.286 ✓ 短路 |
| Q14 | `how do I fix the printer on the second floor` | 0.264 ✓ 短路 |
| Q15 | `how do we set up the office wifi` | 0.259 ✓ 短路 |
| Q16 | `what's the weather going to be like next week` | 0.223 ✓ 短路 |

### 2.4 near-miss —— 阈值校准的关键样本【V5】

这三条**库里确实没有**，但实测**越过了 0.45**、被当成命中。它们不是缺陷用例，是 §0.3 那张
重叠区间表的证据；测的时候如果模型拿这些手册硬答，请按 §6 第 1 条记录下来。

| # | 问题 | v5 实测 | 命中了谁 |
|---|---|---|---|
| Q17 | `what's our office lease renewal process` | 0.484 | `contract-register`（lease ≈ contract，沾边） |
| Q18 | `how do we run our employee 401k plan` | 0.465 | `employee-agreement`（HR 沾边） |
| Q19 | `how do I renew my passport` | 0.465 | `license-register`（renew/register 沾边） |

### 2.5 多主题 —— 逼模型一轮多查【V5】

| # | 问题 | 用途 |
|---|---|---|
| Q20 | `how do we do cash flow forecasting, and while you're at it how should we build the budget?` | TC-11（F1 去重）：两个主题相关、命中会重叠 |
| Q21 | `compare how we should run our sales pipeline versus our customer onboarding` | TC-10（C）：看两次调用的 `keywords` 是否都填了 |

---

## 3. 功能用例

> 通用前置条件（下列每条都适用，不再重复）：
> ① 已按 §0.1 发布 v5（除 TC-03 / TC-04 / TC-05 / TC-09）；② 前端 `+` 菜单 Playbook 开关**已打开**；
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
- ⚠️ **别用 §2.4 的 near-miss 三条来测这条**（401k / lease / passport）：它们实测越过了阈值、
  不会短路，用它们测会得出"A 坏了"的错误结论。那三条是 §0.3 的校准样本，不是短路用例

### TC-02 短路仍写召回记录（本项核心承诺，最容易被改坏）【V5】

- **前置**：紧接 TC-01，记下时间
- **步骤**：查 `ai_rag_search_log`（SQL 见 §4）
- **预期**：**多出一行**，`query` 是你刚问的那句、`hit_count` 记的是实际低分命中数
- **为什么重要**：绕过这条记录会同时丢掉"内容覆盖缺口可统计"（该补哪些手册的唯一输入）与
  既有的低分命中统计——而这两件事外表上都看不出来

### TC-03 A 的阈值与 D-1 耦合（对照）【V2 + V5】

- **前置**：**不需要发布 v5**，走 §5.3 的脚本
- **步骤**：`python scripts/compare_playbook_versions.py`（缺省就是 v2 vs v5、口语化问法、关 rerank）
- **预期**：与 §2.1 那张实测表逐行一致 —— v2 上 7/8 短路、v5 上短路降到 3/8
- **判读**：这不是 bug。它证明两件事：① 在**未发布 v5** 的库上，A 会吃掉合法的口语化命中
  （0.45 这个阈值是按改造前的分数分布定的）；② 发布 v5 后阈值仍不完美，见 §0.3 的重叠区间

### TC-04 D-1：口语化问法能不能召回【V2 + V5】

- **前置**：同 TC-03
- **步骤**：同上（脚本一次跑完 §2.1 全部 8 条 × 两个版本）
- **预期**（**实测基线，照它对**）：
  - v2：8 条中 **7 条短路**，只有 Q8（pricing）以 0.562 命中
  - v5：**5 条正确命中第一**（Q1/Q2/Q3/Q5/Q8）、**Q4 命中但排错**（靠 E 救，见 TC-07）、
    **Q6/Q7 仍短路**（0.444 / 0.395，原因见 §0.3，**不是缺陷**）
- **注意**：**不要**用 §2.2 的书面问法评价 D-1——那些在 v5 上是逐字命中（1.000），测的是泄漏

### TC-05 D-1 数据完整性【V5，纯 SQL】

- **前置**：无（不需要发布）
- **步骤**：跑 §4 的"版本分段构成"SQL
- **预期**：`profile 63 / question 315 / body 276`，合计 **654**；随机抽 3 条 question 分段，
  `content` 是**裸问法**（不含 `(category).` 前缀、不含 `Key questions:`）
- **附加**：抽一个 entry 看 seq，应为 `body 0..n-1 → profile n → question n+1..n+m` 连续不重号

### TC-06 D-1 观测红利：哪条问法真被命中过【V5】

- **前置**：已完成 §2.1 若干提问
- **步骤**：跑 §4 的"问法命中"SQL
- **预期**：能列出 `hit_count > 0` 的具体问法文本
- **用途**：这是后续**删减 / 继续扩写问法（D-2）的唯一客观依据**

### TC-07 E 精排改善意图型问题【V5】

- **步骤**：
  1. 问 **Q4**（`who owns the customer relationship after the deal closes`），记下返回的 3 本手册
  2. 把 `playbook_service.py` 的 `RERANK_ENABLED` 改为 `False`，重启服务，再问同一句
- **预期**：
  - 开 rerank：前 3 含 **`account-management-process`**（实测排第 2）
  - 关 rerank：`account-management-process` 不在前 3，首位是 `buyer-persona`（词面像、意图不对）
  - Q3 同理：开 rerank 时 `sales-funnel-creation` 进前 3
- **证实**：`grep "playbook rerank" /logs/*.log | tail -3`（会打候选数、最终 pid、分数、成本、耗时）

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

### TC-10 C 模型是否真填 `keywords`【任一版本看填空率 / V5 看效果】

- **步骤**：连续问 §2.1 的 8 条 + Q15，逐条看日志
- **预期**：`search_playbooks 被调用：q=... kw=...` 中 **`kw=` 有值**，且是**术语短语**
  （2~5 个词、无问号），不是把问句复读一遍
- **证实**：`grep -o "kw=[^ ]*" /logs/*.log | sort | uniq -c | sort -rn | head -20`
- **判读**：这条测的是**提示词**而不是代码。填空率低于一半，或 `kw` 全是问句复读 → 提示词要改
  （`keywords` 留空是**合法降级**、不算 bug，但那样 C 就没生效）

### TC-11 F1 同一轮不重复灌正文【V5】

- **步骤**：问 **Q14**（两个相关主题），使模型一轮内查两次
- **预期**：
  1. 答案里两个主题都答到了、内容完整
  2. 模型**不会**说第二本手册"没有内容"
- **证实**：`grep "search_playbooks 返回" /logs/*.log | tail -3`
  - 第二条出现 `复用上文=1`（或更多），且该手册的 `摘录0`
- **说明**：模型一轮查几次由它自己决定，**逼不出来就换个跨度更大的问题**；这条不算失败

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

-- ⑥ 审核页数据（发布 v5 前）：expanded_questions 是否落齐 63 × 5
select count(*) rows, count(*) filter (where jsonb_array_length(expanded_questions) = 5) with_5
  from ai_rag_playbook where version = 5 and not deleted;
```

---

## 5. 不发布 v5 也能测的两条路

### 5.1 纯 SQL 用例
TC-05 / TC-06 只查库，随时可做。

### 5.2 单测已覆盖、不必手工验
见 §7。

### 5.3 按版本对照脚本 `scripts/compare_playbook_versions.py`（TC-01 / TC-03 / TC-04 / TC-07 / TC-08）

**不需要 activate**：`search(version=N)` 对 DRAFT 版本同样有效。本文档里所有实测数字都是它跑出来的。

```bash
# 在 CIOaas-python 根目录。--no-sync 是为了不让 uv 顺手改 site-packages（踩过一次 .pyd 文件锁）
uv run --no-sync python scripts/compare_playbook_versions.py                 # v2 vs v5，口语化，关 rerank
uv run --no-sync python scripts/compare_playbook_versions.py --versions 5    # 只看 v5
uv run --no-sync python scripts/compare_playbook_versions.py --set formal    # 书面问法（≈索引原文）
uv run --no-sync python scripts/compare_playbook_versions.py --set offsite   # 库外主题（验短路）
uv run --no-sync python scripts/compare_playbook_versions.py --set near-miss # 越过阈值的库外问题
uv run --no-sync python scripts/compare_playbook_versions.py --rerank        # 开精排（⚠️ 每个命中 $0.0025）
uv run --no-sync python scripts/compare_playbook_versions.py --versions 5 --rerank --detail  # 带前置项

# 复现 §0.3.1 那张"覆盖信号"表（向量分 vs rerank 分；⚠️ 每题一次 rerank $0.0025）
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

---

## 6. 测试时请顺手攒三份数据（决定后续参数）

| # | 记什么 | 决定什么 |
|---|---|---|
| 1 | 所有 `coverage=low` 的**真实 query 原文** + top1 分数，**以及"没短路但答得不对"的那些** | A 的阈值 0.45 校准 + "该补哪些手册"。设计明确**不拿金标定阈值**（金标分数偏高会定得过高）。**本轮已攒下 17 个样本（§0.3）**，结论是两类问题在 **0.395~0.484 重叠**、调阈值两头都得罪：<br>· 误杀的合法问题：`we need to plan next year spending` 0.444、`we want a one page view of our key numbers` 0.395<br>· 放过的库外问题：office lease 0.484、401k 0.465、passport 0.465<br>继续攒真实流量样本，重点补这个区间；**别急着改阈值** |
| 2 | 模型填 `keywords` 的比例与样例 | C 的提示词要不要改；低于一半说明 C 实际没生效 |
| 3 | rerank 开 / 关的**主观胜负**（≥20 条问题） | "值不值得多等 2 秒"。目前只有 4 条样本（2 胜 1 平 0 负），不足以支撑决策 |

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
6. **Q6 / Q7 在 v5 上仍被短路**（0.444 / 0.395）：已知的阈值误杀与问法覆盖不足，见 §0.3。
7. **§2.4 那三条库外问题没被短路**（0.484 / 0.465 / 0.465，攀上了沾边的相邻手册）：同上，
   属阈值在重叠区间分不开两类问题的已知表现，**不是 A 失效**。两者都请按 §6 第 1 条记录，
   别改阈值。
8. **开了 rerank 也拦不住第 7 条**：`_rerank_seeds` 永远返回 top_k，cross-encoder 在当前接线里
   没有"都不相关"的出口——所以库外问题开精排后仍返回 3 本手册，只是换了个沾边的排第一。
   这是设计使然，不是 E 失效；能不能用它的**分数**当覆盖信号是另一件事，见 §0.3.1。
