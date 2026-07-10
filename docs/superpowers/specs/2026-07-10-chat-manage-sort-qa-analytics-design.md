> 关联文档: [devSupport 目录查询接口设计](./2026-07-03-devsupport-directory-options-design.md)、[Dev Support 权限门控设计](./2026-06-15-dev-support-permission-gating-design.md)、[AI Chatbot 设计](../../AI-Chatbot/设计/design-doc.md)、[LLM Analytics 扩展（已陈旧，布局范式参照）](./2026-05-29-llm-analytics-expansion-design.md)

# Chat Management 排序/时区 + 问答列表页 + 数据分析页 — 设计文档

**日期**: 2026-07-10
**范围**: CIOaas-python（chatbot manage 接口扩展 + V004 迁移）+ CIOaas-web（chatManage 增强 + 2 个新页面）；Java 零改动
**一句话**: chatManage 列表补时间排序与时区显示；新增 `/devSupport/chatMessages` 按人浏览问答对；新增 `/devSupport/chatAnalytics` 按 人/公司/组织/端类型/时间区间 做使用分析——公司/组织/端类型维度**经会话表两步圈定**（thread 本就持有这三列，消息表不加冗余列），配一次纯索引迁移（V004）。

> **修订记录（2026-07-10 test 环境冒烟反馈，已实施）**：
> 1. 三页端类型筛选改**多选**（company/admin 仅两值，前端归导：恰选 1 个→发该值，选 0/2 个→不发；后端单值等值过滤不变）；
> 2. 问答页前端路径改全称：`/devSupport/chatQa` → **`/devSupport/chatMessages`**（目录同名改，后端 `/manage/qa` 接口路径不动，NAV label 仍 Chat Q&A）；
> 3. 问答页由卡片流改为 **antd Table + 展开行**：默认收起、点击行展开显示答案；列=问题/创建时间/端类型/用户/公司/组织/答案数+状态/Open thread；分页走 Table 受控服务端分页；
> 4. 问答页筛选**级联** + 顺序调整（端类型 → 公司 → 组织 → **用户**）：新增 `GET /manage/filter-options`（§4.4），端类型圈公司/组织候选、公司/组织圈用户候选（distinct 自会话表实际数据，不过滤软删）；
> 5. chatManage 时间语义确认：Created=会话创建时间（thread.created_at）、Last Active=该会话最后一条消息时间（thread.last_message_at，append 时 touch）；
> 6. analytics **byUser 去 Top 20 改全量** + 每用户带归属维度（clientType/companyId/organizationId，取该用户范围内 last_message_at 最新会话的维度值，去掉恒为 1 的 activeUserCount）；前端 Users 表加客户端分页与归属列，行点击跳 `/devSupport/chatMessages?userId=`。

> **修订记录（2026-07-10 二次冒烟，多选+级联，已确认三个 chat 页全上）**：
> 7. **四个维度筛选（client_type / organization / company / user）全部改多选 + 级联**，应用到 chatManage / chatMessages / chatAnalytics 三页：
>    - **传参 = 逗号拼接 CSV**（`companyId=a,b,c`；UUID 不含逗号，规避数组序列化坑）。后端 `/manage/qa`、`/manage/threads`、`/manage/analytics`、`/manage/filter-options` 的这四个参数保持 `str | None`，按 CSV split 成列表做 **IN 查询**（空/缺省=不过滤）；前端发送 `ids.join(',') || undefined`。
>    - **级联候选支持多上游**：filter-options 的 companies/organizations 按 client_types(IN) 收窄、users 按 client_types+company_ids+organization_ids(IN) 收窄。
>    - **`isOrgFilterDisabled` 改数组判定**：选中客户端恰为 `[company/app]` 时禁用组织（规则不变）。client_type 归导从「恰选 1 个」改为「发选中数组 CSV，空则不发」。
>    - **前端**：chatMessages 的级联 Select 改 `mode="multiple"`；chatManage/chatAnalytics 从单选 `DirectorySelect` 换成 filter-options 级联多选下拉；`useManageFilterOptions` + `toFilterSelectOptions` 提升到 `_shared/` 三页复用。多选下拉高度随 tag 自适应（`FilterField` 已加 `min-height`）。
>    - 下游失效自动清空逻辑（上游变→下游选中项不在新候选里则剔除）对数组逐项过滤。

---

## 1. 背景与目标

管理页 `https://admin-test.lgpi.io/devSupport/chatManage` 现状三块缺口：

