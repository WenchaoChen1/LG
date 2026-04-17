# OCR Agent 前端设计

> **技术栈**: React 16 + Ant Design Pro v4 + UmiJS 3 + dva + TypeScript
> **关联文档**: [系统架构](./system-architecture.md) · [Java 端设计](./java-design.md) · [Python 端设计](./python-design.md) · [代码示例](./code-examples.md)

## 与后端交互

前端调用的 Java API 一览：

```
POST   /api/v1/docparse/upload              → UploadPage
GET    /api/v1/docparse/tasks/{id}/status    → ProcessingPage (polling)
GET    /api/v1/docparse/tasks/{id}/result    → ReviewPage
PATCH  /api/v1/docparse/tasks/{id}/review    → ReviewPage (auto-save)
POST   /api/v1/docparse/tasks/{id}/confirm   → ConfirmPage
```

## 1. 页面路由

所有页面挂载在 `/financial` 路由前缀下，通过 `sessionId` 串联完整流程：

```
路由                                  组件               说明
────────────────────────────────────────────────────────────────────────────
/financial/upload                    UploadPage          Step 1: 文件上传 + 队列管理
/financial/upload/:sessionId         ProcessingPage      Step 2: AI 提取进度（自动跳转）
/financial/review/:sessionId         ReviewPage          Step 3: 并排审核 + 内联编辑（核心页面）
/financial/confirm/:sessionId        ConfirmPage         Step 4+5: 冲突解决 + 最终提交
```

**UmiJS 路由配置** (`config/routes.ts`):

```typescript
{
  path: '/financial',
  routes: [
    {
      path: '/financial/upload',
      component: './Financial/Upload/UploadPage',
      name: 'financial-upload',
    },
    {
      path: '/financial/upload/:sessionId',
      component: './Financial/Upload/ProcessingPage',
      name: 'financial-processing',
    },
    {
      path: '/financial/review/:sessionId',
      component: './Financial/Review/ReviewPage',
      name: 'financial-review',
    },
    {
      path: '/financial/confirm/:sessionId',
      component: './Financial/Confirm/ConfirmPage',
      name: 'financial-confirm',
    },
  ],
}
```

**导航守卫**:
- `ProcessingPage`: 如果 session 状态已是 `COMPLETED`，直接 `history.replace` 到 ReviewPage
- `ReviewPage`: 如果 session 状态不是 `COMPLETED`，重定向回 ProcessingPage
- `ConfirmPage`: 如果存在未通过的硬验证，重定向回 ReviewPage 并显示错误提示

## 2. 组件层级

#### UploadPage

```
UploadPage
  ├── UploadZone
  │     拖拽区域 + 文件选择按钮
  │     支持格式提示: PDF, Excel (.xlsx/.xls), CSV, 图片 (PNG/JPG)
  │     单文件 ≤ 20MB，批量 ≤ 100MB
  │
  ├── FileQueue
  │     └── FileQueueItem (每个上传文件)
  │           ├── 文件图标 (根据 MIME 类型)
  │           ├── 文件名 + 文件大小
  │           ├── 文件类型标签 (PDF / Excel / CSV / Image)
  │           ├── 进度条 (antd Progress, 上传中显示百分比)
  │           ├── 状态徽章 (Pending / Uploading / Completed / Error)
  │           └── 删除按钮 (上传完成前可移除)
  │
  └── BatchActions
        ├── Upload All 按钮 (primary, 触发批量上传)
        └── Clear All 按钮 (danger-link, 清空队列)
```

**UploadZone 组件行为**:
- 使用 antd `Upload.Dragger` 作为基础，自定义样式
- 拖拽时高亮边框变为 `primary` 色
- 客户端预校验：文件类型（MIME + 扩展名双检）、单文件大小、总大小
- 校验失败立即在 FileQueueItem 上显示 Error 状态 + 原因文案
- 重复文件检测（同名 + 同大小），提示用户确认是否重复上传

#### ProcessingPage

```
ProcessingPage
  ├── SessionHeader
  │     上传会话 ID + 文件数量摘要
  │
  ├── ProcessingStatus
  │     ├── 整体进度条 (总百分比)
  │     ├── 当前步骤描述
  │     │     PENDING    → "排队等待处理..."
  │     │     PROCESSING → "正在进行 AI 提取... (已完成 45%)"
  │     │     COMPLETED  → "提取完成，正在跳转..." (自动 redirect)
  │     │     FAILED     → "处理失败"
  │     └── 文件级进度列表
  │           └── FileProcessItem (每个文件: 名称 + 状态 + 进度)
  │
  └── ErrorActions (仅 FAILED 时显示)
        ├── RetryButton (重新触发提取)
        └── BackButton (返回上传页重新上传)
```

#### ReviewPage（核心页面）

