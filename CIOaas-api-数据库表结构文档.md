# CIOaas-API 数据库表结构文档

> 基于 JPA 实体类自动扫描生成
> 生成日期: 2026-02-28
> 项目路径: `D:/github-code/LG/CIOaas-api`

---

## 目录

- [一、继承关系说明](#一继承关系说明)
- [二、SYSTEM 领域](#二system-领域)
- [三、FI (Financial Intelligence) 领域](#三fi-financial-intelligence-领域)
- [四、DI (Digital Infrastructure) 领域](#四di-digital-infrastructure-领域)
- [五、ETL 领域](#五etl-领域)
- [六、Currency 领域](#六currency-领域)
- [七、Storage 领域](#七storage-领域)
- [八、Logging 领域](#八logging-领域)
- [九、SQS 领域](#九sqs-领域)
- [十、Scheduler 领域](#十scheduler-领域)
- [十一、Index 领域](#十一index-领域)
- [十二、汇总统计](#十二汇总统计)

---

## 一、继承关系说明

大部分实体继承自以下基类：

- **AbstractEntity**: 提供 `id` (String, length=36, UUID) 主键
- **AbstractAuditingEntity** extends AbstractEntity: 继承 `id`, 并添加 4 个审计字段
- **AbstractCustomEntity**: 独立基类(不继承AbstractEntity), 仅提供 4 个审计字段, 不提供 `id`

**公共审计字段**(标注 **(继承)** 的字段):

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| createdAt | Instant | created_at | 创建时间 (不可更新) |
| createdBy | String | created_by | 创建人 (length=36, 不可更新) |
| updatedAt | Instant | updated_at | 更新时间 |
| updatedBy | String | updated_by | 更新人 (length=36) |

> 以下各表中, 继承字段将以 *(继承)* 标注, 部分表格省略继承字段以减少重复。

---

## 二、SYSTEM 领域

包路径: `com.gstdev.cioaas.web.system.domain`

### 2.1 表名: user (类名: User)

用户表, 存储系统用户信息。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | user_id | 主键, UUID, length=36 |
| username | String | username | 用户名, length=120, 不为空 |
| password | String | password | 密码, length=255 |
| displayName | String | display_name | 显示名称, length=600 |
| firstName | String | first_name | 名, length=225 |
| lastName | String | last_name | 姓, length=225 |
| accessKey | String | access_key | 访问密钥, length=40 |
| secretKey | String | secret_key | 秘密密钥, length=80 |
| roleType | Integer | role_type | 角色类型, length=1 |
| email | String | email | 邮箱, length=100, unique, @Email |
| emailConfirmed | Boolean | email_confirmed | 邮箱是否确认 |
| phoneNumber | String | phone_number | 手机号, length=20, unique |
| phoneNumberConfirmed | Boolean | phone_number_confirmed | 手机号是否确认 |
| avatarUrl | String | avatar_url | 头像URL, length=1024 |
| lastLoginDate | Instant | last_login_date | 最后登录日期 |
| lastLoginIp | String | last_login_ip | 最后登录IP, length=255 |
| lastLoginLocation | String | last_login_location | 最后登录位置, length=255 |
| loginFailTimes | Integer | login_fail_times | 登录失败次数, length=10 |
| status | Integer | status | 状态, length=2 |
| strengths | String | strengths | 优势 |
| stripeCustomerId | String | stripe_customer_id | Stripe客户ID, length=50 |
| companyId | String | company_id | 公司ID |
| activateToken | String | activate_token | 激活Token, length=255 |
| dTimezone | DTimezone | d_timezone_id | 时区(ManyToOne, LAZY) |
| deleted | Boolean | is_deleted | 是否删除, 默认false |
| tempPassword | Boolean | temp_password | 是否临时密码, 默认false |
| loginDate | Instant | login_date | 登录日期 |
| valid | String | valid | 是否有效(0-真实用户, 1-虚拟用户), 默认'0' |
| pwd | String | pwd | 密码, length=255 |
| view | String | view | 视图模式(card/list), 默认'card' |
| currency | String | currency | 货币, length=10 |
| acceptAt | Instant | accept_at | 接受时间 |
| profileId | FileObject | profile_id | 头像文件(ManyToOne, LAZY) |
| inviterId | String | inviter_id | 邀请人ID, length=36 |

**关联中间表**: `r_user_role` (user_id <-> role_id), `r_user_menu` (user_id <-> menu_id)

---

### 2.2 表名: role (类名: Role)

角色表, 软删除过滤 `@SQLRestriction("is_deleted = false")`。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| name | String | name | 角色名称, 不为空 |
| remark | String | remark | 备注 |
| permission | String | permission | 权限 |
| sort | Integer | sort | 排序 |
| isSuperAdmin | boolean | is_super_admin | 是否超级管理员, 默认false |
| key | String | role_key | 角色Key, unique |
| deleted | Boolean | is_deleted | 是否删除, 默认false |
| roleType | String | role_type | 角色类型, 默认"admin" |

**关联中间表**: `r_role_menu` (role_id <-> menu_id)

---

### 2.3 表名: menu (类名: Menu)

菜单表, 软删除过滤 `@SQLRestriction("is_deleted = false")`。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| name | String | name | 菜单名称 |
| sort | Long | sort | 排序, 默认999 |
| path | String | path | 路径 |
| code | String | code | 代码 |
| type | Integer | type | 类型 (0-主菜单, 1-子菜单, 2-功能) |
| permission | String | permission | 权限 |
| icon | String | icon | 图标 |
| hidden | Boolean | hidden | 是否隐藏, 默认false |
| pid | String | pid | 父级ID |
| level | int | level | 层级 |
| remark | String | remark | 备注 |
| deleted | Boolean | is_deleted | 是否删除, 默认false |
| category | Integer | category | 分类 (1-Head Menu, 2-Top Right Menu, 3-client payment menu) |
| enable | String | enable | 是否启用 |

---

### 2.4 表名: organization (类名: Organization)

组织表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| name | String | name | 名称, length=120, 不为空 |
| logoUrl | String | logo_url | Logo URL, length=1024 |
| websiteUrl | String | website_url | 网站URL, length=1024 |
| code | String | code | 代码, length=1024 |
| pid | String | pid | 父级ID |
| description | String | description | 描述 |

---

### 2.5 表名: organize (类名: Organize)

部门表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | organize_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| companyId | String | company_id | 公司ID |

---

### 2.6 表名: company (类名: Invite)

公司表 (注意: 类名为Invite, 表名为company)。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | company_id | 主键, UUID, length=36 |
| displayName | String | display_name | 显示名称, length=255 |
| firstName | String | admin_first_name | 管理员名, length=60 |
| lastName | String | admin_last_name | 管理员姓, length=60 |
| company | String | company_name | 公司名称, length=120 |
| email | String | email | 邮箱, length=80 |
| status | Integer | status | 状态 (1-resolve, 2-pend, 3-reject, 4-pending activation), 默认2 |
| logo | String | logo | Logo URL, length=1024 |
| kpaUpdatedAt | Instant | kpa_updated_at | KPA更新时间 |
| type | Integer | type | 类型, 默认1, 不可更新 |
| archived | Boolean | archived | 是否归档, 默认false |
| category | Integer | category | 分类, 默认0 |
| etlRemindTime | Instant | etl_remind_time | ETL提醒时间 |
| customerId | String | customer_id | 客户ID |
| companyUrl | String | company_url | 公司网址 |
| companyType | Integer | company_type | 公司类型, 默认1 |
| description | String | description | 描述(TEXT) |
| logoId | String | logo_id | Logo文件ID, length=36 |
| logoName | String | logo_name | Logo文件名, length=1024 |
| notificationUserId | String | notification_user_id | 通知用户ID, length=36 |
| revenueRecognition | Integer | revenue_recognition | 收入确认方式 (1-Last Month, 2-Last Quarter, 3-TTM), 默认1 |
| accountMethod | String | account_method | 会计方法 (1-Accrual, 2-Cash) |
| companyStatus | Integer | company_status | 公司状态, 默认THRIVING |
| currency | String | currency | 货币代码, length=8, 默认'USD' |

---

### 2.7 表名: project (类名: Project)

项目表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | project_id | 主键, UUID, length=36 |
| name | String | name | 名称, length=120, 不为空 |
| description | String | description | 描述(TEXT) |
| logo | String | logo | Logo URL, length=1024 |
| dashboardId | String | dashboard_id | 仪表板ID, length=80 |
| dashboardName | String | dashboard_name | 仪表板名称, length=80 |
| status | Integer | status | 状态, 默认1 |
| invite | Invite | company_id | 所属公司(ManyToOne, LAZY) |
| timedTaskOpen | Boolean | timed_task_open | 定时任务是否开启, 默认true |
| type | Integer | type | 类型, 默认1, 不可更新 |
| showBigDataModule | Boolean | show_big_data_module | 是否显示大数据模块, 默认false |
| sprintSetUp | Integer | sprint_set_up | Sprint设置, 默认0 |
| logoId | String | logo_id | Logo文件ID, length=36 |
| logoName | String | logo_name | Logo文件名, length=1024 |

---

### 2.8 表名: r_user_project (类名: UserProject)

用户-项目关联表, 复合主键。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| userId | String | user_id | 用户ID (复合主键) |
| projectId | String | project_id | 项目ID (复合主键) |
| roleType | Integer | role_type | 角色类型 |

---

### 2.9 表名: company_group (类名: CompanyGroup)

公司组/投资组合表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | company_group_id | 主键, UUID, length=36 |
| name | String | name | 组名称 |
| fund | float | fund | 基金金额, 默认0 |
| thesis | String | thesis | 投资论点 |
| organizationId | String | organization_id | 组织ID |

---

### 2.10 表名: company_investment (类名: CompanyInvestment)

公司投资表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| companyGroupId | String | company_group_id | 公司组ID |
| order | int | show_order | 显示顺序 |
| investmentDate | String | investment_date | 投资日期 |
| creditMemoTransactionDate | String | credit_memo_transaction_date | 信用备忘录交易日期 |
| maturityDate | String | maturity_date | 到期日期 |
| valuation | BigDecimal | valuation | 估值 |
| cashInvestment | BigDecimal | cash_investment | 现金投资 |
| creditInvestment | BigDecimal | credit_investment | 信用投资 |
| investmentVehicle | String | investment_vehicle | 投资工具 |
| conversionStatus | String | conversion_status | 转换状态 |
| interest | BigDecimal | interest | 利率 |
| conversionVehicle | String | conversion_vehicle | 转换工具(TEXT) |
| preemptiveRight | String | preemptive_right | 优先购买权(TEXT) |
| redemptionRights | String | redemption_rights | 赎回权(TEXT) |
| dividends | String | dividends | 股息 |
| compoundingMechanism | String | compounding_mechanism | 复利机制 |
| liquidationPreference | String | liquidation_preference | 清算优先权(TEXT) |
| cashEntity | String | cash_entity | 现金实体 |
| creditMemoHolder | String | credit_memo_holder | 信用备忘录持有人 |
| warrantSignedDate | String | warrant_signed_date | 认股权签署日期 |
| warrantExpirationDate | String | warrant_expiration_date | 认股权到期日期 |
| warrantStrikePrice | BigDecimal | warrant_strike_price | 认股权行权价 |
| warrantPercentage | BigDecimal | warrant_percentage | 认股权百分比 |
| warrantNo | String | warrant_no | 认股权编号 |
| warrantNotes | String | warrant_notes | 认股权备注 |
| currency | String | currency | 货币代码, length=8 |

---

### 2.11 表名: company_investment_document (类名: CompanyInvestmentDocument)

公司投资文档表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| investment | CompanyInvestment | investment_id | 所属投资(ManyToOne, 不为空) |
| type | Integer | type | 文档类型 |
| fileId | String | file_id | 文件ID |

---

### 2.12 表名: company_modules_settings (类名: CompanyModulesSettings)

公司模块设置表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | company_modules_settings_id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| fiStatus | boolean | fi_status | FI模块状态 |
| fiWeight | float | fi_weight | FI模块权重 |
| diStatus | boolean | di_status | DI模块状态 |
| diWeight | float | di_weight | DI模块权重 |

---

### 2.13 表名: company_subscription (类名: CompanySubscription)

公司订阅表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | company_subscription_id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| subscriptionTemplateId | String | subscription_template_id | 订阅模板ID |
| status | String | status | 状态 |
| startTime | Instant | start_time | 开始时间 |
| endTime | Instant | end_time | 结束时间 |
| paymentIntentId | String | paymentIntent_id | 支付意图ID |
| count | Integer | count | 数量 |
| paymentOrderId | String | payment_order_id | 支付订单ID |
| stripeSubscriptionId | String | stripe_subscription_id | Stripe订阅ID |
| isUnsubscribe | Boolean | is_unsubscribe | 是否退订, 默认false |
| isRemind | Boolean | is_remind | 是否提醒, 默认false |

---

### 2.14 表名: subscription_template (类名: SubscriptionTemplate)

订阅模板表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | subscription_template_id | 主键, UUID, length=36 |
| name | String | name | 名称, length=255 |
| description | String | description | 描述, length=255 |
| period | String | period | 周期, length=255 |
| days | Integer | days | 天数 |
| currency | String | currency | 货币, 默认'usd' |
| price | float | price | 价格 |
| discount | float | discount | 折扣 |
| status | String | status | 状态(0-可用), 默认'0' |
| type | String | type | 类型(0-全部), 默认'0' |
| sort | Integer | sort | 排序 |
| isDeleted | Boolean | is_deleted | 是否删除, 默认false |
| pid | String | pid | 历史记录同pid |
| stripeProductId | String | stripe_product_id | Stripe产品ID, length=36 |
| stripePriceId | String | stripe_price_id | Stripe价格ID, length=36 |

---

### 2.15 表名: document (类名: Document)

文档表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | document_id | 主键, UUID, length=36 |
| name | String | name | 文档名称 |
| folder | Folder | folder_id | 所属文件夹(ManyToOne, LAZY) |
| fileId | String | file_id | 文件ID |
| project | Project | project_id | 所属项目(ManyToOne, LAZY) |
| invite | Invite | company_id | 所属公司(ManyToOne, LAZY) |
| createdAt | Instant | created_at | 创建时间 |
| createdBy | String | created_by | 创建人, length=36 |
| type | Integer | type | 类型 (1-Company level, 2-Project level, 6-KPA review) |
| kpaCategoryId | String | kpa_category_id | KPA分类ID |
| kpaReview | KpaReview | kpa_review_id | 关联KPA评审(ManyToOne, LAZY) |
| organizationId | String | organization_id | 组织ID |
| fileType | String | file_type | 文件类型 |

---

### 2.16 表名: folder (类名: Folder)

文件夹表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | Integer | folder_id | 主键, 自增 |
| name | String | name | 文件夹名称 |
| companyId | String | company_id | 公司ID |
| deleted | boolean | is_deleted | 是否已删除, 默认false |
| isConstant | boolean | is_constant | 是否固定, 默认false |
| sort | Integer | sort | 排序 |

---

### 2.17 表名: company_documentation (类名: CompanyDocumentation)

公司文档表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID, 不为空, length=36 |
| folderId | String | folder_id | 文件夹ID, length=36 |
| categoryId | String | category_id | 分类ID, length=36 |
| fileId | String | file_id | 文件ID, length=36 |
| fileName | String | file_name | 文件名, length=255 |
| fileType | String | file_type | 文件类型, length=36 |

---

### 2.18 表名: company_documentation_category (类名: CompanyDocumentationCategory)

公司文档分类表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, length=36 |
| name | String | name | 分类名称 |
| showOrder | Integer | show_order | 显示顺序 |

---

### 2.19 表名: company_documentation_folder (类名: CompanyDocumentationFolder)

公司文档文件夹表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, length=36 |
| name | String | name | 文件夹名称 |
| permission | String | permission | 权限 (1-PM/PGM, 2-Company Admin, 3-Company User, 可组合), length=36 |
| showOrder | Integer | show_order | 显示顺序 |
| showInAdd | boolean | show_in_add | 是否在添加时显示, 默认true |

**关联中间表**: `r_documentation_folder_category` (folder_id <-> category_id)

---

### 2.20 表名: dictionary (类名: Dictionary)

数据字典表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| dictionaryId | String | dictionary_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| type | String | type | 类型 |
| key | String | key | 键 |
| value | String | value | 值 |
| code | String | code | 代码, unique |
| parentId | String | parent_id | 父级ID |
| sequence | Integer | sequence | 排序 |
| icon | String | icon | 图标 |
| remark | String | remark | 备注, length=5000 |
| level | Integer | level | 层级 |
| link | String | link | 链接, length=5000 |

---

### 2.21 表名: d_timezone (类名: DTimezone)

时区字典表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | Integer | d_timezone_id | 主键 |
| zoneName | String | zone_name | 时区名称, length=150 |
| gmtOffset | float | gmt_offset | GMT偏移量 |
| displayName | String | display_name | 显示名称, length=150 |
| gmtOffsetName | String | gmt_offset_desc | GMT偏移描述, length=150 |

---

### 2.22 表名: d_tool (类名: DTool)

工具配置表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | d_tool_id | 主键, UUID, length=36 |
| name | String | name | 工具名称 |
| type | String | type | 工具类型 |
| code | String | code | 工具代码, unique, 不为空 |
| logoUrl | String | logo_url | Logo URL, length=1024 |
| docUrl | String | doc_url | 文档URL |
| productUrl | String | product_url | 产品URL |
| extractFrequency | Integer | extract_frequency | 提取频率 |
| parameters | String | parameters | 参数(TEXT) |
| description | String | description | 描述(TEXT) |
| active | Integer | active | 是否激活 |
| sequence | Integer | sequence | 排序, 不为空 |
| logoId | String | logo_id | Logo文件ID, length=36 |
| logoName | String | logo_name | Logo文件名, length=1024 |

---

### 2.23 表名: datasource (类名: Datasource)

数据源配置表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | datasource_id | 主键, UUID, length=64 |
| schemaName | String | schema_name | Schema名称 |
| dTool | DTool | tool_id | 关联工具(ManyToOne, 不为空) |
| companyId | String | company_id | 公司ID, 不为空 |
| projectId | String | project_id | 项目ID, 不为空 |
| itemName | String | item_name | 项目名 |
| parameters | String | parameters | 参数(TEXT) |
| extractFrequency | Integer | extract_frequency | 提取频率 |
| fromDate | Instant | from_date | 开始日期 |
| toDate | Instant | to_date | 结束日期 |
| status | String | status | 状态 |
| owner | String | owner | 所有者 |
| timeType | String | time_type | 时间类型 |
| timeData | String | time_data | 时间数据 |
| dagId | String | dag_id | DAG ID |
| dictionaryCode | String | dictionary_code | 字典代码 |
| accessToken | String | access_Token | 访问令牌 |
| repository | String | repository | 仓库 |
| company | String | company | 公司 |
| project | String | project | 项目 |
| targetAddresses | String | target_addresses | 目标地址 |
| tag | String | tag | 标签 |
| awsAccessKeyId | String | aws_access_key_id | AWS Access Key ID |
| awsSecretAccessKey | String | aws_secret_access_key | AWS Secret Access Key |
| value | String | value | 值 |
| name | String | name | 名称 |
| lastSendEmailDate | String | last_send_email_date | 最后发送邮件日期, length=20 |
| tokenRefreshStatus | Boolean | token_refresh_status | Token刷新状态 |
| lastTokenRefreshStatus | Boolean | last_token_refresh_status | 上次Token刷新状态 |
| isTokenStatusSentEmail | Boolean | is_token_status_sent_email | Token状态是否已发邮件 |

---

### 2.24 表名: datasource_extract_log (类名: DatasourceExtractLog)

数据源提取日志表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | datasource_extract_log_id | 主键, UUID, length=36 |
| datasourceId | Datasource | datasource_id | 关联数据源(ManyToOne, 不为空) |
| triggeredAt | Instant | triggered_at | 触发时间 |
| triggeredMethod | Integer | triggered_method | 触发方式, 默认0 |
| triggeredBy | String | triggered_by | 触发人 |

---

### 2.25 表名: email (类名: Email)

邮件表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| type | int | type | 类型 |
| emailType | Integer | email_type | 邮件类型 |
| senderEmail | String | sender_email | 发送者邮箱, length=200 |
| receiverEmail | String | receiver_email | 接收者邮箱, length=200 |
| subject | String | subject | 主题, length=255 |
| body | String | body | 正文, length=1000 |
| emailContext | String | email_context | 邮件上下文, length=1000 |
| status | int | status | 状态 |
| companyId | String | company_id | 公司ID, length=36 |
| sprintId | String | sprint_id | Sprint ID |
| operator | String | operator | 操作人, length=600 |
| templateName | String | template_name | 模板名称, length=600 |

---

### 2.26 表名: white_list_user (类名: WhiteListUser)

白名单用户表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| email | String | email | 邮箱, length=100, @Email |
| type | String | type | 类型, length=36 |

---

### 2.27 表名: portfolio_capacity (类名: PortfolioCapacity)

投资组合能力表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| userId | String | user_id | 用户ID, length=36 |
| portfolioId | String | portfolio_id | 投资组合ID, length=36 |
| order | int | show_order | 显示顺序 |
| checked | Boolean | checked | 是否勾选, 默认false |
| catalog | PortfolioCapacityCatalog | portfolio_capacity_catalog_id | 关联能力目录(ManyToOne) |

---

### 2.28 表名: portfolio_capacity_catalog (类名: PortfolioCapacityCatalog)

投资组合能力目录表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | Integer | id | 主键, 自增 |
| text | String | text | 文本, length=36 |
| showOrder | Integer | show_order | 显示顺序 |

---

### 2.29 表名: r_project_tech_stack (类名: ProjectTechStack)

项目-技术栈关联表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | r_project_tech_stack_id | 主键, UUID |
| projectId | String | project_id | 项目ID |
| techStackTypeId | String | tech_stack_type_id | 技术栈类型ID, 不为空 |
| techStackId | String | tech_stack_id | 技术栈ID |

---

### 2.30 表名: project_tech_stack_comment (类名: ProjectTechStackComment)

项目技术栈评论表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | project_tech_stack_comment_id | 主键, UUID, length=36 |
| projectId | String | project_id | 项目ID |
| adminComments | String | admin_comments | 管理员评论(TEXT) |
| adminId | String | admin_id | 管理员ID |
| adminCommentTime | Date | admin_comment_time | 管理员评论时间 |
| userComments | String | user_comments | 用户评论(TEXT) |
| userId | String | user_id | 用户ID |
| userCommentTime | Date | user_comment_time | 用户评论时间 |
| adminCommentsHtml | String | admin_comments_html | 管理员评论HTML(TEXT) |
| userCommentsHtml | String | user_comments_html | 用户评论HTML(TEXT) |

---

### 2.31 表名: project_weight (类名: ProjectWeight)

项目权重表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | project_weight_id | 主键, UUID, length=36 |
| projectId | String | project_id | 项目ID |
| weight | float | weight | 权重 |

---

### 2.32 表名: business_issues (类名: BusinessIssues)

业务问题/审批表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | Integer | business_issues_id | 主键, 自增 |
| companyId | String | company_id | 公司ID |
| portfolioId | String | portfolio_id | 投资组合ID |
| organizationId | String | organization_id | 组织ID |
| requestType | Integer | request_type | 请求类型 (1-Request for Funding, 2-Request for Approval), 默认1 |
| submissionTime | Instant | submission_time | 提交时间 |
| state | Integer | state | 审批状态 (0-Pending, 1-Approved, 2-Rejected), 默认0 |
| status | Integer | status | 开关状态 (0-Open, 1-Closed), 默认0 |
| information | String | information | 信息(TEXT) |
| approvalType | Integer | approval_type | 审批类型 (1-6对应不同类型) |
| submissionBy | String | submission_by | 提交人 |
| submissionByIp | String | submission_by_ip | 提交人IP |
| responseBy | String | response_by | 回复人 |
| responseByIp | String | response_by_ip | 回复人IP |
| responseTime | Instant | response_time | 回复时间 |

---

### 2.33 表名: etl_config (类名: EtlConfig)

ETL配置表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| key | String | key | 键 |
| goodValue | float | good_value | 良好值 |
| passValue | float | pass_value | 通过值 |

---

### 2.34 表名: etl_project_status (类名: EtlProjectStatus)

ETL项目状态表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键 |
| tapName | String | tap_name | Tap名称 |
| tapStatus | String | tap_status | Tap状态 |
| projectId | String | project_id | 项目ID |
| updateTime | Instant | update_time | 更新时间 |

---

### 2.35 表名: etl_score (类名: EtlScore)

ETL评分表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | etl_score_id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| projectId | String | project_id | 项目ID |
| companyEtlWeight | float | company_etl_weight | 公司ETL占比 |
| companyEtlScore | float | company_etl_score | 公司ETL分数 |
| projectWeight | float | project_weight | 产品在公司占比 |
| projectScore | float | project_score | 产品分数 |
| etlScoreTargetId | String | etl_score_target_id | 指标ID |
| targetCode | String | target_code | 指标code |
| targetScore | float | target_score | 指标原始分数 |
| targetRule | String | target_rule | 指标规则 |
| projectTargetValue | float | project_target_value | 产品中指标值 |
| projectTargetWeight | float | project_target_weight | 指标对比规则得分 |
| projectTargetScore | float | project_target_score | 最终产品指标所得分数 |
| status | String | status | 状态 |
| batch | String | batch | 批次 |

---

### 2.36 表名: etl_score_target (类名: EtlScoreTarget)

ETL评分指标表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | etl_score_target_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| code | String | code | 代码 |
| rule | String | rule | 规则(TEXT) |

---

### 2.37 表名: etl_score_type (类名: EtlScoreType)

ETL评分类型表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | etl_score_type_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| score | float | score | 分数 |
| weight | float | weight | 权重 |
| pid | String | pid | 父级ID |
| etlScoreTargetId | String | etl_score_target_id | 指标ID |

---

### 2.38 SYSTEM 领域关联表

| 表名 | 类名 | 主要字段 | 说明 |
|------|------|---------|------|
| r_company_group | RCompanyGroup | company_id, company_group_id, status | 公司-组关联 |
| r_company_role | RCompanyRole | company_id, role_id | 公司-角色关联 (软删除) |
| r_organization_company | ROrganizationCompany | organization_id, company_id | 组织-公司关联 |
| r_organization_menu | ROrganizationMenu | organization_id, menu_id | 组织-菜单关联 |
| r_organization_role | ROrganizationRole | organization_id, role_id | 组织-角色关联 |
| r_organization_user | ROrganizationUser | organization_id, user_id | 组织-用户关联 |
| r_organize_user | ROrganizeUser | organize_id, user_id | 部门-用户关联 |
| r_portfolio_user | RPortfolioUser | user_id, company_group_id | 投资组合-用户关联 |
| r_role_company | RRoleCompany | company_id, role_id | 角色-公司关联 |
| r_subscription_menu | RSubscriptionMenu | subscription_template_id, menu_id | 订阅-菜单关联 |

---

## 三、FI (Financial Intelligence) 领域

包路径: `com.gstdev.cioaas.web.fi.domain`

### 公共继承字段 (FinanceManualDataAbstract)

以下字段被 `FinanceManualData`, `FinanceManualDataTemp`, `FinancialAcceptForecastCache`, `FinancialForecastCache`, `FinancialForecastCurrent`, `FinancialForecastHistory` 共同继承:

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | finance_manual_data_id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| colKey | String | colKey | 列键 |
| date | String | date | 日期 |
| versionAt | Instant | version_at | 版本时间 |
| grossRevenue | BigDecimal | gross_revenue | 总收入 (precision=50, scale=10) |
| cogs | BigDecimal | cogs | 销售成本 |
| operatingExpenses | BigDecimal | operating_expenses | 运营费用 |
| capitalizeRd | boolean | is_capitalize_rd | 是否资本化研发 |
| rdExpensesPercent | BigDecimal | rd_expenses_percent | 研发费用百分比 |
| smExpensesPercent | BigDecimal | sm_expenses_percent | 销售费用百分比 |
| gaExpensesPercent | BigDecimal | ga_expenses_percent | 管理费用百分比 |
| rdPayrollPercent | BigDecimal | rd_payroll_percent | 研发工资百分比 |
| smPayrollPercent | BigDecimal | sm_payroll_percent | 销售工资百分比 |
| gaPayrollPercent | BigDecimal | ga_payroll_percent | 管理工资百分比 |
| miscellaneousOperatingExpenses | BigDecimal | miscellaneous_operating_expenses | 杂项运营费用 |
| otherExpenses | BigDecimal | other_expenses | 其他费用 |
| cash | BigDecimal | cash | 现金 |
| accountsReceivable | BigDecimal | accounts_receivable | 应收账款 |
| assetsOther | BigDecimal | assets_Other | 其他资产 |
| capitalizedRd | BigDecimal | capitalized_rd | 资本化研发 |
| accountsPayable | BigDecimal | accounts_payable | 应付账款 |
| longTermDebt | BigDecimal | long_term_debt | 长期债务 |
| liabilitiesOther | BigDecimal | liabilities_other | 其他负债 |
| plFileId | String | pl_file_id | 损益表文件ID |
| bsFileId | String | bs_file_id | 资产负债表文件ID |
| proformaFileId | String | proforma_file_id | 预估表文件ID |
| currency | String | currency | 货币, length=8 |

---

### 3.1 表名: company_forecast (类名: CompanyForecast)

公司预测表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| date | String | date | 日期 |
| forecast | BigDecimal | forecast | 预测值 |
| currency | String | currency | 货币, length=8 |

---

### 3.2 表名: company_quickbooks (类名: CompanyQuickbooks)

公司QuickBooks集成表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | company_quickbooks_id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| realmId | String | realm_id | QuickBooks Realm ID |
| refreshToken | String | refresh_token | 刷新令牌 |
| status | String | status | 授权状态: success/fail |
| SMPayroll | float | SM_payroll | 销售营销工资比例 |
| GAPayroll | float | GA_payroll | 管理工资比例 |
| RDPayroll | float | RD_payroll | 研发工资比例 |
| payrollConfig | String | payroll_config | 工资配置 |
| isRemind | Boolean | is_remind | 是否提醒, 默认false |
| isFirst | Boolean | is_first | 是否首次, 默认false |
| mode | String | mode | 模式, 默认'Manual' |
| cover | Boolean | cover | 是否覆盖, 默认true |
| updateModeAt | Instant | update_mode_at | 模式更新时间 |
| view | String | view | 视图, 默认'Annually' |

---

### 3.3 表名: company_quickbooks_data (类名: CompanyQuickbooksData)

公司QuickBooks数据表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | company_quickbooks_data_id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| score | float | score | 评分 |
| expression | String | expression | 表达式 |
| color | String | color | 颜色 |
| rank | String | rank | 等级 |
| lastUpdated | String | last_updated | 最后更新时间 |
| mode | String | mode | 模式 (Automatic/Manual) |
| ARR | String | arr | 年度经常性收入 |
| revGrowthLTM | String | rev_growth_ltm | 近12个月收入增长率 |
| rule | String | rule | Rule of 40 |
| grossMarginLTM | String | gross_margin_ltm | 近12个月毛利率 |
| salesEfficiency | String | sales_efficiency | 销售效率 |
| cash | String | cash | 现金 |
| AR | String | ar | 应收账款 |
| DeltaAR | String | delta_ar | AR变化量 |
| longTermDebt | String | long_term_debt | 长期债务 |
| burnRate | String | burn_rate | 烧钱率 |
| runway | String | runway | 跑道 Runway (mos) |
| pullTime | Date | pull_time | 拉取时间 |
| currency | String | currency | 货币, length=8 |

---

### 3.4 表名: finance_manual_data (类名: FinanceManualData)

财务手动数据表。继承 FinanceManualDataAbstract 全部字段 + 自有字段:

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| *(继承28个字段)* | | | *见上方公共字段表* |
| state | String | state | 状态 (length=1). 0: 编辑中; 其他: 使用中 |

---

### 3.5 表名: finance_manual_data_temp (类名: FinanceManualDataTemp)

财务手动数据临时表。继承 FinanceManualDataAbstract 全部字段 + 自有字段:

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| *(继承28个字段)* | | | *见上方公共字段表* |
| senderName | String | sender_name | 发送邮件管理员名 |
| sendDate | Date | send_date | 发送日期 |
| senderEmail | String | sender_email | 管理员邮箱 |
| reviewerName | String | reviewer_name | 审核者名称 |
| reviewDate | Date | review_date | 审核日期 |
| reviewerEmail | String | reviewer_email | 审核者邮箱 |
| state | String | state | 状态 |
| batchNo | String | batch_no | 批次号, length=36 |
| userType | Integer | user_type | 用户类型 |

---

### 3.6 表名: finance_manual_data_alert (类名: FinanceManualDataAlert)

财务手动数据告警表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| userId | String | user_id | 用户ID |
| msg | String | msg | 消息内容 |
| level | Short | level | 等级 |
| status | Short | status | 状态 |
| triggerTime | Instant | trigger_time | 触发时间 |
| schedulerId | String | scheduler_id | 调度任务ID, length=36 |

---

### 3.7 表名: finance_manual_data_email (类名: FinanceManualDataEmail)

财务手动数据邮件表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, length=36 |
| senderName | String | sender_name | 发送者名称 |
| sendDate | Date | send_date | 发送日期 |
| senderEmail | String | sender_email | 发送者邮箱 |
| reviewerName | String | reviewer_name | 审核者名称 |
| reviewDate | Date | review_date | 审核日期 |
| reviewerEmail | String | reviewer_email | 审核者邮箱 |
| state | String | state | 状态 (0-未审核, 1-已批准, 2-已拒绝, 3-已编辑) |
| batchId | String | batch_id | 批次ID, length=36 |
| batchState | String | batch_state | 批次状态 (1-邮件已发送; null-未发送) |

---

### 3.8 表名: financial_normalization (类名: FinancialNormalization)

财务归一化表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| date | String | date | 日期, length=20 |
| mode | String | mode | 模式 |
| source_id | String | source_id | 来源ID, length=36 |
| revenue | BigDecimal | revenue | 收入 |
| cogs | BigDecimal | cogs | 销售成本 |
| opex | BigDecimal | opex | 运营费用 |
| otherExpenses | BigDecimal | other_expenses | 其他费用 |
| capitalizedRdMonthly | BigDecimal | capitalized_rd_monthly | 每月资本化研发 |
| cash | BigDecimal | cash | 现金 |
| accountsReceivable | BigDecimal | accounts_receivable | 应收账款 |
| otherAssets | BigDecimal | other_assets | 其他资产 |
| accountsPayable | BigDecimal | accounts_payable | 应付账款 |
| longTermDebt | BigDecimal | long_term_debt | 长期债务 |
| otherLiabilities | BigDecimal | other_liabilities | 其他负债 |
| grossProfit | BigDecimal | gross_profit | 毛利润 |
| grossMargin | BigDecimal | gross_margin | 毛利率 |
| ebitda | BigDecimal | ebitda | EBITDA |
| netIncome | BigDecimal | net_income | 净收入 |
| monthlyRunway | BigDecimal | monthly_runway | 每月跑道 |
| ruleOf40 | BigDecimal | rule_of_40 | Rule of 40 |
| mrrYoyGrowthRate | BigDecimal | mrr_yoy_growth_rate | MRR年同比增长率 |
| netProfitMargin | BigDecimal | net_profit_margin | 净利润率 |
| salesEfficiencyRatio | BigDecimal | sales_efficiency_ratio | 销售效率比 |
| arr | BigDecimal | arr | 年度经常性收入 |
| monthlyNetBurnRate | BigDecimal | monthly_net_burn_rate | 每月净烧钱率 |
| debtAssetsRatio | BigDecimal | debt_assets_ratio | 资产负债率 |
| cashOnHand | BigDecimal | cash_on_hand | 手持现金 |
| mrr | BigDecimal | mrr | 月度经常性收入 |
| newMrrLtm | BigDecimal | new_mrr_ltm | 近12个月新MRR |
| capitalizedRdTotal | BigDecimal | capitalized_rd_total | 资本化研发总计 |
| assets | BigDecimal | assets | 总资产 |
| liabilities | BigDecimal | liabilities | 总负债 |
| runwayLeft | BigDecimal | runway_left | 剩余跑道 |
| endOfRunway | String | end_of_runway | 跑道终点, length=20 |
| endOfRunwaySource | String | end_of_runway_source | 跑道终点来源(TEXT) |
| arrSource | String | arr_source | ARR数据来源(TEXT, JSON) |
| capitalizedRdTotalSource | String | caplitalized_rd_total_source | 资本化研发总计来源(TEXT) |
| lastYearMrrSource | String | last_year_mrr_source | 去年MRR来源(TEXT) |
| lastMrrSource | String | last_mrr_source | 最近MRR来源(TEXT) |
| recognition | Integer | recognition | 识别标识 |
| qboBsBatchId | String | qbo_bs_batch_id | QBO资产负债表批次ID |
| qboPlBatchId | String | qbo_pl_batch_id | QBO损益表批次ID |
| sourceFidata | String | source_fidata | 源财务数据(TEXT) |

---

### 3.9 表名: financial_normalization_version (类名: FinancialNormalizationVersion)

财务归一化版本表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| currency | String | currency | 货币, length=50 |
| recognition | Integer | recognition | 识别标识 |
| source | String | source | 来源, not null |
| versionAt | Instant | version_at | 版本时间, not null |
| accountMethod | String | account_method | 会计方法 |

---

### 3.10 表名: r_financial_normalization (类名: FinancialNormalizationRef)

财务归一化关联表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| versionId | String | version_id | 版本ID |
| normalizationId | String | normalization_id | 归一化记录ID |

---

### 3.11 表名: financial_forecast_year_version (类名: FinancialForecastYearVersion)

财务预测年度版本表, 软删除 `@SQLRestriction("is_archived = false or is_archived is null")`。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| isCommited | Boolean | is_commited | 是否已提交 |
| year | String | year | 年份 |
| note | String | note | 备注 |
| version | Long | version | 版本号 |
| versionName | String | version_name | 版本名称 |
| isCurrentVersion | Boolean | is_current_version | 是否当前版本 |
| accepted | String | accepted | 是否已接受 |
| source | String | source | 来源 |
| userId | String | user_id | 用户ID |
| userName | String | user_name | 用户名 |
| isArchived | Boolean | is_archived | 是否已归档 |

---

### 3.12 表名: r_financial_forecast_year_version (类名: FinancialForecastYearRef)

财务预测年度版本关联表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| versionId | String | version_id | 版本ID |
| forecastId | String | forecast_id | 预测ID |

---

### 3.13 表名: financial_forecast_cache (类名: FinancialForecastCache)

财务预测缓存表。继承 FinanceManualDataAbstract + 自有字段:

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| *(继承28个字段)* | | | *见公共字段表* |
| batchNo | String | batch_no | 批次号, length=36 |

---

### 3.14 表名: financial_accept_forecast_cache (类名: FinancialAcceptForecastCache)

已接受预测缓存表。继承 FinanceManualDataAbstract + 自有字段:

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| *(继承28个字段)* | | | *见公共字段表* |
| batchNo | String | batch_no | 批次号, length=36 |

---

### 3.15 表名: financial_forecast_current (类名: FinancialForecastCurrent)

当前财务预测表。继承 FinanceManualDataAbstract + 自有字段:

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| *(继承28个字段)* | | | *见公共字段表* |
| type | String | type | 类型, length=1 |
| p05 | BigDecimal | p05 | 5%分位预测值 |
| p50 | BigDecimal | p50 | 50%分位预测值 |
| p95 | BigDecimal | p95 | 95%分位预测值 |
| p05Cash | BigDecimal | p05_cash | 5%分位现金预测值 |
| p50Cash | BigDecimal | p50_cash | 50%分位现金预测值 |
| p95Cash | BigDecimal | p95_cash | 95%分位现金预测值 |

---

### 3.16 表名: financial_forecast_history (类名: FinancialForecastHistory)

历史财务预测表。字段同 FinancialForecastCurrent。

---

### 3.17 表名: financial_forecast_alert_record (类名: FinancialForecastAlertRecord)

财务预测告警记录表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| userId | String | user_id | 用户ID |
| alertType | Integer | alert_type | 告警类型 |

---

### 3.18 表名: financial_growth_rate (类名: FinancialGrowthRate)

财务增长率表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| date | String | date | 日期 |
| growthRate | BigDecimal | growth_rate | 增长率 |
| revenue | BigDecimal | revenue | 收入 |
| rdExpensesRate | BigDecimal | rd_expenses_rate | 研发费用率 |
| smExpensesRate | BigDecimal | sm_expenses_rate | 销售费用率 |
| gaExpensesRate | BigDecimal | ga_expenses_rate | 管理费用率 |
| rdPayrollRate | BigDecimal | rd_payroll_rate | 研发工资率 |
| smPayrollRate | BigDecimal | sm_payroll_rate | 销售工资率 |
| gaPayrollRate | BigDecimal | ga_payroll_rate | 管理工资率 |
| operatingExpenses | BigDecimal | operating_expenses | 运营费用 |
| otherExpensesRate | BigDecimal | other_expenses_rate | 其他费用率 |
| cogsRate | BigDecimal | cogs_rate | 销售成本率 |
| capitalizedRdRate | BigDecimal | capitalized_rd_rate | 资本化研发率 |
| accountsReceivableRate | BigDecimal | accounts_receivable_rate | 应收账款率 |
| assetsOtherRate | BigDecimal | assets_Other_rate | 其他资产率 |
| accountsPayableRate | BigDecimal | accounts_payable_rate | 应付账款率 |

---

### 3.19 其余FI领域表

| 表名 | 类名 | 说明 |
|------|------|------|
| finance_category_weight | FinanceCategoryWeight | 财务分类权重 (name, code, description, weight, score, sort) |
| finance_score_level | FinanceScoreLevel | 财务分数等级 (startScore, endScore, scoreRank, color) |
| noname_Company | NonameCompany | 匿名公司报告 (含DI/FI评分、排名等) |
| qbo_logs | QBOLog | QuickBooks操作日志 (action, status, errorMessage等) |
| quickbooks_category | QuickbooksCategory | QuickBooks分类 (name, value, type, sort) |
| quickbooks_category_account | QuickbooksCategoryAccount | QuickBooks分类账户 (accountName, accountType等) |
| quickbooks_data_change | QuickbooksDataChange | QuickBooks数据变更 (companyId, pullTime, status, type等) |
| quickbooks_data_change_comments | QuickbooksDataChangeComments | QuickBooks数据变更评论 (comment, quickbooksDataChangeId) |

---

## 四、DI (Digital Infrastructure) 领域

包路径: `com.gstdev.cioaas.web.di.domain`

### 4.1 表名: stage (类名: Stage)

阶段表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | stage_id | 主键, UUID, length=36 |
| name | String | name | 名称, length=36 |
| kpaNum | Integer | kpa_num | KPA数量 |
| developer | String | developer | 开发人员, length=36 |
| phase | Integer | phase | 阶段 |
| organizationId | String | organization_id | 组织ID |

---

### 4.2 表名: kpa_category (类名: KpaCategory)

KPA类别表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | kpa_category_id | 主键, UUID, length=36 |
| name | String | name | 名称, 不为空 |
| description | String | description | 描述(TEXT) |
| logo | String | logo | 图标 |
| sort | Integer | sort | 排序 |
| detail | String | detail | 详情(TEXT) |
| folderId | Integer | folder_id | 文件夹ID |
| code | String | code | 编码 |
| organizationId | String | organization_id | 组织ID |

---

### 4.3 表名: kpa_category_software (类名: KpaCategorySoftware)

KPA类别软件表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| name | String | name | 名称, 不为空 |
| fileId | String | file_id | 文件ID, length=36 |
| sort | Integer | sort | 排序 |
| kpaCategory | KpaCategory | kpa_category_id | 关联KPA类别(FK) |

---

### 4.4 表名: adoption_level (类名: AdoptionLevel)

采纳等级表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | adoption_level_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| sort | Integer | sort | 排序 |
| selected | Integer | selected | 是否选中, 默认0 |
| kpaCategory | KpaCategory | kpa_category_id | 关联KPA类别(FK) |
| weight | float | weight | 权重 |
| description | String | description | 描述 |
| color | String | color | 颜色 |

---

### 4.5 表名: kpa_review (类名: KpaReview)

KPA评审表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | kpa_review_id | 主键, UUID, length=36 |
| submissionAt | Instant | submission_at | 提交时间 |
| reviewer | String | reviewer | 评审人 |
| idNumber | Integer | id_number | 评审编号 |
| deleted | Boolean | is_deleted | 是否删除, 默认false |
| invite | Invite | company_id | 关联公司(FK) |
| organizationId | String | organization_id | 组织ID |
| stage | Stage | stage_id | 关联阶段(FK) |

---

### 4.6 表名: di_tech_stack_layer (类名: DiTechStackLayer)

技术栈层表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | tech_stack_layer_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| description | String | description | 描述 |
| logo | String | logo | 图标 |
| sort | Integer | sort | 排序 |
| score | float | score | 分数 |
| weight | float | weight | 权重 |
| pid | String | pid | 父级ID |
| organizationId | String | organization_id | 组织ID |
| code | String | code | 编码 |

---

### 4.7 表名: tech_category (类名: TechCategory)

技术类别表, 软删除 `@SQLRestriction("is_deleted = false")`。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | tech_category_id | 主键, UUID, length=36 |
| techCategoryName | String | tech_category_name | 技术类别名称 |
| deleted | boolean | is_deleted | 是否删除, 默认false |
| sort | int | sort | 排序 |
| score | float | score | 分数 |
| weight | float | weight | 权重 |
| rank | Integer | type_sequence | 排名/类型序号 |
| attribute | Integer | attribute | 属性 (1-independent, 3-mutual exclusion) |
| logo | String | logo | 图标 |
| organizationId | String | organization_id | 组织ID |
| code | String | code | 编码 |
| diTechStackLayer | DiTechStackLayer | di_tech_stack_layer_id | 关联技术栈层(FK) |

---

### 4.8 表名: tech_stack (类名: TechStack)

技术栈表, 软删除 `@SQLRestriction("is_deleted = false")`。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | tech_stack_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| logo | String | logo | 图标, length=1024 |
| typeName | String | type_name | 类型名称 |
| sort | Integer | sort | 排序 |
| rank | Integer | type_sequence | 类型序号 |
| architectLayerSmall | String | architect_layer_small | 架构层(小) |
| deleted | boolean | is_deleted | 是否删除, 默认false |
| organizationId | String | organization_id | 组织ID |
| logoId | String | logo_id | 图标文件ID |
| logoName | String | logo_name | 图标文件名, length=1024 |
| techCategory | TechCategory | tech_category_id | 关联技术类别(FK, EAGER) |
| weight | float | weight | 权重 |
| description | String | description | 描述, length=5000 |
| code | String | code | 编码 |

---

### 4.9 表名: tech_stack_type (类名: TechStackType)

技术栈类型表。通过中间表 `r_tech_stack_set` 与 TechStack 多对多关联。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | tech_stack_type_id | 主键, UUID, length=36 |
| name | String | name | 名称 |
| description | String | description | 描述, length=2000 |
| sort | Integer | sort | 排序 |

---

### 4.10 表名: tech_stack_attribute (类名: TechStackAttribute)

技术栈属性表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | Integer | tech_stack_attribute_id | 主键, 自增 |
| name | String | name | 名称 |

---

### 4.11 评分相关表

#### 表名: score (类名: Score)

评分表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | score_id | 主键, UUID, length=36 |
| invite | Invite | company_id | 关联公司(FK) |
| project | Project | project_id | 关联项目(FK) |
| scores | Double | scores | 分数值 |
| processId | String | kpa_category_id | KPA类别ID |
| architectLayer | String | architect_layer | 架构层 |
| type | int | type | 类型 (1-推荐KPA, 0-可选KPA) |
| category | int | category | 分类 (1-KPA, 2-Tech Stack, 3-Document) |
| sort | int | sort | 排序 |
| level | int | level | 采纳等级 |
| architectLayerId | String | architect_layer_id | 架构层ID |
| folderId | int | folder_id | 文件夹ID |
| code | String | code | 编码 |
| kpaCategory | KpaCategory | di_kpa_category_id | 关联KPA类别(FK) |
| techStackLayer | DiTechStackLayer | di_tech_stack_layer_id | 关联技术栈层(FK) |

#### 表名: score_log (类名: ScoreLog)

评分日志表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | score_log_id | 主键, UUID, length=36 |
| companyId | String | company_id | 公司ID |
| kpaScore | float | kpa_score | KPA分数 |
| techStackScore | float | tech_stack_score | 技术栈分数 |
| sdpScore | float | sdp_score | SDP分数 |
| scoreRank | String | score_rank | 综合分数等级 |
| color | String | color | 综合颜色 |
| documentScore | float | document_score | 文档分数 |
| kpaScoreRank | String | kpa_score_rank | KPA分数等级 |
| kpaColor | String | kpa_color | KPA颜色 |
| techStackScoreRank | String | tech_stack_score_rank | 技术栈分数等级 |
| techStackColor | String | tech_stack_color | 技术栈颜色 |
| hasStageSet | Boolean | has_stage_set | 是否设置阶段 |
| hasKpaToolSet | Boolean | has_kpa_tool_set | 是否设置KPA工具 |
| hasKpaAdoptionSet | Boolean | has_kpa_adoption_set | 是否设置KPA采纳 |
| hasTechStackSet | Boolean | has_tech_stack_set | 是否设置技术栈 |
| averageScore | float | average_score | 平均分 |
| etlScore | float | etl_score | ETL分数 |
| etlRank | String | etl_rank | ETL等级 |
| etlColor | String | etl_color | ETL颜色 |

#### 表名: score_level (类名: ScoreLevel)

分数等级表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | Integer | score_level_id | 主键, 自增 |
| startScore | float | start_score | 起始分数 |
| endScore | float | end_score | 结束分数 |
| scoreRank | String | score_rank | 分数等级 |
| color | String | color | 颜色 |
| code | String | code | 编码 |
| organizationId | String | organization_id | 组织ID |

#### 表名: score_weight (类名: ScoreWeight)

评分权重表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | score_weight_id | 主键, UUID, length=36 |
| weight | float | weight | 权重 |
| category | int | category | 分类 (1-KPA, 2-Tech Stack, 3-Document, 4-ETL) |
| organizationId | String | organization_id | 组织ID |

---

### 4.12 DI 领域关联表

| 表名 | 类名 | 主要字段 | 说明 |
|------|------|---------|------|
| r_company_stage | RCompanyStage | company_id, stage_id | 公司-阶段关联 |
| r_kpa_category_weight | RKpaCategoryWeight | stage_id, kpa_category_id, weight, score, sort | KPA类别权重 |
| r_kpa_review_adoption | RKpaReviewAdoption | kpa_category_id, company_id, kpa_review_id, adoption_level_id, comment | KPA评审采纳 |
| r_kpa_review_adoption_software | RKpaReviewAdoptionSoftware | software_id, r_kpa_review_adoption_id | KPA评审采纳软件 |
| r_stage_kpa_category | RStageKpaCategory | stage_id, kpa_category_id | 阶段-KPA类别关联 |
| organization_kpa_level | OrganizationKpaLevel | kpa_category_id, name, description, organizationId | 组织KPA等级 |
| score_kpa_category | ScoreKpaCategory | company_id, score, isCritical, kpaCategoryCode | KPA类别评分 |
| score_tech_stack | ScoreTechStack | company_id, score, code | 技术栈评分 |

---

## 五、ETL 领域

包路径: `com.gstdev.cioaas.web.etl.domain`

### 5.1 AWS 相关表

| 表名 | 类名 | 主要字段 | 说明 |
|------|------|---------|------|
| aws.aws_credit | AwsCredit | batch, label, timestamp, sampleCount, average, sum, minimum, maximum, unit, resourceId | AWS积分数据 |
| aws.aws_credit_balance | AWSCreditBalance | timestamp, count, label, unit | AWS积分余额 |
| aws.aws_credit_usage | AWSCreditUsage | timestamp, count, label, unit | AWS积分使用 |
| aws.aws_data_point | AWSDataPoint | timestamp, maximum, label, unit | AWS数据点 |

### 5.2 CircleCI 相关表

| 表名 | 类名 | 主要字段 | 说明 |
|------|------|---------|------|
| circleci.circleci_build | CircleCIBuild | reponame, branch, status, buildNum, buildTimeMillis, startTime, stopTime等 | CircleCI构建记录 (60+字段) |
| circleci.circleci_login_user | CircleCILoginUser | login, name, selectedEmail, plan, parallelism等 | CircleCI登录用户 |

### 5.3 GitHub 相关表

| 表名 | 类名 | 主要字段 | 说明 |
|------|------|---------|------|
| github.github_contributors | GithubContributors | login, total, additions, deletions, commits, projectName | GitHub贡献者 |
| github.github_issues | GithubIssues | number, state, title, body, assignee, closedAt | GitHub Issues |

### 5.4 Sonarqube 相关表

| 表名 | 类名 | 主要字段 | 说明 |
|------|------|---------|------|
| sonaqube.sonaqube_project_status | SonaqubeProjectStatus | projectKey, status, conditions, periods | Sonarqube项目状态 |
| sonaqube.sonaqube_component | SonaqubeComponent | projectKey, name, qualifier, measures | Sonarqube组件 |
| sonaqube.sonaqube_component_search | SonaqubeComponentSearch | organization, name, qualifier, project | Sonarqube组件搜索 |

### 5.5 Intruder 安全扫描相关表

| 表名 | 类名 | 主要字段 | 说明 |
|------|------|---------|------|
| intruder.intruder_issue | IntruderIssue | severity, title, description, remediation, targetAddress | 安全问题 |
| intruder.intruder_result | IntruderResult | targetAddress, scanStatus, totalIssues, issuesCritical/High/Medium/Low | 安全扫描结果 |

### 5.6 NewRelic 监控相关表

> 注意: 以下8个类有 `@Table` 但缺少 `@Entity` 注解

| 表名 | 类名 | 说明 |
|------|------|------|
| newrelic.newrelic_apdex_score | NewRelicApdexScore | Apdex分数 |
| newrelic.newrelic_error_all | NewRelicErrorAll | 所有错误 |
| newrelic.newrelic_error_rate | NewRelicErrorRate | 错误率 |
| newrelic.newrelic_http_dispatcher | NewRelicHttpDispatcher | HTTP分发 |
| newrelic.newrelic_other_transaction | NewRelicOtherTransaction | 其他事务 |
| newrelic.newrelic_throughput | NewRelicThroughput | 吞吐量 |
| newrelic.newrelic_web_transaction_time | NewRelicWebTransactionTime | Web事务时间 |
| newrelic.newrelic_web_transaction_total_time | NewRelicWebTransactionTotalTime | Web事务总时间 |

---

## 六、Currency 领域

### 6.1 表名: currency (类名: Currency)

货币表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | Integer | id | 主键, 自增 |
| currency | String | currency | 货币代码, length=8, 不为空 |
| symbol | String | symbol | 货币符号, length=5 |
| seriesId | String | series_id | 系列ID |
| inverse | boolean | inverse | 是否反转汇率 (USD to xxx时为true) |

### 6.2 表名: currency_rate (类名: CurrencyRate)

汇率表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| currencyKey | String | currency_key | 货币对Key (如USDNOK), length=16, 不为空 |
| date | String | date | 日期 |
| rate | BigDecimal | rate | 汇率 (precision=22, scale=17) |

---

## 七、Storage 领域

### 7.1 表名: files (类名: FileObject)

文件存储表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 (继承) |
| hash | String | hash | 文件哈希, length=1024 |
| bucketName | String | bucket_name | 存储桶名称 |
| name | String | name | 文件名, length=1024 |
| originalName | String | original_name | 原始文件名 |
| link | String | link | 文件链接, length=1024 |
| contentType | String | content_type | 内容类型 |
| length | long | length | 文件大小 |
| etag | String | etag | ETag标识 |

---

## 八、Logging 领域

### 8.1 表名: log (类名: Log)

操作日志表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键 |
| username | String | username | 用户名 |
| description | String | description | 描述 |
| method | String | method | 方法 |
| params | String | params | 参数(TEXT) |
| logType | String | log_type | 日志类型 |
| requestIp | String | request_ip | 请求IP |
| address | String | address | 地址 |
| browser | String | browser | 浏览器 |
| time | Long | time | 耗时 |
| code | String | code | 状态码 |
| type | String | type | 类型 |
| companyId | String | company_id | 公司ID |
| operation | String | operation | 操作 |
| exceptionDetail | byte[] | exception_detail | 异常详情(TEXT) |
| userId | String | userId | 用户ID |
| result | String | result | 结果(TEXT) |
| exceptionInfo | String | exception_info | 异常信息(TEXT) |

---

## 九、SQS 领域

### 9.1 表名: queue_message_log (类名: QueueMessageLog)

SQS队列消息日志表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键, UUID, length=36 |
| sqsMessageId | String | sqs_message_id | SQS消息ID |
| messageType | Integer | message_type | 消息类型 |
| messageContent | String | message_content | 消息内容(TEXT) |
| messageStatus | Integer | message_status | 消息状态 |
| errorInfo | String | error_info | 错误信息 |
| operatorId | String | operator_id | 操作者ID |
| queueMessageLogBatchId | String | queue_message_log_batch_id | 批次ID |
| sqsMessageGroupId | String | sqs_message_group_id | 消息组ID |
| messageBusinessType | String | message_business_type | 消息业务类型 |
| sqsQueueName | String | sqs_queue_name | 队列名称 |

---

## 十、Scheduler 领域

### 10.1 表名: schedule_config (类名: ScheduleConfig)

调度配置表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| scheduleId | String | schedule_id | 主键, UUID, length=36 |
| scheduleName | String | schedule_name | 调度名称, unique, length=200 |
| scheduleType | String | schedule_type | 调度类型, length=100 |
| sourceType | Enum | source_type | 来源类型 (EnumType.STRING), length=20 |
| description | String | description | 描述, length=500 |
| timezone | String | timezone | 时区, length=50 |
| scheduleExpression | String | schedule_expression | 调度表达式, length=200 |
| messageGroupId | String | message_group_id | 消息组ID, length=200 |
| messageBody | String | message_body | 消息体(TEXT) |
| enabled | Boolean | enabled | 是否启用, 默认true |
| deleted | Boolean | is_deleted | 是否已删除, 默认false |
| extraConfig | String | extra_config | 额外配置(TEXT) |
| scheduleArn | String | schedule_arn | 调度ARN, length=500 |
| lastExecutionTime | Instant | last_execution_time | 上次执行时间 |
| nextExecutionTime | Instant | next_execution_time | 下次执行时间 |
| executionCount | Long | execution_count | 执行次数, 默认0 |
| remark | String | remark | 备注, length=1000 |
| isRemoteDeleted | Boolean | is_remote_deleted | 远程是否已删除 |

---

## 十一、Index 领域

### 11.1 表名: company_index_verify (类名: CompanyIndexVerify)

公司指标验证表。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| id | String | id | 主键 |
| companyId | String | company_id | 公司ID |
| calType | Short | cal_type | 计算类型 |
| date | String | date | 日期 |
| value | BigDecimal | value | 值 |
| indexCreateTime | Instant | index_create_time | 指标创建时间 |
| status | Short | status | 状态 |
| indexDataId | String | index_data_id | 指标数据ID |
| indexId | String | index_id | 指标ID |
| indexName | String | index_name | 指标名称, length=500 |
| formula | String | formula | 公式, length=500 |
| companyName | String | company_name | 公司名称, length=500 |
| currency | String | currency | 货币 |
| indexDesc | String | indexDesc | 指标描述, length=500 |
| projectionBasis | String | projection_basis | 预测基础 |
| haveBtn | Boolean | have_btn | 是否有按钮 |
| dataJson | String | data_json | 数据JSON(TEXT) |

### 11.2 表名: company_index_verify_main (类名: CompanyIndexVerifyMain)

公司指标验证主表, 继承 CompanyIndexVerify 全部字段, 存储顶部指标 (index_id 为空的数据)。

| 字段名 | 类型 | 数据库列名 | 说明 |
|--------|------|-----------|------|
| *(继承全部字段)* | | | *见 company_index_verify* |
| relativeId | String | relative_id | 关联ID (新增字段) |

---

## 十二、汇总统计

### 按领域统计

| 领域 | JPA实体数 | 主要功能 |
|------|----------|---------|
| System | ~47 | 用户、角色、菜单、组织、项目、公司、订阅、数据源、文档等 |
| FI | ~26 | QuickBooks集成、财务归一化、预测、手动数据、增长率、评分等 |
| DI | ~22 | KPA类别、阶段、技术栈、评分、采纳等级等 |
| ETL | ~20 | AWS、CircleCI、GitHub、Sonarqube、Intruder、NewRelic数据采集 |
| Currency | 2 | 货币、汇率 |
| Storage | 1 | 文件存储 |
| Logging | 1 | 操作日志 |
| SQS | 1 | 消息队列日志 |
| Scheduler | 1 | 调度配置 |
| Index | 2 | 公司指标验证 |
| **合计** | **~123** | |

### 关联中间表 (仅通过 @JoinTable 定义, 无独立实体类)

| 中间表名 | 关联关系 |
|----------|---------|
| r_user_role | User <-> Role |
| r_user_menu | User <-> Menu |
| r_role_menu | Role <-> Menu |
| r_tech_stack_set | TechStackType <-> TechStack |
| r_documentation_folder_category | CompanyDocumentationFolder <-> CompanyDocumentationCategory |

---

> 本文档由 Claude Code 自动扫描 JPA 实体类生成。所有字段信息直接来源于 Java 源代码中的 `@Entity`, `@Table`, `@Column`, `@Id` 等注解。
