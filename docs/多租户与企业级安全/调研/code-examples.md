# 证据代码与数据清单

> 关联文档: [决策摘要](./executive-summary.md) | [设计理念](./design-philosophy.md) | [系统架构](./system-architecture.md) | [Java 端](./java-design.md) | [Python 端](./python-design.md) | [前端](./frontend-design.md)

本文集中存放支撑各设计文档结论的代码片段、SQL 与数据清单，避免在设计文档中混写实现细节。

> ⚠️ 安全说明：本文**不包含任何真实密钥、口令或凭据值**。涉及敏感常量处仅标注文件位置。

---

## 1. 租户模型：`Organization` 全部字段

`java/CIOaas-api/gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/system/domain/Organization.java:17-40`

```java
@Entity
@Table(name = "organization")
public class Organization extends AbstractAuditingEntity implements Serializable {

  @Column(length = 120, nullable = false)
  private String name;

  @Column(name = "logo_url", length = 1024)
  private String logoUrl;

  @Column(name = "website_url", length = 1024)
  private String websiteUrl;

  @Column(name = "code", length = 1024)
  private String code;

  @Column(name = "pid")
  private String pid;

  @Column
  private String description;
  // ... 仅 hashCode / copy / equals
}
```

**无 `level` / `type` / `is_tenant` / `depth` / `root_id`。** 加上审计基类的 `id / created_at / created_by / updated_at / updated_by`，这就是全部字段。

---

## 2. 「我在哪个组织」的 6 个实现

### 2.1 Redis 会话重建（Python 侧唯一权威来源的上游）

`.../web/system/repository/UserRepository.java:209-210`

```java
@Query(nativeQuery = true, value = "SELECT organization_id FROM r_organization_user WHERE user_id = ?1 LIMIT 1")
String findOrganizationIdByUserId(String userId);
```

### 2.2 登录期装配

`.../web/oauth/service/UserDetailsServiceImpl.java:177-184`

```java
String organizationId = Optional.ofNullable(user.getOrganization()).map(OrganizationDto::getId).orElse(null);
if (organizationId == null) {
  List<OrganizationDisplayDto> userOrganizations = organizationService.getOrganizationListByUserId(user.getId());
  if (!userOrganizations.isEmpty()) { organizationId = userOrganizations.get(0).getId(); }
}
```

### 2.3 `getCurrentOrganization()`

`.../web/system/service/CompanyGroupServiceImpl.java:88-98`

```java
List<ROrganizationUser> organizationUsers = rOrganizationUserRepository.findByUserId(userId);
if (ObjectUtil.isEmpty(organizationUsers)){
  Optional<Invite> invite = companyRepository.findById(user.get().getCompanyId());
  ...
  List<ROrganizationCompany> rOrganizationCompanyList = rOrganizationCompanyRepository.findByCompanyId(invite.get().getId());
  organization = organizationRepository.findById(rOrganizationCompanyList.get(0).getOrganizationId());  // 空列表则数组越界
} else {
  organization = organizationRepository.findById(organizationUsers.get(0).getOrganizationId());
}
```

### 2.4 Python chatbot 可访问公司集（恒取树根）

`python/CIOaas-python/source/chatbot/application/service/company_service.py:55-61`

```python
orgs = await query_user_organizations(UserOrganizationsParams(auth_token=auth_token))
...
org_id = orgs.organizations[0].id
```

拍平逻辑（**前序 DFS，父节点先入列 → `[0]` 恒为根**），`python/CIOaas-python/source/lgpi_api/user_organizations_api.py:70-84`：

```python
oid = str(node.get("id") or "").strip()
if oid and oid not in seen_ids:
    seen_ids.add(oid); out.append(...)
walk(node.get("subdata"))
```

注意该函数只保留 `id` 与 `name`，**`pid` / 深度 / 父子关系全部丢弃**。

### 2.5 前端 askGoldie（取第一个叶子）

`web/CIOaas-web/src/pages/askGoldie/components/orgScope.ts:15-26`

```ts
/** 组织树首个叶子节点 id（叶子=实际挂 portfolio/公司的组织；对齐主站默认选中子组织）。 */
export function firstLeafOrgId(nodes: OrgNode[]): string | undefined {
  for (const n of nodes || []) {
    if (n.subdata && n.subdata.length > 0) { const child = firstLeafOrgId(n.subdata); if (child) return child; }
    else if (n.id) { return n.id; }
  }
  return nodes?.[0]?.id;
}
```

注释声称"对齐主站默认选中"，但主站取的是根（见 2.6）。

### 2.6 前端 13 处默认值（取第一棵树的根）

`web/CIOaas-web/src/pages/portfolioCompanies/home/PortfolioCompaniesPage.tsx:296`

```ts
let initOrganizationId = ass?.data?.[0]?.id;
```

---

## 3. 子树展开：能力与授权链的错配

### 3.1 递归 CTE（能力存在）

`.../web/system/repository/OrganizationRepository.java:36-43`