1. **排序**：表格所有列无 `sorter`，接口无排序参数，顺序被后端硬编码为 `last_message_at DESC`（`chat_thread_repository.py:112`）——管理员无法按创建时间等重新排序。
2. **时区**：全部时间字段是后端 `"yyyy-MM-dd HH:mm:ss"`（UTC）字符串**原样直显**（`chatManage/index.tsx:192`、`ThreadDetailDrawer.tsx:118-119,161`），用户看到的是 UTC 而非本地时间，且无任何时区标注。
3. **只有会话粒度**：想看"某个人问了什么、AI 答了什么"必须逐个点开会话抽屉；也没有任何按 人/公司/组织/端类型/时间区间 的使用分析视图（现有 `/manage/stats` 无任何筛选维度，窗口 7d/14d 是常量）。

**目标**：
- ① chatManage 列表支持时间字段服务端排序；全站 devSupport 统一"本地时间 + 时区标注"显示；
- ② 新页面 **Chat Q&A**（`/devSupport/chatQa`）：跨会话按人（可叠加公司/组织/端类型/时间/关键字）分页浏览"问题 → 答案"对；
- ③ 新页面 **Chat Analytics**（`/devSupport/chatAnalytics`）：按 用户/公司/组织/端类型/时间区间 筛选的使用分析仪表盘，并给出可分析维度全景（§6）。

**非目标**：不做用户侧（客户端）任何改动；不动 SSE 对话链路；不做导出/订阅报表；P2 埋点项（§6.2）本期不实现只立项。

---

## 2. 现状调研结论（速览）

| 事实 | 出处 |
|---|---|
| `GET /api/ai/chat/manage/threads` 入参只有 page/pageSize/clientType/companyId/userId/organizationId/keyword/dateFrom/dateTo，**无排序参数**；排序硬编码仓储层 | `chatbot/interfaces/routes.py:180-214`、`chat_thread_repository.py:110-115` |
| `ai_chatbot_thread` 五个分析维度列齐全（user_id/company_id/organization_id/client_type/created_at·last_message_at）；索引仅 `(user_id, last_message_at DESC) WHERE deleted=FALSE` | `chat_thread_model.py`、V001 `:31-49` |
| `ai_chatbot_message` **没有 company_id/organization_id/client_type**；`user_id` 仅 user 角色有值（assistant 为 NULL）；索引仅 `(thread_id, seq)` + trace 部分索引，**user_id/parent_message_id/created_at 均无索引** | `chat_message_model.py`、V001 `:52-72` |
| 问答配对手段：assistant 显式挂本轮 user 消息（`parent_message_id`）；同轮 user+assistant 共享 `trace_id`（历史存量可能 NULL） | `chat_history_service.py:231-232`、`chat_message_repository.py:67` |
| 仓储约定**单表禁 JOIN**，跨表组装在 service（两仓储文件头 §1.4） | `domain/repository/*.py` |
| 前端时间显示三种并存，唯一正确的 UTC→本地工具在 tracing 域：`formatUtcToLocal`（moment.utc→local，带单测） | `tracing/utils/time.ts:18-27` |
| 仪表盘全套可抄模式在 llm 域：AnalyticsFilterBar + kpiCard + `_shared/ChartCard`(echarts) + chartOptions.ts 工厂 + `useAnalyticsFilters`（近 7 天默认） | `devSupport/llm/Dashboard.tsx`、`llm/hooks/`、`_shared/chartTheme.ts` |
| 人/公司/组织筛选与 ID→名称已有共享件：`_shared/DirectorySelect`（CompanySelect/UserSelect/OrganizationSelect）+ `useDirectoryNames` + `IdNameCell` | `_shared/DirectorySelect/` |
| 服务端排序的前端受控写法先例：`sorter: true` + `sortOrder` 受控 + `Table.onChange` 取 `sorter.field` | `rag/components/SpaceChunksTable.tsx:80-131` |
| 新增 devSupport 页面 = 3 处：页面目录（必须 `xxx/index.tsx`，check-routes R2）+ `config/routes.ts` 子路由 + `DevSupportShell.tsx` NAV_GROUPS；无 access/locale 改动 | `config/routes.ts:586-773`、`_shell/DevSupportShell.tsx:77-289` |
| `/manage/*` 后端**登录即可**（仅 `get_current_user`，无管理端闸门），"仅管理端"目前靠前端菜单权限 + 语义约定 | `routes.py:167,181,219`、`common/auth/identity.py:34-60` |
| token/成本/耗时不在 chatbot 表：经 `message.trace_id ══ ai_trace.id ══ ai_llm_call_log.trace_id` 关联；**chat 调用 `ref_company_id` 恒 NULL**（TraceContext 不带 company），llm `/stats` 的 byCompany 对 chatbot 失真 | V001 llm/tracing 段、`ai/agent/chatbot_graph/` 各节点 |

---

## 3. 功能一：chatManage 排序 + 时区显示

### 3.1 后端：threads 列表加排序参数

`GET /api/ai/chat/manage/threads` 新增两个 Query（缺省行为不变，向后兼容）：

