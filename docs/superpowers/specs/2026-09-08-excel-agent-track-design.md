# Excel 拉取式智能体轨（excel_agent_graph）设计

> 关联文档: [Excel 解析优化调研 · 设计理念](../../智能解析-Excel解析优化/调研/design-philosophy.md) · [Python 端设计](../../智能解析-Excel解析优化/调研/python-design.md) · [Excel 科目父链交由代码计算设计稿](./2026-08-03-excel-account-label-join-in-code-design.md)
>
> 日期: 2026-09-08 · 状态: 设计已批准，进入开发 · 范围: CIOaas-python；Java 零改动；前端零改动（shadow 对比只落 DB/日志）

## 一、目标与约束

用拉取式智能体（LLM 通过进程内 tool 按窗口读取 sheet、代码负责结构与数值）**整体替换** Excel/CSV 轨，但：

1. 新轨独立成子包 `source/ai/agent/excel_agent_graph/`，老 `excel_preprocess_node.py` 一行不改，验证通过前保留。
2. 只加一个三态开关 `EXCEL_TRACK=legacy|shadow|agent`（默认 `legacy`），两处读取：`build._route_after_download` 与 `parallel_files_node._preprocess_for`。
3. 新轨对外只暴露 `excel_agent_node(state) -> ExcelPreprocessReturn`，返回形状与老轨一致，`refine_extraction → save_to_db`、PDF/图片轨零改动。
4. 用户四个已定决策：三态开关；**数值由代码回填**（模型只回行 id + 语义），shadow 期额外让模型回 `v` 做对照；**代码算结构、模型只判语义**（父级链、合并块类型、稀疏坍缩由代码做）；**预算用尽或新轨失败即该文件 FILE_FAILED 并写明原因**（不回退老轨）。

## 二、三态开关

| 模式 | 行为 |
|---|---|
| `legacy` | 现状，新轨代码不执行 |
| `shadow` | 老轨照常跑并写库；老轨返回后同一 worker 内用同一 `local_path` 串行跑一遍新轨，结果**只**写对比表 `ai_excel_track_shadow` 与日志，不进 `state.tables`；新轨任何异常被吞掉记 `agent_failed=1` |
| `agent` | "excel" 分支指向 `excel_agent_node`，老轨不执行 |

实现：`excel_agent_graph.nodes.shadow_node.with_excel_shadow(legacy_fn)` 返回包装函数，`build.py` 与 `parallel_files_node.py` 在注册 `excel_preprocess` 时套一层；`agent` 模式两处改选 `("excel_agent", excel_agent_node)`。模式每次调用读 env（便于测试 monkeypatch）。

## 三、数据流（agent 模式）

### Stage A · 建模（代码，无 LLM）—— `tools/_sheet_model.py`

openpyxl 读一次（`.xlsx/.xlsm` 走 openpyxl；`.xls` 走 xlrd `formatting_info=True`；`.csv` 合成单 sheet），每 sheet 建 `SheetModel`：

- `CellModel`：`raw`（openpyxl 原值）、`text`（渲染后文本：金额去千分位保留符号、百分比 ×100 带 `%`、日期显示串）、`kind`（blank/number/percent/date/text）、`currency`、`is_formula`。
- `RowModel`：稳定行 id `r`（源行号，1-based）、`cells`、`label`、`indent`、`parent_chain`（纯父链，不含自身）、`merged_block_id`、`is_merged_anchor`、`note`、`has_numeric`。
- `MergedBlock`：源坐标闭区间 + `kind ∈ {two_column, label_merge_sparse, label_merge_dense, header_band, other}` + `anchor_text`。`label_merge_sparse` 直接坍缩成一行（值 coalesce）。
- `ColumnMeta`：`c`、`header_texts`（层级表头文本自上而下）、`month_hint`（代码推 YYYY-MM，推不出 None）、`is_total_like`、`numeric_ratio`、`date_ratio`。
- 表级：`header_rows`、`label_col`、`hierarchy_signal ∈ {none, indent, rowspan, style}`。
- 不设 2000 行上限；网格按需切窗口。

