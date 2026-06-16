# RAG 召回契约改为单 space 粒度 + 按 space 路由 store —— 设计文档

- 日期：2026-06-16
- 范围：`CIOaas-python/source/rag/`（storage / processor / factory / search_service）
- 状态：设计待评审

## 1. 背景与问题

当前召回链对「多 space」的处理建立在两个隐含假设上：

1. `search_service._resolve_visibility` **强制一次召回的所有 space 共享同一个** `storage_backend` + `business_type` + `embedding`（provider, model）。
2. `search_service.recall_by_spaces` 用 `_store_for_granted(granted[0])` **取第一个 space 路由出唯一一个 store**，再把整批 `space_ids` 喂给它；真正的「多 space 并发」发生在最底层 `PgVectorStore.search_vector/keyword` —— 对 `space_ids` 列表里每个 space `asyncio.gather` 并发查询，但它们**共用同一个 engine、同一张 chunk 表**，仅靠 `space_id` 列过滤。

因此现状的召回契约本质是「**同一个库、同一张表里按 space_id 列过滤的批量查询**」。这对应当前形态：一个数据源（storage connection）绑定一张表，多个 `space_id` 共表。

未来形态是「**一 space 一库一表**」：每个 space 可能有自己独立的数据库连接 + 表。届时召回的最小单元必须是单个 space：给定 `(数据库连接/store, business_type, space_id)` 就能取该空间的数据。当前把 `space_ids: list[str]` 作为最底层入参的设计与该方向冲突 —— 这是本次要纠正的核心。

关键利好：仓储层 `domain/repository/chunk_repository.py` 的 `search_vector_single_space` / `search_keyword_single_space` **本来就是单 space**。多 space 的 `asyncio.gather` 是 storage 层**后加**的一层。所以本次改动的本质是「**把 storage 层那层跨空间 gather 拆掉、上移到 factory 编排层**」，仓储层 0 改动。

## 2. 目标 / 非目标

### 目标
- 把召回的最小契约改为**单 space**：`VectorStore.search_*`、`Processor.recall` / `_gather_candidates`、`factory.recall` 全部以单个 `space_id` 为粒度。
- 「多 space 并发 + 跨 space 融合」从 storage 叶子层**上移**到 `factory.recalls` 编排层。
- store 路由改为**按每个 space 各自解析**（`get_vector_store_for_space`），去掉 `granted[0]` 取代表的假设，为「一 space 一库」预留正确的路由接缝。

### 非目标（本次不做，留作独立下一步）
- **不**放开 `_resolve_visibility` 的「同 backend / 同 business_type / 同 embedding」一致性校验（保持现状，仅重构内部结构）。
- **不**实现「每个 space 绑定独立 connection / 独立表名」的具体连接装配（沿用现有 `connection_resolver` / `custom_engine` 能力；粒度和路由接缝改正确即可，未来「一 space 一库」是配置问题，不需再动召回代码）。
- **不**改动入库（vectorize / store）链路。

## 3. 新契约（自底向上）

| 层 | 现状 | 改为 |
|---|---|---|
| `chunk_repository.search_*_single_space` | 单 space | **不变** |
| `VectorStore.search_vector/keyword`（Protocol + pg + es） | `space_ids: list[str]`，内部 gather / `terms` | `space_id: str`；PG 去掉 gather（单 space 查），ES `terms`→`term` |
| `Processor._gather_candidates` / `recall`（base + standard + structured） | `space_ids: list[str]` | `space_id: str` + 新增可选 `query_vector: list[float] \| None`（预算好的查询向量，避免多 space 重复 embed） |
| `factory.recall`（单 space 叶子） | 包成 `[space_id]` 委托 `recalls` | 成为**真正的单 space 叶子**：`build_processor` → `processor.recall(space_id)`，**不记录** |
| `factory.recalls`（多 space 编排） | 单 store + `space_ids` 批量 + 记录一次 | 收 `stores_by_space: dict[str, VectorStore]`；**embed 一次** → 并发 N 个单 space 叶子召回 → 按 RRF 分数合并取全局 `top_k` → **记录一次** |
| `search_service.recall_by_spaces` | `_store_for_granted(granted[0])` 单 store | 按每个 granted space 各自 `get_vector_store_for_space` 组 `stores_by_space` → 调 `recalls` |

## 4. 各层改动详述

### 4.1 storage 层

