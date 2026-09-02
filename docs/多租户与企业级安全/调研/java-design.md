# Java 端（CIOaas-api）：租户模型与隔离现状

> 关联文档: [决策摘要](./executive-summary.md) | [设计理念](./design-philosophy.md) | [系统架构](./system-architecture.md) | [Python 端](./python-design.md) | [前端](./frontend-design.md) | [证据代码](./code-examples.md)

技术栈实测：**JPA / Hibernate + Spring Data + MapStruct，无 MyBatis**（`@Mapper` 全部是 MapStruct）。路径以 `java/CIOaas-api/` 为根，`web/` 指 `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/`，`common/` 指 `gstdev-cioaas-common/src/main/java/com/gstdev/cioaas/common/`。

---

## 1. 租户层级实体

| 概念 | Entity 类 | 表名 | 主键列 | 关键外键 |
|---|---|---|---|---|
| Organization（租户所在层） | `Organization` | `organization` | `id` | `pid`（自嵌套） |
| Portfolio | `CompanyGroup` | `company_group` | `company_group_id` | `organization_id` |
| Company | **`Invite`**（类名与表名不一致） | `company` | `company_id` | **无组织列** |
| User | `User` | `public.user` | `user_id` | `company_id` |

`Organization` 全部业务字段见 `web/system/domain/Organization.java:17-40`：仅 `name` / `logo_url` / `website_url` / `code` / `pid` / `description`。**无 level / type / is_tenant / depth / root_id**。

`company` 表的实体叫 `Invite`（`web/system/domain/Invite.java:22-33`），API 路径至今是 `/invite/*`，而表注释写的是 `'Company/Portfolio.'`——**company / invite / portfolio 三重同名歧义**，是后续统一过滤时最易出错处。

`tenant` 一词在 CIOaas-api 的 `.java/.yml/.xml/.properties` 中命中 **11 处 / 6 个文件**，绝大多数与多租户无关（SharePoint 的 Azure AD tenant、Redis 缓存与 SQS 处理器中的泛用措辞）。**唯一一处真正指向租户层级的是注释而非代码**——`web/system/vo/organization/OrganizationOptionDto.java:9`：

> `tenant-level org — not the legacy per-company "organize" grouping`

即"组织树上存在租户级节点"这个概念**只以一行注释的形式存在过**，没有任何字段、类型或校验与之对应。

### 关系表（全部多对多，均无唯一约束）

`r_organization_company` / `r_organization_user` / `r_organization_role` / `r_organization_menu` / `r_company_group` / `r_portfolio_user` / `r_role_company` / `r_organize_user`。

---

## 2. 用户归属与角色

### 2.1 一个用户属于多个公司 = 同 email 多行 user

`User.companyId` 是单值列（`web/system/domain/User.java:118-119`），无用户↔公司中间表。组织归属与 Portfolio 归属在实体上是 `@Transient`（`User.java:160-169`），必须查 `r_organization_user`。

"一个人属于多个组织/公司"通过**同一 username 建多行 user** 实现（`web/system/repository/UserRepository.java:131-132`），切换 = 拿该行的 userId 重新走 `/oauth/token`。

### 2.2 三套互不对齐的角色机制

| 机制 | 位置 |
|---|---|
| `user.role_type`（int 粗分类） | `User.java:60-61`；枚举 `common/enums/RoleTypeEnum.java:3-8`（1 超管 / 2 公司管理员 / 3 项目管理员 / 4 成员 / 5 Product Owner） |
| `role` 表 + `r_user_role` | `web/system/domain/Role.java:19-64`（另有 `is_super_admin`、`role_key`、字符串型 `role_type`） |
| menu code 决定数据范围 | `web/system/service/CompanyGroupServiceImpl.java:105-120`，判断是否拥有 `seeAllPortfolio` |

代码自己承认三套不对齐：`UserRepository.java:267-269` 注释说明 `role_type=2` 仅做粗分类，真实管理员判定要查 `r_user_role` + 角色名。

**Portfolio Admin / PM 没有独立字段**，靠 `r_portfolio_user` + 角色类型 + 无 `seeAllPortfolio` 菜单码的组合推断（`UserRepository.java:234-265`）。

---

## 3. 认证与租户上下文

