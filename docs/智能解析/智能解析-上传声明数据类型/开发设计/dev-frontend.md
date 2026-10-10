# 手动上传时声明 Actuals / Proforma · 前端开发设计

> 关联文档：
> - 上游（第四阶段 · 功能设计）：[design-doc](../设计/design-doc.md) —— D1 ~ D10 全部结论在那里，本文不重复论证；前端部分对应 §4、§7、§8
> - 需求：[requirement-doc](../需求/requirement-doc.md)（R1 / R2 / R7 / R8 / R12、§5 交互、§8 待确认 Q1 / Q2 与本文直接相关）
> - 参考代码：[code-examples](./code-examples.md) 的「前端」一节（类型、组件片段、service 函数、单测骨架）
> - Java 开发设计：[dev-java](./dev-java.md)（commitUpload 新请求体、校验返回码，§4 / §5）

本文只写 **前端怎么改**：文件清单、插入点、状态形状、启用逻辑、样式、单测和风险。按 `docs/CLAUDE.md`，
完整函数与组件片段放 [code-examples](./code-examples.md)，本文只给签名和插入点。

下文路径简写：`web/` = `CIOaas-web/src/`，`ai页/` = `web/pages/financial/aiFinancialExtraction/`。
行号基于 `CIOaas-web` 分支 `sprint121`、提交 `eea52f3c`（2026-10-09），工作区干净。

---

## 1. 代码基线核对

| 设计里的说法 | 代码现状 | 结论 |
|---|---|---|
| 上传弹窗被 V2 与 V1 共用 | `web/pages/financial/FinancialEntryV2/Index.tsx:11` 跨目录 import `../FinancialEntry/components/ImportStatementsModal`；V1 `FinancialEntry/Index.tsx:9`。两处挂载点 `onNext` 完全相同（V1 `:3393`、V2 `:3449`） | ✅ 只改一个组件，两版同时生效 |
| 点 Next 调 commitUpload | `ImportStatementsModal.tsx:294-318`，`:304` 调 `commitUpload(companyId, fileIds)` | ✅ |
| 首次上传的 getUploadUrl 不带 taskId | `:141-145` 传 `taskIdRef.current`（初始 `''`）。Java 延迟分支返回的 `taskId` 是 **null**（`AiFinancialExtractionServiceImpl.java:193`），第二次 addFiles 传 null，Java `isBlank` 仍走延迟分支 | ✅ 这条路径不传 `dataType`（类型在 Next 时才定） |
| Clear All 功能不变 | `:275-280` + `:411-417`：**只在有文件上传中时显示**，只清掉上传中的文件，已传完的保留 | ⚠️ 与需求 §5.1 画的"列表底部常驻 Clear All"不同，见 §9 |
| 映射页逐行改派 Actual / Forecast | `DataMappingPanel.tsx:736-747` 每个指标下两项；`handleAssign :1887-1903` 写 `editLgCategory + editSourceDataType` | ✅ |
| 映射页 Upload New Document | `FileSelector.tsx:213-217` 菜单 → `:215` 直接 `uploadInputRef.current?.click()`；`:219-225` onChange → `onUploadFiles(files)`；页面接线 `AiFinancialExtractionPage.tsx:760-767` → `useOCRData.uploadAdditionalFiles :392-516`，`:412-416` 调 getUploadUrl | ✅ |
| Replace Document 不问类型 | `useOCRData.replaceFile` `:550-554` 调 getUploadUrl（单文件）→ `file/replace`；Java 无条件以旧文件类型覆盖（dev-java §4.4） | ✅ 前端 0 改动 |
| 文案统一 Proforma | 标签页 `:2128 / :2134` 已是 "Actuals" / "Proforma"；当月横幅 `:2069` 已是 "Proforma"。整个 ai页 与上传弹窗里**唯一**面向用户的 "Forecast" 就是指派下拉那一项（`:745`） | ✅ 去掉下拉选项即完成 R12，无需另改文案 |
| 传输实体放 `request.ts` | `web/services/api/ai/` 只有 `aiService.ts`，全部类型内联；service 层是薄透传 re-export，带 `TODO(service-dto)`（`web/services/service/ai/aiService.ts:7`） | ⚠️ 落点决策见 §2.1 |
| i18n | `web/pages/` 下无 `useIntl` 消费方，financial 域 0 处；ERL 已有先例"英文硬编码集中到 constants、不单独接 i18n"（`pages/exitReadiness/README.md:247-249`） | ⚠️ 处理口径见 §6 |

---

## 2. 传输层：`web/services/api/ai/`

