# ERL 结转锁定与回退审批 设计文档

> 关联文档: 需求 [ERL Yes问题不重复回答](<../../ERL Yes问题不重复回答.md>) · [ERL 问卷锁定项的回退审批](<../../ERL 问卷锁定项的回退审批.md>) · ERL 主设计 [design-doc.md](../../设计/design-doc.md) · Asana LG-1581（Exit Readiness: Carry Forward Yes Answers & Change Request Flow）

| 版本 | 日期 | 说明 |
|---|---|---|
| v1.0 | 2026-11-04 | 第一个需求（已答 Yes 的题结转锁定）规则定档（§3），附接口与页面草案（§7、§8，待评审）；第二个需求（回退审批）待讨论（§12） |
| v1.1 | 2026-11-04 | CF7 改为「全 Yes 之后的季度全部锁定为 Yes、每季手动提交一次确认」，撤销「视为已提交」（`DEEMED_SUBMITTED`）与展示侧回退；开发中的评审结论写入 §8 / §9 / §11 |
| v1.2 | 2026-11-05 | 第二个需求（回退审批）定档：16 条讨论结论（§12.10）整理成规则、数据、接口、页面、邮件（§12.1～§12.8），收录设计稿（§12.9）；§8.3 的提交确认弹窗改按设计稿 |
| v1.3 | 2026-11-10 | GSV 卷结转只预填、不锁定，想改直接改（CF1 / CF9）；删掉 GSV 的 `Change to No` 与接口 31（RB1 / RB3 / RB4、§12.4、§12.5.1、§12.10-3）；GSV 卷按设计稿加预填说明、级别徽标与题旁来源标签，接口 3 加三个出参（§7.1、§8.1）；落到封住的季度不再停留，直接跳到本端本维最后提交的季度（§8.1）；审核期间冻结扩大到 P 及更早的季度，自动作废只剩提交更晚的季度（RB6 / RB7 ①）；未来季度照常可提交（撤销主设计 v4.75），提交晚于 P 的季度即作废申请；「当前季度」统一按关账月所在季度，填报页不带期次时默认打开它（主设计 v4.87）；公司端 A3 页头与 A4 维度卡头加 `Under Review · {季度}` 标签，接口 2 / 22 加 `pendingRollbackPeriod`（§12.4、§12.5.1） |

---

## 1. 背景与范围

ERL 衡量公司离可退出还有多远，按维度（FRL / PRL / BERL / RRL / TRL，可配置）各自逐级推进。现在每个季度都要把题从头答一遍，已经达成的 Yes 也要重答。

本需求把 ERL 当成**单向推进的进度条**：上一次提交里答了 Yes 的题视为已达成，之后的季度不再重答，直接从没达成的地方继续。

| 需求 | 内容 | 本文状态 |
|---|---|---|
| 第一个：ERL Yes问题不重复回答 | 上一次提交的 Yes 结转并锁定；提交后封住更早的季度；全 Yes 的维度之后每季全部锁定、手动提交确认；基线变化时清理草稿 | **规则已定**（§3～§6），接口与页面为草案（§7、§8） |
| 第二个：ERL 问卷锁定项的回退审批 | 锁定的 Yes 不再成立时，Founder 申请改成 No，GS 审批；GSV 卷不锁，直接改 | **已定**（§12） |

- 两个需求**同批上线**：只上第一个的话，锁定题几乎没有改回去的途径（见 CF11）。
- 本文只写这两个需求带来的变化，ERL 其余机制以 [ERL 主设计](../../设计/design-doc.md) 为准，文中「接口 N」的编号与主设计一致。
- Python 零改动：Gap 分析读的是提交记录自带的作答，结转后的提交记录照样是完整的。

## 2. 现状（与本需求相关的现行机制）

| 机制 | 现在的做法 |
|---|---|
| 填报单元 | 一条评估记录 = 公司 × 期次（`YYYYQn`）× 端（Founder / GSV）× 维度；状态只有 `DRAFT` / `SUBMITTED`，提交后永久只读 |
| 草稿 | 每个「公司 × 期次 × 端 × 维度」最多一条草稿，公司内共享。只打开不保存时**不建记录**；第一次存草稿、或没存过草稿直接提交时，才由 `findOrCreateDraft` 建行（直接提交也是先建 DRAFT 行，再在同一事务里改成 SUBMITTED） |
| 重复提交 | 同一期次可以提交多次，都保留；该期次以最新一次（`submitted_at DESC, id DESC`）为准，下称 SOT。每次重新填都从空白卷开始 |
| 计分 | level 内按题序，**遇到第一个 No 整个维度终止**，No 之后的题免答；服务端保存时删除第一个 No 之后的作答（改答回收）。所以一次提交里的 Yes 恰好是「从第一题起到第一个 No 之前」连续的一段 |
| 题库版本 | 评估记录建行时绑定当时最新的已发布版本，之后题库再发布多少版都不跟随。每个维度有自己的题集版本号，只有被编辑过的维度在发布时才复制出新的题目行（新 id），没动过的维度题目 id 不变 |
| 期次 | 前端可选当前年 ±15 年的任意季度，往期可以补录；服务端只校验格式。晚于当前自然季度（UTC）的期次只能存草稿、不能提交 |
| 展示 | 卡片 / A3 / A4 / Gap 分析 / Portfolio 只取「本期次」的 SOT，本期次没有提交就是空态，不回退到更早的期次 |

## 3. 规则（第一个需求，2026-11-04 定档）

| # | 规则 | 说明 |
|---|---|---|
| **CF1** | **两端都结转，只有 Founder 卷锁定** | 以「公司 × 端 × 维度」为单位，各走一条独立的时间线。端与端、维度与维度、公司与公司互不影响。<br>**GSV 卷只预填、不锁**（2026-11-10 改，原为两端都锁）：结转题照 CF2～CF5 算、建行时同样复制，打开时带出上次的 Yes、备注、附件，但 Yes / No、备注、附件都能直接改，存草稿 / 提交照常写入；接口 3 / 29 出参 `carriedForward` 恒为 false、`carriedForwardFromPeriod` 为 null。下文说的「锁定」都只指 Founder 卷 |
| **CF2** | **锁定基线** = 同公司、同端、同维度、**期次早于本期 P** 的最近一次提交 | 按期次倒序取最近的期次，同一期次多次提交取 SOT。由此：<br>• 重复提交最后提交期次 L 时，基线是 L **之前**那一次，**L 自己上一次的 Yes 不锁**（重复提交多半是为了改错，不能把错答锁死）；<br>• 跳季直提（L = 2026Q1，直接提 2026Q3）时基线是 L，跳过的季度不参与 |
| **CF3** | **锁定范围 = 基线里第一个 No 之前的全部题** | 锁定题只读：Yes / No、备注、附件都不能改。页面从基线里那道 No 开始作答，那道 No 本身不锁。基线没有 No（全 Yes）见 CF7 |
| **CF4** | **该维题集换版就一题不锁，从头作答** | 比较基线绑定的该维题集版本号与本期问卷绑定的该维题集版本号（即现在判两端题集是否一致用的那个号），不相等就不锁。只改维度配置（权重、名称）不算换版。版本号相等时题目 id 也相同，锁定题按 id 直接对应 |
| **CF5** | **锁定范围实时算，锁定题的作答在评估行首次创建时复制进去**（GSV 卷的结转题同样复制，见 CF1） | 打开、存草稿、进度预览、提交都按 CF2 现查基线，不加标记列。评估行新建时（首次存草稿，或没存过草稿直接提交）把锁定题的 Yes、备注、附件关联一起复制进去；附件只复制关联行，删除时只删关联、不删文件。Reset 删行后，下次建行按当时的基线再复制。存草稿 / 提交时，入参里的锁定题一律跳过，以库里的复制件为准（GSV 卷不跳过，入参覆盖复制件） |
| **CF6** | **提交后封住过去** | 某端某维一旦有提交，早于其最后提交期次 L 的季度一律不可填（打开只读，存草稿 / 提交拒收），已提交的历史季度也不能再提交，**只有 L 能重复提交**。首次填写仍可从任意季度起步。「未来季度只能存草稿」已于 2026-11-10 撤销（主设计 v4.87）：未来季度照常可提交，提交后它成为 L，更早的季度（含当前季度）一并封住 |
| **CF7** | **全 Yes 之后每季手动确认** | 基线全 Yes（该维全部 level 通关）时，之后的季度照 CF3 **全部锁定为 Yes**（各 level 折叠、打绿勾），提交按钮直接可点，**每个季度仍要手动提交一次**作为确认；没提交的季度与现在一样显示未提交。卡片、A3 / A4、Portfolio、Gap 分析、Share 门槛**只认真实提交**，不回退到更早的期次。换版照 CF4：该维换版后一题不锁、从头作答。<br>⚠ **偏离需求原文**（第 87 行「之后也不需要再提交」、第 94 行「Overview 季度变化时显示绿点已提交」）。2026-11-04 决定：自动视为已提交要在所有展示处回退到更早的提交，并带来 Gap 不随基线刷新、已结束季度两端题集不一致无解等问题；改为每季点一次确认，只认真实提交 |
| **CF8** | **提交即清理该端该维其它期次的草稿** | 某端某维提交期次 P（首次、重复、跳季、中间季度都算），在同一事务里删除该端该维**其它所有期次**的草稿：晚于 P 的锁定基线变了，早于 P 的已经成了历史季度（CF6）。有要删的草稿时，提交前弹窗告知 |
| **CF9** | **GSV 改结转的 Yes 不走审批** | 审批只针对 Founder。GSV 卷不锁（CF1），想改直接改成 No 再存草稿 / 提交，没有 `Change to No`（2026-11-10 改，原为点 `Change to No` 直接回退提交，§12.1 RB3） |
| **CF10** | **存量草稿上线时全部清理** | 用 SQL 删除全部 `DRAFT` 行（两端、所有期次）及其作答、附件关联；Java 发版后立即执行。已提交记录不动；存量里补录造成的乱序提交不处理，基线按 CF2 自然取 |
| **CF11** | **与回退审批同批上线** | 单上本需求的话，锁定题除了「重复提交 L」之外没有任何改回途径 |

