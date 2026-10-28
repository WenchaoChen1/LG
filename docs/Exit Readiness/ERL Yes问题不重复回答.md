# ERL Yes问题不重复回答

## 原始需求：

如果一个公司上个季度**已经回答了Yes的回答**，在这个季度就可以直接**不用他们继续回答了**



## ⭐需求解读：

### 功能定位：一次性进度评估，不是周期性复评

- ERL 用于判断一家公司当前的退出准备程度，输出的是"离可退出还差多远"这一最新状态。
- 并非所有公司都进入 ERL 评估。触发条件是：该公司已被投资一段时间、交易已显著获利、开始筹备退出——此时才启用 ERL。

- 它与 FI、KPA 等功能有本质区别：

  - FI / KPA：对同一组指标在不同时期反复打分，关注历史波动与趋势；

  - ERL：**不是周期性复评**，不记录波动曲线，只反映最新的退出就绪情况。

### 推进方式：进度条式单向推进，已达成项不复评（下方特殊情况申请流程除外）

- 把一个维度下的全部题目理解为一条正向进度条：
  - 本季度回答为 Yes 的题目 = **已达成的进度点，视为永久完成**；
  - **下季度不再重新回答这些题目，直接从未完成的题目继续推进；**
  - 举例：本季度推到 50%，下季度从 51% 开始答，而不是从 0 重答。

- **因此 ERL 不存在"同一题这次 Yes、下次 No"的回退场景——它只向前，不往回看。**
- 注：当前所有问卷均以维度为单位，填写问卷都是单个维度填写。ERL 的 stage gating 按维度走——FRL / PRL / BERL / RRL / TRL 五个维度（当前情况，维度可配），每个维度各自有 Stage，各自独立推进。

## 功能说明：

### ERL问题提交层面（所有维度适用）：

#### 主要需求变更：

进入新一季度填写时：

- 上一个已提交季度中回答为 Yes 的题目 → 自动锁定、折叠、不可无审批修改；
- 页面直接从上一个已提交季度中回答为 No 的题目开始显示；
- 用户只需继续推进剩余未完成的题目即可。

- **特殊情况申请流程（下一个需求）：对于上个季度最后一次提交已锁定的题目进行回退也是可操作的，但是需要走审批流程**

#### 关键前提：ERL 自有的时间轴（方便需求讨论）

ERL 的"历史 / 当前 / 未来季度"不看自然时间，也不看 Overview 页面显示时间，只看 ERL 提交层面的时间轴。

判定方式：以最后一次已提交的季度为锚点——
- 该季度本身 = 当前季度
- 该季度之前的所有季度 = 历史季度
- 该季度之后的所有季度 = 未来季度

▎ - 历史季度 = 2025 Q3 及以前
▎ - 当前季度 = 2025 Q4
▎ - 未来季度 = 2026 Q1 及以后

#### 首次提交规则：任意季度起步，提交后"封住过去"

- 首次填写：可自由选择任意季度 / 年度作为起点；
- 一经提交：该季度之前的所有历史季度统一置灰、不可再填写；已提交的历史季度也不可重复提交。

原因：一个维度下所有题目构成一条正向进度条。既然提交到该季度已达到一定进度，则逻辑上历史进度必然 ≤ 该进度，补录历史无意义；

#### 最后提交的季度可重复提交，不受限制

**仅限最新提交的那一个季度（即当前季度）允许重复提交。**

重复提交时：

- 锁定的题目还是跟首次答题时一样

- 不把该季度上一次提交作为"历史"去锁定其中的 Yes；
- 相当于在该季度原地重做一次。

原因：重复提交通常是因为上一次填错，需要修正，因此不能把错误答案当成已达成进度锁死。

#### 跨季度直提（跳季提交）规则

直接提交未来某个季度时，锁定题目仍以最后一次已提交记录中的 Yes 题为准，中间跨过的季度不参与锁定计算。

