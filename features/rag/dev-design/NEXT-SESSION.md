# RAG 分层重构 — 适配轮已完成（交接）

> 适配轮 **T2/T3/T6/T9/T11/T12/T13/T14/T15** 已全部完成，`tests/rag/` **77 用例全绿**。
> 改动在 CIOaas-python 子仓库 **`sprint111`** 分支，**未 commit**（git 操作需用户明确要求）。

## 一句话状态

RAG 领域模型已从单表重构为 **platform / ops / business 三层**；旧通用单表 `RagChunk`/`RagEntry` 已删除，改为按 `space.business_type` 分表的业务模型（`financial_report` / `enterprise_kb`）；多租户归属（company/owner）从 Space/Connection 抽到 **binding 表**。

## 建表策略（重要 · 已定）

**RAG 是全新功能，数据库当作空库——直接 CREATE 建表，不做 ALTER 迁移。**

- 新环境建表的**权威入口是 `source/rag/infrastructure/db_bootstrap.py`**（FastAPI lifespan 调用 `Base.metadata.create_all` + 业务 chunk 表 raw SQL）。它已对齐三层模型，会直接建出全部 `ai_rag_*` 表（含 binding、业务 entry/chunk、HNSW/trgm 索引）。
- `sql/migrations/` 下的旧 `rag_*` 手写脚本（无 `ai_` 前缀、单表结构）是历史遗留，**与 ORM/bootstrap 的 `ai_rag_*` 命名不一致**。因 RAG 全新、靠 bootstrap 直接建表，这些旧 migration **无需改写/对齐**；若日后要保留 migration 作归档，单独排期清理即可（不阻塞运行）。

## 已完成改动清单（CIOaas-python，未 commit）

**模型层（domain/models）**
- `business/_base.py`：`RagEntryBase` 补 `task_id`（保 list_by_task / ingest 功能）
- 新建 `platform/space_model.py`（瘦身 RagSpace + `business_type`，去 company/owner/created_by/updated_by）
- 新建 `platform/storage_connection_model.py`（瘦身，去 company_id/created_by）
- `ops/` 迁入 4 张运行时/日志表（ingestion_task / migration_task / search_log / operation_log），import 改 `..platform._common`
- 重写 `models/__init__.py`（三层统一导出）；删旧顶层 `space_model/storage_connection_model/chunk_model/entry_model/_common.py`
- `domain/__init__.py`：转发三层符号
- `infrastructure/db_bootstrap.py`：表清单按三层重组，业务 chunk 表 raw SQL（含 HNSW/trgm）

**Repository（domain/repository）**
- `chunk_repository` / `entry_repository`：构造注入 `chunk_cls` / `entry_cls`（业务表保留 company_id 冗余，过滤逻辑不变）
- `space_repository` / `connection_repository`：JOIN binding 过滤 company_id/owner + 新增 binding 读写方法

**Infra（infrastructure/storage）**
- `pg_store`：注入 `chunk_cls`（`_build_chunk` / `_repo`）
- `factory`：`for_space(space, company_id)` 按 business_type 路由 chunk_cls，缓存键含 business_type
- `connection_resolver`：`resolve(space, company_id=...)`（瘦身 space 已无 company_id）

**Service / DTO**
- `space_service` / `connection_service`：create 写 binding；`_to_dto` / 可见性走 binding
- `search` / `ingest` / `stats` / `migration` service + `pipeline_runner` / `migration_runner`：按 `space.business_type` 路由 entry_cls/chunk_cls
- `dto/space_dto.py`：`SpaceCreateDTO` / `SpaceDTO` 加 `business_type`

**连带修复（既有 bug）**
- 6 处 `from llm import X` 顶层 import 改子模块路径（service/_common、embedder、search/migration/pipeline runner、vision_provider）——测试 conftest 的 llm stub 下顶层 import 会失败（陷阱1 模式）

**测试（tests/rag）**
- 新增 `test_models_exports.py`（三层导出 + bootstrap 表清单冒烟）
- 重写 `test_entry_and_chunk_repository.py`（注入 cls）、`test_space_repository.py`（binding JOIN）
- 改 `test_storage.py`（pg_store 传 chunk_cls + lru_cache 隔离 fixture）、`test_search_service.py`（mock 返回 4 元组）

## 验证与边界

- `cd CIOaas-python; uv run pytest tests/rag/ -v` → **77 passed**
- 测试为项目既有的 **mock 单元测试**风格（编译 SQL 断言 + mock session/store），验证 SQL 构造、business_type 路由、binding 读写、签名一致性。
- **未跑真实 DB 集成**（本项目无 testcontainers/Docker 测试设施）；真实建表正确性由 `db_bootstrap.create_all` 保证（启动期幂等）。

## 后续可选项

- 代码审查（agent teams 多角色 + 审查 skill）
- 提交（CIOaas-python 子仓库，英文 Conventional Commits，需用户确认）
- migration SQL 归档清理（独立任务，不阻塞）

## 参考
- 设计：`features/rag/dev-design/2026-06-04-domain-layering-refactor-design.md`
- 计划（含每个 Task 代码）：`features/rag/dev-design/2026-06-04-domain-layering-refactor-plan.md`
- 测试隔离约定：`CIOaas-python/tests/conftest.py`（llm/lg stub）
