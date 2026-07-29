# Playbook 接入 Chatbot 开发设计（复用 rag 存储 + PG 关系边 + 两段式检索）

> 关联文档：
> - 选型对比与实测（上游，先读）：[./playbook-recall-options-comparison.md](./playbook-recall-options-comparison.md)
> - 预研原型（`feature/sprint112-age`，只搬数据、不合并代码）：`python/CIOaas-python/source/playbooks_graph_db/`
> - 内部查看器（独立一条线，本期非范围）：[../../superpowers/specs/2026-06-23-playbook-knowledge-design.md](../../superpowers/specs/2026-06-23-playbook-knowledge-design.md)
>
> 阶段：⑤ 开发设计 | 版本：v1 | 日期：2026-07-28 | 端：Python（CIOaas-python，`sprint115`） | 范围：playbook 落地为 chatbot 可调用的检索能力
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

- playbook 专属空间（`business_type='PLAYBOOK'` 定位）+ 两张新表（属性表 / 关系边）+ 版本化迁移
- 复用 rag 的 entry / chunk 承载内容；导入脚本（JSON → space + entry + chunk + 两张新表）
- chatbot 工具 `search_playbooks` + 提示词接线
- 三处共用代码的受控放宽（§4.6）
- 召回回归评测脚本 + 157 题金标集

**非目标（明确不做）**

| 不做 | 原因 |
|---|---|
| 内部查看器 `/api/ai/playbook/*` + devSupport 页面 | 从零新写是另一条线的工作量，有其独立设计文档；且复用 rag 后 **devSupport 现成的 rag 空间/文档/片段页已能查看 playbook**，必要性进一步下降 |
| 诊断式推荐 `recommend_playbooks` | 二期；本期数据模型已为它预留（category / stage 结构化） |
| 清理 `feature/sprint112-age` | 该分支原样保留作预研记录，**只搬数据、不搬代码** |
| playbook 的增删改界面 | 边由 SQL / 导入脚本维护即可，界面按需再说 |

## 2. 方案结论

采用**关系边落 PG 表（递归 CTE）+ 两段式检索**，并在选型之后进一步定为**复用 rag 既有的 space / entry / chunk 承载内容**（详见 §4 与 D2）——选型文档里被否的"方案 2"是「playbook 混进公司 KB 召回池、走 `search_knowledge_base`」，与此不同。三条实测结论直接决定了本设计：

| 实测结论 | 对设计的约束 |
|---|---|
| profile-only 路由 r@1 **80.9%**，混入 body 后跌到 **61.8%** | 检索**分两段**：先只查 profile 定位 playbook，再取 body 拿细节 |
| **56.2%** 的 DEPENDS_ON 前置项纯向量 top-5 召不到 | 关系边**必须保留**，且要能多跳扩展 |
| 合并关联文本进同一 chunk 为**负收益**（r@1 −5.1%） | 关系以**结构化边**存在，不以合并文本存在 |

## 3. 模块落位

playbook 的存储既然长在 rag 的 space / entry / chunk 上（§4），代码就**落进 rag 模块内**、不单起 `source/playbook/` 包——否则一个能力被劈成两半：数据在 rag、编排在外面，跨模块调用还要绕 `application/service` 门面。

按 `rag/CLAUDE.md` 的既有分层落位（**均为新增文件，不改动 rag 现有文件**，除 §4.6 那三处受控放宽）：

```
source/rag/
├── application/service/playbook_service.py          检索编排：定位 space → 路由(profile 向量检索) → 映射 pid
│                                                    → 按类型分方向扩展 → 取正文 → 拼装（与 search_service 同级）
├── application/dto/playbook_dto.py                  PlaybookHit / Related / PlaybookSearchResult（一域一文件）
├── domain/models/playbook_model.py                  ai_playbook（每实体一文件平铺）
├── domain/models/playbook_relation_model.py         ai_r_playbook_relation
├── domain/repository/playbook_repository.py         属性表单表 CRUD（首参 session、内部不 commit）
└── domain/repository/playbook_relation_repository.py 关系边 + 递归 CTE 扩展

source/ai/tools/search_playbooks_tool.py             chatbot 工具（本期唯一新增工具）
scripts/import_playbooks.py                          导入（部署期工具，与 migrate.py 同目录）
scripts/scrape_playbooks.py                          源站重抓（从 feature 分支搬）
scripts/eval_playbook_recall.py                      召回回归评测
scripts/data/playbook/                               playbooks_data.json / playbooks_bodies.json
                                                     / golden_queries.json（157 题金标）
```

三点说明：

- **`playbook_service` 独立成文件、不并进 `search_service`**：`search_service` 已承载圈定 / 召回编排 / 召回记录 / enrich，够重了；playbook 的编排是另一套职责（空间定位 + 关系扩展）。但它**可以直接调 `search_service.recall`**——同模块内调用，不必绕门面。
- **不新增 `interfaces/routes.py`**：本期不做查看器（§1 非目标），playbook 只经 chatbot 工具暴露。
- **数据文件放 `scripts/data/playbook/`**：三个 JSON 只被导入 / 评测脚本读，属种子数据而非应用代码，与读它的脚本放一起最直接，不污染 `source/`。

