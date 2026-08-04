# Excel 科目父链（account_label_join）交由代码计算 — 开发设计

> 关联文档：[财务提取 Python 端设计](../../智能解析/调研/python-design.md)、[系统架构](../../智能解析/调研/system-architecture.md)
> 提示词权威源：`CIOaas-python/source/ai/prompts/extract/data_values.html.v2.md`
> **引用约定**：`§4.6.3` 这类**阿拉伯数字** = 上述提示词的章节；`§四.5` / `§八` 这类**中文数字** = 本文章节。
> 范围：仅 Python（`CIOaas-python`），Excel / CSV 轨。无 Java / 前端 / DDL 改动。
> 可行性验证：独立 demo 工程 `D:\tmp\test_xls`（非仓库内代码），结论见 §九。
> 状态：设计待评审 —— 核心算法已实测验证：合成 fixture 断言 292/292、真实生产用例代码父链 24/24（§9.6）、12 个真实 Excel 文件值定位零错位（§9.7）。日期 2026-08-03（2026-08-04 补 D9~D12、真实生产数据验证、12 个真实 Excel 文件的值定位交叉校验）。

## 一、背景与目标

`account_label_join`（科目父级链，`Assets || Current Liabilities || 2210 Payroll Liabilities` 这种）目前由 LLM 从两个结构信号推导：**col 0 前导空格** + **col-0 纵向合并 rowspan**。

而提示词 §4.6.3 规则2 自己规定：

> 只能从结构信号**机械派生**，**禁止**凭语义猜父级。可用信号**仅限** (a) 前导空白字符数 (b) rs 属性。

也就是说这是一个对代码已有数据的**确定性函数** —— LLM 在这里被要求「执行算法」，而不是「做判断」。为了防止它偏离算法，§4.6.3 与 §5.2 累积了大量规则、反例、自检（BS sibling 跨越陷阱、`2101 Due to Adriana` 完整反例、四条高频踩坑清单）。

**这件事的代价不只是提示词膨胀。** `lg_category` 两条最难的规则完全锚在 join 上：

| 规则 | 依赖 |
|------|------|
| §6.5 COGS↔R&D 冲突 | 「命中主词袋后**只看 `account_label_join`**」→ 含 R&D 父链归 R&D，否则强制 COGS + `cf=true` |
| §6.3 Payroll 父级语境 | 先读 join 判 BS / CF / P&L 分侧，再按父级定 S&M / R&D / G&A Payroll |

→ **join 错则 `lg_category` 必错，且错得静默** —— 兜底路径还会把 `pf` / `cf` 标成 `true`，看起来像「正常兜底」而不是「父链算错了」。

**目标**：把父链计算搬回代码，LLM 不再负责它，从而
1. 给 §6.5 / §6.3 一个不会塌的地基；
2. 删掉 §4.6.3 整节 + §5.2 四条踩坑（输入 token 下降）；
3. 消除「拼字符串」类错误（自父重复 / trailing space / 末尾段等于 label）——代码拼不会错。

## 二、现状盘点

### 2.1 代码侧已有约 80%

| 现有函数 | 位置 | 当前用途 | 与目标的差异 |
|---|---|---|---|
| `_col0_indent_grid` | `excel_preprocess_node.py:1056` | 取 col 0 前导空白宽度（`len(t) - len(t.lstrip(" \xa0"))`） | 无差异，直接复用 |
| `_col0_anchor_text_grid` | `:1041` | 取 col 0 有效文本，含 rowspan 覆盖回查 | 复用；但需区分「本行 label」与「rowspan 祖先」（见 §4.3） |
| `_section_ancestors_grid` | `:1068` | **切 chunk 时**补祖先行进 chunk（不产出 join） | 走法即目标算法，但有两处过滤要调整（见 §4.1） |
| `_is_col0_label_merge` | `:546` | 判 col-0 纵向合并是双列分类法还是 label-merge | 复用，用于 rowspan 派生分流 |
| `_build_logical_grid` | `:983` | HTML → 逻辑网格（rs/cs 还原） | 复用，无改动 |
| `_explode_nested_extraction` | `shared.py`（`:891` 调用处） | 嵌套 `{lg:{parent:[rows]}}` → 扁平 cell，**重建 full join** + row_position 平移 | **join 注入点** |

关键认识：**要写的不是一个新算法，而是把 `_section_ancestors_grid` 的走法从「chunk 上下文用途」提升为「join 权威来源」。**

### 2.2 两个信号源与其边界

| 信号 | 判定方式 | 已知缺口 |
|---|---|---|
| col 0 前导空白 | 原始字符数**相对比较**（`ind < cur` 单调递减），**无「缩进单位」概念** —— 1/2/3 空格每级、乃至同表不等宽（`0/3/5/8`）均正确，唯一要求是「更深 = 更多空格」的单调性 | ① `\t` **不算缩进**（`lstrip(" \xa0")` 不剥 tab，`'\tWages'` → indent 0，且 tab 残留在 label 里）；② NBSP 按 1 字符计，混用 NBSP 与空格时若「更深的层用更少字符」会判反 |
| col-0 纵向合并 rowspan | `_is_col0_label_merge` 分流：双列分类法（col 0 文本进 join）/ label-merge（N 行合 1 条目） | 无 |

### 2.3 输入缺口（硬前置）

现状「层级丢失 → LLM 看到扁平表 → 按 §4.6.3 规则2-反例判全顶层」，结果错但**逻辑自洽**。改成代码算 join 后，同样的文件变成「**代码自信地断言这些行都在顶层**，LLM 无从质疑」——错误一样，但兜底可能性归零。

因此以下缺口**必须先补**：

| # | 缺口 | 说明 |
|---|---|---|
| G1 | `cell.alignment.indent` 完全没读 | Excel「增加缩进」按钮做的层级：cell 值干净无空格，缩进在格式属性里（实测 `value='Payroll'`、`alignment.indent=1.0`）。`pandas.read_excel` 只取 `cell.value` → 层级凭空消失。`_read_workbook_metadata`（`:192`）已在单次 openpyxl 遍历里读 merged ranges / `data_type=='f'` / `number_format` / 日期，同一 `cell` 对象上取 `alignment.indent` 零额外 IO |
| G2 | `\t` 不计入缩进 | tab 缩进的文件全塌顶层；CSV 路径更易命中 |
| G3 | `.xls` 元数据缺失 | 属**独立改造线**（见 §十二），但若 `.xls` 要走本设计，其缩进/合并信号必须先齐 |

> 样本语料实测（`tests/ai/nodes/samples/` 9 个 sheet）：`alignment.indent` 与 `outline_level` 全为 0，层级 100% 走前导空格 —— 与提示词大量 "QB-style" 引用一致（QuickBooks 导出用字面空格）。故 G1 是**潜在**缺口而非已证实的线上问题，会在手工做的 Excel 上咬人。**验证手段**：查线上 `pf=true` / `cf=true` 占比异常。

## 三、已定决策

