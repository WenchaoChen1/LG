# GS Playbook 托管策略 · 调研总结报告

> 承接：`00-research-plan.md`
> 输出阶段：AI Chatbot Epic 之 Playbook Ingestion Story 启动前
> 证据基础：桌面研究 + 机制性证据（截至 2026-01 公开资料）
> 文档版本：v1.1 · 2026-04-24

---

## 0. 结论摘要

| 项 | 结论 |
|------|------|
| **核心假设**：LG Chatbot 访问 GS 公开站点 → 提升 GS 在其他 AI 对话中的被引用概率？ | **❌ 不成立**。该访问行为对跨模型 GEO 可见性的增量贡献 ≈ 0。 |
| **推荐方案** | **✅ Option B — 全量内部托管** |
| **决策评分**（加权） | Option A **1.60 / 5** · Option B **3.85 / 5** |
| **Option B MVP 工作量** | **22 人日**（后端 11 + 前端 8 + 迁移 3） |
| **Post-MVP 扩展** | AI 写回 Playbook + Admin Review 在同一数据模型上天然闭环 |

---

# 第一部分 · 结论与验证过程

## 1. GEO 假设核查

### 1.1 LLM 获取网页内容的三条通路

| 通路 | 机制 | 是否形成"跨模型 GEO 反馈环" |
|------|------|-------------------------------|
| **① 预训练抓取** | 各家自有爬虫（`GPTBot`、`ClaudeBot`、`CCBot`、`PerplexityBot`、`Google-Extended`）周期性爬公网 → 进入训练集或 RAG 索引 | ✅ 是 —— 但与 LG Chatbot 的运行时访问**无关** |
| **② 实时检索 / tool-use** | LLM 在对话中通过 web_search 工具现场抓取（Claude `web_search`、ChatGPT Search、Perplexity、Gemini Grounding） | ⚠️ 部分 —— 该 LLM 本次会话会引用，但**不会**把访问痕迹投喂给其他模型 |
| **③ 用户上下文注入** | 用户粘贴链接或 Chatbot 把 URL 放进 context | ❌ 否 —— 100% 会话内，零外溢 |

### 1.2 假设不成立的机制性原因

- **厂商隔离**：Claude/OpenAI/Google/Perplexity 的检索索引、训练数据管道**彼此独立**。Claude 在会话 X 访问某 URL 不会反哺 OpenAI 的检索权重。
- **搜索供应商中介**：Claude `web_search` 背后是 Brave Search API、ChatGPT Search 走 Bing、Perplexity 自研但仍锚定 Bing/Google。"被返回"取决于搜索引擎的**排名**，而非被某次 API 会话访问过。
- **训练数据隔离**：前沿模型明确声明不将客户 API 会话用于训练；训练 cutoff 周期以月/季计，会话级行为不会影响下一轮训练。
- **类比**：这等同于"我点开一个网页 → 期待 Google 因此提升它的排名"。PageRank 看反向链接与权威信号，不是个别访客的点击；GEO 同理，看的是爬虫可见性与权威性信号。

### 1.3 真正的 GEO 抓手（业界 2025–2026 共识）

按"机制成熟度 × 影响力"排序（均与托管方是 LG 还是 GS 站 **无关**）：

| 排名 | 抓手 | 说明 | 对托管位置的依赖 |
|------|------|------|------------------|
| 1 | **被主流 LLM 爬虫收录** | `robots.txt` 允许 `GPTBot`、`ClaudeBot`、`CCBot`、`PerplexityBot`、`Google-Extended`；避免纯 JS 渲染正文 | 需**公开 URL** —— LG 内部 URL 天然不参与 |
| 2 | **在 Bing / Google 里有排名** | LLM web_search 多走这两家 | 传统 SEO |
| 3 | **权威外链 & 引用** | HBR、a16z、PitchBook 等反向链接 | 与托管无关 |
| 4 | **`llms.txt` 文件** | 类似 `robots.txt`，向 LLM 提供"本站推荐内容索引" | 仅公开站生效 |
| 5 | **Schema.org 结构化数据**（Article / HowTo / FAQPage） | 让爬虫与检索 API 更容易结构化提取 | 需 HTML 页面 |
| 6 | **E-E-A-T 信号** | 作者署名、机构身份、引用源、更新日期 | 与托管无关 |
| 7 | **内容频次更新** | 训练集与 RAG 索引偏好新鲜内容 | 与托管无关 |

