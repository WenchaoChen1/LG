# LLM Analytics 扩展 — 设计文档

**日期**：2026-05-29
**作者**：Auto（基于 3 个 explore agent 头脑风暴综合）
**范围**：LLM tracking 模块的筛选维度统一、枚举抽取、新增分析页面、call_mode 字段、目录优化

> ⚠️ **已陈旧 · 仅存档（2026-07-01 复核）**：本 spec 写于 `source/llm/` provider-first 重构前，
> 引用的目录（`source/llm/{config,tracing,providers,db}/` 平铺）、单例名（`router`）与建表方式
> （`setup_llm_tables` 启动期幂等建表）**均已过时**——现结构见 `CIOaas-python/source/llm/CLAUDE.md`，
> 建表改为手动执行 `sql/sprint111/llm_schema.sql`（启动期不自动建表）；`call_mode` 已落地且扩到 12 个
> 成员。本文仅作历史参考，落地实现以 `source/llm/` 代码 + 其 CLAUDE.md 为准。

---

## 1. 背景

当前 LLM tracking 已具备：
- **DB / ORM / TraceContext / business 业务侧赋值全部就绪**（agent #122 调查确认）
- 字段：`ref_company_id` / `ref_user_id` / `ref_task_id` / `caller_agent` / `caller_node` / `caller_purpose` / `trace_id` / `provider` / `model` 全部已写入
- 三个前端页面（CallList / Dashboard / TraceView）已具备基本筛选 + KPI + 图表

**缺口**：
1. `caller_agent` / `caller_node` / `caller_purpose` 在前端用 **3 项硬编码** Select，缺乏枚举权威源
2. `is_streaming` 布尔无法覆盖 4 种调用方式（sync/async × complete/stream）+ SSE 推流场景
3. 缺 Cost / Performance / Token 三个**多维下钻**分析页
4. 头脑风暴出更多有价值页面候选

---

## 2. 关键决策

### 2.1 枚举抽取位置

| 枚举 | 后端位置 | 前端导入 | 理由 |
|------|---------|---------|------|
| `caller_agent` | `source/ai/enums/caller_agent.py` | `web/src/services/api/llm/enums.ts`（手工同步） | agent 概念跨 LLM/RAG/MCP 共享，放 `ai` 模块根部 |
| `caller_node` | `source/ai/enums/caller_node.py` | 同上 | node 跨 agent 通用 |
| `caller_purpose` | `source/llm/config/call_purpose.py` | 同上 | 业务语义补充，仅 LLM 调用维度用 |
| `call_mode` (新增) | `source/llm/config/call_mode.py` | 同上 | LLM 调用方式枚举 |

**Python 实现**：`from enum import StrEnum` (3.12)，值用 snake_case 字符串。

**前端实现**：`web/src/services/api/llm/enums.ts` 手工镜像（保持单一事实源在后端，前端打包时一次性同步）。

### 2.2 枚举值

#### caller_agent（11 项）
```
financial_extract / chat / mcp_tools / summary_agent / qa_agent /
normalization_agent / rag_ingest / forecast_agent / vision_agent /
routing_agent / validation_agent
```

#### caller_node（跨 agent 候选，按 agent 分组在代码注释里）
```
# financial_extract
identify_fs / extract_cells / normalize_semantic_groups /
finalize_source_is_mapped / save_to_db / identify_data_values /
excel_identify_statement / excel_identify_data_values /
pdf_preprocess / excel_preprocess /
# chat
classify_intent /
# rag
search_knowledge / embed_for_search /
# summary
generate_summary /
# validation
validate_extracted_data /
# mcp
mcp_call_process_excel / mcp_call_lgpi_query / mcp_call_lgpi_financial
```

#### caller_purpose（11 项）
```
classify / extract / chat / normalize / summarize / qa /
validate / search / translate / json_object / vision_analyze
```

#### call_mode（5 项）
```
SYNC_COMPLETE / ASYNC_COMPLETE / SYNC_STREAM / ASYNC_STREAM / SSE_PROXY
```

### 2.3 call_mode 字段改造

**当前**：`LLMCallLog.perf_is_streaming: Boolean`

**新增**：`LLMCallLog.call_mode: VARCHAR(32)` —— 不删 `perf_is_streaming`（向后兼容），新写入双写。

