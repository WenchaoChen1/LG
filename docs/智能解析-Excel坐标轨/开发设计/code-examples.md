# Excel 坐标提取轨 · 参考代码

> 关联文档：
> - 本阶段开发设计：[dev-design-doc](./dev-design-doc.md) —— 决策与理由在那里，本文只放代码
> - 上游功能设计：[design-doc](../设计/design-doc.md)

本文是 [dev-design-doc](./dev-design-doc.md) 各节引用的代码骨架。**不是可直接粘贴的成品**
——省略了日志、类型注解细节与错误分支，落地时按仓库规范补全。

本轨**没有 DDL**：D5 定的是坐标不落库、`ai_financial_extraction_mapping_data` 表结构
零改动。

---

## 1. 一次 LLM 调用（dev-design-doc §8.1）

```python
from common.enums import CallerAgent, CallerNode
from common.llm_concurrency import llm_units_gate
from llm import TraceContext, llm_db_router
from llm.infrastructure.constants import (
    AI_CLASSIFICATION_MAX_TOKENS,
    AI_REQUEST_MAX_RETRIES,
    AI_REQUEST_TIMEOUT_SECONDS,
)
from llm.infrastructure.response_parser import parse_json_response


# ⚠️ 模型 / reasoning 档位的读取函数**在本包自己定义**，不从
# ai.agent.financial_extract_graph.nodes.shared 跨包 import —— 那是另一个 agent 子包的
# 节点文件，跨包引用违反 ai/CLAUDE.md §三 的隔离约定，而且 D1 会让旧轨整体下线。
# env 名沿用（OCR_EXTRACT_MODEL / OCR_EXTRACT_REASONING），部署侧零变更。
# 依赖分类见 dev-design-doc §2.2。

_REASONING_LEVELS = frozenset({"none", "minimal", "low", "medium", "high", "xhigh", "max"})


def _model() -> str | None:
    """未配置返回 None，让 kernel 落到 provider 默认模型。"""
    return get_optional("OCR_EXTRACT_MODEL") or get_optional("OCR_IDENTIFY_MODEL")


def _reasoning_kwargs() -> dict:
    """未配置 / 配错 → 返回 {} 不发该参数，行为与存量部署一致。"""
    effort = (get_optional("OCR_EXTRACT_REASONING") or "").strip().lower()
    if not effort:
        return {}
    if effort not in _REASONING_LEVELS:
        logger.warning("OCR_EXTRACT_REASONING=%r 不在白名单，忽略", effort)
        return {}
    return {"extra_kwargs": {"extra_body": {"reasoning": {"effort": effort}}}}


def _call_kwargs(call_purpose: str) -> dict:
    """三步共用的调用参数。

    与旧轨的差别只有两处，都别抄错：
      - **不传 cache_system**（旧轨是 True）：D4 定缓存先不开，保 sheet 级并行的墙钟。
      - max_tokens 用**分类档** 10240 而不是抽取档 98496：新轨输出是 O(rows+cols)，
        实测定位步 143 ~ 1291 tok；抽取档那个数是为旧轨逐 cell 输出准备的。
    """
    return {
        "provider": "openrouter",
        "model": _model(),
        "max_tokens": AI_CLASSIFICATION_MAX_TOKENS,
        "timeout": AI_REQUEST_TIMEOUT_SECONDS,
        "max_retries": AI_REQUEST_MAX_RETRIES,
        "json_mode": True,
        "call_purpose": call_purpose,
        **_reasoning_kwargs(),
    }


def _trace(node: CallerNode, ctx: dict) -> TraceContext:
    """ContextVar 透传只带 span 栈，file_id / company_id 这些审计字段必须显式传。"""
    return TraceContext(
        agent=CallerAgent.FINANCIAL_EXTRACT,
        node=node,
        company_id=ctx.get("company_id"),
        user_id=ctx.get("created_by"),
        task_id=ctx.get("task_id"),
        file_id=ctx.get("file_id"),
        created_by=ctx.get("created_by"),
    )


def ask_json(messages: list[dict], *, node: CallerNode, purpose: str, ctx: dict) -> dict | None:
    """发一次调用并解析 JSON。

    ``with llm_units_gate`` 是必须的：本轨不走 ``parallel_llm_invoke_units``（那个模板
    内部已经包了），自己起线程池就得自己包，否则绕过提取轨的总并发闸门。
    """
    with llm_units_gate:
        result = llm_db_router.complete(messages, trace=_trace(node, ctx), **_call_kwargs(purpose))

    if result.finish_reason == "length":
        # 不用 json_repair 抢救前缀：半个 tables[] 坐标不全但外观合法，比没有更危险。
        return None
    # 禁止业务侧自己 json.loads —— parse_json_response 内含 json_repair L2 兜底。
    return parse_json_response(result.content)
```