## 4. 例子

某公司 Founder 端 FRL 维度，题目 L1（q1、q2）、L2（q3、q4、q5）、L3（q6、q7）。假设自然时间已经足够晚，下面的期次都不算未来季度。

| # | 动作 | 结果 |
|---|---|---|
| 1 | 2025Q3 提交：q1～q3 Yes，q4 No | L = 2025Q3，更早的季度都不能再填 |
| 2 | 打开 2025Q4 | 锁 q1～q3（基线 2025Q3），从 q4 开始答 |
| 3 | 2025Q4 提交：q4、q5 Yes，q6 No | L = 2025Q4，2025Q3 不能再提交 |
| 4 | 重复提交 2025Q4 | 锁 q1～q3（基线仍是 2025Q3，不是 2025Q4 上一次），q4 起可以改 |
| 5 | 给 2026Q1、2026Q2 各存一份草稿，然后提交 2026Q2 | 锁 q1～q5（基线 2025Q4）；提交前弹窗提示 2026Q1 的草稿会被删除；提交后 L = 2026Q2，2026Q1 成为历史季度、不能再填 |
| 6 | 2026Q2 的那次提交全 Yes | 打开 2026Q3：q1～q7 全部锁定为 Yes、各 level 折叠打勾，直接点提交即可；不提交就和现在一样显示未提交 |
| 7 | 2026Q4 题库发布新版，FRL 的题有改动 | 之后新建的 FRL 问卷绑新版，从头答（一题不锁）；已提交的季度不受影响 |
| 8 | 同一时期 GSV 端填 FRL | 按 GSV 自己的提交取结转题，与 Founder 端互不影响；只预填、不锁，GSV 可以直接改（CF1） |

## 5. 打开问卷时怎么判定

对「端 X、维度 D、期次 P」按下面的顺序判定，结果决定页面形态（§8）和能不能存草稿 / 提交（§7）。

1. **历史季度**：L = X 端 D 维最后提交的期次。L 存在且 P 早于 L ⇒ **已封住（CLOSED）**。
2. **取基线**：B = X 端 D 维期次早于 P 的最近一次提交。没有 B ⇒ **可填、不锁**。
3. **其余情况可填（OPEN）**：本期问卷绑定的版本（已有评估行取行上绑定的版本，没有取当前最新已发布版本）里 D 维的题集版本号与 B 相同 ⇒ 锁定 B 第一个 No 之前的题（B 全 Yes 时即全部题，CF7）；不同 ⇒ 不锁。

判定只读不写，接口 3 每次打开都现算。

## 6. 数据与落库

- **不加表、不加列**。锁定范围、最后提交期次都由现有的评估行和题库版本现算。
- **复制时机**：评估行在 `findOrCreateDraft` 新建分支里创建时，把基线中锁定题的作答（Yes、备注）与附件关联行复制进新行。提交出来的记录因此自带完整作答，历史详情、A3 / A4、计分、Gap 分析输入都不用改。
- **入参处理**：存草稿 / 提交时跳过入参里的锁定题。计分、作答顺序校验、改答回收照现有逻辑走，锁定题都在第一个 No 之前，不会被回收。
- **提交时清理**（CF8）：接口 5 在同一事务里删除该端该维其它期次的草稿行，连同作答行与附件关联行（erl_* 表没有外键，要按「附件关联 → 作答 → 评估行」的顺序删）。
- **存量清理**（CF10）：上线 SQL 删除全部草稿；Java 发版后立即执行。

## 7. 接口变更（草案，待评审）

### 7.1 接口 3（打开问卷）新增出参

| 字段 | 类型 | 说明 |
|---|---|---|
| `fillState` | `OPEN` / `CLOSED` | §5 的判定结果 |
| `carriedForwardFromPeriod` | string \| null | 有锁定题时为基线期次，其余为 null（GSV 卷恒为 null） |
| `lastSubmittedPeriod` | string \| null | 本端本维最后提交的期次（CF6），前端据此置灰季度下拉；从没提交过为 null |
| `otherDraftPeriods` | string[] | 本端本维其它期次的草稿期次，提交时会被删除（CF8），供确认弹窗列出；没有为空数组 |
| `levels[].questions[].carriedForward` | boolean | 该题是否结转锁定（不叫 `locked`：前端 `locked` 与 level 状态 `LOCKED` 已表示「还没解锁到」）。接口 29 出参同样带。GSV 卷恒为 false（预填的题照普通作答带出） |
| `prefilledFromPeriod` | string \| null | GSV 卷的预填来源（基线）期次；Founder 卷与没有预填时为 null（2026-11-10 加） |
| `prefilledLevels` | number[] | GSV 卷在基线里整级都答 Yes、本季整级预填的 level，升序；Founder 卷与没有时为空数组 |
| `prefillContinueLevel` | number \| null | GSV 卷基线里第一道非 Yes 所在的 level，即从这一级接着答；基线全 Yes、Founder 卷与没有预填时为 null。这三项按基线算、与草稿无关，接口 29 不带 |

- `OPEN`：`levels` 照现在的规则下发，锁定题带上复制来的作答（没有评估行时，用基线作答现算出来的预览）。
- `CLOSED`：`levels` 为空数组，`canSubmit` 恒为 `false`。

### 7.2 写接口

| 接口 | 变化 |
|---|---|
| 接口 4（存草稿） | `CLOSED` 拒收（文案见下）；入参里的锁定题跳过 |
| 接口 5（提交） | 同接口 4；成功后在同一事务里删除 `otherDraftPeriods` 对应的草稿 |
| 接口 29（进度预览） | 计分时并入锁定题的作答；不拒收，非 `OPEN` 时 `canSubmit` 为 `false` |
| 接口 28（Reset） | 不变 |

拒收文案（形态同现有业务校验：HTTP 200 + `Result.fail`）：`Quarters before {Q1 2026} can no longer be filled in for this dimension.`（`{}` 为 L）

