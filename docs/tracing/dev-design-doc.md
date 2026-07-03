# 链路追踪（Tracing）独立业务模块 — 开发设计文档（dev-design-doc）

> 状态：正式开发设计（由 `/team-design` Architect 团队基于「链路追踪独立模块-方案构想.md」细化）
> 范围：CIOaas-python `source/tracing/`（DDD 四层）+ CIOaas-web `pages/ai/tracing/`
> 红线（不可违背，来自方案构想）：
> 1. 全新独立模块 `source/tracing/`，**绝不修改 / 复用** llm 的存储与页面；llm 代码零改动
> 2. 与 llm 仅靠共享 `trace_id` 值做软关联
> 3. 本期仅 Python 进程内；跨进程（Java 网关）预留不实现
> 4. 埋点低侵入 + 异步写零阻塞业务
> 强制遵循：`CIOaas-python/standards/architecture.md`（§1.1 / §1.3 / §1.4 / §1.5 / §2.1 / §2.2）、`standards/coding.md`

---

## 0. 设计前置确认（与现有实现对齐的关键事实）

读取并核对了以下现有实现，本设计严格沿用其风格：

| 参考 | 借鉴点 | 本设计落点 |
|---|---|---|
| `llm/infrastructure/tracing/context.py` | `@dataclass(frozen=True)` ctx + `ContextVar` + `@contextmanager` scope；`copy_context` 跨线程说明 | `tracing/infrastructure/trace_context.py`（**独立 ContextVar**，与 llm 隔离） |
| `llm/infrastructure/tracing/writer.py` | fire-and-forget `schedule_*` + `_MAX_INFLIGHT` 上限 + `shutdown_pending_writes` | `tracing/infrastructure/async_writer.py`（独立实现；依赖倒置：infra 只调度无参回调） |
| `llm/application/service/tracking_query_service.py` | 函数式 query service + `get_session()` + `_fmt_dt` UTC 格式 + ORM/Row→DTO | `tracing/application/service/trace_query_service.py` |
| `llm/application/router/tracked.py` | `begin/finish` 两段式写 + `schedule_persist_call(lambda: ...)` 注入回调 | `tracing/application/service/trace_record_service.py`（`begin_trace`/`finish_trace`/`record_span`） |
| `llm/interfaces/routes.py` | 开关式 Bearer Token（`secrets.compare_digest`）+ `{success,code,message,data}` 信封 + lowerCamelCase + 路由声明顺序（静态前缀先于通配） | `tracing/interfaces/routes.py` |
| `rag/domain/models/space_model.py` + `_common.py` | 复用 `lg.db.models.models` 的 `Base` + `_now`；`String(36)` UUID PK；`__table_args__` 内声明 `Index` / `CheckConstraint`；软删 `deleted`/`deleted_at` | `tracing/domain/models/trace_model.py` / `span_model.py` |
| `rag/domain/models/__init__.py` + `repository/__init__.py` | 包 `__init__` 统一 re-export，保证实体 import 即注册到 `Base.metadata` | tracing 同款 re-export |
| `rag/infrastructure/db_bootstrap.py` | `create_all(checkfirst=True)` 幂等建表 + 优雅降级 | `tracing/infrastructure/db_bootstrap.py` |
| `consumer/handlers.py` | graph 入口 `trace_id_scope(uuid.uuid4().hex)`（单一 trace_id 来源） | trace_id 一致性方案锚点（§8） |
| `cioaas_mcp/tools_registry.py` `execute_tool` + 第 12 行 TODO | MCP 埋点接入点 | §7.2 MCP 切面 |
| `main.py` | `app.include_router` 挂载 + `combined_lifespan` 嵌套 | §7.3 中间件集成 + §11 bootstrap 集成 |

**关键约束确认**：
- `Base` / `_now` 一律从 `lg.db.models.models` 复用（与 rag `_common.py` 完全一致），保证 `ai_trace` / `ai_trace_span` 注册到同一 metadata，`create_all` 与业务表同引擎建出。
- UUID 主键 Python 端生成（`str(uuid.uuid4())`），与所有 AI 表风格一致。
- 响应信封 `{success, code, message, data}`、空列表 `[]`、Long→String、时间 `"yyyy-MM-dd HH:mm:ss"`（UTC）。
- tracing **零 LLM SDK 依赖**（ruff TID251 天然满足，因为 tracing 不 `import openai/anthropic/langchain`，也不 import `llm.router`）。

---

## 1. 目录结构（`source/tracing/`，遵循 architecture.md §1.1 语义化命名 + 数量伸缩）

```
source/tracing/
├── __init__.py                              # 顶层 re-export：start_trace / start_span / traced_span / TraceContext
├── interfaces/
│   ├── __init__.py
│   ├── routes.py                            # 单组路由 → 文件（GET /api/ai/traces · /{id} · 预留 POST /spans）
│   └── vo/                                  # 入参/出参多 → 文件夹
│       ├── __init__.py
│       ├── request.py                       #   TraceQueryRequest（Query 解析）/ SpanReportRequest（预留）
│       └── response.py                      #   TraceItem / TraceListResponse / TraceDetailResponse / SpanNode ...
├── application/
│   ├── __init__.py                          # re-export 跨模块对外契约：record service 函数 + DTO
│   ├── service/                             # 两个 service → 文件夹（§1.1）
│   │   ├── __init__.py                      #   re-export begin_trace/finish_trace/record_span + query 函数
│   │   ├── trace_record_service.py          #   写编排：begin_trace / finish_trace / record_span（注入 async_writer 回调）
│   │   └── trace_query_service.py           #   读编排：list_traces / get_trace_detail（trace + span 树）
│   └── dto/                                 # 两个 DTO → 文件夹
│       ├── __init__.py                      #   re-export TraceDTO / SpanDTO / TraceListFilters / TraceWriteDTO / SpanWriteDTO
│       ├── trace_dto.py                     #   TraceDTO / TraceWriteDTO / TraceFinishDTO / TraceListFilters
│       └── span_dto.py                      #   SpanDTO / SpanWriteDTO
├── domain/
│   ├── __init__.py                          # re-export Trace / TraceSpan（保证 import 即注册到 Base.metadata）
│   ├── models/                              # 两个实体 → 文件夹
│   │   ├── __init__.py                      #   from .trace_model import Trace; from .span_model import TraceSpan
│   │   ├── _common.py                       #   复用 lg.db.models.models 的 Base + _now + _new_uuid（仿 rag _common.py）
│   │   ├── trace_model.py                   #   class Trace → ai_trace
│   │   └── span_model.py                    #   class TraceSpan → ai_trace_span
│   ├── enums.py                             # TraceStatus / SpanStatus / SpanType / TraceSource（单文件，值集合）
│   └── repository/                          # 两个 repository → 文件夹
│       ├── __init__.py                      #   from .trace_repository import TraceRepository; ...
│       ├── trace_repository.py             #   class TraceRepository（单表 ai_trace CRUD + 列表查询/分页）
│       └── span_repository.py              #   class SpanRepository（单表 ai_trace_span CRUD + by_trace 查询）
└── infrastructure/
    ├── __init__.py                          # re-export 采集 SDK + async_writer + db_bootstrap 公开符号
    ├── trace_context.py                     # 采集 SDK 核心：独立 ContextVar + start_trace/start_span/traced_span
    ├── async_writer.py                      # fire-and-forget 调度 + 上限保护 + flush（依赖倒置，独立实现）
    └── db_bootstrap.py                      # setup_tracing_tables()：create_all(checkfirst=True) 建两表 + 索引
```

**文件命名合规说明**：
- `interfaces/routes.py` 单组路由 → 文件（§1.1 表）；`vo/` 升级文件夹用语义名 `request.py` / `response.py`（§1.1 vo 例外）。
- `application/service/`、`application/dto/` 各有 2 个文件 → 文件夹，文件名带功能前缀（`trace_record_service.py` 而非 `service.py`）。
- `domain/models/` 有 2 个实体 → 文件夹，文件名 `_model` 单数后缀（`trace_model.py` / `span_model.py`）。
- `domain/enums.py` 单文件（§1.1 enums 例外，不带前缀）。
- `domain/repository/` 有 2 个 → 文件夹，`_repository` 单数后缀。
- **无 `domain/service`**（§1.3 强制：领域逻辑全在 `application/service`）。
- `infrastructure/` 3 个功能文件平铺（`trace_context` / `async_writer` / `db_bootstrap` 各一），均带语义名。

**跨模块边界（§2.1）**：tracing 对外只暴露 `application/service` + `application/dto`。业务模块埋点时 import 的是 `infrastructure` 的采集 SDK——这是 tracing 自身定位为「横切平台」的一部分（同 §2.1.1 llm 豁免精神：统一运行时入口）。为收口，**采集 SDK 由 `tracing/__init__.py` 顶层 re-export**，业务侧统一写 `from tracing import start_trace, start_span, traced_span`，不直连深层 `tracing.infrastructure.trace_context`。

