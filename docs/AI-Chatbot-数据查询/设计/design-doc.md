> 关联文档: [注意事项与已知问题](./issues-and-caveats.md) · 上游架构 [AI-Chatbot 设计](../../AI-Chatbot/设计/design-doc.md)

# AI Chatbot 业务数据查询能力 — 设计文档（V1）

## 0. 背景与目标

在已有 AI Chatbot（`CIOaas-python/source/chatbot/`，LangGraph 对话图）基础上，把"查询 LG 业务数据"的能力做扎实、做干净，让 chatbot 能基于**当前会话用户身份与公司数据权限**回答以下四类问题：

1. **身份与公司上下文**：当前会话用户是谁、能访问哪些公司、某公司的简介。
2. **财务指标**：标准化财务字段（Revenue / COGS / OPEX / ARR / MRR / Rule of 40 / Gross Margin …）跨三种数据类型（Actuals / Committed Forecast / System Generated Forecast）的按月数值——对应 Finance 页 **Financial Statements** tab。
3. **Benchmark 对标**：Overall Benchmark Score 百分位、四张卡片分、6 指标 × 12 维度（3 数据类型 × 4 benchmark 源）的百分位——对应 Finance 页 **Benchmarking** tab。
4. **Normalization 溯源**：标准化值 ↔ 原始值 ↔ 折算公式 ↔ 数据源——对应 **normalizationTracing** 页。

**架构铁律（不可违反）**：Python 查 LG 业务数据**一律经 Java 网关回调**（`/api/web/*`，透传当前用户 Bearer token），不直连 DB、不直连 Java 服务。客户端走 `source/lgpi_api/` 模块（一接口一文件 `*_api.py`）。

---

## 1. 关键技术结论（探查所得）

### 1.1 财务指标的"重复"问题与权威源

数据库里财务数据确实分散在多张表，存在三类重复：

| 类型 | 表 | 说明 |
|------|----|------|
| 输入层（命名不一致） | `finance_manual_data` / `_temp` / `financial_forecast_*` | `gross_revenue`/`operating_expenses`/`assets_other` 等原始命名 |
| 归一化层（**权威源**） | **`financial_normalization_current`** | 宽表，`(company_id, date, data_type)` 唯一；30 个标准化字段全在此，含派生 KPI（gross_margin/rule_of_40/arr…） |
| 原始导入层 | `quickbooks_profit_and_loss` / `balance_sheet`（varchar） | QBO 原始未折算 |

**结论**：读取**只认 `financial_normalization_current`**，且现有 `GET /api/web/financialStatements` 已经服务它（Java 端读该表 + 组织 meta/rows）。因此 chatbot 侧**不新增 Java 接口**，而是：**统一只走 `/financialStatements` 这一条权威读路径**，并在 Python 侧做"干净投影"消除用户感知到的重复。这从根上回答了"数据库存了很多重复指标，怎么干净获取"。

### 1.2 Benchmark 百分位是前端客户端算的

`GET /api/web/benchmark/company/{id}/data` **只返回原始值**（公司各指标月度值、外部 benchmark 的 P25/median/P75、peer 列表与 peer 月度值），**百分位、Overall Score、卡片分、12 维聚合全部在前端 `src/pages/companyFinance/benchmark/calc/` 用纯函数客户端计算**。

这套 calc 逻辑：
- `numberParse.ts` — 解析 `"65%"→0.65`、`"$1.2M"→1.2e6`、`"36 months"→36`；百分位展示格式化。
- `percentile.ts` — 内部 peer 百分位（Nearest Rank + Standard Competition Ranking，`P=(R-1)/(N-1)×100`）。
- `externalPercentile.ts` — 外部 benchmark 百分位（P25/P50/P75 四种组合 + 线性插值 + 边界 + reverseIndicator 翻转）。
- `runway.ts` — Monthly Runway 的 4 档分类排名（TOP/CALCULATED/BOTTOM/NO_DATA）。
- `metrics.ts` — 6 指标 + 4 卡片元数据（含 `isReverse`，仅 Sales Efficiency Ratio 反向）。
- `aggregate.ts` — 主聚合：每 metric × dimension 算百分位 → 卡片维度点（卡内各指标均值）→ 卡片分（维度点均值）→ Overall（可见卡片分均值）。

它本身是"后端 calculator 的 TS 移植 + 纯函数"，**可完整、忠实地移植到 Python**。这与用户提供的"benchmark 聚合穷举"规格一致（每维度对齐取均值 → 卡片均值 → 总均值）。

**结论**：chatbot 的 benchmark 能力 = 调原始 `/data` 接口 + **在 Python 侧忠实移植这套 calc**，产出与页面一致的 Overall Score / 卡片分 / 12 维百分位。此方案**不动 Java、不动前端**（零回归），代价是 Python 端需与前端 calc 保持同步（见注意事项）。

