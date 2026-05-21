# AI 财务智能解析 —— 验证与冲突解决接口文档

> **版本**: v1.8.0 · **更新日期**: 2026-05-21
> **作用范围**: 接口 ⑥ 验证（verify） + 接口 ⑦ 完成任务（completeTask）
> **包路径**: `com.gstdev.cioaas.web.ai.financial.extract`
> **关联文档**:
> - 总接口契约: `智能解析/接口文档.md`
> - 需求文档: `智能解析/Manual_Uploads_with_OCR_需求文档.md`
> - 数据库 Schema: `智能解析/调研/database-schema.md`

---

## 📌 v1.8.0 主要变更

1. **resolve / fileSave 合并为单一 `completeTask`**：路径从 `POST /conflicts/{taskId}/resolve` 改为 `POST /ai/financialExtraction/tasks/{taskId}/complete`；删除独立 `/fileSave` 端点。
2. **fileSave 场景内化为 completeTask 的退化输入**：当所有数据数组（`nonConflicts`、`resolutions`、`proformaData`）为空时，行为与 v1.7 的 fileSave 一致 —— 不写 fi_\*、只登记文件到 Imported Statements 文件夹、推 `COMPLETED`。
3. **响应增加 `registeredFileCount` 与 `documentationRedirectUrl`**：前端根据 `writtenAccounts` 决定走 Benchmark popup 还是 Documentation popup；URL 字段双带。
4. **删除 `AiFinancialFileSaveResponse` VO**：统一用 `AiFinancialResolveResultResponse`。

---

## 📌 v1.7.0 主要变更（历史）

1. **新增 fileSave 接口** `POST /ai/financialExtraction/tasks/{taskId}/fileSave`：未解析出有效财务指标时，前端调用本接口把 task 原始文件直接登记到公司 Documentation 页的 "Imported Statements" 文件夹下，task 进入 `COMPLETED`（PRD §3.4）。
2. **resolve 末尾自动登记原始文件**：常规 commit 流程在写完 fi_\* 与 Proforma 之后，自动把 task 关联的所有未删原始文件登记到 "Imported Statements" 文件夹（PRD §3.5 "不论是否抽取到财务科目，上传的源文档都会出现在 Imported Statements 文件夹下"）。
3. **`importedStatementsFolderId` 字段含真实 ID**：从 v1.4–v1.6 的 placeholder `"imported-statements"` 改为 `"ImportedStatements"`（与 V3 SQL 预置的 `company_documentation_folder.id` 一致）。
4. **新增 V3 SQL migration**：`sprint110/V3_imported_statements_folder.sql` 预置 Imported Statements 全局文件夹（permission=`"1,2,3"`、show_in_add=false）。
5. **幂等去重**：`(companyId, folderId, fileId)` 维度去重，resolve / fileSave 多次调用安全。

---

## 📌 v1.6.0 主要变更（历史）

1. **verify 响应扁平化**：`data` 直接是 `Array<ConflictItem>`，**移除**外层 `{conflicts, nonConflicts}` 包裹；ConflictItem 内字段（含 `contributingCellIds`）保持不变。
2. **`nonConflicts` 不再返回**：原 v1.4/v1.5 verify 响应里的 `nonConflicts[]` 字段移除（前端反馈无用）。
3. **resolve 接口保持不变**：仍接收 `{ nonConflicts, resolutions, proformaData }`。前端需自行计算 nonConflicts（典型做法：从本地 mappedData 中过滤掉 verify 返回的冲突 key）后传给 resolve。

---

## 📌 v1.5.0 主要变更（历史）

1. **resolve 接收 Proforma 数据**：新增 `proformaData[]` 字段；Proforma 不参与冲突检测，直接写入新 committed forecast 版本（PRD §3.5）。
2. **resolve 状态机扩容**：原 `{CONFLICT_RESOLUTION, READY_TO_COMMIT}` → 增加 `{REVIEWING, MAPPING_SUMMARY}`，允许"仅 Proforma"场景前端跳过 verify 直接调 resolve。
3. **跨年自动分组**：Proforma 按年聚合，每年生成一个新 committed forecast 版本，`source="Import Statements"`、`versionName="Imported YYYY-MM-DD"`、`versionNote="From task {taskId}"`。
4. **响应字段语义扩展**：`writtenDataTypes` 现可含 `["ACTUALS", "PROFORMA"]`；`writtenPeriods` 含两种数据的所有报告期；`writtenAccounts` 累加 Actuals fi_\* 写入 + Proforma 写入条目数。
5. **币种 / 单位换算复用**：Proforma 与 Actuals 共用同一份 FX 换算 + 同 key SUM 兜底逻辑。

---

## 📌 v1.4.0 主要变更（历史）

1. **verify 增强响应**：响应增加 `nonConflicts[]`（LG 为空 → 待自动写入；LG 与上传一致 → 跳过）；冲突项增加 `contributingCellIds: string[]`（前端用于在冲突弹窗展示明细）。
2. **mappedData 增加 `cellIds?: string[]`** 可选字段：前端传入贡献该聚合值的 cell 列表，后端在响应中透传到 `contributingCellIds`。
3. **resolve 请求结构简化**：原 `cellSnapshots[]` 替换为 `nonConflicts[]`（直接 passthrough verify 响应）+ `resolutions[]`；前端无需再准备 cell 级数据。
4. **暂不更新 `ai_financial_extraction_extracted_data`**：cell 级 `edit_*` 字段的入库由独立流程负责，本批接口不涉及。
5. **冲突解决业务正常工作**：fi_\* 写入、commit_audit 留痕、状态推进逻辑完整保留。

---

## 📌 v1.3.0 主要变更（历史 - 已撤销）

1. resolve 曾改为接收 `cellSnapshots[]`（cell 级），后端按 cellId UPDATE `ai_financial_extraction_extracted_data`。
2. v1.4.0 已撤销该方案 —— extracted_data UPDATE 由独立流程负责，resolve 不再需要 cell 级数据。

---

## 📌 v1.2.0 主要变更（历史）

1. **报告期字段合并**：请求 `mappedData[]` 中 `year` + `month` 两个字段合并为单一 `columnMonth: "YYYY-MM"`；响应 `ConflictItem` 中 `reportingYear` + `reportingMonth` 合并为 `columnMonth: "YYYY-MM"`。
2. 其余契约保持 v1.1.0 一致。

---

## 📌 v1.1.0 主要变更（历史）

1. **简化 verify 请求**：`filesExtractedData[].cellValues[]`（cell 级原始数据）改为 `mappedData[]`（前端聚合后的「指标 × 报告期 × 最终值」）。
2. **resolve 请求结构调整**：原 JSON 数组改为对象 `{ mappedData, resolutions }`；同时携带聚合数据 + 用户决定，让服务端能写入非冲突指标。
3. **记忆学习暂未启用**：resolve 成功后**不**再触发 `memory-learn` SQS（代码以 `TODO(memory-learn)` 注释保留，后续接入 Python 学习时取消注释即可）。

