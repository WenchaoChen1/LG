# Playbook 接入 Chatbot 开发设计（独立 process_type + PG 关系边 + 两段式检索）

> 关联文档：
> - 选型对比与实测（上游，先读）：[./playbook-recall-options-comparison.md](./playbook-recall-options-comparison.md)
> - 预研原型（`feature/sprint112-age`，只搬数据、不合并代码）：`python/CIOaas-python/source/playbooks_graph_db/`
> - 内部查看器（独立一条线，本期非范围）：[../../superpowers/specs/2026-06-23-playbook-knowledge-design.md](../../superpowers/specs/2026-06-23-playbook-knowledge-design.md)
>
> 阶段：⑤ 开发设计 | 版本：**v2** | 日期：2026-07-29 | 端：**Python**（CIOaas-python，`sprint115-playbook`）+ **Java 3 行**（`FileBusinessTypeEnum` 加 PLAYBOOK，§7.0） | 范围：playbook 落地为可维护、可被 chatbot 调用的检索能力
>
> **v2 相对 v1 的方案变更**：v1 把 playbook 塞进 STANDARD 空间、复用 KB 的 chunk 表、靠导入脚本灌数据；v2 改为**新增第三个 `process_type='PLAYBOOK'`**，走 rag 既有的「一个处理类型 = 一套向量化 + 召回 + 存入 + 自己的 chunk 表 + 仓储」契约，维护由**部署期脚本升级为 HTTP API**。代价是多一张 chunk 表，换来的是**共用代码零改动**（v1 需要三处受控放宽，v2 一处都不用）——详见 §2.1 与 D14~D18。
>
> 说明：本文给到模块落位 / 数据模型 / 链路 / 契约 / 异常 / 测试级别；完整 DDL 以迁移文件为准，不在此重复。

---

## 1. 目标与范围

**两个用途**：

| 用途 | 说明 | 对检索的要求 |
|------|------|--------------|
| 方法论问答 | 用户问「怎么做现金流预测 / 怎么搭销售管道」，给可执行步骤 | 找对 playbook + 拿到正文细节 |
| **诊断式推荐** | 结合公司财务 / benchmark 指标判断短板，推荐该执行哪几个 playbook 及**先后顺序** | **必须能查「做 X 前要先做什么」「谁依赖 X」——这是结构查询，语义相似度替代不了** |

把 `feature/sprint112-age` 预研的 playbook 语料落到 sprint115 的 chatbot，让模型能基于**通用方法论**回答"该怎么做 X"，并带出**前置依赖顺序**。

**本期范围**

- **新增第三个处理类型 `PLAYBOOK`**：`SYSTEM_SEEDS` 种子 + `processor/playbook/` 包（爬取 / 切分 / 建关系 / 向量化 / 入库 / 召回）+ 独立 chunk 表，并注册进 `BUSINESS_REGISTRY`
- 三张新表：`ai_rag_playbook_chunk`（向量库）+ `ai_playbook` / `ai_playbook_version`（业务库）+ 版本化迁移
- **维护做成功能（三个 API）**：`crawl`（抓源站整页 HTML → 经 Java 预签名上传 S3 → `files` + `ai_file_registry` 登记）+ `ingest`（从 S3 取 HTML → 解析 + 推关系 + 切分 + 向量化 → 产出一个 **DRAFT 版本**，不影响线上）+ `versions/{v}/activate`（审核后发布，兼回滚）
- **LLM 只用在两处**：关系推断（opus5，一次全局调用，§7.1.1）+ 向量化 embedding。解析 HTML、切分、构造 profile、入库**全部无 LLM**；`summarize` 被覆写成返回 `None`（D16）
- **Java 侧 3 行**：`FileBusinessTypeEnum` 加 `PLAYBOOK`（S3 目录 `uploads/playbook/`、白名单仅 html），service / controller 零改动。⚠️ **必须与 Python 同批上线**——Python 的 crawl 调 presign 时会传这个 code，Java 没有它就直接 400
- chatbot 工具 `search_playbooks` + 提示词接线
- 召回回归评测脚本 + 157 题金标集

**第一阶段不做页面**：维护经手动调 API 触发（Swagger / curl 均可）。空间在 devSupport 现成的 New Space 里选 `Playbook` 类型手建——那个下拉是 `processTypes.map()` 动态渲染的，`GET /process-types` 自动多出这个选项。

⚠️ **但前端不是完全零改动，有 3 行硬编码要补**（已核实）：

| 位置 | 现状 | 不改的后果 |
|---|---|---|
| `services/api/rag/ragDto.ts` 的 `ProcessType` 联合类型 | 只有 `'STANDARD' \| 'STRUCTURED'` | `Record<ProcessType, string>` 类型不准 |
| `devSupport/rag/components/constants.ts` 的 `PROCESS_TYPE_LABEL` | 同上两个 key | 空间卡片显示原始 code **`PLAYBOOK`** 而非 `Playbook` |
| `devSupport/rag/components/RecallPanel.tsx` 的 `PROCESS_TYPE_BY_MODE` | 只有 standard / structured | 召回面板**勾选 mode 筛选后 playbook 空间会消失**（不勾则正常） |

**非目标（明确不做）**

| 不做 | 原因 |
|---|---|
| **playbook 维护页面** | 第一阶段只做到"能手动调 API 触发"。维护是低频运营动作（源站更新时才跑），页面按需再排 |
| 内部查看器 `/api/ai/playbook/*` 查询端点 + devSupport 页面 | 注册进 `BUSINESS_REGISTRY` 后，**devSupport 现成的 rag 空间 / 文档 / 片段 / 召回测试页已能查看 playbook**（§2.1），独立查看器的必要性进一步下降 |
| 诊断式推荐 `recommend_playbooks` | 二期；本期数据模型已为它预留（category / stage 结构化） |
| 清理 `feature/sprint112-age` | 该分支原样保留作预研记录，**只搬数据、不搬代码** |
| playbook 的增删改界面 | 内容由三个维护 API 重建（§7）、关系可直接在 DB 里改（版本化让就地修改安全，§4.8），界面按需再说 |

## 2. 方案结论

采用**新增 `process_type='PLAYBOOK'` + 关系边落 PG 表（递归 CTE）+ 两段式检索**。三条实测结论直接决定了检索形态：

| 实测结论 | 对设计的约束 |
|---|---|
| profile-only 路由 r@1 **80.9%**，混入 body 后跌到 **61.8%** | 检索**分两段**：先只查 profile 定位 playbook，再取 body 拿细节 |
| **56.2%** 的 DEPENDS_ON 前置项纯向量 top-5 召不到 | 关系边**必须保留**，且要能多跳扩展 |
| 合并关联文本进同一 chunk 为**负收益**（r@1 −5.1%） | 关系以**结构化边**存在，不以合并文本存在 |

> 选型文档里被否的"方案 2"是「playbook 混进公司 KB 的召回池、走 `search_knowledge_base`」——与本方案**不同**：本方案是独立处理类型 + 独立空间 + 独立工具，只复用 rag 的**分层骨架与公共文档表**，不复用 KB 的召回池，更不参与公司级圈定。

### 2.1 为什么走独立 `process_type`（v2 的核心决策）

`rag/CLAUDE.md` 的既有契约是「**一个处理类型 = 一套向量化 + 召回 + 存入 + 自己的一张 chunk 表 + 仓储，垂直内聚在 `processor/{type}/`**」。playbook 恰好在这四件事上**每一件都与 KB 不同**：切分要按节点而非字数、召回是两段式带图扩展、入库要额外产出 profile、正文来自爬取而非文件上传。硬塞进 STANDARD 就是在共用代码里到处开特例；顺着契约做反而更省。

**决定性的对比**——v1（复用 KB 表）需要三处受控放宽，v2 一处都不用：

| v1 要改的共用代码 | 风险 | v2 怎么免掉 |
|---|---|---|
| rag `filters` 加 `chunk_kind` 过滤键 | **紧邻租户隔离逻辑** `_recall_scope_from_filters`，误伤会串公司数据 | `PlaybookProcessor.recall` 在自己的表上自己写查询（`metadata->>'chunk_kind'` + `entry_id` 圈定），**`filters` 一个字不动** |
| `factory.vectorize_by_space` 加 `with_summary` | 全平台入库主干道 | 覆写 `PlaybookProcessor.summarize` 直接返回 `None`——基类注释原话"各业务类型可覆盖定制" |
| `business_association_service._validate_payload` 放行空作用域 | 关联表的作用域校验 | 不用业务关联表了：`process_type='PLAYBOOK'` 本身就是定位手段（§4.1） |

**注册进 `BUSINESS_REGISTRY` 后白得的能力**（`business_type → ChunkModel` 一处注册，六个调用方零改动）：

| 调用方 | 白得什么 |
|---|---|
| `space_service.create_space` | 建 PLAYBOOK 空间的校验直接通过 |
| `storage/factory.get_vector_store_for_space` | 按 space 路由到 playbook chunk 表 |
| `stats_service` | devSupport 的**空间页 / 文档页 / 片段页**直接能看 playbook |
| `search_service._record_recall` | 召回日志 + chunk/entry/space 三级 `hit_count` 自动累加 |
| `es_store` | 索引 mapping 维度按 PLAYBOOK 种子取 |
| `interfaces/routes.py GET /process-types` | 前端 New Space 下拉**自动**多出 `Playbook`（`processTypes.map()` 动态渲染）。另有 3 行前端硬编码要补，见 §1 末 |

代价只有一张新表 + 一次 HNSW 索引；顺带**不再把 playbook 的分段混进全平台 KB 表**（会话文件与公司知识库共用那张表，playbook 混进去会让它的统计、清理、召回范围都多一层"要不要排除 playbook"的判断）。

## 3. 模块落位

playbook 是一个**处理类型**，按 `rag/CLAUDE.md`「新增处理类型」的既定动作落位——`processor/playbook/` 垂直内聚一整套能力，编排在 `application/service`，两张属性表在 `domain/`：

```
source/rag/
├── domain/
│   ├── process_type.py                      ⚠️ 改：SYSTEM_SEEDS 加 PLAYBOOK 种子
│   ├── enums.py                             ⚠️ 改：RagOperationType 加三个 PLAYBOOK_* 值（§9.2）
│   ├── models/playbook_model.py             ai_playbook（属性 + 三个关系 JSONB 列）
│   ├── models/playbook_version_model.py     ai_playbook_version（版本 + 发布状态，§4.8）
│   └── repository/playbook_repository.py    属性表 CRUD + 递归 CTE 图扩展 + 版本表读写
│                                            （两表同域、一个仓储；关系是 ai_playbook 的列）
│
├── infrastructure/processor/playbook/       ⚠️ 新包：一个处理类型的一整套能力
│   ├── playbook_processor.py                PlaybookProcessor：_load / _split / _assemble
│   │                                        + 覆写 recall（两段式）+ 覆写 summarize（返回 None）
│   │                                        + route()：阶段 1 单独成方法，线上与评测脚本共用（§10.1）
│   ├── models.py                            ai_rag_playbook_chunk（一张向量分段表）
│   ├── repository.py                        本业务 chunk 仓储（profile 路由 / body 取正文两个查询）
│   ├── scraper.py                           源站爬取（raw HTML，不解析——原样上传 S3）
│   ├── html_parser.py                       HTML → pid/category/stage/questions/正文（bs4，无 LLM）
│   └── prompts.py                           关系推断系统提示词（单独成文件便于调优与 diff；
│                                            rag 的 summarize 提示词只两句、内联即可，此处不同）
│
├── infrastructure/processor/registry.py     ⚠️ 改：BUSINESS_REGISTRY 注册 playbook → chunk 表
├── infrastructure/processor/factory.py      ⚠️ 改：build_processor 加 PLAYBOOK 分支
│
├── application/service/playbook_service.py  维护编排（crawl / ingest）+ 检索编排（图扩展 + 拼装）
├── application/dto/playbook_dto.py          PlaybookHit / Related / PlaybookSearchResult / 维护结果
└── interfaces/
    ├── routes.py                            ⚠️ 改：挂三个端点 —— POST /playbook/crawl
    │                                        + /playbook/ingest + /playbook/versions/{v}/activate
    └── vo/{request,response}.py             ⚠️ 改：三个维护端点的 Request / Response

source/rag/infrastructure/files.py           ⚠️ 改：加 upload_bytes_via_java（presign → PUT → verify，
                                             与既有 download_ingest_file 对称）
source/lgpi_api/storage_upload_api.py        新增：Java 预签名上传客户端（presign + verify）

source/ai/tools/search_playbooks_tool.py     chatbot 工具（本期唯一新增工具）
scripts/eval_playbook_recall.py              召回回归评测（部署期/研发工具，不进 CI）
scripts/data/playbook/                       golden_queries.json（157 题金标）
```

**改既有文件只有 9 处**（§4.6 逐条列出，其中 1 处是迁移里的 CHECK 放宽），全是"加一个分支 / 加一个枚举值 / 加一个函数"的加法，**无既有行为改动**：`process_type.py` 加种子、`enums.py` 加三个操作类型、`registry.py` 加映射、`factory.py` 加 build 分支、`space_service.py` 加 PLAYBOOK 唯一守卫、`routes.py` + `vo/` 挂三个端点、`files.py` 加上传函数、`file_registry.py` 加两个登记函数，外加迁移里放宽 `ai_rag_space` 的 process_type CHECK。

四点说明：

- **爬取放 `processor/playbook/scraper.py`、不放 `scripts/`**：爬取是这个处理类型的**数据来源**，等价于别的类型的 loader；做成 API 后它是被 service 调的运行时能力，不再是一次性脚本。`_load` 有两个来源：DB 暂存（默认）或直连源站。
- **切分产出 profile + body 一次搞定**：`_split` 输出 `[profile 段, body 段 1..N]`，profile 参与同一批 embed，**不需要额外的 embedding 调用、也没有 seq 偏移问题**；`_assemble` 负责给两类打 `chunk_kind`（照 `StructuredProcessor` 覆写 `_assemble` 注入 `statement_type` 的先例）。
- **`recall` 与图扩展分工**：两段式**向量**召回（profile 路由 → body 取正文）在 `PlaybookProcessor.recall`——它是 Processor 契约里"每类型一套召回"的份内事；**图扩展在 `playbook_service`**——递归 CTE 走的是业务库的关系表，而 Processor 契约要求 stateless、不开事务、不查其它表。
- **`playbook_service` 同时管维护与检索**：两者共用"定位空间 → 定位 pid ↔ entry 映射"这套；拆两个文件会把同一份编排抄两遍。

#### ⚠️ 配套要更新**两个** CLAUDE.md（不只 rag 那个）

「两个处理类型」这个说法散落在两份文档里，漏改任何一处，下一个人按 CLAUDE.md 就读不出第三个类型：

**`source/rag/CLAUDE.md`**

| 位置 | 改什么 |
|---|---|
| 三、目录结构 | 加 `processor/playbook/`（6 个文件）、`domain/models/playbook_model.py` + `playbook_version_model.py`、`domain/repository/playbook_repository.py`、`application/service/playbook_service.py`、`application/dto/playbook_dto.py`；`interfaces/routes.py` 那行补三个维护端点 |
| 四、创建规则「新增处理类型（process_type）」 | 动作清单**拿 playbook 当范例**——它是第一个走完这条路的（种子 → processor 子包 → registry 注册 → build_processor 分支），比抽象描述好懂 |
| 五、特殊约定「process_type 与 embedding 配置是代码常量」 | "两处理类型"→**三**；补 PLAYBOOK 的固定 embedding 与 `business_type='playbook'` 映射 |
| 五、特殊约定 | **新增一条 playbook 专属**：空间按 process_type 定位且全局唯一（§4.1）、数据按版本存 + activate 才生效（§4.8）、关系是 `ai_playbook` 的三个 JSONB 列（§4.5）、维护走三个 API（§7） |
| 六、相关设计文档 | 加本文档路径 |

**`CIOaas-python/CLAUDE.md`**（子项目根的「RAG 知识库」节）

