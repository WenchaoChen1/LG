# Excel 解析优化 · Python 端设计

> 关联文档: [设计理念](./design-philosophy.md) · [前端设计](./frontend-design.md) · [代码示例](./code-examples.md)
> 上游文档: [智能解析 Python 端设计](../../智能解析/调研/python-design.md) · [Excel 科目父链交由代码计算设计稿](../../superpowers/specs/2026-08-03-excel-account-label-join-in-code-design.md) · [trace 分析与耗时优化方案](../../../CIOaas-python/docs/2026-07-27-智能解析trace分析与耗时优化方案.md) · [Python 待优化项台账](../../../CIOaas-python/docs/待优化项.md)
>
> 代码基线: CIOaas-python `sprint117` HEAD `2d0cab55`。文中 `:行号` 均指 `source/ai/agent/financial_extract_graph/nodes/excel_preprocess_node.py`，其它文件显式写出。

## 一、今天 Excel 是怎么交给 LLM 的

Java 上传 S3 后发 SQS，Python `financial_extract_graph` 的 Excel mega-node 一次调用内跑完四段：

| 阶段 | 做什么 | 关键函数 |
|---|---|---|
| Stage 0 渲染 | pandas + openpyxl 读全簿；每 sheet 渲染成带 `rs`/`cs`（rowspan/colspan）、`f="1"`（公式）与 `<tr bg/b/i/sz>` 样式属性的 HTML；货币前缀、百分比 ×100、日期显示串按 number_format 还原；源 A 列稀疏互补合并块坍缩为单行 | `_read_workbook_metadata` :484、`_render_html_with_merges` :1353、`_collapse_label_merge_blocks` :1237、`_cell_td` :1033 |
| Stage 1a 分类 | 每 sheet 截前 200 行 HTML + 程序化预过滤（pivot/invoice/staging 正则），LLM 判 is_financial / table_name / data_type / 多表 anchor | `_build_classify_units` :1590、`_detect_non_financial_sheet` :167 |
| Stage 1b 抽取 | 财务表按 row×col ≤ 500 cell 整发，否则 Plan A 按行切片（chunk = 月份头 + 缩进祖先行 + 一段账户行，保留全部列）；并发 4；LLM 输出三层嵌套 JSON 并逐 cell 转录数值 | `_build_extract_units` :2225、`_slice_sheet_html_by_rows` :2152、`shared.py extract_cells_from_units` :926 |
| 精炼与入库 | 展平 → 父链修复 → RAG override → 列位/行位归一 → 推月份 → 跨表补缺 → 写 `ai_financial_extraction_mapping_data` | `shared.py refine_extraction_node` :2498、`save_to_db_node.py` |

输出契约：`{lg_category: {父级链: [{label, row, pf, cf, ut, cur, cells: [{col, mon, v}]}]}}`。`row` 由 LLM 在 chunk 内自编，加 `chunk_idx × CHUNK_ROW_STRIDE(100000)` 防撞；`source_row_id` 按 `(table_id, row_position, account_label_join)` 分配。

成本模型（实测）：抽取输出速率恒定约 110 tok/s，每 cell 输出约 28 token，单 chunk 生产均值约 95 s / 0.39 美元（opus-5）。**墙钟 ∝ 总输出 token ÷ 并发数，与 chunk 大小无关**；切片只是绕 max_tokens 上限，不省钱。

## 二、闸门一览

| 闸门 | 值 | 位置 | 超限后果 |
|---|---|---|---|
| sheet 逻辑行数硬上限 | 2000 | `:86`、`:1504` | sheet_html 置空，分类跳过；**无 error_message，文件仍 REVIEW_READY** |
| 分类输入行数 | 200 | `:92` | 200 行之后的表不可见 |
| 抽取 cell 预算 | 500 | `:111`、`:2196` | Plan A 行切片；24 列 ≈ 20 数据行/chunk，60 列 ≈ 8 行/chunk |
| 单文件抽取并发 | 4 | `:132` | 进程级 `LLM_PARALLEL_UNITS_MAX=10` 兜底 |
| 动态 max_tokens | cells × 75 × 1.5，下限 2048，上限 98496 | `:114-127` | 配 reasoning 档时放开全额 |
| 抽取超时 / 重试 | 300 s / 1 次 | `constants.py` | 超时 chunk 计入 n_unit_failures |
| SQS 可见性 | 600 s，120 s 心跳续期，最多 3 次投递 | `consumer/heartbeat.py`、`handlers.py:39` | 进程崩两次即整 task FAILED |