**`storage/base.py`（VectorStore Protocol）**
- `search_vector` / `search_keyword`：`space_ids: list[str]` → `space_id: str`。
- 更新模块/方法 docstring：删除「决策 C2 跨空间并发在实现内」「search_* 接受多 space_ids」的描述，改为「单 space 召回，多 space 并发由 `factory.recalls` 编排」。

**`storage/pg_store.py`**
- `search_vector`：删除 `asyncio.gather(... for space_id in space_ids)`，直接 `_do_vector_single_space(space_id, query_vector, limit=top_k*_OVER_FETCH_MULTIPLIER, file_id)` → 按 score 降序 → `[:top_k]`。
- `search_keyword`：同理，单 space `_do_keyword_single_space(...)` → `[:top_k]`。
- `_do_*_single_space` 等内部方法**不变**。更新 docstring（删除 C2 相关描述）。

**`storage/es_store.py`**
- `search_vector` / `search_keyword`：`space_ids` → `space_id`。
- `_space_filter(space_ids, filters)` → `_space_filter(space_id, filters)`：`{"terms": {"space_id": space_ids}}` → `{"term": {"space_id": space_id}}`。
- 行为变化：同公司多 space 从「1 次 `terms` 查同一索引」变为「N 次 `term` 查同一索引」（同公司 → 同 fingerprint → 同缓存 store 实例）。属可接受的轻微多查询，换统一的单 space 契约（见 §7 权衡）。

**`storage/__init__.py`**：更新顶部注释（C2 描述）。

### 4.2 processor 层

**`processor/base.py`**
- `recall`（abstract）：`space_ids: list[str]` → `space_id: str`，新增 `query_vector: list[float] | None = None`。
- `_gather_candidates`：`space_ids` → `space_id`，新增 `query_vector` 参数；body 改为 `query_vector = query_vector or await self._embedder.embed_query(query)`（传入则复用，不再 embed），`store.search_vector(space_id=space_id, ...)` / `store.search_keyword(space_id=space_id, ...)`。
- `record_recall`：**签名与逻辑不变**（仍接受 `granted_space_ids: list[str]`，由编排层传入所有 space + 合并后命中，记录一次）。

**`processor/standard/standard_processor.py`**、**`processor/structured/structured_processor.py`**
- `recall`：`space_ids` → `space_id`，新增 `query_vector` 透传给 `_gather_candidates`。
- 内部 `_rrf_fuse`（等权 / 向量加权）、`sort_by_score`、截断 `top_k` **逻辑不变**。每次返回单个 space 的已融合命中。

### 4.3 factory 层

**`processor/factory.py`**

`recall`（单 space 叶子，**纯召回不记录**）：
```python
async def recall(*, process_type, embedding_provider, embedding_model,
                 store, query, top_k, company_id, space_id,
                 query_vector=None, filters=None) -> list[SearchHit]:
    processor = build_processor(process_type, embedding_provider=..., embedding_model=...)
    return await processor.recall(
        store=store, query=query, query_vector=query_vector, top_k=top_k,
        company_id=company_id, space_id=space_id, filters=filters,
    )
```

`recalls`（多 space 编排，**记录一次**）：
```python
async def recalls(*, process_type, embedding_provider, embedding_model,
                  stores_by_space: dict[str, VectorStore],
                  query, top_k, company_id, user_id, caller_type,
                  filters=None) -> list[SearchHit]:
    processor = build_processor(process_type, embedding_provider=..., embedding_model=...)
    space_ids = list(stores_by_space.keys())
    started = time.monotonic()
    # embed 一次（保留校验保证所有 space 同 embedding），传给每个单 space 叶子召回
    query_vector = await processor.embedder.embed_query(query)
    per_space = await asyncio.gather(*(
        processor.recall(
            store=stores_by_space[sid], query=query, query_vector=query_vector,
            top_k=top_k, company_id=company_id, space_id=sid, filters=filters,
        )
        for sid in space_ids
    ))
    merged = Processor.sort_by_score([h for hits in per_space for h in hits])[:top_k]
    duration_ms = int((time.monotonic() - started) * 1000)
    processor.record_recall(
        user_id=user_id, granted_space_ids=space_ids, query=query, top_k=top_k,
        caller_type=caller_type, hits=merged, duration_ms=duration_ms,
    )
    return merged
```

要点：
- **embed 一次**：保持「embed_query 全程只算一次」，trace 内仅一条 `rag_query` LLM 调用。
- **记录一次**：仍由 `processor.record_recall` 触发（base 契约不变），但在合并完成后调一次，`granted_space_ids=所有 space`、`hits=合并结果`；**单 space 叶子 `factory.recall` 不记录**（否则 N 条 search_log）。
- **`factory.recall` 的定位**：它就是本次诉求的「`(store/连接, business_type, space_id) → 该空间数据`」契约本身 —— 纯单 space 召回、无记录副作用。需要单 space 召回**并记录**时走 `recalls(stores_by_space={space_id: store}, ...)`（编排层负责记录）。两者同在 `__all__` 公开。

