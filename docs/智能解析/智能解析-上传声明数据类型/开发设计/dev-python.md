# 手动上传时声明 Actuals / Proforma · Python 开发设计

> 关联文档：
> - 上游（第四阶段 · 功能设计）：[design-doc](../设计/design-doc.md) —— D1 ~ D10 已定，本文照做、不再论证；Python 规则在其 §5
> - 需求：[requirement-doc](../需求/requirement-doc.md)（R3 / R4 / R5 / R10 / R11 与本文直接相关）
> - 参考代码：[code-examples](./code-examples.md) 的「Python」一节（V030、两个新 helper 骨架、init_task 映射、测试桩）
> - Java 侧：[dev-java](./dev-java.md)（写 `business_type`、§10 J-R2 / J-R4 与本文风险项互指）；前端开发设计各自成文
> - 被取代的旧规则：[需求文档-Actuals导入中处理当前日历月数据](../../需求文档-Actuals导入中处理当前日历月数据.md)
> - 智能解析 Python 总体方案：[python-design](../../调研/python-design.md)

本文只写 **Python 怎么改**：改哪些文件、新步骤插在哪、删什么留什么、测试怎么动。按 `docs/CLAUDE.md`，
完整函数与 DDL 放 [code-examples](./code-examples.md)，本文只给签名与插入点。

路径简写：`graph/` = `CIOaas-python/source/ai/agent/financial_extract_graph/`。
行号基于 `CIOaas-python` 分支 `sprint121`、提交 `70ca1e6a`（2026-10-10）。

---

## 1. 代码基线核对

| 设计前提 | 代码现状 | 结论 |
|---|---|---|
| init_task 组装文件清单时能读到 `business_type` | `graph/nodes/init_task_node.py:79-98` 查的是整个 `AiFileRegistry` ORM 对象（`ef`），`business_type` 已映射（`lg/db/models/models.py:190`） | ✅ 查询不用改，直接读 `ef.business_type` |
| "文件判 FILE_FAILED" 有现成机制可用 | 现有 FILE_FAILED 只有两条路：`save_to_db_node.py:30-41`（`is_corrupted` 或 `error_message` → `update_file_status`）与 consumer 的 `settle_stuck_file_claims`（只动 PROCESSING）。**init 阶段没有逐文件失败机制** | 新增：init 内直接写 FILE_FAILED + 不进 `file_list`（§3.2） |
| Stage 2.6 / 2.8 的位置 | `graph/nodes/shared.py:2680-2724`：Stage 2 → 2.6 → 2.7 → 2.8 → 2.85 → 2.45 → 2.5 | 2.6 原位替换，2.8 删除，护栏插在 2.6 之后、2.7 之前（§4.1） |
| "沿用传给大模型的参考日期"（D6） | 大模型的参考日期在各 preprocess 里各取一次 `datetime.now(timezone.utc)`（`pdf_preprocess_node.py:405`、`:554`，`image_preprocess_node.py:237`，`excel_extract_agent/locate.py:79`）；refine 自己再取一次（`shared.py:2691`），2.6 / 2.8 用的是 refine 这一份 | **同一口径、不是同一个值**。护栏沿用 refine 自取的那一份（与旧 2.8 相同）；跨 UTC 月末的极端时刻两者可能差一个月，因模型的类型判定已不参与结果，无影响 |
| 训练信号 / RAG override / task 级归一化不看类型 | `ai_financial_training_data.py`、`consumer/learn/`、`ai_financial_embedding_service.py`、`finalize_extract_node.py` 中 `data_type` 均 0 处命中 | ✅ 不动 |
| Python 读 `business_type` 的地方只匹配 rag 取值 | `file_registry_repository.py` / `lg/db/service/file_registry.py` 全部是 `== KNOWLEDGE_BASE / SESSION_UPLOAD / PLAYBOOK` 等值过滤；`file_registry_service.py:520-524` 的下载分支对两者之外的取值与 NULL 走同一条路 | ✅ `EXTRACT_FI_*` 行与今天的 NULL 财务行行为完全一致 |
| `business_type` 无 CHECK、长度够 | ORM `String(40)`；最近一次列注释在 `sql/migrations/business/V023__sprint118_erl_attachment_summary_only.sql:36`，无约束 | ✅ V030 只改 COMMENT；business 迁移树当前最大号 V029，全部分支无 V030 |

---

## 2. 改动清单

