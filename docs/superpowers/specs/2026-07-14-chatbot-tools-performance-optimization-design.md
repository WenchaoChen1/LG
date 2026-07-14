# Chatbot 数据工具性能与成本优化方案（v2，2026-07-14 晚间修订）

> 日期：2026-07-14（v2 修订，取代同日早版）
> 基线代码：CIOaas-python `sprint113` @ `db9f9d2`（已含当天全部队友提交，含晚间四连：`3f1b4e5` aiDetail 携带 close_month+entry_mode / 删 trace_metric、`3e8382b` financials/benchmark 要求 UUID + company_name 入参、`db9f9d2` scope 解析只做 ∩allowed）
> 证据来源：真实 trace `ec44a7e9614e416d96985f336dd726a0`（25 次 LLM / $0.360378 / 169,326 tokens / 442.6s）+ `ai_llm_call_log`、`ai_llm_tool_call_log` 落库数据逐条核对
> 关联文档：CIOaas-python `docs/AI-Chatbot/chatbot-tools-v2-design.md`

## 一、问题背景（trace 实测数据，2026-07-14 上午）

一轮"按状态对比全部公司"的对话耗时 442.6s、花费 $0.36：

| 环节 | 耗时 | LLM 次数 | 成本占比 | 根因 |
|------|------|---------|---------|------|
| rewrite 节点 | 165.6s | 2×sonnet | 10% | 其中 get_companies（全量+close_month）156.4s |
| retrieve 节点 | 269.1s | 6×sonnet | **87%** | get_companies 三连慢调用（99.6s + 98.4s + 4×分批） |
| resolve_company 消歧 | 分散 | 15×haiku | 3% | 同 5 个模糊公司名重复消歧 3 轮 |

三个实锤根因：① aiDetail 批量 20 家必超时（30s×3 重试 ≈ 99.6s，签名精确吻合）后静默降级；② 降级 message "temporarily unavailable" 诱导模型原样重试再烧 98s；③ 零缓存双杀——`usage_cached_tokens` 全程 0（21-25k tokens × 6 轮全额计费）+ 公司名 LLM 消歧结果不缓存。

## 二、现状核对（对照 `db9f9d2`，队友当天改动大量命中本方案）

| 原方案项 | 队友已做的对应改动 | 现状结论 |
|---------|-------------------|---------|
| P5 提示词引导回传 UUID | `3e8382b`/`db9f9d2`：financials/benchmark 的 `company_ids` **契约改为须传 UUID**，scope 解析只做 ∩allowed、误传名字直接忽略；名字解析统一收口 get_companies（新增 `company_name` 入参） | ✅ **已完成**（更强形式），移出待办 |
| P6 close_month 路径 | `3f1b4e5`：aiDetail 批量携带 `close_month` + `financial_entry_mode`（`include_close_month`，Java 侧顺带算）；`_support/close_month.py`、`ReqCtx.close_month_cache`、filter-options 逐公司 GET 链**整条删除** | ✅ **根治已落地**，移出待办 |
| P2 名字→UUID 三处收口 | financials/benchmark 的名字匹配循环已删；`resolve_cid`→`match_company`（含 LLM 消歧）现**仅剩 get_companies 与 sql 轨**在用 | ⬇️ **大幅缩水**，残留见新 P2 |
| P1 aiDetail 自动分批 | **未做**；且 close_month 成默认字段后 `want_close_month=True` 恒真、"仅 id+name 的廉价短路"被移除——**每次 get_companies 都走一次全量 aiDetail 批量** | ⬆️ **更关键**（见新 P1） |
| P4 降级 message | 未变（`companies_tool.py` 仍 "company details are temporarily unavailable"） | 成立 |
| P3 prompt caching + 瘦身 | llm router 未动（cached 仍 0）；注册表缩至 **6 工具**（trace_metric 删）、schema 略小但量级不变 | 成立 |
| P7 死代码扫尾 | `aggregate`+`percentile_*`+`Scorecard`+`test_benchmark_scoring` 被队友**明确保留**（`ai/CLAUDE.md` §五：对齐前端 calc 的回归基线，改前端 calc 须同步）——**不得删**；trace_metric 的两个 lgpi 客户端队友已删 | 🔄 **范围重定**（见新 P7） |

其它同日变化（不影响方案，供上下文）：`bbe4bb5` MRR YoY N/A 改判修正；`6f774df` 停止轮次标记；提示词补行为红线；web 侧饼图 legend 布局修复。

## 三、优化项（v2 修订版，按性价比排序）

### P1 aiDetail 工具内自动分批（最高优先，且紧迫度上升）