### 3.1 JWT 只有 userId

`common/security/jwt/JwtTokenProvider.java:56-70`：`Jwts.builder().subject(userId)` —— **没有 companyId / organizationId / roles 任何一个 claim**。

同文件 `:81-88` 有 `getOrganizationIdFromToken()` 读 `organization_id` claim，但**没有任何地方写这个 claim**，是死代码，永远返回 null。

### 3.2 租户信息在 Redis，但几乎没人读

`common/web/UserContext.java:8-15`：`id / username / organizationId / roles / companyId`。写入点 `web/oauth/controller/OAuthTokenController.java:163-173`（登录）与 `:231-241`（刷新），键 `auth:user:{userId}`，TTL 约 300 天（`web/oauth/store/UserInfoCache.java:32-36`）。

**全仓仅 2 处代码读取它**（`SecurityUtils.getPrincipal()` 的调用方）；`SecurityUtils.getOrganizationId()` 同样只有 2 个调用方（`web/index/service/impl/IndexValidationServiceImpl.java:229`、`web/scheduler/service/SchedulerServiceImpl.java:474`）。

缓存 miss 回源数据库时 **roles 直接置空**（`UserInfoCache.java:94`）。

### 3.3 网关不鉴权

`gstdev-cioaas-gateway` 只有 2 个 Java 文件；唯一的全局过滤器只打访问日志（`gateway/filter/LoggingGlobalFilter.java:26-38`）。CORS 在 `deploy/cioaas-gateway.yml:19-26` 全开且 `allow-credentials: true`。

唯一的 SecurityFilterChain 在 `common/security/config/CommonSecurityConfiguration.java:45-59`，只有 `anyRequest().authenticated()` —— **全局只有"登录/未登录"二态，无租户维度**。

### 3.4 「我在哪个组织」的三个 Java 实现

| 实现 | 位置 | 取法 |
|---|---|---|
| Redis 会话重建 | `UserRepository.java:209-210` | `SELECT organization_id FROM r_organization_user WHERE user_id = ?1 LIMIT 1`，**无 ORDER BY** |
| 登录期装配 | `web/oauth/service/UserDetailsServiceImpl.java:177-184` | `userOrganizations.get(0)` |
| `getCurrentOrganization()` | `CompanyGroupServiceImpl.java:78-103` | `organizationUsers.get(0)`；无组织关联时兜底 `rOrganizationCompanyList.get(0)`，**列表为空则直接数组越界**（`:94-95`） |

实体注释自己记录了这个问题：`web/ai/financial/extract/domain/AiFinancialExtractionTask.java:47-50` 写明"多组织用户的主组织由登录链路无序取一（LIMIT 1 无 ORDER BY），是不确定值"，并紧接着声明该字段"**不参与鉴权**，标错只影响筛选归因，勿据此做隔离"。

**团队已在台账中登记该问题**（`java/CIOaas-api/docs/待优化项.md`，2026-07-27）：条目原文指出两条路径可能挑出不同组织，并建议"定一个确定性排序（如按 organization.created_at 或 code）"。本调研的结论与之一致，但补充一点：**确定性排序只能消除随机性，不能解决"取到的不是租户那一级"**——租户级别需要第 0 步的显式标记列才能解决。

---

## 4. 数据访问层：无任何框架级隔离

### 4.1 逐项实测结果

| 机制 | 结果 |
|---|---|
| MyBatis TenantLineHandler | **不存在**（项目未引入 MyBatis） |
| Hibernate `@FilterDef` / `@Filter` | **零命中** |
| `@SQLRestriction` | 8 处，**全部是软删/归档过滤，与租户无关** |
| `StatementInspector` / SQL 改写 | **零命中** |
| MVC `HandlerInterceptor` | **零命中** |
| 全局切面 | 仅 2 处，无租户切面 |
| `@PreAuthorize` / `@PostAuthorize` / `@Secured` | **全仓 0 处**（`WebApplication.java:24` 开了 `@EnableMethodSecurity` 但无人使用） |
| 动态数据源 / schema 切换 | **零命中** |

通用查询构造器 `common/utils/QueryUtils.java:19-40` 也不注入任何租户条件。

### 4.2 实际隔离靠手写，且 ID 来自客户端

