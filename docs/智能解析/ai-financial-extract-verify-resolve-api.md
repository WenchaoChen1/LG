# AI 财务智能解析 —— 验证与冲突解决接口文档

> **版本**: v1.1.0 · **更新日期**: 2026-05-18
> **作用范围**: 接口 ⑥ 验证（verify） + 接口 ⑦ 冲突解决与提交（resolve）
> **包路径**: `com.gstdev.cioaas.web.ai.financial.extract`
> **关联文档**:
> - 总接口契约: `智能解析/接口文档.md`
> - 需求文档: `智能解析/Manual_Uploads_with_OCR_需求文档.md`
> - 数据库 Schema: `智能解析/调研/database-schema.md`

---

## 📌 v1.1.0 主要变更

1. **简化 verify 请求**：`filesExtractedData[].cellValues[]`（cell 级原始数据）改为 `mappedData[]`（前端聚合后的「指标 × 报告期 × 最终值」）。
2. **resolve 请求结构调整**：原 JSON 数组改为对象 `{ mappedData, resolutions }`；同时携带聚合数据 + 用户决定，让服务端能写入非冲突指标。
3. **记忆学习暂未启用**：resolve 成功后**不**再触发 `memory-learn` SQS（代码以 `TODO(memory-learn)` 注释保留，后续接入 Python 学习时取消注释即可）。

---

## 📑 目录

