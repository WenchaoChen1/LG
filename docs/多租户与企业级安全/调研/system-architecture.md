# 系统架构：租户模型现状、隔离缺口与数据库级隔离评估

> 关联文档: [决策摘要](./executive-summary.md) | [设计理念](./design-philosophy.md) | [Java 端](./java-design.md) | [Python 端](./python-design.md) | [前端](./frontend-design.md) | [证据代码](./code-examples.md)

本文是系统层视角：租户模型、跨端一致性、数据库层评估、分期建议。各端实现明细见对应文档。

---

## 1. 租户模型现状

### 1.1 层级结构

```
organization                 表 organization，PK = id，pid 自引用（递归树，深度不固定）
    │  字段仅：name / logo_url / website_url / code / pid / description + 审计列
    │  没有 level / type / is_tenant / depth / root_id
    │
    ├─ 租户节点（Golden Section）        ← 本次锚定的租户边界，无字段标识
    │
    ├── company_group            表 company_group，PK = company_group_id
    │      └ organization_id     → 指向某个 organization 节点
    │
    └── company                  表 company，PK = company_id
           └ 无 organization_id 列
```

**注意 `company` 表本身没有 `organization_id` 列**。公司归属哪个组织，只能查关联表，而关联表没有外键约束。

### 1.2 两条并存且互不同步的 org → company 路径

| 路径 | 表 | 写入场景 |
|---|---|---|
| **直连** | `r_organization_company (organization_id, company_id)` | 新建/编辑公司时，按请求体中的 `organizationList` 全量重建或逐条插入 |
| **经 Portfolio** | `company_group.organization_id` → `r_company_group (company_group_id, company_id)` | 建/改 Portfolio 时、公司关联 Portfolio 时 |

**两条路径零同步代码。** Portfolio 相关服务完全不触碰直连表；公司编辑接口中，`organizationList` 与 `rCompanyGroups` 是两段独立分支，改一个不会同步另一个。

**两张关系表均无唯一约束**（全仓 `@UniqueConstraint` 仅 5 处，无一涉及组织/公司/Portfolio 关系表），且新建公司走的是纯 `save()` 循环不查重。

> **业务规则（2026-09-02 确认）**：一个 company **可以同时属于同一租户下的多个子组织**——这是**正常业务形态**。约束在于**不得跨租户**：company 的归属最多跨到租户下一层的若干子组织，不会出现在另一个租户名下。

因此"多组织归属"本身不是缺陷。真正的问题有三条：

| # | 问题 | 后果 |
|---|---|---|
| 1 | **"不跨租户"这条规则在数据层面零约束** | 关系表无外键、无租户一致性校验，把 company 挂到另一个租户的组织下**数据库照收**。租户化后这是最直接的越界口子 |
| 2 | **两条路径不同步** | 可以出现"直连表指向组织 A、却被挂在组织 B 的 Portfolio 里"的状态，该 company 同时出现在两个组织的列表接口中——**查哪条路径决定你看到什么** |
| 3 | **多归属时取第一个，排序口径与页面不一致** | 见本节末。预期取"页面显示的第一个"，但两条查询排序不同，对齐无保证 |

⚠️ 由此推翻一个常见的修复直觉：**不能给 `(company_id, organization_id)` 加"一个公司只能挂一个组织"式的唯一约束**——那会违反业务规则。正确的约束是两条：① 防同一对重复插入的唯一约束；② **租户一致性约束**（一个 company 的全部组织归属必须落在同一租户子树内），后者目前**完全不存在，且需要第 1 步的租户标记列才写得出来**。

**问题 3 的具体形态**：两条查询用的不是同一个排序——

| 查询 | 排序 |
|---|---|
| 页面组织树 `OrganizationRepository.findByTreeInId:36-43` | **`ORDER BY created_at`** ✅ |
| 公司→组织 `OrganizationRepository.findAllByCompanyId:50-51` | **无 ORDER BY** ❌ |

而所有消费者一律取 `.get(0)`（消费点见 [Java 端](./java-design.md) §4.4）。**预期语义是"页面上显示的第一个组织"，但实现不保证这一点。**

**严重度定性**：**目前没有已确认的线上错误**。不带 ORDER BY 时 PostgreSQL 对简单顺序扫描多半返回接近插入的顺序，与 `created_at` 口径碰巧一致，所以一直没暴露。但这是**依赖未定义行为**——执行计划变化（走索引、并行扫描）、行被 UPDATE 后位置变动、VACUUM 之后，都可能改变返回顺序。

**修法很便宜**：给 `findAllByCompanyId` 补上 `ORDER BY created_at`，与页面口径对齐即可。**不必等多租户，属当下就该做的一致性修正**；且这条修完之后，"多归属"就完全是良性的正常形态了。

---

## 2. 核心问题一："我在哪个组织"有 6 个互不相同的实现

这是本次调研最重要的发现。同一个语义问题，系统里有六个答案：

| # | 实现位置 | 取值逻辑 | 取到的是哪一级 |
|---|---|---|---|
| 1 | Redis 会话 `organizationId`（Python 侧唯一权威来源） | `SELECT organization_id FROM r_organization_user WHERE user_id=? LIMIT 1`，**无 ORDER BY** | 随机一条关联记录 |
| 2 | 登录期身份装配 | `userOrganizations.get(0)` | 随机一条 |
| 3 | Java `getCurrentOrganization()` | `organizationUsers.get(0)`；兜底走公司→组织的 `.get(0)`，且列表为空时直接数组越界 | 随机一条 |
| 4 | Python chatbot 的可访问公司集 | 组织树前序 DFS 拍平后取 `organizations[0]` | **恒为树根** |
| 5 | 前端 askGoldie 作用域 | `firstLeafOrgId`，取第一个叶子节点 | **第一个叶子** |
| 6 | 前端 11 处组织 TreeSelect | `data[0].id` | **第一棵树的根** |

两点值得特别指出：

- **#4 与 #5 直接矛盾**（一个取根、一个取叶），而 #5 的代码注释声称"与主站默认选中一致"——主站（#6）取的是根。#5 与 #6 同在前端，属同一代码库内的自相矛盾。
- **#1 与 #4 在同一次 chatbot 请求中同时生效**：`ctx.organization_id`（来源 #1）用于定位管理端知识库空间，`ctx.allowed`（来源 #4）用于分段级公司过滤。两者层级不同、算法不同，**没有任何一致性检查**。

**结论：租户边界当前不是"定在了错误的一级"，而是"每条代码路径定在不同的一级"。** 第 1 步的本质是把这 6 个收敛成 1 个，而不是新增第 7 个。

---

## 3. 核心问题二：子树展开能力存在，但授权圈定不用它

子树展开能力是存在的：`OrganizationRepository.findByTreeInId` 是标准递归 CTE，有 6 个调用方（删组织、撤销菜单、渲染组织树、SDP 排名分母、benchmark 同侪集、指标筛选），另有 3 处等价的递归 CTE 用于公司列表、项目列表、用户列表。

