# Excel 解析优化 · 前端设计

> 关联文档: [设计理念](./design-philosophy.md) · [Python 端设计](./python-design.md) · [代码示例](./code-examples.md)
> 上游文档: [智能解析前端设计](../../智能解析/调研/frontend-design.md) · [Manual Uploads with OCR 需求文档](../../智能解析/Manual_Uploads_with_OCR_需求文档.md)
>
> 范围: 仅 P0 步 1"跳过可见"涉及前端；其余方案前端零改动。代码基线 CIOaas-web `src/pages/financial/aiFinancialExtraction/`。

## 一、现状

| 现状 | 位置 |
|---|---|
| 文件级失败弹窗 `FileProcessingErrorsModal` 只渲染文件名，**不渲染 `f.error`** | `components/FileProcessingErrorsModal.tsx:42-48` |
| `FileSelector` 对 FILE_FAILED 项已挂 Tooltip `f.error \|\| 'Parse error'`，失败项不可选中 | `components/FileSelector.tsx:84-88`、`:193-197` |
| 只读回放页显示 `f.error` | `AiFinancialExtractionPage.tsx:727` |
| 前端只认 `REVIEW_READY` / `FILE_FAILED` 两态，其余视为处理中 | `hooks/useOCRData.ts:125-129` |
| 没有任何 sheet 级信号：sheet 被跳过、表被跳过、输出截断，前端无字段可展示 | `services/api/ai/aiService.ts:252-300` RawFileResult 无 warning / sheet 字段 |
| 需求 §3.4 的 Excel 多 Sheet Tab 导航与来源定位 tooltip 未实现；`parseXlsx.ts` 已标死代码 | `utils/parseXlsx.ts:1-7` |

## 二、改动

| 改动 | 位置 | 说明 |
|---|---|---|
| `RawFileResult` 新增可选 `warning?: string` | `services/api/ai/aiService.ts` | 对应 Python `ExtractFileItem.warning`（只新增字段，既有字段名逐字不变） |
| 数据映射区顶部非阻断黄色横幅：文件 `warning` 非空即展示，可关闭 | `AiFinancialExtractionPage.tsx` 或 `DataMappingPanel.tsx` 顶部 | 文案示例：`Sheet "GL Detail" was skipped: more than 2,000 rows.` / `Table "P&L" may be incomplete: 1 chunk truncated.` 行数用 "more than 2,000 rows"（预检 early-exit 只知下界） |
| `FileSelector` 文件项在 `warning` 非空时加 ⚠ 图标 + Tooltip | `components/FileSelector.tsx` | 与失败项 Tooltip 同一视觉语言，颜色区分（警告 vs 失败） |
| `FileProcessingErrorsModal` 渲染 `f.error` | `components/FileProcessingErrorsModal.tsx:42-48` | 字段已存在未展示；顺手修 |
| devSupport 只读回放页显示 `warning` | `src/pages/devSupport/financialExtract/` | 与 Python `financial_extract` 管理域 DTO 同步 |

不改状态机、不改轮询逻辑、不改 `status` 语义：`warning` 非空的文件仍是 `REVIEW_READY`。

## 三、文案与归属

- reason 枚举（Python 侧）→ 文案映射建议放前端常量表，便于本地化：`too_many_rows` / `non_financial_prefilter` / `classified_non_financial` / `table_over_budget` / `truncated` / `partial_chunk_failed`。
- 现状口径是 Python 直出英文文案（`error_message` 亦如此），与 `user-input-requirements.md` R-2.2"用户可见错误由 Java 生成"相悖；本次沿用现状口径，归属问题留待负责人拍板（见[设计理念 §六](./design-philosophy.md#六未决问题需负责人拍板)）。

## 四、不在本次范围

- Excel 多 Sheet Tab 导航、右侧行回溯到左侧 sheet/单元格（需 `mapping_data` 新增 sheet 名与坐标列，属 P1 #6 稳定行 id 落地后的后续项）。
- GL 聚合轨的"派生聚合行"标记展示（P2，取决于产品拍板）。