| # | 文件 | 动作 | 内容 | 节 |
|---|---|---|---|---|
| 1 | `graph/nodes/init_task_node.py` | 改 | 读 `business_type` → `FileInfo.data_type`；未声明 / 非法 → `update_file_status(FILE_FAILED)` 且不进 `file_list`；模块 docstring Step 3 补一句 | §3 |
| 2 | `graph/state.py` | 改 | 新增 `DataType = Literal["ACTUALS", "PROFORMA"]`；`FileInfo` 加必填键 `data_type: DataType`；模块 docstring 的「只投影三个字段」注记补 `data_type` 同理；**删** `RawRow.parent_table_id`（`:98-101`） | §3.3 / §7 |
| 3 | `graph/nodes/shared.py` | 改 | 删 Stage 2.6 / 2.8 及其专用常量；新增 Stage 2.6 `apply_declared_data_type_in_tables`、Stage 2.65 `drop_current_and_future_actuals_in_tables`；改 refine 接线；同步 `__all__` 与 6 处注释 | §4 |
| 4 | `source/lg/db/service/extract_financial.py` | 改 | 删 `save_extracted_tables` 里的 `parent_table_id=cell.get(...)`（`:433-434`，连同注释） | §7 |
| 5 | `source/lg/db/models/models.py` | 改（仅注释） | `AiFileRegistry` 类 docstring（`:128-137`）与 `business_type` docstring（`:190-192`）；`ExtractedData.parent_table_id` 行尾注释（`:286`） | §7 / §8 |
| 6 | `sql/migrations/business/V030__sprint121_ai_file_registry_business_type_extract_fi.sql` | **新增** | 只有一条 `COMMENT ON COLUMN ai_file_registry.business_type` | §8 |
| 7 | `source/ai/agent/excel_extract_agent/verify.py` | 改（注释 + 文案） | ⑨b data_type WARN（`:832-849`）的注释与两条 WARN 文案，逻辑不动 | §6 |
| 8 | `source/ai/agent/excel_extract_agent/pipeline.py` | 改（仅注释） | `:103` page_number 行尾注释、`:105-109` data_type 注释、`_data_type_of` docstring（`:180-185`） | §6 |
| 9 | `source/ai/CLAUDE.md` | 改 | `:47` init_task 行、`:49` shared.py 行的 Stage 清单 | §9 |
| 10 | 测试 | 删 2 / 改 1 / 增 2 | 见 §10 | §10 |

不改：提示词（§6）、`build.py`、`parallel_files_node.py`、`save_to_db_node.py`、`finalize_extract_node.py`、
`ai/nodes/file_download_check_node.py`、SQS 消费与消息结构（D4）。

---

## 3. init_task：读声明类型

### 3.1 映射

模块常量 `_DATA_TYPE_BY_BUSINESS_TYPE: dict[str, DataType]` 只两项：`EXTRACT_FI_ACTUALS → ACTUALS`、
`EXTRACT_FI_PROFORMA → PROFORMA`（D3：对内 `EXTRACT_FI_*`，对外与单元格 `ACTUALS / PROFORMA`，Python 只在这里转一次）。
**精确匹配、区分大小写**：`None` / 空串 / rag 取值 / 小写 / 直接写 `ACTUALS` 一律视为未声明——Java 侧 T1 用例
（[dev-java](./dev-java.md) §9）把这两个字面值钉成跨语言契约，Python 不做宽容归一。

常量只放 `init_task_node.py`：唯一读取方就是它，不下沉 `common/enums`（YAGNI）。

### 3.2 未声明 → FILE_FAILED：选型与时序

在 Step 3 的循环里（`init_task_node.py:91-98`）：映射得到类型 → 照常组 `FileInfo` 并带上 `data_type`；
映射不到 → 记入 `undeclared` 列表、**不进 `file_list`**。读 session 关闭后，逐个调
`update_file_status(file_id, FILE_FAILED, _ERR_DATA_TYPE_NOT_DECLARED)`（`extract_financial.py:303`，自开写事务），
每个文件一条 WARNING（带原始 `business_type` 值）。`read_files` 那条 INFO 日志加 `undeclared=%d`。

文案（禁改字面，经 `get_extract_data` 展示在文件行上，与既有 "File parsing failed" 同风格）：
`"Table type (Actuals / Proforma) was not declared for this file; please re-upload it"`。

**为什么在 init 写库、而不是让文件进 `file_list` 再在下游失败**：

