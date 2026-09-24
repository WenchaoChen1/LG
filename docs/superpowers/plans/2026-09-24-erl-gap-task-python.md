# ERL 差距分析任务化 — Python 侧实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `source/erl/` 的 Goldie 差距分析从「一个 (公司, 期次) 一份产物、一次 LLM 覆盖全部维度、Redis 期次锁、Share 快照」改成「按 Java 维度任务逐个生成：每任务一次 LLM、并发 3、日志表幂等短路、条目一次写入永不改」，对外只剩 `POST /refresh`（新契约）与 `POST /items` 两个端点。

**Architecture:** Java 持有编排状态（报告记录 + 维度任务表，含 PENDING→RUNNING→SUCCESS/FAILED 的 CAS 状态机），按任务同步 HTTP 派发给 Python；Python 在 `refresh` 内先批量查 `ai_erl_gap_analysis_task`（生成日志 + 幂等标记，SUCCESS 为终态）短路已成功的任务，其余任务附件按 fileId 跨任务去重现场摘要后经 `asyncio.Semaphore(3)` 逐任务「单维 prompt → LLM（重试 2 次）→ 解析 → 一个事务写日志行 + `ai_erl_gap_analysis_task_item` 条目」，逐任务回 `{taskId, status, hasGap}`；双跑靠条目唯一键兜底（撞键按成功处理），不再有 Redis 锁。`items` 端点按任务 id 取 SUCCESS 任务的条目分组下发。旧三张 `ai_erl_gap_analysis*` 表、旧 ORM/仓储本次保留、随 V029 删除。

**Tech Stack:** Python 3.12 / FastAPI / pydantic v2 / SQLAlchemy 2（同步 Session + `asyncio.to_thread`）/ PostgreSQL（版本化迁移 `scripts/migrate.py`）/ `llm.llm_db_router.acomplete`（OpenRouter sonnet，json_mode）/ pytest + pytest-asyncio + pytest-mock（LLM / DB / rag 全 mock）。Windows 下一律 `uv run ...`。

**依赖/顺序：** 本计划先于 Java 计划实施（契约提供方）；部署顺序见设计稿 §9.2（V028（含 GRANT）→ Java sprint119 脚本 → `cio.erl.ai-enabled=false` → Python 发版 → Java 一次性全量替换 → Web → 开开关 → 验证 → V029）。

---

## 全局约束

- 设计稿 `docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md` 是唯一权威；本计划任何一处与之冲突以设计稿为准。
- 遵守 `CIOaas-python/standards/architecture.md`（interfaces → application → domain；repository 单表、首参 `session`、内部不 commit；service 只吃/吐 DTO；domain 无 service）与 `coding.md`（`{success, code, message, data}` 信封、camelCase、`from __future__ import annotations`、Prompt 外置 + 版本字段 + 回归测试）。
- 主方法平铺（`refresh` 一读即懂全流程），重构在**原文件内**做，不新拆文件（新文件只限本计划「文件结构」列出的那些）。
- **不自动跑测试**：每个 Task 末尾只做轻量校验（`uv run python -m py_compile <file>`、`uv run ruff check <path>`）；整套测试单列在 Task 10，需用户下令后执行。
- **不 commit / 不 push**：提交单列在 Task 11，需用户确认。
- 行宽 110（`pyproject.toml` `[tool.ruff] line-length = 110`）。
- 所有命令在仓库根 `D:/workspace/github/LG/python/CIOaas-python` 执行（PowerShell 或 Git Bash 均可；`uv run` 不需要先激活环境）。

## 文件结构

**新增**

| 文件 | 职责 |
|---|---|
| `sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql` | 建 `ai_erl_gap_analysis_task` + `ai_erl_gap_analysis_task_item`（幂等、英文 COMMENT、updated_at 触发器、唯一索引；头注含 GRANT 部署项与「旧三表留 V029」） |
| `source/erl/domain/enums.py` | `GapTaskStatus`（SUCCESS / FAILED）、`GapItemType`（NARRATIVE / GAP / ACTION）——service 写入、repository 比对、测试断言共用一处 |
| `source/erl/domain/models/erl_gap_analysis_task_model.py` | ORM `ErlGapAnalysisTask`（生成日志 + 幂等标记） |
| `source/erl/domain/models/erl_gap_analysis_task_item_model.py` | ORM `ErlGapAnalysisTaskItem`（AI 条目） |
| `source/erl/domain/repository/erl_gap_analysis_task_repository.py` | `find_by_task_ids` / `upsert_by_task_id`（SUCCESS 终态：UPDATE 只命中非 SUCCESS 行，否则 INSERT） |
| `source/erl/domain/repository/erl_gap_analysis_task_item_repository.py` | `find_by_task_ids`（按 task_id, item_type, sort_order, id 排序）/ `bulk_insert` |
| `tests/erl/test_erl_gap_analysis_task_repository.py` | 两个新仓储发出的语句（MagicMock session） |

**修改**

| 文件 | 改动 |
|---|---|
| `source/erl/domain/models/__init__.py` | 追加导出两个新模型（旧三个保留） |
| `source/erl/domain/__init__.py`、`source/erl/domain/repository/__init__.py` | docstring 改口 |
| `source/erl/application/dto/erl_gap_analysis_dto.py` | 按新契约**重写**（输入 / LLM 中间结果 / 输出三组 DTO） |
| `source/erl/application/service/erl_gap_analysis_service.py` | **原文件内重写**：`refresh(dto, *, user_id)` + `items(task_ids)`；删 Redis 锁、shared_snapshot、`_snapshot_is_current`、V027 兜底、share、analyzedContext、noGapDimensions、index↔code 映射与整批校验、summary |
| `source/erl/interfaces/vo/request.py` | **重写**：`GapAnalysisRefreshRequest` / `GapTaskRequest` / `GapAnalysisItemsRequest`（`GapQuestion` / `GapAttachment` 不变） |
| `source/erl/interfaces/vo/response.py` | **重写**：refresh / items 两个信封 |
| `source/erl/interfaces/routes.py` | **重写**：保留 `POST /gap-analysis/refresh`、新增 `POST /gap-analysis/items`、删 `GET /gap-analysis` 与 `POST /gap-analysis/share` |
| `source/erl/__init__.py` | 模块 docstring 改口（两个端点、两张新表、无 infrastructure） |
| `source/main.py` | 挂载处 3 行注释改口 |
| `source/ai/prompts/erl/erl_gap_analysis.md` | **原地**升 v1.7（单维输入、`{narrative, gaps, actions}` 出参、changelog 追加） |
| `source/ai/prompts/erl_gap_analysis_prompts.py` | docstring 改口（runtime_vars） |
| `source/common/enums/caller_node.py` | `ERL_GAP_ANALYSIS` 一行 docstring 改口 |
| `tests/erl/test_erl_gap_analysis_service.py` | **重写**（旧文件整份绑定旧契约） |
| `CIOaas-python/CLAUDE.md` | 「Exit Readiness（ERL）域」段改口 |
| `CIOaas-python/docs/待优化项.md`、`docs/已完成优化.md` | :123 / :126 / :127 / :132 四条——**需用户确认后再改**（本计划只给出拟改文案） |

**删除**

| 文件 | 说明 |
|---|---|
| `source/erl/infrastructure/gap_analysis_lock.py` | Redis 期次锁整体删除（设计 §6.1-5） |
| `source/erl/infrastructure/__init__.py` | 锁删除后该包为空；`architecture.md` §1.1「不造空 `__init__.py` 目录」，整个 `infrastructure/` 目录随之删除（原 `__init__` 只有 docstring、无导出）。锁的单测在旧 `test_erl_gap_analysis_service.py` 末尾（`test_lock_*` 4 例 + `_patch_redis`），随该文件重写一并消失 |

**不动（随 V029 一并处理）**

`source/erl/domain/models/erl_gap_analysis_model.py`、`erl_gap_analysis_dimension_model.py`、`erl_gap_analysis_item_model.py`；`source/erl/domain/repository/erl_gap_analysis_repository.py`、`erl_gap_analysis_dimension_repository.py`、`erl_gap_analysis_item_repository.py`；`tests/erl/test_erl_gap_analysis_repository.py`（只测旧三仓储，仍能通过）；`sql/migrations/business/V024 / V026 / V027`（已应用，永不回改）。

---

### Task 1: V028 迁移脚本

**Files:**
- Create: `sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql`

- [ ] **Step 1: 新建迁移文件（整份内容如下）**

```sql
-- =============================================================================
-- ERL 差距分析任务化（sprint119）：新建 ai_erl_gap_analysis_task + ai_erl_gap_analysis_task_item
--
-- 背景：Java 自本 sprint 起持有「报告分享记录 + 按维度任务」的编排状态（Java 侧
-- erl_gap_analysis_report / erl_gap_analysis_dimension_task），把每个维度任务同步 HTTP 派发给
-- Python；Python **每任务一次 LLM**，把 AI 内容按 Java 任务 id 落到这两张表
-- （设计：LG docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md §3.3 / §3.4）。
--   ① ai_erl_gap_analysis_task：**生成日志 + 幂等标记**，不是状态源（状态源是 Java 的任务表）。
--      一个 Java 任务 id 恒一行；SUCCESS 是本表终态——重投命中 SUCCESS 行直接回状态、不再烧 LLM；
--      FAILED 行可被下一次尝试就地更新（本域唯一允许 UPDATE 的 Python 表）。
--   ② ai_erl_gap_analysis_task_item：AI 条目（NARRATIVE / GAP / ACTION），一次写入永不 UPDATE / DELETE
--      （设计不变量 I2）。唯一索引 (任务 id, item_type, sort_order) 同时是双跑兜底——同一任务被派发两次
--      时后写的一路撞键回滚、按成功处理；期次级 Redis 锁随之删除。
--
-- 与旧三张表（ai_erl_gap_analysis / ai_erl_gap_analysis_dimension / ai_erl_gap_analysis_item，
-- V024 / V026 / V027 建）的关系：**本次不动、不搬存量、不 DROP**（设计决策 D11「存量产物不回填」）。
-- 旧三表连同各自的 updated_at 触发器与函数，留待功能验证通过后的 **V029** 单独 DROP；本文件不写 V029。
--
-- 部署项（缺一条都是 500，而且 LLM 已经烧掉了）：
--   ① **本迁移必须先于 Python 发版执行**（设计 §9.2：V028 → Java sprint119 脚本 → 关 cio.erl.ai-enabled
--      → Python 发版 → Java 一次性全量替换 → Web → 开开关 → 验证 → V029）。
--   ② **GRANT SELECT, INSERT, UPDATE, DELETE ON ai_erl_gap_analysis_task, ai_erl_gap_analysis_task_item
--      TO <Python DB role>**（历次必漏项）。role 名跨环境不同，迁移文件只管 schema、不写 GRANT，
--      部署时人工执行，例如：
--        GRANT SELECT, INSERT, UPDATE, DELETE
--           ON ai_erl_gap_analysis_task, ai_erl_gap_analysis_task_item TO <python_role>;
--
-- 幂等可重跑：CREATE TABLE / CREATE UNIQUE INDEX IF NOT EXISTS + CREATE OR REPLACE FUNCTION
-- + DROP TRIGGER IF EXISTS（CREATE TRIGGER 没有 IF NOT EXISTS，PG 13 也没有 CREATE OR REPLACE TRIGGER）。
-- 无 FK（跨服务引用 Java 任务 id，沿用 ai_ 表软引用约定）；status / item_type / severity **刻意不加
-- CHECK**（取值归一在 Python 出站前完成，加 CHECK 只会把一次模型跑偏变成整份写库失败）。
-- 须与 Python 服务同批上线（ORM 在 erl/domain/models/erl_gap_analysis_task_model.py 与
-- erl_gap_analysis_task_item_model.py）。
-- =============================================================================

-- ========================== ① 生成日志 + 幂等标记 ai_erl_gap_analysis_task

CREATE TABLE IF NOT EXISTS ai_erl_gap_analysis_task (
    id                                  VARCHAR(36) NOT NULL,
    erl_gap_analysis_dimension_task_id  VARCHAR(36) NOT NULL,
    status                              VARCHAR(16) NOT NULL,
    has_gap                             BOOLEAN,
    model                               VARCHAR(64),
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                          VARCHAR(36),
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by                          VARCHAR(36),
    CONSTRAINT pk_ai_erl_gap_analysis_task PRIMARY KEY (id),
    -- 一个 Java 任务 id 恒一行。同时是双跑兜底：两路都判「无行」各自 INSERT 时，后提交的撞这里。
    CONSTRAINT uk_ai_erl_gap_analysis_task UNIQUE (erl_gap_analysis_dimension_task_id)
);

COMMENT ON TABLE  ai_erl_gap_analysis_task IS 'Generation log and idempotency marker for the Goldie gap analysis, one row per Java erl_gap_analysis_dimension_task. NOT the source of truth for task state - that is the Java task table (PENDING / RUNNING / SUCCESS / FAILED with CAS updates). This row only records the outcome of the latest LLM attempt Python made for that task id: SUCCESS is terminal here (a re-dispatch that hits a SUCCESS row returns has_gap immediately without calling the LLM again), FAILED is overwritten in place by the next attempt. The only Python-owned ERL table that is ever UPDATEd.';
COMMENT ON COLUMN ai_erl_gap_analysis_task.id                                 IS 'Primary key (UUID).';
COMMENT ON COLUMN ai_erl_gap_analysis_task.erl_gap_analysis_dimension_task_id IS 'Java erl_gap_analysis_dimension_task.id (soft reference, no DB FK - cross-service reference keeps the full name). Unique: one log row per task.';
COMMENT ON COLUMN ai_erl_gap_analysis_task.status                             IS 'SUCCESS / FAILED - outcome of the latest LLM attempt. No CHECK constraint: the value set is closed in Python (erl.domain.enums.GapTaskStatus). SUCCESS is terminal: the repository UPDATE only matches non-SUCCESS rows, so an attempt to overwrite a SUCCESS row falls through to INSERT and hits uk_ai_erl_gap_analysis_task, which the service treats as "someone else already succeeded".';
COMMENT ON COLUMN ai_erl_gap_analysis_task.has_gap                            IS 'SUCCESS only: true when at least one GAP item was produced (has_gap = count(GAP items) > 0). NULL on FAILED rows. A re-dispatch that hits a SUCCESS row returns this value to Java without a new LLM call.';
COMMENT ON COLUMN ai_erl_gap_analysis_task.model                              IS 'Model used for the attempt, kept for troubleshooting (written on FAILED rows too).';
COMMENT ON COLUMN ai_erl_gap_analysis_task.created_at                         IS 'Created time.';
COMMENT ON COLUMN ai_erl_gap_analysis_task.created_by                         IS 'User who triggered the dispatch: Java forwards the caller''s Bearer token and Python takes ctx.user_id from it.';
COMMENT ON COLUMN ai_erl_gap_analysis_task.updated_at                         IS 'Updated time (maintained by trigger and by the ORM).';
COMMENT ON COLUMN ai_erl_gap_analysis_task.updated_by                         IS 'User of the latest attempt that updated this row.';

-- 一表一函数，对齐 V024 / V026 写法。
CREATE OR REPLACE FUNCTION set_ai_erl_gap_analysis_task_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

-- ⚠️ 这行 DROP 别删：CREATE TRIGGER 没有 IF NOT EXISTS，删掉它重跑第二遍就报 42710 duplicate_object。
DROP TRIGGER IF EXISTS trg_ai_erl_gap_analysis_task_updated_at ON ai_erl_gap_analysis_task;
CREATE TRIGGER trg_ai_erl_gap_analysis_task_updated_at
    BEFORE UPDATE ON ai_erl_gap_analysis_task
    FOR EACH ROW EXECUTE FUNCTION set_ai_erl_gap_analysis_task_updated_at();

-- ========================== ② AI 条目 ai_erl_gap_analysis_task_item

CREATE TABLE IF NOT EXISTS ai_erl_gap_analysis_task_item (
    id                                  VARCHAR(36)   NOT NULL,
    erl_gap_analysis_dimension_task_id  VARCHAR(36)   NOT NULL,
    item_type                           VARCHAR(16)   NOT NULL,
    content                             VARCHAR(1024) NOT NULL,
    severity                            VARCHAR(8),
    sort_order                          INTEGER       NOT NULL,
    created_at                          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    created_by                          VARCHAR(36),
    updated_at                          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_by                          VARCHAR(36),
    CONSTRAINT pk_ai_erl_gap_analysis_task_item PRIMARY KEY (id)
);

-- 唯一索引兼查询索引（前导列就是任务 id，items 端点按任务 id 批量取走它）。
-- 它也是**双跑兜底**：同一任务被派发两次、两路都把 GAP #0 / ACTION #0 / NARRATIVE #0 写进来时，
-- 后提交的一路在这里撞键 → Python 回滚并按成功处理（重查日志行取 has_gap）。
CREATE UNIQUE INDEX IF NOT EXISTS uk_ai_erl_gap_analysis_task_item
    ON ai_erl_gap_analysis_task_item (erl_gap_analysis_dimension_task_id, item_type, sort_order);

COMMENT ON TABLE  ai_erl_gap_analysis_task_item IS 'AI-generated items of one Goldie gap analysis task (NARRATIVE / GAP / ACTION), written once in the same transaction as the SUCCESS log row and never UPDATEd or DELETEd afterwards (design invariant I2). Rows of a task that Java later soft-deletes become orphans and are left for a future cleanup. No FK - same soft-reference convention as the rest of the ai_ tables.';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.id                                 IS 'Primary key (UUID).';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.erl_gap_analysis_dimension_task_id IS 'Java erl_gap_analysis_dimension_task.id (soft reference, no DB FK). Java reads items through result_task_id ?? id, so copied tasks point back at the task that really owns the rows.';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.item_type                          IS 'NARRATIVE / GAP / ACTION - three kinds in one table, no CHECK. NARRATIVE: the dimension-level narrative paragraph, at most one row per task (sort_order 0), only written when the task has at least one GAP. GAP: one gap headline with severity. ACTION: one suggested action. "No gap" is has_gap = false on the log row, never derived from counting rows here.';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.content                            IS 'GAP: the headline. ACTION: the suggested action. NARRATIVE: the whole paragraph. Python truncates to 1024 chars before insert. The former note / why elaborations are NOT stored and NOT folded into this text - the frontend renders titles only (decision D7).';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.severity                           IS 'GAP only: HIGH / MEDIUM / LOW. Anything else the LLM returns is downgraded to MEDIUM before it reaches this table. NULL for NARRATIVE and ACTION.';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.sort_order                         IS 'Display order within (task, item_type), starting at 0; NARRATIVE is always 0, GAP / ACTION follow the model output order (gaps are already sorted by severity by the prompt).';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.created_at                         IS 'Created time.';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.created_by                         IS 'User who triggered the dispatch (same as the log row).';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.updated_at                         IS 'Updated time (trigger kept for convention; rows are never updated).';
COMMENT ON COLUMN ai_erl_gap_analysis_task_item.updated_by                         IS 'Last updater user id; always equals created_by in practice.';

CREATE OR REPLACE FUNCTION set_ai_erl_gap_analysis_task_item_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ai_erl_gap_analysis_task_item_updated_at ON ai_erl_gap_analysis_task_item;
CREATE TRIGGER trg_ai_erl_gap_analysis_task_item_updated_at
    BEFORE UPDATE ON ai_erl_gap_analysis_task_item
    FOR EACH ROW EXECUTE FUNCTION set_ai_erl_gap_analysis_task_item_updated_at();

-- =========================================================================
-- 核验
-- =========================================================================
-- (a) 两张表 + 唯一索引 + 触发器都在：
-- SELECT to_regclass('ai_erl_gap_analysis_task'), to_regclass('ai_erl_gap_analysis_task_item'),
--        to_regclass('uk_ai_erl_gap_analysis_task_item');
-- SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_ai_erl_gap_analysis_task%';
-- (b) Python role 权限（部署项 ②）：
-- SELECT grantee, table_name, privilege_type FROM information_schema.role_table_grants
--  WHERE table_name IN ('ai_erl_gap_analysis_task', 'ai_erl_gap_analysis_task_item')
--  ORDER BY table_name, grantee, privilege_type;
-- (c) 上线后：日志行状态分布 + 条目/任务对账（SUCCESS 且 has_gap=true 的任务应至少有 1 条 GAP）：
-- SELECT status, has_gap, count(*) FROM ai_erl_gap_analysis_task GROUP BY status, has_gap;
-- SELECT t.erl_gap_analysis_dimension_task_id
--   FROM ai_erl_gap_analysis_task t
--   LEFT JOIN ai_erl_gap_analysis_task_item i
--          ON i.erl_gap_analysis_dimension_task_id = t.erl_gap_analysis_dimension_task_id
--         AND i.item_type = 'GAP'
--  WHERE t.status = 'SUCCESS' AND t.has_gap IS TRUE
--  GROUP BY t.erl_gap_analysis_dimension_task_id
-- HAVING count(i.id) = 0;
```

- [ ] **Step 2: 轻量校验——迁移 runner 能识别并预览该文件**

```powershell
uv run python scripts/migrate.py --dry-run --target business
```

预期：输出里列出 `V028__sprint119_erl_gap_analysis_task.sql` 为待应用（本地库不通时只需确认文件名被扫描到；不要真跑 `migrate.py`，DB 迁移全靠人工按环境执行）。

---

### Task 2: domain 枚举 + 两个 ORM 模型

**Files:**
- Create: `source/erl/domain/enums.py`
- Create: `source/erl/domain/models/erl_gap_analysis_task_model.py`
- Create: `source/erl/domain/models/erl_gap_analysis_task_item_model.py`
- Modify: `source/erl/domain/models/__init__.py`（全文替换，原 6 行）
- Modify: `source/erl/domain/__init__.py`（docstring 1 行）

- [ ] **Step 1: 新建 `source/erl/domain/enums.py`**

```python
"""erl 域枚举：日志行状态与条目类型。

放 domain 而不是 service 常量：``status`` 由 service 写入、由 repository 的 UPDATE 条件比对
（SUCCESS 是终态）、由测试断言 —— 三处共用一个定义，否则迟早漂移。写库时取 ``.value``
（不依赖驱动对 str 子类的适配）。
"""
from __future__ import annotations

from enum import StrEnum


class GapTaskStatus(StrEnum):
    """``ai_erl_gap_analysis_task.status``：一次 LLM 尝试的结果。

    ``SUCCESS`` 是**终态**：仓储的 UPDATE 不命中它，重投命中 SUCCESS 行的任务不再烧 LLM。
    ``FAILED`` 可被下一次尝试就地更新。
    """

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class GapItemType(StrEnum):
    """``ai_erl_gap_analysis_task_item.item_type``：NARRATIVE 每任务至多一行（sort_order 0）。"""

    NARRATIVE = "NARRATIVE"
    GAP = "GAP"
    ACTION = "ACTION"


__all__ = ["GapTaskStatus", "GapItemType"]
```

- [ ] **Step 2: 新建 `source/erl/domain/models/erl_gap_analysis_task_model.py`**

```python
"""ai_erl_gap_analysis_task ORM（共享 lg 的 declarative Base，单引擎单 metadata）。

注释约定：每个 ``Column`` 的 ``comment=`` 为英文（与 V028 的 ``COMMENT ON COLUMN`` 一致），
行内 ``#`` 为中文。建表走 ``sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql``，
启动期不自动建表。
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, String, TIMESTAMP, UniqueConstraint, text

from lg.db.models.models import Base, _now


def _uuid() -> str:
    return str(uuid.uuid4())


class ErlGapAnalysisTask(Base):
    """某个 Java 维度任务在 Python 侧的**生成日志 + 幂等标记**（设计 §3.3）。

    不是状态源 —— 任务状态机（PENDING / RUNNING / SUCCESS / FAILED，CAS 更新）在 Java 的
    ``erl_gap_analysis_dimension_task``；本表只记「Python 为这个任务 id 最近一次 LLM 尝试的结果」：
    ``SUCCESS`` 是本表终态（重投命中直接回 ``has_gap``、不再烧 LLM），``FAILED`` 可被下一次尝试
    就地更新 —— 这是本域唯一允许 UPDATE 的 Python 表。
    """
    __tablename__ = "ai_erl_gap_analysis_task"
    __table_args__ = (
        # 一个 Java 任务 id 恒一行；同时是双跑兜底 —— 两路都判「无行」各自 INSERT 时后提交的撞这里，
        # 「想覆盖一条 SUCCESS 行」也会因仓储的 UPDATE 不命中而落到 INSERT、撞这里（见仓储 docstring）。
        UniqueConstraint("erl_gap_analysis_dimension_task_id", name="uk_ai_erl_gap_analysis_task"),
        {"comment": "Generation log and idempotency marker, one row per Java dimension task"},
    )

    id = Column(String(36), primary_key=True, default=_uuid,
                comment="Primary key (UUID)")                               # 主键（UUID）
    # Java erl_gap_analysis_dimension_task.id。列名按跨服务引用保留全名，属性名取短名便于书写
    task_id = Column("erl_gap_analysis_dimension_task_id", String(36), nullable=False,
                     comment="Java erl_gap_analysis_dimension_task.id (soft reference)")
    # SUCCESS / FAILED（erl.domain.enums.GapTaskStatus），不加 CHECK
    status = Column(String(16), nullable=False,
                    comment="SUCCESS / FAILED - outcome of the latest LLM attempt")
    # SUCCESS 时 = GAP 条目数 > 0；FAILED 时为空。重投命中 SUCCESS 行时据此直接回状态
    has_gap = Column(Boolean, nullable=True,
                     comment="SUCCESS only: whether any GAP item was produced")
    model = Column(String(64), nullable=True,
                   comment="Model used for the attempt")                    # 排障用，FAILED 行也写
    # 创建人 = 触发这次派发的用户（Java 转发调用者 Bearer，Python 取 ctx.user_id）
    created_by = Column(String(36), nullable=True,
                        comment="User who triggered the dispatch")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now,
                        server_default=text("now()"),
                        comment="Created time")                             # 创建时间
    updated_by = Column(String(36), nullable=True,
                        comment="User of the latest attempt")               # 最近一次尝试的用户
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now,
                        server_default=text("now()"),
                        comment="Updated time")                             # 修改时间
```

