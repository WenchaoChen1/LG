# AI Chatbot V1 设计文档（聊天页 + LG 数据问答）

> 关联文档：
> - 调研总览：[../调研/overall-requirements.md](../调研/overall-requirements.md)
> - 技术方案（参考，需按本文档修正）：[../调研/langgraph-technical-design.md](../调研/langgraph-technical-design.md)
> - Python↔Java 边界（参考，需按本文档修正）：[../调研/python-java-integration.md](../调研/python-java-integration.md)
> - 记忆文件规格（V2 输入）：用户提供的 `memory_file_spec_v4`
>
> 阶段：④ 设计 | 版本：v1-draft | 日期：2026-06-05 | 范围：仅 V1

---

## 0. 一句话目标

为公司端（`app*.lgpi.io`）与管理端（`admin*.lgpi.io`）各提供一个 **Ask AI 对话页**，让用户用自然语言查询**单个公司**的 **财报（Financial Statements）/ 对标（Benchmarking）/ 公司信息（Company Profile）** 三类 LG 数据；记忆、文件上传、跨公司聚合留到后续阶段。

---

## 1. 范围与分期

### 1.1 V1 范围（本文档）

| 项 | 是否在 V1 | 说明 |
|----|-----------|------|
| 两端 Ask AI 聊天页（公司端 + 管理端） | ✅ | 同一套后端，前端两个入口，按 hostname 区分行为 |
| 财报数据问答 | ✅ | 复用 `lgpi_financial_statements` |
| Benchmark 数据问答 | ✅ | **新建 `lgpi_benchmark` 工具**（调 Java `/benchmark/company/{id}/data`） |
| 公司信息问答 | ✅ | 复用 `lgpi_company_query` / `/invite/{id}` |
| 单公司上下文 | ✅ | 管理端通过"推断 + 确认"锁定单家公司 |
| 会话历史列表（基础版） | ✅ | chatbot 自有表；Today/Yesterday 分组；可继续对话；**不含** rename/delete |
| SSE 流式回复 | ✅ | 复用现有 `chunk_to_sse_bytes` |
| 双编排（确定性路由 + 工具调用循环） | ✅ | 见 §6 |
| 鉴权/ACL（A + Redis 增强） | ✅ | 见 §4 |

### 1.2 明确不在 V1（给引导或礼貌拒绝）

- 记忆文件 Layer 1a/1b（战略 / ICP / 竞品 / 波特五力 / 人员 / 创始人画像）→ **V2**
- 文件上传问答（RAG 索引 + 文档摘要）→ **V3**
- 跨公司聚合问答（"可访问公司里 burn 最差的 5 家"）→ **V1.1**
- Skills / Report Builder（"board-ready report"）→ post-MVP
- 会话 rename/delete、Welcome Prompt 个性化、追问 prompt → post-MVP
- 任何写操作（改财报 / 改 benchmark formula / 写回 LG）→ 不做
- 通用知识问答（"什么是 gross margin"）→ 可答但标注"非贵公司数据"

### 1.3 后续阶段索引

| 阶段 | 内容 | 对应 EPIC |
|------|------|-----------|
| V1（本文档） | 两端聊天页 + 单公司 LG 数据问答 | LG-1332/1335 + LG-1334/1337(单公司部分) + LG-1328 |
| V1.1 | 管理端跨公司聚合问答 | LG-1337 |
| V2 | 记忆 Layer 1a（C1–C10）+ Company Settings 初始化 | LG-1390~1396 |
| V3 | 文件上传问答（RAG）+ 文档摘要写记忆 | LG-1400/1388 |
| V4 | 管理端 Layer 1b + 组织级 KB（Layer 2） | LG-1397/1398/1331/1338 |

---

## 2. 角色与两端

| 端 | Hostname | 角色（roleType） | 公司上下文 | 跨公司 |
|----|----------|------------------|-----------|--------|
| 公司端 | `app*.lgpi.io` | COMPANY_ADMIN(2) / PROJECT_ADMIN(3) / MEMBER(4)，即 roleType>1 | **强制锁定本公司** `inviteDto.id` | 否 |
| 管理端 | `admin*.lgpi.io` | SUPER_ADMIN(1)（含 PM/PGM 产品概念），即 roleType≤1 | 在**可访问公司集**内，按"推断+确认"锁定单家 | V1 否（V1.1 开放） |

