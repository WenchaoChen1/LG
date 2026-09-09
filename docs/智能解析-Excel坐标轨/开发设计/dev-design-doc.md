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
新增 `crosscheck.py`，作为**批次 5**（开发顺序上的最后一批；整个功能做完才上线，所以
它仍在上线之前，见 §12）。

### 2.1 只对 `build.py` 破例（`tools.py` 已按 D9 落地成真工具）

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

⚠️ 别把这条与"为什么用固定状态机而不是自由 ReAct"混为一谈——后者的理由**不含速度**
（实测两者墙钟持平），见[设计文档 §4.1](../设计/design-doc.md)。

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

### 4.2 `column_month` 改由模型给，不由程序解析 `text`

**设计文档 §4.4 原写的是"程序确定性解析 `date_columns[].text`"。实现期发现这条走不通**，
改成 **步 1 同时给 `text`（原文，供回读）与 `month`（归一后的 `YYYY-MM` 或空串）**。

三条理由，一条比一条硬：

1. **旧轨的 `column_month` 本来就是 LLM 给的**，不是程序算的。渲染器只把日期 cell 的
   *显示串*按 `number_format` 的粒度归一成 `YYYY-MM` / `YYYY-MM-DD` / `YYYY`
   （`excel_preprocess_node.py:979` 的 `_extract_date_display`），月份判断在提示词里。
2. **有些列头的月份不在那一格里**。旧轨自己的注释点名了"裸 `Jan`（年份在上一行的常见
   排布）"——程序只拿到 `text="Jan"` 解不出年份，而模型看得到上一行。
3. **有些列头根本没有日历月**（见上方澄清块）：`As of October 21, 2020` 这种非月末
   as-of 日期、`January 1-June 23` 这种跨期区间。程序解析器面对它们只能报错或猜，
   而正确答案是**空**。

**契约**：`date_columns: [{col, text, month}]`

- `text` —— 原文逐字抄，**回读校验的靶子**（这条不变，是本轨最强的一道验证）
- `month` —— `"YYYY-MM"`，**或空串**表示"这一列没有对应的日历月"（合法结果）

**校验**（零额外输出，都在 `verify_locate` 里）：

| 检查 | 级别 |
|---|---|
| `month` 字段必须存在（可以是空串，但不能缺） | FATAL |
| 非空时必须匹配 `YYYY-MM` | FATAL |
| `text` 本身能解析出月份时，必须与 `month` 一致 | FATAL —— 模型自相矛盾 |
| `text` 能解析出月份、而 `month` 给了空串 | WARN —— 可能漏了 |

第三条是白拿的交叉校验：`text` 已经因为回读而必须给，能解析时就顺手比一次。

⚠️ `month` 为空的后果**与旧轨一致**：该行走到 Stage 2.5 会被判 `source_is_mapped=False`
（判据含"该行所有 cell 的 `column_month` 都是源表直读"）。这是既有语义、不是新轨引入的
回归。

### 4.3 `TableInfo` 表级字段

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
| **1b.5** 父链修复 `shared.py:2239` | 修 LLM 写残的 `account_label_join` 前缀（三行窗口锚定） | **原样复用**（已实测） | 见 §5.1 |
| **1c** RAG override `shared.py:2370-2519` | 用 `ai_training_data` 近邻覆盖 `lg_category` | **原样复用** | 它纠正的是**分类判断**，与坐标/数值来源正交。只认 cell dict 的 `account_label_join` + `lg_category` 两个字段 |
| **1d** 列位/行位对齐 `shared.py:1094-1319` | 修多批 LLM 拼表的列/行冲突 | **空转**（预期 no-op） | 根因是"一张逻辑表由多批调用按页拼成"（`shared.py:1099-1105`）。新轨一个 sheet 一次定位调用，`column_position` 出厂即按月份 1..N |
| **2** 链式推月份 `shared.py:1343-1423` | 按左右锚点外推缺失 `column_month` | **空转**（预期 no-op） | 它存在的唯一理由是"LLM 逐 cell 抽取可能漏标某列月份"。新轨逐列穷举 + `verify` 强制原文一致，不存在缺列。`is_predict_month` 因此恒 `False` |
| **2.45** 系统填零 `shared.py:2070` | `value=None` → `0.0` + 标记 | **原样复用** | 业务规则（源表空白/横线该不该算 0），与数值谁读出来无关。程序读真空白格同样得 `None` |
| **2.5** `source_is_mapped` 重算 `shared.py:2106-2157` | 按 `lg_category` + 月份可信度算映射状态 | **原样复用** | 见 §5.3——它会自动退化成简化语义，不需要改造 |
| **2.6** `data_type` 校正 `shared.py:1429-1501` | 用月份 vs 参考日期纠正 LLM 的先验偏差 | **原样复用** | 纯算术规则。新轨的 `column_month` 更可靠，规则更简单地成立 |
| **2.7** 跨表账户对齐补缺 `shared.py:1531-1729` | 同名多个 logical table 间补齐缺账户行 | **原样复用**（已实测；原判"空转"是错的，它确实会触发，但行为符合业务意图） | 见 §5.2 |
| **2.8** 拆 PROFORMA 尾列 `shared.py:1742` | 当月列从 ACTUALS 拆出 | **原样复用** | 纯规则（当月 vs 历史） |
| **2.85** 跨表同月去重 `shared.py:1945` | 同 file 内"月度表 / YTD 表"重复 cell 软删 | **原样复用** | 源文档天然重复，新轨数值再精确也照样发生 |