### 2.1 类型落点（决策）

`coding.md` §2 规定 Request 放 `request.ts`、对外类型放 `dto.ts`；本域现状是全部内联、历史债挂在
`TODO(service-dto)`。取**最小合规**：

| 文件 | 动作 | 内容 |
|---|---|---|
| `web/services/api/ai/dto.ts` | **新增** | `export type FinancialDataType = 'ACTUALS' \| 'PROFORMA'`。页面两处（上传弹窗、映射页）都要用它标注状态，按 architecture §4.1 页面只能拿 `dto.ts`，不能拿 `request.ts` |
| `web/services/api/ai/request.ts` | **新增** | 只放本次改动的两个请求体：`GetUploadUrlRequest` / `GetUploadUrlFileItem`（`dataType?`）、`CommitUploadRequest` / `CommitUploadFileItem`（`dataType` 必填） |
| `web/services/api/ai/aiService.ts` | 改 | 两个函数改用上面的 Request 类型（§2.2）；其余内联类型**不搬**（属 `TODO(service-dto)` 存量，不在本期） |
| `web/services/api/ai/README.md` | **新增**（审核 A-11） | R8 域文档最小版（architecture §3.1 R8 强制；`services/api/` 下 25 个域已有 20 个有 README，`ai/` 是缺的 5 个之一）。三节：① 域职责——智能解析上传 / 映射 / 冲突提交的 HTTP 调用，对应 Java `/api/web/ai/financialExtraction/*`、`/api/web/financial-data-conflict/*` 与 Python 拉取接口 `/api/ai/financial-extract/*`；② 文件介绍——`aiService.ts`（全部 API 函数 + 存量内联类型）、`request.ts`（本期两个请求体）、`dto.ts`（`FinancialDataType`）；③ 对外契约——跨域只可 import `dto.ts`，函数经 `services/service/ai/aiService.ts` 透传，`request.ts` 仅本层用；页面仍从 `aiService.ts` 引内联类型属 `TODO(service-dto)` 存量，照实写明 |

- 不复用 `ai页/types.ts:123` 的 `TabType`：值相同但语义是"标签页"，而且 services 不能反向 import pages
  （2026-07-22 刚解除过一次倒挂，见 `aiService.ts:249-251` 注释）。
- 不放 `src/utils/enum.ts`：只有 financial 一个一级域在用，不是跨域共享内核。

### 2.2 两个函数的签名

| 函数 | 改前 | 改后 |
|---|---|---|
| `getUploadUrl`（`aiService.ts:27-36`） | `(params: {companyId; taskId; fileList: {fileName; length}[]})` | `(params: GetUploadUrlRequest)`，`fileList[]` 每项多一个可选 `dataType`；body 仍原样 `data: params` |
| `commitUpload`（`aiService.ts:61-69`） | `(companyId: string, fileIds: string[])`，body `{companyId, fileIds}` | `(params: CommitUploadRequest)`，body `{companyId, files: [{fileId, dataType}]}` |

`commitUpload` 改成对象入参，与同文件 `getUploadUrl` 一致，也与 Java 新请求类 `AiFinancialCommitUploadRequest`
一一对应。响应类型 `CommitUploadResponse` 不变。

### 2.3 Service 层

`web/services/service/ai/aiService.ts:12-26` 的 re-export **不变**（函数名不变）。只改文件头注释 `:3-4`：
类型清单里补上 `FinancialDataType`（来自 `services/api/ai/dto`）。

---

## 3. 上传弹窗：`ImportStatementsModal`

文件：`web/pages/financial/FinancialEntry/components/ImportStatementsModal.tsx` + `.less`。
组件已在业务边界内（调 service 的上传弹窗，历史形态），本期不拆 hook，沿用组件内 `useState`。

### 3.1 状态形状

`UploadFile`（`:16-22`）加一个字段：

```
tableType?: FinancialDataType   // 未选 = undefined（D7：无默认值）
```

- 新文件占位（`:128-137`）**不写**这个字段 → 天然为空。
- 上传进度 / fileId 回填 / done 置位都是 `{...uf, xxx}` 展开（`:153-159`、`:180-182`、`:189-191`、`:220-222`），
  已选的类型不会被冲掉。
- 字段叫 `tableType` 对齐 UI 列名 TABLE TYPE；只在 `handleNext` 组装请求时映射为 `dataType`。

新增两个回调（都用函数式 `setUploadFiles`，`useCallback([setUploadFiles])`）：

| 回调 | 行为 |
|---|---|
| `handleSetFileType(id, type)` | 只改 `uf.id === id` 的那一行 |
| `handleSetAllTypes(type)` | 当前列表**所有**文件（含上传中）设为该类型 |