## 三、现状缺口（均经代码核实）

### 3.1 合并单元格

| 缺口 | 影响 | 证据 |
|---|---|---|
| 坍缩只认源 A 列：`left == right == 0`，子项列固定读 `df.iat[r, 1]` | "数据从 C 列起"的表（代码自注"很常见"）其稀疏互补块不坍缩、带 rs 交 LLM 逐列求和，正是提示词自认的最高频错因（continuation 行左移 → 错列相加、月份变 N/A）；也违背提示词 §4.5"纯稀疏互补不会到你手上"的承诺 | `:1267`、`:1181`、`:1246-1249`、`:533-536`；`data_values.html.v3.md:352` |
| 稠密 label-merge 块（任一列 ≥2 数值）仍由 LLM 逐逻辑列求和 | LLM 做算术，错则静默 | `data_values.html.v3.md:350-381` |
| `.xls`：xlrd 未声明依赖 → `pd.ExcelFile(engine="xlrd")` ImportError → Stage 0 读失败 → **100% FILE_FAILED**；即便装上，`xlrd.open_workbook` 未传 `formatting_info=True`，`merged_cells` 恒空 | Java 与 Python download_check 都放行 .xls，是真实用户路径 | `:600-623`；pyproject / requirements / uv.lock 均无 xlrd |
| CSV 无合并信息 | 合并块退化为 UNIDENTIFIED 行（静默降级） | `:738-741` |
| 双列分类法大 rs 块不可切片：chunk 边界落在 rowspan 中段时无上限延伸 | 整块进一个 chunk，撞 max_tokens 后 HTML 轨无法拆半重发（`_split_vision_messages_in_half` 对 str 返回 None），只能 json_repair + 记 truncated_table_ids，行静默缺失 | `:2206-2208`、`:2362-2380`；`shared.py:774` |
| 父级链由 LLM 按缩进 / rs / 样式推断 | 语料 17/24 有标签 sheet 无缩进层级（提交 860439cb）；父链错 → lg_category 错且 pf/cf 被标 true 伪装成正常兜底 | 设计稿 §一 |
| 非源 A 列纵向合并、跨标签+数据列的横向合并标题行无专门规则 | 可能被 §4.4 当"跨期合计列"整列跳过（未实测） | `data_values.html.v3.md:319-323` |

### 3.2 大数据量

| 缺口 | 影响 | 证据 |
|---|---|---|
| >2000 行 sheet 静默丢弃 | 文件 REVIEW_READY、0 行；DB 无列、API 无字段、UI 无提示；用户分不清"没识别到"与"被跳过" | `:1504-1516`；`save_to_db_node.py:29-31`；`extract_data_response.py:73-91` |
| 硬上限在全量加载之后才判定 | 20 万行 GL 仍被 openpyxl 逐 cell 遍历 + pandas 全量读入后丢弃（注释自证 2000×200 逐 cell 4.1 s、20 万行 268 MB） | `:516-596`、`:723-731`、`:277`、`:373-375` |
| Plan D"单行太宽整表跳过"分支实际不可达：`data_rows_per_chunk = max(1, budget // width)` | 500 列以上的表以每 chunk 1 行硬跑而非跳过；budget hint 文案仍写已于 2026-05-27 移除的 "column slicing" | `:2196`；`shared.py:90-93`；提交 69f22f91 |
| 上下文行（月份头 + 祖先行）不计入 500 预算，`estimated_cells` 硬记 500 | 60 列表每 chunk 实际 600–720 cell；max_tokens 靠 4 倍余量掩盖 | `:2199-2219`、`:2341` |
| 部分 chunk 失败 / 截断只留日志 | 只有全部 unit 失败才报 "Data extraction failed"；用户看到"抽出来了但少了行" | `shared.py:2536-2542`、`:2561-2572` |
| 只限行数不限列数；分类只看前 200 行 | 极宽表直接进抽取；200 行后开始的表分类看不到（是否真实发生：未实证） | `:89-92`、`:1642-1668` |
| 分类 prompt cache 命中仅约 23% | 首波 4 并发同时发出全部 miss；可缓存约 1 万 token 系统提示词大部分全价 prefill | `docs/待优化项.md:55` |
| 30 sheet 工作簿 | 分类 30 unit / 4 并发 ≈ 8 波；抽取受单文件并发 4 限制；finalize normalize 8192 上限确定性截断（生产 22 次 4 次） | `:132`；trace 文档 §2 |