- [ ] **Step 3: 新建 `source/erl/domain/models/erl_gap_analysis_task_item_model.py`**

```python
"""ai_erl_gap_analysis_task_item ORM（共享 lg 的 declarative Base）。

注释约定同 ``erl_gap_analysis_task_model``：``comment=`` 英文、行内 ``#`` 中文。
建表走 ``sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql``，启动期不自动建表。
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, Index, Integer, String, TIMESTAMP, text

from lg.db.models.models import Base, _now


def _uuid() -> str:
    return str(uuid.uuid4())


class ErlGapAnalysisTaskItem(Base):
    """一个任务的 AI 条目（NARRATIVE / GAP / ACTION 三类同表，设计 §3.4）。

    **一次写入永不改**（设计不变量 I2）：与 SUCCESS 日志行同一事务插入，之后既不 UPDATE 也不 DELETE；
    重跑同一任务只会撞唯一索引。``note`` / ``why`` 不落库、也不拼进 ``content``（前端只渲染标题）。
    """
    __tablename__ = "ai_erl_gap_analysis_task_item"
    __table_args__ = (
        # 唯一索引兼查询索引（前导列是任务 id）。也是双跑兜底：后写的一路在这里撞键回滚、按成功处理。
        Index("uk_ai_erl_gap_analysis_task_item",
              "erl_gap_analysis_dimension_task_id", "item_type", "sort_order", unique=True),
        {"comment": "AI items of one gap analysis task (NARRATIVE / GAP / ACTION), write-once"},
    )

    id = Column(String(36), primary_key=True, default=_uuid,
                comment="Primary key (UUID)")                               # 主键（UUID）
    # Java 任务 id（跨服务引用保留列全名；属性名取短名，与日志表 ORM 一致）
    task_id = Column("erl_gap_analysis_dimension_task_id", String(36), nullable=False,
                     comment="Java erl_gap_analysis_dimension_task.id (soft reference)")
    # NARRATIVE 每任务至多一行 / GAP 差距标题 / ACTION 建议动作（erl.domain.enums.GapItemType）
    item_type = Column(String(16), nullable=False,
                       comment="NARRATIVE / GAP / ACTION")
    # 三类共用这 1024 预算，落库前截断；note / why 不在此
    content = Column(String(1024), nullable=False,
                     comment="GAP headline / ACTION text / NARRATIVE paragraph")
    severity = Column(String(8), nullable=True,
                      comment="GAP only: HIGH / MEDIUM / LOW")              # 仅 GAP 有值（出站前已归一）
    # NARRATIVE 恒 0；GAP / ACTION 按模型输出顺序自 0 递增。刻意不给 default：恒由 service 显式赋值
    sort_order = Column(Integer, nullable=False,
                        comment="Display order within (task, item_type), from 0")
    created_by = Column(String(36), nullable=True,
                        comment="User who triggered the dispatch")         # 创建人
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now,
                        server_default=text("now()"),
                        comment="Created time")                             # 创建时间
    updated_by = Column(String(36), nullable=True,
                        comment="Last updater user ID")                     # 修改人（实际恒 = 创建人）
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now,
                        server_default=text("now()"),
                        comment="Updated time")                             # 修改时间
```

- [ ] **Step 4: 改 `source/erl/domain/models/__init__.py`（全文替换）**

```python
"""erl domain 模型：一实体一文件（§1.1），对外统一从本包取。

任务化（sprint119）新增 ``ErlGapAnalysisTask`` / ``ErlGapAnalysisTaskItem``（V028）；旧三个模型
``ErlGapAnalysis`` / ``ErlGapAnalysisDimension`` / ``ErlGapAnalysisItem`` 已无生产调用方，**本次保留**、
随 V029 DROP 旧表时一并删除。
"""
from erl.domain.models.erl_gap_analysis_dimension_model import ErlGapAnalysisDimension
from erl.domain.models.erl_gap_analysis_item_model import ErlGapAnalysisItem
from erl.domain.models.erl_gap_analysis_model import ErlGapAnalysis
from erl.domain.models.erl_gap_analysis_task_item_model import ErlGapAnalysisTaskItem
from erl.domain.models.erl_gap_analysis_task_model import ErlGapAnalysisTask

__all__ = [
    "ErlGapAnalysis",
    "ErlGapAnalysisDimension",
    "ErlGapAnalysisItem",
    "ErlGapAnalysisTask",
    "ErlGapAnalysisTaskItem",
]
```

- [ ] **Step 5: 改 `source/erl/domain/__init__.py`（全文替换，原 1 行）**

```python
"""erl domain 层：ORM 模型与单表仓储（任务化起自持 ai_erl_gap_analysis_task / _task_item 两表；旧三表随 V029 删）。"""
```

- [ ] **Step 6: 轻量校验**

```powershell
uv run python -m py_compile source/erl/domain/enums.py source/erl/domain/models/erl_gap_analysis_task_model.py source/erl/domain/models/erl_gap_analysis_task_item_model.py source/erl/domain/models/__init__.py
uv run ruff check source/erl/domain
```

---

### Task 3: 两个单表仓储 + 仓储测试

**Files:**
- Create: `source/erl/domain/repository/erl_gap_analysis_task_repository.py`
- Create: `source/erl/domain/repository/erl_gap_analysis_task_item_repository.py`
- Modify: `source/erl/domain/repository/__init__.py`（docstring 1 行）
- Test: `tests/erl/test_erl_gap_analysis_task_repository.py`（新建）

- [ ] **Step 1: 新建 `source/erl/domain/repository/erl_gap_analysis_task_repository.py`**

```python
"""ai_erl_gap_analysis_task 单表仓储。

§1.4：函数第一参数为 service 传入的 ``session``，内部不 commit；只碰本表。

本表的写规则只有一条、写死在 ``upsert_by_task_id`` 里：**SUCCESS 是终态**。UPDATE 只命中非 SUCCESS
行，命中不了就走 INSERT，由唯一约束 ``uk_ai_erl_gap_analysis_task`` 把「想覆盖 SUCCESS 行」变成一个
``IntegrityError`` 交给 service 处理（成功路径：重查取 has_gap 按成功处理；失败路径：回滚忽略）。
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from erl.domain.enums import GapTaskStatus
from erl.domain.models import ErlGapAnalysisTask


def find_by_task_ids(session: Session, task_ids: list[str]) -> list[ErlGapAnalysisTask]:
    """按 Java 任务 id 批量取日志行（无序；缺行 = 该任务 Python 从未跑完过一次尝试）。

    空列表直接返回、不发 SQL：``IN ()`` 在 PG 上是语法错误，而调用方在「全部任务都已 SUCCESS」
    那一轮确实会传空。
    """
    if not task_ids:
        return []
    return list(session.scalars(
        select(ErlGapAnalysisTask).where(ErlGapAnalysisTask.task_id.in_(task_ids))
    ).all())


def upsert_by_task_id(session: Session, *, task_id: str, status: str, has_gap: Optional[bool],
                      model: Optional[str], user_id: Optional[str]) -> None:
    """按任务 id 存在**且未 SUCCESS**则 UPDATE、否则 INSERT（不 commit）。

    **SUCCESS 是本表终态**：无论来者是 SUCCESS（双跑的后一路）还是 FAILED（双跑里先成功后失败的
    那一路），都不许覆盖一条 SUCCESS 行 —— 否则会出现「日志行翻成 FAILED / has_gap 翻转，条目却
    还在」这种读不出来的不一致。UPDATE 的 WHERE 带 ``status <> 'SUCCESS'``，命中不了就落到 INSERT，
    由唯一约束把「覆盖 SUCCESS」变成 IntegrityError 上抛给 service（它知道该按成功还是按忽略处理）。

    先 UPDATE 再按 ``rowcount`` 补 INSERT，而不是先 SELECT 再分支：少一次往返，且命中时先拿到行锁。
    ``status`` / 写库一律取枚举的 ``.value``，不依赖驱动对 str 子类的适配。
    """
    updated = session.execute(
        update(ErlGapAnalysisTask)
        .where(ErlGapAnalysisTask.task_id == task_id)
        .where(ErlGapAnalysisTask.status != GapTaskStatus.SUCCESS.value)
        .values(status=str(status), has_gap=has_gap, model=model, updated_by=user_id)
    ).rowcount
    if updated:
        return
    session.add(ErlGapAnalysisTask(
        id=str(uuid.uuid4()), task_id=task_id, status=str(status), has_gap=has_gap, model=model,
        created_by=user_id, updated_by=user_id))


__all__ = ["find_by_task_ids", "upsert_by_task_id"]
```

- [ ] **Step 2: 新建 `source/erl/domain/repository/erl_gap_analysis_task_item_repository.py`**

```python
"""ai_erl_gap_analysis_task_item 单表仓储。

§1.4：函数第一参数为 service 传入的 ``session``，内部不 commit；只碰本表。

**只有读与插入，没有 UPDATE / DELETE**（设计不变量 I2：条目一次写入永不改）。重跑同一任务时的
「撞唯一键」不在这里处理 —— ``bulk_insert`` 只 ``add_all``，IntegrityError 在 service 的 commit 处
出现、由 service 决定按成功处理。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from erl.domain.models import ErlGapAnalysisTaskItem


def find_by_task_ids(session: Session, task_ids: list[str]) -> list[ErlGapAnalysisTaskItem]:
    """按任务 id 批量取条目，按 (task_id, item_type, sort_order, id) 排序（分组在 service 做）。

    末尾的 ``id`` 是稳定 tie-breaker（唯一索引下前三键不会重复，留着是防将来放宽索引时读序漂移）。
    空列表直接返回、不发 SQL（``IN ()`` 是语法错误）。
    """
    if not task_ids:
        return []
    return list(session.scalars(
        select(ErlGapAnalysisTaskItem)
        .where(ErlGapAnalysisTaskItem.task_id.in_(task_ids))
        .order_by(ErlGapAnalysisTaskItem.task_id,
                  ErlGapAnalysisTaskItem.item_type,
                  ErlGapAnalysisTaskItem.sort_order,
                  ErlGapAnalysisTaskItem.id)
    ).all())


def bulk_insert(session: Session, items: list[ErlGapAnalysisTaskItem]) -> None:
    """只 ``add_all``（不 flush 不 commit）：撞 ``uk_ai_erl_gap_analysis_task_item`` 的 IntegrityError 在
    service 的 commit 处抛出，由 service 决定按成功处理。"""
    if not items:
        return
    session.add_all(items)


__all__ = ["find_by_task_ids", "bulk_insert"]
```

- [ ] **Step 3: 改 `source/erl/domain/repository/__init__.py`（全文替换，原 1 行）**

```python
"""erl domain 仓储：一表一文件（§1.1/§1.4），session 由 application/service 传入。任务化起生产只用
``erl_gap_analysis_task_repository`` / ``erl_gap_analysis_task_item_repository``；旧三个仓储随 V029 删除。"""
```

- [ ] **Step 4: 新建 `tests/erl/test_erl_gap_analysis_task_repository.py`**

```python
"""erl 任务化两个单表仓储（ai_erl_gap_analysis_task / ai_erl_gap_analysis_task_item）。

全仓单测零真实 DB：``session`` 用 MagicMock，断言落在**发出去的语句**上（表名、过滤键、
SET 了哪些列、排序键），而不是查询结果 —— 结果是 mock 给的。

守住的四条口径：

- ``upsert_by_task_id`` 的 UPDATE **只命中非 SUCCESS 行**（SUCCESS 是终态）：少了这个 WHERE，
  双跑里「先成功后失败」的那一路会把 SUCCESS 行翻成 FAILED，而条目还在 —— 读不出来的不一致；
- 命中 0 行时走 INSERT（新任务第一次尝试 / 想覆盖 SUCCESS 行 —— 后者由唯一约束在 commit 时挡下）；
- 条目仓储**没有** UPDATE / DELETE（设计不变量 I2），读序固定 (task_id, item_type, sort_order, id)；
- 空 id 列表不发 SQL（``IN ()`` 是语法错误），仓储内部绝不 commit。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from erl.domain.enums import GapTaskStatus
from erl.domain.models import ErlGapAnalysisTask, ErlGapAnalysisTaskItem
from erl.domain.repository import erl_gap_analysis_task_item_repository as item_repo
from erl.domain.repository import erl_gap_analysis_task_repository as task_repo


def _session(*, all_=None, rowcount: int = 0) -> MagicMock:
    session = MagicMock()
    session.scalars.return_value.all.return_value = all_ or []
    session.execute.return_value.rowcount = rowcount
    return session


def _statement(session: MagicMock, method: str):
    return getattr(session, method).call_args.args[0]


# ============================================================================
# 日志表仓储
# ============================================================================


def test_find_by_task_ids_filters_with_in_on_the_java_task_id_column():
    row = ErlGapAnalysisTask(id="l-1", task_id="t-1", status="SUCCESS", has_gap=True)
    session = _session(all_=[row])

    found = task_repo.find_by_task_ids(session, ["t-1", "t-2"])

    assert found == [row]
    stmt = _statement(session, "scalars")
    sql = str(stmt)
    assert "ai_erl_gap_analysis_task" in sql
    # 过滤列是跨服务引用的全名列，不是属性名 task_id
    assert "erl_gap_analysis_dimension_task_id IN" in sql
    # expanding IN 的绑定值是**一个列表**（不是逐个标量），故按列表比对
    assert list(stmt.compile().params.values()) == [["t-1", "t-2"]]
    session.commit.assert_not_called()


def test_find_by_task_ids_with_no_ids_sends_no_sql():
    """全部任务都已 SUCCESS 那一轮会传空列表；``IN ()`` 在 PG 上是语法错误。"""
    session = _session()

    assert task_repo.find_by_task_ids(session, []) == []
    session.scalars.assert_not_called()


def test_upsert_updates_a_non_success_row_in_place():
    session = _session(rowcount=1)

    task_repo.upsert_by_task_id(session, task_id="t-1", status=GapTaskStatus.SUCCESS, has_gap=True,
                                model="anthropic/claude-sonnet-5", user_id="u-1")

    stmt = _statement(session, "execute")
    assert str(stmt).startswith("UPDATE ai_erl_gap_analysis_task")
    params = stmt.compile().params
    assert params["status"] == "SUCCESS"
    assert params["has_gap"] is True
    assert params["model"] == "anthropic/claude-sonnet-5"
    assert params["updated_by"] == "u-1"
    # 定位键 + 终态守卫两个条件都在
    assert "t-1" in params.values()
    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_upsert_never_matches_a_success_row():
    """**本文件最重要的一条**：UPDATE 的 WHERE 必须带 ``status <> 'SUCCESS'``。

    没有它，双跑里「先成功后失败」的那一路会把 SUCCESS 行翻成 FAILED —— 条目还在、日志却说失败，
    Java 会按 FAILED 重投、Python 重跑撞条目唯一键、回滚后重查却查到 FAILED 行 ⇒ 永远兜不出来。
    """
    session = _session(rowcount=0)

    task_repo.upsert_by_task_id(session, task_id="t-1", status=GapTaskStatus.FAILED, has_gap=None,
                                model="anthropic/claude-sonnet-5", user_id="u-1")

    stmt = _statement(session, "execute")
    sql = str(stmt)
    assert "status !=" in sql, "终态守卫没了：SUCCESS 行会被覆盖"
    assert "SUCCESS" in stmt.compile().params.values()


def test_upsert_inserts_when_no_row_was_updated():
    """第一次尝试（无行）或想覆盖 SUCCESS 行（UPDATE 不命中）都走 INSERT；后者由唯一约束在 commit 时挡下。"""
    session = _session(rowcount=0)

    task_repo.upsert_by_task_id(session, task_id="t-9", status=GapTaskStatus.FAILED, has_gap=None,
                                model="anthropic/claude-sonnet-5", user_id="u-1")

    row = session.add.call_args.args[0]
    assert isinstance(row, ErlGapAnalysisTask)
    assert row.task_id == "t-9"
    assert row.status == "FAILED" and isinstance(row.status, str)
    assert row.has_gap is None
    assert row.model == "anthropic/claude-sonnet-5"
    assert (row.created_by, row.updated_by) == ("u-1", "u-1")
    assert row.id, "id 显式生成，不靠 flush 才有值"
    session.commit.assert_not_called()


def test_task_repository_has_no_delete():
    """日志行只 upsert；「删掉某任务的日志」不是本域的事（Java 软删任务时 Python 行成孤儿，留后续清理）。"""
    assert not any(name.startswith("delete") for name in dir(task_repo))


# ============================================================================
# 条目表仓储
# ============================================================================


def test_item_find_by_task_ids_filters_and_orders():
    rows = [ErlGapAnalysisTaskItem(id="i-1", task_id="t-1", item_type="GAP", content="x",
                                   sort_order=0)]
    session = _session(all_=rows)

    found = item_repo.find_by_task_ids(session, ["t-1"])

    assert found == rows
    stmt = _statement(session, "scalars")
    sql = str(stmt)
    assert "ai_erl_gap_analysis_task_item" in sql
    assert "erl_gap_analysis_dimension_task_id IN" in sql
    assert list(stmt.compile().params.values()) == [["t-1"]]
    # 读序固定：任务 → 类型 → sort_order → id（分组在 service 做，乱序会让 gaps 的严重度顺序失真）
    order_by = sql[sql.index("ORDER BY"):]
    assert order_by.index("erl_gap_analysis_dimension_task_id") < order_by.index("item_type")
    assert order_by.index("item_type") < order_by.index("sort_order")
    assert order_by.rstrip().endswith("ai_erl_gap_analysis_task_item.id")
    session.commit.assert_not_called()


def test_item_find_by_task_ids_with_no_ids_sends_no_sql():
    session = _session()

    assert item_repo.find_by_task_ids(session, []) == []
    session.scalars.assert_not_called()


def test_bulk_insert_stages_every_row_without_flushing():
    """只 add_all：撞唯一索引的 IntegrityError 要留到 service 的 commit 处抛，service 才知道怎么处理。"""
    session = _session()
    rows = [
        ErlGapAnalysisTaskItem(id="i-1", task_id="t-1", item_type="NARRATIVE", content="n", sort_order=0),
        ErlGapAnalysisTaskItem(id="i-2", task_id="t-1", item_type="GAP", content="g", severity="HIGH",
                               sort_order=0),
    ]

    item_repo.bulk_insert(session, rows)

    session.add_all.assert_called_once_with(rows)
    session.flush.assert_not_called()
    session.commit.assert_not_called()


def test_bulk_insert_of_nothing_touches_no_session():
    """无差距任务没有任何条目是合法结果；空 add_all 只是噪声。"""
    session = _session()

    item_repo.bulk_insert(session, [])

    session.add_all.assert_not_called()


def test_item_repository_is_write_once():
    """防回归（设计不变量 I2）：条目仓储不得出现 update / delete，谁加谁就是在破坏「一次写入永不改」。"""
    assert not any(name.startswith(("update", "delete")) for name in dir(item_repo))
```

- [ ] **Step 5: 轻量校验**

```powershell
uv run python -m py_compile source/erl/domain/repository/erl_gap_analysis_task_repository.py source/erl/domain/repository/erl_gap_analysis_task_item_repository.py tests/erl/test_erl_gap_analysis_task_repository.py
uv run ruff check source/erl/domain tests/erl/test_erl_gap_analysis_task_repository.py
```

---

### Task 4: DTO 按新契约重写

**Files:**
- Modify: `source/erl/application/dto/erl_gap_analysis_dto.py`（全文替换，原 291 行）

- [ ] **Step 1: 全文替换 `source/erl/application/dto/erl_gap_analysis_dto.py`**

```python
"""ERL 差距分析 DTO（``erl_gap_analysis_service`` 的入参 / 出参契约，任务化契约见设计稿 §6）。

字段一律 snake_case（Python 侧口径），并统一挂 ``alias_generator=to_camel`` ——
Java 侧契约是 lowerCamelCase，故：

  - 入参：路由把 Request VO ``model_dump()``（camel 键）直接 ``model_validate`` 成本 DTO；
  - 出参：路由把本 DTO ``model_dump(by_alias=True)`` 直接 ``model_validate`` 成 Response VO。

这样 Request/Response（interfaces）与 DTO（application）两套实体各自独立定义（coding.md §2），
中间不需要一层纯字段搬运的 converter。

三组 DTO：**输入**（一次 refresh 的任务包）→ **LLM 中间结果**（单维解析产物，落库前）→ **输出**
（逐任务状态 / 逐任务条目）。决策 D7 砍掉的 summary / analyzedContext / model / generatedAt / note /
why / evidenceMissing / stale / generating / shared* 一个都不再出现。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    """camelCase 别名基类（见模块 docstring）。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ─────────────────────────── 输入 ───────────────────────────


class GapAttachmentDTO(_CamelModel):
    """一道题的证据附件（design-doc §5.1）。

    ``file_id`` / ``file_name`` 由 Java 下发；``summary`` / ``summary_available`` 由
    ``erl_gap_analysis_service`` **现场解析附件生成**后回填（Java 不碰摘要）。

    ``file_name`` 不只是给模型看的：它决定 loader 按哪种格式解析（按扩展名分发），``files`` 行被清理
    导致它为空时该附件直接判无摘要 —— 没有扩展名会静默兜底纯文本 loader，把 PDF 读成乱码送进 prompt。

    生成失败 / 超时一律 ``summary_available=False``，分析不等待、不阻断。
    """

    file_id: str
    file_name: Optional[str] = None
    summary: Optional[str] = None
    summary_available: bool = False


class GapQuestionDTO(_CamelModel):
    """逐题作答快照。

    v4.0：全部题恒 Yes/No（答案在 ``founder_yes_no`` / ``gsv_yes_no``），每题归属一个 level
    （``era_band`` 1-9）。未解锁 level 的题表现为该端 ``*_yes_no`` 为空（Java ``loadQuestions``
    不按 level 过滤）。题级判定标准 ``criteria`` 已于 2026-09-06 按需求方裁决删除，不留兼容字段。
    """

    question_text: str
    era_band: Optional[int] = None
    era_label: Optional[str] = None
    evidence_source: Optional[str] = None
    founder_yes_no: Optional[bool] = None
    gsv_yes_no: Optional[bool] = None
    founder_note: Optional[str] = None
    gsv_note: Optional[str] = None
    attachments: list[GapAttachmentDTO] = Field(default_factory=list)


class GapTaskInputDTO(_CamelModel):
    """一个 Java 维度任务 = 一个维度的双端评估输入（设计 §6.1）。

    ``task_id`` 是 Java ``erl_gap_analysis_dimension_task.id``：**仅供落库与回状态、绝不进 prompt**
    （渲染时由 service ``_PROMPT_EXCLUDE`` 剔除 —— 让模型逐字复现无语义串本就不可靠，此前 ``code``
    的规则原样沿用）。维度身份给模型看的是 ``name`` / ``abbr``。

    ``*_level_score`` 为 ``None`` = 该维在该题集版本内 0 题（**不是 0 分**）；``*_terminated_level``
    为 ``None`` = 该端全部有题的 level 都已通过。
    """

    task_id: str
    name: Optional[str] = None
    abbr: Optional[str] = None
    weight: Optional[float] = None
    founder_level_score: Optional[int] = None
    gsv_level_score: Optional[int] = None
    perception_gap: Optional[int] = None
    founder_terminated_level: Optional[int] = None
    gsv_terminated_level: Optional[int] = None
    questions: list[GapQuestionDTO] = Field(default_factory=list)


class GapAnalysisRefreshInputDTO(_CamelModel):
    """一次 refresh 的输入：某公司某期次**本次派发的任务**（Python 不查 ERL 评估表，输入全部由 Java 传入）。

    非空 / ``task_id`` 唯一由 Request VO 在边界上 422（``request.GapAnalysisRefreshRequest``），
    本 DTO 不重复校验。``company_id`` / ``period`` 只进 prompt 与日志，不再是任何表的键。
    """

    company_id: str
    period: str
    tasks: list[GapTaskInputDTO] = Field(default_factory=list)


# ─────────────────────────── LLM 中间结果（单维，落库前） ───────────────────────────


class GapItemDTO(_CamelModel):
    """一条差距：只有标题与严重度（决策 D7，``note`` / ``evidenceMissing`` 已砍）。
    ``severity`` 值域恒 HIGH/MEDIUM/LOW（service 解析时归一，见 ``_normalize_severity``）。"""

    title: str
    severity: str


class GapActionDTO(_CamelModel):
    """一条建议动作：只有标题（决策 D7，``why`` 已砍）。"""

    title: str


class GapDimensionResultDTO(_CamelModel):
    """一次 LLM 调用的解析产物 = **一个维度**的结果（prompt v1.7）。

    ``narrative`` **只在有差距时留下**（无差距的维度前端渲染 ``No Gap``，没有承载叙述的落点）；
    ``gaps`` 为空是合法结果，``has_gap = len(gaps) > 0`` 由 service 落日志行时算。
    """

    narrative: Optional[str] = None
    gaps: list[GapItemDTO] = Field(default_factory=list)
    actions: list[GapActionDTO] = Field(default_factory=list)


# ─────────────────────────── 输出 ───────────────────────────


class GapTaskStatusDTO(_CamelModel):
    """refresh 逐任务回的状态（契约 §6.1 出参）。

    ``status`` 取 ``erl.domain.enums.GapTaskStatus`` 的值：SUCCESS 时 ``has_gap`` 必为 bool，
    FAILED 时恒 ``None``（Java 按 FAILED 走自愈重投，不读 has_gap）。
    """

    task_id: str
    status: str
    has_gap: Optional[bool] = None


class GapTaskItemsDTO(_CamelModel):
    """items 端点里一个任务的条目（契约 §6.2 出参）。无条目的任务压根不出现在列表里。"""

    task_id: str
    narrative: Optional[str] = None
    gaps: list[GapItemDTO] = Field(default_factory=list)
    actions: list[GapActionDTO] = Field(default_factory=list)


__all__ = [
    "GapAttachmentDTO",
    "GapQuestionDTO",
    "GapTaskInputDTO",
    "GapAnalysisRefreshInputDTO",
    "GapItemDTO",
    "GapActionDTO",
    "GapDimensionResultDTO",
    "GapTaskStatusDTO",
    "GapTaskItemsDTO",
]
```

