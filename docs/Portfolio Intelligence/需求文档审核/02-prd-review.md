# Benchmark Portfolio Intelligence PRD 审核报告

> 评审日期：2026-04-14
> 评审对象：Benchmark Portfolio Intelligence_需求文档.md（原始版本）
> 设计参考：Figma 原型截图 4 张（pics/1776129*.jpg）
> 已加载项目上下文：CLAUDE.md、CIOaas-web/config/routes.ts、CIOaas-api benchmark engine（PeerGroupResolver / InternalPercentileCalculator / ExternalPercentileCalculator / MetricExtractor）、CIOaas-web/src/pages/BenchmarkEntry/types.ts

---

## 一、评分仪表盘

| 维度 | 评分 | 说明 |
|------|------|------|
| 语义与表述 | 6/10 | 拼写错误（Gross Morgin）、Tooltip 描述嵌套不清、超范围处理条件交叉混乱、目录空悬条目 |
| 功能完整性 | 7/10 | 核心功能完整，但缺加载态/错误态、路由定义缺失、Trend 图表布局规则依赖设计稿但文档未记录 |
| 操作闭环 | 6/10 | Data/Benchmark 筛选器缺「至少选一」规则；分页交互未闭合；公司排序规则缺失 |
| 数据一致性 | 7/10 | 指标与现有 MetricExtractor 一致，但外部基准 FY Period 匹配模糊、ARR 无法确定时缺处理 |
| 权限覆盖 | 5/10 | 仅提"管理员用户"，未定义 roleType 映射、非管理员可见性 |
| 业务规则 | 7/10 | 百分位公式完整，但 Overall Score 聚合口径不明、超范围两种 Case 混写 |
| 编号与可追溯性 | 3/10 | 无 SC-xx / BR-xx / AC-xx 编号 |
| **综合** | **6/10** | **⚠️ 有条件通过 — 无 P0 阻塞，存在多项 P1 需修改或确认** |

---

## 二、评审通过项

- ✅ 核心使用流程覆盖：导航 → 选公司 → 配置筛选 → 查看 Snapshot/Trend 结果，与设计原型流程一致
- ✅ 6 个指标名称与后端 `MetricExtractor.MetricEnum` 完全对应
- ✅ Internal Peers 百分位公式 `P = (R-1)/(N-1) × 100` 与 `InternalPercentileCalculator.calculate()` 一致
- ✅ 外部基准线性插值公式与 `ExternalPercentileCalculator.interpolate()` 一致
- ✅ 同行匹配规则（Type + Stage + 会计方法 + ARR 规模 + 数据质量 + 排除条件）与 `PeerGroupResolver` 架构对应
- ✅ Peer Fallback 三级机制（手动绑定 → 系统匹配 → 全平台基准）与代码 `PeerGroupResult.isFallback` 一致
- ✅ Snapshot 表格结构与设计原型吻合：公司 → Benchmark 行 → DataType 子行 → Overall Score → 指标列（百分位+值）
- ✅ Trend 折线图按指标卡片分组、Y 轴 P0~P100、Hover 显示所有公司百分位 — 与设计原型一致
- ✅ 外部 Benchmark 显示 edition（设计中为 "KeyBanc - 2025" 格式）与 PRD 描述的 benchmark-edition 对应
- ✅ Data-Benchmark 排序规则（Benchmark 优先 → Data 次序）在 Trend 设计原型中得到验证

---

## 三、问题与建议

### 3.1 PRD 内部问题

