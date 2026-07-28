# devSupport / Financial Extract 模块设计

> 日期：2026-07-27 ｜ 修订：2026-07-28（按用户指示：新接口从 Java 移至 Python `financial_extract` 一级域）｜ 状态：已确认，进入开发
> 关联文档：[智能解析系统架构](../../智能解析/调研/system-architecture.md)、[devSupport 筛选栏一致性](./2026-07-10-devsupport-filter-bar-consistency-design.md)、[chat manage 排序/问答/分析](./2026-07-10-chat-manage-sort-qa-analytics-design.md)

## 1. 需求

在 devSupport 下新增 `financial_extract`（AI 财务提取 / 智能解析）模块，两个能力：

1. **任务管理列表**：看到所有解析任务，每行能看出是**哪个公司**的数据、**谁**提交的、从**管理端还是客户端**提交、管理端提交的是**哪个组织**。
2. **任务详情**：点详情直接进入 Import Statements 入口进入的那个上传页面（`/aIFinancialExtraction`），但**只有查看权限**——不能修改任何数据，只能看。

> 关于"允许下载 / 导出"：需求确认时定的是"不改数据的操作保留"。实际核查后发现**该页面几乎没有下载 / 导出入口**——只有 `CsvPreview` 在预览失败时给一个兜底下载链接，`PdfPreview` 反而刻意用遮罩盖住了 Chrome 原生的 Save / Print 按钮，图片与 Office iframe 都没有自有下载入口。所以这一条落地为"不新增、也不移除既有入口"，不作为验收项。

## 2. 现状核实（逐条读码确认）

### 2.1 任务表只有两个可用归属维度

`ai_financial_extraction_task`（实体 `ai/financial/extract/domain/AiFinancialExtractionTask.java`）共 10 列：
`id` / `company_id` / `status` / `has_extractable_data` / `deleted` / `completed_at` / `created_by` / `created_at` / `updated_by` / `updated_at`。

需求四个维度里，**公司**（`company_id`）和**提交人**（`created_by`，`@PrePersist` 写 `SecurityUtils.getUserId()`）现成；**端类型**和**组织**表里都没有。

推导路径都不可靠：
- 组织：`company ⟷ organization` 是多对多（`r_organization_company`，且 `organization` 有 `pid` 树），一个公司可挂多个组织；`User.organizationId` 是 `@Transient` **不是列**，用户→组织同样走关联表 `r_organization_user` 多对多。查询期推导必然出现歧义，且用户换组织后历史任务归属会跟着变。
- 端类型：全库没有真实来源。`user.role_type` 只能"按角色近似"；`ai_file_registry.end_type`（APP/ADMIN）列虽存在，但**Java 财务抽取链路从不写它**，财务行恒 NULL；`files.business_type` 同样不写。

运行时能拿到登录态：`SecurityUtils.getPrincipal()` → `UserContext{ companyId, organizationId }`。`companyId` 空 = 管理端，非空 = 公司端。**只能在任务创建时把当时的登录态快照下来**——但这个快照的精度有限，见 §3.5。

### 2.2 没有任务列表接口

`AiFinancialExtractionController` 13 个端点里，12 个是单任务维度；唯一的非任务维度端点是 `GET /companies/{companyId}/dataMappingNotes`（公司维度 + `Pageable` 分页）。`AiFinancialExtractionTaskRepository` 只有 `findByIdAndCompanyIdAndDeletedFalse` 一个方法，既没有分页也没有 `JpaSpecificationExecutor`。

Python 侧有只读列表接口 `GET /lg/financial-extract-tasks`（`source/lg/financial_extract_task/`）：`limit`/`offset` 分页、**无筛选、无 total、无鉴权**（源码注释即 `Auth: none (internal read-only listing)`），全量吐 `id` / `companyId` / `createdBy`，另有 `GET /files` 全量吐文件清单。唯一消费方是前端 `/devSettings` 的两个 Tab（只读表格 + Reload，行不可点、无详情）。前端类型里的 `companyName` / `createdByName` 已恒为 `null`（Python 去掉 JOIN 后未同步前端类型）。

### 2.3 详情页数据：终态任务拉不到解析行

`pullExtractData` 按任务状态分档：

| 状态 | 返回 |
|---|---|
| `REVIEWING` / `CONFLICT_RESOLUTION`（`isDataPullable`） | 全部文件 + `dataValues` 解析行 |
| `FAILED` | 只有文件元信息（`status` + `error`），`dataValues` 空 |
| 其余 15 个状态（含 `COMMITTED` / `COMPLETED` / `PROCESSING` / `DRAFT`） | `files: []` |

`status` 取到脏值时 `fromCode` 返回 empty，同样落到 `files: []`。任务管理列表里绝大多数是已完成任务 → 不动后端，点详情就是空页。

### 2.4 上传页强依赖会话内存，直接访问会被弹走

`/aIFinancialExtraction` 只认 `?id=<companyId>` 和 `?step=1|2`，**`taskId` 不在 URL 里**。数据来源只有 `fileStore`（跨路由内存单例）或 `sessionStorage['ocr_task_payload']`，两者都没有时 `history.replace` 回 `/Finance`。页面内**没有任何 readonly / role 概念**，整页默认可编辑可提交。

已验证的可行前提：`processFromTask(taskId, companyId, [])` 传空 files 可行——`initial = []`，随后拿到接口 `files` 后由 `mergeIntoFiles` 全量 upsert，`fileName` / `fileSize` 都从接口取。**只要 URL 带 taskId 就能重建页面。**

### 2.5 附带发现的既存问题

