# 前端（CIOaas-web）：租户上下文与权限现状

> 关联文档: [决策摘要](./executive-summary.md) | [设计理念](./design-philosophy.md) | [系统架构](./system-architecture.md) | [Java 端](./java-design.md) | [Python 端](./python-design.md) | [证据代码](./code-examples.md)

路径以 `web/CIOaas-web/src/` 为根。

---

## 1. 组织选择器：它是什么

产品截图中的组织树下拉（`Background development organization → Global Authority → Golden Section / paypal9 / google / …`）**不是全局 header 的租户切换器**——前端没有全局组织切换器。它是**页面级 antd `TreeSelect`**，表单里的标签叫 **"Portfolio Group"**（紧邻的 "Portfolio" 普通 Select 才是 `companyGroup`）。

同一份 `TreeSelect` + 递归渲染代码被**复制到 17 个活跃文件**（`<TreeSelect` 出现在 15 个文件，递归 `<TreeNode>` 渲染出现在 17 个），未抽公共组件。下表列主要几处：

| 页面 | 路由 | 行号 |
|---|---|---|
| `pages/portfolioCompanies/home/PortfolioCompaniesPage.tsx` | `/company` | 646-655（渲染函数 337-345） |
| `pages/companySettings/components/general/GeneralTab.tsx` | `/companySetting?active=1` | 511-520 |
| `pages/settings/userManage/detail/UserDetailPage.tsx` | 用户详情抽屉 | 561-571 |
| `pages/portfolioCompanies/addCompany/AddCompanyPage.tsx` | `/addCompany` | 542-550（渲染函数 216-222） |
| `pages/settings/portfolioManagement/PortfolioManagementPage.tsx` | `/portfolios` | 167-177 |
| `pages/settings/userManage/UserManagePage.tsx` | `/settings` | 148-162 |
| 另有 techStackManagement / sDPScore / qboLog / businessIssues / kPAConfiguration / devSupport-rolesManagement 各一处 | | |

### 数据源

全部来自 `GET /api/web/organization/findByTree`（**前端从不传参数**），返回以"当前用户直接关联的组织"为根的整棵子树数组。节点字段：`id / name / code / pid / subdata / menus / roles` —— **没有 `level`**。

同一个接口被写了 **5 份重复 service 函数**（`services/api/portfolioCompanies/portfolioService.ts:3-7`、`services/api/setting/portfolioManagementService.ts:28-32`、`services/api/setting/businessIssuesService.ts:45-49`、`services/api/setting/techStackManagementService.ts:10-14`、`services/api/companyFinance/financeService.ts:4-8`）。

前端唯一的类型声明在 `pages/askGoldie/components/orgScope.ts:9-13`，其余各处全用 `any`。

---

## 2. 前端没有任何"租户"语义

全仓检索 `tenant` / `租户` 只命中两条注释（`pages/devSupport/tracing/detail/TraceDetailPage.tsx:37`、`services/api/tracing/traceDto.ts:41`），且其中"多租户过滤"一句指的是 `companyId` + `organizationId` 两个**可选筛选参数**，不是隔离机制。**产品口中的"Golden Section 那一级 = 租户"在前端没有任何对应代码。**

但存在几处**互相矛盾的硬编码层级假设**：