```sql
with RECURSIVE org as (
  select a.* from organization a where id = ?1
  union all
  select k.* from organization k inner join org c on c.id = k.pid
)
select * from org ORDER BY created_at;
```

### 3.2 授权链却用等值（不递归）

`.../web/system/repository/CompanyGroupRepository.java:51-56`

```sql
FROM company_group cg
INNER JOIN r_company_group rcg ON rcg.company_group_id = cg.company_group_id AND rcg.status = 0
INNER JOIN company c ON c.company_id = rcg.company_id
WHERE cg.organization_id = :orgId
  AND ( :seeAll = TRUE OR cg.company_group_id IN (SELECT company_group_id FROM r_portfolio_user WHERE user_id = :uid) )
```

**无"调用者是否属于 orgId"的校验；`seeAll = TRUE` 直接短路归属条件。**

### 3.3 `findByTree` 对客户端传入的 ids 零校验

`.../web/system/service/OrganizationServiceImpl.java:344-352`

```java
public List<OrganizationDto> findByTree(List<String> ids) {
  ...
  if(ObjectUtil.isEmpty(ids)||ids.isEmpty()){
    List<ROrganizationUser> byUserId = rOrganizationUserService.findByUserId(SecurityUtils.getUserId());
    ids = byUserId.stream().map(ROrganizationUser::getOrganizationId).collect(Collectors.toList());
  }
  // ids 非空 → 直接使用，随后对每个 id 跑 findByTreeInId 展开整棵子树
```

Controller 签名（`OrganizationController.java:80-84`）接受该参数：

```java
@GetMapping("/findByTree")
public Result<List<OrganizationDto>> findByTree(@RequestParam(name = "ids", required = false) List<String> ids) {
  return Result.success(organizationService.findByTree(ids));
}
```

---

## 4. 组织维度越权面全表

**口径说明（重要）**：本表统计的是「**服务端会依据某个组织维度参数改变返回内容或写入归属，且不校验调用者与该组织关系**」的端点，共 **40 个**。其中：

- 参数名并不都叫 `organizationId`——也包括 body 里的 `pid`、`id`、`organizationList` 等组织维度字段
- **#5 `GET /organization/findAllSort` 无任何入参**（直接返回全库组织），列入是因为它同属组织维度越权面
- **#9 `GET /organization/getOrganizationStatusByUserEmail` 入参是 `email`**，列入同上
- **#40 `GET /companyQuickbooks/qboLogPage` 的组织字段在查询对象 `CompanyQuickbooksPostQueryCriteria` 里**（非直接形参）。它原被归入“不读”，复核后发现**强制要求 organizationId 且用它展开该组织全部公司**，故移入本表
- **#8 `GET /organization/options` 有超管门禁**，不属于"0 个校验"的分子——「归属校验 0 个」指的是**没有一个端点校验"调用者是否属于它操作的那个组织"**，超管门禁是另一维度

若只统计 Controller 方法签名上直接出现 `organizationId` 形参的端点，是 **14 个**。两个数字口径不同，引用时请注明。

图例：**无** = 无任何归属校验；**仅超管** = 有超管门禁但与组织归属无关；**不读** = 服务端不读取该参数。