| # | 问题分类 | 问题描述 | 严重程度 | 是否阻塞 | 修订类别 | 建议 |
|---|----------|----------|----------|----------|----------|------|
| 1 | 编号体系 | 全文无 SC-xx / BR-xx / AC-xx 编号，下游 TDD 和 QA 文档无法追溯 | P1 | 否 | 可自动修订 | 自动为场景、业务规则、验收标准添加编号 |
| 2 | 权限覆盖 | 仅提"管理员用户"，未定义 roleType 映射（系统中 admin = roleType ≤ 2）、非管理员可见性、菜单权限 | P1 | 否 | 需用户决策 | 补充权限矩阵 |
| 3 | 操作闭环 | Data 筛选器（多选标签）未定义「至少选一」约束及全部取消后行为 | P1 | 否 | 需用户决策 | 建议：至少保留一个选中项 |
| 4 | 操作闭环 | Benchmark 筛选器（多选复选框）未定义「至少选一」约束及全部取消后行为 | P1 | 否 | 需用户决策 | 建议：至少保留一个选中项 |
| 5 | 业务规则 | Overall Score "该行中4-N列所有列的百分位的算术平均值"：未明确 "行" = 公司 × Benchmark × DataType 的哪个粒度 | P1 | 否 | 需用户决策 | 设计原型表明每行 = 一个 DataType 子行，Overall Score 应为该子行内所有指标百分位的算术平均 |
| 6 | 数据一致性 | 外部基准匹配 "对应正确年份" 的 FY Period 判定规则缺失 | P1 | 否 | 需用户决策 | 需明确：选中月份的日历年度 or 公司财年 |
| 7 | 功能完整性 | 缺少页面路由/导航入口定义 — 设计原型显示为 Portfolio 详情页的 "Benchmarking" tab | P1 | 否 | 需用户决策 | 从设计原型看，路由应为 Portfolio 内的 tab（如 `/portfolio/:id/benchmarking`） |
| 8 | 功能完整性 | 缺少加载态（Loading）、API 错误态、部分数据缺失的降级展示 | P2 | 否 | 可自动修订 | 补充标准三态描述 |
| 9 | 语义与表述 | 指标名 "Gross Morgin" 拼写错误 → "Gross Margin" | P2 | 否 | 可自动修订 | 自动修正 |
| 10 | 语义与表述 | 目录含 "指标卡片与详情展示" 但正文无此章节 | P2 | 否 | 可自动修订 | 删除空悬条目 |
| 11 | 业务规则 | 超范围处理中 "三点齐全但超范围" 与 "点位不齐全的推断规则" 混为一段 | P2 | 否 | 可自动修订 | 拆分为两个子节，用表格呈现 |
| 12 | 语义与表述 | Tooltip 描述嵌套过深，难以转化为 UI 实现 | P2 | 否 | 可自动修订 | 改写为结构化格式 |
| 13 | 功能完整性 | Snapshot 表格公司排序规则未定义 | P2 | 否 | 需用户决策 | 建议按公司名 A-Z |
| 14 | 业务规则 | Trend 视图 "无数据展示 P0" 可能误导用户 | P2 | 否 | 需用户决策 | 建议：折线断开或用虚线+特殊标记 |
| 15 | 数据一致性 | "六个维度" 实际为 4 个匹配维度 + 2 项过滤条件 | P2 | 否 | 可自动修订 | 修正表述 |
| 16 | 功能完整性 | 日期选择器可选范围限制缺失 | P2 | 否 | 需用户决策 | 建议：最早 = 平台最早数据月；最晚 = 当前月 |
| 17 | 数据一致性 | "全平台基准" 概念未定义 — 回退后基准池范围 | P2 | 否 | 需用户决策 | 建议：全平台活跃公司，仍排除 Exited/Shut Down/Inactive |
| 18 | 语义与表述 | "benchmark-edition" 首次出现未解释含义 | P2 | 否 | 可自动修订 | 补充说明：来自 BenchmarkEntry 的 edition 字段 |
| 19 | 业务规则 | Monthly Runway 特殊分类逻辑（TOP_RANK/BOTTOM_RANK/WORST_NEGATIVE_ZERO）在代码中已实现但 PRD 未记录 | P2 | 否 | 需用户决策 | 建议补充到业务规则 |