---

## 2. 数据模型

### 2.1 `ai_trace`（一条业务链路）— SQLAlchemy 模型

文件：`source/tracing/domain/models/trace_model.py`

```python
"""链路追踪 trace ORM 实体（ai_trace）：一条端到端业务链路的根记录。

复用 lg.db.models.models 的 Base + _now（仿 rag space_model.py），供
create_all(checkfirst=True) 在新环境与业务表同引擎建出；DDL 权威来源是
sql/migrations 下的 tracing migration。
"""
from __future__ import annotations

from sqlalchemy import Column, Index, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

from ._common import Base, _new_uuid, _now


class Trace(Base):
    """一条业务链路（SQS / HTTP / cron / MCP 入口 → 多个 span 节点的根容器）。"""

    __tablename__ = "ai_trace"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    """trace_id（业务入口单一来源生成，跨节点 / 跨模块串联；预留外部注入）"""

    name = Column(String(128), nullable=False)
    """链路名 / 业务类型：financial_extract / rag_ingest / mcp_tool / http_request 等"""

    source = Column(String(16), nullable=False)
    """入口来源（TraceSource 枚举）：sqs / http / cron / mcp / manual"""

    status = Column(String(16), nullable=False, default="RUNNING")
    """链路状态（TraceStatus）：RUNNING / SUCCESS / FAILED / PARTIAL"""

    company_id = Column(String(36))
    """多租户归属公司 ID（所有列表查询强制过滤；入口无 company 时可空）"""

    user_id = Column(String(36))
    """业务归属用户 ID（可空）"""

    task_id = Column(String(36))
    """软关联 ExtractionTask.id / 业务任务 ID（无 FK，可空）"""

    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    """链路开始时间（UTC）"""

    finished_at = Column(TIMESTAMP(timezone=True))
    """链路结束时间（RUNNING 时为 NULL；with 退出 / finish_trace 时补）"""

    duration_ms = Column(Integer)
    """链路总耗时毫秒（finished_at - started_at；RUNNING 时 NULL）"""

    attributes = Column(JSONB, nullable=False, default=dict)
    """开放扩展（入口参数摘要 / batch_number / file_count 等；只存摘要不存敏感全文）"""

    error = Column(String(2000))
    """链路级失败摘要（status=FAILED 时填；截断 2000 字符防膨胀）"""

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    """记录创建时间（UTC）"""

    # 索引与 migration 保持一致，供 create_all(checkfirst=True) 建出。
    __table_args__ = (
        Index("idx_ai_trace_company_started", "company_id", "started_at"),
        Index("idx_ai_trace_status_started", "status", "started_at"),
        Index("idx_ai_trace_task", "task_id"),
        Index("idx_ai_trace_name_started", "name", "started_at"),
    )


__all__ = ["Trace"]
```

> 设计说明：
> - `company_id` 可空（HTTP / cron 入口可能无租户），但**列表查询传 company_id 时强制过滤**（§6）。索引 `(company_id, started_at)` 为多租户分页主路径（按时间倒序由 query 层 `ORDER BY started_at DESC` 表达，PG B-tree 双向可用）。
> - `attributes` 用 `JSONB`、`default=dict`（与 rag `vector_index_params` 同款），存入口参数摘要。
> - 不放 `updated_at`：trace 生命周期是 begin→finish 两次写，用 `finished_at` 表达终态时间，无需通用 `updated_at`。

### 2.2 `ai_trace_span`（链路节点，父子树）— SQLAlchemy 模型

文件：`source/tracing/domain/models/span_model.py`

```python
"""链路 span ORM 实体（ai_trace_span）：一条链路上的节点，parent_span_id 构成调用树。"""
from __future__ import annotations

from sqlalchemy import Column, Index, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

from ._common import Base, _new_uuid, _now


class TraceSpan(Base):
    """链路节点：graph_node / llm_call / rag_op / mcp_tool / db / external。"""

    __tablename__ = "ai_trace_span"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    """span_id（Python 端生成）"""

    trace_id = Column(String(36), nullable=False)
    """所属链路 ai_trace.id（软关联，应用层保证一致；不声明跨表 FK 以与 rag 跨库风格兼容）"""

    parent_span_id = Column(String(36))
    """父 span id（构成调用树；根 span 为 NULL）"""

    name = Column(String(128), nullable=False)
    """span 名：identify_fs / extract_cells / llm_identify / rag_ingest / process_excel 等"""

    span_type = Column(String(16), nullable=False)
    """节点类型（SpanType）：graph_node / llm_call / rag_op / mcp_tool / db / external / http"""

    status = Column(String(16), nullable=False, default="RUNNING")
    """span 状态（SpanStatus）：RUNNING / SUCCESS / FAILED"""

    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    """span 开始时间（UTC，瀑布图起点）"""

    finished_at = Column(TIMESTAMP(timezone=True))
    """span 结束时间（RUNNING 时 NULL）"""

    duration_ms = Column(Integer)
    """span 耗时毫秒（瀑布图条长）"""

    attributes = Column(JSONB, nullable=False, default=dict)
    """节点上下文摘要：llm_call 存 {provider, model, tokens, costUsd, call_log_id}；
    rag_op 存 {space_id, top_k, hit_count}；mcp_tool 存 {tool_name, arg_summary}。只存摘要。"""

    error = Column(Text)
    """失败原因（status=FAILED 时填异常类型 + 消息，截断由写编排控制）"""

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    """记录创建时间（UTC）"""

    __table_args__ = (
        Index("idx_ai_trace_span_trace_started", "trace_id", "started_at"),
        Index("idx_ai_trace_span_parent", "parent_span_id"),
        Index("idx_ai_trace_span_type", "span_type"),
    )


__all__ = ["TraceSpan"]
```

### 2.3 `domain/models/_common.py`（仿 rag）

```python
"""tracing 领域 ORM 共享基建：复用 lg.db.models.models 的 Base + _now + UUID 主键。"""
from __future__ import annotations

import uuid

from lg.db.models.models import Base, _now  # 复用同一 DeclarativeBase metadata（与 rag 一致）


def _new_uuid() -> str:
    return str(uuid.uuid4())


__all__ = ["Base", "_now", "_new_uuid"]
```

### 2.4 枚举（`domain/enums.py`）

```python
"""tracing 领域枚举（值集合，单文件——§1.1 enums 例外）。"""
from __future__ import annotations

from enum import StrEnum


class TraceStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"   # 部分 span 失败但链路整体完成


class SpanStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class SpanType(StrEnum):
    GRAPH_NODE = "graph_node"
    LLM_CALL = "llm_call"
    RAG_OP = "rag_op"
    MCP_TOOL = "mcp_tool"
    DB = "db"
    HTTP = "http"
    EXTERNAL = "external"


class TraceSource(StrEnum):
    SQS = "sqs"
    HTTP = "http"
    CRON = "cron"
    MCP = "mcp"
    MANUAL = "manual"
```

### 2.5 Migration SQL DDL

文件：`CIOaas-python/sql/migrations/2026-06-03_tracing_001_create_ai_trace.up.sql`

```sql
-- tracing_001: ai_trace（业务链路根表）
CREATE TABLE IF NOT EXISTS ai_trace (
    id            VARCHAR(36)  PRIMARY KEY,
    name          VARCHAR(128) NOT NULL,
    source        VARCHAR(16)  NOT NULL,
    status        VARCHAR(16)  NOT NULL DEFAULT 'RUNNING',
    company_id    VARCHAR(36),
    user_id       VARCHAR(36),
    task_id       VARCHAR(36),
    started_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMP WITH TIME ZONE,
    duration_ms   INTEGER,
    attributes    JSONB        NOT NULL DEFAULT '{}'::jsonb,
    error         VARCHAR(2000),
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_trace_company_started ON ai_trace (company_id, started_at);
CREATE INDEX IF NOT EXISTS idx_ai_trace_status_started  ON ai_trace (status, started_at);
CREATE INDEX IF NOT EXISTS idx_ai_trace_task            ON ai_trace (task_id);
CREATE INDEX IF NOT EXISTS idx_ai_trace_name_started    ON ai_trace (name, started_at);
```

文件：`CIOaas-python/sql/migrations/2026-06-03_tracing_002_create_ai_trace_span.up.sql`

```sql
-- tracing_002: ai_trace_span（链路节点，父子树）
CREATE TABLE IF NOT EXISTS ai_trace_span (
    id              VARCHAR(36)  PRIMARY KEY,
    trace_id        VARCHAR(36)  NOT NULL,
    parent_span_id  VARCHAR(36),
    name            VARCHAR(128) NOT NULL,
    span_type       VARCHAR(16)  NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'RUNNING',
    started_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMP WITH TIME ZONE,
    duration_ms     INTEGER,
    attributes      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    error           TEXT,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_trace_span_trace_started ON ai_trace_span (trace_id, started_at);
CREATE INDEX IF NOT EXISTS idx_ai_trace_span_parent        ON ai_trace_span (parent_span_id);
CREATE INDEX IF NOT EXISTS idx_ai_trace_span_type          ON ai_trace_span (span_type);
```