**错误类型复用 rag 既有的 `application/service/errors.py`（`RagBusinessError`）**，不另立异常体系。

⚠️ **配套要更新 `source/rag/CLAUDE.md`**：目录结构表加这 6 个新文件，并在「核心概念」补一段 playbook 作为全平台知识库的说明（含 `business_type='PLAYBOOK'` 定位与 `chunk_kind='profile'` 约定）。不更新的话，下一个人按现有 CLAUDE.md 读不出 playbook 这条线。

从 `feature/sprint112-age` **只搬数据与口径**，不搬代码：

| 搬 | 说明 |
|---|---|
| `playbooks_data.json` | 64 节点 + 28 条边（DEPENDS_ON 21 / FEEDS 5 / REFERENCES 2） |
| `playbooks_bodies.json` | 63 条正文（`define-the-vision` 在源站已并入 `executive-execution`，无正文） |
| `scrape_playbooks.py` | 数据可复现的凭证 |
| **切分口径** | `BODY_CHUNK_CHARS=1400` / `BODY_CHUNK_OVERLAP=150` / profile 文本格式 `"{title} ({category}). {description} Key questions: {questions}"` |

⚠️ **切分口径必须逐字照搬**：r@1 80.9% 的实测是在这个切法上跑出来的，换切法数字不作数。

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

而它的 body 首段是 `Cash Flow Forecast | Players | Founder, CFO | Initial Effort | 13 SP | ...`（6583 字符切 5 段）。

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

## 4. 数据模型：复用 rag 的空间 / 条目 / 分段，只补两张表

playbook 作为**全平台知识库**长在 rag 既有模型上，不另造一套向量栈：

| 承载什么 | 用什么 | 说明 |
|---|---|---|
| 空间 | `ai_rag_space` 新建一个（`process_type=STANDARD`） | 空间自持切分 / topK / embedding 配置 |
| 空间定位 | `ai_rag_business_association`，`business_type='PLAYBOOK'` | 该枚举值**本就存在**；代码按业务类型查出 space |
| 一个 playbook | `ai_rag_entry` 一行（`source_type='TEXT'`） | 复用 title / summary / char_count / hit_count / status / deleted |
| profile + 正文分段 | `ai_rag_ent_kb_chunk`（STANDARD 业务 chunk 表） | 复用 HNSW 索引、召回、命中统计 |
| **playbook 专属属性** | **`ai_playbook`（新增）** | pid / category / stage / questions —— rag 模型放不下 |
| **playbook 间关系** | **`ai_r_playbook_relation`（新增）** | rag 模型没有节点间关系 |

**这样省下的**：自建 chunk 表与 HNSW 索引、自写向量检索 SQL、自写切分与 embedding（复用 rag 的 processor / storage）。**额外白得的**：召回日志、命中统计，以及 devSupport 的 rag 空间 / 文档 / 片段页面——playbook 直接可见可查，不必再做查看器。

### 4.1 空间定位：`business_type='PLAYBOOK'`，作用域为空

一条关联：`(end_type=ADMIN, business_type='PLAYBOOK', company_id=NULL, user_id=NULL, organization_id=NULL)` → 挂 1 个 space。

- **作用域三者全空 = 全平台共享**。这正是 PLAYBOOK 与其余 6 个业务类型的本质区别——那 6 个都是"某公司 / 某用户 / 某组织的"。
- **`end_type` 固定 `ADMIN`**，代码里写成常量：playbook 是平台运营方维护的内容，不分客户端 / 管理端；两端工具查同一条关联。
- 定位用现成的 `find_by_exact_scope(end_type, business_type, company_id=None, user_id=None, organization_id=None)`——它对 NULL 作用域是 `IS NULL` 精确匹配，**查询侧零改动**。

⚠️ 创建侧要放宽一处校验，见 §4.6。

### 4.2 `ai_rag_entry`：一个 playbook = 一行（共 64 行）

**为什么按 playbook 拆而不是整库一条**：entry 是 rag 的"文档"粒度，一 playbook 一行才能拿到——每条 playbook 独立的 `hit_count`（哪本手册最常被问到）、独立的软删（源站退掉某条时只停它）、以及 devSupport 文档页里 64 个可点开的条目。整库一条则这些全部失效。`ai_playbook.entry_id` 的 UNIQUE 映射（§4.4）也依赖这个粒度。

| 列 | 填什么 |
|---|---|
| `id` | entry 主键（UUID），playbook 的内部标识 |
| `space_id` | playbook 空间 |
| `company_id` | **NULL**（全平台；该列本就可空） |
| `source_type` | `TEXT`（playbook 来自 JSON，非文件上传） |
| `title` | playbook 标题 |
| `content_text` | 正文全文 |
| `summary` | **直接写源站 `description`**——原文比 LLM 概括更准，且配合 §4.6 的 `with_summary=False` 省掉每条一次 LLM 调用 |
| `chunk_count` / `char_count` / `total_tokens` / `status` | 由导入脚本按 `vectorize_by_space` 的返回回写（§4.2.1 方案 A 自行编排） |
| `hit_count` / `deleted` | 前者由 rag 召回记录自动累加；后者软删时置位 |
| `file_id` / `thread_id` / `mime_type` / `file_size_bytes` / `task_id` | 留空（playbook 非文件上传、非聊天来源，也不建 ingestion task） |

