# Fireflies 会议导入（devSupport 测试页）— 开发设计

> 关联文档: [导入文件格式要求](../测试用例/meeting-import-format.md) · [Fireflies 开发设计](./dev-design-doc.md) · [开发步骤](./meeting-import-dev-steps.md)

## 0. 概述

**目的**：测试人员把会议转录文本按[导入文件格式要求](../测试用例/meeting-import-format.md)导入到指定租户，测试识别和提取时不再依赖 Fireflies 接口。

**范围**：只在本地和 test 环境使用，生产上线前封掉（见第 7 节）。

已定口径（2026-11-05）：

- **触发类型复用 `SYNC_NOW`**，`triggeredBy` 记导入的人。Python 不改。
- **生产环境不加开关**，上线前由人工封掉。
- **只导 Fireflies 本来会给的数据**：标题、时间、时长、受邀邮箱、出席显示名、说话人、逐句转录、overview。角色和公司不导入，由识别流程按系统数据推出来。
- **前置数据不在这里建**：本机构邮箱域名、LG 用户与公司、Cheat Sheet 都走系统正常页面准备。
- 导入不能撤销，也不提供删除。

流程：

```
devSupport 导入页
  选租户 → 拖入 .md → 前端解析、预览（报错 / 提醒）→ 确认
        │ POST /api/web/fireflies/meetings/import?organizationId=
        ▼
Java FfSyncServiceImpl.importMeetings
  逐场：导入 DTO → FfGraphqlTranscriptResponse → writeMeeting（与拉取同一套写库）
        → 发 SQS fireflies-meeting-queue（trigger = SYNC_NOW）→ 返回每场的结果
        ▼
Python 正常消费：识别 → 分类 → 提取（不改）
```

## 1. 数据库

不新增表，也不改表。写入与 Fireflies 拉取相同的两张表，各字段的来源如下：

| 表.列 | 来源 |
|---|---|
| `ff_meeting_meta_info.fireflies_id` | `Fireflies ID` |
| `.title` | `# ` 标题（截断到 512，沿用 `toMeeting`） |
| `.started_at` | `Date`，前端换算成 UTC |
| `.duration_minutes` | `Duration` |
| `.participants` | Participants 中 Email 非空的行（`toMeeting` 负责去空白、转小写、去重） |
| `.attendance` | Attended 为 `yes` 的行：`{name, join_time: null, leave_time: null}` |
| `.speakers` | 转录里的说话人，按首次出现的顺序，`id` 从 0 编起 |
| `.overview` | Summary 正文；没有这一节则为 null |
| `.content_hash` / `.dispatched_at` | 与拉取相同 |
| `ff_meeting_sentence.sentence_order` | 行序，从 0 编起 |
| `.speaker_id` / `.speaker_name` | 按说话人名查上面的 `speakers` |
| `.text` | 内容 |
| `.start_time` | 行首时间换算成秒 |
| `.end_time` | 下一句的 `start_time`；最后一句为 null（Python 按开始时间处理） |

## 2. 页面

| 编号 | 页面 | 路由 | 入口 | 访问 |
|---|---|---|---|---|
| PG-D1 | Fireflies Meeting Import | `/devSupport/firefliesImport` | devSupport 左侧导航新增 Fireflies 分组 → Meeting Import | 与其他 devSupport 页相同（菜单树包含 `/devSupport`）；接口另外要求 PGM / SA |

## 3. 接口

### API-D1 导入会议

`POST /api/web/fireflies/meetings/import?organizationId=`。挂在 `FfMeetingController` 上，与 `/{id}` 的 GET 不冲突。

**权限**：

- 调用 `FfAccessSupport.assertPgmOrSuperAdmin()`，组织取 `resolveOrganizationId(organizationId)`，和 Sync now 相同。
- 导入页总会传 `organizationId`。

**请求体** `FfMeetingImportRequest`：

