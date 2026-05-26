# AI 财务智能解析 —— S3 直传校验接口

> **版本**: v1.0.0 · **更新日期**: 2026-05-26
> **作用范围**: 单接口 `POST /tasks/{taskId}/files/verifyS3`
> **包路径**: `com.gstdev.cioaas.web.ai.financial.extract`
> **关联文档**:
> - 主接口契约: `ai-financial-extract-verify-resolve-api.md`
> - S3 直传流程: 接口 ① `getUploadUrl` + 浏览器 PUT + 接口 ② `uploadComplete`

---

## 用途

在浏览器 S3 直传（接口 ① `getUploadUrl` → 浏览器 PUT）之后、接口 ② `uploadComplete` 之前调用。后端对请求中每个 `fileId` 跑一次 S3 `HeadObject` 探测，前端据此对 **真的没传上去** 的文件提示用户重传或重新申请预签名，避免任务带着缺失对象进入 `UPLOAD_COMPLETE`。

**只读**：本接口不修改 `ai_files` / `files` / S3，反复调用安全。

---

## 流程定位

```
1️⃣ POST /tasks/getUploadUrl                  申请预签名（拿到 uploadUrl / requiredHeaders / fileId）
2️⃣ PUT  {uploadUrl}                          浏览器直传 S3（每个文件一条 PUT）
3️⃣ POST /tasks/{taskId}/files/verifyS3       ← 本接口：批量校验是否真的落盘
4️⃣ POST /tasks/{taskId}/uploadComplete       触发任务进 UPLOAD_COMPLETE 并启动后台解析
```

> 💡 前端拿到本接口结果后，先把 `exists=false` 的文件按 `reason` 提示用户处理；全部 `exists=true` 后再调 ④ `uploadComplete`。

---

## 基本信息

| 项 | 值 |
|---|---|
| 接口路径 | `POST /api/web/ai/financialExtraction/tasks/{taskId}/files/verifyS3` |
| 调用时机 | 浏览器 PUT 全部完成后、`uploadComplete` 之前 |
| 幂等性 | **完全幂等** —— 只读 S3 探测，反复调用结果稳定 |
| 副作用 | 无（不改 DB / 不动 S3） |
| 响应包装 | `{ code, message, data }`；`data` 为 `AiFinancialVerifyS3UploadResponse` |

---

## 请求

### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `taskId` | string(UUID) | 是 | 任务 ID。未找到 / 已软删 → 400 |

### Body 结构

```typescript
{
  fileIds: string[];   // 必填，长度 1-100，每项 ≤ 36 字符
}
```

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `fileIds` | string[] | `@NotEmpty`，最多 100 项 | `files` 表主键列表；后端按请求顺序保序去重（重复 fileId 只校验一次） |
| `fileIds[]` | string(UUID) | `@NotBlank`，≤ 36 字符 | 单个文件 ID |

### 请求示例

```json
{
  "fileIds": [
    "8f2e1d0c-9b8a-7654-3210-fedcba987654",
    "7e1d0c9b-8a76-5432-10fe-dcba98765432",
    "6d0c9b8a-7654-3210-fedc-ba9876543210"
  ]
}
```

---

## 响应

### 成功响应（HTTP 200）

```typescript
{
  code: 200,
  message: "success",
  data: {
    taskId: string;            // path 中传入的 taskId 回显
    allExist: boolean;         // true = 所有 fileId 都通过；前端"是否可调 uploadComplete"的总开关
    missingCount: number;      // items 中 exists=false 的条目数
    items: Array<{
      fileId: string;          // 与请求 fileIds 中一一对应
      objectKey?: string;      // S3 对象逻辑键，exists=false 且 reason!=NOT_IN_TASK 时仍返回（便于排查）
      originalFileName?: string; // 用户原始文件名，便于 UI 弹提示
      exists: boolean;         // 是否真在 S3
      reason: "OK" | "NOT_IN_TASK" | "DELETED" | "FILE_RECORD_MISSING" | "S3_MISSING" | "S3_ERROR";
      size?: number;           // 仅 exists=true 时返回；S3 对象字节数
      etag?: string;           // 仅 exists=true 时返回；S3 返回含引号
      contentType?: string;    // 仅 exists=true 时返回；S3 记录的 MIME
    }>;
  }
}
```

### `reason` 枚举详解

