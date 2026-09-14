# 测试用例：Exit Readiness（退出准备度，ERL）

- **需求来源**：https://github.com/WenchaoChen1/LG/blob/74f25df81d93965b191cb1ba3c9b117c7db37cda/docs/Exit_Readiness_PRD.md
- **生成时间**：2026-09-08


## 需求清单

### 模块一：ERL Configuration（题库与权重配置）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R1 | 功能需求 | 管理员通过顶部导航右侧下拉菜单进入，仅 portfolio portal |
| R2 | 功能需求 | 维度集合可配置：维度数量不固定为 5 个，支持新增维度（维度名称、缩写、题库），FRL/PRL/BERL/RRL/TRL 为初始默认维度 |
| R3 | 业务规则 | 尚未 Publish 的维度可直接删除 |
| R4 | 业务规则 | 已 Publish 的维度不可删除，只能 Deactivate |
| R5 | 业务规则 | Deactivate 后该维度不参与新一轮评估、计分与权重分配，历史提交与历史分数完整保留；Deactivated 维度可重新 Activate |
| R6 | 业务规则 | 总分权重设置随启用中的维度动态生成（维度数量变化时输入项同步增减），总权重必须为 100%，低于或高于 100% 时均不激活保存按钮 |
| R7 | UI 需求 | 每个已配置维度一个 Tab（Tab 数量随维度增减动态变化，初始为 FRL/PRL/BERL/RRL/TRL），题库按 Era Band 分组显示（如 Founder Era-1、Founder Era-2、Founder Era-3） |
| R8 | 功能需求 | 通过 Add New 入口添加新题目（题干、Era Band、Source） |
| R9 | 功能需求 | 编辑题目的题干、Era Band 或 Source |
| R10 | 功能需求 | 删除题目 |
| R11 | 功能需求 | Era Band 内拖拽重排，该顺序即评估中的必答顺序 |
| R12 | 业务规则 | Publish 按钮：任意维度有新增维度、新问题、新顺序或新编辑内容时激活，点击保存为新版本 |
| R13 | 边界条件 | Configuration 中题目顺序变更对进行中/历史评估的解释与处理策略（需求 TBD） |
| R14 | 业务规则 | 允许 portfolio admin 在无需工程介入的情况下管理维度集合、题库与权重；ERL 配置层级按租户层级 |
| R15 | 边界条件 | 启用中的维度数量边界：至少保留 1 个启用维度；维度数量增减时权重、雷达图顶点、评估表与组合看板列同步适配 |

### 模块二：ERL 卡片与公司概览导航

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R16 | 功能需求 | Company Overview 原有 DI 卡片下移至 FI 卡片下方，DI 数据、打分、概览信息与入口全部保留 |
| R17 | UI 需求 | 原 DI 卡片位置由 ERL 卡片替代（原型 Example 2 单卡片方案），卡片直接展示综合分数、当前 Stage、Gap Analysis 摘要、5 维度列表、BPMM、5 维雷达图 |
| R18 | 业务规则 | 综合分数（Composite Score）= 按 Weight Configuration 页面配置的五维度权重加权计算 |
| R19 | 业务规则 | 维度分数 = 该维度连续全部回答 Yes 的最后一个 Level；遇 No 时得分 = 该 Level − 1；9 级全 Yes 得 9 |
| R20 | 业务规则 | Perception Gap（每维度）= Founder 分 − GSV 分；正值表示创始人自评更高，负值表示 GSV 更高 |
| R21 | 功能需求 | 不设独立 Exit Readiness 落地页，ERL 卡片是唯一入口；卡片内每个维度提供 View Details 直接跳转该维度 Score Details 页 |
| R22 | UI 需求 | 从维度页返回时保留面包屑：Exit Readiness ›〔Dimension Name〕 |
| R23 | 功能需求 | ERL 卡片上的 Gap Analysis & Suggested Actions 摘要与 BPMM 展示（需求 TBD） |

### 模块三：维度详情页（Score Details）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R24 | 功能需求 | 5 个维度（FRL/PRL/BERL/RRL/TRL）共用同一套模板，由 dimension 参数驱动 |
| R25 | UI 需求 | 页面展示维度名称（如 Financial Readiness (FRL)）、该维度题目总数、该维度综合分数、全部题目列表（每题含 Era-level 标签与得分） |
| R26 | 功能需求 | 提供 Founder / GSV Tab 切换；公司用户不显示 GSV Tab |
| R27 | UI 需求 | 元数据栏展示 Period、Submitted By、Role、Submitted At |
| R28 | 功能需求 | 提供 View history 入口（跳转限定当前维度的 Assessment History）与 + New 入口（发起该维度新一轮评估） |
| R29 | 业务规则 | 权限：创始人只能看到自己的数据且不显示 GSV 专属字段（Benchmarkit、Top GSV Quartile）；GSV 团队可见 GSV 专属字段 |

### 模块四：ERL 评估表 — Founder Flow

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R30 | 功能需求 | 面向 Company User / Company Admin，在 Assessments 区块内访问；仅限公司用户在其自身 portal 内完成，portfolio admin 不能代填 |
| R31 | 功能需求 | 表单顶部提供评估期选择器（如 Q3 2026） |
| R32 | 数据需求 | 题库来源于 ERL Configuration，按 5 维度组织，每维度内按 3 个 Era 分组（Founder Era 1–3 / Harvest & Growth Era 4–6 / Exit Era 7–9），Configuration 中的顺序即必答顺序 |
| R33 | 业务规则 | Level 递进显示：某 Level 全部回答 Yes 后该 Level 折叠并显示 Check，随后显示下一 Level；出现 No 回答或全部答完后不再显示下一 Level 并激活提交按钮 |
| R34 | 业务规则 | 计分逻辑：得分 = 回答为 No 的 Level − 1；9 个层级全部 Yes 则最终得分为 9 |
| R35 | 功能需求 | 每题提供可选「证据/备注（Evidence/Notes）」文本，并显示来源标签（Founder/CTO、Looking Glass、SharePoint 等） |
| R36 | 业务规则 | 创始人独立完成，全程不可看到 GSV 分数 |
| R37 | 功能需求 | 支持保存进度、稍后继续，无数据丢失 |
| R38 | 业务规则 | 提交后即只读，如需修改必须新建一次提交；同一季度允许多次提交，最新一次为 source of truth |
| R39 | 数据需求 | 每次提交生成带日期的记录（提交日期、评估人、基金/组合），并进入 Assessment History |

### 模块五：ERL 评估表 — GSV Flow

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R40 | 功能需求 | 面向 Portfolio Manager / Portfolio Group Manager，在 Assessments 区块内按 portfolio 公司访问；portfolio admin 可为其权限范围内任意公司完成/更新 GSV 评估 |
| R41 | 数据需求 | 使用与 Founder Flow 相同的题库、Era 分组、打分标度 |
| R42 | 功能需求 | 每题可选择 Yes/No，含来源标签（Looking Glass、SharePoint、GSV Assessment、Board Transcripts / Fireflies 等）与可选证据/备注文本 |
| R43 | 功能需求 | 每个维度均可提交附件；所有维度附件同步写入公司 Memory File 供 Goldie 分析 |
| R44 | 功能需求 | 顶部提供评估期选择器；支持保存进度、可恢复 |
| R45 | 业务规则 | 提交后只读；同一季度可多次提交，最新为 source of truth；每次提交生成带元数据记录进入 Assessment History |

### 模块六：ERL Scorecard 与 Radar Chart

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R46 | 业务规则 | 综合 ERL 分数以 X/9 形式显示 |
| R47 | 业务规则 | 当前 Stage（1–9）由综合分数与 Era 边界推导；Stage 1–3 为 Founder Era，4–6 为 Harvest & Growth Era（分数约 6 表示进入该纪元、可开始接触投行），7–9 为 Exit Era |
| R48 | UI 需求 | Scorecard 展示综合 ERL 分数、当前 Stage 与 Era、每维度 Founder 分或 GSV 分（依权限）、每维度 Perception Gap |
| R49 | UI 需求 | 雷达/蛛网图在同一张图上呈现四条线：Founder 自评、GSV 评估、Benchmarkit 外部对标、Top GSV Quartile |
| R50 | 数据需求 | Benchmarkit 与 Top GSV Quartile 为静态数据输入，通过独立数据接入，不由 Looking Glass 计算 |
| R51 | UI 需求 | 图形规范：仅线条无填充、每线不同色、有图例、中心轴隐藏；5 个顶点分别对应 5 个 ERL 维度并明确标注 |
| R52 | 功能需求 | 交互：悬停数据点显示该维度、该 perspective 的精确分数 |
| R53 | 边界条件 | 架构支持 MVP 展示 4 条线，同时预留后续新增 perspective 的能力 |
| R54 | 业务规则 | 雷达图仅在 Portfolio 端显示 |
| R55 | 业务规则 | BPMM 分数仅作为参考数字（1–5）显示，完整 BPMM 评估交互不在本 story 范围内（需求 TBD） |
| R56 | 功能需求 | 从 Scorecard 可访问历史评估记录，回看往期 |

### 模块七：Gap Analysis 与 Suggested Actions（Goldie）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R57 | 功能需求 | 由 Goldie 基于 Perception Gap 生成实用、可执行的行动建议（需求 TBD） |
| R58 | 数据需求 | 输入源为 Founder 与 GSV 双方提交的证据/备注上下文，以及 ERL Workbook 中各 Stage/维度的准入准则 |
| R59 | 业务规则 | 生成逻辑：存在 Perception Gap，或双方均认为某维度分数低于目标时，Goldie 识别 Workbook 中尚未满足的具体准则作为建议依据 |
| R60 | 业务规则 | 建议为指导性而非强制性任务，说明「可以做什么」及「为何相关」并结合公司具体情境；MVP 不含正式跟踪、指派、Deadline |
| R61 | 业务规则 | 权限与口吻：Founder 与 GSV 均可见，Founder 视角为「你可以做什么…」，GSV 视角为「我们建议这家公司…」；展示于 Scorecard 视图内（inline 于每维度或独立面板） |
| R62 | 业务规则 | 新评估提交后自动刷新分析；双方分数均高、无实质差距时承认此为公司优势，不强行套用差距叙述 |
| R63 | 功能需求 | MVP 备选方案：在 Score Details 页新增「GSV vs. Founder 分数对比」Tab，突出显示差距最大的题目（需求 TBD） |

### 模块八：Portfolio ERL Tab（组合级评估看板）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R64 | 功能需求 | 在现有 Portfolio 下的 Company List 页新增 ERL Tab（与 General、Connections、Issues、Benchmarking 并列），不做独立看板页 |
| R65 | UI 需求 | 表格列包含 Company、ERL Score（综合）、FRL、PRL、BERL、RRL、TRL、Stage、View |
| R66 | 功能需求 | 支持按分数、Stage、维度进行排序与筛选 |
| R67 | 业务规则 | 权限仅 Portfolio Manager / Portfolio Group Manager；View 跳转到该公司的 Score Details 页面 |

