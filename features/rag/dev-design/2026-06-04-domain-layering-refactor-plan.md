# RAG 领域模型分层重构 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `rag/domain/models` 按 platform / ops / business 三层拆分，将系统业务字段（company_id / owner / created_by）从 Space、Connection 抽离到专用 binding 表，并把向量数据按业务拆成独立表，前端功能与召回统计零削减。

**Architecture:** 三层模型目录（platform 配置 / ops 运行时日志 / business 按业务分文件夹）。业务 chunk/entry 继承公共抽象基类保证统一召回视图；`RagSpace.business_type` + `BUSINESS_REGISTRY` 路由到具体业务表。多租户权威源是 binding 表，查询表保留 company_id 冗余以命中 HNSW。

**Tech Stack:** Python 3.12, SQLAlchemy 2.x (DeclarativeBase), pgvector 0.3.6, PostgreSQL (vector + pg_trgm), pytest + testcontainers。

**测试策略：** 模型层用「create_all(checkfirst=True) 建表 + 断言约束/索引/字段」集成测试（testcontainers PG）；路由/注册表与 service binding 写入用单元测试。每个 Task 末尾 commit。

参考设计：`features/rag/dev-design/2026-06-04-domain-layering-refactor-design.md`

---

## 文件结构

**新建（domain/models 下）：**
```
platform/_common.py · platform/space_model.py · platform/storage_connection_model.py
platform/space_binding_model.py · platform/connection_binding_model.py
ops/__init__.py · ops/ingestion_task_model.py · ops/migration_task_model.py
ops/search_log_model.py · ops/operation_log_model.py
business/__init__.py · business/_base.py · business/_registry.py
business/financial_report/{entry_model,chunk_model}.py
business/enterprise_kb/{entry_model,chunk_model}.py
```
**重写：** `domain/models/__init__.py`
**删除：** 旧的顶层 `space_model/storage_connection_model/chunk_model/entry_model/_common.py`（内容迁移后）
**适配：** `domain/repository/*`、`application/service/{space,connection,search,ingest}_service.py`、`application/dto/{space,connection}_dto.py`、`infrastructure/storage/{connection_resolver,factory}.py`、`infrastructure/db_bootstrap.py`
**migration：** 改写 `rag_003`(space)/`rag_009`(connection)，新增 binding + business 表 SQL

---

## Task 1: platform/_common.py 共享基建

**Files:**
- Create: `source/rag/domain/models/platform/_common.py`
- Create: `source/rag/domain/models/platform/__init__.py`（空占位）
- Test: `tests/rag/test_platform_common.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_platform_common.py
def test_common_exports_base_and_helpers():
    from rag.domain.models.platform._common import (
        Base, _now, _new_uuid, RAG_EMBEDDING_DIM, _EMBEDDING_MODEL_WHITELIST,
    )
    assert RAG_EMBEDDING_DIM == 1536
    uid = _new_uuid()
    assert isinstance(uid, str) and len(uid) == 36
    from lg.db.models.models import Base as RootBase
    assert Base is RootBase
```

- [ ] **Step 2: 运行确认失败**

Run: `cd CIOaas-python && pytest tests/rag/test_platform_common.py -v`
Expected: FAIL（ModuleNotFoundError: rag.domain.models.platform）

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/platform/_common.py
"""RAG 平台层 ORM 共享基建：复用根 Base，集中维度白名单与 UUID/时间助手。"""
from __future__ import annotations

import uuid

from lg.db.models.models import Base, _now
from llm import get_models_by_dim

RAG_EMBEDDING_DIM = 1536

_EMBEDDING_MODEL_WHITELIST = (
    "(" + ", ".join(f"'{m}'" for m in get_models_by_dim(RAG_EMBEDDING_DIM)) + ")"
)


def _new_uuid() -> str:
    return str(uuid.uuid4())


__all__ = [
    "Base", "_now", "_new_uuid", "RAG_EMBEDDING_DIM", "_EMBEDDING_MODEL_WHITELIST",
]
```

```python
# source/rag/domain/models/platform/__init__.py
```

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_platform_common.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/platform/_common.py source/rag/domain/models/platform/__init__.py tests/rag/test_platform_common.py
git commit -m "feat(rag): add platform layer _common shared base"
```

---

## Task 2: platform/space_model.py（RagSpace 瘦身 + business_type）

