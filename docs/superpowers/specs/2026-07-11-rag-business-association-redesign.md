> 关联文档: [chatbot 知识库问答设计](./2026-07-05-chatbot-knowledge-base-qa-design.md)、[devSupport 过滤条一致性设计](./2026-07-10-devsupport-filter-bar-consistency-design.md)

# RAG 业务关联（Business Association）页面与数据模型重设计 — 方案文档

**日期**: 2026-07-11
**范围**: CIOaas-python（rag 模块：新主表+子表、V006 迁移、associations CRUD 接口、旧 binding 归属接口下线）+ CIOaas-web（`/devSupport/rag/binding` 页面改版）；Java 零改动
**一句话**: 把「每个 space 一条 1:1 归属（owner_type）」反转为**业务关联实体**——一条关联 = 一个业务作用域（端类型 + 公司 + 用户 + 组织 + 业务类型），**可关联多个 RAG space**；关联的唯一创建入口收敛到本页面，`ai_rag_space_binding` 回归纯租户归属表。

---

> **修订记录（2026-07-11 用户确认，已定稿按此开发）**：
> 1. 表名定 **A 方案**：`ai_rag_business_association` + `ai_r_business_association_space`；
> 2. 新表**保留 organization_id 字段**（§2.2 已含）；建空间自动写的租户归属行保留（未被否决，按 §2.4/§7 执行）；
> 3. **business_type 种子扩为 7 值**：`CLIENT_USER 客户端用户 / ADMIN_USER 管理端用户 / CLIENT_COMPANY 客户端公司 / ADMIN_COMPANY 管理端公司 / KNOWLEDGE_BASE 知识库 / PLAYBOOK Playbook / PARSING_MEMORY 解析记忆`（前 4 个自带端语义，前端选中时自动同步 endType 下拉、仍可改；后端只做白名单校验不做端一致性强校验）。§5 回填映射相应改为逐值直映（CLIENT_COMPANY→CLIENT+CLIENT_COMPANY 等）；
> 4. **多对多确认**：一个空间可挂多个关联、一个关联可挂多个空间（§2.2 设计不变，子表联合唯一）；
> 5. **命名统一到 business association**：前端页面目录/路由改 `/devSupport/rag/businessAssociation`，后端新文件一律 `business_association_*` 命名；前后端字段名逐字对齐（wire 契约 camelCase：endType / businessType / companyId / userId / organizationId / spaceIds / spaces）。

> **修订记录（2026-07-11 二次确认）**：
> 6. **V005 与 V006 合并为单个 V005**：旧 `V005__rag_space_binding_owner_type.sql` 只提交过、未发布到任何环境——直接删除，重写为 `V005__rag_business_association.sql`（建两张关联表 + 保留旧 V005 的 company_id 可空修正；开头加幂等 `DROP COLUMN IF EXISTS owner_type/playbook_id` 收敛跑过旧 V005 的本地库）。owner_type/playbook_id 从此**不会在任何环境被创建**，也无需 §5 的存量回填（无存量）；
> 7. **owner_type 定性**：旧 1:1 模型的归属类型判别符，职责已被新表 end_type + business_type 取代，连同 playbook_id 彻底删除；
> 8. **每张表一个 ORM 文件**：主表 `business_association_model.py`、子表 `business_association_space_model.py` 分列两文件（接口响应里的 `spaces[]` 是空间摘要回显；DB 层的关联即子表 `ai_r_business_association_space`）。

