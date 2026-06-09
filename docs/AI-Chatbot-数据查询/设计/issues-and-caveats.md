> 关联文档: [设计文档](./design-doc.md)

# AI Chatbot 数据查询能力 V1 — 注意事项与已知问题

本文件记录第一版交付后需要关注、复核、后续处理的问题。按严重度排序。完成后逐项处理。

## ★ 真实环境验证结果（2026-06-09，admin-test.lgpi.io + 真实用户 token）

已用真实用户 token 对 Helen Company 02（`1a9e8321-...856fe`）**端到端跑通工具层全部四类能力**：

| 能力 | 结果 |
|------|------|
| ① 公司详情 | ✅ `Helen Company 02` / EUR / status=4 / type=1，解析正确 |
| ② 财务指标 | ✅ entry 返回真实月度值（Gross Revenue Aug=800、ARR、Rule of 40 等）；`type=forecast`/`system` 返回空（该公司无承诺/系统预测数据，与页面"Forecast Horizon below 24 months"一致）。`type` 枚举修正生效 |
| ③ benchmark 评分 | ✅ **Overall(Actuals × Internal Peers) = 17%ile，与页面截图精确一致**；quartile=BOTTOM_QUARTILE 也对上。全 12 维则为 33%ile |
| ④ normalization 溯源 | ✅ 默认返回 31 条真实溯源（`Revenue: std=7.03USD ← Gross Revenue 6.00EUR, formula "Revenue = Gross Revenue * FX Rate"` 等） |

回归单测 111 个全过。下列为验证过程中**已修复**与**仍需关注**的项。

## ★ ACL/授权决策（2026-06-09，已实现）

经核实并由产品拍板：**chatbot 不做公司级授权**，授权交平台/Java（Java 数据接口当前无公司级授权=平台侧 IDOR，列为平台待办，非 chatbot 范围）。chatbot 侧据此改动（单测 154 全过）：

- **端类型判别**：由 **Redis `company_id`** 判定，**不信前端 `x-chat-end`**（可伪造）。已核实（Java 源码 + 真实 token）：仅超管（roleType=1）创建时不设 `company_id`，roleType 2~5 必有；故 `company_id` 有值=公司端、为空=超管。`organizationId`（两端都有）、`authorities`（权限码、cache-miss 退化空）均不可靠，不用于判端。
- **移除授权闸门**：删除 `graph` 的 `derive_scope` 节点与 `acl.py` 的 `enforce_company_scope`/`accessible_company_ids`；请求路径不再取"可访问集"做校验。
- **active 公司（身份路由，非授权）**：公司端 = Redis `company_id`（忽略前端传入 company_id，故公司用户天然只能看本司）；超管 = 前端所选公司（超管本就全可见）。
- **公司列表来源**：`acl.accessible_companies` 仅供 `/companies` 选择器；超管改用 **`/invite/query`**（`/invite/portfolio` 损坏：需 group、非用户作用域；`/invite/getList` 服务端 NPE）。
- **延后（公司处理）**：管理端"按公司名解析→id""选择器全量 333 注入合成上下文"等暂不处理；`company_tool.list_companies` 工具仍指向损坏的 `/invite/portfolio`，待统一到 `/invite/query`。

### 验证中已修复
- **benchmark runway 字符串崩溃**：接口将 `monthlyNetBurnRate`/`ruleOf40` 按字符串下发（保大整数精度），`classify_runway`/`compute_runway_value` 对字符串调 `math.isfinite` 抛 `TypeError`。已加 `isinstance` 守卫，对齐前端 `Number.isFinite("x")=false` 语义（非数值→视为缺失）。
- **后端忽略维度过滤**：`/benchmark/.../data` **始终返回全部 12 维**（忽略请求的 `dataSources`/`benchmarkSources`），过滤须在客户端做。`aggregate()` 已支持 `data_sources`/`benchmark_sources` 覆盖，`benchmark_tool` 透传请求的过滤 → 评分卡按实际选择裁剪（这才让 Overall 能对上页面的 17%ile）。
- **normalization 默认查空**：Java 端 `metricValues` 为空时返回空 Page。已新增 `normalization_metric_options_api`，`query_normalization` 在未指定指标时先拉全部 code 再查（默认即返回全部指标溯源）。