**两个需实测的都已测完**（§5.1 / §5.2），结论都是原样复用。其余七个的分类可以从触发
条件直接推出，不需要跑数据。

### 5.1 Stage 1b.5（已实测：原样复用）

它修的是"LLM 把父链字符串写残"，用三行窗口锚定 + 尾段对齐。新轨的 LLM 给的是**全量
完整链**（D3），理论上没有残缺可修——但它有可能对**正确的**链做出"修复"，那就是净损害。

**验证方法**（不靠推理，靠实测）：拿新轨产出的 `tables` 跑一遍 Stage 1b.5，逐 cell 比对
前后 `account_label_join` 是否有变化。有变化即需要旁路。

**实测结论（已完成）**：构造一份典型的良构结构——两个语义段（`Income` / `Expenses`）、
段内同缩进、含 `Total XXX` 收束行，正是栈式派生最容易串段的形态——喂给 1b.5，**8 条链
被改动 0 条**。

所以 **1b.5 原样复用，不需要旁路**。这条开放风险关闭。

（对照组：把其中一条链的前缀人为截断后再喂，它也没修——说明本形态不在它的触发条件里，
不是被我们废掉了。我们要的答案是"会不会损坏良构链"，那个答案是不会。）

### 5.2 Stage 2.7（已实测：会触发，但原样复用）

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

**实测结论（已完成）**：造两张同名表（月份连续、账户集合不同，第二张缺 `AR`）喂给它，
`raw_rows` 数 `[6, 4] → [6, 6]`——为第二张表补出 `AR` 的 2 个占位 cell（`value=None`）。
**确实会触发。**

但**行为符合业务意图**：跨表补齐账户就是为了让前端按账户合并时视觉对齐，新轨的多 sheet
同名表与旧轨的多批同名表在这一点上诉求相同。所以处置是**原样复用**，不绕过。

⚠️ 留一条给上线观察：占位行会让同表其余行 `row_position` 让位 +1，而 `source_row_id`
的分配键含 `row_position`（§4.3）。这在旧轨上已经是既有行为、不是新轨引入的，但多 sheet
同名表在新轨上会比旧轨更常见（旧轨是因体量拆表、新轨是因多 sheet），值得在真实多 sheet
同名文件上确认一次行号稳定。

### 5.3 Stage 2.5 为什么不用改造

它的判据是：`lg_category != UNMAPPED` 且 `account_label` 非空 且**该行所有 cell 的
`column_month` 都是源表直读**（非 `None` 且非 `is_predict_month`）。

新轨 `is_predict_month` 恒 `False`、`column_month` 由 `date_columns` 原文确定性解析，
所以第三个条件恒真——**现有代码原样跑出来的就是简化语义**
（`lg_category != UNMAPPED and account_label 非空`）。不是"需要砍掉那一支"，是那一支
永不触发。零改动。

