# Playbook Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/devSupport/Playbook Knowledge` page that recalls playbook chunks (vector-only or vector+graph) and shows a per-playbook relationship graph + related chunks in a detail Drawer.

**Architecture:** Reuse the `playbooks_graph_db` prototype — vectors in pgvector (`public.ai_rag_playbook_chunk`, lg_test), graph in LadybugDB (local single-file). Backend adds an `interfaces/` layer over the existing `PlaybookRecallService` (two new methods: `recall_list`, `graph_detail`) exposing `POST /api/ai/playbook/recall` + `GET /api/ai/playbook/detail`. Frontend adds a page under `/devSupport` calling those via `@/utils/request`, rendering the relationship graph with ECharts.

**Tech Stack:** Python 3.12 / FastAPI / pydantic / psycopg / real_ladybug (Kuzu fork); React 16 / UmiJS 3 / Ant Design 4.9 / echarts + echarts-for-react; pytest (asyncio_mode=auto).

**Design spec:** `docs/superpowers/specs/2026-06-23-playbook-knowledge-design.md`

---

## File Structure

**Backend (`python/CIOaas-python/`):**
- Modify `source/playbooks_graph_db/import_playbooks.py` — release LadybugDB lock via `.close()` (enables same-process read-only reopen).
- Modify `source/playbooks_graph_db/chatbot_playbook_service.py` — add `rel_type`/`via_pid` to `PlaybookHit`, add `PlaybookNotFoundError`, add `recall_list` / `_direct_rel_map` / `graph_detail`.
- Create `source/playbooks_graph_db/interfaces/__init__.py`
- Create `source/playbooks_graph_db/interfaces/vo.py` — pydantic Request/Response VO.
- Create `source/playbooks_graph_db/interfaces/routes.py` — `APIRouter(prefix="/api/ai/playbook")` + lazy service singleton.
- Modify `source/main.py` — mount the router.
- Create `tests/playbooks_graph_db/__init__.py`, `tests/playbooks_graph_db/conftest.py`, `tests/playbooks_graph_db/test_recall_list.py`, `tests/playbooks_graph_db/test_graph_detail.py`, `tests/playbooks_graph_db/test_routes.py`.

**Frontend (`web/CIOaas-web/`):**
- Create `src/services/api/playbook/playbookApi.ts` — typed API client.
- Create `src/pages/ai/playbookKnowledge/index.tsx` — search + result list.
- Create `src/pages/ai/playbookKnowledge/components/RelationGraph.tsx` — ECharts graph series.
- Create `src/pages/ai/playbookKnowledge/components/DetailDrawer.tsx` — detail Drawer.
- Modify `config/routes.ts` — add route entry.
- Modify `src/pages/ai/devSupport/DevSupportShell.tsx` — add nav group/item.

---

## Task 1: Release LadybugDB lock with `.close()` in the importer

**Files:**
- Modify: `source/playbooks_graph_db/import_playbooks.py` (the `finally` block of `build_graph_ladybug`)

Background: `Database.close()` + `Connection.close()` exist; using them (instead of `del`) deterministically releases the single-writer file lock so the service / tests can open the DB `read_only` in the same process.

- [ ] **Step 1: Replace the `del` cleanup with explicit close**

In `build_graph_ladybug`, change the `finally` block from:
```python
    finally:
        # 释放 DB 写锁（Kuzu 单写者文件锁），便于随后服务进程只读打开。
        del conn
        del db
```
to:
```python
    finally:
        # 释放 DB 写锁（Kuzu 单写者文件锁）：显式 close 才能让同进程随后 read_only 打开。
        conn.close()
        db.close()
```

- [ ] **Step 2: Verify import still works**

Run: `PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -u source/playbooks_graph_db/import_playbooks.py --graph-only`
Expected: log `LadybugDB 图写入完成：64 playbooks / 28 edges ...`, exit 0.

- [ ] **Step 3: Commit**

```bash
git add source/playbooks_graph_db/import_playbooks.py
git commit -m "fix(playbook): close LadybugDB handles to release lock for read-only reopen"
```

---

## Task 2: Add `recall_list` + `_direct_rel_map` to the service

**Files:**
- Modify: `source/playbooks_graph_db/chatbot_playbook_service.py`
- Create: `tests/playbooks_graph_db/__init__.py` (empty)
- Create: `tests/playbooks_graph_db/conftest.py`
- Create: `tests/playbooks_graph_db/test_recall_list.py`

- [ ] **Step 1: Add fields to `PlaybookHit`**

In the `PlaybookHit` dataclass add two optional fields (after `source`):
```python
    rel_type: str | None = None   # graph 项：连入边的 rtype（仅直接邻居有值）
    via_pid: str | None = None    # graph 项：从哪个命中 playbook 扩展而来
```

- [ ] **Step 2: Write the conftest fixture (tiny LadybugDB graph)**

