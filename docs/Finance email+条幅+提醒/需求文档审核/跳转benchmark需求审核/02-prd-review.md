# redirectToBenchmark PRD 审核报告

> 评审日期：2026-04-22
> 评审对象：`Redirect_to_Benchmark_Dashboard需求.md`（副本：`docs/redirectToBenchmark/01-prd.md`）
> 已加载项目上下文：`CLAUDE.md`、`CIOaas-web/CLAUDE.md`、`~/.claude/standards/common.md`、`CIOaas-web/config/routes.ts`、`CIOaas-web/src/pages/companyFinance/benchmark/*`、`CIOaas-web/src/pages/companyFinance/FinancialEntry/*`；项目级 `.claude/standards/` 未找到（跳过）

---

## 一、评分仪表盘

| 维度 | 评分 | 说明 |
|------|------|------|
| 语义与表述 | 3/10 | 大量歧义句、中英混排、残缺语句（如 "Benchmark results for have been updated"）、术语与仓库不一致 |
| 功能完整性 | 3/10 | 无 SC/AC 编号；失败/取消/并发/多次提交路径全部缺失；"条幅" 机制定义不完整 |
| 操作闭环 | 3/10 | 跳转后是否清/叠加现有筛选、Toast 多次触发如何合并、条幅关闭规则均无结论 |
| 数据一致性 | 4/10 | "closed month"、"新月份"、"Benchmarking 页面" 等关键对象口径未定；与已实现的 DATA+BENCHMARK 双维度筛选不匹配 |
| 权限覆盖 | 2/10 | 仅笼统写 "有该公司权限的人"，未对齐 `roleType` 与仓库 RBAC；通知/条幅可见范围未按角色拆分 |
| 业务规则 | 2/10 | 无集中 BR 章节；跨场景交叉引用错误（§2.1 引用 "场景2.3" 实际不含条幅文案） |
| 编号与可追溯性 | 1/10 | 全文无 SC/BR/AC 编号，下游 TDD/QA 无法追溯 |
| **综合** | **2.6/10** | **❌ 阻塞：存在多处 P0，须先修订 PRD 再进入 TDD** |

---

## 二、评审通过项

- ✅ 核心价值陈述清晰（"加速数据审查和决策流程"）
- ✅ 区分了"手动输入"与"非手动同步"两类触发路径，思路合理
- ✅ 预设过滤器的业务动机合理（与现有 Benchmark 页 `DATA` / `BENCHMARK` 两组 pill filter 的设计一致）

> 通过项仅此三点——PRD 篇幅较短，其余条目多为描述性标语，未构成可验收内容。

---

## 三、问题与建议

> 修订类别：**可自动修订** | **需用户决策**

### 3.1 主问题表