```
ReviewPage
  ├── TableSelector
  │     antd Tabs 组件
  │     Tab 1: "Income Statement (2024_PnL.pdf)" / Tab 2: "Balance Sheet (BS.xlsx)" / ...
  │     每个 Tab 显示: 表名 + 来源文件名 + 置信度汇总 (✓ 12 / ⚠ 5 / ✗ 2)
  │
  ├── SplitView (antd Row + Col, 可拖拽分割线, 默认 50/50)
  │     │
  │     ├── SourcePanel（左侧 — 原始文档）
  │     │     ├── PDFViewer
  │     │     │     react-pdf 渲染
  │     │     │     页码导航: 上一页 / 下一页 / 页码输入跳转
  │     │     │     缩放控制: 放大 / 缩小 / 适应宽度
  │     │     │     当前高亮区域标记 (对应右侧选中行的源位置)
  │     │     │
  │     │     └── ExcelPreview
  │     │           antd Table 只读渲染
  │     │           Sheet 切换标签页 (多 sheet 时)
  │     │           高亮行 (对应右侧选中行的源单元格)
  │     │           合并单元格正确渲染 (colSpan/rowSpan)
  │     │
  │     └── DataPanel（右侧 — 提取数据）
  │           ├── ViewToggle
  │           │     antd Radio.Group: [Raw] [Standardized]
  │           │     Raw: 显示 AI 提取的原始行标签和值
  │           │     Standardized: 显示映射后的 LG 分类、标准化数值
  │           │
  │           ├── EditableTable
  │           │     基于 react-window FixedSizeList 虚拟滚动
  │           │     列定义:
  │           │       - Row #（行号，只读）
  │           │       - Account Label（Raw 视图）/ LG Category（Standardized 视图）
  │           │       - 各月份/期间列（动态，从 reporting_periods 生成）
  │           │       - Confidence（置信度徽章）
  │           │       - Actions（删除行按钮）
  │           │     │
  │           │     ├── EditableCell
  │           │     │     默认: 纯文本渲染 (<span>)
  │           │     │     双击: 切换为 <Input> 受控模式
  │           │     │     失焦/回车: 保存编辑，切回文本
  │           │     │     修改后的单元格左上角显示蓝色三角标记
  │           │     │
  │           │     ├── CategoryDropdown
  │           │     │     仅 Standardized 视图可见
  │           │     │     antd Select, 19 个 LG 分类选项 + 分组:
  │           │     │       Income Statement: Revenue, COGS, S&M Expenses, R&D Expenses,
  │           │     │         G&A Expenses, S&M Payroll, R&D Payroll, G&A Payroll,
  │           │     │         Other Income, Other Expense
  │           │     │       Balance Sheet: Cash, Accounts Receivable, R&D Capitalized,
  │           │     │         Other Assets, Accounts Payable, Short Term Debt,
  │           │     │         Long Term Debt, Other Liabilities, Equity
  │           │     │     选择后立即标记为 user_override, confidence 变为 HIGH
  │           │     │
  │           │     └── ConfidenceBadge
  │           │           ✓ HIGH   — 绿色 Tag (antd Tag color="success")
  │           │           ⚠ MEDIUM — 橙色 Tag (antd Tag color="warning")
  │           │           ✗ UNMAPPED — 红色 Tag (antd Tag color="error")
  │           │           点击展开 Tooltip: 显示 mapping source + reasoning
  │           │
  │           └── ValidationBar (固定在 DataPanel 底部)
  │                 错误计数: "3 errors" (红色) + 警告计数: "5 warnings" (橙色)
  │                 点击展开详细列表，每条可点击定位到对应行
  │
  └── ActionBar (固定在页面底部)
        ├── Previous 按钮 (返回 ProcessingPage 或 UploadPage)
        ├── Save Draft 按钮 (手动触发保存，通常自动保存已覆盖)
        └── Next: Confirm 按钮 (primary, 触发硬验证后跳转 ConfirmPage)
```

**SplitView 分割线交互**:
- 默认 50/50 比例
- 鼠标拖拽分割线调整比例，最小 30%，最大 70%
- 双击分割线恢复 50/50
- 比例存储在 `localStorage` 中，刷新后保持

#### ConfirmPage

```
ConfirmPage
  ├── WriteSummary
  │     信息卡片列表:
  │     ├── 待写入表数量 (e.g. "2 tables")
  │     ├── 时间范围 (e.g. "Jan 2024 - Dec 2024")
  │     ├── 数据类型 (Historical / Forecast / Mixed)
  │     ├── 总行数统计
  │     └── 修改摘要 (用户编辑 N 行, 映射覆盖 M 条)
  │
  ├── ConflictList (仅冲突检测到时显示)
  │     ├── 冲突摘要: "发现 N 条与已有数据的冲突"
  │     └── ConflictItem (每条冲突)
  │           ├── 冲突位置: Table / Account / Period
  │           ├── 对比展示:
  │           │     已有值: $1,234,567 (source: QuickBooks, date: 2024-01-15)
  │           │     新值:   $1,234,890 (source: 当前上传)
  │           ├── 解决方案: antd Radio.Group
  │           │     ○ Overwrite (用新值覆盖)
  │           │     ○ Skip (保留已有值)
  │           │     ○ Cancel (从本次提交中移除此行)
  │           └── Note 字段: antd TextArea (≤ 2000 字, 可选)
  │                 placeholder: "说明覆盖原因..."
  │
  └── CommitButton
        antd Button type="primary" size="large"
        无冲突时: "Confirm & Write to LG"
        有冲突时: 所有冲突项必须选择解决方案后才可点击
        点击后: Loading 状态 → 成功跳转到 Success 页 / 失败显示错误
```

