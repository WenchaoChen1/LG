# OCR Agent 前端设计

> **技术栈**: React 16 + Ant Design Pro v4 + UmiJS 3 + dva + TypeScript
> **关联文档**: [数据库 Schema](./database-schema.md) · [设计理念](./design-philosophy.md) · [需求分析](./requirement-analysis.md) · [系统架构](./system-architecture.md) · [Java 端设计](./java-design.md) · [Python 端设计](./python-design.md) · [代码示例](./code-examples.md)

## 与后端交互

前端调用的 Java API 一览（完整清单，与 java-design.md §2 对齐）：

```
# ============ Task 生命周期 ============
POST   /api/v1/docparse/tasks                           → UploadPage (新建 DRAFT)
POST   /api/v1/docparse/tasks/{id}/revise               → FinancialEntry "基于此任务修订"
GET    /api/v1/docparse/tasks/{id}/status               → ProcessingPage (polling 2s)
GET    /api/v1/docparse/tasks/{id}/result               → ReviewPage
GET    /api/v1/docparse/tasks/{id}/history              → SuccessPage 版本链

# ============ 上传（S3 Presigned URL 直传）============
POST   /api/v1/docparse/upload/request-urls             → UploadPage Step 1
POST   /api/v1/docparse/upload/complete                 → UploadPage Step 3 (per-file)
POST   /api/v1/docparse/upload/abort                    → UploadPage 取消

# ============ 文件查看 ============
POST   /api/v1/docparse/files/{fileId}/download-url     → ReviewPage DocumentViewer

# ============ 审核 / 提交 ============
PATCH  /api/v1/docparse/tasks/{id}/review               → ReviewPage auto-save
POST   /api/v1/docparse/tasks/{id}/verify               → ConfirmPage Stage 1
GET    /api/v1/docparse/tasks/{id}/verify/status        → ConfirmPage Stage 1 polling
GET    /api/v1/docparse/tasks/{id}/conflicts            → ConfirmPage Stage 2
POST   /api/v1/docparse/tasks/{id}/resolve              → ConfirmPage Stage 2
POST   /api/v1/docparse/tasks/{id}/commit               → ConfirmPage Stage 3

# ============ 通知 ============
GET    /api/v1/docparse/tasks/{id}/notifications        → ProcessingPage 通知状态
POST   /api/v1/docparse/notifications/{id}/retry        → NotificationIndicator 手动重试

# ============ 记忆学习 ============
GET    /api/v1/docparse/tasks/{id}/memory-learn         → SuccessPage 悬浮条
GET    /api/v1/docparse/tasks/{id}/memory-learn/history → SuccessPage 历史尝试
POST   /api/v1/docparse/tasks/{id}/memory-learn/retry   → SuccessPage 失败重试

# ============ Note Thread ============
GET    /api/v1/docparse/tasks/{taskId}/conflicts/{conflictId}/notes   → ConfirmPage NoteThread
POST   /api/v1/docparse/tasks/{taskId}/conflicts/{conflictId}/notes   → ConfirmPage 追加 note
```

**已废弃的端点**（请勿使用）:
- ❌ `POST /api/v1/docparse/upload`（旧 multipart，被 Presigned URL 替代）
- ❌ `POST /api/v1/docparse/tasks/{id}/confirm`（旧一体化 commit，被 verify + resolve + commit 三步替代）
- ❌ `POST /api/v1/ocr/sessions/*` 和 `PATCH /api/v1/ocr/sessions/*`（旧命名空间，统一为 `/docparse`）

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

#### ReviewPage（核心页面 — 2026-04-19 按 Asana 更新大幅重构）