| # | HTTP 方法 + 路径 | 位置 | 来源 | 校验 | 泄漏 / 破坏内容 |
|---|---|---|---|---|---|
| 1 | `POST /organization` | `OrganizationController.java:49-53` | body `pid` | **无** | 任意用户在任意父节点下创建组织，并触发 10 张配置表 seed |
| 2 | `PUT /organization` | `:67-71` | body `id` + `pid` | **无** | 改任意组织；pid 任意搬家、可造环 |
| 3 | `DELETE /organization?id=` | `:61-65` | query | **无** | 硬删任意组织及整棵子树 |
| 4 | `GET /organization?id=` | `:55-59` | query | **无** | 任意组织详情 + 完整菜单授权树 |
| 5 | `GET /organization/findAllSort` | `:37-41` | 无参 | **无** | 全库所有组织 + 菜单授权矩阵 |
| 6 | `GET /organization/findByTree?ids=` | `:80-84` | query 数组 | **无** | 任意组织完整子树 |
| 7 | `PUT /organization/modifyOrganizationMenu` | `:73-78` | body | **无** | 重写任意组织菜单并级联撤销整棵子树及其角色 |
| 8 | `GET /organization/options` | `:43-47` | query | 仅超管 | 组织目录 |
| 9 | `GET /organization/getOrganizationStatusByUserEmail?email=` | `:86-90` | 按 email | **无** | 见 §6 阻断项 |
| 10 | `GET /companyGroup/findAllSort?organizationId=` | `CompanyGroupController.java:34-38` | query | **无** | 任意组织全部 Portfolio + 公司清单 |
| 11 | `GET /companyGroup/user?organizationId=` | `:93-97` | query | **无（反向倒挂）** | 传入 ≠ 自己的组织时**跳过** Portfolio 归属过滤 |
| 12 | `GET /companyGroup/companies?organizationId=` | `:99-103` | query | **无** | 任意组织的公司↔Portfolio 全量配对 |
| 13 | `GET /companyGroup/{organizationId}` | `:87-91` | **path** | **无** | 任意组织全部 Portfolio（无 group-manager 判断） |
| 14 | `GET /companyGroup/company?organizationId=` | `:81-85` | query | **无** | 任意组织下全部公司 |
| 15 | `POST /companyGroup` | `:40-45` | body | **无** | 在任意组织下建 Portfolio 并挂任意公司 |
| 16 | `PUT /companyGroup` | `:67-72` | body | **无** | 改任意 Portfolio 并全量重建成员 |
| 17 | `POST /companyGroup/relevance` | `:74-79` | body | **无** | 把任意公司重挂到任意 Portfolio（可跨组织） |
| 18 | `GET /invite/getList?organizationId=` | `CompanyController.java:87-92` | query | **无** | 任意组织**整棵子树**的公司列表 + 各类分数 |
| 19 | `GET /invite/query?organizationId=` | `:74-79` | query | **无** | 任意组织**整棵子树**的项目列表 |
| 20 | `GET /invite/getCompanyNameIsExist?organizationId=` | `:246-250` | query | **无** | 探测任意组织下公司名，可枚举 |
| 21 | `POST /invite/addWithoutEmail` | `:177-190` | body `organizationList` | **无** | 把公司挂到任意组织；**无租户一致性约束，可挂到别的租户名下** |
| 22 | `POST /invite/addCompanyAndSetStage` | `:207-221` | body | **无** | 同上 |
| 23 | `GET /users/query?organizationId=` | `UserController.java:80-91` | query | **无** | 任意组织**整棵子树**的用户列表 |
| 24 | `POST /users` | `:111-129` | body | **无** | 在任意组织下建用户并写关联 |
| 25 | `POST /users/adminUser` | `:131-156` | body | **无** | 先解绑再重挂 → **搬迁已有任意用户到任意组织** |
| 26 | `PUT /users/{userId}` | `:259-283` | body | **无** | 同上 |
| 27 | `GET /rOrganizationRole/getRoleByOrganization?organizationId=` | `ROrganizationRoleController.java:28-32` | query | **无** | 任意组织角色清单 + 菜单授权 |
| 28 | `POST /rOrganizationRole/addOrganizationRole` | `:40-48` | body | **无** | 在任意组织下新建角色 |
| 29 | `GET /tools?organizationId=` | `KpaCategoryController.java:31-41` | query | **无** | 任意组织 KPA 分类 + 工具配置 |
| 30 | `GET /score/getScoreConfigurationByOrganizationId?organizationId=` | `ScoreController.java:94-99` | query | **无** | 任意组织评分配置 |
| 31 | `POST /score/saveScoreConfiguration` | `:101-112` | body | **无** | **改写全库每一个组织的权重**（见 §5） |
| 32 | `GET /score/getDevelopmentIntelligenceScore?organizationId=` | `:70-80` | query | **无** | 用指定组织配置计算分数 |
| 33 | `GET /stage/getStageListByOrganizationId?organizationId=` | `StageController.java:44-49` | query | **无** | 任意组织 stage 配置 |
| 34 | `GET /techStackManagement/layer/{organizationId}` | `TechStackManagementController.java:24-28` | **path** | **无** | 任意组织技术栈层级树 |
| 35 | `GET /techStackManagement/getTechStackElement?organizationId=` | `:36-40` | query | **无** | 任意组织 layer + element |
| 36 | `GET /techStackManagement/getTechStackManagementByOrganizationId?organizationId=` | `:42-46` | query | **无** | 任意组织全量管理视图 |
| 37 | `POST /techStackManagement/layer` | `:30-34` | body 数组 | **无** | 改写任意组织权重并触发公司分数重算 |
| 38 | `POST /businessIssues/admin` | `BusinessIssuesController.java:45-49` | body | **无（反向倒挂）** | 组织 ID 不等于当前组织时**跳过**过滤 |
| 39 | `POST /businessIssues` | `:31-36` | body | **无** | 以任意组织名义写入 |
| 40 | `GET /companyQuickbooks/qboLogPage` | `FinancialSettingController.java:94-98` | query（`CompanyQuickbooksPostQueryCriteria.organizationId`，**强制非空**） | **无** | `companyIds` 为空时用它取该组织**全部公司**（`QuickbooksLogsServiceImpl.java:67-73` → `companyGroupService.company(null, orgId)`），返回其 QuickBooks 连接/同步日志：公司名、操作人、动作、状态、报错原文 |
| — | `GET /users/options`、`GET /invite/options` | — | query | 仅超管 | 用户/公司目录 |
| — | `/invite/portfolio`、`/invite/exportPortfolioDetailView`、`/invite/exportPortfolioDetailViewToPdf`、`/invite/investmentMaxForFilter`、`/companyQuickbooks/connections`、`/companyQuickbooks/companyIssues`、`/financialStatements/exportFinancialPdf`、`/users/invite`、`/kpaBusiness/addKpaReview`、`/kpaBusiness/editKpaReview`、`/businessIssues/client` | — | body/query | **不读** | 死字段；实际按 `companyGroupId` / `companyId` 过滤。已逐个核实，**不再用通配写法**（原 `/companyQuickbooks/*` 里的 `qboLogPage` 实际会读，已移入上表 #40） |

