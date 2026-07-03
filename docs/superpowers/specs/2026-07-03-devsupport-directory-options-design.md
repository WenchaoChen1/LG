> 关联文档: [Dev Support 权限门控设计](./2026-06-15-dev-support-permission-gating-design.md)、[AI Chatbot 设计](../../AI-Chatbot/设计/design-doc.md)、[Tracing 开发设计 §15.2 filter-options](../../tracing/dev-design-doc.md)

# devSupport 统一目录查询接口（用户 / 公司 / 组织 名称+ID）— 设计文档

**日期**: 2026-07-03
**范围**: CIOaas-api（新增 3 个轻量查询端点）+ CIOaas-web（共享选择器组件 + devSupport 各页面接入）；CIOaas-python 仅 P2 跟进项（换源），本期零改动
**一句话**: 新增 `GET /api/web/directory/{users|companies|organizations}` 三个轻量「名称+ID」目录端点，前端封装统一的搜索式选择器组件，替换 devSupport 全部子页面的手填 ID 筛选。

---

## 1. 背景与目标

devSupport（`/devSupport/*`，管理端专属控制台）下 22 个子页面普遍需要按 **用户 / 公司 / 组织** 查询与筛选，但目前没有任何一个统一的「名称+ID」数据源接口，各页面各自凑合：

| 页面域 | 现状 | 证据 |
|---|---|---|
| chatManage | Company / User / Organization **三个 ID 精确输入框**（手填 UUID） | `CIOaas-web/src/pages/ai/chatManage/index.tsx:264-303` |
| LLM 全域（9 页） | Company ID / User ID **手填输入框**，DTO 连 organizationId 都没有 | `llm/components/FilterToolbar.tsx:201-221`、`AnalyticsFilterBar.tsx:135-148`、`services/api/llm/llmDto.ts:36-37` |
| Tracing | 唯一做了下拉，但候选值 = `ai_trace` 表 **distinct 裸 ID**（`GET /api/ai/traces/filter-options`），公司名靠 chat 域 `fetchCompanies` 二次增强、组织只有裸 ID、没出现过的公司/组织选不到 | `ai/tracing/TraceList/index.tsx:274-295`、`hooks/useTraceFilterOptions.ts` |
| RAG binding | ownerId 裸 Input，代码里留有明确 TODO「接入公司/用户选择器替换裸 Input」 | `ai/rag/binding/index.tsx:38-40、242-253` |
| chat / chatSimulate | CompanyPicker 走 `/api/ai/chat/companies`（上游 `/invite/query`，见 §2.3 的坑） | `ai/chat/components/CompanyPicker.tsx:14-34` |

**目标**：
1. 提供三个轻量、快速、口径统一的目录查询端点，返回 `id + 名称（+ 少量辅助显示字段）`；
2. 前端封装一个共享的搜索式选择器组件，devSupport 所有子页面（及后续新页面）统一接入；
3. 保留「直接粘 ID」的现有工作流（管理员经常拿着 UUID 来查），选择器降级可手输；
4. 顺带治理历史坑：公司列表三个口径不一的来源、`/invite/query` 超时（§2.3）。

**非目标**：不做按公司/组织的数据权限过滤（devSupport 是管理端控制台，见 §4.4 鉴权）；不做缓存层与全文索引（量级不需要，YAGNI）；不动 tracing `filter-options`（保留兼容，见 §8）。

---

## 2. 现状调研结论（三端事实）

### 2.1 数据模型（主数据全在 Java 业务库，Java system 域）

| 实体 | 表 | 关键字段 | 证据 |
|---|---|---|---|
| 用户 `User` | `public.user` | `user_id`(36) / `username`(120) / `displayName`(600, **label 首选**) / `email` / `roleType`(1超管 2公司管理 3项目管理 4成员，枚举 `RoleTypeEnum`) / `companyId`(归属公司，**直接外键无中间表**) / `is_deleted` / `status` | `CIOaas-api/.../system/domain/User.java:23-130` |
| 公司 `Invite`（实体名是 Invite，映射表 `company`） | `company` | `company_id`(36) / `company`→列 `company_name`(120, **公司名 label 首选**) / `displayName`(255，语义偏被邀请管理员显示名，仅辅助) / `status`(1 resolve / 2 pend / 3 reject / 4 pending activation) / `companyStatus`(`CompanyStatusEnum`) / `archived`(软删标记，**不是 is_deleted**) / `type`(默认1) | `system/domain/Invite.java:22-129`（同表另有 legacy 备份类 `InviteBak`，勿用） |
| 组织 `Organization` | `organization` | `id`(审计基类) / `name`(120, not null, **label**) / `code` / `pid`(树形) / **无软删除** | `system/domain/Organization.java:18-37` |
| 关联 | `r_organization_user` / `r_organization_company` | 用户-组织、公司-组织多对多；`User.organizationId` 是 `@Transient` 不落表 | `system/domain/ROrganizationUser.java` 等 |