### 1.3 身份与 ACL 链路已就绪

- `require_chat_user`（`interfaces/deps.py`）从 Redis 取 `AuthUser`（user_id / company_id / organization_id / authorities）。
- `routes.send()` 取原始 Bearer token，调 `accessible_companies(user_id, auth_token)`（`auth/acl.py` → `/invite/portfolio`，缓存 5 分钟）拿到**用户可访问公司集**，注入图 state。
- `derive_scope` 节点校验 `active_company_id ∈ accessible_companies`，越权拦截。
- 缺口：**公司简介**没有对应客户端（`/invite/{id}` 详情未封装）。`list_companies` 当前用 `/invite/query`（全量，admin 端有越权泄露风险），应改用 ACL 列表。

---

## 2. 设计总览

```
chatbot 对话图 (LangGraph)
   ├─ call_company       → 身份 + 可访问公司 + 公司简介
   ├─ call_financial     → 财务指标干净投影（权威源 financial_normalization_current）
   ├─ call_benchmark     → 原始值 + Python 移植 calc → Overall/卡片/12维百分位
   └─ call_normalization → normalization 溯源（标准化值↔原始值↔公式）   ← 新增意图
            │
            ▼ 工具层 source/chatbot/tools/
   company_tool / financial_tool / benchmark_tool(+_benchmark_scoring) / normalization_tool
            │
            ▼ 数据层 source/lgpi_api/（经 Java 网关，透传用户 token）
   GET /api/web/invite/portfolio        (已有) 可访问公司 = ACL
   GET /api/web/invite/{id}             (新封装) 公司详情/简介
   GET /api/web/financialStatements     (已有) 财务报表（权威源）
   GET /api/web/benchmark/company/{id}/data  (已有) benchmark 原始值
   POST /api/web/financialNormalized/metricTrace (新封装) normalization 溯源
```

**意图路由（确定性图，沿用现状不改编排范式）**：在现有 `financial / benchmark / company / general` 基础上**新增 `normalization`** 意图。保持确定性路由（可对账、稳定），不切换到 tool-calling loop（降低 V1 风险）。

---

## 3. 数据层设计（`source/lgpi_api/`）

遵循既有模板：入参 `XxxParams`（含 `auth_token`）→ 私有 `_request_xxx` → 解析 `_parse_xxx` → 对外 `query_xxx` → 返回 `XxxResult`；仅经 `__init__.py` 导出。

### 3.1 `_http.py` — 新增 `post_json`

metricTrace 是 POST。新增与 `get_json` 同构的 `post_json(url, *, auth_token, json_body, label, timeout, body_preview)`：复用 `build_headers` + 重试（metricTrace 是只读查询，幂等可安全重试，但仅对网络错误/502/503/504 重试，4xx 不重试）。

### 3.2 `company_detail_api.py`（新）— `GET /api/web/invite/{companyId}`

```python
class CompanyDetailParams(BaseModel):
    company_id: str
    auth_token: Optional[str] = None

class CompanyDetail(BaseModel):       # 取 InviteDto 子集，扁平化，全部 Optional
    id: Optional[str] = None
    name: Optional[str] = None         # company / company_name
    description: Optional[str] = None
    currency: Optional[str] = None
    company_status: Optional[Any] = None
    type: Optional[Any] = None
    category: Optional[Any] = None
    revenue_recognition: Optional[Any] = None
    archived: Optional[bool] = None

class CompanyDetailResult(BaseModel):
    ok: bool
    message: Optional[str] = None
    detail: Optional[CompanyDetail] = None
    raw: dict[str, Any] = Field(default_factory=dict)

async def query_company_detail(params: CompanyDetailParams) -> CompanyDetailResult
```

字段以 Java `InviteDto` 实际返回为准，缺失字段留空（不强约束，避免 Java 改字段即崩）。

### 3.3 `normalization_trace_api.py`（新）— `POST /api/web/financialNormalized/metricTrace`

```python
class NormalizationTraceParams(BaseModel):
    company_ids: list[str]
    metric_values: Optional[list[str]] = None   # 指标 code（如 "REVENUE"）；None/[] → 全部指标
    date: Optional[str] = None                   # YYYY-MM
    data_types: Optional[list[int]] = None       # 0=Actuals 1=Committed 2=System；None → 全部
    page: int = 1
    size: int = 20
    auth_token: Optional[str] = None

class NormalizationTraceItem(BaseModel):
    company_id, company_name, metric, metric_value, metric_currency,
    original_metric_name, original_metric_value, original_currency,
    source, data_type_name, financial_date, exchange_rate,
    conversion_date, normalization_formula            # 均 Optional

class NormalizationTraceResult(BaseModel):
    ok: bool; message: Optional[str]; items: list[NormalizationTraceItem]
    total: int = 0; page: int = 1; size: int = 20
    raw: dict[str, Any] = Field(default_factory=dict)

async def query_normalization_trace(params) -> NormalizationTraceResult
```

