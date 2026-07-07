# 图表选型指导架构优化 — 方案（单源两渲染 + 参数化 guide）

> 关联文档: [入口与样式框架](./2026-07-04-chart-entry-and-style-framework-design.md) · [类型扩展](./2026-07-04-chart-types-expansion-design.md)
> 状态: **已全量回滚（2026-07-04）**——v1.2/v1.3 实验整体撤回，`chart_prompt` 恢复到 GitHub v1.1 原版（318fe74）：常驻最小 stub + `CHART_TYPE_GUIDE` 全文经 get_chart_guide 无参下发。用户决策依据：选型是**数据组驱动**的（前端按 format/suits/resolveType 依数据定型、AI 可省略 type），常驻提示词不教场景选型。本文档仅作决策过程记录。
> 问题（讨论中确认）: v1.1 把逐类型「场景规则+列约定」整体移入 `get_chart_guide` 后，AI 的**初始选型直觉**只能靠预训练常识+类型名单——精编偏好（如"类目多→treemap 而非 pie"）要调了工具才见到；且 guide 恒返 18 类全文，AI 往往只需要其中一两类。

## 1. 目标

1. AI 在**起意阶段**就对齐我们的选型偏好（不等调工具）；
2. 常驻提示词膨胀可控（类型继续扩展时近似零增长的性质尽量保住）；
3. **维护仍是单点**——加一个类型只在一个地方写它的场景短语和填写约定；
4. guide 返回聚焦（只取所需类型的说明书，省 token）。

## 2. 方案：一张结构化表，渲染成两种粒度

### 2.1 单一结构化源（新）

`prompts/chatbot/chart_prompt.py` 内把现在的 `CHART_TYPE_GUIDE` 大字符串改为**结构化表**（类型 → 两个字段），这是逐类型知识的唯一维护点：

```python
# 每类型一条：scene = 场景短语（速查用，≤12 字），detail = 详细约定（guide 用，含列约定/特殊字段/防滥用句）
_TYPE_GUIDE: dict[str, tuple[str, str]] = {
    "line":       ("趋势/随时间变化", "…"),
    "step_line":  ("阶梯状跳变(调价/headcount)", "…"),
    "treemap":    ("占比且类目多或名字长", "…"),
    "waterfall":  ("增减桥(现金流桥/利润桥)", "columns 恰 2 列[环节,增减值]…totals 数组…不许 null"),
    "boxplot":    ("分布五数概括", "仅当有现成分布统计量…绝不把时间序列当五数…"),
    ...  # 18 类全覆盖，契约测试强制
}
```

### 2.2 渲染一：常驻场景速查（进 CHART_SECTION，约 +3 行）

由表自动生成一行式速查，替代"AI 靠常识猜"：

```
类型速查（详细列约定用 get_chart_guide 取）：趋势→line·area·step_line；对比→bar·horizontal_bar；构成→stacked_bar·stacked_area；占比→pie·donut·treemap；多维评分→radar；相关性→scatter·bubble；数值矩阵→heatmap；增减桥→waterfall；分布→boxplot；单值站位→gauge
```

- 起意阶段即可选对方向；类型扩展时速查只涨几个字（场景短语），可接受。
- 展现样式风格段里已有的高频触发句（表/图二选一、量纲混杂→combo、数据点少→gauge 例外）**保持常驻不动**。

### 2.3 渲染二：`get_chart_guide` 参数化（改）

工具加可选参数 `types: Optional[list[str]]`：

- 传入（如 `["waterfall"]`）→ 只返回这些类型的 detail（typo/未知名返回错误提示 + 可用名单）；
- 缺省 → 返回全量（兼容现状）。
- docstring 更新："已从速查确定类型后，只传该类型名取列约定"。

### 2.4 流程指令（微调一句）

> 简单 bar/line 直接画；**其他类型：按速查定方向 → 调 `get_chart_guide(types=[...])` 取该类型列约定** → 照约定写 spec；复杂类型（boxplot/combo/bubble/gauge/waterfall）写完必须 `validate_chart` 复验。

## 2.5 常驻段逐行审计（能搬进工具的都搬，净零增长）

判定原则：**管"调工具之前"行为的必须常驻，管"之后"的可进工具**。审计结论：

- 必须留：能力宣告+fence 协议、格式模板行（含类型名单）、通用规则（bar/line 直接画的最小知识）、画图流程指令（引向工具的路标）、数据红线（覆盖不经工具的 bar/line 直接画路径）。
- 可动（约 -3~4 行）：①"图表前后保留正文叙述；一次可多图"（版面偏好）→ 搬进 guide 全量文本；②"表/图二选一"句 → 删（展现样式风格段常驻已有本体）；③ 缺数 null / 真 0 规则**本体保留**、前端行为解释细节压缩。

与速查行（+3 行）相抵 → **v1.2 常驻提示词净零增长**。

## 3. 为什么不是别的方案

- **全量搬回常驻（v1.0）**：类型扩展线性膨胀、每轮全付，已被否。
- **维持现状（v1.1）**：初始直觉不对齐 + guide 恒返全量，即本方案要修的两点。
- **速查也进工具**：起意阶段的冷启动问题回来（不知道偏好就不会想到查），否。
- 本方案的代价：常驻 +3 行左右（一次性，之后每类型 +几个字）——换初始选型对齐与 guide 聚焦返回，划算。

## 4. 改动面（纯后端提示词/工具层，前端零改动）

| 文件 | 改动 |
|------|------|
| `prompts/chatbot/chart_prompt.py` | `CHART_TYPE_GUIDE` 字符串 → `_TYPE_GUIDE` 结构化表 + 两个渲染函数（速查行 / 明细文本）；`CHART_SECTION` 拼入速查行与新流程指令；版本 bump 1.2 |
| `tools/chart_guide_tool.py` | 加 `types` 可选参数 + 未知名错误处理；docstring 更新 |
| `tools/dto/chart_guide_result.py` | 视需要加 `unknown_types` 字段（错误提示） |
| 测试 | 契约测试：表键集 == CHART_TYPES（少一类红）；速查行含全部场景短语；guide 传参/全量/未知名三路；CHART_SECTION 行数上限断言（防再膨胀） |

## 5. 不做 / 待定

- sql 轨是否补绑 guide+validate（独立决策，与本方案正交——不补则 sql 轨维持 bar/line）；
- kb 轨不画图，不涉及。