### 3.2 PRD 与设计原型的差异

| # | 差异点 | PRD 描述 | 设计原型实际 | 严重程度 | 建议 |
|---|--------|----------|-------------|----------|------|
| D1 | 公司筛选器标签 | "Companies" | 设计中显示为 "Company" + 下拉箭头 | P2 | 以设计为准，统一为 "Company" |
| D2 | Trend 折线图每行数量 | 未定义 | 设计显示为一行 2 个图表 | P1 | 补充到 PRD："Trend 视图折线图每行最多 2 个，从左到右排列" |
| D3 | 外部基准提示条 | 未提及 | Trend 视图顶部有蓝色提示条："External Benchmarks: Industry Survey distribution and metric definitions may vary. Use for directional context only." | P2 | 补充到 PRD |
| D4 | Tooltip 弹窗结构 | 描述模糊 | 设计显示为：指标名 → 每百分位（P0/P25/P50/P75/P100）对应百分比值和实际值 | P1 | 按设计稿改写 Tooltip 结构 |
| D5 | Overall Score 显示格式 | "35%ile" | 设计显示为 "11% ile"（百分号后有空格） | P2 | 统一格式描述 |
| D6 | Trend hover tooltip | "显示所有公司在该月份的百分位值和百分位对应的数值" | 设计显示格式为："月份标题 → 公司名: P值"（如 "Accelerist: P100"），按百分位降序排列 | P1 | 按设计稿精确描述 tooltip 格式 |
| D7 | 分页规格 | "每页最多十家公司" | 设计显示 "1-10 of 192 items" + 页码选择器 + "10/page" 下拉 | P2 | 补充分页组件细节（每页条数可选、总条数显示） |
| D8 | Trend 外部基准选中状态 | 未特殊说明 | 设计中选中外部基准（KeyBanc）时有外部基准提示条，未选中时无提示 | P2 | 补充条件显示逻辑 |

---

### 表述与歧义问题

| # | 位置（章节/段落） | 原文摘录 | 问题类型 | 建议改写 |
|---|------------------|----------|----------|----------|
| T1 | 快照视图-第三列 | "Overall benchmark score:显示为例如：35%ile，数据值为该行中4-N列所有列的百分位的算术平均值" | 歧义 | "Overall Benchmark Score：该公司在当前 Benchmark × DataType 子行中，所有已选指标列百分位的算术平均值（N/A 不参与），格式如 `11%ile`" |
| T2 | 快照视图-第二列 | "tooltip中显示所有指标名称，及该指标的三种数据类型在该月的所有百分位及百分位对应的实际值" | 详略失当 | 按设计原型改写为：Tooltip 结构 = 指标名称标题 → P0 [百分比] [值] / P25 [百分比] [值] / P50 ... / P75 ... / P100 ...，按已选 DataType 分组显示 |
| T3 | 超范围处理-第3点 | "若百分位点位不齐全...大于P25，则展示＞P25，计算时用P50；..." | 重复啰嗦 | 拆分为两表：表A = 三点齐全超范围规则；表B = 点位缺失推断规则 |
| T4 | 同行定义-维度5 | "从closed month开始往前数24个日历月内" | 理解缺口 | 未说明 "closed month" 定义来源（系统全局 or 公司级） |
| T5 | 筛选条件-Data | 仅描述三个选项和默认值 | 不闭环 | 缺多选交互规则：至少选一？是否有 "All"？全部取消时行为？ |
| T6 | 数据格式 | "百分位取整，货币值无缩写两位小数..." | 详略失当 | 建议按指标逐一列出：指标名 → 单位 → 格式 → 是否反向 |

---

## 四、待确认事项