| 参数 | 别名 | 取值 | 缺省 |
|---|---|---|---|
| `sort_by` | `sortBy` | **白名单**：`lastMessageAt` \| `createdAt` | `lastMessageAt` |
| `sort_order` | `sortOrder` | `asc` \| `desc` | `desc` |

- 白名单在仓储层映射到列（`{"lastMessageAt": ChatThread.last_message_at, "createdAt": ChatThread.created_at}`），禁止透传任意列名；非法值 422。
- **不支持按 `messageCount` 排序**：messageCount 是"当页后算"（`chat_manage_service.py:37-38`），排序需跨表聚合，与仓储禁 JOIN 冲突；若未来确有需求，走 thread 冗余 `message_count` 列另行设计（YAGNI，本期不做）。
- 改动文件：`interfaces/routes.py`（两个 Query）→ `application/dto/chat_manage_dto.py`（`ThreadManageFilters` 加 `sort_by/sort_order`）→ `domain/repository/chat_thread_repository.py`（`find_page` 白名单映射）。service 零改动。
- 索引：管理列表不带 user_id 前缀时现有索引对排序无用，现状本就是全扫+排序；表规模（内部管理工具）可接受。V004 顺手补两个部分索引 `(last_message_at DESC) WHERE deleted=FALSE`、`(created_at DESC) WHERE deleted=FALSE`（§7，可选项，成本极低）。

### 3.2 前端：列排序（服务端）

- `Last Active` 列加 `sorter: true`，并**新增 `Created` 列**（`createdAt`，同宽 170）也挂 `sorter: true`；两列 `sortOrder` 受控点亮（仿 `SpaceChunksTable.tsx:80-131`），`Table.onChange` 取 `sorter.field/order` 写入 state，任何排序变更 `setPage(1)`。
- `ListManageThreadsRequest`（`chatManageApi.ts:12-23`）加 `sortBy?/sortOrder?`；`_cleanParams` 惯例已剔除空值，camelCase 原样发（chat 域契约）。
- 默认态与现状一致：`lastMessageAt` 降序。

### 3.3 时区显示（全 devSupport 复用）

**新增共享工具 `src/pages/devSupport/_shared/time.ts`**（内容取自 `tracing/utils/time.ts` 的 `formatUtcToLocal`/`parseUtcMs`，连同单测一并新增；tracing 域原文件本期不动，P2 收敛为 re-export）：

- `formatUtcToLocal(utcStr)` → 本地 `YYYY-MM-DD HH:mm:ss`（moment.utc 严格解析 + ISO8601 回退）；
- 新增 `localTzLabel()` → `"UTC+08:00 · Asia/Shanghai"`（`moment().format('Z')` + `moment.tz.guess()`；`moment-timezone ^0.5.32` 已在依赖，`package.json:79`）。

**chatManage 接入点**：

| 位置 | 改动 |
|---|---|
| 列表 `Last Active` / 新增 `Created` 列 | render = `formatUtcToLocal(v)`，`Tooltip` 显示原始 UTC 值（`{v} UTC`） |
| 抽屉 `Created` / `Last Active` / 每条消息右侧时间 | 同上 |
| 页面标题栏 | Refresh 按钮旁加灰色 Tag：`localTzLabel()`——一处标注全页时区，不在每个单元格重复后缀 |
| `RangePicker` 筛选 | 占位/后缀标注 `(UTC)`——后端 dateFrom/dateTo 契约是 **UTC 自然日含边界**（`chatManageApi.ts:20-22`），本期不改语义，只把口径标示出来（本地日≠UTC 日的错位是已知偏差，管理工具可接受；如需精确改 datetime 参数另行评估） |

新页面（§4、§5）时间显示一律用同一工具，同一"页面级时区 Tag + 单元格本地时间 + Tooltip UTC"范式。

---

## 4. 功能二：问答列表页 Chat Q&A（`/devSupport/chatMessages`，见修订记录 2/3/4）

### 4.1 页面定位

跨会话、以**问答轮**为粒度的浏览页：选一个人（或不选、看全量）→ 按时间倒序翻阅"问题 → 答案"对。定位是**内容审阅**（人问了什么、AI 答得如何），与 chatManage 的会话生命周期管理互补。

### 4.2 后端接口 `GET /api/ai/chat/manage/qa`

**入参**（全 Query，风格对齐现有 manage）：

| 参数 | 别名 | 说明 |
|---|---|---|
| `page` / `page_size`(`pageSize`) | | 分页，pageSize 1~50 默认 20（内容体较大，上限收紧到 50） |
| `user_id`(`userId`) | | 提问人过滤（可选——不传即全量问答流；直接命中 `message.user_id`） |
| `company_id`(`companyId`) / `organization_id`(`organizationId`) / `client_type`(`clientType`) | | 经会话维度圈定：thread 表本就持有这三列，先查 thread_ids 再过滤消息（见下编排） |
| `keyword` | | 问题正文 ILIKE（通配符转义同 threads 现状；content 无索引，管理工具全扫可接受，量大再议 trigram） |
| `date_from`(`dateFrom`) / `date_to`(`dateTo`) | | 提问时间 `created_at` 的 UTC 自然日含边界（语义同 threads，但作用列不同，DTO 内独立命名） |

