# RAG 领域模型分层重构设计

- 日期：2026-06-04
- 范围：`CIOaas-python/source/rag/domain/models` + 对应 migration
- 状态：**设计已定稿**（未上线，可直接改 ORM + migration，无需数据迁移脚本）
- 关系：本文件是对 `dev-design-doc.md`（原始设计）的**领域分层重构**，不替代原文件

---

## 1. 目标（关注点分离）

把 RAG 领域实体按「**服务谁**」拆成三层，消除技术配置实体里混入的系统业务字段，**且不减少任何现有前端功能**：

1. **平台层**：通用 RAG 引擎配置——空间、连接、绑定。与具体业务无关。
2. **业务关联层**：RAG 与「系统业务（公司/用户）」的**唯一关联入口**。
3. **运行时/日志层（ops）**：入库进度、模型迁移、检索统计、操作审计。跨业务通用。
4. **业务数据层**：实际向量化数据。**一个业务一个文件夹，结构各异**。

核心诉求对应：

| 你的诉求 | 落地 |
|---------|------|
| Space 只是空间（连库/名称/存储类型/向量化逻辑） | 平台层 `RagSpace` 瘦身 |
| 「业务存储类型」 | `RagSpace.business_type` |
| StorageConnection 不该有 company_id | 平台层 `RagStorageConnection` 瘦身 |
| 和业务关联的只有一个 | `RagSpaceBinding` / `RagConnectionBinding` |
| 业务数据单独文件夹、不同业务不同结构 | `business/<业务>/` 各自 entry+chunk |
| 每个 space 每个片段的召回要有统计 | 业务 chunk 公共基类带 `hit_count`；检索明细由 `SearchLog` 记录 |
| 前端业务功能不能减少 | 4 张辅助表全保留（归 `ops/`） |
| 默认库可用、连接表的连接也可用 | `storage_config_mode` 保留 default + custom 两模式 |

---

## 2. 采纳的关键决策（已定稿）

- **D1 范围**：只重构 `Space` + `Connection` 抽离业务字段；其余表的 `company_id` 作派生冗余保留（做隔离/索引/命中 HNSW）。
- **D2 多租户**：业务关联表是**权威源**；查询表（Chunk/Entry…）**保留冗余 `company_id`**，由 service 写入时保证一致——性能优先。
- **D3 连接归属**：`Connection` 去 `company_id`，归属移到 `RagConnectionBinding`，仍按公司隔离（A 公司看不到 B 公司连接）。
- **D4 关联表形态**：专用 binding 表（`RagSpaceBinding`、`RagConnectionBinding`），语义清晰、约束强。
- **D5 功能全保留**：现有前端功能不减少 → `IngestionTask` / `MigrationTask` / `SearchLog` / `OperationLog` **全部保留**，归入 `ops/`（跨业务通用）。
- **D6 业务数据**：按业务拆表，每业务独立 chunk 表 + 独立 HNSW 索引；公共基类保证统一召回视图。
- **D7 存储模式**：`default`（走 env 默认数据库）与 `custom`（走连接表的连接）**两种都保留**。
- **D8 片段召回统计**：每个业务 chunk 表经公共基类带 `hit_count`（每片段累计召回次数）；逐次检索明细统计由 `SearchLog` 承载。
- **D9 连接 code**：维持「公司内唯一」语义（由 service + `RagConnectionBinding` 保证），**不改全局唯一**。

---

## 3. 目录结构

