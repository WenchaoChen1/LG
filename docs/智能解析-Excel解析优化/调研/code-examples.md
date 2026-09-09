# Excel 解析优化 · 代码示例

> 关联文档: [设计理念](./design-philosophy.md) · [Python 端设计](./python-design.md) · [前端设计](./frontend-design.md)
>
> 本文只放 DDL 与参考片段，设计文档正文不重复。全部对应 [Python 端设计 §六](./python-design.md#六p0-落地步骤python-侧) P0 步 1、步 2。

## 一、SQL：`ai_file_registry` 新增 warning 列（业务库迁移 V023）

```sql
-- sql/migrations/business/V023__ai_file_registry_warning_message.sql
-- 幂等；error_message 已是 TEXT，warning 同型（30 sheet 工作簿多条跳过 + 截断表 id 拼接易超 VARCHAR(500)）
ALTER TABLE ai_file_registry
    ADD COLUMN IF NOT EXISTS warning_message TEXT;

COMMENT ON COLUMN ai_file_registry.warning_message IS
    'Non-fatal extraction warnings (skipped sheets / skipped tables / truncated output), newline-separated; file status stays REVIEW_READY';
```

ORM（`source/lg/db/models/models.py` 的 `AiFileRegistry`）同步加列，实体内注释用中文（落库 COMMENT 用英文）。

## 二、Python：state 形状

```python
# state.py  MainGraphState / ExcelSheetInfo 追加（不声明会被 LangGraph 静默丢弃）
skipped_sheets: NotRequired[list[dict]]   # [{"sheet_name": str, "row_count": int, "reason": str}]
warning_message: NotRequired[str]         # refine 汇总后的用户可见告警，不进 error_message

# node_return.py  ExcelPreprocessReturn / RefineExtractionReturn 同步声明上述两键
```

`reason` 枚举：`too_many_rows` · `non_financial_prefilter` · `classified_non_financial` · `table_over_budget` · `truncated` · `partial_chunk_failed`。

## 三、Python：read_only 预检（只做 early-exit，未触发者走 `_logical_size` 终判）

```python
def _prescan_oversized_sheets(local_path: Path, cap: int) -> set[str]:
    """返回非空行数 > cap 的 sheet 名。只按 values_only 的 notna 计数，恒 ≤ _logical_size 的
    notna ∪ merged-range 口径，故「预检超限 ⇒ 终判必超限」单向成立，不会新增误跳。
    禁止用 ws.max_row（读的是 dimension 标签，仅格式的远端 cell 会撑到数万行）。"""
    from openpyxl import load_workbook

    oversized: set[str] = set()
    wb = load_workbook(str(local_path), read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            n = 0
            for row in ws.iter_rows(values_only=True):
                if any(v is not None for v in row):
                    n += 1
                    if n > cap:
                        oversized.add(ws.title)
                        break
    finally:
        wb.close()
    return oversized
```

注意：`read_only=True` 的 worksheet 没有 `merged_cells`，元数据通道（`_read_workbook_metadata`）不能整体换成只读模式；预检只省 pandas 一遍与 `_logical_size` 双循环，不承诺内存下降。

## 四、Python：Plan D 可达（预算扣上下文行）

```python
# _slice_sheet_html_by_rows 内
ctx_cells = (len(full_context_indices) + len(ancestors)) * logical_width
data_rows_per_chunk = (cell_budget - ctx_cells) // logical_width
if data_rows_per_chunk < 1:
    return None   # 真正的 Plan D：表头 + 1 数据行已超预算 → 调用方按差集判 skipped
```

必须与"跳过可见"同批上线，否则极宽表从"部分产出"变"零产出"且用户无感知。