> **修订记录（2026-07-11 三次确认）**：
> 9. **关联表命名规范**：多对多关联表用 `{域}_r_xxx` 前缀——子表定名 `ai_r_business_association_space`（全库排查：唯一多对多关联表；Java 域 `r_company_stage` 本就符合）；
> 10. **`ai_rag_space_binding` 整表删除**（表 + model + 全链引用），§2.4/§7 的「保留租户归属」作废：V005（未发布）改为 `DROP TABLE IF EXISTS ai_rag_space_binding` + 建两张关联表；create_space 不再写任何归属；SpaceDTO/VO 删 companyId/userId/organizationId/private；空间列表/详情/召回测试页回归**登录可见全部空间**（rag 彻底去权限的管理端资产）；**chatbot 知识库检索范围改由业务关联表驱动**：end_type(按调用方端映射 company→CLIENT/admin→ADMIN) + business_type=KNOWLEDGE_BASE + (company_id/user_id/organization_id 任一命中调用方身份) 的关联所挂 space 集合（再按 STANDARD 过滤）；无命中关联 = 空结果（empty_scope_ok 语义保留）。私有空间（user_id）与「超管无公司空间后置关联」概念随表废弃。

## 1. 背景与问题

现状（2026-07-11 merge sprint111 后）：

- 页面 `/devSupport/rag/binding` 以 **space 为主体**列出全部空间，每空间经 `PUT /spaces/{id}/binding` 设置一条 1:1 归属（`ai_rag_space_binding.owner_type` + company/user/playbook 权威 id 三选一）。
- 归属行有**两个写入口**：建空间时自动插入（租户归属）+ 本页设置（业务归属），两种语义挤在同一张表同一行上。
- `owner_type` 把「端」与「业务」混在一个枚举里（CLIENT_COMPANY / ADMIN_COMPANY / ADMIN_USER / PLAYBOOK / PARSING_MEMORY），且一个业务对象无法关联多个空间。

新需求（用户 2026-07-11 提出，四点）：

1. 页面主体应是「**业务关联**」——一个业务对象关联（拥有）若干 RAG space，而非逐空间设归属；
2. 关联的创建入口**只保留本页「新建」**，其他入口（建空间自动写业务归属等）全部去掉；
3. 页面与数据表要有「**管理端还是客户端**」（端类型）字段；一条关联可挂**多个 rag space**；表字段含 **公司 id、用户 id、组织 id、业务类型**；
4. 现表名 `ai_rag_space_binding` 语义不合适，需要给出**候选表名**。

## 2. 新数据模型

### 2.1 概念

**业务关联（Business Association）** = 一个业务作用域及其空间集合：

```
一条业务关联
├── 端类型 end_type          CLIENT（客户端）/ ADMIN（管理端）
├── 业务类型 business_type    该关联供哪个业务用（种子枚举，见 §2.3）
├── 作用域 id                company_id / user_id / organization_id（按需填，均可空）
└── 关联空间集合              N 个 rag space（子表，1:N）
```

方向反转：不再是「space 属于谁」，而是「业务对象拥有哪些 space」。

### 2.2 表结构（两张新表；表名见 §3 候选）

**主表**（暂以推荐名 `ai_rag_business_association` 书写）：

| 列 | 类型 | 说明 |
|----|------|------|
| id | VARCHAR(36) PK | UUID |
| end_type | VARCHAR(16) NOT NULL | `CLIENT` / `ADMIN`（与 devSupport 各页端类型语义对齐） |
| business_type | VARCHAR(32) NOT NULL | 业务类型 code（§2.3 种子） |
| company_id | VARCHAR(36) NULL | 作用域公司 |
| user_id | VARCHAR(36) NULL | 作用域用户 |
| organization_id | VARCHAR(36) NULL | 作用域组织 |
| created_by / created_at / updated_at | — | 审计（同现有表约定，updated_at 触发器） |

索引：`(end_type, business_type)`、`(company_id)`、`(user_id)`、`(organization_id)`。

**子表** `{主表名}_space`（关联明细，1:N）：

| 列 | 类型 | 说明 |
|----|------|------|
| id | VARCHAR(36) PK | UUID |
| association_id | VARCHAR(36) NOT NULL | FK → 主表 id，ON DELETE CASCADE |
| space_id | VARCHAR(36) NOT NULL | FK → ai_rag_space.id，ON DELETE CASCADE |
| created_at | — | |