```
source/rag/domain/models/
├── platform/
│   ├── _common.py                    # Base / _now / _new_uuid / 维度白名单
│   ├── space_model.py                # RagSpace（瘦身 + business_type）
│   ├── storage_connection_model.py   # RagStorageConnection（瘦身）
│   ├── space_binding_model.py        # RagSpaceBinding（业务关联）
│   └── connection_binding_model.py   # RagConnectionBinding（业务关联）
├── ops/                              # 运行时与日志（跨业务通用，不分业务）
│   ├── ingestion_task_model.py       # RagIngestionTask（入库批次进度）
│   ├── migration_task_model.py       # RagMigrationTask（embedding 迁移状态机）
│   ├── search_log_model.py           # RagSearchLog（检索统计 / 召回明细）
│   └── operation_log_model.py        # RagOperationLog（写操作审计）
└── business/
    ├── _base.py                      # RagEntryBase / RagChunkBase（公共抽象基类）
    ├── financial_report/             # 业务 A（字段可继续细化）
    │   ├── entry_model.py            # FinancialReportEntry
    │   └── chunk_model.py            # FinancialReportChunk
    └── enterprise_kb/                # 业务 B（字段可继续细化）
        ├── entry_model.py            # EnterpriseKbEntry
        └── chunk_model.py            # EnterpriseKbChunk
```

> 业务名 `financial_report` / `enterprise_kb` 已被你接受；特有字段（§5.2/5.3）为示例，可后续细化。

---

## 4. 平台层表结构

### 4.1 RagSpace（`ai_rag_space`，瘦身）

去掉：`company_id` / `owner_type` / `owner_user_id` / `created_by` / `updated_by`（移到 binding）。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(255) | 空间名称 |
| description | Text | 描述 |
| **business_type** | String(32) | **业务存储类型**，决定用哪套业务表（financial_report / enterprise_kb…）。创建后不可变 |
| storage_backend | String(8) | 物理后端 pg/es。创建后不可变 |
| storage_config_mode | String(8) | **default（默认库）/ custom（连接表）两种都支持** |
| connection_ref | String(64) | custom 模式指向 connection.code |
| index_name_override / index_name_template | String | 索引命名（互斥） |
| pg_schema / pg_table_name | String | PG 隔离选项 |
| embedding_provider / embedding_model / embedding_dim | — | 向量化配置 |
| current_embedding_version / pending_embedding_* | — | 版本路由 |
| default_chunk_size / default_chunk_overlap | Integer | 切片默认值 |
| vector_index_params / retrieval_params | JSONB | 索引/召回参数 |
| status | String(16) | READY / MIGRATING / MIGRATION_FAILED |
| deleted / deleted_at | — | 软删（技术性，保留） |
| created_at / updated_at | TIMESTAMP | 系统时间戳（"谁创建"移到 binding） |

### 4.2 RagStorageConnection（`ai_rag_storage_connection`，瘦身）

去掉：`company_id` / `created_by`。

| 字段 | 说明 |
|------|------|
| id PK | UUID |
| code | 连接短码，**公司内唯一**（由 service + binding 保证，D9） |
| backend | pg / es |
| display_name | 展示名 |
| pg_* / es_* / extra_config | 连接技术字段 + 加密凭据 |
| health_status / last_checked_at | 健康检查 |
| deleted / created_at / updated_at | — |

### 4.3 RagSpaceBinding（`ai_rag_space_binding`，新增）

RAG↔业务的唯一关联入口（空间维度）。

| 字段 | 说明 |
|------|------|
| id PK | UUID |
| space_id | FK→ai_rag_space.id，**unique**（一空间一归属） |
| company_id | 所属公司（多租户权威源） |
| owner_type | COMPANY / PERSONAL |
| owner_user_id | 个人空间所有者 |
| created_by / updated_by | 审计 |
| created_at / updated_at | — |
| 索引 | uk(space_id)；idx(company_id, owner_type, owner_user_id) |

### 4.4 RagConnectionBinding（`ai_rag_connection_binding`，新增）

连接的公司归属（保证连接列表按公司隔离）。

| 字段 | 说明 |
|------|------|
| id PK | UUID |
| connection_id | FK→connection.id，unique |
| company_id | 所属公司 |
| created_by | 审计 |
| created_at | — |
| 索引 | uk(connection_id)；idx(company_id)；uk(company_id, code 反查) 由 service 保证 |

---

## 5. 业务数据层

### 5.1 公共抽象基类（`business/_base.py`）

用 SQLAlchemy abstract mixin（`__abstract__ = True` + `@declared_attr`）提供公共列，**保证前端统一召回视图**：所有业务 chunk 都有 `space_id + hit_count + embedding + content`，可被同一套「按 space 列出片段 + 召回次数」接口读取。