**统计：40 个组织维度越权面，其中校验"调用者是否属于该组织"的为 0 个**（另 11 个端点带组织字段但服务端不读，已逐个核实）。

---

## 5. 单次调用改写全库所有组织权重

`.../web/di/service/ScoreServiceImpl.java:1254-1269`（`saveScoreConfigurationforAllOrganization`）

调用链：`POST /score/saveScoreConfiguration`（`ScoreController.java:101-112`）→ 先写入请求体指定的组织 → 随后 `organizationService.findAll()` 遍历**全库每一个 organization**，覆盖其 kpa / techStack / etl / document 权重 → 最后触发 `etlScoreAirflow()`。

---

## 6. 两条阻断项的代码位置

> 仅标注位置与行为，不复制任何密钥或口令值。

### 6.1 无授权的口令回吐接口

`.../web/system/controller/OrganizationController.java:86-90`（该文件 `@AnonymousAccess` 计数为 0，即需要登录，但**无任何授权校验**）

```java
@GetMapping("/getOrganizationStatusByUserEmail")
public Result<List<OrganizationStatusDto>> getOrganizationStatusByUserEmail(String email) {
  return Result.success(userService.getOrganizationStatusByUserEmail(email));
}
```

查询条件专查超管（`UserRepository.java:135-136`）：

```java
@Query(nativeQuery = true, value = "select * from \"user\" where username = ?1 and username != '' and role_type = 1 and valid = '0' and is_deleted = false ORDER BY status desc,created_at desc")
List<User> findByUsernameAndAdminAndDeletedFalse(String username);
```

返回体装配（`UserServiceImpl.java:1773-1780`）——解密后 Base64 回吐：

```java
String pwd = user.getPwd();
try { pwd = decrypt(pwd); } catch (Exception e){ log.error(e.getMessage()); }
pwd = Base64.getEncoder().encodeToString(pwd.getBytes(StandardCharsets.UTF_8));
organizationStatusDto.setPwd(pwd);
```

解密实现 `UserServiceImpl.java:1735-1741`，使用 **AES-ECB（无 IV、无认证）**，密钥为硬编码常量，位于 `.../web/system/enums/PasswordSecretKeyEnum.java`（该文件在 git 中）。

前端消费点 `web/CIOaas-web/src/pages/auth/chooseCompaniesApp/ChooseCompaniesAppPage.tsx:46`：`password: atob(item?.pwd)`。

**修复方向**：接口收敛为"只能查自己"或下线；切换组织改为服务端令牌交换；移除 `user.pwd` 可逆副本列与加解密工具。

### 6.2 生产 JWT 密钥为默认占位串

- 默认值定义：`gstdev-cioaas-common/.../security/jwt/JwtTokenProvider.java:30`
- 生产配置：`java/CIOaas-api/deploy/cioaas-web-prod.yml:103` —— 与上述默认值**完全一致**
- 校验逻辑 `JwtTokenProvider.java:40-46` 只校验密钥长度 ≥ 32 字节，**不校验是否为默认值**
- 该配置文件被 git 跟踪（`git ls-files deploy/` 可验证），同文件另含数据库密码、AWS 长期密钥、支付平台生产私钥、Sentry DSN
- 未被 `.gitignore` 挡住的原因：根 `.gitignore` 规则为 `cioaas_*.yml`（下划线），实际文件名用连字符

**修复方向**：轮换全部凭据 → 更换签名密钥（将导致全员重新登录）→ 从 git 历史清除 → 改走配置中心 / 密钥管理服务；并在启动期增加"拒绝使用默认密钥"的断言。

---

## 7. 数据库层：RLS 与租户隔离核实

### 7.1 检索结果（全部为 0）

在全仓 `.sql` 文件中检索以下关键字，**零命中**：

```
ROW LEVEL SECURITY | CREATE POLICY | FORCE ROW LEVEL | SET ROLE | current_setting
```

Java 侧检索以下关键字，**零命中**：

```
TenantLineHandler | AbstractRoutingDataSource | @FilterDef | StatementInspector | mybatis
@PreAuthorize | @PostAuthorize | @Secured | hasRole( | hasAuthority(
```

Python 侧在 `source/`、`sql/`、`scripts/` 检索 `SET ROLE` / `row level security` / `search_path`，**零命中**。

