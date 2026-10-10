# 手动上传时声明 Actuals / Proforma · 参考代码

> 关联文档：
> - 本阶段开发设计：[dev-design-doc](./dev-design-doc.md)（总览）· [dev-python](./dev-python.md) · [dev-java](./dev-java.md) · [dev-frontend](./dev-frontend.md)——决策与理由在那里，本文只放代码
> - 上游功能设计：[design-doc](../设计/design-doc.md)

本文是三份分端开发设计各节引用的代码骨架，**不是可直接粘贴的成品**：省略了部分日志、import 与错误分支，
落地时按各子项目规范补全；行号以各节注明的提交为准，开发时可能已漂移。

唯一的 DDL 是 Python 迁移 V030（只改列注释，见 P1），Java 侧没有 DDL。

## Python

> 对应 [dev-python](./dev-python.md)。行号基于 CIOaas-python `sprint121`（`70ca1e6a`）。

### P1. 迁移 `sql/migrations/business/V030__sprint121_ai_file_registry_business_type_extract_fi.sql`
```sql
-- =============================================================================
-- sprint121 / 智能解析：ai_file_registry.business_type 取值清单补 EXTRACT_FI_ACTUALS / EXTRACT_FI_PROFORMA
--
-- 背景：手动上传财务报表时用户为每个文件声明 Actuals / Proforma（需求 R1），Java 写进财务抽取
-- 登记行（purpose='financial_extract'）的 business_type，Python init_task 读取后按文件定类型。
-- 该列是裸 VARCHAR(40)、无 CHECK 约束，新增取值不需要改约束，本迁移只更新列注释。
-- 不改表结构、不动数据：历史财务抽取行保持 NULL（需求 R11）。
--
-- 执行：人工 psql 执行，任何时间均可——只改注释，对任何版本的 Java / Python 代码都无影响。幂等可重跑。
-- 设计文档：LG docs/智能解析/智能解析-上传声明数据类型/设计/design-doc.md §3.1（D2 / D3）
-- =============================================================================

COMMENT ON COLUMN ai_file_registry.business_type IS 'Business-type enum. purpose = rag rows: APP_USER / ADMIN_USER / APP_COMPANY / ADMIN_COMPANY / ADMIN_ORGANIZATION / KNOWLEDGE_BASE / PLAYBOOK / PARSING_MEMORY / ERL_ATTACHMENT / SESSION_UPLOAD. purpose = financial_extract rows: EXTRACT_FI_ACTUALS / EXTRACT_FI_PROFORMA = the statement type (Actuals / Proforma) the user declared for the file at upload, written by Java; NULL for files uploaded before sprint121. Only KNOWLEDGE_BASE rows take part in the chatbot retrieval scope and the Memory panel, so ERL_ATTACHMENT and EXTRACT_FI_* rows are excluded from both by definition.';
```

### P2. `graph/state.py`（另附 `node_return.py`、`parallel_files_node.py` 各一处）
```python
# 不叫 DataType：ai/tools/_support/_enums.py:30 已有同名的无关类型（审核 C-17）
DeclaredDataType = Literal["ACTUALS", "PROFORMA"]


class FileInfo(TypedDict):
    file_id: str
    file_name: str
    file_status: FileStatus
    file_format: FileFormat   # populated by download_check_node (Step 1)
    # 用户上传时声明的文件类型：init_task 由 ai_file_registry.business_type 映射而来
    # （EXTRACT_FI_ACTUALS / EXTRACT_FI_PROFORMA）。未声明的文件在 init 即判 FILE_FAILED、
    # 不进 file_list，所以进来的记录必有值。与 file_format 一样不投影到 state 顶层。
    data_type: DeclaredDataType
    # 文件级解析错误的持久记录（None / 不存在 = 该文件解析无代码错误）。
    # 由 save_extract_data_to_db_node Step 4 从顶层 state.error_message 同步写入，
    # save_to_db Step 5 据此判定整 task 终态（所有文件都有 error_message → FAILED）。
    # 仅由"明确的代码错误"触发：download / LLM API / JSON 解析失败等；no_tables（内容
    # 上没识别到财务表）等业务软失败**不**写此字段。
    error_message: NotRequired[Optional[str]]


class MainGraphState(TypedDict):
    # ── 任务级（init_task 跑完即填，文件循环全程不动）────────────────
    ...  # task_id … next_row_id_in_task 不变
    # Actuals 护栏的截止月（YYYY-MM，处理时刻 UTC，D6）：init_task 每批（每条抽取消息）取一次，本批全部
    # 文件共用（审核 S-7）。NotRequired：START 时还没有。consumer/handlers.py 的 initial_state
    # 刻意不预填——空串会让护栏 month >= "" 恒真、静默剔光 Actuals，缺键 KeyError 更安全。
    reference_month: NotRequired[str]
```
`FileInfo` 仅新增 `data_type` 及其注释，`error_message` 上方原有的 5 行注释（`state.py:43-47`）原样保留（审核 C-16）。

```python
# node_return.py · InitTaskReturn 末尾加一行
    reference_month: str

# parallel_files_node.py · worker 的 state 只拷这几个顶层键；漏加 = 并行路径每个文件 refine KeyError
_TASK_SCOPED_KEYS = (
    "task_id", "task_status", "company_id", "created_by", "file_ids", "file_list",
    "reference_month",
)
```

### P3. `graph/nodes/init_task_node.py`（映射、Step 3 / 3.1、返回参考月）与 `extract_financial.fail_uploaded_files`
```python
from datetime import datetime, timezone

from ai.agent.financial_extract_graph.state import DeclaredDataType, FileInfo, MainGraphState
from lg.db.service.extract_financial import fail_uploaded_files, mark_task_processing

# 登记行 business_type → 文件声明类型（设计 D3：对内 EXTRACT_FI_*，对外与单元格 ACTUALS / PROFORMA）。
# 精确匹配、区分大小写——两个字面值是与 Java（AiFinancialFileDataType）的跨语言契约。
_DATA_TYPE_BY_BUSINESS_TYPE: dict[str, DeclaredDataType] = {
    "EXTRACT_FI_ACTUALS": "ACTUALS",
    "EXTRACT_FI_PROFORMA": "PROFORMA",
}

# 文案禁改字面——经 get_extract_data 展示在前端文件行上。
_ERR_DATA_TYPE_NOT_DECLARED = (
    "Table type (Actuals / Proforma) was not declared for this file; please re-upload it"
)

    # ── Step 3: 拉取文件清单 + 读声明类型 ──────────────────────────────
    file_list: list[FileInfo] = []
    undeclared: list[tuple[str, str | None]] = []
    with get_session() as session:
        rows = (...)  # 查询不变
        for ef, fr in rows:
            data_type = _DATA_TYPE_BY_BUSINESS_TYPE.get(ef.business_type or "")
            if data_type is None:
                undeclared.append((ef.file_id, ef.business_type))
                continue
            file_info: FileInfo = {
                "file_id": ef.file_id,
                "file_name": fr.original_name or fr.name or "",
                "file_status": ef.status,
                "file_format": "unknown",
                "data_type": data_type,
            }
            file_list.append(file_info)

    # ── Step 3.1: 未声明类型的文件直接判 FILE_FAILED、不进 file_list ─────
    # 不回退旧推断（设计 D9）。放在读 session 关闭之后：fail_uploaded_files 自开写事务，
    # 且只动仍是 UPLOADED、未删除的行（读与写之间 Java 可能已删除 / 替换该文件，审核 S-10）。
    # 不进 file_list 不影响任务终态：finalize 对空 / 全失败的 file_list 判 FAILED。
    for file_id, business_type in undeclared:
        logger.warning(
            "init_task_node[declared_type]: task_id=%s file_id=%s business_type=%r "
            "-> FILE_FAILED (table type not declared)",
            task_id, file_id, business_type,
        )
    n_failed = fail_uploaded_files([fid for fid, _ in undeclared], _ERR_DATA_TYPE_NOT_DECLARED)
    if n_failed < len(undeclared):
        logger.warning(
            "init_task_node[declared_type]: task_id=%s %d undeclared file(s) no longer "
            "UPLOADED or deleted meanwhile, left untouched",
            task_id, len(undeclared) - n_failed,
        )
    logger.info(
        "init_task_node[read_files]: task_id=%s file_ids=%d files=%d undeclared=%d",
        task_id, len(file_ids), len(file_list), len(undeclared),
    )

    ...  # Step 3.5 / Step 4 不变

    return InitTaskReturn(
        task_status=TaskStatus.PROCESSING.value,
        file_list=file_list,
        current_file_index=0,
        error_message=None,
        next_row_id_in_task=next_row_id_in_task,
        # Actuals 护栏的截止月（D6：处理时刻 UTC）：每批（每条抽取消息）取一次，本批全部文件共用；
        # refine 读 state["reference_month"]，不再逐文件取时钟（审核 S-7）。
        reference_month=datetime.now(timezone.utc).strftime("%Y-%m"),
    )
```

```python
# lg/db/service/extract_financial.py · 新增，放在 update_file_status 之后（审核 S-10）
def fail_uploaded_files(file_ids: list[str], error_message: str) -> int:
    """把仍是 UPLOADED 且未删除的文件置 FILE_FAILED + ``error_message``，返回实际更新行数。

    init_task 判"未声明类型"用。守卫写在 UPDATE 的 WHERE 里（同 ``settle_stuck_file_claims``）：
    init 读文件清单与这次写之间有窗口，期间 Java 可能已删除 / 替换该文件，不带守卫会把它
    覆盖成 FILE_FAILED。
    """
    if not file_ids:
        return 0
    with get_session() as session:
        n = (
            session.query(AiFileRegistry)
            .filter(
                AiFileRegistry.file_id.in_(file_ids),
                AiFileRegistry.status == FileStatus.UPLOADED.value,
                AiFileRegistry.deleted == False,  # noqa: E712
            )
            .update(
                {AiFileRegistry.status: FileStatus.FILE_FAILED.value,
                 AiFileRegistry.error_message: error_message},
                synchronize_session=False,
            )
        )
        session.commit()
    return n
```