> V1 不细分 PM / PGM / Super Admin 的差异，管理端统一按"可访问公司集"做 ACL 范围。

---

## 3. 架构总览

```
前端  app*.lgpi.io（公司端）/ admin*.lgpi.io（管理端）
  └─ src/pages/ai/chat/  新建聊天页
       │  POST /api/ai/chat (SSE)  —— 带 JWT，复用现有 RAG 同款链路
       │  GET  /api/ai/chat/threads / .../messages / .../companies
       ▼
Python FastAPI (8090)   —— 新增 source/chatbot/ 模块
  ├─ 身份/ACL：网关头(prod)/解JWT(dev) + 读 Redis 验登出&取角色 + /invite/portfolio 缓存
  ├─ Chat LangGraph 图（第二张图，挨着 financial_extract_graph）
  │     guardrail → classify_intent → resolve_company → derive_scope
  │       → [确定性取数: fin / benchmark / company]   ← 默认稳路
  │       → [tool_calling_loop]                        ← 可选：开放式多工具
  │       → synthesize(SSE 流式) → persist(chatbot 表)
  ├─ 工具：lgpi_financial_statements / lgpi_company_query(已有) + lgpi_benchmark(新建)
  ├─ LLM：llm_db_router(强制)，补 tool_calls 透出
  ├─ 会话/历史：chatbot 自有表 ai_chatbot_thread / ai_chatbot_message
  └─ 追踪：ai_trace(已有，仅作可观测，不当业务数据)
       │  LGPI client (REST，静态 service token) —— 不直连业务库
       ▼
Java REST: /financialStatements · /benchmark/company/{id}/data · /invite/{id} · /invite/portfolio
```

### 3.1 关键决策与理由（已与产品确认）

| # | 决策 | 选项 | 理由 |
|---|------|------|------|
| D1 | 后端编排基座 | **复用现有 Python 基础设施**（LangGraph + llm_db_router + ai_trace + SQS） | 调研文档的"全新 LangChain/Celery/LangSmith/直读 PG"与已上线代码冲突且违反 lint（TID251 禁止直接 import langchain_openai/openai/anthropic） |
| D2 | LG 数据访问 | **走 Java REST** | 复用现成工具，不重写 Java 的财报组装/聚合逻辑，避免重复造轮子与漂移 |
| D3 | 编排风格 | **确定性路由 + 工具调用循环 两者都要** | 核心数据问答用确定性路由保稳；开放式多工具业务用 finish_reason 工具循环 |
| D4 | 鉴权/ACL | **Redis 取身份 + 转发用户 token 给 Java 鉴权** | 身份读 Java 写的 Redis（`auth:token`/`auth:user`）；权限与取数用**用户 token** 调 Java（Java 用同一 Redis 校验 token），不引第二套身份、不再用静态 token |
| D5 | chatbot 数据归属 | **自有模块 `source/chatbot/` + 自有表** | 不复用 `ai_llm_*`（LLM 调用追踪）/ RAG 表当作 chatbot 业务数据 |
| D6 | 管理端公司归属 | **可访问集内 AI 推断 + 推不出再确认** | 对齐 LG-1385/LG-1399 思路 |

---

## 4. 鉴权与 ACL 设计（A + Redis 增强）

### 4.1 既有事实（来自代码审查）

- JWT 仅含 `sub`(userId)/iat/exp；签名为 **HMAC 共享密钥**（`jwt.secret`）。
- Java 数据接口（`/financialStatements`、`/benchmark/.../data`）**只验登录、不做逐用户 ACL**。
- 生产 Java 网关会注入 `x-user-id` / `x-company-id` / `x-user-role` 头给 Python（RAG/LLM 页面已在用此链路）。
- Java 把用户上下文写入 Redis：`auth:user:{userId}`（角色/机构/home 公司）、`auth:token:{hash}`（token 有效性）。
- Python 现用**硬编码静态 service token** 调 Java（`LGPI_BEARER_TOKEN`，且指向 `admin-test.lgpi.io`）。

### 4.1.1 已核实的 Java Redis 方案（实现细节）