| # | 决策 | 结论 |
|---|------|------|
| D1 | 用「秩归一成整数层级」还是「直接走链」 | **直接走链**。秩归一只是为了产出「绝对整数 `lv`」这个中间产物；直接算父链不需要它。附带好处：噪声空格的影响**局部化**（只错那一行的父级），而秩归一会凭空多出一整个层级 tier、全表同宽度行连带错 |
| D2 | 是否同时改渲染格式（Markdown / `lv` 列） | **否**。本设计不动渲染格式、不动依赖、不动部署，只把一个确定性算法搬回代码。渲染格式是独立决策线（见 §十二） |
| D3 | 「谁是 join 的权威」的切换方式 | **两阶段**。阶段 A：保留输出 schema 第 2 层 nested key，但**以代码结果为准**、同时记录与 LLM 结果的**分歧率**；阶段 B：分歧率数据支撑后再删字段与 §4.6.3。这样切换零风险且自带 A/B 信号 |
| D4 | 行对齐靠什么 | **代码发稳定 row id、LLM 原样回传**，不再让 LLM 自编 `rn`（详 §五）。这是本设计的硬前提 |
| D5 | 是否覆盖 vision 轨（image / 当前 PDF） | **否**。vision 轨只有像素、无坐标，拿不到确定性结构信号。`_explode_nested_extraction` 为三轨共用 → join 注入必须**按介质 opt-in**（调用方不传 join map 即保持现行为） |
| D6 | 聚合行是否需要在走链时特殊跳过 | **否**（推演见 §四.2） |
| D7 | 层级在入参里怎么表达 | **`parent_chain` 列，用 ` > ` 分隔**（不是 `lv` 整数列，也不是 `\|\|`）。理由：① `lg_category` 判定需要祖先**名字**、直接给最省心（§四.5）；② `\|\|` 与 Markdown 单元格分隔符冲突、要转义成 `\| \|` 每处 +50% 字符且可能被 LLM 字面回写。**入库值仍是 `" \|\| "`（§4.6.3 规定不变）**，`>` 只是入参显示形态 —— 父链在入参里只是给 LLM 读的提示，无需与存储格式一致 |
| D8 | 输出是否保留 `label` | **去掉**。`label` 与 `parent_chain` 都由代码按 `r` 回填。LLM 只决定「哪些 `r` emit / 归哪个 lg / pf·cf / 各 cell 值」。代价见 §5.5（`r` 失去唯一的字段级校验） |
| D9 | 出参 cell 是否保留 `mon` | **去掉，提到表级**。输出加一个表级 `mon_set` 数组（只写一次），cell 只留 `col`，`mon = mon_set[col-1]`。§4.6.4 原文就是这个查表式，逐 cell 重复零信息量 |
| D10 | `ut` / `cur` 怎么放 | **行级默认 + cell 级覆盖**，照 **`data_values.vision.v3.md`（PDF 优化版）**同一套：行级 `ut`/`cur` = 本行多数值；与默认**不同**的 cell **必须**显式覆盖，**相同**的 cell **不写**。保住 §4.6.4「同一条目跨期可换币种，不可提到行级」的语义，同时免掉绝大多数重复 |
| D11 | 出参是否写「不要输出 X」类禁令 | **不写**。schema 里不列该字段本身就是规范；A/B 实测（§9.4）带禁令与不带禁令准确率、多余字段完全相同，禁令白花 728 token，且负向指令反过来提示「该字段存在」 |
| **D12** | **出参是否保留数值 `v`** | **去掉，`cells` 数组整个删除**。值本来就在**入参**里，LLM 只是在抄一遍。改为：出参加一个表级 `cols` 数组（cn → 入参物理列号），代码按 `(r, cols[cn-1])` 从网格取值 + 套 §4.6.4 的五条确定性变换。唯一非确定性的 §6.1 Revenue Contra 改为**行级 `contra` 布尔**，代码据此取 `-abs()`。→ 出参从 O(行×列) 降为 **O(行)**。实测宽表 completion **−82.9%**、墙钟 **−80.5%**、值定位 **912/912 零错**（§9.7） |

## 四、核心算法

### 4.1 父链计算（复现 §4.6.3 规则1）

对每个源行 `r`，自下而上单调递减走：

```
cur = indent(r)
ancestors = []
i = r - 1
while i > scaffold_bound:
    if has_col0_label(i) and indent(i) < cur:
        ancestors.append(i)
        cur = indent(i)
        if cur == 0: break
    i -= 1
ancestors.reverse()
join = " || ".join(strip(label(a)) for a in ancestors)
```

与现有 `_section_ancestors_grid` 的三处差异：

| # | 现状 | 改为 | 理由 |
|---|---|---|---|
| 1 | 过滤 `not _row_has_numeric_grid(i)`（**带数值的行不算祖先候选**） | **去掉该过滤** | §4.6.1.2 QB-style：「自带数据的父级行」既作叶子 emit、又作下层 `parent_chain` key。现状过滤会让自带数字的父行丢掉一层链（切 chunk 时已存在此偏差） |
| 2 | `lower_bound = month_idx` | **保留** | 防止公司名 / 报表标题 / 期间说明等 scaffolding 行成为所有人的祖先 |
| 3 | 只有缩进派生 | **接入 rowspan 派生**（§4.3） | §4.6.3 规则1(b) |

**单位无关性**：算法只用 `indent(i) < cur` 一个不等式，只关心序不关心量 —— 与现状语义完全等价，故不改变既有正确案例的结果。

### 4.2 聚合行不需特殊处理（推演）

§4.6.3 规则1-自检（BS sibling 跨越陷阱）的存在是为了纠正 LLM 的**语义联想**，不是因为算法困难。朴素单调走法在该场景本来就对：

```
Income          (0)
   Sales        (3)
Total Income    (0)      ← 聚合行
Cost of Goods   (0)
   Amazon       (3)
```

从 `Amazon`(3) 向上找首个 `indent < 3` → `Cost of Goods`(0)，正确；`Total Income` 在更上方、根本走不到。要出错需让 Total 的缩进**小于**下一个 section 标题——畸形表。

→ §4.6.3 规则1-自检整段 + `2101 Due to Adriana` 反例可删。

### 4.3 rowspan 派生接入

col 0 被上方 `<td rs="N">X</td>` 覆盖时，按 `_is_col0_label_merge` 分流：

| 形态 | 判据 | join 处理 |
|---|---|---|
| **双列分类法** | 覆盖范围内任一行 col 1 是非数值文本（子条目 label） | `X` 是祖先，排在缩进派生祖先的**更外层**（最左）；被覆盖行的 label 取 col 1 |
| **label-merge** | col 1+ 全为数值 / 空白 | N 行合为 1 个条目，join 按 anchor 行计算一次 |

注：`_collapse_label_merge_blocks`（`:609`）已在渲染前把「col-0 稀疏互补」子形态坍缩掉，走到这里的是其余形态。

### 4.4 缩进输入归一

计算 `indent(r)` 时的有效缩进 = **字面前导空白宽度 ⊕ 原生 `alignment.indent`**（G1）。两者如何合成需一次实测定标（Excel 1 个 indent 单位 ≈ 3 字符宽），但因算法只比较序，**定标精度不敏感** —— 只要同一文件内单调性成立即可。tab（G2）统一按「等效 N 空格」折算或直接纳入 strip 集合。

### 4.5 祖先可达性不变量（⚠️ 代码算 join **不等于** LLM 不再需要祖先）

**这是 demo 暴露出来的、本设计初稿漏掉的一条硬约束。**

代码接管 join 之后，LLM 仍然**必须能读到祖先的名字** —— `lg_category` 三条最难的规则全靠祖先**字面**：

| 规则 | 依赖的祖先字面 |
|---|---|
| §4.6.2 规则4 P&L / BS / CF 分侧 | `Liabilities` / `Assets` / `Operating Activities` … |
| §6.3 Payroll 父级语境（含 BS 段硬例外） | `R&D` / `S&M` / `G&A`；`Liabilities` |
| §6.5 COGS↔R&D 反推锁定 | 含 `R&D` 还是含 `Cost of` |

所以必须成立的不变量是：

