# 需求文档：Exit Readiness（退出准备度，ERL）

## 一、背景与目标

Exit Readiness（ERL）是 Looking Glass 平台中用于评估投资组合公司「退出准备度」的一整套功能。它替代原有的 Development Intelligence（DI）板块，通过创始人（Founder）与 GSV 团队各自独立完成的季度评估，从 5 个维度对公司当前阶段进行打分，识别双方感知差距（Perception Gap），并在 Goldie（AI）的辅助下生成差距分析与行动建议，最终帮助 GS 团队与被投公司共同推进退出准备。

**5 个 ERL 维度**：
- FRL：财务准备度（Financial Readiness）
- PRL：产品准备度（Product Readiness）
- BERL：品牌资产准备度（Brand Equity Readiness）
- RRL：风险准备度（Risk Readiness）
- TRL：人才准备度（Talent Readiness）

**9 级阶段（分三个纪元/Era）**：
- Founder Era：Stage 1–3
- Harvest & Growth Era：Stage 4–6（分数约 6 表示公司进入该纪元，可开始接触投行）
- Exit Era：Stage 7–9

---

## 二、业务闭环流程

1. 管理员在 **ERL Configuration** 中维护 5 个维度的题库、纪元归属、来源标签、问题类型、打分标准及必答顺序。
2. 创始人在 **Founder Flow** 中独立完成季度自评；GSV 团队在 **GSV Flow** 中独立完成同题库的评估。
3. 每次提交生成一条带时间戳的只读记录（同一季度允许多次提交，最新一次为 source of truth）。
4. 双方分数计算生成 **ERL Scorecard 与 Radar Chart**：包含各维度分数、综合分数、当前 Stage、Perception Gap。
5. Goldie 基于分差、笔记证据与题库标准，产出 **Gap Analysis & Suggested Actions**。
6. 结果汇总到 Company Overview 的 **ERL Card** 与投资组合级的 **Portfolio ERL Dashboard**，PM 可从组合层进入具体公司。
7. 通过 **Assessment History** 追溯历史提交

---

## 三、功能需求

### 1. ERL Card 与公司概览导航（Company Overview）

**决策**：采用原型中Example 2单卡片方案。

**功能描述**：

- 系统级隐藏 Company Overview 页原有的 DI 卡片（使用现有 setting/toggle 能力，不删除数据）；DI 数据、KPA 评估、SDP 打分完整保留但不再展示。
- 原 DI 卡片位置由新的 ERL 卡片替代，卡片直接展示完整聚合评分内容：
  - 综合分数（Composite Score）: 五个维度的平均分
  - 当前 Stage
  - Gap Analysis & Suggested Actions 摘要（TBD）
  - 5 个 ERL 维度列表（含各维度分数：新增时手动填写的、Perception Gap：Founder和GSV分数差）
  - BPMM（TBD）
  - 5 维度雷达图
- **不设独立 Exit Readiness 落地页**；ERL 卡片是唯一入口。
- 卡片内提供每个维度的「View Details」入口，直接跳转到该维度的 Score Details 页。
- ERL 卡片及后续页面对当前可访问 Company Overview 的角色开放（具体权限子集待确认）。

**UX 要点**：

- 从维度页返回时保留面包屑：Exit Readiness ›〔Dimension Name〕。

---

### 2. 维度详情页（Dimension Detail Page，模板）

**功能描述**：
- 为 5 个维度（FRL / PRL / BERL / RRL / TRL）提供**同一套模板**，通过 dimension 参数驱动，避免重复维护。
- 页面为「View Details」进入后的题级详情视图，展示：
  - 维度名称（如 "Financial Readiness (FRL)"）
  - 该维度题目总数
  - 该维度综合分数
  - **Founder / GSV Tab 切换**（公司用户不显示 GSV Tab）
  - 元数据栏：Period、Submitted By、Role、Submitted At
  - 该维度全部题目列表，每题显示 Era 标签（如 "Founder Era"）与分数
- **「View history」入口**：跳转到 Assessment History 页（限定当前维度）。
- **「+ New」入口**：发起该维度新一轮评估（分别进入 Founder Flow 或 GSV Flow）。
- 权限规则：
  - 创始人只能看到自己的数据，且不显示 GSV 专属字段（Benchmarkit、Top GSV Quartile 等）。
  - GSV 团队可看到 GSV 专属字段。
- 全端响应式（桌面 + 移动）。

---