**查询编排**（`chat_manage_service.manage_list_qa`，不破单表仓储约定，两步走 thread→message）：

1. **仅当带 company/organization/clientType 过滤时**：thread 仓储 `find_ids_by_filters(filters)` 只取 thread_id 列圈定范围（复用 `_apply_manage_filters` 条件组装）；
2. message 仓储：`WHERE role='user' [+ user_id/keyword/时间] [+ thread_id = ANY(ids)] ORDER BY created_at DESC` 分页取问题页 + count（新方法 `find_user_questions_page` / `count_user_questions`）；
3. message 仓储：`find_by_parent_ids(parent_ids)` 一次 IN 拉全部 assistant 子回答（**配对优先 `parent_message_id`**；对 parent 未命中的历史存量，同 `trace_id` 兜底 `find_by_trace_ids`；两者皆无则孤儿问题、answers 为空）；
4. thread 仓储：`find_by_ids(thread_ids)` 一次 IN 补会话标题/维度列/软删标记（item 的 companyId/organizationId/clientType 就来自这里，消息表不存）。

thread_ids 圈定用 `= ANY(array)` 传参；管理工具的量级（内部会话表）IN 列表可控，无需冗余列。

**返回**（`{ total, items[] }`，每项一轮）：

```jsonc
{
  "questionId": "...", "question": "...",              // user 消息全文（管理工具，不做服务端截断，前端折叠）
  "askedAt": "yyyy-MM-dd HH:mm:ss",                    // UTC，前端转本地
  "userId": "...", "companyId": null, "organizationId": "...", "clientType": "admin",
  "threadId": "...", "threadTitle": "...", "threadDeleted": false,
  "traceId": "...",
  "answers": [                                           // 同一问题多答 = 重新生成分支，按 created_at 升序全返
    { "messageId": "...", "content": "...", "status": "success",
      "createdAt": "...", "usedTools": ["get_financials"], "attribution": ["source:financial"] }
  ]
}
```

**口径**：消息无删除概念，**软删会话的问答默认包含**（与现状 `message_total` 口径一致），`threadDeleted=true` 由前端标注灰 Tag；多答全返、前端默认展示最新一条并可展开历史（重新生成审阅是管理场景的价值点，不丢信息）。

改动文件：`chat_message_repository.py`（3 个新查询）+ `chat_thread_repository.py`（`find_by_ids`）+ `chat_manage_service.py`（编排 + span）+ `chat_manage_dto.py`（`QaFilters`/`QaItem`）+ `interfaces/vo/response.py` + `interfaces/routes.py`。

### 4.3 前端页面 `src/pages/devSupport/chatQa/`

- **筛选栏**（复用 chatManage 全套控件）：`UserSelect` + `CompanySelect` + `OrganizationSelect` + 端类型 Select + 问题关键字 `Input.Search`（非受控 + resetNonce 重挂载）+ `RangePicker`（标注 UTC）+ Reset/Refresh + 时区 Tag。
- **列表体**：不用表格，用**问答卡片流**（分页仍服务端 page/pageSize，antd `List` 或 div 流）：
  - 卡片头：提问时间（本地）· `IdNameCell`(userId) · clientType Tag · company/organization `IdNameCell` · threadTitle（软删标灰 `(deleted)`）；
  - 问题区：user 消息纯文本（`pre-wrap`，超 4 行折叠展开）；
  - 答案区：最新 assistant 消息 `_shared/MarkdownView` 渲染（页面级 `MarkdownViewToggle` 统一 rendered/source/split，抄 ThreadDetailDrawer 受控用法）；status≠success 标 Tag（partial 金 / failed 红）；`usedTools`/`attribution` Tag 行；多答时显示 `regenerated ×N` Tag，点击切换历史答案；
  - 卡片操作：`Open thread` —— 用返回字段构造最小 thread 对象直接复用 **`ThreadDetailDrawer`**（组件已按 props 传对象工作，无需新接口）。
- **services**：`api/chat/chatManageApi.ts` 加 `listManageQa` + Request/Response（同文件同域，不新开文件）；`chatManageService.ts` 加 `fetchManageQa` 解信封转 DTO；DTO 进 `chatManageDto.ts`。
- **注册 3 处**：`config/routes.ts`（`{ path: '/devSupport/chatQa', name: 'AI Chat Q&A', hideInMenu: true, component: './devSupport/chatQa' }`）+ `DevSupportShell.tsx` NAV_GROUPS `AI Chatbot` 分组加 `Chat Q&A`（`matchPrefix: '/devSupport/chatQa'`，比 `/devSupport/chat` 长自然不抢选中态）+ 页面目录 `chatQa/index.tsx`。