| 字段 | 类型 | 校验 |
|---|---|---|
| `meetings` | 数组 | `@NotEmpty` |
| `meetings[].firefliesId` | string | `@NotBlank`，`[A-Za-z0-9_-]{1,64}` |
| `meetings[].title` | string | `@NotBlank` |
| `meetings[].startedAt` | Instant（ISO 8601） | `@NotNull` |
| `meetings[].durationMinutes` | decimal | `@NotNull`，≥ 0 |
| `meetings[].participants` | string[] | 每项 `@Email` |
| `meetings[].attendance` | string[] | 每项 `@NotBlank` |
| `meetings[].overview` | string | 可空 |
| `meetings[].sentences` | 数组 | 可以为空（测试 Invalid 会议） |
| `meetings[].sentences[].speakerName` | string | `@NotBlank` |
| `meetings[].sentences[].text` | string | `@NotBlank` |
| `meetings[].sentences[].startSeconds` | decimal | `@NotNull`，≥ 0 |

前端已经按导入格式校验过一遍，后端只做上面这些基本校验。校验不过时整个请求返回 422（全局异常处理的口径），这种情况只会在绕过页面直接调接口时出现。

**响应** `List<FfMeetingImportResultResponse>`，与请求的顺序一一对应：

| 字段 | 说明 |
|---|---|
| `firefliesId` | 请求里的 ID |
| `status` | `FfMeetingImportStatusEnum`，取值见下表 |
| `meetingId` | `ff_meeting_meta_info.id`；`SKIPPED`、`FAILED` 为 null |

| status | 条件 |
|---|---|
| `IMPORTED` | 写库成功，SQS 也拿到了消息 id |
| `NOT_DISPATCHED` | 写库成功，SQS 没发出去或 `dispatched_at` 没写上。同一个 ID 原样再导，会整场重写后再发 |
| `SKIPPED` | 本租户已有这个 ID，并且已经投递过，原文不动（`writeMeeting` 返回 null） |
| `FAILED` | 写库抛异常。记 ERROR 日志（带 organizationId、firefliesId），响应里不带异常信息 |

**处理逻辑**：在 `FfSyncServiceImpl` 新增 `importMeetings(organizationId, List<FfMeetingImportDTO>)`，主方法平铺各步：

1. 校验权限、取组织，取当前用户 id 和 traceId；组装 `PullContext(orgId, SYNC_NOW, userId, userId, traceId, null)`。
2. 逐场处理，单场失败不影响后面的会议：
   1. `toTranscript(dto)`：先导出 `speakers`；每句的 `index` 取行序，`speakerId` 按名字查，`endTime` 取下一句的开始时间；`dateString` 取 `startedAt.toString()`。
   2. 调现有的 `writeMeeting(transcript, context)`，拿到 meetingId。返回 null 记 `SKIPPED`，抛异常记 `FAILED`。
   3. 调 `dispatchMeeting(meetingId, context)`：返回 true 记 `IMPORTED`，false 记 `NOT_DISPATCHED`。
3. 写一条 INFO 汇总日志：organizationId、operator，以及各状态的场数。

为了复用投递逻辑，`dispatchMeetings` 里单场的发送和标记要抽成 `boolean dispatchMeeting(String meetingId, PullContext context)`。拉取的批量投递改成循环调用它，行为不变。

**不抢同步占用**（`claim`）。导入的 ID 一般不会和真实拉取的撞上。万一撞了：

- 按同一个 ID upsert：已经投递的跳过，没投递的整场覆盖；
- 只有两边同时首次写入时，`(organization_id, fireflies_id)` 唯一约束才会让后到的一方失败，这时导入结果记为 `FAILED`。

**新增与改动的 Java 文件**（都在 `web/fireflies/` 下）：

- 新增：
  - `interfaces/vo/request/FfMeetingImportRequest`（内嵌 Meeting、Sentence）
  - `interfaces/vo/response/FfMeetingImportResultResponse`
  - `application/dto/meeting/FfMeetingImportDTO`、`FfMeetingImportResultDTO`
  - `domain/enums/FfMeetingImportStatusEnum`
