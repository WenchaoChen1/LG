# 图表职责重划：后端只管传输底线，判断全归前端 — 方案（已确认，实施中）

> 关联文档: [图表契约](./2026-06-10-chat-chart-design.md) · [类型扩展](./2026-07-04-chart-types-expansion-design.md)
> 状态: **已确认（2026-07-08），实施中、未提交**（§4 主体已落地；本次追加 Q2/Q5 两条决定同批实施）
> 问题（用户原话大意）: 前端已按数据类型控制用哪种图表样式，后端有必要判断图表吗？重新制定方案，并遵守既定原则（选型数据组驱动、常驻提示词保持 v1.1 不动）。
>
> **2026-07-08 用户追加确认的两条决定**（**刻意覆盖**下文两条既定原则，见 §6）：
> - **Q2 · 两工具强制**：所有图表输出前**必须**先调 `get_chart_guide` 再调 `validate_chart`、通过才可输出——**不分简单/复杂**，取消"简单 bar/line 可直接画/可不验"豁免。为此**解锁 v1.1 提示词 → v1.2**（覆盖"v1.1 常驻提示词不动"原则）。
> - **Q5 · 绝不给用户看到图表 JSON**：任何画不出的 ```chart（JSON 坏 / 非二维表 / 类型不对）一律渲染成"图表数据不对"错误占位卡（JSON 仅折叠在"详情"、默认不外露），**绝不**把围栏原文当文本/代码块显示。为此后端坏 fence 从流中**抑制**、不再当文本回吐（覆盖"降级把围栏原文当文本保内容"原则；内容不丢——落库消息仍含原文，前端落定态渲染成错误卡）。

## 1. 现状盘点：后端现在"判断图表"的四个地方

| # | 位置 | 判断内容 | 失败后果 |
|---|------|----------|----------|
| 1 | fence 解析（`fence_parser`） | 围栏体是不是合法 JSON | 降级文本 |
| 2 | 落地校验·结构底线（`spec.py`） | 是 dict、columns ≥2、rows ≥1、格子是标量 | 降级文本 |
| 3 | **落地校验·按类型分支（`spec.py`）** | type ∈ 18 类枚举；scatter 恰 3 列 / bubble 恰 4 列 / waterfall 2 列数值不许 null / boxplot 6-7 列五数单调不减 / gauge 2 列 1 行 0-100 | 降级文本（一坨 JSON 给用户看） |
| 4 | `validate_chart` 工具 | 同 2+3（AI 自查） | 返回错误让 AI 修 |

## 2. 结论：#3 没必要，#1/#2 必要，#4 保留（换角色）

**#3（按类型判断）与前端重复且效果更差。** 前端已有同一职责的更好实现：AI 的 type 只是建议（`resolveType` 无效/缺省则按数据形状选默认）、`suits` 按数据过滤可用类型、builder 有 try/catch 兜底。同一份"列数不对"的数据：后端拒 → 用户看到一坨 JSON 文本（最差体验）；放行给前端 → 按数据形状画出一张合理的默认图（更好体验）。后端按类型拒绝反而拦掉了前端的数据驱动兜底。

**#1/#2（结构底线）必须留在后端**，它不是"判断图表"而是**传输机制的保真**：只有"像一张二维表"的数据才配发 Chart 事件——否则前端 `isValidChartSpec` 会把 chart 事件直接丢弃，内容**凭空消失**（比降级文本更糟，违反"绝不丢内容"）。底线校验保证烂结构走文本降级、内容永远可见。

**#4（validate_chart 工具）保留**——它是你提出并认可的"AI 自助判卷"通道：按类型的精确规则从"落地闸门"退役后，唯一活在这里（AI 画复杂类型前自查，把 totals/seriesTypes/五数顺序写对）。自查是提升质量的服务，不是拦截；落地不再拦。

## 3. 新职责划分

```
后端 = 传输与底线：fence 切分 + 「是不是一张表」（columns≥2 / rows≥1 / 格子标量）
        ├─ 底线过 → Chart 事件（type/style/扩展字段原样透传，未知 type 也放行）
        └─ 底线不过 / JSON 坏 → 从流中【抑制】该 fence（不再当文本回吐 JSON，Q5）