### 模块九：Assessment History（评估历史）

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R68 | 功能需求 | 提供只读的历史提交日志；同一季度多次提交必须完整保留并清晰区分每一次单独提交，而非只显示最新一条 |
| R69 | UI 需求 | 列表最少字段：Period、Portal（Founder 或 GSV）、Submitted By（姓名与角色）、Completion（如 45/45）、Overall Score（含 Stage 标签） |
| R70 | 业务规则 | 页面完全只读，无编辑入口；每次提交独立保存为一条带日期的记录 |
| R71 | 功能需求 | 点击某条记录可打开该次提交的详情，复用 Score Details 的题级布局，呈现该提交时的状态 |
| R72 | 业务规则 | 列表默认最近提交在前；入口从相应维度的 Score Details 页通过 View history 进入 |

### 模块十：全局规则与跨模块约束

| # | 需求类型 | 需求描述 |
|---|---------|---------|
| R73 | 业务规则 | 权限模型：Company User / Company Admin 为 Founder 侧；Portfolio Manager / Portfolio Group Manager 为 GSV 侧 |
| R74 | 数据需求 | 数据保留：DI 数据不删除；所有历史评估提交完整保留 |
| R75 | UI 需求 | 响应式：所有页面覆盖桌面与移动端 |

---

## 测试用例

### 一、ERL Configuration（题库与权重配置）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-001 | 新增维度 | 以 Portfolio Group Manager 登录进入 ERL Configuration，当前为 FRL/PRL/BERL/RRL/TRL 五个默认维度 | 查看新增维度入口 | 新增维度表单，含维度名称、缩写等字段 |
| | | | 输入维度名称 Governance Readiness、缩写 GRL 并确认 | 新增第 6 个维度 Tab GRL，题库为空，维度数量不再固定为 5 个 |
| | | | 查看权重设置区 | 权重输入项由 5 项变为 6 项，新增 GRL 权重项，合计校验重新计算 |
| | | | 查看 Save 按钮状态 | Save 按钮激活 |
| TC-002 | 新增维度字段校验与重名校验（反向/边界） | 已打开新增维度表单 | 维度名称留空直接确认 | 提示维度名称为必填，无法保存 |
| | | | 输入与已有维度重复的缩写 FRL 并确认 | 提示缩写已存在，不允许重复，无法保存 |
| | | | 输入超长维度名称（如 200 字符）并确认 | 按上限截断或提示超出长度限制，Tab 展示不破版 |
| | | | 输入含特殊字符与中英混排的维度名称并确认 | 按纯文本原样保存与展示，无乱码、无脚本执行 |
| TC-003 | 未 Publish 的维度可直接删除 | 已新增维度 GRL 且尚未 Publish | 查看 GRL 维度的操作按钮| 显示Edit，Delete按钮 |
| | | | 点击删除并确认 | GRL 维度被移除，Tab 数量回到 5，权重输入项回到 5 项 |
| | | | 进入 Founder Flow 与 GSV Flow 查看维度分组 | 均不出现 GRL 维度，未发布的删除不留痕 |
| TC-004 | 已 Publish 的维度不可删除（反向） | GRL 维度已 Publish | 查看 GRL 维度的操作按钮 | 显示 Edit，Deactivate 按钮 |
| | | | 尝试通过接口或 URL 直接删除已 Publish 的 GRL 维度 | 请求被拒绝并提示已发布维度只能停用，维度与其历史数据不被删除 |
| | | | 依次查看 FRL 等其余已 Publish 维度的操作入口 | 同样仅有Edit， Deactivate，无Delete按钮 |
| TC-005 | Deactivate 已 Publish 的维度 | 6 个维度均已 Publish，权重为 FRL25%/PRL20%/BERL15%/RRL15%/TRL15%/GRL10% | 点击 GRL 的 Deactivate 并确认 | GRL 标记为 Deactivated，提示需重新分配权重 |
| | | | 查看权重设置区 | GRL 权重项移除，剩余 5 个维度合计为 90%，保存按钮置灰 |
| | | | 将剩余 5 维度权重调整为合计 100% 后 保存 | 保存成功 |
| | | | 发起新一轮 Founder Flow 与 GSV Flow | 评估表中不再出现 GRL 维度及其题目 |
| | | | 查看 ERL 卡片维度列表、雷达图与 Portfolio ERL Tab | 维度列表与雷达图顶点不含 GRL，Portfolio 表格不含 GRL 列，综合分仅按启用维度权重计算 |
| TC-006 | Deactivate 后历史数据完整保留 | GRL 已 Deactivate，此前存在含 GRL 的历史提交与历史分数 | 进入 Assessment History 查看历史记录 | 含 GRL 的历史提交完整保留，未被删除或隐藏 |
| | | | 打开该条历史提交详情 | GRL 的题级答案、备注与分数按提交时状态呈现 |
| | | | 核对该历史记录的综合分 | 保持提交时的计算结果，不因维度停用而被重算或清零 |
| TC-007 | 重新 Activate 已停用的维度（双向验证） | GRL 处于 Deactivated 状态 | 点击 GRL 的 Activate 并确认 | GRL 状态恢复为启用 |
| | | | 查看权重设置区 | GRL 权重项恢复显示，合计校验重新包含 GRL，未达 100% 时保存按钮置灰 |
| | | | 调整权重至合计 100% 后 保存，再发起新一轮评估 | GRL 题目重新出现，题库沿用停用前的已发布版本 |
| | | | 查看 ERL 卡片、雷达图与 Portfolio ERL Tab | GRL 维度、雷达图顶点与表格列恢复显示 |
| TC-008 | Deactivated 维度在配置页的展示与可操作范围 | GRL 处于 Deactivated 状态 | 查看 GRL 的 Tab 视觉状态 | GRL 的 Tab不显示 |
|  TC-009 | 维度数量变化联动全链路并按新权重计分（公式验证） | 新增维度 GRL 并 Publish；权重为 FRL=25%、PRL=20%、BERL=15%、RRL=15%、TRL=15%、GRL=10%（合计 100%）；某公司维度分数为 FRL=8、PRL=6、BERL=4、RRL=5、TRL=3、GRL=7 | 发起并提交该公司的 Founder Flow | 评估表出现 6 个维度分组，GRL 题目可正常作答与提交 |
| | | | 查看 ERL 卡片的维度列表与雷达图 | 维度列表显示 6 行，雷达图显示 6 个顶点且明确标注 GRL |
| | | | 查看 ERL 卡片的 Composite Score | 显示 5.7/9（计算：8×0.25+6×0.20+4×0.15+5×0.15+3×0.15+7×0.10 = 2.0+1.2+0.6+0.75+0.45+0.7 = 5.7） |
| | | | 查看 Portfolio ERL Tab 表格 | 表格新增 GRL 列，该列可参与排序与筛选 |
| TC-010 | 启用维度数量边界（边界） | 当前有 6 个已 Publish 维度 | 依次 Deactivate 至仅剩 1 个启用维度（FRL），并将 FRL 权重设为 100% 后 Publish | 允许保存，综合分等于 FRL 分数（计算：FRL×100%），雷达图按单顶点的既定降级方式展示且不报错 |
| | | | 尝试 Deactivate 最后一个启用维度 FRL | 操作被拒绝并提示至少需保留 1 个启用维度 |
| | | | 将维度新增至 10 个并 Publish | 配置页 Tab、权重区、评估表、ERL 卡片雷达图、Portfolio 表格列均正常渲染，无破版或横向溢出 |
| TC-011 | 维度配置的租户隔离与权限 | 存在租户 T1（含公司 A）与租户 T2（含公司 C） | 以租户 T1 的 portfolio admin 新增维度 GRL 并 Publish | 保存成功，T1 下公司 A 的评估表与卡片出现 GRL |
| | | | 查看租户 T2 下公司 C 的维度集合 | 不出现 GRL，维度集合按租户层级独立维护 |
| | | | 以 Company User 尝试访问维度新增、删除与 Deactivate 入口 | 无权访问，通过 URL 直接请求被拒绝并提示无权限 |
| TC-012 | 从顶部导航右侧下拉菜单进入且仅 portfolio portal | 以 超管 登录 portfolio portal | 展开顶部导航右侧下拉菜单 | 菜单中显示 ERL Configuration 入口 |
| | | | 点击 ERL Configuration | 进入配置页，页面包含权重设置区与五个维度 Tab |
| | | | 改用 Company User 登录公司 portal 并展开同一菜单 | 无 ERL Configuration 入口；通过 URL 直接访问被拒绝并提示无权限 |
| TC-013 | 配置层级按租户层级生效 | 存在租户 T1（含公司 A、B）与租户 T2（含公司 C） | 以租户 T1 的 portfolio admin 修改 FRL 题库并 Publish | 保存成功 |
| | | | 查看公司 A 与公司 B 的评估表题库 | 均使用 T1 的新题库 |
| | | | 查看租户 T2 下公司 C 的评估表题库 | 保持 T2 自身配置，不受 T1 修改影响 |
| TC-014 | 权重合计等于 100% 时保存按钮激活（公式验证） | 进入 ERL Configuration 权重设置区；当前启用维度为 FRL/PRL/BERL/RRL/TRL 五个；公式 权重合计 = 各启用维度权重之和 | 输入 FRL=30%、PRL=25%、BERL=15%、RRL=15%、TRL=15% | 合计显示 100%（计算：30+25+15+15+15=100） |
| | | | 查看保存按钮状态 | 保存按钮激活可点击 |
| | | | 点击保存 | 保存成功并提示成功，权重生效 |
| TC-015 | 权重合计低于 100% 时保存按钮不激活（边界） | 进入权重设置区 | 输入 FRL=30%、PRL=25%、BERL=15%、RRL=15%、TRL=14% | 合计显示 99%（计算：30+25+15+15+14=99），页面提示总权重需为 100% |
| | | | 查看保存按钮状态 | 保存按钮置灰不可点击 |
| | | | 将 TRL 调整为 14.9% | 合计 99.9%，保存按钮仍置灰 |
| TC-016 | 权重合计高于 100% 时保存按钮不激活（边界） | 进入权重设置区 | 输入 FRL=30%、PRL=25%、BERL=15%、RRL=15%、TRL=16% | 合计显示 101%（计算：30+25+15+15+16=101），页面提示总权重需为 100% |
| | | | 查看保存按钮状态 | 保存按钮置灰不可点击 |
| | | | 将 TRL 调整为 15.1% | 合计 100.1%，保存按钮仍置灰 |
| TC-017 | 单个权重输入边界（边界） | 进入权重设置区 | 将 FRL 设为 0%、其余四维度合计 100%（PRL=40%、BERL=20%、RRL=20%、TRL=20%） | 合计 100%，保存按钮激活，允许单维度权重为 0 |
| | | | 将 FRL 设为 100%、其余四维度均为 0% | 合计 100%，保存按钮激活，综合分等于 FRL 分数 |
| | | | 输入负数（如 FRL=-10%） | 拒绝输入或提示不合法，保存按钮不激活 |
| | | | 输入非数字字符（如 FRL=abc） | 拒绝输入或提示格式错误，保存按钮不激活 |
| TC-018 | 权重保存后综合分数按新权重重算（联动） | 某公司维度分数为 FRL=6、PRL=4、BERL=7、RRL=5、TRL=3；当前权重为各 20% | 记录当前综合分数 | 显示 5.0/9（计算：(6+4+7+5+3)×0.2 = 5.0） |
| | | | 将权重改为 FRL=50%、PRL=20%、BERL=10%、RRL=10%、TRL=10% 并保存 | 保存成功 |
| | | | 返回该公司 ERL 卡片、Scorecard 与 Portfolio ERL Tab 查看综合分 | 三处均刷新为 5.3/9（计算：6×0.5+4×0.2+7×0.1+5×0.1+3×0.1 = 5.3），全链路联动一致 |
| TC-019 | 维度 Tab 切换（数量随已配置维度变化） | 已进入 ERL Configuration，当前启用 5 个默认维度 | 查看 Tab 栏 | 显示 FRL、PRL、BERL、RRL、TRL 五个 Tab，Tab 数量等于当前已配置维度数 |
| | | | 依次点击各维度 Tab | 每个 Tab 展示对应维度的题库，题目内容不串页 |
| | | | 新增一个维度 GRL 后再次查看 Tab 栏 | Tab 数量增加为 6，新增 GRL Tab 可正常切换 |
| TC-020 | 题库按 Era Band 分组显示 | FRL 维度题库覆盖 Founder Era-1 至 Exit Era-9 | 在 FRL Tab 中查看题库结构 | 题目按 Era Band 分组显示（Founder Era-1、Founder Era-2、Founder Era-3 等），与原型稿一致 |
| | | | 核对每组内题目数量与顺序 | 与配置数据一致，分组标题清晰可辨 |
| TC-021 | 通过 Add New 添加新题目 | 在 FRL Tab 的 Founder Era-1 分组 | 点击 Add New | 弹出新增题目表单，含题干、Era Band、Source 字段 |
| | | | 输入题干「是否已完成上一财年审计」，Era Band 选择 Founder Era-1，Source 选择 SharePoint，并确认 | 新题目添加到 Founder Era-1 分组末尾，字段与输入一致 |
| | | | 查看 Publish 按钮状态 | Publish 按钮由置灰变为激活 |
| TC-022 | 添加题目必填校验（反向） | 已打开 Add New 表单 | 题干留空，直接确认 | 提示题干为必填，无法保存 |
| | | | 填写题干但不选择 Era Band，确认 | 提示 Era Band 为必填，无法保存 |
| | | | 填写题干与 Era Band 但不选择 Source，确认 | 按需求校验规则提示 Source 必填或允许留空，行为与定义一致，不产生脏数据 |
| TC-023 | 编辑题目的题干、Era Band 与 Source | FRL 的 Founder Era-2 中存在题目 Q5 | 点击 Q5 的编辑入口，将题干修改为「是否已建立季度滚动预测」并保存 | 题干更新成功，列表显示新题干 |
| | | | 将 Q5 的 Era Band 由 Founder Era-2 改为 Founder Era-3 并保存 | Q5 从 Founder Era-2 分组移动到 Founder Era-3 分组 |
| | | | 将 Q5 的 Source 由 Looking Glass 改为 GSV Assessment 并保存 | Source 更新成功，Publish 按钮保持激活 |
| TC-024 | 删除题目 | FRL 的 Founder Era-1 分组含 3 道题目 | 删除其中第 2 题并确认 | 该题从列表移除，分组剩余 2 题，顺序自动衔接无空位 |
| | | | 查看 Publish 按钮状态 | Publish 按钮激活 |
| | | | Publish 后进入 Founder Flow 查看该分组 | 已删除题目不再出现，题目总数同步减少 |
| TC-025 | Era Band 内拖拽重排 | FRL 的 Founder Era-1 题目顺序为 Q1、Q2、Q3 | 将 Q3 拖拽到 Q1 之前 | 顺序变为 Q3、Q1、Q2，界面即时反映新顺序 |
| | | | 查看 Publish 按钮状态 | Publish 按钮激活 |
| | | | 尝试将 Q3 拖拽到另一个 Era Band 分组内 | 按需求约束仅支持 Era Band 内重排，跨组拖拽被拒绝或按定义处理，不产生错误数据 |
| TC-026 | 重排顺序即评估必答顺序（联动） | 承接 TC-025，已将 FRL Founder Era-1 顺序改为 Q3、Q1、Q2 并 Publish | 进入 Founder Flow 的 FRL 维度 | Founder Era-1 题目按 Q3、Q1、Q2 顺序显示，必答顺序与配置一致 |
| | | | 进入 GSV Flow 的 FRL 维度 | 顺序同为 Q3、Q1、Q2，两侧流程一致 |
| TC-027 | Publish 按钮激活条件 | 已进入 ERL Configuration，无任何未保存变更 | 在 FRL Tab 新增一道题目 | Publish 按钮激活 |
| | | | 刷新页面丢弃变更后，改在 PRL Tab 拖拽重排一道题目 | Publish 按钮激活（任意维度有新顺序即激活） |
| | | | 刷新页面丢弃变更后，改在 TRL Tab 编辑一道题目的题干 | Publish 按钮激活（任意维度有新编辑内容即激活） |
| | | | 刷新页面丢弃变更后，改为新增一个维度 | Publish 按钮激活（有新增维度即激活） |
| | | | 刷新页面丢弃变更后，改为 Deactivate 一个已 Publish 的维度 | Publish 按钮激活（维度启用状态变更即激活） |
| TC-028 | 无变更时 Publish 按钮不激活（反向） | 刚进入 ERL Configuration，未做任何修改 | 查看 Publish 按钮状态 | Publish 按钮置灰不可点击 |
| | | | 仅在五个 Tab 之间切换浏览，不做修改 | Publish 按钮仍保持置灰 |
| | | | 编辑一道题目后又将其改回原值 | 按需求定义，若内容与已发布版本一致则 Publish 保持置灰或提示无实际变更 |
| TC-029 | Publish 保存为新版本并可追溯 | 当前题库为版本 V1，已在 FRL 新增一题 | 点击 Publish | 提示发布成功，题库保存为新版本 V2 |
| | | | 查看版本信息 | 显示当前生效版本为 V2，V1 记录仍可追溯 |
| | | | 进入 Founder Flow 查看题库 | 新一轮评估使用 V2 题库，含新增题目 |
| TC-030 | 题目顺序变更对进行中与历史评估的影响 | 某 Founder 用户已保存进度但未提交（基于 V1 题库）；另有一条基于 V1 的历史提交记录 | 管理员在 Configuration 中重排该维度题目顺序并 Publish 为 V2 | 发布成功 |
| | | | 该 Founder 用户回到未提交的评估表 | 按需求定义处理进行中评估（沿用 V1 或提示题库已更新），已作答内容不丢失（需求 TBD，处理策略待确认） |
| | | | 打开基于 V1 的历史提交记录 | 历史记录保持提交时的题目顺序与答案，不被新版本改写 |
| TC-031 | 题干输入边界（边界） | 已打开 Add New 表单 | 输入 1 个字符的题干并保存 | 按校验规则保存成功或提示最小长度限制 |
| | | | 输入超长题干（如 1000 字符）并保存 | 按上限截断或提示超出限制，列表展示不破版 |
| | | | 输入含特殊字符与中英混排的题干并保存后查看 Founder Flow | 题干按纯文本原样显示，无乱码、无脚本执行 |

