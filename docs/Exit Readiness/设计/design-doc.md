> 关联文档：
> - 原型（Lovable，已发布）：`https://exit-readiness-hub.lovable.app`（项目 `exit-readiness-hub` / Readiness Compass）
> - 后端规范：[../../../CIOaas-api/standards/architecture.md](../../../CIOaas-api/standards/architecture.md) · [../../../CIOaas-api/standards/coding.md](../../../CIOaas-api/standards/coding.md)
> - Python 规范：[../../../CIOaas-python/standards/architecture.md](../../../CIOaas-python/standards/architecture.md) · [../../../CIOaas-python/standards/coding.md](../../../CIOaas-python/standards/coding.md)
> - 前端规范：[../../../CIOaas-web/standards/architecture.md](../../../CIOaas-web/standards/architecture.md) · [../../../CIOaas-web/standards/coding.md](../../../CIOaas-web/standards/coding.md)
>
> 阶段：④ 设计 | 版本：v2.1-draft | 日期：2026-08-26 | 范围：ERL 展示 / 填报 / 配置 / 基准 + Goldie 差距分析 + 组合层 ERL 总表

# Exit Readiness（ERL）设计文档 V1

**v2 变更（2026-08-26）**：范围新增 **E1**（Gap Analysis & Suggested Actions）、**E2**（每维 Strengths & Priority Gaps）、**F2**（Portfolio 列表 ERL Tab）。因 E 引入 LLM 生成，后端由"仅 Java"改为 **Java 为唯一前端出口 + Python 只负责生成**——此项**已于 2026-08-26 确认**（§13-Q8）。另修正 v1 中三处对原型的误述（§2.4、§2.6）。

**v2.1 变更（2026-08-26）**：确认三项口径——① Q8 后端落点（Java 唯一出口 + Python 纯生成）；② **`YES_NO` 题不折算、不计分**（改 §5.3 表结构为 `score` / `yes_no` 双列互斥，新增 §7.1.1「计分范围 ≠ 完成度范围」）；③ **Era 分段以 1–3 / 4–6 / 7–9 为准，原型 FRL 6.4 标 Exit Era 是 bug**（新增 §7.1.2 精确边界 + 交叉验证）。§13-Q2 收窄为只剩 Grade 分档表一项。

> **跨项目协作模式（本功能新增第三种）**：根 `CLAUDE.md` 现记录两种 Java↔Python 协作模式——智能解析走 SQS 异步、AI Chatbot 走 HTTP 经网关 + SSE 流式。ERL 差距分析是第三种：**HTTP 经网关 + 同步非流式**（单次秒级调用，Java 落库缓存）。实现落地后建议把该模式补记进根 `CLAUDE.md` 的「跨项目协作模式」章节。

---

## 0. 一句话目标

把 Lovable 原型 `exit-readiness-hub` 的**退出准备度（Exit Readiness Level, ERL）**能力移植进 LG 平台：公司端 Founder 自评、GSV 端验证评估，五个维度按 1–9 分打分，产出维度分 / 综合分 / 双方认知差（Perception Gap），与 Benchmarkit、Top GSV Quartile 两条外部基准对比；由 Goldie 生成每维优势与差距并合成三条行动洞察；题库管理端可配置；组合层提供跨公司 ERL 总表。

---

## 1. 范围与分期

### 1.1 V1 范围（本文档）

| 模块 | 功能点 | 在 V1 | 说明 |
|------|--------|:-----:|------|
| A 展示 | A1 ERL 总览仪表盘 | ✅ | 综合分 + 所处 Era + 五维卡片（分数 / 线性比例条 / Era / Perception Gap） |
| A 展示 | A2 Dimension Radar 雷达图 | ✅ | 4 条序列：Founder / GSV / Benchmarkit / Top GSV Quartile |
| A 展示 | A3 单维度模板页 | ✅ | **一套模板 5 维复用**，`dimension` 参数驱动 |
| A 展示 | A4 Score Details 全维明细页 | ✅ | 五维合一、可折叠、Founder / GSV 双 Tab |
| A 展示 | A5 "How It's Scored?" 评分标准弹窗 | ✅ | 展示该题三段 Era 的评分标准 |
| B 填报 | B1 Founder 自评问卷 | ✅ | 165 题、期次选择、进度、实时均分、自动存草稿、提交 |
| B 填报 | B2 GSV 验证问卷 | ✅ | 同结构，GSV 端提交，带 Fund / 评估团队 |
| B 填报 | B3 评估历史列表 | ✅ | 期次 / 端 / 提交时间 / 提交人 / 完成度 / 总分 / Era |
| C 配置 | C1 题库列表（五维 Tab + Era band 分组） | ✅ | 管理端 |
| C 配置 | C2 新增题目 | ✅ | 维度 / Era band / 题干 / 证据来源 / 三段式评分标准 |
| C 配置 | C3 编辑 / 删除题目 | ✅ | 删除二次确认 |
| D 基准 | D1 基准记录页 | ✅ | 两条基准最新值 + 环比 + 历史记录表 |
| D 基准 | D2 新增基准记录 | ✅ | 期次 + 两个 1–9 分值 + 备注 |
| **E AI** | **E1 Gap Analysis & Suggested Actions** | ✅ **v2 新增** | summary 段落 + 三条洞察卡（Key risk signal / Value lever / Next 90 days）。**三条洞察由后端按规则合成，不进 LLM**（§7.3） |
| **E AI** | **E2 每维 Strengths & Priority Gaps** | ✅ **v2 新增** | LLM 生成：每维 `strengths[]` + `gaps[{title, note, severity}]`；渲染在 A3 维度页，同时是 E1 的数据源 |
| **F 联动** | **F2 Portfolio 列表 ERL Tab** | ✅ **v2 新增** | 跨公司 ERL 总表：Company / ERL Score / FRL / PRL / BERL / RRL / TRL / Stage / View |

### 1.2 明确不在 V1

| 项 | 原因 / 去向 |
|----|-------------|
| E3 顶栏 Ask Goldie 对话接入 | 与 AI Chatbot 是另一条产品线，推 V2 |
| F1 Finance 页 Exit Readiness 卡片与入口 | 推 V2；**但 A3 入口需另解**，见 §8.5 与 §13-Q7 |
| F3 `?from=finance\|readiness` 面包屑回跳 | 依赖 F1，推 V2 |
| A6 BPMM 卡片 | 原型中即为 `Business Process Maturity Model placeholder`，无定义内容 |
| 原型 out-of-scope 项：Needs Attention 面板、Data Sources & Cadence 卡、Export Report / Full Diagnostic / View All | Lovable story 原文即标注不在 MVP |
| `?variant=b` | 原型的演示开关，非业务功能（语义见 §2.5） |
| 评估版本 diff / 期次间对比 | B3 只做列表，不做版本比对 |
| Goldie 生成结果的人工编辑 / 审核流 | 见 §13-Q11，确认后再定 |
| 题库导入导出、题目排序拖拽 | 无需求 |

### 1.3 后续阶段索引

| 阶段 | 内容 |
|------|------|
| V1（本文档） | A / B / C / D + E1 / E2 + F2 |
| V2 | E3（Ask Goldie 接入）+ F1 / F3（Finance 页卡片与回跳） |

---

## 2. 现状事实（原型探查所得，均有证据）

> 探查方式：该 Lovable 项目对当前账号是 collaborator 身份，`get_project` / `list_files` 返回 403；改为抓取已发布站点（TanStack Start **SSR**，`https://exit-readiness-hub.lovable.app`）的路由 chunk 与各路由渲染 HTML 还原。

### 2.1 原型路由与页面（14 条）

