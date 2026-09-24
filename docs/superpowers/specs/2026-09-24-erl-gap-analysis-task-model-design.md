# ERL 差距分析任务化（sprint119）设计

> 关联文档：
> - ERL 设计文档（唯一权威，本设计以 v4.65 / §0.39 挂接）：[../../Exit Readiness/设计/design-doc.md](../../Exit%20Readiness/设计/design-doc.md)
> - 需求文档：[../../Exit_Readiness_PRD.md](../../Exit_Readiness_PRD.md)（§3.6 Goldie 建议；PRD:193 "所有维度两方都完成"）
> - 后端规范：[../../../java/CIOaas-api/standards/coding.md](../../../java/CIOaas-api/standards/coding.md) · Python 规范：[../../../python/CIOaas-python/standards/coding.md](../../../python/CIOaas-python/standards/coding.md)
> - 评审依据：2026-09-23/24 对用户表设计的 7 视角评审（本文件即其结论落地；原始 76 条发现不另存档）

**状态**：设计已与需求方（本仓库负责人）逐项确认（2026-09-24），待实施计划。
**分支**：`sprint119`（Java / Python / Web 三仓）。

## 0. 决策记录（2026-09-24，全部已拍板）

| # | 决定 | 取代的旧口径 |
|---|------|-------------|
| D1 | 走**全量任务化**：Java 持有"报告分享记录 + 按维度任务"的编排状态，Python 持有 AI 内容 | P3（design-doc §0.33）"产物三表归 Python、Java 无实体" |
| D2 | **Java → Python 同步 HTTP**，Python 在 refresh 响应里逐任务回状态；**不做 Python → Java 回调** | 用户初稿的"成功后回调 Java" |
| D3 | **生成门槛 = 报告级**：全部 Active 维度两端都 SUBMITTED 且无题集 mismatch 才建记录与任务 | design-doc v4.61-G1 维度级门槛（09-20） |
| D4 | **已分享记录不可变**（改动 → 新建记录，未变维度复制任务）；**未分享记录就地更新**（旧任务软删 + 新建） | V027 `shared_snapshot` JSONB 冻结 |
| D5 | 保留 Python 侧任务表，定位为**生成日志 + 幂等标记**（非状态源） | — |
| D6 | Python **每任务一次 LLM**，并发 3；不再有 index↔code 整批校验 | 一次 LLM 覆盖本轮全部维度 |
| D7 | **永久砍掉** summary / analyzedContext / model（Java 侧）/ generated_at / note / why / evidence_missing / stale / generating / analyzedAt / dimensionStale / sharedAt / sharedBy 出参；prompt 升 v1.7 | v1.6 prompt 与现契约 |
| D8 | 表名改为 `erl_gap_analysis_report`、`ai_erl_gap_analysis_task`、`ai_erl_gap_analysis_task_item`（绕开库中同名旧表与已锁定的 V024 / V026） | 用户初稿 `erl_gap_analysis` / `ai_erl_gap_analysis_dimension` |
| D9 | 报告未就绪时两端已交的维度**沿用 `Analyzing…`**，不加新态；前端六态代码不动 | — |
| D10 | 接口 18（手动 Generate）**保持同步**，只换内部链路 | — |
| D11 | 存量产物**不回填**；旧表分两批 DROP（Java 旧两表随 sprint119 脚本；Python 旧三表验证后 V029） | — |

## 1. 目标

- ERL Card 的 Gap 区块按维度展示 Goldie 建议，能区分"没分析 / 正在分析 / 已分析无差距 / 已分析有差距"，失败可自动重投。
- 分享给创始人的报告是**完整且不可变**的一份；管理端后续改动只影响新记录。
- 编排状态（谁在跑、跑完没有、依据哪批提交）在 Java 一张任务表里可查；AI 内容在 Python 表里一次写入永不改。

## 2. 术语与不变量