```
ReviewPage
  ├── SplitView (可调比例, 默认 50/50, 左面板可隐藏)
  │     │
  │     ├── SourcePanel（左面板 — Source Document Viewer, Asana 2026-04-19 扩展）
  │     │     ├── FileSelector（顶部 — 新增）
  │     │     │     antd Select 下拉菜单，列出当前 session 所有已上传文件
  │     │     │     选择后加载对应文件到 DocumentViewer
  │     │     │     与右面板 DocumentTypeFilter 联动（见下方）
  │     │     │
  │     │     ├── NavigationControls（新增 — 文件类型动态）
  │     │     │     如果选中文件是 Excel (多 sheet):
  │     │     │       → 显示 SheetTabs（antd Tabs，tab-based navigation）
  │     │     │     如果选中文件是 PDF:
  │     │     │       → 显示 PageNavigator（上一页 / 下一页 / 页码输入）
  │     │     │
  │     │     ├── FileActions（新增）
  │     │     │     - "添加新文件" 按钮
  │     │     │     - "替换文件" 按钮（触发 UploadZone 弹窗）
  │     │     │
  │     │     ├── DocumentViewer（使用 presigned GET URL，2026-04-20 重写）
  │     │     │     文件 URL 获取方式（Presigned GET URL，5 分钟有效）：
  │     │     │       1. 选中文件时调 POST /api/v1/docparse/files/{fileId}/download-url
  │     │     │       2. Java 返回 { "url": "https://s3.amazonaws.com/...", "expiresAt": "2026-04-20T10:15:00Z" }
  │     │     │       3. 前端缓存 URL + expiresAt；每 4 分钟检查 (expiresAt - now < 1min) 主动续签
  │     │     │     PDF → react-pdf file={url} 渲染当前页
  │     │     │       403 处理：react-pdf onLoadError → 重新申请 URL → 重新渲染
  │     │     │     Excel → fetch(url) → SheetJS 解析为 JSON → antd Table 只读渲染
  │     │     │       403 处理：fetch .catch → 重新申请 URL → 重新 fetch
  │     │     │     图片 → <img src={url}> 渲染
  │     │     │       403 处理：onError 事件 → 重新申请 URL → 重设 src（需加 ?t=timestamp 绕过浏览器缓存）
  │     │     │     支持源位置高亮（见 Source Tracing UX）
  │     │     │
  │     │     └── ZoomControlBar（底部 — 新增）
  │     │           + / - 按钮 + 百分比显示 + "适应宽度" 按钮
  │     │
  │     └── DataPanel（右面板 — Data Mapping, Asana 2026-04-19 扩展）
  │           ├── FilterBar（顶部 — 新增）
  │           │     ├── DocumentTypeFilter
  │           │     │     antd Segmented 或 Select: [All Types (默认)] [P&L] [Balance Sheet] [Proforma]
  │           │     │     与左面板 FileSelector 联动
  │           │     └── CurrencySelector
  │           │           antd Select 货币下拉，与类型过滤器并列
  │           │           默认用 ExtractedTable.currency；多币种时显示 alert 图标
  │           │
  │           ├── MetricsList（支持水平+垂直滚动，Financial Entry 格式）
  │           │     ├── UnmappedSection（未映射账户，集中在顶部）
  │           │     │     标题: "未映射账户 (N)"
  │           │     │     每个 UnmappedItem:
  │           │     │       - 账户标签 + 金额 + 源位置
  │           │     │       - CategoryDropdown: 映射后自动移入对应 LG 分类
  │           │     │
  │           │     ├── LGCategoryGroup[] (按 LG 19 类分组)
  │           │     │     每组显示: 分类名 + MetricRow[]
  │           │     │       ├── EditableCell (数值)
  │           │     │       │     用户删除数值 → 默认显示 0（onBlur 处理）
  │           │     │       ├── AlertIcon (当 label 被删除为空时显示)
  │           │     │       └── ExpandableSourceItems (展开查看每个源行项)
  │           │     │             每个源行项可 CategoryDropdown 重新映射到其他 LG 指标
  │           │     │
  │           │     ├── BlankMonthColumn（新增 2026-04-19）
  │           │     │     ExtractedTable.unresolved_period_count > 0 时
  │           │     │     在指标表最右端追加空白月份列
  │           │     │     每列顶部有 DatePicker 让用户分配月份
  │           │     │
  │           │     └── EmptyMappingMessage
  │           │           当没有财务账户可映射到 LG 指标时显示
  │           │
  │           ├── SourceTracingHint（新增 — 悬停时显示）
  │           │     悬停右面板指标 → tooltip 显示 "来源: PnL.xlsx, Sheet1, B12"
  │           │     左面板高亮仅在 "当前 page/sheet == 指标源" 时显示
  │           │
  │           └── ViewToggle（保留，位置调整）
  │                 [Raw] [Standardized] — Raw 视图下无 LGCategoryGroup 分组，纯列表
  │
  │   （旧的 TableSelector 已移除：Asana 2026-04-19 新设计使用文件过滤+类型过滤代替 Tab 切换）

  ├── LeftRightPanelLinkage（联动逻辑，非组件，在 dva effects 中实现）
  │     左→右: 选文件 → DocumentTypeFilter 自动更新为该文件的文档类型
  │     右→左: 选文档类型 → FileSelector 下拉过滤为只显示该类型文件
  │     示例: 选 Balance Sheet
  │           → 左面板只显示 BS 文件
  │           → 右面板只显示 BS 指标
  │     右面板指标列表始终反映当前 (file, documentType) 组合

  ├── (保留原 EditableTable / EditableCell / CategoryDropdown / ConfidenceBadge 的交互细节，
  │    但渲染结构已按上述 MetricsList 重新组织)
  │
  │ （历史结构归档 — 供对照）
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
ConfirmPage（Asana 2026-04-19 重构为两阶段流程）
  │
  ├── Stage 1: VerifyDataSummary（新增阶段，冲突检测前的摘要）
  │     ├── SummaryStats
  │     │     ├── 源文件总数
  │     │     ├── 映射类型数
  │     │     └── 映射账户数
  │     ├── StartVerificationButton (antd Button primary)
  │     │     点击 → 调 POST /docparse/tasks/{id}/verify
  │     └── VerificationProgress (实时进度指示器)
  │           轮询 GET /docparse/tasks/{id}/verify/status
  │
  ├── Stage 2: ConflictResolutionView（verify 完成后显示）
  │     ├── FinancialEntryFormatGrid
  │     │     以 Financial Entry 格式渲染 (列=报告周期，行=LG 指标)
  │     │     每个 ConflictCell 高亮（黄色背景 + warning 图标）
  │     │
  │     └── ConflictPopup (点击冲突单元格打开)
  │           ├── CurrentLGValue (当前 LG 中的值)
  │           ├── MappingResultSum (映射结果的总和)
  │           ├── ActionButtons (仅两个选项，Cancel 已移除)
  │           │     ├── "用映射值覆盖" (Select action → Overwrite)
  │           │     └── "保留 LG 值" (Keep LG Value → Skip)
  │           └── NoteField (Asana Story #7 2026-04-19)
  │                 ├── Textarea (placeholder: "解释为何这样处理冲突，可选")
  │                 │     2000 字限制 + CharCount (0/2000)
  │                 ├── AutoDefaultNote
  │                 │     用户不填时系统自动生成:
  │                 │     "{时间} - {用户} 接受上传值覆盖 LG（原 {旧值} → 新 {新值}）"
  │                 ├── NoteThread (历史 notes 倒序时间线)
  │                 │     每条 NoteItem: 作者 + 时间 + 内容 + AutoGenerated 徽章
  │                 └── AddReplyInput
  │                       用户可追加新 note 到 thread (类似 Slack 评论回复)
  │
  └── Stage 3: CommitButton (所有冲突解决后才能点击)
        antd Button type="primary" size="large", disabled until 所有冲突都已选择
        Text: "确认并写入 LG"
        点击 → POST /docparse/tasks/{id}/commit
        成功 → 跳转 SuccessPage + 触发新闭月邮件（后端异步）
        失败 → 整体 rollback（不允许部分写入），显示错误
```

**Note 字段可见性（2026-04-19 扩展）**

- **执行上传的用户**：在 ConfirmPage 和 Financial Statements 模块都可查看
- **portfolio managers 及有公司访问权限的其他用户**：可在 Financial Statements 模块查看，了解变化和原因
- **查看入口**：Financial Entry 页面新增"导入备注"折叠面板（NoteThreadPanel 组件），展示该 period 的所有 notes（倒序时间线）
- **上传最终完成后 notes 只读**

**NoteThread 组件**

```
NoteThread
├── NoteItem[] (倒序时间线)
│   ├── AuthorAvatar + UserName
│   ├── Timestamp
│   ├── NoteText (Markdown 渲染)
│   └── AutoGenerated Badge (系统自动 note 标记)
└── AddReplyInput
    ├── Textarea (≤ 2000 字)
    ├── "追加" 按钮
    └── CharCount
```

**冲突解决约束（重要）**

- **用户必须解决每个检测到的冲突才能点击 Commit**
- **映射数据写入作为整体**：任何一个 metric 写入失败 → 全部 rollback
- **Cancel 选项已移除**（如要放弃，直接退出页面，task 状态保持 REVIEWING）

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
  /** 全大写对齐 Java enum DocParseConflictAction；Cancel 选项已移除（Asana 2026-04-19） */
  resolution?: 'OVERWRITE' | 'SKIP';
  note?: string;
}