#### ⚠️ 4.2.1 `company_id=NULL` 会让 rag 的同名去重失效（必须处理）

`ingest_text` 依赖同名覆盖来保证幂等——同 space 同 title 时软删旧 entry + 清其向量：

```python
dup = entry_repo.find_duplicate_title(company_id=company_id, space_id=space.id, title=dto.title)
if dup is not None:
    dup.deleted = True
    chunk_repo.delete_by_entry(entry_id=dup.id)
```

但 `find_duplicate_title` 里是 `.where(company_id == company_id)`——**传 None 会生成 SQL `company_id = NULL`，而 `NULL = NULL` 结果是 UNKNOWN 而非 true，查询恒返 None**。后果：

> 每次重跑导入，64 条 entry **全部重复新增、旧的一条都不软删**。跑三次就有 192 条活跃 entry、chunk 也翻三倍，路由召回全是重复 playbook。

三个可选处置，**实现前必须选定一个**：

| 方案 | 做法 | 代价 |
|---|---|---|
| **A（建议）** | 导入脚本**不调 `ingest_text`**，自己在同一事务里做 "按 (space_id, title) 查 → 软删旧 → 建新 entry → 投递向量化"，`company_id` 保持 NULL | 少复用一层薄编排，但幂等完全自己掌控；`ingest_text` 那段逻辑只有约 20 行 |
| B | 修 `find_duplicate_title` 支持 NULL（`company_id.is_(None)` 分支） | 动共用代码；虽然是纯 bug 修复，但要评估现有调用方是否依赖当前行为 |
| C | 给 playbook entry 填一个哨兵 `company_id`（如 `'PLATFORM'`） | 脏——`company_id` 语义被污染，且租户相关查询可能误命中 |

选 A 的额外理由：playbook 导入还要**额外注入一条 `chunk_kind='profile'` 分段**（§4.3）、**跳过 LLM 摘要**（§4.6），本来就超出 `ingest_text` 的既有行为，自己编排反而更直接。

### 4.3 `ai_rag_ent_kb_chunk`：用 `metadata.chunk_kind` 区分

**沿用 rag 既有的 `chunk_kind` 键**，不发明新机制——rag 现在就在用它：`factory.py` 给正文分段标 `chunk_kind='body'`、`base.py` 给摘要分段标 `chunk_kind='summary'`，注释原话是「用独立 key `chunk_kind`（不占 loader 的 `content_type`=来源类型，两维度并存）」「召回侧据 metadata 可辨」。playbook 只是**多加一个取值 `profile`**。

| `chunk_kind` | 内容 | 谁产生 | 用途 |
|---|---|---|---|
| **`profile`** | `"{title} ({category}). {description} Key questions: {questions}"`（§3.1） | **导入脚本注入**（仿 `base.py` 注入 summary 分段的做法） | **路由**（阶段 1）：只在此类上做向量检索 |
| `body` | 源站正文按 1400 / 150 切分 | rag STANDARD 流水线**自动打标** | **取正文**（阶段 3）；body 的**第一段**是"Players / Effort / Frequency / Stage + 开篇"元数据块 |

**`summary` 这一类 playbook 空间不产生**——但要显式跳过，见 §4.6 第三处放宽。`factory.vectorize_by_space` 里 `processor.summarize` 目前是**无条件调用**的（STANDARD 还会把摘要追加成一条 `chunk_kind='summary'` 分段），§4.2.1 方案 A 绕过的只是 `ingest_text` 那层薄编排，**下一层照样会摘要**。而 playbook 的 `entry.summary` 直接写源站 `description`（§4.2），LLM 摘要既用不上、也不该多一条无人检索的分段，故给该函数加一个默认开启的开关关掉它。

**为什么不为躲摘要而绕过 `vectorize_by_space`**：绕过就得自己重实现 body 打标、token / 字符计数，以及**私有的 `_prune_chunk_metadata`**（metadata 黑名单，抄一份必然漂移）——远比加一个开关贵。

**为什么不借用 summary 来充当 profile**：rag 的 summary 是 LLM 对正文的概括、**不含 questions**，而 questions 恰是 §3.1 里 query↔query 匹配的关键成分、80.9% 路由准确率的主要来源。所以 profile 必须是我们自己构造并注入的独立一类。

⚠️ **索引**：chunk 表 `metadata` 上**目前没有任何索引**。需加一个**部分索引**：`(space_id) WHERE metadata->>'chunk_kind' = 'profile'`——只索引这 64 行、体积极小，对共用表的其它业务零影响。路由查询的候选集本就只有 64 行（单 space 的 profile），按此索引先过滤再精确算距离即可，**不依赖 HNSW**（64 行精确扫描是毫秒级）。该索引随 §4.7 的 vector 迁移建。

其余列：`space_id` = playbook 空间、`entry_id` = 该 playbook 的 entry、`file_id` 留空；sprint114 那批登记列（`file_registry_id` / `end_type` / `business_type` / `thread_id` / `message_id` / `organization_id` / `company_id` / `created_by`）**全部留 NULL**。

### 4.4 `ai_playbook`（新增：属性表）

只装 rag 模型放不下的东西：