| 位置 | 改什么 |
|---|---|
| 核心概念 · process_type | `STANDARD` / `STRUCTURED` → 加 **`PLAYBOOK`**；`business_type` 一一对应关系加 `PLAYBOOK→playbook` |
| 核心概念 · 表布局 | 每业务一张 chunk 表的清单加 **`ai_rag_playbook_chunk`** |
| 核心概念 · Processor 接口 | 子类列表加 **`PlaybookProcessor`**（覆写 `recall` 两段式 + `summarize` 返回 None） |
| `interfaces/routes.py` 端点清单 | 加 playbook 三个维护端点 |

⚠️ 这两处**不是文档洁癖**：`rag/CLAUDE.md` 的「新增处理类型」清单是下一个人加第四个类型时唯一的操作指南，而 playbook 恰好把这条路走了一遍——不写进去，那份清单就仍停在"理论上应该这么做"的状态。

从 `feature/sprint112-age` **只搬数据与口径**，不搬代码：

| 搬 | 说明 |
|---|---|
| `playbooks_data.json` | 64 节点 + 28 条边（DEPENDS_ON 21 / FEEDS 5 / REFERENCES 2） |
| `playbooks_bodies.json` | 63 条正文（`define-the-vision` 在源站已并入 `executive-execution`，无正文） |
| `scrape_playbooks.py` | **改造成 `scraper.py`**（原样保留可复现性，改为可被 service 调用） |
| **切分口径** | `BODY_CHUNK_CHARS=1400` / `BODY_CHUNK_OVERLAP=150` / profile 文本格式 `"{title} ({category}). {description} Key questions: {questions}"` |

⚠️ **切分口径必须逐字照搬**：r@1 80.9% 的实测是在这个切法上跑出来的，换切法数字不作数。**这也是 PLAYBOOK 种子里 `default_chunk_size=1400` / `default_chunk_overlap=150` 的来源**（不用 rag 通用的 800/100）。

⚠️ **两个 JSON 的定位变了**：v1 里它们是导入脚本的数据源；v2 里**各环境自行 crawl 才是唯一数据来源**（§7.0.1 方案 A），JSON **不再作导入种子**，只留一个用途——**可复现基线**：crawl 后核对解析结果是否仍是 64 节点 / 28 关系 / 63 正文，不一致即源站改版信号（§11 步骤 5）。

不搬：LadybugDB 图文件（5.6MB）、`real-ladybug` 依赖、原型 service、原型 routes。

### 3.1 profile chunk 是什么、为什么这么拼（改它之前必读）

每个 playbook 入库成**两种表示**，职责不同：

| | 内容 | 职责 |
|---|---|---|
| **profile**（1 条，约 275 字符） | `title (category). description Key questions: <2~3 条问题>` | **检索名片**——回答"这本手册是干什么用的"，用于**路由**（阶段 1） |
| **body**（约 5 条 × 1400 字符） | 源站正文按段落切分 | **执行细节**——回答"具体怎么做"，用于**取正文**（阶段 3） |

以 `cash-flow-forecast` 为例，profile 渲染结果：

```
Cash Flow Forecast (Executive). Models monthly cash movements to predict cash
depletion and stress-test runway under different scenarios. Key questions: How
do I build an accurate cash flow forecast? What should I model beyond revenue
and expenses? How do I calculate runway?
```

而它的 body 第一段是 `Cash Flow Forecast | Players | Founder, CFO | Initial Effort | 13 SP | ...`（6583 字符切 5 段）。

用户问"我怎么算还剩几个月现金"时表达的是**意图**；body 段落是"第 3 步：把模型发给不同视角的人评审"这类**执行细节**，与意图对不上；profile 才对得上。这就是实测里 profile-only 路由 r@1 **80.9%**、混入 323 段 body 后掉到 **61.8%** 的原因——细节段会把正确 playbook 的名片挤下去。

**四段拼接各自在补什么**：

| 成分 | 作用 | 去掉的后果 |
|---|---|---|
| `title` | 术语锚点 | 用户直接说行话时召不回 |
| `(category)` | 领域上下文 | 跨领域同名概念分不开 |
| `description` | 一句话讲"解决什么问题" | 只剩标题 → 语义太稀疏，向量表达力弱 |
| **`Key questions:` + 2~3 条问题** | **把"用户会怎么问"直接写进被检索文本** | **最关键的一段，见下** |

最后一段是本设计的核心技巧：常规 RAG 是拿 **query 匹配文档正文**（问题 ↔ 陈述句，语义天生有距离）；把"预期问法"嵌进向量后变成 **query 匹配 query**（问题 ↔ 问题），距离天然更近。等于给每个 playbook 预置了一组假设性问题作检索入口——profile 的高召回主要来自这里。

**两个副作用（务必知道）**：

1. 这就是评测**必须先改写查询**的原因：157 条 questions 原文就在被检索文本里，直接拿它们当测试查询等于拿答案考试（§10）。
2. **80.9% 偏乐观**：questions 平均每 playbook 仅 2.5 条，覆盖的问法有限；且金标是从这些 questions 改写来的，存在语义泄漏。用户问法一旦偏离这 2.5 条的表达空间，profile 的优势会衰减，**线上真实召回大概率低于 80.9%**。对应的优化见 §13。

## 4. 数据模型：新增一个处理类型，补三张表

playbook 作为**独立处理类型**长在 rag 的分层骨架上，文档层仍用公共表：

| 承载什么 | 用什么 | 说明 |
|---|---|---|
| 处理类型 | `SYSTEM_SEEDS` 加 **`PLAYBOOK`** 种子 | 固定 embedding 配置 + 切分默认值 1400/150 + `business_type='playbook'` |
| 空间 | `ai_rag_space` 一个（`process_type='PLAYBOOK'`，**全局唯一**） | 页面 New Space 手建，选 `Playbook` 类型 |
| 空间定位 | **按 `process_type='PLAYBOOK'` 直查** | 不用业务关联表（§4.1） |
| 一个 playbook | `ai_rag_entry` 一行（`source_type='TEXT'`） | **公共文档表，全业务共用**——复用 title / summary / char_count / hit_count / status / deleted |
| profile + 正文分段 | **`ai_rag_playbook_chunk`（新增）** | 本处理类型专属的一张向量分段表 |
| **playbook 专属属性** | **`ai_playbook`（新增）** | pid / category / stage / questions —— rag 模型放不下 |
| **playbook 间关系** | **`ai_playbook` 的三个 JSONB 列** | `depends_on` / `feeds` / `refers_to`，不另立边表（D19） |

**复用公共 entry 表而非自建**：`ai_rag_entry` 是平台公共文档表（rag 已明确"文档不再按业务分表"），devSupport 文档页、召回记录、命中统计全指向它。自建一张 playbook entry 表会同时失去这三样，且违背 rag 现行表布局。

### 4.1 空间定位：按 `process_type='PLAYBOOK'` 直查，全局唯一

```
list_ids(process_type='PLAYBOOK')  →  0 个：兜底自建一个（§7.1）
                                   →  1 个：就是它（正常路径）
                                   →  N 个：报错，要求先清理到只剩一个
```

- **全局唯一**：playbook 是全平台共享的第三方方法论，一份就够。**多于一个必须报错而不是"取第一个"**——静默取第一个会让维护 API 往 A 空间灌、检索却读 B 空间，症状是"数据明明导进去了却召不回"，极难排查。
- **`process_type` 本身就是定位手段**，不需要业务关联表：关联表解决的是"哪个公司/用户能看哪些空间"，而 playbook 不做作用域圈定。这也顺带免掉 v1 里 `_validate_payload` 放行空作用域那处改动（D15）。
- **兜底自建**：查不到时由 `playbook_service` 建一个（名称 `Playbook Library`、切分参数取 PLAYBOOK 种子），让首次部署无需先去页面点一下。页面手建仍是首选路径——**手建能自己调切分参数**，兜底自建只用种子默认值。
- **不做"全局唯一"的 DB 唯一约束**：`process_type` 上加部分唯一索引会让"先建新的再删旧的"这种正常运维动作被卡住。改为 `space_service.create_space` 建 PLAYBOOK 空间时若已存在未软删的则拒绝（应用层守卫，可绕、可运维），配合定位处的 N 个报错双保险。

### 4.2 `ai_rag_entry`：一个 playbook 的一个版本 = 一行（每版本 64 行）

**为什么按 playbook 拆而不是整库一条**：entry 是 rag 的"文档"粒度，一 playbook 一行才能拿到——每条 playbook 独立的 `hit_count`（哪本手册最常被问到）、独立的软删（手工剔除某条时只停它）、以及 devSupport 文档页里可点开的条目。整库一条则这些全部失效。`ai_playbook.entry_id` 的 UNIQUE 映射（§4.4）也依赖这个粒度。

⚠️ **每个版本各建一套 entry、旧的不软删**（§4.8）：所以 N 个版本后表里有 64×N 行未软删的 playbook entry。这是版本化的必然代价——软删了就没法按版本跑召回测试。副作用是 devSupport 文档页条目变多，可接受（playbook 空间独立、只有运维会看）。

| 列 | 填什么 |
|---|---|
| `id` | entry 主键（UUID），playbook 的内部标识 |
| `space_id` | playbook 空间 |
| `company_id` | **NULL**（全平台；该列本就可空） |
| `source_type` | **`FILE`**——crawl 把原始 HTML 落了 S3（§7.0），所以 playbook 是真有文件的 |
| `title` | playbook 标题 |
| `content_text` | 从 HTML 解析出的正文全文（devSupport 文档页可看；权威原文在 S3） |
| `summary` | **直接写源站 `description`**——原文比 LLM 概括更准；`PlaybookProcessor.summarize` 覆写成返回 `None`，连 LLM 调用一起省掉（D16） |
| `chunk_count` / `char_count` / `total_tokens` / `status` | 由 `playbook_service` 在 ingest 末尾回写（§7.1 自行编排，不走 `ingest_text`） |
| `hit_count` / `deleted` | 前者由 rag 召回记录自动累加；后者软删时置位 |
| `file_id` | 填——指向 crawl 上传的那份整页 HTML（`files.id`）。⚠️ **同一版本的 64 条 entry 共享同一个 `file_id`**：源站是一个页面（§7.0） |
| `mime_type` / `file_size_bytes` | `text/html` / 整页 HTML 的字节数（同样是 64 条共享同一个值） |
| `thread_id` / `task_id` | 留空（非聊天来源；第一阶段同步执行、不建 ingestion task） |

#### ⚠️ 4.2.1 `company_id=NULL` 会让 rag 的同名去重失效（必须处理）

`ingest_text` 依赖同名覆盖来保证幂等——同 space 同 title 时软删旧 entry + 清其向量：

```python
dup = entry_repo.find_duplicate_title(company_id=company_id, space_id=space.id, title=dto.title)
if dup is not None:
    dup.deleted = True
    chunk_repo.delete_by_entry(entry_id=dup.id)
```

但 `find_duplicate_title` 里是 `.where(company_id == company_id)`——**传 None 会生成 SQL `company_id = NULL`，而 `NULL = NULL` 结果是 UNKNOWN 而非 true，查询恒返 None**。后果：

> 每次重跑 ingest，64 条 entry **全部重复新增、旧的一条都不软删**。跑三次就有 192 条活跃 entry、chunk 也翻三倍，路由召回全是重复 playbook。

三个可选处置，**已选 A**：

| 方案 | 做法 | 代价 |
|---|---|---|
| **A（已定）** | `playbook_service` **不调 `ingest_text`**，自己做 "按 (space_id, title) 查 → 软删旧 → **清旧向量** → 建新 entry → 向量化"，`company_id` 保持 NULL | 少复用一层薄编排，但幂等完全自己掌控；`ingest_text` 那段逻辑只有约 20 行 |
| B | 修 `find_duplicate_title` 支持 NULL（`company_id.is_(None)` 分支） | 动共用代码；虽然是纯 bug 修复，但要评估现有调用方是否依赖当前行为 |
| C | 给 playbook entry 填一个哨兵 `company_id`（如 `'PLATFORM'`） | 脏——`company_id` 语义被污染，且租户相关查询可能误命中 |

选 A 的额外理由：playbook 的 ingest 还要**额外产出 profile 分段**（§4.3）、**跳过 LLM 摘要**（D16），本来就超出 `ingest_text` 的既有行为，自己编排反而更直接。

⚠️ 注意 `ingest_text` 那段逻辑里**软删之后紧跟着 `chunk_repo.delete_by_entry`**——自己编排时这一步最容易漏，漏了的后果见 §7.1 第二条警告（实测踩过）。

### 4.3 `ai_rag_playbook_chunk`（新增：本处理类型的向量分段表，**零业务列**）

**结构 = `RagChunkBase` + `embedding`，一列业务字段都不加**，与 `EnterpriseKbChunk` / `FinancialReportChunk` 同构：

| 来源 | 列 |
|---|---|
| `RagChunkBase`（继承） | `id` / `space_id` / `file_id` / `entry_id` / `seq` / `content` / `content_tokens` / `metadata` / `hit_count` / `created_at` |
| 本业务自带 | `embedding`（维度取 PLAYBOOK 种子，与另两业务互不牵连） |

索引：`entry_id`（照另两张表的 `idx_*_chunk_entry` 惯例）+ `space_id`。

#### profile / body 用 `metadata.chunk_kind` 区分，不加正式列

**`chunk_kind` 是 rag 已有的跨业务约定**：`factory.py` 给正文分段标 `chunk_kind='body'`、`base.py` 给摘要分段标 `chunk_kind='summary'`，注释原话是「用独立 key `chunk_kind`（不占 loader 的 `content_type`=来源类型，两维度并存）」「召回侧据 metadata 可辨」。playbook 只是**多加一个取值 `profile`**。

| `chunk_kind` | 内容 | 用途 |
|---|---|---|
| **`profile`** | `"{title} ({category}). {description} Key questions: {questions}"`（§3.1） | **路由**（阶段 1）：只在此类上做向量检索。每 playbook 每版本恰 1 条 |
| `body` | 源站正文按 1400 / 150 切分 | **取正文**（阶段 3）；第一段是"Players / Effort / Frequency / Stage + 开篇"元数据块 |

**为什么不做成正式列**（单表看，正式列能建普通索引、加 CHECK、schema 自解释）：因为那会让**同一个概念在三张 chunk 表里有两种存法**——另两张表的 `body` / `summary` 在 metadata，playbook 的在列上。跨表一致性比单表最优更值钱：将来任何"按 chunk_kind 统计/清理/筛选"的通用代码，都得为 playbook 写特例。

**不会出现 `summary` 这一类**：`factory.vectorize_by_space` 里的摘要分段只在 `process_type == "STANDARD"` 时追加，PLAYBOOK 天然不走那条；再加上覆写 `summarize` 返回 `None`，**LLM 摘要调用本身也省了**（v1 为此要给共用函数加参数，见 D16）。

**为什么不借用 rag 的 summary 机制来充当 profile**：summary 是 LLM 对正文的概括、**不含 questions**，而 questions 恰是 §3.1 里 query↔query 匹配的关键成分、80.9% 路由准确率的主要来源。profile 必须是我们自己构造的独立一类。

#### ⚠️ 版本过滤靠 `entry_id`，chunk 表**也不存 version**

版本是**业务概念**，让它泄漏进向量库会多一处可能不同步的冗余。改为用 `entry_id` 圈定——每个版本的每条 playbook 各建一条独立 entry（§4.2），所以「某版本的全部 chunk」 ≡ 「该版本 64 个 entry_id 名下的 chunk」：

```
阶段 0（业务库，一条 SQL）：定位 space + 取生效 version + 该版本的 64 个 entry_id
阶段 1（向量库）：WHERE entry_id = ANY(:64 个) AND metadata->>'chunk_kind' = 'profile'
阶段 3（向量库）：WHERE entry_id = ANY(:seed 的) AND metadata->>'chunk_kind' = 'body'
```

**不会因此多一次往返**：阶段 0 本来就要查 `ai_playbook`（定位空间 + 生效版本），顺带把 entry_id 一起取出是零成本。传 64 个 UUID 进 SQL 约 2.4 KB 参数，可忽略。

⚠️ **这类查询不走 HNSW，但无所谓**：`entry_id = ANY(...)` 过滤 + 向量排序只能精确扫。单版本 profile 只有 64 条，**实测 0.099 ms**；多版本后 chunk 总行数 368×N，先按 `entry_id` 索引收窄到 368 条、再筛出 64 条 profile，仍是毫秒级。所以本设计**不依赖 HNSW**（索引仍建，供将来节点数量级上升时用）。