### 3.3 已实现又被整树回退的三项基础设施

| 提交 | 内容 | 验证 | 回退 |
|---|---|---|---|
| `69f0ad98` | `<tr r="N">` 稳定行 id + 代码按缩进走链算父链注入展平层 | MXTR 两表 31/31、41/41 复现 LLM join；设计稿合成 fixture 292/292、生产用例 24/24 | `ac5fdb28`（2026-08-28） |
| `e9e32492` | 输出降两层 `{lg: [rows]}`，§4.6.3 缩为"父级语境"，system 31,811 → 28,028 chars | — | `ac5fdb28` |
| `610e0c81` | Markdown 入参（列 r / parent_chain / account / c1..cN）+ O(行) 精简出参，代码按 (r, cols) 回填值 | Bevz P&L 60×27：completion 26,622 → 4,547（−82.9%），墙钟 244 s → 47.5 s（−80.5%）；4 表值定位 912/912、88/88、52/52、24/24 零错位 | `d9118cca` |
| `32f70e16` | 分类入参 Markdown 替代 HTML | 36 sheet 分类 user msg 51,088 → 27,650 tok（−46%） | `d9118cca` |

回退提交信息："The feature/sprint115-optimize line is not going to main for now"，用 `git read-tree --reset 8f5cbb8e` 整树覆盖；未提任何线上故障或准确率问题，并专门重新应用了两处独立 bug 修复。代码仍在 `origin/feature/sprint115-optimize` 与 sprint117 历史中。**注意**：不能直接 cherry-pick——当前树已加 `row_attrs`（`_build_logical_grid` 第 3 返回值）、5 元组 `_GridCell`、`860439cb` 的样式属性，需按思路重写。

## 四、方案矩阵

评分为三视角对抗验证均分（可落地 / 准确率 / 成本，各 1 到 5）。"未验证"表示验证未完成，结论按同机制族推断。