### 二、ERL 卡片与公司概览导航

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-032 | DI 卡片下移至 FI 卡片下方且入口保留 | 以 Portfolio Manager 登录，进入一家已有 DI 历史评分的公司 Company Overview 页 | 滚动页面定位 FI 卡片 | FI 卡片正常显示，其下方紧邻显示 DI 卡片 |
| | | | 查看 DI 卡片内容 | DI 卡片保留改版前的概览信息与打分，数值与改版前一致 |
| | | | 点击 DI 卡片的详情入口 | 成功跳转至 DI 详情页，DI 全部历史数据可正常查看，未被删除 |
| TC-033 | ERL 卡片替代原 DI 位置并展示完整聚合内容 | 已有 Founder 与 GSV 双方本季度提交记录的公司 Company Overview 页 | 查看原 DI 卡片所在位置 | 该位置显示 ERL 卡片，为原型 Example 2 的单卡片形态 |
| | | | 依次核对卡片内展示项 | 卡片内同时展示 Composite Score、当前 Stage、Gap Analysis & Suggested Actions 摘要、5 个 ERL 维度列表、BPMM 分数、5 维度雷达图 |
| | | | 核对 5 维度列表每行内容 | 每行显示维度名称（FRL/PRL/BERL/RRL/TRL）、该维度分数、该维度 Perception Gap |
| TC-034 | 综合分数按权重配置加权计算（公式验证） | Weight Configuration 已配置 FRL=30%、PRL=25%、BERL=15%、RRL=15%、TRL=15%；GSV 维度分数为 FRL=6、PRL=4、BERL=7、RRL=5、TRL=3；公式 Composite = Σ(维度分 × 权重) | 打开该公司 Company Overview 页，查看 ERL 卡片 Composite Score | 显示 5.5/9（计算：6×0.30+4×0.25+7×0.15+5×0.15+3×0.15 = 1.8+1.0+1.05+0.75+0.45 = 5.5） |
| TC-035 | 权重变更后综合分数同步刷新 | 维度分数同 TC-034（6/4/7/5/3） | 进入 ERL Configuration，将权重改为 FRL=50%、PRL=20%、BERL=10%、RRL=10%、TRL=10% 并保存 | 权重保存成功，提示保存完成 |
| | | | 返回 Company Overview 页刷新，查看 Composite Score | 显示 5.3/9（计算：6×0.50+4×0.20+7×0.10+5×0.10+3×0.10 = 3.0+0.8+0.7+0.5+0.3 = 5.3），综合分随权重实时重算 |
| TC-036 | 维度分数取连续全 Yes 的最后一个 Level（公式验证） | FRL 维度评估中 Founder Era-1、Founder Era-2 全部回答 Yes，Founder Era-3 中存在一个 No；公式 维度分 = 回答 No 的 Level − 1 | 提交该 FRL 评估后查看 ERL 卡片 FRL 分数 | FRL 显示 2 分（计算：No 出现在 Level 3，3−1=2） |
| TC-037 | 九个层级全部 Yes 得满分 9（边界） | PRL 维度 9 个 Level 的全部题目均回答 Yes | 提交该 PRL 评估后查看 ERL 卡片 PRL 分数 | PRL 显示 9 分（9 级全 Yes 时得分为 9） |
| TC-038 | 第一个 Level 即出现 No 得 0 分（边界） | BERL 维度 Founder Era-1 中第一题回答 No | 提交该 BERL 评估后查看 ERL 卡片 BERL 分数 | BERL 显示 0 分（计算：1−1=0），页面不报错、不显示负数或空白 |
| TC-039 | Perception Gap 计算与正负号语义（公式验证） | 本季度 FRL：Founder=6、GSV=4；PRL：Founder=3、GSV=7；公式 Gap = Founder 分 − GSV 分 | 查看 ERL 卡片 FRL 行的 Perception Gap | FRL Gap 显示 +2（计算：6−4=2），正值表示创始人自评更高 |
| | | | 查看 ERL 卡片 PRL 行的 Perception Gap | PRL Gap 显示 −4（计算：3−7=−4），负值表示 GSV 评分更高 |
| TC-040 | Perception Gap 为 0 的展示（边界） | RRL：Founder=5、GSV=5 | 查看 ERL 卡片 RRL 行的 Perception Gap | 显示 0，不显示 +0 或 −0，无差异样式提示 |
| TC-041 | 单侧未提交时 Perception Gap 展示（边界） | 本季度仅 Founder 已提交 TRL 评估，GSV 尚未提交 | 查看 ERL 卡片 TRL 行 | TRL 显示 Founder 分数，Perception Gap 显示为空值或「—」，不按 0 计算、不报错 |
| TC-042 | 不设独立 Exit Readiness 落地页 | 以 Portfolio Manager 登录 | 检查全局顶部导航与左侧菜单 | 无独立的 Exit Readiness 落地页菜单项 |
| | | | 在地址栏直接输入 Exit Readiness 落地页路径并访问 | 页面不存在或重定向回 Company Overview，不出现独立落地页 |
| TC-043 | 卡片内每维度 View Details 跳转对应 Score Details 页 | ERL 卡片已展示 5 个维度 | 点击 FRL 行的 View Details | 跳转到 FRL 维度 Score Details 页，页面标题为 Financial Readiness (FRL) |
| | | | 返回卡片，依次点击 PRL、BERL、RRL、TRL 的 View Details | 分别跳转到对应维度的 Score Details 页，维度名称与所点击行一致，无串页 |
| TC-044 | 维度页返回路径保留面包屑 | 已从 ERL 卡片进入 FRL 维度 Score Details 页 | 查看页面顶部面包屑 | 显示 Exit Readiness › Financial Readiness (FRL) |
| | | | 点击面包屑中的 Exit Readiness | 返回 Company Overview 页 ERL 卡片位置 |
| | | | 进入 TRL 维度页并查看面包屑 | 显示 Exit Readiness › Talent Readiness (TRL)，维度名称随参数变化 |
| TC-045 | ERL 卡片对可访问 Company Overview 的角色开放 | 分别准备 Company User、Company Admin、Portfolio Manager、Portfolio Group Manager 四个账号 | 用 Company User 登录并进入 Company Overview | 可见 ERL 卡片，仅展示自身（Founder）分数 |
| | | | 用 Company Admin 登录并进入 Company Overview | 可见 ERL 卡片 |
| | | | 分别用 Portfolio Manager、Portfolio Group Manager 登录并进入 Company Overview | 均可见 ERL 卡片，且可见 GSV 侧分数与 portfolio 专属信息 |
| TC-046 | 无任何评估数据时 ERL 卡片空状态（边界） | 一家新建公司，Founder 与 GSV 均无任何 ERL 提交记录 | 进入该公司 Company Overview 页查看 ERL 卡片 | 卡片正常渲染，Composite Score 与各维度分数显示为「—」或空状态文案，Stage 不显示错误值，雷达图显示空状态而非报错 |
| | | | 点击任一维度的 View Details | 可正常进入维度页，页面显示暂无评估记录的空状态与 + New 入口 |
| TC-047 | ERL 卡片 Gap Analysis 摘要与 BPMM 展示 | 双方均已提交且存在 Perception Gap 的公司 | 查看 ERL 卡片 Gap Analysis & Suggested Actions 摘要区 | 显示 Goldie 生成的差距摘要（需求 TBD，待细化呈现方案） |
| | | | 查看 ERL 卡片 BPMM 区域 | 显示 BPMM 参考分数，取值在 1–5 范围内（需求 TBD，待细化规则） |