### 3.2 插入点

| 位置 | 改动 |
|---|---|
| `:337` 标题 `<h3>` 之后、拖放区之前 | 固定说明横幅：antd `Alert type="info" showIcon`，文案常量 `ACTUALS_CURRENT_MONTH_NOTE`，不可关闭 |
| `:373-378` 表头 | `colFileSize` 与 `colAction` 之间加 `<span className={styles.colTableType}>TABLE TYPE</span>` |
| `:380-409` 每行 | 文件大小 / 进度块（`:385-399`）之后、Remove（`:401-407`）之前加 antd `Select size="small"`：`value={uf.tableType}`、`options={UPLOAD_DATA_TYPE_OPTIONS}`、`placeholder={UPLOAD_DATA_TYPE_PLACEHOLDER}`、`disabled={isSubmitting}`。**上传中也可选**（类型是本地状态，与上传无关） |
| `:411-417` 列表底部 | 换成常驻的 `.listFooterRow`：左边批量设置（§3.4），右边保留原 Clear All 按钮，**显示条件仍是 `isAnyUploading`、点击仍调 `handleClearAll`** |
| `:328` Modal 宽度 | `560` → `640`（§3.6，以 Figma 为准） |

`import` 增量：antd `Alert / Select / Dropdown / Menu`、`DownOutlined`；`FinancialDataType`（`@/services/api/ai/dto`）；
三个常量（`@/pages/financial/aiFinancialExtraction/constants`，本组件已从这里拿 `UPLOAD_ACCEPTED_EXTENSIONS`，沿用先例）。
顺手删掉 `:2` 早已无用的 `CloseOutlined`（关闭图标用的是 `<img>`，tsc 现报 TS6133）（审核 C-25）。

### 3.3 Next 启用与提交

`canNext`（`:320-321`）由三条变四条：

```
uploadFiles.length > 0 && !isAnyUploading && !isSubmitting && uploadFiles.every((uf) => !!uf.tableType)
```

`handleNext`（`:294-318`）改两处：

1. 取 `doneFiles` 之后加一道兜底：任一 done 文件没有 `tableType` 就 `return`（按钮态已经挡住，这里防按钮态与 ref
   不同步的瞬间）。用类型守卫收窄成"带类型的文件"，不写 `as`。
2. `:299` 的 `fileIds` 换成 `files = [{fileId, dataType: uf.tableType}]`（仍过滤空 fileId，与原 `.filter(Boolean)` 同义），
   `:304` 改调 `commitUpload({ companyId, files })`。

失败分支（`:313-317`：每个 done 文件推一条 GENERIC 吐司、复位 `isSubmitting`）不变。Java 对缺类型 / 非法类型回
**HTTP 422**（dev-java §5.2），`utils/request.ts:77-79` 会额外亮全局错误横幅——前端已拦截，正常路径到不了这里。

### 3.4 批量设置语义

- 形态：antd `Dropdown`（`trigger={['click']}`）+ `Menu`，触发器是文字按钮 "Set table type for all files to ▾"
  （样式同 Clear All 的橙色文字按钮）。**不用受控 Select**：批量设置是一次性动作，没有"当前值"；用 Select 的话，
  批量设成 Actuals 后再把某一行改成 Proforma，批量框仍显示 Actuals，会误导。
- 作用范围：点击时列表里的**全部**文件，包括还在上传的。
- 之后新加入的文件**保持为空**（新占位不带 `tableType`），Next 随之变回不可用——这正是 R1"每个文件都必须选"的要求，
  不做"记住上次批量值自动套用"。
- 设完仍可逐行改（R2）；一批里混合 Actuals / Proforma 合法（D1）。
- 列表非空时常驻显示（含只有一个文件时），`isSubmitting` 时 `disabled`。

### 3.5 不变的行为

Remove（`:256-273`）、Cancel（`:282-292`，删暂存文件）、关闭重置（`:89-97`，`setUploadFiles([])` 连带清空类型）、
文件校验、并行直传、Clear All 的显示条件与语义，全部不动。getUploadUrl（`:141-145`）**不传** `dataType`。

### 3.6 样式（`ImportStatementsModal.less`）

桌面宽度推算（行内可用宽 = 弹窗宽 − 左右 padding 56 − 行 padding 24 − 边框 2；文件名列 = 行内可用宽 − 图标 14
（`.fileIconWrap` / `.fileIconImg`，less `:161-170`）− 各定宽列 − 列间 gap 8 × (列数 − 1)；Remove 列 60）（审核 C-22 重算，结论不变）：