> **不声明跨表 FK**：`ai_trace_span.trace_id → ai_trace.id` 不建数据库级 FK——理由同 rag 跨库设计（span 量大、未来可独立库），一致性由应用层写编排保证（先 begin_trace 拿 trace_id 再 record_span）。30 天清理时先删 span 再删 trace。

---

## 3. 采集 SDK（`infrastructure/trace_context.py`）

**核心职责**：极简埋点入口 + 独立 ContextVar + 自动补时序/状态 + 跨线程透传 helper。**与 llm 的 ContextVar 完全隔离**（不同变量名、不同模块）。

### 3.1 ContextVar 设计

```python
from contextvars import ContextVar

# trace_id：整条链路唯一标识（一次入口设置一次，覆盖整条链路）
_current_trace_id: ContextVar[Optional[str]] = ContextVar("tracing_trace_id", default=None)

# span 栈：当前活跃的 span_id 栈（栈顶 = 当前父 span）。用 tuple（不可变）逐层 push/pop。
_current_span_stack: ContextVar[tuple[str, ...]] = ContextVar("tracing_span_stack", default=())
```

> 与 llm 的 `_current_trace` / `_current_trace_id`（`llm_trace` / `llm_trace_id`）命名不同，互不干扰。tracing 用 **span 栈**（llm 没有），因为 tracing 要构造 parent-child 树，llm 只需平铺 trace_id。

### 3.2 核心 API 签名

```python
@contextmanager
def start_trace(
    name: str,
    *,
    source: str,                       # TraceSource 值：sqs / http / cron / mcp / manual
    trace_id: Optional[str] = None,    # 外部注入（与 llm 共享同值时传入）；None 则内部生成 uuid4().hex
    company_id: Optional[str] = None,
    user_id: Optional[str] = None,
    task_id: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
) -> Iterator[str]:
    """开启一条链路。yield trace_id（业务可同值喂给 llm.trace_id_scope）。

    行为：
      1. trace_id = trace_id or uuid.uuid4().hex
      2. set _current_trace_id + 清空 span 栈
      3. 异步排队 begin_trace（status=RUNNING, started_at=now）
      4. with 正常退出 → finish_trace(status=SUCCESS, finished_at, duration_ms)
         with 异常退出 → finish_trace(status=FAILED, error=repr(exc))，并 re-raise
      5. finally 恢复 ContextVar token
    """

@contextmanager
def start_span(
    name: str,
    *,
    span_type: str,                    # SpanType 值
    attributes: Optional[dict[str, Any]] = None,
) -> Iterator[str]:
    """在当前链路内开一个 span（自动继承 trace_id + 当前栈顶为 parent）。yield span_id。

    行为：
      1. trace_id = _current_trace_id.get()；若为 None → 安全降级（仅日志 debug，
         不报错、不写库——埋点绝不打断业务），yield 一个临时 span_id 但不落库。
      2. span_id = uuid.uuid4().hex；parent_span_id = 栈顶（无则 None）
      3. push span_id 入栈；异步排队 record_span(begin)（status=RUNNING）
      4. 正常退出 → record_span(finish, status=SUCCESS, finished_at, duration_ms)
         异常退出 → record_span(finish, status=FAILED, error=type+msg)，re-raise
      5. finally pop 栈 + 恢复 token
    """

def current_trace_id() -> Optional[str]:
    """返回当前 ContextVar 中的 trace_id（业务可取出喂给 llm.trace_id_scope）。"""

def current_span_id() -> Optional[str]:
    """返回当前栈顶 span_id（如有）。"""
```

> **时序与状态实现细节**：
> - `start_trace` / `start_span` 内部用 `time.perf_counter()` 记录起点；退出时 `duration_ms = int((perf_counter()-t0)*1000)`，`finished_at = datetime.now(timezone.utc)`。
> - 落库**不在 `with` 进入时同步写**——begin/finish 两段都走 `async_writer` fire-and-forget（§4），区别于 llm 流式必须同步 begin 拿 id；tracing 的 span_id 在 Python 端生成，无需同步回读，故 begin 也可异步。
> - 异常处理：`except BaseException as exc:` 记 FAILED 后 `raise`（不吞异常；与业务一致），`error` 写 `f"{type(exc).__name__}: {exc}"[:2000]`。

### 3.3 跨线程透传 helper（ThreadPoolExecutor）

`ai/nodes` 用 `ThreadPoolExecutor`，子线程不继承 ContextVar，需显式透传：

```python
import contextvars

def run_in_traced_context(fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """在「当前」trace/span 上下文的副本中运行 fn（供 ThreadPoolExecutor 子线程透传）。

    用法：
        ctx = contextvars.copy_context()
        future = executor.submit(ctx.run, worker_fn, arg1)
    或直接：
        future = executor.submit(run_in_traced_context, worker_fn, arg1)
    """
    ctx = contextvars.copy_context()
    return ctx.run(fn, *args, **kwargs)
```

> 文档强约束：**任何 `executor.submit(...)` 包裹的、内部会 `start_span` 的 worker，必须经 `run_in_traced_context` 或 `copy_context().run(...)` 透传**，否则子线程 `current_trace_id()` 为 None，span 静默丢失（不报错）。Batch 1 在 financial graph 的并发节点上以此为样板。

### 3.4 可选装饰器 `@traced_span`

```python
def traced_span(
    name: Optional[str] = None,    # 默认取被装饰函数 __name__
    *,
    span_type: str = SpanType.GRAPH_NODE,
    attributes: Optional[dict[str, Any]] = None,
) -> Callable:
    """函数级埋点装饰器（同步 + async 双兼容）。等价于在函数体外包 start_span。

    用法：
        @traced_span(span_type=SpanType.RAG_OP)
        def ingest_documents(...): ...

        @traced_span("identify_fs", span_type=SpanType.GRAPH_NODE)
        async def identify_fs_node(state): ...
    实现：用 inspect.iscoroutinefunction 分支同步 / async 两套 wrapper，
    各自用 with start_span(...) 包裹调用。
    """
```

---

## 4. 异步写（`infrastructure/async_writer.py`）

**独立实现**（不 import llm.writer），结构对称 llm writer，但**依赖倒置**：infra 只调度无参回调，落库编排由 `trace_record_service`（application）注入。

```python
"""tracing 异步落库调度（fire-and-forget）。埋点延迟绝不被 DB 写入拖累。

依赖倒置：本模块（infra）只提供「把无参回调排到事件循环/同步执行」的机制；
具体写 ai_trace / ai_trace_span 的编排在 tracing.application.service 实现并注入，
保持 infra 不反向依赖 application（interfaces→application→domain←infra 单向）。
"""
from __future__ import annotations
import asyncio, logging
from typing import Callable

logger = logging.getLogger("CIOaaS.tracing.async_writer")

_inflight_tasks: set[asyncio.Task] = set()
_MAX_INFLIGHT: int = 2000   # span 量比 llm call 大，上限给到 2000

def schedule_write(write_fn: Callable[[], None]) -> None:
    """异步 fire-and-forget 执行一次落库回调。同步 / 异步上下文都可调。
    - 异步上下文：create_task + asyncio.to_thread（同步 DB 写不 block loop）
    - 同步上下文（无 loop / 线程池）：直接同步执行
    - inflight 超过 _MAX_INFLIGHT：降级同步执行（避免 OOM）
    DB 失败仅记日志，绝不抛回业务。
    """
    # 实现与 llm writer.schedule_persist_call 同款（见参考），仅 logger 名 + 上限不同。

async def shutdown_tracing_writes(timeout: float = 5.0) -> None:
    """lifespan shutdown 时等待所有 in-flight span/trace 写入排空（同 llm shutdown_pending_writes）。"""

__all__ = ["schedule_write", "shutdown_tracing_writes"]
```

> 关键：`start_trace` / `start_span` 调用的是 `trace_record_service.begin_trace(...)` 等 application 函数，**这些函数内部**用 `schedule_write(lambda: <落库 SQL>)` 把实际 DB 写排队。infra 的 `async_writer` 拿到的永远是无参 `write_fn`，不知道 Trace/Span 实体——满足依赖倒置（与 llm `schedule_persist_call(lambda: begin_and_finish(...))` 完全同构）。

---

## 5. application 层

### 5.1 DTO（`application/dto/`）

`trace_dto.py`：
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