> **每个祖先名都能在其所属行的上方被找到** —— 具体形式为「上方最近一个层级更浅的行即直接父级」。

现状 HTML 轨**天然满足**（祖先行都原样在表里、缩进肉眼可见），所以初稿没意识到这是个需要显式维护的条件。但**任何「把祖先行吃掉」的归一都会破坏它**，已知三种形态：

1. **双列分类法拍平** —— col-0 rowspan 的父分类文本被吃进 join 后从表里消失（demo f03 实测命中）
2. **多表 sheet 按 `row_range` 切分** —— 表标题行落在切分边界外
3. **chunk 行切片** —— `_section_ancestors_grid` 现有逻辑已在补祖先行，但它**排除带数值的行**（§4.1 差异 1），QB-style 自带数据的父行会漏

**违反的后果是静默的**：LLM 读不到祖先 → 正确地走「祖先链为空」兜底分支 → `cf=true` / `pf=true`。而这两个标记正是用来诊断「父链有没有塌」的线上信号，假阳性会**污染诊断本身**。

**保证方式（demo 已 A/B 实测，见 §九）**：

| 方案 | 做法 | 成本 |
|---|---|---|
| A | 渲染层补齐：缺失的祖先补一行「无 id、无数据」的 section header 行；层级用 `lv` 整数列 | 只在真缺失时付费；祖先本就可见时零开销。但**正确性依赖一条不变量** |
| **B（已定，D7）** | 每行直接带 `parent_chain` 列 | 恒定开销（demo 表体 1,181 → 1,288 tiktoken，+9%），但**不依赖任何不变量**、抗渲染层 bug |

两者准确率相同（demo 各跑一轮均 100%）。**取 B**：A 省的那点 token 换来的是「必须靠断言保住不变量」，而违反是**静默**的（LLM 读不到祖先 → 正确地走兜底 → `cf`/`pf` 假阳性 → 污染诊断信号本身）。B 把祖先名直接写在每行上，渲染层再怎么归一都不会丢。

⚠️ **B 的分隔符必须换掉 `||`**：join 的分隔符是 `" || "`（§4.6.3：双竖线左右各一空格），而 `|` 正是 Markdown 的单元格分隔符 → 进表格得转义成 `" \|\| "`，**每处 +50% 字符**（demo f05 单表 10 处），且 LLM 可能把 `\|\|` 字面回写。**入参改用 ` > `，入库值不变**（demo 实测表体 1,348 → 1,288 tiktoken）。

> A 方案的祖先可达性断言仍**建议保留为兜底自检**（成本近零、能在渲染层出 bug 时先报警），只是不再是正确性的唯一依靠。

## 五、关键前提：稳定 row id 契约（D4）

### 5.1 为什么 `rn` 不能用作对齐键

代码按源行号算出 `{源行号: join}`，但 LLM 输出的 `row` 字段（`rn`）**不是源行号**：

- §4.5：`rn` 由 LLM 在 `raw_account_set` 上从 1 自编；
- §4.5 label-merge：N 个源行合并成 1 条目 → **只占 1 个 `rn`**；
- §4.6.1 被跳过的行「保留 `rn`」，但 LLM 是否严格照做无法保证。

→ `rn` 与源行号**非位置一一对应**，任何一处合并/漏算都会让其后全部错位。按 `rn` 回填 join 会**静默串行**，比现状更糟。

### 5.2 契约

1. 渲染时每 `<tr>` 的 col-0 `<td>` 带稳定 id 属性（形如 `r="12"`，全局唯一、跨 chunk 不变）；
2. 输出 schema 的 `row` 字段语义改为「**回传你看到的 `r` 值**」，不再自编；
3. label-merge 合并成 1 行时回传 anchor 行的 `r`。

### 5.3 顺带收益：`CHUNK_ROW_STRIDE` 可退役

`shared.py:120` 的 `CHUNK_ROW_STRIDE = 100000` 是为了「不同 chunk 的 `rn` 不在 `(table_id, row_position)` 入库键上碰撞」而做的区间隔离 hack（`:553-554` 平移）。id 本就全局唯一 → 平移逻辑可整块删除。**注意** `shared.py:719-720` 另有一处「从头编 row_position 时共用 offset 会让两半同名行撞同一 `source_row_id`」的相关处理，需一并核对。

### 5.4 排序不变量

`shared.py:909-916` 按 `(row_position, column_position)` 排序恢复报表顺序、供入库 `source_row_id` 按出现序分配。若 `r` 为「源行号 + 表内偏移」的单调序列，该排序语义不变；若改用非单调 id（如 uuid），此处必须改。**结论：`r` 必须是单调递增整数。**

### 5.5 去掉输出 `label` 的代价与替代校验（D8）

`label` 与 `parent_chain` 都由代码按 `r` 回填后，**`r` 失去了唯一的字段级校验**：LLM 若把 `r=5` 错成 `r=6`，两个 id 都合法、字段全都对得上，**无法检出**，而后果是整行数据挂到错误科目上。

保留 `label` 作 checksum 的成本很低（demo 实测约占 completion 的 6~8%），**但已按 D8 去掉**，故必须补上替代校验：

| 校验 | 能力 | 成本 |
|---|---|---|
| **`r` 合法性**：返回的每个 `r` 必须在本 chunk 的行 id 集合内 | 挡住臆造 id / 跨 chunk 串号 | 零 |
| **cell 值交叉核对**（推荐）：代码知道每个源行的原始数值，比对 LLM 返回的 `v` 与 `r` 所指源行的值 | 挡住**行错位**（错位后值必然对不上源行） | 零（`v` 本来就在输出里） |
| **emit 候选集**：`r` 必须是「有数据的行」（纯 header 行不该被 emit） | 挡住把 header 行当叶子 | 零 |

⚠️ cell 值核对是**启发式不是精确匹配** —— `v` 经过千分位 / 括号负 / 货币符剥离 / §6.1 Revenue Contra 强制负化等变换，故按「绝对值集合是否吻合」这类宽松口径比对，不吻合时**告警不阻断**。

### 5.6 ⚠️ 注入的是 parent_chain，**不是**入库那个全路径

`ai_financial_extraction_mapping_data.source_account_label_join`（入库值）**含当前行自身**，由 `shared.py:478` 拼出：

```python
full_join = "||".join(p for p in [parent_chain, account_label] if p)
```

而 LLM 输出的第 2 层 nested key（本设计要替换的那个）是**纯父链、不含自身**（§4.6.3）。两者差一段。

→ **代码注入 `join_by_row` 时必须给纯父链**，让 `shared.py:478` 的拼接照原样跑。若误注入全路径，末段会翻倍成 `... || A || A`，且**入库不报错**、要到前端才看出来。

> 实测踩过：第一轮拿代码算的父链直接对 DB 的 `source_account_label_join`，比出 0/26「全不一致」，误以为是生产 bug；对齐口径后是 **24/24 = 100%**（§9.6）。
>
> 另注：DB 实测分隔符是 ` || `（两侧带空格），而 `:478` 是 `"||".join(...)`（无空格）—— 中间还有 `repair_account_label_joins_in_tables`（`shared.py:1843`）等归一环节。**实现时以实际入库值为准**，不要照着 `:478` 那行推断最终格式。

## 六、改动清单