| 原型路由 | 页面 | 对应功能点 |
|----------|------|-----------|
| `/portfolio`（`/` 重定向） | Portfolio Companies 列表（Tab：General / Connections / Issues / Benchmarking / **ERL**） | **F2（已实现，见 §2.4-③）** |
| `/finance` | Finance 工作台（Exit Readiness 导航项；`?variant=b` 时额外出 ERL 五维卡片） | F1（不做） |
| `/readiness/` | Exit Readiness Dashboard | A1 / A2 / **E1** |
| `/readiness/$dimension` | 单维度页 | A3 / **E2** |
| `/readiness/overall` | Score Details | A4 |
| `/readiness/benchmark/` | Top GSV Quartile & Benchmarkit | D1 |
| `/readiness/benchmark/add` | 新增基准记录 | D2 |
| `/assessments/erl` | Founder 自评问卷 | B1 |
| `/assessments/gsv` | GSV 验证问卷 | B2 |
| `/assessments/history` | 评估历史 | B3 |
| `/erl-configuration/` | 题库列表 | C1 |
| `/erl-configuration/add` | 新增题目 | C2 |
| `/erl-configuration/edit/$id` | 编辑题目 | C3 |

### 2.2 领域常量

- **5 维度**：`FRL` Financial Readiness / `PRL` Product Readiness / `BERL` Brand Equity Readiness / `RRL` Risk Readiness / `TRL` Talent Readiness
- **3 个 Era**：Founder Era（1–3 分）、Harvest & Growth（4–6 分）、Exit Era（7–9 分）
- **题目 Era band**：题库配置页的下拉为 **9 档**——`Founder Era - 1/2/3`、`Harvest & Growth - 4/5/6`、`Exit Era - 7/8/9`
- **题量**：FRL 31 题；五维合计 **165 题**（自评页进度条 `0 of 165`）
- **答题形态两种**：`Answer Yes or No`（如 FRL 首题）与 `Score the highest stage where criteria are substantially met`（1–9 打分器）。**`YES_NO` 题必答但不计分**（2026-08-26 已确认，§7.1）
- **每题固定属性**：`Source`（证据来源，如 `Founder / CFO`、`Looking Glass`）、三段式 `Scoring criteria`
- **gap 的 severity 取值**：原型出现 `high` / `medium`

### 2.3 已核实的计算口径

| 结论 | 证据 |
|------|------|
| **仪表盘上展示的"维度分"是 GSV 分，不是 Founder 分** | FRL `score=6.4`、`founderSelfScore=7.8`，页面显示 `Perception Gap: Positive 1.4` = 7.8 − 6.4 |
| **Perception Gap = Founder 分 − GSV 分** | 五维全部吻合：PRL 7.4−5.1=2.3、BERL 8.1−7.5=0.6、RRL 7.0−4.6=2.4、TRL 5.2−2.8=2.4 |
| **综合分 = 五个维度分的简单平均** | (6.4+5.1+7.5+4.6+2.8)/5 = 5.28 → 页面显示 `5.3 /9` |
| 基准为**两条独立序列**、按期次存历史 | D1 页记录表：Q2 2026 Benchmarkit 6.8 / Top GSV Quartile 7.9，含 `+0.3 vs prior` 环比 |

### 2.4 原型与 Lovable story 验收标准的差异

**① A3 维度页缺了大半个 story**

story 要求单维度模板页包含：score card 头（分数 + 等级 + Founder 自评分 + Perception Gap + 基准位置）、Dimension Intelligence 卡（三 Era 拆分）、Perception Gap 区、Strengths & Priority Gaps、维度图表、分 Era 题目表。

**实际原型的 `/readiness/$dimension` 只实现了最后一项**——页头（维度名 + 题数 + 分数）+ Founder/GSV 双 Tab + 提交元信息 + 逐题列表。经关键词核验：该页 HTML 中 `Perception Gap`、`Intelligence`、`Strengths`、`Radar` 命中数均为 **0**。

→ **本设计以 story 为准**，把 score card 头、Dimension Intelligence、Perception Gap、维度图表、Strengths & Priority Gaps（E2）全部补齐到 A3。见 §13-Q1。

**② A3 页在原型里不可达**

- Dashboard 的五个维度行**没有链接**（整页唯一 readiness 内链是 `/readiness/overall`）
- 唯一的 `View Details → /readiness/$dimension` 写在 **Finance 页**的 ERL 卡片里，而该卡片**只在 `?variant=b` 时渲染**（实测 `/finance?company=anz` 中 `Financial Readiness` 命中 0，`/finance?variant=b&company=anz` 命中 1）

→ F1 不做则 A3 无入口，本设计的解法见 §8.5。

**③ Portfolio ERL Tab 已实现（修正 v1 的误述）**

v1 文档记为"内容未实现"，**有误**。该 Tab 是完整表格（`js/portfolio-DAxrYMTr.js`）：

| 列 | 内容 |
|----|------|
| Company | 公司名 |
| ERL Score | `x.x/9`，按分数着色 |
| FRL / PRL / BERL / RRL / TRL | 各维度分，1 位小数 |
| Stage | 徽章，标签与配色由综合分推导 |
| （末列） | `View →` 链接到 `/readiness?company={id}` |

8 家演示公司各有一行数据。F2 的工作量因此比 v1 估计的大。

### 2.5 演示数据的真实分布

| 事实 | 证据 |
|------|------|
| Example 1（`id=anz`）是**默认演示公司**，原型里唯一一份完整 ERL 数据 | 不带参数访问 `/readiness/` 面包屑即 `Example 1` |
| Example 2 只是**同一份数据换个公司名** | `/readiness/` 与 `/readiness/?variant=b` 整页 diff 只差一行公司名，五维分一字不差 |
| ERL 页面上 `company` 参数**不生效** | `/readiness/?company=conn` 面包屑仍是 `Example 1` |
| `variant=b` 是**双重开关**：在 `/readiness/*` 上换公司名（数据不变）；在 `/finance` 上额外解锁 ERL 五维卡片 + Gap Analysis | 见 §2.4-② 的实测 |
| **Portfolio ERL Tab 与 Dashboard 的 ERL 分数互相矛盾** | Example 1 在 ERL Tab 是 综合 7.2 / 7.5 / 6.8 / 7.0 / 7.4 / 6.9；在 Dashboard 是 综合 5.3 / 6.4 / 5.1 / 7.5 / 4.6 / 2.8。两份 mock 各写各的，无共同数据源 → 见 §13-Q9 |

### 2.6 E1 / E2 的实现性质（关键，决定架构）

原型的 `GoldieSuggestion` 组件（`js/GoldieSuggestion-COALm4CD.js`）由三部分组成：

| 部分 | 原型实现 | 是否需要 LLM |
|------|----------|:---:|
| **summary 段落** | Dashboard 与 Finance **都没传** `summary` prop → 页面显示的是组件内**硬编码兜底文案**（完整版 + compact 版两套） | 待定，见 §13-Q10 |
| **三条洞察卡** | Dashboard 传 `signals: p(E)`、Finance 传 `h(n)`，两者都是**确定性规则函数**——从五维的 `strengths` / `gaps` / `score` 算出，规则已完整反解（§7.3） | ❌ **不需要** |
| **空态** | `signals.length === 0` 时显示 `No gap analysis yet` + `Goldie needs scored questions with evidence notes for this dimension before it can suggest gaps and recommended actions.`（文案含 "for this dimension"，该组件本就为单维度页设计） | — |

每维的 `strengths[]` 与 `gaps[{title, note, severity}]` 在数据模型上**确实存在**（BERL 有 3 条 strengths、2 条 gaps），但全站 14 个路由的渲染 HTML 中 `Strengths` / `Priority Gaps` 字样命中 **0** —— 即 E2 在原型里**只有数据、没有 UI**，唯一消费方就是上面那三条洞察卡。

**结论**：真正需要 LLM 的只有 **E2 的 strengths / gaps 文本**（外加可选的 summary 段落）；E1 的三条洞察卡是纯规则层。这把 AI 的暴露面压到最小。

另注：原型渲染路径上 **`gap.note` 与 `severity='medium'` 的条目从未被消费**（只有第一条 `severity='high'` 的 gap 进了文案）。本设计把 `note` 用在 A3 的 gaps 条目里（E2 有 UI 后就有去处）。

### 2.7 原型无后端

全部数据为前端硬编码 mock，**无接口、无表结构**——数据模型与接口契约由本文档首次定义。