- 改动：
  - `FfMeetingController`：加接口，注入 `FfSyncService`
  - `FfMeetingConverter`：加 Request → DTO、DTO → Response 的映射
  - `FfSyncService` / `FfSyncServiceImpl`

## 4. 页面操作

| 操作 | 位置 | 条件 | 行为 |
|---|---|---|---|
| 选租户 | 顶部 | — | 用 devSupport 的 `OrganizationSelect`（`pages/devSupport/components/DirectorySelect`）。换租户时清空上一次的导入结果，已解析的会议保留 |
| 拖入文件 | 顶部 `Upload.Dragger` | 只收 `.md`，可以多选 | `beforeUpload` 返回 false，不上传。在浏览器里读文本，按第 6 节解析后追加到预览表。同名文件再拖一次，替换这个文件之前解析出的会议 |
| 清空 | 预览表上方 | 有数据时可用 | 清空预览和结果 |
| 移除 | 预览表行内 | — | 去掉这个文件解析出的全部会议 |
| 导入 | 预览表上方 | 已选租户，并且至少有一场没有报错 | 二次确认：「向 <租户名> 导入 N 场会议，导入后会发起 AI 处理，不能撤销」。只提交没有报错的会议；返回后把结果填进对应行；全部成功时提示成功，否则提示各状态的场数。请求进行中按钮显示 loading |

## 5. 页面布局

无原型，参照 devSupport 现有页面的风格（`PageHeader` 加内容卡片）。

```
┌ PageHeader: Fireflies Meeting Import ─────────────────────────────┐
│ 说明一行：格式见 docs/Fireflies 转录接入/测试用例/meeting-import-format.md   │
├───────────────────────────────────────────────────────────────────┤
│ 租户 [OrganizationSelect            ▼]                              │
│ ┌ Upload.Dragger ─────────────────────────────────────────────┐   │
│ │  拖入或点击选择 .md 文件（可多选）                               │   │
│ └─────────────────────────────────────────────────────────────┘   │
│ 共 N 场：可导入 x，报错 y        [清空]  [导入 (x)]                  │
│ ┌ Table ───────────────────────────────────────────────────────┐  │
│ │文件│Fireflies ID│标题│时间(UTC)│受邀/出席│说话人│句数│检查│结果│  │
│ └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

- **检查**：报错用红色列表，提醒用橙色列表，都没有时显示 `OK`。
- **结果**：导入后才有值，显示 已导入 / 未投递 / 已存在 / 失败 的 Tag，并附一句「怎么办」，文案同导入文件格式要求附录 A。
- **空态**：Table 默认的空态。
- **解析不出任何会议的文件**（没有 `# ` 行）：在表里占一行，报错「没有找到会议（缺少 # 标题行）」。

## 6. 前端解析

纯函数 `parseMeetingImport(text, fileName): ParsedMeeting[]`，不依赖 React，可以单独写单测。

**输入的处理**：

- 规则与[导入文件格式要求](../测试用例/meeting-import-format.md)第 2 节一一对应，改格式时两处要同步改。
- 文本先去掉 BOM，统一成 `\n` 换行。

**切分**：

- 按行首 `# `（井号加空格，不含 `##`）切分成会议，第一个 `# ` 之前的内容丢弃。
- 每场会里按行首 `## ` 切节，节名去掉首尾空白后，按 `Participants` / `Summary` / `Transcript` 精确匹配，大小写不敏感。其他节忽略。

**会议信息**：

- 只看标题与第一个 `## ` 之间、形如 `- 键: 值` 的行。键允许带 `**` 加粗。只认 `Fireflies ID`、`Date`、`Duration` 三个键（大小写不敏感），其余的忽略。
- `Date` 按正则 `^\d{4}-\d{2}-\d{2} \d{2}:\d{2} (Z|[+-]\d{2}:\d{2})$` 匹配，换算成 UTC 的 ISO 字符串。月、日、时、分越界算报错；做法是换算后再格式化回去对比，不一致即越界。
- `Duration` 必须是非负数字。