约束：`UNIQUE (association_id, space_id)`（同一关联内空间不重复）。**一个 space 允许被多个关联引用**（如同一知识库空间既供 chatbot 又供 playbook；若将来需要独占，加 space_id 唯一索引即可，先不做）。

### 2.3 business_type 种子（代码常量，仿 `SPACE_OWNER_TYPE_SEEDS`）

原 `owner_type` 五值的「端」维度拆到 `end_type` 后，剩下纯业务面：

| code | 显示名 | 说明 |
|------|--------|------|
| KNOWLEDGE_BASE | 知识库 | chatbot 知识库检索作用域（演进方向：kb 工具按关联圈 space） |
| PLAYBOOK | Playbook | Playbook 业务（V1 不设 playbook_id 列——用户字段清单未含；作用域按公司/组织圈定，将来要精确到单 playbook 再加列） |
| PARSING_MEMORY | 解析记忆 | 智能解析映射记忆 |

种子经 `GET /api/ai/rag/association-business-types` 下发（替代现 `GET /owner-types`，返回结构同款 `{code, label}`——新模型下 id 列不再按类型三选一，故无 `idField`）。

### 2.4 现表 `ai_rag_space_binding` 的去向

**回归纯租户归属表，不改名不迁移**：保留 `space_id(唯一)/company_id/organization_id/user_id`——这是建空间时写入、支撑列表与召回**可见性**（同 company + 公司共享/本人私有）的根基，与「业务关联」是两个概念。V006 **删除 V005 刚加的 `owner_type`、`playbook_id` 两列**（该功能尚未产生业务数据，本地/测试环境直接删列；若有存量 owner_type 数据，V006 内先按 §5.3 映射回填成关联再删列）。

## 3. 表名候选（需求点 4，选一个）

| 方案 | 主表 + 子表 | 评价 |
|------|-------------|------|
| **A（推荐）** | `ai_rag_business_association` + `ai_r_business_association_space` | 与页面概念「业务关联」逐字对应，语义最直白；名字略长但全库同风格（ai_rag_ 前缀 + 全拼） |
| B | `ai_rag_business_scope` + `ai_rag_business_scope_space` | 「业务作用域」语义，更短；但"scope 拥有空间"比"association 关联空间"隐晦一点 |
| C | `ai_rag_space_group` + `ai_rag_space_group_item` | 突出"一组空间"；丢了"业务对象"含义，像纯技术分组 |
| D | `ai_rag_biz_binding` + `ai_rag_biz_binding_space` | 延续 binding 词根好联想旧表；但缩写 biz 不合库内全拼风格，且与保留的 `ai_rag_space_binding` 易混 |

推荐 **A**；文档其余部分以 A 书写，选 B/C/D 则全局替换。

## 4. 接口设计（`/api/ai/rag` 前缀，interfaces → service → repository 分层照旧）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/associations` | 分页列表；响应每行含作用域字段 + `spaces: [{spaceId, name, processType}]` 简要 |
| POST | `/associations` | 新建：`{endType, businessType, companyId?, userId?, organizationId?, spaceIds: []}`；spaceIds 允许空（先建作用域后挂空间） |
| PUT | `/associations/{id}` | 编辑：同 POST 字段，space 集合**整体替换**（子表 delete+insert，同事务） |
| DELETE | `/associations/{id}` | 删除关联（级联删子表；**不动 space 本身**） |
| GET | `/association-business-types` | 业务类型种子 |

**下线**（本功能 2026-07-11 刚上线、无其他消费方，前后端同批删）：`GET /owner-types`、`PUT /spaces/{id}/binding`、`space_service.set_binding`、`SPACE_OWNER_TYPE_SEEDS`、Space DTO/VO 上的 `ownerType/playbookId` 回显字段（`companyId/userId/organizationId/isPrivate` 仍来自租户归属 binding，保留）。

