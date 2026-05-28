# 财务页 Financial — 样式 Bug 清单

> 路由（LG-UI）：`/dashboard/block/financial`
> 全局主题色对照与严重度图例见 [README.md](./README.md)

## 涉及文件

| 侧 | 文件 |
|----|------|
| **当前系统** | `CIOaas-web/src/pages/companyFinance/FinancialEntry/components/ImportStatementsModal.tsx`<br>`…/components/ImportStatementsModal.less`<br>触发按钮 `…/components/TableToolbar.tsx`（`.importStatementsBtn`，样式在 `…/FinancialEntry/index.less:274`） |
| **LG-UI 目标** | `Remix of LG-UI_UX/src/components/financial/OcrUploadDialog.tsx`<br>`…/components/ui/dialog.tsx`、`…/components/ui/button.tsx`、`…/src/index.css`（主题变量） |

---

## 0. 触发按钮：Import Statements（弹窗入口）

| 属性 | LG-UI 目标 | 当前系统 | 差异 |
|------|-----------|----------|------|
| 高度 | **36px** (`h-9`) | **40px** | 🟡 偏高 4px |
| 水平内边距 | **12px** (`px-3`) | **16px** | 🔵 偏大 4px |
| 字号 | **12px** (`text-xs`) | **14px** | 🟡 偏大 2px |
| 圆角 | 4px | 4px | ✅ |
| 边框 | 1px `#ECEEF1` | 1px `#D6D8DC` | 🔵 当前偏深 |
| 文字色 | `#15191C`（近黑） | `#0D2B56`（navy 品牌色） | 🔵 当前用品牌色，可保留 |
| hover 边框 | `#E1990F` | `#E1990F` | ✅ |
| **hover 文字** | 保持深色不变 | **变 `#E1990F` 金色** | 🟡 当前 hover 文字变金，LG 不变 |

**修复建议**（`index.less:274 .importStatementsBtn`）：`height: 36px; padding: 0 12px; font-size: 12px;`；hover 去掉 `color: #E1990F`，只保留 `border-color`。文字色 `#0D2B56` 属品牌色，可保留。

---

## 弹窗本体 Bug 清单

### A. 弹窗容器

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| A1 | 🟡 | 圆角 | `8px`（`.ant-modal-content { border-radius: 8px }`） | `0px`（`dialog.tsx` 基类含 `rounded-none`，**方形角**） | ⚠️ LG 方形角较特殊，建议**与设计确认**是否真要方角；若否则保留 8px |
| A2 | 🔵 | 宽度 | `560px` | `540px`（`sm:max-w-[540px]`） | 改 `width={540}` |
| A3 | 🔵 | 内边距 | `modalBody: 28px 28px 24px` | `24px`（`px-6` / `p-6`） | 统一为 24px（连带 footer 负 margin 改 -24px） |

### B. 标题

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| B1 | 🔴 | 文案大小写 | `Upload financial documents`（句首式） | `Upload Financial Documents`（标题式 Title Case） | 改文案为 Title Case |
| B2 | 🟡 | 字号 | `18px` | `24px`（`text-[24px]`） | `.title { font-size: 24px }` |
| B3 | ✅ | 颜色 | `#0D2B56` | `#0D2B56` | 一致，无需改 |

### C. 拖拽上传区（Drop zone）

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| C1 | 🔴 | hover / 拖拽金色 | `#F59F0A`（`&:hover` 边框、`.dropZoneDragOver` 边框） | `#E1990F`（`hover:border-primary`） | 改 `#F59F0A` → `#E1990F` |
| C2 | 🟡 | 默认边框色 | `2px dashed #D1D5DB` | `2px dashed #ECEEF1` | 调浅为 `#ECEEF1`（或统一边框 token） |
| C3 | 🔵 | 内边距 | `28px 20px` | `32px`（`p-8`） | 改 `padding: 32px` |
| C4 | 🔵 | 拖拽态背景 | `#FFFBF0` | `primary/5`≈`rgba(225,153,15,.05)` | 改 `rgba(225,153,15,.05)`（与品牌金一致） |
| C5 | 🔵 | 图标/文字灰 | 图标 `#9CA3AF`、标题 `#111827`、提示 `#6B7280` | 图标 `#848688`、标题 `#15191C`、提示 `#848688` | 近似可保留；若统一则按 LG 取值 |

### D. 文件列表（表头 + 行）

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| D1 | 🟡 | 行边框宽度 | `2px`（`.fileRow`） | `1px`（`border`） | 改 `1px` |
| D2 | 🟡 | 行圆角 | `8px` | `6px`（`rounded-md`） | 改 `6px` |
| D3 | 🔵 | 行边框色 | `#E5E7EB` | `#ECEEF1` | 统一边框 token |
| D4 | 🔵 | 行背景 | `#fff` | `muted/30`≈近白 `#FBFBFB` | 可保留白底，或加极浅底 |
| D5 | 🔵 | 垂直对齐 | `center` | `flex items-start`（顶对齐） | 长文件名换行时 LG 顶对齐；可按 LG 改 `align-items: flex-start` |
| D6 | 🔵 | 文件名字号 | `13px` | `12px`（`text-xs`） | 改 `12px` |
| D7 | 🔵 | 表头字号/色 | `11px` `#9CA3AF` | `12px` `#848688` | 近似可保留 |

