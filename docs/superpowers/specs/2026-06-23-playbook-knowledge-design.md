# Playbook Knowledge（/devSupport 子页）设计文档

> 关联文档：原型模块 `python/CIOaas-python/source/playbooks_graph_db/`、产出记录 `source/playbooks_graph_db/graph_rag_demo_results.md`、向量表 DDL `python/CIOaas-python/sql/sprint112/playbook_graph_schema.sql`
> 状态：设计已确认（2026-06-23），待写实现计划

## 1. 目标与范围

在 Web `/devSupport` 下新增子菜单 **Playbook Knowledge**，提供一个内部知识召回查看器，复用已有 `playbooks_graph_db` 原型（图关系在 LadybugDB、向量在 pgvector）：

- 输入查询内容 + 召回数量，两种召回方式：**Vector Search**（纯向量）、**V&Graph Search**（向量 + 图关系扩展）。
- 结果以 **chunk 级** 列表展示，每行预览召回文本前 200 字符，标注来源（vector / graph）。
- 任一结果行可点击，打开 **详情 Drawer**：上半部 **关系图**（该 playbook 与关联 playbook 的关系，ECharts graph series），下半部 **通过关系召回的块列表**（前 200 字符）。

**非目标**：不做新建/编辑 playbook、不做 LLM 合成回答（`answer()` 不在本页）、不改图/向量的入库链路、不做公司级权限过滤。

## 2. 架构与数据流

```
Web /devSupport/playbook-knowledge  (src/pages/ai/playbookKnowledge/)
  └─ @/utils/request → /api/ai/playbook/*   (dev 直连 Python:8090 / prod 经 Java 网关)
       └─ FastAPI: playbooks_graph_db.interfaces.routes
            └─ PlaybookRecallService (扩展)
                 ├─ pgvector  public.ai_rag_playbook_chunk   (向量召回 / 取块)
                 └─ LadybugDB  playbooks_graph_db (本地文件)  (图扩展 / 邻域)
```

衔接键：`pid`（LadybugDB Playbook.pid == ai_rag_playbook_chunk.pid）。鉴权：`get_current_user`，登录即可访问，数据全局（不按公司过滤），与 chatManage 一致。

## 3. 后端设计（CIOaas-python）

### 3.1 模块结构（方案 A：给原型加 interfaces 层）

`source/playbooks_graph_db/` 增加：
- `interfaces/__init__.py`
- `interfaces/routes.py` — `APIRouter(prefix="/api/ai/playbook", tags=["Playbook Knowledge"])`，`Depends(get_current_user)`，统一信封 `{success, code, message, data}`，只调 service。
- `interfaces/vo.py` — Pydantic Request / Response（lowerCamelCase）。
- `main.py` 挂载：`from playbooks_graph_db.interfaces.routes import router as playbook_router` → `app.include_router(playbook_router)`。

`PlaybookRecallService`（`chatbot_playbook_service.py`）扩展两个查询方法（复用现有 `recall` / `_graph_expand` / `_fetch_by_pids` 及 `_graph()` 只读连接）：
- `recall_list(query, top_k, use_graph, hops=3) -> list[PlaybookHit]`：向量召回 top_k chunk（source=vector）；`use_graph` 时对命中的 distinct seed pid 做 `_graph_expand(hops)`（沿 PlayRel 出边，**默认 3 跳**），取关联 playbook 的 profile chunk（source=graph，带 `rel_type` / `via_pid`）。返回合并列表，总数可超 top_k。
- `graph_detail(pid, hops=3) -> {playbook, nodes, edges, related_chunks}`：以 pid 为中心取 PlayRel 邻域（**双向**，≤hops）。nodes=邻域内 playbook（pid/title/category）；edges=PlayRel（source/target/rtype）；related_chunks=邻域 playbook 的 profile 前 200 字符（剔除中心 pid 自身）。

`PlaybookHit` 增补可选字段：`rel_type: str | None`、`via_pid: str | None`（图来源标注；vector 项为 None）。

### 3.2 接口契约

**POST `/api/ai/playbook/recall`**
- Request：`{ inputContent: str(非空), topK: int(1–50), useGraph: bool }`
- Response `data`：
  ```
  {
    items: [ {
      pid, title, category, stage,
      chunkType: "profile"|"body", seq: int,
      preview: str(≤200),
      source: "vector"|"graph",
      score: float|null,        // vector：余弦相似度；graph：null
      relType: str|null,        // graph：DEPENDS_ON/REFERENCES/FEEDS；vector：null
      viaPid: str|null          // graph：从哪个命中 playbook 扩展而来
    } ],
    vectorCount: int, graphCount: int
  }
  ```