### 7.3 展示类接口

接口 1（卡片）、2（A3）、22（A4）、20（Portfolio）及 Gap 分析相关接口**不变**：只认真实提交，本期次没有提交仍是空态（CF7）。

## 8. 页面交互（草案，待评审）

### 8.1 填报页

| 状态 | 页面 |
|---|---|
| `OPEN`，有锁定题 | 顶部提示条：`Questions answered Yes in {Q4 2025} are carried forward and locked.`<br>全部锁定的 level 照现有规则默认折叠、打绿勾，展开后锁定题只读、带 `Carried forward` 标记；含基线 No 的那一级展开，锁定题只读。页面定位到第一道可答的题（即基线里那道 No）。Reset 只清空非锁定题（服务端删行后重拉，锁定题自然再带出来）。<br>基线全 Yes 时（CF7）所有题锁定、各 level 折叠打勾、不定位，提示条改为 `All questions were answered Yes in {Q4 2025} and are carried forward. Submit to confirm this quarter.`，提交按钮直接可点<br>**2026-11-06 按设计稿改（本地联调时用户定）**：顶部提示条撤下（含 CF7 全锁定时的 `Submit to confirm` 那句）；题干旁的 `Carried forward` 去掉，改为级别标题上的 `🔒 Locked · answered Yes in {Q4 2025}` 徽标（该级有锁定题就出）；锁定题右侧是灰底 `🔒 Yes` 标签（代替已答绿勾）+ 橙框 `Change to No`，下半部分作答与备注区保留（禁用）。**2026-11-10 改**：锁定题不出 Yes / No 作答块（恒禁用、用不到），备注与附件只读保留、占满整行。 |
| `OPEN`，GSV 卷有预填（2026-11-10 按设计稿） | 结转题照普通作答带出、可直接改（CF1），没有锁定标签与 `Change to No`。<br>• 维度卡片里、所有级别之上一行说明：`Levels 1–7 were answered “Yes” in {Q3 2026} and are pre-filled — you can still change them. Continue from **{Exit Era - 8}**, answered “No” last quarter.`（只有一级时用单数；没有整级预填时开头改为 `Questions answered “Yes” in {Q3 2026} are pre-filled — you can still change them.`；基线全 Yes 时没有 `Continue from` 那句）。<br>• 整级预填的级别标题旁标 `“Yes” in {Q3 2026}`（逆时针时钟图标，不带底框）；该级被改成 No、显示终止句时不标。<br>• 整级预填的级别里的题仍答 Yes 时，题目右侧、已答绿勾左边标浅灰底 `From {Q3 2026}`（同一图标）；改成 No 就不标。「接着答」那一级里排在基线 No 之前的题也是预填的，但前端分不出来，与说明框、级别徽标同口径只认整级，不标。<br>• 不自动定位 |
| `OPEN`，没有锁定题 | 与现在一致 |
| `CLOSED` | **2026-11-10 改（测试问题，需求方定）：不再停留，直接跳到本端本维最后提交的季度 L**（同切季度下拉，回写网址）。起因：A1 卡片 `Start an Assessment`、A3 `+ New`、A4 `+ Add New` 带的是查看季度（默认关账月所在季度），本端已提交过更晚的季度时它已封住，点进去只剩提示条。规则：没提交过 → 传入季度；L 不晚于传入季度 → 传入季度；L 晚于传入季度 → L（L 可重复提交，一定可填）。旧链接直接打开历史季度同样跳。原提示条 `This quarter is closed. {维度} was last submitted for {Q1 2026}; …` 与 `View history` 入口删掉。<br>~~原定：不显示题目，提示条：`This quarter is closed. {维度} was last submitted for {Q1 2026}; earlier quarters can no longer be filled in.`，附历史记录入口（`View history`）；按钮整排不显示（含 `Cancel`，同现有已提交只读态）。顶部信息栏照常显示，`Assessed by / Role` 因无草稿而显示当前用户；只有旧链接能进到这一页，2026-11-05 定不隐藏~~ |

### 8.2 季度下拉

按 `lastSubmittedPeriod` 置灰更早的季度。下拉是「季度」「年份」两个下拉框：早于 L 所在年份的年份置灰，L 所在年份里早于 L 的季度置灰。通过 URL 直接打开历史季度时按 `CLOSED` 显示。

### 8.3 提交确认弹窗

`otherDraftPeriods` 不为空时，在现有提交确认弹窗（首次提交 / `Submit again?` 两套）里加一段，主按钮改名：

> You also have draft(s) for {Q1 2026, Q2 2026} in this dimension. Submitting will refresh the locked-question baseline, so these drafts will be permanently discarded.
>
> [Cancel] [Submit and discard drafts]

题库更新弹窗的 `Submit draft content` 也是提交，同样在弹窗里加这一段（按钮文案不改）。

需求文档写的是两套弹窗（重复提交当前季度 / 提交中间季度），都只提到晚于本期的草稿。按 CF8 早于本期的草稿也会删除，这里合成一段文案（待确认，§11-①）。

> **v1.2 起本节作废**：改按设计稿的弹窗 1、2（§12.9），早于本期的草稿删除不提示（§12.10-11），有待审核申请时并入弹窗 3（§12.5.1）。第 7 步已按本节做的弹窗要返工。

### 8.4 展示页

卡片、A3 / A4、Portfolio 不变：只认真实提交（CF7）。

## 9. 边界情况

| 情况 | 处理 |
|---|---|
| 基线期次有多次提交 | 取 SOT（`submitted_at DESC, id DESC` 首条） |
| 基线里第一个 No 之后还有作答（2026-09-28 改答回收上线前的存量数据） | 锁定范围按题序只取第一个 No 之前，之后的作答忽略 |
| 草稿建好后题库又发了新版 | 草稿保持绑定旧版本，锁定按草稿绑定的版本比较，不受影响。题库更新弹窗的 `Submit draft content` 自动补 No 落在第一道未答题上，那是锁定题之后，不冲突；选 `Access new question library` 会 Reset，新草稿按新版本重新判定（该维换版就不锁） |
| 两人同时操作同一端同一维的不同期次 | 草稿行有行锁；提交清理时锁住已有草稿，与另一人存草稿撞上时，对方后存的按提交后的新基线建行。极小概率的例外，不另做处理：① 对方是首次存草稿、INSERT 还没提交时清理看不到它，那份草稿带着旧基线的复制件留下（Reset 可恢复）；② 同端同维两个期次同时提交，互相等对方的行，数据库判死锁回滚其一，返回一次 500，重试即可（2026-11-05 确认接受，不修） |
| 存量补录导致的乱序提交 | 不处理，基线与 L 按期次取，自然生效 |
| 已提交的未来期次（2026-09-29 之前与 2026-11-10 之后都允许） | L 会是一个未来季度，按 CF6 当前季度会被封住。上线前查一下存量（§11-⑤） |
| 维度停用 | 与现在一致：停用后写接口拒收 |

## 10. 上线

- 与第二个需求（回退审批）同批上线（CF11）。
- Java 与 Web 同批：只上 Java 时，旧前端会把锁定题当普通题让人改，服务端却忽略这些修改，用户会困惑。
- Java 发版后立即执行存量草稿清理 SQL（CF10），放在 Java `deploy/upgrade_doc/sprint122/`。
- Python 零改动。

## 11. 待定事项