- **SOT**：某公司某期次某端某维度最新一次 SUBMITTED 的评估（`submitted_at DESC, id DESC`，`ErlAssessmentRepository` 现有查询）。
- **可分析维度**：两端都有 SOT 且不处于题集 mismatch（`resolveQuestionSetMismatch` 现有逻辑）。
- **报告就绪（ready）**：每个 Active 维度都是可分析维度。
- **零感知差维度**：两端 `levelScore` 相等（`ErlScoreCalculator.noPerceptionGap`），不送 LLM，直接判无差距。
- 不变量 I1：`shared = true` 的报告记录及其任务**永不修改、永不软删**。
- 不变量 I2：Python 条目表一次写入永不 UPDATE / DELETE。
- 不变量 I3：任务状态只能 `PENDING → RUNNING → SUCCESS | FAILED`，所有状态更新都是条件 UPDATE（CAS）。
- 不变量 I4：同一报告记录下同一维度至多一个未软删任务（部分唯一索引兜底）。
- 不变量 I5：同一 `(company_id, period)` 至多一条未分享记录（部分唯一索引兜底）。流程本就如此：只在最新记录不存在或已分享时新建记录，且只能分享最新记录，所以非最新记录必然已分享。

## 3. 数据模型

四张表全部无外键，跨表按 id 列关联（沿用 ERL / ai_ 表口径）。

### 3.1 Java `erl_gap_analysis_report`（报告分享记录）

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | varchar(36) PK | UUID |
| `company_id` | varchar(36) NOT NULL | |
| `period` | varchar(8) NOT NULL | `2026Q3` |
| `shared` | boolean NOT NULL DEFAULT false | 只由 Share 写 |
| `shared_at` | timestamp(6) | |
| `shared_by` | varchar(36) | |
| `created_at/by`, `updated_at/by` | 审计基类 | `created_by` 在异步线程内**显式赋值**为触发提交的用户（`@PrePersist` 不覆盖已有值） |

索引：`idx_erl_gap_analysis_report (company_id, period, created_at DESC)`；`uk_erl_gap_analysis_report_unshared (company_id, period) WHERE shared = false`（I5，Redis 规划锁 fail-open 时并发首建 / 分叉的 DB 兜底，后到事务撞键回滚）。
"最新记录"统一 `ORDER BY created_at DESC, id DESC`。

### 3.2 Java `erl_gap_analysis_dimension_task`（维度任务）

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | varchar(36) PK | |
| `erl_gap_analysis_report_id` | varchar(36) NOT NULL | |
| `dimension_code` | varchar(8) NOT NULL | |
| `source_founder_assessment_id` | varchar(36) NOT NULL | 依据的 Founder SOT |
| `source_gsv_assessment_id` | varchar(36) NOT NULL | 依据的 GSV SOT |
| `status` | varchar(16) NOT NULL | `PENDING / RUNNING / SUCCESS / FAILED`，`ErlGapAnalysisTaskStatusEnum` + `@Enumerated(STRING)`，**不加 CHECK** |
| `has_gap` | boolean | SUCCESS 时必填。零感知差由 Java 建任务时写 false；LLM 维度取 Python 响应 |
| `result_task_id` | varchar(36) | 复制任务时指向**真正持有 Python 内容**的原任务 id；自己持有内容、或无内容（零感知差 / LLM 判无差距）时为 NULL |
| `deleted` | boolean NOT NULL DEFAULT false | 未分享记录内被新任务取代的旧任务软删。命名沿用 ERL 域现有 `erl_dimension_config.deleted`（`coding.md` §8 `is_deleted` 与"Boolean 不加 is 前缀"两条互斥，取域内一致） |
| 审计四列 | | |

索引：`uk_erl_gap_analysis_dimension_task (erl_gap_analysis_report_id, dimension_code) WHERE deleted = false`（部分唯一索引，ERL 已有先例 `uk_erl_assessment_draft`）；`idx_erl_gap_analysis_dimension_task_report (erl_gap_analysis_report_id)`。
不要 `CANCELLED`（未分享记录用 `deleted` 表达取代，已分享记录不改）；不要 `@Version`（状态更新一律条件 UPDATE）。

### 3.3 Python `ai_erl_gap_analysis_task`（生成日志 + 幂等标记）

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `erl_gap_analysis_dimension_task_id` | VARCHAR(36) NOT NULL **UNIQUE** | Java 任务 id |
| `status` | VARCHAR(16) NOT NULL | `SUCCESS / FAILED`（一次 LLM 尝试的结果；重投时就地更新，是本域唯一允许 UPDATE 的 Python 表） |
| `has_gap` | BOOLEAN | SUCCESS 时 = GAP 条目数 > 0；重投命中 SUCCESS 行时据此直接回状态、不再烧 LLM |
| `model` | VARCHAR(64) | 排障 |
| `created_at/by`, `updated_at/by` | | `created_by = ctx.user_id`（三个端点已解析 `ctx`，现状未使用）；`updated_at` 触发器沿用 ai_ 表写法 |