| # | 假设 | 位置 |
|---|---|---|
| 1 | **取第一棵树的根**（主流，13 处） | `PortfolioCompaniesPage.tsx:296`、`PortfolioManagementPage.tsx:95`、`TechStackManagementPage.tsx:149`、`SdpScorePage.tsx:111`、`QboLogPage.tsx:124`、`BusinessIssuesPage.tsx:97`、`IssueAddPage.tsx:81`、`GeneralTab.tsx:67`、`RolesManagementPage.tsx:214`、`AddCompanyPage.tsx:379`、`KpaConfigurationPage.tsx:42`、`PortfolioAddPage.tsx:45`、`UserDetailPage.tsx:101-104` —— 主体形态是 `ass?.data?.[0]?.id`，个别变体：`TechStackManagementPage.tsx:149` 用 `res?.data?.[0]?.id`；`UserDetailPage.tsx:101-104` 用 `portfolio?.data[0].id`（**无可选链，空数组会抛 TypeError**）；`GeneralTab.tsx:67` 被包在「根无子节点」分支内（同时也是假设 3 的实例） |
| 2 | **取第一个叶子**，且注释声称与主站一致（**实际不一致**） | `pages/askGoldie/components/orgScope.ts:15-26` `firstLeafOrgId`；用于 `useAdminMemoryScope.ts:34`、`KnowledgeBasePage.tsx:218`。这两个页面无组织切换 UI，硬锁首叶 |
| 3 | **"根没有子节点 → 隐藏整个组织下拉"**，且用 `!subdata` 而非 `!subdata?.length` | `PortfolioCompaniesPage.tsx:291-293`、`PortfolioManagementPage.tsx:90-92`、`UserManagePage.tsx:26-28`、`QboLogPage.tsx:121-123`、`UserDetailPage.tsx:102-114` |
| 4 | **`allPortfolioList[0]` 视为不可编辑的超级组织** + 写死一个组织 UUID | `pages/devSupport/portfolioGroupManagement/PortfolioGroupManagementPage.tsx:197-202,349,389` |
| 5 | **不限制只能选叶子** | 所有 `getTreeNode` 无条件给每个节点 `<TreeNode value={item.id}>`，无 `selectable={false}` → **中间层（含 `Global Authority`）与租户层一样可选** |

假设 1 与假设 2 直接矛盾（取根 vs 取叶），而假设 2 的注释声称两者一致。

---

## 3. 没有统一的租户上下文

**全仓无 company/tenant 的 dva model 或 Context。** dva models 只有 `connect.d.ts / global.ts / login.ts / setting.ts / user.ts`；contexts 只有 `CurrencyContext / MobileContext / usePermission`。

当前公司/组织的实际来源分散在三处：

| 来源 | 位置 | 规模 |
|---|---|---|
| `localStorage.localuser.inviteDto.id` | `utils/utils.ts:409-430` `getUserInfo()` | **65 处** |
| URL query `?id=` | `getQueryString('id')` | **63 处** |
| `localStorage['sdp-company']` | `GeneralTab.tsx:291-292`、`DevelopmentPage.tsx:82` | 少量 |
| `localStorage['portfolioCompanies'].organizationId` | `utils/utils.ts:444-473` | 仅 `/company` 页持久化，其余 TreeSelect **完全不持久化**，刷新即回到 `data[0].id` |

**这是做真多租户的第一块必补基建。**

---

## 4. 切换组织 / 切换公司都要重新登录

树内切换（页面级 TreeSelect）：不重登、不刷新，`setState` + 局部 localStorage，立刻 `GET companyGroup/user?organizationId=`。

跨组织切换（头像菜单 `Switch Organizations`，`layouts/BasicLayout.tsx:581-583,891-896`）：**必须重新走 OAuth 登录**。

实现见 `pages/auth/chooseCompaniesApp/ChooseCompaniesAppPage.tsx:41-52`：`choose()` 用 `atob(item?.pwd)` 解出**后端回传的口令**，连同目标 `userId` 一起重新 dispatch 登录（代码见 [证据代码](./code-examples.md) §17）。

流程：`models/login.ts:124-136` 先 `revokeCurrentSession()` 吊销旧令牌 + `clearUserInfo()` 清空 localStorage，再用目标身份重新登录。

**即"一个人在每个组织下是一条独立的 user 记录"**，切换靠换一条记录重新登录。数据源 `organizationsList(email)` = `GET /api/web/organization/getOrganizationStatusByUserEmail?email=`，而 **`email` 来自 URL query，不是来自登录态**（`ChooseCompaniesAppPage.tsx:16,20`）。

> 这条路径与 [Java 端](./java-design.md) §10 的阻断项 2 是同一件事：该接口无授权校验、专查超管账号、返回口令的可逆解密结果。**修复方案应是服务端令牌交换（token exchange），而不是回传口令。**

---

## 5. 权限控制：四层混杂，且全部在前端

项目**没有** umi `access.ts` / `@umijs/plugin-access`（`config/config.ts` 未启用该插件）。