| 方案 | 文件名列剩余宽度 |
|---|---|
| 现状 560，无类型列 | 478 − 14 − 180 − 60 − 24 ≈ 200px |
| 560 + 类型列 128 | 478 − 14 − 180 − 128 − 60 − 32 ≈ 64px（不可用） |
| **640，FILE SIZE 列 180 → 120，类型列 128** | 558 − 14 − 120 − 128 − 60 − 32 ≈ 204px（与现状持平） |

| 选择器 | 改动 |
|---|---|
| `.colFileSize`（`:138-145`）、`.fileSize`（`:183-188`）、`.progressWrap`（`:190-195`） | `flex: 0 0 180px` → `120px`（进度条剩 ≈80px，仍可读） |
| 新增 `.colTableType` | 表头字样式同 `.colFileSize`，`flex: 0 0 128px` |
| 新增 `.typeSelect` | `flex: 0 0 128px; width: 128px` |
| 新增 `.notice` | 字体对齐弹窗（`Futura-PT-Medium` 13px） |
| `.clearAllRow`（`:218-222`） | 删除，换成 `.listFooterRow`（`display:flex; justify-content:space-between; align-items:center; padding-top:8px`） |
| 新增 `.bulkTypeBtn` | 同 `.clearAllBtn`（`:224-232`）+ `inline-flex` 放箭头 |

**手机（`@media (max-width: 575px)`，`:297-340`）**：375 宽的手机上行内只剩 ≈290px，现状文件名列 ≈109px，
再塞一个类型列文件名就没了。做法：`.fileRow` 加 `flex-wrap: wrap`，`.typeSelect` 设 `order: 1; flex: 1 1 100%; width: auto`
——类型下拉换到第二行占满整行；表头 `.colTableType` 在手机上 `display: none`；`.listFooterRow` 加 `flex-wrap: wrap`。
原有 `.colFileSize/.fileSize/.progressWrap` 的 88px 规则保留。手机样式同样待 Figma 确认。

---

## 4. 映射页（`/aIFinancialExtraction`）

### 4.1 去掉逐行 Actual / Forecast

| 位置 | 改动 |
|---|---|
| `DataMappingPanel.tsx:697-701` `MetricSelectPanelProps.onSelect` | `(lgCategory: string, type: 'Actual' \| 'Forecast')` → `(lgCategory: string)` |
| `:736-747` 每个指标的三段结构（名称 + Actual + Forecast） | 合成一个可点的 `<button type="button" className={styles.mspMetricItem} onClick={() => onSelect(metric)}>`（§14 可访问性：用语义按钮代替 div） |
| `:819`、`:1002`、`:1259` 三处 `onAssign` 类型 | 去掉第三个参数 |
| `:834-837` `AssignBtn` 内 `onSelect` | `(cat) => { onAssign(rowId, cat); setOpenId(null); }` |
| `:1887-1903` `handleAssign` | 签名去掉 `type`；`onRowEdit` 的 patch 只剩 `{ editLgCategory: isUnmap ? 'UNMAPPED' : lgCategory }`，**不再写 `editSourceDataType`** |
| `ai页/types.ts:99-106` `EditFields` | 删掉 `editSourceDataType`：这是"写入补丁"类型，删掉后任何人再想写类型都过不了 tsc，把 R7 变成编译期约束。`RawCell.editSourceDataType`（读侧）保留 |
| `DataMappingPanel.less:973-1015` | `.mspMetricItem` 并入原 `.mspMetricName` 的字体 + hover 背景 + 按钮样式重置；删除 `.mspMetricName`、`.mspOption`、`.mspDot`、`.mspDotActual`、`.mspDotForecast`、`.mspOptionText`（全仓只此一处使用，已 grep 确认） |
| `ai页/utils/rowClassify.ts:65` 注释 | "handleAssign 会写入 editLgCategory + editSourceDataType" → 只写 `editLgCategory`，类型跟随文件声明 |

"Other > Unmapped Accounts"（`:78-84`）这一项同样变成单击：降级只改指标、不动类型，行留在原标签页的 Unmapped 区。

### 4.2 为什么不会破坏下游

下游全部读 **有效类型** `editSourceDataType || sourceDataType`（`rowClassify.ts:27-28` 的 `effectiveDataType`，以及
`useOCRData.ts:55-57` 的同义内联），从不要求 `editSourceDataType` 有值：