`GRANT` 唯一真实出现处是 Nacos 的 MySQL 账号初始化（`java/CIOaas-api/docs/dev环境配置信息/Docker方案/init/mysql/01-create-nacos-db.sql:19-24`），与 LG 业务租户无关。

### 7.2 物理库清单

| 库 | 引擎 | 实例名 | 分库依据 |
|---|---|---|---|
| 业务库 | PostgreSQL | dev/test `lg_test`、staging `lg_staging`、prod `cioaas_prod_v2` | **按功能** |
| RAG 向量库 | PostgreSQL + pgvector | `lg_rag`（未配置时回落业务库） | **按功能**（pgvector / pg_trgm 扩展隔离） |
| Nacos 配置库 | MySQL 5.7 | `nacos_devtest` | **按功能**，无 LG 业务数据 |

`docker/postgres/init/01-init-rag-db.sh` 注释原文说明分库理由是扩展隔离，与租户无关。

### 7.3 三处看似分片、实则无关的机制

1. `java/CIOaas-api/.../resources/templates/etl/add/github.sql:5` 的 `create schema schemaName;` —— **全仓无任何代码引用，死代码**，且按 ETL 工具而非租户分
2. `ai_rag_space.pg_schema` / `pg_table_name` —— per-space 可选覆盖，且 `pg_store.py:48-52` 注释写明**未真正应用到 SQL**
3. ES 索引名按 `company_id` 前 8 位路由（`rag/infrastructure/storage/es_store.py:51-60`）—— 唯一真正按租户切分物理存储的机制，但 ES 在 `docker-compose.yml` 中是**注释掉的**，且所有空间默认后端为 `pg`，**实际未启用**

---

## 8. 完全没有租户列的表（隔离盲区）

### 8.1 Java 侧关键表

| 表 | 用途 | 行数 / 大小（lg_test 实测） |
|---|---|---|
| **`files`** | **全站 S3 文件登记（bucket / link / hash / 原始文件名）** | — |
| **`r_financial_normalization`** | 归一化财务 明细↔版本 关联 | **632,906 行 / 102 MB** |
| **`r_financial_forecast_year_version`** | 预测↔年度版本关联 | **136,898 行 / 24 MB** |
| `schedule_config` | 定时任务配置（`schedule_name` 内嵌 companyId 字符串，只能 LIKE 匹配） | — |
| `role` / `menu` / `r_user_role` / `r_user_menu` / `r_role_menu` / `r_organize_user` 等 | 权限元数据 | — |
| `finance_manual_data_email` | 财务数据邮件通知（含收件人邮箱） | — |
| 全局字典（`currency` / `currency_rate` / `d_timezone` / `dictionary` / `financial_benchmark_entry`） | 合理无租户列 | — |
| 全平台配置（`subscription_template` / `r_subscription_menu` / `tech_stack_type` / `third_party_d_tool` / `finance_category_weight` / `finance_score_level`） | **归属待拍板** | 见[系统架构](./system-architecture.md) §12.2 / §12.5 |

### 8.2 AI 侧关键表

| 表 | 库 | 用途 | 归属反查路径 |
|---|---|---|---|
| `ai_financial_extraction_mapping_data` | 业务 | 逐单元格解析结果 + 编辑痕迹 | `file_id` |
| `ai_financial_extraction_task_state_log` | 业务 | 状态机事件（含模型识别原文） | `task_id` |
| `ai_chatbot_message` | 业务 | **全部对话正文 + 附件绑定** | `thread_id`（thread 的 company_id 可能为 NULL） |
| `ai_llm_conversation` | 业务 | **完整 system/user/assistant 全文 + `msg_full_json`** | `call_log_id`（有 CASCADE） |
| `ai_trace_span` | 业务 | 链路节点上下文 | `trace_id` |
| `ai_rag_space` | 业务 | 知识库空间 | **归属表已被 V005 `DROP`** |
| `ai_rag_storage_connection` | 业务 | 存储连接（含加密凭据） | 全局，注释 `global, no company ownership` |
| `ai_rag_search_log` | 业务 | **检索日志（含用户原始提问）** | 注释：`tenant scope carried by user_id + space_ids (no company_id)` |
| `ai_rag_operation_log` | 业务 | RAG 写操作审计 | 注释：`tenant scope via space_id (no company_id)` |
| `ai_r_business_association_space` | 业务 | 关联↔空间明细 | `association_id` |
| `ai_rag_playbook` / `_version` | 业务 | 全局方法论库 | 设计即全局 |
| `ai_rag_fin_report_chunk` | 向量 | **财报向量分段（含正文）** | 仅 `company_ref`，注释明确是 business metadata 非过滤键 |
| `ai_rag_playbook_chunk` | 向量 | Playbook 向量分段 | 注释：「零业务列」 |
| **`checkpoints` / `checkpoint_blobs` / `checkpoint_writes`** | 业务 | **LangGraph 图状态（含解析出的财务数据）** | 仅 `thread_id`；**由 `PostgresSaver.setup()` 启动时自建、无任何 DDL 脚本、不受版本化迁移管控**（仅在 `sprint109/V15` 的"未能可信解析"注释清单里被提及过） |