| 文件 | 作用 | 是否生效 |
|---|---|---|
| `utils/authority.ts` | 读写 `localStorage['antd-pro-authority']` | 半空转（`login.ts:324` 传入的值恒 undefined） |
| `components/Authorized/`（7 文件） | Pro 权限内核；`CheckPermissions.tsx:27-29` 无 authority 直接放行 | 生效但权限值为空 |
| `utils/utils.ts:153-180` `getAuthorityFromRouter` | **真正的路由门**：`route.role` 打 `forbid`，再按后端菜单种子放行 | ✅ |
| `utils/utils.ts:355-360` `hasMenuPermissionByPath` | `/devSupport` 整区门禁（读 `localStorage['roles']`） | ✅ |
| `utils/utils.ts:1493-1519` `checkClientRoutePermission` | 公司端路由权限（读 `localStorage['clientRoutePermissions']`） | ✅ |
| `contexts/usePermission.tsx` | 上者的 hook 包装 | 生效但**零业务消费者** |
| `utils/utils.ts:182-207` `getCurrentMenuData` | 按钮级：拆 `functionList` | 部分生效（**仅 6 处消费**，其中 1 处算完不用） |
| `utils/companyRole.ts` | Company Admin 判定 | ✅ |

`config/routes.ts` **无一条 `authority` 字段**（129 条 path，grep 零命中），`role: true` 字面出现 12 次，其中 3 次在注释里，**实际生效 9 条**。

菜单可见性靠 `BasicLayout.tsx:687-859` 的硬编码数组 + 后端菜单种子求交集；其中公司端 `getVerifyRolesForApp`（`:632-639`）对 5 个 key **硬白名单绕过订阅列表**。

### 根因：所有门禁数据源都是用户可写的 localStorage

| 数据 | 写入点 | 读取点 |
|---|---|---|
| `localuser.roleType` | 登录 | `endContext.ts:22`、`BasicLayout.tsx:651-663`、`SecurityLayout.tsx:59/103` |
| `roles`（菜单种子） | `BasicLayout.tsx:351-360`（**由前端提交自己的 roleIds 换回**） | `utils.ts:163-165,355-360` |
| `clientRoutePermissions` | `login.ts:181` 等 3 处 | `utils.ts:1493-1507` |
| `fiStatus` / `diStatus` | — | `SecurityLayout.tsx:32-45` |

**结论：前端权限不构成安全边界，任何前端限制都必须有后端对应校验。**

台账已登记此问题（`web/CIOaas-web/docs/待优化项.md`，2026-07-20：「settings 权限/状态直读写 localStorage、全域无 hasAuthority()」）。

---

## 6. 请求拦截器只带令牌

`utils/request.ts:105-129` 是全仓唯一的 umi-request 请求拦截器。除固定的 `Accept` / `Cache-Control` / `Pragma` 外，**身份相关只注入 `Authorization: Bearer <token>`**（另有 2 个端点白名单与认证端点跳过条件）。`companyId` / `organizationId` / 端类型**一律不在 header 中**，无自定义 `X-Tenant-*` 头（全仓零命中）。

租户 ID 的实际传法散落在业务层：query `?companyId=` / `?organizationId=`、path 段、SSE body 的 snake_case 字段、CSV 串。

旁路（不经拦截器、自行注入）：`services/api/chat/streamApi.ts:47-55`（SSE fetch）、`services/api/common/userService.ts:23-39`、`services/api/companyFinance/financeEditingService.ts:193-200`。

令牌存在 `localStorage`（`utils/utils.ts:363,374`），XSS 可窃。

---

## 7. organizationId 的传播面

全仓 `organizationId` 命中 **310 行 / 358 次 / 74 文件**。前端发给后端的位置分四类：

- **只读树（不发参数）**：5 处 `findByTree`
- **拼进 URL**：12 个接口（`companyGroup/user`、`organization?id=`、`stage/getStageListByOrganizationId`、`techStackManagement/*`、`invite/getCompanyNameIsExist`、`invite/clientKpaStatistics`、`tools`、`score/getScoreConfigurationByOrganizationId`、`rOrganizationRole/getRoleByOrganization`、`companyGroup/company` 等）
- **params / body 对象**：8 个接口（`companyGroup/findAllSort`、`businessIssues/admin`、`businessIssues/client`、`companyQuickbooks/qboLogPage`、`users/query`、`organization/modifyOrganizationMenu`、表单提交的 `organizationList` 等）
- **Python 侧**：9 个接口（memory、file-registry files/filter-options、chat manage 四个（**CSV 多值**）、tracing、financialExtract、rag 业务关联、SSE 的 `simulate_organization_id`）