| # | 事项 | 现在的处理 |
|---|---|---|
| ① | ~~提交确认弹窗文案：需求文档两套弹窗只提到晚于本期的草稿~~ | **已定**（2026-11-05）：按设计稿弹窗 1、2，早于本期的草稿删除不提示（§12.10-11） |
| ② | ~~两端在同一季度都只是视为已提交时，不会触发 Gap 对账~~ | **不再适用**（v1.1 CF7 改为每季手动确认）。原结论：（第 9 步核实）：管理员打开该公司 Company Overview 时，接口 17 的自愈对账（触发点 ②）按两端各自的全 Yes 提交规划，两端分相等 ⇒ 任务直接 SUCCESS + No Gap、不调 AI，约 5 秒后显示 No Gap。卡片两端分数、Era、`Information Last Submitted` 都取那次全 Yes 提交。Share 按钮来自接口 1，要刷新页面后才亮（现有行为） |
| ③ | 锁定题、`CLOSED` 的页面形态与文案 | §8.1 草案，待确认 |
| ④ | LG-1581 写的「GSV flow is unchanged」与 CF1 / CF9 | 2026-11-10 GSV 卷改为只预填、不锁后基本一致，只多了预填；票里补一句即可 |
| ⑤ | 存量里已提交的未来期次会让当前季度被封住 | 上线前查线上数据，有的话再定 |
| ⑥ | ~~已结束季度可能永远生成不了 Gap、不能 Share~~（v1.1 CF7 改为每季手动确认后不再适用，原记录保留）：一端全 Yes 后该维换版，另一端再回头填那个已结束、被视为已提交的季度（新建行绑新版），两端题集不一致，要求视为已提交那端按新版重交，而它只读 | **接受**（2026-11-04）。只影响该已结束季度的该维；当前季度不会出现（换版后当前季度不再视为已提交）。后续题库版本需求会给题库加生效时间，届时可解决 |

## 12. 第二个需求：锁定项回退审批

规则、数据、接口、页面由 2026-11-05 的逐条讨论整理而成（§12.10）。设计稿见 §12.9。下文用 P 表示申请所在的季度，qk 表示申请回退的那道题。

### 12.1 规则

| # | 规则 | 说明 |
|---|---|---|
| **RB1** | **入口：锁定题的 `Change to No`** | Founder 填报页上，结转锁定的题（`carriedForward = true`）每题右侧有 `Change to No`，只在 `OPEN` 的季度出现；GSV 卷不锁，没有这个入口（CF9）。全 Yes 之后全部锁定的季度同样处理（§12.10-4） |
| **RB2** | **Founder 申请，GS 审批** | 一次只回退一道题，原因必填。点 Apply 后建一条待审核申请；页面上还没保存的作答直接丢掉（§12.10-9）。找不到任何审批人时报错，不建申请（§12.10-5） |
| **RB3** | **GSV 直接改，不走审批** | GSV 卷结转题不锁（CF1），直接改成 No，按普通存草稿 / 提交走；不建申请，不发邮件（CF9）。<br>2026-11-10 改：原为 `Change to No` → `Submit` 按 RB4 直接回退提交（§12.10-3），接口 31 已删 |
| **RB4** | **回退提交**（Founder 获批时） | • 新建一条提交记录，草稿不动：qk 之前的锁定作答（Yes、备注、附件关联）取自基线那次提交；qk 记 No，原因写进 qk 的备注；qk 之后按「遇 No 终止」不答。计分照现有逻辑。<br>• 绑定的题库版本：该季草稿绑定的版本，没有草稿时取当前最新已发布版本。审核期间换版会作废申请（RB7），所以两者一致。<br>• 草稿：本季和晚于本季的保留，早于本季的删除（§12.10-2）。<br>• 提交人：记申请人（§12.10-7）。<br>• 提交后照接口 5 触发 Gap 对账；Founder 获批时用审批人的 token |
| **RB5** | **一个维度最多一条待审核** | 范围是「公司 × 维度」（只有 Founder 端有申请）。<br>• 在更晚的季度再申请：旧申请自动作废。<br>• 同一季度（审核中）与比待审核更早的季度：不允许，`Change to No` 置灰（§12.10-8；同季那条 2026-11-06 按设计稿改，见下）。后端照旧会顶掉（接口不拦），入口只在前端关掉 |
| **RB6** | **审核期间冻结 P 及更早的季度** | **2026-11-10 改（测试问题，需求方定）**：P 与早于 P 的季度都不能存草稿、提交、Reset、删附件（原为只冻结 P）。依据需求第 4 条「当前季度不可提交、不可存草稿」与第 5 条「只有提交未来季度才作废申请」；更早季度的重复提交会改动 P 的锁定基线。早于 P 的季度不出审核中提示条，只出一句 `A rollback request for {P} is pending review.`（同服务端拒收文案）。<br>原文：P 这一季不能存草稿、提交、Reset、删附件。页面显示审核中提示条，整卷置灰；申请那道题右侧显示 `Change to No · Pending approval`，本季其他锁定题的 `Change to No` 置灰、不能再申请（2026-11-06 按设计稿改，原为「仍可再申请」）。冻结保证审核期间草稿不变（§12.10-15） |
| **RB7** | **自动作废** | 以下三种情况，申请自动作废，不发邮件：<br>① 提交该维度晚于 P 的季度，提交前弹弹窗 3（§12.10-15）。2026-11-10 起 P 及更早的季度被冻结（RB6），原来「重复提交 L、补交跳过的季度」这两种已走不到；<br>② 被新申请顶掉（RB5）；<br>③ 发布新版题库，且该维的题集版本号变了（§12.10-16）。<br>①③ 保证审核期间基线不变，所以申请不存作答快照 |
| **RB8** | **审批人** | 管理端用户，公司在其组织子树内，且 `UserServiceImpl.canAccessCompany(userId, companyId)` 为真（PGM 看全组织、PM 看所属 Portfolio）。SA 不算：它是平台级、不属于任何组织。两人同时处理，先提交的算数（§12.10-5） |
| **RB9** | **邮件** | • 申请时发邮件 01，收件人 = 公司所属那一级组织的 PGM（带 `seeAllPortfolio`、不是 SA）∪ 公司所属各 Portfolio 的 PM，按邮箱去重。<br>• 批准、拒绝时分别发邮件 02、03 给申请人（§12.10-5） |
| **RB10** | **拒绝** | 原因必填。锁定题保持 Yes，提交记录和草稿都不动 |
| **RB11** | **批准后重复提交 P** | 基线照 CF2 退回上一季，qk 重新锁成 Yes，要改得再申请一次（§12.10-1）。交 P 的旧草稿也是这个效果，等于放弃已批准的那份（§12.10-2） |
| **RB12** | **不能撤回，不超时，不提醒** | Founder 只能等审批，或者提交其他季度让申请作废（§12.10-6） |

### 12.2 数据

新增一张表 `erl_assessment_rollback_application`（实体 `ErlAssessmentRollbackApplication`；不以 `Request` 结尾，免得和入参类的层后缀撞名）。DDL 为 Java `deploy/upgrade_doc/sprint122/V2__erl_assessment_rollback_application.sql`，Java 发版前执行。现有表不改：批准生成的提交记录就是一条普通提交。

| 列 | 说明 |
|---|---|
| `id` | 主键 |
| `organization_id` | 申请时解析出的公司 ERL 组织。发布新版题库时按它找要作废的申请（RB7 ③） |
| `company_id`、`dimension_code`、`period` | 申请所在的公司、维度、季度 P。没有端列，只有 Founder 端有申请 |
| `question_id` | qk 的题目 id（`erl_question_config.id`）。题目行按版本不可变，邮件和页面据此取题面 |
| `reason` | 申请原因 |
| `applicant_user_id`、`applicant_name`、`applicant_role` | 申请人和姓名、角色快照。批准时写进提交记录的 `submitterName` / `submitterRole` |
| `status` | `PENDING` / `APPROVED` / `DECLINED` / `VOIDED` |
| `reviewer_user_id`、`reviewer_name`、`reviewed_at` | 审批人与审批时间，批准、拒绝时写入 |
| `refuse_reason` | 拒绝原因 |
| `submission_id` | 批准生成的提交记录 id |
| 审计列 | 同其他 `erl_*` 表；`created_at` 就是申请时间 |

- 部分唯一索引：`(company_id, dimension_code) WHERE status = 'PENDING'`，兜底 RB5。
- 不存作答快照，不存作废原因（§12.10-8、§12.10-15）。

### 12.3 状态流转

| 从 | 到 | 触发 |
|---|---|---|
| — | `PENDING` | Founder 点 Apply（接口 30） |
| `PENDING` | `APPROVED` | 审批人批准（接口 33） |
| `PENDING` | `DECLINED` | 审批人拒绝（接口 34） |
| `PENDING` | `VOIDED` | RB7 的三种情况 |