| # | 问题 | 需要谁确认 | 是否阻塞后续设计 |
|---|------|-----------|----------------|
| Q1 | 页面路由：设计原型显示为 Portfolio 详情页 "Benchmarking" tab（与 General / Connections / Issues 同级），路由建议 `/portfolio/:id` 下的 tab 切换，是否正确？ | 产品/前端 | 是 |
| Q2 | Data 和 Benchmark 筛选器是否「至少选一」？设计原型中未见全部取消的状态 | 产品 | 是 |
| Q3 | Overall Score 粒度确认：从设计原型看，每个 DataType 子行各自有 Overall Score，即粒度 = 公司 × Benchmark × DataType，对吗？ | 产品 | 是 |
| Q4 | 外部基准 FY Period 匹配：取选中月份的日历年度 or 公司财年？设计原型中 edition 显示为 "2025" | 产品 | 是 |
| Q5 | Trend 无数据月份处理：PRD 说展示 P0，但这可能误导用户；建议折线断开或特殊标记 | 产品/UX | 否 |
| Q6 | Monthly Runway 特殊分类（TOP_RANK/BOTTOM_RANK/WORST_NEGATIVE_ZERO）已在代码中实现，是否正式纳入 PRD？ | 产品 | 否 |
| Q7 | 分页器是否支持切换每页条数？设计原型中显示有 "10/page" 下拉 | 产品 | 否 |

---

## 五、假设（待验证）

- 假设 Portfolio Intelligence 即为现有 Portfolio 详情页（设计中 "Barragon Fund I" 的 General/Connections/Issues/Benchmarking tabs），本次新增 Benchmarking tab
- 假设 roleType ≤ 2 的管理员可访问此页面，其他角色隐藏此 tab
- 假设外部基准 FY Period 取选中月份的日历年度进行匹配（设计原型 edition 为年份如 "2025"）
- 假设 "全平台基准"（Peer Fallback）= 所有活跃公司（排除 Exited/Shut Down/Inactive）
- 假设现有 `benchmark` 包 engine 类可直接复用
- 假设 Overall Score 粒度 = 公司 × Benchmark × DataType 的单行内所有指标百分位均值
- 假设 Trend 折线图每行最多 2 个（基于设计原型观察）

---

## 六、建议补充到 PRD 的内容

- **验收标准**：需添加 AC-xx 编号的可验收条件，覆盖 Snapshot 查看、Trend 查看、空状态、Peer Fallback、筛选切换等核心路径
- **非功能需求**：
  - 性能：多公司 × 多月 × 多基准查询响应时间目标（建议 < 3s）
  - 兼容性：最低浏览器版本
- **设计稿对齐项**（从原型中提取但 PRD 未覆盖）：
  - Trend 视图折线图每行 2 个
  - 外部基准提示条（蓝色 info banner）的出现条件与文案
  - Snapshot Tooltip 的精确结构（按指标分组，每组列出 P0/P25/P50/P75/P100 及对应值）
  - Trend Hover Tooltip 的排序规则（按百分位降序列出所有公司）
  - 分页组件规格（总条数 + 页码 + 每页条数可选）
- **范围澄清**：
  - 本次是否包含数据导出功能？
  - 本次是否包含保存/分享对标配置？
  - Snapshot 表格是否支持按指标列排序？

---

## 七、评审结论

**⚠️ 有条件通过**

PRD 核心功能描述完整，与设计原型基本一致，与现有后端 benchmark engine 对齐良好。主要问题集中在：

1. **可追溯性缺失**（P1）：无编号体系，可通过自动修订解决
2. **交互边界未闭合**（P1）：Data/Benchmark 筛选器的「至少选一」规则需产品确认
3. **PRD 与设计稿未完全对齐**（P1/P2）：Trend 布局、Tooltip 结构、外部基准提示条等细节设计稿已定义但 PRD 未记录
4. **权限定义不足**（P1）：需补充角色权限矩阵

**无 P0 阻塞问题，可进入自动修订阶段。**

待用户确认 Q1-Q7 待确认事项后，执行自动修订（添加编号、修正拼写、补充设计稿对齐内容），然后进入下一步。