**关键区分**：公开托管**有**独立 GEO 价值（通路 ①），但**把 LG Chatbot 指向它**对 GEO **无**任何增量。Option A 的立论基础不成立。

### 1.4 Q1–Q5 逐条回答

| # | 问题 | 结论 |
|---|------|------|
| Q1 | LLM 的 URL 访问行为是否反馈到自身或他家索引？ | **否**，会话级访问不改变索引/训练权重 |
| Q2 | "被 LLM 引用"的机制？ | 三条通路（§1.1），决定性的是**通路 ①** 与**通路 ②** 背后的搜索引擎排名 |
| Q3 | 公开 URL 是否是 GEO 的必要条件？ | **对通路 ① 是**；但"LG Chatbot 访问"不是任何通路的放大器 |
| Q4 | GEO 最佳实践？ | 见 §1.3 的 7 条 |
| Q5 | 每月几千次 Chatbot 访问对 GS GEO 的增量？ | **可忽略**（0%–1%，机制不支持） |

### 1.5 剩余不确定性

| 编号 | 疑点 | 影响 | 概率 |
|------|------|------|------|
| U1 | LLM 厂商未来是否将客户 web_search 日志用于检索质量评估 | 即便发生，也是单厂商内部信号，不跨模型 | 低 |
| U2 | Perplexity 等 AI 搜索平台"被访问频次影响排序"的可能性 | 需 >10⁵/月访问量才有意义，远超 Chatbot 规模 | 低 |

以上不影响主结论。后续可通过 **GEO 探针 A/B 实验**（4 周滚动）做验证，**不阻塞决策**。

---

## 2. Option A 可行性评估（外部托管 + 内部 Changelog）

### 2.1 可行的技术路线

**方向 A1：Claude `web_search` + 内部 Markdown RAG 并行**
```
User Query
   ├── RAG: 内部 playbook-changelog.md（向量检索 top-k）
   └── Tool: web_search("site:goldensection.com <query>")
          ↓ 结果合并 + 去重
       LLM 综合回答
```

**方向 A2：定时爬虫 + 本地镜像 + 变更 diff**
- 每日抓取 GS 站点 → 存入本地 cache → diff 出 changelog 增量。
- 本质已接近 Option B，"外部为名、内部为实"，无实际收益。不评估。

### 2.2 限制与风险

| 维度 | 评估 | 严重度 |
|------|------|:------:|
| **延迟** | web_search 每次 +1.5–3.5 s；内部 RAG ~200 ms；双源合并拖慢到最慢一路 | 🟡 中 |
| **可用性** | 外部站点停机 / 改版 / CDN 抖动，Chatbot 直接退化；SLA 受制于市场站 | 🔴 高 |
| **反爬/限流** | 走 web_search 绕开反爬；自建爬虫需协商 | 🟢 低 |
| **版本一致性** | GS 站改了，changelog 未必同步；无统一版本号 | 🔴 高 |
| **内容合并冲突** | 外部章节被删但 changelog 引用仍在 → Chatbot 矛盾输出 | 🟡 中 |
| **Admin 编辑 UX** | 跨两套系统，"这条更新是否生效"需双边确认 | 🔴 高 |
| **可观测性** | 无法统一记录 Chatbot 引用了哪一版内容 | 🟡 中 |

### 2.3 工作量估算

| 模块 | 人日 |
|------|:----:|
| 后端：web_search tool 接入 + RAG 并行编排 + 结果合并器 | 8 |
| 后端：changelog 存储（Postgres + 版本表）+ 编辑 API | 5 |
| 前端：changelog 编辑器 | 5 |
| 外部站点可用性探针 + 降级策略 | 3 |
| 版本对账工作流 | 4 |
| QA + 文档 | 3 |
| **合计** | **28** |