- token 校验：`auth:token:{base64url_nopad(SHA256(原始JWT))}` → `userId`；TTL 24h；**登出立即删 key**（key 在 = 未登出）。
- 用户上下文：`auth:user:{userId}` → JSON `{id, username, organizationId, authorities}`；TTL 300 天。**注意：不含 company_id，不含 roleType，只有 organizationId + Spring authorities。**
- Redis 连接：`localhost:6379`，**DB 10**，无密码（生产以各环境实际为准）。
- ⚠️ 网关（`LoggingGlobalFilter`）当前**不注入** `x-user-*` 头；RAG 的 `require_user_context` 跑在 dev 占位上。故 V1 不依赖网关头注入，改用下面的 token 直读方案。

### 4.2 V1 方案（最终）

身份与权限分两条**真实可用**的机制，均基于前端透传的 `Authorization: Bearer <token>`（网关不剥离该头；dev 直连也带）：

**① 登录身份（identity）— 读 Redis**
- Python **新增 redis 客户端**（连共享 Redis，默认 DB 10，配置化 `REDIS_*`）。
- 取请求头 token → 算 `auth:token:{base64url_nopad(SHA256(token))}` → `redis.get` → `userId`；为空 ⇒ token 失效/已登出 ⇒ **401**（天然吊销校验）。
- `auth:user:{userId}` → `{organizationId, authorities}` → 构造 `ChatUserContext`（user_id / org_id / authorities）。
- `is_admin` 由 authorities 命中 admin 白名单判定（复用 `RAG_ADMIN_ROLES` / `get_admin_roles` 模式）。

**② 权限与公司范围（authorization）— 用该 token 调 Java**
- 可访问公司：用**用户 token** 调 Java `GET /invite/portfolio`（Java 的 `JwtAuthenticationFilter` 用同一 Redis 校验 token）→ 返回该用户可访问公司；**内存缓存 5 分钟**（按 user_id）。
- 本次问答 `company_id` 必须 ∈ 该集合：company 端=自身公司（集合通常单元素）；admin 端=多元素集，**V1 仍限单公司**（不聚合）。

**③ 取数 — 转发用户 token**
- 财报/Benchmark/公司信息均用**用户 token** 调 Java（`/financialStatements`、`/benchmark/company/{id}/data`、`/invite/{id}`），Java 校验 token；公司越权已在 ② 拦截。
- **不再使用硬编码静态 service token**（解决原技术债）。

### 4.3 安全注意 / 待对齐

- Redis 连接配置（host/port/db=10/password）需各环境提供给 Python（新增 `REDIS_*` env）。
- `authorities` → `is_admin` / 端类型 的映射格式需与 Java 对齐（authorities 是 Spring `ROLE_*` 串，非 roleType 1–4）。
- 确认网关对 `/api/ai/*` **透传** `Authorization` 头（dev 直连必带；prod 需确认不剥离）。
- "网关头注入 + RAG/Chat 统一 `require_user_context` 升级" 仍是全平台 `/api/ai/*` 身份硬化的后续任务（RAG 同步受益），但 V1 不依赖它。

---

## 5. 数据问答范围圈定

| 数据域 | 取数通道 | 范围内可问 | 范围外（不答/引导） |
|--------|----------|-----------|----------|
| 财报 | `lgpi_financial_statements`（已有） | 标准行项（Revenue/COGS/Gross Profit/Gross Margin/OPEX/EBITDA/Net Income/Cash/AR/AP/Long-Term Debt/ARR/MRR/Runway/Burn Rate 等接口返回行）；类型 Actuals/Committed Forecast/System Forecast；视图 Monthly/Quarterly/Annually；取值、同比环比、区间趋势、缺数据补全引导 | 自定义公式、写回、钻取原始凭证 |
| 对标 | **`lgpi_benchmark`（新建）** | 百分位定位(P0–P100)、Overall Benchmark Score、与 Internal Peers/KeyBanc/High Alpha/Benchmarkit.ai 对比、按 Growth/Efficiency/Margins/Capital 分类 | 改 benchmark formula、benchmark 录入 |
| 公司信息 | `lgpi_company_query` / `/invite/{id}` | Company name/Overview/Type/Status(阶段)/URL/industry 等基础事实 | 抓官网、记忆性认知（V2） |