**Files:**
- Create: `source/rag/domain/models/platform/space_model.py`
- Test: `tests/rag/test_space_model.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_space_model.py
def test_space_has_business_type_and_no_business_columns():
    from rag.domain.models.platform.space_model import RagSpace
    cols = set(RagSpace.__table__.columns.keys())
    assert "business_type" in cols
    for removed in ("company_id", "owner_type", "owner_user_id", "created_by", "updated_by"):
        assert removed not in cols, f"{removed} 应已移到 RagSpaceBinding"
    assert RagSpace.__tablename__ == "ai_rag_space"
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_space_model.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/platform/space_model.py
"""RAG 空间 ORM（ai_rag_space，瘦身）：纯技术 + 向量化配置，业务归属移到 RagSpaceBinding。"""
from __future__ import annotations

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Index, Integer, String, Text, TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB

from ._common import (
    Base, RAG_EMBEDDING_DIM, _EMBEDDING_MODEL_WHITELIST, _new_uuid, _now,
)


class RagSpace(Base):
    """RAG 空间：名称 + 业务存储类型 + 物理存储 + 向量化逻辑配置。"""

    __tablename__ = "ai_rag_space"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    business_type = Column(String(32), nullable=False)
    """业务存储类型：决定用哪套业务表（financial_report / enterprise_kb…）。创建后不可变。"""

    embedding_provider = Column(String(32), nullable=False)
    embedding_model = Column(String(128), nullable=False)
    embedding_dim = Column(Integer, nullable=False, default=RAG_EMBEDDING_DIM)
    current_embedding_version = Column(Integer, nullable=False, default=1)
    pending_embedding_version = Column(Integer)
    pending_embedding_provider = Column(String(32))
    pending_embedding_model = Column(String(128))

    default_chunk_size = Column(Integer, nullable=False, default=800)
    default_chunk_overlap = Column(Integer, nullable=False, default=100)

    status = Column(String(16), nullable=False, default="READY")
    deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(TIMESTAMP(timezone=True))

    storage_backend = Column(String(8), nullable=False, default="pg")
    storage_config_mode = Column(String(8), nullable=False, default="default")
    connection_ref = Column(String(64))
    index_name_override = Column(String(128))
    index_name_template = Column(String(128))
    pg_schema = Column(String(64))
    pg_table_name = Column(String(128))
    vector_index_params = Column(JSONB, nullable=False, default=dict)
    retrieval_params = Column(
        JSONB, nullable=False, default=lambda: {"top_k": 10, "rrf_k": 60},
    )

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    __table_args__ = (
        CheckConstraint(
            f"embedding_model IN {_EMBEDDING_MODEL_WHITELIST}",
            name="chk_rag_space_embedding_model",
        ),
        CheckConstraint(
            f"embedding_dim = {RAG_EMBEDDING_DIM}", name="chk_rag_space_embedding_dim",
        ),
        CheckConstraint(
            "(pending_embedding_version IS NULL AND pending_embedding_provider IS NULL "
            " AND pending_embedding_model IS NULL) "
            "OR (pending_embedding_version IS NOT NULL AND pending_embedding_provider IS NOT NULL "
            " AND pending_embedding_model IS NOT NULL)",
            name="chk_rag_space_pending_consistency",
        ),
        CheckConstraint(
            f"pending_embedding_model IS NULL OR pending_embedding_model IN {_EMBEDDING_MODEL_WHITELIST}",
            name="chk_rag_space_pending_model",
        ),
        CheckConstraint("storage_backend IN ('pg', 'es')", name="chk_rag_space_backend"),
        CheckConstraint(
            "storage_config_mode IN ('default', 'custom')", name="chk_rag_space_storage_mode",
        ),
        CheckConstraint(
            "(storage_config_mode = 'default' AND connection_ref IS NULL) "
            "OR (storage_config_mode = 'custom' AND connection_ref IS NOT NULL)",
            name="chk_rag_space_mode_ref_consistent",
        ),
        CheckConstraint(
            "NOT (index_name_override IS NOT NULL AND index_name_template IS NOT NULL)",
            name="chk_rag_space_index_naming",
        ),
        Index("idx_ai_rag_space_business_type", "business_type", "deleted"),
        Index("idx_ai_rag_space_backend", "storage_backend",
              postgresql_where=Column("deleted") == False),  # noqa: E712
        Index("idx_ai_rag_space_connection_ref", "connection_ref",
              postgresql_where=Column("connection_ref").isnot(None)),
    )


__all__ = ["RagSpace"]
```

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_space_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/platform/space_model.py tests/rag/test_space_model.py
git commit -m "feat(rag): slim RagSpace, add business_type, drop business columns"
```

---

## Task 3: platform/storage_connection_model.py（瘦身）

**Files:**
- Create: `source/rag/domain/models/platform/storage_connection_model.py`
- Test: `tests/rag/test_connection_model.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_connection_model.py
def test_connection_dropped_business_columns():
    from rag.domain.models.platform.storage_connection_model import RagStorageConnection
    cols = set(RagStorageConnection.__table__.columns.keys())
    for removed in ("company_id", "created_by"):
        assert removed not in cols, f"{removed} 应已移到 RagConnectionBinding"
    assert "code" in cols and "backend" in cols
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_connection_model.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/platform/storage_connection_model.py
"""RAG 连接配置（ai_rag_storage_connection，瘦身）：纯连接技术，公司归属移到 RagConnectionBinding。"""
from __future__ import annotations

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Index, Integer, String, Text, TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB

from ._common import Base, _new_uuid, _now


class RagStorageConnection(Base):
    """连接配置（公司归属见 RagConnectionBinding；凭据 AES-256-GCM 加密）。"""

    __tablename__ = "ai_rag_storage_connection"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    code = Column(String(64), nullable=False)
    """连接短码，公司内唯一（由 service + RagConnectionBinding 保证）。"""
    backend = Column(String(8), nullable=False)
    display_name = Column(String(128), nullable=False)

    pg_host = Column(String(255))
    pg_port = Column(Integer)
    pg_database = Column(String(64))
    pg_username = Column(String(64))
    pg_password_enc = Column(Text)
    pg_sslmode = Column(String(16), default="require")

    es_cloud_id = Column(Text)
    es_endpoint = Column(String(512))
    es_api_key_enc = Column(Text)

    extra_config = Column(JSONB, nullable=False, default=dict)
    health_status = Column(String(16), nullable=False, default="UNKNOWN")
    last_checked_at = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now
    )
    deleted = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("backend IN ('pg', 'es')", name="chk_rag_conn_backend"),
        CheckConstraint(
            "health_status IN ('HEALTHY', 'UNHEALTHY', 'UNKNOWN')", name="chk_rag_conn_health",
        ),
        CheckConstraint(
            "backend != 'pg' OR (pg_host IS NOT NULL AND pg_port IS NOT NULL "
            " AND pg_database IS NOT NULL)",
            name="chk_rag_conn_pg_required",
        ),
        CheckConstraint(
            "backend != 'es' OR (es_endpoint IS NOT NULL OR es_cloud_id IS NOT NULL)",
            name="chk_rag_conn_es_required",
        ),
        Index("idx_ai_rag_conn_health_check", "health_status", "last_checked_at"),
    )


