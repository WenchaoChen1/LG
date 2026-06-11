# AI Chatbot 历史与两端完善（Python 后端）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 chatbot 补齐多轮上下文回填、thread 重命名/软删除端点（含 deleted 过滤）、管理端可访问公司注入与续聊换公司。
**Architecture:** 严格沿现有 DDD 分层增量改造：`repository.py` 补单表查询/软删与 deleted 过滤；`chat_service.stream_turn` 编排层注入历史；`routes.py`/`vo.py` 增 PATCH/DELETE 端点与发送分支改造。不动 LangGraph 图结构、`llm` 公共层与已落地的 SSE 统一序列化（`stream_sse` 泵 + `sse_event()` 协议）。
**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / LangGraph / pytest
**关联 spec:** docs/superpowers/specs/2026-06-11-chat-history-and-two-end-design.md

---

## 执行约定（执行者必读）

- 工作目录：`C:\github-code\LG\CIOaas-python`；测试命令统一 `uv run pytest tests/chatbot/ -v`。
- **基线（2026-06-11，另一会话未提交改动，叠加其上、不要回退）**：SSE 序列化已合并进 `llm/infrastructure/llm_router/sse.py`（通用 `to_sse` + `stream_sse` 泵）、`chatbot/interfaces/sse_events.py` 已删除、`chat_events.py` 为 `_SSE_NAME + sse_event()` 协议版（含 `TitleGenerated`、`Done = StreamDone`）、`chat_service.stream_turn` 已有 `needs_title` 标题生成与 try/finally 部分落库、`routes.py` 已用 `stream_sse` 泵且 `needs_title` 已接线。**标题、停止生成、SSE 重构不在本计划范围**。
- 改任何文件前先 Read 当前版本（工作区有未提交改动，行号以实际为准）。
- TDD：每 Task 先写失败测试 → 确认失败 → 最小实现 → 全绿。
- **提交**：本计划执行期间**不执行任何 git add/commit**（与另一会话的未提交改动混在工作区，统一由主会话最后与用户确认提交方案）。
- 每个 Task 完成后 `tests/chatbot/` 必须全绿。

---

## Task 1：repository 新增 `get_recent_messages` / `soft_delete_thread` 与 deleted 过滤

**Files:**
- Modify: `source/chatbot/domain/repository.py`（`get_messages` 的 EXISTS 子查询、`get_thread` 归属分支、文件末尾追加两个函数）
- Test: `tests/chatbot/domain/test_repository.py`（末尾追加，沿用既有 mock-session 风格）

**Steps:**

- [x] 1. 在 `tests/chatbot/domain/test_repository.py` 末尾追加 4 个失败测试（先 Read 该文件，沿用其既有 mock get_session 的写法；以下骨架按需对齐既有风格）：

```python
def test_get_recent_messages_queries_desc_with_limit_and_returns_ascending(mocker):
    session = mocker.MagicMock()
    cm = mocker.MagicMock()
    cm.__enter__.return_value = session
    cm.__exit__.return_value = False
    mocker.patch.object(repo, "get_session", return_value=cm)
    m3, m2, m1 = object(), object(), object()
    session.scalars.return_value.all.return_value = [m3, m2, m1]  # DB 按 seq 倒序给

    rows = repo.get_recent_messages(thread_id="t1", limit=3)

    assert rows == [m1, m2, m3]  # 反转为升序返回
    stmt = str(session.scalars.call_args.args[0])
    assert "ORDER BY ai_chatbot_message.seq DESC" in stmt
    assert "LIMIT" in stmt


def test_soft_delete_thread_sets_deleted_true(mocker):
    session = mocker.MagicMock()
    cm = mocker.MagicMock()
    cm.__enter__.return_value = session
    cm.__exit__.return_value = False
    mocker.patch.object(repo, "get_session", return_value=cm)

    repo.soft_delete_thread(thread_id="t1")

    stmt = session.execute.call_args.args[0]
    assert stmt.compile().params["deleted"] is True
    assert session.commit.called


def test_get_thread_owner_query_filters_deleted(mocker):
    """软删 thread 经归属查询不可见（续聊 404 的数据层保障）。"""
    session = mocker.MagicMock()
    cm = mocker.MagicMock()
    cm.__enter__.return_value = session
    cm.__exit__.return_value = False
    mocker.patch.object(repo, "get_session", return_value=cm)
    session.scalars.return_value.first.return_value = None

    repo.get_thread(thread_id="t1", user_id="u1")

    stmt = str(session.scalars.call_args.args[0])
    assert "ai_chatbot_thread.deleted IS" in stmt


def test_get_messages_owner_query_filters_deleted(mocker):
    """软删 thread 的消息经归属查询不可读。"""
    session = mocker.MagicMock()
    cm = mocker.MagicMock()
    cm.__enter__.return_value = session
    cm.__exit__.return_value = False
    mocker.patch.object(repo, "get_session", return_value=cm)
    session.scalars.return_value.all.return_value = []

    repo.get_messages(thread_id="t1", user_id="u1")

    stmt = str(session.scalars.call_args.args[0])
    assert "ai_chatbot_thread.deleted IS" in stmt
```