**但授权圈定链没有使用它**——`CompanyGroupRepository.findVisibleCompanies` 用的是 `cg.organization_id = :orgId` **等值、不递归**，且 `seeAll = TRUE` 会直接短路 Portfolio 归属条件（SQL 全文见 [证据代码](./code-examples.md) §3.2）。

> ⚠️ **"等值不递归"本身不是产品缺陷。** 前端组织树下拉允许用户切换到任意子组织节点浏览其下的 Portfolio 与公司，**按单节点查正是现有交互的设计**。以下三个方向的后果，说的不是浏览场景。

**方向一：后端自动圈定范围时，取到哪一级不确定。**
不由用户点选、而由服务端按会话身份自动圈定范围的场景（Python 侧记忆面板、知识库面板、知识库检索），传入的是会话里那个 `LIMIT 1` 无序取一的组织 id（见 §2 的实现 #1）。**若恰好取到 Portfolio 并未挂载的那一级，返回空列表，且没有任何"层级不对"的信号**——表现为面板空白而非报错。用户无法通过切换节点自救，因为这条路径不经过 UI 选择。

**方向二：租户级圈定给不出集合。**
第 2 步需要的是"某租户下全部公司"这一个整体集合来做强制过滤。等值查询只能给出单节点结果，**要么改成递归展开，要么在应用层自行遍历子树**——这是第 2 步中一处确定的改造点，而非现存 bug。

**方向三：`seeAll = TRUE` 直接短路归属条件。**
拥有"看全部 Portfolio"菜单码的用户，传**任意** `organizationId` 都能拿到该组织的全部公司。而这条 SQL **完全没有"调用者是否属于该组织"的校验**。**这一条才是当下就成立的越权面。**

### 本该展开子树却只做单层等值的位置

| 域 | 影响 |
|---|---|
| Portfolio 全线（列表 / 用户可见 / 公司列表 / 重名校验） | 租户视角下看不到子组织的 Portfolio 与公司；父子组织可有同名 Portfolio |
| `business_issues` 全线（14 处） | 同上 |
| 全部 DI 配置表（stage / kpa_category / score_weight / score_level / tech_stack_layer） | 每个组织节点各持一份独立配置，改父不影响子 |
| 用户按组织查询 | 只取直连节点成员，不含父/子组织成员 |

**一处待业务确认的疑点**（不作为结论）：技术栈层级权重保存后触发的公司分数重算使用等值版本查询，只重算该组织**直接挂载**的公司，不含子组织的公司。

是否算缺陷取决于一条业务规则——**子组织的公司在评分时用的是自己那一级的配置，还是继承父组织的配置？**

- 若各组织节点的配置**互相独立**（现状确实是每个新组织克隆一份自己的配置），那么只重算直接挂载的公司**是正确行为**，本条不成立
- 若子组织**继承**父组织配置，则改父不重算子，分数与配置会长期不一致

调研未能从代码判定产品意图，**留待业务确认**。

---

## 4. 核心问题三：39 个接口接受 organizationId，0 个校验归属

全量扫描 50 个 Controller 的结果：

- 服务端**真正读取** `organizationId` 的端点：**39 个**
- 其中校验调用者与该组织归属关系的：**0 个**
- 另有 12 个端点带该字段但服务端不读（死字段或换维度过滤）
- 3 个 `/options` 端点有超管门禁，但门禁与 `organizationId` 无关

全仓 `@PreAuthorize` / `@Secured` 使用数为 **0**；唯一的授权 helper 是一个超管断言，挂在 3 个接口上。

### 按破坏力排序的代表

| 端点 | 效果 |
|---|---|
| `POST /score/saveScoreConfiguration` | 先写传入组织，随后遍历**全库每一个 organization** 覆盖其评分权重。**单次调用改写所有租户的评分口径** |
| `DELETE /organization?id=` | 任意登录用户硬删任意组织**及整棵子树**，软删其下全部用户与角色，清空 7 张配置表 |
| `PUT /organization`（含 pid） | 任意用户把任意节点搬到任意父节点下，**可造环**（pid 指向自己的后代会让递归 CTE 无限递归）。搬家后排名分母、同侪集、可见范围静默改变，无审计 |
| `PUT /organization/modifyOrganizationMenu` | 重写任意组织菜单授权，并级联撤销其整棵子树及子树全部角色的菜单 |
| `POST /users/adminUser`、`PUT /users/{userId}` | 先解绑再重挂 → **把已有任意用户搬迁到任意组织**，凭空获得该租户身份 |
| `GET /organization/findByTree?ids=` | 传任意 ids 返回对应组织的完整子树（含菜单、角色）。前端从不传该参数，但接口接受 |
| `GET /organization/findAllSort` | 全库**所有**组织清单 + 每个组织的菜单授权矩阵 |

### 两处"反向权限倒挂"

这两处不是单纯缺校验，而是设计错误——**传别人的组织 ID 反而比传自己的权限更大**：

1. `GET /companyGroup/user`：传入组织 ≠ 自己的组织时，**跳过** Portfolio 归属过滤，直接返回该组织全部 Portfolio
2. `POST /businessIssues/admin`：组织 ID 与当前组织不等时走 else 分支，**跳过** group-manager 与用户维度过滤

且这两处还被内部代码消费：指标校验服务在展开子树后对每个子组织调用前者，由于"传入组织 ≠ 当前组织"恒成立，实际拿到的是每个子组织的**全部** Portfolio，而注释声称行为与该接口一致。

---

## 5. 跨端隔离现状总表

| 层 | 隔离机制 | 级别 |
|---|---|---|
| 网关 | **不做鉴权**，纯路由转发；CORS 全开且允许携带凭据 | — |
| Java 认证 | JWT 仅含 `sub = userId`；租户信息在 Redis 会话，但全仓仅 2 处代码读取 | 第 1 档 |
| Java 数据访问 | 无任何框架级过滤（无 MyBatis 拦截器、无 Hibernate Filter、无 SQL 改写、无 MVC 拦截器）；每个 Repository 手写条件 | 第 1 档 |
| Python 身份 | 唯一可信来源是 Java 写入的 Redis 会话；全局中间件只验令牌有效性，不判租户 | 第 1–2 档 |
| Python 各模块 | 差异极大：memory / file_registry / 训练样本达第 2 档；RAG 读路径、LLM 与链路追踪端点为第 0 档 | 第 0–2 档 |
| 前端 | 门禁数据源为可写 `localStorage`；无统一租户上下文 | 不构成安全边界 |
| 数据库 | 单库单 schema 全租户共享；无 RLS、无角色分权、无分区 | 第 0 档 |

各端明细见 [Java 端](./java-design.md) / [Python 端](./python-design.md) / [前端](./frontend-design.md)。

---

## 6. 数据库级隔离评估

> PRD 要求列出数据库级隔离的可行方案。本节给出完整评估，结论为**不建议现阶段实施**，理由见 §6.4。

### 6.1 现状核实：全部为 0

