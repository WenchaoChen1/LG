# Playbook 接入 Chatbot 开发设计：召回方案选型对比（含实测）

> 关联文档：
> - 预研原型（上游）：`python/CIOaas-python/source/playbooks_graph_db/`
> - 预研产出记录：`python/CIOaas-python/source/playbooks_graph_db/graph_rag_demo_results.md`
> - 向量表 DDL：`python/CIOaas-python/sql/sprint112/playbook_graph_schema.sql`
> - 内部查看器设计（同源、非本文范围）：[../../superpowers/specs/2026-06-23-playbook-knowledge-design.md](../../superpowers/specs/2026-06-23-playbook-knowledge-design.md)
>
> 阶段：⑤ 开发设计 | 版本：v1 | 日期：2026-07-28 | 端：Python（CIOaas-python） | 范围：playbook 在 chatbot 内的存储与召回选型
>
> 说明：本文是**选型对比**，结论用实测数据支撑；被选中方案的落地设计另文。本文不含完整函数体与 DDL（遵循 docs 规范）。

---

## 1. 背景与目标

`feature/sprint112-age` 分支已完成 playbook 预研：抓取 Golden Section 公开的 vertical SaaS playbooks，建成「图关系 + 向量」双存储原型。现需把它落到 sprint115 的 chatbot 里。

**已确认的两个用途**（决定了方案取舍）：

| 用途 | 说明 | 对检索的要求 |
|------|------|--------------|
| 方法论问答 | 用户问「怎么做现金流预测 / 怎么搭销售管道」，给可执行步骤 | 找对 playbook + 拿到正文细节 |
| **诊断式推荐** | 结合公司财务 / benchmark 指标判断短板，推荐该执行哪几个 playbook 及**先后顺序** | **必须能查「做 X 前要先做什么」「谁依赖 X」——这是结构查询，语义相似度替代不了** |

**已确认的数据形态**：playbook 条目与关系边会**持续扩充**，需要有人长期维护关系。这把「关系边的维护成本」从一次性变成经常性，是区分方案的关键变量。

## 2. 现有资产盘点

| 项 | 现状 |
|---|---|
| 语料 | 64 条 playbook 节点（源站 66+），63 条有正文（`define-the-vision` 在源站已并入 `executive-execution`） |
| 结构化属性 | pid（业务键：源站标题 slugify 后的 slug，如 `cash-flow-forecast`，关系边引用的就是它）/ title（标题：手册名）/ category（分类：6 值 Executive、Sales & Marketing、Development、Customer、Operations、Vendor）/ players（负责角色：谁来做，如 Founder、CFO）/ stage（适用阶段：5 值 Pre-Revenue、Early Traction、Traction、Growth、All Stages）/ frequency（执行频率：多久做一次，如 Monthly、Quarterly）/ description（简介：一句话说明这本手册解决什么问题，源站原文）/ questions（预期问法：每本 2~3 条，全库 157 条；进 profile 的 `Key questions:` 段，把匹配变成 query↔query） |
| 关系边 | **28 条**：DEPENDS_ON 21 / FEEDS 5 / REFERENCES 2，**人工策划与推断**而来 |
| 向量 | `ai_rag_playbook_chunk`（**RAG 向量库**，由 `sql/migrations/vector/` 建；带 `embedding` 列的 chunk 表都归向量库，其余 `ai_rag_*` 元数据表在业务库），387 chunk = 64 profile + 323 body，1536 维，embedding 模型与 RAG STANDARD 一致 |
| 图 | LadybugDB 嵌入式**单文件** 5.6MB，已提交进仓库作测试/部署数据 |
| 查询侧 | `PlaybookRecallService`：recall / rerank(Cohere) / answer(图增强合成) / recall_list / graph_detail，扁平原型未分层 |
| HTTP | `/api/ai/playbook/{recall,detail,answer}`，登录即可访问、**全局不按公司过滤** |

**贯穿所有方案的张力**：playbook 是**全局共享的第三方方法论**，而 chatbot 现有知识库是**公司私有上传件**（检索范围由 `ai_file_registry` 按 company_id 圈定）。两者作用域模型不同。

## 3. 候选方案

### 方案 1：沿用预研（LadybugDB 图 + 独立向量表）

把现成 `PlaybookRecallService` 包成 chatbot 工具注册进 `TOOL_REGISTRY_V2`，存储与召回原样搬运。

- **落地**：查询侧代码已跑通，主要工作是按 standards 从扁平原型重构进分层、包工具、写提示词。两个未验证点：LadybugDB 只读连接在多 worker 下的行为；嵌入式本地文件在容器部署时的打包/挂载（现为 `Path(__file__).parent` 本地目录）。
- **维护**：两套存储、两套备份、两种查询语言（Cypher + SQL）。**改一条关系边要跑 import 脚本重建整个图文件**；`real_ladybug` 在本技术栈无第二个使用场景，长期是孤儿依赖。在「关系持续扩充」的前提下，这是**经常性**成本。
- **召回**：见 §4 实测——图扩展补上 56.2% 纯向量召不到的前置项。