| 备选 | 问题 |
|---|---|
| 进 `file_list`、标 FILE_FAILED，靠下游跳过 | 串行环路没有终态跳过逻辑——`download_check` 会照常下载、preprocess 照常调 LLM（只有并行节点的幂等守卫 `parallel_files_node.py:124-140` 会跳） |
| 在 refine 发现缺类型时置 `error_message` | 文件已经跑完 Stage 1a/1b 的全部 LLM 调用，白花钱 |
| 改公共节点 `download_check` 判类型 | 公共节点（`ai/nodes/`）不该承载本图业务规则 |

**被排除后任务终态仍正确**，不用改 finalize：`_finalize_task_status`（`finalize_extract_node.py:178`）对
`file_list` 判 `all_errored`，空列表视为全失败。

| 本批文件 | `file_list` | 任务终态 |
|---|---|---|
| 全部未声明 | `[]` → `_route_after_init` 走 `done`（`build.py:109-110`） | FAILED（有历史 REVIEW_READY 文件则 REVIEWING，与现状同） |
| 部分未声明、其余成功 | 只含已声明文件 | REVIEWING |
| 部分未声明、其余也失败 | 只含已声明文件，全有 `error_message` | FAILED |

重投安全：SQS 重投从 START 重跑，init 只选 `status == UPLOADED`（`init_task_node.py:86`），已判 FILE_FAILED 的文件
不会再被选中；consumer 的 `settle_stuck_file_claims` 只动 PROCESSING，也碰不到它们。

⚠️ 这是一条**新的状态迁移** `UPLOADED → FILE_FAILED`（今天的失败都经过 PROCESSING）。Java / 前端按终态展示，
联调时确认没有"必须先 PROCESSING"的假设（§12 R1）。

### 3.3 声明类型怎么到 refine

`FileInfo` 加必填键 `data_type: DataType`（init 保证进 `file_list` 的文件必有值）。它与 `file_format` 一样**只在
`file_list[current_file_index]` 里**，不投影到 state 顶层（`state.py:7-9` 的注记补一句"`data_type` 同理"）。
沿途三处复制都是整条 dict 拷贝，新键自然保留：`file_download_check_node.py:124-128`、
`parallel_files_node.py:225`（每 worker 一份）、`save_to_db_node.py:53`。

refine 直接下标读取 `state["file_list"][state["current_file_index"]]["data_type"]`，**不做缺省兜底**：缺键 =
编程错误，抛出比静默按 ACTUALS 处理安全（D9 不回退推断）。

---

## 4. refine_extraction_node 改造

### 4.1 Stage 顺序：现状 → 改造后

现状（`shared.py:2659-2729`，正常路径）：

| 行号 | Stage | 函数 |
|---|---|---|
| 2663 | 1b.5 | `repair_account_label_joins_in_tables` |
| 2669 | 1c | `_apply_rag_override_safe` |
| 2674-2679 | 1d | `renumber_column_positions_by_month` / `align_row_positions_across_blocks` / `warn_on_merged_table_anomalies` |
| 2680 | 2 | `infer_missing_months_in_tables` |
| 2681-2705 | 2.6 | `finalize_data_type_in_tables`（连同取 `sheets`、`reference_date`、`file_format`） |
| 2709 | 2.7 | `infer_missing_rows_per_account` |
| 2712-2714 | 2.8 | `split_proforma_tail_in_tables` |
| 2719 | 2.85 | `dedupe_duplicate_month_cells_in_tables` |
| 2723 | 2.45 | `apply_zero_default_in_tables` |
| 2724 | 2.5 | `finalize_source_is_mapped_in_tables` |

改造后：1b.5 → 1c → 1d → 2 → **2.6 声明类型落表** → **2.65 Actuals 当月护栏** → 2.7 → 2.85 → 2.45 → 2.5。
即 `:2681-2705` 整段换成"取声明类型 + 取参考月 + 两次调用"，`:2710-2714` 删除。主方法仍是平铺调用，无分支。

**护栏插在这里的理由**（逐个对着前后 Stage）：

| 相邻 Stage | 为什么护栏必须在它之前 / 之后 |
|---|---|
| 2（推月份）**之后** | 推出来的月份也要查——含被推成"末月 + 1"的合计列（设计 §5.3）。放之前的话这类 cell 还没有月份，会被当成"无月份"保留；而且先剔会拿走 Stage 2 的月份锚点、改变其余列的推断结果 |
| 2.7（跨表补行）**之前** | 2.7 的"组内月份互不相交 + 连续"判据与补出的占位 cell 都按表内月份算；后剔会让它按最终不入库的月份做判断，并为将被剔掉的月份补占位 |
| 2.85（同月去重）**之前** | 去重按"月份跨度最大"选权威表；跨度应按最终入库的月份算 |
| 2.45（补零）/ 2.5（source_is_mapped）**之前** | 只处理最终入库的 cell；2.5 按行判"任一 cell 月份不可信 → 整行降级"，被剔掉的推断列不该再拖累同行 |

