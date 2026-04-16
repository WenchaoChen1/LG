# Benchmark Portfolio Intelligence 需求文档 — 审阅报告

**审阅文件**：Benchmark Portfolio Intelligence_需求文档.md
**审阅日期**：2026-04-13

---

## 【总体评估】

Needs Revision — 文档核心逻辑框架清晰，但存在**1处关键指标分类映射错误**、**2个目录章节内容缺失**、**日期默认值与已有功能不一致**，以及多处边界情况和交互细节未定义。

---

## 【文档完整性问题】

1. **目录中列出但正文中不存在的章节**：
   - 「指标卡片与详情展示」
   - 「特殊情况说明」

   两个章节在目录中有，正文中完全缺失，需补充或从目录移除。

2. **缺少访问权限说明**：文档未定义哪些管理端角色可访问此 Portfolio Intelligence Benchmarking 页面（是所有管理端用户，还是特定角色如 Portfolio Manager？）

3. **缺少空状态完整说明**：提到空状态显示 "To begin select a company"，但未说明此时筛选器区域的状态——是正常可操作，还是置灰锁定？

4. **缺少分页/滚动逻辑**：公司数量较多时，Snapshot 表格如何处理？无分页或滚动行为定义。

---

## 【语言与清晰度问题】

1. **功能概述第一句为无效套话**：
   > "Portfolio Intelligence Benchmark Comparison UI 为管理员用户提供 Portfolio 级别的多公司财务指标对标分析工具"

   仅是对标题的复述，建议删除，直接从"支持对标化的相对性能展示..."开始。

2. **使用流程第5步与功能模块详解重复**：仅是对后续章节内容的预告，无独立信息量，建议删除。

3. **Tooltip 内容描述不够精确**（第206行）：Benchmark 列 Tooltip 描述为"已选指标的已选数据类型的所有百分位"，未说明选择多个 Benchmark 时是否在 Tooltip 中区分 Benchmark 来源，缺少格式示例。

---

## 【逻辑一致性问题】

### ⚠️ 关键错误：Filter 指标分类映射错误

文档中 Filter 映射：

| Filter | 文档定义 |
|--------|---------|
| EFFICIENCY | Gross Margin、Sales Efficiency Ratio |
| MARGINS | Gross Margin |

与标准定义不符，正确映射应为：

| Filter | 正确定义 |
|--------|---------|
| GROWTH | ARR Growth Rate |
| EFFICIENCY | Gross Margin |
| MARGINS | Monthly Net Burn Rate、Monthly Runway |
| CAPITAL | Rule of 40、Sales Efficiency Ratio |

当前文档将 EFFICIENCY 和 MARGINS 都映射到了 Gross Margin，且 MARGINS 完全缺失 Monthly Net Burn Rate 和 Monthly Runway，需立即修正。

---

### 日期默认值与已有 Benchmark Company 功能不一致

- 文档 Snapshot 默认值："**当前月份**"
- 文档 Trend 默认值："**当前月份及之前5个月**"
- Benchmark Company 页面定义：默认使用 **"the last closed month"**（区分 Manual/Automatic 设置）

两个页面是否使用相同的日期默认逻辑，需确认统一。

---

### Overall Benchmark Score 计算缺少 N/A 处理规则

文档说明 Overall Benchmark Score = "所有百分位的算术平均值"，但未说明：
- 某指标无数据（N/A）时是否排除出分母？
- 某公司所有指标均无数据时显示什么？

建议参照 Benchmark Company 文档中 6.3.4 的处理规则对齐。

---

### 百分位计算逻辑位置不当

Internal Peers 百分位公式、同行匹配规则、外部基准插值逻辑全部塞在 Snapshot 视图章节下，但这些规则对 Trend 视图同样适用。建议抽出作为独立章节，避免读者误以为仅适用于 Snapshot。

---

## 【边界与异常覆盖缺失】

1. **Trend 视图数据缺失处理**：第336行"无数据时展示 P0"——折线是否连续显示（落到 P0 连接）还是断线？悬浮时 Tooltip 是否显示 NA？需与 Benchmark Company 文档对齐确认。

2. **Peer Fallback 的 UI 表现**：文档提到"显示 Peer Fallback 提示"，但未描述提示的具体位置（整行、整列，还是独立 Banner？）和文案内容。