> ⚠️ 易混淆：另有 `Organize`（表 `organize`，`system/domain/Organize.java:18-28`）是**公司内用户分组**（legacy，归属 company_id），不是租户级「组织」。devSupport 各表的 `organization_id`（Redis 会话 `UserInfoCache` 与 `SecurityUtils.getOrganizationId()` 同源）对应的是 **`organization` 表**，目录接口只查它。

Python 侧相关表（`ai_chatbot_thread` / `ai_trace` / `ai_llm_call_log` / rag binding）**全部只存 UUID、无名称冗余**；管理端链路 `company_id` 恒 NULL、靠 `organization_id`（`tracing/domain/models/trace_model.py:33-46`）——所以组织维度筛选是刚需，不是锦上添花。

### 2.2 Python 侧拿不到用户/组织主数据（关键约束）

- Redis `auth_store` 只能按 key 单查活跃会话，无法列举（`common/redis/auth_store.py:88-98`）；
- `lgpi_api` 12 个客户端里只有「公司列表」（`/invite/query`）和「当前登录用户」，**没有用户列表、没有组织列表**；
- 共享 PG 的 Python ORM 只读映射了 `company` 表部分列（不含名称），**完全没有 user / organization 表映射**（`lg/db/models/models.py:395-416`）。

结论：想给前端供「用户/组织 名称+ID」，**必须在 Java 端出接口**——这也是本方案把落点放 Java 的决定性理由。

### 2.3 Java 现有接口为什么一个都不能直接用

| 端点 | 问题 | 证据 |
|---|---|---|
| `GET /invite/query` | 名字叫 query company，**实际返回 `List<ProjectDto>`（项目维度）**；N+1 已定位：`findByProjectId` 对每个可见项目循环触发 3 次 DB（LAZY `project.getInvite()` + techStack + document），约 **3×N 条 SQL**，超管可见数百项目 → 本机 >30s 超时的根源。Python `/companies` 正在用它 | `CompanyController.java:75` → `CompanyServiceImpl.findByProjectId:371-439`（循环体 `:414-436`） |
| `GET /invite/getList` | 页面业务接口：score / stage / scoreLog 多轮聚合；有两处 NPE（`getHasSetStage()` 拆箱 `:2191`、空列表 `get(0)` `:2148`） | `CompanyServiceImpl.java:609-625` |
| `GET /invite/portfolio` | 强制要求 portfolio group 入参；且与 getList 共享崩溃点 `startWithLetter`（`companyName.charAt(0)` 对 null NPE，`:1653-1657`） | `CompanyController.java:86-93` |
| `GET /invite/all` | 相对最轻（已做批量 stage 优化），但仍返回全量 `InviteDto` 重对象 + stage 联查，且无 keyword | `CompanyServiceImpl.java:281-321` |
| `GET /users/query` | 已有名称模糊！但作用域**绑定当前用户所属组织**（未传 organizationId 时按调用者的组织圈定）、含 `super@gstdemo.com` 特判、经全量 `userMapper.toDto`（`UserDto` 约 95 字段，懒加载 roles/menus 触发 N+1 风险）后再内存过滤 status | `UserController.java:95-107`、`UserServiceImpl.java:213-238` |
| `GET /users/all1` / `GET /users/company/{id}/members` | 前者一次拉 2000 条全量重 DTO；后者循环内每用户查 count（N+1） | `UserController.java:88-93`、`:484` |
| `GET /organization/findAllSort` / `/findByTree` | **findAllSort 禁止用作下拉数据源**：内部递归建菜单树，严重 N+1；findByTree 树形中重。服务层已有轻量 `getOrganizationListByUserId`→`OrganizationDisplayDto`（`OrganizationServiceImpl.java:515`）但无 Controller 暴露 | `OrganizationController.java:35-45、78` |
| `GET /colleague/companies/options` / `/select-options` | **唯一的轻量 options 先例**（`CompanyOptionDto` 仅 6 字段），体量理想；但强绑定 colleague 语义（只返回 active 公司 + 掺 `inColleagueGroup/eligibleAsPeer` 标记），不宜直接复用端点，**DTO 形态可参考** | `ColleagueCompanyController.java:30、51` |