- [x] 2. 运行 `uv run pytest tests/chatbot/domain/test_repository.py -v`，确认：前两个报 `AttributeError`（函数不存在），后两个断言失败（语句无 deleted 过滤）。
- [x] 3. 修改 `source/chatbot/domain/repository.py`：
      ① `get_messages` 的 `if user_id is not None:` 块改为：

```python
        if user_id is not None:
            stmt = stmt.where(
                select(ChatThread.thread_id)
                .where(ChatThread.thread_id == thread_id)
                .where(ChatThread.user_id == user_id)
                .where(ChatThread.deleted.is_(False))
                .exists()
            )
```

      ② `get_thread` 的归属查询分支改为：

```python
        return session.scalars(
            select(ChatThread)
            .where(ChatThread.thread_id == thread_id)
            .where(ChatThread.user_id == user_id)
            .where(ChatThread.deleted.is_(False))
        ).first()
```

      ③ 文件末尾追加：

```python
def get_recent_messages(*, thread_id: str, limit: int = 10) -> list[ChatMessage]:
    """最近 limit 条消息（升序返回）：按 seq 倒序取 limit 条后反转（多轮上下文用）。"""
    with get_session() as session:
        rows = list(session.scalars(
            select(ChatMessage).where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.seq.desc()).limit(limit)
        ).all())
    return list(reversed(rows))


def soft_delete_thread(*, thread_id: str) -> None:
    """软删 thread（deleted=TRUE）；list/get/续聊均经 deleted 过滤后不可见。"""
    with get_session() as session:
        session.execute(update(ChatThread).where(ChatThread.thread_id == thread_id)
                        .values(deleted=True))
        session.commit()
```

- [x] 4. 运行 `uv run pytest tests/chatbot/ -v`，确认全绿（`list_threads` 已有 deleted 过滤，保持不动）。

---

## Task 2：chat_service 注入最近 10 条历史到 `state["history"]`

**Files:**
- Modify: `source/chatbot/application/chat_service.py`（`stream_turn` 函数体开头 + state 的 `"history"`）
- Test: `tests/chatbot/application/test_chat_service.py`（先 Read 当前版本——另一会话已改过；imports 后加 autouse fixture，末尾加 1 个测试）

**Steps:**

- [x] 1. Read `tests/chatbot/application/test_chat_service.py` 当前版本，在其 import 块后插入 autouse fixture（`stream_turn` 开场将读历史，既有用例统一给空历史，否则 mock 击穿到真实 DB）：

```python
@pytest.fixture(autouse=True)
def _empty_history(mocker):
    """stream_turn 开场读历史；既有用例不关心历史，统一 mock 为空。"""
    mocker.patch.object(svc.repo, "get_recent_messages", return_value=[])
```

      > 注：`svc` 为该测试文件中 chat_service 的既有导入别名，以实际为准。

      并在文件末尾追加失败测试：

