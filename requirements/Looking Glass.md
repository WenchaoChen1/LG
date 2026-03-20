# Looking Glass 文档上传工作流 需求规格

> 版本：v1.0
> 创建时间：2026-03-12
> 来源文档：Looking Glass.docx
> 状态：待确认

---

## 1. 业务背景与目标

### 1.1 背景
Looking Glass (LG) 平台需要支持 CIO/财务分析师将企业财务报表（PDF、图片、Excel）上传后，通过 OCR 或直接解析提取结构化财务数据，经用户审查与 AI 辅助分类，最终写入 LG 标准 Schema。

当前阶段（MVP）：构建独立的文档上传页面，完成文件上传 → OCR/解析 → 并排审查 → AI 映射的前端展示闭环，**暂不写入数据库**，后端由 Python FastAPI 服务承接。

### 1.2 目标
1. 提供独立的文档上传入口页面，支持 PDF / 图片 / Excel 三类财务报表
2. 后端（Python FastAPI）完成 OCR/解析，返回结构化提取数据
3. 前端实现并排审查界面，支持 Raw View / Standardized View 切换与内联编辑
4. AI 自动映射提取的 line items 至 LG 17 个标准类别，结果在前端展示
5. MVP 阶段提取结果仅在前端维护状态，不持久化数据库

### 1.3 成功指标
- 支持上传 PDF / 图片（JPG、PNG）/ Excel（xlsx）/ CSV 文件
- OCR 或解析结果在前端正确展示，字段对应准确率 ≥ 90%
- AI 映射覆盖率 100%（所有 line items 均获得建议类别，即使置信度低）
- 并排审查页面可正常编辑、切换模式，编辑内容不丢失
- 移动端与桌面端均可正常使用

---

## 2. 用户故事

| 角色 | 操作 | 价值 |
|------|------|------|
| 作为财务分析师 | 我希望拖拽上传 PDF/Excel 财务报表 | 以便快速导入多份文档而无需手动录入 |
| 作为财务分析师 | 我希望并排查看原始文档与提取数据 | 以便直观对比并纠正 OCR 识别偏差 |
| 作为财务分析师 | 我希望在审查界面直接编辑提取的数值和标签 | 以便在保存前确保数据准确 |
| 作为财务分析师 | 我希望在 Raw View 和 Standardized View 间切换 | 以便既能看原始行项目，也能看 LG 分类结果 |
| 作为 CIO | 我希望系统自动将财务行项目映射到 LG 标准类别 | 以便减少手动分类工作量 |
| 作为投资组合经理 | 我希望上传的文档类型被自动识别（P&L/BS/Cash Flow） | 以便无需手动标注报表类型 |

---

## 3. 功能需求

### 3.1 核心功能流程

```
Step 1: 文档上传
  └── 用户选择/拖拽文件（PDF/图片/Excel）
  └── 前端校验（格式、大小）
  └── 上传至 Python 后端（/api/lg/upload）
  └── 进入 Step 2

Step 2: 数据提取（后端异步处理）
  └── PDF/图片 → OCR → 结构化 line items
  └── Excel/CSV → 直接解析 → 结构化 line items
  └── 文档类型自动识别（P&L / Balance Sheet / Cash Flow / Proforma）
  └── 报告期间自动推断
  └── 前端轮询进度状态

Step 3: 并排审查与内联编辑
  └── 左侧：原始文档预览（PDF/图片/Excel）
  └── 右侧：提取数据（Raw View / Standardized View）
  └── 用户内联编辑数值、标签、类别
  └── 用户确认 → 触发 Step 4 AI 映射（或同步进行）

Step 4: AI 辅助账户映射（后端自动，结果展示在 Step 3 Standardized View）
  └── 每条 line item → 建议 LG 类别
  └── 结果返回前端，用户可在审查界面修改

Step 5: Review & Save（MVP 阶段：仅前端展示，不写 DB）
  └── 汇总待写入数据预览
  └── 检测重复/冲突（前端逻辑）
  └── 用户确认（数据保留在前端状态，供后续扩展写入 DB）
```