> 缺数据统一进入"如何补全"引导（如"请在 Financial Entry 录入该月数据"）。财务数字必须来自工具结果，**禁止模型自行推算**。

---

## 6. 编排设计（Chat LangGraph 图）

新建第二张 `StateGraph`，与 `financial_extract_graph` 并存，节点均为 `(state)->partial_state`。

### 6.1 状态（ChatState，要点）

- 鉴权上下文（入口注入、节点不可改）：`user_id` / `user_role` / `end_type(company|admin)` / `accessible_companies` / `home_company_id`。
- 会话：`thread_id` / `messages`(近 N 轮) / `question`。
- 路由：`intent(financial|benchmark|company|general|blocked)` / `active_company_id` / `needs_company_pick(bool)` / `orchestration(deterministic|tool_loop)`。
- 结果：`tool_results` / `answer` / `attribution` / `needs_data_hint`。
- 安全：`blocked_reason`。

### 6.2 节点职责

| 节点 | 模型 | 职责 |
|------|------|------|
| `guardrail` | 规则/轻量 | prompt injection / 越权探测拦截 |
| `classify_intent` | Haiku | 意图分类 + 抽参（指标/期间/数据类型/视图）；判定 orchestration 模式 |
| `resolve_company` | Haiku + 规则 | 见 §6.3 公司归属解析 |
| `derive_scope` | 纯代码 | 角色 → 允许范围；锁定 `active_company_id` 并做 ACL 断言 |
| `call_financial` / `call_benchmark` / `call_company` | 纯代码 + 工具 | 确定性取数（默认稳路） |
| `tool_calling_loop` | Opus/Sonnet + tools | 可选：开放式多工具循环（finish_reason=tool_calls → 执行 → 回填） |
| `synthesize` | Opus/Sonnet | 综合工具结果生成回复，SSE 流式输出；附免责声明 |
| `compose_no_data` | Haiku | 缺数据/未锁定公司时的引导话术 |
| `persist` | 纯代码 | 落 `ai_chatbot_thread`/`ai_chatbot_message`（首轮 LLM 生成 title） |

### 6.3 公司归属解析（resolve_company）

- 公司端：跳过推断，`active_company_id = home_company_id`。
- 管理端：
  1. 取可访问公司集（§4.2 缓存）。
  2. 轻量识别本轮消息是否提及某可访问公司（名称/别名匹配）。
  3. 决策：
     - 命中唯一公司 → 设为本会话 `active_company_id`（UI 顶部显示"正在分析：X"）。
     - 已有 active 且本轮未提新公司 → 沿用。
     - 未命中且无 active → `needs_company_pick=true`，回引导话术，前端弹公司选择器（来自可访问集）。
     - 命中多家 → V1 提示"仅支持单公司，请指定一家"。

### 6.4 双编排选择

- 默认 `deterministic`：`classify_intent` 已判定单一数据域 → 走对应 `call_*` 节点（稳定、可对账）。
- `tool_loop`：问题需多工具自由组合时启用；依赖给 `llm_db_router` 补 `tool_calls` 透出（见 §8）。
- 两条路最终都汇到 `synthesize`。

---

## 7. 安全隔离（V1 适配）

| 层 | 实现 | 防什么 |
|----|------|--------|
| L1 入口 | 身份在入口注入 state，节点不可覆盖 | 伪造身份 |
| L2 ACL | 公司端锁 home 公司；管理端校验 ∈ 可访问集 | 越权查别家公司 |
| L3 工具 | 工具入参 company_id 由 state 注入，节点二次裁剪 | 工具越权 |
| L4 Prompt | system prompt 禁令 + guardrail 入口扫描 | prompt 注入 |

> V1 无 Layer 1b，故暂无"1b 泄露"风险；但架构上为 V2/V4 预留：管理端与公司端共用图但 `end_type` 决定可达节点与可见数据。

---

## 8. 工具设计