### Stage B · 智能体（每 sheet 一次会话，同文件内串行）—— `nodes/agent_runner.py` + `tools/*_tool.py`

经 `llm.infrastructure.langchain.create_agent`（`DBRouterChatModel`，`ai_llm_call_log` 审计保留，trace `agent=financial_extract, node=excel_agent`），`context_schema=ExcelAgentCtx`，工具在 `runtime.context` 取 `SheetModel`（对 LLM 不可见）。四个 `@tool`：

| tool | 输入 | 输出 |
|---|---|---|
| `sheet_profile` | — | 行列数、表头区、月份列候选、合并块清单（类型 + 行范围 + anchor）、层级信号、列统计、前 40 行预览 |
| `read_rows` | `start, end` | 窗口只向外扩到合并块与表头区边界（返回实际范围），单次 ≤120 行；每行 `r` / 缩进 / 父链 / 单元格文本 / `note` |
| `find_rows` | `pattern` | 按标签正则定位的 `r` 列表 |
| `emit_table` | `EmitTable` | 终止工具，可多次：`{table_name, data_type, cols:[{c, mon}], rows:[{r, label, lg, pf, cf, ut, cur, dense_mode?, v?}]}`；`label` 为 checksum；`v` 仅 shadow 期要求 |

预算（env，默认）：`EXCEL_AGENT_MAX_TOOL_CALLS=12`、`EXCEL_AGENT_MAX_INPUT_TOKENS=150000`、`EXCEL_AGENT_MAX_SECONDS=300`（每 sheet）。由 `BudgetMiddleware`（`awrap_model_call` 计输入 token + 计时、`awrap_tool_call` 计次）执行，超限抛 `ExcelAgentBudgetExceeded`。每次模型调用逐次进 `llm_units_gate`。

### Stage C · 组装（代码）—— `nodes/assemble.py`

对每个 emit 行按 `(r, c)` 取 `CellModel`：`kind=number` 用 `raw`，`percent` 用 `raw×100`，文本走五条确定性变换（去千分位、括号负、去货币符、去百分号、空→None）；`RawRow(row_position=r, column_position=cols 序号, column_month=mon, account_label=label, account_label_join=代码父链 + label, lg/pf/cf/ut/cur=模型值)`；经 `shared.post_process_extraction_cells`（新增的公开别名，行为不变）做白名单/截断归一。

- `label` 与网格标签归一化后不等 → 丢行计数 `label_mismatch`。
- `dense_mode=sum` 的 `label_merge_dense` 块由代码逐列求和；`sub_items` 则按块内每行各出一行。
- 探针（计数 + 日志 + span 属性）：emit 外有数值行、cols 外有数值列、`r` 非法、看似数值解析失败。
- shadow 期：模型 `v` 与代码值逐 cell 比对，进对比表。

### 失败处理（agent 模式，用户决策 B）

预算用尽 / 工具异常 / emit 不合规 / SheetModel 构建失败 → `error_message`：
`"Excel agent budget exhausted (calls=N, tokens=M, seconds=S)"` 或 `"Excel agent failed: <reason>"`，同时填 `n_extract_units`（尝试的 sheet 数）与 `n_extract_failures`。模型判非财务（含 GL detail）的 sheet 不出表、不算失败。

## 四、同步/异步

抽取图同步，`create_agent` 仅 async：`agent_runner.run_sheet_agent` 用 `asyncio.run` 起独立事件循环（worker 线程内，`contextvars.copy_context` 传 trace/span），`asyncio.wait_for` 兜墙钟。`DBRouterChatModel` 与 `create_agent` 工厂新增可选透传 `max_tokens` / `cache_system` / `timeout`（默认 None，行为不变）。