### 三、维度详情页（Score Details）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-048 | 5 个维度共用同一模板并由 dimension 参数驱动 | 5 个维度均已有本季度提交记录 | 依次通过 View Details 进入 FRL、PRL、BERL、RRL、TRL 五个维度页 | 五个页面布局结构完全一致（头部信息、Tab、元数据栏、题目列表、View history 与 + New 入口位置相同） |
| | | | 对比五个页面的标题与数据 | 仅维度名称、题目总数、分数、题目内容随维度变化，无重复维护造成的样式或字段差异 |
| TC-049 | 维度页头部展示维度名称、题目总数与维度综合分数 | FRL 维度题库共 9 题，本季度 FRL 得分为 4 | 进入 FRL 维度 Score Details 页，查看头部 | 显示维度名称 Financial Readiness (FRL)、题目总数 9、该维度综合分数 4 |
| TC-050 | 题目列表显示 Era-level 标签与得分 | FRL 维度题库覆盖 Founder Era-1 至 Exit Era-9 | 查看题目列表每一行 | 每题显示对应的 Era-level 标签（如 Founder Era-1、Harvest & Growth Era-5、Exit Era-9）与该题得分/答案 |
| | | | 核对标签与 Configuration 中该题的 Era Band 配置 | 标签与 Configuration 配置完全一致 |
| TC-051 | 元数据栏字段完整性 | 该维度本季度由 Founder 用户于 2026-07-15 提交 | 查看页面元数据栏 | 依次显示 Period（Q3 2026）、Submitted By（提交人姓名）、Role（提交人角色）、Submitted At（2026-07-15） |
| TC-052 | GSV 用户 Founder / GSV Tab 切换与数据隔离 | 以 Portfolio Manager 登录，该维度 Founder 与 GSV 均已提交且答案不同 | 进入该维度页，查看 Tab 区域 | 同时显示 Founder 与 GSV 两个 Tab，默认选中其中一个 |
| | | | 点击 Founder Tab | 显示 Founder 提交的答案、备注与元数据 |
| | | | 点击 GSV Tab | 切换为 GSV 提交的答案、备注与元数据，数据与 Founder Tab 不混淆 |
| TC-053 | 公司用户不显示 GSV Tab（反向） | 以 Company User 登录，该维度 GSV 侧已有提交 | 进入该维度 Score Details 页 | 页面不显示 GSV Tab，仅展示 Founder 自身数据 |
| | | | 尝试通过 URL 参数直接请求 GSV Tab 数据 | 请求被拒绝或回退到 Founder 视图，不泄露 GSV 分数 |
| TC-054 | 创始人不显示 GSV 专属字段（反向） | 以 Company User 登录；该公司已接入 Benchmarkit 与 Top GSV Quartile 静态数据 | 进入任一维度 Score Details 页并通篇查看 | 页面不出现 Benchmarkit、Top GSV Quartile 等 GSV 专属字段 |
| | | | 改用 Portfolio Manager 登录进入同一维度页 | 可见 Benchmarkit、Top GSV Quartile 等 GSV 专属字段 |
| TC-055 | View history 入口跳转限定当前维度的历史 | FRL 维度本季度有 2 次提交，PRL 维度有 1 次提交 | 在 FRL 维度页点击 View history | 跳转到 Assessment History 页，列表仅显示 FRL 维度的提交记录，共 2 条 |
| | | | 返回后进入 PRL 维度页并点击 View history | 列表仅显示 PRL 维度的 1 条记录，不混入 FRL 记录 |
| TC-056 | + New 入口按角色进入对应评估流程 | 分别准备 Company User 与 Portfolio Manager 账号 | 以 Company User 在 FRL 维度页点击 + New | 进入 FRL 维度的 Founder Flow 评估表 |
| | | | 以 Portfolio Manager 在 FRL 维度页点击 + New | 进入 FRL 维度的 GSV Flow 评估表 |
| TC-057 | 维度详情页响应式 | 同一维度页有完整提交数据 | 在 1920×1080 桌面分辨率打开页面 | 布局完整，题目列表与元数据栏无横向滚动条 |
| | | | 切换到 375×812 移动端视口 | 页面自适应，Tab、元数据栏、题目列表纵向堆叠可读，操作入口可点击 |
| TC-058 | 该维度尚无提交时的空状态（边界） | RRL 维度从未有过任何提交 | 进入 RRL 维度 Score Details 页 | 显示暂无评估记录的空状态文案，题目总数与分数显示为空或 0，元数据栏为空，不报错 |
| | | | 查看页面入口按钮 | + New 入口可用；View history 入口不可用或点击后显示无历史记录 |