所有流转都是条件更新（`WHERE id = ? AND status = 'PENDING'`）。更新了 0 行，说明已被别人处理，返回 `This request has already been processed.`（§12.10-13）。

### 12.4 接口

新增接口续用主设计的编号：

| # | 接口 | 调用方 | 说明 |
|---|---|---|---|
| 30 | `POST /erl/assessment/rollback-request` | 公司端 | 入参 `period`、`dimensionCode`、`questionId`、`reason`。<br>校验：P 为 `OPEN`；qk 在 P 是锁定题；P 不早于已有的待审核申请；找得到审批人。<br>同一事务里先作废同维已有的待审核申请，再插入 `PENDING`。事务提交后给每个收件人发一封邮件 01。<br>出参：申请 id |
| ~~31~~ | ~~`POST /erl/assessment/rollback`~~ | — | 2026-11-10 删除：GSV 卷不锁、直接改（CF9），不再需要直接回退接口。编号不复用 |
| 32 | `GET /erl/rollback-request/{id}` | 管理端 | 申请详情：状态、公司、维度、季度、题目、原因、申请人、申请时间。邮件链接落地时据此决定显示什么（§12.5.2）。按申请的公司做读权限校验 |
| 33 | `POST /erl/rollback-request/{id}/approve` | 审批人（RB8） | 按 RB4 回退提交，同一事务里把申请改为 `APPROVED` 并写入 `submission_id`。<br>批准前重算一次 qk 是否仍是锁定题；不是就作废申请，返回已处理。<br>事务提交后发邮件 02，并用审批人 token 触发 Gap 对账 |
| 34 | `POST /erl/rollback-request/{id}/refuse` | 审批人（RB8） | 入参 `reason`（必填）。把申请改为 `DECLINED`，事务提交后发邮件 03 |

现有接口的变化：

| 接口 | 变化 |
|---|---|
| 接口 3（打开问卷） | 出参加 `pendingRollbackRequest`：本公司 Founder 端本维当前的待审核申请（不限季度），没有为 null，GSV 卷恒为 null。字段：`id`、`period`、`questionId`、`reason`、`applicantName`、`appliedAt`。<br>再加 `canReviewRollback`：调用者是不是审批人，公司端恒为 false。<br>填报页用它显示提示条、置灰按钮、弹弹窗 3；审核页用它渲染卡片和按钮 |
| 接口 4（存草稿）、接口 28（Reset）、删附件（`DELETE /erl/assessment/attachment/{id}`） | 本期是 P 或早于 P 时拒收（RB6，2026-11-10 扩大到更早的季度），文案报 P |
| 接口 5（提交） | 本期是 P 或早于 P 时拒收；提交晚于 P 的季度时，在同一事务里作废待审核申请（RB7 ①） |
| 接口 2（A3 维度页） | 公司端调用时页头加 `pendingRollbackPeriod`：本公司本维待审核申请所在的季度（不限所看季度），没有为 null；管理端恒为 null（管理端 `+ New` 开 GSV 卷，申请只属于 Founder）。A3 据此在 `+ New` 左边标 `Under Review · {Q3 2026}`（2026-11-10 测试问题补） |
| 接口 22（A4） | 管理端调用时，Founder 端每个维度加 `pendingRollbackRequest`（结构同接口 3）。A4 据此在 Founder 药丸显示卡片，再用接口 3 读 P 的草稿<br>公司端调用时每个维度加 `pendingRollbackPeriod`（同接口 2），A4 维度卡头据此标 `Under Review · {季度}`（2026-11-10 补） |
| 题库发布（`ErlQuestionConfigVersionServiceImpl.publishDraft`） | 同一事务里作废该组织下题集版本号变了的维度的待审核申请（RB7 ③） |

拒收文案（形态同现有业务校验：HTTP 200 + `Result.fail`，草案）：
- 审核中：`A rollback request for {Q4 2026} is pending review.`
- 找不到审批人：`No reviewer is available for this company. Please contact your GS team.`

### 12.5 页面

#### 12.5.1 填报页（Founder 卷；GSV 卷不锁，见 CF1）

| 情况 | 页面 |
|---|---|
| `OPEN` 季度的锁定题 | 每题右侧 `Change to No`。点开后的弹框还没有设计稿，按需求做：题目原文只读，原因文本框必填，`Cancel` / `Apply`，填了原因才可点 |
| Founder 点 Apply 后 | 页面按服务端状态刷新。P 进入审核中：顶部提示条用需求文档第 53～55 行的文案；非锁定题置灰；`Save as Draft` / `Submit` / Reset 置灰。<br>**2026-11-06 按设计稿改**：提示条移到元信息栏之上，改成浅琥珀卡片（标题 + `SUBMITTED BY` / `ON` / `CHANGE` / `QUESTION` 四列 + `REASON`）；维度卡头加 `Under Review` 标签；申请那道题右侧显示 `Change to No · Pending approval`，本季其余题置灰、`Change to No` 不可点（RB5）；每级题目装进白底圆角描边的框。<br>**2026-11-10 补（测试问题）**：打开审核中的季度时，自动展开申请那道题所在的级别（哪怕已通关、默认折叠）并定位到它，**2026-11-11 起其余级别全部收起**（含当前在答的级别）；公司端与管理端打开 Founder 卷都这样，每份填报只定位一次；审核中的季度题目不出 Yes / No 作答块（设计稿），备注区占满整行；已作答的题右上角改为只读答案标签（绿色 `Yes` / 琥珀 `No`），代替绿勾与锁定题的 `🔒 Yes` |
| Founder 打开比 P 更早的季度 | 整卷只读、`Save as Draft` / `Submit` / Reset / `Discard draft` 置灰（RB6，2026-11-10）；不出审核中提示条，只出一句信息提示 `A rollback request for {Q4 2026} is pending review.`；`Change to No` 置灰，悬停同一句 |
| 公司端 A3 维度页、A4 维度卡（Full View） | 本维有待审核申请时，A3 页头 `+ New` 左边、A4 卡头（`+ Add New` 左边）出浅琥珀标签 `🕓 Under Review · {申请季度}`（A3 有设计稿，A4 无设计稿、同 A3 样式；2026-11-10 测试问题补）；`+ New` / `+ Add New` 照常可点。管理端不出 |
| 提交确认弹窗 | 第 7 步做的合并弹窗按设计稿改成弹窗 1、2（§12.9）。<br>有待审核申请、又提交该维其他季度时弹弹窗 3；与弹窗 1 或 2 同时成立时合成一个：标题和按钮用 1 或 2 的，正文在 `Continue?` 前加弹窗 3 那句（§12.10-12、15）。<br>早于本季的草稿删除不提示（§12.10-11）。<br>题库更新弹窗里的 `Submit draft content` 也是提交，有待审核申请时同样加弹窗 3 那句。<br>开发补充（第 21 步）：管理端替 Founder 提交时，弹窗 3 那句的 `your` 换成 `the pending`（同审核中提示条的管理端口径）；季度按屏上格式写 `Q4 2025`；宽 568px、圆角 3px 原来两套确认也用；题库更新弹窗删草稿那段沿用 §8.3 原句，只列晚于本期的 |

#### 12.5.2 审核页（A4 的 Founder 药丸）

- 版式见 §12.9 审核页。卡片、高亮来自 `pendingRollbackRequest`。问卷来自接口 3 读出的 Founder 在 P 的草稿，审核期间冻结；从没存过草稿时显示锁定题预览。这是新增的读取路径：A4 的 Founder 药丸原来只读已提交记录。
- `Refuse` / `Approve` 只在 `canReviewRollback` 为 true 时显示。
- Approve 弹框、Refuse 弹框还没有设计稿，按需求文档的文字做（需求文档第 121～124 行、第 151～156 行）。处理完刷新页面，恢复成正常的 Founder 药丸。
- 邮件链接带 `rollbackRequestId`。页面先调接口 32，按状态显示（§12.10-13）：
  - 待审核：如上；
  - 已作废：作废整页；
  - 已批准或已拒绝：正常的 Founder 药丸，顶部提示 `This request has already been processed.`，然后从 URL 去掉 `rollbackRequestId`。
