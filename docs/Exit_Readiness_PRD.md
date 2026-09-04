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
- Harvest & Growth Era：Stage 4–6
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

- Company Overview 页原有的 DI 卡片放在FI卡片下；DI 数据、打分保留概览信息和入口。
- 原 DI 卡片位置由新的 ERL 卡片替代，卡片直接展示完整聚合评分内容：
  - 综合分数（Overall Score）: 按照weight configuration页面配置的五个维度的权重算分
  - 当前 Stage
  - Gap Analysis & Suggested Actions 摘要（TBD）
  - 5 个 ERL 维度列表（含各维度分数：回答问题时该维度最后一个全部Yes的level的level为此维度得分；Perception Gap：Founder和GSV每个维度的分数差）
    - 数据来源：closed month所在季度的评价
  - BPMM（TBD）
  - 5 维度雷达图
- **不设独立 Exit Readiness 落地页**；ERL 卡片是唯一入口。
- 卡片内提供每个维度的「View Details」入口，直接跳转到该维度的 Score Details 页。
- ERL 卡片及后续页面对当前可访问 Company Overview 的角色开放（具体权限子集待确认）。

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
  - 该维度全部题目列表，每题显示 Era-level 标签（如 "Founder Era-1"）与得分
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
- 表单顶部提供**评估期选择器**（如 "Q3 2026"），有Save as draft、Cancel、Reset、submit按钮
- 题库来源于 ERL Configuration，按 5 个维度组织；每个维度内按 3 个 Era 分组：
  - Founder Era（Stage 1–3）
  - Harvest & Growth Era（Stage 4–6）
  - Exit Era（Stage 7–9）