1. [前置约定](#前置约定)
2. [流程总览](#流程总览)
3. [接口 ⑥：验证（verify）](#接口-验证verify)
4. [接口 ⑦：冲突解决与提交（resolve）](#接口-冲突解决与提交resolve)
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
6️⃣ 解决并提交（本文档）  POST /ai/financialExtraction/conflicts/{taskId}/resolve
```

### 前端职责（重要）

由于 verify / resolve 都接收**已聚合**的数据，下列工作在前端完成：

- 把 `pullExtractData` 返回的 cell 列表，按 `(lgCategory, year-month, ACTUALS)` 求和聚合
- 仅保留 `sourceIsMapped=true && dataType=ACTUALS && lgCategory ∈ 15类` 的项
- 同 cell 的 `edit*` 优先 / 否则用 `source*`（前端实现 fallback）
- Proforma 数据排除（不传入）
- 用户的 cell 级编辑由前端 state 管理，不需要回写后端（直到提交时聚合好再发）

---

## 接口 ⑥：验证（verify）

### 基本信息

| 项 | 值 |
|---|---|
| 接口路径 | `POST /api/web/ai/financialExtraction/tasks/{taskId}/verify` |
| 调用时机 | 用户在 Mapping Summary 页点击 **Start Verification** 按钮 |
| 幂等性 | **可重复调用**（每次会清空旧冲突重新生成；用户回退修改 mapping 后重跑安全） |
| 核心职责 | 1) 把 `mappedData[]` 按公司币种换算 + 同 key 兜底求和<br/>2) 与 `finance_manual_data` 现存值逐项比对<br/>3) 清空旧 `conflict_record` 并写入新冲突列表<br/>4) 按 LG enum × month 升序填 `resolved_order`<br/>5) 推进任务状态 |

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
    year: number;           // 必填，1900-9999
    month: number;          // 必填，1-12
    value: number;          // 必填，聚合后的最终值
    currency?: string;      // 选填，如 "USD"；省略或等于公司币种则不换算
    unitType?: "CURRENCY" | "PERCENT";   // 选填，默认 "CURRENCY"；PERCENT 不参与币种换算
  }>;
}
```

#### `mappedData` 元素字段详解

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `lgCategory` | string(≤50) | 是 | 必须是 [LG 映射表](#lg-标准科目映射表) 中的 API Code（大小写不敏感）。`UNMAPPED` 或不在 15 类中将被**静默丢弃**，不入冲突表 |
| `year` | int | 是 | 报告年（1900-9999） |
| `month` | int | 是 | 报告月（1-12） |
| `value` | number(BigDecimal) | 是 | 前端已聚合的最终值。CURRENCY 单位传金额数值；PERCENT 单位传小数（如 0.30 表示 30%） |
| `currency` | string | 否 | 该值所代表的币种（如 `USD`）。空值或等于公司当前币种时不换算；不一致时后端按 (P&L→月均 / BS→月末) 汇率换算到公司币种 |
| `unitType` | string | 否 | `CURRENCY`（默认） 或 `PERCENT`；`PERCENT` 不进行币种换算 |

> 💡 **同 `(lgCategory, year, month)` 重复键** 后端会兜底 SUM，但**不建议**前端依赖这一行为 —— 前端应保证每个 key 只出现一次。

#### 请求示例

```json
{
  "mappedData": [
    {
      "lgCategory": "Revenue",
      "year": 2025,
      "month": 9,
      "value": 123000.50,
      "currency": "USD",
      "unitType": "CURRENCY"
    },
    {
      "lgCategory": "Cash",
      "year": 2025,
      "month": 9,
      "value": 500000.00,
      "currency": "USD"
    },
    {
      "lgCategory": "R&D Expenses",
      "year": 2025,
      "month": 9,
      "value": 0.30,
      "unitType": "PERCENT"
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
  data: {
    conflicts: Array<ConflictItem>;
  }
}
```

#### `ConflictItem` 字段详解

| 字段 | 类型 | 说明 |
|---|---|---|
| `conflictId` | string(UUID) | 冲突主键；后续在 resolve 请求的 `resolutions[].conflictId` 中引用 |
| `taskId` | string(UUID) | 任务 ID |
| `lgCategory` | string | LG 标准科目（与映射表 API Code 一致） |
| `dataClassification` | string | 数据分类；本期固定为 `"ACTUALS"` |
| `reportingYear` | number | 报告年 |
| `reportingMonth` | number | 报告月（1-12） |
| `existingValue` | number | LG 现有值（已换算为公司币种）；本期为冲突所以 ≠ null |
| `mappedValue` | number | 本次映射聚合值（已换算为公司币种）。**注：resolve 阶段 OVERWRITE 写入用的是此值**，verify→resolve 期间值不变 |
| `resolution` | string | 初始为 `"PENDING"`；用户解决后变为 `"OVERWRITE"` 或 `"SKIP"` |
| `note` | string | 备注；`PENDING` 时为空串 |
| `resolvedOrder` | number | Save & Next 跳转排序序号（LG 15 类 enum 顺序 × month 升序，从 1 开始） |

> 📌 **响应中只包含真正的冲突项**：LG 为空的指标 / LG 与上传一致的指标都**不出现**在 `conflicts[]` 中（它们会在 resolve 阶段自动处理或忽略）。

#### 响应示例（有冲突）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "conflicts": [
      {
        "conflictId": "8f2e1d0c-9b8a-7654-3210-fedcba987654",
        "taskId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "lgCategory": "Revenue",
        "dataClassification": "ACTUALS",
        "reportingYear": 2025,
        "reportingMonth": 9,
        "existingValue": 100000.0000,
        "mappedValue": 123000.5000,
        "resolution": "PENDING",
        "note": "",
        "resolvedOrder": 1
      },
      {
        "conflictId": "7e1d0c9b-8a76-5432-10fe-dcba98765432",
        "taskId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "lgCategory": "Revenue",
        "dataClassification": "ACTUALS",
        "reportingYear": 2025,
        "reportingMonth": 10,
        "existingValue": 98000.5000,
        "mappedValue": 34.7600,
        "resolution": "PENDING",
        "note": "",
        "resolvedOrder": 2
      }
    ]
  }
}
```

#### 响应示例（无冲突）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "conflicts": []
  }
}
```

> 🟢 **无冲突时**：任务状态自动推进为 `READY_TO_COMMIT`，前端应直接调用接口 ⑦ resolve（body 中 `resolutions` 传空数组 `[]`，`mappedData` 与本次请求一致）触发 fi\_\* 写入。

### 错误响应

| HTTP | 触发条件 | 用户可见消息（message） |
|---|---|---|
| 400 | `taskId` 为空 | `taskId is required` |
| 400 | 任务不存在 | `Task not found: {taskId}` |
| 400 | 任务已逻辑删除 | `Task not found or deleted: {taskId}` |
| 400 | 状态不允许 verify | `Task is not ready for verification (current=DRAFT)` |
| 400 | 请求体缺失 `mappedData` 或为空数组 | `mappedData must not be empty`（由 `@NotEmpty` 校验） |
| 400 | 任意 item 缺 `lgCategory` / `year` / `month` / `value` | `must not be null/blank` |
| 400 | `year` < 1900 或 > 9999 | `must be between 1900 and 9999` |
| 400 | `month` < 1 或 > 12 | `must be between 1 and 12` |

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
   - `year` / `month` 越界
6. **`resolved_order` 计算**：先按 LG 15 类 enum 顺序排序，同 metric 内按 `(year, month)` 升序，从 1 开始顺序填序号。
7. **副作用**：本接口**不修改** `ai_financial_extraction_extracted_data`；cell 级编辑由前端 state 管理。

---

## 接口 ⑦：冲突解决与提交（resolve）

### 基本信息

| 项 | 值 |
|---|---|
| 接口路径 | `POST /api/web/ai/financialExtraction/conflicts/{taskId}/resolve` |
| 调用时机 | 1) 有冲突场景：用户在 Conflict Resolution 页对所有冲突选择 OVERWRITE/SKIP + 填写 note 后点击 **Save** <br/>2) 无冲突场景：verify 返回 `conflicts=[]` 时前端自动调用（`resolutions` 传 `[]`） |
| 幂等性 | **非幂等**：成功后任务进入 `COMPLETED` 终态，重复调用会因状态不允许而失败 |
| 核心职责 | 1) UPDATE `conflict_record` + INSERT `conflict_note`<br/>2) 按 `mappedData` 写入 `finance_manual_data`（新版本行）<br/>3) 写 `commit_audit`（WRITTEN/OVERWRITTEN/SKIPPED 全记录）<br/>4) 推进任务状态到 `COMPLETED` |