**写入逻辑**：
- `router.complete()` → `SYNC_COMPLETE`
- `router.acomplete()` → `ASYNC_COMPLETE`
- `router.stream()` → `SYNC_STREAM`
- `router.astream()` → `ASYNC_STREAM`
- HTTP SSE 端点（如 chat 推流给前端）→ `SSE_PROXY`

**幂等迁移**：`setup_llm_tables` 加 `ALTER TABLE ai_llm_call_log ADD COLUMN IF NOT EXISTS call_mode VARCHAR(32)`，老数据 NULL 不回填。

### 2.4 前端筛选统一

**CallList / Dashboard / TraceView 三页面统一筛选字段**：

| 字段 | 类型 | 状态 |
|------|------|------|
| 时间范围 | DateRangePicker | ✅ 已有 |
| Company ID | Input | ✅ 已有（Dashboard / CallList） |
| User ID | Input | ✅ 已有 |
| Caller Agent | Select（枚举） | 改造：从 enums.ts 导入 |
| Caller Node | Select（枚举） | **新增**：从 enums.ts 导入 |
| Trace ID | Input | ✅ 已有 |
| Provider | Select | ✅ 已有 |
| Model | Select（动态拉取 + 静态合并） | ✅ 已有 |
| Call Mode | Select | **新增** |
| Status | Select | ✅ 已有 |
| Finish Reason | Select | ✅ 已有 |

TraceView 当前无独立筛选条 —— **不强加**（trace 视图聚焦单 trace_id 详情，无需多维筛选）。

### 2.5 新增分析页面

**P0（用户明确要求）**：

| 路径 | 页面 | 内容 |
|------|------|------|
| `/ai/devSupport/llm/cost` | **Cost Analytics** | KPI: total / avg per call / by-agent top；图：成本时序、cost by model/provider/agent/node Top；表：by company / by user 排行 |
| `/ai/devSupport/llm/performance` | **Performance Analytics** | KPI: P50/P95/P99/avg；图：latency 时序、by-node P50/P95 柱图；表：慢调用 Top 100 |
| `/ai/devSupport/llm/tokens` | **Token Analytics** | KPI: input/output/cached/reasoning total；图：token by agent/model；表：高 token 调用 + 截断列表 |

**P1（头脑风暴择优 2-3 个）**：

| 路径 | 页面 | 价值 |
|------|------|------|
| `/ai/devSupport/llm/errors` | **Error Analysis** | 失败率 by error_class / provider / model；定位失败根因 |
| `/ai/devSupport/llm/providers` | **Provider & Model Comparison** | 多维度横向对比（成本/延迟/失败率/token 效率） |

剩余候选（Retry 链路 / Cache 命中 / Heatmap / Top Companies / Top Users / Truncation Risk）**留作后续**，部分已在 Dashboard 内集成。

### 2.6 共用筛选条 + 共用聚合 API

**前端**：抽取 `<LlmAnalyticsFilterBar>` 公共组件，覆盖 11 个筛选字段。CallList / Dashboard / Cost / Performance / Tokens / Errors / Providers 七页面共用。

**后端**：复用已有 `aggregate_global_stats`（含 byProvider/byModel/byAgent/byNode + timeSeries + topErrors）+ 新增维度：`byCompany` / `byUser`（已有 Dashboard 表格用了）。

新增端点：
- `GET /api/ai/llm-calls/stats/cost-summary` — Cost 页用，多维 GROUP BY
- `GET /api/ai/llm-calls/stats/performance-summary` — Performance 页用
- `GET /api/ai/llm-calls/stats/token-summary` — Token 页用
- `GET /api/ai/llm-calls/stats/error-summary` — Error 页用

实际**先评估**：现有 `/stats` 是否已满足，能复用就不重复造端点（YAGNI）。

### 2.7 目录优化

**前端**：
```
src/pages/ai/llm/
├── components/
│   ├── ChartCard.tsx           # 已有
│   ├── FilterToolbar.tsx       # 已有，CallList 用
│   ├── AnalyticsFilterBar.tsx  # ★ 新增：分析页共用
│   ├── chartOptions.ts         # 已有
│   ├── CallLogTable.tsx        # 已有
│   └── analytics/              # ★ 新增子目录：3+N 分析页共用组件
│       ├── KpiGrid.tsx
│       ├── DimensionChart.tsx
│       └── TopNTable.tsx
├── hooks/                      # 已有 useLlmCallList / useLlmDashboard 等
├── CallList.tsx                # 已有
├── CallDetail.tsx              # 已有
├── Dashboard.tsx               # 已有
├── TraceView.tsx               # 已有
├── Cost.tsx                    # ★ 新增
├── Performance.tsx             # ★ 新增
├── Tokens.tsx                  # ★ 新增
├── Errors.tsx                  # ★ 新增（P1）
├── Providers.tsx               # ★ 新增（P1）
└── index.less                  # 已有
```