---

## 3. 架构总览

### 3.1 落点

```
CIOaas-web (React 16 / UmiJS 3 / AntD Pro)
   src/pages/exitReadiness/**              ERL 页面群（8 个路由页）
   src/pages/portfolioCompanies/**         F2：列表页新增 ERL Tab（改存量页）
   src/services/api/exitReadiness/         HTTP 调用（1:1 后端接口）
   src/services/service/exitReadiness/     Response ↔ DTO 转换
        │
        │  /api/web/erl/**            ← 前端只调 Java，不直连 Python
        ▼
Gateway :9000  ──►  CIOaas-web(Java) :5213/web
                        com.gstdev.cioaas.web.erl/      ← 新建业务域，DDD 四层
                        │       │
                        │       │  POST /api/ai/erl/gap-analysis（经网关，同步 HTTP）
                        │       ▼
                        │  CIOaas-python  source/erl/     ← 仅负责 LLM 生成，不落库
                        │                 └─ 复用 source/llm/ 基建
                        │                 └─ prompt 放 source/ai/prompts/
                        ▼
                   PostgreSQL
                     erl_question / erl_assessment / erl_assessment_answer
                     erl_benchmark_record / erl_gap_analysis / erl_gap_analysis_item
```

- **前端只有一个后端出口**（Java），不出现前端直连 Python 的路径。
- Python 侧**不落库、不做公司 ACL**（Java 已校验），是一个纯生成服务。
- 不使用 SQS：ERL 的 LLM 调用是单次秒级，理由见 §3.2。

### 3.2 关键决策与理由

| 决策 | 理由 | 否掉的替代方案 |
|------|------|----------------|
| 新建 Java 业务域 `erl/`，走 **DDD 四层** | `standards/architecture.md` §1 强制；`quickbooks/`、`thirdParty/` 已是四层实现可作参照 | ❌ 仿照 `fi/` 的扁平结构 —— 那是历史遗留，不得在新域复制 |
| ERL 不并入 `fi/`（财务域） | ERL 覆盖五个维度，不属财务域 | ❌ 放 `fi/erl/` |
| **E 的 LLM 生成落 CIOaas-python，Java 经网关同步调用**（✅ 2026-08-26 已确认） | Java 侧**零 LLM 客户端**（全仓 grep `bedrock\|anthropic\|openai\|claude` 的命中全是 SQS 消息类）；Python 有 `source/llm/` 完整基建 + Prompt 管理规范 + 调用追踪 | ❌ 在 Java 接 LLM SDK —— 要重建模型配置、Prompt 管理、调用追踪，与 Python 侧完全重复 |
| Java↔Python 走 **HTTP 经网关**，不走 SQS | 单次、秒级、用户可等待；SQS 那套是给分钟级批处理（智能解析）用的 | ❌ SQS 异步 —— 要引入回调队列、任务表、轮询，为一个秒级调用付全套异步成本 |
| **三条洞察卡由 Java 按规则合成**，不进 LLM | 规则已完整反解（§7.3），确定、可复现、零成本；LLM 只负责 strengths/gaps 文本 | ❌ 让 LLM 直接产出三条卡 —— 不可复现、措辞每次漂移、无法写断言测试 |
| Gap analysis **落库缓存 + 前端显式触发生成** | LLM 秒级，Dashboard 首屏不能阻塞；同一份评估的分析结果不变 | ❌ 每次进页面实时生成；❌ 提交评估时后台异步生成 —— 要轮询或推送，YAGNI |
| **维度分、综合分、Era、等级、Perception Gap、三条洞察全部实时计算，不落库** | 题库可增删（C 模块），落库的聚合值会失真；`strengths`/`gaps` 才是需要持久化的 LLM 产物 | ❌ 在 `erl_assessment` 上冗余 `dimension_score` |
| 答案表 `erl_assessment_answer` **一行一题**，不做 JSON 大字段 | 需要按维度 / Era 聚合、按题 join 题库 | ❌ `answers jsonb` |
| 草稿与正式提交**同一条记录**，用 `status` 区分 | 原型"Progress saves automatically — you can leave and return" | ❌ 独立草稿表 |
| 题目删除用**软删除**（`enabled=false`） | 历史评估的答案行指向题目，硬删会让历史无法还原题干 | ❌ 物理删除 |
| Gap analysis 绑定 **`(company_id, period)`** 而非单个 `assessment_id` | 分析要同时读 Founder 与 GSV 两份（Perception Gap 是判断依据之一） | ❌ 绑 GSV 那一份 |
| C2/C3 保持**独立页面**；D2 改为 **Modal** | C 的表单含 3 段长文本；D2 只 4 个字段 | ❌ 全部照搬原型的独立页面 |
| 前端新增 API 域 `exitReadiness/` | `standards/architecture.md` §2 的 24 个域无一匹配 | 需同步登记进 §2 域表，见 §13-Q5 |

---

## 4. 鉴权与端类型

### 4.1 复用现有的两端判定

现有财务页已有的判定方式（`src/pages/financial/home/FinancialPage.tsx:99`）：

```
companyId = user.roleType <= 1 ? getQueryString('id') : user?.inviteDto?.id
```

即：`roleType <= 1` 为管理端（GSV），公司从 URL `?id=` 取；否则为公司端（Founder），锁定本公司。ERL 沿用同一套，**不新增端类型机制**。

### 4.2 页面与端的对应

| 页面 | 公司端（Founder） | 管理端（GSV） |
|------|:---:|:---:|
| A1 / A2 / A3 / A4 展示页 | ✅ 只看本公司 | ✅ 看所选公司 |
| **E1 / E2 差距分析（展示）** | ✅ 只读 | ✅ 只读 |
| **E 生成 / 重新生成** | ❌ 不可触发 | ✅ 仅管理端 |
| B1 Founder 自评问卷 | ✅ **填报** | ✅ 只读查看 |
| B2 GSV 验证问卷 | ❌ 不可见 | ✅ **填报** |
| B3 评估历史 | ✅ 只看本公司 | ✅ |
| C1 / C2 / C3 题库配置 | ❌ 不可见 | ✅ |
| D1 基准记录 | ✅ 只读 | ✅ |
| D2 新增基准 | ❌ | ✅ |
| **F2 Portfolio ERL Tab** | ❌ 不可见（跨公司聚合） | ✅ |

### 4.3 后端强制校验（不依赖前端）

- 所有接口的 `companyId` 一律**服务端复核**：公司端请求忽略入参 `companyId`，强制取当前登录用户所属公司（`SecurityUtils`）；管理端才允许按入参取。
- `portal=GSV` 的写入（B2 提交）、C 模块写接口、E 的生成接口、F2 的跨公司查询，服务端一律校验调用者为管理端，否则 `BadRequestException`。
- **F2 只返回当前用户有权访问的公司集**，不返回全库。
- Java→Python 的生成接口带服务间鉴权；Python 侧不重复做公司 ACL，但**必须落 LLM 调用追踪**（复用 `source/llm/`）。
- 违规一律抛异常交 `GlobalExceptionHandler`，**Controller 内不 try-catch**（`standards/architecture.md` §3）。

---

## 5. 数据模型

> 库：PostgreSQL 业务库。Java 侧 `ddl-auto: update` 由 Entity 自动建表；索引/约束/种子数据补 `CIOaas-api/deploy/upgrade_doc/sprint{N}/*.sql`（当前最新 `sprint116`）。所有实体继承 `AbstractCustomEntity`，自动带 `created_at / created_by / updated_at / updated_by`。主键 `String(36)` + `@UuidGenerator`（与 `quickbooks_*` 一致）。