| 值 | 含义 | exists | 前端建议处理 |
|---|---|---|---|
| `OK` | 已落盘 | `true` | 正常 |
| `NOT_IN_TASK` | `fileId` 不属于本 task（也覆盖完全找不到的 fileId，统一吞掉以防信息泄漏） | `false` | 提示「文件无效」；通常是前端串号 bug，需排查 |
| `DELETED` | `ai_files` 行已软删 | `false` | 提示文件已删除；不要再用此 fileId |
| `FILE_RECORD_MISSING` | `ai_files` 存在但 `files` 主表缺记录 | `false` | 数据治理异常；提示「上传失败请重试」并打点上报 |
| `S3_MISSING` | DB 行齐全但 S3 `HEAD` 返回 404 | `false` | **直传失败**：提示用户重传，或重新调 `getUploadUrl` 拿新签名 |
| `S3_ERROR` | S3 返回 401 / 403 / 5xx 等非 404 错误（鉴权 / 网络 / 服务端） | `false` | 基础设施问题；提示「网络繁忙稍后重试」，可让用户重试本接口而非重传 |

### 响应示例（全部成功）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "taskId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "allExist": true,
    "missingCount": 0,
    "items": [
      {
        "fileId": "8f2e1d0c-9b8a-7654-3210-fedcba987654",
        "objectKey": "ai/7c9e6679-.../8f2e1d0c-..._report.xlsx",
        "originalFileName": "Q3-Financial-Report.xlsx",
        "exists": true,
        "reason": "OK",
        "size": 245678,
        "etag": "\"d41d8cd98f00b204e9800998ecf8427e\"",
        "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      },
      {
        "fileId": "7e1d0c9b-8a76-5432-10fe-dcba98765432",
        "objectKey": "ai/7c9e6679-.../7e1d0c9b-..._supplement.pdf",
        "originalFileName": "Supplement.pdf",
        "exists": true,
        "reason": "OK",
        "size": 89234,
        "etag": "\"e3b0c44298fc1c149afbf4c8996fb924\"",
        "contentType": "application/pdf"
      }
    ]
  }
}
```

### 响应示例（部分缺失）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "taskId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "allExist": false,
    "missingCount": 2,
    "items": [
      {
        "fileId": "8f2e1d0c-9b8a-7654-3210-fedcba987654",
        "objectKey": "ai/7c9e6679-.../8f2e1d0c-..._report.xlsx",
        "originalFileName": "Q3-Financial-Report.xlsx",
        "exists": true,
        "reason": "OK",
        "size": 245678,
        "etag": "\"d41d8cd98f00b204e9800998ecf8427e\"",
        "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      },
      {
        "fileId": "7e1d0c9b-8a76-5432-10fe-dcba98765432",
        "objectKey": "ai/7c9e6679-.../7e1d0c9b-..._supplement.pdf",
        "originalFileName": "Supplement.pdf",
        "exists": false,
        "reason": "S3_MISSING"
      },
      {
        "fileId": "6d0c9b8a-7654-3210-fedc-ba9876543210",
        "exists": false,
        "reason": "NOT_IN_TASK"
      }
    ]
  }
}
```

---

## 错误响应

| HTTP | 触发条件 | message |
|---|---|---|
| 400 | `taskId` 为空 / 空白 | `taskId is required` |
| 400 | 任务不存在 | `Task not found: {taskId}` |
| 400 | 任务已逻辑删除 | `Task not found or deleted: {taskId}` |
| 400 | 请求体缺 `fileIds` 或为空数组 | Bean Validation 报错 `must not be empty` |
| 400 | `fileIds` 长度 > 100 | `size must be between 0 and 100` |
| 400 | 单个 fileId 为空字符串 | `must not be blank` |
| 400 | 单个 fileId 长度 > 36 | `size must be between 0 and 36` |
| 400 | 请求体中 `fileIds` 全为空白字符串 | `fileIds is required` |

> ✅ 单条 S3 探测失败（`S3_ERROR`）**不会**让整批 400 —— 错误信息进入对应 `items[].reason`，整体仍 200。

---

## 业务规则细节

1. **保序去重**：响应 `items` 顺序与请求 `fileIds` 一致；同一 fileId 在请求中重复出现，只校验一次（首次出现的位置）。
2. **归属校验**：fileId 必须属于本 `taskId`。否则 `reason=NOT_IN_TASK` 而不暴露「文件存在但属其它 task」的信息，避免横向越权窥探。
3. **完全找不到的 fileId 也归 `NOT_IN_TASK`**：和「属于其它 task」的响应一致，避免通过差异判断 fileId 是否存在于系统。
4. **软删行不去探 S3**：`ai_files.deleted=true` 直接返回 `reason=DELETED`，节省一次 S3 调用。
5. **数据治理异常**：`ai_files` 行存在但 `files` 主表缺对应行（极少见，通常是事务半成品）→ `reason=FILE_RECORD_MISSING`；服务端会打 WARN 日志。
6. **HEAD 操作并发**：当前实现为串行循环 + 单次 SQL 批量预取 `ai_files`/`files`；S3 探测 N 个文件最坏耗时 ≈ N × HEAD 单次延迟（通常 < 50ms / 个）。100 文件预计 < 5s。
7. **S3 鉴权 / 网络异常**：单条 fileId 探测异常仅记到对应 item（`reason=S3_ERROR`）+ WARN 日志，**不**影响同批次其它 fileId 的探测，整体仍 HTTP 200。