- [ ] **Step 2: 轻量校验**

```powershell
uv run python -m py_compile source/erl/application/dto/erl_gap_analysis_dto.py
uv run ruff check source/erl/application/dto
```

（此时 `service` / `routes` 仍引用旧 DTO 名，import 会失败——属计划内的中间态，Task 6 / 7 收口。）

---

### Task 5: prompt v1.7（原地改）+ 外壳 docstring

**Files:**
- Modify: `source/ai/prompts/erl/erl_gap_analysis.md`（全文替换，原 375 行；**文件名不变**）
- Modify: `source/ai/prompts/erl_gap_analysis_prompts.py`（docstring，原 1-8 行）

- [ ] **Step 1: 全文替换 `source/ai/prompts/erl/erl_gap_analysis.md`**

保留 §2 计分口径、§5 判断规则主体、§6 措辞硬约束（含 GSV 分与内部称谓禁令）、附件摘要用法、narrative 三句结构；改动点：输入从 `dimensions[]` + `analyzedContext[]` 变为**单个维度对象**、去 `index`、去 `summary`、出参去 `note` / `why` / `evidenceMissing`、规则重新编号、changelog 追加 1.7、`runtime_vars` 变为 `company_id / period / dimension_json`。

````markdown
---
prompt_id: erl_gap_analysis
version: 1.7
role: system + user
input: 一家公司某期次**某一个维度**的评估结果（双端 level 分 + 止步 level + 逐级解锁的 Yes/No 作答与备注 + 附件摘要）
renders_to:
  system: ERL_GAP_ANALYSIS_SYSTEM_PROMPT
  user:   ERL_GAP_ANALYSIS_USER_PROMPT
used_by:
  - source/erl/application/service/erl_gap_analysis_service.py::_run_task
runtime_vars:
  - company_id
  - period
  - dimension_json
changelog:
  - "1.7 (2026-09-24)：**任务化 —— 每次调用只分析一个维度**（设计 2026-09-24-erl-gap-analysis-task-model-design
     §6.4 / 决策 D6、D7）。① 输入由「`dimensions[]` + `analyzedContext[]` 两个数组」改为**单个维度对象**
     `dimension_json`；删 `index`（不再需要跨维度对号）、删 `analyzedContext`（其它维度由平台分别调用）。
     ② 输出改为 `{narrative, gaps:[{title, severity}], actions:[{title}]}`：删顶层 `summary` 与 `dimensions[]`
     包裹、删 `index`，条目**只剩标题**——`note` / `why` / `evidenceMissing` 永久砍掉（前端只渲染标题）。
     ③ 规则重编号：原规则 12 的「输入里每一个维度都要出现」与原规则 14（summary 覆盖全貌）整条删除；
     原规则 4 的 `evidenceMissing` 置位改为「无证据的 Yes 题不得当作已具备证据的做法引用」；原规则 11
     的 `why` 复述依据改为「依据写进 `title` 本身」。④ §6 删 summary 段落；§3 删 `index` 标识说明。
     计分口径（§2）、双端处置、附件摘要用法、内部称谓禁令、narrative 三句结构、数量约束全部保留。"
  - "1.6 (2026-09-20)：**称谓订正 + 计分口径纠错 + 一轮审核修复**（同一次改动，未拆版本）。
     ① 平台名 `LG 平台` → `Looking Glass 平台(LG)`（产品真名见 PRD 首行与 Java 用户可见文案；
     同目录 extract 系列已三处为 `LG` 加消歧注，易与 General Ledger 混淆）；`LG 投后团队（GSV）`
     → `GSV 团队（投资方一侧…）`（「投后团队」在 PRD / design-doc 全文 0 命中）。
     ② §6 新增硬约束：输出里不得出现内部称谓（含输入字段名 `gsvNote` 之类），改用
     `external validation`；但维度名 / 题干本身含这些词照引不违规。
     ③ **§2 计分口径纠错** —— 原文「维度分 = `terminatedLevel − 1`，与更低的 level 有没有题目
     无关」是 2026-09-15（design-doc v4.37）已作废的旧口径，举例「只配 3/6/9、L3 踩 No → 2」
     恰是 `ErlLevelScorerTest` 点名的反例（实际 0）。改为「有题 level 升序列表里的前一个」，
     补「答满才算通过」「解锁 / 终止每端各一套」「止步 level 之后仍可能有已答的 Yes 行」三条，
     `0` 的定义改为「第一个有题的 level 内就出现 No」。
     ④ §5 规则 3 原写「未解锁 level 的题不在输入中」**与 Java 实现不符**（`loadQuestions` 不按
     level 过滤，下发该维全部题目，未解锁表现为 `*YesNo` 键缺失），改为「未作答的题不得编造
     判断」。
     ⑤ §7 `narrative` 首句原来只说「写分数」不指明哪一端 —— 该段 share 后创始人可见，而公司端
     被服务端硬裁掉 GSV 分（design-doc §4.3），故定死只取 founder 侧并补「已通关 / 该端无数据」
     两种写法；②句同步限定取该端的备注。
     ⑥ §4 补 `evidenceSource`（题库**预期**的来源标签，不是公司实际持有的材料，不构成证据）
     与 `perceptionGap`（只是线索、绝不能进输出）两条字段说明；`terminatedLevel` 缺失改为结合
     同端分数读（分数也缺 = 无数据，**不得读作已通关**，否则该维会被判无差距、前端渲染成
     绿点 `No Gap`）；删 `\"gsvNote\": null`、`weight` 改 `30.0`（Python 侧 `exclude_none=True`，
     空值是键不出现；DTO 是 float），并说明实际是两个裸数组分开下发、没有外层包裹。
     ⑦ §5 规则 2 的双端处置细化为三类（含「另一端未作答不是分歧」）；规则 1 / 7 / 13 / 14 随
     双端与稀疏 level 口径订正；规则 11 第三条反例去掉 `Top GSV quartile`（并去掉替换后引入的
     `external benchmark` —— 输入里没有任何 benchmark 数据）。⑧ §8 末尾改为一句英文输出约束。"
  - "1.5 (2026-09-20)：**维度级增量生成** —— `dimensions[]` 的语义由「该期次全部 Active 维度」
     收窄为「**本轮要分析的**维度」（某一维双端都提交就单独分析这一维，不必等齐）；新增只读
     输入 `analyzedContext[]`（本期次已分析过的其他维度的结论摘要），**不得为它们产出 gaps /
     actions / index**；`summary` 必须覆盖两者之和（整个期次目前已知的全貌），否则总结读起来
     像是公司只评了本轮这几维。"
  - "1.4 (2026-09-18)：① 每题输入新增 `attachments[{fileName, summary, summaryAvailable}]`（附件
     摘要接进 Goldie，design-doc §5.1）；② `evidenceMissing` 判定由「无备注」改为「无备注**且**
     无可用摘要」（§5.2）；③ 新增摘要使用规则（二手信息不得当原文引用、`summaryAvailable=false`
     不得凭文件名推断）；④ 新增 actions 反套话强约束（把维度名替换掉仍成立的句子一律不合格，
     §5.4-7）；⑤ 输出新增维度级 `narrative`（§5.3）；⑥ 数量约束收紧为 gaps 1-5 条按 severity
     降序、actions 1-3 条。"
  - "1.3 (2026-09-18)：维度标识由 `code` 改为 `index`（1..N，按下发顺序）+ `abbr`，
     `dimension_code` 只在服务端流转、不进 prompt。依据 design-doc §6.6（2026-09-08 裁决，
     理由见该节「为什么不把 dimension_code 送进 LLM」）；Java 侧当时已改，本次补齐 Python 侧。"
  - "1.2 (2026-09-07)：规则 7 的「落到具体的题与**准则**上」改为「题与**作答**上」 —— 
     「准则」是 1.1 删掉的 `criteria` 留下的用词，输入里已无该概念，留着会暗示模型存在准则原文。"
  - "1.1 (2026-09-06)：删除题级 `criteria`（判定标准）的输入示例、字段说明与两处引用规则。
     依据：需求方 2026-09-06 裁决「需求设计不使用该字段」（design-doc §13-Q25 / M11 —— 该字段
     为设计自创、题库只采集题干 / Era Band / Source），Java 侧同步停止下发，不做向后兼容。
     判断依据收敛为：题干 + 逐题 Yes/No + 双端备注 + level 口径。"
  - "1.0：v4.4 单份产物（双 audience 合并）初版。"
---
# Exit Readiness 差距分析（Goldie gap analysis）

> v1.7 起**每次调用只分析一个维度**（任务化，2026-09-24 设计 D6）：平台按维度逐个调用你，
> 你看不到、也不需要该期次的其它维度。产出只有叙述段、差距与建议三类（§0.10-D4），无差距的维度
> 由前端显示 `No Gap`。措辞仍是**单一口吻的一份内容**（v4.4 / §0.10-D3），同时供 GSV 与创始人阅读。

## 1. 角色和任务

你是 Goldie —— Looking Glass 平台(LG)的退出准备度（Exit Readiness Level，ERL）顾问。
给定一家公司在某个期次**某一个维度**的 ERL 评估结果，为这个维度产出：

- `narrative`：该维度的叙述段（**只有存在差距时才产出**）
- `gaps`：与该 level 题目要求之间的实质差距
- `actions`：针对该维度差距的建议动作

产出**只有一套措辞**，同时供 GSV 团队（投资方一侧，在平台管理端独立完成同一套问卷的校验
评估）与创始人阅读 —— GSV 随时可读，创始人在 GSV 点 Share 之后可读，**两端看到的是同一份内容**。

## 2. 计分口径（必读）

**每道题只有 Yes / No 两个取值，题目本身不折算成分数。** 每道题归属**一个** level
（`eraBand`，取值 1–9），该维度**有题的** level 按由低到高逐级解锁（首个可作答的 level
不一定是 1，见本节末尾「level 分布是稀疏的」）：

- 某 level 的**全部题都已作答且全为 Yes** → 该 level 通过（`CLEARED`），解锁下一个**有题的** level；
- 某 level 内**出现任一 No** → 该维度就在此终止，后续 level 不再解锁；
- **维度分（`founderLevelScore` / `gsvLevelScore`）= 该维度最后一个「全部 Yes」的 level**
  （该 level 的题**答满且全是 Yes** 才算通过），取值 **0–9 整数**。出现 No 的 level 记为
  `terminatedLevel`，则**维度分 = 该维度有题的 level 升序列表里 `terminatedLevel` 的前一个**，
  **不是 `terminatedLevel − 1`**（两者只在那一级的上一个有题 level 恰好是 `terminatedLevel − 1`
  时才相等）—— **一律直读输入里的分数，不要自己推算**：某维度只配了 level 3 / 6 / 9 时，
  L3 踩 No → **0**（一级都没通关）、L6 踩 No → **3**、L9 踩 No → **6**。
- **全部已有题的 level 都通过 → 维度分 = 该维度最大的有题 level**，`terminatedLevel` 字段缺失。
  题库配满九级时该值才是 9；某维度最高只配到 level 8，全 Yes 就是 **8 分**，不要按 9 解读。
- **维度分字段缺失 ≠ 0 分**（值为空的键整个不出现，不会是 `null`）：`0` 是「**第一个有题的
  level 内就出现 No、一级都没通关**」这一真实结果；键缺失表示该端对该维**没有可用数据**
  （该维一道题都没有，或该端没有可分析的提交），此时不要臆造该端的判断。
- **解锁 / 通过 / 终止是每一端各算一套**：`founder*` 与 `gsv*` 两条链互不影响，同一维度两端
  可以停在不同 level。上面凡说「该维度终止」，指的都是**某一端**终止。
- **`terminatedLevel` 之后出现的作答不改变维度分**：作答被改过（Yes 改成 No）时，首个 No
  之后仍可能留下已答的行，你会看到止步 level 之后的题标着 `true`。**它们不代表那些 level
  已通过**，维度分只按上面的口径算。

**整体退出准备度按各维权重加权得出**（`weight`，百分比）—— 综合分由平台计算、不需要你算。
本次只分析一个维度，`weight` 只是背景信息，不需要你做任何跨维度的排序或取舍。

**感知差 `perceptionGap` = `founderLevelScore` − `gsvLevelScore`**（两个整数之差；
正数 = 创始人比 GSV 更乐观）。

**level 分布是稀疏的**：输入里的 `eraBand` 只会出现该维度**实际配了题的** level，档位之间
可能有跳空（如 3 → 6 → 9）。**跳空的 level 不代表「未达成」，只代表题库没配题**，
不得据此推断差距。

## 3. 领域常量

- **维度不是固定的一组**：维度集合、名称、权重由平台按期次配置下发，本次输入的是其中**一个**
  维度，展示身份见 `name` / `abbr`，**完全以输入给出的这一个维度为准**。不得引入输入中没有的维度，
  也不得对其它维度做任何推断。
- **9 个 level 分属 3 个 Era**：Founder Era（level 1–3）、Harvest & Growth Era（level 4–6）、
  Exit Era（level 7–9）。维度分为 `0` 表示**一个有题的 level 都没通过**，不归入任何 Era
  （**不等于**「level 1 没做到」—— 该维可能根本没配 level 1 的题）。
- **差距严重度 `severity` 值域固定三选一**：`HIGH` / `MEDIUM` / `LOW`。
  **禁止**输出其它任何取值（不得用 `CRITICAL` / `High` / `中` / 数字等）。

## 4. 输入 (Inputs)

实际下发是**一个裸 JSON 对象**（这个维度本身），`companyId` / `period` 以纯文本行给出（见 §8）。
**值为空的字段整个键都不出现**，不会出现 `null`。

```json
{
  "name": "Financial Readiness",
  "abbr": "FRL",
  "weight": 30.0,
  "founderLevelScore": 2,
  "gsvLevelScore": 4,
  "perceptionGap": -2,
  "founderTerminatedLevel": 3,
  "gsvTerminatedLevel": 5,
  "questions": [
    {
      "questionText": "...",
      "eraBand": 3,
      "eraLabel": "Founder Era - 3",
      "evidenceSource": "Monthly management accounts",
      "founderYesNo": false,
      "gsvYesNo": true,
      "founderNote": "...",
      "attachments": [
        {"fileName": "FY2025-management-accounts.pdf", "summary": "...", "summaryAvailable": true},
        {"fileName": "close-checklist.xlsx", "summaryAvailable": false}
      ]
    }
  ]
}
```

字段说明：

- `name` / `abbr`：该维度的展示名与缩写（如 `Financial Readiness` / `FRL`），供你理解这一维
  谈的是什么；维度集合随平台配置变化，见 §3。
- `founderLevelScore` / `gsvLevelScore`（维度级）：该端的**维度分（0–9 整数 level）**，
  口径见 §2。字段缺失 = 该维无题或该端本期未提交，此时不要臆造该端的判断。
- `founderTerminatedLevel` / `gsvTerminatedLevel`：该端**首次出现 No 的 level**。
  该键缺失要**结合同端的 `*LevelScore` 一起读**：同端分数**有值** = 该端全部有题的 level 都已
  通过（已通关，不必然到 level 9）；同端分数**也缺失** = 该端无数据，**不得读作「已通关」**，
  也不要为该端产出任何判断。
- `weight`：该维在综合分中的权重百分比（`30.0` 表示 30%，可能带小数点），只是背景信息。
- `perceptionGap`：`founderLevelScore − gsvLevelScore`（口径见 §2）。**只是线索，绝不能出现在
  输出里**（公司端看不到它，见 §6 与 §5 规则 9）；两端任一缺失时该键不出现。
- `eraBand` / `eraLabel`：该题所属 level 与其展示名（如 `Founder Era - 3`）。
- `evidenceSource`：题库为该题**预期**的证据来源标签（题目配置，取值形如 `Founder / CFO`、
  `SharePoint`、`Board Transcripts`），**不是公司实际持有的材料**。它**不构成证据**，
  **严禁**据它断言公司有这份东西；它也可能含内部称谓，不得抄进输出。
- `founderYesNo` / `gsvYesNo`：该端对该题的作答（`true` = Yes / `false` = No）。字段缺失 = 该端未作答。
- `founderNote` / `gsvNote`：作答者填的证据/备注。**这是最重要的输入** —— 有备注的题才谈得上
  「有证据支撑的判断」。
- `attachments`：该题上传的证据附件，**空数组 = 该题没有附件**。两端上传的附件已合并去重。
  - `fileName`：附件的原始文件名。
  - `summary`：平台对该附件正文生成的英文摘要（**只有摘要，没有原文**）。字段缺失 = 当前无摘要。
  - `summaryAvailable`：该附件有没有可用摘要。`false` = 摘要生成失败或超时 ——
    此时你**只知道存在一份叫这个名字的文件**，见 §5 规则 6。

## 5. 判断规则（强制）

1. **每道题只有 Yes/No 两个取值；已作答的题都参与该端计分**（某端 `*YesNo` 键缺失 = 该端
   没答这道题，不参与该端计分）。一道题答 No 就意味着该 level 的要求对该端未达成、
   该端到此终止。陈述时说「已具备 / 尚未具备题干描述的做法」，**不得**给单题编造分值、
   也不得说「这题得了几分」（题级分不存在）。
2. **止步 level 内答 No 的那些题，就是该维度最直接的差距来源**。答 No 意味着该题**题干
   描述的做法当前没有做到** —— `gaps` 与 `actions` **必须优先围绕它们**展开，且逐条回指
   具体是哪道题没达成；只有这批题谈完还有余量时，才谈更靠后的观察。
   **两端各有自己的止步 level**（`founderTerminatedLevel` 与 `gsvTerminatedLevel` 常常不同），
   按三类分别处置：
   - **两端都答 No** → 最优先，直陈「这道题描述的做法当前没有做到」；
   - **一端 No、另一端 Yes** → 照样要谈，但只落在题目上（「外部验证尚未确认<题干要点>」），
     **不点名是哪一侧、也不暗示谁更乐观**（见 §6）；只有 `perceptionGap` 明显为正时才可另外
     用规则 9 那句方向性表述；
   - **一端 No、另一端该题 `*YesNo` 键缺失** → 这**不是分歧**，只是另一端还没走到这一级。
     照常把它当差距谈，**严禁**写成「自评与外部验证之间存在落差」。
3. **未作答的题不得编造判断**。输入里带的是该维的全部题目，某端没解锁到的题**没有该端的
   `*YesNo` 键** —— 那是「还没问到」，不是「答了 No」。**严禁**据此推测该端在更高 level 上的
   表现，也不要写「level 7 的要求也没做到」这类没有作答支撑的话。可以说的是「先通过当前
   止步的 level，才谈得上后续 level」。
4. **证据 = 备注 或 可用摘要**。某道题**既没有 note**（`founderNote` 与 `gsvNote` 都为空）
   **又没有可用摘要**（`attachments` 为空，或全部附件 `summaryAvailable: false`）时，你对它只
   知道「答了 Yes/No」这一件事：答 No 照规则 2 当差距谈；答 Yes 则**不得把它当作已具备证据的
   做法来引用**（narrative 的正面证据句也不得取它），措辞上可以指出该做法「尚未有证据支撑」。
   **备注为空但该题有可用摘要时视为有证据**。不确定时按「无证据」处理（宁可少引一条正面证据，
   也不要假装有证据）。
5. **附件摘要是二手信息**。摘要由平台对附件正文自动生成，**不是原文**。它可以用来佐证
   「这件事有没有证据支撑」，也可以用自己的话概括其中的做法，但**不得当作原文引用**
   （不加引号、不写「文件中写道」），更**不得据其编造精确数字、金额、日期或条款原文** ——
   摘要里没有出现的东西，就当它不存在。
6. **`summaryAvailable: false` 时，你只知道存在一份叫这个名字的附件**。
   **严禁凭文件名推断它的内容**（不得因为文件名叫 `audited-financials.pdf` 就认定公司有审计
   报告）。此时该附件不构成证据，按规则 4 处理。
7. **没有实质差距的维度不产出任何条目**：`gaps` / `actions` 返回空数组，`narrative` 省略。
   **严禁**为了凑满结构而编造差距叙述，也不要改写成正面评价来填充 —— 无差距这件事由平台
   渲染为 `No Gap`，不需要你输出任何条目。已通关（分数有值而 `terminatedLevel` 缺失）的维度
   尤其如此。
8. **不要发明输入里没有的事实**。不得虚构财务数字、客户名、合同、人名或日期。所有判断只能
   来自维度分、逐题题干与 Yes/No 作答、双端备注、附件摘要。**输入里没有「判定标准」字段**，
   不得编造某道题「需要做到什么才算 Yes」的标准原文，只能引用题干本身。
9. **感知差是线索不是结论**：`perceptionGap` 明显为正（创始人更乐观）时，可以指出
   「自评与外部验证之间存在落差」，但差距本身仍要落到具体的题与作答上。
10. 某端维度分缺失时，只基于**有值的一端**作答，并在措辞上避免暗示另一端的判断。
11. **`actions` 必须锚定具体事实（反套话强约束）**。每一条建议都要锚定到本维度的**一条具体
    `gap`，或一道具体的 No 题**，并且**把依据写进 `title` 本身**（哪道题没达成、备注里的哪个
    条件、哪份附件摘要里的哪个事实）—— `title` 是唯一会被展示的文字，没有别的字段可以补充依据。
    **判定标准：凡是把维度名替换成任何其它维度后仍然成立的句子，一律不合格。** 下面三条是
    典型的不合格样本，**不得**产出这一类：

    - `Assign an owner and 90-day plan for the highest-severity FRL gap.`
    - `Collect and version the supporting evidence so FRL answers can move from No to Yes.`
    - `Re-score FRL next quarter and track the delta.`

    它们换成任何维度都成立，等于没有信息量。合格的写法必须出现该维输入里的具体事实
    （某道 No 题的题干要点、某条备注里的数字或条件、某份附件摘要里的事实），例如：

    - ✅ `Cut the monthly close from 12 business days to 5 so the level-3 close-timing question can move to Yes.`
      （依据就在句子里：该维 level 3 的「10 个工作日内完成月结」答 No，备注写的是 12 个工作日）

    ⚠️ 这条只是**写法示范**：里面的天数与题目出自举例，**不得照搬进真实输出**，
    每次都要换成本维输入里真实出现过的事实。
12. 数量：有差距时 `gaps` **1–5 条**（按 `severity` 从高到低排列）、`actions` **1–3 条**；
    宁少勿凑数。无差距时两个数组都为空（规则 7）。
13. `severity` 定级口径：`HIGH` = 阻碍解锁下一个**有题的** level 的硬门槛（止步 level 内的 No 题优先
    定为 HIGH）；`MEDIUM` = 影响估值/尽调效率但不致命；`LOW` = 打磨项。

## 6. 措辞（单一口吻）

同一份内容既给 GSV 团队看，也会被分享给创始人，因此用**中立、可执行的第三人称**：
「The company …」「Establish …」「Document …」。不要用 `you` 直呼创始人，也不要用 `we`
自称 GSV 团队。

⚠️ **不得直接引用 GSV 的具体分数**（不得写「GSV rated this company 4」「the GSV score is two
levels lower」这类句子）—— 公司端看不到 GSV 分与 Perception Gap（design-doc §4.3），而本内容
分享后创始人可见。要谈落差时只说「外部验证尚未确认」这类定性表述。

⚠️ **输出里不得出现任何内部称谓**：`GSV` / `Looking Glass` / `LG` / `portfolio` / `管理端` /
`投后` 等一律不写（本提示词里出现它们只是让你理解这份数据是谁填的）。公司端界面从不展示
这些词，创始人在这份分析里读到就是唯一一次 —— 要指代对端的判断时一律用
`external validation` / `the external review` 这类中性说法；输入的**字段名**同样不许露出
（不要写 `the gsvNote says …`）。
这条只禁把它们**用作平台 / 团队 / 角色的指代** —— 若某个**维度名或题干本身**含这些词
（例如维度就叫 `Portfolio Readiness`），照原样引用不算违规。