### P4. `graph/nodes/shared.py`（两个新函数，放在原 Stage 2.6 的位置）
```python
# 顶部 import:state 多导入 DeclaredDataType;`from datetime import datetime, timezone` 删除
# (唯一使用方是 refine 旧的取时钟处,参考月改读 state)
from ai.agent.financial_extract_graph.state import DeclaredDataType, MainGraphState, RawRow, TableInfo

# =============================================================================
# Stage 2.6: 表类型 = 文件声明类型
# =============================================================================
def apply_declared_data_type_in_tables(
    tables: list[TableInfo], file_id: str, *, data_type: DeclaredDataType,
) -> list[TableInfo]:
    """Stage 2.6:文件内每张表的 ``data_type`` 统一设为用户上传时声明的类型(需求 R3)。

    模型在识别阶段给出的类型(pdf/image Stage 1a、excel 坐标轨步 1)不再参与判定,直接覆盖。
    进到 refine 的表三条轨都只含财务表,且落库不看 is_financial,故不按它过滤。
    ``llm_disagreed`` 只作观测:模型判定(含没给)与声明不一致的表数。
    """
    n_disagreed = sum(1 for t in tables if t.get("data_type") != data_type)
    logger.info(
        "declared_data_type: file_id=%s data_type=%s tables=%d llm_disagreed=%d",
        file_id, data_type, len(tables), n_disagreed,
    )
    return [{**tbl, "data_type": data_type} for tbl in tables]


# =============================================================================
# Stage 2.65: Actuals 文件剔除当前月及以后的 cell
# =============================================================================
def drop_current_and_future_actuals_in_tables(
    tables: list[TableInfo], file_id: str, *, data_type: DeclaredDataType, reference_month: str,
) -> list[TableInfo]:
    """Stage 2.65:声明为 ACTUALS 的文件,剔除 ``column_month >= reference_month`` 的 cell(需求 R4)。

    - 只剔带合法 ``YYYY-MM`` 月份的 cell;无月份(None / "" / 非 YYYY-MM)保留,由用户在映射页
      指定月份,提交时 Java 的 Actuals 护栏兜底。
    - 链式推出的月份(is_predict_month=True,含被推成"末月+1"的合计列)同样参与——故须在 Stage 2 之后。
    - 剔空的表整张移除(原本就空的表不动);整文件剔空 = tables=[],与 no_tables 同形。
    - 不重排 column_position / row_position(留洞有先例,下游不要求连续)。
    - PROFORMA 原样返回(需求 R5)。``reference_month`` 由 refine 从 state 顶层传入(init_task 每批
      取一次,处理时刻 UTC,D6),本函数不取时钟、便于单测注入。
    """
    if data_type != "ACTUALS":
        return tables
    new_tables: list[TableInfo] = []
    dropped_months: set[str] = set()
    n_dropped_cells = 0
    n_dropped_tables = 0
    for tbl in tables:
        rows = tbl.get("raw_rows") or []
        kept: list[RawRow] = []
        for cell in rows:
            month = cell.get("column_month") or ""
            if _MONTH_RE.match(month) and month >= reference_month:
                dropped_months.add(month)
                n_dropped_cells += 1
                continue
            kept.append(cell)
        if rows and not kept:
            n_dropped_tables += 1
            continue
        new_tables.append(tbl if len(kept) == len(rows) else {**tbl, "raw_rows": kept})
    logger.info(
        "actuals_guard: file_id=%s ref_month=%s dropped_cells=%d dropped_tables=%d "
        "dropped_months=%s",
        file_id, reference_month, n_dropped_cells, n_dropped_tables, sorted(dropped_months),
    )
    return new_tables
```

### P5. `refine_extraction_node` 接线（替换 `shared.py:2681-2714`）
```python
    tables = infer_missing_months_in_tables(tables, file_id)
    # Stage 2.6: 表类型 = 文件声明类型。声明类型与 file_format 一样只在 file_list 里
    # (state 顶层没有);init_task 保证必有值,缺键是编程错误,不兜底(D9)。
    declared = state["file_list"][state["current_file_index"]]["data_type"]
    tables = apply_declared_data_type_in_tables(tables, file_id, data_type=declared)
    # Stage 2.65: Actuals 剔除当前月及以后。须在 Stage 2 之后(推出来的月份也要查)+
    # 2.7 / 2.85 / 2.45 / 2.5 之前(它们只该处理最终入库的 cell)。截止月由 init_task
    # 每批取一次(state 顶层 reference_month),同批全部文件共用,本节点不取时钟。
    tables = drop_current_and_future_actuals_in_tables(
        tables, file_id, data_type=declared, reference_month=state["reference_month"],
    )
    # Stage 2.7: 跨 logical table 账户对齐补缺。必须在 Stage 2 之后(依赖月份补齐)
    # + Stage 2.5 之前(让补出来的 cells 也走 source_is_mapped 重算)。
    # 触发条件严:同 file + 同 table_name + 月份连续 + 单 group ≥ 2 table。
    tables = infer_missing_rows_per_account(tables, file_id)
    # 2.85 / 2.45 / 2.5 及其注释不变(2.85 注释里的"在 2.8 之后"改"在 2.65 之后")
    tables = dedupe_duplicate_month_cells_in_tables(tables, file_id)
    tables = apply_zero_default_in_tables(tables)
    tables = finalize_source_is_mapped_in_tables(tables)
```

### P6. 单测桩（`tests/ai/nodes/test_init_task_declared_type.py`、`test_declared_data_type.py`、`test_parallel_files.py` 新增用例）
```python
from types import SimpleNamespace

from ai.agent.financial_extract_graph.nodes import init_task_node as mod


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def join(self, *a, **k):
        return self

    filter = order_by = join

    def all(self):
        return self._rows

    def scalar(self):          # Step 3.5 max(source_row_id)
        return 0


class _Session:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, model, key):  # Step 1 校验
        return SimpleNamespace(status="UPLOAD_COMPLETE", deleted=False)

    def query(self, *a, **k):
        return _Query(self._rows)


def _row(file_id, business_type):
    ef = SimpleNamespace(file_id=file_id, status="UPLOADED", business_type=business_type)
    fr = SimpleNamespace(original_name=f"{file_id}.xlsx", name=file_id)
    return ef, fr


def _run(monkeypatch, rows):
    failed = []

    def _fail(ids, msg):
        if ids:                 # 全部已声明时 init 也会以空列表调用一次,不记
            failed.append((list(ids), msg))
        return len(ids)

    monkeypatch.setattr(mod, "get_session", lambda: _Session(rows))
    monkeypatch.setattr(mod, "mark_task_processing", lambda *a: True)
    monkeypatch.setattr(mod, "fail_uploaded_files", _fail)
    state = {"task_id": "t1", "file_ids": [r[0].file_id for r in rows], "created_by": "u1"}
    return mod.init_task_node(state), failed


# guard 单测样例
def _cell(col, month, **kw):
    return {"row_position": 1, "column_position": col, "account_label": "Rent",
            "account_label_join": "Rent", "column_month": month, "value": 1.0,
            "unit_type": "CURRENCY", "currency_type": "USD", "lg_category": "G&A Expenses",
            "semantic_group": "", "is_payroll_defaulted": False,
            "is_cogs_rd_conflict_defaulted": False, **kw}


def test_actuals_drops_current_and_future_months():
    tbl = {"table_id": "t", "table_name": "P&L", "page_number": 1, "is_financial": True,
           "data_type": "ACTUALS",
           "raw_rows": [_cell(1, "2026-08"), _cell(2, "2026-09"),
                        _cell(3, "2026-10"), _cell(4, "2026-11")]}
    out = drop_current_and_future_actuals_in_tables(
        [tbl], "f1", data_type="ACTUALS", reference_month="2026-10")
    assert [c["column_month"] for c in out[0]["raw_rows"]] == ["2026-08", "2026-09"]


# 节点级用例的 state:参考月经 state 注入、不取时钟(审核 S-7)。
# test_renumber_column_positions.py:447 同样补 file_list(data_type=PROFORMA,护栏不剔)/
# current_file_index / reference_month 三个键。
from ai.agent.financial_extract_graph.nodes import shared   # 落地放文件顶部


def _refine_state(tables, data_type, reference_month="2026-10"):
    return {"task_id": "t1", "file_id": "f1", "tables": tables,
            "file_list": [{"file_id": "f1", "file_name": "f1.xlsx", "file_status": "PROCESSING",
                           "file_format": "excel", "data_type": data_type}],
            "current_file_index": 0, "reference_month": reference_month}


def test_refine_uses_task_reference_month_not_clock(monkeypatch):
    monkeypatch.setattr(shared, "_apply_rag_override_safe", lambda tables, *a: tables)
    tbl = {"table_id": "t", "table_name": "P&L", "page_number": 1, "is_financial": True,
           "data_type": "ACTUALS", "raw_rows": [_cell(1, "2026-05")]}
    out = shared.refine_extraction_node(_refine_state([tbl], "ACTUALS", reference_month="2000-01"))
    assert out["tables"] == []          # 2026-05 >= 2000-01 → 剔光:读的是 state 而不是时钟


# init:参考月每批取一次
from datetime import datetime, timezone   # 落地放文件顶部


def test_reference_month_is_set_once_per_task(monkeypatch):
    out, _ = _run(monkeypatch, [_row("f1", "EXTRACT_FI_ACTUALS"), _row("f2", "EXTRACT_FI_PROFORMA")])
    assert out["reference_month"] == datetime.now(timezone.utc).strftime("%Y-%m")


# fail_uploaded_files 的守卫(桩写法同 tests/consumer/test_handlers_recovery.py:295)
def test_fail_uploaded_files_update_carries_uploaded_and_deleted_guard(monkeypatch):
    import contextlib

    import lg.db.service.extract_financial as ef

    updates = []

    class _Q:
        def __init__(self):
            self._filters = []

        def filter(self, *args):
            self._filters.extend(args)
            return self

        def update(self, values, synchronize_session=None):
            updates.append((list(values.values()), " AND ".join(str(f) for f in self._filters)))
            return 1

    class _S:
        def query(self, *entities):
            return _Q()

        def commit(self):
            pass

    @contextlib.contextmanager
    def _get_session():
        yield _S()

    monkeypatch.setattr(ef, "get_session", _get_session)
    assert ef.fail_uploaded_files(["f1"], "msg") == 1
    (values, where), = updates
    assert "file_id" in where and "status" in where and "deleted" in where
    assert "FILE_FAILED" in values and "msg" in values


# test_parallel_files.py:_state() 补 "reference_month": "2026-10",并新增
def test_worker_state_carries_reference_month(monkeypatch):
    from ai.agent.financial_extract_graph.nodes import parallel_files_node as helper

    _install_fakes(monkeypatch, helper, rows_per_file={})
    seen = []

    def _refine(st):
        seen.append(st["reference_month"])      # 漏进 _TASK_SCOPED_KEYS → KeyError
        return {"tables": []}

    monkeypatch.setattr(helper, "refine_extraction_node", _refine)
    helper.parallel_extract_files_node(_state(3))
    assert seen == ["2026-10"] * 3
```