▎ 举例：当前最后提交季度为 2026 Q1，若直接提交 2026 Q3 → 2026 Q3 的锁定题目 = 2026 Q1 最新记录中的 Yes 题目（Q2 被跳过，不影响锁定基线）。

#### 特殊情况说明

- 某维度上个提交季度的问题全部为YES，之后也不需要再提交，默认之后所有的季度均为已提交且回答为YES。



### Overview显示层面（适用所有维度&两个端）：

- 显示的逻辑和规则不变，依然与FI模块同步，FI显示哪个月，ERL就显示哪个月所在的季度的数据
- Overview季度变化时，上个提交季度全部为YES的维度就显示绿点已提交，details页面也对应显示所有YES记录



### 草稿：

#### 未来季度草稿失效规则

触发失效的两种情形：

当"锁定题目的基线"因为新的提交动作发生变化时，所有相关的未来季度草稿一律作废。具体包括：

情形 A：当前季度被重复提交
- 已保存了未来某季度的草稿；
- 用户又对最后已提交的那个季度重新提交了一次；
- → 该草稿作废。

情形 B：
- 已保存了多个未来季度的草稿；
- 用户对其中中间某一季度做了正式提交；
- → 该中间季度之后的所有未来季度草稿全部作废。

情形 C：
- **特殊情况审批流程：** 对于最后提交季度已锁定的题目进行回退
- 已保存未来季度的草稿
- 审批通过后"锁定题目的基线"发生变化
- → 草稿作废。

#### 作废的原因

根因：锁定题目完全由"最新一次正式提交的数据"决定。

- 不论是重复提交当前季度、对锁定题目进行回退，还是正式提交多个草稿月的一个中间季度，都会刷新"最新提交记录"；
- 一旦基线刷新，原草稿所依赖的锁定题目集合就可能发生变化（例如原本未锁定的题目变成已锁定，或反之）；
- 此时草稿里已填写的答案，可能落在新锁定的题目上，逻辑冲突；
- 因此草稿失去意义。

#### 为什么不"自动把草稿转为正式提交"

- 锁定题目有变化导致此历史记录无意义；
- 所以草稿只能作废处理，不能被动晋升为提交。

#### 加UI 提示

在用户执行以下任一动作时，提交确认弹窗需加提示：

- **有未来月草稿的情况下，对最后已提交季度做重复提交；**  
Title: Re-submit current quarter?  
Body:  
▎ You're about to re-submit {current quarter, e.g., 2025 Q4}.  
▎ You have {N} future-quarter draft(s) saved ({2026 Q1, 2026 Q2, ...}).  
▎ Re-submitting will refresh the locked-question baseline. All future-quarter drafts above will be permanently discarded and must be re-entered against the new baseline.  
▎ Continue?  

Buttons: Cancel ｜ Submit and discard drafts
 
- **对多个未来季度草稿中的一个中间季度做正式提交；**  
Title: Submit this quarter?  
Body:   
▎   You're about to submit {selected quarter, e.g., 2026 Q2}.  
▎ There are {N} future-quarter draft(s) scheduled after this quarter ({2026 Q3, 2026 Q4, ...}).  
▎ Submitting will refresh the locked-question baseline. All drafts for quarters after the one being submitted will be permanently discarded.  
▎ Continue?  

Buttons: Cancel ｜ Submit and discard later drafts

- **有未来月草稿的情况下，对于最后提交季度已锁定的题目进行回退，提交审批。提示语与上面不同（应提示审批通过后草稿将作废）**  
Title: Submit rollback request for approval?  
Body:  
▎ You're requesting a rollback on locked question(s) in {last submitted quarter, e.g., 2025 Q4}. This change takes effect only after approval.  
▎ You have {N} future-quarter draft(s) saved.  
▎ ⚠ If approved, the locked-question baseline will change, and all future-quarter drafts will be automatically discarded at the moment of approval and cannot be recovered.  
▎ If the request is rejected, your drafts remain untouched.  
▎ Submit this request?  

Buttons: Cancel ｜ Submit for approval