**Note 字段**

来自 Asana Story #7：冲突解决步骤可选添加 Note（≤2000 字符），记录修改原因。

```
ConflictItem
  ├── 字段对比（已有值 vs 新值）
  ├── 解决方案选择 (Overwrite / Skip / Cancel)
  └── NoteField (可选)
        ├── Textarea (placeholder: "解释为何这样处理冲突，可选")
        └── CharCount (0/2000)
```

**Note 查看入口**：写入 fi_* 后，Note 关联到该 upload event，在 Financial Statements 模块的 Financial Entry 页面新增 **"导入备注"折叠面板**，展示历史所有冲突解决的备注（按时间倒序）。

## 3. dva Model 设计

#### State 接口定义

```typescript
/** 上传文件项 */
interface UploadFileItem {
  uid: string;                    // 前端唯一标识
  fileId?: string;                // 后端返回的文件 ID
  fileName: string;
  fileType: 'pdf' | 'excel' | 'csv' | 'image';
  fileSize: number;               // bytes
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;               // 0-100
  errorMessage?: string;
  originFile: File;               // 原始 File 对象（不持久化）
}

/** 提取的表格 */
interface ExtractedTable {
  tableId: string;
  fileName: string;               // 来源文件名
  documentType: 'income_statement' | 'balance_sheet' | 'cash_flow_statement' | 'misc';
  docTypeConfidence: 'HIGH' | 'MEDIUM' | 'LOW';
  currency: string;
  reportingPeriods: string[];     // e.g. ["2024-01", "2024-02", ...]
  rows: ExtractedRow[];
}

/** 提取的行 */
interface ExtractedRow {
  rowId: string;
  accountLabel: string;           // 原始标签
  values: Record<string, number | null>;  // period → value
  isHeader: boolean;
  isTotal: boolean;
  sectionHeader?: string;         // 所属段落标题
  sourcePageNumber?: number;      // PDF 页码（用于左侧定位）
  sourceRowIndex?: number;        // Excel 行号（用于左侧高亮）
}

/** 映射结果 */
interface MappingResult {
  rowId: string;
  lgCategory: string;             // 19 个 LG 分类之一
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNMAPPED';
  source: 'rule_engine' | 'company_memory' | 'llm' | 'user_override';
  reasoning: string;
  originalAiSuggestion?: string;  // 用户覆盖前的原始建议
}

/** 用户编辑记录 */
interface RowEdit {
  rowId: string;
  field: string;                  // 'accountLabel' | period key
  oldValue: string | number | null;
  newValue: string | number | null;
}

/** 映射覆盖记录 */
interface MappingOverride {
  rowId: string;
  oldCategory: string;
  newCategory: string;
}

/** 冲突项 */
interface ConflictItem {
  conflictId: string;
  tableId: string;
  accountLabel: string;
  period: string;
  existingValue: number;
  existingSource: string;         // e.g. "QuickBooks"
  existingDate: string;           // 写入时间
  newValue: number;
  resolution?: 'overwrite' | 'skip' | 'cancel';
  note?: string;
}

/** 会话状态 */
interface SessionStatus {
  sessionId: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress: number;               // 0-100
  errorMessage?: string;
}

/** 验证错误 */
interface ValidationError {
  rowId: string;
  tableId: string;
  tableName: string;
  fileName: string;
  rowIndex: number;
  field: string;
  message: string;
}

/** 验证警告 */
interface ValidationWarning {
  rowId: string;
  tableId: string;
  field: string;
  message: string;
}

/** dva model state */
interface FinancialUploadModelState {
  // Upload
  fileList: UploadFileItem[];
  sessionId: string | null;

  // Processing
  sessionStatus: SessionStatus | null;
  pollingTimer: ReturnType<typeof setInterval> | null;  // 内部使用，不持久化

  // Review
  extractedTables: ExtractedTable[];
  mappingResults: Record<string, MappingResult>;  // rowId → MappingResult
  activeTableId: string | null;
  viewMode: 'raw' | 'standardized';
  editedRows: RowEdit[];
  mappingOverrides: MappingOverride[];
  selectedRowId: string | null;
  validationErrors: ValidationError[];
  validationWarnings: ValidationWarning[];

  // Auto-save
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  hasUnsavedChanges: boolean;

  // Confirm
  conflicts: ConflictItem[];
  commitStatus: 'idle' | 'committing' | 'success' | 'error';
  commitErrorMessage?: string;
}
```

#### Key Reducers