2.6 放在护栏之前只是为了读起来顺：护栏吃的是显式参数 `data_type`，不依赖表上的类型。

### 4.2 Stage 2.6：`apply_declared_data_type_in_tables`

签名：`(tables, file_id, *, data_type: DataType) -> list[TableInfo]`。

- 每张表 `data_type` 一律设为声明类型（需求 R3）。**不看 `is_financial`**：进到 refine 的表三条轨都只含财务表
  （旧轨 `shared.py:446-453` 判 false 直接 `continue`；坐标轨只塞财务表），且 `save_extracted_tables` 本来也不看它。
- 一条 INFO：`declared_data_type: file_id=… data_type=… tables=… llm_disagreed=…`。`llm_disagreed` = 模型给的类型
  （含没给）与声明不一致的表数——零成本的观测量，用来回答"声明与模型判定多常打架"。
- 返回新 list，不原地改入参。

### 4.3 Stage 2.65：`drop_current_and_future_actuals_in_tables`

签名：`(tables, file_id, *, data_type: DataType, reference_month: str) -> list[TableInfo]`。

| 规则 | 实现 |
|---|---|
| PROFORMA 不剔（R5） | `data_type != "ACTUALS"` 直接原样返回 |
| 剔除对象（R4） | `column_month` 匹配 `_MONTH_RE`（`YYYY-MM`）且 `>= reference_month` 的 cell；`YYYY-MM` 字符串比较即时间序，跨年正确 |
| 推断月份同样检查 | 不看 `is_predict_month` |
| 无月份保留（R4 末条） | `None` / `""` / 非 `YYYY-MM` 一律保留——与 2.85 / 旧 2.8 同一个 `_MONTH_RE` 口径 |
| 整表剔空 | 有 cell 且全被剔的表从列表移除；原本就空的表不动（不扩大行为面） |
| 列位 / 行位 | **不重排**。留洞有先例：旧 2.8 拆出的尾表列位从 N 起（`shared.py:1813-1814`），2.85 软删的行在读取时被过滤 |
| 日志 | 一条 INFO：`actuals_guard: file_id=… ref_month=… dropped_cells=… dropped_tables=… dropped_months=[…]`——"为什么我 10 月的数据没了"靠它排查 |

`reference_month` 由 refine 传入：`datetime.now(timezone.utc).strftime("%Y-%m")`（D6，与旧 2.6 / 2.8 同一口径）。
做成参数是为了单测注入，不在 helper 内部取时钟。

### 4.4 整个文件被剔空

护栏把全部表移除后 `tables=[]`，后续 2.7 / 2.85（`len < 2` 直接返回）、2.45、2.5 都在空集合上空转，refine 返回
`tables=[]`、无 `error_message` —— 与"没识别到财务表"（refine 防御 2，`shared.py:2622-2627`）**同形**：
`save_to_db` 判 REVIEW_READY、`save_extracted_tables` 不开 session、0 行；`finalize` 里它算 `any_ready`，单文件任务
落 REVIEWING。与设计 §5.3"按解析完成但没有数据处理"一致，不另加提示（D5）。

### 4.5 删除 / 保留清单（`shared.py`）

| 符号 | 处置 | 依据 |
|---|---|---|
| `finalize_data_type_in_tables`（`:1417-1542`，含章节横幅） | **删** | 被 2.6 取代；`coding.md` §6「禁止废弃代码」 |
| `split_proforma_tail_in_tables` + `_PROFORMA_SPLIT_NAMESPACE`（`:1773-1926`） | **删** | 被 2.65 取代；新任务不再产 `parent_table_id` |
| `_PROFORMA_KEYWORDS_RE`（`:109-117`） | **删** | 唯一使用方是旧 2.6 |
| `_DATA_TYPES`（`:122-124`） | **删** | 唯一使用方是旧 2.6 |
| `_MONTH_RE`（`:119-120`） | 保留 | 2.85 与 2.65 在用 |
| `import uuid` / `from datetime import datetime, timezone` | 保留 | Stage 1a 建 `table_id`（`:458`）/ refine 取参考月 |
| `__all__`（`:2748-2756`） | 删两项、加两项 | 分组注释改成 `# Stage 2 / 2.45 / 2.5 / 2.6 / 2.65 / 2.7 / 2.85` |
| refine 里的 `sheets` / `sheet_names_by_page` / `file_format` 读取（`:2684-2699`） | **删** | 只服务旧 2.6 |

