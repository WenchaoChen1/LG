# Excel 坐标提取轨 · 开发设计文档

> 关联文档：
> - 上游（第四阶段 · 功能设计）：[design-doc](../设计/design-doc.md) —— D1 ~ D7 全部结论在此，本文不重复论证
> - 参考代码：[code-examples](./code-examples.md)
> - 旧轨设计：[python-design](../../智能解析/调研/python-design.md)
> - 已落地代码：`CIOaas-python/source/ai/agent/excel_extract_agent/`（提交 `bdafff51`、`bdd0bf7c`）

本文只写**怎么建**：文件划分、集成契约、逐字段产出者、旧 Stage 的处置、并发落地、
测试与落地顺序。**为什么这么设计**在上游设计文档，不在这里复述。

按 `docs/CLAUDE.md`，完整函数与 DDL 不写在本文，放 [code-examples](./code-examples.md)。
本轨**没有 DDL**——D5 定的是坐标不落库、表结构零改动。

---

## 1. 三条不可动摇的前提

实现期任何取舍都要先过这三条：

1. **落库同形**（D5）。新轨产出的行与旧轨在 `ai_financial_extraction_mapping_data` 里
   逐字段同形，无迁移、无回滚 DDL。这条把"新增字段"这个选项直接关掉了。
2. **旧轨节点代码一行不改**（D1）。新轨是独立子包；切换只动**接线**（§3.1），不动
   旧节点内部。
3. **坐标必须显式、可回读**（设计文档 §2.1）。坐标错一行 = 整表数值系统性错位而外观
   正常，这是本轨唯一想防的失败模式。任何"看起来更简洁"的改动若削弱回读能力，不做。

---

## 2. 包结构

```
source/ai/agent/excel_extract_agent/
├── __init__.py        改造  补包 docstring（说明本包提供的是节点实现、不自持 graph）
├── coords.py          不动  1-based 坐标原语 + MergeIndex
├── render.py          改造  §6：ind + 5 个样式属性 + with_styles 开关 + csv 支路
├── verify.py          改造  §7：逐表 + D7 三条验伪
├── pipeline.py        新增  单 sheet 的三步流水线（主编排，平铺调用下面五个）
├── llm_call.py        新增  三个 LLM 步共用的调用壳（call_kwargs / TraceContext / 闸门 / JSON 解析）
├── locate.py          新增  步 1+2  定位 + 回读校验 + FATAL 重问一次
├── semantics.py       新增  步 3+4  父链 + lg 指标（合并调用）+ 校验
├── currency.py        新增  步 6    货币与符号规则
├── values.py          新增  步 5+7  按坐标取值 / 应用规则 / 聚合行标记（纯程序，无 LLM）
├── tools.py           新增  约定占位（本包不绑 @tool，见 §2.1）
└── nodes/
    ├── __init__.py    新增
    └── extract_node.py 新增  LangGraph 节点：文件级入口、sheet 级并发、错误升级、组装返回
```

一个步骤一个文件（约 150 ~ 250 行），`pipeline.py` 的主函数按顺序**平铺**调用它们——
读主函数即懂全流程，不做 a→b→c 嵌套链（根 `CLAUDE.md`「编码原则」）。`llm_call.py`
是三个 LLM 步的共用壳，独立成文件而不是塞进某一步——三处 import 它比"藏在 locate.py
里被另外两个反向依赖"清楚。

⚠️ **步 8（取数后校验）本轮不落地**：设计文档 §7.3 自身标"待设计"（抽样比对 + 聚合行
自校验的口径还没定）。它不阻塞批次 1 ~ 3（没有任何东西依赖它），但**上线前必须补**
——本轨的第一性原则是"坐标可回读"，只有坐标级校验、缺数值级交叉校验，等于只做了上半场。
届时新增 `crosscheck.py`，并作为**批次 5** 排在切换之后（§12）。

### 2.1 只对 `build.py` 破例，`tools.py` 建占位

`source/ai/CLAUDE.md` §三 规定 `agent/` 下每个智能体子包都要有 `build.py` +
`nodes/` + `tools.py`。本包的处置**一破一守**：

**`tools.py` 建占位**（近空文件 + 一句 docstring）。照 `chatbot_kb_graph/tools.py`
与 `chatbot_combo_graph/tools.py` 的「约定占位」先例——那两个子包同样不直接绑工具
（工具绑在它们调用的子智能体节点里），但仍保留占位文件维持 §三 约定的整齐。本包同理：
零成本，且不新开"整体省略约定文件"的先例。

**`build.py` 不建**——这条是硬理由，不是嫌麻烦：

新轨**不是一张新图**，而是 `financial_extract_graph` 里 excel 那个 per-format 节点的
替换实现，**没有 graph 可 build**。造一个 `build.py` 里面什么都不 build，比不造更让人
误会。

而且它**刻意不能上 LangGraph 子图**：LangGraph 的超步 barrier 会跟 sheet 级 4 路并发
打架（同一原因让 `generate_title` 至今不挂图——见 `ai/CLAUDE.md`「LangGraph 图的特定
约束」②）。三步流水线是严格串行 + FATAL 重问一次，没有需要图来表达的分支。

**代价**：`build.py` 这一项偏离 §三 的字面规定，要在 `ai/CLAUDE.md` 里把本包条目从
现在的"⚠️ 尚无 `build.py`/`nodes`/`tools.py`——成图时按本文件 §三 补齐"改成事实描述，
并在 §五 按该文件既有格式（"⚠️ **标题**：说明 + 理由"）追加一条例外（§13）。**例外
范围仅限 `build.py`**。

---

### 2.2 新包对旧轨的依赖清单

三类，**别混**。判据是同一条：D1 会让旧轨整体下线，任何"住在旧轨包里的、非契约性的"
符号都不能 import。

**① 可以直接 import——住在共享位置，与旧轨同生共死无关**

| 符号 | 出处 |
|------|------|
| `VALID_LG_CATEGORIES` | `lg.db.enums`（共享 db 枚举，实测恰 16 个值） |
| `llm_units_gate` | `common.llm_concurrency` |
| `TraceContext` / `llm_db_router` | `llm` |
| `CallerAgent` / `CallerNode` | `common.enums` |
| `parse_json_response` | `llm.infrastructure.response_parser` |
| `AI_CLASSIFICATION_MAX_TOKENS` 等常量 | `llm.infrastructure.constants` |