| # | 文件 | 改动 |
|---|---|---|
| 1 | `excel_preprocess_node.py:192` `_read_workbook_metadata` | 读 `cell.alignment.indent`，随 metadata 返回（G1） |
| 2 | `excel_preprocess_node.py:490` `_cell_td`（前导空白处理在 `:530-532`） | 有效缩进合成（字面空白 ⊕ 原生 indent ⊕ tab 折算，G1/G2） |
| 3 | `excel_preprocess_node.py` 新增 | `_resolve_account_joins(grid_cells, month_idx) -> dict[int, str]`：§4.1 + §4.3 的父链计算，返回 `{row_id: join}` |
| 4 | `excel_preprocess_node.py:1292` `_render_grid_rows_as_html` + `_render_html_with_merges`（`:665`） | col-0 `<td>` 输出 `r="N"` 稳定 id（§5.2） |
| 5 | `excel_preprocess_node.py:983` `_build_logical_grid` | 解析并透出 `r` 属性（现只取 `rs`/`cs`；`f` 亦未取，见 §八注） |
| 6 | `excel_preprocess_node.py` `_build_extract_units`（`:1500` 附近） | unit 携带本 chunk 的 `join_by_row` 子集 |
| 7 | `shared.py` `_explode_nested_extraction` | 新增**可选** `join_by_row` 入参（值是**纯父链**、不含自身，见 §5.6）：给了就以代码结果为准 + 记录与 LLM 结果的分歧（D3 阶段 A）；不给则保持现行为（D5）。`:478` 的 `full_join` 拼接**不动** |
| 7b | `shared.py` `_explode_nested_extraction` | 同批适配新出参 schema：顶层 `{mon_set, cols, data}`、`mon` 由 `col` 查 `mon_set`（D9）、`ut`/`cur` 行级默认（D10）、`label` 按 `r` 回填（D8，含 UNIDENTIFIED 归一） |
| 7c | `shared.py` `_explode_nested_extraction` | **值由代码重建**（D12）：按 `(r, cols[cn-1])` 从网格取原文 → 套 §4.6.4 五条变换 → `contra` 为真时取 `-abs()`。每个 emit 行 × 每个 cn 都产出 cell（含 null），对齐 §4.6.5「总 cell 数 = mon_counts × account_counts」 |
| 7d | `shared.py` 新增 | **两个丢失探针**（§9.7）：① 列外数值（emit 行内、列不在 `cols`）② 整行跳过（有值未 emit）。**都是 warning 不是 error** —— 合计/比率列会合法命中 ① |
| 8 | `shared.py:120` + `:553` + `:719` | `CHUNK_ROW_STRIDE` 平移逻辑退役（§5.3，可延后到阶段 B） |
| 9 | `data_values.html.v2.md` → 新版本 | 见 §八 |

## 七、提示词改动

新增版本文件（**已应用版本不改**，按 `ai/CLAUDE.md`「提示词以 markdown 为权威源、带版本后缀」）：`data_values.html.v3.md`。

**阶段 A（并行验证期）**：
- §4.5 `rn` 定义 → 改为「回传 `r` 属性值」；
- 其余不动（第 2 层 nested key 仍由 LLM 产出，供分歧率统计）。

**阶段 B（切换完成后）**：
- 删 §4.6.3 `account_label_join` 整节（含规则1/1-自检/2/2-反例 + 全部 example）；
- 删 §5.2 四条父链踩坑清单 + 「禁止反例」段；
- 删 §4.6.4 `label` 字段规则（D8：LLM 不再回传 label）；
- **新增入参格式段**：说明 `r` / `parent_chain`（` > ` 分隔）/ `account` / 数据列各是什么，并明确「父链已由上游算好，判 `lg_category` 时**直接读 `parent_chain` 列**，不许从缩进 / 语义自行推导」；
- §3.2 / §4.6.2 / §6.3 / §6.5 里所有「读 `account_label_join`」的措辞改为「读 `parent_chain` 列」（规则逻辑不变，只换指代）；
- §1.2 输出 schema：移除第 2 层 nested key（降为 `{lg_category: [rows]}`）+ 移除 `label` 字段 → 行对象只剩 `r` / `pf` / `cf` / `cells`。**schema 里不写就是规范，不要再补「不要输出 label / parent_chain」这类显式禁令** —— demo A/B 实测（§9.4）：带禁令与不带禁令**准确率同为 285/285、多余字段同为 0**，而禁令白花 728 真实 prompt token。负向指令还反过来提示了「这个字段存在」；
- 保留一条正向强调：「`r` 是唯一行标识，必须来自输入表、必须精确，写错无法被检出」—— 因为 D8 去掉 label 后确实没有字段级校验了（§5.5）。⚠️ **这一条未做 A/B**，是否必需待验。
- §4.6.1 的 UNIDENTIFIED 行规则去掉「`label="UNIDENTIFIED"`」（改由代码回填），只保留「照常 emit + `lg` 强制 UNMAPPED + pf/cf false」；
- §4.6.1 其余保留（emit 与否仍属 LLM 语义判断，与 join 计算无关，提示词自身已声明二者分离）。

> demo 实测的 token 走向（7 次调用合计，API 回报值）：
>
> | 提示词形态 | 真实 prompt | completion |
> |---|---|---|
> | 出参含 `label` + `\|\|` 分隔 | 51,722 | 6,609 |
> | 出参去 `label` + ` > ` 分隔 + **带禁令** | 53,186 | 6,100 |
> | 出参去 `label` + ` > ` 分隔 + **无禁令（采用）** | **52,458** | 6,222 |
>
> 两条教训：① **裁剪提示词时别只算删的、不算加的** —— 中间那行删了 label 规则却因新增禁令净涨 1,464；② completion 在 6,100~6,609 间波动（`temperature=0` 仍非完全确定），**单轮差异 <5% 不要当结论**。

> **注意**：`IDENTIFY_DATA_VALUES_FROM_HTML_*` 由 `excel_preprocess_node` 与 `pdf_preprocess_node`（**text-PDF 轨**）**共用**。text-PDF 轨当前被注释禁用（`pdf_preprocess_node.py:141` `# if metadata.has_text_layer:`），故本设计落地范围 = Excel/CSV。若日后重启 text-PDF 轨，它必须一并发 `r` id ——**且其父链信号更干净**：`pdfutil/text_tables.py:127` `_indent_levels` 已用标签左边界 x0 算出离散层级，随后在 `:165` 用 `"  " * lvl` 降级回前导空格供 LLM 反推，本设计正好消除这次 round-trip。

## 八、边界与已知限制

| # | 限制 | 处理 |
|---|------|------|
| L1 | **UNIDENTIFIED 行**（col 0 空但有数据）：`_col0_anchor_text_grid` 返 `""` → indent 0 → 走链时 `ind < 0` 永假 → 链为空。但 §4.3 要求这类行「保留 ancestor 链」 | 需显式定规则：沿用**上一行的 indent** 作为起点。该行仍不作祖先候选（`col0_text.strip()` 已保证） |
| L2 | **噪声空格造假层级**：手滑多打一空格使 sibling 变 child | 影响**局部**（只错该行父级）。可加告警：某宽度全表仅出现 1-2 次时 warning |
| L3 | **多表 sheet**：一张 sheet 上下叠两套缩进约定 | 父链按 `_resolve_table_ranges_across_sheets` 切出的 `row_range` **按表**计算，不跨表走链。（与「不能逐 chunk 算」不冲突：表是语义单位、chunk 是切片单位，前者可分后者不可分） |
| L4 | **错误性质改变**：代码算错 = 静默数据错误，LLM 不再有机会靠语义兜 | 必须配：语料回归、「层级跳跃 > 1」告警、阶段 A 分歧率监控 |
| L5 | `f="1"` 公式标记 | 与本设计无关，不动。（`_build_logical_grid` 现未解析 `f` 属性，`r` 的解析实现可顺带对齐，但不改变 `f` 的语义用途） |
| L6 | vision 轨（image / 当前 PDF）不受益 | D5 已定：join 注入按介质 opt-in，vision 轨提示词与行为完全不变 |
| L7 | **祖先可达性不变量被破坏**（§四.5）：归一 / 切分吃掉祖先行 → LLM 读不到祖先名 → 静默走兜底、`cf`/`pf` 假阳性 | **渲染层断言**：每行的每个祖先名必须能在上方找到一个层级更浅的行，不成立就补合成 header 行 + 打 warning。断言进单测，覆盖双列分类法 / 多表切分 / chunk 边界 / QB-style 自带数据父行四种形态 |
| L8 | ⚠️ **「末段 = 前一段」不是错误判据** | QuickBooks 的**同名父子**（账户组 + 同名账户）是真实合法形态，full path 天然出现重复段。真实数据实测：`Bevz Balance Sheet` 源 HTML 里就是 `'      Accounts Receivable'`（6 空格，组）+ `'         Accounts Receivable'`（9 空格，同名账户）→ 全路径 `... \|\| Accounts Receivable \|\| Accounts Receivable` **正确**。§5.2 禁止的是「父行被错放进**自己**的 bucket」，与此不同。**别把这个形态写成校验规则**，单测须专门覆盖以防后来人误"修" |