### 3.4 Python `ai_erl_gap_analysis_task_item`（AI 条目）

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `erl_gap_analysis_dimension_task_id` | VARCHAR(36) NOT NULL | Java 任务 id（跨服务引用保留全名） |
| `item_type` | VARCHAR(16) NOT NULL | `GAP / ACTION / NARRATIVE`，不加 CHECK |
| `content` | VARCHAR(1024) NOT NULL | GAP 标题 / ACTION 动作 / NARRATIVE 整段；**note、why 不落库、不拼进 content**（前端只渲染标题） |
| `severity` | VARCHAR(8) | 仅 GAP；越界出站归一 `MEDIUM` |
| `sort_order` | INTEGER NOT NULL | NARRATIVE 恒 0；GAP / ACTION 按模型输出顺序 |
| 审计四列 | | 写后永不改（I2） |

索引：`uk_ai_erl_gap_analysis_task_item (erl_gap_analysis_dimension_task_id, item_type, sort_order)`。

## 4. 任务状态机

```
PENDING ──(派发前 CAS)──► RUNNING ──(Python 响应 SUCCESS，CAS)──► SUCCESS
                             │
                             └──(Python 响应 FAILED，CAS)──────► FAILED
自愈（管理端读接口，60s 冷却）：FAILED、或 RUNNING 且 updated_at 距今 > 10 分钟 ⇒ CAS → RUNNING，同一 task id 重新派发
```

- 所有更新 `UPDATE … WHERE id = ? AND status = ? AND deleted = false`，rowcount = 0 记 INFO 忽略（迟到结果、已软删任务自然落空）。
- HTTP 传输失败 / 读超时 **不**置 FAILED，留 RUNNING 交给 10 分钟规则：Python 可能仍在跑，立刻重投会双跑。
- 零感知差任务建行即 `SUCCESS + has_gap=false`，不经过 PENDING。
- 不加扫描器（design-doc §7.5"判断只发生在读写时刻"维持）。

## 5. 写路径：`reconcile(companyId, period, callerUserId, force)`

一个主方法按步骤平铺，三个触发点共用：

| 触发点 | 调用方式 | 说明 |
|---|---|---|
| ① 评估提交 | `ErlAssessmentServiceImpl.submit` 事务提交后 `AfterCommitExecutor` → `@Async("ioExecutor")`，`force=false` | 取代现 `regenerate`；参数带请求线程捕获的 Bearer 与 userId |
| ② 管理端读接口 17 | `stale`-等价判定前直接调 `reconcile`，Redis 冷却键 `erl:gapAnalysis:cooldown:{c}:{p}` 60s，`@Async` | 取代触发点 B；同时兜住存量已交齐期次的首次生成与并发对账 |
| ③ 接口 18 手动 Generate | 请求线程**同步**调 `reconcile(force=true)`，返回最终状态 | D10；门槛不就绪 → 400（同现状） |

`cio.erl.ai-enabled = false` 时 ① ② 整体跳过（不建行），③ 不受影响（同现状）。

步骤：

```
1  加 Java Redis 锁 erl:gapAnalysis:plan:{c}:{p}（SETNX 60s）；抢不到直接返回
2  Active 维度、每维两端 SOT、mismatch 集合 → ready；!ready ⇒ 释放锁返回（不建、不改任何行）
3  R = 最新记录；每维目标 source = (F_sot.id, G_sot.id)，zero = noPerceptionGap(F.levelScore, G.levelScore)
4  R 不存在 ⇒ 建 R + 全维任务：zero ⇒ SUCCESS/has_gap=false；否则 PENDING
5  R 已分享 ⇒ changed = source 与 R 中活任务不同、或 R 中该维活任务非 SUCCESS 的维度（force ⇒ 全部）
     —— 后一条保住 I1：分享时已停用、之后又恢复的维度若在 R 里留有未完成任务，不得在 R 上认领重跑；
     changed 为空 ⇒ 不建新记录（此时 R 中全部 Active 维度任务必为 SUCCESS，步骤 7 不会碰 R）；
     否则建 R'：changed 维建新任务（同 4）；未变维：原任务 SUCCESS ⇒ 复制
       （status/has_gap/source 照抄；有内容的任务 result_task_id = 原.result_task_id ?? 原.id，
        has_gap=false 的复制品 result_task_id 留 NULL，与 §3.2 一致）；
       原任务非 SUCCESS ⇒ 不复制，建新 PENDING（重跑，避免结果回写到旧任务而复制品永远 RUNNING）
6  R 未分享 ⇒ changed 维（force ⇒ 全部）：旧活任务 deleted=true，同 R 下建新任务（同 4）
7  待派发 = 最新记录下 status ∈ {PENDING, FAILED} ∪ {RUNNING 且超龄} 的活任务，逐个 CAS → RUNNING
8  释放锁
9  待派发非空 ⇒ 组包一次调 Python refresh ⇒ 按响应逐任务 CAS 落 status + has_gap
```