共性：**全是为特定页面业务而生的重接口**，没有一个通用「轻量目录」语义的端点。前端因此出现三个口径不一的公司列表来源（`/api/ai/chat/companies`、`/api/web/invite/query`、`/api/web/indicator/validation/filter/company`），用户/组织则完全没有名称数据源。

### 2.4 前端基础设施（复用现状，零新增依赖）

- `/api/web/**` → Java 网关（9000）→ Web(5213)；`/api/ai/**` → Python（prod 也经 Java 网关反代）。两者**共用同一 umi-request 实例**，拦截器统一注入 Bearer token（`utils/request.ts:79-98`、`config/proxy.ts:9-25`）——devSupport 页面直调 `/api/web` 无任何障碍（normalizationTracing 等页面已在这么做）。
- 现有三套选择器（CompanyPicker / Tracing 内联 Select / MultiSelectDropdown）全是「一次全量拉取 + 客户端过滤」，**全项目没有防抖服务端搜索选择器**。

---

## 3. 方案选型

| 方案 | 说明 | 结论 |
|---|---|---|
| **A. Java 新增统一目录端点，前端直调 `/api/web/directory/*`** | 主数据单表直查，天然轻量；用户/组织数据只有 Java 有（§2.2）；前端已具备直调 Java 的全部基础设施（§2.4）；顺带给 Python chatbot `/companies` 提供换源目标，治掉超时根因 | ✅ **推荐** |
| B. Python 新增接口直查共享业务库 | Java 零改动、跳数最少；但要在 Python 侧新映射 `user`（含 password 等敏感列的表）/`organization`，跨系统 schema 耦合加深；且与「chatbot 域业务数据经 Java 网关」的既有约定相悖，目录主数据的对外口径旁落 Python | ❌ 备选。仅当 Java 侧确实无法排期时临时采用 |
| C. Python 新增接口、内部回调 Java | Python 没有可回调的合适端点（§2.3），Java 依然要新增端点——那前端直调 Java 即可，Python 中转纯属多一跳、多一个故障点 | ❌ 排除 |
| D. 前端拼凑现有接口 | 公司勉强可用（口径混乱），用户/组织无解；治标不治本 | ❌ 排除 |

选 A 的另一个长期收益：**公司列表口径收敛**。现有三个公司列表来源可逐步统一到 `directory/companies`（本期只接 devSupport，不动存量页面）。

---

## 4. 接口设计（Java, gstdev-cioaas-web, system 域）

### 4.1 端点契约

三个端点，统一入参与响应形态（REST：路径小写、资源复数，`standards/coding.md §1`）：

```
GET /directory/users?keyword=&limit=            （前端完整路径 /api/web/directory/users）
GET /directory/companies?keyword=&limit=
GET /directory/organizations?keyword=&limit=
```

**入参**（`DirectoryQueryRequest`，JSR-380 校验）：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | String | 否 | 名称模糊匹配（不区分大小写）。空 = 返回前 `limit` 条（小目录全量场景） |
| `limit` | Integer | 否 | 默认 100，服务端钳制上限 500，防无界返回（`standards/coding.md §10` 精神；选择器场景不翻页，keyword 负责收窄结果，故用 limit 而非 Pageable） |

**响应**：`Result<List<XxxOptionDto>>`（system 域 contract 惯例的 Dto 后缀，同 `CompanyOptionDto` 先例），信封 `{success, code, message, data}`，空列表 `[]`。三个独立 Dto（不做万能实体），公共契约是 `id + name`，辅助字段按类型：