## 九、demo 实测验证（2026-08-03）

独立 demo 工程 `D:\tmp\test_xls`（uv 管理，7 个 `.xls` fixture + 标准答案 + 评分器；非仓库内代码，仅作可行性验证）。链路 = `.xls` → 逻辑网格 → 代码算 join → **Markdown 表**入参 → `anthropic/claude-opus-5`（经 OpenRouter，与生产同模型）。

### 9.1 结果

最终形态（D7 `parent_chain` + ` > ` / D8 去 `label` / D9 `mon` 表级 / D10 `ut`·`cur` 行级默认 / D11 无禁令）实测：

| 指标 | 数值 |
|---|---|
| **代码回填字段准确率** | **74/74 = 100%**（`join` + `label` 两个字段，LLM 均不产出） |
| **LLM 断言通过率** | **292/292 = 100%**（7 个 fixture 全过，无失败断言） |
| 输出契约遵守 | **零多余字段** —— 7 个 fixture 无一回传 `label` / `parent_chain`，且**未用任何显式禁令**（§9.4） |
| 稳定 row id 契约 | **零臆造 id、零错位** —— `r` 回传机制成立（§五） |
| 耗时 | 7 个 fixture 共 **64.7s**（单个 6.3~11.6s） |
| 真实 token | prompt 59,591 / completion **4,296**（API 回报，Claude 分词器） |
| **真实生产用例** | 代码父链覆盖入库全路径 **24/24 = 100%**，表体 token **−44.1%**（§9.6） |

演进过程（三轮，同一套 fixture 与断言）：

| 轮次 | 入参层级形态 | 输出含 `label` | LLM 断言 | 表体 tiktoken | 真实 completion |
|---|---|---|---|---|---|
| ① | `lv` 列（祖先行被吃掉） | ✅ | 316/317 | 1,158 | 6,495 |
| ② | `lv` 列 + 补合成祖先行 | ✅ | 317/317 | 1,181 | 6,495 |
| ③ | `lv` 列 → `parent_chain`（`\|\|` 转义） | ✅ | 317/317 | 1,348 | 6,609 |
| ④ | `parent_chain` + ` > ` 分隔 + 显式禁令 | ❌ 去掉 | 285/285 | 1,288 | 6,100 |
| ⑤ | 同上，去掉禁令（schema-only，D11） | ❌ | 285/285 | 1,288 | 6,222 |
| **⑥ 最终** | 同上 + `mon` 表级 + `ut`·`cur` 行级（D9/D10） | ❌ | **292/292** | **1,288** | **4,296** |

> ③→④：`>` 换掉 `\|\|` 让表体 −4.5%（1,348 → 1,288）；去掉 `label` 让 completion −7.7%。
> ④→⑤：删禁令，准确率与多余字段不变、prompt −728（§9.4）。
> ⑤→⑥：**completion −31.0%、7 fixture 总墙钟 −22.1%**（§9.5）。
> 断言总数 317→285 是 label 断言从 LLM 侧移到代码侧（并入「代码回填 74/74」）；285→292 是新增 `mon_set` 与「覆盖卫生」断言。

fixture 覆盖：前导空格层级、**原生 `alignment.indent`**（G1 探针）、tab / NBSP 缩进（G2）、双列分类法、label-merge 稀疏 + 稠密、cs 季度表头、QB-style 自带数据父行、真聚合行、比率行印成小数、Revenue Contra 强制负、COGS↔R&D 冲突三分支、Payroll 父级语境 + BS 段硬例外、黑名单反例、UNIDENTIFIED 行、稀疏空 cell 列对齐、`Total` 列跳过、`Notes` 非期间列、`[$¥-411]` LCID 消歧。

### 9.2 关键验证点

1. **`account_label_join` 确实可由代码算准** —— 单调递减走链 42/42，其中 f05 那张 4 层 BS 表把 §4.6.3 规则1-自检的「`2101 Due to Adriana` 陷阱」原样复刻，代码一次走对（印证 §四.2 的推演：该段自检可删）。
2. **label-merge 代码求和成立** —— 稀疏 `[45000,'',47000] + ['',48000,'']` → `[45000,48000,47000]`；稠密三行 → 逐列累加。合并后 LLM 只看单行稠密数据，该 fixture **completion 仅 410 token / 6.8s 全对**。生产 HTML 轨这里是「错列相加」重灾区（§4.5 用了 4 个带反例的段落在打它）。
3. **原生缩进是真缺口（G1）** —— f02 那张表值里零空格、层级全在 `alignment.indent` 里。读到 = 100%；读不到则 join 全塌成空 → `Wages` 变 G&A Payroll+`pf=true`、`Cloud Hosting (AWS)` 变 COGS+`cf=true`。**生产现在正是读不到的状态。**
4. **祖先可达性是硬约束（§四.5，D7 的由来）** —— 第①轮唯一一次失败（f03 `Hosting` 的 `cf` 假阳性）根因是渲染层把 col-0 父分类吃掉了、LLM 读不到祖先名，7 个 fixture 里只有它祖先名缺失、也只有它失败，单变量归因干净。这条促成了「入参直接带 `parent_chain` 列」的决策 —— 不再依赖「祖先行必须可见」这条易被归一破坏的不变量。
5. **输出瘦身靠 schema 本身就够** —— 7 个 fixture **零多余字段、零错位**，无需任何显式禁令（§9.4）。说明 D8 在提示词层面可落地，不需要靠后处理丢字段、也不需要负向指令。

### 9.3 A/B：层级怎么表达（→ D7）

| 方案 | 表体 tiktoken（7 fixture 合计） | vs HTML 基线 | 准确率 |
|---|---|---|---|
| A `lv` 整数列 + 缺失祖先补合成行 | 1,181 | −31.0% | 100% |
| B `parent_chain` 列（`\|\|` 转义） | 1,348 | −21.3% | 100% |
| **B' `parent_chain` 列 + ` > ` 分隔（已定）** | **1,288** | **−24.8%** | **100%** |

三者准确率相同。A 最省（比 B' 再省 8%，f05 那张 4 层深表单看 209 vs 343），**但它的正确性挂在「祖先行必须可见」这条不变量上，而违反是静默的**。B' 把祖先名直接写在每行 → 渲染层怎么归一都不会丢，为这份鲁棒性付 8% 是划算的（D7）。