| 问题 | 处置 |
|---|---|
| **跨公司越权读写**：`pullExtractData` / `pullExtractDataIncrement` / conflict service 的 `loadTask` 以及 `deleteFiles` / `replaceFile` / `uploadComplete` / `verify` / `completeTask` 全部只 `findById` + 判 `deleted`，**不校验 companyId**（全模块唯一带公司过滤的是 `resolveOrCreateTask`）。且 `verify` 明确注释"state machine check intentionally skipped"后直接 `deleteAllByTaskId`；`FILE_MUTATION_BLOCKED` 不含 `REVIEWING` / `READY_TO_COMMIT` / `CONFLICT_RESOLUTION`，这些状态的文件可删可换 | 见 §3.6（范围决策，建议纳入本次） |
| **TIFF 预览全局失效（既存缺陷，非本模块新增）**：`previewAsPng` 现在**已需 JWT**（`@AnonymousAccess` 只剩死 import，`CommonSecurityConfiguration` 兜底 `anyRequest().authenticated()`），但前端 `ImagePreview` 用 `<img src>` 直载、带不上 Authorization 头 → **所有状态**的 TIFF 预览都 401，不只终态。`isPreviewable` 白名单不含 `COMPLETED` 只是叠加在上面的第二道门 | 进 CIOaas-api 台账；本模块记为已知限制 |
| 死代码：`streamFilePreview` + `PREVIEW_URL_TEMPLATE` 无 controller 映射、`AnonymousAccess` 死 import、controller javadoc 仍写"安全闸门为 @AnonymousAccess 无鉴权"（事实已错） | 进 CIOaas-api 台账 |
| `findOrganizationIdByUserId` 是 `LIMIT 1` 无 `ORDER BY`，多组织用户取到不确定值 | 进 CIOaas-api 台账 |
| conflict service 签名直接返回 Response VO（`Page<AiDataMappingNoteResponse>`）、模块未按 `architecture.md` §1 四层组织、Controller 路径 camelCase 不符 `coding.md` §1 | 进 CIOaas-api 台账 |
| `/devSettings` 两个 Tab 与本模块重复；`aiExtract` 的 companyName/createdByName 类型与 Python 实现脱节 | 进 CIOaas-web 台账 |

## 3. 已定决策

| # | 决策 | 理由 |
|---|---|---|
| 1 | **新增专用只读回放端点**，不动 `pullExtractData`、不动 `isPreviewable` 白名单 | 放宽现有判定会改变生产上传流的轮询终止逻辑（前端靠空 `files` + 终态 status 判断任务已结），有回归风险 |
| 2 | **任务表加 `end_type` + `organization_id` 两列快照** | 提交端与组织是"提交那一刻的事实"，查询期推导会因用户换角色/换组织而漂移，且多对多关系有歧义 |
| 3 | **只读仅前端强制**（页面不给写入口、不调写接口） | devSupport 是内部工具；后端硬闸需要新权限模型。⚠️ 这条成立的前提是 §3.6 的 ACL——否则前端只读等于没有防线 |
| 4 | **详情复用原页面 URL** `/aIFinancialExtraction?id=&taskId=` | 需求明确要"直接指向 Import Statements 入口进入的上传页面" |
| 5 | **新接口（列表 + 只读回放）放 Python 新一级域 `source/financial_extract/`**（2026-07-28 用户指示，替代初稿"列表接口放 Java"） | ① devSupport 生态的管理查询接口本来就都在 Python（chatManage→`/api/ai/chat/manage/*`、rag、llm、file_registry），放 Java 反而偏离生态；② 任务/文件/单元格三张表 Python 侧全有 ORM（`ExtractionTask` / `AiFileRegistry` / `ExtractedData`，`ExtractedData` 还是 Python 写入的）；③ 鉴权与 ACL 先例现成（`get_current_user` + file_registry 的"公司端锁本公司、跨公司 404"口径）；④ Java 改动收敛到最小（两列 + 快照写入，不新增接口），绕开 Java 侧 dto 包缺失等分层争议。**Java 既有接口（`pullExtractData` 等生产上传流）原样复用不动** |