## Java

> 对应 [dev-java](./dev-java.md)。行号基于 CIOaas-api `sprint121`（`ccf3430f6`）。

### J1. `extract/util/AiFinancialFileDataType.java`（新增，取值映射唯一定义处）
```java
package com.gstdev.cioaas.web.ai.financial.extract.util;

import org.apache.commons.lang3.StringUtils;

import java.util.Optional;

/**
 * 财务抽取文件的声明类型（需求 R1：上传时用户为每个文件声明 Actuals / Proforma）。
 *
 * <p>接口值（枚举常量名，与单元格 {@code source_data_type} 同一套）与登记行
 * {@code ai_file_registry.business_type} 的对应关系只在这里定义（设计 D3）。Python init_task
 * 读取时按同一张表反向转换——两个字面值是跨语言契约，改动须两端同步。
 */
public enum AiFinancialFileDataType {

  ACTUALS("EXTRACT_FI_ACTUALS"),
  PROFORMA("EXTRACT_FI_PROFORMA");

  private final String businessType;

  AiFinancialFileDataType(String businessType) {
    this.businessType = businessType;
  }

  /** 写入 {@code ai_file_registry.business_type} 的值。 */
  public String businessType() {
    return businessType;
  }

  /** 接口值 → 枚举；空或不认识返回 empty（区分大小写、不 trim，与请求上的 {@code @Pattern} 一致）。 */
  public static Optional<AiFinancialFileDataType> fromCode(String raw) {
    if (StringUtils.isBlank(raw)) {
      return Optional.empty();
    }
    try {
      return Optional.of(valueOf(raw));
    } catch (IllegalArgumentException ignored) {
      return Optional.empty();
    }
  }

  /** 登记行上的 business_type 是否为已声明的财务抽取类型；上线前的历史行为 NULL → false。 */
  public static boolean isDeclaredBusinessType(String businessType) {
    for (AiFinancialFileDataType type : values()) {
      if (type.businessType.equals(businessType)) {
        return true;
      }
    }
    return false;
  }
}
```

### J2. `extract/vo/request/AiFinancialCommitUploadRequest.java`（新增）
```java
package com.gstdev.cioaas.web.ai.financial.extract.vo.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * Request body of {@code /tasks/commitUpload} (deferred-upload flow, no task yet): the staged files
 * to commit, each with the data type the user declared at upload (requirement R1).
 */
@Data
@Schema(description = "延迟上传提交：companyId + 本次提交的文件及其声明类型")
public class AiFinancialCommitUploadRequest {

  @NotBlank
  @Size(max = 36)
  @Schema(description = "公司 ID", requiredMode = Schema.RequiredMode.REQUIRED)
  private String companyId;

  @NotEmpty(message = "files is required")
  @Size(max = 100)
  @Schema(description = "本次提交的文件（presignUploads 返回的 fileId + 用户声明的类型）",
    requiredMode = Schema.RequiredMode.REQUIRED)
  private List<@NotNull @Valid AiFinancialCommitUploadFileItem> files;
}
```

### J3. `extract/vo/request/AiFinancialCommitUploadFileItem.java`（新增）
```java
package com.gstdev.cioaas.web.ai.financial.extract.vo.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * One file in a commitUpload request: {@code files.id} plus the declared data type.
 */
@Data
@Schema(description = "提交的单个文件：fileId + 声明类型")
public class AiFinancialCommitUploadFileItem {

  @NotBlank
  @Size(max = 36)
  @Schema(description = "files 表主键（presignUploads 返回的 fileId）", requiredMode = Schema.RequiredMode.REQUIRED)
  private String fileId;

  @NotBlank(message = "dataType is required")
  @Pattern(regexp = "ACTUALS|PROFORMA", message = "dataType must be ACTUALS or PROFORMA")
  @Schema(description = "用户声明的文件类型；无默认值，必填", requiredMode = Schema.RequiredMode.REQUIRED,
    allowableValues = {"ACTUALS", "PROFORMA"})
  private String dataType;
}
```

### J4. `AiFinancialPresignUploadFileItem` 新增字段（另加 import `jakarta.validation.constraints.Pattern`）
```java
  @Pattern(regexp = "ACTUALS|PROFORMA", message = "dataType must be ACTUALS or PROFORMA")
  @Schema(description = "映射页「上传新文件」时声明的类型，带 taskId 时写入登记行；替换文件、首次上传弹窗不传",
    allowableValues = {"ACTUALS", "PROFORMA"})
  private String dataType;
```

### J5. Controller 与 Service 接口签名
```java
// AiFinancialExtractionController
  @Operation(summary = "延迟上传流程：点击 Next 时创建 task 并提交解析")
  @PostMapping("/tasks/commitUpload")
  public Result<AiFinancialCommitUploadResponse> commitUpload(
    @RequestBody @Valid AiFinancialCommitUploadRequest request) {
    return Result.success("success", aiFinancialExtractionService.commitUpload(request));
  }

// AiFinancialExtractionService
  /**
   * ……（原注释）
   * @param request companyId + 本次要提交的文件及其声明类型（ACTUALS / PROFORMA，写入登记行 business_type）
   */
  AiFinancialCommitUploadResponse commitUpload(AiFinancialCommitUploadRequest request);
```

### J6. ServiceImpl 片段
需新增 import：`java.util.LinkedHashMap`、`java.util.Map`，以及 `AiFinancialFileDataType`、`AiFinancialCommitUploadRequest`、`AiFinancialCommitUploadFileItem`（replaceFile 改用 `orElseThrow`，不再需要 `java.util.Optional`）。
```java
  /** 接口值 ACTUALS / PROFORMA → 登记行 business_type（映射见 AiFinancialFileDataType）；空或非法抛 BadRequestException。 */
  private static String toBusinessType(String dataType) {
    return AiFinancialFileDataType.fromCode(dataType)
      .map(AiFinancialFileDataType::businessType)
      .orElseThrow(() -> new BadRequestException("dataType must be ACTUALS or PROFORMA: " + dataType));
  }

  // ── commitUpload：替换原 :391-402 去重段并加已提交校验，循环改遍历 map ──
  @Override
  @Transactional(propagation = Propagation.REQUIRED, rollbackFor = Exception.class)
  public AiFinancialCommitUploadResponse commitUpload(AiFinancialCommitUploadRequest request) {
    String companyId = request.getCompanyId().trim();
    // fileId → business_type（保持请求顺序）。类型在建任务之前全部校验完，失败不建任务；
    // 同一文件重复且类型相同 → 去重；类型不同 → 拒绝（R6：一个文件只能是一种类型）
    Map<String, String> businessTypeByFileId = new LinkedHashMap<>();
    if (request.getFiles() != null) {
      for (AiFinancialCommitUploadFileItem item : request.getFiles()) {
        if (item == null || StringUtils.isBlank(item.getFileId())) {
          continue;   // 同旧实现跳过空项；入口 @NotNull / @NotBlank 已拦，这里只防直接调用时 NPE（审核 C-7）
        }
        String fileId = item.getFileId().trim();
        String businessType = toBusinessType(item.getDataType());
        String previous = businessTypeByFileId.putIfAbsent(fileId, businessType);
        if (previous != null && !previous.equals(businessType)) {
          throw new BadRequestException("Conflicting dataType for file: " + fileId);
        }
      }
    }
    if (businessTypeByFileId.isEmpty()) {
      throw new BadRequestException("files is required");
    }
    // 已登记的文件不得再次提交：@Id 是业务赋值的 file_id，save 新对象会 merge 覆盖已有行（审核 S-6）。
    // findAllById 不带 deleted 条件，软删行同样拦
    List<AiFileRegistry> registered = extractionFileRepository.findAllById(businessTypeByFileId.keySet());
    if (!registered.isEmpty()) {
      throw new BadRequestException("File already committed: " + registered.get(0).getFileId());
    }

    String bucketName = s3Properties.getBucketName();
    String stagingPrefix = OCR_PREFIX + "staging/" + companyId + "/";
    AiFinancialExtractionTask task = resolveOrCreateTask(companyId, null);
    String tid = task.getId();

    List<String> committed = new ArrayList<>();
    List<String> missing = new ArrayList<>();
    for (Map.Entry<String, String> entry : businessTypeByFileId.entrySet()) {
      String fileId = entry.getKey();
      // …… 原 :411-416 不变（staging 前缀校验）……
      // HEAD 看返回值：对象不存在也算 missing（审核 J-R6）。原实现只 catch 异常，
      // 而 headObject 遇 404 返回 S3ObjectHead.missing()、不抛，S3 上没有的文件照样被登记
      try {
        if (!storage.headObject(bucketName, fo.getName()).exists()) {
          missing.add(fileId);
          continue;
        }
      } catch (Exception ex) {
        log.warn("commitUpload: file_id={} key={} HEAD failed: {}", fileId, fo.getName(), ex.getMessage());
        missing.add(fileId);
        continue;
      }
      AiFileRegistry row = new AiFileRegistry();
      // …… 原 :426-433 不变 ……
      row.setDeleted(Boolean.FALSE);
      row.setBusinessType(entry.getValue());   // 用户声明的类型，Python init_task 从这里读（D4）
      extractionFileRepository.save(row);
      committed.add(fileId);
    }
    // …… 原 :438-450 不变（空集合报错 / 任务置 UPLOAD_COMPLETE / afterCommit 发 SQS / 返回）……
  }

  // ── presignUploads：增量分支 if (!deferred) 内（原 :155-166），setDeleted 之后加 ──
        row.setDeleted(Boolean.FALSE);
        // 映射页「上传新文件」带声明类型；替换文件不带（replaceFile 再从旧文件继承），留空
        row.setBusinessType(StringUtils.isBlank(entry.getDataType()) ? null : toBusinessType(entry.getDataType()));
        stagedRows.add(row);

  // ── uploadComplete：校验保留列表循环（原 :338-345），归属校验之后加 ──
    for (String fileId : keptIds) {
      AiFileRegistry row = extractionFileRepository.findByFileIdAndDeletedFalse(fileId)
        .orElseThrow(() -> new BadRequestException("File not found for task: " + fileId));
      if (!tid.equals(row.getTaskId())) {
        throw new BadRequestException("File " + fileId + " does not belong to task " + tid);
      }
      // 只看本批新文件（PENDING）：fileIds 里可能带已解析的历史文件，上线前的任务这些行类型为 NULL（R11 不补写）
      if ("PENDING".equals(row.getStatus())
        && !AiFinancialFileDataType.isDeclaredBusinessType(row.getBusinessType())) {
        throw new BadRequestException("Table type (Actuals / Proforma) is required for file: "
          + StringUtils.defaultIfBlank(row.getFileName(), fileId));
      }
    }

  // ── replaceFile：替换原 :276-287（先校验、后删除，审核 S-5）──
    // 1. 校验：旧登记行必须存在（assertFileBelongsToTask 在登记行、files 行都不在时会放行）；
    //    新行必须 PENDING。都在删除之前做——fileService.delete 的 S3 删除不随事务回滚
    AiFileRegistry oldRow = extractionFileRepository.findByFileIdAndDeletedFalse(oldId)
      .orElseThrow(() -> new BadRequestException("Old file not found for task: " + oldId));
    AiFileRegistry newRow = extractionFileRepository.findByFileIdAndDeletedFalse(newId)
      .orElseThrow(() -> new BadRequestException("New ai_file_registry row not found or already deleted: " + newId));
    if (!"PENDING".equals(newRow.getStatus())) {
      throw new BadRequestException("New file must be PENDING for replace; current=" + newRow.getStatus());
    }
    String inheritedBusinessType = oldRow.getBusinessType();   // 软删前取（软删后按未删条件查不到）

    // 2. 旧文件下线：ai_file_registry 软删 + files/S3 物理删
    softDeleteExtractionFile(oldRow);
    fileRepository.findById(oldId).ifPresent(f -> fileService.delete(oldId));

    // 3. 新文件转 UPLOADED 并继承旧文件的声明类型（R8），推进 task 状态 + 触发 Python 解析（本次仅解析 newId）
    if (inheritedBusinessType == null) {
      // 上线前上传的旧文件没有类型（R11 不补写）：照设计原样复制，Python 会把新文件判为 FILE_FAILED。
      // 已拍板照此处理、不在替换时拒绝（dev-java §10 J-R2）。traceId 由 MDC 带出（coding.md §11）
      log.warn("[AI-Extract] replaceFile: old file has no declared type, new file inherits null: "
        + "taskId={}, organizationId={}, userId={}, oldFileId={}, newFileId={}",
        tid, task.getOrganizationId(), SecurityUtils.getUserId(), oldId, newId);
    }
    newRow.setBusinessType(inheritedBusinessType);   // 无条件覆盖：替换以旧文件为准
    newRow.setStatus("UPLOADED");
    extractionFileRepository.save(newRow);
```