```python
@pytest.mark.asyncio
async def test_stream_turn_injects_recent_history_into_graph_state(mocker):
    """续聊：落本轮用户消息之前读最近历史，仅 user/assistant 注入 state["history"]。"""
    calls: list[str] = []
    read_kwargs: dict = {}
    rows = [
        SimpleNamespace(role="user", content="earlier q"),
        SimpleNamespace(role="system", content="internal"),   # 非 user/assistant，应过滤
        SimpleNamespace(role="assistant", content="earlier a"),
    ]

    def _recent(**kw):
        calls.append("read_history")
        read_kwargs.update(kw)
        return rows

    mocker.patch.object(svc.repo, "get_recent_messages", side_effect=_recent)

    captured: dict = {}

    class _Graph:
        async def ainvoke(self, state):
            captured["state"] = state
            return {"needs_company_pick": False, "blocked_reason": None,
                    "active_company_id": "c-1",
                    "synthesis_messages": [{"role": "user", "content": "q"}],
                    "tool_results": [], "attribution": []}

    mocker.patch.object(svc, "get_chat_graph_app", return_value=_Graph())

    async def _astream(messages, **kw):
        yield TextChunk(delta="hi")

    mocker.patch.object(svc.llm_db_router, "astream", _astream)

    def _append(**kw):
        calls.append("append_user" if kw.get("role") == "user" else "append_assistant")
        return "m1"

    mocker.patch.object(svc.repo, "append_message", side_effect=_append)

    identity = SimpleNamespace(user_id="u1", org_id=None)
    async for _ in svc.stream_turn(thread_id="t1", question="q", identity=identity,
                                   end_type="company", active_company_id="c-1"):
        pass

    # 1) 历史在落本轮用户消息之前读取（窗口不含当前问题）
    assert calls[:2] == ["read_history", "append_user"]
    assert read_kwargs == {"thread_id": "t1", "limit": 10}
    # 2) 只保留 user/assistant，格式 [{"role","content"}]
    assert captured["state"]["history"] == [
        {"role": "user", "content": "earlier q"},
        {"role": "assistant", "content": "earlier a"},
    ]
```

- [x] 2. 运行 `uv run pytest tests/chatbot/application/test_chat_service.py -v`，确认新测试失败（`calls[:2]` 不含 read_history、`history == []`），既有用例仍绿。
- [x] 3. 修改 `source/chatbot/application/chat_service.py` 的 `stream_turn`：函数体第一行 `repo.append_message(...)` 之前插入：

```python
    # 多轮上下文：先读历史（窗口不含本轮问题），再落当前用户消息——顺序不可倒置。
    # 窗口 10 条与 build_synthesis 现有 history[-10:] 对齐，控制 token 成本。
    recent = repo.get_recent_messages(thread_id=thread_id, limit=10)
    history = [{"role": m.role, "content": m.content}
               for m in recent if m.role in ("user", "assistant")]
```

      并把 state 中 `"history": []` 改为 `"history": history`。
- [x] 4. 运行 `uv run pytest tests/chatbot/ -v`，确认全绿。

---

## Task 3：vo + routes 新增 PATCH（重命名）/ DELETE（软删）端点

**Files:**
- Modify: `source/chatbot/interfaces/vo.py`（末尾追加）
- Modify: `source/chatbot/interfaces/routes.py`（末尾追加两个端点）
- Test: `tests/chatbot/interfaces/test_routes.py`（先 Read 当前版本，沿用其 `_app()`/TestClient 模式，末尾追加 6 个测试）

**Steps:**

- [x] 1. 在 `tests/chatbot/interfaces/test_routes.py` 末尾追加失败测试（`_app()` 等 helper 以该文件现状为准）：