## 7. 输出格式（严格 JSON）

只输出一个 JSON 对象，**不要**任何解释文字或 markdown 围栏。**全部文案用英文**
（面向用户的产品文案；本提示词为中文仅面向开发）。

```json
{
  "narrative": "...",
  "gaps": [
    {"title": "...", "severity": "HIGH"}
  ],
  "actions": [
    {"title": "..."}
  ]
}
```

约束：

- 顶层**只有** `narrative` / `gaps` / `actions` 三个键，不要输出结构以外的任何键（不要 `summary`、
  不要 `index`、不要 `name` / `abbr`、不要任何维度代码或任务标识）。
- **`gaps` 键必须始终存在**（无差距时是 `[]`）—— 平台以它是否为数组判断输出是否合法，缺了整份判失败。
- `narrative`：该维度的叙述段，**最多 3 句、不超过 60 词**，写成一段连贯的话（不要模板拼接）。
  依次是：① 该维当前的状态 —— **数字只能取 `founderLevelScore`**（另一端的分创始人看不到，
  见 §6），分三种情形：分数与 `founderTerminatedLevel` 都有值 → 写「分数 + 止步在第几级的题
  上」；分数有值而 `founderTerminatedLevel` 缺失（该端已全部通过）→ 只写分数、**不写任何止步
  level**；分数缺失 → **既不写数字也不写任何 level**（更不许借用另一端的），改写一句定性的话。
  ② 该维**在该端已通过的 level 内最有说服力的一条正面证据**（取该端答 Yes 那道题的
  `founderNote` 或该题的附件摘要，**用自己的话转述、不加引号**，不要用另一端的备注）；
  ③ 转折到差距（`but …`），引出下面的 `gaps`。
  ⚠️ **②没有素材时就省略这一句、只写 2 句** —— 该维已通过的题全无备注也无可用摘要、或止步在
  level 1 时就是这种情况，**不得为了凑满三句编一条正面证据**（规则 8）。
  **没有差距时不要输出这个字段** —— 该维由平台渲染为 `No Gap`，没有承载叙述的位置。
- `gaps[].title` / `actions[].title`：一句话（≤ 15 词）。**条目只有标题**，没有 `note` / `why` /
  `evidenceMissing` 这类补充字段 —— 依据要写进标题本身（规则 11）。
- `severity` 只能是 `HIGH` / `MEDIUM` / `LOW`；`gaps` 按 `severity` 从高到低排列。

---

## 8. User Prompt

```text
公司 ID：{{var:company_id}}
期次：{{var:period}}

本次要分析的维度（JSON）：
{{var:dimension_json}}

按系统提示词的规则只为这一个维度产出差距分析。

Output only the JSON object. All text inside it must be in English.
```
````

- [ ] **Step 2: 改 `source/ai/prompts/erl_gap_analysis_prompts.py` 的模块 docstring（原 1-8 行替换为下面 10 行，其余不动）**

```python
"""ERL 差距分析 prompt —— Markdown 加载器外壳。

prompt 正文在 ``erl/erl_gap_analysis.md``；本文件只导出两个常量名。改 prompt 内容只动 .md。

**v1.7（2026-09-24 任务化）**：每次调用只装**一个维度**，user 模板的运行期变量是
``company_id`` / ``period`` / ``dimension_json`` 三个（``dimensions_json`` / ``analyzed_context_json``
已删）；``_md_loader`` 的 ``format`` 是 ``{{var:x}}`` 的 ``str.replace``，少传 key 不抛异常、会把占位符
原样留在 prompt 里发给模型 —— 调用方 ``erl_gap_analysis_service._build_user_prompt`` 三个一个都不能漏。
v4.4 起双 audience 方案取消、只有这一份 prompt（旧 ``gap_analysis.v1.md`` / ``v2.md`` 已删除）。
"""
```

- [ ] **Step 3: 轻量校验——加载器能切出 system / user 两段且三个占位符都在**

```powershell
uv run python -c "import sys; sys.path.insert(0, 'source'); from ai.prompts.erl_gap_analysis_prompts import ERL_GAP_ANALYSIS_SYSTEM_PROMPT as s, ERL_GAP_ANALYSIS_USER_PROMPT as u; t = str(u); assert '{{var:dimension_json}}' in t and '{{var:company_id}}' in t and '{{var:period}}' in t; assert 'analyzed_context' not in t and 'dimensions_json' not in t; assert 'analyzedContext' not in s and '\"summary\"' not in s; print('prompt v1.7 OK', len(s))"
uv run ruff check source/ai/prompts/erl_gap_analysis_prompts.py
```

---

### Task 6: service 原文件内重写 + 删除 Redis 锁

**Files:**
- Modify: `source/erl/application/service/erl_gap_analysis_service.py`（全文替换，原 1061 行）
- Delete: `source/erl/infrastructure/gap_analysis_lock.py`
- Delete: `source/erl/infrastructure/__init__.py`（整个 `source/erl/infrastructure/` 目录随之删除）

- [ ] **Step 1: 全文替换 `source/erl/application/service/erl_gap_analysis_service.py`**

```python
"""ERL 差距分析（Goldie）：**按 Java 维度任务**逐个生成并落库（sprint119 任务化，设计稿 §6）。

Java 持有「报告分享记录 + 按维度任务」的编排状态（PENDING → RUNNING → SUCCESS | FAILED，CAS 更新），
把某公司某期次**本次派发的任务**（一个任务 = 一个维度的双端评估：level 分 + 止步 level + 逐题 Yes/No
与备注 + 附件）同步 HTTP 送进来；本服务对外两个方法：

  - ``refresh(dto, *, user_id)``  批量查日志表 → 已 SUCCESS 的任务直接回状态 → 其余任务：附件按 fileId
    **跨任务去重**现场摘要 → ``Semaphore(3)`` 每任务「单维 prompt → LLM（重试 2 次）→ 解析 → 一个事务写
    日志行 + 条目」→ 逐任务回 ``{taskId, status, hasGap}``。单任务失败只影响它自己（日志行 FAILED、
    不写条目、``hasGap=null``）。
  - ``items(task_ids)``  取日志表 SUCCESS 的任务的条目，按任务分组回 narrative / gaps / actions；
    无条目的任务不出现。

两张表 ``ai_erl_gap_analysis_task``（生成日志 + 幂等标记）/ ``ai_erl_gap_analysis_task_item``（AI 条目）
归 Python（V028）；Python 仍**不查 ERL 评估表、不做公司 ACL**（Java 已校验）。

几条落地口径：

- **没有期次级锁了**（2026-09-24 起）：单派发由 Java 任务表的 CAS 保证；同一任务被双跑时，条目唯一键
  ``uk_ai_erl_gap_analysis_task_item``（或日志行的 ``uk_ai_erl_gap_analysis_task``）让后写的一路撞键
  回滚、**按成功处理**（重查日志行取 has_gap）。原 Redis 锁 ``erl:gapAnalysis:{c}:{p}`` 连同
  ``infrastructure/gap_analysis_lock.py`` 已删除。
- **SUCCESS 是日志表终态**：重投命中 SUCCESS 行直接回 ``has_gap``、不再烧 LLM（Java 500s 读超时 /
  发版重启后按 10 分钟规则重投时靠它省钱）；FAILED 行可被下一次尝试就地更新；仓储的 UPDATE 不命中
  SUCCESS 行，「想覆盖 SUCCESS」会在 commit 时撞唯一约束，由本层决定按成功（成功路径）还是按忽略
  （失败路径）处理。
- **每任务一次 LLM、prompt 只装一个维度**（prompt v1.7）：不再有 index↔code 整批校验、summary、
  analyzedContext、noGapDimensions（零感知差维度 Java 建任务时直接置 SUCCESS/has_gap=false，不派发）。
  ``taskId`` 是 Java 的内部标识，**绝不进 prompt**（同此前 ``code`` 的规则：模型逐字复现无语义串不可靠，
  且它对模型零信息量）。
- **条目一次写入永不改**（设计不变量 I2）：无 UPDATE / DELETE；重跑同一任务只会撞唯一键。
- **附件只进摘要、不进原文**（design-doc §5.1）：摘要现场生成、不落库，按 fileId **跨任务去重**（同一份
  附件挂在两个维度的题上只解析一次），限并发 3 / 单份 90s / 阶段总闸 120s，失败一律
  ``summaryAvailable=false`` 继续；已 SUCCESS 的任务的附件不再解析。
- **severity 值域恒 HIGH/MEDIUM/LOW**：越界归一 MEDIUM 并告警；**无 gaps 时丢 narrative**（前端该维渲染
  ``No Gap``，没有承载叙述的落点）；**输出没有 ``gaps`` 数组 ⇒ 该任务判失败**，绝不把「解析不出」降级
  成「无差距」—— 那个渲染态是绿点 No Gap，是无声的假阴性。
- **出参精简**（决策 D7）：gap 只有 title + severity、action 只有 title；note / why / evidenceMissing /
  summary / generatedAt / model 都不再出站。
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError

from common.enums import CallerAgent, CallerNode
from db import get_session
from llm import Models, TraceContext, llm_db_router, parse_json_response
from llm.infrastructure import AI_REQUEST_TIMEOUT_SECONDS

from ai.prompts.erl_gap_analysis_prompts import (
    ERL_GAP_ANALYSIS_SYSTEM_PROMPT,
    ERL_GAP_ANALYSIS_USER_PROMPT,
)
from erl.application.dto.erl_gap_analysis_dto import (
    GapActionDTO,
    GapAnalysisRefreshInputDTO,
    GapDimensionResultDTO,
    GapItemDTO,
    GapTaskInputDTO,
    GapTaskItemsDTO,
    GapTaskStatusDTO,
)
from erl.domain.enums import GapItemType, GapTaskStatus
from erl.domain.models import ErlGapAnalysisTaskItem
from erl.domain.repository import erl_gap_analysis_task_item_repository as item_repo
from erl.domain.repository import erl_gap_analysis_task_repository as task_repo

logger = logging.getLogger("CIOaaS.erl.erl_gap_analysis_service")

# 输出预算：单个维度 = 1 段 narrative（≤60 词）+ gaps≤5（title ≤15 词 + severity）+ actions≤3，
# 量级在几百 token；4096 是上限不是消耗，留 ~8 倍头寸防 JSON 断在半路整包解析失败。
# 此前 16384 是为「一次调用覆盖 N 个维度 + note/why」留的，任务化后每任务只装一个维度。
# ⚠️ 仍是估算——上线后按 ai_llm_call_log 的 usage_output_tokens 与 finish_reason 复核。
_MAX_TOKENS = 4096

# 叙述类生成：全 0 会让措辞高度雷同，给一点点温度换可读性；不设更高是因为事实判断必须稳定
# （同一份输入两次生成不该在「有没有这个差距」上翻转）。
_TEMPERATURE = 0.2

_MODEL = Models.openrouter.text.sonnet

_SEVERITIES: frozenset[str] = frozenset({"HIGH", "MEDIUM", "LOW"})
_DEFAULT_SEVERITY = "MEDIUM"

# 条目 content 的落库预算（ai_erl_gap_analysis_task_item.content varchar(1024)，见 V028）。
# 超长不是异常：模型偶尔多写两句，截断后仍是可读内容，比整份写库失败（DataError）划算。
_MAX_CONTENT_CHARS = 1024

# LLM 失败重试：额外 2 次，指数退避 2s / 4s。**这是本链路唯一一层重试**：``_call_llm`` 显式把 SDK 的
# 传输级 ``max_retries`` 关成 0，否则两层叠乘（3 × 4 × 120s ≈ 1440s）。
# 单任务最坏 = 3 × AI_REQUEST_TIMEOUT_SECONDS(120s) + 2s + 4s = 366s。没有锁 TTL 要对齐了，但 Java 侧
# refresh 的读超时是 500s：多任务时 ``_TASK_CONCURRENCY`` 分批，整轮可能超过 500s —— 这是设计接受的
# （Java 留 RUNNING、10 分钟后重投，重投命中 SUCCESS 日志直接回、不重复烧 LLM，设计 §8）。
_LLM_RETRY_BACKOFF_SECONDS = (2.0, 4.0)

# 一轮 refresh 内同时在跑的 LLM 任务数（设计 D6：并发 3）。信号量必须在**当前事件循环**里建，
# 不能提到模块级（那时通常还没有循环）。
_TASK_CONCURRENCY = 3

# 单份附件的摘要预算（下载 + 解析 + 一次摘要 LLM），到点即按「无摘要」继续。
# ⚠️ 90 不是随手取的整数：ERL 要的证据恰恰是财报 / 管理账 / 审计包这类多页 PDF，152 页 PDF 实测光文本
# 抽取就 53.5s，再加下载与一次摘要 LLM —— 给 60s 等于「这类文件永远出不了摘要」。
_ATTACHMENT_SUMMARY_TIMEOUT_SECONDS = 90.0

# 摘要阶段的**并发上限**。需求方明确「不限制附件数量」，但并发必须限：rag 的 loader 走
# ``asyncio.to_thread``，用的是**全进程共享**的默认线程池（2 vCPU 容器只有 6 个线程），不限并发的话
# 一次十来份 PDF 就能把池占满几十秒，整个进程的 DB 调用跟着排队 —— 拖死的是别人的请求。
_ATTACHMENT_SUMMARY_CONCURRENCY = 3

# 摘要阶段的**总预算**（不是单份的）：加了并发闸之后附件数会真实影响墙钟，必须另有一个与附件数无关
# 的总闸；到点未完成的附件按「无摘要」继续。120s ≈ 1 批满并发跑满单份预算后还留一点余量。
_ATTACHMENT_SUMMARY_STAGE_TIMEOUT_SECONDS = 120.0

# 渲染 prompt 时剔除的字段：
#   - ``task_id``：Java 任务 id，只用于落库与回状态，模型见了既无从判断、又会诱它复述无语义串；
#   - ``file_id``：服务端取摘要用的内部标识，同理。
_PROMPT_EXCLUDE = {
    "task_id": True,
    "questions": {"__all__": {"attachments": {"__all__": {"file_id"}}}},
}


async def refresh(dto: GapAnalysisRefreshInputDTO, *, user_id: str) -> list[GapTaskStatusDTO]:
    """按任务生成并落库，逐任务回状态（契约 §6.1）；返回顺序 = 入参 ``tasks`` 顺序、一个不少。

    一轮的全部步骤平铺在这里（读主方法即懂全流程）：批量查日志表 → 已 SUCCESS 的短路 → 其余任务
    的附件摘要（跨任务去重）→ 信号量并发逐任务跑 → 按入参顺序汇总。单任务的失败在 ``_run_task``
    内收口成 FAILED，本方法不因某个任务而抛；查日志表本身失败（DB 不可用）才上抛 ⇒ 500。

    ``tasks`` 非空 / ``task_id`` 唯一由 Request VO 在边界上 422，这里不重复校验。
    ``user_id`` 是触发这次派发的用户（Java 转发 Bearer、路由由 ``ctx.user_id`` 取），落日志行与条目的
    ``created_by`` / ``updated_by``；不进 prompt。
    """
    task_ids = [task.task_id for task in dto.tasks]
    succeeded = await asyncio.to_thread(_load_succeeded, task_ids)
    pending = [task for task in dto.tasks if task.task_id not in succeeded]
    if succeeded:
        logger.info(
            "ERL 差距分析 %d/%d 个任务已有 SUCCESS 日志，直接回状态不再生成（company=%s, period=%s, tasks=%s）",
            len(succeeded), len(task_ids), dto.company_id, dto.period, sorted(succeeded),
        )

    ran: dict[str, GapTaskStatusDTO] = {}
    if pending:
        await _fill_attachment_summaries(pending, company_id=dto.company_id, period=dto.period)
        semaphore = asyncio.Semaphore(_TASK_CONCURRENCY)
        results = await asyncio.gather(*(
            _run_task(task, company_id=dto.company_id, period=dto.period,
                      semaphore=semaphore, user_id=user_id)
            for task in pending
        ))
        ran = {status.task_id: status for status in results}

    statuses = [
        ran[task.task_id] if task.task_id in ran
        else GapTaskStatusDTO(task_id=task.task_id, status=GapTaskStatus.SUCCESS.value,
                              has_gap=succeeded[task.task_id])
        for task in dto.tasks
    ]
    failed = [s.task_id for s in statuses if s.status == GapTaskStatus.FAILED.value]
    logger.info(
        "ERL 差距分析本轮完成（company=%s, period=%s, tasks=%d, ran=%d, failed=%s）",
        dto.company_id, dto.period, len(statuses), len(pending), failed,
    )
    return statuses


async def items(task_ids: list[str]) -> list[GapTaskItemsDTO]:
    """取已 SUCCESS 任务的条目、按任务分组（契约 §6.2）。无条目的任务不出现（含 has_gap=false 的）。

    非空 / 去重由 Request VO 承担；这里收到空列表只会得到空结果（仓储对空 id 列表不发 SQL）。
    """
    return await asyncio.to_thread(_load_items, task_ids)


# ---------------------------------------------------------------------------
# 单任务生成
# ---------------------------------------------------------------------------


async def _run_task(task: GapTaskInputDTO, *, company_id: str, period: str,
                    semaphore: asyncio.Semaphore, user_id: str) -> GapTaskStatusDTO:
    """一个任务：组 prompt → LLM（重试）→ 解析 → 一个事务落日志行 + 条目。**永不抛**（CancelledError 除外）。

    任何失败（LLM / 解析 / 落库）都收口成 FAILED：写一行 FAILED 日志（不写条目）并回 ``has_gap=None``，
    让 Java 按自愈规则重投；其它任务不受影响。``except Exception`` 放过 ``CancelledError``
    （BaseException）—— uvicorn 关停时取消必须真正传播下去。
    """
    async with semaphore:
        try:
            user_prompt = _build_user_prompt(task, company_id=company_id, period=period)
            raw = await _call_llm_with_retry(user_prompt, company_id=company_id, period=period,
                                             task_id=task.task_id)
            result = _parse_dimension(raw, task_id=task.task_id)
            has_gap = await asyncio.to_thread(_persist_success, task.task_id, result, user_id)
        except Exception as exc:  # noqa: BLE001 — 单任务失败不能掀翻整轮
            logger.error(
                "ERL 差距分析任务失败，记 FAILED（company=%s, period=%s, task=%s, abbr=%s）: %s",
                company_id, period, task.task_id, task.abbr, exc, exc_info=True,
            )
            await asyncio.to_thread(_persist_failure, task.task_id, user_id)
            return GapTaskStatusDTO(task_id=task.task_id, status=GapTaskStatus.FAILED.value,
                                    has_gap=None)
    logger.info(
        "ERL 差距分析任务完成（company=%s, period=%s, task=%s, abbr=%s, hasGap=%s, gaps=%d, actions=%d）",
        company_id, period, task.task_id, task.abbr, has_gap, len(result.gaps), len(result.actions),
    )
    return GapTaskStatusDTO(task_id=task.task_id, status=GapTaskStatus.SUCCESS.value, has_gap=has_gap)


def _build_user_prompt(task: GapTaskInputDTO, *, company_id: str, period: str) -> str:
    """单任务 DTO → user prompt（维度按 Java 契约的 camelCase 键序列化给模型）。

    ``exclude_none`` 是 token 预算：一份题目 8 个字段里常有 3-4 个为空。缺字段 = 该项无值，
    提示词 §4 已说明。另剔 ``task_id`` 与附件项的 ``file_id``（见 ``_PROMPT_EXCLUDE``）。

    ⚠️ **三个变量一个都不能漏传**：``_md_loader`` 的 ``format`` 是 ``{{var:x}}`` 的 ``str.replace``，
    少传 key 不抛异常、会把占位符原样留在 prompt 里发给模型。
    """
    dimension_json = json.dumps(
        task.model_dump(by_alias=True, exclude_none=True, exclude=_PROMPT_EXCLUDE),
        ensure_ascii=False,
    )
    return ERL_GAP_ANALYSIS_USER_PROMPT.format(
        company_id=company_id,
        period=period,
        dimension_json=dimension_json,
    )


async def _call_llm_with_retry(user_prompt: str, *, company_id: str, period: str,
                               task_id: str) -> str:
    """调 LLM，失败额外重试 2 次（指数退避 2s / 4s）。

    重试放在**解析之前**：解析失败属于内容不合法，重跑一轮同样的输入大概率还是同样的结果，
    白等 6 秒不如早点记 FAILED 交给 Java 的自愈重投。
    """
    attempts = len(_LLM_RETRY_BACKOFF_SECONDS) + 1
    for attempt in range(attempts):
        try:
            return await _call_llm(user_prompt, company_id=company_id)
        except RuntimeError:
            if attempt == attempts - 1:
                raise
            backoff = _LLM_RETRY_BACKOFF_SECONDS[attempt]
            logger.warning(
                "ERL 差距分析 LLM 调用失败，%.0fs 后重试（company=%s, period=%s, task=%s, 第 %d/%d 次）",
                backoff, company_id, period, task_id, attempt + 1, attempts,
            )
            await asyncio.sleep(backoff)
    raise RuntimeError("gap analysis LLM call failed")  # 循环必然 return/raise，此行只为类型收敛


async def _call_llm(user_prompt: str, *, company_id: str) -> str:
    """调 LLM 取原始文本。超时 / 重试按 coding.md §10；失败上抛 RuntimeError 由 ``_run_task`` 记 FAILED。"""
    messages = [
        {"role": "system", "content": ERL_GAP_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    try:
        result = await llm_db_router.acomplete(
            messages,
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            json_mode=True,
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
            # 重试由本模块显式控制（``_call_llm_with_retry`` 指数退避），不叠加 SDK 传输级重试：
            # router 的 max_retries 是 OpenAI SDK 的「初次 + N 次」，传 3 就是 4 次 × 120s，再乘外层 3 次
            # ⇒ 单任务最坏约 1440s。
            max_retries=0,
            trace=TraceContext(
                agent=CallerAgent.ERL,
                node=CallerNode.ERL_GAP_ANALYSIS,
                company_id=company_id,
            ),
        )
    except Exception as exc:
        logger.error("ERL 差距分析 LLM 调用失败（company=%s）: %s", company_id, exc, exc_info=True)
        raise RuntimeError("gap analysis LLM call failed") from exc
    content = getattr(result, "content", None) or ""
    if not content.strip():
        raise RuntimeError("gap analysis LLM returned empty content")
    return content


def _parse_dimension(raw: str, *, task_id: str) -> GapDimensionResultDTO:
    """模型输出 → 单维结果 DTO（严禁 ``json.loads`` 裸解析；容错剥围栏 / 修残缺走 parse_json_response）。

    **结构层不容错**：不是对象、或没有 ``gaps`` 数组 ⇒ RuntimeError（该任务 FAILED，Java 重投）。
    绝不把「解析不出」降级成「无差距」—— 那个渲染态是绿点 No Gap，GSV 会以为该维没问题并照常 Share
    给创始人，是全程无日志无告警的假阴性。**条目层容错**：无 title 的条目丢弃；severity 越界归一；
    无 gaps 时丢 narrative（前端该维渲染 No Gap、没有承载叙述的落点）。
    """
    payload = parse_json_response(raw)
    if not isinstance(payload, dict):
        logger.error("ERL 差距分析任务 %s 的输出无法解析为 JSON: %r", task_id, raw[:500])
        raise RuntimeError("gap analysis output is not valid JSON")
    raw_gaps = payload.get("gaps")
    if not isinstance(raw_gaps, list):
        logger.error("ERL 差距分析任务 %s 的输出没有 gaps 数组（keys=%s）", task_id, sorted(payload))
        raise RuntimeError("gap analysis output has no gaps array")

    gaps = [
        GapItemDTO(title=str(g.get("title") or "").strip(),
                   severity=_normalize_severity(g.get("severity")))
        for g in raw_gaps
        if isinstance(g, dict) and str(g.get("title") or "").strip()
    ]
    raw_actions = payload.get("actions")
    actions = [
        GapActionDTO(title=str(a.get("title") or "").strip())
        for a in (raw_actions if isinstance(raw_actions, list) else [])
        if isinstance(a, dict) and str(a.get("title") or "").strip()
    ]
    raw_narrative = payload.get("narrative")
    if raw_narrative is not None and not isinstance(raw_narrative, str):
        # 模型偶发回 dict / list，``str()`` 会把 Python repr 一路落进 content 并渲染给用户 —— 宁可没有叙述段。
        logger.warning("ERL 差距分析任务 %s 的 narrative 不是字符串（%s），已丢弃",
                       task_id, type(raw_narrative).__name__)
        raw_narrative = None
    narrative = (raw_narrative or "").strip()
    if narrative and not gaps:
        logger.warning(
            "ERL 差距分析任务 %s 无差距却返回了 narrative，已丢弃（模型回的 gaps 条数=%d，"
            "若非 0 则是这些条目都缺 title 被过滤光了）",
            task_id, len(raw_gaps),
        )
        narrative = ""
    return GapDimensionResultDTO(narrative=narrative or None, gaps=gaps, actions=actions)


def _normalize_severity(value: object) -> str:
    """severity 归一到 HIGH/MEDIUM/LOW；越界值降级 MEDIUM 并告警（提示词已约束，越界=模型跑偏）。"""
    normalized = str(value or "").strip().upper()
    if normalized in _SEVERITIES:
        return normalized
    logger.warning("ERL 差距分析返回越界 severity=%r，降级为 %s", value, _DEFAULT_SEVERITY)
    return _DEFAULT_SEVERITY


# ---------------------------------------------------------------------------
# 附件摘要（现场生成、不落库；跨任务按 fileId 去重）
# ---------------------------------------------------------------------------


async def _fill_attachment_summaries(tasks: list[GapTaskInputDTO], *, company_id: str,
                                     period: str) -> None:
    """现场解析每份附件并生成摘要，就地回填到**所有任务**的附件项（design-doc §5.1）。

    **摘要不落库**：每轮 refresh 现场下载 + 解析 + 一次摘要 LLM、用完即弃。**按 fileId 跨任务去重**：
    同一份文件可能挂在多个维度、多道题上（两端各传过一次、或不同题引用同一份），一份文件只解析一次，
    回填时按 fileId 摊回到每个附件项上。

    **限并发（不限数量）+ 每份独立超时 + 阶段总闸**（三个常量的理由见各自定义处）：净效果是墙钟上界
    恒为 ``_ATTACHMENT_SUMMARY_STAGE_TIMEOUT_SECONDS``、与附件数无关。

    **任何一份失败都不阻断分析**：下载失败 / 类型不受支持 / 解析为空 / 扫描件无文字层 / 超时，一律
    降级为 ``summary_available=False`` 继续 —— 提示词 §5 已约束模型此时不得凭文件名臆测内容。

    作用域由上游保证，本方法不校验：Java 侧已做公司 ACL，``fileId`` 来自该公司该期次的作答行。
    """
    attachments = [a for t in tasks for q in t.questions for a in q.attachments]
    names_by_file_id: dict[str, Optional[str]] = {}
    for attachment in attachments:
        if attachment.file_id and attachment.file_id not in names_by_file_id:
            names_by_file_id[attachment.file_id] = attachment.file_name
    if not names_by_file_id:
        return

    semaphore = asyncio.Semaphore(_ATTACHMENT_SUMMARY_CONCURRENCY)

    async def _guarded(file_id: str) -> Optional[str]:
        async with semaphore:
            return await _summarize_attachment(file_id, names_by_file_id[file_id],
                                               company_id=company_id, period=period)

    file_ids = list(names_by_file_id)
    pending = {file_id: asyncio.create_task(_guarded(file_id)) for file_id in file_ids}
    try:
        await asyncio.wait(pending.values(), timeout=_ATTACHMENT_SUMMARY_STAGE_TIMEOUT_SECONDS)
    finally:
        # 到点未完成的一律取消，并**等取消落定**再走：不等的话它们会变成孤儿任务，在本轮早已交卷
        # 之后继续下载、继续占线程（整轮被外部取消时同理）。
        for task in pending.values():
            if not task.done():
                task.cancel()
        await asyncio.gather(*pending.values(), return_exceptions=True)

    summaries: dict[str, Optional[str]] = {}
    unfinished: list[str] = []
    for file_id, task in pending.items():
        if task.cancelled():
            unfinished.append(file_id)
            continue
        # ``_summarize_attachment`` 自己收口了全部 Exception，这里只可能拿到 None 或摘要；
        # 仍判一次 exception() 是防它日后被改坏时静默变成"全部无摘要"。
        error = task.exception()
        if error is not None:
            logger.error("ERL 差距分析附件 %s 摘要任务异常退出（company=%s, period=%s）: %s",
                         file_id, company_id, period, error, exc_info=error)
            continue
        summaries[file_id] = task.result()
    if unfinished:
        logger.warning(
            "ERL 差距分析附件摘要阶段超时 %.0fs，%d/%d 份未完成按无摘要继续（company=%s, period=%s, files=%s）",
            _ATTACHMENT_SUMMARY_STAGE_TIMEOUT_SECONDS, len(unfinished), len(file_ids),
            company_id, period, unfinished,
        )

    for attachment in attachments:
        summary = summaries.get(attachment.file_id)
        attachment.summary = summary
        attachment.summary_available = bool(summary)

    missing = sum(1 for file_id in file_ids if not summaries.get(file_id))
    if missing:
        # WARNING 而非 INFO：送进模型的证据被削弱了，属于分析质量下降、不是常态流水账。
        logger.warning(
            "ERL 差距分析有 %d/%d 份附件无可用摘要（company=%s, period=%s），按无摘要继续",
            missing, len(file_ids), company_id, period,
        )


async def _summarize_attachment(file_id: str, file_name: Optional[str], *, company_id: str,
                                period: str) -> Optional[str]:
    """一份附件：下载 → 解析 → 摘要，全程不落库；**失败一律返回 None**，由调用方降级。

    ⚠️ 收口的是 ``Exception``，**``CancelledError`` 照常穿透**（它继承 ``BaseException``）——
    阶段总闸取消本任务、或整轮被取消时，必须让取消真正传播下去，否则取消不掉。
    """
    if not file_name:
        # files 行已被清理。没有文件名就定不了用哪个 loader —— rag 侧按扩展名分发，空名字连类型白名单
        # 都过不了。
        logger.warning("ERL 差距分析跳过附件 %s：无文件名，无法确定解析格式", file_id)
        return None

    try:
        # 函数内延迟导入：``rag`` 包的 __init__ 有路由聚合与 llm re-export 副作用，上提到模块顶层会把它
        # 拖进 erl 的导入链（单测也专门 stub 了 rag）。放在 try **内**：导入失败也只让这一份附件降级。
        from rag.application.service.ingest_service import get_ingest_service

        summary = await asyncio.wait_for(
            get_ingest_service().summarize_file_inline(file_id=file_id, title=file_name),
            timeout=_ATTACHMENT_SUMMARY_TIMEOUT_SECONDS,
        )
        # 归一成「非空摘要或 None」：调用方按 ``bool(summary)`` 判可用，而空白串是 truthy。
        return (summary or "").strip() or None
    except asyncio.TimeoutError:
        # 超时是设计内的降级路径（坏文件 / 超大 PDF），记 WARNING 不记 ERROR。措辞刻意不写死"到了 90s"：
        # Py3.11 起 ``asyncio.TimeoutError is TimeoutError``，底层冒上来的 socket 超时也会落进这一支。
        logger.warning(
            "ERL 差距分析附件 %s（%s）摘要超时（本函数预算 %.0fs），按无摘要继续（company=%s, period=%s）",
            file_id, file_name, _ATTACHMENT_SUMMARY_TIMEOUT_SECONDS, company_id, period,
        )
        return None
    except Exception as exc:  # noqa: BLE001 — 摘要是增量信息，失败就按无摘要分析
        logger.error(
            "ERL 差距分析附件 %s（%s）摘要失败，按无摘要继续（company=%s, period=%s）: %s",
            file_id, file_name, company_id, period, exc, exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# 落库（事务边界在本层：开 session、传给 repository、统一 commit，§1.4/§1.5）
# 同步函数（内部是同步 SQLAlchemy），async 调用方用 ``asyncio.to_thread`` 包装。
# ---------------------------------------------------------------------------


def _load_succeeded(task_ids: list[str]) -> dict[str, bool]:
    """批量查日志表，返回 ``{task_id: has_gap}``（只含 SUCCESS 行）—— refresh 开头的幂等短路。

    一次 IN 查询而不是每任务一查（coding.md §6 禁双重循环调 DB）。
    """
    with get_session() as session:
        rows = task_repo.find_by_task_ids(session, task_ids)
    return {row.task_id: bool(row.has_gap) for row in rows
            if row.status == GapTaskStatus.SUCCESS.value}


def _persist_success(task_id: str, result: GapDimensionResultDTO, user_id: str) -> bool:
    """一个事务：upsert 日志行（SUCCESS + has_gap + model）+ 插条目；返回落库的 has_gap。

    **撞唯一键按成功处理**（设计 §6.1-5 / §8）：同一任务被双跑时，后提交的一路会在 commit 时撞
    ``uk_ai_erl_gap_analysis_task_item``（或日志行的 ``uk_ai_erl_gap_analysis_task`` —— 两路都判「无行」
    各自 INSERT，或先到者已 SUCCESS 而仓储的 UPDATE 不命中终态行、落到 INSERT）。回滚后重查日志行：
    已有 SUCCESS 行 ⇒ 先到者赢，取它的 has_gap 回状态；没有 ⇒ 不是双跑而是真异常，上抛让
    ``_run_task`` 记 FAILED。

    ⚠️ try 要罩住写库几步一起，不能只罩 commit：add_all 之后任何触发 autoflush 的语句都可能在 commit
    之前就把 INSERT 发出去。
    """
    has_gap = bool(result.gaps)
    with get_session() as session:
        try:
            task_repo.upsert_by_task_id(session, task_id=task_id, status=GapTaskStatus.SUCCESS.value,
                                        has_gap=has_gap, model=_MODEL, user_id=user_id)
            item_repo.bulk_insert(session, _build_items(task_id, result, user_id))
            session.commit()
            return has_gap
        except IntegrityError:
            session.rollback()
            winner = next(iter(task_repo.find_by_task_ids(session, [task_id])), None)
            if winner is None or winner.status != GapTaskStatus.SUCCESS.value:
                raise
            logger.info("ERL 差距分析任务 %s 双跑撞唯一键，按先到者的结果处理（hasGap=%s）",
                        task_id, winner.has_gap)
            return bool(winner.has_gap)


def _persist_failure(task_id: str, user_id: str) -> None:
    """写一行 FAILED 日志（不写条目）。**自身绝不抛**：它已经在失败路径里，再抛只会把「记不下失败」
    升级成整轮 500，还连累同轮其它任务。

    撞唯一键 = 这个任务在另一路已经 SUCCESS（仓储的 UPDATE 不命中终态行 ⇒ 落到 INSERT ⇒ 撞
    ``uk_ai_erl_gap_analysis_task``），本次失败记录作废：Java 下次重投会命中 SUCCESS 日志直接回状态。
    """
    try:
        with get_session() as session:
            try:
                task_repo.upsert_by_task_id(session, task_id=task_id,
                                            status=GapTaskStatus.FAILED.value, has_gap=None,
                                            model=_MODEL, user_id=user_id)
                session.commit()
            except IntegrityError:
                session.rollback()
                logger.info("ERL 差距分析任务 %s 已在另一路 SUCCESS，本次 FAILED 记录作废", task_id)
    except Exception:  # noqa: BLE001 — 失败路径里的失败只记日志
        logger.error("ERL 差距分析任务 %s 的 FAILED 日志写入失败", task_id, exc_info=True)


def _build_items(task_id: str, result: GapDimensionResultDTO,
                 user_id: str) -> list[ErlGapAnalysisTaskItem]:
    """单维结果 → 条目行。三类条目的落库口径（与 V028 表注释一致）：

    - ``NARRATIVE``：至多一行，``sort_order`` 0，``severity`` 空；只有有 gaps 时才存在（解析层已保证）；
    - ``GAP``：``severity`` 已归一，``sort_order`` 自 0 递增（模型已按严重度降序）；
    - ``ACTION``：``severity`` 空，``sort_order`` 自 0 递增。

    ``content`` 一律按列宽截断；``id`` 显式生成、不靠 flush。
    """
    rows: list[ErlGapAnalysisTaskItem] = []
    if result.narrative:
        rows.append(ErlGapAnalysisTaskItem(
            id=str(uuid.uuid4()), task_id=task_id, item_type=GapItemType.NARRATIVE.value,
            content=_truncate(result.narrative), severity=None, sort_order=0,
            created_by=user_id, updated_by=user_id))
    for order, gap in enumerate(result.gaps):
        rows.append(ErlGapAnalysisTaskItem(
            id=str(uuid.uuid4()), task_id=task_id, item_type=GapItemType.GAP.value,
            content=_truncate(gap.title), severity=gap.severity, sort_order=order,
            created_by=user_id, updated_by=user_id))
    for order, action in enumerate(result.actions):
        rows.append(ErlGapAnalysisTaskItem(
            id=str(uuid.uuid4()), task_id=task_id, item_type=GapItemType.ACTION.value,
            content=_truncate(action.title), severity=None, sort_order=order,
            created_by=user_id, updated_by=user_id))
    return rows


def _load_items(task_ids: list[str]) -> list[GapTaskItemsDTO]:
    """读 SUCCESS 任务的条目并按任务分组（同步，供 ``items`` 调用）。

    先查日志表圈出 SUCCESS 的任务再取条目：条目与 SUCCESS 行同事务写入且 SUCCESS 永不被覆盖，
    故「有条目必有 SUCCESS 行」；反向多这一道过滤是契约 §6.2 的口径，也防将来有人放宽终态守卫。
    分组顺序 = 条目读序（按 task_id 排序），Java 按 taskId 对号、不依赖顺序。
    """
    with get_session() as session:
        rows = task_repo.find_by_task_ids(session, task_ids)
        success_ids = [row.task_id for row in rows if row.status == GapTaskStatus.SUCCESS.value]
        item_rows = item_repo.find_by_task_ids(session, success_ids)
    grouped: dict[str, GapTaskItemsDTO] = {}
    for item in item_rows:
        group = grouped.setdefault(item.task_id, GapTaskItemsDTO(task_id=item.task_id))
        if item.item_type == GapItemType.NARRATIVE.value:
            group.narrative = item.content
        elif item.item_type == GapItemType.GAP.value:
            group.gaps.append(GapItemDTO(title=item.content,
                                         severity=item.severity or _DEFAULT_SEVERITY))
        elif item.item_type == GapItemType.ACTION.value:
            group.actions.append(GapActionDTO(title=item.content))
    return list(grouped.values())


def _truncate(value: str, limit: int = _MAX_CONTENT_CHARS) -> str:
    """按列宽截断。超长是模型多写了两句，截断后仍可读，不值得整份写库失败。"""
    return value if len(value) <= limit else value[:limit]


__all__ = ["refresh", "items"]
```