**典型形态**：`web/fi/controller/FinancialStatementsController.java:93-99` 的 `overview(String companyId)` —— `companyId` 直接来自 query param，方法体**只判空、不判归属**即交给 Service。同文件 `:85-91` / `:102-108` / `:110-116` 同一形状。代码见 [证据代码](./code-examples.md) §15.1。

85/150 个 Repository 含 `companyId` 条件，全部是手写谓词。

### 4.3 已有的对象级授权守卫（正面样板，可作为第 1 步的改造基准）

`UserService` 提供 **3 个**归属校验方法，均有生产调用方：

| 方法 | 位置 | 语义 |
|---|---|---|
| `findInaccessibleCompanies(userId, companyIds)` | `web/system/service/UserServiceImpl.java:1327` | 批量版，返回无权访问的公司 |
| `canAccessCompany(userId, companyId)` | `:1347` | 单个：`seeAllPortfolio` 全放行 → 直连 `company_id` → 经 Portfolio 可见 |
| `hasVisibleCompanyUnderGroup(userId, companyGroupId)` | `:1365` | Portfolio 维度 |

调用点共 **3 处**：

- `web/fi/service/PortfolioBenchmarkServiceImpl.java:86-95` `assertCompaniesAccessible()` → 由 `getSnapshot:102`、`getTrend:189` 调用，对应端点 `POST /portfolio-benchmark/snapshot`、`POST /portfolio-benchmark/trend`；**并有回归测试**（`src/test/.../PortfolioBenchmarkTrendGuardsTest.java`、`PortfolioBenchmarkTrendSourceFilterTest.java`）
- `web/fi/service/BenchmarkNotifyAlertServiceImpl.java:97`（Portfolio 维度）与 `:99`（公司维度）

**这是全仓仅有的、在请求期判定"这个调用者能不能看这行数据"的实现**，覆盖 3 个端点。它是第 1 步要推广到全站的模式，也是最贴合的工作量基准（见 [决策摘要](./executive-summary.md) §4）。

同一文件 `:80-83` 的注释还直接印证了 §6 的"`seeAll` 短路"结论：

> ⚠️ 口径继承：Group Manager 分支对任意 companyId 放开（既有语义写的是"本组织下所有公司"但未校验组织归属）。本守卫不扩大也不收窄它；要按组织收口得改 `canAccessCompany` 本身，那会影响它的全部调用方。

即团队已自认：**`seeAllPortfolio` 分支不校验组织归属，且收口需要改动决策链本身**——这正是第 1 步中 J-6 的成本来源。

### 4.4 多归属时取 `.get(0)`：排序口径与页面树不一致

`OrganizationRepository.java:50-51` 的 `findAllByCompanyId` **无 ORDER BY**，下游一律取 `.get(0)`：

| 消费点 | 影响 |
|---|---|
| `CompanyServiceImpl.java:2948-2957`（`overview`） | 用哪个组织的 `score_weight` 取决于数据库返回顺序 |
| `CompanyServiceImpl.java:3444-3447`（`benchmarks`） | 用哪个组织的 `score_level` 色带同理 |
| `web/di/service/KpaBusinessServiceImpl.java:396-404` | 决定 KPA 分类全集，直接影响"首次评审必须含全部分类"的校验 |
| `web/di/service/TechStackServiceImpl.java:123, 290` | 同类问题 |
| `CompanyServiceImpl.java:2534-2575`（`getAdminUserByCompanyId`） | 三个无序 `[0]` 互相比较 |

**排序口径与页面不一致（依赖未定义行为，非已确认线上错误）。**

预期语义是"取页面上显示的第一个组织"，而页面组织树来自 `findByTreeInId:36-43`，它**带 `ORDER BY created_at`**；`findAllByCompanyId:50-51` 却**不带排序**。两者对齐没有保证，只是 PostgreSQL 对简单顺序扫描多半返回接近插入的顺序，才碰巧一致至今。执行计划变化、行被 UPDATE 后位置变动、VACUUM 之后都可能打破它。

**修法**：给 `findAllByCompanyId` 补 `ORDER BY created_at` 与页面对齐。业务规则已确认「一家公司可同时属于同租户下多个子组织」是**正常形态**，因此这条修完之后多归属完全良性——属当下的一致性修正，不必等多租户。