### 3.2 边界条件
- 单文件最大 20MB（可配置）
- 单批次总大小最大 100MB（可配置）
- 支持文件类型：`.pdf`、`.jpg`、`.jpeg`、`.png`、`.xlsx`、`.csv`
- Processing 状态进入后不可取消
- 多页文档中无财务内容的页面右侧显示"该页无有效数据"提示
- 批量上传时，部分文件失败不影响其他文件继续上传
- 同一批次可能包含多种财务报表类型（P&L + Balance Sheet 等）

### 3.3 异常处理

| 场景 | 错误提示 | 处理方式 |
|------|---------|---------|
| 文件超过 20MB | "File exceeds 20MB limit" | 不上传，前端标红该文件卡片 |
| 批次总大小超 100MB | "Total batch size exceeds 100MB" | 阻止上传，提示用户减少文件 |
| 不支持的文件类型 | "Unsupported file type. Please upload PDF, image, or Excel." | 前端拦截，不上传 |
| OCR 未检测到表格 | "No financial tables found in this document" | 右侧面板显示提示，源文档仍展示 |
| OCR 质量差 | "Low OCR quality detected, please review carefully" | 显示警告提示，允许继续 |
| 上传失败（网络/服务器错误） | "Upload failed. Please retry." | 文件卡片显示重试按钮 |
| 解析超时（>60s） | "Processing is taking longer than expected..." | 前端轮询超时后提示用户重试 |
| 无法识别文档类型 | 归类为 "Financial Summary / Misc"，标记待确认 | 用户可在审查界面手动修改 |

---

## 4. API 设计

> 后端：Python FastAPI（`CIOaas-python/source/`），路由前缀 `/api/lg/`

### 4.1 新增接口

**POST /api/lg/upload**
- 描述：上传单个财务文档文件
- 请求：`multipart/form-data`，字段 `file`（文件）、`companyId`（string，可选 MVP 阶段）
- 响应：
  ```json
  {
    "code": 200,
    "data": {
      "taskId": "uuid",
      "fileName": "Q1_2024_PL.pdf",
      "fileType": "pdf",
      "status": "pending"
    },
    "message": "success"
  }
  ```

**GET /api/lg/task/{taskId}/status**
- 描述：轮询提取任务状态
- 响应：
  ```json
  {
    "code": 200,
    "data": {
      "taskId": "uuid",
      "status": "processing | completed | failed",
      "progress": 60,
      "stage": "Running OCR | Preparing review",
      "errorMessage": null
    }
  }
  ```

**GET /api/lg/task/{taskId}/result**
- 描述：获取提取完成后的结构化数据
- 响应：
  ```json
  {
    "code": 200,
    "data": {
      "taskId": "uuid",
      "documentType": "P&L | Balance Sheet | Cash Flow | Proforma | Misc",
      "reportPeriods": ["2024-01", "2024-02"],
      "pages": [
        {
          "pageIndex": 1,
          "hasFinancialData": true,
          "previewUrl": "...",
          "lineItems": [
            {
              "id": "uuid",
              "label": "Revenue",
              "values": { "2024-01": 1000000, "2024-02": 1200000 },
              "sourceRef": { "page": 1, "row": 3 },
              "suggestedCategory": "Revenue",
              "mappingSource": "AI",
              "originalLabel": "Revenue",
              "originalValues": { "2024-01": 1000000, "2024-02": 1200000 }
            }
          ]
        }
      ]
    }
  }
  ```

**POST /api/lg/task/{taskId}/mapping**
- 描述：（可选）触发或重新触发 AI 映射
- 请求体：`{ "lineItems": [ { "id": "uuid", "label": "..." } ] }`
- 响应：每条 line item 的 `suggestedCategory`

### 4.2 前端状态接口（MVP 阶段无需后端）
- 编辑操作（修改数值/标签/类别）仅在前端 state 维护
- Review & Save 的最终数据结构由前端组装，暂不调用写入接口

---

## 5. 数据模型

> MVP 阶段不写数据库，以下为前端内存数据结构定义，供后续扩展参考。

### 5.1 前端核心数据结构