- 两人同时处理时，后点的那位收到「已处理」的拒收，同样提示并刷新。
- 开发补充（第 22 步）：卡片不看页面当前季度，该维有待审核申请就出，问卷是 P 的草稿、卡头题数也取草稿那份；自己批准 / 拒绝后同样从 URL 去掉 `rollbackRequestId`；成功 toast `Rollback request approved.` / `Rollback request declined.`（自拟）；卡片时间用 A4 本地时间格式；作废页整页只剩空态（面包屑与标题也不出，2026-11-06 联调时按设计稿改）、宽度跟页面；「已处理」提示可关。

#### 12.5.3 作废页

版式和文案见 §12.9。被新申请顶掉、因换版作废的申请也用这一页，说明文案对不上，可以接受（§12.10-8、16）。

### 12.6 邮件

- 走现有的 `EmailDispatcher.enqueue`，新增三种 `EmailComposer`，分别对应邮件 01、02、03。`bizKey` 为申请 id，每个收件人一封；都在事务提交后发。
- 内容和版式见 §12.9。邮件 01 的按钮链接：`{管理端地址}/exitReadiness/scoreDetails?companyId={公司}&period={P}&dimension={维度}&portal=FOUNDER&rollbackRequestId={申请 id}`。
- 申请人或收件人已经注销时，照 `EmailComposer` 约定抛 `NonRetryableEmailException`，不发。

### 12.7 边界情况

| 情况 | 处理 |
|---|---|
| Apply 与同维另一季度的提交同时发生 | 两条待审核由部分唯一索引兜底，撞上时返回一次 500（同 §9 的既有口径）。如果提交的作废先于申请插入，会留下一条基线已变、或 P 已被封住（提交的是更晚季度）的待审核申请；批准前会重新判断 P 是否仍开放、qk 是否仍锁定（接口 33），任一不成立就作废 |
| 回退提交与同端同维另一季度的普通提交同时发生 | 两边按不同顺序给草稿行加锁，可能被数据库判死锁、回滚其一，返回一次 500，重试即可。与 §9 已接受的「两个期次同时提交」同类，不另做处理 |
| 两人同时申请（同公司的两个公司端用户） | 部分唯一索引兜底，后到的返回一次 500，重试后按 RB5 顶掉前一条 |
| Apply 与 P 的存草稿 / 提交 / Reset 同时发生（如自动保存的请求还在途中就点了 Apply，或另一个用户同时提交 P） | 冻结是先查后写、不加锁，在途的写入照常成功：审核页看到的是 Apply 之后才落盘的草稿，或者 P 已提交而申请仍待审核。批准内容按基线现算，结果不受影响。2026-11-06 接受，不加锁 |
| 批准与 Founder 补交更早季度 Q 同时发生（Q 还没有草稿） | 两边都先查后写，Q 没有草稿行可锁：批准先提交时，Founder 的提交会写进已被封住的 Q，并按 CF8 删掉 P 与更晚季度的草稿，和邮件 02「草稿保留」对不上。窗口是毫秒级，与上面「回退提交与普通提交同时发生」同类，2026-11-06 接受，不加锁 |
| Apply 与发布新版题库同时发生 | 发布的作废语句看不到还没提交的新申请，该维换版后这条申请仍是待审核；批准时按 P 草稿绑定的旧版提交。窗口是毫秒级，2026-11-06 接受，不加锁 |
| 批准时维度已停用 | 照接口 5 拒收，申请保持待审核。停用期间填报页、A4 都不显示该维，申请无人可见；重新启用后照常可批可拒（批准前重算锁定）。停用不算换版，发布题库时不作废它（2026-11-06 定） |
| 批准时 P 已被封住 | 正常不会发生：封住 P 需要提交更晚的季度，而那会先作废申请（RB7 ①）。只有上面「Apply 与提交同时发生」会留下这种申请，批准时作废、返回已处理 |
| 申请时 P 还没有草稿 | 正常申请。审核页显示锁定题预览；批准时按 RB4 从基线取作答 |
| P 是未来季度 | 不拦，Founder 申请允许（2026-11-10 起普通提交也不拦未来季度）。后果：最后提交季度 L 会成为未来季度，当前季度按 CF6 封住。2026-11-05 接受：实际不会有人这么做 |

### 12.8 上线

- 与第一个需求同批上线（CF11）。
- 发版顺序：先执行 `V1__ff_init.sql`（Fireflies）与 `V2__erl_assessment_rollback_application.sql` 建表，再发 Java 与 Web（同批），发完立即执行 `V3__erl_draft_cleanup.sql` 清理草稿（CF10）。编号即执行顺序（2026-11-06 合并进 sprint122 时 ERL 两个脚本顺延一号，给 Fireflies 的 V1 让位）。
- Python 零改动：批准生成的提交记录和普通提交一样，Gap 分析读的是记录自带的作答。

### 12.9 设计稿（2026-11-05 收到）

**提交确认弹窗**：宽 568px，圆角 3px，字体 Jost / Futura。`{}` 是变量，设计稿里用浅蓝底高亮。

| # | 场景 | 标题 | 正文 | 按钮 |
|---|---|---|---|---|
| 1 | 重复提交最后提交季度 L，且有晚于 L 的草稿 | `Re-submit current quarter?` | `You're about to re-submit {2025 Q4}.`<br>`You have {2} future-quarter draft(s) saved ({2026 Q1, 2026 Q2}).`<br>`Re-submitting will refresh the locked-question baseline. All future-quarter drafts above will be permanently discarded and must be re-entered against the new baseline.`<br>`Continue?` | `Cancel` / `Submit and discard drafts` |
| 2 | 提交晚于 L 的季度，且有更晚季度的草稿 | `Submit this quarter?` | `You're about to submit {2026 Q2}.`<br>`There are {2} future-quarter draft(s) scheduled after this quarter ({2026 Q3, 2026 Q4}).`<br>`Submitting will refresh the locked-question baseline. All drafts for quarters after the one being submitted will be permanently discarded.`<br>`Continue?` | `Cancel` / `Submit and discard later drafts` |
| 3 | 有待审核的回退申请时，提交该维度其他季度（更晚、重复提交 L、补交跳过的季度都算，第 15 条） | `Submit this form?` | `Upon submission of this form, your {2025 Q4} return application will be automatically withdrawn.` | `Cancel` / `Submit` |

弹窗 1、2 取代 §8.3 合成一段的草案。第 7 步按草案做的弹窗要按设计稿返工。

**邮件**：

- 三封邮件共用 Looking Glass 页头 logo、分隔线、产品介绍和页脚，只换标题和正文。
- 版式：宽 450px，内容区 420px。标题 Arial Bold 22/27 居中；正文 Arial 11/17，段距 14px；按钮通栏，30px 高，圆角 3px。
- 色值：标题和正文藏青 #002B56，按钮和链接橙 #E1990F，分隔线 #C2C4C6，页脚 #AAAAAA。

| # | 收件人 | 主题 = 标题 | 正文 |
|---|---|---|---|
| 01 | 审批人 | `A locked answer rollback request requires your review` | `Hello {收件人},`<br>`There is a locked answer rollback request requires your review.`<br>`Applicant` / `Company` / `Dimension` / `Quarter` / `Question` / `Requested change: Yes → No` / `Reason provided`<br>`Click the button below to review the full questionnaire and approve or refuse this request.`<br>按钮 `Review Request` |
| 02 | 申请人 | `Your rollback request has been approved` | `Hello {收件人},`<br>`Question` / `Change applied: Yes → No` / `Reviewed by` / `On`<br>`The questionnaire for {Quarter}{Dimension} has been formally submitted. Your drafts for this and future quarters remain available for editing.` |
| 03 | 申请人 | `Your rollback request has been declined` | `Hello {收件人},`<br>`Question` / `Requested change: Yes → No (not applied)` / `Reviewed by` / `On` / `Reason`<br>`The locked answer remains unchanged. All submitted questionnaires and drafts are preserved. You may continue editing drafts or submit a new request if circumstances change.` |