V1 不做 metric 名称↔code 的映射接口（`metricOptions`）：`metric_values` 传 None 即返回该公司该期所有指标，由 LLM 直接读。

### 3.4 `financial_statements_api.py` — 干净投影 + 修正 type 枚举

- **修正 `StatementType`**：现为 `Literal["entry","financial_forecast","system"]`，但 Java/前端实际用 **`entry` / `forecast` / `system`**。改为 `Literal["entry","forecast","system"]`（开发时先 grep `FinancialQueryCriteria` / Controller 核实 Java 接受值，以 Java 为准）。
- **新增投影函数** `build_financial_metric_view(parsed) -> list[dict]`：从 `meta.headers` + `rows[{text,data,unit,id}]` 产出
  ```
  [{ "label": text, "unit": unit, "id": id, "periods": { headers[i]: data[i] } }, ...]
  ```
  让工具层返回扁平、带标签、按期对齐的结构，消除"重复指标"困惑（一个指标一行，权威源单一来源）。
- 修正 `from_date` 默认值：现硬编码 `"2025-01-01"`（已过期）。工具层改为按运行期 `datetime` 取当年 1 月 1 日（或最近 12 个月起点），不在实体里写死年份。

### 3.5 `benchmark_api.py` — 补全聚合所需字段

`_parse_benchmark_data` 当前只透传 `type/company_id/company_name/months/company_metrics/external_benchmarks/peers`。**移植 calc 必须的额外字段需补全**：`peer_metrics`、`peer_group_info`、`data_sources`、`benchmark_sources`、`company_arr`。`BenchmarkData` 增加对应字段（全 Optional）。

### 3.6 `__init__.py`

新增导出：`CompanyDetailParams/CompanyDetail/CompanyDetailResult/query_company_detail`、`NormalizationTraceParams/NormalizationTraceItem/NormalizationTraceResult/query_normalization_trace`、`build_financial_metric_view`，以及 benchmark 新字段实体（沿用 `BenchmarkData`）。

---

## 4. Benchmark 评分移植（`source/chatbot/tools/_benchmark_scoring.py`，新）

**忠实移植**前端 `calc/` 全部纯函数（不引第三方库，纯 Python），逐文件对应：

| Python 函数 | TS 来源 | 要点 |
|------|------|------|
| `parse_benchmark_value` / `round_to` / `format_percentile_display` | numberParse.ts | `%→/100`、`K/M/B`、`months` 后缀；四舍五入 2 位；`~P/<P25/>P75/>P50/<P50` 展示 |
| `compute_internal_percentile(target, peers, is_reverse)` | percentile.ts | N==1→P100；全等→totalTie(None)；标准竞争排名；`(R-1)/(N-1)×100` |
| `compute_external_percentile(v, bv, is_reverse)` + 4 个 case | externalPercentile.ts | Case A/B/C/D；`effective_is_reverse = reverseIndicator ?? is_reverse`；`needs_reversal = eff & !is_reverse → 100-p` |
| `classify_runway` / `compute_runway_value` / `compute_runway_percentile` | runway.ts | 4 档分类 + 位置排名（非竞争排名）；TOP=P100/BOTTOM=P0 |
| `METRICS` / `CATEGORIES` 常量 | metrics.ts | 6 指标 + 4 卡片；维度顺序 BENCHMARK 外层、DATA 内层 |
| `aggregate(raw, selected_categories=None)` | aggregate.ts | metric×dimension 月度百分位→均值；卡片维度点=卡内各指标该维度均值；卡片分=维度点均值（round）；Overall=可见卡片分均值；`quartile_of`（≥75/50/25） |

**对外产出**（`aggregate` 返回 dict，供工具直接给 LLM）：
```python
{
  "overall_score": {"percentile": 17.0, "display": "17%ile", "quartile": "BOTTOM_QUARTILE", "metric_count": 6},
  "categories": [
    {"name": "Revenue & Growth", "score": 12, "quartile": "...", "scoreDisplay": "~12%ile",
     "metrics": [{"name": "ARR Growth Rate",
        "dimensions": [{"dataSource":"ACTUALS","benchmarkSource":"INTERNAL_PEERS",
                        "percentile": 30, "percentileDisplay":"P30","companyValue": 0.12}, ...12项]}]},
    ... 4 卡片
  ],
  "dimension_summary": [ {dataSource, benchmarkSource, percentile, percentileDisplay}, ...12 ],
}
```