前端 = 全部图表判断（唯一权威）：resolveRenderType 判定链（结构底线→AI建议且suits→数据驱动回落→null）
        + suits 数据适配 + builder 渲染防御；判不出（null）或渲染失败 → 「图表数据不对」错误占位卡
        （落定态由 parseChartFences 权威渲染，坏 fence 同样进错误卡、JSON 不外露，Q5）
工具 = AI 自助：get_chart_guide 发说明书 + validate_chart 自查（承接按类型精确规则）
        ——**每张图输出前都必须依次调这两个、通过才输出**（Q2，不分简单/复杂）
```

## 4. 改动面

### 后端 CIOaas-python

**主体（已落地）**
- ✅ `spec.py`：`ChartSpec` 保留结构底线（columns ≥2 宽容转字符串、rows ≥1、标量格、可选字段透传）；**删除 `_check_format` 全部按类型分支**；`type` 改为**任意可选字符串**（不再校验枚举——未知 type 由前端落默认；`ChartType`/`CHART_TYPES` 枚举保留，只服务提示词模板行与 guide，不再参与落地校验）。
- ✅ 按类型的精确校验逻辑**内联进 validate_chart 工具**（`chart_validate_tool.py` 的 `_typed_errors`：scatter/bubble 列数、waterfall、boxplot 五数单调、gauge 0-100、combo seriesTypes、未知 type 名单）。
- ✅ 测试：落地校验用例改为"结构底线过/不过"两组；按类型用例整体迁到 `test_chart_validate_tool.py`。

**Q2 追加（2026-07-08）· 提示词 v1.1 → v1.2**
- `chart_prompt.py`：版本 bump `1.2`；"画图流程"从条件调用改为**强制**——任何图表输出 ```chart 前都先调 `get_chart_guide` 再调 `validate_chart`、通过才输出，删除"简单 bar/line 可直接画/可不验"豁免；`chart_validate_tool.py` docstring 同步。CHART_SECTION/CHART_TYPE_GUIDE/数据红线其余不变。

**Q5 追加（2026-07-08）· 坏 fence 抑制**
- `fence_parser.py`：`_try_parse_spec` 为 None（JSON 坏 / 结构底线不过）时**不再** `TextSegment(围栏原文)`，改为**抑制**（该 fence 不产出 Segment）；未闭合 fence 的 final 分支同样抑制半截 JSON；正常文本照旧输出。前提已核实：落库 assistant 消息是 LLM 原始答案文本（含围栏），与 fence_parser 流式切分独立——抑制不丢内容，落定态由前端 parseChartFences 渲染错误卡。测试 `test_fence_parser.py` 相应把"降级文本"用例改为"抑制"。
- `sse_provider` 零改动（仍 `ChartSegment→Chart` / `TextSegment→text`，坏 fence 已在 parser 侧被抑制、根本不产段）。

### 前端 CIOaas-web（接住下放的判断）

**主体（已落地）**
- ✅ registry 给三个特型补 suits：`waterfall`（恰 2 列且数值格全为数）、`boxplot`（恰 6-7 列且格 1..5 数值单调不减）、`gauge`（恰 2 列 1 行且 0≤值≤100）。
- ✅ 判定链单点纯函数 `resolveRenderType(spec)`：结构底线 → AI 建议且 suits 则用 → 数据驱动回落（默认候选 / 组内首个 suitable）→ 都不成则 **null**。`ChatChart` 据此：能画则画，`null` 或渲染 try/catch 失败 → 渲染 `ChartFallback`「图表数据不对，无法展示」（JSON 只折叠在"详情"、默认不外露），**不画误导图、不甩 JSON**。