### 4.4 service 层

**`processor/factory.py` 的调用方 `search_service.recall_by_spaces`**
- `_resolve_visibility` 改造（见 §5），返回 `ResolvedScope`（含 granted 的 `RagSpace` 对象）。
- 新增 `_stores_for_granted(granted_spaces, company_id) -> dict[str, VectorStore]`：对每个 granted `RagSpace` 调 `get_vector_store_for_space(space, company_id)`，组成 `{space_id: store}`。复用 `_resolve_visibility` 已加载的 space 对象，**不二次查库**。
- `recalls(...)` 调用：去掉 `store=...` 单 store，改传 `stores_by_space=...`。

## 5. `_resolve_visibility` 重构为 dataclass

现状返回 6 元组，且 store 路由会二次查库。重构：

```python
@dataclass
class ResolvedScope:
    granted: list[str]            # granted space ids（顺序保留）
    dropped: list[str]
    granted_spaces: list[RagSpace]  # granted 的 space 对象（store 路由复用，避免二次查库）
    business_type: str | None
    process_type: str | None
    embedding_provider: str | None
    embedding_model: str | None
```

`_resolve_visibility` 在裁剪可见空间时把 `space` 对象收集进 `granted_spaces`；一致性校验（同 backend / 同 business_type / 同 embedding）**逻辑不变**。`recall_by_spaces` 改用 `scope.granted` / `scope.granted_spaces` / `scope.business_type` 等字段；`_stores_for_granted(scope.granted_spaces, company_id)` 直接复用对象。`_store_for_granted`（取 granted[0] 单 store）删除。

## 6. 跨 space 融合语义

- 每个 space 内部仍：候选收集 → `_rrf_fuse`（STANDARD 等权 / STRUCTURED 向量加权）→ `sort_by_score` → 截 `top_k`（**语义不变**）。
- 编排层把 N 个 space 各自已融合命中拼接 → `Processor.sort_by_score` → 截全局 `top_k`。
- 正确性依据：RRF 分（`1/(k+rank)`）是纯排名分、跨 space 可比；又因「保留校验」所有 space 同 process_type → 融合参数（`rrf_k` / 权重）一致 → 合并干净。
- 与今天的差异：今天是「跨 space 合并原始候选后做一次全局 RRF」，新版是「每 space 各自 RRF 再按分合并」。对 RRF 这类排名分两者几乎等价；`_similarity`（向量真实余弦相似度）仍逐片段保留在 metadata，`_enrich` 行为不变。

## 7. 权衡

- **PG**：行为基本等价 —— 本来就是 N 次单 space 查询，只是从 storage 内部 `gather` 移到 factory 编排 `gather`。
- **ES**：从「1 次 `terms` 查」变「N 次 `term` 查同一索引」（同公司同 store 实例，缓存命中）。轻微多几次查询，换统一的单 space 契约。可接受。
- **保留一致性校验**：跨 backend / 业务类型 / embedding 仍禁止。未来「一 space 一库 + 跨类型融合」是独立下一步 —— 契约已就位，只差放开校验 + 把记录改成按 per-space `chunk_cls`（base `record_recall` 当前按单一 `self.chunk_cls`）。

## 8. 改动文件清单

代码：
- `infrastructure/storage/base.py`
- `infrastructure/storage/pg_store.py`
- `infrastructure/storage/es_store.py`
- `infrastructure/storage/__init__.py`（注释）
- `infrastructure/processor/base.py`
- `infrastructure/processor/standard/standard_processor.py`
- `infrastructure/processor/structured/structured_processor.py`
- `infrastructure/processor/factory.py`
- `application/service/search_service.py`

测试（`tests/rag/`）：
- storage 层 pg/es 的 `search_*` 单 space 签名 + 行为（去 gather / `term`）。
- processor 层 standard/structured `recall` 单 space + `query_vector` 透传。
- factory `recalls` 编排（多 space fan-out + 合并 + 记录一次 + embed 一次）、`recall` 叶子不记录。
- service `recall_by_spaces` 组 `stores_by_space` + `ResolvedScope`。