`>` 相比 `||` 省的 4.5%（1,348 → 1,288）纯粹来自免掉 Markdown 转义。

### 9.4 A/B：出参契约要不要写显式禁令（→ 不要）

去掉出参 `label` 时的一个自然疑问：需不需要在提示词里补一句「不要输出 `label` / `parent_chain`」？

| 提示词 | LLM 断言 | 多余字段 | 真实 prompt |
|---|---|---|---|
| 带禁令 | 285/285 | 0 | 53,186 |
| **无禁令（schema-only，采用）** | **285/285** | **0** | **52,458（−728）** |

→ **schema 里不写这些字段本身就是规范**，显式禁令零收益、白花 728 token；而且负向指令反过来在提示「这个字段存在」。**结论：不加。**

（`r` 精确性那条正向强调保留但**未做 A/B**，因 D8 去掉 label 后确实无字段级校验兜底，见 §5.5。）

### 9.5 出参再瘦身：`mon` 表级化 + `ut`/`cur` 行级默认（→ D9 / D10）

问题起点：算清输出 token 构成后发现，**单个 cell ≈ 28 token，而它出现「行数 × 期间列数」次**，行级字段只出现行数次。所以去掉 `label` / 第 2 层 key 对**宽表**几乎没用：

| 表形状 | cells 占输出 | 去 `label` + 去第 2 层 key 的降幅 |
|---|---|---|
| demo 窄表（6 行 × 3 列） | 85% | −7.5% |
| **真实宽表（40 行 × 24 列）** | **~100%** | **−1.1%** |

→ 真正的杠杆在 cells 内部：`mon` 是纯查表（`mon = mon_set[cn-1]`）、`ut`/`cur` 绝大多数全表同值。改成 D9 + D10 后实测：

| | 改前 | 改后 | 变化 |
|---|---|---|---|
| LLM 断言 | 285/285 | **292/292**（新增 mon_set + 覆盖卫生断言） | 全过 |
| **completion（真实）** | 6,222 | **4,296** | **−31.0%** |
| **7 fixture 总墙钟** | 83.1s | **64.7s** | **−22.1%** |
| prompt（真实） | 52,458 | 59,591 | +13.6% |

- **这是实测墙钟、不是 token 折算** —— 单 fixture 最快的 f04 从 10.2s → 6.3s（completion 522 → 291）
- prompt 那 +7.1k 全来自新增的 schema 说明 + 正例 + 禁止反例（照 vision v3 抄的三段）。按仓库 `pricing.py` 的 Opus 档（$5/$25 per M）折算：输入多花 $0.036、输出省 $0.048，**成本基本打平但墙钟省 22%**
- 而且 prompt 那部分是**固定成本**（系统提示词可缓存，生产 `cache_system=True`），completion 的 −31% 是**随表规模线性放大**的
- 评分器加了**覆盖卫生检查**（cell 写了与行级默认相同的 `ut`/`cur` 即算违约）→ 7 个 fixture **零违约**，含 f02 那张「`Cash` 是 JPY、其余行无货币格式」的表，模型正确在行级给 JPY 而没污染别行

### 9.6 真实生产数据验证（经 DB 取真实 `sheet_html` + 入库结果）

不再靠合成 fixture —— 直接从生产库取真实用例（新增 `fetch_real.py` / `run_real.py`，**只读不写库**）：

- 取数链路：`ai_financial_extraction_mapping_data`（入库提取结果）→ `file_id` → 反查 `checkpoint_blobs.file_list` 定位 thread → 同 thread 的 `sheets` blob（msgpack，含真实 `sheet_html`）
- HTML → 逻辑网格**直接复用生产的 `_build_logical_grid`**，保证 rs/cs 还原口径与生产一致

用例 `Bevz Balance Sheet - Monthly 2026.xlsx`（真实客户资产负债表，56 行 × 7 列，7,737 字符生产 HTML，144 条入库 cell / 48 行，**22 条人工修正**，父链最深 4 层 / 最长 119 字符）：

| 指标 | 结果 |
|---|---|
| **代码算的父链覆盖生产入库全路径** | **24/24 = 100%** |
| **表体 token**：生产 HTML 3,553 → Markdown 1,985 | **−44.1%** |

- 「仅代码有」的 31 条全是 header / 聚合行（`ASSETS` / `Total Current Assets` / `Total Bank Accounts` …）—— 本就该被 §3.4 业务过滤跳掉，不算分歧
- **−44.1% 远高于 demo fixture 的 −24.8%**，印证「真实表更宽更稀疏 → Markdown 降幅更大」；早前在 24 月 P&L（56×27）上测到的 −56% 是宽表代表值
- 4 层深父链全靠 col-0 前导空格，代码单调递减走链一次走对

**顺带在真实数据里发现的父链损坏（支持本设计的论点）**：

| 现象 | 实测 |
|---|---|
| **首字符被吃** | 13 条入库父链形如 `'xpenses \|\| 100 Payroll \|\| 5100-01 Payroll - Labor'` —— `Expenses`→`xpenses`、`5100`→`100`、`6150`→`150`。全部来自同一个 **PDF**（`FreightTrain LLC Financials - May 2026.pdf`），正是 `pdfutil/text_tables.py` 头注释点名的 `find_tables` 失败模式（原文：「会**吃掉每行首字符**（`6145`→`145`、`Expenses`→`xpenses`）」）。父链字面被损坏 → §6.5 / §6.3 的反推锁定直接失效，且**静默** |
| 「末段=前一段」 | 全库 7,931 条入库 cell 中 36 条（0.5%）。查证后**是合法形态**，见 §八 L8 —— 差点误判成 bug |

> 前者是 PDF / OCR 轨的问题（本设计 D5 不覆盖 vision 轨），但它是「父链损坏静默污染 lg_category」这一风险的**真实存在证据**；Excel 轨代码算 join 拿的是网格 cell 完整文本，不可能出现这类字符级损坏。

### 9.7 出参去掉数值 `v`（→ D12）

**起点**：§9.5 已把 `mon`/`ut`/`cur` 收干，剩下 `cells` 里只有 `col` + `v`，而它仍是 O(行×列)。而**值本来就在入参表里** —— LLM 只是在抄。§4.6.4 的 `v` 五条规则（去千分位 / 括号=负 / 去货币符 / 去百分号 / 空值→null）全是**确定性字符串变换**，代码能做。

**契约**：出参加表级 `cols`（cn → 入参物理列号），行级加 `contra`；`cells` 整个删掉。

```
{ "mon_set": [...], "cols": [1,2,3],          // c4 是 Total 列 → 不进 cols
  "data": { "<lg>": [ {"r":12, "pf":false, "cf":false, "contra":false,
                       "ut":"CURRENCY", "cur":"USD"} ] } }
```

LLM 的职责收敛成一句：**决定哪些 `r` emit、每行归哪个 `lg_category`、pf/cf/contra、行级 ut/cur、以及哪些物理列是期间列**。一个数字都不输出。

#### 实测：12 个真实 Excel 文件（`ocr_test_file` 目录）

**值定位交叉校验** —— 同表跑两种契约，对同一 `(r, cn)` 比对「代码重建值」vs「LLM 转录值」：

| 表 | 规模 | 比对 | 结果 |
|---|---|---|---|
| **Bevz Historical P&L (2021-2022)** | 60 行 × 27 列 | **912/912** | ✅ 零错位 |
| `OCR测试数据.xlsx` | 88 行 × 1 列 | 88/88 | ✅ |
| `GRP3_DataQuality` OCR_Noise | 13 行 × 4 列 | 52/52 | ✅ |
| `D09_ExcelFeatures.xlsx` | 3 行 × 13 列 | 24/24 | ✅ |