| # | 问题分类 | 问题描述 | 严重程度 | 是否阻塞 | 修订类别 | 建议 |
|---|----------|----------|----------|----------|----------|------|
| 1 | 编号缺失 | 全文无任何 SC-xx / BR-xx / AC-xx 编号，下游 TDD 无法引用 | P0 | 阻塞 | 可自动修订 | 按 project-conventions §2 补全：SC-01 手动输入跳转、SC-02 非手动同步通知；BR-01~BR-0x；AC-01~AC-0x |
| 2 | 术语不一致 | 文中"Company Benchmarking页面"在仓库中不存在。实际页面位于 `companyFinance/benchmark/Index.tsx`（路由入口 `/Finance`），菜单/页标题为 **Benchmark**，不是 Benchmarking | P0 | 阻塞 | 需用户决策 | 将 "Company Benchmarking页面" 统一改为 "公司财务 Benchmark 页（Finance → Benchmark）"，并明确跳转目标 URL（当前仓库是 `/Finance?tab=benchmark` 或相当 anchor，由 TDD 确认） |
| 3 | 关键对象未定义 | "closed month" 未定义：指代 (a) 用户输入表单里的 period 字段？(b) 后端 `fi` 模块某个状态字段？(c) 财年关闭动作？三种口径结果完全不同 | P0 | 阻塞 | 需用户决策 | 在 PRD 增加"数据定义"小节：给出 closed month 的字段来源、取值范围（年月）、成功关闭的判定（提交动作 vs 月结审批） |
| 4 | 触发时机歧义 | 场景1 "提交新closed month成功后"——在现有 FinancialEntry 页有 Save Draft / Commit / OCR Upload / Manual Input 多种操作。哪些算"提交成功"？ | P0 | 阻塞 | 需用户决策 | 明确列出触发动作白名单，例如：① 手动表单点击 Commit 成功；② OCR 上传后审核通过；草稿保存不触发 |
| 5 | 闭环缺失：失败路径 | 仅描述成功后跳转，未定义：提交成功但 Benchmark 数据尚未计算完成、提交成功但 peer group 缺失（UI 已有 Peer Fallback）、跳转目标加载失败、用户在跳转中点浏览器返回等情况 | P0 | 阻塞 | 需用户决策 | 新增 §错误处理：为每种失败态明确用户所见（如"Benchmark 计算中"占位 + 过 N 秒自动刷新） |
| 6 | 过滤器语义错位 | "基准视图：Actuals – Internal Peers"在现有 UI 中对应**两个独立 pill group**：`DATA=Actuals`（已实现）+ `BENCHMARK=InternalPeers`（已实现，多选）。PRD 把它描述成单一"视图"会误导 TDD | P0 | 阻塞 | 可自动修订 | 改写为："预设 `DATA` 过滤器为 `Actuals`（单选），`BENCHMARK` 过滤器为 `InternalPeers`（即使允许多选也仅选此项）" |
| 7 | 条幅内容未定义 | §2 场景1 步骤2 写 "条幅内容见场景2.3"，但场景 2.3 定义的是 Toast 文案而非条幅文案；条幅文案在全文中**从未出现** | P0 | 阻塞 | 需用户决策 | 显式给出条幅文案（英文 + 中文），明确"条幅出现在 FinancialEntry 页顶部、是否可关闭、关闭持久化范围" |
| 8 | 条幅/Toast 机制混淆 | §2.1 step2 说"有条幅提示"，§2.3 的交互里却说"跳转完成后条幅关闭后续解除通知"——条幅是针对其他用户在 FinancialEntry 的视觉元素，Toast 是针对当前用户登录时的弹层，两者不应互相解除 | P0 | 阻塞 | 需用户决策 | 分别为"条幅"与"Toast"写独立的显示/消失规则表 |
| 9 | 通知持久化缺失 | §2 场景2 step2 说"下次登录时显示" + "按照用户通知"——后半句语义残缺；且未说明通知是否走 `alertConfiguration` 现有通道、TTL、是否多端同步、重复同步事件如何合并 | P0 | 阻塞 | 需用户决策 | 补充：通知存储位置（后端 table/现有消息中心）、去重策略（同公司+同月份合并为一条）、TTL、已读状态同步 |
| 10 | Toast 文案残缺 | 场景 2.3 文案 "Benchmark results for have been updated"——`for` 后缺变量（公司名？月份？） | P0 | 阻塞 | 需用户决策 | 补全为 "Benchmark results for **{companyName}** ({closedMonth}) have been updated based on the latest financial data." |
| 11 | 权限与 RBAC 未对齐 | "有该公司权限的人"在仓库中映射到多种角色：Admin（roleType ≤ 2）、Finance Viewer、Company Member 等。条幅/Toast 对每类角色是否都显示？提交人与非提交人是否看到不同内容？ | P0 | 阻塞 | 需用户决策 | 增加"权限矩阵"表：列=角色（Admin/Member/Viewer），行=[看见条幅, 收到 Toast, 可点击跳转]，值=Y/N |
| 12 | 多公司场景缺失 | 用户具备多公司权限时，Toast 是否按公司堆叠？点击跳转是否自动切换 `chooseCompanies` 上下文？ | P1 | 阻塞 | 需用户决策 | 增加 SC：多公司收到多条通知时的展示顺序、每条对应一次公司切换 |
| 13 | 连续提交去重 | 提交人一次性补录 2~3 个月的 closed month 数据，是否跳转 N 次？还是仅跳转最新月？ | P1 | 阻塞 | 需用户决策 | 规则示例：以"最后一次提交"为跳转依据，单次跳转；filter 使用该次月份 |
| 14 | 第三方同步范围 | §2 说"QuickBooks或其他第三方系统"——"其他"涵盖范围未定；目前仓库 `connectorsManagement` 接入的还有哪些？是否都触发本流程？ | P1 | 阻塞 | 需用户决策 | 列出白名单连接器；对新接入连接器默认行为给出规则（默认触发 / 默认不触发） |
| 15 | 用户既有筛选被覆盖 | 用户当前已在 Benchmark 页设置了其他筛选（如不同 peer group、不同 category），点击 Toast 跳转时预设值是**覆盖**还是**并入**？ | P1 | 阻塞 | 需用户决策 | 建议：始终覆盖为 `Actuals + InternalPeers + 新月份`；并在 URL 带参数 `?preset=redirect` 以便后续分析 |
| 16 | 并发场景 | 提交人点 Commit 同时后端 QBO 同步 webhook 到达——是否两条触发都生效？ | P1 | 阻塞 | 需用户决策 | 规则：同公司 30 秒内只触发一次跳转/通知，以最早一次为准 |
| 17 | 非功能需求缺失 | 无性能、响应时间、跳转延迟（Financial Entry → Benchmark 加载时长目标）、埋点、可访问性要求 | P2 | 非阻塞 | 需用户决策 | 建议：跳转 ≤ 800ms 内开始加载新页；Toast 需 ARIA `role="status"`；增加 `redirect_source` 埋点 |
| 18 | 状态完整性缺失 | 加载态（Benchmark 计算未完成）、空态（peer group 缺失时是否仍跳转）、错误态（Benchmark 页接口 500）无定义 | P2 | 非阻塞 | 需用户决策 | 补充状态定义矩阵 |
| 19 | 格式/章节结构 | 仅有 §1、§2 两章；缺少标准模板中的"角色与权限 / 业务规则 / 数据定义 / 验收标准 / 非功能需求 / 范围外"等章节 | P1 | 阻塞 | 可自动修订 | 按 `gen-requirements/template.md` 的章节骨架补全 |
| 20 | 中英文混排 | "基准视图" vs "Benchmarking" vs "benchmark"；Toast 文案中英掺杂；正文存在"新closed month"这种直接嵌入英文名词 | P1 | 非阻塞 | 可自动修订 | 全文统一：界面术语用英文原词（Benchmark、Actuals、Internal Peers），描述性中文保持纯中文 |