```typescript
reducers: {
  /** 设置文件列表（添加/移除文件） */
  setFileList(state, { payload }: { payload: UploadFileItem[] }) {
    return { ...state, fileList: payload };
  },

  /** 更新单个文件的上传进度 */
  updateUploadProgress(state, { payload }: { payload: { uid: string; progress: number; status?: string } }) {
    return {
      ...state,
      fileList: state.fileList.map(f =>
        f.uid === payload.uid
          ? { ...f, progress: payload.progress, ...(payload.status && { status: payload.status }) }
          : f
      ),
    };
  },

  /** 设置 AI 提取结果 */
  setExtractedTables(state, { payload }: { payload: { tables: ExtractedTable[]; mappings: Record<string, MappingResult> } }) {
    return {
      ...state,
      extractedTables: payload.tables,
      mappingResults: payload.mappings,
      activeTableId: payload.tables[0]?.tableId ?? null,
    };
  },

  /** 更新行数据（内联编辑） */
  updateRow(state, { payload }: { payload: RowEdit }) {
    const { rowId, field, oldValue, newValue } = payload;
    return {
      ...state,
      extractedTables: state.extractedTables.map(table => ({
        ...table,
        rows: table.rows.map(row =>
          row.rowId === rowId
            ? {
                ...row,
                ...(field === 'accountLabel'
                  ? { accountLabel: newValue as string }
                  : { values: { ...row.values, [field]: newValue as number } }),
              }
            : row
        ),
      })),
      editedRows: [...state.editedRows, payload],
      hasUnsavedChanges: true,
      saveStatus: 'idle' as const,
    };
  },

  /** 覆盖映射分类 */
  overrideMapping(state, { payload }: { payload: MappingOverride }) {
    return {
      ...state,
      mappingResults: {
        ...state.mappingResults,
        [payload.rowId]: {
          ...state.mappingResults[payload.rowId],
          lgCategory: payload.newCategory,
          confidence: 'HIGH',
          source: 'user_override',
          originalAiSuggestion: state.mappingResults[payload.rowId]?.lgCategory,
        },
      },
      mappingOverrides: [...state.mappingOverrides, payload],
      hasUnsavedChanges: true,
      saveStatus: 'idle' as const,
    };
  },

  /** 设置冲突解决方案 */
  setConflictResolution(state, { payload }: { payload: { conflictId: string; resolution: string; note?: string } }) {
    return {
      ...state,
      conflicts: state.conflicts.map(c =>
        c.conflictId === payload.conflictId
          ? { ...c, resolution: payload.resolution, note: payload.note }
          : c
      ),
    };
  },

  /** 设置会话状态（轮询更新） */
  setSessionStatus(state, { payload }: { payload: SessionStatus }) {
    return { ...state, sessionStatus: payload };
  },

  /** 设置保存状态 */
  setSaveStatus(state, { payload }: { payload: 'idle' | 'saving' | 'saved' | 'error' }) {
    return {
      ...state,
      saveStatus: payload,
      hasUnsavedChanges: payload === 'saved' ? false : state.hasUnsavedChanges,
    };
  },

  /** 切换视图模式 */
  setViewMode(state, { payload }: { payload: 'raw' | 'standardized' }) {
    return { ...state, viewMode: payload };
  },

  /** 选中行（触发左侧定位） */
  setSelectedRow(state, { payload }: { payload: string | null }) {
    return { ...state, selectedRowId: payload };
  },

  /** 删除行 */
  removeRow(state, { payload }: { payload: { tableId: string; rowId: string } }) {
    return {
      ...state,
      extractedTables: state.extractedTables.map(table =>
        table.tableId === payload.tableId
          ? { ...table, rows: table.rows.filter(r => r.rowId !== payload.rowId) }
          : table
      ),
      hasUnsavedChanges: true,
    };
  },

  /** 重置状态（离开页面时清理） */
  resetState() {
    return initialState;
  },
}
```

#### Key Effects