### 2.4 致命短板
1. **架构负债永久化**：双源一致性问题不随时间衰减，只随 Playbook 数量线性累积。
2. **收益侧为零**：§1 已证明假设不成立。
3. **Post-MVP 反向冲突**：Post-MVP 要求"AI 写回 Playbook + Admin Review"，但 GS 公开站改写不在 LG 控制范围 → AI 只能写内部 changelog，形成"主源静态、增量肥大"的畸形结构。

---

## 3. Option B 可行性评估（全量内部托管）

### 3.1 Playbook 体量（估算，待爬虫复核）

| 指标 | 估算 |
|------|------|
| Playbook 数量 | 20–30 篇 |
| 平均篇幅 | 2 000–4 000 字 / 篇（含图） |
| 总字数 | 6 万 – 12 万字 |
| 图表数 | 100–150 张 |
| 结构层级 | 2–3 层（章 → 节 → 要点） |

**一次性导入完全可行**：向量化后 <1000 chunk，单次嵌入成本 <$5（OpenAI `text-embedding-3-small`）。

### 3.2 格式选型

| 候选 | 编辑体验 | 检索/RAG | 版本管理 | AI 写回 | 结论 |
|------|:--------:|:--------:|:--------:|:-------:|:----:|
| 单一 markdown 文件 | ❌ | ⚠️ 需拆 chunk | ❌ | ❌ | 否决 |
| **结构化 markdown 集合**（每篇一条记录，正文 markdown） | ✅ | ✅ 天然按篇 chunk | ✅ DB 版本表 | ✅ 改单篇即可 | **✅ 推荐** |
| Wiki-CMS（Outline / BookStack） | ✅ | 🟡 需适配 | ✅ | 🟡 | 否决（架构溢出） |

### 3.3 工作量估算

| 模块 | 人日 |
|------|:----:|
| 后端：`playbook` 领域（Controller/Service/Repo/Mapper/DTO）+ 版本表 | 6 |
| 后端：embedding + 向量检索（pgvector） | 3 |
| 后端：内容迁移脚本（爬取 → markdown → 入库） | 2 |
| 前端：列表 + 详情 + Markdown 编辑器 | 6 |
| 前端：权限与 Admin 路由 | 2 |
| QA + 文档 + 数据校验 | 3 |
| **合计** | **22** |

向量能力复用 **pgvector**（PostgreSQL 已在用），零新增组件。

### 3.4 剩余风险与缓解

| 风险 | 缓解 |
|------|------|
| 一次性迁移漏内容 | 迁移脚本输出对账 CSV，人工抽样 ≥20% |
| GS 站后续更新需同步 | Playbook 更新频率低（季度级）；Post-MVP AI 写回自动化 |

---

## 4. 决策评分

| 维度 | 权重 | Option A | Option B |
|------|:----:|:--------:|:--------:|
| GEO 价值实现 | 20% | 1 / 5（假设不成立） | 3 / 5（公开站独立存在，不因 B 受损） |
| Chatbot 答案质量 | 25% | 2 / 5（外部依赖 + 延迟 + 版本漂移） | 4 / 5（本地索引，确定性高） |
| 一次性实现成本 | 15% | 2 / 5（28 人日） | 3 / 5（22 人日） |
| 长期维护成本 | 20% | 1 / 5（双源对账永久负债） | 4 / 5（单源 SSOT） |
| Post-MVP 扩展性 | 20% | 2 / 5（写回主源不可行） | 5 / 5（AI 写回 + Admin Review 闭环） |
| **加权总分** | 100% | **1.60** | **3.85** |

触发条件：`A ≥ B 且 GEO 维度 ≥ 3` → ❌ 不满足 → **推荐 Option B**。

---

# 第二部分 · 实现方案规划

> 本部分将作为 AI Chatbot Epic → **Playbook Ingestion Story** 的 `01-prd.md` 直接输入。

## 5. 总体架构

