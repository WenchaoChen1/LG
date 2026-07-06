# AI Chatbot 知识库问答 + 三智能体（standard/kb/combo）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 关联文档: [方案设计 spec](../specs/2026-07-05-chatbot-knowledge-base-qa-design.md)

**Goal:** chatbot 能基于知识库文档回答（进程内直调 RAG recall），并提供三个独立智能体：默认 standard（业务+KB 兜底）/ 纯知识库 kb / 组合 combo（dispatch 分诊，可双场景作答）。

**Architecture:** 三张图三个 build 函数并列在 `chatbot_graph/build.py`，共用 guardrail/init/ChatState/横切件；KB 检索是一个 `@tool`（`search_knowledge_base`），进程内调 `rag.search_service.recall`（加 `caller_type`/`empty_scope_ok` 参数 + service 层 to_thread 阻塞治理）；`sse_provider` 按 payload `agent_mode` 选图；前端聊天页加 3 档模式选择器。

**Tech Stack:** Python 3.12 / FastAPI / LangGraph / pydantic v2 / pgvector；前端 React16 + UmiJS3 + AntD v4 + TS。

---

## 执行须知（强制）

1. **串行执行**：用户明确要求"完成一个任务再做下一个"——任务间禁止并行/跳跃，每个任务完成后向用户简报再进入下一个。
2. **嵌套仓库**：`CIOaas-python/`、`CIOaas-web/` 是独立 git 仓库。提交发生在各自仓库内；提交前 `git branch --show-current` 确认分支（chatbot 工作分支惯例 `feature/ai-chatbot-v1`，并发会话可能切过分支）、**窄 `git add`（逐文件）**、提交消息英文。根仓库只提交 docs。
3. **提交确认**：根 CLAUDE.md 要求 git add/commit 前经用户确认。执行本计划时按"每任务一次提交、任务简报中列出待提交文件清单征得同意"节奏执行。
4. **测试策略**：根 CLAUDE.md 规定不自动跑测试；用户批准执行本计划即视为授权计划内 TDD 步骤的测试命令。Python 测试命令一律 `uv run pytest`（Windows，工作目录 `CIOaas-python/`）；前端用 `npx umi-test`（须先挂 node PATH，见 memory web-test-commands）。
5. **规范复查**：每个 Python 任务收尾按 `CIOaas-python/standards/`（architecture/coding）自查；前端任务按 `CIOaas-web/standards/`。
6. **行号是锚点不是坐标**：计划中的 `文件:行号` 以当前 HEAD 为准，执行时先 Read 目标区域再改，内容对不上以文件实际内容为准（找注释/函数名锚点）。

---

## 任务总览（9 个，串行）

| # | 任务 | 交付 | 仓库 |
|---|------|------|------|
| 1 | rag `recall` 增强（caller_type / empty_scope_ok / to_thread / 注解） | KB 工具的地基 | CIOaas-python |
| 2 | `KnowledgeSearchResult` DTO + `search_knowledge_base` 工具 | 工具可单测通过 | CIOaas-python |
| 3 | 注册 `TOOL_REGISTRY_V2` + 提示词 2 处 + 接口文档再生成 | **智能体 1（standard）完成** | CIOaas-python |
| 4 | kb 轨提示词 + `retrieve_kb_node` 节点 | 纯知识库子智能体核心 | CIOaas-python |
| 5 | `build_kb_graph()` + 三图编译改造 + payload `agent_mode` 透传 | **智能体 2（kb）完成** | CIOaas-python |
| 6 | `dispatch_node` 场景分诊 + 提示词 + CallerNode | combo 的分诊器 | CIOaas-python |
| 7 | `build_combo_graph()`（含 both 顺序双场景 + 段落头） | **智能体 3（combo）完成** | CIOaas-python |
| 8 | 前端：AgentModePicker + payload 穿透 + 按会话记忆 | 三智能体可选可用 | CIOaas-web |
| 9 | CLAUDE.md 文档同步 + 真实环境冒烟（spec §5 清单） | 收尾验收 | 三仓库 |

---

### Task 1: rag `recall` 增强（caller_type / empty_scope_ok / to_thread / 注解）

**Files:**
- Modify: `CIOaas-python/source/rag/application/service/search_service.py:165-219`（recall）、`:200-203`（圈定）、`:223-305`（_resolve_visibility 调用点）、`:332-344`（_store_for_granted 调用点）、`:348-392`（_enrich 调用点）
- Test: `CIOaas-python/tests/rag/application/test_recall_chatbot_params.py`（新；若 tests/rag/ 下已有 search_service 测试文件则将用例并入该文件）

- [ ] **Step 1: 写失败测试**

```python
"""recall 的 chatbot 适配参数：caller_type 透传 / empty_scope_ok 空间集为空不抛错。"""
import pytest

from rag.application.service.errors import RagBusinessError
from rag.application.service.search_service import SearchService


class _NoopBackground:
    def add_task(self, fn, *args, **kwargs):
        pass


@pytest.fixture
def svc(monkeypatch):
    service = SearchService()
    # 圈定结果可控：monkeypatch 掉"可见空间圈定"内部调用（以实际私有实现为准，
    # 若 recall 内联调用 SpaceRepository 则 patch SpaceRepository.list_visible_ids）
    return service


async def test_empty_scope_ok_returns_empty_result(svc, monkeypatch):
    monkeypatch.setattr(
        "rag.domain.repository.space_repository.SpaceRepository.list_visible_ids",
        lambda self, **kw: [])
    out = await svc.recall(
        mode="standard", query="报销", top_k=None, company_id="c1", user_id="u1",
        background=_NoopBackground(), empty_scope_ok=True)
    assert out.hits == [] and out.granted_space_ids == []


async def test_empty_scope_default_still_raises(svc, monkeypatch):
    monkeypatch.setattr(
        "rag.domain.repository.space_repository.SpaceRepository.list_visible_ids",
        lambda self, **kw: [])
    with pytest.raises(RagBusinessError):
        await svc.recall(
            mode="standard", query="报销", top_k=None, company_id="c1", user_id="u1",
            background=_NoopBackground())


async def test_caller_type_passthrough(svc, monkeypatch):
    monkeypatch.setattr(
        "rag.domain.repository.space_repository.SpaceRepository.list_visible_ids",
        lambda self, **kw: ["s1"])
    captured = {}

    async def _fake_search(self, dto, background):
        captured["caller_type"] = dto.caller_type
        from rag.application.dto.search_dto import SearchResultDTO
        return SearchResultDTO(hits=[], granted_space_ids=["s1"], dropped_space_ids=[], duration_ms=1)

    monkeypatch.setattr(SearchService, "search", _fake_search)
    await svc.recall(
        mode="standard", query="q", top_k=None, company_id="c1", user_id="u1",
        background=_NoopBackground(), caller_type="CHATBOT")
    assert captured["caller_type"] == "CHATBOT"
```