### E. 文件类型图标

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| E1 | 🔴 | 图标风格 | **24px 纯色文字徽章**：Excel 绿底 `#16A34A`「X」、PDF 红底 `#DC2626`「PDF」、其它灰底「FILE」 | **16px 写实彩色文件类型 SVG**（蓝色图片图标 / 红色 PDF / 绿色 Excel，带文件折角细节） | 风格差异大。建议改用与 LG 一致的 16px 彩色 SVG 图标（LG 图标定义在 `OcrUploadDialog.tsx` 的 `ImageFileIcon`/`PdfFileIcon`/`ExcelFileIcon`） |
| E2 | 🟡 | 图标类型覆盖 | 仅区分 xlsx/xls、pdf，其余（图片/CSV）统一回退「FILE」 | 区分 图片 / PDF / Excel(含 csv) | 补齐图片、CSV 的专属图标 |

### F. 上传进度展示

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| F1 | 🔴 | 进度展示方式 | **Ant 进度条 + 百分比**（`Progress` + `{n}%`） | **旋转 spinner（`Loader2`）+ "Uploading..." 文字**，无进度条、无百分比 | ⚠️ 属 UX 决策，建议**确认**统一走哪种。若以 LG 为准则改为 spinner + 文案 |
| F2 | 🔴 | 进度条金色（若保留进度条） | `strokeColor="#F59F0A"` | 品牌金 `#E1990F` | 改 `#F59F0A` → `#E1990F`（`.tsx` 的 `strokeColor` 与 `.less .progressBar .ant-progress-bg`） |
| F3 | 🔵 | 进度条槽色 | `#E5E7EB` | grey-300 `#ECEEF1` | 统一边框/槽 token |

### G. 底部按钮（Footer）

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| G1 | 🟡 | 分隔线 | `2px solid #E5E7EB` | `1px #ECEEF1`（`border-t border-border`） | 改 `1px solid #ECEEF1` |
| G2 | 🔴 | **Next 按钮底色** | `#F59F0A`（`.nextBtn`） | 品牌金 `#E1990F`（`bg-primary`） | 改 `#F59F0A` → `#E1990F` |
| G3 | 🟡 | Next disabled 态 | 实色 `#fad7b0` | 品牌金 50% 透明（`disabled:opacity-50`） | 改为 `#E1990F` + `opacity: .5`，或浅品牌金 |
| G4 | 🔵 | Next hover | 无 | `#C88C1A`（`hover:bg-[#C88C1A]`） | 加 hover 深金 `#C88C1A` |
| G5 | 🔵 | 按钮高度 | ≈40px（`padding:10px 24px`+14px 字） | 36px（`h-9`） | 可统一为 36px |
| G6 | 🔵 | Cancel 文字色 | `#0D2B56`（navy 品牌色） | `#15191C`（近黑 foreground） | **可保留 navy**（属当前品牌色） |
| G7 | 🔵 | Cancel 边框色 | `#D6D8DC` | `#ECEEF1` | 统一边框 token |
| G8 | 🔴 | Remove / Clear All 金色 | `#F59F0A`（`.removeBtn` / `.clearAllBtn`，hover `#d48a09`） | `#E1990F`（`text-primary`） | 改 `#F59F0A` → `#E1990F` |

### H. 关闭按钮

| ID | 严重度 | 属性 | 当前系统 | LG-UI 目标 | 修复建议 |
|----|--------|------|----------|-----------|----------|
| H1 | 🔵 | 颜色 / 尺寸 / 定位 | Ant 默认 close，`#6B7280`，32×32，`top/right:16px` | 自定义 X，`#4E5153`，16px，`top/right:24px`，`strokeWidth 2.5` | 近似可保留；若统一则调色 `#4E5153`、定位 24px |

---

## 修复优先级建议

**第一优先（🔴，统一品牌 + 文案）——一次性改动量小、收益最大：**
- 全弹窗金色 `#F59F0A` → 品牌金 `#E1990F`（涉及 C1、F2、G2、G8，外加 disabled/hover 派生色）
- 标题文案改 Title Case（B1）
- 文件图标改 16px 彩色 SVG（E1）
- 上传进度展示方式与 LG 对齐 —— **需先确认** spinner 还是进度条（F1）

**第二优先（🟡，尺寸/边框）：**
- 边框宽度 2px → 1px、圆角对齐、分隔线 1px（D1/D2/G1）
- 标题字号 18→24px（B2）、触发按钮尺寸（第 0 节）

**第三优先（🔵，近似色/微调，可批量统一 token）：**
- 边框灰统一为 `#ECEEF1`、灰文字/近黑微调、内边距与宽度微调

**保留项（不算 bug）：**
- 标题与 Cancel 文字的 navy `#0D2B56` —— 当前系统既定品牌文字色
- 弹窗 8px 圆角（A1）—— LG 的方角较特殊，建议确认后再定