**后端**：
```
source/llm/
├── config/                     # 已有 tokens.py / request.py / models.py
│   ├── call_mode.py            # ★ 新增 StrEnum
│   └── call_purpose.py         # ★ 新增 StrEnum
├── tracing/                    # 已有
├── providers/                  # 已有
├── db/                         # 已有
├── application/                # 已有
└── interfaces/                 # 已有

source/ai/
└── enums/                      # ★ 新建模块
    ├── __init__.py
    ├── caller_agent.py         # StrEnum
    └── caller_node.py          # StrEnum
```

### 2.8 路由 + Sider 导航

**routes.ts** 新增 5 路由：
```ts
{ path: '/ai/devSupport/llm/cost', component: './ai/llm/Cost' },
{ path: '/ai/devSupport/llm/performance', component: './ai/llm/Performance' },
{ path: '/ai/devSupport/llm/tokens', component: './ai/llm/Tokens' },
{ path: '/ai/devSupport/llm/errors', component: './ai/llm/Errors' },
{ path: '/ai/devSupport/llm/providers', component: './ai/llm/Providers' },
```

**DevSupportShell.tsx LLM 组**：
```
- Dashboard
- Call Logs
- Trace Timeline
[Analytics 子分组]
- Cost
- Performance
- Tokens
- Errors          [P1]
- Providers       [P1]
```

---

## 3. 实施顺序

| # | 任务 | 阻塞 |
|---|------|------|
| 126 | 枚举模块（后端 + 前端） | 设计 ✅ |
| 127 | DB call_mode 字段（bootstrap 幂等 + ORM + business 写入） | 126 |
| 128 | 后端筛选 / 聚合 API 补全（call_mode 维度 + 必要的新端点） | 127 |
| 129 | 前端 DTO / API 同步 + AnalyticsFilterBar 公共组件 | 128 |
| 130 | 3 个新分析页：Cost / Performance / Tokens | 128, 129 |
| 131 | P1 页面：Errors + Providers | 130 |
| 132 | 目录结构按规范 review + Sider 导航 | 130 |
| 133 | 验证：tsc + ast + 重启 + 浏览器 smoke | 131, 132 |

---

## 4. 风险 / 缓解

| 风险 | 缓解 |
|------|------|
| 4 个枚举值如果未来扩展频繁，前端 `enums.ts` 与后端不同步 | 文档化"修改后端 enum 必须同步前端 enums.ts" + 加 git hook 提醒（后续） |
| call_mode 字段加在生产环境时已有 NULL 老数据 | 不回填，新查询用 `IS NULL OR call_mode IN (...)` 兼容；前端 Select 含 "All" 选项 |
| 5 个新页面太多 → 用户不知道用哪个 | Sider 加 "Analytics" 子分组分隔；首页 Dashboard 加 quick links 跳转 |
| AnalyticsFilterBar 公共组件抽得不够通用 | 先在 Cost 页内联实现，验证后再抽取（避免过早抽象） |

---

## 5. 不在本设计范围

- caller_step / caller_agent_version 业务侧赋值（非阻塞，后续按需补）
- Retry Chain / Cache Hit / Heatmap 页面（候选已记录，留作 P2）
- 跨 LLM Provider 自动 fallback / cost-routing 策略（router 层改动，与分析无关）
- 用户级 alerting / 阈值告警（需通知系统支持，另起设计）

---

## 6. 验收

- ✅ 三个原页面（CallList / Dashboard / TraceView）筛选条统一接 `enums.ts` 而非硬编码
- ✅ 新增 5 个枚举（caller_agent / caller_node / caller_purpose / call_mode + DB 字段）
- ✅ 3 个新分析页跑通 → 选时间 / agent / company → 数据正确
- ✅ 2 个 P1 页面（Errors / Providers）跑通
- ✅ tsc 0 错误 + python ast 0 错误
- ✅ Sider Analytics 子分组导航 OK