---

## 9. 租户列命名不一致清单

| 概念 | 出现过的列名 | 位置 | 影响 |
|---|---|---|---|
| 公司 ID | `company_id` | 743 次，主流 | — |
| | `ref_company_id` | `ai_llm_call_log`、`ai_llm_tool_call_log` | **统一脚本会漏这两张表** |
| | `company_ref` | `ai_rag_fin_report_chunk`（向量库） | 且注释说明它不是过滤键 |
| | `main_company_id` | `colleague_company_group` | — |
| | `company`（**freetext 公司名，非 FK**） | `user` 表，与同表 `company_id` 并存 | **极易误用**；列注释原文 `Company name (freetext field, not FK)` |
| 组织 ID | `organization_id` | 301 次，主流 | — |
| Portfolio ID | `company_group_id` | `company_group`(PK)、`r_company_group`、`r_portfolio_user` 等 | — |
| | **`portfolio_id`** | `business_issues`、`portfolio_capacity`、`financial_benchmark_email_portfolio_record` | **同一概念两个名字**；列注释自陈 `FK to company_group.company_group_id (portfolio)` |

### 主键命名不一致（影响自动生成删除脚本）

`company.company_id` / `organization.id` / `company_group.company_group_id` / `schedule_config.schedule_id` / `finance_manual_data_alert.id` / `financial_benchmark_entry.detail_id` / `ai_*.id` —— 至少 4 种风格。`deploy/upgrade_doc/sprint116/cleanup_orphan_finance_manual_data_alert.sql:20-23` 专门写了"主键列名注意（易踩）"段落。

### 表名漂移

| 现名 | 历史名 |
|---|---|
| `ai_file_registry` | `ai_files` → `ai_financial_extraction_file` → 今名（一个迁移文件里两次 RENAME） |
| `ai_financial_extraction_mapping_data` | `ai_financial_extraction_extracted_data` |
| `ai_financial_training_data` | `ai_training_data` |
| `third_party_*`（26 张） | `github_*` / `sonarqube_*` / `circleci_*` / `aws_*` / `newrelic_*` 等 |
| `financial_*`（5 张） | `company_close_month_update` / `benchmark_report_*` 等 |

**后果**：`sprint109/V15` 那份"外键关系权威清单"里仍残留 `ai_rag_chunk`、`ai_rag_migration_task`、`ai_rag_space.company_id`、`ai_files` 等**已不存在的表/列**。

---

## 10. 外键与级联现状

`java/CIOaas-api/deploy/upgrade_doc/sprint109/V15__foreign_key_column_comments.sql:4-6` 原文：

> 背景：外部平台扫描测试库报「Complete foreign key constraint definitions（**158 foreign keys with issues**）」。**本项目全环境挂 `IgnoreForeignKeyExceptionHandler`，FK 约束多数未真正落库**，故按「补外键描述」处理。

处理器位置：`.../web/datasource/IgnoreForeignKeyExceptionHandler.java`，挂载于 `deploy/cioaas-web{,-staging,-prod}.yml:41`。305 条"外键"中仅 **61 条**在 `pg_catalog` 中真实存在。

**全仓 DDL 中 `ON DELETE CASCADE` 共 7 处（另有 6 处出现在注释里），无一指向 `company` 或 `organization`。**

**更彻底的事实：线上根本不存在"删除公司"这条路径。** 代码里仅存的两条硬删路径**当前都不可达**，`CompanyServiceImpl.java:695-698` 的注释已写明：

> ⚠️ 本方法与 `deleteCompany` 是仅存的两条硬删路径，且当前**都不可达**：本方法零调用方，`deleteCompany` 的唯一调用点在 `deleteByCompanyId` 里被注释（2026-02-04 `c00f7a7d8`），线上「删除公司」实为停用、不删行。

两条路径各自发出 `CompanyDeletedEvent`（`:699`、`:1022`），而唯一监听器只清理一条告警记录且失败仅记日志——**但因为两条路径都不可达，这个监听器实际也从不触发**。

两次真实事故留下的清洗脚本：

- `deploy/upgrade_doc/sprint103/cleanup-invalid-company-ids.sql`
- `deploy/upgrade_doc/sprint116/cleanup_orphan_finance_manual_data_alert.sql:5-13`（注释记录：公司行曾被硬删，该调用已于 **2026-02-04 `c00f7a7d8` 注释掉**）

---

## 11. 索引现状（影响未来加租户过滤的性能）

`deploy/upgrade_doc/sprint109/V17__add_missing_fk_indexes.sql:4-6` 原文：

> 在测试库 lg_test 扫描出 **367 个 `*_id` 列不是任何索引的首列**（无法支撑等值查找）。全部建会过度索引、拖慢热表写入，故按既定口径只取高价值列。