### 3.2 表述与歧义问题

| # | 位置 | 原文摘录 | 问题类型 | 建议改写 |
|---|------|----------|----------|----------|
| T1 | §1 功能目标 | "当用户提交新的财务数据时，系统自动引导用户查看最新的Benchmarking" | 歧义 + 不闭环 | "当用户成功提交一个新月份（closed month）的财务数据后，系统根据触发方式分别采用(a)**自动跳转**到该公司 Benchmark 页（手动输入），或 (b) **异步通知 + 手动跳转**（第三方同步），引导用户查看对应月份的 Internal Peers 基准对比结果。" |
| T2 | §1 关键特点 | "自动重定向机制（手动输入场景）；智能通知机制（非手动同步场景）" | 套话/水分 | 直接删除或替换为明确动作："手动输入 → 自动跳转；第三方同步 → Toast 通知 + 手动跳转" |
| T3 | §2.1 step2 | "提交人将跳转到Company Benchmarking页面；其他有该公司权限的人进入该公司Financial Entry页面，有条幅提示，条幅内容见场景2.3" | 前后不一致 + 闭环缺失 | "**提交人**：跳转到 Benchmark 页（Finance → Benchmark），自动应用预设过滤器（BR-03）。**同公司其他有权限用户**：下次打开 Financial Entry 页时顶部显示条幅 '{companyName}: Benchmark data for {closedMonth} has been updated. View benchmark →'，点击进入 Benchmark 页并应用同一组预设过滤器；条幅可关闭，关闭后在本用户-本月份维度持久化 30 天。" |
| T4 | §2.1 step3 | "用户无需手动配置过滤条件，立即看到最相关的基准对比数据" | 套话/水分 | 删除或并入 BR-03 规则描述 |
| T5 | §2.2 step1 | "QuickBooks或其他第三方系统自动同步新的财务数据到LG" | 歧义 | "由已接入 Connectors Management 的第三方系统（目前为 QuickBooks Online；其他连接器的启用由 BR-05 控制）自动同步新月份财务数据到 CIOaaS 后端 `fi` 模块" |
| T6 | §2.2 step1 | "系统识别closed month并可用" | 歧义/不闭环 | "系统在同步完成后检测到存在新的 closed month（判定条件：该月份首次达到 `period_status=CLOSED`），触发本 SC-02 流程" |
| T7 | §2.2 step2 | "而是在有该公司权限的用户下次登录时显示通知或toast消息，按照用户通知" | 语义残缺 | "向所有对该公司拥有查看权限的用户生成一条站内通知；下次该用户登录或从其他页面进入 CIOaaS Web 时，在当前页右上角以 Toast 形式呈现（BR-06 定义展示时机与去重规则）" |
| T8 | §2.2 step3 | "Benchmark Data Updated. Benchmark results for have been updated based on the latest financial data." | 语义残缺（缺变量）| "Benchmark Data Updated — benchmark results for **{companyName}** ({closedMonth}) have been updated based on the latest financial data. **[View] [Dismiss]**" |
| T9 | §2.2 step3 | "用户可点击通知中的链接，导航到Company Benchmarking页面 跳转完成后条幅关闭后续解除通知" | 不闭环 + 机制混淆 | 拆为两条：① 点击 View → 跳转 Benchmark 页 + 应用预设过滤器 + 标记通知已读；② 点击 Dismiss → 仅标记已读，不跳转。条幅与 Toast 是两个独立机制，不互相联动 |
| T10 | §2 基准视图 | "基准视图：Actuals – Internal Peers（实际数据 – 内部同业）" | 前后不一致（与实现）| "预设过滤器组合：`DATA pill = Actuals`（单选）+ `BENCHMARK pill = Internal Peers`（单选 / 或多选但仅选此项）+ `DATE pill = {closedMonth}`；VIEW 模式保持 Snapshot" |