```typescript
// 上传任务
interface UploadTask {
  taskId: string;
  fileName: string;
  fileSize: number;
  fileType: 'pdf' | 'image' | 'excel' | 'csv';
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  stage?: string;
  result?: ExtractionResult;
}

// 提取结果
interface ExtractionResult {
  documentType: 'P&L' | 'Balance Sheet' | 'Cash Flow' | 'Proforma' | 'Misc';
  reportPeriods: string[];           // ['2024-01', '2024-02', ...]
  pages: PageData[];
}

// 页面数据
interface PageData {
  pageIndex: number;
  hasFinancialData: boolean;
  previewUrl: string;
  lineItems: LineItem[];
}

// 行项目
interface LineItem {
  id: string;
  label: string;                     // 用户编辑后的标签
  originalLabel: string;             // 原始提取标签
  values: Record<string, number>;    // 用户编辑后的值 { '2024-01': 1000000 }
  originalValues: Record<string, number>;  // 原始提取值
  sourceRef?: { page: number; row?: number; cell?: string };
  suggestedCategory: LGCategory;    // AI 建议类别
  userCategory?: LGCategory;        // 用户覆盖类别
  mappingSource: 'AI' | 'user';
  isEdited: boolean;
}

// LG 标准 17 类
type LGCategory =
  'Revenue' | 'COGS' | 'S&M Expenses' | 'R&D Expenses' | 'G&A Expenses' |
  'S&M Payroll' | 'R&D Payroll' | 'G&A Payroll' | 'Misc Operating Expenses' |
  'Cash' | 'Accounts Receivable' | 'R&D Capitalized' | 'Other Assets' |
  'Accounts Payable' | 'Long Term Debt' | 'Other Liabilities' | 'Misc';
```

### 5.2 后期扩展（写 DB 时参考）
- 新增表 `lg_upload_task`：存储任务状态、文件引用、关联 company_id
- 新增表 `lg_extracted_line_item`：存储每条提取行项目及 AI 映射结果
- 复用现有 `files` 表（`/storage/files`）存储原始文件
- 复用现有 `finance_manual_data` 表写入最终审查通过的数据

---

## 6. 前端页面与交互

### 6.1 页面/组件

**新增独立页面：**
- 路由：`/companyFinance/documentUpload`（或 `/lg/upload`，待确认）
- 文件：`src/pages/companyFinance/documentUpload/`

**主要组件：**
| 组件 | 文件 | 描述 |
|------|------|------|
| `UploadZone` | `components/UploadZone.tsx` | 拖拽上传区域（桌面）/ 文件选择按钮（移动） |
| `FileCard` | `components/FileCard.tsx` | 单个文件卡片（进度/状态/操作） |
| `FileQueue` | `components/FileQueue.tsx` | 文件队列列表，含 Clear All |
| `ReviewPanel` | `components/ReviewPanel.tsx` | 并排审查主容器 |
| `DocumentPreview` | `components/DocumentPreview.tsx` | 左侧原始文档预览（PDF/图片/Excel） |
| `ExtractedDataTable` | `components/ExtractedDataTable.tsx` | 右侧提取数据表格（Raw/Standardized） |
| `ViewToggle` | `components/ViewToggle.tsx` | Raw View / Standardized View 切换控件 |
| `ReviewSummary` | `components/ReviewSummary.tsx` | Step 5 汇总确认页 |

### 6.2 表单字段与校验

**上传阶段：**
| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|---------|
| 文件 | File[] | 是 | 类型：pdf/jpg/jpeg/png/xlsx/csv；单个 ≤ 20MB；批次总计 ≤ 100MB |
| 公司（companyId） | Select | 否（MVP） | 从现有公司列表选择，MVP 阶段可选填 |

**审查阶段（内联编辑）：**
| 字段 | 类型 | 规则 |
|------|------|------|
| 数值 | Number | 支持负数、小数、货币符号（展示） |
| 行项目标签 | Text | 非空，≤ 200 字符 |
| LG 类别 | Select | 从 17 个标准类别中选择 |

### 6.3 交互逻辑

**Step 1 上传区域：**
- 桌面端：虚线边框大拖拽区，拖拽悬停时边框高亮，区域内显示 PDF/XLSX/图片图标
- 文件添加后展示纵向文件队列，每个文件卡片含：文件名、类型、大小、缩略图、进度条、颜色状态标签、移除/重试按钮
- Pending 状态下显示 Clear All 按钮
- 上传中可继续添加新文件