---

### 4.4 级联筛选端点 `GET /api/ai/chat/manage/filter-options`（修订记录 4）

问答页筛选候选值取自会话表**实际数据**（distinct，单表，不过滤软删——与 QA 口径一致），实现"端类型→圈公司/组织、公司/组织→圈用户"的级联：

- 入参（全可选，alias camelCase）：`client_type(clientType)`、`company_id(companyId)`、`organization_id(organizationId)`；
- 返回 `{ companies: [id...], organizations: [id...], users: [id...] }`——companies/organizations 按 client_type 过滤，users 按三者过滤；顺序不保证，前端经 `useDirectoryNames` 解析名称后按名称排序；
- 上游选择变化后，若下游当前选中值不在新候选内，前端自动清空该下游选择。

## 5. 功能三：数据分析页 Chat Analytics（`/devSupport/chatAnalytics`）

### 5.1 后端接口 `GET /api/ai/chat/manage/analytics`

**一个端点吃下整页**（llm `/stats` 先例：KPI+图表+分组同接口，前端多视图复用）。

**入参**：`user_id(userId)` / `company_id(companyId)` / `organization_id(organizationId)` / `client_type(clientType)` / `date_from(dateFrom)` / `date_to(dateTo)`（UTC 自然日含边界，**缺省近 30 天**）/ `interval`（`day` 默认 \| `hour`）。

**返回**（camelCase，NULL 维度归 `"(unknown)"` 哨兵，llm 先例）：

```jsonc
{
  "overview": {
    "threadCount": 0,            // 区间内新建会话数（thread.created_at，排软删）
    "activeThreadCount": 0,      // 区间内活跃会话数（thread.last_message_at 落区间）
    "turnCount": 0,              // 问答轮次 = user 消息数（message.role='user'）
    "messageCount": 0,           // 全部消息数
    "activeUserCount": 0,        // distinct 提问人（message.user_id）
    "avgTurnsPerThread": 0,      // turnCount / activeThreadCount
    "answerSuccessRate": 0.98,   // assistant status='success' 占比
    "partialCount": 0, "failedCount": 0,   // 打断 / 失败的 assistant 消息数
    "forkThreadCount": 0,        // 区间内新建且 parent_thread_id 非空
    "regenCount": 0              // 同一 user 消息下第 2+ 个 assistant 子（重新生成次数）
  },
  "timeSeries": [ { "bucket": "2026-07-01", "turnCount": 0, "messageCount": 0,
                    "newThreadCount": 0, "activeUserCount": 0 } ],
  "byClientType":   [ { "key": "company", "threadCount": 0, "turnCount": 0, "activeUserCount": 0 } ],
  "byCompany":      [ /* 同构，turnCount 降序 Top 20 */ ],
  "byOrganization": [ /* 同构，Top 20 */ ],
  "byUser":         [ // 修订记录 6：全量（无 Top 20）、独立结构、带归属维度（取该用户范围内 last_message_at 最新会话的维度值）
                      { "key": "user-id", "clientType": "company", "companyId": null,
                        "organizationId": null, "threadCount": 0, "turnCount": 0 } ],
  "byTool":         [ { "key": "get_financials", "turnCount": 0 } ],   // used_tools JSONB unnest
  "byAnswerStatus": [ { "key": "success", "count": 0 } ]
}
```

**实现要点**：

- 会话类指标 = `ai_chatbot_thread` 单表 GROUP BY（五个维度列全在 thread 上）；
- 消息/轮次/工具/状态类指标 = **两步单表 + service 内存映射**（消息表不加冗余列，维度经会话取）：message 仓储按 时间/user 过滤后 `GROUP BY thread_id` 单表聚合 → thread 仓储 `find_by_ids` 拿这批 thread 的 company/organization/client_type → service 内存按维度二次聚合出 byCompany/byOrganization/byClientType（byUser 直接用 `message.user_id`，不经 thread）；带公司/组织/端**过滤**时同 §4.2 先 `find_ids_by_filters` 圈定再聚合。全部单表查询，不违禁 JOIN；
- `regenCount` = `GROUP BY parent_message_id HAVING count>1` 于 assistant 行（V004 的 parent 部分索引支撑）；
- `byTool` 用 `jsonb_array_elements_text(used_tools)`（SQLAlchemy `func` 表达式，仍单表）；
- 统计口径沿用现状混合口径并**在响应里显式化**：thread 排软删、message 不排；
- P1 扩展（不阻塞 P0）：overview 追加 `totalTokens / totalCostUsd / avgDurationMs / p95DurationMs`——chatbot service **进程内直调** tracing/llm 查询服务（先例：`knowledge_base_tool` 直调 rag `search_service`），按 `ai_trace.name='chatbot.chat'` + company/organization/时间过滤聚合 `duration_ms`，经 trace_id 聚合 `ai_llm_call_log` 的 usage/cost。注意 **chat 调用 `ref_company_id` 恒 NULL**，公司维度必须走 trace join 口径，不能用 llm `/stats` 的 byCompany（失真）；根治项见 §6.2（TraceContext 补 company_id）。