| 工具 | 状态 | 输入 | 输出（AI 友好） |
|------|------|------|----------------|
| `lgpi_company_query` | 复用 | 无 | `flattened_companies[]`（id/name/path） |
| `lgpi_financial_statements` | 复用 | company_id, from_date, type(entry/financial_forecast/system), view, is_edit | `data_structure_for_ai` + meta(headers/currency/view) + rows[] + metrics_index[] |
| **`lgpi_benchmark`** | **新建** | company_id, date(或区间), data_sources[], benchmark_sources[], filter(Growth/Efficiency/Margins/Capital) | 百分位/Score/peer 对比的 AI 友好结构（参照 financial 的 `data_structure_for_ai` 风格封装 Java `BenchmarkRawDataResponse`） |

**`llm_db_router` 工具能力扩展（低侵入，约 6 文件）：**
- `TextResult` 增加 `tool_calls` 字段；
- `openai_compat` / `anthropic_native` 两个 kernel 从 `raw` 抽取 tool_calls / tool_use；
- SSE 增加 tool_calls 透出；
- （可选）`ai_llm_call_log` 记录 tool_calls。
- 仅 `tool_loop` 路线需要；`deterministic` 路线不依赖此扩展。

---

## 9. 数据模型（chatbot 自有，`source/chatbot/`）

> **原则：chatbot 业务数据独立存储，不复用 `ai_llm_*`（LLM 调用追踪）与 RAG 表。** LangGraph checkpointer 非 V1 历史的依赖来源——多轮上下文由下表显式加载。

```sql
-- 会话/线程索引
CREATE TABLE ai_chatbot_thread (
  thread_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          TEXT NOT NULL,
  org_id           TEXT,
  end_type         TEXT NOT NULL,          -- 'company' | 'admin'
  active_company_id TEXT,                  -- 锁定公司（管理端推断/确认后写入）
  title            TEXT,                   -- 首轮后 LLM 生成
  last_message_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  status           TEXT NOT NULL DEFAULT 'active',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_chatbot_thread_user ON ai_chatbot_thread (user_id, last_message_at DESC);

-- 消息（chatbot 视角的真实对话轮）
CREATE TABLE ai_chatbot_message (
  message_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id    UUID NOT NULL REFERENCES ai_chatbot_thread(thread_id),
  seq          INT  NOT NULL,
  role         TEXT NOT NULL,              -- 'user' | 'assistant' | 'system'
  content      TEXT NOT NULL,
  attribution  JSONB,                      -- 数据来源标注
  used_tools   JSONB,                      -- 本轮调用的工具与参数
  trace_id     TEXT,                       -- 软关联 ai_trace（仅可观测）
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_chatbot_message_thread ON ai_chatbot_message (thread_id, seq);
```

- 多轮上下文：按 `thread_id` 取最近 N 条 `ai_chatbot_message`。
- 历史列表：按 `user_id` 查 `ai_chatbot_thread`，前端按 `last_message_at` 做 Today/Yesterday/Last Week 分组。

---

## 10. 接口契约（Python `/ai/*`，前端经 `/api/ai/*`）

### 10.1 发送消息（SSE 流式）
`POST /ai/chat`
```json
{ "thread_id": "uuid|null", "company_id": "string|null", "question": "..." }
```
- 公司端：忽略入参 company_id，强制 home 公司。
- 管理端：company_id 可空（触发推断）；若已选定则带上。
- 响应：SSE 流（复用 `chunk_to_sse_bytes`）。流末附 final 元信息：
```json
{ "thread_id":"...", "attribution":[...], "active_company_id":"...|null",
  "needs_company_pick": false, "needs_data_hint": null }
```

### 10.2 会话历史
- `GET /ai/chat/threads` → 当前用户会话列表（按 last_message_at 倒序）。
- `GET /ai/chat/threads/{thread_id}/messages` → 某会话完整消息。

### 10.3 公司选择器（管理端）
- `GET /ai/chat/companies` → 当前用户可访问公司集（供推不出时的选择器；后端复用 `/invite/portfolio` + 缓存）。

---

## 11. 前端设计（功能级）