- 规划（1–8）在锁内且是一个事务；派发（9）在锁外。双端几乎同时提交各读到对方旧 SOT 的情况，由下一次读接口的 `reconcile` 对账收敛（同今天的触发点 B 机制）。
- `created_by`：记录与任务行显式 `setCreatedBy(callerUserId)`。
- 派发 payload 只含 `RUNNING` 任务；Python 对已 SUCCESS 的任务 id 直接回状态。

## 6. Java ↔ Python 契约

Java 仍**内网直连** `cio.erl.ai-base-url`，转发调用者 Bearer；Python `AuthMiddleware` 不变。读超时 refresh 500s / items 10s。

### 6.1 `POST /api/ai/erl/gap-analysis/refresh`

入参：
```
{ companyId, period,
  tasks: [ { taskId, name, abbr, weight,
             founderLevelScore, gsvLevelScore, perceptionGap,
             founderTerminatedLevel, gsvTerminatedLevel,
             questions: [ { questionText, eraBand, eraLabel, evidenceSource,
                            founderYesNo, gsvYesNo, founderNote, gsvNote,
                            attachments: [ { fileId, fileName } ] } ] } ] }
```
出参：`{ success, data: { tasks: [ { taskId, status: "SUCCESS" | "FAILED", hasGap } ] } }`

Python 流程：
1. 校验 `tasks` 非空、`taskId` 唯一（422）。
2. 附件按 `fileId` **跨任务去重**现场摘要（沿用 3 并发 / 单份 90s / 阶段总闸 120s，失败降级 `summaryAvailable=false`）。
3. 每任务：`ai_erl_gap_analysis_task` 已有 `SUCCESS` 行 ⇒ 直接回 `{SUCCESS, has_gap}`；否则一次 LLM（`Semaphore(3)`，重试 2 次同现状）→ 解析 → **一个事务**写日志行（upsert by task id）+ 条目 → 回 `SUCCESS`；LLM / 解析失败 ⇒ 日志行 `FAILED`（不写条目）→ 回 `FAILED`。单任务失败不影响其他任务。
4. `taskId` **不进 prompt**（同现状 `code` 的规则）。
5. **删除**期次级 Redis 锁 `erl:gapAnalysis:{c}:{p}`：单派发由 Java CAS 保证，双跑由条目唯一键兜底（撞键按成功处理）。

### 6.2 `POST /api/ai/erl/gap-analysis/items`

入参 `{ taskIds: [...] }`；出参 `{ items: [ { taskId, narrative, gaps: [ { title, severity } ], actions: [ { title } ] } ] }`。无条目的 taskId 不出现。

### 6.3 删除

`GET /api/ai/erl/gap-analysis`、`POST /api/ai/erl/gap-analysis/share`、`shared_snapshot` 全部逻辑、`_snapshot_is_current`、V027 存量兜底、`analyzedContext` 与 `noGapDimensions` 入参。

### 6.4 prompt v1.7（`source/ai/prompts/erl/erl_gap_analysis.md` 原地改，出参契约变化故升版）

- 输入：**单个维度**（name / abbr / weight / 两端分 / 止步 level / questions 含附件摘要），无 index、无 analyzedContext、无 summary 要求。
- 输出：`{ "narrative": "...", "gaps": [ { "title", "severity" } ], "actions": [ { "title" } ] }`；无差距时 `gaps` 为空且不输出 narrative（同现状规则）。
- `has_gap = len(gaps) > 0`。

## 7. 读路径与出参

### 7.1 选行（只此一处 `visibleReport`）

- 管理端：`latestReport(company, period)`。
- 公司端：`latestSharedReport(company, period)`；无 ⇒ `shared=false` 空态（前端渲染 `No gap analysis shared yet.`，不变）。