### 四、Founder Flow（创始人评估流程）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-059 | Company User / Company Admin 从 Assessments 区块进入 Founder Flow | 以 Company User 登录公司自身 portal，ERL Configuration 已发布题库 | 进入 Assessments 区块 | 显示 ERL 评估入口 |
| | | | 点击 ERL 评估入口 | 进入 Founder Flow 评估表，表单可编辑 |
| | | | 改用 Company Admin 登录并重复上述操作 | 同样可进入 Founder Flow 评估表 |
| TC-060 | Portfolio Admin 不能代填 Founder 评估（反向） | 以 Portfolio Manager 登录 portfolio portal | 在该公司页面查找 Founder Flow 填写入口 | 无 Founder Flow 填写入口，仅有 GSV Flow 入口 |
| | | | 尝试通过 URL 直接访问该公司的 Founder Flow 表单 | 访问被拒绝并提示无权限，不能代替公司用户填写或提交 |
| TC-061 | 评估期选择器默认值与切换 | 当前日期为 2026-09-08（Q3 2026） | 进入 Founder Flow 并查看顶部评估期选择器 | 默认显示当前季度 Q3 2026 |
| | | | 展开评估期选择器 | 可选季度列表正常展开，含 Q3 2026 与其他季度 |
| | | | 选择 Q2 2026 | 评估期切换为 Q2 2026，表单归属该季度，提交后记录 Period 为 Q2 2026 |
| TC-062 | 题库同步自 ERL Configuration 并按 5 维度 3 Era 分组 | ERL Configuration 中 FRL 维度已发布 9 题，覆盖 3 个 Era | 进入 Founder Flow 查看整体结构 | 表单按 FRL、PRL、BERL、RRL、TRL 五个维度组织 |
| | | | 展开 FRL 维度 | 该维度内按 Founder Era（Stage 1–3）、Harvest & Growth Era（Stage 4–6）、Exit Era（Stage 7–9）三组显示 |
| | | | 逐题核对题干与来源标签 | 题干、Era Band、Source 与 ERL Configuration 中已发布版本完全一致 |
| TC-063 | 必答顺序与 Configuration 拖拽顺序一致 | ERL Configuration 中 FRL 的 Founder Era-1 题目顺序为 Q1、Q2、Q3 并已 Publish | 进入 Founder Flow 查看 FRL 的 Founder Era-1 题目顺序 | 题目按 Q1、Q2、Q3 顺序显示 |
| | | | 尝试跳过 Q1 直接回答 Q3 | 无法跳答，Q3 在 Q1、Q2 回答前不可操作或不可见 |
| TC-064 | Level 全部 Yes 后折叠显示 Check 并展开下一 Level | 进入 FRL 维度 Founder Flow，当前显示 Founder Era-1 题目 | 将 Founder Era-1 全部题目按顺序回答 Yes | Founder Era-1 自动折叠，标题行显示 Check 标记 |
| | | | 查看折叠后的页面 | 紧随其后显示 Founder Era-2 的题目，且此时不显示 Founder Era-3 及之后的 Level |
| | | | 将 Founder Era-2 全部题目回答 Yes | Founder Era-2 折叠并显示 Check，随后显示 Founder Era-3 题目 |
| TC-065 | 出现 No 回答后停止展开后续 Level 并激活提交按钮 | FRL 的 Founder Era-1、Era-2 已全部回答 Yes，当前显示 Founder Era-3 | 在 Founder Era-3 中任选一题回答 No | 该 Level 不再要求继续，且不显示 Harvest & Growth Era 及之后的任何 Level |
| | | | 查看提交按钮状态 | 提交按钮由置灰变为激活可点击 |
| | | | 点击提交并查看 FRL 得分 | 提交成功，FRL 得分为 2（计算：No 所在 Level 3 − 1 = 2） |
| TC-066 | 9 个层级全部答完且全 Yes 时激活提交 | PRL 维度题库覆盖完整 9 个 Level | 依次将 9 个 Level 的全部题目回答 Yes | 每个 Level 全 Yes 后依次折叠并显示 Check，直至第 9 个 Level 答完 |
| | | | 查看第 9 个 Level 答完后的页面与按钮 | 无后续 Level 可展开，提交按钮激活 |
| | | | 提交并查看 PRL 得分 | PRL 得分为 9 |
| TC-067 | 当前 Level 未答完时提交按钮置灰（反向） | 进入 BERL 维度 Founder Flow，Founder Era-1 共 3 题 | 仅回答 Founder Era-1 的第 1 题为 Yes | 提交按钮保持置灰不可点击 |
| | | | 回答第 2 题为 Yes，仍留第 3 题未答 | 提交按钮仍置灰，页面提示当前 Level 尚未完成 |
| | | | 回答第 3 题为 No | 提交按钮激活 |
| TC-068 | 已答 Yes 改为 No 后后续 Level 收起（交互完整性） | FRL 的 Founder Era-1、Era-2 已全 Yes 并折叠，当前显示 Founder Era-3 | 展开已折叠的 Founder Era-2 | 该 Level 展开且答案可修改 |
| | | | 将 Founder Era-2 中一题由 Yes 改为 No | Founder Era-2 的 Check 标记消失，Founder Era-3 及之后的 Level 立即收起 |
| | | | 查看提交按钮与预计得分 | 提交按钮保持激活，得分预期为 1（计算：2−1=1） |
| TC-069 | 将 No 改回 Yes 后重新展开下一 Level（双向验证） | 承接 TC-068，Founder Era-2 中存在一题为 No | 将该题由 No 改回 Yes | Founder Era-2 重新折叠并显示 Check |
| | | | 查看页面后续内容 | Founder Era-3 重新显示，题目为未回答状态，流程可继续向下推进 |
| TC-070 | 每题证据/备注可选填并保留 | 进入 FRL 维度 Founder Flow | 在第 1 题回答 Yes 但不填写证据/备注，直接进入下一题 | 允许留空，无必填校验拦截 |
| | | | 在第 2 题的证据/备注中输入「2026 Q2 审计报告已完成，见附件」 | 文本正常录入并保存 |
| | | | 提交后进入该维度 Score Details 页查看第 2 题 | 该题证据/备注内容完整显示，与录入一致 |
| TC-071 | 每题显示来源标签 | ERL Configuration 中 FRL 题目分别配置了 Founder/CTO、Looking Glass、SharePoint 三种 Source | 进入 Founder Flow 查看 FRL 各题的来源标签 | 每题均显示来源标签，取值与 Configuration 配置一致 |
| TC-072 | 创始人全程不可见 GSV 分数（反向） | 以 Company User 登录，该公司本季度 GSV 侧已提交且分数与 Founder 不同 | 通篇查看 Founder Flow 表单 | 表单内无任何 GSV 答案、GSV 分数或 GSV 备注 |
| | | | 提交后查看 Company Overview 的 ERL 卡片与维度页 | 仅显示 Founder 自身分数，不暴露 GSV 分数 |
| TC-073 | 保存进度后稍后继续且无数据丢失 | 进入 FRL 维度 Founder Flow | 回答 Founder Era-1 全部题目为 Yes，并在其中一题填写备注「已完成月度对账」 | 答案与备注正常录入 |
| | | | 点击保存进度并退出登录 | 提示保存成功，未生成提交记录 |
| | | | 重新登录并回到该评估表 | Founder Era-1 保持全 Yes 折叠状态与 Check 标记，备注完整保留，当前展开位置为 Founder Era-2 |
| TC-074 | 提交后表单即只读 | FRL 维度 Founder 评估已提交 | 再次进入该次提交的详情视图 | 全部答案、备注均为只读展示，无可编辑控件 |
| | | | 尝试修改任一题答案 | 无法修改，页面无编辑入口 |
| | | | 查看修改途径 | 页面提供 + New 入口，提示如需修改需新建一次提交 |
| TC-075 | 同季度多次提交且最新一次为 source of truth | Q3 2026 的 FRL 评估已提交一次，得分为 2 | 通过 + New 在 Q3 2026 再次填写 FRL，答案调整为 Founder Era-3 全 Yes、Harvest & Growth Era-4 出现 No，并提交 | 提交成功，生成第二条独立记录 |
| | | | 查看 ERL 卡片与维度页的 FRL 分数 | 显示 3 分（计算：No 所在 Level 4 − 1 = 3），以最新一次提交为准 |
| | | | 进入 Assessment History 查看 Q3 2026 记录 | 两条提交记录均完整保留并可区分，最新一条被标识为 source of truth |
| TC-076 | 提交记录含日期、评估人、基金/组合并进入历史 | 以 Company User（姓名 Zhang Wei）于 2026-09-08 提交 FRL 评估，公司隶属 GSV Fund II | 提交完成后进入 Assessment History | 新增一条记录，含提交日期 2026-09-08、评估人 Zhang Wei、所属基金/组合 GSV Fund II |
| | | | 核对记录的 Portal 字段 | Portal 显示为 Founder |
| TC-077 | Founder Flow 响应式 | 已进入 Founder Flow 评估表 | 在 1920×1080 桌面分辨率填写表单 | 维度、Era 分组、题目与 Yes/No 控件布局完整，无横向滚动 |
| | | | 切换到 375×812 移动端视口并完成一个 Level 的作答 | 题目纵向堆叠可读，Yes/No 控件与备注输入框可正常操作，折叠与 Check 效果正常 |
| TC-078 | 证据/备注输入边界（边界） | 进入 FRL 维度 Founder Flow 任一题的备注输入框 | 输入 1 个字符并保存 | 保存成功 |
| | | | 输入超出字数上限的超长文本（如 5000 字符）并保存 | 按上限截断或提示超出限制，不出现保存失败或页面崩溃 |
| | | | 输入特殊字符与 emoji 混排文本（含 <script>alert(1)</script>）并保存后查看详情页 | 内容按纯文本原样存储与展示，脚本不被执行，中文与 emoji 显示正常 |
| | | | 清空备注内容后保存 | 允许清空，该题备注为空且不影响提交 |