- **问题**：`companies_tool.py` 对全部 `target_ids` 打**一次** `query_company_detail`（现 `include_close_month=True` 恒开）；≥20 家在当前环境必超时（30s×3 重试 ≈ 100s）后整批降级。close_month 变默认字段后**每次 get_companies 都命中该路径**（廉价短路已移除），rewrite 全量调用、retrieve 列表调用全部受影响——原 trace 的 ~300s 故障面现在更宽。
- **改法**：`target_ids` 按 `_DETAIL_BATCH = 5` 切批、`asyncio.gather` 有界并发（信号量 ≤4）调 `query_company_detail`（每批带 `include_close_month`），合并 `details_by_id`；**单批失败只降级该批公司**（该批 close_month/detail 字段为 null + 行内说明），其余批照常。批大小/并发做成模块常量，Java 侧优化后可调大。
- **依据**：trace 实测 5 家/批 9-17s 成功、20 家/批 100s 超时；模型已用行为验证过该解法。
- **涉及**：`source/ai/tools/companies_tool.py`（aiDetail 段）+ 单测（>5 家拆批、坏批局部降级、全批失败整体降级）。
- **验收**：20 家 + 默认字段的调用从 ~100s 降到 ~20s 内、close_month 不再整批丢失。

### P2 get_companies 内消歧缓存 + 并发（残留项，缩水后仍有效）

- **现状**：名字解析已收口 get_companies（好事），但其 `resolve_cid` 循环仍**串行**逐个 await、`match_company` 的 LLM 消歧结果**零缓存**——模型多轮重复传同一批名字时（原 trace 同 5 名 ×3 轮=15 次 haiku），每轮全额重付。
- **改法**：①`ReqCtx` 加 `match_cache: dict[str, Optional[str]]`（mention→UUID/None，负缓存防重复失败）；`resolve_cid` 先查缓存、结果回写；②`companies_tool` 的逐项循环改 `asyncio.gather` 有界并发（≤5），保留逐项 needs_pick/scope_errors 语义（gather 收集逐项 outcome）。
- **涉及**：`_support/request_context.py`、`companies_tool.py`；sql 轨 `retrieval_sql_agent` 经同一 `resolve_cid` 自动受益。
- **验收**：同名字第二次出现 0 LLM；一轮内消歧 haiku 次数 = 去重后模糊名个数。

### P3 Prompt 成本：开 caching + 工具 description 瘦身（成本 -70%）

- **问题**：retrieve 6 轮迭代 20.9k→25.6k input tokens 全额计费（`usage_cached_tokens` 恒 0）、$0.31/轮占 87% 成本；大头 = 系统提示词 + 工具 schema（`get_financials` 50 行 docstring + 31 项指标 JSON、`get_benchmark_data` 68 行 docstring）。注册表已缩至 6 工具，但量级未变。
- **改法**：
  1. **prompt caching**：`llm_db_router`/OpenRouter 请求对 system prompt（+工具定义段）加 Anthropic `cache_control` breakpoint；验证 `usage_cached_tokens` 落库非 0（成本三层采集已支持）。**需小样验证后再全量**。
  2. **description 压缩**：不改语义只压措辞（重复告诫合并、示例精简），目标 -30-40%；指标全集 JSON 保留（防猜名设计成立）、压为紧凑格式。
- **涉及**：`llm/application/router/`、`financials_tool.py`、`benchmark_data_tool.py`、`prompts/chatbot/retrieval_agent_prompt.py`；改 description 后重新生成 `chatbot-tools-v2-interface.md` + `tool_call_schema` 探针。

### P4 降级 message 可操作化（P1 的保底，几行）

- `companies_tool.py` 批失败 message 从 "company details are temporarily unavailable" 改为可操作指令（分批后场景大减，保底措辞：`"detail fetch failed for N companies; their detail fields are null"`——P1 落地后失败粒度已是批级，不再邀请全量重试）。

### P7 死代码扫尾（v2 重定范围）