**metadata 上暂不建索引**：`entry_id` 索引已把候选收窄到单版本约 368 条，在其上筛 `chunk_kind` 是内存过滤。若将来 playbook 数量级上升，再加 `(entry_id) WHERE metadata->>'chunk_kind'='profile'` 部分索引即可（YAGNI）。

### 4.4 `ai_playbook`（新增：属性 + 关系，**按版本存**）

⚠️ **一行 = 一个 pid 的一个版本**（不是"一个 pid 一行"）。重跑 ingest **不动任何旧行**，而是整批生成下一版本的 64 行——见 §4.8 的版本化模型。

| 列 | 类型 | 约束 / 默认 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(36) | **PK**，default uuid4 | 主键（UUID） |
| `pid` | VARCHAR(128) | NOT NULL，**`UNIQUE(pid, version)`** | 业务键 = 源站 slug；**不再单列 UNIQUE**——同一 pid 每个版本各一行 |
| **`version`** | **INTEGER** | NOT NULL，**索引**，参与上面的复合唯一 | **全局数据版本**（不是"这条改了几次"）：一次 ingest = 一个版本 = 64 行 + 一套关系。生效状态在 `ai_playbook_version`（§4.8） |
| `entry_id` | VARCHAR(36) | NOT NULL，**UNIQUE** | 指向本版本这条 playbook 自己的 `ai_rag_entry.id`（每版本各建一条 entry，故仍全局唯一） |
| `category` | VARCHAR(64) | NOT NULL，**索引** | 6 值：Executive / Sales & Marketing / Development / Customer / Operations / Vendor |
| `stage` | VARCHAR(64) | **索引** | 5 值：Pre-Revenue / Early Traction / Traction / Growth / All Stages |
| `questions` | JSONB | NOT NULL DEFAULT `'[]'` | profile 的成分（§3.1） |
| `depends_on` | JSONB | NOT NULL DEFAULT `'[]'` | **我的前置** pid 数组（要先做的）——检索时递归 ≤2 跳 |
| `feeds` | JSONB | NOT NULL DEFAULT `'[]'` | **我喂给谁** 的 pid 数组——检索时**反查**（"谁喂给我"），1 跳 |
| `refers_to` | JSONB | NOT NULL DEFAULT `'[]'` | 软提及的 pid 数组，**不做图扩展** |
| `source_url` | VARCHAR(512) | | 溯源 |
| `deleted` | BOOLEAN | NOT NULL DEFAULT `false` | 软删（手工剔除某条时用；整版本的启停靠 §4.8 的 status，不靠这个） |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT `now()` | `updated_at` 由触发器维护 |

⚠️ **列名不能叫 `references`**：它是 PostgreSQL **保留关键字**（`pg_get_keywords()` catcode=`R`，用于 FK 语法），做列名必须处处带双引号。实测 `CREATE TABLE t (references jsonb)` 直接语法错误。故取名 `refers_to`。

**关系数组只存 pid、不带来源标记**：版本化已经解决了"重推冲掉人工修改"的问题（§4.8），不需要再给每个元素标 `llm` / `manual`。人工在某个版本的行上直接改，下次 ingest 生成的是**新版本的新行**，改动天然安全。

`title` / `description` **不在此表**——已在 entry 的 `title` / `summary` 里，不重复存。

**不建 `frequency` / `players` 列**：展示型元数据，不参与检索与过滤，且本就写在 body 第一段文本里；改为在取正文阶段固定带上 body 第一段（§5），连 JSON 里根本没有的 **effort** 也一起拿到。

**三个关系列不建 GIN 索引**：单版本 64 行，`feeds @> to_jsonb('x')` 全表扫是毫秒级（实测）。版本数上去后检索恒带 `version = :active`，扫的仍是 64 行。

### 4.5 关系：三个 JSONB 列，不建边表

28 条关系（DEPENDS_ON 21 / FEEDS 5 / REFERENCES 2）分散存进 64 行的三个数组列里。**实测两种存法的查询能力完全等价**（§5.1 给出跑通的 SQL）：

| 查询 | JSONB 写法 | 与边表结果 |
|---|---|---|
| DEPENDS_ON 递归 2 跳 | `CROSS JOIN LATERAL jsonb_array_elements_text(depends_on)` | 一致 |
| FEEDS 反查入边 | `WHERE feeds @> to_jsonb(:seed_pid)` | 一致 |

#### ⚠️ 4.5.0 丢掉的 4 个 DB 约束必须在应用层补上

这是本决策唯一的实质代价（D19）。边表本可由 DB 保证的事，现在**全是 ingest 的责任**：

| 原本靠 | 现在必须在 `playbook_service.ingest` 里做 |
|---|---|
| `FK → ai_playbook(pid)` | ⚠️ **写关系前先校验每个 target pid 都存在于本批 64 个 pid 中**。这是最要紧的一条——源站改了某个 slug 时，边表会当场拒绝插入，而 JSONB 会**静默存一个不存在的 pid**，症状是图扩展时少一个前置节点、**完全不报错**。校验不通过要**拒绝整批并列出坏 pid**，不能只跳过 |
| `UNIQUE(source,target,type)` | 合并时按数组元素去重（见 §7.2） |
| `CHECK rel_type IN (...)` | 三个列名就是类型，写错列名在 ORM 层即报错——这条**天然被列名替代了** |
| `CHECK source <> target` | 校验时顺带拒掉自引用（`pid` 出现在自己的任一关系数组里） |

**为什么仍值得并表**：28 条关系、64 个节点，两种存法性能零差别；少一张表 + 少一次 JOIN，读一个节点的全部关系就是一行。约束搬到应用层的代价是**一处集中的校验函数**，而不是散落各处。

#### ⚠️ 4.5.1 方向语义（最容易搞反，务必按此实现）

`depends_on` 里装的是**前置**（源 JSON 原话 "points to a prerequisite"），**不是**下游：

| 列 | 我这行的数组里装的是 | 反查（我出现在别人数组里）意味着 |
|---|---|---|
| `depends_on` | **我的前置**（要先做的） | 那些人依赖我（我的下游） |
| `feeds` | 我喂给谁（下游消费方） | **那些人喂给我**（我的输入源）← 检索用这个方向 |

实例：`Cash Flow Forecast --DEPENDS_ON--> Budget Creation --DEPENDS_ON--> Define the Mission`。**执行顺序恰好相反**：先定使命 → 再做预算 → 最后才做现金流预测。

两种心智模型都常见——"箭头 = 时间流向"（A→B 意为先 A 后 B）vs"箭头 = 依赖指向"（A→B 意为 A 需要 B）。**本数据用后者**；若按前者实现，诊断推荐会把执行顺序**整个颠倒**。

#### 4.5.2 `feeds` 无法由 `depends_on` 推导（实测）

5 条 `feeds` **全部**推不出来：`depends_on` 只覆盖 **28 / 64** 个节点，NPS、Churn Identification、Support Metrics 这三个度量类 playbook **完全不在依赖图里**；剩下那条（Product Roadmap → Adoption）两端虽在依赖图，却分属**互不连通的子图**。

所以 `feeds` 承载独立信息，删了真丢——它表达的是"哪些度量的产出会回流进某个流程"，这是 `depends_on` 表达不了的。所以三个关系列都要留，不能只留 `depends_on`。

### 4.6 ✅ 共用代码零放宽（v1 的三处全部消失）

v2 对 rag 共用代码**只有加法、没有行为改动**：

| 既有文件 | 改什么 | 为什么安全 |
|---|---|---|
| `domain/process_type.py` | `SYSTEM_SEEDS` 加一个 `PLAYBOOK` 条目 | 纯新增字典项；`PROCESS_TYPES` / `business_type_of` / `seed_for_business` 都是从它派生，自动生效 |
| `processor/registry.py` | `BUSINESS_REGISTRY` 加 `"playbook": PlaybookChunk` | 纯新增映射项；六个调用方零改动（§2.1） |
| `processor/factory.py` | `build_processor` 加一个 `elif process_type == "PLAYBOOK"` 分支 | 既有两分支不动 |
| `interfaces/routes.py` + `vo/` | 挂两个新端点 + 对应 Request/Response | 纯新增路由 |
| `application/service/space_service.py` | `create_space` 加一条 PLAYBOOK 全局唯一守卫（§4.1） | 只对 PLAYBOOK 生效，其余类型逐字节不变 |
| `domain/enums.py` | `RagOperationType` 加三个枚举值（`PLAYBOOK_CRAWL` / `_INGEST` / `_ACTIVATE`，§9.2） | 纯新增枚举项，复用现成的 `ai_rag_operation_log` 而非另造审计表 |
| `infrastructure/files.py` | 加 `upload_bytes_via_java`（presign → PUT → verify，§7.0） | 纯新增函数，与既有 `download_ingest_file` 对称；后者一个字不动 |
| `lg/db/service/file_registry.py` | 加 `register_playbook_file` + `list_playbook_files` | 纯新增函数。**不能复用 `upsert_kb_registration`**——它把 `business_type` 写死成 `KNOWLEDGE_BASE`，而用独立类型正是 §7.0 那两道保险的第二道 |
| ⚠️ **迁移**：`ai_rag_space` 的 CHECK 约束 | `chk_rag_space_process_type` 放宽到三值（V021 第 ② 段） | **实测才发现的第四处注册点**——Python 侧 `SYSTEM_SEEDS` / `BUSINESS_REGISTRY` / `build_processor` 三处全齐了，建 PLAYBOOK 空间仍被 DB 拒（`CheckViolation`）。这是 DDL 层的枚举，只能靠迁移放宽 |

**对比 v1 被免掉的三处**（每处都动共用逻辑，其中 filters 那处紧邻租户隔离）见 §2.1 的表格与 D14~D16。这是 v2 最主要的收益——多一张表换掉三处共用代码的风险。

### 4.7 库归属与跨库

| 表 | 库 | 迁移 |
|---|---|---|
| `ai_rag_space` / `ai_rag_entry` | 业务库（现状） | 无（已存在） |
| **`ai_rag_playbook_chunk`** | **向量库** | `sql/migrations/vector/V004__sprint115_playbook.sql`——建表（`RagChunkBase` 列 + `embedding`，零业务列）+ HNSW + `entry_id` / `space_id` 索引。⚠️ **迁移末尾要加一段结构自检**（见下） |
| **`ai_playbook`**（含三个关系列） / **`ai_playbook_version`** | **业务库**（与 space / entry 同库，可 JOIN） | `sql/migrations/business/V021__sprint115_playbook.sql` |

> 迁移号已按实际占用情况定为 business **V021** / vector **V004**（V019 / V020 与 vector V003 已被 sprint114 占用）。

⚠️ **迁移要防"同名脏表"**：`CREATE TABLE IF NOT EXISTS` 对"表已存在但结构不对"是**静默通过**的。V004 末尾加一段 `DO` 块校验关键列（`entry_id` / `space_id` / `content_tokens` / `embedding`）存在，缺任一就 `RAISE EXCEPTION` —— 让问题在**迁移期**暴露而不是运行期。这不是假想风险：选型评测期就在本地留下过一张同名实验表（§11 步骤 1）。

**跨库后果**：阶段 0 与阶段 2 在业务库（space / version / playbook / entry）、阶段 1 与阶段 3 在向量库（chunk）——共 **4 次交互**（§5）。全程按 `entry_id` / `pid` **点查**，**任何时候不写跨这两组表的 JOIN**——本地未配 `RAG_DATABASE_*` 时向量库会回退到业务库、看着能 JOIN，一上有独立向量库的环境就崩。

⚠️ **v1 已跑进本地库的数据要清理重导**：v1 把 64 条 entry 与 368 条分段写进了 `ai_rag_ent_kb_chunk`（STANDARD 空间）。v2 换表换空间，那批数据**不迁移、直接删**（源站可重爬，没有迁移价值）：删 PLAYBOOK/STANDARD 那个旧空间下的 entry 与其 chunk、删旧的业务关联行，再走 §7 的 API 重建。

### 4.8 版本化：重跑不动旧数据，新版本审核后生效

这是本设计的**核心运维模型**，取代原先"重跑就地覆盖 + 关系只增不删"的做法（D7 因此废除）。

```
ingest  →  生成 version N+1 的整套数据（64 行属性 + 一套关系 + 64 条 entry + 368 条 chunk）
           status = DRAFT，**线上检索完全看不到**
              ↓
人工审核（比 diff、按版本跑召回测试）
              ↓
activate →  version N   status: ACTIVE → ARCHIVED
            version N+1 status: DRAFT  → ACTIVE      ← 同一事务内切换
              ↓
线上检索立即读到新版本；旧版本原样留着，随时可 activate 回去（= 回滚）
```

**旧数据一行都不动**：旧版本的 `ai_playbook` 行、`ai_rag_entry`、chunk **全部保留、不软删**。所以：

- **人工修改天然安全**——不再需要"关系只增不删"这种策略，也不需要给关系元素标来源（§4.4）。你在 ACTIVE 版本上就地改的东西，下次 ingest 生成的是**新版本的新行**，碰不到它；
- **回滚是一次 activate**，不用重跑爬取与向量化；
- **可以按版本做 A/B**——devSupport 的召回测试传不同 version 就能比"opus 推的关系是不是比 sonnet 的好"（§13 会把选择版本做成页面能力）。

#### `ai_playbook_version`（新增：版本表，很轻）

| 列 | 类型 | 约束 / 默认 | 说明 |
|---|---|---|---|
| `version` | INTEGER | **PK** | 全局递增，ingest 时取 `max(version)+1` |
| `status` | VARCHAR(16) | NOT NULL，`CHECK IN ('DRAFT','ACTIVE','ARCHIVED','FAILED')` | **同时只能有一个 ACTIVE**，DB 层强制（见下）。`FAILED` = ingest 跑挂了（§7.1.2），不可 activate |
| `node_count` / `relation_count` | INTEGER | NOT NULL DEFAULT 0 | 本版本的节点数与关系元素总数（正常 64 / 28）。⚠️ **`node_count` 回填是 ingest 的最后一个动作，等价于 commit marker**——为 0 说明这批没跑完，activate 会拒（§7.1.2） |
| `relation_model` | VARCHAR(64) | | 推关系用的模型（如 `anthropic/claude-opus-5`）——**换模型后要能追溯是哪一版推的** |
| **`file_id`** | **VARCHAR(36)** | | 本次 ingest 实际用的那份整页 HTML（`files.id`，§7.0）。命名对齐项目惯例——`ai_rag_entry.file_id` / chunk 的 `file_id` 同样是指向 `files.id`。**各环境 version 号独立**，靠它区分"同一个版本号但源自不同抓取"（§7.0.1） |
| `note` | TEXT | | 审核备注 / 本次变更说明 |
| `created_at` / `created_by` | TIMESTAMPTZ / VARCHAR(36) | NOT NULL / | ingest 发起时间与操作人 |
| `activated_at` / `activated_by` | TIMESTAMPTZ / VARCHAR(36) | | 生效时间与审核人（DRAFT 时为空） |

**"同时只有一个 ACTIVE"用部分唯一索引在 DB 层兜住**（实测可行，PG 13+）：

```sql
CREATE UNIQUE INDEX uq_ai_playbook_version_single_active
    ON ai_playbook_version ((status)) WHERE status = 'ACTIVE';
```

实测行为：已有一行 ACTIVE 时再 UPDATE 第二行为 ACTIVE → `UniqueViolation` 直接拒绝；而"同事务内先把旧的降 ARCHIVED、再把新的升 ACTIVE"正常通过。**这条约束是必须的**——两个 ACTIVE 会让检索侧的"取生效版本"随机命中一个，症状是同一个问题两次答得不一样，极难排查。

**为什么单独建这张表、不把 status 放 `ai_playbook` 的 64 行上**：状态放 64 行上，切换要批量 UPDATE 64 行、且无法用一个约束保证"整批状态一致"（漏改一行就出现半个版本生效）。版本表一行一状态，切换是两条 UPDATE、约束是一个索引。而且版本本身有元数据要记（谁审的、用哪个模型推的关系、几个节点几条关系），这些放不进节点行。

#### 版本号从哪来、检索侧怎么用