`RagChunkBase`（abstract）公共列：
`id, space_id(冗余,命中HNSW), company_id(冗余,租户隔离), entry_id, embedding_version, seq, content, content_tokens, embedding Vector(1536), metadata, hit_count(召回次数统计), created_at`

`RagEntryBase`（abstract）公共列：
`id, space_id, company_id(冗余), source_type, file_id, title, content_text, mime_type, file_size_bytes, chunk_size_used, chunk_overlap_used, embedding_version, chunk_count, total_tokens, status, processing_stage, error_message, hit_count, deleted, deleted_at, created_at, updated_at`

> `company_id` 作冗余（D2）：权威在 `RagSpaceBinding`，业务表冗余一份供向量检索单表过滤命中 HNSW。

### 5.2 业务 A：financial_report

- 表 `ai_rag_fin_report_chunk` / `ai_rag_fin_report_entry`
- chunk 特有列（示例）：`fiscal_year`(财年)、`company_ref`(关联公司)、`statement_type`(资产负债/利润/现金流)
- entry 特有列（示例）：`report_period`、`source_company_id`

### 5.3 业务 B：enterprise_kb

- 表 `ai_rag_ent_kb_chunk` / `ai_rag_ent_kb_entry`
- chunk 特有列（示例）：`category`(分类)、`effective_date`(生效日期)、`doc_version`
- entry 特有列（示例）：`department`、`confidentiality`

### 5.4 业务路由

- `RagSpace.business_type` → 映射到业务表类（注册表 `BUSINESS_REGISTRY = {"financial_report": (FinancialReportEntry, FinancialReportChunk), ...}`）。
- service/repository 按 `space.business_type` 取对应 Entry/Chunk 类做读写与检索。
- 向量检索：每业务表各自 HNSW 索引，`WHERE space_id + company_id + embedding_version`。

---

## 6. 前端「每个 space 每个片段召回 + 统计」如何满足

1. 一个 space 绑定一个 business_type → 该 space 的所有 chunk 都在同一张业务表。
2. 前端「列出某 space 的所有片段 + 召回」= 经 `business_type` 路由到对应 chunk 表，`WHERE space_id=X ORDER BY seq`，读公共列（含 `hit_count` 召回次数）。
3. 公共基类保证不同业务表都暴露相同的召回展示字段，前端/service 无需关心业务差异。
4. 逐次检索的召回明细（哪次查询命中哪些片段、耗时、top_k）由 `ops/search_log_model.py` 记录，支撑统计页。

---

## 7. 影响与迁移

- **未上线** → 直接改 ORM + 改写 migration `rag_003`(space) / `rag_009`(connection) + 新增 binding & 业务表 migration；`ops/` 4 表沿用原 `rag_004/007/008/operation_log` 定义只调整 import 路径；**无数据迁移脚本**。
- 需同步改：`space_repository` / `connection_repository`（company_id 来源改为 join/写 binding）、`space_service` / `connection_service`（创建时写 binding、可见性过滤走 binding）、`chunk_repository`（按 business_type 路由表）、`connection_resolver` / `factory`（default/custom 两模式）、`db_bootstrap`（注册新表）、DTO（SpaceDTO/ConnectionDTO 字段来源调整）。
- `__init__.py` re-export 改为 `from .platform... / .ops... / .business...`。

---

## 8. 已确认决策（2026-06-04）

1. ✅ 两个业务名采用 `financial_report` / `enterprise_kb`；特有字段为示例，后续可细化。
2. ✅ `connection.code` 维持公司内唯一（不改全局唯一）。
3. ✅ 保留 `RagConnectionBinding`（连接按公司隔离）。
4. ✅ 4 张辅助表全部保留（前端功能不减少），归入 `ops/`。
5. ✅ default + custom 两种存储模式都保留。
6. ✅ 片段召回统计：chunk.hit_count + SearchLog。

---

## 9. 下一步

进入 `writing-plans`：按"平台层 → ops 层 → 业务层 → migration → repository/service/DTO 适配 → bootstrap/导出"的顺序产出分步实现计划。