**② 契约性 import——必须用旧轨那一份，不能自己定义**

`MainGraphState` / `ExcelPreprocessReturn` / `TableInfo` / `RawRow` / `ExcelSheetInfo`
（`financial_extract_graph` 的 `state.py` / `node_return.py`）。它们**就是**§3 那份集成
契约本身；自己复制一份等于让契约有两个事实源，第一次上游改字段就会静默漂移。

**③ 必须复制到本包——旧轨私有，或住在旧节点文件里**

| 符号 | 出处 | 复制而非 import 的理由 |
|------|------|----------------------|
| `_color_id` / `_size_id` / `_INVISIBLE_BG` | `excel_preprocess_node.py:286-347` | 私有函数，住在 2800 行的旧节点里 |
| `ocr_extract_model` / `ocr_extract_reasoning_kwargs` / `_reasoning_effort_kwargs` 的白名单校验 | `financial_extract_graph/nodes/shared.py` | 虽无下划线前缀，但住在**另一个 agent 子包的节点文件**里，跨包 import 违反 `ai/CLAUDE.md` §三 的隔离约定。复制时**沿用同名 env**（`OCR_EXTRACT_MODEL` / `OCR_EXTRACT_REASONING`），部署侧零变更 |
| `_CSV_ENCODINGS` | `s3util/validation/__init__.py:90` | 模块私有、不在 `__all__` |

> 提升到公共位置（`ai/nodes/` 或 `common/`）本来更干净，但那要改旧轨的 import 行
> ——违反前提 2「旧轨节点代码一行不改」。所以选复制。

**④ 绝不依赖**

`_load_sheet_dataframes`（返回元组近一年改过多次元数）、
`_detect_table_boundary_candidates` / `_resolve_boundaries_from_anchors` / 报表标题
关键词表（D7 已定不复用，实测召回 63%）。

---

## 3. 集成契约（新节点必须遵守）

这一节是"能不能原地替换"的全部条件。**下游节点一行不改**是硬要求。

### 3.1 接线点：两处，必须同步改

| 位置 | 现状 | 动作 |
|------|------|------|
| `build.py:52` | `import excel_preprocess_node` | 换成新节点 |
| `build.py:170` | `graph.add_node("excel_preprocess", ...)` | 换实现，**节点名字符串不能改** |
| `parallel_files_node.py:74` | 同上 import | 换成新节点 |
| `parallel_files_node.py:261` | `_preprocess_for` 里 `("excel_preprocess", excel_preprocess_node)` | 换实现，**名字面量必须与图节点名逐字一致** |

⚠️ **节点名 `"excel_preprocess"` 是承重的**：`build.py:234` 的边
`add_edge("excel_preprocess", "refine_extraction")` 靠它接线，`parallel_files_node` 的
span 名也必须逐字相同。改名等于同时改图拓扑与 trace 聚合口径，不在本轨范围内。

⚠️ `build._route_after_download`（`build.py:127-145`）把 **`excel` 和 `csv` 都路由到
这个节点**。所以 D1 要求的 `.csv` 支持**不需要新增路由**，只需新节点自己能吃 csv（§6.4）。
`_preprocess_for` 与 `_route_after_download` 是同一份判据在两处各写一遍（靠注释互指、
避免循环 import），改的时候两边都要过一遍。

### 3.2 `ExcelPreprocessReturn` 的填写矩阵

三条 return 路径，每条填哪些字段是定死的：

| 字段 | 技术失败 | 业务软失败（no_tables） | 正常完成 |
|------|:--------:|:----------------------:|:--------:|
| `error_message` | **填** | 绝不填 | 绝不填 |
| `sheets` | 不填 | 填 | 填 |
| `tables` | 不填 | 填（空 list） | 填 |
| `n_extract_units` / `n_extract_failures` | 不填 | 不填 | **填真实统计** |
| `skipped_table_ids` | 不填 | 不填 | 填（新轨无列切片，恒空 list） |
| `truncated_table_ids` | 不填 | 不填 | 填 |

**统计字段必须诚实填**。`refine_extraction_node`（`shared.py:2547-2616`）的错误升级
短路链完全依赖它们：

```
① 上游已有 error_message            → 透传
② tables 空 / 无 is_financial=True  → 透传，无 error（no_tables）
③ n_extract_units > 0 且 == n_extract_failures → "Data extraction failed"
④ skipped_table_ids 非空且 len == len(tables) → budget hint
```

新轨不做列切片，但仍要老实写 `n_extract_units` / `n_extract_failures`，否则③判据失真。
`skipped_table_ids` 恒空 list（不是不填）。

### 3.3 错误文案禁改字面

`shared.py:2553` 有一句「错误文案禁改字面——前端可能展示」。四条既有文案：

| 触发点 | 文案 |
|---|---|
| Stage 0 读取异常 | `f"sheet read failed: {type(exc).__name__}: {exc}"` |
| 分类全失败 | `"Statement identification failed"` |
| 抽取全失败（由 refine 判，不是节点自己） | `"Data extraction failed"` |
| 全表超 cell budget | `_EXCEL_EXTRACTION_BUDGET_HINT_TEMPLATE` |

新轨复用前两条时**逐字保留**。新轨自己的技术失败（例如三步流水线的 FATAL 重问后仍失败）
可以新增文案，但不能改动这四条。

### 3.4 软失败 / 硬失败严格二分

- `error_message` 非空 = **技术失败** → `save_to_db_node.py:30-31` 判 `FILE_FAILED`
- `tables=[]` 且 `error_message` 为 None = **业务软失败** → `REVIEW_READY`，不入库

`is_financial=False` 的表**不进 `tables` 列表**（旧轨 `shared.py:455-462` 判 false 直接
`continue`），所以 `tables=[]` 就是 no_tables 的实际形态。**把 no_tables 也写一个
`error_message` 会误判 FILE_FAILED**，这是最容易犯的错。

### 3.5 不许写的 state 字段

`local_path` / `is_corrupted` / `image_paths` / `page_count` 属 `download_check_node`；
任务级字段与 `file_id` / `file_name` / `file_status` 投影字段也不许写。新节点只能写
`ExcelPreprocessReturn` 里那七个。

### 3.6 `sheets` 里的 `sheet_html` 放什么