| 列 | 类型 | 约束 / 默认 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(36) | **PK**，default uuid4 | 主键（UUID），对齐项目惯例 |
| `pid` | VARCHAR(128) | NOT NULL，**UNIQUE** | 业务键 = 源站 slug；**关系边按它关联**（比 entry_id 稳定，重导入不变） |
| `entry_id` | VARCHAR(36) | NOT NULL，**UNIQUE** | 指向 `ai_rag_entry.id`（跨库软关联，无 FK） |
| `category` | VARCHAR(64) | NOT NULL，**索引** | 6 值：Executive / Sales & Marketing / Development / Customer / Operations / Vendor |
| `stage` | VARCHAR(64) | **索引** | 5 值：Pre-Revenue / Early Traction / Traction / Growth / All Stages |
| `questions` | JSONB | NOT NULL DEFAULT `'[]'` | profile 的成分（§3.1） |
| `source_url` | VARCHAR(512) | | 溯源 |
| `deleted` | BOOLEAN | NOT NULL DEFAULT `false` | 与 entry 软删同步维护 |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT `now()` | `updated_at` 由触发器维护 |

`title` / `description` **不在此表**——已在 entry 的 `title` / `summary` 里，不重复存。

**不建 `frequency` / `players` 列**：展示型元数据，不参与检索与过滤，且本就写在 body 首段文本里；改为在取正文阶段固定带上 body 首段（§5），连 JSON 里根本没有的 **effort** 也一起拿到。

### 4.5 `ai_r_playbook_relation`（新增：关系边）

| 列 | 类型 | 约束 / 默认 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(36) | **PK**，default uuid4 | |
| `source_pid` | VARCHAR(128) | NOT NULL，**FK → `ai_playbook(pid)`**，**索引** | |
| `target_pid` | VARCHAR(128) | NOT NULL，**FK → `ai_playbook(pid)`**，**索引** | 两个方向都要走（§5），故两列都建索引 |
| `rel_type` | VARCHAR(32) | NOT NULL，`CHECK IN ('DEPENDS_ON','FEEDS','REFERENCES')` | 现有 28 条：21 / 5 / 2 |
| `created_by` | VARCHAR(36) | | 审计：谁加的这条边 |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT `now()` | |

约束：`UNIQUE(source_pid, target_pid, rel_type)`（§7.1「只增不删」的 `ON CONFLICT` 冲突目标）、`CHECK(source_pid <> target_pid)` 防自环。

#### ⚠️ 4.5.1 方向语义（最容易搞反，务必按此实现）

`DEPENDS_ON` 的箭头**指向前置**（源 JSON 原话 "points to a prerequisite"），**不是**指向下游：

| | `source_pid = 我` 时 `target_pid` 是 | `target_pid = 我` 时 `source_pid` 是 |
|---|---|---|
| `DEPENDS_ON` | **我的前置**（要先做的） | 依赖我的（我的下游） |
| `FEEDS` | 我喂给谁（下游消费方） | **喂给我的输入源** |

实例：`Cash Flow Forecast --DEPENDS_ON--> Budget Creation --DEPENDS_ON--> Define the Mission`。**执行顺序恰好相反**：先定使命 → 再做预算 → 最后才做现金流预测。

两种心智模型都常见——"箭头 = 时间流向"（A→B 意为先 A 后 B）vs"箭头 = 依赖指向"（A→B 意为 A 需要 B）。**本数据用后者**；若按前者实现，诊断推荐会把执行顺序**整个颠倒**。

#### 4.5.2 `FEEDS` 无法由 `DEPENDS_ON` 推导（实测）

5 条 `FEEDS` **全部**推不出来：`DEPENDS_ON` 只覆盖 **28 / 64** 个节点，NPS、Churn Identification、Support Metrics 这三个度量类 playbook **完全不在依赖图里**；剩下那条（Product Roadmap → Adoption）两端虽在依赖图，却分属**互不连通的子图**。

所以 `FEEDS` 承载独立信息，删了真丢——它表达的是"哪些度量的产出会回流进某个流程"，这是 `DEPENDS_ON` 表达不了的。

### 4.6 ⚠️ 需要放宽的两处共用代码

| 位置 | 现状 | 改成 |
|---|---|---|
| `business_association_service._validate_payload` | `if not (company_id or user_id or organization_id): raise` —— 拒绝无作用域关联 | **仅对 `business_type='PLAYBOOK'`** 放行全空作用域（全平台语义）；其余 6 个业务类型照旧强校验 |
| rag `filters` → `pg_store` | 只认 `file_ids` / `company_ids` / `thread_id` / `created_by` 几个**硬编码**键 | 加 `chunk_kind` 过滤键，供路由只查 `profile`、取正文只查 `body` |
| `factory.vectorize_by_space` | `processor.summarize` **无条件调用**，STANDARD 还会追加一条 `chunk_kind='summary'` 分段 | 加 keyword-only 参数 `with_summary: bool = True`，导入脚本传 `False`。**改动就一行**——`summary = await processor.summarize(...) if with_summary else None`，下游 `if is_kb and summary:` 自然不成立，摘要分段一并不产生。生产上该函数**只有 `ingest_pipeline.py` 一个调用方**、不传即行为不变，血缘极窄 |