- [ ] **Step 2: 删除 Redis 锁及其空包**

```powershell
Remove-Item -Force source/erl/infrastructure/gap_analysis_lock.py
Remove-Item -Recurse -Force source/erl/infrastructure
```

（Git Bash：`rm -f source/erl/infrastructure/gap_analysis_lock.py && rm -rf source/erl/infrastructure`。）删除后 `grep -rn "gap_analysis_lock\|erl.infrastructure" source/ tests/` 只应剩旧测试文件 `tests/erl/test_erl_gap_analysis_service.py` 的引用——Task 8 重写它。

- [ ] **Step 3: 轻量校验**

```powershell
uv run python -m py_compile source/erl/application/service/erl_gap_analysis_service.py
uv run ruff check source/erl/application
```

---

### Task 7: Request / Response VO + 路由重写，包 docstring 与挂载注释改口

**Files:**
- Modify: `source/erl/interfaces/vo/request.py`（全文替换，原 236 行）
- Modify: `source/erl/interfaces/vo/response.py`（全文替换，原 133 行）
- Modify: `source/erl/interfaces/routes.py`（全文替换，原 99 行）
- Modify: `source/erl/__init__.py`（全文替换，原 24 行）
- Modify: `source/main.py`（第 90-92 行注释）

- [ ] **Step 1: 全文替换 `source/erl/interfaces/vo/request.py`**

```python
"""ERL 内部接口 Request VO（Java **内网直连、不经网关**调用，非前端可达；JSON key lowerCamelCase）。

契约见设计稿 `2026-09-24-erl-gap-analysis-task-model-design.md` §6.1（refresh）/ §6.2（items）。
入参错误一律在这里 422（pydantic 原生，FastAPI 默认信封 ``{"detail": [...]}``），service 不重复校验。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

# Java 任务 id 的落库列宽（ai_erl_gap_analysis_task.erl_gap_analysis_dimension_task_id varchar(36)，
# 见 V028）。超长在这里 422 而不是落库时 DataError —— 后者是裸 500，且已经白烧了一次 LLM。
_MAX_TASK_ID_CHARS = 36


class GapAttachment(BaseModel):
    """一道题上传的证据附件（Java 只送标识与文件名，摘要由 Python 侧现场生成，design-doc §5.1）。"""

    fileId: str = Field(..., description="附件 fileId（files.id），服务端据此取摘要，不进 prompt")
    fileName: Optional[str] = Field(None, description="附件原始文件名（files.original_name）")


class GapQuestion(BaseModel):
    """逐题作答快照（v4.0：全部题恒 Yes/No，每题归属一个 level）。结构与任务化前完全一致。"""

    questionText: str = Field(..., description="题干")
    eraBand: Optional[int] = Field(None, description="题目所属 level 1-9（逐级解锁的级次）")
    eraLabel: Optional[str] = Field(None, description="Era-level 展示名，如 'Founder Era - 1'")
    evidenceSource: Optional[str] = Field(None, description="证据来源说明")
    founderYesNo: Optional[bool] = Field(None, description="创始人端作答 Yes/No，未作答为空")
    gsvYesNo: Optional[bool] = Field(None, description="GSV 端作答 Yes/No，未作答为空")
    founderNote: Optional[str] = Field(None, description="创始人端证据/备注")
    gsvNote: Optional[str] = Field(None, description="GSV 端证据/备注")
    attachments: list[GapAttachment] = Field(
        default_factory=list, description="该题的证据附件（两端合并下发；无附件为空数组）",
    )


class GapTaskRequest(BaseModel):
    """一个 Java 维度任务的输入：任务 id + 该维双端 level 分 + 止步 level + 权重 + 已解锁题目作答。

    ``taskId`` 是 Java ``erl_gap_analysis_dimension_task.id``，**仅供落库与回状态、绝不进 prompt**
    （service ``_PROMPT_EXCLUDE`` 剔除）；维度身份给模型看的是 ``name`` / ``abbr``。
    维度代码 / 提交指纹 / index 都不再下发（Java 持有编排状态，Python 只按任务 id 落 AI 内容）。
    """

    taskId: str = Field(..., description="Java erl_gap_analysis_dimension_task.id（≤36 字符，非空，本请求内唯一）")
    name: Optional[str] = Field(None, description="维度展示名")
    abbr: Optional[str] = Field(None, description="维度展示缩写，与 name 一起给模型人类可读的维度身份")
    weight: Optional[float] = Field(None, description="该维在综合分中的权重百分比 0-100")
    founderLevelScore: Optional[int] = Field(
        None, description="创始人端维度分 0-9（最后一个整级全 Yes 通关的 level）；该维 0 题为空",
    )
    gsvLevelScore: Optional[int] = Field(
        None, description="GSV 端维度分 0-9（最后一个整级全 Yes 通关的 level）；该维 0 题为空",
    )
    perceptionGap: Optional[int] = Field(
        None, description="founderLevelScore - gsvLevelScore（两整数之差）",
    )
    founderTerminatedLevel: Optional[int] = Field(
        None, description="创始人端首次出现 No 的 level 1-9；全部有题 level 都通过时为空",
    )
    gsvTerminatedLevel: Optional[int] = Field(
        None, description="GSV 端首次出现 No 的 level 1-9；全部有题 level 都通过时为空",
    )
    questions: list[GapQuestion] = Field(default_factory=list, description="该维已解锁题目作答")


class GapAnalysisRefreshRequest(BaseModel):
    """`POST /api/ai/erl/gap-analysis/refresh` 入参（契约 §6.1）。

    ``tasks[]`` = Java 本次派发的 **RUNNING** 任务（已 SUCCESS 的任务 Java 不会再送；送了 Python 也会按
    日志表直接回状态）。``companyId`` / ``period`` 只进 prompt 与日志。
    """

    companyId: str = Field(..., description="公司 ID（ACL 在 Java 侧，Python 不做；只进 prompt 与日志）")
    period: str = Field(..., description="评估期次，形如 2026Q3（Java 侧 erl_assessment.period 的口径）")
    tasks: list[GapTaskRequest] = Field(default_factory=list, description="本次派发的维度任务，非空")

    @model_validator(mode="after")
    def _check_tasks(self) -> GapAnalysisRefreshRequest:
        """整包边界校验：``tasks`` 非空 + ``taskId`` 非空、≤ 36 字符、两两不同（契约 §6.1 步骤 1，422）。

        - **``taskId`` 重复**：两个任务共用一个 id 时，落库只可能留下一份内容、另一份被唯一键挡下后
          「按成功处理」—— 前一个维度的结论被安到后一个头上，全程无日志无告警。放到这里拦，模型都不用跑。
        - **超 36 字符 / 空白**：落库时撞 varchar(36) 是 DataError，路由捕不到 ⇒ 裸 500，还白烧一次 LLM。
        - 长度**按 strip 后的值判并写回**：只判不写回的话 ``"<36 位> "`` 能过校验、落库仍撞列宽。
        """
        if not self.tasks:
            raise ValueError("tasks must not be empty")
        task_ids: list[str] = []
        for index, task in enumerate(self.tasks):
            task_id = (task.taskId or "").strip()
            if not task_id:
                raise ValueError(f"taskId must not be blank (tasks[{index}])")
            if len(task_id) > _MAX_TASK_ID_CHARS:
                raise ValueError(
                    f"taskId must be at most {_MAX_TASK_ID_CHARS} characters, "
                    f"got {len(task_id)} (tasks[{index}], taskId={task_id!r})")
            task.taskId = task_id
            task_ids.append(task_id)
        if len(set(task_ids)) != len(task_ids):
            raise ValueError(f"taskId must be unique, got {task_ids}")
        return self


class GapAnalysisItemsRequest(BaseModel):
    """`POST /api/ai/erl/gap-analysis/items` 入参（契约 §6.2）。"""

    taskIds: list[str] = Field(default_factory=list, description="要取条目的 Java 任务 id 列表，非空")

    @model_validator(mode="after")
    def _check_task_ids(self) -> GapAnalysisItemsRequest:
        """非空、每个 id 非空且 ≤ 36 字符；**去重并保序**后写回（重复 id 只会让 IN 列表变长，不报错）。"""
        cleaned: list[str] = []
        for index, raw in enumerate(self.taskIds):
            task_id = (raw or "").strip()
            if not task_id:
                raise ValueError(f"taskIds[{index}] must not be blank")
            if len(task_id) > _MAX_TASK_ID_CHARS:
                raise ValueError(
                    f"taskIds[{index}] must be at most {_MAX_TASK_ID_CHARS} characters, got {len(task_id)}")
            if task_id not in cleaned:
                cleaned.append(task_id)
        if not cleaned:
            raise ValueError("taskIds must not be empty")
        self.taskIds = cleaned
        return self


__all__ = [
    "GapAttachment",
    "GapQuestion",
    "GapTaskRequest",
    "GapAnalysisRefreshRequest",
    "GapAnalysisItemsRequest",
]
```

- [ ] **Step 2: 全文替换 `source/erl/interfaces/vo/response.py`**

```python
"""ERL 内部接口 Response VO（`{success, code, message, data}` 信封；JSON key lowerCamelCase）。

调用方只有 Java，**内网直连、不经网关**。契约见设计稿 §6.1（refresh）/ §6.2（items）。
两个端点在业务上**恒 200**：单任务失败在 ``status`` 里表达，入参错 422 由 pydantic 原生给出，
非预期异常 500 由框架默认处理 —— 本层没有别的状态码。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GapTaskStatus(BaseModel):
    """refresh 逐任务状态。``status`` 恒 SUCCESS / FAILED；FAILED 时 ``hasGap`` 为 null。"""

    taskId: str = Field(..., description="Java erl_gap_analysis_dimension_task.id，原样回传")
    status: str = Field(..., description="SUCCESS / FAILED（一次 LLM 尝试的结果；已有 SUCCESS 日志的任务直接回 SUCCESS）")
    hasGap: Optional[bool] = Field(None, description="SUCCESS 时 = 是否产出了 GAP 条目；FAILED 时为 null")


class GapAnalysisRefreshData(BaseModel):
    """``data`` 恒非 null：``tasks`` 与入参 ``tasks`` 一一对应、顺序一致。"""

    tasks: list[GapTaskStatus] = Field(default_factory=list)


class GapAnalysisRefreshResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: GapAnalysisRefreshData


class GapItem(BaseModel):
    """一条差距：只有标题与严重度（severity 恒 HIGH / MEDIUM / LOW，服务端已归一）。"""

    title: str
    severity: str


class GapAction(BaseModel):
    """一条建议动作：只有标题。"""

    title: str


class GapTaskItems(BaseModel):
    """一个任务的条目。``narrative`` 无差距时为 null（实际上无差距的任务压根没有条目、不在列表里）。"""

    taskId: str = Field(..., description="Java erl_gap_analysis_dimension_task.id")
    narrative: Optional[str] = Field(None, description="该维度的叙述段（NARRATIVE 条目）")
    gaps: list[GapItem] = Field(default_factory=list, description="按落库顺序（模型已按 severity 降序）")
    actions: list[GapAction] = Field(default_factory=list, description="按落库顺序")


class GapAnalysisItemsData(BaseModel):
    """``items`` 只含**有条目**的任务：无日志行 / FAILED / SUCCESS 但无差距的任务都不出现。"""

    items: list[GapTaskItems] = Field(default_factory=list)


class GapAnalysisItemsResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: GapAnalysisItemsData


__all__ = [
    "GapTaskStatus",
    "GapAnalysisRefreshData",
    "GapAnalysisRefreshResponse",
    "GapItem",
    "GapAction",
    "GapTaskItems",
    "GapAnalysisItemsData",
    "GapAnalysisItemsResponse",
]
```

- [ ] **Step 3: 全文替换 `source/erl/interfaces/routes.py`**