### 5.1 `erl_question` — 题库

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `dimension` | varchar(8) | not null | `FRL` / `PRL` / `BERL` / `RRL` / `TRL` |
| `era_band` | smallint | not null, 1–9 | 题目归属档位；Era 由此推导（1–3 Founder / 4–6 Harvest / 7–9 Exit） |
| `question_text` | varchar(1024) | not null | 题干 |
| `answer_type` | varchar(16) | not null | `SCORE`（1–9）/ `YES_NO` |
| `evidence_source` | varchar(255) | | 证据来源；空显示 `—` |
| `criteria_founder` | varchar(1024) | | Founder Era（1–3）评分标准 |
| `criteria_harvest` | varchar(1024) | | Harvest & Growth（4–6）评分标准 |
| `criteria_exit` | varchar(1024) | | Exit Era（7–9）评分标准 |
| `sort_order` | int | not null | 同 `dimension + era_band` 内的展示顺序 |
| `enabled` | boolean | not null, 默认 true | 软删除标记 |

索引：`idx_erl_question_dim_band (dimension, era_band, sort_order)`。题库**全局单份**，不按公司隔离（见 §13-Q4）。

### 5.2 `erl_assessment` — 一次评估

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | 形如 `2026Q3` |
| `portal` | varchar(8) | not null | `FOUNDER` / `GSV` |
| `status` | varchar(16) | not null | `DRAFT` / `SUBMITTED` |
| `submitted_at` | timestamp | | `SUBMITTED` 才有值 |
| `submitter_name` | varchar(128) | | 提交人姓名快照 |
| `submitter_role` | varchar(128) | | 提交人角色快照，如 `Founder & CEO` |
| `fund` | varchar(128) | | 仅 GSV 端 |

唯一约束：`uk_erl_assessment (company_id, period, portal)`。提交人姓名/角色**存快照**：人员离职或改名后历史记录仍显示当时信息。

### 5.3 `erl_assessment_answer` — 逐题作答

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `assessment_id` | varchar(36) | not null | → `erl_assessment.id` |
| `question_id` | varchar(36) | not null | → `erl_question.id` |
| `score` | numeric(3,1) | **nullable** | 仅 `answer_type = SCORE` 的题有值，1–9 |
| `yes_no` | boolean | **nullable** | 仅 `answer_type = YES_NO` 的题有值 |

唯一约束 `uk_erl_answer (assessment_id, question_id)`；索引 `idx_erl_answer_assessment (assessment_id)`。

> **两列恰好一个非空**（`score` 与 `yes_no` 互斥），由 service 层按题目的 `answer_type` 保证；建库脚本补 CHECK 约束 `(score IS NULL) <> (yes_no IS NULL)`。
>
> **`YES_NO` 题不折算成分数、不参与任何分数计算**（2026-08-26 已确认，§7.1）。它仍是必答题、仍计入完成度，只是不进分母。因此不能沿用 v2 早期"折算后存 `score`"的设计——那会把 Yes/No 混进平均值。

### 5.4 `erl_benchmark_record` — 基准记录

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | |
| `benchmarkit_score` | numeric(3,1) | not null | 1–9 |
| `top_quartile_score` | numeric(3,1) | not null | 1–9 |
| `note` | varchar(512) | | 空显示 `—` |

唯一约束 `uk_erl_benchmark (company_id, period)`。记录表里的 Recorded 日期由 `period` 推导（期末日），Recorded by 用 `created_by`。

### 5.5 `erl_gap_analysis` — Goldie 差距分析（v2 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `company_id` | varchar(36) | not null | |
| `period` | varchar(8) | not null | |
| `summary` | varchar(2048) | | LLM 生成的整体判断段落（是否要，见 §13-Q10） |
| `model` | varchar(64) | | 生成所用模型，便于回溯 |
| `generated_at` | timestamp | not null | 前端展示"最后生成时间" |

唯一约束 `uk_erl_gap_analysis (company_id, period)`。重新生成 = 覆盖本行 + 全量替换其 item 行。

### 5.6 `erl_gap_analysis_item` — 每维优势与差距（v2 新增）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | varchar(36) | PK | |
| `analysis_id` | varchar(36) | not null | → `erl_gap_analysis.id` |
| `dimension` | varchar(8) | not null | 五维之一 |
| `item_type` | varchar(16) | not null | `STRENGTH` / `GAP` |
| `title` | varchar(512) | not null | STRENGTH 用整句；GAP 用标题 |
| `note` | varchar(1024) | | 仅 GAP |
| `severity` | varchar(8) | | 仅 GAP：`HIGH` / `MEDIUM` / `LOW` |
| `sort_order` | int | not null | 组内顺序 |

索引 `idx_erl_gap_item (analysis_id, dimension, item_type, sort_order)`。

> **strengths 与 gaps 合成一张表**，用 `item_type` 区分：STRENGTH 只用 `title`，GAP 用 `title` + `note` + `severity`。避免两张近乎相同的表。

---

## 6. 接口契约

> 统一前缀：Java 侧 `@RequestMapping("/erl")`，前端经网关调 `/api/web/erl/**`。响应统一 `Result<T>`。入参走 `interfaces/vo/request`、出参走 `interfaces/vo/response`（`standards/coding.md` 三层传输实体强制），**禁止直接暴露 Entity**。

### 6.1 展示（A）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 1 | `GET /erl/overview` | A1 + A2 仪表盘 | `companyId`, `period`(可选，默认最新已提交期次) | `overallScore`、`overallEra`、`period`、`dimensions[]`（`dimension` / `name` / `gsvScore` / `founderScore` / `perceptionGap` / `gapDirection` / `era` / `grade`）、`radar`（四条序列的五维值） |
| 2 | `GET /erl/dimension/{dimension}` | A3 单维度模板页 | path `dimension`；`companyId`、`period`、`portal`(默认 `FOUNDER`) | `header`（`gsvScore` / `founderScore` / `grade` / `perceptionGap` / `benchmarkPosition`）、`intelligence`（三 Era 的 `score` + `progress`）、`chart`、`submission`、`questions[]`（含三段 `criteria`）、**`strengths[]`**、**`gaps[{title,note,severity}]`** |
| 3 | `GET /erl/scoreDetails` | A4 全维明细 | `companyId`、`period`、`portal` | `submission` + `dimensions[]`（每维 `questionCount` / `score` / `questions[]`） |

- A5「How It's Scored?」弹窗**不单独发请求**：三段评分标准随接口 2 / 3 的 `questions[].criteria` 返回。
- 接口 2 的 `strengths` / `gaps` 来自 `erl_gap_analysis_item`，无分析记录时为空数组。
- `benchmarkPosition` 取该公司该期次的 `erl_benchmark_record`；无记录返回 `null`。

### 6.2 填报（B）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 4 | `GET /erl/assessment` | B1 / B2 打开问卷（含回填草稿） | `companyId`、`period`、`portal` | `assessmentId`、`status`、`answeredCount`、`totalCount`、`scoredCount`、`overallAverage`、`dimensions[]`（题带 `answerType` / `evidenceSource` / `myScore` / `myYesNo`） |
| 5 | `POST /erl/assessment/draft` | 自动存草稿（幂等增量） | `companyId`、`period`、`portal`、`answers[{questionId, score?, yesNo?}]` | `answeredCount`、`overallAverage`、`savedAt` |
| 6 | `POST /erl/assessment/submit` | 提交 | 同上 | `assessmentId`、`overallScore`、`overallEra` |
| 7 | `GET /erl/assessment/periods` | 期次下拉 | `companyId` | `periods[]`（`period` + 各端 `status`） |
| 8 | `GET /erl/assessment/history` | B3 历史列表 | `companyId`、可选 `dimension` | `records[]`（`period` / `portal` / `submittedAt` / `submitterName` / `submitterRole` / `answeredCount` / `totalCount` / `overallScore` / `era`） |

- 草稿保存**幂等增量**：只 upsert 传入的 `answers`，不影响未传题目。每条 `answers` 项按题目的 `answerType` 二选一填 `score` 或 `yesNo`，填错的一方由服务端拒绝（§5.3 的互斥约束）。
- `totalCount` 含全部已启用题（含 `YES_NO`）；`scoredCount` 只含 `SCORE` 题，前端用它解释"题数 ≠ 分数分母"（§7.1.1）。
- 提交前置校验 `answeredCount == totalCount`（**含 `YES_NO` 题**），否则 `BadRequestException("Please answer all questions before submitting.")`。
- 已 `SUBMITTED` 再次提交 → 拒绝（见 §13-Q3）。