---

## 2. FATAL 重问一次（dev-design-doc §8.2）

```python
def locate_sheet(view, overview: str, ctx: dict) -> tuple[dict | None, VerifyResult]:
    """步 1 + 步 2：定位并回读校验，FATAL 则带证据重问一次。

    重问逻辑放在本步自己的文件里，不放 pipeline —— 提示词与解析都是这一步的事，
    主编排只该看到"成了还是没成"。
    """
    messages = _build_messages(view, overview)
    answer = ask_json(messages, node=CallerNode.EXCEL_EXTRACT_LOCATE,
                      purpose="excel_locate", ctx=ctx)
    if answer is None:
        return None, VerifyResult()

    res = verify_locate(view, answer)
    if res.ok:
        return answer, res
    # 下面重问一次；重问后仍 FATAL 的**按表丢弃**（见文末 drop_fatal_tables），
    # 不整个 sheet 报废 —— 坏表的数据该丢，同 sheet 好表没理由跟着丢。

    # evidence() 只列 FATAL，不含 WARN 噪声 —— 把统计类告警塞给模型会让它改对的东西。
    retry = messages + [{
        "role": "user",
        "content": "上一次回答的坐标与源文件不符，逐条修正后重新输出完整 JSON：\n"
                   + res.evidence(),
    }]
    answer2 = ask_json(retry, node=CallerNode.EXCEL_EXTRACT_LOCATE,
                       purpose="excel_locate_retry", ctx=ctx)
    if answer2 is None:
        return None, res
    return answer2, verify_locate(view, answer2)


def drop_fatal_tables(answer: dict, res: VerifyResult) -> dict:
    """把仍带 FATAL 的表从 answer["tables"] 里剔掉，保留通过校验的表。

    依赖 Issue.detail 携带表序号（dev-design-doc §7.1）—— 没有它就只能整 sheet 报废。
    """
    bad = {i.table_index for i in res.fatal if i.table_index is not None}
    if not bad:
        return answer
    kept = [t for k, t in enumerate(answer.get("tables") or []) if k not in bad]
    logger.warning("excel_extract: dropped %d table(s) with FATAL, kept %d",
                   len(bad), len(kept))
    return {**answer, "tables": kept}


# ── pipeline.py 侧的失败传播（dev-design-doc §10.4）──────────────────────────
class SheetExtractFailed(Exception):
    """本包自定义：一个 sheet 的某个 LLM 步彻底失败。

    **必须抛，不能"静默产出 0 张表正常返回"** —— 后者会让 _run_sheets 的 except 计不到
    这次失败，于是 n_extract_failures 恒小于 n_extract_units，refine_extraction 的判据③
    永远算不出"全失败"，整个文件会被当成业务软失败（REVIEW_READY）而不是技术失败
    （FILE_FAILED）。
    """


def extract_sheet(view: SheetView, ctx: dict) -> list[TableInfo]:
    """单 sheet 的三步流水线 —— 按顺序平铺，读这个函数即懂全流程。"""
    answer, res = locate_sheet(view, ctx["overview"], ctx)
    if answer is None:
        raise SheetExtractFailed(f"locate failed: sheet={view.name}")
    answer = drop_fatal_tables(answer, res)
    if not answer.get("tables"):
        raise SheetExtractFailed(f"all tables FATAL: sheet={view.name}")
    if not answer.get("is_financial"):
        return []                      # 业务软失败：不是财报，不抛异常、不产表

    rows = resolve_semantics(view, answer, ctx)      # 步 3 + 4
    if rows is None:
        raise SheetExtractFailed(f"semantics failed: sheet={view.name}")
    rules = resolve_currency(view, answer, ctx)      # 步 6（失败可降级默认规则，不抛）
    return build_tables(view, answer, rows, rules)   # 步 5 + 7，纯程序
```