新 helper 放在原 Stage 2.6 章节位置（`infer_missing_months_in_tables` 之后），各带章节横幅；需要从 `state` 多导入 `DataType`。

### 4.6 注释同步（只改文字，不改逻辑）

| 位置 | 改成 |
|---|---|
| 文件头 `:3`、`:7`、`:22` 的 Stage 清单 | 去掉 2.8；2.6 描述改"表类型 = 文件声明类型"；在 2.6 后加一行 `Stage 2.65 drop_current_and_future_actuals_in_tables (Actuals 文件剔除当前月及以后)` |
| `renumber_column_positions_by_month` docstring `:1116-1117` | 删"而 Stage 2.8 … 跑在本步骤之后"这半句，保留"列一旦并了就救不回来"的结论 |
| 2.7 `:1633-1637`（组内类型不一致整组跳过） | **代码保留**，注释改为：2.7 本身的不变量（实际数与预测数不互相补行）；自 sprint121 同一文件内类型统一为声明类型，正常路径不再触发 |
| 2.85 docstring `:2020` | "Stage 2.8 之后(拆表收尾…)" → "Stage 2.65 之后(Actuals 剔除完成、表集合最终化)" |
| 2.45 docstring `:2119-2120` | "Stage 2.8 … 之后" → "Stage 2.85 之后" |
| refine docstring `:2569-2586` 与 `:2715-2718` 注释 | Stage 清单同上；"state 读 … sheets(excel 供 Stage 2.6 …)" → "file_list[current_file_index].data_type"；"在 2.8 之后" → "在 2.65 之后" |

---

## 5. 下游输入的变化（回归要盯的点）

去重、补行、映射判定的**算法都不变**，但输入变了，回归时要对比结果（设计 §5.4 只列了前两条）：

1. **2.85 去重**：去重键含 `data_type`（`shared.py:1950-1962`）。过去同一文件里模型把月表判 ACTUALS、YTD 表判
   PROFORMA 时两表不互删；现在类型统一，**可能多标记一些重复 cell**——这是对的（前端合并桶键同样含 dataType）。
2. **2.85 去重**：Actuals 文件的当月及以后 cell 先被剔，各表"月份跨度"变小，**权威表的选择可能变**。
3. **2.7 补行**：过去因模型给的类型不一致被整组跳过（`:1638-1646`）的同名表组，现在会正常进入补行判断，
   **可能补出过去没有的占位行**。
4. **2.5 映射判定**：某行唯一的推断月份 cell 被剔后，该行**不再被整行降级**，`source_is_mapped` 可能由 false 变 true
   ——预期内（那个 cell 本来就不入库）。

不受影响（已核实 0 处读 `data_type`）：RAG override（Stage 1c）、训练信号（learn 队列）、task 级 semantic_group 归一化。

---

## 6. 模型侧的 data_type：本期保留不动

| 对象 | 决定 | 理由 |
|---|---|---|
| 提示词：`excel_extract_locate.v3.md` §6（`:361-395`）、`identify_statement.html.v2.md` / `.vision.v2.md` §5.6、`data_values.*.v3.md` 的 `data_type` 上下文标签 | **不改** | ① 结果被 2.6 覆盖，零功能影响；② 改坐标轨出参契约按提示词约定要升 v4，并连带改 `verify.py`、`pipeline.py` 与 `tests/ai/excel_extract_agent/test_prompts.py` 里钉住这些段落的 ≥4 条断言；③ 旧轨分类提示词改动要真文件回归；④ 代价只是每表几个输出 token |
| Stage 1b（pdf / image）收到的 `data_type` 上下文标签（`pdf_preprocess_node.py:615`、`:699`，`image_preprocess_node.py:294`） | **不改**，仍是模型自判的类型 | 提示词明写该标签"不改变 cell 抽取规则"（`data_values.html.v3.md:106`、`.vision.v3.md:102`），只在规则 7 兜底归类时作参考；改成声明类型要把 `file_list` 穿进三处参数组装，收益不抵改动面 |
| `excel_extract_agent/pipeline._data_type_of` | **保留逻辑**，只改 docstring 与 `:105-109` 注释 | 它把模型判定带进 `TableInfo`，2.6 才算得出 `llm_disagreed`；删掉还要改 `test_pipeline.py` |
| `excel_extract_agent/verify.py` ⑨b WARN | **保留检查**，改注释与文案 | 提示词仍要求这个字段，WARN 仍是"模型没守出参契约"的信号；但现有文案"会退回算术校正 … 落到默认值 ACTUALS"已不成立，会误导排查，必须改。只是日志，无测试断言该文案 |