**收益随表宽陡增**（窄表的 ±2% 是运行噪声）：

| 表 | completion | 墙钟 |
|---|---|---|
| **Bevz P&L 60×27** | 26,622 → 4,547 = **−82.9%** | 244.0s → 47.5s = **−80.5%** |
| D09 3×13 | 561 → 212 = −62.2% | 9.4s → 5.5s = −42.0% |
| GRP3 13×4 | 2,140 → 1,826 = −14.7% | +2.5% |
| OCR测试 88×1 | 8,136 → 7,961 = −2.2% | +1.9% |

**比 token 更硬的一条证据**：`max_tokens=16000` 时，Bevz P&L 在**旧契约下 165 秒后 JSON 解析失败**（27 列输出被截断）；novalue 契约 31 秒正常返回。提到 32,000 旧契约才跑通，用掉 26,622 output token / 244 秒。→ **宽表在旧契约下会撞输出上限而失败，新契约不会。** 生产的 `_EXTRACTION_CELL_BUDGET=500` 切片本质就在绕这个，本改动让切片压力大幅下降。

#### 为什么「值放错行列」这个风险反而消失

提示词把「逻辑列锚定」标为 *html 最高频错因*，§4.4/§4.5 用大段反例在打它。**LLM 不再转录数字之后，根本不存在转录错位** —— 代码按 `(r, 物理列)` 一个坐标查表。可错的只剩两个小而可校验的面：表级 `cols` 数组（一表一个）和 `r` 集合。

#### 数据丢失探针（新增，建议搬进生产）

分两类，都是**告警不是错误**：

| 探针 | 含义 | 12 文件实测 |
|---|---|---|
| **列外数值** | 行在 emit 集合内，但某个有值的列不在 `cols` 里 | 仅 1 个文件命中 2 处，**经查证属合法丢弃**（见下） |
| **整行跳过** | 整行有数值但未 emit | 全部合法：`Total Income` / `TOTAL ASSETS` / `Total Revenue` 等聚合行 |

⚠️ **「列外数值」不能当错误判据**（初版误标成"真问题"，已纠正）。命中有两种成因，探针分不出来：① `cols` 真漏了期间列；② 该 cell 本身是合计/比率（§3.3 汇总列、§3.4 比率行本该丢）。

实测那 2 处经查证是 ②：`Bevz P&L` 的 c25/c26 是报表作者手工加的稀疏「合计 + 比率」列 —— r12 c25=`120704.22`（Amazon Services 的 24 月合计）、r25 c25=`44893.2`、r11 c25=`2.187…`、r24 c25=`0.578…`、r25 c26=`USD0.3719…`。**c25/c26 确实渲染进了入参 markdown（表头 `…|c24|c25|c26|`），LLM 看得见并正确排除了它们**，`cols=[1..24]` 与 24 个月的 `mon_set` 一致。

> 也就是说：这类丢弃**在旧契约下同样发生**（LLM 的 `cn` 编号同样只到 24），novalue 没有引入新的丢失，只是**让它变得可检测**。

#### 顺手发现的两个真实问题（与 §十二 `.xls` 那条线相关）

| # | 发现 |
|---|---|
| 1 | **`GRP3_DataQuality.xls` 其实是 xlsx 改名** —— magic bytes 是 `50 4B 03 04`（zip）。生产 `_load_sheet_dataframes` 按**扩展名**分派 → 这类文件会以 `"sheet read failed"` 失败。**印证了 §十二 `.xls` 那条线里提的「改名文件」场景，现在有实例。** 建议改 magic-byte 嗅探分派 |
| 2 | **openpyxl 按扩展名硬拒 `.xls`**（即使内容是 zip，`_validate_archive` 直接抛 `InvalidFileException`）→ 必须传文件对象（`BytesIO`）绕过 |

### 9.8 ⚠️ token 口径修正（影响本文其它处的估算）

**tiktoken 显著低估中文文本。** demo 提示词 tiktoken 数 4,920，而 API 回报的真实 prompt 约 7,000（表体只 100~290 token）→ **中文提示词 Claude 分词器高约 40%**。

推论：本文 §一 / §七 引用的「生产 `data_values.html.v2.md` = 14,670 token」是 tiktoken 数，**真实可能 20k+**。表体那侧主要是 ASCII 标记与数字，故先前测得的 Markdown 降幅**比例**仍可信，但所有绝对值都是低估。后续做 token 预算时以 **API 回报值**为准。

### 9.9 `.xls` 侧确认（供 §十二 那条平行线用）

| # | 事实 |
|---|---|
| 1 | `xlrd.open_workbook(..., formatting_info=True)` **必须传**：不传则 `merged_cells` 恒空、`cell_xf_index()` 直接抛 `XLRDError`。生产 `excel_preprocess_node.py:258` 没传 |
| 2 | `merged_cells` 是 `(rlo, rhi, clo, chi)`，**hi 为开区间** |
| 3 | 原生缩进在 `xf_list[...].alignment.indent_level`、格式串在 `format_map[xf.format_key].format_str` —— **`_extract_currency_prefix` / `_extract_date_display` 可零改动复用** |
| 4 | **公式对 `.xls` 永久拿不到**（cell type 无 FORMULA，只读缓存值）→ `f="1"` 与 `_check_formula_cache_health` 均不适用；要救只能 LibreOffice 转 `.xlsx` |

### 9.10 demo 与生产的差异（别照抄数字）

- 提示词是**为 demo 浓缩**的（tiktoken 4,920 vs 生产 14,670），§3 词袋精简、去掉大量反例与 checksum 冗余 → **绝对准确率不能外推到生产**，它验的是方向可行性
- fixture 都很小（≤14 行），不含 chunk 切片、多表切分、>2000 行超大 sheet
- `detect_label_col` 假定整张 sheet 布局一致
- UNIDENTIFIED 行的 join 用「沿用上一行」这个简化规则（= §八 L1 的待定项，demo 里可行但未穷举）

## 十、测试策略

| 层次 | 内容 |
|---|---|
| 单测 | `_resolve_account_joins` 纯函数：3 空格/级、1 空格/级、不等宽（`0/3/5/8`）、tab 缩进、NBSP 混用、原生 indent、双列分类法、label-merge、QB-style 自带数据父行、UNIDENTIFIED 行、scaffolding 边界、聚合行夹在中间（§4.2 场景）、多表 sheet |
| 单测 | 渲染 `r` id 稳定性：整表渲染与切 chunk 后渲染的同一行 `r` 必须一致 |
| 单测 | **祖先可达性断言**（§四.5 / §八 L7）：每行每个祖先名都能在上方找到层级更浅的行。四种破坏形态各一例：双列分类法拍平、多表 `row_range` 切分、chunk 边界、QB-style 自带数据父行 |
| 单测 | **QB 同名父子必须保留**（§八 L8）：源表 `Accounts Receivable`(6 空格) + `Accounts Receivable`(9 空格) → 全路径末段重复是**正确**的，不得被"修掉" |
| 单测 | **注入的是父链不是全路径**（§5.6）：给 `_explode_nested_extraction` 传父链后，`full_join` 拼出的结果末段**只出现一次** |
| 单测 | 出参新契约（D9/D10）：`mon` 由 `col` 查 `mon_set` 回填；`ut`/`cur` 取「cell 覆盖 ?? 行级默认」；**覆盖卫生** —— cell 写了与行级默认相同的值应告警 |
| 单测 | **值重建**（D12）：五条变换逐条（千分位 / 括号负 / 货币符 / 百分号 / 空值）；`contra=true` → 全行取 `-abs()`；`cols` 越界 / 长度与 `mon_set` 不等时的行为 |
| **交叉校验回归（强烈建议常设）** | 同表跑「代码重建值」vs「LLM 逐 cell 转录值」，比对同 `(r, cn)`。这是**唯一能证明值没放错行列**的手段，demo 在 4 张真实表上跑出 912/912、88/88、52/52、24/24（§9.7）。上线前至少对宽表跑一轮 |
| 回归 | 现有 `tests/ai/nodes/test_repair_account_label_join.py`（已存在，正是这块的现有覆盖）、`test_excel_currency_prefix.py`、`test_excel_date_display.py` |
| 真调 LLM 验证 | 现成评测台 `tests/ai/nodes/test_prompt_data_values.py --input X.xlsx --all-sheets`（真调 LLM、结果落 `results/*.md` + `.cells.json`）。阶段 A 的**分歧率**可直接从此处取样 |
| **真实用例回归（推荐）** | demo 的 `fetch_real.py` / `run_real.py` 路子可沉淀成常设回归：从库里按 `mapping_data` 取真实 `sheet_html` + 入库结果，**离线**比对代码算的父链覆盖率（零 LLM 成本）。已跑通用例见 §9.6 |