### J7. `AiFileRegistry.businessType` 注释（只改注释）
```java
  /**
   * 业务类型枚举，按 {@code purpose} 分两组：
   * <ul>
   *   <li>{@code purpose = 'rag'}（Python 写）：APP_USER / ADMIN_USER / APP_COMPANY / ADMIN_COMPANY /
   *       ADMIN_ORGANIZATION / KNOWLEDGE_BASE / PLAYBOOK / PARSING_MEMORY / SESSION_UPLOAD / ERL_ATTACHMENT
   *       （ERL_ATTACHMENT 2026-09-18 新增：ERL 答题附件，落 ERL 专属 space 且 {@code business_type ≠ KNOWLEDGE_BASE}
   *       ⇒ 不进 chatbot 检索、也不进知识库 / Memory 面板（两者都按 KNOWLEDGE_BASE 圈定）；走 SUMMARY_ONLY，不产出 chunk）。</li>
   *   <li>{@code purpose = 'financial_extract'}（Java 本模块写，sprint121 新增）：EXTRACT_FI_ACTUALS /
   *       EXTRACT_FI_PROFORMA = 用户上传时声明的文件类型（需求 R1），Python init_task 据此决定整份文件按 Actuals
   *       还是 Proforma 抽取；取值映射见 {@link com.gstdev.cioaas.web.ai.financial.extract.util.AiFinancialFileDataType}。
   *       本需求之前上传的历史行为 NULL（不补写）。</li>
   * </ul>
   */
  @Column(name = "business_type", length = 40)
  private String businessType;
```
另需同步：类 javadoc 第 29 行"本财务模块仅写 OCR 相关列"、字段组注释第 88-90 行"本财务模块不写这些列"，改为"除 business_type 外不写"。
另：`AiFinancialExtractionMappingData.parentTableId` 的 javadoc（第 39-44 行）与 `AiFinancialPullExtractRowResponse.parentTableId` 的 `@Schema` 描述（第 30-33 行）各补一句"历史字段：sprint121 起新任务恒为 NULL，仅供历史回放"（Python 停止写 parent_table_id，审核 A-7）。