**申请已作废页**：审批人从邮件打开一条已经自动作废的申请时显示，整页空态，宽 1200px。

- 内容：一个图标，标题 `This request has been automatically voided.`，说明 `The applicant has since submitted a later quarter's questionnaire for this dimension, which has advanced beyond the question in this request. The rollback is no longer applicable, and no action is required.`
- 场景：Founder 在 Q3 申请把一道题改成 No，GS 一直没审。Founder 提交 Q4 时，弹窗 3 提示后这条申请自动作废；之后 Founder 又发了第二条申请。审批人点第一封邮件进来，看到的就是这一页。

**审核页（2026-11-05 收到）**：就是管理端 A4 Score Details 页的 `Founder` 药丸。有待审核申请时：

- 药丸下方先显示一张浅橙色卡片：标题 `Pending review · Rollback request for {Q4 2026}`（带时钟图标）；下面是 `SUBMITTED BY` / `ON` / `QUESTION` 三列，再下面是 `REASON`。
- 问卷整份只读。锁定题标 `Locked · "Yes" in {Q3 2026}`。申请的那道题整块浅橙高亮，题下多一个框：`CHANGE REQUEST · YES → NO · PENDING REVIEW`，下一行是 `{申请人}: {原因}`。
- 问卷卡片下方右对齐两个按钮：`Refuse`（红框白底）、`Approve`（橙底）。
- 有待审核申请时，`Founder` 药丸显示申请那一季 Founder 最后一次保存的草稿（审核期间冻结；从没存过就显示锁定题预览），不显示平时的最近一次提交。申请批准、拒绝或作废后恢复原样。
- 卡片和高亮所有管理端用户都能看到；`Refuse` / `Approve` 只有审批人能看到（第 5 条）。
- 数据来源（不存快照，2026-11-05 定）：卡片和高亮的题来自申请记录；问卷来自 Founder 该季的草稿，由管理端调接口 3 读 Founder 卷。锁定标记 `Locked · "Yes" in {期次}` 用接口 3 已有的结转标记和基线期次。现在 A4 的 Founder 药丸只读已提交记录，读草稿是新增的读取路径。

**还没有设计稿的**：`Change to No` 申请弹窗、Founder 侧的审核中提示条、Approve 和 Refuse 两个弹窗。这些目前按需求文档的文字做。

### 12.10 讨论记录（2026-11-05 全部已定）

1～10 来自 2026-11-04 的需求审查，11～14 是对照设计稿后新增的，15～16 是讨论中发现的。§12.1～§12.8 由这些结论整理而成，引用时写作「§12.10-n」；本节和 §12.9 里的「第 n 条」也指这里的编号。