**边界澄清（2026-07-28）**：`source/ai/agent/financial_extract_graph/`（财务提取对话图/AI 节点）**不迁入新域**——按 `source/ai/CLAUDE.md` 与 chatbot 先例（业务域 `source/chatbot/` 与图 `source/ai/agent/chatbot_graph/` 分离），agent 图归 ai 域、业务接口归业务域。既有 `source/lg/financial_extract_task/`（/lg/* 裸接口）也**不迁不动**——它已随 `/devSettings` 挂了下线计划（台账），迁移其 URL 会破坏现有调用方。

### 3.1 `taskId` 深链恒为只读，不设 `readonly` 参数

初稿是 `?taskId=&readonly=1`，**已改为只用 `taskId`**：带 `taskId` 进来即只读回放模式。

理由是安全的：只读若靠独立开关，把 `readonly=1` 从 URL 删掉就能以**可编辑模式**打开任意历史任务，而写端点当前无公司 ACL（§2.5）。把只读绑定到 `taskId` 本身，这条路径不存在。

两种模式天然可区分：生产上传流经 `fileStore` / `sessionStorage` 传 payload、URL 里**没有** `taskId`；管理端详情只带 `taskId`、不写会话存储。同时少一个用不到的参数（YAGNI）。

### 3.2 端类型取值口径：`APP` / `ADMIN`

新列 `end_type` 取 **`APP`（客户端）/ `ADMIN`（管理端）**，与同表族的 `ai_file_registry.end_type` 一致（V012 专门把存量 `CLIENT` 改写为 `APP`），列名同样叫 `end_type` 而非 `client_type`。

**不要**复用前端 `devSupport/components/clientType.ts`——那是 chatbot 的口径（`company` / `admin`），取值不同。本模块在自己域内定常量。

### 3.3 schema 变更走 Python 迁移树，但要防 Hibernate 抢跑

⚠️ 易踩点一：`ai_financial_extraction_task` 是 Java 建的表，但按 `CIOaas-python/source/lg/CLAUDE.md`，**`ai_` 前缀表的 schema 变更自 sprint114 起统一写 CIOaas-python 的 `sql/migrations/`**（先例 V012–V015 都在改 `ai_file_registry`）。

⚠️ 易踩点二：**Java 全环境 `ddl-auto: update`**（`deploy/cioaas-web.yml` / `-prod.yml` / `-staging.yml` 均为 `update`）。加两个 `@Column` 字段后 Hibernate 会在启动时自建这两列——但**不带列注释**。所以：

- 迁移必须 `ADD COLUMN IF NOT EXISTS` + **独立的 `COMMENT ON COLUMN`**（能在 Hibernate 已建列的情况下事后补注释）
- 回填必须带 `WHERE end_type IS NULL` 防重跑
- **部署顺序**：Phase 1 迁移须在 Phase 3 的 Java 版本上线**前**跑完，否则列由 Hibernate 先建、注释与回填时序错乱

⚠️ 易踩点三：**两侧 ORM 都要改**。Python 也映射了这张表（`CIOaas-python/source/lg/db/models/models.py` 的 `ExtractionTask`，且 Python 侧有写封装 `extract_financial.mark_*` / `finalize_task`）。两列要同批加到 `ExtractionTask`（可空 + 中文注释，标注 Java 写入、Python 只读）。漏改会被 Python 侧评审按强制流程打回。

**迁移拆两个文件**：
- `V019__ai_financial_extraction_task_add_end_type_and_organization.sql` — 只加列 + 索引
- `V020__ai_financial_extraction_task_backfill_end_type.sql` — 只回填

> 审核附注（2026-07-28，F4/F5）：V019 的 `ALTER TABLE IF EXISTS` 与后续无守卫的 `COMMENT`/`CREATE INDEX` 语义不完全一致——全新环境（Java 尚未建出 `ai_financial_extraction_task`）会整文件失败；V020 的异常兜底只覆盖权限、覆盖不到列缺失。两者均不影响存量环境（表恒在），且 V019/V020 已在本地库应用记账、按"已应用文件永不再改"不回改；全新环境的前提（Java 先建 ai_ 基础表）V001 头注释已有约定。

拆开的原因：runner 是一文件一事务，回填失败会把加列一起回滚；而已应用的迁移文件永不许再改。另外回填要读 Java 属主表（`"user"`），**迁移树里零先例**（现有 18 个 business 迁移无一读 Java 表），所以回填语句要包 `DO $$ ... IF to_regclass('public."user"') IS NOT NULL THEN ... END IF; $$` 守卫，上线前确认 Python 迁移账号对 `"user"` 有 SELECT 权限。

### 3.4 快照写在 service 层，不写 `@PrePersist`

初稿说"写入点在 `@PrePersist`（与 `createdBy` 同处，一致）"——**这个类比是错的，已改**。

`createdBy` 用的 `SecurityUtils.getUserId()` 是纯 ThreadLocal 读、零 I/O；而 `getPrincipal()` 要反射取 bean + 读 Redis，缓存 miss 时 `UserInfoCache.reloadFromDb` 会执行 `userRepository.findById` + `userRepository.findOrganizationIdByUserId` 并回写 Redis——**等于在 JPA 生命周期回调里重入同一个 EntityManager**，Hibernate 可能抛异常或触发嵌套 flush，直接打挂任务创建。同时这也违反 `architecture.md` §1.2（domain 层零框架依赖、业务规则一律在 application/service）。

改为：在 `AiFinancialExtractionServiceImpl.resolveOrCreateTask` 的**新建分支**里取一次 `SecurityUtils.getPrincipal()`，显式 `setEndType` / `setOrganizationId` 后 save；`@PrePersist` 一行不动。

⚠️ 顺带纠正一处事实错误：初稿说"任务创建有两条路径（presignUploads 带空 taskId、commitUpload）"。**`presignUploads` 从不创建 task**——`taskId` 空时走 deferred 分支根本不调 `resolveOrCreateTask`，非空时只查不建。全仓唯一 `new AiFinancialExtractionTask()` 就在 `resolveOrCreateTask` 里，唯一以 `null` 调它的是 `commitUpload`。所以**只有一个写入点**。

`principal` 为空时两列留 NULL 并打一条 WARN（含 **companyId + userId**——不是 taskId：该时点 `task.id` 尚未生成、由 `@PrePersist` 在 save 时才赋值，照写只会打出 null）。打日志的原因：`created_by` 恒非空，所以上线后新任务再出现 NULL 只可能是写入期取不到 principal，与"历史回填推不出"的 NULL 同形、无法从数据区分——靠日志区分。不为此新增 `UNKNOWN` 枚举值（不多造一个态）。

### 3.5 组织快照是"登录态主组织"，不是确定值

必须把话说准：`organization_id` 落的是**登录会话里的主组织**，对多组织用户而言是**不确定的任意一个**——`UserDetailsServiceImpl` 取 `user.organization`，为空时取 `getOrganizationListByUserId(...).get(0)`（**无 `ORDER BY`**）；缓存重建走另一条 `findOrganizationIdByUserId`（`LIMIT 1`、同样无 `ORDER BY`）。两条路径可能挑出不同结果。

所以：
- 决策 2 的立论改成"快照比查询期推导更稳定"，**删掉"准确"的表述**
- 列注释写明"登录态主组织；多组织用户为不确定值"
- **组织与端类型解耦**：不预设"客户端提交没有组织"。`UserDetailsServiceImpl` 对任何用户（含公司端）都会解析主组织，无端类型分支，所以 APP 行的 `organization_id` 通常**非空**。前端也因此**不做**"仅选 APP 时禁用组织筛选"的联动（chatbot 的 `isOrgFilterDisabled` 是它自己的业务规则，不照搬）
- **回填侧 `organization_id` 一律留 NULL**：历史任务没有组织依据，而写入侧口径本身就不确定，回填等于按"今天的用户状态"给历史任务贴标签。回填只做 `end_type`

回填的风险是**归因错误**而非越权——`organization_id` 不参与任何鉴权（§3.6 的 ACL 只看 companyId / roleType），标错只会让"按 Organization 筛选"得出错误结论。**这一点要写进文档，避免后来者误以为组织列是隔离手段而基于它做鉴权。**

### 3.6 ACL 口径（Python 侧，对齐 devSupport 生态既定口径）

**定稿口径**（列表接口与只读回放接口**共用同一个校验函数**，不各写一遍），与 file_registry / chatbot 生态一致：

1. `ctx.company_id` 非空（公司端）→ 强制圈定本公司：列表忽略前端传的 `companyId` 筛选、改用本公司；回放校验 task 行的 `company_id`，越界返回业务失败（同 file_registry"跨公司 404 不泄露存在性"语义，但走 `success=false` 信封——见 §5.3 第 4 条）
2. `ctx.company_id` 为空（管理端）→ 放开全量

**关于"company_id 空 ≠ 超管"的评审 blocker 的处置**：Java 侧确实存在 `role_type ∈ {2,3,4,5}` 的非超管角色，初版 Java 方案因此加了 `role_type=1` 硬判。但接口移到 Python 后：① Redis 会话（`AuthUser`）**没有 roleType 字段**，Python 侧拿 roleType 要额外回查 Java/user 表，复杂化；② devSupport 生态的既定口径（`2026-06-15-dev-support-permission-gating-design.md`，chatManage `/manage/*` 的现行实现）就是"登录 + company_id 判端"，本模块不该单独发明更严的判定；③ 该口径依赖的系统不变式是"**company_id 为空的账号即 roleType=1 超管**"（chatbot CLAUDE.md 明文："空=超管 ⟺ roleType=1"）。**处置**：沿用生态口径 + 把不变式写进代码注释；部署前用一条 SQL 验证一次不变式（`SELECT role_type, count(*) FROM "user" WHERE company_id IS NULL AND is_deleted = false GROUP BY role_type;`）——若出现 `role_type <> 1` 的行，这是**平台级**口径问题（chatManage 等全部 devSupport 管理接口同病），单独立项修，不在本模块内特判。

**另外两条必须写明的边界：**

- **只读深链不受 devSupport 菜单闸门保护**。`SecurityLayout` 的闸门只覆盖 `/devSupport*`，判据是 `localStorage` 里的 `roles`（纯客户端可改）；而 `/aIFinancialExtraction` 路由没有任何 `role` 字段、也不在 `adminUrls` 黑名单里。所以只读页的越权防线**100% 依赖新只读端点的后端 ACL**。
- **深链的 `id` 参数不参与 ACL**（ACL 按 task 行的 `company_id` 判），但页面拿它直接调 `companyXQ` → `/invite/{id}`（该端点无归属校验）。结果是只读页头部可以显示 A 公司、表格是 B 公司的数据。**修法**：只读回放响应带上权威 `companyId`（取自 task 行），页面用它渲染公司信息与返回链接，URL 的 `id` 只作首屏兜底。

### 3.7 两项范围决策（建议纳入本次，待用户拍板；未拍板前按"不做"实施）

这两项都不是本需求"必须"，但新功能会放大既存风险：

**A. 补齐 Java 存量端点的公司 ACL。** 列表页把全公司 `taskId` 递到更多人手里之后，`verify`（跳状态机 + `deleteAllByTaskId`）、`batchDelete`、`replace`、`uploadComplete`、`complete` 这些**写**端点在 devtools 里就能改别家公司在跑的任务——`FILE_MUTATION_BLOCKED` 不含 `REVIEWING` / `READY_TO_COMMIT` / `CONFLICT_RESOLUTION`。改法是把 `taskRepository.findById(tid)` 换成 `findByIdAndCompanyIdAndDeletedFalse`（公司端）/ 显式 company 校验（管理端放行），`loadTask` 加一个 companyId 入参，一行级改动。代价：8 个端点全在生产上传主链路上，有回归面。不做的代价（明示）：**本页把写越权的可利用面从"已知某个 taskId 的人"扩大到"所有能打开列表页的人"**。

**B. 给 Python `/lg/*` 三个裸接口加鉴权。** 当前**无鉴权**、全量吐 task/file 清单。新页面加了 ACL 而旧裸接口还开着，等于 ACL 白做。既然已计划下线 `/devSettings`，顺手加鉴权（或直接关闭）成本很低。

## 4. 架构

```
devSupport 侧栏
└── Financial Extract（新一级导航组）
    └── Task Management  → /devSupport/financialExtractTasks
                             │ 行点击 / View
                             ↓
                   /aIFinancialExtraction?id={companyId}&taskId={taskId}
                   （生产上传页，只读模式；带 taskId 即只读）
```

数据流（新接口全在 Python，经统一网关 `/api/ai/**` → Python，与 chatManage 同链路）：

```
列表页 → GET /api/ai/financial-extract/manage/tasks（Python 新域，分页 + 筛选 + §3.6 ACL）
        → 返回 ID 维度，公司/提交人/组织名由前端 DirectorySelect 批量解析（Java options 接口）

只读详情 → GET /api/ai/financial-extract/manage/tasks/{taskId}/extract-data（Python 新域）
         → 任何状态都回放文件 + 解析行 + 用户编辑痕迹（edit* 字段）+ 权威 companyId
         → previewUrl 经 lgpi_api.query_file_link（Java getFileLinkById）取预签名 GET

快照写入 → Java resolveOrCreateTask（任务唯一创建点）落 end_type / organization_id 两列
生产上传流 → Java 既有 13 个端点原样不动
```

## 5. 后端设计

### 5.1 Java：仅两列 + 快照写入（不新增任何接口）

`AiFinancialExtractionTask` 加两个可空字段：`endType`（`end_type` varchar(16)，`APP`/`ADMIN`）、`organizationId`（`organization_id` varchar(36)），实体内中文注释。

写入点：`AiFinancialExtractionServiceImpl.resolveOrCreateTask` 的**新建分支**（全仓唯一 task 创建点，见 §3.4）——取一次 `SecurityUtils.getPrincipal()`，`companyId` 空→`ADMIN`、非空→`APP`，`organizationId` 原样落；principal 为空时两列留 NULL 并打 WARN（含 taskId + userId）。不碰 `@PrePersist`。

索引（在 Python 迁移里建）：只加 `(organization_id, created_at DESC) WHERE deleted = FALSE`。`(company_id, created_at DESC)` 已存在；`end_type` 基数只有 2，低基数索引等真出现慢查询再加——已应用的迁移不可改，宁可少加。

### 5.2 Python：`source/financial_extract/` 新一级域

按 file_registry / chatbot 模板做标准 DDD 分层，HTTP 统一前缀 **`/api/ai/financial-extract`**（kebab-case，对齐 `/api/ai/file-registry` 先例；经统一网关到 Python，无需网关改动）：

```
source/financial_extract/
├── __init__.py                     导出 router 供 main.py include
├── CLAUDE.md                       域文档（模块定位/目录/特殊约定）
├── interfaces/
│   ├── routes.py                   GET /manage/tasks ＋ GET /manage/tasks/{task_id}/extract-data
│   └── vo/response.py              envelope 响应模型（lowerCamelCase）
├── application/
│   ├── service/task_manage_service.py   列表查询 + 只读回放编排 + ACL（§3.6）
│   └── dto/task_manage_dto.py           service 内部 DTO（snake_case）
└── domain/
    └── repository/extraction_task_repository.py   本域查询封装（首参 session、不 commit）
```

分工边界（照 file_registry 先例）：**ORM 实体在共享 DB 层** `lg/db/models/models.py`（`ExtractionTask` / `AiFileRegistry` / `FileRecord` / `ExtractedData`），本域不另建实体；本域 repository 只做本域视角的查询封装（分页筛选、按 task 取文件与单元格），不含业务编排。鉴权 `ctx: AuthUser = Depends(get_current_user)`；文件链接经 `lgpi_api.query_file_link`（Python 不直连 S3——"去 S3 直连"是 2026-07 已收敛的平台约定）。

**列表接口**：

```
GET /api/ai/financial-extract/manage/tasks
```

| Query 参数 | 说明 |
|---|---|
| `companyId` / `createdBy` / `endType` / `organizationId` / `status` | CSV 多选（照 chatManage 口径，后端 split 成 IN） |
| `dateFrom` / `dateTo` | 创建时间自然日区间（含边界，UTC，复用 chatbot `_common` 同款区间语义） |
| `page` / `pageSize` | 1-based 分页，缺省 20（对齐 chatManage） |
| `sortBy` / `sortOrder` | 白名单 `createdAt` / `completedAt`（FastAPI `Query` 约束 + service 白名单映射列），缺省 `createdAt desc` |

响应 `{success, code, message, data: {items, total, page, pageSize}}`，item：`id` / `companyId` / `endType` / `organizationId` / `createdBy` / `status` / `hasExtractableData` / `createdAt` / `completedAt`（UTC `yyyy-MM-dd HH:mm:ss`，service 层格式化）。**不返回 `updatedAt`**（列表无此列，YAGNI）。**不 JOIN 名称**：前端 `DirectorySelect` 批量解析。恒过滤 `deleted = false`。

**只读回放接口**：

```
GET /api/ai/financial-extract/manage/tasks/{task_id}/extract-data
```

响应 `data` 的形状**逐字段对齐前端既有契约**（`services/api/ai/aiService.ts` 的 `PullExtractData` / `RawFileResult` / `RawCell`——`{status, files:[{fileId,fileName,fileSize,status,previewUrl,error,dataValues:[RawCell...]}]}`），前端 `useOCRData` 共用同一套解析逻辑。要点：

1. **不按状态分档**：任何未软删任务都返回全部文件（`AiFileRegistry ⨝ FileRecord`，`deleted=false`）+ 全部解析行（`ExtractedData`，`deleted=false`，含 `edit*` 编辑痕迹——排查价值所在）
2. **`status`**：任务当前状态原样下发（前端轮询终止判定读它）
3. **带权威 `companyId`**（取自 task 行，§3.6 末条；`data` 增加该字段，前端只读模式用）
4. **ACL 失败 / 任务不存在 / 已软删**：返 **HTTP 200 + `success=false`**（前端只在 `resp.success === false` 时终止并报错；HTTP 异常会落进 catch 静默每 5 秒重试）
5. **`previewUrl`**：逐文件经 `lgpi_api.query_file_link`（用户 token 透传）取预签名 GET，TTL 由 Java `getFileLinkById` 平台口径决定（与 file_registry 下载一致，不单独设计）；单文件取链接失败降级空串（不炸整个回放）。**TIFF 文件 previewUrl 置空**——浏览器渲不了 TIFF，Java 的 PNG 代理端点又对历史任务不可用（§2.5 既存缺陷），签了也白搭
6. `RawCell` 字段映射自 `ExtractedData` 列（`source_*`/`edit_*` → lowerCamelCase；`sourceValue`/`editValue` Numeric→float、None 保持 null；`tableId`/`parentTableId` 透传）

**测试**：`tests/financial_extract/`（interfaces / application 分层镜像），DB session mock、`query_file_link` mock，覆盖 ACL 三分支（公司端锁定 / 管理端全量 / 越界 success=false）与 RawCell 字段映射。

**冲突记录接口（2026-07-28 增量，用户要求补上冲突数据展示）**：

```
GET /api/ai/financial-extract/manage/tasks/{task_id}/conflicts
```

数据源 `ai_financial_extraction_conflict_record`（Java 建表/写入，verify 阶段落库；**表无 deleted 列**、无软删语义）。要点：

1. **返回全部 resolution 状态含 `PENDING`**——这正是生产 `dataMappingNotes` 接口查不到的部分（它恒过滤 `resolution IN (OVERWRITE, SKIP)`），也是 `CONFLICT_RESOLUTION` 卡住任务的排查刚需
2. Python 侧无此表 ORM → 在共享 DB 层 `lg/db/models/models.py` 加只读映射 `ExtractionConflictRecord`（Java 写入、Python 只读，照 `FileRecord` 先例），`lg/db/models/__init__.py` 导出
3. ACL / 越权同形失败：与回放接口**共用同一校验**（task 行归属判定，失败 = HTTP 200 + `success=false` + "Task not found"）
4. 响应 `data`：`{status, companyId, conflicts: [...]}`（status/companyId 取自 task 行，页头用）；conflict item 全字段透出：`id / documentType / reportingYear / reportingMonth / dataClassification / lgCategory / existingValue / mappedValue / mappedOriginalValue / mappedCurrency / existingCurrency / exchangeRate / resolution / note / resolvedOrder / resolvedBy / resolvedAt / createdAt`（Numeric→float 保留 null、时间 UTC `yyyy-MM-dd HH:mm:ss`）
5. 排序 `resolved_order ASC NULLS LAST, lg_category, reporting_year, reporting_month`；**不分页**（单任务冲突量级为几条~几十条，全量返回，前端本地分页）

## 6. 前端设计（Web）

### 6.1 新域目录

```
src/pages/devSupport/financialExtract/
├── README.md                                  域文档（§3.1 R8 强制）
└── taskList/
    ├── index.tsx                              注释 + 一行转发
    ├── FinancialExtractTaskListPage.tsx
    ├── constants.ts                           endType + status 的下拉候选与 Tag 配色
    ├── useFinancialExtractTaskList.ts          服务端分页 + 筛选
    └── index.less
```

单个 hook 平铺、两组常量合成一个文件（R4：`hooks/` 与 `components/` 都要 ≥ 2 个才建子文件夹）。等第二个功能页出现再上浮到 `financialExtract/components/`。命名统一 `financialExtractTask` 前缀（memory 的 naming-prefix-clustering 规则）。

**路由 URL 用 `/devSupport/financialExtractTasks`**（不是 `/devSupport/financialExtract`）：R3 要求"域自身 URL 直达的页面收进 `home/`"，而这个页面语义上是任务列表、不是域主页。用带 `Tasks` 后缀的 URL 对齐 `chatManage` 先例（URL `/devSupport/chatManage` → 目录 `chat/manage/`），域根就不承接任何 URL、只放共享物。

导航：`DevSupportShell.tsx` 的 `NAV_GROUPS` 新增一级组 `financial-extract`（title `Financial Extract`），下挂 `Task Management`。新建一级组而非塞进现有 5 组——智能解析是独立业务域，后续还会加文件列表等页面。

`src/pages/devSupport/README.md` 同步补：模块表格一行 + **两条刻意偏离登记**（R8 要求域 README 写明本域特有约定）：① devSupport 全域用英文字面量、不接 i18n（明示豁免 `coding.md` §15，覆盖全部现有页面）；② Financial Extract 详情整页复用 `pages/financial/aiFinancialExtraction`（R5 整页复用允许），URL 落在 `/devSupport` 之外属登记在案的例外，不作为放宽域 URL 前缀约定的先例。

### 6.2 service 层

新建域 `services/api/financialExtract/`（`financialExtractTaskApi.ts` + `financialExtractTaskDto.ts`）+ `services/service/financialExtract/financialExtractTaskService.ts`，两层各带 README（R8）。

**为什么这次新建域成立**（上一轮评审反对新建的理由已不适用）：`architecture.md` §2 域表的组织轴心是**后端契约**，上一轮反对是因为初稿的新接口挂在 Java 同一个 Controller 下、劈域会把一个后端契约拆两处；现在后端本来就是**新的 Python 一级域** `source/financial_extract/`，前端按后端域对齐建新域正是该表的组织原则（先例：chat/ ↔ chatbot、rag/ ↔ rag）。**必须同步在 `architecture.md` §2 权威表登记一行**（`financialExtract/` ｜ Python `source/financial_extract/` ｜ 智能解析任务管理查询）。

**不落 `ai/` 域**：那是 Java `/api/web/ai/financialExtraction/*` 的客户端（Java Result 信封）；**不复用 `aiExtract/`**：那是 Python `/lg/*` 裸接口层（待随 /devSettings 下线），两者信封与生命周期都不同，README 里注明三个域的分界。

页面只 import `services/service/financialExtract/financialExtractTaskService` + `services/api/financialExtract/financialExtractTaskDto`（§4.1）。**上传页只读旁路的 apiFn 也从这里拿**（`useOCRData` 只读模式调 `fetchReadonlyExtractData`，返回结构与既有 `PullExtractDataResponse` 同形）。

### 6.3 列表页

结构照 `ChatManagePage`：`PageHeader`（标题 + 时区 Tag + Refresh）→ 错误 `Alert` → 筛选栏（`FilterField` 包裹）→ antd `Table` 服务端分页 + 列头受控排序。**不做顶部统计卡**（需求没要）。

筛选项（6 个 + Reset）：End Type 多选、Company 多选、Submitter 多选、Organization 多选、Status 多选、创建时间区间。后三个走 `DirectorySelect`（`/invite/options`、`/users/options`、`/organization/options`）。**不做**"仅选 APP 时禁用组织筛选"的联动（§3.5）。

列：Company（`IdNameCell`）、Submitter（`IdNameCell`）、End Type（Tag，NULL→`Unknown`）、Organization（`IdNameCell`，NULL→`-`）、Status（Tag）、Has Extractable Data、Created At、Completed At、Action（View）。时间统一 `formatUtcToLocal` + Tooltip 原始 UTC。

行点击 / View → `history.push('/aIFinancialExtraction?id={companyId}&taskId={taskId}')`。

### 6.4 上传页只读改造

`readonly = Boolean(getQueryString('taskId'))`（§3.1）。按 `benchmarkEntry` 的 `isAdmin` 范式作 prop 逐层下传。

⚠️ **"条件渲染隐藏"不是万能的**，两条例外：
- **`EditableCell` 不能整块隐藏**——值和编辑触发器是同一个节点（非编辑态就是带 `onClick` 的 `<span>{fmtVal(...)}</span>`），隐藏等于把数值一起隐掉、只读页变空表。只读时替换为**去掉 `onClick` 与 hover 样式的纯展示 span**（保留 `fmtVal` 输出与 `ZeroDefaultCellIcon`）。`metricNameNA` 的 'N/A' 文本同理（它本身是 label 编辑入口）
- **本页没有 `colSpan` / `rowSpan`**（flex 布局，全目录 grep 零命中）。真实的对齐约束是 `.colAssign` 那个 `flex:0 0 40px` + `position:sticky` 的占位外壳——只读时**保留外壳、只隐藏内部 `AssignBtn`**，删掉外壳会让表头与行错开 40px 且 sticky 首列吸附失效。Select Date 隐藏后行高由 `.metricLeft` 的 `min-height:48px` 兜住，`NO DATE` 徽标保留

**入口分支**：只读分支必须在 mount effect **最前面 `return`**，不执行后续任何逻辑。特别是那句 `if (stepParam === '2') history.replace('?id=...&step=1')` ——它只带 `id`、**会把 `taskId` 从 URL 抹掉**，之后刷新就掉出只读模式并被弹回 `/Finance`。（同类只带 `id` 的 `replace` 还有 `goToVerifyStep` 与 Step2 Previous 两处；将来若放开 Step 2，这三处都要保留 `taskId`。）只读分支仍执行一次 `fileStore.clear()`（只是不消费内容）——它是模块级单例，同一 SPA 会话里先开 Import 弹窗再点详情会残留旧 payload。

**冻结清单**（每项给出实施坐标；行号以 2026-07-27 的 HEAD 为准，实施时以符号定位为主）：

| 位置 | 冻结内容 |
|---|---|
| `DataMappingPanel` — Assign | 三处 `AssignBtn`（~1153 / ~1346 / ~1397）+ `MetricSelectPanel` 选项落点 → `handleAssign`；`AssignHintFloater`（~1978）传 `null` 并跳过 `assignHintRowId` 计算；面板副标题的行动号召文案换只读文案 |
| `DataMappingPanel` — 日期 | 两处 `MonthPickerPopover`（~1087 / ~1138）+ 月份格 → `handleSaveDate` |
| `DataMappingPanel` — 单元格 | 四处 `EditableCell`（~1046 / ~1165 / ~1368 / ~1407）→ `handleEndEdit`（按上面的例外改纯展示） |
| `DataMappingPanel` — label | label input（~1024）→ `handleEndLabelEdit` |
| **`DataMappingPanel` — 自动降级（blocker）** | `useLayoutEffect`（~1471–1515）**挂载即自动改数据**：把合并行的 `editLgCategory` 改写成 `UNMAPPED`，触发条件只需 files 非空 + 多 tableId + 合并行命中 `hasPredictMonth`/`hasNullValue`，**不需要任何用户操作**。只读若不冻结，回放出的映射归属与库里不一致——正好破坏"看用户编辑痕迹"的排查价值。首行 `if (readonly) return;`（或只读时不传 `onRowEdit`，该 effect 已有 `!onRowEdit` 早退可复用） |
| `FileSelector` | kebab 菜单（Upload New Document / Replace / Delete）+ `handleMenuClick` + 隐藏 file input |
| `FileSelector` — 失败文件 | ⚠️ 该组件全链路只吃 `REVIEW_READY`（`readyFiles` 过滤后传给所有下游），`FILE_FAILED` 分支在当前数据流下是死代码。只读要么把文件集合改成 `REVIEW_READY + FILE_FAILED`（失败项不可选、只显示错误 Tooltip），要么明确记为已知限制"只读页看不到失败文件" |
| 页面 — Step 条 | 只渲染 `Data Mapping` 一步（Step 2 不可达，别显示走不到的步骤；箭头由 `index < length-1` 控制，只渲染第 1 步不会留孤立箭头） |
| 页面 — Cancel / Next | Next 隐藏；**Cancel 换成纯导航「Back to task list」**（`history.push('/devSupport/financialExtractTasks')`），不复用 `CancelConfirmModal`（含放弃任务语义） |
| **页面 — 失败弹窗（major）** | `FileProcessingErrorsModal` 的弹出是 **effect 驱动**（条件只有 `uploadStage === 'done'` + 有 `FILE_FAILED` 文件，只读端点必然回 FAILED 文件），不是用户点的。三个出口全不可用：Discard → `apiBatchDeleteFiles`（写）、Reupload → `removeFiles` + 跳 `/Finance`、Close → `exitOcrIfNoReadyFiles` → 跳 `/Finance`（把只读用户弹出 devSupport 落到公司端页面）。**必须在 effect 首句 `if (readonly) return;`**（连 `shownFailedIdsRef` / `setFailedModalVisible` 一起短路），且 `exitOcrIfNoReadyFiles` 在只读下不可调用 |
| 页面 — 不可达 Modal | 只读时不渲染 `UnmappedAccountsModal` / `CancelConfirmModal` / `FileProcessingErrorsModal`（不依赖"不可达"的隐式保证——它们当前是恒挂载的） |
| 只读横幅 | 作 `.ocrAnalysis` 的**第一个 flex 子项**插入（`flex-shrink:0`），不要放在 `.ocrPageWrap` 与 `.ocrAnalysis` 之间——后者会撑出双滚动条并裁掉底部内容 |
| **空态（major）** | `files` 全为 `FILE_FAILED` 或为空时，`hasExtractData` 为 false → 会渲染成空表头 + 一条孤立 banner + 左栏骨架条的半空壳页。生产流靠 `exitOcrIfNoReadyFiles` 跳走兜底，只读禁用了它 → **必须给整页空态**（如 `This task has no extractable data · Status: {status}`）并展示失败文件与错误原因 |

**不能调的后端写接口（9 个）**：`getUploadUrl` / `commitUpload` / `batchDeleteByIds` / `batchDelete` / `file/replace` / `uploadComplete` / **`files/verifyS3`**（语义只读但是 POST，随上传入口一并冻结）/ **`verify`**（名字像读，实际 `deleteAllByTaskId` 清空重写 conflict_record 并推进状态）/ `complete`。

**`useOCRData` 只读旁路（3 个 blocker 都在这里）**：

- **只读端点是一次性回放，不复用"等解析完"的轮询语义**：`success === true` 即 `setUploadStage('done')` + `stopPolling()`（`files` 空则落空态文案）。不这样做会无限轮询——`TERMINAL_POLL_STOP` 只有 6 个状态，其余 12 个一律 5 秒重试且无次数上限；而 `files` 来源是 `findByTaskIdAndDeletedFalse`，文件被全部软删的 `REVIEWING` 任务、以及 `DRAFT` 任务（列表不筛状态，会出现在列表里）`files` 恒空
- **`TERMINAL_POLL_STOP` 命中时的 `history.replace('/Finance')` 按模式分叉，不得删生产分支**：那个跳转是为修"back 导航回已完成 task 时空 files 被误当还在解析 → 无限轮询 → 页面卡 loading"加的（hook 内注释有记录）。给 `processFromTask` 加 `{ readonly: true }` 或给 `startPolling` 加 `onTerminalEmpty` 回调；只读走"`stopPolling` + `setUploadStage('done')` + 空态"，生产流原样
- 注意终态分支当前**没有** `setUploadStage('done')`：只去掉跳转会让 `isProcessing` 恒 true → skeleton + "Processing Document" 永久停留

**冲突解决记录：独立展示页（2026-07-28 由"已知限制"升级为交付项，用户要求）。** 背景：`listDataMappingNotes` 恒过滤 `resolution IN (OVERWRITE, SKIP)`，`CONFLICT_RESOLUTION` 状态任务（verify 已跑、用户未解决）的 `PENDING` 冲突在生产 notes 页一条都查不到；生产 Step 2 的 `ConflictPanel` 是"解决冲突"的交互组件、只读模式不可达。方案见 §6.5——**单独页面组件**，不复用 ConflictPanel。

### 6.5 冲突展示视图（只读 mapping 页内嵌 tab，2026-07-28 终版）

数据源：§5.2 的冲突记录接口（全量 resolution 含 `PENDING`）。**纯只读展示**，不做任何解决/编辑交互。

**形态演进**：初版做成 devSupport 独立路由页（`/devSupport/financialExtractTasks/conflicts?taskId=`，列表 Action + 横幅两处入口）；用户两轮修正后终版为——**只读 mapping 页内的视图切换（tab 语义）**，不走路由跳转；独立路由页与 `pages/devSupport/financialExtract/conflicts/` 目录**整体删除**（唯一入口没了，留着就是死路由）。

```
src/pages/financial/aiFinancialExtraction/components/
├── ConflictRecordsView.tsx            冲突展示视图（接 taskId prop；resolution 筛选 + 平铺表格 + 空态；hook 逻辑并入本文件，单消费者不另立）
└── ConflictRecordsView.less
```

- **视图状态机**：`readonlyView: 'mapping' | 'conflicts'`（仅 readonly 模式存在）。横幅按钮组随视图切换：mapping 视图 → `View conflicts` + `Open Agent Trace`；conflicts 视图 → `View data mapping` + `Open Agent Trace`。**只有 `Open Agent Trace` 是页面跳转**，其余均为组件切换（不改 URL）
- conflicts 视图渲染时**不渲染** Step 条与 mapping 主体（横幅以下整个主区域替换为 `ConflictRecordsView`）；横幅常驻（task id 上下文 + 切换按钮）
- **跨域纪律（§4.1）**：组件在 financial 域，**禁止 import devSupport 域任何共享物**（`IdNameCell`/`time.ts`/域 `constants.ts` 等）。resolvedBy 展示截断 id + Tooltip 全值（不做名称解析）；时间格式化内联（moment UTC→本地 + Tooltip 原始 UTC）；resolution Tag 配色在 View 文件内定义
- services 层 `fetchTaskConflicts` 等**保留不动**（financial 域页面 import services 合规）

**只读横幅直达按钮组（2026-07-28 终版）**：只读 mapping 页横幅（`Read-only view · Task {id}`）右侧两个**黄色按钮**（页面主按钮同款配色 `#F59F0A`/hover `#e3910d`，`gap: 24px`）：
- `View conflicts` ⇄ `View data mapping` → §6.5 内嵌视图切换（组件切换，非路由跳转）
- `Open Agent Trace` → 点击时经 `fetchTraceList({ taskId, limit: 1 })` 查该任务**最新一条** trace（`ai_trace.task_id` 软关联，后端 `ORDER BY started_at DESC`），直跳 `/devSupport/llm/agent-trace?traceId=`；查不到 trace 给 `message.info` 轻提示不跳、查询失败 `message.error`。初版跳 Trace Explorer 列表（`/devSupport/tracing?taskId=`），**已按用户指示改为直跳 agent-trace**——代价是多条 trace（重试）时只达最新一条，旧执行仍可从 Trace Explorer 手动按 taskId 筛。后端零改动（task_id 列/索引/接口筛选全现成）。
- 展示形态：**平铺表格**（每行一条冲突记录），不复刻 ConflictPanel 的指标×月份矩阵——那是为逐格解决冲突设计的交互 UI，排查场景平铺 + 排序更直接（YAGNI）
- 列：Metric（lgCategory）、Period（`{year}-{month}` 补零）、Mapped Value（`mappedOriginalValue` + `mappedCurrency`；Tooltip 显示换算值 `mappedValue`、基准币种 `existingCurrency` 与 `exchangeRate`）、Existing (LG) Value（`existingValue` + `existingCurrency`）、Resolution（Tag：`PENDING` 橙 / `OVERWRITE` 蓝 / `SKIP` 灰 / 脏值灰）、Note（截断 + Tooltip 全文）、Resolved By（截断 id + Tooltip）、Resolved At、Created At
- resolution 本地筛选下拉（前端过滤，数据量小不走服务端）+ 本地分页
- 空态：该任务无冲突记录时明确文案（"No conflict records for this task"，附说明：仅 verify 阶段检出差异才产生记录）；接口 `success=false` → 错误 Alert

## 7. 分期

| Phase | 内容 | 仓库 |
|---|---|---|
| 0 | 台账登记（§2.5 各条按归属写入三仓 `docs/待优化项.md`）——已完成（2026-07-27） | 三仓 |
| 1 | V019 加列+索引 / V020 回填（`end_type` only）+ `ExtractionTask` ORM 同步两列 ＋（§3.7-B 若采纳）`/lg/*` 三接口加鉴权 | CIOaas-python |
| 2 | `source/financial_extract/` 新域：列表接口 + 只读回放接口（§5.2，ACL / 权威 companyId / query_file_link）+ main.py 挂 router + tests | CIOaas-python |
| 3 | Entity 两字段 + `resolveOrCreateTask` 写快照（§5.1，不新增接口）＋（§3.7-A 若采纳）存量端点补 ACL | CIOaas-api |
| 4 | services financialExtract 域 + architecture.md §2 登记 + taskList 页面 + 路由 + 导航 + README | CIOaas-web |
| 5 | 上传页 taskId 深链 + readonly 贯穿（§6.4 冻结清单逐项） | CIOaas-web |

**Phase 1 的迁移必须在 Phase 3 的 Java 版本上线前跑完**（§3.3 的 `ddl-auto: update` 抢跑问题）。Phase 4 依赖 Phase 2 的接口契约（spec 已定死，可并行开发）；Phase 5 与 4 改不同文件、可并行。

## 8. 风险与已知限制

1. **`DataMappingPanel` 2196 行是 Phase 5 的主要风险面**。§6.4 已把写入口逐点列出（含那个挂载即改数据的 `useLayoutEffect`），实施时按清单逐项核对，不要凭"看起来只读了"收工。
2. **`end_type` / `organization_id` 对历史任务是近似值或 NULL**；`organization_id` 即便对新任务也只是"登录态主组织"、多组织用户不确定（§3.5）。口径写进列注释。**该列不参与鉴权**，标错只影响筛选结论。
3. **TIFF 预览当前对所有任务都失败**（既存缺陷，前端 `<img>` 带不上 JWT），不是只读页引入的；只读回放对 TIFF 直接置空 previewUrl（§5.2 第 5 条）。
4. ~~`CONFLICT_RESOLUTION` 任务的 PENDING 冲突不可见~~ **已解决（2026-07-28）**：独立冲突展示页（§6.5）+ Python conflicts 接口（§5.2）返回全量 resolution 含 PENDING。生产 `dataMappingNotes` 接口本身的局限（无 taskId、过滤 PENDING）仍在台账。
5. **只读页看不到 `FILE_FAILED` 文件**（除非按 §6.4 把 FileSelector 的集合放宽）。
6. **目录 options 接口是超管 only（Java `assertSuperAdmin`）**。管理端（company_id 空）按生态不变式即超管，名称解析可用；公司端用户能进页面（ACL 圈定本公司）但 options 会 403、解析不出名称，会看到裸 ID——与 chatManage 现状一致。
7. **只读深链的越权防线 100% 在后端 ACL**（Python 只读回放接口）：`/aIFinancialExtraction` 路由零 role 闸门，devSupport 的菜单闸门既不覆盖这个 URL、判据也在 localStorage（客户端可改）。
8. **`/devSettings` 两个 Tab 功能重复**，本次不动，已进台账。
9. **§3.7 两项范围决策未定**（默认不做）：若都不做，本页会把写越权的可利用面从"已知某个 taskId 的人"扩大到"所有能打开列表页的人"，且 Python `/lg/*` 裸接口仍在无鉴权全量吐清单。
10. **§3.6 的管理端放开依赖平台不变式**（"company_id 空 ⟺ roleType=1"），部署前跑一次验证 SQL；不变式破产属平台级问题、另行立项。
11. **previewUrl 逐文件经 Java `getFileLinkById` 取**，一个任务 N 个文件 = N 次内部 HTTP 调用（N≤20），本机 Java→RDS 慢时回放接口首包会慢；可接受（管理端排查页非高频路径）。