以上清理（提示词去掉 data_type 段、删 `_data_type_of` 与 ⑨b）留到下次因别的原因改这几份提示词时一并做。

---

## 7. `parent_table_id`：停止写入

新任务恒为空（设计 §3.2）。删 2.8 后它已无生产者，顺手把写入链收掉，避免留一个没人产出的契约字段：

- 删 `RawRow.parent_table_id`（`state.py:98-101`）。
- 删 `save_extracted_tables` 的 `parent_table_id=cell.get("parent_table_id")` 与上方注释（`extract_financial.py:433-434`）
  ——ORM 列无默认值，不传即 NULL，结果相同。
- **保留**：ORM 列 `ExtractedData.parent_table_id` 与全部读路径（`lg/financial_extract_task/extract_data_service.py:231`、
  `financial_extract/application/service/task_manage_service.py:230`）——devSupport 回放历史任务要用（D9）。
- `models.py:286` 行尾注释改为"历史字段：sprint121 前 Stage 2.8 拆表时写入；新任务恒 NULL，保留供历史回放"。

---

## 8. V030 迁移与 ORM 注释

**文件**：`sql/migrations/business/V030__sprint121_ai_file_registry_business_type_extract_fi.sql`（业务库；`ai_file_registry`
在业务库）。内容只有一条 `COMMENT ON COLUMN`，在 V023 的取值清单后追加两个值，并说明它们只用于
`purpose='financial_extract'` 行、表示用户声明的类型、历史行为 NULL、且不参与 chatbot 检索范围与 Memory 面板。
全文见 [code-examples](./code-examples.md)。

**执行时机写进文件头**：人工 psql 执行，**任何时间都可以**——只改注释，对任何版本的 Java / Python 代码都无影响；
`COMMENT ON` 天然幂等，可重跑。

**ORM**（`models.py`，只改注释）：

- `AiFileRegistry` 类 docstring（`:131-133`）"财务抽取（Java 建行、Python 推进 status）"补：`business_type` 写用户声明的
  `EXTRACT_FI_ACTUALS / EXTRACT_FI_PROFORMA`，init_task 读取。
- `business_type` docstring（`:190-192`）按用途分两组：`purpose='rag'` 沿用 V023 的十个取值（现在的 docstring 只列了七个，
  漏了 `ADMIN_ORGANIZATION / ERL_ATTACHMENT / SESSION_UPLOAD`，借这次对齐）；`purpose='financial_extract'` 为两个
  `EXTRACT_FI_*`，历史行 NULL，取值映射在 `init_task_node._DATA_TYPE_BY_BUSINESS_TYPE`。与 Java 实体注释
  （[dev-java](./dev-java.md) §7）同口径。

---

## 9. CLAUDE.md 同步

| 文件 | 位置 | 改成 |
|---|---|---|
| `source/ai/CLAUDE.md` | `:47` init_task 行 | "任务初始化节点（校验 + 标记 PROCESSING + 读文件清单 + 读声明类型，未声明的文件直接 FILE_FAILED）" |
| `source/ai/CLAUDE.md` | `:49` shared.py 行 | "… / 2.5 source_is_mapped / 2.6 data_type / 2.7 …" → "… / 2.5 source_is_mapped / 2.6 表类型 = 文件声明类型 / 2.65 Actuals 剔除当前月及以后 / 2.7 …" |

`CIOaas-python/CLAUDE.md`、`source/lg/CLAUDE.md`、`source/financial_extract/CLAUDE.md`、`docs/prompt-usage-map.md`
均未提 Stage 2.6 / 2.8，不用改。其它功能的历史设计文档（如
[Excel 坐标轨开发设计](../../../智能解析-Excel坐标轨/开发设计/dev-design-doc.md) §5 的 Stage 表）记录的是当时实现，不回改。

---

## 10. 测试

按根 `CLAUDE.md`，开发完不自动跑；以下是改动范围与收到指令后的执行清单。

### 10.1 删除

| 文件 | 原因 |
|---|---|
| `tests/ai/nodes/test_split_proforma_tail.py` | 被测函数删除（13 个用例） |
| `tests/ai/nodes/test_finalize_data_type.py` | 被测函数与 `trust_llm` 接线删除。它的接线教训（"必须真跑 `refine_extraction_node`，从 `file_list[current_file_index]` 读"）由 §10.3 的节点用例接住 |