```python
def test_rename_thread_ok(mocker):
    """PATCH /threads/{id}：owner 校验通过 → strip 后 set_title，返回 OK 信封。"""
    from chatbot.interfaces import routes
    mocker.patch.object(routes.repo, "get_thread",
                        return_value=SimpleNamespace(thread_id="t-1"))
    spy = mocker.patch.object(routes.repo, "set_title")
    c = TestClient(_app())
    r = c.patch("/api/ai/chat/threads/t-1", json={"title": "  Q1 复盘  "})
    assert r.status_code == 200
    assert r.json() == {"success": True, "code": 0, "message": "OK"}
    spy.assert_called_once_with(thread_id="t-1", title="Q1 复盘")


def test_rename_thread_not_owner_404(mocker):
    """非本人 thread：404（IDOR 语义），不触达 set_title。"""
    from chatbot.interfaces import routes
    mocker.patch.object(routes.repo, "get_thread", return_value=None)
    spy = mocker.patch.object(routes.repo, "set_title")
    c = TestClient(_app())
    r = c.patch("/api/ai/chat/threads/t-1", json={"title": "x"})
    assert r.status_code == 404
    spy.assert_not_called()


def test_rename_thread_blank_title_422(mocker):
    """全空白标题：strip 后为空 → 422，不触达 set_title。"""
    from chatbot.interfaces import routes
    mocker.patch.object(routes.repo, "get_thread",
                        return_value=SimpleNamespace(thread_id="t-1"))
    spy = mocker.patch.object(routes.repo, "set_title")
    c = TestClient(_app())
    r = c.patch("/api/ai/chat/threads/t-1", json={"title": "   "})
    assert r.status_code == 422
    spy.assert_not_called()


def test_rename_thread_too_long_title_422(mocker):
    """超长标题（>255）：pydantic max_length → 422。"""
    from chatbot.interfaces import routes
    spy = mocker.patch.object(routes.repo, "set_title")
    c = TestClient(_app())
    r = c.patch("/api/ai/chat/threads/t-1", json={"title": "x" * 256})
    assert r.status_code == 422
    spy.assert_not_called()


def test_delete_thread_ok(mocker):
    """DELETE /threads/{id}：owner 校验通过 → soft_delete_thread，返回 OK 信封。"""
    from chatbot.interfaces import routes
    mocker.patch.object(routes.repo, "get_thread",
                        return_value=SimpleNamespace(thread_id="t-1"))
    spy = mocker.patch.object(routes.repo, "soft_delete_thread")
    c = TestClient(_app())
    r = c.delete("/api/ai/chat/threads/t-1")
    assert r.status_code == 200
    assert r.json() == {"success": True, "code": 0, "message": "OK"}
    spy.assert_called_once_with(thread_id="t-1")


def test_delete_thread_not_owner_404(mocker):
    from chatbot.interfaces import routes
    mocker.patch.object(routes.repo, "get_thread", return_value=None)
    spy = mocker.patch.object(routes.repo, "soft_delete_thread")
    c = TestClient(_app())
    r = c.delete("/api/ai/chat/threads/t-1")
    assert r.status_code == 404
    spy.assert_not_called()
```

- [x] 2. 运行 `uv run pytest tests/chatbot/interfaces/test_routes.py -v`，确认 6 个新测试失败（PATCH/DELETE 返回 405）。
- [x] 3. 在 `source/chatbot/interfaces/vo.py` 末尾追加（确认文件顶部已 import `Field`，没有则补）：

```python
class ThreadRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255,
                       description="新标题（strip 后非空，最长 255 字符）")


class OkResponse(BaseModel):
    """无 data 的统一信封（与现有 {success, code, message, data} 同构）。"""
    success: bool
    code: int
    message: str
```

- [x] 4. 在 `source/chatbot/interfaces/routes.py` 末尾追加：

