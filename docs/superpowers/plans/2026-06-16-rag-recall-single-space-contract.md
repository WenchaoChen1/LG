# RAG 召回契约改为单 space 粒度 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 RAG 召回的最小契约从「多 space 批量（`space_ids: list`）」改为「单 space（`space_id: str`）」，多 space 并发 + 跨 space 融合上移到 `factory.recalls` 编排层，store 按每个 space 各自路由。

**Architecture:** 自底向上重构调用链 —— storage（`VectorStore.search_*`）/ processor（`Processor.recall` / `_gather_candidates`）/ `factory.recall` 全部单 space；`factory.recalls` 成为编排层（embed 一次 → 并发 N 个单 space 叶子召回 → 按 RRF 分合并取全局 top_k → 记录一次）；`search_service` 按每个 granted space `get_vector_store_for_space` 组 `stores_by_space` 传入。保留「同 backend / 同 business_type / 同 embedding」一致性校验。仓储层 `search_*_single_space` 本就单 space，0 改动；`record_recall` 契约不变。

**Tech Stack:** Python 3.12、FastAPI、pytest + pytest-asyncio（`asyncio_mode=auto`）、SQLAlchemy、pgvector / Elasticsearch。

**设计依据：** [docs/superpowers/specs/2026-06-16-rag-recall-single-space-contract-design.md](../specs/2026-06-16-rag-recall-single-space-contract-design.md)

**执行约束（项目规则，强制）：**
- 本工程在 `CIOaas-python/`，测试命令在该目录下跑：`cd CIOaas-python && uv run pytest ...`（Windows PowerShell；本机依赖见 dev-stack，但本计划测试全程 mock、不连 DB/ES）。
- **Git：提交前需用户确认**（执行到 commit 步骤先征求用户同意）；**禁止自动 push**；提交消息用英文，scope=`rag`。
- 每个任务跑**本任务作用域的测试文件**（中间状态全量套件会暂时红，正常）；**全量套件绿**在最后一个任务作为门禁。

---

## File Structure

代码（全部在 `CIOaas-python/source/rag/`）：
- `infrastructure/storage/base.py` — `VectorStore` Protocol：`search_vector/keyword` 改单 `space_id`。
- `infrastructure/storage/pg_store.py` — 去掉跨空间 `gather`，单 space 查询。
- `infrastructure/storage/es_store.py` — `search_*` 单 space；`_space_filter` `terms`→`term`。
- `infrastructure/storage/__init__.py` — 顶部注释更新。
- `infrastructure/processor/base.py` — `recall` 抽象 + `_gather_candidates` 改单 `space_id` + 新增可选 `query_vector`；`record_recall` 不变。
- `infrastructure/processor/standard/standard_processor.py` — `recall` 单 space + 透传 `query_vector`。
- `infrastructure/processor/structured/structured_processor.py` — 同上。
- `infrastructure/processor/factory.py` — `recall` 单 space 叶子（不记录）；`recalls` 改编排（`stores_by_space` + embed 一次 + fan-out + 合并 + 记录一次）。
- `application/service/search_service.py` — `ResolvedScope` dataclass + `_resolve_visibility` 返回它（含 granted spaces）+ `_stores_for_granted` + `recall_by_spaces` 改组 `stores_by_space`。

文档：
- `source/rag/CLAUDE.md`、根 `CLAUDE.md`（RAG 段）、`source/rag/README.md`。

测试（`CIOaas-python/tests/rag/`）：
- `test_storage.py`、`test_financial_pipeline.py`、`test_search_service.py`、`test_recall_by_space.py`、`test_recall_service.py`（后者预期保持绿）。

---

## Task 0：建分支

- [ ] **Step 1: 从 master 建特性分支**

按 `CIOaas-python/standards/git.md` 命名规范建分支（若规范未另指定，用下名）。在 `CIOaas-python/` 仓库内执行（该目录是独立嵌套 git 仓库）：

```bash
cd CIOaas-python
git checkout -b feature/rag-recall-single-space
```

预期：切到新分支。**不提交、不 push**。

---

## Task 1：storage 层改单 space 契约

**Files:**
- Modify: `CIOaas-python/source/rag/infrastructure/storage/base.py`
- Modify: `CIOaas-python/source/rag/infrastructure/storage/pg_store.py`
- Modify: `CIOaas-python/source/rag/infrastructure/storage/es_store.py`
- Modify: `CIOaas-python/source/rag/infrastructure/storage/__init__.py`（注释）
- Test: `CIOaas-python/tests/rag/test_storage.py`

- [ ] **Step 1: 改测试到单 space 契约（red）**

在 `tests/rag/test_storage.py`，把所有 `store.search_vector(...)` / `store.search_keyword(...)` 调用的 `space_ids=[...]` 改为 `space_id="..."`，并**删除**跨空间用例 `test_pg_search_vector_cross_space_calls_each_space_once`（跨空间并发已上移，storage 不再负责）。改后受影响用例如下（其余不变）：