**Step 2 进度状态：**
- 每个文件独立显示状态：`Pending → Uploading → Processing → Completed / Failed`
- Processing 阶段显示阶段文案：`"Processing document" → "Running OCR" → "Preparing review"`
- 前端以 2s 间隔轮询 `/api/lg/task/{taskId}/status`

**Step 3 并排审查：**
- 左侧文档预览，右侧提取数据；点击右侧行，高亮左侧对应位置
- PDF/图片：按页对应，翻页同步；跨页表格在右侧合并展示
- Excel：按 Sheet 对应，切换 Sheet 同步
- Raw View / Standardized View 切换，Standardized View 中 LG 类别可展开查看底层 line items
- 已编辑字段显示视觉标识（如蓝色边框或标记图标）
- 编辑内容在页面导航时持久保留（前端 state）

**Step 5 Review & Save：**
- 汇总展示：报表类型、报告期、映射/未映射行数、已编辑行数
- 检测前端已有同类型+同期间数据时，弹窗提示 Overwrite / Skip / Cancel
- MVP 阶段点击 Save 后数据保留在前端 state（不调用写入接口）

---

## 7. 权限与角色

| 角色 | 可见 | 可操作 | 依据（role 权限码） |
|------|------|--------|-----------------|
| Admin | 是 | 全部操作（上传/审查/保存） | 默认全权限 |
| 有 `seeAllPortfolio` 的用户 | 是 | 全部操作 | `seeAllPortfolio` 权限码选中 |
| 普通用户（无该权限） | 仅限自己关联的公司 | 仅限自己关联公司的上传操作 | 无 `seeAllPortfolio` |
| 只读用户 | 是 | 仅查看，不可上传/编辑 | 待后端权限扩展时补充 |

> MVP 阶段权限校验可简化，以 `seeAllPortfolio` 作为是否能看到所有公司文件的核心判断。

---

## 8. 非功能需求

- **性能**：
  - 文件上传响应时间 < 3s（20MB 文件在正常网络下）
  - OCR 处理时间：单页 PDF ≤ 10s；多页文档进度实时反馈
  - Excel 解析时间：100 行以内 ≤ 5s
  - 前端审查页面初始加载 < 2s
- **安全**：
  - 文件上传通过 Python 后端转存 S3，前端不直接操作 S3
  - 文件类型白名单校验（前端 + 后端双重）
  - 上传接口需 JWT 鉴权（通过网关）
- **兼容性**：
  - 桌面端：Chrome、Safari、Edge 最新版本
  - 移动端：iOS Safari、Android Chrome
  - 响应式断点：≥ 1024px 双栏并排；< 1024px 可折叠面板
- **可扩展性**：
  - 前端数据结构设计为后续写 DB 预留（`LineItem` 含完整字段）
  - OCR/解析逻辑封装在 Python 服务，前端通过接口调用，解耦

---

## 9. 测试场景

### 9.1 正常流程

| 序号 | 操作步骤 | 预期结果 |
|------|---------|---------|
| T01 | 拖拽一个 PDF 文件到上传区域 | 文件卡片出现，显示 Pending 状态 |
| T02 | 点击上传，等待处理完成 | 状态依次变化：Uploading → Processing → Completed |
| T03 | 上传 Excel 财务报表 | 进入审查页面，左侧展示 Excel Sheet，右侧展示提取数据 |
| T04 | 切换 Raw View / Standardized View | 数据切换，已编辑内容不丢失 |
| T05 | 在 Standardized View 修改某行的 LG 类别 | 类别更新，字段显示已编辑标识 |
| T06 | 编辑某行数值后翻页再回来 | 编辑值仍保留 |
| T07 | 上传包含多个 Sheet 的 Excel | 每个 Sheet 独立展示，左右面板联动切换 |
| T08 | 上传扫描件 PDF（图片型 PDF） | OCR 启动，处理完成后提取行项目展示 |
| T09 | 批量上传 3 个文件 | 3 个文件卡片并行显示进度 |
| T10 | MVP 阶段点击 Save | 数据保留在前端 state，页面显示确认信息 |