### 方案 2：playbook 进现有知识库（rag space）

64 条 playbook 当文档灌进一个 STANDARD space，复用 `search_knowledge_base`。

- **落地**：入库链路现成，但**卡在作用域模型**。两条路都不好走：给每个公司各登记一份 → 数据冗余 N 份、向量化成本 ×N、内容更新要刷 N 遍；或改 `search_knowledge_base` 支持「全局 space」新路径 → **改动的是安全关键的租户隔离代码**。
- **维护**：最低。复用 RAG 全套基建（版本化迁移、知识库面板、状态机、重试、软删）。
- **召回**：**关系边彻底丢失**，诊断式推荐做不了。另有隐患：playbook 与公司自有文档进同一召回池会互相稀释——用户问「怎么做现金流预测」可能召回公司自己上传的现金流表格而非方法论。

### 方案 3：关联文本合并进同一 chunk

把有关系的 playbook 正文/简介拼进同一 chunk，靠向量一次召回带出关联内容。

- **落地**：最低，纯离线数据加工，查询侧零改动。
- **维护**：**写放大**——改 1 条边要重切、重嵌入受影响的多个 chunk；关系变成**隐式**的（埋在文本里），无法查询、校验、可视化。
- **召回**：见 §4 实测——**实测为负收益**。且结构上无法回答「谁依赖 X」这类反向查询，只能 1 跳、静态。

### 方案 4：关系边落 PG 表 + 递归 CTE（本文推荐）

保留「图」的**能力**，换掉承载它的**存储**：28 条边进 `ai_rag_playbook_edge(source_pid, target_pid, rel_type)`，向量仍在 pgvector，多跳扩展用 `WITH RECURSIVE`。

- **落地**：一张表 + 一段递归 CTE，替换 `_graph_expand` / `_direct_rel_map` / `graph_detail` 三个方法，其余（向量召回、rerank、answer 合成、提示词、eval 脚本）原样复用。边数据从现有 JSON 一次性导出。比方案 1 少一个「嵌入式文件怎么部署」的未知数。
- **维护**：**单一存储、单一查询语言**。走现有版本化迁移 `sql/migrations/`；加边就是一条 INSERT；可用外键 + 唯一约束保证边合法（图文件做不到）；备份恢复与业务库统一。正对「关系持续扩充」这个痛点。
- **召回**：与方案 1 **完全相同**——同样的向量召回、同样的多跳扩展，只是执行引擎从 Cypher 换成递归 CTE。当前 64 节点 / 28 边，扩到数百条边 PG 递归 CTE 依然无压力。
- **代价**：失去 Cypher 表达力（PageRank、最短路径等）。当前用法只有 1–2 跳邻居 + 邻域子图，用不上。

## 4. 实测（2026-07-28）

### 4.1 方法

**必须先解决数据泄漏**：profile chunk 的文本是 `"{title} ({category}). {description} Key questions: {questions}"`——157 条 questions 原文就在被检索的 chunk 里，直接拿它们当查询会让召回率虚高到无参考价值。故先用 haiku 把 157 条改写成口语化提问（平均词面重合度降至 43%），得到无字面泄漏的金标集，每条查询的期望命中 = 其所属 playbook 的 pid。

**候选口径对齐**（第一次跑出错误结论的原因）：一 playbook 多 chunk 的表（387 条）若按 chunk 取 top-k 再去重，会因同一 playbook 的多个 body 段挤占名额而只剩 4~5 个候选；而一 playbook 一 chunk 的表（64 条）top-k 就是 k 个候选。**必须按「取到 k 个不同 playbook 为止」对齐**，否则比的是表的粒度、不是方案。

### 4.2 结果

候选统一为 10 个不同 playbook，n=157：

| 检索配置 | r@1 | r@3 | r@5 | MRR |
|---|---|---|---|---|
| A1 profile+body（现状 387 chunk） | 61.8% | 86.0% | 92.4% | 0.756 |
| **A2 profile-only（64 chunk）** | **80.9%** | **94.3%** | **97.5%** | **0.880** |
| C 方案 3 合并关联 chunk（64 chunk） | 75.8% | 93.0% | 96.8% | 0.849 |

**前置项覆盖**（图关系的净增益）：73 组 (问题, 关系边) 中，纯向量 top-5 只带出 **43.8%**，**56.2% 完全召不到**。用 A1 / A2 两种基线分别测，结果一致，结论稳健。典型漏检：

```
budget-creation  -[DEPENDS_ON]->  define-the-mission     （做预算前要先定使命）
cash-flow-forecast -[DEPENDS_ON]-> budget-creation
budget-creation  -[REFERENCES]->  kpi-and-strategic-meetings
```