> **审核期澄清（数据判定，含一处自我纠正）**
>
> 曾担心"没有月份的列"会被 Stage 2 的锚点外推静默塞进一个编造的月份。第一次核查只查了
> `source_column_month IS NULL`（0/59644），据此判定"旧轨从不产出无月份的 cell"
> ——**这个判定是错的**：那些行用的是**空串 `''` 而不是 NULL**。
>
> 正确的数据是：**1161/59644 = 1.95% 的行没有月份**，涉及 **22 个 table / 20 个文件
> （11%）**。而且它们**不是合计列**——`source_column_order=1` 上就有 427 行、横跨全部
> 22 个 table。看表名就清楚它们是什么：
>
> | 表名 | 空月份行数 |
> |---|---|
> | `Balance Sheet` / `Caravel Balance Sheet As of October 21, 2020` | 443 / 352 |
> | `Wise Rock, LLC Profit and Loss January 1-June 23, 2026` | 162 |
> | `Balance Sheet as of Dec 31, 19` | 84 |
>
> **非月末的 as-of 日期**（`As of October 21`）与**跨期区间**（`January 1-June 23`）
> ——它们本来就没有"日历月"可对。旧轨的做法是给空串、让
> `source_is_mapped=False`（实测这 1161 行**全部**是 False），把该行标记为不可用。
>
> **所以"没有月份"是一个必须支持的合法结果，不是错误。** 新轨的契约与校验都按这个来
> （§4.2）。原先"程序确定性解析 `text` 得月份"的设想也随之修正——见本节。
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
| 0 | 各表**派生跨度**不重叠 | FATAL |
| 1a | `header_row` 不在本表条目区间下方（否则派生跨度都立不住） | FATAL |
| 1b | **表内出现"重复列头行"** —— 见下 | FATAL |
| 2 | 相邻两表边界处有分隔证据（空行断档，或边界行在条目列是标题性文本） | WARN |
| 3 | 条目列里每个有文本的行都落在某张表的 `label_range` 内；连续 ≥5 行未覆盖 | FATAL（不足 5 行 WARN） |

**⚠️ 检查 1 在实现时被拆成 1a/1b，因为文档原来写的那条在逐表契约下几乎是空的**：跨度
既然由 `min(header_row, 条目起行)..条目止行` 派生，`header_row` 就**天然**落在跨度内，
"落在本表行段内"无从失败。而"两张表被当成一张"这个失败模式在逐表契约下也不再表现为
"缺 header_row"（模型给的那一张表自带一个合法的），于是原检查抓不到它。

**1b 是真正的合并检测器**：两张表被并成一张时，**第二张表的列头行落在第一张表的区间
里**——那一行在期间列上会与本表 `header_row` 的对应格**文本相同**。所以扫表内每一行，
统计它在该表 `date_columns` 上与 `header_row` 文本相同的格子数，**≥2 即 FATAL**。
取 2 而不是 1：单列重合可能只是巧合（两张表都有一列叫 `Total`）。零额外输出。

**另外两处实现期补充**：

- 新增 `date_columns_missing`（一张表没有任何期间列 → 取不出数，FATAL）。
- 覆盖完整性检查把各表的 **`header_row` 也算作"已交代"**：那一行在条目列上常有个
  `Period` / `Account` 之类的标签，它不是条目行、但也不是漏掉的东西。不排除的话每张表
  都会白报一条 WARN（基线夹具上实测到了）。
- "连续"按**文本行序列里的相邻**判、不按行号相邻：漏掉一整张表时它的条目行之间往往夹
  着空行（段落分界），按行号相邻会把一段漏表拆成几个短段、每段都够不到阈值 5。

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

### 8.3 截断：`ask_json` 回 `(应答, 是否被截断)`

`finish_reason == "length"` 要判。旧轨的 `_salvage_truncated_unit` **对本轨无用**——它
只能拆 ≥2 张图的 vision 消息，HTML/文本轨返回 `None`（这也是旧轨 HTML 轨"截断会静默
丢行"的根因）。**不做 `json_repair` 抢救前缀**——半个 `tables[]` 比没有更危险（坐标不全
但外观合法）。

⚠️ **截断必须与其它失败分开回出去**，所以 `ask_json` 的返回是 `tuple[Optional[dict],
bool]` 而不是 `Optional[dict]`：

| 失败种类 | 正确反应 |
|---|---|
| `finish_reason == "length"` | **缩整张 sheet 的批大小**重发（见 §8.4） |
| 解析不出 JSON | **原样重发一次**，仍不行才放弃（切小了也不会变成合法 JSON） |

两者反应相反，混成一个 `None` 就只能二选一。定位步与货币步的输出是 O(列)，拿到这个
布尔量原样 `_` 丢弃即可（`answer, _ = ask_json(...)`）。

另外 `ask_json` 里 `content` 为空要单独挡一下：`parse_json_response` 首行就
`content.strip()`，provider 只回 reasoning 或拒答时 content 是 `None`，不挡直接
`AttributeError`。

### 8.4 步 3 的分批实现