```python
def test_pg_search_vector_single_space_passes_space() -> None:
    store, session, repo = _pg_store_with_mocks()

    asyncio.run(
        store.search_vector(
            space_id="s1",
            query_vector=[0.0] * 1536,
            top_k=5,
            filters={},
            company_id="c1",
        )
    )

    repo.search_vector_single_space.assert_called_once()
    kwargs = repo.search_vector_single_space.call_args.kwargs
    assert kwargs["space_id"] == "s1"
    assert "company_id" not in kwargs
    assert "embedding_version" not in kwargs
    assert kwargs["file_id"] is None


def test_pg_search_vector_passes_file_id_filter() -> None:
    """单文件召回（§req-1）：filters['file_id'] 透传到单空间检索。"""
    store, session, repo = _pg_store_with_mocks()

    asyncio.run(
        store.search_vector(
            space_id="s1",
            query_vector=[0.0] * 1536,
            top_k=5,
            filters={"file_id": "f9"},
            company_id="c1",
        )
    )

    kwargs = repo.search_vector_single_space.call_args.kwargs
    assert kwargs["file_id"] == "f9"


def test_pg_search_returns_searchhits_with_score() -> None:
    store, session, repo = _pg_store_with_mocks()
    chunk = MagicMock()
    chunk.id = "ck1"
    chunk.entry_id = "e1"
    chunk.space_id = "s1"
    chunk.content = "text"
    chunk.metadata_ = {"page": 1}
    repo.search_vector_single_space.return_value = [(chunk, 0.1)]

    hits = asyncio.run(
        store.search_vector(
            space_id="s1",
            query_vector=[0.0] * 1536,
            top_k=5,
            filters={},
            company_id="c1",
        )
    )

    assert len(hits) == 1
    assert isinstance(hits[0], SearchHit)
    assert hits[0].chunk_id == "ck1"
    assert abs(hits[0].score - 0.9) < 1e-9


def test_es_search_vector_uses_knn_not_hybrid() -> None:
    store, client = _es_store_with_mock_client()
    client.indices.exists.return_value = True
    client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "ck1",
                    "_score": 0.9,
                    "_source": {
                        "chunk_id": "ck1",
                        "entry_id": "e1",
                        "space_id": "s1",
                        "content": "text",
                        "metadata": {},
                    },
                }
            ]
        }
    }

    hits = asyncio.run(
        store.search_vector(
            space_id="s1",
            query_vector=[0.0] * 1536,
            top_k=5,
            filters={},
            company_id="c1",
        )
    )

    assert len(hits) == 1
    assert isinstance(hits[0], SearchHit)
    call_kwargs = client.search.call_args.kwargs
    serialized = str(call_kwargs)
    assert "knn" in serialized
    assert "hybrid" not in serialized.lower()
    # 单 space 用 term（非 terms）过滤
    assert "'term'" in serialized


def test_es_search_keyword_uses_match_not_hybrid() -> None:
    store, client = _es_store_with_mock_client()
    client.indices.exists.return_value = True
    client.search.return_value = {"hits": {"hits": []}}

    asyncio.run(
        store.search_keyword(
            space_id="s1",
            query_text="revenue",
            top_k=5,
            filters={},
            company_id="c1",
        )
    )

    call_kwargs = client.search.call_args.kwargs
    serialized = str(call_kwargs)
    assert "match" in serialized
    assert "knn" not in serialized
    assert "hybrid" not in serialized.lower()


def test_es_search_skips_missing_index_gracefully() -> None:
    store, client = _es_store_with_mock_client()
    client.indices.exists.return_value = False

    hits = asyncio.run(
        store.search_vector(
            space_id="s1",
            query_vector=[0.0] * 1536,
            top_k=5,
            filters={},
            company_id="c1",
        )
    )
    assert hits == []
    client.search.assert_not_called()
```

同时把模块 docstring 里「跨空间用 asyncio.gather 并发单空间查询（决策 C2）」改为「单空间查询（多空间并发已上移 factory.recalls）」。

- [ ] **Step 2: 跑测试确认 red**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_storage.py -q
```
预期：FAIL（现有 `search_*` 仍要求 `space_ids` 关键字 → `TypeError: unexpected keyword argument 'space_id'`）。

- [ ] **Step 3: 改 `base.py`（Protocol 单 space）**

`source/rag/infrastructure/storage/base.py`：`search_vector` / `search_keyword` 的 `space_ids: list[str]` 改 `space_id: str`，并更新 docstring（删 C2 跨空间并发描述）：

```python
    async def search_vector(
        self,
        *,
        space_id: str,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, Any],
        company_id: str,
    ) -> list[SearchHit]:
        """向量召回（pgvector HNSW / ES knn），**单空间**。多空间并发由 factory.recalls 编排。"""
        ...

    async def search_keyword(
        self,
        *,
        space_id: str,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
        company_id: str,
    ) -> list[SearchHit]:
        """关键词召回（PG ILIKE/trigram / ES BM25 match），**单空间**。不开 ES hybrid（决策 C1）。"""
        ...
```

并把类/模块 docstring 中「跨空间并发在实现内（决策 C2）」「search_* 接受 space_ids 列表」相关句改为「search_* 单空间；多空间并发在 factory.recalls 编排层」。

- [ ] **Step 4: 改 `pg_store.py`（去 gather）**

`source/rag/infrastructure/storage/pg_store.py` 的 `search_vector` / `search_keyword` 改为单 space（删除 `asyncio.gather(... for space_id in space_ids)`）：

```python
    async def search_vector(
        self,
        *,
        space_id: str,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, Any],
        company_id: str,
    ) -> list[SearchHit]:
        """单空间向量召回（命中 HNSW），按相似度降序取 top_k。

        ``filters['file_id']`` 非空时叠加单文件过滤（§req-1）；company_id 不参与 PG 过滤
        （隔离由调用方圈定的 space 范围保证），仅 Protocol 统一签名保留。多空间并发由
        factory.recalls 编排（对每个 space 各调一次本方法）。
        """
        limit = top_k * _OVER_FETCH_MULTIPLIER
        file_id = filters.get("file_id") if filters else None
        hits = await asyncio.to_thread(
            self._do_vector_single_space, space_id, query_vector, limit, file_id,
        )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    async def search_keyword(
        self,
        *,
        space_id: str,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
        company_id: str,
    ) -> list[SearchHit]:
        """单空间关键词召回（ILIKE/trigram），取 top_k。``filters['file_id']`` 非空叠加单文件过滤。"""
        limit = top_k * _OVER_FETCH_MULTIPLIER
        file_id = filters.get("file_id") if filters else None
        hits = await asyncio.to_thread(
            self._do_keyword_single_space, space_id, query_text, limit, file_id,
        )
        return hits[:top_k]