### 3. ERL 评估表 — 创始人流程（Founder Flow）

**功能描述**：
- 面向 **Company User / Company Admin** 角色，在 Assessments 区块内访问。
- 表单顶部提供**评估期选择器**（如 "Q3 2026"）
- 题库来源于 ERL Configuration，按 5 个维度组织；每个维度内按 3 个 Era 分组：
  - Founder Era（Stage 1–3）
  - Harvest & Growth Era（Stage 4–6）
  - Exit Era（Stage 7–9）
- **打分格式（当前占位 + TBD）**：
  - 现阶段：每题 1–9 分，映射至 Stage/Era。
  - 后续极可能改为：Yes/No + 固定必答顺序；某题回答 "No" 后，该维度后续题目不再计入分数。
  - 开发时以占位形式实现，保证未来切换到 Yes/No + 固定顺序不用重构。
- 每题字段：
  - 打分输入
  - 可选「证据/备注（Evidence/Notes）」文本
  - 可选文件/图片上传（同步写入公司 Memory File，供 Goldie 后续分析）
  - 每题显示来源标签（Founder/CTO、Looking Glass、SharePoint 等）
- 创始人**独立**完成，全程不可看到 GSV 分数。
- 支持保存进度、稍后继续，无数据丢失。
- 需为每个维度**手动填写一个整体维度分**。若该手动分与题目答案推导出的结果**不一致**，弹出软确认弹窗提示分歧"Your score doesn't match the questionnaire answers, please confirm this is intentional" ；仅需确认，不阻止提交。
- **提交后即只读**，如需修改必须新建一次提交。
- 同一季度允许多次提交，最新一次为 source of truth。
- 每次提交生成带日期的记录（提交日期、评估人、基金/组合）。
- 历史记录进入 Assessment History。
- 仅限公司用户在其自身 portal 内完成，portfolio admin 不能代填。
- 全端响应式。

**UX 要点**：
- 30+ 题目，需使用可折叠的 Era 分组，避免长度令用户不堪重负。
- 每个 section 顶部显示打分标度图例（1–3 / 4–6 / 7–9 → Era）。
- 若切换至 Yes/No 模式，需清晰提示「No 会中止该维度后续计分」。
- 证据/备注字段视觉从属于打分输入，不应看起来是必填。
- 文件上传使用轻量小图标（靠近备注），不喧宾夺主。
- 自动保存无感。
- 提交确认要明确告知已锁定为只读、下一步（GSV 独立评估 → 对比出现）。

---

### 4. ERL 评估表 — GSV 团队流程（GSV Flow）

**功能描述**：
- 面向 **Portfolio Manager / Portfolio Group Manager**，在 Assessments 区块内、按 portfolio 公司访问。
- 使用与 Founder Flow **相同**的题库、Era 分组、打分标度（同样受 Yes/No + 固定顺序 TBD 影响）。
- 每题字段：
  - 打分输入
  - **来源标签**（Looking Glass、SharePoint、GSV Assessment、Board Transcripts / Fireflies 等）
  - 可选「证据/备注」文本
  - 可选文件/图片上传（同步写入 Memory File）
- 表单顶部提供**评估期选择器**（如 "Q3 2026"）。
- GSV 需为每个维度**手动填写一个整体维度分**。若该手动分与题目答案推导出的结果**不一致**，弹出软确认弹窗提示分歧"Your score doesn't match the questionnaire answers, please confirm this is intentional" ；仅需确认，不阻止提交。
- 保存进度、可恢复。
- 提交后只读；同一季度可多次提交，最新为 source of truth。
- 每次提交生成带元数据的记录，进入 Assessment History。
- Portfolio admin 可为其权限范围内任意公司完成/更新 GSV 评估。
- 全端响应式。

---

### 5. ERL Scorecard 与 Radar Chart

**功能描述（评分与计算）**：
- 每个维度分数：由该维度内各题分数计算得出（**具体计算方法**：初步为各题平均，最终待开发前确认）。
- **综合 ERL 分数** = 5 个维度分数的简单平均，以 X/9 形式显示。
- **当前 Stage（1–9）**：由综合分数与 Workbook 中的 Era 边界推导。
- **Perception Gap**（每维度）= Founder 分 − GSV 分；正值 = 创始人自评更高，负值 = GSV 更高。
- 打分规则为进行中工作项，未定前使用占位并逐步迭代。

