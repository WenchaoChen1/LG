# RAG 召回编排模板方法 + connection_binding 合并 — 设计文档

> 日期：2026-06-12
> 状态：已与用户确认设计，待实现
> 范围：仅 CIOaas-python（`source/rag/`），无 Java / 前端改动
> 关联：`CIOaas-python/CLAUDE.md`（RAG 知识库章节）、`sql/sprint111/rag_schema_business_db.sql`

## 背景与动机

两个独立的改进点，均来自对 RAG 方案 v3（2026-06-12 业务垂直内聚重构）落地后的复盘：

1. **`ai_rag_connection_binding` 是过度设计**：该表存 connection ↔ company 归属（非 ↔ space），
   `connection_id` 上有唯一索引、是严格 1:1，且没有 space_binding 那样的 `user_id`
   可见性语义，只承载 `company_id` + `created_by` 两列。一个 1:1 纯归属关系不需要中间表。
2. **召回编排不够内聚**：`search_service.search` 中召回（`processor.recall`）与记录
   （`processor.record_recall`）是两步分散调用。期望"召回 → 记录"这一固定序列内聚为
   processor 的单一入口方法，service 调用一次即可。

### 已确认的设计边界（用户决策）

召回编排下沉到 processor 的边界为**只下沉「召回 → 记录」序列**：

- base 提供模板方法 `recall_and_record`，内部调子类 `recall`（各业务类型一套）
  → `record_recall`（回调 service 存库）；
- **space 可见性圈定不下沉**——company 归属裁剪、process_type 过滤、跨 backend /
  跨业务类型校验是租户隔离业务规则，需查库开 session，按 `standards/architecture.md`
  留在 application service 层；processor 保持 stateless（只依赖传入的 store）。

被否决的备选：① 圈定 space 也下沉到 processor（违反分层规范、infrastructure→application
反向依赖扩散）；② 维持现状不改（编排零碎，未满足内聚诉求）。

---

## Part 1：`ai_rag_connection_binding` 合并进主表

### 改动清单

| 文件 | 改动 |
|------|------|
| `domain/models/platform/storage_connection_model.py` | `RagStorageConnection` 增加 `company_id VARCHAR(36) NOT NULL`（所属公司）、`created_by VARCHAR(36) NOT NULL`（创建人）两列（ORM 注释中文）；`__table_args__` 增加索引 `idx_ai_rag_conn_company (company_id, deleted)` |
| `domain/models/platform/connection_binding_model.py` | **删除**（`RagConnectionBinding`），同步删 `models/__init__.py` 导出 |
| `domain/repository/connection_repository.py` | 删 `create_binding` / `get_binding` / `list_bindings`；`get_by_id` / `list_by_company` / `count_by_company` 由 JOIN binding 改为 `WHERE company_id` |
| `application/service/connection_service.py` | 创建只写一条主表记录（不再同事务写 binding）；`_to_dto` 去掉 `binding` 参数，直接读 `conn.company_id` / `conn.created_by`（防御性空串分支随之消失） |
| `domain/__init__.py` | 同步去掉 `RagConnectionBinding` re-export（如有） |
| `tests/rag/test_connection_binding_model.py` | **删除**（整文件只测 binding 模型） |
| `tests/rag/test_models_exports.py` | 去掉 `RagConnectionBinding` 导入与表名断言；第 59 行「company_id/created_by 应已移到 RagConnectionBinding」断言反转为「应在主表」；表清单去掉 `ai_rag_connection_binding` |

### SQL（遵循 sprint111 手动 SQL 模式）

- **全量留档** `sql/sprint111/rag_schema_business_db.sql`：
  `ai_rag_storage_connection` 表定义加两列 + 索引；删除 `ai_rag_connection_binding`
  表段；文件头注释「9 张元数据/记录表」改为「8 张」。
- **存量库修改脚本**（新增，幂等，COMMENT 用英文）`sql/sprint111/rag_alter_connection_binding.sql`：
  1. `ALTER TABLE ai_rag_storage_connection ADD COLUMN IF NOT EXISTS company_id / created_by`（先可空）
  2. `UPDATE ... FROM ai_rag_connection_binding` 回填两列
  3. 孤儿行（无 binding 的连接）回填空串——与现状 `_to_dto` 的防御行为语义一致
  4. `SET NOT NULL` + `CREATE INDEX IF NOT EXISTS idx_ai_rag_conn_company`
  5. `DROP TABLE IF EXISTS ai_rag_connection_binding`

### 风险

- 回填脚本第 3 步保证 `SET NOT NULL` 不因孤儿行失败；正常流程（创建即同事务写
  binding）下不应存在孤儿行。