三处都动**共用代码**，其中 filters 那块紧邻租户隔离逻辑（`_recall_scope_from_filters`）。硬性要求：

- 新增分支**只在显式传入新键时生效**，不传时行为与改动前**逐字节一致**；
- 配套单测覆盖"不传新键 → 与改动前同结果"，防止误伤 KB / 会话文件召回。

### 4.7 库归属与跨库

| 表 | 库 | 迁移 |
|---|---|---|
| `ai_rag_space` / `ai_rag_entry` / `ai_rag_business_association` | 业务库（现状） | 无（已存在） |
| `ai_rag_ent_kb_chunk` | 向量库（现状） | `sql/migrations/vector/V005__spring115_playbook.sql`——**只加 §4.3 那个部分索引**，不改表结构 |
| **`ai_playbook`** / **`ai_r_playbook_relation`** | **业务库**（与 space / entry 同库，可 JOIN） | `sql/migrations/business/V019__spring115_playbook.sql` |

**跨库后果**：路由在向量库（chunk）、映射 / 扩展 / 取属性在业务库（playbook / relation / entry）、取正文回向量库——共 **3 次交互**（§5）。全程按 `entry_id` / `pid` **点查**，**任何时候不写跨这两组表的 JOIN**——本地未配 `RAG_DATABASE_*` 时向量库会回退到业务库、看着能 JOIN，一上有独立向量库的环境就崩。

## 5. 检索链路（两段式 + 图扩展）

入口 `query` = 模型调 `search_playbooks` 时**自拟的检索词**（陈述式关键词，非用户原话直传；§6.1）。

⚠️ **全链路是 3 次数据库交互，不是 5 个串行步骤**——「映射 / 扩展 / 取属性」三件事同在业务库、可 JOIN，**必须合并为一条 SQL**。

```
━━ 阶段 1 ┃ 向量库 ┃ 1 次查询 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【路由】在该 space 的 profile chunk 上向量检索（每 playbook 恰 1 条，共 64 条）
        → 产出 top_k(=3) 个 seed 节点的 entry_id
        · 只查 profile、绝不掺 body
        · profile 与 playbook 1:1，故无需"从 chunk 去重到 playbook"

              ↓  传 entry_id[]

━━ 阶段 2 ┃ 业务库 ┃ 1 次查询（一条 SQL，含递归 CTE）━━━━━━━━━━━━

【映射】  entry_id → ai_playbook → pid（+ category / stage）
【扩展】  沿 pid 递归走 ai_r_playbook_relation：
              DEPENDS_ON → 出边 ≤2 跳（前置）
              FEEDS      → 入边  1 跳（输入源）
              REFERENCES → 不扩展
【取属性】JOIN ai_rag_entry → title / summary
              seed 与扩展节点都取；扩展节点的 summary 即其简介
        · 三件事同库可 JOIN，务必**合并成一条 SQL**，别写成三次往返

              ↓  传 seed 的 pid[] + 扩展节点（已带 title / summary）

━━ 阶段 3 ┃ 向量库 ┃ 1 次查询 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【取正文】只取 seed 的 body chunk（`chunk_kind='body'`）
        每 seed = body 首段（元数据块，固定带）+ 相似度前 2 段
        · 扩展节点**不取正文**——阶段 2 已给 summary 作简介，防 context 爆炸

              ↓

组装：3 个 seed（带正文）+ 各自 prerequisites / inputs（只带简介）
```

**检索词口径为什么重要**：docstring 明确要求"陈述式关键词、不要整句照抄"（与 `search_knowledge_base` 同口径），这对召回质量有实际影响——profile 里嵌的是 `Key questions`（§3.1），检索侧给出**主题式短语**比灌一整句带寒暄和上下文的原话更容易对上；而且 standard 轨在此之前还有 `rewrite_node` 补全过公司/指标/期间，模型手里已是明确的问题。**评测时也必须按这个口径构造查询**，否则测出来的数字与线上不同源。

**路由为什么只查 `profile`**：实测混入 body 会把 r@1 从 80.9% 拖到 61.8%。profile 是"这本手册解决什么问题"，天然匹配"我该怎么做 X"；body 是具体行文，适合当细节而非路由依据。

**路由的候选粒度（易误读，说清）**：一个 playbook = 1 条 entry = **1 条 profile chunk**，三者 1:1，所以在 64 条 profile 上取 top_k 条天然就是 **top_k 个互不相同的候选 playbook**，不需要"从 chunk 去重到 playbook"这一步。这是两段式的附带好处：预研版本在 387 条混合 chunk 上做 chunk 级召回，同一 playbook 的多个 body 段会**挤占候选名额**（top-10 条 chunk 可能只剩 4~5 个不同 playbook），选型评测就栽在这里——未对齐候选口径，一度得出"方案 3 +14%"的错误结论（见对比文档 §4.1）。

**扩展为什么按关系类型分方向**（§4.5.1 / §4.5.2）：