/** Task 级状态 —— 对齐 java-design.md §3.1 DocParseStatus enum 20 值 */
type TaskStatus =
  | 'DRAFT' | 'UPLOADING' | 'UPLOAD_COMPLETE' | 'PROCESSING'
  | 'SIMILARITY_CHECKING' | 'SIMILARITY_CHECKED' | 'SIMILARITY_CHECK_FAILED' | 'REVIEWING'
  | 'VERIFYING' | 'CONFLICT_RESOLUTION' | 'COMMITTING' | 'COMMITTED'
  | 'MEMORY_LEARN_PENDING' | 'MEMORY_LEARN_IN_PROGRESS'
  | 'MEMORY_LEARN_COMPLETE' | 'MEMORY_LEARN_FAILED'
  | 'COMPLETED' | 'SUPERSEDED' | 'FAILED' | 'EXPIRED';

/** File 级状态 */
type FileStatus =
  | 'PENDING' | 'UPLOADING' | 'UPLOADED' | 'QUEUED' | 'PROCESSING'
  | 'REVIEW_READY' | 'FILE_COMMITTED' | 'FILE_FAILED';

/** Processing stage —— 12 子状态，仅 file.status=PROCESSING 时有效 */
type ProcessingStage =
  | 'PREPROCESS_PENDING' | 'PREPROCESSING' | 'EXTRACTING' | 'CLASSIFYING'
  | 'MAPPING_RULE' | 'MAPPING_MEMORY_LOOKUP' | 'MAPPING_MEMORY_APPLY' | 'MAPPING_MEMORY_COMPLETE'
  | 'MAPPING_LLM' | 'VALIDATING' | 'PERSISTING' | 'REVIEW_READY';