---

## 3. 有效缩进与样式指纹（dev-design-doc §6.2 / §6.3）

```python
# ── 以下三个 helper 的口径复制自旧轨 excel_preprocess_node.py:286-347。
#    刻意复制而不 import：它们是私有函数、住在 2800 行的旧节点里，而新轨是直接替换、
#    旧轨迟早删（同 design-doc §14 对 _load_sheet_dataframes 的判断）。

_INVISIBLE_BG = frozenset({"FFFFFF", "t0", "i64", "i65"})

_INDENT_LEVEL_CHARS = 3
"""Excel「增加缩进」一级约等于 3 个字符宽 —— 旧轨注释记的经验值。

两种缩进机制实践上互斥（用空格的文件 alignment.indent 恒 0，反之亦然），所以相加安全；
这个常数只在两处语料都从未观测到的混用场景才起作用，且那种场景下它只影响"深多少"、
不影响"谁比谁深"，而父链要的正是后者。
"""


def effective_indent(raw_value, alignment) -> int:
    """有效缩进 = 前导空白字符数 + alignment.indent × 3。

    **必须在 _cell_text 的 strip() 之前算** —— 视图文本要保持干净，缩进走 ind 属性。
    """
    n = 0
    if isinstance(raw_value, str):
        n = len(raw_value) - len(raw_value.lstrip())
    level = getattr(alignment, "indent", 0) or 0
    if isinstance(level, (int, float)):
        n += int(level) * _INDENT_LEVEL_CHARS
    return n


def color_id(color) -> str | None:
    """RGB → "F5F5F5"；主题色 → "t1+0.20"；索引色 → "i5"。

    ⚠️ **不能只认 .rgb**：openpyxl 对主题色 / 索引色的 .rgb 返回的是描述符错误对象
    （RGB 实例，不是 str），只做 isinstance(str) 守卫会把它们一律吞成 None —— 与
    "没填充"分不开。而 **Excel 界面的填充色选择器默认给的就是主题色**，那等于在按标准
    UI 排版的工作簿上整个 bg 信号都收不到，而 bg 正是父链步的主要信号之一。
    只需要"能区分"、不需要真实色值，所以主题 / 索引色按编号编码即可。
    """
    if color is None:
        return None
    v = getattr(color, "rgb", None)
    if isinstance(v, str):
        return v[2:] if len(v) == 8 else v  # 8 位是 ARGB，alpha 对层级判断无意义
    theme = getattr(color, "theme", None)
    if isinstance(theme, int):
        tint = getattr(color, "tint", 0.0)
        tint = tint if isinstance(tint, (int, float)) else 0.0
        return f"t{theme}" if not tint else f"t{theme}{tint:+.2f}"
    indexed = getattr(color, "indexed", None)
    if isinstance(indexed, int):
        return f"i{indexed}"
    return None


def size_id(size):
    """字号：整数发整数（11），半磅保留（10.5）。

    ⚠️ **先 round 再判整**。反过来的话 12.005 走 else 分支出 "12.0"、而 12 出 "12"，
    同一个视觉字号两种编码 —— 与排除字体颜色的理由同类的伪差异。
    """
    if not size:
        return None
    f = round(float(size), 1)
    return int(f) if f.is_integer() else f


def style_fp(cell) -> StyleFp:
    """(bg, b, i, sz) 四元组。刻意**不含**字体颜色与边框 —— 旧轨实测均为噪声，
    理由见 design-doc §6.2。也**不做** _normalize_fingerprint：那是旧轨"只发有差异的
    属性"的差分机制需要的，D3 定的是发全量、没有被省略的行。
    """
    fill, font = cell.fill, cell.font
    bg = color_id(fill.fgColor) if (fill is not None and fill.patternType) else None
    return (
        None if bg in _INVISIBLE_BG else bg,
        bool(font and font.bold),
        bool(font and font.italic),
        size_id(font.size) if font else None,
    )
```

---

## 4. `.csv` 支路（dev-design-doc §6.5）