| 项 | 结果 |
|---|---|
| 按租户分库 | **0**。3 个物理库（业务库 / RAG 向量库 / Nacos 用 MySQL）全部**按功能**分，分向量库的理由是 pgvector 扩展隔离 |
| 按租户分 schema | **0**。全租户共用 `public`。全仓唯一的 `CREATE SCHEMA` 在一个 ETL 模板里，无任何代码引用，是死代码 |
| PostgreSQL RLS | **0**。`ROW LEVEL SECURITY` / `CREATE POLICY` / `FORCE ROW LEVEL` 在全仓 SQL 中零命中 |
| 按租户建数据库角色 | **0**。所有服务共用同一个超级账号连库 |
| 按租户分区 | **0** |
| 动态数据源 / 路由 | **0**。单数据源 |
| 连接层租户上下文 | **0**。`SET ROLE` / `current_setting` 零命中 |

**文档与代码不符（需清理）**：设计文档中写有完整的数据库角色方案与 40 余条授权语句，并称"复用现有财务表的 RLS 策略（按 company_id 隔离）"——**一行都没落地，且其引用的那批表在全仓 SQL 中一张都不存在**。向量表的列注释写着"租户隔离由空间归属保证"，而那张归属表已在迁移 V005 中被整表删除。这些描述若被引用到客户安全问卷或审计材料中会构成实质陈述风险。

### 6.2 四种手段对比

> 四种技术手段里**只有"行级策略"进入了决策摘要 §2.4 的取舍表**（对应第 4 档），其余三种在本表即被排除。

| 手段 | 隔离强度 | 主要阻碍 | 对现有功能影响 |
|---|---|---|---|
| 分库（每租户一个数据库） | 最强 | 运维成本随租户数线性增长；迁移、备份、监控各乘 N | **破坏跨租户聚合**（对标 benchmark 同侪集、组织级汇总） |
| 分 schema（每租户一个 schema） | 强 | 生产开着 `ddl-auto: update`，表结构由实体自动演进，多 schema 下此路不通；全局字典表如何共享需另设计 | 同上 |
| **行级策略**（共享表 + 租户 ID 过滤，即**第 4 档**） | 中强（DB 兜底） | 见 §6.3；**逐项功能改动明细见 §11** | 小 |
| 按租户分区 | 弱（性能手段） | 大表重建；分区键须进主键 | 不解决越权，不在本题范围 |

### 6.3 RLS 的前置条件逐条对照

| 前置条件 | 现状 | 差距 |
|---|---|---|
| ① 应用能提供**可信**的租户上下文 | JWT 无租户 claim；租户 ID 来自客户端参数 | **致命**。策略里的"当前租户"没有可信值可填 |
| ② 每张表都有租户列 | Java 侧 151 个 JPA 实体中 85 个有 `company_id`（落在租户下面若干级）、21 个有 `organization_id`、53 个二者皆无；**0 个有租户列**；16 张连公司键都没有 | 需新增列 + 回填 |
| ③ 租户列命名统一 | 4 类别名并存：`company_id` / `ref_company_id` / `company_ref` / `main_company_id`，以及 `portfolio_id` 与 `company_group_id` 指同一概念 | 统一脚本会漏 |
| ④ 租户列上有索引 | 测试库扫出 **367 个 `*_id` 列不是任何索引首列**，仅补了 79 个，**剩 288 个**；向量库三张分段表租户列**零索引** | 大表需 CONCURRENTLY 建索引 |
| ⑤ 数据库角色可分权 | 单一超级账号 | **超级用户默认绕过 RLS**，不拆等于策略形同虚设 |
| ⑥ 数据完整性可依赖 | 外部扫描报 **158 个外键有问题**；全环境挂"忽略外键异常处理器"，建外键失败静默降级为告警；305 条"外键"中仅 61 条真实存在 | 已发生两次孤儿行生产事故 |
| ⑦ 跨库一致 | 业务库 + 向量库两个 PG；另有 3 张 LangGraph 检查点表由框架启动时自建，**不受版本化迁移管控** | 需各做一遍，且检查点表无人视其为业务表 |

### 6.4 若坚持要做，工作分解

**前置任务（第 1 步的组成部分，当前完全不存在）**

1. `organization` 增加显式租户标记列并标定节点。**当前只有 1 个租户，标定成本≈0**
2. 补**租户一致性约束**（company 的全部组织归属须落在同一租户子树内）+ 防重复行的唯一约束 + 清洗存量。**当前单租户，清洗量≈0**。注意：**不可加"一公司一组织"式约束**，那会违反业务规则
3. 收敛 6 个"取哪一级"实现为单一可信来源，并放入认证链

**主体工作**

4. 引入反规范化 `tenant_id` 列（写入时打戳），让策略谓词从"递归子树集合成员判断"退回"等值判断"——**这是让 RLS 可行的唯一路径**
5. 85+ 张表加列 + 回填（单租户下是一次全量 UPDATE）+ 建索引
6. **16 张无租户键的表**需先设计归属方案：

| 表 | 内容 | 反查难度 |
|---|---|---|
| `files` | 全站 S3 文件元数据 | **无可靠反查键**，须从 6+ 个来源反推，且这些外键列全部无索引 |
| `checkpoints` / `checkpoint_blobs` / `checkpoint_writes` | LangGraph 图状态（含解析出的财务数据） | **无可靠反查键**，仅有 thread_id |
| `ai_chatbot_message` | 全部对话正文 | 经 thread 反查 |
| `ai_llm_conversation` | 完整提示词与回复正文 | 经调用日志反查（**全仓唯一有级联的 AI 表**） |
| `ai_trace_span` | 链路节点上下文 | 经 trace 反查 |
| `ai_rag_search_log` | 用户原始提问 | 仅有 user_id + 空间 ID 数组 |
| `ai_rag_operation_log` | RAG 写操作审计 | 仅有空间 ID |
| `ai_rag_space` | 知识库空间 | **归属表已被 V005 整表删除，现为"全局资产"** |
| `ai_rag_fin_report_chunk` / `ai_rag_playbook_chunk` | 财报与方法论向量分段 | 无业务列 |
| `ai_financial_extraction_mapping_data` | 逐单元格解析结果与编辑痕迹 | 经文件反查 |
| `ai_financial_extraction_task_state_log` | 任务状态机事件 | 经任务反查 |
| `r_financial_normalization`（63 万行） | 归一化财务明细关联 | 两跳 JOIN |
| `r_financial_forecast_year_version`（13.7 万行） | 预测版本关联 | 两跳 JOIN |

7. 关闭生产 `ddl-auto: update`，把全部 DDL 收进版本化迁移
8. 拆分数据库角色（前置条件⑤）
9. 两个物理库各做一遍；注意存量 `organization_id` 列全部可空且历史行为空——改为过滤条件会让历史数据整批消失（此坑已在文件登记表上踩过一次，代码注释留有记录）

**估算：在应用层第 1–3 步完成的基础上，额外 5 人周（初步估算，明细见 §11）。**

### 6.5 结论

**不建议现阶段做数据库级隔离。理由不是工作量，而是顺序。**