### 4.5 无租户条件的接口（第 0 档）

| 接口 | 位置 | 暴露内容 |
|---|---|---|
| `GET /invite/all` | `CompanyServiceImpl.java:301-316` | 全库公司。查询规格（`:1629-1654`）本身无一条身份谓词；上游 `queryAll()` 有一处身份分支，但那是**按硬编码邮箱判定的特例**（`:306`），决定返回 type=1 还是 type=2，不构成归属过滤 |
| `GET /invite/{id}` | `CompanyServiceImpl.java:509-533` | IDOR，枚举 id 拉任意公司详情（含组织列表、Portfolio 列表）。项目自己已登记：`docs/代码审查/2026-07-16-java-code-review-issues.md:104` |
| `GET /users/{userId}` | `UserServiceImpl.java:239-269` | 任意用户详情（组织、Portfolio、角色、加密后 pwd），无归属校验 |
| `GET /companyGroup/user?organizationId=` | `CompanyGroupServiceImpl.java:446-462` | 见 §5 反向倒挂 |
| 智能解析冲突**读**路径 | `web/ai/financial/extract/service/AiFinancialExtractionConflictServiceImpl.java:1231-1242` | 无 companyId 校验（写路径 `AiFinancialExtractionServiceImpl.java:771` 有）。已登记于 `docs/待优化项.md:13` |
| `LogServiceImpl.java:231` | — | 为做 id→名称映射执行 `userRepository.findAll()` 全表扫描 |

### 4.6 匿名端点（`@AnonymousAccess`，实测 15 处 + 硬编码 `/error`）

机制：`CommonSecurityConfiguration.java:43,53-55,82-86` 扫描注解路径注册 `permitAll`，并同时注册 `/api` 前缀变体。

风险最高的三个：

| 端点 | 位置 | 说明 |
|---|---|---|
| `GET /storage/files/inner/getFileLinkById` | `web/storage/controller/FileController.java:122-134` | 代码自陈：**当前完全无鉴权**，唯一屏障是 fileId 不可猜，任何拿到 fileId 者可换取 600 秒预签名 GET（全 files 表范围） |
| `GET /storage/files/read?fileNamePath=` | `FileController.java:52-63` | 任意对象 key 流式读取，当前**只告警不拦截** |
| `POST /users/sendEmailToReset` | `web/system/controller/UserController.java:363-364` | 无限流 → 邮件轰炸 / 账号枚举 |

其余：`/oauth/token`、`/actuator/health`、`/users/logout`、`/users/changePassword`、`/users/tokenIsExpired`、`/users/changePasswordWhenLogin`、`/users/get`（已收窄为只回 email）、QBO 回调与授权跳转、`/document/downLoadFileStream`、`/document/getShareDocument`、`/companyDocumentation/getSharedDocumentationList`。

> 文档陷阱：`AiFinancialExtractionController.java:114-118` 的 javadoc 声称某预览端点"无鉴权"，但该文件 `@AnonymousAccess` 实际计数为 0，javadoc 已过时。

---

## 5. 组织维度的越权面：39 个端点，归属校验 0 个

全量扫描 50 个 Controller。完整表格见 [证据代码](./code-examples.md) §3，此处列破坏力最高的：