| 下游 | 现在拿到什么 | 结论 |
|---|---|---|
| 行构建 / 标签页过滤（`DataMappingPanel.tsx:1585-1592`） | 新任务 `editSourceDataType` 恒空 → 回落到 `sourceDataType` = 文件声明类型 | 行落在声明类型的标签页 |
| `deriveMappingResult.hasActuals`（`useOCRData.ts:55-57`）→ `goToVerifyStep`（`AiFinancialExtractionPage.tsx:413-415`） | 有 Actuals 文件就 true，只送 ACTUALS 去 verify | 不变。唯一差别：纯 Proforma 任务的用户不能再把行改成 Actual 去触发 verify——这是 R7 的本意 |
| `dataTypesUpdated`（`useOCRData.ts:76-83`）、`computeSubmitSummary`、`buildMappedData`、面板 `mappedDataAll`（`:1735` 只收 ACTUALS / PROFORMA） | 有效类型都是合法值 | 不变 |
| `collectEditedData`（`AiFinancialExtractionPage.tsx:46-63`）→ `/complete` 的 `editedData` | 只改了指标的 cell，`editSourceDataType` 送 `''`；Java 用 `defaultString` 落库（`AiFinancialExtractionConflictServiceImpl.java:562`），与"只改日期 / 数值"的既有情形相同 | 不变 |
| `isCellEditedByUser`（`rowClassify.ts:114-115`） | 新任务该分支永不命中；历史任务里用户以前改过的类型仍被识别并提交 | 保留，不删 |
| 跨表合并分桶键含 dataType（`DataMappingPanel.tsx:338`，上方 `:335-337` 是说明注释）（审核 C-25） | 一批里可以混合两种文件且常有同名科目 | **必须保留**，否则 Actuals 与 Proforma 同名行会被并到一起 |
| 类型为 `''` 的行 | 两个标签页都过滤掉（`r.dataType === activeTab`），改前就看不到 | 不会因去掉选项而新增"看不见的行"；新任务 Python 恒写声明类型 |

### 4.3 Upload New Document：先选类型再选文件（临时交互，待 Q2）

需求 R8 要求上传新文件必须选类型；Q2 的样式待设计。先落一个**最小临时方案**，换样式时只动 `FileHeaderBar` 内部：

```
点 kebab → Upload New Document
  → 打开小弹窗（antd Modal）：一句说明 + Radio.Group [Actuals | Proforma]（无默认，D7）+ 与上传弹窗同一条 Actuals 当月说明
  → OK（文案 "Select Files"，未选类型时 disabled）
  → 关弹窗，并在**同一个点击回调里同步**调 uploadInputRef.current.click() 打开系统文件框
  → onChange：onUploadFiles(files, uploadType)
```

| 位置 | 改动 |
|---|---|
| `FileSelector.tsx:162` `FileHeaderBar` 内 | 新增两个 `useState`：`typePickerOpen`、`uploadType: FinancialDataType \| undefined`。纯 UI 交互状态，组件不调 API，符合 architecture §3 |
| `:215` 菜单 `upload` 分支 | 不再直接点 input，改为 `setUploadType(undefined); setTypePickerOpen(true)`——每次打开都清空，保证无默认 |
| `:219-225` `handleUploadInputChange` | 有文件且 `uploadType` 有值时调 `onUploadFiles(Array.from(list), uploadType)` |
| `FileHeaderBar` JSX 尾部（隐藏 input 旁） | 渲染类型选择弹窗（`!readonly` 时） |
| `:27`、`:156` 两处 `onUploadFiles` 类型 | `(files: File[]) => void` → `(files: File[], dataType: FinancialDataType) => void`；`:380` 透传不变 |
| `FileSelector.less` | 新增 `.typePickerText`、`.typePickerRadios`、`.typePickerNote` 三个类（规范禁内联样式） |
| `AiFinancialExtractionPage.tsx:760-767` | 回调改为 `(rawFiles, dataType) => uploadAdditionalFiles(rawFiles, dataType).catch(...)` |
| `useOCRData.ts:392-393` | 签名 `(rawFiles: File[], dataType: FinancialDataType)`；`:415` `fileList` 每项带 `dataType`。依赖数组不变 |

**用户手势约束**：浏览器只允许在用户点击的同步调用栈里程序化打开文件框。antd `Modal` 的 `onOk` 由 OK 按钮的
`onClick` 同步调用，满足条件；**不能**把 `click()` 放进 `setTimeout`、`Promise.then` 或 `afterClose`。
用户在系统文件框里点了取消：onChange 不触发，什么也不发生，下次打开类型重新为空。