**功能描述（雷达图）**：
- 雷达/蛛网图在同一张图上呈现**四条线**：
  1. Founder 自评
  2. GSV 评估
  3. Benchmarkit 外部对标
  4. Top GSV Quartile
- Founder 与 GSV 线来自评估提交；Benchmarkit 与 Top GSV Quartile **为外部静态数据输入**，不由 Looking Glass 计算得出，需单独数据接入。
- 图形规范：**仅线条无填充**（与 Workbook 一致）、每线不同色、有图例、中心轴隐藏。
- 5 个顶点分别对应 5 个 ERL 维度，明确标注。
- 交互：悬停数据点显示该维度、该 perspective 的精确分数。
- 架构上支持 MVP 展示 4 条线，同时预留后续新增 perspective 的能力。

**功能描述（Scorecard 展示）**：
- 展示项：
  - 综合 ERL 分数
  - 当前 Stage 与 Era
  - 每维度 Founder 分与 GSV 分
  - 每维度 Perception Gap
  - 每维度状态摘要（基于 gap 幅度推导）
- **Strengths & Priority Gaps**：由评估中填写的证据/备注推导；如无笔记，标注为「未提供备注」。
- **Data Sources & Cadence**（按维度）：显示主要与补充证据来源，以及评估频率（季度）。
- **BPMM 分数**：仅作为参考数字（1–5）显示；完整 BPMM 评估交互**不在本 story 范围内**。
- 权限：
  - 创始人（公司 portal）：并列查看自己的分数与 GSV 分数。
  - GSV 团队（portfolio admin）：相同视图 + admin 专属信息。
- 从 Scorecard 可访问历史评估记录，回看往期。
- 全端响应式。

---

### 6. Gap Analysis 与 Suggested Actions（AI 辅助 / Goldie）

**功能描述**：
- 由 Goldie 基于 Perception Gap 生成实用的、可执行的行动建议，将 Scorecard 从「度量工具」升级为「教练工具」。
- 输入源：
  - Founder 与 GSV 双方提交的证据/备注上下文
  - ERL Workbook 中各 Stage/维度的准入准则
- 生成逻辑：
  - 存在 Perception Gap，或双方均认为某维度分数低于目标时，Goldie 识别 Workbook 中尚未满足的具体准则，将其作为建议行动的依据。
- 建议为**指导性**而非强制性任务：
  - 说明「可以做什么」以及「为何相关」，结合公司具体情境（非通用建议）。
  - MVP 不含正式跟踪、指派、Deadline 功能。
- 展示位置：Scorecard 视图内（inline 于每维度 或 作为独立面板）。
- 权限：Founder 与 GSV 团队均可见，但两者展示口吻不同：
  - Founder 视角：「你可以做什么…」
  - GSV 视角：「我们建议这家公司…」
- 新评估提交后自动刷新分析，始终反映最新数据。
- 双方分数均高、无实质差距时，Goldie 承认此为公司优势，不强行套用差距叙述。
- 全端响应式。

**已知 TBD 与 MVP 备选方案**：
- 详细生成逻辑与 prompt（Founder / GSV 两套）尚未定义。
- 待决定：是否在 Score Details 页新增一个「GSV vs. Founder 分数对比」Tab，突出显示两者差距最大的题目，作为完整 AI 建议上线前的 MVP 替代方案。
- 待 Li 团队确认：「Gap」的粒度是按题、按维度，还是仅取 GSV 与 Founder 综合分的差值。
- 后续：当 Fireflies 会议转录 与 SharePoint 集成上线后，Goldie 分析将扩展这些数据源；「Goldie 直接根据外部源自动打分」作为独立的 post-MVP story，取决于 Li 与 Blake 敲定的评分逻辑与数据源决策。

---

### 7. 投资组合级评估看板（Portfolio-Wide Assessment Dashboard）

**功能描述**：
- 交付形式：**在现有 Portfolio 下的 Company List 页新增一个「ERL」Tab**（与 General、Connections、Issues、Benchmarking 并列），**不做独立看板页**。
- 表格列：
  - Company
  - ERL Score（综合）
  - FRL、PRL、BERL、RRL、TRL（5 个维度分数）
  - Stage
  - View（跳转到该公司的 Score Details 页面）
- 支持按分数、Stage、维度进行**排序与筛选**。
- 权限：仅 Portfolio Manager / Portfolio Group Manager。

---

### 8. ERL Configuration（题库配置）