`ExcelSheetInfo`（`state.py:139-146`）是 `TypedDict`（非 `total=False`），5 个字段全必填：
`sheet_index`（0-based）/ `sheet_name` / `sheet_html` / `row_count` / `column_count`。

但**下游只读 `sheet_index` 与 `sheet_name`**（`shared.py:2643-2648` 构造
`sheet_names_by_page`，供 Stage 2.6 按 `sheet_index + 1 == table.page_number` 映射）。
`sheet_html` 只有旧轨自己的 Stage 1a/1b 消费。

**`sheet_html` 放坐标视图本身**——它确实是本轨发给模型的那份 HTML，语义诚实，且日后
排查时能看到模型当时看到的东西。体量 0.4 ~ 36 KB / sheet，与旧轨同量级；且只在内存里
（checkpointer 已于 `1e92edeb` 移除），不落库。

---

## 4. `RawRow` 逐字段的产出者

**这是本文最要紧的一张表。** 上游设计文档的 7 步流程没有覆盖全部落库字段，下面把
Stage 1b 该产出的 12 个字段逐一指派产出者。缺一个就是 `save_extracted_tables`
（`lg/db/service/extract_financial.py:405-440`）里 KeyError 或静默丢信号。

| 字段 | 新轨产出者 | 说明 |
|------|-----------|------|
| `row_position` | **程序** | `label_range` 内的行序，1-based。⚠️ 它与 `source_row_id` 的分配键相关（§4.1） |
| `column_position` | **程序** | `date_columns` 的序号，1-based |
| `account_label` | **程序** | 条目列 cell 文本（strip 后） |
| `account_label_join` | **LLM 步 3** | D3：模型给完整链，程序不派生 |
| `column_month` | **程序** | **确定性解析** `date_columns[].text`，不是推断（§5 Stage 2） |
| `value` | **程序** | openpyxl 按坐标取，应用步 6 的符号规则后 |
| `unit_type` | **程序** | `"CURRENCY"` / `"PERCENT"`——看 `number_format` 含不含 `%`。旧轨这个字段问 LLM 要（`shared.py:577`），新轨不用问 |
| `currency_type` | **LLM 步 6 给规则 + 程序应用** | 行/列级规则优先、单元格兜底 |
| `lg_category` | **LLM 步 3** | 必在 16 值白名单内（§7.2） |
| `semantic_group` | **恒 `""`** | 旧轨 excel 路径本来就不产它（`shared.py:740-741` 的 "Plan A：Step 2 不产 semantic_group，post_process 缺省补 `''`"），归一在 task 级 `finalize_extract_node` 一次性跑。**不进任何提示词** |
| `is_payroll_defaulted` | **LLM 步 3 附带** | Payroll 父级不明 → 默认 G&A Payroll。短键 `pf` |
| `is_cogs_rd_conflict_defaulted` | **LLM 步 3 附带** | cloud / hosting / AWS 等词在 COGS↔R&D 冲突 → 默认 COGS。短键 `cf` |

**绝不能自己填**（下游 Stage 的职责，填了会破坏它们的语义）：
`is_predict_month`（Stage 2）/ `source_is_mapped`（Stage 2.5）/ `parent_table_id`
（Stage 2.8）/ `is_zero_default`（Stage 2.45）/ `is_duplicate_removed`（Stage 2.85）。

### 4.1 步 3 的输出契约要比设计文档多两个键

设计文档 §5.2 写的是 `rows: [{r, parent, lg}]`。**实际要加 `pf` / `cf`**：

```
rows: [{r, parent, lg, pf?, cf?}]
```

这两个是**模型对自己 `lg` 判断的出处标注**——"这条是我有把握的，还是父级不明只好兜底的"。
漏了它们不报错，但会让**训练信号链断掉**：RAG override 命中改写时要同时清零这两个标记
（`shared.py:2466-2479`），拿不到就无法区分"模型确信"与"模型兜底"。

> 上游设计文档 §5.2 需补这两个键——见 §13 待同步清单。

### 4.2 `TableInfo` 表级字段

| 字段 | 来源 |
|------|------|
| `table_id` | 程序生成 UUID4 字符串 |
| `table_name` | LLM 步 1 的 `tables[].name` |
| `page_number` | **程序** = `sheet_index + 1`（excel 语义，Stage 2.6 靠它映射 sheet 名） |
| `is_financial` | 恒 `True`——**只把判定为财务表的塞进 list**，`False` 的不放进去 |
| `data_type` | 可为 `None`，下游 Stage 2.6 会校正 |
| `raw_rows` | 上面那张表 |
| `row_range` / `anchor_text` | **程序**，可选。`row_range` 按设计文档 §5.1 的公式派生（`min(header_row, label_range 起行) .. label_range 止行`）后填入，**不是**又向模型索取——D7 刻意把它从 LLM 输出里删掉了。仅供多表场景排查用 |
| `extra_pages` | **不填**。PDF 跨页表专用（`state.py:134`），Excel 轨用不到 |

⚠️ `source_row_id` 的分配键是 `(table_id, row_position, account_label_join)`
（`extract_financial.py:398-410`），同键复用同号。**所以 `row_position` 与
`account_label_join` 必须稳定**——同一行在两次运行里得到不同的 `account_label_join`
会分配到不同 `source_row_id`。这是 D3「父链由模型给」带来的一个新的稳定性要求：
提示词要求逐字抄写、temperature 0，且步 4 校验要挡住空链。

---

## 5. `refine_extraction` 各 Stage 的处置

结论先行：**不删、不改旧轨任何 Stage**（前提 2）。新轨的数据流过它们时，为弥补旧轨
分批抽取而生的那几个 Stage 会**空转**。实现期要做的是**验证空转确实是 no-op**，而不是
动刀。