1. 审批通过后再重复提交同一季度，按 CF2 被回退的题会重新锁成 Yes。要不要保留已批准的回退？保留的话要调整 CF2。<br>**定（2026-11-05）：不保留，CF2 不改。** 重复提交时基线退回上一季，被回退的题重新锁成 Yes，用户要改只能再申请一次。
2. 审批通过后草稿怎么处理：需求文档《Yes 不重复回答》说作废（情形 C），《回退审批》说保留。<br>**定（2026-11-05）：本季和晚于本季的草稿都保留**，照《回退审批》，Approve 弹窗和批准邮件的文案不改。<br>• 批准时新建一条提交记录，Founder 的草稿不动。提交内容按基线现算：被回退那题之前的锁定作答（含备注、附件关联）取自基线那次提交，被回退的题记 No，原因写进它的备注，之后的题按「遇 No 终止」不答。申请不存作答快照，因为审核期间基线和草稿都不会变（第 15 条）。草稿唯一索引只约束 `DRAFT`，同一季度的提交记录和草稿本来就能共存。<br>• 只删早于本季的草稿：批准后本季成为最后提交季度，更早的季度封住，那些草稿已经用不上。<br>• 本季草稿仍按上一季的基线锁定，被回退的题还是 Yes。Founder 交这份草稿，就等于放弃已批准的那份；这和第 1 条一致，重复提交本季本来就会把这道题重新锁回 Yes。<br>• 晚于本季的草稿改按新基线锁定，被回退的题解锁，按旧基线复制进来的 Yes 留作可改的作答。<br>• 还有别的锁定题要改，就再申请一次。
3. GSV 改锁定题不走审批（CF9），具体怎么改。<br>**改（2026-11-10）：GSV 卷结转只预填、不锁，想改直接改，下面 2026-11-05 的 `Change to No` 方案作废，接口 31 已删（CF1 / CF9）。**<br>~~定（2026-11-05）：GSV 点 `Change to No` 直接提交。~~<br>• GSV 的锁定题也有 `Change to No`，弹框和 Founder 的一样（题目 + 必填原因），按钮改为 `Submit`。<br>• 确认后直接提交本季：这道题之前的锁定作答照旧，这道题改为 No，后面的题按「遇 No 终止」不用答。<br>• 和 Founder 获批走同一段回退提交，不建申请记录，不发邮件。<br>• 原因写进这次提交里该题的备注。Founder 获批时也写进该题备注，两端一致，B3 历史里能看到改 No 的原因。<br>• 草稿照第 2 条处理：本季和晚于本季的保留，早于本季的删除，弹框不提草稿。
4. 全 Yes 之后的季度所有题都锁定（CF7），回退入口与普通锁定题相同即可，确认一下。<br>**定（2026-11-05）：与普通锁定题相同**，入口、审批、回退提交都不做特殊处理，提示条文案不改。
5. 审批人与收件人：PGM 的判定与 Fireflies 相同，即管理端用户，且是 superAdmin 或角色菜单含 `seeAllPortfolio`。收件人取该公司所属组织的 PGM。要定的是：公司所属组织没有 PGM 时怎么办；PM 能不能审批；两人同时审批以谁为准。<br>**定（2026-11-05）：**<br>• 收件人是 PGM；审批人是该公司所在租户的 PGM 和 SA。<br>• 判定（2026-11-05 定）：<br>　- PGM = 角色菜单含 `seeAllPortfolio`（同 `CompanyGroupServiceImpl.getIsGroupManager`）。<br>　- SA = 任一角色 `role.is_super_admin`（同登录用户信息的 `superAdmin`）。<br>　- `RoleTypeEnum.SUPER_ADMIN`（`roleType = 1`）是全部管理端用户，不是 SA。<br>• 收件人·PGM = 公司所属那一级组织下、角色带 `seeAllPortfolio` 且不是 `is_super_admin` 的用户。显式排除 SA，不依赖库里 SA 角色有没有配 `seeAllPortfolio`。上级组织的 PGM 能审批，但不收邮件，与删除 Forecast 版本邮件（`UserRepository.findUserEmailForDeleteForecastVersion`）同口径。<br>• 审批人 = 管理端，公司在其组织子树内，且 `UserServiceImpl.canAccessCompany(userId, companyId)` 为真（已含 PGM 看全组织、PM 经所属 Portfolio）。<br>• **SA 从审批人与「有没有审批人」里拿掉**（2026-11-05，开发第 15 步查本地库后定）：带 `is_super_admin` 的只有一个平台级角色「Super Admin」，12 个用户都是 `role_type = 0`，没有一个挂在任何组织上（`r_organization_user`、`r_organization_role` 都是 0）。SA 登录后 ERL 解不出组织，本来就过不了组织子树判定。收件人 SQL 里排除 SA 的条件保留。test / 生产未核实，大概率同样。<br>• 现有邮件都不发 PGM（Benchmark 邮件只发 PM 与 Company Admin），这是第一封发给 PGM 的邮件。<br>• 一个审批人都找不到时，点 Apply 报错，不建申请，提示 Founder 联系 GS。Founder 正常提交本季不受影响。「找得到」= 收件人非空，即至少有一个人会收到邮件（开发第 15 步时改，见下一条）。<br>• 两人同时审批，先提交的算数。状态从待审核改为已批准或已拒绝时带条件更新；后到的人看到「已被某人处理」，页面刷新为处理后的样子（显示什么见第 13 条）。<br>• PM 能审批自己负责的公司，也收这些公司的邮件。负责的判断走 Portfolio：公司 → `r_company_group` 找所属 Portfolio（可能有多个）→ `r_portfolio_user` 找这些 Portfolio 的 PM。审批时反过来校验调用者负责的 Portfolio 里有这家公司。<br>• 收件人 = 公司所属组织的 PGM ∪ 公司所属各 Portfolio 的 PM，按邮箱去重，SA 不收。审批人 = PGM ∪ 这些 PM（判定见上）。
6. 申请能否撤回、有没有超时或提醒、管理端有没有站内待办入口。<br>**定（2026-11-05）：**<br>• 不能撤回。Founder 只能等审批，或者提交更晚的季度让申请自动作废。<br>• 不做超时，也不做提醒，需要时再加。<br>• 做站内入口，就是审核页本身：管理端打开该公司该维度 Score Details 的 Founder 药丸，就能看到待审核申请并处理（设计稿见 §12.9）。邮件里的 `Review Request` 也跳到这里。
7. 审批通过 = 替 Founder 提交：提交人和审批人存在哪里；Gap 分析用谁的 token 触发。<br>**定（2026-11-05）：**<br>• 提交记录上的提交人（`submitterName` / `submitterRole`）记申请人 Founder。审批人、审批时间和结果记在申请记录上。<br>• B3 历史先不标「Approved by」，改 No 的原因已写进该题备注（第 3 条）。<br>• Gap 分析用审批人的 token 触发，新建 Gap 记录的 `created_by` 记审批人。
8. 一次申请能回退几道题；「一个维度只能有一条待审核申请」是按维度算还是按「维度 × 季度」算。<br>**定（2026-11-05）：**<br>• 一次申请只回退一道题。<br>• 同公司同维度只有一条待审核申请。<br>• 在更晚的季度申请，更早季度的申请自动作废；同一季度第二次申请，上一条自动作废。所以审核期间，本季和更晚季度的锁定题仍可点 `Change to No`。**（2026-11-06 本地联调时按设计稿改：审核期间本季其他锁定题置灰、不能再申请；更晚季度照旧可申请并顶掉旧申请。）**<br>• 在比待审核申请更早的季度不能申请：`Change to No` 置灰，提示 `A rollback request for {Q4 2026} is pending review.` 这种情况只在跳过一季、回头补填时出现。Founder 要等审完：被拒则更早的季度还能补、可再申请；获批则该季度算已提交，更早的季度按 CF6 封住。<br>• 文案不补：`Change to No` 弹窗不提示会顶掉旧申请；被新申请顶掉的申请，作废页沿用设计稿那段说明，申请记录不存作废原因。
9. 点 Apply 时页面上还没保存的作答怎么处理。<br>**定（2026-11-05）：直接丢掉。** 已存进草稿的作答照常保留，只丢页面上没保存的部分。Apply 后页面按服务端状态刷新为审核中，审核页显示最后一次保存的草稿。没保存的作答只可能在锁定题之后：获批时这些题本来就不用答；被拒时 Founder 重新答即可。
10. 回退一道题，会把它之后已锁定的进度一起清掉（逐题终止），弹窗是否要提示。<br>**定（2026-11-05）：不提示。** 答 No 后后面的题置灰，这条规则 Founder 平时就熟悉；Apply 后页面上后续题目置灰，本身已经说明了。
11. 弹窗 1、2 只提到晚于本期的草稿。按 CF8，早于本期的草稿也会删掉：L 与本期之间的季度，以及首次提交时的任意季度。这部分怎么告知用户（即 §11-①）。<br>**定（2026-11-05）：不提示，直接删。** 提交后那些季度按 CF6 封住，草稿留着也交不了，是垃圾数据。封住更早季度本来就不提示，和第一个需求一致。弹窗 1、2 按设计稿原样做。弹窗 1 本来也碰不到这种情况：早于 L 的季度存不了草稿。
12. 弹窗 3 和弹窗 1 或 2 的条件同时成立时显示哪个：有待审核的申请，又有要删的草稿。<br>**定（2026-11-05）：合成一个弹窗。** 例：2026 Q4 有待审核申请，2027 Q2 有草稿，Founder 提交 2027 Q1。标题和按钮用弹窗 2 的；正文在 `Continue?` 前加弹窗 3 那句。弹窗 1 与弹窗 3 同时成立的情况见第 15 条，合并方式相同。
13. 审批人打开已批准、已拒绝或已撤回（如果加撤回）的申请时显示什么。设计稿只画了已作废这一种。<br>**定（2026-11-05）：进正常的 Founder 药丸，顶部提示一句。** 邮件链接带申请 id，页面按「URL 里的申请 id + 该申请当前状态」决定显示什么：<br>• 待审核：审核卡片 + 高亮 + 审批人可见的 Refuse / Approve；<br>• 已作废：设计稿的作废整页；<br>• 已批准、已拒绝：Founder 药丸恢复正常，顶部提示 `This request has already been processed.`，不显示谁处理的。显示后从 URL 去掉申请 id，刷新不再重复提示。<br>• URL 没带申请 id（站内点进来）时不提示，有待审核申请才显示卡片。<br>• 两人同时审批时，后点的那位 Approve / Refuse 被拒，也显示这句提示并刷新页面（第 5 条）。
14. 批准邮件写的是「草稿保留」，和第 2 条的建议（作废）冲突，随第 2 条一起定。<br>**定（2026-11-05）：不冲突了**。第 2 条改为保留，设计稿和需求文档的文案照用。
15. 有待审核申请时，提交比它**更早**的季度怎么办。需求只写了「提交更晚的季度 → 申请作废」。例：L = Q2，Q4 有待审核申请，Founder 补交了 Q3。Q4 的锁定基线由 Q2 变为 Q3，而且按 CF8 Q4 的草稿会被删掉。Q4 的申请要不要作废？（2026-11-05 讨论第 8 条时发现）<br>**改（2026-11-10，测试问题，需求方定）：更早的季度在审核期间直接冻结，不能存草稿、不能提交（RB6），自然也就不会作废申请；下面 11-05 的结论只剩「提交更晚的季度 → 作废」仍成立。**<br>~~定（2026-11-05）：作废。~~ 有待审核申请时，提交该维度任何其他季度，申请都作废，提交前弹弹窗 3。<br>• 包括两种情况：重复提交 L（例：L = Q3，Q4 待审核，Founder 改了 Q3 没锁定的题后重交），以及补交跳过的季度。<br>• 重复提交 L 时又有 Q4 草稿要删，弹窗 1 与弹窗 3 合成一个：标题和按钮用弹窗 1 的，正文加弹窗 3 那句（同第 12 条）。<br>• 由此审核期间基线不会变，草稿也不会变（另须在审核期间禁掉该季的 Reset 和删草稿附件）。申请不用自带作答快照：批准时按基线现算提交内容，审核页直接读草稿（第 2 条已改）。
16. 审核期间 GS 发布了新版题库怎么办。按 CF4，换版后不锁定，被回退的题也随之解锁，申请就失去了意义；Founder 的草稿还绑定在旧版上。可选（推荐在前）：<br>• A：发布新版时，作废该组织下所有待审核申请。换版后 Founder 在新版里直接答 No 即可，不用再审批；审批人看到的是作废页。<br>• B：申请保留，批准时按草稿绑定的旧版提交。要先确认现有提交是否允许按旧版提交。<br>• C：批准时才检查，版本变了就不让批准，并把申请作废。<br>（2026-11-05 讨论快照时发现）<br>**定（2026-11-05）：A。** 发布新版题库时，作废该组织下该维题集版本号变了的维度的待审核申请。只改维度配置（权重、名称）不算换版，与 CF4 同口径。作废后 Founder 那边申请状态解除，在新版里照常填写。审批人从邮件进来看到作废页，说明文案对不上，与第 8 条一样接受。