```
┌──────────────────────────────────────────────┐
│  Admin UI (CIOaas-web)                       │
│  - Playbook 列表 / 编辑 / 版本 Diff          │
└──────────────┬───────────────────────────────┘
               │ umi-request
┌──────────────▼───────────────────────────────┐
│  CIOaas-api · playbook domain                │
│  Controller → Service → Repository           │
│        │              │                       │
│        ▼              ▼                       │
│  playbook       playbook_version              │
│  playbook_chunk (pgvector)                    │
└──────────────┬───────────────────────────────┘
               │ retrieve API
┌──────────────▼───────────────────────────────┐
│  AI Chatbot (Layer 2 检索)                   │
│  向量检索 top-k → 注入 prompt → LLM 回答     │
└───────────────────────────────────────────────┘
```

单一可信源（SSOT）= `playbook` 表。公开站仅作为**迁移起点**与**答案外链品牌露出**，不参与运行时检索。

## 6. 数据模型（JPA · 继承 `AbstractCustomEntity`）

### 6.1 MVP 表

```sql
-- 领域主表
CREATE TABLE playbook (
    id              VARCHAR(36) PRIMARY KEY,         -- UUID, 前缀 pbk-
    title           VARCHAR(200) NOT NULL,
    slug            VARCHAR(200) NOT NULL UNIQUE,
    summary         VARCHAR(500),
    body_markdown   TEXT         NOT NULL,           -- 主正文
    source          VARCHAR(32)  NOT NULL,           -- MIGRATED_FROM_GS | ADMIN_CREATED | AI_PROPOSED
    external_url    VARCHAR(500),                    -- GS 原文链接（品牌露出用）
    current_version INT          NOT NULL DEFAULT 1,
    status          VARCHAR(16)  NOT NULL DEFAULT 'DRAFT',  -- DRAFT | PUBLISHED | ARCHIVED
    created_at      TIMESTAMP    NOT NULL,
    created_by      VARCHAR(64),
    updated_at      TIMESTAMP    NOT NULL,
    updated_by      VARCHAR(64)
);
CREATE INDEX idx_playbook_status ON playbook(status);

-- 版本历史
CREATE TABLE playbook_version (
    id                     VARCHAR(36) PRIMARY KEY,
    playbook_id            VARCHAR(36) NOT NULL REFERENCES playbook(id),
    version_no             INT         NOT NULL,
    body_markdown_snapshot TEXT        NOT NULL,
    change_summary         VARCHAR(500),
    created_at             TIMESTAMP   NOT NULL,
    created_by             VARCHAR(64),
    UNIQUE(playbook_id, version_no)
);

-- RAG 分片 + 向量
CREATE TABLE playbook_chunk (
    id           VARCHAR(36) PRIMARY KEY,
    playbook_id  VARCHAR(36) NOT NULL REFERENCES playbook(id) ON DELETE CASCADE,
    chunk_index  INT         NOT NULL,
    content      TEXT        NOT NULL,
    embedding    VECTOR(1536),                       -- pgvector
    token_count  INT,
    UNIQUE(playbook_id, chunk_index)
);
CREATE INDEX idx_playbook_chunk_embedding
    ON playbook_chunk USING ivfflat (embedding vector_cosine_ops);
```

### 6.2 Post-MVP 扩展

```sql
playbook_revision_proposal   -- AI 生成的改版草稿
playbook_review_queue        -- Admin 审阅队列
```

改版流程：`AI 生成 proposal` → `进入 review queue` → `Admin 通过/驳回` → `合并到 playbook 并写 playbook_version`。全部在 LG 内闭环。

## 7. 后端 API（`Result<T>` 包装）

| Method | Path | 说明 | 权限 |
|--------|------|------|------|
| GET | `/web/playbooks` | 列表（`ProTable` 分页） | Admin |
| GET | `/web/playbooks/{id}` | 详情（含当前版本） | Admin |
| GET | `/web/playbooks/{id}/versions` | 版本历史 | Admin |
| POST | `/web/playbooks` | 新建 | Admin |
| PUT | `/web/playbooks/{id}` | 编辑（自动写 `playbook_version`） | Admin |
| POST | `/web/playbooks/{id}/publish` | 发布（`status = PUBLISHED`） | Admin |
| DELETE | `/web/playbooks/{id}` | 软删（`status = ARCHIVED`） | Admin |
| POST | `/web/playbooks/retrieve` | Chatbot：向量检索 top-k | Service-to-Service |