### 11.1 目录结构（遵循 CIOaas-web 三层数据流）
```
src/pages/ai/chat/
├── index.tsx                 入口（按 hostname 判定公司端/管理端行为）
├── index.less
├── types.ts / constants.ts
├── components/
│   ├── ConversationPane.tsx  消息列表（流式渲染 react-markdown）
│   ├── MessageBubble.tsx
│   ├── InputBox.tsx          文本输入（V1 不含附件/语音/network 开关）
│   ├── SuggestionCards.tsx   V1 范围内的建议卡（见 11.3）
│   ├── CompanyPicker.tsx     管理端公司选择器（推不出/手动切换时用）
│   └── HistorySidebar.tsx    会话历史列表（Today/Yesterday 分组）
├── hooks/
│   ├── useChatStream.ts      SSE 流式消费
│   ├── useChatThreads.ts     历史列表
│   └── useAccessibleCompanies.ts  管理端公司集
└── ...
src/services/api/chat/ + src/services/service/chat/   三层服务
config/routes.ts  公司端 & 管理端两入口
```

### 11.2 两端差异（hostname 驱动）
- 公司端：进入即聊天，无公司选择器；上下文=本公司。
- 管理端：顶部显示/可切换"正在分析：X 公司"；当后端返回 `needs_company_pick` 时弹 `CompanyPicker`。

### 11.3 建议卡片（V1 重做，匹配圈定范围）
- 财报：Summarize this company's latest financial highlights
- 财报趋势：How has ARR/MRR trended over the last 4 quarters?
- 对标：Where does this company rank vs peers (percentile)?
- 现金/Runway：What's the current runway and burn rate?
- 预测：Compare actuals vs committed forecast for revenue
- 公司信息：What does this company do and what stage is it at?
> 图一原卡片中的"compare across all portfolio companies / board-ready report"超出 V1 范围，移除。

### 11.4 流式与免责
- SSE 增量渲染；回复底部固定"内容由 AI 生成，仅供参考"。

---

## 12. 失败降级

| 场景 | 行为 |
|------|------|
| Java 数据接口不可达 | 回"业务数据系统暂时不可用，请稍后重试" |
| 单指标在 Java 为空 | 进 `compose_no_data`，给补全引导 |
| 管理端推不出公司 | `needs_company_pick=true`，前端弹选择器，不取数 |
| token 已登出（Redis 校验失败） | 401，前端按现有逻辑跳登录 |
| guardrail 命中 | 礼貌拒绝，不进入取数 |

---

## 13. 待确认事项（开发前与各端对齐）

| # | 问题 | 影响 |
|---|------|------|
| 1 | 生产网关是否已为 `/api/ai/chat*` 配置路由（现有 RAG/LLM 路径已通，需确认 chat 子路径同样覆盖） | 部署/联调 |
| 2 | 开发态身份：解 JWT 拿 userId 后，角色/home 公司取自 Redis 还是调 Java「current user」接口？需 freeze 具体来源 | §4.2 |
| 3 | `/invite/portfolio` 返回是否已是"当前用户可访问公司"且稳定？字段语义 freeze | §4.2 管理端 ACL |
| 4 | Java `BenchmarkRawDataResponse` 字段 freeze（供 `lgpi_benchmark` 封装 AI 友好结构） | §8 |
| 5 | 多轮上下文窗口 N（建议 10）与 token 上限策略 | §6.1 / 成本 |
| 6 | 生产 LGPI base_url + 正式服务 token 替换计划 | §4.3 安全 |

---

## 14. 与调研文档的差异说明（供后续修订调研稿）

| 调研文档原设 | 本设计修正 | 原因 |
|--------------|-----------|------|
| 全新 LangChain `ChatOpenAI`/`bind_tools` | 强制 `llm_db_router`，工具能力扩展 router | lint TID251 禁直接用 langchain_openai/SDK |
| Celery + Redis broker | 复用现有 SQS（V1 聊天为同步图，暂不需异步抽取） | 不引入并存的第二套异步体系 |
| LangSmith | 复用自研 `ai_trace` | 代码库零 LangSmith 引用 |
| Python 直读 `fi_*` 表（`cioaas_ai_ro`） | 走 Java REST | 该只读角色当前不存在；避免重写 Java 财报组装逻辑 |
| LangChain PGVector + Cohere rerank | （V3 再议）复用自研 RAG | V1 不含文档问答 |
| chatbot 历史复用 checkpointer/`ai_llm_conversation` | chatbot 自有表 `ai_chatbot_*` | 不复用 LLM/RAG 数据当 chatbot 业务数据 |