## A. 必须在真实环境验证（代码已写，未跑通真实链路）

单测（111 个：评分 73 + lgpi_api 38）与导入/图编译全部通过，但**未对接真实 Java/Redis 做端到端验证**（需 DB + SQS + Redis 会话 + 真实用户 token）。下列均已对照 Java 源码核实字段，但未经真实调用：

1. **`/invite/{id}` 返回结构**：`CompanyDetail` 按 `InviteDto` 字段映射（`company`→name、`companyStatus`/`type`/`category`/`revenueRecognition` 等）。需真实调一次确认 `data` 信封层级（是否 `{success,data:{...}}`）与 `description` 是否真有值。
2. **`metricTrace` 响应**：按 `PageResponse{content,totalElements}` 解析。需确认实际信封是否 `{success,data:{content,totalElements}}`；以及 `date`/`metricValues` 传 None 时 Java 是否返回全量而非空 Page（Java 对空 companyIds/metricValues/date 可能直接返回空 Page —— 若如此，normalization 工具需要总是带 `date`）。
3. **财务 `type=forecast`**：原 Python 用的是错误值 `financial_forecast`，本次按 Java/前端改为 `forecast`。**这是一个潜在 bug 修复**——此前 chatbot 查 Committed Forecast 很可能拿不到数据。需真实验证 `forecast`/`system` 两种 type 能正确返回。
4. **benchmark 内层 data 形状**：`aggregate()` 直接吃 `/data` 响应的 `data` 字段（camelCase：`companyMetrics`/`peerMetrics`/`externalBenchmarks`/`dataSources`/`benchmarkSources`/`months`/`peers`/`peerGroupInfo`）。需真实响应核对键名与嵌套（尤其 `externalBenchmarks[].values` 与 `year`/`benchmarkSource`/`metricId`/`found`）。

## B. Benchmark 评分移植的固有风险

5. **与前端 calc/ 的同步风险（最重要）**：百分位/Overall/卡片分由 `_benchmark_scoring.py` **移植自前端 `src/pages/companyFinance/benchmark/calc/`**。前端 calc 一旦改动，Python 侧会**静默漂移**。建议：① 在前端 calc 目录加注释指向本 Python 文件；② 中长期把聚合下沉到 Java 服务端（`BenchmarkingServiceImpl` 已有同源 calculator），chatbot 直接取服务端算好的分，彻底消除双份逻辑。
6. **舍入差异**：Python `round()` 为银行家舍入，JS `Math.round()` 为 0.5 向上。极少数 `.5` 边界百分位可能与页面差 1。影响极小，但对账时若出现 ±1 个百分位差异属预期。
7. **benchmark 默认维度 = 全 12 维（Overall 33%ile）**：因后端忽略过滤、恒返 12 维，`query_benchmark` 不传 `data_sources`/`benchmark_sources` 时 `aggregate` 按全 12 维算 → Overall=33%ile。**页面上的数字取决于用户当前选了哪些 DATA×BENCHMARK**（如截图 Actuals×Internal Peers=17%ile）。chatbot 无法得知用户 UI 的即时勾选，故默认给"全维度综合分"；要复现某个具体页面视图，需让工具带上对应的 `data_sources`/`benchmark_sources`。是否把默认改成"Actuals × 全源"或其它更贴近用户预期的口径，待产品确认。
8. **Runway 维度的 companyValue**：`met-runway` 展示值取接口 `monthlyRunway`（常为 null），但百分位用 cash/burn 4 档分类（与前端一致）。故 runway 维度的 `companyValue` 可能为 null 而 percentile 有值，属正常。
9. **TREND 未做折线**：`type=TREND` 可透传，但 `aggregate()` 对多月取均值（与前端 SNAPSHOT 聚合口径一致），**不产出趋势折线**。趋势视图属后续。
10. **FILTER 固定 ALL**：V1 不暴露 GROWTH/EFFICIENCY/MARGINS/CAPITAL 子集过滤，Overall 恒为 4 卡片均值。