数据库级隔离的价值是"应用层漏写条件时兜底"。而 LG 的问题不是漏写——条件基本都写了（第 1 档），问题是条件里那个租户 ID **来自客户端且零校验**，是"我在哪个组织"有 6 个答案，是多归属时"取第一个"的排序口径不统一。**这些不解决，RLS 策略里的"当前租户"根本没有可信的值可填；这些一旦解决，数据库级隔离的绝大部分收益已经拿到。**

同等工作量投入应用层第 1–3 步，能覆盖全部已识别的越权面；投入数据库层，则必须先把认证链、130+ 张表的列与索引、以及两个库的迁移体系全部重做一遍，做完仍然要回来做第 1–3 步。

---

## 7. 租户生命周期现状

### 7.1 开通

`POST /organization`，**无任何权限校验**，任何登录用户可在任意父节点下创建（唯一校验是同父节点下重名）。

创建时自动初始化：组织级 KPA 等级（Java 硬编码）、评分等级与权重（读 SQL 模板）、stage 与 KPA 分类与分类权重（**运行时取表中第一行所属组织的当前快照来克隆**）、技术栈三张表（**从一个硬编码的组织 ID 克隆**）。

**不会创建**：默认角色、默认菜单（新组织菜单为空）、默认 Portfolio、创建者关联。**新建的组织是无人可登录的孤岛**，必须再手工调用建管理员接口挂人。

其他问题：

- 6 个种子 SQL 模板中**仅 2 个仍被引用**，其余 4 个（含 800 行的 KPA 模板）全仓零引用，逻辑已改为运行时克隆
- 因此**新租户的种子数据不是版本化模板，而是某个既存租户的当前快照**；某租户改了自己的 stage，后续新建租户会继承该改动
- 评分权重初始化**无幂等守卫**，重复调用重复插入
- 模板按行读取执行，文件中的 `--` 注释行与空行也会被逐行送入执行

### 7.2 注销

`DELETE /organization?id=`，**无任何权限校验**，删除任意组织及其整棵子树。

| 已清理 | 未清理 |
|---|---|
| 角色（软删）、用户（软删）、7 张 DI 配置表、4 张组织关系表 | `company_group`（Portfolio 带悬空 `organization_id` 永久留存）、`r_portfolio_user`、开通时创建的技术栈三张表（有初始化无删除）、`business_issues`、`company` 行本身（变成无归属孤儿） |

补充问题：

- 用户仅软删且**不吊销令牌**——组织删除后，该组织用户手上的令牌仍然有效（有效期约 300 天）
- 执行顺序为**先硬删组织行，再删关系表**（当前无外键约束才未报错）
- 删除时用直连路径收集公司，而 Portfolio 走的是另一条路径，两条路径不一致的公司会被漏处理

### 7.3 树上搬家

`PUT /organization` 接受 `pid`，**任意用户可把任意节点挂到任意父节点下，包括造环**（pid 指向自己的后代会使递归 CTE 无限递归）。

搬家后：节点自身的配置与 Portfolio 归属跟着走，但**所有依赖递归子树的口径立刻改变**——SDP 排名分母、benchmark 同侪集、公司/用户/项目可见范围，全部在一次 PUT 后静默变化，无审计、无二次确认。另外重名校验使用的是**旧** pid，搬到新父节点下时不校验新父节点下是否重名。

---

## 8. 建议的分期

> **初步估算：应用层强制（第 1–4 步）合计 7 人周**（优先项另计），依据是 §10 的逐项功能改动明细（口径「只算功能修改、不含运维」）。
> 下表原按阶段给出的人周数已被上述总量取代，故改为只标相对量级；阶段内的具体分配待排期时确定。

| 阶段 | 目标 | 关键交付 | 相对量级 |
|---|---|---|---|
| **优先项（阻断）** | 身份不可伪造 | 轮换签名密钥与全部凭据、清理 git 历史、下线或收敛口令回吐接口、移除可逆口令副本 | 小 |
| **第 1 步：租户模型** | 让"租户"可查询 | `organization` 租户标记列 + 标定；6 个实现收敛为 1 个可信来源并入认证链；补租户一致性约束 | 小 |
| **第 2 步：服务端强制（→ 第 2 档）** | 客户端不能再决定看谁的数据 | 39 个接口改服务端解析；2 处倒挂修复；授权链改子树展开；Python 作用域收敛；前端统一租户上下文；替换「company_id 为空 ⟺ 超管」不变式 | **最大** |
| **第 3 步：框架级强制（→ 第 3 档）** | 漏写即拒绝 | 统一过滤机制；16 张无租户键表归属方案 | 中 |
| **第 4 步：租户运营** | 可开通、可注销、可管理 | 开通向导（版本化种子）、注销级联、组织级权限管理 UI（多为改造非新建，见 §10.4） | 中 |
| ~~（另计）行级策略 = 第 4 档~~ | ~~纵深防御~~ | **不建议**，见 §6.5 与 §11.5 | ~~另计 5 人周（初步估算）~~ |

企业级安全的现状与差距明细见 §9；其分期与第 1/2 步高度重叠（零信任改造与第 1 步实为同一件事），决策级估算见 [决策摘要](./executive-summary.md) §4。

---

## 9. 企业级安全现状与差距

> 本节是系统层的安全现状明细，对应 [决策摘要](./executive-summary.md) §3 的四个方向（SOC 2 Type II / GDPR / 零信任 / 审计日志）。摘要给结论与估算，本节给现状与差距。
>
> ⚠️ 需求要求以产品战略附录中的 SOC 2 阶段划分 / 时间线 / 预算作为分析起点，该附录未随本任务提供。本节仅基于代码现状给差距，**阶段与预算需与附录对齐后定档**。

### 9.1 审计日志

**结论：有表、有注解、无数据。**

| 组件 | 位置 | 状态 |
|---|---|---|
| 审计表实体 | `web/logging/domain/Log.java:15-58` | 表定义存在，含 `company_id` / `userId` / `request_ip` / `params` / `method` / `browser` / `exception_detail` 等 |
| 表用途声明 | `deploy/upgrade_doc/sprint105/V1__table_comments.sql:64` | 表注释写明用途为 Application log / Audit trail |
| **唯一写入路径** | `web/logging/aspect/LogAspect.java:23` | **`@Component` 被注释禁用** → Bean 未注册 → 零写入 |
| `@Log` 注解本体 | `web/logging/aop/Log.java:10` | 仅 4 个字符串字段，**无任何处理器** |
| 注解使用量 | 16 个 Controller 共 116 处 | **全部无效** |
| 读取端 | `web/logging/controller/LogController.java:26` | 仍在查一张不再增长的表；其 `companyId` 查询条件无 `@Query` 注解，不参与谓词生成 |

切点原本也只覆盖 2 个包（`LogAspect.java:34-35`），**不含** fi / storage / oauth / quickbooks。

团队已列为待决策项：`java/CIOaas-api/docs/代码审查/2026-07-16-java-code-review-issues.md:81`（T-13 LogAspect / @Log 去留决策）。