### 五、GSV Flow（GSV 团队评估流程）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-079 | PM / PGM 按 portfolio 公司进入 GSV Flow | 以 Portfolio Manager 登录 portfolio portal，权限范围含公司 A 与公司 B | 进入 Assessments 区块 | 显示按 portfolio 公司组织的 ERL 评估入口列表，含公司 A 与公司 B |
| | | | 选择公司 A 并进入 GSV Flow | 进入公司 A 的 GSV Flow 评估表，页面标明当前评估对象为公司 A |
| | | | 改用 Portfolio Group Manager 登录并重复操作 | 同样可进入 GSV Flow 评估表 |
| TC-080 | GSV 题库与 Founder 完全一致 | ERL Configuration 已发布题库，FRL 共 9 题、PRL 共 9 题 | 在 GSV Flow 中查看 FRL 维度的题目总数、题干与 Era 分组 | 与 Founder Flow 中的 FRL 完全一致（题目数、题干、Era Band、题目顺序均相同） |
| | | | 依次核对其余 4 个维度 | 5 个维度的题库、Era 分组与打分标度均与 Founder Flow 一致 |
| TC-081 | GSV 侧 Level 递进与计分逻辑一致 | 进入公司 A 的 GSV Flow，PRL 维度 | 将 PRL 的 Founder Era-1、Era-2、Era-3 全部回答 Yes | 三个 Level 依次折叠并显示 Check，随后显示 Harvest & Growth Era-4 |
| | | | 在 Harvest & Growth Era-4 中一题回答 No | 停止展开后续 Level，提交按钮激活 |
| | | | 提交后查看 GSV 侧 PRL 分数 | 显示 3 分（计算：4−1=3），与 Founder Flow 计分规则一致 |
| TC-082 | GSV 每题来源标签可选取值 | 进入公司 A 的 GSV Flow 任一题 | 展开该题的来源标签选择器 | 可选项包含 Looking Glass、SharePoint、GSV Assessment、Board Transcripts / Fireflies |
| | | | 选择 Board Transcripts / Fireflies 并提交 | 选择成功，提交后在 Score Details 页该题显示所选来源标签 |
| TC-083 | 每个维度均可提交附件 | 进入公司 A 的 GSV Flow | 在 FRL 维度上传附件 FRL_evidence.pdf | 上传成功，附件名与大小正确显示在 FRL 维度下 |
| | | | 依次在 PRL、BERL、RRL、TRL 各上传一个附件 | 5 个维度均支持附件上传，各维度附件互不混淆 |
| | | | 删除 PRL 维度已上传的附件 | 删除成功，该维度附件列表更新，其余维度附件不受影响 |
| TC-084 | 附件同步写入公司 Memory File | 承接 TC-083，已在 5 个维度分别上传附件并提交 | 进入该公司 Memory File 查看文件列表 | 5 个维度的附件均已同步写入公司 Memory File，文件名与上传一致 |
| | | | 检查 Goldie 可读取的数据源 | 上述附件在 Goldie 分析可用的数据源中可见 |
| TC-085 | GSV 评估期选择器 | 当前日期为 2026-09-08 | 进入公司 A 的 GSV Flow 并查看评估期选择器 | 默认显示 Q3 2026 |
| | | | 切换为 Q2 2026 并提交 | 提交记录的 Period 为 Q2 2026，不影响 Q3 2026 已有记录 |
| TC-086 | GSV 保存进度可恢复 | 进入公司 A 的 GSV Flow，BERL 维度 | 回答 Founder Era-1 全部题目为 Yes，上传一个附件并填写备注，点击保存进度 | 提示保存成功，未生成提交记录 |
| | | | 退出后重新进入该评估表 | 答案、备注、附件均完整保留，当前进度定位到 Founder Era-2 |
| TC-087 | GSV 提交后只读与同季多次提交 | 公司 A 的 Q3 2026 GSV 评估已提交一次 | 再次进入该次提交详情 | 全部内容只读，无编辑入口 |
| | | | 通过 + New 在 Q3 2026 再次提交一份不同答案的 GSV 评估 | 提交成功，生成第二条独立记录 |
| | | | 查看 Scorecard 的 GSV 分数与 Assessment History | Scorecard 采用最新一次提交的分数；History 中两条记录均保留并可区分 |
| TC-088 | Portfolio Admin 可为权限范围内任意公司完成/更新 GSV 评估 | 以 Portfolio Manager 登录，权限范围含公司 A、公司 B、公司 C | 为公司 A 完成并提交 GSV 评估 | 提交成功，记录归属公司 A |
| | | | 切换到公司 B 完成并提交 GSV 评估 | 提交成功，记录归属公司 B，公司 A 数据不受影响 |
| | | | 对公司 A 再次提交一份更新后的 GSV 评估 | 更新成功，公司 A 的 GSV 分数以最新提交为准 |
| TC-089 | 无法访问权限范围外公司的 GSV 评估（反向） | 以 Portfolio Manager 登录，公司 D 不在其权限范围内 | 在 Assessments 区块的公司列表中查找公司 D | 列表中不出现公司 D |
| | | | 通过 URL 直接访问公司 D 的 GSV Flow | 访问被拒绝并提示无权限，无法查看或提交 |
| TC-090 | GSV Flow 响应式 | 已进入公司 A 的 GSV Flow | 在 1920×1080 桌面分辨率填写表单并上传附件 | 布局完整，附件区与来源标签选择器可正常操作 |
| | | | 切换到 375×812 移动端视口 | 题目、来源标签、备注、附件上传控件纵向堆叠可读可操作 |
| TC-091 | 附件上传边界（边界） | 进入公司 A 的 GSV Flow FRL 维度附件区 | 上传超出大小上限的文件 | 提示文件超出大小限制，上传被拒绝，页面不崩溃 |
| | | | 上传不支持的文件格式（如 .exe） | 提示不支持该格式，上传被拒绝 |
| | | | 不上传任何附件直接提交评估 | 允许提交，附件非必填 |
| | | | 在同一维度连续上传多个附件 | 多附件均上传成功并在该维度列表中完整显示 |

### 六、ERL Scorecard 与 Radar Chart

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-092 | 综合 ERL 分数以 X/9 形式显示 | 综合分计算结果为 5.5 | 打开 Scorecard 查看综合 ERL 分数 | 显示为 5.5/9 形式，含分母 9，不显示百分比或裸数字 |
| TC-093 | Stage 与 Era 映射关系 | 分别构造综合分数为 2、5、8 的三家公司 | 查看综合分 2 的公司 Scorecard | Stage 显示 2，Era 显示 Founder Era |
| | | | 查看综合分 5 的公司 Scorecard | Stage 显示 5，Era 显示 Harvest & Growth Era |
| | | | 查看综合分 8 的公司 Scorecard | Stage 显示 8，Era 显示 Exit Era |
| TC-094 | Era 边界值验证（边界） | 分别构造综合分数为 3、4、6、7 的四家公司 | 查看综合分 3 的公司 | Stage 3 归属 Founder Era（Era 上界含 3） |
| | | | 查看综合分 4 的公司 | Stage 4 归属 Harvest & Growth Era（Era 下界含 4） |
| | | | 查看综合分 6 的公司 | Stage 6 归属 Harvest & Growth Era |
| | | | 查看综合分 7 的公司 | Stage 7 归属 Exit Era，边界切分与 Workbook 定义一致 |
| TC-095 | 分数达到 6 时进入 Harvest & Growth Era 提示 | 某公司综合分数为 6.0 | 查看该公司 Scorecard 的 Stage 与 Era 展示 | Stage 显示 6，Era 显示 Harvest & Growth Era，表示公司已进入该纪元、可开始接触投行 |
| TC-096 | Scorecard 展示项完整性 | 以 Portfolio Manager 登录，双方均已提交的公司 | 查看 Scorecard 全部展示项 | 依次显示综合 ERL 分数、当前 Stage 与 Era、每维度 GSV 分数、每维度 Perception Gap |
| | | | 改用 Company User 登录查看同一 Scorecard | 显示综合分、Stage 与 Era、每维度 Founder 分数，不显示 portfolio 专属信息 |
| TC-097 | 雷达图同图呈现四条线 | 该公司已有 Founder 与 GSV 提交，且已接入 Benchmarkit 与 Top GSV Quartile 静态数据 | 以 Portfolio Manager 打开雷达图 | 同一张图上呈现四条线：Founder 自评、GSV 评估、Benchmarkit、Top GSV Quartile |
| | | | 核对图例 | 图例列出四条线的名称，与线条颜色一一对应 |
| TC-098 | Benchmarkit 与 Top GSV Quartile 为静态外部数据 | 已接入的 Benchmarkit 数据为 FRL=5、PRL=6、BERL=5、RRL=6、TRL=5 | 记录当前雷达图上 Benchmarkit 线的取值 | 与静态数据源取值一致 |
| | | | 提交一次新的 Founder 与 GSV 评估后重新打开雷达图 | Founder 与 GSV 两条线随新提交变化，Benchmarkit 与 Top GSV Quartile 两条线保持不变，不参与平台内部计算 |
| TC-099 | 雷达图图形规范 | 雷达图已渲染四条线 | 查看各线条的填充效果 | 仅显示线条，无区域填充 |
| | | | 查看四条线的颜色 | 四条线颜色互不相同，可清晰区分 |
| | | | 查看图表中心与坐标轴 | 中心轴隐藏，符合 Workbook 规范 |
| | | | 查看图例存在性 | 图例存在且可读 |
| TC-100 | 5 个顶点对应 5 个 ERL 维度并标注 | 雷达图已渲染 | 查看图形顶点数量与标注 | 共 5 个顶点，分别明确标注 FRL、PRL、BERL、RRL、TRL |
| | | | 核对某一顶点的数值与 Scorecard 中该维度分数 | 顶点位置对应的数值与 Scorecard 中同维度分数一致 |
| TC-101 | 悬停数据点显示维度与 perspective 精确分数 | 雷达图上 GSV 线在 FRL 顶点的分数为 4 | 将鼠标悬停在 GSV 线的 FRL 数据点上 | 显示提示框，含维度名称 FRL、perspective 名称 GSV、精确分数 4 |
| | | | 移动悬停到 Benchmarkit 线的 PRL 数据点 | 提示框切换为 PRL 维度、Benchmarkit perspective 及其精确分数 |
| | | | 移开鼠标 | 提示框消失，图形恢复原状 |
| TC-102 | 图例点击显隐单条线（交互完整性） | 雷达图已渲染四条线 | 点击图例中的 Benchmarkit | Benchmarkit 线从图中隐藏，图例项呈置灰态 |
| | | | 再次点击图例中的 Benchmarkit | Benchmarkit 线恢复显示，图例项恢复正常态 |
| | | | 依次隐藏三条线仅保留 Founder 线 | 图形正常渲染单条线，不报错、不变形 |
| TC-103 | 雷达图仅在 Portfolio 端显示 | 同一家公司，分别以 Portfolio Manager 与 Company User 登录 | 以 Portfolio Manager 查看 Scorecard 与 ERL 卡片 | 雷达图正常显示 |
| | | | 以 Company User 查看 Scorecard 与 ERL 卡片 | 不显示雷达图，页面布局无空白错位 |
| TC-104 | BPMM 仅显示 1–5 参考数字 | 该公司 BPMM 参考分数为 3 | 查看 Scorecard 的 BPMM 区域 | 显示 3，取值落在 1–5 范围内 |
| | | | 尝试点击 BPMM 分数或查找 BPMM 评估入口 | 无完整 BPMM 评估交互入口，仅作参考数字展示（需求 TBD，本 story 范围外） |
| TC-105 | 从 Scorecard 访问历史评估记录 | 该公司有 Q1 2026、Q2 2026、Q3 2026 三个季度的提交 | 在 Scorecard 上点击历史评估记录入口 | 进入 Assessment History，三个季度的记录均可见 |
| | | | 打开 Q1 2026 的记录 | 显示该季度提交时的分数与题级答案，可回看往期 |
| TC-106 | 架构预留新增 perspective 能力 | 在配置/数据层新增第 5 条 perspective 数据（如 Industry Median） | 打开雷达图 | 新 perspective 线正常渲染，图例新增对应项，其余四条线显示不受影响 |
| | | | 悬停新增线的数据点 | 提示框正确显示该 perspective 名称与分数 |
| TC-107 | 雷达图与 Scorecard 数据边界（边界） | 构造三种数据：五维度分数全部相同（均为 5）、五维度分数全部为 0、仅 Founder 侧有数据 | 查看五维度分数均为 5 的雷达图 | 图形呈规则五边形，正常渲染 |
| | | | 查看五维度分数均为 0 的雷达图 | 线条收缩至中心，图形不报错、不消失，Scorecard 综合分显示 0.0/9 |
| | | | 查看仅 Founder 侧有数据的雷达图 | Founder 线正常渲染，GSV 线缺失但不报错，Perception Gap 显示为空 |
| TC-108 | Scorecard 响应式 | Scorecard 与雷达图均有完整数据 | 在 1920×1080 桌面分辨率查看 | Scorecard 与雷达图并排或分区显示完整，无横向滚动 |
| | | | 切换到 375×812 移动端视口 | Scorecard 各项与雷达图纵向堆叠自适应，雷达图顶点标注不重叠、可读 |
| TC-109 | 跨视图视觉一致性 | 同一公司的 ERL 卡片、Scorecard、Portfolio ERL Tab 均有数据 | 对比三处同一维度（如 FRL）的标签与配色 | 维度名称、缩写、配色在三处保持一致 |
| | | | 对比 Founder 与 GSV 两个视图中同一维度的颜色与样式 | 两个视图间维度配色、Gap 正负值样式保持一致 |