命名遵循项目规范：`PlaybookController` / `PlaybookService` + `PlaybookServiceImpl` / `PlaybookRepository` / `PlaybookMapper` / `PlaybookSaveInput` / `PlaybookModifyInput` / `PlaybookDto`。

## 8. 前端（CIOaas-web · UmiJS + Ant Pro）

| 位置 | 内容 |
|------|------|
| 路由 | `/admin/playbooks`、`/admin/playbooks/:id/edit`、`/admin/playbooks/:id/versions` |
| 页面 | `src/pages/Playbook/List.tsx`、`Edit.tsx`、`VersionDiff.tsx` |
| 组件 | `ProTable`（列表）+ `@uiw/react-md-editor`（Markdown 编辑器）+ Diff 面板 |
| 服务层 | `src/services/api/playbook/playbookService.ts` |
| 权限 | `roleType ≤ 2`（复用现有 admin 判据，参见 `src/utils/authority.ts`） |

## 9. 数据迁移（一次性）

| 步骤 | 产出 |
|------|------|
| 1. 爬取 `goldensection.com/playbooks` 全量页面 | 原始 HTML 快照 |
| 2. `turndown` 转 markdown | `.md` 文件集合 |
| 3. 人工校对 ≥20% 抽样 | 对账 CSV |
| 4. 生成 seed SQL（ID 规约 `pbk-<slug>`） | Flyway migration `V{n}__playbook_seed.sql` |
| 5. 入库后自动 embedding | `playbook_chunk` 填充 |
| 6. 上线前跑一次 Chatbot 答案质量 A/B（50 条代表性问题） | 基线报告 |

迁移脚本位置：`CIOaas-api/gstdev-cioaas-web/src/main/resources/db/migration/V{n}__playbook_seed.sql`。

## 10. 实施阶段

| 阶段 | 工作 | 人日 | 输出 |
|------|------|:----:|------|
| S1 · 数据模型与后端骨架 | 建表 + 领域层 CRUD + 版本表 | 6 | 可通过 Postman 增删改查 |
| S2 · 向量化 | pgvector + embedding pipeline + retrieve API | 3 | 向量检索 top-k 跑通 |
| S3 · 数据迁移 | 爬取 + 清洗 + seed SQL | 3 | 全量 Playbook 入库 |
| S4 · 前端 Admin | 列表 + 编辑器 + 版本 Diff + 权限路由 | 8 | Admin 可完整增删改查 |
| S5 · QA + 文档 | 对照 PRD/TDD 自验 + 答案质量 A/B 基线 | 2 | `verify-report.md` |
| **合计** | | **22** | |

## 11. 与 AI Chatbot 其他 Story 的接口

| Chatbot 侧需要的能力 | Playbook 侧提供 |
|----------------------|-----------------|
| Layer 2 检索入口 | `POST /web/playbooks/retrieve`（向量 top-k） |
| 答案来源可追溯 | `playbook.external_url`（用于在回答末尾展示 "Reference: ..."） |
| Post-MVP：AI 写回 | `POST /web/playbooks/{id}/revision-proposal`（草稿）+ review queue |

## 12. 后续验证（不阻塞开发）

| 项 | 方法 | 窗口 |
|----|------|------|
| GEO 探针 A/B 实验 | 按 `00-research-plan.md` §4.4 跑 4 周 | 与 Story 开发并行 |
| Chatbot 答案质量基线 | 50 条代表性问题 A/B 打分 | Story 交付前一周 |

若探针结果颠覆主结论（概率 <5%），可通过在 `PlaybookService.retrieve` 外挂 `web_search` 回到 A 形态，**沉没成本可控**。

---

## 13. 立即行动（Playbook Ingestion Story 启动）

1. 触发 `/gen-requirements playbook-ingestion` → 以本文件 §5–§11 为输入产出 `01-prd.md`。
2. 触发 `/gen-tdd playbook-ingestion` → 基于本文件 §6–§9 产出 `03-technical-design.md`。
3. 触发 `/gen-impl playbook-ingestion` → 按 §10 阶段拆分成开发任务。
4. 并行启动：爬取脚本 + pgvector 扩展启用。

_本报告结束。_
