# 租户级知识库 — 开发设计

> 关联文档：[多租户与企业级安全 · 需求](../../多租户与企业级安全/需求/requirement-doc.md)（M-7 是收紧现有校验，本文是新增一层共享级别，两者独立）
>
> 范围：`CIOaas-python`。Java 侧仅一项前置依赖（见 §6）；前端面板见 §7 待定。

## 1. 目标

知识库共享级别从两层扩到三层：

| 级别 | 组合键 | 谁能检索到 | 状态 |
|---|---|---|---|
| 公司级 | `(APP, APP_COMPANY, company_id)` | 该公司的公司端用户 + 有该公司权限的管理端用户 | 已有 |
| 管理端级 | `(ADMIN, ADMIN_COMPANY, organization_id)` | 管理端用户（再按可访问公司集收窄） | 已有 |
| **租户级** | `(ALL, TENANT_KB, organization_id)` | **同 organization 下所有人，两端都能看到同一批** | **本次新增** |

## 2. 方案选型

**走业务关联组合键，不新增 `process_type`。**

租户级是**作用域**需求；`process_type` 管的是"走哪条处理管线"。参照物不是 playbook（它靠 `process_type='PLAYBOOK'` 全局直查，不做作用域圈定，`playbook_service.py:355-356` 注释明写"不用业务关联表"），而是 **ERL 附件**——换一个关联 `business_type` 即派生出全新关联行 + 全新 space。

由此**不需要**：新 processor 子包、新 chunk 表、`BUSINESS_REGISTRY` 注册、`build_processor` 分支、`chk_rag_space_process_type` 放宽、`GENERIC_RECALL_EXCLUDED` 登记。`source/rag/CLAUDE.md`「新增处理类型」那整套清单**整体跳过**。

租户级空间 `process_type` 仍为 `STANDARD` → rag 存储 `business_type='enterprise_kb'` → 复用 `ai_rag_ent_kb_chunk`。

**DDL：零**。`ai_rag_business_association.business_type` / `.end_type`、`ai_file_registry.business_type` 均为裸 VARCHAR 无 CHECK；`ai_file_registry.organization_id`（业务库 V015）与 `ai_rag_ent_kb_chunk.organization_id`（向量库 V003）两列**已存在**。可选补一个索引迁移（见 §5）。

## 3. 关键实现点

### 3.1 新增 `end_type = ALL`

`AssociationEndType` 加第三个成员。`_END_TYPES` 是从枚举派生的（`business_association_service.py:37`），5 处校验点（`:79 / :147 / :223 / :551`）**自动放宽，不用逐个改**。

租户级空间查与建**一律写死 `end_type='ALL'`**，`organization_id` 进组合键、`company_id` 恒空。这样公司端与管理端派生出同一个 uuid5 → 同一个 space。

> 不复用 `ADMIN` 的理由：库里会出现标着"管理端"但两端都在读的关联行，语义撒谎，是后续改错的高发点。

### 3.2 空间定位：两个新方法，不改既有分叉

- `ensure_tenant_space()` — 复用 `_ensure_space()`（`business_association_service.py:133-211`，已支持传任意 `business_type` / `process_type`），照 `ensure_erl_space`（`:116-131`）写。
- `find_tenant_space_id()` — 仿 `find_chat_space_id`（`:213-244`）。

**不能复用 `_chat_space_scope`（`:283-298`）与 `_scope_by_end`（`:300-310`）**：前者把 `business_type` 从 `end_type` 二元三目推导死，后者 APP 只带 company、ADMIN 只带 org，都表达不了租户级。新方法直接拼组合键，`_scope_by_end` 保持原样不动。

### 3.3 检索：并入 space + 行级过滤加一支

`knowledge_base_tool.py` 公司端分支（`:104-114`）与管理端分支（`:115-135`）**都要**把 tenant space 追加进 `space_ids`。

行级过滤（`chunk_repository._recall_scope_clauses`，`:66-82`）加一支析取：

```
OR (organization_id = :org AND business_type = 'TENANT_KB')
```

配套 `search_service.recall` 参数族加 `recall_organization_id`（缺省 None → 不产生该分支，HTTP `/recall` 调用方零影响）。

**选"加过滤分支"而非"单独查一次再合并"的理由**：`_normalize_and_merge`（`factory.py:290-300`）按 rag 存储 `business_type` 分组做 min-max 归一后全局取 top_k。租户空间与普通 KB 同属 `enterprise_kb`，单次调用内分数可比；分两次查则各自归一到 [0,1]，**弱的租户命中可能排到强的公司命中前面，且静默无感**，还得人为拍 top_k 怎么分。

### 3.4 写入与上传

- 新增登记原语 `register_tenant_kb_file()`，模板 `register_erl_file`（`lg/db/service/file_registry.py:373-447`，**它已经写 `organization_id`**）。
- **不要**给 `upsert_kb_registration` 加参数——它把 `business_type` 写死 `KNOWLEDGE_BASE`（`:115 / :128`），仓库既有惯例（`register_playbook_file` / `register_erl_file` 的 docstring 都写了）是并列新函数。
- **也不要**顺手给普通 KB 登记行补写 `organization_id`——理由见 §4.1。
- 入库编排复用 `ingest_kb_file` → `start_vectorization`，零改动（`thread_id` 传 None 已支持）。chunk 冗余列回填链（`get_kb_registry_stamp_by_entry` → `stamp_registry_columns`）**逐字不用改**，登记行一写 org，chunk 自动拿到。
- 上传入口：现成的管理端 `POST /api/ai/rag/files` 能灌向量，但**不写 `ai_file_registry` 登记行**（`ingest_service.py:267-268` 明确注释），后果是面板看不见 + chunk 冗余列全 NULL + 召回过滤不到。**必须新建一条编排链**，模板 `erl_attachment_service.py:63-160`。