> 写前先 Read `search_service.py:165-219` 与 `search` 的实际签名（`search(dto, background)` 的参数形态、`SearchDTO` 构造字段），fixture/fake 与实际形态对齐；`SearchResultDTO` 构造字段名以 `rag/application/dto/search_dto.py:44-50` 为准。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/rag/application/test_recall_chatbot_params.py -v`
Expected: FAIL（`recall() got an unexpected keyword argument 'empty_scope_ok'`）

- [ ] **Step 3: 实现 recall 增强**

`search_service.py` 四处改动：

(a) 签名（:165-176）——加两个可选参 + 注解按真实用法修正：

```python
async def recall(
    self,
    *,
    mode: str,
    query: str,
    top_k: Optional[int],
    company_id: Optional[str],   # 超管为 None（HTTP 路由本就透传可空 ctx.company_id）
    user_id: str,
    background: Any,             # 鸭子类型：只调 .add_task（processor 侧本就是 Any）
    space_ids: Optional[list[str]] = None,
    file_id: Optional[str] = None,
    caller_type: str = "USER",       # 检索日志来源标识：USER | CHATBOT
    empty_scope_ok: bool = False,    # True：可见空间为空返回空结果而非抛 invalid_param
) -> SearchResultDTO:
```

(b) 圈定块（:200-203）同步查询下线程 + 空集分流（:208-210）：

```python
        def _visible() -> list[str]:
            with get_session() as session:
                return SpaceRepository(session).list_visible_ids(
                    company_id=company_id, user_id=user_id, process_type=process_type)

        visible = await asyncio.to_thread(_visible)
        ...
        if not scoped:
            if empty_scope_ok:
                return SearchResultDTO(
                    hits=[], granted_space_ids=[], dropped_space_ids=[], duration_ms=0)
            raise errors.invalid_param(f"当前无 {process_type} 类型的可召回空间")
```

（保留原有 space_ids 交集逻辑不动，只把"查询"部分提为 `_visible` 局部函数下线程；`import asyncio` 加到文件头。）

(c) `caller_type` 透传：`:215` 处 `SearchDTO(..., caller_type="USER")` 改为 `caller_type=caller_type`。

(d) 阻塞治理——`search` 管线内三处同步查询调用点包 `asyncio.to_thread`：
`_resolve_visibility`（:257-272 被 search 调用处）、`_store_for_granted`（:338-341 调用处）、`_enrich`（:358-360 调用处）。**按各方法实际形态选包装点**：方法本身是同步 `def` → 调用处改 `await asyncio.to_thread(self._方法, ...)`；方法是 `async def` 但内部整段 `with get_session()` 同步块 → 把同步块提为局部 `def` 后 `await asyncio.to_thread(局部fn)`（与 (b) 同款手法）。不改任何查询语义，不做 N 次 get_by_id 的合并优化（spec §7 明确不做）。

- [ ] **Step 4: 跑测试确认通过 + rag 存量测试回归**

Run: `uv run pytest tests/rag/ -v`
Expected: 新 3 条 PASS，存量全绿（`recall` 新参数均有默认值，HTTP 路由零改动向后兼容）。

- [ ] **Step 5: 提交（CIOaas-python 仓库，先确认分支与用户同意）**

```bash
git add source/rag/application/service/search_service.py tests/rag/application/test_recall_chatbot_params.py
git commit -m "feat(rag): recall supports caller_type/empty_scope_ok and offloads sync queries to threads"
```

---

### Task 2: `KnowledgeSearchResult` DTO + `search_knowledge_base` 工具

**Files:**
- Create: `CIOaas-python/source/ai/tools/dto/knowledge_result.py`
- Create: `CIOaas-python/source/ai/tools/knowledge_base_tool.py`
- Test: `CIOaas-python/tests/ai/tools_v2/test_knowledge_base_tool.py`

- [ ] **Step 1: 写 DTO**（snake_case 无 alias，对齐 `dto/company_result.py` 头注释约定；**不写** `from __future__ import annotations`；不加入 `dto/__init__.py` 导出）

```python
"""知识库检索工具（search_knowledge_base）返回契约。字段全 snake_case、无 alias。"""
from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeHit(BaseModel):
    content: str = Field(description="文档片段正文")
    similarity: float = Field(description="相似度 [0,1]")
    match_type: str = Field(description="匹配类型：SEMANTIC | KEYWORD | BOTH")
    source_title: str = Field(description="来源文件标题（作答引用出处）")
    space_name: str = Field(description="所属知识库空间名")


class KnowledgeSearchResult(BaseModel):
    ok: bool = Field(description="成败")
    message: Optional[str] = Field(None, description="失败原因（ok=false 时）")
    note: Optional[str] = Field(None, description="无空间/无命中等非错误提示")
    hits: Optional[list[KnowledgeHit]] = Field(None, description="召回片段（ok=true 时显式给出，空命中为 []）")
```

- [ ] **Step 2: 写失败测试**

先 Read `tests/ai/tools_v2/test_financials_tool_v2.py` 前 60 行，照它的工具调用方式（直接 await 底层 coroutine 并以 SimpleNamespace 冒充 runtime，或其既有 helper）写；用例集：

```python
"""search_knowledge_base 工具单测：mock rag search_service，验证参数映射与错误二分。"""
from types import SimpleNamespace

import pytest

from ai.tools._support.request_context import ReqCtx
from ai.tools.knowledge_base_tool import search_knowledge_base_tool


def _runtime(company_id="c1", user_id="u1"):
    return SimpleNamespace(context=ReqCtx(
        auth_token="t", user_id=user_id, home_company_id=company_id, end_type="company"))