| Stage | 是什么 | 新轨处置 | 依据 |
|-------|--------|---------|------|
| **1b.5** 父链修复 `shared.py:2239` | 修 LLM 写残的 `account_label_join` 前缀（三行窗口锚定） | ⚠️ **唯一需实测确认** | 见 §5.1 |
| **1c** RAG override `shared.py:2370-2519` | 用 `ai_training_data` 近邻覆盖 `lg_category` | **原样复用** | 它纠正的是**分类判断**，与坐标/数值来源正交。只认 cell dict 的 `account_label_join` + `lg_category` 两个字段 |
| **1d** 列位/行位对齐 `shared.py:1094-1319` | 修多批 LLM 拼表的列/行冲突 | **空转**（预期 no-op） | 根因是"一张逻辑表由多批调用按页拼成"（`shared.py:1099-1105`）。新轨一个 sheet 一次定位调用，`column_position` 出厂即按月份 1..N |
| **2** 链式推月份 `shared.py:1343-1423` | 按左右锚点外推缺失 `column_month` | **空转**（预期 no-op） | 它存在的唯一理由是"LLM 逐 cell 抽取可能漏标某列月份"。新轨逐列穷举 + `verify` 强制原文一致，不存在缺列。`is_predict_month` 因此恒 `False` |
| **2.45** 系统填零 `shared.py:2070` | `value=None` → `0.0` + 标记 | **原样复用** | 业务规则（源表空白/横线该不该算 0），与数值谁读出来无关。程序读真空白格同样得 `None` |
| **2.5** `source_is_mapped` 重算 `shared.py:2106-2157` | 按 `lg_category` + 月份可信度算映射状态 | **原样复用** | 见 §5.3——它会自动退化成简化语义，不需要改造 |
| **2.6** `data_type` 校正 `shared.py:1429-1501` | 用月份 vs 参考日期纠正 LLM 的先验偏差 | **原样复用** | 纯算术规则。新轨的 `column_month` 更可靠，规则更简单地成立 |
| **2.7** 跨表账户对齐补缺 `shared.py:1531-1729` | 同名多个 logical table 间补齐缺账户行 | ⚠️ **需实测确认**（原判"空转"已被数据推翻） | 见 §5.2 |
| **2.8** 拆 PROFORMA 尾列 `shared.py:1742` | 当月列从 ACTUALS 拆出 | **原样复用** | 纯规则（当月 vs 历史） |
| **2.85** 跨表同月去重 `shared.py:1945` | 同 file 内"月度表 / YTD 表"重复 cell 软删 | **原样复用** | 源文档天然重复，新轨数值再精确也照样发生 |

**要实测的有两个**：Stage 1b.5（§5.1）与 Stage 2.7（§5.2）。其余七个的分类可以从触发
条件直接推出，不需要跑数据。

### 5.1 Stage 1b.5 要实测

它修的是"LLM 把父链字符串写残"，用三行窗口锚定 + 尾段对齐。新轨的 LLM 给的是**全量
完整链**（D3），理论上没有残缺可修——但它有可能对**正确的**链做出"修复"，那就是净损害。

**验证方法**（不靠推理，靠实测）：拿新轨产出的 `tables` 跑一遍 Stage 1b.5，逐 cell 比对
前后 `account_label_join` 是否有变化。有变化即需要旁路。

**旁路怎么做而不改旧轨**：`refine_extraction_node` 是按顺序调用的，旁路只能在新节点侧
做——把新轨的父链**在节点内先自检一遍**（步 4 已经在校验行号与 lg 白名单，加一条"链非空
且不以分隔符起止"），确保交给下游的链是良构的。若实测证明 1b.5 仍会改动良构链，再评估
是否需要在 `refine_extraction_node` 加一个"上游已给全量链"的判据——那属于改旧轨，要
单独拍板，不在本轨范围。

### 5.2 Stage 2.7 也要实测——原来的"空转"判断是错的

本文初稿断言 Stage 2.7 对新轨空转，理由是"新轨一张表一个 TableInfo"。**这个理由只排除了
"一个 sheet 内多表"，没排除"多个 sheet 各出一张同名表"**，而后者在真实数据里很常见。

`lg_uat` 实测——同一 file 内**同 `table_name` 但不同 `table_id`** 的组合有 **35 个**：

| 表名 | 同名 table_id 数 | 文件数 |
|------|:---------------:|:------:|
| `Caravel BALANCE SHEET As of October 21, 2020` | 4 | 8 |
| `Auxilia, Inc Profit & Loss January through December …` | 3 | 4 |
| `Profit & Loss` | 2 ~ 3 | 12 |

Stage 2.7 的分组键就是 `table_name`（**不含 sheet 归属**），触发条件是"同 file + 同
`table_name` + ≥2 张表 + 月份连续 + `data_type` 一致"。新轨若在一个 workbook 的多个
sheet 上读出同一个报表标题，**这一步会真实触发**。

**它触发未必有害**——跨表补齐账户本来就是同一个业务意图（让前端按账户合并时视觉对齐），
新轨的多 sheet 同名表和旧轨的多批同名表在这一点上诉求相同。所以处置不是"想办法绕过"，
而是**实测确认它的行为符合预期**：拿一个多 sheet 同名表的真实文件跑新轨，检查补出来的
占位行数量与位置是否合理，以及 `row_position` 让位 +1 会不会与 `source_row_id` 的分配键
（§4.2）打架。

### 5.3 Stage 2.5 为什么不用改造

它的判据是：`lg_category != UNMAPPED` 且 `account_label` 非空 且**该行所有 cell 的
`column_month` 都是源表直读**（非 `None` 且非 `is_predict_month`）。

新轨 `is_predict_month` 恒 `False`、`column_month` 由 `date_columns` 原文确定性解析，
所以第三个条件恒真——**现有代码原样跑出来的就是简化语义**
（`lg_category != UNMAPPED and account_label 非空`）。不是"需要砍掉那一支"，是那一支
永不触发。零改动。

> **审核期澄清（数据判定）**：曾担心"TOTAL / 合计列这类没有月份的列"会被 Stage 2 的
> 锚点外推静默塞进一个编造的月份。实测否决了这个担心——`lg_uat` 上
> `source_column_month IS NULL` 是 **0/59644 = 0.00%**，**旧轨从不产出无月份的 cell**。
> 合计列在 `date_columns` 阶段就被排除（设计文档 §5.1：只列真期间列，排除
> `%` / 差异 / 占比 / 合计），因此根本不会产生 `column_month=None` 的 cell，Stage 2
> 碰不到它。新轨沿用同一口径即可，无需额外机制。
>
> 顺带量到 `is_predict_month` 在旧轨占 **678/59644 = 1.14%**——Stage 2 确实在旧轨上
> 起作用，新轨会把它归零。

---

## 6. `render.py` 改造

### 6.1 `SheetView` 加两个字段

```
indents: dict[tuple[int, int], int]        有效缩进字符数
styles:  dict[tuple[int, int], StyleFp]    (bg, b, i, sz) 四元组
```