### 7.2 接口 17 出参

期次级：`shared`（管理端 = 最新记录.shared；公司端 = 有已分享记录）、`shareable`（仅管理端，见 7.4）、`analysisServiceUnavailable`（= 向 Python 取条目失败；没有条目可取时恒 false）。
删除：`summary / generatedAt / model / stale / generating / sharedAt / sharedBy`。

维度级（管理端遍历当前 Active 维度；公司端只遍历分享记录里的 SUCCESS 任务——非 SUCCESS 的只可能属于分享前已停用的维度、不是这份报告的一部分——同时消掉"分享后新增维度"的假阴性）：

| 字段 | 来源 |
|---|---|
| `dimensionCode / dimensionAbbr` | 维度配置（公司端取任务行对应维度；停用维度按快照名） |
| `bothSubmitted / questionSetMismatch / mismatchSide` | Java 现算（同今天；公司端不冻结，已接受） |
| `analyzed` | 该维活任务存在且 `status = SUCCESS` |
| `hasGap` | 任务列 `has_gap`（`analyzed=false` 时下发 false） |
| `narrative / gaps[].title,severity / actions[].title` | 按 `result_task_id ?? id` 一次批量取 Python；`has_gap=false` 的任务不取 |
| `dimensionStale` | **恒 false**（字段保留一版供前端兼容，六态 `Updating…` 不再可达） |
| 删除 | `analyzedAt`、`gaps[].note / evidenceMissing`、`actions[].why` |

D9：报告未就绪时，两端已交的维度 `analyzed=false` ⇒ 前端 `Analyzing…`（接受空轮询 125s 后提示刷新）。

### 7.3 接口 1（卡片）/ 接口 21（维度详情）

- 接口 1：`shared / shareable / dimensions[].hasGap` 全部来自 Java 表，**不调 Python**（顺手消掉 JAVA-TODO:211 的口径分叉）。
- 接口 21：只取该维一个任务的条目。

### 7.4 Share（接口 27）

`isShareable` = ready ∧ 最新记录存在 ∧ 未分享 ∧ 全部活任务 `SUCCESS` ∧ 每维任务 source == 当前 SOT。
流程：`SELECT … FOR UPDATE` 最新记录 → 校验 → 置 `shared / shared_at / shared_by`。前端请求体不变（不带 analysisId）；管理员点击与后台新建记录之间的窄竞态 ⇒ 400 "Content updated, please refresh"，接受。

## 8. 并发、幂等、自愈汇总

| 场景 | 处理 |
|---|---|
| 同期次两次 `reconcile` 并发 | Java 规划锁 60s；抢不到的直接返回，下次读再来。锁 fail-open（Redis 不可用）时由 `uk_erl_gap_analysis_report_unshared`（首建 / 分叉）与 `uk_erl_gap_analysis_dimension_task`（同记录同维度）兜底，后到事务回滚 |
| 双端交错提交各读到旧 SOT | 建出 `(F1,G0)` 任务；下次管理端读 ⇒ source ≠ SOT ⇒ 未分享则软删重建 / 已分享则新记录 |
| Java 500s 超时、Python 仍在跑 | 任务留 RUNNING；10 分钟后重投 ⇒ Python 命中 SUCCESS 日志直接回，不重复烧 LLM |
| Python 崩溃 | 日志行无 / FAILED ⇒ 10 分钟后重投 |
| Java 发版重启、派发线程被杀 | 同上 |
| 迟到响应撞已软删 / 已终态任务 | CAS rowcount 0，忽略 |
| 同一 task 被双跑 | 日志行 / 条目撞唯一键 ⇒ rollback 重查日志行：先到者 SUCCESS ⇒ 按它的 has_gap 返回；先到者 FAILED ⇒ 重试写入一次，把 FAILED 覆盖为 SUCCESS；查不到行 ⇒ 真异常记 FAILED |
| 已分享记录后又提交 | 新记录；创始人继续读旧已分享记录（I1） |

## 9. 迁移与部署

### 9.1 脚本