__all__ = ["RagStorageConnection"]
```

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_connection_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/platform/storage_connection_model.py tests/rag/test_connection_model.py
git commit -m "feat(rag): slim RagStorageConnection, drop company_id/created_by"
```

---

## Task 4: platform/space_binding_model.py（新增）

**Files:**
- Create: `source/rag/domain/models/platform/space_binding_model.py`
- Test: `tests/rag/test_space_binding_model.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_space_binding_model.py
def test_space_binding_columns_and_unique():
    from rag.domain.models.platform.space_binding_model import RagSpaceBinding
    cols = set(RagSpaceBinding.__table__.columns.keys())
    assert {"space_id", "company_id", "owner_type", "owner_user_id",
            "created_by", "updated_by"} <= cols
    assert RagSpaceBinding.__tablename__ == "ai_rag_space_binding"
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_space_binding_model.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/platform/space_binding_model.py
"""RAG 空间业务归属（ai_rag_space_binding）：RAG↔公司/用户的唯一关联入口（空间维度）。"""
from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, String, TIMESTAMP

from ._common import Base, _new_uuid, _now


class RagSpaceBinding(Base):
    """一个空间一条归属记录（company / owner / 创建人）。"""

    __tablename__ = "ai_rag_space_binding"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    space_id = Column(
        String(36), ForeignKey("ai_rag_space.id", ondelete="CASCADE"), nullable=False,
    )
    company_id = Column(String(36), nullable=False)
    owner_type = Column(String(16), nullable=False)
    owner_user_id = Column(String(36))
    created_by = Column(String(36), nullable=False)
    updated_by = Column(String(36))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    __table_args__ = (
        CheckConstraint(
            "(owner_type = 'COMPANY' AND owner_user_id IS NULL) OR "
            "(owner_type = 'PERSONAL' AND owner_user_id IS NOT NULL)",
            name="chk_rag_space_binding_owner",
        ),
        Index("uk_rag_space_binding_space", "space_id", unique=True),
        Index("idx_rag_space_binding_company", "company_id", "owner_type", "owner_user_id"),
    )


__all__ = ["RagSpaceBinding"]
```

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_space_binding_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/platform/space_binding_model.py tests/rag/test_space_binding_model.py
git commit -m "feat(rag): add RagSpaceBinding business ownership entity"
```

---

## Task 5: platform/connection_binding_model.py（新增）

**Files:**
- Create: `source/rag/domain/models/platform/connection_binding_model.py`
- Test: `tests/rag/test_connection_binding_model.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_connection_binding_model.py
def test_connection_binding_columns():
    from rag.domain.models.platform.connection_binding_model import RagConnectionBinding
    cols = set(RagConnectionBinding.__table__.columns.keys())
    assert {"connection_id", "company_id", "created_by"} <= cols
    assert RagConnectionBinding.__tablename__ == "ai_rag_connection_binding"
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_connection_binding_model.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/platform/connection_binding_model.py
"""RAG 连接业务归属（ai_rag_connection_binding）：连接↔公司，保证连接列表按公司隔离。"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, String, TIMESTAMP

from ._common import Base, _new_uuid, _now


class RagConnectionBinding(Base):
    """一个连接一条公司归属。"""

    __tablename__ = "ai_rag_connection_binding"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    connection_id = Column(
        String(36),
        ForeignKey("ai_rag_storage_connection.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id = Column(String(36), nullable=False)
    created_by = Column(String(36), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        Index("uk_rag_conn_binding_conn", "connection_id", unique=True),
        Index("idx_rag_conn_binding_company", "company_id"),
    )


__all__ = ["RagConnectionBinding"]
```

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_connection_binding_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/platform/connection_binding_model.py tests/rag/test_connection_binding_model.py
git commit -m "feat(rag): add RagConnectionBinding ownership entity"
```

---

## Task 6: ops/ 层（迁移 4 张运行时/日志表）

ops 表定义沿用现有 4 个 model，**仅改 import 来源**为 `from ..platform._common import Base, _new_uuid, _now`。

**Files:**
- Create: `source/rag/domain/models/ops/__init__.py`（空占位）
- Move+Edit: 4 个 model 文件到 `ops/`
- Test: `tests/rag/test_ops_models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_ops_models.py
def test_ops_models_import():
    from rag.domain.models.ops.ingestion_task_model import RagIngestionTask
    from rag.domain.models.ops.migration_task_model import RagMigrationTask
    from rag.domain.models.ops.search_log_model import RagSearchLog
    from rag.domain.models.ops.operation_log_model import RagOperationLog
    assert RagIngestionTask.__tablename__ == "ai_rag_ingestion_task"
    assert RagSearchLog.__tablename__ == "ai_rag_search_log"
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_ops_models.py -v`
Expected: FAIL

- [ ] **Step 3: 迁移文件**

```bash
git mv source/rag/domain/models/ingestion_task_model.py source/rag/domain/models/ops/ingestion_task_model.py
git mv source/rag/domain/models/migration_task_model.py source/rag/domain/models/ops/migration_task_model.py
git mv source/rag/domain/models/search_log_model.py source/rag/domain/models/ops/search_log_model.py
git mv source/rag/domain/models/operation_log_model.py source/rag/domain/models/ops/operation_log_model.py
```
在每个迁移后的文件里把 `from ._common import ...` 改为 `from ..platform._common import ...`，创建空 `ops/__init__.py`。

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_ops_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/ops/ tests/rag/test_ops_models.py
git commit -m "refactor(rag): move runtime/log models into ops layer"
```

---

## Task 7: business/_base.py（公共抽象基类）

**Files:**
- Create: `source/rag/domain/models/business/__init__.py`（空占位）
- Create: `source/rag/domain/models/business/_base.py`
- Test: `tests/rag/test_business_base.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_business_base.py
def test_base_is_abstract_and_has_recall_columns():
    from rag.domain.models.business._base import RagChunkBase, RagEntryBase
    assert getattr(RagChunkBase, "__abstract__", False) is True
    assert getattr(RagEntryBase, "__abstract__", False) is True
    assert hasattr(RagChunkBase, "hit_count")
    assert hasattr(RagChunkBase, "space_id")
    assert hasattr(RagChunkBase, "embedding")
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_business_base.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/business/_base.py
"""业务数据公共抽象基类：保证不同业务的 entry/chunk 暴露统一的召回展示字段。"""
from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger, Boolean, Column, Integer, String, Text, TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB

from ..platform._common import Base, RAG_EMBEDDING_DIM, _new_uuid, _now


class RagEntryBase(Base):
    """业务条目公共列（abstract，不建表）。"""
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=_new_uuid)
    space_id = Column(String(36), nullable=False)
    company_id = Column(String(36), nullable=False)  # 冗余，租户隔离
    source_type = Column(String(16), nullable=False)
    file_id = Column(String(36))
    title = Column(String(512), nullable=False)
    content_text = Column(Text)
    mime_type = Column(String(128))
    file_size_bytes = Column(BigInteger)
    chunk_size_used = Column(Integer, nullable=False)
    chunk_overlap_used = Column(Integer, nullable=False)
    embedding_version = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="PROCESSING")
    processing_stage = Column(String(32))
    error_message = Column(Text)
    hit_count = Column(BigInteger, nullable=False, default=0)
    deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(TIMESTAMP(timezone=True))
    created_by = Column(String(36), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class RagChunkBase(Base):
    """业务片段公共列（abstract，不建表）；hit_count = 召回次数统计。"""
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=_new_uuid)
    space_id = Column(String(36), nullable=False)   # 冗余，命中 HNSW
    company_id = Column(String(36), nullable=False)  # 冗余，租户隔离
    entry_id = Column(String(36), nullable=False)
    embedding_version = Column(Integer, nullable=False)
    seq = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_tokens = Column(Integer, nullable=False)
    embedding = Column(Vector(RAG_EMBEDDING_DIM), nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    hit_count = Column(BigInteger, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)


__all__ = ["RagEntryBase", "RagChunkBase"]
```

```python
# source/rag/domain/models/business/__init__.py
```

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_business_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/business/_base.py source/rag/domain/models/business/__init__.py tests/rag/test_business_base.py
git commit -m "feat(rag): add business data abstract base classes"
```

---

## Task 8: 两个业务模型 + 注册表

**Files:**
- Create: `business/financial_report/{__init__,entry_model,chunk_model}.py`
- Create: `business/enterprise_kb/{__init__,entry_model,chunk_model}.py`
- Create: `business/_registry.py`
- Test: `tests/rag/test_business_models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_business_models.py
def test_two_business_tables_distinct():
    from rag.domain.models.business.financial_report.chunk_model import FinancialReportChunk
    from rag.domain.models.business.enterprise_kb.chunk_model import EnterpriseKbChunk
    assert FinancialReportChunk.__tablename__ == "ai_rag_fin_report_chunk"
    assert EnterpriseKbChunk.__tablename__ == "ai_rag_ent_kb_chunk"
    for m in (FinancialReportChunk, EnterpriseKbChunk):
        cols = set(m.__table__.columns.keys())
        assert {"space_id", "hit_count", "embedding", "content"} <= cols
    assert "fiscal_year" in FinancialReportChunk.__table__.columns.keys()
    assert "category" in EnterpriseKbChunk.__table__.columns.keys()

def test_registry_routes_business_type():
    from rag.domain.models.business._registry import BUSINESS_REGISTRY, get_business_models
    e, c = get_business_models("financial_report")
    assert c.__tablename__ == "ai_rag_fin_report_chunk"
    assert "enterprise_kb" in BUSINESS_REGISTRY
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_business_models.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/business/financial_report/entry_model.py
"""财务报表业务条目（ai_rag_fin_report_entry）。"""
from __future__ import annotations
from sqlalchemy import Column, Index, String
from .._base import RagEntryBase


class FinancialReportEntry(RagEntryBase):
    __tablename__ = "ai_rag_fin_report_entry"
    report_period = Column(String(32))
    source_company_id = Column(String(36))
    __table_args__ = (
        Index("idx_fin_report_entry_space_status", "space_id", "status", "deleted"),
    )


__all__ = ["FinancialReportEntry"]
```

```python
# source/rag/domain/models/business/financial_report/chunk_model.py
"""财务报表业务片段（ai_rag_fin_report_chunk）。"""
from __future__ import annotations
from sqlalchemy import Column, Index, Integer, String
from .._base import RagChunkBase


class FinancialReportChunk(RagChunkBase):
    __tablename__ = "ai_rag_fin_report_chunk"
    fiscal_year = Column(Integer)
    company_ref = Column(String(36))
    statement_type = Column(String(32))
    __table_args__ = (
        Index("idx_fin_report_chunk_space_version", "space_id", "embedding_version"),
        Index("idx_fin_report_chunk_entry", "entry_id"),
    )


__all__ = ["FinancialReportChunk"]
```

```python
# source/rag/domain/models/business/financial_report/__init__.py
from .entry_model import FinancialReportEntry
from .chunk_model import FinancialReportChunk
__all__ = ["FinancialReportEntry", "FinancialReportChunk"]
```

```python
# source/rag/domain/models/business/enterprise_kb/entry_model.py
"""企业知识库业务条目（ai_rag_ent_kb_entry）。"""
from __future__ import annotations
from sqlalchemy import Column, Index, String
from .._base import RagEntryBase


class EnterpriseKbEntry(RagEntryBase):
    __tablename__ = "ai_rag_ent_kb_entry"
    department = Column(String(64))
    confidentiality = Column(String(16))
    __table_args__ = (
        Index("idx_ent_kb_entry_space_status", "space_id", "status", "deleted"),
    )


__all__ = ["EnterpriseKbEntry"]
```

```python
# source/rag/domain/models/business/enterprise_kb/chunk_model.py
"""企业知识库业务片段（ai_rag_ent_kb_chunk）。"""
from __future__ import annotations
from sqlalchemy import Column, Index, String, TIMESTAMP
from .._base import RagChunkBase


class EnterpriseKbChunk(RagChunkBase):
    __tablename__ = "ai_rag_ent_kb_chunk"
    category = Column(String(64))
    effective_date = Column(TIMESTAMP(timezone=True))
    doc_version = Column(String(32))
    __table_args__ = (
        Index("idx_ent_kb_chunk_space_version", "space_id", "embedding_version"),
        Index("idx_ent_kb_chunk_entry", "entry_id"),
    )


__all__ = ["EnterpriseKbChunk"]
```

```python
# source/rag/domain/models/business/enterprise_kb/__init__.py
from .entry_model import EnterpriseKbEntry
from .chunk_model import EnterpriseKbChunk
__all__ = ["EnterpriseKbEntry", "EnterpriseKbChunk"]
```

```python
# source/rag/domain/models/business/_registry.py
"""business_type → (EntryModel, ChunkModel) 路由注册表。"""
from __future__ import annotations

from .financial_report import FinancialReportEntry, FinancialReportChunk
from .enterprise_kb import EnterpriseKbEntry, EnterpriseKbChunk

BUSINESS_REGISTRY = {
    "financial_report": (FinancialReportEntry, FinancialReportChunk),
    "enterprise_kb": (EnterpriseKbEntry, EnterpriseKbChunk),
}


def get_business_models(business_type: str):
    """按 business_type 取 (EntryModel, ChunkModel)；未知类型抛 KeyError。"""
    if business_type not in BUSINESS_REGISTRY:
        raise KeyError(f"unknown business_type: {business_type}")
    return BUSINESS_REGISTRY[business_type]


__all__ = ["BUSINESS_REGISTRY", "get_business_models"]
```

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_business_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/business/ tests/rag/test_business_models.py
git commit -m "feat(rag): add financial_report & enterprise_kb business models + registry"
```

---

## Task 9: 重写 domain/models/__init__.py（统一 re-export）

**Files:**
- Modify: `source/rag/domain/models/__init__.py`
- Delete: 旧顶层 `space_model.py / storage_connection_model.py / chunk_model.py / entry_model.py / _common.py`
- Test: `tests/rag/test_models_exports.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/rag/test_models_exports.py
def test_package_exports():
    from rag.domain.models import (
        RagSpace, RagStorageConnection, RagSpaceBinding, RagConnectionBinding,
        RagIngestionTask, RagMigrationTask, RagSearchLog, RagOperationLog,
        RagEntryBase, RagChunkBase, BUSINESS_REGISTRY,
    )
    assert RagSpace.__tablename__ == "ai_rag_space"
    assert "financial_report" in BUSINESS_REGISTRY
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/rag/test_models_exports.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# source/rag/domain/models/__init__.py
"""RAG 领域 ORM 统一导出（platform / ops / business 三层）。