```

（`_do_vector_single_space` / `_do_keyword_single_space` / `asyncio` import 不变；模块 docstring 的「决策 C2 跨空间并发」句改为「单空间查询，多空间并发上移 factory.recalls」。）

- [ ] **Step 5: 改 `es_store.py`（单 space + `_space_filter`）**

`source/rag/infrastructure/storage/es_store.py`：`search_vector` / `search_keyword` 的 `space_ids: list[str]` 改 `space_id: str`，`_space_filter(space_ids, ...)` 调用改 `_space_filter(space_id, ...)`；并改 `_space_filter`：

```python
    async def search_vector(
        self,
        *,
        space_id: str,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, Any],
        company_id: str,
    ) -> list[SearchHit]:
        """knn 向量召回（决策 C1：不开 hybrid），**单空间**。多空间并发由 factory.recalls 编排。"""
        limit = top_k * _OVER_FETCH_MULTIPLIER
        index = self._index_name(company_id=company_id)
        try:
            if not await self.client.indices.exists(index=index):
                return []
            knn = {
                "field": "embedding",
                "query_vector": query_vector,
                "k": limit,
                "num_candidates": max(limit * 2, 50),
                "filter": self._space_filter(space_id, filters),
            }
            response = await self.client.search(index=index, knn=knn, size=limit)
            hits = self._parse_hits(response)
            hits.sort(key=lambda h: h.score, reverse=True)
            return hits[:top_k]
        except Exception as exc:  # noqa: BLE001
            logger.error("ES knn 检索失败: %s", exc, exc_info=True)
            raise StorageError(f"es search_vector failed: {exc}") from exc

    async def search_keyword(
        self,
        *,
        space_id: str,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
        company_id: str,
    ) -> list[SearchHit]:
        """BM25 关键词召回（决策 C1：独立 match 查询），**单空间**。"""
        limit = top_k * _OVER_FETCH_MULTIPLIER
        index = self._index_name(company_id=company_id)
        try:
            if not await self.client.indices.exists(index=index):
                return []
            query = {
                "bool": {
                    "must": [{"match": {"content": query_text}}],
                    "filter": self._space_filter(space_id, filters),
                }
            }
            response = await self.client.search(index=index, query=query, size=limit)
            hits = self._parse_hits(response)
            return hits[:top_k]
        except Exception as exc:  # noqa: BLE001
            logger.error("ES BM25 检索失败: %s", exc, exc_info=True)
            raise StorageError(f"es search_keyword failed: {exc}") from exc