```typescript
effects: {
  /** 上传文件（multipart） */
  *uploadFiles({ payload }: { payload: { companyId: number } }, { call, put, select }) {
    const fileList: UploadFileItem[] = yield select(state => state.financialUpload.fileList);
    const pendingFiles = fileList.filter(f => f.status === 'pending');

    // Step 1: 创建会话
    const { sessionId } = yield call(createSession, { companyId: payload.companyId });
    yield put({ type: 'setState', payload: { sessionId } });

    // Step 2: 逐文件上传（并行最多 3 个）
    for (const file of pendingFiles) {
      yield put({ type: 'updateUploadProgress', payload: { uid: file.uid, progress: 0, status: 'uploading' } });
      try {
        const formData = new FormData();
        formData.append('file', file.originFile);
        const { fileId } = yield call(uploadFile, sessionId, formData, (progress: number) => {
          // onUploadProgress callback → dispatch updateUploadProgress
        });
        yield put({ type: 'updateUploadProgress', payload: { uid: file.uid, progress: 100, status: 'completed', fileId } });
      } catch (error) {
        yield put({ type: 'updateUploadProgress', payload: { uid: file.uid, status: 'error', errorMessage: error.message } });
      }
    }

    // Step 3: 触发 AI 提取
    yield call(triggerExtraction, sessionId);

    // Step 4: 跳转到 ProcessingPage
    history.push(`/financial/upload/${sessionId}`);
  },

  /** 轮询提取状态（2s 间隔） */
  *pollStatus({ payload }: { payload: { sessionId: string } }, { call, put }) {
    const POLL_INTERVAL = 2000;
    const MAX_POLLS = 150; // 最多 5 分钟
    let pollCount = 0;

    while (pollCount < MAX_POLLS) {
      const status: SessionStatus = yield call(getSessionStatus, payload.sessionId);
      yield put({ type: 'setSessionStatus', payload: status });

      if (status.status === 'COMPLETED') {
        // 提取完成，加载结果并跳转
        yield put({ type: 'fetchResult', payload: { sessionId: payload.sessionId } });
        history.replace(`/financial/review/${payload.sessionId}`);
        return;
      }

      if (status.status === 'FAILED') {
        // 失败，停止轮询，显示错误
        return;
      }

      // 等待 2s 再轮询
      yield call(delay, POLL_INTERVAL);
      pollCount += 1;
    }

    // 超时处理
    yield put({
      type: 'setSessionStatus',
      payload: { sessionId: payload.sessionId, status: 'FAILED', progress: 0, errorMessage: '处理超时，请重试' },
    });
  },

  /** 获取提取结果 */
  *fetchResult({ payload }: { payload: { sessionId: string } }, { call, put }) {
    const { tables, mappings } = yield call(getSessionResult, payload.sessionId);
    yield put({ type: 'setExtractedTables', payload: { tables, mappings } });
  },

  /** 提交审核编辑（自动保存） */
  *submitReview(_, { call, put, select }) {
    yield put({ type: 'setSaveStatus', payload: 'saving' });
    try {
      const { sessionId, editedRows, mappingOverrides } = yield select(state => state.financialUpload);
      yield call(updateReview, sessionId, { edits: editedRows, mapping_overrides: mappingOverrides });
      yield put({ type: 'setSaveStatus', payload: 'saved' });
      // 清空已保存的编辑队列
      yield put({ type: 'setState', payload: { editedRows: [], mappingOverrides: [] } });
    } catch (error) {
      yield put({ type: 'setSaveStatus', payload: 'error' });
    }
  },

  /** 提交写入 LG */
  *commitToLG(_, { call, put, select }) {
    yield put({ type: 'setState', payload: { commitStatus: 'committing' } });
    try {
      const { sessionId, conflicts } = yield select(state => state.financialUpload);
      const resolutions = conflicts
        .filter(c => c.resolution)
        .map(c => ({ conflictId: c.conflictId, resolution: c.resolution, note: c.note }));
      const result = yield call(commitToLG, sessionId, { conflict_resolutions: resolutions });
      if (result.success) {
        yield put({ type: 'setState', payload: { commitStatus: 'success' } });
        message.success(`成功写入 ${result.written_periods.length} 个期间的数据`);
      } else {
        // 返回新冲突（首次提交时检测到的）
        yield put({ type: 'setState', payload: { conflicts: result.conflicts, commitStatus: 'idle' } });
      }
    } catch (error) {
      yield put({ type: 'setState', payload: { commitStatus: 'error', commitErrorMessage: error.message } });
    }
  },
}
```

#### Subscriptions

```typescript
subscriptions: {
  /** 路由变化时清理轮询和重置状态 */
  routeChange({ dispatch, history }) {
    return history.listen(({ pathname }) => {
      // 离开 financial 路由时完全重置
      if (!pathname.startsWith('/financial')) {
        dispatch({ type: 'resetState' });
      }
      // 离开 ProcessingPage 时停止轮询
      if (!pathname.includes('/financial/upload/')) {
        dispatch({ type: 'stopPolling' });
      }
    });
  },
}
```

## 4. 关键交互流程

#### 上传流程

```
用户拖拽/选择文件
  │
  ├── 客户端预校验
  │     ├── 文件类型检查: MIME type + 扩展名
  │     │     允许: application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
  │     │           application/vnd.ms-excel, text/csv, image/png, image/jpeg
  │     ├── 单文件大小: ≤ 20MB
  │     ├── 批量总大小: ≤ 100MB
  │     └── 校验失败 → FileQueueItem 立即显示 Error + 原因
  │
  ├── 文件加入 FileQueue (status: pending)
  │     显示: 文件名、类型图标、大小、Pending 徽章
  │
  ├── 用户点击 "Upload All"
  │     ├── POST /api/v1/ocr/sessions → 获取 sessionId
  │     ├── 逐文件 POST /api/v1/ocr/sessions/{id}/files (multipart)
  │     │     onUploadProgress → 实时更新进度条百分比
  │     │     成功 → status: completed, 绿色 ✓
  │     │     失败 → status: error, 红色 ✗, 显示重试按钮
  │     ├── 全部上传完成 → POST /api/v1/ocr/sessions/{id}/extract
  │     └── 自动跳转 → /financial/upload/:sessionId (ProcessingPage)
  │
  └── ProcessingPage 开始轮询
        GET /api/v1/ocr/sessions/{id}/status (每 2s)
```

