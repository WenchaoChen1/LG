# 图表规则走 tool 获取（提示词瘦身）— 评估与方案

> 关联文档: [修复回路删除](./2026-07-04-chart-repair-removal-design.md) · [类型扩展](./2026-07-04-chart-types-expansion-design.md) · [图表契约](./2026-06-10-chat-chart-design.md)
> 状态: 已实施（2026-07-04，CIOaas-python `3682ccb`，285 passed）
> 提出（用户原话大意）: 类型/格式规则全写到系统提示词太多；画图规则改走 tool 获取，评估这种方式合不合适。

## 1. 评估结论：合适，但必须是「混合式」

方向正确。当前 `CHART_SECTION` 约 42 行（≈1.5k token），**每轮对话、两条取数轨都无条件全量进上下文**，其中大头是 22 行「类型怎么选」逐类型规则——这部分只在真要画图的轮次才有用，且随类型继续扩展（18 → 更多）还会膨胀。把它下放到工具，按需加载，是对的。

**关键技术事实（决定方案形态）**：给 LLM 的规则有三个放置层，token 成本完全不同：

| 层 | 何时进上下文 | 结论 |
|----|------------|------|
| 系统提示词 | 每轮，无条件 | 只留必须常驻的 |
| 工具 docstring（schema） | **也是每轮**（工具定义随每个请求下发） | ⚠️ 挪到这里**不省 token**，只是换个位置 |
| 工具**返回值** | 仅调用的轮次 | 大块规则放这里才真省 |

所以「画图走 tool 获取」的正确形态：**新工具的 docstring 只有一两句话，类型规则目录放在返回值里**。不能照搬 d818bd5（数据语义规则挪 tool docstrings）的做法——那次是为了「规则跟着工具走」的归属清晰，不是为省 token。

不适合「全搬」的部分：AI 必须**不调工具就知道**自己能画图、什么时候该画、以及数据红线——这些没有常驻提示词就永远不会触发画图/永远有编数风险。

## 2. 方案：stub 常驻 + guide 工具按需

### 2.1 CHART_SECTION 瘦身为 stub（~12 行，原 ~42 行）

保留（必须常驻）：
- 能力宣告 + fence 协议 + 格式模板（含占位符警告）
- 通用规则 3 行（columns[0] 分类轴、row 形状、type 可省略）
- **数据红线全文**（数字必须来自工具结果 / 缺数填 null 不填 0 / 真实 0 照填 / 没真实数据不出图）——安全规则，绝不下放
- 表/图二选一句
- **新增流程指令**（替换 22 行类型规则）：「简单 bar/line 可按通用规则直接画；**用其他类型前必须先调 `get_chart_guide` 取类型选择与列约定**，复杂类型（boxplot/combo/bubble/gauge/waterfall）写完 spec 后必须再调 `validate_chart` 复验」

移出（进 guide 工具返回值）：「类型怎么选」逐类型规则 22 行（趋势→line、桥→waterfall、boxplot 防滥用句、combo 列约定等）。

### 2.2 新工具 `get_chart_guide`

- `tools/v2/chart_guide_tool.py`（一 @tool 一文件），**无入参**（目录本身很小，不做按类型过滤——YAGNI），纯本地、无 ToolRuntime。
- docstring 一句话：「获取图表类型选择规则与各类型列约定（画非 bar/line 图前先调）」。
- 返回 `ChartGuideResult(ok, guide: str)`（`v2/dto/`，中文 description），`guide` 内容 = 从 `chart_prompt.py` 移出的逐类型规则文本（常量 `CHART_TYPE_GUIDE`，仍留在 chart_prompt.py——提示词资产统一位置，类型行继续由 `CHART_TYPES` 枚举生成，单点不变）。
- `metadata = {ui_label: ("Reading chart rules", "Read chart rules"), result_model: ChartGuideResult}`，登记 `TOOL_REGISTRY_V2`（5→6），重跑 `interface_doc.py` 再生成接口文档。

### 2.3 与 validate_chart 的分工（不合并）

`get_chart_guide` = 画前拿规则（教怎么写）；`validate_chart` = 写完验 spec（判对不对）。职责不同、调用时机不同，合并成"无参返回指南 / 有参校验"的双态 API 会让 schema 变含糊（spec 字段被迫可选），不合并。

## 3. 成本收益与风险

- **收益**：每轮常驻从 ~42 行降到 ~12 行；画图轮次 guide 响应 ~25 行 + 一次本地工具调用（在本就多轮工具调用的取数阶段，延迟增量可忽略）；类型继续扩展时**常驻提示词零膨胀**（只长 guide 返回值）。
- **诚实的折扣**：若模型侧对静态系统提示词有 prompt caching，常驻 42 行的真实边际成本本就打折——本方案的主要价值是**可扩展性与提示词整洁**，token 节省是次要收益。
- **风险与兜底**：AI 不调 guide 就画复杂图 → spec 大概率列约定错 → `validate_chart` 必须复验兜底（errors 会教正确格式）→ 仍漏则 fence 落地校验降级文本 → 前端占位符（见 [前端渲染校验方案](./2026-07-04-chart-frontend-render-validation-design.md)）终极兜底。四层防线下，规则后置的风险可控。

## 4. 改动面（全在 CIOaas-python）

| 位置 | 改动 |
|------|------|
| `prompts/chatbot/chart_prompt.py` | `_TEMPLATE` 拆两段：stub（CHART_SECTION）+ `CHART_TYPE_GUIDE`（逐类型规则，guide 工具数据源） |
| `tools/v2/chart_guide_tool.py` + `dto/chart_guide_result.py` | 新工具 + 返回模型 |
| `tools/v2/__init__.py` | 注册表 +1 |
| `docs/AI-Chatbot/chatbot-tools-v2-interface.md` | 再生成 |
| 测试 | guide 工具单测（返回含全部 18 类型名）、chart_prompt 测试改断言（stub 含红线/流程指令、不含逐类型行）、注册表契约测试自动覆盖新工具 |

前端零改动、协议零改动（LLM 仍只输出 type）。