**Q5 追加（2026-07-08）· 坏 fence 也进错误卡**
- `parseChartFences`：落定消息的权威渲染。原先坏 fence 降级为 text 块（把围栏原文当代码块显示 = 泄漏 JSON）——改为**每个 ```chart 都产出 chart 块**，携带 `JSON.parse` 结果（坏 JSON 则 `null`）；非法结构 / null 交 `ChatChart` 走 `ChartFallback`。`messageReducer` 的 chart 块 `spec` 放宽为 `ChartSpec | null`，`ChatChart` 对 null/非法 spec 健壮。
- `chatEvents.isValidChartSpec` 不变（直播 `chart` SSE 事件仍按它过滤，合法才 `appendChart`；坏的在后端已被抑制、不产该事件）。
- 清死代码：删除孤儿 `charts/validate.ts` + `validate.test.ts`（生产已改走 `resolveRenderType`，`index.ts` 已不再导出 `validateChartSpec`）。

### Q5 延伸 · 图表加载态三态（2026-07-08）

用户 UX 追问："回答过程中数据只是没生成完，此时显示错误不合适——应 加载中→图→（完成仍坏）失败"。核实：**错误只在完成后出现**这半本就成立（后端 fence 憋到闭合才吐、错误卡只来自 `onDone→loadThread→parseChartFences`），缺的是**生成中那段的"数据加载中"占位**（原为静默留白——后端把整段 fence 缓冲到闭合才吐、前端拿不到"图要来了"的信号）。落地为新增 `chart_pending` 信号：

- **后端**：`fence_parser.py` 进入 ```chart 围栏（`_OPEN` 命中）即产出 `ChartPendingSegment`（每 fence 恰一次）；`sse_provider._seg_to_event` → `events.ChartPending()`（新事件 `chart_pending`，无 payload，仿 `AnswerReset`）。段/事件序列 = 一个 `chart_pending` → 随后 要么一个 `chart`（合法）要么无（非法抑制）。`chart/__init__.py` re-export `ChartPendingSegment`。
- **前端**：`chatEvents` 加 `CHART_PENDING`/`onChartPending`；`messageReducer` chart 块加 `loading?`，`appendChartPending` 插加载占位、`appendChart` 顶替末尾加载块（复用同 id 防重挂）；`useChatStream` 两处（send+enterThread）挂 `onChartPending`；`ChatChart` 加 `loading` 分支渲染 `ChartLoading`（antd Spin + "数据加载中"，hooks 之后早退）。
- **三态闭环**：生成中=加载中 → 闭合合法=图（顶替占位）→ 非法则占位保持加载中，直到 `onDone→loadThread` 经 `parseChartFences` 重渲染成图/「图表数据不对」失败卡。**加载态仅直播 reducer 路径**，历史/落定路径永不产加载态。
- 验证：后端 chart 全量 79 passed；前端 umi-test 63 passed；tsc 0 新增报错。

### 优化 · 结构卡回迁常驻 + 报错自纠 + 单源收口 + UI 英文（A+B+②③，2026-07-08，chart_prompt v1.2 → v1.5；① 降按需已撤回）

用户追问"AI 到底怎么知道这几种数据类型"，指出 **per-type 数据结构（列约定）并没常驻给 AI**——只在 `CHART_TYPE_GUIDE` 里、靠 Q2 强制调 `get_chart_guide` 才送到（软约束、可能被跳过）。据此优化（**refine Q2**）：

- **A · 结构卡回迁常驻**：`chart_prompt.py` 的 `CHART_SECTION` 新增"各类型列约定"精简卡（series/scatter/bubble/waterfall/boxplot/gauge/combo 的 columns 摆法，~6 行）。结构信息**可靠常驻**，AI 不调工具也知道怎么摆。**注（v1.5，用户最终决定）**：`get_chart_guide` + `validate_chart` **每张图都必调、不分简单复杂**（曾在 v1.3/v1.4 试降按需，用户撤回）；结构卡作速查、不替代工具调用。版本 → v1.5。
- **B · 报错自纠**：`chart_validate_tool.py` 的 `_typed_errors` 在 typed 校验失败时，末尾附该类型正确列约定（`_SHAPE_HINT`，与常驻卡同一份事实）——AI 一次照着改对，不用再往返 guide。
- **架构修订**：这把 v1.1"逐类型规则一律移出常驻、零膨胀"的原则做了**有分寸的回调**——区分「结构（列约定）」与「选型（怎么选）」：**结构回迁常驻**（AI 产出正确数据的硬信息）、**选型仍留 guide 按需**（选型本就是前端数据驱动的活）。对应更新 `test_chart_prompt.py` 的架构守卫测试。
- **进一步收口（②③，用户点名执行；① 已撤回）**：① ~~`validate_chart` 降按需~~ **已撤回**（用户 v1.5 要求两工具每图必调、不分简单复杂）；② 结构卡与 validate 报错自纠**收敛到单一事实源** `spec.COLUMN_SHAPES`（`chart_prompt._shape_card()` 与 `chart_validate_tool._typed_errors` 都从它派生，消除 A+B 引入的两份副本；前端 registry/builder 因语言不同仍独立，属必要副本）；③ 前端错误卡 / 加载 / 详情文案**本地化为英文**（`Chart data unavailable` / `Loading chart…` / `Details`，面向英文终端用户，与聊天回答默认英文一致）。
- 验证：后端 chart+validate+guide+提示词 **85 passed**；前端 umi-test **63 passed**；tsc 0 新增。**④ 提交按用户要求不做**。

