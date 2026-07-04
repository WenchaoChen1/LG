# 图表校验方案收敛：删除 SSE 修复回路，保留工具自查 + 降级 — 范围确认

> 关联文档: [图表契约](./2026-06-10-chat-chart-design.md) · [类型扩展](./2026-07-04-chart-types-expansion-design.md) · [数据格式设计](./2026-07-04-chart-data-format-design.md) · [总入口与样式框架](./2026-07-04-chart-entry-and-style-framework-design.md)
> 状态: 待用户确认范围（删除代码已提交 `458c270`，本地未推送；本文档确认保留 / 删除 / 修改 / 新增边界与目标流程）
> 决策来源: 用户拍板（2026-07-04，临上线）——修复回路嫌乱、非必须，删；只留 validate_chart 工具自查 + 失败降级文本

## 1. 决策与理由

上线前最值钱的是**简单可预测、出问题好排查**。原「非法 fence → LLM 一次性修复（成功改写落库 / 失败降级）」是锦上添花不是保命件：修复本身是 LLM 调用，有不确定性、坏图时流停顿 1–2s、多养一套提示词/枚举/测试。删除后收敛为干净两态：**合法出图 / 非法降级文本**，完全确定性。

坏图防线从「双防线」变为「单防线 + 兜底」：

| 防线 | 删除前 | 删除后（当前） |
|------|--------|----------------|
| 生成期自查 | validate_chart 工具（建议复杂类型先验） | **保留**，且拟升级为「复杂类型必须先验」（见 §6） |
| 解析期 | 校验失败 → haiku 修复 → 复验 → 数字子集闸门 | **删除**，校验失败直接降级文本 |
| 落库 | 修复成功会改写 buf 里的坏 fence | 恒存原文，绝不改写 |

## 2. 现状快照（2026-07-04，已核实）

- **删除已完成并提交**：CIOaas-python `458c270`（refactor(chart): remove SSE auto-repair loop, keep tool-side validation），工作区干净，**恰 1 笔未推送**（origin/sprint113 之上）。
- **残留检查通过**：`source/` + `tests/` 下 `repair_chart_spec` / `InvalidChartSegment` / `chart_repair` / `CHART_REPAIR` / `_replace_fence_in_buf` 五关键字**零命中**（其余 `repair` 命中均为无关既有代码：`json_repair` 三方库、text2sql SQL 重试）。
- **前端零改动**：修复回路是纯后端概念，CIOaas-web 无任何残留（SSE 事件契约本就没有 repair 类事件）。
- **测试已跑**：删除改动提交前 223 passed（另一会话执行记录）；若 §6.1 确认改 docstring，需再跑受影响测试。

## 3. 保留清单（不动）

### 后端（CIOaas-python）

| 部件 | 现状 |
|------|------|
| `ai/chatbotgraph/chart/spec.py` | 契约单点：18 类型 / 5 格式（`CHART_TYPES` + `TYPE_FORMAT`）、pydantic `ChartSpec`（type 建议性可选、style 透传）、按 format 分支校验（scatter 3 列 / bubble 4 列 / waterfall 2 列数值必填 / boxplot 五数单调不减 / gauge 0–100）、`parse_chart_spec` + `parse_chart_spec_verbose`（verbose 版专供 validate_chart 工具回喂错误摘要） |
| `ai/chatbotgraph/chart/fence_parser.py` | 流式围栏状态机（跨 chunk hold、未闭合回吐），两态产出 `TextSegment` / `ChartSegment` |
| `ai/chatbotgraph/chart/__init__.py` | 总入口 10 项导出；**包内现已全部纯逻辑（无 IO）**——repair.py 删除后「深路径例外」不复存在 |
| `ai/tools/v2/validate_chart_tool.py` + `ValidateChartResult` DTO | 生成期自查工具：复用 `parse_chart_spec_verbose`，「自查通过 = 落地必过」（与 fence 落地同一套规则）；registry 恰 5 工具 |
| `ai/prompts/chatbot/chart_prompt.py` | `CHART_SECTION` 由枚举生成、两轨共享；数据红线（数字必须来自工具结果、缺数填 null 不填 0、真实 0 照填、没真实数据不出图）；type 可省略句；boxplot 防滥用句；gauge 例外（在两轨【展现样式风格】段） |
| `sse_provider` 落库语义 | `buf` 恒为原始增量拼接，落库 = 用户所见原文 |