**登录日志：无独立表。** `User` 实体有 `last_login_date` / `last_login_ip` / `last_login_location` / `login_fail_times` / `login_date` 五个字段，但：

- 实际只写 2 个且为覆盖式滚动（`UserServiceImpl.java:1152-1162`），只留最近两次
- `lastLoginIp` / `lastLoginLocation` / `loginFailTimes` **全仓零 setter 调用** → 无 IP 留痕、无失败计数、无锁定机制
- 失败登录只落应用日志文本，不入库（`OAuthTokenController.java:183`）

**行级审计**：Java 有两个基类（`common/persistence/AbstractCustomEntity.java:23-60`、`AbstractAuditingEntity.java:23-50`），自动填 `created_at/by`、`updated_at/by`；**Python 侧无审计基类**，每个模型手写重复列。

**局部有效的 append-only 表（正例）**：

- `ai_rag_operation_log`（`python/CIOaas-python/source/rag/domain/models/operation_log_model.py:33`）—— RAG 写操作审计，注释明写 append-only
- `ai_financial_extraction_task_state_log`（`lg/db/models/models.py:233`）—— 任务状态机流水

**LLM 调用追踪不算操作审计**：字段很全（`ai_llm_call_log` 40+ 列、`ai_llm_conversation` 存完整对话正文、`ai_llm_tool_call_log`、`ai_trace` / `ai_trace_span`），但——① 只覆盖 LLM 调用，不覆盖业务增删改；② 无变更前/后值；③ 无 append-only 保护与保留策略；④ 唯一的真脱敏只在链路属性上按 key 名替换密钥（`tracing/application/service/trace_record_service.py:58-90`），**对话正文不做 PII 脱敏**。

### 9.2 认证与会话（零信任基线）

| 项 | 现状 | 位置 |
|---|---|---|
| 认证方式 | 自研 OAuth2 password-grant 外观 + HS256 JWT + Redis 撤销表；`client_secret` 可空 | `web/oauth/controller/OAuthTokenController.java:90-127, 278-300` |
| 会话存储 | `auth:token:{sha256(jwt)}` → userId；`auth:user:{userId}` JSON | `common/security/store/RedisTokenStore.java:22-23` |
| **访问令牌 TTL** | **25,920,000 秒 = 恰好 300 天**，且生产配置未覆盖该默认值 | `OAuthTokenController.java:66-67` |
| **刷新令牌 TTL** | **同为 300 天** | `:69-70` |
| 刷新 | 有，旧 refresh 轮换销毁 | `:192-254` |
| 注销 | 有，撤 access + refresh | `web/system/controller/UserController.java:331-343` |
| **并发登录控制** | **无**。key 按 token hash 建，同一 userId 可有无限并发令牌 | — |
| **改密后旧令牌失效** | **无**。改密路径不清 Redis | — |
| **MFA / SSO / SAML / OIDC** | **全仓零命中**（唯一 Azure AD 痕迹是 SharePoint 服务间调用，与用户登录无关） | — |
| 密码哈希 | BCrypt ✅ | `web/oauth/config/WebSecurityConfiguration.java:49-51` |
| **密码复杂度 / 过期 / 历史 / 锁定** | **全部无**；前端只有 `required` | — |

> 另有一处配置隐患：`jwt.expiration`（1 天）与 `oauth.*-token-validity-seconds`（300 天）**两套过期配置并存**，令牌端点走的是后者。

团队已写方案未执行：`java/CIOaas-api/docs/代码审查/token-会话撤销加固方案.md`（文档明确"只是方案，未改代码"）、`AuthController-抽取方案.md`。

### 9.3 加密与密钥管理

**传输**：仓库内 4 份 nginx 配置**只监听 80，无一条 `ssl_certificate`**；只透传 `X-Forwarded-Proto` → TLS 由上游负载均衡终结，**该配置不在本仓库**。HTTP→HTTPS 跳转的 rewrite 被注释掉；**无 HSTS / CSP / X-Frame-Options** 等安全响应头。内部链路为明文 HTTP（nginx → 网关）。

**静态加密**：

| 数据 | 存法 |
|---|---|
| 用户密码哈希 | BCrypt ✅ |
| **用户口令可逆副本**（`user.pwd`） | 🔴 明文直存或 AES-ECB（密钥硬编码），见 [Java 端](./java-design.md) §10 阻断项 1 与 [证据代码](./code-examples.md) §6 |
| **QuickBooks access/refresh token** | 🔴 明文 TEXT，无加密 |
| 密码重置 token（`activate_token`） | 明文 |
| Java 侧字段级加密 | **无**（`@Convert` 仅两个枚举转换器） |
| **RAG 存储连接凭据** | ✅ **正例**：AES-GCM + 随机 nonce，密钥走环境变量（`rag/infrastructure/crypto/connection_cipher.py:19,66-76`） |
| 数据库 / S3 层加密（TDE / SSE） | 仓库内无配置或文档 |

**密钥管理**：正规路径是 Nacos 配置中心 + `.env`（未提交），但被 [Java 端](./java-design.md) §10 的阻断项 2 绕过——`deploy/*.yml` 四份配置**被 git 跟踪**且含生产凭据。**全仓无 AWS Secrets Manager / SSM / Vault / KMS 调用**（`rag/infrastructure/crypto/__init__.py:4` 只写了"生产应由 KMS 托管"的期望）。Python 侧另有一处硬编码回退令牌（`common/config/lgpi.py:28-31, 41-46`）。

### 9.4 PII 与 GDPR 能力

**PII 分布**（节选）：

| 表 | 字段 |
|---|---|
| `user` | username(=email)、password、**pwd（可逆口令）**、display_name、first/last_name、email、phone_number、avatar_url、last_login_*、stripe_customer_id、activate_token |
| **`ai_llm_conversation`** | 🔴 **用户 prompt / LLM 回复全文 + `msg_full_json`**（可重放全部提示词与财务数据） |
| `ai_llm_tool_call_log` | `tool_args` / `tool_result` 全文 + `ref_user_id` |
| `ai_chatbot_message` / `_thread` | 聊天正文 |
| **`ai_rag_search_log`** | **用户原始提问 `query_text`** |
| `ai_trace` / `ai_trace_span` | `user_id` + `attributes` JSONB |
| `white_list_user` / `invite` / `email` / `fi_finance_manual_data_email` | 邮箱 |

**数据主体权利能力**：

| 能力 | 结论 |
|---|---|
| 数据脱敏 | **无**（唯一脱敏是链路属性按 key 名替换密钥，不含 PII 规则） |
| 被遗忘权 / 硬删除 | **无实现**。用户删除是软删；`UserController` 里唯一的 `@DeleteMapping` 是 `/users/logout` |
| 擦除审计表 | **只在设计文档里**——`docs/智能解析/调研/database-schema.md:740-762` 设计了擦除审计表，全仓 SQL 与 Python 模型**零实现** |
| 数据可携带 / 导出 | 只有业务报表导出，非"主体数据导出" |
| 数据保留策略 | **无代码、无配置**（仅设计文档提 180/365 天） |
| 同意管理 / cookie 同意 | **无** |
| 🔴 PII 外发第三方 | Sentry **开启默认 PII 上报**（Java 生产 + Python 全环境，Python 侧写死在 `main.py:344`，无环境判断） |
| 🔴 PII 出境到 LLM 供应商 | 6 家 provider 直连（OpenAI / Anthropic / Google / DeepSeek / Cohere / OpenRouter），仓库内**无 DPA 或区域约束痕迹** |