- **打分格式**：
  - 全部问题包含Era和level,为Yes/No + 固定顺序必答模式（在ERL configuration中配置的顺序）；
  - 五个维度的所有问题按照Era和等级依次显示
    - 例如用户回答完了Founder Era-1的问题，且答案全部为yes,该level折叠并显示Check,再显示下一level的问题，直到有No回答(或全部答完），就不再显示下一Level,激活提交按钮，分数就是此回答为No的Level减一；若9个层级都是yes回答，则最终得分为9
- 每题字段：
  - 可选「证据/备注（Evidence/Notes）」文本、可上传附件（单个最大10MB）
  - 每题显示来源标签（Founder/CTO、Looking Glass、SharePoint 等）
- 创始人**独立**完成，全程不可看到 GSV 分数。
- 支持保存进度、稍后继续，无数据丢失。
- **提交后即只读**，如需修改必须新建一次提交。
- 同一季度允许多次提交，最新一次为 source of truth。
- 每次提交生成带日期的记录（提交日期、评估人、基金/组合）。
- 历史记录进入 Assessment History。
- 仅限公司用户在其自身 portal 内完成，portfolio admin 不能代填。
- 操作流程说明：
  - 点击Add New按钮，进入问卷回答页面，若有草稿则进入之前的草稿（若题库已更新，则提示题库更新，不做强制退出和更新），提示草稿，显示上次保存时间和保存人；若无草稿则直接新增。
  - 答题完成后，可提交为该季度评价，若之前已提交该季度评价，则弹出提示：已提交该季度评价，是否再次提交？
  - 答题后，可保存为草稿，若之前有其他草稿，则直接覆盖，草稿为公司共享，不区分账户。
  - 问卷提交人已最终提交者为准
- 全端响应式。
---

### 4. ERL 评估表 — GSV 团队流程（GSV Flow）

**功能描述**：
- 面向 **Portfolio Manager / Portfolio Group Manager**，在 Assessments 区块内、按 portfolio 公司访问。
- 使用与 Founder Flow **相同**的题库、Era 分组、打分标度（同样受 Yes/No + 固定顺序 TBD 影响）。
- 每题字段：
  - 可选择yes/no
  - **来源标签**（Looking Glass、SharePoint、GSV Assessment、Board Transcripts / Fireflies 等）
  - 可选「证据/备注」文本
- 表单顶部提供**评估期选择器**（如 "Q3 2026"）。
- 每个维度均可提交附件
- 保存进度、可恢复。
- 提交后只读；同一季度可多次提交，最新为 source of truth。
- 每次提交生成带元数据的记录，进入 Assessment History。
- Portfolio admin 可为其权限范围内任意公司完成/更新 GSV 评估。
- 全端响应式。

---

### 5. ERL Scorecard 与 Radar Chart

**功能描述（评分与计算）**：
- 每个维度分数：由该维度内各题分数计算得出（**具体计算方法**：初步为各题平均）。
- **综合 ERL 分数** = 5 个维度分数的简单平均，以 X/9 形式显示。
- **当前 Stage（1–9）**：由综合分数与 Workbook 中的 Era 边界推导。
- **Perception Gap（仅Porfolio portal）**：（每维度）= Founder 分 − GSV 分；正值 = 创始人自评更高，负值 = GSV 更高。
- **Full View (仅Company portal)**：点击进入Score details 页面，该页面包含五个维度的最新版的问题记录，每个维度包括一个Add New按钮和一个View History链接，可以查看每个维度的问卷历史记录，也可以从该页面点击AddNew新增问卷

**功能描述（雷达图）**：
- 雷达/蛛网图在同一张图上呈现**四条线**：
  1. Founder 自评
  2. GSV 评估
  3. Benchmarkit 外部对标
  4. Top GSV Quartile
- Founder 与 GSV 线来自评估提交；Benchmarkit 与 Top GSV Quartile **为静态数据输入**，不由 Looking Glass 计算得出。
- 图形规范：**仅线条无填充**（与 Workbook 一致）、每线不同色、有图例、中心轴隐藏。
- 5 个顶点分别对应 5 个 ERL 维度，明确标注。
- 交互：悬停数据点显示该维度、该 perspective 的精确分数。
- 架构上支持 MVP 展示 4 条线，同时预留后续新增 perspective 的能力。
- 该图仅在Portfolio端显示
- Benchmarkit 与 Top GSV Quartile输入和历史记录：在雷达图下方的链接，点击进入可以看历史记录和新增记录

**功能描述（Scorecard 展示）**：
- 展示项：
  - 综合 ERL 分数
  - 当前 Stage 与 Era
  - 每维度 Founder 分或 GSV 分（根据账户权限）
  - 每维度 Perception Gap
- **BPMM 分数**：仅作为参考数字（1–5）显示；完整 BPMM 评估交互**不在本 story 范围内**。
- 权限：
  - 创始人（公司 portal）：只能查看自己的分数。
  - GSV 团队（portfolio portal）：相同视图 + portfolio 专属信息。
- 从 Scorecard 可访问历史评估记录，回看往期。
- 全端响应式。

---

### 6. Gap Analysis 与 Suggested Actions（AI 辅助 / Goldie）

**功能描述**：
- 由 Goldie 基于 Perception Gap 生成实用的、可执行的行动建议，将 Scorecard 从「度量工具」升级为「教练工具」。
- 输入源：
  - Founder 与 GSV 双方提交的题目gap/备注上下文
- 生成逻辑：
  - 各维度存在 Perception Gap、备注内容，AI自动分析，将其作为消除gap建议行动的依据。
- 数据来源：closed month所在季度的评价
- 只有所有维度两方都完成时，share按钮才被激活，有gap的，展示建议，没有的不展示。
  - 绿点代表该维度GSV和founder都已提交问卷，灰点代表未全部提交，下方文字为是否有gap分析的提示
- View details按钮：点击弹出建议详情弹框，分为五个维度，没有gap的展示No Gap，没有提交的显示未提交
- 权限：GSV 团队均可见，可以点击Share按钮分享给Founder端。
- 全端响应式。

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
    - Score Details页面：该页面包含五个维度的最新版的问题记录（GSV和Founder的记录），每个维度包括一个Add New按钮和一个View History链接，可以查看每个维度的问卷历史记录，也可以从该页面点击AddNew新增问卷
- 权限：仅 Portfolio Manager / Portfolio Group Manager。

---

### 8. ERL Configuration（题库配置）

**功能描述**：
- 管理员通过顶部导航右侧下拉菜单进入；仅 portfolio portal。
- 允许 portfolio admin 在**无需工程介入**的情况下管理维度、题库和维度在总分计算中的权重。
- 该页面包含一个维度题库tab和维度管理tab
- **题库tab**，每个维度一个（FRL / PRL / BERL / RRL / TRL...），展示该维度题库。
  - 按 **Era Band** 分组显示（如 Founder Era-1、Founder Era-2、Founder Era-3），与原型稿一致。
    - 支持操作：
    - **添加**新题目（题干、Era Band、Source）——通过「Add New」入口。
    - **编辑**题目的题干、Era Band 或 Source。
    - **删除**题目。
    - **拖拽重排**：在 Era Band 内调整顺序，该顺序即评估中的**必答顺序**（对应 Yes/No + 固定序列模型）。
    - Publish按钮：五个维度任意维度有新问题、新顺序或新编辑内容，按钮会被激活，点击保存为新版本。
- **Dimension Configuration tab**
  - 该页面可以新增、删除维度，为维度排序，修改维度的占比。新增删除或排序后，对应的页面应回显，如overview页面、雷达图、题库页面
  - Save按钮只有在有新增删除或调整维度且各维度比重相加为100%时激活，若权重超过或小于100%会显示提示

---

### 9. Assessment History（评估历史）

**功能描述**：
- 由于评估按季提交且提交后不可编辑，用户需要一份**只读的历史提交日志**，追溯公司准备度演进；由于同一季度可多次提交（最新为 source of truth），本页必须完整保留并清晰区分每一次单独提交，而非只显示最新一条。
- 列表最少字段：
  - Period（评估周期）
  - Portal（Founder 或 GSV）(Portfolio端）
  - Submitted (提交时间）
  - Submitted By（姓名与角色）
  - 维度Overall Score（含 Stage 标签）
- 每次提交独立保存为一条带日期的记录。
- 页面完全只读，无编辑入口。
- 点击某条记录可打开该次本维度提交的详情。
- 列表默认**最近提交在前**。
- 入口：从相应维度的 Score Details 页面通过「View history」进入。
---

## 四、汇总：全局规则与跨模块约束

- **权限模型**：Company User / Company Admin（Founder 侧）；Portfolio Manager / Portfolio Group Manager（GSV 侧）；ERL配置层级按照租户层级
- **评估周期**：季度提交；提交后只读；同季度多次提交允许，最新为 source of truth。
- **数据保留**：DI 数据不删除；所有历史评估提交完整保留。
- **文件上传**：所有维度附件同步写入公司 Memory File，供 Goldie 分析使用。
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