Create `tests/playbooks_graph_db/__init__.py` (empty file) and `tests/playbooks_graph_db/conftest.py`:
```python
"""Builds a tiny LadybugDB graph in a temp dir and returns a service pointed at it.

Graph: a -DEPENDS_ON-> b -DEPENDS_ON-> c ; a -FEEDS-> d
pgvector-dependent methods (recall / _fetch_by_pids) are mocked by individual tests.
"""
import pytest
import real_ladybug as kz
from playbooks_graph_db.chatbot_playbook_service import PlaybookRecallService


@pytest.fixture
def graph_svc(tmp_path):
    db_path = tmp_path / "g"
    db = kz.Database(str(db_path))
    conn = kz.Connection(db)
    conn.execute(
        "CREATE NODE TABLE Playbook(pid STRING, title STRING, category STRING, "
        "stage STRING, frequency STRING, description STRING, PRIMARY KEY(pid))"
    )
    conn.execute("CREATE REL TABLE PlayRel(FROM Playbook TO Playbook, rtype STRING, metric STRING)")
    for pid, title in [("a", "A"), ("b", "B"), ("c", "C"), ("d", "D")]:
        conn.execute(
            "CREATE (:Playbook {pid:$pid, title:$t, category:'Cat', stage:'All Stages', "
            "frequency:'', description:''})",
            {"pid": pid, "t": title},
        )
    for f, t, rt, m in [("a", "b", "DEPENDS_ON", ""), ("b", "c", "DEPENDS_ON", ""), ("a", "d", "FEEDS", "nps")]:
        conn.execute(
            "MATCH (x:Playbook {pid:$f}),(y:Playbook {pid:$t}) "
            "CREATE (x)-[:PlayRel {rtype:$rt, metric:$m}]->(y)",
            {"f": f, "t": t, "rt": rt, "m": m},
        )
    conn.close()
    db.close()
    # dsn is dummy: tests mock every pgvector-touching method.
    return PlaybookRecallService(dsn="postgresql://u:p@127.0.0.1:5432/x", graph_db_path=str(db_path))
```

- [ ] **Step 3: Write the failing tests for `recall_list`**

Create `tests/playbooks_graph_db/test_recall_list.py`:
```python
from unittest.mock import AsyncMock

from playbooks_graph_db.chatbot_playbook_service import PlaybookHit


def _vhit(pid):
    return PlaybookHit(pid=pid, title=pid.upper(), category="Cat", stage="All Stages",
                       content=f"{pid} vector body", score=0.9, recall_rank=1, source="vector")


def _profile(pids):
    return [PlaybookHit(pid=p, title=p.upper(), category="Cat", stage="All Stages",
                        content=f"{p} profile", score=0.0, recall_rank=0, source="graph") for p in pids]


async def test_recall_list_vector_only(graph_svc):
    graph_svc.recall = AsyncMock(return_value=[_vhit("a")])
    out = await graph_svc.recall_list("q", top_k=5, use_graph=False)
    assert [h.pid for h in out] == ["a"]
    assert all(h.source == "vector" for h in out)


async def test_recall_list_with_graph_merges_and_annotates(graph_svc):
    graph_svc.recall = AsyncMock(return_value=[_vhit("a")])
    graph_svc._fetch_by_pids = lambda pids: _profile(pids)
    out = await graph_svc.recall_list("q", top_k=5, use_graph=True, hops=3)
    pids = [h.pid for h in out]
    assert pids[0] == "a"                       # vector hits first
    assert set(pids) >= {"a", "b", "c", "d"}    # graph reachable from a within 3 hops
    b = next(h for h in out if h.pid == "b" and h.source == "graph")
    assert b.via_pid == "a" and b.rel_type == "DEPENDS_ON"   # direct neighbor annotated
    c = next(h for h in out if h.pid == "c")
    assert c.source == "graph" and c.rel_type is None         # 2-hop: no single rtype
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/playbooks_graph_db/test_recall_list.py -v`
Expected: FAIL — `AttributeError: 'PlaybookRecallService' object has no attribute 'recall_list'`.

- [ ] **Step 5: Implement `recall_list` + `_direct_rel_map`**