---

## 前端联调清单

### 1. 调用前置条件
- [ ] 浏览器对全部预签名 URL 完成 PUT（不必全部成功 —— 部分失败也可调本接口确认到底哪些没传上去）
- [ ] 收集本批次所有 fileId（来自 `getUploadUrl` 响应中的 `items[].fileId`）

### 2. 响应处理建议

```ts
const res = await verifyS3Uploads(taskId, { fileIds });
if (res.data.allExist) {
  // 全部就绪 → 直接进入 uploadComplete
  await uploadComplete(taskId, fileIds);
} else {
  // 按 reason 分组提示
  const retryable = res.data.items.filter(i => i.reason === 'S3_MISSING');     // 重传
  const infra = res.data.items.filter(i => i.reason === 'S3_ERROR');           // 重试本接口
  const broken = res.data.items.filter(i =>
    ['NOT_IN_TASK', 'DELETED', 'FILE_RECORD_MISSING'].includes(i.reason));     // 数据问题
  // ...弹窗提示，列出 originalFileName
}
```

### 3. 错误恢复路径

| 场景 | 用户操作 | 前端动作 |
|---|---|---|
| `S3_MISSING` | 重传单个文件 | 调 `getUploadUrl` 拿新签名 → 浏览器 PUT → 再次调本接口 |
| `S3_ERROR` | 用户点重试 | 直接再调本接口（不必重传，等基础设施恢复） |
| `DELETED` / `FILE_RECORD_MISSING` | 提示「文件失效，请重新上传」 | 把该 fileId 从本地列表删除，引导用户重新上传 |
| `NOT_IN_TASK` | 排查代码 | 通常是 fileId 串号 bug；上报埋点 |

### 4. UX 建议

- [ ] 进度条 / 全屏 loading 标记本接口为「正在确认上传结果...」
- [ ] 失败列表用文件名（`originalFileName`）+ 状态（`reason`）的卡片列表
- [ ] 重传后**只对失败的 fileId** 重跑流程，不要重新上传成功的文件
- [ ] `S3_ERROR` 给两个按钮：「重试探测」（再调本接口）和「联系客服」

---

## 与其它接口的关系

| 接口 | 是否互相依赖 | 说明 |
|---|---|---|
| `POST /tasks/getUploadUrl` | 强依赖 | 必须先拿到 fileId 才能 verify |
| 浏览器 PUT S3 | 强依赖 | verify 验的就是 PUT 是否落盘 |
| `POST /tasks/{taskId}/uploadComplete` | 推荐前置 | 没 verify 也能 uploadComplete，但风险是任务带着缺失对象进入后台解析；建议必先 verify |
| `POST /tasks/{taskId}/batchDelete` | 弱关联 | 已 verify 通过的文件还可被 batchDelete |
| `POST /tasks/{taskId}/file/replace` | 弱关联 | 也是另一条修复路径（用新 fileId 替换旧的） |

---

## 性能与配额

- 单次请求 fileId 上限 100（Bean Validation `@Size(max=100)`）
- S3 HEAD 单次延迟约 30-80ms（跨区域可能更高）
- 后端用一次 SQL `findAllById` 批量预取 `ai_files` 和 `files`，避免 N+1
- 不缓存结果 —— 每次调用都重新探测，保证强一致

---

## 附录：参数枚举速查表

### 请求 `fileIds[]`
- 类型：`string[]`
- 限制：1 ≤ length ≤ 100，每项 1 ≤ char ≤ 36

### 响应 `items[].reason`
- `OK` — 校验通过
- `NOT_IN_TASK` — fileId 不属于本 task 或不存在
- `DELETED` — ai_files 已软删
- `FILE_RECORD_MISSING` — files 主记录缺失
- `S3_MISSING` — S3 对象不存在（HEAD 404）
- `S3_ERROR` — S3 返回非 404 错误（401/403/5xx 等）

### 响应顶层字段
- `taskId`: string — path 回显
- `allExist`: boolean — 全部 OK
- `missingCount`: number — 缺失数量
- `items`: array — 每个 fileId 一行（保序去重）

---

**更新历史**

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-05-26 | v1.0.0 | 初版：接口契约 + 6 种 reason 枚举 + 前端联调清单 |