### 9.2 异常流程

| 序号 | 异常场景 | 预期结果 |
|------|---------|---------|
| E01 | 上传 30MB 超大文件 | 前端拦截，文件卡片红色标记，提示超限 |
| E02 | 上传 .exe 非支持格式文件 | 前端拦截，不加入队列 |
| E03 | OCR 后未检测到任何财务表格 | 右侧显示"No financial tables found" |
| E04 | Processing 阶段断网 | 轮询失败，文件状态显示 Failed + 重试按钮 |
| E05 | PDF 部分页面无财务内容 | 该页右侧显示"该页无有效数据"，左侧仍展示原始页面 |
| E06 | 移动端上传并审查 | 布局切换为可折叠面板，功能完整可用 |
| E07 | 批量上传中部分文件失败 | 失败文件显示重试按钮，其他文件继续正常流程 |

---

## 10. 验收标准

**Step 1 文档上传**
- [ ] 桌面端拖拽区域正常，悬停时边框高亮
- [ ] 移动端显示 Choose Files 按钮，无拖拽功能
- [ ] 文件卡片展示：名称、类型、大小、进度条、状态标签、移除/重试按钮
- [ ] 超限文件不上传，显示友好错误信息
- [ ] Pending 状态下 Clear All 可用；Processing 后不可取消

**Step 2 数据提取**
- [ ] PDF/图片文件触发 OCR 流程，状态提示正确展示
- [ ] Excel 文件直接解析，所有 Sheet 被处理
- [ ] 文档类型自动识别（P&L / Balance Sheet / Cash Flow / Proforma）
- [ ] 报告期间自动推断（列标题 > Sheet 名 > 文件名）
- [ ] 无财务内容的页面右侧显示提示

**Step 3 并排审查**
- [ ] 左右面板并排展示，点击右侧行高亮左侧对应位置
- [ ] PDF 按页联动翻页；Excel 按 Sheet 联动切换
- [ ] Raw View / Standardized View 切换正常，编辑不丢失
- [ ] 已编辑字段有视觉标识
- [ ] 内联编辑数值、标签、类别均可操作

**Step 4 AI 映射**
- [ ] 所有 line items 均获得 LG 类别建议（不留空）
- [ ] 映射结果在 Standardized View 正确展示
- [ ] 用户修改类别后，标记为 user 来源

**Step 5 Review & Save（MVP）**
- [ ] 汇总页展示待写入数据概览
- [ ] 重复检测弹窗在检测到冲突时正确弹出
- [ ] Save 后前端 state 数据正确保留（控制台或 UI 可验证）
- [ ] 移动端全流程可完整操作

---

## 11. 依赖与影响分析

- **依赖模块**：
  - `CIOaas-python/source/`：新增 OCR 解析路由（`/api/lg/upload`、`/api/lg/task/{id}/status`、`/api/lg/task/{id}/result`）
  - `CIOaas-web/src/pages/companyFinance/`：新增 `documentUpload/` 子页面
  - `config/routes.ts`：新增路由配置
  - 网关路由：需配置 `/api/lg/**` 转发至 Python 服务（端口 8090）
  - Python 依赖：`pdfplumber` 或 `pytesseract`（OCR）、`openpyxl`（Excel）、`fastapi`（已有）

- **受影响模块**：
  - `CIOaas-web/src/pages/companyFinance/`：新增入口页面，不修改现有页面
  - 网关配置（`gstdev-cioaas-gateway`）：新增路由规则
  - 后续扩展写 DB 时：影响 `fi/` 模块（FinanceManualDataController）和 `storage/` 模块

- **风险与注意事项**：
  - OCR 精度依赖图片质量，倾斜/低分辨率文件需提前测试
  - MVP 阶段前端 state 在页面刷新后丢失，需提示用户避免意外刷新
  - Excel 合并单元格处理复杂度较高，需重点测试
  - Python 服务 OCR 处理为耗时操作，前端轮询策略需合理设置间隔和超时
  - 写 DB 阶段需对接现有 `finance_manual_data` 表结构，需确认字段映射方案