## C. 行为变更与范围

11. **⚠️ `/invite/portfolio` 需要 portfolio 上下文（待解决）**：验证发现用浏览器 admin token 直调 `/invite/portfolio` 返回 `success=false: "Please select a portfolio"`（缺 `companyGroupId`）。这意味着：① 我把 `list_companies` 从 `/invite/query` 改为 `/invite/portfolio`（ACL）后，admin 端无 group 上下文时会取不到列表；② 既有 `auth/acl.py` 的 `accessible_companies` 也用 portfolio，同样依赖该上下文。真实 chatbot 会话可能携带 group 上下文（或 company 端用 home_company 不需要列表）。**需在真实 chatbot 会话里确认**；若 admin 端确需公司列表，应传 `companyGroupId` 或回退 `/invite/query`。
12. **身份信息较薄**：synthesis 上下文里的 `identity` 只有 `user_id` + `org_id`（来自 Redis `AuthUser`），**没有姓名/邮箱/角色名**（页面顶部"Super Admin wenchao chen"那种）。如需友好身份展示，要加 `/users/current` 客户端。属增强项。
13. **normalization 名称→code 映射（已部分解决）**：`metric_values` 为枚举 code（`REVENUE`/`ARR`...）。已新增 `normalization_metric_options_api`，`query_normalization` 未指定指标时自动拉全部 code 再查（默认即返回全部指标溯源，已验证 31 条）。**剩余增强**：若希望用户用自然语言点名单个指标（"看看我的现金怎么折算的"），需在工具里把 metricOptions 的 label 做模糊匹配 → code 传入；当前是"全量返回由 LLM 自行挑"。
14. **`from_date` 默认当年 1 月 1 日**：不再硬编码 2025。若公司数据不在当年，可能返回空——LLM 应据 `structure_description` 提示用户给时间范围，或后续改为按"最近 12 个月/最新有数月份"动态取。

## D. 编排与安全

15. **保留确定性路由，未启用 tool-calling loop**：`tool_schemas.py`/`dispatch_tool` 已同步全部新工具（loop 路径可用），但对话图仍走确定性单意图路由。**多数据域组合提问**（如"对比我的 Rule of 40 实际值、benchmark 分位、以及它的折算来源"）在 V1 只会命中单一意图节点。若要组合，需将 `tool_calling_loop` 挂入图（后续）。
16. **公司身份强制由 state 注入**：`dispatch_tool` 的 `company_id`/`auth_token` 一律来自 state，不信任 LLM 传参（防越权）。新增工具已遵守。
17. **`DEFAULT_BEARER_TOKEN` 硬编码**（`common/config/lgpi.py`，既有）：auth_token 为空时回退该 service token。chatbot 链路始终透传用户 token，不会用到；但该硬编码 token 本身是既有安全债，建议清理为纯环境变量。

## E. 测试与后续

18. 已加单测：`tests/chatbot/tools/test_benchmark_scoring.py`（73 个，纯函数）、`tests/lgpi_api/`（38 个，mock httpx）。**缺**：工具层与图节点的集成测试（mock lgpi_api，验证 call_* 节点产出与 build_synthesis 上下文）。
19. 建议补端到端冒烟：用一个真实 admin token + 截图里的 company（`1a9e8321-60e5-4332-b963-978713a856fe`，Helen Company 02）跑通四类问题，核对 benchmark Overall 与页面 17%ile、财务数值与 Financial Statements 表是否一致。