```jsonc
// GET /directory/users —— UserOptionDto
{ "id": "u-uuid", "name": "Zhang San",            // name = displayName，空则回退 username
  "email": "zs@x.com", "roleType": 2 }             // email 供重名区分；roleType 供前端标注 Admin/Member

// GET /directory/companies —— CompanyOptionDto（directory 包下新建，与 colleague 包下同名类互不影响）
{ "id": "c-uuid", "name": "Acme Inc",              // name = company_name（公司名 label 首选，§2.1）
  "status": 1 }                                     // 透出让前端标注/禁用（参考 benchmark 选择器禁用 Exited/Shutdown 的先例）

// GET /directory/organizations —— OrganizationOptionDto
{ "id": "o-uuid", "name": "LG Portfolio", "code": "LG" }   // 查 organization 表（勿混淆 legacy 的 organize 分组表）
```

### 4.2 查询口径（每条一句理由）

| 端点 | WHERE 口径 | 匹配列 | 排序 |
|---|---|---|---|
| users | `is_deleted = false AND status IN (ENABLED, INVITED)`（对齐现网 `/users/query` 的 status 过滤口径，`UserServiceImpl.java:236`）；**不筛 roleType**——devSupport 查的是全体用户（客户端用户为主）的会话/调用 | `displayName` / `username` / `email` 任一 ILIKE | `displayName` 升序 |
| companies | `archived = false AND type = 1`（对齐 `queryAll` 普通用户口径，`CompanyServiceImpl.java:293`；注意公司软删标记是 `archived` 不是 `is_deleted`）；**不筛 status**，透出交前端标注——管理端要能筛到 pending 公司的数据 | `company_name` / `displayName` 任一 ILIKE | `company_name` 升序（注意 null 安全，勿重蹈 `startWithLetter` 的 `charAt(0)` NPE） |
| organizations | 无过滤（organization 表量级为几十，树形 `pid` 不下发——选择器要平铺列表） | `name` ILIKE | `name` 升序 |

开发时需二次确认的口径（不在文档拍死）：company 表另有 `company_status` 列（`CompanyStatusEnum`），与 `status` 并存，具体透出哪个/是否都透出，开发时对齐 `queryAll` 现状后定。

### 4.3 性能红线（本接口存在的意义就是快）

1. **JPQL 构造器投影单条 SQL**（`select new ...UserOptionDto(u.id, u.displayName, u.email) from User u where ...`），**禁止复用现有 `userMapper` / `companyMapper` 全量 DTO 映射**——那是 `/users/query`、`/invite/*` 慢的病灶（懒加载 roles/menus/stage 触发 N+1，`standards/coding.md §10`「禁止循环 findById」同源）；
2. 单表、无 JOIN、无后置内存聚合；
3. 不加新索引：用户（千级）/公司（百级）/组织（十级）量级下 ILIKE 顺序扫描毫秒级，业务库保持干净（YAGNI；未来量级上来再议 trigram）。

预期：即便本机连远程 RDS（历史上 `/invite/query` 超 30s 的环境），单条投影 SQL 也在数十毫秒级——历史超时的根因是 N+1 次往返，不是单次网络延迟。

### 4.4 鉴权

- 与全站一致的 JWT 登录校验自动生效（`CommonSecurityConfiguration` `anyRequest().authenticated()`，不加 `@AnonymousAccess` 即需登录）。
- **额外加超管守卫**：目录接口会枚举全量用户名+邮箱/公司名/组织名，对公司端用户属于敏感面。devSupport 管理端登录强制 roleType==1（[权限门控设计 §4](./2026-06-15-dev-support-permission-gating-design.md)），守卫不会误伤任何合法调用方。实现要点（来自现状核查）：
  - **roleType 既不在 JWT 也不在 Redis 会话里**（JWT 只承载 userId，`JwtAuthenticationFilter.java:39-45`；`UserInfoCache` value 无 roleType），必须回库查 `User.roleType`——用现成助手 `UserServiceImpl.getUser()`（`:1310-1316`），判定对齐 `RoleTypeEnum.SUPER_ADMIN`（值=1，`RoleTypeEnum.java:3-8`），范例 `CompanyServiceImpl.isAdminRole()`（`:1011`）；
  - 项目虽开了 `@EnableMethodSecurity`，但全仓 `@PreAuthorize` 零使用（死代码），**不引入注解式权限**——service 入口手写守卫，非超管抛 `BadRequestException`，交 `GlobalExceptionHandler` 兜底（Controller 不 try-catch）；
  - 守卫回库查一次 user 是每次请求 +1 条主键查询，目录接口低频（选择器打开/搜索时），可接受。