### J8. 单测骨架
```java
// src/test/java/com/gstdev/cioaas/web/ai/financial/extract/service/AiFinancialExtractionDeclaredTypeTest.java
@ExtendWith(MockitoExtension.class)
class AiFinancialExtractionDeclaredTypeTest {

  private static final String COMPANY_ID = "company-1";
  private static final String TASK_ID = "task-1";
  private static final String BUCKET = "bucket";

  @Mock private AiFinancialExtractionTaskRepository taskRepository;
  @Mock private AiFileRegistryRepository extractionFileRepository;
  @Mock private FileRepository fileRepository;
  @Mock private FileService fileService;
  @Mock private AbstractStorage storage;
  @Mock private S3Properties s3Properties;
  @Mock private AiFinancialExtractionSqsProcessor sqsProcessor;

  @InjectMocks private AiFinancialExtractionServiceImpl service;

  /** 两个字面值是给 Python 的契约，钉住。 */
  @Test
  void mappingLiteralsArePinned() {
    assertEquals("EXTRACT_FI_ACTUALS", AiFinancialFileDataType.ACTUALS.businessType());
    assertEquals("EXTRACT_FI_PROFORMA", AiFinancialFileDataType.PROFORMA.businessType());
    assertTrue(AiFinancialFileDataType.fromCode("actuals").isEmpty(), "区分大小写，与 @Pattern 一致");
    assertFalse(AiFinancialFileDataType.isDeclaredBusinessType(null));
    assertFalse(AiFinancialFileDataType.isDeclaredBusinessType("KNOWLEDGE_BASE"));
  }

  @Test
  void commitUploadWritesDeclaredTypePerFile() {
    when(s3Properties.getBucketName()).thenReturn(BUCKET);
    when(taskRepository.save(any())).thenAnswer(inv -> {
      AiFinancialExtractionTask t = inv.getArgument(0);
      t.setId(TASK_ID);
      return t;
    });
    stubStagedFile("f-1");
    stubStagedFile("f-2");
    // HEAD 返回"存在"（J-R6 修后会看返回值）
    when(storage.headObject(eq(BUCKET), anyString()))
      .thenReturn(new S3ObjectHead(true, 1L, "etag", "application/octet-stream"));

    service.commitUpload(commitRequest(item("f-1", "ACTUALS"), item("f-2", "PROFORMA")));

    ArgumentCaptor<AiFileRegistry> rows = ArgumentCaptor.forClass(AiFileRegistry.class);
    verify(extractionFileRepository, times(2)).save(rows.capture());
    assertEquals(List.of("EXTRACT_FI_ACTUALS", "EXTRACT_FI_PROFORMA"),
      rows.getAllValues().stream().map(AiFileRegistry::getBusinessType).toList());
    verify(sqsProcessor).sendExtractionStartMessage(eq(TASK_ID), eq(COMPANY_ID), any(), eq(List.of("f-1", "f-2")));
  }

  /** T16（审核 J-R6）：HEAD 返回"不存在"→ 进 missingFileIds、不登记；其余文件照常提交。 */
  @Test
  void commitUploadTreatsMissingS3ObjectAsMissing() {
    when(s3Properties.getBucketName()).thenReturn(BUCKET);
    when(taskRepository.save(any())).thenAnswer(inv -> {
      AiFinancialExtractionTask t = inv.getArgument(0);
      t.setId(TASK_ID);
      return t;
    });
    stubStagedFile("f-1");
    stubStagedFile("f-2");
    when(storage.headObject(eq(BUCKET), anyString()))
      .thenReturn(new S3ObjectHead(true, 1L, "etag", "application/octet-stream"))
      .thenReturn(S3ObjectHead.missing());

    AiFinancialCommitUploadResponse resp =
      service.commitUpload(commitRequest(item("f-1", "ACTUALS"), item("f-2", "ACTUALS")));

    assertEquals(List.of("f-1"), resp.getCommittedFileIds());
    assertEquals(List.of("f-2"), resp.getMissingFileIds());
    verify(extractionFileRepository, times(1)).save(any());
  }

  @Test
  void commitUploadRejectsUnknownTypeBeforeCreatingTask() {
    BadRequestException ex = assertThrows(BadRequestException.class,
      () -> service.commitUpload(commitRequest(item("f-1", "FORECAST"))));
    assertEquals("dataType must be ACTUALS or PROFORMA: FORECAST", ex.getMessage());
    verify(taskRepository, never()).save(any());
    verifyNoInteractions(sqsProcessor);
  }

  @Test
  void commitUploadRejectsConflictingTypesForSameFile() {
    BadRequestException ex = assertThrows(BadRequestException.class,
      () -> service.commitUpload(commitRequest(item("f-1", "ACTUALS"), item("f-1", "PROFORMA"))));
    assertEquals("Conflicting dataType for file: f-1", ex.getMessage());
    verify(taskRepository, never()).save(any());
  }

  @Test
  void uploadCompleteRejectsPendingFileWithoutDeclaredType() {
    when(taskRepository.findById(TASK_ID)).thenReturn(Optional.of(task("REVIEWING")));
    AiFileRegistry pending = registryRow("f-1", "PENDING", null);
    when(extractionFileRepository.findByFileIdAndDeletedFalse("f-1")).thenReturn(Optional.of(pending));
    AiFinancialUploadCompleteRequest request = new AiFinancialUploadCompleteRequest();
    request.setFileIds(List.of("f-1"));

    BadRequestException ex = assertThrows(BadRequestException.class,
      () -> service.uploadComplete(TASK_ID, request));

    assertTrue(ex.getMessage().contains("f-1.xlsx"));
    assertEquals("PENDING", pending.getStatus(), "先校验后改写，失败时行未被改动");
    verifyNoInteractions(sqsProcessor);
  }

  @Test
  void replaceFileInheritsOldFileType() {
    when(taskRepository.findById(TASK_ID)).thenReturn(Optional.of(task("REVIEWING")));
    AiFileRegistry oldRow = registryRow("old", "REVIEW_READY", "EXTRACT_FI_ACTUALS");
    AiFileRegistry newRow = registryRow("new", "PENDING", "EXTRACT_FI_PROFORMA"); // 模拟前端误传
    when(extractionFileRepository.findByFileIdAndDeletedFalse("old")).thenReturn(Optional.of(oldRow));
    when(extractionFileRepository.findByFileIdAndDeletedFalse("new")).thenReturn(Optional.of(newRow));
    when(fileRepository.findById("new")).thenReturn(Optional.of(new FileObject()));
    when(fileRepository.findById("old")).thenReturn(Optional.empty());
    AiFinancialFileReplaceRequest request = new AiFinancialFileReplaceRequest();
    request.setOldFileId("old");
    request.setNewFileId("new");

    service.replaceFile(TASK_ID, request);

    assertEquals("EXTRACT_FI_ACTUALS", newRow.getBusinessType());
    assertEquals("UPLOADED", newRow.getStatus());
    assertTrue(oldRow.getDeleted());
  }

  /** 审核 S-6：已有登记行（含软删）的 fileId 不得再次提交——save 会 merge 覆盖旧行。 */
  @Test
  void commitUploadRejectsAlreadyRegisteredFile() {
    AiFileRegistry existing = registryRow("f-1", "REVIEW_READY", "EXTRACT_FI_ACTUALS");
    existing.setDeleted(true);   // findAllById 不带 deleted 条件，软删行同样拦
    when(extractionFileRepository.findAllById(any())).thenReturn(List.of(existing));

    BadRequestException ex = assertThrows(BadRequestException.class,
      () -> service.commitUpload(commitRequest(item("f-1", "ACTUALS"))));

    assertEquals("File already committed: f-1", ex.getMessage());
    verify(taskRepository, never()).save(any());
    verify(extractionFileRepository, never()).save(any());
    verifyNoInteractions(sqsProcessor);
  }

  /** 审核 S-5：旧登记行不存在（files 行也没有，assertFileBelongsToTask 放行）→ 拒绝，且什么都不删。 */
  @Test
  void replaceFileRejectsMissingOldRow() {
    when(taskRepository.findById(TASK_ID)).thenReturn(Optional.of(task("REVIEWING")));
    AiFileRegistry newRow = registryRow("new", "PENDING", null);
    when(extractionFileRepository.findByFileIdAndDeletedFalse("old")).thenReturn(Optional.empty());
    when(extractionFileRepository.findByFileIdAndDeletedFalse("new")).thenReturn(Optional.of(newRow));
    when(fileRepository.findById("old")).thenReturn(Optional.empty());
    when(fileRepository.findById("new")).thenReturn(Optional.of(new FileObject()));

    BadRequestException ex = assertThrows(BadRequestException.class,
      () -> service.replaceFile(TASK_ID, replaceRequest()));

    assertEquals("Old file not found for task: old", ex.getMessage());
    assertEquals("PENDING", newRow.getStatus());
    verify(fileService, never()).delete(any());
  }

  /** 审核 S-5：新行不是 PENDING → 拒绝，旧文件没被删（先校验后删除）。 */
  @Test
  void replaceFileValidatesNewRowBeforeDeletingOld() {
    when(taskRepository.findById(TASK_ID)).thenReturn(Optional.of(task("REVIEWING")));
    AiFileRegistry oldRow = registryRow("old", "REVIEW_READY", "EXTRACT_FI_ACTUALS");
    when(extractionFileRepository.findByFileIdAndDeletedFalse("old")).thenReturn(Optional.of(oldRow));
    when(extractionFileRepository.findByFileIdAndDeletedFalse("new"))
      .thenReturn(Optional.of(registryRow("new", "UPLOADED", null)));
    when(fileRepository.findById("new")).thenReturn(Optional.of(new FileObject()));

    assertThrows(BadRequestException.class, () -> service.replaceFile(TASK_ID, replaceRequest()));

    assertFalse(oldRow.getDeleted());
    verify(fileService, never()).delete(any());
  }

  // T5、T10、T12 与上面同构，省略。
  // T6–T8 走 presignUploads，比 commitUpload 多下面这些 stub（审核 C-3）；请求项的 length 是 Long，必须赋值（:129 拆箱）
  private void stubPresign() {
    when(s3Properties.getBucketName()).thenReturn(BUCKET);
    when(fileRepository.saveAndFlush(any())).thenAnswer(inv -> {   // 不 stub 则 persisted 为 null，:149 NPE
      FileObject fo = inv.getArgument(0);
      fo.setId(UUID.randomUUID().toString());
      return fo;
    });
    when(storage.presignPutObject(eq(BUCKET), anyString(), anyString(), any()))   // 不 stub 则 :186 NPE
      .thenReturn(new PresignedPutObjectResult("https://s3.example/put", Map.of(), 900L));
  }

  /** T6 / T7 带 taskId：任务状态不能是 UPLOAD_COMPLETE / PROCESSING，否则 :113 blocksNewUpload 拒绝。 */
  private void stubTaskForPresign() {
    when(taskRepository.findByIdAndCompanyIdAndDeletedFalse(TASK_ID, COMPANY_ID))
      .thenReturn(Optional.of(task("REVIEWING")));
  }

  private static AiFinancialFileReplaceRequest replaceRequest() {
    AiFinancialFileReplaceRequest request = new AiFinancialFileReplaceRequest();
    request.setOldFileId("old");
    request.setNewFileId("new");
    return request;
  }

  private void stubStagedFile(String fileId) {
    FileObject fo = new FileObject();
    fo.setName("ai/staging/" + COMPANY_ID + "/" + fileId + "_a.xlsx");
    fo.setOriginalName(fileId + ".xlsx");
    fo.setLength(10L);
    when(fileRepository.findById(fileId)).thenReturn(Optional.of(fo));
  }

  private static AiFinancialCommitUploadRequest commitRequest(AiFinancialCommitUploadFileItem... items) {
    AiFinancialCommitUploadRequest request = new AiFinancialCommitUploadRequest();
    request.setCompanyId(COMPANY_ID);
    request.setFiles(List.of(items));
    return request;
  }

  private static AiFinancialCommitUploadFileItem item(String fileId, String dataType) {
    AiFinancialCommitUploadFileItem item = new AiFinancialCommitUploadFileItem();
    item.setFileId(fileId);
    item.setDataType(dataType);
    return item;
  }

  private static AiFinancialExtractionTask task(String status) {
    AiFinancialExtractionTask task = new AiFinancialExtractionTask();
    task.setId(TASK_ID);
    task.setCompanyId(COMPANY_ID);
    task.setStatus(status);
    task.setDeleted(false);
    return task;
  }

  private static AiFileRegistry registryRow(String fileId, String status, String businessType) {
    AiFileRegistry row = new AiFileRegistry();
    row.setFileId(fileId);
    row.setTaskId(TASK_ID);
    row.setCompanyId(COMPANY_ID);
    row.setStatus(status);
    row.setFileName(fileId + ".xlsx");
    row.setBusinessType(businessType);
    return row;
  }
}

// src/test/java/com/gstdev/cioaas/web/ai/financial/extract/vo/request/AiFinancialCommitUploadRequestValidationTest.java
class AiFinancialCommitUploadRequestValidationTest {

  private static final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

  /** 旧前端只发 companyId + fileIds；fileIds 被 Jackson 忽略，files 为 null → 必须被拒（Java 与前端须同批发布）。 */
  @Test
  void rejectsLegacyBodyWithoutFiles() {
    AiFinancialCommitUploadRequest request = new AiFinancialCommitUploadRequest();
    request.setCompanyId("company-1");
    assertEquals(Set.of("files"), violatedPaths(request));
  }

  @ParameterizedTest
  @NullSource
  @ValueSource(strings = {"", "Actuals", "FORECAST"})
  void rejectsMissingOrUnknownDataType(String dataType) {
    AiFinancialCommitUploadFileItem item = new AiFinancialCommitUploadFileItem();
    item.setFileId("f-1");
    item.setDataType(dataType);
    AiFinancialCommitUploadRequest request = new AiFinancialCommitUploadRequest();
    request.setCompanyId("company-1");
    request.setFiles(List.of(item));
    assertTrue(violatedPaths(request).contains("files[0].dataType"));
  }

  /** V4：presign 的 dataType 可选但须合法；只校验这一个字段，未赋值的 fileName / length 不掺进来（审核 C-4）。 */
  @Test
  void presignDataTypeIsOptionalButMustBeValid() {
    AiFinancialPresignUploadFileItem item = new AiFinancialPresignUploadFileItem();
    assertTrue(validator.validateProperty(item, "dataType").isEmpty());
    item.setDataType("X");
    assertEquals(1, validator.validateProperty(item, "dataType").size());
  }

  private static Set<String> violatedPaths(Object bean) {
    return validator.validate(bean).stream()
      .map(v -> v.getPropertyPath().toString())
      .collect(Collectors.toSet());
  }
}
```