`StyleFp` 给个确切类型别名，不写裸 `tuple`（`coding.md` §12；`coords.py` 的
`MergeIndex` 与旧轨的 `_GridCell` 都是这个规矩）。

### 6.2 `ind` 必须在 `strip()` 之前算

`render.py:137` 的 `s = s.strip()` **保留不动**——视图文本要干净。前导空格数在
`load_sheet_views` 读原始值时就算掉、存进 `indents`。这正是 D3「显式属性而非保留空白」
的落地方式：空白会在 HTML 语义折叠、`verify._norm` 折叠、模型回抄时被多处归一，
`ind="8"` 免疫。

`ind` 的口径（设计文档 §6.3）：

```
ind = 前导空白字符数 + alignment.indent × 3
```

两种机制实践上互斥（用空格的文件 `alignment.indent` 恒 0，反之亦然），所以相加安全。
从 `data_only=True` 那一遍读（要的是用户看到的那个值）。

### 6.3 样式三个 helper：复制，不 import

旧轨的 `_color_id` / `_size_id` / `_INVISIBLE_BG`（`excel_preprocess_node.py:286-347`）
口径直接沿用，但**复制到本包**。理由与设计文档 §14 对 `_load_sheet_dataframes` 的判断
相同：它们是私有函数、住在 2800 行的旧节点里，而 D1 是直接替换、旧轨迟早删。复制时
留注释指明出处。

三个坑必须一起搬过来，否则等于没搬：

| helper | 坑 |
|--------|-----|
| `_color_id` | **不能直接读 `.rgb`**——openpyxl 对主题色/索引色的 `.rgb` 返回描述符对象不是 str，只做 `isinstance(str)` 守卫会把它们全吞成 `None`，与"没填充"分不开。而 **Excel 界面默认给的填充色就是主题色**。编码：RGB → `F5F5F5`（剥 ARGB 的 alpha）、主题色 → `t1+0.20`、索引色 → `i5` |
| `_size_id` | 先 `round(..., 1)` 再判整。反过来会让 `12` 与 `12.0` 成为同一字号的两种编码——与排除字体颜色的理由同类的伪差异。半磅 `10.5` 保留（财报里真实存在） |
| `_INVISIBLE_BG` | `{"FFFFFF", "t0", "i64", "i65"}` 归一成 `None`。不然"白底"会被当成信号 |

**不移植 `_normalize_fingerprint`**：它服务的是旧轨"只发有差异的属性"的差分发送机制
（省内存 + 消除幻影差异）。D3 定的是**发全量**，没有被省略的行，那个幻影差异不存在。

### 6.4 `render_view` 加 `with_styles`

```
render_view(view, *, row_range=None, col_range=None, max_rows=None, with_styles=False)
```

设计文档 §6.1 要求分步视图：定位步**不带**样式（纯噪声），父链步才带。默认 `False`
——让"忘记传参"退化到更省的那一侧。

`_td` 的属性从 7 个（`c` / `rs` / `cs` / `f` / `cache` / `err` / `ctx`）加到 12 个，
新增 `ind` / `bg` / `b` / `i` / `sz` 五个，仅在 `with_styles=True` 时发。

### 6.5 `.csv` 支路

D1 要求新轨补 `.csv`（旧轨吃、新轨原本不吃，不补就是能力回退）。

`load_sheet_views` 增加 csv 分支，产出一个 `SheetView`：`merges` / `formula_cells` /
`formula_empty` / `error_cells` 全空，`styles` 全默认，`indents` 仍然算（csv 文本里的
前导空格是真实存在的）。`name` 用文件 stem（对齐旧轨 `_load_sheet_dataframes` 的
`local_path.stem or "Sheet1"`）。

⚠️ **编码梯子别继承旧轨的 bug**：`s3util.validation.validate_csv` 依次试
**utf-8-sig / utf-8 / gb18030**（`s3util/validation/__init__.py:90`），但旧轨真正读的
时候是 `pd.read_csv(path, header=None)`（`excel_preprocess_node.py:753`）——**没传
encoding**，pandas 默认 utf-8。所以一个 gb18030 的 CSV 能过上传校验、然后在提取时炸。

新轨用同一把梯子读。那个常量是模块私有（`_` 前缀、不在 `__all__` 里），按 §6.3 的同一
理由**在本包自定义一份**，不 import 私有名。

---

## 7. `verify.py` 改造

### 7.1 逐表

契约从扁平变成 per-table（设计文档 §5.1），`verify_locate` 现在从 answer **顶层**取
`label_range`（`verify.py:112`）/ `header_row`（`:123`）/ `date_columns`（`:173`）/
`label_anchors`（`:251`）。

**签名保持 `verify_locate(view, answer) -> VerifyResult` 不变**，内部循环
`answer["tables"]`：一个 sheet 仍然只出**一个** `VerifyResult`。理由是 `evidence()`
要一次把整个 sheet 的 FATAL 交给重问（§8.2），分成多个结果反而要在调用方再拼回去。

9 组自由校验逻辑不变，逐表各跑一遍。

**`Issue` 要加一个 `table_index: int | None` 字段**，而不是只把表序号塞进 `detail` 文本。
两个用途都需要结构化的表序号：`evidence()` 要让模型分清是哪张表的问题；§8.2 的
`drop_fatal_tables` 要**按表剔除**——从 `detail` 字符串里正则解析表序号是脆的，一改文案
就断。单表 sheet 时该字段为 `0`（`tables` 恒有一个元素），非 per-table 的检查填 `None`。

### 7.2 三条 D7 验伪 + 三条步 4 检查

`_verify_tables`（`verify.py:269`）现在解析 `row_range`——**D7 去掉了该字段**（行跨度
由 `min(header_row, label_range 起行) .. label_range 止行` 派生），这个函数要重写成
设计文档 §7.2 的三条：

| # | 检查 | 级别 |
|---|------|------|
| 1 | 每张表都有自己的 `header_row`，且落在本表行段内 | FATAL |
| 2 | 相邻两表边界处有分隔证据（空行断档，或边界行在条目列是标题性文本） | WARN |
| 3 | 条目列里每个有文本的行都落在某张表的 `label_range` 内；连续 ≥5 行未覆盖 | FATAL（不足 5 行 WARN） |

这三条里有**两个算法整个仓库都没有先例**，骨架见
[code-examples §7](./code-examples.md)：