- `DROP TABLE` 不可逆：脚本顺序保证回填完成后才删表；执行前建议确认
  `SELECT count(*) FROM ai_rag_storage_connection WHERE company_id IS NULL` 为 0。

---

## Part 2：召回编排模板方法 `Processor.recall_and_record`

### 新增（`infrastructure/processor/base.py`，约 +30 行）

公共模板方法（非抽象，各业务类型共用；需补 `import time`）：

```python
async def recall_and_record(
    self, *, store, query, top_k, company_id, user_id,
    granted_space_ids, version_groups, caller_type, background, filters=None,
) -> list[SearchHit]:
    """召回 + 记录（模板方法）：子类 recall → record_recall 经 service 存库。"""
    started = time.monotonic()
    hits = await self.recall(            # 多态：STANDARD / STRUCTURED 各自的召回
        store=store, query=query, top_k=top_k, company_id=company_id,
        version_groups=version_groups, filters=filters,
    )
    duration_ms = int((time.monotonic() - started) * 1000)
    self.record_recall(                  # 回调 search_service.build_recall_side_effect 存库
        background=background, company_id=company_id, user_id=user_id,
        granted_space_ids=granted_space_ids, query=query, top_k=top_k,
        caller_type=caller_type, hits=hits, duration_ms=duration_ms,
    )
    return hits
```

满足的诉求：一个入口（单/多 space 经 `version_groups` 天然支持，单文件经
`filters['file_id']`）→ 调各业务类型自己的召回（`recall` 抽象方法多态）→
查询出来后在方法内调 service 的方法把召回结果存入数据库（`record_recall` →
`build_recall_side_effect` → BackgroundTasks）。

### service 侧改动（`application/service/search_service.py`）

- `search`：`rag_op_scope` 内一次调用 `processor.recall_and_record(...)`（新增透传
  `user_id` / `granted` / `caller_type` / `background`），删除原先 scope 外的独立
  `processor.record_recall(...)` 调用；`_enrich` → 构造 `SearchResultDTO` 照旧。
- `build_recall_side_effect` 的 `hits` 类型注解由 `list[SearchHitDTO]` 改为
  `list[SearchHit]`（副作用只用 `chunk_id` / `entry_id` / `space_id` 三个属性，两类型均有）。
- `recall`（mode 路由 + 圈定可见 space + topK 钳制）不变，仍委托 `search`。

### 有意的语义变化（均已验证无害）

1. `ai_rag_search_log.duration_ms` 由「全链路耗时（含圈定 + enrich）」变为
   **纯召回耗时**（更准确反映召回本身）；返回前端的 `SearchResultDTO.duration_ms`
   仍为全链路耗时，不变——两处 duration 自此为不同值，属预期。
2. 记录的命中由 enrich 后变为 enrich 前——已验证集合一致：`_rrf_fuse` 已在 base 内
   截断 top_k，`_enrich` 只补 entryTitle / spaceName / 相似度与 PARTIAL 占位、不增删
   命中（其 `[:top_k]` 为冗余防御），写库的 chunk/entry/space id 集合与现状完全一致。
3. `record_recall` 的投递动作进入 trace scope 内——它只构造副作用对象 + `add_task`，
   真正执行在 BackgroundTasks 线程池（scope 已退出），无实质影响。

### 不变项（明确不动）

- `recall` 仍为抽象方法：STANDARD（`standard_processor.py`，等权 RRF）/
  STRUCTURED（`structured_processor.py`，向量加权）各一套召回。
- `record_recall` 仍为 infrastructure 公共方法 + 延迟导入回调 service（持久化与事务
  在 service 层，分层不变）。
- 三级召回次数（space / entry / chunk `hit_count`）+ `ai_rag_search_log` 历史的
  写库逻辑（`SearchSideEffect.run`）不变。

---

## 测试策略

- **Part 1**：`tests/` 下 connection 相关现有用例调整（去 binding mock，断言
  `company_id` / `created_by` 落主表）；repository 查询改 `WHERE` 后的过滤行为用例。
- **Part 2**：base 新增模板方法单测（mock `recall` / `record_recall`，验证串接顺序、
  参数透传与 `duration_ms` 计时）；`search_service.search` 现有用例调整为断言
  `recall_and_record` 一次调用。
- 覆盖率维持 ≥80%。

## 实施顺序

两部分相互独立，可分别提交：

1. Part 1（connection_binding 合并）：模型 → repository → service → 测试 →
   sprint111 全量 SQL + alter 脚本。
2. Part 2（recall_and_record）：base 模板方法 + 单测 → search_service 接线 + 用例调整。