### 10.2 修改

| 文件 | 改什么 |
|---|---|
| `tests/ai/nodes/test_renumber_column_positions.py:425-449`（`test_refine_pipeline_renumbers_columns_before_aligning_rows`） | state 补 `file_list=[{…, "data_type": "PROFORMA"}]` 与 `current_file_index=0`——否则 refine 读声明类型时 `KeyError`。用 PROFORMA 是为了护栏不剔任何 cell，不干扰它要钉的顺序 |
| `tests/ai/excel_extract_agent/test_pipeline.py:109` | 只改行尾注释"下游 Stage 2.6 校正" → "下游 Stage 2.6 以文件声明覆盖"，断言不变 |

### 10.3 新增

`tests/ai/nodes/test_declared_data_type.py`（helper 直接注入 `reference_month`；节点级用例取远离当前的月份
`2000-01` / `2999-01`，再加一个由 `datetime.now(timezone.utc)` 算出的当月，避免冻结时钟）：

| 用例 | 断言 |
|---|---|
| `test_apply_declared_type_overrides_llm_label` | 参数化模型标签 `None / "" / ACTUALS / PROFORMA` × 声明两值 → 每张表 `data_type == 声明`；`raw_rows` 不变；入参未被改 |
| `test_actuals_drops_current_and_future_months` | ref `2026-10`：`2026-08/09` 留，`2026-10/11` 剔 |
| `test_actuals_keeps_cells_without_month` | `None` / `""` / `"Q3 2026"` 全留 |
| `test_actuals_drops_inferred_months_too` | `is_predict_month=True` 且月份 = ref → 剔 |
| `test_actuals_month_compare_crosses_year` | ref `2027-01`：`2026-12` 留，`2027-01` 剔 |
| `test_table_emptied_by_guard_is_removed` | 全被剔的表移除；原本就空的表保留 |
| `test_column_positions_not_renumbered` | 新月在左的版式（col 1 = 当月）剔后余下 cell 的 `column_position` 仍是 2、3… |
| `test_proforma_file_keeps_every_month` | 过去 / 当月 / 未来全留 |
| `test_refine_node_reads_declared_type_from_file_list` | 参数化 ACTUALS / PROFORMA，真跑 `refine_extraction_node`（只 patch `_apply_rag_override_safe`），模型标签给反 → 全表 = 声明；ACTUALS 只剩 `2000-01`，PROFORMA 三个月都在；表数不变（不再拆表）；没有 cell 带 `parent_table_id` |
| `test_inferred_total_column_at_current_month_is_dropped` | 真跑：col 1 = 上月、col 2 无月份（`lg_category` 给非 UNMAPPED）→ Stage 2 推成当月 → 被剔；该行余下 cell `source_is_mapped` 为 true（不再被推断列拖累） |
| `test_whole_file_dropped_yields_no_tables` | ACTUALS 且全部月份 ≥ 当月 → `tables == []`，无 `error_message`（即 save_to_db 判 REVIEW_READY） |
| `test_guard_runs_after_month_inference_and_before_downstream_stages` | 把 Stage 2 / 2.6 / 2.65 / 2.7 / 2.85 / 2.45 / 2.5 换成记录器，断言调用顺序；钉住 §4.1 的插入点（同 `test_renumber_column_positions.py:425` 的写法） |

`tests/ai/nodes/test_init_task_declared_type.py`（桩掉 `init_task_node.get_session` / `mark_task_processing` /
`update_file_status`；查询链桩见 [code-examples](./code-examples.md)）：

| 用例 | 断言 |
|---|---|
| `test_business_type_maps_to_declared_data_type` | 参数化两值 → `file_list[0]["data_type"]` 为 `ACTUALS` / `PROFORMA` |
| `test_undeclared_file_is_failed_and_left_out` | 参数化 `None / "" / "KNOWLEDGE_BASE" / "extract_fi_actuals" / "ACTUALS"` → `update_file_status` 以 `(file_id, "FILE_FAILED", 文案)` 调用一次；不在 `file_list` |
| `test_all_files_undeclared_gives_empty_file_list` | `file_list == []`，`task_status == PROCESSING`（之后 FAILED 由既有 `test_finalize_extract.py:300` 覆盖） |
| `test_mixed_batch_keeps_declared_files_in_order` | 已声明文件保持查询返回的顺序，未声明的逐个判失败 |