### 用户可随意篡改的位置（URL query，无前端校验）

| 位置 | 形式 | 说明 |
|---|---|---|
| `AddCompanyPage.tsx:41,53,379,388` | `?organizationId=<明文>` | **URL 值优先于树，且不校验是否在自己的树里**，随后直接拿去请求 stage/techStack/companyGroup |
| `PortfolioCompaniesPage.tsx:297-299,550-555` | `?params=<base64>` 内含 organizationId | base64 **不是加密**（`utils.ts:251-270` 用 `window.atob`），且这条路径**绕过**了 `:300-306` 的白名单校验 |
| `KpaConfigurationPage.tsx:14,42-43`、`KpaConfigEditPage.tsx:18,127` | `?organizationId=<明文>` | 同上 |
| `ChooseCompaniesAppPage.tsx:16,20` | `?email=<任意邮箱>` | 见 §4 |

---

## 8. 仅靠前端限制的功能清单

| # | 功能 | 后端状况（代码自述） |
|---|---|---|
| 1–3 | Chat Management / Q&A / Analytics（`/devSupport/chatManage` 等） | "后端仅登录即可访问、端类型限制靠前端入口"（`pages/devSupport/chat/README.md:33`、`services/api/chat/chatManageApi.ts:2`） |
| 4 | **devSupport 全区 36 个页面 URL** | README 原文（`pages/devSupport/README.md:8`）：「**鉴权口径**：登录即可访问、不加 role 门禁；管理性页面（如 chatManage）的限制靠前端入口收敛 **+ 后端接口 403**」。即 README 自述**部分**管理性页面另有后端兜底；前端单点门禁在 `SecurityLayout.tsx:67-71`，读 localStorage |
| 5 | Platform Admin 7 页 | 与同级一致 = 登录即可（`pages/devSupport/README.md:27-35`） |
| 6 | 角色删除按钮 | `roleType === 1` 内联判断，未见后端校验声明 |
| 7 | Benchmark Entry 页 | `roleType <= 2` 内联 |
| 8 | Ask Goldie 顶部入口 | 注释明写"不依赖后端菜单/角色权限种子" |
| 9 | 公司端 5 个顶部菜单 | 硬白名单绕过订阅列表 |
| 10 | Company Settings 各 Tab | `roleType <= 2` / `<= 1` 内联 |
| 11 | Business Issues 公司列/超管操作 | `roleType <= 1` 内联，含直接 `return false` 藏按钮 |
| 12 | User Management 的 Add/Edit | **权限算完从未消费**，编辑图标无条件渲染（`UserManagePage.tsx:99-105` vs `:117-122`） |
| 13 | 9 条 `role: true` 路由 | 命中 localStorage 中任一 path 即放行 |
| 14–15 | `/investmentDetails`、FI/DI 模块开关 | 读 localStorage |

**对照：确有后端兜底的**（不在隐患清单）：Memory Settings（后端 40301）、Chat 身份模拟（非超管 403）、SSE `/subscribe` 归属校验、知识库授权公司集（fail-closed 红线）。

---

## 9. 多租户 UI：已有 vs 缺失

### 可复用页面

| 能力 | 路由 | 复用价值 |
|---|---|---|
| 租户（公司）开通表单 | `/addCompany` | ★★★ |
| 租户列表/总览 | `/company` | ★★★（已带按钮权限 + 双视图） |
| 组织 CRUD + 菜单授权 | `/devSupport/portfolio` | ★★★ |
| 平台用户管理（带组织 TreeSelect 过滤） | `/settings` | ★★★ |
| 公司成员管理 + 邀请 + 角色分配 | `/companySetting?active=2` | ★★★（邀请的现成实现） |
| 平台角色管理（角色×菜单矩阵，支持按组织建角色） | `/devSupport/rolesManagement` | ★★★ |
| 公司角色（客户端权限配置） | `/devSupport/companyRoles` | ★★★ |
| 菜单/功能点管理 | `/devSupport/menuManagement` | ★★★（按钮级权限的数据源） |
| 组织选择/切换 + 邀请接受/拒绝 UI | `/chooseCompaniesApp` | ★★ |
| 目录选择器（用户/公司/组织统一） | `pages/devSupport/components/DirectorySelect/` | ★★★ |
| Portfolio 管理 + 新建 | `/portfolios` | ★★ |