**"删除一个租户"的实际成本**：全仓 `ON DELETE CASCADE` 仅 7 处且**无一指向 company 或 organization**；删除路径本身已不可达（见 §7.2）。要真删需人工处理 85+ 张带 `company_id` 的表、10 张仅有 `organization_id` 的表，以及 16 张需 2–3 跳 JOIN 反查的表——其中 `files` 与 3 张 checkpoint 表 **没有可靠反查键**。

### 9.5 网络与访问控制

| 项 | 现状 |
|---|---|
| 网关鉴权 | ❌ **不做**。`gstdev-cioaas-gateway` 仅 2 个 Java 文件，唯一全局过滤器只打访问日志 |
| **CORS** | 🔴 来源 / 方法 / 头部全部通配，**且允许携带凭据**（`deploy/cioaas-gateway.yml:19-26`） |
| **限流** | ❌ 无。无 `RequestRateLimiter`、无 `limit_req`、无 Bucket4j |
| IP 白名单 / WAF | ❌ 无 |
| 方法级授权 | ❌ `@PreAuthorize` 全仓 0 处；JWT 过滤器给的权限集恒为空（`JwtAuthenticationFilter.java:43`） |
| actuator | 暴露 `health,info,gateway`，`show-details: always`；网关日志级别 DEBUG |
| Python 鉴权前置 | ✅ 全局中间件（`main.py:287`），但只验令牌有效性、不判租户 |

**免鉴权端点**：Java 侧 `@AnonymousAccess` **实测 15 处** + 硬编码 `/error`；风险最高的三个见 [Java 端](./java-design.md) §4.6。Python 侧豁免为 `/`（精确）、`/health_check`、`/actuator` 前缀 + 环境变量追加项；另有 `AUTH_CHECK_ENABLED` / `AUTH_MOCK_ENABLED` 两个全局开关（后者在 prod/uat 有保护）。

⚠️ LLM 与 tracing 管理端点采用"环境变量令牌**未配置即放行**"的开关式鉴权，且返回提示词全文。

### 9.6 依赖与基础设施安全

**结论：完全没有。**

- CI 在三个子仓的 `.circleci/config.yml`；**无 GitHub Actions**
- **依赖扫描**：无（dependabot / snyk / trivy / OWASP 全部零命中）
- **构建期安全插件**：无（Java `pom.xml` 唯一插件是 compiler-plugin）
- **`npm audit` 被显式关闭**：前端 CI 四个 job 全部 `--no-audit`
- **镜像扫描**：无；基础镜像不固定 digest（`nginx:latest`、`circleci/python` 无 tag）
- **Python CI 完全不跑测试**；Java 打包时 `-DskipTests`
- CI 使用**长期 IAM 凭据**而非 OIDC 短期角色
- 容器加固：`docker-compose.yml` 无 `user:` / `read_only:` / `cap_drop:`
- **部署链路（2026-09-02 核实修正）**：三个项目的 CI **均只到"构建 + 推镜像/产物"为止**——Java prod job 最后一步是 `docker push ... :latest`，全部配置中**无 `ecs update-service` / `kubectl` / 任何部署动作**，仓库内也无独立部署脚本。**实际部署是 CI 之外的人工操作。**
  - 因此"分支直接触发部署、无人工介入"的说法**不成立**。真实差距是**审批未固化为可审计记录**：CI 内无 `type: approval` 闸门（三份配置零命中），无"谁批准了哪个版本上生产"的凭证，也无"批准人不能是作者本人"的职责分离规则。
  - ⚠️ 若部署经 AWS 控制台执行，CloudTrail 可能已含部分证据（谁在何时更新了服务）——**建议核实后再定差距范围**，这条可能比预想的便宜。

### 9.7 与多租户改造的重叠关系

| 企业级安全项 | 与多租户分期的关系 |
|---|---|
| **零信任** | **与第 1 步是同一件事**——两者的第一步都是"让认证链承载可信身份与租户上下文"。零信任工程侧初估 3 人天，分开排期就要做两遍 |
| **审计日志** | 独立，但需在 SOC 2 观察期开始前上线（控制措施须先运行才能收集证据） |
| **GDPR 删除能力** | 依赖第 1 步/第 3 步——"删除一个租户"需要先有租户归属标记与完整反查链 |
| **SOC 2 访问控制域** | 直接由第 2/3 步满足 |

### 9.8 文档与代码不符（合规风险）

以下描述存在于设计文档中但**代码零实现**，若被引用到客户安全问卷或审计材料会构成实质陈述风险（对应 [决策摘要](./executive-summary.md) §5 的 R10）：

| 文档位置 | 声称 | 实际 |
|---|---|---|
| `docs/智能解析/调研/database-schema.md:876-963` | 完整的数据库角色方案 + 40 余条 GRANT | **零实现**，所有服务共用一个超级账号 |
| `docs/智能解析/调研/python-design.md:1153` | "复用现有 `fi_*` 的 RLS 策略（按 company_id 隔离）" | **RLS 零实现**，且引用的 `fi_*` 表在全仓 SQL 中**一张都不存在** |
| `docs/智能解析/调研/database-schema.md:740-762` | GDPR 擦除审计表 | **零实现** |
| `docs/智能解析/调研/system-architecture.md:122` | Python 承载"全部审计日志表"（5 张） | **只有任务状态流水表落地** |
| 向量库 V001 列注释 | "tenant isolation via space binding" | binding 表已被业务库 V005 `DROP` |

**清理这些描述本身就是 SOC 2 准备工作的一部分。**

---

## 10. 改造项清单（功能改动明细）

> **口径**：本节**只列功能改动**（写代码、改页面、改 SQL）。
> **不含**：运维与日常数据维护（建组织、挂人、配权限等属运营成本，不计入研发工时）、测试环境搭建、回归验证、灰度发布、数据迁移演练。
> **初步估算**：依据本清单初估，**应用层强制（第 1–3 步 + 租户运营）合计 7 人周**。§8 分期表与决策摘要 §4.2 均已按此更新。

### 10.1 第 1 步：租户模型落地