### 6.3 题库配置（C）

| # | 方法 / 路径 | 用途 | 关键入参 |
|---|-------------|------|----------|
| 9 | `GET /erl/question` | C1 列表（按 `eraBand` 分组、组内带题数） | `dimension` |
| 10 | `POST /erl/question` | C2 新增 | `dimension`、`eraBand`、`questionText`、`answerType`、`evidenceSource`、三段 `criteria` |
| 11 | `GET /erl/question/{id}` | C3 编辑回填 | path `id` |
| 12 | `PUT /erl/question/{id}` | C3 更新 | 同 10 |
| 13 | `DELETE /erl/question/{id}` | C3 删除（软删） | path `id` |

### 6.4 基准（D）

| # | 方法 / 路径 | 用途 | 关键出参 |
|---|-------------|------|----------|
| 14 | `GET /erl/benchmark` | D1 页 | `latest`（两条基准最新值 + `deltaVsPrior`）、`records[]` |
| 15 | `POST /erl/benchmark` | D2 新增 | — |

`deltaVsPrior` 由服务端按 `period` 倒序取前一条计算，前端不算。

### 6.5 Goldie 差距分析（E，v2 新增）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 16 | `GET /erl/gapAnalysis` | E1 + E2 读取（读缓存，不触发 LLM） | `companyId`、`period`、可选 `dimension` | `summary`、`signals[]`（3 条，服务端按 §7.3 规则算）、`dimensions[{dimension, strengths[], gaps[]}]`、`generatedAt`、`model` |
| 17 | `POST /erl/gapAnalysis/generate` | 触发生成 / 重新生成（仅管理端） | `companyId`、`period` | 同 16 |

**Python 内部接口**（Java 经网关调，非前端可达）：

```
POST /api/ai/erl/gap-analysis

入参  companyId、period、
      dimensions[{ dimension, name, gsvScore, founderScore,
                   questions[{ questionText, era, evidenceSource, answerType,
                               founderScore, gsvScore,        // SCORE 题
                               founderYesNo, gsvYesNo }] }]   // YES_NO 题

出参  summary、
      dimensions[{ dimension, strengths[string], gaps[{ title, note, severity }] }]
```

- **`YES_NO` 题的答案照样传给 Python**——它不计分，但对判断优势与差距有信息量（如"是否已分离对公账户"）。prompt 中须说明这类题不参与打分，不要在文案里编造它的分值。
- Python 侧**不落库、不查库**：全部输入由 Java 传入，输出交 Java 落库。
- Prompt 放 `source/ai/prompts/`，带 `# version: x.x`，变更须附回归测试（`CIOaas-python/standards/coding.md` §15）。
- `severity` 值域固定 `HIGH` / `MEDIUM` / `LOW`，在 prompt 中约束并在 Java 侧校验，非法值降级为 `MEDIUM`。

### 6.6 组合层 ERL 总表（F2，v2 新增）

| # | 方法 / 路径 | 用途 | 关键入参 | 关键出参 |
|---|-------------|------|----------|----------|
| 18 | `GET /erl/portfolio` | F2 Tab | 可选 `period` | `companies[{ companyId, name, overallScore, frl, prl, berl, rrl, trl, stage }]` |

- 只返回当前登录用户**有权访问的公司集**（§4.3）。
- 每家取其**最新已提交期次**的 GSV 评估；无评估的公司 `overallScore = null`，前端显示 `—`。
- **必须批量聚合**：一次查出全部公司的答案并在内存归组，禁止按公司循环查询（N+1）。

---

## 7. 计算口径与状态流转

### 7.1 分数

| 口径 | 规则 |
|------|------|
| 单题分 | 仅 `answer_type = SCORE` 的题有分，取 1–9。**`YES_NO` 题不折算、不计分**（2026-08-26 已确认） |
| 维度分 | 该维度**已启用且 `answer_type = SCORE`** 的题目得分算术平均，保留 1 位小数 |
| 综合分 | 五个维度分的算术平均，保留 1 位小数（已核实，§2.3） |
| Perception Gap | `Founder 维度分 − GSV 维度分`；`> 0` 显示 `Positive`，`< 0` 显示 `Negative`，取绝对值展示 |
| Era 归属 | 按分数落段（2026-08-26 已确认），见下表 |
| Stage（F2 徽章） | 由综合分推导，与 Era 同一套分段规则 |
| 等级（Grade） | 待产品给分档表，见 §13-Q2 |

展示页的"维度分"一律取 **GSV 分**（§2.3）；GSV 侧未提交时的降级见 §9。

### 7.1.1 计分范围 ≠ 完成度范围（易错点）

`YES_NO` 题不计分，但**仍是必答题**。两个分母必须分开：

| 用途 | 分母 | 举例（FRL 31 题，假设含 3 道 YES_NO） |
|------|------|------|
| **维度分 / 综合分** | 只数 `SCORE` 题 | 28 题求平均 |
| **完成度 / 进度条 / 提交校验** | 数**全部**已启用题 | `31 / 31` 才算答满 |

- A3 页头的"31 questions"是**题数**（含 YES_NO），与分数的分母不是同一个数——这是原型页面上"题数与分数对不上"的正解。
- B1/B2 的 `0 of 165` 进度、B3 的 `45 / 45` 完成度、提交时的 `answeredCount == totalCount` 校验，一律按**全部题**算。
- 某维度**全是 `YES_NO` 题**（无计分题）时，该维度分为 `null`，走 §9 降级；综合分按剩余有分维度平均。

### 7.1.2 Era / Stage 分段规则（2026-08-26 已确认）

以 **1–3 / 4–6 / 7–9** 分段为准；原型 FRL 6.4 标 `Exit Era` 是**原型错误**，不予沿用。精确边界（分数为 1 位小数，需明确开闭区间）：

| 分数区间 | Era / Stage |
|----------|-------------|
| `1.0 ≤ score < 4.0` | **Founder Era** |
| `4.0 ≤ score < 7.0` | **Harvest & Growth** |
| `7.0 ≤ score ≤ 9.0` | **Exit Era** |

**交叉验证**：该规则套原型的 6 个数值，5 个与原型显示一致（综合 5.3 → Harvest ✓；PRL 5.1 → Harvest ✓；BERL 7.5 → Exit ✓；RRL 4.6 → Harvest ✓；TRL 2.8 → Founder ✓），唯一不一致的就是被判定为 bug 的 FRL 6.4（原型 Exit，本规则 **Harvest & Growth**）。

> 题目的 `era_band`（1–9 整数档位）到 Era 的映射不受影响：band 1–3 → Founder Era、4–6 → Harvest & Growth、7–9 → Exit Era，整数无边界歧义。

### 7.2 评估状态流转

```
        (首次打开问卷)                (自动存草稿)              (提交)
无记录 ──────────────► DRAFT ──────────────► DRAFT ──────────────► SUBMITTED
                        ▲                                            │
                        └──────────── 不允许回退（V1） ───────────────┘
```

- `GET /erl/assessment` 命中无记录时**不建记录**，返回空答案的题目结构；首次 `POST draft` 才落 `DRAFT` 行。
- 只有 `SUBMITTED` 的记录进 B3 历史列表、A 展示页与 F2 总表。

### 7.3 三条洞察卡的合成规则（E1，v2 新增）

已从原型完整反解，**在 Java `application/service` 内实现，不进 LLM**：

| 卡片 | 规则 | 文案模板 |
|------|------|----------|
| **Key risk signal** | 把五维全部 `gaps` 展平，取**第一条 `severity = HIGH`** | `{abbr}: {gap.title} — flagged as a high-severity diligence blocker.` |
| **Value lever** | 按维度分**降序**取第一名，用其 `strengths[0]` | `{abbr} scores {score}/9 — {strengths[0]} can be leaned on in the equity story.` |
| **Next 90 days** | 按维度分**升序**取第一名 | `Lift {abbr} ({score}/9) first — the fastest route to moving the composite up a stage.` |