| # | 方案族 | 解决 | 机制 | 评分 | 结论 |
|---|---|---|---|---|---|
| 1 | 跳过可见 + 流式预检 | 大表 | state 加 `skipped_sheets` / `warning_message`；`ai_file_registry` 新增 TEXT 列（V023）；`ExtractFileItem.warning`；预检用 read_only `iter_rows` 非空计数 early-exit | 4.0 | **推荐 P0**。预检只能省 pandas 一遍，**内存不降**（非只读加载器一次解析全簿，read_only 无 `merged_cells`）；**禁用 `ws.max_row`**（仅格式的远端 cell 撑到数万行会误跳真报表） |
| 2 | 成本旋钮 | 大表 | cache 预热；确认 `OCR_CLASSIFY_MODEL` 降档；`_TOKENS_PER_OUTPUT_CELL` 75→60；并发 4→8；上下文行计入预算让 Plan D 可达 | 未验证 | **推荐 P0**，但 Plan D 可达会把"部分产出"变"零产出"，须与 #1 同批；系数别压到 40（HTML 轨截断不可救）；并发 8 需确认账号 tier |
| 3 | 坍缩按实际标签列 + .xls 补齐 | 合并 | 判块条件改"源 col0 ∪ 最左含文本列"，冲突判定与求和只扫子项列右侧；加 xlrd + `formatting_info=True` | 3.7 | **推荐 P0**。**不能**直接用 `_pick_label_col` 的文本最密列（双列分类法表 col1 每行有文本必被挑中，现有源 col0 坍缩反而失效）；上线前用 860439cb 语料比对坍缩块数 |
| 4 | 稠密 label-merge 代码求和 | 合并 | has_conflict 块由代码逐列 `sum`，行打 `lm="N"` | 3.7（#3 的②） | **有条件 P2**。"含公式不求和"排除条件在 85% 公式语料上让机制形同虚设；块内小计双计不可判定；提示词原规则保留，先建金样本 |
| 5 | 代码拍平多级列头 / chunk≥1 带回年份 cs 头 | 两者 | colspan 展开 + 前向填充推 col → YYYY-MM 作 Stage 2 强锚点；后续 chunk 不再只带月份头一行 | 未验证 | **带回 cs 头这半边推荐 P0**（便宜、正向，已在 #13 验证中确认）；全量拍平列头解析器长尾大，只填 LLM 留 None 的 cell，尊重其排除的 Total 列 |
| 6 | 稳定行 id + 代码父链 | 合并 | `<tr r=N>`；代码走链算纯父链（不含自身）注入 `_explode_nested_extraction`；LLM 输出两层 | 3.0 | **推荐 P1 前置**。69f0ad98 只会缩进走链，在 17/24 无缩进 sheet 上"以代码为准"会覆盖 LLM 的样式派生链而倒退 → 按信号可用性决定权威；保留 `label` 作 checksum（约占 completion 6–8%）；Stage 1b.5 repair 对代码接管行门控；≥100 张真实 sheet_html 离线回放 |
| 7 | 精简出参 + 代码回填值（spec D12） | 大表 | LLM 只回 `(r, lg, pf, cf, ut, cur)` 与 `cols`/`mon_set`，代码按 (r, 物理列) 从**渲染后文本**取值组装 cells | 3.7（成本 5/5） | **推荐 P1 主线**。60 列表推算 −89% 成本 / −95% 墙钟。条件：依赖 #6；值源必须用 `_cell_td` 渲染文本而非 df 原值（否则百分比差 100 倍、非 17 币种前缀解析成 null）；rs 块要有求和规则；预算 500 → 1600 → 3000 分档 A/B；金样本脚本入仓 |
| 8 | 两遍法（先出读取计划再取值） | 两者 | 第一遍只看结构出 read_plan；代码按计划取值；第二遍逐行判语义 | 3.3 | **P2**，仅对超大 / 含 rs 块表；"shared 零改动"不成立（需 `assemble_fn` 钩子）；计划校验须对照代码先验而非 TOTAL 列 |
| 9 | 算术校验闸门 + 定向修复 | 两者 | 代码用源网格复算行内 Total、`Total <X>` 区间和、位置比对；不一致回送片段修一次 | 3.3 | **"只校验不修复"推荐 P1**（零 LLM 成本，目前唯一能检出截断丢行的手段）；TOTAL 列识别现无代码需新写；label 匹配不可靠，位置比对等 #6 的 `r`；修复调用等生产统计后再开 |
| 10 | GL 流水代码聚合轨 | 大表 | 列头指纹判 GL → pandas `groupby(科目, 月)` → 合成小表走现有抽取或直接产条目；LLM 只判列角色 / 科目映射 | 未验证（3 变体） | **P2，需产品拍板**。#11 验证给出的硬伤同样适用：GL 按月 SUM 对 7 个 BS 科目得到**发生额而非余额**；与"GL detail 非财务报表"分类政策相悖；QBO 式导出有分段标题与小计行；先加遥测看 >2000 行 sheet 频率 |
| 11 | duckdb 工具智能体 | 大表 | ReAct 只读 SQL 探索并 emit | 2.3 | **不推荐（原稿）**，理由见[设计理念 §五](./design-philosophy.md#五否决的方案与理由) |
| 12 | 合并块 LLM 微裁决 | 合并 | 对未坍缩 rs/cs 块发无数值微调用 | 2.7 | **不推荐**，同上 |
| 13 | map-reduce：尾部语境 + reduce 归一 | 大表 | chunk≥1 带上一片尾 3 叶子行；合并后 LLM 出 patch | 3.0 | **只保留 cs 头带回**（并入 #5） |
| 14 | 分类锚点采样替代前 200 行 | 大表 | 脚手架 + 头 40 + 边界上下文 + 尾 10 行 | 3.7 | **backlog**：需求未实证；先用 classify 日志量化 |

## 五、推荐路线总览

```
P0  跳过可见 + 预检（省 pandas 一遍）+ Plan D 修正 + .xls 补齐 + 坍缩标签列泛化 + cs 头带回 + cache 预热/模型分档/max_tokens 系数
P1  稳定行 id + 代码父链 (#6) → 精简出参 + 代码回填值 (#7) → 算术校验（只校验）(#9)
P2  GL 聚合轨 (#10，先拍板) · 两遍法 (#8) · 稠密块代码求和 (#4，先金样本) · 分类锚点采样 (#14，先量化)
```

## 六、P0 落地步骤（Python 侧）

| 步 | 改动点 | 验证闸门 | 预期收益 |
|---|---|---|---|
| 1 | **跳过可见**：`state.py MainGraphState` 与 `node_return.py ExcelPreprocessReturn / RefineExtractionReturn` 声明 `skipped_sheets: NotRequired[list[dict]]`、`warning_message: NotRequired[str]`（不声明会被 LangGraph 静默丢弃）；`download_check_node.py:183-188` per-file 重置加两项；`_load_and_render_sheets` 写 reason=`too_many_rows`；`_build_classify_units` 返回形状带出预过滤命中 reason=`non_financial_prefilter`，LLM 判非财务写 reason=`classified_non_financial`（最常见的 GL 静默路径）；`_build_extract_units` 切片失败写 reason=`table_over_budget`；`refine_extraction_node` 把 skipped + truncated + 部分失败汇成 warning（**不写 error_message**，否则 `save_to_db` 翻成 FILE_FAILED 且 refine 防御 1 短路）；`extract_financial.update_file_status` 多写一列；`extract_data_response.ExtractFileItem` 新增 `warning: str = ""`（只新增不改既有字段名）；devSupport 管理域 `task_manage_service.py:137` 同步 | 三类 xlsx fixture 端到端：>2000 非空行 early-exit；1999 非空行 + 3 行仅由合并区覆盖（预检不触发、终判触发，验证一致）；A1 标题 + C50000 仅格式空 cell（不得误跳）；跑 860439cb 语料确认 0 个 sheet 新增被跳 | 消除现状最大静默丢数据点；Java 零改动（extract-data 由 Python 承接） |
| 2 | **预检**：`_load_sheet_dataframes` 前插 `openpyxl.load_workbook(read_only=True)` 逐 sheet `iter_rows(values_only=True)` 计非空行，到 2001 即停；触发者不进 `pd.read_excel` 与 `_logical_size`；未触发者仍走 `_logical_size` 终判（预检按 notna 计恒 ≤ 终判的 notna ∪ merged-range 口径，单向安全）。**不用 `ws.max_row`** | 同上 | 省 pandas 一遍 + 双循环；不承诺内存下降 |
| 3 | **Plan D 修正**：`_slice_sheet_html_by_rows` 预算扣上下文行 `(budget − ctx_cells) // width`，结果 <1 返回 None 使 skipped 路径可达；`_build_extract_units` 的 `estimated_cells` 改真实 chunk cell 数；更正 `:103`、`:109`、`:2313-2325` 注释；`shared.py:90-93` 文案字面禁改，先记待优化项待前端确认 | `test_excel_extract_budget.py` 增：宽表 chunk 数、600 列表 → None → skipped | 让 max_tokens 反映真实输出规模；Plan D 从不可达变可达（**必须与步 1 同批**） |
| 4 | **.xls**：`pyproject.toml` / `requirements.txt`（`uv export --no-dev` 重导）加 xlrd；`_read_workbook_metadata` xls 分支 `open_workbook(formatting_info=True)`；顺手读 XF `format_str` 补 percent_decimals / currency_prefixes（做不到则提示词 :289 明写 .xls 百分比可能为裸比值）；先查 `d9118cca` 回退 xlrd 的原因 | 1 个真实 .xls fixture 逐 cell 断言 | .xls 从 100% 失败变可解析且带合并信息 |
| 5 | **坍缩标签列泛化**：`_collapse_label_merge_blocks` / `_is_col0_label_merge` / `_block_numeric_profile` / `_collapse_one_column` 参数化 label_col 与 child_col；判块条件"源 col0 ∪ 最左含文本 cell ≥ max(3, 20% 数据行) 的保留列"；冲突判定与取值只扫 child_col 右侧；实现顺序写死：坍缩前 keep mask → 选 label_col → 坍缩 → 坍缩后重算 keep mask；`_logical_size` 移到坍缩后、cap 判定前 | 新增 `test_excel_label_merge_collapse.py`：稀疏 col0 / 稀疏 C 列起 / 双列分类法保留 rs / 纯占位不坍缩 / label_col 左侧数值列不计冲突；860439cb 语料前后坍缩块数对照 | 把最高频错因在 A 列为空的常见表上堵住；零契约、零提示词改动 |
| 6 | **cs 头带回**：`_slice_sheet_html_by_rows :2186-2193` 的 `month_only_indices` 改为表头区索引（年份 / 季度 cs 头 + 月份头，通常 2–3 行） | `test_excel_row_style.py` 增 chunk≥1 含年份头断言 | 后续 chunk 的 mon 不再全靠 Stage 2 按列位链式推 |
| 7 | **成本旋钮**：`llm_concurrency.parallel_llm_invoke_units` 加 `warm_first`（unit ≥3 才预热）；核对各环境 `OCR_CLASSIFY_MODEL` / `OCR_EXTRACT_MODEL`；`_TOKENS_PER_OUTPUT_CELL` 75→60；`_EXTRACTION_MAX_WORKERS` 4→8 前确认 OpenRouter 账号并发 tier | `ai_llm_call_log` 的 `usage_cached_tokens` 与 `truncated_table_ids` 非空率 <0.5% 作回滚闸门 | 分类输入成本约 −73%；OpenRouter 预扣配额下降 |

## 七、P1 落地步骤（主线）

前置动作：向 `ac5fdb28` 提交者确认回退原因并写进本目录；把设计稿 12 个真实 Excel 的交叉校验与 860439cb 的 35 sheet 逐 cell diff 脚本化入仓（可放 `tests/ai/nodes/` standalone 脚本目录）作放行闸门。

| 步 | 改动点 | 验证闸门 |
|---|---|---|
| A | **稳定行 id + 代码父链**（以 69f0ad98 / e9e32492 为思路重写）：`_render_html_with_merges` 给 `<tr>` 打 `r="N"`（原始 df 行号，单调不连续）；`_build_logical_grid` 返回 `(grid_cells, width, row_attrs, row_ids)`，所有 `_GridCell` 解包改 5 元组；新增 `_resolve_account_joins` / `_labels_by_row`；unit 带 `join_by_row` / `label_by_row` / `valid_row_ids`；`shared._explode_nested_extraction` 可选参数注入纯父链（不含自身，由现有 `" || ".join([parent, label])` 拼接，误注全路径会 `A \|\| A` 且入库不报错）；Excel 轨 `chunk_row_offset` 置 0、`CHUNK_ROW_STRIDE` 退役；`repair_account_label_joins_in_tables` 对代码接管行跳过；提示词 rename v3 → v4：`row` 改为回传 `r`，§4.6.3 缩为"父级语境"；恢复 `test_excel_account_joins.py` / `test_inject_code_joins.py` 并适配 | 阶段 A：**按信号可用性决定权威**——仅当 sheet 存在 ≥2 级缩进时代码接管，无缩进 sheet 保持 LLM 父链只记分歧；保留 `label` 作 checksum；`matched / diverged / relocated / unresolved` 写进 span 属性可查询；860439cb 语料 + ≥100 张真实 sheet_html 离线回放，样式层级 sheet 上代码不得劣于 LLM。阶段 B（删 LLM 父链）要求 diverged <2% 且 unresolved <1% 持续两个 sprint |
| B | **精简出参 + 代码回填值**（以 610e0c81 `tableutil/values.py rebuild + probe_losses` 为蓝本移植到 HTML 网格）：unit 新增 `value_lookup`（从 `_build_logical_grid` 的 `<td>` 文本取值，即 `_cell_td` 渲染后字符串）；`shared.extract_cells_from_units` 按 unit 是否带 `value_lookup` 分派新展平器，旧三层路径原样保留（vision 轨零改动）；出参 `{mon_set, cols, data: {lg: [{r, label, pf, cf, contra, ut, cur}]}}`；套 §4.6.4 五条确定性变换（去千分位、括号负、去货币符、去百分号、空 → null），`contra=true` 取 `-abs()`；对 rs>1 的 col0 anchor 行按 §4.5 规则代码求和；`_EXTRACTION_CELL_BUDGET` 语义改为输入预算，`_estimate_extract_max_tokens` 改按行数（保留 reasoning 档全额联动，`test_excel_extract_budget.py` 锁死）；探针：`cols` 外有数值列 / emit 集合外有数值行 / `r` 非法 / 看似数值解析失败 → 任务级告警 | 阶段 A 双跑：同 (r, cn) 绝对值集合吻合率 ≥99%（spec §5.5 口径），样本含 MXTR BS/P&L、Bevz、`[$INR]` 类前缀、稠密 label-merge、数据区 cs；预算 500 → 1600 → 3000 三档比 emit 行召回与 lg 一致率，取最后一个不退化档 |
| C | **算术校验（只校验）**：抽取合并后、refine 之前（refine 的 1d 会改写 row/col 位）新增 `_verify_against_grid`：新写 TOTAL/YTD 列识别（词表与提示词 :309 同源）并把 LLM 的 cn 映射回物理列；行内 Total、`Total <X>` 行回溯区间求和、按 `r` 位置比对；跳过规则显式化（ut=PERCENT 行、行内 cur 不一致、公式缓存空、Total 列识别失败、无 Total 且无 `Total <X>` 行）；结果写 `verify_failed_rows`（state.py + node_return.py 双声明）并透到 devSupport 回放页 | 生产跑 ≥2 周统计 discrepancy 率与类型分布，再决定是否开定向修复及其模型档 |

## 八、P2 候选与前提

| 方案 | 前提 |
|---|---|
| GL 流水代码聚合轨（#10） | 产品拍板 GL 是否允许派生入库；范围收缩为 P&L 类科目（BS 科目一律不从 GL 派生，除非有 Beginning Balance 列）；≤2000 行 GL 与 >2000 行统一政策；遥测 >2000 行 sheet 出现频次；≥10 份真实 GL 导出（QBO 分段式、Xero 平铺式、Debit/Credit 双列、带小计行）金样本；LLM 只出列角色与科目映射，代码执行聚合并物化 cells；`mapping_data` 需能标"派生聚合"与来源 sheet |
| 两遍法（#8） | 在 #7 之后仅对输入 HTML 超约 50K token 或含未坍缩 rs 块的表启用；`extract_cells_from_units` 加可选 `assemble_fn(unit, parsed)` 钩子；计划校验对照代码先验（月份头行、按列数值密度的数据列集合、祖先行），任一分歧回退 v3 |
| 稠密块代码求和（#4） | 排除条件改为可判定项：块高 ≤12、块内某列数值个数 == 块高、无一行等于其余行之和；percent 列 / 混合货币前缀 / 公式缓存缺失即降 unknown；4 类 fixture（稀疏 col0 / 稀疏 C 列起 / 稠密无小计 / 稠密含小计反例）+ 1 个真实 .xls |
| 分类锚点采样（#14） | classify 日志统计 >200 逻辑行且含财务表的 sheet 比例接近 0 则降 backlog；否则采样选区须对齐 rs 块边界、展示行号 → 真实行号由代码映射、两轮金样本分类 diff 硬闸门 |

## 九、外部参考

- SpreadsheetLLM / SheetCompressor（结构锚点、倒排索引、格式聚合；压缩 25 倍；聚合丢确切数值）：https://arxiv.org/abs/2407.09025
- Table Meets LLM（HTML 对合并单元格检测 76.67%；格式说明伤检索）：https://arxiv.org/abs/2305.13062
- A Closer Look into LLMs for Table Understanding（新模型 Markdown vs HTML 差 1–2 pp）：https://arxiv.org/abs/2603.15402
- TableRAG（全表直读 ≥100 行退化；检索式 49.2% vs 4.6%）：https://arxiv.org/abs/2410.04739
- Rethinking Tabular Data Understanding（代码代理对转置表 −77.73%）：https://arxiv.org/abs/2312.16702
- Anthropic Files API 支持的内容块与 xlsx 处理指引：https://platform.claude.com/docs/en/build-with-claude/files
- Docling MsExcelDocumentBackend（BFS + gap_tolerance 切子表、锚点记 span）：https://github.com/docling-project/docling/blob/main/docling/backend/msexcel_backend.py