改动文件：两仓储（aggregate 方法）+ `chat_manage_service.py`（`manage_analytics` 编排）+ `chat_manage_dto.py` + `vo/response.py` + `routes.py`。

### 5.2 前端页面 `src/pages/devSupport/chatAnalytics/`

整页照抄 llm Dashboard 骨架（`llm/Dashboard.tsx` + `useAnalyticsFilters` + `useLlmDashboard` 模式）：

- **筛选条**：端类型 Select（`__ALL__` 哨兵）+ `UserSelect`/`CompanySelect`/`OrganizationSelect` + `RangePicker`（缺省近 30 天，标注 UTC）+ interval Select（day/hour）+ Refresh/Reset + 时区 Tag；filters 整体 `useMemo` 作数据 hook 依赖，hook 带 cancelled flag + refreshTick（`useLlmDashboard.ts:24-50` 模板）。
- **KPI 行**（div kpiCard 风格，非 antd Statistic）：会话数 / 轮次 / 活跃用户 / 平均轮次每会话 / 回答成功率（阈值语义色：<95% kpiWarning、<90% kpiDanger）/ 打断+失败 / fork+重新生成。
- **图表区**（`_shared/ChartCard` + echarts，option 工厂集中 `chatAnalytics/components/chartOptions.ts`，色板 `_shared/chartTheme.ts`）：
  1. 时序双轴：柱=轮次、线=活跃用户（interval 粒度）；
  2. 端类型占比（环形）；
  3. byCompany 横向柱 Top 10（`IdNameCell` 名称化）；
  4. byTool 柱状（工具热度）；
  5. byAnswerStatus 环形（success/partial/failed）。
- **Users 表**（修订记录 6：原 byUser Top 20 改全量+分页）：标题 "Users — click a row to view their Q&A"，antd Table 客户端分页（pageSize 默认 10，showSizeChanger），列：User `IdNameCell` / Client（端类型 Tag）/ Company / Organization（`IdNameCell`，空不显）/ Turns / Threads；行点击跳 `/devSupport/chatMessages?userId=...`（问答列表页读 query 初始化筛选——两页联动，`(unknown)` 不跳）。
- **注册 3 处**：路由 `{ path: '/devSupport/chatAnalytics', name: 'AI Chat Analytics', component: './devSupport/chatAnalytics' }` + NAV_GROUPS `AI Chatbot` 分组 `Chat Analytics` + 页面目录。
- P1：KPI 行追加 Tokens / Cost / 单轮耗时 p95 三卡（后端 P1 就绪后），并放 "Deep dive →" 链接跳 `/devSupport/llm/dashboard`（caller_agent=chat 预置筛选）复用既有成本/性能下钻页。

---

## 6. 可分析维度全景（回答"能从哪些维度分析"）

通用切片维度（以下指标基本都可按这些组合切）：**时间**（day/hour）× **人** × **公司** × **组织** × **端类型**。

### 6.1 现有数据直接可算（无需埋点）