### 缺失清单

| # | 缺失 | 说明 |
|---|---|---|
| 1 | **统一租户上下文（TenantProvider / model）** | 见 §3。**第一块必补基建** |
| 2 | **无刷新切换租户** | 现在必须重新登录且依赖前端持有口令；需改为服务端令牌交换 |
| 3 | 租户开通向导 | 只有单页表单；缺"建组织 → 建首个管理员 → 分配套餐 → 初始化菜单权限"串联 |
| 4 | 组织自助管理页 | 组织 CRUD 只在超管内部工具里；租户侧无 Organization Settings |
| 5 | 组织级成员管理 / 跨公司成员视图 | 现有成员页是**单公司**；用户管理页只查超管 |
| 6 | 邀请生命周期管理 | 缺待处理列表、过期/撤回、批量邀请、链接管理 |
| 7 | 成员-角色批量分配矩阵 | 现在只有一个下拉且禁用条件复杂 |
| 8 | 按钮级权限统一 API（`hasAuthority()`） | 数据源已有，仅 6 处消费 |
| 9 | 组织级数据隔离的 UI 表达 | 无"当前组织"面包屑/切换器；管理端记忆作用域**锁定首叶、无切换 UI** |
| 10 | 套餐 / 席位 / 计费管理页 | 订阅接口只读；Plans & Pricing 菜单项已被注释 |
| 11 | 租户/权限变更审计 | 只有业务审计 `/auditTrail` 与 `/QBOLog` |
| 12 | SSO / 域名绑定 / 租户品牌化 | 零实现；端类型仍靠域名硬编码白名单，**加一个新租户域名要改代码** |

---

## 10. 端类型判定（两套并存）

| 口径 | 位置 | 取值 |
|---|---|---|
| **域名硬编码**（老） | `utils/utils.ts:304-332` `isAdminEnd()` / `isClientEnd()` | admin*.lgpi.io / app*.lgpi.io |
| **roleType**（新，权威） | `pages/devSupport/chat/utils/endContext.ts:17-26` `resolveEndType()` | roleType 1 → admin，2/3/4 → customer，缺失回退 host |

老口径仍在 3 处生产路径使用（`request.ts:17`、`BasicLayout.tsx:419`、`SecurityLayout.tsx:69/89/110/117`），**本地 dev（localhost）在老口径下恒判为客户端**。

登录时有反向校验（`models/login.ts:191-198`）：roleType 2/3/4 用 admin 入口会被拒，roleType 1 用 user 入口同样被拒。

---

## 11. 前端缺口清单（以 organization 为租户）

| # | 缺口 | 优先级 |
|---|---|---|
| F-1 | 无统一租户上下文，公司/组织 ID 散落 4 处（`inviteDto` 65 处 + `getQueryString('id')` 63 处） | P1 |
| F-2 | 切换组织依赖后端回传口令 → 应改服务端令牌交换 | **P-1 阻断（与 Java 同一问题）** |
| F-3 | 三处 URL query 可篡改 `organizationId` 且绕过前端白名单 | P1（后端补校验后自动失效） |
| F-4 | 权限门禁数据源为可写 localStorage，前端不构成安全边界 | P1（依赖后端补齐） |
| F-5 | 层级假设互相矛盾（取根 vs 取叶），且中间层可选 | P0（随 Phase 0 收敛） |
| F-6 | 组织树下拉代码复制到 17 个文件、service 重复 5 份 | P2 |
| F-7 | 端类型两套口径并存 | P2 |
| F-8 | 多租户运营 UI 缺 12 项（见 §9） | P3 |