为什么是"一次上传一种类型"而不是每个文件各选：最小实现；同一次选中的文件共用一个类型，混合类型分两次上传
（R6 本来就要求一个文件一种类型）。接口层面 `fileList[]` 本来就是逐文件带 `dataType`，设计若改成"选完文件后逐个选"，
只换 `FileHeaderBar` 的交互，service / hook 不用动。

### 4.4 Replace Document

不变。`FileSelector.tsx:216` 仍直接打开单选文件框，`useOCRData.replaceFile` 调 getUploadUrl 时**不带** `dataType`，
Java 在 `file/replace` 里把旧文件的类型复制给新文件。

### 4.5 当月 Proforma 横幅

`DataMappingPanel.tsx:1786-1815`（`hasParentTable` 计算）与 `:2063-2077`（横幅）**保留**（D9）。新任务
`parentTableId` 恒空，横幅不会出现；历史任务（含 devSupport 只读回放、上线前已进入映射的在途任务）照常显示。
建议顺手把 `web/services/api/ai/aiService.ts:255-258` 的 `parentTableId` 注释补一句"新任务恒为空，仅历史任务有值"。

---

## 5. 常量（`ai页/constants.ts`）

上传弹窗与映射页共用，加在 `UPLOAD_MAX_BATCH_BYTES`（`:13`）之后：

| 常量 | 值 | 备注 |
|---|---|---|
| `UPLOAD_DATA_TYPE_OPTIONS` | `[{value:'ACTUALS', label:'Actuals'}, {value:'PROFORMA', label:'Proforma'}]` | R12：只用 Proforma 字样 |
| `UPLOAD_DATA_TYPE_PLACEHOLDER` | `'Select'` | Q1 临时值 |
| `ACTUALS_CURRENT_MONTH_NOTE` | `'For Actuals files, data for the current month and later is not extracted.'` | 需求 §5.1 原文 |

上传弹窗从 `FinancialEntry/` 跨功能夹 import `aiFinancialExtraction/constants` 是既有先例（同属 financial 一级域）；
按 R5 理想位置是 `pages/financial/components/`，本期不迁。

---

## 6. 文案与 i18n

- 新增文案（横幅、TABLE TYPE、批量设置、占位、类型选择弹窗）全部英文，与所在文件现有文案一致地硬编码，并把会被设计改动的
  几条集中进 §5 的常量，Q1 / Q2 定稿时只改一处。
- 这与 `coding.md` §15（禁硬编码、四语言同步）不符，但 `web/pages/` 尚无 `useIntl` 消费方、financial 域整体未接 i18n，
  为一个弹窗单独引入 i18n 链路不划算——口径与 ERL 先例一致（`pages/exitReadiness/README.md:247-249`）。
- R12 全面核查结果：ai页 与上传弹窗内面向用户的 "Forecast" 只有 `DataMappingPanel.tsx:745` 一处，"Pro Forma" 0 处，
  §4.1 删掉即达成。`mspDotForecast` 等类名随 §4.1 一并删除。

---

## 7. 单元测试

Jest + `@testing-library/react@12`（无 `renderHook`；hook 用最小 Harness 组件承载，先例
`pages/askGoldie/memorySettings/hooks/useMemoryData.test.tsx`）。测试文件与被测文件同目录 `*.test.tsx`。

`jest.config.js` 没有任何全局 setup，新测试文件要自己补两件事：
- **新测试文件须显式引入 jest-dom**：`import '@testing-library/jest-dom'`（无 `setupFilesAfterEnv`，`toBeDisabled` /
  `toBeInTheDocument` 靠它；先例 `pages/exitReadiness/assessment/AssessmentPage.test.tsx`）（审核 C-19）。
- 没开 `clearMocks` / `resetMocks`，mock 调用记录跨用例累积：读 `mock.calls[0]` 的文件须在 `beforeEach` 里 `mockReset()`（审核 C-2）。