- **写侧**：ingest 开头 `SELECT COALESCE(max(version),0)+1 FROM ai_playbook_version`，本次全部写入都带这个号；
- **读侧**：`playbook_service` 在**阶段 0 的同一条 SQL 里**拿齐三样（都在业务库，不增加往返）——space、生效版本号、**该版本全部 entry_id**（供向量库两阶段圈定，§4.3）：

  ```sql
  WITH active AS (SELECT version FROM ai_playbook_version WHERE status = 'ACTIVE')
  SELECT s.id AS space_id,
         (SELECT version FROM active) AS active_version,
         array_agg(p.entry_id) FILTER (WHERE p.entry_id IS NOT NULL) AS entry_ids
    FROM ai_rag_space s
    LEFT JOIN ai_playbook p
           ON p.version = (SELECT version FROM active) AND NOT p.deleted
   WHERE s.process_type = 'PLAYBOOK' AND NOT s.deleted
   GROUP BY s.id;
  ```

- **无 ACTIVE 版本时**（首次部署、或误把唯一的版本 ARCHIVED 了）：`active_version` 为 NULL → 工具返回 `ok=True, playbooks=[], note="playbook library is not published yet"`，**不报错、也不退化成查全部版本**。查全部版本会把 N 个版本的同一个 playbook 一起召回，比"没有结果"糟糕得多。

#### 旧版本数据的留存与清理

| 项 | 每版本增量 | 5 个版本 |
|---|---|---|
| `ai_playbook` 行 | 64 | 320 |
| `ai_rag_entry` 行 | 64 | 320 |
| `ai_rag_playbook_chunk` 行 | 368 | 1840 |
| 向量存储（1536 维 float4 ≈ 6KB/条） | ≈ 2.2 MB | ≈ 11 MB |

**第一阶段不做清理**（YAGNI）：13 MB 完全不值得为它写清理逻辑。版本攒多了再加一个 `DELETE /playbook/versions/{version}` 端点，**允许删 `ARCHIVED` 与 `FAILED`**（后者是跑挂的废版本，§7.1.2）。**不自动清 FAILED**——自动清会掩盖「上次跑挂了」这个事实。

⚠️ **两个已知副作用，接受**：

1. **devSupport 文档页会看到 64 × 版本数 个条目**（旧版本 entry 不软删——软删了就没法按版本跑召回测试了）。playbook 空间是独立空间、只有运维会点进去，可接受；将来页面加版本筛选即可。
2. **chunk 表的 HNSW 索引包含全部版本的向量**。检索靠 `entry_id = ANY(生效版本的 64 个)` 圈定（§4.3），召回集不受影响；只是索引体积随版本数线性增长——这也是上面那个清理端点的触发条件。

## 5. 检索链路（两段式 + 图扩展）

入口 `query` = 模型调 `search_playbooks` 时**自拟的检索词**（陈述式关键词，非用户原话直传；§6.1）。

⚠️ **全链路是 4 次数据库交互，不是 6 个串行步骤**——阶段 0（定位 + 取版本 + 取 entry_id）是一条 SQL；阶段 2 的「映射 / 扩展 / 取属性」三件事同在业务库、可 JOIN，**也必须合并为一条 SQL**。

**职责划分**：阶段 1 与阶段 3 是纯向量召回、在 `PlaybookProcessor.recall`（Processor 契约里"每类型一套召回"的份内事）；阶段 2 走业务库、在 `playbook_service`（Processor 要求 stateless、不开事务、不查其它表）。

⚠️ **`entry_id` 是贯穿全链路的传递键**（§4.3）：阶段 0 一条 SQL 拿到 space、生效 version、**该版本 64 个 entry_id**；阶段 1 在这个范围内检索、产出 seed 的 entry_id；阶段 2 用它换 pid 并做图扩展；阶段 3 再用它取正文。**chunk 表既不存 version 也不存 pid**（零业务列），版本与 pid 都在业务库侧。业务库侧（阶段 2）的查询仍要显式带 `version = :active`。

`active_version` 为 NULL（尚无 ACTIVE 版本）时**直接返回空结果**，不退化成查全部版本——退化会把 N 个版本的同一个 playbook 一起召回，比"没有结果"糟糕得多。

```
━━ 阶段 1 ┃ 向量库 ┃ 1 次查询 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【路由】在生效版本的 profile chunk 上向量检索（每 playbook 恰 1 条，共 64 条）
        → 产出 top_k(=3) 个 seed 的 **entry_id**
        · WHERE entry_id = ANY(阶段 0 拿到的 64 个) AND metadata->>'chunk_kind'='profile'
        · chunk 表只有 entry_id、**不存 pid**（§4.3 零业务列）——pid 由阶段 2 换取
        · profile 与 playbook 1:1，故无需"从 chunk 去重到 playbook"

              ↓  传 seed 的 entry_id[]

━━ 阶段 2 ┃ 业务库 ┃ 1 次查询（一条 SQL，含递归 CTE）━━━━━━━━━━━━

【映射】  entry_id + version → ai_playbook → pid / category / stage
【扩展】  读 ai_playbook 的三个关系列（同一张表，见 §4.5）：
              depends_on → 递归展开 ≤2 跳（前置）
              feeds      → **反查**谁的 feeds 含我，1 跳（输入源）
              refers_to  → 不扩展
【取属性】JOIN ai_rag_entry → title / summary
              seed 与扩展节点都取；扩展节点的 summary 即其简介
        · 三件事同库可 JOIN，务必**合并成一条 SQL**，别写成三次往返

              ↓  传 seed 与扩展节点的 entry_id[]（已带 pid / title / summary）

━━ 阶段 3 ┃ 向量库 ┃ 1 次查询 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【取正文】只取 seed 的 body chunk（`WHERE entry_id = ANY(seed 的 entry_id) AND metadata->>'chunk_kind'='body'`）
        每 seed = body 第一段（元数据块，固定带）+ 相似度前 2 段
        · 扩展节点**不取正文**——阶段 2 已给 summary 作简介，防 context 爆炸

              ↓

组装：3 个 seed（带正文）+ 各自 prerequisites / inputs（只带简介）
```

**检索词口径为什么重要**：docstring 明确要求"陈述式关键词、不要整句照抄"（与 `search_knowledge_base` 同口径），这对召回质量有实际影响——profile 里嵌的是 `Key questions`（§3.1），检索侧给出**主题式短语**比灌一整句带寒暄和上下文的原话更容易对上；而且 standard 轨在此之前还有 `rewrite_node` 补全过公司/指标/期间，模型手里已是明确的问题。**评测时也必须按这个口径构造查询**，否则测出来的数字与线上不同源。

**路由为什么只查 `profile`**：实测混入 body 会把 r@1 从 80.9% 拖到 61.8%。profile 是"这本手册解决什么问题"，天然匹配"我该怎么做 X"；body 是具体行文，适合当细节而非路由依据。

**路由的候选粒度（易误读，说清）**：一个 playbook = 1 条 entry = **1 条 profile chunk**，三者 1:1，所以在 64 条 profile 上取 top_k 条天然就是 **top_k 个互不相同的候选 playbook**，不需要"从 chunk 去重到 playbook"这一步。这是两段式的附带好处：预研版本在 387 条混合 chunk 上做 chunk 级召回，同一 playbook 的多个 body 段会**挤占候选名额**（top-10 条 chunk 可能只剩 4~5 个不同 playbook），选型评测就栽在这里——未对齐候选口径，一度得出"方案 3 +14%"的错误结论（见对比文档 §4.1）。

**扩展为什么按关系类型分方向**（§4.5.1 / §4.5.2）：

| 关系列 | 怎么走 | 为什么 |
|---|---|---|
| `depends_on` | **正向**递归展开，≤2 跳 | 数组里装的就是前置；补上那 **56.2%** 纯向量召不到的依赖项 |
| `feeds` | **反查**（谁的 `feeds` 含我），1 跳 | 有用的是"谁喂给我"（输入源）。正向读只会拿到下游消费方——预研 Q2（产品路线图）图增益几乎为零，正是因为拉进来的是弱关联下游。只走 1 跳：隔两层的输入源关系已很弱，拉进来是噪声 |
| `refers_to` | 不扩展 | 软提及（"预算正文里提了一句 KPI 周会"），既非前置也非数据流，跟着 2 跳只会稀释 context |

**取正文为什么固定带 body 第一段**：该段是"`Players / Initial Effort / Ongoing / Frequency / Stage` + 开篇"的元数据块。纯按相似度取 3 段时它未必入选（平均 5 段选 3），而"这事多久做一次、谁负责、要多少投入"恰是可执行答案的必要成分。固定带上它，等于用 0 成本换掉两个数据库列（§4.4）。

**扩展节点为什么只给简介、不给正文**：预研已验证展开正文会让 context 爆炸——2 跳能拉出十几个节点，每个再给 5 段正文直接超预算。而且没必要：用户问的是那几个 seed 怎么做，前置项只需说明"你还得先做 X"。简介直接用**阶段 2 已取回的 `ai_rag_entry.summary`**（= 源站 `description`），**不必再去向量库捞 profile 文本**。

**体量**：3 seed × 3 段 × 1400 字符 ≈ 12k 字符 ≈ 4k token，加扩展节点简介后单次工具返回可控。

**默认参数**：`top_k=3`；`depends_on` hops=2、`feeds` 反查 1 跳；每 seed 取 3 段（body 第一段 + 相似度前 2，去重后不足则少给）。

#### ⚠️ 5.1 图扩展 SQL：防环用 `path` 数组，**不得**用 `CYCLE` 子句

递归 CTE 遇环会无限递归，必须防环。两种写法，**本项目只能用前者**：

| 写法 | 版本要求 | 结论 |
|---|---|---|
| **手写 `path` 数组** + `NOT target = ANY(path)` | PG 8.4+ | ✅ **采用** |
| `CYCLE pid SET is_cycle USING path` 子句 | **PG 14+** | ❌ **不可用**——测试环境不支持 |

**实测（2026-07-28）**：

| 环境 | `server_version` | pgvector | 递归 CTE | `CYCLE` 子句 |
|---|---|---|---|---|
| 本地 docker | **18.3** | 0.8.2 | ✅ | ✅ 可用 |
| **测试环境** | **13.23** | **0.8.0** | ✅ | ❌ **语法报错** `ERROR 42601: syntax error at or near "CYCLE"` |

本地与测试**跨了 5 个大版本**，`CYCLE` 是唯一踩空的特性——**本地跑通不代表测试能跑**，故 §11 把环境自检列为步骤 0。

其余特性在 PG 13 上均已确认可用：递归 CTE（8.4+）、`jsonb_array_elements_text`（9.4+）、`CROSS JOIN LATERAL`（9.3+）、`@>` 包含判断、部分索引、`ARRAY` 与 `= ANY()`。pgvector 0.8.0 远高于 HNSW 所需的 0.5.0。**本设计除 `CYCLE` 外无任何版本依赖。**

**`depends_on` 正向递归展开（≤2 跳）——实测跑通的写法**：

```sql
WITH RECURSIVE
walk(pid, via, depth, path) AS (
    SELECT d.value, p.pid::text, 1, ARRAY[p.pid, d.value]::text[]
      FROM ai_playbook p
     CROSS JOIN LATERAL jsonb_array_elements_text(p.depends_on) AS d(value)
     WHERE p.pid = ANY(:seed_pids) AND p.version = :active AND NOT p.deleted
  UNION ALL
    SELECT d.value, w.pid, w.depth + 1, w.path || d.value
      FROM walk w
      JOIN ai_playbook p ON p.pid = w.pid AND p.version = :active AND NOT p.deleted
     CROSS JOIN LATERAL jsonb_array_elements_text(p.depends_on) AS d(value)
     WHERE w.depth < :hops
       AND NOT d.value = ANY(w.path)     -- 防环：走过的不再走
)
SELECT DISTINCT pid, via, depth FROM walk;
```

**`feeds` 反查（谁的 feeds 含我，1 跳，不需要递归）**：

```sql
SELECT pid FROM ai_playbook
 WHERE feeds @> to_jsonb(:seed_pid::text) AND version = :active AND NOT deleted;
```

用 `UNION ALL` 而非 `UNION`：后者每轮多一次去重排序；本查询靠 `path` 防环、结果层再 `DISTINCT`，不需要它。

⚠️ **递归 CTE 的每一列都要在 anchor 显式对齐类型（同一个坑踩了两次）**：PG 要求非递归项与递归项**逐列类型完全一致**，`varchar(128)`（带长度修饰）与 `text` / `varchar`（无修饰）**不是同一类型**，直接拒绝执行：

```
ERROR 42P08 DatatypeMismatch: 递归查询 "walk" 的第 N 列在非递归项中的类型是
character varying(128)，但整体类型是 character varying
HINT: 将非递归项的输出指派为正确的类型
```

两次都栽在这上面：第一次在 `path` 列（`ARRAY[p.pid, ...]` 推成 `varchar(128)[]`），第二次在 `via` 列（anchor 的 `p.pid` 是 `varchar(128)`，递归项的 `w.pid` 源自 `jsonb_array_elements_text` 是 `text`）。**规避办法就一条：anchor 里凡是取自表列的值统统 `::text`，数组统统 `::text[]`**，别指望 PG 自动收窄。用 `VALUES` 内联数据测不出这个问题（内联字面量本就是 `text`），必须接真表才暴露。

## 6. 工具契约与提示词

### 6.1 `search_playbooks`

```
search_playbooks(query: str, top_k: int = 3) -> {
  ok: bool,
  playbooks: [{
    pid, title, category, stage,
    excerpts: [str],                       # 正文段：body 第一段（元数据块）+ 相似度前 2 段
    prerequisites: [{pid, title, summary}],  # depends_on 正向递归展开的前置（只给简介）
    inputs: [{pid, title, summary}]          # feeds 反查（谁喂给我）的输入源（只给简介）
  }],
  note?: str,        # 无命中 / 关联项暂缺 / **playbook 库尚未发布**（§8.1）
  message?: str      # ok=false 的降级说明
}
```

**`prerequisites` 与 `inputs` 分成两个字段**、不合并成一个带类型标记的列表：二者语义完全不同——前置是"必须先做"（决定步骤顺序），输入源是"它的产出会喂进来"（决定数据依赖）。合并后模型得自己按类型标记分辨，容易把输入源误当成前置写进步骤序列。分开命名就没有歧义。

两者都**嵌在各 playbook 之下**而非平铺：模型要输出"先做 A 再做 B"的有序步骤，归属关系必须一眼可见。

返回值经 `_support/tool_result.tool_result` 序列化；`metadata = {"ui_label": ("Searching playbooks", "Searched playbooks"), "result_model": PlaybookSearchResult}`，文案随工具走、不在 chatbot 端另立映射表。

工具模块**不得写 `from __future__ import annotations`**（`Literal` schema 保真 / `ToolRuntime` 注入两个理由，v2 全包禁令）。

本工具**不带 `runtime` 参数、不需要 `ReqCtx`**——playbook 全局只读、不按公司过滤，没有任何要注入的鉴权或范围上下文。已有先例：`chart_validate_tool` 同为无 runtime 的纯函数式工具（`async def chart_validate_tool(spec) -> str`），照此实现即可。

### 6.2 与 `search_knowledge_base` 的分工

两者会被同一类问题命中，边界必须写死，否则模型乱调：

| | `search_playbooks` | `search_knowledge_base` |
|---|---|---|
| 数据 | **全局通用方法论**（第三方，所有公司同一份） | **用户自己上传的公司文件** |
| 回答 | "行业最佳实践该怎么做" | "你们公司的资料里怎么说" |
| 作用域 | 不按公司过滤 | 按 `company_id` 严格隔离 |

docstring 沿用既有四段式（何时用 / 何时不用 / 检索词 / 结果处理）。**新增一条红线**：playbook 是通用方法论，**绝不能说成"贵公司的资料显示…"**——把第三方方法论冒充成客户自有资料，性质等同编造。

### 6.3 触发方式

**模型按 docstring 自主调用**，不加斜杠命令、不加新 `agent_mode`，与 `search_knowledge_base` 一致。

## 7. 维护功能（三个 API）：抓取 / 计算 / 发布

第一阶段**不做页面**，三个端点手动调即可（Swagger / curl）。挂在 rag 现有前缀下、走 `_require_admin` 管理端闸门（与 rag 其它写操作同口径，公司端 403）。