| 类型 | 方向 | 为什么 |
|---|---|---|
| `DEPENDS_ON` | 出边，≤2 跳 | 出边即前置；补上那 **56.2%** 纯向量召不到的依赖项 |
| `FEEDS` | **入边**，1 跳 | 有用的是"谁喂给我"（输入源）。若也走出边只会拿到下游消费方——预研 Q2（产品路线图）图增益几乎为零，正是因为拉进来的是弱关联下游。只走 1 跳：隔两层的输入源关系已很弱，拉进来是噪声 |
| `REFERENCES` | 不扩展 | 软提及（"预算正文里提了一句 KPI 周会"），既非前置也非数据流，跟着 2 跳只会稀释 context |

**取正文为什么固定带 body 第一段**：该段是"`Players / Initial Effort / Ongoing / Frequency / Stage` + 开篇"的元数据块。纯按相似度取 3 段时它未必入选（平均 5 段选 3），而"这事多久做一次、谁负责、要多少投入"恰是可执行答案的必要成分。固定带上它，等于用 0 成本换掉两个数据库列（§4.4）。

**扩展节点为什么只给简介、不给正文**：预研已验证展开正文会让 context 爆炸——2 跳能拉出十几个节点，每个再给 5 段正文直接超预算。而且没必要：用户问的是那几个 seed 怎么做，前置项只需说明"你还得先做 X"。简介直接用**阶段 2 已取回的 `ai_rag_entry.summary`**（= 源站 `description`），**不必再去向量库捞 profile 文本**。

**体量**：3 seed × 3 段 × 1400 字符 ≈ 12k 字符 ≈ 4k token，加扩展节点简介后单次工具返回可控。

**默认参数**：`top_k=3`；`DEPENDS_ON` hops=2、`FEEDS` hops=1；每 seed 取 3 段（body 首段 + 相似度前 2，去重后不足则少给）。

#### ⚠️ 5.1 防环必须用 `path` 数组，**不得**用 `CYCLE` 子句

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

其余特性在 PG 13 上均已确认可用：递归 CTE（8.4+）、JSONB `->>`（9.4+）、部分索引、`ARRAY` 与 `= ANY()`。pgvector 0.8.0 远高于 HNSW 所需的 0.5.0（本设计新增的是普通 btree 部分索引、本不依赖 pgvector，此项确认的是现有 chunk 表 HNSW 索引的基础在位）。**本设计除 `CYCLE` 外无任何版本依赖。**

写法（`depth < N` 是必需的刹车，与防环二者缺一不可）：

```sql
WITH RECURSIVE walk(pid, via_pid, rel_type, depth, path) AS (
    SELECT r.target_pid, r.source_pid, r.rel_type, 1, ARRAY[r.source_pid, r.target_pid]
      FROM ai_r_playbook_relation r
     WHERE r.source_pid = ANY(:seed_pids) AND r.rel_type = 'DEPENDS_ON'
  UNION ALL
    SELECT r.target_pid, w.pid, r.rel_type, w.depth + 1, w.path || r.target_pid
      FROM walk w JOIN ai_r_playbook_relation r ON r.source_pid = w.pid
     WHERE r.rel_type = 'DEPENDS_ON'
       AND w.depth < :hops
       AND NOT r.target_pid = ANY(w.path)     -- 防环：走过的不再走
)
SELECT DISTINCT pid, via_pid, rel_type, depth FROM walk;
```

用 `UNION ALL` 而非 `UNION`：后者每轮多一次去重排序；本查询靠 `path` 防环、结果层再 `DISTINCT`，不需要它。

## 6. 工具契约与提示词

### 6.1 `search_playbooks`

```
search_playbooks(query: str, top_k: int = 3) -> {
  ok: bool,
  playbooks: [{
    pid, title, category, stage,
    excerpts: [str],                       # 正文段：body 首段（元数据块）+ 相似度前 2 段
    prerequisites: [{pid, title, summary}],  # DEPENDS_ON 出边扩展来的前置（只给简介）
    inputs: [{pid, title, summary}]          # FEEDS 入边扩展来的输入源（只给简介）
  }],
  note?: str,        # 无命中 / 关联项暂缺
  message?: str      # ok=false 的降级说明
}
```

**`prerequisites` 与 `inputs` 分成两个字段**、不合并成一个带 `rel_type` 的列表：二者语义完全不同——前置是"必须先做"（决定步骤顺序），输入源是"它的产出会喂进来"（决定数据依赖）。合并后模型得自己按 `rel_type` 分辨，容易把输入源误当成前置写进步骤序列。分开命名就没有歧义。

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

## 7. 数据导入与幂等

`scripts/import_playbooks.py` 的步骤：

1. **定位 / 创建空间**：按 `business_type='PLAYBOOK'` 找关联（§4.1），没有则经 `create_association(auto_create_space=True)` 建一个 STANDARD 空间；
2. **逐条 playbook 入 rag**（按 §4.2.1 方案 A 自行编排，不直接调 `ingest_text`）：按 `(space_id, title)` 查既有 entry → 有则软删旧的并清其向量 → 建新 entry（`company_id=NULL`、`summary` 写源站 `description`、不触发 LLM 摘要）→ 复用 rag 的切分与 embedding 产出 body 分段（自动带 `chunk_kind='body'`）→ **额外注入一条 `chunk_kind='profile'` 分段**；
3. **写属性表** `ai_playbook`（pid ↔ entry_id 映射 + category / stage / questions）；
4. **写关系边** `ai_r_playbook_relation`。