## 4. 三个必须守住的点

### 4.1 越权：org 分支必须带业务类型限定

会话上传文件（`SESSION_UPLOAD`）**已经带 `organization_id`，且与 ADMIN KB 共用同一个 space**（`business_association_service.py:41` 注释写死了这个设计）。生产库实测：

```
space=9bcf053e  KNOWLEDGE_BASE  484片  org非空=0    company非空=484
space=9bcf053e  SESSION_UPLOAD   61片  org非空=61   company非空=0
```

所以**裸的 `OR organization_id = :org` 会放出同 org 内其他人的会话上传文件**——它们现在靠 `thread_id = 本会话` 保护。org 分支必须 `AND business_type = 'TENANT_KB'`。

同理**不得给普通 KB 登记行补写 `organization_id`**：现有 KB chunk 的 org 恒 NULL（实测 563 片全空）是隔离的一部分，一旦补上，即便有业务类型限定也多了一个可被下一个人写错的面。

失败形态：不报错、不告警，只是多返回几条，**看起来像检索效果变好了**。

### 4.2 回归：公司端管理员会丢掉整个公司 KB

现状公司端管理员 `company_ids=None, thread_id=None` → `scope = []` → `if scope:` 不成立 → **整个 space 无行级过滤**（`chunk_repository.py:121-123`），这是对的，因为 space 本身就是那家公司的。

加了 org 分支后 `scope` 变非空 → 拼出 `WHERE (organization_id=… AND business_type='TENANT_KB')` → **公司端管理员只剩租户文档，公司 KB 全丢**。

处理：公司端也显式传自己的 `company_ids`，使析取成为 `(company_id IN [本公司] OR (org AND TENANT_KB))`。这改变了"公司端不加行级过滤"这条既有约定，**上线前须在真实数据上确认公司 space 内没有 `company_id` 为 NULL 的行会因此被挡掉**（本地库 484/484 均有值）。

### 4.3 `ALL` 会静默落进 `if APP else` 的 ADMIN 支

全仓 19 处对 `end_type` 做分支判断，rag 内有 4 处二元三目（`business_association_service.py:108 / :296 / :308 / :340`）。租户级走 §3.2 的新方法即绕开它们，但**需一次性审计确认没有别的路径会拿着 `ALL` 撞进去**。

## 5. 改动清单

**必改**

| 位置 | 内容 |
|---|---|
| `rag/domain/enums.py` | `AssociationEndType` 加 `ALL`；`ASSOCIATION_BUSINESS_TYPE_SEEDS` 加 `TENANT_KB` 种子 |
| `rag/application/service/business_association_service.py` | 新增 `ensure_tenant_space` + `find_tenant_space_id` |
| `ai/tools/knowledge_base_tool.py` | 两个分支并入 tenant space；公司端补传 `company_ids`（§4.2）；传 `organization_id` |
| `rag/application/service/search_service.py` | `recall` 参数族加 `recall_organization_id` → `filters` |
| `rag/domain/repository/chunk_repository.py` | `_recall_scope_clauses` 加 org 析取支（带业务类型限定） |
| `lg/db/service/file_registry.py` | 新增 `register_tenant_kb_file` |
| 新增租户级入库编排 service + HTTP 端点 | 模板 `erl_attachment_service.py` |
| `sql/migrations/business/V0NN`（可选） | `(organization_id, business_type) WHERE deleted=FALSE` 部分索引——按 org 圈定走不上现有的 `idx_ai_file_registry_kb_scope`（`(company_id, business_type)`） |

**零改动复用**：`ai_file_registry.organization_id` 与 `ai_rag_ent_kb_chunk.organization_id` 两列、chunk 冗余列回填链、`ingest_kb_file` / `start_vectorization` / `finalize_entry` / 删除联动、space 创建挂接机制、`_ensure_space` find-or-create。

**工作量**：核心链路 2～3 人天（不含前端面板与 Java 前置）。

## 6. 前置依赖（Java）

公司端 Redis 会话 `auth:user:{userId}` 当前**不写 `organizationId`**——本地库 `ai_trace` 实测公司端 88 条、org 非空 0 条，而 `sse_provider.py:254` 是无条件写入的，说明源头为空。

租户级要对公司端生效，**必须先由 Java 在登录写会话时补上该字段**。建议动手前在 test 环境用真实公司端账号复验一次（本地数据可能只是测试账号特例）。

## 7. 待定（需产品拍板）

1. **租户级文档要不要出现在知识库面板与 Memory 面板**——两者都按 `company_id IN` 圈定，租户级行（company 为 NULL）会被**静默排除**。要可见则需改 `_kb_documents_query` 与 `distinct_kb_uploaders`（两处必须同改，否则筛选器与列表漂移）+ DTO/VO/路由，另计约 1 人天；并须把面板的 `organizationId` 从前端 query 参数改为会话身份取值——它一旦用于圈定数据就从"展示筛选"升格为"安全边界"。
2. **谁能往租户级知识库上传**（仅平台管理员？租户管理员？）——决定新端点的鉴权闸门。
3. 租户级文档是否参与 Memory 面板的"记忆"语义。