| # | 改动项 | 端 | 规模 | 备注 |
|---|---|---|---|---|
| 1-1 | `organization` 加租户标记列 | Java + SQL | 1 列 + 1 个迁移文件 | 不能用层级深度推断，必须显式列 |
| 1-2 | 标定租户节点 | 数据 | **1 条 UPDATE** | 当前只有 Golden Section 一个租户 |
| 1-3 | 租户 id 进认证链 | Java | 4 个类：`JwtTokenProvider` / `UserContext` / `UserInfoCache` / `OAuthTokenController` | 签发时写入 + 会话结构扩展 |
| 1-4 | Python 读取契约同步 | Python | `auth_store.AuthUser` 加字段，1 处 | |
| 1-5 | **收敛 6 个"我在哪个组织"实现** | 三端 | Java 3 处（`findOrganizationIdByUserId` / `UserDetailsServiceImpl` / `getCurrentOrganization`，后者有 2 份复制）+ Python 1 处（`company_service` 取 `organizations[0]`）+ 前端 2 处（`firstLeafOrgId`、13 处 `data[0].id`） | 本步的主体工作 |
| 1-6 | 租户一致性约束（DDL + 写入校验） | Java + SQL | 2 个写入点（`CompanyServiceImpl` 的 `update` / `inviteCompany`） | 见 §1.2：不可加"一公司一组织"式唯一约束 |
| 1-7 | `findAllByCompanyId` 补 `ORDER BY created_at` | Java | **1 行** | 与页面树口径对齐，见 §1.2 |

### 10.2 第 2 步：服务端强制圈定

**10.2.1 39 个接口 —— 按 Controller 分组**

| 分组 | 数量 | 改法 |
|---|---|---|
| `organization` CRUD + 菜单授权 | 9 | 加权限校验（谁能建/改/删组织）+ 归属校验 |
| `companyGroup`（Portfolio 查询与维护） | 8 | 组织 id 改服务端解析；**含 1 处反向倒挂** |
| `invite`（公司列表 / 查询 / 新建） | 5 | 同上 |
| `users`（查询 / 新建 / 改归属） | 4 | 重点是"把已有用户搬迁到任意组织" |
| DI 配置类（`stage` / `score` / `techStackManagement` / `tools`） | 9 | 组织 id 改服务端解析；`saveScoreConfiguration`（遍历全库覆盖）需单独设计 |
| `businessIssues` | 2 | **含 1 处反向倒挂** |
| `rOrganizationRole` | 2 | 加归属校验 |

> **同质性很高**：真正需要独立设计的约 5–8 个（组织 CRUD 权限模型、`saveScoreConfiguration`、2 处反向倒挂、用户搬迁），其余是套用同一个守卫模式。
>
> **有现成模板可复用**：`UserService` 的 `findInaccessibleCompanies` / `canAccessCompany` / `hasVisibleCompanyUnderGroup` 三个方法已存在且带测试；`PortfolioBenchmarkServiceImpl.assertCompaniesAccessible` 是可直接照搬的实现样板（见 [Java 端](./java-design.md) §4.3）。

**10.2.2 其余项**

| # | 改动项 | 端 | 规模 |
|---|---|---|---|
| 2-1 | 授权链改子树展开 | Java | `findVisibleCompanies` 1 条 SQL + 调用方；递归 CTE `findByTreeInId` 已存在可直接用 |
| 2-2 | **替换「`company_id` 为空 ⟺ 超管」不变式** | Java + Python | **4 个模块**：Java 登录链、chatbot 端类型判定、rag `_require_admin`、financial_extract ACL。**本步风险最高的一项** |
| 2-3 | Python 组织作用域收敛 | Python | 7 个模块：memory / file_registry / chatbot manage / financial_extract / tracing / llm / rag |
| 2-4 | Python `list_org_companies` 链改子树 | Python | 1 条链 |
| 2-5 | rag 读路径补归属 | Python | 4 个端点（`/spaces`、`/spaces/{id}/chunks`、`/entries/{id}/chunks`、`/recall`） |
| 2-6 | **前端统一租户上下文** | 前端 | 新建 1 个 Context/model + 替换 **65 处 `inviteDto` + 63 处 `getQueryString('id')`**（机械但量大） |
| 2-7 | 前端组织树下拉收敛 | 前端 | 17 个文件中复制的 TreeSelect + 5 份重复 service |
| 2-8 | 平台用户管理放开查询维度 | 前端 + Java | `UserManagePage` 现写死 `roleTypes: 1`（只查超管），需支持按组织查全部用户 |

### 10.3 第 3 步：框架级强制

| # | 改动项 | 端 | 规模 |
|---|---|---|---|
| 3-1 | Java 统一过滤机制（Hibernate Filter 或拦截器） | Java | 1 套机制 + 全量 Repository 回归 |
| 3-2 | Python 统一依赖 | Python | 1 套机制 |
| 3-3 | 补 16 张无租户键表 | 三端 + SQL | 12 张可反查；**`files` 与 3 张 checkpoint 表无可靠反查键，需先设计归属方案** |

### 10.4 第 4 步：租户运营（**多为改造，非新建**）

⚠️ 此前将本组归为"缺失功能"是**不准确的**——页面骨架基本都已存在，缺的是入口位置、聚合维度与状态流转。核实结果：

| 功能 | 现有页面（已核实存在） | 实际要改的 | 可否延后 |
|---|---|---|---|
| 组织自助管理 | `pages/devSupport/portfolioGroupManagement/`（组织 CRUD + 菜单授权，功能完整） | **仅入口在超管内部工具区**，租户管理员进不去 → 搬入口 + 加权限 | 接客户前需做 |
| 成员总览 | `pages/companySettings/components/team/`（成员管理 + 邀请 + 角色分配） | **维度是单公司**（`companyId: urlId \|\| inviteDto.id`）→ 加"租户下全部企业成员"聚合视图 | 可延后 |
| 邀请生命周期 | 已有发邀请 + Reinvite + 选择页 Accept/Decline | 补状态流转：待处理列表、过期/撤回、批量邀请 | 可延后 |
| 角色批量分配 | `pages/devSupport/rolesManagement/` + `companyRoles/`（角色×菜单矩阵完整） | 角色**定义**齐全；缺"给成员批量分配"，现仅 `addUser` 一个下拉 | 可延后 |
| 套餐 / 席位 | ⚠️ 仅只读接口；`pricingTierApp` 菜单项**已被注释**（`BasicLayout.tsx:830`） | **这一项基本是从零做** | **最该延后** |
| 开通向导 | `pages/portfolioCompanies/addCompany/`（单页表单） | 串联：建组织 → 建首个管理员 → 配菜单权限 → 建 Portfolio → 固定模板种子 | 接客户前需做，**可先用脚本代替 UI** |
| 种子改版本化模板 | 现为运行时克隆某家现有客户配置（见 §7.1） | 改为固定模板 | 接客户前需做 |
| 注销级联清理 | 见 §7.2，级联严重不全 | 补清理 | 可延后（现在也无真删能力） |
| 组织搬动权限 + 环检测 | 见 §7.3，任意用户可搬、可造环 | 加权限 + 环检测 | 便宜，建议做 |

### 10.5 最小可行范围（目标：能安全接第二家客户）

若只求"安全接入第二家客户"，**必须做**的是：

- 第 1 步 **全部**（1-1 ~ 1-7）
- 第 2 步的 **10.2.1（39 个接口）+ 2-1 / 2-2 / 2-3 / 2-6**
- 租户运营的 **开通向导（脚本版即可）+ 种子改版本化模板 + 组织搬动权限**
- 附录性质的 **两条阻断项**（见 [决策摘要](./executive-summary.md) 附录 A）