### 前端（CIOaas-web，全部保留）

`chat/utils/charts/` 总入口 + registry（18 builder、`resolveType` 缺 type 选默认、`buildChart` 样式变体、suits 适配、menuGroup 分组切换器只列 suitable）、`ChatChart`（builder 异常唯一占位「图表渲染失败」）、`parseChartFences` 历史重现、`chatEvents.isValidChartSpec` 最小结构校验、收尾 `loadThread` 静默刷新。

### 文档（无需改）

`2026-06-10-chat-chart-design.md`（契约）§6.1/§8 的降级语义本就是「解析失败 → 原文降级文本」，与删除后状态一致——契约文档从未吸收修复回路概念，零改动。

## 4. 删除清单（已完成，均在 `458c270`）

| 部件 | 说明 |
|------|------|
| `ai/chatbotgraph/chart/repair.py` | 修复核心（haiku 温 0 一次修复 + parse 复验 + 数字子集硬校验） |
| `ai/prompts/chatbot/chart_repair_prompt.py` | 修复系统提示词 |
| `tests/ai/chatbotgraph/chart/test_repair.py` | 修复回路单测 |
| `InvalidChartSegment`（fence_parser 定义 + `__init__` 导出） | 第三种段类型，专为把坏 fence 交消费方修复 |
| `CallerNode.CHART_REPAIR` 枚举 | 修复调用的 trace/成本归因节点 |
| `sse_provider._AnswerStream._emit` 整方法 | 修复调用 + `rfind` 落库 buf 改写 + 失败降级三合一 |
| `_AnswerStream.__init__` 的 `user_id`/`trace_id` 参数 | 原来只为修复的 TraceContext 服务 |
| `test_chat_turn.py` 2 个集成用例 | 修复成功改写 buf / 修复失败降级（被测对象已不存在） |

## 5. 修改清单

### 代码侧（已完成，在 `458c270`）

- `fence_parser.py`：`_classify_fence`→`_try_parse_spec`（改用非 verbose 版），**降级决策下沉到 parser 内部**——校验失败直接产 `TextSegment(围栏原文)`。
- `sse_provider.py`：`feed`/`finish` 从 async 生成器改**同步生成器**（管道内不再有 LLM await），新增纯函数 `_seg_to_event`；`_AnswerStream` 退化为纯渲染管道（无 IO）。
- `test_fence_parser.py`：6 个「→InvalidChartSegment」用例**改写**（非删除）为「→TextSegment 原文保留」，覆盖面不减（invalid JSON / 坏形状 / unknown type / scatter 少列 / waterfall null / gauge 越界）。
- `spec.py`：verbose 版 docstring 消费方去掉修复回路（1 行注释）。

### 文档/记忆侧（待做，本次收尾）

| 位置 | 改什么 |
|------|--------|
| `2026-07-04-chart-entry-and-style-framework-design.md` L11 | 删「含 IO 的 `repair.py` 刻意深路径显式 import」表述 → 包内全部纯逻辑经入口 |
| 同文件 L49 | 「后端 repair / validate_chart 随 parse_chart_spec 单点自动继承」→ 只剩 validate_chart |
| 记忆 `ai-chatbot-v1.md` | 交接段收尾：删除已提交 `458c270`、双防线段改单防线表述 |

## 6. 新增清单（唯一开放决策 + 一个可选顺手项）

### 6.1 「复杂类型必须先验」提示词升级（待确认，推荐做）

**事实澄清**：`chart_prompt.py`（CHART_SECTION）里**从来没有**任何「先验证」措辞——引导先验的唯一出处是 validate_chart 工具 docstring（模型每轮可见的 tool schema）：

> 复杂类型（boxplot / combo / bubble / gauge / waterfall）**强烈建议先验证**……简单 bar/line 有把握可不验。

**推荐方案（最小、不破原则）**：只把 docstring 的「强烈建议先验证」升级为「**必须先验证**」（简单 bar/line 可不验的句子保留）。一行措辞改动，直接堵住删修复后「AI 忘调工具」这个唯一口子。

**不推荐的备选**：在 CHART_SECTION 加一行点名 validate_chart——违反既有「CHART_SECTION 不描述具体工具」原则（两轨共享的图表段与工具层解耦），且 docstring 本身就在模型上下文里，边际收益小。