```python
@router.patch("/threads/{thread_id}", response_model=vo.OkResponse)
async def rename_thread(
    thread_id: str,
    request: vo.ThreadRenameRequest,
    ctx: AuthUser = Depends(get_current_user),
):
    # owner 校验：非本人/已删 thread 一律 404（沿用现有 IDOR 语义，不泄露存在性）。
    if repo.get_thread(thread_id=thread_id, user_id=ctx.user_id) is None:
        raise HTTPException(
            status_code=404, detail={"code": 40400, "message": "thread not found"})
    title = request.title.strip()
    if not title:
        # pydantic min_length 拦不住全空白串，strip 后再校验一次。
        raise HTTPException(
            status_code=422, detail={"code": 42200, "message": "title must not be blank"})
    repo.set_title(thread_id=thread_id, title=title)
    return vo.OkResponse(success=True, code=0, message="OK")


@router.delete("/threads/{thread_id}", response_model=vo.OkResponse)
async def delete_thread(
    thread_id: str,
    ctx: AuthUser = Depends(get_current_user),
):
    if repo.get_thread(thread_id=thread_id, user_id=ctx.user_id) is None:
        raise HTTPException(
            status_code=404, detail={"code": 40400, "message": "thread not found"})
    repo.soft_delete_thread(thread_id=thread_id)
    return vo.OkResponse(success=True, code=0, message="OK")
```

- [x] 5. 运行 `uv run pytest tests/chatbot/ -v`，确认全绿。

---

## Task 4：routes 发送分支改造（accessible_companies 注入 / 续聊换公司）

**Files:**
- Modify: `source/chatbot/interfaces/routes.py`（`send` 函数：续聊分支 + 新增 accessible 注入；**保留既有 `needs_title` 与 `stream_sse` 泵不动**）
- Test: `tests/chatbot/interfaces/test_routes.py`（末尾追加 4 个测试）

**Steps:**

- [x] 1. 在 `tests/chatbot/interfaces/test_routes.py` 末尾追加失败测试（管理端 = Redis `company_id` 为空；`_app(user)` 形态以该文件现状为准）：

```python
def _admin_user() -> AuthUser:
    """管理端（超管）：Redis 会话 company_id 为空。"""
    return AuthUser(user_id="u1", company_id=None, organization_id="o1", authorities=[])


def test_send_admin_injects_accessible_companies(mocker):
    """管理端发送：注入 accessible_companies 结果（恢复公司提及匹配与 company 工具上下文）。"""
    from chatbot.interfaces import routes
    from chatbot.application.chat_events import Done

    companies = [{"id": "c-1", "name": "Acme"}]

    async def _acc(**kw):
        return companies

    mocker.patch.object(routes, "accessible_companies", side_effect=_acc)
    mocker.patch.object(routes.repo, "create_thread", return_value="t-9")

    captured: dict = {}

    async def _turn(**kw):
        captured.update(kw)
        yield Done()

    mocker.patch.object(routes.chat_service, "stream_turn", _turn)
    c = TestClient(_app(_admin_user()))
    r = c.post("/api/ai/chat",
               json={"question": "q", "thread_id": None, "company_id": "c-1"})
    assert r.status_code == 200
    assert captured["accessible_company_list"] == companies


def test_send_company_end_skips_accessible_companies(mocker):
    """公司端：不调 accessible_companies（零开销），仍传 []。"""
    from chatbot.interfaces import routes
    from chatbot.application.chat_events import Done

    spy = mocker.patch.object(routes, "accessible_companies")
    mocker.patch.object(routes.repo, "create_thread", return_value="t-9")

    captured: dict = {}

    async def _turn(**kw):
        captured.update(kw)
        yield Done()

    mocker.patch.object(routes.chat_service, "stream_turn", _turn)
    c = TestClient(_app())   # 既有默认用户为公司端
    r = c.post("/api/ai/chat",
               json={"question": "q", "thread_id": None, "company_id": None})
    assert r.status_code == 200
    spy.assert_not_called()
    assert captured["accessible_company_list"] == []


def test_send_admin_resume_switches_active_company(mocker):
    """管理端续聊：前端所选公司 ≠ thread 当前 active → set_active_company。"""
    from chatbot.interfaces import routes
    from chatbot.application.chat_events import Done

    thread = SimpleNamespace(thread_id="t-1", active_company_id="c-1", title="t")
    mocker.patch.object(routes.repo, "get_thread", return_value=thread)
    spy = mocker.patch.object(routes.repo, "set_active_company")

    async def _acc(**kw):
        return []

    mocker.patch.object(routes, "accessible_companies", side_effect=_acc)

    async def _turn(**kw):
        yield Done()

    mocker.patch.object(routes.chat_service, "stream_turn", _turn)
    c = TestClient(_app(_admin_user()))
    r = c.post("/api/ai/chat",
               json={"question": "q", "thread_id": "t-1", "company_id": "c-2"})
    assert r.status_code == 200
    spy.assert_called_once_with(thread_id="t-1", company_id="c-2")


def test_send_admin_resume_same_company_no_switch(mocker):
    """管理端续聊：所选公司与 thread 当前 active 相同 → 不写库。"""
    from chatbot.interfaces import routes
    from chatbot.application.chat_events import Done

    thread = SimpleNamespace(thread_id="t-1", active_company_id="c-1", title="t")
    mocker.patch.object(routes.repo, "get_thread", return_value=thread)
    spy = mocker.patch.object(routes.repo, "set_active_company")

    async def _acc(**kw):
        return []

    mocker.patch.object(routes, "accessible_companies", side_effect=_acc)

    async def _turn(**kw):
        yield Done()

    mocker.patch.object(routes.chat_service, "stream_turn", _turn)
    c = TestClient(_app(_admin_user()))
    r = c.post("/api/ai/chat",
               json={"question": "q", "thread_id": "t-1", "company_id": "c-1"})
    assert r.status_code == 200
    spy.assert_not_called()
```