```python
_CSV_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "gb18030")
"""与 s3util.validation.validate_csv 的梯子逐项一致。

⚠️ 这一致性是**必须**的，不是巧合：旧轨校验期试三种编码、真正读的时候却是
``pd.read_csv(path, header=None)`` 不传 encoding（excel_preprocess_node.py:753），
于是一个 gb18030 的 CSV 能过上传校验、然后在提取时炸。新轨不继承这个 bug。

那个常量在 s3util 里是模块私有（_ 前缀、不在 __all__），按"不 import 旧轨私有名"的
同一理由在本包自定义一份。
"""


def _load_csv_view(local_path: Path) -> SheetView:
    """CSV 合成单 sheet 的坐标视图。

    csv 没有合并 / 公式 / 样式，但**前导空格是真实存在的**，所以 indents 照算。
    sheet 名用文件 stem，对齐旧轨 _load_sheet_dataframes 的 ``local_path.stem or "Sheet1"``。
    """
    rows = None
    for encoding in _CSV_ENCODINGS:
        try:
            with local_path.open("r", encoding=encoding, newline="") as fp:
                rows = list(csv.reader(fp))
            break
        except UnicodeDecodeError:
            continue
    if rows is None:
        raise ValueError(f"csv: not decodable as text (tried {', '.join(_CSV_ENCODINGS)})")

    cells: dict[tuple[int, int], str] = {}
    indents: dict[tuple[int, int], int] = {}
    for r, row in enumerate(rows, start=1):          # 1-based，与 xlsx 口径一致
        for c, raw in enumerate(row, start=1):
            text = _cell_text(raw)
            if not text:
                continue
            cells[(r, c)] = text
            ind = len(raw) - len(raw.lstrip())
            if ind:
                indents[(r, c)] = ind
    return SheetView(
        index=0,
        name=local_path.stem or "Sheet1",
        cells=cells,
        indents=indents,
        # merges / formula_cells / formula_empty / error_cells / styles 全取默认空值
    )
```

---

## 5. sheet 级并发（dev-design-doc §10）

```python
_SHEET_MAX_WORKERS = 4
"""5 文件 × 4 sheet = 20 对闸门 10 维持 2× 超订，与旧轨 5×4:10 同比值。

超过闸门的并发**不增加吞吐**（吞吐上限就是闸门 10），只增加排队方差；取 2× 而非 1×
是因为流水线有相当部分时间待在程序步（渲染、校验、按坐标取值）、那时不占闸门。
不加 env —— D1 的口径是不加开关。
"""


def _run_sheets(views: list[SheetView], ctx: dict) -> tuple[list[TableInfo], int, int]:
    """每个 sheet 一条 3 步流水线，最多 4 路并发。

    刻意**不用** parallel_llm_invoke_units：那个模板是"一批 unit 各发一次调用"，
    而本轨每个 sheet 是一条串行流水线，形状不同。
    """
    n_workers = min(_SHEET_MAX_WORKERS, len(views))
    tables: list[TableInfo] = []
    n_units = n_failures = 0

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        # 每个 sheet 各拷一份 context：同一个 Context 对象并发 run 会抛 RuntimeError。
        # 这份透传让 worker 内看到提交方的 span 栈，trace_span_id 才挂得上。
        futs = {
            pool.submit(contextvars.copy_context().run, extract_sheet, v, ctx): v
            for v in views
        }
        for fut in as_completed(futs):
            view = futs[fut]
            # ⚠️ 本轨的 unit = **一个 sheet**，不是旧轨的"一次 LLM 调用"
            # （shared.py:938-958 那个 docstring 说的是调用数）。理由见
            # dev-design-doc §10.5：判据③要回答"这个文件是不是彻底废了"，
            # sheet 粒度才对应这个语义。改这行前先读那一节。
            n_units += 1
            try:
                tables.extend(fut.result())
            except Exception:
                # sheet 级**不抛**：一个 sheet 读不出来不该让整个文件 SQS 重投。
                # （文件级的 parallel_files_node 相反 —— 它收齐后原样抛，保留 resume 语义。）
                n_failures += 1
                logger.exception("excel_extract: sheet=%s failed", view.name)
    return tables, n_units, n_failures
```

---

## 6. 节点返回的三条路径（dev-design-doc §3.2 / §3.4）