```python
"""ERL（Exit Readiness）内部路由（/api/ai/erl/*）。

**调用方只有 Java**（内网直连同步 HTTP、**不经网关** —— 网关只有 ``/api/web/**`` 与 ``/web/**``
两条路由；Java 用 Nacos 配置项 ``cio.erl.ai-base-url`` 直连本服务。前端不可达）。任务化（sprint119）
起两个端点（设计稿 §6）：

  - ``POST /gap-analysis/refresh``  按 Java 维度任务逐个生成并落库，逐任务回 ``{taskId, status, hasGap}``
  - ``POST /gap-analysis/items``    按任务 id 取已 SUCCESS 任务的条目（narrative / gaps / actions）

``GET /gap-analysis`` 与 ``POST /gap-analysis/share`` 已删除（编排状态与分享记录归 Java）。

HTTP 语义只有三种：入参错 **422**（pydantic 原生）；其余业务情形一律 **200**（单任务失败在 ``status``
里表达，Java 按 FAILED 走自愈重投）；非预期异常（DB 不可用等）**500** 由框架默认处理 —— 本层不再
把 ValueError / RuntimeError 翻译成 400 / 502。

AI 内容表 ``ai_erl_gap_analysis_task`` / ``ai_erl_gap_analysis_task_item`` 归 Python；ERL 评估表仍属 Java，
**公司 ACL 也仍在 Java**。鉴权由全局 ``AuthMiddleware`` 统一拦截，本层只经 ``get_current_user`` 取身份
（``ctx.user_id`` 落日志行 ``created_by``）。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from common.auth.identity import get_current_user
from common.redis.auth_store import AuthUser

from erl.application.dto.erl_gap_analysis_dto import GapAnalysisRefreshInputDTO
from erl.application.service import erl_gap_analysis_service
from erl.interfaces.vo import request as req
from erl.interfaces.vo import response as res

router = APIRouter(prefix="/api/ai/erl", tags=["Exit Readiness"])

logger = logging.getLogger("CIOaaS.erl.routes")


@router.post("/gap-analysis/refresh", response_model=res.GapAnalysisRefreshResponse)
async def refresh_gap_analysis(
    request: req.GapAnalysisRefreshRequest,
    ctx: AuthUser = Depends(get_current_user),
) -> res.GapAnalysisRefreshResponse:
    """按任务生成差距分析并落库（同步；每任务一次 LLM、并发 3），逐任务回状态（契约 §6.1）。

    已有 SUCCESS 日志的任务直接回 SUCCESS + hasGap、不再烧 LLM；单任务失败回 FAILED、不影响其它任务。
    """
    dto = GapAnalysisRefreshInputDTO.model_validate(request.model_dump())
    statuses = await erl_gap_analysis_service.refresh(dto, user_id=ctx.user_id)
    return res.GapAnalysisRefreshResponse(
        success=True, code=0, message="OK",
        data=res.GapAnalysisRefreshData(tasks=[
            res.GapTaskStatus.model_validate(status.model_dump(by_alias=True)) for status in statuses
        ]),
    )


@router.post("/gap-analysis/items", response_model=res.GapAnalysisItemsResponse)
async def list_gap_analysis_items(
    request: req.GapAnalysisItemsRequest,
    # ctx 只为强制解析登录态（公司 ACL 在 Java 侧，本接口不按身份收窄数据）
    ctx: AuthUser = Depends(get_current_user),
) -> res.GapAnalysisItemsResponse:
    """取已 SUCCESS 任务的条目，按任务分组（契约 §6.2）。无条目的任务不出现；一个都没有时 ``items=[]``。"""
    groups = await erl_gap_analysis_service.items(request.taskIds)
    return res.GapAnalysisItemsResponse(
        success=True, code=0, message="OK",
        data=res.GapAnalysisItemsData(items=[
            res.GapTaskItems.model_validate(group.model_dump(by_alias=True)) for group in groups
        ]),
    )
```

- [ ] **Step 4: 全文替换 `source/erl/__init__.py`**

```python
"""erl 域：Exit Readiness（ERL）的 **Goldie 差距分析 AI 内容**（sprint119 任务化）。

两个内部端点（Java **内网直连**调用、不经网关——网关只有 ``/api/web/**`` 与 ``/web/**`` 两条路由，
Java 用 Nacos 配置项 ``cio.erl.ai-base-url`` 直连；前端不可达）：

  - ``POST /api/ai/erl/gap-analysis/refresh``  按 Java 维度任务逐个生成并落库（每任务一次 LLM、并发 3、
    日志表 SUCCESS 短路），逐任务回 ``{taskId, status, hasGap}``
  - ``POST /api/ai/erl/gap-analysis/items``    按任务 id 取已 SUCCESS 任务的条目

编排状态（报告分享记录 + 按维度任务、状态机）归 Java；本域只持有 AI 内容：
``ai_erl_gap_analysis_task``（生成日志 + 幂等标记）+ ``ai_erl_gap_analysis_task_item``（条目，一次写入
永不改），迁移 ``sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql``。分层为
``interfaces`` + ``application`` + ``domain``（无 infrastructure —— 原 Redis 期次锁已随任务化删除，
双跑由条目唯一键兜底）。旧三张 ``ai_erl_gap_analysis*`` 表与其 ORM / 仓储保留至 V029。

答题附件**没有独立端点**：摘要在 ``refresh`` 内现场解析生成、按 fileId 跨任务去重、不落任何库。
其余 ERL 业务表（评估 / 维度配置 / 题库 …）仍属 Java，Python **不查、不做公司 ACL**（Java 调用前已校验）。

``main.py`` 通过 ``from erl.interfaces.routes import router as erl_router`` 挂载。
"""
```

- [ ] **Step 5: 改 `source/main.py` 第 90-92 行注释（`app.include_router(erl_router)` 不动）**

原文：
```python
# Exit Readiness 内部端点（source/erl/，前缀 /api/ai/erl/*：差距分析生成/读取/分享 + 答题附件入知识库；
# 调用方只有 Java（内网同步 HTTP）。P3 起产物落 Python 自持的 ai_erl_gap_analysis* 两表，
# 其余 ERL 业务表仍属 Java，公司 ACL 也仍在 Java）
```
改为：
```python
# Exit Readiness 内部端点（source/erl/，前缀 /api/ai/erl/*：按 Java 维度任务生成差距分析 refresh + 取条目 items；
# 调用方只有 Java（内网同步 HTTP）。sprint119 任务化起 AI 内容落 Python 自持的 ai_erl_gap_analysis_task /
# _task_item 两表（V028），编排状态归 Java；其余 ERL 业务表仍属 Java，公司 ACL 也仍在 Java）
```

- [ ] **Step 6: 轻量校验（含一次 import 冒烟：整条 erl 导入链 + 路由注册）**

```powershell
uv run python -m py_compile source/erl/interfaces/vo/request.py source/erl/interfaces/vo/response.py source/erl/interfaces/routes.py source/erl/__init__.py source/main.py
uv run ruff check source/erl source/main.py
uv run python -c "import sys; sys.path.insert(0, 'source'); from erl.interfaces.routes import router; paths = sorted((r.path, tuple(sorted(r.methods))) for r in router.routes); print(paths); assert paths == [('/api/ai/erl/gap-analysis/items', ('POST',)), ('/api/ai/erl/gap-analysis/refresh', ('POST',))]"
```

预期最后一条打印两条 POST 路由、无 GET、无 share。（若本机 import 因 `.env` / DB 配置报错，改跑 Task 8 的测试文件 import 即可——测试 conftest 已 stub 掉副作用包。）

---

### Task 8: service 测试重写（tests/erl/test_erl_gap_analysis_service.py）

**Files:**
- Modify: `tests/erl/test_erl_gap_analysis_service.py`（全文替换，原 2448 行——旧文件整份绑定旧契约，含锁 / 快照 / index / share 用例）

- [ ] **Step 1: 全文替换 `tests/erl/test_erl_gap_analysis_service.py`（模块头 + 夹具 + 短路 / 落库两节）**

```python
"""erl_gap_analysis_service — Goldie 差距分析任务化（sprint119，设计稿 §6 / §10）。

LLM / DB / rag 全部 mock（standards/coding.md §11）。固定输入 → 验证：

- **幂等短路**：``refresh`` 开头批量查日志表，已 SUCCESS 的任务直接回状态、既不进附件摘要也不进 LLM；
  FAILED 日志不短路（重跑）；返回顺序 = 入参顺序、一个不少；
- **每任务一次 LLM、并发受 ``Semaphore(_TASK_CONCURRENCY)`` 约束**；单任务失败（LLM / 解析 / 落库）只影响
  它自己：日志行 FAILED、不写条目、``hasGap=null``，同轮其它任务照常 SUCCESS；
- **一个事务**写日志行 + 条目（commit 一次、先 upsert 后插条目）；条目形态（NARRATIVE sort 0 无 severity /
  GAP 带 severity / ACTION）；``content`` 截 1024；``created_by`` = 调用者；无 gaps 时 ``has_gap=False`` 且零条目；
- **撞唯一键按成功处理**：commit 抛 IntegrityError → rollback → 重查日志行为 SUCCESS → 回先到者的 has_gap；
  重查不到 SUCCESS 行则是真异常 → FAILED；
- **FAILED 永不覆盖 SUCCESS**：失败路径撞唯一键只回滚忽略；FAILED 日志自身写不进去也不抛、不影响状态；
- **解析**：severity 越界归一 MEDIUM；无 gaps 丢 narrative；非字符串 narrative 丢弃；无 title 条目丢弃；
  多余键（note / why / evidenceMissing / summary / index）丢弃；**没有 ``gaps`` 数组 ⇒ 判失败**
  （绝不降级成「无差距」—— 那是绿点 No Gap 的假阴性）；
- **prompt v1.7 回归**（coding.md §15）：user prompt 只装**一个维度对象**、无 index / analyzedContext；
  **taskId / fileId 绝不进 prompt**；system prompt 保留计分口径、双端处置、附件规则、内部称谓禁令，
  不再要求 summary / note / why / evidenceMissing；LLM 调用带 timeout、SDK 重试关 0、json_mode、trace；
- **附件**：按 fileId **跨任务**去重只解析一次、摊回每个附件项；已 SUCCESS 任务的附件不解析；无文件名
  跳过；单份失败不影响其它；并发闸；阶段总闸；
- **items**：只查 SUCCESS 任务的条目、按任务分组、无条目的任务不出现、条目顺序跟读序；
- **Request VO 422 边界**：``tasks`` 非空 / ``taskId`` 非空 ≤ 36 唯一且 strip 写回、多余键（旧
  ``organizationId`` / ``index`` / ``code`` / ``submissionSignature``）忽略；``taskIds`` 非空 / 去重保序；
- **路由 HTTP 语义**：入参错 422、单任务 FAILED 仍 200、信封形状、只剩两条 POST 路由。

落库相关用例一律 mock ``get_session`` 与两个仓储 —— 全仓单测零真实 DB。
"""
from __future__ import annotations

import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from erl.application.dto.erl_gap_analysis_dto import (
    GapActionDTO,
    GapAnalysisRefreshInputDTO,
    GapItemDTO,
    GapTaskItemsDTO,
    GapTaskStatusDTO,
)
from erl.application.service import erl_gap_analysis_service as svc
from erl.domain.enums import GapItemType, GapTaskStatus
from erl.domain.models import ErlGapAnalysisTask, ErlGapAnalysisTaskItem
from erl.interfaces.vo import response as res
from erl.interfaces.vo.request import GapAnalysisItemsRequest, GapAnalysisRefreshRequest
from llm.infrastructure import AI_REQUEST_TIMEOUT_SECONDS

# Java 任务 id（UUID，恰 36 字符 —— Request VO 的列宽上限）。
_TASK_FRL = "8c1c5a5e-6f1e-4c3a-9a8f-0f1e2d3c4b5a"
_TASK_CRL = "2b7e9d10-1a2b-4c3d-8e9f-a0b1c2d3e4f5"
_USER = "u-1"

# 一个任务（契约 §6.1）：FRL 维度止步 level 3（founder）/ level 4（GSV），第三题只有 GSV 作答
# —— 覆盖「某端未作答字段缺失」这条（exclude_none 会把它整个去掉）。
_INPUT = {
    "companyId": "c-1",
    "period": "2026Q1",
    "tasks": [
        {
            "taskId": _TASK_FRL,
            "name": "Financial Readiness",
            "abbr": "FRL",
            "weight": 30,
            "founderLevelScore": 2,
            "gsvLevelScore": 3,
            "perceptionGap": -1,
            "founderTerminatedLevel": 3,
            "gsvTerminatedLevel": 4,
            "questions": [
                {
                    "questionText": "Are monthly management accounts closed within 10 days?",
                    "eraBand": 1,
                    "eraLabel": "Founder Era - 1",
                    "evidenceSource": "Monthly management accounts",
                    "founderYesNo": True,
                    "gsvYesNo": True,
                    "founderNote": "We close by day 8.",
                    "gsvNote": None,
                },
                {
                    "questionText": "Is there an audit committee?",
                    "eraBand": 3,
                    "eraLabel": "Founder Era - 3",
                    "founderYesNo": False,
                    "gsvYesNo": True,
                },
                {
                    "questionText": "Is the cap table reconciled quarterly?",
                    "eraBand": 4,
                    "eraLabel": "Harvest & Growth - 4",
                    "gsvYesNo": False,
                },
            ],
        },
    ],
}

_EXTRA_TASK = {
    "taskId": _TASK_CRL,
    "name": "Customer Readiness",
    "abbr": "CRL",
    "weight": 20,
    "founderLevelScore": 5,
    "questions": [
        {"questionText": "Is churn tracked monthly?", "eraBand": 5, "founderYesNo": True},
    ],
}


def _dto(**overrides) -> GapAnalysisRefreshInputDTO:
    return GapAnalysisRefreshInputDTO.model_validate({**_INPUT, **overrides})


def _dto_two_tasks() -> GapAnalysisRefreshInputDTO:
    return _dto(tasks=[*_INPUT["tasks"], _EXTRA_TASK])


def _output(*, gaps: list | None = None, actions: list | None = None,
            narrative: str | None = "FRL sits at level 2 ... but ...", **extra) -> dict:
    """一次 LLM 的单维输出（prompt v1.7 契约）。``gaps=None`` 给一条默认差距；``narrative=None`` 不输出该键。"""
    payload: dict = {
        "gaps": [{"title": "No audit committee", "severity": "HIGH"}] if gaps is None else gaps,
        "actions": [{"title": "Stand up an audit committee before the level-3 re-score"}]
        if actions is None else actions,
        **extra,
    }
    if narrative is not None:
        payload["narrative"] = narrative
    return payload


def _patch_llm(mocker, payload) -> AsyncMock:
    """打桩 llm_db_router.acomplete。

    ``payload``：dict / str = 每次同样的输出；list = 按调用顺序逐个给（元素可为异常实例）；
    callable（async）= 直接作 side_effect（并发用例按 prompt 内容分流）。
    """
    def _content(item):
        return SimpleNamespace(content=item if isinstance(item, str) else json.dumps(item))

    if callable(payload):
        acomplete = AsyncMock(side_effect=payload)
    elif isinstance(payload, list):
        acomplete = AsyncMock(side_effect=[
            item if isinstance(item, BaseException) else _content(item) for item in payload])
    else:
        acomplete = AsyncMock(return_value=_content(payload))
    mocker.patch.object(svc, "llm_db_router", MagicMock(acomplete=acomplete))
    return acomplete


def _no_backoff(mocker) -> None:
    """失败路径用例把退避清零，否则每条要真等 2s + 4s。"""
    mocker.patch.object(svc, "_LLM_RETRY_BACKOFF_SECONDS", (0.0, 0.0))


def _log_row(**overrides) -> ErlGapAnalysisTask:
    defaults = dict(id="l-1", task_id=_TASK_FRL, status=GapTaskStatus.SUCCESS.value, has_gap=True,
                    model="anthropic/claude-sonnet-5", created_by=_USER)
    return ErlGapAnalysisTask(**{**defaults, **overrides})


def _item_row(**overrides) -> ErlGapAnalysisTaskItem:
    defaults = dict(id="i-1", task_id=_TASK_FRL, item_type=GapItemType.GAP.value,
                    content="No audit committee", severity="HIGH", sort_order=0)
    return ErlGapAnalysisTaskItem(**{**defaults, **overrides})


def _patch_db(mocker, *, log_rows=(), item_rows=()):
    """打桩 session + 两个仓储。

    ``log_rows`` 是 ``task_repo.find_by_task_ids`` 的返回（refresh 开头的批量短路查询、撞键后的重查、
    items 的圈定都走它；要按调用顺序区分时改 ``db.task.find_by_task_ids.side_effect``）；
    ``item_rows`` 是 ``item_repo.find_by_task_ids`` 的返回。两个仓储挂同一个 parent，跨仓储的调用
    顺序经 ``db.calls.mock_calls`` 断言。
    """
    session = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = session
    ctx.__exit__.return_value = False
    mocker.patch.object(svc, "get_session", return_value=ctx)
    task = MagicMock()
    task.find_by_task_ids.return_value = list(log_rows)
    item = MagicMock()
    item.find_by_task_ids.return_value = list(item_rows)
    calls = MagicMock()
    calls.attach_mock(task, "task")
    calls.attach_mock(item, "item")
    mocker.patch.object(svc, "task_repo", task)
    mocker.patch.object(svc, "item_repo", item)
    return SimpleNamespace(session=session, task=task, item=item, calls=calls)


def _upserts(db) -> list[dict]:
    return [call.kwargs for call in db.task.upsert_by_task_id.call_args_list]


def _inserted_items(db) -> list[ErlGapAnalysisTaskItem]:
    return [row for call in db.item.bulk_insert.call_args_list for row in call.args[1]]


def _user_prompt(acomplete: AsyncMock, call: int = 0) -> str:
    return acomplete.await_args_list[call].args[0][1]["content"]


def _system_prompt(acomplete: AsyncMock) -> str:
    return acomplete.await_args_list[0].args[0][0]["content"]


def _dimension_json(acomplete: AsyncMock, call: int = 0) -> dict:
    """从 user prompt 里把那个单维 JSON 对象解回来（按段落标题定位后 raw_decode）。"""
    text = _user_prompt(acomplete, call)
    marker = "本次要分析的维度（JSON）："
    start = text.index("{", text.index(marker) + len(marker))
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    return value


async def _refresh(mocker, dto: GapAnalysisRefreshInputDTO | None = None, **db_kwargs):
    db = _patch_db(mocker, **db_kwargs)
    statuses = await svc.refresh(dto or _dto(), user_id=_USER)
    return statuses, db


# ============================================================================
# 幂等短路与状态汇总（契约 §6.1 步骤 3 / 设计 §8）
# ============================================================================


async def test_a_task_with_a_success_log_is_short_circuited(mocker):
    """重投命中 SUCCESS 行：不调 LLM、不写库，直接回它的 has_gap。"""
    acomplete = _patch_llm(mocker, _output())

    statuses, db = await _refresh(mocker, log_rows=[_log_row(has_gap=True)])

    acomplete.assert_not_awaited()
    assert [(s.task_id, s.status, s.has_gap) for s in statuses] == [(_TASK_FRL, "SUCCESS", True)]
    db.task.upsert_by_task_id.assert_not_called()
    db.item.bulk_insert.assert_not_called()
    db.session.commit.assert_not_called()


async def test_only_the_tasks_without_a_success_log_are_run(mocker):
    acomplete = _patch_llm(mocker, _output())

    statuses, _ = await _refresh(mocker, _dto_two_tasks(),
                                 log_rows=[_log_row(task_id=_TASK_CRL, has_gap=False)])

    assert acomplete.await_count == 1
    assert _dimension_json(acomplete)["abbr"] == "FRL"
    assert [(s.task_id, s.status, s.has_gap) for s in statuses] == [
        (_TASK_FRL, "SUCCESS", True), (_TASK_CRL, "SUCCESS", False)]


async def test_a_failed_log_row_does_not_short_circuit(mocker):
    """FAILED 不是终态：Java 重投时要真的再跑一次。"""
    acomplete = _patch_llm(mocker, _output())

    statuses, _ = await _refresh(mocker, log_rows=[_log_row(status="FAILED", has_gap=None)])

    assert acomplete.await_count == 1
    assert statuses[0].status == "SUCCESS"


async def test_the_log_table_is_queried_once_for_all_tasks(mocker):
    """一次 IN 查询而不是每任务一查（coding.md §6）；成功路径不重查，整轮只有开头那一次。"""
    _patch_llm(mocker, _output())

    _, db = await _refresh(mocker, _dto_two_tasks())

    assert db.task.find_by_task_ids.call_count == 1
    assert db.task.find_by_task_ids.call_args.args[1] == [_TASK_FRL, _TASK_CRL]


async def test_statuses_follow_the_input_order(mocker):
    """短路的与跑过的混在一起也按入参顺序回：Java 按 taskId 对号，但顺序稳定省它一次排序。"""
    _patch_llm(mocker, _output())

    statuses, _ = await _refresh(mocker, _dto(tasks=[_EXTRA_TASK, *_INPUT["tasks"]]),
                                 log_rows=[_log_row(task_id=_TASK_FRL, has_gap=False)])

    assert [s.task_id for s in statuses] == [_TASK_CRL, _TASK_FRL]


# ============================================================================
# 落库：一个事务 / 条目形态 / 撞唯一键 / 失败路径
# ============================================================================


async def test_success_writes_the_log_row_and_items_in_one_transaction(mocker):
    _patch_llm(mocker, _output())

    statuses, db = await _refresh(mocker)

    db.session.commit.assert_called_once()
    db.session.rollback.assert_not_called()
    [upsert] = _upserts(db)
    assert upsert == {"task_id": _TASK_FRL, "status": "SUCCESS", "has_gap": True,
                      "model": svc._MODEL, "user_id": _USER}
    # 先 upsert 日志行（拿行锁）再插条目
    names = [c[0] for c in db.calls.mock_calls
             if c[0] in ("task.upsert_by_task_id", "item.bulk_insert")]
    assert names == ["task.upsert_by_task_id", "item.bulk_insert"]
    assert (statuses[0].status, statuses[0].has_gap) == ("SUCCESS", True)


async def test_item_rows_follow_the_documented_shape(mocker):
    _patch_llm(mocker, _output(
        narrative="FRL sits at level 2 ... but ...",
        gaps=[{"title": "No audit committee", "severity": "HIGH"},
              {"title": "Cap table not reconciled", "severity": "LOW"}],
        actions=[{"title": "Stand up an audit committee"}]))

    _, db = await _refresh(mocker)

    rows = _inserted_items(db)
    assert [(r.item_type, r.sort_order, r.content, r.severity) for r in rows] == [
        ("NARRATIVE", 0, "FRL sits at level 2 ... but ...", None),
        ("GAP", 0, "No audit committee", "HIGH"),
        ("GAP", 1, "Cap table not reconciled", "LOW"),
        ("ACTION", 0, "Stand up an audit committee", None),
    ]
    assert all(r.task_id == _TASK_FRL for r in rows)
    assert all(r.id for r in rows), "id 显式生成，不靠 flush"
    assert all((r.created_by, r.updated_by) == (_USER, _USER) for r in rows)


async def test_over_long_content_is_truncated_to_the_column_width(mocker):
    _patch_llm(mocker, _output(narrative="n" * 3000,
                               gaps=[{"title": "g" * 2000, "severity": "HIGH"}],
                               actions=[{"title": "a" * 2000}]))

    _, db = await _refresh(mocker)

    assert [len(r.content) for r in _inserted_items(db)] == [1024, 1024, 1024]


async def test_no_gaps_is_recorded_as_success_without_items(mocker):
    _patch_llm(mocker, _output(gaps=[], actions=[], narrative=None))

    statuses, db = await _refresh(mocker)

    assert (statuses[0].status, statuses[0].has_gap) == ("SUCCESS", False)
    assert _upserts(db)[0]["has_gap"] is False
    assert _inserted_items(db) == []
    db.session.commit.assert_called_once()


async def test_unique_key_collision_is_treated_as_success(mocker):
    """双跑：后提交的一路在 commit 撞唯一键 → rollback → 重查到先到者的 SUCCESS 行 → 回它的 has_gap。"""
    _patch_llm(mocker, _output())
    db = _patch_db(mocker)
    # ① 开头短路查询：无行 ② 撞键后重查：先到者已 SUCCESS（has_gap=False，与本路算出的 True 不同）
    db.task.find_by_task_ids.side_effect = [[], [_log_row(has_gap=False)]]
    db.session.commit.side_effect = IntegrityError(
        "INSERT INTO ai_erl_gap_analysis_task_item ...", {},
        Exception("duplicate key value violates unique constraint"))

    statuses = await svc.refresh(_dto(), user_id=_USER)

    db.session.rollback.assert_called_once()
    assert (statuses[0].status, statuses[0].has_gap) == ("SUCCESS", False), "先到者赢"
    assert [u["status"] for u in _upserts(db)] == ["SUCCESS"], "没有再写 FAILED 行"


async def test_unique_key_collision_without_a_success_row_is_a_failure(mocker):
    """撞键却查不到 SUCCESS 行 = 不是双跑而是真异常 → 该任务 FAILED（写 FAILED 行、不写条目）。"""
    _patch_llm(mocker, _output())
    db = _patch_db(mocker)
    db.task.find_by_task_ids.side_effect = [[], []]
    db.session.commit.side_effect = [IntegrityError("INSERT ...", {}, Exception("boom")), None]

    statuses = await svc.refresh(_dto(), user_id=_USER)

    assert (statuses[0].status, statuses[0].has_gap) == ("FAILED", None)
    assert [u["status"] for u in _upserts(db)] == ["SUCCESS", "FAILED"]
    assert db.item.bulk_insert.call_count == 1, "失败路径不写条目"


async def test_llm_failure_writes_a_failed_row_and_no_items(mocker):
    _no_backoff(mocker)
    acomplete = _patch_llm(mocker, [TimeoutError("t1"), TimeoutError("t2"), TimeoutError("t3")])

    statuses, db = await _refresh(mocker)

    assert acomplete.await_count == 3
    assert [(s.status, s.has_gap) for s in statuses] == [("FAILED", None)]
    assert _upserts(db) == [{"task_id": _TASK_FRL, "status": "FAILED", "has_gap": None,
                             "model": svc._MODEL, "user_id": _USER}]
    db.item.bulk_insert.assert_not_called()
    db.session.commit.assert_called_once()


@pytest.mark.parametrize("raw", [
    "Sorry, I can't help with that.",           # 不是 JSON
    {"error": "no gaps key"},                    # 对象但没有 gaps
    {"gaps": "none"},                            # gaps 不是数组
    {"dimensions": [{"index": 1, "gaps": []}]},  # 旧的整批包裹形状
])
async def test_output_without_a_gaps_array_is_a_failure_never_a_no_gap(mocker, raw):
    """**本文件最重要的一条**：解析不出一律 FAILED，绝不降级成「无差距」（绿点 No Gap 的假阴性）。"""
    _patch_llm(mocker, raw)

    statuses, db = await _refresh(mocker)

    assert (statuses[0].status, statuses[0].has_gap) == ("FAILED", None)
    assert [u["status"] for u in _upserts(db)] == ["FAILED"]
    db.item.bulk_insert.assert_not_called()


async def test_one_failing_task_does_not_affect_the_other(mocker):
    _no_backoff(mocker)

    async def _by_task(messages, **kwargs):
        if '"abbr": "FRL"' in messages[1]["content"]:
            raise TimeoutError("provider down")
        return SimpleNamespace(content=json.dumps(_output()))

    _patch_llm(mocker, _by_task)

    statuses, db = await _refresh(mocker, _dto_two_tasks())

    assert [(s.task_id, s.status, s.has_gap) for s in statuses] == [
        (_TASK_FRL, "FAILED", None), (_TASK_CRL, "SUCCESS", True)]
    assert {u["task_id"]: u["status"] for u in _upserts(db)} == {
        _TASK_FRL: "FAILED", _TASK_CRL: "SUCCESS"}


async def test_a_failed_row_never_overwrites_a_success_row(mocker):
    """失败路径撞唯一键（UPDATE 不命中 SUCCESS 终态行 ⇒ INSERT ⇒ 撞 uk）只回滚忽略；本次仍回 FAILED，
    Java 重投时会命中那条 SUCCESS 日志直接回状态。"""
    _no_backoff(mocker)
    _patch_llm(mocker, [TimeoutError("x"), TimeoutError("x"), TimeoutError("x")])
    db = _patch_db(mocker)
    db.session.commit.side_effect = IntegrityError(
        "INSERT INTO ai_erl_gap_analysis_task ...", {}, Exception("duplicate"))

    statuses = await svc.refresh(_dto(), user_id=_USER)

    db.session.rollback.assert_called_once()
    assert statuses[0].status == "FAILED"


async def test_a_broken_failure_log_write_is_swallowed(mocker):
    """失败路径里的失败只记日志：不能把「记不下失败」升级成整轮 500。"""
    _no_backoff(mocker)
    _patch_llm(mocker, [TimeoutError("x"), TimeoutError("x"), TimeoutError("x")])
    db = _patch_db(mocker)
    db.task.upsert_by_task_id.side_effect = RuntimeError("db is down")

    statuses = await svc.refresh(_dto(), user_id=_USER)

    assert [(s.status, s.has_gap) for s in statuses] == [("FAILED", None)]


async def test_llm_failure_is_retried_twice_with_exponential_backoff(mocker):
    sleep = mocker.patch.object(svc.asyncio, "sleep", AsyncMock())
    acomplete = _patch_llm(mocker, [TimeoutError("t1"), TimeoutError("t2"), _output()])

    statuses, db = await _refresh(mocker)

    assert acomplete.await_count == 3
    assert [c.args[0] for c in sleep.await_args_list] == [2.0, 4.0]
    assert statuses[0].status == "SUCCESS"
    db.session.commit.assert_called_once()


async def test_llm_call_uses_bounded_timeout_and_no_sdk_retries(mocker):
    """coding.md §10：AI 调用必须设 timeout + 有界重试 —— 且**只有一层**重试（SDK 传输级关 0）。"""
    acomplete = _patch_llm(mocker, _output())

    await _refresh(mocker)

    kwargs = acomplete.await_args.kwargs
    assert kwargs["timeout"] == AI_REQUEST_TIMEOUT_SECONDS == 120
    assert kwargs["max_retries"] == 0
    assert kwargs["json_mode"] is True
    assert kwargs["max_tokens"] == svc._MAX_TOKENS
    assert kwargs["trace"].agent == "erl" and kwargs["trace"].company_id == "c-1"


def test_single_task_worst_case_is_bounded():
    """算术断言：单任务最坏 = 3 × 120 + 2 + 4 = 366s。没有锁 TTL 要对齐了，但改任一常量这条会红，
    提醒复核 service 头部关于 Java 500s 读超时的说明。"""
    attempts = len(svc._LLM_RETRY_BACKOFF_SECONDS) + 1
    assert attempts == 3
    assert attempts * AI_REQUEST_TIMEOUT_SECONDS + sum(svc._LLM_RETRY_BACKOFF_SECONDS) == 366
    assert svc._ATTACHMENT_SUMMARY_TIMEOUT_SECONDS < svc._ATTACHMENT_SUMMARY_STAGE_TIMEOUT_SECONDS
    assert svc._TASK_CONCURRENCY == 3


async def test_tasks_run_concurrently_up_to_the_semaphore(mocker):
    mocker.patch.object(svc, "_TASK_CONCURRENCY", 2)
    inflight, peak = 0, 0

    async def _slow(messages, **kwargs):
        nonlocal inflight, peak
        inflight += 1
        peak = max(peak, inflight)
        await asyncio.sleep(0.01)
        inflight -= 1
        return SimpleNamespace(content=json.dumps(_output()))

    _patch_llm(mocker, _slow)
    tasks = [{**_EXTRA_TASK, "taskId": f"t-{i}", "abbr": f"D{i}"} for i in range(5)]

    statuses, _ = await _refresh(mocker, _dto(tasks=tasks))

    assert peak == 2, f"并发闸没生效（峰值 {peak}）"
    assert len(statuses) == 5 and all(s.status == "SUCCESS" for s in statuses)


async def test_two_tasks_really_overlap(mocker):
    """默认并发 3 下两个任务应同时在途，而不是一个跑完再跑下一个。"""
    inflight, peak = 0, 0

    async def _slow(messages, **kwargs):
        nonlocal inflight, peak
        inflight += 1
        peak = max(peak, inflight)
        await asyncio.sleep(0)
        inflight -= 1
        return SimpleNamespace(content=json.dumps(_output()))

    _patch_llm(mocker, _slow)

    await _refresh(mocker, _dto_two_tasks())

    assert peak == 2
```