import 本包即把所有实体注册到共享 Base.metadata（db_bootstrap 依赖）。
"""
from .platform.space_model import RagSpace
from .platform.storage_connection_model import RagStorageConnection
from .platform.space_binding_model import RagSpaceBinding
from .platform.connection_binding_model import RagConnectionBinding

from .ops.ingestion_task_model import RagIngestionTask
from .ops.migration_task_model import RagMigrationTask
from .ops.search_log_model import RagSearchLog
from .ops.operation_log_model import RagOperationLog

from .business._base import RagEntryBase, RagChunkBase
from .business._registry import BUSINESS_REGISTRY, get_business_models

__all__ = [
    "RagSpace", "RagStorageConnection", "RagSpaceBinding", "RagConnectionBinding",
    "RagIngestionTask", "RagMigrationTask", "RagSearchLog", "RagOperationLog",
    "RagEntryBase", "RagChunkBase", "BUSINESS_REGISTRY", "get_business_models",
]
```

删除旧顶层文件：
```bash
git rm source/rag/domain/models/space_model.py source/rag/domain/models/storage_connection_model.py source/rag/domain/models/chunk_model.py source/rag/domain/models/entry_model.py source/rag/domain/models/_common.py
```

> 旧 `RagChunk` / `RagEntry`（通用单表）被业务表取代，引用它们的代码在 Task 11-12 适配。

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_models_exports.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/models/__init__.py
git commit -m "refactor(rag): rewrite models package exports for 3-layer structure"
```

---

## Task 10: Migration SQL（改写 space/connection + 新增 binding/business）

**Files:**
- Modify: `sql/migrations/2026-05-27_rag_003_*space*.{up,down}.sql`
- Modify: `sql/migrations/2026-05-29_rag_009_*connection*.{up,down}.sql`
- Create: `sql/migrations/2026-06-04_rag_010_create_bindings.{up,down}.sql`
- Create: `sql/migrations/2026-06-04_rag_011_create_business_tables.{up,down}.sql`

- [ ] **Step 1: 读现状**

Run: `ls sql/migrations/`，Read rag_003 / rag_009 的 up/down，确认确切文件名与列定义。

- [ ] **Step 2: 改写 rag_003（space）**

在 `ai_rag_space` 的 `CREATE TABLE` 中删除列 `company_id, owner_type, owner_user_id, created_by, updated_by`，删除 `chk_rag_space_owner` 及唯一/可见性索引（`uk_rag_space_company_name`、`uk_rag_space_personal_name`、`idx_ai_rag_space_company_owner`、`idx_ai_rag_space_personal_owner`）。新增列与索引：
```sql
business_type VARCHAR(32) NOT NULL,         -- 加在 CREATE TABLE 列定义中
-- 索引：
CREATE INDEX idx_ai_rag_space_business_type ON ai_rag_space (business_type, deleted);
```
（未上线，直接把 CREATE TABLE 整理成最终形态。）

- [ ] **Step 3: 改写 rag_009（connection）**

从 `ai_rag_storage_connection` 删除 `company_id, created_by` 列，删除索引 `uk_rag_conn_company_code` 与 `idx_ai_rag_conn_company`。保留 `code`（唯一性由 service 保证）。

- [ ] **Step 4: 新增 rag_010 binding 表**

```sql
-- 2026-06-04_rag_010_create_bindings.up.sql
CREATE TABLE ai_rag_space_binding (
    id            VARCHAR(36) PRIMARY KEY,
    space_id      VARCHAR(36) NOT NULL REFERENCES ai_rag_space(id) ON DELETE CASCADE,
    company_id    VARCHAR(36) NOT NULL,
    owner_type    VARCHAR(16) NOT NULL,
    owner_user_id VARCHAR(36),
    created_by    VARCHAR(36) NOT NULL,
    updated_by    VARCHAR(36),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_rag_space_binding_owner CHECK (
        (owner_type = 'COMPANY' AND owner_user_id IS NULL) OR
        (owner_type = 'PERSONAL' AND owner_user_id IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uk_rag_space_binding_space ON ai_rag_space_binding (space_id);
CREATE INDEX idx_rag_space_binding_company ON ai_rag_space_binding (company_id, owner_type, owner_user_id);

CREATE TABLE ai_rag_connection_binding (
    id            VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL REFERENCES ai_rag_storage_connection(id) ON DELETE CASCADE,
    company_id    VARCHAR(36) NOT NULL,
    created_by    VARCHAR(36) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uk_rag_conn_binding_conn ON ai_rag_connection_binding (connection_id);
CREATE INDEX idx_rag_conn_binding_company ON ai_rag_connection_binding (company_id);
```
```sql
-- down: DROP TABLE ai_rag_connection_binding; DROP TABLE ai_rag_space_binding;
```

- [ ] **Step 5: 新增 rag_011 业务表**

```sql
-- 2026-06-04_rag_011_create_business_tables.up.sql
CREATE TABLE ai_rag_fin_report_entry (
    id VARCHAR(36) PRIMARY KEY, space_id VARCHAR(36) NOT NULL, company_id VARCHAR(36) NOT NULL,
    source_type VARCHAR(16) NOT NULL, file_id VARCHAR(36), title VARCHAR(512) NOT NULL,
    content_text TEXT, mime_type VARCHAR(128), file_size_bytes BIGINT,
    chunk_size_used INT NOT NULL, chunk_overlap_used INT NOT NULL, embedding_version INT NOT NULL,
    chunk_count INT NOT NULL DEFAULT 0, total_tokens BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'PROCESSING', processing_stage VARCHAR(32), error_message TEXT,
    hit_count BIGINT NOT NULL DEFAULT 0, deleted BOOLEAN NOT NULL DEFAULT FALSE, deleted_at TIMESTAMPTZ,
    created_by VARCHAR(36) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    report_period VARCHAR(32), source_company_id VARCHAR(36)
);
CREATE INDEX idx_fin_report_entry_space_status ON ai_rag_fin_report_entry (space_id, status, deleted);

CREATE TABLE ai_rag_fin_report_chunk (
    id VARCHAR(36) PRIMARY KEY, space_id VARCHAR(36) NOT NULL, company_id VARCHAR(36) NOT NULL,
    entry_id VARCHAR(36) NOT NULL, embedding_version INT NOT NULL, seq INT NOT NULL,
    content TEXT NOT NULL, content_tokens INT NOT NULL, embedding vector(1536) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}', hit_count BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    fiscal_year INT, company_ref VARCHAR(36), statement_type VARCHAR(32)
);
CREATE INDEX idx_fin_report_chunk_space_version ON ai_rag_fin_report_chunk (space_id, embedding_version);
CREATE INDEX idx_fin_report_chunk_entry ON ai_rag_fin_report_chunk (entry_id);
CREATE INDEX idx_fin_report_chunk_hnsw ON ai_rag_fin_report_chunk USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_fin_report_chunk_trgm ON ai_rag_fin_report_chunk USING gin (content gin_trgm_ops);

-- enterprise_kb 同构：ai_rag_ent_kb_entry / ai_rag_ent_kb_chunk
--   entry 特有列: department VARCHAR(64), confidentiality VARCHAR(16)
--   chunk 特有列: category VARCHAR(64), effective_date TIMESTAMPTZ, doc_version VARCHAR(32)
--   索引名前缀 ent_kb_*，HNSW/trgm 同上
```
```sql
-- down: DROP 四张业务表
```

- [ ] **Step 6: Commit**

```bash
git add sql/migrations/
git commit -m "feat(rag): migration for layered space/connection + bindings + business tables"
```

---

## Task 11: db_bootstrap 注册新表

**Files:**
- Modify: `source/rag/infrastructure/db_bootstrap.py`
- Test: `tests/rag/test_bootstrap_create_all.py`（testcontainers）

- [ ] **Step 1: 读现状**

Read `source/rag/infrastructure/db_bootstrap.py`，确认它如何 import models 触发注册、如何调用 `Base.metadata.create_all`。

- [ ] **Step 2: 写集成测试**

```python
# tests/rag/test_bootstrap_create_all.py
import pytest
import sqlalchemy

@pytest.mark.integration
def test_create_all_builds_all_rag_tables(pg_engine):  # pg_engine: testcontainers fixture（已 CREATE EXTENSION）
    from lg.db.models.models import Base
    import rag.domain.models  # noqa: F401  触发注册
    Base.metadata.create_all(pg_engine, checkfirst=True)
    tables = set(sqlalchemy.inspect(pg_engine).get_table_names())
    assert {
        "ai_rag_space", "ai_rag_storage_connection",
        "ai_rag_space_binding", "ai_rag_connection_binding",
        "ai_rag_fin_report_chunk", "ai_rag_ent_kb_chunk",
        "ai_rag_ingestion_task", "ai_rag_search_log",
    } <= tables
```

- [ ] **Step 3: 运行确认失败**

Run: `pytest tests/rag/test_bootstrap_create_all.py -v -m integration`
Expected: FAIL

- [ ] **Step 4: 适配 bootstrap**

确保 `import rag.domain.models` 注册 platform + ops + business 全部实体。若 bootstrap 内有显式旧路径 import（如 `from rag.domain.models.chunk_model import ...`），改为统一 `import rag.domain.models`。

- [ ] **Step 5: 运行确认通过**

Run: `pytest tests/rag/test_bootstrap_create_all.py -v -m integration`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add source/rag/infrastructure/db_bootstrap.py tests/rag/test_bootstrap_create_all.py
git commit -m "feat(rag): register layered models in db_bootstrap + integration test"
```

---

## Task 12: Repository 适配（space / connection / 业务路由 chunk·entry）

**Files:**
- Modify: `source/rag/domain/repository/{space,connection,chunk,entry}_repository.py`
- Test: `tests/rag/test_repository_routing.py`

- [ ] **Step 1: 读现状**

Read 4 个 repository，定位：① space/connection 查询里 `WHERE company_id`；② chunk/entry 对旧 `RagChunk`/`RagEntry` 的直接引用。

- [ ] **Step 2: 适配规则（逐文件）**

- `space_repository`：可见性查询不再过滤 `RagSpace.company_id`，改为 **JOIN `RagSpaceBinding`** 过滤 `company_id`/`owner_type`/`owner_user_id`；`create` 不写 space 业务列。
- `connection_repository`：查询 JOIN `RagConnectionBinding` 过滤 `company_id`；`get_by_code` 用 `code` + JOIN binding company。
- `chunk_repository`/`entry_repository`：方法新增 `entry_cls`/`chunk_cls` 参数（service 按 business_type 注入），把硬编码 `RagChunk`/`RagEntry` 替换为传入类。向量检索保持 `WHERE chunk_cls.space_id == ? AND chunk_cls.company_id == ? AND chunk_cls.embedding_version == ?` 命中 HNSW。

- [ ] **Step 3: 写测试（路由 + 隔离）**

```python
# tests/rag/test_repository_routing.py
import pytest

@pytest.mark.integration
def test_chunk_repo_routes_by_business_model(db_session):
    from rag.domain.models.business._registry import get_business_models
    from rag.domain.repository.chunk_repository import ChunkRepository
    _, chunk_cls = get_business_models("financial_report")
    repo = ChunkRepository(db_session)
    # 插入一条 1536 维向量 + space_id/company_id，断言单表向量检索能查回该 chunk
    ...
```

- [ ] **Step 4: 运行 + 实现至通过**

Run: `pytest tests/rag/test_repository_routing.py -v -m integration`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/domain/repository/ tests/rag/test_repository_routing.py
git commit -m "refactor(rag): repositories join binding + route chunk/entry by business_type"
```

---

## Task 13: Service 适配（写 binding + 可见性 + 业务路由）

**Files:**
- Modify: `source/rag/application/service/{space,connection,search,ingest}_service.py`
- Test: `tests/rag/test_space_service_binding.py`

- [ ] **Step 1: 读现状**

Read 4 个 service，定位 `create_space`/`create_connection` 当前如何写 company/owner、可见性如何过滤、搜索/入库如何取 chunk 模型。

- [ ] **Step 2: 适配规则**

- `space_service.create_space`：同一事务先 `INSERT RagSpace`（含 `business_type`），再 `INSERT RagSpaceBinding`（company/owner/created_by）。`business_type` 必须命中 `BUSINESS_REGISTRY`，否则抛业务错误。
- `space_service` 可见性/列表/`_to_dto`：经 binding 过滤与取 owner/company。
- `connection_service.create_connection`：`INSERT RagStorageConnection` + `INSERT RagConnectionBinding`；`code` 唯一性按 `company_id`（经 binding）在 service 校验。
- `search_service`/`ingest_service`：取 `space.business_type` → `get_business_models()` → 把 `entry_cls/chunk_cls` 传给 repository。

- [ ] **Step 3: 写测试**

```python
# tests/rag/test_space_service_binding.py
import pytest

@pytest.mark.integration
def test_create_space_writes_binding(db_session):
    from rag.application.service.space_service import SpaceService
    from rag.application.dto.space_dto import SpaceCreateDTO
    svc = SpaceService(db_session)
    dto = SpaceCreateDTO(name="t", business_type="financial_report",
                         owner_type="COMPANY", embedding_model="text-embedding-3-small",
                         storage_backend="pg", storage_config_mode="default")
    out = svc.create_space(dto, company_id="c1", user_id="u1", is_admin=True)
    from rag.domain.models import RagSpaceBinding
    b = db_session.query(RagSpaceBinding).filter_by(space_id=out.id).one()
    assert b.company_id == "c1" and b.created_by == "u1"

@pytest.mark.integration
def test_create_space_rejects_unknown_business_type(db_session):
    from rag.application.service.space_service import SpaceService
    from rag.application.dto.space_dto import SpaceCreateDTO
    svc = SpaceService(db_session)
    dto = SpaceCreateDTO(name="t", business_type="NOPE", owner_type="COMPANY",
                         embedding_model="text-embedding-3-small",
                         storage_backend="pg", storage_config_mode="default")
    with pytest.raises(Exception):
        svc.create_space(dto, company_id="c1", user_id="u1", is_admin=True)
```

> `SpaceCreateDTO` 需新增 `business_type`（Task 14 同步改 DTO）。

- [ ] **Step 4: 运行 + 实现至通过**

Run: `pytest tests/rag/test_space_service_binding.py -v -m integration`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/application/service/ tests/rag/test_space_service_binding.py
git commit -m "refactor(rag): services write bindings, route business_type, validate registry"
```

---

## Task 14: DTO 适配 + infra 适配

**Files:**
- Modify: `source/rag/application/dto/{space,connection}_dto.py`
- Modify: `source/rag/infrastructure/storage/{connection_resolver,factory}.py`
- Test: `tests/rag/test_dto_fields.py`

- [ ] **Step 1: 读现状**

Read 两个 DTO 与 connection_resolver / factory，确认字段与 import。

- [ ] **Step 2: 写测试**

```python
# tests/rag/test_dto_fields.py
def test_space_create_dto_has_business_type():
    import dataclasses
    from rag.application.dto.space_dto import SpaceCreateDTO
    fields = {f.name for f in dataclasses.fields(SpaceCreateDTO)}
    assert "business_type" in fields
```

- [ ] **Step 3: 适配实现**

- `SpaceCreateDTO`/`SpaceDTO` 增加 `business_type`；`SpaceDTO` 的 `owner_type/owner_user_id/created_by` 由 service `_to_dto` 从 binding 填。
- `ConnectionDTO`：`company_id/created_by` 由 service `_to_dto` 从 binding 取。
- `connection_resolver`：`default` 模式走 env（不变）；`custom` 模式按 `connection_ref` 解析 `RagStorageConnection` 解密凭据（不再依赖 connection.company_id）。
- `factory`：确认 `from rag.domain.models import RagSpace` 等 import 仍有效。

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/rag/test_dto_fields.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add source/rag/application/dto/ source/rag/infrastructure/storage/ tests/rag/test_dto_fields.py
git commit -m "refactor(rag): DTO business_type + binding-sourced ownership; resolver two modes"
```

---

## Task 15: 端到端冒烟 + 全量回归 + 规范自查

**Files:**
- Test: `tests/rag/test_smoke_layering.py`

- [ ] **Step 1: 写冒烟测试**

```python
# tests/rag/test_smoke_layering.py
import pytest

@pytest.mark.integration
def test_end_to_end_space_ingest_search_recall(db_session):
    """建空间(financial_report) → 写 binding → 插一条 entry+chunk → 检索 → 片段含 hit_count，SearchLog 落一条。"""
    # 1) create_space(business_type=financial_report)
    # 2) 断言 RagSpaceBinding 存在
    # 3) 插入 FinancialReportEntry + FinancialReportChunk(1536维)
    # 4) search_service 向量检索命中该 chunk
    # 5) 断言返回片段含 hit_count；检索后 SearchLog 落一条
    ...
```

- [ ] **Step 2: 运行全量**

Run: `cd CIOaas-python && pytest tests/rag/ -v`
Expected: 全绿

- [ ] **Step 3: 规范自查（项目强制）**

按 `CIOaas-python/standards/{architecture,coding}.md` 审查四层边界、repository 单表/JOIN binding、service 只吃吐 DTO、类型注解齐全，修正不符项。

- [ ] **Step 4: Commit**

```bash
git add tests/rag/test_smoke_layering.py
git commit -m "test(rag): end-to-end smoke for layered space/ingest/search/recall"
```

---

## Self-Review 结果

- **Spec 覆盖**：platform 瘦身(T2/T3)、binding(T4/T5)、ops 保留(T6)、业务基类+召回字段(T7)、两业务+注册表(T8)、导出(T9)、migration(T10)、bootstrap(T11)、repo/service/dto/infra 适配(T12-14)、端到端(T15) —— 设计 §1-§7 全覆盖。
- **占位扫描**：适配类 Task（12/13/14）含「读现状」首步 + 明确改写规则 + 关键测试代码；因这些文件源码需执行时读取，给的是规则+锚点而非整文件重写（避免基于未读源码编造）。
- **类型一致**：`get_business_models` / `BUSINESS_REGISTRY` / 表名 / 列名跨任务一致。

## 待执行者注意
- 业务特有字段（§5.2/5.3）为示例，若已有真实字段定义，先替换 Task 8 / Task 10 对应列再执行。
- testcontainers fixture 需在建表前 `CREATE EXTENSION vector; CREATE EXTENSION pg_trgm;`（见现有 `tests/rag/test_storage.py` 约定）。