| 端点 | 做什么 | 对线上的影响 |
|---|---|---|
| `POST /api/ai/rag/playbook/crawl` | 抓源站**整页** HTML（1 个页面含全部 64 个 playbook）→ 上传 S3 → `files` + `ai_file_registry` 各一行 | **无**（不动向量、不动版本） |
| `POST /api/ai/rag/playbook/ingest` | 从 S3 取 HTML → 解析 → 推关系 → 切分 → 向量化 → 写 **version N+1** 整套数据 | **无**——新版本是 `DRAFT`，线上检索看不到 |
| `POST /api/ai/rag/playbook/versions/{version}/activate` | 把某版本切成生效（旧的转 ARCHIVED），同一事务 | **有**，立即生效 |

**三个端点对应三件性质完全不同的事**：抓取（打外网、慢、易失败）／计算（本地、可重跑、产出待审草稿）／发布（一次事务、要人拍板）。发布单独成端点是版本化模型的必然结果——**ingest 不再直接影响线上**，所以它可以随便重跑。

**职责边界**：crawl 只负责把**不可再生**的东西（源站原始响应）安全落地；ingest 负责所有**可再生**的计算（解析 / 推关系 / 切分 / 向量化）。**两者之间没有暂存表**——S3 上的 HTML 就是暂存，`ai_file_registry` 里 `business_type='PLAYBOOK'` 的未软删登记行就是它的索引。

**为什么拆成两个而不是一条龙**：爬取要打外部站点，慢且易失败（网络 / 改版 / 限流），而 ingest 是纯本地计算 + embedding。分开后爬取失败不会连带重跑向量化，也能"先爬下来人工看一眼再决定要不要灌"。

**为什么不把 ingest 再拆细**（split / relations / vectorize 各一个端点）：切分、推关系、向量化、入库之间没有值得人工介入的检查点——**唯一需要人介入的检查点是「这批数据要不要上线」，那已经由 activate 承担了**。拆更细只会多出中间态与状态机。

**召回测试不另建端点**：devSupport 现成的 `POST /api/ai/rag/recall` 传 playbook 的 spaceId 就能测（§2.1）。

**长耗时**：ingest 全量约 64 次 embedding 批次 + 1 次关系推断，数十秒。第一阶段**同步返回**（管理端手动调、能等），返回体给出各步计数 + **与当前生效版本的 diff**（§7.2）。若后续嫌久，再挪到 `BackgroundTasks` + `ai_rag_ingestion_task`——rag 已有这套设施，届时是接线而非新造。

### 7.0 `crawl`：抓整页 HTML → S3 → 登记

⚠️ **源站是一个页面，不是 64 个**（实现前务必知道）：

```python
URL = "https://www.goldensection.com/vertical-saas-playbooks"   # 单个页面
soup.find_all("section", class_="playbook-section")              # 分类 section
  → sec.find_all("article", class_="play-card")                  # 每张 card = 一个 playbook
    → card.select_one(".play-content")                           # 正文也在 card 内
```

**64 个 playbook 及其全部正文都在这一个页面里**，体积约 **1.3–2.6 MB**（329 KB 纯文本 × 标签膨胀 4–8 倍）。所以 crawl 是**一次 HTTP 请求、一个 S3 对象、一条 `files` 行、一条登记行**——不是 64 份。

#### 为什么存 **HTML** 而不是提取后的 txt / json

| 理由 | 说明 |
|---|---|
| **爬取贵、解析便宜** | crawl 打外部站点、慢且易失败；解析是纯本地计算。存 HTML = 留住**不可再生**的原始响应，提取出的文本随时可重算。存解析结果等于把 bs4 规则固化在爬取那一刻——将来发现漏了某个区块（或源站改版后要调选择器），只能重爬 |
| **项目已有现成的 HTML 语义分割器** | `splitters/html_splitter.py` 的 docstring 原话："本期 loader 不产出 HTML……**保留此工具供未来 HTML 入库使用**"。它用 `HTMLSemanticPreservingSplitter` 按 `h2` 边界切、`preserve_links` / `preserve_images`。playbook 的 card 内部正是按小节组织的，**按 h2 切比按 1400 字符硬切更贴结构** |
| **能真正 diff 源站改版** | §11 要求"核对 64 节点 / 28 关系 / 63 正文，不一致说明源站改版，先看差异再决定要不要 ingest"。只有存了 HTML 才能 diff 出**页面结构**的变化（而不只是解析结果的差异） |

⚠️ **换 html_splitter 不会让 r@1 80.9% 失效**：那个数字只依赖 profile chunk（title + category + description + questions），与 body 怎么切无关；body 切法只影响"取正文"阶段的段边界（详见 §11 抽验里 323 / 365 / 304 三个数字的说明）。**但仍要在切换后用金标集跑一次对比**（§10），别凭推断。

⚠️ **预研没有保存过 HTML**：`scrape_playbooks.py` 抓完只写了两个解析结果 JSON、原始 HTML 用完即丢。所以**首次上线时手里没有 HTML 存档**，crawl 必须能访问源站——这条对部署有约束，见 §7.0.1。

#### 上传链路：经 Java 预签名，**Python 不直连 S3**

架构约定是 Python 不直连 S3（2026-07 起 boto3 直连下载已删除，只剩 SQS / Textract 用 boto3）。**不需要破例**——Java 已有预签名上传链路，正好是现有下载链路的镜像：

```
① POST /api/web/storage/uploads/presign
     body { fileBusinessType: "PLAYBOOK",
            files: [{ name: "vertical-saas-playbooks-{yyyyMMddHHmm}.html",
                      contentType: "text/html", size: <字节数> }] }     ← 只有 1 个文件
     ← [{ fileId, objectKey, httpMethod: "PUT", uploadUrl, requiredHeaders, expiresInSeconds }]
       ↑ fileId 由 Java 预生成并写入 files 表

② httpx PUT uploadUrl，带上 requiredHeaders（键值须与签名完全一致）+ HTML 字节

③ POST /api/web/storage/uploads/{fileId}/verify
     ← { fileId, status: "READY"|"FAILED", reason, size, etag, link, originalName }
       ↑ Java 做 HeadObject 校验；FAILED 时 reason ∈ S3_MISSING / S3_ERROR

④ 登记 ai_file_registry 一行：business_type='PLAYBOOK'、purpose='rag'、
     company_id=NULL、file_id、file_name、file_size
```

**文件名带时间戳**：每次 crawl 产出一个新对象、旧的留存，这样"源站在某个时间点长什么样"可追溯（与版本化的思路一致）。登记行按 `file_id` 各自一行，历史 crawl 的行不删。

**落位**：`lgpi_api/storage_upload_api.py`（一接口一文件，presign + verify 两个调用）+ `rag/infrastructure/files.py` 加一个 `upload_bytes_via_java`（编排 ①②③，与既有 `download_ingest_file` 对称同放一处）。

⚠️ **登记行的 `ai_rag_entry_id` 留空**：`ai_file_registry` 的既有语义是**一个文件对应一个 entry**（rag 流水线靠 `update_status_by_entry` 按它反查登记行、镜像向量化状态）。playbook 是**一个文件 → 64 条 entry**，打破了这个假设——`ai_rag_entry_id` 只能填 64 个里的 1 个，填了反而误导。故留空，`status` 由 ingest 自己维护（本来就不走 `ingest_pipeline`，用不到那套状态镜像，§4.2.1 方案 A）。

#### 7.0.1 部署：各环境自行 crawl（已确认测试 / 生产均可出网）

crawl 要访问 `goldensection.com`。**已确认测试与生产环境都能出网，故各环境自行 crawl**——不做"HTML 进仓库"或"JSON 种子导入"那两条备选路径（它们的数据血缘不同：前者仓库 +2.6 MB 且 HTML 变更让 git diff 难看，后者登记的是解析结果而非原始响应、失去 D21 的"可重解析"优势）。若将来出网策略收紧，再按这两条改。

⚠️ **由此产生的运维陷阱：各环境的 `version` 号相互独立，不可跨环境对齐。**

每个环境各自 crawl、各自从 `max(version)+1` 起编号，且抓取时间不同——源站在两次抓取之间可能已改版。所以**「测试环境的 v3」与「生产环境的 v3」不是同一批数据**。有人凭"测试 v2 验过了，生产也切 v2"来操作就会踩坑。

对策：版本表记 **`file_id`**（本次 ingest 实际用的那份 HTML 的 `files.id`）。它让"这个版本基于哪次抓取"可追溯——排查"为什么 v3 和 v2 的节点数不同"时，一眼能看出是源站变了（`file_id` 不同）还是模型推的关系变了（同一个 `file_id`、不同 `relation_model`）。

#### 7.0.2 抓取参数：一次请求，httpx，退避重试 3 次

源站是一个页面（§7.0），所以整个 crawl **只有一次 HTTP 请求**——重试策略因此很简单：

| 项 | 取值 | 理由 |
|---|---|---|
| HTTP 客户端 | **httpx**（async） | 与既有 `download_ingest_file` 一致。预研用的是标准库 `urllib.request`，**不照抄**——项目已统一 httpx，混用两个客户端没必要 |
| 超时 | **60s** | 页面 1.3–2.6 MB。预研设的 30s 偏紧，网络稍慢就会假失败 |
| `User-Agent` | **必须带**（预研用 `Mozilla/5.0`） | 预研显式设了它，说明源站可能拒默认 UA（Python 的默认 UA 常被反爬拦）。照搬 |
| 重试 | **3 次，指数退避 1s / 2s / 4s** | 只对**网络错误与 5xx** 重试；**4xx 不重试**——重试也不会变好，直接失败让人看到（403 大概率是反爬、404 是源站改了路径，两者都需要人介入） |
| 重试安全性 | 天然安全 | crawl 在 presign 之前失败**零副作用**（§8.2），重试不会产生多余的 S3 对象或登记行 |

**不做定时自动 crawl**：第一阶段手动触发（D18）。若将来接定时任务，要一并加 §7.1.2 提到的 `pg_try_advisory_lock`，并把"源站改版导致解析节点数骤降"做成告警——否则自动化会静默产出一堆 `FAILED` 版本。

#### ⚠️ Java 侧要加一个 `FileBusinessTypeEnum.PLAYBOOK`（3 行）

**不能复用 `KNOWLEDGE_BASE`**——它的扩展名白名单 `ExtSets.KNOWLEDGE` 是 `pdf / docx / xlsx / xls / csv / txt`，**不含 html**，拿它传 `.html` 会被 presign 直接 `BadRequestException` 拒掉。

`FileBusinessTypeEnum` 把 `code` / S3 目录段 `folder` / 扩展名白名单 / 大小上限绑在一起，presign 校验与 verify 反解共用；类注释原话"**新增一种文件业务类型只需在此登记一个枚举值，无需改动 service**"。所以改动是：

```java
// ① 枚举体加一行（10 MB 上限对 2.6 MB 的整页 HTML 有充足余量）
PLAYBOOK("PLAYBOOK", "playbook", ExtSets.PLAYBOOK, 10);
// ② ExtSets 加一行（只允许 html——各环境自行 crawl，不需要 json 种子，§7.0.1）
private static final Set<String> PLAYBOOK = Set.of("html");
// ③ StorageUploadPresignRequest 的 @Schema description 补上 PLAYBOOK（纯文档字符串）
```

`fromCode` / `fromFolder` 都是遍历 `values()`，**自动生效；service / controller 零改动**。

**为什么不给 `ExtSets.KNOWLEDGE` 加 `html`（只需 1 行、更省）**：那个白名单管的是**所有**走 KB 通道的上传，包括公司用户在 chat 里传的文件。放开 html 等于允许用户上传**可执行内容**（含 `<script>`），将来任何地方直接渲染就是 XSS 面。playbook 是我们自己爬的可信内容，与用户上传的 HTML 不是一回事——用独立枚举把接受面隔开，顺带 S3 目录独立成 `uploads/playbook/`，以后单独统计 / 清理也方便。

#### 两个 `business_type` 是不同维度，别混

| 字段 | 取值 | 决定什么 | 改动 |
|---|---|---|---|
| Java presign 的 `fileBusinessType` | **`PLAYBOOK`** | S3 目录段 `uploads/playbook/` + 扩展名白名单 + 大小上限 | Java 加 3 行（见上） |
| `ai_file_registry.business_type` | **`PLAYBOOK`** | chatbot 知识库检索圈定 | 枚举**本来就有这个值**（V013 注释），零改动 |

两者恰好同名但**互不相关**：前者是 Java 存储域的上传分类，后者是 Python 侧的业务登记分类。

⚠️ **登记进 `ai_file_registry` 为什么不会串进别的公司的知识库检索**（安全关键，已核实实现）——两道保险：

1. `list_kb_space_ids` 用的是 `AiFileRegistry.company_id.in_(company_ids)`，而 playbook 登记行 `company_id` 是 **NULL**——`NULL IN (...)` 恒为 UNKNOWN，**任何公司的 KB 圈定都匹配不到它**；
2. 该函数还要求 `business_type == 'KNOWLEDGE_BASE'`，而我们登记的是 `'PLAYBOOK'`。**这是刻意照抄会话文件的做法**——会话文件 `company_id` 同样恒 NULL，它的注释原话是"`business_type='SESSION_UPLOAD'`（≠ KNOWLEDGE_BASE）使其不进 `list_kb_space_ids` KB 圈定"。

第 2 道保险单独看是冗余的，但**必须留**：万一将来有人给 `list_kb_space_ids` 加"全平台公共知识库"支持（放开 NULL），playbook 会突然被圈进**所有公司**的检索范围。用一个不同的 `business_type` 把这条路堵死。

### 7.1 `ingest`：产出一个 DRAFT 版本

1. **分配版本号**：`SELECT COALESCE(max(version),0)+1 FROM ai_playbook_version`，本次全部写入都带它；同时插入版本表一行（`status='DRAFT'` / `created_by` / `relation_model` / **`file_id`**＝步骤 3 取到的那份 HTML 的 `files.id`）；
2. **定位空间**：`process_type='PLAYBOOK'` 直查 → 0 个兜底自建 / N 个报错（§4.1）；
3. **取素材**：查 `ai_file_registry` 里 `business_type='PLAYBOOK'` 未软删登记行中**最新的一条**（按 `created_at` 降序），经 `download_ingest_file` 从 S3 拉那**一个**整页 HTML（**Python 不直连 S3**，走 Java 预签名 GET）；
4. **解析整页 → 64 个节点**（bs4 确定性解析，**无 LLM**）：遍历 `section.playbook-section` → `article.play-card`，每张 card 取 pid / title / category / stage / players / frequency / description / questions / 正文（`.play-content`）；⚠️ **解析出的节点数 < 阈值（如 50）要拒绝整批**——源站改版导致选择器失效时会静默解析出 0 个，不能让它产出一个空 DRAFT（同 §7.1.1 边数上限，属同一类防线）；
5. **推断关系**（⚠️ **本流程唯一的非 embedding LLM 调用**，细节见 §7.1.1）：把全部 64 个节点一次喂给 opus5，产出 `depends_on` / `feeds` / `refers_to`。**必须等全部解析完**——关系是跨节点的，逐个文件边解析边推无从下手；
6. **校验 pid**（§4.5.0）：LLM 可能吐出**不存在的 pid**（幻觉）。逐个核对是否在本批 64 个 pid 内，不通过则**拒绝整批并列出坏 pid**，不静默跳过；
7. **逐条写 entry + 分段**：每条 playbook 建**一条新 entry**（`source_type='FILE'`、`file_id` 填登记行的、`mime_type='text/html'`、`company_id=NULL`、`summary` 写源站 `description`）→ `PlaybookProcessor` 一次产出 profile + body 分段，全部带 `version = N+1`；
8. **写属性与关系**：`ai_playbook` 插入 64 行新行（带 `version`）；
9. **回填**版本表的 `node_count` / `relation_count`，以及登记行的 `space_id` / `ai_rag_entry_id` / `status`。

⚠️ **全程只插入、不更新、不软删任何既有行**。这是版本化模型的根本（§4.8）——线上仍读 ACTIVE 版本，ingest 失败或产出垃圾都碰不到它。**这也让 ingest 天生可重跑**：失败了再调一次，代价只是多一个废弃的 DRAFT 版本。