文档：
- `source/rag/CLAUDE.md`、根 `CLAUDE.md`（RAG 段）、`source/rag/README.md`：把「决策 C2 storage 内部跨空间并发」表述改为「单 space 叶子 + `factory.recalls` 上层 fan-out + 按 RRF 分合并」。

## 9. 验证

- `uv run pytest tests/rag/`（storage / processor / service / factory 全绿）。
- 规范自查：按 `CIOaas-python/standards/` + `source/rag/CLAUDE.md` 复查分层、类型注解、docstring。
- 行为回归：单 space 召回结果与改前一致；多 space 召回 top_k 集合与改前基本一致（RRF 合并语义差异见 §6）；search_log 仍每次一条、三级 hit_count 累加正确。

---

## 10. 增量（2026-06-16 追加）：connection 维度做**前端 space 筛选器**（只传 spaceIds）

recall 页（`/devSupport/rag/search`）按三个维度组织召回：**业务类型（mode）+ connection（数据源）+ space（多选）**。

### 决策（已与用户确认 · 取代早先「后端 connectionRef」方案）
- **筛选在前端、后端只认 spaceIds**：connection（含 Default）+ 业务类型在**前端**收窄 space 多选框；用户多选 space（留空 = 该筛选下全部，前端展开成显式 spaceIds）；后端 `/recall` **只收 mode + spaceIds**，按 spaceId 取各自配置 → 逐个 space 轮询召回 → 全部召回后统一排序。这正是单 space 重构 + `stores_by_space` 已实现的链路。
- **回退早先的后端 connectionRef**：删除 `RecallRequest.connectionRef`、`_resolve_visibility` 的连接筛选、routes 透传及对应测试。**单 space 重构 + 按 space 路由 store（`get_vector_store_for_space` / `stores_by_space`）保留**——那是召回核心，与连接筛选无关。
- **connection 下拉三类**：`All connections`（清空 = 不筛）/ `Default`（系统默认库、未绑定自建连接即 `connection_ref` 为空的 space）/ 各自创建的 connection（value = `code`）。
- **space 受 connection ∩ 业务类型 双重筛选**、可多选；切 connection 时剔除不属于该连接的已选 space。

### 改动
**后端（CIOaas-python）= 回退连接筛选**：
1. `interfaces/vo/request.py`：删 `RecallRequest.connectionRef`。
2. `interfaces/routes.py` `/recall`：去掉 `connection_ref=request.connectionRef`。
3. `application/service/search_service.py`：`recall` / `recall_by_spaces` / `_resolve_visibility` 去掉 `connection_ref` 参数与连接筛选逻辑（恢复到单 space 重构后、加连接筛选前的状态）。
4. `tests/rag/test_recall_service.py`：删 3 个 connection 测试。

**前端（CIOaas-web）= 连接做前端筛选器**：
1. `SpaceDTO.connectionRef` + `toSpaceDTO` 映射 **保留**（前端筛选所需；后端 space 接口本就返回 `connectionRef`）。
2. `ragApi.RecallRequest.connectionRef` **删除**；`useRecall.runRecall` 恢复 4 参（mode/query/topK/spaceIds），不再传 connectionRef。
3. `RecallPanel`：connection 下拉加 `Default`（哨兵值）+ 各自创建连接；`connectionRef` 仅作**本地筛选 state**，不进召回请求。space 选项按 `processType(mode) ∩ connection` 过滤：`Default → connectionRef 为空`、`code → connectionRef===code`、`All → 不筛`。`handleRecall` 计算有效 spaceIds（多选非空用所选；空且有连接筛选则展开成收窄后的全部 spaceIds；空且无连接筛选则传 undefined 让后端按 mode 展开）。

### 行为
后端 `/recall` 契约与单 space 重构后一致（mode + spaceIds + fileId）；connection 不再进后端。`search`（chatbot DTO）不受影响。

---

## 11. 增量（2026-06-16 追加）：混合召回（放开同类型校验 · 取代 §10 的"保留校验/单 mode"）

recall 页三个筛选**都改多选 + All**（业务类型 / 连接 / space）。一次召回可能跨**不同业务类型 / embedding / 后端**的 space。**放开**单 space 重构时保留的「同后端 / 同业务类型 / 同 embedding」校验，每个 space 用**各自配置**独立召回再合并。