**连带动作**（若确认）：重跑 `interface_doc.py` 重新生成 `docs/AI-Chatbot/chatbot-tools-v2-interface.md`（既有约定：docstring 改动须再生成）。

### 6.2 可选顺手项：interface doc 摘要行句中截断

生成器 `interface_doc.py` 用 `description.splitlines()[0]` 取首行，validate_chart 条目摘要恰断在「boxplot / combo / bubble / gauge /」处（确定性复现的观感问题，非文档过期）。若 6.1 确认，可顺手改生成器取整段、或把 docstring 首行写短。不做也不影响功能。

## 7. 目标流程（端到端，删除后状态）

```
【生成期】AI 合成回答
    ├─ 打算画复杂类型（boxplot/combo/bubble/gauge/waterfall）
    │     → 必须先调 validate_chart（§6.1 确认后）
    │        ├─ ok: true  → 把返回的规范化 spec 原样写入 ```chart 围栏
    │        └─ ok: false → 按 errors 修正后重验
    └─ 简单 bar/line 有把握可直接写围栏

【流式下发】sse_provider（同步管道，无 IO）
    answer_delta → buf 累积原文（落库内容）
                 → ChartFenceStreamParser.feed
                      ├─ 合法 spec   → ChartSegment → event: chart（结构化下发）
                      ├─ 非法 fence  → TextSegment(围栏原文) → 普通 delta 文本
                      └─ 未闭合 fence → flush 时按原文回吐
    落库：无论哪个分支，content 恒为原文（绝不改写）

【前端·流式】
    event: chart → isValidChartSpec(最小结构) → appendChart → ChatChart
                    （resolveType 选型 → suits 过滤切换器 → buildChart 含样式变体）
    降级文本   → ReactMarkdown 渲染为 language=chart 代码块（原始 JSON 可见）

【前端·收尾/历史】
    流正常收尾 → loadThread 静默刷新 → parseChartFences(content) 重解析
    历史进入会话同路径；chatManage 管理页走 MarkdownView，不解析 fence（现状保持）
```

最坏用户体验（低频但非零）：AI 没先验且格式错 → 用户在流式中看到一段 JSON 代码块。这是删除修复回路后有意接受的 trade-off。

## 8. 已知口子（已于 2026-07-04 由前端渲染校验方案关闭）

**前后端校验宽严不一（删除前就存在，删除后触达频率略升）**：后端按 format 严格校验（gauge 越界 / boxplot 五数错位 / waterfall null 都会降级文本）；但落库是 fence 原文，前端历史路径 `parseChartFences` 只做最小结构校验（type 可缺省 + columns/rows 是数组）。于是**同一条坏 fence：流式期间显示为代码块，收尾刷新 / 重进会话后可能被前端画成图**（如 150 的 gauge 照画超表）。

~~处置建议：不在前端复刻后端 format 校验，接受现状 + 上线观察。~~ **该决策已被取代（2026-07-04 用户拍板）**：前端渲染前按镜像校验器拦截，语义违规 spec 显示「图表数据格式有误」占位符 + 弱化详情（不再画错图），口子关闭。方案与同步契约见 [前端渲染校验](./2026-07-04-chart-frontend-render-validation-design.md)。

## 9. 待办顺序（验收路径）

1. **确认本文档范围**（用户），特别是 §6.1 是否升级「必须先验」。
2. （若确认 6.1）改 validate_chart docstring 一行 + 重跑 `interface_doc.py` 再生成接口文档（可顺手做 6.2），随后跑受影响测试：
   ```bash
   uv run pytest tests/ai/tools_v2/ tests/ai/chatbotgraph/chart/ tests/chatbot/ -q
   ```
   （删除改动本身已 223 passed 后提交；前端零改动，无需跑前端测试。）
3. 文档/记忆收尾（§5 文档侧两处 + 记忆更新）。
4. 提交（英文消息，若有 2/3 的新改动）；**推送 `458c270`（+ 新提交）待用户明确说推送**。

## 10. 恢复路径（若上线后降级频率高）

完整实现在 commit `8bd9dbd`，删除是干净的顶端提交——**`git revert 458c270` 一步全量恢复、必然无冲突**（只要其后没有再动这批文件的新提交）。唯一需注意：若 `sse_provider.py` 之后又有新提交叠加，该文件需手工合并修复分支（`_emit` + buf 改写 + 两个消费点 async 化），其余文件 `git checkout 51a377d -- <file>` 即可。