**可延后**：第 3 步全部（框架级强制是"漏写也安全"的加固，不是接客户的前提）、2-4 / 2-5 / 2-7 / 2-8、以及 §10.4 中标注"可延后"的全部条目。

> 若第二家客户的日常组织/成员/权限维护由**内部代运营**，则 §10.4 中"成员总览 / 邀请生命周期 / 角色批量分配 / 套餐席位"四项可整体延后——**这是产品侧的一个选择，直接决定这批工作要不要做**。

---

## 11. 行级策略（第 4 档）改造项清单

> **前置**：本清单**全部建立在应用层强制已完成的基础上**——行级策略**不能替代**应用层强制：策略里的"当前租户"必须由第 1 步提供可信值，否则无值可填（理由见 §6.5）。
> **手段取向**：四种技术手段中只有**行级策略（PostgreSQL RLS）**成本可控（分库/分 schema 会破坏跨租户聚合功能，分区不解决越权）。本清单按 RLS 路线展开。
> **口径**：同 §10——只列功能改动，不含运维。
> **条目号**：本节的 `4-x` 指【**第 4 档**（行级策略）】的改动项，与【第 4 步（租户运营）】无关——后者的改动项未编号，见 §10.4。

### 11.1 数据层改造

| # | 改动项 | 规模（实测） | 说明 |
|---|---|---|---|
| 4-1 | 引入反规范化 `tenant_id` 列 | Java 侧 **98 张**已有归属列的表 + **16 张**无归属键的表；Python 侧 **33 张** ORM 表 | 让 RLS 谓词从"递归子树集合判断"退回"等值判断"，**这是 RLS 可行的唯一前提** |
| 4-2 | 存量回填 | **单租户下是一次全量 UPDATE** | 当前唯一租户，回填成本≈0；有第二家客户后成本剧增 |
| 4-3 | 补索引 | 每张表 1 个；且测试库有 **288 个 `*_id` 列不是任何索引首列**；向量库 3 张分段表归属列**零索引** | 大表须 `CREATE INDEX CONCURRENTLY` |
| 4-4 | 归属字段命名统一 | **4 类别名**：`ref_company_id`（2 张）/ `company_ref`（1 张）/ `main_company_id`（1 张）/ `portfolio_id` vs `company_group_id` | 不统一则任何批量脚本都会漏表 |
| 4-5 | `files` 与 `checkpoints` 归属方案设计 | 2 组（`checkpoints` 实为 3 张表） | **无可靠反查键**，须先设计再实施。`checkpoints` 由 LangGraph 在启动时 `PostgresSaver.setup()` 自建（`source/bootstrap/lifespan.py:119-121`），**不受版本化迁移管控**——性质类似 Java 的 `ddl-auto`，但范围仅 3 张表 |
| 4-6 | 全局字典表豁免清单 | 待梳理（`currency` / `dictionary` / `menu` / `role` / 对标基准数据等） | **漏排会把跨租户共享数据全部拦掉**，属高风险项 |

### 11.2 数据库配置改造

| # | 改动项 | 规模 | 说明 |
|---|---|---|---|
| 4-7 | **关闭生产 `ddl-auto: update`** | **仅 Java 侧**：3 个环境配置（`cioaas-web.yml` / `-staging` / `-prod` 的 `:43`）+ 把现有全部表结构收进版本化迁移 | Java 表结构现由 JPA 实体自动演进，与 RLS 方案**根本冲突**。**Python 侧无此问题**——已走版本化迁移（`sql/migrations/`），`create_all` 不在生产路径调用 |
| 4-8 | 拆分数据库角色 | 现为**所有服务共用一个超级账号** | **超级账号默认绕过 RLS**，不拆等于策略完全失效；或全表加 `FORCE ROW LEVEL SECURITY` |
| 4-9 | 建 RLS 策略 | 约 **114 张（Java）+ 33 张（Python）** 表，每张 2 条语句（`ENABLE` + `CREATE POLICY`） | 机械但量大 |
| 4-10 | 两个物理库各做一遍 | 业务库 + RAG 向量库 | 向量库另有 HNSW 索引与列过滤组合的性能问题 |

### 11.3 应用层配套

| # | 改动项 | 规模 | 说明 |
|---|---|---|---|
| 4-11 | 连接层注入租户上下文 | Java（Hikari 取连接后 / AOP）+ Python（SQLAlchemy session 事件）各 1 处 | 每个连接或事务执行 `SET app.tenant_id` |
| 4-12 | **无用户上下文的执行路径**改造 | 定时任务、SQS 消费者、迁移脚本、后台作业 | 这些没有登录身份，需要系统级角色或显式设租户，**容易被漏掉且出问题时很隐蔽** |
| 4-13 | 跨租户聚合功能的豁免机制 | 对标 benchmark 同侪集、组织级汇总等 | RLS 会把这些**正常业务功能一并拦掉**，需专用角色或策略豁免 |

### 11.4 验证与保障

| # | 改动项 | 说明 |
|---|---|---|
| 4-14 | 全量接口回归 | RLS 是行级拦截，影响面是**全部读写路径** |
| 4-15 | 性能验证 | RLS 对每行做判定；向量库"HNSW + 列过滤"会退化为先扫再排序 |
| 4-16 | 运维与排障预案 | 策略生效后，跨租户运维查询、线上排障、数据修复都需要新的操作路径 |

### 11.5 判断

行级策略的**机械工作量**（4-1/4-2/4-3/4-9）在单租户现状下并不算大——回填是一次 UPDATE，建策略是批量脚本。**真正的成本与风险集中在四处**：

1. **4-7 关闭 `ddl-auto`** —— 要先把现有全部表结构收进版本化迁移，这本身是一次独立的工程
2. **4-8 拆数据库角色** —— 不拆则 RLS 形同虚设，拆则牵动全部服务的连接配置
3. **4-6 + 4-13 豁免清单** —— 漏排会打断正常业务功能，且故障表现为"数据莫名其妙查不到"
4. **4-12 无用户上下文的路径** —— 定时任务与消息消费者最容易被漏

**结论不变，但理由要说准**：行级策略初步估算为 **5 人周**，**比应用层强制（7 人周）还小**——所以对它的判断**与成本无关**。三条真实理由：

1. **依赖应用层强制，不能替代它。** 策略里的"当前租户"必须由第 1 步提供；第 1 步没做，策略就无值可填（§6.5）
2. **收益重叠。** 应用层强制完成后已达第 3 档（漏写即拒绝），行级策略只额外覆盖"应用被完全绕过"这一种情形——而那种情形下攻击者已持有数据库凭据，4-8 若未彻底拆角色，RLS 同样被绕过
3. **风险不在工作量而在副作用。** 上面四条（4-6/4-7/4-8/4-12/4-13）出问题时，表现是**正常业务功能突然查不到数据**，排查成本远高于开发成本

本清单的用途：若未来因客户合规要求必须做，可据此直接估算与实施，不必重新调研。