⚠️ **profile 分段要显式打 `chunk_kind='profile'`**（§4.3）：body 由 rag 流水线自动标 `body`，但 profile 是导入脚本额外注入的一条，**必须自己写上这个 metadata 键**——漏了它，路由阶段就一条也查不到。参照 `base.py` 注入 summary 分段的写法。

### ⚠️ 7.1 关系边只增不删

| 表 | 重跑策略 | 理由 |
|---|---|---|
| `ai_rag_entry` + chunk | 走 rag 既有幂等（同 space 同 title 复用 entry、重新向量化替换 chunk） | 正文分段数会变，必须整体替换 |
| `ai_playbook` | UPSERT（按 `pid` 更新属性） | 属性以源站为准，可覆盖 |
| **`ai_r_playbook_relation`** | **`ON CONFLICT DO NOTHING`，只补新边、不删不改** | **JSON 只是初始种子，DB 才是权威源** |

边表这条是刻意取舍。前提是"关系会持续扩充"，以后必然有人直接在 DB 里加边；若照搬"先删后插"，某天重跑一次导入就会**把人工维护的边全冲掉**。

**代价**：改 JSON 里已有的一条边、重跑脚本**不会生效**——这是预期行为。要全量替换必须显式 `--replace-edges`。

387 段重嵌约 $0.003、数秒，**不做 content-hash 增量**（YAGNI）。

## 8. 错误处理

| 情形 | 返回 |
|---|---|
| 向量库不可用 / SQL 异常 | `ok=False, message="playbook library is temporarily unavailable"` |
| embedding 调用失败 | 同上 |
| 检索无命中 | `ok=True, playbooks=[], note=...` |
| **图扩展失败** | `ok=True` + 纯向量结果，`note` 注明关联项暂缺——**降级不整体失败**，图是增强不是必需 |

**红线**：`ok=False` 时提示词必须要求如实说"暂时不可用、稍后重试"，**绝不能说成"没有找到相关 playbook"**。把服务故障说成"内容不存在"是最误导用户的一类错误（`search_knowledge_base` 已踩过并写死同款约束）。

**数据容错**：`define-the-vision` 无正文，被召回时 `excerpts` 为空、只给 profile，按正常情况处理，不得报错。

## 9. 可观测

- **LLM**：embedding 走 `llm_db_router.aembed(call_purpose="playbook_search")`，自动落 `ai_llm_call_log`，无需额外埋点
- **链路**：service 编排方法挂 `@traced_span`，span 记 `seed_count` / `expanded_count` / `hops`
- **排障日志**（对齐 `search_knowledge_base scope: ...` 的习惯，实践证明最省排障时间）：

  ```
  search_playbooks: q=%r top_k=%d -> seeds=%s expanded=%s(depth<=%d) excerpts=%d
  ```

## 10. 测试

**关键约束**：这层**不能用 SQLite 做单测**——`vector` 类型 SQLite 完全不支持，数组运算（`ARRAY[...]` / `= ANY(path)`）也没有。

| 层 | 位置 | 方式 |
|---|---|---|
| service 编排 | `tests/rag/test_playbook_service.py` | **mock repository**；覆盖 seed→expand→拼装、图扩展失败降级、空召回、无正文 playbook |
| 工具 | `tests/ai/tools_v2/test_search_playbooks_tool.py` | mock service；覆盖 ok / 空 / `ok=False` 三态 + 返回结构 + `ui_label` 契约 |
| SQL 正确性 | 上线抽验（§11 步骤 3） | **不新造真连 PG 的单测**——项目已有 `test_delete_thread_ok` 这一真连 5432 的痛点长期挂在待优化项，不再新增同类 |

**召回回归**：`scripts/eval_playbook_recall.py` + `scripts/data/playbook/golden_queries.json`（157 题）。

金标构造方式（复现必读）：playbook 自带的 157 条 `questions` **原文就在 profile chunk 里**，直接用会数据泄漏；故先用 haiku 改写成口语化提问（平均词面重合度降至 43%）。评测时**候选口径必须按"取到 k 个不同 playbook 为止"对齐**，否则比的是表的粒度而非方案——首轮就是栽在这里，得出过方案 3 "+14%" 的错误结论。

**不进 CI**（需 API key + DB）。以下情况必须手工跑一遍：改切分参数、换 embedding 模型、加 rerank、大批量加边。

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

1. `python scripts/migrate.py --target business` 建 `ai_playbook` + `ai_r_playbook_relation` 两张表
2. `python scripts/import_playbooks.py`：建 PLAYBOOK 空间与关联 → 64 条 playbook 自行编排入 entry + chunk（§4.2.1 方案 A）→ 写属性表与关系边（需 `OPENROUTER_API_KEY`）
3. 抽验：
   - `ai_rag_business_association` 有 1 条 `business_type='PLAYBOOK'`、作用域三列全 NULL
   - `ai_rag_entry` 该 space 下**未软删** 64 行、`ai_playbook` 64 行、`ai_r_playbook_relation` 28 行
   - **连跑两次导入后，未软删 entry 仍是 64 行**（验 §4.2.1 的幂等，这是最容易出错的一条）
   - chunk 表该 space 下 **`chunk_kind='profile'` 恰好 64 条**（每 playbook 一条）、`chunk_kind='body'` 约 323 条；**`chunk_kind='summary'` 必须为 0 条**（验 §4.6 的 `with_summary=False` 真的生效）
   - 跑一次 `search_playbooks` 看 seed / prerequisites / inputs 是否合理
   - devSupport 的 rag 空间页能看到这个 playbook 空间及其 64 个文档