| 文件（新增） | 用例 | 关键 mock |
|---|---|---|
| `FinancialEntry/components/ImportStatementsModal.test.tsx` | ① 两个文件传完、都未选类型 → Next disabled ② 只选一个 → 仍 disabled ③ 逐个选齐 → enabled ④ 批量设 Actuals → 两行都是 Actuals 且 Next enabled；再把一行改 Proforma → Next 后 `commitUpload` 收到 `{companyId, files:[{fileId, dataType:'ACTUALS'}, {fileId, dataType:'PROFORMA'}]}` ⑤ 批量设置后再加一个文件 → 新行为空、Next disabled ⑥ 横幅文案常驻 ⑦ 上传中 Clear All 仍只清上传中的文件（行为回归） ⑧ 只有一个文件：批量设置照常显示，选好类型后 Next enabled（审核 D-13） | `@/services/service/ai/aiService`（`getAiUploadUrl` 按文件名回 fileId、`commitUpload`、`batchDeleteFilesByIds`）；`uploadValidation` 两个函数透传；`UploadErrorToast`；`window.XMLHttpRequest` 换成 `send()` 后触发 `load`(200) 的假实现。⑦ 另换一个 `send()` **不**触发 `load` 的变体，让文件停在上传中，其 `abort()` 走组件的 abort 分支（自动 load 的假实现到不了"上传中"）（审核 C-20） |
| `ai页/components/DataMappingPanel.test.tsx` | ① 打开 Unmapped 行的指派下拉 → 没有 "Actual" / "Forecast" 文本 ② 点 "Gross Revenue" → `onRowEdit` 第二参严格等于 `{editLgCategory:'Gross Revenue'}`，无 `editSourceDataType` 键 ③ Mapped 行选 "Unmapped Accounts" → patch 为 `{editLgCategory:'UNMAPPED'}`。（原 ④"PROFORMA 行指派后仍在 Proforma 标签页"删除：`onRowEdit` 是普通 `jest.fn`，面板数据不会变，断言恒真；行不换标签页已由 ② 的 patch 不含 `editSourceDataType` 保证（审核 C-24）） | 夹具：一个 `REVIEW_READY` 文件，行要有月份且每月有值（`canAssign` = `rowHasAllValues && !hasPredictMonth`，`:1140`） |
| `ai页/components/FileSelector.test.tsx` | ① 菜单点 Upload New Document → 出现类型弹窗、OK disabled、未打开文件框 ② 选 Proforma → OK → `HTMLInputElement.prototype.click` 被调用 ③ 对 multiple input 触发 change → `onUploadFiles(files, 'PROFORMA')` ④ 再次打开弹窗 → Radio 为空 ⑤ Replace Document 不出弹窗、直接打开单选框，`onReplaceFile(oldId, file)` 签名不变 | `fromModal`、`uploadStage:'done'`、两个 `REVIEW_READY` 文件且选中其一（Replace 才显示） |
| `ai页/hooks/useOCRData.test.tsx` | ① `uploadAdditionalFiles([f], 'ACTUALS')` → `getAiUploadUrl` 的 `fileList` 为 `[{fileName, length, dataType:'ACTUALS'}]` ② `replaceFile(old, f)` → `fileList[0]` 没有 `dataType` 键 | `getAiUploadUrl` 回 `{success:false}` 让流程在第一步收住；`uploadValidation`（`validateFiles` / `filterByMagicNumber` / `checkFileMagic` / `activeUploadNames`）透传 |

antd 在 jsdom 里的操作：Select 用 `fireEvent.mouseDown(combobox)` 打开，选项在
`.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[title="…"]`；Dropdown 菜单项在
`.ant-dropdown:not(.ant-dropdown-hidden) .ant-dropdown-menu-item`。骨架见 [code-examples](./code-examples.md)。

轻量校验：
- **tsc 判据：改动文件不新增 tsc 错误**（审核 C-23）。`npm run tsc` 在本地当不了闸门：`@types/color-convert` 是空壳
  stub 包，直接跑只报一条 TS2688 就中止；排除它后全仓存量约 1.4k 条错误（`eea52f3c` 实测 1377 条）。做法：
  ```
  npx tsc --noEmit -p tsconfig.json --types "$(ls node_modules/@types | grep -v '^color-convert$' | paste -sd, -)"
  ```
  输出按本期改动文件过滤，与改动前对比。基线：`AiFinancialExtractionPage.tsx` 2 条（`LeftOutlined` / `buildMappedData`
  未使用，非本期引入）、`ImportStatementsModal.tsx` 1 条（`CloseOutlined`，本期删掉后为 0），其余改动文件 0 条。
- `npm run lint`（含 `check:routes` / `check:pages`，本期不动路由）。

按根 `CLAUDE.md`，单测等用户下令再统一跑。

---

## 8. 发布与回滚

Java、前端、Python 三端在**同一个发布窗口**上线（审核 S-1 / A-1）：

| 顺序 | 内容 | 原因 |
|---|---|---|
| 1 | Java + 前端**同批**（本文全部改动） | commitUpload 请求体两端同时切换：旧前端 + 新 Java → `{fileIds}` 被 `@NotEmpty files` 拒（HTTP 422）；新前端 + 旧 Java → `fileIds` 缺失被拒。映射页上传同理（新 Java 的 uploadComplete 要求类型） |
| 2 | Python，**紧接第 1 步、同一窗口内** | 不能先发：登记行还没有类型，新任务会全部判失败。也不能拖：新前端已去掉逐行改派（§4.1），旧 Python 却忽略文件声明、照旧推断表类型——两步之间创建的任务，推断错的行在映射页改不回来，只能重传 |