- 无 `HIGH` gap → 第 1 条不产出；最高分维度无 strengths → 第 2 条不产出；三条全空 → 走 §9 的空态。
- 文案模板固定在后端，前端只渲染。**规则可写断言测试**（§11 第 15 项）。

### 7.4 差距分析的生成时机

```
GSV 提交评估  ──►  (不自动生成)
                     │
管理端进入 Dashboard / A3 页  ──►  GET /erl/gapAnalysis
                     │
              ┌──────┴──────┐
        有缓存 │             │ 无缓存
              ▼             ▼
          直接渲染      显示「Generate gap analysis」按钮
                            │  管理端点击
                            ▼
                   POST /erl/gapAnalysis/generate
                   （前端 loading，Java 同步调 Python，落库后返回）
```

已有缓存时页面同时给 **Regenerate** 按钮（显示 `generatedAt`）。公司端只读，看不到这两个按钮。

---

## 8. 前端设计（功能级）

### 8.1 路由（`config/routes.ts`）

| URL | component | 页面 |
|-----|-----------|------|
| `/exitReadiness` | `./exitReadiness/dashboard` | A1 / A2 / E1 |
| `/exitReadiness/dimension/:dimension` | `./exitReadiness/dimension` | A3 / E2 |
| `/exitReadiness/scoreDetails` | `./exitReadiness/scoreDetails` | A4 |
| `/exitReadiness/assessment` | `./exitReadiness/assessment` | B1（`?portal=gsv` 切 B2） |
| `/exitReadiness/history` | `./exitReadiness/history` | B3 |
| `/exitReadiness/benchmark` | `./exitReadiness/benchmark` | D1 + D2(Modal) |
| `/exitReadiness/configuration` | `./exitReadiness/configuration` | C1 + C3 删除 |
| `/exitReadiness/configuration/add` | `./exitReadiness/configuration/add` | C2 |
| `/exitReadiness/configuration/edit/:id` | `./exitReadiness/configuration/edit` | C3 |

F2 不新增路由——它是 `/company`（`./portfolioCompanies/home`）页内的第 5 个 Tab。

> B1 / B2 共用一套问卷页，用 `portal` 参数切换；C 模块三条路由对管理端可见，公司端由菜单与路由守卫双重拦截。

### 8.2 目录结构（`src/pages/exitReadiness/`）

遵循 `CIOaas-web/CLAUDE.md`「同域多功能归入域文件夹作第二层」「域根须有 README.md」「转发式 index.tsx 仅限路由页面入口」：

```
src/pages/exitReadiness/
├── README.md                      域文档（职责 / 目录 / 域内要求）
├── components/                    域级共享：DimensionScoreCard、EraProgressBar、
│                                  QuestionRow、ScoringCriteriaModal(A5)、
│                                  GapAnalysisCard(E1)、StrengthsAndGaps(E2)、
│                                  PeriodSelect、PortalTabs、constants.ts、types.ts
├── dashboard/{index.tsx, DashboardPage.tsx, hooks/, components/}
├── dimension/{index.tsx, DimensionPage.tsx, hooks/, components/}
├── scoreDetails/{...}
├── assessment/{...}
├── history/{...}
├── benchmark/{...}
└── configuration/{index.tsx, ConfigurationPage.tsx, add/, edit/, hooks/, components/}
```

分层口径按 `standards/architecture.md` §3：`index.tsx` 只转发；`XxxPage.tsx` 组装 hooks 与 components；**业务逻辑（调 API / 管状态）只写在 `hooks/`，`components/` 收 DTO props 不调 API**。

**F2 改存量页**：`src/pages/portfolioCompanies/home/` 下新增 ERL Tab 组件 + 取数 hook。ERL Tab 的表格组件放该页 `components/`，不下沉 `src/components/`（当前只此一处使用）。

### 8.3 服务层（`src/services/`）

```
services/api/exitReadiness/       erlApi.ts / request.ts / response.ts / dto.ts / README.md
services/service/exitReadiness/   erlService.ts   （Response ↔ DTO 转换，跨页面复用）
```

F2 的 `GET /erl/portfolio` 也归入 `exitReadiness/` 域（按后端接口归域，不按页面归域）。

### 8.4 关键交互

| 交互 | 设计 |
|------|------|
| **A3 模板参数化** | 维度名称、缩写、简介、主题色收在 `components/constants.ts` 的 `DIMENSIONS` 映射，页面按 `:dimension` 取；**禁止**在 5 个分支里硬编码文案（story 明确要求） |
| **维度间跳转** | A3 页头提供维度切换器（5 个 chip），不必回仪表盘 |
| **雷达图（A2）** | 复用 `src/components/Charts/`（ECharts）；4 条序列，五维为轴，域 0–9 |
| **A3 维度图表** | 三 Era 为轴的对比图，配色与图例与 A2 同一套（story 要求 5 维一致） |
| **E1 卡片** | summary 段落 + 三张洞察卡（横向 3 栏，窄屏堆叠）；管理端多一个 Generate / Regenerate 按钮 + `generatedAt` 时间戳 |
| **E2 区块（A3 内）** | 左 Strengths 列表（无序列表），右 Priority Gaps 条目（`title` 加粗 + `note` 次级文字 + `severity` 色标徽章：HIGH 红 / MEDIUM 黄 / LOW 灰） |
| **F2 ERL Tab** | 与现有 4 个 Tab 同一套表格样式；ERL Score 与 Stage 按分数着色；末列 `View →` 跳 `/exitReadiness?id={companyId}` |
| **自动存草稿（B1/B2）** | 打分后本地即时更新进度与均分；**去抖 1.5s 批量 POST** 变更题目；保存中/已保存状态在吸底条提示；离开页面前 flush |
| **进度与均分** | 前端本地算，不每次请求 |
| **提交（B1/B2）** | 吸底提交条；未答满时按钮禁用并提示剩余题数 |
| **`YES_NO` 题的呈现** | B1/B2 填报页渲染 Yes / No 两个按钮（原型即如此）；A3/A4 逐题列表右侧显示 `Yes` / `No` 徽章**而非 `x.x/9`**，并带 `Not scored` 次级标注，避免用户以为它进了平均值 |
| **题数与分数分母的说明** | A3 页头显示 `{totalCount} questions · {score}/9`，其中 `totalCount` 含 YES_NO 题。当 `scoredCount < totalCount` 时，分数旁加 tooltip：`Score averages the {scoredCount} scored questions; Yes/No questions are not scored.` |
| **只读态** | 公司端打开 B2、或期次已 `SUBMITTED` 时，问卷渲染为只读 |
| **C1 分组** | 五维 Tab + 组内按 Era band 折叠分组，组头显示题数 |
| **C3 删除** | `Modal.confirm` 二次确认，文案含所属维度、提示不可撤销 |
| **响应式** | 桌面 + 移动均可用（story AC）；表格类窄屏横向滚动，卡片单列堆叠 |
| **国际化** | 文案走 `locales/`，不硬编码中文 |

### 8.5 A3 入口方案（补 §2.4-② 的缺口）

原型中通往 A3 的唯一入口在 Finance 页（属 F1，不做）。本设计的解法：

**在 A1 Dashboard 的五个维度行上各加一个 `View Details →` 链接**，跳 `/exitReadiness/dimension/{dimension}`。

- 这是原型没有的**新增交互**（原型的 Dashboard 维度行不可点）
- 不碰 Finance 页，不破坏 F1 的排除
- F2 的 `View →` 只到 Dashboard，不直达维度页（与原型一致）

见 §13-Q7。

---

## 9. 失败降级