Add these methods to `PlaybookRecallService` (after `answer`, before `_build_user_prompt`):
```python
    async def recall_list(
        self, query: str, top_k: int = 5, use_graph: bool = False, hops: int = 3
    ) -> list[PlaybookHit]:
        """向量召回(chunk 级) + 可选图扩展(沿 PlayRel 出边 hops 跳)。返回合并列表，总数可超 top_k。"""
        hits = await self.recall(query, top_k)            # source="vector"
        if not use_graph:
            return hits
        seed_pids = list(dict.fromkeys(h.pid for h in hits))
        related_pids = self._graph_expand(seed_pids, hops)   # 可达 pid（已剔除种子）
        if not related_pids:
            return hits
        direct = self._direct_rel_map(seed_pids)             # {target_pid: (seed_pid, rtype)}
        graph_hits: list[PlaybookHit] = []
        for ph in self._fetch_by_pids(related_pids):         # source="graph" 的 profile
            via, rtype = direct.get(ph.pid, (None, None))
            graph_hits.append(replace(ph, via_pid=via, rel_type=rtype))
        return hits + graph_hits

    def _direct_rel_map(self, seed_pids: list[str]) -> dict[str, tuple[str, str]]:
        """种子 playbook 的直接出邻居 → (seed_pid, rtype)；多 seed 命中取首个。"""
        if not seed_pids:
            return {}
        res = self._graph().execute(
            "MATCH (s:Playbook)-[r:PlayRel]->(n:Playbook) WHERE s.pid IN $s "
            "RETURN s.pid, n.pid, r.rtype",
            {"s": list(seed_pids)},
        )
        out: dict[str, tuple[str, str]] = {}
        while res.has_next():
            s, n, rtype = res.get_next()
            out.setdefault(n, (s, rtype))
        return out
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/playbooks_graph_db/test_recall_list.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add source/playbooks_graph_db/chatbot_playbook_service.py tests/playbooks_graph_db/
git commit -m "feat(playbook): add recall_list (vector + graph-expanded chunks)"
```

---

## Task 3: Add `graph_detail` + `PlaybookNotFoundError` to the service

**Files:**
- Modify: `source/playbooks_graph_db/chatbot_playbook_service.py`
- Create: `tests/playbooks_graph_db/test_graph_detail.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/playbooks_graph_db/test_graph_detail.py`:
```python
import pytest

from playbooks_graph_db.chatbot_playbook_service import PlaybookHit, PlaybookNotFoundError


def _profile(pids):
    return [PlaybookHit(pid=p, title=p.upper(), category="Cat", stage="All Stages",
                        content=f"{p} profile text", score=0.0, source="graph") for p in pids]


def test_graph_detail_neighborhood(graph_svc):
    graph_svc._fetch_by_pids = lambda pids: _profile(pids)
    d = graph_svc.graph_detail("a", hops=3)
    assert d["playbook"]["pid"] == "a"
    node_pids = {n["pid"] for n in d["graph"]["nodes"]}
    assert node_pids >= {"a", "b", "c", "d"}
    assert any(e["source"] == "a" and e["target"] == "b" and e["relType"] == "DEPENDS_ON"
               for e in d["graph"]["edges"])
    related = {c["pid"] for c in d["relatedChunks"]}
    assert "a" not in related and related >= {"b", "c", "d"}
    assert all(len(c["preview"]) <= 200 for c in d["relatedChunks"])


def test_graph_detail_not_found(graph_svc):
    with pytest.raises(PlaybookNotFoundError):
        graph_svc.graph_detail("zzz")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/playbooks_graph_db/test_graph_detail.py -v`
Expected: FAIL — `ImportError`/`AttributeError` (no `PlaybookNotFoundError` / `graph_detail`).

- [ ] **Step 3: Implement `PlaybookNotFoundError` + `graph_detail`**

Add the exception near the top of the module (after imports, before `PlaybookHit`):
```python
class PlaybookNotFoundError(Exception):
    """graph_detail 时 pid 在图中不存在。"""
```
Add `"PlaybookNotFoundError"` to `__all__`.