@dataclass(frozen=True)
class TraceWriteDTO:
    """begin_trace 入参（采集 SDK → record service）。"""
    id: str
    name: str
    source: str
    company_id: Optional[str] = None
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    started_at: datetime = None          # SDK 传 now(UTC)
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class TraceFinishDTO:
    """finish_trace 入参。"""
    id: str
    status: str
    finished_at: datetime
    duration_ms: int
    error: Optional[str] = None

@dataclass(frozen=True)
class TraceDTO:
    """查询输出（service → interfaces）。"""
    id: str
    name: str
    source: str
    status: str
    company_id: Optional[str]
    user_id: Optional[str]
    task_id: Optional[str]
    started_at: Optional[str]            # 已格式化 "yyyy-MM-dd HH:mm:ss" UTC
    finished_at: Optional[str]
    duration_ms: Optional[int]
    attributes: dict[str, Any]
    error: Optional[str]
    created_at: Optional[str]

@dataclass(frozen=True)
class TraceListFilters:
    """列表查询规格（interfaces → service → repository 作入参契约，§1.4）。"""
    company_id: Optional[str] = None     # 多租户：列表强制由 interfaces 注入
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    source: Optional[str] = None
    status: Optional[str] = None
    task_id: Optional[str] = None
    name: Optional[str] = None
```

`span_dto.py`：
```python
@dataclass(frozen=True)
class SpanWriteDTO:
    id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: str
    started_at: datetime
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class SpanFinishDTO:
    id: str
    status: str
    finished_at: datetime
    duration_ms: int
    error: Optional[str] = None

@dataclass(frozen=True)
class SpanDTO:
    """查询输出。children 由 query service 在 Python 层组装树时填充。"""
    id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: str
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    duration_ms: Optional[int]
    attributes: dict[str, Any]
    error: Optional[str]
    children: list["SpanDTO"] = field(default_factory=list)
```

### 5.2 `trace_record_service.py`（写编排）

函数式 API（被采集 SDK 调用）：

```python
"""trace/span 写编排：被采集 SDK 注入回调调用，经 async_writer fire-and-forget 落库。

§1.5：application service 管 session + 调 repository；这里把「拿 session + 写表」
封成无参回调交给 async_writer.schedule_write 调度（依赖倒置）。
"""
from __future__ import annotations
import logging
from db import get_session
from tracing.application.dto import (
    TraceWriteDTO, TraceFinishDTO, SpanWriteDTO, SpanFinishDTO,
)
from tracing.domain import Trace, TraceSpan
from tracing.domain.repository import TraceRepository, SpanRepository
from tracing.infrastructure.async_writer import schedule_write

logger = logging.getLogger("CIOaaS.tracing.record")
_trace_repo = TraceRepository()
_span_repo = SpanRepository()


def begin_trace(dto: TraceWriteDTO) -> None:
    """异步写 RUNNING trace 行。"""
    def _write() -> None:
        with get_session() as session:
            _trace_repo.insert(session, _to_trace_entity(dto))
            session.commit()
    schedule_write(_write)


def finish_trace(dto: TraceFinishDTO) -> None:
    """异步更新 trace 终态（status / finished_at / duration_ms / error）。"""
    def _write() -> None:
        with get_session() as session:
            _trace_repo.update_finish(
                session, dto.id, status=dto.status,
                finished_at=dto.finished_at, duration_ms=dto.duration_ms, error=dto.error,
            )
            session.commit()
    schedule_write(_write)


def record_span_begin(dto: SpanWriteDTO) -> None:
    """异步写 RUNNING span 行。"""
    def _write() -> None:
        with get_session() as session:
            _span_repo.insert(session, _to_span_entity(dto))
            session.commit()
    schedule_write(_write)


def record_span_finish(dto: SpanFinishDTO) -> None:
    """异步更新 span 终态。"""
    def _write() -> None:
        with get_session() as session:
            _span_repo.update_finish(
                session, dto.id, status=dto.status,
                finished_at=dto.finished_at, duration_ms=dto.duration_ms, error=dto.error,
            )
            session.commit()
    schedule_write(_write)


# ── 内部 DTO → Entity（converter 内联，单模块小规模）──
def _to_trace_entity(dto: TraceWriteDTO) -> Trace: ...
def _to_span_entity(dto: SpanWriteDTO) -> TraceSpan: ...
```

> **写合并优化（可选，Batch 2）**：begin + finish 两次写可合并为单次「finish 时 upsert」减半写量。本期为简单先 begin/finish 两段（与 llm 一致）；若实测 span 写放大，再在 record service 内做内存缓冲 + 批量 flush（不改 SDK 与 repository 契约）。

### 5.3 `trace_query_service.py`（读编排）

```python
"""trace 查询编排：只读 session + repository 单表查询 + ORM→DTO + span 树组装。

仿 llm.tracking_query_service：函数式 API、get_session、_fmt_dt UTC 格式。
span 树（parent-child）的组装是「多查询 → 内存组装」的编排，属 application 层。
"""
from __future__ import annotations

def list_traces(
    *, filters: TraceListFilters, limit: int = 50, offset: int = 0,
) -> tuple[list[TraceDTO], int]:
    """链路列表 + 多维筛选 + 分页。返回 (rows, total)。company_id 强制过滤（多租户）。"""
    with get_session() as session:
        rows, total = _trace_repo.list_paged(session, filters, limit=limit, offset=offset)
        result = [_to_trace_dto(r) for r in rows]
    return result, total


def get_trace_detail(trace_id: str, *, company_id: Optional[str] = None) -> Optional[TraceDTO]:
    """链路详情：trace 元数据。不存在 / 跨租户 → None。"""
    # company_id 给定时校验归属，防越权读他租户 trace。

def get_trace_spans_tree(trace_id: str, *, company_id: Optional[str] = None) -> list[SpanDTO]:
    """返回该 trace 的 span 列表，组装成 parent-child 树（根 span 列表）。

    实现：repo.list_by_trace(session, trace_id) 取扁平 span（ORDER BY started_at ASC）→
    转 SpanDTO → Python 层按 parent_span_id 建树（O(n) 字典索引）→ 返回根 span 列表，
    children 已挂好。孤儿 span（parent 不在集合）挂到根层级兜底。
    """

def _to_trace_dto(row: "Trace") -> TraceDTO: ...
def _to_span_dto(row: "TraceSpan") -> SpanDTO: ...
def _fmt_dt(dt) -> Optional[str]:  # 复刻 llm.tracking_query_service._fmt_dt（UTC yyyy-MM-dd HH:mm:ss）
```

### 5.4 repository（`domain/repository/`，§1.4 单表）

`trace_repository.py`：
```python
class TraceRepository:
    """单表 ai_trace 访问。session 由 application 传入，不开/提交事务（§1.4）。"""
    def insert(self, session, entity: Trace) -> None: ...
    def update_finish(self, session, trace_id, *, status, finished_at, duration_ms, error) -> None: ...
    def get(self, session, trace_id: str) -> Optional[Trace]: ...
    def list_paged(self, session, filters: TraceListFilters, *, limit, offset) -> tuple[list[Trace], int]:
        """按 filters 构造 select() + count()。所有条件 AND；company_id 非空时强制
        WHERE company_id = :cid；ORDER BY started_at DESC；LIMIT/OFFSET。"""
    def delete_finished_before(self, session, cutoff: datetime) -> int:
        """30 天清理：删 started_at < cutoff 的 trace，返回删除行数。"""
```

`span_repository.py`：
```python
class SpanRepository:
    """单表 ai_trace_span 访问。"""
    def insert(self, session, entity: TraceSpan) -> None: ...
    def update_finish(self, session, span_id, *, status, finished_at, duration_ms, error) -> None: ...
    def list_by_trace(self, session, trace_id: str) -> list[TraceSpan]:
        """ORDER BY started_at ASC（瀑布图时序）。"""
    def delete_by_trace_ids(self, session, trace_ids: list[str]) -> int:
        """30 天清理：先删 span 再删 trace（无 FK，应用层级联）。"""
```

> **§1.4 合规**：repository 单表、不开事务（接 session）、不跨表 JOIN。span 树组装是多查询编排 → 在 query service（§5.3）。

### 5.5 `application/__init__.py` 对外契约（§2.1）

```python
# 跨模块只允许 import 这里（service + dto）。
from tracing.application.service import (
    list_traces, get_trace_detail, get_trace_spans_tree,
    begin_trace, finish_trace, record_span_begin, record_span_finish,
)
from tracing.application.dto import (
    TraceDTO, SpanDTO, TraceListFilters, TraceWriteDTO, SpanWriteDTO,
)
```

---

## 6. interfaces 层

### 6.1 routes（`interfaces/routes.py`）

> ⚠️ 本节为首版实现契约，已有后续演进（company/organization 范围**改为可选**、新增
> `GET /filter-options`、`TraceItem` 增 `attributes` 等），差异汇总见 **§15 实现后变更追记**；
> 现状权威以代码与 `source/tracing/CLAUDE.md` 为准。

仿 llm routes：开关式 Bearer Token（`secrets.compare_digest`）、`{success,code,message,data}` 信封、lowerCamelCase、静态前缀先于通配声明。

```python
from fastapi import APIRouter, Depends, Header, HTTPException, Query