回滚：**三端一起回滚**（审核 A-2）。只回 Java + 前端、留新 Python → 旧端不写声明，新 Python 把新任务全判 FILE_FAILED；
只回 Python → 又落回"新界面不能逐行改派 + 旧 Python 不认声明"。版本切换窗口里，开着旧页面的用户点 Next 会看到全局错误横幅
+ 每个文件一条上传失败吐司，刷新后恢复。发布后的核对 SQL 见 [dev-design-doc](./dev-design-doc.md) §3。

commitUpload 在原路径上改请求体，已拍板登记为例外（审核 A-3，见 dev-java §10 J-R8）：改 `commitUpload` 请求体的那次前端提交，
body 末尾加 `BREAKING CHANGE:` 脚注，写明须与 Java 同批发布。

---

## 9. 风险与待确认

| # | 项 | 说明 / 处置 |
|---|---|---|
| 1 | Clear All 与需求 §5.1 的画法不一致 | 代码里 Clear All 只在上传中出现、只清上传中的文件；需求画成列表底部常驻。按"功能保持现状"不改，常驻与否请设计在 Figma 里确认 |
| 2 | Q1 占位文案、Q2 映射页交互、弹窗宽度与手机布局 | 均为临时方案，集中在常量与 `FileHeaderBar` / less 内，定稿后小改 |
| 3 | 上线前已进入映射的在途任务 | 类型来自旧推断，上线后不能再逐行改；用户以前改过的类型保留生效但无法撤回。需要改类型只能重新上传。属 R7 的直接后果，建议产品知悉 |
| 4 | 文件框必须同步打开 | §4.3 的约束写进注释；单测 ② 守住 `click()` 在 OK 回调里被同步调用 |
| 5 | 跨表合并键里的 dataType | 混合批次让它比以前更重要，后续重构不能删（§4.2） |
| 6 | 422 时只显示通用失败 | commitUpload 校验失败时前端不展示服务端文案（`res.success` 判失败 → GENERIC 吐司）。前端已拦截，正常不可达，不另做 |
| 7 | 规范偏离 | i18n 硬编码（§6）、上传弹窗跨功能夹 import 常量（§5）、`services/api/ai` 仍以内联类型为主（§2.1；R8 README 本期补上，审核 A-11），均为存量口径，本期只保证新增部分落到 `request.ts` / `dto.ts` |
| 8 | **待拍板**：Python 的失败原因用户看不到（审核 D-1） | 未声明类型的文件被 Python 判 FILE_FAILED，错误 "Table type (Actuals / Proforma) was not declared for this file; please re-upload it" 已随 `error` 传进 `FileProcessingErrorsModal`（`AiFinancialExtractionPage.tsx:246`），但弹窗只渲染通用文案 + 文件名（`FileProcessingErrorsModal.tsx:38-49`，`error` 没用上）；只有只读回放（devSupport）才把失败文件放进列表并挂 error Tooltip（`FileSelector.tsx:355-363`）。可选：弹窗里在每个文件名下渲染它的 `error`。新前端已拦截未选类型，碰到的主要是发布窗口前后的在途任务 |
| 9 | **待拍板**：Actuals 标签页的月份选择器能选当月和未来月（审核 D-9） | NO DATE 行的 `MonthPickerPopover`（`DataMappingPanel.tsx:761-810`，用于 `:1107`、`:1160`）不限月份；在 Actuals 标签页选了当月 / 未来月，提交时被 Java Actuals 护栏静默剔除（`AiFinancialExtractionConflictServiceImpl.java:667-668` 按 `isClosedActualsMonth` 做 `removeIf`），用户无感知。可选：Actuals 标签页里禁用这些月份，或在选择器里显示固定说明 `ACTUALS_CURRENT_MONTH_NOTE` |
| 10 | **待拍板**：Actuals 文件被整份剔除时的空状态像解析失败（审核 D-10） | Actuals 文件只有当月 / 未来月数据时会被 Python 全部剔除，落到空状态 "No financial accounts found for the uploaded file."（`DataMappingPanel.tsx:2029-2033`）或 "No financial accounts extracted. …"（`UploadSuccessModal.tsx:31-34`），看着像解析失败。可选：两处空状态文案后追加 `ACTUALS_CURRENT_MONTH_NOTE` |