| 端点 | 位置 | 效果 |
|---|---|---|
| `POST /score/saveScoreConfiguration` | `ScoreController.java:101-112` → `web/di/service/ScoreServiceImpl.java:1254-1269` | 先写传入组织，再 `findAll()` 遍历**全库每个 organization** 覆盖其权重。**单次调用改写所有租户评分口径** |
| `DELETE /organization?id=` | `OrganizationController.java:61-65` → `OrganizationServiceImpl.java:244-275` | 硬删任意组织及整棵子树 |
| `PUT /organization` | `OrganizationController.java:67-71` → `OrganizationServiceImpl.java:284-297` | 改 pid 任意搬家，**可造环**；重名校验用的是旧 pid（`:290`） |
| `PUT /organization/modifyOrganizationMenu` | `OrganizationController.java:73-78` → `OrganizationServiceImpl.java:320-326` | 重写任意组织菜单并级联撤销整棵子树及其角色的菜单 |
| `POST /users/adminUser` | `UserController.java:131-156` → `UserServiceImpl.java:474-486` | 先 `deleteAllByUserId` 再重挂 → **把已有任意用户搬迁到任意组织** |
| `PUT /users/{userId}` | `UserController.java:259-283` → `UserServiceImpl.java:857-868` | 同上 |
| `GET /organization/findByTree?ids=` | `OrganizationController.java:80-84` → `OrganizationServiceImpl.java:344-352` | **传 ids 则完全跳过归属推导**，返回对应组织完整子树 |
| `GET /organization/findAllSort` | `OrganizationController.java:37-41` → `OrganizationServiceImpl.java:167-181` | 全库所有组织 + 菜单授权矩阵 |
| `GET /companyGroup/{organizationId}` | `CompanyGroupController.java:87-91` | 任意组织全部 Portfolio，连 group-manager 判断都没有 |

### 两处反向权限倒挂

| 位置 | 行为 |
|---|---|
| `CompanyGroupServiceImpl.java:450-452` | 传入组织 ≠ 自己的组织时，**跳过** `r_portfolio_user` 过滤，返回该组织全部 Portfolio |
| `web/system/service/BusinessIssuesServiceImpl.java:414-586`（共 12 处分支） | 组织 ID 不等于当前组织时走 else 分支，**跳过** group-manager 与用户维度过滤 |

被内部代码消费：`IndexValidationServiceImpl.java:253-259` 展开子树后对每个子组织调前者，"传入 ≠ 当前"恒成立，实际拿到每个子组织的**全部** Portfolio，而注释声称行为与该接口一致。

---

## 6. 子树展开：能力在，但没用在授权链上

`OrganizationRepository.java:36-43` `findByTreeInId` 是标准递归 CTE。调用方 6 处：

| 调用点 | 用途 |
|---|---|
| `OrganizationServiceImpl.java:247` | 删组织需连带整棵子树 |
| `OrganizationServiceImpl.java:320` | 撤销菜单需级联子树及其角色 |
| `OrganizationServiceImpl.java:367` | 渲染组织树 |
| `ScoreServiceImpl.java:714` | SDP 排名分母 = 整棵子树下全部公司 |
| `ScoreServiceImpl.java:744` | benchmark 同侪集合 |
| `IndexValidationServiceImpl.java:245` | 指标校验公司筛选 |

另有 3 处等价递归 CTE：`CompanyRepository.java:61-75`（`/invite/getList`）、`ProjectRepository.java:69-79`（`/invite/query`）、`UserRepository.java:114-128`（`/users/query`）。

**授权链却不用它**——`CompanyGroupRepository.java:51-56` `findVisibleCompanies` 是 `cg.organization_id = :orgId` **等值不递归**，且 `seeAll = TRUE` 直接短路归属条件，**并且完全没有"调用者是否属于 orgId"的校验**（SQL 全文见 [证据代码](./code-examples.md) §3.2）。

### 本该展开却只做单层等值的位置

- **Portfolio 全线**：`CompanyGroupRepository.java:22-23`（调用方永远传单元素 list：`CompanyGroupServiceImpl.java:130-136` / `:431-433` / `:451-458`）、`:54` `findVisibleCompanies`、`:31-32` 重名校验（父子组织可有同名 Portfolio）
- **确定的 bug**：`CompanyRepository.java:77-78` 等值版本被用在 `CompanyServiceImpl.java:2719` `saveAllCompanyScoreByOrganizationId`（由 `TechStackManagementServiceImpl.java:376` 调用）→ **改父组织技术栈权重后子组织公司分数不重算**
- **DI 配置表全线**：stage / score_weight / score_level / kpa_category / tech_stack_layer 各自等值查询，每个组织节点各持一份独立配置
- **`business_issues` 全线**：`BusinessIssuesServiceImpl.java` 中 24 处 `findAllByOrganizationId*`（12 个派生方法 × if/else 两分支）
- **用户按组织**：`CompanyServiceImpl.java:2554` 只取直连组织成员

---

## 7. 权限 / RBAC