3. **Trend 视图悬浮交互细节不完整**：
   - 只描述了"悬浮折线上的数据点显示所有公司的百分位值"，未说明具体 UI 形式（竖向网格线+浮窗，还是气泡？）
   - 多家公司数据点位置重叠时如何处理？

4. **Companies 全部取消选择时**：用户先选了公司再全部取消，页面如何返回空状态？是否有过渡动效或提示？

5. **Trend 超范围百分位的折线坐标处理**：文档未提及超范围时（>P75 或 <P25）折线点落在哪个坐标位置，需补充（参考：Benchmark Company 文档定义 >P75 落在 P100 坐标，<P25 落在 P0 坐标）。

---

## 【文案合规问题】

文档无文案合规章节，以下 UI 文案均未记录字符数：

| 文案元素 | 内容 | 类型 | 规定上限 |
|---------|------|------|---------|
| 页面标题 | "Benchmarking" | 页面标题 | 50字符 |
| 页面说明 | "Benchmark values are normalized for comparability..." | 说明文字 | 需界定 |
| 空状态提示 | "To begin select a company" | 提示文字 | 需界定 |
| Peer Fallback 提示 | 未定义 | 提示文字 | 需界定 |
| 折线图标题格式 | "[Data Type] - [Benchmark Source]" | 标签 | 30字符 |

---

## 【开发可行性问题】

1. **Snapshot 表格列顺序和列标题命名规则未定义**：文档说"列数取决于用户选择的指标分类和对标基准数量"，但未给出多个 Benchmark 时各指标列的排列顺序和列标题格式。

2. **筛选器默认值分散**：各筛选器默认值分散在各自说明末尾，建议在筛选条件区域开头集中列出默认值汇总表，方便开发实现初始化逻辑：

   | 筛选器 | 默认值 |
   |--------|--------|
   | Companies | 空（无默认选中） |
   | View | Snapshot |
   | Filter | All |
   | Data | Actuals |
   | Benchmark | Internal Peers |
   | 日期（Snapshot） | Last closed month |
   | 日期（Trend） | Last closed month 前推6个月 |

3. **External Benchmark 的 Segment Type 定义与其他文档冲突**：本文档说"Segment Type 是 ARR"，Benchmark Company 文档说"Segment Type 是数据年份"，两份文档定义不同，需确认哪个正确。

4. **Trend 视图文档深度与 Snapshot 不对等**：Snapshot 有详细的表格列定义、计算逻辑、Tooltip 说明；Trend 视图仅有基础描述，缺少对应的计算说明和交互细节，两个视图的文档深度应对齐。

---

## 【行业可行性问题】

✓ 无问题 — 多公司横向对标分析为 VC/PE 行业标准工具，功能设计符合行业惯例。

---

## 【建议修改项】

1. **【紧急】** 修正 Filter 指标映射表：EFFICIENCY → Gross Margin；MARGINS → Monthly Net Burn Rate、Monthly Runway；CAPITAL → Rule of 40、Sales Efficiency Ratio。

2. 确认 Snapshot/Trend 日期默认值是否采用 "last closed month" 逻辑（与 Benchmark Company 保持一致），并补充 Manual/Automatic 的区分说明。

3. 补充「指标卡片与详情展示」和「特殊情况说明」两个章节内容，或从目录中移除。

4. 补充 Overall Benchmark Score 的 N/A 排除规则（缺失指标不计入分母）。

5. 统一 "Benchmarkit.ai" 拼写（文档中写的是 "Benchmarkit"）。

6. 补充 Peer Fallback 的 UI 表现：位置、文案、触发范围（单列？整行？）。

7. 补充 Trend 视图折线悬浮交互的具体 UI 行为，以及超范围时折线坐标处理规则。

8. 补充访问权限：哪些管理端角色可见此页面。

9. 将百分位计算逻辑（Internal Peers 公式、同行匹配规则、外部基准插值）抽出为独立章节，供 Snapshot 和 Trend 共同引用。

10. 在筛选条件区域开头补充默认值汇总表，方便开发实现页面初始化逻辑。

11. 确认 Segment Type 字段的定义（"ARR 范围" vs "数据年份"），与 Benchmark Company 文档对齐。

12. 补充 Snapshot 表格列顺序和列标题命名规则。