1. **表跨度派生** —— `min(header_row, label_range 起行) .. label_range 止行`。边界情况：
   多张表的 `header_row` 互相交叉时，派生出的 span 会重叠 → 直接判 FATAL（这本身就是
   "边界切错"的证据，不需要额外规则）。
2. **覆盖率断档游程** —— 在条目列所有非空行里，找**不落在任何表 `label_range` 并集内**
   的连续段，按段长判 FATAL / WARN。

⚠️ 检查 2（相邻两表的分隔证据）隐含要求**先按派生 span 排序**——`tables[]` 的顺序来自
模型输出，没有任何东西保证它按行序排列。排序这一步要显式做。

外加步 4（父链+lg）的三条（设计文档 §7.1），全部零额外输出：

1. `lg` 在 **16 值白名单**内——复用旧轨的 `VALID_LG_CATEGORIES`。脏类别会绕过白名单
   直达 DB、炸整批 INSERT，这坑旧轨踩过
2. 每个 `r` 落在本表 `label_range` 内
3. 每个条目行都要有 `lg`——漏行会以 `UNMAPPED` 落库，是静默降级

再加 §5.1 提到的父链自检：链非空、不以分隔符起止。

---

## 8. LLM 调用

### 8.1 标准写法

完整骨架见 [code-examples](./code-examples.md) §1。要点：

| 项 | 取值 | 来源 / 理由 |
|---|------|------------|
| 调用函数 | **`llm_db_router.complete`**（同步） | 节点是同步函数 + ThreadPool 并发，与旧轨三个 mega-node 一致。**不是 `acomplete`** |
| `provider` | `"openrouter"` | 同旧轨 |
| `model` | `ocr_extract_model()` | env `OCR_EXTRACT_MODEL`，兜底 `ocr_identify_model()`；未配置返回 `None` 让 kernel 落 provider 默认 |
| `max_tokens` | 定位/父链步用 `AI_CLASSIFICATION_MAX_TOKENS`(10240)；不用抽取档 | 新轨输出量级是 O(rows+cols)，实测定位步 143 ~ 1291 tok。抽取档 98496 是为旧轨逐 cell 输出准备的 |
| `timeout` / `max_retries` | `AI_REQUEST_TIMEOUT_SECONDS`(120) / `AI_REQUEST_MAX_RETRIES`(3) | 同上，不用抽取档的 300/1 |
| `json_mode` | `True` | 三步输出都是 JSON |
| `cache_system` | **`False`（即不传）** | D4：缓存全部先不开，保并行优先墙钟。⚠️ **旧轨这里是 `True`，别顺手抄过来** |
| `call_purpose` | 自由字符串，按步区分 | 非枚举 |
| reasoning | `ocr_extract_reasoning_kwargs()` 用 `**` 展开 | env `OCR_EXTRACT_REASONING`，未配置=不发 |

**JSON 解析必须走 `parse_json_response`**（`llm/infrastructure/response_parser.py:27-79`）
——它剥围栏、抽 `{...}` 主体、`json.loads`，失败后 L2 兜底 `json_repair`。
**禁止业务侧自己 `json.loads`**。

### 8.2 FATAL 重问一次怎么实现

放在**各步自己的文件里**（`locate.py` / `semantics.py`），不放 `pipeline.py`——重问用的
提示词与解析都是那一步的事，主编排只该看到"这一步成了还是没成"。

流程：调用 → `parse_json_response` → `verify_*` → 有 FATAL 则把 `res.evidence()`
（只含 FATAL，不含 WARN 噪声）追加成一条 user 消息重发**一次**。

**重问仍失败时按表丢弃，不整个 sheet 报废。** FATAL 本来就是逐表判出来的
（§7.1：`Issue.detail` 带表序号），所以知道是哪张表坏：

- 丢掉带 FATAL 的那张表，**保留通过校验的表**
- 只有**全部**表都 FATAL 才抛 `SheetExtractFailed`（§10.4）

多表 sheet 占比不低（设计文档 §10：27% 上界），"一张坏表拖累同 sheet 的好表整体不入库"
是不必要的代价——坏表的数据本来就该丢，好表的没有理由跟着丢。

⚠️ 重问是**整个 sheet 重发**（一份提示词、一次调用），不是按表重问：按表重问要单独的
提示词变体，而多表本身就是少数场景，不值得为它开一条提示词分支。"整 sheet 重问 + 按表
丢弃"是这两件事的正确组合。

### 8.3 截断

`finish_reason == "length"` 要判。旧轨的 `_salvage_truncated_unit` **对本轨无用**——它
只能拆 ≥2 张图的 vision 消息，HTML/文本轨返回 `None`（这也是旧轨 HTML 轨"截断会静默
丢行"的根因）。

新轨输出量级低一个数量级，截断风险小得多，但仍要显式处理：判到 `length` 即视为该 sheet
本步失败（走重问，重问时可缩小视图范围），**不做 `json_repair` 抢救前缀**——半个
`tables[]` 比没有更危险（坐标不全但外观合法）。

### 8.4 新增三个 `CallerNode` 枚举值

按 `ai/CLAUDE.md`「新增 agent / node 标识」，加到 `common/enums/caller_node.py` 的
financial_extract 分组，带中文注释。三个 LLM 步各一个，让 `ai_llm_call_log` 能按步聚合：

```
EXCEL_EXTRACT_LOCATE      步 1 坐标定位
EXCEL_EXTRACT_SEMANTICS   步 3 父链 + lg 指标
EXCEL_EXTRACT_CURRENCY    步 6 货币与符号规则
```

`agent` 沿用 `CallerAgent.FINANCIAL_EXTRACT`，**不新增**——新轨仍属这个 agent。
建议直接用枚举而非旧轨那样的字面量 `"financial_extract"`。

---

## 9. 提示词组织

### 9.1 三个 `.md`，运行时拼接

D4：按步拆文件、运行时拼成一个 system。三个文件：

```
source/ai/prompts/extract/
├── excel_extract_common.v1.md        坐标口径 + 合并 + 三个标记 + 转义/日期约定
├── excel_extract_locate.v2.md        步 1 定位（含 per-table 输出 schema）
├── excel_extract_semantics.v1.md     步 3 父链 + lg 指标
└── excel_extract_currency.v1.md      步 6 货币与符号规则
```