/** Task 状态聚合（GET /tasks/{id}/status 返回） */
interface TaskStatusResp {
  taskId: string;
  status: TaskStatus;
  totalFiles: number;
  completedFiles: number;
  failedFiles: number;
  files: Array<{
    fileId: string;
    filename: string;
    status: FileStatus;
    stage: ProcessingStage | null;
    progressPct: number;
    stageDetail?: Record<string, unknown>;  // Python 透传，前端按 §5.2 渲染
    errorMessage?: string;
  }>;
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
  sessionStatus: TaskStatusResp | null;  // 类型已重命名为 TaskStatusResp，见上方 interface 定义
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
  setSessionStatus(state, { payload }: { payload: TaskStatusResp }) {
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
      const status: TaskStatusResp = yield call(getTaskStatus, payload.taskId);
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

  /** 提交写入 LG（Q7 方案 B：失败后 task.status 自动回 REVIEWING，允许用户重试） */
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
      // ⚠️ 关键：根据 errorCode 分别处理
      // - COMMIT_FAILED_RETRYABLE: Java 事务回滚，task.status 已自动回 REVIEWING，可重试
      // - 其他错误: 非技术失败（如 INVALID_STATUS），不建议重试
      const errorCode = error.response?.data?.errorCode;
      const retryable = errorCode === 'COMMIT_FAILED_RETRYABLE';
      yield put({ type: 'setState', payload: {
        commitStatus: 'error',
        commitErrorMessage: error.message,
        commitErrorRetryable: retryable
      } });
      // 弹 Modal 询问用户是否重试
      Modal.error({
        title: '提交失败',
        content: retryable
          ? `${error.message}\n\n数据未写入，您可以重试或返回调整。`
          : `${error.message}\n\n请联系管理员。`,
        okText: retryable ? '重试' : '知道了',
        cancelText: retryable ? '返回审核' : undefined,
        onOk: retryable ? () => dispatch({ type: 'commitToLG' }) : undefined,
        onCancel: retryable ? () => history.replace(`/financial/review/${sessionId}`) : undefined,
      });
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

#### 上传流程（S3 Presigned URL 直传模式，2026-04-20 重写）

**变更原因**: 旧的 multipart 上传先把文件发到 Java，再由 Java 转发到 S3，造成 Java 服务器要承担 N 倍文件大小的网络流量。改为 presigned URL 模式：前端直传 S3，Java 只负责颁发短期令牌和记录元数据。

```
用户拖拽/选择文件
  │
  ├── 客户端预校验
  │     ├── 文件类型检查: MIME type + 扩展名
  │     │     允许: application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
  │     │           application/vnd.ms-excel, text/csv, image/png, image/jpeg
  │     ├── 单文件大小: ≤ 20MB
  │     ├── 批量总大小: ≤ 100MB
  │     ├── 计算 SHA-256 hash（用于后端去重校验）
  │     │     小文件（< 5MB）: crypto.subtle.digest('SHA-256', buffer)
  │     │     大文件（≥ 5MB）: hash-wasm 的 createSHA256() 分块增量计算
  │     │     理由：Web Crypto API 不支持流式哈希，全量读入 20MB 会卡低端机 1-2 秒
  │     └── 校验失败 → FileQueueItem 立即显示 Error + 原因
  │
  ├── 文件加入 FileQueue (status: pending)
  │     显示: 文件名、类型图标、大小、Pending 徽章
  │
  ├── 用户点击 "Upload All"
  │     │
  │     ├── Step 1: 创建任务草稿 + 申请 presigned URLs
  │     │     POST /api/v1/docparse/upload/request-urls（与 java-design.md §2.1 对齐）
  │     │     body: {
  │     │       "taskId": "uuid",        // 前端先调 POST /tasks 拿到 DRAFT 任务的 id
  │     │       "files": [
  │     │         { "name": "2024_PnL.pdf", "size": 2048576, "type": "application/pdf", "hash": "sha256..." },
  │     │         { "name": "BS.xlsx",     "size": 500000, "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "hash": "def..." }
  │     │       ]
  │     │     }
  │     │     ↓
  │     │     Java 响应:
  │     │     {
  │     │       "taskId": "task-uuid",         // status=DRAFT
  │     │       "uploads": [
  │     │         {
  │     │           "fileId": "file-uuid-1",
  │     │           "presignedUrl": "https://s3.amazonaws.com/bucket/xxx?X-Amz-Signature=...",
  │     │           "expiresAt": "2026-04-20T10:15:00Z",
  │     │           "requiredHeaders": { "Content-Type": "application/pdf" }
  │     │         },
  │     │         { "fileId": "file-uuid-2", ... }
  │     │       ]
  │     │     }
  │     │     错误场景:
  │     │       - 重名 + hash 相同 → 提示"与本任务中 {otherFilename} 重复"（拒绝）
  │     │       - 重名 + hash 不同 → 提示"文件名重复，请重命名"（拒绝）
  │     │
  │     ├── Step 2: 并发直传 S3（最多 3 个并行）
  │     │     对每个 upload:
  │     │       PUT {presignedUrl}
  │     │       Content-Type: {requiredHeaders.Content-Type}
  │     │       Body: {originFile}
  │     │       XMLHttpRequest.upload.onprogress → dispatch updateUploadProgress
  │     │     成功 → status: uploading（仍未确认，等 Step 3）
  │     │     失败 → status: error + 重试按钮（重新申请单文件 presigned URL）
  │     │     注意：浏览器 → S3 是跨域请求，需 S3 bucket 配置 CORS 允许前端 origin
  │     │
  │     ├── Step 3: 通知后端上传完成 + 触发提取（每个文件单独调一次）
  │     │     POST /api/v1/docparse/upload/complete（与 java-design.md §2.1 对齐）
  │     │     body: { "fileId": "file-uuid-1", "etag": "...", "actualSize": 2048576 }
  │     │     ↓
  │     │     Java 后端:
  │     │       1. s3:HeadObject 确认文件已存在 + 校验 ETag + actualSize
  │     │       2. 读取首 2KB 做 MIME + magic bytes 二次校验
  │     │       3. 通过 → file.status=UPLOADED + 发 SQS
  │     │       4. 失败 → s3:DeleteObject + file.status=FILE_FAILED
  │     │       5. 所有文件 UPLOADED → task.status 推进到 PROCESSING
  │     │     响应: { "status": "UPLOADED" | "FILE_FAILED", "error": null | "..." }
  │     │
  │     └── Step 4: 自动跳转 → /financial/upload/:taskId (ProcessingPage)
  │
  └── ProcessingPage 开始轮询
        GET /api/v1/docparse/tasks/{taskId}/status (每 2s)
```

**前端 XHR 直传 S3 的关键代码**:
```typescript
async function uploadToS3(
  file: File,
  presignedUrl: string,
  requiredHeaders: Record<string, string>,
  onProgress: (pct: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', presignedUrl, true);
    // 不能用 fetch，因为 fetch 没有可靠的 upload progress 事件
    Object.entries(requiredHeaders).forEach(([k, v]) => xhr.setRequestHeader(k, v));

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    });
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`S3 upload failed: ${xhr.status}`));
    });
    xhr.addEventListener('error', () => reject(new Error('S3 upload network error')));
    xhr.send(file);
  });
}
```

**dva effect 更新（替换旧 multipart 实现）**:
```typescript
*uploadFiles({ payload }: { payload: { companyId: number, parentTaskId?: string } }, { call, put, select }) {
  const fileList = yield select(state => state.financialUpload.fileList);

  // Step 0: 创建 DRAFT task（修订场景调 /tasks/{parentTaskId}/revise，普通场景调 /tasks）
  const { taskId } = payload.parentTaskId
    ? yield call(reviseTask, payload.parentTaskId, { reason: payload.revisionReason })
    : yield call(createTask, { companyId: payload.companyId });
  yield put({ type: 'setState', payload: { sessionId: taskId } });

  // Step 1: 申请 presigned URLs
  const { uploads } = yield call(requestUploadUrls, {
    taskId,
    files: fileList.map(f => ({
      name: f.fileName,
      size: f.fileSize,
      type: f.originFile.type,
      hash: f.sha256
    }))
  });

  // Step 2: 并发直传 S3（每个文件独立 progress）
  yield all(uploads.map((up, idx) =>
    call(uploadToS3, fileList[idx].originFile, up.presignedUrl, { 'Content-Type': fileList[idx].originFile.type },
      (pct: number) => put({ type: 'updateUploadProgress', payload: { uid: fileList[idx].uid, progress: pct } }))
  ));

  // Step 3: 逐文件通知后端完成（每文件一次）
  yield all(uploads.map((up) =>
    call(completeUpload, { fileId: up.fileId, etag: up.etag, actualSize: up.actualSize })
  ));

  // Step 4: 跳转（task.status 已被 Java 推进到 PROCESSING）
  history.push(`/financial/upload/${taskId}`);
}
```

**safety 设计**:
- presigned PUT URL 生存期: 15 分钟（Java 配置，上传时间宽裕）
- presigned GET URL 生存期: 5 分钟（Java 配置，视图查看短期即可，前端自动续签）
- 过期后用户点击"重试" → 前端重新调 `POST /upload-urls`（只为失败的文件）
- 前端不能把 presignedUrl 存入 localStorage（泄露风险），只在 dva 内存态保存
- Bucket 策略: `s3:PutObject` 仅对 presigned URL 有效（普通 GET/PUT 拒绝）

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
        └── 验证通过 → POST /api/v1/docparse/tasks/{id}/verify
              ├── 无冲突 → 跳转 ConfirmPage (conflicts = [])
              └── 有冲突 → 跳转 ConfirmPage (conflicts 填充)
```

**噪音数据清除**: 用户可通过右键菜单或行尾操作按钮执行 Remove Row / Remove Column，清除 AI 误提取的噪音数据后重新通过硬验证。

## 5. 轮询状态管理（2026-04-20 重写：对齐两级状态模型）

### 5.1 状态 → 页面映射

前端根据 `GET /docparse/tasks/{id}/status` 返回的 **task.status**（批次级）精确映射到不同页面：

| task.status | 前端页面 | 显示内容 |
|------------|---------|---------|
| `DRAFT` | UploadPage | 任务已创建，文件待上传（刚点击"新建任务"或"基于此任务修订"时的初始态） |
| `UPLOADING` | UploadPage | 文件上传进度条（presigned URL 直传进度） |
| `UPLOAD_COMPLETE` | ProcessingPage | "所有文件已上传，等待解析..." |
| `PROCESSING` | ProcessingPage | 文件级进度列表（见 §5.2）|
| `SIMILARITY_CHECKING` | ProcessingPage（通知浮层）| "解析完成，正在发送通知..."（在进入 Review 前的持久化状态，见 §5.6） |
| `SIMILARITY_CHECKED` | ProcessingPage（自动跳转）| "通知已发送，正在进入审核..."（短暂过渡态） |
| `REVIEWING` | ReviewPage（自动跳转）| 并排审核页 |
| `VERIFYING` | ConfirmPage（Stage 1） | Verify Data Summary + 进度条 |
| `CONFLICT_RESOLUTION` | ConfirmPage（Stage 2）| 冲突解决界面 |
| `COMMITTING` | ConfirmPage（Stage 3）| "正在写入 LG..." Loading |
| `MEMORY_LEARN_PENDING` | SuccessPage（记忆学习浮层）| "财务数据已写入，记忆学习排队中..."（见 §5.7） |
| `MEMORY_LEARN_IN_PROGRESS` | SuccessPage（记忆学习浮层）| "记忆学习中 (2/3 文件)..." |
| `MEMORY_LEARN_COMPLETE` | SuccessPage | 记忆学习完成 Toast + "已学习 5 条新规则" |
| `MEMORY_LEARN_FAILED` | SuccessPage（警告浮层）| "记忆学习失败，可重试"（不影响财务数据） |
| `COMMITTED` | SuccessPage | 完全终态 + Benchmark Info + "基于此任务修订"按钮 |
| `SUPERSEDED` | HistoricalTaskView（只读）| 显示 "此任务已被修订版 v2 替代" + 跳转到最新版本链接 |
| `FAILED` | ErrorPage | 失败原因 + "基于此任务修订" 按钮（唯一恢复路径） |
| `EXPIRED` | 无页面（不出现在列表） | DRAFT 超 24h 自动过期，S3 已清理 |

**重要：`FAILED` 是终态**（Q7 方案 B 下），只有以下 3 种情况：
1. 所有文件 FILE_FAILED（Phase 2 Python 全部失败）
2. Sweeper 自动推进（VERIFYING > 10min）
3. MEMORY_LEARN_FAILED 达到 3 次重试上限（但此时 fi_* 已写，实际是"带标记的终态"）

**Commit 失败不进 FAILED**。`POST /commit` 抛异常时 Java 事务回滚，`task.status` 自动回到 `REVIEWING`，用户在 ErrorModal 点击"重试"即可再次 commit（数据未写入，幂等安全）。

### 5.2 文件级进度展示（task.status=PROCESSING 时）

status API 响应示例:
```json
{
  "taskId": "xxx",
  "status": "PROCESSING",
  "totalFiles": 3,
  "completedFiles": 1,
  "failedFiles": 0,
  "files": [
    { "fileId": "a", "filename": "2024_PnL.pdf",  "status": "REVIEW_READY",   "stage": null,           "progressPct": 100 },
    { "fileId": "b", "filename": "BS.xlsx",       "status": "PROCESSING",    "stage": "MAPPING_LLM",  "progressPct": 72 },
    { "fileId": "c", "filename": "CashFlow.pdf",  "status": "QUEUED",        "stage": null,           "progressPct": 0  }
  ]
}
```

**ProcessingPage 布局**:
```
┌─────────────────────────────────────────────────────┐
│  正在解析文件 (1/3 完成)                              │
│  ───────────────────────────────────────────────    │
│  ✓ 2024_PnL.pdf          已完成              100%    │
│  ⟳ BS.xlsx               LLM 推理中...       72%     │  ← 实时显示当前阶段
│  ⋯ CashFlow.pdf          排队中              0%      │
└─────────────────────────────────────────────────────┘
```

**processing_stage → 中文显示**（12 个子状态，对齐 java-design.md 与 python-design.md §1.3.1）:

| stage | 显示文案 | progressPct 区间 | stageDetail 附加显示 |
|-------|---------|------------------|---------------------|
| `PREPROCESS_PENDING` | 预处理等待中... | 0-5% | — |
| `PREPROCESSING` | 预处理中（PDF→图像 / Excel→JSON）... | 5-15% | — |
| `EXTRACTING` | 正在提取文档内容... | 15-30% | `pageIndex/totalPages` → "第 3/8 页" |
| `CLASSIFYING` | 文档类型识别中... | 30-35% | — |
| `MAPPING_RULE` | 规则引擎映射中... | 35-45% | — |
| `MAPPING_MEMORY_LOOKUP` | 记忆查询中... | 45-55% | `matchedMemoryCount` → "查到 12 条候选" |
| `MAPPING_MEMORY_APPLY` | 记忆应用中... | 55-65% | `appliedMemoryCount/totalRowCount` → "8/47 已应用" |
| `MAPPING_MEMORY_COMPLETE` | 记忆匹配完成 | 65-70% | — |
| `MAPPING_LLM` | LLM 推理中... | 70-85% | `processedRowCount/remainingRowCount` → "已处理 15 / 剩余 24" |
| `VALIDATING` | 数据验证中... | 85-95% | — |
| `PERSISTING` | 正在保存... | 95-100% | `insertedRowCount` → "已写入 47 行" |
| `REVIEW_READY` | 处理完成 | 100% | — |

**设计要点**:
- 每个 stage 和 progressPct 都持久化到 DB（`doc_parse_file.processing_stage`）
- 前端轮询拿到最新状态后直接展示，Python 崩溃重启也能继续
- stageDetail 是可选附加信息（JSON），前端渲染时用 `Tooltip` 悬浮展示避免主列表过挤

### 5.3 轮询生命周期

```
ProcessingPage mounted
  │
  ▼
开始轮询: GET /docparse/tasks/{id}/status (每 2s)
  │
  ├── task.status = UPLOADING / UPLOAD_COMPLETE
  │     UI: 显示 "等待解析..." + 所有文件显示 QUEUED
  │     继续轮询
  │
  ├── task.status = PROCESSING
  │     UI: 文件级进度列表（见 §5.2）
  │     每个文件显示当前 stage + progressPct
  │     继续轮询
  │
  ├── task.status = REVIEWING
  │     UI: "解析完成，正在跳转..."
  │     ★ 停止轮询
  │     ★ history.replace → /financial/review/:taskId
  │
  ├── task.status = FAILED
  │     UI: 显示 failedFiles 列表 + 错误信息
  │     ★ 停止轮询
  │     ★ 显示 [重试失败文件] / [返回] 按钮
  │
  └── 其他状态（VERIFYING/COMMITTING/COMPLETED）
        这些状态通常不在 ProcessingPage 看到（用户已跳到 ConfirmPage）
        如果看到（用户直接访问了 /processing URL）→ 自动跳转到对应页面

超时保护:
  最大轮询次数 = 150 (2s × 150 = 5 分钟)
  超时 → 显示 "处理时间较长，是否继续等待？" 让用户选择继续轮询或离开

清理机制:
  ├── 组件 unmount → useEffect cleanup → clearInterval
  ├── 路由离开 → dva subscription → dispatch stopPolling
  └── 浏览器关闭 → 服务端 LangGraph checkpoint 保存状态
        用户重新访问 → 恢复到最近状态（见 §5.5）
```

### 5.4 批次完成判定（重要）

**task.status=REVIEWING 的条件**：所有**非 FAILED** 文件 status=REVIEW_READY

**task.status=COMPLETED 的条件**：所有**非 FAILED** 文件 status=FILE_COMMITTED（批次结束）

前端**不需要**自己计算这些，Java 端状态机会自动推进，前端只需根据 task.status 做页面跳转。

**失败文件的处理**：
- 部分文件失败不阻塞批次（继续其他文件）
- ProcessingPage 显示失败文件的错误信息
- ReviewPage 只显示 REVIEW_READY 的文件（失败的单独在顶部提示 "3 个文件中有 1 个解析失败"）
- ConfirmPage 只提交成功的文件

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
  ├── PATCH /api/v1/docparse/tasks/{id}/review
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

## 12. Task 修订（Revision）UI

### 12.1 业务场景

历史任务提交（`task.status = COMMITTED`）后，用户可能发现个别映射错误、需要补充新文件、或季度结束后追加期间数据。**不是重新上传**（会产生冲突），而是"基于历史任务创建修订版"：

- 修订版保留原任务的所有文件 + 映射结果作为起点
- 用户可以增删文件、修改映射
- 最终提交时会**覆盖**原期间的 `fi_*` 数据（或用户选择"保留原值"）
- 原任务状态变为 `SUPERSEDED`，修订版成为当前版本

### 12.2 入口与页面流转（Q5 方案 A：仅原上传者）

```
Financial Entry 列表页
  ├── 每行显示: 任务名 + 期间 + 提交时间 + 版本徽章 (v1/v2/v3) + 上传者头像
  └── 历史任务右侧操作列:
        [查看]（所有同公司用户可见）
        [基于此任务修订]（⚠️ 仅 task.uploaded_by === current_user.id 可见）
                    ↓
                点击后:
                  1. 调 POST /api/v1/docparse/tasks/{parentTaskId}/revise
                     若当前用户不是原上传者 → 403 ACCESS_DENIED（前端已在 UI 层隐藏按钮，API 层是兜底）
                     Java 返回新建的 draft task（status=DRAFT, parent_task_id 已填充）
                  2. 把原任务的文件作为"已有文件"展示到新 UploadPage（只读，可删除）
                  3. 进入 UploadPage，路径 /financial/upload?taskId={newTaskId}&parentTaskId={parentTaskId}
                    用户可追加新文件或删除原文件
                  4. 常规流程继续（上传 → 解析 → 审核 → 确认）
```

**按钮可见性条件**（前端组件 `RevisionButton`）:
```typescript
const RevisionButton: React.FC<{ task: Task; currentUser: User }> = ({ task, currentUser }) => {
  // 条件 1: 当前用户是原上传者（服务端权限的 UI 镜像）
  const isUploader = task.uploadedBy === currentUser.id;
  // 条件 2: task 状态允许修订
  const isRevisable = ['COMMITTED', 'COMPLETED', 'SUPERSEDED'].includes(task.status);

  if (!isUploader || !isRevisable) return null;  // 不是原上传者，按钮不渲染

  return <Button onClick={handleRevise}>基于此任务修订</Button>;
};
```

**为什么不让 portfolio manager 也能修订**:
- 修订会覆盖 fi_* 财务数据，责任必须明确到原作者
- 如果 portfolio manager 发现问题，应通过评论或 Linear/Asana 工单通知原作者
- 原作者离职的场景通过运维流程（DB 层面变更 uploaded_by）处理，不走修订后门

### 12.3 UploadPage 的修订态 UI

```
┌──────────────────────────────────────────────────────┐
│  📝 修订任务 v2                                        │
│  基于 v1 (2026-01-15 提交)                            │
│  📎 原因: [请描述修订原因（必填，≥ 10 字）...]        │
│  ──────────────────────────────────────────────────  │
│  继承的文件：                                          │
│    📄 2024_PnL.pdf    [保留] [删除]                   │
│    📄 BS.xlsx        [保留] [删除]                    │
│                                                      │
│  新增文件：                                            │
│    [拖拽区域 / + 添加文件]                             │
└──────────────────────────────────────────────────────┘
```

**交互要点**:
- "继承的文件" 区块有明确视觉分组（浅灰背景 + "Inherited" 徽章）
- 删除继承文件时弹出确认："此操作将使 {filename} 的数据不在修订版中，原任务的数据仍保留在 LG 中。确定删除?"
- "修订原因" 是必填字段（`revision_reason`），对应 `doc_parse_task.revision_reason`，最少 10 字符
- 修订原因会在 `SuccessPage` 和 `Financial Entry` 历史列表中展示（用户可回溯）

### 12.4 ConfirmPage 的修订态 UI

修订版提交时，ConfirmPage 的冲突展示会标明**上一个版本的值**：

```
┌──────────────────────────────────────────────────────┐
│  冲突: 2024-03 的 Revenue                              │
│  ──────────────────────────────────────────────────  │
│  当前 LG 值 (来自 v1): $1,250,000                     │
│  修订版值: $1,275,000                                  │
│                                                      │
│  选择操作:                                             │
│    ○ 用修订版覆盖 (推荐)                               │
│    ○ 保留 v1 值                                        │
│                                                      │
│  备注（可选）:                                         │
│    [解释为何这样处理...]                                │
└──────────────────────────────────────────────────────┘
```

### 12.5 SuccessPage 的修订链显示

```
┌──────────────────────────────────────────────────────┐
│  ✓ 修订版 v2 已提交                                    │
│  修订原因: "Q1 末追加 March 数据"                      │
│  ──────────────────────────────────────────────────  │
│  版本链:                                               │
│    v1 (2026-01-15) → v2 (当前，2026-04-20)           │
│                                                      │
│  已覆盖的期间: 2024-01, 2024-02                        │
│  新增的期间: 2024-03                                   │
│                                                      │
│  [查看 Benchmark] [返回 Financial Entry]              │
└──────────────────────────────────────────────────────┘
```

### 12.6 SUPERSEDED 状态的任务展示

原任务（v1）在 Financial Entry 列表中不会消失，但展示会变化：

- 版本徽章变为灰色 "v1 (已被 v2 替代)"
- 点击"查看"进入只读页面，顶部横幅提示："此任务已被 v2 替代。[跳转到最新版本]"
- 不显示"基于此任务修订"按钮（只能从最新版本上修订）

### 12.7 dva model 调整

新增字段:
```typescript
interface TaskRevision {
  parentTaskId: string;           // 原任务 ID
  parentRevisionNumber: number;   // 原任务版本号
  revisionReason: string;         // 必填，≥ 10 字符
  inheritedFileIds: string[];     // 继承的文件 ID（用户可删减）
}

interface FinancialUploadModelState {
  // ... 原有字段
  revision: TaskRevision | null;  // 非 null 时表示当前是修订态
}
```

新增 effect: `initRevision({ parentTaskId })` 调用后端创建 draft task 并拉取原文件列表

## 13. 通知与记忆学习状态 UI（Q16 简化版）

### 13.1 通知系统的简化

**Q16 决策（2026-04-20）**: 系统**不主动推送通知**（不发邮件、不发站内信、不推 WebSocket）。`doc_parse_notification` 表只作为"事件日志"记录任务状态变化，用户通过以下方式自行发现：

1. **LG Dashboard "待处理任务" 模块**：查 `doc_parse_task.status IN ('REVIEWING', 'VERIFYING', 'CONFLICT_RESOLUTION', 'MEMORY_LEARN_PENDING')` 的任务列表，用户登录就能看到
2. **NotificationIndicator 🔔 徽章**（仍保留）：读 `doc_parse_notification` 事件日志，展示"你上次登录以来发生的事件"

**状态推进**:
```
PROCESSING → SIMILARITY_CHECKING → SIMILARITY_CHECKED → REVIEWING
              ↑ 瞬间完成  ↑ 瞬间完成
              （仅写一条事件日志）
```

`SIMILARITY_CHECKING` 和 `SIMILARITY_CHECKED` 是**瞬态**（毫秒级），因为没有真的发送流程，只是写一条 `doc_parse_notification` 行就推进。

### 13.2 ProcessingPage 状态展示（无通知等待）

```
┌──────────────────────────────────────────────────────┐
│  📄 所有文件解析完成                                   │
│  ──────────────────────────────────────────────────  │
│  正在进入审核页面...                                   │
└──────────────────────────────────────────────────────┘

（几乎不可见，因为 SIMILARITY_CHECKING → SIMILARITY_CHECKED → REVIEWING 瞬间完成）
```

- 轮询 `GET /tasks/{id}/status`，一旦收到 `status=REVIEWING` 立即跳转 ReviewPage
- 没有"邮件发送进度"展示
- 没有"跳过通知进入审核"按钮（不需要）

### 13.3 NotificationIndicator（全局事件徽章，App 头部）

作为"事件查看器"而非"推送通知器"。读 `doc_parse_notification` 表展示事件：

```
┌──────────────────────────────────────────────────────┐
│  LG Dashboard      👤 alice          🔔 3            │  ← 未查看事件数
└──────────────────────────────────────────────────────┘

 点击 🔔 后:
┌────────────────────────────────────────────────────┐
│  近期事件 (3)                              [标记已查看] │
│  ─────────────────────────────────────────────────  │
│  📄 2026-04-20 10:30  PARSE_COMPLETE                │
│     您上传的 Q1 财务数据已解析完成 →                  │
│                                                    │
│  ✅ 2026-04-19 16:12  COMMIT_COMPLETE                │
│     您提交的 2024-03 数据已写入 LG                   │
│                                                    │
│  🧠 2026-04-18 09:00  MEMORY_LEARN_COMPLETE          │
│     系统已学习您的 5 条映射修正                      │
└────────────────────────────────────────────────────┘
```

**与旧推送式通知的区别**:
- 不弹出、不响声、不发邮件 —— 用户不打开就不知道
- 用户关闭浏览器再回来，事件列表还在（永久保留）
- "已查看"仅是 UI 标记（存 localStorage），不影响 DB 记录

**数据源**: `GET /api/v1/docparse/tasks/events?companyId=...&since=...` 返回最近 30 天的 `doc_parse_notification` 事件。

### 13.4 记忆学习悬浮条（SuccessPage）

**场景**：用户在 ConfirmPage 提交后跳转到 SuccessPage，此时 task 状态为 `MEMORY_LEARN_PENDING`，但财务数据已经写入 LG（不影响用户查看数据）。悬浮条展示后台的记忆学习进度：

```
SuccessPage
┌──────────────────────────────────────────────────────┐
│  ✓ 财务数据已成功写入 LG                               │
│                                                      │
│  [查看 Benchmark]  [查看 Financial Statements]        │
└──────────────────────────────────────────────────────┘

     页面右下角悬浮条（遵循 antd Notification 风格）:
     ┌────────────────────────────────────┐
     │  🧠 记忆学习中 (2/3 文件)...         │
     │  ──────────────────────────────    │
     │  完成后将在下次上传中自动应用您的    │
     │  修正，减少手动调整工作量。          │
     └────────────────────────────────────┘
```

**状态变化**:
| task.status | 悬浮条内容 |
|-------------|------------|
| `MEMORY_LEARN_PENDING` | "记忆学习排队中..." |
| `MEMORY_LEARN_IN_PROGRESS` | "记忆学习中 (N/M 文件)..."（从 stageDetail.processedFileCount/totalFileCount） |
| `MEMORY_LEARN_COMPLETE` | Toast 闪现 "已学习 5 条新规则" + 悬浮条消失 |
| `MEMORY_LEARN_FAILED` | "记忆学习失败，不影响已提交的财务数据 [重试]" |

### 13.5 记忆学习失败重试

```
用户点击 [重试] 按钮
  → POST /api/v1/docparse/tasks/{taskId}/memory-learn/retry
  → Java 校验 attempt_number < 3（读 doc_parse_memory_learn_log 计数）
  → Java 重新向 ocr-memory-learn-queue 发送消息
  → doc_parse_task.status 从 MEMORY_LEARN_FAILED 回到 MEMORY_LEARN_PENDING
  → 悬浮条切回 "记忆学习排队中..."
```

**限制**: 最多重试 3 次（`doc_parse_memory_learn_log` 的 `attempt_number <= 3`）。3 次全失败后 API 返回 400 `RETRY_LIMIT_EXCEEDED`，前端显示"已达重试上限"。

**重要**：记忆学习失败**不影响**财务数据（`fi_*` 已写入）。任务本身可视为完成，只是少了这次积累的记忆规则。

### 13.6 轮询策略调整

SuccessPage 的轮询逻辑调整（仅当 `task.status` 在 `MEMORY_LEARN_*` 状态时启用）：

```typescript
// SuccessPage 组件
useEffect(() => {
  if (!['MEMORY_LEARN_PENDING', 'MEMORY_LEARN_IN_PROGRESS'].includes(task.status)) return;

  const interval = setInterval(async () => {
    const latest = yield call(getTaskStatus, taskId);
    if (latest.status === 'COMMITTED') {
      clearInterval(interval);
      notification.success({ message: `已学习 ${latest.memoryLearnResult.newMemoryCount} 条新规则` });
    } else if (latest.status === 'MEMORY_LEARN_FAILED') {
      clearInterval(interval);
      // 悬浮条切换为失败态
    }
    // 更新 state，触发 FloatingPanel 重新渲染
  }, 3000);  // 3s 一次（比上传页 2s 慢，因为学习本身较慢）

  return () => clearInterval(interval);
}, [task.status]);
```

### 13.7 dva model 调整

```typescript
interface MemoryLearnProgress {
  processedFileCount: number;
  totalFileCount: number;
  newMemoryCount: number;
  updatedMemoryCount: number;
  error?: string;
  retryCount: number;
}

interface FinancialUploadModelState {
  // ... 原有字段
  memoryLearnProgress: MemoryLearnProgress | null;

  // Q16 简化后：事件日志（不含 recipient/channel）
  notifications: Array<{
    id: string;
    eventType: string;
    payload: Record<string, unknown>;
    createdAt: string;
  }>;

  // 2026-04-20 新增：相似度提示（Phase 2.5 产出）
  similarityHints: SimilarityHint[];
}

interface SimilarityHint {
  id: string;
  taskId: string;
  rowIdA: string;
  rowIdB: string;
  labelA: string;
  labelB: string;
  fileIdA: string;
  fileIdB: string;
  similarityScore: number;            // 0.900 ~ 1.000
  userDecision: 'MERGED' | 'IGNORED' | null;
  decidedAt: string | null;
  decidedBy: number | null;
}
```

---

## 14. 相似度提示 UI（Phase 2.5 产出）

### 14.1 场景

AI 提取出的 `account_label` 可能因拼写/措辞差异而被误判为不同账户，例如：

```
文件 1:  "AWS Hosting"           → 映射到 COGS
文件 2:  "AWS hosting costs"     → 映射到 R&D Expenses    ← 实际应该是同一账户
同一文件内:  "Total Revenue"
             "Total Revenues"    ← 重复行（AI 没合并）
```

Phase 2.5 后 Python 把这些"高相似度对"写入 `doc_parse_similarity_hint` 表，前端在 ReviewPage 顶部展示横幅，让用户决策。

### 14.2 SimilarityHintBanner 组件

```
ReviewPage 顶部（CurrencyWarningBanner 下方）
┌───────────────────────────────────────────────────────────────────┐
│  ⚠ 检测到 3 组可能相似的指标，请确认是否为同一账户                  │
│                                                                    │
│  ▸ "AWS Hosting" (文件 1) ↔ "AWS hosting costs" (文件 2)   95%    │
│      [合并] [忽略]                                                  │
│                                                                    │
│  ▸ "Total Revenue" ↔ "Total Revenues" (同一文件)           99%    │
│      [合并] [忽略]                                                  │
│                                                                    │
│  ▸ "Office Rent" ↔ "Rent Expense"                          91%    │
│      [合并] [忽略]                                                  │
│                                                                    │
│  [全部忽略]                                                         │
└───────────────────────────────────────────────────────────────────┘
```

**组件结构**:
```
SimilarityHintBanner
  ├── HintSummary (顶部：未处理 hint 数量 + "全部忽略"按钮)
  └── HintList
        └── HintItem[]
              ├── ScoreTag (95%, 颜色随 score 变化)
              ├── LabelA + FileIndicator
              ├── '↔' 连接符
              ├── LabelB + FileIndicator
              ├── MergeButton
              └── IgnoreButton
```

### 14.3 用户决策处理

**合并（MERGED）**:
```
点击"合并" → 弹出 MergeConfirmModal:
  "将 '{labelA}' 和 '{labelB}' 视为同一账户吗？"
  "合并后，{labelB} 的所有数值会被归入 {labelA}，且映射到相同的 LG 分类。"
  [确认合并] [取消]

→ PATCH /api/v1/docparse/similarity-hints/{hintId}
  body: { userDecision: "MERGED" }
→ 后端:
    1. 把 rowIdB 的映射指向 rowIdA 的分类
    2. 把 rowIdB 的 cell_values 合并到 rowIdA（同 period 值相加）
    3. 标记 rowIdB.deleted = true
    4. hint.userDecision = "MERGED"
→ 前端 hint 从列表消失，右侧数据表刷新
```

**忽略（IGNORED）**:
```
点击"忽略" → 直接调 PATCH
→ PATCH /api/v1/docparse/similarity-hints/{hintId}
  body: { userDecision: "IGNORED" }
→ hint 从列表消失（本次 session 不再展示）
→ 数据保持原样（两条 row 都保留，映射保持 AI 的原判）
```

**全部忽略**:
```
点击"全部忽略" → 确认对话框 → 批量 PATCH
→ 所有未处理的 hint 标记为 IGNORED
→ Banner 消失
```

### 14.4 HintItem 视觉细节

```typescript
const ScoreColor = (score: number) => {
  if (score >= 0.98) return 'red';     // 极高相似度，几乎肯定是重复
  if (score >= 0.95) return 'orange';  // 很高
  return 'yellow';                      // 0.90-0.95
};

const FileIndicator: React.FC<{ fileId: string }> = ({ fileId }) => {
  // 从 extractedTables 找到 fileId 对应的 filename，展示简短缩写
  const filename = useFileName(fileId);
  return <Tag color="blue">{filename}</Tag>;
};
```

**跨文件 vs 同文件的视觉区分**:
- 跨文件：两边各显示 `<FileIndicator>`（蓝色 tag）
- 同文件：右侧显示 "（同一文件）"

### 14.5 dva effect

```typescript
*fetchSimilarityHints({ payload: { taskId } }, { call, put }) {
  const hints = yield call(getSimilarityHints, taskId);
  yield put({ type: 'setState', payload: { similarityHints: hints } });
}

*mergeSimilarityHint({ payload: { hintId } }, { call, put, select }) {
  yield call(patchSimilarityHint, hintId, { userDecision: 'MERGED' });
  // 重新拉取 extractedTables（因为数据已变化）
  const taskId = yield select(s => s.financialUpload.sessionId);
  yield put({ type: 'fetchResult', payload: { sessionId: taskId } });
  // 从 hints 列表移除
  yield put({ type: 'removeSimilarityHint', payload: { hintId } });
}

*ignoreSimilarityHint({ payload: { hintId } }, { call, put }) {
  yield call(patchSimilarityHint, hintId, { userDecision: 'IGNORED' });
  yield put({ type: 'removeSimilarityHint', payload: { hintId } });
}

*ignoreAllSimilarityHints(_, { call, put, select }) {
  const hints: SimilarityHint[] = yield select(s => s.financialUpload.similarityHints);
  yield all(hints
    .filter(h => !h.userDecision)
    .map(h => call(patchSimilarityHint, h.id, { userDecision: 'IGNORED' }))
  );
  yield put({ type: 'setState', payload: { similarityHints: [] } });
}
```

### 14.6 失败容忍

- `SIMILARITY_CHECK_FAILED` 状态下前端**不显示** Banner（因为没有 hint 数据）
- 不阻塞用户审核流程 —— 没有提示只是少了一个辅助，数据本身不受影响
```