### 不变项
- `chart_prompt` 的 fence 协议 / 格式模板 / 数据红线（null 规则等）与 `CHART_TYPE_GUIDE` 全文不变；get_chart_guide 无参全量下发不变。（**注**：仅"画图流程"段随 Q2 改为强制调两工具、版本 → v1.2；"v1.1 锁定"原则已被 Q2 有意解除。）
- 前端 format/suits/traits/styles 四层架构与总入口不变。

## 5. 收益与取舍

**收益**：后端图表代码显著变薄（校验只剩十来行底线）；"图表知识"归一到前端 registry（加类型彻底不动后端校验）；坏 type/坏列数的用户体验从"JSON 文本"升级为"画出合理默认图"；与"选型数据组驱动"哲学完全一致。

**取舍（诚实列出）**：
1. 误导性图形的防线从后端换到前端 suits——三个特型的 suits 必须随本方案一起补，否则错序五数会被画成错误盒须图（窗口期风险）。
2. validate_chart 的语义从"自查=落地必过"变为"自查=画得对"（落地变宽了，必过更容易，语义只强不弱）。
3. 历史消息零影响（校验只放宽不收紧，以前能过的现在都能过）。
4. **Q2 代价**：每张图（含最简单 bar/line）都多两次工具往返 `get_chart_guide`+`validate_chart`——首字延迟与 token 上升；且仍是提示词软约束（LLM 遵守），非代码硬闸门。用户已知悉并接受（要"所有图表必走这两个、无简单不走之说"）。
5. **Q5 代价**：局部推翻"降级把围栏原文当文本保内容"——坏 chart fence 的围栏原文不再作为文本呈现。但 fence 体本就是 JSON、周围正文是独立 text 段不受影响，落库消息保留原文、前端渲染错误卡，**不丢有价值内容**。

## 6. 确认记录

**已确认（初版方向）**
1. ✅ 职责重划方向（§3）认可。
2. ✅ `type` 落地不再校验枚举（未知 type 放行给前端落默认）。
3. ✅ 三个特型 suits 前端补全随本方案同批做。

**2026-07-08 追加确认（覆盖既定原则）**
4. ✅ **Q2 · 两工具强制**：所有图表输出前必须依次调 `get_chart_guide`→`validate_chart`、通过才输出，不分简单/复杂；为此解锁 v1.1 提示词 → v1.2。已知代价 = 每张图多两次工具往返（见 §5.4），接受。
5. ✅ **Q5 · 绝不让用户看到图表 JSON**：坏 chart fence 一律进"图表数据不对"错误卡（JSON 折叠、默认不外露）；后端流式抑制坏 fence、前端 parseChartFences 坏 fence 进错误卡。已知代价 = 局部覆盖"降级文本保内容"（见 §5.5），接受（内容不丢）。
6. ✅ **加载态三态（Q5 延伸）**：生成中显示"数据加载中"、好了显示图、完成仍坏显示失败。新增 `chart_pending` 信号（后端围栏打开即发、前端插加载占位由 chart 顶替）。错误"只在完成后出现"本就成立，本次补齐生成中的加载占位。
7. ✅ **结构卡回迁常驻（单源）+ 报错自纠 + UI 英文（A+B+②③）**：per-type 列约定精简卡进常驻（单源 `spec.COLUMN_SHAPES`，结构可靠可见）；validate 失败报错自带正确摆法；前端错误卡/加载/详情英文化。chart_prompt → v1.5。**⚠️ 工具调用最终策略：两工具（get_chart_guide + validate_chart）每张图必调、不分简单复杂**（v1.3/v1.4 曾试"降按需"，用户 2026-07-08 撤回，回到 Q2 立场）。

> 关联运行时理解（用户 Q3/Q4 已答，非改动项）：Q3 失败重试 = validate_chart 回 errors 引导 AI 在 ReAct 迭代内自修（软约束，无确定性循环）；失败数据不入前端由落地闸门保证。Q4 后端**不取数不构图**，只做 fence 切分 + 结构底线 + 轻规范化后透传——这是 §3 既定职责。
