# Excel 预览单元格定位与高亮 — 组件选型调研

> **调研日期**: 2026-09-04
> **调研范围**: 仅评估「Excel 在线预览组件 / 服务能否通过 JS 定位到某 sheet 的某行或某格并高亮 / 获取焦点」这一项能力，含开源与商业方案
> **不在本文范围**: 提取结果 → 原始单元格的坐标溯源改造（Python 渲染层 / DTO / DB 三处新增字段），该部分按可改造处理，另行设计
> **关联文档**: [前端设计](./frontend-design.md) · [需求分析](./requirement-analysis.md) · [系统架构](./system-architecture.md) · [Python 端设计](./python-design.md) · [数据库 Schema](./database-schema.md)

## 目录

- [一、背景与结论](#一背景与结论)
- [二、现状盘点](#二现状盘点)
- [三、协议层不可能的方案](#三协议层不可能的方案)
- [四、可行方案对比](#四可行方案对比)
- [五、逐方案评述](#五逐方案评述)
- [六、已排除方案](#六已排除方案)
- [七、推荐路线](#七推荐路线)
- [八、必做 POC](#八必做-poc)
- [九、交互设计建议](#九交互设计建议)
- [十、未核实清单](#十未核实清单)

---

## 一、背景与结论

**需求**：mapping 页面右侧点击某条目名或某格子，左侧 Excel 预览定位到该值所在的行 / 单元格并高亮或获取焦点，用于提升人工核对提取数据准确性的效率。

**结论**：能实现，但**必须替换当前的微软在线预览 iframe**。这不是集成方式没做对，而是该能力在协议层不存在 —— 微软没有对外开放任何可从宿主页面控制 Excel Online 选区的接口。

替换后可选的方案分两类：

1. **前端自渲染表格**（SheetJS / ExcelJS / FortuneSheet / Univer / AG Grid / SpreadJS 等）—— 定位与高亮完全在自己手里；
2. **私有化部署的在线 Office**（ONLYOFFICE Developer Edition / Collabora）—— 有官方通道但代价高、且存在"选中不滚动"的已知缺陷。

**推荐**：先用 SheetJS（依赖已在项目中）以 1~2 天做出可点击定位的 MVP，验证交互本身是否好用；若"外观不像 Excel"被确认为真痛点，再升级到 ExcelJS 自绘 —— 两者定位模型同构，是升级路径而非二选一。

### 前置说明：坐标溯源是另一件工程

选型只解决"能不能跳"，**跳到哪里**依赖一条目前不存在的数据链路。现状简述（详见排查记录，不在本文展开）：

- Python 提取链路是 `Excel → 裁剪为 HTML → LLM → JSON cells`。openpyxl 在预处理阶段确实读到过物理坐标，但 `_render_html_with_merges` 渲染时丢弃空行空列、label 合并块上移，`keep_rows` / `keep_cols` / `moved` 三份坐标映射只是局部变量，输出的 `<td>` 不带行列索引。
- LLM 回填的 `row_position` / `column_position` 是裁剪后 HTML 的表内序号，之后又被按月重排、跨块同名科目归一 → **与 Excel 物理行列彻底解耦，不可反查**。
- 落库表 `ai_financial_extraction_mapping_data` 有 `table_name`（Excel 场景即 sheet 名）但无 sheet / row / col / cell_ref 任何一列，且 `table_name` 未透出到响应 DTO。

即：**组件选型与坐标溯源是两件必须都做的工程**，本文只覆盖前者。

---

## 二、现状盘点


| 文件类型       | 组件                          | 实现方式                                              | 位置                                                                                          |
| -------------- | ----------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **xlsx / xls** | `OfficeIframePreview`（内联） | **微软 Office Online Viewer iframe**                  | `web/CIOaas-web/src/pages/financial/aiFinancialExtraction/components/FileSelector.tsx:97-120` |
| csv            | `CsvPreview`                  | `fetch` + 自写 parser + 自渲染 `<table>`，上限 500 行 | `components/CsvPreview.tsx`                                                                   |
| pdf            | `PdfPreview`                  | 浏览器原生 PDFium iframe                              | `components/PdfPreview.tsx:35-49`                                                             |
| 图片           | `ImagePreview`                | `<img>` + 自定义缩放                                  | `components/ImagePreview.tsx:45-78`                                                           |

关键代码（`FileSelector.tsx:31` / `:99`）：

```js
const OFFICE_VIEWER_URL = 'https://view.officeapps.live.com/op/embed.aspx';
const src = `${OFFICE_VIEWER_URL}?src=${encodeURIComponent(previewUrl)}`;
```

`previewUrl` 为 S3 预签名 GET URL（24 小时有效，Java `getPreviewLinkById` 下发）。xlsx/xls **完全外发给微软公有云渲染**，前端不解析 Excel 内容。

**已有的相关资产 / 隐患**：

- `xlsx@^0.18.5` 已在 `package.json:101`，但当前**零引用** —— 唯一用法 `utils/parseXlsx.ts` 已于 2026-07-21 整体注释并标 `@deprecated`，可作为自渲染方案的起点。
- `FileSelector.tsx:35` 注释已记录："CSV → 前端 fetch + 自渲染表格（Office viewer **经常拒绝带签名 query 的 S3 URL**）"—— 微软这条路本身已有稳定性问题。
- nginx 各环境配置无任何 CSP / `frame-src` / `X-Frame-Options`，引入前端自渲染不会遇到策略层阻挡。

**前端硬约束**（影响选型）：


| 项         | 值               | 说明                                           |
| ---------- | ---------------- | ---------------------------------------------- |
| React      | `^16.8.6`        | 无 concurrent、无`createRoot`                  |
| UmiJS      | `3.2.27`（锁死） | 底层**webpack 4**                              |
| antd       | `4.9.2`（锁死）  | —                                             |
| TypeScript | 4.9.5            | 会成为 AG Grid 的版本天花板                    |
| 包管理     | npm              | `.npmrc` 的 `--openssl-legacy-provider` 不可删 |

---

## 三、协议层不可能的方案

以下方案**没有任何运行时选区 API**，不是集成问题，是能力不存在：


| 方案                                         | 依据                                                                                                                                                                                                                                                                                                                                                                            |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **现状 `view.officeapps.live.com`**          | 无 JS / postMessage API。[MS Q&A 明确答复不支持读取单元格交互](https://learn.microsoft.com/en-us/answers/questions/371403/using-the-view-officeapps-live-com-to-read-documen)。且为无文档、无 SLA 的非公开服务                                                                                                                                                                  |
| **自建 WOPI host（CSPP）**                   | 宿主→Office 仅 6 条消息：`App_PopState` / `Blur_Focus` / `CanEmbed` / `Grab_Focus` / `Host_PerfTiming` / `Host_PostmessageReady`，[官方原文 "all others are ignored"](https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/online/scenarios/postmessage)。discovery 参数表无 ActiveCell                                                               |
| **SharePoint / OneDrive 嵌入 `ActiveCell=`** | [官方措辞是 "when the web page opens"](https://support.microsoft.com/en-us/office/embed-your-excel-workbook-on-your-web-page-or-blog-from-sharepoint-or-onedrive-for-business-7af74ce6-e8a0-48ac-ba3b-a1dd627b7773) —— 只在加载时生效，运行时每次定位需重载 iframe；且要求文件托管在 M365，与 S3 存储冲突。**无证据表明 `view.officeapps.live.com/op/embed.aspx` 支持该参数** |
| **Office.js `Excel.Range.select()`**         | API 真实存在，但[只能在 Office 加载项宿主内运行](https://learn.microsoft.com/en-us/office/dev/add-ins/overview/office-add-ins)，第三方网页无法控制自己 iframe 里的 Office Online                                                                                                                                                                                                |
| **Microsoft Graph `driveItem: preview`**     | [参数只有 `page` / `zoom`](https://learn.microsoft.com/en-us/graph/api/driveitem-preview)，无单元格维度                                                                                                                                                                                                                                                                         |
| **Google Sheets 嵌入**                       | 嵌入参数只有`gid` / `range` / `widget` / `headers` / `chrome`，`range=` 是"发布哪块区域"不是跳转；Sheets API v4 的 67 种 Request 无一能设选区；Apps Script `setActiveRange` 官方明写只能容器内运行                                                                                                                                                                              |
| **Zoho Office Integrator (Sheet)**           | 宿主→编辑器 postMessage[全集](https://www.zoho.com/officeintegrator/api/v1/sheet-postmessage-api-list.html)仅 `CellContent`（按 row/col 写值，不选中不滚动）/ `ExportSpreadsheet` / `SaveSpreadsheet`                                                                                                                                                                          |
| **腾讯云 CI / 腾讯文档**                     | Excel 侧只有`Sheets.Count` / `Item(i).Name` / `Item(i).Activate()` / `Zoom`，**无 Range / Cells / Selection**                                                                                                                                                                                                                                                                   |
| **永中 Office / DCS**                        | 纯服务端 REST 转 HTML / 图片，无前端 API                                                                                                                                                                                                                                                                                                                                        |
| **Nutrient Web SDK**                         | 转 PDF 后渲染，[官方 guide](https://www.nutrient.io/guides/web/viewer/office-documents/) 无任何表格 / 单元格 API                                                                                                                                                                                                                                                                |

---

## 四、可行方案对比


| 方案                                    | 定位到某格的真实 API                                                                                                                                                                                                                                                                                                                                                                                                               | 高亮方式                                                          | xlsx 保真度                                                                                                                                                  | 许可 / 成本                                                                                                                                        | React 16                                                                                                                       | 工作量                                |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------- |
| **① SheetJS CE + `sheet_to_html`**     | `XLSX.utils.sheet_to_html(ws,{id:'sjs'})` 输出的每个 `<td>` **自带 `id="sjs-B7"`** → `getElementById('sjs-B7').scrollIntoView({block:'center'})`（[html utils](https://docs.sheetjs.com/docs/api/utilities/html)）                                                                                                                                                                                                                | 自加 CSS class，完全可控                                          | 结构✅ <br />合并✅（rowspan/colspan）<br />数字格式✅（`cell.w`）<br />列宽行高✅（需 `cellStyles`）／ **字体·边框·对齐❌ 冻结❌ 图表❌**                | Apache-2.0，**依赖已在项目中**                                                                                                                     | ✅ 无关                                                                                                                        | **1~2 天**                          |
| **② ExcelJS + 自绘 table**             | 自打`data-row` / `data-col` → `querySelector` + `scrollIntoView`（ExcelJS 只解析不渲染 UI，表格 DOM 自绘，定位用浏览器原生 API）                                                                                                                                                                                                                                                                                                                                  | 同上                                                              | **免费方案最高**：完整 `Style{font,fill,border,alignment,numFmt}`、`isMerged/master`、冻结 `WorksheetViewFrozen{xSplit,ySplit}`、`getImages()`；<br />图表❌ | MIT                                                                                                                                                | ✅ 官方 browser 构建                                                                                                           | **3~5 天**                         |
| **③ FortuneSheet**                     | `setSelection({row:[r,r],column:[c0,c1]})` + `scroll({targetRow,targetColumn})`（[API](https://ruilisi.github.io/fortune-sheet-docs/guide/api.html)，源码实证：目标行落视口顶部）                                                                                                                                                                                                                                                  | `setCellFormatByRange('bg',color,range)`；有 `allowEdit` 只读开关 | 合并 / 样式 / 公式 / 冻结 / 条件格式 / 批注 / 图片✅；<br />图表❌ <br />透视表❌                                                                            | MIT                                                                                                                                                | 🔴 peerDeps 声明`react >= 18.2`（源码只用 16.8+ 的 hook，**需实测**）                                                          | **2~4 天 + POC**                    |
| **④ Univer OSS**                       | **API 最贴需求**：`fWorksheet.scrollToCell(row,col)`、`fRange.highlight(color)` **返回 `IDisposable`**（可撤销）、`fRange.activate()`、`fWorksheet.setActiveSelection(range)`、`univerAPI.addEvent(Event.SelectionChanged, cb)`（[FWorksheet](https://reference.univer.ai/en-US/classes/FWorksheet) · [FRange](https://reference.univer.ai/en-US/classes/FRange)）                                                                | `highlight()` 不抢用户选区                                        | 核心：合并 / 样式 / 公式 / 冻结 / 条件格式✅；<br />图表属 Pro❌                                                                                             | 内核 Apache-2.0，但**xlsx 导入属 Pro**（`@univerjs-pro/exchange-client`，需自托管服务端），[Pro 页面当前"新购暂停"](https://pro.univer.ai/license) | ⚠️ README 原文 "minimal compatibility support for React 16.9+ and 17"                                                        | **4~6 天**                         |
| **⑤ AG Grid Community + SheetJS 解析** | `api.ensureIndexVisible(index,'middle')` / `api.ensureColumnVisible(key,'middle')` / `api.flashCells({rowNodes,columns})`（[Cell Styles](https://www.ag-grid.com/react-data-grid/cell-styles/)）                                                                                                                                                                                                                                   | `cellClassRules`                                                  | 取决于解析层；**免费拿到虚拟滚动 + 合并 colSpan/rowSpan + 冻结列**                                                                                           | MIT（Enterprise $999/dev）                                                                                                                         | ✅ peer 含`^16.8.0`，🔴 但 **TS 4.9.5 锁在 31.3.4**（[Compatibility](https://www.ag-grid.com/react-data-grid/compatibility/)） | **3~4 天**                          |
| **⑥ Aspose.Cells for Java → HTML**    | `HtmlSaveOptions.setCellNameAttribute("data-cell")` 让服务端 HTML 每格自带 `data-cell="A1"` → `querySelector` + `scrollIntoView`；另有 `setExportCellCoordinate(boolean)`                                                                                                                                                                                                                                                         | CSS class                                                         | 中高（保样式 / 合并；细节无官方矩阵）                                                                                                                        | Developer OEM **$3,597** 一次性（含 SaaS 再分发）；Small Business $1,199                                                                           | ✅ 自写                                                                                                                        | 中                                    |
| **⑦ SpreadJS**（商业）                 | `sheet.setActiveCell(r,c)` / `setSelection(r,c,rowCount,colCount)` / **`showCell(r,c,VerticalPosition,HorizontalPosition)`** / `setStyle`；`workbook.setActiveSheetIndex(i)`（[Worksheet API](https://developer.mescius.com/spreadjs/api/classes/GC.Spread.Sheets.Worksheet)）                                                                                                                                                     | `setStyle` / `options.selectionBackColor`                         | **极高**（图表 / 形状 / 透视需额外包）；**`.xls` 不支持且官方无计划**                                                                                        | $999/dev（永久 + 1 年维护）**＋ 商业单域名部署 $12,499/年**                                                                                        | ✅ 官方明写支持 React 16~19                                                                                                    | 低                                    |
| **⑧ Wijmo FlexSheet**（同厂低价线）    | `select(r,c,r2?,c2?)` / `selection` / **`scrollIntoView(r,c)`** / `applyCellsStyle(style,target?)` / `loadAsync(url)`（[FlexSheet API](https://developer.mescius.com/wijmo/api/classes/Wijmo_Grid_Sheet.Flexsheet.html)）                                                                                                                                                                                                          | `applyCellsStyle`                                                 | 中（导入含样式，图表 / 透视不保，需 jszip）                                                                                                                  | $799/dev + 商业单 hostname $499；**明写不含 SaaS，需单独年度 SaaS License → 需询价**                                                              | ⚠️ 官方未声明，需实测                                                                                                        | 低                                    |
| **⑨ ONLYOFFICE Developer Edition**     | `docEditor.createConnector()` → `connector.callCommand(() => Api.GetSheet(n).SetActive(); ws.GetRange("C10").Select())`（[Automation API](https://api.onlyoffice.com/docs/docs-api/usage-api/automation-api/) · [ApiRange.Select](https://api.onlyoffice.com/docs/office-api/usage-api/spreadsheet-api/ApiRange/Methods/Select/)）。❌ `executeMethod` 白名单**无任何设选区方法**（只有 `GetSelectedText` / `GetSelectionType`） | `SetFillColor()`                                                  | 最高（真 Office 引擎）                                                                                                                                       | $3,500 起（Development Server 档**官方禁止以自家品牌交付终端用户**）；生产档需询价。**CE（AGPL）无此 API**                                         | ✅ 用原生`DocsAPI.DocEditor`                                                                                                   | 高（需自建 DS）                       |
| **⑩ Collabora Online / CODE**          | `Send_UNO_Command` 转发 `.uno:GoToCell` + `ToPoint=$Sheet1.B12`（[PR #6099](https://github.com/CollaboraOnline/online/pull/6099) 已合并，22.05.13 起）                                                                                                                                                                                                                                                                             | —                                                                | 最高（LibreOffice 引擎）                                                                                                                                     | 主要 MPLv2；CODE 官方"不建议生产"                                                                                                                  | ✅                                                                                                                             | 🔴**高**（须自建 WOPI host）          |
| **⑪ Jspreadsheet Pro**                 | `updateSelectionFromCoords(x1,y1,x2,y2)` / `getSelection()` / **`setBorder(x1,y1,x2,y2,name,colorHex)`**（命名高亮框，不抢选区）/ `setStyle` / `getCellFromCoords`。⚠️ **滚动 API 文档未找到**                                                                                                                                                                                                                                   | `setBorder` / `setStyle`                                          | 中（官方 parser 带样式、多 sheet，文档自认 "known limitations"）                                                                                             | Enterprise **$2,499/年** 或永久 $7,499；**按单应用计费、与人数无关**，允许 SaaS                                                                    | ⚠️ 未声明（用 hooks → ≥16.8）                                                                                              | 中                                    |
| **⑫ DHTMLX Spreadsheet**               | `setSelectedCell()` / `setFocusedCell()` / `setStyle()` / `setActive()`。⚠️ 无独立滚动 API                                                                                                                                                                                                                                                                                                                                       | `setStyle`                                                        | 中（`load(url,"xlsx")` 走 WASM，纯客户端；保真度无官方明细）                                                                                                 | Individual$599 / Commercial $1,299 / Enterprise $2,899，**全档允许 SaaS**、含源码、永久                                                            | ⚠️ 未核实                                                                                                                    | 中                                    |
| **⑬ Syncfusion EJ2 Spreadsheet**       | `selectRange(address)` / **`goTo(address)`**（滚动定位）/ `cellFormat(style,range)` / `activeSheetIndex`（[selection](https://help.syncfusion.com/document-processing/excel/spreadsheet/react/selection)）                                                                                                                                                                                                                         | `cellFormat`                                                      | 高（服务端 XlsIO 解析，支持`.xls`）                                                                                                                          | $1,199/dev/年 × **最少 5 席 = $5,995/年起**，纯订阅无永久；**EULA：停订须从产品移除**                                                             | ✅ 官方兼容表：React 16 → ≥16.2.45                                                                                           | 🔴**高：xlsx 打开强依赖 .NET 服务端** |

---

## 五、逐方案评述

- **① SheetJS CE** — ✅ 适合做 MVP：依赖已在 `package.json`，零新增体积；`id="sjs-B7"` 恰好就是溯源需要的坐标键；同目录 `CsvPreview.tsx`（160 行）可直接抄容器与截断逻辑。❌ 只给"结构 + 格式化后文本"，字体 / 边框 / 对齐一个都没有，冻结窗格读不到，无虚拟化。
- **② ExcelJS** — ✅ 唯一能真正"像 Excel"的免费方案，样式 / 冻结 / 图片全读得到，定位靠自打 `data-*` 最可控。❌ 渲染器全自写；**`numFmt` 是隐藏大坑**（ExcelJS 只给格式字符串不给格式化文本，会计格式 / 负数红括号 / 日期本地化要自己实现，约 1~2 天，而 SheetJS 的 `cell.w` 是白送的）；上游 4.4.0 停在 2023-10，接管 fork 为 `exceljs-community`。
- **③ FortuneSheet** — ✅ 唯一「活跃维护 + 原生 React 组件 + 真实 setSelection/scroll + MIT + 只读开关」全中的成品。❌ peerDeps 冲突必须先 POC；`.xls` 不支持（需另接 SheetJS）；图表不还原。
- **④ Univer OSS** — ✅ 定位 / 高亮 API 是所有方案里最贴合需求的，`highlight()` 返回 `IDisposable` 天生适合"高亮跟着核对项走"；活跃度最好（0.25.1 / 2026-06-27，14.3k star）。❌ xlsx 导入属 Pro 且 Pro 暂停新购；React 16 仅"minimal compatibility"；对"只读预览 + 高亮"这个需求偏重。
- **⑤ AG Grid Community** — ✅ 免费拿虚拟滚动 + 合并 + `ensureIndexVisible` / `flashCells`，大表不怕。❌ `!merges` → `colSpan/rowSpan` 按列回调的映射最费神；TS 4.9.5 钉死在 31.3.4；框选区域高亮本身属 Enterprise；+354 KB gzip。
- **⑥ Aspose.Cells → HTML** — ✅ 最贴合现有栈（Java 后端已有），定位高亮 100% 自主、无 per-hostname 授权、一次性买断。❌ 大表虚拟滚动要自己写。
- **⑦ SpreadJS** — ✅ "花钱买零技术风险"，四件套（切 sheet / 选区 / 滚动 / 高亮）官方齐备且纯前端导入。❌ $12,499/年 部署授权是报价单上不显眼的一项，每个 hostname（dev/test/uat/prod）都要 key，无 key 只能 localhost 且带水印；`.xls` 需服务端先转。
- **⑧ Wijmo FlexSheet** — ✅ 同厂便宜近一个数量级，`scrollIntoView` 真实存在。❌ 保真度弱于 SpreadJS；**我们是 SaaS，部署授权必须单独询价**。
- **⑨ ONLYOFFICE DE** — ✅ 唯一"真 Excel 渲染 + 可 JS 定位 + 数据不出境"的组合。❌ [官方社区帖明确 `Select()` / `SetActive()` 不触发滚动](https://community.onlyoffice.com/t/how-to-scroll-the-screen-to-the-desired-position/731)（"we don't have ready-to-go solution"）—— 这对"定位到远处单元格"基本判死；且 Automation API 是否属基础包官方三处表述冲突。
- **⑩ Collabora** — ✅ 三条 iframe 路线里唯一有官方通道可运行时反复调用。❌ 须自建 WOPI host，比现状贵一个数量级；CODE 不建议生产；命令名与参数属社区核实（官方 SDK 站被反爬挡住）。
- **⑪ Jspreadsheet Pro** — ✅ 按应用计费（团队大反而便宜）+ `setBorder` 命名高亮框很契合"标记不抢选区"。❌ 滚动 API 无文档；保真度官方自留口子。
- **⑫ DHTMLX** — ✅ 价格最友好、全档允许 SaaS、含源码、WASM 纯前端导入。❌ 保真度与滚动能力都缺官方说明。
- **⑬ Syncfusion** — ✅ `goTo(address)` 语义上最贴需求。❌ **xlsx 打开强依赖 .NET 服务端**（官方无 Java 版，论坛明确"Java 无 open/save 支持"），我们是 Java + Python 栈，引入 .NET 容器 = 多一门运维技术栈 + 一条新合规资产。

---

## 六、已排除方案


| 方案                                                                                                                    | 排除原因                                                                                                                                                                                                                                |
| ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Luckysheet**                                                                                                          | 仓库**2025-10-30 已归档**，npm 冻结在 2021-01，Luckyexcel 2025-07-08 亦归档。（API 本身可用：`setRangeShow` + 必须另调 `scroll()`）                                                                                                     |
| **x-spreadsheet**                                                                                                       | 🔴**无任何选区 / 滚动 API**（`index.d.ts` 公开方法仅 `cell/cellStyle/cellText/loadData/getData/deleteSheet/change/on`）；master 停在 2023-08                                                                                            |
| **Handsontable**                                                                                                        | 自**7.0.0（2019-03）起放弃 MIT**，CE 版已不存在，商用 $999+/dev；且**官方无 xlsx 导入**，Excel 外观须自行重建 —— 对财报保真核对是反向选择。`react-office-viewer` 因依赖它而传染该许可                                                 |
| **DevExpress**                                                                                                          | DevExtreme 组件清单里**没有 Spreadsheet**（只有 .NET / Blazor 版），Office File API 是服务端 .NET 库                                                                                                                                    |
| **KendoReact Spreadsheet**                                                                                              | `range.select()` / `background()` 存在但**无官方滚动 API**（官方建议用 jQuery 操作 `scrollTop`）；最新 16.x 要求 React ≥18，须锁 5.14.0；2026-06-01 起不再售永久许可                                                                   |
| **RevoGrid**                                                                                                            | MIT 且`scrollToCoordinate` / `setCellsFocus` 齐全，但**合并单元格是 Pro 付费功能** —— 财务报表场景硬伤                                                                                                                                |
| **轻量预览库**（`@vue-office/excel`、`@js-preview/excel`、`react-file-viewer`、`xlsx-preview`、`react-excel-renderer`） | 定位 API**全部为「无」**；`react-file-viewer` 走 `sheet_to_csv`，样式与合并全丢；vue-office 家族渲染内核是已停更的 x-spreadsheet                                                                                                        |
| **kkFileView**                                                                                                          | 官方无定位 API（底层 Luckysheet 有，但需改源码加 postMessage 桥，且 Luckysheet 已归档）                                                                                                                                                 |
| **WPS WebOffice / 阿里云 IMM WebOffice**                                                                                | 技术上满足（`Sheets.Item(i).Activate()` + `Range('A1').Select()` + `Interior.Color` 这套 VBA 风格 API 真实存在），但**美国客户财务底稿进中资云，合规基本走不通**；阿里云 IMM 还要求文件复制到阿里云 OSS，等于在 S3 之外再留一份财务数据 |

---

## 七、推荐路线

### 第一步：SheetJS CE + `sheet_to_html` + DOM 定位（1~2 天）

```js
const wb = XLSX.read(buf, { cellStyles: true });
container.innerHTML = XLSX.utils.sheet_to_html(wb.Sheets[name], { id: 'sjs', header: '', footer: '' });
// 定位 + 高亮就是两行
document.getElementById(`sjs-${addr}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
el.classList.add(styles.traceHighlight);
```

以最低成本把硬需求做实，零新增依赖，先验证"右侧点条目 → 左侧定位高亮"这个交互本身好不好用。

**风险**：

1. 外观只有结构 + 数字格式，字体 / 边框 / 对齐全无 —— 若产品验收标准是"跟 Excel 一样"，这条直接不达标；
2. 无虚拟化，几千行以上需截断兜底；
3. **前置决策**：`xlsx` 是继续留 npm 0.18.5（Snyk `SNYK-JS-XLSX-5457926` 告警无法通过升级消除），还是把 `https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz` 写进 `package.json` / vendoring 到私服 —— 需过依赖治理。

### 第二步（条件触发）：ExcelJS 自绘（3~5 天）

只有当"外观不像 Excel"被真实核对场景确认为痛点时才升级。**两者定位模型完全同构**（都是 DOM 属性 + `scrollIntoView`），换渲染层不必重写定位代码。

### 备选分支


| 若约束是                         | 选                                                   |
| -------------------------------- | ---------------------------------------------------- |
| 大表必须流畅                     | AG Grid Community 31.3.4 + SheetJS / ExcelJS 解析    |
| 想少写渲染代码、直接用成品编辑器 | FortuneSheet（先花半天做 React 16 POC）或 Univer OSS |
| Java 后端愿意承担渲染            | Aspose.Cells`setCellNameAttribute("data-cell")`      |
| 预算充足、要零技术风险           | SpreadJS（注意 $12,499/年 部署授权）                 |

**判断依据**：先上重方案，多花一倍工期买到的是外观，而外观未必是核对效率的瓶颈。

---

## 八、必做 POC


| # | 验证项                                      | 为什么必须验                                                                                                                                                                                                                                             | 量级      |
| - | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| 1 | **只读模式下能否选中并改底色**              | ONLYOFFICE / Collabora / Univer 三家官方文档都没写，而这是核对场景的前提。若选 ONLYOFFICE，只需验一件事：`mode:"view"` / `permissions.edit:false` 下 `connector.callCommand(() => Api.GetSheet(x).SetActive())` 是否生效 —— 这一个实验决定方案成立与否 | 1 天      |
| 2 | **FortuneSheet 在 React 16 下的实际可用性** | peerDeps 声明`react >= 18.2`，仅核对了 `Workbook/index.tsx` 的 import，Toolbar / ContextMenu / ModalProvider 等子组件未逐个核对                                                                                                                          | 0.5 天    |
| 3 | **真实财报保真度比对**                      | Kendo / Jspreadsheet / DHTMLX / FlexSheet 的官方保真度说明全是笼统一句话，无明细矩阵。须拿真实客户 xlsx（含合并单元格、条件格式、多 sheet、公式）跑一遍肉眼比对                                                                                          | 1 天      |
| 4 | **大文件性能**                              | 参考基线：6 MB / ~15 万有值单元格的 xlsx，浏览器端"Parse + mount 3–8 秒，UI blocked"，峰值堆 80–120 MB。**该量级适用于所有浏览器端解析路线** —— 解析必须放 Web Worker 或动态 `import()` + loading 态，不能在主线程直接跑                             | 含在 1 内 |

---

## 九、交互设计建议

**核对场景应使用「高亮」而非「选区」。** 用户点击左侧表格后选区会被抢走，溯源标记随即丢失。

- Univer 的 `fRange.highlight(color)` 返回 `IDisposable`、Jspreadsheet 的 `setBorder(x1,y1,x2,y2,name,color)` 都是专为"命名标记不抢选区"设计的；
- 走 SheetJS / ExcelJS 自渲染时，高亮就是一个 CSS class，天然满足，且可同时存在"当前项高亮"与"已核对项弱标记"两层。

配套注意：需求分析文档 §Source Tracing（[requirement-analysis.md](./requirement-analysis.md)）已定过一条规则 —— **左侧面板的视觉高亮仅在当前显示与指标来源相同的 sheet 时才显示**，跳 sheet 时应先切 sheet 再高亮，避免误导。

---

## 十、未核实清单

以下项**不可当结论使用**，决策前需自行确认：

1. ONLYOFFICE / Collabora / Univer 在**只读模式**下能否执行选中与改底色（三家官方文档均未写）。
2. Collabora 官方 postMessage 完整清单 —— `sdk.collaboraonline.com` 全站被反爬挡住；`.uno:GoToCell` / `ToPoint` 参数名属社区核实，TDF 官方 wiki 未直接读到。
3. FortuneSheet 的 xlsx 插件 `@corbe30/fortune-excel` 是否存在（两路调研结论冲突），安装前 `npm view` 确认。
4. `@zwight/luckyexcel`（Univer 的免费 xlsx 转换路径）生成的快照与 Univer 0.25.x 的兼容性 —— 其依赖声明为 `@univerjs/core ^0.6.0`，跨了 19 个 minor。
5. 价格类：SpreadJS + GcExcel 捆绑价与 OEM 条款、Wijmo SaaS License 价格、Univer Pro 定价、ONLYOFFICE 生产档价格与 Automation API 是否加价、WPS WebOffice 全部价格（官方站为 SPA）、Zoho Office Integrator 具体金额。
6. ONLYOFFICE CE 的 20 连接上限口径不一致（9.4 博客称取消，Compare editions 仍写 "up to 20 recommended"）。
7. `@revolist/react-datagrid` 对 React 16 的支持（registry 无 peerDependencies 字段）；`jspreadsheet-ce` v5 实际条款（npm license 字段为空）。
8. Excel Online 的 `#'Sheet1'!A1` fragment / `nav=` 参数在嵌入端点是否生效 —— 官方嵌入文档未提及。