**Participants**：

- 第一行管道表格必须是 `Name | Email | Attended`（大小写不敏感），分隔行跳过。
- 每个单元格去掉首尾空白。Attended 只认 `yes` / `no`，空着视同 `no`。

**Transcript**：

- 以 ```` ``` ```` 开头的行和空行都跳过。
- 其余的行必须匹配 `^\[(\d+:\d{2}(?::\d{2})?)\]\s+(.+?):\s+(.+)$`：
  - 时间两段表示 `m:ss`，三段表示 `h:mm:ss`，秒和分必须小于 60（两段式的分不限）；
  - 说话人去掉首尾空白后不能以 `(` 或 `（` 开头。

**输出**：

- `ParsedMeeting` 包含请求要的字段，外加 `fileName`、`errors: string[]`、`warnings: string[]`。
- 报错和提醒的条目与导入文件格式要求 2.6 节一致。报错信息带行号，方便定位。
- 批内重复的 ID 由页面在汇总全部文件后判断，不在单个文件内判断。

**新增与改动的前端文件**：

- 新增，都在 `src/pages/devSupport/firefliesImport/` 下：
  - `index.tsx`：只做转发，`scripts/check-pages.js` 规定入口只能转发；
  - `FirefliesImportPage.tsx`、`index.less`；
  - `hooks/useMeetingImport.ts`：负责选租户、解析、批内查重、导入并回填结果；
  - `components/MeetingPreviewTable.tsx`；
  - `types.ts`、`constants.ts`；
  - `utils/parseMeetingImport.ts` 及其 `.test.ts`。
- 改动：
  - `config/routes.ts`：在 `/devSupport` 下加路由；
  - `src/pages/devSupport/_shell/DevSupportShell.tsx`：`NAV_GROUPS` 新增 `fireflies` 分组；
  - `src/services/api/fireflies/` 的 `firefliesWebApi.ts`、`request.ts`、`response.ts`、`dto.ts`：加 API-D1 的方法和类型；
  - `src/services/service/fireflies/firefliesService.ts` 及其单测：页面只能经过 Service 层调接口；
  - `src/pages/devSupport/README.md`、`src/services/api/fireflies/README.md`：同步域文档。

页面文案用英文，和 devSupport 其他页保持一致。

## 7. 上线前封掉

要封的有三处，改动都很小：

- 前端 `NAV_GROUPS` 里的 Fireflies 分组；
- `config/routes.ts` 里的 `/devSupport/firefliesImport` 路由；
- Java `FfMeetingController` 里的 API-D1 方法。

具体怎么封，由上线负责人决定。删除这三处，或给接口加环境判断，都可以。

## 8. 测试

**Java**：在 `FfSyncServiceImplTest` 里新增以下用例：

- 新会议：写库并投递，结果为 `IMPORTED`；
- SQS 返回 null：结果为 `NOT_DISPATCHED`；
- 已投递的同一个 ID：结果为 `SKIPPED`，原文不变；
- 写库抛异常：结果为 `FAILED`，后面的会议照常导入；
- 说话人编号、`endTime` 取下一句开始时间、最后一句为 null；
- 非 PGM / SA 调用被拒。

**前端**：`parseMeetingImport.test.ts` 覆盖以下情况：

- 格式要求第 4 节的示例能解析出 4 场会，并且没有报错；
- 格式要求 2.6 节里的每一种报错和提醒；
- 两种时间写法；
- 带 `**` 的键；
- Transcript 有代码块和没有代码块两种写法。

**联调**：

1. 把[导入文件格式要求](../测试用例/meeting-import-format.md)第 4 节的示例存成 `.md`，导入本地的一个测试租户，前置数据要按附录 B 配好；
2. 在 Summary Records 能看到 4 场会，Python 处理到终态；
3. 再导一次，4 场都应为「已存在」。