## 前端

> 对应 [dev-frontend](./dev-frontend.md)。行号基于 CIOaas-web `sprint121`（`eea52f3c`）。

### W1. `src/services/api/ai/dto.ts`（新增）
```ts
/**
 * ai 域对外 DTO（页面可 import；见 standards/architecture.md §4.1）。
 * 2026-10「上传声明数据类型」新增；本域其余类型仍内联在 aiService.ts（TODO(service-dto)）。
 */

/** 财务数据类型：上传时声明的文件类型，与单元格 sourceDataType 同一套值（design-doc §3.3）。 */
export type FinancialDataType = 'ACTUALS' | 'PROFORMA';
```

### W2. `src/services/api/ai/request.ts`（新增）
```ts
/**
 * ai 域 Request 传输实体（仅 API 层用；见 standards/coding.md §2）。
 * 只收录 2026-10「上传声明数据类型」改到的两个请求体，其余仍内联在 aiService.ts（TODO(service-dto)）。
 */
import type { FinancialDataType } from './dto';

/** getUploadUrl 单文件条目。dataType 仅映射页「Upload New Document」（带 taskId）传；首次上传弹窗与替换文件不传。 */
export interface GetUploadUrlFileItem {
  fileName: string;
  length: number;
  dataType?: FinancialDataType;
}

/** POST /api/web/ai/financialExtraction/tasks/getUploadUrl 请求体。taskId 为空 = 首次上传的延迟流程。 */
export interface GetUploadUrlRequest {
  companyId: string;
  taskId: string;
  fileList: GetUploadUrlFileItem[];
}

/** commitUpload 单文件条目：每个文件都必须声明类型（需求 R1）。 */
export interface CommitUploadFileItem {
  fileId: string;
  dataType: FinancialDataType;
}

/** POST /api/web/ai/financialExtraction/tasks/commitUpload 请求体。 */
export interface CommitUploadRequest {
  companyId: string;
  files: CommitUploadFileItem[];
}
```

### W3. `src/services/api/ai/aiService.ts`（改动的函数）
```ts
import request from '@/utils/request';
import type { CommitUploadRequest, GetUploadUrlRequest } from './request';

export async function getUploadUrl(params: GetUploadUrlRequest): Promise<GetUploadUrlResponse> {
  return request('/api/web/ai/financialExtraction/tasks/getUploadUrl', {
    method: 'POST',
    data: params,
  });
}

// 延迟上传流程「点击 Next 提交」：presignUploads(不带 taskId) 只 PUT 到 S3，
// 本接口此刻才创建 task + 登记 ai_file_registry（含每个文件的声明类型）+ 触发解析，返回新 taskId。
export async function commitUpload(params: CommitUploadRequest): Promise<CommitUploadResponse> {
  return request('/api/web/ai/financialExtraction/tasks/commitUpload', {
    method: 'POST',
    data: params,
  });
}
```

### W4. `src/pages/financial/aiFinancialExtraction/constants.ts`（新增常量）
```ts
import type { FinancialDataType } from '@/services/api/ai/dto';

// 上传声明的表类型（需求 R1 / R12：文案统一 Proforma；值与单元格 sourceDataType 同一套）
export const UPLOAD_DATA_TYPE_OPTIONS: { value: FinancialDataType; label: string }[] = [
  { value: 'ACTUALS', label: 'Actuals' },
  { value: 'PROFORMA', label: 'Proforma' },
];
// TABLE TYPE 下拉未选时的占位（需求 Q1，待设计确认）
export const UPLOAD_DATA_TYPE_PLACEHOLDER = 'Select';
// Actuals 当前月保护的固定说明（需求 §5.1 / R4）
export const ACTUALS_CURRENT_MONTH_NOTE =
  'For Actuals files, data for the current month and later is not extracted.';
```

### W5. `ImportStatementsModal.tsx`（片段）
```tsx
import { DownOutlined } from '@ant-design/icons'; // 原 CloseOutlined 一直没用（关闭图标是 <img>，tsc 报 TS6133），顺手删除（审核 C-25）
import { Alert, Dropdown, Menu, Modal, Progress, Select } from 'antd';
import type { FinancialDataType } from '@/services/api/ai/dto';
import {
  UPLOAD_ACCEPTED_EXTENSIONS,
  UPLOAD_DATA_TYPE_OPTIONS,
  UPLOAD_DATA_TYPE_PLACEHOLDER,
  ACTUALS_CURRENT_MONTH_NOTE,
} from '@/pages/financial/aiFinancialExtraction/constants';

interface UploadFile {
  id: string;       // local key
  fileId: string;   // server-assigned ID returned by getUploadUrl
  file: File;
  progress: number;
  status: 'uploading' | 'done';
  tableType?: FinancialDataType; // 用户声明的类型；未选 = undefined（D7 无默认值）
}

// Helpers 区
type DeclaredUploadFile = UploadFile & { tableType: FinancialDataType };
const isDeclared = (uf: UploadFile): uf is DeclaredUploadFile => !!uf.tableType;

// 组件内
const handleSetFileType = useCallback(
  (id: string, type: FinancialDataType) => {
    setUploadFiles((prev) => prev.map((uf) => (uf.id === id ? { ...uf, tableType: type } : uf)));
  },
  [setUploadFiles],
);

// 批量设置：只作用于此刻列表里的文件（含上传中）；之后新加的文件保持未选（需求 R1 / R2）
const handleSetAllTypes = useCallback(
  (type: FinancialDataType) => {
    setUploadFiles((prev) => prev.map((uf) => ({ ...uf, tableType: type })));
  },
  [setUploadFiles],
);

const handleNext = useCallback(async () => {
  const doneFiles = uploadFilesRef.current.filter((uf) => uf.status === 'done');
  if (!doneFiles.length || isSubmitting) return;
  // 兜底：canNext 已要求每个文件都选了类型，这里防按钮态与 ref 不同步的瞬间
  const declared = doneFiles.filter(isDeclared);
  if (declared.length !== doneFiles.length) return;

  const files = declared
    .filter((uf) => uf.fileId)
    .map((uf) => ({ fileId: uf.fileId, dataType: uf.tableType }));
  setIsSubmitting(true);

  try {
    const res = await commitUpload({ companyId, files });
    if (!res.success || !res.data?.taskId) throw new Error(res.message || 'Upload completion failed');
    // S3 上没有对象的文件：Java 未登记、不会出现在映射页，逐个提示（审核 J-R6）；其余文件照常进入下一步
    for (const id of res.data.missingFileIds ?? []) {
      const uf = doneFiles.find((f) => f.fileId === id);
      if (uf) pushUploadError('GENERIC', uf.file.name);
    }
    // …其余与现状相同（taskIdRef / fileMeta / onNext；catch 推 GENERIC 并复位 isSubmitting）
  } catch {
    for (const uf of doneFiles) pushUploadError('GENERIC', uf.file.name);
    setIsSubmitting(false);
  }
}, [isSubmitting, onNext, companyId]);

const isAnyUploading = uploadFiles.some((uf) => uf.status === 'uploading');
const allTyped = uploadFiles.every((uf) => !!uf.tableType);
const canNext = uploadFiles.length > 0 && !isAnyUploading && !isSubmitting && allTyped;

// JSX — 标题后
<h3 className={styles.title}>Upload Financial Documents</h3>
<Alert type="info" showIcon message={ACTUALS_CURRENT_MONTH_NOTE} className={styles.notice} />

// JSX — 表头
<span className={styles.colFileSize}>FILE SIZE</span>
<span className={styles.colTableType}>TABLE TYPE</span>
<span className={styles.colAction} />

// JSX — 每行：大小 / 进度块之后、Remove 之前
<Select<FinancialDataType>
  size="small"
  className={styles.typeSelect}
  placeholder={UPLOAD_DATA_TYPE_PLACEHOLDER}
  value={uf.tableType}
  options={UPLOAD_DATA_TYPE_OPTIONS}
  disabled={isSubmitting}
  onChange={(v) => handleSetFileType(uf.id, v)}
/>

// JSX — 列表底部（替换原 isAnyUploading && <div className={styles.clearAllRow}>…）
<div className={styles.listFooterRow}>
  <Dropdown
    trigger={['click']}
    disabled={isSubmitting}
    overlay={
      <Menu>
        {UPLOAD_DATA_TYPE_OPTIONS.map((o) => (
          <Menu.Item key={o.value} onClick={() => handleSetAllTypes(o.value)}>
            {o.label}
          </Menu.Item>
        ))}
      </Menu>
    }
  >
    <button type="button" className={styles.bulkTypeBtn}>
      Set table type for all files to <DownOutlined />
    </button>
  </Dropdown>
  {isAnyUploading && (
    <button type="button" className={styles.clearAllBtn} onClick={handleClearAll}>
      Clear All
    </button>
  )}
</div>

// <Modal width={560} …> → width={640}
```

### W6. `ImportStatementsModal.less`（新增 / 改动）
```less
.notice {
  font-family: 'Futura-PT-Medium', sans-serif;
  font-size: 13px;
}

// .colFileSize / .fileSize / .progressWrap：flex 0 0 180px → 0 0 120px

.colTableType {
  flex: 0 0 128px;
  font-family: 'Futura-PT-Demi', sans-serif;
  font-size: 11px;
  color: #85878A;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.typeSelect {
  flex: 0 0 128px;
  width: 128px;
}

// 删除 .clearAllRow，改用：
.listFooterRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 8px;
}

.bulkTypeBtn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: 'Futura-PT-Demi', sans-serif;
  font-size: 13px;
  color: #E3910D;
}

@media (max-width: 575px) {
  // …既有规则保留
  .fileRow { flex-wrap: wrap; }
  .typeSelect { order: 1; flex: 1 1 100%; width: auto; } // 类型下拉换到第二行
  .colTableType { display: none; }
  .listFooterRow { flex-wrap: wrap; }
}
```