⚠️ **不复用 `ingest_service.ingest_text`**：它靠 `find_duplicate_title(company_id=...)` 做同名覆盖来保证幂等，而 playbook 的 `company_id` 是 NULL——SQL 里 `company_id = NULL` 恒为 UNKNOWN、查询永远返回 None（§4.2.1）。不过**这个坑在版本化之后反而无关了**：我们本来就不要「同名覆盖」，要的是「同名并存、按版本区分」。此处列出只为说明为什么不用它。

⚠️ **空正文只出 profile**：`define-the-vision` 在源站已并入别的 playbook、无正文。若照常走流水线，loader 在正文为空时会退化成「拿 title 当内容」、产出一条 17 字符的 body 段——纯噪声，会参与取正文阶段的相似度检索。正确结果是这条 playbook **只有 1 条 profile 分段**。

#### ⚠️ 7.1.1 关系推断（ingest 唯一的非 embedding LLM 调用）

**源站不提供任何关系信息**——这是本设计最容易被误解的一点。预研的 `scrape_playbooks.py` 分得很清：节点字段（title / category / stage / players / frequency / description / questions / 正文）是 **bs4 确定性解析、无 LLM**；关系是**全靠 LLM 基于领域知识推断**（方案 B）。所以关系不是"抓来的数据"，是**推出来的假设**，必须经人审核才能当权威源用（§7.2）。

**输入**：全部 64 个节点各一行，`pid | category | stage | title — description`（实测 2008 token）。

**输出**：`{"edges":[{"from":..,"to":..,"relType":..}]}`（当前 28 条 = 实测 790 token，单条均摊 28 token）。

| 参数 | 取值 | 说明 |
|---|---|---|
| 模型 | **`Models.openrouter.text.opus5`**（`anthropic/claude-opus-5`） | 见 D27。**钉住具体版本、不用 `opus` 符号**——输出要人工审核后长期沉淀，registry 静默升级会让"这版为什么和上版不同"多一个说不清的变量，`relation_model` 的记录也就失去确定含义 |
| 可覆盖 | `ingest` 的可选入参 `relationModel` | 版本化让 A/B 成为可能：跑一版 sonnet5、跑一版 opus5，diff 后择优 activate |
| `max_tokens` | **8000**（预研 4000） | output 按实际用量计费，上限本身零成本。提高只为兜住"模型吐出带缩进 / 带额外字段的冗长格式" |
| `temperature` | `0.0` | 沿用预研。注意 **0 不保证逐次一致**，这正是要 diff 审核的原因 |
| `json_mode` | `True` | ⚠️ 落成 `response_format={"type":"json_object"}`（OpenAI 风格）。Anthropic 原生没有此模式，走 OpenRouter 时是转译，**不是硬保证**——必须保留预研的 `parse_json_response` 容错解析（能处理 ` ```json ` 包裹等），别以为开了就能直接 `json.loads` |
| `call_purpose` | `playbook_edge_infer` | 落 `ai_llm_call_log`，成本与 token 用量可查 |

##### 必须单次全局调用，不可分批

64 个节点一次喂给模型。将来若有人为了"更聚焦 / 更细致"改成分批（如按 category 分 6 批），会**推不出跨 category 的关系**——而实测 5 条 `feeds` 边**全部跨 category**（NPS / Churn / Support Metrics 属 Customer，喂给属 Development 的 Product Roadmap）。分批等于把 `feeds` 这一类关系整体废掉（§4.5.2 已证明它无法由 `depends_on` 推导）。

##### 三条防线，主防线是边数上限而不是 token 上限

| 防线 | 挡什么 |
|---|---|
| **① 提示词给边数指引** | 源头抑制过度生成。明确写「只输出最确定的关系，总数通常 30 条左右」——`refers_to`（软提及）判断标准最松、最容易泛滥 |
| **② 边数上限 96 = 节点数 × 1.5（主防线）** | 质量灾难入库。超限 **拒绝整批 + 报警**，不截断——半批关系比没关系更难排查 |
| **③ `max_tokens=8000` + `finish_reason=='length'` 检测** | 万一真被截断。检测要在 `parse_json_response` **之前**，因为两种失败的处置完全不同：截断 → 调上限；非法 JSON → 改提示词。混成同一个 parse 失败会白花排查时间 |

⚠️ **为什么主防线是边数、不是 token**：实测 `max_tokens=4000` 能装 **141 条边**，余量 5 倍——token 根本不是瓶颈。而边数从 28 涨到 141 意味着 2 跳图扩展能拉出的节点数**平方级增长**，§5 算过"2 跳十几个节点、每个再给正文就超预算"，那批数据**不该入库**而不是"想办法装下"。96 条边只占 2707 token，**这条校验永远比 token 上限先触发**，等于把截断这个失败模式屏蔽掉。

阈值 96 的来由：当前 28 条，留 3 倍余量容纳"opus 更细致"；再往上就进入图扩展会爆的区间。数字可按实际调，但**必须有**。

##### 实际用量靠日志确认，不靠猜

首次 ingest 后查 `ai_llm_call_log` 里 `call_purpose='playbook_edge_infer'` 那条的 `output_tokens` / `cost_usd`（走 OpenRouter 时是 provider 回传的**真实成本**、不走本地价表估算），据此决定要不要调整上限。

##### 为什么不给输入加 questions 或正文（实测否掉）

| 候选输入 | 实测结果 | 结论 |
|---|---|---|
| **questions** | 157 条 questions 里**只有 2 条（1.3%）**提到别的 playbook 的特征词，且那 2 条指向的关系**现有边集已覆盖** | 不加。questions 按 §3.1 的设计意图是"用户会怎么问这一本"，是**单个节点的检索入口**，天然不承载节点间关系 |
| **正文开篇** | 63 篇正文的前 600 字符里，含 `before` / `prerequisite` / `builds on` 等前置线索词的**只有 3 篇**，且全是误报（"identify customers **before** they churn" 是业务语义、"D&O insurance **before** fundraising" 是被拼进正文的 questions） | 不加。**源站根本不写前置依赖** |

这两组数字解释了预研为什么选"LLM 推断"（方案 B）——**不是偷懒，是源站确实没有这个信息**。也意味着：**输入侧没有可加的事实依据**，能改善关系质量的杠杆只剩「换更强的模型」和「人工审核」两条。

#### ⚠️ 7.1.2 中途失败：靠 activate 前的完整性校验，不靠事务

ingest 写 64 条 entry（业务库）+ 368 条 chunk（**向量库**）+ 64 行属性（业务库），中间还夹着 64 次 embedding 与 1 次关系推断的网络调用。失败可能发生在任何一步，后果是**留下一个不完整的 DRAFT 版本**——而它一旦被 activate，线上就静默少掉若干 playbook。

##### 为什么不能用事务兜住

**跨库事务做不到**：entry / 属性在业务库、chunk 在向量库，需要 2PC，项目没有也不该有。即使退化成单库（本地未配 `RAG_DATABASE_*` 时两库重合），事务里还包着几十秒的 embedding 网络调用——长事务阻塞 vacuum、占连接。rag 现有的 `ingest_pipeline` 同样是分步提交 + entry 状态机，不用大事务。

##### 主防线：`node_count` 当 commit marker + activate 前校验

| 机制 | 说明 |
|---|---|
| **`node_count` 回填是 ingest 的最后一个动作** | 版本表插入时 `node_count = 0`，全套数据写完才回填成 64。**它等价于一个 commit marker** |
| **`activate` 前校验完整性** | 见下三条 SQL。校验不过 → 拒绝 activate 并指出缺什么 |
| **失败时把版本标 `FAILED`**（补充手段） | 让人一眼看出哪一版跑挂了，而不是留一堆 `node_count=0` 的 DRAFT 去猜。`status` 因此有四态：`DRAFT` / `ACTIVE` / `ARCHIVED` / `FAILED` |

⚠️ **为什么主防线是校验而不是"失败时标 FAILED"**：标 FAILED **依赖失败处理路径能执行**——进程被 kill（OOM / 部署重启 / 手动中断）时 catch 根本跑不到，版本会永远停在不完整的 DRAFT。而校验是**验证结果**，不依赖进程如何退出：进程被 kill 时 `node_count` 还是 0，activate 直接拒。

##### activate 的三条校验

```sql
-- ① 属性行数对得上（业务库）
SELECT count(*) FROM ai_playbook WHERE version = :v AND NOT deleted;
-- 须 == node_count 且 > 0

-- ② entry 数对得上（业务库）
SELECT count(*) FROM ai_rag_entry
 WHERE id IN (SELECT entry_id FROM ai_playbook WHERE version = :v) AND NOT deleted;

-- ③ ⚠️ 每个 entry 都有 profile 分段（向量库，最关键）
SELECT count(DISTINCT entry_id) FROM ai_rag_playbook_chunk
 WHERE entry_id = ANY(:该版本 entry_id) AND metadata->>'chunk_kind' = 'profile';
-- 须 == node_count
```

⚠️ **③ 最关键**：profile 是路由阶段**唯一**被检索的分段（§4.3）。某条 playbook 缺了它 → **那本手册永远召不回，且不报任何错**，属于最难发现的一类数据缺陷。这是一次跨库**点查**（按 entry_id，不是 JOIN，符合 §4.7 的约束）。activate 是低频运维动作，多两次 count 无所谓。

##### 两个连带问题

**并发 ingest：不加锁，因为版本化已经让并发无害**。先算清危害再决定要不要防：

| 时序 | 结果 | 代价 |
|---|---|---|
| 第二个在第一个提交版本行**之后**开始 | 各自拿到不同版本号（3 和 4），**独立写数据、互不干扰**（版本天然隔离） | 浪费一次 embedding（约 $0.05）+ 多一个废版本（可删） |
| 两个几乎**同时**开始 | 都算出同一个号 → 第二个 INSERT 撞版本表主键 → **在第一步就失败，还没写任何数据** | 一条报错 |

**两种情况都不损坏数据**——数据安全由版本表主键 + 版本隔离共同保证。所以只需把主键冲突转成友好文案：

```python
except IntegrityError:
    raise RagBusinessError("版本号冲突，可能有另一个 ingest 正在运行，请稍后重试")
```

⚠️ **为什么不用 `pg_advisory_lock`**（`scripts/migrate.py` 有先例）：它是**会话级**锁，绑在**具体那条连接**上、不随事务结束释放。migrate.py 能用是因为它自己开一条独占裸连接（`psycopg.connect(autocommit=True)`）、进程退出即断连释放；而 ingest 是 HTTP 端点、走 SQLAlchemy 连接池、分步提交，每步的 `get_session()` 可能拿到不同连接——**锁会白拿**。要做对就得整个 ingest 期间持有一条专用 AUTOCOMMIT 连接 + `try/finally` 释放，还要防「忘了 unlock 导致连接被池回收后永久持锁」。为省几分钱引入这套复杂度不值。

（顺带说明 advisory lock 本身的性质，免得被误解：它是**应用层协作锁**，PG 只维护「锁 ID → 持有者」注册表、**不锁任何表 / 行 / 库**，对其他查询零影响；只有请求同一个 ID 的会话才等待。将来若接了定时自动 ingest 再引入，且要用**非阻塞版 `pg_try_advisory_lock`**——HTTP 端点不该用阻塞版把请求挂住几十秒。）

**失败版本的垃圾**：每次失败留一个废版本占着 chunk 表的行。§4.8 那个 `DELETE /playbook/versions/{version}` 端点要**允许删 `FAILED`**（不只 `ARCHIVED`）。但**不自动清**——自动清会掩盖「上次跑挂了」这个事实，运维应该看见它。

### 7.2 `activate`：审核后发布，兼回滚

```
POST /api/ai/rag/playbook/versions/{version}/activate
  body { note?: "审核说明" }