**校验**：endType/businessType 白名单；spaceIds 存在性 + 去重；`companyId/userId/organizationId` 至少填一个（无作用域的关联无意义）。

**权限**：页面在 devSupport（SecurityLayout 权限闸门内，管理端页面）。service 侧沿用防越权基线：公司端身份（ctx.company_id 非空）仅可创建/编辑 `companyId == 本公司` 的关联；超管无限制。列表对公司端只返回本公司关联。

## 5. 迁移（V006，business 库）

1. `CREATE TABLE` 主表 + 子表（幂等 IF NOT EXISTS，含英文 COMMENT、索引、updated_at 触发器）；
2. **存量回填**（幂等，`ON CONFLICT DO NOTHING` 语义）：`ai_rag_space_binding` 中 `owner_type IS NOT NULL` 的行 →

   | 旧 owner_type | end_type | business_type | 作用域 id |
   |---------------|----------|---------------|-----------|
   | CLIENT_COMPANY | CLIENT | KNOWLEDGE_BASE | company_id |
   | ADMIN_COMPANY | ADMIN | KNOWLEDGE_BASE | company_id |
   | ADMIN_USER | ADMIN | KNOWLEDGE_BASE | user_id |
   | PLAYBOOK | ADMIN | PLAYBOOK | （playbook_id 丢弃，V1 无此列） |
   | PARSING_MEMORY | ADMIN | PARSING_MEMORY | — |

   同作用域多行合并为一条关联、space 进子表；
3. `ALTER TABLE ai_rag_space_binding DROP COLUMN IF EXISTS owner_type, DROP COLUMN IF EXISTS playbook_id`。

## 6. 前端改版（`/devSupport/rag/binding`，路由与 NAV 入口不变，label 改 "RAG Associations"）

- **列表** = 关联行：端类型（Tag）/ 业务类型 / 公司（IdNameCell）/ 用户（IdNameCell）/ 组织 / 关联空间（数量 + 悬停名称列表）/ 更新时间 / 操作（编辑、删除）。
- **新建/编辑弹窗**：端类型 Select（CLIENT/ADMIN）→ 业务类型 Select（种子）→ 作用域三输入（CompanySelect / UserSelect 复用 `_shared/DirectorySelect`，组织用 organization options 端点）→ **空间多选**（`mode="multiple"`，数据源 `fetchSpaces`，展示 name + processType）。
- 删除需 Modal 确认（提示不影响空间与文档本身）。
- 原「逐空间设置归属」交互整体移除；spaces 管理页/详情页不出现任何关联入口（需求点 2）。

## 7. 入口收敛（需求点 2）

| 入口 | 现状 | 改后 |
|------|------|------|
| 本页「新建/编辑」 | 逐空间 PUT binding | **唯一入口**：POST/PUT `/associations` |
| 建空间自动写归属 | 同时承担租户归属 + 业务归属雏形 | 仅写**租户归属**（company/org/user，可见性用），不再涉业务关联字段 |
| `PUT /spaces/{id}/binding` | 本页旧接口 | 删除 |

## 8. 非目标（本期不做）

- **不接线消费方**：chatbot `search_knowledge_base` / playbook / 解析记忆按关联圈 space 是演进方向（关联表就是为此准备的查找表），本期只交付数据管理，召回可见性链路不动；
- 不做 playbook_id 精确定位列（§2.3）；
- 不做关联级别的启停/生效时间等状态字段（YAGNI）。

## 9. 待确认决策点

1. **表名**：A/B/C/D 选一（推荐 A）；
2. **建空间自动写的租户归属保留**（§2.4/§7）——若连租户归属也去掉，空间列表与召回的可见性根基（`binding.company_id`）会失效，需另行重设计可见性，不建议；
3. business_type 种子三值是否符合预期（KNOWLEDGE_BASE / PLAYBOOK / PARSING_MEMORY，可增删）；
4. 一个 space 允许挂多个关联（§2.2，推荐允许）。