```python
def excel_extract_node(state: MainGraphState) -> ExcelPreprocessReturn:
    local_path = Path(state["local_path"])

    # ── 路径 A：技术失败 —— 只填 error_message，文案逐字沿用旧轨（前端可能已在展示）
    try:
        views = load_sheet_views(local_path)
    except Exception as exc:
        logger.exception("excel_extract: file_id=%s sheet read failed", state["file_id"])
        return ExcelPreprocessReturn(
            error_message=f"sheet read failed: {type(exc).__name__}: {exc}",
        )

    sheets = [
        ExcelSheetInfo(
            sheet_index=v.index,
            sheet_name=v.name,
            sheet_html=render_view(v),        # 就是发给模型的那份视图，语义诚实、便于排查
            row_count=len(v.rows),
            column_count=len(v.cols),
        )
        for v in views
    ]
    tables, n_units, n_failures = _run_sheets(views, _ctx_of(state))

    # ── 路径 B：业务软失败（no_tables）—— tables 空 + **绝不写 error_message**。
    #    写了会被 save_to_db 判 FILE_FAILED，这是最容易犯的错。
    # ── 路径 C：正常完成。
    #    统计字段必须诚实填 —— refine_extraction 的错误升级短路链完全依赖它们。
    #    skipped_table_ids 恒空 list（新轨无列切片），是"填空列表"不是"不填"。
    return ExcelPreprocessReturn(
        sheets=sheets,
        tables=tables,
        n_extract_units=n_units,
        n_extract_failures=n_failures,
        skipped_table_ids=[],
        truncated_table_ids=[],
    )
```

---

## 7. D7 三条验伪的两个算法（dev-design-doc §7.2）

整个仓库没有这两段的先例，所以给出骨架。

```python
def table_spans(tables: list[dict]) -> list[tuple[int, int, int]]:
    """派生每张表的行跨度，返回按起行排序的 ``[(top, bottom, table_index), ...]``。

    D7 刻意把 row_range 从 LLM 输出里删掉了（少一个模型能与自己矛盾的字段），
    所以跨度由 header_row 与 label_range 派生。

    ⚠️ **必须排序**：tables[] 的顺序来自模型输出，没有任何东西保证它按行序排列，
    而检查 2（相邻两表的分隔证据）依赖"相邻"这个概念。
    """
    spans = []
    for k, t in enumerate(tables):
        (top, _), (bottom, _) = parse_range(t["label_range"])
        header = int(t["header_row"])
        spans.append((min(header, top), bottom, k))
    return sorted(spans)


def uncovered_runs(view: SheetView, tables: list[dict]) -> list[tuple[int, int]]:
    """条目列里有文本、但不落在任何表 label_range 内的**连续行段**。

    这是 D7 检查 3 的核心。为什么要按"连续段"而不是按"总行数"判：漏掉一整张表会露出
    一段**连续**的未覆盖行（那才是真问题），而脚注 / 说明行是零散的一两行（源文件本身
    的噪声，一刀切会挡住好文件）。段长阈值 5 沿用既有口径。
    """
    covered: set[int] = set()
    label_cols: set[int] = set()
    for t in tables:
        (top, left), (bottom, _) = parse_range(t["label_range"])
        covered.update(range(top, bottom + 1))
        label_cols.add(left)

    # 条目列里"有文本"的行 —— 先解合并 anchor，否则段落标签管辖的行会被误判成空
    text_rows = sorted(
        r for r in view.rows
        for c in label_cols
        if (v := view.cells.get(view.merges.anchor_of(r, c))) and not _is_number_text(v)
    )

    runs: list[tuple[int, int]] = []
    start = prev = None
    for r in text_rows:
        if r in covered:
            continue
        if start is None:
            start = prev = r
        elif r == prev + 1:
            prev = r
        else:
            runs.append((start, prev))
            start = prev = r
    if start is not None:
        runs.append((start, prev))
    return runs
```

判级：`uncovered_runs` 里任一段长度 ≥ `_UNCOVERED_RUN_FATAL`（5）→ FATAL（漏了一整张
表，或某表 `label_range` 提前截断）；否则 WARN。

`table_spans` 若派生出**重叠**的 span，直接判 FATAL——那本身就是"边界切错"的证据，
不需要额外规则。