### 决策（已与用户确认）
- **放开校验**：`_resolve_visibility` 删除三道一致性校验，只保留公司可见性；返回每个 granted space 各自的配置（process_type / business_type / embedding / store）。
- **per-space 处理器 + per-embedding 向量**：`factory.recalls` 不再 build 单一处理器/embed 一次；按 `process_type` 各 build 处理器（≤2：STANDARD/STRUCTURED），按**不同 embedding 各 embed query 一次**（同模型复用），每个 space 用自身处理器 + 自身 store 召回。
- **合并 = 按 business_type 分组 min-max 归一 → 全局取 topK**：各 business_type 组内命中按 `.score` min-max 归一到 [0,1]（单调，单类型时排序与原一致），再全局合并按归一分降序取 topK。向量真实相似度 `_similarity` 仍保留在 metadata 供 `_enrich` 展示。
- **记录移到 service、按 business_type 分组**：召回记录由 `recall_by_spaces` 负责——`ai_rag_search_log` 写**一条**（user_id + 全部 space_ids + 命中数）、`RagEntry`/`RagSpace` hit_count 各累加一次（公共表）、**chunk hit_count 按 business_type 分组写各自 chunk 表**（`get_business_chunk`）。**移除** `Processor.record_recall` 契约与 `factory.recalls` 内的记录调用——`factory.recalls` 变纯召回+合并、返回命中。
- **去掉 mode**：`RecallRequest` 删 `mode`；`/recall` 直接走 `recall_by_spaces(space_ids)`（前端筛选产出 spaceIds）。`recall(mode)` 方法移除（chatbot 走 `search`/`recall_by_spaces`，不受影响）。

### 改动
**后端（CIOaas-python）**：
1. `application/service/search_service.py`：
   - `ResolvedScope` 简化为 `granted / dropped / granted_spaces`（删 business_type/process_type/embedding_* 共享字段）。
   - `_resolve_visibility`：删三道校验，只裁可见性 + 收集 granted_spaces。
   - `recall_by_spaces`：按 granted_spaces 构造**每个 space 的 RecallTarget**（space_id + process_type + business_type + embedding + `get_vector_store_for_space`），调 `factory.recalls(targets=...)`；拿回合并命中后调 `_record_recall`（search_log 一条 + entry/space 各一次 + chunk 按 business_type 分组）。
   - 删 `recall(mode)`（或保留薄壳直接转 `recall_by_spaces`，不带 mode）；`search`（DTO）继续走 `recall_by_spaces`。
   - `_record_recall`：新签名带 `business_type_by_space`，chunk 计数按 business_type 分组。`save_recall_record` 旧函数并入/重写。
2. `infrastructure/processor/factory.py`：
   - 定义 `RecallTarget`（space_id / process_type / business_type / embedding_provider / embedding_model / store）。
   - `recalls(targets, query, top_k, company_id, filters)` → per-process_type build 处理器 + per-embedding embed + 并发 per-space recall + `_normalize_and_merge`（按 business_type 分组 min-max 归一合并取 topK）。**纯召回不记录**。
   - `recall`（单 space 叶子）保留。
3. `infrastructure/processor/base.py`：删 `Processor.record_recall`（记录移到 service）。
4. `interfaces/vo/request.py`：`RecallRequest` 删 `mode`（留 query/topK/spaceIds/fileId）。
5. `interfaces/routes.py`：`/recall` → `recall_by_spaces(space_ids=request.spaceIds, ...)`。
6. 测试：service（混合 targets 构造 + 归一合并 + 分组记录）、factory（per-space 处理器 + 归一合并）、删 mode 相关用例。

**前端（CIOaas-web）**：
1. 业务类型：单选下拉 → **多选 + All**（值为 process_type 集合；空/All = 不按类型筛）。
2. 连接：单选 → **多选 + All**（含 Default 哨兵 + 各连接 code；空/All = 不筛）。
3. space 选项 = `spaces.filter(processType ∈ 选中类型集 ∩ connection ∈ 选中连接集)`；多选；切筛选时剔除越界已选。
4. `handleRecall`：有效 spaceIds = 多选非空用所选；否则展开成当前筛选下全部 space id；请求**只传 spaceIds**（去掉 mode）。
5. `ragApi.RecallRequest` 去 mode；`useRecall.runRecall` 去 mode（只 query/topK/spaceIds）。

### 兼容性说明（更新既有不变式）
- §6「保留一致性校验」与 §10「后端只收 mode+spaceIds」被本节取代：跨类型混合召回，校验放开。
- rag/CLAUDE.md「召回记录由 base Processor.record_recall 契约触发」不变式**更新**为「召回记录由 service `recall_by_spaces._record_recall` 负责，chunk 计数按 business_type 分组写各自表」。新增 process_type 仍自动被覆盖（按 business_type→chunk 表分组记录）。