### W7. `DataMappingPanel.tsx`（片段）
```tsx
interface MetricSelectPanelProps {
  title: string;
  showUnmappedOption?: boolean;
  // 只选指标；类型跟随文件声明，不再提供 Actual / Forecast（需求 R7）
  onSelect: (lgCategory: string) => void;
}

// MetricSelectPanel 列表项（替换原 名称 + Actual + Forecast 三段）
{group.metrics.map((metric) => (
  <button
    key={metric}
    type="button"
    className={styles.mspMetricItem}
    onClick={() => onSelect(metric)}
  >
    {metric}
  </button>
))}

// AssignBtnProps / UnmappedRowProps / MappedCategoryProps
onAssign: (rowId: string, lgCategory: string) => void;

// AssignBtn 内
onSelect={(cat) => {
  onAssign(rowId, cat);
  setOpenId(null);
}}

const handleAssign = useCallback((rowId: string, lgCategory: string) => {
  const row = rowsByIdRef.current.get(rowId);
  if (!row || !onRowEdit) return;
  if (!row.effectiveIsMapped) dismissAssignHint();
  const isUnmap = lgCategory === UNMAPPED_OPTION_LABEL;
  const cellRefs = row.rawCellRefs.map(({ fileId, cellId }) => ({ fileId, cellId }));
  // 需求 R7：只改指标，不写 editSourceDataType——行的类型始终跟随所在文件的声明
  onRowEdit(cellRefs, { editLgCategory: isUnmap ? 'UNMAPPED' : lgCategory });
}, [onRowEdit, dismissAssignHint]);

// ── MonthPickerPopover：Actuals 行置灰当前月及以后（审核 D-9，dev-frontend §4.6）──
// 浏览器本地时间；与 Python（UTC）/ Java（服务器时区）月末几小时可能差一个月，可忽略
const currentMonthKey = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
};

const MonthPickerPopover: React.FC<{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (date: string) => void;
  // YYYY-MM：该月及以后不可选（Actuals 行传当前月；提交时 Java 会剔除这些月，见需求 R4）
  disableFromMonth?: string;
  children: React.ReactNode;
}> = ({ open, onOpenChange, onSelect, disableFromMonth, children }) => {
  // ...year 状态与翻页不变
        {MONTHS.map((m, i) => {
          const value = `${year}-${String(i + 1).padStart(2, '0')}`;
          return (
            <button
              key={m}
              className={styles.monthPickerCell}
              disabled={!!disableFromMonth && value >= disableFromMonth}
              onClick={() => {
                onSelect(value);
                onOpenChange(false);
              }}
            >
              {m}
            </button>
          );
        })}
  // ...Popover 包装不变
};

// 两处调用（NO DATE 行 :1107、推断月份行 :1160）各加一个 prop
<MonthPickerPopover
  open={selectingDate}
  onOpenChange={(v) => onSelectDate(v ? row.rowId : null)}
  onSelect={(date) => onSaveDate(row.rowId, date)}
  disableFromMonth={row.dataType === 'ACTUALS' ? currentMonthKey() : undefined}
>

// ── 空状态追加当前月说明（审核 D-10，dev-frontend §4.7）──
import { ACTUALS_CURRENT_MONTH_NOTE } from '../constants';

<div className={styles.emptyText}>
  No financial accounts found for the uploaded file. {ACTUALS_CURRENT_MONTH_NOTE}
</div>

// UploadSuccessModal.tsx（同样 import 常量），说明段落末尾追加
<p className={styles.desc}>
  No financial accounts extracted. {files.length} {fileWord} been uploaded to the
  Imported Statements folder in Documentation. {ACTUALS_CURRENT_MONTH_NOTE}
</p>
```

### W8. `DataMappingPanel.less`
```less
.mspMetricItem {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-bottom: 1px solid #F5F5F5;
  background: none;
  text-align: left;
  cursor: pointer;
  font-family: 'Futura-PT-Demi', sans-serif;
  font-size: 14px;
  color: #161A1d;
  transition: background 0.12s;
  &:hover { background: #f5f5f5; }
  &:last-child { border-bottom: none; }
}
// 删除：.mspMetricName / .mspOption / .mspDot / .mspDotActual / .mspDotForecast / .mspOptionText

// .monthPickerCell（:1076）内追加：Actuals 行的当前月及以后（审核 D-9）
.monthPickerCell {
  &:disabled,
  &:disabled:hover {
    border-color: #E8E8E8;
    background: #FAFAFA;
    color: #BFBFBF;
    cursor: not-allowed;
  }
}
```

### W9. `aiFinancialExtraction/types.ts`
```ts
// 编辑可写入的字段子集（与 RawCell 中的 editXxx 同名）。
// 不含 editSourceDataType：类型跟随文件声明、映射页不可改（需求 R7）；读侧 RawCell.editSourceDataType 保留给历史任务。
export interface EditFields {
  editAccountLabel?: string;
  editColumnMonth?: string;
  editLgCategory?: string;
  editUnitType?: string;
  editValue?: number | null;
}
```

### W10. `FileSelector.tsx`（FileHeaderBar 片段，Upload New Document 选类型的临时方案，待 Q2）
```tsx
import { Spin, Dropdown, Menu, Tooltip, Modal, Radio, Alert } from 'antd';
import type { FinancialDataType } from '@/services/api/ai/dto';
import { UPLOAD_ACCEPTED_EXTENSIONS, UPLOAD_DATA_TYPE_OPTIONS, ACTUALS_CURRENT_MONTH_NOTE } from '../constants';

// Props 与 FileHeaderBarProps
onUploadFiles?: (files: File[], dataType: FinancialDataType) => void;

// FileHeaderBar 内
const [typePickerOpen, setTypePickerOpen] = useState(false);
const [uploadType, setUploadType] = useState<FinancialDataType>();

const handleMenuClick = ({ key }: { key: React.Key }) => {
  if (key === 'delete' && onDeleteSelected) onDeleteSelected();
  if (key === 'upload' && onUploadFiles) {
    // 需求 R8：上传新文件先选类型；每次打开都清空（D7 无默认值）
    setUploadType(undefined);
    setTypePickerOpen(true);
  }
  if (key === 'replace' && onReplaceSelected) replaceInputRef.current?.click();
};

const handleTypePickerOk = () => {
  setTypePickerOpen(false);
  // 必须在 OK 点击的同步调用栈里打开文件框（浏览器要求用户手势），不能挪进 setTimeout / Promise / afterClose
  uploadInputRef.current?.click();
};

const handleUploadInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  const list = e.target.files;
  if (list && list.length > 0 && onUploadFiles && uploadType) {
    onUploadFiles(Array.from(list), uploadType);
  }
  e.target.value = '';  // 允许重复选同名文件
};

// JSX：放在 !readonly 的隐藏 input 片段内
<Modal
  visible={typePickerOpen}
  title="Upload New Document"
  okText="Select Files"
  okButtonProps={{ disabled: !uploadType }}
  onOk={handleTypePickerOk}
  onCancel={() => setTypePickerOpen(false)}
  centered
  destroyOnClose
>
  <p className={styles.typePickerText}>Select the table type for the files you are about to upload.</p>
  <Radio.Group
    className={styles.typePickerRadios}
    value={uploadType}
    onChange={(e) => setUploadType(e.target.value)}
  >
    {UPLOAD_DATA_TYPE_OPTIONS.map((o) => (
      <Radio key={o.value} value={o.value}>{o.label}</Radio>
    ))}
  </Radio.Group>
  <Alert type="info" showIcon message={ACTUALS_CURRENT_MONTH_NOTE} className={styles.typePickerNote} />
</Modal>
```
```less
// FileSelector.less
.typePickerText { margin: 0 0 12px; font-family: 'Futura-PT-Medium', sans-serif; font-size: 14px; color: #4E5153; }
.typePickerRadios { display: flex; gap: 24px; margin-bottom: 16px; }
.typePickerNote { font-family: 'Futura-PT-Medium', sans-serif; font-size: 13px; }
```

### W11. `AiFinancialExtractionPage.tsx` 与 `useOCRData.ts`
```tsx
// AiFinancialExtractionPage.tsx :760-767
onUploadFiles={
  readonly
    ? undefined
    : (rawFiles, dataType) =>
        uploadAdditionalFiles(rawFiles, dataType).catch((err) => {
          console.error('[uploadAdditionalFiles] failed', err);
        })
}
```
```ts
// useOCRData.ts
import type { FinancialDataType } from '@/services/api/ai/dto';

const uploadAdditionalFiles = useCallback(
  async (
    rawFiles: File[],
    dataType: FinancialDataType, // 映射页 Upload New Document 选的类型，本次所有文件共用（需求 R8）
  ): Promise<{ accepted: number; rejected: number }> => {
    // …校验不变
    const urlResp = await getAiUploadUrl({
      companyId,
      taskId,
      fileList: accepted.map((f) => ({ fileName: f.name, length: f.size, dataType })),
    });
    // …其余不变
  },
  [companyId, taskId, files, startPolling],
);
// replaceFile 的 getAiUploadUrl 保持不带 dataType（Java 在 file/replace 里继承旧文件类型）
```