class _FakeService:
    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.calls = result, exc, []

    async def recall(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return self.result


def _hit(content="正文", title="差旅报销办法.pdf", space="公司制度"):
    return SimpleNamespace(content=content, similarity=0.87, match_type="SEMANTIC",
                           entry_title=title, space_name=space)


def _result(hits, granted=("s1",)):
    return SimpleNamespace(hits=list(hits), granted_space_ids=list(granted),
                           dropped_space_ids=[], duration_ms=5)


async def test_happy_path_maps_hits_and_params(monkeypatch):
    svc = _FakeService(result=_result([_hit()]))
    monkeypatch.setattr("rag.application.service.search_service.get_search_service", lambda: svc)
    import json
    out = json.loads(await search_knowledge_base_tool.coroutine(query="报销 制度", runtime=_runtime()))
    assert out["ok"] is True
    assert out["hits"][0]["source_title"] == "差旅报销办法.pdf"
    kw = svc.calls[0]
    assert kw["mode"] == "standard" and kw["caller_type"] == "CHATBOT"
    assert kw["empty_scope_ok"] is True and kw["space_ids"] is None
    assert kw["company_id"] == "c1" and kw["user_id"] == "u1"


async def test_no_spaces_returns_note(monkeypatch):
    svc = _FakeService(result=_result([], granted=()))
    monkeypatch.setattr("rag.application.service.search_service.get_search_service", lambda: svc)
    import json
    out = json.loads(await search_knowledge_base_tool.coroutine(query="q", runtime=_runtime()))
    assert out["ok"] is True and out["hits"] == [] and "note" in out


async def test_rag_error_degrades_to_ok_false(monkeypatch):
    from rag.application.service.errors import RagBusinessError
    svc = _FakeService(exc=RagBusinessError(http_status=503, code=50301, message="down"))
    monkeypatch.setattr("rag.application.service.search_service.get_search_service", lambda: svc)
    import json
    out = json.loads(await search_knowledge_base_tool.coroutine(query="q", runtime=_runtime()))
    assert out["ok"] is False and "unavailable" in out["message"]
```

> `RagBusinessError` 构造参数以 `rag/application/service/errors.py` 实际签名为准；`ReqCtx` 未列字段用默认值即可（dataclass 全默认）。若 `@tool` 对象无 `.coroutine` 属性，用邻文件既有调用手法替换（保持断言不变）。

- [ ] **Step 3: 跑测试确认失败**

Run: `uv run pytest tests/ai/tools_v2/test_knowledge_base_tool.py -v`
Expected: FAIL（`ModuleNotFoundError: ai.tools.knowledge_base_tool`）

- [ ] **Step 4: 写工具实现**

`source/ai/tools/knowledge_base_tool.py`（**头部 import 照抄 `companies_tool.py` 的 `tool`/`ToolRuntime` 来源路径**；禁 `from __future__ import annotations`）：

```python
"""知识库检索工具：进程内直调 rag search_service.recall（STANDARD 文档空间）。

space 范围不进 LLM schema——按 ReqCtx 身份（home_company_id + user_id）由 rag 侧
圈定全部可见空间（V1 占位 space_ids=None，spec §4）。rag 模块经 application/service
进程内调用（ai/CLAUDE.md"工具经 Java 网关"约定的登记例外，见 spec §6）。
"""
import asyncio
import functools
import logging
from typing import Optional

from ai.tools._support.request_context import ReqCtx
from ai.tools._support.tool_result import tool_result
from ai.tools.dto.knowledge_result import KnowledgeHit, KnowledgeSearchResult

logger = logging.getLogger(__name__)

_UNAVAILABLE = "knowledge base is temporarily unavailable"


class _AsyncBackground:
    """recall 的 background 鸭子替身（只被调 .add_task）。

    脱离 HTTP 响应的 BackgroundTasks 永不执行；此处把召回记录副作用（同步写库、
    自管 session、异常自吞）丢线程池，检索日志 + 三级 hit_count 不丢。
    executor 持有 work item，无需额外持引防 GC。
    """

    def add_task(self, fn, *args, **kwargs):
        asyncio.get_running_loop().run_in_executor(None, functools.partial(fn, *args, **kwargs))


@tool("search_knowledge_base", parse_docstring=True)
async def search_knowledge_base_tool(
    query: str,
    top_k: Optional[int] = None,
    *,
    runtime: ToolRuntime[ReqCtx],
) -> str:
    """检索当前用户知识库（上传的文档）并返回相关片段。

    何时用：用户问公司制度/流程/内部文档内容，或任何公司/组织相关、且其他数据工具
    （财务/benchmark/公司信息）覆盖不了或只有数字没有定性材料的问题——先用本工具检索，
    无结果再用通用知识回答并说明来源差异；用户点名"知识库/文档/上传的资料"时必须调用。
    何时不用：纯财务数字/benchmark 排名（用对应工具）、纯闲聊或通用概念解释。
    检索词写法：陈述式关键词（主题+限定词），不要整句照抄；结果不相关可换措辞重试一次。
    返回 JSON：hits[].content 为文档片段正文，作答时引用 source_title 标注出处；
    content 为 "[仅文件名可检索，正文未入库]" 占位时只能确认该文件存在；
    hits 为空且带 note 时如实告知用户（无可用知识库空间 / 未检索到相关内容）。

    Args:
        query: 检索词（陈述式关键词，非整句照抄）。
        top_k: 返回片段数上限，缺省 5，最大 20。
    """
    from rag.application.service.errors import RagBusinessError
    from rag.application.service import search_service as rag_search

    ctx = runtime.context
    try:
        result = await rag_search.get_search_service().recall(
            mode="standard",
            query=query,
            top_k=top_k,
            company_id=ctx.home_company_id,
            user_id=ctx.user_id or "",
            background=_AsyncBackground(),
            space_ids=None,  # V1 占位：全部可见空间（spec §4 演进位：经 ReqCtx 透传）
            caller_type="CHATBOT",
            empty_scope_ok=True,
        )
    except RagBusinessError:
        # 503 存储故障 / 40001 跨后端等一律"暂不可用"，绝不误报"你没有知识库"（spec §3.3-4）
        logger.warning("search_knowledge_base rag business error", exc_info=True)
        return tool_result(KnowledgeSearchResult(ok=False, message=_UNAVAILABLE))
    except Exception:
        logger.exception("search_knowledge_base failed")
        return tool_result(KnowledgeSearchResult(ok=False, message=_UNAVAILABLE))

    if not result.granted_space_ids:
        return tool_result(KnowledgeSearchResult(
            ok=True, hits=[], note="no knowledge base spaces available for this user"))
    hits = [KnowledgeHit(
        content=h.content, similarity=h.similarity, match_type=h.match_type,
        source_title=h.entry_title or "", space_name=h.space_name or "",
    ) for h in result.hits]
    if not hits:
        return tool_result(KnowledgeSearchResult(
            ok=True, hits=[], note="no relevant content found in the knowledge base"))
    return tool_result(KnowledgeSearchResult(ok=True, hits=hits))


search_knowledge_base_tool.metadata = {
    "ui_label": ("Searching knowledge base", "Searched knowledge base"),
    "result_model": KnowledgeSearchResult,
}
```

注意：rag import 放函数体内（延迟导入，避免 ai.tools 包加载即拉起 rag 全链）；monkeypatch 路径 `rag.application.service.search_service.get_search_service` 正因此生效。

- [ ] **Step 5: 跑测试确认通过 + schema 探针**

Run: `uv run pytest tests/ai/tools_v2/test_knowledge_base_tool.py -v`
Expected: 3 条 PASS。
再快验 schema（`runtime` 不得出现在参数里）：

```bash
uv run python -c "import sys; sys.path.insert(0,'source'); from ai.tools.knowledge_base_tool import search_knowledge_base_tool as t; s=t.tool_call_schema.model_json_schema(); print(sorted(s['properties'])); assert 'runtime' not in s['properties']"
```
Expected: `['query', 'top_k']`

- [ ] **Step 6: 提交**

```bash
git add source/ai/tools/knowledge_base_tool.py source/ai/tools/dto/knowledge_result.py tests/ai/tools_v2/test_knowledge_base_tool.py
git commit -m "feat(chatbot): add search_knowledge_base tool calling rag recall in-process"
```

---

### Task 3: 注册工具 + 提示词 2 处 + 接口文档（→ 智能体 1 完成）

**Files:**
- Modify: `CIOaas-python/source/ai/agent/chatbot_graph/tools.py`（:9 头注释、:19-25 import、:28-35 列表、:37-47 `__all__`）
- Modify: `CIOaas-python/source/ai/prompts/chatbot/retrieval_agent_prompt.py`（:21 职责①、:24-25 条款④）
- Regenerate: `docs/AI-Chatbot/chatbot-tools-v2-interface.md`

- [ ] **Step 1: 注册（唯一代码接线点）**

`tools.py`：import 段加 `from ai.tools.knowledge_base_tool import search_knowledge_base_tool`；`TOOL_REGISTRY_V2` 数据工具区段（`get_benchmark_data_tool` 之后、`get_current_user_tool` 之前）插入：

```python
    search_knowledge_base_tool,  # ai/tools/knowledge_base_tool.py（知识库文档检索，进程内调 rag recall）
```

`__all__` 加 `"search_knowledge_base_tool"`；模块头注释"6 个 @tool"改"7 个 @tool"并在清单中补一行。

- [ ] **Step 2: 提示词 2 处（先 Read :16-45 原文再改）**

(a) :21 职责边界①核心能力枚举（财务 / benchmark / Normalization Tracing / 公司信息）追加"知识库文档问答"；
(b) :24-25 条款④原文"回答不了公司相关问题时可用通用业务知识补充"改写为：

```
④ 公司/组织相关但业务数据工具覆盖不了（或只有数字没有定性材料）的问题：先检索知识库
（search_knowledge_base），有结果基于文档作答并注明来源，无结果再用通用业务知识补充并
说明这不是来自该公司的资料。
```

（措辞融入原条款语气；version 注释号 +1。）

- [ ] **Step 3: 跑注册表契约测试 + chatbot 图存量测试**

Run: `uv run pytest tests/ai/tools_v2/ tests/ai/chatbotgraph/ -v`
Expected: 全绿（`test_interface_doc_v2.py` 的注册表契约测试自动覆盖新工具的 ui_label/result_model/runtime 探针；若有"工具数量=6"类断言，按测试文件本意更新为 7）。

- [ ] **Step 4: 重新生成接口文档**

先 Read `source/ai/tools/interface_doc.py` 找生成入口（`generate_all_docs` 或同名函数）并按其现有调用方式执行，确认 `docs/AI-Chatbot/chatbot-tools-v2-interface.md` 新增 search_knowledge_base 段。

- [ ] **Step 5: 提交**

```bash
git add source/ai/agent/chatbot_graph/tools.py source/ai/prompts/chatbot/retrieval_agent_prompt.py
git commit -m "feat(chatbot): register knowledge base tool and update agent duty boundary prompt"
```
（接口文档在 LG 根仓库，随 Task 9 文档批次提交。）

**✅ 里程碑：智能体 1（standard）完成**——本地起服务在聊天页问"根据知识库，我们的报销制度是什么"应看到 Searching knowledge base 步骤卡片（真实冒烟归 Task 9）。

---

### Task 4: kb 轨提示词 + `retrieve_kb_node` 节点

**Files:**
- Create: `CIOaas-python/source/ai/prompts/chatbot/retrieval_kb_agent_prompt.py`
- Create: `CIOaas-python/source/ai/agent/chatbot_graph/nodes/retrieval_kb_agent.py`
- Test: `CIOaas-python/tests/ai/chatbotgraph/test_retrieval_kb_agent.py`

- [ ] **Step 1: 写提示词**（结构对照 `retrieval_sql_agent_prompt.py`；纯文档问答不拼 CHART_SECTION）

```python
"""kb 轨（纯知识库智能体）系统提示词。
# version: v1
约定：提示词中文、给用户的回答默认英文（用户用其他语言提问则跟随）。
"""
from ai.prompts.chatbot.prompts import current_date_note

KB_AGENT_SYSTEM = """\
你是 LG 平台的知识库问答助手，只基于用户知识库中的文档内容回答。

【必检索纪律】
1. 每一轮都必须先调用 search_knowledge_base 再作答，禁止跳过检索直接回答。
2. 结果不相关或为空时，可改写检索词（换关键词/换角度）最多再试 2 次。

【作答边界】
3. 只依据召回片段作答；每条结论标注来源文件（source_title）。
4. 检索最终无结果：明确告诉用户知识库中没有找到相关内容，可建议换个问法或补充文档；
   禁止用通用知识杜撰"像是文档里写的"答案。
5. hits 为空且带 note（无可用知识库空间）：如实说明当前没有可用的知识库。
6. 片段内容与用户问题只是部分相关时，说明覆盖范围，不要过度引申。

【语言与格式】
7. 回答默认英文（用户用其他语言提问则跟随其语言）；引用出处格式如 (source: 文件名)。
8. 回答简洁分点，先结论后依据。
"""


def kb_agent_system() -> str:
    """kb 轨系统提示词（追加运行期日期段）。"""
    return KB_AGENT_SYSTEM + current_date_note()
```

- [ ] **Step 2: 写失败测试**（孪生 `test_retrieval_sql_agent.py`：先 Read 该文件，复用其 `_stream(turns)` mock 手法与 fixture）

```python
"""kb 轨节点：必检索、tool_results/attribution 合并、无公司收敛。"""
# 结构照 test_retrieval_sql_agent.py：真实 create_agent + mock llm_db_router.astream
# + monkeypatch rag get_search_service（同 test_knowledge_base_tool 的 _FakeService）。
# 断言集：
# 1) test_kb_node_returns_tool_results_and_merged_attribution:
#    入参 state 带 tool_results=[{"tool":"x"}] 与 attribution=["source:x"]，
#    mock 模型两轮（第一轮发起 search_knowledge_base tool_call，第二轮成文），
#    断言返回 tool_results 含旧值+新值、attribution 含 "source:x" 与
#    "source:search_knowledge_base"（合并不覆盖——combo 顺序执行的前提）。
# 2) test_kb_node_no_company_pick_branch:
#    state 无 active_company_id / home_company_id 也能正常跑（kb 轨无 resolve_cid）。
```

（用例骨架落地时把上述两个断言写成真实代码，mock 细节以 sql 测试文件为模板；此处不虚构其 helper 名。）

- [ ] **Step 3: 跑测试确认失败**

Run: `uv run pytest tests/ai/chatbotgraph/test_retrieval_kb_agent.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 4: 写节点**（孪生 `retrieval_sql_agent.py:23-109` 骨架；先整读该文件）

```python
"""kb 轨：纯知识库子智能体节点（kb 图主体 / combo 图 both 场景第一段）。

孪生自 retrieval_sql_agent：去掉公司收敛（KB 工具不吃公司参数，范围由 ReqCtx 身份
在 rag 侧圈定）；attribution 合并 state 原值（combo 顺序执行两段不互相覆盖）。
"""
import logging

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from ai.agent.chatbot_graph.nodes.retrieval_agent import (
    _AnswerEchoFilter, _StepCardMiddleware, _history_messages, _resolve_allowed)
from ai.agent.chatbot_graph.stream_channel import StreamMode
from ai.agent.chatbot_graph.stream_emit import StreamEmitter
from ai.prompts.chatbot.retrieval_kb_agent_prompt import kb_agent_system
from ai.tools._support.request_context import ReqCtx
from ai.tools.knowledge_base_tool import search_knowledge_base_tool
from llm.application.router.context import TraceContext
from llm.infrastructure.langchain import create_agent

logger = logging.getLogger(__name__)

_MAX_ITERS = 4  # 必检索 1 次 + 改写重试至多 2 次 + 成文
_RECURSION_LIMIT = 2 * _MAX_ITERS + 1


async def retrieve_kb_node(state: dict) -> dict:
    ctx = ReqCtx(
        auth_token=state.get("auth_token") or "",
        allowed=_resolve_allowed(state),
        accessible=state.get("accessible_company_list") or [],
        user_id=state.get("user_id"),
        home_company_id=state.get("home_company_id"),
        end_type=state.get("end_type"),
        current_user=state.get("current_user"),
    )
    emit = StreamEmitter()  # 必须在图节点上下文内构造
    mw = _StepCardMiddleware(emit)
    agent = create_agent(
        temperature=0.3,
        trace=TraceContext(agent="chat", node="retrieve_kb", user_id=ctx.user_id),
        tools=[search_knowledge_base_tool],
        system_prompt=kb_agent_system(),
        middleware=[mw],
        context_schema=ReqCtx,
    )
    messages = _history_messages(state) + [HumanMessage(content=state.get("question") or "")]
    dedup = _AnswerEchoFilter()
    try:
        async for _meta, chunk in agent.astream(
                {"messages": messages}, stream_mode=StreamMode.MESSAGES,
                context=ctx, config={"recursion_limit": _RECURSION_LIMIT}):
            # 帧处理循环与 retrieval_sql_agent.py:91-99 完全同款（调工具轮不外推正文、
            # 回声去重后 emit.answer_delta）——落地时照抄该段
            ...
    except GraphRecursionError:
        logger.warning("retrieve_kb hit recursion limit, finishing with gathered results")
    return {
        "tool_results": (state.get("tool_results") or []) + mw.results,
        "attribution": (state.get("attribution") or [])
        + [f"source:{t['tool']}" for t in mw.results],
    }
```

> `ReqCtx` 构造字段名/astream 帧循环/import 路径以 `retrieval_sql_agent.py` 实文为准逐行对照（尤其 `id_to_name` 是否必传——sql 轨传了就跟着传）。`...` 处必须替换为 sql 轨 :91-99 的真实循环体。

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/ai/chatbotgraph/test_retrieval_kb_agent.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add source/ai/prompts/chatbot/retrieval_kb_agent_prompt.py source/ai/agent/chatbot_graph/nodes/retrieval_kb_agent.py tests/ai/chatbotgraph/test_retrieval_kb_agent.py
git commit -m "feat(chatbot): add pure knowledge-base retrieval agent node and prompt"
```

---

### Task 5: `build_kb_graph()` + 多图编译 + payload `agent_mode` 透传（→ 智能体 2 完成）

**Files:**
- Modify: `CIOaas-python/source/ai/agent/chatbot_graph/build.py`（新增 build_kb_graph；`build_chat_graph` 不动）
- Modify: `CIOaas-python/source/main.py`（:88-94 访问器、:156-157 编译处）
- Modify: `CIOaas-python/source/chatbot/application/sse_provider.py`（:61-73 payload、:110-112 factory、:144-163 _traced_turn、:220-238/:248-250 stream_turn）
- Test: `CIOaas-python/tests/ai/chatbotgraph/test_chat_graph.py`（补 kb 图拓扑）、`tests/chatbot/interfaces/test_sse_provider.py` + `tests/chatbot/application/test_chat_turn.py`（透传断言）

- [ ] **Step 1: 写失败测试**

test_chat_graph.py 补（节点名与现有拓扑断言写法对齐，先 Read :40-51）：

```python
def test_kb_graph_topology():
    from ai.agent.chatbot_graph.build import build_kb_graph
    g = build_kb_graph().compile()
    names = set(g.get_graph().nodes)
    assert {"input_guard", "init", "retrieve_kb"} <= names
    assert "retrieve_tool" not in names and "retrieve_sql" not in names
```

test_chat_turn.py 补（用其 `_fake_graph.captured` 现成机制，先 Read :30-60）：

```python
# stream_turn(..., agent_mode="kb") 时：断言选图函数收到 "kb"
# （mock main.get_chat_graph_app 捕获入参），且非法值 "xxx" 归一为 "standard"。
```

test_sse_provider.py 补：payload 带 `"agent_mode": "kb"` 时工厂把它传给 stream_turn（mock stream_turn 捕 kwargs）；payload 不带时 kwargs 为 "standard" 或 None（与实现一致即可）。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/ai/chatbotgraph/test_chat_graph.py tests/chatbot -v`
Expected: 新用例 FAIL（build_kb_graph 不存在 / unexpected kwarg）

- [ ] **Step 3: build.py 加 `build_kb_graph()`**（guard/init 两行 add_node/add_edge **照 build_chat_graph() 内现有行照抄**，函数名以实文为准）

```python
def build_kb_graph() -> StateGraph:
    """纯知识库智能体（agent_mode='kb'）：guardrail → init → retrieve_kb → END。"""
    g = StateGraph(ChatState)
    g.add_node("input_guard", _traced_node("input_guard", <照抄现有 guard 节点函数>))
    g.add_node("init", _traced_node("init", <照抄现有 init 节点函数>))
    g.add_node("retrieve_kb", _traced_node("retrieve_kb", retrieve_kb_node))
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", _route_after_guard, {"block": END, "ok": "init"})
    g.add_edge("init", "retrieve_kb")
    g.add_edge("retrieve_kb", END)
    return g
```

顶部 import `retrieve_kb_node`；`<照抄...>` 两处在落地时替换为 build_chat_graph 里同名 add_node 行的真实函数引用。

- [ ] **Step 4: main.py 多图编译 + 带参访问器**（保持现有单例/懒加载风格，先 Read :88-94 与 :156-157）

```python
# lifespan 编译处（原 build_chat_graph().compile() 单值改 dict）：
_chat_graph_apps = {
    "standard": build_chat_graph().compile(),
    "kb": build_kb_graph().compile(),
}

# 访问器（保持旧调用 get_chat_graph_app() 语义不变）：
def get_chat_graph_app(mode: str = "standard"):
    apps = _chat_graph_apps
    return apps.get(mode) or apps["standard"]
```

- [ ] **Step 5: sse_provider 四处透传**

(a) `ChatStreamPayload`（:61-73）加：

```python
    agent_mode: Optional[str] = Field(
        None, description="智能体模式：standard(缺省)/kb/combo；非法值归一 standard")
```

(b) `chat_stream_factory`（:110-112）`_traced_turn(...)` 调用加 `agent_mode=payload.agent_mode`；
(c) `_traced_turn`（:144-163）签名与 `stream_turn(...)` 调用各加 `agent_mode`；
(d) `stream_turn`（:220-238）签名加 `agent_mode: Optional[str] = None`，函数体开头归一 + :248 选图：

```python
    mode = agent_mode if agent_mode in ("kb", "combo") else "standard"
    ...
    app = get_chat_graph_app(mode)   # 原 get_chat_graph_app()
```

（`agent_mode` 不进图 state——图身份即行为，`ChatState`/`init_node`/`financial_mode` 零改动。）

- [ ] **Step 6: 跑测试确认通过 + 存量回归**

Run: `uv run pytest tests/ai/chatbotgraph/ tests/chatbot/ tests/sse/ -v`
Expected: 全绿（payload 新字段可选，旧前端不发不影响；combo 值此时归一后仍会取到 dict 缺省 standard——`apps.get("combo") or apps["standard"]` 兜底，Task 7 前 combo 请求走 standard 不炸）。

- [ ] **Step 7: 提交**

```bash
git add source/ai/agent/chatbot_graph/build.py source/main.py source/chatbot/application/sse_provider.py tests/ai/chatbotgraph/test_chat_graph.py tests/chatbot/interfaces/test_sse_provider.py tests/chatbot/application/test_chat_turn.py
git commit -m "feat(chatbot): add kb agent graph and agent_mode payload routing"
```

**✅ 里程碑：智能体 2（kb）完成**——curl 直发 `POST /api/ai/sse/stream`、payload 带 `"agent_mode":"kb"` 可验（真实冒烟归 Task 9）。

---

### Task 6: `dispatch_node` 场景分诊 + 提示词 + CallerNode

**Files:**
- Create: `CIOaas-python/source/ai/prompts/chatbot/dispatch_prompt.py`
- Create: `CIOaas-python/source/ai/agent/chatbot_graph/nodes/dispatch_node.py`
- Modify: `CIOaas-python/source/ai/agent/chatbot_graph/state.py`（加 combo_scenario 键）
- Modify: `CIOaas-python/source/ai/enums/caller_node.py`（加 DISPATCH）
- Test: `CIOaas-python/tests/ai/chatbotgraph/test_dispatch_node.py`

- [ ] **Step 1: 写提示词**

```python
"""combo 图 dispatch 场景分诊提示词。
# version: v1
"""

DISPATCH_SYSTEM = """\
你是场景分诊器。判断用户问题需要哪类信息源作答：
- business：公司业务数据（财务指标 / benchmark / 公司信息 / 用户信息）
- kb：知识库文档（制度 / 流程 / 上传资料 / 定性内容）
- both：两者都需要，或无法确定

只输出一个词：business 或 kb 或 both。不要输出任何其他内容。
"""
```

- [ ] **Step 2: 写失败测试**

```python
"""dispatch 节点：三分支解析 + 失败降级 both。"""
import pytest

from ai.agent.chatbot_graph.nodes.dispatch_node import dispatch_node


@pytest.mark.parametrize("reply,expected", [
    ("business", "business"), ("kb", "kb"), ("both", "both"),
    (" Both ", "both"), ("kb\n", "kb"), ("unrelated words", "both"),
])
async def test_dispatch_parses_reply(monkeypatch, reply, expected):
    async def _fake_acomplete(*a, **kw):
        return reply
    # patch 点以 dispatch_node 实际调用的 llm_db_router 入口为准（照 guardrail_node 的用法）
    monkeypatch.setattr("ai.agent.chatbot_graph.nodes.dispatch_node._acomplete", _fake_acomplete)
    out = await dispatch_node({"question": "q", "user_id": "u1"})
    assert out["combo_scenario"] == expected


async def test_dispatch_llm_failure_falls_back_to_both(monkeypatch):
    async def _boom(*a, **kw):
        raise RuntimeError("llm down")
    monkeypatch.setattr("ai.agent.chatbot_graph.nodes.dispatch_node._acomplete", _boom)
    out = await dispatch_node({"question": "q", "user_id": "u1"})
    assert out["combo_scenario"] == "both"
```

- [ ] **Step 3: 跑测试确认失败**

Run: `uv run pytest tests/ai/chatbotgraph/test_dispatch_node.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 4: 写节点**（LLM 调用方式**照抄 `guardrail_node.py` 对 `llm_db_router.acomplete` 的真实用法**——先 Read :60-90；把调用包成模块级 `_acomplete` 便于测试 patch）

```python
"""combo 图场景分诊节点：business / kb / both（失败降级 both，宁全勿漏）。"""
import logging

from ai.prompts.chatbot.dispatch_prompt import DISPATCH_SYSTEM

logger = logging.getLogger(__name__)

_VALID = ("business", "kb", "both")


async def _acomplete(question: str, user_id) -> str:
    # 照 guardrail_node 的 llm_db_router.acomplete 调用形态实现：
    # system=DISPATCH_SYSTEM、user=question、TraceContext(agent="chat", node="dispatch",
    # user_id=user_id)、轻量模型档位与 guardrail 同款。
    ...


async def dispatch_node(state: dict) -> dict:
    question = state.get("question") or ""
    try:
        raw = (await _acomplete(question, state.get("user_id")) or "").strip().lower()
        scenario = raw if raw in _VALID else "both"
    except Exception:
        logger.warning("dispatch classification failed, fallback to both", exc_info=True)
        scenario = "both"
    return {"combo_scenario": scenario}
```

`state.py` 加键（注释同款风格）：

```python
    combo_scenario: str  # combo 图 dispatch 分诊结果：business | kb | both（其余图不写）
```

`ai/enums/caller_node.py`：按既有成员格式加 `DISPATCH = "dispatch"`。
`_acomplete` 的 `...` 落地时替换为 guardrail 同款真实调用（模型档位/参数照抄）。

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/ai/chatbotgraph/test_dispatch_node.py -v`
Expected: 7 条 PASS

- [ ] **Step 6: 提交**

```bash
git add source/ai/prompts/chatbot/dispatch_prompt.py source/ai/agent/chatbot_graph/nodes/dispatch_node.py source/ai/agent/chatbot_graph/state.py source/ai/enums/caller_node.py tests/ai/chatbotgraph/test_dispatch_node.py
git commit -m "feat(chatbot): add combo dispatch node classifying business/kb/both scenarios"
```

---

### Task 7: `build_combo_graph()`（→ 智能体 3 完成，后端全量）

**Files:**
- Modify: `CIOaas-python/source/ai/agent/chatbot_graph/build.py`（combo 图 + 包装节点 + 路由）
- Modify: `CIOaas-python/source/main.py`（编译 dict 加 combo 行）
- Test: `CIOaas-python/tests/ai/chatbotgraph/test_chat_graph.py`（combo 拓扑与路由）

- [ ] **Step 1: 写失败测试**

```python
def test_combo_graph_topology():
    from ai.agent.chatbot_graph.build import build_combo_graph
    g = build_combo_graph().compile()
    names = set(g.get_graph().nodes)
    assert {"input_guard", "init", "dispatch",
            "retrieve_kb", "retrieve_tool", "combo_kb", "combo_tool"} <= names


def test_route_after_dispatch():
    from ai.agent.chatbot_graph.build import _route_after_dispatch
    assert _route_after_dispatch({"combo_scenario": "kb"}) == "retrieve_kb"
    assert _route_after_dispatch({"combo_scenario": "business"}) == "retrieve_tool"
    assert _route_after_dispatch({"combo_scenario": "both"}) == "combo_kb"
    assert _route_after_dispatch({}) == "combo_kb"  # 缺失降级 both 路径
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/ai/chatbotgraph/test_chat_graph.py -v`
Expected: 新 2 条 FAIL

- [ ] **Step 3: 实现 combo 图**（加在 build.py；先 Read `retrieval_agent.py:166-171` 确认 tool 轨节点返回是否已含 `state 原值 + mw.results` 合并——已合并则包装节点只负责段落头与 attribution 兜底）

```python
# --- combo 图（agent_mode='combo'）：dispatch 分诊，both 场景顺序双段作答 ---

_COMBO_KB_HEADER = "\n\n### From your knowledge base\n\n"
_COMBO_BIZ_HEADER = "\n\n### From business data\n\n"


async def _combo_kb_node(state: dict) -> dict:
    """both 场景第一段：知识库视角（段落头 + 委托 kb 节点）。"""
    StreamEmitter().answer_delta(_COMBO_KB_HEADER)
    return await retrieve_kb_node(state)


async def _combo_tool_node(state: dict) -> dict:
    """both 场景第二段：业务数据视角（段落头 + 委托 tool 轨节点 + attribution 兜底合并）。"""
    StreamEmitter().answer_delta(_COMBO_BIZ_HEADER)
    out = await retrieve_tool_node(state)
    prior = state.get("attribution") or []
    if prior:
        merged = prior + [a for a in (out.get("attribution") or []) if a not in prior]
        out["attribution"] = merged
    return out


def _route_after_dispatch(state: dict) -> str:
    return {"kb": "retrieve_kb", "business": "retrieve_tool"}.get(
        state.get("combo_scenario"), "combo_kb")


def build_combo_graph() -> StateGraph:
    """组合智能体：guardrail → init → dispatch →[场景] kb / business / both(顺序双段) → END。"""
    g = StateGraph(ChatState)
    g.add_node("input_guard", _traced_node("input_guard", <照抄>))
    g.add_node("init", _traced_node("init", <照抄>))
    g.add_node("dispatch", _traced_node("dispatch", dispatch_node))
    g.add_node("retrieve_kb", _traced_node("retrieve_kb", retrieve_kb_node))
    g.add_node("retrieve_tool", _traced_node("retrieve_tool", retrieve_tool_node))
    g.add_node("combo_kb", _traced_node("combo_kb", _combo_kb_node))
    g.add_node("combo_tool", _traced_node("combo_tool", _combo_tool_node))
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", _route_after_guard, {"block": END, "ok": "init"})
    g.add_edge("init", "dispatch")
    g.add_conditional_edges("dispatch", _route_after_dispatch,
                            ["retrieve_kb", "retrieve_tool", "combo_kb"])
    g.add_edge("combo_kb", "combo_tool")
    g.add_edge("retrieve_kb", END)
    g.add_edge("retrieve_tool", END)
    g.add_edge("combo_tool", END)
    return g
```

`main.py` 编译 dict 加 `"combo": build_combo_graph().compile(),`。
超步数核对：guard→init→dispatch→combo_kb→combo_tool = 5 超步 < `_GRAPH_RECURSION_LIMIT`(10)，无需调限。
`StreamEmitter` import 在 build.py 顶部补（包装节点在图上下文内构造合法，先例 `retrieval_sql_agent.py:77` 注释）。

- [ ] **Step 4: 跑测试确认通过 + 全量回归**

Run: `uv run pytest tests/ai/ tests/chatbot/ tests/sse/ -v`
Expected: 全绿

- [ ] **Step 5: 提交**

```bash
git add source/ai/agent/chatbot_graph/build.py source/main.py tests/ai/chatbotgraph/test_chat_graph.py
git commit -m "feat(chatbot): add combo agent graph with dispatch and dual-scenario answering"
```

**✅ 里程碑：智能体 3（combo）后端完成。**

---

### Task 8: 前端——模式选择器 + payload 穿透 + 按会话记忆

**Files（均在 CIOaas-web/）:**
- Modify: `src/services/api/chat/streamApi.ts`（:15-20 类型、:84 后 payload）
- Modify: `src/pages/ai/chat/hooks/useChatStream.ts`（:118-119 send 签名、:148-149 streamChat 调用）
- Modify: `src/pages/ai/chat/Chat.tsx`（state、sendWith、handleSelectThread、handleNewChat、handleDeleteThread、InputBox 渲染处）
- Modify: `src/pages/ai/chat/components/InputBox.tsx`（Props + footer 工具栏）+ `InputBox.less`
- Create: `src/pages/ai/chat/components/AgentModePicker.tsx`
- Create: `src/pages/ai/chat/utils/agentMode.ts`
- Test: `src/services/api/chat/streamApi.test.ts`（:80-97 payload 断言区补用例）

- [ ] **Step 1: 写失败测试**（streamApi.test.ts 补，断言写法照同文件 :80-97 既有用例）

```ts
it('serializes agent_mode when not standard and omits it otherwise', async () => {
  // 照本文件既有 fetch mock 手法各调一次 streamChat：
  // 1) req.agentMode = 'kb'   → body.payload.agent_mode === 'kb'
  // 2) req.agentMode = 'standard' → body.payload 无 agent_mode 键
  // 3) req.agentMode 缺省      → body.payload 无 agent_mode 键
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npx umi-test src/services/api/chat/streamApi.test.ts`（先挂 node PATH）
Expected: FAIL（类型/断言不满足）

- [ ] **Step 3: 类型与 payload**（streamApi.ts）

```ts
export type AgentMode = 'standard' | 'kb' | 'combo';

export interface StreamChatRequest {
  threadId: string | null;
  companyId: string | null;
  question: string;
  simulate?: StreamChatSimulate;
  agentMode?: AgentMode;
}
```

L84 后（simulate 映射同款"非默认才放入"）：

```ts
if (req.agentMode && req.agentMode !== 'standard') payload.agent_mode = req.agentMode;
```

- [ ] **Step 4: hook 穿透**（useChatStream.ts）——send 签名加第 4 参 `agentMode?: AgentMode`，:148-149 `streamChat({ threadId, companyId, question, simulate, agentMode }, ...)`；续流路径（enterThread/subscribeStream）零改动。

- [ ] **Step 5: 按会话记忆 util**（`utils/agentMode.ts`，仿 `streamResume.ts` 的 try/catch 降级，但用 **localStorage**——模式是跨刷新偏好，先例 `pinnedThreads.ts`）

```ts
import type { AgentMode } from '@/services/api/chat/streamApi';

const KEY = 'chat_agent_mode';

type ModeMap = Record<string, AgentMode>;

function read(): ModeMap {
  try {
    return JSON.parse(window.localStorage.getItem(KEY) || '{}') as ModeMap;
  } catch {
    return {};
  }
}

function write(map: ModeMap): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(map));
  } catch {
    /* 存储不可用时静默降级 */
  }
}

export function getThreadMode(threadId: string): AgentMode | undefined {
  return read()[threadId];
}

export function setThreadMode(threadId: string, mode: AgentMode): void {
  const map = read();
  map[threadId] = mode;
  write(map);
}

export function clearThreadMode(threadId: string): void {
  const map = read();
  delete map[threadId];
  write(map);
}
```

- [ ] **Step 6: 选择器组件**（`AgentModePicker.tsx`，仿 `CompanyPicker.tsx` 受控哑组件；antd **v4** Select）

```tsx
import React from 'react';
import { Select } from 'antd';
import type { AgentMode } from '@/services/api/chat/streamApi';

const OPTIONS: Array<{ value: AgentMode; label: string }> = [
  { value: 'standard', label: 'Standard' },
  { value: 'kb', label: 'Knowledge Base' },
  { value: 'combo', label: 'Combo' },
];

interface Props {
  value: AgentMode;
  onChange: (m: AgentMode) => void;
  disabled?: boolean;
}

const AgentModePicker: React.FC<Props> = ({ value, onChange, disabled }) => (
  <Select<AgentMode>
    size="small"
    bordered={false}
    value={value}
    onChange={onChange}
    disabled={disabled}
    dropdownMatchSelectWidth={false}
    options={OPTIONS}
  />
);

export default AgentModePicker;
```

（若该 antd v4 小版本 Select 不支持 `options` prop，改 `<Select.Option>` 子元素写法。）

- [ ] **Step 7: 容器接线**（Chat.tsx，六处）

(a) L47 旁 `const [agentMode, setAgentMode] = useState<AgentMode>('standard');`
(b) `sendWith`（L110-117）：`send(text, cid, simulateParams, agentMode)`，send 返回后 `threadIdRef.current` 就绪处 `setThreadMode(threadIdRef.current, agentMode)`（所有发送路径 handleSend/handleRetry/handlePickCompany/forkAndResend 单点继承）
(c) `handleSelectThread`（L241-254）：`setAgentMode(getThreadMode(id) ?? 'standard');`
(d) `handleNewChat`（L256-263）：`setAgentMode('standard');`
(e) `handleDeleteThread`（L265-275，`clearResume(id)` 旁）：`clearThreadMode(id);`
(f) InputBox 渲染（L377-384）传 `agentMode={agentMode} onAgentModeChange={setAgentMode}`。

InputBox.tsx：Props（L13-20）加 `agentMode: AgentMode; onAgentModeChange: (m: AgentMode) => void;`，footer 工具栏（L104-138）`+` 按钮右侧渲染 `<AgentModePicker value={agentMode} onChange={onAgentModeChange} />`（streaming 中保持可用，只影响下一条）；`.footer` 布局在 InputBox.less（:71 段）按需微调间距。

- [ ] **Step 8: 验证**

Run: `npx umi-test src/services/api/chat/streamApi.test.ts`（PASS）→ `npm run tsc`（除 2 个存量坏文件外无新错）→ `npm run lint:fix`（无新告警）。

- [ ] **Step 9: 提交（CIOaas-web 仓库）**

```bash
git add src/services/api/chat/streamApi.ts src/services/api/chat/streamApi.test.ts src/pages/ai/chat/hooks/useChatStream.ts src/pages/ai/chat/Chat.tsx src/pages/ai/chat/components/InputBox.tsx src/pages/ai/chat/components/InputBox.less src/pages/ai/chat/components/AgentModePicker.tsx src/pages/ai/chat/utils/agentMode.ts
git commit -m "feat(chat): agent mode picker (standard/kb/combo) with per-thread memory"
```

---

### Task 9: 文档同步 + 真实环境冒烟验收

**Files:**
- Modify: `CIOaas-python/source/ai/CLAUDE.md`（tools/ 清单 + "工具经 Java 网关"例外登记 + agent/ 图清单补 kb/combo）
- Modify: `CIOaas-python/source/rag/CLAUDE.md`（:7 模块定位改"被 chatbot 经进程内 recall(caller_type=CHATBOT) 调用"）
- Modify: `CIOaas-python/CLAUDE.md`（数据查询能力表补知识库行并注明进程内例外；AI Chatbot 段补三智能体一句）
- Modify: `LG 根仓库 CLAUDE.md`（AI Chatbot 段补一句三智能体 + 知识库能力）与 `docs/AI-Chatbot/chatbot-tools-v2-interface.md`（Task 3 已生成，此处一并提交）

- [ ] **Step 1: 文档同步**（各文件按上述条目补写；ai/CLAUDE.md 例外登记措辞：“第二个例外 `knowledge_base_tool.py`——经 rag `application/service` 进程内调用，属 Python 域内跨模块协作、非 LG 业务数据取数，仍禁直连 DB/Java”）

- [ ] **Step 2: 真实环境冒烟（spec §5 清单逐项，本地需 dev-stack PG + RAG 库有已入库 STANDARD 空间）**

按 spec §5 的 11 项执行，重点：
1. standard：问"根据知识库，我们的报销制度"→ 步骤卡片 + 回答引 source_title；闲聊/纯财务不触发 KB 工具；
2. kb：必检索、无业务工具调用、无结果时明说；
3. combo：纯业务问题只跑业务、纯文档问题只跑 kb、混合问题两段作答（段落头清晰、tool_results 无丢失）；
4. 副作用：`ai_rag_search_log` 有 `caller_type=CHATBOT` 且 trace_id=本轮 chatbot.chat；hit_count 三级 +1；`ai_llm_call_log` 有 agent=rag/node=query 与 agent=chat/node=dispatch 记录；
5. 兼容：不带 agent_mode 的旧 payload 行为与现状一致；`/sql` 仅 standard 生效；
6. 并发：KB 检索进行中另一会话 token 输出无明显停顿。
逐项记录结果，任何不符回到对应任务修复后重验。

- [ ] **Step 3: 提交（三仓库各自提交，先征用户同意）**

```bash
# CIOaas-python
git add source/ai/CLAUDE.md source/rag/CLAUDE.md CLAUDE.md
git commit -m "docs: register knowledge-base tool exception and three-agent modes"
# LG 根仓库
git add CLAUDE.md docs/AI-Chatbot/chatbot-tools-v2-interface.md docs/superpowers/specs/2026-07-05-chatbot-knowledge-base-qa-design.md docs/superpowers/plans/2026-07-05-chatbot-knowledge-base-qa.md
git commit -m "docs: chatbot knowledge-base qa design and implementation plan"
```

---

## 计划自审记录

- **Spec 覆盖**：§3.1-3.6（Task 1-3）、§3.7 触发策略（Task 3 提示词 + Task 9 冒烟 4/1 项）、§3.8 三智能体（Task 4-8）、§4 占位（Task 2 space_ids=None）、§5 验证清单（Task 9）、§6 清单全部文件均有归属任务、§7 不做项无任务（正确）。
- **占位符**：Task 4 Step 2 用例与 Step 4 帧循环、Task 6 `_acomplete`、build 函数 `<照抄>` 两处——均为"以指定文件实文为准逐行对照落地"的显式指令并给出确切参照位置（防止凭空编造不存在的内部 API），非悬空 TBD。
- **类型一致性**：`KnowledgeSearchResult`/`AgentMode`/`combo_scenario`/`agent_mode` 命名全计划一致；`retrieve_kb_node` 返回契约（tool_results/attribution 合并）在 Task 4 定义、Task 7 依赖，语义一致。