表结构完整（`role` / `menu` / `r_user_role` / `r_user_menu` / `r_role_menu` / `r_organization_role` / `r_organization_menu` / `r_role_company` / `subscription_template` / `r_subscription_menu`），但**没有任何声明式鉴权落地**。

- 权限工具类 `web/config/PermissionConfiguration.java:17-40`（bean 名 `rc`）**零调用方**（`@rc.check(...)` 全仓 0 命中）
- 权限串装配 `web/system/service/RoleServiceImpl.java:426-450` 只在签发令牌时使用，之后 `JwtAuthenticationFilter.java:43` 把 authorities 置空、`UserInfoCache.java:94` 回源时 roles 置空
- 实际生效仅两处硬编码：`web/system/util/DirectoryQueryUtils.java:30-35` 超管断言（挂 3 个 `/options` 端点）与 `CompanyGroupServiceImpl.java:105-120` 的 `seeAllPortfolio` 判断
- 另有约 70 处散落的 `getRoleType()` 硬编码分支，无统一抽象
- `dataScope` 字段仅在一个 DTO 上出现（`web/system/contract/role/RoleSmallDto.java:16`），实体无对应列，是遗留字段

---

## 8. 数据库连接

单数据源、单 schema、全租户共享。`deploy/cioaas-web-prod.yml:46-48` 指向单一 JDBC URL；表实体统一 `schema = "public"` 或默认。

无 `AbstractRoutingDataSource` / 动态数据源 / schema 切换（零命中）。`web/datasource/` 下唯一文件是忽略外键异常的处理器。

⚠️ `deploy/cioaas-web.yml:43`、`cioaas-web-staging.yml:43`、`cioaas-web-prod.yml:43` 三份配置均为 `hibernate.ddl-auto: update` —— **生产表结构由实体自动演进**。这是多 schema / RLS 方案的直接阻碍。

历史上曾有 PG + Redshift 双源（`deploy/nacos/backup/cioaas-web-20260311-170406.yml:54-63`），是 ETL 时代的分析库，非租户维度，现已随 ETL 模块下线。

---

## 9. 审计

### 9.1 行级审计基类（有）

`common/persistence/AbstractCustomEntity.java:23-60`（无 `@Id`，实体自定义主键列名）与 `AbstractAuditingEntity.java:23-50`（带统一 `@Id`），均提供 `created_at / created_by / updated_at / updated_by`，通过 `@PrePersist` / `@PreUpdate` 自动填充。

例外：`ROrganizeUser.java:16`、`AiFinancialExtractionTask.java:28`、`AiFileRegistry.java:51` 不继承基类。

### 9.2 操作审计（表在，写入链路已断）

`web/logging/domain/Log.java:15-58` 定义 `log` 表，含 `company_id` / `userId` / `request_ip` / `params` 等；`deploy/upgrade_doc/sprint105/V1__table_comments.sql:64` 的表注释写明 `'Application log. Audit trail.'`。

**唯一写入方被禁用**——`web/logging/aspect/LogAspect.java:23`：

> `// @Component  // Disabled: audit logging not needed currently, and the hard cast to Result causes ClassCastException for OpenFeign endpoints`

它是唯一调用 `logService.save(...)` 的地方（`:78`），因此 `log` 表**无写入方**；16 个 Controller 上约 116 处 `@Log` 注解全部失效。读接口 `web/logging/controller/LogController.java:26` 仍在查一张不增长的表；其查询条件 `companyId` 没有 `@Query` 注解，不参与谓词生成。

切点原本也只覆盖 2 个包（`LogAspect.java:34-35`），不含 fi / storage / oauth / quickbooks。

项目已列为待决策项：`docs/代码审查/2026-07-16-java-code-review-issues.md:81`。

### 9.3 登录日志（无独立表）

`User.java:79-89,156-158` 有 `last_login_date` / `last_login_ip` / `last_login_location` / `login_fail_times` / `login_date`，但：

- 实际只写 2 个字段且是覆盖式滚动（`UserServiceImpl.java:1152-1162`），只留最近两次
- `lastLoginIp` / `lastLoginLocation` / `loginFailTimes` **全仓零 setter 调用** → 无 IP 留痕、无失败计数、无锁定机制
- 失败登录只落应用日志文本，不入库（`OAuthTokenController.java:183`）