V17 只补了 **79 列**，**剩余 288 个 `*_id` 列至今不是任何索引首列**。

### 有租户列但没有以它打头的索引

| 表 | 缺什么 |
|---|---|
| `ai_chatbot_thread` | `company_id` / `organization_id` **零索引** → 管理端按公司/组织筛会话是全表扫 |
| `ai_llm_tool_call_log` | `ref_company_id` 零索引 |
| `ai_rag_ingestion_task` | `company_id` 无索引 |
| `ai_financial_extraction_conflict_record` | `company_id`（NOT NULL）无索引 |
| `ai_rag_ent_kb_chunk` | V003 新加的 `company_id` / `organization_id` **零索引** |
| 5 张 benchmark 相关表 | `company_id` 无独立打头索引 |

**向量表全部零租户索引**：三张分段表的索引全是 `(space_id)` / `(entry_id)` / HNSW / gin_trgm。若要在向量检索中加租户前置过滤，三张表都要新建索引，且 HNSW 与列过滤组合会走"先扫再排序"路径（V004 注释已记录此现象）。

**正面样板**：`ai_financial_training_data` 的 `(company_id, ...)` 复合索引以租户列打头，是全仓租户索引的唯一正例。

---

## 12. 数据规模（lg_test 实测，prod 应更大）

| 表 | 行数 | 大小 | 有 company_id |
|---|---|---|---|
| `company_index_verify` | 1,986,485 | **943 MB** | ✅ |
| `score_kpa_category` | 1,558,678 | 352 MB | ✅ |
| `log`（审计表，已停止增长） | 590,552 | 248 MB | ✅ |
| `queue_message_log` | 293,365 | 201 MB | ✅ |
| `score_tech_stack` | 821,240 | 186 MB | ✅ |
| `company_index_verify_main` | 375,552 | 135 MB | ✅ |
| `third_party_sonarqube_search_history` | 450,455 | 115 MB | ✅ |
| **`r_financial_normalization`** | **632,906** | **102 MB** | **❌** |
| `third_party_sonarqube_component_search` | 340,362 | 96 MB | ✅ |
| `third_party_cloudwatch_metric` | 264,474 | 68 MB | ✅ |
| `financial_normalization` | 30,081 | 49 MB | ✅ |
| `financial_forecast_history` | 130,498 | 48 MB | ✅ |
| `financial_normalization_current` | 11,433 | 33 MB | ✅ |
| **`r_financial_forecast_year_version`** | **136,898** | **24 MB** | **❌** |

> `V16` 头注释另记录：外部平台报「84 tables missing primary keys」，实测 lg_test 只有 7 张。脚本原文对差异给的是并列猜测而非结论——「84 很可能来自其它环境(prod/staging)或把视图/别的库算进去了」。**即"生产与测试 schema 可能不一致"是待验证项，不是已确认事实。**

---

## 13. 租户开通的种子机制

### 13.1 模板读取与占位符替换

`.../web/di/utils/JdbcReadUtils.java:19-30` 按**行**读取 SQL 文件成 `List<String>`，一行 = 一条 SQL。

`.../web/di/service/ScoreLevelServiceImpl.java:90-100`：

```java
List<String> list = JdbcReadUtils.bufferedReaderSQL("templates/di/initScoreLevel.sql");
for (String o : list) {
    scoreLevelId += 1;
    String sql = o.replace("organization_name", organizationId);
    sql = sql.replace("score_level_uuid", String.valueOf(scoreLevelId));
    sql = sql.replace("created_date", Instant.now().toString());
    sql = sql.replace("created_user", SecurityUtils.getUserId());
    jdbcTemplate.update(sql);              // 字符串替换后直接执行，无参数绑定
}
```

`ScoreWeightServiceImpl.java:90-96` 同款，但**无幂等守卫**（重复调用重复插入），且模板中的 `--` 注释行与空行也会被逐行执行。

### 13.2 6 个模板里只有 2 个是活的

| 模板 | 状态 |
|---|---|
| `initScoreLevel.sql` | ✅ 被 `ScoreLevelServiceImpl.java:90` 引用 |
| `initScoreWeight.sql` | ✅ 被 `ScoreWeightServiceImpl.java:90` 引用 |
| `initKpa.sql`（800 行） | ❌ **全仓零引用** |
| `initStage.sql` | ❌ 零引用 |
| `initRStageKpaCategory.sql` | ❌ 零引用 |
| `initRKpaCategoryWeight.sql` | ❌ 零引用 |

后 4 个的逻辑已被改写为"从数据库现有行克隆"：

- `StageServiceImpl.java:229-234`：`stageRepository.findAll()` 取**第 0 行**，用其 `organizationId` 过滤出该组织全部 stage 复制给新组织
- `KpaManagementServiceImpl.java:68-73`：同样 `findAll()` 取第 0 行的组织，复制其全部 kpa_category
- `KpaBusinessServiceImpl.java:127-129`：同样方式克隆分类权重
- `TechStackManagementServiceImpl.java:391`：从**硬编码的组织 ID** 克隆 category / tech_stack