- Python `sql/migrations/business/V028__sprint119_erl_gap_analysis_task.sql`：建 `ai_erl_gap_analysis_task`、`ai_erl_gap_analysis_task_item` + 索引 + `updated_at` 触发器 + 英文 COMMENT；头注写明**部署项：GRANT SELECT/INSERT/UPDATE/DELETE 给 Python DB role**（历次必漏项）。
- Python `V029`（功能验证通过后单独出）：DROP `ai_erl_gap_analysis_item`、`ai_erl_gap_analysis_dimension`、`ai_erl_gap_analysis`（含三个触发器）。
- Java `deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql`（人工执行）：`DROP TABLE IF EXISTS erl_gap_analysis_item, erl_gap_analysis`（P3 欠账）→ 建两张新表 + 索引（含部分唯一索引，ddl-auto 建不出）。
- Java `deploy/upgrade_doc/sprint118/V1__erl_init.sql`：去掉旧两表 §5.7/5.8 与索引 `uk_erl_gap_analysis / idx_erl_gap_item`（全新库不再建死表）；README 表数与清单改口，注明新表在 sprint119。

### 9.2 顺序（缺一不可，回滚三侧一起）

V028（含 GRANT）→ Java sprint119 脚本 → `cio.erl.ai-enabled=false` → Python 发版 → Java **一次性全量替换** → Web → 开开关 → 验证 → V029。
中间态说明：新 Java + 旧 Python ⇒ refresh 422，任务留 PENDING/RUNNING，开关打开后由自愈重投；旧 Java + 新 Python ⇒ 旧 GET 404 ⇒ `analysisServiceUnavailable`，故 Java 必须全量替换而非滚动。

### 9.3 同批清理

- Java：Redis 期次级冷却键逻辑改挂到 `reconcile`；`ErlGapAnalysisResultDTO`、`ErlGapAnalysisRequestDTO` 重写；过时 Javadoc 4 处（`ErlGapAnalysisService.java:483-486`"Python 落库复位分享位"、`ErlDimensionConverter.java:24`、`ErlActionItemResponse.java:13`、`ErlDimensionConfig.java:57`）。
- Python：`gap_analysis_lock.py` 删除；`erl_gap_analysis_service.py` 落库 / 读取 / share / 快照相关全部重写；旧三个 ORM 与仓储随 V029 删除。
- 文档：design-doc v4.65 + §0.39（本次）；PRD:193 "分享后 founder 端置空"回写为冻结口径；根 `CLAUDE.md` ERL 段"Python 不落 ERL 业务表 / 一次 LLM 调用产出一份分析"改口；sprint118 README；`CIOaas-python/CLAUDE.md` ERL 段；台账 PY-TODO:123 / 126 / 127 / 132、JAVA-TODO:5（部分：接口 18 仍同步，保留）/ 211 / 213 / 215 / 216 了结或改口。

## 10. 测试策略

- Java：`reconcile` 规划逻辑单测（首建 / 已分享复制 / 未分享软删 / force / 超龄重投 / 双端交错 / ready=false 不建行 / 零感知差直建 SUCCESS）；仓储（最新行排序、部分唯一索引冲突、CAS 更新 rowcount）；`ErlPythonClient` 新契约；接口 1 / 17 / 21 / 27 拼装（管理端 vs 公司端选行、`analysisServiceUnavailable`、`isShareable` 五条）。
- Python：单任务 LLM 流程与并发、SUCCESS 日志短路、FAILED 日志、条目唯一键撞键按成功、items 端点分组、prompt v1.7 结构回归、Request VO 422 边界、V028 幂等重跑。
- Web：无必需改动；若同批清理死字段，`erlService` 单测同步。
- E2E（按记忆规则先审核再跑，只挑 2–3 个代表场景）：首次交齐生成 → Share → 一端改一维重交 → 管理端见新记录、创始人仍见旧报告 → 再 Share。

## 11. 明确不做 / 已知代价

- 不做真正的任务取消（LLM 请求不可中止）；不做扫描器；不做 Python → Java 回调；不做前端 `failed` 态（FAILED 自动重投，屏上仍是 `Analyzing…`）。
- 报告级门槛下，部分维度已交齐时屏上显示 `Analyzing…` 并空轮询 125s（D9，需求方接受）。
- 接口 18 仍同步等待，网关 120s 先超时的既有问题保留（D10，JAVA-TODO:5 继续挂账）。
- 未分享记录内被软删任务的 Python 条目成为孤儿行，留待后续清理任务处理。
- 公司端 `questionSetMismatch / bothSubmitted` 不冻结（沿用 09-21 接受的口径）。
- 零感知差与 LLM 判无差距在屏上同为 `No Gap`（JAVA-TODO:214 已接受）。