> ⚠️ **memory-learn 暂未启用**：本期 resolve 成功后**不**触发 Python 端 mapping memory 学习；后续启用时由后端无痛接入，前端契约不变。

### 请求

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `taskId` | string(UUID) | 是 | 任务 ID |

#### Body 结构

```typescript
{
  mappedData: Array<MappedItem>;           // 必填，与 verify 一致的聚合数据
  resolutions: Array<ResolutionItem>;       // 必填字段（可为空数组 []）
}

type MappedItem = {
  // 字段定义与 verify 的 mappedData 元素完全一致
  lgCategory: string;
  year: number;
  month: number;
  value: number;
  currency?: string;
  unitType?: "CURRENCY" | "PERCENT";
};

type ResolutionItem = {
  conflictId: string;     // 必填，verify 返回的 conflictId
  action: "OVERWRITE" | "SKIP";  // 必填
  note: string;           // 必填，trim 后长度 1-2000
};
```

#### 字段语义

| 字段 | 必填 | 说明 |
|---|---|---|
| `mappedData[]` | **是** | 与 verify 同一份聚合数据；后端用它写入**非冲突指标**（LG 为空时自动写入）。冲突指标的写入值不从这里取，而是从 verify 阶段固化的 `conflict_record.mapped_value` 取，以确保用户决策时看到的值与最终写入一致 |
| `resolutions[]` | 是（可空数组） | 每个 PENDING 冲突必须出现一次；无冲突场景传 `[]` |
| `resolutions[].conflictId` | 是 | 必须属于本 task；重复抛 400 |
| `resolutions[].action` | 是 | `OVERWRITE`（用 verify 时的 mappedValue 覆盖 LG）/ `SKIP`（保留 LG 现值） |
| `resolutions[].note` | 是 | trim 后非空，1-2000 字符 |