---

## 四、待确认事项

| # | 问题 | 需要谁确认 | 是否阻塞后续设计 |
|---|------|-----------|----------------|
| Q1 | "closed month" 在后端 `fi` 模块的具体字段是什么？取值何时变更？ | 后端 owner / PM | 阻塞 |
| Q2 | Benchmark 页的稳定跳转 URL 结构（route + query params）？现在 `/Finance` 下 tab 切换无 URL 体现 | 前端 owner | 阻塞 |
| Q3 | 条幅与 Toast 的展示权限矩阵（按 `roleType` 划分） | PM + 安全/权限 owner | 阻塞 |
| Q4 | 第三方连接器白名单（当前仅 QBO？未来接入默认是否自动启用本流程） | PM + 集成 owner | 阻塞 |
| Q5 | 用户已有自定义筛选在跳转时**覆盖 vs 合并**的策略抉择 | 产品经理 | 阻塞 |
| Q6 | 连续补录多个月份时的去重规则 | 产品经理 | 阻塞 |
| Q7 | 通知是否复用现有 `alertConfiguration` 通道，还是新增独立 table | 架构师 | 阻塞 |
| Q8 | 手动提交 OCR 场景下，是以"上传即成功"还是"审核通过即成功"触发跳转？ | 产品经理 | 阻塞 |
| Q9 | 国际化范围：Toast 与条幅是否需要中英双语？仓库 default locale `en-US` | 产品经理 | 非阻塞但影响文案冻结 |
| Q10 | 跳转后是否需埋点（redirect_source、触发方式、是否点击 View） | 数据分析 | 非阻塞 |

---

## 五、假设（待验证）