## 十一、分期

| 阶段 | 内容 | 可独立上线 |
|---|---|---|
| **P1 输入缺口** | G1 `alignment.indent` + G2 tab；不改任何算法归属 | ✅ 是。纯修复现有缺口，LLM 仍算 join，风险最低 |
| **P2 稳定 row id** | 渲染发 `r`、提示词改 `row` 语义（`data_values.html.v3.md` 阶段 A）；join 仍由 LLM 产出 | ✅ 是。为 P3 铺路，本身也修掉 `rn` 自编的不确定性 |
| **P3 代码算 join（并行）** | `_resolve_account_joins` + `_explode_nested_extraction` opt-in 注入，**以代码为准 + 记录分歧率** | ✅ 是。可随时关掉（不传 join map 即回退） |
| **P4 提示词瘦身** | 分歧率数据支撑后删 §4.6.3 / §5.2 / 第 2 层 nested key / `label` 字段；`CHUNK_ROW_STRIDE` 退役 | 需 P3 数据支撑 |
| **P5 出参瘦身一期（D9/D10）** | `mon` 提表级 `mon_set`、`ut`/`cur` 改行级默认+cell 覆盖（照 `data_values.vision.v3.md`） | ✅ 是，**与 P1~P4 正交** —— 不依赖父链外置，可独立先做。demo 实测 completion −31%、墙钟 −22%（§9.5） |
| **P6 出参瘦身二期（D12）** | 删 `cells`、加表级 `cols` + 行级 `contra`，**值由代码按 `(r, cols)` 重建** | ✅ 是。依赖 P2 的稳定 `r`（要按 `r` 定位行），不依赖 P3 的父链外置。**收益最大**：宽表 completion −82.9% / 墙钟 −80.5%（§9.7），且宽表在旧契约下会撞输出上限失败 |

**回滚**：P3 之前每阶段均可独立回滚；P3 的开关就是「调用方是否传 `join_by_row`」，无需改代码结构。P4 一旦删了提示词章节，回滚需切回 v2 提示词文件（版本化目录天然支持）。

## 十二、不在本设计范围内

以下三条是**可独立决策**的平行改造线，与本设计无依赖（除标注处）：

| 线 | 内容 | 与本设计的关系 |
|---|------|----------------|
| **渲染格式** | HTML `<td>` → Markdown `|`（demo 合成 fixture −24.8%、**真实宽表 −44.1%**、24 月 P&L −56%；需处理前导空格歧义、空 cell 占位、合并 materialize、colspan 填充） | 独立。若两条都做，本设计的 `r` id 与 join 计算不受渲染格式影响。**注意 D7 的 `parent_chain` 列本身是 Markdown 形态下的产物** —— 若保留 HTML 渲染，父链应作 `<td>` 属性或独立列，分隔符冲突问题不存在 |
| **`lv` 层级列** | 表内加显式层级整数列 | **已并入本设计**（原判「被取代」有误）：代码算 join 之后 LLM 仍需读祖先名（§四.5），`lv` 正是最省的那种「祖先可达」编码 —— demo 实测 A 方案即 `lv` + 可达性断言（§9.3）。它不是给代码用的中间产物，是给 LLM 用的层级信号 |
| **`.xls` 支持** | `xlrd` 依赖缺失导致 `.xls` 100% 失败（Java `AiFinancialExtractionServiceImpl.java:860` 明确收 `.xls`）；候选方案含 LibreOffice 转 `.xlsx` 后复用 xlsx 轨 | 弱依赖：若 `.xls` 要走本设计，其缩进/合并信号须先齐（G3）。转 `.xlsx` 方案可让 `.xls` 自动继承本设计全部收益 |

## 十三、待拍板

1. **P4 的删除范围**：第 2 层 nested key 是否真删（输出 token 收益 vs 契约变更面）——建议等 P3 分歧率数据。demo 侧已跑通「输出只有一层 `{lg_category: [rows]}` 且不含 `label`」，可行性无问题。
2. **`r` id 的编码**：源行号直用，还是「表内序号」？涉及多表 sheet 下 `row_position` 的单调性（§5.4）。
3. **有效缩进合成定标**（§四.4）：原生 indent 1 单位折几个字符——需一个含原生缩进的真实文件实测。**仓库样本语料没有这类文件**（9 个 sheet 实测 `alignment.indent` 全 0），demo 用「1 单位 = 3 字符」跑通，但仍需真实文件校准。
4. **§5.5 的替代校验取哪几条**：`r` 合法性（必做）之外，cell 值交叉核对是否上线、告警阈值怎么定。这条随 D8 而来，不做就意味着**行错位完全不可检出**。
5. **P5 是否先于 P1~P4 上线**：它与父链外置正交、收益已实测（completion −31% / 墙钟 −22%）、改动面只在出参 schema + `_explode_nested_extraction`，**风险明显低于 P3**。若想先拿一个确定收益，建议 P5 走在前面。
6. **P6 的两个探针上不上线、阈值怎么定**（§9.7）：「列外数值」会被合计/比率列合法命中（实测 `Bevz P&L` 的 c25/c26），故只能做 warning。要不要按「命中数 / emit 行数」定个比例阈值再报？
7. **`xpenses` 那批损坏数据要不要订正**（§9.6）：13 条入库父链首字符被吃，全来自一个 PDF。属 PDF/OCR 轨问题、不在本设计范围，但已入库的脏数据是否重跑、以及**是否该加一条入库前的父链合理性告警**（如首段不在本表任何 col-0 文本中出现）需要拍。

> 已消解的原待拍板项：**输出是否保留 `label`** → D8 决定去掉（原建议保留作 checksum，已被推翻；替代校验见 §5.5）。**层级表达 A 还是 B** → D7 决定取 B' （`parent_chain` + ` > `）。
>
> ⚠️ 仍需记住的一条边界：`account_label_join` **按定义不含当前行自身**（§4.6.3 + §5.2「末尾段不能等于本行 label」），所以**入参里的 `account` 列绝不能因为有了 `parent_chain` 就删** —— 两者信息不重叠，且 `account` 是 §3.2 词袋匹配、§6.1 Revenue Contra 触发、§4.6.1 比率行判定的主输入。