## 五、Shadow 对比与删除判据

表 `ai_excel_track_shadow`（迁移 `V023__sprint117_ai_excel_track_shadow.sql`，一行一 sheet）：`task_id, file_id, sheet_index, sheet_name, legacy_cells, agent_cells, value_match, value_mismatch, missing_in_agent, extra_in_agent, lg_match, lg_mismatch, label_mismatch, agent_failed, agent_error, agent_tool_calls, agent_input_tokens, agent_seconds, created_at`。比对键 `(account_label_join, account_label, column_month)`。

删老轨判据：连续 30 个真实任务，值一致率 ≥99.5%、lg 一致率不低于老轨（分歧人工抽检定责）、agent 失败率 <2%、单文件墙钟 ≤ 老轨 1.2×；达标后 `agent` 跑满一个 sprint，再删 `excel_preprocess_node.py` 及其测试。shadow 每个 Excel 文件付两份 LLM 费用，只在 test/uat 开。

## 六、提示词

`prompts/extract/excel_agent/agent.system.v1.md`（角色、工具用法、探索策略、输出契约）+ `lg_rules.v1.md`（从 `data_values.html.v3.md` §3 词袋与 §6 特殊规则复制，注明来源与同步责任）。只讲语义判断，不含父链拼接、列锚定、数值转换。经 `_md_loader` 加载，`.py` 只留常量名。

## 七、文件清单

| 文件 | 职责 |
|---|---|
| `source/ai/agent/excel_agent_graph/__init__.py` | 包说明 |
| `.../constants.py` | 三态开关读取、预算常量、错误文案 |
| `.../state.py` | `CellModel` / `RowModel` / `MergedBlock` / `ColumnMeta` / `SheetModel` / `EmitTable` 系列 / `ExcelAgentCtx` / 异常 |
| `.../tools/_sheet_model.py` | Stage A 建模 + 窗口对齐 + 查找 |
| `.../tools/sheet_profile_tool.py` `read_rows_tool.py` `find_rows_tool.py` `emit_table_tool.py` | 四个 @tool（不写 `from __future__ import annotations`） |
| `.../nodes/agent_runner.py` | create_agent 装配、BudgetMiddleware、asyncio.run、gate |
| `.../nodes/assemble.py` | Stage C 组装、探针、shadow 值对照 |
| `.../nodes/excel_agent_node.py` | mega-node 入口 |
| `.../nodes/shadow_node.py` | `with_excel_shadow` 包装 + 对比落库 |
| `source/ai/prompts/extract/excel_agent/*.md` + `source/ai/prompts/excel_agent_prompts.py` | 提示词 |
| `source/lg/db/models/models.py` + `source/lg/db/service/excel_track_shadow.py` + `sql/migrations/business/V023__...sql` | 对比表 |
| `source/llm/infrastructure/langchain/chat_model.py` + `agent.py` | 透传 max_tokens/cache_system/timeout |
| `source/common/enums/caller_node.py` | `CallerNode.EXCEL_AGENT` |
| `source/ai/agent/financial_extract_graph/build.py` + `nodes/parallel_files_node.py` | 开关接线 |
| `source/ai/agent/financial_extract_graph/nodes/shared.py` | 新增公开别名 `post_process_extraction_cells` |
| `pyproject.toml` | 加 `xlrd` |
| `tests/ai/excelagentgraph/*` | 单测（全部 mock LLM） |

## 八、测试

单测覆盖：SheetModel（合并块四类、父链走链、层级信号、稳定 `r`、窗口只向外扩、稀疏坍缩）；组装器（五条变换、label 校验丢行、dense sum/sub_items、四个探针、shadow 值对照）；开关路由三态；预算中间件熔断；shadow 隔离（新轨抛错不污染 state、不写 tables）；DBRouterChatModel 透传。金样本：860439cb 语料与设计稿 12 个真实文件的逐 cell diff 脚本入仓（后续）。