#### 审核流程

```
ReviewPage 加载
  │
  ├── 获取提取结果 → 渲染 TableSelector + 第一个表格
  │
  ├── 点击表格行 (单击)
  │     ├── 设置 selectedRowId → 高亮右侧行
  │     ├── SourcePanel 联动:
  │     │     PDF: react-pdf 跳转到 row.sourcePageNumber 页
  │     │     Excel: 滚动到 row.sourceRowIndex 行并高亮
  │     └── ConfidenceBadge tooltip 显示 mapping reasoning
  │
  ├── 双击单元格 (数值/标签)
  │     ├── EditableCell 切换为 <Input> (受控模式)
  │     ├── 用户编辑 → 回车或失焦
  │     ├── dispatch updateRow → state 更新 + hasUnsavedChanges = true
  │     └── 触发 debounced submitReview (500ms)
  │
  ├── 修改分类 (Standardized 视图)
  │     ├── 点击 CategoryDropdown → antd Select 展开
  │     ├── 分组显示 19 个 LG 分类
  │     ├── 选择 → dispatch overrideMapping
  │     │     source 变为 'user_override'
  │     │     confidence 变为 'HIGH'
  │     │     ConfidenceBadge 变绿
  │     └── 触发 debounced submitReview (500ms)
  │
  ├── 切换 Raw ↔ Standardized 视图
  │     ├── dispatch setViewMode
  │     ├── 表格列定义切换（标签列 vs 分类列）
  │     └── 已有编辑保留（editedRows 和 mappingOverrides 不受影响）
  │
  └── 点击 "Next: Confirm"
        ├── 执行硬验证:
        │     1. Account Name 不为空
        │     2. Value 必须是数值
        │     3. Month 不为空且不是 "Unidentified"
        ├── 验证失败 → 显示精确错误:
        │     "2024_PnL.pdf → Table 1 → Row 5: Account Name is empty"
        │     点击错误可跳转到对应行
        └── 验证通过 → POST /api/v1/ocr/sessions/{id}/validate
              ├── 无冲突 → 跳转 ConfirmPage (conflicts = [])
              └── 有冲突 → 跳转 ConfirmPage (conflicts 填充)
```

**噪音数据清除**: 用户可通过右键菜单或行尾操作按钮执行 Remove Row / Remove Column，清除 AI 误提取的噪音数据后重新通过硬验证。

## 5. 轮询状态管理

```
ProcessingPage mounted
  │
  ▼
开始轮询: GET /api/v1/ocr/sessions/{id}/status (每 2s)
  │
  ├── status = PENDING
  │     UI: 显示 "排队等待处理..."
  │     进度条: 不确定模式 (antd Progress status="active" 无百分比)
  │     继续轮询
  │
  ├── status = PROCESSING
  │     UI: 显示 "正在进行 AI 提取..."
  │     进度条: 显示 progress% (服务端返回的实际进度)
  │     文件级状态: 每个文件显示独立进度
  │     继续轮询
  │
  ├── status = COMPLETED
  │     UI: 显示 "提取完成，正在跳转..."
  │     进度条: 100%, 绿色
  │     ★ 停止轮询 (clearInterval)
  │     ★ 加载提取结果 (fetchResult effect)
  │     ★ history.replace → /financial/review/:sessionId
  │
  └── status = FAILED
        UI: 显示错误信息 (errorMessage 来自服务端)
        进度条: 红色
        ★ 停止轮询 (clearInterval)
        ★ 显示操作按钮:
            [重试] → POST /api/v1/ocr/sessions/{id}/extract → 重新开始轮询
            [返回] → history.push('/financial/upload')

超时保护:
  最大轮询次数 = 150 (2s × 150 = 5 分钟)
  超时 → 视同 FAILED，显示 "处理超时，请重试"

清理机制:
  ├── 组件 unmount → useEffect cleanup → clearInterval
  ├── 路由离开 → dva subscription → dispatch stopPolling
  └── 浏览器关闭 → 服务端 LangGraph checkpoint 保存状态
        用户重新访问同一 URL → 恢复到最近状态
```

### 5.5 LangGraph Checkpoint 恢复 UX

**场景**：用户上传后浏览器崩溃/关闭，重新打开页面时如何恢复。

**实现策略**：

```
用户重新进入 /financial/upload
  → 调用 GET /docparse/tasks?status=in_progress
  → 返回该用户最近的进行中 task list

  if (有进行中 task) {
    显示恢复对话框:
      "您有未完成的上传任务：
       - {filename} (状态: {status})
       是否继续？"
    选择"继续" → 跳转到对应阶段：
      - status=PROCESSING → /financial/upload/:sessionId (ProcessingPage)
      - status=REVIEWING → /financial/review/:sessionId (ReviewPage)
      - status=CONFLICT  → /financial/confirm/:sessionId (ConfirmPage)
    选择"忽略" → 留在 UploadPage，task 保持原状态
  } else {
    正常显示 UploadPage
  }
```