- `useGraph=false`：仅 vector 项。`useGraph=true`：vector 项 + graph 项（去重：图扩展剔除已在 vector 命中的 pid；同一关联 playbook 只取 1 个 profile）。

**GET `/api/ai/playbook/detail?pid=...`**
- Response `data`：
  ```
  {
    playbook: { pid, title, category, stage },
    graph: {
      nodes: [ { pid, title, category } ],          // 含中心 + 邻域
      edges: [ { source: pid, target: pid, relType } ]
    },
    relatedChunks: [ { pid, title, relType, preview(≤200) } ]
  }
  ```
- pid 不存在 → `code != 0` + message。

### 3.3 错误处理

service 抛业务异常（如查询空、pid 不存在）在路由层转信封 `code != 0`；输入校验（topK 范围、inputContent 非空）在 VO + 路由。LadybugDB 只读连接打开失败（图库未生成）→ 明确报错信息提示先跑 `import_playbooks.py`。

## 4. 前端设计（CIOaas-web）

### 4.1 路由 / 菜单

`config/routes.ts` 在 `/devSupport` 子路由内（chatManage 之后）新增：
```
{ path: '/devSupport/playbook-knowledge', name: 'Playbook Knowledge', component: './ai/playbookKnowledge' }
```
（菜单显示名 / icon / access 跟随同级 devSupport 子项现有写法。）

### 4.2 页面结构 `src/pages/ai/playbookKnowledge/`

- `index.tsx`：查询区（`Input` 输入内容 + `InputNumber` top_k(默认 5，1–50) + 两个按钮 `Vector Search` / `V&Graph Search`）+ 结果区（列表/表格）。
  - 结果行：来源标签（vector 蓝 / graph 紫）、playbook 标题、`chunkType·seq`、score 或 `via relType`、前 200 字符预览。行可点击 → 打开详情 Drawer（传 pid）。
- `components/DetailDrawer.tsx`：右侧大号 Drawer。
  - 上：`components/RelationGraph.tsx` —— `echarts-for-react` 的 `graph` series（force 布局），节点=playbook（中心节点高亮），边带 relType label；点击节点可切换中心（再次拉 detail）。
  - 下：关联召回块列表（relType + 标题 + 200 字符预览）。
- `services/api/playbook/playbookApi.ts`：`recallPlaybook(req)`、`getPlaybookDetail(pid)`，走 `@/utils/request`，类型定义在 `services/api/playbook/typings.ts`（或就近）。

### 4.3 交互 / 状态

- 组件内局部状态（useState）即可，无需 dva model（单页、无跨页共享）。
- 两个按钮分别以 `useGraph` true/false 调同一接口；loading 态分别管理。
- 空结果 → Empty 占位；接口 `code!=0` → message.error。
- Drawer 内图加载失败 → 仅显示关联块列表（降级）。

## 5. 数据与依赖

- 复用现有：pgvector 表 `public.ai_rag_playbook_chunk`（lg_test）、LadybugDB 图库（`source/playbooks_graph_db/playbooks_graph_db`）、`PlaybookRecallService`、embedding 经 `llm_db_router.aembed`。
- 前端零新增依赖（ECharts 关系图复用已装 `echarts` + `echarts-for-react`）。
- 后端零新增依赖（已装 `real-ladybug`、`pgvector`、`psycopg`）。

## 6. 测试

- 后端 pytest（`tests/playbooks_graph_db/`）：`recall_list`（mock embedding + pg + Ladybug）、`graph_detail`（mock Ladybug）、路由 smoke（mock service）；覆盖率 ≥ 80%。
- 前端：`tsc` + `lint:fix` 通过 + 手动验证（两按钮、详情 Drawer、关系图渲染、空态/错误态）。

## 7. 关键决策记录

- 关系图库：**ECharts graph series**（零新依赖）。
- 结果粒度：**chunk 级**。
- V&Graph 图扩展：**默认 3 跳**（沿 PlayRel 出边）；详情邻域双向 ≤3 跳。
- 详情形态：**右侧 Drawer**（非独立路由页）。
- 详情入口：**所有结果行可点**（不限 graph 来源）。
- 鉴权：登录即可，数据全局，不按公司过滤。