**引擎三件套处置变更（2026-07-14 深夜，Wenchao 拍板推翻保留决策）**：WangZhenLx 当日 19:08（`403b999`）曾在 `ai/CLAUDE.md` 记录将 `aggregate`+`test_benchmark_scoring` 留作"前端 calc 回归基线"；经确认该基线已无受益方（引擎零生产消费者），Wenchao 决定删除。**已删**：`aggregate.py`/`percentile_internal.py`/`percentile_external.py`、`dto/benchmark_result.py`（Scorecard）、包内连带孤儿（numbers 的 `parse_benchmark_value`/`format_percentile_display`/`_eq`/`_quartile_of`、runway 的 `compute_runway_value`/`compute_runway_percentile`/`_TIER_ORDER`、metrics 的 `benchmark_source_label` 等 4 符号）、`test_benchmark_scoring.py` 对应用例（保留 round_to/classify_runway/METRICS 常量三组在用符号的用例）。**保留**：`numbers`（`round_to`/`_round_half_up`/`_num`/`_arithmetic_mean`）/`metrics`（`METRICS`/`CATEGORIES`/`_ENUM_TO_METRIC_ID`）/`runway`（`classify_runway`）——`get_benchmark_data`/`get_financials` 在用。`ai/CLAUDE.md` §五口径条目已改写（Python 不再镜像前端 calc、改前端无需同步 Python）。

**孤儿处置（按作者归属分流，2026-07-14 晚执行）**：
1. ✅ `lgpi_api/benchmark_api.py` **已删**（作者 Wenchao Chen，唯一调用方 rank_companies 已删、确认无用）：连带 `__init__.py` 导出 + `lgpi_api/CLAUDE.md` 行 + 测试 `test_benchmark_api_extra_fields.py`、`test_benchmark_lgpi.py`；py_compile + 导入冒烟通过。
2. ✅ `lgpi_api/benchmark_filter_options_api.py` **已删**（作者 WangZhenLx，其唯一调用方 `_support/close_month.py` 被作者本人随 `3f1b4e5` 删除后成孤儿；经 Wenchao 确认无用后删除）：连带 `__init__.py` 导出 + `lgpi_api/CLAUDE.md` 表格行（设计文档指引行改为记录"已随 aiDetail include_close_month 方案删除"）；无专属测试。
3. ✅ 全面孤儿复扫（同日）：lgpi_api 余下 10 个导出、`ai/tools/` 12 模块、`_support/` 8 件、`dto/` 7 件均有活消费者或属刻意保留（sql 轨 / `_benchmark_scoring` 回归基线 / MCP 链），**无更多待删项**。

### ~~P5 提示词引导回传 UUID~~ ✅ 队友已完成（须传 UUID + company_name 收口，`3e8382b`/`db9f9d2`）

### ~~P6 close_month 路径~~ ✅ 队友已根治（aiDetail 携带 close_month，`3f1b4e5`）

## 三补、遗留项处置记录（2026-07-14 晚，Wenchao 确认）

- **web 大 trace（上千 span）渲染虚拟化**：❌ 不做（won't-fix）——几百 span 实测无感、超大 trace 尚未出现，YAGNI；届时再考虑 react-window / 行级 memo。
- **py `_RECURSION_LIMIT=7` 打满降级路径**：❌ 不做（won't-fix）——审核结论：异常路径 passthrough 完备、needs_pick 有 retrieve 兜底，后果仅多跑一轮取数。
- **参考文档陈旧漂移**：✅ 已清理（CIOaas-python `docs/AI-Chatbot/chatbot-java-api-tools.md` 顶部加 2026-07-14 大清理注记；`2026-07-10-close-month-anchor` 设计+计划两篇加"实现已被取代"声明；历史设计存档类不逐行改，沿用 `ai/CLAUDE.md` 相关文档节的"已取代"标注惯例）。

## 四、明确不在本方案内

- Java 侧 aiDetail 性能根治（现还多算 close_month，20 家批的服务端耗时值得 Java 侧专项；本方案 P1 只在 Python 侧绕行）；
- web 端 agent-trace 页审查修复清单（startMs 降级等，独立事项）；
- Ask Goldie 域名名单（待产品确认）。

## 五、实施顺序与测试

| 批次 | 项 | 说明 |
|------|----|------|
| 批1（一次提交） | P1 + P4 | companies_tool aiDetail 分批 + message，~80 行 + 单测 |
| 批2（一次提交） | P2 | ReqCtx.match_cache + companies_tool 并发收敛，~80 行 + 单测 |
| 批3（独立验证） | P3 | cache_control 小样验证 → 全量；description 压缩 |
| 批4（小扫尾，先 pull 复核） | P7 | 纯删除 + 导出/文档/测试同步 |

- 测试范围：`tests/ai/tools_v2/`（companies/financials/benchmark/docstrings）+ 新增分批与缓存单测；P3 后重生成接口文档。
- 效果验收基准：复跑同款"全公司状态对比"问题（对照 trace `ec44a7e…`）：442.6s → 目标 ~60-90s、$0.36 → ~$0.10-0.15、LLM 25 次 → ~12 次。