```

`_space_filter` 改单 space（`terms`→`term`）：

```python
    @staticmethod
    def _space_filter(
        space_id: str, filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """构造 term 过滤：space_id（单空间召回范围）+ 附加业务 filters；**不带 company_id**。

        隔离由索引分区（公司粒度，无版本）+ space 范围保证，故文档无 company_id 字段、过滤
        也不需要它。``filters['file_id']`` 非空时叠加单文件过滤（§req-1）；``entry_ids`` 兼容保留。
        """
        clauses: list[dict[str, Any]] = [
            {"term": {"space_id": space_id}},
        ]
        file_id = filters.get("file_id") if filters else None
        if file_id:
            clauses.append({"term": {"file_id": file_id}})
        entry_ids = filters.get("entry_ids") if filters else None
        if entry_ids:
            clauses.append({"terms": {"entry_id": entry_ids}})
        return clauses
```

- [ ] **Step 6: 改 `storage/__init__.py` 注释**

`source/rag/infrastructure/storage/__init__.py` 顶部说明里若提及「search_* 接受多 space_ids / 跨空间并发」，改为「search_* 单空间；多空间并发在 factory.recalls 编排」。

- [ ] **Step 7: 跑测试确认 green**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_storage.py -q
```
预期：PASS。

- [ ] **Step 8: 提交（需用户确认）**

```bash
git add source/rag/infrastructure/storage/ tests/rag/test_storage.py
git commit -m "refactor(rag): storage search_* single-space contract (drop cross-space gather)"
```

---

## Task 2：processor 层单 space + 可选 query_vector

**Files:**
- Modify: `CIOaas-python/source/rag/infrastructure/processor/base.py`
- Modify: `CIOaas-python/source/rag/infrastructure/processor/standard/standard_processor.py`
- Modify: `CIOaas-python/source/rag/infrastructure/processor/structured/structured_processor.py`
- Test: `CIOaas-python/tests/rag/test_search_service.py`（`test_recall_truncates_to_top_k`）、`CIOaas-python/tests/rag/test_financial_pipeline.py`（`test_recall_gathers_candidates_with_weighted_fusion`）

- [ ] **Step 1: 改测试到单 space（red）**

`tests/rag/test_search_service.py` 的 `test_recall_truncates_to_top_k`：`space_ids=["s1"]` → `space_id="s1"`：

```python
async def test_recall_truncates_to_top_k() -> None:
    """recall 三步解耦后仍截断到 top_k（截断从 _rrf_fuse 移到 recall）。"""
    from rag.infrastructure.processor.standard.standard_processor import (
        StandardProcessor,
    )

    proc = StandardProcessor(embedder=MagicMock(), ocr_provider=MagicMock())
    vec = [_hit(str(i), score=1.0 - i * 0.05) for i in range(10)]

    async def _fake_gather(**_kwargs):
        return vec, []

    proc._gather_candidates = _fake_gather  # type: ignore[method-assign]
    hits = await proc.recall(
        store=object(), query="q", top_k=3, company_id="c1", space_id="s1",
    )
    assert len(hits) == 3
    assert [h.chunk_id for h in hits] == ["0", "1", "2"]
```

`tests/rag/test_financial_pipeline.py` 的 `test_recall_gathers_candidates_with_weighted_fusion`：`space_ids=["s1"]` → `space_id="s1"`：

```python
    def test_recall_gathers_candidates_with_weighted_fusion(self) -> None:
        """财报 recall：按单 space 调 store 向量+关键词检索后做（向量加权）融合（无版本概念）。"""
        store = MagicMock()
        store.search_vector = AsyncMock(return_value=[])
        store.search_keyword = AsyncMock(return_value=[])
        embedder = MagicMock()
        embedder.embed_query = AsyncMock(return_value=[0.1] * 1536)

        p = StructuredProcessor(embedder=embedder, ocr_provider=MagicMock())
        hits = asyncio.run(
            p.recall(
                store=store, query="q", top_k=5, company_id="c1",
                space_id="s1",
            )
        )

        assert hits == []
        store.search_vector.assert_awaited_once()
        store.search_keyword.assert_awaited_once()
```

- [ ] **Step 2: 跑测试确认 red**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_search_service.py::test_recall_truncates_to_top_k "tests/rag/test_financial_pipeline.py::TestStructuredProcessor::test_recall_gathers_candidates_with_weighted_fusion" -q
```
（注：财报用例类名以实际文件为准，可直接 `uv run pytest tests/rag/test_financial_pipeline.py -q`。）
预期：FAIL（`recall()` 仍要求 `space_ids`）。

- [ ] **Step 3: 改 `base.py`（`recall` 抽象 + `_gather_candidates` + `query_vector`）**

`source/rag/infrastructure/processor/base.py`：

`recall` 抽象签名：`space_ids: list[str]` → `space_id: str`，新增 `query_vector`：

```python
    @abstractmethod
    async def recall(
        self,
        *,
        store: "VectorStore",
        query: str,
        top_k: int,
        company_id: str,
        space_id: str,
        query_vector: list[float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """召回（**抽象**，单 space）：各处理类型实现一套召回逻辑（§req-4/req-7）。

        基类提供共用原语：``_gather_candidates``（embed query 或复用传入 query_vector + 并发
        向量/关键词检索）+ ``_rrf_fuse``（RRF 融合算分，不排序不截断）+ ``sort_by_score``。
        **内部不查 space**：单个 ``space_id`` 由调用方圈定后传入；多空间并发 + 跨空间融合由
        ``factory.recalls`` 编排（对每个 space 各调一次本方法）。``query_vector`` 由编排层预算
        （所有 space 同 embedding）后传入以避免重复 embed；不传则内部 embed 一次。
        """
        ...
```

`_gather_candidates`：单 space + 可选 `query_vector`：

```python
    async def _gather_candidates(
        self,
        *,
        store: "VectorStore",
        query: str,
        top_k: int,
        company_id: str,
        space_id: str,
        query_vector: list[float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[SearchHit], list[SearchHit]]:
        """召回候选收集（两类型共用，单 space）：并发向量+关键词检索，合并两路候选。

        ``query_vector`` 传入则复用（编排层预算、避免多 space 重复 embed），否则内部 embed 一次。
        """
        if query_vector is None:
            query_vector = await self._embedder.embed_query(query)
        vec_hits, kw_hits = await asyncio.gather(
            store.search_vector(
                space_id=space_id, query_vector=query_vector,
                top_k=top_k, filters=filters or {}, company_id=company_id,
            ),
            store.search_keyword(
                space_id=space_id, query_text=query,
                top_k=top_k, filters=filters or {}, company_id=company_id,
            ),
        )
        return vec_hits, kw_hits
```

（`record_recall` / `sort_by_score` / `_rrf_fuse` 不变。）

- [ ] **Step 4: 改 `standard_processor.py`**

`source/rag/infrastructure/processor/standard/standard_processor.py` 的 `recall`：

```python
    async def recall(
        self,
        *,
        store: "VectorStore",
        query: str,
        top_k: int,
        company_id: str,
        space_id: str,
        query_vector: list[float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """STANDARD 基础向量召回（单 space）：向量+关键词并发检索 → 等权 RRF 融合取 top_k。"""
        rrf_k = get_rag_search_settings().rrf_k
        all_vec, all_kw = await self._gather_candidates(
            store=store, query=query, top_k=top_k, company_id=company_id,
            space_id=space_id, query_vector=query_vector, filters=filters,
        )
        fused = self._rrf_fuse(all_vec, all_kw, k=rrf_k)
        return self.sort_by_score(fused)[:top_k]
```

- [ ] **Step 5: 改 `structured_processor.py`**

`source/rag/infrastructure/processor/structured/structured_processor.py` 的 `recall`：

```python
    async def recall(
        self,
        *,
        store: "VectorStore",
        query: str,
        top_k: int,
        company_id: str,
        space_id: str,
        query_vector: list[float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """STRUCTURED 财报召回（单 space）：复用候选收集，融合时向量路加权（语义 > 词面）。"""
        rrf_k = get_rag_search_settings().rrf_k
        all_vec, all_kw = await self._gather_candidates(
            store=store, query=query, top_k=top_k, company_id=company_id,
            space_id=space_id, query_vector=query_vector, filters=filters,
        )
        fused = self._rrf_fuse(
            all_vec, all_kw, k=rrf_k,
            vector_weight=_STRUCTURED_VECTOR_WEIGHT,
            keyword_weight=_STRUCTURED_KEYWORD_WEIGHT,
        )
        return self.sort_by_score(fused)[:top_k]
```

- [ ] **Step 6: 跑测试确认 green**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_search_service.py::test_recall_truncates_to_top_k tests/rag/test_financial_pipeline.py -q
```
预期：PASS。

- [ ] **Step 7: 提交（需用户确认）**

```bash
git add source/rag/infrastructure/processor/base.py source/rag/infrastructure/processor/standard/ source/rag/infrastructure/processor/structured/ tests/rag/test_search_service.py tests/rag/test_financial_pipeline.py
git commit -m "refactor(rag): Processor.recall/_gather_candidates single-space + optional query_vector"
```

---

## Task 3：factory 层（recall 叶子 + recalls 编排）

**Files:**
- Modify: `CIOaas-python/source/rag/infrastructure/processor/factory.py`
- Test: `CIOaas-python/tests/rag/test_recall_by_space.py`

- [ ] **Step 1: 重写 `test_recall_by_space.py`（red）**

整文件替换为下述内容（`recalls` 改收 `stores_by_space`、fan-out 单 space、embed 一次、合并、记录一次；`recall` 叶子不记录；base `record_recall` 回调 service 不变）：

```python
"""factory.recalls（多 space 编排）/ recall（单 space 叶子）+ base.record_recall 单测。

不连 DB：patch ``build_processor`` 返回 mock 处理器。验证：
  - recalls：build → embed 一次 → 每个 space 各调一次 processor.recall(单 space + query_vector)
    → 按 RRF 分合并取 top_k → processor.record_recall 记录一次（granted=所有 space, hits=合并）。
  - recall：单 space 叶子，build → processor.recall(space_id)，**不记录**。
  - base record_recall：同步回调 service save_recall_record（传 self.chunk_cls）。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from rag.infrastructure.processor import factory
from rag.infrastructure.processor.base import SearchHit

_MOD = "rag.infrastructure.processor.factory"


def _hit(chunk_id: str, *, space_id: str = "s1", score: float = 1.0) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id, entry_id="e1", space_id=space_id,
        content=f"content-{chunk_id}", score=score, metadata={},
    )


def _mock_processor() -> MagicMock:
    """mock 处理器：recall 按 space_id 返回单条命中；embedder.embed_query 受控；record_recall 受控。"""
    proc = MagicMock()

    async def _recall(*, space_id, score=1.0, **_kw):
        return [_hit(space_id, space_id=space_id, score=score)]

    # 每个 space 返回一条 score 递减的命中，便于断言合并顺序
    async def _recall_by_space(*, space_id, **_kw):
        score = {"s1": 0.9, "s2": 0.8}.get(space_id, 0.5)
        return [_hit(space_id, space_id=space_id, score=score)]

    proc.recall = AsyncMock(side_effect=_recall_by_space)
    proc.record_recall = MagicMock()
    proc.embedder = MagicMock()
    proc.embedder.embed_query = AsyncMock(return_value=[0.1] * 8)
    return proc


async def _invoke_recalls(proc: MagicMock, **overrides):
    kwargs = dict(
        process_type="STANDARD", embedding_provider="openai", embedding_model="m1",
        stores_by_space={"s1": "STORE1", "s2": "STORE2"},
        query="q", top_k=5, company_id="c1", user_id="u1",
        caller_type="USER", filters={"file_id": "f1"},
    )
    kwargs.update(overrides)
    with patch(f"{_MOD}.build_processor", return_value=proc) as build:
        result = await factory.recalls(**kwargs)
    return result, build


async def test_build_processor_called_with_process_type():
    """① 按 process_type + embedding 配置构造处理器。"""
    proc = _mock_processor()
    _result, build = await _invoke_recalls(proc)
    build.assert_called_once_with(
        "STANDARD", embedding_provider="openai", embedding_model="m1",
    )


async def test_query_embedded_once():
    """② query 只 embed 一次（编排层预算，传给每个单 space 召回）。"""
    proc = _mock_processor()
    await _invoke_recalls(proc)
    proc.embedder.embed_query.assert_awaited_once_with("q")


async def test_recall_called_per_space_single_space_with_vector():
    """③ 每个 space 各调一次 processor.recall：单 space_id + 对应 store + 透传 query_vector/filters。"""
    proc = _mock_processor()
    await _invoke_recalls(proc)

    assert proc.recall.await_count == 2
    by_space = {c.kwargs["space_id"]: c.kwargs for c in proc.recall.await_args_list}
    assert set(by_space) == {"s1", "s2"}
    assert by_space["s1"]["store"] == "STORE1"
    assert by_space["s2"]["store"] == "STORE2"
    # 预算好的向量透传，避免重复 embed
    assert by_space["s1"]["query_vector"] == [0.1] * 8
    assert by_space["s1"]["filters"] == {"file_id": "f1"}
    # 单 space 契约：不再传 space_ids 列表
    assert "space_ids" not in by_space["s1"]


async def test_merges_and_truncates_top_k():
    """④ 跨 space 命中按分数合并取全局 top_k。"""
    proc = _mock_processor()
    result, _build = await _invoke_recalls(proc, top_k=1)
    # s1(0.9) > s2(0.8)，top_k=1 → 仅留 s1 的命中
    assert len(result) == 1
    assert result[0].chunk_id == "s1"


async def test_record_recall_called_once_with_all_spaces_and_merged_hits():
    """⑤ 记录一次：granted_space_ids=所有 space，hits=合并结果，同步（无 background）。"""
    proc = _mock_processor()
    result, _build = await _invoke_recalls(proc)

    proc.record_recall.assert_called_once()
    kwargs = proc.record_recall.call_args.kwargs
    assert kwargs["granted_space_ids"] == ["s1", "s2"]
    assert kwargs["hits"] == result
    assert kwargs["user_id"] == "u1"
    assert kwargs["caller_type"] == "USER"
    assert isinstance(kwargs["duration_ms"], int) and kwargs["duration_ms"] >= 0
    assert "background" not in kwargs


async def test_single_space_leaf_does_not_record():
    """⑥ factory.recall（单 space 叶子）：build → processor.recall(space_id)，不记录。"""
    proc = _mock_processor()
    with patch(f"{_MOD}.build_processor", return_value=proc):
        hits = await factory.recall(
            process_type="STANDARD", embedding_provider="openai",
            embedding_model="m1", store="STORE", query="q", top_k=5,
            company_id="c1", space_id="s1",
        )

    proc.recall.assert_awaited_once()
    assert proc.recall.await_args.kwargs["space_id"] == "s1"
    assert proc.recall.await_args.kwargs["store"] == "STORE"
    proc.record_recall.assert_not_called()
    assert [h.chunk_id for h in hits] == ["s1"]


def test_record_recall_calls_service_save():
    """base ``record_recall`` 触发记录 → 同步回调 service ``save_recall_record``（传 self.chunk_cls）。"""
    from rag.infrastructure.processor.standard.standard_processor import (
        StandardProcessor,
    )
    from rag.infrastructure.processor.standard.models import EnterpriseKbChunk

    proc = StandardProcessor(embedder=MagicMock(), ocr_provider=MagicMock())
    with patch(
        "rag.application.service.search_service.save_recall_record"
    ) as save:
        proc.record_recall(
            user_id="u1", granted_space_ids=["s1"], query="q", top_k=5,
            caller_type="USER", hits=[_hit("a")], duration_ms=3,
        )

    save.assert_called_once()
    kwargs = save.call_args.kwargs
    assert kwargs["chunk_cls"] is EnterpriseKbChunk
    assert kwargs["space_ids"] == ["s1"]
    assert kwargs["hits"] == [_hit("a")]
```

- [ ] **Step 2: 跑测试确认 red**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_recall_by_space.py -q
```
预期：FAIL（现 `recalls` 仍要求 `store`+`space_ids`，无 `stores_by_space`）。

- [ ] **Step 3: 改 `factory.py`（`recall` 叶子 + `recalls` 编排）**

`source/rag/infrastructure/processor/factory.py`：

顶部确保有 `import asyncio` 与 `from rag.infrastructure.processor.base import Processor, SearchHit`（`Processor` 已用于类型，`time` 已 import）。`recall` / `recalls` 替换为：

```python
async def recall(
    *,
    process_type: str,
    embedding_provider: str | None,
    embedding_model: str | None,
    store: "VectorStore",
    query: str,
    top_k: int,
    company_id: str,
    space_id: str,
    query_vector: list[float] | None = None,
    filters: dict[str, Any] | None = None,
) -> list[SearchHit]:
    """单 space 召回叶子（**纯召回、不记录**）：build_processor → processor.recall。

    这是本契约的最小单元 ``(store/连接, business_type→process_type, space_id) → 该空间数据``。
    需要召回**并记录**时走 ``recalls`` 传单元素 ``stores_by_space``（编排层负责记录）。
    ``query_vector`` 传入则复用（编排层预算），否则处理器内部 embed 一次。
    """
    processor = build_processor(
        process_type,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )
    return await processor.recall(
        store=store, query=query, query_vector=query_vector, top_k=top_k,
        company_id=company_id, space_id=space_id, filters=filters,
    )


async def recalls(
    *,
    process_type: str,
    embedding_provider: str | None,
    embedding_model: str | None,
    stores_by_space: dict[str, "VectorStore"],
    query: str,
    top_k: int,
    company_id: str,
    user_id: str,
    caller_type: str,
    filters: dict[str, Any] | None = None,
) -> list[SearchHit]:
    """多 space 召回编排（**召回 + 记录一次**）：fan-out 单 space 叶子 → 合并 → 记录。

    步骤：``build_processor``（零分支）→ ``embedder.embed_query`` **算一次**（所有 space 同
    embedding，已由 service 校验）→ 对每个 ``space_id`` 用其各自的 ``store``（一 space 一连接的
    路由接缝）并发调 ``processor.recall``（单 space）→ 各 space 已融合命中按 RRF 分
    （``sort_by_score``）合并取全局 ``top_k`` → ``processor.record_recall`` 记录一次
    （**base Processor 触发、回调 service ``save_recall_record``**，granted=所有 space、hits=合并）。
    不查 space / 不做 ACL / 不 enrich（在 service）；单文件经 ``filters['file_id']``。
    """
    processor = build_processor(
        process_type,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )
    space_ids = list(stores_by_space.keys())
    started = time.monotonic()
    # query 只 embed 一次（所有 space 同 embedding），传给每个单 space 召回避免重复 embed。
    query_vector = await processor.embedder.embed_query(query)
    per_space = await asyncio.gather(
        *(
            processor.recall(
                store=stores_by_space[sid], query=query, query_vector=query_vector,
                top_k=top_k, company_id=company_id, space_id=sid, filters=filters,
            )
            for sid in space_ids
        )
    )
    merged = Processor.sort_by_score(
        [hit for space_hits in per_space for hit in space_hits]
    )[:top_k]
    duration_ms = int((time.monotonic() - started) * 1000)
    # base Processor 契约触发记录：record_recall 同步回调 service save_recall_record 持久化。
    processor.record_recall(
        user_id=user_id, granted_space_ids=space_ids, query=query, top_k=top_k,
        caller_type=caller_type, hits=merged, duration_ms=duration_ms,
    )
    return merged
```

并把 `__all__` 保持含 `"recalls"`, `"recall"`；模块 docstring 把「recalls（多 space）→ recall（单 space，委托前者）」改为「recalls 多 space 编排（fan-out 单 space 叶子 + 合并 + 记录一次）/ recall 单 space 叶子（纯召回不记录）」。确认文件顶部已 `import asyncio`（若无则添加）。

- [ ] **Step 4: 跑测试确认 green**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_recall_by_space.py -q
```
预期：PASS。

- [ ] **Step 5: 提交（需用户确认）**

```bash
git add source/rag/infrastructure/processor/factory.py tests/rag/test_recall_by_space.py
git commit -m "refactor(rag): factory.recalls orchestrates per-space leaf recalls (stores_by_space, embed once, merge, record once)"
```

---

## Task 4：service 层（ResolvedScope + per-space store 路由）

**Files:**
- Modify: `CIOaas-python/source/rag/application/service/search_service.py`
- Test: `CIOaas-python/tests/rag/test_search_service.py`（`test_search_empty_granted_raises_401`、`test_search_delegates_to_recalls`）

- [ ] **Step 1: 改测试到新契约（red）**

`tests/rag/test_search_service.py` 顶部 import 增加 `ResolvedScope`：

```python
from rag.application.service.search_service import SearchService, ResolvedScope
```

`test_search_empty_granted_raises_401` 改为返回 `ResolvedScope`：

```python
def test_search_empty_granted_raises_401() -> None:
    from rag.application.dto import SearchDTO

    svc = _svc()
    dto = SearchDTO(query="q", space_ids=["s1"], top_k=5)

    with patch.object(
        svc, "_resolve_visibility",
        return_value=ResolvedScope(
            granted=[], dropped=["s1"], granted_spaces=[],
            business_type=None, process_type=None,
            embedding_provider=None, embedding_model=None,
        ),
    ):
        with pytest.raises(errors.RagBusinessError) as exc:
            asyncio.run(svc.search(dto, company_id="c1", user_id="u1"))
    assert exc.value.http_status == 401
    assert exc.value.code == 40101
```

`test_search_delegates_to_recalls` 改为新签名（`_resolve_visibility`→ResolvedScope；`_stores_for_granted` 替代 `_store_for_granted`；`recalls` 收 `stores_by_space`）：

```python
def test_search_delegates_to_recalls() -> None:
    """search（经 recall_by_spaces）一次调用 infra ``factory.recalls``，透传 process_type /
    stores_by_space / query / top_k / company_id / user_id / caller_type；记录由 recalls 内部触发。"""
    from rag.application.dto import SearchDTO

    _MOD = "rag.application.service.search_service"
    svc = _svc()
    dto = SearchDTO(query="q", space_ids=["s1"], top_k=5)
    recalls_mock = AsyncMock(return_value=[_hit("a")])
    stores = {"s1": object()}

    with (
        patch.object(
            svc, "_resolve_visibility",
            return_value=ResolvedScope(
                granted=["s1"], dropped=[], granted_spaces=[object()],
                business_type="enterprise_kb", process_type="STANDARD",
                embedding_provider="openai", embedding_model="m1",
            ),
        ),
        patch.object(svc, "_stores_for_granted", return_value=stores),
        patch(f"{_MOD}.recalls", recalls_mock),
        patch(f"{_MOD}.rag_op_scope"),
        patch.object(svc, "_enrich", return_value=[]) as enrich,
    ):
        result = asyncio.run(svc.search(dto, company_id="c1", user_id="u1"))

    recalls_mock.assert_awaited_once()
    kwargs = recalls_mock.await_args.kwargs
    assert kwargs["process_type"] == "STANDARD"
    assert kwargs["query"] == "q"
    assert kwargs["top_k"] == 5
    assert kwargs["company_id"] == "c1"
    assert kwargs["user_id"] == "u1"
    assert kwargs["stores_by_space"] is stores
    assert kwargs["caller_type"] == "USER"
    # 不再传单一 store / space_ids 列表
    assert "store" not in kwargs
    assert "space_ids" not in kwargs
    assert "background" not in kwargs
    assert enrich.call_args.args[0] == [_hit("a")]
    assert isinstance(result.duration_ms, int) and result.duration_ms >= 0
```

- [ ] **Step 2: 跑测试确认 red**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_search_service.py -q
```
预期：FAIL（无 `ResolvedScope` 导出 / `_stores_for_granted` 不存在 / `recalls` 仍收 `store`+`space_ids`）。

- [ ] **Step 3: 改 `search_service.py`（ResolvedScope + 路由 + 调用）**

`source/rag/application/service/search_service.py`：

顶部 import 加 `from dataclasses import dataclass`；`get_vector_store_for_space` 已 import（保留），`get_vector_store` 保留（构造默认 self._store）。在 `RagSpace` import 后、`SearchService` 类前加 dataclass：

```python
from dataclasses import dataclass


@dataclass
class ResolvedScope:
    """``_resolve_visibility`` 结果：granted 空间（id + 对象）+ 本次共享的处理配置。

    ``granted_spaces`` 携带 granted 的 RagSpace 对象，供 ``_stores_for_granted`` 按 space 路由
    store 时复用、不二次查库。business_type / process_type / embedding_* 为所有 granted space
    共享值（已校验单一）；granted 空时为 None。
    """

    granted: list[str]
    dropped: list[str]
    granted_spaces: list[RagSpace]
    business_type: Optional[str]
    process_type: Optional[str]
    embedding_provider: Optional[str]
    embedding_model: Optional[str]
```

`_resolve_visibility` 改为返回 `ResolvedScope` 并收集 granted spaces（签名 + 收集 + 返回三处改）：

```python
    def _resolve_visibility(
        self, *, space_ids: list[str], company_id: str
    ) -> ResolvedScope:
        """裁剪可见空间，校验跨后端 / 跨业务类型 / 跨 embedding 模型一致，返回 ResolvedScope。

        （一致性校验逻辑不变；额外把 granted 的 RagSpace 对象收进 granted_spaces 供 store 路由复用。）
        """
        granted: list[str] = []
        dropped: list[str] = []
        granted_spaces: list[RagSpace] = []
        backends: set[str] = set()
        business_types: set[str] = set()
        process_types: set[str] = set()
        embedding_specs: set[tuple[str, str]] = set()

        with get_session() as session:
            repo = SpaceRepository(session)
            for sid in space_ids:
                space = repo.get_by_id(space_id=sid, company_id=company_id)
                if not self._is_visible(space):
                    dropped.append(sid)
                    continue
                granted.append(sid)
                granted_spaces.append(space)
                backends.add(getattr(space, "storage_backend", None) or "pg")
                business_types.add(space.business_type)
                ptype = getattr(space, "process_type", None) or "STANDARD"
                process_types.add(ptype)
                seed = get_seed(ptype)
                embedding_specs.add((seed.embedding_provider, seed.embedding_model))

        if len(backends) > 1:
            raise errors.invalid_param(
                f"v1 不支持跨后端检索：本次涉及 backend={sorted(backends)!r}，"
                "请仅选择同一存储后端（pg 或 es）的空间"
            )
        if len(business_types) > 1:
            raise errors.invalid_param(
                "单次检索不支持跨业务类型空间："
                f"本次涉及 business_type={sorted(business_types)!r}，"
                "请仅选择同一业务类型的空间"
            )
        if len(embedding_specs) > 1:
            raise errors.invalid_param(
                "单次检索不支持跨 embedding 模型的空间："
                f"本次涉及 {sorted(embedding_specs)!r}，请仅选择 embedding 配置一致的空间"
            )

        business_type = next(iter(business_types)) if business_types else None
        process_type = next(iter(process_types)) if process_types else None
        embedding_provider, embedding_model = (
            next(iter(embedding_specs)) if embedding_specs else (None, None)
        )
        return ResolvedScope(
            granted=granted, dropped=dropped, granted_spaces=granted_spaces,
            business_type=business_type, process_type=process_type,
            embedding_provider=embedding_provider, embedding_model=embedding_model,
        )
```

把 `_store_for_granted` 方法**替换**为 `_stores_for_granted`：

```python
    def _stores_for_granted(
        self, granted_spaces: list[RagSpace], *, company_id: str
    ) -> dict:
        """按每个 granted space **各自**路由检索 store，组 {space_id: VectorStore}。

        这是「未来一 space 一库」的路由接缝：每个 space 经 factory 按自身 storage 配置解析
        （同 business_type + 同 backend 已校验）。空列表 → 空 dict（上层已保证 granted 非空）。
        """
        return {
            s.id: get_vector_store_for_space(s, company_id) for s in granted_spaces
        }
```

`recall_by_spaces` 改用 ResolvedScope + stores_by_space：

```python
    async def recall_by_spaces(
        self, *, space_ids: list[str], query: str, top_k: int,
        company_id: str, user_id: str, caller_type: str = "USER",
        filters: Optional[dict] = None,
    ) -> SearchResultDTO:
        """高层召回入口：**只穿 space id(s)**，查配置 + 按 space 路由 store 后调 ``factory.recalls``。"""
        started = time.monotonic()

        scope = self._resolve_visibility(space_ids=space_ids, company_id=company_id)
        if not scope.granted or scope.business_type is None:
            raise errors.RagBusinessError(
                http_status=401, code=40101,
                message="无可见空间，拒绝检索",
            )

        # 按每个 granted space 各自路由 store（一 space 一连接的接缝）。
        stores_by_space = self._stores_for_granted(
            scope.granted_spaces, company_id=company_id
        )
        search_trace_id = str(uuid.uuid4())
        try:
            with rag_op_scope(
                name="rag_query",
                source=TraceSource.HTTP.value,
                trace_id=search_trace_id,
                company_id=company_id,
                user_id=user_id,
                node="query",
                call_purpose="rag_query",
                attributes={"topK": top_k, "spaceCount": len(scope.granted)},
                span_attributes={"topK": top_k},
            ):
                fused = await recalls(
                    process_type=scope.process_type,
                    embedding_provider=scope.embedding_provider,
                    embedding_model=scope.embedding_model,
                    stores_by_space=stores_by_space,
                    query=query, top_k=top_k,
                    company_id=company_id, user_id=user_id,
                    caller_type=caller_type, filters=filters or {},
                )
        except StorageError as exc:
            logger.error("检索存储层失败: %s", exc, exc_info=True)
            raise errors.service_unavailable("检索服务暂不可用") from exc

        hits = self._enrich(fused, top_k=top_k, company_id=company_id)
        duration_ms = int((time.monotonic() - started) * 1000)
        return SearchResultDTO(
            hits=hits,
            granted_space_ids=scope.granted,
            dropped_space_ids=scope.dropped,
            duration_ms=duration_ms,
        )
```

更新该方法及类 docstring 中「`_store_for_granted` 取 granted[0] 单 store」「storage 内部对多空间 gather（C2）」表述为「按每个 granted space 路由 store 组 stores_by_space；多空间并发在 factory.recalls fan-out」。

- [ ] **Step 4: 跑测试确认 green**

```bash
cd CIOaas-python && uv run pytest tests/rag/test_search_service.py tests/rag/test_recall_service.py -q
```
预期：PASS（`test_recall_service.py` 不改即绿——它 mock `recall_by_spaces`，签名未变）。

- [ ] **Step 5: 提交（需用户确认）**

```bash
git add source/rag/application/service/search_service.py tests/rag/test_search_service.py
git commit -m "refactor(rag): search_service routes per-space stores via ResolvedScope + _stores_for_granted"
```

---

## Task 5：文档同步 + 全量回归 + 规范自查

**Files:**
- Modify: `CIOaas-python/source/rag/CLAUDE.md`
- Modify: `CIOaas-python/source/rag/README.md`
- Modify: `CLAUDE.md`（根，RAG 段）

- [ ] **Step 1: 跑 rag 全量测试套件（门禁）**

```bash
cd CIOaas-python && uv run pytest tests/rag/ -q
```
预期：全绿。若有红，定位到对应任务的 Step 修复后重跑。

- [ ] **Step 2: 改 `source/rag/CLAUDE.md`**

- 「目录结构」中 `storage/base.py` / `pg_store.py` / `es_store.py` 描述：把「跨空间并发（C2）/ search_* 接受 space_ids」改为「search_* 单空间；多空间并发在 factory.recalls 编排」。
- `factory.py` 描述：「recalls(多空间召回+记录) + recall(单空间,委托前者)」改为「recalls(多空间编排：fan-out 单 space 叶子 + 按 RRF 分合并 + record_recall 记录一次) + recall(单 space 叶子,纯召回不记录)」。
- 「§五 特殊约定」Processor 契约段：`_gather_candidates` 注明单 space + 可选 query_vector；召回范围由 service 圈定后**按每个 space 各自路由 store**、多空间并发在 factory.recalls。
- `search_service` 一行：「圈定 space(ACL) → recall_by_spaces(查配置 + 按 space 路由 stores_by_space) → factory.recalls(fan-out + 合并 + record_recall) → enrich」。

- [ ] **Step 3: 改 `source/rag/README.md`**

把 `factory.py` 那行（多空间召回 / 单空间）与任何「storage 跨空间并发 C2」描述改为与上一致（单 space 叶子 + factory.recalls fan-out + 合并 + 记录一次）。

- [ ] **Step 4: 改根 `CLAUDE.md`（RAG 段）**

「召回编排」「召回三层职责」段：把「factory.recalls（…多空间在 storage 层并发查询后融合）→ storage（连库 + 向量/关键词查询）」改为「factory.recalls（embed 一次 + 对每个 space 用各自 store 并发调单 space 叶子 recall + 按 RRF 分合并 top_k + record_recall 记录一次）→ processor.recall（单 space）→ storage（单 space 查询）」；service 一段补「按每个 granted space 路由 store 组 stores_by_space」。

- [ ] **Step 5: 规范自查**

按 `CIOaas-python/standards/architecture.md` + `coding.md` + `source/rag/CLAUDE.md` 复查改动：分层（infrastructure 不查 DB、service 是事务/路由边界）、类型注解、docstring、命名。修正不符合项。再次 `uv run pytest tests/rag/ -q` 确认绿。

- [ ] **Step 6: 提交（需用户确认）**

```bash
git add source/rag/CLAUDE.md source/rag/README.md ../CLAUDE.md
git commit -m "docs(rag): single-space recall contract + factory.recalls fan-out orchestration"
```

（根 `CLAUDE.md` 在父仓库，需在父仓库 `LG/` 下 `git add CLAUDE.md` 单独提交；`CIOaas-python` 子仓库只提交其内文件。两仓库提交均需用户确认。）

---

## Self-Review（计划编写后自查结果）

**1. Spec coverage：** spec §3/§4 各层改动 → Task 1（storage）/ Task 2（processor）/ Task 3（factory）/ Task 4（service）逐一覆盖；§5 ResolvedScope → Task 4 Step 3；§6 跨 space 融合（sort_by_score 合并）→ Task 3 Step 3；§4.3 embed 一次 + 记录一次 → Task 3 Step 3 + 测试 ②⑤；§8 文档 → Task 5。仓储层 0 改动、`record_recall` 不变 → 无任务（符合预期）。✓

**2. Placeholder scan：** 无 TBD/TODO；每个改动步骤含完整代码或完整测试代码。✓

**3. Type/signature consistency：** `search_vector/keyword(space_id=...)`、`recall(space_id=..., query_vector=...)`、`recalls(stores_by_space=...)`、`recall`(叶子)、`ResolvedScope` 字段（granted/dropped/granted_spaces/business_type/process_type/embedding_provider/embedding_model）、`_stores_for_granted(granted_spaces, company_id)` 在各任务间签名一致；`record_recall(granted_space_ids=..., hits=..., duration_ms=...)` 与 base 不变签名一致。✓

**4. 注意点：** `test_recall_service.py` 不改、应保持绿（mock `recall_by_spaces`，其 `recall→recall_by_spaces` 边界签名未变）；`RagSearchLog.space_ids` 列保持 list（召回覆盖空间数组，非本次契约范围）。