- [ ] **Step 2: 追加「解析 / prompt 回归」两节到同一文件末尾**

```python
# ============================================================================
# 解析：severity / narrative / 条目容错
# ============================================================================


@pytest.mark.parametrize("raw", ["CRITICAL", "", "中", "3", None])
async def test_illegal_severity_downgraded_to_medium(mocker, raw):
    _patch_llm(mocker, _output(gaps=[{"title": "No audit committee", "severity": raw}]))

    _, db = await _refresh(mocker)

    [gap] = [r for r in _inserted_items(db) if r.item_type == "GAP"]
    assert gap.severity == "MEDIUM"


@pytest.mark.parametrize("raw,expected", [("HIGH", "HIGH"), ("low", "LOW"), (" Medium ", "MEDIUM")])
async def test_legal_severity_normalized_to_upper(mocker, raw, expected):
    _patch_llm(mocker, _output(gaps=[{"title": "No audit committee", "severity": raw}]))

    _, db = await _refresh(mocker)

    [gap] = [r for r in _inserted_items(db) if r.item_type == "GAP"]
    assert gap.severity == expected


async def test_narrative_without_gaps_is_dropped(mocker):
    _patch_llm(mocker, _output(gaps=[], actions=[], narrative="Looks fine."))

    statuses, db = await _refresh(mocker)

    assert statuses[0].has_gap is False
    assert _inserted_items(db) == []


async def test_non_string_narrative_is_dropped(mocker):
    _patch_llm(mocker, _output(narrative={"text": "x"}))

    _, db = await _refresh(mocker)

    rows = _inserted_items(db)
    assert not [r for r in rows if r.item_type == "NARRATIVE"]
    assert [r for r in rows if r.item_type == "GAP"]


async def test_items_without_a_title_are_dropped(mocker):
    _patch_llm(mocker, _output(
        gaps=[{"severity": "HIGH"}, {"title": "  ", "severity": "LOW"},
              {"title": "Real gap", "severity": "LOW"}, "not-a-dict"],
        actions=[{"why": "no title"}, {"title": "Do it"}]))

    _, db = await _refresh(mocker)

    rows = _inserted_items(db)
    assert [r.content for r in rows if r.item_type == "GAP"] == ["Real gap"]
    assert [r.content for r in rows if r.item_type == "ACTION"] == ["Do it"]


async def test_extra_output_keys_are_ignored(mocker):
    """模型多回 note / why / evidenceMissing / summary / index 一律丢弃（决策 D7），不落库不影响状态。"""
    _patch_llm(mocker, _output(
        gaps=[{"title": "No audit committee", "note": "elaboration", "severity": "HIGH",
               "evidenceMissing": True}],
        actions=[{"title": "Do it", "why": "because"}],
        summary="cross-dimension summary", index=1))

    statuses, db = await _refresh(mocker)

    assert statuses[0].status == "SUCCESS"
    contents = [r.content for r in _inserted_items(db)]
    assert "elaboration" not in contents and "because" not in contents
    assert "cross-dimension summary" not in contents


# ============================================================================
# prompt v1.7 回归（coding.md §15：固定输入 → 验证输出结构）
# ============================================================================


async def test_prompt_carries_exactly_one_dimension_with_its_answers_and_levels(mocker):
    acomplete = _patch_llm(mocker, _output())

    await _refresh(mocker)

    dimension = _dimension_json(acomplete)
    assert dimension["abbr"] == "FRL" and dimension["name"] == "Financial Readiness"
    assert dimension["founderLevelScore"] == 2 and dimension["gsvLevelScore"] == 3
    assert dimension["founderTerminatedLevel"] == 3 and dimension["weight"] == 30
    audit = dimension["questions"][1]
    assert audit["founderYesNo"] is False and audit["gsvYesNo"] is True and audit["eraBand"] == 3
    cap_table = dimension["questions"][2]
    assert "founderYesNo" not in cap_table and cap_table["gsvYesNo"] is False  # 未作答 = 键缺失
    user = _user_prompt(acomplete)
    assert "2026Q1" in user and "c-1" in user
    assert "null" not in user and '"gsvNote"' not in user
    assert "Output only the JSON object. All text inside it must be in English." in user
    for stale in ('"index"', "analyzedContext", "本轮要分析的维度", "已分析过的其他维度", "{{var:"):
        assert stale not in user, f"user prompt 残留旧契约：{stale}"


def test_task_id_never_reaches_the_prompt():
    """**本节最重要的一条**：taskId 只用于落库与回状态，靠 ``_PROMPT_EXCLUDE`` 剔除；剔除没了立刻转红。"""
    task = _dto().tasks[0]

    user = svc._build_user_prompt(task, company_id="c-1", period="2026Q1")

    assert _TASK_FRL not in user and "taskId" not in user and "task_id" not in user
    assert '"abbr": "FRL"' in user  # 证明是「只丢了 taskId」而不是整包没序列化


def test_file_id_never_reaches_the_prompt():
    payload = copy.deepcopy(_INPUT)
    payload["tasks"][0]["questions"][0]["attachments"] = [{"fileId": "f-secret-1", "fileName": "a.pdf"}]
    task = GapAnalysisRefreshInputDTO.model_validate(payload).tasks[0]

    user = svc._build_user_prompt(task, company_id="c-1", period="2026Q1")

    assert "f-secret-1" not in user and "fileId" not in user
    assert '"fileName": "a.pdf"' in user and '"summaryAvailable": false' in user


async def test_prompt_declares_the_single_dimension_contract(mocker):
    acomplete = _patch_llm(mocker, _output())

    await _refresh(mocker)

    system = _system_prompt(acomplete)
    assert "只分析一个维度" in system
    assert '"narrative"' in system and '"gaps"' in system and '"actions"' in system
    assert "`gaps` 键必须始终存在" in system
    assert "No Gap" in system
    for stale in ('"summary"', "analyzedContext", '"index"', '"evidenceMissing"', '"note"', '"why"',
                  "audience", "results", "5 个维度", "五维", "PRL", "BERL"):
        assert stale not in system, f"提示词残留旧契约：{stale}"


async def test_prompt_keeps_the_scoring_and_wording_rules(mocker):
    acomplete = _patch_llm(mocker, _output())

    await _refresh(mocker)

    system = _system_prompt(acomplete)
    for required in ("最后一个「全部 Yes」的 level", "升序列表里 `terminatedLevel` 的前一个",
                     "最大的有题 level", "跳空的 level 不代表", "止步 level 内答 No 的那些题",
                     "未作答的题不得编造判断", "解锁 / 通过 / 终止是每一端各算一套", "不点名是哪一侧",
                     "不得直接引用 GSV 的具体分数", "输出里不得出现任何内部称谓", "不构成证据",
                     "HIGH", "MEDIUM", "LOW"):
        assert required in system, required
    for stale in ("与更低的 level 有没有题目无关", "未解锁 level 的题不在输入中", "Top GSV quartile",
                  "criteria", "Workbook"):
        assert stale not in system, stale


async def test_prompt_declares_the_attachment_and_item_rules(mocker):
    acomplete = _patch_llm(mocker, _output())

    await _refresh(mocker)

    system = _system_prompt(acomplete)
    for required in ("summaryAvailable", "二手信息", "严禁凭文件名推断", "最多 3 句、不超过 60 词",
                     "1–5 条", "1–3 条", "把维度名替换成任何其它维度后仍然成立", "依据写进 `title` 本身"):
        assert required in system, required
```

- [ ] **Step 3: 追加「附件摘要」「items」「Request VO」「路由」四节到同一文件末尾**

```python
# ============================================================================
# 附件摘要：跨任务按 fileId 去重、现场生成、不落库（design-doc §5.1）
# ============================================================================


_ATTACHMENTS = [
    {"fileId": "f-1", "fileName": "FY2025-management-accounts.pdf"},
    {"fileId": "f-2", "fileName": "close-checklist.xlsx"},
]


def _dto_with_attachments_across_tasks() -> GapAnalysisRefreshInputDTO:
    """f-1 挂在 FRL 第 1 题**与** CRL 第 1 题上（跨任务复用同一 fileId），f-2 只在 FRL 第 1 题。"""
    payload = copy.deepcopy(_INPUT)
    payload["tasks"][0]["questions"][0]["attachments"] = copy.deepcopy(_ATTACHMENTS)
    extra = copy.deepcopy(_EXTRA_TASK)
    extra["questions"][0]["attachments"] = [copy.deepcopy(_ATTACHMENTS[0])]
    payload["tasks"].append(extra)
    return GapAnalysisRefreshInputDTO.model_validate(payload)


def _patch_summaries(mocker, summaries: dict[str, str] | None = None, *, side_effect=None) -> AsyncMock:
    """打桩 rag 入口 ``summarize_file_inline``（进程内直调、不经 Java 网关；摘要不落库）。"""
    table = summaries or {}
    summarize = AsyncMock(side_effect=side_effect or (lambda *, file_id, title: table.get(file_id)))
    mocker.patch("rag.application.service.ingest_service.get_ingest_service",
                 return_value=SimpleNamespace(summarize_file_inline=summarize))
    return summarize


def _attachments_in_prompt(acomplete: AsyncMock, abbr: str) -> list:
    for call in range(acomplete.await_count):
        dimension = _dimension_json(acomplete, call)
        if dimension["abbr"] == abbr:
            return dimension["questions"][0]["attachments"]
    raise AssertionError(f"no prompt for {abbr}")


async def test_each_file_is_summarized_once_across_tasks_and_fanned_back(mocker):
    acomplete = _patch_llm(mocker, _output())
    summarize = _patch_summaries(mocker, {"f-1": "Monthly close within 8 days.",
                                          "f-2": "Close checklist with owners."})

    await _refresh(mocker, _dto_with_attachments_across_tasks())

    assert summarize.await_count == 2, "f-1 挂在两个任务上，只该解析一次"
    assert {c.kwargs["file_id"] for c in summarize.await_args_list} == {"f-1", "f-2"}
    assert {c.kwargs["title"] for c in summarize.await_args_list} == {
        "FY2025-management-accounts.pdf", "close-checklist.xlsx"}
    frl = _attachments_in_prompt(acomplete, "FRL")
    assert [a["summary"] for a in frl] == ["Monthly close within 8 days.", "Close checklist with owners."]
    assert all(a["summaryAvailable"] is True for a in frl)
    crl = _attachments_in_prompt(acomplete, "CRL")
    assert crl[0]["summary"] == "Monthly close within 8 days." and crl[0]["summaryAvailable"] is True


async def test_attachments_of_already_succeeded_tasks_are_not_summarized(mocker):
    _patch_llm(mocker, _output())
    summarize = _patch_summaries(mocker, {"f-1": "x", "f-2": "y"})

    await _refresh(mocker, _dto_with_attachments_across_tasks(),
                   log_rows=[_log_row(task_id=_TASK_FRL)])

    # FRL 已 SUCCESS ⇒ 只剩 CRL 的 f-1 要解析；f-2 只在 FRL 上 ⇒ 不解析
    assert [c.kwargs["file_id"] for c in summarize.await_args_list] == ["f-1"]


async def test_attachment_without_a_file_name_is_skipped(mocker):
    acomplete = _patch_llm(mocker, _output())
    summarize = _patch_summaries(mocker, {})
    payload = copy.deepcopy(_INPUT)
    payload["tasks"][0]["questions"][0]["attachments"] = [{"fileId": "f-1", "fileName": None}]

    await _refresh(mocker, GapAnalysisRefreshInputDTO.model_validate(payload))

    summarize.assert_not_awaited()
    first = _dimension_json(acomplete)["questions"][0]["attachments"][0]
    assert first["summaryAvailable"] is False and "summary" not in first


async def test_mixed_success_and_failure_keeps_the_good_one(mocker):
    acomplete = _patch_llm(mocker, _output())

    async def _one_fails(*, file_id: str, title: str) -> str:
        if file_id == "f-2":
            raise RuntimeError("parse blew up")
        return "good summary"

    _patch_summaries(mocker, side_effect=_one_fails)

    statuses, _ = await _refresh(mocker, _dto_with_attachments_across_tasks())

    frl = _attachments_in_prompt(acomplete, "FRL")
    assert frl[0]["summary"] == "good summary" and frl[1]["summaryAvailable"] is False
    assert all(s.status == "SUCCESS" for s in statuses), "一份附件失败不阻断分析"


async def test_summary_concurrency_is_capped(mocker):
    _patch_llm(mocker, _output())
    mocker.patch.object(svc, "_ATTACHMENT_SUMMARY_CONCURRENCY", 2)
    inflight, peak = 0, 0

    async def _slow(*, file_id: str, title: str) -> str:
        nonlocal inflight, peak
        inflight += 1
        peak = max(peak, inflight)
        await asyncio.sleep(0.01)
        inflight -= 1
        return "s"

    _patch_summaries(mocker, side_effect=_slow)
    payload = copy.deepcopy(_INPUT)
    payload["tasks"][0]["questions"][0]["attachments"] = [
        {"fileId": f"f-{i}", "fileName": f"doc{i}.pdf"} for i in range(5)]

    await _refresh(mocker, GapAnalysisRefreshInputDTO.model_validate(payload))

    assert peak == 2, f"并发闸没生效（峰值 {peak}），会打爆共享线程池"


async def test_stage_timeout_degrades_the_unfinished_ones(mocker):
    acomplete = _patch_llm(mocker, _output())
    mocker.patch.object(svc, "_ATTACHMENT_SUMMARY_STAGE_TIMEOUT_SECONDS", 0.05)

    async def _one_fast_one_stuck(*, file_id: str, title: str) -> str:
        if file_id == "f-2":
            await asyncio.sleep(3600)
        return f"summary of {file_id}"

    _patch_summaries(mocker, side_effect=_one_fast_one_stuck)

    statuses, _ = await _refresh(mocker, _dto_with_attachments_across_tasks())

    assert all(s.status == "SUCCESS" for s in statuses), "阶段超时不该让任务失败"
    frl = _attachments_in_prompt(acomplete, "FRL")
    assert frl[0]["summaryAvailable"] is True and frl[0]["summary"] == "summary of f-1"
    assert frl[1]["summaryAvailable"] is False


async def test_no_attachment_means_no_summarization(mocker):
    _patch_llm(mocker, _output())
    summarize = _patch_summaries(mocker, {})

    await _refresh(mocker)

    summarize.assert_not_awaited()


# ============================================================================
# items（契约 §6.2）
# ============================================================================


async def test_items_groups_by_task_and_keeps_the_read_order(mocker):
    db = _patch_db(mocker, log_rows=[_log_row(task_id=_TASK_FRL), _log_row(id="l-2", task_id=_TASK_CRL)],
                   item_rows=[
                       _item_row(id="i-1", task_id=_TASK_CRL, item_type="ACTION",
                                 content="Track churn monthly", severity=None, sort_order=0),
                       _item_row(id="i-2", task_id=_TASK_CRL, item_type="GAP",
                                 content="Churn not tracked", severity="MEDIUM", sort_order=0),
                       _item_row(id="i-3", task_id=_TASK_CRL, item_type="NARRATIVE",
                                 content="CRL narrative", severity=None, sort_order=0),
                       _item_row(id="i-4", task_id=_TASK_FRL, item_type="GAP",
                                 content="No audit committee", severity="HIGH", sort_order=0),
                       _item_row(id="i-5", task_id=_TASK_FRL, item_type="GAP",
                                 content="Cap table not reconciled", severity="LOW", sort_order=1),
                   ])

    groups = await svc.items([_TASK_FRL, _TASK_CRL])

    by_task = {g.task_id: g for g in groups}
    assert set(by_task) == {_TASK_FRL, _TASK_CRL}
    assert by_task[_TASK_CRL].narrative == "CRL narrative"
    assert [(g.title, g.severity) for g in by_task[_TASK_CRL].gaps] == [("Churn not tracked", "MEDIUM")]
    assert [a.title for a in by_task[_TASK_CRL].actions] == ["Track churn monthly"]
    assert by_task[_TASK_FRL].narrative is None
    assert [(g.title, g.severity) for g in by_task[_TASK_FRL].gaps] == [
        ("No audit committee", "HIGH"), ("Cap table not reconciled", "LOW")]
    db.item.find_by_task_ids.assert_called_once()
    assert set(db.item.find_by_task_ids.call_args.args[1]) == {_TASK_FRL, _TASK_CRL}
    db.session.commit.assert_not_called()


async def test_items_only_looks_at_succeeded_tasks(mocker):
    db = _patch_db(mocker, log_rows=[_log_row(task_id=_TASK_FRL, status="FAILED", has_gap=None),
                                     _log_row(id="l-2", task_id=_TASK_CRL)])

    groups = await svc.items([_TASK_FRL, _TASK_CRL, "t-unknown"])

    assert groups == []
    assert db.item.find_by_task_ids.call_args.args[1] == [_TASK_CRL]


async def test_items_omits_tasks_without_items(mocker):
    _patch_db(mocker, log_rows=[_log_row(task_id=_TASK_FRL, has_gap=False)])

    assert await svc.items([_TASK_FRL]) == []


async def test_items_falls_back_to_medium_for_a_missing_severity(mocker):
    _patch_db(mocker, log_rows=[_log_row()], item_rows=[_item_row(severity=None)])

    [group] = await svc.items([_TASK_FRL])

    assert group.gaps[0].severity == "MEDIUM"


def test_output_dtos_serialize_to_the_java_contract():
    """camel 别名是跨仓契约的一部分：Java 按 taskId / hasGap / narrative / gaps / actions 反序列化。"""
    assert GapTaskStatusDTO(task_id="t", status="FAILED").model_dump(by_alias=True) == {
        "taskId": "t", "status": "FAILED", "hasGap": None}
    dto = GapTaskItemsDTO(task_id="t", narrative="n", gaps=[GapItemDTO(title="g", severity="HIGH")],
                          actions=[GapActionDTO(title="a")])
    assert dto.model_dump(by_alias=True) == {
        "taskId": "t", "narrative": "n", "gaps": [{"title": "g", "severity": "HIGH"}],
        "actions": [{"title": "a"}]}


# ============================================================================
# Request VO 入参边界（契约 §6.1 步骤 1：在边界上直接 422）
# ============================================================================


def _request(**overrides) -> dict:
    return {**_INPUT, **overrides}


def test_request_rejects_empty_tasks():
    with pytest.raises(ValidationError, match="must not be empty"):
        GapAnalysisRefreshRequest.model_validate(_request(tasks=[]))


def test_request_rejects_duplicated_task_id():
    """重复 taskId = 落库只留一份、另一份被唯一键挡下「按成功处理」—— 前一维的结论被安到后一维头上。"""
    with pytest.raises(ValidationError, match="unique"):
        GapAnalysisRefreshRequest.model_validate(
            _request(tasks=[_INPUT["tasks"][0], {**_EXTRA_TASK, "taskId": _TASK_FRL}]))


@pytest.mark.parametrize("task_id", ["", "   "])
def test_request_rejects_blank_task_id(task_id):
    with pytest.raises(ValidationError, match="blank"):
        GapAnalysisRefreshRequest.model_validate(
            _request(tasks=[{**_INPUT["tasks"][0], "taskId": task_id}]))


def test_request_rejects_task_id_longer_than_the_column():
    with pytest.raises(ValidationError, match="at most 36"):
        GapAnalysisRefreshRequest.model_validate(
            _request(tasks=[{**_INPUT["tasks"][0], "taskId": "x" * 37}]))


def test_request_normalizes_the_task_id_it_validated():
    request = GapAnalysisRefreshRequest.model_validate(
        _request(tasks=[{**_INPUT["tasks"][0], "taskId": f" {_TASK_FRL} "}]))

    assert request.tasks[0].taskId == _TASK_FRL, "落库拿到的必须是 strip 后的值"


def test_request_accepts_the_normal_payload_and_keeps_the_question_structure():
    request = GapAnalysisRefreshRequest.model_validate(
        _request(tasks=[_INPUT["tasks"][0], _EXTRA_TASK]))

    assert [t.taskId for t in request.tasks] == [_TASK_FRL, _TASK_CRL]
    question = request.tasks[0].questions[1]
    assert (question.questionText, question.eraBand, question.founderYesNo, question.gsvYesNo) == (
        "Is there an audit committee?", 3, False, True)
    assert request.tasks[0].questions[0].attachments == []


def test_request_ignores_legacy_keys():
    """旧契约的键（organizationId / dimensions / noGapDimensions / analyzedContext / index / code /
    submissionSignature）一律被 pydantic 忽略，不再是模型字段。"""
    request = GapAnalysisRefreshRequest.model_validate(_request(
        organizationId="o-1", dimensions=[], noGapDimensions=[], analyzedContext=[],
        tasks=[{**_INPUT["tasks"][0], "index": 1, "code": "FRL", "submissionSignature": "a" * 64}]))

    for legacy in ("organizationId", "dimensions", "noGapDimensions", "analyzedContext"):
        assert not hasattr(request, legacy)
    for legacy in ("index", "code", "submissionSignature"):
        assert not hasattr(request.tasks[0], legacy)


def test_items_request_rejects_empty_and_blank():
    with pytest.raises(ValidationError, match="must not be empty"):
        GapAnalysisItemsRequest.model_validate({"taskIds": []})
    with pytest.raises(ValidationError, match="must not be blank"):
        GapAnalysisItemsRequest.model_validate({"taskIds": ["", _TASK_FRL]})


def test_items_request_dedupes_and_keeps_order():
    request = GapAnalysisItemsRequest.model_validate(
        {"taskIds": [_TASK_CRL, _TASK_FRL, f" {_TASK_CRL} ", _TASK_FRL]})

    assert request.taskIds == [_TASK_CRL, _TASK_FRL]


def test_items_request_rejects_over_long_ids():
    with pytest.raises(ValidationError, match="at most 36"):
        GapAnalysisItemsRequest.model_validate({"taskIds": ["x" * 37]})


# ============================================================================
# 路由：HTTP 语义（422 / 200 / 信封 / 只剩两条 POST）
# ============================================================================


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from common.auth.identity import get_current_user
    from erl.interfaces.routes import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=_USER, company_id=None, organization_id=None)
    return TestClient(app)


def test_route_returns_422_for_an_empty_task_list():
    response = _client().post("/api/ai/erl/gap-analysis/refresh",
                              json={"companyId": "c-1", "period": "2026Q1", "tasks": []})

    assert response.status_code == 422


def test_route_returns_200_with_per_task_status_even_when_a_task_failed(mocker):
    refresh = mocker.patch.object(svc, "refresh", AsyncMock(
        return_value=[GapTaskStatusDTO(task_id=_TASK_FRL, status="FAILED")]))

    response = _client().post("/api/ai/erl/gap-analysis/refresh", json=_INPUT)

    assert response.status_code == 200
    assert response.json() == {"success": True, "code": 0, "message": "OK",
                               "data": {"tasks": [{"taskId": _TASK_FRL, "status": "FAILED", "hasGap": None}]}}
    assert refresh.await_args.kwargs["user_id"] == _USER, "created_by 取自登录态"


def test_route_items_returns_the_grouped_envelope(mocker):
    mocker.patch.object(svc, "items", AsyncMock(return_value=[
        GapTaskItemsDTO(task_id=_TASK_FRL, narrative="n",
                        gaps=[GapItemDTO(title="g", severity="HIGH")], actions=[GapActionDTO(title="a")])]))

    response = _client().post("/api/ai/erl/gap-analysis/items", json={"taskIds": [_TASK_FRL]})

    assert response.status_code == 200
    assert response.json() == {"success": True, "code": 0, "message": "OK", "data": {"items": [
        {"taskId": _TASK_FRL, "narrative": "n", "gaps": [{"title": "g", "severity": "HIGH"}],
         "actions": [{"title": "a"}]}]}}


def test_router_only_exposes_refresh_and_items():
    from erl.interfaces.routes import router

    assert sorted((r.path, tuple(sorted(r.methods))) for r in router.routes) == [
        ("/api/ai/erl/gap-analysis/items", ("POST",)),
        ("/api/ai/erl/gap-analysis/refresh", ("POST",)),
    ]
    assert not hasattr(svc, "share") and not hasattr(svc, "get")
    assert isinstance(res.GapAnalysisRefreshResponse.model_fields["data"].annotation, type)
```