- [x] 2. 运行 `uv run pytest tests/chatbot/interfaces/test_routes.py -v`，确认 4 个新测试失败。
- [x] 3. 修改 `source/chatbot/interfaces/routes.py` 的 `send`（**基于当前磁盘版本做最小增量**，保留 `needs_title` / `stream_sse` 泵 / trace 包裹原样）：
      ① 续聊分支（`if request.thread_id:` 块内、`needs_title = row.title is None` 之后）追加：

```python
        # 管理端续聊换公司：前端所选 ≠ thread 当前 active 时落库更新（公司端忽略前端传值）。
        if (not is_company) and request.company_id \
                and request.company_id != row.active_company_id:
            repo.set_active_company(thread_id=thread_id, company_id=request.company_id)
```

      ② 在 `tid = uuid.uuid4().hex` 之前插入：

```python
    # 管理端：注入可访问公司列表（accessible_companies 自带 5 分钟/用户缓存），
    # 恢复 resolve_company 的公司提及匹配与 call_company 上下文；
    # 公司端锁本公司用不到，传 []（零开销）。
    accessible: list[dict] = []
    if not is_company:
        accessible = await accessible_companies(user=ctx, auth_token=auth_token)
```

      ③ `_events()` 内 `stream_turn(...)` 调用的 `accessible_company_list=[]` 改为 `accessible_company_list=accessible`。
- [x] 4. 运行 `uv run pytest tests/chatbot/ -v`，确认全绿（既有 send 测试为公司端用户，不触达 accessible_companies）。

---

## Task 5：全量回归与规范自查（无新代码）

**Steps:**

- [x] 1. 运行 `uv run pytest tests/chatbot/ -v` 全绿；再运行 `uv run pytest tests/` 确认未波及其他模块。
- [x] 2. 运行 `uv run ruff check source/chatbot/`，无新增违例。
- [x] 3. 按 `standards/` 自查：LLM 统一入口（llm_db_router）✓；interfaces 零业务逻辑、Request/Response 在 vo ✓；repository 仅单表 CRUD ✓；404 不泄露存在性 ✓。

---

## Spec 覆盖对照（已剔除另一会话完成项）

| spec 条目 | 状态 |
|---|---|
| §3 title 事件 + 序列化 | ✅ 另一会话已实现（TitleGenerated + llm to_sse），不在本计划 |
| §4.2 标题生成 / 部分落库 | ✅ 另一会话已实现（needs_title / finally 落库），不在本计划 |
| §4.1 get_recent_messages / soft_delete / deleted 过滤 | Task 1 |
| §4.2 历史注入 | Task 2 |
| §4.3 PATCH / DELETE + §4.4 vo | Task 3 |
| §4.3 accessible 注入 / 续聊换公司 | Task 4 |
| §7 后端测试清单 | Task 1–4 各自步骤 |