### 七、Gap Analysis 与 Suggested Actions（Goldie，需求 TBD）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-110 | 存在 Perception Gap 时生成差距分析与建议 | 某公司 PRL：Founder=7、GSV=3（Gap=+4），双方均已填写证据/备注 | 打开 Scorecard 的 Gap Analysis & Suggested Actions 区域 | 针对 PRL 生成差距分析，指出双方感知差距并给出可执行的行动建议（需求 TBD，待细化生成逻辑） |
| | | | 核对建议内容与 Gap 维度的对应关系 | 建议聚焦在存在差距的 PRL 维度，未对无差距维度强行生成差距叙述 |
| TC-111 | 双方分数均低于目标时生成建议 | 某公司 RRL：Founder=2、GSV=2（Gap=0），均低于目标 Stage | 查看 RRL 的 Gap Analysis 内容 | 尽管无 Perception Gap，仍针对分数偏低生成建议，识别 Workbook 中尚未满足的准则（需求 TBD） |
| TC-112 | 双方均高分且无实质差距时承认为公司优势 | 某公司 FRL：Founder=8、GSV=8 | 查看 FRL 的 Gap Analysis 内容 | Goldie 将 FRL 表述为公司优势，不套用差距叙述、不虚构改进项 |
| TC-113 | 建议引用 Workbook 准则与双方证据/备注 | GSV 在 BERL 某题备注「品牌资产未做第三方估值」，Workbook 中该 Stage 要求已定义 | 查看 BERL 的 Gap Analysis 内容 | 建议引用该证据/备注上下文，并指向 Workbook 中尚未满足的具体准入准则（需求 TBD） |
| TC-114 | 建议为指导性且结合公司具体情境 | 某公司已有完整评估与备注数据 | 阅读生成的建议文案 | 文案说明「可以做什么」以及「为何相关」，内容结合该公司具体情境，非通用模板化建议（需求 TBD） |
| TC-115 | MVP 不含跟踪、指派与 Deadline（反向） | Gap Analysis 已生成建议列表 | 在建议项上查找任务跟踪、指派负责人、设置 Deadline 等控件 | 均不存在，建议仅为指导性内容，不可被指派或跟踪 |
| TC-116 | Founder 视角口吻 | 以 Company User 登录 | 查看 Gap Analysis 的建议文案 | 文案采用「你可以做什么…」的第二人称口吻，面向创始人（需求 TBD，prompt 待定义） |
| TC-117 | GSV 视角口吻 | 以 Portfolio Manager 登录，查看同一公司同一维度 | 查看 Gap Analysis 的建议文案 | 文案采用「我们建议这家公司…」的口吻，面向 GSV 团队（需求 TBD，prompt 待定义） |
| TC-118 | 新评估提交后分析自动刷新 | 某公司 TRL：Founder=3、GSV=6，Gap Analysis 已生成对应内容 | 记录当前 TRL 的分析文案 | 文案已生成并可读 |
| | | | 由 Founder 在同季度新提交一次 TRL 评估，得分改为 6 | 提交成功，TRL Gap 变为 0 |
| | | | 回到 Scorecard 查看 TRL 的 Gap Analysis | 分析自动刷新，反映最新数据与新的 Gap 值，不残留旧结论 |
| TC-119 | 展示位置在 Scorecard 视图内 | 双方均已提交的公司 | 在 Scorecard 视图内查找 Gap Analysis | Gap Analysis inline 展示于每个维度旁或作为独立面板出现在 Scorecard 视图内，不需跳转其他页面 |
| TC-120 | Gap Analysis 响应式 | Gap Analysis 已生成内容 | 在 1920×1080 桌面分辨率查看 | 文案与维度对应关系清晰，布局完整 |
| | | | 切换到 375×812 移动端视口 | 内容自适应换行、可完整阅读，不出现截断或溢出 |
| TC-121 | MVP 备选：GSV vs. Founder 分数对比 Tab | 某维度 Founder 与 GSV 在多题答案不一致 | 在该维度 Score Details 页查看是否存在 GSV vs. Founder 分数对比 Tab | 若已实现该 MVP 方案，则显示该 Tab（需求 TBD，是否采用待确认） |
| | | | 打开该 Tab | 突出显示 Founder 与 GSV 差距最大的题目，按差距大小排序（需求 TBD） |
| TC-122 | 无任一方提交数据时 Gap Analysis 空状态（边界） | 一家 Founder 与 GSV 均未提交的公司 | 查看 Scorecard 的 Gap Analysis 区域 | 显示空状态文案（如需完成评估后生成分析），不生成虚构建议、不报错 |

### 八、Portfolio ERL Tab（组合级评估看板）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-123 | Company List 页新增 ERL Tab | 以 Portfolio Manager 登录，进入某 Portfolio 的 Company List 页 | 查看页面 Tab 栏 | 显示 ERL Tab，与 General、Connections、Issues、Benchmarking 并列 |
| | | | 点击 ERL Tab | 切换到 ERL 表格视图，其余 Tab 状态与功能不受影响 |
| TC-124 | 不做独立看板页（反向） | 以 Portfolio Manager 登录 | 检查全局导航与 Portfolio 菜单 | 无独立的 Portfolio ERL 看板页入口 |
| | | | 在地址栏直接访问独立看板页路径 | 页面不存在或重定向到 Company List 的 ERL Tab |
| TC-125 | ERL Tab 表格列完整性 | 该 Portfolio 下有 5 家公司均有 ERL 数据 | 查看 ERL Tab 表格表头 | 依次显示 Company、ERL Score、FRL、PRL、BERL、RRL、TRL、Stage、View 九列 |
| | | | 核对任一行的数据 | 该公司综合分、5 个维度分数、Stage 与其 Scorecard 页数据一致 |
| TC-126 | 按 ERL Score 排序 | ERL Tab 中 5 家公司综合分分别为 2.0、4.5、5.5、7.0、8.5 | 点击 ERL Score 列表头一次 | 按综合分升序排列，顺序为 2.0、4.5、5.5、7.0、8.5 |
| | | | 再次点击 ERL Score 列表头 | 切换为降序排列，顺序为 8.5、7.0、5.5、4.5、2.0 |
| TC-127 | 按 Stage 排序与筛选 | 5 家公司 Stage 分别为 2、4、5、7、8 | 点击 Stage 列表头进行排序 | 按 Stage 升序/降序正确排列 |
| | | | 使用 Stage 筛选器选择 Harvest & Growth Era（4–6） | 仅显示 Stage 为 4 与 5 的两家公司 |
| | | | 追加选择 Exit Era（7–9） | 显示 Stage 为 4、5、7、8 的四家公司，多选条件正确叠加 |
| TC-128 | 按单个维度分数排序与筛选 | 5 家公司的 FRL 分数分别为 1、3、5、7、9 | 点击 FRL 列表头排序 | 按 FRL 分数正确升序/降序排列 |
| | | | 使用维度筛选器筛选 FRL 大于等于 5 的公司 | 仅显示 FRL 为 5、7、9 的三家公司 |
| | | | 切换为筛选 TRL 维度 | 筛选条件切换到 TRL 生效，FRL 筛选条件按交互定义被替换或叠加，结果正确 |
| TC-129 | 多筛选条件组合联动 | 该 Portfolio 下有 10 家公司，数据覆盖不同 Stage 与维度分数 | 同时设置 Stage 为 4–6、FRL 大于等于 5 | 结果为同时满足两个条件的公司集合 |
| | | | 在此基础上再叠加 ERL Score 大于等于 5 的条件 | 结果进一步收窄为同时满足三个条件的公司，列表实时刷新 |
| | | | 在筛选结果上点击 ERL Score 列排序 | 排序在筛选结果范围内生效，不重新引入被筛掉的公司 |
| TC-130 | 清空筛选条件恢复全量（取消操作） | 承接 TC-129，已应用三个筛选条件 | 逐个取消已选筛选条件 | 每取消一个条件，列表相应扩大，结果实时刷新 |
| | | | 点击清空全部筛选 | 恢复显示该 Portfolio 下全部 10 家公司，排序恢复默认 |
| TC-131 | View 跳转到该公司 Score Details | ERL Tab 表格已加载 | 点击公司 A 行的 View | 跳转到公司 A 的 Score Details 页面 |
| | | | 返回后点击公司 B 行的 View | 跳转到公司 B 的 Score Details 页面，无跳错公司 |
| TC-132 | ERL Tab 权限控制 | 分别准备 Portfolio Manager、Portfolio Group Manager、Company User、Company Admin 账号 | 以 Portfolio Manager 与 Portfolio Group Manager 分别登录查看 Company List | 均可见并可访问 ERL Tab |
| | | | 以 Company User 与 Company Admin 分别登录 | 不可见 ERL Tab；通过 URL 直接访问被拒绝并提示无权限 |
| TC-133 | 组合内公司无 ERL 数据时的展示（边界） | 该 Portfolio 下公司 E 从未有任何 ERL 提交 | 在 ERL Tab 中查看公司 E 所在行 | ERL Score、5 个维度分数、Stage 均显示为「—」或空值，不显示 0 导致误读，行不消失 |
| | | | 点击公司 E 行的 View | 正常进入其 Score Details 页并显示空状态 |
| | | | 对含空值的列执行排序 | 空值行统一排在末尾（或按既定规则），排序不报错 |