父链与 lg 虽合并成**一次调用**（D2），但**文件层面仍分开维护**（用户明确要求"不跟系统
提示词糅合成一个很长的提示词"），运行时拼接。合并后 system 约 14K 字符——旧轨那份的 37%。

### 9.2 `locate.v1` → `v2`：命中约定的触发条件

现有 `excel_extract_locate.v1.md` 的输出 schema（`:120-124`）是扁平单表形状。D7 把
`label_range` / `header_row` / `date_columns` / `label_anchors` 全移进 `tables[]`——
**出参契约变了**，按「提示词原地改，只有出参契约变了才升版号」这条约定，升 `v2`。

同步要改的还有该文件的**自检清单**（`:87-99`）与 `label_anchors` 那一节（`:75-85`），
它们现在都是单表口径。

### 9.3 `_md_loader` 的三个语义要记住

| 项 | 语义 |
|---|------|
| SYSTEM / USER 切分 | 按正则 `## \d+\. User Prompt` 标题切；标题**之前**（剥 frontmatter 后）整段是 SYSTEM，标题**之后第一个**围栏的 body 是 USER 模板 |
| `{{var:name}}` | **`str.replace` 逐个替换**，不是 `str.format`——所以不识别单花括号 `{name}`（避免 JSON schema 示例里字面 `{}` 触发 KeyError）。多传的 kwarg 忽略，少传的占位符原样保留、**不抛异常** |
| `load_fragment(path, heading)` | 按 H3 标题**包含**匹配取该节第一个围栏，用于条件性片段 |

「少传不抛异常」这条要当心：占位符打错字不会报错，会把 `{{var:sheet_view}}` 原样发给
模型。测试要覆盖"渲染后的 user prompt 里不含 `{{var:`"。

### 9.4 `.py` 常量模块

`excel_extract_agent_prompts.py` 改成加载四个 `.md`、导出各步的 SYSTEM / USER 常量，
并提供拼接好的组合常量。`.py` 里**不含提示词正文**（`coding.md` §15）。

---

## 10. 并发落地

三层模型见设计文档 §4.3。实现要点：

### 10.1 不用 `parallel_llm_invoke_units`

那个模板是"一批 unit 各发一次调用"（Stage 1a/1b 的形状）。本轨的形状不同：**每个
sheet 是一条 3 步串行流水线**，不是一个 unit。

所以自己起 `ThreadPoolExecutor(min(4, len(sheets)))`，每个 worker 跑
`pipeline.extract_sheet(...)` 整条流水线。

### 10.2 三件必须自己做的事

模板里免费给的东西，自己起线程池就要自己补：

1. **`with llm_units_gate:` 手动包每一次 LLM 调用**。它是模块级
   `BoundedSemaphore(LLM_PARALLEL_UNITS_MAX=10)`、**跨 SQS 任务共享**。不包就绕过了
   提取轨的总并发闸门，多任务 in-flight 时会把 provider tier 撞穿、429 退避拖垮所有
   任务的 P95。旧轨的 salvage 路径就是这么手动包的（`shared.py:890-893`）。
2. **`contextvars.copy_context().run(...)` 每个 sheet 各拷一份**。不能共享同一个
   `Context` 对象——并发 `run` 会抛 `RuntimeError`。这份透传让 worker 内能看到提交方的
   span 栈，`ai_llm_call_log.trace_span_id` 才挂得上。
3. **`TraceContext` 仍要显式按 sheet 构造**。ContextVar 不携带 `file_id` / `table_id` /
   `company_id` 这些审计字段，透传不取代显式参数。

### 10.3 sheet worker 数 = 4

设计文档 §4.3：`5 文件 × 4 sheet = 20` 对闸门 `10` 维持 2× 超订，与旧轨同比值。
**写成模块级常量**（对齐旧轨 `_CLASSIFICATION_MAX_WORKERS = 4` 的做法），不加 env
——D1 的口径是不加开关。

### 10.4 失败传播契约（**照文档实现最容易漏的一处**）

三层各自的失败语义不同，必须写死，否则统计字段会失真、错误升级会误判：

| 层 | 失败时怎么做 | 为什么 |
|----|------------|--------|
| **步内**（`locate.py` 等） | 返回 `None`，**不抛** | 重问一次也是这一层的事，调用方只需知道成没成 |
| **`pipeline.extract_sheet`** | 任一 LLM 步拿到 `None` → **抛 `SheetExtractFailed`**（本包自定义异常） | 见下 |
| **`_run_sheets`** | `except SheetExtractFailed` → `n_failures += 1`，其余 sheet 照跑 | 一个 sheet 读不出来不该让整个文件 SQS 重投 |
| **文件级 `parallel_files_node`** | 收齐后**原样抛出** | 保留"SQS 重投 + resume"语义。**与 sheet 级相反**，别弄混 |

⚠️ **`pipeline` 必须抛而不能"静默产出 0 张表正常返回"。** 后者会让
`_run_sheets` 的 `except` 计不到这次失败，于是 `n_extract_failures` 恒小于
`n_extract_units`，`refine_extraction_node`（`shared.py:2588-2599`）的判据③
`n_extract_units > 0 且 == n_extract_failures` **永远算不出"全失败"**——哪怕所有 sheet
都报废，节点也只表现成 `tables=[]` 的**业务软失败**（`REVIEW_READY`），而不是**技术失败**
（`FILE_FAILED`）。两者在 `save_to_db_node.py:30-31` 走向完全不同的终态。

用异常而不是"判返回值"的理由：`_run_sheets` 已经有 `except` 在计数，再加一条返回值判断
等于两套失败通道，迟早对不上。

### 10.5 `n_extract_units` 的口径是 **sheet**，与旧轨不同

旧轨的 unit = **一次 LLM 调用**（Stage 1b 的 extract unit，`shared.py:938-958` 的
docstring 写明"实际跑 LLM 的 unit 总数"）。本轨取 **sheet** 作为 unit。

**为什么改**：判据③要回答的问题是"这个文件是不是彻底抽取失败了"。本轨每个 sheet 是一条
3 步流水线，"9 次调用里失败 1 次"没有可解释的业务含义（那 1 次属于某个 sheet 的某一步，
该 sheet 已经整体失败了），而"3 个 sheet 全失败"直接对应"这个文件废了"。sheet 粒度让
判据③恰好表达它想表达的意思。