def _require_tracing_token(authorization: Optional[str] = Header(None)) -> None:
    """开关式 Bearer Token：TRACING_API_TOKEN 未配 → 放行（dev 友好）；配了 → 校验。
    复刻 llm._require_admin_token（secrets.compare_digest 防时序侧信道）。"""
    expected = os.environ.get("TRACING_API_TOKEN", "")  # 收口建议见下
    if not expected:
        return
    import secrets
    presented = authorization[7:].strip() if authorization and authorization.startswith("Bearer ") else ""
    if not presented or not secrets.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

api_router = APIRouter(
    prefix="/api/ai/traces",
    tags=["LG Tracing"],
    dependencies=[Depends(_require_tracing_token)],
)

@api_router.get("", response_model=TraceListResponse)
async def list_traces_endpoint(
    company_id: Optional[str] = Query(None, description="多租户过滤（建议必传）"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    source: Optional[str] = Query(None, description="sqs/http/cron/mcp/manual"),
    status: Optional[str] = Query(None, description="RUNNING/SUCCESS/FAILED/PARTIAL"),
    task_id: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TraceListResponse:
    # 校验 source/status 白名单（仿 llm 的 _STATUS_WHITELIST），非法 → 400
    filters = TraceListFilters(company_id=company_id, start_time=start_time, ...)
    rows, total = service.list_traces(filters=filters, limit=limit, offset=offset)
    data = TraceListPagedData(total=total, limit=limit, offset=offset,
                              items=[_to_trace_item(r) for r in rows])
    return TraceListResponse(success=True, code=0, message="OK", data=data)

@api_router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_trace_detail_endpoint(
    trace_id: str,
    company_id: Optional[str] = Query(None, description="多租户校验归属"),
) -> TraceDetailResponse:
    trace = service.get_trace_detail(trace_id, company_id=company_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    spans = service.get_trace_spans_tree(trace_id, company_id=company_id)
    data = TraceDetail(**_to_trace_item(trace).__dict__, spans=[_to_span_node(s) for s in spans])
    return TraceDetailResponse(success=True, code=0, message="OK", data=data)

# 预留（Batch 3 跨进程）：POST /api/ai/traces/spans — HTTP 上报，本期返回 501
@api_router.post("/spans", response_model=SpanReportResponse)
async def report_span_endpoint(request: SpanReportRequest) -> SpanReportResponse:
    raise HTTPException(status_code=501, detail="Cross-process span report not implemented (Batch 3)")

router = api_router   # 供 main.py include
```

> **路由声明顺序**：`POST /spans` 与 `GET /{trace_id}` 不冲突（方法不同 + `/spans` 是 POST）；若未来加 `GET /spans` 静态前缀，必须声明在 `GET /{trace_id}` 之前（仿 llm `/trace` / `/distinct-models` 先于 `/{call_log_id}` 的注释）。

### 6.2 token 收口建议

为与 llm 收口风格一致（llm 用 `get_llm_settings().tracking_api_token`），建议在 `common/config/` 增 `get_tracing_settings()` 暴露 `api_token`（读 `TRACING_API_TOKEN`）。若 Dev 想最小化，直接 `os.environ.get` 也可接受（dev 友好放行语义不变）。

### 6.3 vo response（`interfaces/vo/response.py`，lowerCamelCase 信封）

```python
from pydantic import BaseModel
from typing import Any, Optional

class TraceItem(BaseModel):
    id: str
    name: str
    source: str
    status: str
    companyId: Optional[str] = None
    userId: Optional[str] = None
    taskId: Optional[str] = None
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    durationMs: Optional[int] = None
    error: Optional[str] = None
    createdAt: Optional[str] = None

class SpanNode(BaseModel):
    id: str
    parentSpanId: Optional[str] = None
    name: str
    spanType: str
    status: str
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    durationMs: Optional[int] = None
    attributes: dict[str, Any] = {}
    error: Optional[str] = None
    children: list["SpanNode"] = []

class TraceDetail(TraceItem):
    spans: list[SpanNode] = []

class TraceListPagedData(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TraceItem]

class TraceListResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: TraceListPagedData

class TraceDetailResponse(BaseModel):
    success: bool; code: int; message: str
    data: Optional[TraceDetail] = None
```

`interfaces/vo/request.py`：`TraceQueryRequest`（如改用 body 查询；当前用 Query 参数即可，留作未来）+ `SpanReportRequest`（预留跨进程上报：traceId / parentSpanId / name / spanType / startedAt / finishedAt / attributes）。

---

## 7. 入口埋点方案（重点 — 覆盖 graph / MCP / API-HTTP / SQS consumer）

> 统一抽象：tracing 提供三种埋点形态，按入口场景选用——
> | 形态 | 适用场景 | 入口 |
> |---|---|---|
> | **上下文管理器** `with start_trace/start_span` | 已有清晰代码块边界的入口（graph 入口、node 内手动埋点） | §7.1 |
> | **装饰器** `@traced_span` | 一个函数 = 一个 span 的稳定切点（MCP execute_tool、rag service 方法） | §7.2 |
> | **中间件** | 进程边界统一兜底（FastAPI HTTP 请求） | §7.3 |

### 7.1 graph 入口（financial_extract）— Batch 1 样板

接入点 1：`source/consumer/handlers.py` `process_task()`，现状第 160–169 行已有 `trace_id = uuid.uuid4().hex` + `with trace_id_scope(trace_id):`（喂给 llm）。改造为**外层再包 tracing 的 start_trace，同值复用**：

```python
# handlers.py（改造后，约第 160 行）
from tracing import start_trace            # 顶层 re-export
from llm.infrastructure.tracing import trace_id_scope   # llm 现有，不动

trace_id = uuid.uuid4().hex                # 单一来源（§8）
try:
    with start_trace(
        name="financial_extract", source="sqs", trace_id=trace_id,
        company_id=company_id, task_id=task_id, user_id=created_by,
        attributes={"batchNumber": batch_number, "threadId": thread_id},
    ):
        with trace_id_scope(trace_id):     # llm 软关联同值（llm 代码零改动）
            result = get_extraction_graph_app().invoke(initial_state, config={...})
except Exception:
    ...   # start_trace 已自动记 FAILED；这里保留现有 RETRY 处置
```

接入点 2：graph node 埋点（样板取 1~2 个 node）。在 `source/ai/agent/` 各 node 函数体内：

```python
from tracing import start_span
from tracing.domain.enums import SpanType

def identify_statement_node(state):
    with start_span("identify_fs", span_type=SpanType.GRAPH_NODE):
        ...
        # node 内的 LLM 调用再包一层 llm_call span，attributes 存关联 call_log_id（§8）
        with start_span("llm_identify", span_type=SpanType.LLM_CALL,
                        attributes={"provider": ..., "model": ...}) as span_id:
            result = router.complete(messages, ...)   # llm 无感，照写 ai_llm_call_log
            # 软关联：把本次 llm call_log_id 回填进 span attributes（见 §8 方案）
```

接入点 3（跨线程）：若该 node 用 `ThreadPoolExecutor`（如多文件并发），worker 提交处改 `executor.submit(run_in_traced_context, worker_fn, ...)`（§3.3）。

### 7.2 MCP 入口

接入点：`source/cioaas_mcp/tools_registry.py` `execute_tool()`（第 107 行）——这是所有 `@mcp.tool()` 的统一执行收口。现状第 12–16 行已有 TODO 标注。**在 execute_tool 包一层 start_trace（MCP 一次工具调用 = 一条 trace）+ 工具本身一个 mcp_tool span**：

```python
# tools_registry.py execute_tool（改造）
from tracing import start_trace, start_span
from tracing.domain.enums import SpanType, TraceSource

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    arg_summary = {k: ("<bytes>" if k == "file_content_base64" else v)
                   for k, v in arguments.items()}   # 脱敏：base64 不入 attributes（coding.md §14）
    with start_trace(name=f"mcp:{tool_name}", source=TraceSource.MCP,
                     attributes={"tool": tool_name, "args": arg_summary}):
        with start_span(tool_name, span_type=SpanType.MCP_TOOL,
                        attributes={"tool": tool_name}):
            ...  # 现有路由分发逻辑原样保留；内部下游 router.complete 由 §7.1 同款 llm_call span 覆盖
```

> 说明：MCP 当前在 `main.py` 被临时屏蔽（第 29 / 177–252 行），但接入点已就绪；启用 MCP 时埋点随之生效。MCP 无 company/user 上下文 → trace.company_id 为空（列表查询「MCP」来源时不强制租户）。装饰器形态也可选：给 execute_tool 加 `@traced_mcp` 等价封装，但 execute_tool 需先 start_trace 再 start_span（trace + span 两层），用显式 `with` 更清晰，推荐上面写法。

### 7.3 API / HTTP 入口（FastAPI 中间件）

**中间件设计**（新增 `tracing/interfaces/middleware.py` 或 `infrastructure/http_middleware.py`，归 interfaces 更贴切）：对**带 trace 语义**的请求自动 start_trace，避免污染健康检查 / 静态路由。

```python
# tracing/interfaces/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from tracing import start_trace
from tracing.domain.enums import TraceSource

# 仅对这些前缀的请求自动开 trace（白名单，避免给 /health_check、/api/ai/traces 自身埋点）
_TRACED_PATH_PREFIXES = ("/ai/extract", "/lg/upload", "/financial")
_EXCLUDED_PREFIXES = ("/api/ai/traces", "/health_check", "/actuator", "/mcp")

class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if (not path.startswith(_TRACED_PATH_PREFIXES)) or path.startswith(_EXCLUDED_PREFIXES):
            return await call_next(request)
        company_id = request.headers.get("X-Company-Id")   # 或从已有鉴权上下文取
        with start_trace(name=f"http:{request.method} {path}", source=TraceSource.HTTP,
                         company_id=company_id,
                         attributes={"method": request.method, "path": path}):
            return await call_next(request)
```

集成到 `main.py`（在现有 CORS middleware 之后，约第 197 行后追加）：
```python
# main.py（约第 198 行，app.add_middleware(CORSMiddleware, ...) 之后）
from tracing.interfaces.middleware import TracingMiddleware
app.add_middleware(TracingMiddleware)
```

> **不破坏其他路由**：通过 `_TRACED_PATH_PREFIXES` 白名单 + `_EXCLUDED_PREFIXES` 黑名单双重控制，默认只给业务处理类路由开 trace；trace 查询接口自身、健康检查、MCP mount 一律跳过（否则递归 + 噪音）。中间件异常安全：start_trace 内部失败仅日志，绝不影响请求。
> **与 SQS 入口不重叠**：HTTP `/ai/extract/trigger`（debug 入口）会经中间件开 http trace，再进入 process_task；process_task 已会 start_trace（sqs 同函数）。为避免双 trace，**process_task 的 start_trace 优先**——中间件检测到 `current_trace_id()` 已存在时跳过（start_trace 内部可加「已在 trace 中则复用不新建」的判断，或中间件白名单不含 `/ai/extract/trigger`）。本设计采用后者：`_EXCLUDED_PREFIXES` 增加 `/ai/extract/trigger`，由 handler 层统一开 trace。

### 7.4 SQS consumer 入口

接入点：同 §7.1 接入点 1（`consumer/handlers.py process_task`）。**消费一条 SQS 消息 = process_task 一次调用 = 一条 trace**（source=sqs）。poller（`consumer/poller.py`）只是调度，不另开 trace。

### 7.5 统一入口埋点抽象总结

```
┌─ 进程边界入口（每入口一条 trace，start_trace）────────────────────────┐
│  SQS    → consumer/handlers.py process_task        with start_trace(source=sqs)  │
│  HTTP   → tracing TracingMiddleware（白名单路由）   with start_trace(source=http) │
│  MCP    → cioaas_mcp/tools_registry.execute_tool   with start_trace(source=mcp)  │
│  cron   → 清理 / 定时任务入口                        with start_trace(source=cron) │
└──────────────────────────────────────────────────────────────────────┘
        │ 内部各步骤一个 span（start_span / @traced_span，自动继承 trace_id + 父 span）
        ├─ graph node      span_type=graph_node
        ├─ LLM 调用        span_type=llm_call（attributes 存 call_log_id 软关联）
        ├─ rag 操作        span_type=rag_op
        ├─ MCP 工具        span_type=mcp_tool
        └─ DB / 外部调用   span_type=db / external
```

---

## 8. trace_id 一致性与 llm 软关联

### 8.1 单一来源生成 trace_id

业务入口（process_task / middleware / execute_tool）**只生成一次** `trace_id = uuid.uuid4().hex`，同一个值：
1. 传给 tracing 的 `start_trace(trace_id=trace_id, ...)` → 写 `ai_trace.id`
2. 沿用 llm 现有的 `with trace_id_scope(trace_id):` → 写 `ai_llm_call_log.trace_id`（**llm 代码零改动**，只是业务侧把同值喂进去）

这样 `ai_trace.id == ai_llm_call_log.trace_id`，两侧用同一值软关联（无 FK、无代码耦合）。

### 8.2 llm_call span 关联 call_log_id

`start_span(span_type="llm_call")` 包裹 `router.complete(...)` 时，需把本次 llm 调用的 `call_log_id` 回填到 span 的 `attributes.call_log_id`，供前端从 span 跳转 llm CallDetail 页。

**取 call_log_id 的方式（不改 llm 代码）**：llm router 不直接返回 call_log_id（它在 fire-and-forget 落库里生成）。两种容错策略：
- **方案 A（推荐，本期）**：span attributes 只存 `trace_id`（已知），**不强求 call_log_id**。前端 TraceDetail 点击 llm_call span 时，按 `trace_id` 跳转 llm 现有 `/api/ai/llm-calls/trace/{trace_id}` 时间线页（已存在，§参考 llm routes 第 444 行 `/trace/{trace_id}`）——按 trace_id 即可关联到该链路所有 llm 调用，粒度足够，零侵入。
- **方案 B（Batch 2 增强）**：在 span attributes 额外存 `{provider, model, node, step}`，前端用这些维度 + trace_id 在 llm 列表页加筛选定位单条 call_log。仍不需 llm 改动。

> 结论：**本期采用方案 A**——llm_call span 不依赖 call_log_id，靠共享 trace_id 软跳转，彻底零耦合。call_log_id 精确关联留作 Batch 2 可选增强。

### 8.3 前端软跳转

TraceDetail 页 span 树中，`spanType === "llm_call"` 的节点渲染一个「查看 LLM 调用」链接 → 跳转前端 llm 页面 `/ai/llm/trace/{traceId}`（llm 现有 TraceView，按 trace_id 展示）。无关联数据时不渲染链接（容错）。

---

## 9. 前端设计（`CIOaas-web/src/pages/ai/tracing/`，独立新建，与 llm 页面零耦合）

> 技术栈：React 16 + Ant Design Pro + UmiJS 3 + TypeScript。分层：`pages/`（组件）+ `services/api/tracing/`（HTTP）+ `services/service/tracing/`（业务封装）。

### 9.1 页面组件结构

```
CIOaas-web/src/pages/ai/tracing/
├── TraceList/
│   ├── index.tsx                 # 链路列表页：ProTable + 多维筛选（时间/source/status/name/task）+ 分页
│   └── components/
│       └── TraceStatusTag.tsx    # 状态色标签（RUNNING 蓝 / SUCCESS 绿 / FAILED 红 / PARTIAL 橙）
├── TraceDetail/
│   ├── index.tsx                 # 链路详情页：trace 元数据卡 + SpanWaterfall
│   ├── components/
│   │   ├── SpanWaterfall.tsx     # 瀑布/时间线：递归渲染 span 树（层级缩进 + 耗时条 + 状态色）
│   │   ├── SpanRow.tsx           # 单 span 行：name + type 标签 + duration 条 + 展开子 span
│   │   └── SpanDetailDrawer.tsx  # 点 span 弹出抽屉：attributes / error 全文；llm_call 显「查看 LLM 调用」软链接
│   └── waterfall.css             # 瀑布图样式（耗时条按 durationMs 占比着色，相对 trace 总时长定位）
└── index.ts                      # 路由聚合导出
```

### 9.2 services 分层

```
CIOaas-web/src/services/
├── api/tracing/
│   └── index.ts                  # 纯 HTTP：listTraces(params) / getTraceDetail(traceId, companyId)
└── service/tracing/
    └── index.ts                  # 业务封装：解构信封 .data、span 树扁平化/格式化、跳转 URL 生成
```

`services/api/tracing/index.ts`（仿现有 llm api 风格，用 `@/utils/request`）：
```ts
import request from '@/utils/request';

export async function listTraces(params: {
  companyId?: string; startTime?: string; endTime?: string;
  source?: string; status?: string; taskId?: string; name?: string;
  limit?: number; offset?: number;
}) {
  return request('/api/ai/traces', { method: 'GET', params });
}

export async function getTraceDetail(traceId: string, companyId?: string) {
  return request(`/api/ai/traces/${traceId}`, { method: 'GET', params: { companyId } });
}
```

### 9.3 路由注册

UmiJS 路由配置（`config/routes.ts` 或 `config/config.ts` 的 routes 段）新增，**独立于 llm 路由**：
```ts
{ path: '/ai/tracing', name: 'tracing-list', component: './ai/tracing/TraceList' },
{ path: '/ai/tracing/:traceId', name: 'tracing-detail', component: './ai/tracing/TraceDetail', hideInMenu: true },
```

### 9.4 与 llm 页面零耦合

- tracing 页面**不 import** `pages/ai/llm/` 任何组件 / service。
- 唯一交互：`SpanDetailDrawer` 中 `spanType==='llm_call'` 时渲染 `<a href={`/ai/llm/trace/${traceId}`}>查看 LLM 调用</a>`——纯 URL 软链接，按 trace_id 值约定，无代码依赖。无 trace_id 关联时不渲染该链接（容错）。

---

## 10. 非功能

| 维度 | 设计 |
|---|---|
| **多租户** | 列表查询 `company_id` 强制过滤（query service + repository 双层）；详情按 company_id 校验归属防越权。HTTP/MCP/cron 无租户的 trace company_id 为空，列表查询「全部」时才可见（建议前端默认带 companyId）。 |
| **鉴权** | 开关式 Bearer Token（`TRACING_API_TOKEN` 未配放行 dev 友好，配了校验，`secrets.compare_digest`），复刻 llm。生产配置 `TRACING_API_TOKEN` 即启用。 |
| **30 天保留清理** | cron 任务（`tracing/infrastructure/` 或 `common/` 调度）调 `trace_query_service` 暴露的 `cleanup_traces_before(cutoff)`：先 `span_repo.delete_by_trace_ids`（分批，每批 ≤ 1000 trace_id）再 `trace_repo.delete_finished_before(cutoff)`。`cutoff = now - TRACING_RETENTION_DAYS（默认 30，env 可配）`。与 rag 软删清理风格一致；trace 量大故硬删（非软删）。 |
| **性能** | ① 埋点零阻塞：begin/finish 全异步 fire-and-forget（§4），DB 失败仅日志。② 索引：trace `(company_id, started_at)` / `(status, started_at)`；span `(trace_id, started_at)` / `parent_span_id`。③ attributes 只存摘要（base64/prompt 全文绝不入库，llm 侧已存）。④ `_MAX_INFLIGHT=2000` 上限保护 + lifespan flush。⑤ span 写放大可在 Batch 2 加内存缓冲批量 flush。 |
| **安全 / 脱敏** | attributes 不存敏感全文（coding.md §14 MCP 审计脱敏）：MCP `file_content_base64` → `<bytes>`；error 截断 2000；prompt 全文留 llm 侧仅存 call_log 引用。 |
| **ruff TID251** | tracing 模块**零 LLM SDK 依赖**——不 `import openai/anthropic/langchain`，也不 import `llm.router`（只共享 trace_id 值）。天然满足 §2.2 黑名单，CI `ruff check source/` 通过。 |
| **错误处理** | 埋点 SDK 内所有写路径 `try/except + 仅日志`（绝不打断业务）；routes 用 `HTTPException`；query service 用只读 session。日志名 `CIOaaS.tracing.*`。 |

---

## 11. DB bootstrap（`infrastructure/db_bootstrap.py`）

仿 rag `setup_rag_tables`：`create_all(checkfirst=True)` 让两表在新环境建出（业务 engine，与 ai_trace 同库）。

```python
"""tracing schema bootstrap — 启动期幂等建 ai_trace + ai_trace_span（含索引）。

与 rag.setup_rag_tables / llm.setup_llm_tables 设计对称：FastAPI lifespan 调一次，
create_all(checkfirst=True) 幂等。索引由 ORM __table_args__ 内 Index 声明，create_all
一并建出（无 HNSW 等特殊 access method，无需 raw SQL）。
"""
from __future__ import annotations
import logging
from tracing.domain.models import Trace, TraceSpan   # import 即注册到 Base.metadata

logger = logging.getLogger("CIOaaS.tracing.db_bootstrap")
_TRACING_TABLES = [Trace, TraceSpan]

def setup_tracing_tables(engine=None) -> None:
    from db import get_engine
    from lg.db.models.models import Base
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(
        engine, tables=[t.__table__ for t in _TRACING_TABLES], checkfirst=True,
    )
    logger.info("tracing schema bootstrap: %d tables ensured (ai_trace, ai_trace_span)", len(_TRACING_TABLES))

__all__ = ["setup_tracing_tables"]
```

集成到 `main.py` `agent_runtime_lifespan`（约第 116–122 行，紧随 `setup_llm_tables()` / `setup_rag_tables()` 之后）：
```python
# main.py 约第 122 行后
from tracing.infrastructure.db_bootstrap import setup_tracing_tables
setup_tracing_tables()
```

lifespan flush 集成（仿 `llm_tracking_lifespan`，约第 151–164 行）：在 `combined_lifespan` 增 tracing flush，或复用 `llm_tracking_lifespan` 模式新增 `tracing_lifespan`：
```python
# main.py 新增
from tracing.infrastructure.async_writer import shutdown_tracing_writes

@asynccontextmanager
async def tracing_lifespan(app):
    yield
    await shutdown_tracing_writes(timeout=5.0)

# combined_lifespan 嵌套：tracing_lifespan 放最外层（最后 flush，同 llm_tracking_lifespan 理由）
async with tracing_lifespan(app):
    async with llm_tracking_lifespan():
        async with agent_runtime_lifespan():
            async with ai_consumer_lifespan():
                yield
```

router 挂载（约第 205 行后）：
```python
# main.py
from tracing.interfaces.routes import router as tracing_router
app.include_router(tracing_router)
```

---

## 12. 分批实施清单（文件级交付物，供 Dev 直接据此实现）

### Batch 1 — 最小闭环（模块骨架 + 两表 + SDK + API + 前端 + financial graph 埋点样板）

**后端文件交付物**：
1. `source/tracing/__init__.py` — re-export `start_trace / start_span / traced_span / run_in_traced_context / current_trace_id`
2. `source/tracing/domain/models/_common.py` — Base/_now/_new_uuid（§2.3）
3. `source/tracing/domain/models/trace_model.py` — `class Trace`（§2.1）
4. `source/tracing/domain/models/span_model.py` — `class TraceSpan`（§2.2）
5. `source/tracing/domain/models/__init__.py` — re-export + 注册 metadata
6. `source/tracing/domain/enums.py` — TraceStatus/SpanStatus/SpanType/TraceSource（§2.4）
7. `source/tracing/domain/repository/trace_repository.py` — `TraceRepository`（§5.4）
8. `source/tracing/domain/repository/span_repository.py` — `SpanRepository`（§5.4）
9. `source/tracing/domain/repository/__init__.py` + `domain/__init__.py` — re-export
10. `source/tracing/application/dto/trace_dto.py` / `span_dto.py` / `dto/__init__.py`（§5.1）
11. `source/tracing/application/service/trace_record_service.py`（§5.2）
12. `source/tracing/application/service/trace_query_service.py`（§5.3）
13. `source/tracing/application/service/__init__.py` + `application/__init__.py`（§5.5 对外契约）
14. `source/tracing/infrastructure/async_writer.py`（§4）
15. `source/tracing/infrastructure/trace_context.py` — 采集 SDK（§3）
16. `source/tracing/infrastructure/db_bootstrap.py`（§11）
17. `source/tracing/infrastructure/__init__.py`
18. `source/tracing/interfaces/routes.py` — `GET /api/ai/traces` + `/{trace_id}` + 预留 `POST /spans`（§6.1）
19. `source/tracing/interfaces/vo/request.py` / `response.py` / `vo/__init__.py`（§6.3）
20. `source/tracing/interfaces/__init__.py`
21. `sql/migrations/2026-06-03_tracing_001_create_ai_trace.up.sql`（§2.5）
22. `sql/migrations/2026-06-03_tracing_002_create_ai_trace_span.up.sql`（§2.5）

**接入改造（最小侵入）**：
23. `source/main.py` — 挂 `tracing_router` + `setup_tracing_tables()` + `tracing_lifespan` flush（§11）
24. `source/consumer/handlers.py` — process_task 包 `with start_trace(source=sqs, ...)`（§7.1 接入点 1，约第 160 行）
25. `source/ai/agent/` 1~2 个 node — 包 `with start_span(graph_node)` + 内层 `llm_call` span 样板（§7.1 接入点 2）

**前端文件交付物**：
26. `CIOaas-web/src/services/api/tracing/index.ts`（§9.2）
27. `CIOaas-web/src/services/service/tracing/index.ts`（§9.2）
28. `CIOaas-web/src/pages/ai/tracing/TraceList/index.tsx` + `TraceStatusTag.tsx`（§9.1）
29. `CIOaas-web/src/pages/ai/tracing/TraceDetail/index.tsx` + `SpanWaterfall.tsx` / `SpanRow.tsx` / `SpanDetailDrawer.tsx` / `waterfall.css`（§9.1）
30. UmiJS 路由注册 `/ai/tracing` + `/ai/tracing/:traceId`（§9.3）

**Batch 1 验收**：跑一条真实 financial_extract SQS 任务 → `ai_trace` 出 1 行 + `ai_trace_span` 出 node/llm_call 树 → 前端 TraceList 看到该链路 → TraceDetail 瀑布图展示 span 树 + llm_call 软跳转 llm 页面。

### Batch 2 — rag + MCP + API 中间件 + consumer 全量

31. `source/cioaas_mcp/tools_registry.py` `execute_tool` — 包 start_trace(mcp) + mcp_tool span（§7.2，落实第 12 行 TODO）
32. `source/tracing/interfaces/middleware.py` — `TracingMiddleware`（§7.3）+ `main.py` `add_middleware`
33. `source/rag/application/service/*` — 入库/检索/迁移关键方法加 `@traced_span(span_type=rag_op)`（§7.5）
34. financial graph 全量 node 埋点（Batch 1 只做样板，本批补齐）
35. `source/tracing/infrastructure/cleanup.py`（或 common 调度）— 30 天 cron 清理（§10）
36. 前端：TraceList 增 source=mcp/http/rag 维度筛选 + span attributes 富展示（rag top_k / mcp tool args）
37. （可选增强）span attributes 回填 call_log_id（§8.2 方案 B）+ 前端精确跳转

### Batch 3 — 跨进程预留（不实现逻辑，仅留接口）

38. `source/tracing/interfaces/routes.py` `POST /api/ai/traces/spans` — 落实跨进程 HTTP 上报逻辑（当前 501）
39. `SpanReportRequest` 契约定稿 + Java 网关侧 trace_id 透传约定（HTTP header `X-Trace-Id`）
40. 中间件读 `X-Trace-Id` header 复用外部 trace_id（跨进程同一条 trace）

---

## 13. 关键设计决策摘要

1. **完全独立 + 零侵入 llm**：tracing 自建两表 + SDK + 页面，与 llm 仅共享 `trace_id` 值；llm 代码 0 改动，前端靠 `/ai/llm/trace/{traceId}` 软链接关联。
2. **独立 ContextVar + span 栈**：`tracing_trace_id` + `tracing_span_stack`（tuple 不可变），与 llm 的 `llm_trace_id` 物理隔离；span 栈支持 parent-child 树（llm 无此需求）。
3. **依赖倒置异步写**：`async_writer` 只调度无参回调，落库编排在 `trace_record_service` 注入（`schedule_write(lambda: ...)`），与 llm writer 同构但独立实现，infra 不反依赖 application。
4. **三形态统一埋点抽象**：上下文管理器（graph/手动）/ 装饰器（MCP·rag 方法）/ 中间件（HTTP），覆盖 SQS·HTTP·MCP·cron 全部进程边界入口；trace_id 由进程入口单一生成。
5. **§1.1 命名全合规**：两实体两 service 两 repository 两 DTO 均升级文件夹 + 语义前缀；enums 单文件例外；infra 三功能平铺；无 domain/service（§1.3）。
6. **call_log_id 软关联走容错路径（方案 A）**：本期 llm_call span 不强依赖 call_log_id，靠 trace_id 跳转 llm 时间线页，精确关联留 Batch 2，彻底零耦合。
7. **bootstrap 幂等 + lifespan flush**：`create_all(checkfirst=True)` 新环境自动建表（仿 rag/llm）；shutdown 等待异步写排空防尾部 span 丢失。

---

## 14. 给 Dev 团队的实现顺序建议

1. **先建领域底座**：`domain/models/_common.py` → `trace_model.py` / `span_model.py` → `enums.py` → `__init__` re-export，立即可被 `setup_tracing_tables` 反射建表。先写 migration SQL 与 ORM 对齐自检。
2. **再做基础设施**：`async_writer.py`（直接对照 llm `writer.py` 改 logger + 上限）→ `db_bootstrap.py` → 集成到 `main.py` 验证新环境冷启动两表建出。
3. **写编排 + 读编排**：`trace_record_service.py`（依赖 async_writer）→ repository 两件 → `trace_query_service.py`（span 树组装）。此时可用脚本手插数据验证查询。
4. **采集 SDK**：`trace_context.py`（start_trace/start_span/traced_span/run_in_traced_context），单测覆盖：正常 with、异常记 FAILED、嵌套 span 父子栈、跨线程 copy_context 透传、trace_id 缺失安全降级。
5. **接口层**：`routes.py` + `vo`，对照 llm routes 改前缀 + 字段；冒烟测 `GET /api/ai/traces`。
6. **graph 埋点样板**：改 `consumer/handlers.py`（外包 start_trace，复用现有 trace_id）+ 1~2 个 node 的 start_span；跑一条真实 SQS 任务端到端验证落库。
7. **前端**：先 `services/api` + `services/service` → TraceList（ProTable）→ TraceDetail 瀑布图 → llm 软跳转。先用 Batch 1 真实 trace 数据联调。
8. **Batch 2/3** 按 §12 清单推进；每加一类入口（MCP/HTTP/rag）独立验收一条该来源的真实 trace。

> 全程红线自检：每次提交前跑 `ruff check source/`（验证 TID251 零 LLM SDK 依赖 + 跨模块 import 仅 `tracing.application`）；确认 llm 模块与 `pages/ai/llm/` 无任何改动。

---

## 15. 实现后变更追记（2026-07-03）

> 实现落地后的契约演进汇总（相对 §6 / §9 首版设计）。现状权威 = 代码 +
> `source/tracing/CLAUDE.md`；本节只记差异与动机，不重写正文。

### 15.1 查询范围参数可选化（原"至少必传一个"废除）

- 三个查询端点（列表 `GET /api/ai/traces`、详情 `GET /{trace_id}`、chain `GET /{trace_id}/chain`）
  的 `company_id` / `organization_id` 均**可选**：都不传时列表不加租户条件返回全量
  （`started_at DESC` 分页），详情 / chain 跳过归属校验按 trace_id 直取。
- **传了任一仍按对应通道过滤 / 校验归属，不命中 404**（防越权口径保留；
  `_scope_matches` 双 None 放行、给值必须命中）。
- 动机：这是 dev-support 查询端点，管理端（Portfolio 层）无"当前公司"上下文，
  强制必填导致首屏无法出数。授权闸门本就不是该参数（参数只圈范围），而是
  `TRACING_API_TOKEN` —— **非 dev 环境必须配置该 token，否则无参调用即全租户可读**。
- 背景：`organization_id` 双通道（客户端=company、管理端=organization 且 company 恒
  NULL）由 V002 迁移加列引入。

### 15.2 新端点 `GET /api/ai/traces/filter-options`

- 返回 `{data: {companyIds: string[], organizationIds: string[]}}`：`ai_trace` 表
  distinct 非空值（各自升序），为前端范围筛选下拉供数（仿 llm `distinct-models` 范式）。
- 声明必须先于通配 `/{trace_id}`。

### 15.3 `TraceItem` VO 增 `attributes` 透出

- 链路级 `attributes`（如 HTTP 入口的 `method` / `path`）此前只落库不出参；现列表 /
  详情 / chain 均携带，让无 span 的入口壳 trace 在详情页也能看到入口上下文。

### 15.4 前端（`pages/ai/tracing/`）同步演进

- Company / Organization 由文本框改为**可搜索下拉**（候选值 = filter-options；公司
  label 经 chat 域 service `fetchCompanies` 增强为 `name (id)`，失败退化裸 id 不阻塞），
  选中即时生效；首屏无任何筛选直接请求全量，"companyId 必填门槛 +
  `resolveCurrentCompanyId` 注入"整套删除（`utils/companyId.ts` 已删）。
- 列表新增 **Trace ID 列**（截断 + copyable 复制完整值，作为与 LLM Tracing 等页面
  联查的 join key）；详情页标题 trace_id 同样 copyable。
- 详情页渲染 trace 级 attributes；span 瀑布空态文案改为解释成因（见 15.5）。

### 15.5 chatbot REST 接口 service 层 span 埋点（消除"空壳 trace"）

- 背景：`TracingMiddleware` 对 `/api/ai/chat` 前缀只开链路不下钻，chatbot 的 REST
  CRUD / 管理接口内部原无任何埋点 → 详情页 span 恒为空。
- 落法：chatbot `application/service/` 各公开编排方法体包 `start_span`
  （`chat_history_service` / `chat_manage_service` 全部 `db:*`（`span_type=db`），
  `company_service.accessible_companies` 为 `http:*`（经 Java 网关外呼））；
  attributes 只放 thread_id / 分页等非敏感摘要，消息正文 / title / keyword 不入。
- SSE 对话路径复用这些方法时，span 自然挂到 `chatbot.chat` trace 下；无活跃
  trace 时 `start_span` 安全降级（不落库、不打断业务）。