设计与实测依据见[设计文档 §4.5](../设计/design-doc.md#45-步-3-的分批取数d8)，这里只记
落地形状。**只有步 3 分批**，另两步不动。

`semantics.py` 的五个函数，`resolve_semantics` 是平铺主方法：

| 函数 | 职责 |
|---|---|
| `_label_cells(view, geoms)` | 条目区每行的 `(行号, 标签原文, ind)`，取**最左非空**（同 `verify.label_at`），阶梯 / 单列共用一条规则 |
| `_batch_size(cells, geoms)` | 按"预计每行输出 token"反推批大小，钳制 `[_BATCH_MIN, _BATCH_MAX] = [100, 250]` |
| `_label_view(view, geoms, rows)` | 只渲染本批那一段：`row_range=(rows[0], rows[-1])`、`col_range` 取**全部条目列**、`with_styles=True` |
| `_carry_over(answer, texts, batch)` | 挑三段承接文案之一并填行 |
| `_ask_batch(...)` | 发一批：首答 → `verify_semantics(..., rows_scope=set(batch))` → FATAL 则带证据重问一次 → 返回 `(采用的应答, 是否截断)` |

主循环用 `deque`，截断时**把剩余队列按新尺寸整个重切**（左半仍排最前：它的
`open_stack` 要喂给右半，顺序颠倒承接链就反了）：

```python
size = _batch_size(cells, geoms)
queue = deque(rows[i:i + size] for i in range(0, len(rows), size))
shrinks = 0
while queue:
    batch = queue.popleft()
    answer, truncated = _ask_batch(...)
    if truncated and len(batch) > 1:
        shrinks += 1
        if shrinks > _MAX_SHRINKS:               # 250 缩 8 次已 < 1，正常路径够不到
            return None
        size = len(batch) // 2                   # ⚠️ 缩的是后续所有批次，不只这一批
        rest = [r for b in queue for r in b]
        queue = deque([batch[:size], batch[size:]]
                      + [rest[i:i + size] for i in range(0, len(rest), size)])
        continue
    if answer is None:
        return None                              # 已重发过一次，不再救
    out.update(_index_rows(answer, set(batch)))  # ⚠️ 按本批过滤，防跨批静默覆盖
    carry_over = _carry_over(answer, texts, batch)
```

**五处最容易写错**：

1. **`verify_semantics` 必须传 `rows_scope`**。不传的话"每个条目行都要有记录"这条按
   sheet 全集判，每一批都会报"漏了几百行"、每一批都触发一次带证据的重问，调用数直接
   翻倍。**但行号合法性（落在某张表条目区内）仍按 sheet 全集判**——批外的行号是真的错，
   不是"这批没轮到"。
2. **单批 sheet 不走特例分支**。一批就是"批数为 1"，`carry_over` 走第三段文案。分叉出
   一条"短表直发"的路径只会多一处要维护的行为差异。
3. **发给模型的文案一律不许内联进 Python**（`coding.md` § 15 / `ai/CLAUDE.md` § 四）。
   三段承接文案在 `excel_extract_semantics.v1.md` § 7.1~7.3、重问提示在 § 7.4（定位步
   的在 `locate.v2.md` § 7.1），全部经 `_md_loader.load_fragment` 取出——这正是
   `load_fragment` 当初为"切片批次才发的块"设计的用法，`_carry_over` 只负责挑哪一段、
   填哪些行。

   ⚠️ `load_fragment` 按 H3 标题**子串**匹配，且在**模块 import 期**执行：.md 里的标题
   改一个字就 `ValueError`，整个应用起不来，不是某个请求失败。所以
   `test_prompts.py` 必须有一组用例把这五个标题钉住。

4. **模型应答的形状要挡类型**。`open_stack` 退化成 `["Assets", "Cash"]`（字符串数组）
   是极常见的降级形状，只挡 `isinstance(stack, list)` 不挡元素类型的话，一个
   `AttributeError` 会从 `resolve_semantics` 一路冒到 sheet worker，把**已经答对的全部
   批次**一起作废——而触发它的只是一个可选字段。`rows` 同理（可能是字符串数组、也可能
   整个是 dict）。

5. **父链逐字校验的比对集合不能排除数值文本**。段落名本来就可能是纯数字（`2024` 这种
   年度分段头、会计括号负数同理），排掉它们只挡住"模型把 100 当段落名"这种几乎无害的
   情况，却会把一整批正确答案判成臆造。

### 8.5 新增三个 `CallerNode` 枚举值

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
├── excel_extract_locate.v3.md        步 1 定位（含 per-table 输出 schema + data_type）
├── excel_extract_semantics.v1.md     步 3 父链 + lg 指标（含 § 7.1~7.4 三个承接片段 + 重问提示）
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

`excel_extract_semantics` **不升版、留在 `v1`**：它从未进过 git（`git log --all` 为空），
所以分批带来的出参变化（多一个 `open_stack`）是**原地改**。升成 v2 会凭空造出一个仓库里
不存在的前身——版本号只对能被别人 checkout 出来的东西才有意义。`locate` 不同，它的 v1
确实在 `bdafff51` / `bdd0bf7c` 里。该文件同时新增「§ 1 本批的范围与承接」一节、三个
`carry_over` 片段（§ 7.1~7.3）与重问提示片段（§ 7.4），见 §8.4。

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

分五批。**批次是开发与提交的单位，不是发布单位**——整个功能全部完成后一次上线，
不分批发布：

| 批次 | 内容 | 可独立验证？ |
|------|------|-------------|
| **1** | `render.py`：`ind` + 5 个样式 + `with_styles` + csv 支路；`tools.py` 占位 + `nodes/__init__.py`；`test_render.py` 补齐 | 是。渲染结果可对着源文件逐格核 |
| **2** | `verify.py`：per-table + `Issue.table_index` + D7 三条 + 步 4 三条；提示词 `locate.v2` + 拆三个 `.md`；`test_verify.py` 改 | 是。用批次 1 的视图 + 手写 answer 跑 |
| **3** | `llm_call.py` / `locate.py` / `semantics.py` / `currency.py` / `values.py` / `pipeline.py` + **`CallerNode` 三个枚举值** + 单测 | 是。LLM mock 后纯逻辑可测 |
| **4** | `nodes/extract_node.py` + 接线（`build.py` / `parallel_files_node.py`）+ `ai/CLAUDE.md` 条目 | **不是**。要跑真文件端到端，验收清单见下 |
| **5** | `crosscheck.py`：步 8 取数后校验（抽样比对 + 聚合行自校验）+ 步 7 的聚合行标记 | 口径见设计文档 §7.3（当前标"待设计"） |

⚠️ **三处排序修正**（初稿排错了）：

- **`CallerNode` 三个枚举值从批次 4 挪到批次 3**。批次 3 一发 LLM 调用就要传
  `CallerNode.EXCEL_EXTRACT_LOCATE`，排在批次 4 的话批次 3 根本编译不过。
- **步 7 的"聚合行标记"从批次 3 挪到批次 5**。落库表 **37 列里没有**聚合/求和行字段
  （`state.py` 与 `extract_financial.py` 各 0 处命中），而 D5 定的是表结构零改动
  ——这个标记**落不了库**，只能作运行期中间值；而它唯一的消费者就是步 8 的聚合行
  自校验。所以批次 3 的 `values.py` 只做"按坐标取值 + 应用符号/货币规则"。
- **批次 5 不是"上线后补"**。既然整个功能做完才上线，就不存在"生产上只有坐标级校验"
  的窗口——原先写的那个缺口不成立。它只是开发顺序上排在最后。

批次 1 ~ 3 不碰旧轨、不改接线，随时可停。

**批次 4 的合并前验收清单**（不只是"跑通"）：

1. 跑一遍阶段一那批语料（`C:\Users\Administrator\Desktop\ocr_test_file`，设计文档 §3 的
   16 个 xlsx + §3② 的 7 个最脏形态文件），坐标级回读 0 不一致
2. **实测 Stage 1b.5**（§5.1）：比对前后 `account_label_join` 有无变化
3. **实测 Stage 2.7**（§5.2）：拿一个多 sheet 同名表的文件，确认补出的占位行合理、
   `row_position` 让位不与 `source_row_id` 分配键打架
4. 确认 `n_extract_units` 取 sheet 口径（§10.5）后，`refine_extraction` 的四条错误升级
   判据在真实失败场景下仍能正确触发

⚠️ 上面第 1 条的验收在批次 5 之后**值得再跑一遍**：步 8 的聚合行自校验（子项之和 vs
合计行）是唯一能自动扫出"坐标全对但取值 / 符号错"的手段，只有它在手时这轮验收才覆盖
到数值层。批次 4 当时跑那一遍只能覆盖坐标层。

---

### 12.1 真文件验收挖出来的三处修复

批次 4 的端到端验收（8 个 sheet、3092 个 cell、真实 LLM）跑出三个问题，都已修并回归：

**① 符号双重取负——我引入的设计缺陷，也是最严重的一个**

真实文件 `MXTR Balance Sheet` 上 `=SUM(C31:C32)` 的自校验对不上：

```
C31 = 43291.94    C32 = -13512    C33 = =SUM(C31:C32) 缓存 29779.94   ← 文件自洽
抽取后的子项之和 = 56803.94 = 43291.94 + 13512                        ← C32 被翻了
```

`C32` **源值本来就是负数**，而步 6 因为科目名含 `Less:` 把它标了转负。根因是**我的提示词
让模型按"科目名含 `Less:` 且数值为正时才标"判断，而步 6 看不到数值**（按设计只发格式
统计）——那条规则要的信息模型手里根本没有。

两处修：

- **给步 6 每行的符号分布**（`[+]` / `[-]` / `[±]` / `[空]`，O(rows) 不是 O(cells)，
  与"不发格子值"的口径一致），提示词明写"`[-]` 与 `[±]` 的行无论科目名长什么样都不要标"。
- **程序侧兜底**：`SignRules.should_flip` 对**已经是负数**的值忽略**行级**取反并告警。
  只兜行级不兜列级——行级针对 contra 科目，对已是负的值取反必然与意图相反；列级针对
  "变动额 / 减项列"，那种列本就有正有负、取反是要的。

效果：`sums_flagged: 7 → 0`（`sums_checked: 28` 不变）。**这条正是步 8 存在的理由的实证**
——坐标全对、外观正常，只有聚合自校验能抓。

**② 空 sheet 白发了一次 LLM 调用**

`2019 Balance Sheet Detail.xlsx` 的 sheet#0 是个 **0 cell** 的
`QuickBooks Desktop Export Tips` 说明页，对它发一次定位调用白花 4 秒。设计文档 §4.3 的
口径本来就是"每个**有内容的** sheet 跑一遍步 1"，实现漏了这个过滤。已在
`extract_node` 里按 `used_range() is None` 跳过（`sheets` 仍如实列出它）。

**③ 覆盖完整性检查在几乎每个真实文件上白报 WARN**

8 个 sheet 里有 3 个报 `label_rows_uncovered`（第 1~2 / 1~1 / 1~3 行）——那些是**表跨度
之上**的脚手架行（公司名 / 报表标题 / 期间说明），不是"漏掉的条目行"。已把跨度最上沿
之上的行排除在检查之外。效果：`uncovered_runs: ['1-2'] → []`。

> 顺带在真实文件上看到 **FATAL 重问机制生效**：MXTR 首答 `anchors_matched: 2`（1 条
> FATAL）→ 带证据重问 → `3` 并通过。这个环路此前只有单测覆盖。

---

## 13. 待同步清单（本文之外要改的东西）

| 对象 | 改什么 | 为什么 | 状态 |
|------|--------|--------|------|
| `../设计/design-doc.md` §5.2 | 步 3 输出契约补 `pf` / `cf` 两个键 | §4.1：漏了会断训练信号链 | **已改** |
| `../设计/design-doc.md` §4.4 | 新增小节，记 `unit_type` 由程序从 `number_format` 派生、`semantic_group` 恒空串 | §4：设计文档的 7 步没覆盖这两个落库字段 | **已改** |
| `CIOaas-python/source/ai/CLAUDE.md` | 本包条目从"尚无 build.py/nodes/tools.py，成图时补齐"改成"本包提供 per-format 节点实现、不自持 graph"；在 §五 追加一条例外，**范围仅限 `build.py`**（`tools.py` 按占位先例建，不属例外） | §2.1 | 待改（属代码仓库，随批次 4 一起） |
| `CIOaas-python/source/common/enums/caller_node.py` | 新增三个值 | §8.5 | 待改（**随批次 3**——批次 3 就要用） |
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


---

## 15. 步 1 的工具循环（D9）

设计依据见[设计文档 §4.1](../设计/design-doc.md#41-步-1-是工具循环步-3--步-6-是固定调用d9-改)。
这里只记落地形状。

### 15.1 走同步 `agent.invoke`，循环交给 `create_agent`

**（2026-09-08 改写。原文写的是"只能走异步、每条 worker 线程 `asyncio.run` 起一个事件
循环"——那个前提和那个解法都已经不成立，且后者被当成 bug 删掉了。）**

`llm_db_router.complete`（同步）**现在收** `tools` / `tool_choice` / `cache_conversation`，
`DBRouterChatModel._generate` 也接上了它。所以本轨每 sheet 一条线程的线程池直接用
`agent.invoke`，**不自建事件循环**。

自建循环踩的是三个坑，都实测过：

1. `writer.schedule_persist_call` 见到 running loop 就 `create_task`，主协程返回时循环随即
   关闭 → **最后一轮的 `ai_llm_call_log` 记录丢掉**（缺的恰好是产出坐标契约、输入最大的
   那次，按 trace 聚合的成本因此系统性偏低）。
2. 异常路径下那个 task 永不完成 → `_inflight_tasks` 的强引用永不释放 → 累积到上限后
   **整个进程的 LLM 追踪落库降级成同步阻塞写**。
3. 进程级共享的 `AsyncOpenAI` 连接绑定事件循环（`openai_compat/chat.py` 有明写的单 loop
   假设），keep-alive 连接建在已关闭的循环上 → 每个新循环白烧一次重试。

循环本身用 `llm/infrastructure/langchain/` 的 `create_agent`（桥接回统一入口的唯一集成
点），换来的是**工具调用的审计**：那个工厂恒挂 `ToolCallLogMiddleware`，每次工具调用写一条
`ai_llm_tool_call_log` + 开一个 `mcp_tool` span。手搓循环这两样都没有。

两处必须显式给：`provider="openrouter"`（两个 `cache_*` 断点的注入守着它）、
`recursion_limit = 轮数 × 2`（LangGraph 数超步，一轮"模型 + 工具"两步；撞上限抛
`GraphRecursionError`，调用方要接住转成"无应答"）。

### 15.2 三个工具

在 `tools.py`，吃**步 0 已经载入内存的** `SheetView`（工具不碰磁盘）：

| 工具 | ref 形态 | 输出 | 上限 |
|---|---|---|---|
| `read_sheet` | — | `<tr r><td c>` 全表 | `_MAX_CHARS = 40000` |
| `read_range` | `A1:G50` | 同上，矩形 | 同上 |
| `read_line_column_range` | `A5:A200` / `A5:G5` / `B7` | 紧凑 `<c ref="A5">…</c>`，省约 30% | `_MAX_CELLS = 500` |

**四条必须照做的**：

1. **用 LangChain 原生 `@tool`，`SheetView` 经 `ToolRuntime[ExcelToolCtx]` 注入**
   （2026-09-08 改；原文写的是"用裸 schema + 显式 dispatch"）。这样工具才能交
   `create_agent` 驱动、白拿工具调用审计。⚠️ **`tools.py` 因此不许写
   `from __future__ import annotations`**：它会把 `ToolRuntime[Ctx]` 字符串化，历史上会让
   注入静默失效（见记忆 `langchain-toolruntime-future-annotations-gotcha`）。实测当前
   langchain 版本已能处理字符串化的注解，所以这条现在是**版本相关的防御**——留着是因为
   踩过、且降版就复发。另外三个工具要在 `metadata` 里声明 `plain_text`：它们返回的是给
   模型看的坐标视图原文、不走 `tool_result` 的 `{ok}` 约定，不声明的话每一次成功读取都会
   被记成 `FAILED`。
2. **任何失败都返回可读文本，不抛**。抛出去整张 sheet 就废了；模型拿到"区间要形如
   A1:G50"完全能自己纠正——这正是工具循环相对固定视图的价值。
3. **截断必须显式**（`<truncated rows_not_shown=… hint=…/>`）。悄悄少发几行的后果是模型
   把"视图到此为止"当成"表到此为止"，`label_range` 提前截断、后面几百行静默丢掉。
4. **格子文本一律 `escape`**。不转义的话一个含 `<td c="Z">` 字样的备注格就能伪造出一列
   坐标——坐标通道被内容注入，是本包第一性原则要防的那件事。

### 15.3 循环期间关掉 `json_mode`

模型要么回 `tool_calls`、要么回 JSON，强制 `response_format=json_object` 会和工具调用
打架。最终那轮用 `parse_json_response`（含 json_repair 兜底）解析；解析不出就再问一次、
明确要求只输出 JSON（`_JSON_ONLY_HINT`）。轮次上限 `_MAX_ROUNDS = 8`（实测同类 ReAct
max 7）。

### 15.4 回炉要重述首答

`locate._restate` 把首答 `json.dumps` 成一条 assistant 消息再接证据。**不能像原来那样塞
空串**：工具循环里模型看不到上一轮的工具结果（那是另一次 `acomplete` 的对话），空
assistant 消息会让"逐条修正"失去修正对象。

### 15.5 数值段折叠变成可选优化

原先为"步 1 输入无上限"设计的**数值段折叠**（把一行里连续的数值格折成
`<num c="B:Y" n="24"/>`，实测省 51%、把视图从 O(格) 降到 O(行)）**不再是必需项**——
工具有上限、模型可以自己分段读。但它仍能让 `read_sheet` / `read_range` 便宜一半，
且要注意**必须每段保留第一个格子的原文**，否则单独占一行的年份列头（纯数字 `2026`）
会被吞掉，而提示词明确依赖它来补裸 `Jan` 的年份。本次未做。


---

## 16. D9 落地后的真实文件 E2E（挖出 6 个问题）

跑了三个有代表性的文件、全程真 LLM：`2019 Balance Sheet Detail`（QuickBooks 阶梯版式
+ 无列头行的 Sheet2）、`Bevz Balance Sheet`（59 行 × 25 列，输入最大）、
`MXTR P. L`（期间列月/%交替 + 孤立噪声格）。

### 16.1 结果

| 文件 / sheet | 轮次 | 用了什么工具 | 产出 |
|---|---|---|---|
| BS Detail · Tips（空 sheet） | 2 | `read_sheet` | 正确判非财报 |
| **· Sheet1（阶梯版式）** | 2 | `read_sheet` | **70 条目行全覆盖**、orphan 0、月份 `2019-12` |
| · Sheet2（无列头行） | 2 | `read_sheet` | 29 cell、月份空（前端补数据流程） |
| Bevz BS | 3 | `read_range` ×2 分页 | 55 行 × 24 期间列 = 1320 cell |
| MXTR P&L | 3 | `read_range` ×2 分页 | **27 列里只挑出 12 个月份列**、780 cell、SUM 自校验 51 项 0 flag |

阶梯那张之前是 4 个 cell。模型自己按规模选工具（小表 `read_sheet` 一次看全、大表
`read_range` 分页），轮次 2~3，与实测预期的 2.82 吻合。单 sheet 全流水线 25~48 s。

**回炉循环被真实触发过一次并成功**：MXTR 首答把第 92 行（有数值）漏在 `label_range` 外
→ `uncovered_rows_have_values` FATAL → 模型拿到证据后自己去查
`read_range('A80:AA93')` → `read_range('A1:AA10')` → `read_line_column_range('A85:A93')`，
**精准回到出问题的位置**。这是"证据接回同一个循环"相对盲重问的收益，实测到了。

### 16.2 挖出来的 6 个问题（全部已修）

| # | 问题 | 后果 | 修法 |
|---|---|---|---|
| 1 | 回喂 assistant 消息的 `tool_calls` 用了 router 的 `arguments` 键，而 LangChain 回放要 `args` | **第 1 轮不报、第 2 轮回放才 TypeError**，整张 sheet 废 | `llm_call._tool_loop` 转键；测试补 `convert_to_openai_messages` 真转一遍（原来的替身绕过了这层） |
| 2 | 概览列出全文件 sheet，但工具只给当前一个 | 模型第一轮就去读别的 sheet、拿到错误文本，白烧一轮 | `views` 从 `extract_node` 透到 `locate_sheet`；跨 sheet 读本来也**有用**（QuickBooks 把一张表拆两个 sheet、列头只在第一个上） |
| 3 | `_month_from_text` 不认 `Dec 31, 19`（`_MON_YEAR_RE` 中间夹了日期就不匹配） | 模型给空月份时 `date_col_month_empty_but_parseable` 永不响，**49 个格子静默落成无月份** | 加 `_MON_DAY_YEAR_RE`，沿用"月末或 1 号才算该月"口径（`As of October 21, 2020` 仍正确回 None）；提示词对照表补一行 |
| 4 | 未覆盖的条目行**只按段长 ≥5 判 FATAL** | 同一文件两次跑，一次 70 cell 一次 68，差的是 `Total Equity` / `TOTAL LIABILITIES & EQUITY` 两个**有金额的收尾行**，而校验全绿 | 分级改看**这些行有没有数值**：有数值 = 确定丢数据 → FATAL（`uncovered_rows_have_values`）；无数值（脚注）才按段长判 |
| 5 | 视图是转义过的，模型照抄 `T&amp;M Comm`，校验拿原文 `T&M Comm` 比 | 假 FATAL。实测语料 **75/5211 格**含 `&` 或 `<>`，每个用作锚点 / 列头原文 / 父链段都会中 | 新增 `_norm_claim()`（先 `html.unescape` 再归一），用在三处"模型声称的原文"比对上。**只反转义模型那一侧**，原文侧最坏多一次匹配成功、不会造成假失败 |
| 6 | 单批 sheet 也算 `_carry_over`，模型没给 `open_stack` 时刷误导性告警 | 每张表一条噪声 WARNING | 只在 `queue` 非空时算 |

### 16.3 一个必须记住的性质：ReAct 引入了跑与跑之间的抖动

问题 4 是**同一个文件两次跑给出不同 `label_range`** 暴露的（70 cell vs 68 cell）。这是
D9 的固有代价，不是 bug：

- **不能靠"跑一遍看对不对"验收**，要靠**格式无关的不变量**兜。问题 4 的修法正是把一条
  "看段长"的启发式换成一条"有没有数值"的不变量。
- 抖动落在**契约**上（`label_range` 边界），不落在数值上——数值始终由程序按坐标取，
  抽样回读三个文件全部 0 不符。
- 所以 D9 之后，**校验的分级口径比以前更重要**：状态机时代一个 WARN 只是"这次有点怪"，
  ReAct 时代它是"这次抖到了坏的那一侧"。