---

## 📑 目录

1. [前置约定](#前置约定)
2. [流程总览](#流程总览)
3. [接口 ⑥：验证（verify）](#接口-验证verify)
4. [接口 ⑦：完成任务（completeTask）](#接口-完成任务completetask)
5. [状态机](#状态机)
6. [LG 标准科目映射表](#lg-标准科目映射表)
7. [前端联调清单](#前端联调清单)
8. [典型场景示例](#典型场景示例)

---

## 前置约定

| 维度 | 说明 |
|------|------|
| 基础路径 | `/api/web` |
| Content-Type | `application/json`（请求 / 响应） |
| 认证 | Bearer Token；header: `Authorization: Bearer <token>` |
| 时区 | ISO 8601 UTC |
| ID 类型 | UUID 字符串（小写 + 连字符） |
| 响应包装 | `{ code, message, data }`；成功 `code=200`；失败抛业务异常由 `GlobalExceptionHandler` 兜底 |
| 业务边界 | 仅 **Actuals** 数据走冲突检测；**Proforma** 数据**由前端排除**，不传入 |

### 通用错误响应结构

```json
{
  "code": 400,
  "message": "Task is not ready for verification (current=DRAFT)",
  "data": null
}
```

> ⚠️ 本批接口的所有业务校验失败都会以 `BadRequestException` 形态抛出（HTTP 400），具体 message 见各接口的错误说明。

---

## 流程总览

```
1️⃣ 上传文件          POST /ai/financialExtraction/tasks/getUploadUrl
2️⃣ 上传完成          POST /ai/financialExtraction/tasks/{taskId}/uploadComplete
3️⃣ 轮询解析数据      GET  /ai/financialExtraction/tasks/{taskId}/pullExtractData
4️⃣ 用户审核与编辑    （前端本地状态；聚合在前端完成）
5️⃣ 验证（本文档）    POST /ai/financialExtraction/tasks/{taskId}/verify
   ├─ 无冲突 → 状态 READY_TO_COMMIT → 前端直接调用 6️⃣（resolutions 传空数组）
   └─ 有冲突 → 状态 CONFLICT_RESOLUTION → 前端展示冲突列表 → 用户逐条解决 → 6️⃣
6️⃣ 解决并提交（本文档）  POST /ai/financialExtraction/tasks/{taskId}/complete
```

### 前端职责（重要）

两个接口的数据粒度不同，前端要分别处理：

**verify（接收聚合数据）**

- 把 `pullExtractData` 返回的 cell 列表，按 `(lgCategory, columnMonth)` 整理；如果**不预合并**，后端也会自动 SUM 同 key 多条（典型场景：多文件同指标）
- 仅保留 `sourceIsMapped=true && dataType=ACTUALS && lgCategory ∈ 15 类` 的项
- 同 cell 的 `edit*` 优先 / 否则用 `source*`（前端 fallback；verify 看到的是用户最终值）
- Proforma 数据排除（不传入 verify；Proforma 不走冲突检测）

**resolve（passthrough verify 响应 + Proforma）**

- 把 verify 响应中的 `nonConflicts[]` 原样回传（Actuals；不需要任何加工）
- `resolutions[]` 携带用户对每条 PENDING 冲突的决定（OVERWRITE/SKIP + note）
- `proformaData[]` 携带预测数据（**不参与冲突检测**，直接写入 committed forecast）
- 后端：Actuals 用 `nonConflicts` 写非冲突指标 + `conflict_record.mapped_value` 写冲突指标；Proforma 按年分组各生成一个新 committed forecast 版本

**"仅 Proforma" 场景（PRD §3.5）**

- 前端**跳过 verify**，直接调 resolve；body 中 `nonConflicts=[]`、`resolutions=[]`、`proformaData=[...]`
- 任务状态从 `REVIEWING` / `MAPPING_SUMMARY` 直接进入 `COMPLETED`

**通用**

- 用户的 cell 级编辑由前端 state 管理；verify 阶段不入库 cell；resolve 阶段也**不**入库 cell（extracted_data UPDATE 由独立流程处理）
- 冲突弹窗里要展示"哪些 cell 贡献了这个聚合值"时，用 verify 响应中 conflict 的 `contributingCellIds` 反查前端 state 即可

---

## 接口 ⑥：验证（verify）

### 基本信息

| 项 | 值 |
|---|---|
| 接口路径 | `POST /api/web/ai/financialExtraction/tasks/{taskId}/verify` |
| 调用时机 | 用户在 Mapping Summary 页点击 **Start Verification** 按钮 |
| 幂等性 | **可重复调用**（每次会清空旧冲突重新生成；用户回退修改 mapping 后重跑安全） |
| 核心职责 | 1) 把 `mappedData[]` 按公司币种换算 + 按 `(lgCategory, columnMonth)` 自动 SUM 合并多文件来源的同 key 项<br/>2) 与 `finance_manual_data` 现存值逐项比对<br/>3) 清空旧 `conflict_record` 并写入新冲突列表<br/>4) 按 LG enum × columnMonth 升序填 `resolved_order`<br/>5) 推进任务状态<br/>**6) 响应 `data` 直接是 `Array<ConflictItem>`（v1.6.0）** |

### 请求

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `taskId` | string(UUID) | 是 | 任务 ID |

#### Body 结构

```typescript
{
  mappedData: Array<{
    lgCategory: string;     // 必填，LG 标准科目（见 §LG 映射表的 API Code）
    columnMonth: string;    // 必填，报告期，格式 YYYY-MM（如 "2025-09"）
    value: number;          // 必填，聚合后的最终值
    currency?: string;      // 选填，如 "USD"；省略或等于公司币种则不换算
    unitType?: "CURRENCY" | "PERCENT";   // 选填，默认 "CURRENCY"；PERCENT 不参与币种换算
    cellIds?: string[];     // 选填，贡献该聚合值的 cell ID 列表；后端会在响应 contributingCellIds 中合并同 key 多条
  }>;
}
```

#### `mappedData` 元素字段详解

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `lgCategory` | string(≤50) | 是 | 必须是 [LG 映射表](#lg-标准科目映射表) 中的 API Code（大小写不敏感）。`UNMAPPED` 或不在 15 类中将被**静默丢弃**，不入冲突表 |
| `columnMonth` | string | 是 | 报告期，格式严格为 `YYYY-MM`（如 `"2025-09"`）。年份范围 1900-9999，月份 01-12，必须补零 |
| `value` | number(BigDecimal) | 是 | 前端已聚合的最终值。CURRENCY 单位传金额数值；PERCENT 单位传小数（如 0.30 表示 30%） |
| `currency` | string | 否 | 该值所代表的币种（如 `USD`）。空值或等于公司当前币种时不换算；不一致时后端按 (P&L→月均 / BS→月末) 汇率换算到公司币种 |
| `unitType` | string | 否 | `CURRENCY`（默认） 或 `PERCENT`；`PERCENT` 不进行币种换算 |
| `cellIds` | string[] | 否 | 贡献该聚合值的 cell ID 列表（来自 `pullExtractData` 的 `cellId`）。后端把同 key 多条的 cellIds 合并后透传到响应的 `contributingCellIds`，便于前端在冲突弹窗中展示明细 |

> ✅ **多文件同 key 自动合并**：同一 `(lgCategory, columnMonth)` 出现多次时（典型场景：同一指标的数据分散在多个文件中），后端会自动 SUM 求和后再与 LG 现存值对比，前端不需要预先合并。币种不一致的多条会先按汇率换算到公司币种再求和；`unitType=PERCENT` 的条目不参与币种换算。

#### 请求示例

```json
{
  "mappedData": [
    {
      "lgCategory": "Revenue",
      "columnMonth": "2025-09",
      "value": 123000.50,
      "currency": "USD",
      "unitType": "CURRENCY",
      "cellIds": ["c-001", "c-002"]
    },
    {
      "lgCategory": "Cash",
      "columnMonth": "2025-09",
      "value": 500000.00,
      "currency": "USD",
      "cellIds": ["c-010"]
    },
    {
      "lgCategory": "R&D Expenses",
      "columnMonth": "2025-09",
      "value": 0.30,
      "unitType": "PERCENT",
      "cellIds": ["c-020"]
    }
  ]
}
```

### 响应

#### 成功响应（HTTP 200）

```typescript
{
  code: 200,
  message: "success",
  data: Array<ConflictItem>;       // v1.6.0 起 data 直接是冲突列表（不再嵌套 conflicts/nonConflicts）
}

type ConflictItem = {
  conflictId: string;
  taskId: string;
  lgCategory: string;
  dataClassification: string;        // 本期固定 "ACTUALS"
  columnMonth: string;               // "YYYY-MM"
  existingValue: number;
  mappedValue: number;
  resolution: "PENDING";              // 初始；resolve 后变为 OVERWRITE/SKIP
  note: string;                       // PENDING 时为空串
  resolvedOrder: number;
  contributingCellIds: string[];
};
```

> ⚠️ v1.6.0 起 verify 不再返回 `nonConflicts`。如果 resolve 仍需要 `nonConflicts[]`（用于驱动非冲突指标的 fi_\* 写入），由**前端自行计算**：从本地 mappedData 中过滤掉响应里出现的所有 `(lgCategory, columnMonth)` 冲突 key，剩余的就是 nonConflicts。

#### `ConflictItem` 字段详解

| 字段 | 类型 | 说明 |
|---|---|---|
| `conflictId` | string(UUID) | 冲突主键；后续在 resolve 请求的 `resolutions[].conflictId` 中引用 |
| `taskId` | string(UUID) | 任务 ID |
| `lgCategory` | string | LG 标准科目（与映射表 API Code 一致） |
| `dataClassification` | string | 数据分类；本期固定为 `"ACTUALS"` |
| `columnMonth` | string | 报告期，格式 `YYYY-MM`（如 `"2025-09"`） |
| `existingValue` | number | LG 现有值（已换算为公司币种）；本期为冲突所以 ≠ null |
| `mappedValue` | number | 本次映射聚合值（已换算为公司币种）。**注：resolve 阶段 OVERWRITE 写入用的是此值**，verify→resolve 期间值不变 |
| `resolution` | string | 初始为 `"PENDING"`；用户解决后变为 `"OVERWRITE"` 或 `"SKIP"` |
| `note` | string | 备注；`PENDING` 时为空串 |
| `resolvedOrder` | number | Save & Next 跳转排序序号（LG 15 类 enum 顺序 × columnMonth 升序，从 1 开始） |
| `contributingCellIds` | string[] | 贡献该聚合值的 cell ID 列表（来自请求 `mappedData[].cellIds`）；前端可用于在冲突弹窗中展示明细 |

> 📌 **响应只含冲突项**：LG 与上传不一致的 `(lgCategory, columnMonth)` → 入 `data[]`；LG 为空 / 一致 → 不在响应中出现（前端从本地 mappedData 自行计算 nonConflicts 给 resolve）。

#### 响应示例（有冲突）

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "conflictId": "8f2e1d0c-9b8a-7654-3210-fedcba987654",
      "taskId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "lgCategory": "Revenue",
      "dataClassification": "ACTUALS",
      "columnMonth": "2025-09",
      "existingValue": 100000.0000,
      "mappedValue": 123000.5000,
      "resolution": "PENDING",
      "note": "",
      "resolvedOrder": 1,
      "contributingCellIds": ["c-001", "c-002"]
    },
    {
      "conflictId": "7e1d0c9b-8a76-5432-10fe-dcba98765432",
      "taskId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "lgCategory": "Revenue",
      "dataClassification": "ACTUALS",
      "columnMonth": "2025-10",
      "existingValue": 98000.5000,
      "mappedValue": 34.7600,
      "resolution": "PENDING",
      "note": "",
      "resolvedOrder": 2,
      "contributingCellIds": ["c-003"]
    }
  ]
}
```

#### 响应示例（无冲突）

```json
{
  "code": 200,
  "message": "success",
  "data": []
}
```

> 🟢 **无冲突时**：任务状态自动推进为 `READY_TO_COMMIT`，前端应直接调用接口 ⑦ completeTask（body 中 `resolutions` 传空数组 `[]`，`nonConflicts` 把 verify 响应的 `nonConflicts[]` 原样回传）触发 fi\_\* 写入。

### 错误响应

| HTTP | 触发条件 | 用户可见消息（message） |
|---|---|---|
| 400 | `taskId` 为空 | `taskId is required` |
| 400 | 任务不存在 | `Task not found: {taskId}` |
| 400 | 任务已逻辑删除 | `Task not found or deleted: {taskId}` |
| 400 | 状态不允许 verify | `Task is not ready for verification (current=DRAFT)` |
| 400 | 请求体缺失 `mappedData` 或为空数组 | `mappedData must not be empty`（由 `@NotEmpty` 校验） |
| 400 | 任意 item 缺 `lgCategory` / `columnMonth` / `value` | `must not be null/blank` |
| 400 | `columnMonth` 格式非法（非 `YYYY-MM`、月份越界、未补零） | `columnMonth must be in YYYY-MM format` |

### 业务规则细节

1. **状态机入口**：当前状态必须 ∈ `{REVIEWING, MAPPING_SUMMARY, VERIFY_PENDING, VERIFYING, CONFLICT_RESOLUTION, READY_TO_COMMIT}`；后两个允许用户回退后重跑。
2. **重跑清理**：每次 verify 都会先 `DELETE FROM ai_financial_extraction_conflict_record WHERE task_id = ?` 再重建。前端不需要先调清空接口。
3. **冲突判定规则**：
   - LG 现有值为 `null` → 不入冲突表（resolve 时自动写入）
   - LG 现有值 == mapped → 不入冲突表（视为一致，resolve 时不写）
   - LG 现有值 ≠ mapped → 入冲突表，需用户解决
4. **币种换算**：`item.currency` 与公司当前币种不一致且 `unitType ≠ PERCENT` 时按汇率换算到公司币种；P&L 类（Revenue / COGS / 6 类 Expense&Payroll）用 `MONTHLY_AVERAGE`，BS 类用 `MONTHLY_LAST_DAY`。汇率取不到时降级使用原值并打 WARN 日志。
5. **过滤规则**（item 被静默丢弃）：
   - `lgCategory` 不在 15 类中（含 `UNMAPPED`）
   - `value` 为 `null`
6. **`resolved_order` 计算**：先按 LG 15 类 enum 顺序排序，同 metric 内按 `columnMonth` 升序，从 1 开始顺序填序号。
7. **副作用**：本接口**不修改** `ai_financial_extraction_extracted_data`；cell 级编辑由前端 state 管理。

---

## 接口 ⑦：完成任务（completeTask）

> **v1.8.0 起合并了原 resolve（冲突解决与提交）+ fileSave（未识别出有效财务指标直存文档）两个接口。**
> 同一端点根据 body 内容自动区分两种行为：
> - 有数据（任一数组非空）→ 写 fi\_\* / 提交 forecast / 写 commit_audit + 自动登记文件到 Documentation
> - 全空 → 仅登记原始文件到 "Imported Statements" 文件夹

### 基本信息

| 项 | 值 |
|---|---|
| 接口路径 | `POST /api/web/ai/financialExtraction/tasks/{taskId}/complete` |
| 调用时机 | 1) 有冲突场景：用户在 Conflict Resolution 页对所有冲突选择 OVERWRITE/SKIP + 填写 note 后点击 **Save** <br/>2) 无冲突场景：verify 返回 `conflicts=[]` 时前端自动调用（`resolutions` 传 `[]`）<br/>3) 退化场景：OCR 未识别出有效财务指标（PRD §3.4），三个数组都传 `[]` |
| 幂等性 | **非幂等**：成功后任务进入 `COMPLETED` 终态，重复调用会因状态不允许而失败 |
| 核心职责 | 1) UPDATE `conflict_record` + INSERT `conflict_note`<br/>2) Actuals：按 `nonConflicts[]` 与 `conflict_record.mapped_value` 写入 `finance_manual_data`（新版本行）<br/>3) 写 `commit_audit`（WRITTEN/OVERWRITTEN/SKIPPED 全记录）<br/>4) Proforma：按年分组 `proformaData[]` → 每年一个新 committed forecast 版本（写 `FinancialForecastHistory` + `FinancialForecastCurrent`，`source="Import Statements"`）<br/>5) 把 task 原始文件登记到公司 Documentation 的 "Imported Statements" 文件夹（去重）<br/>6) 推进任务状态到 `COMPLETED` |

> ⚠️ **memory-learn 暂未启用**：本期 completeTask 成功后**不**触发 Python 端 mapping memory 学习；后续启用时由后端无痛接入，前端契约不变。

### 请求

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `taskId` | string(UUID) | 是 | 任务 ID |

#### Body 结构

```typescript
{
  nonConflicts: Array<NonConflictItem>;     // verify 响应中的 nonConflicts，原样 passthrough；仅 Proforma 场景传 []
  resolutions: Array<ResolutionItem>;        // 每条 PENDING 冲突的处理；仅 Proforma 场景传 []
  proformaData: Array<ProformaItem>;        // Proforma 数据；无 Proforma 时传 []
}