Add the method to `PlaybookRecallService` (after `_direct_rel_map`):
```python
    def graph_detail(self, pid: str, hops: int = 3) -> dict:
        """以 pid 为中心的 PlayRel 邻域(双向, ≤hops): 节点 + 边(带 rtype) + 邻居 profile 预览。"""
        conn = self._graph()
        res = conn.execute(
            "MATCH (c:Playbook {pid:$pid}) RETURN c.pid, c.title, c.category, c.stage",
            {"pid": pid},
        )
        if not res.has_next():
            raise PlaybookNotFoundError(pid)
        cpid, ctitle, ccat, cstage = res.get_next()

        res = conn.execute(
            f"MATCH (c:Playbook {{pid:$pid}})-[:PlayRel*1..{int(hops)}]-(n:Playbook) "
            "RETURN DISTINCT n.pid",
            {"pid": pid},
        )
        pids = [pid] + [r[0] for r in _iter(res) if r[0] != pid]

        res = conn.execute(
            "MATCH (n:Playbook) WHERE n.pid IN $p RETURN n.pid, n.title, n.category", {"p": pids}
        )
        nodes = [{"pid": p, "title": t, "category": c} for p, t, c in _iter(res)]

        res = conn.execute(
            "MATCH (a:Playbook)-[r:PlayRel]->(b:Playbook) "
            "WHERE a.pid IN $p AND b.pid IN $p RETURN a.pid, b.pid, r.rtype",
            {"p": pids},
        )
        edges = [{"source": a, "target": b, "relType": rt} for a, b, rt in _iter(res)]

        rt_by_pid = {e["target"]: e["relType"] for e in edges if e["source"] == pid}
        related_pids = [p for p in pids if p != pid]
        related_chunks = [
            {"pid": ph.pid, "title": ph.title, "relType": rt_by_pid.get(ph.pid),
             "preview": ph.content[:200]}
            for ph in self._fetch_by_pids(related_pids)
        ]
        return {
            "playbook": {"pid": cpid, "title": ctitle, "category": ccat, "stage": cstage},
            "graph": {"nodes": nodes, "edges": edges},
            "relatedChunks": related_chunks,
        }
```
Add this small module-level helper (after the imports / before the dataclasses):
```python
def _iter(result):
    """把 LadybugDB QueryResult 迭代成 list[row]。"""
    rows = []
    while result.has_next():
        rows.append(result.get_next())
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/playbooks_graph_db/test_graph_detail.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full module test set**

Run: `uv run pytest tests/playbooks_graph_db/ -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add source/playbooks_graph_db/chatbot_playbook_service.py tests/playbooks_graph_db/test_graph_detail.py
git commit -m "feat(playbook): add graph_detail (neighborhood nodes/edges + related chunks)"
```

---

## Task 4: Backend VO (pydantic Request/Response)

**Files:**
- Create: `source/playbooks_graph_db/interfaces/__init__.py` (empty)
- Create: `source/playbooks_graph_db/interfaces/vo.py`

- [ ] **Step 1: Create the VO module**

Create `source/playbooks_graph_db/interfaces/__init__.py` (empty) and `source/playbooks_graph_db/interfaces/vo.py`:
```python
"""Playbook Knowledge 接口 VO（信封 {success, code, message, data}；JSON key lowerCamelCase）。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RecallRequest(BaseModel):
    inputContent: str = Field(min_length=1)
    topK: int = Field(default=5, ge=1, le=50)
    useGraph: bool = False


class RecallItem(BaseModel):
    pid: str
    title: str
    category: str | None = None
    stage: str | None = None
    chunkType: str
    seq: int
    preview: str
    source: str            # "vector" | "graph"
    score: float | None = None
    relType: str | None = None
    viaPid: str | None = None


class RecallData(BaseModel):
    items: list[RecallItem] = Field(default_factory=list)
    vectorCount: int = 0
    graphCount: int = 0


class RecallResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: RecallData | None = None


class GraphNode(BaseModel):
    pid: str
    title: str
    category: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relType: str


class RelatedChunk(BaseModel):
    pid: str
    title: str
    relType: str | None = None
    preview: str


class GraphPayload(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class DetailData(BaseModel):
    playbook: GraphNode
    graph: GraphPayload
    relatedChunks: list[RelatedChunk] = Field(default_factory=list)


class DetailResponse(BaseModel):
    success: bool
    code: int
    message: str
    data: DetailData | None = None
```

- [ ] **Step 2: Verify it imports**

Run: `cd python/CIOaas-python && uv run python -c "from playbooks_graph_db.interfaces import vo; print('ok', vo.RecallRequest.__name__)"`
Expected: prints `ok RecallRequest`.

- [ ] **Step 3: Commit**

```bash
git add source/playbooks_graph_db/interfaces/__init__.py source/playbooks_graph_db/interfaces/vo.py
git commit -m "feat(playbook): add interfaces VO for recall/detail"
```

---

## Task 5: Backend routes + mount

**Files:**
- Create: `source/playbooks_graph_db/interfaces/routes.py`
- Modify: `source/main.py`
- Create: `tests/playbooks_graph_db/test_routes.py`

- [ ] **Step 1: Create the router**

Create `source/playbooks_graph_db/interfaces/routes.py`:
```python
"""Playbook Knowledge REST: /api/ai/playbook/*（登录即可，数据全局）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from common.auth.identity import get_current_user
from common.redis.auth_store import AuthUser
from playbooks_graph_db.chatbot_playbook_service import (
    PlaybookNotFoundError,
    PlaybookRecallService,
)
from playbooks_graph_db.interfaces import vo

router = APIRouter(prefix="/api/ai/playbook", tags=["Playbook Knowledge"])

_service: PlaybookRecallService | None = None


def _svc() -> PlaybookRecallService:
    global _service
    if _service is None:
        _service = PlaybookRecallService()
    return _service


def _preview(text: str) -> str:
    return (text or "")[:200]


@router.post("/recall", response_model=vo.RecallResponse)
async def recall(req: vo.RecallRequest, ctx: AuthUser = Depends(get_current_user)) -> vo.RecallResponse:
    hits = await _svc().recall_list(req.inputContent, top_k=req.topK, use_graph=req.useGraph)
    items = [
        vo.RecallItem(
            pid=h.pid, title=h.title, category=h.category, stage=h.stage,
            chunkType=getattr(h, "chunk_type", "profile"), seq=getattr(h, "seq", 0),
            preview=_preview(h.content), source=h.source,
            score=h.score if h.source == "vector" else None,
            relType=h.rel_type, viaPid=h.via_pid,
        )
        for h in hits
    ]
    vector_count = sum(1 for it in items if it.source == "vector")
    data = vo.RecallData(items=items, vectorCount=vector_count, graphCount=len(items) - vector_count)
    return vo.RecallResponse(success=True, code=0, message="OK", data=data)


@router.get("/detail", response_model=vo.DetailResponse)
async def detail(pid: str = Query(min_length=1), ctx: AuthUser = Depends(get_current_user)) -> vo.DetailResponse:
    try:
        d = _svc().graph_detail(pid)
    except PlaybookNotFoundError:
        return vo.DetailResponse(success=False, code=404, message=f"playbook not found: {pid}", data=None)
    return vo.DetailResponse(success=True, code=0, message="OK", data=vo.DetailData(**d))
```

Note: `PlaybookHit` currently has no `chunk_type`/`seq` fields — `_vector_search` does not set them. They ARE needed for the response. Add them in Step 2.

- [ ] **Step 2: Add `chunk_type`/`seq` to `PlaybookHit` and populate in `_vector_search`**

In `chatbot_playbook_service.py`, add to `PlaybookHit` (after `via_pid`):
```python
    chunk_type: str = "profile"
    seq: int = 0
```
In `_vector_search`, update the SQL + row mapping to also select `chunk_type, seq`:
```python
        sql = """
            SELECT pid, title, metadata->>'category', metadata->>'stage', content,
                   chunk_type, seq, 1 - (embedding <=> %s::vector) AS similarity
            FROM public.ai_rag_playbook_chunk
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (vec_literal, vec_literal, top_k))
            rows = cur.fetchall()
        return [
            PlaybookHit(
                pid=r[0], title=r[1], category=r[2], stage=r[3], content=r[4],
                chunk_type=r[5], seq=r[6], score=float(r[7]), recall_rank=i + 1,
            )
            for i, r in enumerate(rows)
        ]
```
(`_fetch_by_pids` returns profile chunks; leave its `PlaybookHit(...)` as-is — `chunk_type` defaults to `"profile"`, `seq` to `0`.)

- [ ] **Step 3: Mount the router in `main.py`**

In `source/main.py`, alongside the other `from X import router as Y` lines add:
```python
from playbooks_graph_db.interfaces.routes import router as playbook_router
```
and alongside the other `app.include_router(...)` calls add:
```python
app.include_router(playbook_router)
```

- [ ] **Step 4: Write the route smoke test**

Create `tests/playbooks_graph_db/test_routes.py`:
```python
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import playbooks_graph_db.interfaces.routes as routes_mod
from common.auth.identity import get_current_user
from playbooks_graph_db.chatbot_playbook_service import PlaybookHit, PlaybookNotFoundError


def _client(monkeypatch, fake):
    app = FastAPI()
    app.include_router(routes_mod.router)
    app.dependency_overrides[get_current_user] = lambda: object()
    monkeypatch.setattr(routes_mod, "_svc", lambda: fake)
    return TestClient(app)


def test_recall_endpoint(monkeypatch):
    class Fake:
        recall_list = AsyncMock(return_value=[
            PlaybookHit(pid="a", title="A", category="Cat", stage="All Stages",
                        content="x" * 300, score=0.9, source="vector", chunk_type="body", seq=2),
            PlaybookHit(pid="b", title="B", category="Cat", stage="All Stages",
                        content="y" * 50, score=0.0, source="graph", rel_type="DEPENDS_ON", via_pid="a"),
        ])
    c = _client(monkeypatch, Fake())
    r = c.post("/api/ai/playbook/recall", json={"inputContent": "q", "topK": 5, "useGraph": True})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] and body["code"] == 0
    assert body["data"]["vectorCount"] == 1 and body["data"]["graphCount"] == 1
    assert len(body["data"]["items"][0]["preview"]) == 200      # truncated
    assert body["data"]["items"][1]["score"] is None            # graph → null


def test_detail_not_found(monkeypatch):
    class Fake:
        def graph_detail(self, pid):
            raise PlaybookNotFoundError(pid)
    c = _client(monkeypatch, Fake())
    resp = c.get("/api/ai/playbook/detail", params={"pid": "zzz"})
    assert resp.status_code == 200
    assert resp.json()["success"] is False and resp.json()["code"] == 404
```

- [ ] **Step 5: Run the route tests**

Run: `uv run pytest tests/playbooks_graph_db/test_routes.py -v`
Expected: PASS (2 tests). If `common.auth.identity` import pulls heavy deps and fails, the root `tests/conftest.py` stubs (llm/rag/etc.) should cover it; if a new heavy import appears, mock it there.

- [ ] **Step 6: Run the whole backend test set + a live smoke**

Run: `uv run pytest tests/playbooks_graph_db/ -v`
Expected: PASS (6 tests).

Live smoke (needs lg_test + OpenRouter key + built graph): start the app or run:
```bash
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'source'); import asyncio; from playbooks_graph_db.chatbot_playbook_service import PlaybookRecallService as S; svc=S(); print([(h.pid,h.source,h.rel_type) for h in asyncio.run(svc.recall_list('cash flow forecast', 3, True))][:8])"
```
Expected: a mix of `vector` + `graph` items.

- [ ] **Step 7: Commit**

```bash
git add source/playbooks_graph_db/interfaces/routes.py source/playbooks_graph_db/chatbot_playbook_service.py source/main.py tests/playbooks_graph_db/test_routes.py
git commit -m "feat(playbook): expose /api/ai/playbook recall + detail endpoints"
```

---

## Task 6: Frontend API client

**Files:**
- Create: `web/CIOaas-web/src/services/api/playbook/playbookApi.ts`

- [ ] **Step 1: Create the typed client**

Create `src/services/api/playbook/playbookApi.ts`:
```typescript
import request from '@/utils/request';

export interface PythonEnvelope<T> {
  success: boolean;
  code: number;
  message: string;
  data: T | null;
}

export interface RecallItem {
  pid: string;
  title: string;
  category: string | null;
  stage: string | null;
  chunkType: string;
  seq: number;
  preview: string;
  source: 'vector' | 'graph';
  score: number | null;
  relType: string | null;
  viaPid: string | null;
}
export interface RecallData {
  items: RecallItem[];
  vectorCount: number;
  graphCount: number;
}
export interface GraphNode { pid: string; title: string; category: string | null }
export interface GraphEdge { source: string; target: string; relType: string }
export interface RelatedChunk { pid: string; title: string; relType: string | null; preview: string }
export interface DetailData {
  playbook: GraphNode;
  graph: { nodes: GraphNode[]; edges: GraphEdge[] };
  relatedChunks: RelatedChunk[];
}

export async function recallPlaybook(body: {
  inputContent: string;
  topK: number;
  useGraph: boolean;
}): Promise<PythonEnvelope<RecallData>> {
  return request('/api/ai/playbook/recall', { method: 'POST', data: body });
}

export async function getPlaybookDetail(pid: string): Promise<PythonEnvelope<DetailData>> {
  return request('/api/ai/playbook/detail', { method: 'GET', params: { pid } });
}
```

- [ ] **Step 2: Type-check**

Run: `cd web/CIOaas-web && npm run tsc`
Expected: no new TS errors referencing `playbookApi.ts`.

- [ ] **Step 3: Commit**

```bash
git add src/services/api/playbook/playbookApi.ts
git commit -m "feat(playbook): add frontend api client"
```

---

## Task 7: Frontend RelationGraph component (ECharts)

**Files:**
- Create: `web/CIOaas-web/src/pages/ai/playbookKnowledge/components/RelationGraph.tsx`

- [ ] **Step 1: Create the component**

Create `src/pages/ai/playbookKnowledge/components/RelationGraph.tsx`:
```typescript
import React from 'react';
import ReactECharts from 'echarts-for-react';
import type { GraphNode, GraphEdge } from '@/services/api/playbook/playbookApi';

interface Props {
  centerPid: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (pid: string) => void;
}

const RelationGraph: React.FC<Props> = ({ centerPid, nodes, edges, onNodeClick }) => {
  const option = {
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        label: { show: true, position: 'right', formatter: (p: any) => p.data.title },
        force: { repulsion: 220, edgeLength: 120 },
        edgeSymbol: ['none', 'arrow'],
        edgeLabel: { show: true, fontSize: 10, formatter: (p: any) => p.data.relType },
        data: nodes.map((n) => ({
          id: n.pid,
          name: n.pid,
          title: n.title,
          symbolSize: n.pid === centerPid ? 46 : 30,
          itemStyle: { color: n.pid === centerPid ? '#722ed1' : '#1890ff' },
        })),
        links: edges.map((e) => ({ source: e.source, target: e.target, relType: e.relType })),
      },
    ],
  };
  return (
    <ReactECharts
      option={option}
      style={{ height: 360, width: '100%' }}
      onEvents={{
        click: (p: any) => {
          if (p.dataType === 'node' && onNodeClick) onNodeClick(p.data.id);
        },
      }}
    />
  );
};

export default RelationGraph;
```

- [ ] **Step 2: Type-check**

Run: `npm run tsc`
Expected: no new TS errors. (If `echarts-for-react` lacks bundled types, the project already uses it elsewhere — follow that import style; otherwise add `// @ts-ignore` only on the import line if the existing codebase does so.)

- [ ] **Step 3: Commit**

```bash
git add src/pages/ai/playbookKnowledge/components/RelationGraph.tsx
git commit -m "feat(playbook): add ECharts relation graph component"
```

---

## Task 8: Frontend DetailDrawer component

**Files:**
- Create: `web/CIOaas-web/src/pages/ai/playbookKnowledge/components/DetailDrawer.tsx`

- [ ] **Step 1: Create the component**

Create `src/pages/ai/playbookKnowledge/components/DetailDrawer.tsx`:
```typescript
import React, { useEffect, useState } from 'react';
import { Drawer, List, Tag, Spin, Empty, message } from 'antd';
import { getPlaybookDetail, DetailData } from '@/services/api/playbook/playbookApi';
import RelationGraph from './RelationGraph';

interface Props {
  pid: string | null;
  onClose: () => void;
}

const DetailDrawer: React.FC<Props> = ({ pid, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<DetailData | null>(null);

  useEffect(() => {
    if (!pid) {
      setDetail(null);
      return;
    }
    setLoading(true);
    getPlaybookDetail(pid)
      .then((res) => {
        if (res.success && res.data) setDetail(res.data);
        else {
          message.error(res.message || 'Failed to load detail');
          setDetail(null);
        }
      })
      .catch(() => message.error('Failed to load detail'))
      .finally(() => setLoading(false));
  }, [pid]);

  return (
    <Drawer
      title={detail ? `${detail.playbook.title} (${detail.playbook.pid})` : 'Playbook Detail'}
      width={720}
      visible={!!pid}
      onClose={onClose}
      destroyOnClose
    >
      <Spin spinning={loading}>
        {detail ? (
          <>
            <h4>Relationship Graph</h4>
            {detail.graph.nodes.length > 0 ? (
              <RelationGraph
                centerPid={detail.playbook.pid}
                nodes={detail.graph.nodes}
                edges={detail.graph.edges}
              />
            ) : (
              <Empty description="No relations" />
            )}
            <h4 style={{ marginTop: 16 }}>Related chunks ({detail.relatedChunks.length})</h4>
            <List
              dataSource={detail.relatedChunks}
              locale={{ emptyText: <Empty description="No related chunks" /> }}
              renderItem={(c) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <span>
                        {c.relType && <Tag color="purple">{c.relType}</Tag>}
                        {c.title} <span style={{ color: '#999' }}>({c.pid})</span>
                      </span>
                    }
                    description={c.preview}
                  />
                </List.Item>
              )}
            />
          </>
        ) : (
          !loading && <Empty description="No data" />
        )}
      </Spin>
    </Drawer>
  );
};

export default DetailDrawer;
```

- [ ] **Step 2: Type-check**

Run: `npm run tsc`
Expected: no new TS errors.

- [ ] **Step 3: Commit**

```bash
git add src/pages/ai/playbookKnowledge/components/DetailDrawer.tsx
git commit -m "feat(playbook): add detail drawer (graph + related chunks)"
```

---

## Task 9: Frontend page (search + result list)

**Files:**
- Create: `web/CIOaas-web/src/pages/ai/playbookKnowledge/index.tsx`

- [ ] **Step 1: Create the page**

Create `src/pages/ai/playbookKnowledge/index.tsx`:
```typescript
import React, { useState } from 'react';
import { Card, Input, InputNumber, Button, Space, List, Tag, Empty, message } from 'antd';
import { recallPlaybook, RecallItem } from '@/services/api/playbook/playbookApi';
import DetailDrawer from './components/DetailDrawer';

const PlaybookKnowledge: React.FC = () => {
  const [content, setContent] = useState('');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState<'vector' | 'graph' | null>(null);
  const [items, setItems] = useState<RecallItem[] | null>(null);
  const [detailPid, setDetailPid] = useState<string | null>(null);

  const run = async (useGraph: boolean) => {
    if (!content.trim()) {
      message.warning('Please enter query content');
      return;
    }
    setLoading(useGraph ? 'graph' : 'vector');
    try {
      const res = await recallPlaybook({ inputContent: content.trim(), topK, useGraph });
      if (res.success && res.data) setItems(res.data.items);
      else message.error(res.message || 'Recall failed');
    } catch {
      message.error('Recall failed');
    } finally {
      setLoading(null);
    }
  };

  return (
    <Card title="Playbook Knowledge">
      <Space>
        <Input
          style={{ width: 420 }}
          placeholder="Enter query content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onPressEnter={() => run(false)}
        />
        <span>top_k</span>
        <InputNumber min={1} max={50} value={topK} onChange={(v) => setTopK(Number(v) || 5)} />
        <Button type="primary" loading={loading === 'vector'} onClick={() => run(false)}>
          Vector Search
        </Button>
        <Button loading={loading === 'graph'} onClick={() => run(true)}>
          V&amp;Graph Search
        </Button>
      </Space>

      <div style={{ marginTop: 16 }}>
        {items === null ? null : items.length === 0 ? (
          <Empty description="No results" />
        ) : (
          <List
            dataSource={items}
            renderItem={(it) => (
              <List.Item
                style={{ cursor: 'pointer' }}
                onClick={() => setDetailPid(it.pid)}
              >
                <List.Item.Meta
                  title={
                    <span>
                      <Tag color={it.source === 'vector' ? 'blue' : 'purple'}>{it.source}</Tag>
                      {it.title}{' '}
                      <span style={{ color: '#999' }}>
                        ({it.pid} · {it.chunkType}#{it.seq})
                      </span>
                      {it.source === 'vector' && it.score != null && (
                        <span style={{ color: '#52c41a', marginLeft: 8 }}>
                          sim {it.score.toFixed(3)}
                        </span>
                      )}
                      {it.source === 'graph' && (
                        <span style={{ color: '#999', marginLeft: 8 }}>
                          via {it.viaPid || '-'}{it.relType ? ` (${it.relType})` : ''}
                        </span>
                      )}
                    </span>
                  }
                  description={it.preview}
                />
              </List.Item>
            )}
          />
        )}
      </div>

      <DetailDrawer pid={detailPid} onClose={() => setDetailPid(null)} />
    </Card>
  );
};

export default PlaybookKnowledge;
```

- [ ] **Step 2: Type-check + lint**

Run: `npm run tsc && npm run lint:fix`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add src/pages/ai/playbookKnowledge/index.tsx
git commit -m "feat(playbook): add playbook knowledge page (search + result list)"
```

---

## Task 10: Wire route + devSupport menu

**Files:**
- Modify: `config/routes.ts` (inside `/devSupport` children, after the chatManage entry near line 735)
- Modify: `src/pages/ai/devSupport/DevSupportShell.tsx` (add a `NAV_GROUPS` entry)

- [ ] **Step 1: Add the route**

In `config/routes.ts`, after the `chatManage` child object (the one with `path: '/devSupport/chatManage'`) and before the `{ path: '/devSupport', redirect: ... }` entry, insert:
```typescript
              {
                path: '/devSupport/playbook-knowledge',
                name: 'Playbook Knowledge',
                hideInMenu: true,
                component: './ai/playbookKnowledge',
              },
```

- [ ] **Step 2: Add the nav group**

In `src/pages/ai/devSupport/DevSupportShell.tsx`, add a new entry to the `NAV_GROUPS` array (e.g., after the `chatbot` group). Reuse an already-imported icon (`NodeIndexOutlined` is imported in this file):
```typescript
  {
    key: 'playbook',
    title: 'Playbook Knowledge',
    icon: <NodeIndexOutlined />,
    items: [
      {
        key: 'playbook-knowledge',
        label: 'Knowledge',
        icon: <NodeIndexOutlined />,
        path: '/devSupport/playbook-knowledge',
        matchPrefix: '/devSupport/playbook-knowledge',
      },
    ],
  },
```

- [ ] **Step 3: Type-check + lint**

Run: `npm run tsc && npm run lint:fix`
Expected: no new errors.

- [ ] **Step 4: Manual verification**

Run: `npm run start:dev` (port 8004) with the Python app running on 8090 and the LadybugDB graph + pgvector populated (`uv run python source/playbooks_graph_db/import_playbooks.py`). Then:
- Navigate to `/devSupport` → see **Playbook Knowledge** in the left nav → open it.
- Enter "cash flow forecast", top_k 5 → **Vector Search**: list shows `vector` items with 200-char previews + sim.
- **V&Graph Search**: list additionally shows `graph` items (count may exceed top_k), tagged with `via <pid>`.
- Click a row → Drawer opens → relationship graph renders (center node purple) + related chunks list.
- Click a graph node → drawer reloads centered on that playbook.
- Empty query → warning; no-result query → Empty state.

- [ ] **Step 5: Commit**

```bash
git add config/routes.ts src/pages/ai/devSupport/DevSupportShell.tsx
git commit -m "feat(playbook): add /devSupport/playbook-knowledge route + nav entry"
```

---

## Notes / Known limitations

- The backend service caches a `read_only` LadybugDB handle per process. If `import_playbooks.py` rebuilds the graph file while the app is running, the cached handle is stale — restart the app (or the prototype service) after a re-import.
- `recall_list` graph items annotate `relType`/`viaPid` only for **direct** (1-hop) neighbors of a vector-hit playbook; deeper (2–3 hop) items have them `null` (no single connecting edge).
- Frontend has no component-test harness in this repo; frontend tasks verify via `npm run tsc` + `npm run lint:fix` + manual checks (matches existing project practice). Backend logic is covered by pytest.