- 说明：全项目现状无 API 级角色控制（门控在前端），这是首个从严起步的新增接口；若团队决定保持全站现状（仅登录），删掉守卫即可，风险自担（用户目录枚举）。

### 4.5 代码落点（就近落 system 域——数据与可复用 service 都在这；另起 DDD 标准域会因跨域只能调 `application/service` 而与 system 的 legacy `service/` 冲突违规）

system 域是 legacy 平铺布局（`controller/` + `service/` + `repository/` + `domain/` + `contract/`(DTO/VO 混承)），新代码随域不新造层级：

| 类 | 位置 | 说明 |
|---|---|---|
| `DirectoryController`（`@RequestMapping("/directory")`） | `web/system/controller/` | 三个 `@GetMapping` + 入口超管守卫，只做参数校验 + service 调用；`@Tag`/`@Operation` 按 standards |
| `DirectoryService` / `DirectoryServiceImpl` | `web/system/service/` | 三个查询方法 + 守卫逻辑 |
| `DirectoryQueryRequest` / `UserOptionDto` / `CompanyOptionDto` / `OrganizationOptionDto` | `web/system/contract/directory/` | 随 system 域惯例放 `contract/`（同 `ColleagueCompanyController` 的 `CompanyOptionDto` 先例）；类命名带语义后缀，JSR-380 注解齐全 |
| 查询实现 | 复用现有 `UserRepository` / `CompanyRepository` / `OrganizationRepository` 各加一个 `@Query` DTO 构造器投影方法 | 单表、绑定参数（禁拼接，standards §9）、不新建 repository |

路径推导（网关 `Path=/api/web/**` + `StripPrefix=1` → web 服务 `context-path=/web`，`deploy/cioaas-gateway.yml:27-39`）：`@RequestMapping("/directory")` → 前端完整路径 **`/api/web/directory/*`**，网关零配置。

> 命名说明：Controller 取中性名 `Directory`（而非 DevSupportQuery），因为 §3 的长期目标是把全站公司列表口径收敛到这套端点；当前的超管守卫已由 §4.4 表达使用边界，未来若要放开给客户端页面，另行评估守卫策略即可，URL 不用改。

---

## 5. 前端设计（CIOaas-web）

### 5.1 services 层（按 chat/tracing 域现状两层结构）

- `services/api/directory/directoryApi.ts`：`fetchUserOptions(params)` / `fetchCompanyOptions(params)` / `fetchOrgOptions(params)`，GET `/api/web/directory/*`；
- `services/service/directory/directoryService.ts`：解 `Result` 信封、类型出口（`DirectoryOption` 联合类型）。

### 5.2 共享组件 `src/pages/ai/_shared/DirectorySelect/`

放 `_shared/`（devSupport 共享组件先例：`_shared/MarkdownView`）。核心行为：

| 行为 | 设计 | 理由 |
|---|---|---|
| 搜索模式 | **用户**：300ms 防抖服务端搜索（keyword→接口）；**公司/组织**：挂载时一次拉取（limit=500 视作全量）+ antd 客户端过滤 | 「小目录全量、大目录搜索」；公司/组织保持现有 CompanyPicker 的零延迟过滤体验 |
| 展示 | 选项 label = `name`，副行/后缀展示辅助字段（email / status 标注 / code）；选中值回填 `name (id前8位…)` | 对齐 tracing 现有 `name (id)` 习惯 |
| **ID 直填兼容** | 输入内容形如 UUID 或搜索无结果时，提供「Use as ID: xxx」选项直接提交输入值 | 保留管理员「拿着 UUID 来查」的现有工作流，替换输入框不能变成能力回退 |
| 降级 | 接口失败时组件退化为可输入状态（等价现状裸 Input），不阻塞页面 | 对齐 `/companies` 降级空列表、tracing label 增强失败退裸 id 的既有降级哲学 |
| 提交语义 | 对外 onChange 只吐 `id`（string） | 各页面既有查询参数（companyId/userId/organizationId）零改动 |

三个薄封装导出：`UserSelect` / `CompanySelect` / `OrganizationSelect`（传 type 与占位文案）。

### 5.3 页面接入清单（分两批，每批独立可验收）