**LangGraph 端的能力**：因为 Python workflow 用 PostgreSQL 作 checkpoint，重新进入 ReviewPage 时获取的数据完全是上次保存的状态（包括用户已编辑的内容），无需用户重做。

## 6. 大表格性能

目标: 流畅支持 1000+ 行表格，无卡顿。

**虚拟滚动方案**:

```
react-window FixedSizeList
  ├── 行高: 40px (固定)
  ├── 可视区域: 视口高度 / 40 ≈ 15-20 行
  ├── overscanCount: 10 (上下各预渲染 10 行)
  ├── 实际 DOM 节点: 30-40 个 (而非 1000+)
  └── 滚动时只替换内容，不创建/销毁 DOM
```

**EditableCell 性能优化**:

```
非激活状态 (99% 的时间):
  渲染: <span className="cell-text">{value}</span>
  零事件监听，零受控 state

激活状态 (双击时):
  渲染: <Input value={editValue} onChange={...} onBlur={...} onPressEnter={...} />
  仅当前单元格使用受控模式

切换机制:
  双击 → setActiveCellId(cellKey) → 仅 1 个单元格重渲染
  失焦 → setActiveCellId(null) → 恢复纯文本
```

**额外优化**:
- `React.memo` 包裹 `EditableCell`、`ConfidenceBadge`、`CategoryDropdown`
- `useMemo` 缓存列定义（仅 viewMode 或 reportingPeriods 变化时重算）
- 映射结果 (`mappingResults`) 使用 `rowId` 索引的 `Record`，O(1) 查找
- 避免在滚动事件中触发 state 更新

## 7. 自动保存

**触发机制**:

```
用户编辑操作 (updateRow / overrideMapping / removeRow)
  │
  ▼
hasUnsavedChanges = true
  │
  ▼
debounce 500ms (lodash.debounce)
  │ (500ms 内的连续编辑合并为一次请求)
  │
  ▼
dispatch submitReview effect
  │
  ├── saveStatus = 'saving'
  │     UI: ActionBar 显示 "Saving..." + 旋转图标
  │
  ├── PATCH /api/v1/ocr/sessions/{id}/review
  │     请求体: 仅发送自上次保存以来的增量 diff
  │     {
  │       edits: RowEdit[],           // 新增的行编辑
  │       mapping_overrides: MappingOverride[]  // 新增的映射覆盖
  │     }
  │
  ├── 成功:
  │     saveStatus = 'saved'
  │     hasUnsavedChanges = false
  │     清空 editedRows/mappingOverrides 队列
  │     UI: ActionBar 显示 "All changes saved" + 绿色 ✓ (3s 后淡出)
  │
  └── 失败:
        saveStatus = 'error'
        hasUnsavedChanges = true (保留，下次重试)
        UI: ActionBar 显示 "Save failed — retry" + 红色 ✗
        点击 "retry" → 立即触发 submitReview
```

**浏览器关闭保护**:

```typescript
// ReviewPage 中注册 beforeunload
useEffect(() => {
  const handler = (e: BeforeUnloadEvent) => {
    if (hasUnsavedChanges) {
      e.preventDefault();
      e.returnValue = ''; // 浏览器标准：显示离开确认对话框
    }
  };
  window.addEventListener('beforeunload', handler);
  return () => window.removeEventListener('beforeunload', handler);
}, [hasUnsavedChanges]);
```

**路由离开保护**:

```typescript
// UmiJS Prompt 组件
<Prompt
  when={hasUnsavedChanges}
  message="有未保存的更改，确定要离开吗？"
/>
```

## 8. Mobile 策略

| 页面 | Mobile 策略 | 实现方式 |
|------|------------|----------|
| **UploadPage** | 完全响应式 | 隐藏拖拽区域，仅保留文件选择按钮；FileQueue 纵向堆叠；BatchActions 全宽按钮 |
| **ProcessingPage** | 完全响应式 | 进度条自适应宽度；文件列表纵向堆叠 |
| **ReviewPage** | Desktop Only | 检测视口宽度 < 1024px 时显示全屏提示页 |
| **ConfirmPage** | 完全响应式 | WriteSummary 卡片纵向堆叠；ConflictItem 改为纵向对比布局 |

**ReviewPage Desktop Only 实现**:

```typescript
// ReviewPage.tsx
const ReviewPage: React.FC = () => {
  const isDesktop = useMedia('(min-width: 1024px)');

  if (!isDesktop) {
    return (
      <Result
        icon={<DesktopOutlined style={{ color: '#999' }} />}
        title="请使用桌面浏览器进行数据审核"
        subTitle="并排审核和内联编辑功能需要更大的屏幕空间。请在宽度 ≥ 1024px 的桌面浏览器中打开此页面。"
        extra={
          <Button type="primary" onClick={() => history.push('/financial/upload')}>
            返回上传页
          </Button>
        }
      />
    );
  }

  return <ReviewPageContent />;
};
```

**响应式断点** (与现有 Ant Design Pro 保持一致):