V1 固定 `selected_categories = 全部 4 类`（对应页面 FILTER=ALL），不暴露 FILTER 子集。Runway 展示值直接取接口 `monthlyRunway`（与前端一致），但**内部百分位仍用 cash/burn 分类**（calc 现行为）。

附 `pytest` 单测：用 1~2 组构造样本（含正常值/全等 totalTie/外部插值/runway 分类/reverse 指标），断言关键百分位与展示串，作为"与前端不漂移"的回归基线。

---

## 5. 工具层设计（`source/chatbot/tools/`）

| 工具函数 | 签名 | 行为 |
|------|------|------|
| `list_companies` | `(auth_token)` | **改用** `query_portfolio_companies`（ACL 列表，修复越权泄露），返回 `[{id,name}]` |
| `get_company_detail`（新） | `(*, company_id, auth_token)` | `query_company_detail` → 公司简介/币种/状态等 |
| `query_financial` | `(*, company_id, auth_token, from_date=None, type="entry", view="Annually")` | 调权威源；返回 `{ok, metric_view:[...], structure_description, raw}`；`from_date` 动态默认；`type∈{entry,forecast,system}` |
| `query_benchmark` | `(*, company_id, auth_token, date=None, type="SNAPSHOT", data_sources=None, benchmark_sources=None)` | 调原始 `/data` → `aggregate()` → `{ok, scorecard, structure_description}`；透传过滤参数 |
| `query_normalization`（新） | `(*, company_id, auth_token, date=None, metric_values=None, data_types=None, page=1, size=20)` | `query_normalization_trace(company_ids=[company_id], ...)` → 溯源条目 |

身份信息（user_id / role / 可访问公司）不单设工具：已在图 state（`accessible_companies` 等），由节点注入 synthesis 上下文 + prompt 说明即可。

---

## 6. 对话图改动（`source/chatbot/graph/`）

- `state.py` — `Intent` Literal 增加 `"normalization"`。
- `prompts.py` — `CLASSIFY_SYSTEM` 增加 `normalization` 意图描述（"数据溯源/为什么这个数是这样/原始值与折算"）；`SYNTHESIS_SYSTEM` 增补："身份与公司范围来自 context.identity / context.accessible_companies；财务/benchmark/normalization 数字只能来自工具结果，不得臆造或自行重算。"
- `tool_schemas.py` — 更新 `TOOL_SCHEMAS`：`query_financial` 明确 `type` 枚举 `entry|forecast|system`；`query_benchmark` 增 `date`、`data_sources`(枚举 ACTUALS/COMMITTED_FORECAST/SYSTEM_GENERATED_FORECAST)、`benchmark_sources`(枚举 INTERNAL_PEERS/KEYBANC/HIGH_ALPHA/BENCHMARK_IT)；新增 `get_company_detail`、`query_normalization`。同步 `dispatch_tool` 分支（`company_id`/`auth_token` 仍由 state 强制注入，禁止 LLM 传公司身份）。
- `chat_graph.py` — 注册 `call_normalization` 节点 + 条件边（intent==normalization）。
- `nodes.py` — `call_company` 注入身份 + 可访问公司 + 活跃公司详情；`call_financial` 用干净投影；`call_benchmark` 返回 scorecard；新增 `call_normalization`。

---

## 7. 改动文件清单

**新增**：
- `source/lgpi_api/company_detail_api.py`
- `source/lgpi_api/normalization_trace_api.py`
- `source/chatbot/tools/_benchmark_scoring.py`（+ 单测 `tests/chatbot/tools/test_benchmark_scoring.py`）
- `source/chatbot/tools/normalization_tool.py`

**修改**：
- `source/lgpi_api/_http.py`（+`post_json`）
- `source/lgpi_api/financial_statements_api.py`（type 枚举 + 投影函数）
- `source/lgpi_api/benchmark_api.py`（补 peer_metrics/peer_group_info/data_sources/benchmark_sources/company_arr）
- `source/lgpi_api/__init__.py`（导出）
- `source/chatbot/tools/company_tool.py` / `financial_tool.py` / `benchmark_tool.py`
- `source/chatbot/graph/state.py` / `prompts.py` / `tool_schemas.py` / `chat_graph.py` / `nodes.py`

---

## 8. V1 明确不做（YAGNI / 风险控制）

- 不新增任何 Java 接口、不动前端、不动 DB（全部基于既有 `/api/web/*` 接口）。
- benchmark 不暴露 FILTER 子集（固定 ALL）、不做 TREND 折线聚合（仅 SNAPSHOT 评分；TREND 原始值可透传但不出折线视图）。
- normalization 不做 metric 名称↔code 映射接口（传 None 取全量）。
- 不切换到 tool-calling loop 编排（保留确定性路由）。
- 不做跨公司聚合、不做写操作、不做记忆层。