| 类别 | 指标 | 数据来源 | 本期落点 |
|---|---|---|---|
| 规模 | 会话数（新建/活跃）、消息数、问答轮次、会话深度分布、归档率 | `ai_chatbot_thread` + `ai_chatbot_message` | **P0 §5** |
| 活跃 | 活跃用户 DAU/WAU/MAU、Top 用户/公司/组织、端类型占比 | 同上 | **P0 §5** |
| 质量 | 回答成功率、打断率（partial）、失败率、需选公司率（`attribution @> '["needs_company_pick"]'`） | `ai_chatbot_message.status/attribution` | **P0 §5**（需选公司率 P1 可加） |
| 行为 | fork 次数、编辑重问/回答重新生成次数（parent 分支统计）、斜杠命令使用量（`/knowledge`、`/combined` 词边界正则，命令原文随消息落库） | `thread.parent_thread_id`、`message.parent_message_id/content` | P0 含 fork/regen；斜杠命令 P1 |
| 功能 | 工具使用分布（get_financials/get_benchmark_data/search_knowledge_base…）、带图回答数（`content LIKE '%```chart%'`） | `message.used_tools/content` | P0 含 byTool；图表量 P1 |
| 性能 | 单轮端到端耗时 avg/p50/p95、各图节点耗时瀑布、LLM TTFB | `ai_trace.duration_ms`、`ai_trace_span`、`ai_llm_call_log.perf_*`（`message.trace_id` 关联） | P1（进程内直调 tracing/llm 服务） |
| 成本 | token（in/out/cached/reasoning）与 USD 成本按 人/公司/模型/节点；Top 贵会话 | `ai_llm_call_log.usage_*/cost_usd`（经 trace join 取公司/组织） | P1；深度下钻直接复用 `/devSupport/llm/*` 五个分析页（caller_agent=chat） |
| 可靠性 | LLM 失败/截断（finish_reason='length'）/重试率（trace_attempt_no>1）/模型流量占比 | `ai_llm_call_log` | 复用 llm Dashboard，不重造 |
| 知识库 | chatbot 内知识库检索量、零命中率、检索耗时、热门空间/文档 | `ai_rag_search_log`（caller_type='CHATBOT'）、`ai_rag_space/entry.hit_count` | P1 备选（rag 域已有 stats 页，先看是否重复） |
| 智能体 | 实际执行图分布 standard/kb/combo（span 名反推，近似值） | `ai_trace_span.name`（dispatch/retrieve_kb） | 近似值不上页面，等 §6.2 埋点后做精确版 |

### 6.2 需新增埋点/列才能算（P2 立项清单，本期不做）

| 指标 | 缺口 | 建议落点 |
|---|---|---|
| agent_mode 精确分布（命令触发 vs API 触发） | 模式判定收口 `stream_turn` 不落库 | assistant 消息加 `agent_mode` 列或写 `ai_trace.attributes` |
| guardrail 拦截率/原因 | 无专列；moderation_unavailable 轮根本不落库 | 拒答 assistant 加 attribution 标记（仿 needs_company_pick）+ 计数打点 |
| combo 分诊场景分布（business/kb/both 精确） | `combo_scenario` 只在图 state | 落 trace attributes |
| 图表类型×数据类型结构化统计、坏 fence 率 | 只能全文解析围栏 | assistant 消息加 `charts` JSONB |
| partial 细分（用户停止 vs 断连 vs 异常） | finally 兜底统一 partial | 落库带 `stop_reason` |
| 首帧延迟（发问→首个 answer_delta） | 无 | `stream_turn` 计时写 trace attributes |
| 问题语种分布 | guard 判定不落库 | message 列或 trace attributes |
| 消息级赞/踩反馈 | 无表 | 新表 `ai_chatbot_message_feedback`（需求另立） |
| chatbot 成本免 join 按公司聚合 | chat 调用 `ref_company_id` 恒 NULL | 图节点 `TraceContext` 补传 company_id——**建议优先做**，llm `/stats` byCompany 即刻对 chatbot 生效 |

---

## 7. 数据库迁移 `V004__chatbot_manage_indexes.sql`（纯索引，无列变更）

**用户拍板：消息表不加公司/组织/端类型冗余列**——这三个维度 thread 表本就持有，查询走"thread 圈定 → message 单表"两步编排（§4.2、§5.1）。V004 只补索引（幂等 `CREATE INDEX IF NOT EXISTS`；ORM `chat_message_model.py` / `chat_thread_model.py` 的 `__table_args__` 同步声明）：

```
-- 消息侧（现状 user_id / parent_message_id / created_at 全无索引）
(user_id, created_at DESC) WHERE role='user'                       -- QA 分页主查询
(parent_message_id)        WHERE parent_message_id IS NOT NULL     -- 答案反查 / regen 统计
(created_at)                                                       -- 时序/区间聚合（也治现状 stats 14 天全扫）
-- （可选）thread 排序部分索引
(last_message_at DESC) WHERE deleted=FALSE ；(created_at DESC) WHERE deleted=FALSE
```

thread 的 company_id/organization_id/client_type 过滤列不加索引：会话表量级小、`find_ids_by_filters` 全扫可接受（与现有 manage 列表过滤同水位），量大再议。

**选型记录**：冗余列方案（消息表加三列 + 回填 + 写入点改造）被否——thread 已知维度，两步编排零 schema 侵入、无双写一致性负担。附带口径：维度取**会话当前归属**——管理端续聊切换公司（`set_active_company`）会使该会话全部历史消息随之重归属，接受此口径（会话粒度归属本就是产品语义）。

---

## 8. 权限与口径决策

