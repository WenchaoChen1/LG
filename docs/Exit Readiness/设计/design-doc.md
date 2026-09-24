> 关联文档：
> - **需求文档（本设计的唯一权威来源）**：[../../Exit_Readiness_PRD.md](../../Exit_Readiness_PRD.md)（**2026-09-04 修订版**，当前为 `49d9a29`）
> - **需求方裁决（2026-09-06）**：① **提交粒度＝维度级**；② ~~**维度只停用不硬删**~~ → **v4.8 订正为「维度可物理删除」**，**维度集合与权重按期次快照**（快照机制不变，见 §0.14）；③ **展示期次＝closed month 所在季度，该季两端无提交即空态、不回退**。三条均已落入本版，见 §0.10-R1 / R2 / R3
> - **需求方裁决（2026-09-08）**：① **数据模型重构**（表数 12 → 11；维度配置去版本化、期次绑定表删除、题库版本线改为每维一条、新增发布时维度快照表）；② **删除维度改软删**（`status` = `Active` / `Inactive`）；③ **权重不做任何快照、接受历史漂移**（§13-Q21 重新打开）；④ `erl_assessment` 删 `submission_seq` / `is_latest`，SOT 改按 `submitted_at DESC, id DESC`。逐条见版本说明 v4.15
> - **需求方裁决（2026-09-09）**：**维度的「删除」按「是否进入过已发布题库版本」分成两个动作** —— 从未进入过 ⇒ 垃圾桶 = **真删**（新增 `deleted` 列，行留在表里但**整页不再出现、无恢复入口**）；进入过 ⇒ **禁止删除**，图标改**电源按钮** = 停用（`status = 'Inactive'`，即旧行为），改由常显的 `Deactivated Dimensions` 区块承载与恢复；**`Show deactivated` 开关整个撤下**。**§13-Q24 由「已关闭：无条件允许删除」改判为「有前置拦截，但判据是「是否进入过已发布题库版本」而非「有无历史数据」」**。逐条见 §0.21
> - **需求方裁决（2026-09-09，当日第二批 —— C7 题库版本历史页）**：① **版本下拉只列已发布版本**，草稿不进下拉（过滤做在前端 hook，**接口 25 契约不变**）；② **C7 维度卡头不显示 `Retired` 灰标**，维度卡与其题目照常整卡展示 ⇒ C7 **不再取接口 23**，与「今天的维度配置」彻底解耦。**§0.17-K1 由此关闭（取值＝整条取消）**。逐条见 §0.22
> - **PRD 回写建议**（本设计发现的 PRD 待改项，含可直接粘贴的改法）：见 §0.10-④
> - 原型（Lovable，已发布，**仅作 UI 参考**）：`https://exit-readiness-hub.lovable.app`（项目 `exit-readiness-hub` / `ERL-Portfolio portal`）。**2026-09-03 03:32 更新过，当日已重抓并反解，见 §2.3.1** —— 该版原型也换成了 Yes/No 逐级解锁 + 五维权重，多数结论印证 v4.0；10 处与 PRD 冲突的地方一律按 PRD。**当日晚些时候 `/erl-configuration` 又改了一版（两个顶层 Tab + 题目表格 + `View history`），见 §2.3.1-⑤，v4.1 据此调整 C 模块 UI**。**2026-09-04 补充**：`/erl-configuration/history` 在已发布站上是 404（该路由不在已发布构建里），v4.2 依据的是需求方提供的整页截图，见 §2.3.1-⑥。**2026-09-06 补充**：需求方提供 ERL Card 的 Gap 区块整块截图，v4.4 据此定档该区块 UI（§0.10-D4）。⚠️ **原型全部为五维形态，在「维度可增删」这一点上已整体过期**（§0.10-D1）
> - 后端规范：[../../../CIOaas-api/standards/architecture.md](../../../CIOaas-api/standards/architecture.md) · [../../../CIOaas-api/standards/coding.md](../../../CIOaas-api/standards/coding.md)
> - Python 规范：[../../../CIOaas-python/standards/architecture.md](../../../CIOaas-python/standards/architecture.md) · [../../../CIOaas-python/standards/coding.md](../../../CIOaas-python/standards/coding.md)
> - 前端规范：[../../../CIOaas-web/standards/architecture.md](../../../CIOaas-web/standards/architecture.md) · [../../../CIOaas-web/standards/coding.md](../../../CIOaas-web/standards/coding.md)
>
> 阶段：④ 设计 | 版本：**v4.60** | 日期：2026-09-20 | 范围：ERL Card（含 Gap 区块）/ 维度详情 / 全维 Score Details（**双端可达**）/ 双端填报（**Yes/No 逐级解锁 + 维度级提交**）/ 题库配置（**`Question Library` / `Dimension Configuration` 两个顶层 Tab + 题库版本历史页**）/ 基准 / Goldie 差距分析（**已回归 V1，含 Share**）/ 组合层 ERL Tab

# Exit Readiness（ERL）设计文档 V1

## 版本说明

| 版本 | 日期 | 依据 | 说明 |
|------|------|------|------|
| v1 / v2 / v2.1 | 2026-08-26 | Lovable 原型 + Lovable story | 原型反解产物。**部分结论已被 PRD 推翻**，见 §0.2 |
| v3.0 | 2026-08-27 | `docs/Exit_Readiness_PRD.md` | 按 PRD 全量重校，共 **20 条修正**（9 处需求冲突、9 项缺失补齐、2 项无 PRD 依据的自创设计），逐条见 §0.2 |
| v3.1 | 2026-08-27 | **原型新截图**：`/readiness/benchmark`（D1）、`/readiness/benchmark/add`（D2） | **基准模块（D）按原型重做**：每期次由「两个总分」改为「五维各两个分」；D1 定为 `Latest by Dimension` + `Record History` 双卡；D2 由 Modal 改为**独立页面**。逐条见 §0.3 |
| v3.2 | 2026-08-28 | `docs/Exit_Readiness_PRD.md` **2026-08-28 修订** | 按 PRD 修订重校，共 **4 条**：题库新增 **Publish 发布态**（新增需求，影响面最大）；F2 `View` 目标由 Company Overview 改为 **Score Details 页**；每维状态摘要三值枚举**由 PRD 明文降级为设计占位**；打分格式的「0/1 二元 / 光谱型」表述从 PRD 移除。逐条见 §0.4 |
| v3.3 | 2026-08-28 | **需求方对 §13-Q11 的裁决**（2026-08-28） | **题库改为版本化**：v3.2 的「只有新增题需发布」作废 —— **新增 / 编辑 / 删除 / 重排全部经 Publish 才生效**。`erl_question_config` 上的状态位改为独立的**版本表 + 写时复制草稿版本**；评估绑定题库版本快照；在填草稿按 `question_key` 重基。逐条见 §0.5 |
| v3.4 | 2026-08-28 | **需求方裁决**（2026-08-28）：「保留旧答案，以正在编辑的版本为准」 | **重基（rebase）整体删除，改为版本锁定**：评估创建时绑定当时最新已发布版本，此后**无论题库发布多少版都不跟随**（Founder 用 v3 打开就一路 v3，GSV 后填用 v4）。据此关闭 §13-Q13 ~ Q16 四条边界，并删掉重基链路的全部实现物。逐条见 §0.6 |
| v3.5 | 2026-08-28 | **需求方裁决**（2026-08-28）：「F2 `View` 跳 A4 全维 Score Details 页」+ 指定原型 `/readiness/overall`（标题 `Score Details`）为 UI 依据 | **复活 A4 全维 Score Details 页**：纳入 V1，新增路由 `/exitReadiness/scoreDetails` 与**接口 22** `GET /erl/scoreDetails`；F2 `detailUrl` 由「维度详情页 + 默认 FRL」改为指向 A4（不带维度）。据此关闭 §13-Q12。逐条见 §0.7 |
| v3.6 | 2026-08-28 | `docs/Exit_Readiness_PRD.md` **当日第二次提交**（`4442613`，10:24）+ 全文一致性复核 | **Founder 端补齐「每维手动整体分 + 软确认弹窗」**：PRD §3.3 当日 10:24 追加了与 §3.4 完全同款的要求 → 手动维度分由「仅 GSV」改为**双端**，§13-Q3b 由 PRD 自身关闭。另订正 6 处内部不一致 + 定档 5 项此前留白。逐条见 §0.8。⚠️ **本版的核心结论（双端手动分 + 软确认弹窗）已被 PRD 2026-09-02 修订整体删除，见 §0.9-1** |
| v4.0 | 2026-09-03 | `docs/Exit_Readiness_PRD.md` **2026-09-02 / 09-03 修订**（4 次提交：`621e857` / `a6b0906` / `74f25df` / `6d8c800`）**+ 原型 2026-09-03 重抓**（§2.3.1） | **计分模型换底 + 综合分改加权 + 手动分整体删除**，属结构性变更，故进大版本：① 打分格式由「1–9 占位 + 双题型」**定档为 Yes/No 逐级解锁**，维度分 = **最后一个全 Yes 的 level**（0–9 整数）；② 综合分由「五维简单平均」改为**按配置权重加权**，配置页新增权重设置（新表 + 2 个接口）；③ v3.6 刚补的**双端手动维度分与软确认弹窗全部作废**；④ **Founder 端不可见 GSV 分数**，⑤ **雷达图仅组合端显示**；⑥ DI 卡片由「系统级隐藏」改为**移到 FI 卡片下并保留入口**（`erl.enabled` 开关删除）；⑦ 题库 / 权重作用域由「全局单份」改为**按组织（租户）**；⑧ 附件补 **10MB/个** 上限与 ~~**GSV 维度级附件**~~（**v4.6 作废**：维度级附件取消，双端统一题级，§0.12）；⑨ PRD 删掉的三块展示（状态摘要 / Strengths & Priority Gaps 的 §5 依据 / Data Sources & Cadence）随之处置；⑩ Goldie（E 模块）被 PRD 标为「待定功能」。逐条见 §0.9 |
| v4.1 | 2026-09-03 | **原型 `/erl-configuration` 当日改版**（仅 UI 参考，见 §2.3.1-⑤） | **配置页（C 模块）UI 按新原型对齐 —— 纯 UI 调整，PRD 未变，计分口径（§7.1 / §7.2）、权限口径（§4.2 / §4.3）、数据模型（§5）一律不变**：① 配置页由「五维 Tab + 第 6 个 `Weights` Tab」改为 **`Question Library` / `Dimension Weights` 两个顶层 Tab**（题库 Tab 内才是五维 Tab）；② 题库由折叠面板改为**题目表格**（列 `QUESTION / ERA BAND / SOURCE / ACTIONS` + 最左拖拽列，按 Era band 分组、每组一条组头行）；③ 权重面板**取消滑条**，只留五个百分比输入平铺一行；④ 跨 Era band 移动改为**题目行内 `Era band` 下拉**（走接口 12），v4.0 的「跨 band 移动请走编辑表单」作废；⑤ 新增 **C7 题库版本历史页**（路由 `/exitReadiness/configuration/history`）与**接口 25** `GET /erl/question/version`，入口是题库 Tab 的 `View history`。逐条见 §2.3.1-⑤ |
| v4.2 | 2026-09-04 | **原型 `/erl-configuration/history` 截图**（仅 UI 参考，见 §2.3.1-⑥） | **C7 由「版本清单表」改为「版本快照页」—— 纯 UI 调整 + 一个只读接口，PRD 未变，计分 / 权限 / 数据模型一律不变**：① C7 页面由「一张版本列表表格」改为**「页头版本下拉 + 五维各一张只读题目表」**，即选一个版本看**那一版的整份题面**；② 为此新增**接口 26** `GET /erl/question/version/{versionNo}`（接口 25 只给版本元数据，取不到题面）；③ 接口 25 **保留不变**，改作 C7 的版本下拉数据源。逐条见 §2.3.1-⑥ |
| v4.3 | 2026-09-04 | **原型 Company Overview 截图 + PRD §3.1 原文复核** | **§8.6 订正：三卡不是纵向排列，而是「左列 FI → DI ＋ 右列 ERL」两列** —— 这不是需求变更，是 v4.0 落地时的**误读回正**：PRD §3.1 说的是「原 DI 卡片的**位置**由 ERL 卡片替代」，而存量 Company Overview **本来就是左右两列**（`.btmContent` 为 `row` + `space-between`，`.finanStyle` / `.deveStyle` 各 604px，左 FI 右 DI），「原 DI 位置」= **右列**；v4.0 把「位置」读成了「顺序」，顺手把两列压成了单列纵排。原型截图与 PRD 原文一致，故按原型回正。逐条见 §8.6 |
| v4.4 | 2026-09-06 | `docs/Exit_Readiness_PRD.md` **2026-09-03 / 09-04 修订**（9 次提交：`57225d2` / `8f2fcc0` / `9a203ce` / `0333162` / `08b7a32` / `8324a3f` / `4f959bb` / `273671a` / `49d9a29`）**+ 需求方 2026-09-06 三条裁决 + ERL Card Gap 区块截图** | **提交粒度换底 + 维度动态化 + Goldie 回归 V1**，三处均为结构性变更：① **提交单元由「整卷」改为「单个维度」**（需求方裁决，§13-Q19 随之关闭）；② **维度不再是五个固定枚举**，改为租户级可增删排序的配置数据，维度集合与权重**按期次快照**，历史分数永不漂移（§13-Q21 关闭）；③ **Goldie（E 模块）撤销「待定功能」标记回归 V1**，并换成 **GSV 生成 → Share to founder** 的单向分享模型，双 audience 双 prompt 作废（§13-Q22 关闭）；④ 展示期次缺省由「最新已提交期次」改为 **closed month 所在季度**，该季无提交即**空态、不回退**（新增对 FI 域的跨域依赖）；⑤ **A4 全维 Score Details 双端可达**（`Full View`），每张维度卡各带 `Add New` + `View History`，§13-Q17 的旧裁决被 PRD 推翻；⑥ 填报页按钮组定档 `Save as draft / Cancel / Reset / Submit`，Reset 需新接口（§13-Q23 关闭）；⑦ 题库更新在填报页给**非阻断提示**（推翻「无任何提示」的旧承诺）；⑧ 历史列表删 `Completion`、补 `Submitted`、分数改维度口径；⑨ 配置页第二 Tab 由 `Dimension Weights` 扩为 `Dimension Configuration`。逐条见 §0.10 |
| ~~v4.5~~ | 2026-09-06 | **需求方 2026-09-06 追加要求：两张版本表补「是否当前在用」的标记列**（⚠️ **本版已整条失效**：`erl_dimension_config_version` 于 2026-09-08 整表删除，`erl_question_config_version.is_latest` 于 **2026-09-09 删列** —— 两个标记列都不存在了，判据回到 `status` + `version_no`，见 §5.1.1） | **`erl_question_config_version` / `erl_dimension_config_version` 各加一列 `is_latest`（boolean，not null，默认 `false`）**，标识该行是否为**当前正在使用的最新版本**：题库版本标在**最新已发布版本**上（`DRAFT` 恒 `false`），维度配置版本标在**当前生效版本**上；两表各加一个**组织内**部分唯一索引 `WHERE is_latest` 保证唯一。取「最新已发布版本 / 当前生效版本」由「按 `version_no` 倒排取第一条」改为**直接命中标记列**，Publish（接口 21）与 Save（接口 24）在同一事务内完成标记的转移。**纯模型与取数路径调整，计分口径、权限口径、接口契约、UI 一律不变。** 逐条见 §0.11 |
| v4.6 | 2026-09-06 | **需求方 2026-09-06 追加裁决：附件双端统一题级** | **附件回退 v4.0 的「扩粒度」**：① **GSV 维度级附件取消**，Founder 与 GSV **一律逐题挂附件**（10MB/个上限不变）；② 表名由 `erl_assessment_attachment` **改回 `erl_answer_attachment`**，`answer_id` 收紧回 **not null**，**`assessment_id` 列删除**（该列当初只是「维度级附件没有作答可挂」时的归属列）；③ 接口 4 / 5 删入参 `dimensionAttachments`、接口 3 删顶层出参 `attachments`，前端 `DimensionAttachmentPanel` 与 B2 维度级附件区整体删除。**本裁决推翻 PRD `621e857`（2026-09-02）写入的两处措辞，须回写 PRD（新增 M13）。** 计分口径、权限口径、题库与维度配置一律不变。逐条见 §0.12 |
| v4.7 | 2026-09-07 | **需求方 2026-09-07 追加要求：配置页可替租户做 ERL 配置** | **C 模块（题库 + 维度配置）11 个接口新增可选入参 `organizationId`**：缺省 = 登录态组织（行为与 v4.6 逐字节一致），传值则必须是调用者**自身组织或其组织树下的子孙组织**，否则报**业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3）。配置页右上新增租户下拉（数据源复用存量 `GET /api/web/organization/findByTree`，**根节点无子组织即隐藏** → Portfolio Group Manager 看不到）。**本版推翻 v4.0 起反复申明的「C 模块组织一律取自登录态、不接受入参」**（§4.3 / §5.1.1 / §5.1.2 / §6.4）。计分口径、题库版本模型、维度配置模型、表结构一律不变。逐条见 §0.13 |
| v4.8 | 2026-09-07 | **需求方 2026-09-07 追加裁决：维度删除即物理删除** | **`erl_dimension_config_item.status` 整列删除，「删除维度 = Retire 软删」口径作废** —— 配置页删掉一行、Save 后该维度就**不在新生成的配置版本里**；**历史仍不漂移**，靠的是 `erl_company_period_config` 的**期次-版本绑定**（R2 的核心机制**不变**），与状态位无关。`ErlDimensionConfigStatusEnum` **保留但降级为纯派生的展示态**（某 code 在当前生效版本里还在 ⇒ `ACTIVE`，不在了 ⇒ `RETIRED`，历史期次据此标灰），卡片（A1 / A2）与评分详情响应里的 `status` 字段照常下发、形态不变。**权重合计口径**由「仅 `ACTIVE` 行合计」改为**版本内全部维度合计恰为 100.00**；接口 23 / 24 的维度项**不再有 `status`**。另：**配置页 C6 布局改版**（新增栏上移到面板头下一行、列表由表格改为卡片行、行内编辑、`code` 列撤下），新增维度的 `code` ~~取填写的 `Abbreviation`（大写化）~~ → **2026-09-08 推翻：改为 `{abbr 前 3 位}{4 位随机}`，见 §5.1.3**；原文为 `Abbreviation`（大写化）且**此后永不改变**，`abbr` 可随时改名。**§13-Q24 关闭**。逐条见 §0.14 |
| v4.9 | **2026-09-06**（裁决日；**登记日 2026-09-07**，v4.5 ~ v4.8 编制时漏登记，此版补登，理由见 §0.15） | **需求方 2026-09-06 裁决：题目判定标准不进需求设计** | **题目判定标准 `criteria` 整体删除 + A5 弹窗整块删除**：① **`erl_question_config.criteria` 整列删除** —— 配置页 C2 / C3 **不再采集**，接口 10 / 12 无该入参、接口 2 / 8 / 9 / 22 / 26 无该出参，题库版本 diff 比对项亦不含它；② **A5「How It's Scored?」弹窗整块删除**（唯一实质内容就是该字段），`ScoringCriteriaModal` 组件与三处题目行的入口一并移除；③ **Goldie 输入去掉 `criteria`**，判断依据收敛为**题干 + 逐题 Yes/No + 双端备注 + level 口径**，prompt 升至 `# version: 1.1` 并加「不得编造判定标准原文」的反向约束；④ **§13-Q25 关闭**（取值＝从 Goldie 输入中移除）、**回写项 M11 关闭**（PRD §3.8 无需补该字段）。**计分口径、题库版本化、权限口径、附件与备注链路一律不变。** 逐条见 §0.15 |
| v4.10 | **2026-09-07** | **需求方 2026-09-07 裁决：C7 维度按题库版本发布当时的集合显示** | **题库版本发布时冻结维度集合**：① `erl_question_config_version` 新增列 **`dimension_config_version_id`**（varchar(36)，可空），**接口 21 Publish 在同一事务内**写入当时生效的维度配置版本 id，草稿行不写；② **接口 26 出参新增 `dimensions[{ code, name, abbr, sortOrder, weight }]`**（该版本绑定配置版本的 items，按 `sortOrder` 升序），C7 页体据此渲染维度卡 —— **推翻 v4.4-D1「前端按接口 23 的当前生效配置自行归组」**；绑定为空（草稿行、及本列上线前的存量已发布行）时回退当前生效配置；③ 两条版本线（§5.1.2 / §7.11）由「互不联动」订正为**写侧单向记录**，读侧仍不联动；④ 后续维度增删改名**不再影响**已发布版本的历史展示。**计分口径、权限口径、期次-版本绑定（§7.11）、维度配置 Save 流程、接口 23 / 24 契约一律不变。** 逐条见 §0.16 |
| v4.11 | **2026-09-07** | **需求方 2026-09-07 追加要求：C7 不显示带 `Retired` 灰标的维度** | **C7 页体只显示「发布当时有、且今天仍在维度配置里」的维度**：① 今天已不在当前生效配置（接口 23）里的维度**整卡不显示**，**连带其题目也不出现在本页**；② 本页的 `Retired` 灰标随之**整体取消**（`QuestionVersionSection.retired`、卡头标注与 `.retiredTag` 样式一并删除；`TEXT.retired` 仍被 A4 `DimensionQuestionsCard` 使用，保留）；③ 「题目 code 不在发布当时集合内」的**兜底卡取消**（那种卡必然是已删维度）—— v4.10-H3 的「题目永不消失」在本页作废；④ 全部维度都被滤掉时页体走空态 `None of this version's dimensions are in the current configuration.`，不留白页。**仅 C7 这一页的展示规则**：接口 23 / 26 契约、`dimension_config_version_id` 绑定与回退、历史期次（A1 / A2 / A4 / 雷达图）「已删维度照常显示 + `Retired` 标」的口径（§9 / §13-N4）一律不变。 逐条见 §0.17。⚠️ **本行 ① ~ ④ 已于 2026-09-09 整体作废**（v4.17，§0.22-Y2 / -Y3）：① 与 ③ 因 K1 待裁决**从未实现**（§8.4-C7 写着「未裁决前不得实现本条」），② 的灰标随之被回退、一直显示在页面上，④ 的空态从未可达；本版给出的最终取值是「**不过滤、也不标注**」—— 卡与题照常全展示，`Retired` 灰标在 C7 单独撤下。 |
| v4.12 | **2026-09-07** | **2026-09-07 ERL 代码审核的两条 P0 + 实现回写**（报告见 `CIOaas-api/.claude/doc/features/ERL业务域代码审核报告-20260907.md`） | **并发正确性定档 + 两处「文档与实现相反」的收敛**，全部为实现侧回正、无新需求：① **`stale` 不再无条件清零** —— 差距分析落库前重算「提交批次指纹」，只有输入没变过才清，变了就写入新内容但保留 `stale = true`；抢锁失败不再静默丢弃，持锁者跑完（锁已释放后）重读 `stale` 决定是否补跑，上限 2 轮；锁 TTL 由 5 分钟提到 **600 秒**（原值小于单轮最坏耗时，锁会中途过期导致并发写同一份分析）（§7.5 时序图 / S7 / S8）；② **`erl_gap_analysis` 主行的三个写入方（重生成 / 置脏 / Share）一律加行锁**，刻意不用乐观锁（置脏跑在用户提交事务里，乐观锁失败会让整次提交回滚）；③ **`erl_assessment` 与 `erl_question_config_version` 各加 `version` 列**（`@Version` 乐观锁）+ 写路径加悲观锁，兜住「已 SUBMITTED 一律只读」与「已发布版本一字不改」这两条不变量（§5.1.1 / §5.2 / §7.7 / §12）；④ **「0 题维度可提交」四处写反的表述订正为「不可提交」** —— 视图侧 `canSubmit` 本来就要求该维有题，提交侧漏了这一条，属同一契约两个口径（§6.3 校验 3 / §7.2 / §9 / §11-11b）；⑤ **§4.3 补一条强制校验**：写接口的 `dimension` 必须属于该期次绑定的配置版本（此前 `ZZZ` 这类字符串能落库成 SUBMITTED）；⑥ §9 失败降级表补「乐观锁冲突」一行。**计分口径、权限口径、接口契约、UI 一律不变。** 逐条见 §0.18 |
| v4.13 | **2026-09-07** | **2026-09-07 题库两张表与对应 Java 类改名**（与 interfaces 层既有的 `ErlQuestionConfigResponse` 命名对齐） | **纯改名，零语义变更**：① 表 `erl_question` → **`erl_question_config`**、`erl_question_version` → **`erl_question_config_version`**，两表的索引与唯一约束名一并对齐（`uk_erl_question_config_key` / `idx_erl_question_config_version_dim` / `uk_erl_question_config_version_draft` / `uk_erl_question_config_version_no` / `idx_erl_question_config_version_status` / `uk_erl_question_config_version_latest`）；② 对应 Java 类全套 `ErlQuestion*` → **`ErlQuestionConfig*`**（实体 / 仓储 / 服务 / DTO / 枚举 / 控制器 / 转换器 / Request / Response），与 interfaces 层**早已叫** `ErlQuestionConfigResponse` 的命名对齐；③ **两个例外不改名**：`ErlQuestionConfigResponse`（已含 `Config`）与 `ErlQuestionDetailResponse`（评估回放的只读逐题结构，A3 / A4 / B3 共用，**不属题库配置**；其 DTO 对应物 `ErlQuestionDetailDTO` 同理保留）；④ 迁移脚本 **sprint118 的 V1 / V3 / V4 就地更新**表名，**不新增改名脚本**。**HTTP 路径（`/erl/question` 系列）、列名（`question_key` / `question_text` / `question_version_id` / `version_no` / `dimension_config_version_id`）、其它 `erl_*` 表名、计分与权限口径、接口契约、UI 一律不变。** 逐条见 §0.19 |
| v4.14 | **2026-09-07** | **需求方 2026-09-07 决定：ERL Configuration 的菜单入口改由管理后台配置** | **菜单入口的落库途径换掉，前置条件与操作要求一律不变**：① 原先往 `menu` 表插 `path = '/exitReadiness/configuration'` 根节点行、并给超管角色授权的迁移脚本 **`V2__erl_menu.sql` 已删除**，这两件事改为**在管理后台的菜单配置界面**完成；② §8.1.1 的三个前置条件**一个不少**——`menu` 表必须有该 `path` 的行、**`pid` 必须是 `'0'`（根节点）**、该菜单经 `r_role_menu` 授权给用户角色、配好后必须**清两处缓存**（服务端 `menu` cache + 浏览器 `localStorage.roles`）再重新登录，只是「落地位置」由 SQL 脚本换成后台界面；③ sprint118 的**可执行脚本由四份减为三份**（`V1` / `V3` / `V4`，文件名保留旧称不变）；④ **路由守卫按端类型（`roleType`）判、不按菜单权限判的口径不变**，其论据里的反例由「脚本没跑」换成「菜单未在管理后台配置」。**表结构、计分口径、权限口径、接口契约、UI 一律不变。** 逐条见 §0.20 |
| v4.15 | **2026-09-08** | **需求方 2026-09-08 对 §5 数据模型的连续四轮调整 + 三条口径裁决** | **数据模型重构，并向接口 / 流程 / UI / 建表 / 用例全面对齐**：① **表数 12 → 11**：删 `erl_dimension_config_version`（维度配置去版本化）与 `erl_company_period_config`（期次-配置绑定取消），增 `erl_question_config_dimension_version`（发布时逐维快照）；② **三张表改名**：`erl_dimension_config_item` → `erl_dimension_config`、`erl_benchmark_record` → `erl_reference_score`、`erl_benchmark_dimension` → `erl_reference_score_item`；③ **题库版本线改为每维一条**：`erl_question_config.version_id` → `version_no`（按 `dimension_code` 自增），定位键 `(dimension_code, version_no)`；组织级发布批次仍在 `erl_question_config_version`，两者由 §5.1.5 快照表对应；**草稿仍是组织级一份**（保住 §0.18-L4 的并发论证）；④ **`erl_question_config_version` 精简为八列**（删 `based_on_version_id` / `change_summary` / `dimension_config_version_id`）—— 接口 25 不再返回 `changeSummary`，接口 26 的 `dimensions[]` 改取 §5.1.5 快照；⑤ **`erl_assessment` 删 `submission_seq` / `is_latest`**（连带删 `uk_erl_assessment_seq` / `uk_erl_assessment_latest`，**部分唯一索引五个 → 三个**），「最新一次提交」改判 **`submitted_at DESC, id DESC` 首条**；同时新增 `dimension_name` / `dimension_abbr` 提交时快照；⑥ **维度删除改软删**：`erl_dimension_config.status` 重新落库，取值 `Active` / `Inactive`，权重合计 100% 只算 `Active` 行，`Retired` 灰标由列值直接判定（v4.8 的派生态作废）；⑦ **列名统一**：`dimension` → `dimension_code`（题库 / 评估 / 基准）、`question_version_id` → `erl_question_config_version_id`、`assessment_id` → `erl_assessment_id`、`question_id` → `erl_question_config_id`、`answer_id` → `erl_assessment_answer_id`、`record_id` → `erl_reference_score_id`；⑧ **三条口径裁决**：权重**不做任何快照**（接受改权重 / 增删维度回溯改变历史期次的综合分与 Stage）—— **R2「历史永不漂移」正式失效、§7.10-W1 反转回「接受漂移」、§13-Q21 重新打开**；`file_name` / `file_size` 暂不删除（**⚠️ 2026-09-09 推翻：两列已删除，改按 `file_id` 查 `files`，见 §5.5**）；**⑨ `erl_dimension_config.dimension_code` 改为服务端生成的 `{abbr 前 3 位}{4 位随机}`**（如 `OPS4K7M`，≤ 7 字符），与 `dimension_abbr` 解耦、创建后永不变，推翻 v4.8-P8；同时 **`dimension_abbr` 恢复组织内 `Active` 唯一**、**接口 24 改为显式判别（`isNew` / `deactivatedCodes` / `savedAt` 乐观锁 / `clientRef` 幂等键）**、**`dimension_code` 不再送进 LLM**（改送 `index`）；**⑩ `erl_question_config` 补 `organization_id`**（键位变 `(organization_id, dimension_code, version_no, question_key)`），收口跨租户串号，并使种子数据恢复按组织插、V5 免掉重编号步骤。**本版受影响面：§2 / §3 / §4 / §5 全节 / §6 约 60 处 / §7.1、§7.2、§7.5、§7.7、7.8、7.9、7.10、§7.11（整节重写）/ §8 / §9 / §10.1 / §11（十一条用例重写）/ §12 / §13 / 附录 A~C。** ⚠️ **开发前仍有待答项**：§13-Q21（权重与历史漂移）、~~§5.1.5 是否补 `weight` 列~~（**2026-09-09 订正**：§5.1.5 2026-09-08 已定档采用「另造窄 Response」，2026-09-09 实现落地 —— 接口 26 **压根不下发 `weight`**，从来不是待答项）、~~§0.17-K1（软删后 C7 的显示规则）~~（**2026-09-09 已关闭，取值 = 整条取消，v4.17 / §0.22-Y3**）、`erl_question_config` 是否补 `organization_id`。 |
| v4.16 | **2026-09-09** | **需求方 2026-09-09 裁决：维度的删除按「是否进入过已发布题库版本」分成两个动作**（布局取自当日 mockup） | **配置页的单一破坏性动作一分为二，`status` 之外新增一个与它正交的 `deleted` 位**：① **从未进入过任何已发布题库版本的维度** —— 行尾仍是**垃圾桶 = 删除**，落库为 `erl_dimension_config.deleted = true` 的**真软删**：行与 `weight` / `dimension_name` / `dimension_abbr` 全部原样保留（历史仍能按 `dimension_code` 反查），但**所有读侧一律排除**、页面两处都不再出现、**没有恢复入口**；**删除只写 `deleted` 这一列、`status` 原样保留**（需求方当日追加明确，§0.21-X13）；② **进入过已发布版本的维度** —— **删除被禁止**，图标改为**电源按钮**（`PoweroffOutlined`）= 停用（`status = 'Inactive'`，**行为与 v4.15 的软删一字不差，只是换了图标并挪了恢复入口**）；③ **`status` 仍只有 `Active` / `Inactive` 两值，`deleted` 与它正交**（`Active + false` = 主列表 / `Inactive + false` = `Deactivated Dimensions` 区块 / `deleted = true` = 完全不显示）；④ **`Show deactivated` 开关整个撤下**（连同它的脏态确认弹框文案 `dimensionConfigToggleDeactivated`）—— 页面此后**恒**带 `includeDeactivated=true` 取数，停用行改由**面板底部常显的 `Deactivated Dimensions` 区块**承载（含空态 + `Activate`）；⑤ **接口 23 出参每项新增 `deletable`**（⟺ 该 code 从未进入任何 `PUBLISHED` 版本的维度快照，⚠️ 判据必须过滤 `status = 'PUBLISHED'` —— 草稿版本上也有快照行），`deleted = true` 的行**任何情况下都不下发**；**接口 24 入参新增可缺省的 `deletedCodes[]`** + **三条新校验**（未命中 / 已发布不许删 / 三个桶互斥），集合完整性校验把 `deletedCodes` 也算作已交代；⑥ **`uk_erl_dimension_config_abbr` 的谓词变为 `WHERE status = 'Active' AND deleted = false`**（漏掉后半边 ⇒ 删掉的行永久占着缩写、且页面上看不见它）；⑦ **迁移 `V11__erl_dimension_config_add_deleted.sql`**（加列 + 按新谓词重建索引，**additive、无 `V10` 那种发版顺序陷阱**）；⑧ **§13-Q24 改判** —— 由「已关闭：无条件允许删除、不做前置拦截」改为「**拦截存在**，但判据是「是否进入过已发布题库版本」，保护对象不是那一行（软删下行不消失），而是**已发布题库版本的语义**」。**本版受影响面：§1.2 / §4.3 / §5.1.3 / §5.1.5 / §6.4（接口 23 / 24）/ §7.10-N4 / §7.11-②④⑤ / §8.4-C6 / §9 / §10.1 / §11-77、§11-86 / §12 / §13-Q24。** ⚠️ **v4.15 的待答项一条未减**（§13-Q21 / §5.1.5 的 `weight` / §0.17-K1）（**2026-09-09 订正**：`§5.1.5 的 weight` 其实在 §5.1.5 本节已于 2026-09-08 定档采用出路 ②、并非待答项，2026-09-09 实现按出路 ② 落地 —— 接口 26 **压根不下发 `weight`**），且 **§0.17-K1 不会因本版自愈** —— 理由见 §0.21-X9。（**2026-09-09 当日更晚**：**K1 已由 v4.17 关闭** —— 需求方在两个候选取值里选了「整条取消」，见 §0.22-Y3；本行的分析仍然正确，只是不再是最终结论。） |
| v4.17 | **2026-09-09** | **需求方 2026-09-09 对 C7 题库版本历史页的两条追加裁决**（截图圈定） | **只改 C7 这一页「看什么」，不改任何契约、服务端零改动**：① **版本下拉只列已发布（`PUBLISHED`）版本** —— 草稿一律不进下拉，`v{n} — Draft (edited {时间})` / `v{n} — Draft (not published yet)` 这一支标签**删除**；**过滤做在前端取数 hook `useQuestionVersions` 里，接口 25 的契约一字不改**（仍返回草稿 + 已发布 —— 「有没有草稿」是 `Publish` 按钮能不能点的依据，服务端把草稿滤掉那个判断就没了数据来源，而 C7 是它当前唯一消费方，过滤放页面侧只多一个 `filter`）；默认选中仍是**最新已发布版本**。⚠️ **本版的行为变化**：一份都没发布过（只有草稿）的组织在 C7 上是**空态** `No published question set versions yet.`，不再退回「选中草稿」；② **C7 维度卡头不再显示 `Retired` 灰标** —— 维度卡与其题目**照常整卡展示**（「完整回看发布当时那一版」的口径不变，2026-09-07 那次「整卡连题滤掉」的回退依然有效）。连带：C7 **不再取接口 23**（那次取数**只**为算这个灰标），`QuestionVersionSection.retired` 字段、兜底卡上的 `retired: true`、`QuestionVersionHistoryPage.less` 的 `.retiredTag` 一并删除 ⇒ **C7 此后完全不依赖当前维度配置，只读接口 25 / 26 的历史快照**（少一次请求，页面 loading / error 也不再受接口 23 影响）；⚠️ **`TEXT.retired` 这个文案本身还在用**（`ErlCard` 的维度行与 A4 `DimensionQuestionsCard` 仍按 `status === 'RETIRED'` 打标）—— **不得**读成「全站不再有 `Retired` 标注」；③ **§0.17-K1 由此关闭** —— 它的两个候选取值里需求方选了**整条取消**：C7 既不隐藏「今天已不在配置里」的维度、也不再标注它，**C7 与「今天的维度配置」彻底解耦**；§0.21-X9 写的「本版不使 K1 自愈、该待裁决项原样保留」其分析仍正确，但**结论已被本版取代**。**接口 25 / 26 的出入参、§5.1.5 快照表、计分与权限口径、数据模型、C6 的两个破坏性动作（§0.21）、以及历史期次（A1 / A2 / A4）「已停用维度照常显示 + `Retired` 灰标」的口径一律不变。** 逐条见 §0.22 |
| v4.18 | **2026-09-09** | **2026-09-09 实现落地后的全文一致性复核**（逐条对着仓库现文核实：`ErlDimensionConfigServiceImpl` / `GlobalExceptionHandler` / `ErlQuestionConfigDimensionVersionResponse` / `ErlQuestionConfigVersionServiceImpl` / web `constants.ts` / `DimensionConfigForm.tsx` / `useDimensionConfigForm.ts` / `ConfigurationPage.tsx` / `sprint118/{README.md,V10,V11}`） | ⚠️ **本版是纯文档订正，没有任何设计变更** —— **计分口径 / 权限与 ACL 口径 / 数据模型（11 张表、列与索引）/ 全部接口的出入参契约一律不变**，改的只是「文档写的」与「仓库里实际是什么」不一致的地方。七条：<br>① **业务错误的 HTTP 形态**：全文写作 ~~`400`~~ 的地方，只要错误由 ERL service 层 `throw new BadRequestException(...)` 产生（`assertNotStale`、入参形态校验、集合完整性校验、空入参、端类型 / 组织越权……），实际线上形态一律是 **HTTP 200 + `success: false`** —— `GlobalExceptionHandler` 对该异常返回 `HttpStatus.OK` + `Result.fail(...)`。已全文统一（§4.3 开头新增判据与例外清单：真 400 只有 `UnrecognizedPropertyException`，`@Valid` / `BindException` 是 **422**，兜底是 **500**；§11 开头另加一条给写断言的人）。原文档里唯一正确的那句（§6.4-3「⑧⑨⑩ 一律是业务错误：HTTP 200 + `success: false`」）现在是全文口径。<br>② **接口 26 出参 `dimensions[]` 的字段清单**：~~`{ dimensionCode, dimensionName, dimensionAbbr, sortOrder, weight }`，`weight` 取实时值会漂移~~ → **实为 `{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }`** —— **没有 `weight`**（§5.1.5 定档的「另造窄 Response」出路 ② 已落地，`ErlQuestionConfigDimensionVersionResponse` / `...DTO` 从不 set weight，前端 `response.ts` 亦注明「没有 `weight`、没有 `status`」），**多一个 `questionVersionNo`**（该维在这一版下用的题目集版本号，无题为 `0`）。连带订正 §0.16-H2、§5.1.5、§13 收尾段与 v4.15 / v4.16 两行版本记录里「§5.1.5 是否补 `weight` 列」这条**待答项的前提** —— 现状不是「取实时值会漂移」而是**压根不下发**，⇒ **开发前仍开着的待答项由两项减为一项（只剩 §13-Q21）**。<br>③ **恢复按钮的文案是 `Activate`，不是 `Restore`**（2026-09-09 mockup 定档，`TEXT.activate`）：仓库里**没有任何** `Restore` 文案常量，全文面向用户的按钮文案已一律订正（讲「恢复」这个动作时仍用中文；前端 handler 名 `onRestore` / 标志位 `isRestored` 保留旧词）。<br>④ **主列表行尾图标是三态，不是二选一**：~~`deletable ? 垃圾桶 : 电源按钮`~~ → **`row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`** —— 本次会话里刚从停用区恢复回来的行**即便 `deletable = true` 也只给电源按钮**，语义是「**撤销恢复**」，另有 `dimensionRestoredTooltip` / `undoRestoreConfirm` / `undoRestoreOk` 三条独立文案与独立 aria-label `Undo restore`。这条**防误删设计**此前只活在代码注释里，本版写进 §0.21 状态矩阵 + 新增 **X14** 行 + §7.11-④ 表 + §8.4-C6-③。<br>⑤ **`V11` / `V10` 迁移脚本的形态与约束**：`V11` **不是**「`ADD COLUMN ... NOT NULL DEFAULT false` 一步到位 + 重建索引」（那正是脚本文件头点名「不能这么写」的形态 —— 列已存在时 `IF NOT EXISTS` 会把 `DEFAULT` / `NOT NULL` 一起跳过，`V4` 的 `version` 列踩过），实为**四步同处一个 `DO` 块** + 表不存在即 `RAISE NOTICE` 返回的守卫；`V10` 第 ③ 步**已改为按 `information_schema` 探 `deleted` 列自适应谓词**，⇒ 两份脚本**谁先谁后都不影响终态**、`V11` 不必跑第二遍。§0.21-X11 另补两条此前漏写的实质约束：**(a)** `V11` 之所以**必须**排在「发版前」，是因为 `ddl-auto` 在**有数据**的表上加不出这个 `NOT NULL` 列（不是「可提前任意时间跑」）；**(b)** `V11` 跑完到 `V10` 跑完之间有一段**无约束窗口**（索引谓词已是 `'Active'`、数据还是 `'Activate'` ⇒ 命中零行，「同组织启用维度缩写唯一」在此期间不受约束）。<br>⑥ **§10.3 前端改动清单补 C6 条目**：原先只为 C7 单列了一段，而 C6 才是本轮改动量最大的一块 —— 补齐 `DimensionConfigForm.tsx`（三态 + 常驻停用区 + 提示段）、`useDimensionConfigForm.ts`（`isDeleted` / `canDelete` / `isRestored` / `rowsIssue` / 三桶归属）、`constants.ts`（新增约 14 条、删 `removeDimensionConfirm`）、`ConfigurationPage.tsx`（恒带 `includeDeactivated=true` + 两个保存分支弹框）、`ConfigurationPage.less`、以及 `configuration/__tests__/` 下的一新一扩两份测试。<br>⑦ **删除二次确认与停用 tooltip 的例文换成 `constants.ts` 里的实际取值**（逐字）：~~`Delete “{name} ({abbr})”? … cannot be restored.`~~ → `Delete this dimension? It has never been published in a question set, so it will be removed from the configuration. This cannot be undone from this page.`（**不带 name / abbr 插值**）；停用 tooltip ~~`This dimension was published in a question set — it can only be deactivated.`~~ → `Published in a question set — deactivate instead of deleting.`；规则提示段与停用区尾注同样改为逐字实文。<br>⚠️ **本版未处理的一条**（需求方尚未裁决，原样挂着）：**§8.4-C6-⑤ / §11-86-③ 要求停用行展示「只读可复制 `code` + 权重 + 最后期次 + 提交条数」，而 2026-09-09 mockup 落地的停用行只有灰化 `Name (ABBR)` + `INACTIVE` 标 + `Activate` 三样** —— 代价是两行同名时 `Activate` 分不清是哪一行、恢复后要补多少权重也得自己算。 |
| v4.19 | **2026-09-09** | **需求方 2026-09-09 裁决：F2 ERL Tab 照 Lovable 原型 `/portfolio` 的 ERL Tab 定稿 + 追加「ERL tab 页面显示数据为当前季度的数据」** | **只改 F2 这一个 Tab 的前端表现，服务端零改动**，七条：① **期次** —— F2 前端**固定传 `period = 当前自然季度`**，整张表同一期次，**F2 由此成为 §0.10-R3「缺省 = closed month 所在季度、明确不猜当前自然季度」的显式例外**；R3 的服务端缺省**原样保留**，对接口 1 / 17 / 22 与任何不传 `period` 的调用方继续有效。② **排序与筛选全部撤下** —— 表格上方的 Stage 下拉与 `Min score` / `Max score`、**以及全部列头的排序器**均按原型删除（原型两者都没有），F2 成为一张**纯展示表**；接口 20 的 `sortBy` / `sortOrder` / `stage` / `minScore` / `maxScore` 入参与服务端实现**保留不删**，只是 F2 恒不下发，**§0.10-D15 的「排序筛选功能保留」由此整条失效**（仅指界面，服务端能力仍在）。③ **`Stage` 列只渲染一枚 Era 徽章**，stage 整数不再显示。④ **`ERL Score` 补上分母**渲染 `7.2/9`（一位小数不变 —— 原型上的整数 `7/9` 是造的假数据，需求方当日确认按一位小数）。⑤ **着色只给 `ERL Score` 与 `Stage`**，维度列改中性色（**回到 §8.4 原文**，此前的实现多给维度列上了 Era 色）。⑥ **期次标签整个撤下** —— 先由逐行挂在公司名后面改为表格上方标一次，同日需求方圈图追加裁决**连这一行也删掉**，页面不出现任何期次文字（§0.23-P6）。⑦ `View →` 文案改 **`View ›`**。逐条见 §0.23 |
| v4.20 | **2026-09-09** | **需求方 2026-09-09 裁决：A4 Score Details 照 Lovable 原型 `/readiness/overall` 重排版，并明确「严格照原型」**（依据为该已发布站当日的 SSR 实测 + 截图，不是 2026-08-28 那次 chunk 反解） | **A4 全维 Score Details 页整页重排版 —— 纯前端，接口契约零变更**：① 面包屑三级改**两级**（不再夹公司名）；② 页头**只剩 H1 `Score Details`**，加权 `Overall Score` 与 Era（Stage）徽章整块删除 ⇒ **§0.8-12 的裁决被推翻**；③ 五张维度折叠卡改**维度横向 Tab**（一次只渲染一维，标签取 `abbr`）；④ 页尾基准折叠卡改**末位 Tab**，标题改原型原文 `External Benchmarks & Top GSV Quartile`；⑤ 组合端**双端同屏并列改回 `GSV` / `Founder` 药丸切换**（`GSV` 默认选中）⇒ **§0.10-D5 的「同屏并列」被推翻**，但**取数不变**（管理端仍不传 `portal` 一次取双端，切药丸只换本地切片、不重发接口 22）；⑥ 卡头计数改为只报总题数；⑦ 按 level 分组的组头移除；⑧ 徽章三态、附件补体积与下载、`+ Add New` 仅 GSV 侧、`View history` 小写 h。**接口 22 契约零变更**（出入参一个字段不增不减），数据模型 / 计分 / 权限 / ACL 一律不动。⚠️ ~~服务端零改动~~ **不准确**：同批有**一处非契约的服务端缺陷修复** —— `ErlDimensionConverter#fillAddNewUrl`（`dimensions[].addNewUrl` 被 MapStruct 判成 adder 而恒发 `null`，⑧ 的 `+ Add New` 依赖它），属**出参修复、不是契约变更**。逐条见 §0.24 |
| v4.21 | **2026-09-10** | **实现落地后的一致性回写：A4 卡头两条下发 URL 的取值口径**（2026-09-10 B3 原型改版排查出「面包屑回 A4 恒落到缺省期次」，连带补记 2026-09-10 `addNewUrl` 补 `portal=gsv` 那次漏回写） | ⚠️ **本版无设计变更，也无契约变更** —— **接口 22 的出入参一个字段不增不减**（`addNewUrl` / `historyUrl` 仍由后端下发、前端不拼路径），数据模型 / 计分 / 权限与 ACL / 期次口径一律不动；改的只是这两条 URL 的**取值**，以及文档写的与仓库现文不一致的地方。两条：① **`addNewUrl` 追加 `&portal=gsv`**（补记 2026-09-10 落地）—— 判据是「**这张卡装的是哪一卷**」而非调用端，公司端恒 Founder 卷、恒不带，⇒ 从 A4 的 `GSV` 药丸点 `+ Add New` 落地的是 B2 GSV 卷而非 Founder 卷；② **`historyUrl` 追加 `&period={period}`**（期次空白时不拼）—— **B3 自身不按期次过滤**（历史列表跨期次全量），该参数纯粹是 B3 面包屑「Score Details」回 A4 的**返回上下文**，不带则 A4 落到服务端缺省期次（closed month 所在季度）而非用户来时那一期；同批前端三个上游入口（A4 卡头 `historyUrl` 由后端补、A2 维度页 `View history`、B 填报页提交后跳转）与 **B3 → 详情页 → 回 B3** 这一跳一并透传 `period`。⚠️ 详情页那一跳**只补了 `period`、没有补 `dimension`**，返回落到的仍是全维混排的 B3。逐条见 §0.25 |
| v4.22 | **2026-09-10** | **需求方 2026-09-10 圈图：A4 末位基准 Tab 的 `AVERAGE` 去掉** | **只改 A4 末位基准 Tab 的表尾一行 —— 纯前端，服务端零改动，接口 22 契约零变更**：① 表尾那行加权 `Average`（屏显 `AVERAGE`）**整行撤下**；② **A4 是它唯一的用处**（D1 / 基准记录详情页 本就不传权重、从来不出这行），故 `BenchmarkDimensionTable` 的**可选入参 `weights` 与整个 `summary` 一并删除** —— 不留一个没有调用方的「传了才渲染」开关（YAGNI）；③ 接口 22 `header.weightsApplied` **出参保留**（契约零变更），只是 **A4 前端此后 `header` 四项一项都不消费**（`overallScore` / `stage` / `era` 已于 v4.20 停渲染）。**加权 Overall Score 的计分口径不变**（§7.1；⚠️ `erlScoring.weightedOverallScore()` **本就不是 ERL Card / F2 的取数来源** —— 那两处一律直接渲染后端下发的 `overallScore`，该函数自本版起前端零调用方、只剩单测在用，见 §0.26-Z1），数据模型 / 权限与 ACL / D1 / 基准记录详情页 两处基准表 —— 一律不变。逐条见 §0.26 |
| v4.23 | **2026-09-10** | **需求方 2026-09-10 决定：基准允许同期次重复录入** | **D 模块取消「一期次至多一条」的两道限制** —— ① 服务端 `ErlBenchmarkServiceImpl.assertPeriodNotTaken`（原报 `A benchmark record for this period already exists.`）**删除**；② 数据库唯一索引 `uk_erl_reference_score (company_id, period)` **删除**，改建同键位的**普通**索引 `idx_erl_reference_score_company_period`（新增迁移 `sprint118/V13__erl_reference_score_drop_period_unique.sql`，`V1__erl_init.sql` 就地改为直接建普通索引）。⚠️ **代价**：不再有数据库级「同期次至多一条」保证，读侧「最新一条 / 适用记录」一律改判 **`period DESC, created_at DESC, id DESC` 的第一条**（`id` 是同一微秒的平局兜底，与 §5.2 评估 SOT 的 `submitted_at DESC, id DESC` 同源）；D1 记录表按同一排序键展示（同期次多条并列，最近录入的排前面）。**页面结构、录入表单、维度动态化、值域与计分口径一律不变。** 逐条见 §0.27 |
| v4.24 | **2026-09-10** | **需求方 2026-09-10 决定：后端补真实录入时刻** | **接口 15 出参 `recordedAt` 换口径 —— 由「`period` 推导的期末日」改为「审计列 `created_at` 的真实录入时刻」**：Java 类型 `LocalDate` → **`Instant`**（下发 ISO-8601 串），`ErlBenchmarkDTO.recordedAt` 与 `ErlBenchmarkRecordResponse.recordedAt` 同改；私有方法 `ErlBenchmarkServiceImpl#periodEndDate` 与它专用的常量 `MONTHS_PER_QUARTER` **一并删除**（`PERIOD_PATTERN` **保留**，只用于写入前的期次格式复核）；`created_at` 为空的历史行下发 `null`、前端显示 dash。前端**三个展示位**（D1 `Record History` 的 `SUBMISSION TIME` 列、D1 卡一与 D3 详情卡的 `BenchmarkSubmissionMeta`）一律改走 `formatErlIsoDate()`（**只到日、`YYYY-MM-DD`**，需求方 2026-09-10 定的写法），不再直出后端原串。**列头文案 `SUBMISSION TIME` 一字不改** —— 此前它在说谎（值与录入时间无关、同期次两条完全相同、与 `PERIOD` 列 100% 冗余），本版起名副其实。⚠️ **表结构零变更、无新迁移脚本**（`created_at` 是审计基类自带的列）。逐条见 §0.28 |
| v4.25 | **2026-09-10** | **2026-09-10 缺陷：D1 面包屑「Score Details」回 A4 恒落到缺省期次** | **把期次一路透传为「面包屑返回上下文」，补上 A4 → D1 这一跳断掉的期次** —— 与 v4.21-Z2 修的「B3 面包屑回 A4 恒落缺省期次」是同一条链的另一段：D1 面包屑第二级早就写了「URL 上带了 `period` 就带回去」，但上游从来不给（A4 基准 Tab 的两个入口只拼 `?companyId=`、后端 `benchmarkUrl` 也只拼 `?companyId=`），于是回到 A4 时走 `ErlPeriodService.resolveDefaultPeriod`（closed month 所在季度，实测 `Q4 2025`）打开另一期。本版**五处补参 + 一条口径**：① A4 基准 Tab 的 `+ Add New`（→ D2）与 `View history`（→ D1）都拼 `&period=`，取的是**本页真正在看的那一期** `shownPeriod`（= `data?.period \|\| URL 参数`）而非 URL 原参；② D1 抽出 `periodQuery`，到 D2 的 `addUrl` 与到 D3 的 `recordUrl` 一并带上（回 A4 的 `scoreDetailsUrl` 照旧带）；③ D3 从路由取 `contextPeriod`，面包屑与 `Back` 回 D1 时带上（⚠️ 与本页**展示**的期次 = 记录自身 `record.period` 是两件事）；④ D2 保存成功回 D1 时带上 `contextPeriod`（`Back` / `Cancel` 走 `history.goBack()`，不受影响）；⑤ **后端** `ErlCardServiceImpl` 下发的 `benchmarkUrl` 由 `?companyId={id}` 改为 `?companyId={id}[&period={period}]`（新私有方法，两个 build 点都改）。**口径**：期次在 D 模块**只作面包屑返回上下文，各页取数一律不用它**（D1 / D3 都不按期次过滤）。⚠️ **契约零变更**（`benchmarkUrl` 改的是取值、不是字段）、**无数据库改动、无迁移脚本**。逐条见 §0.29 |
| v4.26 | **2026-09-10** | **需求方 2026-09-10 口径：Reset 之后要拿到最新的题库** | **Reset 清空答案后把草稿改绑到当前最新的已发布版本** —— 这不是新开一条口子，而是**把 §7.9-⑤ 早就写明的换题集正路接通**：那条正路是「Reset 丢弃旧草稿 → `Add New` 重新发起，新草稿创建时绑定当时最新的已发布版本」，但实现按 §6.3 / §9 选了**保留草稿行**，于是 `findOrCreateDraft` 永远命中那条旧行、走不到创建分支 ⇒ 这条路自上线起就是断的，Reset 完再 `Add New` 拿到的还是旧题集。本版在 `discardDraft` 清完答案之后补一次改绑（批次 id + 逐维快照 id **同一时刻一起写**）。⚠️ **与 §7.10-N3 否掉的「升级按钮」不是一回事**：那个是把旧答案跨版本迁移（v3.4 已删除的 rebase），而这里答案在上一步已经全删干净，**没有任何需要迁移的作答** —— 这是它相对 rebase 唯一但决定性的安全点。两个边界：① 该组织当下没有任何已发布版本 ⇒ **保持原绑定**（该列 NOT NULL）；② 已经绑的就是最新版 ⇒ 两列都不动。⚠️ **接口契约零变更**（前端 Reset 成功后本来就重拉接口 3，新题集自动生效，**前端零改动**）、**无数据库改动、无迁移脚本**。逐条见 §0.30 |
| v4.27 | **2026-09-14** | **需求方 2026-09-14 逐张截图圈定：C 配置页撤下一批提示物与二次确认** | **只改 `/exitReadiness/configuration` 的呈现与确认闸门，计分口径 / 数据模型 / 全部接口契约一律不变**，七条：<br>**① 草稿态的五处提示物全部撤下** —— 页头版本条（`Draft vN — unpublished changes · last edited by …`）、题库 Tab 顶部的草稿告警、操作条左侧的变更摘要计数（`n added · n modified · n removed · n reordered`）、维度 Tab 上的红点（`dirtyDimensions`）、题目行的变更徽章（`New` / `Edited` / `Moved`）。**服务端照常下发 `changeSummary` / `version`，只是页面不再渲染**（接口不动）。⚠️ **代价**：草稿态的可感知线索只剩两条 —— 有草稿时整页那圈浅色边框（白底上的 `#ffe7ba`，肉眼极淡）与「无草稿即禁用」的 `Publish`；§8.4-C5「变更徽章」与 §7.9 里凡以这些提示物为前提的论证均已不成立。<br>**② `Publish` 取消二次确认**：点了直接发。⚠️ 发布**不可撤销**、即刻对填报页与 Score Details 生效，页面上没有回滚入口，撤掉确认后**唯一的误触防线是按钮禁用态**；实现上因此把禁用条件由 `!hasDraft` 补成 `!hasDraft \|\| library.loading` —— 发布成功后 `reload()` 只是排期重拉，此前按钮会在重拉在途时凭陈旧的 `hasDraft` 回到可点，一次误点即对空草稿再发一版。<br>**③ 电源按钮（停用 / 撤销恢复）取消 `Popconfirm`**，点了直接生效；**垃圾桶（真删）的二次确认保留**。⚠️ **这条不对称是有意的**：停用可逆（落到底部停用区、可 `Activate`，且整组不点 `Save` 都不落库），真删在本页无恢复入口。§8.4-C6-③ 里「三态都要二次确认」作废，`deactivateDimensionConfirm` / `deactivateDimensionOk` / `undoRestoreConfirm` / `undoRestoreOk` 四条文案已删。<br>**④ 行内编辑态的「只读 `code` + 一键复制」撤下** —— `code` 此后**页面上哪里都不显示**（停用行上的 code 早在 2026-09-09 mockup 已撤）。§8.4-C6-⑤ / §11-86-③ 关于展示 code 的口径全面作废。⚠️ 代价：两行同名时行内编辑与 `Activate` 都分不清是哪一行，排查线上问题也只能去接口出参里看。<br>**⑤ C1 题目行 ACTIONS 列两枚图标的 Tooltip 撤下**，文案转为 `aria-label`，并补 `role="button"` + `tabIndex` + Enter/Space —— 原先是无 `href` 的 `<a>`，映射到 ARIA `generic` 角色，既不在 Tab 序列里、`aria-label` 也会被读屏丢弃（键盘够不着是撤 Tooltip 之前就有的存量问题）。<br>**⑥ 两段说明文字改为按需显示**：§8.4-C6-④ 的规则提示仅在**有启用维度**时出现，⑤ 区块尾注仅在**有停用行**时出现；`Deactivated Dimensions` 区块标题与空态 `No deactivated dimensions.` **仍常驻**（它是「我刚停用的维度去哪了」的唯一答案）。<br>**⑦ C1 行内 `Era band` 下拉一次列全 9 档、不出滚动条**（antd `listHeight` 缺省 256px 装不下 9 × 32px）。<br>**⑧ 两个删除确认按原型改版**：C3 删题与 C6 删维度现在是**同一款** `Modal.confirm` —— 无图标（`icon: null`）、`rgba(0,0,0,.8)` 深遮罩（原型 `bg-black/80`；antd 缺省 0.45）、18px 标题 + 14px 正文（维度名加粗）、右下角 `Cancel` / `#C0392B` 红 `Delete`，焦点落 `Cancel`（与 Radix AlertDialog 缺省一致；删除不可撤销，不该开局就焦点在删上）。⚠️ **C6 的垃圾桶由 `Popconfirm` 换成 `Modal.confirm`**，仓库里已无任何 `Popconfirm`；§8.4-C6-③ 「三态都要二次确认」及其逐字引用的 `deactivateDimensionConfirm` / `undoRestoreConfirm` / `dimensionPublishedTooltip` / `dimensionRestoredTooltip` / `deleteDimensionConfirm` 六条文案**均已作废且已从仓库删除**；其中「`deleteDimensionConfirm` **不带 name / abbr 插值**」一句与现实相反 —— 新正文插的正是 `{name}`。⚠️ 两份新正文都**不再说明「删除要 Publish 才生效、已提交评估仍按当时题面」**，而同批撤掉的首次拖拽提示里那句同义说明也没了 ⇒ 该语义在题库 Tab 上**一处不剩**（记在 `CIOaas-web/docs/待优化项.md`）。<br>**⑨ 两个 Tab 的删除图标换成原型的 lucide `trash-2`**（描边桶身 + 桶内两道竖线），替掉 antd 的 `DeleteOutlined`。<br>**⑩ 首次拖拽的一次性提示（`TEXT.reorderHint` + `Modal.info`）撤下**。<br>⚠️ **本版未处理**：草稿态是否要保留一条可感知线索、停用误点后是否给提示，两条均已向需求方提出、等裁决（见 `CIOaas-web/docs/待优化项.md`）。 |
| v4.28 | **2026-09-14** | **需求方 2026-09-14：选了 No 之后的题不必再答** | **首个 No 即终止本维 —— v4.0 定的「该 level 全部题都要作答、其中含 No 才终止」由本版作废（§7.2-① 状态机换判据）**：① `ErlLevelScorer` 在 level 内按 `sort_order` 扫到**第一道 No** 就置 `BLOCKED` + `terminated`，该 No **之后**的题（本级剩下的 + 其后所有 level）不再计入 `unansweredCount`，`canSubmit` 随之翻 `true`；它**之前**漏答的题仍计入、仍拦提交；② 填报页把首个 No **之后**的题（Yes/No、证据、附件）**全部禁用**，那道 No 自己及它之前的题**仍可改**（点错 No 要能改回来）；③ 前端把「答了 No」与「**把 No 改回 Yes**」都加进立即落盘的时机 —— `canSubmit` 只取接口出参：不发前者 Submit 永远亮不起来，不发后者它会停在答 No 那次的 `true` 上、终止已解除却仍可点；④ 草稿**正在存**的这段时间 Submit 一律禁用（此时 `canSubmit` 必然是上一次的出参）。**接口契约、权限口径、得分公式（= 出现 No 的 level − 1）、其余 UI 一律不变。**（⚠️ **v4.37 就地标注**：其中**得分公式已换底** —— 2026-09-15 裁决改为「最后一个整级通关的 level」，本行记录的是 v4.28 当时的口径；本版立身之本的「**首个 No 即终止本维**」这半条**不受影响、仍然有效**） |
| v4.29 | **2026-09-14** | **需求方 2026-09-14：B 填报页 `Reset` 的二次确认弹窗撤下** | **只改 `/exitReadiness/assessment` 的确认闸门 —— 纯前端，接口 28 契约与清空语义一字不变**：① `Reset` 点下去**直接**调接口 28 清空本次草稿的答案与附件（`unlockedLevel` 回 `1`），按钮自带 loading，失败仍只提示、页面不重绘成已清空；② 组件 `ResetDraftConfirm/` **删除**，域级 `.erlDialog` / `.confirmDimensionLabel` 样式与 `TEXT.resetConfirmTitle` / `resetConfirmBody` 两条文案常量随之删除（再无使用方）。**与 v4.27 撤下 C 配置页二次确认是同一类裁决。** |
| v4.30 | **2026-09-15** | **需求方 2026-09-15：B 填报页「不点按钮绝不写库」** | **填报页的落盘时机收敛到两个按钮 —— 计分口径 / 数据模型 / 接口 3 / 4 / 5 / 28 契约一律不变**：① **接口 4 只由 `Save as draft` 与 `Submit` 两个按钮触发** —— ~~Yes/No 或备注变更后去抖 1.5s 批量 POST~~（**2026-09-14 需求方裁决取消自动保存**，实现已改、本版才回写）与 ~~答 No / No 改回 Yes / 本级满答时存一次~~（**2026-09-15 裁决一并取消**）**全部作废**；② **新增接口 29** `POST /erl/assessment/progress`（§6.3）—— 与接口 4 **同形入参、只算不存零写入**，草稿期的解锁 / 终止 / `canSubmit` 改由它推进，「解锁判定只在服务端做」这条不变量**继续成立**（§7.2-①）；③ **明确不做**未保存离开拦截（`<Prompt>` / `beforeunload` / 二次确认 / `Unsaved changes` 常驻）与浏览器本地草稿缓存 —— 口径是**「没点保存就是没保存」**，不提醒、不挽留、不代偿，**答一半关标签即全部丢失是刻意接受的后果**。 |
| v4.31 | **2026-09-15** | **需求方 2026-09-15 裁决：C6 新增维度不做任何重名 / 重缩写校验** | **`erl_dimension_config` 组织内此后只保留 `dimension_code` 唯一（`uk_erl_dimension_config (organization_id, dimension_code)`），「同一组织内启用维度的缩写唯一」这条不变量整条取消 —— 计分口径 / 数据模型（除该索引外）/ 其余接口契约一律不变**，五条：① **部分唯一索引 `uk_erl_dimension_config_abbr` 整条删除**（迁移 `sprint118/V15__erl_dimension_config_drop_abbr_unique.sql`，`V1__erl_init.sql` 就地不再建它）⇒ ERL 的部分唯一索引由 ~~3 条~~ **减为 2 条**（`uk_erl_question_config_version_draft`，§5.1.1 + `uk_erl_assessment_draft`，§5.2）；同组织此后**可以有两个 `Active` 维度叫同一个缩写、甚至同名**，它们靠 `dimension_code` 区分；② **接口 24 的服务端校验删两条** —— ~~`dimensionAbbr` 在本次提交的数组内不重复、也不与本组织其它 `Active` 行重复~~（§6.4-2-③；⚠️ **`abbr` 的 1–8 字符长度校验保留**，列宽是 `varchar(8)`）与 ~~同名软拦截~~（§6.4-2-⑦：新增项 `(dimensionName, dimensionAbbr)` 命中某个 `Inactive` 行时返回需 `confirmCreateAnyway` 显式确认的业务错误），**顶层入参 `confirmCreateAnyway` 一并删除**；③ **§7.11-② 的两阶段保存 `parkAll` 随之删除** —— 它存在的唯一理由就是「先把该组织全部行落成 `Inactive` 并 flush、腾空 `uk_erl_dimension_config_abbr`」，好让「停用 `FRL` + 新建同名 `FRL`」「A / B 互换缩写」这类**终态合法**的中间态不撞索引；索引没了，这些场景天然合法，保存**变成单阶段直接写终态**。连带：删除分支不再需要「按 `previouslyActive` 把 `status` 退回删除前的值」（那一步是为了抵消 `parkAll` 的副作用），改为**只写 `deleted = true`、完全不碰 `status`**；`savedAt = max(updated_at)` 的口径变成「**只有真正发生变更的行会 bump**」（乐观锁仍然正确：有变更必 bump，无变更则令牌不变、下次仍校验得过）；④ **前端 C6 随之删三处** —— `+ Add` 栏的 abbr 查重（原先查重不通过就**静默不加**、用户看不到任何提示，**这正是本次需求的触发点**）、Save 前的 `DUPLICATE_ABBR` 否决项、同名软拦截的 `Create anyway` 二次确认弹窗与它的三条文案；⑤ 原先**为这条索引而写**的警告条目一律**按既有写法就地标注失效、不删历史条目**（§0.21-X2 / X8 / X11-④ / X13 的 `parkAll` 段、§5.1.3 的索引清单与「存量行可能已有重复缩写」那条迁移警告、§5.1.4 / §10.1 的统计口径）。**本版受影响面：§0.21-X2 / X8 / X11 / X13 / §5.1.3 / §5.1.4 / §6.4（接口 24）/ §7.11-② / §8.4-C6 / §10.1 / §11-86。** |
| v4.32 | **2026-09-15** | **需求方 2026-09-15 圈图：A1 Gap 区块 `Share to founder` 置灰时的 tooltip 撤下** | 纯前端、**零接口改动** —— ① `ErlGapBlock.tsx` 去掉包在按钮外的 `Tooltip` 与那层只为「禁用按钮不触发鼠标事件」而存在的 `<span>`，置灰按钮**不再有任何悬停提示**（原文案 `Waiting on both submissions: {abbrs}`）；② 该文案的唯一数据源 `pendingShareDimensions()` 与贯穿 `useErlCard` → `ErlCard` → `ErlGapBlock` 的 `pendingShareAbbrs` 属性链**一并删除**（除喂这句 tooltip 外无消费方）；③ **按钮 disabled 口径一字不变** —— 始终只取接口 1 的 `shareable`（服务端算，与接口 27 校验同源），本次删掉的那条从来就「只管文案、不决定 disabled」；④ 还差哪些维度改由区块底部常驻的 `Share unlocks once gap analysis is available for all {total} dimensions in {period}.` 独力承担。 |
| v4.33 | **2026-09-15** | **需求方 2026-09-15 裁决：closed month 取不到时按当前季度展示** | **缺省期次的「取不到就空态」那一半被推翻 —— 改为回退当前自然季度（UTC）**，纯服务端、**零接口契约改动、零数据库改动、前端零改动**，四条：① `ErlPeriodServiceImpl.resolveDefaultPeriod` 的**三条失败分支**（公司无任何 actuals / FI 侧抛异常 / closed month 格式不可解析）由 ~~`return null`~~ 改为**回退当前自然季度**，WARN 日志保留（文案由 `falling back to an empty state` 改为 `falling back to the current quarter`）；② **`companyId` 为空这一条仍返回 `null`** —— 连公司都没有时给一个季度只是凭空造上下文，且五个调用方（接口 1 / 2 / 17 / 20 / 22）都先经 `ErlAccessService#resolveCompanyId`（拿不到即抛），该分支只是防御，各 service 的 `isBlank(period)` 空态分支**因此全部保留**；③ **「不回退到更早期次」那半条完全不动** —— 本次放开的只是「期次本身定不下来」这一步，期次定下来之后该季两端无提交仍是空态、仍绝不取更早期次反填；④ **接口 20 / F2 各行期次可能不一致**（有 closed month 的按自己的季度，取不到的按当前季度），需求方 2026-09-15 **已确认接受** —— 该表本就不显示期次（§0.23-P6），肉眼分辨不出。⚠️ **代价**：季度初财务尚未结账时，新公司会展示一个**尚未闭合、且通常一份提交都没有**的当前季度 —— 卡片仍是空态，但期次 chip 会显示该季度，这正是 R3 当初「不展示财务上尚未闭合的季度」想避免的情形，本次由需求方明确取舍。**本版受影响面：§0.10-R3 / §7.1.2 / §9 / §11-32。** ⚠️ **顺带订正一处文档漂移**：§0.23-P1（v4.19）写的「F2 前端固定传 `period = 当前自然季度`」**早在 2026-09-15 就被需求方撤回、代码已改（`useErlPortfolio.ts` 不发 `period`）、但一直没回写本文档**，本版就地标注失效（§0.23-P1 / §5 功能覆盖表 / §6 接口 20 / §7.1.2 / §9 共 7 处）。接口 20 由此**回到服务端缺省**，也正因如此才吃得到本版的当前季度回退。 |
| v4.34 | **2026-09-15** | **需求方 2026-09-15 圈图：D2 两列分数框只允许输入整数** | **纯前端输入限制 —— 数据模型、接口契约、服务端校验一律未动**，三条：① `BenchmarkAddPage` 的 `renderScoreInput`（`External Benchmarks` / `Top GSV Quartile` 两列共用）由 ~~`step={0.1}`~~ 改 `step={1}` + `precision={0}`，并加 `parser` 把小数点连同其它非数字字符在输入过程中剔掉 —— **小数点根本落不进框里**；② 表单校验里 ~~「最多一位小数」（`Math.round(value * 10) === value * 10`，文案 `At most one decimal place`）~~ 换成 **`Number.isInteger`**（文案 `Whole numbers only`），兜住 parser 覆盖不到的路径（粘贴、键盘上下键、`setFieldsValue`）；③ 本条**只约束 D2 的录入**。⚠️ **三处刻意未动，需知悉**：**(a)** 列 `erl_reference_score_item.benchmarkit_score` / `top_quartile_score` 仍是 **`numeric(3,1)`**，列注释仍写着 `External static input, one decimal, 1-9`；**(b)** 服务端 `ErlBenchmarkCreateRequest.DimensionScore` 仍只有 `@DecimalMin("1.0")` / `@DecimalMax("9.0")`，**没有整数校验** ⇒ **绕过页面直调接口仍写得进 `1.1`**；**(c)** 存量已落库的一位小数记录**原样保留、原样展示**，D1 / A4 的 `BenchmarkDimensionTable` 不做取整。⇒ 「基准分是一位小数」这条口径**只在录入侧收紧为整数，存储与读取侧未变**，要彻底改成整数需另行裁决（补服务端校验 + 列类型迁移 + 存量数据处理）。**本版受影响面：§6.5（D2 校验）/ §7.8 / §8.4-D2 / §11-59。** |
| v4.35 | **2026-09-15** | **需求方 2026-09-15 裁决：综合分改等权、分母取维度个数** | **计分口径变更 —— 接口契约零变更、数据库零变更，只改一个算法与它的三个调用点**，六条：① **综合分由 ~~`Σ(维度分 × weight%) ÷ Σ(参与维度的 weight)`~~ 改为 `Σ(各维度分) ÷ 维度个数`** —— `ErlScoreCalculator.weightedAverage` 整个换成 `overallAverage(levelScores, dimensionCodes)`，**分母恒为该组织 `status = 'Active'` 的维度个数**，与「填了几维」无关；② **未填写的维度按 `0` 计入分子** ⇒ **v4.4 / §0.9-20 的「剔除该维、其余权重按比例归一化」整条作废**，这是本版唯一会让存量分数**普遍下降**的改动（配 5 维填 2 维、得分 6 与 4：旧 `5.2` → 新 `2.0`）；③ **Stage / Era 跟着新分数走**（两者本就由 `overallScore` 推导，`stageOf` / `eraOf` 一字未改）；④ **`erl_dimension_config.weight` 与接口 24 的「合计必须 = 100」校验全部保留不动**，但综合分**不再读它** —— `weightsOf` 此后唯一的消费者是 Goldie 差距分析的入参组装（§6.6），新增 `codesOf` 承担「给出维度集合」这件事；⑤ **零提交仍是 `null` 空态、不按 `0.0` 算**（需求方 2026-09-15 确认）—— 否则与「填了、level 1 就没过」的合法 `0` 分在界面上分不开，§7.1 末段的 `0` vs `null` 约束继续成立；⑥ **可见影响面只有两处**：F2 组合表的 `ERL Score` / `Stage` 列与 A1 ERL Card 的卡头（大数字 + 进度条 + Era + `X points out of 9`）。接口 22（A4 Score Details）的 `header.overallScore` 同路径一起变，但**该页自 v4.20 重排版起就不再渲染它**，界面上看不出来。连带：前端 `weightedOverallScore`（早已无页面引用、只剩自己的单测）随本版删除，前端此后一律取后端 `overallScore` 只做取整展示。**本版受影响面：§6.8 接口 20 / §7.1 / `ErlScoreCalculator` / `ErlLevelScorer#computeOverall` / `ErlPortfolioServiceImpl` / `ErlCardServiceImpl` / `ErlDimensionServiceImpl` / `ErlDimensionConfigService#codesOf`。** |
| v4.36 | **2026-09-15** | **需求方 2026-09-15：B3 历史列表的面包屑要跟来处走到底** | **纯前端、零接口改动、零数据库改动** —— 把 2026-09-14 定的「落地页面包屑 = 来处页面包屑 + 本页一级」补齐到 A3 这条入口，三条：① **A3（维度详情页）的 `View history` 此前不发 `?from=`**，B3 于是按缺省当作「从 A4 过来」、渲染成 `Portfolio Companies > Score Details > History`，与用户实际来处（A3）对不上；现改为发**写死的** `?from=companyOverview,dimension` ⇒ B3 接成 `Portfolio Companies > {公司名} > {维度名} > History`，即 A3 自己那三级 + `History`。写死而不接 URL 上的 `from`，是因为 A3 自己的面包屑本就是写死的那三级、与来处无关（两者必须同步改）；② `ERL_FROM` 新增 `dimension` 段，`erlTrailCrumbProps` 补 `dimensionName` / `dimensionUrl` 两个入参 —— 维度那一级显示**纯 `name`**（与 A3 页头同串，**不带缩写**，B3 H1 的 `name (abbr)` 是另一串）、点回 A3，显示名未就绪（`metaPending`）时该级**不占位**（同 `companyName` 的既有口径，空名字会让 `BreadCrumb` 连画两个分隔符）；③ 该链继续往下游传，B3 → 单次提交详情页因此接成五级 `Portfolio Companies > {公司名} > {维度名} > History > Record`（正好用满 `BreadCrumb` 的四前缀 + 末级槽位）。⚠️ **A4（Score Details）→ B3 那条本就已经是对的**（2026-09-14 落地，`DimensionQuestionsCard` 的 `View history` 一直在发 `[...from, scoreDetails]`），本版未动。**本版受影响面：`components/constants.ts`（`ERL_FROM` / `erlTrailCrumbProps`）/ `dimension/DimensionPage.tsx` / `history/HistoryPage.tsx` / `history/detail/HistoryDetailPage.tsx`。** |
| v4.37 | **2026-09-15** | **需求方 2026-09-15 裁决：维度分改取「最后一个整级通关的 level」** | **计分口径换底 —— 接口契约零变更、数据库零变更、前端零代码改动**，六条：① **维度分由 ~~「出现 No 的 level − 1」（`Math.max(0, level − 1)`）~~ 改为「该维最后一个『整级全部 Yes』通关的 level」** —— 即**踩 No 那一级在该维实际有题的 level 升序列表里的前一个**，一级都没通关则为 **`0`**；这正是现有 `DimensionScore#clearedLevel`，`ErlLevelScorer` 只需把 `levelScore` 的取值由「`terminatedLevel − 1`」换成「`clearedLevel`」，**算法主干与四态机一行不动**；② **稀疏题库下新旧不再相等** —— 某维只配了 level 1 / 2 / 7 / 9 时：全 Yes → `9`（**同**）、L9 内有 No → 新 **`7`**（旧 8）、L7 内有 No → 新 **`2`**（旧 6）、L2 内有 No → `1`（同）、L1 内有 No → `0`（同）。**level 连续时两者完全一致**，故本文档中 level 1/2/3 之类的连续举例一字不用改；③ **`terminated_level` 与 `level_score` 不再满足 `terminated_level = level_score + 1`** —— 稀疏题库下两列之间可以隔着若干个「该维没配题」的 level（§5.2 列注释就地订正）；④ ⚠️ **分值变离散**：维度分此后**只可能取「该维配置过的 level」或 `0`**（只配 1/2/7/9 ⇒ 维度分只会是 `0` / `1` / `2` / `7` / `9`），**综合分水位随之下移** —— 配得越稀疏、踩 No 那一级前面的空档越大，掉得越多；⑤ ⚠️ **历史数据不追溯**：`erl_assessment.level_score` 是**提交时冻结的快照**，本版只影响**此后的提交**；已提交的稀疏维度**继续带旧分（偏高）**，同一维度的历史曲线在本版前后因此不可直接比较，**是否回刷存量须另行裁决**；⑥ **不变的部分逐条列明，别读成更大范围的变更**：「**首个 No 即终止本维**」（v4.28）不变；「**全通关 = 该维最大有题 level、不是固定 9**」不变；`0` 是**合法低分**、`null` 才是「该维 0 题」的无数据（§7.1 末段）不变；**综合分 = Σ(各维度分) ÷ 维度个数**（v4.35）不变；Era / Stage 分段（§7.3）不变；`unlocked_level` / `terminated_level` 的语义与 BLOCKED / ACTIVE / CLEARED / LOCKED 四态不变；**接口 3 / 4 / 5 / 22 / 29 的出入参一个字段不增不减**，前端一律直出后端 `levelScore`、**零代码改动**。⚠️ **PRD §3.3 原文「分数就是此回答为 No 的 Level 减一」与 2026-09-03 原型的 `Math.max(0, i - 1)`，自本版起与本项目口径不再一致** —— 原文与原型事实**一字不改、照录存档**，回写建议见 §0.9-④ M1 / §0.10-④ M1。**本版受影响面：§0.9-③-22 / §0.9-④ M1 / §0.10-④ M1 / §2.3.1-① / §5.2（`level_score` / `terminated_level` 列注释）/ §7.1 / §7.2-① / §8.4（B 填报页解锁反馈）/ §9（某 level 内混有 Yes 和 No）/ §11-10 / §13-Q5 / `ErlLevelScorer` / `ErlLevelScorerTest` / `ErlAssessmentServiceImplTest`。** |
| v4.38 | **2026-09-16** | **需求方 2026-09-16：按钮行那句 `Draft saved …` 只在本次访问存过之后才出** | **纯前端、零接口改动、零数据库改动** —— B 填报页按钮行左下那一格的显示条件由「跟着接口 3 出参 `lastSavedAt` 走」改为「**本次访问内真正落盘成功过**」（置位点在 `runSave` 落盘成功那一支；`Submit` 先走的 `flush()` 同样会走到它，只是随后 `reload()` 又把它归零，屏上看不到）（`useAssessmentDraft` 新出参 `savedThisVisit`，换填报 / 重新挂载即归零）：刷新、退出重进都不显示，哪怕服务端存着草稿。「进来时接手了谁的草稿」由 2026-09-15 那条顶部 `Draft restored` 横幅讲，两格分工不再重叠 ——一进页面只可能看到横幅，刚存完只可能看到这一格。文案与取数口径见 §8.4-D9。<br>**本版受影响面**：`useAssessmentDraft.ts`（新出参 `savedThisVisit`）、`AssessmentPage.tsx`（按钮行那一格）、`useAssessmentDraft.test.tsx`；§6.3-D9 与 §8.4-D9 就地订正。 |
| v4.39 | **2026-09-16** | **需求方 2026-09-16 圈图：D2 分数框只能输入数字、`Whole numbers only` 提示不显示** | **纯前端、零接口改动、零数据库改动 —— 是 v4.34「只收整数」的收口**，两条：① `BenchmarkAddPage.renderScoreInput` 新增 `onKeyPress`，**非 `0-9` 的字符一律 `preventDefault`** —— 小数点 / 负号 / 字母 / 中文**当场就打不进框里**（v4.34 只有 `parser`，而 antd 4 的 `parser` 只改取值、不改显示，用户仍会看见自己敲的 `1.5a`）；`parser` + `precision={0}` **保留**，兜住粘贴与键盘上下键这两条不走 keypress 的路径；② v4.34 加的整数校验规则（`Number.isInteger` + 文案 **`Whole numbers only`**）**整条删除** —— 字符进不来之后它成了触发不到的死提示，屏上只会在必填红字下面多挂一行。⚠️ **必填（`Required`）与范围（`Must be between 1 and 9`）两条校验不动**；服务端校验、列类型 `numeric(3,1)`、存量一位小数记录的展示**一律仍未动**（v4.34-(a)(b)(c) 三条原样成立）。**本版受影响面：§6.5（D2 校验）/ §8.4-D2 / §11-37。** |
| v4.40 | **2026-09-16** | **需求方 2026-09-16 圈图：D1 卡一改名 `Current Version`、按检索季度取；`Record History` 按提交时间倒序** | **一条排序键的服务端变更 + 卡一取数口径的前端变更，接口出入参一个字段不增不减、数据库零变更**，三条：① **D1 卡一由 ~~`Latest by Dimension`~~ 改名 `Current Version`**，且显示的记录由「接口 15 的 `latest` 段（全库最大期次的那条）」改为「**URL 上下文期次 `?period=` 里提交时间最新的那条**」—— 前端直接从 `records[]` 里挑（该数组每条都带逐维明细，§6.5），该期次没有记录或 URL 没带期次时**落到列表首条 = 全库最近一次提交**；② **`Record History` 的排序键由 ~~`period DESC, created_at DESC, id DESC`~~ 改为 `created_at DESC NULLS LAST, id DESC`**（`ErlReferenceScoreRepository.findByCompanyIdOrderByCreatedAtDesc`，派生方法名表达不了 `nulls last` 故改 `@Query`）—— 补录旧期次的那条此后排在最前，`LATEST` 徽章随之由「最大期次的那条」变为「**最近一次提交的那条**」。⚠️ `nulls last` 不能省：Postgres 的 `DESC` 默认 `NULLS FIRST`，`created_at` 为空的历史行（屏上显 `—`）会被顶到最前、连徽章一起抢走；③ **「适用记录」那个方法一字不动** —— `findFirstByCompanyIdAndPeriodLessThanEqualOrderByPeriodDescCreatedAtDescIdDesc` 仍按 `period` 找 ≤ 当前展示期次的最近一条（§7.8），换成提交时间会把晚录入的未来期次基准错配到当期评估上。⚠️ **接口 15 的 `latest` 段就此没有消费方** —— 它算不出上下文期次，前端已改从 `records[]` 挑；字段**本版未删**（契约变更另议），已记两侧 `docs/待优化项.md`。**本版受影响面：§0.27-Z2 / Z3 / §6.5（接口 15 排序说明）/ §7.8 / §8.4-D1 / §11-35 / §11-38。** |
| v4.41 | **2026-09-16** | **需求方 2026-09-16 裁决：`Submit draft content` 改为「自动补一道 No」后照常提交** | **「部分提交」这个形态整体作废 —— 提交出来的行重新只有一种形态；接口契约只动接口 5 的一个入参名 + 删接口 7 的一个出参字段，计分公式、权限口径、UI 一律不变。**① **接口 5 入参 ~~`allowIncomplete`~~ → `autoAnswerNo`**：`true` 时服务端先给**顺序上第一道未作答的题**落一条 `yesNo = false` 使本维终止，**然后照常**走下方三条前置校验 —— ~~2026-09-15 那版「跳过两条校验的部分提交」~~ **由本版作废**，校验**没有任何旁路**；⚠️ **必须补第一道、不能补最后一道**：`unansweredCount` 只数「首个 No **之前**」漏答的题（v4.28），补在末尾的话它前面那些漏答依旧拦着提交。<br>② **`erl_assessment.unanswered_count` 列删除**（2026-09-15 由 V16 加入，本版由 **V17** 删除；`V1__erl_init.sql` 就地改为不建该列）：既然提交必已终止、漏答恒为 0，该列无信息量。随之删除的还有 `ErlAssessment#isCompleteSubmission()` 与接口 7 出参 `unansweredCount`；<br>③ **Share 门槛与 Goldie 生成门槛回到「两端每维都有 SUBMITTED 记录即算数」**（2026-09-15 曾加的「且都是完整提交」随 ② 一并撤下）—— ⚠️ 这是**实现侧回退**，§7.5-S1 / S2 的原文一直写的就是「有 SUBMITTED 记录」，本版无需订正、别去找那段 diff；<br>④ **`autoAnswerNo` 有前置条件**（2026-09-16 代码审核追加）：只有这份草稿**确实还绑在旧题库版本上**（`hasNewerQuestionSet`，与接口 3 决定弹不弹弹窗的是**同一处判定**）时才被接受，别的调用方传 `true` 会被**静默忽略**、照原规则校验。弹窗那条真实入口恒满足这条，拦的是 Swagger 直调 / 前端误传 / 将来别的入口 —— 不拦的话任何人都能把一题没答的维度提交成`level_score = 0`，而 ② 撤掉完整性门槛之后那一行与「用户真的在 L1 答了 No」**不可区分**；<br>⑤ **补出来的 No 与用户亲手答的 No 在库里刻意不可区分**（需求方明确接受）：它照常进历史详情与 Goldie 输入，事后无从分辨，这正是 ② 删掉的那一列原本承载的信息；<br>⑥ **本版同时回写 2026-09-15 已经落地但没进文档的「题库更新提示由 banner 改为强阻断弹窗」**（原 D10 的「非阻断、可关闭、无操作按钮」整体作废）：§0.10-D10、§0.30-Z5、§1.1 V1 范围表 B1、§6.3（接口 3 出参口径段）、§7.9 场景表、§7.10-N1 / N3、§8.2 与 §10 两处页面组成树、§8.4、§9 失败降级表、§11-82-⑥ / -83 **各处就地订正**。<br>⚠️ **发布耦合（两条，缺一不可）**：① 接口 5 是**入参改名**、接口 7 删了一个出参，故 **`CIOaas-api` 与 `CIOaas-web` 必须同批发布**。错批不会 500（Jackson 配的是 `FAIL_ON_UNKNOWN_PROPERTIES = false`，多余入参被**静默丢弃**），而是弹窗那一支退化成普通提交 ⇒ 半截草稿拿到 `Please answer all visible questions before submitting.`、被锁在不可关闭的弹窗里；② **先发代码、再跑 `V17`**（反方向 = 整个 ERL 模块 42703，见 §10.1 的 2026-09-16 补记）。 |
| v4.42 | **2026-09-16** | **需求方 2026-09-16：清空之后没再存过的空草稿，重进不许再弹 `Draft restored`** | **纯前端、零接口改动、零数据库改动。**顶部横幅的出现判据由「服务端 `status = DRAFT` 且有 `lastSavedAt`」**加一条 `answeredCount > 0`**。⚠️ 原因是接口 28（`Reset` / `Discard draft`，以及题库弹窗的 `Access new question library`）**清空答案但保留草稿行**（§6.3），而清空这一下自己会刷新 `updated_at` / `updated_by` ⇒ 重进时 `status` 仍是 `DRAFT`、`lastSavedAt` 还是个**刚刚的**时刻，横幅于是对着一份空草稿说「你在接着某某的草稿填，上次保存于 04:54」—— 屏上一个答案都没有，那句话是假的。「真有内容」只能问答案行数：清空后恒 0，存过草稿则 ≥ 1（接口 4 只落有 `yesNo` 的题，附件挂在答案行上、一并覆盖）。按钮行那句 `Draft saved …` 不受影响 —— 它自 v4.38 起本就只认「本次访问内自己存过」。<br>**本版受影响面**：`useAssessmentDraft.ts`（`applyAssessment` 里的横幅判据）、`useAssessmentDraft.test.tsx`（新增「Reset 清空后重进」一条 + 5 处夹具补 `answeredCount`）；§8.4-D9 就地订正。服务端一行未动。 |
| v4.43 | **2026-09-16** | **需求方 2026-09-16 圈图：Add / Edit Question 的题干要能写长，输入框限 2000 字符并显示字数** | **一列改宽 + 前端一处上限，接口出入参一个字段不增不减、计分与权限口径一律不变**，三条：① **`erl_question_config.question_text` 由 ~~`varchar(1024)`~~ 改为 `varchar(2048)`**（§5.1 字段表就地改）；② **服务端 `@Size` 跟着列宽走 2048**（`ErlQuestionConfigCreateRequest` / `ErlQuestionConfigUpdateRequest`）—— 它的职责是「别让库炸」，**不是**产品上限；③ **产品上限是 2000，只落在前端一处**：C2 / C3 共用的 `QuestionForm` 给题干文本域加 `maxLength={2000}` + `showCount`，超出打不进去、右下角实时显示 `n / 2000`（样式对齐 Company Overview 那个框：边框上移到 `showCount` 外层 div、计数贴框内右下角）。⚠️ 库比入口宽的那 48 是**留白不是第二个上限**，日后调入口上限（≤ 2048）不必再动库。<br>**本版受影响面**：`ErlQuestionConfig`（列长）、两个 Request（`@Size`）、`V1__erl_init.sql`（就地改宽 + 文件头登记）、**新增 `V18__erl_question_config_question_text_2048.sql`**（存量环境，⚠️ **必须先跑脚本再发代码** —— `ddl-auto: update` 只加列不改列宽，反过来 1024–2000 字的题干过得了 Bean Validation、写库 22001 ⇒ 接口 10 / 11 直接 500）、`QuestionForm.tsx` + `ConfigurationPage.less`。既有数据一行未动（只放宽不收窄）。 |
| v4.44 | **2026-09-16** | **需求方 2026-09-16 圈图：填报页 `Diligence evidence / rationale` 也要限 2000 字符并显示字数** | **纯前端、零接口改动、零数据库改动** —— `erl_assessment_answer.note` **本来就是 `varchar(2048)`**（§5.3，v3.0 即如此），接口 4 的 `@Size(max = 2048)` 也早已在，本版补的只是**入口那一道**：`AssessmentQuestionRow` 的证据文本域加 `maxLength={2000}` + `showCount`，超出打不进去、框内右下角实时显示 `n / 2000`（样式与 v4.43 的题干框同一档：边框挪到 `showCount` 外层 div、文本域去边框、计数贴框内右下角）。两条附带决定：① **`showCount` 恒开、禁用态只把计数行藏掉** —— 关掉 `showCount` 会让 antd 4.9 把 `className` 从外层 div 挪到 `<textarea>` 上（`className && !showCount`），同一个类名落到两种元素上样式整个错位；只读 / 未解锁 / 未作答的题行顶着一句 `0 / 2000` 也不像话。② 编辑态的框比只读态高一档（≈ 55px vs 40px）—— 计数行要占位，textarea 的最小高与底内边距已同步压过。<br>⚠️ **存量 2001–2048 字的备注不会被截断**：`maxLength` 只挡新输入，不动受控 `value`，原样回显、原样存回（服务端仍收 2048）；只是那种备注要改就得先删到 2000 以内。<br>**本版受影响面**：`AssessmentQuestionRow.tsx` + `AssessmentQuestionRow.less` 两个文件，服务端与数据库一行未动。 |
| v4.45 | **2026-09-16** | **需求方 2026-09-16 圈图：D2 `Add Benchmark Record` 的 `Note (optional)` 也要限 2000 字符并显示字数** | **与 v4.43 同型的一列改宽 + 前端一处上限，接口出入参一个字段不增不减**，三条：① **`erl_reference_score.note` 由 ~~`varchar(512)`~~ 改为 `varchar(2048)`**（§5.6 字段表就地改）；② **接口 16（`POST /erl/benchmark`，D2 保存记录）`ErlBenchmarkCreateRequest.note` 的 `@Size` 由 512 跟到 2048** —— 本表**没有更新接口**，改宽只影响新增这一条路径；③ **产品上限 2000 只落在前端一处**：`BenchmarkAddPage` 的 Note 文本域加 `maxLength={2000}` + `showCount`，超出打不进去、框内右下角实时显示 `n / 2000`。⚠️ 那 48 是留白**不是**第二个上限。<br>⚠️ **`showCount` 打开会把 `className` 从 `<textarea>` 挪到外层 div**（antd 4.9 `className && !showCount`），本页原来那句 `.noteInput.ant-input` 复合选择器随之失效 —— less 已按「容器承边框 / 文本域只剩文字」重写，计数行另需 `:global(.ant-form-item)` 祖先才压得住 antd 把计数甩到框外那条规则。框的总高因此比 2026-09-15 校准的 98px 高出约 22px（计数行），属需求变更不是校准漂移。<br>**本版受影响面**：`ErlReferenceScore`（列长）、`ErlBenchmarkCreateRequest`（`@Size`）、`V1__erl_init.sql`（就地改宽 + 列注释 + 文件头登记）、**新增 `V19__erl_reference_score_note_2048.sql`**（存量环境，⚠️ **必须先跑脚本再发代码**，理由同 `V18`；两份互相独立、先后无要求）、`BenchmarkAddPage.tsx` + `BenchmarkAddPage.less`。既有数据一行未动。 |
| v4.46 | **2026-09-16** | **需求方 2026-09-16 报障：D3 记录详情页的 `note` 超长时整页被撑宽** | **纯前端样式修复、零接口改动、零数据库改动**（是 v4.45 放宽 `note` 到 2048 之后立刻暴露的显示缺陷）。症状：标题下那行 `note` 若是**超长无空格串**（`1111…` / token / URL），会横着捅出正文列，把标题行、卡片与整页一起撑出横向滚动条。两处改动缺一不可：① `.note` 加 `overflow-wrap: break-word`（A3 `.noteBlock` 与 A4 `.notesText` 早就有这一条，本页 2026-09-15 加 `note` 行时漏了）；② 页头左格补一个 `.headerText { min-width: 0 }` —— **`.pageHeader` 是 flex 容器**，子项默认 `min-width: auto`（不小于内容的 min-content 宽），而 `overflow-wrap: break-word` 按规范**不改变** min-content 宽度，只加 ① 那一条断不开，这一格照样把页面撑宽。（不用 `overflow-wrap: anywhere` / `word-break: break-all`：前者 Safari 15.4 才支持、后者会把正常英文单词也拦腰截断。）<br>**本版受影响面**：`BenchmarkRecordPage.tsx` + `BenchmarkRecordPage.less`，两个文件。 |
| v4.47 | **2026-09-16** | **需求方 2026-09-16 圈图：D3 记录详情页的 `note` 由标题下挪到卡片内** | **纯前端、零接口改动、零数据库改动。**`note` 的落点由 ~~页头 `<h1>` 之下~~ 改为 **`By Dimension` 卡片内、维度表之下**（v4.45 放宽到 2048 之后，标题与 `Back` 之间顶着一大段灰字很喧宾夺主）。上边距 8 → 16px，与表格末行拉开。<br>⚠️ **v4.46 的 `.headerText { min-width: 0 }` 随之删除** —— 它存在的唯一理由是「页头是 flex 容器、子项 `min-width: auto` 挡住 `break-word`」，`note` 一挪进卡体（普通块级容器，行盒天然被卡宽限住）这条就没用了；`.note` 的 `overflow-wrap: break-word` **保留**，否则超长串照样捅出卡片。<br>**本版受影响面**：`BenchmarkRecordPage.tsx` + `BenchmarkRecordPage.less`；`BenchmarkRecordPage.test.tsx` 的断言是「文本在页面上」、不绑位置，**无需改**（只更了注释）。 |
| v4.48 | **2026-09-16** | **需求方 2026-09-16 圈图：D3 的 `note` 改成 A3 / A4 那个 `NOTES` 灰底块** | **纯前端、零接口改动、零数据库改动**（v4.47 挪位之后同日的第二次圈图，只改长相不改落点）。`note` 由 ~~本页私有的 14px 裸文本~~ 改为**复用域级共享的 `.noteBlock` / `.noteLabel`**（`pages/exitReadiness/components/index.less`）+ 同一条 `TEXT.notesLabel` —— 小号大写 `NOTES` 标签 + 浅灰底 + 4px 圆角 + 13px 正文，与 A3 逐题行、A4 Score Details 的备注块**一模一样**，本页**不另写样式**。<br>⚠️ **v4.47 那句「上边距 8 → 16px」随之作废** —— 本页私有的 `.note` 类已整块删除，间距改由共享类的 `margin-top: 8px` 决定（灰底本身就把它和表格分开了）；`overflow-wrap: break-word` 共享类自带，v4.46 的防溢出结论不变。<br>**本版受影响面**：`BenchmarkRecordPage.tsx` + `BenchmarkRecordPage.less`（删类）；测试断言不绑位置与样式，**无需改**。 |
| v4.49 | **2026-09-16** | **需求方 2026-09-16 圈图：D3 备注块的标签 `NOTES` 改为 `Note (optional)`** | **纯前端、零接口改动、零数据库改动**（同日第三次圈图，只改标签文案）。D3 的备注块标签由共享的 ~~`NOTES`（`TEXT.notesLabel`）~~ 改为 **`Note (optional)`**，与 D2 录入页那个字段的 label 逐字一致。<br>⚠️ **只改 D3 一页**：`TEXT.notesLabel` 还挂着 A3 逐题行与 A4 Score Details（两页 2026-09-16 刚统一成 `NOTES`），动共享常量会顺手改掉那两页，故本页写字面量、**不动 `TEXT`**。<br>⚠️ 共享的 `.noteLabel` 带 `text-transform: uppercase`（A3 / A4 的 `NOTES` 靠它成型），本页要原样大小写，故加一个本页私有的 `.noteLabelCased { text-transform: none }` 关掉它 —— 类名写两遍抬特异度，因为它盖的是同为单类的共享 `.noteLabel`。块样式（灰底 / 圆角 / 13px / `break-word`）仍**全部复用共享类**。<br>**本版受影响面**：`BenchmarkRecordPage.tsx` + `BenchmarkRecordPage.less`；测试不断言标签文案，**无需改**。 |
| v4.50 | **2026-09-16** | **需求方 2026-09-16 报障：C1 题库列表的超长题干显示不全、把表撑破** | **纯前端样式修复、零接口改动、零数据库改动**（与 v4.46 同一类缺陷，是 v4.43 把题干放宽到 2000 之后暴露的）。两条改动**缺一不可**：① C1 的题目表 `.table` 加 **`table-layout: fixed`** —— `auto` 布局下列宽由内容的 min-content 宽决定，而 `overflow-wrap: break-word` 按规范**不改变** min-content 宽度，只给单元格加 `break-word` 一点用没有；改 `fixed` 后列宽只看四个写死 px 的 `.col*`（40 / 224 / 256 / 96），QUESTION 列吃剩余空间；② `QuestionBandGroup.less` 的 `.text` 与 **`.source`** 各加 `overflow-wrap: break-word` —— `.source` 也要加，因为固定列宽之后 255 字符的来源标签同样撑不开自己那一列、不给断点就会溢到 ACTIONS 列上。<br>⚠️ 代价：`th` 上的 `white-space: nowrap` 不再能把列撑开，四个列头都是短词、现有列宽装得下；**日后改列头文案或收窄列宽时要一并核一眼**。<br>⚠️ **C7 题库版本历史页（同一份数据的另一张表）本轮未动**：它外面套着 `.tableScroll { overflow-x: auto }`，超长串只在那层里拉横向滚动条、页面不塌，属「要不要也改成换行」的产品口径问题，已记入 `CIOaas-web/docs/待优化项.md`。<br>**本版受影响面**：`ConfigurationPage.less` + `QuestionBandGroup.less`，两个样式文件。 |
| v4.51 | **2026-09-16** | **需求方 2026-09-16 报障：B 填报页的超长题干显示不全、捅出卡片** | **纯前端样式修复、零接口改动、零数据库改动**（v4.46 / v4.50 同一类缺陷的第三处，都是 v4.43 把题干放宽到 2000 之后暴露的）。`AssessmentQuestionRow.less` 的 `.stem`（题干）与 `.sub`（`{Era} · Source: {来源}`，来源同为用户录入、最长 255 字符）各加 `overflow-wrap: break-word`。<br>⚠️ **这里只需这一条**，不像 C1 那张表还得先把 `table-layout` 改 `fixed`：父级 `.headMain` 早就有 `flex: 1; min-width: 0`，flex 子项缩得下来、行盒已被卡宽限住，`break-word` 直接生效。三处缺陷的差别正在于「行盒有没有先被限住」——`min-width: auto` 的 flex 子项（v4.46）、`table-layout: auto` 的表格列（v4.50）都得先解决这一层。<br>⚠️ **A3 逐题行（与 B3 详情共用 `components/index.less` 的 `.questionText` / `.questionMeta`）与 A4 Score Details（`ScoreQuestionRow.less` 的 `.stem` / `.sub`）同型缺陷本轮未动** —— 需求方只圈了 B 填报页；两处父级同样已有 `min-width: 0`，修法与本条逐字相同（各加一条 `break-word`）。<br>**本版受影响面**：`AssessmentQuestionRow.less` 一个样式文件。 |
| v4.52 | **2026-09-16** | **需求方 2026-09-16 报障：A3 维度详情的超长题干显示不全** | **纯前端样式修复、零接口改动、零数据库改动 —— 至此「超长题干/备注撑破布局」这一类缺陷全域收口**（v4.46 D3 备注、v4.50 C1 题库表、v4.51 B 填报页、本版 A3 / B3 / A4）。两个文件各两条 `overflow-wrap: break-word`：① `components/index.less` 的 `.questionText` / `.questionMeta` ——**A3 维度详情与 B3 单次提交详情共用 `QuestionRow`，一处即两页**；② `ScoreQuestionRow.less` 的 `.stem` / `.sub`（A4 全维 Score Details，需求方未圈，**随本轮一并收掉**：它与 A3 是同一份题目的同一种渲染，留着必然是下一条报障）。副行都带一条，因为 `Source: {来源}` 同为用户录入（最长 255 字符）。<br>⚠️ 这三处都**只需 `break-word` 一条**，父级（`.questionMain` / `.main`）早就有 `flex: 1; min-width: 0`。**全域口径记在这里，日后新写只读题行照抄**：行盒先被限住（flex 子项给 `min-width: 0`、表格列给 `table-layout: fixed`），文本再给 `overflow-wrap: break-word`；两步缺一不可，因为 `break-word` 按规范**不改变** min-content 宽度。<br>**本版受影响面**：`components/index.less` + `ScoreQuestionRow.less`，两个样式文件。 |
| v4.53 | **2026-09-16** | **需求方 2026-09-16 裁决：ERL Score 的分子改回按维度权重加权** | **计分口径变更 —— 接口契约零变更、数据库零变更、前端零逻辑改动**，五条：① **综合分由 ~~`Σ(各维度分) ÷ 维度个数`~~（v4.35 的等权口径，只活了一天）改回 `Σ(各维度分 × 该维权重)`** —— `ErlScoreCalculator.overallAverage(levelScores, dimensionCodes)` 换成 `overallWeighted(levelScores, weights)`，权重经 `ErlDimensionConfigService#weightsOf` 取；需求方算例：FRL 2 分 20% + PRL 4 分 20%、其余未填 = `1.2` → 展示 `1/9`。② **未填写的维度仍按 `0` 计入、其余维度的权重不归一化** —— v4.35 这一条口径原样保留，v4.4 / §0.9-20 的「剔除该维、其余权重按比例归一化」**继续作废**。③ **百分比换算的除数取「权重表的权重合计」而不是写死 `100`** —— §9 等权降级是 `100 ÷ 维度数` 保留 4 位小数（3 维合计 `99.9999`），写死 100 会让降级路径的满分算成 `8.9999`。④ **v4.35 为等权口径新增的 `ErlDimensionConfigService#codesOf` 随本版删除**（无其它调用方）；`weightsOf` 重新成为综合分的权重来源，Goldie 差距分析的入参组装（§6.6）继续共用。⑤ **Stage / Era 跟着新分数走**（两者本就由 `overallScore` 推导，`stageOf` / `eraOf` 一字未改）；零提交仍是 `null` 空态、不按 `0.0` 算。**可见影响面**与 v4.35 相同的两处：F2 组合表的 `ERL Score` / `Stage` 列与 A1 ERL Card 的卡头；接口 22 的 `header.overallScore` 同路径一起变，但该页自 v4.20 起不再渲染它。**改权重即回溯改变历史期次的综合分**（§7.11-W1 已裁决接受漂移）这条因本版重新生效 |
| v4.54 | **2026-09-16** | **需求方 2026-09-16 报障：清空之后没再存过的空草稿，期间发布了新版题库，重进又撞上「题库已更新」弹窗** | **纯前端、零接口改动、零数据库改动 —— 与 v4.42 同根同源的第二处**（那一版治的是横幅，本版治的是弹窗）。接口 28（`Reset` / `Discard draft` / 弹窗的 `Access new question library`）**清答案但保留草稿行**并改绑到清空那一刻的最新版本（§6.3 / §0.30-Z5），此后管理端再发一版，这条**一个答案都没有**的草稿又成了「旧版本草稿」⇒ `status = DRAFT` + `hasNewerQuestionSet` 同时成立，弹窗照弹 —— 而它给的两条路（`Submit draft content` 按旧题库就地提交 / `Access new question library` 清空换新题库）对着一份空草稿**都没有意义**：没有内容可提交，也没有内容可清。两条改动：<br>① **`useAssessmentDraft.load` 新增 `rebindEmptyDraft`**：接口 3 回包若是「`status = DRAFT` 且 `hasNewerQuestionSet` 且 `answeredCount = 0`」，就地替它走一次**接口 28**再重拉 —— 草稿是空的，所谓「清空」只剩**改绑**这一个动作，**不删任何用户内容**（附件恒挂在答案行上，没有答案行就没有附件）⇒ 屏上直接换成新题库、弹窗本来也走不到。⚠️ 这不违反「不点按钮绝不写库」（v4.29）：那条讲的是**用户的作答**，这里一个字的作答都没有，动的只是版本指针。⚠️ 判据只认**这一拉的服务端回包**，不是 state 里的 `assessment.answeredCount` —— 后者会被接口 29 用本地未落盘的答案数改写。⚠️ 改绑**失败不报错**：按旧题库继续填、不弹 toast（它是替用户省一次点击、不是他要求的动作）。<br>② **弹窗的门加第三条「草稿真有内容」**（`AssessmentPage.questionSetUpdated`）：由 ~~`status = DRAFT && hasNewerQuestionSet`~~ 改为再要求 `draft.restoredDraft` 非空（该快照进页面钉死一次、判据里已含 `answeredCount > 0`，与 v4.42 横幅同源）—— 兜的是①**改绑失败**那一路：旧题库继续填，但**仍然不弹**。取 `restoredDraft` 而不是 `assessment.answeredCount > 0` 的理由同上：后者填报途中会从 0 跳到 1，弹窗会在填报中途弹出来。<br>**服务端为何不动**：更彻底的修法是接口 3 返回前就地改绑空草稿，但那会把一个 GET 变成写操作 —— 类上是 `@Transactional(readOnly = true)`、`findDraft` 不加锁（并发打开同一草稿会撞 `@Version` 乐观锁 ⇒ 打开问卷直接报错）、且 `@PreUpdate` 会把 `updated_at` / `updated_by` 刷成「查看者刚刚保存过」，而接口 3 的 `lastSavedAt` / `lastSavedBy` 正读这两列。已记入 `CIOaas-api/docs/待优化项.md`。<br>**本版受影响面**：`useAssessmentDraft.ts`（新增 `rebindEmptyDraft` + `load` 串上它）、`AssessmentPage.tsx`（`questionSetUpdated` 加一条）、`useAssessmentDraft.test.tsx`（新增 3 条用例 + 2 处夹具补 `answeredCount`）；§6.3 接口 3 出参口径段、§8.4-B、§11-94 就地订正。服务端一行未动。 |
| v4.55 | **2026-09-17** | **`V1__erl_init.sql` 的初始化数据（四份种子）整段删除** | **纯部署脚本改动、零接口改动、零代码改动，但有一处实质行为变更。**`CIOaas-api/deploy/upgrade_doc/sprint118/V1__erl_init.sql` 原第 ③ 段的四条 `INSERT`（每组织一条 `PUBLISHED` 题库版本行 / 五行 `erl_dimension_config` / 15 道 `[PLACEHOLDER]` 题目 / 每维一行发布快照）**整段删除**，该脚本此后只建表、建索引与唯一约束。<br>**行为变更**：跑完 `V1` 是**空库** —— 题库版本、维度配置、题目、维度快照四样全无，**任何组织**在配置页录入维度并 Publish 第一版题库之前，填报页空态、维度列表为空、综合分走 §9 的**等权降级**路径。原先「种子使系统起来即与『简单平均』等价、不出现权重未配的空窗」（§5.1.3）**作废**：那个空窗现在是新库的**默认状态**，不是异常。<br>⚠️ **`FRL / PRL / BERL / RRL / TRL` 这五个可读 code 从此只是叙述用的举例**（存量库里仍有这几行真实数据）—— 「种子数据例外」这条 `dimension_code` 格式例外**不再成立**，但结论不变：新建维度一律走 `{abbr 前 3 位}{4 位随机}` 生成，而存量库里两种形态并存，**任何正则 / 长度 / 前缀 / 大写断言依旧都会误杀一方**（§5.1.3）。<br>**本版受影响面**：§2.2 / §5 引言 / §5.1 / §5.1.3 / §7.9 / §9 / §10.1 / §11（用例 5、72、77、86-⑰、88-①）/ §13-Q4 就地订正；`sprint118` 的 `README.md` 与 `V3` / `V5` / `V9` / `V10` / `V18` 的相关注释同批订正。代码与接口一行未动。 |
| v4.56 | **2026-09-17** | **需求方 2026-09-17 圈图两条：D1 空态里重复的 `Add New` 撤下；B3 空态收掉列头并补配图** | **纯前端、零接口改动、零数据库改动。**① **D1（`/exitReadiness/benchmark`）无记录时空态内那颗 `Add New` 删除** —— 页头已有一颗，同屏两颗是同一个入口重复；删后 D1 与 A4 基准 Tab 同构（按钮在卡头 / 页头、空态只有配图与文案）。⚠️ 被删那颗原本就带 `companyId &&` 门控，**缺 `companyId` 时改动前后都是 0 颗**，不是本版引入；全站进 D2 的入口仍有两处（D1 页头、A4 基准卡头），均带 `companyId`。② **B3（`/exitReadiness/history`）空态 = `PRESENTED_IMAGE_SIMPLE` 收纳盒配图 + 文案，且连列头一起收掉** （`showHeader={loading \| records.length > 0}`）—— 空表上留一条列头灰带像「只加载了一半」。**加载中仍留列头**（有数据那条主路径全程无跳变）；空结果那条路径的塌陷只是从「加载开始」挪到「加载结束」，不是消除了，要彻底无跳变只能让列头常驻、与需求方口径冲突，故按现状取舍。⚠️ **这是全仓唯一「空列表收列头」的表**，同域 `BenchmarkDimensionTable` / D2 维度表 / C1 题库表照旧常驻列头，别当全域口径去推平。③ 审核补一条：B3 的空态压制条件由 `loading` 扩到 **`loading \| error`** —— 取数失败时 `useAssessmentHistory` 会把 `records` 置空且 `loading` 落回 false，不守 `error` 的话屏上是「错误横幅 + 配图 + 确凿地说没有记录」两条互斥结论（D1 的空态分支一直是 `!loading && !error && !hasRecords`）。<br>**本版受影响面**：§8.4-B3 行、§9「无基准记录」行就地订正；前端 `BenchmarkPage.tsx` / `HistoryPage.tsx` 及两个 `.test.tsx`、`src/pages/exitReadiness/README.md`。接口、数据库、Java / Python 一行未动。 |
| v4.57 | **2026-09-18** | **ERL Gap Analysis 开发设计 v1.0 的 P0 / P1 / P2 已定档并实现**（`erl-gap-analysis-dev-design.md` §0.1 裁决 R4 ~ R9 / R11、§3 ~ §5） | **三件事：两条既有裁决被推翻 + 一次列改名，接口只增一个出参字段、入参每题增一个数组。**① **ERL 答题附件改走独立 space + 新处理类型 `SUMMARY_ONLY`**（**推翻 §13-Q10**「沿用现有端类型规则、不为 ERL 单开空间」）—— 业务关联组合键的 `business_type` 换成 **`ERL_ATTACHMENT`**（APP 按公司 / ADMIN 按组织，粒度不变），**只解析正文 + 出摘要，不分片不向量化**、`ai_rag_ent_kb_chunk` **零行**，正文落 `ai_rag_entry.content_text`（截断 1,000,000 字符，`char_count` 记真值）、摘要落 `.summary`；ERL 附件因此**不进** chatbot 检索、Memory 面板与知识库面板（§13-Q10 / §6.7 / §9）。Python 端点 `/api/ai/erl/attachments/ingest` 同批**改名** `/attachments/summarize`；`erl_answer_attachment.ingest_status` **列名沿用、语义改写为「摘要生成状态」**（裁决 R8，`sprint118/V20` 只改 COMMENT）。② **附件摘要接进 Goldie** —— §6.6 入参每题新增 `attachments[{fileId, fileName}]`（**Java 只送 id 与文件名，不碰摘要**），摘要由 Python 按 `fileId` 批量现取 `ai_rag_entry.summary`、取不到即 `summaryAvailable = false`，**不等待不阻断**；出参维度项新增 **`narrative`**（维度级叙述段，落库为第三个 `item_type = NARRATIVE`）；`evidenceMissing` 判定由「该题无备注」放宽为「该题**无备注且无可用附件摘要**」，前端文案随之由 ~~`No notes provided`~~ 改为 **`No supporting evidence provided`**（串名 `noNotesProvided` 沿用）。prompt `erl_gap_analysis.md` 升至 **v1.4**（§5.8 / §6.6 / §8.4 / §9 / §11-28）。③ **`erl_gap_analysis_item.dimension` 列改名 `dimension_code`**（`sprint118/V22`），§6 开头 2026-09-08 定规时特意留的那条「本轮不改列名」**例外就此消除**，五处关联键清单一并订正。逐条见 §0.31。<br>⚠️ **P3（产物搬迁 Python）与 P4（题库版本 mismatch）本版一律不回写** —— 两者**尚未开发**，§7.10-N1 / N2 与 §12「不做题集版本不一致的告警 / 阻断」**保持原样**；文档不得比代码超前（**P4 已于 v4.58 回写、P3 已于 v4.59 回写**） |
| v4.58 | **2026-09-19** | **ERL Gap Analysis 开发设计 P4（题库版本 mismatch 提示 + 小卡第四态）已实现**（`erl-gap-analysis-dev-design.md` §7） | **一处新增判定 + 出参两个字段 + 前端一个新状态；入参、数据库、Share 门槛、计分口径一律未动（Python 侧零改动）。**① **判据只能是维度级的 `erl_question_config_dimension_version.question_version_no`** —— 组织级发布批次号 `erl_question_config_version.version_no` **不能用**（发 v8 时可能只改了 FRL，拿批次号比会把一字未动的 PRL 误判成不可分析 = 假阳性），两端实际作答的 `questionKey` 集合**更不能用**（逐级解锁下两端止步 level 天然不同）；取数复用 `bothSubmitted` 已查出的两端 SOT 行，版本号按 `(版本行 id, dimension_code)` 复合键**一次 `IN` 批量查**（评估行上的捷径列可空，故读侧走复合键）。② **接口 1 与接口 17 的 `dimensions[]` 各新增 `questionSetMismatch: boolean` + `mismatchSide: FOUNDER \| GSV`**（落后的一端 = 版本号较小的一方，方向服务端算好下发、前端不复算）——⚠️ 这是与 `bothSubmitted` / `hasGap` **并列的第三条独立布尔**，压进 `hasGap` 就是 `false` ⇒ 渲染成绿点 `No Gap`，GSV 以为该维没问题照常 Share（与 §6.6 那条 index 幻觉防的是同一类假阴性）。③ **前端四级优先级写死**（`!bothSubmitted` → `questionSetMismatch` → `hasGap` → else）：A1 小卡新增**黄点 + `Question set mismatch`**，`View details` 该维分区出琥珀药丸 + 按端分叉的说明（管理端带方向、公司端中性）；**mismatch 排在 `hasGap` 之前** —— 旧产物未被覆盖时两者会同真，此时旧条目与旧 `narrative` 都不渲染。④ **生成侧跳过 mismatch 维度**（`index` 按下发顺序重排后仍连续），**全维 mismatch 时不调 Python**（空 `dimensions` 会被 Python 判 400）、不报错、旧产物原样保留。⑤ **版本号解不出时 fail-open**：WARN 后按「不 mismatch」继续分析 —— 快照行缺失是数据问题不是业务状态。⑥ **Share 门槛与计数文案一字不改**（`shareable` 口径不带 mismatch 条件；mismatch 时 `hasGap = false`，`{n} of {total}` 自动不计入）。⑦ 随本版回写 **§7.10-13 / N1 / N2 与 §12** 那两处「不做题集版本不一致的告警」结论。逐条见 §0.32 |
| v4.59 | **2026-09-19** | **ERL Gap Analysis 开发设计 P3（差距分析产物搬迁到 Python）已落地并回写**（`erl-gap-analysis-dev-design.md` §6；裁决 R1 / R2 / R3） | **服务端内部的所有权变更 —— 对外三个接口（17 / 18 / 27）出入参一字未动、前端零改动、数据库对 Java 只减不增。**① **产物两张表搬到 Python 并加 `ai_` 前缀**（`ai_erl_gap_analysis` / `ai_erl_gap_analysis_item`，Python 迁移 `V024__erl_gap_analysis.sql`）—— 因为改了表名，这**不是「同表换所有权」而是建新表 + `INSERT … SELECT` 迁数据**；**旧表刻意不 DROP**，留作回滚路径、由 Java 侧下一个 sprint 单独出脚本。Java 侧两个实体 + 两个仓储**已删除**，域内一律经 `ErlGapAnalysisService#loadResult` 取产物。② **`stale` 列取消，改为读接口现算派生** —— `S1 成立 && 现算提交批次指纹 ≠ 产物里存的 `submission_signature``；指纹 = 当前 Active 维度 × 双端 SOT `erl_assessment.id` 排序拼接后 SHA-256，**由 Java 算、Java 比，Python 只存不算不比**。⚠️ **`S1 成立` 这个前置条件不能省**：新增一个两端都没提交的 Active 维度时指纹永远不等，页面会永久显示 `Refreshing analysis…`。③ **并发控制整体下移 Python** —— Java 侧 Redis 锁、`SELECT … FOR UPDATE` 行锁协议、失败重试补跑全删；写入方从 3 个降到 2 个且都在 Python 进程内，Redis 锁（key `erl:gapAnalysis:{companyId}:{period}`、TTL 600s、释放前比 token）+ 单表短事务足够。`shared` 的复位随「覆盖产物」一起在 Python 侧做。④ **Java↔Python 由一个端点扩为三个**：`/gap-analysis/refresh`（生成并落库）、`GET /gap-analysis`（读产物，**无产物也 200**）、`/gap-analysis/share`（置位，门槛仍由 Java 校验）；读超时按端点分开（refresh 180s，读与 share **10s**）。⑤ **refresh 入参的维度项从此同时带 `index` 与 `code`** —— `code` **仅供 Python 落库，渲染 prompt 时写死剔除**（有单测断言「渲染结果不含 dimension code」），§6.6 原先「`code` 不进入参」的论证随之改判；出参仍只有 `code`，`index` 不出现在任何出参里。⑥ **触发时机补全为三个触发点**（提交后异步 / 读接口 17 被动自愈 / 管理端手动），并补上「没有定时任务、没有扫描器」「最后一个维度的最后一端提交时 S1 首次成立，那一次提交触发的异步任务就是首次生成」两句结论与「不触发情形」表。⑦ **§7.11 接口 24 那条「同事务把该组织全部差距分析置脏」随本版失效**（跨服务已不可能同事务）—— 改由「Active 集合进指纹」自然覆盖，并记下它留出的一个边界（见 §0.33-X11）。逐条见 §0.33 |
| v4.60 | **2026-09-20** | **需求方 2026-09-20 三处前端调整已实现**（`CIOaas-web` `28695d36` / `16a76b00` / `536274e3`） | **纯前端展示，数据库 / 接口契约 / Java / Python 一律未动。**① **A1 Gap 区块的分享次级文字 `Shared {time} by {name}` 整行撤下**（两端都不显示；按钮态不变，接口 17 照旧下发 `sharedAt` / `sharedBy`，只是不再上屏）；② **A2 雷达图追加「维度数 < 3 整块不渲染」门槛**（含标题条；门槛取 `dimensions[]` 长度，与顶点标签同源；**雷达图正下方的基准入口不跟这道门槛**，见 §0.34-Y2）；③ **Gap 详情弹框 `SUGGESTED ACTIONS` 条目图标由 lucide `circle-dot` 换成 `target`**（尺寸 / 颜色 / 描边未动）。详见 §0.34 |
| v4.61 | **2026-09-20** | **需求方 2026-09-20 裁决：差距分析改为「维度级增量生成」** | **分析单元由「期次」降到「维度」——生成门槛、提交批次指纹、落库粒度、前端状态机四处同步改；Share 门槛刻意不动。**① **生成门槛 S1 由「全部 Active 维度两端都提交」改为「至少有一个可分析维度」**（可分析 = 该维两端都有 `SUBMITTED` 且非题集 mismatch）——某一维两端一凑齐就立刻分析这一维，不必等其余维度；5 维里先交完 1 维就能看到该维结论。② **提交批次指纹由期次级下沉到维度级**（`sha256(code\|founderAssessmentId\|gsvAssessmentId)`），新建**第 13 张表** `ai_erl_gap_analysis_dimension` 承载它 + `has_gap` + `generated_at`；`ai_erl_gap_analysis.submission_signature` 随之**废弃停写**（恒 NULL，下个 sprint DROP）。③ **落库由「全量替换条目」改为「按维度覆盖」** —— 只删重跑那几维的 item，其余维度的结论原样保留。④ **「维度行存在 = 该维已分析」**：接口 17 / 18 / 27 的 `dimensions[]` 新增 `analyzed` / `analyzedAt` / `dimensionStale` 三个字段，前端小卡状态机由四态扩到**六态**（新增 `Analyzing…` / `Updating…`）—— **`No Gap` 从此只在真的分析过之后出现**，堵掉「尚未生成也渲染成绿点 `No Gap`」的假阴性（这正是 §6.6 末尾那条早已预告、`CIOaas-api/docs/待优化项.md` 2026-09-20 登记的缺陷）。⑤ **Share 门槛 S2 维持「全维两端提交 + 无 mismatch」不变**（需求方裁决：半份报告不发给创始人）——`allDimensionsSubmitted` 保留，专供 S2，不再兼任生成门槛。⑥ **重生成复位 `shared` 维持无条件**（需求方裁决），频率随增量化上升是已知代价。⑦ prompt 升 **1.5**，新增只读入参 `analyzed_context_json`，让期次级 `summary` 覆盖「本轮分析 + 此前已分析」的全貌。⑧ **存量不回填**（需求方裁决）：老产物没有维度行 ⇒ 读成「未分析」⇒ 触发点 B 自动重跑一轮自愈。逐条见 §0.35 |
| v4.62 | **2026-09-20** | **需求方 2026-09-20：Share 按钮分享后不改文案** | **一处纯前端文案态调整，接口契约 / 门槛 / 数据库一律未动。**A1 Gap 区块的 `Share to founder` 按钮**已分享后文案保持不变、只置灰**；~~切成禁用的 `Shared`~~ 作废（该口径自 v4.4-D3 起沿用，v4.60-Y1 撤次级文字时还特意声明「按钮态不变」，本版把按钮态本身也改了）。理由：同一颗按钮随状态换标签，会让「这颗按钮是干什么的」跟着漂移；禁用态本身已经表达「现在点不了」，再换一次措辞是多余的一层。实现上两个禁用成因合并成一个 `disabled`（`shared` 已分享过 / `!canShare` 服务端 `shareable` 未放行），不再按 `shared` 分叉渲染两颗 Button；`TEXT.shared` 随之无消费方、已删除。详见 §0.36 |
| v4.63 | **2026-09-20** | **2026-09-20 实测缺陷：已分享的期次出现 mismatch 后创始人仍看得到** | **一处读侧派生，接口契约只增语义不增字段；数据库、Python、Share 门槛本身一律未动。****公司端的「已分享」改为读侧派生** —— 由「直接读 `shared` 列」改成「`shared` 列为真 **且** 该期次当前仍满足分享门槛（§7.5-S2 三条）」。成因：复位 `shared` 一直搭在**重生成**上（Python `overwrite_generated` 无条件复位），而 v4.61 把指纹下沉到维度级之后，「某维变 mismatch」**不改变任何可分析维度的指纹** ⇒ `toRefresh` 为空 ⇒ 压根不调 Python ⇒ 复位永不发生。改造前指纹是期次级的、任一次提交都会让它变化，所以「GSV 重新答题就结束分享」看着像规则，其实只是重生成的副作用 —— v4.61 把这层隐式耦合弄丢了。**已知代价（需求方 2026-09-20 知情后选择口径单一）**：判据复用 `isShareable`，故「新增一个两端都还没提交的 Active 维度」也会让创始人暂时失去访问。详见 §0.37 |
| **v4.64** | **2026-09-20** | **需求方 2026-09-20：分析过程中去掉顶部提示** | **一处纯前端删除，接口契约 / 出参 / 服务端一律未动。**A1 Gap 区块顶部那条期次级横幅 `Refreshing analysis…` **整条撤下**。理由：v4.61 给每个维度小卡加了 `Analyzing…` / `Updating…` 之后，进行时已经**逐维**说清楚了，顶部再压一条笼统的横幅是同一件事说两遍；且横幅是**期次级**、小卡是**维度级**，粒度不同还容易打架（横幅亮着、几张卡却全是终态）。`stale` / `generating` 两个出参字段**保留不动**（前端仍用它们判「已分享过的内容又被重生成」⇒ 提示需重新分享）；`TEXT.refreshingAnalysis` 随之无消费方、已删除。详见 §0.38 |
| **v4.65（本版）** | **2026-09-24** | **需求方 2026-09-24 裁决：差距分析任务化（sprint119）** | **数据模型、Java↔Python 契约、生成门槛、分享冻结方式四处同改；前端六态代码不动。**① 产物归属再切分：Java 新增 `erl_gap_analysis_report`（报告分享记录）+ `erl_gap_analysis_dimension_task`（按维度任务，含两端 SOT id / status / has_gap / result_task_id / deleted），Python 改为 `ai_erl_gap_analysis_task`（生成日志 + 幂等标记）+ `ai_erl_gap_analysis_task_item`（条目，一次写入永不改）；② **生成门槛回到报告级**（全部 Active 维度两端 SUBMITTED 且无 mismatch），v4.61-G1 维度级门槛作废；③ **已分享记录不可变**：任一端改动 ⇒ 新建记录、未变维度复制任务，未分享记录就地软删重建 —— 取代 V027 `shared_snapshot` JSONB 冻结；④ Java → Python 仍同步 HTTP，refresh 响应逐任务回 `{taskId, status, hasGap}`，新增 `POST /items` 按任务批量取条目，删 GET / share 端点与 Python 期次级 Redis 锁；Python 每任务一次 LLM，prompt 升 1.7；⑤ 砍掉 summary / analyzedContext / model / generated_at / note / why / evidence_missing / stale / generating / analyzedAt / dimensionStale 全链；⑥ 指纹 `submission_signature` 全链删除，改比任务行的两个 source id。详细设计见 `docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md`，逐条见 §0.39 |

---

## 0. 目标与裁决原则

### 0.1 一句话目标

在 LG 平台内实现**退出准备度（Exit Readiness Level, ERL）**：**替代 Company Overview 页的 Development Intelligence（DI）板块**，由创始人（Founder）与 GSV 团队各自独立完成季度评估，**按维度分别提交**（v4.4），从若干维度（出厂为 FRL / PRL / BERL / RRL / TRL，**数量与权重可由管理员配置**）打分，产出维度分 / 综合分 / 当前 Stage / 双方认知差（Perception Gap），与 Benchmarkit、Top GSV Quartile 两条外部基准对比；由 Goldie 生成差距分析与行动建议、**由 GSV 决定是否 Share 给 Founder 端**；题库与维度配置可由管理员自助维护；组合层提供跨公司 ERL 总表。

### 0.2 权威来源与冲突裁决

| 来源 | 地位 |
|------|------|
| `docs/Exit_Readiness_PRD.md` | **唯一权威**。任何与之冲突的原型行为、Lovable story 描述、v2.1 结论一律作废 |
| Lovable 原型 | 仅作 **UI 布局与交互参考**；其数据、计算口径、页面结构均不构成需求 |
| Lovable story 验收标准 | 参考。v2.1 曾以 story 为准补齐 A3，PRD §3.2 已给出正式定义，以 PRD 为准 |

**v2.1 → v3.0 修正清单**（每条注明 PRD 依据）：

| # | v2.1 的问题 | 类型 | PRD 依据 | v3.0 处理 |
|---|-------------|:---:|----------|-----------|
| 1 | 建了独立 `/exitReadiness` Dashboard 落地页（A1/A2） | **冲突** | §3.1「**不设独立 Exit Readiness 落地页**；ERL 卡片是唯一入口」 | **删除 Dashboard 路由**；A1/A2 合并为 Company Overview 页内的 **ERL Card**（§8.1） |
| 2 | 完全未提 DI 板块 | **缺失** | ~~§3.1「系统级隐藏原有 DI 卡片…」~~ → **v4.0 作废**：PRD 2026-09-02 改为「DI 卡片**放在 FI 卡片下**；DI 数据、打分**保留概览信息和入口**」 | ~~§8.6「DI 卡片下线方案」~~ → §8.6 改为 **「三卡排序方案」**（DI 不下线、不新增开关，§0.9-6） |
| 3 | `uk_erl_assessment (company_id, period, portal)` 唯一约束 | **冲突** | §3.3 / §3.9「同一季度允许多次提交，最新一次为 source of truth」「必须完整保留并清晰区分每一次单独提交」 | **去掉唯一约束**，改 `submission_seq` + `is_latest`（§5.2） |
| 4 | 答案表无「证据/备注」字段 | **缺失** | §3.3 / §3.4「每题：可选证据/备注（Evidence/Notes）文本」；§3.6 Goldie 输入源即为该备注 | `erl_assessment_answer.note`（§5.3） |
| 5 | 无文件/图片上传 | **缺失** | §3.3 / §3.4 / §4「可选文件上传，同步写入公司 Memory File，供 Goldie 分析」 | 新增 `erl_answer_attachment` 表 + §6.7 上传登记链路 |
| 6 | 维度分只有「题目平均」一种来源 | **冲突** | ~~§3.4 / §3.3「手动填写一个整体维度分 + 软确认弹窗」~~ → **v4.0 作废**（PRD 2026-09-02 两处同时删除）。现依据：§3.1「各维度分数：**回答问题时该维度最后一个全部 Yes 的 level 的 level 为此维度得分**」+ §3.3 打分格式 | `erl_assessment_dimension` 表**保留但换语义**：`manual_score` / `derived_score` / `divergence_*` 四列删除，改为 `level_score` + `terminated_level`（§5.3）；**维度分 = 逐级解锁推导，无任何手动录入**（§7.1 / §0.9-1、§0.9-3） |
| 7 | 明确排除「题目排序拖拽（无需求）」 | **冲突** | §3.8「**拖拽重排**：在 Era Band 内调整顺序，该顺序即评估中的**必答顺序**」 | 纳入 V1，新增 `PUT /erl/question/reorder`（§6.4） |
| 8 | 决定「不自动生成，前端显式触发」 | **冲突** | ~~§3.6「新评估提交后**自动刷新**分析，始终反映最新数据」~~ → **v4.4 依据作废**：PRD `49d9a29` 删去该条 | 改为**提交即置脏 + 自动重生成**（§7.5），保留手动 Regenerate。**v4.4：行为保留、依据改标「本设计」，并补「重生成 ⇒ `shared` 复位」边界**（§0.10-D19） |
| 9 | Goldie 单套 prompt / 单份产物 | **缺失** | ~~§3.6「Founder 与 GSV 均可见，但两者**展示口吻不同**」~~ → **v4.4 作废**：PRD `8324a3f` 删除该句，改为「GSV 团队均可见，可以点击 **Share 按钮**分享给 Founder 端」 | ~~`erl_gap_analysis.audience` + 双 prompt~~ → **v4.4 回到单份产物 + 单 prompt**（v2.1 的原判反而对了）：`audience` 列删除，可见性改由 `shared` 控制（§0.10-D3） |
| 10 | 明确排除「Data Sources & Cadence 卡」 | **冲突** | ~~§5「Data Sources & Cadence（按维度）」~~ → **v4.0 作废**：PRD 2026-09-02 删去该条 | ~~纳入 V1~~ → **移出 V1**（v2.1 的原判反而对了）：删 §7.6 推导规则、接口 2 的 `dataSources` 出参与 A3 该卡片（§0.9-9） |
| 11 | 明确排除「A6 BPMM 卡片」 | **冲突** | §3.1 卡片含 BPMM；§5「BPMM 分数仅作为参考数字（1–5）显示」 | **参考数字纳入 V1**（完整 BPMM 评估交互仍不做），数据来源见 §13-Q1 |
| 12 | 无「每维状态摘要」 | **缺失** | ~~§5「每维度状态摘要（基于 gap 幅度推导）」~~ → **v4.0 作废**：三值枚举于 2026-08-28 删去、整条展示项于 **2026-09-02 删去** | ~~新增 §7.4 判定规则~~ → **整块删除**（§7.4-①、`ErlDimensionStatusEnum`、卡片状态徽章全删，§0.9-9） |
| 13 | 打分格式仅按「题目级 answer_type」建模 | **缺失** | ~~§3.3 / §4「MVP 用 1–9 占位…保证未来切换不用重构」~~ → **v4.0 作废**：PRD 2026-09-02 把打分格式**直接定档**为 Yes/No + 固定顺序必答 + 逐级解锁 | ~~§7.2「计分策略可切换设计」~~ → §7.2 改为**「逐级解锁计分模型（已定档）」**：`answer_type` 双题型、`ErlScoringStrategy` 策略工厂、`scoring_mode` 快照列**全部删除**（§0.9-1） |
| 14 | 雷达图无图形规范 | **缺失** | §5「仅线条无填充、每线不同色、有图例、中心轴隐藏、悬停显示精确分、架构预留新增 perspective」 | 补入 §8.4。**v4.0 追加**：PRD 2026-09-02 补「该图**仅在 Portfolio 端显示**」→ 公司端 ERL Card 不渲染雷达图（§0.9-5） |
| 15 | F2 无排序筛选 | **缺失** | ~~§3.7「支持按分数、Stage、维度进行排序与筛选」~~ → **v4.4 依据作废**：PRD `57225d2`（2026-09-03）删去该条 | 补入 §6.5 / §8.4。**v4.4：功能保留、依据改标「本设计」**（§0.10-D15）。**v4.19：F2 的排序与筛选在界面上全部撤下**（原型两者都没有），服务端能力保留（§0.23-P2） |
| 16 | 维度页无「+ New」入口；GSV Tab 对公司端可见 | **冲突/缺失** | §3.2「『+ New』入口发起新一轮评估」「**公司用户不显示 GSV Tab**」「创始人不显示 GSV 专属字段（Benchmarkit、Top GSV Quartile 等）」 | 补入 §8.4，并收紧 §4.2 权限表 |
| 17 | 自创 A4「Score Details 全维明细页」（原型 `/readiness/overall`） | **无依据** | ~~PRD 全文无此页~~ → **v4.4：PRD 已明文写它**（§3.5 `Full View` + §3.7 `View`，`57225d2`） | ~~删除 A4~~ → **v3.5 复活**（2026-08-28 裁决 F2 `View` 跳全维 Score Details 页）→ **v4.4 扩为双端可达**：ERL Card 右上 `Full View` 是入口，每张维度卡各带 `Add New` + `View History`；§13-Q17「V1 不给公司端入口」的旧裁决**被 PRD 推翻**（§0.10-D5） |
| 18 | 自创 §8.5「在 Dashboard 维度行加 View Details」 | **已被 PRD 取代** | §3.1「卡片内提供每个维度的『View Details』入口」 | 入口改挂 ERL Card |
| 19 | §7.1「展示页维度分一律取 GSV 分」 | **需重述** | ~~§5「每维度 Founder 分与 GSV 分」~~ → **v4.0 改口**：PRD 2026-09-02（`74f25df`）改为「每维度 Founder 分**或** GSV 分（**根据账户权限**）」+「创始人：**只能查看自己的分数**」 | ~~并列展示双方分~~ → **按端裁剪**：管理端并列双方分，**公司端只见 Founder 分**（§0.9-4 / §4.2） |
| 20 | 把「维度分 = 题均分」写成已定口径 | **越权定稿** | ~~§5「初步为各题平均，最终待开发前确认」~~ → **v4.0 作废**：§3.1 / §3.3 已把维度分定档为 **level 口径**（PRD §5 残留的「各题平均」一句是**未同步的旧文**，见 §0.9-④ M1） | 题均分口径**整体删除**（连 `derived_score` 快照一起），维度分即 level 分（§7.1） |

**保留的 v2.1 结论**（PRD 未推翻，继续有效）：
- Java 为前端唯一出口 + Python 只做 LLM 生成，HTTP 经网关同步调用（§3）。
- Era 分段 `[1,4)` / `[4,7)` / `[7,9]`；原型 FRL 6.4 标 Exit Era 是原型 bug（§7.3）。
- ~~综合分 = 五维简单平均~~ → **v4.0 作废**：PRD §3.1 改为「按 weight configuration 页面配置的五个维度的**权重**算分」（§0.9-2 / §7.1）。等权（各 20%）时与简单平均等价，故原型的交叉验证不算被推翻，只是不再是唯一口径。**v4.4**：权重改为**按期次快照**（历史不随配置变动漂移，§0.10-R2），且维度数量本身可变（§0.10-D1）。
- Perception Gap = Founder − GSV（PRD §5 明确，一致）。**v4.0**：公式不变，但**公司端不再展示**（§0.9-4）。
- 不引入 SQS。（**v3.3**：「题目软删除」结论作废 —— 题库版本化后，草稿版本内直接物理删行，历史由版本快照保住，见 §0.5-2 / §5.1。**v4.0**：「题库**全局**单份」作废 —— PRD §4 改为「ERL 配置层级按照**租户**层级」，题库与权重按组织隔离，见 §0.9-7）

> **跨项目协作模式（本功能新增第三种）**：根 `CLAUDE.md` 现记录两种 Java↔Python 协作模式——智能解析走 SQS 异步、AI Chatbot 走 HTTP 经网关 + SSE 流式。ERL 差距分析是第三种：**HTTP 内网直连 + 同步非流式**（单次秒级调用）。<br>**2026-09-19 两处订正**（v4.59）：① ~~经网关~~ → **内网直连** —— 本仓库网关没有 `/api/ai/**` 路由，实际走 Nacos 配置项 `cio.erl.ai-base-url` 直连 `python:8090`（与存量财务预测的 `AI_MODEL_URL` 同款）；② ~~Java 落库缓存~~ → **Python 落库**（产物两张表已搬过去，§0.33-X1）。该模式**已补记进根 `CLAUDE.md`**。

### 0.3 v3.0 → v3.1 修正清单（基准模块 D，依据 2026-08-27 原型截图）

> 原型仍**仅作 UI 参考**；PRD §4 只规定「Benchmarkit / Top GSV Quartile 是外部静态数据、平台不计算」，**未规定录入粒度与页面结构**。原型给出的粒度（**按维度**）与 PRD §5「雷达图四条序列各覆盖五维」自洽 —— v3.0 的「每期两个总分」根本画不出这两条序列，因此以原型粒度为准。

| # | v3.0 的写法 | 类型 | 原型证据 | v3.1 处理 |
|---|-------------|:---:|----------|-----------|
| 1 | `erl_benchmark_record` 每条记录只有 `benchmarkit_score` / `top_quartile_score` 两个总分 | **粒度错误** | D2 页「Scores by dimension (1–9)」表格：五维 × 两列输入；D1 页「Latest by Dimension」卡逐维列值 | 拆为**主表 + 维度明细表**：`erl_benchmark_record`（期次 / 备注 / 录入人）+ `erl_benchmark_dimension`（五维 × 两个分），见 §5.6 |
| 2 | 雷达图 `BENCHMARKIT` / `TOP_GSV_QUARTILE` 序列的 `values[5]` 无数据来源（只有一个总分） | **自洽性缺陷** | 同上 | 两条序列取**适用记录的五维值**，见 §6.1 / §7.8 |
| 3 | D2「新增基准」是 Modal | **冲突** | 原型为独立页 `/readiness/benchmark/add`，含 `< Back`、页级标题与说明、底部 `Save Record` / `Cancel` | 改为独立路由页 `/exitReadiness/benchmark/add`（§8.1） |
| 4 | D1 页结构未定义 | **缺失** | 原型两张卡：`Latest by Dimension · {period}` 与 `Record History` | 补入 §8.4 交互表 |
| 5 | 记录表带 `+0.3 vs prior` 环比（v2.1 从旧原型反解，v3.0 沿用） | **无依据** | 新原型 D1 两张卡**均无环比列** | **删除 `deltaVsPrior`**（YAGNI；PRD 未要求，趋势对比由 Record History 逐期值体现） |
| 6 | 记录表列未定义 | **缺失** | `PERIOD`（最新条带 `LATEST` 徽章）/ `RECORDED` / `RECORDED BY`（姓名 + 角色）/ `BENCHMARKIT (AVG)` / `TOP GSV QUARTILE (AVG)` / `NOTE` / `ACTIONS`（`Details`） | 补入 §6.5 出参与 §8.4 |

> 本版**只动基准模块 D**，其余章节（A / B / C / E / F）的 v3.0 结论全部有效。

### 0.4 v3.1 → v3.2 修正清单（依据 2026-08-28 PRD 修订）

> ⚠️ **v3.6 补注**：本节处理的是 PRD 当日 **09:12 那次提交**（`200513c`）的 5 处修订，其中 1 处为纯措辞整理（§3.6 标题去掉「（原文更新）」），对设计无影响；其余 4 处逐条处理如下。**PRD 当日 10:24 还有第二次提交**（`4442613`，Founder 端手动维度分），v3.2 ~ v3.5 均未覆盖，**由 v3.6 补齐，见 §0.8**。

| # | PRD 变更（2026-08-28） | 类型 | v3.2 处理 | 影响章节 |
|---|------------------------|:---:|-----------|----------|
| 1 | §3.8 新增「**Publish 按钮：五个维度任意维度有新问题，按钮会被激活**」 | **新增需求** | ~~题库引入草稿 / 已发布两态，只有新增题需发布~~ —— **v3.3 已被需求方裁决取代，改为题库版本化、所有变更经发布**，见 §0.5 | §0.5 |
| 2 | §3.7 `View` 列由「跳转到该公司的 **Exit Readiness 页面**」改为「跳转到该公司的 **Score Details 页面**」 | **冲突（改口）** | F2 末列 `View →` 的目标由「Company Overview 锚点定位 ERL Card」改为该公司的**维度详情页（Score Details 模板，§0.2-17 已确立二者等价）**，默认落在 **FRL** 并带当前 `period`；面包屑首级仍回 Company Overview。~~**不新增全维明细页**（A4 仍不做）~~ → **v3.5 作废**：`View` 改跳 A4 全维页（§0.7-3） | §6.8 / §8.4 / §9 / §11-32 / §13-Q12 |
| 3 | §5「每维度状态摘要（**Met / Partial / Gap**，基于 gap 幅度推导）」删去括号内三值枚举 | **依据减弱** | 设计**不改实现**（仍需要一个状态摘要），但 `MET / PARTIAL / GAP` 三值由「PRD 明文」降级为**本设计占位枚举** —— 取值命名与阈值一并回填 §13-Q3，产品可整体替换。§0.2-12、§7.4-①、§8.5 的措辞同步订正 | §0.2-12 / §7.1 / §7.4 / §8.5 / §13-Q3 |
| 4 | §5 打分规则删去「（部分指标是 **0/1 二元**、部分为**光谱型**）」 | **依据减弱** | **不改设计** —— `answer_type ∈ {SCORE, YES_NO}` 的双题型建模来自 §3.3「MVP 用 1–9 占位、未来切 Yes/No + 固定顺序」与 §四「打分格式演进」，**不依赖被删的这句**；§7.2 补一行说明该表述已从 PRD 移除，避免后续被当作遗漏 | §7.2 |

> 本版**只动上述 4 处涉及的章节**，其余 v3.0 / v3.1 结论全部有效。

### 0.5 v3.2 → v3.3 修正清单（依据需求方 2026-08-28 对 §13-Q11 的裁决）

**裁决原文**：Q11 选「**所有变更都经发布，增加题库版本化**」；**不需要**撤回（已发布 → 草稿）与单维度发布。

> ⚠️ **该裁决与 PRD §3.8 现有原文冲突**：PRD 仍写着「变更**立即生效**到评估表与 Score Details 的题目列表中，无需其他配置步骤」。本设计以**裁决为准**（裁决晚于 PRD 且针对性回答了本问题），并建议 PRD §3.8 同步删去该句、补上发布语义 —— 见 §13-Q11 的「回写 PRD」一栏。

| # | v3.2 的写法 | 类型 | v3.3 处理 | 影响章节 |
|---|-------------|:---:|-----------|----------|
| 1 | 「只有**新增题**需要 Publish，编辑 / 删除 / 重排立即生效」 | **被裁决推翻** | **四类变更（新增 / 编辑 / 删除 / 重排）全部经 Publish 才对填报页与维度详情页生效**；配置页始终编辑草稿版本 | §7.9 全节重写 / §6.4 / §8.4 |
| 2 | `erl_question_config.publish_status` + `published_at` 两个状态位；删除用软删 `enabled` | **模型不够** | 状态位**放不下「编辑前后两份题干」** —— 改为**版本化**：新增 `erl_question_config_version` 版本表（第 10 张表），`erl_question_config` 挂 `version_id` + 跨版本稳定的 `question_key`；**删去 `publish_status` / `published_at` / `enabled` 三列**（草稿版本内物理删行，历史由版本快照保住） | §5.1 / §5.1.1 / §3.2 决策表 / §0.2 |
| 3 | 评估与题库无版本绑定 | **缺失** | `erl_assessment` 加 `question_version_id`（作答所依据的题库版本快照）。~~`erl_assessment_answer` 加 `question_key`~~ —— **v3.4 已删除**（其唯一用途是重基迁移，见 §0.6-3） | §5.2 |
| 4 | 发布后在填草稿只能整卷重载（答案丢失） | **不可接受** | ~~按 `question_key` 重基~~ —— **v3.4 已被需求方裁决取代，改为版本锁定（评估不跟随题库）**，见 §0.6 | §0.6 |
| 5 | 写接口按题目 `id` 定位（接口 11 / 12 / 13 / 14） | **契约缺陷** | 写时复制会让草稿行拿到**新 id**，前端手里的 id 属于已发布版本 → **写接口一律改按 `questionKey` 定位**（path 参数与 `reorder` 数组同步改） | §6.4 |
| 6 | Publish 按钮激活条件 = 「有新问题」 | **口径扩大** | 激活条件 = **存在草稿版本**（= 有任意未发布变更）。PRD 原文「五个维度任意维度有新问题」是该条件在「只有新增」场景下的特例，扩大后仍满足 | §6.4 / §8.4 |

**明确不做**（依裁决）：撤回（已发布 → 草稿）、单维度发布、定时发布、版本回滚与版本对比 UI（§12）。

### 0.6 v3.3 → v3.4 修正清单（依据需求方 2026-08-28 的第二次裁决）

**裁决原文**：「**保留旧答案，以正在编辑的版本为准** —— Founder 用 v3 版本打开就是 v3，GSV 用 v4 填。」

即：**评估在创建时绑定当时最新的已发布版本，此后不跟随题库变化**（版本锁定），v3.3 的「打开问卷时按 `question_key` 重基」整体作废。

| # | v3.3 的写法 | 类型 | v3.4 处理 | 影响章节 |
|---|-------------|:---:|-----------|----------|
| 1 | 打开在填评估时按 `question_key` 重基（答案迁移 / 新题留空 / 删题的答案丢弃 / 改题标 `changed`） | **被裁决取代** | **整体删除**，改为**版本锁定**：评估自始至终按 `question_version_id` 渲染与计分。§7.9-⑤ 由「重基」重写为「版本锁定」 | §7.9-⑤ / §6.3 / §9 / §10.1 / §11 |
| 2 | §7.9-①「填报页、维度详情页、计分、组合层、Goldie 输入一律只读**最新已发布版本**」 | **表述错误**（版本锁定下不成立） | 订正为：**只有「新发起一次评估」这一个动作**取最新已发布版本；已存在的评估（草稿 + 已提交）、维度详情页、计分、组合层、Goldie 输入**一律读该评估绑定的版本** | §7.9-① |
| 3 | `erl_assessment_answer.question_key`；唯一约束改为 `(assessment_id, question_key)` | **YAGNI** | **删除该列**，唯一约束**改回 `(assessment_id, question_id)`** —— 该列的唯一用途是重基时迁移答案，重基没了它就没有消费者（`question_key` 仍保留在 `erl_question_config`，版本 diff 与写接口定位需要） | §5.4 |
| 4 | 接口 5 前置校验 0「提交时绑定版本必须是最新已发布版本，否则 400」 | **必须删除** | 版本锁定下该校验会让旧版本草稿**永远提交不了**。删除该校验，**不阻止**按旧版本提交 | §6.3 / §9 |
| 5 | 接口 3 出参 `rebase{...}`、`ErlAssessmentRebaseService` | **随重基一起删** | 出参只保留 `questionVersionNo`（供页面标注题集版本） | §6.3 / §10.1 |

**本次裁决同时关闭的四条边界**（原 §13-Q13 ~ Q16，详见 §7.10）：

| 原问题 | 结论 |
|--------|------|
| Q13 题干被编辑后旧答案是否仍有效 | **问题消失** —— 在填的评估看不到新题干，答案与题面永远同版本自洽 |
| Q14 删题时已答内容如何处置 | **问题消失** —— 删除只落在新版本，旧版本评估里该题原样保留，**不再有任何用户数据丢失路径** |
| Q15 发布是否触发 Goldie 重生成 | **不触发**（从「设计选择」升级为「逻辑结论」）—— 分析的全部输入都锚在评估绑定的版本快照上，题库发新版后输入一字未变，无从触发 |
| Q16 同期次两端可否不同版本 | **允许**（裁决原文即取值）。后果是 Perception Gap 可能跨两套题集，接受；页面标注两端题集版本号 |

**版本锁定自身新增的三条边界**（已并入 §7.10）：**N1** 旧版本草稿可无限期停留、提交不阻止；**N2** 同期次多次提交可能跨版本，历史列表须标版本号否则像 bug；**N3** 不提供「升级到最新题集」按钮。

### 0.7 v3.4 → v3.5 修正清单（依据需求方 2026-08-28 的第三次裁决）

**裁决原文**：「ERL Tab `View` 的落地页，点击 View 跳转 A4 全维 Score Details 页」，UI 依据指定为原型路由 `/readiness/overall`（标题 `Score Details`）。

即：§13-Q12 的两个候选项中，需求方选了「**一页看全五维**」—— §0.2-17 / §1.2 / §12 三处「不做 A4」的结论作废。

| # | v3.4 的写法 | 类型 | v3.5 处理 | 影响章节 |
|---|-------------|:---:|-----------|----------|
| 1 | §0.2-17 / §1.2 / §12：「A4 全维 Score Details 页 PRD 无依据，不做」 | **被裁决取代** | **复活 A4**，纳入 V1 的 A 展示模块；§1.2 与 §12 的对应条目删除 | §0.2-17 / §1.1 / §1.2 / §12 |
| 2 | §8.1：「❌ `/exitReadiness/scoreDetails`（A4 全维明细）—— PRD 无此页」 | 同上 | **恢复该路由**（§8.1）；仍不复活 `/exitReadiness` Dashboard（PRD §3.1 明确不做，**与 A4 无关**） | §8.1 |
| 3 | F2 `detailUrl` = 维度详情页、默认维度 `FRL` | **被裁决取代** | 改为 **A4 全维页**：`/exitReadiness/scoreDetails?companyId={id}&period={period}`，**不再带默认维度** | §6.8 / §8.4 / §9 / §11-32 |
| 4 | 接口共 21 个（v3.0 的 1~20 + v3.3 的 #21 publish） | **新增需求** | 新增**接口 22** `GET /erl/scoreDetails`（一次返回五维全部题目），共 **22 个**（v3.5 原写「21 个」漏算 #21，v3.6 订正，§0.8-3） | §6.2.1 / §10.1 |
| 5 | §13-Q12「F2 `View` 落在哪个维度」 | ✅ **已裁决** | 关闭 Q12；新增 Q17（公司端入口）并**于同日确认**：**V1 不加公司端入口**，A4 的唯一入口就是 F2 `View` | §13 |

**Q17 同日确认**：需求方接受设计建议 —— **V1 不为公司端加 A4 入口**（ERL Card 已有逐维 `View Details`，PRD 未要求全维入口）。因此 A4 在 V1 的**唯一入口是 F2 ERL Tab 的 `View`**（管理端）；公司端仍保有本公司 A4 的后端权限（后续要开放入口时即可用），但界面上不提供入口。已并入 §12 的「明确不做」。

**UI 证据**：已发布站 `/readiness/overall` 的 chunk `readiness.overall-*.js`（2026-08-28 抓取，非截图）。页面结构为：**面包屑 → H1 `Score Details` + 右上 `+ New` → `Founder` / `GSV` 双 Tab + `View history` → 四列元数据栏 → 五张维度折叠卡（默认只展开第一张）→ 页尾基准折叠卡**。~~**四处有意偏离原型**见 §8.4 的「A4 与原型的四处有意偏离」行~~ → ⚠️ **2026-09-09 更新**（v4.20，§0.24）：① 本段记的是 **2026-08-28 那次 chunk 反解**的原型形态；A4 现行排版的依据已换成**同一路由 2026-09-09 的 SSR 实测 + 截图** —— **两级面包屑 → H1 `Score Details`（页头无分数）→ 维度横向 Tab + 末位基准 Tab → `GSV` / `Founder` 药丸**；② 有意偏离由**四处减为三处**，见 §8.4「A4 与原型的三处有意偏离」行。

> §0.2-17 当时判「无依据」并没有错 —— PRD 至今未定义该页；本次是**需求方直接裁决并指定原型为依据**，属新增需求。**待回写 PRD**：§3.7 的「View（跳转到该公司的 Score Details 页面）」需明确为「全维 Score Details 页」，并补上该页的内容清单（本设计 §8.4 已按原型给出）。⚠️ **v4.4 更新**：PRD `57225d2` 已补上该页的内容清单，本条基本闭环；剩余分歧见 §0.10-D5 与回写 M9。

### 0.8 v3.5 → v3.6 修正清单（依据 PRD 当日第二次提交 + 全文一致性复核）

**触发**：复核发现 PRD 在 2026-08-28 有**两次**提交，而 v3.2 的重校只覆盖了第一次：

| PRD 提交 | 时间 | 内容 | 被哪版设计消化 |
|----------|------|------|----------------|
| `200513c` | 09:12 | 5 处（0/1 二元表述、`Met/Partial/Gap` 三值、F2 `View` 目标、Publish 按钮、措辞整理） | v3.2（§0.4） |
| `4442613` | **10:24** | **§3.3 Founder Flow 追加「每维手动整体分 + 软确认弹窗」**；同时给出两处弹窗的英文原文 | **此前无 —— 本版补齐** |

**① 需求冲突（PRD 明文，必须改）**

| # | v3.5 的写法 | 类型 | PRD 依据 | v3.6 处理 | 影响章节 |
|---|-------------|:---:|----------|-----------|----------|
| 1 | 手动整体维度分**只有 GSV 端**填；Founder 维度分取题目平均 | **冲突** | §3.3（10:24 追加）「需为每个维度**手动填写一个整体维度分**。若该手动分与题目答案推导出的结果**不一致**，弹出软确认弹窗…仅需确认，不阻止提交」——与 §3.4 GSV 措辞完全一致；§3.1「各维度分数：**新增时手动填写的**」 | **手动分改为双端**：`manual_score` 两端均必填；提交前置校验与软确认弹窗去掉端限定；**Founder 维度分口径由「题均分」改为「手动分」**，题均分（`derived_score`）两端都退为软确认参照 | §1.1 / §3.2 / §5.3 / §6.3 / §7.1 / §7.1.1 / §7.4 / §8.4 / §9 / §11 |
| 2 | 软确认弹窗文案自拟（`Your manual score differs from the score derived from your answers.`） | **冲突** | §3.3 / §3.4 均给出原文 `Your score doesn't match the questionnaire answers, please confirm this is intentional` | **改用 PRD 原文**，前端不再自拟 | §8.4 |

> **§13-Q3b「口径不对称」由 PRD 自身关闭**：v3.0 ~ v3.5 记的疑问是「GSV 手动 / Founder 推导，Perception Gap 混合两种口径，是否要对称」，并给了两个可选方案。PRD 10:24 的修订**直接选了其中一个**——两端都手动填。Q3b 无需再问产品，标记为已关闭。

**② 内部不一致订正（不改需求，只对齐文档自身）**

| # | 问题 | v3.6 处理 | 位置 |
|---|------|-----------|------|
| 3 | 接口总数写「共 21 个」——v3.0 的 1~20 + v3.3 的 #21 publish + v3.5 的 #22，**实为 22 个** | 全文订正为 **22 个** | §0.7-4 / 附录 A |
| 4 | §8.1 配置页编辑路由仍是 `/configuration/edit/:id`，而 §6.4 已把 C 模块写接口全改为 `questionKey` 定位（§0.5-5）——按 `id` 进页面、回填接口要 `questionKey`，写时复制后必然失配 | 路由改 **`/configuration/edit/:questionKey`** | §8.1 |
| 5 | §6.7 链路第②步写「`POST /erl/assessment/draft` 带 `answers[].attachments[]`」，但 §6.3 接口 4 的入参清单里没有 `attachments` | 接口 4 入参**补上 `attachments`** | §6.3 |
| 6 | 接口 7 带可选 `dimension` 参数、§8.4 与 §11-8 都说「限定当前维度」，但 `records[]` 的 `answeredCount` / `totalCount` / `overallScore` **全是整卷口径**，"过滤"到底过滤什么没定义 | 定档：**记录条数不过滤**（评估是整卷提交），带 `dimension` 时把完成度与分数**换成该维度的值** | §6.3 / §8.4 / §11-8 |
| 7 | §7.9-⑤ 说不做「升级到最新题集」按钮、代价是「需重开一份评估」；但 §5.2 有同期次同端**唯一草稿**约束、且全设计无丢弃草稿接口 ⇒ 该补救路径实际不可达 | 定档补救路径：**先提交旧草稿再新建**（`submission_seq + 1`），并在 §7.10-N3 与 §12 写明这一代价 | §7.9-⑤ / §7.10-N3 / §12 |
| 8 | §7.4-① 状态摘要三条规则会**同时命中**（如 gap = 2.0 且双方同 Era：`PARTIAL` 的「同 Era」与 `GAP` 的「> 1.5」都成立） | 明确**按表格自上而下短路匹配**，首个命中即结果 | §7.4 |

**③ 此前留白，本版定档（不改结论，只把话说全）**

| # | 留白 | v3.6 定档 | 位置 |
|---|------|-----------|------|
| 9 | §8.6 新增全局配置项 `erl.enabled`，而 PRD §3.1 原文是「**使用现有** setting/toggle 能力」——属字面偏离，Q2 只提了公司级/系统级之争、没点这层 | 在 §8.6 与 §13-Q2 写明该偏离与理由 | §8.6 / §13-Q2 |
| 10 | `erl_assessment.fund` 标「仅 GSV 端」，而 PRD §3.3 要求 Founder 提交记录也含「基金/组合」 | `fund` 改为**双端都存**（公司所属基金快照） | §5.2 |
| 11 | PRD §3.2 的 `+ New` 是「发起**该维度**新一轮评估」，而设计的问卷是整卷 | ~~定档：问卷恒为整卷，`+ New` 带 `?anchor={dimension}` 锚定到该维度分组~~ → **v4.4 作废**：需求方 2026-09-06 裁决**提交粒度＝维度级**，PRD §3.2 的字面读法反而是对的；`+ New` 直接发起**该维度**的一次评估（§0.10-R1） | §8.4 |
| 12 | A4 作为 F2 的落地页只有逐题明细，无综合分 / Stage / Perception Gap，且不提供跳 A3 的入口 —— PM 从组合表点进来拿不到 Scorecard 视角 | ~~A4 页头**补综合分 `X/9` + Stage 徽章**（仍不重复 E2 / Data Sources / 雷达图）~~ → ❌ **2026-09-09 整条撤销**（v4.20，§0.24-Z2）：需求方裁决「严格照原型」，原型页头只有 H1 `Score Details` —— 加权 `Overall Score` 与 Era（Stage）徽章**整块删除**。整体判断改由 ERL Card 与 F2 该行承载（这两处的口径与「三处一致」的要求不变）；**接口 22 的 `header` 出参保留不动**，只是 A4 不再渲染它 | §6.2.1 / §8.4 / §8.5 / §0.24-Z2 |
| 13 | §5.1 `evidence_source` 示例写 `Founder / CFO`，PRD §3.3 原文是 `Founder/CTO` | ✅ **需求方 2026-08-28 裁决：`Founder / CFO` 正确，PRD 的 `Founder/CTO` 是输入错误** —— 设计**保持 `Founder / CFO` 不变**，反过来**回写 PRD**（§13-Q18） | §5.1 / §13-Q18 |

### 0.9 v3.6 → v4.0 修正清单（依据 PRD 2026-09-02 / 09-03 的 4 次修订）

**PRD 变更台账**（v3.6 的基线是 `4442613`，此后 PRD 又改了 4 次）：

| PRD 提交 | 时间 | 内容 | 影响级别 |
|----------|------|------|:---:|
| `621e857` | 2026-09-02 11:26 | **本轮主体**：打分格式定档为 Yes/No 逐级解锁；综合分改按权重；维度分改 level 口径；手动维度分与软确认弹窗（§3.3 / §3.4 两处）删除；DI 卡片改为放 FI 卡片下；雷达图仅 Portfolio 端；配置页新增五维权重设置；Publish 条件扩为「新问题 / 新顺序 / 新编辑」且明确「保存为新版本」；删「变更立即生效」；配置权限改「仅 portfolio portal」+「按租户层级」；Goldie 标题加「待定功能」；删除 §3.3 / §3.4 / §3.8 / §3.9 的全部 UX 要点；删除状态摘要 / Strengths & Priority Gaps / Data Sources & Cadence 三条展示项；每题标签改 `Era-level` | **结构性** |
| `a6b0906` | 2026-09-02 13:38 | 补「若 9 个层级都是 yes 回答，则最终得分为 9」 | 边界补齐 |
| `74f25df` | 2026-09-02 15:23 | Scorecard「每维度 Founder 分**与** GSV 分」→「Founder 分**或** GSV 分（根据账户权限）」；创始人「并列查看自己与 GSV 分数」→「**只能查看自己的分数**」 | **权限收紧** |
| `6d8c800` | 2026-09-03 11:01 | 每题附件补「**单个最大 10MB**」 | 约束补齐 |

> ✅ **顺带确认**：v3.6 产出的 PRD 回写建议里，**M1（§3.8 变更立即生效 → 草稿 + Publish 生效）与 M2（Publish 保存为新版本）已被 `621e857` 采纳** —— PRD 现文与本设计的题库版本化（§7.9）一致，`design-doc` 与 PRD 在这条上不再冲突。M3（`Founder/CTO` → `Founder / CFO`）尚未回写。

---

#### ① 需求冲突（PRD 明文，必须改设计）

| # | v3.6 的写法 | 类型 | PRD 依据（2026-09-02 起） | v4.0 处理 | 影响章节 |
|---|-------------|:---:|--------------------------|-----------|----------|
| **1** | **打分格式**：每题 `answer_type ∈ {SCORE, YES_NO}`；`SCORE` 题 1–9 分；维度分取**手动填写**的 `manual_score`，题均分 `derived_score` 用于软确认；计分策略做成可切换 Strategy（`SCORE_1_9` / 预留 `YES_NO_SEQUENTIAL`） | **推翻重做** | §3.3「全部问题包含 Era 和 level，为 **Yes/No + 固定顺序必答**模式（在 ERL configuration 中配置的顺序）」「某 level 全 Yes → 该 level 折叠并显示 Check → 再显示下一 level；直到有 No（或全部答完）就不再显示下一 level，激活提交按钮，**分数就是此回答为 No 的 level 减一**」；`a6b0906`「**9 个层级都是 yes → 得分 9**」；§3.1「各维度分数：回答问题时该维度**最后一个全部 Yes 的 level** 的 level 为此维度得分」；§3.4「可选择 yes/no」 | **计分模型换底**（详见 §7.2 全节重写）：<br>· `erl_question_config.answer_type` **删除**（全部题恒 Yes/No）<br>· `erl_assessment_answer.score` **删除**，只留 `yes_no`<br>· `erl_assessment.scoring_mode`、`ErlScoringStrategy` / `Score1To9Strategy` / `ErlScoringStrategyFactory` **全部删除**（PRD 已定档，占位抽象成了 YAGNI）<br>· 维度分 = **最后一个全 Yes 的 level**，**整数、值域 0–9**（level 1 即有 No → 0 分）<br>· 填报页改为**逐级解锁（progressive disclosure）** | §1.1 / §2.2 / §3.2 / §5.1 / §5.3 / §5.4 / §6.2 / §6.2.1 / §6.3 / §6.6 / §7.1 / §7.1.1 / §7.2 / §7.3 / §8.4 / §9 / §10.1 / §11 / §12 |
| **2** | 综合分 = 五维**简单平均** | **冲突** | §3.1「综合分数（Composite Score）: 按照 **weight configuration 页面配置的五个维度的权重**算分」；§3.8「管理 5 个维度的题库**和五维度在总分计算中的权重**」「五维度总权重 100%，当权重低于或高于 100% 时均不激活保存按钮」 | 综合分 = **Σ(维度分 × 权重%)**；新增**第 11 张表** `erl_dimension_weight`（§5.1.2）与**接口 23 / 24**（`GET` / `PUT /erl/weight`）；配置页新增 **C6 权重 Tab**，合计 ≠ 100% 时 Save 禁用 | §1.1 / §3.1 / §3.2 / §5.1.2 / §6.4 / §7.1 / §8.1 / §8.4 / §10.1 / §10.3 / §11 |
| **3** | **每维手动整体分 + 软确认弹窗**（v3.6 刚从「仅 GSV」扩为双端） | **整体删除** | §3.3 / §3.4 中该两条**同时被删除**（`621e857`）；维度分改由 level 推导（同 #1） | **v3.6 的核心结论作废**：`manual_score` / `derived_score` / `divergence_ack` / `divergence_delta` 四列删除；接口 4 / 5 的 `dimensionScores` / `divergenceAcks` 入参删除；提交前置校验 2、3 删除；§7.4-② 软确认阈值整节删除；B1/B2 的手动分输入与弹窗删除 | §0.8-1（自我作废）/ §3.2 / §5.3 / §6.3 / §7.1 / §7.4 / §8.4 / §9 / §11 / §13-Q3 |
| **4** | 公司端可见 GSV 维度分与 Perception Gap（v3.0 依 §5「并列查看」定的） | **权限收紧** | §3.5（`74f25df`）「每维度 Founder 分**或** GSV 分（根据账户权限）」「创始人（公司 portal）：**只能查看自己的分数**」 | **公司端不下发 GSV 分**：`gsvScore` 由服务端裁剪；**Perception Gap 亦不下发**（gap + 自己的分可反推对方分，给 gap 等于给分）→ **§4.2 权限表改写**，§13-Q8-① 的张力**由 PRD 自身关闭**（PRD 选了「不并列」这一边）。⚠️ 与 §3.1 卡片清单仍列 Perception Gap 存在**残留矛盾** → §13-Q20 + 回写 PRD | §4.2 / §4.3 / §6.1 / §6.2 / §7.1 / §8.4 / §8.5 / §9 / §11 / §13-Q8 |
| **5** | 雷达图在 ERL Card 内、两端均可见（公司端仅少两条基准线） | **冲突** | §3.5（`621e857`）「**该图仅在 Portfolio 端显示**」 | **公司端整个雷达图不渲染**、服务端 `radar` 字段整体不下发（不再是「裁剪掉两条基准序列」）。与 #4 自洽 —— 公司端看不到 GSV 线后，雷达图只剩一条自评线，本就无对比价值 | §1.1 / §4.2 / §6.1 / §8.4 / §8.5 / §9 / §11 |
| **6** | **A7 DI 卡片下线**：新增全局配置 `erl.enabled`，DI 区块渲染条件改 `DiStatus && !erlEnabled` | **推翻重做** | §3.1（`621e857`）「Company Overview 页原有的 DI 卡片**放在 FI 卡片下**；DI 数据、打分**保留概览信息和入口**」 | **A7 由「下线」改为「卡片重排」**：Company Overview 顺序 = **ERL Card（原 DI 位置）→ FI Card → DI Card**；DI 卡照旧按存量 `DiStatus` 显隐、入口与下钻全部保留。**新增配置项 `erl.enabled` 整体删除**（PRD 已不要求隐藏 DI）→ §13-Q2 **关闭**（那个「字面偏离」问题随需求变更消失） | §1.1 / §2.1 / §3.2 / §8.6 / §10.1 / §10.3 / §10.4 / §11-1 / §12 / §13-Q2 |
| **7** | 题库**全局单份**（版本序列亦全局单份），配置页「仅 admin」 | **作用域变更** | §3.8「管理员通过顶部导航右侧下拉菜单进入；**仅 portfolio portal**」；§4「**ERL 配置层级按照租户层级**」 | 题库版本与权重**按组织（租户）隔离**：`erl_question_config_version` / `erl_dimension_weight` 加 `organization_id`，「全局唯一草稿」「version_no 唯一」等约束**全部加组织前缀**；租户即平台既有 `organization_id`（JWT claim + `SecurityUtils.getOrganizationId()`，非新增概念）。§13-Q7-② 部分得到回答 | §0.2 / §3.2 / §4.1 / §4.2 / §5.1 / §5.1.1 / §5.1.2 / §6.4 / §7.9 / §10.1 / §11 / §13-Q7 |
| **8** | 附件：题级、无大小上限；「所有**题目**附件同步写入 Memory File」 | **约束补齐 + 粒度新增** | §3.3（`6d8c800`）「可上传附件（**单个最大 10MB**）」；§3.4「**每个维度均可提交附件**」；§4「**所有维度附件**同步写入公司 Memory File」 | ~~`erl_answer_attachment` → 改名 **`erl_assessment_attachment`**：`answer_id` 改为**可空**，新增 `assessment_id` + `dimension`，同时承载**题级**（Founder）与**维度级**（GSV）附件~~ → **v4.6 整条回退**（§0.12）：维度级附件取消，表名改回、`answer_id` 回 not null、`assessment_id` 删除（`dimension` 已于 v4.4 删除）；**保留**下来的只有 **10MB/个**前后端双校验 | §5.5 / §6.3 / §6.7 / §8.4 / §9 / §10.1 / §11 |
| **9** | 逐题标签为 Era 粒度（`Founder Era`） | **粒度变更** | §3.2「每题显示 **Era-level** 标签（如 `Founder Era-1`）与**得分**」 | `eraLabel` 口径改为 **`{Era 名} - {level}`**（如 `Founder Era - 1`），A3 / A4 / 填报页 / 配置页四处统一 | §2.2 / §6.2 / §8.4 / §11 |

#### ② PRD 删除的展示项 —— 随之处置

`621e857` 从 §3.5 删掉了三条展示项，并把 §3.3 / §3.4 / §3.8 / §3.9 的「UX 要点」整段删除。处理原则：**PRD 删掉的是「需求依据」，不等于自动删掉功能** —— 逐条判定该功能是否还有其他依据。

| # | 被删的 PRD 原文 | v4.0 处置 | 理由 |
|---|-----------------|-----------|------|
| 10 | §3.5「每维度**状态摘要**（基于 gap 幅度推导）」 | **删除该功能**：§7.4-① 判定表、`ErlDimensionStatusEnum`、接口 1 / 2 的 `status` 出参、卡片与维度页的状态徽章全删 | 该功能自 v3.2 起已是「设计占位」（三值枚举先被删），如今整条展示项也被删 ⇒ **零依据**。且它依赖 Perception Gap，而 gap 在公司端已不可见（#4），状态徽章两端语义不一致 |
| 11 | §3.5「**Strengths & Priority Gaps**：由证据/备注推导；如无笔记标注未提供备注」 | **功能保留，依据换到 §3.6**：E2 仍在 V1，但 PRD 依据由「§5 + §3.6」改为**仅 §3.6**（Goldie 产出的展示位）；「未提供备注」的标注一并挂 §3.6 | §3.6 仍完整保留 Goldie 产出 gaps / 建议行动、「无笔记标注」等要求，E2 只是它的渲染位置。⚠️ 但 §3.6 整块已被标「**待定功能**」→ 见 #12 |
| 12 | §3.6 标题改为「Gap Analysis 与 Suggested Actions（AI 辅助 / Goldie）**待定功能**」 | **E 模块（E1 + E2）整体标注为「PRD 待定」**：设计方案（§5.7 / §5.8 / §6.6 / §7.5 / §10.2）**原样保留、不删**，但在 §1.1 / §1.3 标明「**依赖 PRD §3.6 定稿**；若需求方确认 V1 不做，则 E1 / E2 / Python 侧全部产物可整块摘除，对 A / B / C / D / F 无影响」 | 「待定功能」是需求状态，不是删除。设计已把 E 做成**可整块摘除**的边界（Python 侧不落 ERL 表、Java 侧只多两张表 + 一个 client），保留成本低于返工成本 → §13-Q22 |
| 13 | §3.5「**Data Sources & Cadence**（按维度）」 | **删除该功能**：§7.6 整节、接口 2 的 `dataSources` 出参、A3 该卡片全删 | v2.1 原本明确排除该卡，v3.0 因 PRD §5 明文才纳入（§0.2-10）；依据消失 ⇒ 回到不做（YAGNI） |
| 14 | §3.3 / §3.4 UX 要点（Era 折叠分组、打分标度图例、「No 会中止后续计分」提示、备注视觉从属、附件轻量图标、~~自动保存无感~~（**v4.30 作废** —— 填报页已取消自动保存，§8.4「B 草稿落盘时机」）、提交确认告知）；§3.8 UX 要点（原型匹配、重排影响警告、admin 定位）；§3.9 UX 要点（可扫读、配色一致、突出 SOT） | **功能全部保留**，但 §8.4 交互表中这些行的「PRD 依据」列由 `§3.3 UX` 等改为 **`本设计（原 PRD UX 要点已于 2026-09-02 删除）`** | 这些是 UI 决策，删掉依据不等于要改交互；但**必须标明来源变化**，否则后续复核会误判为「设计凭空加料」。其中**「打分标度图例」改为「level 进度指示」**（1–9 分标度已不存在，§0.9-1） |

#### ③ 本版定档的新边界（PRD 未写，实现必须有确定取值）

| # | 边界 | v4.0 定档 | 若取反面 | 状态 |
|---|------|-----------|----------|:---:|
| 15 | **解锁是按维度独立、还是五维全局同步？** PRD「五个维度的所有问题按照 Era 和等级依次显示」像全局，但「**该维度**最后一个全部 Yes 的 level」是维度独立的 | **按维度独立解锁**：每个维度各自从 level 1 推进到自己的终止 level | 全局同步 ⇒ 任一维度先出现 No 就会卡住其余四维、让它们拿不到本可得的分数，与「每维度独立得分」直接矛盾 | ✅ **v4.4 关闭（§13-Q19）**：需求方 2026-09-06 裁决**提交粒度＝维度级**，一次提交只涉一个维度，「全局同步」这个读法连讨论前提都没有了（§0.10-R1） |
| 16 | **提交按钮的激活条件** | ~~**五个维度全部到达终止态**且所有已解锁题已作答~~ → **v4.4 改为「本维度到达终止态**（出现至少一个 No，或到达该维最大有题 level 全 Yes）**且本维已解锁题全部作答」**（§0.10-R1） | 沿用「五维全终止」⇒ 与维度级提交自相矛盾，且让单维提交永远无法成立 | 定档（v4.4 换底） |
| 17 | **`Completion` 的分母**（PRD §3.9 示例 `45/45`） | `answeredCount / totalCount`（**该题集版本全部题数**），并在旁以次级文字标注各维终止 level | 分母取「已解锁题数」⇒ 恒等于分子、永远显示 `n/n`，该列失去信息量 | ⚠️ **v4.4：`Completion` 列已被 PRD `8f2fcc0` 从历史列表中删除**（§0.10-D12）。分母口径**保留为实现说明**，`answeredCount` / `totalCount` 降为页头用途；原挂该列的 `v{n}` / `stopped at L{t}` 次级标注**挪到分数列下方** |
| 18 | **维度分为 0 时的 Era / Stage** | `score = 0`（level 1 就有 No）→ **Stage `0`、Era 显示 `—`**（未达 Stage 1），不归入 Founder Era | 强行归 Founder Era ⇒ 与「Founder Era = Stage 1–3」冲突 | 定档（§7.3） |
| 19 | **权重是否随题库版本化 / 是否在评估上快照** | ~~**不版本化、不快照**，综合分实时按当前权重算~~ → **v4.4 推翻**：需求方 2026-09-06 选了「历史不漂移」。**维度集合与权重整体版本化**，期次首次创建评估时绑定配置版本、此后永不跟随（§0.10-R2 / §5.1.2 ~ §5.1.4 / §7.11） | 沿用实时算 ⇒ 今天调权重、去年 Q1 的综合分与 Stage 也跟着变，历史不可比 | ✅ **v4.4 定档，§13-Q21 关闭**（取值：改权重**不影响**历史期次） |
| 20 | **维度题库为空 / 该维无任何已发布题时的维度分** | `score = null`，**不按 0 计入综合分**；权重按剩余维度**归一化**后算综合分，并在综合分旁标注口径 | 按 0 计 ⇒ 题库尚未配全时综合分被系统性拉低 | 定档（§7.1 / §9） |
| 21 | **每题的三段式评分标准**（`criteria_founder` / `criteria_harvest` / `criteria_exit`） | **合并为单列 `criteria`**：每题现在恒属于**一个** level（`era_band` 1–9），「同一题在三个 Era 下各有一套标准」的模型已不成立；A5「How It's Scored?」弹窗改为展示**该题的判定标准 + 所属 `Era-level`** | 保留三段 ⇒ 配置页要为每题填三套永远只用到一套的文案 | 定档（§5.1 / §8.4）；原三段来自原型，PRD §3.8 只要求「题干 / Era Band / Source」。→ **2026-09-06 裁决整体删除**：合并后的单列 `criteria` 与 A5 弹窗一并撤除（v4.9，§0.15） |
| **22** | **level 分布是稀疏的**（某维度可能只配了 level 3/6/9，或最高只到 L8） | 状态机遍历**实际存在的 level 升序列表**而非 1→9 计数器；~~**得分 = 出现 No 的 level − 1**（与更低 level 有无题目无关，PRL 在 L3 答 No → **2 分**）~~ → **v4.37 作废（需求方 2026-09-15 裁决）**：得分 = **最后一个「整级全部 Yes」通关的 level**（= 踩 No 那一级在该维有题 level 升序列表里的**前一个**），一级都没通关即 **`0`** ⇒ PRL 在 L3（它的首个有题 level）答 No → **`0` 分**，不再是 2 分；**全通关 = 该维最大有题 level**（RRL 全 Yes → **8 分**，不是 9） | 按 1→9 递增 ⇒ PRL 卡在「L1 无题、既非全 Yes 也非含 No」的**死锁**；封顶写死 9 ⇒ RRL 全通关也拿不到满分却显示 9 | **定档（§7.2-①）**。依据：2026-09-03 原型反解出的真实分布（§2.3.1-③）+ PRD §3.3 原文「分数就是此回答为 No 的 Level 减一」。⚠️ v4.0 初稿的状态机写错了，本条是修正。⚠️ **v4.37 只废「得分 = 出现 No 的 level − 1」这半条** —— 「**遍历实际存在的 level 升序列表**」与「**全通关 = 该维最大有题 level**」两半条**原样有效**，别一起读成失效 |

#### ④ 需回写 PRD（本版新增，与 v3.6 的遗留项合并）

| # | PRD 位置 | 问题 | 建议改法 |
|---|----------|------|----------|
| **M1** | §3.5 评分与计算第 1 条 | 「每个维度分数：由该维度内各题分数计算得出（**具体计算方法**：初步为各题平均）」—— 与 §3.1 / §3.3 已定档的 **level 口径直接冲突**，且「各题平均」在全 Yes/No 题型下无意义 | 改为：「每个维度分数 = 该维度**最后一个整级全部 Yes 通关的 level**（0–9 整数）；某 level 中出现任一 No 即终止，得分为**该维已通关的最后一个 level**（= 有题 level 升序列表里踩 No 那一级的前一个，一级都没通关则为 0）；9 个 level 全 Yes 则为 9。」（**v4.37 订正**：原建议写的「得分为该 level − 1」照抄 PRD §3.3，该口径已被 2026-09-15 裁决推翻 ⇒ 回写 PRD 时须**连同 §3.3 原文「分数就是此回答为 No 的 Level 减一」一并改掉**，否则 PRD 内两处互相打架） |
| **M2** | §3.5 评分与计算第 2 条 | 「**综合 ERL 分数 = 5 个维度分数的简单平均**」—— 与 §3.1「按 weight configuration 配置的权重算分」冲突（同一份 PRD 内两种口径） | 改为：「综合 ERL 分数 = 五个维度分数按 **ERL Configuration 中配置的权重**加权求和（权重合计 100%），以 X/9 形式显示。」 |
| **M3** | §五 TBD 第 2、3 条 | 「打分格式最终形态（1–9 vs Yes/No + 固定顺序）及 "No" 中断后的精确计分逻辑」「每维度分数的具体计算方法（是否为题均分）」—— **两条均已在 §3.3 / §3.1 定档**，留在 TBD 里会让开发以为还没定 | **删除这两条 TBD**（对应 §13-Q3、Q5 关闭） |
| **M4** | §3.1 卡片内容清单 | 清单列「Perception Gap：Founder 和 GSV 每个维度的分数差」，而 §3.5 已规定「创始人只能查看自己的分数」—— 创始人若能看到 gap，即可反推 GSV 分 | 在该条后补：「（**Perception Gap 仅 portfolio 端可见**；公司端卡片不展示 GSV 分与 Perception Gap）」——或明确「公司端可见 gap」，二者择一（→ §13-Q20） |
| **M5** | §3.3 来源标签 | `Founder/CTO` 应为 `Founder / CFO`（2026-08-28 已裁决，**至今未回写**） | §3.3「每题显示来源标签（Founder/CTO、Looking Glass、SharePoint 等）」中的 `Founder/CTO` 改为 `Founder / CFO`（→ §0.10-④ M7） |
| **M6** | §3.8 权重设置 | 「该页面包含一个五维度总分 weight 的设置」未说明**权重的作用范围与生效方式**：是否随 Publish 生效？改权重是否影响历史期次的综合分？ | ~~补「保存后立即对所有期次生效」~~ → **v4.4 改法**：「维度配置（增删 / 排序 / 权重）独立保存、不随题库 Publish；**保存即生成新配置版本，从下一个尚未开始填报的期次起生效；已有提交的期次沿用其绑定的版本，历史分数与雷达图不变**。」 |

> **v4.4 复核（`49d9a29` 时点）**：M1 / M2 / M3 / M5 **至今未被 PRD 采纳，原样有效**，已并入 §0.10-④ 重列；**M4 部分闭环** —— PRD `57225d2` 已在 §3.5 加了「Perception Gap（仅 Portfolio portal）」，但 **§3.1 的卡片内容清单仍未加端限定**，故该条降级为「照 §3.5 补 §3.1 的括注」继续挂账（§0.10-④ M10）；**M6 的建议改法已按 §0.10-R2 重写**（见上）。

---

### 0.10 v4.3 → v4.4 修正清单（依据 PRD 2026-09-03 / 09-04 的 9 次修订 + 需求方 2026-09-06 三条裁决）

**PRD 变更台账**（v4.0 ~ v4.3 的基线都是 `6d8c800`；此后 PRD 又改了 9 次，而 v4.1 / v4.2 / v4.3 是**原型驱动的 UI 订正**，并没有消化这 9 次）：

| PRD 提交 | 时间 | 内容 | 影响级别 |
|----------|------|------|:---:|
| `57225d2` | 2026-09-03 15:29 | 综合分改名 `Overall Score`；§3.1 删「面包屑」UX 要点；**§3.5 新增 `Perception Gap（仅 Portfolio portal）` 与 `Full View（仅 Company portal）`**；§3.7 **删除「按分数 / Stage / 维度排序与筛选」**、补 Score Details 页说明；Gap 粒度定为按维度；删「Harvest Era 约 6 可接触投行」注解 | **结构性** |
| `8f2fcc0` | 2026-09-03 15:34 | **§3.9 历史列表字段重写**：Portal 列标注「(Portfolio 端)」、新增 `Submitted`、**删除 `Completion`**、`Overall Score` → 「**维度** Overall Score」、详情改为「该次**本维度**提交的详情」 | 中 |
| `9a203ce` | 2026-09-03 16:33 | §3.5 新增「Benchmarkit 与 Top GSV Quartile 输入和历史记录：**在雷达图下方的链接**」 | 小（入口位置） |
| `0333162` | 2026-09-04 11:17 | **§3.8 配置页结构重写**：由「题库五维 Tab + 权重设置」改为「**维度题库 tab + Dimension Configuration tab**」，后者可**新增 / 删除维度、维度排序、修改占比**，维度列表写作 `FRL / PRL / BERL / RRL / TRL...`（省略号＝不固定五个）；Save 双条件 | **结构性（本轮最大）** |
| `08b7a32` | 2026-09-04 15:28 | §3.3 顶部按钮组 `Save as draft / Cancel / Reset / Submit`；新增「操作流程说明」四条（草稿进入 / 重复提交确认 / 草稿公司共享且覆盖 / 提交人以最终提交者为准） | 中 |
| `8324a3f` | 2026-09-04 15:35 | **§3.6 标题删去「待定功能」⇒ Goldie 回归 V1**；输入源改为「题目 gap / 备注」（删 Workbook 准入准则）；新增「数据来源：**closed month 所在季度**的评价」（§3.1 同步）；权限改为「GSV 可见 + **Share 给 Founder**」，删「双口吻」 | **结构性** |
| `4f959bb` | 2026-09-04 15:37 | §3.3 草稿补「若题库已更新，则**提示**题库更新，不做强制退出和更新」 | 小（但推翻旧承诺） |
| `273671a` | 2026-09-04 16:07 | §3.6 **删除「已知 TBD 与 MVP 备选方案」整段**（含 prompt 未定义、GSV vs Founder 对比 Tab、Fireflies / SharePoint 扩展） | 依据消失 |
| `49d9a29` | 2026-09-04 17:46 | §3.6 补「绿点 / 灰点」与「**View details** 弹框（No Gap / 未提交）」；删「自动刷新分析」「双方分数均高时承认为优势」「指导性非强制」「展示位置」 | 中 |

---

#### ① 需求方 2026-09-06 裁决（R 类，本版的定盘星）

| # | 裁决 | 落点 | 关闭的旧问题 |
|---|------|------|------|
| **R1** | **提交粒度 = 维度级** —— 一次提交＝某公司某期次某端的**单个维度** | `erl_assessment` 加 `dimension` 列，唯一约束与两条部分唯一索引全部加 `dimension`；`erl_assessment_dimension` **整表删除**（维度级后恒一行，三列上提）；提交校验由「五维全终止」改为「**本维终止**」；`question_version_id` 绑定粒度变每维一份（同期次各维可绑不同题库版本，系统不阻止、不告警）；Assessment History 与 Score Details 要求的「每维 Add New / View History」由此天然成立 | **§13-Q19 关闭**（逐级解锁按维度独立）；**§13-Q23 缓解**（单维终止即可提交） |
| **R2** | ~~**维度只停用不硬删**（v4.8 作废改物理删除）**+ 维度集合与权重整体版本化**：新增 3 张表；每个期次首次创建评估时绑定当时的配置版本、此后永不跟随 ⇒ 历史期次永不漂移~~ → **2026-09-08 整条反转**：① `erl_dimension_config_version` 与 `erl_company_period_config` **两张表均已删除**（§5.1.2 / §5.1.4），维度配置降为单表 `erl_dimension_config` 的**当前值**（§5.1.3）；② **无期次绑定**，任何期次一律读当前 `Active` 集合；③ **「历史永不漂移」正式失效**（改权重 / 增删维度会回溯改变历史期次的综合分与 Stage），**§13-Q21 重新打开**；④ 「删除维度」~~物理删除（v4.8）~~ → **软删**（`status = 'Inactive'` 落库） | 需求方 2026-09-06 裁决 → **2026-09-08 再裁决** | §5.1.2（墅碋）/ §5.1.3 / §5.1.4（墅碋）/ §7.1 / §7.10-W1 / §7.11（整节重写）/ §10.1 / §11-77 / §12 / §13-Q21 |
| **R3** | **展示期次缺省 = closed month 所在季度；该季两端均无提交 → 空态，不回退** | 接口 1 / 17 / 20 / 22 的 `period` 缺省由 ~~最新已提交期次~~ 改为 closed month 所在季度；closed month **沿用 Financial Intelligence 域既有口径**（按公司 Manual / Automatic 推导，来自 Financial Entry actuals），ERL **复用 FI 既有服务、不自己算**；~~closed month 取不到（无任何 actuals）→ 同样空态 + WARN，不回退~~ → **v4.33 作废（2026-09-15 裁决）：closed month 取不到时回退当前自然季度（UTC），WARN 保留**。⚠️ **被推翻的只有这半条** —— 「该季两端均无提交 → 空态、不回退到更早期次」**原样有效** | 新增 **ERL → FI 的跨域依赖**（原设计对 FI 零依赖），见 §3 / §7.1.2 / §9 / §10.1。⚠️ **v4.19：F2（接口 20）成为本条的显式例外** —— 前端固定传 `period = 当前自然季度`，本条缺省口径对接口 1 / 17 / 22 仍然有效（§0.23-P1） |

> **R1 与 R3 的交互（易错点）**：维度级提交后，「该季有没有提交」要**按维度分别判定** —— ERL Card 的 Gap 区块正是靠这个逐维状态渲染绿 / 灰点（D4）。**整卡空态只在该期次一个维度都没提交时出现**；只要有一个维度提交过，卡片就要正常渲染，未提交的维度按空值展示。

---

#### ② 需求冲突与新增（D1 ~ D14，PRD 明文，必须改设计）

| # | v4.3 的写法 | 类型 | PRD 依据 | v4.4 处理 | 影响章节 |
|---|-------------|:---:|----------|-----------|----------|
| **D1** | **五维是硬假设**：`ErlDimensionEnum` 编译期枚举、「恒五行」「固定返回五项」「按五维固定顺序」、F2 出参硬编码 `frl / prl / berl / rrl / trl` 五列、前端 `constants.ts` 静态 `DIMENSIONS` 映射 | **推翻重做** | §3.8（`0333162`）「可以新增、删除维度，为维度排序，修改维度的占比。新增删除或排序后，对应的页面应回显，如 overview 页面、雷达图、题库页面」；维度列表写作 `FRL / PRL / BERL / RRL / TRL...` | **维度全面参数化**：枚举与静态映射删除、改**接口驱动**；F2 出参改动态数组 `dimensionScores: [{ code, abbr, score }]`，表格列与 `sortBy` 白名单随之动态化；雷达图顶点数、A3 维度 chip、A4 / C7 维度卡、Gap 状态点数量全部按接口返回的维度列表渲染；综合分的「剩余维度归一化」逻辑保留但基数「五」参数化 | §1.1 / §2.2 / §2.3.1 / §5.1 ~ §5.1.4 / §6.1 ~ §6.8 / §7.1 / §7.11 / §8.1 ~ §8.4 / §10.1 / §10.3 / §11 / §12 / §13-Q24 |
| **D2** | E 模块（Goldie）全文 26+ 处标「PRD 已标待定功能 / 本节整体可摘除 / 待定期间隐藏 / `gapSummary` 恒 null / `strengths` 恒空数组 / 验收组仅在确认后执行」 | **状态反转** | §3.6 标题（`8324a3f`）**删去「待定功能」四字** ⇒ 回归 V1 | **全部条件语删除**，E1 / E2 状态列改 ✅，验收组去掉前置条件。历史台账性质的行（v4.0 变更说明⑩、§0.9-12）**保留事实**并补注「已于 `8324a3f` 撤销」 | §1.1 / §1.3 / §4.2 / §5 / §5.7 / §5.8 / §6.1 / §6.2 / §6.6 / §6.7 / §7.5 / §8.2 / §8.4 / §8.5 / §9 / §10.1 / §10.2 / §11 / §12 / §13-Q22 / 附录 B |
| **D3** | **双 audience 模型**：`erl_gap_analysis.audience`（FOUNDER / GSV）、唯一约束含 audience、一次 LLM 出两套口吻、两份 prompt 文件、Founder 端**直接可见** | **推翻重做** | §3.6（`8324a3f`）「权限：**GSV 团队均可见，可以点击 Share 按钮分享给 Founder 端**」；`49d9a29`「**只有所有维度两方都完成时，share 按钮才被激活**」 | **降为单份产物 + 单 prompt**：`audience` 列删除、唯一约束回 `(company_id, period)`、两份 prompt 合并、删「前端不做措辞转换」与「双 audience 回归测试」「两端口吻不同」验收；**新增 `shared` / `shared_at` / `shared_by` 三列**；**新增接口 27** `POST /erl/gapAnalysis/share`（仅管理端）；公司端读接口 17 时 `shared = false` **直接返回空态**（§4.3 补强制校验）；**激活门槛**＝该期次**每个维度**的 FOUNDER 与 GSV 都有 `is_latest` 的 `SUBMITTED` 记录 | §3.2 / §4.2 / §4.3 / §5.7 / §6.1 / §6.6 / §7.5 / §8.4 / §8.5 / §9 / §10.2 / §11 |
| **D4** | Gap 区块只有「summary 截断 + View details 跳 A3」，且含 Strengths 展示 | **UI 定档 + 展示项删除** | §3.6（`49d9a29`）绿 / 灰点、`View details` 弹框（No Gap / 未提交）、「有 gap 的展示建议，没有的不展示」；**2026-09-06 ERL Card 截图** | 按截图定档：标题 `Gap Analysis & Suggested Actions` + `AI GENERATED` 标签；按钮 **`View details`**（弹框，按维度分区）与 **`Share to founder`**（门槛未达成置灰）；期次 chip；计数文案 **`{n} of {total} dimensions have gap analysis for {period}`**；每维小卡三态（绿点 `Gap analysis ready` / 绿点 `No Gap` / 灰点 `Not submitted`）；底部提示 **`Share unlocks once gap analysis is available for all {total} dimensions in {period}.`**。接口 17 出参补 `dimensions[].{code, abbr, bothSubmitted, hasGap}`。**`item_type` 的 `STRENGTH` 枚举值、出参 `strengths[]`、prompt 中「双方分数均高时承认为优势」一段全部删除**。<br>⚠️ **易错点**：**圆点颜色 = 双方是否都已提交；文字 = 有无 gap**，两条独立信息，不要混成一个枚举（截图里 TRL 就是「绿点 + `No Gap`」） | §5.8 / §6.1 / §6.6 / §8.4 / §8.5 / §9 / §10.2 / §11 |
| **D5** | §4.2「A4 公司端 **V1 无任何界面入口**」；§8.1.1「**不要**在 ERL Card 或主导航自行加链接」；§12「不做 A4 的公司端入口」；A4 的 `+ New` / `View history` 是**页级**且不带 `dimension` | **旧裁决被推翻** | §3.5（`57225d2`）「**Full View（仅 Company portal）**：点击进入 Score details 页面…**每个维度**包括一个 Add New 按钮和一个 View History 链接」；§3.7 同款说明（含「GSV 和 Founder 的记录」） | **三处禁令一并撤销**，§13-Q17 标「已被 PRD `57225d2` 推翻」；**ERL Card 右上 `Full View ›` 为入口**，按 2026-09-06 截图**两端都渲染**（PRD 的「仅 Company portal」与原型不符 → 回写 M9）；**A4 每张维度卡卡头各加 `Add New`（带 `?dimension={code}`）+ `View History`（带 `?dimension={code}`）**，原页级入口取消；~~组合端 A4 需同屏呈现 GSV 与 Founder~~ → ❌ **2026-09-09 作废**（v4.20，§0.24-Z5）：改回 **`GSV` / `Founder` 药丸切换**（`GSV` 在前且默认选中，原型口径）—— PRD §3.7「同时呈现两端记录」仍然满足，因为**一次取回双端数据 + 本地切片**（接口 22 契约与请求次数均不变），只是不再同屏并列；「A4 上不加跳 A3 的入口（YAGNI）」的判断**撤回** | §4.2 / §6.2.1 / §8.1.1 / §8.4 / §8.5 / §11 / §12 / §13-Q17 |
| **D6** | 期次缺省＝「最新已提交期次」 | **冲突** | §3.1 / §3.6（`8324a3f`）「数据来源：**closed month 所在季度**的评价」 | 见 **R3**；新增 §7.1.2「展示期次的确定」 | §3 / §6.1 / §6.6 / §6.8 / §7.1.2 / §9 / §10.1 / §11 |
| **D7** | §8.1.1 声称基准页入口在「维度详情页 / A4 页内链接」，但 §8.4 交互表里 A3 / A4 **从未定义过该链接** —— 按现文档实现，`/exitReadiness/benchmark` 站内不可达 | **冲突 + 既有文档缺口** | §3.5（`9a203ce`）「Benchmarkit 与 Top GSV Quartile 输入和历史记录：**在雷达图下方的链接**，点击进入可以看历史记录和新增记录」 | ERL Card **雷达图正下方**加链接 `Benchmarkit & Top GSV Quartile ›` → `/exitReadiness/benchmark?companyId=`，**仅管理端渲染**（与雷达图同条件）；订正 §8.1.1 的入口描述。D1 / D2 双卡内容本就满足「看历史 + 新增」，页面不改 | §6.5 / §8.1.1 / §8.4 / §11 |
| **D8** | 填报页只有 1.5s 去抖自动保存 + 吸底提交条；**无 Cancel / Reset**；§13-Q23 记「V1 没有任何摆脱旧草稿的办法」 | **缺失（需新接口）** | §3.3（`08b7a32`）「有 **Save as draft、Cancel、Reset、submit** 按钮」 | 顶部按钮组定档：`Save as draft` = 手动 flush（~~与自动保存并存、不互斥~~ → **v4.30 作废：自动保存取消，接口 4 只由 `Save as draft` / `Submit` 两个按钮触发**）；`Cancel` = 离开页面、不做数据操作；**`Reset` 走新增接口 28** `DELETE /erl/assessment/draft`（清空本次草稿的答案与附件、`unlocked_level` 回到 1），二次确认写明附件一并删除。接口 28 同时是 Q23 的解法 ⇒ **§13-Q23 关闭** | §6.3 / §7.7 / §8.3 / §8.4 / §10.1 / §10.3 / §11 / §12 / §13-Q23 |
| **D9** | 草稿共享语义只在模型上成立（唯一索引不含用户维度），文档未写明；接口 3 **不返回**最后保存时间与保存人 | **缺失** | §3.3（`08b7a32`）「显示上次保存时间和保存人」「草稿为**公司共享，不区分账户**」「若之前有其他草稿，则**直接覆盖**」「问卷提交人**以最终提交者为准**」 | 接口 3 出参补 `lastSavedAt` + `lastSavedBy`（姓名 + 角色，取 `updated_at` / `updated_by` join 用户表，**不新增快照列**）；§5.2 / §7.7 显式写明「A 保存后 B 打开看到的是 A 的内容，B 的保存直接覆盖」与「即使草稿由他人保存，提交人只记录点提交的那个人」；草稿提示条带出保存人姓名 | §5.2 / §6.3 / §7.7 / §8.4 / §11 |
| **D10** | §9 明文承诺「在填期间题库发布了新版 → 填报页**无任何提示、无任何变化**」（§7.10-N1 / N3 同调） | **半冲突** | §3.3（`4f959bb`）「若题库已更新，则**提示**题库更新，**不做强制退出和更新**」 | **版本锁定本体不变**（不强制更新、不退出），**冲突只在「无任何提示」这一句**：接口 3 出参补 `latestPublishedVersionNo` + `hasNewerQuestionSet`；~~填报页顶部挂**非阻断、可关闭、无操作按钮**的 banner `The question library has been updated (v{n}). This assessment continues on v{m}.`~~ → **2026-09-15 需求方圈图作废，改为强阻断二选一弹窗**（`Submit draft content` / `Access new question library`，v4.41 回写，形态与两颗按钮的语义见 §8.4）；同步订正 §9 与 §7.9-⑤ / §7.10-N1 / N3 | §6.3 / §7.9 / §7.10 / §8.4 / §9 / §11 |
| **D11** | 提交确认弹窗只有一套文案 | **缺失（纯 UI 分支）** | §3.3（`08b7a32`）「若之前已提交该季度评价，则弹出提示：**已提交该季度评价，是否再次提交？**」 | 拆两种：首次提交沿用现文案；该期次该端**该维度** `submissionCount > 0` 时改用 PRD 原话，并补「本次提交将成为该季度的 source of truth，历史提交保留」。数据侧 `submissionCount` 已有 | §8.4 / §11 |
| **D12** | B3 历史列表列 = Period / Portal / Submitted By / **Completion** / Overall Score；接口 8 无 `dimension` 入参；详情「复用 A3 整卷题级布局」 | **冲突（多处）** | §3.9（`8f2fcc0`） | **删 `Completion` 列**（次级标注 `v{n}` / `stopped at L{t}` **挪到分数列下方**，`answeredCount` / `totalCount` 降为页头用途，§7.1.1 的分母论证保留为实现说明）；**补 `Submitted`（提交时间）列**；**`Portal` 列仅管理端渲染**；分数列改「**维度 Overall Score**（`{level}/9` 整数 + 该维 Era 徽章）」，**不是加权综合分**；**接口 8 补可选 `dimension` 入参**，从带维度的历史列表进入时只渲染该维度 | §6.3 / §7.1.1 / §8.4 / §11 |
| **D13** | 配置页第二 Tab 为 `Dimension Weights`，**只管权重**；Save 仅按「合计 ≠ 100% 禁用」 | **命名 + 职责变更** | §3.8（`0333162`） | Tab 改名 **`Dimension Configuration`**，职责扩为「维度**新增 / 删除 / 排序 / 权重**」；**接口 23** 语义扩为 `GET /erl/dimension/config`、**接口 24** 扩为 `PUT /erl/dimension/config`（整组保存，校验「维度集合合法 + 权重合计恰为 100.00」，保存即生成新配置版本）；**Save 双条件**＝脏态 + 合计 100%；Save 确认框文案由 ~~「权重立即生效，并会改变所有历史期次的综合分与 Stage」~~ 改为「**新配置从下一个尚未开始填报的期次起生效；已有提交的期次沿用其绑定的配置版本，历史分数不变**」（R2）；`Dimension Configuration` 的改动**不激活 Publish**，走自己的 Save。**v4.8 面板改版**：新增栏（`Dimension name` + `Abbreviation` + `+ Add`）上移至面板头下一行、列表由表格改为**卡片行**（拖拽手柄 + `Name (ABBR)` + 权重输入 + 铅笔进入行内编辑 + ~~垃圾桶删除并二次确认~~ → **2026-09-09：行尾图标改为「`deletable` ? 垃圾桶 : 电源按钮」，两者都要二次确认**，§0.21 / §8.4-C6）、**`code` 列撤下不再显示**、行内 `Save` / `Cancel` **只本地提交该行、不调接口**（§0.14 / §8.4-C6） | §1.1 / §2.3.1 / §4.2 / §5.1.2 ~ §5.1.4 / §6.4 / §7.11 / §8.1 / §8.2 / §8.4 / §10.1 / §10.3 / §11 |
| **D14** | 文中并存 `Composite Score` 与 `Overall Score` 两种叫法 | **文案定档** | §3.1（`57225d2`）改名为「综合分数（**Overall Score**）」 | 英文 UI 文案统一为 **`Overall Score`**；§0.9-2 等处引用 PRD 旧文的地方一并订正 | §0.9 / §6.1 / §8.4 |

---

#### ③ PRD 删除依据的处置（D15 ~ D22）

沿用 §0.9-② 已建立的体例：**PRD 删掉的是「需求依据」，不等于自动删掉功能** —— 逐条判定并**标明来源变化**，不得沉默不处理（否则后续复核会误判为「设计凭空加料」，或开发照旧文漏做）。

| # | 被删的 PRD 原文 | v4.4 处置 | 理由 |
|---|-----------------|-----------|------|
| **D15** | §3.7「支持按分数、Stage、维度进行**排序与筛选**」（`57225d2`） | **功能保留**；§1.1 / §6.8 / §8.2 / §8.4 / §11 中直接引用「PRD §3.7」的依据全部改标 **「本设计（PRD 2026-09-03 已删除该条依据）」** | 组合层跨公司总表没有排序筛选就没法用；删依据不等于删功能，但必须标明来源变化。⚠️ **v4.19 在界面层面整条推翻**：F2 顶部的 Stage 与分数区间筛选器、以及全部列头排序器**一并按原型撤下**，F2 成为纯展示表；接口 20 的 `sortBy` / `sortOrder` / `stage` / `minScore` / `maxScore` 入参与服务端实现保留不删（§0.23-P2） |
| **D16** | §3.9 `Completion（如 "45/45"）` | **列删除**（见 D12），分母口径论证保留为实现说明 | PRD 给的是「列表**最少**字段」清单，删掉即不再是必需列；但它承载的 `v{n}` / `stopped at L{t}` 是逐级解锁与版本锁定的可解释性来源，故只挪位、不丢弃 |
| **D17** | §3.1 UX 要点「从维度页返回时保留面包屑 Exit Readiness ›〔Dimension Name〕」（`57225d2`） | **功能保留**，§8.4 A3 面包屑行的依据列由「§3.1 / §4」改为「**§4**（§3.1 的 UX 要点已于 2026-09-03 删除）」 | §四「导航一致性」仍保留同一条要求 ⇒ 依据未消失，只是换了出处。**PRD 自身矛盾**（§3.1 删、§四 留）→ 回写 M6 |
| **D18** | §3.6 输入源「ERL Workbook 中各 Stage / 维度的准入准则」（`8324a3f`） | ~~`criteria` 入参**保留字段**~~，但删除全部「即 PRD §3.6 的 Workbook 准入准则」这类引用，改标 **「设计自创；题库配置只采集『题干 / Era Band / Source』，本字段无处产生 → §13-Q25」** → **2026-09-06 裁决整体删除**：字段、A5 弹窗与 Goldie 入参一并撤除，§13-Q25 关闭（v4.9，§0.15） | 这是 `criteria` 的**最后一个 PRD 锚点**。它本就不在 §3.8 的题目字段里（§0.9-21 已自认「原三段来自原型」），依据消失后必须显式挂账，否则实现时会发现「prompt 要吃的字段没人填」—— **v4.9 的裁决正是从这条挂账里长出来的** |
| **D19** | §3.6「新评估提交后**自动刷新**分析，始终反映最新数据」（`49d9a29`） | §7.5 的「置脏 + `AfterCommit` + 异步重生成 + 重试 + Redis 去重」**作为实现手段保留**，依据改标「本设计」；**并补 D3 带出的新边界** | 行为本身合理（否则用户要手点 Regenerate）。但叠加 Share 后出现 PRD 与设计都没定义的场景：**GSV 已 Share → Founder 又提交 → 分析被自动重写 → Founder 侧内容在无人操作下变了**。**v4.4 定档：重生成后 `shared` 复位为 `false`，需 GSV 重新 Share**，管理端提示「内容已更新，需重新分享」 |
| **D20** | §3.6「建议为**指导性**非强制」「说明『可以做什么』以及『**为何相关**』」「MVP 不含正式跟踪、指派、Deadline」 | `actions[{ title, why }]` 的 `why` 字段**保留**为设计选择；「不做跟踪 / 指派 / Deadline」结论**保留**，理由由「PRD §3.6 明确 MVP 不含」改为「**PRD 未要求**」 | 结论不变，只是不能再引用一段已经不存在的原文 |
| **D21** | §3.6「已知 TBD 与 MVP 备选方案」整段（`273671a`），含「GSV vs Founder 对比 Tab」「Fireflies / SharePoint 扩展」「Gap 粒度待定」 | 结论均不变（本就不做 / 本就按维度），依据改标「PRD 未要求」；**§13-Q6 关闭** —— ①对比 Tab：PRD 已删该备选；②gap 粒度：§3.6「View details…**分为五个维度**」已明确＝**按维度**，与本设计一致 | 备选方案段落被删＝需求方不再考虑该替代路径 |
| **D22** | §一「Harvest & Growth Era：Stage 4–6（**分数约 6 表示公司进入该纪元，可开始接触投行**）」（`57225d2`） | §2.3 引用该注解处订正为「（PRD 2026-09-03 已删除该注解）」 | 纯引文陈旧，不影响 Era 分段规则（§7.3 不变） |

---

#### ④ 需回写 PRD（v4.4 清单，含 v4.0 未闭环的遗留项）

| # | PRD 位置 | 问题 | 建议改法 |
|---|----------|------|----------|
| **M1** | §3.5 评分与计算第 1 条 | 「维度分＝各题平均」与 §3.1 / §3.3 已定档的 level 口径**直接冲突**，且「各题平均」在全 Yes/No 题型下无意义（v4.0 已提，**至今未采纳**） | 「每个维度分数 = 该维度**最后一个整级全部 Yes 通关的 level**（0–9 整数）；某 level 中出现任一 No 即终止，得分为**该维已通关的最后一个 level**（= 有题 level 升序列表里踩 No 那一级的前一个，一级都没通关则为 0）；全部 level 均为 Yes 则取该维最大有题 level。」（**v4.37 订正**：原建议的「得分为该 level − 1」已被需求方 2026-09-15 裁决推翻，回写 PRD 时 §3.3 原文「分数就是此回答为 No 的 Level 减一」须一并改） |
| **M2** | §3.5 评分与计算第 2 条 | 「综合 ERL 分数＝5 个维度分数的**简单平均**」与 §3.1「按权重算分」冲突（同一份 PRD 内两种口径，**至今未采纳**） | 「综合 ERL 分数 = 各维度分数按 **ERL Configuration 中配置的权重**加权求和（权重合计 100%），以 X/9 形式显示。」 |
| **M3** | §五 TBD 第 2、3、5、6 条 | 四条**均已被正文定档**（打分格式 / 维度分算法 / 对比 Tab / gap 粒度），留在 TBD 里会让开发以为还没定 | **删除这四条** |
| **M4** | §五 TBD 第 1 条 | 「ERL 卡片上 Gap Analysis 呈现方案 与 BPMM 内容/规则」—— Gap 呈现已由 §3.6（`49d9a29`）定档 | **拆分，只保留 BPMM** |
| **M5** | §五 TBD 第 8 条 | 「Configuration 中题目顺序变更对进行中 / 历史评估解释的处理策略」—— 已由 2026-08-28「版本锁定」裁决关闭 | **删除**，或改写为「已按版本锁定处理，见设计 §7.9-⑤」 |
| **M6** | §四 vs §3.1 | §3.1 的「面包屑」UX 要点已于 `57225d2` 删除，而 §四「导航一致性：Exit Readiness ›〔Dimension Name〕」仍保留 —— **PRD 自身矛盾** | 二选一：恢复 §3.1 那句，或在 §四 注明「面包屑规则统一见 §四，各功能节不再重复」 |
| **M7** | §3.3 来源标签 | `Founder/CTO` 应为 `Founder / CFO`（2026-08-28 已裁决，**至今未回写**） | 改为 `Founder / CFO` |
| **M8** | §3.3 打分格式第 2 条 | 「**五个维度的所有问题**按照 Era 和等级依次显示」与「每个维度一个 Add New」「该次**本维度**提交的详情」（＝维度级提交）**矛盾** | 「填报按**维度**进行，一次填报只覆盖一个维度；该维度内的问题按 Era 与 level 依次显示。」 |
| **M9** | §3.5 | 「**Full View（仅 Company portal）**」与 2026-09-06 原型不符 —— 截图里组合端的卡片同样有 `Full View`（同一张卡上还有 `Share to founder`） | 删去端限定：「**Full View**：两端均可从 ERL Card 右上进入 Score Details 页」 |
| **M10** | §3.1 卡片内容清单 | 仍列「Perception Gap：Founder 和 GSV 每个维度的分数差」而**无端限定**，与 §3.5「创始人只能查看自己的分数」冲突（创始人有 gap + 自己的分即可反推 GSV 分）。原 §0.9-④ M4，**仍未闭环** | 照 §3.5 补括注：「（**Perception Gap 仅 portfolio 端可见**）」 |
| ~~**M11**~~ | §3.8 题目字段 | ✅ **v4.9 关闭（需求方 2026-09-06 裁决，§0.15）—— 取「从 Goldie 输入中移除」这一支，PRD §3.8 无需改动**。**原问题存档**：题库只采集「题干 / Era Band / Source」，而 Goldie 的 prompt 依赖每题的判定标准（`criteria`）—— **该字段无处产生**（→ §13-Q25） | ~~二选一：在配置页题目表单中增加「判定标准」字段；或明确 Goldie 只吃「Yes/No 差 + 备注」，从输入中移除~~ → **已选后者**：`criteria` 整列删除、A5 弹窗删除、Goldie 输入收敛为「题干 + 逐题 Yes/No + 双端备注 + level 口径」。**本条无需回写 PRD**，回写清单收敛为 M1 ~ M10 + M12 + M13 |
| **M12** | §3.8 Dimension Configuration | 未说明**维度删除 / 删除对历史期次的影响**，也未说明配置的生效时点 | 「**维度删除后不再进入新期次的问卷与展示**；**已有提交的期次沿用其绑定的配置版本，历史分数、Stage 与雷达图不变**。维度配置保存后从下一个尚未开始填报的期次起生效。」（**v4.8**：删除即物理删除，历史安全由期次-版本绑定保证） |
| **M13（v4.6 新增，两处必改）** | §3.4「每个维度均可提交附件」+ §4「所有**维度**附件同步写入公司 Memory File」 | 需求方 2026-09-06 裁决**附件双端统一题级**，维度级附件取消 —— 这两句（均为 PRD `621e857` 于 2026-09-02 写入，其中 §4 那句是把原文的「题目」改成了「维度」）与本版设计**直接冲突**，不回写就会留下两套口径 | §3.4：删去「每个维度均可提交附件」，改为与 §3.3 同款的**每题字段**子项「可选『证据/备注』文本、**可上传附件（单个最大 10MB）**」；§4：把「所有**维度**附件」改回「所有**题目**附件同步写入公司 Memory File，供 Goldie 分析使用」 |

---

#### ⑤ §13 待确认事项的状态变化

| 编号 | v4.4 新状态 |
|---|---|
| **Q6** | ✅ **关闭**（D21）：对比 Tab 的 PRD 备选已删；gap 粒度已明确为按维度 |
| **Q17** | ❌ **旧裁决被推翻**（D5）：PRD `57225d2` 明确公司端经 `Full View` 进入 A4 |
| **Q19** | ✅ **关闭**（R1）：维度级提交 ⇒ 逐级解锁按维度独立 |
| **Q20** | ✅ **关闭**：PRD §3.5「创始人只能查看自己的分数」已定，设计按「公司端不给 gap」实现；仅剩 §3.1 卡片清单待回写（M10） |
| **Q21** | ✅ **关闭**（R2）：维度与权重按期次快照，改配置**不影响**历史 |
| **Q22** | ✅ **关闭**（D2）：PRD 删「待定功能」⇒ Goldie 进 V1 |
| **Q23** | ✅ **关闭**（D8 + R1）：接口 28 提供丢弃草稿，且单维终止即可提交 |
| **Q24（新）** | ~~🟡 非阻塞~~ → ✅ **v4.8 关闭**（需求方 2026-09-07）：**不区分 `Delete` 与 `Retire`，只有 `Delete`，且无条件允许物理删除**（历史安全由期次-版本绑定保证，不需要软删这层）；`erl_dimension_config_item.status` 整列删除（§0.14） |
| **Q25（新）** | ~~🟡 非阻塞~~ → ✅ **v4.9 关闭**（需求方 2026-09-06 裁决）：**从 Goldie 输入中移除** —— `criteria` 整列删除、A5「How It's Scored?」弹窗整块删除、prompt 收敛为「题干 + 逐题 Yes/No + 双端备注 + level 口径」；**回写项 M11 随之关闭**（§0.15） |

> **v4.0 立的「五个必须先答的问题」（Q19 / Q20 / Q21 / Q22 / Q23）在本版全部关闭**；新增的 Q24 / Q25 均为**非阻塞**项，不挡开发启动（**Q24 已于 v4.8 关闭**，§0.14；**Q25 已于 v4.9 关闭**，§0.15 —— 两条现均已定案）。

---

### 0.11 v4.4 → v4.5 修正清单（依据需求方 2026-09-06 追加要求：版本表补 `is_latest`）—— ⚠️ **本节 L1 / L3 / L5 / L6 已于 2026-09-09 整体作废**

> ⚠️ **本节已失效，仅留档**（2026-09-09）：`is_latest` 这条路走完了一整圈 —— L2 的 `erl_dimension_config_version` 于 2026-09-08 随表删除；L1 的 `erl_question_config_version.is_latest` 于 **2026-09-09 删列**（连带 L3 的部分唯一索引、L5 的取数路径、L6 的种子标记一并回退）。判据回到本节想取代的那个「隐式推算」：**`status = 'PUBLISHED'` 中 `version_no` 最大的那一条**。
>
> **为什么回退是对的**（§5.1.1）：`version_no` 在组织内本就有唯一索引，草稿号恒为 `max + 1`，所以那条「隐式规则」其实是**天然唯一、无需兜底索引**的；标记列换来的只是 SQL 直查可读性，代价是每次 Publish 都要写两行版本头 —— 而那次多写正是「发布改写上一版最后编辑人 / 时间」这条债的成因。**L4 的「标记转移必须原子」随之无对象**。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| ~~**L1**~~ | ❌ **2026-09-09 作废（删列）** —— `erl_question_config_version` **+ `is_latest`**（boolean，not null，默认 `false`）：标识该行是否为**当前正在使用的最新版本**。口径 = 本组织 `status = 'PUBLISHED'` 中最新的那一版；**`DRAFT` 行恒为 `false`**（草稿「在改、未生效」，不是在用的版本），被取代的旧发布版本置 `false` | 「哪一版在用」原先只能靠 `status = 'PUBLISHED'` + `version_no` 倒排**推算**，读的人得知道这条隐式规则；改为**表上自解释的标记列**，SQL 直查即可看出在用版本 | §5.1.1 / §7.9-① |
| ~~**L2**~~ | ❌ **2026-09-08 作废（整表删除）** —— `erl_dimension_config_version` **+ `is_latest`**（同上）：标识**当前生效版本**。本表无状态位，`is_latest = true` 的那条恒为 `version_no` 最大的一条 | 同 L1；且「当前生效版本」在 §5.1.4 的空态回退、§7.11-③ 的期次绑定里被反复引用，值得一个显式落点 | §5.1.2 / §5.1.4 / §7.11 |
| ~~**L3**~~ | ❌ **2026-09-09 作废（两个索引都已不存在）** —— 两表各加一个**部分唯一索引**：`uk_erl_question_config_version_latest` / `uk_erl_dimension_config_version_latest`，`ON (organization_id) WHERE is_latest` —— **同一组织内至多一条 `true`**。建库脚本的部分唯一索引由 3 个增至 **5 个** | 「正在使用的版本只有一个」是本列的全部意义，靠代码自觉守不住；并发 Publish / Save 时由索引兜底 | §5.1.1 / §5.1.2 / §10.1 |
| ~~**L4**~~ | ❌ **2026-09-09 作废（两个标记列都已不存在，无标记可转移）** —— **标记的转移在同一事务内完成**：Publish（接口 21）把上一条 `true` 的已发布版本置 `false`、本版置 `true`；Save（接口 24）把上一条 `true` 的配置版本置 `false`、新版本置 `true`。**旧版本的题目行 / item 行仍然永不改写**（只翻版本头上的标记位） | 两步写必须原子，否则中途失败会出现「零个在用版本」或「两个在用版本」 | §6.4 / §7.9-② / §7.11-② |
| ~~**L5**~~ | ❌ **2026-09-09 作废（改回按 `version_no` 倒排）** —— 取数路径改走标记列：`findFirstByStatusAndOrganizationIdOrderByVersionNoDesc(PUBLISHED, org)` → 按 `organization_id + is_latest` 命中；维度配置的 `findFirstByOrganizationIdOrderByVersionNoDesc` 同理。**按 `version_no` 倒排的查询保留**，仍用于版本历史列表与算 `version_no = max + 1` | 语义与索引都更直接；`idx_erl_question_config_version_status` / `idx_erl_dimension_config_version` 因此降级为「版本序列」用途，不再是取在用版本的主路径 | §5.1.1 / §5.1.2 / §10.1 |
| ~~**L6**~~ | ❌ **2026-09-09 作废（种子不再落该列）** —— **种子数据补标记**：题库 `version_no = 1` 的 `PUBLISHED` 行、维度配置 `version_no = 1` 的行，一律 `is_latest = true` | 漏标会让系统起来后「无在用版本」—— 填报页全空、维度配置读空态，与漏建版本行的后果相同 | §10.1 |

> **不变的部分**（避免过度解读）：`is_latest` **不进任何接口出参**（配置页显示的仍是 `Published v3` / `Draft v4`，靠 `status` + `version_no`）、**不进前端**、**不改变版本绑定语义**（评估仍锚在 `erl_assessment.question_version_id`、期次仍锚在 `erl_company_period_config`，§7.9 / §7.11）。它只是「当前在用版本」这一事实的**显式落点**，取代原先的隐式推算。

---

### 0.12 v4.5 → v4.6 修正清单（依据需求方 2026-09-06 追加裁决：附件双端统一题级）

> **裁决原文口径**：附件回到 `erl_answer_attachment`，**Founder 端 / GSV 端统一使用题级附件**。
> 这条推翻的是 v4.0 依 PRD `621e857` 落下的「GSV 维度级附件」，**不是**设计自创的东西 —— 故本节
> 同时给出 PRD 回写项 **M13**（§0.10-④），否则设计与 PRD 会长期反向冲突。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **A1** | **维度级附件整体取消**：GSV 端不再有「每个维度提交附件」这一挡，两端**一律逐题挂附件**，10MB/个上限、直传通道、入知识库链路一字不变 | 维度级附件在 PRD 里只有 §3.4 一句 12 字、无入口位置/数量/上限的任何补充说明；而两端问卷本就是同一套题、同一套解锁规则，附件却分两种粒度，导致同一份证据在两端落在不同层级、A4 双端并列时对不齐 | §1.1-B2 / §5.5 / §6.3 / §6.7 / §8.4-B / §11 |
| **A2** | 表名 `erl_assessment_attachment` **改回 `erl_answer_attachment`**；`answer_id` **收紧回 not null**；**`assessment_id` 列删除** | v4.0 改名的**唯一理由**是「它已不只挂在答案上」，该前提随 A1 消失；`assessment_id` 是「维度级附件没有作答可挂」时的 owner 列，粒度归一后与 `erl_assessment_answer.assessment_id` 完全重复。代价只有一处：接口 19 的删附件鉴权由「附件 → 评估」一跳变「附件 → 作答 → 评估」两跳 | §3.1 / §3.2 / §5 表清单 / §5.5 / §9 / §10.1 |
| **A3** | 接口 4 / 5 **删入参 `dimensionAttachments`**；接口 3 **删顶层出参 `attachments`**；接口 19 路径**不变** | 入参/出参里的维度级通道随 A1 一并撤除；接口 19 按附件主键定位，与粒度无关，改路径只会白白破坏契约 | §6.3 / §6.7 |
| **A4** | 前端删 `DimensionAttachmentPanel` 组件与 B2 的 `Dimension evidence` 区块；**题级上传入口两端都渲染** | v4.0 的「前端按 PRD 各渲染各自的入口」随 A1 作废 —— 现在两端渲染完全一致，端区分只留在权限与数据归属上 | §8.2 / §8.4 |
| **A5** | 索引 `idx_erl_attachment_assessment` 随列删除；`idx_erl_attachment_answer` 与按 `file_id` 的回写索引保留 | 「按维度 / 按一次提交取附件」改走「先取该评估的作答、再 `findByErlAssessmentAnswerIdIn`」—— 那本就是填报页、维度页、A4 的既有主路径，不是新增查询 | §5.5 / §10.1 |
| **A6** | **§11-18b 作废**，新增 **§11-89**；§11-69 的 14 项删除清单**撤销 `erl_answer_attachment` 那一项**（它现在是正确表名，不能再作为「应当不存在」的检索目标） | 不改的话验收清单会自相矛盾：一边要求表名叫 `erl_answer_attachment`，一边要求全仓检索确认它不存在 | §11 / 附录 B |
| **A7** | **PRD 回写 M13**（两处）：§3.4 删「每个维度均可提交附件」、改为与 §3.3 同款的每题字段；§4 把「所有**维度**附件」改回「所有**题目**附件」 | PRD §4 那句原本就写作「题目附件」，是 `621e857` 连同 §3.4 一起改成「维度」的；A1 等于把这两处一并回退 | §0.10-④ / §5.5 / §6.7 |

> **不变的部分**：10MB 双侧校验、直传通道与 `fileBusinessType = KNOWLEDGE_BASE`、异步入库与
> `ingest_status` 三态、失败不阻断提交、改答回收与 Reset 一并删附件、**已入知识库的文件不回删知识库
> 条目**（§7.10-W3）、~~`file_size`~~ / `registry_id` / `ingest_status` 三列 —— 这些都与粒度无关，一律沿用
> （**2026-09-09 例外**：`file_size` 连同 `file_name` 已删列，改按 `file_id` 查 `files`，§5.5 —— 与 v4.6 的粒度调整无关，是后续独立裁决）。

### 0.13 v4.6 → v4.7 修正清单（依据需求方 2026-09-07 追加要求：super 可替租户配置）

> **要求原文口径**：ERL Configuration 页给 super 角色加租户下拉，选中哪个租户就为其做配置；
> Portfolio Group Manager 不显示该下拉。参照实现为 `/settings` 的 Portfolio User Management。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **B1** | **C 模块 11 个接口（9-14 / 21 / 23 / 24 / 25 / 26）新增可选 query 参数 `organizationId`**（POST / PUT 也走 query，**不进 Request 体**）；缺省即登录态组织 | 一个 super 管理多个租户，原「组织只能取自登录态」意味着换租户就得换账号登录。走 query 而不塞 Request 体，是为了 11 个接口一个口径、且现有 Request VO / Converter 零改动 | §4.3 / §6.4 |
| **B2** | **ACL：传入的组织必须是调用者自身组织或其组织树下的子孙组织**，否则 `BadRequestException("You do not have access to this organization.")`；`assertAdminEnd()` 前置不变 | 「接受入参」不等于「谁都能改谁」——租户边界改由服务端按**组织树**复核（`OrganizationService.findByTree` 拍平，不碰 system 域 repository），与前端下拉能选到的集合是同一份数据，天然对齐 | §4.3 |
| **B3** | 组织**显式参数化**透传：`ErlAccessService.resolveOrganizationId(...)` 为唯一入口，`ErlQuestionConfigVersionService` / `ErlQuestionConfigService` / `ErlDimensionConfigService` 的 C 模块方法各加一个 `organizationId` 形参；`currentPublished()` / `versionOf()` / `weightsOf()` / `bindPeriod()` 等**公司端与计分链路方法签名与语义一律不动** | 不用 ThreadLocal / 请求上下文夹带租户：C 模块之外的调用方传 `null` 即旧行为，一眼可查谁在切租户 | §4.3 / §10.1 |
| **B4** | 前端配置页右上角新增租户下拉，**隐藏规则与 `/settings` 一致**（组织树根节点无 `subdata` 即隐藏）；选中的 `organizationId` 随 URL query 传给 `add` / `edit` / `history` 三个子页 | 子页是独立路由，不带租户就会把题写进登录态组织的草稿 —— 那是最难发现的一类串租户错误 | §8.4 |

> **不变的部分**：表结构（两张版本表的 `organization_id` 早已存在）、组织内 `version_no` 唯一与
> 部分唯一索引、写时复制与 Publish 流程、维度配置保存即生效、管理端门禁、计分口径 —— 本版只改
> 「目标组织从哪来」，不改「拿到组织之后做什么」。

### 0.14 v4.7 → v4.8 修正清单（依据需求方 2026-09-07 追加裁决：维度删除即物理删除 + C6 布局改版）

> **裁决原文口径**：配置页上删掉一行维度，保存后该维度**就不在新生成的配置版本里** —— 没有 `ACTIVE` / `RETIRED` 这层**存储**状态。
> **历史仍然不漂移**，但靠的是 `erl_company_period_config` 的**期次-版本绑定**（**R2 的核心机制不变**），与状态位无关：
> 历史期次绑的是旧版本，旧版本里那一行原样还在，照常渲染。同时按新原型改 C6 的面板布局。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **P1** | **`erl_dimension_config_item.status` 整列删除**：维度配置项不再有 `ACTIVE` / `RETIRED` 存储状态 | 这一列存在的**唯一理由**是「删掉的维度还得给历史期次看」；而 R2 落地后历史期次读的本来就是**旧版本的 item 行**，那一行从未被改写 —— 状态位没有保护对象，只是一份需要被处处 `WHERE status = 'ACTIVE'` 记着的冗余 | §5.1.3 / §5.1.4 / §7.11 / §10.1 |
| **P2** | **「删除维度 = Retire 软删」口径作废，改为物理删除**：配置页删掉一行，右上角 `Save` 后该维度就不在新配置版本的 item 里 | 同 P1。软删还有一处实际代价：配置页得长期显示一批「已停用」的死行，或者靠 `status` 过滤把它们藏起来 —— 两种都不如「新版本里干脆没有它」直白 | §1.2 / §3.2 / §4.3 / §6.4 / §7.11-④ / §12 |
| **P3** | **历史不漂移的依据换了**：由 ~~「软删 ⇒ 行还在」~~ 改为 **「期次-版本绑定 ⇒ 旧版本还在」** | R2 的绑定机制本身**一个字没改**（§5.1.4 / §7.11-③ 全部沿用）；本版只是把「历史为什么安全」的解释从状态位挪回它真正的落点 | §5.1.4 / §7.10-N4 / §9 / §11-77 |
| **P4** | **`ErlDimensionConfigStatusEnum` 保留，但降级为纯派生的展示态**：某 `code` 在**当前生效版本**里还在 ⇒ `ACTIVE`，不在了 ⇒ `RETIRED`（历史期次据此标灰） | 前端仍需要「这一维是历史遗留的」这一信息来标灰，但那是**算出来的**，不是存出来的。枚举保留 ⇒ 卡片（接口 1）与评分详情（接口 22）响应 `dimensions[]` 里的 `status` 字段**照常下发、形态与 v4.7 逐字节一致**，前端零改动（⚠️ 与 v4.0 删掉的 `MET` / `PARTIAL` / `GAP` 那个 `status` 不是同一个字段，§0.9-10） | §7.11-④ / §10.1 |
| **P5** | **权重合计口径**：由 ~~「仅 `ACTIVE` 行合计 = 100.00」~~ 改为 **「版本内全部维度合计恰为 100.00」** | 版本内已不存在「非 ACTIVE」的行，旧口径的限定词失去意义；服务端校验与前端 `Total` 都按全部行算 | §4.3 / §6.4 / §7.1 / §7.11-② |
| **P6** | **接口 23 / 24 的维度项不再有 `status`**：出入参一律 `{code, name, abbr, sortOrder, weight}`；`total` = 全部维度的合计 | 删除的表达方式变成「**不出现在提交的数组里**」，比传一个 `RETIRED` 更少一种中间态 | §6.4 |
| **P7**（⚠️ **面板已于 2026-09-09 再次改版**：行尾图标改为**三态**（~~「`deletable` ? 垃圾桶 : 电源按钮」~~ → `canDelete && !isRestored ? 垃圾桶 : 电源按钮`，**2026-09-09 实现落地后订正**，§0.21-X14）、面板底部加常显 `Deactivated Dimensions` 区块、`Show deactivated` 开关撤下，见 §0.21 / §8.4-C6；本行其余布局结论仍成立） | **配置页 C6 布局改版**：新增栏（`Dimension name` + `Abbreviation` + `+ Add`）**上移到面板头下一行**（取代表底的 `+ Add Dimension`）；列表由**表格**改为**卡片行**（拖拽手柄 + `Name (ABBR)` + 权重输入 + 铅笔 + ~~垃圾桶~~ → **2026-09-09：垃圾桶 / 电源按钮二选一**）；**`code` 列从页面撤下**；铅笔进入**行内编辑**（name / abbr / weight + 行内 `Save` / `Cancel`），**行内 `Save` 只本地提交这一行、不调接口**，只有右上角 `Save` 调接口 24 整组保存 | 「加一个维度」是配置页最高频的动作，放在表底要先滚到底；`code` 既不可改又与 `abbr` 高度重复，占一列只会让人误以为能编辑；行内 `Save` 与整组 `Save` 分层，是为了让「改了几行再一起提交」不产生 N 个配置版本 | §0.10-D13 / §2.3.1-⑤ / §8.4-C6 / §11-86 |
| **P8**（⚠️ **已于 2026-09-08 推翻前半段**：`code` 改为**服务端随机生成**、与 `Abbreviation` 彻底解耦，见 §5.1.3；后半段「code 永不改变、abbr 可随时改名」仍成立） | ~~**`code` 与 `abbr` 的关系定档**：新增维度时 `code` **取用户填的 `Abbreviation`（大写化）**~~；`code` 此后**永不改变**（它是 `erl_assessment.dimension_code` / `erl_reference_score_item.dimension_code` / `ai_erl_gap_analysis_item.dimension_code` 的关联键 —— 前两者的列名与表名分别于 2026-09-08 的 v4.15-② / v4.15-⑦ 改过，末者于 2026-09-18 随 `sprint118/V22` 改名），`abbr` **可随时改名、`code` 不跟随**。编辑一行改的是 `name` / `abbr` / `weight` 三样 | 页面上不再有 `code` 输入框，总得有个地方产生它；`abbr` 正是用户心里那个「缩写」。二者从此**只在创建那一刻相等**，之后各走各的 —— 改名不能动关联键，这是历史数据不断链的底线 | §2.2 / §5.1.3 / §6.4 / §8.4-C6 |
| **P9**（⚠️ **已于 2026-09-08 反转为软删，又于 2026-09-09 整条改判**：配置页**确实区分两个动作**（垃圾桶=删 / 电源按钮=停用），且删除**有**前置拦截 —— 判据是「是否进入过已发布题库版本」，见 §13-Q24 / §0.21） | ~~**§13-Q24 关闭**：取值 = **不区分 `Delete` 与 `Retire`，只有 `Delete`，且无条件允许物理删除**（不限于「从未被任何期次绑定过」的维度）~~ | 由 P1 ~ P3 直接推出：软删这层既然不再承担历史安全，就没有留着它、也没有为它做 UI 区分的必要 | §13 / §12 / §1.2 |

> **不变的部分**（避免过度解读）：`erl_company_period_config` 的**期次-版本绑定与「绑定后永不改写」**、`erl_dimension_config_version`
> 的 `is_latest`（v4.5）、**整组替换语义**与「保存即生成新版本」、**旧版本 item 行永不改写**、计分口径（§7.1 / §7.2）、
> 权限口径（§4.2 / §4.3，含 v4.7 的 `organizationId`）、题库版本化与 Publish（§7.9）、其余 11 张表 —— 一律不动。
> 本版只改「删掉一个维度在库里长什么样」与「配置页那一屏怎么摆」。

### 0.15 v4.8 → v4.9 修正清单（依据需求方 **2026-09-06** 裁决：题目判定标准不进需求设计 —— **v4.5 ~ v4.8 编制时漏登记，此节补登**）

> **裁决原文口径**：题目的**判定标准（`criteria`）不进需求设计** —— **不再采集、不再展示、不再作为 Goldie 差距分析的输入**；
> A5「How It's Scored?」弹窗（唯一实质内容就是该字段）**整块删除**。
>
> ⚠️ **版本号与日期为何这样排**（不伪造时间线）：本裁决与 §0.12 的附件裁决**同日**（2026-09-06），早于 v4.7 / v4.8 所依据的
> 2026-09-07 追加要求，但 v4.5 ~ v4.8 编制时**漏登记了这一条**。为不改动已发布的 v4.5 ~ v4.8 编号，本节按**登记先后**取下一个
> 版本号 **v4.9**；版本说明表的日期列记**裁决日 2026-09-06**，并注明**登记日 2026-09-07**。三条裁决内容互不冲突（v4.7 改
> C 模块入参、v4.8 改维度配置、v4.9 改题目字段），故补登不影响 v4.7 / v4.8 的任何结论。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **S1** | **`erl_question_config.criteria` 整列删除**：题库不再有「判定标准」字段 —— 配置页 C2 / C3 表单**不采集**，接口 **10 / 12 无该入参**，接口 **2 / 8 / 9 / 22 / 26 无该出参**（题目结构复用同一个 `ErlQuestionDetailDTO`），题库版本 diff（`changeType` / `changeSummary`）的比对项里也不再有它。建表脚本、列注释与种子数据一律无该列；已建过库的环境执行 `ALTER TABLE erl_question_config DROP COLUMN IF EXISTS criteria;` | 该字段自始至终是**设计自创**：PRD §3.8 的题目字段只有「题干 / Era Band / Source」，最后一个 PRD 锚点已在 v4.4 消失（§0.10-D18），此后一直挂在 §13-Q25 上、**配置页根本没有产生它的地方**。需求方裁决即选了 Q25 的「从输入中移除」这一支 | §5.1 / §6.2 / §6.2.1 / §6.4 / §10.1 |
| **S2** | **A5「How It's Scored?」弹窗整块删除**：三处题目行（A3 / A4 复用的 `QuestionRow`、填报页题目行、A4 双端并列行）的入口链接与弹窗状态一并移除，`ScoringCriteriaModal` 组件与 `.criteriaLink` 样式删除；A5 从 §1.1 范围表、§6.2 标题、§8.1 路由表、§8.2 目录结构、§8.4 交互表中撤下 | 弹窗的**唯一实质内容**就是 `criteria` + 所属 `Era-level`；字段没了以后只剩一个重复显示 Era-level 的空壳（Era-level 本就在逐题行的次级行上），留着等于给用户一个点开是空的图标。原型里它本就是 `return null` 的桩（§2.3.1-②-7），「桩即最终形态」 | §1.1 / §6.2 / §8.1 / §8.2 / §8.4 |
| **S3** | **Goldie 输入去掉 `criteria`**：`POST /api/ai/erl/gap-analysis`（**2026-09-19 改名 `/gap-analysis/refresh`**）的 `questions[]` 不再携带该字段，判断依据收敛为**题干 + 逐题 Yes/No + 双端备注 + level 口径**；prompt `source/ai/prompts/erl/erl_gap_analysis.md` 升至 **`# version: 1.1`**，正文删去该输入，并新增一条**反向约束**「输入里没有判定标准字段，不得编造标准原文」（**2026-09-07 又升至 `1.2`**：规则 7 残留的「准则」一词改为「作答」—— 那是 `criteria` 留下的用词，留着会暗示模型存在准则原文） | 少一个字段不等于 gap 质量必然下降 —— **止步 level 内那些答 No 的题本身就是最直接的差距来源**（§6.6 的 level 语义说明一字不变），备注才是证据主体。反向约束是必需的：prompt 早期版本引用过「Workbook 准入准则」，不写清楚会让模型把标准**编出来** | §6.6 / §10.2 |
| **S4** | **§13-Q25 关闭、回写项 M11 关闭**：Q25 取值 = **从 Goldie 输入中移除**（不再是 v4.4 的「V1 保留该字段」）；M11 的「在 PRD §3.8 补该字段 / 从 Goldie 输入中移除」二选一**已选后者** —— **PRD §3.8 无需为此改动**，回写清单收敛为 M1 ~ M10 + M12 + M13 | 两条出路本就互斥，需求方选定即关闭，不留「V1 先保留、以后再说」的中间态 | §0.10-④ / §13 / 附录 B / 附录 C.4 |
| **S5** | **验收清单反转**：§11-24c 由「C2/C3 表单只有**一个** `criteria` 输入」**反转**为「表单**没有** `criteria` 输入、题目行**没有** `How It's Scored?` 入口」；§11-25a 的 gap 校验由「围绕那两道 No 的题的 `criteria`」改为「围绕那两道 No 的**题干与备注**」；§11-69 的残留检索清单**补入**单列 `criteria` 与 `ScoringCriteriaModal` | 删字段最容易留下的残留正是「表单输入框 / 弹窗入口 / DTO 字段」三处，必须由验收项正面盯住，否则回归时看不出来 | §11-24c / §11-25a / §11-62 / §11-69 / §11-74 |

> **不变的部分**（避免过度解读）：`question_text` / `era_band`（level）/ `evidence_source` / `sort_order` / `question_key` 五列、
> 题库版本化与 Publish（§7.9）、版本锁定与期次-版本绑定（§7.9-⑤ / §7.11）、逐级解锁计分口径（§7.1 / §7.2）、
> 权限口径（§4.2 / §4.3）、备注与附件链路、Goldie 的 level 语义说明与「未解锁 level 的题不在输入中、不得编造」
> 这条**原有**约束 —— 一律不动。
> **历史变更记录不删**：§0.9-21、§0.10-D18、附录 A、附录 B、附录 C.3-D18 中关于 `criteria` 的记载**原文保留 + 加反标**。

### 0.16 v4.9 → v4.10 修正清单（依据需求方 **2026-09-07** 裁决：C7 维度按题库版本发布当时的集合显示）

> **裁决原文口径**：`Question Library History` 页面的数据**按发布时的维度显示** —— 发布当时只有 `test1 / test2 / test3` 三个维度，选中那一版就只显示这三个；**此后维度增、删、改名一律不影响已发布版本的历史展示**。
>
> ⚠️ **本版是「设计自相矛盾的收敛」，不是新需求**：v4.4-D1 在 §1.1 / §2.3.1-⑥ / §8.2 / §8.4-C7 四处写的是「按**该版本对应 / 绑定的**维度配置渲染」，而 §6.4 接口 26 的条款写的是「**前端按接口 23 返回的（当前生效）维度配置**自行归组与排序」—— 两者不可能同时成立，因为当时**模型里根本没有「题库版本 ↔ 维度配置版本」的绑定**。实现照后者落地，于是历史版本的维度区恒等于今天的配置。本版按需求方裁决取前者，并把缺失的绑定补上。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **H1** | **`erl_question_config_version` 新增列 `dimension_config_version_id`**（varchar(36)，**可空**，无外键约束、与 `based_on_version_id` 无关）：**接口 21 Publish 在同一事务内**写入「发布当时该组织生效的维度配置版本 id」（v4.7 起替租户发布时按**目标组织**取值）；**草稿行不写**（草稿还没定版，读时回退当前生效配置） | 「发布时的维度」这件事此前**没有任何落点**：`change_summary` 里的 `dimensions[]` 只是本次发布**改动过**的维度 code，既非全量集合、也不含 name / abbr / sortOrder。可空是必需的：存量已发布行无法精确重建，且本仓 `ddl-auto: update` 加不上 NOT NULL 列 | §5.1.1 / §5.1.2 / §6.4 / §7.9 / §7.11 / §10.1 |
| **H2** ⚠️（**字段清单与复用口径均已于 2026-09-09 订正，见 §5.1.5 / §6.4 接口 26**：现为 `{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }`，**无 `weight`**，且**另造窄 Response**、不复用 `ErlQuestionConfigListResponse`；本行其余结论仍成立） | ~~**接口 26 出参新增 `dimensions[{ code, name, abbr, sortOrder, weight }]`** —— 取该题库版本绑定的配置版本的 items，按 `sortOrder` 升序；仍**复用 `ErlQuestionConfigListResponse`**（不另造 DTO / Response）~~，**接口 9 恒为 `null`**。绑定列为空时**服务端**回退当前生效配置，前端不做回退 | C7 是版本快照页，维度骨架必须与题面同源、同一次请求给全；让前端再拼一次「该看哪个配置版本」等于把版本解析逻辑复制到前端 | §6.4 / §8.4-C7 / §10.1 / §10.3 |
| **H3** | **C7 页体归组骨架换源**：由 ~~接口 23（当前生效配置）~~ 改为**接口 26 出参的 `dimensions[]`**；卡头 `{全称} ({缩写})` 用**发布当时**的 name / abbr；~~接口 23 在该页**只剩一个用途** —— 判断某维度「今天是否还在配置里」以决定是否打 `Retired` 灰标（与 §6.1 `status` 的派生口径一致，v4.8）~~ → **2026-09-09 作废（v4.17，§0.22-Y2 / -Y4）：灰标撤下，接口 23 在本页的最后一个用途随之消失 ⇒ C7 不再调接口 23，只读接口 25 / 26**。某题目的 `dimension` 不在发布时集合内（脏数据 / 近似回填不准）时**仍兜底出卡**，name / abbr 退化为 code 并标 `Retired` —— **题目永不消失** | 「卡片来源」与「今天还在不在」是两件事，之前被合成了一件，于是被删维度的卡头退化成 `FRL (FRL)`、发布后新增的维度在旧版本上多出一张空卡。⚠️ ~~**v4.11 部分作废**（§0.17-K1 ~ K3）：`Retired` 灰标与兜底卡在本页**整体取消**，今天已不在配置里的维度**整卡不显示**（连带其题目）~~ → **2026-09-09 恢复本行原文（v4.17，§0.22-Y2 / -Y3）**：K1 / K3 从未实现、已整条取消 ⇒ **维度整卡照常展示、兜底卡与「题目永不消失」照常成立**，本行唯一被推翻的只有 `Retired` 灰标那半句（灰标撤下，兜底卡的 name / abbr 仍退化为 code、但**不再打标**）；卡头仍用发布当时的 name / abbr | §8.4-C7 / §11-90 / §0.17 |
| **H4** | **两条版本线的表述订正**：§5.1.2 与 §7.11 边界表注释里的「**互不联动**」改为**写侧单向记录**（Publish 时题库版本记下当时生效的配置版本 id），**读侧仍不联动** —— 题库发布不改变任何期次的 `erl_company_period_config` 绑定，维度配置 Save 也不产生题库版本、不改写任何已发布题库版本行。§7.11「所有按期次取维度」的清单里**移出 C7**：C7 没有期次概念，它按题库版本自己的绑定取维度 | 不订正的话，「互不联动」会被后来人当成「不许加这一列」的依据；但也必须写清订正的**边界**，否则会被误读成两条版本线开始互相激活 | §5.1.2 / §7.11 |
| ~~**H5**~~ | ❌ **2026-09-09 整条作废**（`V3` 已作废、`erl_dimension_config_version` 与 `saved_at` 均已删除；`V8` 改为按 `(批次 id, dimension_code)` **精确**回填，不再按时间近似） —— **存量回填是近似的**：迁移脚本对 `status = 'PUBLISHED'` 且 `published_at` 非空的行，按同组织 `erl_dimension_config_version` 中 `saved_at <= published_at` 的最大 `version_no` 回填，**取不到则回落到该组织最早的那一版配置**（V1 种子先插题库版本、后插配置版本，`saved_at` 恒晚于`published_at` 几微秒，时间比对对种子行必然不成立；两行本是同一段种子建出来的，「首版发布时的配置」就是 `version_no` 最小那版），两支都取不到才留 `NULL`（读时回退当前生效配置）。脚本内注明**这不是精确重建** | ERL 尚未发版，正常环境命不中任何行；写成近似回填只为已建过库的本地 / 测试环境不至于整体回退到当前配置 | 附录 C / §10.1 |

> **不变的部分**（避免过度解读）：`erl_dimension_config_version` / `erl_dimension_config_item` / `erl_company_period_config` 三张表**一列未改**；**期次-版本绑定（§7.11）仍是历史分数不漂移的唯一机制，本版不动它**；接口 23 / 24 契约不变（C6 配置页行为逐字节不变）；题库两态发布流程（§7.9）、版本锁定（`erl_assessment.question_version_id`）、计分与权限口径一律不变。**表数仍为 12 张**（只加一列）。

### 0.17 v4.10 → v4.11 修正清单（依据需求方 **2026-09-07** 追加要求：C7 不显示带 `Retired` 灰标的维度）—— ⚠️ **本节 K1 ~ K4 已于 2026-09-09 整体作废**（v4.17，§0.22）

> ⚠️ **2026-09-09 全节墓碑（v4.17，§0.22-Y2 / -Y3）**：本节的落地方式（**先按当前配置过滤、再把灰标删掉**）已被需求方当日的裁决取代 ——
> 最终取值是「**既不过滤、也不标注**」：C7 照常整卡展示发布当时的每个维度与它的题目，只是**卡头不再有 `Retired` 灰标**。
> K1 / K3 / K4 **从头到尾没有实现过**（§8.4-C7 一直写着「未裁决前不得实现本条」），K2 的灰标也随之被回退、一直显示在页面上；
> **K1 由 §0.22-Y3 正式关闭（取值 = 整条取消）**。以下四条**原文保留**作变更记录。

> **要求原文口径**：`exitReadiness/configuration/history` 页面，**带 `Retired` 灰标的数据不显示**。
>
> ⚠️ **只改 C7 这一页的展示规则，不动口径 A 的机制**：卡片仍取该题库版本**发布当时**的维度集合（接口 26 的 `dimensions[]`，v4.10-H1 / -H2 一字不变），只是在渲染前**按当前生效配置过滤一次**。**历史期次**（A1 卡 / A2 雷达图 / A4 Score Details）那条「已删维度照常显示 + `Retired` 灰标」的口径（§9 边界表 / §13-N4 / §11-77）**不受本版影响** —— 那里的依据是 `erl_company_period_config` 的期次绑定，与本页无关。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| ~~**K1**~~ **（2026-09-09 整条取消，§0.22-Y3）** | ~~**已删维度整卡不显示**~~：C7 页体 = 该版本发布当时的维度集合 **∩** 当前生效配置的 code 集合（大小写不敏感），差集里的维度**不渲染**，**其题目也不出现在本页** | 需求方 2026-09-07 追加要求。灰标方案下，一个只发布过一次、其后维度被整批换掉的版本会显示成「一排灰标的陌生维度 + 一堆空卡」，比不显示更难读 | §8.4-C7 / §0.16-H3 |
| **K2**（**2026-09-09 由 §0.22-Y2 / -Y4 以另一条路径重新落地**） | **`Retired` 灰标在本页整体取消**：`QuestionVersionSection.retired` 字段、卡头标注与 `QuestionVersionHistoryPage.less` 的 `.retiredTag` 一并删除（**`TEXT.retired` 常量保留** —— A4 `DimensionQuestionsCard` 仍按 `status === 'RETIRED'` 用它） | ~~过滤之后没有任何 section 会带 `retired = true`，留着就是死代码~~（**2026-09-09 换论据**：过滤从未实现、灰标一直在，本条实际是被 v4.17 的裁决兑现的 —— **标本身撤下**后这三处才真正失去消费方，连带**接口 23 的取数也一起撤**，§0.22-Y4）；但常量是跨页共用的，不能一起删（**`TEXT.retired` 的这条理由 2026-09-09 仍然成立**） | §8.4-C7 / §0.22-Y2 / -Y4 |
| ~~**K3**~~ **（2026-09-09 随 K1 一并取消，§0.22-Y3）** | ~~**兜底卡取消**~~：题目的 `dimension` 不在发布当时集合内时（脏数据 / 存量回填不准）**不再另出一张裸 code 卡**，该题目在本页不显示 —— **v4.10-H3 的「题目永不消失」在本页作废** | 那种卡必然是「已从配置里删掉的维度」，与 K1 要隐藏的是同一批东西；留着它等于给 K1 开一个后门 | §0.16-H3 / §11-90 |
| ~~**K4**~~ **（2026-09-09 该空态整条删除，§0.22-Y3）** | ~~**新增空态**~~：`versions` 非空但过滤后 `sections` 为空时，页体渲染一条 `None of this version's dimensions are in the current configuration.` | 发布当时的维度今天一个都不在（例如种子版本 + 维度整批换过）是**常见**情形，不能只留一页空白让人以为页面坏了 | §8.4-C7 / §9 |

> **不变的部分**（避免过度解读）：接口 26 的出参契约（含 `dimensions[]`）、`erl_question_config_version.dimension_config_version_id` 的写入与回退、卡头用**发布当时**的 name / abbr、卡片顺序按发布当时的 `sortOrder`、"发布后新增的维度不在旧版本上冒空卡"、以及**服务端一行代码都不用改** —— 本版是纯前端过滤。

### 0.18 v4.11 → v4.12 修正清单（依据 **2026-09-07 ERL 代码审核**的两条 P0 与实现回写）

> **性质**：本版**没有新需求**，是「文档与实现不一致」的收敛 + 并发正确性的定档。两处属**文档写反**
> （`stale` 无条件清零、0 题维度可提交），其余为此前从未落到文档的实现约束。
>
> ⚠️ **本版不改任何对外契约**：接口出入参、计分口径、权限口径、UI 一律不变；改动集中在
> 「并发下这些不变量靠什么兜底」以及「两处相反表述的订正」。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **L1** | **`stale` 清零加前置条件**：差距分析落库前重算「双端各维最新已提交记录 id」的指纹（**2026-09-08**：「最新」按 `submitted_at DESC, id DESC` 取首条），只有与调 LLM 之前一致才清 `stale`；不一致则内容照写、**保留 `stale = true`** | 一次 LLM 往返最长 3 分钟，期间完全可能又有人提交。原先无条件清零，叠加「抢锁失败静默返回」，会让并发的第二次提交**永久**不进分析 —— 而前端 `stale = false` / `generating = false` 一切正常、没有任何后续触发点，GSV 点 Share 分享出去的正是一份声称最新、实际漏了一次提交的内容。这直接推翻本节自己写的「始终反映最新数据」 | §7.5（时序图 + S7） |
| **L2** | **抢锁失败不再静默丢弃 + 补跑**：持锁者跑完、**且已释放锁**后重读一次 `stale`，仍为 true 就再跑一轮，上限 **2 轮**；超限保留 `stale = true` 交下一次提交或手动 Regenerate 收敛。锁 TTL 5 分钟 → **600 秒** | 「重读放在释放锁之后」是关键：此刻另一个提交要么被下一轮吃掉、要么它自己就能抢到锁，两条路都不丢；若放在持锁期间，落在这之后到达的提交既进不了循环也抢不到锁。TTL 原值 300 秒**小于单轮最坏耗时**（3 次尝试 × 180 秒读超时 + 退避 ≈ 546 秒），锁会在生成中途过期、让第二个线程拿到同一把锁并发写同一份分析（item 行交错、主行 last-write-wins）。改成每轮各自抢锁释放后，TTL 只需覆盖单轮 | §7.5（并发去重与补跑） |
| **L3** | **`erl_gap_analysis` 主行的三个写入方一律加 `SELECT … FOR UPDATE`**：重生成落库、提交时置脏、Share。**刻意不用乐观锁** | 三者都是全列 UPDATE，不串行化会互相回写：置脏方读到旧摘要后提交，会把重生成刚写入的新摘要连同 `generated_at` / `model` 一起回退，而 item 明细已是新一代 —— 主行与明细来自两代生成、`generated_at` 倒退。不用乐观锁的理由：置脏方跑在**用户提交评估的事务**里，乐观锁失败会让整次提交回滚（用户白填一份问卷）。这把行锁同时让「指纹重算」与「置脏」互斥，是 L1 成立的基础，也是本设计**不需要**任何额外 Redis 待办标记的原因 | §7.5（S8） |
| **L4** | **`erl_assessment` / `erl_question_config_version` 各新增 `version` 列**（bigint, not null, default 0；JPA `@Version`）；**写路径同时加悲观锁** | 全仓此前 `@Version` 零命中，而这两张表都是**多人共享同一行**的写入对象。仅加乐观锁不够：存草稿与 Reset 只改三列，而 Reset 恰好把它们设回与自己加载快照**逐字相同**的初始值 —— 配 `@DynamicUpdate` 后 Hibernate 判定该行干净、**一条 UPDATE 都不发**，版本谓词根本没出现过，于是它能把别人刚提交记录的作答与证据附件删空且全程无异常；删附件更是完全不写主行。故写路径（存草稿 / 提交 / Reset / 删附件）一律先加行锁。题库侧草稿的并发编辑也取悲观锁，让失败落在**低频的发布方**而不是高频的编辑方 | §5.1.1 / §5.2 / §7.7 / §7.9 / §12 |
| **L5** | **「0 题维度可提交」四处订正为「不可提交」**：§6.3 校验 2 的附注、§7.2 状态机的「不拦提交」、§9「某维 0 题」行、§11-11b；`canSubmit` 判定口径同步订正 | **文档内部本来就分裂**：§9 另一处（「某维度在已发布版本中 0 题」）早就写着「整页即空态、`Submit` 禁用」，而这四处写的是「视为已终止、不拦提交」。实现侧 `canSubmit` 从一开始就要求 `totalCount > 0`，所以那四处在改动前就是错的；本版把提交侧对齐视图侧，并订正文档 | §6.3 / §7.2 / §9 / §11 |
| **L6** | **§4.3 新增一条后端强制校验**：接口 4 / 5 / 28 的 `dimension` 必须属于该期次绑定的配置版本，否则报**业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3），并按配置里的规范写法归一大小写 | 此前只校验「非空 + 转大写」，于是任何满足 `^[A-Za-z0-9]{1,8}$` 的字符串（如 `ZZZ`）都能一路落库成 `SUBMITTED`：该维在题库里查不到题、计分器对空题集返回「已终止、无未答题」、提交前置校验全过，最后污染 ERL Card / 组合层 / Share 门槛判定，还白触发一次 LLM。只读的接口 3 早就在校验（它要拿配置项渲染页头），漏的是这三个写接口 | §4.3 / §6.3 |
| **L7** | **§9 失败降级表补「并发写同一行（乐观锁冲突）」一行**：HTTP 200 + `success: false`，文案 `This record was changed by someone else. Please reload and try again.`，日志 WARN 带异常 | 乐观锁冲突不是服务端故障而是「另一个人刚改过同一行」的可重试正常竞争。没有这条口径时它会落到 `Throwable` 兜底返回 500，用户看到的是「服务器错误」而不是「重新加载再试」；记 ERROR 也会污染 Sentry 告警面 | §9 |
| **L8** | **「门槛未达成」由抛异常改为返回值表达** | 设计 §7.5-S1 明确「该期次每维双端都提交才调 LLM，未达成时不调、保持 `stale = true`」属**正常路径**，而实现用 `BadRequestException` 表达并被统一 `log.error(带栈)` 捕获 —— 5 维 × 双端 = 10 次提交里有 9 次都会往 Sentry 刷一条带堆栈的 ERROR。异步入口现记 INFO，手动入口自己按返回值抛出提示 | §7.5（S1） |

> **不变的部分**（避免过度解读）：接口 1 ~ 28 的出入参契约、维度分与综合分的计分口径（§7.1 / §7.2）、
> 期次-版本绑定（§7.11）、题库版本化与 diff 口径（§7.9）、权限与裁剪清单（§4.2 / §4.3 的其余各条）、
> Share 流转（S1 ~ S6）、以及全部 UI 规格（§8）—— 本版一律未动。
>
> **两项已知残留**（已登记 `CIOaas-api/docs/待优化项.md`）。**2026-09-19 更新**：第 ① 项随 P3 **自动失效** —— Java 侧的差距分析 Redis 锁已删除，Python 侧那把锁自带「按 token 释放」（Lua 单步比对后再删）；第 ② 项**仍然成立**，Java 侧依旧用 `@Async("ioExecutor")` 投递重生成。原文：① `RedisDistributedLock` 的锁 value 是常量、
> 解锁不校验持有者，TTL 提高只是回避而非根治；② 差距分析仍寄生在通用 `ioExecutor` 上，
> 队列打满时 `CallerRunsPolicy` 会把 LLM 往返倒灌回请求线程。

### 0.19 v4.12 → v4.13 修正清单（依据 **2026-09-07** 题库两张表与对应 Java 类改名）

> **性质**：**纯改名**，无需求变更、无语义变更、无契约变更。动机是与 interfaces 层**早已存在**的
> `ErlQuestionConfigResponse` 对齐 —— 同一个「题库配置」概念，响应体上叫 `QuestionConfig`、
> 表与实体上却叫 `Question`，两套名字并存，读代码的人分不清 `ErlQuestionResponse` 与
> `ErlQuestionConfigResponse` 谁是谁。
>
> ⚠️ **本版一个字都不改对外行为**：HTTP 路径、列名、出入参字段名、计分与权限口径、UI 一律不动；
> **前端零改动**（`/erl/question` 系列路径原样保留；前端 TypeScript 的传输实体不在本次范围）。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **T1** | **两张表改名**：`erl_question` → **`erl_question_config`**、`erl_question_version` → **`erl_question_config_version`**。**列名一个未改**（`question_key` / `question_text` / `sort_order` / `version_id` / `version_no` / `is_latest` / `dimension_config_version_id` …），外键指向的写法只跟着表名走（`erl_assessment.question_version_id` → `erl_question_config_version.id`），**表数仍 12 张** | 表名与响应体名对不上时，「题库配置」这一个概念在库里、在实体里、在接口里各叫一套 | §5（表清单）/ §5.1 / §5.1.1 / §5.2 / §5.4 |
| **T2** | **索引与唯一约束名一并对齐**：`uk_erl_question_config_key` / `idx_erl_question_config_version_dim` / `uk_erl_question_config_version_draft` / `uk_erl_question_config_version_no` / `idx_erl_question_config_version_status` / `uk_erl_question_config_version_latest` | 约束名里嵌着旧表名，DBA 在库里按名字找不到对应的表；**索引的语义、条数与「五个部分唯一索引」的口径一律不变** | §5.1 / §5.1.1 / §10.1 |
| **T3** | **Java 类全套改名** `ErlQuestion*` → **`ErlQuestionConfig*`**：实体（`ErlQuestionConfig` / `ErlQuestionConfigVersion`）、两个 Repository、两套 `Service(+Impl)`、`Mapper`、DTO（`…DTO` / `…ListDTO` / `…VersionDTO` / `…VersionHistoryRecordDTO`）、枚举（`…ChangeTypeEnum` / `…VersionStatusEnum`）、`Controller`、`Converter`、Request（`Create` / `Update` / `Reorder`）、Response（`List` / `Version` / `VersionHistory` / `VersionHistoryRecord`） | 类名跟表名同步走，否则会出现「表叫 config、实体叫 question」的第三套口径 | §6.4 / §7.9 / §10.1 |
| **T4** | **两个例外保持原名**：① `ErlQuestionConfigResponse` —— 它本来就带 `Config`，跟着替换会变成 `…ConfigConfigResponse`；② `ErlQuestionDetailResponse` 与其对应的 `ErlQuestionDetailDTO` —— 这是**评估回放的只读逐题结构**（A3 / A4 / B3 与接口 2 / 8 / 9 / 22 / 26 共用），描述的是「某次作答的题面」而不是题库配置 | 例外不是漏改：`Detail` 那一套跨展示域与配置域共用，冠上 `Config` 反而会让人以为它只服务配置页 | §6.2 / §6.2.1 / §10.1 |
| **T5** | **迁移脚本就地改**：`sprint118` 的 `V1__erl_init.sql`（建表 / 索引 / 种子）、`V3__erl_question_version_add_dimension_config_version.sql`（加 `dimension_config_version_id`）、`V4__erl_optimistic_lock.sql`（加 `version`）里的表名与约束名**原地更新为新名**，**不新增 `ALTER TABLE … RENAME` 改名脚本**；`V3` 的**文件名保留原样**，README 的执行顺序不变 | 本仓库无 Flyway/Liquibase，这三份脚本是**人工按序执行**的建库 runbook（§10.1 补注），ERL 还没有需要保数据升级的正式环境 —— 就地改比「先按旧名建、再改名」少一步，也少一个漂移源；已按旧名建过库的本地环境按 README 重建即可 | §10.1 |

> **不变的部分**（避免过度解读）：接口 1 ~ 28 的路径与出入参契约（`GET / POST /erl/question`、`GET /erl/question/version`、`GET /erl/question/version/{versionNo}`、`POST /erl/question/publish`、`PUT /erl/question/reorder` **一律原样**）、题库两态发布流程与写时复制（§7.9）、版本锁定（`erl_assessment.question_version_id` **列名不变**）、`is_latest` 与 `dimension_config_version_id` 的口径（§0.11 / §0.16）、期次-版本绑定（§7.11）、计分与权限口径（§7.1 / §7.2 / §4.2 / §4.3）、其它 `erl_*` 表名（`erl_assessment` / `erl_assessment_answer` / `erl_answer_attachment` / `erl_dimension_config_version` / `erl_dimension_config_item` / `erl_company_period_config` / `erl_benchmark_record` / `erl_gap_analysis` …）、以及全部 UI 规格（§8）—— 本版一律未动。

### 0.20 v4.13 → v4.14 修正清单（依据需求方 **2026-09-07** 决定：ERL Configuration 的菜单入口改由管理后台配置）

> **性质**：**落库途径变更**，无需求变更、无表结构变更、无契约变更。ERL Configuration
> 「挂顶部导航右侧下拉菜单、仅管理端可见」这件事**本身不变**，变的只是那条 `menu` 记录
> 与角色授权**由谁写进库** —— 原先靠迁移脚本 `V2__erl_menu.sql`，现在由**管理后台已有的
> 菜单配置功能**添加，该脚本已从 `sprint118/` 删除。
>
> ⚠️ **不要把「不用脚本了」读成「不用配了」**：§8.1.1 的三个前置条件缺一个菜单就不显示，
> 在后台界面上配也一样要满足，尤其是 **`pid` 必须是 `'0'`**。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **U1** | **菜单入口的落地位置换源**：§8.1.1 前置条件表第 1、2 行的「落地位置」由 ~~`deploy/upgrade_doc/sprint118/V2__erl_menu.sql`~~ 改为**管理后台菜单配置**。**前置条件本身一字不改** —— `menu` 表要有 `path = '/exitReadiness/configuration'` 的行、**`pid` 必须是 `'0'`（根节点）**、该菜单经 `r_role_menu` 授权给用户角色（后台配置时授权给超管角色） | 需求方决定这条菜单不再由发版脚本落库，走后台自助配置。⚠️ **`pid = '0'` 这条约束在后台界面上同样是硬要求**：`MenuServiceImpl.buildTree` 只把 `pid = '0'` 的行放进返回数组顶层，而 `getVerifyRoles` **只比较顶层 `path`、不递归 `menuDtoList`** —— 在后台把它挂到某个父菜单下面，会被 `buildTree` 嵌进 `menuDtoList` 子级，下拉里**依然不显示** | §8.1.1 |
| **U2** | **清两处缓存的操作要求保留**：配好菜单后仍须 ① 清服务端 `MenuServiceImpl.findAllByUserId` 的 `@Cacheable(key = "'menu:user:' + #userId")`；② 清浏览器 `localStorage.roles` + 同名 cookie，然后重新登录 | 缓存链路与「记录是脚本插的还是后台插的」无关 —— 两处都不清，**在后台配好了也不生效**，和以前改库不清缓存是同一个坑 | §8.1.1 |
| **U3** | **sprint118 可执行脚本由四份减为三份**：`V1__erl_init.sql` / `V3__erl_question_version_add_dimension_config_version.sql` / `V4__erl_optimistic_lock.sql`（**V3 / V4 的文件名保留旧称不变**，不因 V2 消失而重排序号），另有 `README.md` 作为 runbook。§10.1 的脚本清单与数量词、§0.19-T5 的「这四份脚本」一并订正 | 序号重排会让已按旧编号执行过的环境对不上账，代价大于「编号有缺口」这点观感 | §10.1 / §0.19-T5 |
| **U4** | **路由守卫的口径不变、论据换例子**：`SecurityLayout.tsx` 仍对 `/exitReadiness/configuration*` 与 `/exitReadiness/benchmark*` 按**端类型 `roleType > 1`** 拦截，**不按菜单权限判**；其论据里的反例由 ~~「`V2__erl_menu.sql` 没跑」~~ 改为「**菜单未在管理后台配置**（或配错成非根节点、忘了授权）」 | 论点原样成立 —— 菜单权限只决定「入口显不显示」，配置页若压在菜单权限上，菜单没配好就会把管理员彻底锁在门外；只是不该再引用一个已删除的脚本当例子 | §8.1.1 |

> **不变的部分**（避免过度解读）：ERL Configuration「仅管理端可见 + 按 `organizationId` 隔离」
> 的口径（§8.1 / §4.3）、后端「C 模块写接口与 D 模块全部接口一律校验管理端」的第三层拦截、
> `menu` / `r_role_menu` / `r_user_role` 三张表的结构与 `buildTree` / `getVerifyRoles` 的行为、
> 以及 §10.1 里 12 张表、五个部分唯一索引、题库与维度配置种子 —— 本版一律未动。（⚠️ **这两个数字是 v4.14 当时的口径**：现为 **11 张表、3 条部分唯一索引**，见 §10.1。）

---

### 0.21 v4.15 → v4.16 修正清单（依据需求方 **2026-09-09** 裁决：维度的删除按「是否进入过已发布题库版本」分成两个动作）

> **裁决原文口径**：**一个从来没被发布出去过的维度，管理员应该能把它彻底删掉**；而**已经随题库发布出去过的维度不许删** ——
> 那份已发布的题库版本必须始终解得出它是哪个维度。所以配置页那一个破坏性动作要分成两个：
> **垃圾桶（删）** 与 **电源按钮（停用）**，由服务端按「该 `dimension_code` 有没有出现在某个 `PUBLISHED`
> 题库版本的维度快照里」决定给哪一个。布局取自当日 mockup（面板底部常显 `Deactivated Dimensions` 区块）。
>
> ⚠️ **本版**不是**「把软删换成真删」** —— v4.15 定的那套「置 `status = 'Inactive'`、行与 `weight` 原样保留、可恢复」
> **一字未改**，只是它的触发入口从垃圾桶换成了电源按钮，恢复入口从 `Show deactivated` 开关换成了常显区块。
> 新增的是**另一个**动作（真删）与承载它的**另一个**列（`deleted`）。把两者混成一件事，就会写出「删除时把 `status`
> 置 `Inactive` 再置 `deleted`」这种既停又删的行，页面上它不显示、库里它却还占着「停用」的语义。
>
> ⚠️ **`status` 与 `deleted` 正交，不要合并成一个三值枚举**（`Active` / `Inactive` / `Deleted`）：
> 合并后「删掉一个当前**已停用**的维度」这件事就没有落点了 —— 而它是可达的（一个从未发布过的维度可以先被停用、
> 再被删除），三值枚举下只能靠丢掉原状态来表达，恢复入口一旦回来就无从判断它该回到哪个状态。

| `status` | `deleted` | 页面 |
|---|---|---|
| `Active` | `false` | **主列表**，可编辑；行尾按**三态**给销毁按钮（见下表） |
| `Inactive` | `false` | **`Deactivated Dimensions` 区块**，行尾 **`Activate`**（~~`Restore`~~，2026-09-09 mockup 定档，§0.21-X14） |
| 任意 | `true` | **完全不显示**（已删，无恢复入口） |

> **主列表行尾的销毁按钮是三态，不是二选一**（**2026-09-09 实现落地后补记**，§0.21-X14）：
>
> | 行的状态 | 行尾图标 | 语义 | 二次确认 / 提示 |
> |---|---|---|---|
> | `deletable = true` 且**本次会话未从停用区恢复过** | **垃圾桶** | **删除**（`deleted = true`，不可恢复） | `deleteDimensionConfirm` / OK 文案 `Delete` |
> | `deletable = false` | **电源按钮** | **停用**（`status = 'Inactive'`） | tooltip `dimensionPublishedTooltip` + `deactivateDimensionConfirm` / OK 文案 `Deactivate` |
> | **本次会话里刚从停用区 `Activate` 回来的行**（`isRestored`），**即便 `deletable = true`** | **电源按钮** | **撤销恢复**（把它放回停用区） | tooltip `dimensionRestoredTooltip` + `undoRestoreConfirm` / OK 文案 `Undo restore`；aria-label `Undo restore` |
>
> ⚠️ **第三态是防误删设计，不是实现细节**：判据是 `row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`。刚恢复一行之后，用户最想做的下一个动作往往是「撤销刚才的恢复」，而行尾**最近的那个按钮**若是垃圾桶，一次误点就把维度连历史一起葬掉（真删在本页**没有**恢复入口）。⇒ **恢复态的行不给垃圾桶**，等这一次 Save 落库、页面重新取数之后它才回到常规两态。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **X1** | **新增列 `erl_dimension_config.deleted`**（`boolean`，`not null`，默认 `false`）：配置页的「删除」= 置 `deleted = true`，**行与 `weight` / `dimension_name` / `dimension_abbr` 全部原样保留**（历史数据仍按 `dimension_code` 反查得到），但**所有读侧一律排除**，页面上**没有恢复入口** | 需求方要的是「彻底删掉」，而 `dimension_code` 被五张表当历史外键引用（§5.1.3），**真的 `DELETE` 会让那些历史数据解不出维度名**。留行 + 读侧一律排除是唯一能同时满足「用户看不到」和「历史解得出」的形态。**不复用 `status` 的第三个取值**，理由见本节开头第二条 ⚠️ | §5.1.3 |
| **X2** ⚠️ **（整条于 2026-09-15 作废，索引本身已删除）** | ~~**部分唯一索引的谓词加一半**：`uk_erl_dimension_config_abbr ON erl_dimension_config (organization_id, dimension_abbr) WHERE status = 'Active' AND deleted = false`~~ → **2026-09-15 作废**：需求方当日裁决「新增维度不做任何重名 / 重缩写校验」，`uk_erl_dimension_config_abbr` **整条删除**（迁移 `V15__erl_dimension_config_drop_abbr_unique.sql`，v4.31），谓词怎么写已无对象；组织内此后**只剩 `uk_erl_dimension_config (organization_id, dimension_code)` 一条唯一约束**。右栏的分析**仍然正确**，只是它要防的那个索引不复存在 | ⚠️ 漏掉 `deleted = false` 这半边的后果**不是**约束失效，而是**约束过紧且无法自救**：已删的行仍满足 `status = 'Active'`（删除**不改** `status`），于是它**永久占着自己的缩写** ⇒ 「删掉 `OPS`、再新建一个也叫 `OPS` 的维度」**永远撞唯一冲突**，而用户在页面两处都看不到那一行，**既不知道是谁占的、也没有任何入口把它放出来**。对比 `Inactive` 行：它至少在 `Deactivated Dimensions` 区块里看得见、可 `Activate` | §5.1.3 / §10.1 |
| **X3** | **两处读侧刻意不过滤 `deleted`**：① **全局 code 占用探针** `existsByDimensionCode` —— 已删维度的 `dimension_code` **永久保留占用**；② **`savedAt` = 全部行（含 `deleted = true`）的 `max(updated_at)`** | ① 那个 code 仍被五张表当历史数据引用（`erl_question_config` / `erl_assessment` / `erl_reference_score_item` / `erl_question_config_dimension_version` / `ai_erl_gap_analysis_item.dimension_code`）—— 生成新维度时若把它重新分配出去，**旧历史会静默地挂到新维度身上**，而这种错在库里长得完全正常，只有对着历史列表看名字才发现串了；② 删除也是一次写入，**必须 bump 乐观锁令牌** —— 否则「A 删了一行、B 拿着删除前的 `savedAt` 保存」会被判为无冲突，B 那份不含该行的数组一提交，删除动作直接被覆盖回去 | §5.1.3 / §6.4 |
| **X4** | **接口 23 出参每项新增 `deletable`**（boolean，非空）：`true` ⟺ 该 `dimension_code` 从未进入任何**已发布**题库版本的维度快照。另：**`deleted = true` 的行任何情况下都不下发**（含 `includeDeactivated=true`） | 「给垃圾桶还是给电源按钮」是**服务端才知道**的事实（要 join 题库版本），前端不能自己算；做成布尔而不是让前端拿版本列表自己推，是为了让判据只有一处实现。⚠️ **判据必须 join 到版本行并过滤 `status = 'PUBLISHED'`** —— `erl_question_config_dimension_version` **草稿版本上也有行**（§5.1.5 开头那条 ⚠️：某维本轮首次被编辑触发克隆时就写一行挂在草稿版本行上），**只查快照表**会把「只在未发布草稿里改过题」的维度误判成不可删，用户看到一个电源按钮却找不出任何理由 | §6.4 / §5.1.5 |
| **X5** | **接口 24 入参新增 `deletedCodes[]`**（本次要删除的已有维度 code），⚠️ **与 `deactivatedCodes` 不同，它可缺省**（缺省 / null = 空数组） | `deactivatedCodes` 之所以**必传**，是因为那条契约要杜绝「未出现即停用」的隐式软删（§6.4-2-⑥）—— 漏传会造成静默的状态变更。而 `deletedCodes` **缺省表达的是「什么都没删」**，本身就是安全的默认值，**没有可保护的对象**：不传 = 不删，不存在「本来该删却被漏掉」的隐式破坏 | §6.4 / §4.3 |
| **X6** | **接口 24 新增三条校验**（业务错误，HTTP 200 + `success: false`）：① code 不命中本组织已有行 → 沿用 `Unknown dimension code: {code}`；② 该 code 在**已发布**版本的快照里出现过 → `This dimension was published in a question set and cannot be deleted: {code}. Deactivate it instead.`；③ 同一个 code 同时出现在 `dimensions[]` / `deactivatedCodes[]` / `deletedCodes[]` 中的两个及以上 → `Dimension cannot be saved, deactivated and deleted at once: {code}` | ① / ② 是**服务端不能靠前端已拦就省掉**的那类校验（前端根本不显示垃圾桶，但抓包可以直接传）；③ 是三个桶引入的新中间态 —— 不拦就得定义优先级，而任何优先级都是猜用户意图，报错让用户自己说清楚 | §6.4 / §4.3 |
| **X7** | **集合完整性校验把 `deletedCodes` 也算作已交代**：`当前 Active 集合` 必须恰等于 `带 code 的项` ∪ `deactivatedCodes` ∪ **`deletedCodes`** | 原校验（§6.4-2-⑥，2026-09-08 加的「防静默软删」）只认前两个桶，**删一行必然触发误报** —— 那一行既不在 `dimensions[]` 里也不在 `deactivatedCodes[]` 里，于是每一次删除都会被判成「前端漏传了一行」并报**业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3）。⚠️ 这是本版最容易漏改的一处：新功能全部实现对了，删除仍然一次都成功不了 | §6.4 / §4.3 |
| **X8**（**理由已于 2026-09-15 作废，结论保留**） | ⚠️ **实现口径：可删性检查必须在 `validate()` 阶段、用整组锁读到的 `existing` / `previouslyActive` 判定** | ~~§7.11-② 的**第一阶段 `parkAll`** 会把该组织**全部行**落成 `Inactive` 并 flush（为腾空 `uk_erl_dimension_config_abbr`）——**之后再读 `status` 看到的全是 `Inactive`**。检查若落在第一阶段之后，「这一维原本是不是 `Active`」「集合完整性对不对」两件事同时失去判据，而它**不会报错**，只会开始放行本该被拦住的删除~~ → **2026-09-15 作废**：`uk_erl_dimension_config_abbr` 整条删除后 `parkAll` 随之取消（v4.31 / §7.11-②），保存是单阶段直接写终态，**不再有「先被落成 `Inactive` 再读 `status`」这个陷阱**。**结论仍然成立**（校验一律在 `validate()` 阶段、用整组锁读到的 `existing` 判定，落库前一律不写任何行），只是理由换成了「业务错误必须**库中无任何写入**」这条通用口径（§6.4-3） | §7.11-② / §6.4 |
| **X9** ⚠️ **（结论已被 v4.17 取代，见 §0.22-Y3）** | ~~**§0.17-K1（软删后 C7 的显示规则）**：⚠️ **本版不使它自愈，该待裁决项原样保留**~~ → **2026-09-09 当日更晚，需求方直接裁决 K1「整条取消」** ⇒ **该待裁决项已关闭**（§0.22-Y3）。本行的**分析仍然正确**（能删的维度与 C7 展示的维度正交、K1 那条规则确实永不触发），只是「原样保留」这个**结论**不再成立 —— 规则没有等到自愈，是被整条取消掉了 | v4.11 那条「C7 只显示今天仍在维度配置里的维度」原本靠「维度被物理删掉」判定；本版确实让维度**能够**从配置页彻底消失了，看起来 K1 有救 —— **但两个判据正交且方向相反**：能被删的**恰恰**是「从未进入过任何已发布版本」的维度，而 C7 展示的**只有**已发布版本的快照。**能删的维度永远不会出现在 C7 上，出现在 C7 上的维度永远不能删** ⇒ 该规则依旧永不触发、空态依旧不可达。~~K1 的两个候选取值（改判 `status = 'Inactive'` / 整条取消）**一个都没被本版排除**~~ → **2026-09-09（v4.17）：需求方选了「整条取消」**，C7 既不隐藏这类维度、也不再标注它 | §0.17-K1 / §0.22-Y3 / §8.4-C7 / §11-90 |
| **X10** | **`Show deactivated` 开关整个撤下**（连同它的脏态确认弹框文案 `dimensionConfigToggleDeactivated`）：页面此后**恒**带 `includeDeactivated=true` 取数，停用行由**面板底部常显的 `Deactivated Dimensions` 区块**承载（标题 + 空态 `No deactivated dimensions.` + 停用行 + 说明） | 那个开关是 2026-09-08 为「§5.1.3 说可恢复、但前端不可达」临时补的一个入口，代价是**它自己成了一个脏态**：开/关要不要确认、开着的时候提交集合算不算变化，都得单独定义（那条确认文案就是为此加的）。改成常显区块后，「展开」不再是一个动作，这些问题一并消失。⚠️ **但「④ 展开 ≠ 恢复」那条口径仍然成立** —— 停用行**看得见**不等于它进了 `dimensions[]`，没点 `Activate` 就仍进 `deactivatedCodes[]`（§8.4-C6-④ / §11-86-⑭） | §8.4-C6 / §6.4 / §11-86 |
| **X11**（**形态与约束已于 2026-09-09 按脚本现文订正，v4.18**） | **迁移 `V11__erl_dimension_config_add_deleted.sql`**：~~加列（`boolean not null default false`，`ADD COLUMN IF NOT EXISTS` 幂等）+ DROP 并按新谓词重建 `uk_erl_dimension_config_abbr`~~ → **实际是四步同处一个 `DO` 块**（外加「表不存在就 `RAISE NOTICE` + `RETURN`」的守卫）：① `ADD COLUMN IF NOT EXISTS deleted boolean`（**先建成可空**）→ ② `UPDATE ... SET deleted = false WHERE deleted IS NULL` 回填 → ③ `SET DEFAULT false` + `SET NOT NULL` → ~~④ `DROP INDEX IF EXISTS` + 按 `WHERE status = 'Active' AND deleted = false` 重建（索引名与键位不变）~~（**2026-09-15 作废**：`uk_erl_dimension_config_abbr` 已被 `V15` **整条删除**，这一步重建出来的索引此后由 `V15` 再删掉一次；`V11` 本身**不改**、仍按原样执行，只是第 ④ 步的终态被后续脚本覆盖，v4.31）。`V1__erl_init.sql` **已就地含该列**（~~与新谓词~~ —— **2026-09-15 起 `V1` 就地不再建该索引**） | **① 为什么不能写成一句 `ADD COLUMN ... NOT NULL DEFAULT false`**（PG 11+ 本不重写表）：**列已存在**的库上 `IF NOT EXISTS` 会把整条跳过、**连 `DEFAULT` 与 `NOT NULL` 一起跳过** —— 而「列已存在但可空、由 `ddl-auto` 建出来」正是「代码先上线环境」的常态（`V4` 的 `version` 列踩过）。脚本文件头点名的「不能这么写」的形态，正是本文档原来写的那个。<br>**② 方向仍是「先跑脚本、再发代码」，但「可提前任意时间跑」不成立**（**2026-09-09 补两条实质约束**，与 `sprint118/README.md` 同口径）：**(a) 必须排在「发版前」那一段** —— `ddl-auto` 在**有数据**的表上**加不出这个 `NOT NULL` 列**（PG 直接拒 `23502`），且它加列时不带实体侧默认值，所以本脚本是唯一把这一列建对的地方；漏跑则新代码每条带 `deleted = false` 的读查询直接 `42703`。**(b) `V11` 跑完到 `V10` 跑完之间有一段无约束窗口** —— 此时索引谓词已是 `status = 'Active' AND deleted = false`，而库里的 `status` 还是旧值 `'Activate'` ⇒ **该部分唯一索引命中零行，「同组织启用维度缩写唯一」在这段时间不受任何约束**（与 `V10` 文件头描述的是同一个窗口，同批执行下以分钟计，`V10` 一跑完即恢复）。（**2026-09-15 起该窗口已无后果** —— 「同组织启用维度缩写唯一」这条不变量整条取消，索引由 `V15` 删除，v4.31）。<br>**③ 与 `V10` 的先后顺序：没有要求**（2026-09-09 定）—— `V10` 第 ③ 步已改为**按库里有没有 `deleted` 列自适应谓词**，故两份谁先谁后、各自重复跑多少遍，**终态都一样**；`V11` **不需要跑第二遍**。<br>**④ 本次确实是纯增量、没有 `V10` 那种「静默空数据」风险**（不改任何现有列的取值，旧代码按 `status` 过滤的热读路径一字未动）—— 这个方向判断没变，只是上面 (a)(b) 两条约束此前漏写了 | §5.1.3 / §10.1 |
| **X12** | **§13-Q24 改判**（原「✅ 已关闭：无条件允许删除，不做前置拦截」）：**拦截现在存在**，但判据是「**是否进入过已发布题库版本**」而不是「**有无历史数据**」，且**保护对象不是那一行**（软删下行不会消失）而是**已发布题库版本的语义** | 2026-09-08 关闭 Q24 的论据是「软删下行不消失 ⇒ 拦截没有保护对象」，**那个论据在真删面前不再成立**：`deleted = true` 的行虽然还在，但它已经从产品里消失且不可恢复，若它同时是某个已发布版本快照里的维度，那份版本就成了「引用着一个用户再也管理不到的维度」的版本。⚠️ **注意判据的差别**：「有无历史数据」会把「有人填过、但题库从没发布过」的维度也拦住（那种维度删掉是安全的 —— 快照按 code 仍解得出名字，而它本就不是任何已发布版本的一部分）；「是否进入过已发布版本」才是真正的边界 | §13-Q24 / §12 / §1.2 / §7.11-④ |

| **X13** | **删除只写 `deleted` 一列，`status` 原样保留**（需求方 2026-09-09 **追加**明确）：删掉一个启用中的维度落库是 `(Active, true)`，删掉一个停用中的维度落库是 `(Inactive, true)` | 两个动作各写一列、互不越界，库里才始终分得清「这行被停用了」与「这行被删了、删之前是启用的」；`status` 若被删除动作顺带改掉，排查时这两种情况长得一模一样。~~⚠️ **在 §7.11-② 的两阶段落库下这是一道主动动作**：`parkAll` 已经把该行落成 `Inactive`，处理 `deletedCodes[]` 时**必须按 `previouslyActive` 把 `status` 显式写回**，只 `setDeleted(true)` 就收工等于让 `parkAll` 决定了 `status`（本版首次实现即漏在此处，已修正 + 补两条单测）。~~ → **2026-09-15 作废**：`parkAll` 已随 `uk_erl_dimension_config_abbr` 一并删除（v4.31 / §7.11-②），没有东西会顺手改 `status` 了 ⇒ 处理 `deletedCodes[]` 就是**只 `setDeleted(true)`、完全不碰 `status`**，那道「按 `previouslyActive` 写回」的补偿动作连同它的两条单测口径一起取消。**本条裁决本身（删除只写 `deleted` 一列）不变**，只是它此后是默认结果、不再是主动动作。⚠️ **代价**：库里会真实存在 `status = 'Active'` 且 `deleted = true` 的行 ⇒ 「已删行不被热读捞出来」**完全依赖读侧都带 `deleted` 这一半**（~~索引谓词 + ~~ 读侧 `AndDeletedFalse`；**2026-09-15：索引谓词那一半随 `uk_erl_dimension_config_abbr` 删除一并消失，「已删行不占缩写」也不再是个需要保证的事**，v4.31），漏掉它这一行就会以启用维度的身份复活 | §5.1.3 / §7.11-② / §11-86-⑱ |
| **X14** ⚠️ **（2026-09-09 实现落地后补记，v4.18 文档订正，非设计变更）** | **① 恢复按钮的文案是 `Activate`，不是 `Restore`**：当日 mockup 把标签定档为 `Activate`（`CIOaas-web/src/pages/exitReadiness/components/constants.ts` 的 `TEXT.activate`），仓库里**没有任何** `Restore` 文案常量 —— 本文档全文写作 ~~`Restore`~~ 的**按钮文案**已一律订正为 **`Activate`**（讲「恢复」这个**动作**时仍用中文「恢复」；前端 handler 名 `onRestore` / 本地标志位 `isRestored` **保留旧词**，它们表达的是标志位翻转、不是屏上的字）。**② 主列表行尾图标是三态，不是「`deletable` ? 垃圾桶 : 电源按钮」二选一**：实际判据是 **`row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`** —— 本次会话里刚从停用区恢复回来的行，**即便 `deletable = true` 也只给电源按钮**，此时它的语义是「**撤销恢复**」，另有三条独立文案 `dimensionRestoredTooltip` / `undoRestoreConfirm` / `undoRestoreOk` 与独立 aria-label `Undo restore`（对照表见本节状态矩阵下方） | ① 屏上没有叫 `Restore` 的东西，文档按 `Restore` 写会让实现、验收用例与 UI 三方对不上（`getByText('Restore')` 直接查不到）。② 三态是**防误删设计**：真删在本页没有恢复入口，而「恢复一行 → 想撤销 → 点到最近的按钮」是一条高频且不可逆的误操作路径；这条此前**只活在代码注释里**，文档不写就会在下一次重构时被当成多余分支删掉 | §0.21 / §7.11-④ / §8.4-C6 / §11-86 |
> **不变的部分**（避免过度解读）：`status` 的**两个取值与全部语义**（`Active` / `Inactive`，含「置 `Inactive` = 行与 `weight` 原样保留、可恢复」）、
> `dimension_code` 的**生成规则与永不改变**（§5.1.3）、~~`dimension_abbr` 的组织内 `Active` 唯一~~（**2026-09-15 整条取消**，v4.31）、**整组替换语义**与
> ~~§7.11-② 的**两阶段落库**（`parkAll` + upsert）~~（**2026-09-15：`parkAll` 删除，改为单阶段直接写终态**）、`savedAt` 乐观锁与 `clientRef` 幂等键、~~`confirmCreateAnyway` 同名软阻断~~（**2026-09-15 连同入参一并删除**）、
> **权重合计只算 `Active` 行 = 100.00**、「保存即全局生效、历史会漂移」（§13-Q21 仍开着）、题库版本化与 Publish（§7.9）、
> §5.1.5 快照表的结构与写入时机、其余 10 张表 —— 一律不动。**本版只改「配置页那一个破坏性动作长什么样、落到哪一列」。**

---

### 0.22 v4.16 → v4.17 修正清单（依据需求方 **2026-09-09** 两条追加裁决：C7 的版本下拉只列已发布版本 + 卡头不显示 `Retired` 灰标）

> **裁决原文口径**：① `/exitReadiness/configuration/history`（C7 题库版本历史）的版本下拉**只显示「已下发」的版本**，草稿不要出现在里面；
> ② 维度卡头 `Test Dimension 002 (TEST002)` 后面那个灰色 `Retired` 标（截图圈定的就是它）**不显示**。
>
> ⚠️ **本版只改这一页「看什么」，不改「有什么」**：接口 25 仍如实返回草稿 + 已发布，接口 26 的 `dimensions[]` 仍是卡片骨架的**唯一**来源，
> 维度卡本身与它的题目**照常整卡展示** —— 「完整回看发布当时那一版」的口径一字不变（**2026-09-07 那次「整卡连题滤掉」的回退依然有效**）。
> **服务端零改动，纯前端。**
>
> ⚠️ **两条裁决合起来的净效果是「C7 与今天的维度配置彻底解耦」**：C7 此前取**接口 23**（当前生效的维度配置）**只**为了算那个灰标。
> 标一撤，这次取数、`QuestionVersionSection.retired` 字段与 `.retiredTag` 样式**同时失去唯一消费方** ⇒ 一并删除。
> 此后 C7 只读接口 25 / 26 的历史快照 —— 少一次请求，页面的 loading / error 也不再被接口 23 的失败牵连。

| # | 变了什么 | 为什么 | 影响章节 |
|---|---------|--------|---------|
| **Y1** | **版本下拉只列 `PUBLISHED`**：接口 25 的出参在**前端取数 hook `useQuestionVersions`** 内按 `status === 'PUBLISHED'` 过滤后才进下拉与默认选中；下拉标签的**草稿那一支删除**（~~`v{n} — Draft (edited {时间})`~~ / ~~`v{n} — Draft (not published yet)`~~，不再可达），只剩「最新已发布 `v{n} — Current (published {日期})`」与「其余已发布 `v{n} (published {日期})`」两支；**默认选中仍是最新已发布版本** | 需求方裁决：C7 是「回看已下发的题库」，草稿还没生效、放进同一个下拉里等于让人以为它是一份在用的版本。⚠️ **过滤刻意不下沉到服务端**：接口 25 如实下发草稿行是「库里到底有没有未发布变更」这件事的**数据来源**（`Publish` 按钮能不能点就取决于它），服务端一旦滤掉，那个判断就没了依据；而 C7 是接口 25 **当前唯一的消费方**，过滤放在页面侧的代价只是一个 `filter` | §6.4（接口 25）/ §8.4-C7 / §10.3 / §11-90 |
| **Y2** | **C7 维度卡头的 `Retired` 灰标不显示**；维度卡与其题目**照常整卡展示**（不隐藏、不过滤、不打标） | 需求方裁决（截图圈定卡头那个灰标）。⚠️ **这不是「回到 v4.11 的过滤」** —— v4.11 走的是「把这类维度整卡滤掉」，本版走的是**另一条路**：**既不滤、也不标**。两条路都能让「灰标」从页面上消失，但只有后者保住「完整回看发布当时那一版」 | §8.4-C7 / §0.17 / §11-90 |
| **Y3** | **§0.17-K1 关闭，取值 = 「整条取消」**：K1 的两个候选取值（① 改判 `status = 'Inactive'` 即隐藏；② 整条取消）中，需求方的裁决等于选了 ②。连带 **K4 的空态 `None of this version's dimensions are in the current configuration.` 一并删除**（过滤取消后它永不可达）；`§8.4-C7` / `§5.1.3` / `§7.11-④` / `§9` / `§11-90` 里那几处「待裁决」注记全部改为**已关闭**并指向本节 | K1 从 v4.11 定档起就没实现过（§8.4-C7 明写「未裁决前不得实现本条」），2026-09-08 改软删后它失去判据、2026-09-09 的 `deleted` 列也不使它自愈（§0.21-X9）。裁决落到「取消」后，**C7 与「今天的维度配置」不再有任何耦合点**，这条规则连同它的空态一起没有了存在理由 | §0.17-K1 / §0.21-X9 / §5.1.3 / §7.11-④ / §8.4-C7 / §9 / §11-90 |
| **Y4** | **C7 撤下接口 23 的取数**：`QuestionVersionSection.retired` 字段、兜底卡上的 `retired: true`、`QuestionVersionHistoryPage.less` 的 `.retiredTag` 一并删除 ⇒ **C7 此后只读接口 25 / 26** | 那次请求与这三处代码的**唯一**目的就是渲染灰标，标撤了它们即成死代码。顺带的收益是页面的 loading / error 不再受接口 23 影响 —— 此前当前维度配置取失败会连带把一页历史快照拖成错误态，而两者在业务上毫无关系 | §8.4-C7 / §10.3 / §11-90 |
| **Y5** | ⚠️ **本版唯一的行为退化：一份都没发布过（库里只有草稿）的组织，C7 是空态** `No published question set versions yet.` —— 不再退回「选中那份草稿」 | 这是 Y1 的直接后果，必须在文档里明说：过滤前「没有已发布版本」时下拉还能落到草稿上、页面有东西看；过滤后该组织的下拉为空、页体走空态。**这不是 bug** —— 新建组织在第一次 Publish 之前本来就没有「已下发的题库」可回看 | §8.4-C7 / §9 / §11-90 |

> **不变的部分**（避免过度解读）：**接口 25 的出入参契约**（仍返回 `DRAFT` + `PUBLISHED`，仍按 `versionNo` 倒序、草稿最前）、
> **接口 26 的出入参契约**（`dimensions[]` 仍是 C7 卡片骨架的唯一来源，仍取 §5.1.5 的发布当时快照，草稿版本仍回退当前 `Active` 集合）、
> 卡头用**发布当时**的 name / abbr、卡片顺序按发布当时的 `sortOrder`、某维 0 题时卡片保留 + `No questions in this dimension for this version.`、
> **`TEXT.retired` 文案本身**（`ErlCard` 维度行与 A4 `DimensionQuestionsCard` 仍按 `status === 'RETIRED'` 打标 —— **本版只撤 C7 这一处**）、
> 历史期次（A1 / A2 / A4 / 雷达图）「已停用维度照常显示 + `Retired` 灰标」的口径（§9 / §7.10-N4 / §11-77）、
> C6 的两个破坏性动作与 `Deactivated Dimensions` 区块（§0.21）、数据模型 11 张表、计分与权限口径 —— 一律不动。
> **服务端一行代码都不用改。**

---

### 0.23 v4.18 → v4.19 修正清单（依据需求方 **2026-09-09** 裁决：F2 ERL Tab 照 Lovable 原型 `/portfolio` 的 ERL Tab 定稿）

> **裁决原文口径**：`/company` 页 ERL Tab 的显示「根据原型页 <https://exit-readiness-hub.lovable.app/portfolio> 中 ERL tab 修改」，
> 并追加一条 **「ERL tab 页面显示数据为当前季度的数据」**。原型该 Tab 的表格是
> `Company / ERL Score / FRL / PRL / BERL / RRL / TRL / Stage / View ›` 九列，**表格上方没有任何筛选控件、列头也没有排序箭头**，
> `Stage` 列只有一枚 Era 徽章（`Exit Era` / `Harvest & Growth` / `Founder Era`），维度列是中性色数字。
> （原型里的 `FRL / PRL / BERL / RRL / TRL` 只是 seed 数据长成那样，**不构成对 §0.10-D1 动态维度列的推翻**。）
>
> ⚠️ **本版只改 F2 这一个 Tab 的前端表现与它自己发的入参，服务端一行代码都不用改** ——
> 接口 20 的出入参契约、`ErlPeriodService` 的缺省期次推导、排序与筛选的**服务端**实现一律不动（撤下的只是界面）；
> 计分口径、权限与 ACL、数据模型 11 张表、其余全部页面同样不动。

| # | 项 | 原设计 | 本版定档 | 影响 |
|---|-----|--------|----------|------|
| **P1** | **F2 的展示期次** | §0.10-R3 / §7.1.2：不传 `period` 时由服务端按**该公司 closed month 所在季度**逐家推导，并明写「**不猜当前自然季度**」 | **F2 成为 R3 的显式例外**：前端**固定传 `period = 当前自然季度`**（`YYYYQn`，**按 UTC 算** —— 与 Java `ErlAssessmentServiceImpl.currentPeriod()`（`ZoneOffset.UTC`，填报页期次下拉的兜底项来源）同口径；用本地时区会让季度交替那十几个小时内 UTC±n 的用户请求一个「还没人能提交」的季度，整表空且无任何报错），**整张表同一期次**，组合层总表由此横向可比。R3 的服务端缺省**原样保留**，只是 F2 不再走它。⚠️ **v4.33 订正（2026-09-15）：F2 的这条例外已被需求方撤回，且撤回一直没回写本文档** —— `useErlPortfolio.ts` 现在**不发** `period`，F2 回到服务端逐公司缺省（`resolvePeriod(companyId, null)`），各行期次因此可能不一致（本表不显示期次，需求方已确认接受）。 | §6.8 / §7.1.2 / §8.4 / §9 / §11-32 |
| **P2** | **F2 的排序与筛选** | §0.10-D15 / §8.4：**列头排序 + 顶部 Stage 下拉与分数区间筛选器**，标注「功能保留」 | **两者全部按原型撤下，F2 成为一张纯展示表**：① 顶部三个筛选控件删除（Stage 下拉 / `Min score` / `Max score`）；② **全部列头的排序器一并删除**（需求方 2026-09-09 圈图追加裁决 —— 原型的表头就没有排序箭头）。接口 20 的 `sortBy` / `sortOrder` / `stage` / `minScore` / `maxScore` 入参与服务端实现**保留不删**，只是 F2 恒不下发；前端的 `sortBy` 白名单函数（`resolveErlPortfolioSortBy`）**随之删除**，hook 里不再有 query 状态。**D15 的「功能保留」在界面层面整条失效** | §0.2-15 / §0.10-D15 / §6.8 / §8.2 / §8.4 / §11-32 / §11-33 |
| **P3** | **F2 的 `Stage` 列** | 渲染 `{stage} · {era}`（Stage 整数 + Era 文字） | **只渲染一枚 Era 徽章**（同色文字 + 该色 10% 薄底），**stage 整数不再显示**；`stage = 0` 仍出灰徽章 `Not yet Stage 1`，`null` 仍出 `—` | §8.4 / §9 / §11-32 |
| **P4** | **`ERL Score` 的展示形态** | 「加权，一位小数」，实现只渲染 `7.2`（无分母） | 一位小数**不变**（原型的整数 `7/9` 是假数据，需求方当日确认按一位小数），但**补上分母**渲染 `7.2/9`；无分数仍是 `—`（**不是 `—/9`**） | §8.4 / §11-32 |
| **P5** | **着色范围** | §8.4 原文只写「ERL Score 与 Stage 按分数着色」，**实现却把维度列也按 Era 上了色** | **回到 §8.4 原文**：着色只给 `ERL Score` 与 `Stage`，**维度列走中性色**（整表七列全是彩字反而看不出重点）；`0`（红底）与 `—`（灰底）的区分**不变**（§7.1 末段的硬要求） | §8.4 |
| **P6** | **期次标签** | 实现把期次逐行挂在公司名后面（`Acme · 2026Q2`） | **整个撤下，页面不出现任何期次文字**。两步走：先因「整表同一期次、逐行标是冗余」改为表格上方标一次（`Showing {period}`），**需求方同日圈图追加裁决把这一行也删掉**。⚠️ **代价（已知并接受）**：§9「用户看到的期次标签必须和数据是同一个期次」在 F2 上**改为靠约定保证**（期次恒为当前自然季度）而非靠界面标注 —— 整表全 `—` 时，用户在本页看不出这是哪个季度的空态，需进 A4（`View ›` 带 `period`）才看得到 | §8.4 / §9 / §11-32 |
| **P7** | **`View` 列文案** | `View →` | **`View ›`**（文字 + 右尖角图标，原型口径）。跳转目标仍取后端下发的 `detailUrl`，**前端不拼路径**（§8.4 该条不变） | §8.4 / §11-57 |

> **本版不动的部分**（避免误读）：接口 20 的出入参一个字段不增不减；服务端的缺省期次推导（closed month → 季度）
> 与「不回退到更早期次」**继续对接口 1 / 17 / 22 及任何不传 `period` 的调用方生效**；
> F2 的公司可见集（§4.3）、服务端 `sortBy` 白名单与 `dimensionColumns[]` 动态列（§0.10-D1）、
> `0` 与 `—` 的语义区分（§7.1 末段）—— 一律不变。

#### 需求方 2026-09-09 对 F2 显示口径的四条确认（**结论：全部维持现状，无代码改动**）

需求方当日就 F2 显示的数据来源提出四条口径，逐条对照实现后的结论：

| # | 需求方口径 | 核实结论 | 备注 |
|---|-----------|----------|------|
| 1 | 显示**当前季度**的数据 | ✅ 符合 | 前端固定发当前自然季度（UTC，§0.23-P1）。⚠️ 后端评估的 `period` 是按公司 closed month 所在季度落的，季度初通常还挂在上一季 —— 此时整表空态属**预期行为**，不回退（§0.10-R3） |
| 2 | 维度 = **Dimension Configuration tab 配置的维度** | ✅ 符合，一处口径差 | 两者同源同表同排序（`erl_dimension_config`，`deleted = false`，`sort_order ASC`，唯一入口 `ErlDimensionConfigService.currentVersion()`）。**差别**：配置页恒带 `includeDeactivated = true`，底部 `Deactivated Dimensions` 区（`status = 'Inactive'`）**照常显示**，而 F2 只出 `Active` 列 —— 这是设计意图（§7.11），但「配置页里看得到的维度」≠「F2 的列」，交接时需说明 |
| 3 | **ERL Score = Σ(维度分 × 占比)** | ✅ 符合，两个既有例外 | 实现是 `Σ(weight × score) ÷ Σ(全部 Active 维度的 weight)`；权重合计恒 100，与该公式等价（除数取权重合计而非写死 100，只为兜住下面例外②的 4 位小数降级值）。例外：① 维度分缺失（未填 / 该维 0 题）→ **按 0 计入，权重照样占在除数上、不做归一化**（**2026-09-15 起改此口径，2026-09-16 改回加权时维持**；v4.4 的「剔除后剩余权重归一化」§0.9-20 已废）；② 权重缺失或合计 ≠ 100 → **静默等权降级** + WARN（§9） |
| 4 | Era 分档：**Founder `(0,4)` / Harvest & Growth `[4,7)` / Exit `[7,9]`** | ✅ 符合，逐个边界一致 | 需求方当日**先后给过两版**：初版写作「Founder = Stage 1–3 / Harvest = Stage 4–6 / Exit = Stage 7–9」，若按字面理解成「先 round 成 Stage 再映射 Era」，会与现实现在 **`3.5 ≤ score < 4.0`** 与 **`6.5 ≤ score < 7.0`** 两段（一位小数下共 10 个取值）结论相反（如 6.7 分：现判 `Harvest & Growth`，Stage 映射法判 `Exit Era`）。**当日订正为上列分数区间口径后，分歧消失** —— `0` 用**开区间排除**在 Founder Era 之外（与 §0.9-18 / §7.3 一致，仍渲染 `Not yet Stage 1`），`4.0` / `7.0` 均为左闭右开，与 `ErlScoreCalculator.eraOf` 逐个边界对得上。§7.3 与 `eraOf` **均不改**；`ErlScoreCalculatorTest.eraIsTakenFromTheScoreIntervalNotFromTheRoundedStage` 继续钉住「按分数区间、不经 Stage 二次转换」 |

> **同日一并确认**：F2 的 `Stage` 列**只渲染 Era 徽章、不显示 Stage 整数**（§0.23-P3 维持）。因此上表第 4 条的分歧在 F2 界面上**看不出来** —— 用户看到的只有 Era 名称。
> 也正因如此，维度列（整数 0–9）永远踩不到那两个分歧区间，**只有加权 `ERL Score` 一列受影响**。

---

### 0.24 v4.19 → v4.20 修正清单（依据需求方 **2026-09-09** 裁决：A4 Score Details 照 Lovable 原型 `/readiness/overall` 重排版，「严格照原型」）

> **裁决原文口径**：`/exitReadiness/scoreDetails`（A4 全维 Score Details）「根据原型页
> <https://exit-readiness-hub.lovable.app/readiness/overall> 重新排版」，并明确 **「严格照原型」**。
> 本版依据是该已发布站 **2026-09-09 的 SSR 实测 + 截图**，**不是** 2026-08-28 那次 chunk 反解（§0.7 的「UI 证据」记的是旧版形态，已同步标注）。
>
> ⚠️ **本版是纯前端排版，接口 22 契约零变更**：出入参**一个字段不增不减**（`header` 出参照常下发，只是页面不再渲染 ——
> 其中 `weightsApplied` 当时仍被基准 Tab 表尾的加权 `Average` 消费 —— **v4.22 起该行已撤下，A4 连它也不再消费**，见 §0.26-Z1），
> 管理端**仍不传 `portal`、一次请求取回双端**（`dimensions[].portals[]`），端切换只在本地换切片、**不重新请求接口 22**；
> `addNewUrl` / `historyUrl` 仍由后端下发、前端不拼路径；数据模型 11 张表、计分口径、权限与 ACL、期次口径 —— 一律不动。
> ⚠️ **但「服务端一行代码都不用改」不准确** —— 同批有**一处非契约的服务端缺陷修复**：`ErlDimensionConverter#fillAddNewUrl`。
> `dimensions[].addNewUrl` 此前被 MapStruct 判成 adder 而**恒发 `null`**，Z9 的 `+ Add New` 依赖它才渲染得出来；
> 这属**出参修复、不是契约变更**（字段本就在契约里，只是从没被填上值）。
>
> ⚠️ **本版推翻两条既有裁决**：**§0.8-12**（2026-08-28「A4 页头补综合分 + Stage 徽章」）与
> **§0.10-D5 的「组合端 A4 需同屏呈现 GSV 与 Founder」**（2026-09-06）。两条都不是功能取消，而是**表现形式**回到原型 ——
> 整体判断留在 ERL Card 与 F2，「同时呈现两端记录」改由「一次取双端 + 药丸切换」满足。

| # | 项 | 原设计 | 本版定档 | 影响 |
|---|-----|--------|----------|------|
| **Z1** | **面包屑层级** | 三级 `Portfolio Companies › {公司名} › Score Details`（§8.4 原文甚至写的是四级，含 `Exit Readiness`） | **两级 `Portfolio Companies › Score Details`** —— 中间**不再夹公司名**，首级回组合公司列表，末级不可点 | §8.4 / §11-57 |
| **Z2** | **页头内容** | H1 `Score Details` + **加权 `Overall Score` `X/9`** + **Era（Stage）徽章**（§0.8-12，2026-08-28 裁决） | **页头只剩 H1 `Score Details`**，分数与徽章**整块删除** ⇒ ⚠️ **§0.8-12 整条撤销**。整体判断改由 ERL Card 与 F2 该行承载（那两处的口径与「必须走同一个 `ErlLevelScorer.computeOverall`」的要求**不变**）；**接口 22 的 `header` 出参保留**，只是不渲染 | §0.8-12 / §6.2.1 / §8.4 / §8.5 / §11-57 |
| **Z3** | **维度的组织形式** | **五张（v4.4 起 N 张）维度折叠卡**，默认只展开第一张，其余收起 | **维度横向 Tab，一次只渲染一维**：标签取 `dimensions[].abbr`，**顺序与张数仍按接口 22 返回**（v4.4-D1 的动态维度口径**一字不变**），默认选中第一项 | §8.4 / §11-58 |
| **Z4** | **基准的位置与文案** | **页尾折叠卡**（徽章 `BQ`），标题 `Benchmarkit & Top GSV Quartile`，默认收起；公司端**整卡不渲染** | **末位 Tab**，标题改原型原文 **`External Benchmarks & Top GSV Quartile`**；⚠️ **卡头徽章 `BQ` 保留** —— 左侧那列「原设计」把折叠卡整块划掉时把它一起带走了，但**原型上仍有这枚徽章、实现也保留**，撤掉的只是「折叠」这个形态，不是徽章；~~卡内多一行说明 `Reference scores recorded for each Exit Readiness dimension (1-9). These feed the dimension radar.`~~ → **2026-09-20 需求方圈图撤下该行说明**（串 `benchmarkCaption` 与 `.caption` 样式一并删除，卡内只剩表格 / 空态）；**该 Tab 仅管理端渲染**（口径不变，只是「整卡不渲染」变成「Tab 不渲染」）。⚠️ **2026-09-09 联调订正**：判据是**端类型**，~~`benchmark == null`~~ **不可作判据** —— 服务端在「公司端不下发」与「管理端但该期次查不到基准记录」两种情况下都发 `null`（`ErlDimensionServiceImpl.buildBenchmarkDimensions` 无记录时 `return null`），前端分不开；按 `null` 判会让**还没录过基准的公司整个 Tab 消失**，连 `Add New` 入口都找不到。无记录时该 Tab 照常在，卡内走空态 `No benchmark records yet.`；组合端切 `Founder` 药丸时该 Tab 只有一句 `External Benchmarks & Top GSV Quartile is recorded by GSV only.`；**卡头右侧按原型加 `+ Add New` / `View history`** → D2 `/exitReadiness/benchmark/add?companyId=` 与 D1 `/exitReadiness/benchmark?companyId=`（⚠️ **这两条前端拼路径是对的** —— 它们是固定站内路由，`BenchmarkPage` / `BenchmarkAddPage` 之间本就这么互跳；维度卡那两个入口仍一律取接口出参，两者不是一回事）。**§8.4「A4 基准 Tab 不是基准页的入口」一句由此作废**。**表格两处按原型定稿（2026-09-09 联调追加，需求方裁决 D1 一并改）**：① 列头 ~~`BENCHMARKIT` / `TOP GSV QUARTILE`~~ → **`EXTERNAL BENCHMARKS` / `TOP GSV QUARTILE`**（⚠️ 当时一并抄来的 ~~`(1-9)`~~ 后缀已于 2026-09-10 去掉，§0.26-Z2）（`BenchmarkDimensionTable` 是 A4 与 D1 共用组件，**D1 的两处一起改**：同一个概念不该在两页两个叫法）；② ~~表尾多一行 **`Average`**~~ → **v4.22 整条作废**（§0.26-Z1：该行已撤下，组件的 `weights` 入参与 `summary` 一并删除；以下原文仅存档）（源串是首字母大写的 `Average`，`.sectionLabel` 带 `text-transform: uppercase`，**屏显 `AVERAGE`** —— 两处写法都对得上，不是笔误）—— 值是**加权**（Σ 维度分 × 该维占比，权重取本接口的 `weightsApplied`），复用 `erlScoring.weightedOverallScore()`（无分维度剔除、其余权重按比例归一化，与 Overall Score 同一套口径），**一位小数**（原型图上的整数 `6` 是它自己对等权平均做了取整；本设计取一位小数，与全域加权分写法一致）、**不带 `/9` 分母**（表尾是综合值，不是某一维的分）。⚠️ **`weights` 为空数组（或不传）时该行整行不渲染** —— 否则会退化成一个标着 `Average` 的等权平均，把「没有权重可用」伪装成一个像模像样的加权值。⚠️ **D1 因此不渲染该行** —— 基准列表出参里没有权重，组件的 `weights` 是可选入参 | §8.4 / §9 / §11-60 |
| **Z5** | **组合端的双端呈现** | §0.10-D5：**同屏并列**两端（两组页头元数据、卡头并列两个分、逐题行并列两个徽章） | **改回 `GSV` / `Founder` 药丸切换**，**`GSV` 在前且默认选中**（原型口径，与 A3 的 `PORTAL_TABS` 顺序相反）⇒ ⚠️ **§0.10-D5 的「同屏并列」作废**。⚠️ **取数一字不变**：管理端仍**不传 `portal` 一次取回双端**，切药丸**只换本地 `dimensions[].portals` 切片、不重发接口 22** —— PRD §3.7「同时呈现 GSV 与 Founder 的记录」由此满足。前端 `DualQuestionRow.tsx` **删除**，改为 `ScoreQuestionRow.tsx` | §0.10-D5 / §4.2 / §8.4 / §9 / §11-59 / §11-60 |
| **Z6** | **提交元数据的位置** | 页级四列元数据栏（组合端两行并列） | **页级元数据栏取消**，元数据**仍渲染在维度卡内**，四格 **`PERIOD` / `SUBMITTED BY` / `ROLE` / `SUBMITTED AT`**（大写小标签）。理由不变且更强：同期次各维可能绑**不同题库版本、不同提交人与时间**（§0.10-R1），页级取不到一份正确的元数据。⚠️ 顺带撤下的还有**元数据栏右侧的 `Question set v{n}` 次级文字**（原型的四格里没有它）—— A4 不再显示题集版本号，A3 页头 / 历史列表 / C7 三处照旧，**「按 `erl_question_config_version_id` 渲染」的口径本身不变** | §8.4 / §9 / §11-61 |
| **Z7** | **题目分组** | 逐题**按 level 分组**，组头带 ✓ 与 `Stopped here` 标记 | **组头整块移除，题目平铺**；level 信息**仍在每题副行** `{eraLabel} · Source: {evidenceSource}` | §8.4 / §11-62 |
| **Z8** | **卡头计数** | `{已答} answered / {总数} questions` | **只报总题数 `{总数} questions`**（原型口径）。「已答数」与「stopped at Level N」**在 A4 上不再呈现**；⚠️ **其它页面（A3 / 历史列表 / ERL Card）不受影响** | §8.4 / §11-58 |
| **Z9** | **卡头按钮** | `Add New` + `View History`，两端都渲染 | **`+ Add New`（原型口径：只在 `GSV` 侧出现**；公司端单端模式照常渲染）+ **`View history`**（**h 小写**，原型原文；~~`View History`~~）。⚠️ **URL 仍一律取接口 22 出参 `addNewUrl` / `historyUrl`，前端不拼路径 —— 这条不变**；为 `null` 时不渲染 | §4.2 / §8.4 |
| **Z10** | **作答徽章** | `Yes` / `No` 两态 | **三态，且不得合并**：`Yes` 绿丸 / `No` 红丸 / **`yesNo === null` 灰圈减号 `Not answered`** —— 「没答」与「答了 No」在逐级解锁模型里是两件事（未解锁 vs 止步于此） | §8.4 / §11-62 |
| **Z11** | **附件 chip** | 只读 chip，仅文件名 | **`{文件名} {体积}` + 下载按钮**，下载走既有 `storageService.getFileLink(fileId)` 现取预签名 GET 链接（**无新接口、无契约变更**）；备注与附件为 `NOTES` / `ATTACHMENTS` 两个**大写小标签块** | §8.4 / §6.7（仅复用，不改） / §11-62 |
| **Z12** | **`Retired` 灰标** | `dimension.status === 'RETIRED'` 时卡头打灰标 | **A4 保留，口径不变** —— §0.22-Y2 撤的只有 C7 那一处，A4 与 ErlCard 维度行照旧（`TEXT.retired` 常量也因此保留） | §0.22 / §8.4 / §11-62 |

> **本版不动的部分**（避免误读）：**接口 22 的出入参一个字段不增不减**（含 `header` / `portals[]` / `addNewUrl` / `historyUrl`）；
> **管理端一次取双端**的取数模型（§6.2.1）与「公司端忽略 `portal`、恒 `FOUNDER`、不下发 `benchmark`」的服务端行为（§4.3）；
> 维度集合动态化（§0.10-D1）、维度级提交（§0.10-R1）、展示期次口径（§0.10-R3 / §7.1.2）、
> A4 的两个入口（F2 `View ›` + 两端 ERL Card 的 `Full View ›`，§0.10-D5）、页级 `+ New` / `View history` 仍不存在、
> 计分口径与 `ErlLevelScorer.computeOverall` 的三处一致要求（改在 ERL Card 与 F2 上校验）、
> 数据模型 11 张表、权限与 ACL —— 一律不变。**本版是纯前端排版，接口 22 契约零变更。**
> ⚠️ ~~服务端零改动~~ **不准确**：同批还有**一处非契约的服务端缺陷修复** —— `ErlDimensionConverter#fillAddNewUrl`
> （`addNewUrl` 被 MapStruct 判成 adder、恒发 `null`，Z9 的 `+ Add New` 依赖它），属**出参修复、不是契约变更**。
> ⚠️ **v4.21 补**：「URL 由后端下发、前端不拼路径」这条不变，但 `addNewUrl` / `historyUrl` 两条 URL 的**取值**
> 在 v4.21 各多一个 query 参数（`&portal=gsv` / `&period=`）—— **「契约零变更」≠「URL 字符串没变」**，别读混，见 §0.25。

---

### 0.25 v4.20 → v4.21 修正清单（**实现落地后的一致性回写**，2026-09-10）

> **本版不是裁决、也不是设计变更**，而是把「文档写的 URL 形状」与「仓库里实际拼出来的 URL」对齐 ——
> 两条都是 A4 维度卡卡头的下发链接（§6 接口 22 / §8.4-A4）。**接口 22 的出入参一个字段不增不减**，
> 数据模型 11 张表、计分口径、权限与 ACL、期次口径（§0.10-R3 / §7.1.2）—— 一律不动。
>
> ⚠️ **两条改的都只是「值」，不是「字段」** —— `addNewUrl` / `historyUrl` 仍由后端算好整条下发、
> 前端仍**不拼路径**（拼出来的动态 URL 仍要过 `isInternalPath`，§0.24-Z9 / Z4 那条对照说明照旧）。
>
> Z1 是**补记**：该改动 2026-09-10 已随 A4 原型收尾一并落地，当时漏了回写；Z2 是本次改动。

| # | 项 | 原文档写的 | 本版定档 | 影响 |
|---|-----|-----------|----------|------|
| **Z1** | **`addNewUrl` 的卷别** | `/exitReadiness/assessment?companyId={id}&period={period}&dimension={code}`，**不带端别** | 追加 **`&portal=gsv`** —— **判据是「这张卡装的是哪一卷」，不是「调用者是哪个端」**：双端模式下 A4 的 `+ Add New` 按原型只在 `GSV` 药丸下渲染（§0.24-Z9）故给 GSV 卷，单端模式下跟着所看的 `portal` 走；**公司端恒 Founder 卷、恒不带**（带上会被接口 3 的端类型校验拒掉，§4.3）。⚠️ 若判据改用「调用端」，管理端显式请求 `portal=FOUNDER` 时会出现「卡里是 Founder 数据、链接指向 GSV 卷」。⇒ 从 `GSV` 药丸点 `+ Add New` 落地的是 **B2 GSV 卷**，填报页页头显示 `{维度} — GSV Validation` | §6（接口 22）/ §8.4-A4 / §11-79 |
| **Z2** | **`historyUrl` 的期次** | `/exitReadiness/history?companyId={id}&dimension={code}`，**不带期次** | 追加 **`&period={period}`**，**期次空白时整段不拼**（与同处 `addNewUrl` 同款判空）。⚠️ **B3 自己不按期次过滤** —— 历史列表跨期次全量，该参数**不参与取数**，纯粹是 B3 面包屑「Score Details」那一级回 A4 的**返回上下文**：不带时那一级拼不出 `&period=`，A4 走服务端缺省期次（closed month 所在季度，§0.10-R3）打开**另一期**，而不是用户来时那一期。<br>· **上游三个入口一并透传**：① A4 卡头 `historyUrl`（后端补，即本条）；② A2 维度页 `View history`；③ B 填报页**提交成功后**跳 B3 的那一跳。<br>· **B3 → 详情页 → 回 B3** 这一跳同样接上（列表页行链接透传 `period`、详情页面包屑回拼），否则进一次详情页期次上下文照样断。⚠️ **该跳只补了 `period`、没有补 `dimension`** —— 从详情页返回落到的仍是**全维混排**的 B3（`?dimension=` 过滤态不保留），这一层**本版不处理** | §6（接口 22）/ §8.4-A4 / §8.4-B3 详情 / §11-8 / §11-79 |

> **本版不动的部分**（避免误读）：接口 22 / 接口 7 / 接口 8 的出入参**一个字段不增不减**；
> B3 历史列表「跨期次全量、`dimension` 才是真过滤」的口径（§0.10-D12）；服务端缺省期次口径（§0.10-R3）；
> A4 自身的排版、药丸与取数模型（§0.24 全节）；B3 列表页 2026-09-10 那次原型改版本身的口径 —— 一律不变。

---

### 0.26 v4.21 → v4.22 修正清单（**需求方 2026-09-10 圈图**）

> 需求方在 A4 末位基准 Tab 上圈掉了表尾那行 `AVERAGE`。**纯前端一行表尾的撤下**：服务端零改动，
> 接口 22 出入参**一个字段不增不减**，数据模型 11 张表、计分口径、权限与 ACL、期次口径 —— 一律不动。

| # | 项 | 原设计（v4.20 / §0.24-Z4） | 本版定档 | 影响 |
|---|-----|---------------------------|----------|------|
| **Z1** | **A4 基准 Tab 的表尾 `AVERAGE` 行** | 表尾多一行 `Average`（`.sectionLabel` 转大写，屏显 `AVERAGE`），值是加权 Σ(维度分 × 该维占比)、一位小数、无 `/9` 分母；权重取接口 22 的 `weightsApplied`，为空数组时整行不渲染 | **整行撤下** —— 基准 Tab 只剩按维度的明细行。连带：**`BenchmarkDimensionTable` 的可选入参 `weights` 与整个 `summary` 一并删除**（A4 是它唯一的调用方，D1 与基准记录详情页 `/exitReadiness/benchmark/record/:recordId`（§8.1 路由表未列，属存量缺口）本就不传，留着就是个没有调用方的开关）；`BenchmarkPanel` 的 `weights` 入参、`ScoreDetailsPage` 传的 `weights={data.weightsApplied \|\| []}` 同批删除。⚠️ **`erlScoring.weightedOverallScore()` 代码保留、但前端自本版起零调用方** —— 它是 §7.1 加权口径的前端实现（函数注释写明「草稿期本地即时预览用，权威值取后端返回」），**ERL Card（`ErlCard.tsx`）与 F2（`ErlTab.tsx`）从来不调它**、一律直接渲染后端下发的 `overallScore`；删掉表尾后它只剩 `erlScoring.test.ts` 在用。⚠️ **不要据此以为「删了这行就动了计分口径」** —— 服务端加权口径（§7.1）一字未动。该函数的去留已登记在 `CIOaas-web/docs/待优化项.md`，本版不处理 | §0.24 / §0.24-Z4 / §6（接口 22 `header`）/ §8.4-A4 基准 Tab / §8.4-D1 / §10.3 / §11-60 |
| **Z2** | **两个分数列头的 `(1-9)` 后缀**（**补记** —— 2026-09-10 先前已随实现落地，当时漏回写，本版补齐文档） | 列头 `EXTERNAL BENCHMARKS (1-9)` / `TOP GSV QUARTILE (1-9)`（2026-09-09 照原型抄来，§0.24-Z4-①） | **去掉 `(1-9)` 后缀** —— 值域由每格的 `/9` 分母表达，列头不重复说一遍（需求方 2026-09-10 圈图）。组件三处共用 ⇒ **一起去**。⚠️ ~~**卡内那句说明 `Reference scores recorded for each Exit Readiness dimension (1-9). These feed the dimension radar.` 里的 `(1-9)` 保留** —— `constants.ts` 该串未动，去掉的只有列头~~ → **2026-09-20 整句说明已撤下**（需求方），这条保留意见随之作废；列头去 `(1-9)` 的结论不变 | §0.24-Z4 / §8.4-A4 基准 Tab / §8.4-D1 / §10.3 / §11-60 |

> **本版不动的部分**（避免误读）：接口 22 的 `header.weightsApplied` **照常下发**（契约零变更，其它调用方仍在用），
> 变的只是 **A4 不再消费它** —— 加上 v4.20 已停渲染的 `overallScore` / `stage` / `era`，**A4 此后 `header` 一项都不用**；
> 列头 `EXTERNAL BENCHMARKS` / `TOP GSV QUARTILE`、每格的 `/9` 分母、空态 `No benchmark records yet.`、
> 卡头 `+ Add New` / `View history`、Tab 按端类型显隐与 Founder 侧那句 `... is recorded by GSV only.` —— 一律不变。

---

### 0.27 v4.22 → v4.23 修正清单（**需求方 2026-09-10 决定：基准允许同期次重复录入**）

> 基准（D 模块）原先是「一期次至多一条」：服务端 `ErlBenchmarkServiceImpl.assertPeriodNotTaken` 拦重复、
> 数据库唯一索引 `uk_erl_reference_score (company_id, period)` 兜底。需求方 2026-09-10 决定**取消该限制** ——
> 同一 `(company, period)` 可重复添加（peer set 换了、口径改了要重新录一份，属正常路径）。
>
> **改的只是「能不能重复」这一件事**：D 模块的页面结构、录入表单、维度动态化（§0.10-D1）、值域 1–9、
> 「外部输入、平台不计算」（PRD §4）、基准不参与综合分与 Perception Gap —— 一律不变。
>
> ⚠️ **本版是 ERL 唯一一次「放开」数据库约束**，代价全在 Z2：**没有数据库级「至多一条」保证了** ——
> 读侧每一处取「最新 / 适用」都必须用同一排序键，漏一处就会出现「雷达图基准环与 D1 的 `LATEST` 指向两条不同记录」，
> 而且**不报任何错**。

| # | 项 | 原设计 | 本版定档 | 影响 |
|---|-----|--------|----------|------|
| **Z1** | **「一期次至多一条」的两道限制** | ① 服务端 `assertPeriodNotTaken` 命中即 `BadRequestException("A benchmark record for this period already exists.")`；② 数据库唯一索引 `uk_erl_reference_score (company_id, period)` 兜底 | **两道一并删除** —— ① 该私有方法与它依赖的 `findByCompanyIdAndPeriod` 一起删（同期次重复提交**不再是错误路径**，照常落库为新的一条记录）；② 唯一索引改为**同键位的普通索引** `idx_erl_reference_score_company_period`（新增迁移 `sprint118/V13__erl_reference_score_drop_period_unique.sql`；`V1__erl_init.sql` **就地改为直接建普通索引** ⇒ 全新环境跑 V13 是 no-op；⚠️ **`V5`（2026-09-08 存量迁移）未改**，它仍会建出唯一索引 ⇒ 同批执行时 V13 **排在 V5 之后**）。⚠️ **发版顺序：先跑脚本、再发代码**（或同批）—— 反方向 = 新代码已不拦重复而库里唯一索引还在，用户重复添加由 400 变成唯一约束冲突的 **500**；先跑脚本这个方向不炸（旧代码仍在服务端拦重复，只是少了数据库兜底） | §5.6 / §6（接口 16）/ §8.4-D2 / §9 / §10.1 / §11-37 |
| **Z2** | **读侧「最新一条 / 适用记录」的判据** | 「适用记录」= `period ≤ 当前展示期次` 中 `period DESC` 的第一条；`latest` 卡 = 记录表 `period` 最大的那条 —— 单键排序即确定，因为唯一索引保证了「同期次至多一条」 | 一律改判 **`period DESC, created_at DESC, id DESC` 的第一条**（`id` 是同一微秒的平局兜底），与 §5.2 评估 SOT 的 `submitted_at DESC, id DESC` **同源**。两个读方法都在 `ErlReferenceScoreRepository`：`findByCompanyIdOrderByPeriodDescCreatedAtDescIdDesc`（D1 列表 + `latest` 卡）与 `findFirstByCompanyIdAndPeriodLessThanEqualOrderByPeriodDescCreatedAtDescIdDesc`（ERL Card / 维度页 / A4 的适用记录）。⚠️ **代价**：没有数据库级保证兜底 ⇒ **读侧每一处都必须走这两个方法**，各处自己拼查询会在同期次多条时选出不同的一条（雷达图基准环取 A、D1 的 `LATEST` 落在 B），而两处各自看都「正常」 | §5.6 / §7.8 / §6（接口 15 `latest`）/ §6.2（`benchmarkPosition`）/ §6.2.1（A4 `benchmark`） |
| **Z3**（⚠️ **排序键已于 v4.40 再次改判为 `created_at DESC NULLS LAST, id DESC`**，本行留作历史） | **D1 `Record History` 的展示排序与 `LATEST` 徽章** | 按 `period` 倒序，首条 `isLatest = true` | 同一排序键 **`period DESC, created_at DESC, id DESC`** —— 同期次多条**并列展示、不合并不去重**，最近录入的排前面，`LATEST` 徽章只给这个排序下的**首条**。⚠️ `isLatest` 仍是**服务端派生、不落列**（与已删的 `erl_assessment.is_latest` 无关，§6.5 的 2026-09-08 澄清照旧）。⚠️ **D3 记录详情页 `/exitReadiness/benchmark/record/:recordId` 不受影响** —— 它按 `id` 打开，同期次多条各有自己的 `id` | §6.5 / §8.4-D1 / §11-35 / §11-38 |
| **Z4** | **前端的「期次已存在」报错文案** | D2 把后端那句 `A benchmark record for this period already exists.` 挂在 `Period` 字段下（文案常量 `constants.ts` 的 `benchmarkPeriodExists`） | 该报错**再无触发路径**（后端已不返回这句）。该常量**本就没有任何调用方**（D2 直接渲染后端返回的 message），**已随本版从** `CIOaas-web/src/pages/exitReadiness/components/constants.ts` **删除**（删的是一个无人引用的残留串，不影响行为）。**前端其余改动只有注释**（D2 页头、`.less`、`erlApi.ts` 里「期次重复」的口径改为「同期次可重复添加」） —— D1 的排序由后端给定，D2 表单与校验一字未改 | §8.4-D2 / §9 / §10.3 |

> **本版不动的部分**（避免误读）：接口 15 / 16 的出入参**一个字段不增不减**（`latest` / `records[]` / `isLatest` 照旧下发）；
> `erl_reference_score_item` 的唯一约束 `uk_erl_reference_score_item (erl_reference_score_id, dimension_code)` **保留**
> —— 一条记录内仍是**一维一行**、且必须齐当前 `status = 'Active'` 的全部维度（§5.6.1），放开的只有主表的期次；
> D2 的其它校验（`2 × 维度数` 个分数框全必填、范围 1–9、~~最多一位小数~~ → **v4.34：只允许整数**、`Period` 归一为 `{YYYY}Q{n}`）；
> §7.8 的「基准向前沿用」与「基准不参与综合分 / Perception Gap」；两个接口**仅管理端可调**与公司端裁剪 —— 一律不变。

---
### 0.28 v4.23 → v4.24 修正清单（**需求方 2026-09-10 决定：后端补真实录入时刻**）

> D1 `Record History` 那一列的列头 2026-09-10 已按原型由 `RECORDED` 改成 **`SUBMISSION TIME`**，
> 而下发的值一直是 `ErlBenchmarkServiceImpl#periodEndDate` 由 `period` 推出来的**期末日**
> （`2026Q3 → 2026-09-30`，`LocalDate`，**不是存储列**）—— **与谁在什么时候录入无关**：
> 同期次两条显示完全相同，且与 `PERIOD` 列 100% 冗余。改名把原先含糊的说法变成了明确的错误断言，
> v4.23 放开「同期次可重复录入」之后更扎眼 —— 屏上会出现 `PERIOD` 与 `SUBMISSION TIME` **两列都一模一样**的多行，
> 真实先后只体现在行序与 `LATEST` 徽章上。
>
> 本版把这一列**改成它列头说的那个东西**：下发审计列 `created_at`。
>
> ⚠️ **这不是数据模型变更** —— `created_at` 是 `AbstractCustomEntity` 本来就带的审计列（§5 前言），
> **表结构零变更、没有新的迁移脚本**；接口 15 的字段**只改类型与语义、不增不减**。
> D 模块的页面结构、录入表单、维度动态化、值域 1–9、读侧排序键（§0.27-Z2 / Z3）—— 一律不变。

| # | 项 | 原设计 | 本版定档 | 影响 |
|---|-----|--------|----------|------|
| **Z1** | **接口 15 出参 `recordedAt` 的取值与类型** | 由 `period` 推导为**期末日**（`2026Q2 → 2026-06-30`），私有方法 `periodEndDate` 现算、不落列，Java 类型 `LocalDate`（§7.8） | 取审计列 **`erl_reference_score.created_at`** 的**真实录入时刻**，Java 类型改 **`Instant`**、序列化为 **ISO-8601 串**（`ErlBenchmarkDTO.recordedAt` 与 `ErlBenchmarkRecordResponse.recordedAt` 同改）。`periodEndDate` 与它专用的常量 `MONTHS_PER_QUARTER` **一并删除**；`PERIOD_PATTERN` **保留** —— 它的唯一用处是写入前把 `period` 复核成 `{YYYY}Q{n}`（接口 16，§6.5）。历史行 `created_at` 为空 ⇒ **下发 `null`**（前端 dash），不拿期末日兜底。<br>⚠️ **只删 `ErlBenchmarkServiceImpl` 里那份 `MONTHS_PER_QUARTER`** —— `ErlAssessmentServiceImpl` / `ErlPeriodServiceImpl` 各有同名常量、算的是「当前日历季度」（§7.1.2），与本条无关，**不要跟着删**。<br>⚠️ **排序键本来就用的是 `created_at`**（§0.27-Z2），本版只是把同一列也拿来**展示** —— 展示位与行序从此同源、不会互相打架 | §5.6 / §6.5（接口 15）/ §7.8 / §8.4-D1 / §11-35 / §11-37 |
| **Z2** | **前端三个展示位的取值与格式** | 后端给的是 `LocalDate` 串，三处**直出原串**（`record.recordedAt \|\| '—'`） | 三处一律走 **`formatErlIsoDate()`** → **`YYYY-MM-DD`**（如 `2026-06-30`；需求方 2026-09-10 定的写法。**新开的第三个格式函数** —— 域内既有 `formatErlDate`（`Jun. 30, 2026`）与 `formatErlDateTime`（`D MMM YYYY, HH:mm`）都不是这个写法，基准页三处独用它，别把 A4 `SUBMITTED AT` 等到分的位置跟着改）：① D1 卡二 `Record History` 的 **`SUBMISSION TIME`** 列；② D1 卡一卡头下的 **`BenchmarkSubmissionMeta`**（`Submitter` / `Submission time` 一行）；③ **D3 记录详情卡**内的同一个组件。为空显示 dash（该函数自带空值分支，不用各处再判一遍）。<br>⚠️ **只到日的代价**：同一天录入的同期次多条在屏上仍然一模一样，先后只体现在行序与 `LATEST` 徽章（要分辨到分钟得改回到分的格式）。<br>⚠️ 顺带清掉 `CIOaas-web/docs/待优化项.md` 里「基准两页的时间位是 ERL 全域**唯一**漏走 `formatErl*` 的地方」那笔账的 **① 子项** | §8.4-D1 / §8.4「D1 / D3 提交元信息行」/ §10.3 |
| **Z3** | **列头与标签文案** | 列头 `RECORDED`（v3.1 起）→ **2026-09-10 按原型改名 `SUBMISSION TIME`**（该次 D1 三列改版本身尚未回写本文档，见 §8.4-D1 的追注） | **文案一字不改** —— 本版改的是**值**，不是说法。`BENCHMARK_META_LABELS.submissionTime`（D1 列头与 D1 / D3 元信息行**同取**的那一份源串）保持 `Submission time`；它 docstring 里「目前绑的是期末日、不是提交时刻」那条告警随本版删除。⚠️ **不要退回 `PERIOD END` 之类「不撒谎但没用」的说法** —— 需求方选的是「后端补真实时刻」这一支 | §8.4-D1 / §10.3 |

> **本版不动的部分**（避免误读）：接口 15 的其它出参（`latest` / `records[]` / `isLatest` / `recordedBy` /
> `benchmarkitAvg` / `topQuartileAvg` / `note` / `dimensions[]`）与接口 16 的出入参 —— **一个字段不增不减**；
> 读侧「最新一条 / 适用记录」的排序键 `period DESC, created_at DESC, id DESC`（§0.27-Z2 / Z3）；
> `erl_reference_score` / `erl_reference_score_item` 的表结构与约束（**含 `created_at` 本身**）；
> D2 表单与校验；期次显示口径 `formatErlPeriod()`（`Q3 2026`）；`recordedBy` 仍由 `created_by` join 用户表得到 —— 一律不变。

---

### 0.29 v4.24 → v4.25 修正清单（**2026-09-10 缺陷：D1 面包屑回 A4 落到缺省期次**）

> **现象**：D1 基准页（`/exitReadiness/benchmark`）面包屑 `Portfolio Companies › Score Details › Top GSV Quartile & External Benchmarks`，
> 点第二级「Score Details」回 A4 时期次变成 **`Q4 2025`**（服务端缺省期次 = closed month 所在季度），不是用户来时那一期。
>
> **根因**：期次上下文在 **A4 → D1 这一跳**就断了 —— D1 的面包屑第二级本来就写了「URL 上带了 `period` 就带回去」，
> 但**上游从来不给**：A4 基准 Tab 的两个入口只拼 `?companyId=`，后端下发的 `benchmarkUrl` 也只拼 `?companyId=`，
> 于是 A4 走 `ErlPeriodService.resolveDefaultPeriod`（§0.10-R3）。与 v4.21-Z2 修的「B3 面包屑回 A4 恒落缺省期次」
> **是同一类问题、同一条链的另一段**。
>
> **口径（本版的定盘星）**：期次在 D 模块**只作面包屑 / 返回按钮的返回上下文，各页取数一律不用它** ——
> D1 `Record History` 跨期次全量、D1 卡一取「最新一条」、D3 按 `recordId` 打开、D2 的期次由表单自己填，
> 四处都不按 URL 上的 `period` 过滤。⚠️ 因此 v4.21 之前文中那句「透传期次是它用不到的参数」**不是理由** ——
> 页面用不到，**面包屑要用**；不带就等于把用户甩到另一期。
>
> ⚠️ **本版无设计变更、无契约变更**：`benchmarkUrl` 改的是**取值**、不是字段（接口 1 出入参一个字段不增不减），
> 数据模型 11 张表、计分口径、权限与 ACL、服务端缺省期次推导（§0.10-R3 / §7.1.2）—— 一律不动，
> **无数据库改动、无迁移脚本**。

| # | 项 | 原文档写的 | 本版定档 | 影响 |
|---|-----|-----------|----------|------|
| **Z1** | **A4 基准 Tab 两个入口的期次** | `+ Add New` → `/exitReadiness/benchmark/add?companyId=`、`View history` → `/exitReadiness/benchmark?companyId=`，**都只带 `companyId`**（§0.24-Z4 定这两个按钮时的写法） | 两条一律追加 **`&period=`**（期次空则整段不拼、值走 `encodeURIComponent`）。⚠️ **传的是 `shownPeriod`（= `data?.period \|\| URL 上的 period`）、不是 URL 原参** —— URL 没带期次时（如从 F2 `View ›` 之外的入口、或直接贴地址）**后端解出来的那一期才是本页真正在看的那一期**，拿 URL 原参会拼出空串、断点照旧。组件层面为 `BenchmarkPanel` 新增 `period` prop，由 `ScoreDetailsPage` 传入。⚠️ **这里前端拼路径是对的** —— 与维度卡的 `addNewUrl` / `historyUrl`（后端按维度算、属动态 URL、必须过 `isInternalPath`，§0.24-Z9）不同，D1 / D2 是两条编译期固定的站内路由 | §8.4-A4 基准 / §10.3 / §11-38a / §11-79-⑤ |
| **Z2** | **D1 三条出链的期次** | 面包屑第二级 `Score Details` 回 A4 **已带** `periodQuery`（2026-09-10 D1 改版时就写了）；到 D2 的 `addUrl` 与到 D3 的 `recordUrl` **不带** | 抽出一份 `periodQuery`，**三条链接共用**：`addUrl`（→ D2）与 `recordUrl(id)`（→ D3）一并带上，`scoreDetailsUrl`（→ A4）照旧。⚠️ **D1 自己不按期次过滤**（`Record History` 跨期次全量，§0.10-D12 同款口径），带上纯粹是为了让下游把上下文再传回来 | §8.4-D1 页头 / §8.4「D1 / D3 / D2 的期次返回上下文」/ §11-38a |
| **Z3** | **D3 记录详情页的返回链路** | 面包屑第二级与右上 `Back` 回 D1 时**只带 `companyId`** | 从路由参数取 **`contextPeriod`**，面包屑与 `Back`（两处：正常态与错误态）回 D1 时都带上。⚠️ **与本页「展示」的期次是两件事** —— 屏上标题、面包屑末级、卡头 `By Dimension · {period}` 一律取**记录自身的 `record.period`**（该记录属于哪一期是它自己的事实），`contextPeriod` 只往回传、**不参与本页任何展示与取数**，两者不要混 | §8.4「D1 / D3 / D2 的期次返回上下文」/ §11-38a |
| **Z4** | **D2 保存成功后的落点** | 保存成功 `history.push` 回 D1，**只带 `companyId`** | 带上 `contextPeriod`（同款判空）。⚠️ **`Back` / `Cancel` 不受影响** —— 它们走 `history.goBack()` 原路退回（进本页时是 `PUSH` 才用 `goBack`，直接贴 URL 进来的落到 D1，§8.4-D2），退回去的那一页 URL 本来就是对的 | §8.4-D2 校验与返回 / §11-38a |
| **Z5** | **后端 `benchmarkUrl` 的期次**（A1 ERL Card 下发，站内进 D1 的**另一个**入口） | `ErlCardServiceImpl` 里两处都写常量拼接 `"/exitReadiness/benchmark?companyId=" + companyId`，**不带期次** | 抽出私有方法 **`benchmarkUrl(companyId, period)`**，期次非空则追加 **`&period=`**（写法与 `ErlDimensionServiceImpl#historyUrl` 一致，即 §0.25-Z2 那套判空），**正常卡与空态卡两个 build 点都改**。⚠️ **改的是取值、不是字段** —— 接口 1 的 `benchmarkUrl` 仍是「后端算好整条下发、仅管理端下发」（§0.10-D7），前端不拼路径 | §6.1（接口 1 `benchmarkUrl`）/ §6.5（D1 页面入口）/ §8.4-A1 / §11-38a / §11-79-④ |
| **Z6** | **相关用例的判词** | D1 用例「**URL 上的期次不透传给 D3**」（当时按「D3 用不到期次」写的）；D3 用例同款 | **两条整条改判**：D1 改为「**透传给 D3 与 D2，且面包屑带回 A4**」；D3 改为同款，并补一条「**URL 没带期次时不拼空 `&period=`**」；A4 `ScoreDetailsPage.test.tsx` 新增一条「基准 Tab 两个入口带上本页期次」。⚠️ 旧判词的依据是「D3 取数用不到期次」—— 事实没错、结论错了（返回上下文要用），属本版推翻的口径 | §11-38a / §11-79 |

> **本版不动的部分**（避免误读）：接口 1 / 15 / 16 / 22 的出入参**一个字段不增不减**；服务端缺省期次推导
> （closed month → 季度，§0.10-R3）与 `ErlPeriodService` 的实现；D1 `Record History` 跨期次全量、D1 卡一「最新一条」的
> 排序键（§0.27-Z2 / Z3）、D3 按 `recordId` 打开、D2 表单与校验、`recordedAt` 的取值与格式（§0.28）—— 一律不变。
> ⚠️ **A4 → D1 → D3 这条链上的「其它上下文」仍不透传** —— 与 §0.25-Z2 的已知口径一致：只补 `period`，
> A4 当前选中的维度 Tab 与药丸（`portal`）返回后回到缺省态，这一层**本版同样不处理**。


---

### 0.30 v4.25 → v4.26 修正清单（**需求方 2026-09-10 口径：Reset 之后要拿到最新的题库**）

| # | 主题 | 原口径 | 新口径（v4.26） | 影响面 |
|---|------|--------|----------------|--------|
| **Z1** | **Reset 后的题库版本** | Reset 只清答案 + 复位 `unlocked_level` / `level_score` / `terminated_level` 三列，**草稿行保留、版本绑定一个字不动**（§6.3 / §9） | **清完答案后改绑到当时最新的已发布版本** —— `erl_question_config_version_id` 与 `erl_question_config_dimension_version_id` **同一时刻一起写**（只写一个会让读侧的批次一致性校验回退到复合键并打 WARN） | §6.3 / §7.9-⑤ / §7.10-N3 |
| **Z2** | **这是修复，不是新口子** | §7.9-⑤ 早就把换题集的正路写成「**Reset 丢弃旧草稿 → `Add New` 重新发起**，新草稿创建时绑定当时最新的已发布版本」 | 那条正路**自上线起就是断的**：实现按 §6.3 / §9 选了**保留草稿行**，`findOrCreateDraft` 于是永远命中旧行、走不到「创建时绑定最新版本」的分支 ⇒ Reset 完再 `Add New` 拿到的还是旧题集。本版是把它接通，**不是**改回「Reset 删行」（§7.7 那条口径仍作废） | §7.9-⑤ |
| **Z3** | **与「升级按钮」禁令的关系** | §7.10-N3：**不做**「在填评估升级到最新题集」按钮 —— 理由是「等于把已删除的重基（rebase）又请回来」 | **禁令不变，但它禁的是「保着答案换题面」**。Reset 改绑发生在答案**全部删除之后**，没有任何跨版本迁移作答的动作 —— 「答案与题面永远自洽」这条硬保证一字未破。这是它相对 rebase 唯一但决定性的安全点 | §7.9-⑤ / §7.10-N3 |
| **Z4** | **两个边界** | — | ① 该组织当下**没有任何已发布版本**（`currentPublished()` 空）⇒ **保持原绑定**，该列是 NOT NULL、且没有比「继续用原来那版」更好的选择；② **已经绑的就是最新版** ⇒ 两列都不动，也不白查一次逐维快照 | §6.3 |
| **Z5** | **提示与前端** | 改绑前 `hasNewerQuestionSet = latestPublishedVersionNo > questionVersionNo` 恒为 `true`，提示一直在（~~banner~~ → 2026-09-15 起是强阻断弹窗） | 改绑后两个版本号相等 ⇒ **提示自然消失**：Reset 成功后本来就 `await load()` 重拉接口 3 并整份重建题目列表（`useAssessmentDraft`），新题集自动生效。~~**前端零改动**~~ → **2026-09-15 作废**：弹窗那一支的 `Access new question library` 本身就是新写的前端代码（它走的正是这条 Reset 路径） | §0.10-D10 / §8.4 |

**接口契约零变更、无数据库改动、无迁移脚本。** 接口 28 的出参仍是 `assessmentId` / `unlockedLevel` / `answeredCount` 三个字段。

**同批确认的两条现状（无需改动）**：① ~~「填写自动保存成草稿」已成立 —— 前端改动后 debounce 1.5s 批量增量 POST 接口 4~~ → **整条作废**（需求方 2026-09-14 裁决取消自动保存、2026-09-15 再裁决收敛到两个按钮，v4.30）：**接口 4 只由 `Save as draft` / `Submit` 触发**，草稿期的解锁推进走**接口 29**（只算不存）—— 口径改为**「没点保存就是没保存」**；② 「没提交前允许修改」已成立 —— 整页只读的唯一判据是 `status === 'SUBMITTED'`，而接口 3 只查 `DRAFT` 行。已知的两处**局部**禁用是设计使然、不在本条范围内：踩到 `No` 之后那一级 `state = 'BLOCKED'` 只读（§7.2 终止语义），以及未作答的题其备注 / 附件禁用（接口 4 的 `yesNo` 必填）。

---

### 0.31 v4.56 → v4.57 修正清单（**ERL Gap Analysis 开发落地回写**，2026-09-18；依据 `erl-gap-analysis-dev-design.md` §0.1 / §0.2）

| # | 主题 | 原口径 | 新口径（v4.57） | 影响面 |
|---|------|--------|----------------|--------|
| **Z1** | **ERL 附件的空间归属**（**推翻既有裁决**） | §13-Q10 的建议：**沿用现有端类型规则**（公司端上传 → 公司空间；管理端上传 → 组织空间），**与 chatbot 一致、不为 ERL 单开空间** | **改判为「单开」** —— 业务关联组合键里的 `business_type` 由 `APP_COMPANY` / `ADMIN_COMPANY` 换成 **`ERL_ATTACHMENT`**（**端与粒度一字不改**：`APP` 仍按 `company_id`、`ADMIN` 仍按 `organization_id`）。`business_association_space_id()` 把 `business_type` 拼进 uuid5 组合串 ⇒ 换一个取值即派生出全新关联行、全新 space，与 chatbot 的空间**天然不相交**，检索侧**一行过滤都不用加** | §13-Q10 / §6.7 / §9 |
| **Z2** | **为什么隔离必须落在 space 维度**（Z1 的成立依据，**不是可选项**） | 直觉上「把登记行的 `business_type` 从 `KNOWLEDGE_BASE` 改掉，chatbot 就检索不到了」 | **该直觉不成立**：chatbot 的 `search_knowledge_base` 调 `recall()` **不传 `mode`**，space 由 `find_chat_space_id` / `find_app_space_ids` 按**组合键**定位，chunk 层的 where 里根本没有 `business_type`；按 `business_type` 圈定的那条 `list_kb_space_ids` 分支要 `mode` 非空才触发、**生产无调用方**。⇒ **只改 `business_type` 而不换 space，chatbot 照样检索得到**。反向确实成立的只有 **Memory 面板**（`list_kb_entry_scopes`）与**知识库面板**（`_kb_documents_query`）—— 这两处真的按 `business_type = 'KNOWLEDGE_BASE'` 过滤，换了取值即自动排除 | §6.7 / §9 |
| **Z3** | **附件的处理深度** | 走**完整入库链路**：`ingest_kb_file` → 登记 → `start_vectorization`（分片 + embedding + 写 `ai_rag_ent_kb_chunk`，摘要另存一条 `chunk_kind=summary` 分段），见 §6.7 第 ⑤ 步 | **新处理类型 `SUMMARY_ONLY`**（与 `STANDARD` 并列的一条处理管线，不是 `STANDARD` 上的开关）：loader 提取全文 → 直接出摘要，**不分片、不向量化**，`ai_rag_ent_kb_chunk` **零行**、`chunk_count = 0`。正文落 `ai_rag_entry.content_text`（**截断 1,000,000 字符**，`char_count` 记真值、超限打 WARN），摘要落 `.summary` —— **Goldie 唯一消费的就是摘要**。「抽不出内容即判 `FAILED`」这道安全网**在两条管线上都保留** | §6.7 / §9 |
| **Z4** | **「附件同步写入公司 Memory File」** | §6.7 与 §1.3：附件是**独立于 Goldie 的全局约束**，「一个 `fileId` 一条公司知识库条目」，**本链路与 Goldie 无耦合** | **两句都作废**：附件解析出的正文与摘要**专供 Goldie 差距分析**，**不进公司 Memory File / 知识库面板**；本链路与 Goldie 由「无耦合」变为**直接耦合**（缺了它 §6.6 的 `attachments[]` 就永远是空摘要）。<br>⚠️ **PRD §四（全局规则·文件上传）那一句「所有维度附件同步写入公司 Memory File」本版未回写**，两边口径暂不一致 —— **以本设计为准**，PRD 回写另行处理 | §6.7 / §1.3 / **PRD §四（待回写）** |
| **Z5** | **`erl_answer_attachment.ingest_status` 的语义** | 「入知识库（Memory File）的结果」 | **改为「摘要生成状态」** —— 列名、Entity 字段名、`ErlIngestStatusEnum`、service 方法名、前端出参字段 `ingestStatus` **一律不动**（裁决 R8「原名复用、字段名称暂不调整」），三态 `PENDING` / `SUCCESS` / `FAILED` 与「失败不阻断评估提交、附件旁给重试入口」的规则**一字不改**，变的只有语义。升级脚本 `sprint118/V20` **只改 COMMENT、不改 schema**。<br>⚠️ **代价**：列名从此名不副实（叫 `ingest`、实际是 summary），只有 COMMENT 与 Javadoc 能说明 —— 已记入 `CIOaas-api/docs/待优化项.md`，等下一次 ERL 表结构变更的窗口一并改名为 `summary_status` | §6.7 / §9 / §10.4 |
| **Z6** | **Goldie 看不看得到附件** | §6.6 入参**没有** attachment / summary / fileId 任何字段，prompt 里 grep `attachment` / `summary` 零命中 —— PRD「附件供 Goldie 分析使用」**从未兑现** | §6.6 入参每题新增 **`attachments[{fileId, fileName}]`**（Java 只送 id 与文件名，**不碰摘要**）；摘要由 Python 在生成前按 `fileId` **批量现取** `ai_rag_entry.summary`，取不到即 `summaryAvailable = false`、**不等待不阻断**；`fileId` 本身**不进 prompt**（模型只看得到 `fileName` / `summary` / `summaryAvailable`） | §6.6 / §9 |
| **Z7** | **维度级 `narrative`** | `item_type` 自 v4.4 删 `STRENGTH` 后只剩 `GAP` / `ACTION`；`summary` 是**整期一份**，**维度级叙述无字段可落** | `item_type` 增加第三个取值 **`NARRATIVE`**：每维**至多一行**，正文存 `title` 列（三类共用同一份 `varchar(512)` 预算），`note` / `severity` 留空、`sort_order = 0`、`evidence_missing = false`；**只有有差距的维度才产出**，且**不参与 `hasGap` 判定**（`hasGap` 只数 `GAP` 行）。<br>与 v4.4 删 `STRENGTH` 的关系：`STRENGTH` 被删的理由是「有 gap 才展示建议，优势项在 UI 上无落点」，而 `NARRATIVE` **有明确落点**（`View details` 弹框每维分区顶部），不属同一情形；复用现表零成本，好过新建一张每维一行的表 | §5.8 / §6.6 / §8.4 / §9 |
| **Z8** | **`evidenceMissing` 的判定口径** | 该条由**该题无备注**的题推导而来 | **放宽为「该题无备注 _且_ 无可用附件摘要」** —— 不改的话，把证据放在附件里的题会被错标成「未提供备注」。前端文案随之由 ~~`No notes provided`~~ 改为 **`No supporting evidence provided`**（前端串名 `noNotesProvided` **沿用原名**，只换值）。判定本身**在 prompt 里做**，服务端只做透传归一 | §5.8 / §8.4 / §9 / §11-28 |
| **Z9** | **`erl_gap_analysis_item` 的维度列列名** | §6 开头 2026-09-08 定「维度字段命名规则」时**特意留的一条例外**：该列**本轮不改**，但出参仍叫 `dimensionCode` | **已改名 `dimension_code`**（`sprint118/V22`：`RENAME COLUMN` 只改元数据不重写表，索引 `idx_erl_gap_item` 自动跟随；另带一条 ddl-auto 抢先建了新列时的自愈分支）。**出入参本来就叫 `dimensionCode`，两边从此一致**，那条例外**整条消除**；§5.1.3 / §5.1.4 等五处「关联键清单」里的旧列名一并订正 | §5.8 / §6 开头 / §5.1.3 / §5.1.4 |
| **Z10** | **本版明确 _不_ 回写的两块** | — | **P3（gap analysis 两张表搬迁到 Python，加 `ai_` 前缀 + `stale` 改指纹派生）与 P4（题库版本 mismatch 提示 + 小卡第四态）尚未开发** —— §7.10-N1 / N2 与 §12 里「**不做**题集版本不一致的告警 / 阻断」两处结论**保持原样**，§5.7 的 `stale` 列与 §7.5 的置脏链路**一字不动**。理由：回写未实现的行为会让文档比代码更超前，**比不写更糟**；等实现落地后另版回写。<br>**v4.58 更新**：**P4 已实现并回写**（§0.32，§7.10-13 / N1 / N2 与 §12 四处已改判）。<br>**v4.59 更新（本行就此关闭）**：**P3 也已落地并回写**（§0.33）—— 产物两张表已搬到 Python （`ai_erl_gap_analysis` / `ai_erl_gap_analysis_item`）、`stale` 列取消改为现算指纹派生、§5.7 / §7.5 / §6.6 / §10 已按现状重写。⚠️ v4.58 那次回写在本格里写的「只剩 P3 仍未开发」**当时就已过期**（P3 的代码早于那次文档编辑合并），属回写疏漏，由本版更正 | §5.7 / §7.5 / §7.10 / §12 |

**数据库改动共三份升级脚本 + 一份 Python 迁移 + 一个一次性脚本**：`sprint118/V20`（`ingest_status` COMMENT 改摘要语义）、`V21`（`item_type` / `title` / `evidence_missing` 三条 COMMENT，并 `DROP CONSTRAINT` 掉 ddl-auto 可能带出的旧枚举 CHECK —— 不删则第一条 `NARRATIVE` 撞 `23514`）、`V22`（`dimension` → `dimension_code`）；Python `sql/migrations/business/V023__erl_attachment_summary_only.sql`（放宽 `chk_rag_space_process_type` 加入 `SUMMARY_ONLY`，并更新 `ai_rag_space.process_type` / 两张表 `business_type` / `ai_rag_entry.content_text` 四处 COMMENT）；存量附件改挂 space + 删旧 chunk 由一次性脚本 `CIOaas-python/scripts/migrate_erl_attachments_to_erl_space.py` 处理（**跨业务库与向量库、不能同事务，故不放 `sql/migrations/`**；**先删 chunk 再改 space**，顺序颠倒会出现 entry 已指向新 space 而 chunk 还在旧 space、chatbot 反而仍能召回；`content_text` **不回填**，存量只保留 `summary`，而摘要正是 Goldie 唯一消费的东西）。

**接口契约净变化**：入参每题 `+attachments[{fileId, fileName}]`；出参维度项 `+narrative`（接口 17 / 18 与 Python 内部接口三处同步）。**其余字段不增不减、不改类型。**

---

### 0.32 v4.57 → v4.58 修正清单（**P4 题库版本 mismatch 落地回写**，2026-09-19；依据 `erl-gap-analysis-dev-design.md` §7）

| # | 主题 | 原口径 | 新口径（v4.58） | 影响面 |
|---|------|--------|----------------|--------|
| **Y1** | **题集版本不一致要不要告警**（**推翻既有结论**） | §12 与 §7.10-13：**不做**题集版本不一致的告警 / 阻断，同期次两端跨版本**只在界面标注版本号** | **拆成两半改判**：**阻断仍然不做**（跨版本提交、旧草稿延迟提交照旧允许，版本号照旧只作次级标注），但**维度级的「不可比」要告警** —— 两端同维 `question_version_no` 不等时，A1 小卡渲染第四态、该维不送进 Goldie。PRD §6 那条「提醒 user，另一方未提交本季度新版本问卷」**至此兑现** | §12 / §7.10-13 / N1 / N2 / §6.1 / §6.6 / §8.4 |
| **Y2** | **判据取哪条版本号** | —（原先没有这个判定） | **只能是维度级的 `erl_question_config_dimension_version.question_version_no`**（copy-on-write 时才 +1 ⇒ 版本号相等等价于题集逐题相同）。**组织级发布批次号 `erl_question_config_version.version_no` 不可用**：发 v8 时可能只改了 FRL，Founder 绑 v7 / GSV 绑 v8 会把一字未动的 PRL 误判成不可分析（假阳性）。**两端实际作答的 `questionKey` 集合更不可用**：逐级解锁下两端止步的 level 天然不同、答题数本就不一样，会把绝大多数正常维度判成 mismatch | §5.1.5 / §7.10 |
| **Y3** | **粒度与取数** | — | **维度级**（整期级会让一个维度的版本差异传染成整期不可分析）。取数**复用 `bothSubmitted` / `allDimensionsSubmitted` 已经查出的两端 SOT 行**，版本号按 `(erl_question_config_version_id, dimension_code)` **一次 `IN` 批量查**（评估行上的捷径列 `erl_question_config_dimension_version_id` 可空，读侧一律走复合键）；判定收在**一个方法**里同时喂三处（接口 17 出参、接口 1 出参、生成时维度过滤）—— 与 `bothSubmitted` 一样三处口径必须同源 | §6.1 / §6.6 / §7.10 |
| **Y4** | **出参形态** | 维度项只有 `bothSubmitted` / `hasGap` 两条独立信息 | **加第三条独立布尔 `questionSetMismatch` + 方向 `mismatchSide`（`FOUNDER` / `GSV`，版本号较小的那一端）**，接口 1 与接口 17 同步。⚠️ **绝不能压进 `hasGap`**：压进去就是 `hasGap = false` ⇒ 前端渲染成绿点 `No Gap`，GSV 以为该维没问题照常 Share（假阴性，同 §6.6 那条 index 幻觉）。方向**服务端算好下发**（同 `shareable` 的口径，前端不复算）——PRD 要求的提示原文「提醒 user，**另一方**未提交」本身需要方向。<br>⚠️ **两条容易被「修掉」的刻意选择**：① mismatch **不随 `shared` 可见性裁剪**（同旁边的 `summary` / `generatedAt` / `stale` 都被 `visible` 挡住，它偏不挡）—— 它与 `bothSubmitted` 同属「提交事实」而非分析内容，公司端未分享时照常下发、不泄露任何 LLM 产物；② `mismatchSide` 的语义是**落后的那一端**、不是「另一方」，前端必须先与当前登录端比对再选文案（管理端 `FOUNDER` → 指创始人、`GSV` → 指己方团队；公司端一律中性），直接当「另一方」渲染会指错人 | §6.1 / §6.6 / §8.4 |
| **Y5** | **前端渲染** | 小卡三态：灰点 `Not submitted` / 绿点 `Gap analysis ready` / 绿点 `No Gap` | **四态，优先级写死不靠隐式短路**：`!bothSubmitted` → 灰点 `Not submitted`；`questionSetMismatch` → **黄点 `Question set mismatch`**；`hasGap` → 绿点 `Gap analysis ready`；else → 绿点 `No Gap`。**mismatch 必须排在 `hasGap` 之前** —— 正常路径下 mismatch 维度没送进 LLM、条目恒空，但「上一代生成过该维条目 + 本次整份失败未覆盖旧内容」时两者会同真，此时**显示 mismatch、旧条目与旧 `narrative` 都不渲染**（旧内容依据的是已不可比的提交，继续展示比不展示更糟；**不做**「折叠展示上一代旧分析」）。`View details` 该维分区：琥珀药丸 + 说明**按端分叉**（管理端 `mismatchSide` 带方向、公司端一律中性，理由同 §4.3 对公司端偏严的裁剪口径） | §8.4 / §9 |
| **Y6** | **生成侧** | 输入组装按 Active 维度全量下发 | **跳过 mismatch 维度**（`index` 仍按下发顺序 1..N，跳过后连续，Python 的 `index → code` 映射天然支持）；**可分析维度为 0（全维 mismatch）时不调 Python** —— 空 `dimensions` 会被 Python 判 `ValueError` → 400，这里提前收手、记 INFO、旧产物原样保留，**不向用户报错**。生成门槛 **S1 不改**（mismatch 时两端确实都 `SUBMITTED`，S1 照常成立，只是少送一维） | §6.3 / §7.5 / §9 |
| **Y7** | **版本号解不出怎么办** | — | **fail-open**：打 WARN（含 `companyId` / `period` / `dimensionCode` / 哪一端）后按 `mismatch = false` 继续分析。理由：快照行缺失是**数据问题不是业务状态**，默认 `true` 会把正常维度锁成「无法分析」而用户没有任何手段自己解决 = 把运维债转嫁给用户；继续分析的最坏后果「分析了两份不同题集」正是今天的既有行为，不算回退。⚠️ **「解不出」与「版本号 0」必须区分**（`0` = 该维在这一版下一道题都没有，是真实取值）：混同会让「一端快照缺失、另一端真的没题」判成版本一致 | §7.8 / §9 |
| **Y8** | **Share 门槛与计数** | — | **都不改**。`shareable` **不带 mismatch 条件**（PRD 对 Share 的原文只有「所有维度两方都完成」；把 mismatch 加进门槛会让一个维度的版本差异锁死整期分享，而其余维度的分析是有效的）；`{n} of {total} dimensions have gap analysis` 文案与算法也不动 —— **正常路径**下 mismatch 维度的 `hasGap = false`，自动不计入。⚠️ 别照 §7.9 原文写成「mismatch ⇒ `hasGap = false`」：Y5 那个「旧产物未被覆盖」的边角里两者会**同真**，此时计数会把该维算成「有分析」而弹框按 mismatch 渲染 —— 这个不自洽已记 `CIOaas-web/docs/待优化项.md`（修法：`readyCount` 改用四态判定 `gapMiniState(d) === 'ready'`），本版按设计不改 | §7.6 / §8.4 |
| **Y9** | **自愈** | — | **不需要为 mismatch 单独加触发点**：落后一方补交新版问卷 = 一次普通提交 → 走触发点 A → 指纹变化 → 重生成 → 版本对齐、mismatch 消失。⚠️ **别和填报页那个弹窗搞混**：填报页 2026-09-15 起的强阻断二选一弹窗（靠接口 3 的 `hasNewerQuestionSet`）提醒的是**我方**题库更新，本次提醒的是**对方落后** —— 两件事、两个位置 | §6.3 / §7.7 / §8.4 |

**数据库改动：无**（判据全部取自既有列）。**Python 侧改动：无**（判定与过滤都在 Java，Python 收到的入参只是少了几个维度）。

**接口契约净变化**：接口 1 / 接口 17 出参维度项各 `+questionSetMismatch` `+mismatchSide`。**入参、其余字段不增不减、不改类型。**

---

### 0.33 v4.58 → v4.59 修正清单（**P3 产物搬迁到 Python 落地回写**，2026-09-19；依据 `erl-gap-analysis-dev-design.md` §6 + 实测代码）

> ⚠️ **本节同时更正 v4.58 的一处事实错误**：v4.58（2026-09-19）在 §0.31-Z10 的补注里写「本行此后只剩 **P3 仍未开发**」，而 P3 的代码（`CIOaas-api` `0cd86b871`、`CIOaas-python` `V024__erl_gap_analysis.sql`）在那次回写之前就已合并。v4.57 写「P3 未开发」时属实，v4.58 照抄时已经过期。**Z10 至此整条关闭**：P3 与 P4 都已落地并回写。

| # | 主题 | 原口径 | 新口径（v4.59） | 影响面 |
|---|------|--------|----------------|--------|
| **X1** | **产物的所有权**（裁决 R1 / R3） | `erl_gap_analysis` + `erl_gap_analysis_item` 两张表归 **Java**，由 `ErlGapAnalysisServiceImpl` 落库；Python 只做一次 LLM 调用、把结果回给 Java | **两张表搬到 Python 并加 `ai_` 前缀** —— `ai_erl_gap_analysis` / `ai_erl_gap_analysis_item`（`CIOaas-python` `sql/migrations/business/V024__erl_gap_analysis.sql`）。因为改了表名，这**不是「同表换所有权」而是建新表 + `INSERT … SELECT` 迁数据**；**旧表不 DROP**，由 Java 侧下一个 sprint 单独出脚本，两步走保留回滚路径。Java 侧 `ErlGapAnalysis` / `ErlGapAnalysisItem` 两个实体与两个仓储**已删除**，域内一律经 `ErlGapAnalysisService#loadResult` 取产物 | §5.7 / §6.6 / §7.5 |
| **X2** | **`stale` 的形态**（裁决 R2） | `erl_gap_analysis.stale` 是**落库列**：提交事务内由 `invalidateGapAnalysis` 置脏，重生成成功后清零 | **列取消，改为读接口现算派生**：`stale` = 「S1 成立」且「现算的提交批次指纹 ≠ 产物里存的 `submission_signature`」。<br>⚠️ **`S1 成立` 这个前置条件不能省**：新增一个两端都没提交的 Active 维度时它永远进不了任何一次生成，指纹于是**永远**不等，页面会一直显示 `Refreshing analysis…`。<br>⚠️ Python 不可用（产物读成 null）时也不判 stale —— 此刻整块已降级空态，再投一次注定失败的 refresh 只会刷日志。<br>指纹 = **当前 Active 维度** × 双端 SOT `erl_assessment.id` 排序拼接后取 SHA-256（`ErlGapAnalysisServiceImpl#submissionSignature`）。⚠️ **必须按 Active 集合圈定，不能拿两端 SOT 全量算**：停用一个维度时它的 SOT 行仍在库里，全量算法下指纹一个字节不变 → 永不判 stale → 那一维的旧条目会一直挂在产物里。<br>⚠️ 末尾那层 SHA-256 不能省：产物列是 `varchar(64)`，5 维双端的原始拼接串是 369 字符，直接存会被截断、截断后两批不同提交还可能撞成同一个值 | §5.7 / §7.5 / §9 |
| **X3** | **`submission_signature` 的归属** | —（新列） | **Java 算、Java 比；Python 只存不算不比** —— refresh 入参带上本轮指纹，Python 原样落库、GET 时原样回传，全 Python 服务无 SHA-256 计算与比对（列注释已钉死）。这样「内容是否落后」这件事只有一个判定者 | §6.6 |
| **X4** | **`shared` 复位的位置** | Java 在置脏的同一事务里复位 `shared` / `shared_at` / `shared_by` | **随「覆盖产物」一起在 Python 侧做**（`overwrite_generated` 的 UPDATE 语句里一并置回 false / null）。重生成即取消分享的语义不变，只是执行点从 Java 移到 Python | §5.7 / §7.5 |
| **X5** | **并发控制** | Java 侧 Redis 锁 + `SELECT … FOR UPDATE` + 失败重试补跑（`callWithRetry`） | **Java 侧三者全删**，`ErlPythonClient` 只负责一次 HTTP 往返（不重试、不落库、不吞异常）。写入方从 3 个降到 **2 个**（重生成落库、Share）且都在 Python 进程内 ⇒ Redis 锁 + 单表短事务足够，**不再需要跨服务的行锁协议**。锁 key `erl:gapAnalysis:{companyId}:{period}`、TTL **600 秒**（须 ≥ 单轮最坏耗时：3 次尝试 × 180s 读超时 + 退避 2s/4s ≈ 546s，Python 侧有算术断言的单测钉住）；释放时**先比 token 再删**（Lua 单步），**Redis 异常保守放行**（拒绝会让功能整体不可用，重复生成只多烧一次 LLM 且落库是覆盖 + 全量替换，最终一致） | §7.5 / §9 |
| **X6** | **LLM 失败与校验失败的处置** | Java 重试补跑 | **Python 内重试 2 次、指数退避 2s / 4s**（并显式关掉 SDK 传输级重试，免得叠成天文数字）；**LLM 失败或 `index` 校验失败一律不写库**，旧产物原样保留。`index` 越界 / 重复 / 缺失 → **打 ERROR（带 companyId / period / 缺的是哪几个 index）+ 整份判失败**，**绝不降级成「该维无 gap」**（那是假阴性、且全程无告警） | §6.6 / §9 |
| **X7** | **落库顺序**（实现细节，别「优化」掉） | —（Java 侧 `overwriteAnalysis` 事务） | Python 侧覆盖路径是 **UPDATE 主行 → DELETE items → 批量 INSERT items**，**UPDATE 必须排在 DELETE 之前**：先拿到主行的行锁把并发串行化，否则两代条目会混在同一个 `analysis_id` 下。首次生成走 INSERT，撞 `uk_ai_erl_gap_analysis` 唯一键时回滚后转覆盖路径重试一次 | §5.7 |
| **X8** | **Java↔Python 的三个端点** | 只有一个「生成」调用 | `POST /api/ai/erl/gap-analysis/refresh`（生成并落库）、`GET /api/ai/erl/gap-analysis`（读产物，**无产物也 200**、回 `generatedAt = null` 的空态对象）、`POST /api/ai/erl/gap-analysis/share`（置分享位，**门槛仍由 Java 校验**）。读超时**按端点分开**：refresh 180s（一次 LLM 往返），读与 share **10s**（绝不能沿用生成端点的 180s，否则一次页面级读会挂着连接 3 分钟）。鉴权靠**转发调用者的 Bearer token**；异步线程取不到请求上下文，故 token 在请求线程内捕获后作为参数传入（走不带 token 的重载会让 Python 一律 401 → 产物读成 null → 幂等短路永不成立 → 每次提交都白烧一次 LLM） | §6.6 / §7.5 |
| **X9** | **维度标识 `index` / `code`**（P0 的延续） | 入参只有 `index`（`code` 一律不出现） | Python 要落库，故 refresh 入参的维度项**同时带 `index` 与 `code`**，但 **`code` 仅供落库、渲染 prompt 时必须剔除**（`_PROMPT_EXCLUDE` 连 `fileId` 一并剔，有单测断言「渲染结果不含 dimension code」）。理由不变：让模型逐字复现 `OPS4K7M` 这类无语义串，一次字符级幻觉就会让该维全部条目被丢弃、并恰好渲染成绿点 `No Gap`。**出参只有 `code`，`index` 不出现在任何出参里** | §6.6 |
| **X10** | **Java 侧留下什么** | 落库 + 置脏 + 锁 + 重试 + 输入组装 + 门槛 | 只剩 **ACL / 期次 / Active 维度 / SOT 取数、输入组装、Share 门槛、指纹现算、mismatch 判定**（P4）。接口 **17 / 18 / 27 的出入参逐字未变 ⇒ 前端零改动**（P3 这次提交没有碰任何 `interfaces/vo/` 文件；`submissionSignature` **不外泄到 VO**） | §6.6 / §8.4 |
| **X11** | **接口 24（维度配置保存）与差距分析的关系**（⚠️ **本条不是照抄开发设计，是按代码现状裁决**） | §7.11：接口 24 保存成功后**必须同事务**把该组织全部 `erl_gap_analysis` 置 `stale = true` 并复位 `shared = false`，否则公司端会继续看到一份按旧维度集合生成、且已不满足门槛的分析 | **那条实现手段随 P3 失效**：产物已在另一个服务的库里，跨服务**不可能同事务**；代码里也确实没有任何显式置脏（Java 侧 `invalidateGapAnalysis` 已整体删除）。改由**「Active 维度集合进指纹」自然覆盖**：<br>· **改权重** → 不触发（权重不改变作答，指纹不变；它只影响综合分展示，与分析内容无关）；<br>· **停用维度** → Active 集合变小 ⇒ 指纹变 ⇒ 其余维度若都已提交则 S1 仍成立 ⇒ 下次读或下次提交即重生成并覆盖（`shared` 随覆盖复位），§7.11 担心的「按旧维度集合生成」由此自愈；<br>· **新增维度** → 指纹同样变，但新维两端都还没提交 ⇒ **S1 不成立 ⇒ 既不重生成、也不判 stale**（这正是 X2 那个前置条件要的效果，否则页面永久 `Refreshing…`）。<br>⚠️ **残留边界（已知并接受，未自动兜住）**：新增一个 Active 维度、而该期次的分析此前已 `shared = true` 时，公司端会**继续看到那份按旧维度集合生成的分析**（内容不假、只是少一维），直到新维两端提交后重生成。要收有两条路：① 让接口 24 在新增 / 停用维度时显式调一次 Python 的 share 复位；② 读接口在「Active 集合 ⊄ 产物覆盖的维度集合」时降级为空态。**两条都要新接口或新判定，属产品口径问题**，已记 `CIOaas-api/docs/待优化项.md` | §7.11 / §6.3 / §9 |

**部署耦合（两条，缺一不可）**：① **先给 Python 的 DB role 授 `ai_erl_gap_analysis` / `ai_erl_gap_analysis_item` 两张新表的写权限，再上代码** —— 漏授权的表现是「提交后分析永远出不来、只有 Python 侧日志里有写失败」；Java role 对这两张表只读或无权限。② 存量搬迁随 Python 迁移 `V024` 自动执行（`to_regclass` 守卫 + 旧列名 `dimension` / `dimension_code` 双兼容），`submission_signature` 回填 **NULL** ⇒ 首次读必判过期 ⇒ 下次提交自动重生成一次，**可接受**。

**接口契约净变化：无。** 三个对外接口出入参一字未动，变的全是服务端内部的所有权与协作方式。

**随本版作废的历史条目（原文一律保留在原处，不改写变更日志）**：§7.5-S7（`stale` 何时才敢清零）、§7.5-S8（主行三个写入方一律加行锁）、§0.18-L1 / L2 / L3（指纹清零 + 补跑 2 轮 + `FOR UPDATE` 协议）、版本表 v4.12 行的 ①②、§0.10-D19 里「置脏 + `AfterCommit` + 异步重生成 + 重试 + Redis 去重」这串实现手段中的「置脏」与「Java 侧重试 / 去重」部分。**它们当时都是对的**，是 P3 把前提换掉了 —— 查历史裁决时请连同本节一起读。

**两处实现与本设计文本的有意偏离（以实现为准）**：① 产物表的时间列用 **`TIMESTAMPTZ`** 而非本文写的 `timestamp`（PG 化选择，避免存量时区位移）；② `item_type` / `severity` **刻意不加 CHECK 约束**（取值归一在 Python 出站前完成，加 CHECK 只会把归一漏洞变成 23514）。另：`source_founder_assessment_id` / `source_gsv_assessment_id` 两列建了但 **Python 从不写入**（refresh 入参带的是作答内容、不是评估 id），属有意保留的 legacy 列、永久为 NULL。

---

### 0.34 v4.59 → v4.60 修正清单（**2026-09-20 需求方三处前端调整落地回写**；依据 `CIOaas-web` `28695d36` / `16a76b00` / `536274e3`）

> 三处都是**纯前端展示**改动：**数据库、接口契约、Java / Python 服务端一律未动**。接口 17 照旧下发
> `sharedAt` / `sharedBy`，只是不再上屏；雷达图门槛是前端判定，后端 `radar` 字段的下发条件不变。

| # | 主题 | 原口径 | 新口径（v4.60） | 影响面 |
|---|------|--------|----------------|--------|
| **Y1** | **A1 Gap 区块的分享次级文字** | 已分享时按钮切 `Shared`（禁用）**+ 次级文字 `Shared {time} by {name}`** | **次级文字整行撤下，两端都不显示**。按钮态不变（管理端已分享仍切禁用的 `Shared`）—— ⚠️ **这半句已于 2026-09-20 当天被 v4.62 收窄**：按钮文案改为恒定 `Share to founder`、只置灰（§0.36-H1）。撤下理由：创始人读到的就是分享给他的那一份，「谁在何时分享」对他没有信息量；且 `sharedBy` 存的是 userId，屏上渲染出来的是一串裸 uuid | §0.10-D3 / §8.4 交互表 A1 行 |
| **Y2** | **A2 雷达图的渲染门槛** | 仅管理端；顶点数 = 当前 `status = 'Active'` 的维度集合的维度数（v4.4 / §0.10-D1），维度数本身不设下限 | **追加一道门槛：维度数 < 3 时整块不渲染**（连 `Dimension Radar` 标题条一起）。理由：雷达图要 3 个顶点才围得出面积，2 个退化成一条线、1 个退化成一个点，画出来读不出东西。门槛取 `dimensions[]` 长度 —— 与顶点标签同源，两者不可能失配；**不取 `radar.series` 长度**，否则会退回 v4.4 前「无人提交即整块消失」的老问题 | §0.10-D1 / §8.4 交互表 A2 行 |
| **Y3** | **Gap 详情弹框（A1 `View details`）内 `SUGGESTED ACTIONS` 的条目图标** | lucide `circle-dot`（外圈描边 + 实心内点，两层） | lucide **`target`**（三层同心圆靶心）。尺寸 / 颜色 / 描边宽度均未动，仅换图形 | 纯视觉，无契约面 |

**Y2 的一处有意例外**：雷达图**正下方**的基准入口 `Benchmarkit & Top GSV Quartile ›`（§0.10-D7）**不跟这道门槛** —— 参考分是按维度逐条录的，维度只有 1、2 个时照样要能进去录。代价是维度不够时版面上会出现「没有图的基准入口」，**这是有意的**，不是漏改。⚠️ 由此 D7 那句「与雷达图同条件」**自本版起只在「仅管理端」这一层成立**，不再是字面意义上的同条件。

**随本版作废的历史条目（原文一律保留在原处）**：§8.4 交互表 `A1 Share 后的状态与复位` 行里的「+ 次级文字 `Shared {time} by {name}`」半句（Y1）。其余条目只是被**收窄**、不作废。

---

### 0.35 v4.60 → v4.61 修正清单（**需求方 2026-09-20 裁决：差距分析改为维度级增量生成**）

> **一句话**：分析单元从「期次」降到「维度」。**不是**把门槛调松一点，而是把「一份期次产物」拆成「N 份维度产物 + 一段期次 summary」，
> 因此指纹、落库粒度、出参语义、前端状态机必须一起改 —— 只改门槛不改其余三处，会让每交一维就把已分析维度的结论删一次。

| # | 结论 |
|---|------|
| **G1** | **生成门槛 S1 改判**：~~该 `(company, period)` 下**每一个** Active 维度的两端都有 `SUBMITTED` 才生成~~ → **只要存在至少一个「可分析维度」就生成**。可分析维度 = 该维 FOUNDER 与 GSV 都有 `SUBMITTED` 记录，**且**不处于题集版本 mismatch（§0.32-Y6 的过滤前移到门槛里，原先那条独立的「全维 mismatch 就跳过」判断随之删除 —— 它已被「可分析集合为空」天然覆盖）。 |
| **G2** | **提交批次指纹下沉到维度级**：~~当前 Active 维度 × 双端 SOT `erl_assessment.id` 排序拼接后 SHA-256（一个期次一个值）~~ → **每维一个值**，`sha256Hex(dimensionCode + "\|" + founderAssessmentId + "\|" + gsvAssessmentId)`。<br>⚠️ v4.59 那条「**必须按 Active 集合算**，否则停用维度时指纹一字不变、旧条目永远挂着」的顾虑在维度级下**自然消解**：停用的维度不下发骨架、其维度行留在库里不上屏，重新启用时指纹与当年一致。**这是有意的，不是抄漏** —— 代码注释里必须写这一句。 |
| **G3** | **新增第 13 张表 `ai_erl_gap_analysis_dimension`**（Python 迁移 `V026__sprint118_erl_gap_analysis_dimension.sql`，见 §5.9）：`(analysis_id, dimension_code)` 唯一，存该维的 `submission_signature`、`has_gap`、`generated_at`、`model`。**三个作用缺一不可**：① 行存在 = 该维已分析（前端 `analyzed` 的唯一来源）；② 维度级指纹的存放处（增量判定的依据）；③ `has_gap` 显式落库，不再从 item 行数反推。<br>`ai_erl_gap_analysis.submission_signature` 同步**废弃停写**（恒 NULL），V024 已应用、按 `CIOaas-python/CLAUDE.md`「已应用的迁移文件永不再改」不得回改，故本次只在 V026 里改 COMMENT 标注废弃，DROP 留给下个 sprint。 |
| **G4** | **落库粒度：全量替换 → 按维度覆盖**。原 `UPDATE 主行 → DELETE 全部 item → 重插` 改为 `UPDATE 主行 →（逐个本轮分析的维度）upsert 维度行 → DELETE 该维 item → 插该维 item`。<br>⚠️ v4.59-X7 那条「**UPDATE 主行必须排在 DELETE 之前**、靠主行行锁把并发串行化」的顺序要求**继续成立**，不得因为拆成了维度级就调换。 |
| **G5** | **出参每维新增三个字段**（接口 17 / 18 / 27 同步）：`analyzed`（该维有维度行 = 分析过）、`analyzedAt`（该维上次分析时间）、`dimensionStale`（已分析过、但之后又有新提交，正在重跑）。<br>⚠️ **`hasGap` 的语义随之收紧**：它**只在 `analyzed = true` 时有意义**，且取值来源由 Java 的 `!gaps.isEmpty()` 改为 Python 下发的 `has_gap` 列。此前「产物里没有该维」与「该维确实无 gap」都落到 `hasGap = false`，是 §6.6 末尾那条「**「维度缺失」与「该维确实无 gap」被压成了同一个渲染态，需分开**」预告的缺陷，本版正式关闭。 |
| **G6** | **前端小卡状态机四态 → 六态**，优先级写死：`!bothSubmitted`（灰 `Not submitted`）→ `questionSetMismatch`（黄 `New version pending`）→ **`!analyzed`（蓝 `Analyzing…`）** → **`dimensionStale`（蓝 `Updating…`）** → `hasGap`（绿 `Gap analysis ready`）→ `else`（绿 `No Gap`）。§0.32-Y5 定的四级优先级是本表的前两级 + 后两级，**中间插进来的两级是本版新增**。计数文案由 `{n} of {total} dimensions have gap analysis` 改为 `{analyzed} of {comparable} dimensions analyzed`（分母是**可分析**维度数，不是全部维度数 —— 否则永远凑不满）。 |
| **G7** | **Share 门槛 S2 一字不改**（需求方 2026-09-20 裁决）：仍是「每个 Active 维度两端都已提交 **且** 无维度题集不一致」（后半条由 v4.58 加入）。理由：分析可以是增量的，但**分享给创始人的应当是一份完整报告**，半份发过去只会引出「剩下的呢」。`allDimensionsSubmitted` 方法因此**保留**，从「生成门槛 + Share 门槛」两用降为**只服务 S2**。前端把按钮禁用时的提示改为**列出还差哪些维度**（取 `dimensions[]` 里 `!bothSubmitted` 的 `dimensionAbbr`），替换原先那句笼统文案。 |
| **G8** | **`shared` 复位维持无条件**（需求方 2026-09-20 裁决，S4 不变）：任一次重生成都复位。**已知代价**：增量化后重生成频率由「一期一次」升到「一期最多 N 次」，「已分享 → 又交一维 → 创始人立刻失去访问 → 管理端再点一次 Share」会更频繁出现。当时评估过的折中（只在**已分析维度的内容被覆盖**时才复位）**未被采纳**，登记在此以便日后有人当 bug 排查时能查到原委。 |
| **G9** | **prompt 升 `# version: 1.5`**：新增只读入参 `analyzed_context_json` —— 本期次**已分析过的其他维度**的 `{name, abbr, hasGap, narrative}`，**不得为它们产出 gaps / actions，也不进 index 体系**；`dimensions[]` 仍是「本轮要分析的维度」，`summary` 必须覆盖**两者之和**（整个期次目前已知的全貌），否则每次增量都会写出一段只看得见新维度的期次摘要。`_resolve_indexes` 的「index 一个不少、不重、不越界 ⇒ 整份判失败不写库」校验**只对 `dimensions[]` 生效**，不变。 |
| **G10** | **存量不回填**（需求方 2026-09-20 裁决）：V026 不含 `INSERT … SELECT` 段。后果是老产物没有维度行 ⇒ 每维读成 `analyzed = false` ⇒ 管理端下次打开页面经触发点 B 自动重跑一轮，旧 item 在重跑时被按维覆盖。**自愈，无需人工干预**；数据量极小（落地时全库仅 1 份产物），重跑比回填干净。 |
| **G11** | **成本**：一个期次的 LLM 调用次数由 **1 次**升到**最多 N 次**（N = Active 维度数），加上重新提交的场景更多。维度级指纹去重兜住了「同一维反复跑」，不会白烧。需求方 2026-09-20 **明确接受**，不做额外节流。<br>⚠️ **2026-09-20 提交前审核后修正：「不做额外节流」这个结论当场就不成立了**。它成立的前提是「触发点 B 只在**手动**打开页面时触发」，而本版前端新增了有界轮询 ⇒ 每一轮都会打一次接口 17 ⇒ 每一轮都可能投一次触发点 B（读接口的写副作用）。任何让某维**永远出不了终态**的成因（LLM 反复 index 校验失败、落库 500、DB 权限缺失）都会让 `stale` 恒真，于是管理端页面开着就是**固定间隔的完整重生成循环**（Java 先跑完 `buildInput` 的三批 DB 查询再 POST，Python 锁一空出来就真跑，内含 ≤3 次 LLM 调用）。Python 的 Redis 锁只做**互斥**（`finally` 立刻释放），**不是节流**。两侧各自都合理，拼起来不合理。**改为两道各管一头**：① 触发点 B 加 Redis 冷却键 `erl:gapAnalysis:cooldown:{companyId}:{period}`（TTL 60s），拿不到就不投递 —— **只管触发点 B**，触发点 A（提交后）与 C（手动 Regenerate）不受限，否则真实提交会被吞掉；② 前端轮询间隔退避 **5s → 10s → 20s → 30s 封顶**、共 6 轮（≈125s），不再固定 5s。 |
| **G12** | **上线不兼容矩阵（2026-09-20 提交前审核补）**：本版是**破坏性契约变更**，**Java 与 Python 不得跨版本并存**，顺序写死 `V026（含 DB role GRANT）→ Python → Java → Web`。两个坏组合的后果**不对称**，必须都写进发布单：<br>• **老 Java + 新 Python**：老 Java 不发 `dimensions[].submissionSignature` ⇒ Python 每次 refresh **422**；读接口顶层指纹已删 ⇒ 老 Java 现算值恒 ≠ null ⇒ `stale` 永远 true ⇒ 页面常驻 `Refreshing analysis…` + 每次打开页面重投一次注定 422 的生成。**功能失效，但无数据损坏。**<br>• **新 Java + 老 Python**：⚠️ **会删数据**。老 Python 对多出来的 `submissionSignature` / `analyzedContext` 是 pydantic 默认忽略、顶层指纹又是 `Optional` ⇒ **refresh 会成功**，然后执行老的「DELETE 整份 item + 只插本轮这几维」⇒ **此前已分析维度的内容被物理删除**；同时响应里没有维度级指纹 ⇒ Java 算出 `dimensionStale` 恒真 ⇒ 前端进 `updating` ⇒ 轮询每轮真跑一轮 LLM 并再删一次。**数据丢失 + 成本失控。**<br>**回滚同理必须三侧一起**：全回滚是自愈的（老 Python 重新写回主表指纹，维度表变孤儿表不被读，一轮重生成后收敛）；**单侧回滚 = 重新落入上面两个坏组合之一**。 |
| **G13** | **接口 17 新增顶层 `analysisServiceUnavailable`（2026-09-20 提交前审核补）**：`loadResult` 把「Python 不可用 / 401 / 落库失败」一律降级成 `artifact = null`，于是 `isStale` 返回 false、每维 `analyzed = false` ⇒ 前端走第 3 优先级显示 **`Analyzing…`**，2 分钟后提示「刷新页面」——**而刷新解决不了 Python 宕机**；区块里的失败态 + Retry 在这个场景**永远不触发**（Java 已把故障吞成 200）。DB 权限缺失（V026 漏 GRANT）表现完全相同，且每轮都是 LLM 烧完之后才失败。故把这一位**显式下发**（公司端同样下发 —— 它同样需要知道是坏了而不是在跑），前端据此走失败态 + 专用文案 `Analysis service is temporarily unavailable. Gap analysis will resume once it is back.`，并**一次都不轮询**（宕机不会因为多轮几次好转，且每轮还会投一次注定失败的 refresh）。<br>⚠️ 注意这一位堵的是「**失败**伪装成进行中」；**维度级的 LLM 失败仍然落在 `Analyzing…`**（接口 17 没有 per-dimension 失败标志），已记 `CIOaas-web/docs/待优化项.md`。 |

**随本版作废 / 改判的历史条目（原文一律保留在原处）**：§7.5-S1 的「全部 Active 维度」口径（改判为 G1）、§7.5 触发点 A 流程图的第 3 / 4 / 5 步（改判为 G1 / G2）、§6.6 关于 `submissionSignature` 在请求与响应中位于顶层的描述（下沉到 `dimensions[]`，G2）、§6.6 末尾那条「需分开」的待办（本版关闭，G5）。

---

### 0.36 v4.61 → v4.62 修正清单（**需求方 2026-09-20：Share 按钮分享后不改文案**）

| # | 原口径 | 新口径 | 依据 |
|---|--------|--------|------|
| **H1** | 已分享时 A1 的 Share 按钮**切成禁用的 `Shared`**（v4.4-D3 定，v4.60-Y1 撤次级文字时明确「按钮态不变」） | **文案恒为 `Share to founder`，已分享只置灰、不改字** | 需求方 2026-09-20 |

- **理由**：同一颗按钮在两种状态下换标签，会让「这颗按钮是干什么的」随状态漂移；**禁用态本身已经表达了「现在点不了」**，再换一次措辞是多余的一层。
- **实现口径**：两个禁用成因**合并成一个 `disabled`** —— `shared`（已经分享过，没有可重复的动作）与 `!canShare`（服务端 `shareable` 未放行，门槛见 §7.5-S2，前端不复算）。**不再按 `shared` 分叉渲染两颗 Button**，这一条要写进代码注释，否则很容易被「顺手」改回去。
- **连带**：`TEXT.shared`（`'Shared'`）自此**无任何消费方，已删除**。
- **不变的部分**：Share 门槛（§7.5-S2 三条）、`shared` 复位规则（§7.5-S4）、底部常驻门槛提示（§7.5-S2 / §0.35-G7）、公司端在 `shared = false` 时不渲染该按钮（§0.10-D3）、以及 v4.60-Y1 撤下的次级文字 —— **一律未动**。
- **随本版收窄的历史条目（原文保留在原处）**：§0.34-Y1 那句「按钮态不变（管理端已分享仍切禁用的 `Shared`）」与 §8.4 交互表 `A1 Share 后的状态与复位` 行的前半句。

---

### 0.37 v4.62 → v4.63 修正清单（**2026-09-20 实测缺陷：已分享的期次出现 mismatch 后创始人仍看得到**）

**复现**（本地库实测）：`20:16:36` 管理端 Share ⇒ 创始人可见；`20:26:23` GSV 换新版问卷重新提交 FRL ⇒ 该维变 mismatch、卡面显示 `New version pending (Founder)`、Share 按钮置灰 —— 但**创始人照常看得到那份分析**，其中 FRL 的结论依据的是**已经被替换掉的题集**。

| # | 结论 |
|---|------|
| **J1** | **公司端的「已分享」改为读侧派生**：~~直接读产物的 `shared` 列~~ → **`shared` 列为真 且 该期次当前仍满足分享门槛（§7.5-S2 三条）**。管理端不受影响（它始终可读，且要看得见内容才能判断该不该重新分享），读到的仍是真实那一列。<br>**为什么不去修「重生成时复位」那条路**：那条耦合本身就是问题的来源 —— 复位 `shared` 一直是 Python `overwrite_generated` 的动作，也就是说它只在**内容真被覆盖**时发生。改造前指纹是期次级的，任一次提交都会让它变化 ⇒ 必然重生成 ⇒ 必然复位，于是「GSV 重新答题就结束分享」看着像一条规则，**其实是重生成的副作用**。v4.61 把指纹下沉到维度级后，「某维变 mismatch」不改变任何**可分析**维度的指纹 ⇒ `toRefresh` 为空 ⇒ 不调 Python ⇒ 复位永不发生。<br>读侧派生与 §0.33-X2 把 `stale` 从存储列改成现算是**同一个套路**：能算出来的状态就不要多一个写入方。**Python 侧的复位保持不变**，它负责的是「内容真被覆盖了」那一路，两者各管一头、不重叠。 |
| **J2** | **判据刻意复用 `isShareable`**（口径只此一处，本域反复强调；需求方 2026-09-20 在两个方案之间选了这一个）。<br>**已知代价**：`isShareable` 含「每个 Active 维度两端都已提交」，所以**新增一个两端都还没提交的 Active 维度**时，创始人也会暂时失去访问 —— 那份内容本身并没有失效、只是不完整。备选方案是把撤销判据收窄成「已分析的维度里出现 mismatch 或 outdated」，与 Share 门槛分成两个口径，**未采纳**，登记在此以便日后有人当 bug 排查时能查到原委。 |
| **J3** | **`shared` 出参的端差异**：管理端下发库里那一列，公司端下发派生值。公司端必须下发 `false` 而不是「`true` + 空内容」—— 前端 `hiddenForCompany = !isAdmin && !shared`，下发 `true` 会让创始人看到一块**内容为空的区块**（各维小卡还会因为 `analyzed=false` 渲染成 `Analyzing…`，像是在跑），而不是 `No gap analysis shared yet.` 的空态。 |
| **J4** | **恢复路径不变**：落后一方补交新版问卷 ⇒ 该维重新可比、指纹变化 ⇒ 重生成 ⇒ `overwrite_generated` 照常把 `shared` 复位为 false ⇒ **仍需管理端重新 Share**，与 §7.5-S4 和 `CIOaas-api/docs/待优化项.md` 2026-09-19 那条在册记录一致。若 mismatch 是因为发版后又撤回（题集回到原版）而消失，则内容从未变过，创始人自动恢复访问 —— 这是对的，不需要重新分享。 |

---

### 0.38 v4.63 → v4.64 修正清单（**需求方 2026-09-20：分析过程中去掉顶部提示**）

| # | 原口径 | 新口径 | 依据 |
|---|--------|--------|------|
| **K1** | A1 Gap 区块在期次级 `stale \| generating` 时，顶部挂一条 `Refreshing analysis…` 细条，旧内容继续展示 | **横幅整条撤下**。旧内容继续展示这一条**不变**（§9 的「不清空」仍然成立），只是不再用一条顶部提示去宣告它 | 需求方 2026-09-20 |

- **理由**：v4.61 给维度小卡加了 `Analyzing…` / `Updating…`（§0.35-G6）之后，进行时已经**逐维**说清楚了。顶部再压一条笼统横幅是同一件事说两遍；而且横幅是**期次级**、小卡是**维度级**，粒度不同还容易打架 —— 会出现「横幅说在刷新、几张卡却全是终态」这种对不上的画面。
- **`stale` / `generating` 两个出参字段保留不动**：前端仍用 `stale || generating` 判「已分享过的内容又被重生成」⇒ 渲染 `Content updated — reshare to founder.`（§7.5-S5）。**服务端零改动。**
- `TEXT.refreshingAnalysis` 自此无消费方，**已删除**。
- ⚠️ **本节是这条口径的唯一权威**：全文其余各处凡把 `Refreshing analysis…` / `Refreshing…` 描述成**屏上元素**的表述（§6.6 的出参说明、§7.5 触发点 B 与页面读取图、§9 失败降级表、§11 验收项 25），一律以本节为准 —— 那些句子里关于**服务端行为**（下发 `stale = true`、保留旧内容、触发点 B 自愈）的部分**依然有效**，失效的只是「屏上会看到一条 Refreshing 提示」这半句。历史修正清单（§0.33-X2、§0.35-G12 等）中的提及属留档，不再逐条订正。

---

### 0.39 v4.64 → v4.65 修正清单（**需求方 2026-09-24：差距分析任务化，sprint119**）

> 本节只记结论与作废关系；数据模型、状态机、契约、读写路径、迁移顺序的**唯一权威**是
> `docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md`（§5 / §6 / §7 等正文段落随实施回写，回写前以该文件为准）。

| # | 原口径 | 新口径 | 依据 |
|---|--------|--------|------|
| **O1** | §0.33-X1 产物三表归 Python，Java 无实体 | Java 持有 `erl_gap_analysis_report` + `erl_gap_analysis_dimension_task`（编排状态：记录、任务、status、has_gap、分享）；Python 持有 `ai_erl_gap_analysis_task`（生成日志 + 幂等标记）+ `ai_erl_gap_analysis_task_item`（AI 内容） | 需求方 2026-09-24 |
| **O2** | §0.35-G1 生成门槛 =「至少一个可分析维度」 | **报告级**：全部 Active 维度两端都 SUBMITTED 且无题集 mismatch 才建记录与任务；未就绪时两端已交的维度屏上沿用 `Analyzing…` | 需求方 2026-09-24（回到 PRD:193 口径） |
| **O3** | 2026-09-21 V027 `shared_snapshot` JSONB 冻结分享内容 | **记录级不可变**：`shared = true` 的记录及任务永不改；改动 ⇒ 新建记录，未变维度复制任务（`result_task_id` 指向持有内容的原任务）；未分享记录就地软删 + 新建。公司端读「最新 shared=true 的记录」，管理端读最新记录 | 需求方 2026-09-24 |
| **O4** | §0.35-G2 维度级指纹 `sha256(code\|founderId\|gsvId)` | 任务行明文 `source_founder_assessment_id / source_gsv_assessment_id`，指纹全链删除 | 同上 |
| **O5** | §6.6 refresh 一次 LLM 覆盖本轮全部维度，index↔code 映射与整批校验；`analyzedContext` 供期次级 `summary` | **每任务一次 LLM**（并发 3），`taskId` 不进 prompt；prompt 升 **1.7**（单维度输入，输出 `narrative / gaps[{title,severity}] / actions[{title}]`）；`summary` / `analyzedContext` 删除 | 同上 |
| **O6** | Python 端点 refresh / GET / share；Python 期次级 Redis 锁提供 `generating` | refresh（响应 `tasks[{taskId,status,hasGap}]`）+ **`POST /items`**（按任务批量取条目）；GET / share 端点与 Redis 锁删除；`generating` / `stale` / `dimensionStale`（恒 false）不再有来源 | 同上 |
| **O7** | 失败「不写库 → 指纹不等 → 触发点 B 重投」 | 任务状态机 `PENDING → RUNNING → SUCCESS \| FAILED`；管理端读接口按 60s 冷却把 `FAILED` 与超 10 分钟的 `RUNNING` 同 id 重投，Python 命中 SUCCESS 日志直接回状态不重复烧 LLM；HTTP 超时不置 FAILED | 同上 |
| **O8** | 用户初稿「Python 成功后回调 Java」 | **不做回调**（无可用凭证、回调丢失无对账）；同步响应回状态 | 评审 2026-09-24 |
| **O9** | 表名 `erl_gap_analysis` / `ai_erl_gap_analysis_dimension` | 改名 `erl_gap_analysis_report` / `ai_erl_gap_analysis_task(_item)`：库内同名旧表仍在、V024 / V026 已锁定，且全新库下 Java `ddl-auto=update` 先建同名表会让 V024 搬迁块 42703 中止 | 评审 2026-09-24 |
| **O10** | 出参含 summary / generatedAt / model / stale / generating / sharedAt / sharedBy / analyzedAt / note / why / evidenceMissing | 全部删除（前端 2026-09-21 / 09-23 起均无渲染方）；接口 1 的 `hasGap` 改读任务行，与接口 17 同源（了结 `CIOaas-api/docs/待优化项.md` 2026-09-20「口径不一致」条） | 同上 |
| **O11** | 旧 Java 表「留一个 sprint 做回滚路径」（§0.33-X1） | 随 sprint119 Java 脚本 DROP；Python 旧三表功能验证后 V029 DROP；存量产物不回填（Gap 区块仅 test 主机可见） | 需求方 2026-09-24 |

- **保持不变**：Share 门槛 S2 的三条（全维两端提交 / 无 mismatch / 无过期）在新模型下表达为「ready ∧ 全部活任务 SUCCESS ∧ 每维任务 source == 当前 SOT」，语义不变；接口 18 手动 Generate 仍同步（`CIOaas-api/docs/待优化项.md` 首条继续挂账）；前端六态代码、轮询、Share 请求体一律不动。
- **随本版作废的条目（原文保留在原处）**：§0.33-X1 / X4 / X5（归属与跨服务写协议）、§0.35-G1 / G2 / G3 / G4 / G9 / G10、§0.37-J1 ~ J4（读侧派生的 `shared`，被记录级不可变取代）、§5.8 三张 `ai_erl_gap_analysis*` 表定义、§6.6 契约、§7.5-S4「重生成复位 shared」、§12「不做差距分析的版本历史」（记录级追加即版本历史，但仍不做逐次浏览 UI）。
- **PRD 待回写**：PRD:193「若分享后又重新提交内容 … founder 端的内容就置空，直到下次分享」应改为「创始人继续看上一次分享的报告，直到管理端再次 Share」（2026-09-21 裁决，本版以记录级不可变落实）。

---

## 1. 范围与分期

### 1.1 V1 范围

| 模块 | 功能点 | 在 V1 | PRD | 说明 |
|------|--------|:-----:|-----|------|
| A 展示 | **A1 ERL Card（Company Overview 页内）** | ✅ | §3.1 | **加权**综合分 + 当前 Stage + Gap Analysis 区块（**v4.4** 定档形态见 §8.4 / D4） + **维度列表**（条目数由当前 `status = 'Active'` 的维度集合决定，**v4.4** 不再恒为 5，§5.1.3）（维度分 / Perception Gap **仅组合端**） + BPMM 参考数字 + 雷达图（**仅组合端**） + **`Full View ›`（v4.4，两端均有，A4 入口，§0.10-D5）** + **雷达图正下方 `Benchmarkit & Top GSV Quartile ›`（v4.4，仅管理端，§0.10-D7）**。**唯一入口，无独立落地页**。**v4.0：状态摘要徽章删除**（§0.9-10） |
| A 展示 | A2 Dimension Radar 雷达图（卡片内） | ✅ **仅组合端** | §3.5 | 4 条序列：Founder / GSV / Benchmarkit / Top GSV Quartile。顶点数 = 当前 `status = 'Active'` 的维度集合的维度数（**v4.4**，§0.10-D1）。**v4.60：维度数 < 3 时整块不渲染**（含标题条，§0.34-Y2）。**v4.0：PRD「该图仅在 Portfolio 端显示」→ 公司端整图不渲染**（§0.9-5） |
| A 展示 | **A3 维度详情页（Score Details，模板）** | ✅ | §3.2 / §3.5 | **一套模板全维度复用**（**v4.4**：由「5 维复用」改为按配置版本的维度列表复用）；含 score card 头、Perception Gap（**仅组合端**）、逐题列表、`View history`、`+ New`。**v4.0 删除三块**：状态摘要、Data Sources & Cadence（PRD 依据消失，§0.9-10 / -13）；Strengths & Priority Gaps 保留但依据改挂 §3.6（§0.9-11） |
| A 展示 | **A4 全维 Score Details 页**（v3.5 复活，**v4.20 照原型重排版**） | ✅ | §3.7 + §3.5（**v4.4** 补 `57225d2`） | **一页看全维度逐题明细**（**v4.4**：维度张数按当前维度集合，不恒为五）：~~双端 Tab + 各维度折叠卡 + 页尾基准卡~~ → **v4.20 全页重排版**（§0.24）：**两级面包屑 → H1 `Score Details`（页头无综合分、无 Stage 徽章，§0.8-12 撤销）→ 维度横向 Tab（一次只渲染一维，标签取 `abbr`）+ 末位基准 Tab（`External Benchmarks & Top GSV Quartile`）→ 组合端 `GSV` / `Founder` 药丸切换（`GSV` 默认，§0.10-D5 的「同屏并列」撤销）**。入口 **v4.4 由「F2 `View` 唯一入口」扩为「F2 `View` + ERL Card 的 `Full View ›`（两端）」**（§0.10-D5）；**每张维度卡卡头各有 `+ Add New`（v4.20：仅 `GSV` 侧）/ `View history`，原页级 `+ New` / `View history` 取消**（§0.10-D5）。原型 `/readiness/overall`（§0.7 反解 + **2026-09-09 重抓**，§0.24）。⚠️ **重排版是纯前端，接口 22 契约零变更** |
| A 展示 | ~~A5 "How It's Scored?" 评分标准弹窗~~ | ❌ **删除** | — | ~~**v4.0**：由「三段 Era 标准」改为**该题的单段判定标准 + 所属 `Era-level`**（每题现在只属一个 level，§0.9-21）~~ → ❌ **2026-09-06 裁决整体删除**（v4.9，§0.15）：判定标准字段 `criteria` 不进需求设计，弹窗唯一实质内容随之消失，组件与三处入口一并移除 |
| A 展示 | **A7 Company Overview 三卡布局**（v4.0 由「DI 下线」改，**v4.3 订正为两列**） | ✅ | §3.1 | **左列 `FI → DI` ＋ 右列 `ERL`**（ERL 占原 DI 的右列位置）；DI 数据、打分、入口与下钻**全部保留**，不新增任何开关（§8.6 / §0.9-6） |
| B 填报 | B1 Founder 自评问卷 | ✅ | §3.3 | **提交单元 = 单个维度**（**v4.4**，需求方 2026-09-06 裁决 R1，§0.10-R1）；期次选择、**Yes/No 逐级解锁**（本 level 全 Yes → 折叠打勾 → 解锁下一 level）、逐题备注 + 附件（**≤10MB/个**）、进度、~~自动存草稿~~ → **v4.30：手动存草稿（只有 `Save as draft` / `Submit` 两个按钮会落盘）**、提交即只读。**v4.4 新增**：顶部按钮组 `Save as draft` / `Cancel` / `Reset` / `Submit`（§0.10-D8）、题库更新提示（§0.10-D10；~~非阻断 banner~~ → 2026-09-15 起为**强阻断二选一弹窗**）、重复提交确认文案分支（§0.10-D11）、进入草稿显示上次保存时间与保存人（§0.10-D9）。**v4.0：手动维度分与软确认弹窗删除**（§0.9-3） |
| B 填报 | B2 GSV 验证问卷 | ✅ | §3.4 | 同题库、同解锁规则 + **逐题附件（与 B1 同口径，v4.6）** + 评估团队；提交单元同为**单个维度**（**v4.4**，§0.10-R1）。**v4.0：手动维度分与软确认弹窗删除** |
| B 填报 | **B4 Reset / 丢弃草稿**（**v4.4 新增**） | ✅ | §3.3（`08b7a32`） | 填报页 `Reset` 按钮：清空本次草稿的全部答案与附件、`unlocked_level` 回到 1；~~二次确认弹窗写明附件一并删除~~ → **v4.29 撤下二次确认，点下去直接清**。**接口 28** `DELETE /erl/assessment/draft`（§6.3）；同时是 §13-Q23「摆脱旧版本草稿」的解法（§0.10-D8） |
| B 填报 | B3 评估历史列表 | ✅ | §3.9 | 完整保留每次提交，突出最新 SOT。**v4.4**：新增 `Submitted` 列、删除 `Completion` 列、分数列改为**本维度 Overall Score + Stage 徽章**、`Portal` 列仅管理端渲染、详情限本维度（§0.10-D12） |
| C 配置 | C1 题库列表（**`Question Library` 顶层 Tab** 内：各维度 Tab + Era band 分组表格，v4.1；**v4.4** 维度 Tab 数按当前 `status = 'Active'` 的维度集合动态，不恒为五） | ✅ | §3.8 | **仅 portfolio portal**；题库按**组织（租户）**隔离（v4.0，§0.9-7） |
| C 配置 | C2 新增题目 / C3 编辑删除 | ✅ | §3.8 | 题干 / Era band（1–9 level）/ Source ~~/ **单段判定标准**（v4.0）~~ → ❌ **判定标准字段删除**（2026-09-06 裁决，v4.9，§0.15）；表单字段与 PRD §3.8 完全一致 |
| C 配置 | **C4 Era Band 内拖拽重排（= 必答顺序）** | ✅ | §3.8 | 含管理员影响提示 |
| C 配置 | **C5 题库版本化 + Publish 发布**（v3.3 改） | ✅ | §3.8 | 配置页改的是**草稿版本**；**新增 / 编辑 / 删除 / 重排全部经 Publish 才生效**；存在草稿版本即激活按钮（§7.9）。**v4.0：PRD 现文已与本设计一致**（`621e857` 采纳了 v3.6 的回写建议 M1/M2） |
| C 配置 | **C6 维度配置**（v4.0 新增，**v4.4 由「五维权重设置」扩容改名**） | ✅ | §3.8（`0333162`）/ §3.1 | 配置页第二个顶层 Tab ~~`Dimension Weights`~~ → **`Dimension Configuration`**（**v4.4**，§0.10-D13）：可**新增 / 删除 / 排序 / 改权重**；维度集合与权重**整组保存**、~~保存即生成新配置版本~~ → **2026-09-08：就地整组替换，不产生版本**（§7.11）；权重合计**必须 = 100%** 且需脏态才激活 Save；综合分按**当前 `status = 'Active'` 的维度集合**加权（§5.1.3 / §6.4 接口 23/24）。删除维度 = **物理删除**（新版本里不再有这一行），历史期次仍绑旧版本、照常显示（**v4.8**，§0.14） |
| C 配置 | **C7 题库版本历史页**（v4.1 新增，**v4.2 改形态**） | ✅ | 原型 2026-09-03 改版（§2.3.1-⑤）+ 2026-09-04 截图（§2.3.1-⑥） | `Question Library` Tab 的 `View history` 入口；**v4.2 起是「版本快照页」**：页头版本下拉（取**接口 25**）+ **各维度各一张只读题目表**（取**接口 26**；**v4.4** 卡片张数按该版本的维度列表，不恒为五；**v4.10** 该维度列表由接口 26 出参 `dimensions[]` 下发 = 该版本**发布当时**绑定的配置版本，后续维度增删改名不影响历史展示）。~~不新增表（v4.10 仅加一列 `dimension_config_version_id`）~~ → **2026-09-08：该列已删，改为新增表 `erl_question_config_dimension_version`（§5.1.5）承载发布当时的逐维快照**。**2026-09-09**（v4.17，§0.22）：版本下拉**只列已发布版本**（草稿不进下拉），卡头**不显示 `Retired` 灰标**，**本页不再取接口 23** —— 只读接口 25 / 26 |
| D 基准 | D1 基准记录页 + **D2 新增记录（独立页）** | ✅ | §4 | Benchmarkit / Top GSV Quartile 的**外部静态数据接入口**，平台不计算；**每期次按维度各录两个分**（v3.1，§0.3；**v4.4** 维度条目数按当前 `status = 'Active'` 的维度集合动态）。入口：ERL Card 雷达图正下方 `Benchmarkit & Top GSV Quartile ›`，**仅管理端**（**v4.4** 新增，§0.10-D7） |
| E AI | **E1 Gap Analysis & Suggested Actions** | ✅ | §3.6（**v4.4**：`8324a3f` 已删标题上的「待定功能」） | summary + 建议行动；~~Founder / GSV 两套口吻~~ → **v4.4 作废**：PRD 已删该段，改为**单一口吻 + GSV 手动 Share 给 Founder 端**（§0.10-D3）；ERL Card Gap 区块形态按 2026-09-06 原型定档（§0.10-D4）；提交后自动重生成（依据改标「本设计」，§0.10-D19；**2026-09-19 起「置脏」改为读侧现算指纹派生**，§0.33-X2），**重生成后 `shared` 复位为 false**（执行点已移到 Python，§0.33-X4）。~~可整块摘除~~ → **v4.4 作废**：**§13-Q22 关闭，E 模块确认进 V1**（§0.10-D2） |
| E AI | **E2 每维 Strengths & Priority Gaps** | ✅ | §3.6（**v4.0：§5 依据已删**） | 由证据/备注推导；无备注标注「未提供备注」。~~随 E1 一同待定~~ → **v4.4 作废**：随 E1 一同进 V1（§0.10-D2）。**v4.4**：`STRENGTH` 枚举与 `strengths[]` 出参删除，「有 gap 才展示建议」（§0.10-D4） |
| E AI | **E3 Share to Founder**（**v4.4 新增**） | ✅ | §3.6（`8324a3f` + `49d9a29`） | 差距分析默认**仅 GSV 团队可见**；该 `(company, period)` 下**每个维度**的 FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录（**2026-09-08**：`is_latest` 列已删，改按 同 `(company_id, period, portal, dimension_code)` 内按 `submitted_at DESC, id DESC` 取首条 `SUBMITTED` 判存在）时，`Share to founder` 按钮才激活。**接口 27** `POST /erl/gapAnalysis/share`（仅管理端）；`shared = false` 时公司端读到空态（§0.10-D3） |
| F 联动 | **F2 Portfolio ERL Tab** | ✅ | §3.7 | 跨公司总表（**v4.4**：排序筛选的依据改标 **「本设计（PRD 2026-09-03 已删除该条依据）」**，§0.10-D15；**v4.19**：顶部筛选器与列头排序器**一并按原型撤下**，界面上是纯展示表，服务端能力保留，§0.23-P2）；维度列**动态**，出参由硬编码 `frl/prl/berl/rrl/trl` 改为 `dimensionScores[]`（**v4.4**，§0.10-D1）；~~**展示期次 = 当前自然季度**，前端固定传 `period`~~（**v4.19** → **v4.33 撤回**，§0.23-P1）：现为**各公司自己 closed month 所在季度**，取不到的回退当前自然季度（§7.1.2） |

### 1.2 明确不在 V1

| 项 | 原因 / 去向 |
|----|-------------|
| 独立 Exit Readiness 落地页 / Dashboard 路由 | **PRD §3.1 明确不做**（v2.1 的 A1/A2 独立页已删除） |
| 顶栏 Ask Goldie 对话接入（E3） | 与 AI Chatbot 是另一条产品线 |
| Finance 页 Exit Readiness 卡片与入口（F1 / F3） | PRD 未要求；入口统一在 Company Overview 的 ERL Card |
| **完整 BPMM 评估交互** | PRD §5「不在本 story 范围内」；V1 只显示参考数字 |
| **每维状态摘要（`MET`/`PARTIAL`/`GAP` 徽章）** | **v4.0 移出**：PRD 2026-09-02 删去该展示项，三值枚举更早已删 ⇒ 零依据（§0.9-10） |
| **Data Sources & Cadence 卡** | **v4.0 移出**：PRD 2026-09-02 删去该展示项（§0.9-13） |
| **1–9 分打分控件 / 计分模式可切换的策略工厂** | **v4.0 移出**：PRD 已把打分格式定档为 Yes/No 逐级解锁，占位抽象成了 YAGNI（§0.9-1 / §7.2） |
| **每维手动整体分与软确认弹窗** | **v4.0 移出**：PRD 2026-09-02 在 §3.3 / §3.4 同时删除该要求（§0.9-3） |
| Goldie 建议的正式跟踪 / 指派 / Deadline | ~~PRD §3.6「MVP 不含」~~ → **v4.4 改依据**：PRD `273671a` 已删「指导性非强制 / 不含跟踪指派 Deadline」整段，结论不变，理由改为「**PRD 未要求**」（§0.10-D20） |
| Goldie 生成结果的人工编辑 / 审核流 | 见 §13-Q9 |
| 评估期次间对比 / 趋势 / 导出 | PRD 未要求 |
| 「GSV vs. Founder 分数对比 Tab」MVP 替代方案 | ~~PRD §3.6 列为待决定，见 §13-Q6~~ → **v4.4 改依据**：PRD `273671a` 删掉「已知 TBD 与 MVP 备选方案」整段，该备选不复存在，理由改为「**PRD 未要求**」；**§13-Q6 关闭**（§0.10-D21） |
| 题库导入导出、题库**公司级**覆盖 | PRD 未要求；题库按**组织（租户）**单份，组织内不再按公司细分（v4.0，§0.9-7） |
| Fireflies 转录 / SharePoint 作为 Goldie 数据源 | ~~PRD §3.6 明确为后续阶段~~ → **v4.4 改依据**：同上，PRD `273671a` 已删该段，结论不变，理由改为「**PRD 未要求**」（§0.10-D21） |
| **维度的物理删除**（v4.4 列为不做 → ~~v4.8 作废：物理删除已进 V1~~ → **2026-09-08 恢复为「不做」**，**2026-09-09 仍为「不做」**） | 配置页的两个破坏性动作**落库都是置位、都不删行**：**停用** = 置 `status = 'Inactive'`（行与 `weight` 原样保留、可恢复）；**删除**（**2026-09-09 新增**）= 置 `deleted = true`（行与 `weight` 同样保留，但**所有读侧排除、页面无恢复入口**）—— 「真删」指「从产品里彻底消失」，**不是 SQL `DELETE`**（§5.1.3 / §7.11-④）。~~历史安全由期次-版本绑定保证~~ → **2026-09-08 换依据**：置位下行不消失，历史提交仍能取到名称与缩写。~~**仍不做**的只剩「有历史数据禁止删除」的**前置拦截** —— 软删无保护对象~~ → **2026-09-09 改判**：**拦截存在**，但判据是「是否进入过已发布题库版本」而非「有无历史数据」，保护对象是**已发布题库版本的语义**（§13-Q24 / §0.21-X12） |
| **展示期次在无数据时回退到更早期次**（**v4.4 新增**） | R3 定档：缺省期次 = closed month 所在季度，**该季度两端均无提交即空态，不回退**（§0.10-R3；原 §9 的降级回退逻辑作废） |

### 1.3 后续阶段索引

| 阶段 | 内容 |
|------|------|
| V1（本文档） | A（含 A7 三卡布局）/ B（含 **B4 Reset**）/ C（含 C6 **维度配置**、**C7 版本历史**）/ D / **E1 + E2 + E3 Share**（**v4.4**：PRD `8324a3f` 已删「待定功能」，E 模块确认进 V1，§0.10-D2）/ F2 |
| V2 | 完整 BPMM 评估、Ask Goldie 接入、Fireflies + SharePoint 数据源、Goldie 自动打分 |

> ~~**E 模块的可摘除性（v4.0）**：PRD §3.6 现标「待定功能」，若需求方确认 V1 不做则整块摘除……~~ → **v4.4 作废并整段删除**：PRD `8324a3f` 已删去 §3.6 标题上的「待定功能」，**E 模块确认进 V1**，摘除面不再需要维护；**§13-Q22 关闭**（§0.10-D2）。

---

## 2. 事实基线

### 2.1 存量代码事实（本次落地必须对接的现状，均已核对源码）

| 事实 | 位置 | 对设计的影响 |
|------|------|--------------|
| Company Overview 页的 **DI 卡片**由 `DiStatus` 状态控制显隐 | `CIOaas-web/src/pages/companyOverview/home/CompanyOverviewPage.tsx:82`（state）、`:1561`（`display: DiStatus ? '' : 'none'`） | **v4.0**：ERL Card **插入**该位置，DI 卡片**下移到 FI 卡片之后**并**照旧受 `DiStatus` 控制**（不再改它的渲染条件，§8.6） |
| `DiStatus` 来源于 `getSdpModulesSettings(companyId)` 的 `diStatus`，**按公司维度**存储，另写入 `localStorage.diStatus` | 同上 `:99-109`；`companySettings/components/modules/ModulesTab.tsx` | ~~PRD 要求「系统级」隐藏而现有开关是公司级~~ → **v4.0 该矛盾消失**：PRD 2026-09-02 改为「DI 卡片放 FI 下、保留概览与入口」，**不再要求隐藏** ⇒ 该开关语义原样不动，`erl.enabled` 不新增（§0.9-6 / §13-Q2 关闭） |
| 平台**租户 = `organization_id`**：JWT claim `organization_id` → `SecurityUtils.getOrganizationId()` / `UserContext.organizationId`；`ai_file_registry` 等存量表已按该列隔离 | `CIOaas-api/gstdev-cioaas-common/.../security/jwt/JwtTokenProvider.java:83`、`.../utils/SecurityUtils.java:63`、`.../web/ai/financial/extract/domain/AiFileRegistry.java:79` | **v4.0**：PRD §4「ERL 配置层级按照**租户**层级」落到该列，**不新增租户概念**（§0.9-7 / §5.1.1） |
| 存量上传的单文件上限：chat 附件 `MAX_FILE_BYTES = 20 * 1024 * 1024` | `CIOaas-web/src/pages/devSupport/chat/components/InputBox.tsx:27` | **v4.0**：ERL 附件上限 PRD 明确为 **10MB/个**，比 chat 更严 ⇒ **不能复用 chat 常量**，ERL 域自带 `ERL_MAX_FILE_BYTES = 10 * 1024 * 1024`（§6.7） |
| Portfolio Company List 的 Tab 键位：`1` General / `2` Investment / `3` Connections / `4` Issues / `5` Benchmarking | `CIOaas-web/src/pages/portfolioCompanies/home/PortfolioCompaniesPage.tsx:501, :825` | ERL Tab 取 **`key='6'`**，并在 `trackPortfolioButtonClick` 埋点分支补 `'ERL'` |
| 各 Tab 的内容组件是 `portfolioCompanies/` 下的**平级目录**（`Benchmarking/`、`Issues/`、`connections/`…） | `portfolioCompanies/` 目录树 | ERL Tab 组件放 `portfolioCompanies/erl/`，**不是** v2.1 写的 `home/components/` |
| 文件直传通道：`storageService.uploadFile(file, fileBusinessType)` → presign → S3 PUT → verify，返回 `fileId` | `CIOaas-web/src/services/service/storage/storageService.ts:114`；类型枚举 `services/api/storage/dto.ts:8` | ERL 逐题附件复用该通道，`fileBusinessType = 'KNOWLEDGE_BASE'` |
| 「公司 Memory File / 知识库」登记 + 向量化的完整链路是 `ensure_kb_space` → `ingest_kb_file` → register → `start_vectorization` | `CIOaas-python/source/chatbot/application/service/chat_attachment_service.py:45-146` | ERL 附件须走**同一条链路**才能被 Goldie 检索到 |
| Python `POST /api/ai/file-registry/records` 是**低层入口**：只建登记行，**不建 rag 条目、不向量化** | `CIOaas-python/source/file_registry/interfaces/routes.py:267-284` | **不能**直接复用它做 ERL 附件登记（会得到检索不到的死文件）→ 见 §6.7 |
| 前端 API 域现有 25 个目录，无 `exitReadiness` | `CIOaas-web/src/services/api/` | 需新增并登记进 `standards/architecture.md` §2，见 §13-Q7 |
| Java 升级脚本最新目录 `sprint116` | `CIOaas-api/deploy/upgrade_doc/` | ERL DDL 落 `sprint{N}`（以实际排期 sprint 为准） |

### 2.2 领域常量（PRD §一）

- ~~**5 维度**：`FRL` / `PRL` / `BERL` / `RRL` / `TRL` 为领域常量~~ → **v4.4 作废**（§0.10-D1 / §0.10-R2）：**维度不是常量，而是租户级、可版本化的配置数据** —— 见 §5.1.3（`erl_dimension_config`，**2026-09-08 去版本化**：~~`erl_dimension_config_version` / `erl_dimension_config`~~ 两张表已删 / 改名）与 §5.1.5（`erl_question_config_dimension_version`，题库版本 ↔ 维度快照；原此处指的 `erl_company_period_config` 已于 **2026-09-08 删表**`，期次绑定配置版本）。
  - PRD §3.8（`0333162`）把维度列表写作 `FRL / PRL / BERL / RRL / TRL...`，**省略号即表示不固定五个**；配置页可新增 / 删除 / 排序 / 改权重
  - `FRL` Financial Readiness / `PRL` Product Readiness / `BERL` Brand Equity Readiness / `RRL` Risk Readiness / `TRL` Talent Readiness ~~现降级为**初始化种子数据**（组织的第 1 版配置）~~ → **2026-09-17（v4.55）：连种子也不再有** —— `V1__erl_init.sql` 的种子段整段删除，这五个 code 此后只是**叙述用的举例**（存量库里仍有这几行真实数据），新库的维度集合完全由租户在配置页录入；不再是编译期枚举 —— `ErlDimensionEnum` 与前端 `constants.ts` 的静态 `DIMENSIONS` 映射一并删除，改**接口驱动**（接口 23）
  - 维度 `code` 是**组织内稳定标识**，历史数据靠它关联；~~`code` 新增时取用户填的 `Abbreviation`（大写化），v4.8~~ → **2026-09-08 作废：`code` 由服务端随机生成（与 `abbr` 无关），此后永不改变**（`abbr` 可随时改名，`code` 不跟随，§5.1.3）；删除维度 = **软删**（**2026-09-08 推翻 v4.8**：置 `status = 'Inactive'`，行保留），历史提交记录照常显示（名称/缩写取评估行快照），但**实时聚合值（综合分 / Stage / 雷达图）会因停用而变**
  - 全文凡「恒五行」「固定返回五项」「按五维固定顺序」等表述一律按「当前 `status = 'Active'` 的维度集合的维度列表」理解
- **9 级 Stage 分 3 个 Era**（**不变，仍是领域常量**）：Founder Era（Stage 1–3）、Harvest & Growth Era（Stage 4–6，~~PRD 注「分数约 6 表示公司进入该纪元，可开始接触投行」~~ → **v4.4 订正**：该注解 PRD 2026-09-03 已删除，本设计不再引用，§0.10-D22）、Exit Era（Stage 7–9）
- **题目 level（= Era band）**：9 档 —— `Founder Era - 1/2/3`、`Harvest & Growth - 4/5/6`、`Exit Era - 7/8/9`。**一道题恒属一个 level**，一个 level 内可有多题（**v4.0**：PRD §3.3 的「level」与本设计的 `era_band` 是同一概念，字段名用 `era_band`、展示标签用 `Era-level`，§0.9-9）
- **分数值域（v4.0 改）**：**维度分 = 0–9 整数**（最后一个全 Yes 的 level；level 1 即出现 No → `0`）；**综合分（UI 文案统一为 `Overall Score`，v4.4 定档，§0.10-D14）= 0.0–9.0 一位小数**，按**当前 `status = 'Active'` 的维度集合**中各维度的权重加权求和（**v4.4**，§0.10-R2）。原「每题 1–9 分 / 维度分一位小数」随 1–9 打分格式一并删除（§0.9-1）
- **评估频率**：季度（PRD §4「评估周期：季度提交」）；**展示缺省期次 = 该公司 closed month 所在季度**（**v4.4**，§0.10-R3，口径复用 Financial Intelligence 域既有服务，见 §3.1 / §3.2）
- **提交粒度（v4.4 新增，§0.10-R1）**：一次提交 = **某公司 + 某期次 + 某端 + 单个维度**，不再是整卷五维
- **gap severity**：`HIGH` / `MEDIUM` / `LOW`（仅 E 模块使用）

### 2.3 原型可复用的事实（仅 UI 与口径参考）

> 探查方式：该 Lovable 项目对当前账号是 collaborator 身份，`get_project` / `list_files` 返回 403；改为抓取已发布站点（TanStack Start SSR）的路由 chunk 与渲染 HTML 还原。**原型无后端，全部数据为前端硬编码 mock**，数据模型与接口契约由本文档首次定义。
>
> ⚠️ **v4.4 总体注记（§0.10-D1 / §0.10-D13）**：本节及 §2.3.1 引用的原型（含 2026-09-03 / 09-04 两次重抓）**全部为「固定五维」形态** —— 五维 Tab、五个权重输入、雷达图五顶点、五张维度卡。PRD `0333162` 已把维度改为**可新增 / 删除 / 排序的租户级配置**，故原型在**动态维度这一点上已经过期**：下表凡以「五维」为形态的证据，**只作 UI 排版与文案参考，条目数一律按当前 `status = 'Active'` 的维度集合动态渲染**，不得据此把维度数写死。

| 结论 | 证据 | 与 PRD 的关系 |
|------|------|---------------|
| 综合分 = 五维简单平均 | (6.4+5.1+7.5+4.6+2.8)/5 = 5.28 → 显示 `5.3 /9` | ⚠️ **v4.0 降级为「等权特例」**：PRD §3.1 现要求按配置权重加权，各 20% 时与该式等价 —— 原型仍可用于校验加权实现（§7.1）。**v4.4 补注**：加权基数「五」参数化，按期次绑定配置版本的维度数取（§0.10-D1）；UI 文案统一为 `Overall Score`（§0.10-D14） |
| Perception Gap = Founder − GSV | 五维全部吻合（PRL 7.4−5.1=2.3、BERL 8.1−7.5=0.6、RRL 7.0−4.6=2.4、TRL 5.2−2.8=2.4） | ✅ 公式采纳；**v4.0：仅组合端展示**（PRD §3.5「创始人只能查看自己的分数」，§0.9-4） |
| 原型的维度分是一位小数（如 `6.4`） | 原型渲染 | ❌ **v4.0 不再适用**：维度分现在是 level 整数 0–9（§0.9-1）。**原型的分数展示、雷达图取值、Score Details 的逐题 `x.x/9` 均属旧口径，不得照抄** |
| 基准为两条独立序列、**按期次 × 维度**存历史（**v4.4**：原写「× 五维」，维度数改为按当前 `status = 'Active'` 的维度集合动态，§0.10-D1） | 基准页 `Latest by Dimension` 卡 + `Add Benchmark Record` 页的五维输入表（2026-08-27 截图） | ✅ 与 PRD §4「外部静态数据独立接入」相容，采纳（§5.6）。**v4.4**：录入表行数按当前生效配置版本渲染，不写死五行 |
| 旧截图记录表的 `+0.3 vs prior` 环比列 | 旧基准页记录表 | ❌ 新原型两张卡均无此列，**不实现**（§0.3-5） |
| 题量：FRL 31 题，五维合计 165 题 | 自评页进度条 `0 of 165` | ⚠️ PRD §3.3 写「30+ 题目」、§3.9 示例写 `45/45`。**题量由题库配置决定，代码不写死**；见 §13-Q4 |
| FRL 6.4 标 `Exit Era` | 原型渲染 | ❌ **原型 bug**，不予沿用（§7.3） |
| Portfolio ERL Tab 与 Dashboard 分数互相矛盾 | Example 1 两处数值完全不同 | ❌ 两份 mock 各写各的；本设计两处统一走 §7.1 实时计算 |
| A4 全维 Score Details 页的结构（~~面包屑 / 双端 Tab / 四列元数据栏 / 五张维度折叠卡 / 页尾基准折叠卡~~ → **v4.20：两级面包屑 / H1 无分数 / 维度横向 Tab / 端切换药丸 / 卡内四格元数据栏 / 末位基准 Tab**） | ~~已发布站 `/readiness/overall` 的 chunk `readiness.overall-*.js`（2026-08-28 抓取）~~ → **2026-09-09 同一路由的 SSR 实测 + 截图**（chunk 反解那版已过期） | ✅ 2026-08-28 裁决指定为 A4 的 UI 依据，**采纳**（§8.4）；三处有意偏离同处标注。**v4.4 两处补充**：① 维度卡张数按当前 `status = 'Active'` 的维度集合动态（§0.10-D1）；② 每张卡卡头加 `Add New` / `View history`，页级 `+ New` / `View history` 取消（§0.10-D5）。**v4.20 全面重排版**（需求方裁决「严格照原型」）：折叠卡 → 横向 Tab、同屏并列 → 端切换药丸、页头分数删除、基准卡 → 末位 Tab（§0.24） |
| 空态文案 `No gap analysis yet` + `Goldie needs scored questions with evidence notes ...` | `GoldieSuggestion` 组件 | ✅ 文案可复用（§9） |

### 2.3.1 原型 2026-09-03 重抓（**v4.0 新增**，原型当日 03:32 更新过）

> 抓取方式同 §2.3（MCP 仍 403，走已发布站 SSR HTML + 24 个 `/assets/*.js` chunk）。**该版原型自己也把计分模式换成了 Yes/No 逐级解锁**，与 PRD 2026-09-02 修订同向 —— 下表逐条标注它对 v4.0 是**印证**还是**冲突**。

**① 印证 v4.0 的关键结论（原型已实现，可直接作为 UI 依据）**

| 结论 | 原型证据 | 对 v4.0 的意义 |
|------|----------|----------------|
| **Yes/No + 逐级解锁是主路径** | 填报页 Yes/No 两按钮（`role: radiogroup`）；解锁算法按 level 升序逐组放行，出现 No 即 `failedLevel` 终止 | ✅ 印证 §7.2 状态机 |
| **维度分 = 出现 No 的 level − 1** | `Math.max(0, i - 1)`，`i = failedLevel` | ~~✅ 印证 §7.1~~ → ⚠️ **v4.37 就地标注**：**原型事实一字不改**（它确实是这么算的），但**该行印证的是旧口径** —— 本项目自 2026-09-15 裁决起改取「最后一个整级通关的 level」，稀疏题库下与 `Math.max(0, i - 1)` 不等，**与原型不再一致**（§7.1 / §7.2-①） |
| **无手动维度分、无软确认弹窗** | 填报页维度分是只读推导值 `{u ?? '—'}/9`，无 input；全 bundle 无 `doesn't match the questionnaire` 类文案 | ✅ 印证 §0.9-3（PRD 删除该要求） |
| **无 `Met`/`Partial`/`Gap` 状态徽章** | 三个词作为独立字面量在全部 JS 与 SSR HTML 中零命中 | ✅ 印证 §0.9-10（整块删除） |
| **无 Data Sources & Cadence 卡** | `Data Sources` 零命中；`Cadence` 只出现在题干里 | ✅ 印证 §0.9-13（整块删除） |
| **有维度权重配置、合计必须 100%** | `Dimension Weights` 卡：五个百分比输入 + `Total: {v}%` + `Save Weights`（合计 ≠ 100 时 disabled）；默认各 20% | ✅ 印证 §5.1.2 / §6.4 接口 24 的**合计 100% 校验**这一半；⚠️ **v4.4 部分过期**：该面板只管权重、且固定五个输入框，已被 PRD `0333162` 的 `Dimension Configuration`（新增 / 删除 / 排序 / 权重）取代（§0.10-D13）—— 校验规则与提示文案可复用，**面板形态与「五个」不可复用**（**v4.8 又改了一次布局**，§8.4-C6） |
| **填报页 / 配置页逐题标签带 level** | 组头与题行渲染 `{Era} - {level}`，如 `Founder Era - 1 · Source: Founder / CFO` | ✅ 印证 §0.9-9 的 `eraLabel` 格式（含空格） |
| **雷达图不在维度页 / Score Details 页** | recharts 雷达（`domain:[0,9]`）只出现在原型的 `/readiness` 与 `/finance?variant=b` | ✅ 与 §8.5「雷达图只落 ERL Card」一致 |

**可直接复用的原型文案**（已在 §8.4 落地）：
- 填报页吸底条：`Keep answering the current level. The next level unlocks when every answer is Yes; a No ends the dimension.` / 完成时 `All questions answered — ready to submit.`
- 失败 level 组头：`Answered "No" — assessment stops here, score {level-1}`（⚠️ **v4.37**：占位符 `{level-1}` 是**原型按旧口径写死的**，本项目落地文案改为直出后端 `levelScore`，见 §8.4）
- 权重卡：说明 `Allocate the weight of each dimension in the overall ERL score. The total must equal 100%.`；不合格提示二选一 `Exceeds 100% by {n}%` / `Needs {n}% more`；按钮 `Save Weights` → 成功后 `Saved`（**v4.4**：面板改名 `Dimension Configuration`、Save 按钮改为整组保存，说明与两条越界提示文案沿用，§0.10-D13）
- level 图例：`1–3 = Founder Era` / `4–6 = Harvest & Growth` / `7–9 = Exit Era`

**② 与 PRD / 本设计冲突的地方（一律按 PRD 与本设计，不照抄原型）**

| # | 原型行为 | 冲突对象 | 处置 |
|---|----------|----------|------|
| 1 | 已通关 level **直接不渲染**，无「折叠 + 显示 Check」 | PRD §3.3 原文「该 level **折叠并显示 Check**」 | 按 PRD 做 `CLEARED` 折叠 + ✓；未解锁 level 不渲染（这半条与原型一致） |
| 2 | **只读明细页**逐题标签**不带 level**（`Founder Era · Source: ...`） | PRD §3.2「每题显示 **Era-level** 标签」 | A3 / A4 也带 level |
| 3 | 只读页逐题右侧显示 `x/9`（内部把 Yes→9 / No→1 折算） | v4.0 模型题目**不折算分数**（§7.1） | 显示 `Yes` / `No` 徽章，不显示题级分 |
| 4 | `/readiness/overall` 页头**无**综合分与 Stage 徽章 | ~~2026-08-28 裁决（§0.8-12）~~ → ❌ **v4.20 撤销（§0.24-Z2）** | ~~A4 页头必须有加权综合分 + Stage~~ → **按原型，页头只有 H1 `Score Details`** —— 这一行原本就不是冲突，是本设计逆着原型加的，v4.20「严格照原型」后回到原型口径 |
| 5 | 附件上传**只在 GSV 页、挂在题上**；Founder 页**无上传** | PRD §3.3（Founder 题级 ≤10MB）+ §3.4（GSV 维度级） | ~~按 PRD：Founder 题级 + GSV 维度级~~ → **v4.6：双端题级**（§0.12）—— 原型「GSV 挂在题上」这一半反而与本版一致，只需补 Founder 页的上传入口（§5.5） |
| 6 | **无任何附件大小限制**（`10 MB` / `accept=` 零命中） | PRD §3.3「单个最大 10MB」 | 前后端双校验（§6.7） |
| 7 | 评分标准弹窗被桩成 `return null`（三处调用点仍在） | PRD §3.8 的评分标准 | ~~保留单段弹窗（A5，§0.9-21）~~ → **v4.9 改判**：**桩即最终形态** —— 2026-09-06 裁决判定标准不进需求设计，弹窗与三处调用点**一并删除**（§0.15） |
| 8 | 维度详情页无维度分卡头、无 Perception Gap、无 Strengths & Gaps | PRD §3.2 要求「该维度综合分数」 | 页头保留分数；gap 仅管理端（§4.2）；Strengths & Gaps 随 E 模块待定 |
| 9 | 有独立 `/readiness` 落地页 + `?variant=b` 内嵌 Finance 两种变体 | PRD §3.1「**不设独立** Exit Readiness 落地页」 | 两者都不做（§1.2） |
| 10 | `Completion` 硬编码 `45 / 45`（与其自身 165 题矛盾） | — | 原型 bug，不参考（真口径见 §0.9-17） |

**③ 原型给出的一条重要事实：level 分布是稀疏的**（已据此修正 §7.2 状态机）

原型题库共 165 题，`level` 分布如下（题量与其 Score Details 页显示的 31/29/38/31/36 吻合）：

| 维度 | 各 level 题量 | 合计 | 首个可作答 level |
|------|--------------|:---:|:---:|
| FRL | L1:4 L2:4 L3:5 L4:3 L5:4 L6:2 L7:6 L8:2 L9:1 | 31 | L1 |
| **PRL** | **L3:7 L6:12 L9:10**（只用三档） | 29 | **L3** |
| BERL | L1:2 L2:1 L3:4 L4:5 L5:9 L6:7 L7:4 L8:3 L9:3 | 38 | L1 |
| **RRL** | L1:1 L2:3 L3:4 L4:2 L5:9 L6:6 L7:5 L8:1（**无 L9**） | 31 | L1 |
| TRL | L1:1 L2:2 L3:6 L4:6 L5:6 L6:6 L7:3 L8:3 L9:3 | 36 | L1 |

首屏可见题数 `4+7+2+1+1 = 15`，正好等于原型自评页的 `0 of 15 questions answered` —— **反向印证「只渲染当前解锁 level」**。

> **这直接推翻了 v4.0 初稿状态机里「level 指针从 1 递增到 9」的写法**：PRL 没有 L1，指针会卡在「L1 既非全 Yes 也非含 No」的死锁上；RRL 全通关只能得 8 分而非 9。§7.2-① 已按「遍历实际存在的 level 升序列表」重写，并加了三条反直觉口径。

**④ 原型的入口回路缺陷**（不影响本设计，仅记录）：`/assessments/erl`（创始人自评）在任何 chunk 里都没有站内链接，所有 `+ New` 都指向 GSV 流；变体 A 的 `/readiness` 维度卡不可点、基准页不可达。本设计的入口规划见 §8.1，不沿用原型。

**⑤ 配置页 `/erl-configuration` 当日再次改版（**v4.1 新增**，仅 UI 参考）**

> ⚠️ **本节是原型驱动的 UI 调整，不是需求变更**：PRD §3.8 一字未改，**计分口径（§7.1 / §7.2）、权限口径（§4.2 / §4.3）、题库版本化口径（§7.9）、数据模型（§5）全部不变**。改的只是 C 模块的页面结构与控件形态，以及由 `View history` 带出的一个只读页（C7）+ 一个只读接口（#25）。
>
> ⚠️ **v4.4 追注（§0.10-D13 / §0.10-D1）**：上面「PRD §3.8 一字未改」的前提**已不成立** —— PRD `0333162`（2026-09-04）改写了 §3.8，把第二个 Tab 由「只管权重」扩为 **`Dimension Configuration`**（新增 / 删除 / 排序 / 权重），并把维度列表写作 `FRL / PRL / BERL / RRL / TRL...`。因此：本节记录的 `Dimension Weights` 面板**已被 PRD `0333162` 取代**；且**本节全部原型证据均为五维形态，在动态维度这一点上已过期**，仅余排版与文案参考价值。

| # | 新原型的结构 | v4.0 的写法 | v4.1 处理 |
|---|--------------|-------------|-----------|
| 1 | 页头：H1 `ERL Configuration` + 说明 `Configure dimension weights and the question library for each Exit Readiness dimension.` | 未写页头文案 | **采纳**（§8.4 C1） |
| 2 | **两个顶层 Tab**：`Question Library` / `Dimension Weights` | 「五维 Tab + **第 6 个 `Weights` Tab**」 | **改为两个顶层 Tab**；维度 Tab 下沉到 `Question Library` 内（§8.4 C1 / C6）。**v4.4**：第二个 Tab 改名 ~~`Dimension Weights`~~ → **`Dimension Configuration`**（§0.10-D13） |
| 3 | 题库 Tab 内：五维 Tab + **题目表格**，列 `QUESTION / ERA BAND / SOURCE / ACTIONS`（另有最左拖拽列），按 Era band 分组、每组一条组头行（band 徽章 + `{n} questions`） | 「组内按 level 折叠分组」（折叠面板） | **改为表格 + 分组行，不再用折叠面板**（§8.4 C1） |
| 4 | 题目行内的 `Era band` **下拉**可直接改 band | 「跨 band 移动请走接口 12 改 `eraBand`（编辑表单）」 | **改为行内下拉**，仍走接口 12 全量更新；接口 14 维持「只做同 band 拖拽重排」（§6.4 / §8.4 C4） |
| 5 | 权重面板：标题 + 说明在左，`Total: {n}%` + `Save Weights` 在右，**五个百分比输入平铺一行**（无滑条） | 「五行（维度名 + 百分比数字输入 + **滑条**）」 | **取消滑条**，按原型平铺；其余口径（合计 ≠ 100% 禁用 Save、不进题库版本、不激活 Publish、保存前确认框）**不变**（§8.4 C6）。⚠️ **v4.4**：该面板已被 PRD `0333162` 的 `Dimension Configuration` 取代 —— 每行改为「维度名 + 排序手柄 + 权重输入 + 删除操作」+ 面板上的 `Add Dimension`，**行数动态**（**v4.8 再改一版**：新增栏上移到面板头下一行、列表改卡片行、`code` 列撤下，§8.4-C6）；Save 双条件（脏态 + `Active` 行合计 100%）、~~整组保存生成新配置版本~~ → **2026-09-08：就地整组替换**；确认框文案 ~~「…历史分数不变」~~ → **「新配置立即全局生效，已有期次的综合分、Stage 与雷达图形状会随之变化」**（§0.10-D13） |
| 6 | 操作区 `Add New` / `Publish` / `View history` 右对齐，位于五维 Tab 之上 | 只有 `Add New` 与 `Publish`（页面右上） | 采纳该布局；**`View history` 为新入口** → C7（§8.4 C7） |
| 7 | `View history`：题库版本历史列表（版本号 + 状态 / 发布时间 / 发布人 / 变更计数 / 受影响维度） | 无此页 | **新增 C7 页 + 接口 25**；数据全部取自已有的 `erl_question_config_version`（`published_at` / `published_by` / `change_summary`），**不新增表**（§5.1.1 / §6.4 / §8.1 / §8.2 / §8.4 C7）。⚠️ **v4.2 已改形态**，见 §2.3.1-⑥ |

**⑥ `/erl-configuration/history` 的真实形态（**v4.2 新增**，仅 UI 参考）**

> ⚠️ **同样是原型驱动的 UI 调整，不是需求变更**：PRD §3.8 一字未改，**计分口径（§7.1 / §7.2）、权限口径（§4.2 / §4.3）、题库版本化口径（§7.9）、数据模型（§5）全部不变**。改的是 C7 这一个只读页的形态，外加它需要的一个只读接口（#26）。
>
> ⚠️ **v4.4 追注**：同 §2.3.1-⑤ —— 「PRD §3.8 一字未改」的前提已被 `0333162` 打破（动态维度，§0.10-D1），且**数据模型 §5 已因 R1 / R2 / D3 改动**。本节的截图证据仍为五维形态，C7 的卡片张数改为按**所选题库版本对应的维度列表**渲染，不写死五张。

**证据与其局限**：本次依据是需求方提供的整页**截图**（2026-09-04）。已发布站 `https://exit-readiness-hub.lovable.app/erl-configuration/history` 当前返回 **404** —— 该路由不在已发布构建里（36 个 chunk 全量抓取后 grep `Question Library History` / `Current (published` 零命中，预览域名 401）。因此：页面结构、文案、列与排序**以截图为准**；Era 徽章配色与 Era 标签则取自已发布 chunk 里的原始 token（`--founder:#e1990f` / `--harvest:#ded87a` / good `#1e8e4a`，标签 `Founder Era - {n}` / `Harvest & Growth - {n}` / `Exit Era - {n}`），与本设计 §6.2 的 `eraLabel` 口径**已经一致**，无需改动。

| # | 截图里的结构 | v4.1 的写法 | v4.2 处理 |
|---|--------------|-------------|-----------|
| 1 | 页头：H1 `Question Library History` + 说明 `All questions across the five Exit Readiness dimensions for the selected version.` | 「H1 + 页首 `< Back`」，未定文案 | **采纳文案**；`Back` 移到页头**右侧**与版本下拉同排（§8.4 C7）。**v4.4**：说明文案中的 `the five` 参数化为 `all`（`All questions across all Exit Readiness dimensions for the selected version.`），§0.10-D1 |
| 2 | 页头右侧：`Version` 标签 + 版本下拉（选项形如 `v3 — Current (published 12 Aug 2026)`）+ `Back` | 无版本选择器（页面就是版本清单本身） | **改为版本下拉**；清单数据仍取接口 25，只是从「表格行」变成「下拉选项」（§8.4 C7）。**2026-09-09**：下拉**只列已发布版本**，草稿不进下拉（§0.22-Y1） |
| 3 | 页体：**五维各一张卡**，卡头左为 `{维度全称} ({缩写})`、右为 `{n} questions`；卡内表格列 `QUESTION / ERA BAND / SOURCE` | 「一张表：VERSION / PUBLISHED / PUBLISHED BY / CHANGES / DIMENSIONS」 | **整页重做**（§8.4 C7）。变更计数与发布人不再单独成列 —— 它们已在下拉选项文案里。**v4.4**：「五维各一张卡」→「**每个维度一张卡**」，张数按该版本的维度列表（§0.10-D1） |
| 4 | 维度内题目**平铺**（无 Era band 组头行），Era 归属由行内徽章表达 | — | **采纳**：C7 是回看、不能拖拽，分组只会把页面切碎；配置页 C1 的分组行是为拖拽服务的，两者**有意不同**（§8.4 C1 / C7） |
| 5 | 无 source 的行显示 `—` | — | 采纳（与全站空值口径 `ERL_EMPTY_TEXT` 一致） |
| 6 | 选中版本后要展示**那一版的整份题面** | 接口 25 只回版本元数据；接口 9 只回**当前版本（草稿优先）的单个维度** | **新增接口 26** `GET /erl/question/version/{versionNo}`（§6.4）—— 仓库现有取题路径全部锁死在「草稿优先的当前版本」，历史版本取不到题面 |

---

## 3. 架构总览

### 3.1 落点

```
CIOaas-web (React 16 / UmiJS 3 / AntD Pro)
   src/pages/companyOverview/home/           A1/A2：ERL Card 替换 DI 卡（改存量页）
   src/pages/exitReadiness/**                ERL 页面群（维度详情 / 全维明细 / 填报 / 历史 / 配置 / 基准）
   src/pages/portfolioCompanies/erl/         F2：Company List 第 6 个 Tab（改存量页）
   src/services/api/exitReadiness/           HTTP 调用（1:1 后端接口）
   src/services/service/exitReadiness/       Response ↔ DTO 转换
        |
        |  /api/web/erl/**            <- 前端只调 Java，不直连 Python
        v
Gateway :9000  -->  CIOaas-web(Java) :5213/web
                        com.gstdev.cioaas.web.erl/      <- 新建业务域，DDD 四层
                        |       |
                        |       +- POST /api/ai/erl/gap-analysis/refresh  同步 HTTP（LLM 生成 + 落库）
                        |       +- GET  /api/ai/erl/gap-analysis          读产物（2026-09-19 新增）
                        |       +- POST /api/ai/erl/gap-analysis/share    置分享位（2026-09-19 新增）
                        |       +- POST /api/ai/erl/attachments/summarize 同步 HTTP（附件解析 + 出摘要）
                        |       |             （2026-09-18 由 /attachments/ingest 改名，§6.7）
                        |       |             v
                        |       |  CIOaas-python  source/erl/  <- 生成 + 落产物 + 附件编排（2026-09-19 起拥有两张 ai_erl_* 表）
                        |       |                 +- 复用 source/llm/ 基建
                        |       |                 +- 复用 rag ingest_service（2026-09-18：ensure_erl_space /
                        |       |                 |   ingest_kb_file / 摘要-only 管线，不再向量化）与 file_registry 登记
                        |       |                 +- prompt 放 source/ai/prompts/erl/（v4.4：合并为一份，
                        |       |                     不再分 Founder / GSV 两套口吻，§0.10-D3）
                        |       |
                        |       +- [v4.4 新增] 进程内调用 fi/（Financial Intelligence 域）
                        |             closed month 服务 —— 求「该公司 closed month 所在季度」
                        |             作为所有读接口的缺省期次（§0.10-R3）
                        v
                   PostgreSQL   ← Java 侧 9 张表（2026-09-19：差距分析两张搬到 Python 后由 11 张减为 9 张，见 §5）
                     erl_question_config_version / erl_question_config
                     erl_dimension_config                       ← v4.4 新增、2026-09-08 去版本化改名
                     erl_question_config_dimension_version      ← 2026-09-08 新增（发布时的维度快照）
                     ❌ erl_company_period_config —— **2026-09-08 已整表删除**（期次不再绑定配置版本）
                     erl_assessment                                              ← v4.4：+dimension，并上提 level_score /
                     erl_assessment_answer / erl_answer_attachment                  terminated_level / unlocked_level
                     erl_reference_score / erl_reference_score_item   ← 2026-09-08 改名
                     ~~erl_gap_analysis / erl_gap_analysis_item~~                ← 2026-09-19 搬到 Python：
                                                                                    改名 ai_erl_gap_analysis(_item)，
                                                                                    旧表留作回滚、下个 sprint 再 DROP
                     （erl_dimension_weight / erl_assessment_dimension           ← v4.4 两表删除）
```

- **前端只有一个后端出口**（Java），不出现前端直连 Python 的路径。
- Python 侧**不做公司 ACL**（Java 已校验）。~~不落 ERL 业务表~~ → **2026-09-19 起它拥有差距分析的两张产物表**（`ai_erl_gap_analysis` / `ai_erl_gap_analysis_item`，§0.33-X1）；**其余 ERL 业务表（评估 / 维度配置 / 题库 / 附件）仍属 Java，Python 不查**。
- 不使用 SQS：ERL 的 LLM 调用是单次秒级，理由见 §3.2。
- **v4.4 新增：ERL 域对 Financial Intelligence（`fi/`）域的跨域依赖**（§0.10-R3）。原设计对 FI **零依赖**，R3 裁决后所有 `period` 可选的读接口（1 / 17 / 20 / 22）缺省期次 = **该公司 closed month 所在季度**，closed month 沿用 FI 域既有口径（按公司 Manual / Automatic 两种推导，数据来自 Financial Entry actuals）。约束：
  - **复用 FI 既有服务，ERL 不自己算 closed month**，也不复制其推导逻辑；调用方向单向 `erl/ → fi/`，不得反向
  - closed month 取不到（公司无任何 actuals）→ **返回空态 + WARN 日志，不回退**到更早期次
  - 该季度两端均无提交 → **同样空态，不回退**（原 §9 的「降级到上一个已提交期次」逻辑作废）
  - 文件清单见 §10

### 3.2 关键决策与理由

| 决策 | 理由 | 否掉的替代方案 |
|------|------|----------------|
| ERL 入口是 **Company Overview 页内的卡片**，不建独立落地页 | PRD §3.1 明确要求；卡片是唯一入口 | ❌ v2.1 的 `/exitReadiness` Dashboard 路由 |
| **DI 卡片保留在页面上、下移到 FI 卡片之后**（v4.0 改） | PRD §3.1（2026-09-02）「DI 卡片**放在 FI 卡片下**；DI 数据、打分**保留概览信息和入口**」 | ❌ v3.x 的「新增 `erl.enabled` 开关隐藏 DI」（PRD 已不要求隐藏，§0.9-6）；❌ 删除 DI 组件与接口 |
| 新建 Java 业务域 `erl/`，走 **DDD 四层** | `standards/architecture.md` §1 强制；`quickbooks/`、`thirdParty/` 已是四层实现可作参照 | ❌ 仿照 `fi/` 的扁平结构 —— 那是历史遗留，不得在新域复制 |
| ERL 不并入 `fi/`（财务域） | ERL 覆盖五个维度，不属财务域 | ❌ 放 `fi/erl/` |
| **LLM 生成落 CIOaas-python，Java 经网关同步调用** | Java 侧零 LLM 客户端（全仓检索 bedrock / anthropic / openai / claude 的命中全是 SQS 消息类）；Python 有 `source/llm/` 完整基建 + Prompt 管理规范 + 调用追踪 | ❌ 在 Java 接 LLM SDK —— 要重建模型配置、Prompt 管理、调用追踪 |
| Java 与 Python 之间走 **HTTP 经网关**，不走 SQS | 单次、秒级、用户可等待 | ❌ SQS 异步 —— 为一个秒级调用付全套异步成本 |
| **差距分析提交后自动重生成 + 落库缓存** | ~~PRD §3.6「新评估提交后自动刷新分析」~~ → **v4.4 改依据**：PRD `273671a` 已删「自动刷新分析」这条，置脏 + 异步重生成**作为实现手段保留**，依据改标「**本设计**」（§0.10-D19）。**v4.4 新增边界**：重生成后 `shared` 复位为 `false`，需 GSV 重新 Share，管理端提示「内容已更新，需重新分享」（§0.10-D3） | ❌ v2.1 的「仅前端手动触发」；❌ 每次进页面实时生成（Company Overview 首屏会被 LLM 阻塞）；❌ 重生成后静默改写 Founder 已看到的内容 |
| 自动重生成走**提交事务外的异步任务**（**2026-09-19：~~+ 置脏标记~~ 改为读侧现算指纹派生**，§0.33-X2），页面判出落后时显示 `Refreshing…` | 提交动作本身不能被 LLM 时延拖住；PRD 只要求「自动刷新」，未要求同步 | ❌ 在提交事务里同步调 LLM —— 提交接口 RT 不可控，LLM 失败会回滚提交 |
| **评估记录不加 `(company, period, portal, dimension)` 唯一约束**，~~改用 `submission_seq` + `is_latest`~~ → **2026-09-08：两列均已删除**，改按 `submitted_at DESC, id DESC` 取 SOT（无数据库级「至多一条 SOT」保证，§5.2）（**v4.4** 补 `dimension`） | PRD §3.3 / §3.9 要求同季多次提交且全量留档 | ❌ v2.1 的唯一约束（会丢历史提交） |
| **提交粒度 = 维度级**（**v4.4 新增**，需求方 2026-09-06 裁决） | 一次提交 = 某公司 + 某期次 + 某端 + **单个维度**；提交前置校验由「五维全部终止」降为「**本维度终止**」；PRD §3.5 / §3.7 的「每维 `Add New` / `View History`」由此天然成立；逐级解锁天然按维度独立 ⇒ **§13-Q19 关闭**（§0.10-R1） | ❌ v4.3 的「整卷五维一次提交」—— 单维完不成就全卷交不了，且与 PRD 的每维入口矛盾；❌ 保留 `erl_assessment_dimension`（维度级后恒一行，属多余一层，整表删除，§5） |
| **同一期次不同维度允许绑不同题库版本**（**v4.4 新增**） | 维度级提交后 `erl_question_config_version_id`（**2026-09-08 改名**）的绑定粒度**每维一份**；先交的维度锁旧版、后交的锁新版是正常现象，**系统不阻止、不告警**，各自按自己的版本渲染与计分 | ❌ 强制同期次五维同版本 —— 会要求先交的维度回退重填，与「提交后即只读」冲突 |
| **维度分 = 逐级解锁推导的 level 分，无任何手动录入**（v4.0 换底） | PRD §3.1 / §3.3（2026-09-02）「该维度最后一个全部 Yes 的 level 的 level 为此维度得分」「分数就是此回答为 No 的 level 减一」 | ❌ v2.1 的「维度分 = 题均分」；❌ v3.5 的「GSV 手动 + Founder 推导」；❌ **v3.6 的「双端手动分 + 软确认弹窗」**（PRD 已删除该要求，§0.9-3） |
| **综合分按配置权重加权**，权重独立保存、**不随版本化**（v4.0 提出 → ~~v4.4 作废~~ → **2026-09-08 恢复生效**） | ~~v4.4：需求方 2026-09-06 裁决维度集合与权重整体版本化、期次绑定、历史永不漂移，§13-Q21 关闭~~ → **2026-09-08 再次反转**：`erl_dimension_config_version` 与 `erl_company_period_config` **两张表均已删除**（§5.1.2 / §5.1.4），维度与权重只有一份**当前值**（`erl_dimension_config`，§5.1.3），综合分**实时按当前权重算** —— **改权重 / 增删维度会回溯改变历史期次的综合分与 Stage（已接受）**；§7.10-W1 改回「接受历史漂移」、**§13-Q21 重新打开** | §5.1.3 / §7.1 / §7.11 / §13-Q21 |
| **题库、维度配置按组织（`organization_id`）隔离**，不按公司（v4.0 改，**v4.4** 由「题库与权重」扩为「题库与维度配置」） | PRD §4「ERL 配置层级按照**租户**层级」；平台已有 `organization_id`（§2.1） | ❌ v3.x 的「题库全局单份」（跨租户串题）；❌ 按公司隔离（PRD 只说到租户层级，公司级覆盖是 §1.2 明确不做的） |
| **展示缺省期次 = closed month 所在季度，无数据即空态**（**v4.4 新增**） | 需求方 2026-09-06 裁决 R3：季度提交的口径要与财务已结账月对齐，避免展示一个财务上尚未闭合的季度；closed month **复用 FI 域既有服务**，ERL 不自己算（§3.1） | ❌ ~~缺省 = 最新已提交期次~~（v4.3 口径，**已被 R3 推翻**）；❌ 无数据时回退到更早期次 —— 会悄悄显示上一季数据，用户误以为是本季结果（§9 的降级逻辑作废） |
| **计分不做策略抽象**，只有一个 level 计分器（v4.0 改） | PRD 已把打分格式定档，「保证未来切换不用重构」的要求随之删除 ⇒ 策略工厂成了为假想场景预留的扩展点，违反根 `CLAUDE.md` 的 YAGNI | ❌ v3.x 的 `ErlScoringStrategy` + `ErlScoringStrategyFactory` + `erl_assessment.scoring_mode` 快照（§0.9-1） |
| 答案表 `erl_assessment_answer` **一行一题**，不做 JSON 大字段 | 需要按维度 / level 聚合、按题 join 题库、逐题挂附件与备注 | ❌ `answers jsonb` |
| ~~**附件表同时承载题级与维度级两种挂载**（`answer_id` 可空）~~ → **v4.6 作废**（§0.12）：**附件只有题级一种粒度**，双端同口径 —— 表名改回 `erl_answer_attachment`、`answer_id` 回 not null、`assessment_id` 列删除（`dimension` 列已在 v4.4 删除） | 维度级附件本就只有 PRD §3.4 一句 12 字的依据，需求方 2026-09-06 裁决取消；粒度归一后「附件属于哪道题」是表上自明的事实，不再需要「空 / 非空」这种隐式区分标志 | ❌ 保留可空 `answer_id` 只在服务端拦维度级写入（表结构仍在说谎，日后必被误用）；❌ `erl_answer_attachment` + `erl_dimension_attachment` 两张近乎相同的表 |
| **计分不落库、实时算**（含维度 level 分与加权综合分） | 与 §12「不冗余存储聚合分数」一致；level 分由答案唯一决定，无二义。~~v4.4 补充：实时算不等于按当前权重算 —— 一律按该期次绑定的配置版本计算~~ → **2026-09-08 反转**：期次绑定表已删，**加权综合分与 Stage 一律按当前 `status = 'Active'` 的维度集合与其当前 `weight` 实时算**（§7.1 / §7.11）—— 故它们会随配置变更而**回溯改变历史期次的值**（已接受，§13-Q21）。「存在 null 维度分时按剩余维度归一化」的逻辑保留，基数由「五」改为该版本的维度数（§0.10-R2 / §0.10-D1） | ❌ 提交时把综合分 / Stage 写死；❌ ~~按「当前生效权重」实时算~~（v4.3 口径，**已被 R2 推翻** —— 会让历史期次的综合分随配置改动漂移） |
| 草稿与正式提交**同一条记录**，用 `status` 区分；提交后该行冻结，再改则新建下一条 | PRD §3.3「支持保存进度」+「提交后即只读，如需修改必须新建一次提交」 | ❌ 独立草稿表 |
| **题库版本化**：版本表 + 写时复制草稿版本，所有配置变更经 Publish 生效（v3.3，依 2026-08-28 裁决） | 需求方要求「所有变更都经发布」；状态位只能表达「新增未发布」，表达不了「同一题的编辑前后两份题干」 | ❌ v3.2 的 `publish_status` 状态位（编辑无法两态并存）；❌ 双表（草稿表 + 正式表，等于版本化但只能存两代、且两套 DDL 要同步维护） |
| 题目删除 = **在草稿版本内物理删行**（v3.3 改；原为软删 `enabled=false`） | 历史评估绑定题库版本快照，已发布版本的行不会被删，软删标记失去价值 | ❌ 继续软删 —— 版本内还留一堆 `enabled=false` 的行，查询恒要带条件 |
| **必答顺序落在 `erl_question_config.sort_order`**，配置页拖拽即改该列 | PRD §3.8「该顺序即评估中的必答顺序」 | ❌ 顺序只做展示、计分顺序另存 |
| **level 计分收在 `application/scoring/ErlLevelScorer` 一个类里**（v4.0 改） | 逐级解锁的「终止 level」判定同时被填报解锁、提交校验、展示计分、组合层、Goldie 输入五处消费，散写必然漂移 | ❌ 把 level 判定散写在各 service；❌ v3.x 的策略接口 + 工厂（只剩一种模式，抽象无消费者） |
| ~~Gap analysis 绑定 **`(company_id, period, audience)`**，双 audience 各生成一份~~ → **v4.4 作废**：绑 **`(company_id, period)`** 单份 + `shared` 状态位（§0.10-D3） | PRD `8324a3f` + `49d9a29` 删掉「Founder / GSV 两套口吻」整段，改为「GSV 团队可见，点 `Share to founder` 分享给 Founder 端」⇒ `audience` 列删除、两份 prompt 合并为一份、`shared` / `shared_at` / `shared_by` 三列新增；激活门槛 = 该 `(company, period)` 下**每个维度**的 FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录（**2026-09-08**：`is_latest` 列已删，改按 同 `(company_id, period, portal, dimension_code)` 内按 `submitted_at DESC, id DESC` 取首条 `SUBMITTED` 判存在）（接口 27） | ❌ 绑单个 `assessment_id`；❌ ~~双 audience 两份内容~~（PRD 已删该要求，一次 LLM 产两套口吻的优化随之无的放矢）；❌ 生成即对 Founder 可见（PRD 要求 GSV 主动 Share） |
| ERL 附件复用**知识库完整入库链路**（ingest + 向量化），不用 `file-registry/records` 低层入口 | 后者只登记不向量化，Goldie 检索不到（§2.1） | ❌ 直接调 `POST /api/ai/file-registry/records` |
| 前端新增 API 域 `exitReadiness/` | `standards/architecture.md` §2 的现有域无一匹配 | 需同步登记进 §2 域表，见 §13-Q7 |

---

## 4. 鉴权与端类型

### 4.1 角色映射

PRD §4 的权限模型 → 平台现有机制：

| PRD 角色 | 平台判定 | 说明 |
|----------|----------|------|
| Company User / Company Admin（Founder 侧） | `user.roleType > 1`，公司锁定 `user.inviteDto.id` | 公司端 |
| Portfolio Manager / Portfolio Group Manager（GSV 侧） | `user.roleType <= 1`，公司取 URL `?id=` | 管理端 |
| ERL Configuration 管理员（**v4.0 收紧**） | 管理端（PRD §3.8「**仅 portfolio portal**」）**且** 具备配置权限（粒度见 §13-Q7）；**其读写一律限定在调用者自己的 `organization_id` 内**（PRD §4「ERL 配置层级按照租户层级」） | 顶部导航右侧下拉入口；题库版本与**维度配置版本**按组织隔离（§5.1.1 / §5.1.2；**v4.4** 由「权重」扩为「维度配置」，§0.10-D13） |

沿用存量财务页已有的同一套判定（`src/pages/financial/home/FinancialPage.tsx:99`），**不新增端类型机制**：

```
companyId = user.roleType <= 1 ? getQueryString('id') : user?.inviteDto?.id
isAdmin   = user.roleType <= 1        // 管理端（portfolio portal）
```

> ⚠️ **前端端类型判定只认 `roleType`，禁止用 `isAdminEnd()`**（v4.0 订正）：`isAdminEnd()` 是**域名白名单**（`utils.ts:304`，只认 `admin.lgpi.io` / `admin-staging|uat|test.lgpi.io`），在 **`localhost` 上恒为 `false`** —— 用它判端会让本地开发时整个 ERL 前端锁死在公司端形态（无 GSV Tab、无雷达图、无基准、`portal` 恒被归一回 `FOUNDER`），管理端功能在本地**完全不可达**。
>
> v3.x 的实现误用了 `isAdminEnd()`（`useErlRouteParams.ts` 与 `ErlCard.tsx` 各一处），v4.0 已改回 `roleType <= 1`。全仓 `src/pages/` 有 **100+ 处** `roleType` 同款写法，`isAdminEnd()` 仅 5 处且属域名路由用途 —— 后者不是功能可见性的判据。

### 4.2 页面与端的对应（按 PRD §3 逐条收紧）

| 页面 / 元素 | 公司端（Founder） | 管理端（GSV） | PRD 依据 |
|------|:---:|:---:|------|
| A1 ERL Card | ✅ 只看本公司 | ✅ 看所选公司 | §3.1 |
| **A1 卡片内的 GSV 维度分**（v4.0 收紧） | ❌ **不可见** | ✅ | §3.5（`74f25df`）「创始人（公司 portal）：**只能查看自己的分数**」 |
| **A1 卡片内的 Perception Gap**（v4.0 收紧） | ❌ **不可见** | ✅ | 同上 —— gap 与自己的分合起来可反推 GSV 分，给 gap 等于给分（§0.9-4）。⚠️ 与 §3.1 卡片清单残留矛盾 → §13-Q20 |
| **A2 雷达图（整图）**（v4.0 改） | ❌ **不渲染** | ✅ 4 条序列 | §3.5「**该图仅在 Portfolio 端显示**」（§0.9-5）。原「公司端只少两条基准线」的方案作废 |
| A3 维度详情页 | ✅ 只看本公司 | ✅ | §3.2 |
| A3 **GSV Tab（逐题明细）** | ❌ **不显示** | ✅ | §3.2「公司用户不显示 GSV Tab」 |
| **A3 页头的 GSV 维度分 / Perception Gap**（v4.0 收紧） | ❌ **不可见** | ✅ | §3.5（同 A1 两行）。**v3.x 的「并列展示双方分」作废** |
| **A4 全维 Score Details 页**（v3.5，**v4.4 改**） | ~~V1 无任何界面入口（§13-Q17）~~ → **v4.4 作废**：✅ 只看本公司，**经 ERL Card 右上角 `Full View ›` 进入**（§0.10-D5） | ✅ 由 F2 `View` **或** ERL Card 的 `Full View ›` 进入 | §3.7 + §3.5（`57225d2`）；**2026-08-28 的「不给公司端入口」裁决已被 PRD 推翻，§13-Q17 标记为「已被 PRD `57225d2` 推翻」** |
| **A4 每张维度卡卡头的 `Add New` / `View history`**（**v4.4 新增**，**v4.20 订正文案与渲染条件**） | ✅ 仅 Founder 侧（单端模式，`+ Add New` 照常渲染 → 填报页带 `?dimension={code}`） | ✅ 双端数据一次取回、以 `GSV` / `Founder` 药丸切换查看（~~同屏并列~~ → **v4.20 改回端切换**，§0.24-Z5）；**`+ Add New` 只在 `GSV` 药丸下渲染**（原型口径，§0.24-Z9），`View history` 两侧都有 | §3.5 / §3.7（`57225d2`，§0.10-D5）；原**页级** `+ New` / `View history` 取消。⚠️ 这是**渲染条件**，不是权限口径 —— 后端仍按 §4.3 校验，`addNewUrl` / `historyUrl` 一律由接口 22 下发，前端不拼路径 |
| A4 ~~**GSV Tab 与页尾基准卡**~~ → **GSV 药丸与末位基准 Tab**（**v4.20 改形态**，§0.24-Z4 / Z5） | ❌ **不显示** | ✅ | §3.2（同 A3 口径，服务端裁剪）。⚠️ **基准 Tab 的显隐判据是「端类型」，不是 `benchmark == null`**（§0.24-Z4）—— 服务端在「公司端不下发」与「管理端但该期次无基准记录」两种情况下都发 `null`，按 `null` 判会让还没录过基准的管理端整个 Tab 消失 |
| E1 / E2 差距分析（展示） | ✅ 只读，**仅 `shared = true` 后**（**v4.4**：`shared = false` 时接口 17 对公司端直接返回空态，§0.10-D3） | ✅ 只读（生成即可见，无需 Share） | §3.6（`8324a3f` + `49d9a29`）。~~「Founder / GSV 两套口吻」「PRD 待定功能」~~ → **v4.4 双双作废**：口吻合一（§0.10-D3）、E 模块进 V1（§0.10-D2） |
| **E3 `Share to founder` 按钮**（**v4.4 新增**） | ❌ **不可见** | ✅ 门槛未达成时置灰（该 `(company, period)` 下每个维度的两端都有 `SUBMITTED` 才激活（**2026-09-08**：`is_latest` 列已删，改按 `submitted_at DESC, id DESC` 判存在））；接口 27 | §3.6（`8324a3f`，§0.10-D3） |
| E 手动 Regenerate | ❌ | ✅ | 本设计（自动刷新为主，手动为兜底） |
| B1 Founder 自评问卷 | ✅ **填报** | ✅ 只读查看 | §3.3「portfolio admin 不能代填」 |
| B2 GSV 验证问卷 | ❌ 不可见 | ✅ **填报** | §3.4 |
| B3 评估历史 | ✅ 只看本公司 | ✅ | §3.9 |
| **B3 的 `Portal` 列**（**v4.4 新增行**） | ❌ **不渲染**（公司端只有 Founder 侧数据，该列恒定值、无信息量） | ✅ 渲染 | §3.9（§0.10-D12） |
| **B4 Reset / 丢弃草稿**（**v4.4 新增行**） | ✅ 对自己公司的 Founder 草稿 | ✅ 对 GSV 草稿；接口 28 按 `portal` + `dimension` 定位草稿 | §3.3（`08b7a32`，§0.10-D8） |
| C1–C7 题库配置（含 Publish、**`Dimension Configuration`**、**版本历史**） | ❌ 不可见 | ✅ 且**只能读写本 `organization_id` 的题库与维度配置** | §3.8「**仅 portfolio portal**」+ §4「ERL 配置层级按照租户层级」（v4.0，§0.9-7；**v4.4** 第二个 Tab 由 ~~`Dimension Weights`~~ 改名并扩容为 `Dimension Configuration`，§0.10-D13） |
| D1 基准记录页 | ❌ **不可见** | ✅ | §3.2（基准属 GSV 专属字段） |
| **ERL Card 雷达图下方 `Benchmarkit & Top GSV Quartile ›` 链接**（**v4.4 新增行**） | ❌ **不渲染**（与雷达图同条件 —— **v4.60 起仅指「仅管理端」这一层**：雷达图另有 <3 维度不渲染的门槛，本链接**不跟**，§0.34-Y2） | ✅ | §3.5（`9a203ce`，§0.10-D7） |
| D2 新增基准 | ❌ | ✅ | §4 |
| F2 Portfolio ERL Tab | ❌ 不可见 | ✅ | §3.7「仅 PM / PGM」 |

> ✅ **原 PRD 内部张力已由 PRD 自身关闭（v4.0，§13-Q8-① 关闭）**：v3.x 记的张力是「§3.2 说创始人不显示 GSV 专属字段，§5 说创始人并列查看双方分数」，当时设计裁决为「GSV 维度分对创始人可见」。PRD 2026-09-02（`74f25df`）把 §3.5 改成「创始人**只能查看自己的分数**」，**等于选定了不并列这一边** —— 设计的旧裁决作废。现口径统一为：
>
> - 公司端**只见 Founder 侧的一切**（自己的维度分、综合分、Stage、逐题作答、备注、附件）；
> - 公司端**看不到** GSV 维度分 / GSV 综合分 / Perception Gap / GSV 逐题明细 / 雷达图 / Benchmarkit / Top GSV Quartile；
> - 以上一律**服务端裁剪**，不靠前端隐藏（§4.3）。
>
> ⚠️ **残留矛盾（v4.4：判定已闭合，只剩 PRD 回写）**：PRD §3.1 的卡片内容清单仍把「Perception Gap」列为卡片内容且无端限定，而卡片在公司端也要渲染。**§13-Q20 于 v4.4 关闭** —— PRD §3.5「创始人只能查看自己的分数」已定，设计口径不再待确认；剩下的只是 PRD 自身的清单未同步，列入回写 **§0.10-④ M10**（原 §0.9-④ M4，仍未闭环）。本设计按「公司端不给 gap」落地。

### 4.3 后端强制校验（不依赖前端）

> ⚠️ **业务错误的 HTTP 形态（2026-09-09 全文订正，v4.18）**：本文档此前多处把 ERL 的业务校验失败写作 ~~`400`~~ —— **与实现不符**。ERL 服务层这类失败一律 `throw new BadRequestException(...)`（`assertNotStale`、入参形态校验、集合完整性校验、空入参、组织 / 端类型越权……全是它），而 `gstdev-cioaas-common` 的 `GlobalExceptionHandler` 对 `BadRequestException` / `ServiceException` / `EntityExistException` / `EntityNotFoundException` 四者**统一返回 `HttpStatus.OK` + `Result.fail(message)`**，即 **HTTP 200 + `success: false` + 提示语**（与乐观锁冲突 `OptimisticLockingFailureException` 同形态）。
>
> ⇒ **全文凡由 service 层 `BadRequestException` 产生的错误，一律写作「业务错误（HTTP 200 + `success: false`）」，不再写 400**；本次已逐处替换，保留本条作为决策留痕（原表述见各处 ~~400~~ 删除线）。
>
> ⚠️ **不在本条订正范围内的三类**（它们是真正的非 200，别一起改掉）：① `UnrecognizedPropertyException`（请求体带未知字段）→ **HTTP 400**，这是本仓库唯一会返回 400 的分支；② `MethodArgumentNotValidException` / `BindException`（`@Valid` 校验、参数绑定失败）→ **HTTP 422**；③ 兜底 `Throwable` → **HTTP 500**。
>
> ⚠️ **对前端与测试的实际影响**：抓包核对时**看 `success` 字段与 `msg`，不要看状态码** —— 按状态码 400 写断言会全部失败；前端 axios 拦截器也不会把它当成网络错误。

- 所有接口的 `companyId` 一律**服务端复核**：公司端请求忽略入参 `companyId`，强制取当前登录用户所属公司（`SecurityUtils`）；管理端才允许按入参取。
- **C 模块（题库 + 维度配置）的 `organization_id` 缺省取 `SecurityUtils.getOrganizationId()`，v4.7 起接受可选入参 `organizationId`**（v4.0 的「一律不接受入参」到此作废；v4.4 由「权重」扩为「维度配置」）：不传即登录态组织；传值时服务端按**组织树**复核 —— 只认调用者自身组织或其子孙组织，否则 `BadRequestException("You do not have access to this organization.")`。校验集中在 `ErlAccessService.resolveOrganizationId(...)`，各 service **显式传参**、不从请求上下文夹带。跨组织树读写他人题库 / 维度配置仍直接 `BadRequestException`。
- **维度配置的租户隔离与合法性校验（v4.4 新增，§0.10-R2 / §0.10-D13）**：
  - 接口 23 / 24 只操作调用者 `organization_id` 名下的 `erl_dimension_config` 行（**2026-09-08**：~~`erl_dimension_config_version` / `erl_dimension_config`~~ 两张表已删 / 改名，入参也不再有 `versionId`）；写入时按 `(organization_id, dimension_code)` upsert，**跨组织的 `dimension_code` 天然命中不到**。
  - 接口 24 保存前服务端**必须**校验（**2026-09-08 三处均已反转**）：① 数组每项**显式二选一**：带 `dimensionCode`（已有，必须命中本组织已有行）或带 `isNew: true` + `clientRef`（新增，服务端生成 code）；两者都不带 / 同时带 → **业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3）。**并做集合完整性校验**：当前 `Active` 且**未删除**的集合 恰等于 带 code 的项 ∪ `deactivatedCodes` ∪ **`deletedCodes`**（**2026-09-09 补第三个并集项**，不补则每次删除都被误判为漏传），对不上即**业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3）（**2026-09-08**，防前端漏传造成静默软删 + 身份分叉）；~~新增的 code 不得命中已停用行的拦截~~ **降级为内部重试** —— 用户无法指定 code，天然撞不到旧 code；② **`status = 'Active'` 的维度**的 `weight` 合计**恰为 `100.00`**（~~v4.8：不再区分 ACTIVE / RETIRED~~ 作废；`Inactive` 行不计入），且**至少保留一个 `Active` 维度**；③ 提交里**缺席的维度置 `status = 'Inactive'`（软删，不删行）**（~~物理删除、`status` 入参已删，v4.8~~ 作废）；④ **`deletedCodes[]` 里的每个 code**（**2026-09-09 新增**）必须命中本组织已有行、且**不得出现在任何已发布题库版本的维度快照里**（join `erl_question_config_version` 过滤 `status = 'PUBLISHED'`），并**不得与 `dimensions[]` / `deactivatedCodes[]` 里的 code 重叠**；三者任一不满足即业务错误（HTTP 200 + `success: false`）且**库中无任何写入**（文案与理由见 §6.4-3-⑧⑨⑩）。⚠️ **前端不显示垃圾桶不等于拦住了** —— 抓包可以直接给已发布维度的 code 传 `deletedCodes`，这条服务端校验是唯一的实际防线。校验通过即**就地整组替换**（~~生成新配置版本~~ 作废）。
  - 一切按期次渲染维度、计分、绘雷达图的读接口，**服务端按 `~~erl_company_period_config~~（**2026-09-08 已删表**）` 取当前 `status = 'Active'` 的维度集合**，不接受前端传入的 `dimensionConfigVersionId`。
- **填报写接口的维度合法性（2026-09-07 新增）**：接口 4 / 5 / 28（存草稿 / 提交 / Reset）的入参 `dimensionCode` **必须属于当前 `status = 'Active'` 的维度集合**（**2026-09-08**：~~`~~erl_company_period_config~~（**2026-09-08 已删表**）` → `erl_dimension_config`~~ 两张表已删 / 改名，改查 `erl_dimension_config`；**`Inactive` 的维度也算不合法**；**2026-09-09**：`deleted = true` 的行**更不合法** —— 它已从所有读侧排除，「当前 `Active` 集合」天然不含它，无需额外分支），否则**业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3），并按配置里的规范写法归一大小写。此前只校验「非空 + 转大写」，于是任何满足 `^[A-Za-z0-9]{1,8}$` 的字符串（如 `ZZZ`）都能一路落库成 `SUBMITTED`，污染 ERL Card / 组合层 / Share 门槛判定，还会白触发一次 LLM 差距分析。只读的接口 3 早就在校验（它要拿配置项渲染页头），漏的是这三个写接口。
- **差距分析的 share 可见性（v4.4 新增，§0.10-D3）**：接口 17 在**公司端**调用且该 `(company_id, period)` 的 `shared = false`（含记录不存在）时（**2026-09-19 起该状态位读自 Python 产物**，不再是 Java 库里的列），**直接返回空态**，不下发 `summary` / `items` / `dimensions` 中的任何分析内容。**是不下发，不是下发后前端隐藏**。接口 27（Share）仅管理端可调。
- `portal=GSV` 的读写（B2 填报、A3 的 GSV 逐题明细）、C 模块写接口、D 模块全部接口、E 的生成接口与**接口 27 Share**、F2 的跨公司查询，服务端一律校验调用者为管理端，否则 `BadRequestException`。
- **公司端请求一律裁剪掉以下字段**（v4.0 收紧，PRD §3.5）：`gsvScore`、`perceptionGap`、整个 `radar`、`benchmark*`（`benchmarkitScore` / `topQuartileScore` / `benchmarkPosition`）。**是不下发，不是下发后前端隐藏**。
- **F2 只返回当前用户有权访问的公司集**，不返回全库。
- Java → Python 的两个内部接口带服务间鉴权；Python 侧不重复做公司 ACL，但**必须落 LLM 调用追踪**（复用 `source/llm/`）。
- 违规一律抛异常交 `GlobalExceptionHandler`，**Controller 内不 try-catch**（`standards/architecture.md` §3）。

---

## 5. 数据模型

> 库：PostgreSQL 业务库。Java 侧 `ddl-auto: update` 由 Entity 自动建表；索引 / 约束补 `CIOaas-api/deploy/upgrade_doc/sprint{N}/erl_init.sql`（**2026-09-17 起该脚本不含任何种子数据**）。所有实体继承 `AbstractCustomEntity`，自动带 `created_at / created_by / updated_at / updated_by`。主键 `String(36)` + `@UuidGenerator`（与 `quickbooks_*` 一致）。

**表清单（2026-09-08：12 张 → 11 张，删 2 增 1、改名 3；**2026-09-19：11 张 → 9 张**，差距分析两张搬到 Python，见 §0.33-X1）**

| # | 表 | 小节 | 最近变化 |
|---|------|------|------|
| 1 | `erl_question_config` | §5.1 | **2026-09-08**：`dimension` → `dimension_code`；`version_id` → **`version_no`**，定位键 `(dimension_code, version_no)`，**版本线改为每维一条** |
| 2 | `erl_question_config_version` | §5.1.1 | **2026-09-08**：精简为八列（删 `based_on_version_id` / `change_summary` / `dimension_config_version_id`） |
| 3 | **`erl_question_config_dimension_version`** | §5.1.5 | **2026-09-08 新增**：题库版本 ↔ 维度快照（发布当时的维度集合冻结在此） |
| 4 | **`erl_dimension_config`** | §5.1.3 | **2026-09-08 改名 + 去版本化**：由 `erl_dimension_config_item` 改名，`version_id` → `organization_id`，列名加 `dimension_` 前缀，~~收回 `saved_at` / `saved_by`~~（**2026-09-09 两列删除**，改用审计列 `updated_at` / `updated_by`），重新加 `status`（`Active` / `Inactive`，删除维度改软删） |
| 5 | `erl_assessment` | §5.2 | **2026-09-08**：`dimension` → `dimension_code` + 加 `dimension_name` / `dimension_abbr` 快照；`question_version_id` → `erl_question_config_version_id`；**删 `submission_seq` / `is_latest`**；**2026-09-09：加 `erl_question_config_dimension_version_id`**（可空，→ §5.1.5 快照行，取题一跳直达；存量行由 `V8` 精确回填） |
| 6 | `erl_assessment_answer` | §5.4 | **2026-09-08**：`assessment_id` → `erl_assessment_id`；`question_id` → `erl_question_config_id` |
| 7 | `erl_answer_attachment` | §5.5 | **2026-09-08**：`answer_id` → `erl_assessment_answer_id`；**2026-09-09：删 `file_name` / `file_size`**（推翻 v4.15-⑧「暂不删除」），文件名与字节数改按 `file_id` 查 `files`（`original_name` / `length`），10MB 上限亦按 `files.length` 复核 |
| 8 | **`erl_reference_score`** | §5.6 | **2026-09-08 改名**：由 `erl_benchmark_record` 改名 |
| 9 | **`erl_reference_score_item`** | §5.6.1 | **2026-09-08 改名 + 改列**：由 `erl_benchmark_dimension` 改名；`record_id` → `erl_reference_score_id`，`dimension` → `dimension_code` + 加 `dimension_name` / `dimension_abbr` 快照 |
| ~~10~~ | ~~`erl_gap_analysis`~~ → **`ai_erl_gap_analysis`（Python）** | §5.7 | **2026-09-19 搬到 Python 并改名**（§0.33-X1）：不再由 Java 的 `ddl-auto` 建，DDL 在 `CIOaas-python` `V024__erl_gap_analysis.sql`；`stale` 列删除、新增 `submission_signature`。**旧表留作回滚路径、下个 sprint 再 DROP**。v4.4：删 `audience`，加 `shared` / `shared_at` / `shared_by`（D3） |
| ~~11~~ | ~~`erl_gap_analysis_item`~~ → **`ai_erl_gap_analysis_item`（Python）** | §5.8 | **2026-09-19 搬到 Python 并改名**（§0.33-X1）。v4.4：`item_type` 删 `STRENGTH`（D4）；2026-09-18：加 `NARRATIVE`、列名 `dimension` → `dimension_code` |

**v4.4 删除的两张表**：~~`erl_dimension_weight`~~（原 §5.1.2，被 §5.1.3 取代）、~~`erl_assessment_dimension`~~（原 §5.3，三列上提到 §5.2）。
**2026-09-08 删除的两张表**：~~`erl_dimension_config_version`~~（§5.1.2，维度配置不再版本化）、~~`erl_company_period_config`~~（§5.1.4，期次-配置版本绑定随之取消）。

> **E 模块（Goldie）的两张表（§5.7 / §5.8）无条件建**（**v4.4**，§0.10-D2；**2026-09-19：改由 Python 的版本化迁移建**，不再走 Java `ddl-auto`）：PRD `8324a3f` 已删去 §3.6 标题上的「待定功能」标记，Goldie 进 V1。本节 ~~「E 模块待定，可整块摘除 / 待定期间隐藏 / 恒 null / 仅在需求方确认后才执行」~~ 一类的条件注记 **v4.4 全部删除**，**§13-Q22 关闭**。

### 5.1 `erl_question_config` — 题库（PRD §3.8）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`organization_id`** | **varchar(36)** | **not null** | **2026-09-08 新增裁决**：所属组织（租户）。~~原先本表不加此列、靠版本号间接归属~~ —— 那条链路在「版本线改为每维一条」后**已经断了**（`erl_question_config.version_no` 与 `erl_question_config_version.version_no` 不再是同一个数），故直接补上。取值缺省来自 `SecurityUtils.getOrganizationId()`（§2.1），**v4.7** 起可由可选入参 `organizationId` 指定组织树内的组织（§4.3） |
| **`question_key`** | **varchar(36)** | **not null** | **v3.3 新增**：**跨版本稳定的题目标识**。克隆时原样复制，新增题时生成新 UUID。**版本 diff（`changeType`）与 C 模块写接口定位按它**，不用 `id`。**v3.4**：答案表不再携带它（重基已删除，§0.6-3） |
| **`dimension_code`** | **varchar(8)** | **not null** | **2026-09-08 改名**（原 `code`） **+ 同日裁决：创建时生成、与 `dimension_abbr` 解耦**。**组织内稳定** —— `erl_question_config.dimension_code`、`erl_assessment.dimension_code`、`erl_reference_score_item.dimension_code`、`erl_question_config_dimension_version.dimension_code`、`ai_erl_gap_analysis_item.dimension_code` 五处历史数据全靠它关联，故**一经创建即永不改变**。<br>**生成规则（**2026-09-08 定档**）：`{前缀}{随机后缀}`，如 `OPS4K7M`**<br>· **前缀** = 创建时 `dimension_abbr` 的**前 3 位**（大写化，只保留 `A-Z0-9`；不足 3 位就用实际长度）—— **只是创建时的一次快照，此后 `dimension_abbr` 怎么改都不影响它**。<br>· **后缀** = **4 位随机**，字符集取 **Crockford Base32**（`0-9A-Z` 去掉 `I` / `L` / `O` / `U`）—— 去 `I/L/O/U` 是为了 `0/O`、`1/I/L` 不混淆（这串要被人从日志里抄进 SQL），去 `U` 顺带避开冗余拼出冒犯性单词。<br>· **总长 ≤ 7**，`varchar(8)` **留 1 位余量**（日后加前缀 / 校验位不用 ALTER 五张表）。<br>· **唯一性按全局查重**（生成时 `SELECT 1 WHERE dimension_code = ?` **不带 `organization_id`**）—— 落库约束仍是组织内唯一，但全局查重成本为零，可让「用户新建的维度」彻底免疫于 §5.1 那个未收口的跨租户串号问题。<br>· ⚠️ **生成必须在写事务之前完成**（循环「生成 → 查重 → 命中则重生成」+ 本次请求内维护已分配集合），**不得在整组替换的事务内 catch 唯一冲突重试** —— PostgreSQL 下唯一冲突会把整个事务置为 aborted，同事务内重试必抛 `current transaction is aborted`；且 JPA 延迟 flush 会让冲突在提交那一刻才爆。真撞上了就**整个请求失败重试**，不在事务内继续。<br>· 配置页主列表不展示本列、**也不允许用户指定**；但行内编辑态与 `Show deactivated` 行上**以只读 + 一键复制的形式可见**（运维 / 客服需要它，§8.4-C6） |
| `era_band` | smallint | not null, 1–9 | **题目归属的 level**（PRD §3.3 的「level」即此列）；Era 由此推导（1–3 Founder / 4–6 Harvest / 7–9 Exit）。**逐级解锁与维度分判定的唯一依据**（§7.2） |
| `question_text` | **varchar(2048)** | not null | 题干。**v4.43（2026-09-16）由 ~~`varchar(1024)`~~ 放宽** —— 配置页 C2 / C3 的输入框限 **2000 字符**（前端 `maxLength` + `n / 2000` 字数提示），库留 48 余量，**那 48 不是第二个业务上限**；服务端 `@Size(max = 2048)` 跟列宽走。存量环境跑 `V18__erl_question_config_question_text_2048.sql`（**脚本先于代码发版**） |
| `evidence_source` | varchar(255) | | 来源标签（**`Founder / CFO`**、`Looking Glass`、`SharePoint`、`GSV Assessment`、`Board Transcripts / Fireflies`…）；空显示 `—`。**PRD §3.3 写的 `Founder/CTO` 是输入错误**，需求方 2026-08-28 裁决以 `Founder / CFO` 为准（§13-Q18，待回写 PRD） |
| `sort_order` | int | not null | **同 `dimension_code + era_band` 内的必答顺序**，配置页拖拽即改此列（PRD §3.8）。**level 内的作答顺序**，跨 level 的推进由解锁规则控制（§7.2） |
| **`version_no`** | **int** | **not null** | **2026-09-08 取代 `version_id`**：**按 `dimension_code` 自增**的题目集版本号，从 1 起 —— **每个维度各有一条独立的版本线**（`FRL` 到 v7 时 `PRL` 可能才 v2）。一行只属于「该维度的某一版」；同一维度的版本间整份克隆，故同一道题在该维度的 N 个版本里有 N 行。⚠️ **与 `erl_question_config_version.version_no` 不是同一个东西** —— 后者是**组织级发布批次号**（§5.1.1），两者由 §5.1.5 的快照表建立对应关系 |

约束与索引（**2026-09-08：定位键由 `version_id` 改为 `(organization_id, dimension_code, version_no)`**）：
- `uk_erl_question_config_key (organization_id, dimension_code, version_no, question_key)` —— **同组织同维度的同一版本内**一个 key 只有一行。
- `idx_erl_question_config_version_dim (organization_id, dimension_code, version_no, era_band, sort_order)` —— 配置页与填报页的主查询路径（**恒带 `(organization_id, dimension_code, version_no)`** —— 一次只取一个维度的一版）。
- **题库按组织（租户）单份**（v4.0 改，PRD §4「ERL 配置层级按照租户层级」）：~~`erl_question_config` **不加** `organization_id` —— 组织归属挂在版本表上，题目行经版本号间接归属，避免两处存同一事实~~ → **2026-09-08 作废：本表直接带 `organization_id`**。「间接归属」在版本线改为每维一条后**已经不成立** —— `erl_question_config.version_no`（按维度自增）与 `erl_question_config_version.version_no`（组织级发布批次）**不是同一个数**，已发布只能经 §5.1.5 快照绕回、草稿态则完全无路。**发布批次仍在组织内单份**（Publish 是组织内的全局动作，§7.9），但**各维度的题目集版本线相互独立**。

> **题库版本改为「每维一条版本线」**（2026-09-08 定档）：`version_no` 按 `dimension_code` 自增，一份维度题目由 `(dimension_code, version_no)` 定位。**组织级的「第 n 次发布」仍在 `erl_question_config_version`**（§5.1.1），它与各维度当时 `version_no` 的对应关系逐行落在 `erl_question_config_dimension_version`（§5.1.5）—— 即「本次发布 = FRL 的 v7 + PRL 的 v2 + …」。只改了某一个维度的题目时，**只有那个维度的 `version_no` 前进**，其余维度在新发布批次里仍指向各自的旧版本号，不再整库克隆。
>
> **草稿态的题目集怎么定位（**2026-09-08 补齐**）**：已发布版本经 §5.1.5 快照拿到各维 `question_version_no`；**草稿没有快照行**，故草稿态取该维的 `max(version_no)`。为让这条规则安全，配套两条约束：
> - **新版本号只在写时复制时分配**：某维度本轮首次被编辑时，在**草稿版本行的悲观锁内**算 `version_no = max(version_no) + 1 WHERE organization_id = ? AND dimension_code = ?`（**2026-09-08：补组织作用域**） 并克隆该维题目；未被编辑的维度**不产生新号**，其 `max` 恰等于已发布号，读侧行为自洽。
> - **丢弃草稿必须同事务清理高版本号题目行**（删除该组织所有 `version_no` 大于“当前已发布版本快照里该维的 `question_version_no`”的行）—— 否则那批行会被 `max` 永久命中，成为**幽灵草稿**。⚠️ 本仓当前**没有丢弃题库草稿的接口**（§7.10 边界 5：“不做丢弃草稿”），故该风险当前不可达；**日后若补丢弃接口，这条清理是必选项**。

> ✅ **跨租户串号已收口（**2026-09-08 裁决：补 `organization_id`**）**：本表曾一度不带组织列，导致两个组织都有 `FRL` 时 `(FRL, 1)` 会指向两组题。写 DDL 时这条又暴露出两个具体后果，一并随本次裁决消失：
> - ~~种子数据只能全局插一份（所有租户共享同一组 `(FRL, 1)`）~~ → ~~**恢复为按组织各插一套**（同旧 V1 的做法）~~ → **2026-09-17 作废：种子段已整段删除，一套也不插**。补 `organization_id` 的收口价值不变 —— 题目行按 `(organization_id, dimension_code, version_no)` 定位，各组织互不相干，只是现在这些行一律由业务侧写入。
> - ~~存量迁移必须按维度跨组织重编 `version_no`（A 组 FRL → `(FRL,1)`、B 组 → `(FRL,2)`），导致迁移后 `version_no` 不再对应「该组织的第 n 次发布」~~ → **V5 的重编号步骤直接去掉**，各组织的 `version_no` 保持原语义。
> - 另：§7.9-②’’ 的 `max(version_no)` 与写时复制的取号，**一律改为带 `organization_id` 的作用域**。

**v3.3 删除的三列****v3.3 删除的三列**（依 §0.5-2）：
- ❌ `publish_status` / `published_at` —— 发布状态上移到**版本级**（§5.1.1）。状态位表达不了「同一道题编辑前后的两份题干必须并存」，而这正是「编辑也要经发布」的硬需求。
- ❌ `enabled`（软删除）—— 删除改为**在草稿版本内物理删行**。已发布版本的行不受影响，历史评估按 `erl_assessment.erl_question_config_version_id`（**2026-09-08 改名**）读旧版本，题干天然可还原（§11-24）。

**v4.0 删除的四列**（依 §0.9-1 / -21）：
- ❌ `answer_type` —— 全部题恒 Yes/No。
- ❌ `criteria_founder` / `criteria_harvest` / `criteria_exit` —— 合并为单列 `criteria`；**合并后的单列 `criteria` 亦已于 2026-09-06 按需求方裁决删除**（v4.9，§0.15）。

**v4.9 删除的一列**（依 §0.15-S1）：
- ❌ `criteria`（单段判定标准）—— **判定标准不进需求设计**：配置页不采集、题目行不展示（A5 弹窗一并删除）、不作为 Goldie 输入。本列自始至终**属设计自创**（PRD §3.8 的题目字段只有「题干 / Era Band / Source」），§13-Q25 / 回写 M11 随之关闭。**建表脚本、列注释与种子数据一律无该列**；已建过库的环境执行 `ALTER TABLE erl_question_config DROP COLUMN IF EXISTS criteria;`。
- 本列删除后，题库字段清单**与 PRD §3.8 逐项对齐**，题面不再有任何无处产生的字段。

### 5.1.1 `erl_question_config_version` —— 题库版本（**v3.3 新增**，第 10 张表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`organization_id`** | **varchar(36)** | **not null** | **v4.0 新增**：所属组织（租户）。PRD §4「ERL 配置层级按照租户层级」；取值缺省来自 `SecurityUtils.getOrganizationId()`（§2.1）；**v4.7** 起管理端可用可选入参 `organizationId` 指定**自身组织树内**的组织（§4.3） |
| `version_no` | int | not null | **组织内**递增的**发布批次号**（v4.0 由「全局」改），从 1 起；配置页显示 `Published v3` / `Draft v4`。⚠️ **2026-09-08：与 `erl_question_config.version_no` 不是同一个东西** —— 后者按 `dimension_code` 自增、是各维度题目集各自的版本号（§5.1），两者的对应关系落在 §5.1.5 |
| `status` | varchar(16) | not null | `DRAFT`（在改，未生效）/ `PUBLISHED`（已生效） |
| ~~`is_latest`~~ | — | — | ❌ **2026-09-09 删除**（推翻 v4.5-L1 / -L3 / -L5 / -L6）：~~本行是否为当前正在使用的最新版本~~ → 判据回到**本组织 `status = 'PUBLISHED'` 中 `version_no` 最大的那一条**（新发起的评估绑定它，§7.9-①）。<br>**本次删列不丢任何不变量**：`version_no` 在组织内有唯一索引 `uk_erl_question_config_version_no`，且草稿号恒为 `max + 1`，故「`PUBLISHED` 里 `version_no` 最大」**天然唯一、不需要次级排序键** —— 与 2026-09-08 删 `erl_assessment.is_latest`（判据换成 `submitted_at DESC, id DESC`，`submitted_at` 无唯一约束、**丢掉了「至多一条 SOT」的索引兜底**，§5.2）**性质不同**。<br>**不用 `published_at` 作判据**：它只是时间戳、无唯一约束（同微秒两次发布就并列），草稿行还是 `null`。<br>**唯一的陷阱**：草稿行的 `version_no` 恒为最大，故取在用版本**必须带 `status = 'PUBLISHED'`**，漏了就会把未发布的草稿当成在用版本发到问卷上（§11-88 有专项用例守它）。<br>**附带收益**：Publish 不再需要「先把上一版置 `false`、再把本版置 `true`」的两阶段 flush（那个顺序本是为了绕开下面那条部分唯一索引），现在**一行都不碰上一版** —— 而那段 `saveAndFlush(previous)` 正是「发布题库会改写上一版的最后编辑人 / 时间」这条技术债的成因（触发审计基类 `@PreUpdate` 回填），随本次一并闭掉 |
| `published_at` | timestamp | | `PUBLISHED` 才有值 |
| `published_by` | varchar(128) | | 发布人姓名快照 |
| `version` | bigint | not null, default 0 | **2026-09-07 新增**：JPA `@Version` 乐观锁版本号。草稿版本行是**同组织多管理员共编**的对象：A 的加题事务持有草稿行时、B 把同一行发布成 PUBLISHED，A 随后把新题写进那个版本号（`erl_question_config.version_no`）—— 一道从未发布过的题瞬间进入线上问卷。题目的增删改排写的是 `erl_question_config`、**不碰本表**，故防线是 `ensureDraftVersion` 对草稿行发的那条带版本谓词的 UPDATE。列由 `V4__erl_optimistic_lock.sql` 建，**必须部署前执行** |

约束（**v4.0：全部加 `organization_id` 前缀**）：
- **部分唯一索引** `uk_erl_question_config_version_draft ON erl_question_config_version (organization_id) WHERE status = 'DRAFT'` —— **同一组织内同时最多一份草稿版本**。题库按组织单份，草稿也就按组织单份（同组织的多个管理员共享同一份草稿，后果见 §7.9-④）。
- `uk_erl_question_config_version_no (organization_id, version_no)` —— **2026-09-09 起它同时是「至多一个在用版本」的兜底**：在用版本 = `PUBLISHED` 里 `version_no` 最大的那条，组织内号唯一 ⇒ 结果必然唯一。
- 索引 `idx_erl_question_config_version_status (organization_id, status, version_no DESC)` —— 版本历史列表、建草稿时算 `version_no = max + 1`，**2026-09-09 起又回到「取本组织最新已发布版本」的主路径**（v4.5 曾把这条路让给 `is_latest`，该列已删）。
- ~~**部分唯一索引** `uk_erl_question_config_version_latest ... WHERE is_latest`~~ → ❌ **2026-09-09 随列一并删除**（v4.5 新增）：它守的「正在使用的版本只有一个」已由 `uk_erl_question_config_version_no` 天然保证。**本表现存部分唯一索引只剩 `uk_erl_question_config_version_draft` 一条。**

**2026-09-08 删除的三列**（本表精简为 `id` / `organization_id` / `version_no` / `status` / `published_at` / `published_by` / `version` **七列** —— **2026-09-09** 再删 `is_latest`，由八列变七列）：
- ❌ `based_on_version_id`（克隆来源版本）—— 写时复制建草稿时只是记一笔来源，读侧没有任何功能依赖它；版本序列由 `version_no` 表达即可。
- ❌ `change_summary`（发布时的变更摘要快照：`added` / `modified` / `removed` / `reordered` 四个计数 + 受影响维度）—— 变更摘要不再落库快照，只在接口 9 实时算（供 Publish 按钮与确认框）；**接口 25 不再返回 `changeSummary`**。
- ❌ `dimension_config_version_id`（v4.10 新增，发布当时生效的维度配置版本 id）—— **2026-09-08 起改由新表 `erl_question_config_dimension_version`（§5.1.5）承接**：不再用一个 id 引用整份配置版本，而是把发布当时的 `dimension_code` / `dimension_name` / `dimension_abbr` / `sort_order` **逐维抄进快照表**，「发布时的维度」因此不再依赖维度配置留存历史。

> **为什么不用「双表（草稿表 + 正式表）」**：双表本质就是只能存两代的版本化，却要把 `erl_question_config` 的全部列复制一份 DDL 并长期同步维护；版本表方案用版本号表达同样的语义，还顺带给了历史评估一个天然的题干快照来源（省掉软删）。

> **~~`erl_dimension_weight`~~（原 §5.1.2，第 11 张表，v4.0 新增）→ v4.4 整表删除**（§0.10-R2 / -D1）：维度不再是编译期枚举、权重也不再是「每组织一份、恒五行」的**当前值**，两者并入可配置的维度集合。原表承载的两条事实（有哪些维度、每维权重多少）现在都落在 **`erl_dimension_config`**（§5.1.3）上。⚠️ **2026-09-08**：原先为它提供版本序列的 `erl_dimension_config_version` 与期次绑定表 `erl_company_period_config` **也已一并删除**（见下两个墓碑节）。

### 5.1.2 ~~`erl_dimension_config_version`~~ —— **2026-09-08 整表删除**

~~维度配置版本表（v4.4 新增；PRD §3.8 / R2）~~ → **2026-09-08 整表删除**：**维度配置不再版本化**。原表承载的三件事各有新落点 —— 「有哪些维度、每维权重多少」落在去版本化后的 `erl_dimension_config`（§5.1.3，每组织一份**当前配置**），「谁在什么时候保存的」由 `erl_dimension_config` 的**审计列 `updated_at` / `updated_by`** 承接（**2026-09-09**：一度为此收回的 `saved_at` / `saved_by` 两列已删除，理由见 §5.1.3），「某个题库版本发布当时的维度长什么样」改由新表 `erl_question_config_dimension_version`（§5.1.5）逐行快照。原表的 `version_no` / `is_latest` 两列与三个索引（`uk_erl_dimension_config_version_no` / `uk_erl_dimension_config_version_latest` / `idx_erl_dimension_config_version`）一并消失。

> ⚠️ **删表后失去落点的口径**：① 接口 24 Save 由「每次保存生成新版本」改为**就地整组替换**（§6.4 / §7.11），**改动前的旧值不再留存**；② `erl_company_period_config` 失去绑定对象，已一并删表（§5.1.4）；③ **R2「历史期次永不漂移」整条失效** —— 改权重 / 增删维度会回溯改变历史期次的综合分、Stage、雷达图，**§13-Q21 重新打开**。

### 5.1.3 `erl_dimension_config` —— 维度集合与权重（**2026-09-08 由 `erl_dimension_config_item` 改名并去版本化**；PRD §3.8 / D1）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`organization_id`** | **varchar(36)** | **not null** | **2026-09-08 取代 `version_id`**：所属组织（租户）。维度配置**每组织一份当前值**，不再挂在配置版本下；取值缺省来自 `SecurityUtils.getOrganizationId()`（§2.1），**v4.7** 起可由可选入参 `organizationId` 指定组织树内的组织（§4.3） |
| **`dimension_code`** | **varchar(8)** | **not null** | **2026-09-08 改名**（原 `code`） **+ 同日追加裁决：改为系统生成的不透明标识**。**组织内稳定** —— `erl_question_config.dimension_code`、`erl_assessment.dimension_code`、`erl_reference_score_item.dimension_code`、`erl_question_config_dimension_version.dimension_code`、`ai_erl_gap_analysis_item.dimension_code` 五处历史数据全靠它关联，故**一经创建即永不改变**。<br>**生成规则（**2026-09-08 定档**）**：新增维度时由**服务端随机生成一个唯一值**，**与 `dimension_abbr` 无任何关系**，此后新增 / 修改都**不跟随 `dimension_abbr` 变动**。~~v4.8：新增时取新增栏里填的 `Abbreviation`、大写化后写入~~ **作废**。<br>**具体形式**：**纯随机码（8 位大写字母 + 数字）**（**已于 2026-09-08 审查后否决，改为前缀 + 4 位随机**）（如 `K7M2XQ4B`）。不用 UUID 的理由：本列为 `varchar(8)` 且被上述五处引用，改 UUID 要把五处列宽拉到 36（连带五张表的 DDL 与实体），代价明显更大；36⁸ ≈ 2.8×10¹² 的空间配下方的唯一索引重试已绰绰有余。<br>**生成时碰撞**（命中 `uk_erl_dimension_config`）则**重新生成并重试**（上限 5 次，超限报 500）。<br>配置页**不显示本列**（§8.4-C6），行内编辑能改的只有名称 / 缩写 / 权重 |
| **`dimension_name`** | **varchar(64)** | **not null** | **2026-09-08 改名**（原 `name`）：全称，如 `Financial Readiness` |
| **`dimension_abbr`** | **varchar(8)** | **not null，1–8 字符** | **2026-09-08 改名**（原 `abbr`）：显示缩写。~~v4.8：新增时它就是 `dimension_code` 的来源~~ → **2026-09-08：与 `dimension_code` 解耦**，code 仅在**创建时**取它前 3 位做前缀，此后本列**可随时改名、code 一律不跟随**。雷达图顶点、A3 维度 chip、F2 列头、A4 卡头徽章用它。<br>**唯一性：无（**2026-09-15 定档**）** —— ~~**同一组织内 `Active` 的行不得重复**（部分唯一索引，见下）。~~ ~~一度写作「不要求唯一」~~ ~~**作废** —— 解耦 code 并不要求 abbr 非唯一，而重名会直接造成 F2 两列同名、雷达图两个同名顶点、送给 LLM 的维度列表歧义、`Activate` 无法判别。`Inactive` 行**不占用**缩写（否则停用过的缩写永久不能再用）。~~ → **2026-09-15 需求方裁决：新增维度不做任何重名 / 重缩写校验**，部分唯一索引 `uk_erl_dimension_config_abbr` **整条删除**（v4.31）⇒ **同组织内本列可以任意重复**（两个 `Active` 维度同缩写、甚至同名都合法），它们靠 `dimension_code` 区分；上面那段「重名的代价」**仍然是事实**（F2 两列同名、雷达图同名顶点、LLM 维度列表歧义），只是需求方明确接受。⚠️ **`1–8` 字符的长度约束保留**（列宽就是 `varchar(8)`，接口 24 仍校验，§6.4-2-③） |
| `sort_order` | int | not null | 展示顺序：维度卡列表、雷达图顶点、题库 Tab、F2 列序、Gap 状态点一律按它排（PRD §3.8 拖拽排序即改此列） |
| `weight` | numeric(5,2) | not null, 0–100 | **百分比数值**（如 `20.00` 表示 20%）。**同一组织内 `status = 'Active'` 的行合计必须 = 100.00**（2026-09-08：范围由「同一版本内全部行」改为「同一组织内的启用行」—— 软删后 `Inactive` 行仍在表里，若计入则永远凑不满 100），由服务端在保存时校验（§6.4 接口 24）。`Inactive` 行的 `weight` **原样保留不清零**，供历史回看 |
| **`status`** | **varchar(16)** | **not null，默认 `Active`** | **2026-09-08 重新加回**（v4.8 曾整列删除）：维度启用状态，取值 **`Active`（启用）/ `Inactive`（停用）**（**2026-09-09 改名**：原 `Activate` / `Deactivate` —— 这一列表达的是**状态**，该用形容词，原值是动词、读起来像动作。列名 / 类型 / 语义一字未改，只换两个字面值；存量库由 `V10` 改值并按新谓词重建部分唯一索引，Java 侧 `fromDbValue` **临时兼容旧值**以免脚本未跑时读侧就炸）。**配置页的「删除维度」= 置 `Inactive` 的软删**（**不物理删行**）：停用后该维度不再出现在填报 / 计分 / 雷达图的当前口径里，但行仍在，历史数据（`erl_assessment.dimension_code`、`erl_reference_score_item`、Gap items 与 §5.1.5 的发布快照）仍能反查到它的名称与缩写。`Inactive` 的维度可再置回 `Active` 恢复。**2026-09-09**：置 `Inactive` 的触发入口由垃圾桶换成**电源按钮**（`PoweroffOutlined`），恢复入口由 `Show deactivated` 开关换成面板底部常显的 `Deactivated Dimensions` 区块 —— **落库语义一字未改**（§8.4-C6 / §0.21-X10） |
| **`deleted`** | **boolean** | **not null，默认 `false`** | **2026-09-09 新增**（需求方当日裁决，§0.21-X1）：配置页的「**删除**」= 置 `deleted = true`。**行与 `weight`、`dimension_name` / `dimension_abbr` 全部原样保留**（历史数据仍按 `dimension_code` 反查得到），但**所有读侧一律排除**，页面上**没有恢复入口**（既不在主列表、也不在 `Deactivated Dimensions` 区块）。**只有 `deletable = true`（该 code 从未进入任何已发布题库版本的维度快照）的维度才允许删**，否则服务端拒绝并要求改用停用（§6.4 接口 24）。<br>⚠️ **与 `status` 正交，不是它的第三个取值**：`Active + false` = 主列表 / `Inactive + false` = `Deactivated Dimensions` 区块 / `deleted = true` = 完全不显示。合并成三值枚举后，「删掉一个当前**已停用**的维度」（可达：从未发布过的维度可以先停用再删除）就只能靠丢掉原状态来表达（§0.21 开头）。<br>⚠️ **删除不改 `status`** —— 一个被删掉的行 `status` 仍是它被删那一刻的值。所以**每一处按 `status` 过滤的读都必须同时过滤 `deleted = false`**，漏一处就会漏出一个用户已经删掉、且再也管理不到的维度。 |

> **~~`saved_at` / `saved_by`~~ —— 2026-09-09 两列删除**：「这份配置上次保存于何时 / 谁保存的」改由**审计基类的 `updated_at` / `updated_by`** 承接。**接口 23 / 24 的契约一字不变**（出参仍是 `savedAt` / `savedBy`，入参仍收 `savedAt` 乐观锁令牌，前端零改动），只换取数口径：`savedAt` = 该组织**全部行**（含 `Inactive`；**2026-09-09 明确：也含 `deleted = true` 的行**）的 `max(updated_at)`，`savedBy` 取其中 `updated_at` 最大那一行的 `updated_by`。
> - ⚠️ **为什么 `savedAt` 必须算上已删行**（**2026-09-09**，§0.21-X3）：删除也是一次写入，**必须 bump 乐观锁令牌**。反例：A 删掉维度 X，B 的页面是删除**之前**打开的、本地数组里**还有 X**。若 `max()` 把已删行排除在外，A 那次删除就没抬高令牌 ⇒ B 的 `savedAt` 仍然匹配、**被判为无冲突**，B 那份含 X 的数组照常提交 —— X 被当成「已有维度」upsert 回 `Active`，**A 的删除被静默撤销**，而两次请求都返回成功、日志一行不报。算上已删行，B 会正常拿到「配置已被他人修改，请重新加载」，重载后 X 不再出现，这才是 v4.15 立这把锁时要的行为（同 §11-86-⑮ 的并发用例）。
> - **为什么两列是冗余的**：~~设列的理由曾是「整组替换只有实际发生变化的行会动 `updated_at`」，而 §7.11 的保存流程会**先把该组织全部已有行落成 `Inactive` 并 flush、再盖终态**（为腾空 `uk_erl_dimension_config_abbr` 这个部分唯一索引）—— 真发生变更的保存必然 bump 全组行的 `updated_at`，独立列拿不到任何额外信息。~~ → **2026-09-15 理由换了一半**（`parkAll` 已随该索引一并删除，保存改为单阶段直接写终态，v4.31 / §7.11-②）：`max(updated_at)` 此后**只被真正发生变更的行 bump**。**两列仍然冗余、结论不变** —— 乐观锁要的只是「有变更就抬高令牌」：有变更必 bump，无变更则令牌不变、下一次照样校验得过，独立列依旧拿不到额外信息。
> - ⚠️ **实现硬约束：`savedAt` 必须从库里读回**（`select max(d.updatedAt) …`），**不得**取一级缓存里实体的字段值 —— `updated_at` 落库是 `timestamp(6)`（微秒），而审计基类写入的 `Instant.now()` 带纳秒；回显未截断的纳秒值，同一个管理员**连续保存第二次必被乐观锁判成「已被他人修改」**，而根本没有第二个人。也**不能靠客户端侧 `truncatedTo(MICROS)` 规避** —— pgjdbc 文本模式下 PG 是**四舍五入**到微秒，截断与舍入会差 1 微秒。
> - **`savedBy` 的一处边界**（已接受）：接口 23 默认不带停用行，若全局 `updated_at` 最大的那行恰是 `Inactive` 行，`savedBy` 会取到这批行里较早的那个保存人 —— `savedAt` 不受影响（它查的是全部行），而 `savedBy` 当前**无任何展示方**（前端只存进 state 不渲染），故不为它多查一次库。

> **取值改名的三处连带影响**（**2026-09-09**）：
> - ~~**部分唯一索引的谓词跟着改**：`uk_erl_dimension_config_abbr ... WHERE status = 'Active'`。⚠️ 存量库若只 `UPDATE` 数据、不重建索引，旧谓词（`= 'Activate'`）此后**一行都命不中** —— 「同组织启用维度的缩写唯一」这条约束会**静默失效**，不报任何错。`V10` 把这一步与改值放在同一个事务里。~~ → **2026-09-15 作废**：该索引已由 `V15` **整条删除**（v4.31），「同组织启用维度的缩写唯一」这条约束整条取消，谓词对不对已无后果。`V10` 本身**不改**、仍按原样执行。
> - **线上取值统一为 `Active` / `Inactive`**：接口 23 / 24 与卡片、评分详情里的 `status` 出参**此前实际下发的是枚举名 `ACTIVATE` / `DEACTIVATE`**（`ErlDimensionConfigConverter` 走的是 `.name()`），与本文档写的取值**并不一致** —— 本次一并收口：**库值 = 线上值 = 文档值**同一套词。前端不消费该字段（`Retired` 灰标是靠「接口 23 的 code 集合里还有没有它」算的），故**前端零改动**。
> - **读侧临时兼容旧值**：`ErlDimensionConfigStatusEnum.fromDbValue` 除认 `Active` / `Inactive` 外**也认旧值** `Activate` / `Deactivate`（映射到同一枚举、不抛异常）；**写侧永远只写新值**。⚠️ **2026-09-09 审核订正**：这条兼容**只保住「实体读到旧值不抛异常」这一件事，保不住按 `status` 过滤的查询** —— ERL 的热读路径是在 SQL 里过滤的（`findByOrganizationIdAndStatusOrderBySortOrderAsc(org, ACTIVE)`，转换器绑定的字面值是 `'Active'`），库里还是旧值时**一行都命不中**：维度列表空、卡片 / 雷达 / Score Details / 组合层 / Goldie 全空、接口 24 必报业务错误（~~400~~，2026-09-09 订正，§4.3），而且**不报错**。所以 `V10` **不是**「先发代码也撑得住」，见下一条。
> - **`V10` 的发版顺序（**2026-09-09 审核订正**）**：**必须与代码同批，且脚本紧跟代码之后、窗口以分钟计；两个方向都坏，没有「不炸」的方向**。① **先发代码**（库还是旧值）⇒ 新代码按 `'Active'` 过滤一行命不中：维度列表空、卡片 / 雷达 / Score Details / 组合层 / Goldie 全空、接口 24 收到空入参报**业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3）（**静默空数据，比 500 难查**；但整组锁读 `findForUpdateByOrganizationId` **不带 `status` 过滤**，老行没丢、脚本跑完即恢复），~~代价是窗口内新写入不受「缩写唯一」保护~~（**2026-09-15：这项代价已消失** —— 「缩写唯一」整条取消、索引由 `V15` 删除，v4.31）。② **先跑脚本**（旧代码还在跑）⇒ 同样的静默空数据**再加两条 500** —— 配置页的全量取数（**当时是 `Show deactivated` 开关，2026-09-09 起已改为恒带 `includeDeactivated=true`**，§8.4-C6）与接口 24 的整组读会把新值读进**旧** `fromDbValue`，抛 `IllegalArgumentException`，**保存路径彻底堵死**。⇒ **选①、把窗口压到最短**。~~原先写作「建议先发代码、再跑脚本，读侧靠临时兼容撑得住」~~ —— 结论方向对、理由是错的，已作废。`V10` 全环境跑完、确认库里只剩新值后，这段兼容就是死代码、应连同两个 `LEGACY_*` 常量与那条单测一起删掉（已记入 `CIOaas-api/docs/待优化项.md`）。
> - **入参字段名不改**：接口 23 的 `includeDeactivated` 与接口 24 的 `deactivatedCodes` **保持原名**（改名属接口契约破坏，且它们表达的是「动作 / 要停用哪些」而不是状态值本身），只是它们指向的那个状态值现在叫 `Inactive`。

约束与索引（**2026-09-08：键位由 `version_id` 改为 `organization_id`**）：
- `uk_erl_dimension_config (organization_id, dimension_code)` —— 同一组织内一个 code 只有一行。
- 索引 `idx_erl_dimension_config_org (organization_id, sort_order)` —— 按组织取有序维度列表的主查询路径。
- ❌ **2026-09-15 删除** ~~**部分唯一索引** `uk_erl_dimension_config_abbr ON erl_dimension_config (organization_id, dimension_abbr) WHERE status = 'Active' AND deleted = false`（**2026-09-08 新增**；谓词于 **2026-09-09 加了一半**，§0.21-X2）—— **同一组织内启用且未删除的缩写唯一**。~~ → **需求方 2026-09-15 裁决「新增维度不做任何重名 / 重缩写校验」**（v4.31）：该索引**整条删除**（迁移 `V15__erl_dimension_config_drop_abbr_unique.sql`，`V1__erl_init.sql` 就地不再建它），**本表此后只剩 `uk_erl_dimension_config (organization_id, dimension_code)` 一条唯一约束**；同组织可以有两个 `Active` 维度共用一个缩写、甚至同名，靠 `dimension_code` 区分。⚠️ **ERL 的部分唯一索引由此由 3 条减为 2 条**：`uk_erl_question_config_version_draft`（§5.1.1）与 `uk_erl_assessment_draft`（§5.2）。
  - ~~⚠️ **漏掉 `deleted = false` 这半边的后果不是约束失效，而是约束过紧且用户无法自救**：删除**不改** `status`（§上表 `deleted` 行），已删的行仍满足 `status = 'Active'`，于是它**永久占着自己的缩写** ⇒ 「删掉 `OPS`、再新建一个也叫 `OPS` 的维度」**永远撞唯一冲突**，而那一行在页面**两处都看不见**（不在主列表、也不在 `Deactivated Dimensions` 区块）—— 用户既查不出是谁占的，也没有任何入口把它放出来，只能找 DBA。对比 `Inactive` 行：它至少在常显区块里看得见、可 `Activate`。**这是本次加列最容易漏、且最难从现象反推的一处**（§11-86-⑳ 有对应用例）。~~ → **2026-09-15 作废**：索引整条删除后「谁占着这个缩写」不再是个问题（同缩写本就允许并存），v4.31。
  - ~~`deleted = true` 的行**不占用**缩写，与 `Inactive` 行同理（否则删过的缩写永久不能再用）。**部分唯一索引因此由三个增至四个**（§5.1.1 两个 + §5.2 一个 + 本条）—— **2026-09-09 更正为三条**：`uk_erl_question_config_version_latest` 随 `is_latest` 删列一并消失（§5.1.1），故现存 = `uk_erl_question_config_version_draft`（§5.1.1）+ `uk_erl_assessment_draft`（§5.2）+ 本条。~~ → **2026-09-15 更正为两条**：本条随索引删除一并消失，现存 = `uk_erl_question_config_version_draft`（§5.1.1）+ `uk_erl_assessment_draft`（§5.2）。
- **乐观锁**（**2026-09-08 新增**）：本表是「同组织多管理员整组替换」的写入对象，而整组替换 + 缺席即软删 = 典型的 lost update（A 加维度 X 保存，B 随后保存自己那份不含 X 的数组 ⇒ X 静默被置 `Inactive`，A 完全无感）。因此：**接口 24 入参必须带上接口 23 返回的 `savedAt` 作为前置条件**，不匹配即返回「配置已被他人修改，请重新加载」（与 §11-91-⑦ 的乐观锁口径一致）。**2026-09-09 换底**：该令牌取自审计列 —— 该组织**全部行**的 `max(updated_at)`，独立的 `saved_at` / `saved_by` 两列已删除（见上方墓碑说明）。
- 保存仍是**整组替换**（一次提交整份启用维度集合），不支持单维更新 —— 否则中间态必然破坏「合计 100%」。⚠️ **去版本化后「整组替换」写的是本组织的这批行本身**（就地覆盖 `dimension_name` / `dimension_abbr` / `sort_order` / `weight` / `status`），**改动前的旧值不再留存**；提交里缺席的维度不删行，改为置 `status = 'Inactive'`。**2026-09-09**：删除同样不删行，改为置 `deleted = true`；「缺席」此后**只表示停用**，删除必须由 `deletedCodes[]` 显式点名（§6.4 接口 24）。
- ⚠️ **两处读侧刻意不过滤 `deleted`**（**2026-09-09**，§0.21-X3）—— 其余每一处读都必须过滤：
  - **全局 code 占用探针 `existsByDimensionCode`**：已删维度的 `dimension_code` **永久保留占用**，生成新 code 时照旧要避开它。理由是那个 code 仍被**五张表**当历史数据引用（⚠️ **2026-09-19 起其中一张在另一个库里** —— `ai_erl_gap_analysis_item` 归 Python，§0.33-X1。这让「永久保留占用」的论证**更强而不是更弱**：跨库引用没有外键、没有级联，一旦 code 被复用，Python 库里那些历史条目会**静默挂到另一个维度名下**，而探针是唯一的防线）（`erl_question_config` / `erl_assessment` / `erl_reference_score_item` / `erl_question_config_dimension_version` / `ai_erl_gap_analysis_item.dimension_code`）—— 若把它重新分配给一个新维度，**旧历史会静默地挂到新维度身上**：库里每一行都长得完全正常，只有对着历史列表看名字才发现串了，而那时已无从判断哪些行属于哪一个维度。
  - **`savedAt` 的 `max(updated_at)`**：见上方 `saved_at` 墓碑说明里的乐观锁反例。
- **迁移**（**2026-09-09**；**形态已于 2026-09-09 按脚本实际写法订正**）：`deploy/upgrade_doc/sprint118/V11__erl_dimension_config_add_deleted.sql`。~~加列（`boolean not null default false`）（`ADD COLUMN IF NOT EXISTS` 幂等）+ DROP 并按新谓词重建 `uk_erl_dimension_config_abbr`~~ —— **这正是脚本文件头点名「不能这么写」的那个形态**。实际是**四步同处一个 `DO` 块**（外加一道「表不存在就 `RAISE NOTICE` + `RETURN`」的守卫）：① `ADD COLUMN IF NOT EXISTS deleted boolean`（**先建成可空**）→ ② `UPDATE ... SET deleted = false WHERE deleted IS NULL` 回填存量行 → ③ `ALTER COLUMN ... SET DEFAULT false` + `SET NOT NULL` → ④ `DROP INDEX IF EXISTS` + 按新谓词 `CREATE UNIQUE INDEX`（`WHERE status = 'Active' AND deleted = false`，索引名与键位不变）。**为什么不能一句 `ADD COLUMN ... NOT NULL DEFAULT false`**（PG 11+ 本来不重写表）：**列已经存在**的库上 `IF NOT EXISTS` 会把整条跳过，**连带 `DEFAULT` 与 `NOT NULL` 一起跳过** —— 而「列已存在但可空、且是 `ddl-auto` 建的」正是「代码先上线环境」的常态（`V4` 的 `version` 列踩过，见 `sprint118/README.md` 的「`ddl-auto` 建列不带默认值」）。拆成三步后，无论列存不存在、存量行有没有值，跑完都收敛到同一个终态。`V1__erl_init.sql` **已就地含该列**（~~与新谓词~~ —— **2026-09-15 起 `V1` 就地不再建 `uk_erl_dimension_config_abbr`**）。发版顺序约束见 §10.1 与 §0.21-X11（**不是「可提前任意时间跑」**）。
- **迁移**（**2026-09-15 新增**，v4.31）：`deploy/upgrade_doc/sprint118/V15__erl_dimension_config_drop_abbr_unique.sql` —— `DROP INDEX IF EXISTS uk_erl_dimension_config_abbr`，**只删索引、不动任何数据与列**。幂等，**存量环境必须跑**（`V11` 第 ④ 步刚把它按新谓词重建过）；**全新环境** `V1` 已就地不再建它 ⇒ 跑它是 no-op。⚠️ **与 `V11` 的先后顺序有要求**：必须排在 `V11` **之后**（`V11` 会重建该索引，先跑 `V15` 等于白删）。**发版方向无约束** —— 删约束是纯放宽，脚本先跑（旧代码仍带着已被删掉的重复校验，行为不变、只是比库更严）或代码先上（新代码不再校验，而库里索引还在 ⇒ 建重名维度会撞唯一冲突，报「缩写重复」类错误）都不会静默出错，但**代码先上会让用户在窗口内看到一个已经取消的拦截**，故仍按「脚本先跑、代码紧跟」执行。

> **`dimension_code` 与 `dimension_abbr` 的关系（**2026-09-08 定档**）**：
> - **新增**：用户只填 `Dimension name` 与 `Abbreviation`；`dimension_code` 由**服务端生成**为 `{abbr 前 3 位}{4 位随机}`（如 `OPS4K7M`），前端不传、不可指定。
> - **修改**：改 `Abbreviation` **不会**带动 `dimension_code`，两者此后永不同步。前缀只是**创建时的历史提示**，不是对当前 `abbr` 的断言 —— `OPS4K7M` 的维度今天可能叫 `Finance (FIN)`，**排查时以 `dimension_abbr` 为准**。
> - **为什么不用纯随机码**（**2026-09-08 审查后改定**）：纯随机码让 code 全站不可读，代价集中在四处 —— ① **LLM 需逐字回传 code**，拄错一位就被 §9 当成「该维无 gap」静默丢弃；② 日志 / URL / 手工改数全靠回表 join；③ 客服无处可查；④ 实现极易写成 `UUID.substring(0,8)`（那是 16⁸ 的纯十六进制，与本规则不符）。加一个前缀就能把这四样一起拿回来，**而不损失任何不可预测性与不可变性**。
> - ~~**种子数据例外**：`FRL / PRL / BERL / RRL / TRL` 仍使用这五个**可读 code**（建库初始化数据、不走「新增」路径）。~~ → **2026-09-17 作废**：种子段已删，**新库不再有任何可读 code**，全部走生成路径。这五个 code 在全文与 PRD 里只作**叙述举例**；**存量库**里它们仍是真实数据行，故下面那条「格式无约束」的结论**照旧成立**。
>
> ⚠️ **`dimension_code` 无任何格式约束（**2026-09-08 明确**）**：同一列里既有存量库遗留的 `FRL`（3 位）又有 `OPS4K7M`（7 位），**任何正则 / 长度 / 前缀 / 大写断言都会误杀一方**。合法性的**唯一判据是「命中 `erl_dimension_config` 中该组织的行」**；大小写不敏感比较仅作输入容错，**不得用于生成或存储归一**。受影响需同步的三处：§4.3 / §0.18-L6 里的 `^[A-Za-z0-9]{1,8}$` 正则、§0.17-K1 的「大小写不敏感的 code 集合交集」。
>
> ⚠️ **存量环境的影响（**2026-09-08 订正** —— 原写「无 DDL 变更、无数据迁移」是错的）**：① `dimension_code` 的**列宽与类型确实一字未改**（仍 `varchar(8)`），现存的 `FRL/PRL/BERL/RRL/TRL` 与按 v4.8 规则建过的用户维度（code = abbr 大写化）**原样保留、不重新生成**，新规则只作用于此后新增的维度；② ~~**但本节同时新增了部分唯一索引 `uk_erl_dimension_config_abbr`，这就是一项 DDL 变更** —— 而旧模型从未要求 `abbr` 唯一，**存量行可能已有重复缩写，建索引会失败并回滚整个事务**；迁移脚本必须先跑去重预检（`V5` 第 5-e 步）~~ → **2026-09-15 作废**：该索引已由 `V15` **整条删除**（v4.31），「存量行有重复缩写」此后是**合法状态**，去重预检不再有对象（`V5` 本身不改、仍按原样执行）；③ 新表 `erl_question_config_dimension_version` 需建表 + **回填**（存量环境从未冻结过发布当时的维度名，回填只能回退到今天的名字 —— 这是近似值，不是真历史）。
>
> ⚠️ **前后端必须同一个发版周期上线**（**2026-09-08**）：存量前端对新增行也会发 `code`（= abbr 大写化），而新服务端把「带了 code」判为「已有维度，必须命中已有行」⇒ **业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3）。若无法同发，服务端需一版兼容：带了 code 但命中不到 ⇒ 忽略并当新增，打 WARN。

> **维度数量不再固定为五**> **维度数量不再固定为五**（§0.10-D1）：`FRL / PRL / BERL / RRL / TRL` 只是**叙述用的举例**（**2026-09-17 起脚本连种子都不插**），不是模型约束（PRD §3.8 的维度列表本身就写作 `FRL / PRL / BERL / RRL / TRL...`，省略号即「不固定五个」）。全文凡「五维之一」「恒五行」「固定五项」「按五维固定顺序」的表述一律改为「按维度配置中的维度集合，按 `sort_order` 排序」。`ErlDimensionEnum` 枚举与前端 `constants.ts` 的静态 `DIMENSIONS` 映射一并删除，改**接口驱动**（接口 23）。
>
> ~~**种子数据**（**2026-09-08 简化**）：`erl_init.sql` 为已有组织各插五行 `erl_dimension_config`（`FRL / PRL / BERL / RRL / TRL`，`sort_order` 1–5，`weight` 各 `20.00`，`status = 'Active'`）；使系统起来即与 PRD 修订前的「简单平均」等价，不出现「权重未配 → 综合分算不出」的空窗。~~
>
> → **2026-09-17（v4.55）整条作废：脚本不再插任何维度行。** 新库与新建组织在管理员于配置页保存第一组维度之前，`erl_dimension_config` 是**零行** ⇒ **那个空窗现在必然出现**：维度列表为空、综合分按 §9 的**等权降级**路径算并打 WARN。这是既定行为、不是 bug，但产品上**没有任何引导**（已记入 `CIOaas-api/docs/待优化项.md`）。
>
> **删除维度 —— 两个动作，按「是否进入过已发布题库版本」二选一**（**2026-09-09 定档**，§0.21）：
> - ~~UI 上仍**只有 `Delete` 一个动作**（垃圾桶 + 二次确认），落库是把 `status` 置 `Inactive`~~ → **2026-09-09 作废**（需求方当日裁决：从未发布出去过的维度应当能彻底删掉）。现在是：
> - **`deletable = true`（该 code 从未进入任何已发布题库版本的维度快照）** ⇒ 行尾是**垃圾桶 = 删除**，落库 `deleted = true`（行留、页面两处都不显示、**无恢复入口**）；
> - **`deletable = false`** ⇒ **删除被禁止**，行尾是**电源按钮**（`PoweroffOutlined`）= 停用，落库 `status = 'Inactive'` —— **就是上面那套一字未改的软删**，可从 `Deactivated Dimensions` 区块 `Activate`。
> - **两者都要二次确认**；`status` 仍只有两个取值，`deleted` 与它**正交**（§0.21 的三行对照表）。
>
> 停用（或删除）后剩余维度的权重合计会不足 100%，**需在同一次 Save 里补齐**。已 `Inactive` 的维度：① 不进填报页、不进当前的综合分与雷达图；② **已提交的历史记录照常显示**（B3 历史列表 / A4 详情 / C7 版本快照）—— 名称 / 缩写取 `erl_assessment.dimension_name` / `dimension_abbr` 行上快照或 §5.1.5 的发布快照，`Retired` 灰样式由 `status = 'Inactive'` **直接判定**（v4.8 的派生口径作废，§0.14）；③ ⚠️ **但「按当前口径重算」的东西会变** —— 综合分、Stage、雷达图顶点集合一律只取 `Active` 维度，故历史期次的这三项**会因停用而漂移**（已接受，§5.1.4 / §13-Q21）。**两者不矛盾：存下来的提交行还在、能看；实时算出来的聚合值会变。**
>
> ⚠️ ~~**软删对 C7 的影响（§0.17-K1，本次未改）**：v4.11 定的「C7 只显示今天仍在维度配置里的维度」原本靠「维度被物理删掉」来判定；改软删后**没有维度会消失**，该规则要么改判 `status = 'Inactive'`、要么整条取消。~~
> - ~~**2026-09-09 补：`deleted` 列不使这条自愈，K1 原样保留待裁决**（§0.21-X9）。现在确实有维度会从配置页彻底消失了，但**两个判据正交且方向相反**：能被删的**恰恰**是「从未进入过任何已发布版本」的维度，而 C7 展示的**只有**已发布版本的快照 ⇒ **能删的维度永远不会出现在 C7 上，出现在 C7 上的维度永远删不掉**。该规则依旧永不触发。~~
> - ✅ **2026-09-09 当日更晚：§0.17-K1 已关闭，取值 = 整条取消**（v4.17，§0.22-Y3）。**C7 与 `erl_dimension_config` 的当前值再无任何耦合** —— 该页既不按当前配置过滤维度，也不再打 `Retired` 灰标（**连接口 23 的取数都撤了**），只读接口 25 / 26 的历史快照。⇒ **停用 / 删除一个维度对 C7 的展示零影响**，本表格上方 ② 里「C7 版本快照」那一项此后只依赖 §5.1.5 的发布快照。**注意范围**：`Retired` 灰标在**历史期次**（B3 / A4 / A1 / A2 雷达图）上照常按 `status = 'Inactive'` 显示，撤掉的只有 C7 这一处。

### 5.1.4 ~~`erl_company_period_config`~~ —— **2026-09-08 整表删除**

~~期次与配置版本的绑定（v4.4 新增；R2）~~ → **2026-09-08 整表删除**：维度配置去版本化后（§5.1.2 / §5.1.3）已无版本可绑，本表唯一的业务列 `dimension_config_version_id` 失去指向，整表随之取消。原表的唯一约束 `uk_erl_company_period_config` 与索引 `idx_erl_company_period_config` 一并消失。

**取而代之的取数口径**：按期次渲染维度、算综合分与 Stage、画雷达图、Gap 状态点计数、Share 门槛 —— 一律读 `erl_dimension_config` 中该组织 **`status = 'Active'`** 的当前维度集合（§5.1.3），按 `sort_order` 排序。历史期次上出现过、如今已 `Inactive` 的维度，其名称 / 缩写可由 `erl_assessment` 行上的 `dimension_name` / `dimension_abbr` 快照还原（§5.2）。

> ⚠️ **R2「历史期次永不漂移」正式失效**（需求方 2026-09-08 裁决：**接受漂移**）：① 改权重会**回溯改变**已提交历史期次的综合分与 Stage —— `erl_assessment` 上有每维的 `level_score` 快照，但**权重不在快照里**，综合分是实时加权算出来的（§7.1）；② 新增维度会让历史期次凭空多出一个「未填」的维度，`Inactive` 维度会从历史雷达图上消失；③ **§13-Q21 重新打开**，取值「改权重影响历史」。
>
> **若要保住 R2**，最省的落点是在 `erl_assessment` 上补一列权重快照（提交时冻结本维度的 `weight`），综合分按行上的权重加权 —— 但这只救得回权重，救不回「那个期次有哪些维度」，完整方案仍需某种期次级的维度集合冻结。**本次未采纳。**

### 5.1.5 `erl_question_config_dimension_version` —— 题库版本 ↔ 维度快照（**2026-09-08 新增**）

> ⚠️ **2026-09-09：本表也在草稿阶段写入**。某维本轮首次被编辑、触发克隆时就写一行
> （挂在**草稿版本行**上）—— 它是「本轮克隆过哪些维度」的**唯一记录**（§7.9-②’’）。
> Publish 只是把同一条版本行翻成 `PUBLISHED`，这批行随之成为该发布版本的快照。
> ~~草稿版本在本表无行、读侧回退当前维度配置~~ 作废。
>
> ⚠️ **2026-09-09：这条特性直接决定接口 23 的 `deletable` 怎么算**（§6.4 / §0.21-X4）。「该维度是否进入过
> 已发布题库版本」**不能**只查本表有没有行 —— 草稿版本上也有行。判据必须 **join 到 `erl_question_config_version`
> 并过滤 `status = 'PUBLISHED'`**；只查本表会把「只在未发布草稿里改过题」的维度误判成不可删，
> 用户看到一个电源按钮却找不出任何理由（那一版从未发布，删掉它不会让任何已发布版本失去指向）。

**题库版本发布当时的维度集合，逐维冻结一行。** 取代已删的 `erl_question_config_version.dimension_config_version_id`（那是「一个 id 引用整份配置版本」，本表改为**把名称与顺序直接抄进来**，不再依赖维度配置留存历史）。C7 版本历史页据此还原「那一版有哪些维度、叫什么、什么顺序」，后续维度改名 / 停用 / 调序**一律不影响**已发布版本的历史展示。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `erl_question_config_version_id` | varchar(36) | not null | → `erl_question_config_version.id`（§5.1.1）：本行快照所属的题库版本 |
| `dimension_code` | varchar(8) | not null | 快照自 `erl_dimension_config.dimension_code`（§5.1.3） |
| `dimension_name` | varchar(64) | not null | 快照自 `erl_dimension_config.dimension_name` —— **发布当时**的全称，此后不随配置改名 |
| `dimension_abbr` | varchar(8) | not null | 快照自 `erl_dimension_config.dimension_abbr` —— **发布当时**的缩写，此后不随配置改名 |
| `question_version_no` | int | not null | 快照自 `erl_question_config.version_no`（§5.1）：**该维度在本次发布时所用的题目集版本号**（按 `dimension_code` 自增的那条版本线）。本次没改动的维度，此列仍指向它上一版的号 |
| `sort_order` | int | not null | 排序：C7 版本快照页的维度卡顺序按它排（= 发布当时 `erl_dimension_config.sort_order` 的快照） |
| `bound_at` | timestamp | not null | 绑定时间（= 该题库版本的发布时刻） |

> ⚠️ **本表的行会被评估行直接指向**（**2026-09-09**）：`erl_assessment.erl_question_config_dimension_version_id` 存的就是本表某一行的 id（§5.2）。因此「**已发布版本的快照行此后永不改写、永不删除**」这条不再只是历史展示的需要，而是**评估取题的前提** —— 行被删掉，那条评估就退回复合键路径（仍能取到题，但「作答依据」的直连断了）。Publish 时删行的那一支（§7.9-②'''' 边界 ①：草稿期克隆过、发布前又被置 `Inactive`）删的是**草稿版本**的行，评估只会绑到**已发布版本**的行上，两者不重叠。

约束与索引：
- `uk_erl_question_config_dimension_version (erl_question_config_version_id, dimension_code)` —— 同一题库版本内一个维度只有一行。
- 索引 `idx_erl_question_config_dimension_version (erl_question_config_version_id, sort_order)` —— 按版本取有序维度列表的主查询路径（接口 26 出参 `dimensions[]`）。

**写入时机：接口 21 Publish 在同一事务内**，把该组织当时 `erl_dimension_config` 中 **`status = 'Active'` 的行**逐行快照进本表（每维一行，带上该维度当时的 `question_version_no`），`bound_at` = 发布时刻；**此后永不改写**。~~草稿（`DRAFT`）版本**不写本表** —— C7 选中草稿时读侧回退当前维度配置（§5.1.3）~~ → **2026-09-09 作废**（与本节开头的 ⚠️ 及实现一致）：**草稿版本行上也有快照行** —— 某维本轮首次被编辑、触发克隆时就写一行挂在草稿版本行上（`ErlQuestionConfigVersionServiceImpl.ensureDimensionCloned`），它是「本轮克隆过哪些维度」的**唯一记录**（§7.9-②''）。Publish 只是把同一条版本行翻成 `PUBLISHED`，这批行随之成为该发布版本的快照，**无需重写**；Publish 当时只补写「本轮未克隆过的 `Active` 维度」那几行。⚠️ 若按作废前那句实现成「草稿不写本表」，§7.9-②'' 的判据就没有落点，写时复制会退回用两个 `max` 比大小反推 —— 那有两个可达的静默错误分支（§7.9-②'' 已列）。

> **`question_version_no` 与 `erl_question_config_version_id` 不冗余**（2026-09-08 澄清）：前者是**该维度题目集自己的版本号**（`erl_question_config.version_no`，按 `dimension_code` 自增，§5.1），后者是**组织级的发布批次**（§5.1.1）。本表正是两者的对应关系表 —— 一行 = 「第 n 次发布时，维度 X 用的是它自己的第 m 版题目」。取某个发布版本下某维度的题目：先按 `erl_question_config_version_id` 查出本行，再用 `(dimension_code, question_version_no)` 回 `erl_question_config` 取题。
>
> **本表不含 `weight`（**2026-09-08 定档**；**2026-09-09 出路 ② 已落地**）**：~~接口 26 出参 `dimensions[]` 现契约为 `{ code, name, abbr, sortOrder, weight }`（与接口 23 同构、复用同一个 Response，§6.4-H2）~~ → **2026-09-09 订正**：那是 v4.10 ~ v4.15 期间的**旧契约**，实现已按下面的出路 ② 落地 —— 现契约是 **`{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }`**，**不含 `weight`**（§6.4 接口 26）。C7 页面本身**不显示权重**（卡头只有 `{全称} ({缩写})` + `{n} questions`，§8.4-C7），故 `weight` 纯属类型复用带出来的字段。两条出路：① ~~本表补一列 `weight`~~ —— **与 2026-09-08「权重不做任何快照」的裁决相左，已排除**；② **采用：接口 26 的 `dimensions[]` 另造一个不含 `weight` 的窄 Response**（模型不加列，代价是拆一个 DTO）。C7 页面本就不显示权重，该字段无消费方。**本项已定档，不再是待裁决项。** ✅ **2026-09-09：出路 ② 已实现** —— `ErlQuestionConfigDimensionVersionResponse` / `ErlQuestionConfigDimensionVersionDTO` 五字段（`dimensionCode` / `dimensionName` / `dimensionAbbr` / `questionVersionNo` / `sortOrder`），**不复用** `ErlQuestionConfigListResponse`。⇒ 全文凡把这条写成「待裁决 / 当前取实时值会漂移」的地方一律作废（**现状是压根不下发**）。

### 5.2 `erl_assessment` — 一次提交（**v4.4：粒度改为「一次维度级提交」**，PRD §3.3 / §3.9）

> ⚠️ **v4.4 变更（§0.10-R1，关闭 §13-Q19）**：一次提交的单元由 ~~「某公司某期次某端的整卷（含五维）」~~ 改为「某公司某期次某端的**单个维度**」。三处后果全在本表：① 新增维度列（**2026-09-08 改名 `dimension_code`**）并进入**每一条**唯一约束 / 索引；② 原 `erl_assessment_dimension`（§5.3）的三列**上提**到本表；③ 题库版本 `erl_question_config_version_id` 的绑定粒度随之变为**每维一份**。提交前置校验相应由「所有维度全部到达终止态」改为「**本维度到达终止态**」（§7.2 / §6.3）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | 形如 `2026Q3` |
| `portal` | varchar(8) | not null | `FOUNDER` / `GSV` |
| **`dimension_code`** | **varchar(8)** | **not null** | **2026-09-08 改名**（原 `dimension`）：本次提交所属维度的 code（对应 `erl_dimension_config.dimension_code`，§5.1.3）。取值域 = 该组织当前 `status = 'Active'` 的维度集合，**不是固定五值枚举**（D1） |
| **`dimension_name`** | **varchar(64)** | **not null** | **2026-09-08 新增**：提交时该维度全称的**快照**。维度日后改名或 `Inactive` 后，历史详情、雷达图图例、Gap 报告仍显示当时的名字 |
| **`dimension_abbr`** | **varchar(8)** | **not null** | **2026-09-08 新增**：提交时该维度缩写的**快照**，同上 |
| `status` | varchar(16) | not null | `DRAFT` / `SUBMITTED` |
| ~~`submission_seq`~~ | — | — | ❌ **2026-09-08 删除**：同组内的提交序号。历史提交的先后改按 `submitted_at` 倒排（见下方 ⚠️） |
| ~~`is_latest`~~ | — | — | ❌ **2026-09-08 删除**：SOT 标记。「最新一次提交」改按 `submitted_at` 取最大（见下方 ⚠️） |
| ~~`unanswered_count`~~ | — | — | ❌ **2026-09-16 删除**（v4.41）：2026-09-15 为「部分提交」加的漏答数（`V16` 加列 → `V17` 删列，存活一天）。未答完的提交改为**自动补一道 No 先终止**之后，SUBMITTED 行只剩一种形态、漏答数恒为 0，该列无信息量 |
| ~~`scoring_mode`~~ | — | — | ❌ **v4.0 删除**：PRD 已把打分格式定档，只剩一种计分模型，快照列无消费者（§0.9-1 / §7.2） |
| **`erl_question_config_version_id`** | **varchar(36)** | **not null** | **2026-09-08 改名**（原 `question_version_id`） → `erl_question_config_version.id`（§5.1.1）：本次作答所依据的**题库版本快照**。**创建评估时写入当时最新的已发布版本，此后永不改写**（含 `DRAFT` 期间 —— v3.4 取消重基，见 §7.9-⑤）。填报、计分、历史详情、Goldie 输入**全部按此版本**渲染与计算。**v4.4（R1）：绑定粒度由「每卷一份」变为「每维一份」** —— 见下方说明 |
| **`erl_question_config_dimension_version_id`** | **varchar(36)** | **可空** | **2026-09-09 新增** → `erl_question_config_dimension_version.id`（§5.1.5）：本次作答所依据的**那一维的题目集快照行**。上一列绑的是**组织级发布批次**，要取「这一维当时用的是第几版题目」还得拿 `(erl_question_config_version_id, dimension_code)` 去 §5.1.5 按复合键反查；本列把**那一行的 id 直接记在评估上**，一跳 `findById` 即得 `question_version_no`（连同发布当时的维度名 / 缩写 / 排序）。**创建草稿时写入，此后永不改写**（与上一列同口径，v3.4 已否决重基）。<br>**为什么可空**：① 本仓库 `ddl-auto: update` **加不上 NOT NULL 列**（同 `version` 列的处境）；② 该维度在所绑那一版下**可能本来就没有快照行**（例如它在那次 Publish 之后才启用），此时 `null` 是**正确状态、不是异常**。<br>**读侧优先级**：非空 ⇒ 一跳直达，但要过三道校验 —— 行还在、行的 `dimension_code` 与评估行一致、行的 `erl_question_config_version_id` 等于评估绑定的批次；任一不成立即按**脏数据**处理（打 WARN 后回退，**不抛异常**）。正常路径下两列是同一时刻由同一个版本行写入的，永远相等；不相等只能是手工改数或迁移写歪，此时宁可回退也不能拿别的维度 / 别的一版的号去取题。为空 ⇒ **回退原来的复合键查询**（存量行与上面②那种情形）。两条路径结果必须一致。<br>**不取代 `erl_question_config_version_id`**：`organization_id`（评估表上没有）与版本号徽章（`questionVersionNo` / `hasNewerQuestionSet`）仍从批次列解，本列只是取题的捷径。存量行由 `V8` 精确回填（§10.1） |
| **`level_score`** | **smallint** | **提交时非空，0–9** | **v4.4 由 `erl_assessment_dimension` 上提（R1），语义与取值域不变**：本维度得分 = 最后一个全 Yes 的 level。`0` = 一级都没通关（该维第一个有题 level 内就有 No）；`9` = 九级全 Yes（PRD `a6b0906`）。`DRAFT` 期间为 `null`（尚未终止），提交时由服务端算出并落库。⚠️ **v4.37（2026-09-15 换底）**：取值虽仍在 0–9 内，但**只可能是该维配置过的 level 或 `0`**（只配 level 1/2/7/9 ⇒ 该列只会出现 0 / 1 / 2 / 7 / 9）；⚠️ 该列是**提交时冻结的快照**，换底**不追溯存量行** |
| **`terminated_level`** | **smallint** | 0–9 | **v4.4 由 `erl_assessment_dimension` 上提（R1）**：**首次出现 No 的 level**（~~`level_score + 1`~~ → **v4.37 订正**：稀疏题库下两列不再相差 1 —— `level_score` 取的是**上一个有题且整级通关的 level**，两列之间可能隔着若干个该维没配题的 level，如 levels `[1, 2, 7, 9]` 在 L7 踩 No ⇒ `terminated_level = 7`、`level_score = 2`）；九级全 Yes 时为 `null`。冗余存一列是为了历史详情页能直接标出「止于 Level n」而不必重扫答案 |
| **`unlocked_level`** | **smallint** | not null, 1–9 | **v4.4 由 `erl_assessment_dimension` 上提（R1）**：**草稿期的解锁进度**，当前已解锁到第几 level。创建草稿时写 `1`，填报页据此渲染（§7.2）；提交后即等于 `terminated_level ?? 9` |
| `submitted_at` | timestamp | | `SUBMITTED` 才有值 |
| `submitter_name` | varchar(128) | | 提交人姓名快照 |
| `submitter_role` | varchar(128) | | 提交人角色快照，如 `Founder & CEO` |
| `fund` | varchar(128) | | **双端均存**（v3.6）：提交时该公司所属基金 / 组合的名称快照。PRD §3.3「每次提交生成带日期的记录（提交日期、评估人、**基金/组合**）」与 §3.4 均要求 |
| `assessment_team` | varchar(255) | | 仅 GSV 端（PRD §3.4 元数据） |
| `version` | bigint | not null, default 0 | **2026-09-07 新增**：JPA `@Version` 乐观锁版本号。草稿行是**公司共享**的多人写入对象，存草稿事务读到 DRAFT 行后、若另一事务已把同一行提交成 SUBMITTED，落盘时会把 `status` / `submitted_at` / `submitter_*` 整行写回旧值（**2026-09-08**：`is_latest` 列已删，不再列举） —— 一次已完成的提交被静默抹掉。列由 `V4__erl_optimistic_lock.sql` 建，**必须部署前执行**（`ddl-auto: update` 加不上 NOT NULL 列）|

**约束变更（v2.1 的关键修正；v4.4 起每一条都加维度列；**2026-09-08 随两列删除再减两条**）**：
- ❌ 删除 v2.1 的 `uk_erl_assessment (company_id, period, portal)` —— 它与 PRD「同一季度允许多次提交」直接冲突。
- ❌ **2026-09-08 删除** `uk_erl_assessment_seq` —— 随 `submission_seq` 列一并消失。
- ❌ **2026-09-08 删除** `uk_erl_assessment_latest` —— 随 `is_latest` 列一并消失；**部分唯一索引本轮删 2 条**（`uk_erl_assessment_latest` 与随表删除的 `uk_erl_dimension_config_version_latest`）**、新增 1 条**（`uk_erl_dimension_config_abbr`，§5.1.3），现存 ~~4 条~~ → ~~**2026-09-09：3 条**（`uk_erl_question_config_version_draft` + 本表的 `uk_erl_assessment_draft` + 缩写唯一 —— `uk_erl_question_config_version_latest` 随题库版本表的 `is_latest` 一并删除，§5.1.1）~~ → **2026-09-15：2 条**（`uk_erl_question_config_version_draft` + 本表的 `uk_erl_assessment_draft` —— `uk_erl_dimension_config_abbr` 随「缩写唯一」这条不变量整条取消一并删除，§5.1.3 / v4.31）。
- ✅ **部分唯一索引** `uk_erl_assessment_draft ON erl_assessment (company_id, period, portal, dimension_code) WHERE status = 'DRAFT'` —— **每维**同时只允许一份在填草稿（草稿仍是公司共享、不含用户维度，D9）。**本表唯一存活的部分唯一索引。**
- 索引 `idx_erl_assessment_company_period (company_id, period, portal, dimension_code, submitted_at DESC, id DESC)` —— **2026-09-08：列改名，并升级为「取最新提交」的主路径**（原先靠 `is_latest` 命中）。

> ⚠️ **删 `submission_seq` / `is_latest` 的后果（表外口径本次未同步修改）**：① **「最新一次提交」失去标记列** —— 由「命中 `is_latest = true`」改为「同 `(company_id, period, portal, dimension_code)` 内 `status = 'SUBMITTED'` 且 `submitted_at DESC, id DESC` 的第一条」，读侧每一处 SOT 取数（A1 卡片、A2 雷达图、A4、F2、Gap 输入、Share 门槛）都要改写，且**并发下没有索引兜底「至多一条 SOT」**；② `submitted_at` 相同（同秒两次提交）时靠 `id` 作次级排序键兜底，**读侧必须全部走同一个 Repository 方法**，否则不同页面会选出不同的一条；③ **提交序号 `Submission #n` 无处可取** —— A2 / A4 历史列表的序号改为按 `submitted_at` 倒排后的行号实时计算（翻页时会漂移）；④ §7.2 / §7.5-S1 / §9 / §11 / §12 相关口径待改。

提交人姓名 / 角色 / Fund **存快照**：人员离职或改名后历史记录仍显示当时信息。即使草稿由他人保存，`submitter_name` / `submitter_role` 只记录**点提交的那个人**（D9）。

> **`erl_question_config_version_id` 每维一份的后果（v4.4 定档，R1）**：维度 A 在 3 月创建草稿（绑 v5），维度 B 在 5 月才创建（此时最新已发布是 v7，绑 v7）—— **同一公司同一期次的各维度可能绑不同的题库版本**。**系统不阻止、不告警**，各维度按各自绑定的版本渲染题目、判定解锁与计分；历史详情同理按行上的版本还原。理由：题库版本本就是「按维度独立的作答依据」，强行对齐要么阻塞后开的维度（不能用新题）、要么重基已开的维度（v3.4 已否决重基，§7.9-⑤）。
>
> ~~**对比维度配置版本**：题库版本每维一份、可以不同；维度配置版本每期次一份、必然相同（§5.1.4）~~ → **2026-09-08 作废**：维度配置已去版本化、期次绑定表已删（§5.1.2 / §5.1.4），不再有「维度配置版本」这一侧可对比。维度的名称与缩写改由本表的 `dimension_name` / `dimension_abbr` 逐行快照，**权重则没有快照**（见 §5.1.4 ⚠️）。

### 5.3 ~~`erl_assessment_dimension`~~ — **v4.4 整表删除**

~~每维汇总（v3.0 新增，v4.0 换语义，PRD §3.1 / §3.3）~~ → **v4.4 整表删除**（§0.10-R1）。

**理由**：提交粒度改为维度级后，一条 `erl_assessment` 只属于一个维度，本表与之**恒一一对应**（恒一行），是纯粹多余的一层表与一次 join。三列 `level_score` / `terminated_level` / `unlocked_level` **原样上提到 `erl_assessment`**（§5.2），**语义与取值域完全不变**。

> ~~唯一约束 `uk_erl_assessment_dimension (assessment_id, dimension)`；**一条评估恒五行**（首次存草稿时即建齐五行，`unlocked_level = 1`），否则填报页要区分「没这行」与「刚开始答」两种空态~~ → **v4.4 作废**（§0.10-R1 / -D1）：一条评估恒**一维**，`unlocked_level = 1` 在创建草稿时直接写在评估行上；「没这行 / 刚开始答」的空态歧义随之消失 —— 评估行本身就是那一行，它不存在就是「这一维还没开始」。
>
> **v4.0 的两条结论保留，只是换了落点**：
> ① `manual_score` / `derived_score` / `divergence_ack` / `divergence_delta` 四列在 v4.0 已删（PRD `621e857` 在 §3.3 / §3.4 同时删除「每维手动整体分 + 软确认弹窗」，改为 level 推导，§0.9-1 / -3），v4.4 **不复活** —— 上提到 `erl_assessment` 的只有三列。
> ② **为什么把 `level_score` 落库而不是全靠实时算**：它由答案唯一决定、实时可算（§3.2 的「计分不落库」指的是**综合分 / Stage / Era**）；但 `unlocked_level` 是**草稿期的交互状态**，必须持久化（否则刷新页面后解锁进度丢失、PRD §3.3「支持保存进度、稍后继续，无数据丢失」不成立）。既然这行本就要存，`level_score` 与 `terminated_level` 一并落库，省掉展示与组合层的重复扫表 —— 且**提交后答案冻结，二者不会与答案不一致**。该论证**原样适用于上提后的 `erl_assessment`**（§5.2）。
>
> **迁移**：本表尚无生产数据（ERL 未上线），`erl_init.sql` 直接不建即可；若已有环境建过，`drop table erl_assessment_dimension` 并在 `erl_assessment` 上补三列。

### 5.4 `erl_assessment_answer` — 逐题作答（PRD §3.3 / §3.4）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`erl_assessment_id`** | **varchar(36)** | **not null** | **2026-09-08 改名**（原 `assessment_id`） → `erl_assessment.id`（§5.2） |
| **`erl_question_config_id`** | **varchar(36)** | **not null** | **2026-09-08 改名**（原 `question_id`） → `erl_question_config.id`（§5.1），**指向作答时所属维度版本的那一行**（历史详情据此还原当时的题干 / level / 来源标签） |
| ~~`score`~~ | — | — | ❌ **v4.0 删除**：1–9 打分格式已废（§0.9-1） |
| **`yes_no`** | **boolean** | **not null**（v4.0 由 nullable 收紧） | **唯一的作答字段**。已解锁且已作答的题恒有值；**未解锁的题不落行**（不是落 `null` 行 —— 见下方说明） |
| **`note`** | **varchar(2048)** | **nullable** | **证据 / 备注（Evidence/Notes），v3.0 新增**；Goldie 的主要输入源（PRD §3.6）。**v4.44（2026-09-16）**：列宽与接口 4 的 `@Size(max = 2048)` **均不变**，但**填报页的输入上限是 2000**（前端 `maxLength` + `n / 2000` 字数提示），那 48 是留白、**不是**第二个业务上限 |

唯一约束 `uk_erl_answer (erl_assessment_id, erl_question_config_id)`；索引 `idx_erl_answer_assessment (erl_assessment_id)`。（**2026-09-08：两处键位随列改名同步**）

> **v3.4 删除了 v3.3 加的 `question_key` 列**：它的唯一用途是重基时按稳定键迁移答案；版本锁定后 `erl_question_config_id` 自始至终不改写，该列没有消费者（YAGNI）。跨版本稳定键 `question_key` 仍保留在 `erl_question_config` 表 —— 版本 diff 与 C 模块写接口定位需要它。
>
> **v4.0 删除的 CHECK 约束**：原 `(score IS NULL) <> (yes_no IS NULL)` 随 `score` 列一并删除；`yes_no` 改为 not null。
>
> **未解锁的题不落答案行**（v4.0 定档）：逐级解锁下，用户根本看不到未解锁 level 的题，落 `null` 行会让「未解锁」与「看到了但没答」无法区分，而后者要拦住提交、前者不能拦。因此 `answeredCount` 就是本表行数，判定简单且无歧义（§6.3 / §7.2）。
>
> `note` 是**可选**字段（PRD §3.3「可选『证据/备注（Evidence/Notes）』文本」）。无备注时 Goldie 侧标注为「未提供备注」（PRD §3.6）。

### 5.5 `erl_answer_attachment` — 逐题附件（**v3.0 新增，v4.0 改名扩粒度，v4.6 改回**，PRD §3.3 / §4）

**只有题级一种粒度**（v4.6，需求方 2026-09-06 裁决）：Founder 与 GSV **一律把附件挂在具体某一道题的作答上**（PRD §3.3「每题…可上传附件（单个最大 10MB）」），~~GSV 端的维度级附件（PRD §3.4）~~ 取消。粒度归一后 v4.0 那次改名的理由（「它已不只挂在答案上」）不复存在，表名**改回 `erl_answer_attachment`**。

⚠️ **本节与 PRD §3.4「每个维度均可提交附件」、§4「所有**维度**附件同步写入公司 Memory File」直接冲突** —— 两处均为 PRD `621e857`（2026-09-02）写入，需求方 2026-09-06 已裁决取消，**须回写 PRD**（§0.10-④ **M13**）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| ~~`assessment_id`~~ | — | — | ❌ **v4.6 删除**（§0.12-A2）：~~v4.0 新增，维度级附件没有作答可挂，必须另给一个 owner~~ → 维度级取消后它与 `erl_assessment_answer.erl_assessment_id`（**2026-09-08 改名**）完全重复，经 `answer → assessment` 一跳即得。删附件鉴权（接口 19）因此由一跳变两跳，是这次回退**唯一**的代价 |
| ~~`dimension`~~ | — | — | ❌ **v4.4 删除**（§0.10-R1）：v4.0 新增的冗余维度列；维度已在 `erl_assessment.dimension_code` 上（§5.2） |
| **`erl_assessment_answer_id`** | **varchar(36)** | **not null** | **2026-09-08 改名**（原 `answer_id`） → `erl_assessment_answer.id`（§5.4）。**附件恒挂在一条作答上**，双端同口径；所属评估、维度、期次、端一律经该作答带出。~~v4.0 放开为可空以承载维度级附件、并以「空 / 非空」区分粒度~~ → v4.6 作废 |
| `file_id` | varchar(36) | not null | 直传通道返回的 `files.id` |
| ~~`file_name`~~ | — | — | ❌ **2026-09-09 删除**（推翻 v4.15-⑧「`file_name` / `file_size` 暂不删除」）：~~原始文件名快照~~ → 按 `file_id` 取 `files.original_name` |
| ~~`file_size`~~ | — | — | ❌ **2026-09-09 删除**（同上）：~~v4.0 新增的字节数快照~~ → 按 `file_id` 取 `files.length`；**10MB 上限也改按 `files.length` 复核** |
| `registry_id` | varchar(36) | | 知识库登记行 id（Python 回传）；未入库成功时为 `null` |
| `ingest_status` | varchar(16) | not null | `PENDING` / `SUCCESS` / `FAILED` —— ~~入 Memory File 的结果~~ → **2026-09-18 语义改写为「该附件的摘要生成结果」**（v4.57，§0.31-Z5，裁决 R8）。**列名、Entity 字段名、`ErlIngestStatusEnum`、前端出参字段 `ingestStatus` 一律不动**，三个取值与「失败不阻断评估提交、附件旁给重试入口」的规则一字不改，变的只有语义；升级脚本 `sprint118/V20` **只改 COMMENT、不改 schema**。⚠️ 列名从此名不副实（叫 `ingest`、实际是 summary），已记入 `CIOaas-api/docs/待优化项.md`，下一次 ERL 表结构变更窗口一并改名为 `summary_status` |

> **~~`file_name` / `file_size`~~ —— 2026-09-09 两列删除**：文件名与字节数**不再在附件行上快照**，一律按 `file_id` 去 `files` 取（`original_name` / `length`）—— 那本就是这两个值的**真值来源**，附件行只是「这道题挂了哪个文件」的指针。
> - **入参收敛**：接口 4 / 5 的 `answers[].attachments[]` **只收 `fileId`**（`fileName` / `fileSize` 入参删除）。存量前端仍会多发这两个字段，服务端忽略（`fail-on-unknown-properties: false`），**前端零改动**。
> - **10MB 上限改按 `files.length` 复核**（§6.7 第 ③ 步）：比原来的「信客户端自报的 `fileSize`」更硬 —— 但**这有个前提**（**2026-09-09 审核补**）：`files.length` 在 `presign` 阶段落的**也是客户端自报的数**，只有 `verify` 才用 S3 `HeadObject` 的真实大小覆盖它并写上 `etag`。所以服务端**先断言 `files.etag` 非空**（= 已 verify）再看 `length`；少了这一条，「presign 声明 1MB → PUT 一个 100MB 对象 → 跳过 verify → 挂上来」就能绕过上限（`KNOWLEDGE_BASE` 的 presign 上限是 1024MB，绕过空间很大）。前端 `storageService.uploadFile` 走的是 `putAndVerify`，正常链路必然已 verify。<br>⚠️ **仍未校验的一项**：`fileId` 的**归属**（谁上传的、是不是 `KNOWLEDGE_BASE` 业务类型、属不属于本公司）—— 任意 `files.id` 都能挂到本公司作答上，属存量口径，已记入 `CIOaas-api/docs/待优化项.md`。两种取不到大小的情况**一律报业务错误**（~~400~~，2026-09-09 订正，§4.3）：① `file_id` 在 `files` 里查不到；② 查到了但 `length <= 0`（直传只 presign 占了行、还没 verify，或 legacy 行从未回填大小）—— **不得**把 `0` 当成「0 字节，肯定不超限」放过去，S3 上那个对象可以任意大。
> - **出参不变**：`fileName` / `fileSize` 照旧下发（B2 / A3 / A4 的附件行要显示名字与大小），只是改由 `files` **批量**回填（一次 `findAllById`，绝不逐个查 —— `coding.md §10`）。
> - ⚠️ **代价（已接受）**：快照消失后，历史附件的名字与大小**依赖 `files` 行仍在**。`files` 行若被清理，回显变 `null`（`file_id` / `registry_id` / `ingest_status` 仍在，附件行本身不丢、知识库条目也不受影响）。当前没有任何清理 `files` 的定时任务，故这是理论风险而非现存缺陷。

索引 `idx_erl_attachment_answer (erl_assessment_answer_id)`（**v4.6**：`idx_erl_attachment_assessment` 随 `assessment_id` 列一并删除）、以及建库脚本里那条按 `file_id` 的索引（Python 回写 `ingest_status` 用，§6.7 第 ⑥ 步）。**按维度 / 按一次提交查附件 = 先取该评估的作答行，再按 `erl_assessment_answer_id` 批量取**（`findByAnswerIdIn`，本就是填报页、维度页、A4 的既有主路径）。

> 附件**先落本表**（保证问卷侧不丢文件），再异步入知识库；`ingest_status` 失败可重试，不阻断评估提交（§6.7）。
>
> **双端完全同口径**（v4.6 定档）：同一个接口、同一张表、同一个 10MB 上限、同一套前端组件；**服务端不做端限制，前端两端都渲染逐题上传入口**。v4.0 那句「若后续产品要求 Founder 也能挂维度级附件，是纯前端改动」随维度级附件一并作废 —— 现在**没有**维度级这一挡。

### 5.6 `erl_reference_score` — 外部基准主表（**2026-09-08 由 `erl_benchmark_record` 改名**；PRD §4，**v3.1 改粒度**）

~~一期次一条记录~~ → **2026-09-10 作废**（§0.27-Z1）：**同一 `(company, period)` 允许多条记录**（peer set 换了、口径改了要重新录一份，属正常路径）；分数落在 §5.6.1 的维度明细表 `erl_reference_score_item`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | 形如 `2026Q3`；D2 页输入 `Q3 2026`，前端归一后提交 |
| `note` | **varchar(2048)** | | 基准数据来源 / peer set 变化说明；空显示 `—`。**v4.45（2026-09-16）由 ~~`varchar(512)`~~ 放宽** —— D2 录入框限 **2000 字符**（前端 `maxLength` + `n / 2000` 字数提示），库留 48 余量，**那 48 不是第二个业务上限**；接口 16 的 `@Size(max = 2048)` 跟列宽走。存量环境跑 `V19__erl_reference_score_note_2048.sql`（**脚本先于代码发版**） |

~~唯一约束 `uk_erl_reference_score (company_id, period)`（**2026-09-08 随表改名**）~~ → **2026-09-10 删除**（§0.27-Z1）：改为**同键位的普通索引** `idx_erl_reference_score_company_period (company_id, period)`（存量环境跑 `V13__erl_reference_score_drop_period_unique.sql`，`V1__erl_init.sql` 已就地改为直接建普通索引，§10.1）。⚠️ **代价：没有数据库级「同期次至多一条」保证了** —— 读侧每一处取「最新一条 / 适用记录」都必须用同一排序键 **`period DESC, created_at DESC, id DESC`**（`id` 是同一微秒的平局兜底；与 §5.2 评估 SOT 的 `submitted_at DESC, id DESC` 同源），且一律走 `ErlReferenceScoreRepository` 的那两个方法 —— 各处自己拼查询会在同期次多条时选出不同的一条（§7.8）。~~`Recorded` 日期由 `period` 推导（期末日，§7.8）~~ → **2026-09-10 改判**（§0.28-Z1）：**`recordedAt` 直接下发审计列 `created_at`（真实录入时刻，`Instant` / ISO-8601）** —— 期末日那份推导与「谁在什么时候录入」无关，而屏上列头写的是 `SUBMISSION TIME`；排序键本就在用这一列，展示位跟着它才不会与行序打架。**仍然不新增存储列**：`created_at` 是审计基类 `AbstractCustomEntity` 自带的列，**表结构与迁移脚本零变更**。`Recorded by` 用 `created_by`（姓名 + 角色由用户表 join 得到，**不冗余存快照** —— 基准录入人不涉及 §5.2 那种历史留档要求）。

### 5.6.1 `erl_reference_score_item` —— 每维基准分（**2026-09-08 由 `erl_benchmark_dimension` 改名**；**v3.1 新增**，原型 D2「Scores by dimension」）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| **`erl_reference_score_id`** | **varchar(36)** | **not null** | **2026-09-08 改名**（原 `record_id`） → `erl_reference_score.id`（§5.6） |
| **`dimension_code`** | **varchar(8)** | **not null** | **2026-09-08 改名**（原 `dimension`）：维度 code，取值来自 `erl_dimension_config.dimension_code`（§5.1.3），~~固定五值枚举~~ 已作废（D1） |
| **`dimension_name`** | **varchar(64)** | **not null** | **2026-09-08 新增**：录入时该维度全称的**快照**，同 `erl_assessment`（§5.2）—— 维度日后改名或 `Inactive` 后，历史基准记录仍显示当时的名字。⚠️ 原先这两列**不落库、由 service 按配置回填**，现在是表列，**映射方向反转** |
| **`dimension_abbr`** | **varchar(8)** | **not null** | **2026-09-08 新增**：录入时该维度缩写的**快照**，雷达图基准环的图例用它 |
| `benchmarkit_score` | numeric(3,1) | not null | 1–9 |
| `top_quartile_score` | numeric(3,1) | not null | 1–9 |

唯一约束 `uk_erl_reference_score_item (erl_reference_score_id, dimension_code)`；索引 `idx_erl_reference_score_item (erl_reference_score_id)`（**2026-09-08 随表与列改名**）。~~**一条记录必须齐五维**（D2 页十个输入框全必填）~~ → **v4.4 参数化**（§0.10-D1）：**一条记录必须齐当前 `status = 'Active'` 的全部维度**（**2026-09-08**：原「该期次绑定配置版本中的全部维度」随 §5.1.4 删表作废），D2 页按该维度集合渲染「每维两个输入框」并**全部必填**（§8.4），否则提交被拒 —— 缺维会让雷达图与维度页的基准位置出现空轴。

> **为什么拆两张表而不是在单表加 `dimension_code` 列**：`note` 与录入人属于「一次录入」的属性，摊到每个维度一行会重复且可能不一致（改一次备注要改 N 行）。**v4.4 订正**：原文说「该主从结构与 `erl_assessment` / `erl_assessment_dimension`（§5.2 / §5.3）一致」—— ~~该类比~~ 已随 §5.3 整表删除而失效（`erl_assessment` 现在自己就是维度级的，不再有从表）。现存的同构主从结构是 `ai_erl_gap_analysis` / `ai_erl_gap_analysis_item`（§5.7 / §5.8；**2026-09-19 起在 Python 库**）。
>
> PRD §4：这两条序列是**外部静态数据输入，不由 Looking Glass 计算**。D 模块即该数据的接入口（管理端手工录入）；未来接自动同步时，只需替换写入方，读取口径不变。

### 5.7 `ai_erl_gap_analysis` — Goldie 差距分析（PRD §3.6；**2026-09-19 起归 Python**，v4.59 / §0.33-X1）

> ⚠️ **本表不在 Java 库、不由 Java 的 `ddl-auto` 建**（2026-09-19，P3）：表名由 ~~`erl_gap_analysis`~~ 改为 **`ai_erl_gap_analysis`**（`ai_` 前缀 = Python 服务的表，裁决 R3），DDL 走 `CIOaas-python` 的版本化迁移 `sql/migrations/business/V024__erl_gap_analysis.sql`。**Java 侧的实体与仓储已删除**，取产物一律经 `ErlGapAnalysisService#loadResult`（→ `GET /api/ai/erl/gap-analysis`）。**旧表 `erl_gap_analysis` 刻意保留不动**（回滚路径），由 Java 侧下一个 sprint 单独出 DROP 脚本。
>
> 两处实现与下表的有意偏离：① 时间列实际是 **`TIMESTAMPTZ`**（PG 化选择，避免存量时区位移）；② `source_founder_assessment_id` / `source_gsv_assessment_id` 两列建了但 **Python 从不写入**（refresh 入参带的是作答内容、不是评估 id），属有意保留的 legacy 列、永久为 NULL。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | |
| ~~`audience`~~ | — | — | ❌ **v4.4 删除**（§0.10-D3）：~~`FOUNDER` / `GSV` 两套口吻各存一份（v3.0 新增，PRD §3.6）~~ → PRD `8324a3f` 已删掉「Founder / GSV 两套口吻」整段，改为「GSV 团队可见 + 点 Share 分享给 Founder 端」。**一个 `(company, period)` 只有一份分析**，两份 prompt 合并为一份（§7.5） |
| `summary` | varchar(2048) | | 整体判断段落 |
| `source_founder_assessment_id` | varchar(36) | | 生成时所依据的 Founder 提交 |
| `source_gsv_assessment_id` | varchar(36) | | 生成时所依据的 GSV 提交 |
| ~~`stale`~~ | — | — | ❌ **2026-09-19 删除**（v4.59，裁决 R2 / §0.33-X2）：~~有更新提交后置 `true`，触发异步重生成~~ —— 「内容是否落后」改为**读接口现算派生**，不再落列。产物搬到 Python 后置脏就要跨服务写一张不属于自己的表，而派生只需比一个字符串 |
| **`submission_signature`** | **varchar(64)** | | **2026-09-19 新增**（v4.59，取代 `stale`）：本份产物**依据哪一批提交**生成 —— 当前 Active 维度 × 双端 SOT `erl_assessment.id` 排序拼接后取 SHA-256（小写 hex）。读接口拿现算值与本列比对，不等即 `stale`。⚠️ **由 Java 算、由 Java 比；Python 只存不算不比**（列注释已钉死），这样「内容是否落后」只有一个判定者。⚠️ 末尾那层 SHA-256 不能省：5 维双端的原始拼接串是 369 字符，直接存会被本列截断，截断后两批不同提交还可能撞成同一个值 |<br>→ **2026-09-20 废弃停写**（v4.61，§0.35-G2 / G3）：指纹**下沉到维度级**、改存 `ai_erl_gap_analysis_dimension.submission_signature`；本列自 V026 起**恒 NULL**，下个 sprint DROP。V024 已应用、按「已应用的迁移文件永不再改」不得回改，故只在 V026 里改 COMMENT 标注废弃。
| **`shared`** | **boolean** | **not null, 默认 false** | **v4.4 新增**（§0.10-D3）：是否已由 GSV 分享给 Founder 端。**`false` 时接口 17 对公司端直接返回空态**（§4.2 / §4.3）；置 `true` 的唯一入口是接口 27 `POST /erl/gapAnalysis/share`（仅管理端） |
| **`shared_at`** | **timestamp** | | **v4.4 新增**：分享时间，`shared = true` 才有值 |
| **`shared_by`** | **varchar(36)** | | **v4.4 新增**：分享人 |
| `model` | varchar(64) | | 生成所用模型，便于回溯 |
| `generated_at` | timestamp | not null | 前端展示「最后生成时间」 |

唯一约束 `uk_ai_erl_gap_analysis (company_id, period)`（**2026-09-19 随表改名**，原 `uk_erl_gap_analysis`） —— **v4.4** 由 ~~`(company_id, period, audience)`~~ 去掉 `audience`（D3）。重新生成 = 覆盖本行 + 全量替换其 item 行。

> **覆盖的语句顺序被钉死**（Python 侧实现，§0.33-X7）：**UPDATE 主行 → DELETE items → 批量 INSERT items**，`UPDATE` 必须排在 `DELETE` 之前 —— 先拿到主行的行锁把并发串行化，否则两代条目会混在同一个 `analysis_id` 下。首次生成走 INSERT，撞唯一键时回滚后转覆盖路径重试一次。

**Share 激活门槛**（PRD §3.6「只有所有维度两方都完成时」）：该 `(company, period)` 下**每一个维度**（**2026-09-08**：§5.1.4 已删表，改按 `erl_dimension_config` 当前 `status = 'Active'` 的维度集合，§5.1.3）取的 `FOUNDER` 与 `GSV` 两端**都有** `SUBMITTED` 记录时（**2026-09-08**：`is_latest` 列已删，改按同 `(company_id, period, portal, dimension_code)` 内 `submitted_at DESC, id DESC` 取首条判存在），`Share to founder` 按钮才激活；否则置灰（§8.4 / D4）。

> ⚠️ **重生成时 `shared` 复位为 `false`**（**v4.4 定档**，§0.10-D3）：PRD 与原设计都没定义「Share 之后又有新提交」的边界，而重生成会**静默改写 Founder 已经看到的内容**。本版定档 —— 重生成落库时把 `shared` 置回 `false`、清空 `shared_at` / `shared_by`；重生成完成后管理端提示「内容已更新，需重新分享」，需 GSV **重新 Share**，Founder 端在此期间回到空态。
>
> ⚠️ **2026-09-19（P3）：复位的执行点从 Java 移到 Python** —— ~~置脏的同一事务内复位~~ 已不可能（产物在另一个服务的库里）；现在它**随「覆盖产物」一起做**（Python 的 `overwrite_generated` 在那条 `UPDATE` 里一并置回 false / null）。语义一字未变：**重生成即取消分享**。这也是为什么读接口的自愈投递（§7.5 触发点 B）**只在管理端做** —— refresh 会复位 `shared`，公司端若也投，创始人打开一次页面就能把自己正在看的那份分析变回「未分享」，读接口绝不能有写副作用。
>
> 取舍：让 Founder 短暂看不到，好过让他看到一份「和上次不一样、却没人告诉他变了」的分析 —— 后者会直接损伤这份 AI 产物的可信度，而 Share 本身是一次成本极低的点击。


### 5.8 `ai_erl_gap_analysis_item` — 每维差距与建议（**2026-09-19 起归 Python**，v4.59 / §0.33-X1；PRD §3.6；**v4.0：§3.5 依据已删，§0.9-11**；**v4.4：删 `STRENGTH`**；**2026-09-18：加 `NARRATIVE`、`dimension` 列改名 `dimension_code`、`evidence_missing` 口径放宽**，v4.57）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `analysis_id` | varchar(36) | not null | → `ai_erl_gap_analysis.id`（**2026-09-19 随主表改名**） |
| **`dimension_code`** | varchar(8) | not null | **v4.4 改（D1）**：维度 code，取值来自 `erl_dimension_config.dimension_code`（§5.1.3；**2026-09-08**：原「该期次绑定配置版本的维度集合」随 §5.1.4 删表作废），~~五维之一~~ 已作废。<br>**2026-09-18 改名（v4.57，§0.31-Z9）**：列名由短名 ~~`dimension`~~ 改为 **`dimension_code`**，与另外四张按 code 关联的表对齐 —— Java 字段本来就叫 `dimensionCode`、出入参也一直叫 `dimensionCode`，**只有列名落在后面**（2026-09-08 定命名规则时把它列为例外，那条例外就此消除）。升级脚本 `sprint118/V22`：`RENAME COLUMN` 只改元数据不重写表，索引自动跟随；另带一条「ddl-auto 抢先建了新列」的自愈分支（回填 → `DROP COLUMN dimension` → 重建索引）。**全新环境的 `V1__erl_init.sql` 已直接建成新列名** |
| `item_type` | varchar(16) | not null | **v4.4 收敛为 `GAP` / `ACTION` 两值**（§0.10-D4）：~~`STRENGTH`~~ 枚举值**删除** —— 2026-09-06 ERL Card 原型定档「有 gap 的展示建议，没有的不展示」，优势项在 UI 上无落点。<br>→ **2026-09-18 扩为三值 `GAP` / `ACTION` / `NARRATIVE`**（v4.57，§0.31-Z7）：`STRENGTH` **仍然是删的**，新增的是**维度级叙述段** `NARRATIVE`（需求方给的 Financial Readiness 示例第一段就是它，而 `summary` 是整期一份、维度级此前无字段可落）。<br>**`NARRATIVE` 的约定**：每维**至多一行**、正文存 `title`、`note` / `severity` **留空**、`evidence_missing = false`、`sort_order = 0`；**只有有差距的维度才产出**；**不参与 `hasGap` 判定**（`hasGap` 只数 `GAP` 行 —— 一条 `NARRATIVE` 绝不能把「无差距」的维度渲染成有差距）。<br>⚠️ **本列必须没有 CHECK 约束**：旧表（Java，Hibernate `ddl-auto`）会按枚举吐一条 `check (item_type in ('GAP','ACTION'))`，不删则第一条 `NARRATIVE` 撞 `23514` —— 升级脚本 `sprint118/V21` 第 (0) 段专门 `DROP CONSTRAINT IF EXISTS` 掉它。**2026-09-19 起的新表（Python）索性不建任何 CHECK**：取值归一在 Python 出站前完成，加 CHECK 只会把归一漏洞从「一条脏数据」变成「整份写失败 23514」 |
| `title` | varchar(512) | not null | GAP 用标题；ACTION 用建议动作（~~STRENGTH 用整句~~ 随枚举值一并删除）；**NARRATIVE 用该维叙述段的整段文字**（2026-09-18）。**三类共用同一份 `varchar(512)` 预算** —— 只有 narrative 有可能逼近它（prompt 限 3 句 / ≤60 词），日后不够就**加宽本列、不要另拆枚举或另建表** |
| `note` | varchar(1024) | | GAP：补充说明；**ACTION：`为何相关`（PRD §3.6 要求说明"为何相关"）**；NARRATIVE：**留空** |
| `severity` | varchar(8) | | 仅 GAP：`HIGH` / `MEDIUM` / `LOW`（ACTION / NARRATIVE 留空） |
| `evidence_missing` | boolean | not null, 默认 false | ~~该条由**无备注**的题推导而来~~ → **2026-09-18 口径放宽**（v4.57，§0.31-Z8）：该条由**既无备注、又无可用附件摘要**的题推导而来 → 前端标注 **`No supporting evidence provided`**（旧文案 ~~`No notes provided`~~；前端串名 `noNotesProvided` 沿用原名，只换值）。**不放宽的话，把证据放在附件里的题会被错标成「未提供备注」**。判定本身**在 prompt 里做**（§6.6），服务端只做透传归一 |
| `sort_order` | int | not null | 组内顺序（NARRATIVE 恒 `0`） |

索引 `idx_ai_erl_gap_item (analysis_id, dimension_code, item_type, sort_order)`（**2026-09-18 随列改名**，§0.31-Z9；**2026-09-19 随表改名**，原 `idx_erl_gap_item`）。

> ~~**三类**合成一张表~~ → ~~**v4.4：两类**（`GAP` / `ACTION`）~~ → **2026-09-18 起又是三类**（`GAP` / `ACTION` / `NARRATIVE`，v4.57，§0.31-Z7）合成一张表，用 `item_type` 区分，避免多张近乎相同的表。**`NARRATIVE` 复用现表零成本，好过新建一张「每维一行」的表** —— 它与 v4.4 删掉的 `STRENGTH` 不是同一情形：`STRENGTH` 删的理由是「UI 上无落点」，而 `NARRATIVE` 有明确落点（`View details` 弹框每维分区顶部，§8.4）。`ACTION` 是 v3.0 新增 —— PRD §3.6 的「Suggested Actions」是独立于 gaps 的产物（「可以做什么」+「为何相关」），v2.1 把它误并进 gaps。
>
> **`STRENGTH` 删除的连带改动**（§0.10-D4）：接口 17 出参的 `strengths[]` 删除；§7.5 prompt 中「双方分数均高时承认为优势」一段删除；§11 对应验收项删除。**「无 gap」这条信息不靠 `STRENGTH` 行表达**，而是靠接口 17 新增的 `dimensions[].hasGap = false` —— 该维在 Gap 区块显示绿点 + `No Gap`（§8.4 / D4）。
>
> **`note` 的 `why` 字段保留**（§0.10-D20）：PRD 已删「指导性非强制 / 说明为何相关」整段，但 `ACTION` 的「为何相关」是本设计的选择，**保留**；「不做跟踪 / 指派 / Deadline」的结论也保留，理由由「PRD §3.6 明确 MVP 不含」改为「**PRD 未要求**」。

---

### 5.9 `ai_erl_gap_analysis_dimension` — 每维分析元信息（**2026-09-20 新增，第 13 张表**，v4.61 / §0.35-G3）

> **为什么必须有这张表**：v4.61 把分析单元从「期次」降到「维度」之后，有三件事在原来的两张表里**无处安放** ——
> ① 「这一维已经分析过了」这个事实（无 gap 的维度一行 item 都不写，`ai_erl_gap_analysis_item` 里查不到任何痕迹）；
> ② 维度级的提交批次指纹（增量判定的唯一依据）；
> ③ 「分析过、结论是无差距」这个**结论本身**。
> 缺 ①③ 就回到了本版要修的那个假阴性：**「没分析过」与「分析过但无差距」在库里同形**，前端只能都渲染成绿点 `No Gap`。

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `id` | varchar(36) | PK | UUID |
| `analysis_id` | varchar(36) | not null | 所属 `ai_erl_gap_analysis.id`（**软引用，不建 DB FK** —— 与其余 `ai_` 表同一约定） |
| `dimension_code` | varchar(8) | not null | `erl_dimension_config.dimension_code`。⚠️ 与 §5.8 同理，**这个 code 从不进 prompt**：模型只见 `index`，映射在 Python 内完成（§6.6 末尾那条防线） |
| `submission_signature` | varchar(64) | not null | 该维**依据哪一批提交**生成：`sha256Hex(dimensionCode + "\|" + founderAssessmentId + "\|" + gsvAssessmentId)`，小写 hex。⚠️ **只有 Java 算、只有 Java 比；Python 只存不算不比** —— 与原先期次级那一列同一分工（§0.33-X2） |
| `has_gap` | boolean | not null, 默认 false | 该维是否有差距。**显式落库，不从 item 行数反推** —— 这是「分析过但无差距」能与「没分析过」区分开的那一位（§0.35-G3） |
| `generated_at` | timestamptz | not null | 该维上次分析时刻；出参的 `analyzedAt` 取它 |
| `model` | varchar(64) | | 该维生成所用模型，留痕用 |
| `created_at` / `created_by` / `updated_at` / `updated_by` | | | 审计四列，与 §5.7 同款（异步重生成路径无请求用户，`*_by` 为 null） |

- **唯一约束 `(analysis_id, dimension_code)`**：一份产物下一个维度恒一行。重生成是**覆盖这一行 + 替换该维的 item**，不追加版本 —— 与 §5.7「一个 `(company, period)` 恒一份产物」同款语义，只是下沉了一层。
- **写入时机**：只有 Python 写，且只在 `refresh` 的落库事务里写。**顺序有要求**：`UPDATE 主行 →（逐维）upsert 本行 → DELETE 该维 item → 插该维 item`，主行的 UPDATE 必须排在最前，靠它的行锁把并发串行化（§0.33-X7 的顺序要求在维度级下继续成立）。
- **「行不存在」是一个有意义的状态**：出参的 `analyzed = false` 就是它。老产物（V026 之前）一行都没有，于是每维都读成未分析 —— 这正是 §0.35-G10「存量不回填、靠触发点 B 自愈」能成立的原因。
- **部署项**：给 Python 的 DB role 授本表的写权限（与 V024 的 T3.6 同一类）。漏授的表现是**落库那一步 500、而 LLM 已经烧掉**，且路由的两个 `except` 都接不住（既非 `ValueError` 也非 `RuntimeError`）。

## 6. 接口契约

> 📌 **维度字段的命名规则（**2026-09-08 定规，§6 全域适用**）** —— 本轮改名后文中一度出现 `dimension` / `dimensionCode` / `code` 三套写法，统一为：
>
> | 位置 | 写法 |
> |------|------|
> | **数据库列** | `dimension_code` / `dimension_name` / `dimension_abbr`（§5） |
> | **出参（所有接口）** | **`dimensionCode` / `dimensionName` / `dimensionAbbr`** —— 包括 `dimensions[]` 数组内的元素（接口 1 / 17 / 20 / 22 / 23 / 24 / 26 原写作 `code` / `name` / `abbr` 的，**一律改齐**） |
> | **入参（query / path / body）** | **一律 `dimensionCode`**（接口 2 的 path 变量也从 `{dimension}` 改为 `{dimensionCode}`） |
> | **Python 内部接口** | 同出参规则（§6.6 的 `dimensions[{ code, ... }]` 一并改） |
>
> 下文各接口表格中仍写作 `dimension` / `code` / `name` / `abbr` 的，**一律以本规则为准**（逐处改写属文案清理，不再单独列为变更项）。⚠️ ~~**例外**：`erl_gap_analysis_item.dimension` 列名本轮**不改**（§5.8），但它对外的出参仍叫 `dimensionCode`~~ → **2026-09-18 该例外整条消除**（v4.57，§0.31-Z9）：该列**已随升级脚本 `sprint118/V22` 改名为 `dimension_code`**，而它的出入参本来就叫 `dimensionCode` —— **列名与出入参两边从此一致，§6 的命名规则在 ERL 全域再无例外**。

> ⚠️ **破坏性变更声明（**2026-09-08 新增**）** —— `CIOaas-api/standards/coding.md` §9 要求「已发布接口禁止删除字段或改类型，破坏性变更须新路径 + `BREAKING CHANGE`」。本轮确实产生了破坏性变更：
>
> | 类型 | 具体 |
> |------|------|
> | **删出参字段** | 接口 5 `submissionSeq`、接口 7 `records[].isLatest`（**⚠️ 2026-09-09 已回退：该字段重新下发** —— 当时连出参一起删掉是误伤，前端类型里一直声明着它、`Current` 徽章因此从未出现过，见 §6.3）、接口 21 `changeSummary`、接口 25 `changeSummary` + `basedOnPublishedVersionNo`、接口 9 `version.basedOnPublishedVersionNo`、接口 23/24 `versionNo` |
> | **字段改名** | 各接口的 `dimension` → `dimensionCode`（并新增 `dimensionName` / `dimensionAbbr`）；接口 23/24/26 的 `code` / `name` / `abbr` → `dimensionCode` / `dimensionName` / `dimensionAbbr` |
> | **语义改变** | 接口 24 由「生成新版本」改为「就地替换 + 软删」；所有「最新一次提交」的判定换底 |
>
> **豁免依据**：**ERL 域接口尚未上线**（无正式环境、无外部调用方，§10.1 建库脚本仍处于人工执行阶段），因此**不走「新路径 + BREAKING CHANGE」流程，直接改契约**。⚠️ **一旦 ERL 上线，本豁免即失效**，后续同类改动必须按 §9 走版本化。**前后端必须同一个发版周期上线**（前端调用点清单见 §10.3）。


> 统一前缀：Java 侧 `@RequestMapping("/erl")`，前端经网关调 `/api/web/erl/**`。响应统一 `Result<T>`。入参走 `interfaces/vo/request`、出参走 `interfaces/vo/response`（`standards/coding.md` 三层传输实体强制），**禁止直接暴露 Entity**。
>
> **接口共 29 个**（**v4.30**）：v3.0 的 1~20 + v3.3 的 #21 publish + v3.5 的 #22 scoreDetails + v4.0 的 #23 / #24（**v4.4 语义扩为维度配置读写**）+ v4.1 的 #25 题库版本历史 + v4.2 的 #26 版本题面快照 + **v4.4 的 #27 `POST /erl/gapAnalysis/share`（§6.6，D3）与 #28 `DELETE /erl/assessment/draft`（§6.3，D8）** + **v4.30 的 #29 `POST /erl/assessment/progress`（§6.3 —— 草稿期推进解锁进度，**只算不存、零写入**）**。编号只增不改，删除的接口保留编号空位以免全文交叉引用失效。
>
> **v4.4 三条全局改动，逐接口不再重复声明**：
> ① **维度级提交（R1）** —— 一次提交 = 某公司某期次某端的**单个维度**，填报域（接口 3 / 4 / 5 / 28）的请求体与响应体一律带 `dimension`，原「一条评估含五维」的数组结构降为单维平铺。
> ② **动态维度（D1 / R2）** —— 全文不再有「固定五项 / 五维固定顺序」；维度列表、顺序、权重一律**按当前 `status = 'Active'` 的维度集合**（`~~erl_company_period_config~~（**2026-09-08 已删表**）` → `erl_dimension_config`，§5）返回，期次尚无任何评估时按当前 `status = 'Active'` 的维度集合返回。
> ③ **`period` 缺省口径（R3）** —— 所有 `period` 可选的读接口（1 / 17 / 20 / 22 等），缺省值为**该公司 closed month 所在季度**（复用 Financial Intelligence 域既有服务）；该季度无提交即**返回空态，不回退**到更早期次。

### 6.1 ERL Card（A1 / A2，PRD §3.1）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 1 | `GET /erl/card` | Company Overview 的 ERL 卡片一次取全 | `companyId`、`period`（可选，**v4.4：缺省为该公司 closed month 所在季度**，R3） | `period`、`overallScore`、`stage`、`era`、`bpmmScore`、`gapSummary`、**`shared`**、`dimensions[]`、`radar`、**`benchmarkUrl`**、`hasAnyAssessment` |

`dimensions[]` 每项（**v4.0 改**，**v4.4 补 Gap 区块字段**）：`code`（维度代码，v4.4 起以此为准；即原 `dimension` 字段）/ `name` / `abbr` / `weight`（该维权重百分比，供卡片标注加权口径）/ `founderScore`（**0–9 整数**）/ `gsvScore` / `perceptionGap` / `gapDirection`（`POSITIVE`/`NEGATIVE`/`NONE`）/ `era` / `detailUrl` / **`bothSubmitted`** / **`hasGap`** / **`questionSetMismatch`** / **`mismatchSide`**（后两个 v4.58 新增，P4）。

- **`dimensions[]` 不再恒五项（v4.4，D1 / R2）**：按当前 `status = 'Active'` 的维度集合返回，顺序取 `sort_order`；该期次尚无任何评估时按当前 `status = 'Active'` 的维度集合返回。**已在当前 `status = 'Active'` 的维度集合里删掉的维度**在历史期次照常返回（前端可加 `Retired` 灰样式；该态由「是否还在当前 `status = 'Active'` 的维度集合里」派生，v4.8），不进新期次。
- **`status`（~~`ACTIVE` / `RETIRED`、v4.8 起纯派生~~ → **2026-09-08：`Active` / `Inactive`，落库列**）** —— `dimensions[]` 每项随带，**直接下发 `erl_dimension_config.status` 列值**（§5.1.3）：该维度启用中 ⇒ `Active`，已软删停用 ⇒ `Inactive`（前端据此给历史期次的维度标灰）。~~不落库 / 由「是否还在当前生效版本里」推导~~ 作废（§0.14 随之失效）。⚠️ 与 v4.0 从接口 1 / 2 删掉的那个 `status`（`MET` / `PARTIAL` / `GAP`，§0.9-10）**不是同一个字段**，不要混淆。
- **`bothSubmitted` / `hasGap` / `questionSetMismatch`（v4.4 新增两条 D4，v4.58 新增第三条 P4）** —— 卡片 Gap 区块每维小卡的三条**互相独立**的信息，前端不要合成一个枚举：
  - `bothSubmitted` 决定**圆点颜色**（该维 FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录（**2026-09-08**：同 `(company_id, period, portal, dimension_code)` 内按 `submitted_at DESC, id DESC` 取首条 `SUBMITTED`） → 绿点，否则灰点）；
  - `questionSetMismatch` = 两端该维**题集版本号不等**（不可比，该维未送进分析）⇒ **黄点**；`mismatchSide`（`FOUNDER` / `GSV`）是**落后的那一端**，`questionSetMismatch = false` 时不下发（§0.32-Y2 / Y4，判据只能是维度级 `question_version_no`）；
  - 文字按**四级优先级**取（写死，不靠隐式短路，§0.32-Y5）：`!bothSubmitted` → `Not submitted`；`questionSetMismatch` → `Question set mismatch`；`hasGap` → `Gap analysis ready`；else → `No Gap`。⚠️ **mismatch 排在 `hasGap` 之前**：旧产物未被本轮覆盖时两者会同真，此时显示 mismatch、旧条目不渲染。
  - 计数文案 `{n} of {total} dimensions have gap analysis for {period}` 由前端按本数组自算（`n` = `bothSubmitted && hasGap` 的项数，`total` = 数组长度），**不另加计数字段**。
- **`shared`（v4.4 新增，D3）**：该 `(company, period)` 的差距分析是否已分享给 Founder 端。管理端据此决定 `Share to founder` 按钮态（**每一个维度两端都已提交**才激活，未达成置灰，底部提示 `Share unlocks once gap analysis is available for all {total} dimensions in {period}.`（**2026-09-08**：`{total}` = 当前 `Active` 维度数））；公司端 `shared = false` 时整个 Gap 区块显示空态（同接口 17，§6.6）。Share 动作走**接口 27**。

- ❌ **删除 `status`**（`MET`/`PARTIAL`/`GAP`）—— PRD 2026-09-02 删去「每维度状态摘要」展示项，该枚举零依据（§0.9-10）。
- ⚠️ **公司端不下发 `gsvScore` / `perceptionGap` / `gapDirection`**（v4.0，PRD §3.5「创始人只能查看自己的分数」，§4.3）。
- `overallScore` 为**加权**综合分（§7.1），随出参附 `weightsApplied[{dimension, weight}]`，供前端在 tooltip 里说明「按 FRL 30% / PRL 20% … 加权」。

`radar`（**v4.0 改**，**v4.4 顶点数动态化**）：**仅管理端下发；公司端整个字段不返回**（PRD §3.5「该图仅在 Portfolio 端显示」，§0.9-5）。结构为 `series[]`，每项 `{ key, label, values[] }`，~~`values[5]` 按 `FRL / PRL / BERL / RRL / TRL` 固定顺序~~ → **v4.4 作废**：`values` 与出参 `dimensions[]` **同长、同序**（按当前 `status = 'Active'` 的维度集合的 `sort_order`），前端按数组长度渲染顶点数（§0.10-D1）。取值为**维度 level 分（0–9 整数）**。四条序列：`FOUNDER` / `GSV` / `BENCHMARKIT` / `TOP_GSV_QUARTILE`，后两条取**适用基准记录的各维度分**（§7.8），无适用记录时该序列不下发。

- **`benchmarkUrl`（v4.4 新增，D7；**v4.25 补期次**）**：~~`/exitReadiness/benchmark?companyId={id}`~~ → **`/exitReadiness/benchmark?companyId={id}`**`[&period={period}]` —— **期次空则整段不拼**（写法与 `ErlDimensionServiceImpl#historyUrl` 一致，§0.29-Z5），正常卡与空态卡**两个 build 点都带**。⚠️ **D1 自己不按期次取数** —— 该参数纯粹是 D1 面包屑「Score Details」回 A4 的**返回上下文**，不带则 A4 走服务端缺省期次（closed month 所在季度，§0.10-R3）打开另一期。⚠️ **改的是取值、不是字段**（本字段的契约零变更）。**仅管理端下发**（与 `radar` 同条件，公司端整个字段不返回）。前端在**雷达图正下方**渲染链接 `Benchmarkit & Top GSV Quartile ›`（PRD §3.5，`9a203ce`）—— 这是基准页 D1 的**站内唯一入口**，§8.1.1 原「入口在维度详情页 / A4 页内链接」的描述一并订正（该链接在 §8.4 的 A3 / A4 交互表里从未定义，按原文档实现基准页站内不可达）。
- `bpmmScore` 为 1–5 参考数字，来源见 §13-Q1；无数据返回 `null`，前端隐藏该行。
- `gapSummary` 取 §6.6 的 `summary`（**v4.4：单份产物，不再按 audience 取**，D3），截断展示。~~E 模块待定期间该字段恒 `null`~~ → **v4.4 作废**：PRD `8324a3f` 已删「待定功能」，Goldie 进 V1，本字段正常下发（§0.10-D2）；公司端在 `shared = false` 时为 `null`（D3）。
- **无提交即空态，不回退（v4.4，R3）**：缺省期次取该公司 closed month 所在季度，该季度两端均无提交 → `hasAnyAssessment = false` + 各分数字段 `null`，**不降级显示上一季度数据**；closed month 取不到（公司无任何 actuals）同样空态并打 WARN 日志（§9 原降级逻辑作废）。

### 6.2 维度详情页（A3 / E2，PRD §3.2 / §3.5 —— **v4.9：A5 弹窗已删除**，§0.15）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 2 | `GET /erl/dimension/{dimension}` | A3 单维度模板页 | path `dimension`（**v4.4：即配置项 `code`，不再是枚举值**）；`companyId`、`period`、`portal`（默认 `FOUNDER`） | `header`、`submission`、`questions[]`、~~`strengths[]`~~、`gaps[]`、`actions[]` |

- `header`（**v4.0 改**）：`name` / `abbr` / `questionCount` / `weight` / `founderScore` / `gsvScore` / `perceptionGap` / `era` / `levelScore` / `terminatedLevel` / `benchmarkPosition`（**公司端恒不下发**）。
  - ❌ **删除 `status`**（状态摘要，§0.9-10）；❌ **删除 `dataSources` 出参**（Data Sources & Cadence，§0.9-13）。
  - ⚠️ **公司端不下发 `gsvScore` / `perceptionGap` / `benchmarkPosition`**（v4.0，§4.3）。
  - **`levelScore` / `terminatedLevel`**（v4.0 新增）：该端在本维度的得分与止步 level，页头据此显示 `Level 4 · Harvest & Growth`（九级全 Yes 时 `terminatedLevel = null`，显示 `All levels cleared`）。
  - `benchmarkPosition`：`{ period, benchmarkitScore, topQuartileScore }` —— **本维度**的两个基准分（取 §7.8 的适用记录），无适用记录时为 `null`（v3.1 明确到维度粒度）。
- `submission`：`period` / `submittedBy` / `role` / `submittedAt` / **`questionVersionNo`**（v3.4：元数据栏标注该次提交所用的题集版本，PRD §3.2 元数据栏）。
- `questions[]`（**v4.0 改**）：`questionText` / `eraBand` / `eraLabel`（**`{Era 名} - {level}`，如 `Founder Era - 1`**，PRD §3.2）/ `evidenceSource` / `yesNo` / `note` / `attachments[]` / `locked`（该题所属 level 是否未解锁 —— 未解锁题在**已提交**记录里恒不出现，此字段只在填报页接口 3 用得到，A3 侧恒 `false`）。
  - ❌ **删除 `answerType` / `score`**（1–9 打分格式已废，§0.9-1）；❌ **删除 `criteria`**（判定标准不进需求设计，**v4.9**，§0.15）。
  - **只返回已作答（= 已解锁）的题**，按 `eraBand` 升序、`sortOrder` 升序；未解锁 level 的题不在列表中（用户当时没看到它，展示它等于伪造未发生的作答，§7.2）。
  - `portal=GSV` 且调用者为公司端 → 直接 `BadRequestException`（PRD §3.2 公司用户无 GSV Tab）。
- `gaps[]` / `actions[]` 来自 `erl_gap_analysis_item`，无分析记录时为空数组。
  - ❌ **删除 `strengths[]`（v4.4，D4）**：原型定档「有 gap 的展示建议，没有的不展示」，`item_type` 的 `STRENGTH` 枚举值随之删除（§5.x），出参不再有该数组。
  - ~~按**当前用户 audience** 过滤~~ → **v4.4 作废**：差距分析已收敛为**单份产物**（无 `audience` 维度，D3），两端读到的是同一份内容；公司端在 `shared = false` 时两个数组均为空（§6.6）。
  - ~~E 模块待定期间三者恒为空数组~~ → **v4.4 作废**（Goldie 进 V1，§0.10-D2）。

### 6.2.1 全维 Score Details（A4，2026-08-28 裁决；**v3.5 新增**）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 22 | `GET /erl/scoreDetails` | A4 一页取全维度逐题明细 | `companyId`、`period`（可选，**v4.4：缺省为 closed month 所在季度**，R3）、`portal`（**v4.4：改为可选**，见下） | `header`、`submission`、`dimensions[]`、`benchmark` |

- **`header`（v3.6 新增，v4.0 微调，**v4.20 改渲染口径**）**：`overallScore`（**加权**）/ `stage` / `era` / `weightsApplied[]`。~~A4 是 F2 `View` 的落地页，PM 点进来不该只看到逐题明细而拿不到整体判断（§0.8-12）~~ → **v4.20 作废**（§0.24-Z2，§0.8-12 已整条撤销）：**A4 不再渲染 `overallScore` / `stage` / `era`**，页头只剩 H1；这三项**出参保留**（契约零变更）供其它调用方使用；~~**`weightsApplied` 仍被前端消费** —— 末位基准 Tab 表尾那行加权 `Average` 取的就是它~~ → **v4.22 作废**（§0.26-Z1）：**那行 `AVERAGE` 已撤下 ⇒ A4 此后 `header` 四项一项都不渲染**；`weightsApplied` 同样**出参保留**（契约零变更）供 ERL Card / F2 等其它调用方使用。**仅此四项**，Perception Gap / Strengths & Gaps / 雷达图仍不在 A4 上重复（§8.4「A4 与 A3 的关系」）。无提交时前三项均为 `null`。
- `dimensions[]` ~~**固定返回五项**，顺序 `FRL / PRL / BERL / RRL / TRL`~~ → **v4.4 作废**（D1 / R2）：**按当前 `status = 'Active'` 的维度集合动态返回**，顺序取 `sort_order`；期次尚无评估时按当前 `status = 'Active'` 的维度集合。每项（**v4.0 改**）：`code`（原 `dimension`）/ `name` / `abbr` / `levelScore`（0–9 整数）/ `terminatedLevel` / `weight` / `questionCount`（**该维已作答题数**）/ `totalQuestionCount`（该版本该维全部题数）/ `questions[]` / **`addNewUrl`** / **`historyUrl`**。❌ 删除 `score`（一位小数口径）与 `scoredCount`（`SCORE` 题计数，已无此概念）。
- **`status`（**2026-09-08**：`Active` / `Inactive`）**：`dimensions[]` 每项随带，口径与接口 1 完全相同（直接下发落库列值，不再派生，§5.1.3）。
- **每张维度卡的卡头入口（v4.4 新增，D5，PRD §3.5 / §3.7）**：后端随每维下发两个链接，体例同 F2 的 `detailUrl` —— `addNewUrl` = `/exitReadiness/assessment?companyId={id}&period={period}&dimension={code}`（`Add New`；**v4.21 补**：这张卡装的是 **GSV 卷**时再追加 **`&portal=gsv`** —— 判据是「所看的卷」而非调用端，公司端恒 Founder 卷、恒不带，§0.25-Z1），`historyUrl` = `/exitReadiness/history?companyId={id}`**`[&period={period}]`**`&dimension={code}`（~~`View History`~~ → **v4.20：`View history`**，h 小写，原型原文，§0.24-Z9；**v4.21 补 `period`**，**期次空白时整段不拼** —— B3 自己不按期次过滤、该参数**不参与取数**，只作 B3 面包屑「Score Details」回 A4 的返回上下文，不带则 A4 落到服务端缺省期次而非用户来时那一期，§0.25-Z2）。⚠️ **v4.21 的两处改的都是「取值」、不是「字段」** —— 两条链接仍由后端算好整条下发、前端不拼路径，**接口 22 契约零变更**。两个能力 A3 已有，v4.4 只是**位置挪到 A4 的每张维度卡卡头**；原**页级** `+ New` / `View history` 取消（PRD 未提，且与维度级提交矛盾）。§8.4「A4 上不加跳 A3 的入口（YAGNI）」这条判断随之**撤回**。
- **`portal` 改为可选，管理端两端一起返回（v4.4，D5，PRD §3.7「组合端需同时呈现 GSV 与 Founder 的记录」）**：管理端不传 `portal` 时，`dimensions[]` 每项以 **`portals[{ portal, submission, levelScore, terminatedLevel, questionCount, totalQuestionCount, questions[] }]`** 承载两端数据，顶层 `submission` 为 `null`；显式传 `portal` 时行为与 v4.3 完全一致（单端，顶层 `submission` 照旧）。**公司端忽略该入参，恒按 `FOUNDER` 单端返回**（PRD §3.5「创始人只能查看自己的分数」，§4.3）。
- **`questions[]` 与接口 2 完全同一个结构**（同一个 `ErlQuestionDetailDTO`）：`questionText` / `eraBand` / `eraLabel` / `evidenceSource` / `yesNo` / `note` / `attachments[]` —— **不新造第二套题目结构**；❌ 同接口 2 **无 `criteria`**（**v4.9**，§0.15）。
- `submission` 与接口 2 一致（`period` / `submittedBy` / `role` / `submittedAt` / `questionVersionNo`）。
- `benchmark`：该期次适用基准记录的**各维度明细**（~~`ErlReferenceScoreItemDTO[]`~~ → **订正为 `ErlBenchmarkDimensionDTO[]`** —— 前者不存在，`ErlReferenceScoreItem` 是实体、只在 service 内部用；§5.6.1，**v4.4：项数随配置版本，不再恒五项**），取数规则同 §7.8；**公司端一律不下发**（§4.3），无适用记录为 `null`。
- **实现挂在既有的 `ErlDimensionService` 上新增一个方法**（`listAll`），Controller 用既有 `ErlDimensionController`，**不新建 service / controller 类** —— A4 与 A3 的差别只是「全维 vs 单维」，权限、版本、计分、裁剪规则完全相同。
- **一次查全**：全部维度的题目、答案、附件批量查出后在内存归组，**禁止按维度循环调接口 2 的逻辑**（N+1）；管理端双端模式同理，两端一次查出。
- 题目一律按该评估绑定的 `erl_question_config_version_id` 渲染（§7.9-①，与接口 2 同）。**v4.4**：维度级提交后 `erl_question_config_version_id` **每维一份**，同一期次不同维度可能绑不同题库版本，各自按自己的版本渲染，系统不阻止也不告警（R1）。
- **A4 公司端可访问（v4.4，D5）**：~~V1 不为公司端加 A4 入口（§13-Q17，2026-08-28 裁决）~~ → **已被 PRD `57225d2` 推翻**，ERL Card 右上角 `Full View ›` 是 A4 入口，**两端都有**（PRD §3.5 写「仅 Company portal」，但 2026-09-06 原型显示组合端卡片同样有，按原型落，PRD 回写 M9）。公司端访问时按上一条恒 `FOUNDER` 单端、`benchmark` 不下发；显式传 `portal=GSV` 仍 `BadRequestException`（同接口 2）。

### 6.3 填报（B，PRD §3.3 / §3.4）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 3 | `GET /erl/assessment` | B1 / B2 打开问卷（含回填草稿）；**恒按该评估绑定的题库版本渲染**（§7.9-⑤） | `companyId`、`period`、`portal`、**`dimension`**（v4.4 必填，R1） | `assessmentId`、`status`、`dimension`、`questionVersionNo`、`answeredCount`、`totalCount`、`levelScore`、`canSubmit`、`levels[]`、**`lastSavedAt`**、**`lastSavedBy`**、**`latestPublishedVersionNo`**、**`hasNewerQuestionSet`** |
| 4 | `POST /erl/assessment/draft` | ~~自动存草稿~~ → **v4.30：手动存草稿**（幂等增量；**只由 `Save as draft` / `Submit` 两个按钮触发**）+ **回算解锁进度** | `companyId`、`period`、`portal`、**`dimension`**（v4.4 必填）、`answers[{questionId, yesNo, note?, attachments[{fileId}]}]`（**2026-09-09**：`fileName` / `fileSize` 入参删除，服务端按 `file_id` 查 `files`，§5.5）（**v4.6：顶层 `dimensionAttachments` 入参删除** —— 附件双端统一题级，只经 `answers[].attachments` 提交，§0.12） | `unlockedLevel`、`levelScore`、`terminated`、`answeredCount`、`canSubmit`、`savedAt`、**`lastSavedBy`** |
| 5 | `POST /erl/assessment/submit` | 提交**本维度** | 同接口 4（**v4.0：`dimensionScores` / `divergenceAcks` 入参删除**，§0.9-3）+ **`autoAnswerNo`**（v4.41，缺省 `false`；**仅本接口读**，接口 4 / 29 忽略 —— 三个接口共用同一张入参） | `assessmentId`、`dimensionCode`（+ `dimensionName` / `dimensionAbbr` 快照）、~~`submissionSeq`~~（**2026-09-08 删除**，列已删）、`levelScore`、`terminatedLevel`、`era` |
| 6 | `GET /erl/assessment/periods` | 期次下拉 | `companyId`、**可选 `dimension`**（v4.4） | `periods[]`（`period` + 各端 `latestStatus` + `submissionCount`，**v4.4：口径见下**） |
| 7 | `GET /erl/assessment/history` | B3 历史列表 | `companyId`、可选 `dimension`（**v4.4 口径已变，见下**）、可选 `portal` | `records[]` |
| 8 | `GET /erl/assessment/{id}` | B3 某次提交的详情（复用 A3 题级布局） | path `id`、**可选 `dimension`**（v4.4，D12） | 同接口 2 的 `submission` + `questions[]`（该次提交时的状态） |
| **28** | **`DELETE /erl/assessment/draft`** | **B1 `Reset` 按钮：丢弃并重置当前草稿（v4.4 新增，D8）** | `companyId`、`period`、`portal`、`dimension` | `assessmentId`、`unlockedLevel`（恒 `1`）、`answeredCount`（恒 `0`） |
| **29** | **`POST /erl/assessment/progress`** | **草稿期推进解锁进度：只算不存、零写入（v4.30 新增）** | `companyId`、`period`、`portal`、**`dimension`**、`answers[{questionId, yesNo}]`（与接口 4 同形入参；`note` / `attachments` 可传但服务端不读） | `dimensionCode`、`unlockedLevel`、`levelScore`、`terminated`、`answeredCount`、`canSubmit`、`levels[]` |

**规则**：
- **`questionVersionNo`（v3.4）**：该评估绑定的题库版本号。**首次打开（无草稿记录）时取当时最新的已发布版本并落库，此后不再变**；题库后续发布新版本对本次评估**完全无影响**（§7.9-⑤）。前端在问卷页头以次级文字显示 `Question set v{n}`。**v4.4（R1）：绑定粒度变为「每维一份」** —— 同一公司同一期次的各维度可能绑不同题库版本（各自首次打开的时点不同），系统**不阻止、不告警**，各自按自己的版本渲染与计分。
- **~~`dimensions[]`（接口 3，v4.0 重定义）~~ → v4.4 降为单维平铺（R1）**：一次填报 = 一个维度，出参不再有维度数组，直接平铺 `dimensionCode`（**2026-09-08 改名**，原 `dimension`）/ `dimensionName` / `dimensionAbbr`（**2026-09-08 改名**，原 `name` / `abbr`）/ `weight` / `unlockedLevel` / `levelScore` / `terminated`（本维是否已到终止态）/ `levels[]`；`levels[]` 每项 `{ eraBand, eraLabel, state, questions[] }`，`state ∈ { CLEARED（全 Yes，前端折叠并打勾）, ACTIVE（当前作答中）, BLOCKED（本 level 有 No，终止于此）, LOCKED（未解锁） }`。**`LOCKED` 的 level 只下发 `eraBand` / `eraLabel` / `state`，`questions[]` 为空数组** —— 未解锁的题面不下发到前端，否则用户可从网络面板提前看到后续题目（PRD §3.3「就不再显示下一 Level」）。
- **`lastSavedAt` / `lastSavedBy`（接口 3 出参，v4.4 新增，D9，PRD §3.3）**：取 `erl_assessment.updated_at` / `updated_by` join 用户表得到 `{ name, role }`，**不新增快照列**。~~填报页顶部显示 `Last saved {time} by {name} ({role})`~~ → **2026-09-15 / 16 两次订正**：实际串是按钮行左下的 `Draft saved {UTC 时刻} (UTC) by {姓名}`（**不显示角色**），且**只在本次访问内点过 `Save as draft` 之后才出**（v4.38）；「进来时接手了谁的草稿」改由顶部 `Draft restored` 横幅讲，见 §8.4-D9。配套的产品语义必须写明：**草稿是公司共享的、不区分账户** —— A 保存后 B 打开看到的是 A 的内容，B 的保存**直接覆盖**（草稿唯一索引 `(company_id, period, portal, dimension_code) WHERE status = 'DRAFT'` 不含用户维度，模型上天然如此）。提交人则以**最终点提交的那个人**为准（`submitter_name` / `submitter_role` 提交时快照），即使草稿全程由他人保存。
- **`latestPublishedVersionNo` / `hasNewerQuestionSet`（接口 3 出参，v4.4 新增，D10，PRD §3.3「若题库已更新，则提示题库更新，不做强制退出和更新」）**：`hasNewerQuestionSet = latestPublishedVersionNo > questionVersionNo`。版本锁定本体不变（仍恒按绑定版本渲染，§7.9-⑤），~~填报页无任何提示、无任何变化~~ → **v4.4 作废**：~~填报页顶部挂一条**非阻断、可关闭、无操作按钮**的 banner `The question library has been updated (v{n}). This assessment continues on v{m}.`~~ → **2026-09-15 再次作废**：改为**强阻断二选一弹窗**（v4.41 回写，见 §8.4）——**存过草稿**（`status = DRAFT`）且 `hasNewerQuestionSet` 时一进页面就弹、不可关闭。（§9 与 §7.10-N1 / N3 的表述同步订正）。**2026-09-16（v4.54）再加一条：这份草稿还得真有内容** —— `answeredCount = 0` 的空草稿（清空后没再存过的那种）由前端在载入时就地走接口 28 改绑到最新已发布版本、直接换成新题库，**不弹窗**；服务端出参口径一字未动。
- 草稿保存**幂等增量**：只 upsert 传入的 `answers`（含其 `attachments`），不影响未传项。**服务端在每次保存后按 §7.2 重算该维的 `unlocked_level` / `level_score` / `terminated_level` 并回写**（**v4.4：三列已上提到 `erl_assessment`**，R1），出参把新的解锁进度带回前端 —— **解锁判定只在服务端做**，前端不自行推断（否则前端算法与提交校验会漂移）。**v4.30 补**：草稿期不再落盘，解锁进度改由**接口 29 只算不存**地推进，但这条不变量**没有被破除** —— 计分用的是服务端同一份 `ErlLevelScorer`，且落盘（接口 4）与提交（接口 5）时服务端仍会按传入答案**重算一遍**，前端带来的进度值一概不采信。
- ~~**期次绑定维度配置版本（v4.4 新增，R2）**：首次创建评估时写入 `erl_company_period_config` 并永不改写~~ → **2026-09-08 整条作废**：该表已删（§5.1.4），**不再有任何期次-配置绑定**。后续任何期次的维度列表、权重、综合分、Stage、雷达图一律读 `erl_dimension_config` 当前 `Active` 行 —— **历史会随改权重 / 增删维度而漂移（已接受，§13-Q21）**。
- **拒绝对未解锁 level 的题作答**（v4.0）：`answers` 中出现 `eraBand > unlockedLevel` 的题 → `BadRequestException("Answer levels in order.")`。这是逐级解锁的服务端兜底，防绕过前端直接提交后续 level。
- **改答已作答的题会重算并可能回收解锁**（v4.0 定档）：把某题从 No 改回 Yes → 该 level 若因此全 Yes，则解锁下一 level；把某题从 Yes 改成 No → **该 level 之后的所有答案与附件一并删除**（它们已不该存在），出参 `unlockedLevel`（**v4.4：原 `dimensions[].unlockedLevel`**）回退。前端据此收起后续 level 并提示 `Later levels were reset because an earlier answer changed to No.`
- `totalCount` = 该题集版本**本维度**的全部题数（**v4.4：口径随维度级提交收敛到单维**）；`answeredCount` = 本维度已作答题数（= `erl_assessment_answer` 行数（`where erl_assessment_id = ?`））。逐级解锁下二者通常**不相等**，这是正常的（§0.9-17）。
- **`canSubmit`（v4.0 新增，v4.4 改）**：~~五个维度**全部**到达终止态~~ → **v4.4 作废**（R1）：**本维度**到达终止态且本维度已解锁题全部作答时为 `true`（PRD §3.3「就不再显示下一 Level，激活提交按钮」）。前端提交按钮直接绑该字段，不自行判断。
- 提交前置校验（**v4.0 重写，v4.4 按维度级提交改口径**）。⚠️ **v4.41：三条校验对任何调用方一视同仁，没有旁路** —— `autoAnswerNo = true`（B 填报页「题库已更新」弹窗的 `Submit draft content`）只是在校验**之前**先把顺序上第一道未作答的题补成 No（本维随之终止、漏答归零），补完照样逐条走下面三条；而且它**本身还有一条前置** —— 仅当该草稿确实还绑在旧题库版本上（`hasNewerQuestionSet`）时才被接受，否则**静默忽略**、按原规则校验（2026-09-16 代码审核追加，见 v4.41-④）；~~2026-09-15 的 `allowIncomplete` 曾跳过 1、2 两条~~ **已作废**。⚠️ **编号不是报错优先级** —— 服务端实际先判第 3 条（`totalCount <= 0`）再判 1、2；三条不会同时命中（0 题维度的 `unansweredCount` 恒 0 且 `terminated` 恒 true），编号沿用是因为全仓注释与台账都按「§6.3 校验 3」引用它：
  1. **已解锁的题全部已作答**，否则 `BadRequestException("Please answer all visible questions before submitting.")`。
  2. ~~五个维度全部到达终止态~~ → **v4.4 作废**（R1）：**本维度到达终止态**（本维出现至少一个 No，或九级全 Yes），否则 `BadRequestException("Keep answering until this dimension reaches a No or clears all nine levels.")`。~~**本维在已发布版本中 0 题时视为已终止、`levelScore = null`**（§9）~~ → **2026-09-07 订正**：**该维 0 题时一律拒绝提交**，见下方校验 3 —— 视图侧 `canSubmit` 本来就要求「该维有题」，提交侧从前漏了这一条，于是 0 题维度能落出一条 `level_score` 恒为 null 的 SUBMITTED 行，污染 ERL Card / 组合层 / Share 门槛判定。其余维度是否已提交**不影响本次提交**。
  3. **该维在本期次绑定的题库版本里必须有题**（`totalCount > 0`），否则 `BadRequestException("This dimension has no questions in the question library version bound to this period.")`（**2026-09-07 新增**）。与视图侧 `canSubmit` 的三个条件**逐条对齐** —— 视图侧本来就要求「该维有题」，提交侧从前漏了这一条，属同一契约两个口径。
  4. ~~五维 `manualScore` 必填~~ / ~~软确认 `ack`~~ —— **v4.0 删除**（PRD 已删该要求，§0.9-3）。
- 提交成功后：该行 `status = SUBMITTED`、写 `submitted_at` 与 `dimension_name` / `dimension_abbr` 快照（**2026-09-08**：~~`is_latest = true` + 前一条置 `false`~~、~~`submission_seq = max + 1`~~ **两列已删，不再写**；组的定义为 `(company_id, period, portal, dimension_code)`，**最新一条由 `submitted_at DESC, id DESC` 判定**）；~~五行 `erl_assessment_dimension` 的 `level_score` / `terminated_level` 由服务端算定并冻结~~ → **v4.4 作废**（R1：该表整表删除）：**`erl_assessment` 本行的 `level_score` / `terminated_level` / `unlocked_level` 由服务端算定并冻结**。**已 SUBMITTED 的记录不可再改**（PRD §3.3）；再次填报即新建下一条 `DRAFT`。
- **接口 28（v4.4 新增，D8，PRD §3.3 `Reset`）**：在一个事务内清空**当前草稿**（`status = 'DRAFT'` 的那一行）的**全部答案与附件**，`unlocked_level` 回到 `1`，草稿行本身保留（`answeredCount = 0` 的空草稿）。**v4.26 追加一步**：清完答案后**把这条草稿改绑到当时最新的已发布题库版本**（`erl_question_config_version_id` + `erl_question_config_dimension_version_id` **同一时刻一起写**），于是 Reset 之后看到的就是最新题集（§0.30）。⚠️ **顺序不可换** —— 改绑必须在删答案**之后**：答案行上的 `erl_question_config_id` 指向旧版本的题行，先改绑再删会留下一批读侧匹配不上的孤儿答案。⚠️ 该组织当下**没有任何已发布版本**时保持原绑定（该列 NOT NULL）；已经绑的就是最新版时两列都不动。⚠️ **出参不变**（仍是 `assessmentId` / `unlockedLevel` / `answeredCount` 三个字段）—— 前端 Reset 成功后本来就重拉接口 3，新版本号与题目列表由那一次取回。
  - **附件一并删除**：附件挂在作答上，随作答一并删（`erl_answer_attachment` 按 `erl_assessment_answer_id` 批量删，v4.6）；已入知识库的文件**不回删知识库条目**（同 §6.7 的既有边界，知识库是公司级资产）。
  - 前端**必须二次确认**，弹窗写明「答案与已上传附件将一并删除，且不可恢复」。
  - 目标行不存在或已 `SUBMITTED` → `BadRequestException("No draft to reset.")`；已提交记录**不受影响**。
  - 该接口同时是 §13-Q23「摆脱不掉的旧草稿」的解法 —— 叠加 R1 的单维终止门槛，**§13-Q23 关闭**。
  - 顶部按钮组定档为 `Save as draft` / `Cancel` / `Reset` / `Submit`：`Save as draft` = 手动落盘（走接口 4；~~与 1.5s 去抖自动保存**并存不互斥**~~ → **v4.30 作废**：自动保存已取消，**接口 4 只由 `Save as draft` 与 `Submit` 两个按钮触发**，草稿期的解锁推进走**接口 29**）；`Cancel` = 直接离开页面，**不做任何数据操作**（不调接口）。⚠️ **v4.30 起草稿未必已在服务端** —— 没点 `Save as draft` 就离开即全部丢失，且**不做任何拦截或提示**（§8.4「B 草稿落盘时机」）。
- **接口 29（v4.30 新增，需求方 2026-09-15 裁决「不点按钮绝不写库」）**：与接口 4 **同形入参**（复用同一张请求体），服务端照常按 §7.2 算 `unlockedLevel` / `levelScore` / `terminated` / `canSubmit` 并按解锁进度装配 `levels[]` 回传，但**不写任何一张表** —— 不建草稿行、不 upsert 答案、不删附件、不回写 `unlocked_level` / `level_score` / `terminated_level` 三列，**零写入是本接口的核心不变量**。
  - **只有 `questionId` + `yesNo` 参与计算**：`note` / `attachments` **不参与计分、服务端读都不读**；`yesNo` 仍 `@NotNull`，未作答的题前端不发（与接口 4 一致）。
  - **鉴权与维度校验与接口 4 逐条相同**：`portal` 可读性、`dimension` 必须属于当前 `status = 'Active'` 的维度集合（§4.3-L6）、跨租户题库隔离；取题的组织来源是**被填报的公司**，不是调用者登录态组织（读写必须同源）。
  - **`LOCKED` 的 level 不下发题面这条过滤照旧生效**（`questions[]` 为空数组，见上方 `dimensions[]` 条） —— 正因为新解锁 level 的题面只能由服务端按进度下发，草稿期才需要这么一个接口（否则答满一级后屏上毫无反应、Submit 永远亮不起来）。
  - 因不落库，出参 `levels[].questions[].yesNo` **恒为 `null`**，前端必须**以本地作答为准**、不得用回包重建答案（否则用户答案会被抹平）。
  - 出参**刻意不带** `submissionCount` / `fund` / `latestPublishedVersionNo` —— 这些值在一次填报期间不会变，接口 3 已经给过，放在逐答调用的接口上是纯浪费。
  - 已 `SUBMITTED` 的记录不受影响（本接口本就不写库）；本接口**不替代接口 4** —— 答案要持久化仍必须点 `Save as draft` 或 `Submit`。
- **接口 6 的口径（v4.4，R1）**：维度级提交后 `latestStatus` / `submissionCount` 天然是「该端**该维度**」的口径 —— 传 `dimension` 时按该维度返回；不传时 `latestStatus` 取该端**各维度的最保守值**（有任一维度未提交即 `DRAFT`），`submissionCount` 取各维度之和。维度列表按当前 `status = 'Active'` 的维度集合取（D1）。
- `records[]` 字段（PRD §3.9，**v4.4 按 D12 / R1 调整**）：`assessmentId` / `period` / `portal` / **`dimensionCode`**（v4.4 新增，一条记录 = 一个维度；**2026-09-08 改名** + 随带 `dimensionName` / `dimensionAbbr` 快照）/ `submittedAt` / `submitterName` / `submitterRole` / `fund` / `answeredCount` / `totalCount` / `levelScore` / `terminatedLevel` / `stage` / `era` / **`isLatest`**（boolean；~~2026-09-08 随 `is_latest` 列一并删除~~ → **2026-09-09 重新下发**，判据见下方「排序与 SOT」。⚠️ **算出来的，不落列** —— `erl_assessment.is_latest` 列仍然不存在、本次无 DDL 变更，service 在已查全的列表上按四元组归组标出） / **`questionVersionNo`**（v3.4 新增 —— 同期次多次提交可能基于不同题库版本，题数分母因此不同，不标版本号会被当成 bug，见 §7.10-N2）。默认 `submittedAt DESC`。
  - **排序与 SOT（**2026-09-08**；**2026-09-09 订正排序键**）**：~~`records[]` 排序键为 `period, portal, dimension_code, submitted_at DESC, id DESC`~~ → **实现只按 `submitted_at DESC, id DESC` 排**（两个派生查询 `findByCompanyIdAndStatusOrderBySubmittedAtDescIdDesc` / `...AndPortalAnd...` 的排序键就写在方法名里），即**一条按提交时间倒排的平铺列表**，不做按四元组的外层归组排序 —— 这与本段开头"默认 `submittedAt DESC`"一致，原先那句排序键的写法**与同一段自相矛盾**。四元组只用于**判定 SOT**，不用于排序；**每个 `(companyId, period, portal, dimensionCode)` 四元组分组内的首行即该组 SOT**（接口 7 单公司调用，故页面上看到的是三元组分组）。⚠️ 不传 `dimensionCode` 时返回**多个四元组混排**，**因此 SOT 不能取全表第一行** —— 由后端按四元组标 `isLatest`（见下，§8.4-B3）。
    - **2026-09-09：改由后端下发 `isLatest`，前端不再自己分组**。判据 = 同 `(companyId, period, portal, dimensionCode)` 四元组内 `status = 'SUBMITTED'` 且 **`submitted_at DESC, id DESC` 的第一条**（接口 7 只返 `SUBMITTED`，草稿不进 `records[]`，故不存在草稿占用 SOT 名额的问题；同秒两次提交按 `id` 降序破平），与 `ErlAssessmentRepository#findLatestSubmittedByCompanyAndPeriodAndPortal` 的 `NOT EXISTS` 谓词**同源** —— 正是 §7.7「读侧必须全部走同一个 Repository 方法」要求的那一处口径。列表本就一次查全（`portal` / `dimension` 两个过滤摘掉的都是**整组**），故在内存里按四元组归组标记，**不按维度回查库**。
    - ⚠️ **2026-09-09 补记（隐形 bug）**：`is_latest` 列删除时，出参字段也一并删了，但**前端 `HistoryPage.tsx` 的类型里一直声明并使用 `isLatest`**（选页头记录 `records.find(r => r.isLatest)`、打 `Current` 徽章、决定行高亮 `currentRow` / `pastRow`）⇒ 该值恒为 `undefined`/`false`，**`Current` 徽章从上线起就没出现过、每一行都按「往期行」降级渲染**。编译、类型检查、测试全都发现不了（与 `status === 'RETIRED'` 同类）。修在后端而非前端：让前端按列表自己算等于把这条 SOT 判据实现第二份，正是上面那条 ⚠️ 要防的事。
  - **提交序号**：`submission_seq` 已删，本接口**不再下发任何序号字段**；B3 列表**不再显示 `Submission #n`**（若后续仍要序号，只能按分组内行号实时算，**翻页会漂移**）。
  - ~~`dimensionLevels[{dimension, levelScore, terminatedLevel}]`（v4.0）~~ → **v4.4 作废**：记录已是维度级，两个值直接平铺为 `levelScore` / `terminatedLevel`。
- **列语义（v4.4，D12，PRD §3.9）**：
  - **新增 `Submitted` 列** —— 直接渲染 `submittedAt`（数据侧本就有，只差这一列）。
  - ❌ **删除 `Completion` 列** —— PRD 已从「列表最少字段」中移除。原挂在该列的次级标注 `v{n}` / `stopped at L{t}` **挪到分数列下方的次级文字**；`answeredCount` / `totalCount` 降为**页头用途**的接口字段（不再有列），§7.1.1 关于分母口径的论证**作为实现说明保留**。
  - **分数列改为「维度 Overall Score」** —— 取该维 level 分（`{levelScore}/9` 整数）+ 该维 Era 徽章，**不是加权综合分**（`overallScore` 字段因此从 `records[]` 中移除）。
  - **`Portal` 列仅管理端渲染** —— 公司端只有 Founder 侧数据，该列恒定值、无信息量。
- **接口 7 的 `dimension` 口径（v3.6 定档，v4.0 沿用，v4.4 重写）**：~~评估是**整卷提交**（一条记录覆盖五维），因此该参数**不过滤记录条数**，而是把数值切到该维度~~ → **v4.4 作废**（R1）：维度级提交后**一条记录本就只属于一个维度**，`dimension` 因此是**真正的行过滤**（`where dimension_code = ?`），不再有「切数值」的绕法，`answeredCount` / `totalCount` / `levelScore` 天然就是该维口径。不传 `dimension` 时返回该公司全部维度的提交记录，混排按 `submittedAt DESC`（此时 `Dimension` 列必显示）。前端从 A4 的 `View History` 进入时带 `?dimension={code}`，在列表页头标注当前过滤维度（`Financial Readiness (FRL)` + 清除入口）。
- **接口 8 的 `dimension` 入参（v4.4 新增，D12）**：从带维度的历史列表进入详情时透传，**只渲染该维度**的题目明细；不传时按该记录自身的 `dimension` 渲染（记录已是维度级，该入参实为一致性校验 —— 与记录不符即 `BadRequestException`）。

### 6.4 题库配置（C，PRD §3.8）

> **v3.3 契约变更**：C 模块的读写**一律面向草稿版本**，写接口的定位参数由题目 `id` 改为 **`questionKey`**（§0.5-5）—— 写时复制会让草稿行拿到新 `id`，前端手里的 `id` 属于已发布版本，按 `id` 定位在「首次编辑」这一步必然失配。

| # | 方法 / 路径 | 用途 | 关键入参 |
|---|-------------|------|----------|
| 9 | `GET /erl/question` | C1 列表（按 `eraBand` 分组、组内带题数、按 `sortOrder` 排序）；**返回草稿版本**，无草稿时返回最新已发布版本 | `dimension` |
| 10 | `POST /erl/question` | C2 新增 | `dimension`、`eraBand`（1–9 level）、`questionText`、`evidenceSource`（**v4.0：`answerType` 入参删除**；**v4.9：`criteria` 入参删除**，判定标准不进需求设计，§0.15）—— 与 PRD §3.8 的题目字段逐项一致 |
| 11 | `GET /erl/question/{questionKey}` | C3 编辑回填 | path `questionKey` + **query `dimensionCode`（2026-09-08 新增，必传）** |
| 12 | `PUT /erl/question/{questionKey}` | C3 更新 | path `questionKey` + **query `dimensionCode`（定位用的**原维度**，2026-09-08 新增、必传）** + 体同 10（体里的 `dimensionCode` 是**目标维度**） |
| 13 | `DELETE /erl/question/{questionKey}` | C3 删除（**草稿版本内物理删行**） | path `questionKey` + **query `dimensionCode`（2026-09-08 新增，必传）** |
| 14 | **`PUT /erl/question/reorder`** | **C4 拖拽重排（v3.0 新增）** | `dimension`、`eraBand`、**`questionKeys[]`**（该 band 内的完整新顺序） |
| 21 | **`POST /erl/question/publish`** | **C5 发布草稿版本（v3.3 重定义）** | 仅可选 `organizationId`（v4.7）；出参 `versionNo`、`publishedAt`、~~`changeSummary{...}`~~（**2026-09-08 删除**，`change_summary` 列已删）+ **新增 `dimensions[{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }]`**（本次发布写入 `erl_question_config_dimension_version` 的逐维快照，§5.1.5；**2026-09-08 编码阶段补 `dimensionName` / `dimensionAbbr`** —— 快照行本就存着它们，与接口 26 共用同一个出参结构，发布后的 toast 也能直接报维度名而不是一串 code） |
| 23 | **`GET /erl/dimension/config`** | **C6 读维度配置**（v4.0 的 `GET /erl/weight` → v4.4 扩为 `Dimension Configuration`，D13） | 可选 `organizationId`（v4.7，缺省 = 登录态组织）+ **可选 `includeDeactivated`**（**2026-09-08 新增**，默认 `false`）；出参 ~~`versionNo`~~（**2026-09-08 删除**，配置已去版本化）、`savedAt` / `savedBy`（**2026-09-09 换底**：取本组织**全部行审计列 `updated_at` 的 max**、`savedBy` 取该行的 `updated_by`；`saved_at` / `saved_by` 两列已删，**契约不变**）、`dimensions[{dimensionCode, dimensionName, dimensionAbbr, sortOrder, weight, **status**}]`（**2026-09-08**：字段改名 + **`status` 重新下发**，~~v4.8：删 `status`~~ 作废；默认只返 `Active` 行，带 `includeDeactivated=true` 时返全量供 C6 回看与恢复；**2026-09-09**：C6 **恒**带 `includeDeactivated=true`（`Show deactivated` 开关已撤下，停用行由常显区块承载，§8.4-C6），该入参保留供其它调用方）+ **`deletable`**（**2026-09-09 新增**，boolean 非空：`true` ⟺ 该 `dimension_code` **从未进入任何已发布题库版本的维度快照** ⇒ 行尾给垃圾桶=删除；`false` ⇒ 给电源按钮=停用。⚠️ **判据必须 join `erl_question_config_version` 并过滤 `status = 'PUBLISHED'`** —— `erl_question_config_dimension_version` **草稿版本上也有行**（§5.1.5 开头那条 ⚠️），只查快照表会把「只在未发布草稿里改过题」的维度误判为不可删）。⚠️ **`deleted = true` 的行任何情况下都不下发**（**含 `includeDeactivated=true`**）—— 那个入参管的是 `status`，与 `deleted` 正交，混用会把已删维度重新暴露到 `Deactivated Dimensions` 区块里）、`total`（**2026-09-08**：改为 **`Active` 行**的权重合计 —— 含 `Inactive` 行的合计永远不是 100，前端的 Exceeds/Needs 提示会算错） |
| 24 | **`PUT /erl/dimension/config`** | **C6 整组保存维度配置**（D13） | **顶层**：`savedAt`（**2026-09-08 必传**，取自上一次接口 23；不匹配即「配置已被他人修改，请重新加载」，防 lost update。**2026-09-09 补边界**：该组织**首次保存**时库里一行都没有、令牌本身就是 `null`，此时**必须传 null** —— 一边有一边没有同样算冲突；不匹配返回的是**业务错误**：~~HTTP 400~~ → **HTTP 200 + `success: false`**（2026-09-09 订正，§4.3），既不是 409、也不是 400）+ `deactivatedCodes[]`（**2026-09-08 必传**，本次要停用的已有维度 code，**可为空数组**）+ **`deletedCodes[]`**（**2026-09-09 新增**，本次要**删除**的已有维度 code ⇒ 置 `deleted = true`。⚠️ **与 `deactivatedCodes` 不同，它可缺省**（缺省 / null = 空数组）：`deactivatedCodes` 必传是为了杜绝「未出现即停用」的隐式软删（下方校验 ⑥），而 `deletedCodes` **缺省表达的就是「什么都没删」** —— 这是本身安全的默认值，**没有可保护的对象**，不存在「本该删却被漏掉」这种隐式破坏）+ `dimensions[]`（**整组替换**）。<br>**数组每项二选一**（**2026-09-08 改为显式判别**，~~`dimensionCode` 可缺省~~ 作废）：① **已有维度**：`{dimensionCode, dimensionName, dimensionAbbr, sortOrder, weight}` —— `dimensionCode` 必须命中本组织已有行；② **新增维度**：`{isNew: true, clientRef, dimensionName, dimensionAbbr, sortOrder, weight}` —— **不带 `dimensionCode`**，`clientRef` 是前端生成的**幂等键**（本次请求内唯一）。**两者都不带、或同时带 `dimensionCode` 与 `isNew` → 业务错误**（~~400~~，2026-09-09 订正，§4.3）。<br>~~**另有一个顶层可选入参 `confirmCreateAnyway`（boolean）**（**2026-09-09 补记，此前漏写**，实现早已有）：新增维度的 `dimensionName` + `dimensionAbbr` 命中某个 `Inactive` 行时**软阻断**，返回需显式确认的业务错误「已有同名的已停用维度，是否改为恢复它？」，带 `confirmCreateAnyway = true` 重放才创建新维度（新 code）—— 这是 `Inactive` 软删模型的直接产物（§11-86-⑩ 有对应用例）。~~ → **2026-09-15 删除**（需求方当日裁决「新增维度不做任何重名 / 重缩写校验」，v4.31）：**同名软拦截连同入参 `confirmCreateAnyway` 整条取消** —— 新增项与任何已有行（含 `Inactive` 行）同名 / 同缩写一律**直接创建**，不阻断、不要求二次确认；两行靠 `dimension_code` 区分。<br>出参：同 23（无 `versionNo`）**+ `created[{clientRef, dimensionCode}]` 映射**（**2026-09-08 新增；2026-09-09 降级**：~~允许同名同缩写时前端无法从整份列表里把新 code 对回本地哪一行，必须靠它~~ —— **整体替换语义下前端无需逐条对回**，实现是用出参 `dimensions[]` 整体替换本地列表、从不读 `created`（§8.4-C6）；该映射**保留给需要保持本地行身份的调用方**，也便于排障）；出参 `dimensions[]` **按 `sortOrder` 升序**（契约保证） |
| 25 | **`GET /erl/question/version`** | **C7 版本清单（v4.1 新增）** —— v4.2 起是 C7 页头版本下拉的数据源 | 仅可选 `organizationId`（v4.7，缺省 = 登录态组织）；出参 `versions[]`。**2026-09-09（§0.22-Y1）：契约一字不改** —— 仍返回 `DRAFT` + `PUBLISHED`、仍按 `versionNo` 倒序草稿最前；变的只是**消费方**：C7 的版本下拉此后**只取 `status === 'PUBLISHED'` 的项**，过滤做在前端取数 hook `useQuestionVersions` 里 |
| 26 | **`GET /erl/question/version/{versionNo}`** | **C7 某一版的整份题面（v4.2 新增）** | path `versionNo`；出参复用接口 9 的 `{ version, questions[] }` + **v4.10 新增 `dimensions[]`**（**v4.4：全部维度一次给全，项数动态**） |

- **C 模块 11 个接口（9-14 / 21 / 23 / 24 / 25 / 26）的组织归属：缺省取 `SecurityUtils.getOrganizationId()`，v4.7 起接受可选 query 入参 `organizationId`**（POST / PUT 亦走 query，不进 Request 体），且只认调用者组织树内的组织（§4.3）；仅管理端可调。
- **接口 24 的校验（v4.4 重写，D13 / R2）**：
  1. **`status = 'Active'` 的维度权重合计恰为 `100.00`**（`numeric(5,2)` 精确比较，不用浮点等值；~~v4.8：不再有「仅 ACTIVE 行合计」这一说~~ → **2026-09-08 反转**：软删后 `Inactive` 行仍在表里，若计入则永远凑不满 100），每个 `0 ≤ weight ≤ 100`，否则 `BadRequestException("Dimension weights must add up to 100%.")`。前端 Save 按钮同条件禁用，**服务端不因前端已拦就省掉校验**。
  2. **维度集合合法**（**2026-09-08 整条重写** —— 原文「新增维度的 `code` = 该项 `abbr` 的大写形式」与「与旧版本比对」均已作废）：① **带 `dimensionCode` 的项**必须命中本组织已有行，否则**业务错误**（~~400~~ → HTTP 200 + `success: false`，2026-09-09 订正，§4.3）（跨组织的 code 天然命中不到）；② **带 `isNew` 的项**由服务端生成 code（§5.1.3），**不对 code 做任何格式 / 长度 / 大写校验**（同一列里 `FRL` 与 `OPS4K7M` 并存，任何断言都会误杀一方）；③ `dimensionAbbr` **1–8 字符**（~~且在本次提交的数组内不重复、也不与本组织其它 `Active` 行重复（§5.1.3 的 `uk_erl_dimension_config_abbr`）~~ → **2026-09-15 删除查重那半句**，需求方当日裁决「新增维度不做任何重名 / 重缩写校验」、索引已整条删除，v4.31）—— ⚠️ **长度校验必须保留**：解耦后 `abbr → code` 那条隐式长度约束消失了，列宽就是 `varchar(8)`，不校验会直接撞列宽；④ `sortOrder` 无重复；⑤ **至少保留一个 `Active` 维度**（全停用时合计恒为 0，Save 永远失败）；⑥ **集合完整性校验（本次新增，防静默软删）**：`当前 Active 集合`（**2026-09-09 明确：`deleted = false` 的那些**）必须恰等于 `带 code 的项` ∪ `deactivatedCodes` ∪ **`deletedCodes`**（**2026-09-09 补第三个并集项**）。对不上即**业务错误**（~~400~~，2026-09-09 订正，§4.3）并列出缺口 —— 前端漏传一行的 code 就会落到这里，**不得静默当新增处理**。⚠️ **不补第三项，删除就一次也成功不了**：被删的那一行既不在 `dimensions[]` 也不在 `deactivatedCodes[]` 里，每次删除都会被判成「前端漏传了一行」并报业务错误 —— 这是本版最容易漏改的一处（新功能全部写对，删除仍然全挂）；⑦ ~~**同名软拦截**：带 `isNew` 的项如果 `(dimensionName, dimensionAbbr)` 命中本组织某个 **`Inactive`** 行 → 返回需显式确认的业务错误「已有同名的已停用维度，是否改为恢复它？」（带 `confirmCreateAnyway` 重放才放行）—— 否则管理员误删后重填会建出**孪生维度**，历史全挂在旧停用行上且产品内无补救入口。~~ → **2026-09-15 整条删除**（需求方当日裁决，v4.31）：**新增维度不做任何重名 / 重缩写校验**，同名 / 同缩写直接创建，入参 `confirmCreateAnyway` 一并删除。⚠️ 上面那条「会建出孪生维度」的代价**仍然是事实**（历史照旧挂在旧停用行的 `dimension_code` 上），只是需求方明确接受 —— 恢复旧行的正路仍在（`Deactivated Dimensions` 区块的 `Activate`，§8.4-C6-⑤）。
  3. **`deletedCodes[]` 的三条校验（**2026-09-09 新增**，§0.21-X6）** —— 一律是**业务错误：HTTP 200 + `success: false`**（与乐观锁冲突同形态，§11-91-⑦），**且库中不得有任何写入**：
     - ⑧ **code 不命中本组织已有行** → 沿用既有文案 `Unknown dimension code: {code}`（跨组织的 code 天然命中不到，与 ① 同一道理）。
     - ⑨ **该 code 在已发布版本的快照里出现过**（`erl_question_config_dimension_version` join `erl_question_config_version` 且 `status = 'PUBLISHED'`）→ `This dimension was published in a question set and cannot be deleted: {code}. Deactivate it instead.` ⚠️ **前端根本不显示垃圾桶，但抓包可以直接传** —— 这条校验是唯一的实际防线，**不得因「前端已按 `deletable` 拦了」而省掉**。文案点名替代动作（改用停用），否则用户只知道不能删、不知道该干什么。
     - ⑩ **同一个 code 同时出现在 `dimensions[]` / `deactivatedCodes[]` / `deletedCodes[]` 中的两个及以上** → `Dimension cannot be saved, deactivated and deleted at once: {code}`。**不定义优先级** —— 任何优先级都是在猜用户意图（「又保存又删」到底是哪个？），而三个桶的组合是前端状态机出 bug 时的典型产物，报错让它暴露在开发期而不是变成一次静默的错误落库。
     - ⚠️ **可删性检查必须在 `validate()` 阶段、用整组锁读到的 `existing` 判定**（§7.11-② / §0.21-X8）：~~第一阶段 `parkAll` 会把该组织**全部行**落成 `Inactive` 并 flush，**之后再读 `status` 看到的全是 `Inactive`** —— 检查落在那之后，⑥ 的集合完整性与「这一维原本是不是 `Active`」两件事同时失去判据，而且**不报错**，只是开始放行本该被拦住的删除。~~ → **2026-09-15：`parkAll` 已删除**（v4.31 / §7.11-②），这个陷阱随之消失；**结论仍然成立** —— 三条校验与 ⑥ 的集合完整性一律在 `validate()` 阶段用整组锁读到的 `existing` 判定，**落库前不写任何一行**（业务错误要求「库中不得有任何写入」）。
  4. ~~五维齐全 / 必须齐五维~~ → **v4.4 作废**（D1）：维度集合本身由本接口定义，不存在「齐五维」这一校验。
  - **Save 按钮双条件**：① 脏态（维度增 / 删 / 排序 / 权重任一变化）② 权重合计 = 100%；越界提示 `Exceeds 100% by {n}%` / `Needs {n}% more`。
- ~~**保存即生成新的配置版本（v4.4，R2）**~~ → **2026-09-08：就地整组替换，不产生版本**：每次接口 24 成功即按 `(organization_id, dimension_code)` **upsert** `erl_dimension_config`（覆盖 name / abbr / sort_order / weight / status；**2026-09-09**：不再写 `saved_at` / `saved_by`，两列已删，「上次保存于何时 / 谁保存的」由审计列 `updated_at` / `updated_by` 承接），**提交里缺席的维度置 `status = 'Inactive'`（软删，不删行）**；`erl_dimension_config_version` 已整表删除，无版本行、无 `is_latest`。**保存即全局生效**。
  - **保存即生效，保存后立即影响所有期次（含历史期次）的综合分与 Stage**（v4.0 口径 → ~~v4.4 作废（R2）：从下一个未绑定期次起生效、历史永不漂移~~ → **2026-09-08 再次反转回 v4.0**）。Save 确认框文案同步为「**新配置立即全局生效，已有期次的综合分、Stage 与雷达图形状会随之变化**」（§8.4 C6）。⚠️ **连带副作用（**2026-09-08 新增**）**：改维度集合会回溯改变 Share 门槛（§7.5-S1）与 Gap 区块的 `{n} of {total}` 计数，而§7.5 原本「置脏的触发点只有评估提交一个」⇒ ~~接口 24 保存成功后必须同事务把该组织全部 `erl_gap_analysis` 置 `stale = true` 并复位 `shared = false`~~ → **2026-09-19 改判**（v4.59 / §0.33-X11）：产物已在另一个服务的库里，**跨服务不可能同事务**；改由「**Active 维度集合进指纹**」自然覆盖 —— 停用维度会改变指纹，其余维度若都已提交则下次读或下次提交即重生成并覆盖（`shared` 随覆盖复位）；改权重不改变作答、指纹不变，本就不该触发。<br>⚠️ **残留边界（已知并接受）**：**新增**一个 Active 维度、而该期次的分析此前已 `shared = true` 时，公司端会继续看到那份按旧维度集合生成的分析（内容不假、只是少一维），直到新维两端提交后重生成 —— 因为「新维未提交 ⇒ S1 不成立 ⇒ 不重生成也不判 stale」正是 §0.33-X2 刻意要的（否则页面永久 `Refreshing…`）。要收需新接口或新判定，属产品口径问题，已记 `CIOaas-api/docs/待优化项.md`。
  - 配置页的「**停用**维度」（**2026-09-09**：入口由垃圾桶改为**电源按钮**）= **软删**（**2026-09-08 推翻 v4.8 的物理删除**）：该维度**不出现在接口 24 提交的 `dimensions[]` 里**、且其 code 在 `deactivatedCodes[]` 中，服务端据此置 `status = 'Inactive'`；**行与 `weight` 原样保留**，历史提交记录照常可查，`Retired` 灰样式由 `status` 列**直接判定**（~~派生~~ 作废）。
  - 配置页的「**删除**维度」（**2026-09-09 新增的第二个动作**）= 置 **`deleted = true`**：只对 `deletable = true`（该 code 从未进入任何已发布题库版本的快照）的维度开放，code 走 `deletedCodes[]` 显式点名；行留在表里但**所有读侧一律排除**、页面两处都不显示、**无恢复入口**（§5.1.3）。
  - ~~**无条件允许删除**，不做「有历史数据禁止删除」的前置拦截（§13-Q24）~~ → **2026-09-09 作废**（需求方当日裁决）：**拦截现在存在**，但判据是「**是否进入过已发布题库版本**」而不是「**有无历史数据**」 —— 后者会连「有人填过、但题库从没发布过」的维度也拦住（那种维度删掉是安全的），而**保护对象也不是那一行**（软删下行不会消失），是**已发布题库版本的语义**：那份版本的维度快照与按 code 关联的历史，必须始终解得出那个维度。**§13-Q24 由「已关闭」改判**（§13 / §0.21-X12）。
- **`Dimension Configuration` 的改动不进题库版本、不激活 Publish，走自己的 Save**（§5.1.2 / §0.9-19；题库 Tab 的 Publish 语义不变，§7.9）。
- **单题接口（11 / 12 / 13）新增必传 query 参数 `dimensionCode`（**2026-09-08**）**：题目行的键位已是
  `(organization_id, dimension_code, version_no, question_key)`，而题目集版本号按维度各自自增 ——
  **不知道维度就解析不出用哪个 `version_no`**，`questionKey` 单独不再是一个完整的定位符。
  配置页本就按维度分 Tab，前端手上一定有这个值。
  - ⚠️ **接口 12 的两个 `dimensionCode` 不是同一个**：query 里的是**原维度**（定位用，= 当前所在 Tab），
    请求体里的是**目标维度**。两者不同即**跨维度移动**：题目行从原维的版本线移到目标维的版本线上，
    **两条线都要先克隆**（各调一次 `ensureDimensionCloned`），并排到目标组末尾；diff 上表现为
    原维 removed + 目标维 added，口径自洽。
- **接口 10 / 12 / 13 / 14 均触发写时复制**：进入 service 先 `ensureDraftVersion()`（**2026-09-08 改为两级判据**，§7.9-②）—— ① 无草稿版本行则同事务内建一条（组织级 `version_no = max + 1`），有则**取行锁复用**；② **再判本维度本轮是否已克隆**（`draftDimensionVersions()`），未克隆才克隆该维题目行并拿新的 `version_no`。~~整份克隆最新已发布版本~~ 作废（只克隆被改动的那个维度）。**漏了第二级判据 = 直接写穿已发布版本**，再在草稿版本上执行本次变更。四个接口都不改已发布版本一个字节。
- 接口 14 在一个事务内按数组下标重写该 band 全部题目的 `sort_order`；**只允许同 band 内重排**。**跨 band 移动不走本接口**，而是由题目行内的 `Era band` 下拉触发**接口 12 的全量更新**（v4.1，§8.4 C4；v4.0「跨 band 移动请走编辑表单」的写法作废）。
- 接口 9 出参：根节点增加 `version { versionNo, status, lastEditedBy, lastEditedAt }`（**2026-09-08**：~~`basedOnPublishedVersionNo`~~ 删除 —— `based_on_version_id` 列已删，§5.1.1） 与 **`changeSummary { added, modified, removed, reordered, hasDraft }`** —— **`hasDraft` 即 Publish 按钮的激活依据**（存在草稿版本 = 有未发布变更）；每题增加 `changeType`（`ADDED` / `MODIFIED` / `REORDERED` / `UNCHANGED`，由草稿与最新已发布版本按 `question_key` 逐字段 diff 得出），供列表打徽章。**`changeSummary` 是全局的，切 Tab 不重算**（PRD §3.8「~~五个维度~~**任意维度**有变更，按钮即激活」，**v4.4：维度数动态**）。
- 接口 21 在一个事务内把草稿版本 `status` 置 `PUBLISHED`、写 `published_at` / `published_by`（**2026-09-08**：~~`change_summary` 快照~~ 列已删），**并为每个 `Active` 维度写一行 `erl_question_config_dimension_version`**（`dimension_code` / `dimension_name` / `dimension_abbr` / `question_version_no` / `sort_order` / `bound_at`，§5.1.5），同事务内把上一条 `is_latest` 置 `false`、本版置 `true`。**无草稿版本时返回业务错误**（~~400~~，2026-09-09 订正，§4.3）（前端按钮此时已禁用）；不做「重复点击幂等」的特殊处理 —— 发布成功后草稿已不存在，第二次点击落到同一分支。
- **接口 25 出参（v4.1）**：`versions[]`，每项 `versionNo` / `status`（`DRAFT` | `PUBLISHED`）/ `publishedAt` / `publishedBy` / `lastEditedBy` / `lastEditedAt`（**2026-09-08 删两个字段**：~~`basedOnPublishedVersionNo`~~、~~`changeSummary{...}`~~ —— `based_on_version_id` 与 `change_summary` 两列均已删，§5.1.1）。**按 `versionNo` 倒序，草稿（`DRAFT`）排在最前**。
  - ~~`changeSummary` 取 `erl_question_config_version.change_summary` 的发布快照、不实时重算~~ → **2026-09-08：该列已删，接口 25 不再返回 `changeSummary`**。不改为实时重算的理由不变：历史版本的对比基线早已随后续发布改变，实时 diff 会算出与当时不同的数字（接口 9 的实时 diff 保留，供 Publish 按钮用）。
  - **仅可选入参 `organizationId`**（缺省取 `SecurityUtils.getOrganizationId()`，v4.7 起可指定组织树内的组织）、**仅管理端可调**，公司端报业务错误（~~400~~，2026-09-09 订正，§4.3 —— 端类型 / 组织越权同样由 `ErlAccessServiceImpl` 抛 `BadRequestException`）。**只读接口，不触发写时复制**（不调 `ensureDraftVersion()`）。
  - ⚠️ **草稿行照常下发，但 C7 不再显示它们（**2026-09-09**，§0.22-Y1）**：C7 的版本下拉按 `status === 'PUBLISHED'` 过滤，过滤**落在前端取数 hook `useQuestionVersions`**、**不下沉到服务端** —— 「库里到底有没有草稿版本」是「`Publish` 按钮能不能点」的判据来源，服务端一旦把草稿行滤掉，那个判断就没了数据来源；而 C7 是本接口**当前唯一的消费方**，过滤放在页面侧的代价只是一个 `filter`。⚠️ 由此带来一个**空态**：只有草稿、没有任何已发布版本的组织，C7 下拉为空、页体走 `No published question set versions yet.`（§8.4-C7 / §11-90）。
  - ~~**不新增表** —— `erl_question_config_version` 已有 `published_at` / `published_by` / `change_summary` 三列~~ → **2026-09-08 订正**：`change_summary` 已删，只剩 `published_at` / `published_by`；逐维信息取**新表** `erl_question_config_dimension_version`（§5.1.5）。
- **接口 26（v4.2 新增）**：出参**复用接口 9 的 `ErlQuestionConfigListResponse`**（`version` + `questions[]` + **v4.10 新增 `dimensions[]`**），不为它另造一对 DTO/Response。与接口 9 的四点不同：
  - **版本由 `versionNo` 指定**，不是「草稿优先的当前版本」—— 这正是历史版本取不到题面的那道坎；`versionNo` **只在组织内唯一**，故解析时必须带组织（缺省登录态，v4.7 起可由可选入参 `organizationId` 指定并经 §4.3 复核），查不到即 `BadRequestException("Question set version not found.")`。
  - **全部维度一次给全**（接口 9 是单维度），复用已有的 `findByVersionIdOrderByDimensionAscEraBandAscSortOrderAsc`。⚠️ 其中维度序是 `dimension` 列的**字典序**，不是业务序，~~前端按五维固定顺序自行归组~~ → ~~**v4.4 改**（D1）：前端按接口 23 返回的维度配置（`sortOrder`）自行归组与排序~~ → **v4.10 再改**（§0.16-H2 / -H3）：**前端按本接口新增的 `dimensions[]` 归组与排序**，**不再读接口 23 的当前生效配置**（`ErlDimensionEnum` 枚举与前端静态 `DIMENSIONS` 映射仍是删除状态）。
  - **`dimensions[{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }]`（v4.10 新增，**2026-09-08 换数据源 + 改字段名**，**2026-09-09 按实现订正字段清单**：~~`{ dimensionCode, dimensionName, dimensionAbbr, sortOrder, weight }`~~ —— **没有 `weight`、多一个 `questionVersionNo`**）**：~~取该题库版本 `dimension_config_version_id` 所指配置版本的 items~~ → **取 `erl_question_config_dimension_version` 中该 `erl_question_config_version_id` 的逐维快照行**（§5.1.5），按 `sortOrder` 升序。名称 / 缩写 / 顺序均为**发布当时的快照**，后续改名不影响。⚠️ **出参里根本没有 `weight`**（**2026-09-09 按实现订正**）：~~`weight` 不在快照表里（§5.1.5 已标待裁决）—— 当前取 `erl_dimension_config` 的实时值并会随改权重漂移~~ → **不成立**。实现走的正是 §5.1.5 定档的**出路 ②** —— 接口 26 的 `dimensions[]` 另造了一个**不含 `weight`** 的窄 Response `ErlQuestionConfigDimensionVersionResponse`（DTO `ErlQuestionConfigDimensionVersionDTO` 同形，两处 builder 见 `ErlQuestionConfigVersionServiceImpl` 的发布态与草稿回退分支，**从不 set weight**），所以**既不下发、也无从漂移**；前端 `CIOaas-web/src/services/api/exitReadiness/response.ts` 的对应类型注释亦写明「**没有 `weight`、没有 `status`**」。<br>　**新增的 `questionVersionNo`**（int）= **该维在这一版下用的题目集版本号**（§5.1.5 的 `question_version_no`，按 `dimension_code` 自增的那条独立版本线，§5.1；**该维在该版下无题时为 `0`**）—— 发布后前端据此知道「第 n 次发布里，各维分别落到了自己的第几版题目」；它与外层的组织级发布批次号 `versionNo` 不是同一个东西（§5.1.5 的「两者不冗余」一段）。C7 当前不渲染它，字段留着是因为它是这张快照表**唯一**能表达「这一版用的是哪份题」的列。~~绑定列为空时服务端回退当前生效配置~~ → 改为：**草稿版本（无快照行）时回退当前 `Active` 集合**（⚠️ **2026-09-09 起这条回退在 C7 上不可达** —— 下拉只列已发布版本，草稿选不到了，§0.22-Y1；该分支**保留**给 API 直调方）。**接口 9 恒为 `null`** —— 配置页 C1 的维度骨架另走接口 23。⚠️ **2026-09-09（§0.22-Y2 / -Y4）**：本字段是 C7 卡片骨架的**唯一**来源这一点**不变**，而且此后是**唯一**来源的全部含义 —— C7 不再拿接口 23 的当前生效配置做任何事（既不过滤、也不打 `Retired` 灰标），**本页与「今天的维度配置」彻底解耦**。本字段**不按当前配置过滤**：发布当时快照里有几个维度就出几张卡。
  - **`changeSummary` 与每题 `changeType` 恒为 `null`** —— 那是「草稿 vs 最新已发布」的实时 diff，套到历史版本上没有意义（历史版本的对比基线早已改变，同 §5.1.1 对 `change_summary` 不重算的理由）。
  - **只读接口，不触发写时复制**（不调 `ensureDraftVersion()`）；**仅管理端**，公司端报业务错误（~~400~~，2026-09-09 订正，§4.3）。**不新增表**，也**不新增「查全部题」的无版本查询** —— 仍先解析出 `versionId` 再查（§10.1）。
- 新增题目（接口 10）`sort_order = 该 band 当前 max + 1`，`question_key` 新生成 UUID。
- **生效范围（v3.3 全改）**：四类变更**全部只落草稿版本**，对填报页、维度详情页、计分、组合层**一概不可见**，直到接口 21 发布。详见 §7.9。

### 6.5 基准（D，PRD §4；**v3.1 按原型重做**）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 15 | `GET /erl/benchmark` | D1 页（两张卡一次取全） | `companyId` | `latest`、`records[]` |
| 16 | `POST /erl/benchmark` | D2 保存记录 | `companyId`、`period`、`note`、`dimensions[]`（**v4.4：项数动态，见下**） | `recordId` |

**出参结构**：

```
latest    { period,                                  // 最新一条记录的期次（排序键见 §7.8）；无记录为 null
            dimensions[{ code, name, abbr,           // v4.4：按配置版本 sort_order，不再是固定五维顺序
                         benchmarkitScore,
                         topQuartileScore }] }        // 前端按 `6.5/9` 渲染

records[] { id, period, isLatest,
            recordedAt,                              // 真实录入时刻 = 审计列 created_at，ISO-8601 串；为空下发 null（2026-09-10 改，§0.28-Z1）
            recordedBy { name, role },               // created_by join 用户表
            benchmarkitAvg, topQuartileAvg,          // 各维度平均，服务端算（§7.8）
            note,                                    // 空返回 null，前端显示 "—"
            dimensions[{ code, name, abbr, benchmarkitScore, topQuartileScore }] }
```

- **维度列表动态（v4.4，D1 / R2）**：~~固定五维顺序 `FRL/PRL/BERL/RRL/TRL`~~ 作废 —— 读接口 15 按**该记录 `period` 绑定的配置版本**返回维度与顺序（该期次无绑定时按当前 `status = 'Active'` 的维度集合），写接口 16 按**当前 `status = 'Active'` 的维度集合的全部维度**校验。
- **页面入口（v4.4 补，D7；**v4.25 补期次**）**：D1 页的站内入口是 **ERL Card 雷达图正下方的链接 `Benchmarkit & Top GSV Quartile ›`**（~~`/exitReadiness/benchmark?companyId=`~~ → **v4.25**：`?companyId=`**`[&period={period}]`**，随接口 1 的 `benchmarkUrl` 下发，**仅管理端渲染**）。**另一个入口是 A4 末位基准 Tab 的 `View history`**（2026-09-09 起，§0.24-Z4；**v4.25 同款带期次**，由前端拼，§0.29-Z1）—— 两个入口都带期次，是为了让 D1 的面包屑「Score Details」能回到用户来时那一期（**D1 自己不按期次取数**，§0.29）。§8.1.1 原「入口在维度详情页 / A4 页内链接」的描述**订正为本条** —— 该链接在 §8.4 的 A3 / A4 交互表里从未定义，按原文档实现 `/exitReadiness/benchmark` 与 `/benchmark/add` 站内不可达（既有文档缺口，本版一并补上）。
- `records[]` ~~按 `period` **倒序**~~ → **2026-09-10 补次级键**（§0.27-Z2）：按 **`period DESC, created_at DESC, id DESC`** 倒序（同期次可有多条，最近录入的排前面）；只有首条 `isLatest = true`（D1 的 `LATEST` 徽章）。⚠️ **2026-09-08 澄清**：这个 `isLatest` 是**基准记录的派生字段**（按 `period` 倒序的首条），**与已删除的 `erl_assessment.is_latest` 列没有任何关系**，不受本次改动影响、**不要跟着删**。
- `recordedAt` ~~= 由 `period` 推导的**期末日**（`2026Q2 → 2026-06-30`，`LocalDate`）~~ → **2026-09-10 改判**（§0.28-Z1）：**审计列 `created_at` 的真实录入时刻**，Java 类型 `Instant`、下发 **ISO-8601 串**（如 `2026-09-10T07:21:33Z`）；`created_at` 为空的历史行下发 **`null`**（不拿期末日兜底）。三个展示位（D1 `Record History` 的 `SUBMISSION TIME` 列、D1 卡一与 D3 详情卡的提交元信息行）一律经 `formatErlIsoDate()` 渲染成 **`YYYY-MM-DD`**（需求方定的写法，只到日），**不直出原串**（§8.4-D1）。⚠️ 同期次可有多条（§0.27-Z1）且 `PERIOD` 列相同 ⇒ 这一列是屏上**唯一能分辨先后**的信息，**不可再退回期末日**。⚠️ **字段名不改**（仍叫 `recordedAt`）—— 改的是类型与语义，前端 DTO 三层同步。
- **`Details` 不额外发请求** —— 每条记录的各维度明细随 `records[]` 一并下发（单公司按季度累积，量级极小），前端行内展开 / Modal 渲染，复用 `Latest by Dimension` 的表格组件。
- 接口 16 的 `dimensions[{ code, benchmarkitScore, topQuartileScore }]` **必须覆盖当前配置版本的全部维度、各值在 1–9**（**v4.4：原「必须齐五维」**），否则 `BadRequestException`；~~`period` 已存在时返回 `BadRequestException("A benchmark record for this period already exists.")`（唯一约束，§5.6）~~ → **2026-09-10 删除**（§0.27-Z1）：**同期次可重复新增** —— 服务端 `assertPeriodNotTaken` 已删、数据库唯一索引也已改成普通索引，重复期次照常落库为新的一条记录。
- 两个接口**仅管理端可调**（§4.2），公司端调用直接报业务错误（~~400~~，2026-09-09 订正，§4.3）。
- ❌ **删除 v3.0 的 `deltaVsPrior`** —— 新原型两张卡均无环比列（§0.3-5）。

### 6.6 Goldie 差距分析（E，PRD §3.6）

> ~~标题已标「待定功能」，本节整体可摘除（§0.9-12）~~ → **v4.4 作废**：PRD `8324a3f` 已删「待定功能」，**E 模块进 V1**，本节全节生效，原「待定期间隐藏 / 恒 null / 恒空数组 / 仅在需求方确认后才执行」的条件语一律删除（§0.10-D2）。

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 17 | `GET /erl/gapAnalysis` | E1 + E2 读取（读缓存，不触发 LLM） | `companyId`、`period`（**v4.4：缺省为 closed month 所在季度**，R3）、可选 `dimension` | `summary`、**`shared`**、`dimensions[{code, abbr, bothSubmitted, hasGap, narrative, gaps[], actions[]}]`（**2026-09-18 新增 `narrative`**，v4.57，§0.31-Z7；**2026-09-20 每维再新增 `analyzed` / `analyzedAt` / `dimensionStale`**，v4.61，§0.35-G5）、`generatedAt`、`model`、`stale`、`generating`、**`analysisServiceUnavailable`**（顶层，2026-09-20 提交前审核新增，§0.35-G13：Python 不可用 / 401 / 落库失败时置 true，否则这些故障会伪装成每维 `Analyzing…`，而前端的失败态 + Retry 永远触发不到） |
| 18 | `POST /erl/gapAnalysis/generate` | 手动重新生成（仅管理端） | `companyId`、`period` | 同 17 |
| **27** | **`POST /erl/gapAnalysis/share`** | **把该期次的差距分析分享给 Founder 端（v4.4 新增，D3；仅管理端）** | `companyId`、`period` | `shared`、`sharedAt`、`sharedBy` |

- **单份产物，无 `audience`（v4.4，D3）**：~~服务端按调用者端类型判定 audience（公司端 → `FOUNDER`，管理端 → `GSV`），一次调用产出两套口吻~~ → **v4.4 作废**。PRD `8324a3f` 已删「Founder / GSV 两套口吻」整段，改为「GSV 团队可见 + 点 Share 分享给 Founder」。因此：`erl_gap_analysis.audience` 列删除、唯一约束回 `(company_id, period)`、两份 prompt 合并为一份、§8.4「前端不做措辞转换」与「双 audience 回归测试 / 两端口吻不同」的验收项一并摘除。**两端读到的是同一份内容**。
- **`shared` 与可见性（v4.4，D3）**：
  - 管理端（GSV）**始终可读**，不受 `shared` 影响。
  - 公司端（Founder）在 `shared = false` 时**接口 17 直接返回空态**（`summary = null`、`dimensions[].gaps/actions` 为空数组、`generatedAt = null`），§4.2 权限表 E1 / E2 的 Founder 列由「✅ 只读」改为「✅ **仅 `shared = true` 后**」，§4.3 后端强制校验补这一条。
  - **接口 27 的激活门槛**：该 `(company, period)` 下**每一个维度**的 FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录（**2026-09-08**：同 `(company_id, period, portal, dimension_code)` 内按 `submitted_at DESC, id DESC` 取首条 `SUBMITTED`）（PRD 原文「只有所有维度两方都完成时」）；未达成时按钮置灰，服务端仍校验，不满足返回 `BadRequestException("All dimensions must be submitted by both sides before sharing.")`。仅管理端可调，公司端报业务错误（~~400~~，2026-09-09 订正，§4.3）。
  - **重生成后 `shared` 复位（v4.4 新定档，D3 / D19）**：Share 之后任一端又提交新评估触发重生成（§7.5 的置脏 + 异步重生成，依据改标「本设计」，PRD 已删「自动刷新分析」一条），会静默改写 Founder 已看到的内容 —— 故**重生成时 `shared` 一并复位为 `false`**（`shared_at` / `shared_by` 清空），管理端提示「内容已更新，需重新分享」，需 GSV 重新点 Share。
- **`dimensions[]` 的六态信息（v4.4 三态 D4，v4.58 补第四态 P4，**v4.61 补第五、六态**，§0.35-G5 / G6）**：每项 `code` / `abbr` / `bothSubmitted` / `hasGap` / **`questionSetMismatch`** / **`mismatchSide`** / **`analyzed`** / **`analyzedAt`** / **`dimensionStale`**（后三个 v4.61 新增）（后两个 v4.58 新增，口径与接口 1 同源、同一个服务端方法产出，§0.32-Y3）/ **`narrative`（2026-09-18 新增）** / `gaps[]` / `actions[]`，项数与顺序按该期次绑定的维度配置版本（D1）。⚠️ **`narrative` 不参与三态判定** —— `hasGap` 只数 `GAP` 行，一条 `NARRATIVE` 绝不能让「无差距」的维度渲染成有差距（§5.8）。`bothSubmitted` / `questionSetMismatch` / `hasGap` 的语义、渲染规则同接口 1（§6.1）—— **圆点颜色与文字按 §0.35-G6 的六级优先级取**（未提交 → 题集不一致 → **未分析** → **重跑中** → 有 gap → 无 gap；~~§0.32-Y5 的四级~~ 是它的前两级 + 后两级，中间两级 v4.61 插入）。<br>⚠️ **`hasGap` 的语义 2026-09-20 收紧**（v4.61，§0.35-G5）：它**只在 `analyzed = true` 时有意义**，取值来源也由 Java 的 `!gaps.isEmpty()` 改为 Python 下发的 `has_gap` 列 —— 此前「产物里根本没有该维」与「该维确实无 gap」都落到 `hasGap = false`，是本节末尾那条早已预告的缺陷，`View details` 弹框里 `hasGap = true` 才列 gap 条目与建议动作，mismatch 的维度只出琥珀药丸 + 按端分叉的说明（旧条目与旧 `narrative` 都不渲染）。
- ❌ **删除 `strengths[]`（v4.4，D4）**：原型定档「有 gap 的展示建议，没有的不展示」，`erl_gap_analysis_item.item_type` 的 `STRENGTH` 枚举值删除，收敛为 `GAP` / `ACTION`。
- `stale = true`（内容所依据的那批提交已不是最新）或 `generating = true` 时，前端**继续展示旧内容、不清空**（§7.5）。<br>⚠️ ~~并在卡片上显示 `Refreshing…`~~ → **2026-09-20 横幅撤下**（v4.64 / §0.38-K1）：进行时改由维度小卡的 `Analyzing…` / `Updating…` 逐维表达。**两个字段本身不变**，前端仍用它们判「已分享过的内容又被重生成」⇒ 提示需重新分享。<br>**2026-09-19（P3）：两者的来源都换了，但出参形态一字未变** —— `stale` 由 Java **现算指纹与产物里存的 `submission_signature` 比对**派生（不再有 `stale` 列，§0.33-X2）；`generating` 由 **Python 在 GET 时一并返回**（它自己知道那把 Redis 锁在不在，Java 不跨语言探 Redis）。
- **接口 17 / 18 / 27 的出入参在 P3 前后逐字一致 ⇒ 前端零改动**（v4.59 / §0.33-X10）：搬迁只动服务端内部的所有权与协作方式。`submissionSignature` **不外泄到 VO** —— 它是服务端之间的内部约定，前端既不需要也不该看到（**这一条 v4.61 仍然成立**：指纹下沉到维度级后照旧不外泄，前端看到的是由它派生出来的 `dimensionStale`）。<br>→ **2026-09-20（v4.61）起「前端零改动」不再成立**：`dimensions[]` 每项多了 `analyzed` / `analyzedAt` / `dimensionStale` 三个字段，前端小卡状态机随之由四态扩到六态（§0.35-G5 / G6）。**只增不减**，老前端不会报错、但会继续把「未分析」渲染成 `No Gap`，所以前后端须同批上线。

**Python 内部接口**（**Java 内网直连**，非前端可达）：

> ⚠️ **2026-09-19（P3）两处订正**（v4.59 / §0.33-X8）：① ~~经网关调~~ —— 本仓库网关只有 `/api/web/**` 与 `/web/**` 两条路由，**没有 `/api/ai/**` 路由**；实际是用 Nacos 配置项 `cio.erl.ai-base-url` + `HttpRequest` **直连 `python:8090`**（与存量财务预测的 `AI_MODEL_URL` 同款）。② ~~只有一个「生成」端点~~ → **三个**：产物搬到 Python 之后，「读」与「置分享位」也成了跨服务调用。
>
> **读超时按端点分开**：`refresh` 180s（内含一次 LLM 往返），`GET` 与 `share` **10s** —— 绝不能沿用生成端点的 180s，否则一次**页面级读**会把数据库连接挂 3 分钟。鉴权靠**转发调用者的 Bearer token**（Python 侧对每个非豁免路径都回调 Java `check_access`）；异步线程取不到请求上下文，故 token 必须在请求线程内捕获后**作为参数**传进异步任务 —— 走不带 token 的重载会让 Python 一律 401 ⇒ 产物读成 null ⇒ 指纹短路永不成立 ⇒ **每次提交都白烧一次 LLM**。

```
① POST /api/ai/erl/gap-analysis/refresh          生成并落库（2026-09-19 由 /gap-analysis 改名）

入参  companyId、period、organizationId、
      // ⚠️ 2026-09-20（v4.61）：顶层 submissionSignature **已删除**，下沉到 dimensions[] 每项
      dimensions[{ index,                                              // 送给模型的唯一维度标识（1..N，按下发顺序）
                   code,                                               // 2026-09-19 新增：**仅供 Python 落库**，渲染 prompt 时写死剔除
                   submissionSignature,                                // 2026-09-20 新增：该维依据哪一批提交。Java 算，Python 只存不比
                   name, abbr, weight,
                   founderLevelScore, gsvLevelScore, perceptionGap,   // 0–9 整数 level 分（v4.0）
                   founderTerminatedLevel, gsvTerminatedLevel,        // 各自止步的 level（v4.0）
                   questions[{ questionText, eraBand, eraLabel, evidenceSource,
                               founderYesNo, gsvYesNo,                 // 唯一的作答字段（v4.0）
                               founderNote, gsvNote,                   // 证据/备注（关键输入）
                               attachments[{ fileId, fileName }] }] }] // 2026-09-18 新增：两端附件并集，按 fileId 去重、Founder 在前；无附件送空数组
                                                                       // ⚠️ fileId 同样不进 prompt（模型只看得到 fileName / summary / summaryAvailable）
      analyzedContext[{ name, abbr, hasGap, narrative }]               // 2026-09-20 新增：本期次**已分析过的其他维度**的结论摘要
                                                                       // **只读**：不得为它们产出 gaps / actions，也不进 index 体系
                                                                       // 作用：让期次级 summary 覆盖「本轮 + 此前」的全貌（§0.35-G9）

      ⚠️ **2026-09-20（v4.61）起 dimensions[] 只装「本轮要分析的维度」** —— 即「两端都已提交且非 mismatch」
         之中、维度级指纹与产物里存的不等（或产物里没有该维）的那些。全都相等 ⇒ Java 直接幂等短路，不发这次请求

出参  同 ② 的产物对象（落库后的那一份）

② GET  /api/ai/erl/gap-analysis?companyId=&period=      读产物（2026-09-19 新增）

出参  { companyId, period, summary,
        dimensions[{ code,                                             // 2026-09-19：出参只有 code —— index → code 的映射在 Python 内完成
                     analyzed,                                         // 2026-09-20 新增：该维有维度行 = 分析过（本列表里恒 true，留字段是为了 Java 直传）
                     hasGap,                                           // 2026-09-20 新增：显式结论，不再由 Java 数 gaps 行数反推
                     analyzedAt,                                       // 2026-09-20 新增：该维上次分析时刻。格式同 generatedAt（UTC yyyy-MM-dd HH:mm:ss），
                                                                       // 但**逐维取值不同**：这里是该维度行自己的 generated_at，
                                                                       // 顶层 generatedAt 是「最近一轮任意维度」的时间，两者不可互相顶替
                     submissionSignature,                              // 2026-09-20 新增：该维的指纹，回传给 Java 比对得出 dimensionStale
                     narrative,                                        // 2026-09-18 新增：该维叙述段；无差距的维度为空
                     gaps[{ title, note, severity, evidenceMissing }],
                     actions[{ title, why }] }],
        generatedAt, model, shared, sharedAt, sharedBy,
        generating }                                                   // 该 (company, period) 的 Redis 锁是否被持有 —— Java 不跨语言探 Redis

      ⚠️ **2026-09-20（v4.61）两处改动**：① 顶层 submissionSignature **已删除**（下沉到每维）；
         ② **已分析但无 gap 的维度现在也出现在 dimensions[] 里**（hasGap = false、gaps / actions 空数组、
            narrative = null）—— 此前只有「产出了内容」的维度才出现，Java 因此无法区分「没分析」与「无差距」

      ⚠️ **产物不存在也回 200**，给一个 generatedAt = null 的空态对象（Java 据此渲染空块，不当异常）

③ POST /api/ai/erl/gap-analysis/share                   置分享位（2026-09-19 新增）

入参  companyId、period、sharedBy                                       // 门槛（每维两端都已提交）仍由 Java 校验，本端点只置位
出参  { shared, sharedAt, sharedBy }
```

- **维度标识：`index` 送模型、`code` 只供落库（2026-09-19 改判，v4.59 / §0.33-X9）**：~~入参不送 `dimension_code`，出参也用 `index`、由 Java 按下发顺序映射回 code~~ → P3 之后**落库方变成了 Python**，它必须知道 `dimension_code`，故 **`refresh` 入参的维度项同时带 `index` 与 `code`**；**出参则只有 `code`**（`index` 不出现在任何出参里，映射在 Python 内完成）。<br>⚠️ **`code` 进入参、但绝不进 prompt** —— 渲染用户提示词时写死剔除（连 `fileId` 一并剔），并有单测断言「渲染结果不含 dimension code」。**原来那条防线一字未变**：让模型逐字复现 `OPS4K7M` 这类无语义串，一次字符级幻觉（转位 / 少一位）就会让该维全部 gap 与 action 被丢弃，而那个渲染态恰好是**绿点 + `No Gap`** —— 假阴性、全程无日志无告警。P0（2026-09-08）把标识换成 `index` 就是为了它，本次只是额外捎一个不给模型看的落库字段。
- ~~一次调用产出两套 audience（Founder 口吻 / GSV 口吻）~~ → **v4.4 作废**（D3）：PRD 已删「两套口吻」，出参收敛为**单份** `{ summary, dimensions[] }`，`results[]` 与 `audience` 字段删除。
- ❌ **出参删除 `strengths[string]`**（v4.4，D4）。
- **v4.0：prompt 必须理解 level 语义** —— 传入的是 Yes/No 逐级作答与「止步 level」，不是分数。prompt 中要说明：① 维度分 = 最后一个全 Yes 的 level；② **止步 level 内那些答 No 的题，就是该维度最直接的差距来源**，建议行动应优先围绕它们；③ **未解锁 level 的题不在输入中**，不得编造对它们的判断。
- **判断依据收敛为「题干 + 逐题 Yes/No + 双端备注 + level 口径」（v4.9，§0.15）**：入参**不再有 `criteria`** —— 2026-09-06 裁决判定标准不进需求设计（§13-Q25 关闭、回写 M11 关闭）。prompt 里另有一条**反向约束**：**「输入里没有判定标准字段，不得编造标准原文」**（与上一条「不得编造未解锁 level 的判断」同款写法），prompt 版本随之升到 `# version: 1.1`。
- **附件摘要接进输入（**2026-09-18 新增**，v4.57，§0.31-Z6）**：入参每题带 `attachments[{fileId, fileName}]` —— **Java 只送 id 与文件名，不碰摘要**（它不该为了拼一段 prompt 去读 rag 的表）。摘要由 **Python 在生成前按 `fileId` 批量现取** `ai_rag_entry.summary`（进程内直调 rag 读口，**不经网关、不新增缓存表** —— 摘要天然就落在那一列），就地回填成 `{fileName, summary, summaryAvailable}` 再渲染 prompt；**`fileId` 本身不进 prompt**（模型看不到它，也就不可能复述错）。
  - **取不到摘要不等待、不阻断**：提交那一刻摘要可能仍在 `PENDING`、也可能已 `FAILED`，一律降级为 `summaryAvailable = false` 继续分析（读口整体异常同样吞掉 + ERROR 日志，缺哪几个记 INFO）。**差距分析不为附件摘要排队**。
  - **作用域不额外加校验**，由两层天然保证：① Java 已做公司 ACL；② `fileId` 取自该公司该期次的作答行。这两条依据必须写进代码注释，否则后人看到「一个没有作用域校验的批量读口」会以为是漏洞。
  - prompt 侧三条硬约束：**摘要是二手信息**，可作为「证据是否存在」的佐证，**不得当作原文引用**、不得据其编造精确数字或条款原文；**`summaryAvailable = false` 时只知道「存在一份名为 X 的附件」**，**不得凭文件名推断其内容**；**备注为空但有可用摘要 ⇒ 视为有证据**。
- **维度级 `narrative`（**2026-09-18 新增**，v4.57，§0.31-Z7）**：出参每个维度多一个 `narrative` —— 3 句以内、≤60 词，首句陈述该维分数与止步 level，中句概括该维已通过 level 内最有说服力的一条正面证据（来自 Yes 题备注或附件摘要，**用自己的话、不加引号**），末句转折到差距。**无 gap 的维度不产出 narrative**（服务端对「无 gaps 却回了 narrative」的情形直接丢弃并 WARN）。落库为 `item_type = NARRATIVE` 一行（§5.8）。
- **actions 的反套话强约束（**2026-09-18 新增**）**：每条 action 必须锚定到本维度的**一条具体 gap 或一道具体的 No 题**，`why` 里复述那条依据。判定标准写死为 —— **凡是把维度名替换掉之后仍然成立的句子，一律不合格**（`Assign an owner and 90-day plan for the highest-severity {维度} gap.` 这类通用句正是反面教材）。PRD §3.6 要的是「实用的、可执行的行动建议」，通用句等于没有信息量。
- ~~**无备注的题**：prompt 要求在据其产出的条目上置 `evidenceMissing = true`，前端渲染为「未提供备注」（PRD §5）。~~ → **2026-09-18 口径放宽**（v4.57，§0.31-Z8）：置 `evidenceMissing = true` 的条件是该题**既无备注（两端 `founderNote` / `gsvNote` 都空）、又无可用摘要**（`attachments` 为空，或全部附件 `summaryAvailable = false`）；**备注为空但有可用摘要时视为有证据**，置 `false`；模型不确定时置 `true`。前端文案随之改为 **`No supporting evidence provided`**（§8.4 / §9）。**判定在 prompt 里做，服务端只做透传归一**（`evidenceMissing` 缺省按 `false`）。
- ~~双方分数均高、无实质差距时，prompt 明确要求承认此为公司优势~~ → **v4.4 删除**（D4）：原型定档「有 gap 的展示建议，没有的不展示」，无 gap 的维度前端直接显示 `No Gap`，prompt 中该段一并删除，对应验收项删除。
- **`actions[].why` 保留**为设计选择（PRD 已删「指导性非强制 / 说明为何相关」整段，D20）；**不做跟踪 / 指派 / Deadline** 的结论不变，理由由「PRD §3.6 明确 MVP 不含」改标为「**PRD 未要求**」。
- ~~Python 侧**不落库、不查 ERL 表**：输出交 Java 落库~~ → **2026-09-19 整条反转**（v4.59，裁决 R1 / §0.33-X1）：**产物由 Python 自己落库**（`ai_erl_gap_analysis` / `ai_erl_gap_analysis_item` 两张表归它独占读写，§5.7 / §5.8），Java 改为**调接口取结果**。Python 因此**有了 domain 层**（两个 ORM + 一表一仓储）—— 这也推翻了 `CIOaas-python/source/erl/__init__.py` 原先「本域不落 ERL 业务表、无 domain 层」的自述。<br>Python 仍**不做公司 ACL**（Java 调用前已校验）、仍**不查 Java 那边的 ERL 业务表**（评估 / 维度配置 / 题库 / 附件都属 Java）。⚠️ **2026-09-18 起「全部输入由 Java 传入」这半句也不再成立**（v4.57，§0.31-Z6）：附件**摘要**由 Python 自己按 `fileId` 批量读 `ai_rag_entry.summary` 补齐 —— 读的是 rag 自己的表，Java 送的只有 `fileId` 与 `fileName`。
- Prompt **合并为一份** `source/ai/prompts/erl/erl_gap_analysis.md`（**v4.4**：原 `erl_gap_analysis_founder.md` 与 `erl_gap_analysis_gsv.md` 两份作废，D3），带 `# version: x.x`，变更须附回归测试（`CIOaas-python/standards/coding.md` §15）。**当前 `version: 1.5`**（**2026-09-20 升 1.5**：新增只读入参 `analyzed_context_json`，并要求 `summary` 覆盖「本轮分析 + 此前已分析」两部分之和，§0.35-G9。1.4 于 2026-09-18：加入 attachments 输入段、`evidenceMissing` 新口径、摘要使用三规则、actions 反套话约束、维度级 `narrative`、以及每维 `gaps` 1–5 条（severity 降序）/ `actions` 1–3 条的数量收紧）。
- `severity` 值域固定 `HIGH` / `MEDIUM` / `LOW`，在 prompt 中约束并在 Java 侧校验，非法值降级为 `MEDIUM`。

> ⚠️ **为什么不把 `dimension_code` 送进 LLM（**2026-09-08 新增**）**：若入参 / 出参用 code 作维度标识，就要求模型**逐字复现** `OPS4K7M` 这类串。模型对无语义串的复述本就不可靠（转位 / 少一位），而 §9「LLM 返回结构不合法」的兜底是「缺失维度该维 items 为空」—— 而 items 为空的渲染态恰好是**绿点 + `No Gap`**。两者一叠加：一次字符级幻觉 = 该维全部 gap 与 action 被丢弃 = 页面显示「无差距」，GSV 还能照常 Share 给 Founder，**全程无日志无告警**。故：
> - **入参用 `index`（1..N）+ `name` / `abbr`**，`dimension_code` **只在服务端流转**；Java 侧按下发顺序把出参的 `index` 映射回 code。
> - 出参的 `index` 越界 / 重复 / 缺失 → **打 ERROR 日志（带 companyId / period / 缺的是哪几维）+ 保留旧内容**，**不得降级成 `hasGap = false`**。
> - 这同时暴露了 §9 那个分支本身的缺陷：**「维度缺失」与「该维确实无 gap」被压成了同一个渲染态**，需分开（前者走「分析异常」态，后者才是 `No Gap`）。<br>✅ **2026-09-20（v4.61）关闭**（§0.35-G5 / G6）：产物侧加了「维度行存在 = 已分析」这一位，出参下发 `analyzed`，前端在 `hasGap` 之前先判 `!analyzed` → `Analyzing…`。**`No Gap` 从此只在真的分析过之后出现。** 注意本版关闭的是**产物侧**的那一半（「从未生成」被渲染成绿点）；模型漏回某一维时整份判失败不写库、旧内容原样保留（`_resolve_indexes`），那一半在 v4.59 已经堵住，两者成因不同。

### 6.7 附件解析与摘要（供 Goldie）（~~附件入 Memory File~~ —— **2026-09-18 全节改判**，v4.57，§0.31-Z1 ~ Z5；PRD §3.3 / §4 —— **v4.6：§3.4 的维度级附件已取消**，见 §5.5 / M13）

> ⚠️ **本节标题与链路自 2026-09-18 起整体改判**：ERL 答题附件**不再写入公司 Memory File / 公司知识库**，改为**只解析正文 + 生成摘要**，落在一个**与 chatbot 不相交的独立 space** 里，**唯一消费方是 §6.6 的 Goldie 差距分析**。原「一个 `fileId` 一条公司知识库条目」「本链路与 Goldie 无耦合」两条结论一并作废，逐条依据见 §0.31-Z1 ~ Z5。⚠️ **PRD §四「所有维度附件同步写入公司 Memory File」尚未回写，以本节为准**（§0.31-Z4）。

前端沿用**存量直传通道**，不新建上传接口：

```
⓪ 前端  本地校验 file.size ≤ ERL_MAX_FILE_BYTES(10MB)      ← v4.0，PRD §3.3「单个最大 10MB」
① 前端  storageService.uploadFile(file, 'KNOWLEDGE_BASE')   →  fileId
                （内部 presign → S3 PUT → verify，见 §2.1）
                ⚠ 这个 'KNOWLEDGE_BASE' 是「上传通道」的业务类型（只决定 S3 目录与扩展名白名单），
                  与第 ⑤ 步登记行的 business_type='ERL_ATTACHMENT' 是两套不同的取值，前者本轮不动
② 前端  POST /erl/assessment/draft   { companyId, period, portal, dimension, ... }   ← v4.4：维度在请求体顶层（R1）
          双端一律题级     answers[].attachments[{fileId}]        ← v4.6：dimensionAttachments 入参已删除
                                                                 ← 2026-09-09：fileName / fileSize 入参删除
③ Java  按 file_id 查 files，复核 files.length ≤ 10MB → 落 erl_answer_attachment（ingest_status = PENDING）
                （2026-09-09：不再落 file_name / file_size 快照，也不再信入参自报的大小）
                （2026-09-18：该列语义改为「摘要生成状态」，列名沿用，§0.31-Z5）
④ Java  异步 POST /api/ai/erl/attachments/summarize  { companyId, fileIds[] }
                （2026-09-18 由 /attachments/ingest 改名，裁决 R9；端类型 Python 自己从登录身份推，Java 刻意不传）
⑤ Python  ensure_erl_space（组合键 business_type = ERL_ATTACHMENT：APP 按公司 / ADMIN 按组织，process_type = SUMMARY_ONLY）
              → ingest_kb_file → file_registry 登记（business_type = 'ERL_ATTACHMENT'）
              → 摘要-only 管线：loader 取全文 → 出摘要 → 写 ai_rag_entry.content_text + .summary
                （2026-09-18：不分片、不 embedding、ai_rag_ent_kb_chunk 零行，chunk_count = 0）
⑥ Python  回传 [{fileId, registryId, status}]  →  Java 回写 ingest_status / registry_id
```

| # | 方法 / 路径 | 用途 |
|---|-------------|------|
| 19 | `DELETE /erl/assessment/attachment/{id}` | 草稿态删除附件（已提交则拒绝）。**路径不变**（v4.6：附件只剩题级，鉴权改经「附件 → 作答 → 评估」回溯所属评估） |

- **10MB 双侧校验（v4.0）**：前端 `ERL_MAX_FILE_BYTES = 10 * 1024 * 1024`（**不复用 chat 的 20MB 常量**，§2.1），超限文件不发起上传并提示 `File exceeds the 10 MB limit.`；服务端在第③步**按 `files.length`** 复核（**2026-09-09 换源**：原先复核的是入参自报的 `fileSize`，该入参已删除），超限 `BadRequestException`；`file_id` 查不到、或 `files.length <= 0`（未 verify / legacy 未回填）同样报业务错误（~~400~~，2026-09-09 订正，§4.3）—— 前端可绕过，服务端是底线。
- **为什么不直接调 `POST /api/ai/file-registry/records`**：该接口是低层入口，只建登记行、**不建 rag 条目**（§2.1）—— 没有 `ai_rag_entry` 就既没有 `content_text` 也没有 `summary`，Goldie 拿不到任何内容。**2026-09-18 改判后这条理由反而更硬**：新链路连向量化都不做了，`ai_rag_entry` 是附件内容的**唯一落点**。
- **为什么隔离必须换 space、而不是只换 `business_type`**（**2026-09-18 定档**，v4.57，§0.31-Z2）：chatbot 的检索范围由 **space 组合键**圈定（`find_chat_space_id` / `find_app_space_ids`），chunk 层的 where 里**没有 `business_type`** —— 只改 `business_type` 而不换 space，**chatbot 照样检索得到**。所以组合键里的 `business_type` 换成 `ERL_ATTACHMENT`，uuid5 派生出全新关联行与全新 space，**检索侧一行过滤都不用加**。而 Memory 面板（`list_kb_entry_scopes`）与知识库面板（`_kb_documents_query`）确实按 `business_type = 'KNOWLEDGE_BASE'` 过滤，换了取值即自动排除。<br>`end_type` 口径不变：**后端从登录身份推**（Redis `company_id` 非空 → `APP`，否则 `ADMIN`），**Java 调 Python 时刻意不传** —— 防调用方自报端类型把文件写进另一端的空间。
- **摘要生成失败不阻断评估提交**（原「入库失败不阻断」，2026-09-18 换语义）：`ingest_status = FAILED`（列名沿用、语义为摘要状态，§0.31-Z5），前端在附件旁给重试入口。**解析抽不出内容同样判 `FAILED`，不静默成功**（§9）。
- ❌ **原「本链路与 Goldie 无耦合」整条作废**（v4.0 立、v4.4 去条件语，**2026-09-18 作废**）—— 原文是：「PRD §4『所有**题目**附件同步写入公司 Memory File』是独立的全局约束（§1.3），链路本身与粒度无关，一个 `fileId` 一条知识库条目」。**2026-09-18 改判**（v4.57，§0.31-Z4）：本链路与 Goldie **由「无耦合」变为直接耦合** —— 它的产物（`summary`）正是 §6.6 每题 `attachments[].summary` 的来源，缺了它 Goldie 那一段永远是空摘要。附件**不再产生公司知识库条目**，因此**不出现在** chatbot 检索、Memory 面板与知识库面板里。⚠️ PRD §四那一句尚未回写，两边口径暂不一致，**以本节为准**。
- **附件归属的回溯路径（v4.6）**：`erl_answer_attachment` 只有 `erl_assessment_answer_id` 一条外链 —— 附件 → 作答 → 评估 → 该评估自带的 `company / period / portal / dimension`。表上**没有** `assessment_id`、也**没有** `dimension`（§5.5），任何「按维度 / 按提交取附件」都先取作答再按 `erl_assessment_answer_id` 批量查，不再有第二条捷径。
- **改答导致 level 回收时，被删 level 上的附件一并删除**（§6.3）；**接口 28 `Reset` 时本次草稿的全部附件一并删除**（v4.4，D8）。两种情况下**都不回删已生成的 `ai_rag_entry` 条目**（~~知识库条目~~ —— 2026-09-18 起它落在 ERL 专属 space、不是公司知识库，§0.31-Z1），PRD 未要求联动清理（记入 §7.10 边界）。⚠️ **改判后这条的代价反而更小**：这些条目既不进 chatbot 检索、也不进 Memory 面板与知识库面板，**残留在库里不会被任何用户看到**，唯一影响是管理端 devSupport 的召回测试页不传 `spaceIds` 时会扫到该 space（属管理端工具、非产品链路，已知并接受）。

### 6.8 组合层 ERL 总表（F2，PRD §3.7）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 20 | `GET /erl/portfolio` | F2 Tab | 可选 `period`（**v4.4：缺省为 closed month 所在季度**，R3；~~**v4.19：F2 前端一律显式传「当前自然季度」**~~ → **v4.33 撤回，F2 不发 `period`、走服务端逐公司缺省**，§0.23-P1）、`portfolioId`、`sortBy`、`sortOrder`、`stage`、`minScore`、`maxScore`（**v4.19：这五个排序筛选入参保留不删，但 F2 恒不下发** —— 界面已撤下排序与筛选，§0.23-P2）、`dimension` | **（v4.4 改）** `dimensionColumns[{ code, abbr, sortOrder }]`、`companies[{ companyId, name, overallScore, dimensionScores[{ code, abbr, score }], stage, era, period, detailUrl }]` |

- **`detailUrl`（v3.5 改）**：`View` 列的跳转目标 —— 按 2026-08-28 裁决指向 **A4 全维 Score Details 页**。后端下发 `/exitReadiness/scoreDetails?companyId={id}&period={period}`，**不带维度参数**（v3.2 的「维度详情页 + 默认 FRL」作废，§0.7-3）；带该行取数所用期次；无评估的公司仍下发（进页面看空态）。
- 只返回当前登录用户**有权访问的公司集**（§4.3）。
- **维度列动态化（v4.4，D1）**：~~出参硬编码五列 `frl, prl, berl, rrl, trl`~~ → **作废**，改为 `dimensionScores[{ code, abbr, score }]`；表格列头取根节点 `dimensionColumns[]`（按 `sort_order`），前端**不得**再依赖静态 `DIMENSIONS` 映射渲染列。⚠️ 跨组织同屏时各公司的维度集合可能不同 —— `dimensionColumns[]` 取**当前登录用户所属组织当前 `status = 'Active'` 的维度集合**的维度作为列集合，某公司缺该维度时 `score = null`，前端显示 `—`。
- ~~每家取其**最新已提交期次**的 `is_latest` GSV 评估~~ → **v4.4 作废**（R3）：不传 `period` 时按**该公司 closed month 所在季度**取该期次各维度的 GSV **最新一条 `SUBMITTED`**（**2026-09-08**：原 `is_latest` 已删，改按 `submitted_at DESC, id DESC`），**该季度无提交即整行空态（`overallScore = null`，各维 `—`），不回退到更早期次**；closed month 取不到同样空态 + WARN 日志。无评估的公司仍列出。
- ~~**⚠️ v4.19：F2 不走上面这条缺省**~~ → **v4.33 撤回：F2 现在正是走这条缺省的**（§0.23-P1）。以下整段留作历史（当初钉死当前季度的理由与代价仍值得一读）—— 前端**固定传 `period = 当前自然季度`**（`YYYYQn`，**按 UTC 算**，与填报页期次下拉的兜底项同口径），**整张表同一期次**，服务端 `resolvePeriod(companyId, requestedPeriod)` 收到非空入参即原样采用（只 `trim()`，无格式校验、无归一化）。理由：组合层总表的价值在**横向可比**，而 closed month 逐家推导会让同屏各行落在不同季度，「谁比谁高」失去意义。**该季度无提交的公司整行仍是空态、仍不回退**，`detailUrl` 照常下发。接口 20 的**服务端缺省逻辑保持不变**，供其它调用方使用。
- **v4.0**：各维度列的值是 **level 分（0–9 整数）**；`overallScore` 是**该公司当前 `status = 'Active'` 维度集合上的加权和**（**2026-09-16 改回按权重加权**，§7.1）—— `Σ(各维度分 × 该维权重)`，该期次未提交的维度按 `0` 计入、其余维度的权重**不做归一化**，结果一位小数。⚠️ **跨组织同屏时维度集合可能不同** —— F2 只列当前用户有权访问的公司，正常场景同属一个组织；若出现跨组织，综合分**各按各自组织的维度集合与权重算**，不做任何跨公司归一化，那会改变每家公司自己的分数。
- **排序与筛选在服务端做**（~~PRD §3.7「支持按分数、Stage、维度进行排序与筛选」~~ → **v4.4 改标依据**：**本设计（PRD 2026-09-03 已删除该条依据）**，D15 —— 功能保留，只是依据来源变更）：`sortBy` 白名单**动态化**（⚠️ **2026-09-08**：白名单与请求值一律用 **`dimensionCode`**，而 F2 列头显示的是 **`dimensionAbbr`** —— 二者过去恒相等，`code` 改为 `{前缀}{随机}` 后**完全不同**；点列头排序必须取 `dimensionColumns[].dimensionCode`，**不得用列头文案**，否则稳定报业务错误（~~400~~，2026-09-09 订正，§4.3））为 `{name, overallScore, stage} ∪ {当前配置版本各维度的 code}`（**v4.4：原硬编码 `FRL/PRL/BERL/RRL/TRL` 作废**），非白名单值 `BadRequestException`；筛选支持 Stage 精确值与分数区间。**⚠️ v4.19：本段描述的全部能力保留在服务端，但 F2 界面上已看不到它们**（§0.23-P2）—— 顶部三个筛选控件与**全部列头排序器**都按原型撤下，`sortBy` / `sortOrder` / `stage` / `minScore` / `maxScore` 由 F2 恒不下发；前端那份 `sortBy` 白名单函数也随之删除（服务端白名单校验照旧，供其它调用方用）。
- **必须批量聚合**：一次查出全部公司的答案并在内存归组，禁止按公司循环查询（N+1）。**v4.4**：维度级提交后每家每期次有 N 行 `erl_assessment`（每维一行），聚合时按 `(company_id, dimension)` 归组后按 `submitted_at DESC, id DESC` 取首条（**2026-09-08**），仍是一次查询。

---

## 7. 计算口径与状态流转

### 7.1 分数（PRD §3.1 / §3.3 / §3.5 —— **v4.0 全节重写**；**v4.4 改权重来源与维度集合口径**；**2026-09-16 综合分改回按权重加权**）

| 口径 | 规则 | 状态 |
|------|------|:---:|
| 单题 | 只有 **Yes / No** 两个取值，**本身不折算成分数**（v4.0：1–9 单题分已删除） | 已定档（PRD §3.3 / §3.4） |
| **维度分（Founder / GSV 同口径，v4.0 换底 · 2026-09-15 再换底）** | **该维度最后一个「整级全部 Yes」通关的 level**，取值 **0–9 整数**（**v4.37**）：<br>· 某 level 内**出现任一 No** → 维度分 = **踩 No 那一级在该维有题 level 升序列表里的前一个 level**（题库只配 level 1/2/7/9 时：L9 内有 No → **`7`**，L7 内有 No → **`2`**）<br>· 该维**第一个有题 level** 内即出现 No（= 一级都没通关） → **`0`**<br>· ~~某 level 内出现任一 No → 维度分 = 该 level − 1（PRD §3.3「分数就是此回答为 No 的 Level 减一」）~~ → **v4.37 作废**：**只有 level 连续时新旧两者才相等**，稀疏题库下一律按上两条；PRD §3.3 原文待回写（§0.9-④ M1）<br>· **全部有题 level 均为 Yes → 该维最大有题 level**（题库配满九级时即 `9`，PRD `a6b0906`；**不是固定 9**，§7.2-①）<br>· 该维在该题集版本内 **0 题** → `null`（不按 0 计，§0.9-20）<br>⚠️ **取值离散**：维度分此后**只可能落在「该维配置过的 level」或 `0`** 上（只配 1/2/7/9 ⇒ 只会是 0 / 1 / 2 / 7 / 9），**综合分水位随配置稀疏度下移**<br>⚠️ **不追溯**：`erl_assessment.level_score` 是提交时冻结的快照，本次换底**只影响此后的提交**，存量已提交的稀疏维度继续带旧分（偏高），是否回刷另行裁决 | **2026-09-15 需求方定档（v4.37 换底）**（此前为 PRD §3.1 / §3.3 的「No 的 level 减一」） |
| **综合分（v4.0 换底 · v4.4 换权重来源 · 2026-09-15 改等权 · 2026-09-16 改回加权）** | **Σ(各维度分 × 该维权重)**，保留 1 位小数，以 `X/9` 展示（需求方 2026-09-16）。权重取 `erl_dimension_config` 中该组织 `Active` 行的当前 `weight`（百分比数值，合计 100）。<br>**这是加权和，不是平均 —— 没有「分母 = 维度个数」这回事**：权重本身合计 100%，Σ 出来就已经落在 0–9 的量纲上。需求方算例：FRL 2 分（20%）、PRL 4 分（20%）、其余维度未填 ⇒ `2×0.2 + 4×0.2 = 1.2`，展示取整为 `1/9`。<br>**未填写的维度按 `0` 计入，其余维度的权重不做归一化** —— 上例里已填的两维权重合计只有 40%，分数就只能顶到 40% 的天花板。没做的评估就是没分，会把综合分拉低。这条与 2026-09-15 等权版的「未填按 0」口径一致，与 v4.4 的「剔除该维、其余权重按比例归一化」（§0.9-20）仍然**相反**，后者维持作废。<br>~~**Σ(各维度分) ÷ 维度个数**，综合分不再读 `weight`~~ → **2026-09-16 作废**：2026-09-15 那版等权口径只活了一天，权重重新参与综合分；接口 24 的「合计必须 = 100」校验一直保留未动。<br>**维度集合**：仍取当前 **`status = 'Active'`** 的维度集合（`Inactive` 行不参与、权重也不计入），**个数不固定、不假设五维**（§0.10-D1）。维度停用后，它在历史期次的已提交分数随之退出计算。<br>**百分比换算的除数取「权重表里全部维度的权重合计」而不是写死的 `100`** —— 正常配置下两者等价，但 §9 的等权降级是 `100 ÷ 维度数` 保留 4 位小数（3 维时合计 `99.9999`），写死 100 会让降级路径上的满分算成 `8.9999`。<br>**唯一的空态**：该公司该期次**一维都没填** ⇒ 综合分 `null`（前端灰底 `—`），**不按 `0.0` 算**。⚠️ 这条必须留着 —— 否则「零提交」与「填了、level 1 就没过」的合法 `0` 分在界面上分不出来（见本节末段 `0` vs `null`） | **2026-09-16 需求方定档**（此前为 2026-09-15 的等权口径；再往前是 PRD §3.1 / §3.8 + v4.4 §0.10-R2 / D1 的归一化加权口径） |
| Perception Gap | `Founder 维度分 − GSV 维度分`（两个整数相减，结果为整数）；`> 0` 显示 `Positive`，`< 0` 显示 `Negative`，取绝对值展示。**v4.0：仅管理端展示** | 公式已确认（PRD §3.5）；可见性见 §4.2 |
| Era / Stage | 见 §7.3（**v4.0 补 `score = 0` 的取值**） | 已确认 2026-08-26 + v4.0 补边界 |
| ~~每维状态摘要~~ | ❌ **v4.0 删除**：PRD 2026-09-02 删去该展示项（§0.9-10） | — |
| ~~推导分 `derived_score`~~ / ~~手动分 `manual_score`~~ | ❌ **v4.0 删除**：PRD 2026-09-02 删去手动分与软确认要求（§0.9-3） | — |

**计算示例**（供实现自测，与 §11 验证项对应）：

```
某维度题库（level : 题数）  1:3  2:4  3:2  4:5  5:3 ...
作答          level 1 → Yes Yes Yes          → 全 Yes，解锁 level 2
              level 2 → Yes Yes Yes Yes      → 全 Yes，解锁 level 3
              level 3 → Yes No               → 出现 No，终止
维度分        = 最后一个整级通关的 level = 2   （terminated_level = 3, level_score = 2）
                                      // v4.37：取上一个 CLEARED 的 level（此例 level 连续，与旧口径 3 − 1 同值）
已答题数      = 3 + 4 + 2 = 9        （level 3 的 2 题都要答完才算答满该 level）
level 4/5 的题 从未解锁 → 不下发、不落答案行

综合分（2026-09-16 起 = Σ(维度分 × 权重)，未填按 0、不归一化；①②④⑤ 设该组织配了
        5 个维度 FRL / PRL / BERL / RRL / TRL，权重各 20%）

① **只填了 2 维**（需求方 2026-09-16 给的算例）：FRL = 2、PRL = 4，其余三维未填
              = 2×0.2 + 4×0.2 + 0 + 0 + 0 = 1.2 → 展示 1/9（Stage 1 · Founder Era）
                ⚠️ 不是 (2+4)/2 = 3.0 —— 未填的三维不从权重里剔除，天花板只有 40%

② 五维全填，维度分 2 / 5 / 7 / 4 / 1（等权 20%）
              = (2+5+7+4+1) × 0.2 = 3.8 → 展示 4/9（Founder Era）

③ 同一份分数、权重改为 50 / 20 / 10 / 10 / 10
              = 2×0.5 + 5×0.2 + 7×0.1 + 4×0.1 + 1×0.1 = 3.2 → 展示 3/9
                （权重一改，同一份历史数据的综合分与 Stage 立刻跟着变，§7.11-W1 已裁决接受漂移）

④ 只填 1 维且得 0 分：= 0×0.2 = 0.0 → 展示 0/9，红底 + `Not yet Stage 1`
⑤ 一维都没填：= null（**不是 0.0**）→ 灰底 `—`，Stage / Era 一并空
```

> **示例只是示例，维度数不固定**：上式取五维仅因原型如此，**实现不得写死 5**（§0.10-D1）。
> 真正的算法是「遍历当前 `status = 'Active'` 的全部维度，Σ(维度分，未填按 0) × 该维权重，再除以权重合计」——
> 维度个数、代码、权重、排序全部来自 `erl_dimension_config`（`organization_id` + `status='Active'`，按 `sort_order`；**2026-09-08**：原 `erl_company_period_config → erl_dimension_config_item` 两张表已删，§7.11），
> 而**不是**枚举 `ErlDimensionEnum` 或前端 `constants.ts` 的静态映射（两者均已删除）。
> **唯一实现**：`ErlScoreCalculator#overallWeighted(levelScores, weights)`（Java），权重一律经 `ErlDimensionConfigService#weightsOf` 取（脏数据在那里已等权降级，§9）；前端不再自算（原 `weightedOverallScore` 已删，改回加权后也不要加回来 —— 权重表由后端按被查看公司所属组织现取）。
> ~~`null` 归一化的分母是「剩余维度的权重之和」~~ → **2026-09-15 作废、2026-09-16 维持作废**：未填维度按 0 计入，权重照样占在除数上。

**展示口径（v4.0 重述）**：

- **管理端**：ERL Card 与维度详情页**并列展示 Founder 分与 GSV 分 + Perception Gap**；雷达图四条序列。
- **公司端**：**只展示 Founder 侧**的维度分 / 综合分 / Stage（PRD §3.5「创始人只能查看自己的分数」）；**不展示** GSV 分、Perception Gap、雷达图、基准（§4.2 / §4.3）。
- 两端的维度分**同口径**（都是 level 分），Perception Gap 是两个同口径整数之差，可解释性无问题。
- 任一侧未提交时的降级见 §9。

> **§13-Q3b 已彻底消失**（v4.0）：该问题原是「GSV 手动 / Founder 推导，口径不对称怎么办」，v3.6 记为「由 PRD 选定双端手动而关闭」。v4.0 手动分整体删除后，**两端本就只有一种口径**，该问题连讨论前提都没有了。
>
> **`0` 是合法分数（v4.0 必读）**：原设计的分数域是 1–9，`null` 表示无数据；现在 **`0` 表示「level 1 就没通过」，`null` 表示「该维无题」**，两者语义不同、展示不同（`0/9` vs `—`）。全链路的空值判断**不得用 `!score` 这类真值判断**（会把 0 当成缺数据），必须显式判 `null` —— 这是本次换底最容易踩的坑，代码审查专项检查。

### 7.1.1 已解锁范围 ≠ 全部题（**v4.0 重写**，易错点 —— **v4.4：`Completion` 列已删，本节降级为实现说明**）

> **v4.4 定位变更（§0.10-D12 / D16）**：~~本节的分母口径直接支撑 Assessment History 的 `Completion` 列~~ →
> **v4.4 作废**：PRD 2026-09-04（`8f2fcc0`）已把 `Completion` 从「列表最少字段」中移除，**该列删除**。
> 但下表的三个数在计分、页头文案、Goldie 输入组装里仍然要分清，**论证整体保留为实现说明**，只是不再有对应的列。

逐级解锁下，**一次评估只会作答「已解锁 level」的题**，后续 level 的题从未出现在用户面前。三个数必须分清：

| 概念 | 口径 | 举例（某维度 5 个 level，题数 3/4/2/5/3 = 17 题；止步 level 3） |
|------|------|------|
| **`answeredCount`（已答）** | 已解锁 level 的题数（= 答案行数） | `3 + 4 + 2 = 9` |
| **`totalCount`（题数）** | 该题集版本该维**全部**题数 | `17` |
| **维度分** | 最后一个**整级通关**的 level（v4.37） | `2`（止于 level 3，上一个整级通关的是 level 2；⚠️ **该例 level 连续，新旧口径同值**） |

- **`answeredCount == totalCount` 不再是提交条件**（v3.x 的校验作废）—— 只有该维九级全 Yes 才会相等。~~提交条件改为「五维全部到达终止态」~~ → **v4.4 作废**（§0.10-R1）：提交粒度已是维度级，提交条件为「**本维度到达终止态**」（§6.3 前置校验 2 / §7.2-③）。
- ~~**`Completion` 列显示 `answeredCount / totalCount`**（如 `9/17`），并以次级文字标注 `stopped at Level 3`（§0.9-17 定档）~~ → **v4.4 作废**（§0.10-D12 / D16）：**`Completion` 列删除**。原挂在该列上的两条次级标注**改挂到分数列下方**（Assessment History 的分数列 = 该维 Overall Score `{level}/9` + Stage 徽章，其下以次级文字显示 **`v{n}` 题集版本号**与 **`stopped at L{t}`**），可解释性不丢。PRD §3.9 的 `45/45` 示例是「全通关」特例，本就不是常态。
- **`answeredCount` / `totalCount` 降为页头用途（v4.4）**：接口 7 / 8 仍返回这两个字段，但**只用于详情页与维度页页头的题数文案**，不再驱动任何列表列。
- **维度页页头的「17 questions」是题数，不是已答数** —— 两个数同时展示时必须区分措辞（`17 questions · 9 answered`）。
- **`null` 与 `0` 的区分见 §7.1 末尾的加粗提醒** —— 该维 0 题 → 维度分 `null`、不进综合分；level 1 有 No → 维度分 `0`、照常进综合分。

### 7.1.2 展示期次的确定（`period` 缺省口径）（**v4.4 新增**，§0.10-R3）

所有「`period` 可选」的读接口，在调用方不传 `period` 时用什么期次渲染，此前一直是隐式的。**v4.4 定档**：

| 项 | 取值 |
|------|------|
| **缺省期次** | ~~该公司**最新已提交**的期次~~ → **v4.4 作废**（§0.10-R3）：**该公司 closed month 所在的季度** |
| **closed month 从哪来** | 沿用 **Financial Intelligence 域既有口径**：按公司配置的 **Manual / Automatic** 两种方式推导，数据来自 **Financial Entry 的 actuals**。**ERL 复用 FI 既有服务，自己不算、不复制一份规则**（§3 架构 / §10 文件清单） |
| **季度换算** | closed month → 所属自然季度，形如 `2026Q2`（`2026-04` ~ `2026-06` → `2026Q2`） |
| **该季度两端均无提交** | **空态**（§9 的空态文案），**明确不回退到更早期次** |
| **closed month 取不到**（公司无任何 actuals、FI 侧抛异常、或 closed month 格式不可解析） | ~~**同样空态**，**同样不回退**~~ → **v4.33（2026-09-15 裁决）改为回退​**当前自然季度**（`YYYYQn`，**按 UTC 算** —— 与 `ErlAssessmentServiceImpl.currentPeriod()` 同口径）**，WARN 日志（`companyId` + 原因）保留。⚠️ **例外**：`companyId` 为空时仍返回 `null`（连公司都没有，给季度只是凭空造上下文；五个调用方都先经 `ErlAccessService#resolveCompanyId`，拿不到即抛，该分支只是防御） |
| **显式传 `period`** | 一律以入参为准，本节缺省逻辑不介入 |
| ~~**F2 组合层总表的例外**~~（**v4.19 新增** → **v4.33 撤回**，§0.23-P1） | ⚠️ **本行已作废：接口 20 现在照常走本节缺省**（前端不发 `period`）。原文如下 —— **接口 20 不走本节缺省** —— F2 前端**固定传 `period = 当前自然季度`**（`YYYYQn`，浏览器本地时区），整张表同一期次，走的正是上一行「显式传 `period`」这一支。本节缺省口径对**接口 1 / 17 / 22 与任何不传 `period` 的调用方**仍然有效 |

- **⚠️ 必须改掉的既有行为**：现 §9 的降级逻辑会在当前期次无数据时**悄悄显示上一季数据**。这与本条裁决直接冲突 ——
  **v4.4 起一律不做期次回退**：宁可空态，也不能让用户在没有标注的情况下把上一季的分数当成本季的分数。
- **⚠️ v4.33（2026-09-15）划清的两步，别混为一谈**：**①「期次定不下来」** —— closed month 取不到，本版起**回退当前自然季度**；**②「期次定下来但该季没数据」** —— 仍是**空态、绝不取更早期次反填**，上一条的禁令**原样有效**。本次放开的只有 ①。
- **影响接口**：**接口 1**（ERL Card / overview）、**接口 17**（差距分析）、**接口 20**（F2 组合层总表，**v4.33 归队** —— ~~v4.19 曾由前端固定传当前自然季度而不走缺省~~，该例外已撤回，§0.23-P1）、**接口 22**（A4 全维 Score Details），
  以及其余任何 `period` 可选的读接口 —— 缺省口径统一走本节，**不得各接口各写一套**（收在一个 `ErlPeriodResolver` 里，§10.1）。
- **这是 ERL 域对 FI 域的新增跨域依赖**：原设计对 FI **零依赖**，v4.4 起 ERL 读侧依赖 FI 的 closed month 服务。
  依赖方向为**单向只读**（ERL → FI），不反向、不写 FI 数据；FI 侧不可用时按「closed month 取不到」处理（空态 + WARN），**不阻断整页**。
- **维度配置版本的取用与本节一致**：先定期次（期次只决定取哪批评估数据）；**维度集合与期次无关，一律读当前 `status = 'Active'` 的配置**（**2026-09-08**：`erl_company_period_config` 已删表，§7.11）；期次都定不下来时不渲染任何维度。

### 7.2 逐级解锁计分模型（**v4.0 全节重写**，PRD §3.3 已定档 —— **v4.4：提交粒度改为维度级**）

PRD §3.3 原文（`621e857` + `a6b0906`）：

> 全部问题包含 Era 和 level，为 **Yes/No + 固定顺序必答**模式（在 ERL configuration 中配置的顺序）；五个维度的所有问题按照 Era 和等级依次显示。
> 例如用户回答完了 Founder Era-1 的问题，且答案全部为 yes，**该 level 折叠并显示 Check**，再显示下一 level 的问题，**直到有 No 回答（或全部答完），就不再显示下一 Level，激活提交按钮**，分数就是此回答为 No 的 Level 减一；**若 9 个层级都是 yes 回答，则最终得分为 9**。

> ⚠️ **上文末句「分数就是此回答为 No 的 Level 减一」已由需求方 2026-09-15 裁决取代（v4.37）**：维度分改取「**最后一个整级全部 Yes 通关的 level**」，稀疏题库下与「No 的 Level 减一」不等（§7.1 / §7.2-① 口径 1）。**PRD 原文一字未改、照录于此**，回写建议见 §0.9-④ M1 / §0.10-④ M1；「若 9 个层级都是 yes 回答，则最终得分为 9」那半句**仍然成立**（且早经 v4.0 补全为「全通关 = 该维最大有题 level」）。

**① 状态机（~~每个维度各一份~~ → **v4.4**：**一次提交就是一个维度**，状态机与评估记录一一对应 → §13-Q19 **已关闭**）**

> **v4.4（§0.10-R1）**：提交单元由「某公司某期次某端的**整卷（含五维）**」改为「某公司某期次某端的**单个维度**」。
> 于是 ~~「一条 `erl_assessment` 挂五行 `erl_assessment_dimension`，每行一份状态机」~~ → **v4.4 作废**：
> `erl_assessment_dimension` **整表删除**，`level_score` / `terminated_level` / `unlocked_level` 三列**上提到 `erl_assessment`**（§5.2），
> 一条评估记录 = 一个维度 = 一份状态机。下文算法**本体一字未改**，只是它现在作用在「一条评估记录」上，而不是「一条记录里的第 k 行维度」上。
> **§13-Q19（逐级解锁是全卷还是按维度）由此关闭，取值「按维度独立」** —— 维度级提交下它是模型的必然结果，不再是设计选择。

> ⚠️ **level 分布是稀疏的，不得假设 1..9 连续**（v4.0 补，依 2026-09-03 原型反解）：实测 PRL 维度只用 level **3 / 6 / 9**（首个可作答的是 L3），RRL 只到 L8。因此状态机遍历的是**该维度实际存在的 level 升序列表**，而不是 1→9 的计数器；否则 PRL 会卡在「L1 无题、既非全 Yes 也非含 No」的死锁上。

```
levels = 该维度在该评估绑定版本内 distinct(era_band) 升序     // 如 PRL → [3, 6, 9]

for L in levels:
    qs = level L 的全部题（按 sort_order）
    │
    ├── qs 中出现第一道 No ──► level L = BLOCKED              // v4.28：扫到即终止，不等本级答满
    │                            维度终止：level_score = 上一个已 CLEARED 的 level（一级都没通关则 0），terminated_level = L
    │                                      // v4.37：不再是 L − 1 —— 稀疏 levels 下两者不等，如 [1,2,7,9] 在 L7 踩 No ⇒ 2
    │                            unlocked_level = L，后续 level 全部 LOCKED，跳出
    │                            该 No 之后的题不再要求作答（不计入 unansweredCount）；
    │                            它之前漏答的题仍计入 ⇒ canSubmit 仍为 false
    │                            ⚠ v4.41：「首个 No 之前的第一道漏答题」正是提交时自动补 No 的落点
    │                            （scorer 顺带出参 firstUnansweredQuestionId，§6.3 接口 5 的 autoAnswerNo）
    │
    ├── 到此全为 Yes、但仍有题未作答 ──► level L = ACTIVE
    │                            维度未终止：level_score = null，unlocked_level = L
    │                            后续 level 全部 LOCKED，跳出
    │
    └── qs 全部已答且全为 Yes ──► level L = CLEARED（前端折叠 + 打勾）
                                   继续下一个 L

循环自然走完（所有存在的 level 全 CLEARED）：
    维度终止：level_score = max(levels)     ← **不是固定 9**
              terminated_level = null
              unlocked_level = max(levels)

levels 为空（该维 0 题）：
    level_score = null，terminated_level = null，unlocked_level = 1
    **视为已终止，但不可提交**（2026-09-07 订正：原文「不拦提交」已作废，见 §6.3 校验 3）
```

**三条反直觉但必须照做的口径**（实现与代码审查专项检查）：

1. **得分 = 最后一个「整级全部 Yes」通关的 level，与踩 No 那一级的编号无关**（**v4.37 换底，需求方 2026-09-15 裁决**）。取**踩 No 那一级在 `levels` 升序列表里的前一个**；一级都没通关即 **`0`**（等价于 `DimensionScore#clearedLevel`）。PRL 只配了 level 3 / 6 / 9：在 L3（它的首个有题 level）答 No → **得 `0` 分**；在 L6 答 No → **得 `3` 分**（不是 5）。<br>~~得分 = 出现 No 的 level − 1，与前面的 level 有没有题无关；PRD §3.3 原文即「分数就是此回答为 No 的 Level 减一」；PRL 在 L3 答 No → 得 2 分，不是 0~~ → **v4.37 作废**（PRD 原文待回写，§0.9-④ M1）。⚠️ **level 连续时新旧同值** —— 本文档中 level 1/2/3 的连续举例因此不受影响。
2. **「全通关」= 该维度最大的有题 level，不是无条件 9 分。** RRL 只到 L8，全 Yes → **8 分**。PRD `a6b0906` 的「若 9 个层级都是 yes 回答，则最终得分为 9」是**题库配满九级时的特例**。
3. **`unlocked_level` 存实际 level 值，不是序号。** PRL 停在 L6 存 `6`（不是「第 2 组」的 2）。前端据此与 `levels[].eraBand` 对齐。

- **「level 内出现 No」即终止，不要求答完该 level 的其余题**吗？—— **不要求**（**v4.28 定档，需求方 2026-09-14**）：按 `sort_order` 扫到**第一道 No** 就终止，该 No 之后的题（本级剩下的 + 其后所有 level）一律不必作答，填报页把它们**禁用**。<br>~~v4.0 原定「要求答完」，理由是 PRD「level 折叠并显示 Check」的前提是答完该 level、且 Goldie 要拿到该 level 内「哪些准则没达成」的完整信息（§6.6）~~ → **作废**：终止语义优先，Goldie 拿到的就是「答到第一个 No 为止」的那批答案。<br>⚠️ 与此同时**那道 No 自己及它之前的题仍可改**（点错 No 必须能改回 Yes）—— 禁用的粒度是**题**，不是整级。改回 Yes 后其后的题重新可答，**终止随之解除**：`canSubmit` 落回 `false`、Submit 变回不可提交（前端为此把「No→Yes」也列为立即落盘的时机）。
- **解锁与终止判定只在服务端做**（`ErlLevelScorer`），前端消费接口 3 / 4（**v4.30 补：草稿期是接口 29**）返回的 `levels[].state` 与 `unlockedLevel`，**不自行推断**（§6.3）。**v4.30：草稿期改由**接口 29 只算不存**地推进（同一份 `ErlLevelScorer`，只是不写库），这条不变量**没有被破除** —— 落盘（接口 4）与提交（接口 5）时服务端仍会按传入答案**重算一遍**。
- **改答的回收规则**见 §6.3：把已答的 Yes 改成 No，会删除该 level 之后的全部答案与附件。

**② 唯一实现，不做策略抽象**

- 计分逻辑收在 **`application/scoring/ErlLevelScorer`** 一个类里（§10.1），对外只有两个方法：`computeDimension(orderedQuestions, answers)` → `{levelScore, terminatedLevel, unlockedLevel}`；`computeOverall(dimensionScores, weights)` → 加权综合分。
  - **v4.4**：`computeOverall` 的 `weights` 入参**由调用方取自 `erl_dimension_config` 当前 `Active` 行**（**2026-09-08**：原「按期次取绑定版本」作废，§7.11），`ErlLevelScorer` 本身不查库、不感知「当前生效版本」；`dimensionScores` 是**变长**集合，方法内不得假设 5 项（§0.10-D1 / R2）。
- ❌ **删除** `ErlScoringStrategy` / `Score1To9Strategy` / `ErlScoringStrategyFactory` / `ErlScoringModeEnum` / `erl_assessment.scoring_mode`（§0.9-1）：PRD 已把格式定档，「保证未来切换不用重构」的要求随之删除，为单一实现留一层策略工厂属违反根 `CLAUDE.md` 的 YAGNI。
- 五处消费者（填报解锁、提交校验、展示计分、组合层、Goldie 输入组装）**一律调该类**，不得内联 level 判定。

**③ 前端渲染**

- 题目顺序**恒按后端返回的 `levels[]` 与 `questions[]` 顺序**，前端不重排、不合并 level。
- `CLEARED` 折叠 + 打勾、`ACTIVE` 展开、`BLOCKED` 展开且标注止步（**v4.28**：首个 No 之后的题禁用，那道 No 及它之前的仍可改）、`LOCKED` 只显示占位行（`Level n · locked`）或整段不渲染（§8.4）。
- 提交按钮绑接口 3 / 4 返回的 `canSubmit`，不自行判断（§6.3）。
  - **`canSubmit` 的判定口径（v4.4，§0.10-R1）**：~~五个维度**全部**到达终止态（BLOCKED 或全 CLEARED）~~ → **v4.4 作废**：
    **只看本次填报的这一个维度是否终止** —— 本维 BLOCKED 或全 CLEARED、且已解锁题全部作答（**v4.28**：首个 No **之后**的题不算在「已解锁题」里），即 `canSubmit = true`；**该维 0 题时恒为 `false`**（2026-09-07 订正：原文把「该维 0 题」也算作可提交，与实现及 §9 的「整页即空态、`Submit` 禁用」相反），
    **与其他维度填没填、填到哪一级完全无关**。这也是 §13-Q23「旧草稿摆脱不掉」被大幅缓解的原因（提交门槛由五维降为单维；配合接口 28 丢弃草稿后正式关闭，§0.10-D8）。

**④ PRD 已定档、V1 必须实现的原「待确认」项**

- 原 §13-Q5-①「切到 Yes/No 后『No 中断』时该维度分数如何计算」→ **PRD 已给出答案**（No 的 level − 1；九级全 Yes 为 9）⇒ **Q5-① 关闭**，V1 直接实现。（⚠️ **v4.37 就地标注**：PRD 给的「No 的 level − 1」已被需求方 2026-09-15 裁决取代为「**最后一个整级通关的 level**」—— **Q5-① 仍然是关闭的**，只是取值换了底；「九级全 Yes 为 9」那半条不变）
- 原 §五 TBD-2 / TBD-3（打分格式最终形态、维度分计算方法）→ **PRD §3.3 / §3.1 已定档**，但 PRD §五 的 TBD 清单**未同步删除** ⇒ 回写 PRD（§0.9-④ M3）。

### 7.3 Era / Stage 分段规则（2026-08-26 已确认）

以 **1–3 / 4–6 / 7–9** 分段为准；原型 FRL 6.4 标 `Exit Era` 是**原型错误**，不予沿用。精确边界（分数为 1 位小数，需明确开闭区间）：

| 分数区间 | Era | Stage |
|----------|-----|-------|
| **`score == 0`**（**v4.0 新增**） | **`—`（未达 Stage 1）** | **`0`** |
| `0 < score < 4.0` | **Founder Era** | 1–3 |
| `4.0 ≤ score < 7.0` | **Harvest & Growth** | 4–6 |
| `7.0 ≤ score ≤ 9.0` | **Exit Era** | 7–9 |

**`score == 0` 的取值（v4.0 定档，§0.9-18）**：维度分 `0` 表示「level 1 内就有 No」，即连 Stage 1 的准入准则都未达成 ⇒ **Stage `0`、Era 显示 `—`**，前端渲染为灰色 `Not yet Stage 1` 徽章。**不归入 Founder Era** —— Founder Era 的定义是 Stage 1–3，`0` 不在其中。加权综合分为 `0.0` 时同理。

**Stage 整数值**：`stage = clamp(round(score), 1, 9)`，但 **`score == 0` 时 `stage = 0`**（不 clamp 到 1）。PRD §3.5「当前 Stage（1–9）由综合分数与 Workbook 中的 Era 边界推导」未给出取整规则 → 取整方式待产品确认，见 §13-Q3。Era 判定**只按上表区间**，不经由 Stage 二次转换，避免 6.5 → round 7 → Exit Era 的错判。

> **维度分是整数，综合分是小数**（v4.0）：维度分为 0–9 整数，落在上表时区间判定无边界歧义；**只有加权综合分**会出现 3.9 / 4.0 / 6.9 / 7.0 这类边界值，上表的开闭区间因此仍然必要。

**交叉验证**：该规则套原型的 6 个数值，5 个与原型显示一致（综合 5.3 → Harvest ✓；PRL 5.1 → Harvest ✓；BERL 7.5 → Exit ✓；RRL 4.6 → Harvest ✓；TRL 2.8 → Founder ✓），唯一不一致的就是被判定为 bug 的 FRL 6.4（原型 Exit，本规则 **Harvest & Growth**）。

> 题目的 `era_band`（1–9 整数档位）到 Era 的映射不受影响：band 1–3 → Founder Era、4–6 → Harvest & Growth、7–9 → Exit Era，整数无边界歧义。

> **v4.4 复核**：本节**无任何「五维」硬假设** —— 分段规则只吃一个分数（维度分或综合分），与维度个数、维度集合、权重来源都无关，动态维度（§0.10-D1）与配置版本快照（§0.10-R2）对本节零影响。上文「交叉验证」里的五个维度只是 2026-08 原型的取数样本，非规则的一部分。

### 7.4 ~~状态摘要与软确认阈值~~ → **v4.0 整节删除**

本节原有两块内容，**依据均已被 PRD 2026-09-02 修订移除**，功能一并删除（§0.9-10 / -3）：

| 原内容 | 删除依据 | 连带删除物 |
|--------|----------|-----------|
| **① 每维状态摘要**（`MET` / `PARTIAL` / `GAP` 三值 + gap 阈值 0.5 / 1.5 + 短路匹配顺序） | 三值枚举于 2026-08-28 从 PRD 删去（v3.2 已降级为「设计占位」）；**整条「每维度状态摘要」展示项于 2026-09-02 删去** ⇒ 零依据。且它依赖 Perception Gap，而 gap 在公司端已不可见（§0.9-4），徽章两端语义会不一致 | `ErlDimensionStatusEnum`；接口 1 `dimensions[].status`、接口 2 `header.status`；ERL Card 与 A3 的状态徽章；§8.5 归属表该行；§11 原 66 项 |
| **② 手动分 vs 推导分的软确认阈值**（`abs(manual − derived) > 1.0`） | PRD §3.3 / §3.4 的手动分与软确认要求**于 2026-09-02 同时删除** ⇒ 无手动分即无分歧可确认 | `erl_assessment_dimension` 的 `manual_score` / `derived_score` / `divergence_ack` / `divergence_delta` 四列；接口 4 / 5 的 `dimensionScores` / `divergenceAcks` 入参；提交前置校验 2、3；B1/B2 的手动分输入与软确认弹窗；§11 原 21 / 21b / 63 项 |

> **保留本节标题的原因**：全文有十余处交叉引用 `§7.4`（§6.1 / §6.3 / §7.1 / §8.4 / §9 / §11 / §13-Q3）。直接删掉章节会留下一批指向空处的引用，反而更难核对；保留一节说明「为什么没有了」，比静默消失更利于后续复核。**新的计分口径见 §7.1 与 §7.2。**

### 7.5 差距分析的生成、刷新与分享（**v4.4 改**：E 模块回归 V1 + Share 流转）

> **v4.4 两处依据变更**：
> 1. ~~**E 模块，PRD 已标「待定功能」，本节整体可摘除**（§0.9-12）~~ → **v4.4 作废**（§0.10-D2）：PRD `8324a3f` 已删去 §3.6 标题上的「待定功能」，**Goldie 进 V1**，本节为必做项，全文与之相关的「待定期间隐藏 / 恒 null / 恒空数组 / 需求方确认后才执行」条件语一律删除；**§13-Q22 关闭**。
> 2. ~~本节依据 PRD §3.6「新评估提交后自动刷新」~~ → **v4.4 订正**（§0.10-D19）：PRD 2026-09-04 已删掉「自动刷新分析」这一条。**行为保留**（置脏 + 异步重生成仍是本设计选定的实现手段），**依据改标「本设计」**——「PRD 删掉依据 ≠ 自动删掉功能」（§0.9-②）。

**结论先行：没有定时任务、没有扫描器。** 判断只发生在三个时刻（**2026-09-19 补全为三个触发点**，v4.59 / §0.33）。

```
触发点 A —— 每次评估提交后（主路径）
Founder 或 GSV 提交某一个维度的评估（接口 5，事务提交成功；提交粒度 = 维度级，§0.10-R1）
        |
        +--> 事务提交后（AfterCommitExecutor，事务外）
                 投递异步任务 -> @Async("ioExecutor") regenerate(companyId, period, bearerToken)
                        |   ⚠️ 2026-09-19：原先的「同事务内 UPDATE … SET stale = true」已删除 ——
                        |      产物已在 Python 库里，置脏要跨服务写别人的表；改为读侧现算派生
                        |
                        +-- 1. 取该期次当前 status = 'Active' 的维度集合        空集合 → 返回
                        +-- 2. 取每维两端 SOT（submitted_at DESC, id DESC 首条）
                        +-- 3. 算可分析维度集合（2026-09-20 改判，v4.61 / §0.35-G1）：
                        |        analyzable = { 该维两端都有 SUBMITTED } − { 题集版本 mismatch 的维度 }
                        |        为空 → 记 INFO 返回，两句文案**刻意不同**（成因不同、自愈路径也不同）：
                        |          · 一个维度都没两端交齐 → "no dimension is submitted on both sides yet"
                        |            （对方一交就走触发点 A 自愈）
                        |          · 交齐了但全落在 mismatch 里 → "every dimension has a question set mismatch"
                        |            （要落后一方补交新版问卷才会动，§8）
                        |        ⚠️ 原「S1：全部 Active 维度都两端已提交」与紧随其后那条独立的
                        |           「全维 mismatch 就跳过」已合并进这一步 —— 后者被「集合为空」天然覆盖
                        +-- 4. 逐维算指纹，挑出真正要跑的那几维（2026-09-20 改判，v4.61 / §0.35-G2）：
                        |        toRefresh = { code ∈ analyzable | 产物里该维指纹缺失或 ≠ 现算值 }
                        |        为空 → 记 INFO 返回（已是最新，幂等短路，不白烧 LLM）
                        +-- 5. 组装入参：dimensions[] 只装 toRefresh，
                        |        analyzable − toRefresh 作为只读的 analyzedContext[] 一并下发（§0.35-G9）
                        +-- 6. Python 侧抢 Redis 锁 erl:gapAnalysis:{companyId}:{period}（TTL 600s）
                        |        抢不到 → 回读产物 + generating = true，不重复生成
                        +-- 7. Python 调 LLM（失败重试 2 次、退避 2s/4s）→ 落库
                                 覆盖主行 +（逐个 toRefresh 维度）upsert 维度行 + 换掉该维 item
                                 + shared 复位为 false
                                 ⚠️ 2026-09-20（v4.61 / §0.35-G4）：由「全量替换 item」改为「按维度覆盖」——
                                    没被本轮分析的维度，其维度行与 item 原样保留
                                 LLM / index 校验失败 → 不写库，旧产物原样保留

触发点 B —— 读接口 17（被动自愈）
        Java 现算指纹 ≠ Python 存的指纹（2026-09-20 起**逐维比**，任一可分析维度不等即算）
        → 下发 stale = true（⚠️ 2026-09-20 起前端**不再**为它挂顶部横幅，§0.38-K1；
        并继续展示旧内容），**并顺带投递一次异步 refresh**
        |
        +-- 这是指纹派生方案白捡的能力：即便触发点 A 因 Python 不可用 / 异步线程异常而丢失，
        |   下一次有人打开页面就会自动重新触发。
        |   ⚠️ 2026-09-20 提交前审核改判（§0.35-G11）：~~防抖靠第 6 步的 Redis 锁，不需要额外节流~~ ——
        |      那把锁只做**互斥**（finally 立刻释放），不是节流；而前端本版加了有界轮询，
        |      每一轮都会打一次接口 17 ⇒ 每一轮都可能投一次本触发点。某维永远出不了终态时，
        |      管理端页面开着就是固定间隔的完整重生成循环。故**本触发点加 Redis 冷却键**
        |      erl:gapAnalysis:cooldown:{companyId}:{period}（TTL 60s），拿不到就不投递。
        |      **只管触发点 B** —— A（提交后）与 C（手动）不受限，否则真实提交会被吞掉
        +-- ⚠️ **只在管理端投递**：refresh 会让 Python 复位 shared / shared_at / shared_by，
            公司端若也投，创始人打开一次页面就能把自己正在看的那份分析变回「未分享」——
            读接口绝不能产生写副作用。自愈主路径是 A，B 只是安全网

触发点 C —— 管理端手动 Regenerate（接口 18，POST /erl/gapAnalysis/generate）
        跳过第 4 步的指纹相等短路（用户点它多半就是想重试一次失败的生成），
        即 toRefresh = 全部 analyzable；但**仍要过第 3 步**，且第 3 步的两种成因**给两种反馈**：
          · 真的一个维度都没两端交齐 → 400，文案由 "All dimensions must be submitted by both
            sides before generating." 改为 "At least one dimension must be submitted by both
            sides before generating."（2026-09-20 随门槛改判；**Share 的那句不变**，见 S2）
          · 交齐了但全落在 mismatch 里 → **不报错**，记 INFO 后原样返回旧产物（§8 早已定档：
            页面上每维已经是黄点 Question set mismatch，再抛一句「至少要有一个维度两端都已提交」
            会让管理员去找根本不存在的漏交）

管理端点 Share（接口 27，POST /erl/gapAnalysis/share）
        |
        +--> Java 校验门槛（S2）→ 调 Python 置位 shared / shared_at / shared_by
             → 公司端（Founder）自此可见

页面读取（接口 17）
        |
   +----+----------------------+-------------------+
   |                           |                   |
 有产物且指纹相等          有产物但指纹不等        无产物
   |                           |                   |
 直接渲染            渲染旧内容（2026-09-20 起无横幅）  空态 §9
                       + 管理端顺带投递 refresh（触发点 B）
        |
        └── 公司端额外一层：shared = false → 直接空态（§0.10-D3 / §4.2 / §4.3）
```

**「什么时候首次生成」**：~~最后一个维度的最后一端提交时，S1 **首次**成立~~ → **2026-09-20 改判**（v4.61 / §0.35-G1）：**任意一个维度的第二端提交时**，该维进入可分析集合 —— **那一次提交触发的异步任务就会分析这一维**，其余维度照旧等各自凑齐。不需要任何额外的「双方都提交了」检测机制，也不再需要等齐全部维度。

**不触发的情形**（务必写进代码注释，否则会被「优化」掉）：

| 事件 | 是否触发 | 理由 |
|---|---|---|
| 题库发布新版本 | **否** | 分析输入全部取自评估绑定的版本快照，发布后一字未变（§7.9-⑤） |
| 保存草稿 | 否 | 只有 `SUBMITTED` 进 SOT |
| 维度配置改权重 | 否 | 权重不改变作答，指纹不变（它只改综合分展示，与分析内容无关） |
| 新增 / 停用维度 | **否**（2026-09-20 改判） | ~~Active 集合变化会改变指纹~~ → 指纹下沉到维度级后，**别的维度的指纹一个字节都不会变**（§0.35-G2）。新维两端都没提交 ⇒ 不进可分析集合 ⇒ 不生成、也不显示 `Refreshing…`；停用的维度不下发骨架，其维度行留在库里不上屏，重新启用时指纹与当年一致。**这比 v4.59 那套更干净**：那时停用一个维度会让整份产物判 stale、全量重跑一次 |
| 落后一方补交新版问卷（P4 场景） | **是** | 就是一次普通提交，走触发点 A，mismatch 自动消失（§0.32-Y9） |

- ~~**置脏的触发点只有「评估提交」一个**~~ → **2026-09-19 改为三个触发点**（见上图；「置脏」这个动作本身已随 `stale` 列一起消失）。**题库发布新版本仍然不触发** —— 分析的输入（答案 + 备注 + 题干 / level）全部取自评估绑定的版本快照，发布后一字未变（§7.9-⑤）。
- **自动重生成是异步的**：提交接口不等 LLM，RT 不受影响；LLM 失败不回滚提交（§3.2）。
- **失败重试**（**2026-09-19 起在 Python 侧**，v4.59 / §0.33-X6）：LLM 调用失败最多重试 2 次（指数退避 2s / 4s），仍失败则**不写库、旧内容原样保留** —— 此时指纹自然仍不相等，故页面照旧显示 `Refreshing…`、下一次读又会自愈（触发点 B）；管理端也可手动 `POST /erl/gapAnalysis/generate` 兜底。~~保留 `stale = true`~~ 这个说法随列删除失效：现在它是**算出来的**，不需要谁去「保留」。
- **并发去重**（**2026-09-07 改**，原文「已有生成任务在跑时不重复投递」已作废；**2026-09-19 整体下移 Python**，v4.59 / §0.33-X5）：同 `(companyId, period)` 用 Redis 短锁 `erl:gapAnalysis:{companyId}:{period}` 去重，TTL **600 秒** —— 必须 ≥ **单轮**最坏耗时（3 次尝试 × 180 秒读超时 + 退避 2s/4s ≈ 546 秒）；原定的 5 分钟小于单轮耗时，锁会在生成中途过期、让第二个线程拿到同一把锁并发写同一份分析。**抢锁失败不再静默丢弃**：抢不到锁的那一次直接回读产物并标 `generating = true`，而「内容是否落后」由指纹派生 —— 持锁者跑完写入的指纹若仍不等于现算值（LLM 往返期间又有人提交），**下一次读（触发点 B）或下一次提交（触发点 A）会自动再跑一轮**，不需要谁去记「还欠一轮」。**每轮各自抢锁、跑完即释放**，所以 TTL 只需覆盖单轮，不必乘以轮数。<br>⚠️ **2026-09-19：锁、重试、补跑三者都在 Python 进程内**，Java 侧的 Redis 锁与 `callWithRetry` 已删除；`ErlPythonClient` 只负责一次 HTTP 往返（不重试、不落库、不吞异常）。锁的两条实现细节：**释放前先比 token 再删**（Lua 单步，防误删别人的锁）、**Redis 异常保守放行**（拒绝生成会让功能整体不可用，而重复生成只多烧一次 LLM，且落库是「覆盖 + 全量替换」，最终一致）。
- 已有缓存时管理端页面显示 **Regenerate** 按钮 + `generatedAt`；公司端只读，看不到该按钮。
- ~~**一次 LLM 调用同时产出 Founder / GSV 两套口吻**，落两行（`audience` 区分）、两份 prompt~~ → **v4.4 作废**（§0.10-D3）：PRD `8324a3f` 已删去「Founder / GSV 两套口吻」整段，改为 **GSV 团队可见 + 点 Share 分享给 Founder**。因此 **`erl_gap_analysis.audience` 列删除、唯一约束回 `(company_id, period)`、两份 prompt 合并为一份、一次调用只产出一份内容**；§8.4「前端不做措辞转换」与「双 audience 回归测试 / 两端口吻不同」的验收项一并摘除。

**Share 相关的新流转（v4.4 新增，§0.10-D3 / D4）**

| # | 规则 |
|---|------|
| S1 | ⚠️ **2026-09-20（v4.61 / §0.35-G1）整条改判为「至少有一个可分析维度」** —— 可分析维度 = 该维 FOUNDER 与 GSV 都有 `SUBMITTED` **且**非题集版本 mismatch；某一维两端一凑齐就分析这一维，**不必等其余维度**。`allDimensionsSubmitted` 这个判定**保留但只服务 S2**（见下一行）。同时 `stale` 的前置条件由「S1 成立」改为「该维在可分析集合内」—— 下面那条「新增一个两端都没提交的 Active 维度会让页面永久 Refreshing」的隐患**因此彻底消失**，因为指纹已经下沉到维度级、不再有一个横跨全维的值。<br>**原文留档**（已改判，保留以便复核当时的论证）：**生成门槛**：该 `(company, period)` 下**每一个维度**（**2026-09-08**：按当前 `status = 'Active'` 的维度集合，原「该期次绑定的配置版本」作废，§7.11）的 **FOUNDER 与 GSV 两端**都有 `SUBMITTED` 记录时，才生成/刷新分析；未达成时**不调 LLM**。<br>⚠️ **2026-09-19（P3）：S1 同时成了 `stale` 的前置条件**（§0.33-X2）—— ~~未达成时保持 `stale = true`~~ 反了：新增一个两端都没提交的 Active 维度时，它永远进不了任何一次生成，指纹于是**永远**不等；若不加「S1 成立」这个前置条件，页面会**永久**显示 `Refreshing analysis…`。故 **S1 不成立时一律不判 stale**，显示旧内容的正常态。**2026-09-08**：`is_latest` 列已删，「两端都有」改为按 `(company_id, period, portal, dimension_code)` 按 `submitted_at DESC, id DESC` 取首条判定是否存在 |
| S2 | **Share 按钮激活门槛**：**每个 Active 维度两端都已提交 且 无维度题集不一致 且 无 outdated 维度**（第二条 2026-09-19 加入，**第三条 2026-09-20 提交前审核加入**，§0.35-G7）。第三条不可省：维度级增量下「已提交」**不再蕴含「已分析」**，少了它就会出现「最后一维刚交齐 → Share 放行 → 9 秒后在途生成把 `shared` 复位 → 创始人在无人操作下失去访问」。⚠️ **2026-09-20 需求方明确裁决：这一条不跟着 S1 改判，维持原样**（§0.35-G7）—— 分析可以增量，但**分享给创始人的应当是一份完整报告**，半份发过去只会引出「剩下的呢」。这也是 `allDimensionsSubmitted` 在 S1 改判后仍要保留的唯一原因（从「生成 + Share 两用」降为**只服务 S2**）。<br>⚠️ **2026-09-20 提交前审核后修正**：门槛**再加一条「无 outdated 维度」**（复用 `outdatedDimensions`，零新概念）。原门槛只守「提交」，而维度级增量下**提交不再蕴含已分析** —— 最后一维两端交齐的瞬间 `shareable` 就变 true（该维分析还在跑），GSV 点了 Share，约 9 秒后在途生成落库、`overwrite_generated` 无条件复位 `shared` ⇒ **什么都没再交也会掉分享**，G8 记的代价没覆盖这条竞态。另有三种能让「4 维分析过 + 1 维没有」长期停住的成因：异步 regenerate 还在跑 / Python `_resolve_indexes` 反复 502 不落库 / Redis 锁被占直接回 `generating=true`。改造前 Python 是 all-or-nothing、产物要么全有要么全无，现在这是**稳定可持久**的状态，风险等级实质变了。需求方 2026-09-20 确认：「Share 门槛不变」指的是**不放宽到维度级**，补 `analyzed` 属收紧、与「分享给创始人的应当是一份完整报告」同向。<br>未达成置灰；~~底部提示 `Share unlocks once gap analysis is available for all {total} dimensions in {period}.`~~ → **2026-09-20 改为列出还差哪些维度**（取 `dimensions[]` 里 `!bothSubmitted` 的 `dimensionAbbr`）—— 原文案在增量分析下更容易误导：`No Gap` 的维度同样没有 gap analysis 却不挡解锁，`docs/待优化项.md` 早已记过这条 |
| S3 | **公司端可见性**：`shared = false` 时接口 17 对公司端直接返回**空态**（不是「有内容但灰掉」）；`shared = true` 后 Founder 只读可见。<br>⚠️ **2026-09-20（v4.63 / §0.37-J1）改为读侧派生**：公司端的「已分享」= **`shared` 列为真 **且** 当前仍满足 S2 三条门槛**。产物一旦不再满足门槛（某维题集 mismatch / 有新提交还没重跑），创始人手里那份就是依据**已被替换的输入**得出的，立即收回；管理端不受影响。**不能靠「重生成时复位 `shared`」代替** —— 那只在内容真被覆盖时发生，而「某维变 mismatch」不改变任何可分析维度的指纹，根本不会触发重生成 |
| S4 | **重生成 ⇒ 复位**（本版定档的新边界，PRD 与旧设计均未定义）：Share 之后任一端又提交新评估触发重生成时，**`shared` 复位为 `false`**，`shared_at` / `shared_by` 清空（**2026-09-19：执行点从 Java 的置脏事务移到 Python 的「覆盖产物」语句里**，语义未变，§0.33-X4） —— **必须 GSV 重新 Share**，Founder 端在重新分享前回到空态。理由：否则会**静默改写 Founder 已经看过的内容**，且分享这个动作的语义（「我确认过这版内容可以给创始人看」）会被架空。<br>⚠️ **2026-09-20（v4.61 / §0.35-G8）：维持无条件复位，但代价变大** —— 增量化后重生成频率由「一期一次」升到「一期最多 N 次」，「已分享 → 又交一维 → 创始人立刻失去访问 → 管理端再点一次 Share」会更频繁。评估过的折中（**只在已分析维度的内容被覆盖时才复位**，新增维度的首次分析不复位）**需求方未采纳**，登记在此以便日后有人当 bug 排查时能查到原委。<br>⚠️ **本条覆盖不到的一个竞态（2026-09-20 提交前审核发现）**：「Share 之后**什么都没再交**也会掉分享」—— 最后一维两端交齐时分析还在跑，此刻若 Share 放行，几秒后那一轮在途生成落库就会复位 `shared`。**根治在 S2**（门槛加「无 outdated 维度」），不在本条 |
| S5 | **管理端提示**：复位后 Gap 区块显示 **「内容已更新，需重新分享」**（`Share to founder` 按钮恢复可点态），不弹强提醒、不阻断其他操作 |
| S6 | 状态取值域：`shared` 只有 `false`/`true` 两态，**不做「已分享但已过期」的第三态** —— S4 的复位已经表达了这层含义，多一态只会让前端多一个分支（YAGNI） |
| ~~S7~~ | ❌ **2026-09-19 整条作废**（v4.59 / §0.33-X2）：**问题本身消失了** —— `stale` 不再是一个「需要谁去清零」的列，而是每次读现算的派生值。LLM 往返期间又有人提交 ⇒ 产物里存的指纹就是「这份内容依据的那一批」，下一次读现算出来必然不等 ⇒ 自动判 `stale`、自动自愈。<br>**原文留档**（已作废，保留以便复核当时的论证）：**`stale` 何时才敢清零**（**2026-09-07 定档**，此前是无条件清）：一次 LLM 往返最长 3 分钟，期间完全可能又有人提交。落库前重算「双端各维最新已提交记录 id」的指纹，**只有与调 LLM 前一致才清 `stale`**；不一致就写入新内容但保留 `stale = true`，让 UI 如实显示「已落后」，并由上面的补跑或下一次提交收敛。理由：无条件清零叠加「抢锁失败静默返回」，会让并发的第二次提交**永久**不进分析，而前端 `stale = false` / `generating = false` 一切正常、没有任何后续触发点，GSV 点 Share 分享出去的正是一份声称最新、实际漏了一次提交的内容 |
| ~~S8~~ | ❌ **2026-09-19 整条作废**（v4.59 / §0.33-X5）：产物主行的写入方**从 3 个降到 2 个**（重生成落库、Share），且两者都在 **Python 进程内** —— 置脏那个写入方已不存在，于是不再需要跨服务的 `SELECT … FOR UPDATE` 协议，Redis 锁 + 单表短事务足够。（覆盖时仍有一条顺序要求：**UPDATE 主行排在 DELETE items 之前**，靠主行行锁把并发串行化，§0.33-X7。）<br>**原文留档**（已作废，保留以便复核当时的论证）：**主行的三个写入方一律加行锁**（**2026-09-07 定档**）：`erl_gap_analysis` 有三个并发写入方——重生成落库、提交时置脏、Share。三者都经 `SELECT … FOR UPDATE` 取主行后再写，否则会互相回写（例：置脏方读到旧摘要后提交，把重生成刚写入的新摘要连同 `generated_at` / `model` 一起回退，而 item 明细已是新一代 —— 主行与明细来自两代生成、`generated_at` 还会倒退）。**刻意不用乐观锁**：置脏方跑在**用户提交评估的事务**里，乐观锁失败会让整次提交回滚 —— 用户白填一份问卷，代价远大于收益；悲观锁只是让它阻塞几毫秒。这把行锁同时让「指纹重算」与「置脏」互斥，是 S6 能成立的基础，也是本设计**不需要**任何额外的 Redis 待办标记的原因 |

### 7.6 ~~Data Sources & Cadence 的推导~~ → **v4.0 整节删除**

PRD §3.5 的「**Data Sources & Cadence（按维度）**：显示主要与补充证据来源，以及评估频率（季度）」一条**于 2026-09-02 从 PRD 删去**（§0.9-13）。v2.1 原本明确排除该卡片，v3.0 仅因 PRD §5 的明文才把它纳入（§0.2-10）；依据消失 ⇒ 回到不做。

连带删除：接口 2 的 `dataSources` 出参、A3 的 `Data Sources & Cadence` 卡片、前端 `DataSourcesCadenceCard` 组件、§8.5 归属表该行、§11 原第 9 项。

> **题目的 `evidence_source` 列不删** —— 它另有依据：PRD §3.3 / §3.4「每题显示来源标签」，A3 / A4 的逐题行仍要展示（§8.4）。删掉的只是「按维度聚合成 primary / supplementary 两组」这层推导。

### 7.7 评估状态流转（**v4.4 按维度级提交重写**，§0.10-R1）

> **状态流转的作用域（v4.4；**2026-09-08 改列名**）**：下图的每一条流转线都发生在 **`(company_id, period, portal, dimension_code)` 这一个四元组内部**。
> ~~一次流转覆盖某公司某期次某端的整卷（含五维）~~ → **v4.4 作废**（§0.10-R1）：**一次提交就是一个维度**，
> ~~`submission_seq`、`is_latest`、~~ → **2026-09-08：两列均已删除**（§5.2），只剩**唯一草稿约束按四元组分组**；维度之间**互不影响**：FRL 已提交过 3 次、PRL 还停在草稿、TRL 一次没填，都是合法且常见的状态组合。

```
作用域 = (company_id, period, portal, dimension_code)   ← v4.4：每个维度一条独立的流转线
最新一次提交（SOT）= 同四元组内 status='SUBMITTED' 且 ORDER BY submitted_at DESC, id DESC 的第一条（2026-09-08）

                    (首次打开该维问卷)      (Save as draft / Submit)          (提交该维)
无记录          ────────────► DRAFT ──────────────────────► DRAFT ──────────────► SUBMITTED
                                 ▲   │                                              │ 只写 submitted_at
                                 │   │ 丢弃草稿 / Reset（接口 28）                   │ 2026-09-08：不再置 is_latest
                                 │   └──────────► 无记录（DRAFT 行连同答案、附件删除，
                                 │                        unlocked_level 概念回到 1）
                                 └──── 提交后不可回退；该维再填 = 新建一条记录 ────┘
```

- `GET /erl/assessment`（带 `dimension`）命中无草稿时**不建记录**，返回**只有该维首个可作答 level 解锁**的题目结构（其余 level 为 `LOCKED`、题面不下发，§6.3）；首次 `POST draft` 才落 `DRAFT` 行（**2026-09-08**：~~`submission_seq = 该四元组内 max + 1`~~ 已随列删除）。
  - ~~**同时建齐五行 `erl_assessment_dimension`**（`unlocked_level = 1`，§5.3）~~ → **v4.4 作废**（§0.10-R1）：`erl_assessment_dimension` **整表删除**，`level_score` / `terminated_level` / `unlocked_level` 三列**直接落在 `erl_assessment` 这一行上**（§5.2），首次落草稿时 `unlocked_level` 初始化为该维首个有题 level。
  - ~~**v4.4 顺带**：首次创建评估时同事务写入 `erl_company_period_config` 的期次-配置版本绑定~~ → **2026-09-08 删除**（该表已删，§5.1.4）：不再有任何期次-配置绑定的写入点。
- **草稿的唯一性与共享语义（v4.4 显式定档，§0.10-D9）**：
  - **同公司 + 同期次 + 同端 + 同维度只有一份草稿**（`uk_erl_assessment_draft` 部分唯一索引，§5.2）。
  - **草稿是公司共享的、不区分账户**（唯一索引里没有用户维度，模型上天然如此，但产品语义必须写明）：**A 保存后 B 打开看到的就是 A 的内容，B 的保存直接覆盖 A 的** —— 后保存覆盖先保存，不做冲突检测、不做编辑锁、不做按人隔离的草稿（V1，§12）。
  - 为降低「不知道自己在改谁的东西」的风险：进入草稿时页头显示**上次保存时间与保存人**（接口 3 出参 `lastSavedAt` / `lastSavedBy{name, role}`，取 `updated_at` / `updated_by` join 用户表，**不新增快照列**）。
  - **提交人以最终点提交的那个人为准**：`submitter_name` / `submitter_role`（**2026-09-08 同时快照** `dimension_name` / `dimension_abbr`，§5.2 新增两列的**唯一写入点**）在提交时快照 —— **即使草稿全程由他人保存，提交人只记录点提交的那一个**。
  - ⚠ **「后保存覆盖先保存」只限草稿之间**（**2026-09-07 补限定**）：它<b>不</b>意味着「草稿写入可以覆盖已提交记录」。「已 SUBMITTED 的记录任何写接口一律拒绝」这条不变量在并发下**由数据库层兜底、不靠代码自觉** —— 写路径（存草稿 / 提交 / Reset / 删附件）一律先用 `SELECT … FOR UPDATE` 取草稿行再写。为什么不能只靠 `@Version`：存草稿与 Reset 只改 `unlocked_level` / `level_score` / `terminated_level` 三列，而 Reset 恰好把它们设回与自己加载快照**逐字相同**的初始值 —— 配 `@DynamicUpdate` 后 Hibernate 判定该行干净、**一条 UPDATE 都不发**，版本谓词根本没出现过，于是它能把别人刚提交记录的作答与证据附件删空且全程无异常。加行锁后行为反而更好：对方先提交时查询直接返回空，调用方走「新建草稿」分支，用户这一轮的作答一条不丢。
- **丢弃草稿 / Reset 的状态转移（v4.4 新增，接口 28 `DELETE /erl/assessment/draft`，§0.10-D8）**：
  - 转移方向 **`DRAFT → 无记录`**（不是「回到某个更早的草稿」，也不产生历史记录）：删除该四元组的 `DRAFT` 行、其全部答案行与附件登记行，`unlocked_level` 概念随之回到该维起点。
  - **不可逆，必须二次确认**，弹窗写明**附件一并删除**。
  - **只对 `DRAFT` 生效**：该四元组已 `SUBMITTED` 的历史记录一行不动，最新提交的判定不受影响（**2026-09-08**：原「`is_latest` 指向不变」随列删除改写）。
  - 附件的知识库副本按 §7.10-W3 处理（本地登记行删除，知识库条目保留）。
  - 这同时是 §13-Q23「摆脱旧版本草稿」的解法 —— **Q23 关闭**：换题集不必再「先把旧草稿提交掉」，直接 Reset 后 `Add New` 即可（订正 §7.9-⑤ 的旧路径）。
- **只有 `SUBMITTED` 的记录**进 B3 历史列表、ERL Card、维度详情页与 F2 总表。
- **四元组内 `submitted_at DESC, id DESC` 的第一条是该维度的 source of truth**（**2026-09-08**：~~`is_latest = true` 的那条~~ 随列删除改判），展示页与 F2 按维度各取各的；B3 展示全部。
  - ⚠️ **没有索引兜底「至多一条 SOT」了**（`uk_erl_assessment_latest` 随 `is_latest` 一并删除）：并发双提交会产生两条合法记录，读侧只是“选出一条”。因此**读侧每一处取 SOT 必须走同一个 Repository 方法**（排序键完全一致），否则同一秒两次提交时不同页面会选出不同的一条。**唯一例外**：接口 7 要列出**全部**记录，故走派生查询 + 在内存里按四元组取首条；允许的前提是**排序键与该 Repository 方法的谓词逐字一致**（§6.3）—— 除此之外一律不得自拼查询。
  - 因此 ERL Card / 雷达图上的一组维度分，**可能来自不同时间、不同提交批次、甚至不同题库版本的多次提交** —— 这是维度级提交的必然结果，不阻止、不告警（§7.10 新增边界）。
- 已 `SUBMITTED` 的记录**任何写接口一律拒绝**（PRD §3.3「提交后即只读」），接口 28 同样拒绝。
- **重复提交确认文案分两支（§0.10-D11）**：该 `(company, period, portal, dimension_code)` 的 `submissionCount = 0` 时沿用首次提交文案；`> 0` 时改为「**已提交该季度评价，是否再次提交？**」并补一句「本次提交将成为该季度**该维度**的 source of truth，历史提交保留」。

### 7.8 基准记录口径（**v3.1 新增**，PRD §4）

> **2026-09-08 表名对齐**：本节说的「基准记录」= `erl_reference_score`（原 `erl_benchmark_record`，§5.6），「每维基准分」= `erl_reference_score_item`（原 `erl_benchmark_dimension`，§5.6.1）；维度键为 `dimension_code`，并随行快照 `dimension_name` / `dimension_abbr`。HTTP 路径 `/erl/benchmark` **不改**。

| 口径 | 规则 |
|------|------|
| 基准分本身 | **外部输入，平台不计算、不折算**（PRD §4）；1–9，按维度存。**存储仍是一位小数**（`numeric(3,1)`），但 **D2 录入侧自 v4.34（2026-09-15）起只收整数** —— 两者不一致是刻意的，见 v4.34 的 (a)(b)(c) |
| `benchmarkitAvg` / `topQuartileAvg` | 该记录**各维基准分的算术平均**，保留 1 位小数（D1 记录表两列）。~~五维必填~~ → **v4.4 参数化**（§0.10-D1）：录入表单按**当前 `status = 'Active'` 的维度**动态渲染（**2026-09-08**：原「当前生效配置版本」作废），**全部必填**，故仍无缺维分母问题；分母是该记录实际的维度个数，**不写死 5** |
| `recordedAt` | ~~由 `period` 推导为**期末日**（`2026Q2 → 2026-06-30`），不另存字段~~ → **2026-09-10 整条改判**（§0.28-Z1）：取**审计列 `created_at`** 下发**真实录入时刻**（`Instant` / ISO-8601，为空则 `null`）。期末日那份推导（私有方法 `periodEndDate` 与常量 `MONTHS_PER_QUARTER`）**已删除** —— 它与「谁在什么时候录入」无关、同期次两条完全相同、且与 `PERIOD` 列 100% 冗余，而屏上的列头写着 `SUBMISSION TIME`；同期次可重复录入（§0.27-Z1）之后，这一列更是屏上唯一能分先后的信息。⚠️ **仍然不新增存储列** —— `created_at` 是审计基类自带的列，**表结构与迁移脚本零变更**（§5.6） |
| **卡片 / 维度页取哪条记录**（「适用记录」） | 取该公司 `period ≤ 当前展示期次` 中**最近的一条**（**2026-09-10 明确排序键**，§0.27-Z2：**`period DESC, created_at DESC, id DESC` 的第一条** —— 同期次可有多条，取最后录入的那条） —— 评估期次晚于最后一次基准录入时沿用最近基准，不留空；无满足条件的记录则视同无基准（§9）。<br>**v4.4 澄清**：这里的「当前展示期次」由 §7.1.2 确定（closed month 所在季度）。**基准记录的「向前沿用」与 §7.1.2 明令禁止的「期次回退」不是一回事** —— 前者是在**已确定的展示期次**内挑一条外部录入的参照值（基准本就按季稀疏录入），后者是把**整页的展示期次**偷偷换成上一季。基准可以沿用，评估分数不可以 |
| **卡一取哪条**（~~`latest` 卡~~ → **v4.40 改名 `Current Version`**） | ~~记录表首条（`period` 最大 → 2026-09-10 补次级键，§0.27-Z2）~~ → **v4.40（2026-09-16）整条改判**：取**该公司 `period` = 前端上下文期次（URL `?period=`）中提交时间最新的那条** —— 由前端从接口 15 的 `records[]` 里挑（每条都带逐维明细），该期次无记录或 URL 未带期次时落到**记录表首条 = 全库最近一次提交**。卡头显示 `Current Version · {所取记录的 period}`。⚠️ 服务端拿不到那个上下文期次，接口 15 的 **`latest` 段自此无消费方**（字段未删，见 v4.40） |
| 与评估分的关系 | 基准**只并列展示，不参与**综合分与 Perception Gap 的任何计算（**v4.0**：原文提到的「状态摘要」已删除，§7.4） |
| 基准分的值域（**v4.0 说明**，**v4.34 补**） | 基准**存储**仍是一位小数 1–9（`numeric(3,1)`），而评估维度分已改为 **0–9 整数**（§7.1）。⚠️ **v4.34：D2 录入框已收紧为只允许整数**，故此后**新录**的基准分事实上都是整数；存量的一位小数记录原样保留，服务端与列类型未改。两者同轴对比**不做取整或折算** —— 雷达图与维度页并列展示原值即可（基准是外部口径，平台无权改写，PRD §4） |

### 7.9 题库版本化与发布（**v3.3 重写**，PRD §3.8 + 需求方 2026-08-28 裁决）

依裁决：**新增 / 编辑 / 删除 / 重排四类变更全部经 Publish 才生效**（v3.2 的「只有新增题需发布」作废）。

> ✅ **PRD 已同步（v4.0）**：v3.3 ~ v3.6 期间本节与 PRD §3.8「变更**立即生效**」直接冲突，靠「裁决晚于 PRD」维持。PRD 2026-09-02（`621e857`）**删去了「变更立即生效」一句**，并把 Publish 条件改为「五个维度任意维度有**新问题、新顺序或新编辑内容**，按钮会被激活，**点击保存为新版本**」—— 与本节完全一致。**§13-Q11 的回写建议已被采纳，该冲突关闭。**
>
> **v4.0 追加**：版本序列的作用域由「全局」改为「**组织（租户）内**」（PRD §4「ERL 配置层级按照租户层级」，§0.9-7）。下文所有「全局」一律读作「**本组织内**」。

**① 版本模型**

| 概念 | 落地 |
|------|------|
| 已发布版本 | `erl_question_config_version.status = 'PUBLISHED'` 中**本组织 `version_no` 最大**的那条（**2026-09-09**：`is_latest` 标记列已删，判据回到倒排取第一条；`version_no` 组织内唯一 ⇒ 结果唯一，§5.1.1）。⚠️ **必须带 `status` 条件** —— 草稿行的 `version_no` 恒为最大。**只被「新发起一次评估」这一个动作读取**（v3.4 订正） |
| 草稿版本 | `status = 'DRAFT'`，**每个组织最多一份**（部分唯一索引保证，v4.0 由「全局一份」改）。**只有 ERL Configuration 页读它** |
| 一道题的跨版本身份 | `question_key`（§5.1）。`id` 每版一换，`key` 恒定 |
| 一次评估依据的题面 | `erl_assessment.erl_question_config_version_id` 快照（**2026-09-08 改名**）+ **`erl_question_config_dimension_version_id`**（**2026-09-09 新增**：该维题目集快照行的 id，取题一跳直达，为空回退复合键查询，§5.2）。**填报页、维度详情页、计分、组合层、Goldie 输入一律读它，而不是最新已发布版本**（v3.4 订正） |
| **绑定粒度（v4.4 新增，§0.10-R1）** | ~~每次评估（整卷含五维）一份~~ → **v4.4**：**每维一份** —— `erl_question_config_version_id` 挂在维度级的 `erl_assessment` 行上，故**同一公司同一期次的各个维度可能绑不同的题库版本**（如 FRL 绑 v3、PRL 绑 v4，只因两维不是同一天开始填的）。**系统不阻止、不告警**，各维按各自绑定的版本渲染、计分、组装 Goldie 输入 |

> ⚠️ **v3.4 订正**：v3.3 曾写「填报 / 展示 / 计分 / 组合层一律只读最新已发布版本」—— 那是重基模型下的表述。**版本锁定后它不成立**：一次评估从创建到提交、再到被展示与计分，全程锚在自己的 `question_version_id` 上。取「最新已发布版本」的地方**全系统只有一处** —— 创建新评估记录时（`ErlAssessmentService` 的首次 `POST draft`）。

**② 写时复制（copy-on-write）**—— **2026-09-08 判据改为两级**

> ⚠️ **为什么必须两级**：克隆粒度已是**维度级**，而草稿版本行是**组织级**。若仍用单一判据「本组织有无草稿版本」，则「先改 FRL（建草稿 + 克隆 FRL）→ 再改 PRL」时，PRL 会走「已有草稿 → 直接改」分支，而它**从未被克隆** —— `erl_question_config` 既无 `status`、也无指向版本行的外键，草稿题与已发布题在库里长得一模一样，于是该改动会**直接写穿已发布版本的题目行**，击穿 §7.9-⑤「版本锁定 / 无用户数据丢失路径」与 §7.9-⑥「不允许改已发布版本的题目行」。

```
管理员在配置页对维度 D 做任一变更（新增 / 编辑 / 删除 / 重排）
        │
        ├── 【第一级・组织级】本组织有 DRAFT 版本行吗？
        │      否 → 同事务内新建 DRAFT 行（version_no = 组织内 max + 1）
        │      是 → 复用它（并 SELECT … FOR UPDATE 取行锁，见 ②’’）
        │
        ├── 【第二级・维度级】维度 D 在**本轮草稿**里已经克隆过了吗？
        │      （判定：max(version_no WHERE dimension_code = D)
        │        > 最新已发布快照里 D 的 question_version_no）
        │      是 → 直接改那批草稿题目行
        │      否 → 同事务内克隆 D 的题目行：
        │            question_key 原样复制、id 重新生成、
        │            新 version_no = max(version_no WHERE organization_id = O AND dimension_code = D) + 1
        │            → 再在新克隆出来的那批行上改
        │
        └──► 填报页 / 维度页 / 计分 此刻读到的仍是旧的已发布版本，毫无变化

⚠️ 两个 max 是**不同集合**的 max：第一级的是 erl_question_config_version.version_no（组织级发布批次号），
   第二级的是 erl_question_config.version_no（按 dimension_code 分组的题目集版本号）。

管理员点 Publish（接口 21）
        │
        └──► DRAFT.status = PUBLISHED，写 published_at / by
             （2026-09-08：change_summary 列已删，不再写快照）
             同一事务内：为每个 status='Active' 的维度写一行
             erl_question_config_dimension_version（code/name/abbr/
             question_version_no/sort_order/bound_at）—— 发布当时的维度快照
             ↑ question_version_no = max(version_no WHERE organization_id = 本组织 AND dimension_code = 该维)，
               本轮被克隆过的维度拿到新号，未改动的拿到与上一版相同的旧号
             本版 status 翻成 PUBLISHED，它自己就成了「PUBLISHED 里 version_no 最大」的那一版
             （2026-09-09：is_latest 已删，**一行都不碰上一版**，也不再有标记转移这一步）
             → 此刻起**新发起的评估**用新版本
             → **已存在的评估（含正在填的草稿）继续用各自绑定的旧版本**（v3.4 版本锁定）
             → **Publish 不推进任何 version_no**（推进发生在每维首次编辑的克隆时刻）
```

**②’’ 本轮草稿改动了哪些维度（**2026-09-08 新增，三处共用**）**

新模型下「哪些维度被改过」**没有任何地方直接记录**，而它是三个地方的前提。统一由**一个解析函数** `draftDimensionVersions(organizationId)` 给出：

> ⚠️ **2026-09-09 判据改写（需求方裁决）**：原先这里写的是「用两个 max 比大小反推」——
> `若 max(erl_question_config.version_no) > 最新快照里该维的 question_version_no ⇒ 本轮已克隆`。
> 该推论**在两个产品可达的状态下给出错误答案，且两次都是静默的**，已作废：
>
> | 触发 | 反推给出的错误答案 | 后果 |
> |------|------|------|
> | 停用某维 → 发布 → 恢复该维 | 该维不在最新快照里（published = 0）而它的孤儿行还在 max ⇒ 误判「已克隆」 | 编辑**直接写穿已发布版本**；走接口 13 则是**物理删掉已发布的题目行**，绑定该版本的历史评估永久丢题 |
> | 把某维的题**删光** | 空的克隆版本让 max 回落到已发布号 ⇒ 误判「未克隆」 | **删除被静默撤销**：刷新后题目原样复活，变更摘要显示「无变更」，发布快照写回旧号 |
>
> 根因是 `max(version_no)` 同时承担了「哪一版是草稿」与「是否已克隆」两个职责，而这两件事并不等价。

**判据改为显式记录**：克隆某维时，**同事务往 `erl_question_config_dimension_version` 写一行草稿版本的快照**。

```
ensureDimensionCloned(organizationId, dimensionCode)：
    若存在快照行 (erl_question_config_version_id = 草稿行 id, dimension_code)
        ⇒ 本轮已克隆，直接返回该行的 question_version_no
    否则
        ⇒ draftNo = max(erl_question_config.version_no WHERE organization_id AND dimension_code) + 1
           克隆该维**现有最新一批行**（即 max 那一版）到 draftNo
             —— 取 max 而不是取已发布号，是为了兑现 ②'''' 边界 ①「孤儿行在维度恢复时直接用上」
           写快照行 (草稿行 id, dimension_code, draftNo)
           返回 draftNo

draftDimensionVersions(organizationId)：
    对每个 status = 'Active' 的维度：
        published = 最新已发布版本的快照行.question_version_no（无则 0）
        若草稿行有该维快照 ⇒ 本轮**已克隆**，草稿题集 = 快照行.question_version_no
        否则                ⇒ 本轮**未改**，草稿题集 = published
```

> 💡 **顺带拿到的好处**：草稿行与发布行是**同一条 `erl_question_config_version`**
> （Publish 只是把它的 `status` 翻成 `PUBLISHED`，`id` 不变），所以克隆时写下的那批快照行
> **自动成为该发布版本的快照**，无需重写。Publish 时只剩两件事：为**本轮未克隆**的
> `Active` 维度补行（取旧号 / 从未有题写 `0`），以及删掉「草稿期克隆过、发布前又被
> `Inactive`」的行（②'''' 边界 ①）。

三个消费方：① 写时复制的第二级判据（上图）；② 草稿态的读侧取题（§7.9-②’）；③ 发布前的变更摘要 diff（§7.9-③）—— **diff 必须逐维做**，跨维度的整版本查询在新模型下不成立（§10.1）。

**②’’’ 并发防线的准确表述（**2026-09-08 订正**）**

之前写的「所有编辑经同一条草稿行的 `@Version` 乐观锁」**说得不准**：`ensureDraftVersion` 在「草稿已存在」时只是一次 SELECT，不发 UPDATE ⇒ 版本谓词根本没出现，`@Version` **只在「首次创建草稿」那一次生效**。真正兜住竞争的是行锁：

- **每次题库写事务开头对草稿版本行 `SELECT … FOR UPDATE`**（§0.18-L4）—— 这才是「A 加题 vs B 发布」与「两人同时首次编辑同一维度」两个竞争的唯一防线，也是第二级判据与克隆必须原子的原因。
- `@Version` 仅兜住**并发建草稿**（两个事务同时发现无草稿），与部分唯一索引 `uk_erl_question_config_version_draft` 双保险。
- ⚠️ **懒克隆新增了一个窗口**：A 首次编辑 PRL（触发 PRL 克隆）与 B 点 Publish 并发时，若 B 先提交，A 的克隆行会落在一个已变成 PUBLISHED 的版本头之下，既不在任何快照里、又是下一轮草稿的克隆基线 ⇒ A 未经审阅的改动会**静默混进下一次发布**。行锁能挡住（前提是编辑方真的取锁），**代码审查须专项检查**。原「整库克隆一次、之后只改草稿行」的模型没有这个窗口。

**②’’’’ Publish 写快照的三个边界（**2026-09-08 定档**）**

| 情形 | `question_version_no` 取值 |
|------|------|
| 本轮被克隆改过的维度 | 新克隆出的那个号（= 该维 `max`） |
| 本轮未改动的维度 | 与上一版快照**相同的旧号**（该维 `max` 恰等于它） |
| **`Active` 但从未有题的维度**（新增后还没加题） | `max` 为空 ⇒ **写 `0`**，表示「该版本下本维题集为空」。**仍要写这一行**（否则 C7 缺卡）；该维的填报与提交由 §6.3 校验 3「0 题维度不可提交」拦住 |

另两个并发边界：① 某维在草稿期被克隆改过、**发布前又被置 `Inactive`** ⇒ 不写快照，其克隆行成为**孤儿行**（无快照指向，但仍是该维 `max`）—— 日后该维被恢复为 `Active` 时会被下一轮直接用上，**需在恢复时提示管理员确认**；② 发布前新 `Active` 但本轮未克隆的维度 ⇒ 按上表第二/第三行取值，正常写快照。

**②’ 两个 `version_no` 的分工与读侧解析（**2026-09-08 新增**）**

| 列 | 含义 | 自增维度 |
|------|------|------|
| `erl_question_config_version.version_no` | **组织级发布批次号**（配置页显示 `Published v3` / `Draft v4`） | 组织内自增 |
| `erl_question_config.version_no` | **某个维度的题目集版本号** | 按 `dimension_code` 各自自增 |

两者由 `erl_question_config_dimension_version`（§5.1.5）建立对应。**读侧取「某发布版本下某维的题」分两条路径**：

- **已发布版本**：先按 `erl_question_config_version_id` + `dimension_code` 命中快照行拿到 `question_version_no`，再按 `(dimension_code, version_no)` 取题。
- **草稿版本**（快照只在 Publish 时写，草稿行无快照）：取该维的 `max(version_no)` —— 本轮未被改动的维度，其 max 恰等于已发布号，行为自洽。
- **已绑定快照行的评估**（**2026-09-09 新增**，优先级最高）：`erl_assessment.erl_question_config_dimension_version_id` 非空时**直接一跳**取该行的 `question_version_no`，不再按复合键反查（§5.2）—— 前提是该行还在、维度与批次都对得上，否则打 WARN 回退。为空（存量行、或该维在那一版下本就没有快照行）时回落到上面两条路径 —— **三条路径对同一份数据必须解出同一个号**。

> **为什么草稿仍是「组织级一份」而不是每维一份**（**2026-09-08 定口径**）：§5.1.1 保留了 `uk_erl_question_config_version_draft ON (organization_id) WHERE status = 'DRAFT'`，即每组织至多一份草稿。这同时保住了 §0.18-L4 的并发论证 —— 所有题库编辑仍经同一条草稿版本行的 `@Version` 乐观锁 + 悲观锁，如果改成每维一份草稿，那条论证会失效。

**③ Publish 按钮**

- **激活条件 = 存在草稿版本**。✅ **v4.0：与 PRD 现文完全一致** —— PRD 2026-09-02 已把条件写成「有**新问题、新顺序或新编辑内容**」（即四类变更任一），不再是 v3.2 时的「只有新问题」。
- **维度配置不受 Publish 管辖**（v4.0 原「权重不受 Publish 管辖」，**v4.4 扩展**）：配置页第二个 Tab 已由 ~~`Dimension Weights`（只管权重）~~ 改为 **`Dimension Configuration`**（维度新增 / 删除 / 排序 / 权重，§0.10-D13），它有**自己的 Save 按钮**与「权重合计 = 100.00」校验，~~保存即生成新的维度配置版本~~ → **2026-09-08：就地整组替换，不产生版本**（§7.11），**不产生题库版本、不激活 Publish 按钮**（§6.4 接口 24）。反之，题库 Publish **不改**维度配置，但**会读**当时 `Active` 的维度写入 §5.1.5 快照 —— ~~两条版本线完全独立~~ 改为**只剩题库一条版本线**。
- 按钮**不分维度**：一次发布整个草稿版本（**该版本内的全部维度一起**，v4.4 不再表述为「五维一起」），不做单维发布（依裁决，§12）。
- 变更摘要由草稿与最新已发布版本按 `question_key` 逐字段 diff 得出（**2026-09-08**：**必须逐维做** —— 先用 `draftDimensionVersions()`（§7.9-②’’）解出每维的草稿号与已发布号，再逐维比；跨维度的整版本查询在新模型下不成立）（`added` / `modified` / `removed` / `reordered`），用于按钮旁提示与发布确认框。⚠️ **2026-09-08：只实时算、不落库**—— `change_summary` 列已删（§5.1.1），故**接口 25（C7 版本历史）的 `changeSummary` 出参已无数据源**：历史版本的对比基线早已随后续发布改变，实时 diff 会算出与当时不同的数字，因此**接口 25 不再返回该字段**（接口 9 的实时 diff 保留，供 Publish 按钮与确认框用）。

**④ 多管理员共享同一份草稿（必须知会）**

草稿版本**在组织内**单份（v4.0）⇒ **同一组织的两个管理员同时改的是同一份草稿**，且**任一人点 Publish 会把另一人尚未改完的变更一并发布出去**。这是「题库按组织单份」的必然结果，不是缺陷，但必须在界面上说清：

- 配置页页头常驻显示 `Draft v{n} · last edited by {name} at {time}`（**2026-09-08 补注数据源**：§5.1.1 八列里**没有** `last_edited_*` 列 —— 取审计基类自带的 `updated_at` / `updated_by`（§5 开头），**前提是每次编辑都 touch 草稿版本行** —— 而二级判据下本就要对它取行锁并写回，恰好自洽）；
- 发布确认框列出**全量变更摘要**（含他人的改动），而不只是当前管理员这次改的部分（§8.4 C5）。

V1 不做草稿的编辑锁、按人隔离的草稿、变更逐条勾选发布 —— 题库配置是低频管理动作，为它上并发控制不划算（§12）。

**⑤ 版本锁定（v3.4 重写，依 2026-08-28 第二次裁决）**

> 裁决原文：「**保留旧答案，以正在编辑的版本为准** —— Founder 用 v3 版本打开就是 v3，GSV 用 v4 填。」v3.3 的重基（rebase）机制**整体删除**。

**规则只有一条**：一次评估在**创建时**绑定当时最新的已发布版本（写入 `erl_assessment.erl_question_config_version_id`，**2026-09-08 改名**；**2026-09-09** 同一时刻再写 `erl_question_config_dimension_version_id` —— 本维在那一版下的快照行 id，取不到则留 `null`，§5.2），**此后只有 Reset（接口 28）会改写** —— 无论期间题库发布了多少个新版本，**在填的那一份都不会自己升级**；只有用户显式 Reset（答案随之全部清空）才会改绑到当时最新的已发布版本（**v4.26**，§0.30）。

| 场景 | 行为 |
|------|------|
| 正在填的草稿，期间题库发布了新版 | **内容零变化**：题目、题序、题数、来源标签、**level 结构与解锁进度**全部不变，已答内容原封不动（v4.0：`unlocked_level` 同样锚在旧版本的 level 结构上）。<br>~~**毫无感知** / 填报页无任何提示、无任何变化~~ → **v4.4 订正**（§0.10-D10；**提示形态已于 2026-09-15 由 banner 换成强阻断弹窗，v4.41 回写，见 §8.4**）：PRD §3.3（`4f959bb`）要求「若题库已更新，则**提示**题库更新，**不做强制退出和更新**」——**版本不跟随这一本体不变**，但要提示：~~填报页顶部挂一条**非阻断、可关闭、无操作按钮**的 banner：`The question library has been updated (v{n}). This assessment continues on v{m}.`~~ → **2026-09-15 起为强阻断二选一弹窗**（见 §8.4）（数据均来自接口 3 出参新增的 `latestPublishedVersionNo` / `hasNewerQuestionSet`） |
| 题干在新版本里被改了 | 该评估看不到 —— 它读的是自己那版的题面。**答案与题面永远同版本自洽**（原 §13-Q13 消失） |
| 某题在新版本里被删了 | 该评估里这题还在，分数 / 备注 / 附件一个不动（原 §13-Q14 消失，**无任何用户数据丢失路径**） |
| 新版本加了题 | 该评估不会多出未答题，`totalCount` 不变，不会被打断 |
| 提交 | **不校验版本是否最新**（v3.3 的前置校验 0 已删除）—— 半年前开的草稿仍按半年前的题集提交，不阻止 |
| 已 `SUBMITTED` 的记录 | 同样恒按 `erl_question_config_version_id` 渲染；历史详情、计分、Goldie 输入全部据此（§11-24） |
| 下一次 `+ New` 发起新评估 | 才取当时最新的已发布版本 |

**衍生结论**：

- **同一期次的两端可以不同版本**（裁决明确接受）：Founder 用 v3 提交 → 管理员发布 v4 → GSV 用 v4 填。Perception Gap 因此可能跨两套题集，**不阻止、不告警**，但**两端的题集版本号在 Scorecard 与历史列表上标出**（§7.10-N2）。
  - **v4.4 扩展（§0.10-R1）**：维度级提交后，**同一期次同一端的各个维度之间也可以不同版本**（FRL 绑 v3、PRL 绑 v4）。同样不阻止、不告警，各维按各自版本渲染与计分；版本号照 N2 标出（**v4.4 起标在分数列下方的次级文字**，`Completion` 列已删，§7.1.1）。
- **同一期次多次提交也可能跨版本**：第 1 次基于 v3、第 2 次基于 v4，题数（`totalCount`）不同是正常现象。~~`Completion` 分母不同~~ → **v4.4 订正**（§0.10-D12）：`Completion` 列已删，该差异现在只体现在详情页页头的题数文案上，列表侧不再暴露分母。
- **Goldie 分析不受题库发布影响**：其输入（答案 + 备注 + 题干 / level）全部取自评估绑定的版本快照，题库发新版后输入一字未变 → **发布不触发重生成**（原 §13-Q15 由设计选择升级为逻辑结论）。
- **不提供「把在填评估升级到最新题集」的按钮**（§7.10-N3）：代价是若新版修正了写错的题干，在填的人享受不到；换来的是「答案与题面永远自洽」这条硬保证。⚠️ **v4.26 补充**：Reset 之后的改绑**不属于**这条禁令 —— 禁的是「保着答案换题面」，而 Reset 是「答案清空后重新开始」，「答案与题面永远自洽」这条硬保证一字未破。
  - ~~**「重开一份」的确切路径（v3.6 定档）**：§5.2 有同 `(company, period, portal)` **唯一草稿**的部分唯一索引，且 V1 无丢弃草稿接口 —— 所以旧版本草稿**不能被直接抛弃后新建**，必须 **先把旧草稿提交掉（成为 `seq = n` 的一条历史提交），再 `+ New` 发起 `seq = n+1` 的新评估**。代价是历史列表多出一条「为了换题集而提交」的记录~~ → **v4.4 作废**（§0.10-D8）：**接口 28 `DELETE /erl/assessment/draft` 已补**（Founder Flow 的 `Reset` 按钮即此接口）。
    - **新路径**：直接 **Reset 丢弃旧草稿 → `Add New` 重新发起**，新草稿创建时绑定当时最新的已发布版本，**不再需要「为了换题集而提交」的垃圾记录**（§7.7）。
    - ⚠️ **v4.26 订正**：上面这条「新路径」在实现上**一直是断的** —— §6.3 / §9 定的 Reset 是**保留草稿行**（只清答案、复位三列），`findOrCreateDraft` 因此永远命中那条旧行、走不到「创建时绑定最新版本」的分支，Reset 完再 `Add New` 拿到的仍是旧题集。修法是在 `discardDraft` 清完答案后**就地改绑**，而不是改回「Reset 删行」（§7.7 的那条口径仍作废，见 §6.3 的三处不一致说明）。改绑后 `hasNewerQuestionSet` 自然变 `false`、题库更新弹窗随之关闭。
    - 唯一草稿的约束本身不变，只是作用域随维度级提交收紧为 `(company, period, portal, dimension_code)`（§5.2 / §0.10-R1）。
    - 代价从「多一条历史记录」变成「**丢掉已填内容与附件**」，故接口 28 必须二次确认并写明附件一并删除。**§13-Q23 关闭。**

**⑥ 首版与部署**

- ~~`erl_init.sql` 种子数据落 `version_no = 1`、`status = 'PUBLISHED'`、`published_by = 'system'`（**2026-09-09**：`is_latest` 已删，不再落该列），题目行 `question_key` 与 `id` 各自生成 —— 否则系统起来后没有已发布版本，填报页全空。~~ → **2026-09-17 作废：脚本不再落任何版本行与题目行** ⇒ **「系统起来后没有已发布版本、填报页全空」正是新库的既定状态**，直到管理员在配置页 Publish 第一版（`ensureDraftVersion` 建 `version_no = 1` 草稿 → Publish 转 `PUBLISHED` 并逐维写 `erl_question_config_dimension_version`）。
- **2026-09-08 补两项**：① 题目行按维度各落 `erl_question_config.version_no = 1`（不再挂 `version_id`）；② **必须为每个维度写一行 `erl_question_config_dimension_version`**（`question_version_no = 1`）—— 漏写则接口 26 解析不出任何维度、C7 页体全空。
- 上线后**不允许直接改库里已发布版本的题目行**（会让历史评估的题面漂移）；任何修正都走配置页 → 草稿 → Publish。

### 7.10 版本化的边界（**v3.3 新增** —— 开发前逐条对齐；**v4.4：W1 改判、新增 N4 / N5**）

题库版本化把「题面」从一份变成多份，随之产生一批**必须明确取值、否则实现会各写各的**的边界。下表是全量清单：**A 类**由裁决直接给出、**B 类**本设计已取默认值（需求方知悉即可）、**C 类**会改变实现结果，**必须产品拍板**（已登记 §13-Q13 ~ Q16）。

| # | 边界 | 类 | 本设计取值 | 若取反面 |
|---|------|:--:|-----------|----------|
| 1 | **发布粒度** | A | 一次发布整个草稿版本（**该版本内的全部维度一起**，v4.4 不再表述为「五维一起」） | 单维发布 —— 裁决已明确不做 |
| 2 | **撤回 / 回滚** | A | 不做（已发布不可退回草稿，无版本回滚 UI） | 需要版本切换与「当前生效版本」指针，模型要再改一层 |
| 3 | **变更类型** | A | 新增 / 编辑 / 删除 / 重排**四类全部**经发布 | v3.2 的「只有新增经发布」——已作废 |
| 4 | **草稿唯一性** | B | **全局一份草稿**，多管理员共享；任一人发布会连带发布他人未完成的改动（§7.9-④） | 每人一份私有草稿 → 需要三方合并与冲突解决，V1 不划算 |
| 5 | **丢弃草稿** | B | **不做**。误改只能手工改回来（变更摘要可见，题库低频） | 加 `DELETE /erl/question/draft` 即可，不影响模型（§12） |
| 6 | **评估是否跟随题库** | A | **不跟随（版本锁定）** —— 评估创建时绑定版本，此后题库发布多少版都与它无关（v3.4 裁决，§7.9-⑤） | 重基（v3.3 方案）—— 已被裁决取代 |
| 7 | **版本数据保留** | B | ~~每发布一版整份克隆题目行~~ → **2026-09-08：只克隆被改动的那个维度**（按 `dimension_code` 分版本线），**永久保留、不清理**（行数比整库克隆低一个量级：一年 20 版中每版均只动 1~2 维） | 定期归档旧版本 —— 会让历史评估取不到题面，不可做 |
| 8 | **谁能 Publish** | B | C 模块的 admin 均可，不再分级 | 若需「编辑者 / 发布者」分权，属 §13-Q7 的角色细化 |
| 9 | **组合层跨版本可比性** | B | 不做提示 —— F2 总表可能同屏比较基于不同题库版本的分数 | 要提示则需在表内标版本号，噪音大于价值（V1 不做趋势对比） |
| **W1** | **改权重会改变历史期次的综合分与 Stage**（~~v4.4：已快照不漂移~~ → **2026-09-08 反转回原取值**） | **A** | **接受漂移**：权重不版本化、**不做任何快照**，综合分实时按当前 `erl_dimension_config.weight` 算（§5.1.3 / §7.1）；C6 的 Save 确认框须写明这一点。~~v4.4：维度与权重整体版本化 + 期次绑定~~ → **2026-09-08 作废**：`erl_dimension_config_version` 与 `erl_company_period_config` 两张表已删（§5.1.2 / §5.1.4），**R2「历史永不漂移」正式失效**。**§13-Q21 重新打开** | 要不漂移 —— 需在 `erl_assessment` 上存每维权重快照，需求方 2026-09-08 已选择不补 |
| **W2** | **跨组织题库结构不同 ⇒ 分数不可比**（v4.0） | B | **接受、不提示**：F2 只列有权访问的公司，正常同组织；跨组织时综合分各按各组织权重算（§6.8） | 要求全平台统一题库 —— 与 PRD §4「配置层级按租户」直接冲突 |
| **W3** | **改答收回 level 时，已入知识库的附件不回删**（v4.0） | B | **不回删**：附件删本地登记行，知识库条目保留（公司级资产，PRD 未要求联动清理，§6.7） | 联动删知识库 —— 需 Python 侧补删除接口，且同一文件可能被别处引用 |
| 10 | ~~题干被编辑后旧答案是否仍有效~~ | **A** | **问题消失**（v3.4）—— 评估看不到新题干，答案与题面永远同版本自洽 | — |
| 11 | ~~删题时该题的已答内容~~ | **A** | **问题消失**（v3.4）—— 删除只落新版本，旧版本评估里该题原样保留。**全设计无用户数据丢失路径** | — |
| 12 | **发布是否触发 Goldie 重新生成** | **A** | **不触发**（v3.4 由设计选择升级为逻辑结论）—— 分析输入全部锚在评估绑定版本上，题库发新版后输入一字未变 | — |
| 13 | **同一期次两端可否基于不同版本作答** | **A** | **允许**（v3.4 裁决原文即取值）。不阻止、~~不告警~~ → **v4.58 改判：维度级不可比要告警**（P4，§0.32-Y1）—— 提交侧仍不阻止、两端版本号照旧在 Scorecard 与历史列表标出；新增的只是 A1 Gap 区块里该维渲染成黄点 `Question set mismatch` 且**不送进 Goldie 分析** | 要求两端同版本 —— 会让「发布」被在填评估无限期阻塞 |
| **N1** | **旧版本草稿的时效** | B | **可无限期停留**：提交时**不校验**绑定版本是否最新，半年前的草稿按半年前的题集提交。~~期间填报页无任何提示~~ → **v4.4 订正**（§0.10-D10）：**「可无限期停留」这条行为不变，但要提示** —— ~~填报页顶部一条非阻断、可关闭的 banner 告知「题库已更新到 v{n}，本次评估继续用 v{m}」~~ → **2026-09-15 起改为强阻断弹窗、必须二选一**（v4.41 回写，见 §8.4）：要么按旧题库就地提交、要么 Reset 换新题库 —— 于是「无限期停留」实际只剩「不主动进这一页」这一种方式，用户可自行决定是否 Reset 重开（接口 28）。**v4.58 增补**（P4，§0.32-Y1）：一方停在旧题集期间，若两端**都已提交**且该维题集版本号不等，A1 Gap 区块该维显示 `Question set mismatch` 并跳过分析，落后一方补交后自动消失（§7.7） | 设过期时间强制重开 —— 会丢已填内容，与「不丢数据」的取向冲突 |
| **N2** | **同期次多次提交跨版本** | B | **允许**：第 1 次基于 v3、第 2 次基于 v4。**历史列表与 Scorecard 必须标题集版本号**（v4.4：标在**分数列下方的次级文字**，`Completion` 列已删，§7.1.1 / §0.10-D12），否则题数不同会被当成 bug。**v4.58 增补**：跨版本本身照旧允许、不阻断，但两端同维版本号不等时 Goldie 不分析该维、小卡出第四态提示（P4，§0.32-Y1） | 强制同期次同版本 —— 同 13 的问题 |
| **N3** | **在填评估「升级到最新题集」按钮** | B | **不做**（⚠️ **v4.26**：指的是「**保着答案**换题面」；**Reset 之后的改绑不在此列**，那时答案已全部清空，见 §0.30）。代价：新版若修正了写错的题干，在填的人享受不到 —— 但 v4.4 起用户至少**知道有新版**（N1 的提示，2026-09-15 起是强阻断弹窗，§0.10-D10 / §8.4）。~~「重开一份」需先提交旧草稿再 `+ New`（唯一草稿约束 + 无丢弃接口，v3.6 定档）~~ → **v4.4 作废**（§0.10-D8）：直接 **Reset（接口 28）丢弃草稿 → `Add New`** 即可，不再需要垃圾提交（§7.7 / §7.9-⑤） | 做升级按钮 —— 等于把已删除的重基又请回来 |
| **N4（v4.4 新增，v4.8 换依据，**2026-09-08 换机制**，**2026-09-09 分成两个动作**）** | **维度删除对历史期次的影响** | A | **2026-09-09 前置**：配置页有**两个**破坏性动作，且**能删的与能影响历史的不重叠** —— **垃圾桶=删除**只对「从未进入过任何已发布题库版本」的维度开放（`deleted = true`；那种维度不可能出现在任何已发布快照里，本行以下讨论的历史漂移**对它同样成立**，只是它多半还没被填报过），**电源按钮=停用**才是已发布维度唯一能做的事。以下原文描述的正是**停用**那一支：**停用 = 软删**（`status = 'Inactive'`，行与 `weight` 原样保留，§5.1.3）：① **历史提交记录照常显示** —— 名称 / 缩写取 `erl_assessment.dimension_name` / `dimension_abbr` 行上快照（§5.2），`Retired` 灰标由 `status` **直接判定**（~~由「是否还在当前生效版本里」派生~~ 作废）；② 不进新期次的问卷、不参与新期次的综合分与 Share 门槛（§7.5-S1）。⚠️ **但历史期次的综合分、Stage 与雷达图形状会因此漂移**（该维退出分母、剩余权重重新归一化）—— 这是 2026-09-08 已接受的代价，~~旧版本 item 行原样保留、历史不变形~~ 随两张表删除而作废。~~V1 仍**不做**「有历史数据禁止删除」的前置拦截（软删下行不消失）~~ → **2026-09-09 改判**：拦截存在，判据是「是否进入过已发布题库版本」（§13-Q24 / §0.21-X12）—— 于是**已被填报过、且题库发布过的维度根本删不掉**，只能停用，本行讨论的漂移场景全部由停用触发 | 物理删除 —— 历史记录连名字都查不到，2026-09-08 已否决（**2026-09-09 的「删除」仍不是物理删除**：置 `deleted = true`、行留、历史按 code 仍解得出，§5.1.3） |
| **N5（v4.4 新增）** | **同一期次的各维度绑不同题库版本** | B | **允许，各自独立**（维度级提交的必然结果，§0.10-R1）：渲染按各维自己的 `erl_question_config_version_id`（再经 §5.1.5 快照解析出该维的 `question_version_no`），计分按各维自己的 level 结构（`max(levels)` 可能因版本而异），Goldie 输入按各维自己的题面组装。**不阻止、不告警**，仅在历史列表/Scorecard 的分数列下方标出各维的版本号 | 要求同期次全维同版本 —— 会让「发布」被任一在填维度无限期阻塞，且与维度级提交直接矛盾 |

> **v4.0：本表新增 W1 ~ W3 三条**（权重与跨组织带来的边界）；~~W1 是 C 类~~ → ~~v4.4：升为 A 类、§13-Q21 关闭~~ → **2026-09-08：W1 仍是 A 类（已裁决），但取值反转为「接受漂移」，§13-Q21 重新打开**。v3.4 关闭的第 10–13 条不受影响。取「最新已发布版本」的代码路径全系统只有一处（创建评估记录时），是本模块的**唯一版本入口**，代码审查专项检查。
>
> **v4.4：本表新增 N4 / N5 两条**（动态维度与维度级提交带来的边界）。⚠️ ~~本模块有两条互相独立的版本线~~ → **2026-09-08 订正：只剩一条版本线** —— **题库版本**（`erl_question_config_version`，Publish 生效，绑在 `erl_assessment.erl_question_config_version_id`；版本内各维的题目集另有按 `dimension_code` 自增的 `erl_question_config.version_no`，两者由 §5.1.5 快照表对应）。~~维度配置版本（`erl_dimension_config_version`，绑在 `erl_company_period_config`）~~ **两张表均已删除**（§5.1.2 / §5.1.4）：维度配置只有一份**当前值**，不再有版本线，也不再与期次绑定。Publish 时只是把当时 `Active` 的维度**逐维快照**进 §5.1.5，供 C7 回看。
>
> **v4.0 另新增的一条计分边界**（不属版本化，记在此处便于集中核对）：**逐级解锁的「同一 level 内是否要答完才算终止」** —— 定档为**要答完**（§7.2-①）。若取反面（见 No 即终止、不必答完该 level），Goldie 会缺失该 level 内其余准则的达成情况，且 `answeredCount` 会因用户答题顺序不同而不同 —— 同一份实际情况能产生两个不同的完成度。

### 7.11 维度配置的保存与生效（~~v4.4 版本化~~ → **2026-09-08 整节重写：去版本化**）

维度不是编译期枚举，而是**租户级的配置数据**（`ErlDimensionEnum` 与前端 `constants.ts` 的静态 `DIMENSIONS` 映射均已删除，改**接口驱动**）。~~v4.4 把它做成了可版本化 + 期次绑定的三张表~~ → **2026-09-08 改回单表当前值**：本节重写为「怎么保存」「怎么生效」「删除怎么算」三件事。

**① 只剩一张表**（模型见 §5.1.3）

| 表 | 作用 |
|------|------|
| `erl_dimension_config` | 一个**组织**的维度集合当前值：`dimension_code` / `dimension_name` / `dimension_abbr` / `sort_order` / `weight` / `status` / **`deleted`**（**2026-09-09 新增**，与 `status` 正交：`deleted = true` 的行**所有读侧一律排除**、页面无恢复入口，§5.1.3）（**2026-09-09**：`saved_at` / `saved_by` 已删，「上次保存于何时」改取审计列 `max(updated_at)`）。`dimension_code` 是**稳定身份**、一经创建永不改变，历史数据靠它关联 |
| ~~`erl_dimension_config_version`~~ | ❌ **2026-09-08 整表删除**（§5.1.2）—— 不再有配置版本头，「上次保存于何时 / 谁保存的」由行上的**审计列 `updated_at` / `updated_by`** 承接（**2026-09-09**：一度下沉的 `saved_at` / `saved_by` 两列已删） |
| ~~`erl_company_period_config`~~ | ❌ **2026-09-08 整表删除**（§5.1.4）—— 期次不再绑定配置版本，**R2「历史永不漂移」随之失效** |

**② 保存：整组就地替换，不产生版本**

```
管理员在配置页 Dimension Configuration Tab 增 / 删 / 改名 / 排序 / 改权重
        │
        └──► 点 Save（接口 24 PUT /erl/dimension/config，整组提交）
                 │
                 ├── 服务端校验：带 dimensionCode 的行必须命中已有行；
                 │                          不带的为新增，由服务端随机生成 code（2026-09-08）
                 │                + **`status = 'Active'` 的行**权重合计**恰为 100.00**
                 │
                 ├── ~~同一事务内**第一阶段**：把本组织**全部已有行**落成 status = 'Inactive' 并 flush~~
                 │                ❌ **2026-09-15 删除 parkAll**（v4.31）：它存在的唯一理由就是腾空
                 │                  部分唯一索引 uk_erl_dimension_config_abbr，而该索引已整条删除
                 │                  ⇒ 「停用 FRL + 新增一个也叫 FRL 的维度」「A/B 互换缩写」这类
                 │                  终态合法的操作天然合法，不再需要中间态；保存**变成单阶段**
                 │                ⚠️ savedAt 的口径随之变化：不再 bump 全组行，
                 │                  「整组上次保存于何时」= 全部行 max(updated_at) 仍成立，
                 │                  只是**只有真正发生变更的行会 bump**（乐观锁仍然正确：
                 │                  有变更必 bump，无变更则令牌不变、下次仍校验得过）
                 │
                 └── 同一事务内**直接写终态**（~~第二阶段~~）：按 (organization_id, dimension_code) upsert erl_dimension_config
                                 （覆盖 name / abbr / sort_order / weight / status；保存时间 / 保存人
                                   由审计列 updated_at / updated_by 承接，2026-09-09）
                                 + 提交里**缺席**的维度置 status = 'Inactive'（软删，**不删行**）
                                 + deletedCodes[] 点名的维度置 deleted = true（**2026-09-09**，
                                   真删：行留、页面两处都不显示、无恢复入口；status 不动
                                   —— **2026-09-15 起这是默认结果**：parkAll 没了，
                                   没有东西会顺手改 status，只 setDeleted(true) 即可）
                     → 保存即**全局生效**，无版本、无生效延迟
```

⚠️ **可删性检查的落点（**2026-09-09**；**2026-09-15 理由更新**，§0.21-X8）**：`deletedCodes[]` 的三条校验（§6.4-3-⑧⑨⑩）与集合完整性校验（§6.4-2-⑥）**必须都在 `validate()` 阶段完成**，用**整组锁读**（`findForUpdateByOrganizationId`）拿到的 `existing` 判定 —— ~~上图**第一阶段 `parkAll` 会把该组织全部行落成 `Inactive` 并 flush**，之后再读 `status` 看到的全是 `Inactive`，「这一维原本是不是 `Active`」就再也问不出来了。⚠️ 这个错**不报异常**：两条校验都还在跑，只是判据变成了常量，于是开始静默放行本该被拦住的删除。~~ → **2026-09-15：`parkAll` 已删除**（本节上图，v4.31），这个陷阱随之消失；**落点的要求不变** —— 校验一律跑在任何写入之前，因为业务错误要求「**库中不得有任何写入**」（§6.4-3）。

~~⚠️ **「删除只写 `deleted`、`status` 一字不动」在两阶段落库下是一道主动动作，不是默认结果（**2026-09-09 追加裁决 + 实现回写**）**：
`parkAll` 已经把这一行落成了 `Inactive`，所以第二阶段处理 `deletedCodes[]` 时**必须把 `status` 显式还原成删除前的值**（按 `previouslyActive` 判：原来是 `Active` 就写回 `Active`），只 `setDeleted(true)` 就收工的话，`status` 会**顺带**被 `parkAll` 改掉 —— 库里从此分不出「这行是被停用了」和「这行是被删了、删之前是启用的」，两个动作在数据上混成一个。~~
→ **2026-09-15 作废**（v4.31）：`parkAll` 已删除 ⇒ **「删除只写 `deleted` 一列」此后是默认结果**，处理 `deletedCodes[]` 就是 `setDeleted(true)`、**完全不碰 `status`**，那道「按 `previouslyActive` 写回」的补偿动作连同它的两条单测口径一并取消。**裁决本身不变**：落库仍是「删掉启用中的维度 = `(Active, true)`、删掉停用中的维度 = `(Inactive, true)`」（§0.21-X13 / §5.1.3）。
> ⚠️ **代价是库里会真实存在 `status = 'Active'` 且 `deleted = true` 的行**，于是「已删维度不被热读捞出来」**完全依赖读侧都带 `deleted` 这一半**：~~`uk_erl_dimension_config_abbr` 的谓词（§5.1.3）与~~（**2026-09-15：索引那一半随该索引删除一并消失，「已删行不占缩写」也不再是个需要保证的事**，v4.31）每一个读侧方法名上的 `AndDeletedFalse`。漏掉它，这一行就会**以启用维度的身份复活**（重新出现在主列表、进权重合计与问卷）。
> ~~本条 2026-09-09 首次实现时正是漏在这里：`status` 留在了 `parkAll` 落下的 `Inactive`，与本节及 §5.1.3 的「删除不改 `status`」不一致，已修正并补了两条单测（启用维度删后仍 `Active`、停用维度删后仍 `Inactive`）。~~（**2026-09-15：`parkAll` 已删除，这条陷阱不复存在**）

⚠️ **落库要绕开已删行（**2026-09-09**；**2026-09-15：由「两阶段」缩为一条**）**：
- ~~**第一阶段 `parkAll` 不需要碰 `deleted = true` 的行** —— 它存在的唯一目的是腾空 `uk_erl_dimension_config_abbr`，而已删行按新谓词（`AND deleted = false`）**本就不在那个索引里**，没什么可腾的。~~（**2026-09-15 作废**：`parkAll` 整个删除，v4.31）
- **「缺席即停用」必须跳过 `deleted = true` 的行**（~~第二阶段~~ —— 现在就是唯一那个阶段） —— 已删行**永远**不出现在 `dimensions[]` 里，若照「缺席」规则处理，每一次保存都会去改一批用户看不见的行的 `status`（本身无害，但把这些行的 `updated_at` 一路推高、`savedBy` 会指向一个从没碰过它们的人）。⚠️ **真正危险的是写成整行覆盖或 upsert 时带上 `deleted` 的默认值** —— 那会把 `deleted` 冲回 `false`，**已删的维度在下一次保存后集体复活**，而页面上看起来只是「保存成功」。

- **整组替换语义**：接口 24 提交的是**完整的维度列表**，服务端不做逐条 diff、不做部分更新 —— 否则中间态必然破坏「合计 100%」。⚠️ **去版本化后“整组替换”写的是本组织的这批行本身**，**改动前的旧值不再留存**。
- **Save 按钮双条件**（§0.10-D13）：① 脏态（维度增 / 删 / 排序 / 权重 / **启停用**任一变化）② **`Active` 行**权重合计 = 100%；越界提示 `Exceeds 100% by {n}%` / `Needs {n}% more`。
- **与题库 Publish 的关系**：配置改动**不激活 Publish 按钮**，走自己的 Save；题库 Publish 也**不改维度配置** —— 但它**会读**当时 `Active` 的维度写入 §5.1.5 快照（不再是 v4.4 说的「完全无关」）。
- **Save 确认框文案（2026-09-08 反转回 v4.0 口径）**：~~「新配置从下一个尚未开始填报的期次起生效；已有提交的期次沿用其绑定的配置版本，历史分数不变」~~ → **「新配置立即全局生效，已有期次的综合分、Stage 与雷达图形状会随之变化」**。

**③ 生效：只有一份当前值，无期次绑定**

| 场景 | 取哪些维度 |
|------|------|
| 任何按期次渲染 / 计分的地方（卡片、雷达图、A3 / A4、F2、Gap 状态点、Share 门槛） | **一律读 `erl_dimension_config` 中该组织 `status = 'Active'` 的行**（**2026-09-09 补一半：且 `deleted = false`** —— 删除**不改** `status`，漏掉这半边会漏出一个用户已经删掉、且再也管理不到的维度），按 `sort_order` 排序 |
| 历史提交里出现过、今天已 `Inactive` **或已删**的维度 | 该维的名称 / 缩写由 `erl_assessment.dimension_name` / `dimension_abbr` **行上快照**还原（§5.2），或回本表读那一行（**两种情况下行都仍在** —— 这正是删除做成置位而不是 `DELETE` 的原因，§5.1.3） |
| C7 题库版本快照页 | **不读本表当前值** —— 读 `erl_question_config_dimension_version` 的发布当时快照（§5.1.5，接口 26 出参 `dimensions[]`） |
| 期次都定不下来（closed month 取不到，§7.1.2） | 不渲染任何维度，走空态 |

⚠️ **R2「历史期次永不漂移」已于 2026-09-08 正式失效**（需求方已裁决「接受漂移」）：
- 改权重会**回溯改变**已提交历史期次的综合分与 Stage —— `erl_assessment` 上有每维的 `level_score` 快照，但**权重不在快照里**，综合分是实时加权算出来的（§7.1）。
- 新增维度会让历史期次凭空多出一个「未填」的维度；`Inactive` 维度会从历史雷达图上消失。
- **§13-Q21 重新打开**，取值「改权重影响历史」。

**④ 两个破坏性动作：停用（软删）与删除（真删）**（**2026-09-08 推翻 v4.8 的「物理删除」定下软删** → **2026-09-09 需求方裁决：按「是否进入过已发布题库版本」一分为二**，§0.21）

**判据只有一条**：该 `dimension_code` **有没有出现在某个 `PUBLISHED` 题库版本的维度快照里**（`erl_question_config_dimension_version` join `erl_question_config_version`，§5.1.5）。服务端把结论作为接口 23 的 `deletable` 下发，前端据此决定行尾给哪个图标 —— **前端不自己算**，判据只有一处实现。

| `deletable` | 前端本地状态 | 行尾图标 | 落库 | 之后在哪儿 |
|---|---|---|---|---|
| `true`（**从未**进入过已发布版本） | 常规行 | **垃圾桶** = 删除 | **`deleted = true`**（`status` 不动） | **哪儿都没有** —— 主列表没有、`Deactivated Dimensions` 区块也没有，**无恢复入口** |
| `false`（进入过已发布版本） | 常规行 | **电源按钮**（`PoweroffOutlined`）= 停用 | `status = 'Inactive'`（`deleted` 不动） | `Deactivated Dimensions` 区块，行尾 **`Activate`** |
| **任意**（含 `true`） | **`isRestored`** —— 本次会话里刚从停用区 `Activate` 回来、尚未 Save | **电源按钮** = **撤销恢复** | 撤销后回到「本次不恢复」，Save 时其 code 仍进 `deactivatedCodes[]` | 回到 `Deactivated Dimensions` 区块 |

⚠️ **所以行尾图标是三态、不是二选一**（**2026-09-09 实现落地后订正**，§0.21-X14）：判据是 **`row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`**。~~`deletable ? 垃圾桶 : 电源按钮`~~ 漏掉了 `isRestored` 这一半 —— 刚恢复回来的行若照常给垃圾桶，用户想撤销刚才的恢复时，行尾**最近的那个按钮**恰好是**不可逆**的真删。撤销恢复那一支另有独立文案 `dimensionRestoredTooltip` / `undoRestoreConfirm` / OK 文案 `Undo restore`，以及独立 aria-label `Undo restore`（取值逐字见 §8.4-C6-③）。

- **两者都要二次确认**；电源按钮另带 tooltip 说明**为什么不能删**（否则用户只看到「这一行的图标跟别的行不一样」）。
- **停用（`Inactive`）那一支的行为与 2026-09-08 定的软删一字未改**：`Save` 时该维度**不出现在提交的 `dimensions[]` 里**、其 code 进 `deactivatedCodes[]`，服务端据此置 `Inactive`；**行与 `weight` 原样保留**，可再置回 `Active` 恢复。~~垃圾桶 + 二次确认后本地标为停用~~ → **2026-09-09：入口换成电源按钮**（垃圾桶另有所指）。
- **删除（`deleted = true`）那一支**：code 由 **`deletedCodes[]` 显式点名**（不是靠「缺席」表达 —— 缺席此后**只表示停用**）；行与 `weight`、`dimension_name` / `dimension_abbr` 全部原样保留，历史数据仍按 `dimension_code` 反查得到，但**所有读侧一律排除**（§5.1.3）。
- 停用或删除后剩余维度的权重合计会不足 100%，**需在同一次 Save 里补齐**。
- **已 `Inactive` 的维度**：① 不进填报页、不进当前的综合分与雷达图；② 历史提交记录照常可查（名称/缩写取评估行快照）。**已 `deleted` 的维度同 ①②** —— 区别只在配置页上看不见、也拿不回来。
- `ErlDimensionConfigStatusEnum` **改回落库枚举**：取值 `Active` / `Inactive`，就是 `erl_dimension_config.status` 列；`Retired` 灰标由列值**直接判定**，~~v4.8 的「纯派生展示态」~~ 作废（§0.14 随之失效）。⚠️ 与 v4.0 从接口 1 / 2 删掉的 `status`（`MET` / `PARTIAL` / `GAP`，§0.9-10）**不是同一个字段**。⚠️ **`deleted` 不进这个枚举**（**2026-09-09**）：它与 `status` 正交，合并成三值后「删掉一个当前已停用的维度」（可达）就没有落点了（§0.21 开头）。
- ~~**无条件允许删除**：不做「有历史数据禁止删除」的前置拦截 —— 软删下行根本不消失，拦截没有保护对象（§13-Q24 结论仍成立，但**依据由「旧版本保留」换成「软删保留」**）~~ → **2026-09-09 作废**（需求方当日裁决）。**取而代之**：
  - **拦截现在存在** —— 已进入过已发布题库版本的维度**禁止删除**（服务端硬校验，§6.4-3-⑨），只能停用。
  - **但判据不是「有无历史数据」**：那个判据会连「有人填过、但题库从没发布过」的维度也拦住 —— 那种维度删掉是**安全的**（它本就不是任何已发布版本的一部分，而 `dimension_code` 仍被占用、历史仍解得出名字）。
  - **保护对象也不是那一行**（软删/真删下行都不消失），而是**已发布题库版本的语义**：那份版本的维度快照、以及按 code 关联到它的历史（`erl_assessment` / `erl_reference_score_item` / Gap items），**必须始终解得出那个维度**。一旦它从产品里彻底消失且不可恢复，那份已发布版本就成了「引用着一个用户再也管理不到的维度」的版本。
  - ⇒ **§13-Q24 由「已关闭：无条件允许删除」改判为「有前置拦截，判据是「是否进入过已发布题库版本」」**（§13 / §0.21-X12）。§12 与 §1.2 的对应条目一并订正。
- ✅ **C7 不受维度配置变更影响（§0.17-K1 已于 2026-09-09 关闭，取值 = 整条取消，§0.22-Y3）**：~~v4.11 定的「C7 只显示今天仍在维度配置里的维度」~~ 已**整条取消** —— 需求方 2026-09-09 裁决：C7 既不隐藏「今天已不在配置里」的维度、也不再给它打 `Retired` 灰标，**连接口 23 的取数都从该页撤下**。⇒ 本节的保存流程（~~含 `parkAll` + upsert~~ → **2026-09-15：单阶段 upsert**，v4.31；停用与删除两个动作）对 C7 的展示**零影响**，C7 只读 §5.1.5 的发布当时快照。
  - ~~**2026-09-09：`deleted` 不使它自愈**（§0.21-X9）—— 能删的恰恰是「从未进入过已发布版本」的维度，而 C7 展示的只有已发布版本的快照，K1 原样保留待裁决。~~ → **同日更晚被裁决取代**：那段分析仍然正确，但 K1 没有等到自愈，是被整条取消掉的。

**⑤ 相关接口**

| 接口 | 语义（**2026-09-08**） |
|------|------|
| **接口 23** `GET /erl/dimension/config` | 返回该组织的维度配置（`dimensionCode` / `dimensionName` / `dimensionAbbr` / `sortOrder` / `weight` / **`status`** / **`deletable`**（2026-09-09 新增）/ `savedAt` / `savedBy`）。**默认只返 `Active`**；~~配置页需回看停用维度时带参返全量~~ → **2026-09-09：配置页恒带 `includeDeactivated=true`**（`Show deactivated` 开关已撤下，停用行由常显区块承载）。⚠️ **`deleted = true` 的行任何情况下都不下发**。~~v4.8：无 `status`~~ 作废；~~出参 `versionNo`~~ 删除 |
| **接口 24** `PUT /erl/dimension/config` | **整组保存**维度集合 + 排序 + 权重，校验通过即**就地替换**（缺席维度置 `Inactive`；**2026-09-09**：另按 `deletedCodes[]` 置 `deleted = true`，**只对从未进入过已发布题库版本的维度开放**）。~~生成新配置版本~~ 作废，出参无 `versionNo` |
| 接口 1 / 20 / 22 等按期次读的接口 | 维度列表与权重一律取**当前 `Active` 集合**（本节 ③），出参中的维度**是变长数组，不是固定五项** |

---

## 8. 前端设计（功能级）

### 8.1 路由（`config/routes.ts`）

| URL | component | 页面 | 变化 |
|-----|-----------|------|------|
| `/companyOverview` | `./companyOverview/home` | **A1 / A2 ERL Card** | **改存量页，不新增路由** |
| `/exitReadiness/dimension/:dimension` | `./exitReadiness/dimension` | A3 / E2（**v4.9：A5 已删除**） | 新增 |
| `/exitReadiness/scoreDetails` | `./exitReadiness/scoreDetails` | **A4 全维 Score Details** | 新增（v3.5 复活），**F2 `View` 的落地页**；**v4.4：同时是两端 ERL Card 右上 `Full View ›` 的落地页**（§0.10-D5） |
| `/exitReadiness/assessment` | `./exitReadiness/assessment` | B1（`?portal=gsv` 切 B2） | 新增 |
| `/exitReadiness/history` | `./exitReadiness/history` | B3 | 新增 |
| `/exitReadiness/history/:assessmentId` | `./exitReadiness/history/detail` | B3 单次提交详情 | 新增 |
| `/exitReadiness/benchmark` | `./exitReadiness/benchmark` | D1 基准记录页（两张卡） | 新增，仅管理端 |
| `/exitReadiness/benchmark/add` | `./exitReadiness/benchmark/add` | **D2 新增记录（独立页，非 Modal）** | 新增，仅管理端（v3.1，§0.3-3） |
| `/exitReadiness/configuration` | `./exitReadiness/configuration` | **两个顶层 Tab（v4.1，v4.4 改名）**：`Question Library`（C1 + C3 删除 + C4 拖拽 / 改 band）+ ~~`Dimension Weights`（C6 权重）~~ → **v4.4**：**`Dimension Configuration`**（C6 维度新增 / 删除 / 排序 / 权重，§0.10-D13） | 新增，**仅管理端**（PRD §3.8「仅 portfolio portal」） |
| `/exitReadiness/configuration/history` | `./exitReadiness/configuration/history` | **C7 题库版本历史**（v4.1 新增，**v4.2 改为版本快照页**） | 新增，**仅管理端**；入口为 `Question Library` Tab 的 `View history` |
| `/exitReadiness/configuration/add` | `./exitReadiness/configuration/add` | C2 | 新增 |
| `/exitReadiness/configuration/edit/:questionKey` | `./exitReadiness/configuration/edit` | C3 | 新增（**v3.6 由 `:id` 改为 `:questionKey`** —— §6.4 的 C 模块写接口一律按 `questionKey` 定位，写时复制后草稿行是新 `id`，用 `id` 进页面必然失配，§0.8-4） |

**对 v2.1 的删除**：
- ❌ `/exitReadiness`（Dashboard）—— PRD §3.1「不设独立 Exit Readiness 落地页」。
- ~~❌ `/exitReadiness/scoreDetails`（A4 全维明细）~~ —— **v3.5 恢复**（2026-08-28 裁决，§0.7-2）。**注意二者无关**：恢复的只是 A4 这一个页面，`/exitReadiness` Dashboard 仍不做。

**F2 不新增路由** —— 它是 `/company`（`./portfolioCompanies/home`）页内的**第 6 个 Tab**（`key='6'`）。

**菜单入口**（PRD §3.1 / §3.8）：
- ERL 展示入口**只在 Company Overview 的 ERL Card 上**，主导航不新增一级菜单。ERL Card 内部下钻的三个入口（**v4.4** 定档）：右上 `Full View ›` → A4（两端）、维度行 `View Details →` → A3、雷达图下方 `Benchmarkit & Top GSV Quartile ›` → D1（仅管理端）。
- **ERL Configuration 挂顶部导航右侧下拉菜单**（PRD §3.8），**仅管理端可见**；其内容按调用者 `organization_id` 隔离（v4.0，§0.9-7）。
- B1/B2 填报入口在 **Assessments 区块**内（PRD §3.3 / §3.4）；另从维度详情页的 `+ New`、**以及 A4 每张维度卡卡头的 `Add New`（v4.4，§0.10-D5）** 进入，两者均带 `?dimension={code}`（填报单元＝单个维度，§0.10-R1）。
- C 模块路由对管理端可见，公司端由菜单与路由守卫双重拦截。

#### 8.1.1 ⚠️ 菜单入口的落地前提（**v4.0 补，此前是文档缺口**）

「挂顶部下拉菜单」不是写一行前端代码就完事 —— 该下拉是**数据驱动**的，缺一条库记录入口就不出现。链路：

```
BasicLayout 里硬编码的 menuRight_SuperAdmin（含 `ERL Configuration`）
        │
        ├── 门 1：userData.roleType === 1 才取用这份清单
        │
        └── 门 2：getVerifyRoles() 把它与后端菜单权限按 `path` **求交集**
                  └── POST /api/web/menus/getMenuTreeByRoleId
                        └── select m.* from menu m
                              join r_role_menu rm on m.id = rm.menu_id
                              join r_user_role  ur on rm.role_id = ur.role_id
                            where ur.user_id = ?
                        └── buildTree(...)：**只返回 pid = '0' 的根节点**
```

**因此必须满足三个条件，缺一个菜单就不显示**：

| # | 条件 | 落地位置 |
|:--:|------|----------|
| 1 | `menu` 表有 `path = '/exitReadiness/configuration'` 的行，且 **`pid = '0'`**（根节点） | **管理后台菜单配置**（**v4.14 改**：原先由 sprint118 的菜单迁移脚本落库，该脚本已删除） |
| 2 | 该菜单经 `r_role_menu` 授权给用户的角色（后台配菜单时授权给超管角色，即原脚本按 `role.is_super_admin = true` 授权的那批） | 同上 |
| 3 | 清两处缓存后重新登录 | 见下 |

- **`pid` 必须是 `'0'`**：`MenuServiceImpl.buildTree` 只把 `pid = '0'` 的行放进返回数组顶层，而 `getVerifyRoles` **只比较顶层 `path`、不递归 `menuDtoList`**。挂到某个父菜单下会被嵌进子级，下拉里依然不显示。
- **两处缓存**：① 服务端 `MenuServiceImpl.findAllByUserId` 带 `@Cacheable(key = "'menu:user:' + #userId")`；② 浏览器 `localStorage.roles` + 同名 cookie（`utils.ts` 的 `saveRoles`），且 `BasicLayout` 只在 `!rolesData || length < 1` 时才重新拉。**两处都不清，改了库也不生效。**
- **基准页 `/exitReadiness/benchmark` 不需要菜单行** —— 它不在那份下拉清单里。~~入口是维度详情页 / A4 页内链接。~~ → **v4.4 订正**（§0.10-D7）：这处描述是**既有文档缺口** —— §8.4 的交互表里 A3、A4 **从未定义过**这条链接，按 v4.3 文档实现，`/exitReadiness/benchmark` 与 `/benchmark/add` 站内**不可达**。本版按 PRD §3.5（`9a203ce`）定档：**入口是 ERL Card 雷达图正下方的链接 `Benchmarkit & Top GSV Quartile ›`**（→ `/exitReadiness/benchmark?companyId=`**`[&period={period}]`**，**v4.25 补期次**、由接口 1 的 `benchmarkUrl` 下发，§0.29-Z5），**仅管理端渲染**（与雷达图同条件）；`/benchmark/add` 由 D1 页内 `+ Add New` 进入。~~A4 页尾仍只有**只读的基准折叠卡**，不再声称它是基准页的入口。~~ → **2026-09-09 作废**（§0.24-Z4）：A4 的基准由页尾折叠卡改为**末位 Tab**，卡头按原型加了 `+ Add New` / `View history`，**A4 由此成为基准页的第二个站内入口**（**v4.25**：这两条同样带 `&period=`，§0.29-Z1）。菜单口径不变 —— 基准页仍不需要菜单行。

**路由守卫（v4.0 补实现）**：`SecurityLayout.tsx` 对 `/exitReadiness/configuration*` 与 `/exitReadiness/benchmark*` 拦截 `roleType > 1`（公司端）→ 重定向回 Company Overview。这补上了本节「双重拦截」承诺的后一半（此前**只有菜单一半**，直接敲 URL 谁都能进）。

> **为什么守卫按端类型判、不按菜单权限判**：菜单权限决定「入口显不显示」；基准页本就没有菜单入口，而配置页若也压在菜单权限上，一旦**菜单未在管理后台配置**（或配错成非根节点、忘了授权），管理员会被彻底锁在门外。PRD §3.8 的原话只是「仅 portfolio portal」，端类型判定已足够。后端另有一层：C 模块写接口与 D 模块全部接口一律校验管理端（§4.3）。

> ⚠️ **端类型判定必须用 `roleType`，不得用 `isAdminEnd()`**（v4.0 订正，见 §4.1 末段）。
- **A4 无菜单入口**（v3.5，**v4.4 修订**）：A4 仍**不进**顶部下拉菜单，但页内入口已扩为两个。~~唯一入口是 F2 ERL Tab 的 `View`（管理端专属）。公司端有权限访问本公司的 A4，但 V1 不提供任何界面入口（§13-Q17 已确认）——**不要**为此在 ERL Card 或主导航上自行加链接。~~ → **v4.4 作废**（§0.10-D5，PRD `57225d2` 推翻 §13-Q17）：**ERL Card 右上角的 `Full View ›` 就是 A4 的入口，两端都渲染**（PRD §3.5 写「仅 Company portal」，但 2026-09-06 原型截图显示组合端卡片同样有 `Full View`，按原型落，并列入 PRD 回写 M9）。故 A4 现有两个入口：① 两端 ERL Card 的 `Full View ›`；② F2 ERL Tab 的 `View →`（管理端）。此前的「不要自行加链接」禁令**撤销**。

### 8.2 目录结构

遵循 `CIOaas-web/CLAUDE.md`「同域多功能归入域文件夹作第二层」「域根须有 README.md」「转发式 index.tsx 仅限路由页面入口」：

```
src/pages/exitReadiness/
├── README.md                      域文档（职责 / 目录 / 域内要求）
├── components/                    域级共享（v4.0 调整）：
│                                  ErlRadarChart(A2，仅管理端渲染)、DimensionScoreRow、
│                                  LevelAccordion(B，逐级解锁分组：CLEARED/ACTIVE/BLOCKED/LOCKED)、
│                                  YesNoField(B，唯一的作答控件)、
│                                  QuestionRow、  ← v4.9：ScoringCriteriaModal(A5) 已删除，
│                                    题目行不再有 How It's Scored? 入口（§0.15）
│                                  EvidenceNoteField、AttachmentUploader(10MB 校验)、
│                                  GapAnalysisPanel(E1)、PriorityGapsPanel(E2)、  ← v4.4：E 已回归 V1，不再可摘除
│                                  GapAnalysisDetailModal(A1「View details」弹框，按维度分区，v4.4 新增)、
│                                  ShareToFounderButton(A1「Share to founder」，门槛未达成置灰，v4.4 新增)、
│                                  DimensionConfigForm(C6，维度新增/删除/排序/权重 + 100% 校验，
│                                    **v4.1：只有数字输入、无滑条**；**v4.4 由 WeightForm 更名扩容**，§0.10-D13)、
│                                  PeriodSelect、PortalTabs、
│                                  SubmissionMetaBar(A3 / B3 元数据栏)、AttachedFilesCard、
                                  ❌ **v4.20 移出本层**：~~DimensionQuestionsAccordion(A4)、BenchmarkPanel(A4)~~
                                     —— 两者都只有 A4 用，现为 `scoreDetails/components/` 下的私有组件
                                     （且前者已不是 Accordion），见下 `scoreDetails/` 一行
│                                  QuestionSetUpdatedModal(B 强阻断题库更新弹窗，2026-09-15 取代原 QuestionSetUpdatedBanner，§0.10-D10)、
│                                  useDimensionConfig(**v4.4 新增**：读接口 1/23 的维度配置，
│                                    维度名/缩写/排序/主题色的唯一来源)、
│                                  types.ts
│                                  ❌ v4.0 删除：EraProgressBar（1–9 标度图例）、StatusBadge（状态摘要）、
│                                     DataSourcesCadenceCard、ScoreSelect（1–9 打分控件）
│                                  ❌ **v4.4 删除**：`constants.ts` 的静态 `DIMENSIONS` 映射 —— 维度集合已是
│                                     租户级可版本化配置（§0.10-D1 / R2），编译期常量必然与配置漂移；
│                                     维度元数据一律**接口驱动**（`useDimensionConfig`），
│                                     `constants.ts` 仅保留与维度无关的常量（Era 配色、附件上限等）
├── dimension/{index.tsx, DimensionPage.tsx, hooks/, components/}
├── scoreDetails/{index.tsx, ScoreDetailsPage.tsx, ScoreDetailsPage.test.tsx, hooks/, components/}   A4（v3.5）
│                                  components/ 内（**v4.20**，均为 A4 私有）：
│                                    DimensionQuestionsCard.tsx（~~DimensionQuestionsAccordion~~ —— 折叠卡已改
│                                      横向 Tab，一次只渲染一维，卡片本身不再折叠，§0.24-Z3）、
│                                    BenchmarkPanel.tsx（末位基准 Tab 的内容，§0.24-Z4）、
│                                    ScoreQuestionRow.tsx（三态徽章 + NOTES / ATTACHMENTS 块，§0.24-Z10 / Z11）
├── assessment/{index.tsx, AssessmentPage.tsx, hooks/, components/}
├── history/{index.tsx, HistoryPage.tsx, detail/, hooks/, components/}
├── benchmark/{index.tsx, BenchmarkPage.tsx, add/, hooks/, components/}
│                                  components/ 内含 BenchmarkDimensionTable（D1 两张卡与 D2 表单共用的
│                                    **按维度行结构**，行数随配置维度动态，**v4.4 由「五维行结构」改**）
└── configuration/{index.tsx, ConfigurationPage.tsx, add/, edit/, history/, hooks/, components/}
                                   ConfigurationPage.tsx 组装两个顶层 Tab（v4.1，**v4.4 第二 Tab 改名扩容**）：
                                     Question Library → 维度 Tab（按配置动态，非固定五个）+ QuestionLibraryTable
                                       （表格 + Era band 分组行 + 拖拽列 + 行内 Era band 下拉）
                                     ~~Dimension Weights → WeightForm~~ → **v4.4**：
                                       **Dimension Configuration → DimensionConfigForm**（维度行的新增 / 删除 /
                                       拖拽排序 / 权重输入，整组 Save 走接口 24，§0.10-D13）
                                   history/ 为 C7 版本历史页（v4.1；**v4.2 改为版本快照页** ——
                                     页头版本下拉取接口 25（**2026-09-09：只列已发布版本，草稿不进下拉**，§0.22-Y1）、只读题目表取接口 26，**v4.4：卡片数按该版本的 §5.1.5 逐维快照（2026-09-08 换源）/ 原「绑定的
                                     维度配置渲染，不再恒五张**；**v4.10：该维度集合随接口 26 出参 `dimensions[]` 下发**（**2026-09-08**：改取 §5.1.5 快照表））

改存量页：
src/pages/companyOverview/home/
├── CompanyOverviewPage.tsx        DI 卡区块 → 渲染 ErlCard；DI 分支保留但不再进入
└── components/ErlCard/            A1 卡片（含 A2 雷达图，复用 exitReadiness/components/）

src/pages/portfolioCompanies/erl/  F2 Tab 内容组件（与 Benchmarking/ Issues/ 平级）
├── ErlTab.tsx                     纯展示表格（非路由 Tab 内容，不写转发 index.tsx）
├── ErlTab.less
└── hooks/useErlPortfolio.ts       取数 + `currentQuarterPeriod()`（无 query 状态，只随 portfolioId 变）
```

分层口径按 `standards/architecture.md` §3：`index.tsx` 只转发；`XxxPage.tsx` 组装 hooks 与 components；**业务逻辑（调 API / 管状态）只写在 `hooks/`，`components/` 收 DTO props 不调 API**。

> ErlCard 放 `companyOverview/home/components/` 而非 `src/components/` —— 当前只此一处使用（YAGNI）；其内部复用的雷达图等下沉在 `exitReadiness/components/`，跨域 import 只允许 import 该域的公开组件与 `erlService`。

### 8.3 服务层（`src/services/`）

```
services/api/exitReadiness/       erlApi.ts / request.ts / response.ts / dto.ts / README.md
services/service/exitReadiness/   erlService.ts   （Response ↔ DTO 转换，跨页面复用）
```

F2 的 `GET /erl/portfolio`、ERL Card 的 `GET /erl/card` 均归入 `exitReadiness/` 域（**按后端接口归域，不按页面归域**）。

**v4.4 新增 / 变更的服务方法**（编号见 §6）：

| 服务方法 | 接口 | 用途 |
|---|---|---|
| `shareGapAnalysis({ companyId, period })` | **接口 27（新）** `POST /erl/gapAnalysis/share` | A1 Gap 区块的 `Share to founder`，**仅管理端**；成功后本地把 `shared` 置 true 并把按钮切为已分享态（§0.10-D3） |
| `discardDraft({ companyId, period, portal, dimension })` | **接口 28（新）** `DELETE /erl/assessment/draft` | B 填报页 `Reset`：清空本次草稿的全部答案与附件、`unlockedLevel` 回 1；调用前必须二次确认（§0.10-D8） |
| `getDimensionConfig()` | **接口 23（语义变更）** `GET /erl/dimension/config` | ~~读五维权重~~ → **当前 `status = 'Active'` 的维度集合**（维度列表 + `sortOrder` + `weight`；**v4.8：无 `status`**）；`useDimensionConfig` 与 C6 共用（§0.10-D13 / §0.14） |
| `saveDimensionConfig(items)` | **接口 24（语义变更）** `PUT /erl/dimension/config` | ~~保存五维权重~~ → **整组保存**维度集合 + 排序 + 权重，服务端校验 **`Active` 行**合计 = 100.00；~~并生成新配置版本~~ → **2026-09-08：就地整组替换，缺席维度置 `Inactive`，不产生版本**（§0.10-D13） |
| `getAssessmentHistoryDetail(assessmentId, { dimension })` | 接口 8（补入参） | B3 从带维度的历史列表进入时只渲染该维度（§0.10-D12） |

### 8.4 关键交互

| 交互 | 设计 | PRD 依据 |
|------|------|------|
| **A1 ERL Card 内容**（v4.0 改，**v4.4 重写**） | **卡头右上 `Full View ›`** → A4（`/exitReadiness/scoreDetails?companyId={id}&period={period}`），**两端都渲染**（§0.10-D5，2026-09-06 原型）。卡体自上而下：**`Overall Score`**（**v4.4 文案定档，全站不再出现 `Composite Score`**，§0.10-D14；**加权** `X/9`，tooltip 列出所用权重）+ 当前 Stage 徽章 + **Gap 区块**（见下一行；~~E 待定期间隐藏~~ → **v4.4 作废**：Goldie 已回归 V1，常驻渲染，§0.10-D2）+ **维度列表**（~~5 维列表~~ → **v4.4**：按接口 1 返回的维度配置**动态渲染**，条数不固定，§0.10-D1；每行：维度分 `n/9` **整数** + `Level n` 标注 + `View Details →`）+ BPMM 参考数字（1–5）+ **雷达图（仅管理端）** + **雷达图正下方链接 `Benchmarkit & Top GSV Quartile ›`**（→ `/exitReadiness/benchmark?companyId=`**`[&period={period}]`**，**v4.25 补期次**、整条仍由接口 1 的 `benchmarkUrl` 下发，§0.29-Z5；**仅管理端**，与雷达图同渲染条件，§0.10-D7）。**管理端额外**：每维 GSV 分与 Perception Gap。❌ 删除状态徽章（§0.9-10） | §3.1 / §3.5 + 2026-09-06 原型 |
| **A1 Gap 区块**（**v4.4 全行新增，按 2026-09-06 原型截图定档**，§0.10-D4） | 区块头：标题 **`Gap Analysis & Suggested Actions`** + **`AI GENERATED`** 标签；右侧两个按钮 —— **`View details`**（弹 `GapAnalysisDetailModal`，**按维度分区**列出该维的 gap 与 `actions[{title, why}]`）、**`Share to founder`**（**仅管理端**，调接口 27；**门槛未达成时置灰**；~~tooltip 说明还差哪些维度~~ → **v4.32 作废**（需求方 2026-09-15 圈图撤下「`Waiting on both submissions: …`」），置灰时**不挂任何 tooltip**，还差哪些维度改由区块底部那句常驻提示承担）。<br>区块体：**期次 chip**（如 `Q2 2026`，取接口 17 的 `period`）+ 计数文案 **`{n} of {total} dimensions have gap analysis for {period}`**（`total` = 当前 `status = 'Active'` 的维度集合的维度数，**不写死 5**）；其下**每维一张小卡**，卡内一个圆点 + 一行文字，**四态**（**v4.58 补第四态**，P4 / §0.32-Y5；优先级**写死**、不靠隐式短路）：<br>· 灰点 + `Not submitted` —— `bothSubmitted = false`<br>· **黄点 + `Question set mismatch`** —— `questionSetMismatch = true`（两端答的不是同一套题 ⇒ 不可比，该维未送进分析）<br>· 绿点 + `Gap analysis ready` —— `hasGap = true`<br>· 绿点 + `No Gap` —— 其余<br>⚠️ **`bothSubmitted` / `questionSetMismatch` / `hasGap` 是三条互相独立的信息，前端不要合并成一个枚举字段**；**mismatch 必须排在 `hasGap` 之前** —— 旧产物未被本轮覆盖时两者会同真，此时显示 mismatch、旧条目不渲染。<br>区块底部提示：**`Share unlocks once gap analysis is available for all {total} dimensions in {period}.`**<br>数据全部取**接口 17** 的 `shared` + `dimensions[].{code, abbr, bothSubmitted, questionSetMismatch, mismatchSide, hasGap}`（后两个 v4.58 新增）。<br>❌ **删除 Strengths 相关展示**：`strengths[]` 出参与「优势」小节一并摘除（§0.10-D4），本区块只呈现 gap 与建议动作 | 2026-09-06 ERL Card 原型 + PRD §3.6 |
| **A1 Share 后的状态与复位**（**v4.4 新增**） | ~~已分享时按钮切为 `Shared`（禁用）~~ → **v4.62 改判**（§0.36-H1）：**按钮文案恒为 `Share to founder`，已分享只置灰不改字**~~+ 次级文字 `Shared {time} by {name}`~~ → **v4.60 撤下次级文字**（§0.34-Y1，两端都不显示；按钮态不变）；**任一端重新提交触发重生成后 `shared` 复位为 `false`**，按钮回到可点态，并在区块顶部提示 **`Content updated — reshare to founder.`**（§0.10-D3 新边界）。**公司端**：`shared = false` 时接口 17 直接返回空态，卡片内该区块显示 `No gap analysis shared yet.`，**不渲染** `View details` / `Share to founder` | 本设计（§0.10-D3） |
| **A1 卡片位置**（v4.0 改，**v4.3 订正**） | 占据**原 DI 卡片的位置与栅格宽度**，即两列布局的**右列**（DI 下移到左列 FI 之后，§8.6）；与左列 Financial Intelligence 卡等宽、顶部对齐 | §3.1 |
| **A1 公司端裁剪**（**v4.0 新增，v4.4 补两条**） | 公司端卡片**不渲染**：GSV 维度分列、Perception Gap 列、雷达图、**雷达图下方的 `Benchmarkit & Top GSV Quartile ›` 链接**（v4.4，与雷达图同条件）、**Gap 区块的 `Share to founder` 按钮**（v4.4）。列宽随之收缩为「维度名 + Founder 分 + View Details」三列，**不留空列**。⚠️ **`Full View ›` 两端都渲染**，不在裁剪之列（§0.10-D5） | §3.5「创始人只能查看自己的分数」「该图仅在 Portfolio 端显示」 + §0.10-D5 / D7 |
| **A2 雷达图规范** | **仅线条无填充**、每条序列不同色、**有图例**、**中心轴隐藏**；~~5 个顶点标注五维~~ → **v4.4**：**顶点数与顺序按当前 `status = 'Active'` 的维度集合动态生成**（`sortOrder` 决定顶点顺序，§0.10-D1）；**v4.60：维度数 < 3 时整块不渲染**（§0.34-Y2）；域 `0–9`（**v4.0：含 0**）；**悬停数据点显示该维度 + 该 perspective 的精确分数**。**v4.0：仅在管理端渲染** | §3.5 |
| **A2 序列可扩展** | `series[]` 由后端下发，前端按数组渲染，**不硬编码 4 条** —— 后续新增 perspective 无需改前端 | §3.5「预留后续新增 perspective 的能力」 |
| **A3 模板参数化**（**v4.4 改为接口驱动**） | ~~维度名称、缩写、简介、主题色收在 `components/constants.ts` 的 `DIMENSIONS` 映射~~ → **v4.4 作废**（§0.10-D1）：维度已是租户级可版本化配置，编译期常量必然与配置漂移。改为 **`useDimensionConfig` 从接口取维度元数据**（`code` / `name` / `abbr` / `sortOrder`），页面按 `:dimension` 在返回列表里查；`:dimensionCode` 不在配置表内（压根没这个 code）时走 404 空态；**2026-09-08：`status = 'Inactive'` 的维度不走 404**（⚠️ 实现注意：`useDimensionConfig` 走的接口 23 **默认只返 `Active`**，照旧实现停用维度恰好查不到、恰好走 404，与本条相反 —— A3 需**单独带 `includeDeactivated=true` 取配置**，或改由接口 2 的 `header` 直接下发该维元数据（更省一次请求）） —— 行仍在表里，历史提交照常渲染并标 `Retired`，仅**不允许新建填报**。**禁止**按维度硬编码分支文案 | §3.2「同一套模板，通过 dimension 参数驱动」 |
| **A3 Founder / GSV Tab** | 双 Tab 切换逐题明细；**公司端不渲染 GSV Tab**（且后端拒绝该请求） | §3.2 |
| **A3 元数据栏**（**2026-09-20 补渲染门槛**） | Period / Submitted By / Role / Submitted At；**该端该期次无提交（`submission == null`）时整条不渲染**（需求方 2026-09-20 圈图）—— ~~四格全占位符、只 Period 有值~~，屏上只留下方那句 `No {端} submission for this period.`。组件 `SubmissionMetaBar` 的 `submission` 入参随之收紧为**非空**、`fallbackPeriod` 入参删除。<br>⚠️ **A4 卡内那份四格不跟这条**（§9「A4 该端在该期次无提交」行仍按原口径：`PERIOD` 回退当前期次、其余三格 `—`）—— 需求方只圈了 A3，且两页组件本就不同份 | §3.2 |
| **A3 页头分数**（**v4.0 新增**） | `{n} questions · {m} answered` + 维度分 `{level}/9`（整数）+ `Level {n} · {Era 名}` 徽章（`0` 分显示灰色 `Not yet Stage 1`）+ `stopped at Level {t}`（九级全通显示 `All levels cleared`）。**管理端另并列 GSV 分与 Perception Gap；公司端两者均不渲染** | §3.1 / §3.2 / §3.5 |
| **A3 `View history`**（**v4.4 改口径**，**v4.21 补期次**） | 跳 `/exitReadiness/history?companyId={id}&period={period}&dimension={dim}`（~~`?dimension={dim}`~~ —— **v4.21 补 `period`**：本页当前期次一并透传，供 B3 面包屑原路回到同一期，§0.25-Z2），**限定当前维度**。~~记录条数不变（评估整卷提交），`Completion` 与分数切为该维度口径~~ → **v4.4 作废**：提交单元已是**单个维度**（§0.10-R1），列表天然只有该维的记录；`Completion` 列已删除（§0.10-D12），分数列即该维 Overall Score。列表页头仍标注当前维度 + 清除入口（口径见 §6.3 接口 7） | §3.2 |
| **A3 `+ New`**（v3.6 补锚点，**v4.4 改**） | 公司端跳 B1、管理端跳 B2，带当前 `period` 预选 + **`?dimension={code}`**。~~**问卷恒为整卷**（PRD §3.3 题库按五维组织、§3.9 的 `45/45` 均是整卷口径），入口在维度页、进去仍填整卷（§0.8-11）~~ → **v4.4 作废**（§0.10-R1，需求方 2026-09-06 裁决）：**填报单元＝单个维度**，从维度页进去**只填该维度**，PRD §3.2「发起该维度新一轮评估」现按字面落地。原 `?anchor={dimension}` 的「滚动并展开该维度分组」不再需要 | §3.2 / §3.3 + §0.10-R1 |
| **A3 面包屑**（**v4.4 改依据**） | `Exit Readiness ›〔Dimension Name〕`，返回落回 Company Overview。**功能不变**，依据由 ~~§3.1 / §4~~ 改标 **§4**（§0.10-D17：PRD §3.1 的面包屑 UX 要点已于 2026-09-03 删除，§四「导航一致性」仍保留；PRD 自身矛盾列入回写 M6） | **§4**（§3.1 的 UX 要点已于 2026-09-03 删除） |
| **A3 维度间跳转**（**v4.4 动态化**） | 页头提供维度 chip 切换器，不必回卡片；~~5 个 chip~~ → **chip 数量与顺序按当前 `status = 'Active'` 的维度集合渲染**（§0.10-D1） | 本设计（模板页自然延伸） |
| **A4 可达性**（**v4.4 新增**） | ~~公司端有权限但 V1 不提供入口（§13-Q17）~~ → **v4.4 作废**（§0.10-D5，PRD `57225d2`）：**公司端与组合端都可达**。入口：两端 ERL Card 右上 `Full View ›`；组合端另有 F2 ERL Tab 的 `View →`。页面按端类型裁剪（见下「A4 双端呈现」「A4 公司端」） | PRD §3.5 / §3.7 + 2026-09-06 原型 |
| **A4 页面结构**（v3.5，v3.6 补页头分数，v4.0 综合分改加权，v4.4 改按钮位置，**v4.20 照原型整页重排**） | ~~自上而下：面包屑 → H1 `Score Details` + **加权 `Overall Score` `X/9` + Stage 徽章** → 双端呈现区 → 四列元数据栏 → 维度折叠卡 → 页尾基准折叠卡~~ → **v4.20 作废**（§0.24，需求方裁决「严格照原型」）。**现行结构自上而下**：**两级面包屑** `Portfolio Companies › Score Details` → **H1 `Score Details`（页头到此为止：无综合分、无 Era/Stage 徽章）** → **维度横向 Tab**（标签 = `dimensions[].abbr`，顺序与张数按接口 22 返回，§0.10-D1；**末位是基准 Tab**）→ **`GSV` / `Founder` 药丸切换**（组合端才有，`GSV` 在前且默认选中）→ **当前维度的单张卡**（卡头 + 四格元数据栏 + 该维逐题列表）；容器宽度与 A3 一致。⚠️ **页级 `+ New` / `View history` 仍不存在**（v4.4 已下沉到卡头，§0.10-D5）；⚠️ **接口 22 的 `header` 出参未删**，只是本页不再渲染 —— **契约零变更**；⚠️ ~~不渲染的只有 `overallScore` / `stage` / `era` 三项，第四项 `weightsApplied` 仍在用~~ → **v4.22 作废**（§0.26-Z1）：末位基准 Tab 表尾那行加权 `Average` 已撤下 ⇒ **`header` 四项本页一项都不渲染**（出参照常下发） | 原型 `/readiness/overall`（2026-09-09 重抓）+ ~~§0.8-12~~ + §0.9-2 + §0.10-D5 + §0.24 |
| **A4 面包屑**（**v4.20 改**） | ~~`Portfolio Companies › {公司名} › Exit Readiness › Score Details`~~ → **v4.20 作废**（§0.24-Z1，原型只有两级）：**`Portfolio Companies › Score Details`** —— 中间不再夹公司名，首级回组合公司列表，末级不可点。公司名改由页内内容承载（进页路径本就带 `companyId`） | 原型（2026-09-09 重抓） |
| **A4 双端呈现**（~~双端 Tab~~ → v4.4 同屏并列 → **v4.20 改回端切换**） | ~~**组合端同屏并列**两端（页头两组元数据、卡头并列 `Founder {level}/9` 与 `GSV {level}/9`、逐题行右侧并列两个徽章）~~ → ❌ **v4.20 作废**（§0.24-Z5，需求方裁决「严格照原型」）：<br>· **组合端**：维度 Tab 下方一组 **`GSV` / `Founder` 药丸**，**`GSV` 在前且默认选中**（原型口径，与 A3 的 `PORTAL_TABS` 顺序相反）；选中哪端就只渲染哪端。<br>· ⚠️ **取数一字不变**：管理端**仍不传 `portal`，一次请求取回双端**（`dimensions[].portals[]`，§6.2.1），**切药丸只在本地换切片，不重新请求接口 22** —— 「同时呈现 GSV 与 Founder 的记录」（PRD §3.7）由此满足。某端该期次无提交时该侧走空态、不报错。<br>· **卡内空态文案按端生成**（`noPortalSubmissionText(portal)`）：**`No GSV submission for this period.`** / **`No Founder submission for this period.`** —— 管理端取**当前选中的药丸**，公司端恒 `Founder`。⚠️ **不要在卡内用 `No assessment for {period} yet.`** —— 管理端一次取双端，「GSV 有、Founder 没有」是常态，说「整个期次没评估」是错的；那句现在**只用于两处**：页顶的提示条（该期次两端皆无提交）与「一个维度都没有」时的整页空态。<br>· **公司端**：只有 Founder 侧，**不渲染药丸、不渲染 GSV 内容**（后端同样拒绝 `portal=GSV`，§4.2 / §4.3） | PRD §3.7 + 原型（2026-09-09 重抓）+ §0.24-Z5 |
| **A4 元数据栏**（v4.4 改，**v4.20 定位**） | 四格 **`PERIOD` / `SUBMITTED BY` / `ROLE` / `SUBMITTED AT`**（大写小标签），**渲染在维度卡内、不在页级** —— ~~页级四列元数据栏~~ / ~~组合端两行并列~~ 均**取消**（§0.24-Z6）。理由不变且更强：维度级提交后**同一期次的不同维度可能绑不同题库版本、不同提交人与提交时间**（§0.10-R1），页级根本取不到一份正确的元数据；组合端切药丸时这四格随所选端整体切换。⚠️ ~~右侧以次级文字追加 `Question set v{n}`~~ → **v4.20 一并撤下**（§0.24-Z6，原型的四格里没有这一项）：A4 不再显示题集版本号；**该标注在 A3 页头、历史列表与 C7 仍在**，「按 `erl_question_config_version_id` 渲染」的口径本身不变 | 原型（2026-09-09 重抓）+ §0.10-R1 |
| **A4 维度卡**（~~折叠卡~~ → **v4.20 改横向 Tab**；v4.4 卡头加两个入口） | ~~每维一张折叠卡，默认只展开第一张，其余收起~~ → ❌ **v4.20 作废**（§0.24-Z3）：**维度改横向 Tab，一次只渲染一维** —— Tab 标签取 `dimensions[].abbr`，**顺序与张数仍按接口 22 返回**（v4.4-D1 动态维度口径不变），默认选中第一项。<br>卡头 = 缩写徽章 + `{全称} ({缩写})` + **`{总数} questions`**（~~`{m} answered / {n} questions`~~ → **v4.20 只报总题数**，§0.24-Z8：「已答数」与「stopped at Level N」在 A4 上不再呈现，**其它页面不受影响**）+ **`+ Add New`**（**仅 `GSV` 药丸下渲染**，公司端单端模式照常，§0.24-Z9）+ **`View history`**（注意 h 小写，原型原文；~~`View History`~~）；`dimension.status === 'RETIRED'` 的 **`Retired` 灰标在 A4 保留**（口径不变，§0.22 只撤了 C7 那一处）。<br>· 两个入口的 URL **一律取接口 22 出参 `addNewUrl` / `historyUrl`，前端不拼路径**（这条不变）；为 `null` 时不渲染；⚠️ **v4.21 补**：这两条出参的**取值**各多一个 query 参数 —— `addNewUrl` 在 GSV 卷上带 `&portal=gsv`、`historyUrl` 带 `&period=`（形状见 §6 接口 22 / §0.25），**字段集与「前端不拼路径」不变**<br>· 卡体 = 四格元数据栏（见上行）+ 该维逐题列表 | 原型（2026-09-09 重抓）+ §3.3 + PRD §3.5 / §3.7 + §0.24 |
| **A4 逐题行**（v4.0 改，v4.9 去掉 A5 入口，**v4.20 独立为 `ScoreQuestionRow`**） | 题干 + 次级行 **`{eraLabel} · Source: {evidenceSource}`**（level 信息在此，**按 level 分组的组头连同 ✓ / `Stopped here` 一并移除**，§0.24-Z7）+ 右侧**作答徽章三态**（**三态不得合并**，§0.24-Z10）：`Yes` 绿丸 / `No` 红丸 / `yesNo === null` **灰圈减号 `Not answered`**。<br>备注与附件是题干下方两个**大写小标签块** `NOTES` / `ATTACHMENTS`；**附件 chip 显示 `{文件名} {体积}` 并带下载按钮**，下载走既有 `storageService.getFileLink(fileId)` 现取预签名 GET 链接（**无新接口**，§0.24-Z11）。<br>⚠️ **v4.20 起 A4 不再与 A3 复用同一个 `QuestionRow`**：A3 是可作答的填报行、A4 是只读明细行，两者的原型形态已分叉 —— A4 侧为 `ScoreQuestionRow.tsx`（同时替掉 v4.4 同屏并列时期的 `DualQuestionRow.tsx`，该组件删除） | 原型（2026-09-09 重抓）+ §3.2 / §3.3 |
| **A4 基准**（~~页尾折叠卡~~ → **v4.20 改末位 Tab**） | ~~页尾折叠卡 `Benchmarkit & Top GSV Quartile`（徽章 `BQ`），默认收起~~ → **v4.20 作废**（§0.24-Z4）：**维度 Tab 的末位再挂一个基准 Tab**，标题改原型原文 **`External Benchmarks & Top GSV Quartile`**（~~`Benchmarkit & Top GSV Quartile`~~），~~卡内多一行说明 `Reference scores recorded for each Exit Readiness dimension (1-9). These feed the dimension radar.`~~ → **2026-09-20 该行说明撤下**（需求方圈图；卡内直接是表格 / 空态）；内容仍是**按维度的明细表**（行数随维度集合，§0.10-D1），复用 D1 的 `BenchmarkDimensionTable`；列头为 `DIMENSION` / `EXTERNAL BENCHMARKS` / `TOP GSV QUARTILE`（2026-09-09 按原型改名，**D1 同步**；~~`(1-9)`~~ 后缀 2026-09-10 去掉，§0.26-Z2），~~**表尾另有一行 `Average`**（加权：Σ 维度分 × 该维占比，一位小数，无 `/9` 分母；**仅 A4 渲染**，D1 无权重数据故不传、不出该行）~~ → **v4.22 作废**（§0.26-Z1，需求方 2026-09-10 圈图）：**表尾整行撤下**，A4 与 D1 / 基准记录详情页 一样只剩明细行，组件的 `weights` 入参一并删除。**该 Tab 仅管理端渲染**（口径不变，只是由「整卡不渲染」变成「Tab 不渲染」；后端对公司端亦不下发，§4.3）。⚠️ **判据是端类型而非 `benchmark == null`**（2026-09-09 联调订正，§0.24-Z4）—— 管理端但该期次没有基准记录时后端同样发 `null`，此时 Tab 照常在、卡内走空态 `No benchmark records yet.`；管理端切到 `Founder` 药丸时该 Tab 只显示一句 `External Benchmarks & Top GSV Quartile is recorded by GSV only.`。~~⚠️ 这是**只读 Tab**，不是基准页的入口~~ → **2026-09-09 作废**（§0.24-Z4）：卡头右侧按原型加 **`+ Add New`**（→ D2 ~~`/exitReadiness/benchmark/add?companyId=`~~）与 **`View history`**（→ D1 ~~`/exitReadiness/benchmark?companyId=`~~），于是 A4 成为基准页的**第二个**入口。**v4.25 两条都补期次**（§0.29-Z1）：`?companyId={id}`**`[&period={期次}]`**（期次空则整段不拼、值走 `encodeURIComponent`）—— ~~只带 `companyId`~~ 作废，理由：D1 的面包屑第二级「Score Details」靠这个参数回到用户来时那一期，不带则 A4 走服务端缺省期次（closed month 所在季度，实测 `Q4 2025`）。⚠️ **带的是本页 `shownPeriod`（= 接口 22 返回的 `period` 兜 URL 参数）、不是 URL 原参** —— URL 没带期次时，后端解出来的那一期才是本页真正在看的那一期。⚠️ 这两条**由前端拼**是对的（编译期固定的站内路由），与维度卡那两条后端下发的动态 URL 不同（§0.24-Z9）；ERL Card 雷达图下方那条入口（§8.1.1 / §0.10-D7）**保留不变** | 原型（2026-09-09 重抓）+ §5.6.1 |
| ~~**A4 页级 `+ New` / `View history`**~~ | ~~`+ New` 公司端跳 B1、管理端跳 B2（带当前 `period` 预选，同 A3）；`View history` 跳 `/exitReadiness/history`，**不带 `dimension` 参数**（本页是全维视角，与 A3 的按维过滤不同）~~ → **v4.4 作废**（§0.10-D5 / R1）：**页级两个按钮取消**，改为**每张维度卡卡头的 `Add New` / `View History`**，两者**都带 `dimension={code}`** —— 提交单元已是单个维度，「全维视角发起一次评估」这个动作不再存在 | — |
| **A4 与原型的三处有意偏离**（v3.5「四处」，v4.4 更新①②③，**v4.20 撤销第 4 条并复核其余三条**） | ① 原型 `+ New` 恒跳 GSV 问卷（`/assessments/gsv`）→ 本设计按端类型分流、下沉到卡头并带 `dimension`，URL 取后端下发的 `addNewUrl`（**仍成立**；v4.20 只是把「哪一侧渲染它」对齐了原型）；② ~~原型元数据与分数是写死 mock、切 Tab 只换本地对象 → 组合端不再用 Tab，两端同屏并列~~ → **v4.20 改写**：组合端已改回端切换药丸，**表现形式不再偏离**；仍偏离的是**数据来源** —— 原型切端只换写死 mock，本设计是真数据（一次取回双端后本地切片），缺一端时该侧走空态而不是假数字（**仍成立，理由改了**）；③ 原型基准是**一对写死总分**（6.5 / 8.2）且两端都显示 → 本设计为**按维度明细**（条数动态）且**公司端不下发**（**仍成立**）；④ ~~原型页头无综合分与 Stage → A4 页头必须有（§0.8-12）~~ → ❌ **v4.20 撤销**（§0.24-Z2，需求方裁决「严格照原型」）—— 页头回到原型形态，本条不再是偏离。<br>（原型逐题无附件、无题集版本标注 → 本设计补齐附件 chip，这条 v3.5 曾并入第 ④ 项；v4.20 起附件展示已是**原型自身就有的形态**（`ATTACHMENTS` 块 + 体积 + 下载），不再算偏离） | §4.2 / §4.3 / §5.6.1 / §7.10-N2 / §0.24 |
| **A4 与 A3 的关系**（v3.5，v3.6 微调，v4.0 收窄 A3 的内容清单，v4.4 撤回 YAGNI 判断，**v4.20 收回页头判断**） | A4 **不是** A3 的替代：A3 是单维深度页（Perception Gap **仅组合端** / Priority Gaps 与建议动作 / 基准位置 **仅组合端**；**v4.0：状态摘要与 Data Sources & Cadence 两块已删**；**v4.4：Strengths 已删，§0.10-D4**），A4 做**逐题明细的全维平铺**；~~外加页头整体判断（加权 `Overall Score` / Stage）~~ → **v4.20 作废**（§0.24-Z2）：**A4 现在只有逐题明细**，整体判断在 ERL Card 与 F2 上看。**不重复** E2、Perception Gap 与雷达图这一点不变。<br>~~A4 上**不加**跳 A3 的入口（原型没有，单维深度从 ERL Card 的 `View Details` 进，YAGNI）~~ → **v4.4 撤回**（§0.10-D5）：A4 每张维度卡卡头已有 `+ Add New` / `View history` 两个维度级入口；单维深度页仍从 ERL Card 的 `View Details →` 进，A4 卡头**不额外**加第三个跳 A3 的链接（避免与 `View history` 混淆） | 本设计（§8.5 的延伸） |
| ~~**A5 评分标准弹窗**（v4.0 改）~~ | ❌ **v4.9 整体删除**（§0.15）：~~每题右侧 `How It's Scored?` 图标，弹出**该题的单段判定标准 + 所属 `Era-level`**；数据随题目返回，不额外请求~~ —— 判定标准字段 `criteria` 不进需求设计，弹窗唯一实质内容消失（`Era-level` 本就在逐题行的次级行上），`ScoringCriteriaModal` 组件、三处题目行的入口链接与 `.criteriaLink` 样式一并移除 | ~~§3.8~~ → 需求方 2026-09-06 裁决取消（PRD §3.8 本就只有「题干 / Era Band / Source」，无需回写） |
| **B 填报单元 = 单个维度**（**v4.4 全行新增**，§0.10-R1） | ~~问卷恒为整卷（五维一起填、一起提交）~~ → **v4.4 作废**（需求方 2026-09-06 裁决）：**一次填报 / 一次提交只覆盖一个维度**。填报页**必须带 `?dimension={code}`**（缺参时按当前期次「尚未提交的第一个维度」兜底，仍只填一个维度）；页头显示 `{维度全称} ({缩写})` + 期次 + 端别；**页内不再有维度切换器**（换维度＝换一次填报，从 A3 / A4 的入口重进）。题库版本按**该维**绑定（同期次不同维度可能是不同版本，系统不阻止、不告警） | §0.10-R1 + PRD §3.2 |
| **B 顶部按钮组**（**v4.4 全行新增**，§0.10-D8 / PRD §3.3 `08b7a32`） | 页面顶部固定四个按钮：**`Save as draft`** / **`Cancel`** / **`Reset`** / **`Submit`**。<br>· **`Save as draft`** = 把当前全部作答落盘（走接口 4）；~~与现有 **1.5s 去抖自动保存并存、不互斥**（自动保存保留，见下「B 自动存草稿」）~~ → **v4.30 作废**：自动保存已取消，**接口 4 只由 `Save as draft` 与 `Submit` 两个按钮触发**（见下「B 草稿落盘时机」）；成功 toast `Draft saved.`<br>· **`Cancel`** = **只离开页面**，草稿已在服务端，**不做任何数据操作、不弹确认**（回来源页；无来源时回 Company Overview）<br>· **`Reset`** = 调**接口 28** `DELETE /erl/assessment/draft`，清空本次草稿的**全部答案与附件**、`unlockedLevel` 回到 `1`；~~**必须二次确认**，弹窗文案须写明附件一并删除~~ → **v4.29（2026-09-14 需求方）撤下二次确认**：点下去直接清，随后重拉接口 3 重绘为全新草稿<br>· **`Submit`** = 见下「B 提交」<br>只读态（公司端看 B2、或打开已 `SUBMITTED` 的记录）下四个按钮**均不渲染**。<br>⚠️ **该维度没有已发布的题时（接口 3 回 `levels = []`，屏上是 `No questions published for this dimension yet.`），`Reset` 与 `Save as draft` 置灰**（需求方 2026-09-20）—— 没题就没作答，存存不出东西、清也没东西可清；`Cancel` **不在此列**（它只是离开页面），`Submit` 本就由 `canSubmit` 把门（该情形下恒为 false）。前端判据与卡内空态 `DimensionSection` 的 `isEmpty` **同一条**（`levels.length === 0`），不得各写各的 | §0.10-D8 |
| **B 草稿语义与上次保存提示**（**v4.4 全行新增**，§0.10-D9 / PRD §3.3） | **草稿是公司共享的、不区分账户**（草稿唯一索引不含用户维度，模型上天然成立，此处显式写明产品语义）：**A 保存后 B 打开看到的是 A 的内容，B 的保存直接覆盖 A 的**，无锁、无冲突提示、无版本合并。<br>~~进入已有草稿时，页头显示**上次保存时间与保存人**：`Draft last saved {time} by {name} ({role})`~~ → **2026-09-15 / 16 两次订正**，拆成分工不重叠的两处，数据都取**接口 3** 出参 `lastSavedAt` / `lastSavedBy`（由 `updated_at` / `updated_by` join 用户表得到，**不新增快照列**）：<br>· **顶部 `Draft restored` 横幅**（2026-09-15 需求方圈图）讲「进来时接手了谁的草稿」：`You are continuing the company’s shared draft, last saved {时刻} (UTC) by {姓名}.` + 右端 `Discard draft`；**进这份填报的首次载入判一次就钉住**，三条判据缺一不可：服务端 `status = DRAFT`、有 `lastSavedAt`、且 **`answeredCount > 0`**（**v4.42** 追加：接口 28 清空答案却保留草稿行、还会刷新 `lastSavedAt`，只看前两条会对着空草稿弹横幅）。清空 / 提交 / 本次自己存过一次之后撤掉。<br>· **按钮行左下 `Draft saved {时刻} (UTC) by {姓名}`**（**不显示角色**）讲「这一页此刻的保存状态」；**v4.38：只在本次访问内点过 `Save as draft` 且落盘成功之后才出** —— 刷新、退出重进都不显示。<br>**提交人以最终提交者为准**：`submitter_name` / `submitter_role` 在**提交时**快照 —— 即使草稿全程由他人保存，提交人只记录**点提交的那个人** | §0.10-D9 |
| **B 题库更新提示**（**v4.4 全行新增**，§0.10-D10 / PRD §3.3 `4f959bb`；**2026-09-15 换形态、v4.41 回写**） | 版本锁定本体不变（评估恒按自己绑定的 `erl_question_config_version_id` 渲染与计分（**2026-09-08 改名**））。接口 3 出参补 `latestPublishedVersionNo` + `hasNewerQuestionSet`。<br>~~`hasNewerQuestionSet = true` 时填报页顶部挂一条**非阻断、可关闭、无操作按钮**的 banner `The question library has been updated (v{n}). This assessment continues on v{m}.`~~ → **2026-09-15 需求方圈图作废**，改为**强阻断二选一弹窗**（`QuestionSetUpdatedModal`）：**存过草稿**（接口 3 `status = DRAFT`）且 `hasNewerQuestionSet` 时**一进页面就弹**，只有标题 `The question library has been updated` 与两颗按钮、**不可关闭**（无 ×、点遮罩与 ESC 都不关）：<br>· **`Submit draft content`** = 按**旧题库**就地交掉这份草稿（接口 5 带 **`autoAnswerNo = true`**）。**v4.41**：没答完时服务端先把顺序上第一道未作答的题补成 No 使本维终止，再走**完全正常**的提交校验与计分 —— ~~跳过校验~~ 的说法已作废，Share 与 Goldie 差距分析一切照旧；唯一仍会拦的是「该维 0 题」那条。前端刻意不看 `canSubmit`、也不弹 D11 的重复提交确认；提交成功后就地重拉接口 3（该行已翻 `SUBMITTED`，服务端按最新版下发空白问卷）。<br>· **`Access new question library`** = 走 `Reset`（接口 28）：服务端清答案 + 删附件后**改绑最新已发布版本**（§0.30）。⚠️ 这不是 §7.10-N3 否决的「保着答案换题面」。<br>⚠️ **2026-09-16（v4.54）追加第三条门槛：这份草稿必须真有内容**（`answeredCount > 0`）—— 清空之后没再存过的空草稿期间又发布了新版时，前端在载入时就地走接口 28 替它改绑（屏上直接换新题库、弹窗不弹），改绑失败也仍然不弹：那两条路对着一份空白问卷都没有意义。<br>⚠️ **失败不关弹窗**（用户可改选另一支）；两支都失败时页面上没有出路，已登记在 [`CIOaas-web/docs/待优化项.md`](../../../CIOaas-web/docs/待优化项.md)。<br>这一条**订正**了 §9 原「填报页无任何提示、无任何变化」的写法 | §0.10-D10 |
| **B level 逐级解锁**（**v4.0 新增，替代原「Era 折叠分组」**） | 每维度内**按 level（1–9）分组**，组头 `{Era 名} - {level}` + 题数/已答数 + 状态图标：<br>· `CLEARED` → **折叠 + ✓ Check**（PRD §3.3 原文「该 level 折叠并显示 Check」）<br>· `ACTIVE` → 展开，可作答<br>· `BLOCKED` → 展开，组头标 `Stopped here`；**首个 No 之后的题禁用、之前的仍可改**（v4.28，非整级只读）<br>· `LOCKED` → **整组不渲染**（后端也不下发题面，§6.3）<br>~~五个维度各自独立推进（§0.9-15）~~ → **v4.4**：一次填报只有**一个**维度，「维度间各自独立推进」在数据上依然成立（每维一条 `erl_assessment`），但**页面上不再同屏出现多个维度**（§0.10-R1） | §3.3 |
| **B 解锁反馈**（**v4.0 新增**） | 某 level 最后一题答完且全 Yes → 该组**动画折叠 + 打勾**，下一组随即展开并滚动到视口；出现 No（**v4.28：不必答完该 level**）→ 该组标 `Stopped here`，该 No 之后的题禁用，下一组**不出现**，并提示 `Dimension score: {levelScore}/9`（⚠️ **v4.37**：该数**直出接口返回的 `levelScore`** —— 原写法 `{level−1}` 按旧口径写死，稀疏题库下会算错，前端一律不自行推导） | §3.3 |
| **B level 进度指示**（v4.0 由「打分标度图例」改） | 每维度分组顶部一条 **1–9 level 进度条**：已通关 level 实心、当前 level 高亮、未解锁 level 置灰；旁标 `Founder Era 1–3 / Harvest & Growth 4–6 / Exit Era 7–9` | 本设计（原 PRD UX「打分标度图例」已于 2026-09-02 删除；1–9 分标度不存在了，改为 level 进度） |
| **B 证据/备注字段** | 折叠式次级输入，**视觉从属于 Yes/No 选择，不呈现为必填**；占位文案 `Add evidence or notes (optional)` | §3.3（「可选」明文）+ 本设计（原 PRD UX 要点已删除） |
| **B 附件上传**（v4.0 补上限，**v4.6 双端同款**） | **轻量小图标**紧邻备注，不喧宾夺主；已传文件以小 chip 列出（文件名 + 大小 + 删除 + 失败重试）；**选择文件时本地校验 ≤10MB**，超限不上传并提示 `File exceeds the 10 MB limit.`。**B1 / B2 两端渲染完全一致**，不做端区分 | §3.3「单个最大 10MB」+ 本设计（原 PRD UX 要点已删除） |
| ~~**B2 维度级附件**（v4.0 新增）~~ | ❌ **v4.6 整体删除**（§0.12）：维度分组头部的 `Dimension evidence` 附件区与 `DimensionAttachmentPanel` 组件一并移除，GSV 端改用与 Founder 完全相同的逐题上传 | ~~§3.4「每个维度均可提交附件」~~ → 需求方 2026-09-06 裁决取消（回写 M13） |
| **B 来源标签** | 每题显示 `Source: {evidenceSource}`，空显示 `—` | §3.3 / §3.4 |
| **B 草稿落盘时机**（v4.0 改，v4.4 补并存说明，**v4.30 全行改写、行标题原为「B 自动存草稿」**） | ~~Yes/No 或备注变更后**去抖 1.5s 批量 POST**；**v4.4：自动保存保留不变，与顶部 `Save as draft` 手动 flush 并存不互斥**（§0.10-D8）；离开页面前 flush~~ → **v4.30 作废**（需求方 2026-09-14 裁决取消自动保存、2026-09-15 再裁决收敛到两个按钮）：**接口 4 只由 `Save as draft` 与 `Submit` 两个按钮触发**，作答 / 改备注 / 传附件本身**一律不落库**；草稿期的解锁推进改走**接口 29**（只算不存、零写入，§6.3），**解锁进度与维度分仍一律采用服务端返回值、前端不本地推断**（§6.3）；保存中 / 已保存状态仍在吸底条提示。<br>⚠️ **不做**未保存离开拦截（`<Prompt>` / `beforeunload` / `Cancel` 与切期次二次确认 / `Unsaved changes` 常驻），也**不做**浏览器本地草稿缓存与 `Restore unsaved answers?` 恢复提示 —— 口径是**「没点保存就是没保存」**，**答一半关标签 / 刷新 / 切期次即全部丢失**，是**刻意接受**的后果（需求方 2026-09-15 裁决） | ~~§3.3「支持保存进度、稍后继续，无数据丢失」~~ + 本设计（原 PRD UX「自动保存无感」已删除；**v4.30：「无数据丢失」以用户自己点 `Save as draft` 为前提**） |
| ~~**B 改答回收提示**（**v4.0 新增**）~~ | ❌ **2026-09-20 整行作废**（需求方，当日分两步撤完）：~~先弹确认 `Changing this to No will clear your answers for later levels. Continue?`~~、~~确认后提示 `Later levels were reset.`~~ → **确认框与事后 toast 全部取消**：把已答的 Yes 改成 No **不做任何提示**，点完即按接口 29 返回的新进度重绘（后续 level 转 `LOCKED`、题面不再下发，屏上自然清空）。**回收行为本身一字未改**，只是不再告知；前端据此删掉 `TEXT.downgradeConfirm` / `TEXT.laterLevelsReset` 两个串与只服务于它们的判定函数 `hasAnswersAfterLevel` | §6.3（服务端回收规则的前端对应） |
| **B 提交**（v4.0 改，**v4.4 改门槛与文案**） | 提交按钮在**顶部按钮组**（v4.4，§0.10-D8）与吸底条各一处；**启用条件直接取接口 3/4 的 `canSubmit`**，~~禁用时 tooltip 说明还差哪个维度（`FRL: keep answering Level 4`）~~ → **v4.4**：门槛降为「**本维度到达终止态**」（§0.10-R1），禁用 tooltip 改为说明**本维还差哪一级**（`Keep answering Level 4`）。<br>**提交确认弹窗分两种文案**（**v4.4**，§0.10-D11 / PRD §3.3 `08b7a32`）：<br>· **首次提交**（该期次该端该维 `submissionCount = 0`）：沿用现文案 —— 提交后锁定为只读、如需修改要新建提交、下一步是对方独立评估后出现对比<br>· **重复提交**（`submissionCount > 0`）：改为 PRD 原话 **「已提交该季度评价，是否再次提交？」**，并补一句 **「本次提交将成为该季度的 source of truth，历史提交保留可查」** | §3.3「激活提交按钮」+ §0.10-R1 / D11 |
| ~~B1 / B2 每维手动整体分 + 软确认弹窗~~ | ❌ **v4.0 删除**：PRD 2026-09-02 在 §3.3 / §3.4 同时删除该要求（§0.9-3）。**开发时勿沿用 v3.6 的实现** | — |
| **Yes/No 呈现**（v4.0 改） | 填报页每题渲染 Yes / No 两个按钮（**唯一的作答控件**）；A3 / A4 逐题列表右侧显示 `Yes` / `No` 徽章。**v3.x 的 1–9 选择器与 `Not scored` 标注一并删除** —— 现在所有题都是 Yes/No，没有「不计分的题」这个概念 | §3.3 / §3.4 |
| **题数与已答数说明**（v4.0 改，**v4.20 把 A4 摘出去**） | ~~A3 / A4 页头~~ → **A3 / 填报页页头**显示 `{totalCount} questions · {answeredCount} answered`（**§0.24-Z8：A4 只报总题数** `{totalCount} questions`，单复数由 `questionCountText` 处理 —— `1 question` / `31 questions`；**A3 / 填报页不变**）；维度分旁 tooltip：`Score is the last level answered all Yes. Levels after Level {t} were not shown.` | §7.1.1 |
| **C6 `Dimension Configuration`**（v4.0 新增，v4.1 改形态，v4.4 全行重写，**v4.8 布局改版 + 删 `status`**；**2026-09-08：`status` 重新加回并落库（`Active` / `Inactive`）、删除改软删、不再生成配置版本**；**2026-09-09 面板改版：破坏性动作一分为二（垃圾桶=删 / 电源按钮=停用）、`Show deactivated` 开关撤下、底部加常显 `Deactivated Dimensions` 区块**，§0.10-D13 / §0.14 / §0.21 / §5.1.3） | 配置页**第二个顶层 Tab `Dimension Configuration`**（与 `Question Library` 并列）。**面板自上而下五块：面板头 / 新增栏 / 主列表 / 规则提示 / `Deactivated Dimensions` 区块**（**2026-09-09 布局取自当日 mockup**）。<br>**① 面板头**：**左侧**标题 + 说明 `Configure the Exit Readiness dimensions and their weights in the overall score. The total must equal 100%.`、**右侧** `Total: {n}%` + **`Save`** 按钮（形态不变）。~~面板头加一个 `Show deactivated` 开关~~ → **2026-09-09 整个撤下**（连同它的脏态确认弹框文案 `dimensionConfigToggleDeactivated`）：页面此后**恒**带 `includeDeactivated=true` 取数，停用行改由底部常显区块承载（见 ⑤）。**理由**：那个开关自己成了一个脏态 —— 开/关要不要确认、开着时提交集合算不算变化，都得单独定义（那条确认文案就是为此加的）；改成常显区块后，「展开」不再是一个动作，这些问题一并消失（§0.21-X10）。<br>**② 面板头下一行 = 新增栏**（**v4.8 新增，取代原表底的 `+ Add Dimension`**）：`Dimension name` 输入 + `Abbreviation` 输入（**2026-09-08 补校验**：**1–8 字符**~~且不得与本组织已有 `Active` 维度重复~~ —— 解耦后 `abbr → code` 那条隐式长度约束消失了，不补会直撞 `varchar(8)`；**2026-09-15 删掉查重那半句**，需求方当日裁决「新增维度不做任何重名 / 重缩写校验」，v4.31。⚠️ **这正是本次需求的触发点**：原先 `+ Add` 的 abbr 查重**不通过就静默不加**，用户既看不到行、也看不到任何提示，只以为按钮坏了） + **`+ Add`** 按钮。~~新增维度的 `code` = 填写的 `Abbreviation` 大写化~~ → **2026-09-08 作废**：`code` 由**服务端随机生成**（与 `Abbreviation` 无关），**页面不展示、用户不可指定**；`code` 此后**永不改变**，**改 `Abbreviation` 也不会带动它**（它是 `erl_assessment.dimension` 等历史数据的关联键，§5.1.3）。<br>**③ 面板体 = 卡片行列表**（取**接口 23**，按 `sortOrder`；**v4.8 由表格改为卡片行**），**只渲染 `Active` 且未删除的行**（**2026-09-09 明确后半句**），每行：**拖拽手柄**（改排序）+ **`Name (ABBR)`** 文本 + **权重输入（带 `%`）** + **铅笔**（进入行内编辑）+ ~~**垃圾桶**（删除，**带二次确认**）~~ → **2026-09-09：行尾图标改为三态**（~~「`deletable` ? 垃圾桶 : 电源按钮」~~ 二选一 → **2026-09-09 实现落地后订正**，判据是 **`row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`**，§0.21-X14）—— `deletable` 由**接口 23** 下发（该 code 从未进入任何已发布题库版本的维度快照 ⇒ `true`），**前端不自己算**；**三态都要二次确认**，文案逐字取自 `CIOaas-web/src/pages/exitReadiness/components/constants.ts`：<br>　· **垃圾桶 = 删除**（`canDelete && !isRestored`）：确认 `deleteDimensionConfirm` = `Delete this dimension? It has never been published in a question set, so it will be removed from the configuration. This cannot be undone from this page.`，OK 文案 `Delete`，aria-label `Delete dimension`；<br>　· **电源按钮 = 停用**（`canDelete === false`）：tooltip `dimensionPublishedTooltip` = `Published in a question set — deactivate instead of deleting.`（~~`This dimension was published in a question set — it can only be deactivated.`~~ 从未实现，2026-09-09 按 `constants.ts` 订正），确认 `deactivateDimensionConfirm` = `Deactivate this dimension? It will no longer appear in new periods. You can activate it again below under Deactivated Dimensions.`，OK 文案 `Deactivate`，aria-label `Deactivate dimension`；<br>　· **电源按钮 = 撤销恢复**（`isRestored` —— **本次会话里刚从停用区 `Activate` 回来的行，即便 `deletable = true` 也走这一支**）：tooltip `dimensionRestoredTooltip` = `Restored in this session — undo the restore to put it back below.`，确认 `undoRestoreConfirm` = `Undo the restore? This dimension goes back under Deactivated Dimensions and stops counting toward the weight total.`，OK 文案 `Undo restore`，aria-label **`Undo restore`**。<br>　⚠️ **第三态是防误删设计，不是实现细节**（§0.21-X14）：真删在本页**没有**恢复入口，而「恢复一行 → 想撤销 → 点行尾最近的按钮」是一条高频路径；若那个按钮是垃圾桶，一次误点就把维度连历史一起葬掉。tooltip 之外还得有 ④ 那段提示，否则用户只看到「这一行的图标跟别的行不一样」（**2026-09-14**：该提示改为仅在有启用维度时显示 —— 论证不受影响，没有启用行时那些图标也不存在）。~~`Code` 列~~ → **v4.8 从页面撤下，不再显示**；~~状态列与行尾 `Retire`~~ → v4.8 删除（当时理由是「已无存储状态位」）—— **2026-09-08：该理由已不成立**（`status` 已回归落库），但主列表仍**只渲染 `Active` 行**，~~停用行改由 `Show deactivated` 开关展开~~ → **2026-09-09：由底部常显区块承载**（见 ⑤）。<br>· **行内编辑态**：`name` 输入 + `abbr` 输入 + 权重输入 + 行内 **`Save` / `Cancel`**。⚠️ **行内 `Save` 只是把这一行的编辑提交到本地状态，不调任何接口**；**只有右上角的 `Save` 调接口 24**，~~整组保存并生成新的配置版本~~ → **2026-09-08：整组就地替换，不产生版本**。行内可改的只有 `name` / `abbr` / `weight` —— `code` 不可改、也不显示<br>· **电源按钮 = 停用 = 软删**（**2026-09-09**：入口由垃圾桶换成电源按钮，**落库语义一字未改**）（**2026-09-08 推翻 v4.8**：置 `status = 'Inactive'`，行与 `weight` 保留、可恢复）（**v4.8**，原「Retire 软删」作废）：确认后本地标为停用，右上角 `Save` 落库时它**不出现在提交的 `dimensions[]` 里**、其 code 进 `deactivatedCodes[]`，服务端据此置 `status = 'Inactive'`（**2026-09-08**：~~新版本的 item 没有这一行 / 绑旧版本的历史期次 / 派生态~~ 三个提法均作废）；**行与 `weight` 保留**，历史提交记录**照常显示并标灰色 `Retired`**（由 `status` 列**直接判定**）；该行随即出现在底部 `Deactivated Dimensions` 区块里，可 `Activate`。<br>· **垃圾桶 = 删除**（**2026-09-09 新增的第二个动作**，只在 `deletable = true` 的行上出现）：确认后本地标为已删，右上角 `Save` 时其 code 进 **`deletedCodes[]`**（**显式点名，不是靠「缺席」表达** —— 缺席只表示停用），服务端置 **`deleted = true`**。此后该行**从页面彻底消失**：主列表没有、`Deactivated Dimensions` 区块也没有、**没有恢复入口**；库里行与 `weight` / 名称 / 缩写原样保留（历史按 `dimension_code` 仍解得出），`dimension_code` **永久保留占用**（不会被重新分配给新维度，§5.1.3）。**二次确认文案必须写明不可恢复**（~~`Delete “{name} ({abbr})”? This dimension has never been published in a question set. It will be removed permanently and cannot be restored.`~~ → **2026-09-09 按 `constants.ts` 逐字订正**：`deleteDimensionConfirm` = `Delete this dimension? It has never been published in a question set, so it will be removed from the configuration. This cannot be undone from this page.`，**不带 name / abbr 插值**，OK 文案 `Delete`）—— 这是产品里唯一一个不可撤销的维度动作，与旁边那个「随时能 `Activate`」的电源按钮只差一个图标，不写明必被当成停用点。**⚠️ C6 本地行模型与提交语义（**2026-09-08 新增，不写死就会出僵尸维度**）**：本地数组同时存在五类行（**2026-09-09 由四类增至五类**：接口 23 来的 `Active` 行 / 来的 `Inactive` 行 / `+ Add` 产生的**无 code** 行 / 被电源按钮标记停用的行 / **被垃圾桶标记已删的行**），故：① **`rowKey = dimensionCode ?? localId`**（`localId` 前端生成、仅本地存活，**提交时作为 `clientRef` 上行**）—— 拖拽排序、行内编辑、二次确认弹框都靠它定位；② **`isNew = !dimensionCode`**，提交时转为 `isNew: true` + `clientRef`；③ **`isDeactivated` 是独立本地标志位**，决定该行进 `dimensions[]` 还是进 `deactivatedCodes[]`；**③' `isDeleted` 是另一个独立的本地标志位**（**2026-09-09 新增**，与 `isDeactivated` **并列、不复用**），另存服务端下发的 **`canDelete`**（= 接口 23 的 `deletable`，决定这一行给哪个图标）。⚠️ **一行在提交时只能进三个桶之一**（`dimensions[]` / `deactivatedCodes[]` / `deletedCodes[]`）—— 进两个即触发服务端的 ⑩ 号校验（§6.4-3）；把删除塞进 `isDeactivated` 或反过来，落库会变成另一个动作，而 UI 上两者只差一个图标、**测不出来**。⚠️ **新增但未保存的行没有 code，垃圾桶对它仍是直接从数组里抹掉**（不进 `deletedCodes[]`，那个数组只收「已有维度」的 code；服务端根本不认识这一行，点名它只会撞 ⑧ 号校验 `Unknown dimension code`）。**权重合计（`Total`）把已删行也排除**，与排除停用行同理；④ ~~**`Show deactivated` 只是视图开关，不改变提交集合**~~ → **2026-09-09：开关已撤下，但这条口径仍然成立**（只是「展开」不再是一个动作）—— 常显区块里**看得见**的停用行，没点 `Activate` 就仍进 `deactivatedCodes[]`，**不得混进 `dimensions[]`**（否则全部被误恢复，且它们原样保留的 `weight` 会把合计冲爆）；⑤ **保存成功后必须用出参整体替换本地数组**（丢弃全部本地临时行，按 `created[{clientRef → dimensionCode}]` 接管服务端下发的 code），**不得增量合并** —— 否则用户不刷页再点一次 Save，那些行**仍然没有 code** ⇒ 再建一批新行、上一批因缺席被软删，**每多点一次 Save 多一批僵尸维度**；⑥ **整组 Save 失败（含 409 / 500）时不得清空本地编辑态** —— 行内 `Save` 不调接口，用户可能已改了十几行。<br>**④ 列表下方的规则提示**（**2026-09-09 新增；2026-09-14 改为「有启用维度时才显示」**）：一段说明，把两个图标的差别讲清楚 —— **实际文案** `dimensionConfigDeleteHint` = `Dimensions already published in a question set cannot be deleted — deactivate them instead. Deactivated dimensions are excluded from the weight total and from new assessments, while past records stay intact.`（**2026-09-09 按 `constants.ts` 逐字补**，原为「大意是……」的转述）。⚠️ **这段不是装饰**：垃圾桶与电源按钮同列出现、只差一个图标，而后果一个可逆一个不可逆，光靠 tooltip（要悬停才看得到）不足以让人在点之前知道差别。<br>**⑤ 面板底部常显 `Deactivated Dimensions` 区块**（**2026-09-09 取代 `Show deactivated` 开关**）：区块标题 `Deactivated Dimensions` + **空态 `No deactivated dimensions.`**（**常显 ⇒ 必须有空态**，这是撤下开关后新增的一个必写状态）+ 停用行列表（**灰化** + `Inactive` 标 + **只读可复制的 `code`** + 权重 + 行尾 **`Activate`**）+ 区块尾一段说明（**2026-09-14 起仅在有停用行时显示；区块标题与空态仍常驻**）`deactivatedSectionNote` = `Deactivated dimensions remain in historical questionnaires and cannot be fully deleted; they are hidden from new assessments and excluded from the weight total.`（**2026-09-09 按 `constants.ts` 逐字补**）。⚠️ **区块里只有 `Inactive` 行，没有已删行** —— 已删行在这里也不出现（§5.1.3：无恢复入口）；接口 23 对 `deleted = true` 的行**任何情况下都不下发**，所以这条在前端天然成立，**但不要为了「让用户知道删过什么」自己去补一个已删列表**，那等于把不可恢复的删除又变成软删。<br>**⚠️ 恢复口径（**2026-09-08 补，2026-09-09 换承载**）**：~~面板头加一个 `Show deactivated` 开关（走接口 23 的 `includeDeactivated=true`），停用行灰化展示 + 行尾 `Activate`~~ → **2026-09-09：开关撤下，改为上述常显区块**（取数改为**恒**带 `includeDeactivated=true`）。点 `Activate` 把它从 `deactivatedCodes[]` 移到 `dimensions[]`，**必须原样携带接口 23 下发的 `dimensionCode`**（恢复的唯一判据就是该 code 命中一行 `Inactive`）—— ⚠️ **千万不能把停用行的 name/abbr/weight 拷进一个新行对象**，那会变成新增一个新 code 的维度、旧行仍停用，而 UI 上看起来「恢复成功了」。右上角 `Save` 后该行回到 `Active`；它原样保留的 `weight` 会破坏 100% 合计，**需在同一次 Save 里补齐**。停用行上必须展示**可区分信息**：`dimension_code`（只读 + 一键复制）、最后一次被提交的期次、关联提交条数 —— 否则两行同名时 `Activate` 是抛硬币。⚠️ **2026-09-15 起这条更要紧**：缩写唯一整条取消后，**同名 / 同缩写的两行是完全合法的常态**（v4.31 / §5.1.3），`dimension_code` 是唯一能把它们分开的东西。没有这个区块，§5.1.3「可再置回 `Active` 恢复」在前端不可达。<br>· ~~**无条件允许删除**，不做「有历史数据禁止删除」的前置拦截（§13-Q24 已关闭）~~ → **2026-09-09 作废**（需求方当日裁决）：**拦截存在** —— 已进入过已发布题库版本的维度**没有垃圾桶**，服务端亦硬拦（§6.4-3-⑨）。但判据是「**是否进入过已发布题库版本**」而不是「**有无历史数据**」，保护对象也不是那一行（软删下行不消失），而是**已发布题库版本的语义**（§7.11-④ / §13-Q24 改判）。⚠️ **前端按 `deletable` 不显示垃圾桶只是体验，不是防线** —— 抓包能直接传 `deletedCodes`，服务端那条校验不可省。<br>· **`Save` 启用条件**（**2026-09-09 由「双条件」补全**，实现即 `dirty && total === 100 && rowsIssue === null && editingKey === null && !saving`；**2026-09-09 补**：③ 的否决原因不再只是个布尔，而是回一个 `DimensionRowsIssue` 并**渲染在 `Total` 左侧** —— ~~恢复一行 abbr 与主列表撞车的停用维度是个典型可达状态，那时合计正好 100%、Save 却永久禁用，屏上不给字用户只能靠猜~~（**2026-09-15**：`DUPLICATE_ABBR` 这一档随缩写唯一取消而删除，举的这个例子不再可达；`DimensionRowsIssue` 本身**保留**，仍承载 `name` / `abbr` 为空、`abbr` 超长、无启用维度三档）：① **脏态**（维度增 / **删** / **停用** / 改名 / 排序 / 权重任一变化）② **全部 `Active` 维度**权重合计 = 100%（**2026-09-08**：`Inactive` 行不计入；**2026-09-09**：**已删行同样不计入**）③ **`rowsValid`** —— 每行 `name` / `abbr` 非空、`abbr` **≤ 8 字符**、~~**本次提交内 `abbr` 不重复**~~（**2026-09-15 删除该否决项**，v4.31）、且**至少有一个启用维度** ④ **无行处于编辑态**（`editingKey === null`）—— ⚠️ **这条产品可感知**：任一行点铅笔进入行内编辑后，右上角 `Save` 就是灰的，必须先行内 `Save` / `Cancel`（另有提交中 `!saving` 的防重入）；不满足即禁用，`Total` 红色标注并提示 `Exceeds 100% by {n}%` / `Needs {n}% more`（二选一）<br>· **Save 走接口 24 整组保存**（维度集合 + 排序 + 权重），服务端校验合法性与合计 100.00，**保存出参此后只有一个需要二次确认的分支 `CONFLICT`（乐观锁）**（~~另一个分支 `DUPLICATE_NAME` —— 新增项同名命中某个 `Inactive` 行时弹 `Create anyway` 二次确认~~ → **2026-09-15 整条删除**：同名软拦截取消，连同它的三条文案与那个 `Modal.confirm` 一并撤下，v4.31 / §6.4-2-⑦），~~**保存即生成一个新的配置版本**~~ → **2026-09-08：就地整组替换，不产生版本、旧值不留存**<br>· **Save 确认框文案**：~~「权重立即生效，并会改变所有历史期次的综合分与 Stage」~~ → ~~v4.4：「新配置从下一个尚未开始填报的期次起生效；已有提交的期次沿用其绑定的配置版本，历史分数不变」~~ → **2026-09-08 反转回 v4.0 口径**（§13-Q21 重新打开）：**「新配置立即全局生效，已有期次的综合分、Stage 与雷达图形状会随之变化。」**<br>· 保存成功 toast `Dimension configuration saved.`，并**刷新 overview 页 / 雷达图 / 题库 Tab 的维度回显**（§0.10-D1）<br>· **其余口径不变**：不进题库版本、**不激活 `Publish`**、走自己的 Save（§7.9） | PRD §3.8（`0333162`：维度可新增 / 删除 / 排序 / 改权重，总权重 100%）+ **需求方 2026-09-07 的 C6 布局改版**（§0.14）+ **需求方 2026-09-09 裁决与当日 mockup**（两个破坏性动作 + 常显 `Deactivated Dimensions` 区块，§0.21）；⚠️ 原型 2026-09-03 改版（§2.3.1-⑤-5）为五维表格形态，**布局部分已过期** |
| **C7 题库版本历史**（v4.1 新增，**v4.2 全行重写**，**2026-09-09 改版本下拉与卡头**） | 入口：`Question Library` Tab 操作区的 `View history` → `/exitReadiness/configuration/history`。**页面是「选一个版本 → 看那一版的整份题库」**，不是版本清单表。<br>**页头**：H1 `Question Library History` + 说明 ~~`All questions across the five Exit Readiness dimensions for the selected version.`~~ → **v4.4** `All questions across the Exit Readiness dimensions for the selected version.`（去掉「five」，§0.10-D1）；**右侧**同排 `Version` 标签 + 版本下拉 + `Back`（回配置页）。<br>**版本下拉**（取**接口 25**，按版本号倒序）—— **2026-09-09 起只列已发布（`PUBLISHED`）版本**（v4.17，§0.22-Y1）：接口 25 的出参在**前端取数 hook `useQuestionVersions`** 里按 `status === 'PUBLISHED'` 过滤后才进下拉与默认选中；**接口 25 的契约一字不改**（仍返回 `DRAFT` + `PUBLISHED`）—— 「库里有没有草稿」是 `Publish` 按钮能不能点的判据来源，服务端不能替 C7 把草稿滤掉，而 C7 是它当前唯一的消费方，过滤放在页面侧的代价只是一个 `filter`。下拉的 placeholder 为 `No published versions yet`；选项文案 ~~三种~~ → **两种**：最新已发布 `v{n} — Current (published {日期})` / 其余已发布 `v{n} (published {日期})`（~~草稿 `v{n} — Draft (edited {时间})` / `v{n} — Draft (not published yet)`~~ —— **2026-09-09 整支删除，不再可达**）。**默认选中最新已发布版本**（填报页正在用的那一版）；~~一版都没有时~~ → **没有任何已发布版本时**下拉置空、页体走空态 `No published question set versions yet.`。~~**草稿也可选** —— 它同样是一份完整题库，只是还没生效。~~ → **2026-09-09 作废**（需求方裁决：C7 只回看「已下发」的版本）。⚠️ **这是本次的行为变化**：一份都没发布过（库里只有草稿）的组织在 C7 上是**空态**，**不再退回「选中草稿」** —— 新建组织在第一次 Publish 之前本来就没有「已下发的题库」可回看，不是 bug。<br>**页体**（取**接口 26**）：~~按五维固定顺序~~ → **v4.4：按该版本对应的维度配置顺序**（`sortOrder`，张数不固定，§0.10-D1）；**v4.10 定源**（§0.16-H2 / -H3）：该维度集合由**接口 26 出参 `dimensions[]`** 下发（**2026-09-08**：数据源改为 `erl_question_config_dimension_version` 的**发布当时逐维快照**，§5.1.5），**不再取接口 23 的当前生效配置** —— ~~发布后被删除的维度仍按**发布当时**的 `{维度全称} ({缩写})` 显示并打 `Retired` 灰标~~ → ~~**v4.11 改**（§0.17-K1 ~ K4）：今天已不在维度配置里的维度整卡不显示、连带其题目也不出现，全部维度都被滤掉时页体走空态 `None of this version's dimensions are in the current configuration.`~~ → **2026-09-09 定档（v4.17，§0.22-Y2 ~ -Y4）：既不过滤、也不标注** —— ① 发布当时的每个维度**照常整卡展示**、连带它的题目一律照出（**K1 / K3 从未实现**，2026-09-07 那次「整卡连题滤掉」的回退依然有效，v4.10-H3 的「题目永不消失」恢复成立：脏数据仍兜底出卡、name / abbr 退化为 code、**但不打标**）；② **卡头不再显示 `Retired` 灰标**（需求方 2026-09-09 截图圈定的就是它）；③ ⇒ **本页不再调接口 23** —— 那次取数**只**为算这个灰标，标一撤，`QuestionVersionSection.retired` 字段、兜底卡上的 `retired: true`、`QuestionVersionHistoryPage.less` 的 `.retiredTag` 一并删除，**C7 此后完全不依赖当前维度配置，只读接口 25 / 26 的历史快照**（少一次请求，页面 loading / error 也不再受接口 23 影响）；④ K1 的空态 `None of this version's dimensions are in the current configuration.` **一并删除**（过滤取消后永不可达）；⑤ **§0.17-K1 由此关闭，取值 = 整条取消** —— C7 与「今天的维度配置」彻底解耦。⚠️ **`TEXT.retired` 这个文案本身还在用**（`ErlCard` 的维度行与 A4 `DimensionQuestionsCard` 仍按 `status === 'RETIRED'` 打标）—— **本次只撤 C7 这一处**。发布后新增的维度**不会**在旧版本上多出空卡 —— 各渲染一张卡，卡头左 `{维度全称} ({缩写})`、右 `{n} question(s)`；卡内表格列 `QUESTION` / `ERA BAND`（Era 徽章，三个 Era 三套配色：Founder `#E1990F` / Harvest `#DED87A` / Exit `#1E8E4A`）/ `SOURCE`（空值 `—`）。**维度内题目平铺、不打 Era band 组头行**（与 C1 有意不同：C1 的分组行是为拖拽服务的，C7 只读、分组只会把页面切碎）；某维在该版 0 题时卡片保留、内文 `No questions in this dimension for this version.`。<br>只读、无操作列（不提供回滚、不做版本间 diff——V1 不做，§12） | 原型 2026-09-04 截图（§2.3.1-⑥）+ §6.4 接口 25 / 26 |
| **只读态** | 公司端打开 B2、或打开已 `SUBMITTED` 的记录时，问卷渲染为只读（无输入、无提交条） | §3.3 |
| **E1 展示**（~~⚠️ PRD 待定~~ → **v4.4：已进 V1**，§0.10-D2） | ERL Card 内为 **Gap 区块**（见上「A1 Gap 区块」，v4.4 按原型定档）；维度详情页内为完整 summary + 该维 `actions[]`（每条：动作标题 + `why`「为何相关」说明）。~~**待定期间整块不渲染**（§0.9-12）~~ → **v4.4 作废**：PRD `8324a3f` 已删「待定功能」标题，**Goldie 进 V1，常驻渲染，不再有任何「待定期间隐藏 / 恒空」的条件语**（§13-Q22 已关闭） | §3.6 |
| ~~**E1 口吻**~~ | ~~文案由后端按 audience 生成，前端不做措辞转换~~ → **v4.4 作废**（§0.10-D3）：PRD `8324a3f` 已删「Founder / GSV 两套口吻」整段，**双 audience 方案取消** —— 只生成**一份**内容，GSV 团队可见，点 `Share to founder` 后 Founder 端才可见。前端本就不做措辞转换，此行连同「两端口吻不同」的验收项一并摘除 | — |
| **E2 区块（A3 内）**（~~⚠️ PRD 待定~~ → **v4.4：已进 V1 + 删 Strengths**） | ~~左 Strengths 列表；右~~ → **v4.4 作废**（§0.10-D4）：**Strengths 相关展示全部删除**（`item_type` 的 `STRENGTH` 枚举与出参 `strengths[]` 一并删除，「有 gap 的展示建议、没有的不展示」）。区块**只剩 Priority Gaps 条目**（`title` 加粗 + `note` 次级文字 + severity 色标徽章 HIGH 红 / MEDIUM 黄 / LOW 灰），单列铺满；`evidenceMissing` 的条目追加灰色标注 ~~`No notes provided`~~ → **`No supporting evidence provided`**（**2026-09-18 随口径放宽改文案**，v4.57，§0.31-Z8；前端串名 `noNotesProvided` 沿用原名）；该维无 gap 时显示 `No Gap`（§9） | §3.6（**v4.0：§5 依据已删**，§0.9-11；**v4.4：进 V1**，§0.10-D2） |
| ~~Data Sources & Cadence~~ | ❌ **v4.0 删除**：PRD 2026-09-02 删去该展示项（§0.9-13 / §7.6） | — |
| **BPMM** | ERL Card 内一行参考数字 `BPMM {n}/5`，带 tooltip 说明为参考值；无数据隐藏 | §5 |
| **B3 历史列表**（v4.0 改口径，**v4.4 全行重写**，§0.10-D12 / PRD §3.9 `8f2fcc0`） | 列：**Period** / **Portal**（**v4.4：仅管理端渲染** —— 公司端只有 Founder 侧数据，该列恒定值、无信息量）/ **Submitted By**（姓名 + 角色）/ **`Submitted`（提交时间，v4.4 新增列**，取 `submittedAt`）/ **Overall Score（v4.4 改口径）**。<br>· ❌ **删除 `Completion` 列**（**v4.4**，PRD 已从「列表最少字段」中移除）。为不丢可解释性，原挂在该列的次级标注 **`v{n}`（题集版本，v3.4）与 `stopped at L{t}`（v4.0）挪到分数列下方的次级文字**；`answeredCount` / `totalCount` 降为**页头**用途的接口字段（§7.1.1 的分母口径论证**保留**为实现说明）<br>· **分数列 = 该维度的 Overall Score**（**v4.4 改**）：`{level}/9`（整数）+ 该维 Era / Stage 徽章 —— **不是加权综合分**（提交单元已是单个维度，§0.10-R1，加权综合分在这里没有意义）<br>· 最近在前；**每个 `(period, portal, dimensionCode)` 分组内的首行加 `Current` 徽章 + 高亮底色**（**2026-09-09**：改由后端出参 `isLatest` 判定（§6.3），前端不再按行序分组。⚠️ **不能只取全表第一行** —— SOT 的作用域是四元组，不传 `dimensionCode` 时列表是多个四元组混排，否则除最新那一条外其余组的 SOT 一个都标不出来），其余行标题色降级<br>· ⚠️ ~~PRD §3.9 的 `45/45` 示例是「五维全通关」的特例~~ —— 该示例随 `Completion` 列删除已不再是列表口径问题，仅在页头计数处保留说明（§0.9-17 / §7.1.1）<br>· **空态（v4.56 / 2026-09-17）**：`PRESENTED_IMAGE_SIMPLE` 配图 + `No submitted assessments yet.`，且**连列头一起收掉**（全仓唯一这样的表）；**加载中仍留列头**；**取数失败时整块空态压掉、只留错误横幅** | §3.9 |
| **B 题集版本标注**（v3.4，v4.0 微调） | 问卷页头、维度详情页元数据栏、Scorecard 的 Perception Gap 旁，均以次级文字显示 `Question set v{n}`；Founder 与 GSV 版本号不同时，Perception Gap 旁并列显示两个版本号（不告警、不阻止，§7.9-⑤）。**v4.0：Perception Gap 仅管理端可见，故该并列标注也只出现在管理端** | §7.10-13 / N2 |
| **B3 详情**（**v4.4 限本维度**，**v4.21 补期次**） | 点击某行进 `/exitReadiness/history/:assessmentId`，复用 A3 的题级布局呈现该次提交时的状态；**v4.4**：从**带 `dimension` 的历史列表**（A3 / A4 卡头的 `View History`）进入时，URL 透传 `?dimension={code}`，**接口 8 补可选 `dimension` 入参**，页面**只渲染该维度**（§0.10-D12）。提交单元本就是单维（§0.10-R1），故该参数在实现上恒等于该条记录的 `dimension`，透传只为页头标注与直链一致。**v4.21 补**：URL 同时透传 **`?period={period}`**（列表页 URL 上有才带）。详情页**自身取数不用它**（题目与元数据都取该条记录本身），它只让详情页面包屑回列表那一级把用户送回**带同一期次**的 B3 —— 否则进一次详情页，期次上下文就在这里断掉。⚠️ **这一跳只补了 `period`、没有补 `dimension`** —— 返回落到的仍是**全维混排**的 B3，`?dimension=` 过滤态不保留（§0.25-Z2） | §3.9 |
| **C1 页面结构**（**v4.1 全行重写**，原「C1 分组」，**v4.4 改 Tab 名与维度 Tab 动态化**） | 页头：H1 `ERL Configuration` + 说明 ~~`Configure dimension weights and the question library for each Exit Readiness dimension.`~~ → **v4.4** `Configure the Exit Readiness dimensions and the question library for each dimension.`；其下**两个顶层 Tab**：`Question Library` / ~~`Dimension Weights`~~ → **`Dimension Configuration`**（§0.10-D13）。`Question Library` 内自上而下：操作区（`Add New` / `Publish` / `View history`，**右对齐**）→ **维度 Tab（按当前生效配置动态渲染，非固定五个；已删除的维度自然不在当前版本里，也就不出 Tab —— v4.8）** → **题目表格**：列 `QUESTION` / `ERA BAND` / `SOURCE` / `ACTIONS`（另有**最左拖拽列**），按 **Era band 分组**、每组一条组头行（band 徽章 + `{n} questions`）。**v4.0 的「五维 Tab + 第 6 个 `Weights` Tab」与「组内 level 折叠面板」均作废**（§2.3.1-⑤-2/3） | §3.8 + 原型 2026-09-03 改版（§2.3.1-⑤） |
| **C4 拖拽重排 + 改 Era band**（v3.3 改，v4.0 依据变更，**v4.1 补跨 band**） | **同 band 内**：表格最左拖拽列拖动排序，松手即调接口 14 **写入草稿版本**（不影响填报页，直到 Publish）；行上出现 `Moved` 徽章；**首次拖拽弹一次性提示**：「Reordering changes the required answering sequence within this level. It takes effect when you publish. Submitted assessments keep the order in effect at the time.」<br>**跨 band 移动（v4.1）**：直接改题目行内 `ERA BAND` 列的**下拉**，选中即调**接口 12 全量更新**该题，行随即移动到目标分组末尾。**v4.0 的「跨 band 移动请走编辑表单」作废**；接口 14 仍**只做同 band 重排**（§6.4） | §3.8「拖拽重排…该顺序即评估中的必答顺序」+ 原型 2026-09-03 改版（§2.3.1-⑤-4）+ 本设计（原 PRD UX 的「给管理员必要的警告」已于 2026-09-02 删除，提示保留） |
| **C3 删除** | `Modal.confirm` 二次确认，文案含所属维度、提示**删除在发布后才生效**、说明已提交的历史评估仍按当时版本展示该题 | §3.8 |
| **C5 版本条**（v3.3） | 配置页页头常驻一行：无草稿时 `Published v{n} · {date}`；有草稿时 `Draft v{n} — unpublished changes · last edited by {name} at {time}`，整页加浅色「编辑中」边框，提示当前所见**不是**填报页正在用的题面 | §7.9-④ |
| **C5 Publish 按钮**（v3.3 改，v4.0 与 PRD 对齐） | 页面右上角主按钮 `Publish`；**存在草稿版本即激活**（任意维度的任意变更，与当前所处 Tab 无关；**`Dimension Configuration` Tab 的改动不激活它**（**v4.4 改名**，§0.10-D13）—— 维度集合 / 排序 / 权重走自己的 Save（接口 24）；~~并生成配置版本、两条互不相干的版本线~~ → **2026-09-08：配置已去版本化，只剩题库一条版本线；Publish 会把当时 `Active` 的维度逐维快照进 §5.1.5**）；无草稿时禁用 + tooltip `No unpublished changes.`；按钮旁显示 `{a} added · {m} modified · {r} removed · {o} reordered`；点击弹确认框列出**全量变更摘要（含其他管理员的改动）**并提示「发布后所有变更立即对填报页与 Score Details 生效；正在填写的评估会保留已答内容」，确认后调接口 21，成功 toast `Published v{n}.` 并刷新列表 | §3.8（PRD 现文「点击保存为新版本」已与此一致） |
| **C5 变更徽章**（v3.3） | 草稿版本中，题目行按 `changeType` 打徽章：`New` / `Edited` / `Moved`；被删除的题**不再显示**（草稿内已物理删行），删除动作的痕迹只体现在按钮旁的摘要计数里 | §7.9-③ |
| **C5 离开页面**（v3.3） | 草稿是服务端持久对象、非表单脏数据，离开不拦截、不弹确认；但**维度 Tab 头**（**v4.4：数量动态**）对**含未发布变更**的维度加小圆点，避免管理员漏发某一维。⚠️ **v4.4 例外**：`Dimension Configuration` Tab 是**普通表单脏态**（不是服务端草稿），未 Save 就离开**要弹确认** | 本设计（§7.9） |
| **D1 页头**（**v4.25 补期次**） | 面包屑 ~~`Portfolio Companies › {公司名} › Top GSV Quartile & Benchmarkit`~~ → **2026-09-10 原型改版**：第二级由公司名改为**来源页 `Score Details`**（末级文案随页标题改 `Top GSV Quartile & External Benchmarks`）；该级链接 `scoreDetailsUrl` 回 A4 **带 `&period=`**（早就写了「URL 上带了就带回去」，v4.25 补的是**上游给不给**，§0.29）。标题下一句说明「Reference scores used to compare this company's Exit Readiness against the GSV top quartile and the ~~Benchmarkit~~ **External Benchmarks** peer set. Each entry is kept as a dated record.」；右上 `+ Add New` → D2，**v4.25 起同样带期次**（`addUrl`，§0.29-Z2）。⚠️ **2026-09-10 D1 三列改版本身仍未逐条回写本节**（既有缺口，见下「D1 / D3 提交元信息行」行的同款追注） | §4 + 原型（§0.3）+ 原型（2026-09-10） |
| **D1 卡一：~~Latest by Dimension~~ → `Current Version`（v4.40）** | 卡头 `Current Version · {period}`（期次取**卡一实际显示的那条记录**，取哪条见 §7.8 与 v4.40）；表格三列 `DIMENSION` / ~~`BENCHMARKIT`~~ / ~~`TOP GSV QUARTILE`~~ → **2026-09-09 按原型改名（§0.24-Z4）**：**`EXTERNAL BENCHMARKS`** / **`TOP GSV QUARTILE`**（~~`(1-9)`~~ 后缀 2026-09-10 去掉，§0.26-Z2；`BenchmarkDimensionTable` 是 A4 末位基准 Tab 与 D1 两张卡共用组件，同一个概念不该在两页两个叫法，故 **D1 这两处一起改**）；⚠️ **D1 无 `Average` 行** —— ~~表尾加权 `Average` 只在传了非空 `weights` 时渲染，基准列表出参里没有权重~~ → **v4.22 起该行连 A4 都没有了**（§0.26-Z1），三处一律只有明细行。~~五行~~ → **v4.4：一维一行，行数按配置维度动态**（§0.10-D1）；维度列 `**FRL** Financial Readiness`（缩写加粗 + 全称次级色）；分值格式 `6.5/9`，`/9` 次级字号；卡头下另有**一行提交元信息**：`Submitter: {姓名 · 角色}` · `Submission time: {D MMM YYYY, HH:mm}`（组件 `BenchmarkSubmissionMeta`，与 D3 详情卡共用；时刻 = 审计列 `created_at`，走 `formatErlIsoDate()`，为空显示 `—`，§0.28-Z2） | 原型（§0.3-4）+ 原型（2026-09-10） |
| **D1 卡二：Record History** | 列 `PERIOD`（最新一条加 `LATEST` 徽章）/ ~~`RECORDED`（期末日）~~ → **2026-09-10**：列头按原型改名 **`SUBMISSION TIME`**，值改为**真实录入时刻**（审计列 `created_at`，经 `formatErlIsoDate()` 渲染 **`YYYY-MM-DD`**，为空显示 `—`，§0.28）—— 列头文案自此**名副其实**（旧口径下 `2026Q3` 的每一行恒显 `2026-09-30`，与 `PERIOD` 列 100% 冗余）/ `RECORDED BY`（姓名 + 角色两行）/ `BENCHMARKIT (AVG)` / `TOP GSV QUARTILE (AVG)`（同 `x.x/9` 格式）/ `NOTE`（空显示 `—`）/ `ACTIONS`；~~按期次**倒序**~~ → ~~2026-09-10 补次级键（§0.27-Z3）：按 `period DESC, created_at DESC, id DESC`~~ → **v4.40（2026-09-16）再改**：按 **`created_at DESC NULLS LAST, id DESC`**（纯提交时间倒序，补录旧期次的那条也排在最前）—— 同期次可有多条**并列**，最近录入的排在前面，`LATEST` 徽章只给这个排序下的**首条** | 原型（§0.3-6） |
| **D1 `Details`** | 展开该记录的**按维度明细**（**v4.4：不再写死五维**），复用 `BenchmarkDimensionTable`；数据已随列表返回，**不发新请求**（§6.5） | 本设计 |
| **D1 / D3 提交元信息行**（**2026-09-10 新增展示位**，§0.28-Z2） | D1 卡一卡头下与 D3 记录详情卡内各有一行裸小字：`Submitter: {姓名 · 角色}` · `Submission time: {时刻}` —— 同一个组件 `BenchmarkSubmissionMeta`（`benchmark/components/`），两个标签与 D1 `Record History` 的列头**同取**一份源串 `BENCHMARK_META_LABELS`，别各写字面量。时刻取审计列 `created_at`（§0.28-Z1）、走 `formatErlIsoDate()` 显示 **`YYYY-MM-DD`**，为空 `—`。⚠️ **不复用 A3 / A4 那个四格 `SubmissionMetaBar`**（那是带灰底边框的盒子，这里是裸的一行两项）。⚠️ **D3 记录详情页 `/exitReadiness/benchmark/record/:recordId` 与 2026-09-10 D1 三列改版本身尚未回写本节** —— 本行只定档这一处时间位的取值与格式 | 原型（2026-09-10）+ §0.28 |
| **D1 / D3 / D2 的期次返回上下文**（**v4.25 全行新增**，§0.29） | **口径**：期次在 D 模块**只作面包屑 / 返回按钮的返回上下文，各页取数一律不用它** —— D1 `Record History` 跨期次全量、D1 卡一取「最新一条」、D3 按 `recordId` 打开、D2 的期次由表单自己填，四处都**不按** URL 上的 `period` 过滤。~~据此认为「透传期次是它用不到的参数」~~ → **v4.25 作废**（§0.29）：页面取数用不到，**面包屑要用**；不带就等于把用户甩到服务端缺省期次那一期。落地三处：<br>· **D1 → 下游**：抽出一份 `periodQuery`，到 D2 的 `addUrl`、到 D3 的 `recordUrl(id)`、回 A4 的 `scoreDetailsUrl` **三条共用**（§0.29-Z2）。<br>· **D3 → D1**：从路由取 `contextPeriod`，面包屑第二级与右上 `Back`（正常态与错误态两处）回 D1 时带上。⚠️ **与本页「展示」的期次是两件事** —— 标题、面包屑末级、卡头 `By Dimension · {period}` 一律取**记录自身的 `record.period`**（属于哪一期是记录自己的事实），`contextPeriod` 只往回传、不参与本页展示与取数（§0.29-Z3）。<br>· **D2 → D1**：**保存成功**跳回 D1 时带上 `contextPeriod`；`Back` / `Cancel` 走 `history.goBack()` 原路退回，**不受影响**（§0.29-Z4）。<br>⚠️ 三处判空一律「期次空则整段不拼」，值走 `encodeURIComponent`。⚠️ **只补 `period`、不补其它上下文** —— 回到 A4 后当前维度 Tab 与 `portal` 药丸仍落缺省态，与 §0.25-Z2 的已知口径一致，本版不处理 | 本设计（2026-09-10 缺陷修复） |
| **D2 独立页** | 路由 `/exitReadiness/benchmark/add`，页首 `< Back` 回 D1；标题 `Add Benchmark Record` + 说明「Enter the Benchmarkit and Top GSV Quartile reference scores (1–9) for each Exit Readiness dimension for a reporting period.」（**v4.4：去掉「five」**，§0.10-D1） | 原型（§0.3-3） |
| **D2 表单** | `Period` 输入（placeholder `e.g. Q3 2026`）→ `Scores by dimension (1–9)` 表格（**每个维度一行** × 两列数字输入，**v4.4 由「五行」改**，placeholder 示例 `6.8` / `7.9`）→ `Note (optional)` 文本域（placeholder `Source of the benchmark data, peer set changes, etc.`）；底部右对齐 `Save Record`（主按钮）/ `Cancel` | 原型（§0.3） |
| **D2 校验与返回** | **全部分数框必填**（**v4.4：`2 × 维度数` 个，由「十个」改**）、范围 1–9、~~最多一位小数~~ → **v4.34（2026-09-15）：只允许整数**（前端 `parser` + `precision={0}` + `Number.isInteger` 校验；⚠️ **服务端未加整数校验**，见 v4.34）；`Period` 必填并归一为 `{YYYY}Q{n}`；~~期次重复由后端报业务错误（400，2026-09-09 订正，§4.3），错误挂在 `Period` 字段下且已填分数不清空~~ → **2026-09-10 作废**（§0.27-Z1）：**同期次可重复保存**，前端再无这条报错路径（文案常量 `benchmarkPeriodExists` 已删除，§0.27-Z4；catch 里把业务错误挂到 `Period` 字段的通用处理保留，其它保存失败仍走这条路）；~~保存成功回 D1 并刷新两张卡~~ → **v4.25 补期次**（§0.29-Z4）：保存成功回 D1 时**带上 URL 上的 `contextPeriod`**（期次空则不拼）并刷新两张卡 —— 否则 D1 的面包屑回 A4 又落到服务端缺省期次；`Back` / `Cancel` 走 `history.goBack()`，不受影响 | §5.6 / §6.5 |
| **F2 ERL Tab**（v4.0 改口径，**v4.4 列动态化 + 依据改标**，**v4.19 照原型定稿**） | 与现有 5 个 Tab 同一套表格样式（`key='6'`）；列 Company / ERL Score / ~~FRL / PRL / BERL / RRL / TRL~~ → **v4.4：维度列按接口出参 `dimensionScores: [{ code, abbr, score }]` 动态生成**（列头取 `abbr`、列序取配置 `sortOrder`，**不再硬编码五列**，§0.10-D1；`sortBy` 白名单随之动态化）（**均为 level 整数 0–9**）/ Stage / View。**v4.19 逐项定稿**（§0.23）：① `ERL Score` = **加权一位小数 + 分母**，渲染 `7.2/9`，无分数渲染 `—`（**不是 `—/9`**）；② **`Stage` 列只渲染一枚 Era 徽章**（同色文字 + 该色 10% 薄底），**stage 整数不显示**，`0` 出灰徽章 `Not yet Stage 1`、`null` 出 `—`；③ **着色只给 `ERL Score` 与 `Stage`，维度列走中性色**（**`0` 与 `—` 用不同底色，勿混**，§7.1 末段）；④ **不排序、不筛选** —— 表格上方的 Stage 下拉与分数区间框、以及**全部列头的排序器**都按原型撤下，F2 是一张纯展示表（服务端能力保留、恒不下发，§0.23-P2）；⑤ **页面不显示期次** —— 既不逐行挂在公司名后面，表格上方也**不放期次标签**（§0.23-P6；期次由前端固定为当前自然季度，靠约定而非界面标注保证一致） | §3.7（Tab 与列）+ **本设计**（排序：~~PRD §3.7~~，PRD 2026-09-03 已删除该条依据）+ **2026-09-09 原型 `/portfolio` ERL Tab**（v4.19） |
| **F2 `View` 跳转**（v3.5 改，**v4.19 改文案**） | 末列 **`View ›`**（~~`View →`~~，v4.19 按原型改为文字 + 右尖角图标）跳该公司的 **A4 全维 Score Details 页**，取后端下发的 `detailUrl`（`/exitReadiness/scoreDetails?companyId={id}&period={period}`，**不带维度**），前端不拼路径；面包屑首级回该公司 Company Overview。**v3.2 的「跳维度详情页 + 默认 FRL」与 v3.1 的「跳 Company Overview 锚点定位 ERL Card」均作废**（§0.7-3） | §3.7「View（跳转到该公司的 Score Details 页面）」+ 2026-08-28 裁决 |
| **响应式** | 桌面 + 移动均可用；表格类窄屏横向滚动、卡片单列堆叠、雷达图等比缩放 | §4「所有页面覆盖桌面与移动端」 |
| **国际化** | 文案走 `locales/`，不硬编码中文 | 前端规范 |

### 8.5 ERL Card 与维度详情页的职责划分（对 PRD 的落地解释）

PRD 中「Scorecard」（§5）的展示项分散在两处，本设计的归属如下（需产品复核 → §13-Q8）：

| PRD §3.5 展示项 | 落在 ERL Card | 落在维度详情页 | 公司端可见 |
|---------------|:---:|:---:|:---:|
| 综合 ERL 分数（v4.0：加权；**v4.4 文案定档 `Overall Score`**） | ✅ | ✅（页头） | ✅ |
| 当前 Stage 与 Era | ✅ | ✅ | ✅ |
| 本端维度分（**v4.0：level 整数**） | ✅（列表，**v4.4：条数动态**） | ✅（页头，仅本维） | ✅ |
| **对端维度分**（GSV 分之于公司端） | ✅（列表） | ✅（页头） | ❌ **v4.0 收紧** |
| 每维度 Perception Gap | ✅ | ✅ | ❌ **v4.0 收紧** |
| ~~每维度状态摘要~~ | ❌ | ❌ | — |
| ~~Strengths~~ & Priority Gaps（~~⚠️ PRD 待定~~） | ❌ | ✅（**v4.4：仅 Priority Gaps，Strengths 已删**，§0.10-D4） | ✅ **仅 `shared = true` 后**（**v4.4**，§0.10-D3） |
| ~~Data Sources & Cadence~~ | ❌ | ❌ | — |
| BPMM 参考数字 | ✅ | ❌ | ✅ |
| 雷达图 | ✅ | ❌（本维不适用多维雷达） | ❌ **v4.0：仅组合端** |
| **基准入口链接 `Benchmarkit & Top GSV Quartile ›`**（**v4.4 新增**，§0.10-D7） | ✅（雷达图正下方；**v4.60**：维度 <3 时雷达图不渲染，本链接仍在原位，§0.34-Y2） | ❌ | ❌（仅管理端。~~与雷达图同条件~~ → **v4.60 收窄**：只在端裁剪这一层同条件） |
| **A4 入口 `Full View ›`**（**v4.4 新增**，§0.10-D5） | ✅（卡头右上） | ❌ | ✅ **两端都渲染** |
| 访问历史评估记录 | ❌ | ✅（`View history`） | ✅ |
| Gap Analysis & Suggested Actions（~~⚠️ PRD 待定~~） | ✅（**v4.4：完整 Gap 区块**，含 `View details` 弹框与 `Share to founder`，§0.10-D4） | ✅（该维完整） | ✅ **仅 `shared = true` 后**（**v4.4**，§0.10-D3；`Share to founder` 按钮仅管理端） |

依据：PRD §3.1 明确列出卡片内容清单（综合分 / Stage / Gap 摘要 / 维度列表 / BPMM / 雷达图），§3.2 明确列出维度页内容。**v4.0 三处变化**：① 「每维度 Founder 分**与** GSV 分」改为「**或**（根据账户权限）」+「创始人只能查看自己的分数」⇒ 新增「公司端可见」一列并收紧三行；② 雷达图「仅 Portfolio 端」；③ 状态摘要与 Data Sources 两行随 PRD 删除（§0.9-4 / -5 / -10 / -13）。

**v4.4 四处变化**：① **E 模块（Gap Analysis / Priority Gaps）去掉 ⚠️ 待定标记** —— PRD `8324a3f` 已删「待定功能」，Goldie 进 V1（§0.10-D2，§13-Q22 关闭）；② 这两行的「公司端可见」由 ~~✅（Founder 口吻）~~ 改为 **✅ 仅 `shared = true` 后** —— 双 audience 方案取消，改为 GSV 主动 Share（§0.10-D3）；③ Strengths 删除，E2 只剩 Priority Gaps（§0.10-D4）；④ 新增 `Full View ›` 与基准入口链接两行（§0.10-D5 / D7）。

> **A4 基本不参与本表的划分**（v3.5，v3.6 微调，v4.4 补入口，**v4.20 收回页头判断**）—— 它承载「逐题明细的全维平铺」+ 基准 Tab，~~**外加页头的加权 `Overall Score` 与 Stage**（v3.6：A4 是 F2 `View` 的落地页，PM 点进来必须先看到整体判断，§0.8-12）~~ → ❌ **v4.20 作废**（§0.24-Z2，需求方裁决「严格照原型」）：**A4 页头只有 H1，不再显示任何分数** —— PM 的「整体判断」在 F2 该行（`ERL Score` / `Stage`）与 ERL Card 上，进 A4 是为了看逐题依据。（**v4.4：A4 也是两端 ERL Card `Full View ›` 的落地页**，§0.10-D5）；Scorecard 的其余展示项（Perception Gap / Priority Gaps / BPMM / 雷达图）一律不在 A4 上重复，见 §8.4「A4 与 A3 的关系」。**v4.4 唯一例外**：A4 每张维度卡卡头承载 `+ Add New` / `View history` 两个**维度级操作入口**（不是展示项，见 §8.4「A4 维度卡」）。

### 8.6 Company Overview 三卡布局方案（v4.0 全节重写，**v4.3 订正为两列**，PRD §3.1）

**PRD 现要求**（2026-09-02 `621e857`）：

> Company Overview 页原有的 DI 卡片**放在 FI 卡片下**；DI 数据、打分**保留概览信息和入口**。
> 原 DI 卡片位置由新的 ERL 卡片替代。

即：**DI 不再下线**，只是**让位**。

> ⚠️ **v4.3 订正 —— 「位置」不是「顺序」**：v4.0 / v4.1 把这段读成「三张卡纵向排成一列 ERL → FI → DI」，据此把 `.btmContent` 从 `row` 改成 `column`、把两张卡的 `604px` 改成 `100%`。这是误读：**存量 Company Overview 本来就是左右两列**（`.btmContent{ display:flex; flex-direction:row; justify-content:space-between }`，`.finanStyle` / `.deveStyle` 各写死 `604px`，左 FI、右 DI），PRD 说的「原 DI 卡片的位置」指的是**右列**，「DI 放在 FI 卡片下」指的是 DI 落到**左列 FI 的下方**。原型 Company Overview 截图与这个读法完全一致。**两列布局是存量事实，不是本设计新引入的东西。**

三张卡的最终布局：

```
Company Overview 页（Revenue / Financials 两张通栏卡在上，不变）
  ├── 左列  ├── FI Card    ← 存量，位置不变（Financial Intelligence）
  │        └── DI Card    ← 存量，由右列移到左列 FI 之下；概览信息与下钻入口全部保留
  └── 右列  └── ERL Card   ← 新增，占据原 DI 卡片的位置与栅格宽度
```

落地方案：

1. **前端**（`CompanyOverviewPage.tsx`）：`bottomHtml` 内加两个列容器 —— 左列 `.btmLeft` 收 FI（Automatic / Manual 两个分支）+ DI，右列 `.btmRight` 放 `<ErlCard />`。**DI 的渲染条件 `DiStatus` 原样不动** —— 它仍按公司级开关决定 DI 卡显隐，语义与现在完全一致。
   - 列宽用 `flex: 1 1 0` 等分而**不再写死 `604px`**：`.mainover` 内容宽 1232、列间距 24，算出来正好 604，与存量像素一致，但容器变窄时不会溢出。
   - 两个列容器**必须带 `min-width: 0`**：左列的 FI / DI 里有宽表格与长数字串，flex item 默认 `min-width:auto` 会被内容撑破，把右列挤没。
   - `.btmContent` 加 `align-items: flex-start`，让两列各自按内容高度收尾（右列 ERL 通常比左列矮）；`max-width: 1024px` 以下回落单列纵排。
2. **后端**：**无改动**。~~新增系统级配置 `erl.enabled`~~ → **v4.0 删除**：PRD 已不要求隐藏 DI，没有任何东西需要这个开关来控制（§0.9-6）。`erl_init.sql` 中该配置项的初始化一并删除。
3. **不动 `diStatus` / `diWeight` / `fiWeight`**：与 v3.x 结论一致，这三个值仍影响 SDP 总分与 Company Settings 的模块页。**v4.0 的方案连碰它们的理由都没有了** —— 卡片顺序是纯前端布局问题。
4. **Company Settings 的 Modules 页**：**无需加说明**（v4.0 改）—— DI 开关的效果没有被 ERL 接管，打开就显示、关闭就隐藏，行为与现在无差别。原 §8.6-4 的说明行与 §10.3 的对应改动一并删除。

> ✅ **v4.4 复核**：本节结论（两列布局、DI 让位到左列 FI 之下、后端零改动）**全部保持不变**。本节**不含任何「五维」硬假设** —— 它只管三张卡的栅格位置，ERL Card 内部的维度列表条数由接口驱动（§0.10-D1），维度增减不影响布局；卡内新增的 `Full View ›` 与雷达图下方链接（§0.10-D5 / D7）也只在卡片内部排布，不改栅格。
>
> ✅ **v3.x 的两个风险点均已消失**：① 「系统级 vs 公司级开关」的差异（原 §13-Q2 主体）—— 不再需要任何系统级开关；② 「新增 `erl.enabled` 属字面偏离 PRD『使用现有 setting/toggle』」（原 §0.8-9）—— 该偏离物已删除。**§13-Q2 整条关闭。**
>
> ⚠️ **仍需注意**：DI 卡片换列后，`CompanyOverviewPage.tsx`（已超 2300 行、DI/FI 分支混杂）的 JSX 结构调整范围不小，容易带出样式与栅格问题 —— **v4.3 的实际教训**：v4.0 那次改动顺手把存量的两列栅格压成了单列，直到看到原型截图才发现。该文件的拆分建议已记入 §10.4 待优化项。

---

## 9. 失败降级

| 场景 | 服务端 | 前端表现 |
|------|--------|----------|
| **展示期次缺省 = closed month 所在季度，该季度两端均无提交**（**v4.4 全行新增**，§0.10-R3） | 接口 1 / 17 / 22 等所有「`period` 可选」的读接口，缺省期次一律取 **该公司 closed month 所在季度**（~~**v4.19：接口 20 / F2 除外**~~ → **v4.33 撤回，接口 20 同样走缺省**，§0.23-P1）（closed month 沿用 Financial Intelligence 域既有口径，按公司 Manual / Automatic 两种推导，ERL 域**复用 FI 既有服务、不自己算**）。该季度**两端均无提交** → 返回**空态**（分数 `null`、`dimensions[]` 按**当前 `status = 'Active'` 的维度集合**返回但分数全 `null`），**明确不回退到更早期次** | ERL Card / A3 / A4 / Gap 区块显示该季度的**空态**（`No assessment for {period} yet.` + 去填报入口），期次 chip 照常显示该季度；⚠️ **不得**悄悄显示上一季的数据 —— 用户看到的期次标签必须和数据是同一个期次 |
| **closed month 取不到（公司无任何 actuals、FI 侧抛异常、格式不可解析）**（**v4.4 全行新增**，**v4.33 全行改判**，§0.10-R3） | ~~**同样返回空态**，**不回退**到「最新已提交期次」，也不猜当前自然季度~~ → **v4.33（2026-09-15 裁决）：回退​**当前自然季度**（UTC）**，WARN 日志（含 `companyId`）保留。⚠️ 该季度通常一份提交都没有 ⇒ 落到上一行的「该季度两端均无提交」走空态，**但期次此时是确定的** | ERL Card 走该季度的空态，**期次 chip 显示该当前季度**（不再是 `—`）；`Reporting period unavailable.` 这句次级说明**因此只剩 `companyId` 为空这一条防御分支可达**，前端逻辑不动。⚠️ **代价**：季度初财务尚未结账时，屏上会出现一个**财务尚未闭合**的季度标签 —— 这正是 R3 当初想避免的，2026-09-15 由需求方明确取舍 |
| ~~**展示期次缺省 = 最新已提交期次**~~ | ~~取该公司最新一条 `is_latest` 提交所在期次，无提交时回退更早期次~~（**2026-09-08**：`is_latest` 列已删除，本行只作历史留存） → **v4.4 作废**（§0.10-R3，需求方 2026-09-06 裁决）：这套降级会**悄悄显示上一季的数据**，与卡片上的期次标签不一致，是本版必须改掉的行为 | — |
| 该公司无任何已提交评估 | 接口 1/2 返回空结构（分数 `null`、`hasAnyAssessment=false`） | ERL Card 显示空态「No assessment submitted yet.」+ 去填报入口；不显示雷达图 |
| 只有 Founder 提交、GSV 未提交 | `gsvScore = null`、`perceptionGap = null`（**v4.0：`status` 出参已删除**） | **管理端**：维度行显示 Founder 分并标注 `Awaiting GSV validation`，Perception Gap 隐去；雷达图 GSV 序列不绘制。**公司端**：本就不展示 GSV 与 gap，页面无任何变化 |
| 只有 GSV 提交、Founder 未提交 | `founderScore = null`、`perceptionGap = null` | 管理端对称处理，标注 `Awaiting founder self-assessment`；**公司端显示与「无任何提交」相同的空态**（它看不到 GSV 那份，§4.2） |
| **维度分为 `0`（level 1 内即有 No）**（**v4.0 新增**） | `levelScore = 0`（**不是 `null`**）、`terminatedLevel = 1`；**照常计入加权综合分** | 维度行显示 `0/9` + 灰色 `Not yet Stage 1` 徽章（§7.3）；**不得显示为 `—`** —— `—` 是「无数据」，`0` 是「有数据且很低」，混淆会让用户以为没填（§7.1 末段） |
| **某维在该题集版本内 0 题**（**v4.0 改**） | `levelScore = null`；**该维不进综合分**，其余维度权重**按比例归一化**（§0.9-20）；~~提交时该维视为已终止、不拦提交~~ → **2026-09-07 订正：该维不可提交**（§6.3 校验 3） | 维度行显示 `—`；综合分旁 tooltip `Weighted over {n} of {total} dimensions ({缺失维度列表} has no published questions).`（~~v4.4：分母由写死的 `5` 改为该期次绑定配置版本的维度数~~ → **2026-09-08：改为当前 `Active` 维度数**，§0.10-D1）；填报页该维度走空态 |
| 无基准记录 | `benchmarkPosition = null`、`latest = null`、`records = []`、雷达图两条基准序列缺省 | A3 隐去基准位置项；D1 两张卡合并为一处空态 `No benchmark records yet.`（**空态内不放按钮** —— v4.56 起需求方撤下，新增入口只剩页头那颗 `+ Add New`，口径同 A4 基准 Tab：按钮在卡头、空态只有配图与文案）；雷达图图例不显示缺失序列 |
| **展示期次早于最早一条基准记录** | 无 `period ≤ 当前期次` 的记录（§7.8） → 同「无基准记录」处理，**不取更晚的记录反填** | 同上 |
| ~~**D2 保存时该期次已存在**~~ → **2026-09-10 整行作废**（§0.27-Z1） | ~~唯一约束冲突 → `BadRequestException`~~ → **不再是失败场景**：服务端 `assertPeriodNotTaken` 与唯一索引 `uk_erl_reference_score` 双双删除，**同期次照常落库为新的一条记录** | ~~`Period` 字段下报错 `A benchmark record for this period already exists.`；已填的十个分数与备注保留~~ → 保存成功回 D1 并刷新两张卡，该期次此后有多条并列，`LATEST` 徽章落在最近录入的那条（§0.27-Z3） |
| **公司端请求**（**v4.0 大幅收紧**） | 服务端裁剪掉：整个 `radar` 字段、`gsvScore`、`perceptionGap` / `gapDirection`、`benchmarkPosition` 与全部基准值（§4.3） | **不渲染雷达图区块**（不是「渲染 2 条线的图」—— v3.x 方案作废，§0.9-5）；维度列表只有「维度名 + 本端分 + View Details」三列，**不留空列、不显示 `—` 占位** |
| **权重未配置 / 合计 ≠ 100%**（**v4.0 新增，v4.4 微调，2026-09-17 改判**） | ~~理论上不会发生（接口 24 强校验 + 种子数据等权）~~ → **2026-09-17（v4.55）起这是新库的默认路径而非异常路径**：种子段删除后，任何组织在配置页保存第一组维度之前 `erl_dimension_config` 都是零行。库中数据异常（改坏权重）时同样走这一支：**按等权（各 `100 / {Active 维度数}`%，v4.4 由写死的「各 20%」改；**2026-09-08**：触发条件补「`Active` 行合计 ≠ 100」）**，§0.10-D1）降级计算并打 WARN 日志，**不抛异常** —— 综合分不该因配置数据坏掉而整页报错 | 综合分正常显示，旁加 tooltip `Weights unavailable — using equal weighting.`；配置页 **`Dimension Configuration`** Tab（**v4.4 改名**）顶部红条提示需重新保存 |
| ~~**该期次找不到绑定的配置版本**（v4.4）~~ → **2026-09-08 整行作废** | `erl_company_period_config` 已整表删除（§5.1.4），不再存在「期次绑定配置版本」这个概念，本降级场景自然消失 —— **任何期次一律读当前 `Active` 集合** | — |
| **维度已被停用（`Inactive`）、但历史期次用过它**（v4.4 新增，v4.8 换依据，**2026-09-08 换机制**；**2026-09-09**：已发布过的维度**只能**停用、删不掉，故这仍是历史期次唯一会遇到的情形；已删（`deleted = true`）的维度行同样留着、名称与缩写同样解得出，**降级行为与本行完全一致**，区别只在配置页两处都不显示它） | 软删后行仍在，历史提交记录照常返回；该维名称 / 缩写取 `erl_assessment.dimension_name` / `dimension_abbr` 行上快照（§5.2），`status` 直接下发 `Inactive` | 历史期次的维度行 / 雷达图顶点 / A4 维度卡**照常渲染**，并加灰色 `Retired` 标注（**由 `status` 列直接判定，不再派生**）；该维**不出现**在新期次的填报、题库 Tab 与配置页的默认维度列表中。⚠️ ~~历史分数、Stage 与雷达图形状不漂移~~ → **2026-09-08 作废：会漂移**（权重不快照、停用维度退出当前集合，§7.11）。⚠️ ~~**v4.11 例外待重新裁决**：C7 「不显示已删维度」原靠物理删除判定，软删后需改判 `Inactive` 或整条取消（§0.17）~~ → **2026-09-09 关闭（v4.17，§0.22-Y3）：整条取消** —— **C7 不是本行的例外了**：它既不隐藏这类维度、也不给它打 `Retired` 灰标（**C7 是全站唯一撤掉该灰标的地方**；本行描述的历史期次 A1 / A2 / A4 / 雷达图**照常打标**），只按 §5.1.5 的发布当时快照整卡展示 |
| **改答收回 level 后再打开页面**（**v4.0 新增**） | 已删除的后续 level 答案与附件不再返回；`unlockedLevel` 为回退后的值 | 填报页只渲染到回退后的 level；**不显示「你曾答过但被清除」的历史**（PRD 无此要求，且会让页面语义混乱） |
| **无差距分析记录**（**v4.4 细化为三态**，§0.10-D4） | 接口 17 返回 `summary = null`，但 **`dimensions[]` 照常返回该期次每个维度**（含 `bothSubmitted` / `hasGap`），**不是空数组** | 区块整体仍渲染（标题 + `AI GENERATED` + 期次 chip + 计数 `0 of {total} dimensions have gap analysis for {period}`）；`summary` 位置沿用原型空态文案 **`No gap analysis yet`** + **`Goldie needs scored questions with evidence notes for this dimension before it can suggest gaps and recommended actions.`**；管理端多一个 Generate 按钮。**每维小卡按下面三行分别取态** |
| **某维：双方已提交且有 gap**（**v4.4 新增**） | `bothSubmitted = true`、`hasGap = true`，`items[]` 非空 | 小卡 **绿点 + `Gap analysis ready`**；`View details` 弹框内该维分区列出 gap 与 `actions[{title, why}]` |
| **某维：双方已提交但无 gap**（**v4.4 新增**） | `bothSubmitted = true`、`hasGap = false`，该维 `items[]` 为空（**没有 gap 就不产出条目** —— `STRENGTH` 枚举已删，不再用「优势」占位，§0.10-D4） | 小卡 **绿点 + `No Gap`**；`View details` 弹框内该维分区显示 `No gap identified for this dimension.`，**不列任何建议** |
| **某维：双方已提交但题集版本不一致**（**v4.58 新增，P4**） | `bothSubmitted = true`、`questionSetMismatch = true`、`mismatchSide = FOUNDER \| GSV`；该维**不进**本轮分析输入，故 `items[]` 正常为空（上一代旧条目若还在产物里也照常下发，由前端按优先级挡住） | 小卡 **黄点 + `Question set mismatch`**；`View details` 该维分区出琥珀药丸 + 说明 —— 管理端按 `mismatchSide` 指明落后的一方（`The founder has not submitted the latest question set for this quarter.` / `Your team has not submitted…`），公司端一律中性（`Gap analysis is unavailable for this dimension because the two sides answered different question sets.`）。**旧条目与旧 `narrative` 都不渲染**；计数文案与 Share 门槛均不受影响（§0.32-Y5 / Y8） |
| **某维：未双方提交**（**v4.4 新增**） | `bothSubmitted = false`（缺 Founder 或缺 GSV 或两者都缺），该维不参与生成 | 小卡 **灰点 + `Not submitted`**；⚠️ **圆点颜色只表示「双方是否都已提交」，文字只表示「有无 gap」** —— 前端**不要**把两者压成一个枚举渲染 |
| **Share 门槛未达成**（**v4.4 新增**，§0.10-D3） | 该 `(company, period)` 下**存在任一 `Active` 维度**未满足「FOUNDER 与 GSV 两端都有 `SUBMITTED` 记录」（**2026-09-08**：`is_latest` 已删，改按 `submitted_at DESC, id DESC` 取组内首条判存在） | `Share to founder` **置灰**，~~tooltip 列出还差哪些维度~~ → **v4.32 作废**（需求方 2026-09-15 圈图撤下，置灰时无悬停提示）；区块底部常驻提示 **`Share unlocks once gap analysis is available for all {total} dimensions in {period}.`** |
| **公司端且 `shared = false`**（**v4.4 新增**，§0.10-D3） | 接口 17 对公司端**直接返回空态**（不下发 `summary` / `items` / `dimensions` 的分析内容），§4.3 后端强制校验 | ERL Card 该区块显示 `No gap analysis shared yet.`；**不渲染** `View details`、`Share to founder`、每维小卡；维度详情页 E2 区块同样走该空态 |
| **Share 后又有新提交触发重生成**（**v4.4 新增**，§0.10-D3） | 重生成时 **`shared` 复位为 `false`**（`shared_at` / `shared_by` 保留作历史） | 公司端**回到未分享空态**（已看过的内容消失属预期）；管理端按钮回到可点态并提示 **`Content updated — reshare to founder.`** |
| **分析已过期（现算指纹 ≠ 产物里存的 `submission_signature`）或正在生成** | 返回旧内容 + `stale/generating = true`（**2026-09-19：`stale` 为 Java 现算派生、`generating` 由 Python 在 GET 时回传**，§0.33-X2） | **继续展示旧内容不清空**；~~卡片顶部条 `Refreshing analysis…`~~ **2026-09-20 撤下**（§0.38-K1），进行时由维度小卡逐维表达 |
| **LLM 生成失败 / 超时** | **Python 侧**重试 2 次后放弃（退避 2s / 4s），**不写库、不覆盖已有分析**（指纹因此仍不相等 ⇒ 下一次读自动重投，触发点 B）；手动接口 18 抛 `ServiceException` | 手动触发时提示 `Gap analysis failed. Please try again.`；自动失败静默保留旧内容（`Refreshing` 条已于 2026-09-20 整体撤下，§0.38-K1） |
| **LLM 返回结构不合法** | Java 侧校验**`dimension_code` 是否属于当前 `Active` 的维度集合**（**2026-09-08**：原「该期次绑定的配置版本」作废）（**v4.4：由「校验维度枚举」改** —— `ErlDimensionEnum` 已删，§0.10-D1）与 `severity` 值域；非法 `severity` 降级 `MEDIUM`；~~缺失维度该维 items 为空~~ → **2026-09-08 作废**：维度标识改用 `index`（§6.6），**越界 / 重复 / 缺失一律打 ERROR + 保留旧内容**，**不得静默降级成「该维无 gap」**（否则是假阴性：页面显示绿点 `No Gap`，GSV 以为该维没问题）；~~缺失某个 audience 则该 audience 不覆盖旧数据~~ → **v4.4 作废**（§0.10-D3）：**双 audience 方案已取消**，只有一份内容，整份生成失败即不覆盖旧数据 | ~~缺失维度的小卡按 `hasGap = false` 渲染（绿点 + `No Gap`）~~ → **2026-09-08 随左栏一并作废**（v4.57 补订正：该描述与左栏「不得静默降级成『该维无 gap』」直接打架，是 2026-09-08 改 `index` 时漏改的残留）。**整份生成失败 ⇒ 不覆盖旧数据**，页面显示的是**上一代分析**（含它的 `stale` 标记）；从未生成过则保持空态。小卡的 `Not submitted` 由两端提交情况决定，与本行无关 |
| **无证据可依据**（原「无备注可依据」，**2026-09-18 口径放宽**，v4.57，§0.31-Z8） | 该题**既无备注、又无可用附件摘要**时，据其产出的 item 带 `evidenceMissing = true`（~~只看有无备注~~ 作废 —— 那会把证据放在附件里的题错标成「未提供备注」）；**备注为空但有可用摘要 ⇒ `false`**。判定在 prompt 里做，服务端只做透传归一 | 条目下方灰字 **`No supporting evidence provided`**（~~`No notes provided`~~；前端串名 `noNotesProvided` **沿用原名**、只换值）（PRD §5「如无笔记，标注为未提供备注」） |
| **附件摘要生成中（`PENDING`）**（**2026-09-18 新增**，§0.31-Z6） | 差距分析**不等待**：该附件以 `summaryAvailable = false` 送入 prompt，prompt 明令**不得凭文件名推断其内容**。整份分析照常产出、不报错 | 附件 chip 显示处理中；Gap 区块无任何异常表现 |
| **附件摘要生成失败**（原「附件入知识库失败」，**2026-09-18 换语义**，§0.31-Z5） | `ingest_status = FAILED`（**列名沿用、语义为摘要生成状态**），**不阻断评估提交**；差距分析同上按无摘要处理 | 附件 chip 显示告警图标 + `Retry` |
| **附件解析抽不出内容**（**2026-09-18 新增**，§0.31-Z3） | 摘要-only 管线在拿到空白正文时即抛「抽不出内容」并判该条目 `FAILED` —— **绝不静默成功**（否则库里会留下一条 `content_text` 与 `summary` 都为空、却标 `SUCCESS` 的条目）。扫描件 / 图片照走 OCR，OCR 失败走既有的部分成功路径 | 同上：附件 chip 告警图标 + `Retry` |
| **附件上传中提交** | 服务端只认已落 `erl_answer_attachment` 的附件（**v4.6 表名**） | 提交前 flush 上传队列；仍在传的文件弹提示「N files still uploading」 |
| **附件超过 10MB**（**v4.0 新增**） | 服务端按 `files.length` 复核后 `BadRequestException`（**2026-09-09**：原先复核入参 `fileSize`，该入参已删；前端可被绕过，服务端是底线，§6.7） | 选择文件时即在本地拦下，提示 `File exceeds the 10 MB limit.`，**不发起上传**、不占用上传队列 |
| **对未解锁 level 的题提交答案**（**v4.0 新增**） | `BadRequestException("Answer levels in order.")`（§6.3） | 正常交互下不会触发（未解锁题面不下发）；触发时提示重新加载问卷 |
| **A4 该端在该期次无提交（v3.5，v4.4 改，**v4.20 改呈现**）** | 接口 22 返回 `submission = null`；`dimensions[]` **按当前 `status = 'Active'` 的维度集合返回**（条数动态，§0.10-D1），`score = null`、`questions[] = []` | **维度 Tab 与卡片照常渲染**（卡头 `0 questions`，`+ Add New` / `View history` 仍可点），卡内四格元数据栏 **`PERIOD` 回退为当前展示期次、其余三格 `—`**（期次是页面级已知的信息，跟着 `—` 一起空掉反而让人以为连看的是哪个季度都不确定），题目区空态**按端出文案**：**`No GSV submission for this period.`** / **`No Founder submission for this period.`**（管理端取当前药丸，公司端恒 `Founder`；**不是** `No assessment for {period} yet.`）；~~组合端同屏并列时缺失的那一端标 `Not submitted`~~ → **v4.20**：组合端切到缺失的那一端时该端走同一条按端文案（§0.24-Z5）；页面不整体空白 |
| **A4 公司端（v3.5，v4.4 改，**v4.20 改呈现**）** | 服务端不下发 `benchmark`，且拒绝 `portal=GSV` | ~~**不渲染** GSV Tab~~ / ~~公司端本就不渲染任何端切换器（组合端才同屏并列两端）~~ → **v4.20**：公司端**不渲染 `GSV` / `Founder` 药丸、不渲染 GSV 侧内容**（§0.24-Z5）；**末位基准 Tab 整个不渲染**（判据是端类型，**不是** `benchmark == null` —— 后者在管理端无记录时同样为 `null`，§0.24-Z4）。⚠️ **公司端可正常进入 A4**（`Full View ›`），不再是「有权限但无入口」（§13-Q17 已被 PRD `57225d2` 推翻） |
| **A4 该公司无任何评估（由 F2 `View` 或 `Full View ›` 进入，v3.5，v4.4 改，**v4.20 改呈现**）** | `submission = null` 且无可用期次（含 §0.10-R3 的 closed month 空态） | ~~页头与**全部**空维度卡照常渲染~~ → **v4.20**（页头已无分数、维度改横向 Tab，一次只渲染一维）：**维度 Tab 与当前那一维的空卡照常渲染**，顶部一句 `No assessment for {period} yet.`（无可用期次时 `No assessment submitted yet.`）；发起入口为**每张卡卡头的 `Add New`**（~~页级 `+ New`~~ 已取消，§0.10-D5）；**不报错、不 404** |
| F2 某公司在**当前自然季度**无评估（**v4.19 换期次口径**，§0.23-P1） | 该行 `overallScore = null`、各维 `score = null`，`detailUrl` **仍下发**；**不回退到更早期次** | `ERL Score` 与各维度列显示 `—`，**Stage 列显示 `—`**（**v4.19：不再留空** —— 空单元格与「没渲染出来」分不清），`View ›` 仍可点（**v3.5 改**：进该公司 **A4 全维页**看空态；v3.2 的「进维度详情页」作废）。⚠️ **本页不标期次**（§0.23-P6）—— 整表全 `—` 时看不出是哪个季度的空态，需经 `View ›`（`detailUrl` 带 `period`）进 A4 才看得到 |
| 草稿保存失败（网络） | — | ~~吸底条红色提示 `Draft not saved — retrying`，本地保留未保存变更并自动重试；离开前二次确认~~ → **v4.30 订正**（自动保存取消后既无自动重试、也不做离开拦截）：吸底条红色提示 **`Draft not saved.`**，本地作答原样留在页面上，**由用户自己再点一次 `Save as draft`** |
| **在填期间题库发布了新版（v3.4，v4.4 订正）** | **不是降级场景，是正常路径**：评估恒按 `question_version_id` 渲染与计分，服务端行为与没发布过完全一致。**v4.4**：接口 3 出参补 `latestPublishedVersionNo` + `hasNewerQuestionSet`（§0.10-D10） | ~~填报页**无任何提示、无任何变化**；仅页头次级文字 `Question set v{n}` 可看出用的是哪版~~ → **v4.4 作废**（§0.10-D10，PRD §3.3 `4f959bb`「若题库已更新，则**提示**题库更新，不做强制退出和更新」）：~~填报页顶部挂一条 **非阻断、可关闭、无操作按钮**的 banner —— **`The question library has been updated (v{n}). This assessment continues on v{m}.`**；作答、计分、提交**均不受影响**~~ → **2026-09-15 需求方圈图作废**（v4.41 回写，见 §8.4）：改为**强阻断二选一弹窗**，**存过草稿**且 `hasNewerQuestionSet` 时一进页面就弹、不可关闭，必须在「按旧题库就地提交」与「Reset 换新题库」之间选一个 —— **服务端行为仍不受影响**（版本锁定本体不变），~~页头次级文字 `Question set v{m}`~~ 已于 2026-09-10 撤下 |
| **提交时绑定版本已不是最新（v3.4）** | **不校验、不拦截**（v3.3 的前置校验 0 已删除），正常提交 | 无提示；历史列表该行标 `Question set v{n}`，与新版本提交的行分母不同属正常（§7.10-N2） |
| **配置页有草稿但未发布（v3.3）** | 填报页 / 维度页 / 计分**读不到任何草稿变更**，行为与没改过完全一致 | 无任何感知（这是版本化的目的）；仅配置页显示 `Draft v{n} — unpublished changes` |
| **某维度在已发布版本中 0 题（v3.3）** | 同「题库为空」：该维度 `levelScore = null`，`totalCount` 不含未发布内容 | 填报页该维度显示空态 `No questions published for this dimension yet.`（**v4.4：填报单元＝单个维度，此时整页即空态，`Submit` 禁用**，§0.10-R1）；维度详情页维度分显示 `—`；配置页则正常列出草稿内容 + `Publish` 提示 |
| **提交时题序已变更（v4.0 改）** | 不阻断，且**因版本锁定而不可能影响本次评估** —— 评估恒按自己绑定的版本渲染与计分（§7.9-⑤） | 无提示。⚠️ **v4.0 注意**：题序现在**直接影响 level 内的作答顺序**（PRD §3.8「该顺序即评估中的必答顺序」），但**不影响维度分** —— 维度分只看「该 level 是否全 Yes」，与 level 内答题先后无关 |
| **某 level 内混有 Yes 和 No（v4.0 新增，v4.28 改口径，v4.37 换分值）** | 扫到**第一道 No** 即 `BLOCKED`，~~`levelScore = level − 1`~~ → **v4.37**：`levelScore = 该维上一个整级通关的 level`（一级都没通关则 `0`；level 连续时与 `level − 1` 同值）；**该 No 之后的题不必作答**（v4.28）；已答的那些（含 Yes）**照常保留并传给 Goldie**（§6.6） | 该 level 组头标 `Stopped here`，组内逐题各显示自己的 Yes / No 徽章；**不把整组显示为 No** |
| 重复提交（**该条记录**已 SUBMITTED） | `BadRequestException` | 提示已提交并跳转到该次提交的只读详情。⚠️ **v4.4 区分**：这指「同一条 `erl_assessment` 被提交两次」；**该期次该端该维再提交一份新的**是**正常路径**（`submissionCount > 0` 时按 §0.10-D11 的第二套确认文案弹窗，新记录因 `submitted_at` 最大而成为该维 SOT（**2026-09-08**：`is_latest` 列已删），历史提交保留） |
| **并发写同一行（乐观锁冲突）**（**2026-09-07 新增**） | `@Version` 版本号不匹配 → `ObjectOptimisticLockingFailureException`，由 `GlobalExceptionHandler` 统一转成 **HTTP 200 + `success: false`**（业务错误口径，`coding.md §1`），文案 `This record was changed by someone else. Please reload and try again.`；日志记 **WARN 带异常**（并发竞争是可恢复的正常竞争，不需要人介入，记 ERROR 会污染 Sentry 告警面）。注：写路径的草稿行取数已加悲观锁（§7.7），本分支主要覆盖题库发布与其它未加锁的写入 | 提示后重拉当前接口即可；不阻断其它操作 |
| **`Reset` 时草稿已被他人清空 / 已提交**（**v4.4 新增**，§0.10-D8 / D9） | 接口 28 找不到 `DRAFT` 记录 → 幂等返回成功（不抛异常） | 提示 `Draft already cleared.` 并重拉接口 3 重绘；若该维已被他人提交，则重绘为**只读态**并提示 `This dimension was submitted by another user.`（草稿为公司共享、不区分账户，§0.10-D9） |
| 跨端越权访问 | `BadRequestException` | 统一错误提示，路由守卫先行拦截 |

---

## 10. 改动文件清单

### 10.1 CIOaas-api（新增业务域 `erl/`）

```
gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/erl/
├── interfaces/controller/     ErlCardController / ErlDimensionController
│                              ErlAssessmentController / ErlQuestionConfigController
│                                ← **v4.4**：ErlAssessmentController 增 `discardDraft()`
│                                  （**接口 28** `DELETE /erl/assessment/draft`，Reset 按钮，§0.10-D8）
│                              ❌ **v4.4 删除**：ErlWeightController（v4.0 的接口 23/24）
│                              ErlDimensionConfigController（**v4.4**，接口 23/24：
│                                `GET` / `PUT /erl/dimension/config` —— 维度集合 + 排序 + 权重
│                                **整组**读写，§0.10-D13）
│                              ErlBenchmarkController / ErlGapAnalysisController
│                                ← **v4.4**：ErlGapAnalysisController 增 `share()`
│                                  （**接口 27** `POST /erl/gapAnalysis/share`，仅管理端，§0.10-D3）
│                              ErlPortfolioController
├── interfaces/vo/request/     ErlCardQueryRequest / ErlDimensionQueryRequest
│                              ErlScoreDetailsQueryRequest（v3.5，A4）
│                              ErlAssessmentQueryRequest / ErlAssessmentSaveRequest
│                              ErlAssessmentSubmitRequest / ErlQuestionConfigCreateRequest
│                              ❌ **v4.4 删除**：ErlWeightSaveRequest（v4.0，接口 24）
│                              ErlDimensionConfigSaveRequest（**v4.4**，接口 24：整组维度
│                                集合 + 排序 + 权重，服务端校验合计 = 100.00）
│                              ErlGapAnalysisShareRequest（**v4.4**，接口 27）
│                              ErlAssessmentDraftDiscardRequest（**v4.4**，接口 28：
│                                `companyId` / `period` / `portal` / `dimension`）
│                              ErlQuestionConfigUpdateRequest / ErlQuestionConfigReorderRequest
│                              （Publish 无入参，接口 21 不需要 Request VO）
│                              ErlQuestionConfigVersionResponse（v3.3）
│                              ❌ **2026-09-08 删除**：ErlChangeSummaryResponse —— `change_summary`
│                                 列已删（§5.1.1），变更摘要不再落库
│                              ErlBenchmarkCreateRequest / ErlGapAnalysisGenerateRequest
│                              ErlPortfolioQueryRequest
├── interfaces/vo/response/    ErlCardResponse / ErlDimensionDetailResponse
│                              ErlScoreDetailsResponse（v3.5，A4）
│                              ErlAssessmentResponse / ErlAssessmentSubmitResponse
│                              ErlAssessmentHistoryResponse / ErlQuestionConfigResponse
│                              ❌ **v4.4 删除**：ErlWeightResponse（v4.0，接口 23/24）
│                              ErlDimensionConfigResponse（**2026-09-08 合并**：原
│                                ErlDimensionConfigResponse + ErlDimensionConfigItemResponse 二合一
│                                —— 维度配置去版本化后没有「版本头 + item」两层，接口 23/24 的出参
│                                就是一组维度行：`dimensionCode` / `dimensionName` / `dimensionAbbr` /
│                                `sortOrder` / `weight` / `status`（`Active` / `Inactive`）/
│                                `savedAt` / `savedBy`）
│                              ErlQuestionConfigVersionHistoryResponse +
│                              ErlQuestionConfigVersionHistoryRecordResponse（v4.1，接口 25）
│                              ❌ **2026-09-08 删除**：ErlChangeSummarySnapshotResponse —— 快照列已删
│                              ← v4.2：接口 26 复用 ErlQuestionConfigListResponse，不新增 Response
│                              ErlBenchmarkResponse / ErlGapAnalysisResponse
│                              ErlPortfolioResponse
├── interfaces/converter/      ErlConverter（MapStruct，Request/Response ↔ DTO）
├── application/service/       ErlCardService(+Impl) / ErlDimensionService(+Impl)
│                                                             ← v3.5：ErlDimensionService 增 listAll()（A4 全维，
│                                                               一次查全后内存归组），复用 ErlDimensionController，
│                                                               不新建 service / controller 类（§6.2.1）
│                              ErlAssessmentService(+Impl)      ← 含提交事务 + 置脏 + afterCommit 投递
│                                                                 **v4.4**（R1）：提交单元由整卷改为**单个维度**，
│                                                                 前置校验改为「本维度到达终止态」；
│                                                                 ❌ **2026-09-08 删除**：首次创建评估时写
│                                                                 `erl_company_period_config` 的期次-配置版本绑定
│                                                                 （该表已删，§5.1.4）
│                                                                 **2026-09-08**：提交时把当前维度的
│                                                                 `dimension_name` / `dimension_abbr` 快照进评估行；
│                                                                 不再写 `submission_seq` / `is_latest`
│                                                                 **v4.4**（D8）：增 discardDraft()（接口 28）——
│                                                                 同事务删该草稿的答案行与附件行、`unlocked_level` 回 1
│                              ErlQuestionConfigService(+Impl)        ← 含 reorder 事务
│                                                                 v4.2：增 listQuestionsByVersion()（接口 26，
│                                                                 ~~五维~~ → ~~v4.4：按配置版本的全部维度~~ →
│                                                                 **2026-09-08：按 `erl_question_config_dimension_version`
│                                                                 的逐维快照解析出各维 `question_version_no`，
│                                                                 再按 `(dimension_code, version_no)` 取题**，
│                                                                 一次给全，changeType 不填）
│                              ErlQuestionConfigVersionService(+Impl) ← v3.3：ensureDraftVersion 写时复制 /
│                                                                 publish 事务 / 版本 diff（changeSummary）
│                                                                 **2026-09-08**：① 写时复制**只克隆被改动的那个维度**
│                                                                 （该维 `version_no = max(该维) + 1`），不再整库克隆；
│                                                                 ② publish 事务内为每个 `Active` 维度写一行
│                                                                 `erl_question_config_dimension_version`；
│                                                                 ③ changeSummary **不落库**，需要时实时算
│                                                                 v4.0：全部方法按 organizationId 收敛
│                                                                 v4.1：增 listVersions()（C7 只读列表，接口 25，
│                                                                 ~~直接读 change_summary 快照~~ → **2026-09-08：
│                                                                 该列已删，出参不再含 changeSummary**）
│                                                                 v4.2：增 requireByVersionNo()（按版本号取本组织
│                                                                 某一版，查不到即业务错误；供接口 26）
│                              ❌ **v4.4 删除**：ErlWeightService(+Impl)（v4.0：C6 五维权重读写）
│                              ErlDimensionConfigService(+Impl) ← **v4.4**（D1 / D13）；**2026-09-08 去版本化**：
│                                                                 list(organizationId) 读该组织维度行
│                                                                 （默认只返 `status = Active`）；
│                                                                 saveConfig() **整组 upsert**（校验维度集合合法 +
│                                                                 `Active` 行权重合计 = 100.00；提交里缺席的维度
│                                                                 置 `Inactive` 软删），**不再生成版本行**；
│                                                                 **2026-09-09**：list() 另下发 `deletable`
│                                                                 （join erl_question_config_version 过滤
│                                                                 `status = 'PUBLISHED'` —— **不是只查快照表**，
│                                                                 草稿版本上也有快照行），且**永不下发
│                                                                 `deleted = true` 的行**；saveConfig() 另按
│                                                                 `deletedCodes[]` 置 `deleted = true`
│                                                                 （可删性检查必须在 validate() 阶段、
│                                                                 任何写入之前，§0.21-X8；~~parkAll 之前~~
│                                                                 —— **2026-09-15 parkAll 已删除**，
│                                                                 保存改为单阶段直接写终态，§7.11-②）；
│                                                                 ❌ **2026-09-08 删除**：currentVersion() 与
│                                                                 versionOf(companyId, period)（期次绑定表已删）——
│                                                                 卡片 / A3 / A4 / 雷达图 / 题库 / F2 / Goldie
│                                                                 的维度列表与权重**一律经 list() 入口**，禁止各自查表
│                              ErlPeriodService(+Impl)          ← **v4.4**（R3，**跨域新增依赖**）：
│                                                                 resolveDefaultPeriod(companyId) —— 调用
│                                                                 **`fi/` 域既有 closed month 服务**（Manual /
│                                                                 Automatic 两种推导，源自 Financial Entry actuals），
│                                                                 换算为所在季度；ERL 域**不自己算 closed month**。
│                                                                 取不到 → 返回 `null` + WARN 日志，调用方走空态、
│                                                                 **不回退**到更早期次（§9）
│                              ErlBenchmarkService(+Impl)
│                              ErlGapAnalysisService(+Impl)     ← 2026-09-19 起是薄编排：ACL/期次/Active
│                                                                 维度/SOT、输入组装、Share 门槛、指纹现算、
│                                                                 mismatch 判定（落库/锁/重试已归 Python）
│                                                                 **v4.4**（D3）：增 share()（接口 27）+ Share 门槛
│                                                                 判定（每个维度两端均有 `SUBMITTED` 记录 ——
│                                                                 **2026-09-08**：`is_latest` 已删，改按
│                                                                 `submitted_at DESC, id DESC` 取组内第一条）；
│                                                                 重生成时 `shared` 复位 false
│                              ErlPortfolioService(+Impl)
│                              ErlAttachmentService(+Impl)      ← 附件登记 + 入库回写
├── application/scoring/       ErlLevelScorer（v4.0：逐级解锁计分的唯一实现，§7.2-②）
│                                computeDimension() → {levelScore, terminatedLevel, unlockedLevel}
│                                computeOverall(dimensionScores, weights) → 加权综合分
│                                **v4.4**（D1）：不再假设「五维」，null 维度分归一化的基数参数化
│                                ~~R2：`weights` 来自该期次绑定的配置版本（versionOf）~~ →
│                                **2026-09-08：一律来自当前生效的 `erl_dimension_config`
│                                （`ErlDimensionConfigService.list`）—— 权重不快照，改权重会
│                                回溯改变历史期次的综合分与 Stage（已接受，§13-Q21）**
│                              ❌ v4.0 删除：ErlScoringStrategy / Score1To9Strategy /
│                                 ErlScoringStrategyFactory（PRD 已定档，抽象无消费者）
├── application/dto/erl/       ErlDimensionScoreDTO / ErlAssessmentDTO / ErlAnswerDTO
│                              ErlLevelGroupDTO（v4.0：level 分组 + state，§6.3）
│                              ❌ **v4.4 删除**：ErlDimensionWeightDTO（v4.0）
│                              ErlDimensionConfigDTO（**2026-09-08 合并**：原 DTO + ItemDTO 二合一）
│                              ErlAttachmentDTO / ErlQuestionConfigDTO
│                              ErlBenchmarkDTO / ErlBenchmarkDimensionDTO
│                                （**2026-09-08 定档：只有实体与仓储随表改名**——
│                                 `ErlReferenceScore` / `ErlReferenceScoreItem` 及其 Repository；
│                                 DTO / Service / Controller / Request / Response **一律保留 `ErlBenchmark*`**，
│                                 HTTP 路径 `/erl/benchmark` 也不变。理由：改名的驱动力是「表名」，
│                                 实体/仓储与表 1:1 才需跟随；对外契约没有改名的理由，
│                                 全链改名反而多一批破坏性变更）
│                              ErlGapAnalysisDTO / ErlGapItemDTO / ErlRadarSeriesDTO
├── application/mapper/        ErlMapper（MapStruct，DTO ↔ Entity）
├── domain/entity/             ErlQuestionConfigVersion（v3.3） / ErlQuestionConfig
│                              ❌ **v4.4 删除**：ErlDimensionWeight（v4.0，表已被配置版本取代）
│                              ❌ **v4.4 删除**：ErlAssessmentDimension（R1：维度级提交后恒一行，
│                                 三列上提到 ErlAssessment）
│                              ❌ **2026-09-08 删除**：ErlDimensionConfigVersion（表已删，§5.1.2）
│                              ❌ **2026-09-08 删除**：ErlCompanyPeriodConfig（表已删，§5.1.4）
│                              ErlDimensionConfig（**2026-09-08 改名**，原 ErlDimensionConfigItem，§5.1.3：
│                                organization_id / dimension_code / dimension_name / dimension_abbr /
│                                sort_order / weight / status；2026-09-09 删 saved_at / saved_by）
│                              **ErlQuestionConfigDimensionVersion**（**2026-09-08 新增**，§5.1.5：
│                                题库版本 ↔ 维度快照）
│                              ErlAssessment                                ← **v4.4**：加维度列，
│                                上提 `level_score` / `terminated_level` / `unlocked_level`
│                                **2026-09-08**：`dimension` → `dimension_code` + 加 `dimension_name` /
│                                `dimension_abbr` 快照；`question_version_id` →
│                                `erl_question_config_version_id`；删 `submission_seq` / `is_latest`
│                                **2026-09-09**：加 `erl_question_config_dimension_version_id`（可空，
│                                  → §5.1.5 快照行，取题一跳直达）
│                              ErlAssessmentAnswer / ErlAnswerAttachment（v4.6 改回；
│                                **v4.4** 删 `dimension` 列，维度已在 ErlAssessment 上）
│                              ErlReferenceScore / ErlReferenceScoreItem（**2026-09-08 改名**，原
│                                ErlBenchmarkRecord / ErlBenchmarkDimension；后者加
│                                `dimension_name` / `dimension_abbr` 两列 —— 原先不落库、
│                                由 service 回填，现在是表列，**映射方向反转**
│                              ~~ErlGapAnalysis / ErlGapAnalysisItem~~  ← 2026-09-19 删除（产物归 Python）
│                                ← **v4.4**（D2）：Goldie 已回归 V1，原「E 待定，可摘除」注记撤销；
│                                  ErlGapAnalysis 删 `audience`、加 `shared` / `shared_at` / `shared_by`
├── domain/enums/              ❌ **v4.4 删除**：ErlDimensionEnum（D1：维度改为租户级配置数据，
│                                 不再是编译期枚举 —— 全仓不得再有维度硬编码）
│                              ErlEraEnum / ErlPortalEnum
│                              ErlAssessmentStatusEnum / ErlLevelStateEnum（v4.0：
│                                CLEARED / ACTIVE / BLOCKED / LOCKED，§7.2-①）
│                              ErlGapItemTypeEnum（**v4.4**：删 `STRENGTH`，收敛为 `GAP` / `ACTION`，
│                                §0.10-D4） / ErlSeverityEnum
│                              ErlDimensionConfigStatusEnum（~~`ACTIVE` / `RETIRED`、v4.8 起不落库改派生~~
│                                → **2026-09-08 改回落库**：取值 `Active` / `Inactive`，就是
│                                `erl_dimension_config.status` 列（§5.1.3）；`Retired` 灰标由列值
│                                **直接判定**，不再推导—— §0.14 与 §7.11-④ 的派生态论述作废）
│                              ❌ **v4.4 删除**：ErlAudienceEnum（D3：双 audience 方案取消）
│                              ErlIngestStatusEnum
│                              ErlQuestionConfigVersionStatusEnum / ErlQuestionConfigChangeTypeEnum（v3.3）
│                              ❌ v4.0 删除：ErlAnswerTypeEnum（双题型）、ErlScoringModeEnum（模式切换）、
│                                 ErlDimensionStatusEnum（状态摘要）
├── domain/repository/         ErlQuestionConfigVersionRepository（v3.3） / ErlQuestionConfigRepository / ErlAssessmentRepository
│                              ❌ **v4.4 删除**：ErlDimensionWeightRepository（v4.0）
│                              ❌ **v4.4 删除**：ErlAssessmentDimensionRepository（R1）
│                              ❌ **2026-09-08 删除**：ErlDimensionConfigVersionRepository
│                              ❌ **2026-09-08 删除**：ErlCompanyPeriodConfigRepository
│                              ErlDimensionConfigRepository（**2026-09-08 改名**，原
│                                ErlDimensionConfigItemRepository；查询键由 `version_id`
│                                改为 `organization_id` + `status`）
│                              **ErlQuestionConfigDimensionVersionRepository**（**2026-09-08 新增**）
│                              ErlAssessmentAnswerRepository
│                              ErlAnswerAttachmentRepository（v4.6 改回）
│                              ErlReferenceScoreRepository / ErlReferenceScoreItemRepository
│                                （**2026-09-08 改名**，原 ErlBenchmarkRecordRepository /
│                                 ErlBenchmarkDimensionRepository）
│                              ~~ErlGapAnalysisRepository / ErlGapAnalysisItemRepository~~ ← 2026-09-19 删除
├── infrastructure/client/     ErlPythonClient   ← 内网直连 Python：refresh / GET / share 三个差距分析端点
│                                                 + 附件摘要端点（只负责一次 HTTP 往返，不重试不落库）
└── infrastructure/converter/  ErlDimensionConfigStatusConverter（**2026-09-09 补记**，此前漏列）
                                 ← JPA `@Converter(autoApply = true)`：枚举 ACTIVE / INACTIVE ↔ 落库
                                   字面值 `Active` / `Inactive`；取值改名靠它落地（§5.1.3）
```

另需 `deploy/upgrade_doc/sprint{N}/erl_init.sql`（**2026-09-08 重写**）：~~11 张~~ → ~~v4.4：12 张~~ → **2026-09-08：11 张表**（删 `erl_dimension_config_version` 与 `erl_company_period_config`，增 `erl_question_config_dimension_version`，净 -1）的建表与索引（**2026-09-17：种子数据段整段删除，本脚本不再写入任何业务数据**）：

- **索引与唯一约束**：~~三个~~ → ~~v4.5：五个部分唯一索引~~ → ~~2026-09-08：四个~~ → ~~2026-09-09：三个~~ → **2026-09-15：两个** —— `uk_erl_question_config_version_draft`（§5.1.1）、`uk_erl_assessment_draft`（§5.2）（~~**`uk_erl_dimension_config_abbr`**（§5.1.3）~~ —— **2026-09-15 整条删除**，「同组织启用维度缩写唯一」这条不变量取消，迁移 `V15`，v4.31）。**累计删掉四个**：`uk_erl_dimension_config_version_latest`（表已删）、`uk_erl_assessment_latest`（`is_latest` 列 2026-09-08 删）、`uk_erl_question_config_version_latest`（`is_latest` 列 **2026-09-09** 删，§5.1.1）、**`uk_erl_dimension_config_abbr`**（**2026-09-15** 删，缩写唯一整条取消，迁移 `V15`，§5.1.3 / v4.31）；普通唯一约束另删 `uk_erl_assessment_seq`；**2026-09-10 再删一个普通唯一约束 `uk_erl_reference_score (company_id, period)`** —— 改为同键位的**普通**索引 `idx_erl_reference_score_company_period`（同期次允许重复录入，§5.6 / §0.27-Z1）。
- **键位改名**：`uk_erl_question_config_key (organization_id, dimension_code, version_no, question_key)`、`idx_erl_question_config_version_dim (organization_id, dimension_code, version_no, era_band, sort_order)`（**2026-09-08：键位补 `organization_id`**）、`uk_erl_dimension_config (organization_id, dimension_code)`、`uk_erl_answer (erl_assessment_id, erl_question_config_id)`、`idx_erl_attachment_answer (erl_assessment_answer_id)`、~~`uk_erl_reference_score (company_id, period)`~~（**2026-09-10 删除，改为普通索引 `idx_erl_reference_score_company_period`**，§0.27-Z1）、`uk_erl_reference_score_item (erl_reference_score_id, dimension_code)`；`uk_erl_assessment_draft` 与 `idx_erl_assessment_company_period` 的 `dimension` → `dimension_code`。
- **新增索引**：`uk_erl_question_config_dimension_version (erl_question_config_version_id, dimension_code)`、`idx_erl_question_config_dimension_version (erl_question_config_version_id, sort_order)`（接口 26 主查询路径）、~~**部分唯一索引 `uk_erl_dimension_config_abbr (organization_id, dimension_abbr) WHERE status = 'Active' AND deleted = false`**（**2026-09-08**；谓词于 **2026-09-09 加了一半**，漏掉后半边 ⇒ 已删行永久占着缩写且页面上看不见它，§5.1.3 / §0.21-X2）—— 部分唯一索引一度因此是四个，**2026-09-09 随 `uk_erl_question_config_version_latest` 删除回到三个**。~~ → **2026-09-15 整条删除**（`V15`，缩写唯一取消，v4.31）：`V1__erl_init.sql` **就地不再建它**，部分唯一索引**回到两个**。
- ⚠️ **`idx_erl_assessment_company_period` 升为「取最新提交」的主路径**（原先靠 `uk_erl_assessment_latest` 命中），键位需补成 `(company_id, period, portal, dimension_code, submitted_at DESC, id DESC)`。
- ~~**题库种子数据**（见 §13-Q4）：先建 `version_no = 1`、`status = 'PUBLISHED'` 的 `erl_question_config_version` 发布行；题目行按维度各落 `erl_question_config.version_no = 1`；再为每个维度写一行 `erl_question_config_dimension_version`。~~ → **2026-09-17 整条删除**（脚本不再插种子）。⚠️ **约束本身没变，只是落到了发布流程上**：Publish 时**必须为每个维度写一行 `erl_question_config_dimension_version`**，漏了就是接口 26 解析不出任何维度、C7 全空（§5.1.5 / §7.9）。
- ~~**维度配置种子数据**（**2026-09-08 简化**）：直接为每个组织插五行 `erl_dimension_config`（`FRL / PRL / BERL / RRL / TRL`，`sort_order` 1 ~ 5，`weight` 各 `20.00`，合计 `100.00`）。~~ → **2026-09-17 整条删除**：维度集合改由租户在配置页（接口 24）录入，脚本一行不插；「`Active` 行权重合计 100.00」这条不变量仍由接口 24 强校验保证（§5.1.3）。
- ~~`erl_company_period_config` 不放种子~~ → 该表已删。

> **2026-09-07 补**（**v4.14 更新**）：该脚本实际已按顺序拆成~~三份~~ → **2026-09-08：四份**（新增 `V5`）→ **2026-09-09：九份**（新增 `V6` ~ `V10`）→ **2026-09-09 当日再增一份：十份**（新增 `V11`，维度配置加 `deleted` 列）→ **2026-09-10 再增一份 ERL 脚本：`V13`**（基准期次唯一索引改普通索引，形态与执行时机见本节末尾的 2026-09-10 补记；⚠️ 编号中间的 `V12` 是 `score_log` 的性能索引、**与 ERL 域无关**，不属本设计范围）→ **2026-09-15 再增一份 ERL 脚本：`V15`**（删部分唯一索引 `uk_erl_dimension_config_abbr`，见本节末尾的 2026-09-15 补记，v4.31） → **2026-09-15 / 16 一加一删两份：`V16` / `V17`**（`erl_assessment.unanswered_count` 加列与删列，见本节末尾的 2026-09-16 补记，v4.41），都在 `CIOaas-api/deploy/upgrade_doc/sprint118/` 下、**需人工按序执行**；⚠️ **执行顺序按环境分岭**（**2026-09-09 更新**）：**三类环境分岭**（以 `sprint118/README.md` 为准；**2026-09-09 审核后按发版时点再拆两段**）：① **全新环境** `V1 → V4`（`V6` ~ **`V11`** 在这种库上都是 no-op，跑不跑都行 —— `V1` 已就地含 `deleted` 列与新谓词；⚠️ **不要**再跑 `V3` / `V5` —— 那两份是给存量库的，在空库上跑会造成「服务起得来但页面全空」）；② **存量环境**（**2026-09-09 由单一顺序拆成两段**）：**发版前**跑 `V5 → V4 → V8 → `**`V11`**，**发代码后立刻**跑 `V6 → V7 → V9 → V10`。**`V11` 排在「发版前」这一段**（**2026-09-09 新增**；**2026-09-09 补两条实质约束，v4.18**）：~~它与 `V4` / `V8` 同类 —— 加一个带默认值的列 + 重建一条部分唯一索引，**旧代码完全无感**（不查该列，且默认 `false` 让旧代码原有过滤条件的命中集合一行不变），可提前任意时间跑~~ → **方向对，但「可提前任意时间跑」不成立，且漏了一个无约束窗口**（与 `sprint118/README.md` 同口径）：**(a) 它之所以「必须」排在发版前，是因为 `ddl-auto` 在有数据的表上加不出这个 `NOT NULL` 列**（PG 拒 `23502`），而且 `ddl-auto` 加列时不带实体侧默认值 —— `V11` 是**唯一**把这一列建对的地方（「可空建列 → 回填 `false` → `SET DEFAULT` + `SET NOT NULL`」三步就是为此存在的）；漏跑则新代码上线后每条带 `deleted = false` 的读查询直接 `42703`。**(b) `V11` 跑完到 `V10` 跑完之间有一段无约束窗口** —— 此时 `uk_erl_dimension_config_abbr` 的谓词已是 `status = 'Active' AND deleted = false`，而库里的 `status` 还是旧值 `'Activate'` ⇒ **该部分唯一索引命中零行，「同组织启用维度缩写唯一」在这段时间不受任何约束**（与 `V10` 文件头描述的是同一个窗口；同批执行下以分钟计，`V10` 一跑完即恢复）。⚠️ **但仍须排在 `V5` 之后** —— `V5` 才把表改名成 `erl_dimension_config`。⚠️ **`V11` 不需要跑第二遍**：随后的 `V10` 重建那条索引时会自己看到 `deleted` 列已在、按带 `deleted = false` 的新谓词建（`V10` 第 ③ 步 2026-09-09 改为自适应）。⚠️ 「发版前」里只有 `V4`（加 `NOT NULL DEFAULT 0` 列）与 `V8`（加**可空**列）是旧代码**完全无感**、可以提前任意时间跑；**`V5` 是例外中的例外** —— 它改表名 / 改列名，**旧代码从它执行完那一刻起就 `42P01` / `42703`**，所以它必须**紧贴发版、排在这一段最前面**（`V8` 的回填还依赖 `V5` 建出来的快照表与 `dimension_code` 列）；③ **代码先上线环境**（`ddl-auto: update` 已按**改名前**的实体建过表）**`V11`**` → V1 → V4 → V6 → V7 → V8 → V9 → V10` —— ⚠️ **`V11` 在这一格必须排在 `V1` 之前**（`sprint118/README.md` 同口径）：这类库的表是 `ddl-auto` 建的 ⇒ `V1` 的建表段被 `IF NOT EXISTS` 跳过 ⇒ `deleted` 的 `DEFAULT false` 从未被应用，而 `V1` 的维度种子 `INSERT` 不显式给该列 ⇒ 撞 `23502`、**整份 `V1` 失败**（含种子）；先跑一遍 `V11` 两种情形都收敛（列不在就建、在就补 `DEFAULT` + `NOT NULL`）。 —— 那版实体上还有 `savedAt` / `savedBy` / `fileName` / `fileSize`，`ddl-auto` 会把这四列建出来而 `V1` 的建表段被 `IF NOT EXISTS` 跳过，**没有任何脚本删它们**，故 `V6` / `V7` 必须跑（列不存在时它们本就是 no-op）。<br>⚠️ **「发代码后立刻」这段窗口内的代价**：`V6` / `V7` 删的四列是 `NOT NULL` 且无默认值，代码已不写它们 ⇒ 窗口内「新增维度 / 新增附件」会撞 `23502`。这是相对 `V9` / `V10` 那种**静默空数据**的必然取舍 —— 报错可见、可重试，静默不可见。<br>⚠️ **执行方式是强制的**：`psql -v ON_ERROR_STOP=1 --single-transaction -f <script>` —— `V5` / `V9` / `V10` 的中止语义（守卫 `RAISE EXCEPTION` 后不许继续执行 DDL）**依赖这两个参数**，psql 默认 `ON_ERROR_STOP=off` 会让守卫报完错、删列照样跑。（V5 开头有守卫：跑在空库上会主动报错并点名 V1，而不是报一个裸的 `42P01`）（本仓库无 Flyway/Liquibase，README 就是唯一的 runbook）：`V1__erl_init.sql`（~~12 张表 + 五个部分唯一索引~~ → **2026-09-08：11 张表 + 三个部分唯一索引** + 题库与维度配置种子）、~~`V3__erl_question_version_add_dimension_config_version.sql`（+ `dimension_config_version_id`，可空）~~ → **2026-09-08 整份作废**（该列已删，它回填所依赖的 `erl_dimension_config_version` 也不存在了；~~该位置改为建 `erl_question_config_dimension_version` 的新脚本~~ → **2026-09-08 实际做法**：新表由**重写后的 `V1`** 建（全新环境），存量环境另出 **`V5__erl_model_refactor_20260908.sql`**（DROP / RENAME / ALTER / 建新表 + 回填，12 步、幂等）；V3 **原文件保留、SQL 整体注释掉**（README 的执行顺序依赖它的存在））、`V4__erl_optimistic_lock.sql`（两张表各 + `version`，**NOT NULL**）、**`V5__erl_model_refactor_20260908.sql`**（**2026-09-08 新增**，存量环境专用：DROP 两表 / RENAME 三表七列 / `erl_assessment` 删两列两约束 / 建新表 + 回填，12 步、幂等、**无自动回滚，跑前先 pg_dump**）、**`V6__erl_dimension_config_drop_saved_stamp.sql`**（**2026-09-09 新增**：`erl_dimension_config` 删 `saved_at` / `saved_by` 两列，`DROP COLUMN IF EXISTS` 幂等；只对**跑过旧版 `V5`、库里确实有这两列**的环境有动作，`V1` 已改为不建这两列。⚠️ **必须与 erl 代码同批发版** —— 先跑脚本后发代码，旧代码往不存在的列写 `42703`；先发代码后跑脚本，两列 NOT NULL 且无默认值，**新增维度插不进去** `23502`）、**`V7__erl_answer_attachment_drop_file_meta.sql`**（**2026-09-09 新增**：`erl_answer_attachment` 删 `file_name` / `file_size` 两列，同样 `DROP COLUMN IF EXISTS` 幂等、同样**必须与代码同批发版**（`42703` / `23502` 两个方向对称）。脚本核验段另给一条「附件行的 `file_id` 在 `files` 里命不中」的排查查询 —— 这些行删列后名字与大小回显为 `null`，见 §5.5 的代价说明）、**`V8__erl_assessment_add_dimension_version.sql`**（**2026-09-09 新增**：`erl_assessment` 加**可空**列 `erl_question_config_dimension_version_id` + 按 `(erl_question_config_version_id, dimension_code)` **精确回填**（快照表在这两列上有唯一索引，命中至多一行，故不是 `V3` 那种近似回填，且**可重放**）。⚠️ **与 `V6` / `V7` 不同，这一份不要求与代码同批**：列可空、旧代码不认识也不写它、新代码读到 `null` 会回退复合键查询，故**建议先跑脚本再发代码**；命不中的行留 `null` 是**正确结果**（该维在那一版下确实没有快照行），脚本不报错也不猜行）、**`V9__erl_question_config_version_drop_is_latest.sql`**（**2026-09-09 新增**：删 `is_latest` 列 + 部分唯一索引 `uk_erl_question_config_version_latest`。**删列前有一道必须通过的守卫**（照 `V5` 删 `erl_assessment.is_latest` 的家法）：比对「当前 `is_latest = true` 的行」与「新判据会选出的行」是否同一行，不一致即 `RAISE EXCEPTION` 中止 —— 否则删完会**静默切换到另一版题库**（新评估绑上另一个版本 id、填报页题面直接变，而迁移正常结束、日志一行不报）；「有 `PUBLISHED` 却无任何标记」的组织只 `RAISE NOTICE`，删列反而是自愈。⚠️ **执行顺序与 `V6` / `V7` 相反：先发代码、再跑脚本** —— 该列是 `NOT NULL DEFAULT false`，新代码不写它也插得进去（只是那列永远 false、无人读），而反过来旧代码撞上不存在的列会 `42703`）、**`V10__erl_dimension_config_status_rename_values.sql`**（**2026-09-09 新增**：`status` 取值 `Activate` / `Deactivate` → `Active` / `Inactive`。**三步同一事务、顺序不可乱**：① `UPDATE` 改值 → ② `ALTER COLUMN ... SET DEFAULT 'Active'` → ③ **DROP 并按新谓词重建** `uk_erl_dimension_config_abbr`（~~`WHERE status = 'Active'`~~ → **2026-09-09 改为自适应，v4.18 订正**：先查 `information_schema.columns` 看库里有没有 `deleted` 列，**有就把谓词拼成 `status = 'Active' AND deleted = false`**、没有就只按 `status` 建（`abbr_where` 变量 + `format()`）—— 目的是让 `V10` 与 `V11` **谁先谁后都不影响终态**；无条件写死旧谓词的话，「`V11` 跑完再跑 `V10`」会把 `deleted = false` 那一半**静默抹掉**，索引名与键位一字不差、PG 一声不响，而「删掉 `OPS` 再新建一个 `OPS`」从此撞 `23505`）。⚠️ 第 ③ 步是本脚本最危险的一步：只改值不重建索引**不报任何错**，但旧谓词此后一行都命不中 ⇒ 「同组织启用维度的缩写唯一」**静默失效**。重建不会撞唯一冲突 —— 改值前后行集合完全相同，旧谓词下已唯一，新谓词下自然也唯一。三道守卫：列不存在则 `RAISE NOTICE` 跳过、两套值混用则报出行数与组织、改完仍有非法值则 `RAISE EXCEPTION` 中止（否则 Java 侧 `fromDbValue` 会在运行期抛异常、配置页 500）。**纯字面值替换、完全可逆**，与前几份删列脚本不同。⚠️ **必须与代码同批、且脚本紧跟代码之后（窗口以分钟计）**：两个方向都坏、且都**静默** —— ERL 的热读路径是**在 SQL 里按 `status` 过滤**的（`... AndStatus...(org, ACTIVE)`，绑定字面值 `'Active'`），所以**先跑脚本**旧代码按 `'Activate'` 过滤一行命不中（另有实体读到 `'Active'` 抛 `IllegalArgumentException` 的那一半），**先发代码**新代码按 `'Active'` 过滤同样一行命不中：维度列表空、卡片 / 雷达 / Score Details / 组合层 / Goldie 全空、接口 24 必报业务错误（HTTP 200 + `success:false`，~~400~~，2026-09-09 订正），而且不报错。~~原先写作「先发代码后跑脚本，读侧靠 `fromDbValue` 的临时兼容撑得住」~~ **2026-09-09 审核作废** —— 那条兼容只保住「实体读到旧值不抛异常」，**保不住按 `status` 过滤的查询**）、**`V11__erl_dimension_config_add_deleted.sql`**（**2026-09-09 新增**；**形态已于 2026-09-09 按脚本现文订正，v4.18**：~~`erl_dimension_config` 加 `deleted boolean not null default false`（`ADD COLUMN IF NOT EXISTS` 幂等）+ DROP 并按新谓词重建 `uk_erl_dimension_config_abbr`~~ —— **这正是脚本文件头点名「不能这么写」的形态**）：实际是**四步同处一个 `DO` 块**，开头另有一道「表不存在就 `RAISE NOTICE` + `RETURN`」的守卫 —— ① `ADD COLUMN IF NOT EXISTS deleted boolean`（**先建成可空**）→ ② `UPDATE ... SET deleted = false WHERE deleted IS NULL` 回填存量行（`GET DIAGNOSTICS` 报回填行数）→ ③ `ALTER COLUMN deleted SET DEFAULT false` + `SET NOT NULL` → ④ `DROP INDEX IF EXISTS` + 按 `WHERE status = 'Active' AND deleted = false` 重建 `uk_erl_dimension_config_abbr`（索引名与键位一字不变），末尾再写 `COMMENT ON COLUMN`。**为什么不能一句 `ADD COLUMN ... NOT NULL DEFAULT false`**（PG 11+ 本不重写表）：**列已存在**的库上 `IF NOT EXISTS` 会把整条跳过、**连 `DEFAULT` 与 `NOT NULL` 一起跳过**，而「列已存在但可空、由 `ddl-auto` 建出来」正是「代码先上线环境」的常态（`V4` 的 `version` 列踩过，见 README「`ddl-auto` 建列不带默认值」）；拆成三步后无论列存不存在、存量行有没有值，跑完都收敛到同一终态。⚠️ **重建索引这一步不可省**，与 `V10` 第 ③ 步同一个坑：只加列不重建**不报任何错**，但已删的行仍满足旧谓词 ⇒ 它**永久占着自己的缩写**，「删掉 `OPS` 再新建一个 `OPS`」永远撞唯一冲突，而那一行在页面两处都看不见、用户无从自救（§5.1.3 / §0.21-X2）。重建不会撞唯一冲突 —— 加列时全表 `deleted = false`，新旧谓词此刻筛出的是同一批行。⚠️ **与 `V6` / `V7` / `V9` / `V10` 不同，本份是 additive**：不改任何现有列的取值，旧代码按 `status` 过滤的热读路径一字未动，故**没有** `V10` 那种「静默空数据」的发版顺序陷阱。⚠️ **但方向不是「两边都行、可提前任意时间跑」**（**2026-09-09 订正，v4.18**）：**先发代码、脚本还没跑**时新代码每条带 `deleted = false` 的读查询报 `42703` ⇒ 取「**先跑脚本、再发代码**」；而且它**必须**落在「发版前」那一段，因为 **`ddl-auto` 在有数据的表上加不出这个 `NOT NULL` 列**（PG 拒 `23502`）、加列也不带实体侧默认值 —— `V11` 是唯一把这一列建对的地方。⚠️ **`V11` 跑完到 `V10` 跑完之间有一段无约束窗口**：索引谓词已是 `'Active'` 而数据还是 `'Activate'` ⇒ 该部分唯一索引命中零行、「同组织启用维度缩写唯一」在这段时间不受约束（`V10` 一跑完即恢复）。⚠️ **与 `V10` 的先后顺序没有要求**（`V10` 第 ③ 步已自适应，见上），`V11` **不必跑第二遍**。⚠️ 仍须排在 `V5` 之后（表名要先由 `V5` 改成 `erl_dimension_config`）。`V1__erl_init.sql` **已就地含该列与新谓词**）。⚠️ **两处回填不可解时一律 `RAISE EXCEPTION` 而不猜**：① `erl_question_config` 行的 `version_id` 为 NULL 或悬空（行上无公司、无用户，`dimension_code` 又可跨租户重复 —— 猜一个就会把 A 租户的题放进 B 租户的问卷）；② `erl_dimension_config` 行的版本头已丢（静默删掉可能抹掉某租户唯一的维度配置、静默破掉 100% 合计）。⚠ **V4 必须先于应用发版执行**：实体已标 `@Version` 而 `ddl-auto: update` 加不上 NOT NULL 列，漏跑不是启动失败而是运行期 `42703 column "version" does not exist`，`erl_assessment` / `erl_question_config_version` 的所有读写全挂。**配置页的菜单入口不在这三份脚本里**（**v4.14**）—— 原先那份菜单迁移脚本已删除，入口改由**管理后台的菜单配置界面**添加（根节点 `pid = '0'` + 授权超管角色 + 清两处缓存，前置条件见 §8.1.1）。

> **2026-09-10 补：`V13__erl_reference_score_drop_period_unique.sql`**（基准同期次允许重复录入，§5.6 / §0.27-Z1） —— `DROP INDEX IF EXISTS uk_erl_reference_score`（连改名前的旧名 `uk_erl_benchmark` 一并删）+ `CREATE INDEX IF NOT EXISTS idx_erl_reference_score_company_period ON erl_reference_score (company_id, period)`，另改写 `COMMENT ON TABLE`（原文写着 `ONE ROW PER (company, period)`）。幂等，可随 README 的 `--single-transaction` 整份执行（**无 `CONCURRENTLY`**，与 `V12` 不同）。⚠️ **不进上面三类环境的分流**：**存量环境**（库里真有那条唯一索引）必须跑；**全新环境** `V1` 已就地改为直接建普通索引 ⇒ 跑它是 no-op；⚠️ **`V5` 未改**（它仍会建出唯一索引），同批执行时**排在 `V5` 之后**。⚠️ **执行时机：先跑脚本、再发代码**（或同批）—— 反方向 = 新代码已不拦重复而唯一索引还在，重复添加直接 500；先跑脚本这个方向**不炸**（旧代码仍在服务端拦重复，只是少了数据库兜底，窗口以分钟计），不阻塞读写。✅ 可逆，但**回滚前必须先人工去重**（库里已有重复期次时重建唯一索引会失败），回滚段已写明。

> **2026-09-15 补：`V15__erl_dimension_config_drop_abbr_unique.sql`**（维度缩写不再唯一，§5.1.3 / v4.31） —— `DROP INDEX IF EXISTS uk_erl_dimension_config_abbr`，**只删索引，不动任何数据与列**。幂等，可随 README 的 `--single-transaction` 整份执行（**无 `CONCURRENTLY`**）。⚠️ **必须排在 `V11` 之后** —— `V11` 第 ④ 步会按新谓词把这个索引**重建**出来，先跑 `V15` 等于白删。⚠️ **不进 `V10` / `V11` 那三类环境的分流**：**存量环境**（`V11` 已跑过、索引真在）必须跑；**全新环境** `V1` 已就地不再建它 ⇒ 跑它是 no-op。**发版方向无硬约束**（删约束是纯放宽，两个方向都不会静默出错），但**先发代码**会让窗口内的用户撞上一个已被取消的拦截（新代码不再校验、库里索引还在 ⇒ 建重名维度报唯一冲突），故仍按「**脚本先跑、代码紧跟**」执行。✅ 可逆，但**回滚前必须先人工去重**（缩写唯一取消后库里很可能已有重复缩写，重建唯一索引会失败）。

> **2026-09-16 补：`V16__erl_assessment_add_unanswered_count.sql` 与 `V17__erl_assessment_drop_unanswered_count.sql`**（一加一删，§5.2 / v4.41） —— `V16`（2026-09-15）为「允许未答完提交」加了可空列 `unanswered_count`；`V17`（2026-09-16）在需求方把那条路径改成「自动补第一道 No 后照常提交」之后把它删掉（`ALTER TABLE IF EXISTS … DROP COLUMN IF EXISTS` + 两条 `COMMENT ON` 套 `DO` 守卫，幂等）。`V1` 已**就地改为不建这一列**。<br>⚠️ **判据是「库里有没有这一列」，不是环境类别**（同 `V13`）：`information_schema.columns` 里见到 `erl_assessment.unanswered_count` 就必须跑 `V17`；没见到则两份都不用跑。⚠️ **`V16` 在改版后的 `V1` 上已不再是 no-op** —— 若出于按序重放跑了它，**必须紧跟 `V17`**，否则留下一列永远为 NULL、无人读写的死列。<br>⚠️ **执行时机：`V17` 必须先发代码、再跑脚本**（同 `V6` / `V7` / `V9`，**与 `V16` 相反**：`V16` 加的是可空列、两个方向都不炸）。反方向 = 旧实体上 `unansweredCount` 仍是映射字段，Hibernate 的每条 SELECT / INSERT / UPDATE 都会列出它 ⇒ **整个 ERL 模块 42703**（打开问卷、存草稿、提交、ERL Card、B3 历史、组合层、Share 门槛全线 500），且 `ddl-auto: update` 兜不住（只加列、不删列）。<br>⚠️ **删列前先决定存量「部分提交」行怎么办**：2026-09-15~16 之间落的那些行（`coalesce(unanswered_count, 0) > 0`）删列后会一律被读成完整提交、重新解锁 Share 与 Goldie，且判别信息**无法重建**（答案行事后可被新草稿覆盖）。⚠️ 它们的 `terminated_level` **不一定是 NULL** —— 跳着答（同级先漏答、后对更靠后的题答 No）当年就会同时落下正的漏答数与非空止步级，拿 `terminated_level IS NULL` 当判据一筛就漏。✅ 可逆：**重跑 `V16` 整份**（它自带 `ADD COLUMN IF NOT EXISTS` + 注释守卫），但回滚不会把信息找回来。

**v4.0 从建库脚本中删除**：
- ❌ 系统配置项 `erl.enabled` 初始值 —— PRD 已不要求隐藏 DI（§8.6）。
- ❌ `erl_assessment_answer` 的 CHECK 约束 `(score IS NULL) <> (yes_no IS NULL)` —— `score` 列已删（§5.4）。

> **v4.4 新增跨域依赖（R3）**：展示期次缺省值＝**该公司 closed month 所在季度**，closed month 由 **`fi/`（Financial Intelligence）域既有服务**给出（按公司 Manual / Automatic 两种推导，源自 Financial Entry actuals）。`erl/` 域**只调不算**，唯一落点是 `ErlPeriodService` —— 其余 service 一律经它取缺省期次，禁止各自去查 FI 表。这是原设计「ERL 对 FI 零依赖」的**唯一破例**，架构影响见 §3。

> **题库查询的统一入口（v3.3 改，v4.0 加组织维度；**2026-09-08 键位改为二元组**）**：`ErlQuestionConfigRepository` 的**每个查询方法都必须带 `(dimensionCode, versionNo)` 两个入参**（原先是单一的 `versionId`），禁止「查全部题」的无版本方法。⚠️ **跨维度的整版本查询（如原 `countByVersionId` / `findByVersionIdOrderBy...`）在新模型下不成立** —— 一个 `version_no` 只属于一条维度线，取「一个发布版本的全部题」必须先过 `erl_question_config_dimension_version` 拿到逐维的 `question_version_no`，再逐维查。上层只有两个取版本的入口 —— `ErlQuestionConfigVersionService.currentPublished(organizationId)`（填报 / 展示 / 计分 / 组合层 / Goldie）与 `ensureDraftVersion(organizationId)`（仅 C 模块写接口）、`currentDraftOrPublished(organizationId)`（仅 C 模块读接口）。**漏带版本 = 草稿题泄进问卷；漏带组织 = 跨租户串题**，是本模块最容易出的两个错，代码审查须专项检查。

> 分数聚合、附件编排、洞察合成属跨表编排，写在 `application/service`；`domain/repository` 只做单表访问（`standards/architecture.md` §1.2 / §1.3）。**level 计分与加权综合分一律经 `application/scoring/ErlLevelScorer`，不在 service 内联**（§7.2-②）。

### 10.2 CIOaas-python（生成 + **落产物** + 附件编排）

```
新增  source/erl/interfaces/routes.py                     POST /api/ai/erl/gap-analysis/refresh
                                                         GET  /api/ai/erl/gap-analysis
                                                         POST /api/ai/erl/gap-analysis/share
      source/erl/domain/{models,repository}/              两个 ORM + 一表一仓储（2026-09-19 新增）
      source/erl/infrastructure/gap_analysis_lock.py      Redis 锁（2026-09-19 新增）
      sql/migrations/business/V024__erl_gap_analysis.sql  建两张 ai_erl_* 表 + 存量迁数据
                                                          POST /api/ai/erl/attachments/summarize
                                                          （2026-09-18 由 /attachments/ingest 改名，§6.7）
新增  source/erl/interfaces/vo/{request,response}.py
新增  source/erl/application/service/erl_gap_analysis_service.py
新增  source/erl/application/service/erl_attachment_service.py   ← 复用 rag ingest_service 与 file_registry
❌ v4.4 删除  source/ai/prompts/erl_gap_analysis_founder.md   ┐ 双 audience 方案取消（§0.10-D3），
❌ v4.4 删除  source/ai/prompts/erl_gap_analysis_gsv.md       ┘ 两份合并
新增  source/ai/prompts/erl_gap_analysis.md              **v4.4**：单份 prompt（原带 # version: 1.0）
                                                          —— 只产出一套措辞；已删「双方分数均高时
                                                          承认为优势」一段（§0.10-D4：STRENGTH 取消）。
                                                          **v4.9：`criteria` 字段整体移除
                                                          （prompt v1.1）** —— 正文不再有该输入，
                                                          判断依据收敛为「题干 + 逐题 Yes/No +
                                                          双端备注 + level 口径」，并新增反向约束
                                                          「输入里没有判定标准字段、不得编造标准
                                                          原文」（§0.15-S3）
修改  source/main.py                                     注册 router
新增  tests/erl/test_erl_gap_analysis_service.py         prompt 回归测试（固定输入 → 验证输出结构 /
                                                          severity 值域；**v4.4**：~~双 audience~~ 断言删除，
                                                          改为断言输出**不含** `strengths[]`、
                                                          `item_type` 仅 `GAP` / `ACTION`；
                                                          **v4.9**：补防回归断言 —— 请求 VO 与
                                                          prompt 渲染结果均**不含** `criteria`）
新增  tests/erl/test_erl_attachment_service.py           入库链路顺序（ingest → register → vectorize）
```

~~Python 侧**无 domain 层、无 ERL repository** —— 不落 ERL 业务表~~ → **2026-09-19 反转**（v4.59 / §0.33-X1）：`source/erl/` **有了 domain 层** —— `domain/models/` 两个 ORM（`ai_erl_gap_analysis` / `ai_erl_gap_analysis_item`）+ `domain/repository/` 一表一仓储，外加 `infrastructure/gap_analysis_lock.py`（Redis 锁）；DDL 走 `sql/migrations/business/V024__erl_gap_analysis.sql`。**其余 ERL 业务表仍属 Java、Python 不查**；附件编排照旧复用 rag / file_registry 的既有服务。

### 10.3 CIOaas-web

```
新增  src/pages/exitReadiness/**                      （§8.2 全部）
                                                       v4.4：configuration 页第二个 Tab 由
                                                       ~~`Dimension Weights`~~ 改为
                                                       **`Dimension Configuration`**（新增 / 删除 /
                                                       排序 / 权重，Save 双条件，§0.10-D13）；
                                                       A4 每张维度卡卡头加 `Add New` / `View History`，
                                                       原页级 `+ New` / `View history` 取消（§0.10-D5）；
                                                       A3 顶部按钮组 `Save as draft` / `Cancel` /
                                                       `Reset` / `Submit`（§0.10-D8）+ 题库更新弹窗
                                                       （§0.10-D10）+ 重复提交确认文案分支（§0.10-D11）
修改  src/pages/exitReadiness/constants.ts            **v4.4**（D1）：❌ 删除静态 `DIMENSIONS` 映射
                                                       （维度码 / 全称 / 缩写 / 顺序）——
                                                       改为**接口驱动**（接口 23 / 各页出参的
                                                       `dimensions[]`），全站不得再有维度硬编码；
                                                       雷达图顶点、A3 维度 chip、A4 维度卡、
                                                       C7 版本快照卡、Gap 状态点数量一律动态渲染
修改  src/pages/exitReadiness/configuration/**（C6 维度配置 Tab）
                                                       **2026-09-09**（§0.21 / §8.4-C6）—— 本轮改动量最大的一块，
                                                       此前本节只列了 C7、漏了 C6（**v4.18 补**）：
                                                       · `components/DimensionConfigForm.tsx`
                                                         ① 行尾销毁按钮改**三态**
                                                            `row.canDelete && !row.isRestored ? 垃圾桶 : 电源按钮`
                                                            —— 刚从停用区恢复回来的行即便 `deletable = true`
                                                            也只给电源按钮（语义 = **撤销恢复**，独立 tooltip /
                                                            确认文案 / aria-label `Undo restore`，§0.21-X14）；
                                                            Tooltip 必须套在 Popconfirm **外层**（反过来套
                                                            确认框弹不出来）；
                                                         ② ❌ 删 `Show deactivated` 开关，改为**面板底部常驻**的
                                                            `Deactivated Dimensions` 区（标题 + 空态 + 停用行 + 脚注）；
                                                            停用行按 mockup 只放三样：灰化 `Name (ABBR)` +
                                                            `INACTIVE` 标 + 行尾 `Activate`
                                                            （⚠️ **与 §8.4-C6-⑤ / §11-86-③ 要求的
                                                            「只读可复制 code + 权重」不一致，以 mockup 为准，
                                                            该条待需求方裁决，本轮不处理**）；
                                                         ③ 列表下方新增规则提示段 `dimensionConfigDeleteHint`（**2026-09-14 起仅在有启用维度时显示**）；
                                                         ④ 拖拽下标一律用**行在 `rows` 里的原下标**（停用 / 已删行
                                                            不在主列表时渲染下标会插错位）
                                                       · `hooks/useDimensionConfigForm.ts`
                                                         行模型由四类增至五类，新增 `isDeleted`（真删本地标志，
                                                         与 `isDeactivated` **并列不复用**）、`canDelete`
                                                         （← 接口 23 的 `deletable`）、`isRestored`（本次会话
                                                         从停用区翻回来的行，出口给的是**带该标志的视图行**）；
                                                         `bucketOf` 把每行**只归一个桶** `A/D/X` →
                                                         `dimensions[]` / `deactivatedCodes[]` / `deletedCodes[]`
                                                         （置 `isDeleted` 时同时清 `isDeactivated`，否则同一 code
                                                         进两个桶 ⇒ 服务端 ⑩ 号校验业务错误）；`deletedCodes`
                                                         **恒发**（无删即空数组）；`rowsIssue`（`DimensionRowsIssue`）
                                                         取代原来的布尔 `rowsValid`，渲染在 `Total` 左侧
                                                         （**2026-09-15**：其中 `DUPLICATE_ABBR` 一档**删除**，
                                                         缩写唯一整条取消；`rowsIssue` 本身保留，仍承载
                                                         name/abbr 为空、abbr 超长、无启用维度三档，v4.31）；
                                                         **2026-09-15 另删 `+ Add` 栏的 abbr 查重** ——
                                                         `addRow` 原先查重不通过就**静默不加**、屏上不给
                                                         任何提示，这正是本次需求的触发点；
                                                         `Total` 与「至少一个启用维度」把**已删行也排除**
                                                       · `components/constants.ts`（域级）新增约 14 条 C6 文案：
                                                         `activate` / `inactive` / `deactivateDimensionConfirm` /
                                                         `deactivateDimensionOk` / `deleteDimensionConfirm` /
                                                         `deleteDimensionOk` / `dimensionPublishedTooltip` /
                                                         `dimensionRestoredTooltip` / `undoRestoreConfirm` /
                                                         `undoRestoreOk` / `dimensionConfigDeleteHint` /
                                                         `deactivatedSectionTitle` / `deactivatedSectionEmpty` /
                                                         `deactivatedSectionNote` / `dimensionConfigAllDeactivated`；
                                                         ❌ 删 `removeDimensionConfirm`（单一销毁动作时代的文案）。
                                                         ❌ **2026-09-15 再删三条**：同名软拦截那个
                                                         `Create anyway` 弹窗的标题 / 正文 / OK 文案
                                                         （软拦截整条取消，v4.31 / §6.4-2-⑦）。
                                                         ⚠️ **恢复按钮的标签是 `Activate` 而不是 `Restore`**
                                                         （2026-09-09 mockup 定档，§0.21-X14）—— 仓库里没有任何
                                                         `Restore` 文案常量，只有 handler 名 `onRestore` /
                                                         标志位 `isRestored` 沿用旧词
                                                       · `ConfigurationPage.tsx`：取数**恒带** `includeDeactivated=true`
                                                         （`useDimensionConfig(true, organizationId, true)`），
                                                         开关撤下后停用行由常驻区块承载；`Question Library` Tab
                                                         另按 `status !== 'RETIRED'` 过滤，**不让停用维度冒到题库 Tab**；
                                                         保存出参分支 `CONFLICT`（乐观锁）弹一个 `Modal.confirm`
                                                         （~~/ `DUPLICATE_NAME`（同名已停用维度 →
                                                         `Create anyway`）~~ —— **2026-09-15 整条删除**：
                                                         同名软拦截取消，该分支与它的 `Modal.confirm`、
                                                         三条文案一并撤下，v4.31 / §6.4-2-⑦）
                                                       · `ConfigurationPage.less`：新增停用区 / 三态按钮 / 提示段样式
                                                       · 测试 `src/pages/exitReadiness/configuration/__tests__/`：
                                                         **新增** `DimensionConfigForm.test.tsx`（三态图标与文案）；
                                                         **大幅扩写** `useDimensionConfigForm.test.tsx`（归桶 / 三桶互斥 /
                                                         `Total` 排除已删行 / `rowsIssue`）—— ⚠️ 后者是**既有文件**，
                                                         不是新增
修改  src/pages/exitReadiness/configuration/history/**        （C7 版本快照页）
                                                       **2026-09-09**（§0.22）：① 取数 hook `useQuestionVersions`
                                                       内按 `status === 'PUBLISHED'` 过滤后才进下拉与默认选中
                                                       （**接口 25 契约不动**，过滤只在页面侧）；下拉标签的
                                                       ❌ `Draft` 那一支删除；② ❌ 删接口 23 的取数、
                                                       `QuestionVersionSection.retired` 字段、兜底卡的
                                                       `retired: true`、`QuestionVersionHistoryPage.less`
                                                       的 `.retiredTag` —— 卡头不再有 `Retired` 灰标，
                                                       本页只读接口 25 / 26（**`TEXT.retired` 常量保留**，
                                                       ErlCard 维度行与 A4 仍在用）
修改  src/pages/companyOverview/home/CompanyOverviewPage.tsx
                                                       v4.0：DI 区块 JSX 整块下移到 FI 之后（渲染条件
                                                       DiStatus 原样不动）；原 DI 位置渲染 ErlCard（§8.6）
                                                       v4.3：订正为两列 —— bottomHtml 内加 .btmLeft
                                                       （FI + DI）与 .btmRight（ErlCard）两个列容器
新增  src/pages/companyOverview/home/components/ErlCard/**
                                                       v4.4：Gap 区块按原型定档（§0.10-D4）——
                                                       `AI GENERATED` 标签、`View details` 弹框、
                                                       `Share to founder` 按钮（门槛未达成置灰）、
                                                       期次 chip、每维三态小卡与计数文案；
                                                       雷达图正下方加 `Benchmarkit & Top GSV Quartile ›`
                                                       链接（仅管理端，§0.10-D7）；
                                                       右上角 `Full View ›` → A4（**两端都有**，§0.10-D5）
新增  src/pages/exitReadiness/components/GapDetailsModal/**
                                                       **v4.4 新增**（D4）：建议详情弹框，按维度分区
删除  src/pages/exitReadiness/components/ResetDraftConfirm/**
                                                       **v4.29 删除**：Reset 二次确认框撤下（v4.4 由 D8 新增），
                                                       `Reset` 直接调接口 28
修改  src/pages/exitReadiness/scoreDetails/**        （A4 全维 Score Details）
                                                       **2026-09-09**（§0.24）—— 照原型 `/readiness/overall` 整页重排版：
                                                       · `ScoreDetailsPage.tsx`：面包屑 `parentDir` 由公司名改为
                                                         `Portfolio Companies`（两级）；❌ 删页头综合分与 Era 徽章；
                                                         维度折叠卡改 `Tabs`（标签 `abbr`）+ 末位基准 Tab；
                                                         新增 `GSV` / `Founder` 药丸（`GSV` 默认，本地切 `portals` 切片，
                                                         **不重发接口 22**）
                                                       · `DimensionQuestionsCard.tsx`：卡头计数改 `{n} questions`；
                                                         `+ Add New` 仅 GSV 侧；`View History` → `View history`；
                                                         卡内四格元数据栏 `PERIOD / SUBMITTED BY / ROLE / SUBMITTED AT`；
                                                         ❌ 删按 level 分组的组头；`Retired` 灰标保留
                                                       · ❌ 删 `components/DualQuestionRow.{tsx,less}`（同屏并列已撤）
                                                       · 新增 `components/ScoreQuestionRow.{tsx,less}`：三态徽章、
                                                         `NOTES` / `ATTACHMENTS` 块、附件体积 + 下载
                                                         （复用 `storageService.getFileLink`，无新接口）
                                                       · 新增 `components/BenchmarkPanel.{tsx,less}`：末位基准 Tab 的内容
                                                         （卡头 `BQ` 徽章 + `+ Add New` / `View history` → D2 / D1，
                                                          **v4.25**：新增 `period` prop，两条 URL 带 `&period=`
                                                          本页 `shownPeriod`（§0.29-Z1）；
                                                          Founder 药丸下只出一句 `benchmarkGsvOnly`）
                                                       · 新增 `ScoreDetailsPage.test.tsx`：药丸切换不重发接口 22、
                                                         基准 Tab 按端类型显隐、按端空态文案三条
修改  src/pages/exitReadiness/components/BenchmarkDimensionTable.tsx
                                                       **2026-09-09**（§0.24-Z4）—— ⚠️ **本批次唯一波及 D1 的改动**
                                                       （A4 末位基准 Tab 与 D1 两张卡共用该组件）：
                                                       · 列头改原型原文 `EXTERNAL BENCHMARKS` /
                                                         `TOP GSV QUARTILE`（D1 两处一起改名；2026-09-10 去 `(1-9)`，§0.26-Z2）
                                                       · ~~新增**可选** `weights` 入参 → 表尾加权 `Average` 行~~
                                                         → **2026-09-10 撤下**（§0.26-Z1）：表尾整行删除，
                                                         `weights` 入参与 `summary` 一并删除（A4 是唯一调用方），
                                                         D1 / 基准记录详情页 始终只有明细行、不受影响
修改  src/pages/exitReadiness/components/constants.ts
                                                       **2026-09-09**（§0.24）：**新增** `benchmarkTitle`
                                                       = `External Benchmarks & Top GSV Quartile`（⚠️ 是**新增**不是改名 ——
                                                       旧串 `benchmarkEntry: 'Benchmarkit & Top GSV Quartile'`
                                                       **原样保留**给 A1 雷达图下方那个入口，两者不是一回事）；
                                                       另新增 ~~`benchmarkCaption`~~（**2026-09-20 删除**）/ `benchmarkGsvOnly` / `notAnswered`
                                                       / `noBenchmarkRecords` 等文案，以及
                                                       `SUBMISSION_META_LABELS`（四格元数据栏标签）、
                                                       `questionCountText`（单复数：`1 question` / `31 questions`）、
                                                       `formatFileSize`、`noPortalSubmissionText`（按端空态）
修改  src/pages/exitReadiness/components/SubmissionMetaBar.tsx
                                                       改用 `SUBMISSION_META_LABELS`（与 A4 卡内四格共用同一份标签）
修改  src/pages/exitReadiness/components/AttachedFilesCard.tsx
                                                       `formatSize` 提到 `constants.formatFileSize`（与 A4 逐题行共用）
修改  src/pages/exitReadiness/components/QuestionRow.tsx
                                                       改用 `TEXT.memoryIngestFailed` 等共用文案常量
新增  src/pages/portfolioCompanies/erl/**             F2 Tab 内容组件 + 取数 hook
      └ hooks/useErlPortfolio.ts                    v4.19：`currentQuarterPeriod()` 在此，挂载时算一次并固定作为 `period` 发出（§0.23-P1）；无 query 状态、不发排序筛选入参（§0.23-P2）
                                                       v4.4：表格列与 `sortBy` 白名单由静态五列
                                                       改为按 `dimensionScores[]` **动态生成**（D1）
修改  src/pages/portfolioCompanies/home/PortfolioCompaniesPage.tsx
                                                       新增 TabPane key='6'；trackPortfolioButtonClick 补 'ERL' 分支
新增  src/services/api/exitReadiness/**
新增  src/services/service/exitReadiness/erlService.ts
修改  config/routes.ts                                 （§8.1 十一条路由 —— v3.5 增 scoreDetails、v4.1 增 configuration/history + Configuration 顶部下拉入口）
修改  src/locales/en-US/**                             （ERL 文案）
修改  CIOaas-web/standards/architecture.md §2          （登记新 API 域 exitReadiness/，见 §13-Q7）

v4.0 从清单中删除：
❌ 修改 src/pages/companySettings/components/modules/ModulesTab.tsx
        —— 原为「DI 开关旁加『ERL 已接管展示』说明」；DI 不再被接管，无需说明（§8.6-4）
```

### 10.4 台账

- `CIOaas-api/docs/待优化项.md` 已于 2026-08-26 记入 `fi/` 分层与 `QuickbooksController` 存量违规一条。
- 本次新增待优化项（实现阶段登记）：
  - ~~Company Overview 的 DI 开关语义与 ERL 接管后的冲突~~ → **v4.0 删除该条**：DI 不再被 ERL 接管，开关语义无变化（§8.6）。
  - `CompanyOverviewPage.tsx` 已超 1600 行且 DI/FI 分支混杂，**本次还要整块挪动 DI 区块**（§8.6-1），拆分优先级上调。

> **v4.4 写法确认（无实质变化）**：台账条目一律按根 `CLAUDE.md` 的格式写 —— 待优化项 `- **标题**（识别日期）：一两句问题与建议方案（来源）`，完成后从 `docs/待优化项.md` **删除该条**并在 `docs/已完成优化.md` 追加 `- **标题**（完成日期）：改动摘要（涉及文件/提交）`。写入前先查重，同一事项**更新原条目**而不是新增。三个主工程各自维护自己 `docs/` 下的两份台账（`CIOaas-api/docs/`、`CIOaas-web/docs/`、`CIOaas-python/docs/`），不合并到根目录。

---

## 11. 验证清单（实现后逐项过）

> ⚠️ **本节「返回 400」已一律订正为「返回业务错误」**（2026-09-09，v4.18）：ERL 服务层的业务校验失败一律 `BadRequestException` ⇒ 线上形态是 **HTTP 200 + `success: false` + 提示语**，不是 HTTP 400（判据与例外见 §4.3 开头的订正说明）。**写断言时看 `success` 与 `msg`，不要看状态码。**

**入口与卡片（PRD §3.1）**
1. **（v4.0 改，v4.3 订正）** Company Overview 页三张卡为**两列**：左列 `FI → DI`、右列 `ERL`（两列等宽、顶部对齐，窄屏回落单列）；DI 卡片**仍然显示**（不是消失），其概览数据与下钻入口可正常使用；关闭公司的 `diStatus` 后 DI 卡隐藏、ERL 与 FI 不受影响（开关语义未变，§8.6）。
2. **（v4.0 改，v4.4 再改）** ERL Card 完整包含：**加权** `Overall Score` `X/9`（tooltip 列出所用权重）、当前 Stage、**`Gap Analysis & Suggested Actions` 区块**（~~E 待定期间隐藏~~ → **v4.4 作废**：Goldie 已回归 V1，恒渲染，§0.10-D2）、**维度列表**（~~5 维~~ → **v4.4 参数化**：按当前 `status = 'Active'` 的维度集合渲染，§0.10-D1；**level 整数分** + `Level n`）、BPMM 参考数字、右上角 **`Full View ›`**（→ A4，**两端都有**，§0.10-D5）；**管理端**另有 GSV 分、Perception Gap、雷达图，以及雷达图**正下方**的 `Benchmarkit & Top GSV Quartile ›` 链接（§0.10-D7）。❌ 不含状态徽章、不含 Data Sources。
3. **全站不存在独立的 Exit Readiness 落地页路由**；`/exitReadiness` 直接访问返回 404 或重定向到 Company Overview。
4. 卡片上每个维度的 `View Details` 正确跳到对应维度页；维度页面包屑为 `Exit Readiness ›〔Dimension Name〕`，返回落回 Company Overview。

**维度页与模板（PRD §3.2）**
5. **（v4.4 参数化，D1）** ~~五个~~ **配置版本中每一个维度**的维度页 `/exitReadiness/dimension/{code}`（**2026-09-17**：新库无任何预置维度，`code` 一律是配置页生成的 7 位码；举例写作 `FRL` 只是叙述，**不得硬编码**）均由**同一组件**渲染，文案随参数变化，无硬编码分支；`code` 不在当前 `status = 'Active'` 的维度集合中 → 404，不崩溃。
6. **公司端进入维度页看不到 GSV Tab**；直接构造 `?portal=gsv` 请求后端返回业务错误。
7. **（v4.0 扩）公司端看不到 GSV 分 / Perception Gap / 雷达图 / Benchmarkit / Top GSV Quartile**；抓包确认服务端**未下发**这些字段（`gsvScore` / `perceptionGap` / 整个 `radar` / `benchmarkPosition` 在响应体中不存在，非前端隐藏）。
8. **（v4.4 重写：R1 + D5 + D12；v4.21 补期次）** 维度页 `View history` → `/exitReadiness/history?companyId={id}&period={period}&dimension={code}`（~~`?dimension={code}`~~），列表**只列该维度的提交**（~~记录条数与不带 `dimension` 时一致，评估整卷提交不该被过滤掉~~ → **v4.4 作废**：维度级提交后每条记录本就归属某一个维度，`dimension` 是真过滤而非视图切换，§0.10-R1）；~~`Completion` 显示该维口径（如 `7/9`）~~ → **v4.4 作废**：`Completion` 列已删（§0.10-D12），分数列改为显示**该维 Overall Score**（`{level}/9` + Era 徽章），其下次级文字为 `v{n}` 与 `stopped at L{t}`；页头标出当前维度并提供清除入口；`Add New` 进入对应端问卷**且只填该维度**（`?dimension={code}`，§0.10-D5）。**v4.21 另验**：从本页当前期次点进 B3 后，B3 面包屑「Score Details」那一级点回来落到的是**同一期次**的 A4，**不是**服务端缺省期次（closed month 所在季度）；再从 B3 点进某条详情、由详情页面包屑退回 B3，期次**仍在**（⚠️ 但 `?dimension=` 过滤态**不保留**，退回的是全维混排列表，属已知口径、不算 bug，§0.25-Z2）。
9. **（v4.0 改）** 维度页**不存在** Data Sources & Cadence 卡（PRD 已删该展示项）；逐题行仍显示 `Source: {来源}`。

**计分（PRD §3.1 / §3.3 / §3.5 —— v4.0 全组重写；编号保持 10 ~ 16 以免打断全文对 §11-n 的交叉引用）**
10. **level 计分基本例**：某维 level 1（3 题）全 Yes、level 2（4 题）全 Yes、level 3（2 题）答 Yes + No → **维度分 `2`**，`terminatedLevel = 3`，已答 `9` 题，**level 4 及以后的题不下发**（抓包确认 `questions` 为空、`state = LOCKED`）。⚠️ **v4.37**：本例 level **连续**，新旧口径同值；**稀疏题库须另测** —— 某维只配 level 1/2/7/9、在 L7 踩 No ⇒ 维度分 **`2`**（不是 6），在 L9 踩 No ⇒ **`7`**（不是 8）。
    - **10a**：level 1 内出现 No → 维度分 **`0`**（不是 `null`、不显示 `—`），Stage `0`、Era 徽章 `Not yet Stage 1`，且**照常计入加权综合分**。
    - **10b**：某维九个 level 全 Yes → 维度分 **`9`**，`terminatedLevel = null`，页头显示 `All levels cleared`（PRD `a6b0906`）。
    - **10c**：某 level 内混有 Yes 与 No → 该组逐题各显示自己的徽章，**不整组显示为 No**；这些 Yes 答案照常传给 Goldie（§6.6）。
11. **加权 `Overall Score`**（**2026-09-16 恢复**：2026-09-15 曾短暂改等权，次日改回加权，§7.1）：权重 **50/20/10/10/10**、维度分 2/5/7/4/1 → 综合分 **`3.2`**（= 1.0+1.0+0.7+0.4+0.1；~~`3.5`~~ 是原文的加总笔误，2026-09-16 订正）**2026-09-08 换算例**：原用的 30/20/20/15/15 + 2/5/7/4/1 恰好算出 3.75→3.8，与改成各 20% 后的 3.8 **完全相同**，是个退化例、观测不到变化，tooltip 列出所用权重（权重条数随当前 `Active` 维度数，不固定五条）。~~v4.4：改权重生成新配置版本，已绑定旧版本的期次综合分必须一字不变~~ → **2026-09-08 整条反转（回到 v4.0 口径）**：改权重为各 20% 后点 Save → **同一份历史数据的综合分从 `3.5` 变为 `3.8`**（(2+5+7+4+1)/5 = 3.8），且 **A1 卡片 / A2 雷达图 / F2 总表三处同步变化、值完全一致**；Stage 如跨档也跟着变。这是**已接受的漂移**（权重不做快照，§7.11 / §13-Q21），**不是 bug**；同时需确认综合分**不是被硬编码成平均值**（改成非均等权重时结果跟着变）。
    - **11a 配置校验（v4.4 改，D13）**：配置页 ~~`Dimension Weights`~~ → **`Dimension Configuration`** Tab 输入合计 99% 或 101% → **Save 按钮禁用**、总计红字并提示 `Exceeds 100% by {n}%` / `Needs {n}% more`；直接调 ~~`PUT /erl/weight`~~ → **`PUT /erl/dimension/config`** 传合计 ≠ 100 → 业务错误且提示 `Dimension weights must add up to 100%.`
    - **11b 某维 0 题**：该维 `levelScore = null`、显示 `—`、**不进综合分**，~~其余四维~~ → **v4.4：其余维度**权重归一化后算综合分并有 tooltip 说明；该维~~不拦提交~~ → **2026-09-07 订正：不可提交**（§6.3 校验 3）。
12. **Era 边界（综合分）**：3.9 → `Founder Era`、4.0 → `Harvest & Growth`、6.9 → `Harvest & Growth`、7.0 → `Exit Era`；**6.4 必须显示 `Harvest & Growth`**（原型的 Exit Era 是 bug，不得复现）；**`0.0` 必须显示 `—` / `Not yet Stage 1`，不得落进 Founder Era**（§7.3）。
13. **`0` 与 `null` 不混淆**（v4.0 换底后最易踩的坑）：全仓检索确认分数判空一律显式判 `null`，**不存在 `!score` / `score ? A : B` 这类真值判断**；页面上 `0/9`（分低）与 `—`（无数据）视觉可区分（§7.1 末段）。
14. **已解锁范围 ≠ 全部题**：上例中页头显示 `17 questions · 9 answered`（不是 `9/9`，也不是 `17/17`）；~~历史列表 `Completion` 显示 `9/17` + 次级文字 `stopped at Level 3`~~ → **v4.4 作废**（§0.10-D12 / D16）：`Completion` **列已删**，`answeredCount` / `totalCount` 降为**页头**用途；`stopped at L3` 与 `v{n}` 两个次级标注挪到历史列表**分数列下方**。§7.1.1 的分母口径论证**保留**为实现说明（页头仍必须是 `9/17` 口径，不是 `9/9` 或 `17/17`）。
15. **Yes/No 是唯一题型**：全仓检索确认**不存在** `answer_type` / `ErlAnswerTypeEnum` / `score` 列 / 1–9 打分控件 / `Not scored` 标注的任何残留（§0.9-1）。
16. **计分逻辑隔离**：level 判定与加权综合分只出现在 `application/scoring/ErlLevelScorer`，各 service 无内联；**且已无 `ErlScoringStrategy` / `Score1To9Strategy` / `ErlScoringStrategyFactory` / `ErlScoringModeEnum` / `scoring_mode` 列**（§7.2-②）。

**填报（PRD §3.3 / §3.4 —— v4.0 大改；编号保持 17 ~ 22）**
17. 自评页答 3 题（含 1 条备注 + 1 个附件）后关闭浏览器，重进同期次同端，答案、备注、附件**与解锁进度**完整回填（`unlocked_level` 已持久化，§5.3）。
18. ~~附件上传后可在**公司 Knowledge Base / Memory File 面板中检索到**（验证走的是 ingest + 向量化链路，而非只登记）。~~ → **2026-09-18 整条反转**（v4.57，§0.31-Z1 ~ Z3）：新上传的 ERL 附件 `ai_rag_entry.content_text` 与 `.summary` **均非空**、`chunk_count = 0`、`ai_rag_ent_kb_chunk` **零行**；且该文件**不出现在** chatbot `search_knowledge_base` 的召回结果、Memory 面板与知识库面板里（**「检索得到」由验收项变成了缺陷**）。另需回归：chatbot 自己的附件行为完全不变；扫描件 PDF / 图片走 OCR 后仍能出摘要；抽不出内容的文件判 `FAILED` 而非静默成功。
    - **18a（v4.0）10MB 上限**：选 11MB 文件 → 前端直接拦下、提示 `File exceeds the 10 MB limit.`、**不发起上传**；绕过前端**直传一个 11MB 文件拿到 `fileId`**、再调 draft 接口挂上去 → 后端按 `files.length` 复核 **业务错误**（**2026-09-09**：入参已无 `fileSize` 可篡改，篡改也不再被采信）；`fileId` 在 `files` 里不存在同样报业务错误。
    - ~~**18b（v4.0）GSV 维度级附件**~~ → ❌ **v4.6 作废**（§0.12）：维度级附件取消，改由**第 89 项**验证「双端逐题附件」。
19. **提交后只读**：已提交记录的问卷页无输入控件；直接调 draft/submit 接口返回业务错误。
20. **同季多次提交**：同一 `period` + 同一端 + **同一 `dimension`**（**v4.4** 补维度键位，R1）连续提交两次 → B3 出现**两条独立记录**，第二条带 `Current` 徽章，第一条不带；展示页与 F2 取第二条。**另验**：同一 `period` 同一端的**不同维度**各提交一次 → 是两条互不影响的记录，不会互相顶掉。**2026-09-08 改判定**：`Current` 徽章不再靠 `is_latest` 列（已删），而是 `records[]` 按 `submitted_at DESC, id DESC` 排序后的**首条**；另验：同一秒内连续两次提交时两条都合法存在（**无唯一索引兜底**），但所有页面选出的那一条必须**完全一致**（读侧走同一个 Repository 方法）。
21. **（v4.0 整条替换 v3.6 的手动分校验）逐级解锁交互**：level 1 全部答 Yes → 该组**折叠并显示 ✓**、level 2 自动展开并滚入视口；level 2 中答一个 No 并答完该组 → 该组标 `Stopped here`、**level 3 不出现**、提示维度分 `1/9`；抓包确认 level 3+ 的题面**从未下发**。
    - **21a 改答回收**：承上，把那个 No 改回 Yes → level 3 解锁；再把 level 1 的某题改成 No → **直接改答**（**2026-09-20 起既不弹确认框、事后也不提示**）、level 2/3 的答案与附件被清除、`unlockedLevel` 回退为 1；库中对应答案行与附件行确已删除。
    - **21b 提交激活条件（v4.4 重写，R1）**：~~五维中有一维尚未到终止态时提交按钮禁用且 tooltip 指出是哪一维；五维全部终止后按钮启用~~ → **v4.4 作废** —— 提交单元已改为**单个维度**：**本维度**未到终止态时提交按钮禁用且 tooltip 说明原因；本维度终止（出现 No，或九级全 Yes）后即可提交，**其余维度的进度完全不影响本维度提交**；绕过前端直接调 submit → 业务错误 `Keep answering until this dimension reaches a No or clears all nine levels.`
    - **21c 顺序兜底**：直接调 draft 接口对未解锁 level 的题提交答案 → 业务错误 `Answer levels in order.`
    - **21d 手动分与软确认弹窗已彻底移除**：全仓检索确认**不存在** `manual_score` / `derived_score` / `divergence_ack` / `divergence_delta` 四列、`dimensionScores` / `divergenceAcks` 入参、以及任何「分数与答案不符」的弹窗文案（§0.9-3）。**开发时勿沿用 v3.6 的实现。**
22. 提交确认弹窗明确告知「锁定只读 / 修改需新建提交 / 下一步对方独立评估」（**v4.4**：这是**首次**提交的文案；`submissionCount > 0` 的重复提交另有文案分支，见 §11-84）。

**配置（PRD §3.8）**
23. level 内拖拽重排后**先不生效**（填报页与维度页题序不变），**点 Publish 后**两处才按新 `sort_order` 呈现；首次拖拽出现影响提示（含「takes effect when you publish」）。
24. 题库删除某题**并发布**后，历史评估详情页仍能展示该题题干与当时的 Yes/No 与备注（由 `erl_question_config_version_id` 版本快照保证，非软删）。
    - **24a（v4.0）租户隔离**：用组织 A 的管理员新增一道题并发布，**组织 B 的管理员在配置页看不到它**，组织 B 公司的填报页题目数不变；直接构造请求读写组织 A 的题库 → 业务错误（§4.3 / §0.9-7）。
    - **24b（v4.0，v4.4 改名 D13）维度配置不激活 Publish**：只改 ~~`Dimension Weights`~~ → **`Dimension Configuration`** Tab（新增 / 删除 / 排序 / 权重任一）并保存 → `Publish` 按钮**仍为禁用**（无草稿版本）、库中无 `DRAFT` 版本行；反之只改题库不动维度配置时该 Tab 的 Save 保持禁用（§7.9-③）。
    - **24c（v4.0 → v4.9 反转）判定标准已整体撤除**：~~C2/C3 表单只有**一个** `criteria` 输入；A5 弹窗展示该单段标准 + 所属 `Era-level`~~ → **v4.9 反转**（§0.15）：C2 / C3 表单**没有** `criteria`（判定标准）输入，只有「题干 / Era band / Source」三项；A3 / A4 / 填报页的题目行**没有** `How It's Scored?` 入口（点不出任何弹窗）；抓包确认接口 10 / 12 请求体与接口 2 / 22 响应体中**均无** `criteria` 字段。

**差距分析（PRD §3.6 —— ~~⚠️ 该章已被 PRD 标为「待定功能」；本组仅在需求方确认 E 进 V1 后才需执行~~ → **v4.4 作废**：PRD `8324a3f` 已删「待定功能」标题，Goldie 确定进 V1，**本组为必执行项**，§0.10-D2 / §13-Q22）**
25. **提交任一端评估后无需手动操作**，稍后进入卡片可看到刷新后的分析；刷新期间显示 `Refreshing…` 且旧内容不被清空（**v4.4**：该行为依据由「PRD 自动刷新分析」改标 **本设计**，PRD 已删该条，§0.10-D19）。<br>**2026-09-19 补一条**（v4.59 / §0.33）：**把 Python 停掉再提交一次**，然后打开页面 —— 页面应显示 `Refreshing…` 且**管理端这次打开本身就会重新投递一次生成**（触发点 B 的被动自愈）；把 Python 起回来后再打开一次，分析应自动出现，全程无需手动 Regenerate。
    - **25a（v4.0）prompt 理解 level 语义**：传入「某维止于 level 3、level 3 内两题答 No」时，生成的 gaps 明确围绕**那两道 No 的题干与备注**（**v4.9**：`criteria` 已不在输入中，§0.15），且**不提及未解锁 level 的任何内容**、**不编造判定标准原文**（§6.6）。
26. ~~**同一份数据下，公司端与管理端看到的建议文案口吻不同**（Founder「你可以…」/ GSV「我们建议这家公司…」），且互相取不到对方的 audience。~~ → ❌ **v4.4 作废**（§0.10-D3）：PRD 已删「Founder / GSV 两套口吻」，双 audience 方案整体取消（`audience` 列删除、两份 prompt 合并为一份）。**替代校验见 §11-80（Share 门槛与 `shared` 复位）**。
27. 建议条目包含「为何相关」（`why`）说明，且能引用到该公司具体证据/备注（非通用建议）（**v4.4**：`why` 依据由「PRD §3.6」改标 **本设计选择**，PRD 已删该整段，§0.10-D20）。
28. ~~**无备注**的题推导出的条目标注 `No notes provided`。~~ → **2026-09-18 换口径与文案**（v4.57，§0.31-Z8）：**既无备注、又无可用附件摘要**的题推导出的条目标注 **`No supporting evidence provided`**；**有附件且摘要可用、但备注为空**的题，其条目 `evidenceMissing = false`、**不带该标注**。
29. ~~双方分数均高且无实质差距的维度，文案承认为优势，**不出现强行套用的差距叙述**。~~ → ❌ **v4.4 作废**（§0.10-D4）：PRD 定「有 gap 的展示建议，没有的不展示」，`STRENGTH` 枚举值、`strengths[]` 出参与 prompt 中「承认为优势」一段一并删除。**替代校验**：该维度在 Gap 区块显示 `No Gap`（绿点 + 无建议条目），且**不生成任何 `item_type = STRENGTH` 的行**（见 §11-81）。
30. **Python 生成接口断连时**：自动重试后仍失败 → 库中原有分析不被清空、页面仍显示旧分析；管理端手动 Generate 返回错误提示。
31. LLM 返回非法 `severity`（如 `critical`）时降级为 `MEDIUM` 且不报错。

**组合层（PRD §3.7）**
32. F2 ERL Tab 位于 Company List 第 6 个 Tab，只列当前用户有权访问的公司；无评估的公司各分数列显示 `—`。**v4.0**：~~五维列~~ → **v4.4：维度列按 `dimensionScores[]` 动态生成**（列数、列序、列名随当前 `status = 'Active'` 的维度集合，§0.10-D1）显示 **level 整数**（`0`~`9`），`ERL Score` 列为**加权**一位小数；`0` 与 `—` 底色可区分（§11-13）。**v4.19 追加五项（§0.23）**：① ~~请求**必带 `period` = 当前自然季度**（抓包核对），**整表各行期次一致**~~ → **v4.33 改判**（§0.23-P1 的例外已撤回）：请求**不带 `period`**，由后端逐公司按 closed month 所在季度解析（取不到的回退当前自然季度），**各行期次可能不一致**；**页面上不出现任何期次文字**（公司名后没有、表格上方也没有，§0.23-P6）；② `ERL Score` 渲染 `7.2/9`，无分数渲染 `—` 而**不是** `—/9`；③ `Stage` 列**只有 Era 徽章、没有 stage 整数**，`0` 出 `Not yet Stage 1`、`null` 出 `—`；④ 表格上方**没有** Stage 下拉与 `Min score` / `Max score`，**列头也没有排序箭头**（点表头无任何反应、不发请求）；⑤ 维度列是**中性色**，只有 `0` 与 `—` 带底色。
    - **`View` 跳该公司的 A4 全维 Score Details 页**（v3.5 改）：URL 为 `/exitReadiness/scoreDetails?companyId=&period=`、**不带 dimension**；**不再跳 Company Overview，也不再落在 `FRL` 维度页**；无评估的公司点 `View` 进入后为空态而非报错。
33. **（v4.19 改为纯接口验证）** 接口 20 的排序与筛选能力：按 `sortBy` = `overallScore` / `stage` / 任一维度 `dimensionCode` 排序、按 `stage` 与 `minScore` / `maxScore` 过滤均生效，`sortBy` 白名单随当前 `status = 'Active'` 的维度集合**动态生成**、非白名单值报业务错误（v4.4-D1）。⚠️ **本项不再经 F2 界面验证** —— 界面上的筛选控件与列头排序器已按原型全部撤下（§0.23-P2），改为直接调接口核对；本项依据由「PRD §3.7」改标 **本设计（PRD 2026-09-03 已删除该条依据）**（§0.10-D15）。
34. F2 在 20 家以上公司时只发 1 次请求、后端无 N+1 查询（开 SQL 日志核对）。

**基准（PRD §4 / §0.3）**
35. D1 两张卡齐全：~~`Latest by Dimension · {period}`~~ → **v4.40：`Current Version · {period}`，期次取该卡实际显示的那条**（= URL 上下文期次里提交时间最新的一条；带 `?period=2026Q1` 进来就显示 `Q1 2026`，哪怕库里有更晚的 `Q3 2026`；该期次无记录才落到最近一次提交）~~五行~~ → **v4.4：按当前 `status = 'Active'` 的维度集合逐维**列出两个基准分（`x.x/9`，D1），`Record History` ~~按 `period DESC, created_at DESC, id DESC` 倒序（2026-09-10 补次级键，§0.27-Z3）~~ → **v4.40：按 `created_at DESC NULLS LAST, id DESC` 倒序**（纯提交时间；**补录一条旧期次后它应当出现在列表最顶上**，这是本条的核验点）、首条（= 最近一次提交）带 `LATEST` 徽章（列数随维度数）。**2026-09-10 补（§0.28）**：`SUBMISSION TIME` 列（~~`RECORDED`~~，按原型改名）显示的是**真实录入时刻的日期**、格式 **`YYYY-MM-DD`**（如 `2026-09-10`），**不再是期末日**（旧口径下 `2026Q3` 的每一行恒显 `2026-09-30`、与 `PERIOD` 列冗余；⚠️ 只到日 ⇒ 同一天录入的两条仍会显示同一个值，这一条不能只靠该列判先后）；D1 卡一与 D3 详情卡的 `Submission time` 同取值、同格式；后端 `created_at` 为空的历史行显示 `—`。
36. D2 是**独立页面**（地址栏变为 `/exitReadiness/benchmark/add`、浏览器可后退），不是 Modal；`< Back` 与 `Cancel` 均回 D1 且不留脏数据。
37. D2 ~~十个~~ → **v4.4：`2 × 维度数` 个**分数框（两条基准线 × 每维一个）任一为空或超出 1–9 → 保存被拒并定位首个非法输入；**v4.34 追加（2026-09-15）**：两列分数框**只收整数** —— 键盘敲 `.` **打不进去**（`parser` 直接剔掉），粘贴 `1.1` 或用键盘上下键后取到的值为整数，~~构造出小数值时校验报 `Whole numbers only`~~ → **v4.39（2026-09-16）**：非数字字符**一个都敲不进去**（`onKeyPress` 拦在键盘层），`Whole numbers only` 那条校验**已删除**、屏上不该再出现这句话；⚠️ **同时核对存量**：D1 / A4 里**已落库的一位小数记录仍原样显示**（如 `7.5`），**不得**被取整；~~录入已存在的期次 → `Period` 下报错且已填分数不丢失~~ → **2026-09-10 改判**（§0.27-Z1）：**录入已存在的期次照常保存成功**，回 D1 后该期次出现两条并列、`LATEST` 徽章落在最近录入的那条 —— **两行的 `SUBMISSION TIME` 应当不同**（先后与行序一致，§0.28-Z1；若两行时刻一模一样，说明 `recordedAt` 又退回了期末日）。
38. 保存成功后 D1 立即出现该期次记录（**v4.40：新记录排在 `Record History` 最顶上**，无论期次大小）；`Current Version` ~~切到新期次~~ → **v4.40：只有当新记录的期次 = URL 上下文期次（或 URL 未带期次）时卡一才切过去**，否则卡一仍守着上下文期次那一条；同期次重复录入时切到**最近录入的那条**（§0.27-Z2）；点 `Details` 展开~~五维~~ **各维**明细**不产生新的网络请求**。
    - **38a（v4.25，§0.29）期次作为面包屑返回上下文全链路不丢**：① 在 A4 选定一个**非缺省期次**（如 `Q2 2026`，缺省期次是 closed month 所在季度、实测 `Q4 2025`）→ 末位基准 Tab 点 **`View history`** 进 D1 → URL 上有 **`&period=2026Q2`** → 点面包屑第二级 **`Score Details`** → 回到的 A4 **仍是 `Q2 2026`**（**不是** `Q4 2025`；这是本组的核心断言）；② 承上，在 D1 点某条记录进 **D3** → URL 带上下文期次（**注意 D3 屏上显示的期次取记录自身的 `period`，两者可以不同**）→ 面包屑第二级或右上 `Back` 回 D1 → **期次仍在** → 再点面包屑回 A4 → **还是同一期**（往返不丢）；③ D1 点 `+ Add New` 进 D2 → 填一条并 **`Save Record`** → 回到的 D1 URL **仍带期次**，面包屑回 A4 同一期（`Back` / `Cancel` 原路退回，同样不丢）；④ **URL 没带期次时不拼空参**：直接贴 `/exitReadiness/scoreDetails?companyId=x`（不带 `period`）进 A4 → 两个入口拼出的 URL 是**后端解出来的那一期**（`shownPeriod`）、**不出现 `&period=`** 空串；再从 D1 / D3 / D2 各自返回一次，URL 上**不得出现 `&period=&`** 之类的空段；⑤ 抓包确认 **D1 / D3 都没有因为这个参数改变取数** —— `Record History` 仍跨期次全量、D3 仍按 `recordId` 取。
39. 管理端雷达图的 `BENCHMARKIT` / `TOP_GSV_QUARTILE` 两条线**逐维取值不同**（非各顶点同值），且与该期适用记录（§7.8）的~~五维分~~ **各维分**逐一吻合；**v4.4**：雷达图**顶点数 = 当前 `status = 'Active'` 的维度集合的维度数**，不写死 5（D1 / R2）。

**通用**
40. 公司端调卡片接口并伪造他人 `companyId` → 服务端仍返回本公司数据。
41. 公司端访问 `/exitReadiness/configuration`、`/exitReadiness/benchmark`、`/exitReadiness/benchmark/add`、`?portal=gsv` 均被拦截；直接调后端写接口返回业务错误。
42. 无 GSV 提交时卡片按 §9 降级，不出现 `NaN` / `null` 字样。**v4.4 补（R3）**：缺省期次改为 closed month 所在季度后，**该季度两端均无提交时必须显示空态、不得回退到更早期次**（详见 §11-78）。
43. 雷达图：**无填充、每线异色、有图例、中心轴隐藏、悬停显示精确分**；**v4.0：公司端整个雷达图区块不渲染**（不是「渲染 2 条线」——原方案作废，§0.9-5），抓包确认响应体中无 `radar` 字段。
44. 移动端（≤768px）各页可用，表格横向滚动、页面不整体横向滚动。
45. `npm run tsc` 与 `npm run lint:fix` 无新增错误；`mvn -pl gstdev-cioaas-web test` 通过；`uv run pytest tests/erl/` 通过。

**题库版本化与发布（PRD §3.8 + 2026-08-28 裁决，v3.3 重写）**
46. **四类变更均不立即生效**：分别做一次新增、改题干、删除、拖拽重排后**不点 Publish** —— 填报页与维度详情页的题目、题序、题数、完成度分母**全部保持原样**；配置页则显示 `Draft v{n} — unpublished changes` 与对应徽章（`New` / `Edited` / `Moved`）。
47. **第一次写触发写时复制**：库中出现一条 `status='DRAFT'` 的新版本行，~~`based_on_version_id` 指向原已发布版本~~ → **2026-09-08：该列已删**，改验「`version_no = 上一版 + 1` 且 `status = 'DRAFT'`」（**2026-09-09 再订正**：~~`is_latest = false`~~ —— 该列已随 `V9` 删除，按它去库里查会直接 `42703`；与第 88 项的新判据对齐）；**另验：只有被改动的那个维度产生了新的 `erl_question_config.version_no`，其余维度的行数一行未增**（不再整库克隆）；且**已发布版本的题目行一字未改**（对比发布前后的 `erl_question_config` 快照）。
48. **草稿全局单份**：连续做 5 次变更只产生**一条** DRAFT 版本行（不是 5 条）；两个管理员分别改不同维度后，任一人点 Publish，**两人的改动一起生效**，确认框中列出的是全量摘要。
49. 点 `Publish` 后：填报页与维度页立即按新版本渲染；配置页版本条变为 `Published v{n+1}`，按钮禁用 + tooltip `No unpublished changes.`；库中无 `DRAFT` 版本。**2026-09-08 换验证点**：~~`change_summary` 快照与确认框计数一致~~（列已删）→ 改验 **`erl_question_config_dimension_version` 里出现了本次发布的 N 行维度快照**（N = 发布当时 `Active` 维度数），各行的 `dimension_name` / `dimension_abbr` / `sort_order` / `question_version_no` 与发布当时一致。⚠️ `v{n+1}` 是 **组织级发布批次号**，与各维自己的 `question_version_no` 不是同一个数。
50. **按钮激活条件是「有草稿版本」而非「有新题」**：只在 PRL **改一道题干**（不新增），切到 FRL Tab 时 `Publish` 仍激活。
51. **版本锁定（v3.4 核心）**：Founder 答了 20 题后管理员发布一版（新增 2 题 / 改 1 题题干 / 删 1 道**已答**题）→ 重新打开问卷：**题目数、题序、题干、已答内容、level 结构与解锁进度逐项不变**，被删的题还在、被改的题仍是旧题干、新增的 2 题不出现；页头仍显示 `Question set v{n}`（旧版本号）。**v4.0 补充**：即使新版在某个已通关 level 里加了题，**该评估的 `unlocked_level` 与维度分也不变**（否则已通关的 level 会凭空多出未答题）。
52. **旧版本草稿可正常提交**：承接上一项，该草稿在题库已发布 v{n+1} 的情况下**提交成功**（无业务错误、无版本校验），历史列表该行标 `v{n}`。
53. **两端跨版本**：Founder 用 v3 提交后发布 v4，GSV 用 v4 填并提交 → ~~两条记录的 `Completion` 分母不同且各自标注版本号~~ → **v4.4 改**（D12）：`Completion` 列已删，两条记录各自在**分数列下方**标注 `v3` / `v4`；Scorecard 的 Perception Gap 正常计算并在旁并列显示 `v3 / v4`，**不告警、不阻止**。**v4.4 补（R1）**：同一公司同一期次的**不同维度**同样可能绑不同题库版本（`erl_question_config_version_id` 现为**每维一份**）—— 系统一律**不阻止、不告警**，各维按自己的版本渲染与计分。
54. **发布不触发 Goldie**：发布新题库版本后，**现算指纹不变**（⇒ 接口 17 下发 `stale = false`）、内容不变、无 LLM 调用（查日志确认）。**2026-09-19**：验法由「查 `stale` 列保持 false」改为「查出参 `stale` 为 false」—— 该列已不存在（§0.33-X2）。
55. **已提交记录不受影响**：任何发布之后，已 `SUBMITTED` 的历史详情页题干、题序、题数、分数**逐项不变**（按其 `erl_question_config_version_id` 渲染）。
56. **版本入口唯一**：全仓检索确认 `ErlQuestionConfigRepository` 无「不带 `versionId`」的查询方法；且「取最新已发布版本」**只出现在创建评估记录这一处**（§7.9-①），填报 / 展示 / 计分 / 组合层 / Goldie 的取数一律来自 `erl_assessment.erl_question_config_version_id`。

**全维 Score Details（A4，2026-08-28 裁决，v3.5 新增；**v4.4** 按 §0.10-D5 双端开放）**
57. F2 `View ›` 进入的是 `/exitReadiness/scoreDetails?companyId=&period=`（**不带 dimension**），页面 H1 为 `Score Details`；~~H1 旁显示加权 `Overall Score` `X/9` 与 Stage 徽章，且与 ERL Card、F2 该行三处一致~~ → ❌ **v4.20 作废**（§0.24-Z2）：**A4 页头不得出现任何分数或 Era/Stage 徽章**（全页检索确认页头只有 H1）；「三处一致」的校验**改在 ERL Card 与 F2 两处做**（仍必须走同一个 `ErlLevelScorer.computeOverall`，§7.2-②）。**面包屑为两级** `Portfolio Companies › Score Details`（**不夹公司名**，§0.24-Z1），末级不可点、首级回组合公司列表。**v4.4 补（D5）**：A4 的第二个入口是 ERL Card 右上角 `Full View ›`，**公司端与管理端都有**（见 §11-79）。
58. **一次取全维**：进页只发 **1 次**接口 22；**维度 Tab 数 = 当前 `status = 'Active'` 的维度集合的维度数**（D1 / R2，末位另有基准 Tab，**仅管理端**渲染；管理端该期次无基准记录时 Tab 照常在、卡内走空态），Tab 标签取 `abbr`、顺序按接口返回；~~默认只有 `sort_order` 最小的那张展开，其余收起~~ → **v4.20**：**默认选中第一个维度 Tab，一次只渲染一维**（§0.24-Z3）；卡头计数为 **`{总数} questions`**，**不含「已答数」、不含 `stopped at Level N`**（§0.24-Z8）；开 SQL 日志确认后端**无按维度循环**的 N+1 查询。
59. **切端不重新取数**（**v4.20 改写**，§0.24-Z5）：组合端在维度 Tab 下有 **`GSV` / `Founder` 药丸**，**`GSV` 在前且默认选中**；点 `Founder` 后卡内四格元数据栏与逐题作答整体切换，**抓包确认不产生第二次接口 22 请求**（管理端首次即不传 `portal` 一次取回双端，切换只换本地 `dimensions[].portals` 切片）；某端该期次无提交时卡内为空态文案而非报错、页面不空白。
60. **公司端**：不渲染 `GSV` / `Founder` 药丸、不渲染末位基准 Tab；抓包确认服务端未下发 `benchmark`；**管理端另验一条**：换一家该期次**没有任何基准记录**的公司，末位基准 Tab **仍在**、卡内是空态 `No benchmark records yet.`、`+ Add New` 可点进 D2（Tab 的显隐判据是端类型，不是 `benchmark == null`，§0.24-Z4）；**有基准记录时另验表头表尾** —— 列头是 `EXTERNAL BENCHMARKS` / `TOP GSV QUARTILE`（**2026-09-10 起无 `(1-9)` 后缀**），~~`Average` 行等于 Σ(该列维度分 × 该维 `weightsApplied` 占比)、一位小数、无 `/9`~~ → **v4.22 改判**（§0.26-Z1）：**表尾不得出现 `AVERAGE` 行**，`weightsApplied` 非空时同样不出现；**D1 基准页同一张表列头一起改了、同样没有 `Average` 行**；直接构造 `?portal=gsv` 请求后端返回业务错误。~~**v4.4 补（D5）**：组合端 A4 需**同时**呈现 GSV 与 Founder 两侧记录~~ → **v4.20 改写**（§0.24-Z5）：组合端**两端数据一次取回**、以药丸切换查看（不再同屏并列）；公司端只有 Founder 侧。
61. **版本一致性**：A4 的题目、题序、题干与该次提交的 A3、历史详情页**逐项一致**（同按 `erl_question_config_version_id` 渲染）；~~元数据栏显示同一个 `Question set v{n}`~~ → **v4.20 作废**（§0.24-Z6）：**A4 的四格元数据栏不再有题集版本号**，该项改到 A3 页头 / 历史列表 / C7 上核（渲染口径本身不变）；题库发布新版后 A4 展示已提交记录**一字不变**。
62. **组件与三态徽章**（**v4.20 改写**）：~~A4 的逐题行与 A3 由同一组件渲染~~ → **v4.20 作废**（§0.24-Z10 / Z11）：A4 侧为独立的 `ScoreQuestionRow`（`DualQuestionRow` 已删除，全仓检索确认不存在引用）。逐项核：① 作答徽章**三态齐全且互不合并** —— `Yes` 绿丸 / `No` 红丸 / `yesNo === null` 灰圈减号 `Not answered`；② 次级行为 `{eraLabel} · Source: {evidenceSource}`，**全页不存在按 level 分组的组头**（无 ✓、无 `Stopped here`）；③ 备注与附件为 `NOTES` / `ATTACHMENTS` 两个大写小标签块，附件 chip 显示 `{文件名} {体积}` 且下载按钮可用（抓包确认走 `storageService.getFileLink(fileId)`，**无新接口**）；④ 基准明细表仍复用 D1 的 `BenchmarkDimensionTable`（行数随当前 `status = 'Active'` 的维度集合，D1）；⑤ `status === 'RETIRED'` 的维度在 A4 卡头**仍有 `Retired` 灰标**（§0.22 只撤了 C7 那一处）。

**v3.6 遗留校验（部分已被 v4.0 作废）**

63. ~~展示分一律取手动分~~ → ❌ **v4.0 作废**（手动分已删除）。**替代校验见 §11-21d + §11-10**。
64. **配置页编辑链路按 `questionKey`**：从题库列表点编辑，地址栏为 `/exitReadiness/configuration/edit/{questionKey}`（不是 `id`）；对一道**从未编辑过**的已发布题首次点编辑 → 触发写时复制、回填正常、保存后草稿生效（这正是按 `id` 会失配的那一步）。
65. **附件随草稿保存**：`POST /erl/assessment/draft` 的请求体中 `answers[].attachments[]` 被服务端接收并落 `erl_answer_attachment`（抓包确认字段存在，不是靠另一个接口补登记）；**请求体里不再有 `dimensionAttachments[]`**（v4.6）。
66. ~~状态摘要短路顺序~~ → ❌ **v4.0 作废**（状态摘要整块删除，§0.9-10）。
67. **旧草稿换题集的路径**：同期次同端**同维度**（**v4.4** 补维度键位，R1）已有旧版本草稿时，直接 `Add New` **不会**产生第二份草稿（唯一约束生效）；按 §7.9-⑤ 先提交旧草稿再 `Add New`，新评估绑定的 `erl_question_config_version_id` 为**当时最新已发布版本**。~~⚠️ **v4.0 注意**：旧草稿要能提交，仍须先满足「五维全部终止」，若旧草稿离终止还差很远，这条补救路径实际走不通~~ → **v4.4 作废**（§13-Q23 已关闭）：① 提交门槛已降为**本维度终止**（R1）；② 还有 **`Reset` / 接口 28** 可直接丢弃草稿（D8）—— 两条路任选其一，不再存在「摆脱不掉旧草稿」的缺口。
68. **`fund` 双端留档**：Founder 提交的记录同样落 `fund`（基金 / 组合名称快照），历史列表与详情页可见（PRD §3.3）。

**v4.0 新增校验（计分换底 / 加权 / 权限收紧 / 三卡布局）**

69. **换底后无残留**：全仓检索一次性确认以下**全部不存在** —— `answer_type`、`score` 列、`scoring_mode`、`manual_score`、`derived_score`、`divergence_*`、`criteria_founder/harvest/exit`、`ErlScoringStrategy`、`ErlScoringModeEnum`、`ErlAnswerTypeEnum`、`ErlDimensionStatusEnum`、`erl.enabled`、`dataSources`、~~`erl_answer_attachment`（旧表名）~~ → **v4.6 撤销该项**：表名已改回，`erl_answer_attachment` 现在是**正确**的表名，不得再作为「应当不存在」的检索目标（§0.12）。**其余 13 项仍是本次换底的删除清单，漏删一项即意味着两套口径并存。**
    - **v4.9 补入两项**（§0.15）：**单列 `criteria`**（实体列 / DTO 字段 / 请求 VO / 版本 diff 比对项 / 建表脚本与列注释 / prompt 正文 —— 全链路零命中）、**`ScoringCriteriaModal`**（组件文件、三处题目行的引用与弹窗 state、`.criteriaLink` 样式）。连同上面 13 项共 **15 项**应当不存在。
70. **公司端权限收紧（v4.0 核心）**：以公司端账号完整走一遍 ERL Card → A3 → 历史 → A4（若开放入口），抓包确认响应体中**始终没有** `gsvScore` / `perceptionGap` / `gapDirection` / `radar` / `benchmarkPosition` / `benchmarkitScore` / `topQuartileScore`；页面上无雷达图区块、无 GSV 分列、无 Perception Gap 列，且**不留空列或 `—` 占位**（§4.3 / §8.4「A1 公司端裁剪」）。
71. **三卡布局**：见 §11-1（DI 不消失、由右列移到左列 FI 之下）。**v4.3 补**：确认 `.btmContent` 仍是**两列**、两列等宽且 `min-width: 0` 生效（左列 FI 的宽表格不把右列挤没）。另确认**全仓无 `erl.enabled` 配置项**、`ModulesTab.tsx` **未被本次改动**（§8.6）。
72. **（v4.4 重写，R2 + D1；2026-09-08 去版本化；**2026-09-17 前置条件重写**）维度配置与降级**：~~全新环境启动后每组织一条配置版本行 + 五条 item~~ → ~~2026-09-08：全新环境启动后每组织恰有五条 `erl_dimension_config`~~ → **2026-09-17（v4.55）：种子段已删，全新环境启动后 `erl_dimension_config` 是零行 —— 这一条必须先手工造数**：先在 `Dimension Configuration` 建五个维度（`sort_order` 1 ~ 5，`weight` 各 `20.00`，`status = 'Active'`，合计 `100.00`）并 `Save`，再验 **① 库里恰有这五行、无任何配置版本行；② 综合分与「简单平均」一致**。⚠️ **顺带验空库那一支**：一个维度都没建时，维度列表为空、综合分走等权降级并打 WARN、**不报 500**（§9，2026-09-17 起这是新库默认状态）。手工把某条改成 `10.00`（`Active` 行合计 90）→ 综合分**按等权降级计算**、打 WARN 日志、页面 tooltip 提示 `Weights unavailable — using equal weighting.`、**不报 500**（§9）。
73. **（v4.4 改，D12 / D16）分母口径与次级标注**：~~历史列表 `Completion` 显示 `9/17`~~ → **列已删**；改为：~~**填报页 / A4 页头**~~ → **v4.20 把 A4 摘出去**（§0.24-Z8）：**填报页 / A3 页头**显示 `17 questions · 9 answered`（不是 `9/9` 或 `17/17`）；**A4 卡头只报总题数** `17 questions`（单复数正确：`1 question`），**不出「已答数」、不出 `stopped at Level N`**，**历史列表分数列下方**有 `stopped at L3` 与 `v{n}` 两个次级标注（§7.1.1 的分母口径论证保留为实现说明，§7.10-N2）。
74. **A4 与 A3 逐题一致（v4.0 版，**v4.9** 去掉判定标准一项）**：同一次提交在 A3、A4、历史详情三处的逐题 **Yes/No 徽章、`Era-level` 标签、来源标签、备注、附件** 完全一致，且三处都**只列已解锁的题**（§6.2 / §6.2.1）。
75. **`ErlLevelScorer` 是唯一计分入口**：卡片 / A3 / A4 / 历史 / F2 / Goldie 输入六条路径的维度分与综合分**逐一比对一致**；代码审查确认六处都调 `ErlLevelScorer`，无第二套实现（§7.2-②）。

**v4.4 新增校验（维度级提交 / 动态维度 / 配置版本快照 / closed month 期次 / Share / Gap 区块 / 草稿按钮组）**

76. **（R1，**2026-09-08 重写**）维度级提交落库**：把 FRL 答到终止并提交 → 库中 `erl_assessment` 新增一行（`dimension_code = 'FRL'`，并写入 `dimension_name` / `dimension_abbr` 快照，`level_score` / `terminated_level` / `unlocked_level` 落在该行上）；~~`is_latest = true`、`submission_seq`~~ **两列均已删除，不得断言**（§5.2）。再把 PRL 答到终止并提交 → **两行并存、互不影响**，各自按 `(company_id, period, portal, dimension_code)` 分组；每组的「最新一条」按 `submitted_at DESC, id DESC` 取首条。
77. **（~~R2：维度删除后历史不漂移~~ → **2026-09-08 整条重写：软删 + 接受漂移**）**：先在 Q1 期次完成五维提交并记下每维分、综合分、Stage 与雷达图形状；再到 `Dimension Configuration` **用~~垃圾桶~~电源按钮停用 TRL 那一行**（**2026-09-09 改图标**：TRL 已随题库发布过 ⇒ 它**没有垃圾桶**，本条验的一直是这个动作。⚠️ **2026-09-17**：TRL 不再由种子预置，本条的前置条件是**先在配置页建好五维并 Publish 一版题库**，「已进入过已发布版本」这个前提才成立）（二次确认）并把权重改成其余四维合计 100，点右上角 `Save` → ① **库里 TRL 行仍在，`status` 变为 `Inactive`、`weight` 原值保留**（**不是物理删除**）；② 新起一个期次 → 问卷、卡片、雷达图、题库页、F2 列**均只剩四维**；③ **Q1 期次的历史提交记录照常可查**（B3 列表仍有 TRL 那条，名称/缩写取评估行快照，并标 `Retired` —— 由 `status` 直接判定）；④ ⚠️ **但 Q1 的综合分、Stage 与雷达图形状会变**（TRL 退出当前集合、剩余权重重新归一化，雷达图从五顶点变四顶点）—— **这是预期行为，不是 bug**（§7.11 / §13-Q21）；⑤ 把 TRL 重新置回 `Active` → 历史与当前均恢复五维；⑥ ~~**不存在任何「有历史数据禁止删除」的前置拦截**~~ → **2026-09-09 改判**：拦截存在，但判据是「**是否进入过已发布题库版本**」—— 本条里的 TRL 已随题库发布过（**2026-09-17 起需按上面的前置条件自己造出这个状态**），故它**只有电源按钮、没有垃圾桶**（本条 ①～⑤ 描述的正是**电源按钮**的行为，验证点一字不变）；「有人填过但题库从没发布过」的维度**仍可删**（§11-86-⑰ ~ ㉑ 专门验这一支）。
78. **（R3）closed month 缺省期次与空态**：① 不传 `period` 调接口 1 / 17 / 20 / 22 → 返回的期次 = **该公司 closed month 所在季度**（与 Financial Intelligence 域显示的 closed month 同源，Manual / Automatic 两种公司各验一次）；② **该季度两端均无提交 → 空态**，抓包确认**没有**回退到更早期次的数据（这是本条的核心，v4.3 的降级逻辑会悄悄显示上一季，必须已被改掉）；③ 公司无任何 Financial Entry actuals（closed month 取不到）→ 同样空态 + 服务端 WARN 日志，**不回退、不报 500**；④ 显式传 `period` 时以传入值为准，缺省逻辑不介入。
79. **（D5）A4 入口与维度卡按钮**：① ERL Card 右上角有 **`Full View ›`**，**公司端与管理端都有**（原 §12「不做 A4 的公司端入口」已撤销）；② ~~A4 **每张维度卡的卡头**~~ → **v4.20 改**（§0.24-Z3 / Z9，维度已改横向 Tab、一次只渲染一维）：**A4 当前维度卡的卡头**各有 **`+ Add New`**（**仅 `GSV` 药丸下渲染**；公司端单端模式照常渲染）与 **`View history`**（**h 小写**，~~`View History`~~）—— 前者跳填报页且带 `?dimension={code}`（进入后只填该维），后者跳 `/exitReadiness/history?companyId=&period=&dimension={code}`（~~`?dimension={code}`~~），**两个 URL 一律取接口 22 出参、前端不拼路径**（为 `null` 时不渲染）。**v4.21 另验两条**（§0.25）：**(a)** 在 `GSV` 药丸下点 `+ Add New`，URL 带 **`&portal=gsv`**、落地的是 **B2 GSV 卷**（页头 `{维度} — GSV Validation`、`PORTAL` 显示 `GSV`）；公司端点进去恒是 Founder 卷、URL 不带该参数。**(b)** 点 `View history` 进 B3 后，面包屑「Score Details」点回来落到的是**点进来时那一期**的 A4，不是服务端缺省期次；③ **页级** `+ New` / `View history` 已移除（全页检索确认不存在）；④ 雷达图正下方有 `Benchmarkit & Top GSV Quartile ›` 链接（**仅管理端**渲染；~~与雷达图同条件~~ → **v4.60**：雷达图在维度数 <3 时不渲染，**本链接不跟这道门槛**，§0.34-Y2），点击可达 `/exitReadiness/benchmark?companyId=`**`[&period=]`**（**v4.25 补期次**，由接口 1 的 `benchmarkUrl` 下发、期次空则不拼，§0.29-Z5）—— ~~该链接是基准页在站内的**唯一可达入口**~~ → **2026-09-09 起是第一个入口、不再唯一**（A4 末位基准 Tab 的 `View history` 是第二个，§0.24-Z4）；⑤ **（v4.25，§0.29-Z1）A4 基准 Tab 两个入口带本页期次**：在**非缺省期次**的 A4 上（如 `Q2 2026`）点末位基准 Tab 的 **`View history`** / **`+ Add New`** → URL 均带 **`&period=2026Q2`**，且从 D1 面包屑「Score Details」点回来落到的是**同一期次**的 A4、**不是**服务端缺省期次（closed month 所在季度）；URL 未带期次进 A4 时，两个入口带的是**接口 22 返回的那一期**（`shownPeriod`）、不出现空的 `&period=`。往返用例见 §11-38a。
80. **（D3）Share 门槛与 `shared` 复位**：① 该 `(company, period)` 下**任一维度**缺 FOUNDER 或 GSV 的 `SUBMITTED` 记录时（**2026-09-08**：按 `(company, period, portal, dimension_code)` 内 `submitted_at DESC, id DESC` 首条判存在），`Share to founder` **置灰**，底部提示 `Share unlocks once gap analysis is available for all {total} dimensions in {period}.`；② 全部维度两端齐全后按钮激活，点击 → 接口 27 落 `shared = true` / `shared_at` / `shared_by`；③ **`shared = false` 时公司端接口 17 返回空态**（抓包确认服务端未下发条目，非前端隐藏）；`shared = true` 后公司端可见；④ **Share 之后任一端再提交触发重生成 → `shared` 复位为 `false`**，公司端重新看不到，管理端提示「内容已更新，需重新分享」；⑤ 公司端直接调接口 27 → 业务错误。
81. **（D4）Gap 区块**：① 标题 `Gap Analysis & Suggested Actions` + `AI GENERATED` 标签；② 期次 chip（如 `Q2 2026`）+ 计数文案 `{n} of {total} dimensions have gap analysis for {period}`，`total` = 该期次维度数（**不写死 5**）；③ 每维一张小卡，三态**必须由两条独立信息组合而成** —— **圆点颜色 = 双方是否都已提交**（`bothSubmitted`），**文字 = 有无 gap**（`hasGap`）：绿点 + `Gap analysis ready` / 绿点 + `No Gap` / 灰点 + `Not submitted`；构造「双方已提交但无 gap」与「未双方提交」两种数据各验一次，确认**没有被实现成单一枚举**；④ `View details` 弹出**按维度分区**的建议详情弹框；⑤ 全链路检索确认**不存在** `STRENGTH` 枚举值与 `strengths[]` 出参。
82. **（D8）草稿按钮组与 Reset**：① 填报页顶部为 **`Save as draft` / `Cancel` / `Reset` / `Submit`** 四个按钮；② `Save as draft` 是**手动落盘**；~~与 1.5s 去抖自动保存**并存**（点它立即落库，不取消自动保存）~~ → **v4.30 作废**：**只答题不点按钮时对接口 4 零请求**（抓包确认，只有接口 29；调用前后 `erl_assessment` / `erl_assessment_answer` / `erl_answer_attachment` 三张表**行数不变**），点 `Save as draft` 或 `Submit` 才发接口 4；另验**答一半刷新页面即全部丢失、且全程无任何拦截或提示**；③ `Cancel` 只离开页面、**不做任何数据操作**（草稿仍在服务端）；④ `Reset` ~~必须二次确认且弹窗写明附件一并删除~~ → **v4.29 作废：无二次确认，点下去直接**调接口 28 → 该草稿的全部答案行与附件行被删除、`unlocked_level` 回到 `1`、页面回到 level 1 初始态；**⑥（v4.26 新增）Reset 期间题库若已发新版：Reset 完成后页面显示的是新版题集**（草稿改绑到当时最新的已发布版本，题库更新弹窗随之关闭）；**该组织无任何已发布版本时保持原绑定**、Reset 仍成功；⑤ 对**已提交**记录调接口 28 → 业务错误。
83. **（D10）题库更新提示**（**2026-09-15 换形态、v4.41 回写**）：**存过草稿**的人进填报页时，若管理端已发布新版本 → 弹出**强阻断、不可关闭、必须二选一**的弹窗（无 ×、遮罩与 ESC 都不关）；**题目、题序、题数、解锁进度一字不变**（版本锁定本体不受影响）；接口 3 出参含 `latestPublishedVersionNo` 与 `hasNewerQuestionSet`。`Submit draft content` = 按旧题库就地提交（接口 5 带 `autoAnswerNo = true`：没答完时服务端补一道 No 再照常校验，**不是跳过校验**）；`Access new question library` = 走 Reset（接口 28，清答案 + 删附件后改绑最新版）。~~非阻断、可关闭、无操作按钮、关闭后不再弹~~ **已作废**（**仍然不强制退出**：两支都是用户自己选的）。<br>**v4.41 追加两个核验点**：① **补的必须是「顺序上第一道未作答的题」** —— 造一份「同级先漏答 q2、后对 q3 答 No」的草稿，点 `Submit draft content` 后查库：新增的答案行必须落在 **q2**（补末尾的话 q2 仍漏答、提交照样 400）；② **别的调用方传 `autoAnswerNo = true` 会被静默忽略** —— 拿一份**已经绑最新题库**的未答完草稿，直调接口 5 带 `true`，应得到与不传该参数完全一致的 `Please answer all visible questions before submitting.`，**库里不得多出任何答案行**（服务端只留一条 WARN）。
84. **（D11）重复提交确认文案**：该期次该端该维度 `submissionCount = 0` 时用首次文案（§11-22）；`submissionCount > 0` 时弹窗改为 **「已提交该季度评价，是否再次提交？」** 并补一句「本次提交将成为该季度的 source of truth，历史提交保留」。
85. **（D12）历史列表字段**：① 有 **`Submitted`（提交时间）列**；② **没有 `Completion` 列**（全页检索确认）；③ 分数列为**该维 Overall Score**（`{level}/9` 整数 + 该维 Era 徽章）—— **不是加权综合分**，与卡片上的综合分数值可以不同；④ 分数列下方有 `v{n}` / `stopped at L{t}` 次级文字；⑤ **`Portal` 列仅管理端渲染**，公司端该列不存在（不是置空）；⑥ 从带维度的历史列表进详情 → 接口 8 带 `dimension` 入参，页面**只渲染该维度**。
86. **（D1 / D13，v4.8 布局改版；**2026-09-09 面板改版 + 删除动作一分为二**，§0.21）维度配置 Tab**：① 第二个顶层 Tab 名为 **`Dimension Configuration`**（不是 `Dimension Weights`）；② 面板头下一行是**新增栏**（`Dimension name` + `Abbreviation` + `+ Add`），**表底不再有 `+ Add Dimension`**；③ 列表是**卡片行**（拖拽手柄 + `Name (ABBR)` + 权重输入 + 铅笔 + ~~垃圾桶~~ → **2026-09-09：铅笔 + （`deletable` ? 垃圾桶 : 电源按钮）**），**主列表看不到 `code` 列与状态列**（**2026-09-08 改口径**：原意是防用户以为能改 code，不是防运维看到 —— **行内编辑态与停用行上 `code` 必须以只读 + 一键复制可见**；**2026-09-09**：「停用行」的落点由 ~~`Show deactivated` 展开的行~~ 改为**底部常显 `Deactivated Dimensions` 区块的行**）；④ 铅笔进入行内编辑（name / abbr / 权重 + 行内 `Save` / `Cancel`），**行内 `Save` 不发任何请求**（开 Network 面板确认），只有右上角 `Save` 调接口 24；⑤ **（2026-09-09 改主体：本条此后描述的是「已发布维度」行尾的电源按钮）** ~~垃圾桶~~ **电源按钮停用**（对已随题库发布过的维度，即种子五维与任何 Publish 过的维度）**必须二次确认**，确认后仅本地标为停用，右上角 `Save` 之后（**2026-09-08 改验证点**）**该行仍在 `erl_dimension_config` 里、但 `status` 变为 `Inactive`**（不是查无此行），且它不再出现在主列表与新期次的问卷里、**改出现在底部 `Deactivated Dimensions` 区块**。⚠️ **垃圾桶此后是另一回事** —— 它只出现在 `deletable = true` 的行上，落库是 `deleted = true`（见 ⑰ ~ ㉑）；⑥ **Save 按钮双条件** —— 脏态（维度增 / 删 / 改名 / 排序 / 权重任一变化）**且** `Active` 维度权重合计 = 100%（**2026-09-08**：`Inactive` 行不计入），越界提示 `Exceeds 100% by {n}%` / `Needs {n}% more`；⑦ **（2026-09-08 整条反转）** Save 确认框文案为 **「新配置立即全局生效，已有期次的综合分、Stage 与雷达图形状会随之变化」**（**不得**再出现 v4.4 的「从下一个未开始填报的期次起生效 / 历史分数不变」）；⑧ **（2026-09-08 改判定）** 新增一个维度（`Abbreviation` 填 `OPS`）并 Save 后：库里该行的 `dimension_code` ~~是**一个 8 位随机码**~~ → **2026-09-09 订正为与 §5.1.3 / 本条 ⑯ 一致**：是 **`{abbr 前 3 位}{4 位随机}`（如 `OPS4K7M`，≤ 7 字符）**、总之**不是裸的 `OPS`**（原文「8 位随机码」写于 2026-09-08 当日 code 规则被改定为「前缀 + 4 位随机」之前，与同条 ⑯ 的正则直接冲突，按 §5.1.3 定档取值）、`dimension_abbr = 'OPS'`；**overview 页、雷达图、题库 Tab、A4、F2 列**在**新期次**上全部回显该维度（PRD §3.8 明文）；随后把它的 `abbr` 改成 `OPSX` 再 Save，**`dimension_code` 一字未变**、历史关联不断；⑨ **（2026-09-08 反转；2026-09-15 再次反转，v4.31）** ~~连续新增两个 `Abbreviation` 都填 `OPS` 的维度 → **第二个被拒**（`uk_erl_dimension_config_abbr`），提示改缩写~~ → **改为：两个都建得出来** —— 连续新增两个 `Abbreviation` 都填 `OPS` 的维度并 Save，**均成功**，库里两行 `dimension_abbr = 'OPS'` 且 `status = 'Active'`，两行 `dimension_code` 不同；⚠️ **`+ Add` 栏不得静默吞掉第二行**（原缺陷：查重不通过就不加、屏上不给提示）；另断言 `Abbreviation` 填 9 个字符仍被拒（长度校验保留）；⑩ **（2026-09-08 反转；2026-09-15 整条作废，v4.31）** ~~停用 `OPS` 后再新增一个 `Abbreviation` = `OPS` 的 → **服务端返回需显式确认的业务错误**「已有同名的已停用维度，是否改为恢复它？」；带 `confirmCreateAnyway` 重放后才新建（新 code），且库里能看到旧行仍是 `Inactive`、历史仍挂旧 code~~ → **改为：直接新建、不弹任何确认** —— 停用 `OPS` 后再新增一个同名同缩写的维度，**一次 Save 即成功**（新 code），旧行仍是 `Inactive`、历史仍挂旧 code；抓包断言请求体**不含** `confirmCreateAnyway`、响应**不含** `DUPLICATE_NAME` 分支；⑪ **漏传 code**：抓包篑改请求体删掉某已有维度的 `dimensionCode` 再 PUT → **业务错误并列出缺口**（集合完整性校验），**库里无任何写入**；⑫ **恢复（`Activate`）全链路**：停用 `FRL`（**2026-09-09**：用**电源按钮**）→ 在**底部常显 `Deactivated Dimensions` 区块**里找到它（~~开 `Show deactivated`~~ 作废，开关已撤下）→ `Activate` → 补权重 → Save → 断言 `dimension_code` **仍是 `FRL`**（不是新码）、`status='Active'`、库中该 code 仅一行、该维历史提交重新计入综合分；⑬ **连续两次 Save 不重复建行**：新增维度 Save 成功后**不刷页**、改个权重再 Save → 库里仍只有一行该维度、code 未变、**无 `Inactive` 僵尸行**；⑭ **展开 ≠ 恢复**（**2026-09-09 改操作、口径不变**）：~~开 `Show deactivated`~~ → **`Deactivated Dimensions` 区块里有停用行**、不点任何 `Activate` 直接 Save → 停用行仍为 `Inactive`、权重合计未被停用行污染（**「看得见」不等于「进了 `dimensions[]`」** —— 开关撤下后这条更容易漏，因为停用行现在**总是**在屏幕上）；⑮ **并发丢维度**：A、B 同时打开配置页，A 加维度 X 保存，B 随后保存（其 `savedAt` 已陈旧）→ **B 得到「配置已被他人修改，请重新加载」**，**X 不得被静默置 `Inactive`**；⑯ **code 形态**：新增维度的 `dimension_code` 匹配 `^[A-Z0-9]{1,3}[0-9A-HJKMNP-TV-Z]{4}$`（前缀 + 4 位 Crockford Base32）、总长 ≤ 7、不含 `I/L/O/U`（§5.1.3）。
    - **以下 ⑰ ~ ㉓ 为 2026-09-09 新增**（删除动作一分为二，§0.21）：
    - ⑰ **两个图标各就各位**：新增一个维度 `Ops (OPS)` 并 Save（**此后不 Publish 题库**）→ 该行行尾是**垃圾桶**；**已随题库发布过**的维度（**2026-09-17**：种子已删，需先建维度并 Publish 一版题库造出该状态；下称 `FRL`）行尾是**电源按钮**，且**悬停有 tooltip 说明为什么不能删**。抓包确认接口 23 出参里这两行的 **`deletable` 分别为 `true` / `false`**（前端**不自己算**）。
    - ⑱ **删除后库里还在、页面两处都没有**：对 ⑰ 里的 `OPS` 点垃圾桶（**二次确认文案必须写明不可恢复**）→ 补齐权重 → Save → ① 库里 `erl_dimension_config` 中该行**仍在**，`deleted = true`、`weight` 与 `dimension_name` / `dimension_abbr` **原值保留**、**`status` 一字未动**（不是被顺手置成 `Inactive`）；② 刷新页面后它**既不在主列表、也不在 `Deactivated Dimensions` 区块**；③ 抓包确认接口 23（**含手动带 `includeDeactivated=true`**）出参里**没有**这一行。
    - ⑲ **`dimension_code` 仍被占用**：接着连续新增若干维度 → 断言**没有任何一个**新维度分配到 ⑱ 里那个已删的 code（`existsByDimensionCode` 不过滤 `deleted`，§5.1.3）。⚠️ 这条要的是「不会重新分配」，**不是**「能不能查到」—— 重新分配的后果是旧历史静默挂到新维度身上，库里每一行都长得正常。
    - ⑳ **删掉某缩写后可以立刻新建同缩写的维度**：新增 `Ops (OPS)` → 不 Publish → 垃圾桶删掉 → **立刻**再新增一个 `Operations (OPS)` → Save **成功**（~~索引谓词 `WHERE status = 'Active' AND deleted = false` 的后半边生效~~ → **2026-09-15：索引整条删除，这条此后天然成立**，v4.31）。~~⚠️ **这条是本版最容易挂的一条**：漏掉谓词的后半边时它会报「缩写重复」，而用户在页面两处都看不见那个占着 `OPS` 的行、**没有任何入口把它放出来**（对比停用行：至少在常显区块里看得见、可 `Activate`）。**另断言不会弹「已有同名的已停用维度，是否改为恢复它？」** —— 同名软阻断（`confirmCreateAnyway`）只认 `Inactive` 行，已删行不参与。~~（**2026-09-15：两段论证都已失去对象** —— 缩写不再唯一、同名软阻断已删除；**用例本身保留**，它验的是「删掉的维度不挡新建」这个产品行为。）
    - ㉑ **抓包硬传已发布维度的 code**：直接给 `deletedCodes` 传 `FRL`（或任何 `deletable = false` 的 code）并 PUT → **业务错误**（HTTP 200 + `success: false`，文案 `This dimension was published in a question set and cannot be deleted: FRL. Deactivate it instead.`），**且库中无任何写入**（`FRL` 那行的 `deleted` 仍为 `false`、`status` 未变、其余行的 `updated_at` 一律未动 —— 校验在 `validate()` 阶段、**任何写入之前**，~~`parkAll` 之前~~（**2026-09-15：`parkAll` 已删除**，v4.31），§0.21-X8）。
    - ㉒ **只在草稿里改过题的维度仍可删**：新增维度 `Tmp (TMP)` → Save → 进 `Question Library` 给它加一道题（**只产生 `DRAFT`，不点 Publish**）→ 回 `Dimension Configuration` → 该行**仍是垃圾桶**（接口 23 的 `deletable` 仍为 `true`），删除**成功**。⚠️ 这条专打「只查 `erl_question_config_dimension_version` 有没有行」的实现 —— **草稿版本上也有快照行**（§5.1.5 开头那条 ⚠️），漏了 `status = 'PUBLISHED'` 这一层过滤，本条会退化成电源按钮且**说不出理由**。
    - ㉓ **三个桶互斥 + 删除不被误判为漏传**：① 构造请求把同一个 code 同时放进 `dimensions[]` 与 `deletedCodes[]` → 业务错误 `Dimension cannot be saved, deactivated and deleted at once: {code}`，库中无写入；② **正常删一行**（只出现在 `deletedCodes[]`）→ **不得**报「These active dimensions are neither saved nor deactivated」类的集合完整性错误（§6.4-2-⑥ 已把 `deletedCodes` 算作已交代）—— 漏改这一处时，前面 ⑰ ~ ㉒ 全对，删除仍然一次也成功不了；③ **`deletedCodes` 缺省**（整个字段不传 / 传 `null`）→ 当空数组处理，保存正常成功，**什么都没删**。
87. **（v4.4 删除清单）换粒度后无残留**：全仓一次性检索确认以下**全部不存在** —— `ErlDimensionEnum`、`erl_dimension_weight` 表与 `ErlDimensionWeight*` 系列、`erl_assessment_dimension` 表与 `ErlAssessmentDimension*` 系列、`erl_gap_analysis.audience` 列与 `ErlAudienceEnum`、`STRENGTH` / `strengths[]`、web 端 `constants.ts` 的静态 `DIMENSIONS` 映射、`erl_gap_analysis_founder.md` / `erl_gap_analysis_gsv.md` 两份 prompt、附件表的 `dimension` 列（**v4.6：该表现名 `erl_answer_attachment`**）。**这 8 项是 v4.4 的删除清单，漏删一项即意味着两套口径并存。**
    - **2026-09-08 补充删除清单（另 9 项）**：`erl_dimension_config_version` 表与 `ErlDimensionConfigVersion*` 系列、`erl_company_period_config` 表与 `ErlCompanyPeriodConfig*` 系列、`erl_assessment.submission_seq` / `is_latest` 两列及 `uk_erl_assessment_seq` / `uk_erl_assessment_latest` 两个约束、`erl_question_config_version.based_on_version_id` / `change_summary` / `dimension_config_version_id` 三列、`ErlChangeSummary*Response` / `ErlChangeSummary*DTO`、`ErlDimensionConfigService.versionOf` / `bindPeriod` / `currentVersion`、旧表名 `erl_benchmark_record` / `erl_benchmark_dimension`、旧列名 `erl_assessment.dimension` / `erl_assessment_answer.assessment_id` / `question_id` / `erl_answer_attachment.answer_id`、`V3__erl_question_version_add_dimension_config_version.sql`。⚠️ 检索 `assessment_id` 时注意**会误命中新列 `erl_assessment_id`**，需用词边界。
88. **（**2026-09-09 全条重写**，原 v4.5-L1 ~ L6 的 `is_latest` 用例作废）「在用的题库版本」按 `PUBLISHED` + `max(version_no)` 判定**：① ~~全新环境起来后，每组织的在用版本是 `version_no = 1` 的 `PUBLISHED` 行，填报页能取到题~~ → **2026-09-17（v4.55）改**：全新环境起来后**一条版本行都没有**，填报页是空态；在配置页建维度、录题并 **Publish 第一版**后，在用版本才是 `version_no = 1` 的 `PUBLISHED` 行、填报页取得到题（`is_latest` 列已不存在，判据是 `PUBLISHED` + `max(version_no)`）；② 配置页改题产生 `DRAFT`（`version_no = 2`）后，**在用版本仍是 v1** —— 草稿号更大却不得被选中，这是新判据**唯一的陷阱**，必须实测：填报页题面在 Publish 之前一字不变；③ 点 Publish 后在用版本变为 v2，且**上一版 v1 的 `updated_at` / `updated_by` 一字未动**（发布不再碰上一版，这同时是「发布改写上一版最后编辑人」那条债的回归验证）；④ 全仓检索确认 `is_latest` 列、`uk_erl_question_config_version_latest` 索引、`findByOrganizationIdAndIsLatestTrue` 方法**均不存在**；⑤ 并发两次 Publish 同一草稿 → 一方成功、另一方因草稿行 `@Version` / 行锁失败，**不会出现两个在用版本**（`version_no` 组织内唯一，天然不可能）。
89. **（v4.6，A1 ~ A4）附件双端统一题级**：① Founder 与 GSV 填报页**逐题都有**上传入口，两端渲染一致；② 上传后落 `erl_answer_attachment`，`answer_id` **有值**（库中 `answer_id IS NULL` 的行应为零，列本身也是 not null）；③ 两端填报页**都没有** `Dimension evidence` 区块，接口 4 / 5 请求体**没有** `dimensionAttachments`，接口 3 出参**没有**顶层 `attachments`（抓包确认）；④ 接口 19 删附件仍只在草稿态放行，鉴权经「附件 → 作答 → 评估」回溯，删他人公司/已提交记录的附件一律报业务错误；⑤ 接口 28 `Reset` 后该草稿的作答行与附件行全部消失，知识库条目仍在（§7.10-W3）；⑥ 全仓检索确认 `erl_assessment_attachment`、`ErlAssessmentAttachment`、`assessment_id`（附件表上的那一列）、`dimensionAttachments`、`DimensionAttachmentPanel` **均不存在**。
90. **（v4.10 + v4.11；**2026-09-08 换存储机制**；**2026-09-09 全条定档 —— 待裁决项已关闭 + 补五条新验证点**，§0.22）C7 维度按发布当时的集合显示**：① 配置页只留 `test1 / test2 / test3` 三个维度 → Publish 得 `v{n}` → 再新增 `test4`、~~删除（软删）~~ **停用**（**2026-09-09 改图标与说法**：`test2` 已随该次 Publish 进过发布快照 ⇒ 它**只有电源按钮、删不掉**，落库仍是 `status = 'Inactive'`，验证点一字未变）`test2`、把 `test3` 改名 `test3x` 并 Save → 回 C7 选 `v{n}`：**页体卡头仍是发布当时的名字**（`test3` 而非 `test3x`）、**`test4` 不出现**（不在发布当时的快照里）、卡片先后按发布当时的 `sortOrder`；② 抓包确认接口 26 出参含 `dimensions[]`（按 `sortOrder` 升序），接口 9 该字段**恒为 `null`**；③ **库里验证点换为**：`erl_question_config_dimension_version` 中该版本有 N 行，各行 `dimension_name` / `dimension_abbr` / `sort_order` / `question_version_no` 为**发布当时快照**（~~`dimension_config_version_id` 列~~ 已删）；④ ~~选中草稿版本时（无快照行）页体按**当前 `Active` 集合**渲染~~ → **2026-09-09（§0.22-Y1）：本项在 C7 上不可达** —— 下拉已不列草稿版本，服务端那条回退分支仍在（只能由 API 直调接口 26 传草稿 `versionNo` 验证）；⑤ 把某题目的 `dimension_code` 改成谁都没有的 code → ~~该题在本页**不显示**~~ → **2026-09-09 订正（§0.22-Y2）：该题仍照常显示** —— 兜底出一张裸 code 卡（name / abbr 退化为 code、**不打任何标**），v4.10-H3 的「题目永不消失」在本页恢复成立。⚠️ ~~**待裁决**：v4.11「今天已不在配置里的维度整卡不显示」…… 本项的 `test2` 是否应该显示取决于该裁决~~ → **2026-09-09 关闭（§0.22-Y3，取值 = 整条取消）**：**`test2` 照常显示**（整卡 + 它的全部题目），且**卡头没有 `Retired` 标** —— 本条 ① 里那个「已停用的 `test2` 该不该出现」的悬念到此消失，答案是**出现、不打标**。
    - **以下 ⑥ ~ ⑩ 为 2026-09-09 新增**（版本下拉只列已发布 + 卡头撤灰标，§0.22）：
    - ⑥ **下拉里没有 `Draft` 项**：先在配置页改一道题**只存草稿、不 Publish**（库里 `erl_question_config_version` 确实存在一条 `status = 'DRAFT'` 的行）→ 进 C7 展开版本下拉 → **一个 `Draft` 选项都没有**（`v{n} — Draft (edited …)` / `v{n} — Draft (not published yet)` 两支文案全站不可达）；抓包确认**接口 25 的出参里那条 `DRAFT` 仍在**（契约不变，过滤在前端 hook `useQuestionVersions` 里做）。⚠️ 这条同时是「别把过滤下沉到服务端」的回归点。
    - ⑦ **已发布维度卡头没有 `Retired` 标**：按 ① 的步骤停用 `test2` 后回 C7 选那一版 → `Test Dimension 002 (TEST002)` 卡**照常在**、题目**照常全列**，**卡头后面没有灰色 `Retired`**；DOM 里搜不到 `.retiredTag`（该样式类已从 `QuestionVersionHistoryPage.less` 删除）。
    - ⑧ **C7 不再调接口 23**：打开 Network 面板刷新 C7 → 请求里**只有接口 25 与 26**，**没有 `GET /erl/dimension/config`**；再把接口 23 人为打成 500（或断网只拦它）→ C7 **照常渲染**，不进 loading / error 态。
    - ⑨ **只有草稿、无已发布版本 ⇒ C7 空态**：取一个从未 Publish 过的组织（库里只有 `DRAFT` 行）→ 进 C7：**下拉为空**、页体是 `No published question set versions yet.`，**不再退回「选中那份草稿」**。⚠️ 这是本次唯一的行为退化，**不是 bug**。
    - ⑩ **`Retired` 标只在 C7 撤掉**（防「全站清干净」的误改）：同一个已停用维度，在 **ERL Card 的维度行**与 **A4 `DimensionQuestionsCard`** 上**仍有** `Retired` 灰标（按 `status === 'RETIRED'` 判定，`TEXT.retired` 常量仍被引用）。
91. **（v4.12，L1 ~ L8）并发不变量与两处相反表述**：① 两个用户同时编辑同一份草稿、其中一个先提交 → 另一个的存草稿 / Reset **不得**把已提交记录写回草稿态，其作答与附件**不得**被删（`erl_assessment` 加 `@Version` + 写路径 `FOR UPDATE`，V4 脚本已执行）；② 管理员 A 加题、B 同时点发布 → 新题**不得**落进已发布版本，A 侧收到「刚被别人发布过、请重载」而不是 500；③ 差距分析生成期间又有人提交 → 内容照写，但**产物里存的指纹是「这份内容所依据的那一批」**，故下一次读现算出来必然不等 ⇒ 页面如实显示 `Refreshing…` 并自动重投（触发点 B），**不得**出现「`stale = false` 但内容漏了一次提交」（**2026-09-19**：~~持锁者跑完会补跑，上限 2 轮~~ 与 ~~`stale` 仍为 true~~ 两处随 P3 改写 —— `stale` 是算出来的，不需要谁去保留，也不需要「补跑计数」，§0.33-X2 / X5）；④ 提交 `dimensionCode = 'ZZZ'`（合法字符集但配置里没有；**2026-09-08**：`status = 'Inactive'` 的维度**也算「没有」**）→ 接口 4 / 5 / 28 **全部报业务错误**，库里不得出现该维度的行；⑤ 0 题维度点提交 → 业务错误（文案含 `no questions`），且填报页整页空态、`Submit` 禁用；⑥ 生成门槛未达成的那 9/10 次提交 → **Sentry 里一条 ERROR 都没有**（只记 INFO）；⑦ 乐观锁冲突 → HTTP 200 + `success: false` + `changed by someone else` 文案，不是 500。
92. **（v4.38 / v4.42）B 填报页两格草稿提示的分工**：① 存过草稿的人**刷新 / 退出重进**：只看到顶部 `Draft restored` 横幅，按钮行左下那一格**恒空**；② 同一页点一下 `Save as draft` 并落盘成功：横幅**撤下**、那一格出 `Draft saved {时刻} (UTC) by {姓名}`（不显示角色）；③ **两者不得同屏** —— 切期次 / 切维度后也不得出现「横幅 + 那一格同时在、内容重复」的一帧；④ 没有待保存项时点 `Save as draft`：**一条请求都不发**、那一格仍空、横幅不撤。
93. **（v4.42）Reset / `Discard draft` / `Access new question library` 之后重进不弹横幅**：存过草稿 → 清空（接口 28）→ **不再点 `Save as draft`** → 刷新 / 重新进入：顶部**不得**出 `Draft restored`（草稿行还在、`lastSavedAt` 也还在，但 `answeredCount = 0`）；元信息栏 `ASSESSED BY` / `ROLE` 同时应显**当前登录用户**、而不是清空那个人。清空后**再答一题并存盘**，重进则横幅照常出。
94. **（v4.54）空草稿撞上新版题库：不弹窗、直接换新题库**：存过草稿 → 清空（`Reset` / `Discard draft` / `Access new question library`）→ **不再点 `Save as draft`** → 管理端**发布一版新题库** → 重新进入填报页：① **不得**弹「The question library has been updated」弹窗；② 屏上的题目应是**新版题库**的题（抓包看接口 3 的 `questionVersionNo` 已等于 `latestPublishedVersionNo`，中间多一次接口 28 是预期的）；③ 全程**没有任何 toast**；④ 对照组：清空后**答一题并存盘**，再发布新版本、重进 → 弹窗**照常弹**，两颗按钮行为一字不变。

---

## 12. V1 明确不做（YAGNI / 风险控制）

- **不建独立 Exit Readiness 落地页 / Dashboard 路由**（PRD §3.1）。
- **A4 全维 Score Details 页已按 2026-08-28 裁决纳入 V1**（§6.2.1 / §8.4）；但 A4 上**不做**维度间对比图、导出、以及 ~~Strengths & Gaps~~ → **v4.4**：Gap 建议 / Data Sources 的重复区块 —— 单维深度仍走 A3。
- ~~**不做 A4 的公司端入口**（2026-08-28 确认，§13-Q17）—— ERL Card 上**不加**「View all dimensions」之类的链接，A4 在 V1 只由 F2 `View`（管理端）进入~~ → ❌ **v4.4 作废**（§0.10-D5）：PRD `57225d2` 推翻了该裁决，**ERL Card 右上角 `Full View ›` 是 A4 的入口，公司端与管理端都有**（原型截图为准）。§13-Q17 标记为「已被 PRD 推翻」。
- 不做完整 BPMM 评估交互，只显示参考数字（PRD §5）。
- 不做 Ask Goldie 对话接入、Finance 页 ERL 卡片与回跳。
- 不做 Goldie 建议的跟踪 / 指派 / Deadline（~~PRD §3.6「MVP 不含」~~ → **v4.4 改标依据**：PRD `273671a` 已删该整段，现理由为 **PRD 未要求**，§0.10-D20）。
- **不做「GSV vs. Founder 分数对比 Tab」**（**v4.4** 显式列出）—— E1/E2 已完整实现，该 MVP 替代方案无必要；依据：~~PRD §五「MVP 备选方案」~~ → **PRD `273671a` 已删该整段，现理由为「PRD 未要求」**（§0.10-D21 / §13-Q6）。
- 不做 Goldie 生成结果的人工编辑 / 审核流（§13-Q9）。
- 不做差距分析的版本历史，只保留「最新一份 + 自动刷新 + 手动 Regenerate」。
- **不做计分模式的可切换抽象**（v4.0 改）—— PRD 已把打分格式定档为 Yes/No 逐级解锁，只实现这一种；原 `ErlScoringStrategy` 策略工厂与 `SCORE_1_9` 模式**一并删除**（§7.2-②）。
- **不做 1–9 分打分控件、题均分、手动维度分、软确认弹窗、每维状态摘要、Data Sources & Cadence**（v4.0 新增）—— PRD 2026-09-02 修订已把这六项的依据全部移除（§0.9-1 / -3 / -10 / -13）。
- **不做「权重快照」**（v4.0 提出 → ~~v4.4 作废~~ → **2026-09-08 恢复生效**）—— 权重独立保存、**实时生效**，既不随题库版本快照、也不在 `erl_assessment` 上存每维权重快照；代价是**改权重会回溯改变历史期次的综合分与 Stage**（§7.10-W1 / §13-Q21）。~~v4.4：需求方裁决维度与权重整体版本化、期次绑定、历史永不漂移~~ → **2026-09-08 作废**：需求方选择**接受漂移**，`erl_dimension_config_version` 与 `erl_company_period_config` 两张表一并删除（§5.1.2 / §5.1.4）。
- **不做维度的物理删除**（v4.4 提出 → ~~v4.8 作废改物理删~~ → **2026-09-08 恢复生效**，**2026-09-09 仍生效**）：配置页的两个破坏性动作**落库都是置位、都不删行** —— 停用 = 置 `erl_dimension_config.status = 'Inactive'`（行与 `weight` 原样保留、可恢复），**删除 = 置 `deleted = true`**（**2026-09-09 新增**：行与 `weight` 同样原样保留，只是**所有读侧一律排除、页面无恢复入口**，§5.1.3 / §7.11-④）。⚠️ **「真删」指的是「从产品里彻底消失」，不是 SQL `DELETE`** —— `dimension_code` 被五张表当历史外键引用，真 `DELETE` 会让那些历史数据解不出维度名。~~v4.8：`status` 整列删除、历史安全靠期次-版本绑定~~ → **2026-09-08 作废**（期次绑定表已删，`status` 已加回并落库）。
- ~~**不做「维度删除的前置拦截」**（v4.4 新增，v4.8 / 2026-09-08 仍成立；当时依据：软删下行根本不消失，历史提交仍能按 `dimension_code` 取到名称与缩写，拦截没有保护对象，故无需在删除前查引用、也无需二次确认之外的任何阻断）~~ → **2026-09-09 整条作废**（需求方当日裁决）：**前置拦截现在有了，但判据换了** ——
  - **拦的是「已进入过某个已发布题库版本的维度不许删」**（只能停用），判据是 `erl_question_config_dimension_version` join `erl_question_config_version` 且 `status = 'PUBLISHED'`（§6.4-3-⑨）。
  - **仍不做的是「有历史数据禁止删除」这个判据本身** —— 它会连「有人填过、但题库从没发布过」的维度也拦住，而那种维度删掉是安全的；**也仍不做**「删除前查五张表的引用计数」这类阻断（引用照旧存在、照旧解得出名字，那不是删除该关心的事）。
  - **保护对象不是那一行**（置位下行不消失），是**已发布题库版本的语义**（§7.11-④ / §13-Q24 改判 / §0.21-X12）。
- **不做全局统一题库**（v4.0 改）—— 题库与权重**按组织（租户）**隔离（PRD §4）；组织内不再按公司细分，公司级覆盖仍不做。**题库版本化已按 2026-08-28 裁决纳入 V1**（§7.9）。
- **不做撤回（已发布 → 草稿）、单维度发布、变更逐条勾选发布、定时发布、版本回滚与版本对比 UI** —— 依 2026-08-28 裁决，V1 只实现「改草稿 → 全量发布」一条路径（§7.9）。**v4.1 澄清**：只读的**版本历史页**（C7）已纳入 V1。**v4.2 再澄清**：C7 现在能按版本回看**那一版的整份题面**（接口 26），但仍**不含回滚、不含版本间 diff 视图**（两版并排比对、逐题标红绿都不做）——「能看某一版长什么样」与「能比较两版差在哪」是两件事，本条其余不变。
- **不做草稿的丢弃（Discard changes）** —— 裁决未要求；代价是误改只能手工改回来（题库低频、变更摘要可见，可接受）。若实际使用中成为痛点，加一个 `DELETE /erl/question/draft` 即可，不影响现有模型。
- **不做草稿的编辑锁 / 按人隔离的草稿 / 变更冲突合并** —— 题库配置是低频管理动作，多人协作靠界面提示（§7.9-④），不上并发控制。⚠ **2026-09-07 补限定**：这里说的「不上并发控制」指**草稿之间**不做编辑锁与冲突合并（后保存覆盖先保存，接受）；而「已发布版本一个字节都不改」（§7.9）与「已 SUBMITTED 的记录一律只读」（§7.7）这两条**不变量**已由 `@Version` 乐观锁 + `SELECT … FOR UPDATE` 悲观锁在数据库层兜底 —— 两者不是一回事，别把这条 V1 范围声明读成「跨状态覆盖也不管」。题库草稿的并发编辑取悲观锁而非乐观锁，是为了让**失败落在低频的发布方**：两个管理员同时编辑不同维度的题目本是设计允许的，若靠乐观锁，后提交者会因为版本号被对方改过而丢掉刚录的题目。
- **不做在填评估的重基 / 「升级到最新题集」按钮**（v3.4 依裁决删除）—— 评估版本锁定，一次评估自始至终用同一版题集（§7.9-⑤）。
- ~~**不做题集版本不一致的告警 / 阻断**~~ → **v4.58 改判（P4 已实现，§0.32）**：**阻断仍然不做** —— 同期次两端跨版本、旧版本草稿延迟提交照旧**允许**，版本号照旧只在界面标注（§7.10-13 / N1 / N2）；**但维度级的「不可比」要告警**：两端同维 `question_version_no` 不等时，接口 1 / 17 的该维下发 `questionSetMismatch` + `mismatchSide`，A1 小卡渲染黄点 `Question set mismatch`、该维不送进 Goldie。判据只能是维度级题集版本号（用组织级发布批次号会假阳性，§0.32-Y2）。
- 不做评估期次之间的对比、趋势图、导出。
- 不做题库批量导入导出。
- 不做 `SUBMITTED` 回退为 `DRAFT` 的重开流程 —— PRD 的口径是新建提交，不是重开。
- ~~**不做「丢弃在填草稿」的接口**（`DELETE /erl/assessment/draft`）—— 代价见 §7.9-⑤：想换到最新题集必须**先提交旧草稿再新建**，历史会多一条记录。~~ → ❌ **v4.4 作废**（§0.10-D8）：PRD `08b7a32` 把填报页按钮组定档为 `Save as draft` / `Cancel` / `Reset` / `Submit`，**`Reset` 就需要这个接口** —— 已作为**接口 28** 纳入 V1，同时关闭 §13-Q23。
- 不冗余存储展示用聚合分数（**综合分 / Stage / Era 全部实时算**；`level_score` / `terminated_level` / `unlocked_level` 落库是因为解锁进度是草稿期交互状态、必须持久化 —— **v4.4**：这三列已由 `erl_assessment_dimension` **上提到 `erl_assessment`**，理由见 §5.3 末段 / §0.10-R1）。~~**v4.4 澄清**：R2 快照的是期次与配置版本的绑定关系……~~ → **2026-09-08 删除**：无配置版本、无期次绑定，**维度与权重一律取当前 `Active` 值**，综合分依旧实时算（因而会随配置变化而漂移）。
- 不新增 dva model（`src/models/` 已冻结）。
- 不引入 SQS：Java 与 Python 走同步 HTTP 经网关。
- 不接 Fireflies / SharePoint 作为 Goldie 数据源（~~PRD §3.6 明确为后续~~ → **v4.4 改标依据**：PRD `273671a` 已删「已知 TBD 与 MVP 备选方案」整段，现理由为 **PRD 未要求**，§0.10-D21）。

**识别到但本次不处理**：

- `fi/` 业务域仍是扁平结构、`QuickbooksController` 在 Controller 内 try-catch 并直接收发 Entity，均不符合 `standards/`，属存量技术债 —— 已记入 `CIOaas-api/docs/待优化项.md`（2026-08-26 条目）。
- `CompanyOverviewPage.tsx` 单文件超 1600 行、DI / FI 分支混杂（§10.4）。
- 题量较大的问卷页单页渲染；题量再翻倍需考虑虚拟滚动。

---

## 13. 待确认事项（开发前必须对齐）

> 编号已与 **PRD §五「明确的 TBD 事项」** 对齐；PRD 未列但本设计发现的新问题标注为「设计新增」。

| # | 对应 PRD TBD | 问题 | 影响 | 建议 |
|---|---|------|------|------|
| **Q1** | §五-1 | **ERL 卡片上 Gap Analysis 的呈现方案**（摘要几行？点开何处？）与 **BPMM 的内容 / 规则 / 数据来源**（1–5 的分值从哪来？现有系统有无该数据？） | 卡片布局与 `bpmmScore` 的取数实现；BPMM 无数据源则该字段无法落地 | Gap 摘要建议取 summary 前 2 行 + `View details`；**BPMM 数据源必须先给** —— 在此之前 `bpmmScore` 恒 `null` 且隐藏该行，其余照常开发 |
| ~~**Q2**~~ | 设计新增 | ✅ **已由 PRD 自身关闭（2026-09-02，`621e857`）**：原问题是「DI 卡片『系统级隐藏』与现有公司级 `diStatus` 开关的差异」+「新增 `erl.enabled` 属字面偏离」。PRD 把 §3.1 改为「DI 卡片**放在 FI 卡片下**；DI 数据、打分**保留概览信息和入口**」—— **不再要求隐藏 DI**，开关之争与偏离物一并消失（§0.9-6 / §8.6） | — | 无需答复。开发按 §8.6 执行：DI 区块**整块下移**到 FI 之后、渲染条件 `DiStatus` 原样不动、**不新增任何配置项**；**勿沿用 v3.x 的 `erl.enabled` 方案** |
| **Q3** | §五-2 / §五-3（**建议删除这两条 TBD** → §0.9-④ M3） | **计分口径（v4.0 大幅收窄）**：① ~~推导分的计算方法~~ → **已关闭**：PRD 把维度分定档为 level 口径，题均分整体删除；② ~~状态摘要枚举与阈值~~ / ~~软确认分歧阈值~~ → **已关闭**：两块功能均被 PRD 删除（§0.9-10 / -3）；③ **仅剩一项**：Stage 由**加权综合分**推导的**取整规则**（round / floor / 查表？）—— PRD §3.5 只说「由综合分数与 Workbook 的 Era 边界推导」 | 只影响 Stage 徽章的整数显示；Era 徽章不受影响（Era 只按 §7.3 的区间判，不经 Stage） | 现按 `stage = clamp(round(score), 1, 9)`，**且 `score == 0` 时 `stage = 0`**（§7.3）。实现集中在 `ErlLevelScorer`，改规则只改一处 |
| ~~**Q3b**~~ | 设计新增 | ✅ **已彻底消失（v4.0）**：原问题是「GSV 手动 / Founder 推导，口径不对称怎么办」，v3.6 记为「由 PRD 选定双端手动而关闭」。PRD 2026-09-02 把手动分整体删除后，**两端本就只有 level 一种口径**，该问题连讨论前提都不存在了（§7.1 末段） | — | 无需答复 |
| **Q4** | 设计新增 | **题库初始内容从哪里来**？PRD §3.3 说「30+ 题目」、§3.9 示例 `45/45`、原型是 165 题，三者不一致。正式题库清单是否已有？ | 决定首版题库内容；影响 UAT 可用性（**2026-09-17 起 `erl_init.sql` 不再预置任何题目，只能靠录入**） | 代码不写死题量（已按题库配置驱动）。**v4.0 更新**：2026-09-03 重抓原型已能反解出**完整 165 题 + 每题的 level 归属 + Source 标签**（分布见 §2.3.1-③），这是目前唯一成型的候选题库 —— 建议**要么由产品确认直接采用它作为首版种子**，要么给出正式清单；~~当前 `erl_init.sql` 只放了 15 道 `[PLACEHOLDER]`（每维 L1/L2/L3 各一道）**仅够跑通解锁链路**，UAT 前必须替换。~~ → **2026-09-17（v4.55）：种子段已整段删除，一道占位题都没有** ⇒ **UAT 前必须从零录入**（不再是「替换」）。录入走配置页草稿 → Publish，不要直接改库（§7.9-⑥）。⚠️ 自测想跑通「level 1 全 Yes → 解锁 level 2」的解锁链路，至少每维铺 3 道（`era_band` 1 / 2 / 3 各一道）；⚠️ 真实题库的 level 分布是**稀疏**的（§2.3.1-③：PRL 只用 level 3/6/9、RRL 最高到 L8），「首个可作答 level 不是 1」「全通关得分不是 9」两条分支要按真实分布录入后才走得到 |
| ~~**Q5**~~ | §五-2 / §五-8 | ✅ **已由 PRD 自身关闭（2026-09-02）**：① 「No 中断时该维度分数如何计算」→ **PRD §3.3 直接给出答案**：~~分数 = 出现 No 的 level − 1~~ → ⚠️ **v4.37 就地标注**：该取值已由需求方 2026-09-15 裁决换底为「**最后一个整级通关的 level**」，**Q5 的关闭结论不变**（口径确实已定、V1 直接实现），只是分值换了底；九级全 Yes 为 9（§0.9-1）；② 「题序变更对进行中 / 历史评估的解释策略」→ **v3.4 的版本锁定已解决**：评估恒按绑定版本渲染与计分，题序变更对已存在的评估毫无影响（§7.9-⑤） | — | 无需答复。V1 **直接实现**该计分规则（§7.2），不再是「留接口占位」。PRD §五 的 TBD-2 建议删除（§0.9-④ M3） |
| ~~**Q6**~~ | §五-5 / §五-6（**PRD `273671a` 已删整段**） | ✅ **v4.4 关闭**（§0.10-D21）：① 「**GSV vs. Founder 分数对比 Tab**」—— PRD 已删掉「已知 TBD 与 MVP 备选方案」整段，该备选方案连同其依据一并消失，**结论仍是不做**（§12，理由改标「PRD 未要求」）；② 「Gap」的粒度 —— PRD §3.6「分为五个维度」已明确即**按维度**，与本设计取值一致 | — | 无需答复。开发按本设计执行：不加对比 Tab；gaps **按维度**产出，逐题证据作为输入上下文 |
| **Q7** | §五-7 | **可见角色子集（v4.0 部分关闭）**：① ERL 卡片及后续页面是否对「当前可访问 Company Overview 的全部角色」开放，还是需收窄？② ~~ERL Configuration 的 admin 是哪一级~~ → **PRD 已答**：§3.8「仅 portfolio portal」+ §4「配置层级按**租户**层级」⇒ 管理端 + 按 `organization_id` 隔离（§0.9-7）。**剩余子问**：同一组织内是否要再分「可编辑题库 / 可发布 / 可改权重」三级？③ 前端新增 API 域 `exitReadiness/` 需登记进 `CIOaas-web/standards/architecture.md` §2 | 权限矩阵（§4.2）与规范符合性 | ① 本设计按 §4.1 的 `roleType` 二分实现；② 本设计**不再分级**（组织内管理端均可编辑 + 发布 + 改权重，§7.10-8）；③ 随本功能一并更新规范文件 |
| **Q8** | 设计新增（**①已关闭**） | ① ~~§3.2「创始人不显示 GSV 专属字段」vs §5「创始人并列查看双方分数」~~ → ✅ **已由 PRD 自身关闭（2026-09-02，`74f25df`）**：§3.5 改为「创始人**只能查看自己的分数**」，等于选定「不并列」；设计的旧裁决（GSV 分对创始人可见）作废，现口径见 §4.2 注（§0.9-4）。② **仍需确认**：PRD §3.5「Scorecard」的展示项在 ERL Card 与维度页之间的归属 —— 本设计的划分见 §8.5（v4.0 已加「公司端可见」一列） | 影响公司端可见范围与两个页面的信息密度 | ① 无需答复，按 §4.2 执行；② 请产品对 §8.5 的表格直接勾选确认 |
| **Q9** | 设计新增 | ~~LLM 生成的 strengths / gaps / actions~~ → **v4.4**：LLM 生成的 **gaps / actions**（`strengths` 已删，§0.10-D4）是否需要 GSV **人工编辑或审核**后才对公司端可见？ | 影响是否需要 `status` 字段与编辑页 | **v4.4 大幅缓解**：D3 已引入 **Share 机制** —— `shared = false` 时公司端本就看不到，GSV 点 `Share to founder` 才推给创始人，重生成后 `shared` 复位。**「未审核内容直接推给创始人」的风险已由 Share 覆盖**；剩余问题仅剩「是否还要一层可编辑/可审批的正式流程」，V1 仍**不做**（生成即可 Share）。~~若要审核……自动刷新只更新 GSV audience~~ → **作废**（audience 已删） |
| ~~**Q10**~~ | 设计新增 | ERL 附件写入公司 Memory File 后，**是否与 chatbot 知识库共用同一空间**？公司端上传的 ERL 证据是否应对管理端可见、反之如何？ | 决定 `ensure_kb_space` 的空间组合键（现有链路：APP 按公司 / ADMIN 按组织） | ❌ **2026-09-18 改判并关闭**（v4.57，§0.31-Z1 ~ Z3）：~~建议沿用现有端类型规则（公司端上传 → 公司空间；管理端上传 → 组织空间），与 chatbot 一致，**不为 ERL 单开空间**~~ **作废** —— ERL 答题附件**单开 space**：业务关联组合键的 `business_type` 换成 **`ERL_ATTACHMENT`**（`APP` 仍按 `company_id`、`ADMIN` 仍按 `organization_id`，**端与粒度一字不改**，改的只有 `business_type` 这一位），配**新处理类型 `SUMMARY_ONLY`** —— **只解析正文 + 出摘要，不分片不向量化**，`ai_rag_ent_kb_chunk` **零行**；正文落 `ai_rag_entry.content_text`、摘要落 `.summary`（Goldie 唯一消费的就是摘要）。因此 ERL 附件**不进 chatbot 检索、不进 Memory 面板、不进知识库面板**，原问题的后半问（「公司端证据是否对管理端可见」）**连讨论前提都不存在了** —— 两端各自的 ERL space 互不相交，且都不参与任何面板展示。<br>**改判理由（决定性的一条）**：chatbot 的检索范围由 **space 组合键**圈定（`find_chat_space_id` / `find_app_space_ids`），chunk 层 where 里**没有 `business_type`** ⇒ **只改 `business_type` 而不换 space，chatbot 照样检索得到**，隔离**必须落在 space 维度**。反之 Memory 面板与知识库面板确实按 `business_type = 'KNOWLEDGE_BASE'` 过滤，换了取值即自动排除。详见 §6.7 |
| ~~**Q11**~~ | §3.8（2026-08-28 新增 Publish） | ✅ **已裁决（2026-08-28）+ PRD 已回写（2026-09-02，`621e857`）**：**所有变更都经发布 + 题库版本化**；**不需要**撤回与单维度发布。设计已按此重写（§0.5 / §5.1.1 / §7.9） | — | ✅ **回写已完成**：PRD 已删去「变更立即生效」一句，并把 Publish 条件改为「有**新问题、新顺序或新编辑内容**…**点击保存为新版本**」—— 与本设计完全一致，v3.6 提出的两条题库回写建议**已被采纳**（§0.9 台账）。**遗留（无需答复、开发时按设计执行）**：同组织的多管理员共享同一份草稿、任一人发布会连带发布他人改动（§7.9-④）；V1 不提供丢弃草稿（§12，但见 **Q23**） |
| ~~**Q13 ~ Q16**~~ | 设计新增（v3.3 边界 §7.10） | ✅ **已随「版本锁定」裁决一并关闭（2026-08-28）**：Q13（题干被编辑后旧答案是否有效）与 Q14（删题时已答内容如何处置）**问题本身消失** —— 评估锁定在自己的题库版本上，看不到新题面；Q15（发布是否触发 Goldie 重生成）**结论为不触发** —— 分析输入锚在版本快照上、发布后一字未变；Q16（同期次两端可否不同版本）**结论为允许** —— 裁决原文即取值，页面标注两端版本号。详见 §0.6 / §7.9-⑤ / §7.10 | — | 无需答复。**版本锁定衍生的 N1 ~ N3 三条边界**（旧草稿无限期有效、同期次多次提交跨版本、不做题集升级按钮）已在 §7.10 定档，开发时按设计执行 |
| ~~**Q12**~~ | §3.7（2026-08-28 改口） | ✅ **已裁决（2026-08-28）**：F2 `View` 的落地页是 **A4 全维 Score Details 页**（一页看全五维），不再落到某个单维度。设计已据此复活 A4（§0.7 / §6.2.1 / §8.4） | — | **待回写 PRD**：§3.7 的「View（跳转到该公司的 Score Details 页面）」需明确为「**全维** Score Details 页」，并补上该页的内容清单。⚠️ **v4.4**：PRD `57225d2` 已补上内容清单，本条闭环 |
| ~~**Q18**~~ | 设计新增（v3.6） | ✅ **已裁决（2026-08-28）**：题目来源标签中的 `Founder / CFO` 是正确写法，**PRD §3.3 的 `Founder/CTO` 是输入错误**。设计保持 `Founder / CFO`（§5.1） | — | 无需答复。**待回写 PRD**（→ §0.10-④ M7）：§3.3「每题显示来源标签（Founder/CTO、Looking Glass、SharePoint 等）」中的 `Founder/CTO` 应改为 `Founder / CFO` |
| **Q17** | 设计新增（v3.5） | ❌ **v4.4：已被 PRD `57225d2` 推翻**（§0.10-D5）—— ~~✅ 已确认（2026-08-28，需求方接受设计建议）：**V1 不为公司端加 A4 入口**，A4 的唯一入口是 F2 ERL Tab 的 `View`（管理端）~~ **作废**。PRD §3.5 / §3.7 给出 `Full View` 入口；2026-09-06 原型截图显示**组合端的卡片同样有 `Full View`**（同一张卡上还有 `Share to founder`） | §4.2 的 A4 行、§8.1.1「不要自行加链接」、§12「不做 A4 的公司端入口」**三处禁令一并撤销**；A4 的入口由 1 个变为 2 个（F2 `View` + ERL Card `Full View ›`） | 无需答复，按 PRD + 原型执行：**两端的 ERL Card 右上角都加 `Full View ›`**；A4 每张维度卡卡头加 `Add New` / `View History`，原**页级** `+ New` / `View history` 取消。⚠️ PRD §3.5 写的「仅 Company portal」与原型不符，**列入回写 M9** |

**~~v4.0 新增待确认（Q19 ~ Q23）~~ → ~~v4.4：五条全部关闭~~ → **2026-09-08：四条关闭，Q21 重新打开****（Q19 / Q21 由 2026-09-06 需求方裁决关闭，Q20 / Q22 由 PRD 自答关闭，Q23 由接口 28 + 维度级提交关闭）。**保留原文以便追溯裁决过程：**

| # | 对应 PRD | 问题 | 影响 | 本设计取值 / 建议 |
|---|---|------|------|------|
| ~~**Q19**~~ | §3.3（打分格式） | ✅ **v4.4 关闭 —— 取值「按维度独立」**：需求方 2026-09-06 裁决把**提交粒度改为维度级**（§0.10-R1），逐级解锁天然按维度独立，「全局同步」读法失去存在基础。**原问题存档**：🔴 **逐级解锁是「按维度独立」还是「五维全局同步」？** PRD 原文「**五个维度的所有问题**按照 Era 和等级依次显示」听起来像五维一起按 level 推进；但「**该维度**最后一个全部 Yes 的 level 的 level 为**此维度**得分」又是维度独立的。两种读法的填报体验与得分结果都不同 | **本轮最大的实现分歧点**：全局同步下，任一维度先出现 No 就会卡住其余四维、让它们拿不到本可得的分数（一个维度的 No 会压低另外四个维度的分数）；按维度独立则每维各自推进到自己的终止 level | ~~**本设计按「按维度独立」实现**（§7.2-① / §0.9-15）…… **请需求方确认**；若确为全局同步，改动面是 §7.2 的状态机与 §6.3 的 `canSubmit` 判定~~ → **v4.4：需求方已裁决为「按维度独立」，并进一步把提交单元也降到维度级** —— `erl_assessment` 加 `dimension` 列、`erl_assessment_dimension` 整表删除、`canSubmit` 改为「本维度终止」、`erl_question_config_version_id` 绑定粒度变为每维一份（§0.10-R1 / §5.x / §6.3）。**无需再答复** |
| ~~**Q20**~~ | §3.1 vs §3.5 | ✅ **v4.4 关闭 —— 取值「公司端不给 gap」**：PRD §3.5「创始人只能查看自己的分数」已定档，与本设计取值一致；仅剩 PRD §3.1 卡片清单的措辞待回写（**M10**，不阻塞开发）。**原问题存档**：**公司端能否看到 Perception Gap？** §3.5 说「创始人只能查看自己的分数」，而 §3.1 的卡片内容清单仍列「Perception Gap：Founder 和 GSV 每个维度的分数差」—— 创始人若能看到 gap，用自己的分即可反推 GSV 分 | 公司端 ERL Card 与 A3 是否渲染 gap 列；服务端是否下发该字段 | **本设计按「公司端不给 gap」实现**（§4.2 / §4.3）—— 否则 §3.5 的限制形同虚设。**v4.4：该取值已被 PRD §3.5 确认，问题关闭**；只剩 **PRD §3.1 卡片清单需回写**（原 §0.9-④ M4，现 **M10**，仍未闭环 —— 属文档一致性问题，不阻塞开发） |
| 🔴 **Q21**（**2026-09-08 重新打开**） | §3.8（权重） | 🔴 **改权重是否应该改变历史期次的综合分？** ~~v4.4 关闭，取值「不影响历史」~~ → **2026-09-08 需求方重新裁决：权重不做任何快照，接受漂移** | 当前取值的后果：改权重 / 启停用维度会**回溯改变**已提交历史期次的综合分、Stage 与雷达图形状（`level_score` 有快照，**权重没有**）。已删 `erl_dimension_config_version` / `erl_company_period_config` 两张表，§7.10-W1 改回「接受历史漂移」 | **本设计按「接受漂移」实现**（§7.1 / §7.11 / §12）。若后续不可接受，**最省的改法**是在 `erl_assessment` 补一列 `weight` 快照（提交时冻结本维权重）—— 但那只救得回权重，**救不回「那个期次有哪些维度」**，完整方案仍需某种期次级的维度集合冻结 |
| ~~**Q22**~~ | §3.6 标题 | ✅ **v4.4 关闭 —— PRD 自答「进 V1」**：PRD `8324a3f` 已把 §3.6 标题里的「待定功能」删掉（§0.10-D2）。**原问题存档**：**Goldie（E 模块）是否进 V1？** | E1 + E2 是本设计里唯一跨 Python 的部分（2 张表、2 个接口、~~2 份~~ **v4.4：1 份** prompt、异步重生成链路）—— **确定要做** | ~~**本设计保留完整方案并做成可整块摘除**（§1.3 / §0.9-12）。**请需求方明确 V1 是否包含**~~ → **v4.4 作废**：确定进 V1，全文「本节整体可摘除 / 待定期间隐藏 / 恒 null / 恒空数组 / 仅在需求方确认后才执行」等条件语**一律删除**，E1/E2 状态改 ✅。同版另有两项调整：**双 audience 取消 + 新增 Share 门槛**（§0.10-D3）、**Strengths 取消**（§0.10-D4） |
| ~~**Q23**~~ | 设计新增（v4.0） | ✅ **v4.4 关闭 —— 两条路同时打通**：① PRD `08b7a32` 的 `Reset` 按钮带来 **接口 28** `DELETE /erl/assessment/draft`（§0.10-D8），可直接丢弃草稿；② 需求方 2026-09-06 裁决把提交门槛降为**本维度终止**（§0.10-R1），「五维全部终止」的高门槛本身也消失了。**原问题存档**：**旧版本草稿的提交门槛变高了** | ~~V1 现在没有任何摆脱旧版本草稿的办法~~ → 缺口已补平（§11-67 / §11-82） | ~~建议**补一个丢弃草稿接口**……**这是 v4.0 唯一新增的功能性缺口**，请产品定~~ → **v4.4：已作为接口 28 纳入 V1**（Reset 按钮与本条共用），§12「不做丢弃在填草稿的接口」一条随之作废。**无需再答复** |

**v4.4 新增待确认（Q24 ~ Q25）—— 原均为 🟡 非阻塞项，两条已分别于 v4.8 / v4.9 关闭（Q24 的取值已于 **2026-09-08 反转为软删**，又于 **2026-09-09 改判为「删除 / 停用两个动作 + 有前置拦截」**，见下）。⚠️ **开发前仍有一条待答项：§13-Q21（已于 2026-09-08 重新打开）**：**

| # | 对应 PRD | 问题 | 影响 | 本设计取值 / 建议 |
|---|---|------|------|------|
| **Q24** | §3.8（动态维度，`0333162`） | ✅ **已关闭，但取值于 2026-09-09 被改判**（原关闭依据：需求方 2026-09-07 裁决，v4.8）：~~配置页是否要在 UI 上显式区分 `Delete` 与 `Retire`？是否允许物理删除「从未被任何期次绑定过」的维度？~~ | ~~结论落到数据模型：`status` 整列删除、物理删除~~ → **2026-09-08 反转**：`erl_dimension_config.status` **重新加回并落库**（`Active` / `Inactive`），**删除 = 软删**；配置页 UI 仍只留一个删除动作（不区分 Delete / Retire），只是落库语义从删行改为置 `Inactive`；历史**记录**仍可查，但历史**分数会漂移**（§13-Q21） | ~~取值：不区分，只有 `Delete`，且无条件允许**物理删除**~~ → **2026-09-08 反转为：UI 仍只有 `Delete` 一个动作（不区分 Delete / Retire），但落库是软删（`status = 'Inactive'`，行与 `weight` 保留、可恢复）；`ErlDimensionConfigStatusEnum` 改回**落库枚举**。仍不做「有历史数据禁止删除」的前置拦截 —— 但依据换成「软删下行不消失」**（不限于「从未被绑定过」的维度）。配置页垃圾桶 + 二次确认删掉一行、右上角 `Save` 后该维度即不在新配置版本里；历史安全**完全由 `~~erl_company_period_config~~（**2026-09-08 已删表**）` 的期次-版本绑定保证**（旧版本 item 行原样保留），**不需要软删这层**。`ErlDimensionConfigStatusEnum` 保留但降级为纯派生的展示态（§0.14 / §5.1.3 / §7.11-④）；仍**不做**「有历史数据禁止删除」这类前置拦截（§12）<br>⚠️ **本格上方从「配置页垃圾桶 + 二次确认删掉一行」起的整段是 v4.8 的原文存档，其中「期次-版本绑定」「不需要软删这层」「纯派生展示态」三处已分别于 2026-09-08 / 2026-09-09 作废，勿按它实现**。<br>**⇒ 2026-09-09 改判（需求方当日裁决，本格的当前取值）**：**配置页有两个破坏性动作**，由服务端按「该 `dimension_code` 是否出现在某个 `PUBLISHED` 题库版本的维度快照里」二选一下发（接口 23 的 `deletable`）—— ① **从未进入过** ⇒ **垃圾桶 = 删除**，落 `deleted = true`（行留、页面两处都不显示、**无恢复入口**）；② **进入过** ⇒ **删除被禁止**，图标改**电源按钮** = 停用（`status = 'Inactive'`，即上面那套软删，可从常显 `Deactivated Dimensions` 区块 `Activate`）。**「无条件允许删除」作废：前置拦截现在存在**，但① 判据是「**是否进入过已发布题库版本**」而**不是**「**有无历史数据**」（后者会连「有人填过、但题库从没发布过」的维度也拦住，而那种维度删掉是安全的）；② **保护对象不是那一行**（置位下行不消失），而是**已发布题库版本的语义** —— 已发布版本的维度快照与按 code 关联的历史，必须始终解得出那个维度。逐条见 **§0.21**（§5.1.3 / §6.4 / §7.11-④ / §8.4-C6 / §11-86 / §12 / §1.2 同步） |
| **Q25** | §3.8（题目字段）→ ~~回写 **M11**~~（已关闭） | ✅ **已关闭（需求方 2026-09-06 裁决，v4.9 补登）**：~~🟡 `criteria`（每题的单段判定标准）在 PRD 中已无任何依据，是保留为设计自创字段，还是从 Goldie 输入中移除？~~ **原问题存档**：PRD `273671a` 删掉「ERL Workbook 各 Stage/维度准入准则」后，`criteria` 失去最后一个 PRD 锚点；而 PRD §3.8 的题目字段只采集「题干 / Era Band / Source」，配置页**根本没有产生它的地方** | 三处影响均已落地：① Goldie 的判断依据收敛为**题干 + 逐题 Yes/No + 双端备注 + level 口径**，prompt 升 v1.1 并加「不得编造判定标准原文」的反向约束（§6.6）；② C2/C3 表单**取消**该输入框（§11-24c 已反转）；③ A5「How It's Scored?」弹窗**整块删除**（§8.4） | **取值：判定标准不进需求设计 —— 从 Goldie 输入中移除**（~~V1 保留该字段~~ **作废**）。`erl_question_config.criteria` 整列删除、接口 10 / 12 入参与接口 2 / 8 / 9 / 22 / 26 出参删除、A5 弹窗与 `ScoringCriteriaModal` 删除；**回写 M11 随之关闭 —— PRD §3.8 无需补该字段**。逐条见 **§0.15** |

> **本表之外还有一个待裁决项，已于 2026-09-09 关闭（v4.17，§0.22-Y3）**：**§0.17-K1** —— 「C7 该怎么处理『今天已不在维度配置里』的维度」。它**从未在本表里编号**（不是 PRD TBD、也不是本表的设计新增项），一直挂在 §0.17 / §5.1.3 / §7.11-④ / §9 / §11-90 五处「待裁决」注记上。需求方 2026-09-09 的裁决等于选了两个候选取值里的**「整条取消」**：C7 既不隐藏这类维度、也不再给它打 `Retired` 灰标，**C7 与「今天的维度配置」彻底解耦**。⇒ ~~**开发前仍开着的只剩两项**：🔴 **Q21**（权重 / 维度集合变更是否该改变历史期次的综合分）与 **§5.1.5 是否补 `weight` 列**。~~ → **2026-09-09 订正（v4.18）：只剩 Q21 一项。**「§5.1.5 是否补 `weight` 列」**从来就不是待裁决项** —— §5.1.5 已于 2026-09-08 定档排除出路 ①（补列与「权重不做任何快照」的裁决相左）、采用出路 ②（另造窄 Response）；**2026-09-09 实现按出路 ② 落地**。⚠️ 连带订正它的**前提描述**：本文档原写作「现状是接口 26 取 `erl_dimension_config` 的实时 `weight`、会随改权重漂移」—— **不成立**，现状是**压根不下发 `weight`**（接口 26 出参为 `{ dimensionCode, dimensionName, dimensionAbbr, questionVersionNo, sortOrder }`，§6.4 接口 26 / §5.1.5），因此既无漂移、也无消费方，**不需要任何裁决**。

---

## 附录 A：与 v2.1 的差异速查（供已读过 v2.1 的同学）

| v2.1 章节 | 变化 |
|-----------|------|
| §1.1 范围表 | A1 由「独立 Dashboard」改为「Company Overview 卡片」；~~删除 A4~~（v3.5 已复活，**v4.4** 再加双端 `Full View ›` 入口）；新增 A7（DI 下线）、C4（拖拽）、D 归入管理端；E1 由「规则合成三条洞察」改为「LLM 生成建议 ~~+ 双 audience~~」→ **v4.4 订正**：双 audience 已删，改为**单份输出 + Share 门槛**（§0.10-D3） |
| §2 现状事实 | 新增 §2.1「存量代码事实」（7 条，均带文件行号）；原型事实降级为参考并逐条标注是否被 PRD 采纳 |
| §3.2 决策表 | 新增 6 条决策（卡片入口、DI 开关、自动刷新、多次提交、手动维度分、附件链路）；修正 1 条（差距分析生成时机） |
| §4.2 权限表 | 新增 GSV Tab、基准两条线、D 模块的公司端拒绝；新增 PRD 内部张力的裁决说明 |
| §5 数据模型 | 表由 6 张增至 8 张（新增 ~~`erl_assessment_dimension`~~（**v4.4 已整表删除**，R1）、`erl_answer_attachment`；**v3.1 再增 `erl_reference_score_item`，共 9 张；v3.3 再增 `erl_question_config_version`，共 10 张**；~~v4.4：共 12 张~~ → **2026-09-08：共 11 张**，见附录 C）；`erl_assessment` 去唯一约束加 ~~`submission_seq`/`is_latest`~~（**2026-09-08 两列均已删除**）/~~`scoring_mode`~~（v4.0 已删）（**v4.4** 再加 `dimension` 并上提三列）；`erl_assessment_answer` 加 `note`；`erl_gap_analysis` 加 ~~`audience`~~（**v4.4 已删**，D3）/`stale`/`source_*`（**v4.4** 加 `shared`/`shared_at`/`shared_by`）；`erl_gap_analysis_item` 加 `ACTION` 类型与 `evidence_missing`（**v4.4** 删 `STRENGTH`，D4） |
| §6 接口契约 | 接口由 18 个增至 20 个（**v4.4：28 个**，见附录 C）；`/erl/overview` → `/erl/card`；~~删 `/erl/scoreDetails`~~（v3.5 已复活为接口 22）；新增 `/erl/question/reorder`、`/erl/assessment/{id}`、附件删除；F2 加排序筛选参数（**v4.4** 依据改标「本设计」，D15）；Python 接口加 note/criteria 输入~~与双 audience 输出~~（**v4.4 订正**：单份输出，D3；`criteria` 现标注为设计自创字段，D18 / §13-Q25）→ **2026-09-06 裁决整体删除**：`criteria` 入参撤除，Python 接口只吃 note + 题干 + Yes/No + level（v4.9，§0.15），新增附件入库接口 |
| §7 计算口径 | 维度分拆为 Founder（推导）/ GSV（手动）；新增 §7.2 计分策略、§7.4 状态摘要与软确认阈值、§7.6 Data Sources 推导；§7.5 生成时机由手动改为自动 |
| §7.3「三条洞察卡规则」 | **整节删除** —— 那是原型 mock 的反解规则，PRD 未要求；改由 LLM 产出 `actions[]`（含「为何相关」） |
| §8 前端 | 删除 Dashboard 与 scoreDetails 路由；新增 §8.5 职责划分、§8.6 DI 下线方案；F2 组件位置更正为 `portfolioCompanies/erl/`；交互表补 14 项 PRD 要求 |
| §9 降级 | 由 13 条增至 21 条 |
| §11 验证清单 | 由 20 项增至 40 项，按 PRD 章节分组（**v4.4：87 项**，新增 76 ~ 87 共 12 项，作废 26 / 29 两项；**v4.5：88 项**，新增 88 `is_latest`；**v4.6：89 项**，新增 89、作废 18b；**v4.10 / v4.11 增 90、v4.12 增 91（之前漏登）⇒ 共 91 项**；**2026-09-08：仍 91 项，但 11 / 20 / 47 / 49 / 72 / 77 / 86 / 87 / 88 / 90 / 91 十一项重写**，其中 **11 / 77 / 88 结论反转**） |
| §13 待确认 | 重编号并与 PRD §五 的 8 项对齐；关闭 v2.1 的 Q8（已确认）、Q1（PRD 已定义 A3）、Q9（已统一口径）；新增 Q2 / Q3b / Q4 / Q8 / Q10 |

> **v3.1 的增量不在此表** —— 该版只动基准模块 D（§5.6 / §5.6.1 / §6.5 / §7.8 / §8.1 / §8.4 / §9 / §11），逐条见 §0.3。
>
> **v3.2 的增量亦不在此表** —— 该版按 2026-08-28 PRD 修订只动 4 处：题库 Publish 发布态、F2 `View` 目标改为 Score Details 页（§6.8 / §8.4 / §9 / §11-32 / §13-Q12）、状态摘要三值降级为设计占位（§0.2-12 / §7.4 / §8.5 / §13-Q3）、打分格式表述依据减弱（§7.2，不改设计），逐条见 §0.4。
>
> **v3.4 的增量亦不在此表** —— 本版按需求方第二次裁决（「保留旧答案，以正在编辑的版本为准」）把 v3.3 的**重基整体删除、改为版本锁定**：删 `erl_assessment_answer.question_key`（唯一约束改回 `question_id`）、删接口 3 的 `rebase` 出参与接口 5 的版本一致性校验、删 `ErlAssessmentRebaseService`；§7.9-① 的「一律读最新已发布版本」订正为「一律读评估绑定版本」；§13-Q13 ~ Q16 四条边界全部关闭。逐条见 §0.6。
>
> **v3.5 的增量亦不在此表** —— 本版按需求方第三次裁决（「ERL Tab `View` 的落地页 = A4 全维 Score Details 页」，UI 依据 `/readiness/overall`）**复活 A4**：新增路由 `/exitReadiness/scoreDetails`（§8.1）与**接口 22** `GET /erl/scoreDetails`（§6.2.1，接口共 **22 个** —— v3.5 原文误写 21，v3.6 订正）；§8.4 补 10 行 A4 交互（含**与原型的四处有意偏离**）、§9 补 3 条 A4 降级、§11 补 6 项 A4 验证（57 ~ 62）；F2 `detailUrl` 改指 A4（§6.8）；§13-Q12 关闭；**Q17**（公司端入口）当日提出并当日确认为「V1 不加」—— ⚠️ **v4.4 订正：该结论已被 PRD `57225d2` 推翻，两端均加 `Full View ›` 入口**（§0.10-D5 / §13-Q17）。逐条见 §0.7。
>
> **v3.6 的增量亦不在此表** —— 本版补上 PRD 当日 **10:24 第二次提交**（`4442613`）漏消化的一条需求：**Founder 端也要填每维手动整体分并弹软确认**，据此把手动分由「仅 GSV」改为**双端**、展示口径统一为手动分、`derived_score` 退为软确认与审计专用、软确认文案改用 PRD 原文，并**关闭 §13-Q3b**（口径不对称问题被 PRD 自身解决）；另订正 6 处内部不一致（接口数 21→22、配置页编辑路由 `:id`→`:questionKey`、接口 4 补 `attachments`、接口 7 的 `dimension` 口径定档、旧草稿换题集路径定档、状态摘要短路顺序）与 5 项留白定档（`erl.enabled` 偏离写明、`fund` 双端、`+ New` 锚点、A4 页头补综合分与 Stage、来源标签 `Founder / CFO` 经裁决保持不变并反向回写 PRD）。逐条见 §0.8。**v3.6 同时产出过一份独立的 PRD 回写报告**（`需求审核/requirement-review.md`），其内容已随 PRD 后续修订失效并**于 2026-09-06 删除**，现行回写清单统一见 §0.10-④。
>
> **v3.3 的增量亦不在此表** —— 该版按需求方对 §13-Q11 的裁决把题库改为**版本化**：表由 9 张增至 **10 张**（新增 `erl_question_config_version`，§5.1.1），`erl_question_config` 删 `publish_status` / `published_at` / `enabled` 三列、加 `version_id` / `question_key`，`erl_assessment` 加 `erl_question_config_version_id`，`erl_assessment_answer` 加 `question_key`；C 模块写接口由 `id` 改按 `questionKey` 定位；新增在填评估的**重基**机制。逐条见 §0.5。

---

## 附录 B：v3.6 → v4.0 差异速查（**供已读过 v3.6 的同学，先读这张表**）

| 主题 | v3.6 | **v4.0** | 章节 |
|------|------|----------|------|
| **打分格式** | 每题 1–9 分（`SCORE`）或 Yes/No（`YES_NO`）双题型；计分策略可切换 | **全部题恒 Yes/No**；**逐级解锁**：本 level 全 Yes → 折叠打勾 → 解锁下一 level；出现 No 即终止 | §7.2 |
| **维度分** | **手动填写**的 `manual_score`（1–9 一位小数），题均分作软确认参照 | **最后一个全 Yes 的 level**（**0–9 整数**）；**无任何手动录入** | §7.1 / §5.3 |
| **软确认弹窗** | 双端都有（v3.6 刚补） | **整体删除** | §7.4 |
| **综合分** | 五维**简单平均** | **Σ(维度分 × 权重%)**，权重可配、合计 100% | §7.1 / §5.1.2 |
| **状态摘要 / Data Sources** | 均在 V1（状态摘要为设计占位） | **两块均删除** | §7.4 / §7.6 |
| **公司端可见范围** | 可见 GSV 维度分、Perception Gap、雷达图（2 条线） | **三者均不可见**（服务端不下发） | §4.2 / §4.3 |
| **雷达图** | ERL Card 内，两端均渲染 | **仅组合端渲染** | §8.4 |
| **DI 卡片** | 新增 `erl.enabled` 开关**隐藏** DI | **不隐藏**，由右列移到**左列 FI 之下**（v4.3 订正：布局是两列，不是单列纵排）；**开关删除** | §8.6 |
| **题库作用域** | 全局单份 | **按组织（`organization_id`）** | §5.1.1 / §7.9 |
| **附件** | 题级、无上限 | 题级（Founder）+ ~~**维度级（GSV）**~~；**≤10MB/个** —— **v4.6：维度级取消，双端统一题级**（§0.12） | §5.5 / §6.7 |
| **每题评分标准** | 三段（Founder / Harvest / Exit） | ~~**单段**~~ → ❌ **2026-09-06 裁决整体删除**（单列 `criteria` 与 A5 弹窗一并撤除，v4.9） | §5.1 / §0.15 |
| **逐题标签** | `Founder Era` | **`Founder Era - 1`**（含 level） | §6.2 |
| **表数量** | 10 张 | **11 张**（+ `erl_dimension_weight`）；`erl_answer_attachment` **改名** `erl_assessment_attachment`（**v4.6 已改回原名**）—— ~~v4.4：12 张~~ → **2026-09-08：11 张**（再删 `erl_dimension_config_version` / `erl_company_period_config`，再增 `erl_question_config_dimension_version`） | §5 |
| **接口数量** | 22 个 | **24 个**（+ `GET`/`PUT /erl/weight`）—— v4.1 增 #25 `GET /erl/question/version`；v4.2 再增 #26 `GET /erl/question/version/{versionNo}`，共 26 个；**v4.4 再增 #27 share、#28 discard draft，现共 28 个** | §6.4 |
| **Goldie（E 模块）** | 在 V1 | ~~⚠️ **PRD 标「待定功能」**，方案保留、可整块摘除~~ → ✅ **v4.4 作废**：PRD `8324a3f` 已撤销「待定功能」标题，**确定进 V1**（§0.10-D2 / §13-Q22 关闭）；同版双 audience 取消、Strengths 取消、新增 Share 门槛 | §1.3 / §13-Q22 |
| **PRD 冲突状态** | 与 PRD §3.8「变更立即生效」冲突（靠裁决压过） | ✅ **该冲突已由 PRD 回写解决**；新增 6 条待回写（M1 ~ M6）—— **v4.4：待回写增至 12 条（M1 ~ M12）**；**v4.6 增 M13**（附件题级，§0.12-A7）；**v4.9：M11 关闭**（`criteria` 整体删除，PRD §3.8 无需补该字段），现为 **M1 ~ M10 + M12 + M13** | §0.9-④ / §0.10-④ / §0.15 |

> **删除清单（14 项，逐一检索确认无残留）**：`answer_type`、`score` 列、`scoring_mode`、`manual_score`、`derived_score`、`divergence_ack`/`divergence_delta`、`criteria_founder`/`_harvest`/`_exit`、`ErlScoringStrategy` 系列、`ErlScoringModeEnum`、`ErlAnswerTypeEnum`、`ErlDimensionStatusEnum`、`erl.enabled`、`dataSources` 出参、~~`erl_answer_attachment`（旧表名）~~（**v4.6 撤销该项**：表名已改回）。**v4.9 实质补入两项**：**单列 `criteria`**（实体列 / DTO / 请求 VO / 版本 diff 比对项 / 建表脚本 / prompt 正文）与 **`ScoringCriteriaModal`**（组件 + 三处调用点 + `.criteriaLink` 样式）—— 判定标准不进需求设计（§0.15），故清单实际为 **15 项**。见 §11-69。**v4.4 另有一份 8 项的删除清单**（`ErlDimensionEnum` / `erl_dimension_weight` / `erl_assessment_dimension` / `audience` / `STRENGTH` / 静态 `DIMENSIONS` / 两份分端 prompt / 附件表 `dimension` 列），见 §11-87。
>
> ~~**五个必须先答的问题**：**Q19**（解锁按维度独立还是全局同步 —— 影响最大）、**Q20**（公司端能否看 Perception Gap）、**Q21**（改权重是否该改历史综合分）、**Q22**（Goldie 是否进 V1）、**Q23**（旧草稿如何摆脱）。见 §13。~~
>
> → ~~✅ v4.4：五条全部关闭，开发前不再有阻塞性待答项。~~ → **2026-09-08 订正：四条关闭，Q21 重新打开**（权重不做快照、接受历史漂移）。 关闭依据：**Q19** 与 **Q21** 由需求方 2026-09-06 裁决关闭（维度级提交 R1 / 配置版本化 R2）；**Q20** 与 **Q22** 由 PRD 自答关闭（§3.5「创始人只能查看自己的分数」/ `8324a3f` 撤销「待定功能」）；**Q23** 由接口 28（`Reset`）+ 单维终止门槛关闭。同批关闭的还有 **Q6**（PRD `273671a` 删掉备选方案整段），**Q17** 则被 PRD `57225d2` **推翻**（公司端必须有 A4 入口）。
>
> **v4.4 新增两条 🟡 非阻塞项**：**Q24**（配置页是否显式区分 Delete / Retire；能否物理删除 —— ~~**已于 v4.8 ✅ 关闭：不区分，只有 `Delete`，无条件物理删除**~~ → **2026-09-08 反转为软删** → **2026-09-09 改判：配置页确实显式区分两个动作（垃圾桶=删 / 电源按钮=停用），删除有前置拦截，判据是「是否进入过已发布题库版本」**，见 §13-Q24 / §0.21）、**Q25**（`criteria` 在 PRD 中已无依据，保留为设计自创字段还是从 Goldie 输入移除 —— ~~V1 保留并标注，列入回写 M11~~ → **已于 v4.9 ✅ 关闭：从 Goldie 输入中移除，字段与 A5 弹窗整体删除，M11 一并关闭**）。~~两条现均已定案，开发前不再有待答项。~~ → **2026-09-08**：Q24 的取值已反转为软删；**Q21 重新打开**，开发前仍有一条待答项。见 §13 / §0.14 / §0.15。

---

## 附录 C：v4.3 → v4.4 差异速查（**供已读过 v4.3 的同学，先读这张表**）

> 本版消化 **PRD 基线 `6d8c800` → `49d9a29`** 的 9 次提交（`57225d2` / `8f2fcc0` / `9a203ce` / `0333162` / `08b7a32` / `8324a3f` / `4f959bb` / `273671a` / `49d9a29`）、**需求方 2026-09-06 的三条裁决（R1 ~ R3）**，以及 **2026-09-06 的 ERL Card 原型截图**。
> 三条裁决是本版的骨架改动（提交粒度、配置版本化、缺省期次），其余 D1 ~ D22 为 PRD 消化项。

### C.1 三条裁决（R 类，改动面最大）

| # | 变了什么 | 依据 | 影响章节 |
|---|---------|------|---------|
| **R1** | **提交粒度 = 维度级**：一次提交由「整卷含五维」变为「**单个维度**」。`erl_assessment` 加 `dimension` 列并上提 `level_score` / `terminated_level` / `unlocked_level` 三列；**`erl_assessment_dimension` 整表删除**；所有唯一约束 / 部分唯一索引补 `dimension`；提交前置校验由「五维全终止」改为「**本维度终止**」；`erl_question_config_version_id` 绑定粒度变为**每维一份**（同期次各维可跨版本，不阻止不告警） | 需求方 2026-09-06 裁决 | §5.2 / §5.3 / §6.3 / §7.2 / §7.9-⑤ / §8.4 / §10.1 / §11-20 / -21b / -53 / -67 / -76 / §13-Q19 |
| **R2** | ~~**维度只停用不硬删**~~（**v4.8 作废，改物理删除**）**+ 维度集合与权重整体版本化**：维度由编译期枚举改为**租户级可版本化配置数据**；新增 3 张表；**每个期次在首次创建评估（含草稿）时绑定当时的配置版本、此后永不跟随** ⇒ 历史期次的维度集合 / 排序 / 权重 / 综合分 / Stage / 雷达图形状**永不漂移**；~~「删除维度」= **Retire（软删）**~~ → **v4.8 订正：物理删除**（`status` 列删除，历史安全全靠期次-版本绑定，§0.14），**不做**「有历史数据禁止删除」的前置拦截 | 需求方 2026-09-06 裁决 | §5.1.2（重写）/ §5.x 新增三表 / §7.1 / §7.10-W1 / §10.1 / §11-77 / §12 / §13-Q21 关闭、Q24 新增 |
| **R3** | **展示期次缺省 = closed month 所在季度**：接口 1 / 17 / 20 / 22 等所有「`period` 可选」的读接口，缺省值由 ~~最新已提交期次~~ 改为**该公司 closed month 所在季度**（复用 **FI 域既有服务**推导，ERL 不自己算）；**该季度两端均无提交 → 空态，明确不回退**到更早期次；closed month 取不到 → 同样空态 + WARN | 需求方 2026-09-06 裁决 | §3（新增跨域依赖）/ §6.1 / §6.7 / §9（降级逻辑改写）/ §10.1（`ErlPeriodService`）/ §11-42 / -78 |

### C.2 PRD 需求冲突与新增（D1 ~ D14）

| # | 变了什么 | 依据 | 影响章节 |
|---|---------|------|---------|
| **D1** | **动态维度**：配置页第二 Tab 可**新增 / 删除 / 排序 / 改权重**，维度列表写作 `FRL / PRL / BERL / RRL / TRL...`（省略号＝不固定五个）。全文「五维」硬假设一律**参数化**：删 `ErlDimensionEnum`、删 web 静态 `DIMENSIONS`（改接口驱动）；F2 出参改 `dimensionScores: [{code, abbr, score}]`；雷达图顶点、A3 chip、A4 卡、C7 快照卡、Gap 状态点数量全部按接口返回渲染 | PRD §3.8（`0333162`） | 全文；重点 §5.1.2 / §6.8 / §7.1 / §8.4 / §10.1 / §10.3 / §11-5 / -32 / -35 / -39 / -58 / -86 |
| **D2** | **Goldie（E 模块）回归 V1**：PRD §3.6 标题删「待定功能」。全文「可整块摘除 / 待定期间隐藏 / 恒 null / 恒空数组 / 仅在需求方确认后才执行」条件语**一律删除**，E1/E2 状态改 ✅ | PRD `8324a3f` | §1.1 / §1.3 / §11 差距分析组组头 / §11-2 / §12 / 结论表 / §13-Q22 关闭 |
| **D3** | **Share 模型取代双 audience**：`erl_gap_analysis` **删 `audience`**（唯一约束回 `(company_id, period)`）、**加 `shared` / `shared_at` / `shared_by`**；两份 prompt 合并为一份；**新增接口 27** `POST /erl/gapAnalysis/share`（仅管理端）；**激活门槛** = 每个维度两端都有 `SUBMITTED`（**2026-09-08**：`is_latest` 已删，改按 `submitted_at DESC, id DESC` 判存在）；`shared = false` 时公司端接口 17 返回空态；**新边界定档：重生成后 `shared` 复位为 `false`** | PRD §3.6（`8324a3f` + `49d9a29`）+ 本版补边界 | §4.2 / §4.3 / §5.7 / §6.6 / §7.5 / §8.4 / §10.1 / §10.2 / §11-26 作废 / §11-80 |
| **D4** | **Gap 区块 UI 定档**：标题 `Gap Analysis & Suggested Actions` + `AI GENERATED`；两个按钮 `View details`（按维度分区弹框）/ `Share to founder`（未达门槛置灰）；期次 chip + 计数文案；每维小卡**三态由两条独立信息组合**（圆点＝双方是否都已提交，文字＝有无 gap）；接口 17 出参补 `dimensions[]`；**`STRENGTH` 枚举值、`strengths[]` 出参、prompt「承认为优势」段一并删除** | 2026-09-06 ERL Card 原型截图 | §5.8 / §6.6 / §8.4 / §10.2 / §10.3 / §11-29 作废 / §11-81 |
| **D5** | **A4 双端入口 + 维度卡按钮**：**推翻 §13-Q17** —— ERL Card 右上角 `Full View ›` 是 A4 入口，**两端都有**（原型为准，PRD §3.5 的「仅 Company portal」列入回写 M9）；**A4 每张维度卡卡头加 `Add New` / `View History`**，原页级 `+ New` / `View history` 取消；组合端 A4 同时呈现 GSV 与 Founder，公司端只有 Founder 侧 | PRD §3.5 + §3.7（`57225d2`）+ 原型 | §4.2 / §8.1.1 / §8.4 / §10.3 / §11-57 / -60 / -79 / §12（禁令撤销）/ §13-Q17 推翻 |
| **D6** | closed month 期次口径 → **并入 R3** | — | 见 R3 |
| **D7** | **基准入口 = 雷达图下方链接**：ERL Card 雷达图**正下方**加 `Benchmarkit & Top GSV Quartile ›` → `/exitReadiness/benchmark?companyId=`，**仅管理端**。⚠️ 顺带修既有文档缺口：§8.1.1 声称入口在 A3/A4 页内，但交互表里两处都没定义过该链接，按现文档基准页站内不可达 | PRD §3.5（`9a203ce`） | §8.1.1（订正）/ §8.4 / §10.3 / §11-79 |
| **D8** | **Founder Flow 按钮组定档** `Save as draft` / `Cancel` / `Reset` / `Submit`：`Save as draft` = 手动 flush（~~与 1.5s 去抖自动保存**并存**~~ → **v4.30 作废：自动保存取消，接口 4 只由 `Save as draft` / `Submit` 触发**）；`Cancel` 只离开页面；**`Reset` 需要新接口 28** `DELETE /erl/assessment/draft`（清空答案与附件、`unlocked_level` 回 1；~~必须二次确认并写明附件一并删除~~ → **v4.29 作废**） | PRD §3.3（`08b7a32`） | §6.3 / §8.4 / §10.1 / §10.3 / §11-82 / §12（「不做丢弃草稿接口」作废）/ §13-Q23 关闭 |
| **D9** | **草稿语义显式化**：草稿**公司共享、不区分账户、新草稿直接覆盖**（A 存 B 看到 A 的、B 存直接覆盖）；进入草稿显示**上次保存时间与保存人** → 接口 3 出参补 `lastSavedAt` / `lastSavedBy`（取 `updated_at` / `updated_by` join 用户表，**不新增快照列**）；提交人仍以**点提交的那个人**为准 | PRD §3.3（`08b7a32`） | §5.2 / §6.3 / §7.9-④ / §8.4 |
| **D10** | **题库更新提示**：接口 3 出参补 `latestPublishedVersionNo` / `hasNewerQuestionSet`；~~填报页顶部挂**非阻断、可关闭、无操作按钮**的 banner~~ → **2026-09-15 需求方圈图作废，改为强阻断二选一弹窗**（`Submit draft content` / `Access new question library`，v4.41 回写，见 §8.4）。版本锁定本体不变，**冲突只在设计现文「填报页无任何提示、无任何变化」这一句** | PRD §3.3（`4f959bb`） | §6.3 / §7.10-N1 / N3 / §8.4 / §9（订正）/ §11-83 |
| **D11** | **重复提交确认文案分支**：`submissionCount > 0` 时改用 PRD 原话「**已提交该季度评价，是否再次提交？**」+「本次提交将成为该季度的 source of truth，历史提交保留」 | PRD §3.3（`08b7a32`） | §8.4 / §11-22 / §11-84 |
| **D12** | **Assessment History 字段调整**：**加 `Submitted` 列**；**删 `Completion` 列**（次级标注 `v{n}` / `stopped at L{t}` 挪到**分数列下方**，`answeredCount` / `totalCount` 降为页头用途，§7.1.1 分母口径论证**保留**）；`Portal` 列**仅管理端**；分数列改为**该维 Overall Score**（含 Stage 徽章，**不是**加权综合分）；**接口 8 补可选 `dimension` 入参** | PRD §3.9（`8f2fcc0`） | §6.4 / §7.1.1 / §8.4 / §11-8 / -14 / -53 / -73 / -85 |
| **D13** | **配置页第二 Tab 改名扩权**：~~`Dimension Weights`~~ → **`Dimension Configuration`**；**接口 23/24** 语义扩为 `GET` / `PUT /erl/dimension/config`（整组保存；**2026-09-08**：~~生成新配置版本~~ → 就地替换、不产生版本）；**Save 双条件**（脏态 + 合计 100%），越界提示 `Exceeds 100% by {n}%` / `Needs {n}% more`；Save 确认框文案 ~~「…历史分数不变」~~ → **2026-09-08 反转为「新配置立即全局生效，已有期次的综合分、Stage 与雷达图形状会随之变化」**；该 Tab 的改动**不激活 Publish**，走自己的 Save | PRD §3.8（`0333162`）+ R2 | §2.3.1-⑤（原型过期注记）/ §6.7 / §7.9-③ / §8.4 / §10.1 / §10.3 / §11-11a / -24b / -86 |
| **D14** | **`Overall Score` 命名定档**：英文 UI 文案统一为 `Overall Score`，全文不再出现 `Composite Score` | PRD §3.1（`57225d2`） | §0.9-2（订正）/ §7.1 / §8.4 / §11-2 / -57 |

### C.3 PRD 删除依据的处置（D15 ~ D22 —— 功能保留，改依据来源）

> 沿用 §0.9-② 的体例：**「PRD 删掉依据 ≠ 自动删掉功能」**，逐条判定并改标来源，不得沉默处理。

| # | 变了什么 | 依据 | 影响章节 |
|---|---------|------|---------|
| **D15** | **F2 排序筛选功能保留**，4 处以上直接引用「PRD §3.7」的依据全部改标「**本设计（PRD 2026-09-03 已删除该条依据）**」（⚠️ **v4.19 在界面层面整条推翻**：筛选器与列头排序器一并按原型撤下，服务端能力保留，§0.23-P2） | PRD §3.7 已删该条 | §1.1 / §6.8 / §8.2 / §8.4 / §11-33 |
| **D16** | **Completion**：列删除、次级标注挪位、§7.1.1 论证保留 → 并入 **D12** | PRD §3.9 | 见 D12 |
| **D17** | **A3 面包屑功能保留**，依据列由「§3.1 / §4」改为「**§4**（§3.1 的 UX 要点已于 2026-09-03 删除）」；PRD 自身矛盾列入回写 **M6** | PRD §3.1 已删 UX 要点、§四 仍保留 | §8.4 / §0.10-④ |
| **D18** | ~~**`criteria` 保留但改标**~~：PRD 删掉「ERL Workbook 各 Stage/维度准入准则」后该字段**失去最后一个 PRD 锚点**（它本就不在 §3.8 的题目字段里）→ 标注「**设计自创、题库中无此字段、待需求方确认**」，删除所有「即 PRD §3.6 的 Workbook 准入准则」这类引用；列入回写 **M11** → **§13-Q25** —— → **2026-09-06 裁决整体删除**：字段、A5 弹窗与 Goldie 入参一并撤除，Q25 与 M11 双双关闭（v4.9，§0.15） | PRD §3.6 删除段落 | §5.1 / §6.6 / §10.2（prompt）/ §11-24c / §13-Q25 / §0.15 |
| **D19** | **「自动刷新分析」保留为实现手段**，依据改标「**本设计**」；并补 D3 定的新边界（重生成 ⇒ `shared` 复位） | PRD 已删该条 | §7.5 / §11-25 |
| **D20** | **`actions[{title, why}]` 的 `why` 保留**为设计选择；「**不做跟踪 / 指派 / Deadline**」结论**保留**，理由由「PRD §3.6 明确 MVP 不含」改为「**PRD 未要求**」 | PRD 已删整段 | §6.6 / §11-27 / §12 |
| **D21** | 「**GSV vs Founder 对比 Tab**」「**Fireflies / SharePoint 扩展**」结论**均不变**（本就不做），依据改标「**PRD 未要求**」；**§13-Q6 关闭**（①对比 Tab：PRD 已删该备选；②gap 粒度：PRD「分为五个维度」＝按维度，与本设计一致） | PRD `273671a` 删「已知 TBD 与 MVP 备选方案」整段 | §12 / §13-Q6 |
| **D22** | §2.3 对「分数约 6 表示进入该纪元、可开始接触投行」的引用订正为「（**PRD 2026-09-03 已删除该注解**）」 | PRD 已删该注解 | §2.3 |

### C.4 数据模型与接口的净变化

| 维度 | v4.3 | **v4.4** |
|------|------|----------|
| **表数量** | 11 张 | ~~**12 张**~~ → **2026-09-08：11 张** —— v4.4 v4.4 删 2（`erl_dimension_weight`、`erl_assessment_dimension`）、增 3；**2026-09-08 再删 2**（`erl_dimension_config_version`、`erl_company_period_config`）**再增 1**（`erl_question_config_dimension_version`）⇒ 11 张（`~~erl_dimension_config_version~~（**2026-09-08 已删表**）`、`erl_dimension_config`、`~~erl_company_period_config~~（**2026-09-08 已删表**）`） |
| **接口数量** | 26 个 | **28 个** —— 接口 23/24 语义扩为维度配置整组读写；新增 **#27** `POST /erl/gapAnalysis/share`、**#28** `DELETE /erl/assessment/draft` |
| **待确认项** | Q19 ~ Q23 五条阻塞 | 全部关闭（连同 Q6）；Q17 被 PRD 推翻；Q24 / Q25 已分别于 v4.8 / v4.9 关闭 —— ⚠️ **2026-09-08：Q21 重新打开**（权重不快照、接受历史漂移），**开发前仍有一条待答项** |
| **待回写 PRD** | M1 ~ M6 | **M1 ~ M12**（新增 M7 ~ M12：来源标签、打分格式与维度级提交矛盾、Full View 端限定、§3.1 卡片清单、~~`criteria` 无处产生~~、维度删除对历史的影响）—— **v4.9：M11 关闭**（`criteria` 整体删除，PRD §3.8 无需补该字段），实际待回写为 **M1 ~ M10 + M12 + M13**（M13 见 §0.12-A7） |
| **验证清单** | 75 项 | **87 项**（新增 76 ~ 87；作废 26「两端口吻不同」与 29「承认为优势」两项） |
| **v4.4 删除清单（8 项）** | — | `ErlDimensionEnum`、`erl_dimension_weight`、`erl_assessment_dimension`、`erl_gap_analysis.audience`（含 `ErlAudienceEnum`）、`STRENGTH` / `strengths[]`、web 静态 `DIMENSIONS`、两份分端 prompt、附件表的 `dimension` 列（**v4.6：表现名 `erl_answer_attachment`**）。逐一检索确认无残留，见 **§11-87** |