- **A1**：跳转目标"Company Benchmarking页面"即 `CIOaas-web/src/pages/companyFinance/benchmark/Index.tsx`（当前没有独立顶层路由，通过 Finance 页内 tab 暴露）
- **A2**："Actuals – Internal Peers 视图"实际是现有 Benchmark 页 `FilterBar` 的两组 pill：`DATA=Actuals` + `BENCHMARK=Internal Peers`
- **A3**：条幅机制可复用 `FinancialEntry/components/SuccessBanner.tsx` 或其变体；Toast 使用 Ant Design `message` / `notification` API
- **A4**：通知持久化若无现成中心，则可新增 `benchmark_data_notification` 表，含 `user_id, company_id, closed_month, read_at, dismissed_at`
- **A5**：权限判定沿用现有公司权限 context，不引入新 RBAC 维度

---

## 六、建议补充到 PRD 的内容

**必须补充的章节（按模板顺序）**：

1. **§数据定义**：closed month 字段来源、period 格式、触发态判定
2. **§角色与权限矩阵**：按 `roleType` 枚举（Admin、Member、Viewer）× [看见条幅 / 收 Toast / 可跳转 / 可解除通知]
3. **§业务规则（BR）**，建议初稿：
   - BR-01：触发动作白名单（手动 Commit / OCR 审核通过 / QBO 同步 closed）
   - BR-02：跳转目标 = Benchmark 页 + 预设过滤器
   - BR-03：预设过滤器 = `DATA=Actuals` ∩ `BENCHMARK=InternalPeers` ∩ `DATE=closedMonth` ∩ `VIEW=Snapshot`；覆盖用户已有筛选
   - BR-04：Toast 去重——同公司同月份仅一条通知；Dismiss 永久有效
   - BR-05：第三方连接器白名单管理（初版：仅 QBO）
   - BR-06：通知 TTL（默认 30 天），超时自动失效
   - BR-07：条幅关闭持久化范围（用户×公司×月份）
4. **§验收标准（AC）**：每个 SC 至少 2 条可判定的 AC
5. **§错误处理**：Benchmark 加载失败、peer group 缺失、计算未完成、权限变更后通知已存在等
6. **§状态完整性**：加载态、空态、错误态、正常态四态定义
7. **§非功能需求**：跳转延迟 ≤ 800ms、Toast 可访问性（ARIA）、埋点字段
8. **§范围外**：移动端、其他财务对比视图（非 Benchmark）、邮件通知

**验收标准示例（供 PM 起草参考）**：
- AC-01：提交人点击 Commit 成功后 ≤ 1s 内跳转至 Benchmark 页；过滤器实际值与 BR-03 完全一致
- AC-02：同公司非提交人次日登录进入 Financial Entry 页，顶部条幅可见；点击"View"跳转后条幅消失且不再对该用户-该月份显示
- AC-03：QBO 同步触发后，拥有权限的 3 个用户登录各自均收到一条 Toast；任一用户 Dismiss 不影响其他用户

---

## 七、已自动修订项

> 本轮评审**未**对 `01-prd.md` 执行自动修订。理由：PRD 存在 **11 条 P0 阻塞问题**，修订必然涉及业务决策（场景、规则、权限、文案、机制分离），不属于"可机械修订"范围。等用户对待确认事项 Q1–Q8 给出答复后，再由 `gen-requirements` 重写或在本报告基础上回写 PRD。

| # | 位置 | 修订内容 | 类型 |
|---|------|----------|------|
| — | — | 无自动修订（全部为 P0 业务决策） | — |

---

## 八、质量关卡结论

**❌ 流水线阻塞 — 不进入 Step 3（gen-tdd）。**

**P0 阻塞项汇总（11 条）**：#1 编号、#2 术语、#3 closed month、#4 触发时机、#5 失败路径、#6 过滤器语义、#7 条幅文案、#8 条幅/Toast 机制、#9 通知持久化、#10 Toast 文案残缺、#11 权限矩阵。

**建议下一步**：

1. PM / 用户逐条回复 §四 Q1–Q8；
2. 按 §六建议补齐 PRD 章节，并给 SC/BR/AC 编号；
3. 回到 `/gen-step-all redirectToBenchmark` 流程，或直接执行 `/gen-requirements redirectToBenchmark` 基于本报告重写 `01-prd.md`；
4. 修订完成后重跑本评审（`/review-prd redirectToBenchmark`），确认 P0 清零后继续 Step 3。