### W12. 单测骨架：`ImportStatementsModal.test.tsx`
```tsx
import React from 'react';
import '@testing-library/jest-dom';
import { render, fireEvent, screen, waitFor, act } from '@testing-library/react';
import ImportStatementsModal from './ImportStatementsModal';
import { getAiUploadUrl, commitUpload } from '@/services/service/ai/aiService';

jest.mock('@/services/service/ai/aiService', () => ({
  getAiUploadUrl: jest.fn(),
  commitUpload: jest.fn(),
  batchDeleteFilesByIds: jest.fn().mockResolvedValue({ success: true }),
}));
jest.mock('@/pages/financial/aiFinancialExtraction/utils/uploadValidation', () => ({
  validateFiles: (files: File[]) => ({ accepted: files, errors: [] }),
  filterByMagicNumber: async (files: File[]) => ({ ok: files, corrupted: [] }),
}));
jest.mock('@/pages/financial/aiFinancialExtraction/components/UploadErrorToast', () => ({
  __esModule: true,
  default: () => null,
  pushUploadError: jest.fn(),
}));

// S3 直传：send() 后异步触发 load(200)
class FakeXHR {
  status = 200;
  upload = { addEventListener: () => undefined };
  private handlers: Record<string, () => void> = {};
  addEventListener(type: string, cb: () => void) { this.handlers[type] = cb; }
  open() {}
  setRequestHeader() {}
  send() { setTimeout(() => this.handlers.load?.(), 0); }
  abort() { this.handlers.abort?.(); }
}

// ⑦ 专用：send() 不触发 load，文件停在上传中；abort() 沿用父类，触发组件注册的 abort 分支（审核 C-20）
class HangingXHR extends FakeXHR {
  static instances: HangingXHR[] = [];
  aborted = false;
  constructor() { super(); HangingXHR.instances.push(this); }
  send() {}
  abort() { this.aborted = true; super.abort(); }
}

const mockGetUploadUrl = getAiUploadUrl as jest.Mock;
const mockCommit = commitUpload as jest.Mock;
const fileOf = (name: string) => new File(['abc'], name);
const nextBtn = () => screen.getByRole('button', { name: 'Next' });

const renderModal = () =>
  render(<ImportStatementsModal visible companyId="c-1" onCancel={jest.fn()} onNext={jest.fn()} />);

async function addFiles(names: string[]) {
  const input = document.body.querySelector('input[type="file"]') as HTMLInputElement;
  await act(async () => {
    fireEvent.change(input, { target: { files: names.map(fileOf) } });
  });
  // 进度百分比消失 = 全部 done；多行同时上传时 queryByText 会因多个匹配而抛错，改用 queryAllByText（审核 C-21）
  await waitFor(() => expect(screen.queryAllByText(/%$/)).toHaveLength(0));
}

function pickRowType(rowIndex: number, label: string) {
  fireEvent.mouseDown(screen.getAllByRole('combobox')[rowIndex]);
  const option = document.body.querySelector(
    `.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[title="${label}"]`,
  ) as HTMLElement;
  fireEvent.click(option);
}

function bulkSet(label: string) {
  fireEvent.click(screen.getByText(/Set table type for all files to/));
  const item = Array.from(
    document.body.querySelectorAll('.ant-dropdown:not(.ant-dropdown-hidden) .ant-dropdown-menu-item'),
  ).find((el) => el.textContent === label) as HTMLElement;
  fireEvent.click(item);
}

beforeEach(() => {
  Object.defineProperty(window, 'XMLHttpRequest', { value: FakeXHR, writable: true });
  mockGetUploadUrl.mockReset().mockImplementation(async ({ fileList }: { fileList: { fileName: string }[] }) => ({
    success: true,
    data: {
      taskId: null,
      items: fileList.map((f) => ({
        fileId: `id-${f.fileName}`, originalFileName: f.fileName, objectKey: '',
        httpMethod: 'PUT', uploadUrl: 'https://s3.test/put', requiredHeaders: {}, expiresInSeconds: 600,
      })),
    },
  }));
  mockCommit.mockReset().mockResolvedValue({
    success: true, data: { taskId: 't-1', committedFileIds: [], missingFileIds: [] },
  });
});

it('未全部选类型时 Next 不可用，选齐后可用', async () => {
  renderModal();
  await addFiles(['a.xlsx', 'b.xlsx']);
  expect(nextBtn()).toBeDisabled();
  pickRowType(0, 'Actuals');
  expect(nextBtn()).toBeDisabled();
  pickRowType(1, 'Proforma');
  expect(nextBtn()).toBeEnabled();
});

it('批量设置后逐行改，Next 提交每个文件的类型', async () => {
  renderModal();
  await addFiles(['a.xlsx', 'b.xlsx']);
  bulkSet('Actuals');
  pickRowType(1, 'Proforma');
  await act(async () => { fireEvent.click(nextBtn()); });
  expect(mockCommit).toHaveBeenCalledWith({
    companyId: 'c-1',
    files: [
      { fileId: 'id-a.xlsx', dataType: 'ACTUALS' },
      { fileId: 'id-b.xlsx', dataType: 'PROFORMA' },
    ],
  });
});

it('批量设置之后新加的文件保持未选', async () => {
  renderModal();
  await addFiles(['a.xlsx']);
  bulkSet('Proforma');
  await addFiles(['b.xlsx']);
  expect(nextBtn()).toBeDisabled();
});

it('顶部固定显示 Actuals 当月说明', () => {
  renderModal();
  expect(
    screen.getByText('For Actuals files, data for the current month and later is not extracted.'),
  ).toBeInTheDocument();
});

it('上传中 Clear All 只清上传中的文件（行为回归，审核 C-20）', async () => {
  renderModal();
  await addFiles(['a.xlsx']); // FakeXHR 自动 load → a 已 done
  HangingXHR.instances = [];
  Object.defineProperty(window, 'XMLHttpRequest', { value: HangingXHR, writable: true });
  const input = document.body.querySelector('input[type="file"]') as HTMLInputElement;
  await act(async () => {
    fireEvent.change(input, { target: { files: [fileOf('b.xlsx')] } });
  });
  await waitFor(() => expect(HangingXHR.instances).toHaveLength(1)); // b 的 XHR 已发出、停在上传中
  fireEvent.click(screen.getByRole('button', { name: 'Clear All' }));
  expect(HangingXHR.instances[0].aborted).toBe(true);
  expect(screen.queryByText('b.xlsx')).toBeNull();
  expect(screen.getByText('a.xlsx')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Clear All' })).toBeNull();
});

it('只有一个文件：批量设置照常显示，选好类型后 Next 可用（审核 D-13）', async () => {
  renderModal();
  await addFiles(['a.xlsx']);
  expect(screen.getByText(/Set table type for all files to/)).toBeInTheDocument();
  expect(nextBtn()).toBeDisabled();
  pickRowType(0, 'Actuals');
  expect(nextBtn()).toBeEnabled();
});
```

### W13. 单测骨架：`FileSelector.test.tsx`（关键用例）
```tsx
import React from 'react';
// toBeDisabled 来自 jest-dom；jest.config.js 无 setupFilesAfterEnv，须逐文件显式引入（先例 AssessmentPage.test.tsx）（审核 C-19）
import '@testing-library/jest-dom';
import { render, fireEvent, screen } from '@testing-library/react';
import FileSelector from './FileSelector';

// 关键用例体（写在 it(...) 内）
const clickSpy = jest.spyOn(HTMLInputElement.prototype, 'click').mockImplementation(() => undefined);
render(
  <FileSelector files={twoReadyFiles} uploadStage="done" fromModal selectedFileId={null}
    onSelectFile={jest.fn()} onCollapse={jest.fn()} onUploadFiles={onUploadFiles} />,
);
fireEvent.click(screen.getByAltText('dots'));
fireEvent.click(screen.getByText('Upload New Document'));
const ok = screen.getByRole('button', { name: 'Select Files' });
expect(ok).toBeDisabled();
expect(clickSpy).not.toHaveBeenCalled();
fireEvent.click(screen.getByLabelText('Proforma'));
fireEvent.click(ok);
expect(clickSpy).toHaveBeenCalledTimes(1); // 同步打开文件框
const input = document.body.querySelector('input[type="file"][multiple]') as HTMLInputElement;
const f = new File(['x'], 'c.xlsx');
fireEvent.change(input, { target: { files: [f] } });
expect(onUploadFiles).toHaveBeenCalledWith([f], 'PROFORMA');
```

### W14. 单测骨架：`useOCRData.test.tsx`（harness 写法，仓库没有 renderHook）
```tsx
import { getAiUploadUrl } from '@/services/service/ai/aiService';
jest.mock('umi', () => ({ history: { push: jest.fn() } }));
jest.mock('@/services/service/ai/aiService', () => ({
  getAiUploadUrl: jest.fn(), pullExtractData: jest.fn(), pullExtractDataIncrement: jest.fn(),
  notifyUploadComplete: jest.fn(), putFileToS3: jest.fn(), batchDeleteFiles: jest.fn(), replaceFile: jest.fn(),
}));
jest.mock('@/services/service/storage/storageService', () => ({ verifyS3Files: jest.fn() }));
jest.mock('@/services/service/financialExtract/financialExtractTaskService', () => ({ fetchReadonlyExtractData: jest.fn() }));
jest.mock('../utils/uploadValidation', () => ({
  validateFiles: (files: File[]) => ({ accepted: files, errors: [] }),
  filterByMagicNumber: async (files: File[]) => ({ ok: files, corrupted: [] }),
  checkFileMagic: async () => true,
  activeUploadNames: () => new Set<string>(),
}));
jest.mock('../components/UploadErrorToast', () => ({ pushUploadError: jest.fn() }));

const mockGetUploadUrl = getAiUploadUrl as jest.Mock;
// jest.config.js 没开 clearMocks / resetMocks：每例前清掉上一例的调用记录，否则 replaceFile 用例读到的 calls[0] 是上一例 uploadAdditionalFiles 的（审核 C-2）
beforeEach(() => mockGetUploadUrl.mockReset());

let api: ReturnType<typeof useOCRData>;
const Harness: React.FC = () => { api = useOCRData(); return null; };
// 用 ReactDOM.render(<Harness />, container) 挂载（同 useMemoryData.test.tsx）

it('uploadAdditionalFiles 把类型带进每个 fileList 项', async () => {
  mockGetUploadUrl.mockResolvedValue({ success: false });
  await act(async () => { await api.uploadAdditionalFiles([new File(['x'], 'a.xlsx')], 'ACTUALS'); });
  expect(mockGetUploadUrl.mock.calls[0][0].fileList).toEqual([{ fileName: 'a.xlsx', length: 1, dataType: 'ACTUALS' }]);
});

it('replaceFile 不带 dataType（继承被替换文件）', async () => {
  mockGetUploadUrl.mockResolvedValue({ success: false });
  await act(async () => { await api.replaceFile('old-1', new File(['x'], 'b.xlsx')); });
  expect(mockGetUploadUrl.mock.calls[0][0].fileList[0]).not.toHaveProperty('dataType');
});
```

`DataMappingPanel.test.tsx` 只在 [dev-frontend](./dev-frontend.md) §7 用文字描述：造一个 `REVIEW_READY` 文件，里面一行带月份和数值的未映射 PROFORMA 数据；点 `.assignDropBtn`（identity-obj-proxy 原样映射类名），断言下拉里没有 "Actual"、"Forecast"；点 "Gross Revenue"，断言 `onRowEdit` 收到 `([{fileId:'f1',cellId:'c1'}], { editLgCategory: 'Gross Revenue' })`。