### 9.4 数据变更留痕（各域自建）

`score_log` / `quickbooks_data_change` / `financial_forecast_history` / `financial_forecast_alert_record` / `financial_benchmark_*_history` / `quickbooks_*_log` / `queue_message_log` / `ai_financial_extraction_conflict_record` / `company_index_verify*` —— 均带 `company_id`，但彼此独立、无统一规范。

---

## 10. 会话与凭据

| 项 | 现状 |
|---|---|
| 认证方式 | 自研 OAuth2 password-grant 外观 + HS256 JWT + Redis 撤销表；`client_secret` 可空（`OAuthTokenController.java:278-300`） |
| access token TTL | **约 300 天**（`OAuthTokenController.java:66-67`） |
| refresh token TTL | **约 300 天**（`:69-70`） |
| 刷新 | 有，旧 refresh 轮换销毁（`:192-254`） |
| 注销 | 有（`UserController.java:331-343`） |
| 并发登录控制 | **无**。Redis key 按 token hash 建，同一 userId 可有无限并发 token |
| 改密后旧 token 失效 | **无**。改密路径不清 Redis |
| MFA / SSO / SAML / OIDC | **全仓零命中** |
| 密码复杂度 / 过期 / 历史 / 锁定 | **全部无** |
| 密码哈希 | BCrypt（`web/oauth/config/WebSecurityConfiguration.java:49-51`） |

项目自己已记录 token 隐患：`docs/代码审查/token-会话撤销加固方案.md`（文档明确"只是方案，未改代码"）。

### 两条阻断项

1. **`user.pwd` 可逆口令副本**：明文直存（`UserServiceImpl.java:708`、`:1557`）或 AES-ECB 加密（`:1704-1712`），密钥硬编码在 `web/system/enums/PasswordSecretKeyEnum.java`。解密后经 Base64 回吐给浏览器（`:1410-1417`、`:1437-1445`、`:1753-1785`）。其中 `getOrganizationStatusByUserEmail`（`OrganizationController.java:86-90`）**需要登录但零授权校验**，且查询条件为 `role_type = 1`（`UserRepository.java:135-136`），即**专门返回超级管理员账号的口令**。

2. **生产 JWT 密钥为默认占位串**：`deploy/cioaas-web-prod.yml:103` 的 `jwt.secret` 与 `common/security/jwt/JwtTokenProvider.java:30` 的默认值完全一致，而该配置文件被 git 跟踪（同文件另含数据库密码、AWS 长期密钥、Stripe 生产私钥）。`JwtTokenProvider.java:40-46` 只校验密钥长度，不校验是否为默认值。

---

## 11. Java 侧缺口清单（以 organization 为租户）

| # | 缺口 | 优先级 |
|---|---|---|
| J-1 | `Organization` 无租户标记列，租户不可查询 | 第 0 步 |
| J-2 | 三个"取哪一级"实现互不相同且均为无序取一 | 第 0 步 |
| J-3 | 39 个接口接受 `organizationId`，0 个校验归属 | 第 1 步 |
| J-4 | 2 处反向权限倒挂 | 第 1 步 |
| J-5 | 授权链等值不递归，与展示层子树口径错配 | 第 1 步 |
| J-6 | 「`company_id` 为空 ⟺ 超管」不变式与租户管理员冲突 | 第 1 步 |
| J-7 | 两条 org→company 路径不同步、无租户一致性约束、`findAllByCompanyId` 排序口径与页面树不一致 | 第 1 步（排序一条可当下单独修） |
| J-8 | 组织创建/删除/搬家均无权限校验；删除级联严重不全；搬家可造环 | 第 1 步 |
| J-9 | 无框架级过滤机制（第 3 档缺失） | 第 2 步 |
| J-10 | 操作审计写入链路已断；无登录日志 | 第 1 步（SOC 2 阻塞） |
| J-11 | 生产 `ddl-auto: update` | 第 2 步 |
| J-12 | 令牌 TTL 约 300 天、无并发控制、改密不失效 | 第 1 步 |
| J-13 | 可逆口令副本 + 无授权的口令回吐接口 | **优先项（阻断）** |
| J-14 | 生产 JWT 密钥为默认占位串且配置在 git 中 | **优先项（阻断）** |