| 断点 | 宽度 | 适用设备 |
|------|------|----------|
| xs | < 576px | 手机竖屏 |
| sm | >= 576px | 手机横屏 |
| md | >= 768px | 平板 |
| lg | >= 992px | 小桌面 |
| xl | >= 1200px | 标准桌面 |
| xxl | >= 1600px | 大屏 |

## 9. 硬验证规则（ReviewPage -> ConfirmPage 前置条件）

三要素必须完整:
1. **Account Name** -- 不为空
2. **Value** -- 必须是数值
3. **Month** -- 不为空且不是 "Unidentified"

不满足时精确提示: `"2024_PnL.pdf" -> Table 1 -> Row 5: Account Name is empty`

用户可通过 Remove Row / Remove Column 清除噪音数据后通过验证。

## 10. 未映射账户处理 UX

### 10.1 场景

AI 映射 Layer 1 (规则) + Layer 2 (公司记忆) + Layer 3 (LLM) 后，仍可能有行项无法映射，标记为 UNMAPPED：
- Payroll 无部门上下文 → S&M/R&D/G&A 都无法判断
- 全新的财务术语，规则和记忆都没匹配，LLM 也无法判断
- 用户主动删除了一个映射

### 10.2 集中展示设计

ReviewPage 在 Standardized View 下方新增 **UnmappedSection 组件**：

```
┌─────────────────────────────────────────────────┐
│  ⚠ 未映射账户 (3)                                │
│                                                 │
│  这些账户暂未映射到 LG 分类，请手动选择：        │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │ Total Compensation Q1     $250,000      │    │
│  │ 来源：表 1 第 12 行                      │    │
│  │ 映射到: [选择 LG 分类 ▼]                 │    │
│  ├─────────────────────────────────────────┤    │
│  │ Misc Operating Item       $5,400        │    │
│  │ 来源：表 2 第 8 行                       │    │
│  │ 映射到: [选择 LG 分类 ▼]                 │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  [全部跳过] [应用建议]                          │
└─────────────────────────────────────────────────┘
```

### 10.3 组件结构

```
ReviewPage
  └── DataPanel (右)
        ├── ViewToggle ([Raw] [Standardized])
        ├── EditableTable (已映射部分)
        ├── UnmappedSection (新增)
        │     ├── UnmappedHeader (含数量徽章 + 说明)
        │     ├── UnmappedItem[]
        │     │     ├── AccountInfo (label + 金额 + 来源)
        │     │     └── CategoryDropdown (19 LG 分类)
        │     └── UnmappedActions (全部跳过/应用建议)
        └── ValidationBar
```

### 10.4 交互细节

- 用户从 Dropdown 选择分类 → 该行项实时移出 UnmappedSection，加入对应 LG 分类组
- "全部跳过" → 这些行项不参与提交（标记 `skipped=true`），不阻塞流程
- "应用建议" → 自动应用 AI 在 LLM 阶段给出的最高分但低于阈值的建议（confidence < threshold 的）
- 硬验证规则：UnmappedSection 不为空时，**不阻止提交**（与"账户名/数值/月份"三要素不同），但在 ConfirmPage 显示警告："3 个账户未映射，将不会写入 LG"

### 10.5 dva model 调整

新增 state 字段：
```typescript
unmappedRows: Array<{
  rowId: string
  tableId: string
  accountLabel: string
  values: Record<string, number>
  sourceRef: { tableIndex: number; rowIndex: number }
  skipped: boolean
}>;
```

新增 reducer：`mapUnmappedRow(rowId, lgCategory)`、`skipUnmappedRow(rowId)`、`applyAllSuggestions()`

## 11. 货币不一致提示

### 11.1 业务规则

来自 Asana Story #5：
> All mapped results from the uploaded file must use a single currency. If multiple currencies are detected, the system shall default to USD but with an alert icon.

### 11.2 触发条件

Python 提取阶段 (`ExtractedTable.currency_warning=true`) 表示该表检测到多种货币符号。

### 11.3 UI 展示

在 ReviewPage 顶部加 **CurrencyWarningBanner 组件**（仅当 `currency_warning=true` 时渲染）：

```
┌─────────────────────────────────────────────────────────┐
│  ⚠ 检测到多种货币 ($USD, €EUR, £GBP)                     │
│  系统已默认按 USD 处理。如需更改请选择: [USD ▼]          │
│  ⚙ 注意：所有数值将按选定货币写入 LG，不会自动汇率换算    │
└─────────────────────────────────────────────────────────┘
```

每个 EditableCell 旁边加货币 icon（仅在 currency_warning=true 时）：
- 鼠标悬停显示该单元格在源文件中的原始货币符号

### 11.4 组件结构

```
ReviewPage
  ├── CurrencyWarningBanner (条件渲染)
  │     ├── DetectedCurrenciesList
  │     ├── CurrencySelector (默认 USD，可改)
  │     └── HelpTooltip
  └── ... (其他组件)
```

### 11.5 dva model 调整

新增 state 字段：
```typescript
currencyWarning: {
  visible: boolean
  detectedCurrencies: string[]
  selectedCurrency: string  // 用户最终选择，默认 USD
}
```