| 场景 | 服务端 | 前端表现 |
|------|--------|----------|
| 该公司无任何已提交评估 | 接口 1/2/3 返回空结构（分数 `null`） | 展示页整页空态："No assessment submitted yet." + 去填报入口 |
| 只有 Founder 提交、GSV 未提交 | `gsvScore = null`、`perceptionGap = null` | 维度卡显示 Founder 分并标注 "Awaiting GSV validation"，Perception Gap 隐去；雷达图 GSV 序列不绘制 |
| 无基准记录 | `benchmarkPosition = null`、`latest = null` | A3 隐去基准位置项；D1 空态 + Add New |
| 题库为空（某维度 0 题） | 该维度 `score = null` | 维度卡显示 `—`，综合分按有题维度平均并提示口径 |
| **某维度只有 `YES_NO` 题（无计分题）** | 该维度 `score = null`、`scoredCount = 0` | 维度卡分数显示 `—` 并标注 "No scored questions"；该维度不进综合分分母；雷达图该轴取 0 但图例标注缺失 |
| **无差距分析记录** | 接口 16 返回 `summary = null`、`signals = []` | 沿用原型空态文案：**`No gap analysis yet`** + **`Goldie needs scored questions with evidence notes for this dimension before it can suggest gaps and recommended actions.`**；管理端多一个 Generate 按钮 |
| **LLM 生成失败 / 超时** | 接口 17 抛 `ServiceException`，**不写库、不覆盖已有分析** | 提示 "Gap analysis failed. Please try again."，保留原有分析内容不变 |
| **LLM 返回结构不合法** | Java 侧校验维度枚举与 `severity` 值域；非法 `severity` 降级 `MEDIUM`；维度缺失则该维度 strengths/gaps 为空 | 缺失维度的区块显示空态，其余正常渲染 |
| **F2 某公司无评估** | 该行 `overallScore = null` | 该行各分数列显示 `—`，Stage 留空，`View` 仍可点（进 Dashboard 看空态） |
| 草稿保存失败（网络） | — | 吸底条红色提示 "Draft not saved — retrying"，本地保留未保存变更并自动重试；离开前二次确认 |
| 提交时题库已变更（有新题） | 校验 `answeredCount == totalCount` 失败 → 400 | 提示 "New questions were added. Please refresh and complete them." 并重载问卷 |
| 跨端越权访问 | `BadRequestException` | 统一错误提示，路由守卫先行拦截 |

---

## 10. 改动文件清单

### 10.1 CIOaas-api（新增业务域 `erl/`）

```
gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/erl/
├── interfaces/controller/     ErlOverviewController / ErlAssessmentController
│                              ErlQuestionController / ErlBenchmarkController
│                              ErlGapAnalysisController / ErlPortfolioController
├── interfaces/vo/request/     ErlOverviewQueryRequest / ErlAssessmentQueryRequest
│                              ErlAssessmentSaveRequest / ErlQuestionCreateRequest
│                              ErlQuestionUpdateRequest / ErlBenchmarkCreateRequest
│                              ErlGapAnalysisGenerateRequest
├── interfaces/vo/response/    ErlOverviewResponse / ErlDimensionDetailResponse
│                              ErlScoreDetailsResponse / ErlAssessmentResponse
│                              ErlAssessmentHistoryResponse / ErlQuestionResponse
│                              ErlBenchmarkResponse / ErlGapAnalysisResponse
│                              ErlPortfolioResponse
├── interfaces/converter/      ErlConverter（MapStruct，Request/Response ↔ DTO）
├── application/service/       ErlOverviewService(+Impl) / ErlAssessmentService(+Impl)
│                              ErlQuestionService(+Impl) / ErlBenchmarkService(+Impl)
│                              ErlGapAnalysisService(+Impl)   ← 含 §7.3 三条洞察规则
│                              ErlPortfolioService(+Impl)
├── application/dto/erl/       ErlDimensionScoreDTO / ErlAssessmentDTO / ErlAnswerDTO
│                              ErlQuestionDTO / ErlBenchmarkDTO / ErlGapAnalysisDTO
│                              ErlGapItemDTO / ErlInsightDTO
├── application/mapper/        ErlMapper（MapStruct，DTO ↔ Entity）
├── domain/entity/             ErlQuestion / ErlAssessment / ErlAssessmentAnswer
│                              ErlBenchmarkRecord / ErlGapAnalysis / ErlGapAnalysisItem
├── domain/enums/              ErlDimensionEnum / ErlEraEnum / ErlPortalEnum
│                              ErlAssessmentStatusEnum / ErlAnswerTypeEnum
│                              ErlGapItemTypeEnum / ErlSeverityEnum
├── domain/repository/         ErlQuestionRepository / ErlAssessmentRepository
│                              ErlAssessmentAnswerRepository / ErlBenchmarkRecordRepository
│                              ErlGapAnalysisRepository / ErlGapAnalysisItemRepository
└── infrastructure/client/     ErlGapAnalysisPythonClient   ← 经网关调 Python 生成接口
```

另需 `deploy/upgrade_doc/sprint{N}/erl_init.sql`（唯一约束 + 索引 + 165 题种子数据）。

> 分数聚合与洞察合成属跨表编排，写在 `application/service`；`domain/repository` 只做单表访问（`standards/architecture.md` §1.2 / §1.3）。

### 10.2 CIOaas-python（v2 新增，仅生成服务）

```
新增  source/erl/interfaces/router.py                    POST /api/ai/erl/gap-analysis
新增  source/erl/interfaces/vo/{request,response}.py
新增  source/erl/application/service/erl_gap_analysis_service.py
新增  source/ai/prompts/erl_gap_analysis.md              带 # version: 1.0
修改  source/main.py                                     注册 router
新增  tests/erl/test_erl_gap_analysis_service.py         prompt 回归测试（固定输入→验证输出结构）
```

Python 侧**无 domain 层、无 repository**——不落库、不查库，输入输出全由 Java 传递。

### 10.3 CIOaas-web

```
新增  src/pages/exitReadiness/**                （§8.2 全部）
修改  src/pages/portfolioCompanies/home/**      F2：新增 ERL Tab + 取数 hook
新增  src/services/api/exitReadiness/**
新增  src/services/service/exitReadiness/erlService.ts
修改  config/routes.ts                          （§8.1 九条路由 + 菜单项）
修改  src/locales/en-US/**                      （ERL 文案）
修改  CIOaas-web/standards/architecture.md §2   （登记新 API 域 exitReadiness/，见 §13-Q5）
```

### 10.4 台账

`CIOaas-api/docs/待优化项.md` 已于 2026-08-26 记入 `fi/` 分层与 `QuickbooksController` 存量违规一条。

---

## 11. 验证清单（实现后逐项过）