### 4.3 三个结论

**① 方案 3 是负收益。** 同粒度对照下 **r@1 −5.1%、MRR −0.030**。合并让 chunk 从 252 → 496 字符，语义被稀释；top-1 命中的 chunk 平均混入 0.8 个其它 playbook 的文本。首轮跑出的「+14%」是候选口径未对齐造成的假象，修正后优势消失并转负。

**② body chunk 正在拖累「找对 playbook」。** profile-only 的 r@1 = 80.9%，加上 323 条 body 后**跌到 61.8%，掉 19 个百分点**。原因：body 是具体行文，某个 playbook 的正文段常比正确 playbook 的 profile 更「像」用户的提问，把正确答案挤下去。
→ 指向**两段式检索**：**profile 定位 playbook（路由）→ 再取该 playbook 的 body 拿细节**。此结论独立于四个方案、对谁都适用。

**③ 图关系是刚需且不可替代。** 56.2% 的前置项纯向量根本召不到——这些前置在语义上离问题很远（「做预算」与「定使命」），向量再怎么调都找不到，只能靠关系边。预研文档的定性结论至此有了数字支撑。

### 4.4 局限（结论适用边界）

1. **绝对数字偏乐观**：金标来自 playbook 自带 questions 的改写，而这些 questions 原文在 profile 里——字面泄漏已消除，**语义泄漏仍在**。但 A1 / A2 / C 共享同一偏差，**相对比较有效**。
2. 前置项覆盖仅 73 组样本，且只覆盖现有 28 条人工边。
3. 未测 Cohere rerank 的增益。
4. 未测多跳（hops≥2）扩展带入的噪声代价。

## 5. 横向对比与结论

| | 方案 1 LadybugDB | 方案 2 进知识库 | 方案 3 合并 chunk | **方案 4 PG 边表** |
|---|---|---|---|---|
| 召回（实测） | r@1 80.9% + 图补 56.2% 前置 | 同底座但**无图** | **r@1 75.8%，负收益** | **同方案 1** |
| 落地难度 | ★★☆☆☆（部署有未知） | ★★★☆☆（卡全局作用域） | ★☆☆☆☆ | ★★☆☆☆ |
| 维护成本 | ★★★★☆ 双存储 / 孤儿依赖 | ★★☆☆☆ | ★★★☆☆ 改边即重嵌入 | ★★☆☆☆ |
| 多跳扩展 | ✅ | ❌ | ❌ 仅 1 跳静态 | ✅ |
| 反向查询（谁依赖 X） | ✅ | ❌ | ❌ | ✅ |
| 关系可校验 / 可视化 | ✅ | ❌ | ❌ 隐式 | ✅ |
| 支持方法论问答 | ✅ | ✅ | ✅ | ✅ |
| **支持诊断式推荐** | ✅ | ❌ | ❌ | ✅ |
| 与公司私有文档隔离 | ✅ 独立表 | ⚠️ 同池稀释 | ✅ | ✅ 独立表 |
| 新增技术栈 | LadybugDB | 无 | 无 | 无 |

**淘汰过程**

1. 方案 3 实测负收益 → 出局（其「关联文本放一起」的诉求由方案 4 的关系边以结构化形式满足）；
2. 方案 2 做不了诊断式推荐，且要动租户隔离代码 → 出局；
3. 方案 1 与方案 4 **召回能力完全相同**，差别只在维护成本；在「关系会持续扩充」前提下，LadybugDB「改边要重建图文件 + 孤儿依赖」的代价长期不划算 → 方案 4 胜出。

**结论：采用方案 4 + 两段式检索。**

- 关系边落 PG 表，递归 CTE 做 1–2 跳扩展；
- 检索分两段：profile 路由定位 playbook → 取该 playbook 的 body 给细节；
- 预期收益：r@1 从现状 61.8% → 80.9%，同时保住 56.2% 那部分只能靠图补的前置项；
- sprint112-age 的成果绝大部分保留（向量表、chunk 切分、rerank、answer 合成、提示词、eval 脚本均不动）。

## 6. 复现方式

评测脚本与 157 题金标集当前在临时目录，尚未入库（是否收编为 `source/playbooks_graph_db/eval_recall_golden.py` 待定）。复现步骤：

1. 建表灌数：执行 `sql/sprint112/playbook_graph_schema.sql`（幂等），再灌 387 chunk 向量；
2. 生成金标：157 条 questions 经 haiku 改写并缓存（一次性）；
3. 跑 A / B / C 三组实验。

注意事项：`import_playbooks.py` 顶层 `import real_ladybug`，未装该包时无法复用其函数，评测脚本内联了同款切分逻辑（常量 `BODY_CHUNK_CHARS=1400` / `BODY_CHUNK_OVERLAP=150` 与生产一致）。关系边直接读 `playbooks_data.json`，评测全程不需要图数据库——这一点本身也验证了方案 4 的前提。