```

**同一事务两条 UPDATE**：当前 `ACTIVE` 降为 `ARCHIVED` → 目标版本升为 `ACTIVE`，并写 `activated_at` / `activated_by`。§4.8 那个部分唯一索引在 DB 层兜住「同时只有一个 ACTIVE」（实测：出现第二个 ACTIVE 会被 `UniqueViolation` 拒绝，而同事务内先降后升正常通过）。

- **只允许 activate `DRAFT` 或 `ARCHIVED`**；`FAILED` 直接拒（§7.1.2）；对已 ACTIVE 的版本调用是 no-op、直接返回成功（幂等）；
- ⚠️ **切换前先跑 §7.1.2 的三条完整性校验**，任一不过就拒绝并指出缺什么——这是防「半成品 DRAFT 被切上线」的唯一防线；
- **回滚 = activate 旧版本**，不需要单独端点、也不需要重跑爬取与向量化；
- **不做「ingest 完自动 activate」**：那等于绕过审核，把版本化的意义抹掉。

#### ingest 返回体给出 diff（人工审核的依据）

审核成本要压到「看一眼 diff」，否则没人会认真审。ingest 返回体除各步计数外，给出与**当前 ACTIVE 版本**的对比：

| diff 项 | 为什么要看 |
|---|---|
| 节点：新增 / 消失的 pid | 源站改版最直接的信号 |
| 节点：`title` / `description` / `questions` 变化的 pid | questions 变了会直接影响路由准确率（§3.1） |
| **关系：新增 / 消失的三元组**（`pid --rel--> pid`） | ⚠️ **审核重点**。关系是 LLM 推的、逐次不完全一致；换模型时这份 diff 是唯一的质量闸门 |
| 计数对比 | 出现 64 / 28 之外的数字，先查原因再 activate |

⚠️ **关系质量没有 ground truth，人工审核是唯一闸门**：§2 那条「56.2% 的前置项纯向量召不到 → 关系必须保留」是**基于 LLM 推的边**算出来的，等于用 LLM 的输出证明 LLM 输出的价值。而 §7.1.1 的两组实测更进一步说明：**输入侧根本没有事实依据可加**——questions 只有 1.3% 提到别的 playbook、63 篇正文里只有 3 篇（且全是误报）含前置线索词，**源站不写依赖关系**。所以关系是纯推断产物，换模型会得到另一组边而**没有客观办法判断哪组更好**。64 个 playbook / 28 条关系，一个懂业务的人能审完，这就是闸门。审核通过后可在 ACTIVE 版本上就地修正个别关系（版本化让这种修改安全，§4.8）。

**按版本跑召回测试**：devSupport 现成的 `POST /api/ai/rag/recall` 传 playbook 的 spaceId 即可，但它默认打 ACTIVE 版本。要测 DRAFT 版本得让 `filters` 支持传 `version`——第一阶段先靠**直接查库看新版本内容**审核，把「页面上选版本测试」留到 §13。

368 段重嵌约 $0.003、数秒，**不做 content-hash 增量**（YAGNI）。

## 8. 错误处理

### 8.1 检索侧（`search_playbooks` 工具）

| 情形 | 返回 |
|---|---|
| **尚无 ACTIVE 版本**（首次部署、或唯一版本被 ARCHIVED 了） | `ok=True, playbooks=[], note="playbook library is not published yet"`——**这是"还没发布"而非"故障"**，不报错 |
| **PLAYBOOK 空间不存在**（还没建） | 同上 |
| **PLAYBOOK 空间有多个** | `ok=False` + 明确错误。这是**配置错误**，必须让人看见（§4.1：静默取第一个会造成"灌 A 读 B"） |
| 向量库不可用 / SQL 异常 | `ok=False, message="playbook library is temporarily unavailable"` |
| embedding 调用失败 | 同上 |
| 检索无命中 | `ok=True, playbooks=[], note=...` |
| **图扩展失败** | `ok=True` + 纯向量结果，`note` 注明关联项暂缺——**降级不整体失败**，图是增强不是必需 |

⚠️ **无 ACTIVE 版本时绝不退化成"查全部版本"**（§4.8）：退化会把 N 个版本的同一个 playbook 一起召回，top_k 全被同一本手册的不同版本占满，比"没有结果"糟糕得多。

**红线**：`ok=False` 时提示词必须要求如实说"暂时不可用、稍后重试"，**绝不能说成"没有找到相关 playbook"**。把服务故障说成"内容不存在"是最误导用户的一类错误（`search_knowledge_base` 已踩过并写死同款约束）。

**数据容错**：`define-the-vision` 无正文，被召回时 `excerpts` 为空、只给 profile，按正常情况处理，不得报错。

### 8.2 维护侧（三个 API）

统一口径：**失败不留下会被误用的中间态**。版本化让这件事容易做到——ingest 的产物是 DRAFT，线上读 ACTIVE，失败最多留个废版本。

#### `crawl`

| 情形 | 处置 |
|---|---|
| 源站不可达 / 超时 / 非 200 | 失败返回，**零副作用**（还没走到 presign） |
| **HTML 拿到了但内容不对**（登录页 / 反爬页 / 改版） | ⚠️ **上传前做 sanity check**：HTML 里必须能匹配到 `article.play-card`，否则**拒绝上传**。不检查的话会把一个错误页面存进 S3 并登记，后续 ingest 才发现、而且要靠"节点数 < 50"那道防线兜——问题暴露得越晚越难查 |
| presign 失败 | 失败，零副作用 |
| **PUT 到 S3 失败** | 有一处副作用：`files` 表已有 fileId（presign 时 Java 预写入），但 S3 无对象 → **孤儿 files 行**。我们**不登记 `ai_file_registry`**，所以对 ingest 不可见；孤儿行由 Java 侧 verify 状态标记，不需要 Python 清理 |
| verify 返回 `FAILED` | 不登记，错误里带上 Java 给的 `reason`（`S3_MISSING` / `S3_ERROR`）——这两个原因的排查方向不同 |

#### `ingest`

| 情形 | 处置 |
|---|---|
| 没有可用登记行（还没 crawl 过） | 失败，明确提示"先跑 crawl" |
| 从 S3 下载失败 | 版本标 `FAILED` |
| **解析出的节点数 < 50** | **拒绝整批** + 标 `FAILED`（源站改版 / 选择器失效，§7.1 步骤 4） |
| 关系推断 LLM 调用失败 | 版本标 `FAILED` |
| **LLM 输出被截断**（`finish_reason == 'length'`） | 明确报"输出被截断"，**与"非法 JSON"区分开**——前者调上限、后者改提示词（§7.1.1） |
| **边数 > 96** | **拒绝整批** + 标 `FAILED`（§7.1.1） |
| **关系里出现不存在的 pid**（LLM 幻觉） | **拒绝整批**并列出坏 pid，不静默跳过（§4.5.0） |
| embedding 中途失败 | 版本标 `FAILED`；**`node_count` 保持 0**，即使标记没写成（进程被 kill）activate 也会拒（§7.1.2） |
| 版本号冲突（并发 ingest） | `IntegrityError` → 转友好文案"可能有另一个 ingest 正在运行，请稍后重试"（§7.1.2） |

#### `activate`

| 情形 | 处置 |
|---|---|
| 版本不存在 | 404 |
| 版本是 `FAILED` | 拒绝（§7.1.2） |
| **完整性校验不过** | 拒绝，并**指出缺什么**——例如"有 3 条 playbook 没有 profile 分段：`pid-a` / `pid-b` / `pid-c`"。只说"校验失败"等于把排查成本推给操作者 |
| 已是 `ACTIVE` | no-op，幂等返回成功 |
| 并发 activate（两人同时切不同版本） | 部分唯一索引（§4.8 / D26）让后者事务失败，重试即可 |

## 9. 可观测

### 9.1 检索侧

- **LLM**：embedding 走 `llm_db_router.aembed(call_purpose="playbook_search")`，自动落 `ai_llm_call_log`，无需额外埋点
- **链路**：service 编排方法挂 `@traced_span`，span 记 `version` / `seed_count` / `expanded_count` / `hops`
- **排障日志**（对齐 `search_knowledge_base scope: ...` 的习惯，实践证明最省排障时间）：

  ```
  search_playbooks: q=%r top_k=%d version=%s -> seeds=%s expanded=%s(depth<=%d) excerpts=%d
  ```

  ⚠️ **`version=` 必须打**：多版本并存后，"召回结果不对"的第一个问题永远是"读的是哪个版本"。不打这个字段就得去查库反推。

### 9.2 维护侧：复用 `ai_rag_operation_log`，不另造审计

rag 已有写类操作审计（`operation_log_service` 的 `safe_begin` / `safe_finish`，审计失败不影响主流程）。三个维护 API 全部走它，与 rag 其它写操作同口径：

**改动只是给 `RagOperationType` 加三个枚举值**（纯新增，与 §4.6"共用代码零放宽"一致）：

```python
PLAYBOOK_CRAWL    = "PLAYBOOK_CRAWL"
PLAYBOOK_INGEST   = "PLAYBOOK_INGEST"
PLAYBOOK_ACTIVATE = "PLAYBOOK_ACTIVATE"
```

现成列直接对上，`extra` JSONB 装 playbook 专属字段：

| 操作 | 用现成列 | `extra` 里放 |
|---|---|---|
| `PLAYBOOK_CRAWL` | `duration_ms` / `err_*` / `operation_status` | `html_bytes` / `file_id` / `card_count`（sanity check 数到的 card 数） |
| `PLAYBOOK_INGEST` | `space_id` / `entry_count` / `chunk_count` / `total_tokens` / `duration_ms` / `llm_trace_id` / `err_*` | `version` / `file_id` / `relation_model` / `relation_count` / `rejected_reason`（拒绝整批时的原因） |
| `PLAYBOOK_ACTIVATE` | `user_id` / `duration_ms` / `err_*` | `version` / `previous_version` |

**关系推断那次 LLM 调用无需额外埋点**：走 `llm_db_router.acomplete(call_purpose="playbook_edge_infer")` 自动落 `ai_llm_call_log`，token / cost / `finish_reason` 全在（`finish_reason` 那列的注释原话就是"截断率等指标源"）。

### 9.3 ⚠️ 版本切换必须有完整历史，版本表不够

版本表的 `activated_by` / `activated_at` **只保留最后一次**。反复切换（v1 → v2 → 回滚 v1 → 再上 v3）时，中间的历史全被覆盖，而"什么时候回滚过、谁干的"恰恰是事故复盘最需要的信息。

`ai_rag_operation_log` 是 **append-only**，每次 activate 一条记录（含 `previous_version`），完整轨迹都在。所以：

- **版本表的两个字段**回答"这个版本现在是谁在什么时候激活的"（当前状态）
- **操作日志**回答"这套数据被怎样切换过"（历史轨迹）

两者都要，不是冗余。

## 10. 测试与召回评测

**关键约束**：这层**不能用 SQLite 做单测**——`vector` 类型 SQLite 完全不支持，`jsonb_array_elements_text` / `@>` / 递归 CTE / `ARRAY … = ANY()` 也都没有。

| 层 | 位置 | 方式 |
|---|---|---|
| processor | `tests/rag/test_playbook_processor.py` | mock embedder + store；覆盖 `_split` 产出 `[profile, body...]` 的顺序与 `chunk_kind` 打标、空正文只出 profile、`summarize` 返回 None |
| service 编排 | `tests/rag/test_playbook_service.py` | **mock repository**；覆盖空间定位三态（0 兜底自建 / 1 正常 / N 报错）、**无 ACTIVE 版本返回空**、seed→expand→拼装、图扩展失败降级、空召回 |
| 版本化 | `tests/rag/test_playbook_service.py` | activate 的三条完整性校验各自不过时被拒（§7.1.2）、`FAILED` 版本不可 activate、已 ACTIVE 时幂等 |
| 关系校验 | `tests/rag/test_playbook_service.py` | **pid 幻觉拒绝整批**（§4.5.0）、**边数 > 96 拒绝**、**解析节点数 < 50 拒绝**——三条防线都要有测试，它们是数据质量的唯一保障 |
| 维护端点 | `tests/rag/test_playbook_routes.py` | mock service；覆盖三个端点的信封 + 管理端闸门（公司端 403） |
| 工具 | `tests/ai/tools_v2/test_search_playbooks_tool.py` | mock service；覆盖 ok / 空 / `ok=False` 三态 + 返回结构 + `ui_label` 契约 |
| **注册完整性** | `tests/rag/test_playbook_processor.py` | `build_processor('PLAYBOOK')` 返回 PlaybookProcessor、`get_business_chunk('playbook')` 返回新表、`'PLAYBOOK' in PROCESS_TYPES`——三处注册漏一个都会在运行期才炸 |
| SQL 正确性 | 上线抽验（§11 步骤 5/6） | **不新造真连 PG 的单测**——项目已有 `test_delete_thread_ok` 这一真连 5432 的痛点长期挂在待优化项，不再新增同类 |

### 10.1 召回评测脚本（`scripts/eval_playbook_recall.py`）

金标集：`scripts/data/playbook/golden_queries.json`（157 题，D9 收编）。

**构造方式（复现必读）**：playbook 自带的 157 条 `questions` **原文就在 profile chunk 里**，直接用会数据泄漏；故先用 haiku 改写成口语化提问（平均词面重合度降至 43%）。

#### ⚠️ 必须复用线上的路由代码，不许自己写 SQL

评测的目的是**预测线上表现**，两边用不同代码路径算出来的数字不可信。**首轮选型就栽在这里**——评测脚本自己写 SQL、候选口径与线上不一致（未对齐"取到 k 个不同 playbook"），一度得出方案 3「+14%」的错误结论，对齐后实际是 **−5.1%**。

所以 `PlaybookProcessor` 要把阶段 1 单独暴露成一个方法，线上与评测**共用**：

```python
async def route(self, *, store, query, top_k, entry_ids,
                query_vector=None) -> list[RouteHit]:
    """阶段 1：在给定 entry_id 范围的 profile chunk 上向量检索，返回 top_k 个 seed。"""