#### 请求示例（有冲突）

```json
{
  "mappedData": [
    { "lgCategory": "Revenue", "year": 2025, "month": 9,  "value": 123000.50, "currency": "USD" },
    { "lgCategory": "Revenue", "year": 2025, "month": 10, "value": 98000.50,  "currency": "USD" },
    { "lgCategory": "Cash",    "year": 2025, "month": 9,  "value": 500000.00, "currency": "USD" }
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

```json
{
  "mappedData": [
    { "lgCategory": "Revenue", "year": 2025, "month": 9, "value": 200.00, "currency": "USD" },
    { "lgCategory": "Cash",    "year": 2025, "month": 9, "value": 500000.00, "currency": "USD" }
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
| 400 | `mappedData` 缺失或为空 | `mappedData must not be empty` |
| 400 | `resolutions` 缺失 | `resolutions must not be null` |
| 400 | 某项 `conflictId` 为空 | `conflictId is required for each item` |
| 400 | 某项 `note` 为空或纯空白 | `Please provide a note before saving` |
| 400 | `resolutions` 中 `conflictId` 重复 | `Duplicate conflictId in resolve payload: {id}` |
| 400 | `conflictId` 不属于本 task | `conflictId does not belong to task: {id}` |
| 400 | 存在 PENDING 冲突未在请求中出现 | `Please resolve all conflicts and unmapped accounts before submitting` |
| 400 | `action` 不是 `OVERWRITE`/`SKIP` | `action must be OVERWRITE or SKIP` |
| 400 | `note` 长度 > 2000 | `size must be between 1 and 2000` |

### 业务规则细节

1. **状态机入口**：必须 ∈ `{CONFLICT_RESOLUTION, READY_TO_COMMIT}`。
2. **必须解决所有 PENDING 冲突**：请求 `resolutions[]` 必须包含 `conflict_record` 中所有 `resolution=PENDING` 的项；缺一即整批拒绝。
3. **写入值来源**：
   - **冲突指标**（在 `conflict_record` 中存在）：写入值取自 `conflict_record.mapped_value`（verify 时固化）。即使本次 `mappedData` 中相同 key 的值变了，仍以 verify 时的为准 —— 保证用户决策与最终写入一致。
   - **非冲突指标**（不在 `conflict_record` 中）：写入值取自本次 `mappedData` 中对应 `(lgCategory, year, month)` 的值。
4. **fi\_\* 写入策略**：
   - 取最新 `finance_manual_data WHERE company_id AND date='YYYY-MM-01' AND state IS NULL ORDER BY version_at DESC LIMIT 1` 作为底版
   - 复制所有字段到一个**新行**，分配新 `id`、`version_at=now()`、`state=NULL`、`is_forecast=false`
   - 按 `(lgCategory, year, month)` 写入对应列（覆盖底版的同列值）
   - 旧行因 `version_at` 更早自动变历史版本（PRD §3.5 "被覆盖的数据保留历史版本"）
5. **OVERWRITE / SKIP / WRITTEN 三种 audit 全部留痕**：
   - `WRITTEN` —— LG 本月无数据，本次写入新值（非冲突指标）
   - `OVERWRITTEN` —— LG 有值且与上传不同，用户选 OVERWRITE
   - `SKIPPED` —— LG 有值且与上传不同，用户选 SKIP（保留 LG，fi\_\* 不变但仍留痕）
   - LG 一致（`existing == mapped`） —— **不写 fi\_\*，也不写 audit**
6. **币种换算**：与 verify 一致；同 task 同 (date) 内多次写入合并到一个新版本行。
7. **memory-learn**：暂未启用。代码以 `TODO(memory-learn)` 注释保留，后续启用时由后端取消注释即可，前端契约不变。
8. **`writtenAccounts` 计数语义**：每条 `(lgCategory, year, month)` 写入操作算 1；SKIPPED 不计；一致不计。

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

- [ ] 在前端把当前页 `cellValues[]` 按 `(lgCategory, year-month, ACTUALS)` 聚合，每个 key 唯一
- [ ] 字段优先级：`edit*` 非空用 `edit*`，否则用 `source*`；`editValue` 为 `null` 时回退 `sourceValue`
- [ ] 过滤：`sourceIsMapped=false` / 数据类型非 ACTUALS / `lgCategory` 非 15 类 / `value` 为 null / 月份非法 → 都不传
- [ ] PERCENT 指标的 `unitType` 必须明确填 `"PERCENT"`
- [ ] `currency` 字段统一用大写 ISO 4217 代码（USD/EUR/CNY/...）

### 2. verify 响应处理

- [ ] `conflicts.length === 0` → 跳过 ConflictPage，直接调用 resolve（resolutions=[]）
- [ ] `conflicts.length > 0` → 进入 ConflictPage，按 `resolvedOrder` 顺序展示冲突详情弹窗
- [ ] 每条冲突展示：`lgCategory` + `reportingYear-reportingMonth` + `existingValue` vs `mappedValue` + Radio + Note 输入框
- [ ] Note 输入框校验：trim 后非空，长度 ≤ 2000

### 3. resolve 调用准备

- [ ] `mappedData` 与 verify 时一致（建议复用同一份内存数据）
- [ ] `resolutions[]` 必须为每条 `PENDING` 冲突提供决定，不能跳过；缺一会被后端拒绝整批
- [ ] **无冲突场景**：`resolutions` 传 `[]`（空数组）；`mappedData` 仍要传

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
    { "lgCategory": "Revenue", "year": 2025, "month": 9, "value": 200, "currency": "USD" },
    { "lgCategory": "Cash",    "year": 2025, "month": 9, "value": 500000, "currency": "USD" }
  ]
}
```

响应：

```json
{ "code": 200, "message": "success", "data": { "conflicts": [] } }
```

前端直接调：

```http
POST /api/web/ai/financialExtraction/conflicts/7c9e6679-7425-40de-944b-e07fc1f90ae7/resolve
```

```json
{
  "mappedData": [
    { "lgCategory": "Revenue", "year": 2025, "month": 9, "value": 200, "currency": "USD" },
    { "lgCategory": "Cash",    "year": 2025, "month": 9, "value": 500000, "currency": "USD" }
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
    { "lgCategory": "Revenue", "year": 2025, "month": 9, "value": 123, "currency": "USD" }
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
        "reportingYear": 2025,
        "reportingMonth": 9,
        "existingValue": 100000.0000,
        "mappedValue": 123.0000,
        "resolution": "PENDING",
        "resolvedOrder": 1
      }
    ]
  }
}
```

用户选择 OVERWRITE，填写 note 后提交 resolve：

```json
{
  "mappedData": [
    { "lgCategory": "Revenue", "year": 2025, "month": 9, "value": 123, "currency": "USD" }
  ],
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
    { "lgCategory": "Cash", "year": 2025, "month": 9, "value": 1400, "currency": "EUR" }
  ]
}
```

**方案 2：前端按币种分项，由后端换算**

```json
{
  "mappedData": [
    { "lgCategory": "Cash", "year": 2025, "month": 9, "value": 1000, "currency": "USD" },
    { "lgCategory": "Cash", "year": 2025, "month": 9, "value": 500,  "currency": "EUR" }
  ]
}
```

后端会把 USD 1000 按 `getRateByTargetCurrency("EUR", "USD", "2025-09-01", MONTHLY_LAST_DAY)` 换算成 EUR（假设汇率 0.9 → 900 EUR），与 EUR 500 求和得 1400 EUR；与 LG 的 cash 列（按 EUR 存储）比对。

> 💡 推荐使用**方案 1**，前端控制聚合更明确；方案 2 是兜底能力。

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