**这个语义差异要在 `pipeline.py` 落一行注释存档**，否则日后排查"为什么这个数字这么小"
会重新纠结一遍。

---

## 11. 测试策略

现有 79 个用例（`tests/ai/excel_extract_agent/`，52 个函数经 parametrize 展开）：

| 文件 | 现状 | 改动面 |
|------|------|--------|
| `test_coords.py` | 15 函数 | **不动**（coords.py 不改） |
| `test_render.py` | 18 函数 | 加：`ind` 折算（空格 / `alignment.indent` / 两者）、5 个样式属性、`with_styles=False` 时不发样式、csv 支路（三种编码）、`_color_id` 的主题色/索引色不被吞 |
| `test_verify.py` | 19 函数 | **契约全改 per-table**；加 D7 三条 + 步 4 三条 |

**契约改动不加兼容适配层**——不做"扁平答案也能过"的兜底。没有生产理由，纯技术债。

新增：

- `test_pipeline.py` —— 三步串行、FATAL 重问一次、重问仍失败则该 sheet 失败
- `test_extract_node.py` —— §3.2 的填写矩阵（三条 return 路径各一例）、软/硬失败二分、
  统计字段诚实性、sheet 级异常不影响其余 sheet
- `test_values.py` —— 按坐标取值、`unit_type` 从 `number_format` 判、符号规则应用、
  聚合行标记

**LLM 调用一律 mock**（`ai/CLAUDE.md`：所有 LLM / AI 组件调用必须 mock，覆盖率 ≥ 80%）。

⚠️ **caplog 断言要用仓库现有的 `_capture_from` helper**：`CIOaaS` 父 logger
`propagate=False`，直接用 caplog 的断言在单文件跑能过、在全量套件里会失败。

---

## 12. 落地顺序

分四批，每批可独立提交与审核：

| 批次 | 内容 | 可独立验证？ |
|------|------|-------------|
| **1** | `render.py`：`ind` + 5 个样式 + `with_styles` + csv 支路；`test_render.py` 补齐 | 是。渲染结果可对着源文件逐格核 |
| **2** | `verify.py`：per-table + D7 三条 + 步 4 三条；提示词 `locate.v2` + 拆三个 `.md`；`test_verify.py` 改 | 是。用批次 1 的视图 + 手写 answer 跑 |
| **3** | `locate.py` / `semantics.py` / `currency.py` / `values.py` / `pipeline.py` + 单测 | 是。LLM mock 后纯逻辑可测 |
| **4** | `nodes/extract_node.py` + 接线（`build.py` / `parallel_files_node.py`）+ `CallerNode` 枚举 + `ai/CLAUDE.md` 条目 | **不是**。要跑真文件端到端，含 §5.1 的 Stage 1b.5 实测 |

| **5** | `crosscheck.py`：步 8 取数后校验（抽样比对 + 聚合行自校验） | 上线**之后**补，口径见设计文档 §7.3（当前标"待设计"） |

批次 1 ~ 3 不碰旧轨、不改接线，随时可停。

**批次 4 的合并前验收清单**（不只是"跑通"）：

1. 跑一遍阶段一那批语料（`C:\Users\Administrator\Desktop\ocr_test_file`，设计文档 §3 的
   16 个 xlsx + §3② 的 7 个最脏形态文件），坐标级回读 0 不一致
2. **实测 Stage 1b.5**（§5.1）：比对前后 `account_label_join` 有无变化
3. **实测 Stage 2.7**（§5.2）：拿一个多 sheet 同名表的文件，确认补出的占位行合理、
   `row_position` 让位不与 `source_row_id` 分配键打架
4. 确认 `n_extract_units` 取 sheet 口径（§10.5）后，`refine_extraction` 的四条错误升级
   判据在真实失败场景下仍能正确触发

⚠️ 批次 5 之前上线，等于只有坐标级校验、没有数值级交叉校验。这是**明知的缺口**，
不是遗漏——见 §2 末尾。

---

## 13. 待同步清单（本文之外要改的东西）

| 对象 | 改什么 | 为什么 | 状态 |
|------|--------|--------|------|
| `../设计/design-doc.md` §5.2 | 步 3 输出契约补 `pf` / `cf` 两个键 | §4.1：漏了会断训练信号链 | **已改** |
| `../设计/design-doc.md` §4.4 | 新增小节，记 `unit_type` 由程序从 `number_format` 派生、`semantic_group` 恒空串 | §4：设计文档的 7 步没覆盖这两个落库字段 | **已改** |
| `CIOaas-python/source/ai/CLAUDE.md` | 本包条目从"尚无 build.py/nodes/tools.py，成图时补齐"改成"本包提供 per-format 节点实现、不自持 graph"；在 §五 追加一条例外，**范围仅限 `build.py`**（`tools.py` 按占位先例建，不属例外） | §2.1 | 待改（属代码仓库，随批次 4 一起） |
| `CIOaas-python/source/common/enums/caller_node.py` | 新增三个值 | §8.4 | 待改（随批次 4） |
| `../设计/design-doc.md` §4.2 / §4.3 / §5.1 / §11 等 | 审核期修正 8 处：步 3 输出形状、单表占比的单位、"旧轨代码一行不改"补"节点"限定、7 个文件 vs 6 类形态、多表统计口径标注全格式、多表时步 3/6 仍每 sheet 一次、tok/s 的分母口径、`openai_compat` 完整路径 | 四路审核 | **已改** |

---

## 14. 明确不做的事（实现期的边界）

- **不改旧轨任何 Stage**（前提 2）。空转的三个 Stage 靠实测确认 no-op，不动刀。
- **不给 `verify_locate` 拆成 per-table 返回多个结果**（§7.1）。
- **不做扁平契约的兼容适配层**（§11）。
- **不 import 旧轨的私有函数**（`_color_id` / `_CSV_ENCODINGS` / `_load_sheet_dataframes`
  一律复制或自写，§6.3 / §6.5）。
- **不抄 `cache_system=True`**（§8.1，D4 定的是缓存先不开）。
- **不用 `json_repair` 抢救截断的坐标 JSON**（§8.3，半个 `tables[]` 比没有更危险）。
- **不加任何 env 开关**（D1）。sheet worker 数写模块常量。
- **不改节点名 `"excel_preprocess"`**（§3.1，它是图边与 span 名的承重字符串）。