1. 五个维度页 `/exitReadiness/dimension/{FRL|PRL|BERL|RRL|TRL}` 均由**同一组件**渲染，文案随参数变化，无硬编码分支。
2. 非法 `dimension` 参数 → 404 页面，不崩溃。
3. Founder 提交 7.8 / GSV 提交 6.4 时，仪表盘显示维度分 `6.4`、`Perception Gap: Positive 1.4`。
4. 五维分 6.4 / 5.1 / 7.5 / 4.6 / 2.8 → 综合分显示 `5.3`。
4.1 **Era 分段**：分数 3.9 → `Founder Era`、4.0 → `Harvest & Growth`、6.9 → `Harvest & Growth`、7.0 → `Exit Era`（边界值逐个验，§7.1.2）；**FRL 6.4 必须显示 `Harvest & Growth`**（原型显示 Exit Era 是 bug，不得复现）。
4.2 **`YES_NO` 不计分**：某维度 10 题中 3 题为 `YES_NO`、7 题 `SCORE` 且分数全为 6 → 维度分显示 `6.0`（不是把 Yes 当 9 分拉高）；页头题数显示 `10 questions`、分数 tooltip 说明按 7 题平均。
4.3 **完成度含 `YES_NO`**：上述维度只答完 7 道 `SCORE` 题时，进度显示 `7 / 10`，提交按钮禁用；补答 3 道 Yes/No 后才可提交。
4.4 某维度全为 `YES_NO` 题时，维度分显示 `—`，且**不进综合分分母**（综合分按其余 4 维平均）。
5. 自评页答 3 题后关闭浏览器，重进同期次同端，3 题答案完整回填、进度条 `3 of 165`。
6. 未答满 165 题时提交按钮禁用；答满后提交成功，记录进 B3 且完成度 `165 / 165`。
7. 公司端访问 `/exitReadiness/configuration` 与 `?portal=gsv` 被拦截；直接调后端写接口返回 400。
8. 公司端调 A1 接口并伪造他人 `companyId` → 服务端仍返回本公司数据。
9. 题库删除某题后，历史评估详情页仍能展示该题题干与当时得分。
10. 新增基准记录后，D1 最新卡的 `vs prior` 环比值正确。
11. 无 GSV 提交时，仪表盘按 §9 降级，不出现 `NaN` / `null` 字样。
12. Dashboard 五个维度行的 `View Details` 能正确跳到对应维度页（§8.5 新增交互）。
13. **管理端点 Generate 后，Dashboard 出现 summary + 三条洞察卡，A3 出现该维度的 Strengths & Priority Gaps；公司端看不到 Generate / Regenerate 按钮。**
14. **Python 生成接口断连时，接口 17 返回错误、库中原有分析不被清空、页面仍显示旧分析。**
15. **三条洞察规则的单测**：构造 gaps 含 1 条 HIGH + 2 条 MEDIUM、五维分已知，断言三条文案与 §7.3 模板逐字一致；再构造无 HIGH gap 的输入，断言只产出 2 条。
16. **LLM 返回非法 `severity`（如 `critical`）时降级为 `MEDIUM` 且不报错。**
17. **F2 ERL Tab 只列当前用户有权访问的公司；无评估的公司各分数列显示 `—`。**
18. **F2 在 20 家以上公司时只发 1 次请求、后端无 N+1 查询**（开 SQL 日志核对）。
19. 移动端（≤768px）各页可用，表格横向滚动、页面不整体横向滚动。
20. `npm run tsc` 与 `npm run lint:fix` 无新增错误；`mvn -pl gstdev-cioaas-web test` 通过；`uv run pytest tests/erl/` 通过。

---

## 12. V1 明确不做（YAGNI / 风险控制）

- 不做 E3（Ask Goldie 对话接入）与 F1 / F3（Finance 页卡片与面包屑回跳）。
- 不做 Goldie 生成结果的人工编辑 / 审核流（见 §13-Q11）。
- 不让 LLM 产出三条洞察卡——规则已知，走确定性实现（§7.3）。
- 不做差距分析的自动生成 / 定时生成 / 版本历史，只保留"最新一份 + 手动 Regenerate"。
- 不做题库的公司级覆盖 / 版本化（题库全局单份）。
- 不做评估期次之间的对比、趋势图、导出。
- 不做题目排序拖拽、批量导入导出。
- 不做 `SUBMITTED` 回退为 `DRAFT` 的重开流程（待 §13-Q3）。
- 不冗余存储任何聚合分数（维度分 / 综合分 / 等级 / Era / 三条洞察全部实时算）。
- 不新增 dva model（`src/models/` 已冻结）。
- 不引入 SQS：Java↔Python 走同步 HTTP 经网关。

**识别到但本次不处理**：

- `fi/` 业务域仍是扁平结构、`QuickbooksController` 在 Controller 内 try-catch 并直接收发 Entity，均不符合 `standards/`，属存量技术债 —— 已记入 `CIOaas-api/docs/待优化项.md`（2026-08-26 条目）。
- 165 题的问卷页单页渲染；题量再翻倍需考虑虚拟滚动（属本次新代码的已知边界，实现后若确有卡顿再记台账）。

---

## 13. 待确认事项（开发前必须对齐）

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| **Q1** | A3 单维度页按**原型现状**（只有题目明细）还是按 **Lovable story 验收标准**（score card 头 + Dimension Intelligence + Perception Gap + 图表 + 题目表 + Strengths & Gaps）实现？§2.4-① 已证实两者不一致 | A3 工作量差一倍 | **按 story 实现**，本文档已按此设计 |
| **Q2** | **仅剩一项未定：等级（Grade）分档表**——`A-` / `B` / `C-` / `D` 等字母等级与分数的映射规则。原型的 `overallPercent` 与 `score/9` 对不上（BERL：7.5/9 = 83.3% 但 mock 写 76.7%），无法反解 | A1 维度卡、A3 score card 头的 Grade 字段无法实现；**其余展示不受阻** | 需产品给出分档表（建议格式：分数区间 → 字母等级）。在此之前 Grade 字段留空、其余照常开发 |
| ~~Q2-①~~ | ~~`YES_NO` 题如何折算成 1–9 分~~ | — | **✅ 已确认（2026-08-26）：不折算、不计分。** `YES_NO` 题必答、计入完成度，但不进分数分母。落地口径见 §5.3（`score` / `yes_no` 双列互斥）、§7.1、§7.1.1 |
| ~~Q2-③~~ | ~~Era 归属规则与原型 FRL 6.4 标 `Exit Era` 矛盾~~ | — | **✅ 已确认（2026-08-26）：原型错误，以 1–3 / 4–6 / 7–9 分段为准。** 精确边界 `[1,4)` Founder / `[4,7)` Harvest / `[7,9]` Exit，见 §7.1.2（已用原型 6 个数值交叉验证，5/6 吻合，唯一不吻合者即该 bug） |
| **Q3** | 已 `SUBMITTED` 的评估是否允许重开修改？同期次同端是否允许多次提交（存多版本）？ | 影响唯一约束与状态机 | V1 建议不允许重开 |
| **Q4** | 题库是否全局单份？还是不同公司 / Fund 可有不同题库？ | 影响 `erl_question` 是否需要 `company_id` | 原型无公司维度，V1 按全局单份 |
| **Q5** | 前端 `services/api/` 新增 `exitReadiness/` 域需登记进 `CIOaas-web/standards/architecture.md` §2 域表（该表现为 24 域，规范写明"禁止自创目录名"） | 规范符合性 | 随本功能一并更新规范文件 |
| **Q6** | 165 道题的初始内容从哪里来？原型内嵌的是 mock 题库，是否即为正式题库？ | 决定 `erl_init.sql` 种子数据 | 若可用，从原型 bundle 提取；否则需产品提供题库清单 |
| **Q7** | ① ERL 菜单入口挂哪一级（F1 不做则无存量页入口）？② A3 入口按 §8.5 在 Dashboard 维度行新增 `View Details`（原型没有的新交互）是否接受？ | 用户找不到功能 / A3 无入口 | ① 主导航新增 `Exit Readiness` 一级入口；② 接受 §8.5 方案 |
| ~~**Q8**~~ | ~~E1/E2 引入 LLM，必须动 `CIOaas-python`（Java 侧零 LLM 客户端，§3.2）。是否接受"Java 唯一前端出口 + Python 只做生成"？~~ | — | **✅ 已确认（2026-08-26）：接受。** 后端形态定为 Java `erl/` 域对前端唯一出口 + Python `source/erl/` 纯生成服务，Java↔Python 走 HTTP 经网关同步调用。§3.1 / §3.2 / §6.5 / §10.2 按此执行，无需再改 |
| **Q9** | 原型里 **Portfolio ERL Tab 与 Dashboard 的 ERL 分数互相矛盾**（Example 1：7.2 / 7.5 / 6.8 / 7.0 / 7.4 / 6.9 对 5.3 / 6.4 / 5.1 / 7.5 / 4.6 / 2.8，§2.5）。确认两处统一走同一套实时计算？ | F2 与 A1 数据是否自洽 | **统一**——两处都用 §7.1 的口径实时算 |
| **Q10** | E1 的 **summary 段落**是否需要 LLM 生成？原型里它是硬编码兜底文案，两个调用方都没传 `summary`（§2.6） | 若不需要，Python 侧只生成 strengths/gaps，prompt 更简单、更稳 | 建议 **要**（三条规则洞察缺少整体判断，价值有限）；若产品认为不必要，`erl_gap_analysis.summary` 留空即可，无需改表 |
| **Q11** | LLM 生成的 strengths / gaps 是否需要 GSV 人工编辑或审核后才对公司端可见？ | 影响是否需要 `status` 字段与编辑页 | V1 建议不做（生成即可见），本文档按此设计 |