- **新端点鉴权跟随现状**：`dependencies=[Depends(get_current_user)]`（登录即可），与既有 3 个 manage 端点一致；devSupport 入口由前端 SecurityLayout 菜单权限闸门控制。
- **建议 P1 顺手收紧（低成本，留决策）**：QA/analytics 暴露全量用户对话内容，敏感面大于会话元数据。可给全部 `/manage/*` 统一加管理端守卫——判定用现成语义 `ctx.company_id` 为空即管理端（同 `identity_resolver` admin-only 判定、`sse_provider` 端类型判定同源），公司端用户调用返回 403。一处 Depends 即可，不新造权限体系。
- 时间口径统一表述：**存储/接口=UTC，展示=浏览器本地时区（页面 Tag 标注）**；日期筛选=UTC 自然日含边界（UI 标注 `(UTC)`）。
- QA 配对口径：`parent_message_id` 优先，`trace_id` 兜底，孤儿问题 answers=[]；多答全返；软删会话问答包含并标注。

---

## 9. 分期与影响文件

| 期 | 内容 |
|---|---|
| **P0** | V004 索引迁移；threads 排序参数；`/manage/qa`、`/manage/analytics` 两端点（纯 chatbot 两表指标，维度经 thread 两步圈定）；前端 chatManage 排序+时区、chatQa 页、chatAnalytics 页（KPI+5 图+byUser 表） |
| **P1** | analytics 追加 token/成本/耗时（直调 tracing/llm 服务）；`/manage/*` 管理端守卫；需选公司率/斜杠命令/带图回答数指标；chatQa↔chatAnalytics 联动跳转打磨 |
| **P2** | §6.2 埋点清单（优先 TraceContext 补 company_id）；tracing 时间工具收敛到 `_shared/time.ts`；dateFrom/dateTo 时区语义精确化（date→datetime） |

**Python**（`CIOaas-python/source/chatbot/` + `sql/`）：

| 文件 | 改动 |
|---|---|
| `sql/migrations/business/V004__chatbot_manage_indexes.sql` | 新增（§7，纯索引） |
| `domain/models/chat_message_model.py` / `chat_thread_model.py` | `__table_args__` 补索引声明（无列变更） |
| `domain/repository/chat_message_repository.py` | QA 3 查询 + `GROUP BY thread_id` 聚合方法 |
| `domain/repository/chat_thread_repository.py` | `find_page` 排序白名单、`find_ids_by_filters`、`find_by_ids`、聚合方法 |
| `application/service/chat_manage_service.py` | `manage_list_qa` + `manage_analytics` 两步编排（+span） |
| `application/dto/chat_manage_dto.py` | Filters/Item DTO 扩展 |
| `interfaces/vo/response.py` + `interfaces/routes.py` | 2 新端点 + threads 排序参数 |

**Web**（`CIOaas-web/src/`）：

| 文件 | 改动 |
|---|---|
| `pages/devSupport/_shared/time.ts`（+ 单测） | 新增（formatUtcToLocal/parseUtcMs/localTzLabel） |
| `pages/devSupport/chatManage/index.tsx` + `ThreadDetailDrawer.tsx` | 排序受控列 + Created 列 + 时间本地化 + 时区 Tag |
| `services/api/chat/chatManageApi.ts` / `chatManageDto.ts` / `services/service/chat/chatManageService.ts` | 排序参数 + qa/analytics 接口三层 |
| `pages/devSupport/chatQa/`（index.tsx + hooks + less） | 新增（§4.3） |
| `pages/devSupport/chatAnalytics/`（index.tsx + hooks + components/chartOptions.ts + less） | 新增（§5.2） |
| `config/routes.ts` + `pages/devSupport/_shell/DevSupportShell.tsx` | 2 路由 + NAV_GROUPS 2 项 |

---

## 10. 验证清单

1. **Python 单测**：排序白名单（合法/非法/缺省）；QA 配对（parent 命中 / trace 兜底 / 孤儿 / 多答排序 / 软删标注）+ 维度圈定（带/不带公司过滤两路径）；analytics 各聚合（thread 维度映射正确、含 `(unknown)` 哨兵、口径：thread 排软删 message 不排）。
2. **迁移验证**：`scripts/migrate.py --dry-run` 预览；执行后 `\di` 确认索引就位；重复执行幂等。
3. **前端**：`npx umi-test` 过 `_shared/time.ts` 与 chatManageService 单测；`npm run tsc`（存量 2 坏文件基线外零新增）；`node scripts/check-routes.js` 无新增违规（新页面必须文件夹 `index.tsx`）。
4. **手动冒烟**（test 环境）：chatManage 两列排序来回切且分页重置；时间显示本地时区 + Tooltip UTC + 页面时区 Tag；chatQa 按人/公司/时间筛选、多答展开、Open thread 抽屉；chatAnalytics 筛选联动全部图表、byUser 行点击跳 chatQa 带参。
5. **性能抽查**：EXPLAIN 抽查 QA 分页走 `(user_id, created_at DESC)`、时序聚合走 `(created_at)`、答案反查走 `(parent_message_id)`；两步圈定路径确认 `= ANY(ids)` 命中 `(thread_id, seq)` 前缀。