- [ ] **Step 4: 轻量校验（只编译 + lint，不跑）**

```powershell
uv run python -m py_compile tests/erl/test_erl_gap_analysis_service.py
uv run ruff check tests/erl
```

同时确认旧引用已清零：`grep -rn "gap_analysis_lock\|erl.infrastructure\|GapAnalysisInputDTO\|GapAnalysisProductDTO\|noGapDimensions\|analyzedContext\|shared_snapshot" source/erl tests/erl` 应无输出（`source/ai/prompts/erl/erl_gap_analysis.md` 的 changelog 里保留历史提法，不在此范围）。

---

### Task 9: 文档同步（CLAUDE.md ERL 段、caller_node docstring、台账拟改文案）

**Files:**
- Modify: `CIOaas-python/CLAUDE.md`（「## Exit Readiness（ERL）域」整段，原第 198-212 行）
- Modify: `source/common/enums/caller_node.py`（第 93 行 docstring）
- Modify（**需用户确认后再改**）: `CIOaas-python/docs/待优化项.md`（:123 / :126 / :127 / :132）、`CIOaas-python/docs/已完成优化.md`

- [ ] **Step 1: 替换 `CIOaas-python/CLAUDE.md` 的「## Exit Readiness（ERL）域」段（从该标题到「设计：LG `docs/Exit Readiness/设计/design-doc.md` + `erl-gap-analysis-dev-design.md` §6。」一行为止，整段换成下文）**

```markdown
## Exit Readiness（ERL）域

`source/erl/` 是 Exit Readiness 的 **Goldie 差距分析 AI 内容**（调用方只有 Java，内网同步 HTTP，前端不可达）。**任务化（sprint119，2026-09-24）起两个端点**：`POST /api/ai/erl/gap-analysis/refresh`（按 Java 维度任务逐个生成并落库，逐任务回 `{taskId, status, hasGap}`）、`POST /api/ai/erl/gap-analysis/items`（按任务 id 取已 SUCCESS 任务的条目 `{taskId, narrative, gaps[{title, severity}], actions[{title}]}`）。`GET /gap-analysis` 与 `POST /share` 已删除——编排状态（报告分享记录 + 按维度任务 + 状态机 + Share）归 Java。**答题附件没有独立端点**：摘要在 `refresh` 内**现场生成、不落任何库**——按 fileId **跨任务**去重后并发（信号量 3）逐份「下载 → 解析 → 一次摘要 LLM」，单份超时 90s、阶段总闸 120s，失败/超时一律降级 `summaryAvailable=false` 继续；已 SUCCESS 任务的附件不解析。

**表归属（2026-09-24 起）**：Python 只持有 AI 内容两张表 **`ai_erl_gap_analysis_task`**（生成日志 + 幂等标记：一个 Java 任务 id 一行，`status` SUCCESS/FAILED，`has_gap`，**SUCCESS 是终态**、FAILED 可被下一次尝试就地更新——本域唯一允许 UPDATE 的表）+ **`ai_erl_gap_analysis_task_item`**（条目 NARRATIVE/GAP/ACTION，`content` 1024，**一次写入永不改**；唯一索引 `(任务 id, item_type, sort_order)` 兼双跑兜底），迁移 `V028__sprint119_erl_gap_analysis_task.sql`（**部署要 GRANT SELECT/INSERT/UPDATE/DELETE 给 Python DB role**）。旧三张 `ai_erl_gap_analysis` / `_dimension` / `_item` 与其 ORM / 仓储**本次保留、随 V029 DROP**（存量不回填）。分层 `interfaces` + `application` + `domain`（`enums.py` + 两模型 + 两仓储），**无 `infrastructure`**（Redis 期次锁已删）。**其余 ERL 业务表（评估 / 维度配置 / 题库 / 附件）仍属 Java，Python 不查、不做公司 ACL**（Java 调用前已校验）。

四条落地口径：

- **每任务一次 LLM，prompt 只装一个维度**（`erl_gap_analysis.md` v1.7，出参 `{narrative, gaps[{title, severity}], actions[{title}]}`）：`refresh` 开头**批量查日志表**，已 SUCCESS 的任务直接回状态、不进附件摘要也不进 LLM；其余任务 `asyncio.Semaphore(3)` 并发，LLM 重试 2 次退避 2s/4s、SDK 传输级重试关 0。**单任务失败只影响它自己**：日志行 FAILED（不写条目）、回 `hasGap=null`，Java 按自愈规则重投。`taskId` / `fileId` **绝不进 prompt**（`_PROMPT_EXCLUDE`）。
- **不再有 index↔code 整批校验、summary、analyzedContext、noGapDimensions、share 快照**：零感知差维度由 Java 建任务时直接置 SUCCESS/has_gap=false、不派发；出参再无 note / why / evidenceMissing / model / generatedAt（决策 D7）。**输出没有 `gaps` 数组 ⇒ 该任务 FAILED**，绝不降级成「无差距」（那是绿点 No Gap 的假阴性）；无 gaps 时丢 narrative；severity 越界归一 MEDIUM。
- **一个事务写日志行 + 条目；撞唯一键按成功处理**：同一任务被双跑时后提交的一路在 commit 撞 `uk_ai_erl_gap_analysis_task_item`（或日志行唯一约束）→ rollback → 重查日志行为 SUCCESS → 回先到者的 `has_gap`；FAILED 永不覆盖 SUCCESS（仓储 UPDATE 带 `status <> 'SUCCESS'`）。**没有 Redis 锁**：单派发靠 Java 任务表 CAS。
- **HTTP 语义**：入参错 422（pydantic 原生：tasks 非空、taskId 非空 ≤36 唯一；taskIds 非空去重）；其余一律 200（失败在 `status` 里）；非预期异常 500。`created_by` = `ctx.user_id`（Java 转发调用者 Bearer）。

设计：LG `docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md`（任务化）+ `docs/Exit Readiness/设计/design-doc.md`。
```

- [ ] **Step 2: 改 `source/common/enums/caller_node.py` 第 93 行 docstring**

原文：
```python
    """ERL：差距分析生成（单次调用产出一份分析，无 audience 分端；REST 端点非图节点）"""
```
改为：
```python
    """ERL：差距分析生成（任务化起每任务一次调用、prompt 只装一个维度；REST 端点非图节点）"""
```

- [ ] **Step 3: 台账——先向用户出示拟改文案，确认后再落笔（本步不自动执行）**

拟改 `docs/待优化项.md`：

- **:123**（旧 Java 产物表待 DROP + 授权）→ 改口为：「旧 Java 两表 `erl_gap_analysis` / `erl_gap_analysis_item` 由 Java sprint119 升级脚本 DROP（设计 §9.1）；Python 侧授权对象改为 V028 两张新表 `ai_erl_gap_analysis_task` / `ai_erl_gap_analysis_task_item`；旧 Python 三表 `ai_erl_gap_analysis` / `_dimension` / `_item`（含触发器与函数）连同 ORM / 仓储 / `tests/erl/test_erl_gap_analysis_repository.py` 待功能验证通过后 **V029** 一并 DROP / 删除」。
- **:126**（`ai_erl_gap_analysis.submission_signature` 列废弃）→ 并入上一条：该列随 V029 整表 DROP，不再单独做列级 DROP；`overwrite_generated` 那个恒传 None 的入参随旧仓储删除。
- **:127**（`analyzedContext` 回传 + 无体积上限）→ **移至 `docs/已完成优化.md`**：「（2026-09-24 完成）任务化把 `analyzedContext` 入参整体删除（prompt v1.7 每任务只装一个维度、不再写跨维 summary），漂移与 token 预算两个问题随之消失（涉及 `source/erl/**`、`source/ai/prompts/erl/erl_gap_analysis.md`）」。
- **:132**（V027 存量已分享行的读路径兜底）→ **移至 `docs/已完成优化.md`**：「（2026-09-24 完成）随 `erl_gap_analysis_service` 任务化重写整段删除（连同 `shared_snapshot` / `_snapshot_is_current` / share 端点）；旧表与快照列随 V029 DROP」。
- **新增一条**（来源：设计稿 §11）：「**ERL 任务化后 Python 条目表的孤儿行待清理**（2026-09-24）：未分享记录内被 Java 软删（`deleted=true`）的任务，其 `ai_erl_gap_analysis_task` / `_task_item` 行不再被任何读路径引用（Java 按 `result_task_id ?? id` 只取活任务），成为孤儿；量级 = 每次「未分享期间重交」一维一批。设计明确留待后续清理任务处理，清理口径需与 Java 任务表对账（跨库，只能离线脚本）」。

> 依据根 `CLAUDE.md`「优化项台账」规则本应由 Claude 自动维护，但记忆条目「待优化项台账：别主动写」记录过用户回退主动写入的先例，故此处只出文案、等用户一句「照写」再改。

- [ ] **Step 4: 轻量校验**

```powershell
uv run ruff check source/common/enums/caller_node.py
```

CLAUDE.md 为 Markdown，无校验命令；人工通读一遍新段落与 `source/erl/__init__.py` docstring（Task 7 Step 4）口径一致即可。

---

### Task 10: 测试（需用户下令后执行）

- [ ] **Step 1: 等用户明确下达「跑测试」后，一次性跑 erl 全目录**

```powershell
uv run python -m pytest tests/erl -q
```

预期：`test_erl_gap_analysis_service.py`（约 60 例）+ `test_erl_gap_analysis_task_repository.py`（11 例）+ 旧 `test_erl_gap_analysis_repository.py`（旧三仓储仍在，照常通过）全绿；无真实 DB / Redis / LLM 访问。若 `tests/erl` 出现挂起，先按记忆条目「rag 测试无库时会挂住」查本地 PG 端口，不改代码。

- [ ] **Step 2: 顺手跑一次 bootstrap 冒烟（挂载 erl 路由的 main 导入链）**

```powershell
uv run python -m pytest tests/bootstrap -q
```

---

### Task 11: 提交（需用户确认）

- [ ] **Step 1: 等用户确认后，在 `CIOaas-python`（分支 `sprint119`）窄暂存本计划涉及的文件并提交（不 push）**

```bash
cd /d/workspace/github/LG/python/CIOaas-python
git status --short
git add sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql \
        source/erl source/main.py \
        source/ai/prompts/erl/erl_gap_analysis.md source/ai/prompts/erl_gap_analysis_prompts.py \
        source/common/enums/caller_node.py \
        tests/erl/test_erl_gap_analysis_service.py tests/erl/test_erl_gap_analysis_task_repository.py \
        CLAUDE.md
git commit -m "feat(erl): task-based gap analysis - per-task LLM, V028 log/item tables, refresh/items contract

- V028: ai_erl_gap_analysis_task (generation log + idempotency marker, SUCCESS terminal)
  and ai_erl_gap_analysis_task_item (write-once items, unique (task, type, sort_order))
- refresh: batch SUCCESS short-circuit, attachment summaries deduped across tasks,
  Semaphore(3) per-task LLM with 2 retries, one-transaction persist, unique-key collision
  treated as success, FAILED log row without items; statuses returned in input order
- items: grouped narrative / gaps / actions for succeeded tasks
- remove GET /gap-analysis, POST /share, Redis period lock (erl/infrastructure),
  shared_snapshot, V027 fallback, analyzedContext, noGapDimensions, index<->code mapping,
  summary; old ai_erl_gap_analysis* tables, models and repositories kept until V029
- prompt erl_gap_analysis v1.7: single dimension in, {narrative, gaps, actions} out
- tests rewritten for the task contract; repository tests for the two new tables

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

（台账两份文件若用户已确认修改，一并 `git add docs/待优化项.md docs/已完成优化.md`。`git push` 只在用户明确说「推送」时执行。）

---

## 自查清单（设计稿 → Task 对应）

| 设计稿条目 | 内容 | 落在 |
|---|---|---|
| §3.3 `ai_erl_gap_analysis_task` | id / `erl_gap_analysis_dimension_task_id` UNIQUE / status varchar(16) / has_gap / model varchar(64) / 审计四列 + 触发器；`created_by = ctx.user_id` | Task 1（DDL）、Task 2（`ErlGapAnalysisTask`）、Task 6（`_persist_success` / `_persist_failure` 写 `user_id`）、Task 7（路由传 `ctx.user_id`） |
| §3.4 `ai_erl_gap_analysis_task_item` | id / 任务 id / item_type varchar(16) / content varchar(1024) NOT NULL / severity varchar(8) / sort_order NOT NULL / 审计四列 + 触发器；唯一索引 `uk_ai_erl_gap_analysis_task_item (任务 id, item_type, sort_order)`；note / why 不落库 | Task 1、Task 2（`ErlGapAnalysisTaskItem`）、Task 6（`_build_items`：NARRATIVE sort 0 / GAP / ACTION、截 1024） |
| §3 「无 FK、不加 CHECK」 | 全部 IF NOT EXISTS 幂等、英文 COMMENT | Task 1 |
| §6 契约总则 | Java 内网直连、转发 Bearer、AuthMiddleware 不变 | Task 7（routes 只经 `get_current_user` 取身份） |
| §6.1 入参 | `{companyId, period, tasks:[{taskId, name, abbr, weight, founderLevelScore, gsvLevelScore, perceptionGap, founderTerminatedLevel, gsvTerminatedLevel, questions:[…attachments:[{fileId, fileName}]]}]}` | Task 7（`GapAnalysisRefreshRequest` / `GapTaskRequest`）、Task 4（`GapAnalysisRefreshInputDTO` / `GapTaskInputDTO`） |
| §6.1 出参 | `{success, data:{tasks:[{taskId, status: SUCCESS\|FAILED, hasGap}]}}` | Task 7（`GapAnalysisRefreshResponse`）、Task 4（`GapTaskStatusDTO`） |
| §6.1 步骤 1 | 校验 tasks 非空、taskId 唯一（422） | Task 7（`_check_tasks`）、Task 8（Request VO 用例） |
| §6.1 步骤 2 | 附件按 fileId 跨任务去重现场摘要，3 并发 / 90s / 120s，失败降级 | Task 6（`_fill_attachment_summaries` / `_summarize_attachment`）、Task 8（附件用例） |
| §6.1 步骤 3 | 已 SUCCESS 行直接回；否则 Semaphore(3) 一次 LLM（重试 2 次）→ 解析 → 一个事务日志行 upsert + 条目；LLM/解析失败 ⇒ FAILED 行、不写条目；单任务失败不影响其它 | Task 6（`refresh` / `_load_succeeded` / `_run_task` / `_persist_success` / `_persist_failure`）、Task 3（`upsert_by_task_id`）、Task 8 |
| §6.1 步骤 4 | taskId 不进 prompt | Task 6（`_PROMPT_EXCLUDE`）、Task 8（`test_task_id_never_reaches_the_prompt`） |
| §6.1 步骤 5 | 删除 Redis 期次锁；双跑由条目唯一键兜底、撞键按成功 | Task 6（Step 2 删 `infrastructure/`；`_persist_success` IntegrityError 分支）、Task 8 |
| §6.2 items | 入参 `{taskIds}`；出参 `{items:[{taskId, narrative, gaps:[{title, severity}], actions:[{title}]}]}`；无条目的 taskId 不出现 | Task 7（`GapAnalysisItemsRequest` / `GapAnalysisItemsResponse`）、Task 6（`items` / `_load_items`）、Task 4（`GapTaskItemsDTO`）、Task 8 |
| §6.3 删除 | GET /gap-analysis、POST /share、shared_snapshot 全部逻辑、`_snapshot_is_current`、V027 存量兜底、analyzedContext 与 noGapDimensions 入参 | Task 4（DTO 无这些字段）、Task 6（service 重写）、Task 7（routes / VO 重写）、Task 8（`test_request_ignores_legacy_keys` / `test_router_only_exposes_refresh_and_items`） |
| §6.4 prompt v1.7 | 单维输入（无 index / analyzedContext / summary）、输出 `{narrative, gaps[{title, severity}], actions[{title}]}`、无差距时 gaps 空且不输出 narrative、`has_gap = len(gaps) > 0` | Task 5（.md 原地改 + changelog）、Task 6（`_build_user_prompt` / `_parse_dimension`）、Task 8（prompt 回归三例） |
| D7 出参精简 | 砍 summary / analyzedContext / model / generated_at / note / why / evidence_missing / stale / generating / analyzedAt / dimensionStale / sharedAt / sharedBy | Task 4、Task 7、Task 8（`test_extra_output_keys_are_ignored`） |
| §9.1 迁移 | V028 建两表 + 索引 + 触发器 + COMMENT；头注 GRANT 部署项；V029 另出 | Task 1 |
| §9.3 Python 同批清理 | `gap_analysis_lock.py` 删除；service 落库 / 读取 / share / 快照全部重写；旧 ORM 与仓储随 V029 | Task 6、「文件结构 · 不动」 |
| §9.3 文档 | `CIOaas-python/CLAUDE.md` ERL 段；台账 PY-TODO:123 / 126 / 127 / 132 | Task 9 |
| §10 Python 测试 | 单任务 LLM 流程与并发、SUCCESS 日志短路、FAILED 日志、条目唯一键撞键按成功、items 分组、prompt v1.7 结构回归、Request VO 422 边界、V028 幂等重跑 | Task 8（前七项）、Task 3（仓储语句）、Task 1 Step 2（V028 幂等靠 IF NOT EXISTS + DROP TRIGGER IF EXISTS，人工在测试库重跑两遍核验） |
| 记忆事项 | Windows 用 `uv run`；提示词原地改不改名、version 1.7 + changelog | 全计划命令均 `uv run ...`；Task 5 |

**类型名 / 函数名一致性核对**（全计划内唯一拼写）：`ErlGapAnalysisTask` / `ErlGapAnalysisTaskItem`（属性 `task_id` ↔ 列 `erl_gap_analysis_dimension_task_id`）；`GapTaskStatus` / `GapItemType`；`erl_gap_analysis_task_repository.find_by_task_ids` / `upsert_by_task_id`；`erl_gap_analysis_task_item_repository.find_by_task_ids` / `bulk_insert`；DTO `GapAttachmentDTO` / `GapQuestionDTO` / `GapTaskInputDTO` / `GapAnalysisRefreshInputDTO` / `GapItemDTO` / `GapActionDTO` / `GapDimensionResultDTO` / `GapTaskStatusDTO` / `GapTaskItemsDTO`；service `refresh(dto, *, user_id)` / `items(task_ids)` / `_load_succeeded` / `_run_task` / `_build_user_prompt` / `_call_llm_with_retry` / `_call_llm` / `_parse_dimension` / `_normalize_severity` / `_fill_attachment_summaries` / `_summarize_attachment` / `_persist_success` / `_persist_failure` / `_build_items` / `_load_items` / `_truncate`；VO `GapAttachment` / `GapQuestion` / `GapTaskRequest` / `GapAnalysisRefreshRequest` / `GapAnalysisItemsRequest` / `GapTaskStatus` / `GapAnalysisRefreshData` / `GapAnalysisRefreshResponse` / `GapItem` / `GapAction` / `GapTaskItems` / `GapAnalysisItemsData` / `GapAnalysisItemsResponse`；路由函数 `refresh_gap_analysis` / `list_gap_analysis_items`；prompt 变量 `company_id` / `period` / `dimension_json`。