其中 `StageServiceImpl.java:229`、`KpaManagementServiceImpl.java:68` 是**裸 `findAll()`，无 `ORDER BY`**；`KpaBusinessServiceImpl.java:123` 用的是 `findAllByOrderBySortAsc()`（带排序）但同样取 `.get(0)`。

**结论：新租户的配置种子不是版本化模板，而是运行时某个既存组织的当前快照；其中两处的源组织完全不确定。一旦某租户改了自己的配置，后续新建租户可能继承其改动。**

---

## 14. 组织删除的级联缺口

`.../web/system/service/OrganizationServiceImpl.java:244-275`，对 `findByTreeInId(id)` 返回的每个子树节点执行：

| 行 | 动作 |
|---|---|
| 249-254 | 角色软删 + 解绑用户 |
| 255-258 | 收集公司 → `deleteByCompanyId`（实际只删 `r_company_group` + colleague 关系，真正的级联在 `CompanyServiceImpl.java:976` **被注释掉**） |
| 259 | `userService.deleteByOrganizationId` → 仅 `is_deleted=true` 软删（`UserServiceImpl.java:1786-1794`），**不清 session / token** |
| 260 | **硬删** organization 行 |
| 261-264 | 删 4 张 `r_organization_*`（**在硬删之后**，顺序反了） |
| 265-272 | 删 7 张 DI 配置表 |

**未清理**：`company_group`（该 Service 根本没注入 `CompanyGroupRepository`）、`r_portfolio_user`、开通时创建的 `di_tech_stack_layer` / `tech_category` / `tech_stack`、`business_issues`、`company` 行本身。

---

## 15. Java：手写隔离的典型形态

### 15.1 Controller 只判空、不判归属

`java/CIOaas-api/gstdev-cioaas-web/.../web/fi/controller/FinancialStatementsController.java:93-99`

```java
@GetMapping(value = "/overview")
public Result<Map<String, Object>> overview(String companyId) {
  if (ObjectUtil.isEmpty(companyId)) return Result.fail("parameter error: company Id");
  return Result.success(financialOverviewService.getOverview(companyId));
}
```

同文件 `:85-91`（getAllAccept）、`:102-108`（metricsNeedAttention）、`:110-116`（revenueOverview）同一形状。

### 15.2 对照：唯一做了对象级授权的实现

`java/CIOaas-api/gstdev-cioaas-web/.../web/fi/service/PortfolioBenchmarkServiceImpl.java:86-95`

```java
private void assertCompaniesAccessible(List<String> companyIds) {
    String userId = SecurityUtils.getUserId();
    if (userId == null) {
        throw new BadRequestException("Not authenticated");
    }
    List<String> denied = userService.findInaccessibleCompanies(userId, companyIds);
    if (!denied.isEmpty()) {
        throw new BadRequestException("No access to company: " + denied.get(0));
    }
}
```

调用点 `:102`（`getSnapshot`）、`:189`（`getTrend`）。同文件 `:80-83` 的注释说明了它刻意不收窄的边界：

> ⚠️ 口径继承：Group Manager 分支对任意 companyId 放开（既有语义写的是"本组织下所有公司"但未校验组织归属）。本守卫不扩大也不收窄它；要按组织收口得改 `canAccessCompany` 本身，那会影响它的全部调用方。

---

## 16. Python：知识库召回实际下发的过滤条件

`python/CIOaas-python/source/rag/domain/repository/chunk_repository.py:66-90, 114-129` 组装后的等价 SQL：

```sql
-- 管理端
WHERE space_id = :sid
  AND (company_id IN (:allowed...) OR thread_id = :tid)
ORDER BY embedding <=> :vec LIMIT :n

-- 公司端普通用户
WHERE space_id = :sid AND created_by = :me
ORDER BY embedding <=> :vec LIMIT :n
```

> ⚠️ 同一文件 `:109-110` 的 docstring 仍写着「**无 company_id 过滤**：租户隔离由调用方按 company 圈定 space 范围保证（chunk 表已不存 company_id 列）」，而 `:79-80` 正在执行 `company_id.in_(...)`。**照该 docstring 改动召回逻辑会直接拆掉现有的行级过滤。**

---

## 17. 前端：切换组织靠回传口令重新登录

`web/CIOaas-web/src/pages/auth/chooseCompaniesApp/ChooseCompaniesAppPage.tsx:41-52`

```ts
const choose = (item: any) => {
  dispatch({ type: 'login/login', payload: {
    username: item?.email,
    password: atob(item?.pwd),          // ← 后端把口令回传给前端
    type: roleType == 1 ? 'admin' : 'inviteUser',
    userId: roleType == 1 ? item.userId : item?.id,
    roleType,
  }});
};
```

数据来源即 §6.1 那个无授权校验的接口。**修复方向是服务端令牌交换（token exchange），而不是回传口令。**