### 10.4 回归（函数不改，必须保持绿）

`tests/ai/nodes/` 全目录（重点 `test_dedupe_duplicate_month_cells.py`、`test_infer_missing_rows_flags.py`、
`test_rag_override*.py`、`test_parallel_files.py`、`test_finalize_extract.py`、`test_file_download_check.py`）、
`tests/ai/excel_extract_agent/`（提示词 / 校验 / 流水线未改）、`tests/lg/`（含 `parent_table_id` 历史读路径
`test_extract_data_service.py:177-192`）、`tests/financial_extract/`、`tests/consumer/test_handlers_recovery.py`。

```
uv run python -m pytest tests/ai/nodes tests/ai/excel_extract_agent tests/lg tests/financial_extract tests/consumer -q
```

真文件验收（审核通过后、只挑代表样本）：① 一份历史 + 当月 + 未来月混排的 Excel，分别声明 ACTUALS / PROFORMA
上传，核对剔除与保留；② 一份"单月表 + YTD 表"同文件的 PDF 声明 ACTUALS，与改造前对比 2.85 的标记结果；
③ 一个上线前建的任务重投，确认文件 FILE_FAILED 且前端显示文案。

---

## 11. 发布与兼容

| 顺序 | 内容 | 说明 |
|---|---|---|
| 任意时间 | V030 | 只改注释，人工 psql |
| 1 | Java + 前端同批 | 见 [dev-java](./dev-java.md) |
| 2 | Python | 先发 Python 会让新任务全部判失败（登记行还没有类型）；Java 先发时旧 Python 忽略这一列，平滑过渡（设计 §8） |

- **在途任务**：Python 发版时还在排队、且是 Java 发版前提交的任务，登记行为 NULL → 文件 FILE_FAILED（需求 R11）。
- **单独回滚 Python**：旧 Python 不读 `business_type`，回到按表推断；已写入的 `EXTRACT_FI_*` 不影响它。不需要清数据。
- **不加 env 开关**：回滚靠回退版本，不做新旧逻辑并存。

---

## 12. 风险与检查项

| # | 风险 | 处理 |
|---|---|---|
| R1 | 新迁移 `UPLOADED → FILE_FAILED`（跳过 PROCESSING） | 联调时确认 Java 轮询 / 前端文件行按终态展示，没有"失败前必经 PROCESSING"的假设 |
| R2 | 2.85 去重、2.7 补行、2.5 映射判定的输入变化（§5） | 真文件验收 ② 对比去重标记；日志 `dedupe_duplicate_month_cells` / `infer_missing_rows` 前后对照 |
| R3 | 列位 / 行位留洞 | 有先例（§4.3）；验收 ① 里用"新月在左"的版式确认映射页正常渲染 |
| R4 | 模型把历史月读成未来月（年份错读）时，Actuals 文件里该列被静默剔除 | 过去同样的错会让整表被改判 Proforma，现在影响面更小；按 `actuals_guard` 日志的 `dropped_months` 排查 |
| R5 | "当前月"口径：Python 用处理时刻 UTC；Java 护栏用 JVM 默认时区（[dev-java](./dev-java.md) J-R4）；用户本地时区在月末前后与 UTC 差一个月 | 需求 R4 已定以 UTC 为准；确认生产 JVM 跑在 UTC |
| R6 | 非 `YYYY-MM` 形态的月份被当成"无月份"保留 | 与 2.85 口径一致；提交时 Java Actuals 护栏兜底 |
| R7 | 上线前建的任务在映射页替换文件 → 继承 NULL → FILE_FAILED，用户不知原因（[dev-java](./dev-java.md) J-R2） | 文案明确写"未声明类型、请重新上传" |
| R8 | 旧日志行 `finalize_data_type` / `split_proforma_tail` 消失 | 改 grep `declared_data_type` / `actuals_guard`；init 的未声明告警 grep `init_task_node[declared_type]` |

---

## 13. 明确不做

- 不回退旧推断：类型缺失只判失败（D9）。
- 不改提示词、不升提示词版本号；不把声明类型传给 Stage 1b（§6）。
- 不给 init 加批量写库函数：每批文件数很少，逐个 `update_file_status` 足够。
- 不删 ORM 的 `parent_table_id` 列与读路径（§7）。
- 不动 2.7 的类型一致性判据，只改注释（§4.6）。
- 不清理坐标轨仍在产出、但 refine 已不再读取的 `sheets`（`ExcelPreprocessReturn` 契约，与本需求无关）。
- 不加 env 开关；不补写历史数据。