**功能描述**：
- 管理员通过顶部导航右侧下拉菜单进入；仅 admin。
- 允许 portfolio admin 在**无需工程介入**的情况下管理 5 个维度的题库（因评分规则仍在演进）。
- **五个 Tab**，每个维度一个（FRL / PRL / BERL / RRL / TRL），展示该维度题库。
- 按 **Era Band** 分组显示（如 Founder Era-1、Founder Era-2、Founder Era-3），与原型稿一致。
- 支持操作：
  - **添加**新题目（题干、Era Band、Source）——通过「Add New」入口。
  - **编辑**题目的题干、Era Band 或 Source。
  - **删除**题目。
  - **拖拽重排**：在 Era Band 内调整顺序，该顺序即评估中的**必答顺序**（对应 Yes/No + 固定序列模型）。
- 变更**立即生效**到评估表与 Score Details 的题目列表中，无需其他配置步骤。
- 明确边界：与顺序相关的具体计分逻辑（例如 "No" 中断时该维度分数如何处理）属于评估表 / Scorecard story，本 story 只覆盖题库配置本身（TBD）。
- Publish按钮：五个维度任意维度有新问题，按钮会被激活。

**UX 要点**：
- 匹配原型稿：按维度分 Tab、按 Era Band 分组、拖拽 handle、行内编辑/删除图标、可见的 Source 列。
- 由于重排会影响必答顺序（不仅是展示顺序），需考虑对进行中或历史评估解释产生的潜在影响，给管理员必要的警告。
- 定位为 admin 配置工具。

---

### 9. Assessment History（评估历史）

**功能描述**：
- 由于评估按季提交且提交后不可编辑，用户需要一份**只读的历史提交日志**，追溯公司准备度演进；由于同一季度可多次提交（最新为 source of truth），本页必须完整保留并清晰区分每一次单独提交，而非只显示最新一条。
- 列表最少字段：
  - Period（评估周期）
  - Portal（Founder 或 GSV）
  - Submitted By（姓名与角色）
  - Completion（如 "45/45"）
  - Overall Score（含 Stage 标签）
- 每次提交独立保存为一条带日期的记录。
- 页面完全只读，无编辑入口。
- 点击某条记录可打开该次提交的详情（复用 Score Details 的题级布局，呈现该提交时的状态）。
- 列表默认**最近提交在前**。
- 入口：从相应维度的 Score Details 页面通过「View history」进入。

**UX 要点**：
- 列表可扫读，无需展开即可看到 period / portal / 提交人 / 完成度 / 分数。
- 与其他 ERL 界面保持一致的分数/Stage 配色。
- 视觉上突出「最新 / source of truth」提交，避免将旧记录误当作当前有效记录。

---

## 四、汇总：全局规则与跨模块约束

- **权限模型**：Company User / Company Admin（Founder 侧）；Portfolio Manager / Portfolio Group Manager（GSV 侧）；配置页仅 admin。
- **评估周期**：季度提交；提交后只读；同季度多次提交允许，最新为 source of truth。
- **数据保留**：DI 数据不删除；所有历史评估提交完整保留。
- **文件上传**：所有题目附件同步写入公司 Memory File，供 Goldie 分析使用。
- **打分格式演进**：MVP 使用 1–9 占位，需保留切换至「Yes/No + 固定顺序」的能力（后者下 "No" 中止该维度后续计分）。
- **外部静态数据**：Benchmarkit、Top GSV Quartile 通过独立数据接入，不由平台内部计算。
- **响应式**：所有页面覆盖桌面与移动端。
- **导航一致性**：Exit Readiness ›〔Dimension Name〕 面包屑保留于维度页返回路径。

---

## 五、明确的 TBD 事项（供后续澄清）

1. ERL 卡片上 Gap Analysis 呈现方案 与 BPMM 内容/规则。
2. 打分格式最终形态（1–9 vs Yes/No + 固定顺序）及 "No" 中断后的精确计分逻辑。
3. 每维度分数的具体计算方法（是否为题均分）。
4. Goldie 建议的详细生成逻辑与 prompt（Founder / GSV 分别）。
5. 是否以「GSV vs. Founder 对比 Tab」作为 AI 建议之前的 MVP 替代方案。
6. 「Gap」的粒度（按题 / 按维度 / 综合分差值）。
7. ERL 卡片及后续页面可见的角色子集是否需要收窄。
8. Configuration 中题目顺序变更对进行中/历史评估解释的处理策略。