4.（可选）`python scripts/eval_playbook_recall.py --run` 确认召回未劣化

## 12. 关键决策记录

| # | 决策 | 理由 / 被否方案 |
|---|---|---|
| D1 | 关系边落 PG 表而非 LadybugDB | 召回能力完全相同；在"关系持续扩充"前提下，图文件"改边要重建 + 孤儿依赖"是经常性成本 |
| D2 | **复用 rag 的 space / entry / chunk 承载 playbook**（取代原"自建三张表"） | 原方案平行重造了一套 mini-RAG（自建 chunk 表 + 自写向量检索 + 自写切分嵌入）。复用后省下这些，并白得召回日志、命中统计、devSupport 管理页；`business_type='PLAYBOOK'` 枚举值本就存在，说明这也是当初的设想。**注意**：选型阶段否掉的"方案 2"是"playbook 混进公司 KB 的召回池、走 `search_knowledge_base`"，与本决策不同——本决策是**独立 space + 独立工具**，只复用存储模型，不复用 KB 的公司级圈定 |
| D3 | 不合并关联文本进同一 chunk | **实测负收益**（r@1 −5.1%）；且无法反向查询、只能 1 跳静态 |
| D4 | 两段式检索（profile 路由 / body 细节） | 实测 r@1 80.9% vs 61.8%，差 19 个百分点 |
| D5 | **用 `metadata.chunk_kind='profile'` 区分 profile / body** | rag 已在用 `chunk_kind`（`body` / `summary`），加一个取值即可、不发明机制。代价是给共用 chunk 表加一个**部分索引**（仅 64 行，零影响） |
| D6 | **属性表 `ai_playbook` 仍需保留** | rag 的 entry 装不下 pid / category / stage / questions；但 title / description 复用 entry 的 title / summary，不重复存 |
| D7 | 关系边只增不删 | 防止重跑导入冲掉人工维护的边 |
| D8 | 一期不做内部查看器 | 只搬数据不搬代码后，查看器等于从零新写；且复用 rag 后 **devSupport 的 rag 空间/文档/片段页已能看 playbook**，独立查看器的必要性进一步下降 |
| D9 | 收编评测脚本与金标集 | 一次性构造成本已付；无它则后续任何调参只能凭感觉 |
| D10 | **`FEEDS` 走入边、`REFERENCES` 不扩展** | 实测 `FEEDS` 无法由 `DEPENDS_ON` 推导（§4.5.2）；其箭头是数据流向，有用的方向是"谁喂给我"。`REFERENCES` 是软提及，2 跳只稀释 context |
| D11 | **`entry.summary` 写源站 description；LLM 摘要用 `with_summary=False` 关掉** | 原文更准，且省掉 64 次调用与 64 条无人检索的 summary 分段。跳过方式是给 `vectorize_by_space` 加一个默认开启的开关（§4.6 第三处放宽，一行改动），**不**绕过该函数——绕过要重抄私有的 `_prune_chunk_metadata` 与 body 打标 |
| D12 | **导入自行编排 entry 写入，不直接调 `ingest_text`** | `find_duplicate_title` 对 `company_id=NULL` 恒不命中，照用会让每次重跑重复新增 64 条 entry（§4.2.1）；且 playbook 还要额外注入 profile 分段，本就超出 `ingest_text` 的行为 |
| D13 | **防环用 `path` 数组，不用 `CYCLE` 子句** | `CYCLE` 需 PG 14+，而**测试环境实测为 PG 13.23、直接语法报错**（§5.1）；省一行代码换来「每个环境都得先验版本」的部署风险，不值 |

## 13. 后续

- **二期 诊断式推荐** `recommend_playbooks(company_id)`：读财务 / benchmark 短板 → 映射 category / stage → 按 DEPENDS_ON 拓扑排序给执行顺序。本期已把 category / stage 结构化，无需再迁表。
- **内部查看器**：按其独立设计文档单独排期。
- **rerank**：`llm_db_router.rerank`（Cohere）在预研里已验证可用，本期未接；接入前先用金标集量化增益。
- **扩写 profile 的 `Key questions`（低成本、见效可能最直接）**：现在每个 playbook 只带 2~3 条问法，覆盖的表达空间窄，是 §3.1 所说"线上召回会低于 80.9%"的主因。用 LLM 给每条 playbook 扩写到 8~10 条不同问法后重嵌 profile，理论上能直接抬高路由准确率。成本极低（64 次调用、几分钱、387 chunk 重嵌 $0.003），且**有金标集可以量化验证是否真的有效**——先跑基线、扩写后再跑一次对比，不生效就回滚。
  ⚠️ 若做这一步，金标集需**同步重建**：现有 157 题就是从原 questions 改写来的，扩写后原 questions 仍在被检索文本里，泄漏面反而扩大。届时应改用"由 body 正文出题"的方式另建一套金标，与现有那套并存对比。