type NonConflictItem = {
  lgCategory: string;                        // LG 标准科目
  columnMonth: string;                       // "YYYY-MM"
  mappedValue: number;                       // 后端写入 fi_* 的值（仅 willAction=WRITTEN 时生效）
  existingValue?: number | null;             // 可选，仅日志/审计用
  willAction?: "WRITTEN" | "CONSISTENT";     // 可选，仅日志/审计用
  contributingCellIds?: string[];            // 可选，仅日志/审计用
};

type ResolutionItem = {
  conflictId: string;                        // 必填，verify 返回的 conflictId
  action: "OVERWRITE" | "SKIP";              // 必填
  note: string;                              // 必填，trim 后长度 1-2000
};

type ProformaItem = {
  lgCategory: string;                        // 必填，15 类之一；UNMAPPED / 非 15 类被静默丢弃
  columnMonth: string;                       // 必填，"YYYY-MM"
  value: number;                             // 必填，聚合后的预测值
  currency?: string;                         // 选填；与公司币种不一致时换算
  unitType?: "CURRENCY" | "PERCENT";         // 选填，默认 CURRENCY
};
```

#### 字段语义

| 字段 | 必填 | 说明 |
|---|---|---|
| `nonConflicts[]` | 是 | 直接 passthrough verify 响应的 `nonConflicts[]`；前端不需要做任何加工。后端根据每项的 `(lgCategory, columnMonth)` + `mappedValue` 写入 fi_\* 的对应列。仅 Proforma 场景传 `[]` |
| `nonConflicts[].lgCategory` | 是 | LG 标准科目；非 15 类的项被静默丢弃 |
| `nonConflicts[].columnMonth` | 是 | 格式 `YYYY-MM`；非法的项被静默丢弃 |
| `nonConflicts[].mappedValue` | 是 | 写入 fi_\* 的值（已是公司币种） |
| `nonConflicts[].existingValue` / `willAction` / `contributingCellIds` | 否 | 可选 passthrough；后端不依赖这些字段做决策，仅用于日志便于排查 |
| `resolutions[]` | 是（可空数组） | 每条 PENDING 冲突必须出现一次；无冲突 / 仅 Proforma 场景传 `[]` |
| `resolutions[].conflictId` | 是 | 必须属于本 task；重复抛 400 |
| `resolutions[].action` | 是 | `OVERWRITE`（用 verify 时的 mappedValue 覆盖 LG）/ `SKIP`（保留 LG 现值） |
| `resolutions[].note` | 是 | trim 后非空，1-2000 字符 |
| `proformaData[]` | 是（可空数组） | Proforma 数据；按年分组写入新 committed forecast 版本。无 Proforma 时传 `[]` |

> 💡 **冲突指标的最终写入值**：取 `conflict_record.mapped_value`（verify 时固化），**不**取本次请求里任何字段 —— 保证用户决策与最终写入一致。`nonConflicts[]` 仅用于驱动**非冲突指标**的 fi_\* 写入。

#### `ProformaItem` 字段详解

| 字段 | 必填 | 说明 |
|---|---|---|
| `lgCategory` | 是 | 15 类之一；非 15 类（含 `UNMAPPED`）被静默丢弃 |
| `columnMonth` | 是 | `YYYY-MM`；月份 01-12 必须补零 |
| `value` | 是 | 前端聚合后的预测值 |
| `currency` | 否 | 与公司当前币种不一致时按汇率换算 |
| `unitType` | 否 | `CURRENCY`（默认）/ `PERCENT`；PERCENT 不参与币种换算 |

> 💡 **Proforma 写入路径**：每条 `(lgCategory, columnMonth)` 同 key 多条会被后端 SUM；按年分组后，每年调一次 `FinancialForecastDataService.acceptForecastDataSave`，**每年生成一个新 committed forecast 版本**：`source="Import Statements"`、`versionName="Imported YYYY-MM-DD"`（YYYY-MM-DD 为接口调用日期 UTC）、`versionNote="From task {taskId}"`。同年同月同指标的 LG 列被覆盖；type=Manual (0)。

#### 请求示例（有冲突）

> 假设 verify 返回的 `nonConflicts[]` 含 1 条（Cash 2025-09 待自动写入），冲突 2 条（Revenue 2025-09 / 2025-10）。前端把 nonConflicts 原样回传，加上对每条冲突的决定。

```json
{
  "nonConflicts": [
    {
      "lgCategory": "Cash",
      "columnMonth": "2025-09",
      "mappedValue": 500000.00,
      "existingValue": null,
      "willAction": "WRITTEN",
      "contributingCellIds": ["c-003"]
    }
  ],
  "resolutions": [
    {
      "conflictId": "8f2e1d0c-9b8a-7654-3210-fedcba987654",
      "action": "OVERWRITE",
      "note": "Q1 财报已审计修正，按上传值更新"
    },
    {
      "conflictId": "7e1d0c9b-8a76-5432-10fe-dcba98765432",
      "action": "SKIP",
      "note": "LG 数据来自独立审计渠道，保留不动"
    }
  ]
}
```

#### 请求示例（无冲突场景）

> verify 返回 `conflicts=[]`，`nonConflicts=[...]`。前端把 nonConflicts 原样回传，resolutions 传空数组。

```json
{
  "nonConflicts": [
    {
      "lgCategory": "Revenue",
      "columnMonth": "2025-09",
      "mappedValue": 200.00,
      "existingValue": null,
      "willAction": "WRITTEN",
      "contributingCellIds": ["c-001"]
    },
    {
      "lgCategory": "Cash",
      "columnMonth": "2025-09",
      "mappedValue": 500000.00,
      "existingValue": null,
      "willAction": "WRITTEN",
      "contributingCellIds": ["c-002"]
    }
  ],
  "resolutions": []
}
```

### 响应

#### 成功响应（HTTP 200）

```typescript
{
  code: 200,
  message: "success",
  data: {
    writtenAccounts: number;                // 实际写入 fi_* 的指标数（含 WRITTEN+OVERWRITTEN，不含 SKIPPED）
    writtenPeriods: string[];               // 写入的报告期，格式 YYYY-MM
    writtenDataTypes: string[];             // 写入的数据分类（本期固定 ["ACTUALS"]）
    writtenSourceFiles: number;             // 本 task 关联的源文件数
    importedStatementsFolderId: string;     // Documents 页文件夹 ID（占位符，待 Documentation 模块接入）
    benchmarkRedirectUrl: string;           // 前端跳转路径（history.push 用）
  }
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "writtenAccounts": 42,
    "writtenPeriods": ["2025-08", "2025-09", "2025-10"],
    "writtenDataTypes": ["ACTUALS"],
    "writtenSourceFiles": 3,
    "importedStatementsFolderId": "imported-statements",
    "benchmarkRedirectUrl": "/benchmark/info/550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 错误响应

| HTTP | 触发条件 | message |
|---|---|---|
| 400 | `taskId` 为空 | `taskId is required` |
| 400 | 任务不存在 / 已删除 | `Task not found: {taskId}` |
| 400 | 状态不允许 resolve | `Task cannot be committed in current state (current=...)` |
| 400 | `resolutions` 中 `note` 缺失 / 空白 | `Please provide a note before saving` |
| 400 | 某项 `conflictId` 为空 | `conflictId is required for each item` |
| 400 | 某项 `note` 为空或纯空白 | `Please provide a note before saving` |
| 400 | `resolutions` 中 `conflictId` 重复 | `Duplicate conflictId in resolve payload: {id}` |
| 400 | `conflictId` 不属于本 task | `conflictId does not belong to task: {id}` |
| 400 | 存在 PENDING 冲突未在请求中出现 | `Please resolve all conflicts and unmapped accounts before submitting` |
| 400 | `action` 不是 `OVERWRITE`/`SKIP` | `action must be OVERWRITE or SKIP` |
| 400 | `note` 长度 > 2000 | `size must be between 1 and 2000` |

### 业务规则细节

1. **状态机入口**：必须 ∈ `{REVIEWING, MAPPING_SUMMARY, CONFLICT_RESOLUTION, READY_TO_COMMIT}`。`REVIEWING`/`MAPPING_SUMMARY` 仅用于"仅 Proforma"场景（前端跳过 verify）。
2. **必须解决所有 PENDING 冲突**：请求 `resolutions[]` 必须包含 `conflict_record` 中所有 `resolution=PENDING` 的项；缺一即整批拒绝。
3. **extracted_data UPDATE**：**本接口不处理**（v1.4.0 起移出 resolve 流程）；cell 级 edit_\* 字段的入库由独立流程负责。
4. **写入值来源**：
   - **冲突指标**（在 `conflict_record` 中存在）：写入值取自 `conflict_record.mapped_value`（verify 时固化）。保证用户决策与最终写入一致
   - **非冲突指标**（在请求 `nonConflicts[]` 中）：写入值取自 `nonConflicts[].mappedValue`
5. **fi\_\* 写入策略**：
   - 取最新 `finance_manual_data WHERE company_id AND date='YYYY-MM-01' AND state IS NULL ORDER BY version_at DESC LIMIT 1` 作为底版
   - 复制所有字段到一个**新行**，分配新 `id`、`version_at=now()`、`state=NULL`、`is_forecast=false`
   - 按 `(lgCategory, columnMonth)` 写入对应列（覆盖底版的同列值）
   - 旧行因 `version_at` 更早自动变历史版本（PRD §3.5 "被覆盖的数据保留历史版本"）
6. **OVERWRITE / SKIP / WRITTEN 三种 audit 全部留痕**：
   - `WRITTEN` —— LG 本月无数据，本次写入新值（非冲突指标）
   - `OVERWRITTEN` —— LG 有值且与上传不同，用户选 OVERWRITE
   - `SKIPPED` —— LG 有值且与上传不同，用户选 SKIP（保留 LG，fi\_\* 不变但仍留痕）
   - LG 一致（`existing == mapped`） —— **不写 fi\_\*，也不写 audit**
7. **币种换算**：verify 阶段已经把 Actuals mappedValue 换算到公司币种；resolve 直接使用。Proforma 在 resolve 阶段做币种换算（P&L 类用月均、BS 类用月末汇率）。同 task 同 (date) 内多次 Actuals 写入合并到一个新版本行；Proforma 按年分组各成版本。

8. **Proforma 写入策略**：
   - 按 `year`（从 `columnMonth` 解析）分组
   - 每年调一次 `FinancialForecastDataService.acceptForecastDataSave(year, companyId, rows, source, versionName, versionNote)`
   - 该方法内部：删除该公司该年现有 `type=Manual` 的 forecast_current 行 → INSERT 新 forecast_current 与 forecast_history → 写 forecast_year_version 一行（新版本元数据）
   - **失败处理**：任意一年写入异常 → 整个事务回滚（包括已写的 fi_\*）

9. **`writtenAccounts` / `writtenPeriods` / `writtenDataTypes` 语义扩展**：
   - `writtenAccounts` = Actuals fi_\* 写入条目数 + Proforma forecast 写入条目数
   - `writtenPeriods` = 两种数据的所有报告期 YYYY-MM 列表（去重）
   - `writtenDataTypes` = `["ACTUALS"]` / `["PROFORMA"]` / `["ACTUALS", "PROFORMA"]`
9. **memory-learn**：暂未启用。代码以 `TODO(memory-learn)` 注释保留，后续启用时由后端取消注释即可，前端契约不变。
10. **`writtenAccounts` 计数语义**：每条 `(lgCategory, columnMonth)` 写入操作算 1；SKIPPED 不计；一致不计。
11. **自动登记原始文件到 Documentation**（v1.7.0+）：completeTask 末尾把 task 关联的所有未删原始文件登记到公司 Documentation 页的 "Imported Statements" 文件夹下；按 `(companyId, folderId, fileId)` 去重；正常 commit + 仅 fileSave 退化场景共用同一登记逻辑。

### 退化场景：未识别出有效财务指标（原 fileSave 接口）

按 PRD §3.4：当 OCR 未识别出任何可映射数据，用户在 Mapping 页看到 "No mapped data" 提示后点击 Next 时调用本接口，**body 中三个数组都传空**：

```json
{
  "nonConflicts": [],
  "resolutions": [],
  "proformaData": []
}
```

后端识别为退化场景：跳过 fi_\* / forecast / commit_audit 写入，**仅**登记原始文件到 Imported Statements 文件夹，state → `COMPLETED`。响应字段中 `writtenAccounts=0`、`writtenPeriods/writtenDataTypes=[]`、`registeredFileCount>0`。

**前端 popup 文案**（PRD §3.4）：

> No financial accounts extracted. **{writtenSourceFiles}** file(s) have been uploaded to the Imported Statements folder in Documentation.

两个按钮：
- `Close` —— 关闭弹窗
- `Go to Documentation` —— `history.push(data.documentationRedirectUrl)`

### 前端跳转判定（统一规则）

| 条件 | 跳转 URL |
|---|---|
| `writtenAccounts > 0`（有 fi_\* 或 forecast 写入） | `data.benchmarkRedirectUrl` —— 跳 Benchmark 页 |
| `writtenAccounts === 0`（退化场景） | `data.documentationRedirectUrl` —— 跳 All Documentation 页 |

---

## 状态机

```
                        ┌──────────────────────────────────────┐
                        │                                      │
                        ▼                                      │
┌─────────────┐    verify   ┌──────────────────────┐  resolve  │
│ MAPPING_    │ ─────────►  │       VERIFYING      │           │
│ SUMMARY     │              └──────────┬───────────┘           │
└──────┬──────┘                         │                       │
       │                                ▼                       │
       │              ┌─────────────────┴─────────────────┐     │
       │              │                                   │     │
       │     有冲突   ▼                          无冲突   ▼     │
       │   ┌─────────────────────┐         ┌──────────────────┐ │
       │   │ CONFLICT_           │         │ READY_TO_COMMIT  │ │
       │   │ RESOLUTION          │         └──────────┬───────┘ │
       │   └──────────┬──────────┘                    │         │
       │              │ resolve                       │ resolve │
       │              ▼                               ▼ (空数组)│
       │   ┌──────────────────────────────────────────┐         │
       │   │              COMMITTING                  │         │
       │   └──────────────────┬───────────────────────┘         │
       │                      ▼                                 │
       │   ┌──────────────────────────────────────────┐         │
       │   │              COMPLETED ✅                │         │
       │   └──────────────────────────────────────────┘         │
       │                                                        │
       └─ 用户从 ConflictPage 回退到 MappingPage ────────────────┘
              （CONFLICT_RESOLUTION / READY_TO_COMMIT 允许重跑 verify）
```

**状态转换规则**：

| 当前状态 | 允许的下一步 | 触发 |
|---|---|---|
| `REVIEWING` | `VERIFYING` | verify |
| `MAPPING_SUMMARY` | `VERIFYING` | verify |
| `VERIFY_PENDING` | `VERIFYING` | verify（重试） |
| `VERIFYING` | `VERIFYING` | verify（重试） |
| `CONFLICT_RESOLUTION` | `VERIFYING` 或 `COMMITTING` | verify（重跑） 或 resolve |
| `READY_TO_COMMIT` | `VERIFYING` 或 `COMMITTING` | verify（重跑） 或 resolve |
| `COMMITTING` | `COMPLETED` | resolve 事务成功 |
| `COMPLETED` | — | 终态 |

---

## LG 标准科目映射表

> 接口 `lgCategory` 字段使用以下 **API Code**（大小写不敏感）；后端会映射到 `finance_manual_data` 对应列。

| LG enum 顺序 | API Code | 报表类型 | finance_manual_data 列 |
|:---:|---|---|---|
| 1 | `Revenue` | P&L | `gross_revenue` |
| 2 | `COGS` | P&L | `cogs` |
| 3 | `Sales & Marketing Expenses` | P&L | `sm_expenses_percent` |
| 4 | `R&D Expenses` | P&L | `rd_expenses_percent` |
| 5 | `G&A Expenses` | P&L | `ga_expenses_percent` |
| 6 | `S&M Payroll` | P&L | `sm_payroll_percent` |
| 7 | `R&D Payroll` | P&L | `rd_payroll_percent` |
| 8 | `G&A Payroll` | P&L | `ga_payroll_percent` |
| 9 | `Cash` | BS | `cash` |
| 10 | `Accounts Receivable` | BS | `accounts_receivable` |
| 11 | `R&D Capitalized` | BS | `capitalized_rd` |
| 12 | `Other Assets` | BS | `assets_other` |
| 13 | `Accounts Payable` | BS | `accounts_payable` |
| 14 | `Long Term Debt` | BS | `long_term_debt` |
| 15 | `Other Liabilities` | BS | `liabilities_other` |

> 🟡 **特殊值**：`UNMAPPED` 不参与映射，传入将被静默丢弃（不入冲突表、不写 fi_\*）。

> 💡 `resolved_order` 跨 metric 排序使用上表的 enum 顺序 1-15。

---

## 前端联调清单

### 1. verify 调用准备

- [ ] 在前端把当前页 `cellValues[]` 按 `(lgCategory, columnMonth, ACTUALS)` 聚合（也可以不预合并，让后端在 verify 时按同 key 自动 SUM）
- [ ] 字段优先级：`edit*` 非空用 `edit*`，否则用 `source*`；`editValue` 为 `null` 时回退 `sourceValue`
- [ ] 过滤：`sourceIsMapped=false` / 数据类型非 ACTUALS / `lgCategory` 非 15 类 / `value` 为 null / 月份非法 → 都不传
- [ ] PERCENT 指标的 `unitType` 必须明确填 `"PERCENT"`
- [ ] `currency` 字段统一用大写 ISO 4217 代码（USD/EUR/CNY/...）

### 2. verify 响应处理

- [ ] `conflicts.length === 0` → 跳过 ConflictPage，直接调用 completeTask（resolutions=[]）
- [ ] `conflicts.length > 0` → 进入 ConflictPage，按 `resolvedOrder` 顺序展示冲突详情弹窗
- [ ] 每条冲突展示：`lgCategory` + `columnMonth` + `existingValue` vs `mappedValue` + Radio + Note 输入框
- [ ] Note 输入框校验：trim 后非空，长度 ≤ 2000

### 3. resolve 调用准备

- [ ] `nonConflicts` 把 verify 响应的 `nonConflicts[]` **原样回传**（passthrough，前端不需要加工）
- [ ] `resolutions[]` 为每条 `PENDING` 冲突提供 OVERWRITE/SKIP + note；缺一会被后端拒绝整批
- [ ] **无冲突场景**：`resolutions` 传 `[]`（空数组）；`nonConflicts` 仍要传（驱动 fi_\* 自动写入）

### 4. resolve 响应处理

- [ ] 成功 popup 文案：`The following data has been submitted to {companyName}: {writtenSourceFiles} Source Files, {writtenDataTypes.length} Data Types Updated, {writtenAccounts} Mapped Accounts`
- [ ] 点击 Close 后 `history.push(data.benchmarkRedirectUrl)` 跳转到 Benchmarking 页

### 5. 错误处理建议

- [ ] 400 `Task cannot be committed in current state` → 提示"任务状态已变更，请刷新页面"
- [ ] 400 `Please resolve all conflicts...` → 提示"还有未解决的冲突，请回到冲突页"
- [ ] 400 `Please provide a note before saving` → 高亮 Note 输入框，禁用 Save 按钮直至填写

### 6. 网络与状态

- [ ] verify / resolve 请求体小（数十到数百行），timeout 建议 30s 即可
- [ ] 两个接口都不需要轮询，单次请求拿到结果即可
- [ ] 用户在 ConflictPage 回退到 MappingPage 后再次进入 verify，状态机允许重跑

---

## 典型场景示例

### 场景 A：无冲突直接提交

```http
POST /api/web/ai/financialExtraction/tasks/7c9e6679-7425-40de-944b-e07fc1f90ae7/verify
```

```json
{
  "mappedData": [
    { "lgCategory": "Revenue", "columnMonth": "2025-09", "value": 200,    "currency": "USD", "cellIds": ["c-001"] },
    { "lgCategory": "Cash",    "columnMonth": "2025-09", "value": 500000, "currency": "USD", "cellIds": ["c-002"] }
  ]
}
```

响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "conflicts": [],
    "nonConflicts": [
      { "lgCategory": "Revenue", "columnMonth": "2025-09", "mappedValue": 200,    "existingValue": null, "willAction": "WRITTEN", "contributingCellIds": ["c-001"] },
      { "lgCategory": "Cash",    "columnMonth": "2025-09", "mappedValue": 500000, "existingValue": null, "willAction": "WRITTEN", "contributingCellIds": ["c-002"] }
    ]
  }
}
```

前端直接调：

```http
POST /api/web/ai/financialExtraction/tasks/7c9e6679-7425-40de-944b-e07fc1f90ae7/complete
```

```json
{
  "nonConflicts": [
    {
      "lgCategory": "Revenue",
      "columnMonth": "2025-09",
      "mappedValue": 200,
      "existingValue": null,
      "willAction": "WRITTEN",
      "contributingCellIds": ["c-001"]
    },
    {
      "lgCategory": "Cash",
      "columnMonth": "2025-09",
      "mappedValue": 500000,
      "existingValue": null,
      "willAction": "WRITTEN",
      "contributingCellIds": ["c-002"]
    }
  ],
  "resolutions": []
}
```

响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "writtenAccounts": 2,
    "writtenPeriods": ["2025-09"],
    "writtenDataTypes": ["ACTUALS"],
    "writtenSourceFiles": 1,
    "importedStatementsFolderId": "imported-statements",
    "benchmarkRedirectUrl": "/benchmark/info/550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 场景 B：单冲突 OVERWRITE

verify 请求：

```json
{
  "mappedData": [
    { "lgCategory": "Revenue", "columnMonth": "2025-09", "value": 123, "currency": "USD", "cellIds": ["c-001"] }
  ]
}
```

verify 响应（LG 已有 Revenue 2025-09=100000，与上传 123 不同 → 冲突）：

```json
{
  "code": 200,
  "data": {
    "conflicts": [
      {
        "conflictId": "8f2e1d0c-9b8a-7654-3210-fedcba987654",
        "lgCategory": "Revenue",
        "columnMonth": "2025-09",
        "existingValue": 100000.0000,
        "mappedValue": 123.0000,
        "resolution": "PENDING",
        "resolvedOrder": 1,
        "contributingCellIds": ["c-001"]
      }
    ],
    "nonConflicts": []
  }
}
```

用户选择 OVERWRITE，填写 note 后提交 resolve：

```json
{
  "nonConflicts": [],
  "resolutions": [
    {
      "conflictId": "8f2e1d0c-9b8a-7654-3210-fedcba987654",
      "action": "OVERWRITE",
      "note": "Q1 财报已审计修正"
    }
  ]
}
```

后端动作：

- `conflict_record.resolution = OVERWRITE`，`resolved_by/_at` 填充
- `conflict_note` 顶层 INSERT 一条（`auto_generated=false`，`resolution=OVERWRITE`）
- `finance_manual_data` 写入新行，`gross_revenue = 123.0000`（取自 verify 时固化的 `conflict_record.mapped_value`）
- `commit_audit` 写入：`action=OVERWRITTEN, old_value=100000.0000, new_value=123.0000, conflict_note_id=<note.id>`
- 任务状态 → `COMPLETED`

### 场景 C：跨币种聚合

公司币种 `EUR`。前端聚合时把 Cash 2025-09 的两个源账目（USD 1000 + EUR 500）合并成一行 EUR 等值后传入，或保留币种分项让后端换算：

**方案 1：前端预换算后聚合**（推荐）

```json
{
  "mappedData": [
    { "lgCategory": "Cash", "columnMonth": "2025-09", "value": 1400, "currency": "EUR" }
  ]
}
```

**方案 2：前端按币种分项，由后端换算**

```json
{
  "mappedData": [
    { "lgCategory": "Cash", "columnMonth": "2025-09", "value": 1000, "currency": "USD" },
    { "lgCategory": "Cash", "columnMonth": "2025-09", "value": 500,  "currency": "EUR" }
  ]
}
```

后端会把 USD 1000 按 `getRateByTargetCurrency("EUR", "USD", "2025-09-01", MONTHLY_LAST_DAY)` 换算成 EUR（假设汇率 0.9 → 900 EUR），与 EUR 500 求和得 1400 EUR；与 LG 的 cash 列（按 EUR 存储）比对。

> 💡 推荐使用**方案 1**，前端控制聚合更明确；方案 2 是兜底能力。

### 场景 E：多文件同指标合并

公司 Q3 财报数据分散在 3 个文件中（P&L 主表 / 补充明细 / 修订表）。前端直接把每个文件下的对应行各发一条，后端会按 `(lgCategory, columnMonth)` 自动合并：

verify 请求（同 `(Revenue, 2025-09)` 来自 3 个不同文件）：

```json
{
  "mappedData": [
    { "lgCategory": "Revenue", "columnMonth": "2025-09", "value": 60000, "currency": "USD" },
    { "lgCategory": "Revenue", "columnMonth": "2025-09", "value": 25000, "currency": "USD" },
    { "lgCategory": "Revenue", "columnMonth": "2025-09", "value": 15000, "currency": "USD" }
  ]
}
```

后端处理：

1. 三条 `(Revenue, 2025-09)` 都换算到公司币种（已是 USD，rate=1）
2. SUM → 100000
3. 查 LG `finance_manual_data.gross_revenue` 对应 2025-09 的现存值
4. 若 LG 现存 = 100000 → 无冲突；若 LG 现存 ≠ 100000 → 入冲突表，`mappedValue=100000`

> 💡 verify 把多文件来源合并后返回 `nonConflicts[]`，前端 passthrough 给 resolve 即可；resolve 不再做聚合。

### 场景 D：用户在 ConflictPage 回退修改 Mapping 后重跑 verify

任务状态 = `CONFLICT_RESOLUTION`。前端再次调用 verify：

```http
POST /api/web/ai/financialExtraction/tasks/{taskId}/verify
```

后端动作：

1. 状态校验通过（`CONFLICT_RESOLUTION` 在允许列表中）
2. 状态 → `VERIFYING`
3. `DELETE FROM conflict_record WHERE task_id=?`（清空旧冲突）
4. 按新 `mappedData` 重新聚合 + 生成新 `conflict_record`
5. 状态 → `CONFLICT_RESOLUTION` 或 `READY_TO_COMMIT`

前端再次拿到新 `conflicts[]`，旧冲突的解决结果（OVERWRITE/SKIP/note）**已丢失**，需要用户重新操作。

---

## 附录

### A. 涉及的数据表

| 表 | 用途 | 写入时机 |
|---|---|---|
| `ai_financial_extraction_task` | 任务主表 | 状态推进 |
| `ai_financial_extraction_extracted_data` | cell 级解析结果（含 edit_\* 字段） | AI 阶段 INSERT；resolve 阶段按 cellId UPDATE `edit_*` + `user_edited` + `edit_at` |
| `ai_financial_extraction_conflict_record` | 冲突列表 | verify 重建 |
| `ai_financial_extraction_conflict_note` | 冲突解决备注 | resolve INSERT |
| `ai_financial_extraction_commit_audit` | fi\_\* 写入流水 | resolve INSERT（WRITTEN/OVERWRITTEN/SKIPPED 全记） |
| `finance_manual_data` | LG 财务数据（写入目标） | resolve INSERT 新版本行 |

### B. 下游影响

- **fi\_\* 下游**：`finance_manual_data` 的新版本会被 normalization / benchmark 流程自动消费（依赖现有 `version_at` 监听机制）。
- **memory-learn**：暂未启用；代码以 `TODO(memory-learn)` 注释保留，后续启用时不影响前端契约。

### C. 未来扩展点（不影响 v1.1 契约）

- `conflict_note` 的 thread 回复接口（PRD §3.6 Notes 列表页）
- `commit_audit` 反查接口（审计排查用）
- `Idempotency-Key` 头支持（防重复提交）
- memory-learn SQS 启用（resolve 末尾自动触发）

---

**更新历史**

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-05-18 | v1.0.0 | 初版：verify 接收 cellValues[]；resolve 接收 ResolveItem[]；触发 memory-learn SQS |
| 2026-05-18 | v1.1.0 | verify 改为接收 `mappedData[]`（前端预聚合）；resolve 改为对象 `{mappedData, resolutions}`；memory-learn 暂停启用（保留 TODO 注释） |
| 2026-05-19 | v1.2.0 | `year` + `month` 合并为 `columnMonth: "YYYY-MM"`（请求 / 响应统一） |
| 2026-05-19 | v1.3.0 | resolve body 从聚合 `mappedData[]` 改为 cell 级 `cellSnapshots[]`（cellId 驱动 UPDATE extracted_data）；后端从 `editIsMapped=true` 的 cell 自行聚合写 fi_\*；verify 契约不变 |
| 2026-05-19 | v1.4.0 | verify 响应新增 `nonConflicts[]`、`contributingCellIds`；mappedData 增加可选 `cellIds`；resolve 简化为 `{ nonConflicts (passthrough), resolutions }`；extracted_data UPDATE 移出本接口由独立流程负责 |
| 2026-05-19 | v1.5.0 | resolve 增加 `proformaData[]` 字段（预测数据直接写新 committed forecast）；状态机允许从 `REVIEWING`/`MAPPING_SUMMARY` 进入（仅 Proforma 场景跳过 verify）；响应字段 `writtenDataTypes` 现可含 `PROFORMA` |
| 2026-05-20 | v1.6.0 | verify 响应扁平化：`data` 直接是 `Array<ConflictItem>`；移除 `nonConflicts[]`（前端反馈无用，自行从 mappedData 计算后传给 resolve）；resolve 接口契约保持不变 |
| 2026-05-21 | v1.7.0 | 新增 `POST /tasks/{taskId}/fileSave` 接口（未识别出有效财务指标时直存 Documentation）；resolve 末尾自动登记原始文件到 "Imported Statements" 文件夹；新增 V3 SQL 预置该全局文件夹；`importedStatementsFolderId` 字段填真实 ID `"ImportedStatements"` |
| 2026-05-21 | v1.8.0 | resolve / fileSave 合并为单一 `POST /tasks/{taskId}/complete`；空数组输入即退化为 fileSave 行为；响应增加 `registeredFileCount` + `documentationRedirectUrl`；删除独立 fileSave 端点与 VO |