### 九、Assessment History（评估历史）

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-134 | 从维度 Score Details 页 View history 进入 | FRL 维度已有多次提交记录 | 在 FRL 维度 Score Details 页点击 View history | 进入 Assessment History 页，且范围限定为 FRL 维度 |
| | | | 查看页面标题与面包屑 | 明确标识当前为 FRL 维度的历史记录 |
| TC-135 | 列表字段完整性 | FRL 维度有一条 Q3 2026 的 Founder 提交，提交人为 Zhang Wei（Company Admin），完成度 45/45，综合分 5.5、Stage 5 | 查看 Assessment History 列表该行 | 依次显示 Period（Q3 2026）、Portal（Founder）、Submitted By（Zhang Wei / Company Admin）、Completion（45/45）、Overall Score（5.5，含 Stage 5 标签） |
| TC-136 | 同季度多次提交全部独立保留并可区分 | Q3 2026 的 FRL 维度由 Founder 先后提交 3 次，提交日期分别为 2026-07-10、2026-08-05、2026-09-01 | 查看 Assessment History 中 Q3 2026 的记录 | 显示 3 条独立记录，而非仅显示最新一条 |
| | | | 核对三条记录的日期与分数 | 三条记录的提交日期与各自分数均正确且互不覆盖 |
| | | | 分别打开三条记录 | 各记录内容对应其提交时的答案，互不混淆 |
| TC-137 | 最新提交标识为 source of truth | 承接 TC-136，Q3 2026 有 3 次提交 | 查看列表中最新一条（2026-09-01）的标识 | 明确标识为当前生效记录 / source of truth |
| | | | 对比 Scorecard 与 ERL 卡片展示的分数 | 与 2026-09-01 这条记录的分数一致 |
| TC-138 | 列表默认最近提交在前 | 存在 Q1 2026、Q2 2026、Q3 2026 共 5 条提交记录 | 首次进入 Assessment History 页 | 列表默认按提交时间倒序排列，最近提交在第一行 |
| | | | 从上往下核对全部记录时间 | 时间严格递减，无乱序 |
| TC-139 | 页面完全只读无编辑入口（反向） | Assessment History 已有多条记录 | 通篇检查列表页的操作控件 | 无编辑、删除、重新提交等编辑入口 |
| | | | 打开任一条记录详情并检查控件 | 详情页全部字段只读，无可编辑控件，无保存按钮 |
| | | | 尝试通过 URL 进入该提交的编辑态 | 请求被拒绝或回退为只读视图 |
| TC-140 | 点击记录打开该次提交详情并复用 Score Details 题级布局 | Q2 2026 的 FRL 提交中，Founder Era-1、Era-2 全 Yes，Era-3 出现 No，得分为 2 | 在 Assessment History 点击 Q2 2026 的记录 | 打开该次提交详情，布局与 Score Details 题级视图一致 |
| | | | 核对题级答案与备注 | 呈现该次提交当时的答案、备注与来源标签，得分显示 2 |
| | | | 核对元数据 | Period、Submitted By、Role、Submitted At 与该次提交时一致，不显示后续提交的数据 |
| TC-141 | Founder 与 GSV 两侧记录区分 | 同一维度 Q3 2026 有 Founder 提交 2 条、GSV 提交 1 条 | 查看 Assessment History 列表 | 共 3 条记录，Portal 列分别标识 Founder 与 GSV |
| | | | 按 Portal 筛选 GSV | 仅显示 1 条 GSV 记录 |
| | | | 以 Company User 登录查看同一页面 | 仅可见 Founder 侧记录，不可见 GSV 提交记录 |
| TC-142 | Completion 字段展示（边界） | 该维度题库共 45 题；存在一条 45/45 的完整提交，以及一条因 Level 出现 No 而提前结束的提交（实际作答 12 题） | 查看完整提交行的 Completion | 显示 45/45 |
| | | | 查看提前结束提交行的 Completion | 按实际作答题数显示（如 12/45），与 Level 递进规则一致，不误显示为未完成异常 |
| TC-143 | 无历史记录时空状态（边界） | 某维度从未有过任何提交 | 从该维度 Score Details 页进入 Assessment History | 显示无历史记录的空状态文案，列表区无空行、不报错 |
| TC-144 | Assessment History 响应式 | 列表已有多条记录 | 在 1920×1080 桌面分辨率查看 | 五个字段列完整显示，无横向滚动 |
| | | | 切换到 375×812 移动端视口 | 列表以卡片或纵向堆叠方式自适应，各字段可读，点击进入详情正常 |

### 十、全局规则、权限与响应式

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-145 | 权限模型全矩阵验证 | 准备 Company User、Company Admin、Portfolio Manager、Portfolio Group Manager 四个账号 | 以 Company User 与 Company Admin 分别登录，依次访问 ERL 卡片、维度页、Founder Flow、Scorecard、Assessment History | 均可访问；可填写 Founder Flow；不可见 GSV Tab、GSV 分数、雷达图、Portfolio ERL Tab、ERL Configuration |
| | | | 以 Portfolio Manager 与 Portfolio Group Manager 分别登录，依次访问同上页面及 GSV Flow、Portfolio ERL Tab、ERL Configuration | 均可访问；可填写 GSV Flow；可见 GSV 专属字段与雷达图；不可代填 Founder Flow |
| | | | 对每个角色尝试越权访问其不可见页面的 URL | 全部被拒绝并提示无权限，无数据泄露 |
| TC-146 | 数据保留：DI 数据不删除、历史评估完整保留 | 改版前该公司有 DI 历史评分与 8 条 ERL 历史提交 | 改版后查看 DI 卡片与 DI 详情 | DI 历史数据完整保留，未被删除或清空 |
| | | | 查看 Assessment History 记录条数 | 8 条历史提交全部保留，无丢失 |
| | | | 在 Configuration 中 Publish 新版本题库后再次查看历史记录 | 历史提交仍完整保留并保持原有题目与答案 |
| TC-147 | 全模块响应式巡检 | 各模块均有完整数据 | 在 1920×1080 桌面分辨率依次访问 ERL 卡片、维度页、Founder Flow、GSV Flow、Scorecard、Gap Analysis、Portfolio ERL Tab、Configuration、Assessment History | 全部页面布局完整，无元素重叠或横向滚动 |
| | | | 切换到 375×812 移动端视口重复上述访问 | 全部页面自适应可用，关键操作（作答、提交、筛选、拖拽重排、上传）均可在移动端完成 |
| | | | 切换到 768×1024 平板视口抽查 3 个页面 | 布局在中间断点正常过渡，无破版 |
| TC-148 | 导航一致性：面包屑保留于各维度页返回路径 | 5 个维度均有数据 | 依次从 ERL 卡片进入 5 个维度页并查看面包屑 | 每页均显示 Exit Readiness ›〔对应 Dimension Name〕 |
| | | | 从维度页进入 Assessment History 后返回 | 面包屑层级正确，可逐级返回至 Company Overview |
| | | | 从 Portfolio ERL Tab 的 View 进入 Score Details 页 | 面包屑保持 Exit Readiness ›〔Dimension Name〕结构，返回路径可用 |

### 十一、端到端全流程

| 编号 | 测试用例名称 | 前置条件 | 测试步骤 | 预期结果 |
|---|---|---|---|---|
| TC-149 | 全流程串联：配置 → 双方评估 → 计分 → 分析 → 组合看板 → 历史追溯 | 一家全新公司，无任何 ERL 数据；已有 Portfolio Manager 与 Company User 账号；Benchmarkit 与 Top GSV Quartile 静态数据已接入 | 以 Portfolio Manager 进入 ERL Configuration，为 5 个维度各配置 9 个 Level 的题目，设置权重 FRL=30%、PRL=25%、BERL=15%、RRL=15%、TRL=15%，点击 Publish | 题库与权重发布成功，保存为新版本 |
| | | | 以 Company User 进入 Assessments，选择 Q3 2026 完成 Founder Flow：FRL 在 Level 7 出现 No、PRL 在 Level 5 出现 No、BERL 在 Level 8 出现 No、RRL 在 Level 6 出现 No、TRL 在 Level 4 出现 No，填写备注后提交 | 提交成功，生成带日期记录；Founder 侧维度分数为 FRL=6、PRL=4、BERL=7、RRL=5、TRL=3 |
| | | | 以 Portfolio Manager 完成同一季度 GSV Flow：FRL 在 Level 5 出现 No、PRL 在 Level 6 出现 No、BERL 在 Level 6 出现 No、RRL 在 Level 5 出现 No、TRL 在 Level 5 出现 No，每维度上传一个附件后提交 | 提交成功；GSV 侧维度分数为 FRL=4、PRL=5、BERL=5、RRL=4、TRL=4；附件同步写入公司 Memory File |
| | | | 进入 Company Overview 查看 ERL 卡片与 Scorecard | Founder 综合分 5.5/9（计算：6×0.3+4×0.25+7×0.15+5×0.15+3×0.15=5.5），Stage 5、Harvest & Growth Era；Perception Gap 分别为 FRL +2、PRL −1、BERL +2、RRL +1、TRL −1 |
| | | | 查看雷达图 | 同图呈现 Founder、GSV、Benchmarkit、Top GSV Quartile 四条线，仅线条无填充、各线不同色、图例完整、中心轴隐藏，悬停显示精确分数 |
| | | | 查看 Gap Analysis & Suggested Actions | 针对存在差距的维度生成分析与建议，GSV 视角口吻为「我们建议这家公司…」（需求 TBD） |
| | | | 进入 Portfolio 的 Company List 页 ERL Tab | 该公司出现在表格中，ERL Score 5.5、5 个维度分数与 Stage 5 均与 Scorecard 一致 |
| | | | 点击该行 View 进入 Score Details，再点击 View history | 进入 Assessment History，显示本季度 Founder 与 GSV 各 1 条记录，字段完整、最近在前 |
| TC-150 | 同季度重复提交后全链路以最新为准 | 承接 TC-149 的数据状态 | 以 Company User 在 Q3 2026 再次提交 Founder Flow，将 FRL 改为 Level 9 全 Yes（得 9 分），其余维度不变 | 提交成功，生成第二条 Founder 记录 |
| | | | 查看 ERL 卡片、Scorecard、Portfolio ERL Tab 的 Founder 综合分与 FRL 分数 | 三处同步刷新：FRL 显示 9，Founder 综合分为 5.95/9（计算：9×0.3+4×0.25+7×0.15+5×0.15+3×0.15=2.7+1.0+1.05+0.75+0.45=5.95），Stage 显示 6、Era 显示 Harvest & Growth Era |
| | | | 查看 FRL 的 Perception Gap 与 Gap Analysis | Gap 更新为 +5（计算：9−4=5），Gap Analysis 自动刷新反映最新数据 |
| | | | 进入 Assessment History 查看 Q3 2026 | 两条 Founder 记录均完整保留，最新一条标识为 source of truth |
| TC-151 | 题库更新后新一轮评估生效且历史记录保持原状 | 承接 TC-150；当前题库版本为 V2 | 以 Portfolio Manager 在 Configuration 中为 FRL 新增一道 Level 9 题目并重排 Founder Era-1 顺序，Publish 为 V3 | 发布成功，版本更新为 V3 |
| | | | 以 Company User 通过 + New 发起新一轮 FRL 评估 | 新评估使用 V3 题库，含新增题目，Founder Era-1 按新顺序显示 |
| | | | 打开基于 V2 的历史提交记录 | 历史记录保持 V2 的题目集合、顺序与答案，不被 V3 改写 |
| | | | 查看该维度题目总数与 Score Details 头部 | 新提交的题目总数按 V3 计算，历史提交的题目总数仍按其提交时版本显示 |

---