```

- 线上 `recall()` 调它 → 再走阶段 3 取正文
- 评测脚本调它 → 直接算 recall@k / MRR，**不碰图扩展与正文**（评的是路由准确率）
- 口径因此天然一致：同一份过滤条件、同一个 embedding 模型（PLAYBOOK 种子）、同一套 top_k 语义

**候选口径在 v2 天然对齐**：profile 与 playbook 1:1（§4.3），top_k 条 profile 就是 top_k 个不同 playbook，**不需要"从 chunk 去重到 playbook"这一步**——首轮那个坑从根上消失了。

#### 支持按版本评测与版本对比

版本化带来的新能力（§4.8）：

```bash
python scripts/eval_playbook_recall.py --version 2            # 评某个 DRAFT 版本
python scripts/eval_playbook_recall.py --version 1 --against 2  # 两版对比
python scripts/eval_playbook_recall.py                       # 缺省评 ACTIVE 版本
```

`--against` 是首次上线要用的（§11 步骤 8）：**同一批金标、两个版本，唯一变量是关系推断的模型**（opus5 vs sonnet5）。注意它只能反映**路由**差异——关系质量的判断仍要靠人审 diff（§7.2），因为关系没有 ground truth。

**不进 CI**（需 API key + DB）。以下情况必须手工跑一遍：**换 body 切分器**（如从 1400 字符硬切改成 `html_splitter` 按 h2 语义切，见 D21）、改切分参数、换 embedding 模型、加 rerank、大批量改关系。

## 11. 上线顺序

0. **先跑环境自检**（每个环境、业务库与向量库**各跑一遍**）——本地 18.3 / 测试 13.23 跨 5 个大版本，本地跑通不代表测试能跑：

   ```sql
   SELECT current_setting('server_version');                        -- 记录版本
   WITH RECURSIVE w(n,path) AS (                                    -- 递归 CTE + path 防环
       SELECT 1, ARRAY[1] UNION ALL
       SELECT w.n+1, w.path||(w.n+1) FROM w WHERE w.n<5) SELECT max(n) FROM w;
   SELECT extversion FROM pg_extension WHERE extname='vector';       -- 向量库才需要
   ```

   全部通过再往下。**不要**测 `CYCLE` 子句——本设计已明确不用它（§5.1）。

1. **清 v1 与预研遗留**（仅相关环境）：
   - 删旧 STANDARD 空间下那 64 条 entry 与 429 条 `ai_rag_ent_kb_chunk` 分段、删 `business_type='PLAYBOOK'` 的业务关联行（§4.7 末）
   - ⚠️ **`DROP TABLE IF EXISTS ai_rag_playbook_chunk`（阻塞性）**：选型评测期在本地建过一张**同名实验表**（387 行，列结构完全不同：有 `chunk_type` / `pid` / `title`，缺 `space_id` / `entry_id` / `file_id` / `content_tokens` / `hit_count`）。不删的话，下一步迁移的 `CREATE TABLE IF NOT EXISTS` 会**静默跳过**、迁移报告"成功"，而应用启动后 ORM 映射到一张缺 5 列的表、**运行期才炸 `column does not exist`**——迁移期不报错、运行期才暴露，是最难查的一类
2. `python scripts/migrate.py`：业务库 `V021__sprint115_playbook.sql`（两张属性表）+ 向量库 `V004__sprint115_playbook.sql`（chunk 表 + HNSW + 两个索引）。
3. **部署代码**——⚠️ **Java 与 Python 必须同批**（Java 的 `FileBusinessTypeEnum.PLAYBOOK` 不上，Python 的 crawl 调 presign 会 400）。启动后先验两条注册链：
   - Java：`POST /api/web/storage/uploads/presign` 传 `fileBusinessType=PLAYBOOK` + 一个 `.html` 文件，应返回 `uploadUrl`，且 `objectKey` 含 `playbook/` 目录段
   - Python：`GET /api/ai/rag/process-types` 应返回**三个**类型，且 `Playbook` 带 `defaultChunkSize=1400` / `defaultChunkOverlap=150`
   - ⚠️ **DB 侧**：`SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='chk_rag_space_process_type'` 必须已含 `PLAYBOOK`——这是**第四处注册点**，Python 三处全齐了它不放宽也建不出空间（V021 第 ② 段负责）
4. **建空间**：devSupport → RAG Management → Spaces → New Space，Process Type 选 `Playbook`（或跳过，靠 ingest 兜底自建）。
5. `POST /api/ai/rag/playbook/crawl`（⚠️ **每个环境都要各自跑一次**，§7.0.1）→ 抽验：
   - `files` 表新增 **1 行**（`content_type='text/html'`，size 约 1.3–2.6 MB）、`ai_file_registry` 新增 **1 行**（`business_type='PLAYBOOK'`、`company_id` NULL、`ai_rag_entry_id` **留空**）
   - 用该 `fileId` 走 `getDownloadLinkById` 下载，确认拿到的是**完整原始 HTML**（能在里面搜到 `article.play-card` 与 `.play-content`），不是被解析过的文本
   - ⚠️ **拿一个真实公司账号调一次 chatbot 知识库问答**，确认 playbook 的 space **没有**被圈进它的检索范围（验 §7.0 那两道保险）
6. `POST /api/ai/rag/playbook/ingest` → 产出 **version 1（DRAFT）**，抽验：
   - `ai_playbook_version` 一行 `version=1, status='DRAFT'`、`node_count=64` / `relation_count=28`、`relation_model` 与 **`file_id`** 均有值
   - ⚠️ **与仓库基线核对**：解析结果应仍是 **64 节点 / 28 关系 / 63 正文**（`scripts/data/playbook/` 那两个 JSON）。不一致 = 源站改版信号，**先看差异再决定要不要 activate**
   - `ai_playbook` **64 行且全部 `version=1`**；`ai_rag_entry` 该 space 下 64 行、status 全 `SUCCESS`、`company_id` 全 NULL
   - `ai_rag_playbook_chunk` 挂在这 64 个 entry_id 名下的分段：**`metadata->>'chunk_kind'='profile'` 恰好 64 条** + `'body'` **304 条**（实测值。三个数字的来历：预研自写切分 323；v1 走 STANDARD 的 `load_text` 会把标题拼进正文、切出 365；v2 的 `PlaybookProcessor._load` 直接用 body、切出 304——不拼标题是刻意的，profile 已含 title、body 第一段也是带标题的元数据块，拼了纯重复还白多 17% 的 chunk。**profile 文本逐字一致，故 r@1 不受影响**，变的只是取正文的段边界）
     ```sql
     SELECT c.metadata->>'chunk_kind' AS kind, count(*)
       FROM ai_rag_playbook_chunk c
      WHERE c.entry_id IN (SELECT entry_id FROM ai_playbook WHERE version = 1)
      GROUP BY 1;
     ```
   - **`define-the-vision` 的 `chunk_count` 必须是 1**（只有 profile，验空正文跳过生效）
   - ⚠️ **孤儿引用必须为 0，且要主动查**（没有 FK 兜底，LLM 可能吐幻觉 pid）：
     ```sql
     SELECT p.pid, d.value FROM ai_playbook p
      CROSS JOIN LATERAL jsonb_array_elements_text(
            p.depends_on || p.feeds || p.refers_to) AS d(value)
      WHERE p.version = 1
        AND NOT EXISTS (SELECT 1 FROM ai_playbook q
                         WHERE q.pid = d.value AND q.version = p.version);
     ```
   - ⚠️ **此时 `search_playbooks` 必须返回空** —— 还没 activate，`active_version` 为 NULL（验 §4.8 那条"不退化成查全部版本"）
7. `POST /api/ai/rag/playbook/versions/1/activate` → 抽验：
   - `ai_playbook_version` 里 `version=1` 变 `ACTIVE`、`activated_at` / `activated_by` 有值
   - `search_playbooks` 开始正常返回 seed / prerequisites / inputs
   - `EXPLAIN` 路由查询按 `entry_id` 索引收窄（不指望走 HNSW，§4.3 已说明）
8. **再跑一次 ingest，同时验版本化与模型 A/B**（最容易出错的一环）——这次传 `relationModel=Models.openrouter.text.sonnet`：
   - 查 `ai_llm_call_log` 里 `call_purpose='playbook_edge_infer'` 两条记录的 `output_tokens` / `cost_usd`，确认实际用量远低于 8000（§7.1.1 预期约 790）
   - diff 两版关系集合，人工判断 opus5 与 sonnet5 哪组更合理——**这是关系质量唯一的闸门**（§7.2）
   - `python scripts/eval_playbook_recall.py --version 1 --against 2` 看两版**路由**差异（注意：它只反映路由，关系质量仍靠人审）
   - 产出 `version=2, status='DRAFT'`；**`version=1` 的一切原样不动**（64 行属性 / 64 条 entry / 368 条 chunk 全在，无一被软删）——按上面那条 SQL 把 `version = 1` 换成 2 应得到同样的 64 / 365
   - **线上仍读 version 1**——此刻 `search_playbooks` 的结果应与步骤 7 完全一致
   - 返回体的 diff 段要能看出两版关系差异（LLM 逐次不完全一致，这正是要审的东西）
   - 试着直接 `UPDATE ai_playbook_version SET status='ACTIVE' WHERE version=2` → **必须被 `UniqueViolation` 拒绝**（验 §4.8 的部分唯一索引真的建上了）
9. `activate 2` → 线上切到 version 2；再 `activate 1` → **回滚验证**，无需重跑任何爬取或向量化。
10.（可选）`python scripts/eval_playbook_recall.py --run` 确认召回未劣化。

## 12. 关键决策记录

> D1~D13 是 v1 的记录，其中 **D2 / D5 / D11 已被 v2 推翻**（下表标注 ~~删除线~~ 并给出接替项）。D14~D18 是 v2 新增。

| # | 决策 | 理由 / 被否方案 |
|---|---|---|
| D1 | 关系边落 PG 表而非 LadybugDB | 召回能力完全相同；在"关系持续扩充"前提下，图文件"改边要重建 + 孤儿依赖"是经常性成本 |
| ~~D2~~ | ~~复用 rag 的 space / entry / chunk 承载 playbook~~ | **被 D14 取代**：chunk 表改为独立。entry / space 仍复用（D17） |
| D3 | 不合并关联文本进同一 chunk | **实测负收益**（r@1 −5.1%）；且无法反向查询、只能 1 跳静态 |
| D4 | 两段式检索（profile 路由 / body 细节） | 实测 r@1 80.9% vs 61.8%，差 19 个百分点 |
| D5 | **用 `metadata.chunk_kind='profile'` 区分 profile / body**（v2 复核后维持） | `chunk_kind` 是 rag 的**跨业务约定**（另两张 chunk 表的 `body` / `summary` 都在 metadata 里），playbook 加一个取值即可。虽然独立表本可以做成正式列（能建普通索引、加 CHECK），但那会让**同一个概念在三张 chunk 表里有两种存法**，将来任何按 chunk_kind 统计/清理的通用代码都得为 playbook 写特例——跨表一致性比单表最优值钱 |
| D6 | **属性表 `ai_playbook` 仍需保留** | rag 的 entry 装不下 pid / category / stage / questions；但 title / description 复用 entry 的 title / summary，不重复存 |
| ~~D7~~ | ~~关系只增不删（并集合并）~~ | **被 D25 取代**：版本化后重跑不动旧数据，不再需要合并策略，也不需要给关系标来源 |
| D8 | 一期不做内部查看器**与维护页面** | 注册进 `BUSINESS_REGISTRY` 后 devSupport 现成的空间/文档/片段/召回页已能看 playbook；维护是低频运营动作，手动调 API 够用 |
| D9 | 收编评测脚本与金标集 | 一次性构造成本已付；无它则后续任何调参只能凭感觉 |
| D10 | **`FEEDS` 走入边、`REFERENCES` 不扩展** | 实测 `FEEDS` 无法由 `DEPENDS_ON` 推导（§4.5.2）；其箭头是数据流向，有用的方向是"谁喂给我"。`REFERENCES` 是软提及，2 跳只稀释 context |
| ~~D11~~ | ~~给 `vectorize_by_space` 加 `with_summary` 开关~~ | **被 D16 取代**：覆写 `PlaybookProcessor.summarize` 返回 None，共用函数不动 |
| D12 | **维护自行编排 entry 写入，不调 `ingest_text`** | `find_duplicate_title` 对 `company_id=NULL` 恒不命中，照用会让每次重跑重复新增 64 条 entry（§4.2.1）；且 playbook 还要额外产出 profile 分段，本就超出 `ingest_text` 的行为 |
| D13 | **防环用 `path` 数组，不用 `CYCLE` 子句** | `CYCLE` 需 PG 14+，而**测试环境实测为 PG 13.23、直接语法报错**（§5.1）；省一行代码换来「每个环境都得先验版本」的部署风险，不值 |
| **D14** | **新增第三个 `process_type='PLAYBOOK'`，带独立 chunk 表** | playbook 在切分（按节点）/ 召回（两段式 + 图扩展）/ 入库（额外产 profile）/ 来源（爬取）四件事上全都与 KB 不同，塞进 STANDARD 就是到处开特例。顺着 rag 的处理类型契约做，反而**免掉 v1 那三处共用代码放宽**（其中 filters 那处紧邻租户隔离）、且六个调用方零改动白得能力（§2.1）。代价：多一张表 + 一次 HNSW |
| **D15** | **空间按 `process_type` 定位，全局唯一，废弃业务关联表** | 关联表解决的是"哪个公司/用户能看哪些空间"，而 playbook 全平台共享、不做作用域圈定——用它属于工具错配，还得为此放行"作用域至少填一个"的校验。多于一个空间**报错而非取第一个**：静默取第一个会造成"灌 A 读 B"，症状是"导进去了却召不回" |
| **D16** | **覆写 `PlaybookProcessor.summarize` 返回 `None`** | 基类注释原话"各业务类型可覆盖定制"，这就是覆写点。entry.summary 写源站 `description`（原文比 LLM 概括更准），既省 64 次调用、也不产出无人检索的 summary 分段 |
| **D17** | **文档层仍复用公共表 `ai_rag_entry`，不自建** | entry 是平台公共文档表（rag 已明确"文档不再按业务分表"）；自建会同时失去 devSupport 文档页、召回记录、命中统计三样 |
| **D18** | **维护做成三个 API（crawl / ingest / activate），第一阶段同步返回、不做页面** | 爬取打外部站点、慢且易失败，与纯本地的 ingest 分开，失败不互相牵连、也能"先爬下来看一眼再灌"。再细拆成四步没有值得人工介入的检查点，只会多三份中间态。同步返回是因为管理端手动调、数十秒能等；嫌久再接 `BackgroundTasks` + 现成的 `ai_rag_ingestion_task` |
| **D19** | **关系并进 `ai_playbook` 的三个 JSONB 列，不建边表** | 28 条关系 / 64 个节点，**实测两种存法查询能力完全等价**（递归 2 跳与反查入边结果一致、全表扫毫秒级）；少一张表 + 少一次 JOIN，读一个节点的全部关系就是一行。**代价是 4 个 DB 约束变成应用层责任**，其中 FK 那条最要紧（slug 写错会静默少节点而不报错）——对策是 §4.5.0 那个集中的 pid 存在性校验 + §11 的孤儿引用抽验。`rel_type` 的 CHECK 天然被"三个列名即类型"替代 |
| **D20** | **`version` 只存在 `ai_playbook` 与版本表，不下沉到 chunk 表** | 一次 ingest = 一个版本 = 64 行属性 + 一套关系 + 64 条 entry + 368 条 chunk；`ai_playbook` 的唯一约束是 `UNIQUE(pid, version)`。**向量库不感知版本**——每版本各建独立 entry，所以「某版本的 chunk」≡「该版本 64 个 entry_id 名下的 chunk」，阶段 0 顺带取出 entry_id 即可圈定（§4.3）。这样版本这个业务概念不泄漏进向量库、也少一处可能不同步的冗余。**不是并发控制版本**，别拿它当乐观锁 |
| **D21** | **crawl 存源站整页**原始 HTML**（1 个文件、非 64 个），不存提取后的 txt / json** | 爬取贵（打外部站点、慢且易失败）、解析便宜（纯本地）——留住不可再生的原始响应，可再生的文本随时重算；存 txt 等于把 bs4 提取规则固化在爬取那一刻，日后发现漏区块只能重爬。附带两个好处：项目已有为"未来 HTML 入库"预留的 `html_splitter`（按 h2 语义边界切，比 1400 字符硬切更贴 playbook 的小节结构）；有 HTML 才能真正 diff 源站改版。r@1 80.9% 只依赖 profile、与 body 切法无关，故换切法安全（但仍要用金标集跑一次对比） |
| **D22** | **上传经 Java 预签名（presign → PUT → verify），Python 不直连 S3** | 不破"Python 不直连 S3"的架构约定、不需要 AWS 凭证，是既有 `download_ingest_file` 的镜像实现 |
| **D23** | **Java 加一个 `FileBusinessTypeEnum.PLAYBOOK`（3 行），不复用 `KNOWLEDGE_BASE`、也不给它的白名单加 html** | 复用**走不通**：`ExtSets.KNOWLEDGE` 白名单不含 html，presign 会拒。给 KNOWLEDGE 加 html 只需 1 行但会**放开所有 KB 通道上传**（含公司用户在 chat 里传的文件）接受可执行内容，引入 XSS 面；playbook 是我们自己爬的可信内容，与用户上传的 HTML 不是一回事。加枚举 3 行、service 零改动（类注释明说"新增只需登记一个枚举值"），顺带 S3 目录独立成 `uploads/playbook/` |
| **D24** | **`ai_file_registry.business_type='PLAYBOOK'`（不是 KNOWLEDGE_BASE）** | 这是登记行不被误圈进公司知识库检索的**第二道保险**：第一道是 `company_id=NULL` 让 `list_kb_space_ids` 的 `company_id.in_(...)` 恒不匹配；第二道防的是"将来有人给 KB 圈定放开 NULL"。照抄会话文件用 `SESSION_UPLOAD` 避开 KB 圈定的先例。该枚举值 V013 起就存在，零改动 |
| **D25** | **版本化 + 审核发布：ingest 只产 DRAFT、activate 才生效，旧版本一行不动** | 取代 D7 的"就地覆盖 + 只增不删"。①**人工修改天然安全**——你在 ACTIVE 版本上改的东西，下次 ingest 生成的是新版本的新行，碰不到它，所以不需要给关系元素标 `llm`/`manual` 来源；②**LLM 关系推断的不稳定被隔离**——每个版本是一次推断的完整快照，不会像"重推 + 只增不删"那样单向累积成并集噪声；③**回滚 = 一次 activate**，不重跑爬取与向量化；④**可按版本做 A/B**，比较不同模型推的关系。代价：三张表都要按版本存（chunk 表冗余 `version` 列）+ 存储线性增长（5 个版本约 13 MB，不值得为它写清理逻辑）+ devSupport 文档页会看到 64×版本数 个条目 |
| **D26** | **"同时只有一个 ACTIVE"用部分唯一索引在 DB 层强制** | `CREATE UNIQUE INDEX ... ON ai_playbook_version ((status)) WHERE status='ACTIVE'`（实测 PG 13+ 可行：第二个 ACTIVE 被 `UniqueViolation` 拒，同事务内先降后升正常）。**不靠应用层保证**——两个 ACTIVE 会让"取生效版本"随机命中一个，症状是同一个问题两次答得不一样，属于最难排查的一类 bug |
| **D27** | **关系推断钉 `opus5`，主防线是边数上限 96 而非 token 上限** | 模型：这是**低频运维动作**（源站更新才跑，一辈子跑不到 10 次），opus 与 sonnet 单次差价 **$0.019**——成本不是判断依据，**人工审核时间才是**（28 条关系要懂业务的人审 15–30 分钟）。任务本质是「4032 个可能有向对里挑约 28 个」的高选择性判断，正是 opus 的强项；弱模型的典型失败是过度生成或判断标准时紧时松。**钉住版本不用 `opus` 符号**：输出要人工审核后长期沉淀，registry 静默升级会让 diff 多一个说不清的变量。防线：实测 `max_tokens=4000` 能装 141 条边、余量 5 倍，**token 不是瓶颈**；真正危险的是边数暴涨（2 跳图扩展节点数平方级增长 → context 爆炸），故主防线是 `_validate_edges` 的边数上限 96（占 2707 token，永远比 token 上限先触发） |
| **D28** | **关系推断的输入不加 questions、不加正文** | 实测：157 条 questions 里**仅 2 条（1.3%）**提到别的 playbook 特征词、且已被现有边集覆盖；63 篇正文前 600 字符含前置线索词的**只有 3 篇且全是误报**。**源站根本不写依赖关系**——这解释了预研为何选 LLM 推断（不是偷懒）。结论：**输入侧无事实依据可加**，改善质量只剩「换更强模型」与「人工审核」两条路。附带好处：首次 opus5 vs sonnet5 对比时**变量只有模型** |
| **D29** | **各环境自行 crawl（方案 A），不用 JSON 种子导入、不把 HTML 进仓库** | 已确认测试 / 生产均可出网。备选两条的代价：HTML 进仓库要 +2.6 MB 且变更让 git diff 难看；JSON 种子登记的是**解析结果**而非原始响应，失去 D21 的"可重解析"优势。**连带风险**：各环境 version 号独立、抓取时间不同，「测试 v3」≠「生产 v3」——靠版本表的 `file_id` 区分（§7.0.1）。仓库里那两个 JSON 因此只剩「可复现基线」一个用途：crawl 后核对 64/28/63，不一致即源站改版信号 |

## 13. 后续

- **二期 诊断式推荐** `recommend_playbooks(company_id)`：读财务 / benchmark 短板 → 映射 category / stage → 按 DEPENDS_ON 拓扑排序给执行顺序。本期已把 category / stage 结构化，无需再迁表。
- **内部查看器**：按其独立设计文档单独排期。
- **rerank**：`llm_db_router.rerank`（Cohere）在预研里已验证可用，本期未接；接入前先用金标集量化增益。
- **扩写 profile 的 `Key questions`（低成本、见效可能最直接）**：现在每个 playbook 只带 2~3 条问法，覆盖的表达空间窄，是 §3.1 所说"线上召回会低于 80.9%"的主因。用 LLM 给每条 playbook 扩写到 8~10 条不同问法后重嵌 profile，理论上能直接抬高路由准确率。成本极低（64 次调用、几分钱、387 chunk 重嵌 $0.003），且**有金标集可以量化验证是否真的有效**——先跑基线、扩写后再跑一次对比，不生效就回滚。
  ⚠️ 若做这一步，金标集需**同步重建**：现有 157 题就是从原 questions 改写来的，扩写后原 questions 仍在被检索文本里，泄漏面反而扩大。届时应改用"由 body 正文出题"的方式另建一套金标，与现有那套并存对比。