**批 1（本期核心）**
| 页面 | 改动 |
|---|---|
| chatManage `ai/chatManage/index.tsx` | 三个 `Input.Search`（264-303 行）→ `UserSelect` / `CompanySelect` / `OrganizationSelect`；提交仍是 id，后端零改动 |
| tracing `ai/tracing/TraceList/index.tsx` | company/organization 两个 Select 换数据源到 DirectorySelect；`useTraceFilterOptions` 的「distinct + fetchCompanies 增强」逻辑整体删除（filter-options 接口本身保留，见 §8） |
| rag/binding `ai/rag/binding/index.tsx` | 兑现代码内 TODO：ownerId 按 ownerType 用 CompanySelect / UserSelect（playbook 维持 Input） |

**批 2（跟进）**
| 页面 | 改动 |
|---|---|
| LLM 域 `FilterToolbar` / `AnalyticsFilterBar` / `Dashboard` | company/user 输入框 → 选择器（llm 表无 org 维度，不加 org 筛选） |
| chatSimulate `CompanyPicker` | 数据源可切到 `directory/companies` 统一口径（可选；`/api/ai/chat/companies` 仍在客户端语义中使用，不强推） |

---

## 6. Python 端（本期零改动，P2 跟进项）

chatbot `company_service.accessible_companies` 超管分支当前经 lgpi_api 走 `/invite/query`（ProjectDto 重接口，本机超时 30s 的根源、`/companies` 降级空列表的直接原因）。新端点落地后：

- **P2**：`lgpi_api` 新增 `directory_companies_api.py`（一接口一文件约定），超管分支换源到 `GET /api/web/directory/companies`，公司端分支不动；`/companies` 的降级逻辑保留。
- 收益：chat 页公司选择器彻底摆脱超时；这是「治本」的最后一环，但不阻塞本期前端接入（devSupport 选择器直调 Java，不经 Python）。

---

## 7. 验证清单

1. Java 单测：三个查询各覆盖 keyword 命中 / 空 keyword / limit 钳制 / 口径过滤（deleted、archived、status）四类用例（`@DataJpaTest` + H2，standards §12）；非超管调用触发守卫异常的用例；`company_name` 为 null 的公司不致排序 NPE 的用例。
2. SQL 验证：确认三个端点各只发 1 条 SQL（开 `show_sql` 或 p6spy 观察，红线 §4.3）。
3. 本机连远程 RDS 实测响应时间（历史超时环境），预期 < 200ms。
4. 前端：DirectorySelect 单测（防抖触发、ID 直填选项、接口失败降级三态）；`npm run tsc`（注意存量 2 个坏文件基线）。
5. 手动回归：chatManage 用名称选人/司/组织后列表过滤正确；粘 UUID 直填仍可查；tracing 下拉能选到「从未出现在 trace 里」的公司（相对 distinct 方案的行为改进点）。

---

## 8. 兼容与迁移

- `GET /api/ai/traces/filter-options` **保留不删**（tracing 详情页等如仍有引用不受影响），前端 TraceList 不再调用；后续确认无消费方后另行下线。
- 现存三个公司列表来源（`/api/ai/chat/companies`、`/invite/query`、`/indicator/validation/filter/company`）**本期不动**，仅 devSupport 新组件统一走新口径；存量页面收敛是后续独立事项。
- 新端点是纯新增，无破坏性变更（standards §9「已发布接口禁止删字段/改类型」不适用）。

## 9. 影响文件清单（预估）

| 端 | 文件 | 改动 |
|---|---|---|
| Java | `system/controller/DirectoryController.java` | 新增 |
| Java | `system/service/DirectoryService(Impl).java`、`system/contract/directory/`（Request + 三个 OptionDto） | 新增 |
| Java | `UserRepository` / `CompanyRepository` / `OrganizationRepository` | 各 +1 个 `@Query` 投影方法 |
| Web | `services/api/directory/` + `services/service/directory/` | 新增 |
| Web | `pages/ai/_shared/DirectorySelect/` | 新增（含三个薄封装） |
| Web | `chatManage/index.tsx`、`tracing/TraceList/index.tsx`（含 `useTraceFilterOptions` 删除）、`rag/binding/index.tsx` | 批 1 替换 |
| Web | `llm/components/FilterToolbar.tsx`、`AnalyticsFilterBar.tsx`、`Dashboard.tsx` | 批 2 替换 |
| Python | `lgpi_api/directory_companies_api.py` + `company_service` 换源 | P2，另行排期 |
