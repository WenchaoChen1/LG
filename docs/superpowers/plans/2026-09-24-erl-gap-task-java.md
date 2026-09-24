# ERL 差距分析任务化 — Java 侧实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 ERL 差距分析从「Python 独占产物 + Java 指纹现算」改成「Java 持有报告记录与维度任务（编排状态、分享、CAS 状态机），Python 每任务一次 LLM 并只持有 AI 内容」，三个触发点共用一个平铺的 `reconcile`。

**Architecture:** Java 新增两张表 `erl_gap_analysis_report`（报告分享记录，已分享即不可变）与 `erl_gap_analysis_dimension_task`（每维一个任务，`PENDING → RUNNING → SUCCESS | FAILED`，全部条件 UPDATE）。写路径 `reconcile(companyId, period, callerUserId, bearerToken, force)`：Redis 规划锁 → 一个 `REQUIRED` 事务内建记录 / 复制 / 软删重建 + CAS 认领 → 锁外一次同步 HTTP `refresh` → 按响应逐任务 CAS 落状态。读路径只在 `visibleReport` 一处选行（管理端最新记录 / 公司端最新已分享记录），条目按 `result_task_id ?? id` 一次批量 `POST /items` 取；接口 1 完全不调 Python。Java 仍内网直连 `cio.erl.ai-base-url` 并转发调用者 Bearer。

**Tech Stack:** Java 17 / Spring Boot 3.3 / Spring Data JPA (Hibernate 6) / Hutool HttpRequest / Redis (StringRedisTemplate) / JUnit 5 + Mockito + AssertJ

**依赖/顺序：** Python 计划（契约提供方：`POST /api/ai/erl/gap-analysis/refresh` 新入出参、`POST /api/ai/erl/gap-analysis/items`、V028）先实施；部署顺序见设计稿 §9.2：V028（含 GRANT）→ Java sprint119 脚本 → `cio.erl.ai-enabled=false` → Python 发版 → Java **一次性全量替换** → Web → 开开关 → 验证 → V029。

**设计稿（唯一权威）：** `docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md`。本计划里凡与设计稿冲突处以设计稿为准。

**仓库 / 分支：** `D:/workspace/github/LG/java/CIOaas-api`，分支 `sprint119`。ERL 代码根：`gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/erl/`（下文以 `erl/` 指代），测试根：`gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/erl/`（下文以 `test/erl/` 指代）。

**编译校验约定：** Task 4 ~ Task 9 是一个编译单元（DTO / 客户端 / VO / 服务 / 消费方相互引用），中间任务跑 `mvn -q -pl gstdev-cioaas-web -am compile -DskipTests` **允许**报错，但报错文件必须只落在「尚未执行的后续任务将要改写的文件」内；Task 9 结束时必须全绿。测试代码在 Task 10 ~ 11 写完后以 `test-compile` 收口，**任何任务都不运行测试**（项目规则：开发中不自动跑测试）。

---

## 文件结构

### 新增

| 文件 | 职责 |
|---|---|
| `deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql` | DROP 旧两表；建 `erl_gap_analysis_report` / `erl_gap_analysis_dimension_task` + 3 个索引（含部分唯一索引）+ 英文 COMMENT |
| `deploy/upgrade_doc/sprint119/README.md` | 执行顺序（Python V028 先）、执行方式、回滚说明 |
| `erl/enums/ErlGapAnalysisTaskStatusEnum.java` | `PENDING / RUNNING / SUCCESS / FAILED` + Python 响应 status 字符串解析 |
| `erl/enums/ErlGapAnalysisReconcileOutcomeEnum.java` | `reconcile` 的收手成因：`NOT_SUBMITTED / MISMATCHED / LOCK_BUSY / DONE`（接口 18 据此挑 400 文案） |
| `erl/entity/ErlGapAnalysisReport.java` | 报告分享记录实体（设计稿 §3.1） |
| `erl/entity/ErlGapAnalysisDimensionTask.java` | 维度任务实体（设计稿 §3.2） |
| `erl/repository/ErlGapAnalysisReportRepository.java` | 最新记录 / 最新已分享记录 / `FOR UPDATE` 最新记录 |
| `erl/repository/ErlGapAnalysisDimensionTaskRepository.java` | 活任务查询、CAS 状态更新、批量软删 |
| `erl/dto/ErlGapItemsResultDTO.java` | `POST /items` 出参 `{items:[{taskId, narrative, gaps[], actions[]}]}` |
| `erl/dto/ErlGapAnalysisReportDTO.java` | 域内读形态：可见记录 + 活任务（接口 1 / 27 / 17 共用，不含 Python 内容） |
| `erl/dto/ErlGapAnalysisShareDTO.java` | 接口 27 出参载体 `{shared, sharedAt, sharedBy}` |
| `erl/dto/ErlGapAnalysisPlanDTO.java` | `plan` 的返回：收手成因 + 待派发的 refresh 入参（无任务可派时为 null） |

### 修改

| 文件 | 改动 |
|---|---|
| `deploy/upgrade_doc/sprint118/V1__erl_init.sql` | 删 §5.7 / §5.8 两段建表（约 :478-538）与 `uk_erl_gap_analysis` / `idx_erl_gap_item`（约 :637-643）；头注 :24「11 张」→「9 张」；:303 COMMENT 里的表名改口 |
| `deploy/upgrade_doc/sprint118/README.md` | 表数 / 清单 / 「差距分析两张新表在 sprint119」/ Python 侧表名改口 |
| `erl/enums/ErlGapItemTypeEnum.java` | 删 `NARRATIVE`（Java 侧无任何引用；Python 表的 `item_type = NARRATIVE` 是它自己的取值），Javadoc 改口 |
| `erl/dto/ErlGapAnalysisRequestDTO.java` | 重写为 `{companyId, period, tasks[]}`：删 `organizationId` / `dimensions` / `noGapDimensions` / `analyzedContext` / `Dimension.index` / `code` / `submissionSignature` |
| `erl/dto/ErlGapAnalysisResultDTO.java` | 重写为 `{tasks:[{taskId, status, hasGap}]}` |
| `erl/dto/ErlGapAnalysisDTO.java` | 只剩 `dimensions / analysisServiceUnavailable / shared / shareable` |
| `erl/dto/ErlGapDimensionDTO.java` | 删 `analyzedAt`；`dimensionStale` 保留（恒 false） |
| `erl/dto/ErlGapItemDTO.java` | 删 `note` / `evidenceMissing` |
| `erl/dto/ErlCardDTO.java` | 删 `gapSummary`（`summary` 已永久砍掉，D7） |
| `erl/vo/response/ErlGapAnalysisResponse.java` | 删 `summary / generatedAt / model / stale / generating / sharedAt / sharedBy` |
| `erl/vo/response/ErlGapAnalysisDimensionResponse.java` | 删 `analyzedAt` |
| `erl/vo/response/ErlGapItemResponse.java` | 删 `note / evidenceMissing` |
| `erl/vo/response/ErlActionItemResponse.java` | 删 `why`，Javadoc 改口（过时 Javadoc 4 处之一） |
| `erl/vo/response/ErlCardResponse.java` | 删 `gapSummary` |
| `erl/converter/ErlGapAnalysisConverter.java` | 删 `why ← note` 映射；`toShareResponse` 改吃 `ErlGapAnalysisShareDTO`；`toResponse` 删死字段 |
| `erl/converter/ErlDimensionConverter.java` | 删 :22-24 那段 `erl_gap_analysis_item.note` Javadoc 与 `@Mapping(target = "why", source = "note")`（过时 Javadoc 4 处之一） |
| `erl/client/ErlPythonClient.java` | 重写：`refresh(ErlGapAnalysisRequestDTO, token)` / `fetchItems(List<String>, token)`；删 `getGapAnalysis` / `shareGapAnalysis` / 时间解析 |
| `erl/service/ErlGapAnalysisService.java` | 接口重写：`find / generate / share / reconcileAsync / reconcile / plan / applyResults / loadResult / loadItems / resolveQuestionSetMismatch / isShareable`（过时 Javadoc「Python 落库复位分享位」随之消失） |
| `erl/service/ErlGapAnalysisServiceImpl.java` | **原文件内**重写（约 1462 行 → 约 900 行）：删指纹 / `isStale` / `outdatedDimensions` 指纹比对 / `analyzedContext` / `noPerceptionGapDimensions` / `visibleArtifact`；新增 `reconcile` 九步平铺 |
| `erl/service/ErlAssessmentServiceImpl.java` | :299-300 与 :893-909：`regenerateGapAnalysisAfterCommit` → `reconcileGapAnalysisAfterCommit`，多传 `callerUserId`，改调 `reconcileAsync` |
| `erl/service/ErlCardServiceImpl.java` | :101-152 `getCard` 与 :178-235 `buildDimensions` 改走 `loadResult(companyId, period, adminEnd)`；删 `gapDimensions` / `truncatedSummary` / `normalizeCode` / `GAP_SUMMARY_MAX_LENGTH`（:351-392） |
| `erl/service/ErlDimensionServiceImpl.java` | :122-144 `getDetail` 改走 `loadItems`；删 `loadGapDimension` / `normalizeCode` / `gapItems` / `actionItems`（:480-561） |
| `erl/controller/ErlGapAnalysisController.java` | 仅 Javadoc（:65-70 的 `is_latest` 门槛描述改口）；代码不变 |
| `erl/entity/ErlDimensionConfig.java` | :57 Javadoc 五表清单里的 `erl_gap_analysis_item` → `erl_gap_analysis_dimension_task`（过时 Javadoc 4 处之一） |
| `test/erl/service/ErlGapAnalysisServiceImplTest.java` | 重写 |
| `test/erl/client/ErlPythonClientTest.java` | 重写 |
| `test/erl/service/ErlCardServiceImplTest.java` | 差距分析段（:270-385、:437-450）重写；setUp 与 `givenSubmitted` 改桩 |
| `test/erl/service/ErlDimensionServiceImplTest.java` | 差距分析段（:342-447）重写；setUp 改桩 |
| `test/erl/service/ErlAssessmentServiceImplTest.java` | :379 一行 `verify` 改口 |
| `docs/待优化项.md` / `docs/已完成优化.md` | :5 保留改口、:211 / :213 / :215 / :216 / :218 了结或改口（**需用户确认后再改**） |
| `D:/workspace/github/LG/docs/Exit Readiness/设计/design-doc.md` | §5.8 / §6.6 / §7.5 正文按设计稿回写 |
| `D:/workspace/github/LG/CLAUDE.md` | ERL 段两句改口 |

### 删除

无整文件删除（旧表随 sprint119 脚本 DROP；Java 侧本就没有旧表实体）。

---

## 跨仓契约假定（写进代码的部分，供与 Python 计划核对）

| 项 | 本计划假定 |
|---|---|
| refresh 路径 / 方法 | `POST {cio.erl.ai-base-url}/api/ai/erl/gap-analysis/refresh`，`Content-Type: application/json`，`Authorization` 原样转发调用者 Bearer |
| refresh 入参 | `{companyId, period, tasks:[{taskId, name, abbr, weight, founderLevelScore, gsvLevelScore, perceptionGap, founderTerminatedLevel, gsvTerminatedLevel, questions:[{questionText, eraBand, eraLabel, evidenceSource, founderYesNo, gsvYesNo, founderNote, gsvNote, attachments:[{fileId, fileName}]}]}]}`；Hutool `JSONUtil.toJsonStr` **省略 null 值键**（与现状一致），`attachments` 恒为数组（可空数组） |
| refresh 出参 | 信封 `{success, code, message, data}`，`data = {tasks:[{taskId, status: "SUCCESS"\|"FAILED", hasGap}]}`；`hasGap` 只在 SUCCESS 时有意义，缺席按 false；`status` 其它取值 Java 一律按 FAILED |
| items 路径 | `POST {cio.erl.ai-base-url}/api/ai/erl/gap-analysis/items`，入参 `{taskIds:[...]}`，出参 `data = {items:[{taskId, narrative, gaps:[{title, severity}], actions:[{title}]}]}`；无条目的 taskId 不出现；`gaps` / `actions` 缺席按空数组 |
| HTTP 状态 | 2xx 即成功；非 2xx（含 401 / 422）与 `success=false` 均抛 `ServiceException`（refresh 时任务留 RUNNING、items 时出参 `analysisServiceUnavailable=true`） |
| 时间格式 | 契约里**没有时间字段**（`generatedAt / analyzedAt / sharedAt` 全部删除），故 `ErlPythonClient` 不再解析任何时间戳 |
| 读超时 | refresh 500 000 ms、items 10 000 ms、连接 5 000 ms |
| 已删端点 | `GET /api/ai/erl/gap-analysis`、`POST /api/ai/erl/gap-analysis/share`（Java 不再调用） |

---

### Task 1: 升级脚本（sprint119 新建 + sprint118 改口）

**Files:**
- Create: `deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql`
- Create: `deploy/upgrade_doc/sprint119/README.md`
- Modify: `deploy/upgrade_doc/sprint118/V1__erl_init.sql:24,167,303,478-538,637-643`
- Modify: `deploy/upgrade_doc/sprint118/README.md:15,49-51`

- [ ] **Step 1: 新建 `deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql`**

```sql
-- =========================================================================
-- Exit Readiness Level（ERL）差距分析任务化（sprint119, V2）
--
--   依据：docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md §3.1 / §3.2 / §9.1
--   范围：① DROP 旧两表 erl_gap_analysis_item / erl_gap_analysis（P3 欠账，设计稿 D11；
--           索引 uk_erl_gap_analysis / idx_erl_gap_item 随表消失）
--         ② 建 erl_gap_analysis_report / erl_gap_analysis_dimension_task
--         ③ 3 个索引（含 1 个部分唯一索引 —— ddl-auto=update 建不出来）
--
--   ⚠ 人工执行、单事务（见同目录 README.md）；⚠ 先跑 Python V028（含 GRANT）再跑本文件；
--   ⚠ 必须先于 sprint119 Java 代码发版：ddl-auto=update 会自己建表，但建不出部分唯一索引，
--     会留下「同一记录同一维度可以有两个活任务」的库（不变量 I4 失守）。
--   ⚠ DROP 不可逆：存量产物不回填（D11）；Python 侧 ai_erl_gap_analysis* 旧三表由 Python V029 另行处理。
--   幂等：DROP IF EXISTS / CREATE IF NOT EXISTS，可重跑。
-- =========================================================================

-- ---- ① 旧表 ------------------------------------------------------------
DROP TABLE IF EXISTS erl_gap_analysis_item;
DROP TABLE IF EXISTS erl_gap_analysis;

-- ---- ② 报告分享记录（设计稿 §3.1）-----------------------------------------
CREATE TABLE IF NOT EXISTS erl_gap_analysis_report (
  id          varchar(36) NOT NULL,
  company_id  varchar(36) NOT NULL,
  period      varchar(8)  NOT NULL,
  shared      boolean     NOT NULL DEFAULT false,
  shared_at   timestamp(6),
  shared_by   varchar(36),
  created_at  timestamp(6),
  created_by  varchar(36),
  updated_at  timestamp(6),
  updated_by  varchar(36),
  CONSTRAINT pk_erl_gap_analysis_report PRIMARY KEY (id)
);

COMMENT ON TABLE erl_gap_analysis_report IS
  'One gap-analysis REPORT RECORD per generation batch of a (company_id, period) -- there can be many rows per period. The LATEST row (ORDER BY created_at DESC, id DESC) is what the admin portal reads; the latest row WITH shared = true is what the company (founder) portal reads. A shared row and its tasks are IMMUTABLE (invariant I1): any later change creates a NEW row and copies the unchanged tasks; an UNSHARED row is updated in place (old tasks soft-deleted, new ones inserted). Replaces erl_gap_analysis (dropped by this script); the AI content itself lives on the Python side (ai_erl_gap_analysis_task_item) keyed by task id';
COMMENT ON COLUMN erl_gap_analysis_report.shared IS
  'Written ONLY by interface 27 POST /erl/gapAnalysis/share (admin only) under SELECT ... FOR UPDATE of the latest row. Never reset: regeneration creates a new row instead';
COMMENT ON COLUMN erl_gap_analysis_report.shared_at IS 'Share timestamp; only set while shared = true';
COMMENT ON COLUMN erl_gap_analysis_report.shared_by IS 'User id that shared it';
COMMENT ON COLUMN erl_gap_analysis_report.created_by IS
  'The user whose submission / click triggered this record. Set EXPLICITLY by the service (the async thread has no security context and the audit base class keeps a pre-set value)';

-- ---- ③ 维度任务（设计稿 §3.2）--------------------------------------------
CREATE TABLE IF NOT EXISTS erl_gap_analysis_dimension_task (
  id                           varchar(36) NOT NULL,
  erl_gap_analysis_report_id   varchar(36) NOT NULL,
  dimension_code               varchar(8)  NOT NULL,
  source_founder_assessment_id varchar(36) NOT NULL,
  source_gsv_assessment_id     varchar(36) NOT NULL,
  status                       varchar(16) NOT NULL,
  has_gap                      boolean,
  result_task_id               varchar(36),
  deleted                      boolean     NOT NULL DEFAULT false,
  created_at                   timestamp(6),
  created_by                   varchar(36),
  updated_at                   timestamp(6),
  updated_by                   varchar(36),
  CONSTRAINT pk_erl_gap_analysis_dimension_task PRIMARY KEY (id)
);

COMMENT ON TABLE erl_gap_analysis_dimension_task IS
  'One task per (report record, active dimension). Holds the ORCHESTRATION state only (status, has_gap, which submissions it was built on); the narrative / gaps / actions are on the Python side, keyed by result_task_id ?? id. No foreign keys, like every other erl_* / ai_* table';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.erl_gap_analysis_report_id IS 'erl_gap_analysis_report.id';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.dimension_code IS 'erl_dimension_config.dimension_code';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.source_founder_assessment_id IS
  'erl_assessment.id of the FOUNDER source of truth (latest SUBMITTED row of that dimension) this task was built on. Compared with the current SOT to decide whether the task is outdated -- replaces the sha256 fingerprint of the previous model';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.source_gsv_assessment_id IS 'Same for the GSV side';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.status IS
  'PENDING / RUNNING / SUCCESS / FAILED (ErlGapAnalysisTaskStatusEnum, @Enumerated(STRING)). NO CHECK constraint on purpose. Every transition is a conditional UPDATE ... WHERE id = ? AND status = ? AND deleted = false (invariant I3). Self-healing: FAILED, or RUNNING with updated_at older than 10 minutes, is re-claimed to RUNNING and re-dispatched under the same id. A dimension whose two sides score the same is inserted directly as SUCCESS + has_gap = false and never goes through PENDING';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.has_gap IS
  'Required once status = SUCCESS. Zero-perception-gap dimensions: written false by Java when the task is created; LLM dimensions: taken from the Python refresh response';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.result_task_id IS
  'When a task is COPIED into a new record (unchanged dimension of a shared record) this points at the ORIGINAL task that actually owns the Python content (copies chain back to the root: copy.result_task_id = original.result_task_id ?? original.id). NULL when the task owns its own content or has none';
COMMENT ON COLUMN erl_gap_analysis_dimension_task.deleted IS
  'Soft delete, ONLY used inside an UNSHARED record when a dimension is rebuilt (the old task is superseded by a new one). Tasks of a SHARED record are never soft-deleted (invariant I1). Column name follows erl_dimension_config.deleted';

-- ---- ④ 索引 ------------------------------------------------------------
-- 「最新记录」的主路径：ORDER BY created_at DESC, id DESC
CREATE INDEX IF NOT EXISTS idx_erl_gap_analysis_report
  ON erl_gap_analysis_report (company_id, period, created_at DESC);

-- 部分唯一索引：同一记录下同一维度至多一个未软删任务（不变量 I4；先例 uk_erl_assessment_draft）
CREATE UNIQUE INDEX IF NOT EXISTS uk_erl_gap_analysis_dimension_task
  ON erl_gap_analysis_dimension_task (erl_gap_analysis_report_id, dimension_code)
  WHERE deleted = false;

CREATE INDEX IF NOT EXISTS idx_erl_gap_analysis_dimension_task_report
  ON erl_gap_analysis_dimension_task (erl_gap_analysis_report_id);

-- 核验（人工，只读）：
--   SELECT tablename, indexname FROM pg_indexes
--    WHERE tablename IN ('erl_gap_analysis_report', 'erl_gap_analysis_dimension_task') ORDER BY 1, 2;
--   期望 5 行：两个 pk_ + idx_erl_gap_analysis_report + uk_erl_gap_analysis_dimension_task
--            + idx_erl_gap_analysis_dimension_task_report
--   SELECT to_regclass('erl_gap_analysis'), to_regclass('erl_gap_analysis_item');  -- 期望两个 NULL
```

- [ ] **Step 2: 新建 `deploy/upgrade_doc/sprint119/README.md`**

```markdown
# sprint119 数据库脚本（ERL 差距分析任务化）

本仓库没有 Flyway / Liquibase，脚本**人工执行**。本目录只有一份脚本，**全部环境**（全新库与存量库）都要跑。

| 脚本 | 内容 | 说明 |
|------|------|------|
| `V2__erl_gap_analysis_report.sql` | `DROP` 旧表 `erl_gap_analysis_item` / `erl_gap_analysis`；建 `erl_gap_analysis_report`、`erl_gap_analysis_dimension_task` + 3 个索引（含部分唯一索引 `uk_erl_gap_analysis_dimension_task ... WHERE deleted = false`）+ 英文 COMMENT | 设计稿 `docs/superpowers/specs/2026-09-24-erl-gap-analysis-task-model-design.md` §3.1 / §3.2 / §9.1。**DROP 不可逆，存量产物不回填**（D11） |

## 执行顺序（缺一不可，回滚三侧一起 —— 设计稿 §9.2）

1. **Python `V028__sprint119_erl_gap_analysis_task.sql`**（含给 Python DB role 的 GRANT）—— 由 CIOaas-python 的 `scripts/migrate.py` 或人工执行，**先于本脚本**
2. 本目录 `V2__erl_gap_analysis_report.sql`
3. Nacos 置 `cio.erl.ai-enabled=false` → Python 发版 → Java **一次性全量替换（不要滚动）** → Web → 开开关 → 验证
4. Python `V029`（DROP 旧 `ai_erl_gap_analysis*` 三表）在功能验证通过后单独执行

中间态：新 Java + 旧 Python ⇒ refresh 422，任务留 PENDING / RUNNING，开关打开后由自愈重投；旧 Java + 新 Python ⇒ 旧 `GET /gap-analysis` 404 ⇒ 页面 `analysisServiceUnavailable`。所以 Java 必须全量替换。

## 执行方式（强制）

```bash
psql -v ON_ERROR_STOP=1 --single-transaction -h <host> -U <user> -d <db> -f V2__erl_gap_analysis_report.sql
```

- `-v ON_ERROR_STOP=1`：psql 默认遇错继续，开启后第一处报错即停。
- `--single-transaction`：整份脚本一个事务，中途失败整份回滚（DROP 也一起回滚）。
- **不要用 DBeaver / pgAdmin 的「执行脚本」**：它们通常逐句继续、报错不停。

## 与 sprint118 的关系

`sprint118/V1__erl_init.sql` 自本 sprint 起**不再**建 `erl_gap_analysis` / `erl_gap_analysis_item`（全新库不建死表）；全新库按 `sprint118/V1 → sprint118/V4 → sprint119/V2` 的顺序执行即得到完整 11 张 `erl_*` 表。
```

- [ ] **Step 3: 修改 `deploy/upgrade_doc/sprint118/V1__erl_init.sql` —— 删两段建表与两个索引**

删除从 `-- ---- 5.7 Goldie 差距分析 ----` 那行（约 :478）起、到 `COMMENT ON COLUMN erl_gap_analysis_item.evidence_missing IS ... ';` 语句结束（约 :538）为止的整段（含 §5.7 的 `CREATE TABLE erl_gap_analysis` / 全部 COMMENT 与 §5.8 的 `CREATE TABLE erl_gap_analysis_item` / 全部 COMMENT），在原位置留下一段说明：

```sql
-- ---- 5.7 / 5.8 Goldie 差距分析（已移出本文件）-----------------------------
--   2026-09-24（sprint119，差距分析任务化）：erl_gap_analysis / erl_gap_analysis_item 两张表
--   **不再由本文件创建**（全新库不建死表）。取代它们的 erl_gap_analysis_report /
--   erl_gap_analysis_dimension_task 在 deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql，
--   该脚本对存量库同时负责 DROP 旧两表。
```

再删除 §② 索引段里的这 6 行（约 :637-643）：

```sql
-- 差距分析
-- **v4.4 / D3**：唯一约束回 (company_id, period) —— audience 列已删除，单份产物
CREATE UNIQUE INDEX IF NOT EXISTS uk_erl_gap_analysis
  ON erl_gap_analysis (company_id, period);
CREATE INDEX IF NOT EXISTS idx_erl_gap_item
  ON erl_gap_analysis_item (analysis_id, dimension_code, item_type, sort_order);
```

- [ ] **Step 4: 修改 `deploy/upgrade_doc/sprint118/V1__erl_init.sql` —— 头注三处改口**

:24 的
```
--   范围：**11 张** erl_* 表 —— 建表 + 索引 + 唯一约束 + **两个**部分唯一索引
```
改为
```
--   范围：**9 张** erl_* 表 —— 建表 + 索引 + 唯一约束 + **两个**部分唯一索引
--         （差距分析两张表 erl_gap_analysis_report / erl_gap_analysis_dimension_task
--          自 2026-09-24 起在 deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql）
```

:167 历史沿革那行末尾追加一句（保持同段缩进）：
```
--          erl_gap_analysis − audience + shared/shared_at/shared_by、item_type 收敛为 GAP / ACTION
--          （**2026-09-24 两表整体移出本文件**，见 5.7 / 5.8 处说明）；
```

:303 `COMMENT ON COLUMN erl_dimension_config.dimension_code` 里的 `erl_gap_analysis_item.dimension_code` 改为 `erl_gap_analysis_dimension_task.dimension_code`（其余原文不动）。

- [ ] **Step 5: 修改 `deploy/upgrade_doc/sprint118/README.md`**

:15 表格首行的
```
| `V1__erl_init.sql` | ERL 全部 11 张 `erl_*` 表 + 索引 / 唯一约束（含部分唯一索引）+ 表/列注释 | 已是最终模型。**不含任何初始化数据**：题库版本、维度配置、题目由业务侧录入 |
```
改为
```
| `V1__erl_init.sql` | ERL 9 张 `erl_*` 表 + 索引 / 唯一约束（含部分唯一索引）+ 表/列注释（**不含**差距分析两张表，见下） | 已是最终模型。**不含任何初始化数据**：题库版本、维度配置、题目由业务侧录入。差距分析的 `erl_gap_analysis_report` / `erl_gap_analysis_dimension_task` 在 `../sprint119/V2__erl_gap_analysis_report.sql`（2026-09-24 起旧的 `erl_gap_analysis*` 两表不再由 V1 创建） |
```

「执行顺序」第 1 条末尾追加：`；全新库随后再跑 ../sprint119/V2__erl_gap_analysis_report.sql 才有差距分析两张表`。

:49-51「不在本目录的表」一节改为：
```markdown
## 不在本目录的表

- 差距分析的 Java 表 `erl_gap_analysis_report` / `erl_gap_analysis_dimension_task`：`../sprint119/V2__erl_gap_analysis_report.sql`。
- Python 侧 ERL 表（`ai_erl_gap_analysis_task`、`ai_erl_gap_analysis_task_item`；旧的 `ai_erl_gap_analysis*` 三表待 V029 删除）不在这里，由 CIOaas-python 的 `sql/migrations/business/` 经 `scripts/migrate.py` 执行。
```

- [ ] **Step 6: 轻量校验**

```bash
grep -n "erl_gap_analysis" deploy/upgrade_doc/sprint118/V1__erl_init.sql
```
期望：只剩 :24 附近、5.7/5.8 处说明、:167、:303 四处**注释**命中，无 `CREATE TABLE` / `CREATE ... INDEX` 命中。再确认 sprint119 脚本能被 psql 解析（不连库）：
```bash
psql --version && grep -c "CREATE TABLE IF NOT EXISTS" deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql
```
期望输出 `2`。

---

### Task 2: 枚举与实体

**Files:**
- Create: `erl/enums/ErlGapAnalysisTaskStatusEnum.java`
- Create: `erl/enums/ErlGapAnalysisReconcileOutcomeEnum.java`
- Create: `erl/entity/ErlGapAnalysisReport.java`
- Create: `erl/entity/ErlGapAnalysisDimensionTask.java`
- Modify: `erl/enums/ErlGapItemTypeEnum.java`（整文件替换）

- [ ] **Step 1: 新建 `erl/enums/ErlGapAnalysisTaskStatusEnum.java`**

```java
package com.gstdev.cioaas.web.erl.enums;

import cn.hutool.core.util.StrUtil;

/**
 * 差距分析<b>维度任务</b>的状态（任务化设计 §4，2026-09-24）。
 *
 * <p>只允许 {@code PENDING → RUNNING → SUCCESS | FAILED}，且每一次状态更新都是条件 UPDATE
 * （{@code WHERE id = ? AND status = ? AND deleted = false}，不变量 I3）。自愈：{@code FAILED}、
 * 或 {@code RUNNING} 且 {@code updated_at} 距今超过 10 分钟的任务，会被 CAS 回 {@code RUNNING}
 * 并按<b>同一个 task id</b> 重新派发；Python 命中自己的 SUCCESS 日志行时直接回状态、不重复烧 LLM。</p>
 *
 * <p>零感知差维度（两端 {@code levelScore} 相等）建行即 {@code SUCCESS + has_gap = false}，
 * 不经过 {@code PENDING}。不设 {@code CANCELLED}：未分享记录里被取代的任务用 {@code deleted}
 * 表达，已分享记录的任务永不改。库列 {@code varchar(16)}，<b>不加 CHECK</b>。</p>
 */
public enum ErlGapAnalysisTaskStatusEnum {

  PENDING,
  RUNNING,
  SUCCESS,
  FAILED;

  /**
   * Python refresh 响应里的 {@code status} 字符串 → 终态。
   *
   * <p>契约只有 {@code SUCCESS} / {@code FAILED} 两个取值；其它任何取值（含 null / 空白 / 拼写漂移）
   * <b>一律按 {@code FAILED}</b> —— 那会让自愈把该任务重投一次，而误判成 SUCCESS 会让一维
   * 永远停在「已分析、无内容」。</p>
   */
  public static ErlGapAnalysisTaskStatusEnum terminalOf(String code) {
    return StrUtil.isNotBlank(code) && SUCCESS.name().equalsIgnoreCase(code.trim()) ? SUCCESS : FAILED;
  }
}
```

- [ ] **Step 2: 新建 `erl/enums/ErlGapAnalysisReconcileOutcomeEnum.java`**

```java
package com.gstdev.cioaas.web.erl.enums;

/**
 * 一次 {@code reconcile}（任务化设计 §5）的收手成因，给接口 18 挑反馈用：
 * 真的有维度没两端交齐 ⇒ 400；两端都交了但有维度题集 mismatch ⇒ 不报错、记 INFO 后原样返回
 * （页面上该维已经是黄点 {@code Question set mismatch}，报「未提交」会让管理员去找不存在的漏交）。
 */
public enum ErlGapAnalysisReconcileOutcomeEnum {

  /** 报告未就绪：至少一个 Active 维度不是两端都 SUBMITTED（不建、不改任何行）。 */
  NOT_SUBMITTED,
  /** 报告未就绪：全部维度两端都交了，但至少一个维度题集版本不一致（不建、不改任何行）。 */
  MISMATCHED,
  /** 规划锁被同期次的另一次 reconcile 占着，本次直接返回，下一次读接口再来。 */
  LOCK_BUSY,
  /** 规划已落库（可能本轮无任务需派发）；有任务时派发与落状态也已完成。 */
  DONE
}
```

- [ ] **Step 3: 新建 `erl/entity/ErlGapAnalysisReport.java`**

```java
package com.gstdev.cioaas.web.erl.entity;

import com.gstdev.cioaas.common.persistence.AbstractCustomEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.UuidGenerator;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

/**
 * 差距分析的<b>报告分享记录</b>（任务化设计 §3.1，表 {@code erl_gap_analysis_report}，sprint119）。
 *
 * <p>同一 {@code (company_id, period)} 下可以有<b>多条</b>记录：每一次「有维度的依据提交变了」
 * 且当时的最新记录已分享，就新建一条；「最新记录」统一按 {@code created_at DESC, id DESC} 取
 * （{@code ErlGapAnalysisReportRepository}）。管理端读最新记录，公司端读最新的
 * {@code shared = true} 记录 —— 创始人手里那份因此天然冻结。</p>
 *
 * <p>不变量 I1：{@link #shared} 为 true 的记录<b>及其任务</b>永不修改、永不软删；
 * 后续改动一律新建记录并复制未变维度的任务。未分享记录就地更新（旧任务软删 + 新建）。</p>
 *
 * <p>{@code created_by} 在异步线程（{@code ioExecutor}）上没有登录态，由服务<b>显式</b>
 * {@code setCreatedBy(callerUserId)}；{@link AbstractCustomEntity#addAuditInfo()} 对已有值不覆盖。</p>
 */
@Getter
@Setter
@Entity
@Table(name = "erl_gap_analysis_report")
@NoArgsConstructor
public class ErlGapAnalysisReport extends AbstractCustomEntity implements Serializable {

  @Id
  @UuidGenerator
  @Column(name = "id", length = 36)
  private String id;

  @Column(name = "company_id", nullable = false, length = 36)
  private String companyId;

  /** 形如 {@code 2026Q3}。 */
  @Column(name = "period", nullable = false, length = 8)
  private String period;

  /**
   * 是否已分享给 Founder 端。<b>只由接口 27 写</b>（{@code SELECT … FOR UPDATE} 最新记录后置位），
   * 永不复位 —— 重生成走「新建记录」而不是改这一位。
   */
  @Column(name = "shared", nullable = false)
  private Boolean shared = Boolean.FALSE;

  @Column(name = "shared_at")
  private Instant sharedAt;

  @Column(name = "shared_by", length = 36)
  private String sharedBy;

  @Override
  public int hashCode() {
    return Objects.hash(id);
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    ErlGapAnalysisReport that = (ErlGapAnalysisReport) o;
    return Objects.equals(id, that.id);
  }
}
```

- [ ] **Step 4: 新建 `erl/entity/ErlGapAnalysisDimensionTask.java`**

```java
package com.gstdev.cioaas.web.erl.entity;

import com.gstdev.cioaas.common.persistence.AbstractCustomEntity;
import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisTaskStatusEnum;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.UuidGenerator;

import java.io.Serializable;
import java.util.Objects;

/**
 * 差距分析的<b>维度任务</b>（任务化设计 §3.2，表 {@code erl_gap_analysis_dimension_task}，sprint119）。
 *
 * <p>一条记录（{@link ErlGapAnalysisReport}）下每个 Active 维度一个<b>未软删</b>任务
 * （部分唯一索引 {@code uk_erl_gap_analysis_dimension_task (erl_gap_analysis_report_id, dimension_code)
 * WHERE deleted = false} 兜底，不变量 I4）。本表只放<b>编排状态</b>：跑没跑、跑完没有、有无差距、
 * 依据哪两次提交；narrative / gaps / actions 在 Python 的 {@code ai_erl_gap_analysis_task_item}，
 * 按 {@code result_task_id ?? id} 关联。</p>
 *
 * <p>不变量：I1 已分享记录的任务永不改、永不软删；I3 状态只能
 * {@code PENDING → RUNNING → SUCCESS | FAILED}，所有更新都走
 * {@code ErlGapAnalysisDimensionTaskRepository#updateStatus} 的条件 UPDATE（CAS），
 * 故本类<b>不要 {@code @Version}</b>；I4 见上。</p>
 *
 * <p>与 {@code ErlDimensionConfig} 一样<b>不用 {@code @SQLRestriction}</b>：读侧一律走带
 * {@code DeletedFalse} 的查询、写侧的 CAS 谓词里显式带 {@code deleted = false}，两处都看得见这一位。</p>
 */
@Getter
@Setter
@Entity
@Table(name = "erl_gap_analysis_dimension_task")
@NoArgsConstructor
public class ErlGapAnalysisDimensionTask extends AbstractCustomEntity implements Serializable {

  @Id
  @UuidGenerator
  @Column(name = "id", length = 36)
  private String id;

  /** 所属记录 {@code erl_gap_analysis_report.id}。 */
  @Column(name = "erl_gap_analysis_report_id", nullable = false, length = 36)
  private String erlGapAnalysisReportId;

  /** {@code erl_dimension_config.dimension_code}。 */
  @Column(name = "dimension_code", nullable = false, length = 8)
  private String dimensionCode;

  /**
   * 依据的 Founder 端 SOT（该维最新一次 SUBMITTED 的 {@code erl_assessment.id}）。
   * 与当前 SOT 逐字比较即知「这一维的分析依据是不是最新提交」—— 取代了旧模型的 sha256 指纹。
   */
  @Column(name = "source_founder_assessment_id", nullable = false, length = 36)
  private String sourceFounderAssessmentId;

  /** 依据的 GSV 端 SOT，同上。 */
  @Column(name = "source_gsv_assessment_id", nullable = false, length = 36)
  private String sourceGsvAssessmentId;

  /** 见 {@link ErlGapAnalysisTaskStatusEnum}；库列 {@code varchar(16)} 不加 CHECK。 */
  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 16)
  private ErlGapAnalysisTaskStatusEnum status;

  /**
   * {@code SUCCESS} 时必填：零感知差维度由 Java 建任务时写 {@code false}；LLM 维度取 Python
   * refresh 响应。非 SUCCESS 时为 null（{@code PENDING / RUNNING / FAILED} 谈不上有无差距）。
   */
  @Column(name = "has_gap")
  private Boolean hasGap;

  /**
   * 复制任务时指向<b>真正持有 Python 内容</b>的原任务 id（{@code 原.result_task_id ?? 原.id}，
   * 链条只有一层）；自己持有内容、或没有内容（零感知差 / LLM 判无差距）时为 null。
   * 读条目一律按 {@code result_task_id ?? id} 去 Python 取。
   */
  @Column(name = "result_task_id", length = 36)
  private String resultTaskId;

  /**
   * 软删：<b>只</b>用于未分享记录内「维度依据变了 ⇒ 旧任务被新任务取代」；已分享记录的任务
   * 永不软删（I1）。命名沿用 ERL 域现有 {@code erl_dimension_config.deleted}。
   */
  @Column(name = "deleted", nullable = false)
  private Boolean deleted = Boolean.FALSE;

  @Override
  public int hashCode() {
    return Objects.hash(id);
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    ErlGapAnalysisDimensionTask that = (ErlGapAnalysisDimensionTask) o;
    return Objects.equals(id, that.id);
  }
}
```

- [ ] **Step 5: 整文件替换 `erl/enums/ErlGapItemTypeEnum.java`**

```java
package com.gstdev.cioaas.web.erl.enums;

/**
 * 差距分析条目类型（design-doc §5.8）。<b>Java 侧只区分两类</b>，用于把一维的条目拆成
 * {@code gaps[]} / {@code actions[]}：
 *
 * <ul>
 *   <li>{@link #GAP}：{@code title} 标题 + {@code severity}；</li>
 *   <li>{@link #ACTION}：{@code title} 建议动作。</li>
 * </ul>
 *
 * <p><b>2026-09-24（任务化）</b>：{@code NARRATIVE} 从本枚举删除 —— 维度级叙述段在 Java 侧是
 * {@code ErlGapDimensionDTO#narrative} 一个字段，不是条目；Python 表 {@code ai_erl_gap_analysis_task_item}
 * 的 {@code item_type = NARRATIVE} 是它自己落库用的取值，Java 从不解析那一列。
 * {@code note} / {@code evidenceMissing} / {@code why} 三个条目字段同日永久删除（设计稿 D7）。</p>
 */
public enum ErlGapItemTypeEnum {

  /** 差距：title 标题、severity 必填 */
  GAP,
  /** 建议动作：title 动作 */
  ACTION
}
```

- [ ] **Step 6: 轻量校验**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests
```
期望：**通过**（本任务全部是新增文件；`ErlGapItemTypeEnum.NARRATIVE` 在 Java 里没有任何引用）。

---

### Task 3: Repository

**Files:**
- Create: `erl/repository/ErlGapAnalysisReportRepository.java`
- Create: `erl/repository/ErlGapAnalysisDimensionTaskRepository.java`

- [ ] **Step 1: 新建 `erl/repository/ErlGapAnalysisReportRepository.java`**

```java
package com.gstdev.cioaas.web.erl.repository;

import com.gstdev.cioaas.web.erl.entity.ErlGapAnalysisReport;
import jakarta.persistence.LockModeType;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * 报告分享记录（任务化设计 §3.1）。「最新记录」<b>三个方法排序键完全一致</b>：
 * {@code created_at DESC, id DESC}（{@code id} 是同一微秒两条记录的平局兜底），主路径
 * {@code idx_erl_gap_analysis_report (company_id, period, created_at DESC)}。
 */
@Repository
public interface ErlGapAnalysisReportRepository extends JpaRepository<ErlGapAnalysisReport, String> {

  /** 管理端可见的那一条：最新记录，不管分没分享。 */
  Optional<ErlGapAnalysisReport> findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(String companyId,
                                                                                         String period);

  /** 公司端可见的那一条：最新的<b>已分享</b>记录；没有即公司端空态。 */
  Optional<ErlGapAnalysisReport> findFirstByCompanyIdAndPeriodAndSharedTrueOrderByCreatedAtDescIdDesc(
      String companyId, String period);

  /**
   * Share 专用：对最新记录加<b>悲观写锁</b>（{@code SELECT … FOR UPDATE}），调用方传
   * {@code PageRequest.of(0, 1)}。
   *
   * <p>为什么要锁：接口 27 是「读最新记录 → 校验五条门槛 → 置三列」，两个管理员同时点、或点击
   * 与后台 {@code reconcile} 新建记录交错时，不加锁会把门槛判在一条已经不是最新的记录上。
   * 锁到手之后调用方还要<b>再读一次最新 id</b>比对：{@code FOR UPDATE} 锁的是本语句快照那一刻的
   * 最新行，锁等待期间若有新记录提交，READ COMMITTED 下下一条语句才看得见（设计稿 §7.4
   * 「窄竞态 ⇒ 400 Content updated, please refresh」）。</p>
   */
  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select r from ErlGapAnalysisReport r where r.companyId = :companyId and r.period = :period "
      + "order by r.createdAt desc, r.id desc")
  List<ErlGapAnalysisReport> lockLatestByCompanyIdAndPeriod(@Param("companyId") String companyId,
                                                            @Param("period") String period,
                                                            Pageable pageable);
}
```

- [ ] **Step 2: 新建 `erl/repository/ErlGapAnalysisDimensionTaskRepository.java`**

```java
package com.gstdev.cioaas.web.erl.repository;

import com.gstdev.cioaas.web.erl.entity.ErlGapAnalysisDimensionTask;
import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisTaskStatusEnum;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.Collection;
import java.util.List;

/**
 * 维度任务（任务化设计 §3.2 / §4）。
 *
 * <p>状态<b>只能</b>经 {@link #updateStatus} 改（条件 UPDATE = CAS，不变量 I3）；软删<b>只能</b>经
 * {@link #markDeleted}。两个 {@code @Modifying} 都开 {@code flushAutomatically}（先把同事务里刚
 * {@code saveAllAndFlush} 的新任务与其它脏数据冲下去，再发 UPDATE）与 {@code clearAutomatically}
 * （UPDATE 绕过一级缓存，清掉之后内存里不会留着一份过期的 status）。返回 rowcount：0 表示
 * 「迟到的结果 / 已软删 / 已被别的线程改走」，调用方记 INFO 忽略，绝不重试也绝不抛。</p>
 */
@Repository
public interface ErlGapAnalysisDimensionTaskRepository extends JpaRepository<ErlGapAnalysisDimensionTask, String> {

  /** 一条记录下的全部<b>活</b>任务（部分唯一索引保证每维至多一条）。 */
  List<ErlGapAnalysisDimensionTask> findByErlGapAnalysisReportIdAndDeletedFalse(String erlGapAnalysisReportId);

  /**
   * CAS 状态更新：{@code status = :fromStatus} 且未软删的那一行才会被改。
   *
   * <p>{@code hasGap} 随状态一起写：认领（→ RUNNING）与失败（→ FAILED）传 {@code null}，
   * 成功（→ SUCCESS）传 Python 回的值。{@code updatedAt / updatedBy} 显式传入 ——
   * JPQL 批量 UPDATE 不触发 {@code @PreUpdate}，异步线程上 {@code SecurityUtils} 也取不到人。</p>
   *
   * @return 改动行数，0 = 前置状态已不成立（迟到结果 / 已软删 / 已被改走）
   */
  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query("update ErlGapAnalysisDimensionTask t set t.status = :toStatus, t.hasGap = :hasGap, "
      + "t.updatedAt = :now, t.updatedBy = :updatedBy "
      + "where t.id = :id and t.status = :fromStatus and t.deleted = false")
  int updateStatus(@Param("id") String id,
                   @Param("fromStatus") ErlGapAnalysisTaskStatusEnum fromStatus,
                   @Param("toStatus") ErlGapAnalysisTaskStatusEnum toStatus,
                   @Param("hasGap") Boolean hasGap,
                   @Param("now") Instant now,
                   @Param("updatedBy") String updatedBy);

  /**
   * 未分享记录内被新任务取代的旧任务批量软删（不变量 I1：已分享记录的任务永远不会传进来）。
   * 必须在插入取代它们的新任务<b>之前</b>执行，否则撞部分唯一索引。
   *
   * @return 改动行数
   */
  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query("update ErlGapAnalysisDimensionTask t set t.deleted = true, t.updatedAt = :now, t.updatedBy = :updatedBy "
      + "where t.id in :ids and t.deleted = false")
  int markDeleted(@Param("ids") Collection<String> ids,
                  @Param("now") Instant now,
                  @Param("updatedBy") String updatedBy);
}
```

- [ ] **Step 3: 轻量校验**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests
```
期望：**通过**（纯新增）。

---
### Task 4: DTO（Python 契约 + 应用层载体）

> 从本任务起到 Task 9 结束前，`compile` 允许报错，但报错只能出现在：`ErlPythonClient`、`ErlGapAnalysisConverter`、`ErlDimensionConverter`、`ErlGapAnalysisService(Impl)`、`ErlCardServiceImpl`、`ErlDimensionServiceImpl`、`ErlAssessmentServiceImpl` 及各 Response VO —— 全是后续任务要改写的文件。

**Files:**
- Create: `erl/dto/ErlGapItemsResultDTO.java`
- Create: `erl/dto/ErlGapAnalysisReportDTO.java`
- Create: `erl/dto/ErlGapAnalysisShareDTO.java`
- Create: `erl/dto/ErlGapAnalysisPlanDTO.java`
- Modify（整文件替换）: `erl/dto/ErlGapAnalysisRequestDTO.java`、`erl/dto/ErlGapAnalysisResultDTO.java`、`erl/dto/ErlGapAnalysisDTO.java`、`erl/dto/ErlGapDimensionDTO.java`、`erl/dto/ErlGapItemDTO.java`
- Modify: `erl/dto/ErlCardDTO.java:46-47`

- [ ] **Step 1: 整文件替换 `erl/dto/ErlGapAnalysisRequestDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.List;

/**
 * {@code POST /api/ai/erl/gap-analysis/refresh} 的入参（任务化设计 §6.1，2026-09-24）。
 *
 * <p>字段名与 Python 侧 Request VO 逐字对齐（lowerCamelCase）；Python <b>不查 ERL 表</b>，
 * 全部输入由 Java 组装传入。{@code JSONUtil.toJsonStr} 会省略 null 值的键（与旧契约同一行为）。</p>
 *
 * <p><b>与旧契约的差别</b>：按<b>任务</b>而不是按维度送 —— 每个任务是一维、一次 LLM；
 * {@code index} / {@code code} / {@code submissionSignature} / {@code organizationId} /
 * {@code noGapDimensions} / {@code analyzedContext} 全部删除（D5 / D6 / D7）。零感知差维度不进本入参
 * （Java 建任务时直接 SUCCESS）。{@code taskId} 只给 Python 落日志行与条目用，<b>不进 prompt</b>。</p>
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapAnalysisRequestDTO implements Serializable {

  /** 只做日志与幂等定位；公司 ACL 在 Java 侧已完成。 */
  private String companyId;

  private String period;

  /** 本轮刚被 CAS 成 {@code RUNNING} 的任务，按配置版本的 {@code sortOrder}。非空（空则 Java 压根不调）。 */
  private List<Task> tasks;

  /** 单任务 = 单维度输入：双端 level 分 + 止步 level + 该维全部题目作答。 */
  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Task implements Serializable {

    /** {@code erl_gap_analysis_dimension_task.id}，Python 按它写 {@code ai_erl_gap_analysis_task(_item)}。 */
    private String taskId;

    private String name;

    /** 显示缩写，与 {@link #name} 一起给模型人类可读的维度身份。 */
    private String abbr;

    /** 该维权重百分比数值，让模型知道这一维在综合分里的份量。 */
    private BigDecimal weight;

    /** 创始人端维度分（整数 level）。 */
    private Integer founderLevelScore;

    /** GSV 端维度分（整数 level）。 */
    private Integer gsvLevelScore;

    /** {@code founderLevelScore - gsvLevelScore}；能进本入参的任务两端都有分，故不为 null 且不为 0。 */
    private Integer perceptionGap;

    /** 创始人端首次出现 No 的 level；全通关为 null。 */
    private Integer founderTerminatedLevel;

    /** GSV 端首次出现 No 的 level；全通关为 null。 */
    private Integer gsvTerminatedLevel;

    private List<Question> questions;
  }

  /**
   * 逐题作答快照。未解锁 level 的题两端都没有答案行，{@code founderYesNo} / {@code gsvYesNo}
   * 因此为 null —— 模型据此知道「这题没问到」而不是「答了 No」。
   */
  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Question implements Serializable {

    private String questionText;

    /** 题目所属 level 1–9。 */
    private Integer eraBand;

    /** level 展示名，如 {@code Harvest & Growth - 5}。 */
    private String eraLabel;

    private String evidenceSource;

    private Boolean founderYesNo;

    private Boolean gsvYesNo;

    /** 证据 / 备注，Goldie 的关键输入。 */
    private String founderNote;

    private String gsvNote;

    /**
     * 该题两端附件的并集，<b>按 {@code fileId} 去重、Founder 端在前</b>；无附件为空数组（不给 null）。
     * Java 只送 id 与文件名；Python 按 {@code fileId} <b>跨任务去重</b>后现场下载 + 解析 + 摘要，不落库。
     * {@code fileName} 为 null（{@code files} 行已清理）时 Python 判该附件无摘要、不阻断分析。
     */
    private List<Attachment> attachments;
  }

  /** 一份题目附件；字段与 Python 侧逐字对齐，刻意不带 summary。 */
  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Attachment implements Serializable {

    /** {@code files.id}。 */
    private String fileId;

    /** 原始文件名（{@code files.original_name}）；{@code files} 行已被清理时为 null。 */
    private String fileName;
  }
}
```

- [ ] **Step 2: 整文件替换 `erl/dto/ErlGapAnalysisResultDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.util.List;

/**
 * {@code POST /api/ai/erl/gap-analysis/refresh} 的出参 {@code data}（任务化设计 §6.1）：
 * <b>只回每个任务的终态</b>，内容另经 {@code POST /items} 取（{@link ErlGapItemsResultDTO}）。
 *
 * <p>Java 拿它逐任务做 CAS：{@code RUNNING → SUCCESS(hasGap) | FAILED}。响应里缺席的任务
 * 留在 {@code RUNNING}，交给 10 分钟超龄规则重投（设计稿 §4）。</p>
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapAnalysisResultDTO implements Serializable {

  private List<Task> tasks;

  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Task implements Serializable {

    private String taskId;

    /** {@code SUCCESS} / {@code FAILED}；其它取值由 {@code ErlGapAnalysisTaskStatusEnum#terminalOf} 归为 FAILED。 */
    private String status;

    /** 只在 SUCCESS 时有意义（= GAP 条目数 &gt; 0）；缺席按 false。 */
    private Boolean hasGap;
  }
}
```

- [ ] **Step 3: 新建 `erl/dto/ErlGapItemsResultDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.util.List;

/**
 * {@code POST /api/ai/erl/gap-analysis/items} 的出参 {@code data}（任务化设计 §6.2）：
 * 按任务 id 批量取 AI 内容。<b>无条目的 taskId 不出现</b>（零感知差 / LLM 判无差距的任务本就不该被查）。
 *
 * <p>Java 一次读页面只调它<b>一次</b>（接口 17 把全部 {@code SUCCESS ∧ has_gap} 任务的
 * {@code result_task_id ?? id} 攒齐再发），接口 21 只带该维一个 id。</p>
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapItemsResultDTO implements Serializable {

  private List<Item> items;

  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Item implements Serializable {

    /** 请求里带过去的那个 id（= 持有内容的原任务 id）。 */
    private String taskId;

    /** 该维叙述段；prompt v1.7 只对有差距的维度产出。 */
    private String narrative;

    private List<Gap> gaps;

    private List<Action> actions;
  }

  /** 一条差距。{@code severity} 非法值由 Java 侧降级为 MEDIUM（{@code ErlSeverityEnum#fromCodeOrDefault}）。 */
  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Gap implements Serializable {

    private String title;

    private String severity;
  }

  /** 一条建议动作，只剩标题（{@code why} 已删，D7）。 */
  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Action implements Serializable {

    private String title;
  }
}
```

- [ ] **Step 4: 新建 `erl/dto/ErlGapAnalysisReportDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisTaskStatusEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.util.List;

/**
 * 域内读形态：<b>这一端可见的那条记录 + 它的活任务</b>（任务化设计 §7.1），不含任何 Python 内容。
 *
 * <p>接口 1（卡片）只吃它 —— {@code shared / shareable / dimensions[].hasGap} 全部来自 Java 表，
 * 不调 Python；接口 27 用它判五条门槛。选行口径只在 {@code ErlGapAnalysisService#loadResult} 一处：
 * 管理端 = 最新记录，公司端 = 最新已分享记录（没有则整个 DTO 为 null）。</p>
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapAnalysisReportDTO implements Serializable {

  private String reportId;

  private Boolean shared;

  /** 该记录下的未软删任务，按记录内维度任意序（消费方按 {@code dimensionCode} 索引）。 */
  private List<Task> tasks;

  @Getter
  @Setter
  @Builder
  @NoArgsConstructor
  @AllArgsConstructor
  public static class Task implements Serializable {

    private String taskId;

    private String dimensionCode;

    private ErlGapAnalysisTaskStatusEnum status;

    /** 见 {@code ErlGapAnalysisDimensionTask#hasGap}；非 SUCCESS 时 null。 */
    private Boolean hasGap;

    private String resultTaskId;

    private String sourceFounderAssessmentId;

    private String sourceGsvAssessmentId;
  }
}
```

- [ ] **Step 5: 新建 `erl/dto/ErlGapAnalysisShareDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.Instant;

/**
 * 接口 27 的出参载体（design-doc §6.6）。接口 17 的出参自 2026-09-24 起<b>不再</b>带
 * {@code sharedAt / sharedBy}（D7），故 Share 的三个字段单独成 DTO，不再复用 {@link ErlGapAnalysisDTO}。
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapAnalysisShareDTO implements Serializable {

  private Boolean shared;

  private Instant sharedAt;

  private String sharedBy;
}
```

- [ ] **Step 6: 新建 `erl/dto/ErlGapAnalysisPlanDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisReconcileOutcomeEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;

/**
 * {@code ErlGapAnalysisService#plan} 的返回：规划事务里做完的事的摘要，交给锁外的派发段。
 *
 * <p>{@link #request} 为 null 表示<b>本轮没有任务要派发</b>（门槛未过、或没有
 * {@code PENDING / FAILED / 超龄 RUNNING} 的活任务），派发段直接返回 {@link #outcome}。</p>
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapAnalysisPlanDTO implements Serializable {

  private ErlGapAnalysisReconcileOutcomeEnum outcome;

  /** 只含本轮刚 CAS 成 {@code RUNNING} 的任务；null = 无事可派。 */
  private ErlGapAnalysisRequestDTO request;
}
```

- [ ] **Step 7: 整文件替换 `erl/dto/ErlGapAnalysisDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.util.List;

/**
 * Goldie 差距分析（design-doc §6.6 接口 17 / 18，任务化设计 §7.2）。
 *
 * <p><b>2026-09-24（任务化，D7）永久删除</b>：{@code summary / generatedAt / model / stale / generating /
 * sharedAt / sharedBy}。接口 27 的分享三字段改走 {@link ErlGapAnalysisShareDTO}。</p>
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapAnalysisDTO implements Serializable {

  /**
   * 按维度分组的差距与建议。管理端遍历<b>当前 Active 维度</b>；公司端有已分享记录时只遍历
   * <b>该记录里的任务</b>（消掉「分享后新增维度」的假阴性），没有已分享记录时仍下发 Active 维度骨架
   * （每维 {@code analyzed = false}），让 Gap 区块的空态照常按维度渲染小卡。
   */
  private List<ErlGapDimensionDTO> dimensions;

  /**
   * <b>向 Python 取条目失败</b>（不可用 / 鉴权失败）。没有条目可取（无任务 {@code SUCCESS ∧ hasGap}）时恒 false。
   * 两端都下发：公司端同样需要知道是「坏了」而不是「在跑」。
   */
  private Boolean analysisServiceUnavailable;

  /** 管理端 = 最新记录已分享；公司端 = 存在已分享记录（前端据此显示 {@code No gap analysis shared yet.}）。 */
  private Boolean shared;

  /** {@code Share to founder} 是否可激活，口径见 {@code ErlGapAnalysisService#isShareable}；<b>仅管理端</b>，公司端 null。 */
  private Boolean shareable;
}
```

- [ ] **Step 8: 整文件替换 `erl/dto/ErlGapDimensionDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.util.List;

/**
 * 差距分析的单维度分组（design-doc §6.6 接口 17，任务化设计 §7.2 维度级字段表）。
 *
 * <p>{@code bothSubmitted} / {@code analyzed} / {@code hasGap} / {@code questionSetMismatch} 是四条
 * <b>互相独立</b>的信息，前端不要压成一个枚举。{@code analyzedAt} 已删（D7）。</p>
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapDimensionDTO implements Serializable {

  private String dimensionCode;

  /** 显示缩写：Active 维度取配置；公司端已分享记录里的停用维度取评估行上的快照缩写。 */
  private String dimensionAbbr;

  /** 该维两端是否都有 SUBMITTED 记录 —— 决定小卡圆点颜色。Java 现算，公司端不冻结（已接受）。 */
  private Boolean bothSubmitted;

  /** 该维活任务存在且 {@code status = SUCCESS}。false 是「还没分析」不是「没差距」。 */
  private Boolean analyzed;

  /** 任务列 {@code has_gap}；{@code analyzed = false} 时恒 false。 */
  private Boolean hasGap;

  /**
   * <b>恒 false</b>（2026-09-24）：任务依据变了走的是「新任务 / 新记录」，屏上不再有 {@code Updating…}
   * 这一态；字段保留一版供前端兼容，下一版随前端六态代码一起删。
   */
  private Boolean dimensionStale;

  /** 该维两端答的不是同一套题 ⇒ 不可比。不能压进 {@link #hasGap}（压进去就是绿点 No Gap 的假阴性）。 */
  private Boolean questionSetMismatch;

  /** mismatch 时落后的那一端：{@code FOUNDER} / {@code GSV}；不 mismatch 时为 null。 */
  private String mismatchSide;

  /** 该维叙述段（只有 {@code hasGap = true} 的维度才有）。 */
  private String narrative;

  /** {@code itemType = GAP} 的条目。 */
  private List<ErlGapItemDTO> gaps;

  /** {@code itemType = ACTION} 的条目。 */
  private List<ErlGapItemDTO> actions;
}
```

- [ ] **Step 9: 整文件替换 `erl/dto/ErlGapItemDTO.java`**

```java
package com.gstdev.cioaas.web.erl.dto;

import com.gstdev.cioaas.web.erl.enums.ErlGapItemTypeEnum;
import com.gstdev.cioaas.web.erl.enums.ErlSeverityEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;

/**
 * 差距分析的一条明细（design-doc §5.8），用 {@link #itemType} 区分：
 * GAP = {@code title + severity}；ACTION = {@code title}。
 * {@code note} / {@code evidenceMissing}（以及 ACTION 的 {@code why}）2026-09-24 永久删除（D7）。
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErlGapItemDTO implements Serializable {

  private String dimensionCode;

  private ErlGapItemTypeEnum itemType;

  private String title;

  /** 仅 GAP 有值；越界值已降级为 MEDIUM。 */
  private ErlSeverityEnum severity;

  /** 数组下标：Python 按 {@code sort_order} 排好序返回。 */
  private Integer sortOrder;
}
```

- [ ] **Step 10: 修改 `erl/dto/ErlCardDTO.java`**

删除 :46-47 这两行：
```java
  /** Goldie summary 的截断展示；公司端在 {@code shared = false} 时为 null（§0.10-D3）。 */
  private String gapSummary;
```
并把 :49 的 `shared` 字段 Javadoc 改为：
```java
  /** 该期次这一端可见的差距分析记录是否已分享（管理端 = 最新记录.shared；公司端 = 有已分享记录）。 */
  private Boolean shared;
```

- [ ] **Step 11: 轻量校验**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests 2>&1 | grep -E "ERROR.*\.java" | sed -E 's/.*erl\///' | sort -u
```
期望：报错文件**只**落在 `client/ErlPythonClient.java`、`converter/ErlGapAnalysisConverter.java`、`converter/ErlDimensionConverter.java`、`service/ErlGapAnalysisService.java`、`service/ErlGapAnalysisServiceImpl.java`、`service/ErlCardServiceImpl.java`、`service/ErlDimensionServiceImpl.java`、`vo/response/*.java` 之内。

---

### Task 5: `ErlPythonClient` 重写 + `ErlPythonClientTest` 重写

**Files:**
- Modify（整文件替换）: `erl/client/ErlPythonClient.java`
- Test（整文件替换）: `test/erl/client/ErlPythonClientTest.java`

- [ ] **Step 1: 整文件替换 `erl/client/ErlPythonClient.java`**

```java
package com.gstdev.cioaas.web.erl.client;

import cn.hutool.core.util.StrUtil;
import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.gstdev.cioaas.common.exception.ServiceException;
import com.gstdev.cioaas.common.message.ServiceErrorMessage;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisRequestDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemsResultDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * ERL 的 Java → Python 客户端（任务化设计 §6，2026-09-24）。<b>只剩两个端点</b>：
 * {@link #refresh}（按任务生成，同步回每任务终态）与 {@link #fetchItems}（按任务 id 批量取条目）。
 * {@code GET /gap-analysis} 与 {@code POST /gap-analysis/share} 已随「Java 持有编排状态」一起删除。
 *
 * <p><b>直连内网、不经网关</b>：本仓库网关只有 {@code /api/web/**} 与 {@code /web/**} 两条路由，
 * 没有 {@code /api/ai/**}；与存量的 {@code AI_MODEL_URL} 走同一套做法（Nacos 配 URL + Hutool）。</p>
 *
 * <p>Python 侧鉴权走全局 {@code AuthMiddleware}，因此每次调用都要把<b>调用者的 Bearer token</b>
 * 透传到 {@code Authorization} 头 —— 异步对账跑在 {@code ioExecutor} 线程上拿不到请求上下文，
 * token 由调用方作为入参传进来。</p>
 *
 * <p>本类<b>只负责一次 HTTP 往返</b>：不重试、不落库、不吞异常。降级口径在
 * {@code ErlGapAnalysisServiceImpl}：refresh 失败 ⇒ 任务留 {@code RUNNING}、10 分钟后重投；
 * items 失败 ⇒ 出参 {@code analysisServiceUnavailable = true}。</p>
 *
 * <p>⚠️ <b>Java 与 Python 不得跨版本并存</b>（设计稿 §9.2）：新 Java + 旧 Python ⇒ refresh 422、
 * 任务留 PENDING / RUNNING，开关打开后自愈；旧 Java + 新 Python ⇒ 旧 GET 404 ⇒
 * {@code analysisServiceUnavailable}。Java 必须一次性全量替换。</p>
 */
@Slf4j
@Component
public class ErlPythonClient {

  private static final String GAP_ANALYSIS_PATH = "/api/ai/erl/gap-analysis";

  /** 按任务生成（任务化设计 §6.1）。Python 每任务一次 LLM、并发 3、自带 2 次重试；Java 不重试。 */
  private static final String GAP_ANALYSIS_REFRESH_PATH = GAP_ANALYSIS_PATH + "/refresh";

  /** 按任务 id 批量取条目（任务化设计 §6.2）。 */
  private static final String GAP_ANALYSIS_ITEMS_PATH = GAP_ANALYSIS_PATH + "/items";

  private static final int CONNECT_TIMEOUT_MS = 5_000;

  /**
   * refresh 的读超时，<b>沿用 500s</b>（设计稿 §6）。
   *
   * <p><b>算式在任务化之后变了，别照旧注释去核</b>：旧模型一次 LLM 覆盖全部维度，最坏
   * 附件摘要阶段总闸 120s + LLM 3 次尝试 × 120s + 退避 6s = 486s ⇒ 500s 完整覆盖。
   * 新模型<b>每任务一次 LLM、Python 侧 {@code Semaphore(3)}</b>：最坏 ≈ 120s + ⌈任务数 / 3⌉ × 366s
   * —— 一次派发 ≤ 3 个任务时仍是 486s；4 ~ 6 个任务（5 维全部重跑 / 手动 Generate）时是 852s，
   * <b>500s 盖不住</b>。撞超时的后果与旧模型不同、也轻得多：任务留 {@code RUNNING}，10 分钟后
   * 被管理端读接口重投，Python 命中自己的 SUCCESS 日志行直接回状态、<b>不重复烧 LLM</b>
   * （设计稿 §4 / §8），代价只是多一次往返而不是丢一轮生成。要不要为手动 Generate 单独上调，
   * 见 {@code docs/待优化项.md} 首条（接口 18 本就受网关 120s 先掐断）。</p>
   *
   * <p>⚠️ 这条「超时不丢工作」依赖「客户端断连不会取消 Python 那边的请求处理协程」，
   * 2026-09-21 在 uvicorn 0.46 / starlette 1.0 / fastapi 0.136 组合下实测成立；
   * 升级 Python 侧 ASGI 栈时要重测。</p>
   */
  private static final int GAP_ANALYSIS_REFRESH_READ_TIMEOUT_MS = 500_000;

  /**
   * items 的读超时：一次索引命中的短查询，<b>绝不能沿用 refresh 的 500s</b> —— 它挂在用户打开页面的
   * 请求线程上，Python 卡住时整页要等 8 分多钟才降级。
   */
  private static final int GAP_ANALYSIS_ITEMS_READ_TIMEOUT_MS = 10_000;

  /** 异常消息里带的响应体截断长度：够看清 detail / 信封，又不把整个 body 灌进 Sentry。 */
  private static final int ERROR_BODY_MAX_LENGTH = 300;

  @Value("${cio.erl.ai-base-url}")
  private String aiBaseUrl;

  /**
   * 派发一批任务并同步等 Python 逐任务回终态（任务化设计 §6.1）。
   *
   * @param input       只含本轮刚 CAS 成 RUNNING 的任务（Python 对已有 SUCCESS 日志行的任务直接回状态）
   * @param bearerToken 调用者的 Bearer token，原样透传到 {@code Authorization} 头
   * @throws ServiceException HTTP 失败、响应信封 {@code success = false} 或结果无法解析
   */
  public ErlGapAnalysisResultDTO refresh(ErlGapAnalysisRequestDTO input, String bearerToken) {
    String url = aiBaseUrl + GAP_ANALYSIS_REFRESH_PATH;
    return toRefreshResult(postForData(url, JSONUtil.toJsonStr(input), bearerToken,
        GAP_ANALYSIS_REFRESH_READ_TIMEOUT_MS));
  }

  /**
   * 按任务 id 批量取条目（任务化设计 §6.2）。无条目的 id 不出现在返回里。
   *
   * @param taskIds 持有内容的任务 id（{@code result_task_id ?? id}），非空
   * @throws ServiceException HTTP 失败或响应信封 {@code success = false}
   */
  public ErlGapItemsResultDTO fetchItems(List<String> taskIds, String bearerToken) {
    String url = aiBaseUrl + GAP_ANALYSIS_ITEMS_PATH;
    JSONObject body = new JSONObject();
    body.set("taskIds", taskIds);
    return toItemsResult(postForData(url, body.toString(), bearerToken, GAP_ANALYSIS_ITEMS_READ_TIMEOUT_MS));
  }

  /** refresh 的 {@code data} → DTO；{@code tasks} 缺席按空列表，逐字段容错（缺字段不抛）。 */
  private ErlGapAnalysisResultDTO toRefreshResult(JSONObject data) {
    List<ErlGapAnalysisResultDTO.Task> tasks = new ArrayList<>();
    JSONArray raw = data.getJSONArray("tasks");
    if (raw != null) {
      for (int i = 0; i < raw.size(); i++) {
        JSONObject task = raw.getJSONObject(i);
        tasks.add(ErlGapAnalysisResultDTO.Task.builder()
            .taskId(task.getStr("taskId"))
            .status(task.getStr("status"))
            .hasGap(task.getBool("hasGap"))
            .build());
      }
    }
    return ErlGapAnalysisResultDTO.builder().tasks(tasks).build();
  }

  /** items 的 {@code data} → DTO；{@code items} / 每项的 {@code gaps} / {@code actions} 缺席都按空列表。 */
  private ErlGapItemsResultDTO toItemsResult(JSONObject data) {
    List<ErlGapItemsResultDTO.Item> items = new ArrayList<>();
    JSONArray raw = data.getJSONArray("items");
    if (raw != null) {
      for (int i = 0; i < raw.size(); i++) {
        JSONObject item = raw.getJSONObject(i);
        items.add(ErlGapItemsResultDTO.Item.builder()
            .taskId(item.getStr("taskId"))
            .narrative(item.getStr("narrative"))
            .gaps(toBeans(item.getJSONArray("gaps"), ErlGapItemsResultDTO.Gap.class))
            .actions(toBeans(item.getJSONArray("actions"), ErlGapItemsResultDTO.Action.class))
            .build());
      }
    }
    return ErlGapItemsResultDTO.builder().items(items).build();
  }

  /** JSON 数组 → Bean 列表；缺字段按<b>空列表</b>处理（下游一律不判 null）。 */
  private <T> List<T> toBeans(JSONArray raw, Class<T> type) {
    if (raw == null) {
      return Collections.emptyList();
    }
    List<T> beans = new ArrayList<>(raw.size());
    for (int i = 0; i < raw.size(); i++) {
      beans.add(JSONUtil.toBean(raw.getJSONObject(i), type));
    }
    return beans;
  }

  /** 发一次 POST 并取出 {@code data} 对象；任何失败都带上 url 与截断后的响应体抛出。 */
  private JSONObject postForData(String url, String jsonBody, String bearerToken, int readTimeoutMs) {
    return JSONUtil.parseObj(requireEnvelopeData(url,
        execute(HttpRequest.post(url).body(jsonBody), url, bearerToken, readTimeoutMs)));
  }

  /** 单次 HTTP 往返；连接异常也统一转成 {@link ServiceException}，日志必附 Throwable。 */
  private String execute(HttpRequest request, String url, String bearerToken, int readTimeoutMs) {
    HttpResponse response;
    try {
      request.setConnectionTimeout(CONNECT_TIMEOUT_MS)
          .setReadTimeout(readTimeoutMs)
          .header("Content-Type", "application/json");
      if (StrUtil.isNotBlank(bearerToken)) {
        request.header("Authorization", bearerToken);
      }
      response = request.execute();
    } catch (Exception e) {
      log.error("ERL python call failed: url={}", url, e);
      throw new ServiceException(ServiceErrorMessage.RC_OPERATION_FAILED, "ERL AI service is unavailable.", e);
    }
    String responseBody = response.body();
    if (response.getStatus() < 200 || response.getStatus() >= 300) {
      log.error("ERL python call returned HTTP {}: url={}, body={}",
          response.getStatus(), url, StrUtil.maxLength(responseBody, ERROR_BODY_MAX_LENGTH));
      throw new ServiceException(ServiceErrorMessage.RC_OPERATION_FAILED,
          "ERL AI service returned HTTP " + response.getStatus() + ".");
    }
    return responseBody;
  }

  /** 校验 {@code {success, code, message, data}} 信封并返回 {@code data} 的原始 JSON 文本。 */
  private String requireEnvelopeData(String url, String responseBody) {
    JSONObject envelope = JSONUtil.parseObj(responseBody);
    if (!Boolean.TRUE.equals(envelope.getBool("success")) || envelope.get("data") == null) {
      log.error("ERL python call returned a failed envelope: url={}, body={}",
          url, StrUtil.maxLength(responseBody, ERROR_BODY_MAX_LENGTH));
      throw new ServiceException(ServiceErrorMessage.RC_OPERATION_FAILED,
          StrUtil.blankToDefault(envelope.getStr("message"), "ERL AI service returned an unsuccessful response."));
    }
    return envelope.get("data").toString();
  }
}
```

- [ ] **Step 2: 整文件替换 `test/erl/client/ErlPythonClientTest.java`**

```java
package com.gstdev.cioaas.web.erl.client;

import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisRequestDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemsResultDTO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

/**
 * {@link ErlPythonClient} 的<b>纯序列化 / 解析</b>单测：只测「Java 发出去的 JSON 长什么样」与
 * 「Python 回了这样一段 JSON，Java 解成什么」。
 *
 * <p><b>刻意不起 Spring 上下文、不发任何真实 HTTP</b>。出站字段名是跨语言契约的一半：Java 靠 Lombok
 * getter 推字段名、Python 是 pydantic 的 lowerCamelCase 字段，对不上时 pydantic <b>静默忽略</b>
 * 未知字段（不是 422）—— 症状是「Java 说送了、Python 说没收到」。入站方向要钉的是容错：
 * 缺字段 / 字段为 null 不能抛，因为 refresh 的解析异常会让本轮任务全部留在 RUNNING、
 * items 的解析异常会让整块 Gap 区块报 {@code analysisServiceUnavailable}。</p>
 *
 * <p>两个解析方法是私有的，经 {@code ReflectionTestUtils} 调用 —— 对外只有两个发 HTTP 的方法。</p>
 */
class ErlPythonClientTest {

  private final ErlPythonClient client = new ErlPythonClient();

  private ErlGapAnalysisResultDTO toRefreshResult(String json) {
    JSONObject data = JSONUtil.parseObj(json);
    return ReflectionTestUtils.invokeMethod(client, "toRefreshResult", data);
  }

  private ErlGapItemsResultDTO toItemsResult(String json) {
    JSONObject data = JSONUtil.parseObj(json);
    return ReflectionTestUtils.invokeMethod(client, "toItemsResult", data);
  }

  // ── 入参序列化（契约 §6.1）──────────────────────────────────────────────

  @Test
  @DisplayName("refresh 入参：顶层只有 companyId / period / tasks，任务字段名逐字与 Python 对齐")
  void serializesTheRefreshInputWithTheContractFieldNames() {
    ErlGapAnalysisRequestDTO input = ErlGapAnalysisRequestDTO.builder()
        .companyId("c1")
        .period("2026Q3")
        .tasks(List.of(ErlGapAnalysisRequestDTO.Task.builder()
            .taskId("t-1")
            .name("Financial Readiness")
            .abbr("FRL")
            .weight(new BigDecimal("20.00"))
            .founderLevelScore(5)
            .gsvLevelScore(4)
            .perceptionGap(1)
            .founderTerminatedLevel(6)
            .gsvTerminatedLevel(null)
            .questions(List.of(ErlGapAnalysisRequestDTO.Question.builder()
                .questionText("Is the monthly close under 10 days?")
                .eraBand(1)
                .eraLabel("Founder Era - 1")
                .evidenceSource("Close checklist")
                .founderYesNo(Boolean.TRUE)
                .gsvYesNo(Boolean.FALSE)
                .founderNote("we close in 8 days")
                .gsvNote(null)
                .attachments(List.of(ErlGapAnalysisRequestDTO.Attachment.builder()
                    .fileId("file-1").fileName("close.pdf").build()))
                .build()))
            .build()))
        .build();

    JSONObject json = JSONUtil.parseObj(JSONUtil.toJsonStr(input));

    assertThat(json.keySet())
        .as("organizationId / dimensions / noGapDimensions / analyzedContext 全部删除（D7）")
        .containsExactlyInAnyOrder("companyId", "period", "tasks");
    JSONObject task = json.getJSONArray("tasks").getJSONObject(0);
    assertThat(task.keySet())
        .as("index / code / submissionSignature 不再存在；gsvTerminatedLevel 为 null 时整键省略（与旧契约同一行为）")
        .containsExactlyInAnyOrder("taskId", "name", "abbr", "weight", "founderLevelScore", "gsvLevelScore",
            "perceptionGap", "founderTerminatedLevel", "questions");
    assertThat(task.getStr("taskId")).isEqualTo("t-1");
    JSONObject question = task.getJSONArray("questions").getJSONObject(0);
    assertThat(question.keySet()).containsExactlyInAnyOrder("questionText", "eraBand", "eraLabel", "evidenceSource",
        "founderYesNo", "gsvYesNo", "founderNote", "attachments");
    JSONObject attachment = question.getJSONArray("attachments").getJSONObject(0);
    assertThat(attachment.getStr("fileId")).isEqualTo("file-1");
    assertThat(attachment.getStr("fileName")).isEqualTo("close.pdf");
  }

  @Test
  @DisplayName("refresh 入参：题目无附件时 attachments 照常下发 []，不会变成 null 或整键消失")
  void serializesAnEmptyAttachmentListAsAnEmptyArray() {
    ErlGapAnalysisRequestDTO input = ErlGapAnalysisRequestDTO.builder()
        .companyId("c1").period("2026Q3")
        .tasks(List.of(ErlGapAnalysisRequestDTO.Task.builder()
            .taskId("t-1")
            .questions(List.of(ErlGapAnalysisRequestDTO.Question.builder()
                .questionText("q").attachments(List.of()).build()))
            .build()))
        .build();

    JSONObject json = JSONUtil.parseObj(JSONUtil.toJsonStr(input));

    assertThat(json.getJSONArray("tasks").getJSONObject(0).getJSONArray("questions").getJSONObject(0)
        .getJSONArray("attachments")).isEmpty();
  }

  // ── refresh 出参（契约 §6.1）────────────────────────────────────────────

  @Test
  @DisplayName("refresh 出参：逐任务还原 taskId / status / hasGap")
  void mapsTheRefreshResponse() {
    ErlGapAnalysisResultDTO result = toRefreshResult("""
        {"tasks": [
          {"taskId": "t-1", "status": "SUCCESS", "hasGap": true},
          {"taskId": "t-2", "status": "SUCCESS", "hasGap": false},
          {"taskId": "t-3", "status": "FAILED"}
        ]}
        """);

    assertThat(result.getTasks()).extracting(
            ErlGapAnalysisResultDTO.Task::getTaskId,
            ErlGapAnalysisResultDTO.Task::getStatus,
            ErlGapAnalysisResultDTO.Task::getHasGap)
        .containsExactly(
            org.assertj.core.groups.Tuple.tuple("t-1", "SUCCESS", Boolean.TRUE),
            org.assertj.core.groups.Tuple.tuple("t-2", "SUCCESS", Boolean.FALSE),
            org.assertj.core.groups.Tuple.tuple("t-3", "FAILED", null));
  }

  @Test
  @DisplayName("refresh 出参：tasks 缺席 / 为 null / 空对象都解成空列表，不抛")
  void toleratesAMissingTaskList() {
    assertThatCode(() -> {
      assertThat(toRefreshResult("{}").getTasks()).isNotNull().isEmpty();
      assertThat(toRefreshResult("{\"tasks\": null}").getTasks()).isEmpty();
      assertThat(toRefreshResult("{\"tasks\": []}").getTasks()).isEmpty();
    }).doesNotThrowAnyException();
  }

  // ── items 出参（契约 §6.2）──────────────────────────────────────────────

  @Test
  @DisplayName("items 出参：按任务还原 narrative / gaps[title, severity] / actions[title]")
  void mapsTheItemsResponse() {
    ErlGapItemsResultDTO result = toItemsResult("""
        {"items": [
          {"taskId": "t-1",
           "narrative": "FRL scores 6/9.",
           "gaps": [{"title": "Close takes 20 days", "severity": "HIGH"}],
           "actions": [{"title": "Version the checklist"}]}
        ]}
        """);

    assertThat(result.getItems()).singleElement().satisfies(item -> {
      assertThat(item.getTaskId()).isEqualTo("t-1");
      assertThat(item.getNarrative()).isEqualTo("FRL scores 6/9.");
      assertThat(item.getGaps()).singleElement().satisfies(gap -> {
        assertThat(gap.getTitle()).isEqualTo("Close takes 20 days");
        assertThat(gap.getSeverity()).isEqualTo("HIGH");
      });
      assertThat(item.getActions()).singleElement()
          .satisfies(action -> assertThat(action.getTitle()).isEqualTo("Version the checklist"));
    });
  }

  @Test
  @DisplayName("items 出参：多出来的键（note / why / evidenceMissing）被忽略，不影响解析")
  void ignoresFieldsThatAreNoLongerPartOfTheContract() {
    ErlGapItemsResultDTO result = toItemsResult("""
        {"items": [{"taskId": "t-1",
          "gaps": [{"title": "g", "severity": "LOW", "note": "n", "evidenceMissing": true}],
          "actions": [{"title": "a", "why": "w"}]}]}
        """);

    assertThat(result.getItems().get(0).getGaps().get(0).getTitle()).isEqualTo("g");
    assertThat(result.getItems().get(0).getActions().get(0).getTitle()).isEqualTo("a");
  }

  @Test
  @DisplayName("items 出参：gaps / actions 缺失时是空列表而不是 null；items 缺席解成空列表")
  void toleratesAnItemWithoutGapsOrActions() {
    ErlGapItemsResultDTO result = toItemsResult("{\"items\": [{\"taskId\": \"t-1\", \"narrative\": \"only\"}]}");

    assertThat(result.getItems()).singleElement().satisfies(item -> {
      assertThat(item.getGaps()).as("给 null 会让读侧各自再补一次空判").isNotNull().isEmpty();
      assertThat(item.getActions()).isNotNull().isEmpty();
    });
    assertThat(toItemsResult("{}").getItems()).isNotNull().isEmpty();
  }
}
```

- [ ] **Step 3: 轻量校验**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests 2>&1 | grep -E "ERROR.*\.java" | sed -E 's/.*erl\///' | sort -u
```
期望：`client/ErlPythonClient.java` **不再**出现在报错清单里；其余报错仍限于 Task 4 列出的后续文件。

---

### Task 6: Response VO 与 Converter

**Files:**
- Modify（整文件替换）: `erl/vo/response/ErlGapAnalysisResponse.java`、`erl/vo/response/ErlGapAnalysisDimensionResponse.java`、`erl/vo/response/ErlGapItemResponse.java`、`erl/vo/response/ErlActionItemResponse.java`、`erl/converter/ErlGapAnalysisConverter.java`
- Modify: `erl/vo/response/ErlCardResponse.java:43-44`
- Modify: `erl/converter/ErlDimensionConverter.java:19-25,33-34`

- [ ] **Step 1: 整文件替换 `erl/vo/response/ErlGapAnalysisResponse.java`**

```java
package com.gstdev.cioaas.web.erl.vo.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 接口 17 / 18 出参：Goldie 差距分析（design-doc §6.6，任务化设计 §7.2）。
 *
 * <p><b>2026-09-24 永久删除</b>（D7）：{@code summary / generatedAt / model / stale / generating /
 * sharedAt / sharedBy}。前端自 2026-09-21 / 09-23 起对它们均无渲染方。</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Goldie 差距分析")
public class ErlGapAnalysisResponse {

  @Schema(description = "按维度分组的差距与建议；管理端按当前 Active 维度、公司端按已分享记录里的任务")
  private List<ErlGapAnalysisDimensionResponse> dimensions;

  @Schema(description = "向 Python 取条目失败（不可用 / 鉴权失败）。为 true 时前端应显示失败态 + Retry，"
      + "而不是「正在分析」；没有条目可取时恒 false。两端都下发")
  private Boolean analysisServiceUnavailable;

  @Schema(description = "管理端 = 最新记录已分享；公司端 = 存在已分享记录")
  private Boolean shared;

  @JsonInclude(JsonInclude.Include.NON_NULL)
  @Schema(description = "Share to founder 是否可激活；仅管理端下发")
  private Boolean shareable;
}
```

- [ ] **Step 2: 整文件替换 `erl/vo/response/ErlGapAnalysisDimensionResponse.java`**

```java
package com.gstdev.cioaas.web.erl.vo.response;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 差距分析的维度分组（design-doc §6.6 接口 17，任务化设计 §7.2）。
 *
 * <p>{@code bothSubmitted} / {@code analyzed} / {@code hasGap} / {@code questionSetMismatch} 是四条
 * <b>互相独立</b>的信息，前端不要压成一个枚举。{@code analyzedAt} 已删（D7）；{@code dimensionStale}
 * 保留一版但恒 false。</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "差距分析的维度分组")
public class ErlGapAnalysisDimensionResponse {

  @Schema(description = "维度 code")
  private String dimensionCode;

  @Schema(description = "显示缩写")
  private String dimensionAbbr;

  @Schema(description = "该维两端是否都已提交 —— 决定小卡圆点颜色")
  private Boolean bothSubmitted;

  @Schema(description = "该维的任务已 SUCCESS。analyzed = false 时 hasGap 恒 false，但那是「没分析」不是「没差距」")
  private Boolean analyzed;

  @Schema(description = "该维是否有 gap —— 取任务行的 has_gap，未分析的维度恒 false")
  private Boolean hasGap;

  @Schema(description = "恒 false（2026-09-24 起任务依据变了走新任务 / 新记录，不再有 Updating… 态）；字段保留一版供前端兼容")
  private Boolean dimensionStale;

  @Schema(description = "该维两端答的不是同一套题 ⇒ 不可比、不做分析；不要压进 hasGap")
  private Boolean questionSetMismatch;

  @Schema(description = "mismatch 时落后的那一端：FOUNDER / GSV；不 mismatch 时为空")
  private String mismatchSide;

  @Schema(description = "该维叙述段，无差距的维度为空")
  private String narrative;

  @Schema(description = "差距条目")
  private List<ErlGapItemResponse> gaps;

  @Schema(description = "建议行动")
  private List<ErlActionItemResponse> actions;
}
```

- [ ] **Step 3: 整文件替换 `erl/vo/response/ErlGapItemResponse.java`**

```java
package com.gstdev.cioaas.web.erl.vo.response;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Goldie 产出的单条差距（design-doc §5.8，{@code item_type = GAP}）。
 * {@code note} / {@code evidenceMissing} 2026-09-24 永久删除（D7，前端只渲染标题与严重度）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "差距条目")
public class ErlGapItemResponse {

  @Schema(description = "差距标题")
  private String title;

  @Schema(description = "严重度：HIGH / MEDIUM / LOW")
  private String severity;
}
```

- [ ] **Step 4: 整文件替换 `erl/vo/response/ErlActionItemResponse.java`**

```java
package com.gstdev.cioaas.web.erl.vo.response;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Goldie 产出的单条建议行动（design-doc §5.8，{@code item_type = ACTION}）。
 * 只剩标题：{@code why}（PRD §3.6「为何相关」）2026-09-24 永久删除（D7，前端不渲染）；
 * Java 侧早已没有存放它的列。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "建议行动条目")
public class ErlActionItemResponse {

  @Schema(description = "建议动作")
  private String title;
}
```

- [ ] **Step 5: 修改 `erl/vo/response/ErlCardResponse.java`**

删除 :43-44 这两行：
```java
  @Schema(description = "差距分析摘要（截断展示）；公司端在 shared = false 时为 null")
  private String gapSummary;
```
（若上一行为空行则连同多余空行一起收掉，保持字段之间恰好一个空行。）

- [ ] **Step 6: 整文件替换 `erl/converter/ErlGapAnalysisConverter.java`**

```java
package com.gstdev.cioaas.web.erl.converter;

import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisShareDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapDimensionDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemDTO;
import com.gstdev.cioaas.web.erl.vo.response.ErlActionItemResponse;
import com.gstdev.cioaas.web.erl.vo.response.ErlGapAnalysisDimensionResponse;
import com.gstdev.cioaas.web.erl.vo.response.ErlGapAnalysisResponse;
import com.gstdev.cioaas.web.erl.vo.response.ErlGapAnalysisShareResponse;
import com.gstdev.cioaas.web.erl.vo.response.ErlGapItemResponse;
import org.mapstruct.Mapper;
import org.mapstruct.NullValuePropertyMappingStrategy;
import org.mapstruct.ReportingPolicy;

import java.util.Collections;
import java.util.List;

/**
 * E 模块的 Response ↔ DTO 转换（design-doc §6.6）。
 *
 * <p><b>2026-09-24（任务化，D7）</b>：接口 17 出参只剩 {@code dimensions / analysisServiceUnavailable /
 * shared / shareable}；接口 27 出参改吃 {@link ErlGapAnalysisShareDTO}；ACTION 的 {@code why ← note}
 * 映射随两个字段一起删除。</p>
 */
@Mapper(componentModel = "spring",
    unmappedTargetPolicy = ReportingPolicy.IGNORE,
    nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
public interface ErlGapAnalysisConverter {

  ErlGapItemResponse toGapResponse(ErlGapItemDTO dto);

  List<ErlGapItemResponse> toGapResponses(List<ErlGapItemDTO> dtoList);

  ErlActionItemResponse toActionResponse(ErlGapItemDTO dto);

  List<ErlActionItemResponse> toActionResponses(List<ErlGapItemDTO> dtoList);

  /** 维度分组的同名字段全部由 MapStruct 直映；只有名字对不上的才需要写 {@code @Mapping}。 */
  ErlGapAnalysisDimensionResponse toResponse(ErlGapDimensionDTO dto);

  List<ErlGapAnalysisDimensionResponse> toDimensionResponses(List<ErlGapDimensionDTO> dtoList);

  /** 接口 27 出参：只回三个 share 字段（§0.10-D3）。 */
  default ErlGapAnalysisShareResponse toShareResponse(ErlGapAnalysisShareDTO dto) {
    if (dto == null) {
      return null;
    }
    return ErlGapAnalysisShareResponse.builder()
        .shared(Boolean.TRUE.equals(dto.getShared()))
        .sharedAt(dto.getSharedAt())
        .sharedBy(dto.getSharedBy())
        .build();
  }

  /** {@code dimensions[]} 骨架照常下发（空态也要按维度渲染小卡，§9 / §0.10-D4）。 */
  default ErlGapAnalysisResponse toResponse(ErlGapAnalysisDTO dto) {
    if (dto == null) {
      return null;
    }
    return ErlGapAnalysisResponse.builder()
        .dimensions(dto.getDimensions() == null
            ? Collections.emptyList() : toDimensionResponses(dto.getDimensions()))
        .analysisServiceUnavailable(Boolean.TRUE.equals(dto.getAnalysisServiceUnavailable()))
        .shared(Boolean.TRUE.equals(dto.getShared()))
        .shareable(dto.getShareable())
        .build();
  }
}
```

- [ ] **Step 7: 修改 `erl/converter/ErlDimensionConverter.java`**

把 :19-25 的类 Javadoc 整段替换为：
```java
/**
 * 接口 2 / 22 的 DTO → Response 转换（standards/coding.md §2 三层传输实体）。
 *
 * <p>两个接口的题目结构<b>共用 {@code ErlQuestionDetailResponse}</b>，不新造第二套（§6.2.1）。
 * 差距 / 建议条目与接口 17 共用 {@code ErlGapItemResponse} / {@code ErlActionItemResponse}，
 * 同名字段直映（{@code why} 已随 2026-09-24 任务化一并删除，不再有跨名映射）。
 */
```
再把 :33-34 的
```java
  @Mapping(target = "why", source = "note")
  ErlActionItemResponse toActionResponse(ErlGapItemDTO dto);
```
改为
```java
  ErlActionItemResponse toActionResponse(ErlGapItemDTO dto);
```
`import org.mapstruct.Mapping;` 若此后无其它 `@Mapping` 使用则删除（本文件 :37 还有 `@Mapping(target = "header", ignore = true)`，故**保留**该 import）。

- [ ] **Step 8: 轻量校验**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests 2>&1 | grep -E "ERROR.*\.java" | sed -E 's/.*erl\///' | sort -u
```
期望：报错清单**只**剩 `service/ErlGapAnalysisService.java`、`service/ErlGapAnalysisServiceImpl.java`、`service/ErlCardServiceImpl.java`、`service/ErlDimensionServiceImpl.java`、`service/ErlAssessmentServiceImpl.java`（以及 MapStruct 因上述文件而未生成实现的连带报错）。

---
### Task 7: `ErlGapAnalysisService` 接口重写

**Files:**
- Modify（整文件替换）: `erl/service/ErlGapAnalysisService.java`

- [ ] **Step 1: 整文件替换 `erl/service/ErlGapAnalysisService.java`**

```java
package com.gstdev.cioaas.web.erl.service;

import com.gstdev.cioaas.web.erl.dto.ErlDimensionConfigDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisPlanDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisReportDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisShareDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemDTO;
import com.gstdev.cioaas.web.erl.entity.ErlAssessment;
import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisReconcileOutcomeEnum;
import com.gstdev.cioaas.web.erl.enums.ErlPortalEnum;

import java.util.List;
import java.util.Map;

/**
 * Goldie 差距分析（E 模块，design-doc §6.6 / §7.5，任务化设计 2026-09-24 / v4.65 §0.39）。
 *
 * <p><b>Java 持有编排状态，Python 持有 AI 内容</b>（D1）：报告记录 {@code erl_gap_analysis_report}
 * + 维度任务 {@code erl_gap_analysis_dimension_task} 在本域两张表里；narrative / gaps / actions
 * 在 Python 的 {@code ai_erl_gap_analysis_task_item}，按 {@code result_task_id ?? id} 取。
 * 本服务是 ERL 域<b>唯一</b>的差距分析入口 —— Card / 维度详情一律走 {@link #loadResult} /
 * {@link #loadItems}，不得自行注入 {@code ErlPythonClient} 或两个新 repository。</p>
 *
 * <p><b>三个触发点共用 {@link #reconcile}</b>：① 评估提交后（{@link #reconcileAsync}，force=false）；
 * ② 管理端读接口 17（{@link #find} 内经 60s 冷却投 {@link #reconcileAsync}）；③ 接口 18 手动
 * Generate（{@link #generate} 同步调 {@link #reconcile}，force=true）。{@code cio.erl.ai-enabled=false}
 * 时 ① ② 整体跳过，③ 不受影响。</p>
 */
public interface ErlGapAnalysisService {

  /**
   * 接口 17 读取：<b>只读记录与任务 + 一次批量取条目，绝不同步等 LLM</b>。
   *
   * <p>管理端读最新记录并（60s 冷却内至多一次）异步投一次 {@link #reconcileAsync} 兜底自愈；
   * 公司端读最新已分享记录，没有即 {@code shared = false} 的空态。{@code dimensions[]} 管理端按
   * 当前 Active 维度、公司端按已分享记录里的任务（没有记录时退回 Active 维度骨架）。</p>
   *
   * @param period    为空时取该公司 closed month 所在季度（§0.10-R3），取不到即空态
   * @param dimension 非空时只返回该维度的条目（A3 维度详情页）
   */
  ErlGapAnalysisDTO find(String requestedCompanyId, String period, String dimension);

  /**
   * 接口 18 手动 Generate（<b>仅管理端</b>，D10 保持同步）：请求线程上 {@code reconcile(force = true)}
   * 后返回 {@link #find} 同形的读结果。
   *
   * <p>报告未就绪时：有维度没两端交齐 ⇒ 400；全部交齐但有维度题集 mismatch ⇒ 不报错、记 INFO
   * 后原样返回（页面上该维已是黄点，报「未提交」会让管理员去找不存在的漏交）。派发失败
   * ⇒ {@code ServiceException}（任务留 RUNNING，10 分钟后由读接口重投）。</p>
   *
   * @param bearerToken 调用者的 Bearer token，透传给 Python 侧鉴权
   */
  ErlGapAnalysisDTO generate(String requestedCompanyId, String period, String bearerToken);

  /**
   * 接口 27 Share（<b>仅管理端</b>）：{@code SELECT … FOR UPDATE} 最新记录 → 五条门槛（{@link #isShareable}）
   * → 置 {@code shared / shared_at / shared_by}。<b>不再调 Python</b>。已分享记录自此不可变（I1）。
   * 门槛未达成 400，按成因给不同文案；锁到手时最新记录已被后台换掉 ⇒ 400 {@code Content updated, please refresh.}
   */
  ErlGapAnalysisShareDTO share(String requestedCompanyId, String period);

  /**
   * 触发点 ① / ②：{@code @Async("ioExecutor")} 上跑一次 {@link #reconcile}（force=false），
   * <b>任何失败都只记日志、不向调用方抛</b>；{@code cio.erl.ai-enabled=false} 时整体跳过。
   * 跑在线程池上没有请求上下文，故 companyId / period / callerUserId / token 必须全部由调用方传入。
   */
  void reconcileAsync(String companyId, String period, String callerUserId, String bearerToken);

  /**
   * 对账主流程（任务化设计 §5 九步）：① Redis 规划锁 → ②~⑦ {@link #plan}（一个事务）→ ⑧ 释放锁 →
   * ⑨ 有待派发任务时组包一次调 Python refresh 并经 {@link #applyResults} 逐任务 CAS 落状态。
   *
   * <p>本方法<b>不进事务</b>（HTTP 往返最长 500s）；派发失败<b>向上抛</b>（任务留 RUNNING，
   * 由 10 分钟超龄规则重投），由 {@link #reconcileAsync} / {@link #generate} 各自决定吞还是转 500。</p>
   *
   * @param callerUserId 触发本次对账的用户，落到新建记录 / 任务的 {@code created_by} 与 CAS 的 {@code updated_by}
   * @param force        true = 每个 Active 维度都视为「依据已变」（手动 Generate 用户就是想重跑）
   * @return 收手成因；{@code DONE} 也可能本轮无任务可派
   */
  ErlGapAnalysisReconcileOutcomeEnum reconcile(String companyId, String period, String callerUserId,
                                               String bearerToken, boolean force);

  /**
   * 对账的<b>规划事务</b>（设计稿 §5 步骤 2 ~ 7）：判报告级门槛 → 算每维目标 source → 建记录 /
   * 复制 / 软删重建 → CAS 认领待派发任务 → 组好 refresh 入参。<b>只供 {@link #reconcile} 经代理调用</b>，
   * 放在接口上是为了让 {@code @Transactional(REQUIRED)} 生效（自调用绕过代理）。
   */
  ErlGapAnalysisPlanDTO plan(String companyId, String period, String callerUserId, boolean force);

  /**
   * 对账的<b>落状态事务</b>（设计稿 §5 步骤 9 后半）：按 Python 响应逐任务 {@code RUNNING → SUCCESS(hasGap) | FAILED}
   * 条件 UPDATE；rowcount = 0（迟到 / 已软删 / 已被改走）记 INFO 忽略。<b>只供 {@link #reconcile} 经代理调用</b>。
   */
  void applyResults(ErlGapAnalysisResultDTO result, String callerUserId);

  /**
   * <b>域内读形态</b>（接口 1 / 27 用）：这一端可见的记录 + 活任务，<b>不调 Python</b>。
   * 选行口径只此一处（设计稿 §7.1）：管理端最新记录、公司端最新已分享记录，没有即 {@code null}。
   */
  ErlGapAnalysisReportDTO loadResult(String companyId, String period, boolean adminEnd);

  /**
   * 接口 21（A3 维度详情）用：这一端可见记录里<b>该维一个任务</b>的 GAP / ACTION 条目（用
   * {@code itemType} 区分，调用方自行拆两组）。任务不存在 / 未 SUCCESS / 无差距 / Python 取不到
   * 都返回空列表（后者已记 WARN），整页不受影响（设计 §8）。<b>仅限请求线程</b>（token 取自请求上下文）。
   */
  List<ErlGapItemDTO> loadItems(String companyId, String period, String dimensionCode, boolean adminEnd);

  /**
   * <b>题库版本 mismatch 判定</b>（P4，设计 §7）：只回不一致的维度 —— {@code 维度码 → 版本号较小的那一端}。
   * 判据是维度级 {@code question_version_no}；只判两端都已提交的维度；任一端解不出即 fail-open（WARN）。
   * 本方法是该判定的<b>唯一入口</b>，同时喂接口 1 / 17 出参与报告级门槛，入参直接吃调用方已查出的两端 SOT 行。
   */
  Map<String, ErlPortalEnum> resolveQuestionSetMismatch(String companyId, String period,
                                                        ErlDimensionConfigDTO config,
                                                        Map<String, ErlAssessment> founderRows,
                                                        Map<String, ErlAssessment> gsvRows);

  /**
   * Share 门槛<b>五条</b>（设计稿 §7.4）：ready（每个 Active 维度两端都 SUBMITTED 且无 mismatch）
   * ∧ 最新记录存在 ∧ 未分享 ∧ 每个 Active 维度的活任务都 {@code SUCCESS} ∧ 每维任务的
   * {@code source_*_assessment_id} == 当前 SOT。同时喂接口 1 / 17 出参与接口 27 校验，三处同源。
   *
   * @param mismatchSides 调用方已算出的那一份，<b>非空</b>（无 mismatch 传空 Map）
   * @param report        调用方 {@link #loadResult}（或 Share 内加锁读出）的那一份；{@code null} 即不可分享
   */
  boolean isShareable(ErlDimensionConfigDTO config,
                      Map<String, ErlAssessment> founderRows,
                      Map<String, ErlAssessment> gsvRows,
                      Map<String, ErlPortalEnum> mismatchSides,
                      ErlGapAnalysisReportDTO report);
}
```

- [ ] **Step 2: 轻量校验**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests 2>&1 | grep -E "ERROR.*\.java" | sed -E 's/.*erl\///' | sort -u
```
期望：报错清单只剩 `service/ErlGapAnalysisServiceImpl.java`、`service/ErlCardServiceImpl.java`、`service/ErlDimensionServiceImpl.java`、`service/ErlAssessmentServiceImpl.java`（接口新方法尚无实现 / 旧方法已不存在）。

---

### Task 8: `ErlGapAnalysisServiceImpl` 原文件内重写

**Files:**
- Modify（整文件替换，分两步写入同一文件，Step 2 的代码紧接 Step 1 末尾）: `erl/service/ErlGapAnalysisServiceImpl.java`

> 全部删除的旧成员：`regenerate`、`loadResult(companyId, period)` 两参版、`isStale`、`isAnalysisUnavailable`、`visibleArtifact`、`groupDimensions`、`indexByCode`、`dimensionSignature`、`GapAnalysisGate` / `resolveGate`、`analyzableDimensions`、`noPerceptionGap` / `noPerceptionGapDimensions`、`outdatedDimensions`、`buildNoGapDimensions`、`analyzedContext`、`DigestUtil` import。保留（逐字或近似）的旧成员：`acquireRegenerationCooldown`、`resolveConfigOrganizationId`、`allDimensionsSubmitted`、`resolveQuestionSetMismatch` 及三个 helper、`latestSubmitted`、`loadAnswers` / `loadAttachments` / `loadQuestions` / `answersOf` / `questionsOf` / `buildQuestions` / `mergeAttachments` / `indexByQuestionKey`、`organizationOf`、`currentBearerToken`、`portalName`、`normalizeCode`。

- [ ] **Step 1: 写入文件上半 —— 包头、字段、接口 17 / 18 / 27、触发点与写路径**

```java
package com.gstdev.cioaas.web.erl.service;

import cn.hutool.core.util.StrUtil;
import com.gstdev.cioaas.common.exception.BadRequestException;
import com.gstdev.cioaas.common.exception.ServiceException;
import com.gstdev.cioaas.common.message.ServiceErrorMessage;
import com.gstdev.cioaas.web.erl.client.ErlPythonClient;
import com.gstdev.cioaas.web.erl.dto.ErlAttachmentDTO;
import com.gstdev.cioaas.web.erl.dto.ErlCallerDTO;
import com.gstdev.cioaas.web.erl.dto.ErlDimensionConfigDTO;
import com.gstdev.cioaas.web.erl.dto.ErlDimensionConfigItemDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisPlanDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisReportDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisRequestDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisShareDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapDimensionDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemsResultDTO;
import com.gstdev.cioaas.web.erl.entity.ErlAssessment;
import com.gstdev.cioaas.web.erl.entity.ErlAssessmentAnswer;
import com.gstdev.cioaas.web.erl.entity.ErlGapAnalysisDimensionTask;
import com.gstdev.cioaas.web.erl.entity.ErlGapAnalysisReport;
import com.gstdev.cioaas.web.erl.entity.ErlQuestionConfig;
import com.gstdev.cioaas.web.erl.enums.ErlAssessmentStatusEnum;
import com.gstdev.cioaas.web.erl.enums.ErlEraEnum;
import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisReconcileOutcomeEnum;
import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisTaskStatusEnum;
import com.gstdev.cioaas.web.erl.enums.ErlGapItemTypeEnum;
import com.gstdev.cioaas.web.erl.enums.ErlPortalEnum;
import com.gstdev.cioaas.web.erl.enums.ErlSeverityEnum;
import com.gstdev.cioaas.web.erl.repository.ErlAssessmentAnswerRepository;
import com.gstdev.cioaas.web.erl.repository.ErlAssessmentRepository;
import com.gstdev.cioaas.web.erl.repository.ErlGapAnalysisDimensionTaskRepository;
import com.gstdev.cioaas.web.erl.repository.ErlGapAnalysisReportRepository;
import com.gstdev.cioaas.web.erl.scoring.ErlScoreCalculator;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Lazy;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * {@link ErlGapAnalysisService} 实现（任务化设计 2026-09-24，design-doc v4.65 / §0.39）。
 *
 * <p><b>Java 持有编排状态</b>：报告记录（{@code erl_gap_analysis_report}）+ 维度任务
 * （{@code erl_gap_analysis_dimension_task}，状态机 {@code PENDING → RUNNING → SUCCESS | FAILED}，
 * 全部条件 UPDATE）；Python 持有 AI 内容。三个触发点共用一个 {@link #reconcile}，按设计稿 §5 九步平铺。</p>
 *
 * <p><b>事务边界</b>：规划（{@link #plan}）是一个 {@code REQUIRED} 事务、在 Redis 规划锁内；派发（HTTP，
 * 读超时 500s）在锁外、事务外；落状态（{@link #applyResults}）是另一个短事务。{@code plan} /
 * {@code applyResults} 由本类自己调用，必须经 {@link #self} 走 Spring 代理，否则 {@code @Transactional}
 * 不生效（{@link #reconcileAsync} 的 {@code @Async} 同理）。</p>
 *
 * <p><b>读路径不进事务</b>：{@link #find} / {@link #loadItems} 挂 {@code NOT_SUPPORTED} —— 各有一次向 Python
 * 取条目的 HTTP 往返（读超时 10s），挂着数据库连接会拖垮连接池；{@link #loadResult} 不发 HTTP，留在类级
 * {@code readOnly} 事务里给 Card 用。代价是放弃事务快照（几次短查询落在不同时点），最坏后果只是多投一次
 * 对账，由下一次读接口收敛。</p>
 */
@Slf4j
@Service
@Transactional(readOnly = true, rollbackFor = Exception.class)
public class ErlGapAnalysisServiceImpl implements ErlGapAnalysisService {

  /** 规划锁键前缀（{@code 域:实体:id} 口径，coding.md §10）：同 (company, period) 同一时刻只有一个 reconcile 在规划。 */
  private static final String PLAN_LOCK_KEY_PREFIX = "erl:gapAnalysis:plan:";

  /** 规划锁 TTL：规划只是几次短查询 + 几行写入，60s 是持锁线程被杀后的死锁上限，不是预期耗时。 */
  private static final long PLAN_LOCK_SECONDS = 60L;

  /** 触发点 ② 的投递冷却键前缀。 */
  private static final String REGENERATION_COOLDOWN_KEY_PREFIX = "erl:gapAnalysis:cooldown:";

  /** 冷却时长：够盖住前端 5s × 24 的整轮轮询里的绝大部分，又不至于拖慢真实提交后的自愈。 */
  private static final long REGENERATION_COOLDOWN_SECONDS = 60L;

  /** RUNNING 超龄阈值（设计稿 §4）：超过它的 RUNNING 任务视为派发线程已丢，允许同 id 重投。 */
  private static final Duration RUNNING_STALE_AFTER = Duration.ofMinutes(10);

  @Resource
  private ErlAccessService erlAccessService;

  @Resource
  private ErlDimensionConfigService erlDimensionConfigService;

  @Resource
  private ErlPeriodService erlPeriodService;

  @Resource
  private ErlAssessmentRepository erlAssessmentRepository;

  @Resource
  private ErlAssessmentAnswerRepository erlAssessmentAnswerRepository;

  @Resource
  private ErlQuestionConfigVersionService erlQuestionConfigVersionService;

  /** 逐题附件：入参组装时一次性批量取，绝不按题 / 按维度查（coding.md §10）。 */
  @Resource
  private ErlAttachmentService erlAttachmentService;

  @Resource
  private ErlGapAnalysisReportRepository erlGapAnalysisReportRepository;

  @Resource
  private ErlGapAnalysisDimensionTaskRepository erlGapAnalysisDimensionTaskRepository;

  @Resource
  private ErlPythonClient erlPythonClient;

  /** 规划锁与触发点 ② 的冷却键。 */
  @Resource
  private StringRedisTemplate stringRedisTemplate;

  /**
   * AI 能力总开关（{@code cio.erl.ai-enabled}，缺省开）。置 false 的环境（uat）触发点 ① ② 整体跳过
   * （不建记录、不建任务、不调 Python）；读路径与 Share 照常；<b>接口 18 手动 Generate 不受本开关约束</b>
   * （人工动作，需求方明确保留）。
   */
  @Value("${cio.erl.ai-enabled:true}")
  private boolean aiEnabled;

  /**
   * 自身代理：{@link #plan} / {@link #applyResults} 的 {@code @Transactional} 与 {@link #reconcileAsync} 的
   * {@code @Async} 都要经代理才生效，而 {@code this.xxx(...)} 自调用绕过代理。{@code @Lazy} 断开自注入的循环依赖。
   */
  @Resource
  @Lazy
  private ErlGapAnalysisService self;

  /** 每维的目标依据：两端 SOT id + 是否零感知差（设计稿 §5 步骤 3）。 */
  private record TaskTarget(String founderAssessmentId, String gsvAssessmentId, boolean zeroPerceptionGap) {
  }

  /** 一次批量取条目的结果：按持有内容的任务 id 索引 + 是否取失败（⇒ {@code analysisServiceUnavailable}）。 */
  private record FetchedItems(Map<String, ErlGapItemsResultDTO.Item> byTaskId, boolean unavailable) {
  }

  // ── 接口 17：读 ────────────────────────────────────────────────────────

  /**
   * {@code NOT_SUPPORTED}：本方法含一次 HTTP 往返（{@link #fetchItems}，读超时 10s），
   * 留在类级 {@code readOnly} 事务里就会在整个往返期间占着一条数据库连接。
   *
   * <p>触发点 ②：管理端每次打开页面（60s 冷却内至多一次）异步投一次对账，兜住「提交后的
   * 异步对账丢失」「FAILED / 超龄 RUNNING 重投」「存量已交齐期次的首次生成」。公司端的读<b>绝不产生写副作用</b>。
   * 开关关闭时 {@link #reconcileAsync} 自己短路，这里不重复判 —— 冷却键白占 60s 无害。</p>
   */
  @Override
  @Transactional(propagation = Propagation.NOT_SUPPORTED)
  public ErlGapAnalysisDTO find(String requestedCompanyId, String period, String dimension) {
    String companyId = erlAccessService.resolveCompanyId(requestedCompanyId);
    ErlCallerDTO caller = erlAccessService.currentCaller();
    String resolvedPeriod = erlPeriodService.resolvePeriod(companyId, period);
    if (caller.isAdminEnd() && StrUtil.isNotBlank(resolvedPeriod)
        && acquireRegenerationCooldown(companyId, resolvedPeriod)) {
      self.reconcileAsync(companyId, resolvedPeriod, caller.getUserId(), currentBearerToken());
    }
    return read(companyId, resolvedPeriod, dimension, caller.isAdminEnd());
  }

  // ── 接口 18：管理端手动 Generate ────────────────────────────────────────

  /**
   * 手动重新生成（触发点 ③，D10 保持同步）：请求线程上跑一次 {@code reconcile(force = true)}，
   * 再返回接口 17 同形的读结果。
   *
   * <p>⚠️ 网关 {@code cioaas-gateway.yml} 的 {@code response-timeout: 120000} 先于客户端 500s 到期，
   * 管理员看到的多半是网关 504 而不是下面那句文案；那时任务留 RUNNING，10 分钟后由读接口重投，
   * Python 命中自己的 SUCCESS 日志行直接回状态（{@code docs/待优化项.md} 首条继续挂账）。</p>
   */
  @Override
  @Transactional(propagation = Propagation.NOT_SUPPORTED)
  public ErlGapAnalysisDTO generate(String requestedCompanyId, String period, String bearerToken) {
    erlAccessService.assertAdminEnd();
    String companyId = erlAccessService.resolveCompanyId(requestedCompanyId);
    if (StrUtil.isBlank(period)) {
      throw new BadRequestException("period is required.");
    }
    String callerUserId = erlAccessService.currentCaller().getUserId();
    ErlGapAnalysisReconcileOutcomeEnum outcome;
    try {
      outcome = reconcile(companyId, period, callerUserId, bearerToken, true);
    } catch (Exception e) {
      // 派发失败要让管理员知道（异步入口才静默）；任务留 RUNNING，自愈会重投
      log.error("ERL gap analysis manual generation failed: companyId={}, period={}", companyId, period, e);
      throw new ServiceException(ServiceErrorMessage.RC_OPERATION_FAILED,
          "Gap analysis failed. Please try again.", e);
    }
    if (outcome == ErlGapAnalysisReconcileOutcomeEnum.NOT_SUBMITTED) {
      // 门槛不就绪 ⇒ 400。报告级门槛（D3）：文案随之由「至少一个维度」改为「全部维度」（2026-09-24 计划核对时改口）
      throw new BadRequestException(
          "All dimensions must be submitted by both sides before generating.");
    }
    if (outcome == ErlGapAnalysisReconcileOutcomeEnum.MISMATCHED) {
      // 两端其实都交了，只是有维度答的不是同一套题：不报错（页面上该维已经是黄点），记 INFO 后原样返回
      log.info("ERL gap analysis manual generation skipped, a dimension has a question set mismatch: "
          + "companyId={}, period={}", companyId, period);
    }
    return read(companyId, period, null, true);
  }

  // ── 接口 27：Share ──────────────────────────────────────────────────────

  /**
   * {@code REQUIRED}：整条路径是「{@code FOR UPDATE} 最新记录 → 校验 → 置三列」的一次短写事务，
   * <b>不再调 Python</b>（记录级不可变取代了快照，D4）。
   */
  @Override
  @Transactional(propagation = Propagation.REQUIRED, rollbackFor = Exception.class)
  public ErlGapAnalysisShareDTO share(String requestedCompanyId, String period) {
    erlAccessService.assertAdminEnd();
    String companyId = erlAccessService.resolveCompanyId(requestedCompanyId);
    if (StrUtil.isBlank(period)) {
      throw new BadRequestException("period is required.");
    }
    Map<String, ErlAssessment> founderRows = latestSubmitted(companyId, period, ErlPortalEnum.FOUNDER);
    Map<String, ErlAssessment> gsvRows = latestSubmitted(companyId, period, ErlPortalEnum.GSV);
    ErlDimensionConfigDTO config = erlDimensionConfigService.activeConfigOf(
        resolveConfigOrganizationId(companyId, founderRows, gsvRows));
    // 门槛分开报只为挑文案：全都交了却被拒时，说「都提交才能分享」会让管理员去找不存在的漏交
    if (!allDimensionsSubmitted(config, founderRows, gsvRows)) {
      throw new BadRequestException("All dimensions must be submitted by both sides before sharing.");
    }
    Map<String, ErlPortalEnum> mismatchSides =
        resolveQuestionSetMismatch(companyId, period, config, founderRows, gsvRows);
    if (!mismatchSides.isEmpty()) {
      // 文案与前端三处 mismatch 提示同一套名词（question bank / new-version questionnaire）
      throw new BadRequestException(
          "The question bank has been updated and one side has not yet submitted the new-version "
              + "questionnaire. Both sides must re-submit before sharing.");
    }
    ErlGapAnalysisReport report = lockLatestReport(companyId, period);
    if (Boolean.TRUE.equals(report.getShared())) {
      throw new BadRequestException("This gap analysis has already been shared.");
    }
    ErlGapAnalysisReportDTO snapshot = toReportDTO(report, activeTasksOf(report));
    // 最终仍由 isShareable 拍板：门槛口径只此一处，与接口 1 / 17 下发的 shareable 不可能不一致
    if (!isShareable(config, founderRows, gsvRows, mismatchSides, snapshot)) {
      throw new BadRequestException(
          "Some dimensions have not been analyzed for the latest submissions yet. "
              + "Please wait for the analysis to finish before sharing.");
    }
    String userId = erlAccessService.currentCaller().getUserId();
    report.setShared(Boolean.TRUE);
    report.setSharedAt(Instant.now());
    report.setSharedBy(userId);
    erlGapAnalysisReportRepository.save(report);
    log.info("ERL gap analysis shared to founder: companyId={}, period={}, reportId={}",
        companyId, period, report.getId());
    return ErlGapAnalysisShareDTO.builder()
        .shared(Boolean.TRUE)
        .sharedAt(report.getSharedAt())
        .sharedBy(userId)
        .build();
  }

  /**
   * {@code SELECT … FOR UPDATE} 最新记录，锁到手后<b>再读一次最新 id</b>比对（设计稿 §7.4 的窄竞态）：
   * 锁等待期间后台 {@code reconcile} 可能刚提交了一条新记录，READ COMMITTED 下下一条语句才看得见。
   */
  private ErlGapAnalysisReport lockLatestReport(String companyId, String period) {
    List<ErlGapAnalysisReport> locked =
        erlGapAnalysisReportRepository.lockLatestByCompanyIdAndPeriod(companyId, period, PageRequest.of(0, 1));
    if (locked.isEmpty()) {
      throw new BadRequestException("There is no gap analysis to share for this period.");
    }
    ErlGapAnalysisReport report = locked.get(0);
    String latestId = erlGapAnalysisReportRepository
        .findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(companyId, period)
        .map(ErlGapAnalysisReport::getId)
        .orElse(null);
    if (!report.getId().equals(latestId)) {
      throw new BadRequestException("Content updated, please refresh.");
    }
    return report;
  }

  // ── 触发点 ① / ②：异步对账 ────────────────────────────────────────────

  @Override
  @Async("ioExecutor")
  @Transactional(propagation = Propagation.NOT_SUPPORTED)
  public void reconcileAsync(String companyId, String period, String callerUserId, String bearerToken) {
    if (StrUtil.isBlank(companyId) || StrUtil.isBlank(period)) {
      return;
    }
    // 开关挡在 ① ② 的汇合处；③ 手动 Generate 直接调 reconcile，不经过这里。设计内的正常路径，记 INFO
    if (!aiEnabled) {
      log.info("ERL gap analysis is disabled (cio.erl.ai-enabled=false), skipping reconciliation: "
          + "companyId={}, period={}", companyId, period);
      return;
    }
    try {
      ErlGapAnalysisReconcileOutcomeEnum outcome = reconcile(companyId, period, callerUserId, bearerToken, false);
      log.info("ERL gap analysis reconciled: companyId={}, period={}, outcome={}", companyId, period, outcome);
    } catch (Exception e) {
      // 派发失败不改任何任务（留 RUNNING，10 分钟后重投），也绝不向提交流程抛出（§7.5 / §9）
      log.error("ERL gap analysis reconciliation gave up, tasks are left as they are: companyId={}, period={}",
          companyId, period, e);
    }
  }

  // ── 对账主流程（设计稿 §5 九步）───────────────────────────────────────

  @Override
  @Transactional(propagation = Propagation.NOT_SUPPORTED)
  public ErlGapAnalysisReconcileOutcomeEnum reconcile(String companyId, String period, String callerUserId,
                                                      String bearerToken, boolean force) {
    // 1  加规划锁；抢不到直接返回，下一次读接口再来
    if (!acquirePlanLock(companyId, period)) {
      log.info("ERL gap analysis plan lock is held by another run, skipping: companyId={}, period={}",
          companyId, period);
      return ErlGapAnalysisReconcileOutcomeEnum.LOCK_BUSY;
    }
    ErlGapAnalysisPlanDTO plan;
    try {
      // 2 ~ 7  规划：一个 REQUIRED 事务，必须经 self 走代理
      plan = self.plan(companyId, period, callerUserId, force);
    } finally {
      // 8  释放锁（规划抛异常也要放，否则要等 60s TTL）
      releasePlanLock(companyId, period);
    }
    if (plan.getRequest() == null) {
      return plan.getOutcome();
    }
    // 9  锁外、事务外的一次同步 HTTP；失败向上抛 —— 任务留 RUNNING，交给 10 分钟超龄规则重投
    ErlGapAnalysisResultDTO result = erlPythonClient.refresh(plan.getRequest(), bearerToken);
    self.applyResults(result, callerUserId);
    log.info("ERL gap analysis dispatched: companyId={}, period={}, tasks={}",
        companyId, period, plan.getRequest().getTasks().size());
    return plan.getOutcome();
  }

  @Override
  @Transactional(propagation = Propagation.REQUIRED, rollbackFor = Exception.class)
  public ErlGapAnalysisPlanDTO plan(String companyId, String period, String callerUserId, boolean force) {
    Map<String, ErlAssessment> founderRows = latestSubmitted(companyId, period, ErlPortalEnum.FOUNDER);
    Map<String, ErlAssessment> gsvRows = latestSubmitted(companyId, period, ErlPortalEnum.GSV);
    ErlDimensionConfigDTO config = erlDimensionConfigService.activeConfigOf(
        resolveConfigOrganizationId(companyId, founderRows, gsvRows));
    // 2  报告级门槛（D3）：不就绪 ⇒ 不建、不改任何行。两种成因分开记，排障时一眼看出是哪一种
    if (!allDimensionsSubmitted(config, founderRows, gsvRows)) {
      log.info("ERL gap analysis is not ready, some dimension is not submitted on both sides yet: "
          + "companyId={}, period={}", companyId, period);
      return ErlGapAnalysisPlanDTO.builder().outcome(ErlGapAnalysisReconcileOutcomeEnum.NOT_SUBMITTED).build();
    }
    if (!resolveQuestionSetMismatch(companyId, period, config, founderRows, gsvRows).isEmpty()) {
      log.info("ERL gap analysis is not ready, a dimension has a question set mismatch: companyId={}, period={}",
          companyId, period);
      return ErlGapAnalysisPlanDTO.builder().outcome(ErlGapAnalysisReconcileOutcomeEnum.MISMATCHED).build();
    }
    // 3  每维目标依据（两端 SOT id）与零感知差判定
    Map<String, TaskTarget> targets = targetSources(config, founderRows, gsvRows);
    ErlGapAnalysisReport latest = erlGapAnalysisReportRepository
        .findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(companyId, period)
        .orElse(null);
    // 4 / 5 / 6  建记录 / 已分享 ⇒ 新记录 + 复制 / 未分享 ⇒ 软删重建；返回值即「最新记录下的活任务」
    List<ErlGapAnalysisDimensionTask> activeTasks;
    if (latest == null) {
      activeTasks = createReportWithTasks(companyId, period, callerUserId, targets);
    } else if (Boolean.TRUE.equals(latest.getShared())) {
      activeTasks = forkSharedReport(latest, targets, callerUserId, force);
    } else {
      activeTasks = replaceTasksInUnsharedReport(latest, targets, callerUserId, force);
    }
    // 7  CAS 认领待派发任务
    List<ErlGapAnalysisDimensionTask> claimed = claimDispatchable(activeTasks, targets.keySet(), callerUserId);
    if (claimed.isEmpty()) {
      return ErlGapAnalysisPlanDTO.builder().outcome(ErlGapAnalysisReconcileOutcomeEnum.DONE).build();
    }
    return ErlGapAnalysisPlanDTO.builder()
        .outcome(ErlGapAnalysisReconcileOutcomeEnum.DONE)
        .request(buildInput(companyId, period, config, founderRows, gsvRows, claimed))
        .build();
  }

  @Override
  @Transactional(propagation = Propagation.REQUIRED, rollbackFor = Exception.class)
  public void applyResults(ErlGapAnalysisResultDTO result, String callerUserId) {
    if (result == null || result.getTasks() == null) {
      log.warn("ERL gap analysis refresh returned no task list, leaving the tasks RUNNING for the retry rule");
      return;
    }
    Instant now = Instant.now();
    int applied = 0;
    for (ErlGapAnalysisResultDTO.Task task : result.getTasks()) {
      if (StrUtil.isBlank(task.getTaskId())) {
        continue;
      }
      ErlGapAnalysisTaskStatusEnum to = ErlGapAnalysisTaskStatusEnum.terminalOf(task.getStatus());
      Boolean hasGap = to == ErlGapAnalysisTaskStatusEnum.SUCCESS ? Boolean.TRUE.equals(task.getHasGap()) : null;
      int updated = erlGapAnalysisDimensionTaskRepository.updateStatus(task.getTaskId(),
          ErlGapAnalysisTaskStatusEnum.RUNNING, to, hasGap, now, callerUserId);
      if (updated == 0) {
        // 迟到的结果 / 任务已被软删 / 已被别的线程改走：CAS 落空是设计内的正常路径（设计稿 §4）
        log.info("ERL gap analysis result ignored, task is no longer RUNNING: taskId={}, status={}",
            task.getTaskId(), task.getStatus());
        continue;
      }
      applied++;
    }
    log.info("ERL gap analysis results applied: applied={}, returned={}", applied, result.getTasks().size());
  }

  // ── 规划子步骤 ─────────────────────────────────────────────────────────

  /** 步骤 3：每个 Active 维度的目标依据。调用方已保证 ready（两端都有 SOT）。 */
  private Map<String, TaskTarget> targetSources(ErlDimensionConfigDTO config,
                                                Map<String, ErlAssessment> founderRows,
                                                Map<String, ErlAssessment> gsvRows) {
    Map<String, TaskTarget> targets = new LinkedHashMap<>();
    for (ErlDimensionConfigItemDTO item : config.getItems()) {
      String code = item.getDimensionCode();
      ErlAssessment founder = founderRows.get(code);
      ErlAssessment gsv = gsvRows.get(code);
      // 两端打分完全一致 ⇒ 不送 LLM，建任务时直接 SUCCESS + has_gap=false（判定只在 ErlScoreCalculator）
      targets.put(code, new TaskTarget(founder.getId(), gsv.getId(),
          ErlScoreCalculator.noPerceptionGap(founder.getLevelScore(), gsv.getLevelScore())));
    }
    return targets;
  }

  /** 步骤 4：首建 —— 一条记录 + 全维任务。 */
  private List<ErlGapAnalysisDimensionTask> createReportWithTasks(String companyId, String period,
                                                                  String callerUserId,
                                                                  Map<String, TaskTarget> targets) {
    ErlGapAnalysisReport report = newReport(companyId, period, callerUserId);
    List<ErlGapAnalysisDimensionTask> tasks = new ArrayList<>(targets.size());
    for (Map.Entry<String, TaskTarget> target : targets.entrySet()) {
      tasks.add(newTask(report.getId(), target.getKey(), target.getValue(), callerUserId));
    }
    List<ErlGapAnalysisDimensionTask> saved = erlGapAnalysisDimensionTaskRepository.saveAllAndFlush(tasks);
    log.info("ERL gap analysis report created: companyId={}, period={}, reportId={}, dimensions={}",
        companyId, period, report.getId(), targets.keySet());
    return saved;
  }

  /**
   * 步骤 5：最新记录已分享 ⇒ 记录不可变（I1）。有维度依据变了（或 force）才建新记录：
   * 变了的维度建新任务；没变的维度原任务 SUCCESS ⇒ 复制（{@code result_task_id} 指向持有内容的原任务），
   * 原任务非 SUCCESS ⇒ 不复制、建新任务重跑（复制品永远等不到回写到旧 id 的结果）。
   * 没有维度变化时什么都不建，返回原记录的活任务。
   */
  private List<ErlGapAnalysisDimensionTask> forkSharedReport(ErlGapAnalysisReport shared,
                                                             Map<String, TaskTarget> targets,
                                                             String callerUserId, boolean force) {
    List<ErlGapAnalysisDimensionTask> current = activeTasksOf(shared);
    Map<String, ErlGapAnalysisDimensionTask> byCode = indexTasksByCode(current);
    Set<String> changed = changedDimensions(targets, byCode, force);
    if (changed.isEmpty()) {
      return current;
    }
    ErlGapAnalysisReport fork = newReport(shared.getCompanyId(), shared.getPeriod(), callerUserId);
    List<ErlGapAnalysisDimensionTask> tasks = new ArrayList<>(targets.size());
    for (Map.Entry<String, TaskTarget> target : targets.entrySet()) {
      String code = target.getKey();
      ErlGapAnalysisDimensionTask original = byCode.get(code);
      if (!changed.contains(code) && original.getStatus() == ErlGapAnalysisTaskStatusEnum.SUCCESS) {
        tasks.add(copyTask(fork.getId(), original, callerUserId));
      } else {
        tasks.add(newTask(fork.getId(), code, target.getValue(), callerUserId));
      }
    }
    List<ErlGapAnalysisDimensionTask> saved = erlGapAnalysisDimensionTaskRepository.saveAllAndFlush(tasks);
    log.info("ERL gap analysis report forked from a shared one: companyId={}, period={}, sharedReportId={}, "
        + "reportId={}, changedDimensions={}", shared.getCompanyId(), shared.getPeriod(), shared.getId(),
        fork.getId(), changed);
    return saved;
  }

  /**
   * 步骤 6：最新记录未分享 ⇒ 就地更新：变了的维度（或 force ⇒ 全部）旧活任务软删、同记录下建新任务。
   * 软删必须在插入之前（部分唯一索引）。返回值 = 未变的旧任务 + 新任务。
   */
  private List<ErlGapAnalysisDimensionTask> replaceTasksInUnsharedReport(ErlGapAnalysisReport report,
                                                                         Map<String, TaskTarget> targets,
                                                                         String callerUserId, boolean force) {
    List<ErlGapAnalysisDimensionTask> current = activeTasksOf(report);
    Map<String, ErlGapAnalysisDimensionTask> byCode = indexTasksByCode(current);
    Set<String> changed = changedDimensions(targets, byCode, force);
    if (changed.isEmpty()) {
      return current;
    }
    List<String> replacedIds = new ArrayList<>();
    List<ErlGapAnalysisDimensionTask> kept = new ArrayList<>();
    for (ErlGapAnalysisDimensionTask task : current) {
      if (changed.contains(task.getDimensionCode())) {
        replacedIds.add(task.getId());
      } else {
        kept.add(task);
      }
    }
    if (!replacedIds.isEmpty()) {
      erlGapAnalysisDimensionTaskRepository.markDeleted(replacedIds, Instant.now(), callerUserId);
    }
    List<ErlGapAnalysisDimensionTask> created = new ArrayList<>(changed.size());
    for (String code : changed) {
      created.add(newTask(report.getId(), code, targets.get(code), callerUserId));
    }
    kept.addAll(erlGapAnalysisDimensionTaskRepository.saveAllAndFlush(created));
    log.info("ERL gap analysis tasks rebuilt in the unshared report: companyId={}, period={}, reportId={}, "
        + "changedDimensions={}, supersededTasks={}", report.getCompanyId(), report.getPeriod(), report.getId(),
        changed, replacedIds.size());
    return kept;
  }

  /**
   * 依据变了的维度：没有活任务、或任务的两端 source 与当前 SOT 任一不等；{@code force} ⇒ 全部。
   * 顺序按配置（{@code targets} 是 LinkedHashMap）。
   */
  private Set<String> changedDimensions(Map<String, TaskTarget> targets,
                                        Map<String, ErlGapAnalysisDimensionTask> byCode, boolean force) {
    Set<String> changed = new LinkedHashSet<>();
    for (Map.Entry<String, TaskTarget> target : targets.entrySet()) {
      ErlGapAnalysisDimensionTask task = byCode.get(target.getKey());
      if (force || task == null
          || !Objects.equals(task.getSourceFounderAssessmentId(), target.getValue().founderAssessmentId())
          || !Objects.equals(task.getSourceGsvAssessmentId(), target.getValue().gsvAssessmentId())) {
        changed.add(target.getKey());
      }
    }
    return changed;
  }

  /**
   * 步骤 7：待派发 = 当前 Active 维度的活任务里 {@code PENDING / FAILED / 超龄 RUNNING} 的那些，逐个
   * CAS → RUNNING；CAS 落空（rowcount 0）的不派发。不在 Active 集合里的任务（维度已停用）不碰 ——
   * 组装入参要它的配置项，而配置里已经没有它。
   */
  private List<ErlGapAnalysisDimensionTask> claimDispatchable(List<ErlGapAnalysisDimensionTask> activeTasks,
                                                              Set<String> activeCodes, String callerUserId) {
    Instant now = Instant.now();
    List<ErlGapAnalysisDimensionTask> claimed = new ArrayList<>();
    for (ErlGapAnalysisDimensionTask task : activeTasks) {
      if (!activeCodes.contains(task.getDimensionCode()) || !isDispatchable(task, now)) {
        continue;
      }
      int updated = erlGapAnalysisDimensionTaskRepository.updateStatus(task.getId(), task.getStatus(),
          ErlGapAnalysisTaskStatusEnum.RUNNING, null, now, callerUserId);
      if (updated == 0) {
        log.info("ERL gap analysis task claim lost the race, not dispatching: taskId={}, dimension={}",
            task.getId(), task.getDimensionCode());
        continue;
      }
      claimed.add(task);
    }
    return claimed;
  }

  /** 设计稿 §4 自愈规则；{@code updatedAt} 为空的 RUNNING（不该出现）按超龄处理，宁可多投一次。 */
  private boolean isDispatchable(ErlGapAnalysisDimensionTask task, Instant now) {
    return switch (task.getStatus()) {
      case PENDING, FAILED -> true;
      case RUNNING -> task.getUpdatedAt() == null
          || task.getUpdatedAt().isBefore(now.minus(RUNNING_STALE_AFTER));
      case SUCCESS -> false;
    };
  }

  private ErlGapAnalysisReport newReport(String companyId, String period, String callerUserId) {
    ErlGapAnalysisReport report = new ErlGapAnalysisReport();
    report.setCompanyId(companyId);
    report.setPeriod(period);
    report.setShared(Boolean.FALSE);
    // 异步线程上没有登录态：审计基类对已置的 createdBy / updatedBy 不覆盖（设计稿 §3.1）
    report.setCreatedBy(callerUserId);
    report.setUpdatedBy(callerUserId);
    return erlGapAnalysisReportRepository.save(report);
  }

  /** 新任务：零感知差 ⇒ 建行即 {@code SUCCESS + has_gap=false}（不经过 PENDING）；否则 {@code PENDING}。 */
  private ErlGapAnalysisDimensionTask newTask(String reportId, String code, TaskTarget target, String callerUserId) {
    ErlGapAnalysisDimensionTask task = new ErlGapAnalysisDimensionTask();
    task.setErlGapAnalysisReportId(reportId);
    task.setDimensionCode(code);
    task.setSourceFounderAssessmentId(target.founderAssessmentId());
    task.setSourceGsvAssessmentId(target.gsvAssessmentId());
    if (target.zeroPerceptionGap()) {
      task.setStatus(ErlGapAnalysisTaskStatusEnum.SUCCESS);
      task.setHasGap(Boolean.FALSE);
    } else {
      task.setStatus(ErlGapAnalysisTaskStatusEnum.PENDING);
    }
    task.setDeleted(Boolean.FALSE);
    task.setCreatedBy(callerUserId);
    task.setUpdatedBy(callerUserId);
    return task;
  }

  /** 复制任务（只对 SUCCESS 的原任务）：status / has_gap / source 照抄，{@code result_task_id = 原.result_task_id ?? 原.id}。 */
  private ErlGapAnalysisDimensionTask copyTask(String reportId, ErlGapAnalysisDimensionTask original,
                                               String callerUserId) {
    ErlGapAnalysisDimensionTask copy = new ErlGapAnalysisDimensionTask();
    copy.setErlGapAnalysisReportId(reportId);
    copy.setDimensionCode(original.getDimensionCode());
    copy.setSourceFounderAssessmentId(original.getSourceFounderAssessmentId());
    copy.setSourceGsvAssessmentId(original.getSourceGsvAssessmentId());
    copy.setStatus(original.getStatus());
    copy.setHasGap(original.getHasGap());
    copy.setResultTaskId(StrUtil.isNotBlank(original.getResultTaskId())
        ? original.getResultTaskId() : original.getId());
    copy.setDeleted(Boolean.FALSE);
    copy.setCreatedBy(callerUserId);
    copy.setUpdatedBy(callerUserId);
    return copy;
  }
```
- [ ] **Step 2: 紧接 Step 1 写入文件下半 —— 读路径、门槛、锁、输入组装、杂项（以类的 `}` 收尾）**

```java
  // ── 读路径（设计稿 §7）─────────────────────────────────────────────────

  /**
   * 接口 17 / 18 共用：SOT → 配置 → mismatch → 可见记录与活任务 → 一次批量取条目 → 组装。
   * 全部内容字段只从 {@code tasksByCode} / {@code items} 取，两端读的是同一套规则、不同的记录。
   */
  private ErlGapAnalysisDTO read(String companyId, String period, String dimension, boolean adminEnd) {
    Map<String, ErlAssessment> founderRows = latestSubmitted(companyId, period, ErlPortalEnum.FOUNDER);
    Map<String, ErlAssessment> gsvRows = latestSubmitted(companyId, period, ErlPortalEnum.GSV);
    ErlDimensionConfigDTO config = erlDimensionConfigService.activeConfigOf(
        resolveConfigOrganizationId(companyId, founderRows, gsvRows));
    Map<String, ErlPortalEnum> mismatchSides =
        resolveQuestionSetMismatch(companyId, period, config, founderRows, gsvRows);
    ErlGapAnalysisReport report = visibleReport(companyId, period, adminEnd);
    Map<String, ErlGapAnalysisDimensionTask> tasksByCode = indexTasksByCode(activeTasksOf(report));
    FetchedItems items = fetchItems(tasksByCode.values(), currentBearerToken());
    return assemble(config, dimension, founderRows, gsvRows, mismatchSides, report, tasksByCode, items, adminEnd);
  }

  /** 记录 + 任务 + 条目 + 配置 + SOT → 接口 17 / 18 的出参 DTO（设计稿 §7.2）。 */
  private ErlGapAnalysisDTO assemble(ErlDimensionConfigDTO config, String dimension,
                                     Map<String, ErlAssessment> founderRows,
                                     Map<String, ErlAssessment> gsvRows,
                                     Map<String, ErlPortalEnum> mismatchSides,
                                     ErlGapAnalysisReport report,
                                     Map<String, ErlGapAnalysisDimensionTask> tasksByCode,
                                     FetchedItems items, boolean adminEnd) {
    Map<String, ErlDimensionConfigItemDTO> configByCode = indexConfig(config);
    String scoped = normalizeCode(dimension);
    List<ErlGapDimensionDTO> dimensions = new ArrayList<>();
    for (String code : renderedCodes(config, tasksByCode, adminEnd, report != null)) {
      if (scoped != null && !scoped.equals(code)) {
        continue;
      }
      dimensions.add(toDimension(code, abbrOf(code, configByCode, founderRows, gsvRows),
          founderRows.get(code), gsvRows.get(code), mismatchSides, tasksByCode.get(code), items));
    }
    return ErlGapAnalysisDTO.builder()
        .dimensions(dimensions)
        // 下游故障要如实说，两端都下发：公司端同样需要知道是「坏了」而不是「在跑」
        .analysisServiceUnavailable(items.unavailable())
        // 管理端 = 最新记录.shared；公司端 visibleReport 只会给已分享记录，同一个表达式两端都对
        .shared(report != null && Boolean.TRUE.equals(report.getShared()))
        .shareable(adminEnd
            ? isShareable(config, founderRows, gsvRows, mismatchSides, toReportDTO(report, tasksByCode.values()))
            : null)
        .build();
  }

  /**
   * 要下发哪些维度：管理端遍历<b>当前 Active 维度</b>；公司端有已分享记录时<b>只遍历该记录里的任务</b>
   * （分享后新增的维度不下发 —— 消掉「新增维度渲染成绿点 No Gap」的假阴性，设计稿 §7.2），
   * 顺序按配置、停用维度排在最后；公司端没有记录时退回 Active 维度骨架，让空态照常按维度渲染小卡。
   */
  private Set<String> renderedCodes(ErlDimensionConfigDTO config,
                                    Map<String, ErlGapAnalysisDimensionTask> tasksByCode,
                                    boolean adminEnd, boolean hasReport) {
    Set<String> codes = new LinkedHashSet<>();
    if (adminEnd || !hasReport) {
      for (ErlDimensionConfigItemDTO item : config.getItems()) {
        codes.add(item.getDimensionCode());
      }
      return codes;
    }
    for (ErlDimensionConfigItemDTO item : config.getItems()) {
      if (tasksByCode.containsKey(item.getDimensionCode())) {
        codes.add(item.getDimensionCode());
      }
    }
    codes.addAll(tasksByCode.keySet());
    return codes;
  }

  /** 单维出参（设计稿 §7.2 维度级字段表）。四条状态信息互相独立，前端不要压成一个枚举。 */
  private ErlGapDimensionDTO toDimension(String code, String abbr, ErlAssessment founder, ErlAssessment gsv,
                                         Map<String, ErlPortalEnum> mismatchSides,
                                         ErlGapAnalysisDimensionTask task, FetchedItems items) {
    boolean analyzed = task != null && task.getStatus() == ErlGapAnalysisTaskStatusEnum.SUCCESS;
    boolean hasGap = analyzed && Boolean.TRUE.equals(task.getHasGap());
    ErlGapItemsResultDTO.Item item = hasGap ? items.byTaskId().get(contentTaskIdOf(task)) : null;
    return ErlGapDimensionDTO.builder()
        .dimensionCode(code)
        .dimensionAbbr(abbr)
        // 圆点颜色看它，口径必须与 allDimensionsSubmitted（门槛）一致
        .bothSubmitted(founder != null && gsv != null)
        // 分析过没有 = 活任务 SUCCESS；PENDING / RUNNING / FAILED 都是「在分析」（D9，前端 Analyzing…）
        .analyzed(analyzed)
        // 文字看它：取任务列 has_gap；未分析恒 false，语义由 analyzed 兜住
        .hasGap(hasGap)
        // 恒 false：任务依据变了走新任务 / 新记录，屏上不再有 Updating… 这一态；字段保留一版供前端兼容
        .dimensionStale(Boolean.FALSE)
        // 第三条独立信息：绝不能压进 hasGap（压进去就是绿点 No Gap 的假阴性）
        .questionSetMismatch(mismatchSides.containsKey(code))
        .mismatchSide(portalName(mismatchSides.get(code)))
        .narrative(item == null ? null : item.getNarrative())
        .gaps(toGapItems(code, item))
        .actions(toActionItems(code, item))
        .build();
  }

  /** 缩写：Active 维度取配置；公司端已分享记录里的停用维度取评估行上的提交时快照；都没有退回 code。 */
  private String abbrOf(String code, Map<String, ErlDimensionConfigItemDTO> configByCode,
                        Map<String, ErlAssessment> founderRows, Map<String, ErlAssessment> gsvRows) {
    ErlDimensionConfigItemDTO item = configByCode.get(code);
    if (item != null) {
      return item.getDimensionAbbr();
    }
    ErlAssessment snapshot = founderRows.get(code) != null ? founderRows.get(code) : gsvRows.get(code);
    return snapshot != null && StrUtil.isNotBlank(snapshot.getDimensionAbbr()) ? snapshot.getDimensionAbbr() : code;
  }

  private Map<String, ErlDimensionConfigItemDTO> indexConfig(ErlDimensionConfigDTO config) {
    Map<String, ErlDimensionConfigItemDTO> byCode = new LinkedHashMap<>();
    for (ErlDimensionConfigItemDTO item : config.getItems()) {
      byCode.put(item.getDimensionCode(), item);
    }
    return byCode;
  }

  /** {@code sortOrder} 取数组下标：Python 按 {@code sort_order} 排好序返回。 */
  private List<ErlGapItemDTO> toGapItems(String code, ErlGapItemsResultDTO.Item item) {
    if (item == null || item.getGaps() == null) {
      return List.of();
    }
    List<ErlGapItemDTO> items = new ArrayList<>(item.getGaps().size());
    for (ErlGapItemsResultDTO.Gap gap : item.getGaps()) {
      items.add(ErlGapItemDTO.builder()
          .dimensionCode(code)
          .itemType(ErlGapItemTypeEnum.GAP)
          .title(gap.getTitle())
          // 非法 severity 降级 MEDIUM（Python 只在 prompt 里约束，一条取值异常不该让整维渲染失败）
          .severity(ErlSeverityEnum.fromCodeOrDefault(gap.getSeverity()))
          .sortOrder(items.size())
          .build());
    }
    return items;
  }

  private List<ErlGapItemDTO> toActionItems(String code, ErlGapItemsResultDTO.Item item) {
    if (item == null || item.getActions() == null) {
      return List.of();
    }
    List<ErlGapItemDTO> items = new ArrayList<>(item.getActions().size());
    for (ErlGapItemsResultDTO.Action action : item.getActions()) {
      items.add(ErlGapItemDTO.builder()
          .dimensionCode(code)
          .itemType(ErlGapItemTypeEnum.ACTION)
          .title(action.getTitle())
          .sortOrder(items.size())
          .build());
    }
    return items;
  }

  /**
   * 一次批量取条目：只取 {@code SUCCESS ∧ has_gap = true} 的任务，按 {@code result_task_id ?? id}。
   * 没有可取的 ⇒ 不发请求、{@code unavailable = false}（空态不是故障）；取失败 ⇒ 记 WARN、
   * 内容为空、{@code unavailable = true}（前端走失败态 + Retry，而不是「正在分析」）。
   */
  private FetchedItems fetchItems(Collection<ErlGapAnalysisDimensionTask> tasks, String bearerToken) {
    Set<String> taskIds = new LinkedHashSet<>();
    for (ErlGapAnalysisDimensionTask task : tasks) {
      if (task.getStatus() == ErlGapAnalysisTaskStatusEnum.SUCCESS && Boolean.TRUE.equals(task.getHasGap())) {
        taskIds.add(contentTaskIdOf(task));
      }
    }
    if (taskIds.isEmpty()) {
      return new FetchedItems(Map.of(), false);
    }
    try {
      Map<String, ErlGapItemsResultDTO.Item> byTaskId = new LinkedHashMap<>();
      ErlGapItemsResultDTO result = erlPythonClient.fetchItems(new ArrayList<>(taskIds), bearerToken);
      for (ErlGapItemsResultDTO.Item item : result.getItems()) {
        if (StrUtil.isNotBlank(item.getTaskId())) {
          byTaskId.putIfAbsent(item.getTaskId(), item);
        }
      }
      return new FetchedItems(byTaskId, false);
    } catch (Exception e) {
      // reason 里带着客户端拼进异常消息的 HTTP 状态码（"... returned HTTP 401."），
      // 用来把「token 没传对」与「Python 真挂了」在日志上分开
      log.warn("ERL gap analysis items are unavailable, degrading to an empty block: taskIds={}, reason={}",
          taskIds, e.getMessage(), e);
      return new FetchedItems(Map.of(), true);
    }
  }

  /** 持有 Python 内容的任务 id：复制品指向原任务，其余就是自己。 */
  private static String contentTaskIdOf(ErlGapAnalysisDimensionTask task) {
    return StrUtil.isNotBlank(task.getResultTaskId()) ? task.getResultTaskId() : task.getId();
  }

  // ── 域内复用：接口 1 / 21 ────────────────────────────────────────────────

  @Override
  public ErlGapAnalysisReportDTO loadResult(String companyId, String period, boolean adminEnd) {
    ErlGapAnalysisReport report = visibleReport(companyId, period, adminEnd);
    return toReportDTO(report, activeTasksOf(report));
  }

  /**
   * {@code NOT_SUPPORTED}：本方法是一次 HTTP 往返（读超时 10s），而域内调用方（维度详情）的类级
   * {@code readOnly} 事务会让这段时间一直占着数据库连接。挂起事务把连接还回池里，跑完再恢复。
   */
  @Override
  @Transactional(propagation = Propagation.NOT_SUPPORTED)
  public List<ErlGapItemDTO> loadItems(String companyId, String period, String dimensionCode, boolean adminEnd) {
    ErlGapAnalysisDimensionTask task =
        indexTasksByCode(activeTasksOf(visibleReport(companyId, period, adminEnd))).get(dimensionCode);
    if (task == null) {
      return List.of();
    }
    FetchedItems items = fetchItems(List.of(task), currentBearerToken());
    ErlGapItemsResultDTO.Item item = items.byTaskId().get(contentTaskIdOf(task));
    List<ErlGapItemDTO> result = new ArrayList<>(toGapItems(dimensionCode, item));
    result.addAll(toActionItems(dimensionCode, item));
    return result;
  }

  /** 选行只此一处（设计稿 §7.1）：管理端最新记录；公司端最新已分享记录。期次解不出 ⇒ 无记录。 */
  private ErlGapAnalysisReport visibleReport(String companyId, String period, boolean adminEnd) {
    if (StrUtil.isBlank(companyId) || StrUtil.isBlank(period)) {
      return null;
    }
    return (adminEnd
        ? erlGapAnalysisReportRepository.findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(companyId, period)
        : erlGapAnalysisReportRepository
            .findFirstByCompanyIdAndPeriodAndSharedTrueOrderByCreatedAtDescIdDesc(companyId, period))
        .orElse(null);
  }

  private List<ErlGapAnalysisDimensionTask> activeTasksOf(ErlGapAnalysisReport report) {
    return report == null ? List.of()
        : erlGapAnalysisDimensionTaskRepository.findByErlGapAnalysisReportIdAndDeletedFalse(report.getId());
  }

  /** 同一 code 重复出现时取第一条：部分唯一索引保证不会重复，这里只是不让重复项把前一条挤掉。 */
  private Map<String, ErlGapAnalysisDimensionTask> indexTasksByCode(List<ErlGapAnalysisDimensionTask> tasks) {
    Map<String, ErlGapAnalysisDimensionTask> byCode = new LinkedHashMap<>();
    for (ErlGapAnalysisDimensionTask task : tasks) {
      byCode.putIfAbsent(task.getDimensionCode(), task);
    }
    return byCode;
  }

  private ErlGapAnalysisReportDTO toReportDTO(ErlGapAnalysisReport report,
                                              Collection<ErlGapAnalysisDimensionTask> tasks) {
    if (report == null) {
      return null;
    }
    List<ErlGapAnalysisReportDTO.Task> taskDTOs = new ArrayList<>(tasks.size());
    for (ErlGapAnalysisDimensionTask task : tasks) {
      taskDTOs.add(ErlGapAnalysisReportDTO.Task.builder()
          .taskId(task.getId())
          .dimensionCode(task.getDimensionCode())
          .status(task.getStatus())
          .hasGap(task.getHasGap())
          .resultTaskId(task.getResultTaskId())
          .sourceFounderAssessmentId(task.getSourceFounderAssessmentId())
          .sourceGsvAssessmentId(task.getSourceGsvAssessmentId())
          .build());
    }
    return ErlGapAnalysisReportDTO.builder()
        .reportId(report.getId())
        .shared(Boolean.TRUE.equals(report.getShared()))
        .tasks(taskDTOs)
        .build();
  }

  // ── 门槛 ───────────────────────────────────────────────────────────────

  @Override
  public boolean isShareable(ErlDimensionConfigDTO config,
                             Map<String, ErlAssessment> founderRows,
                             Map<String, ErlAssessment> gsvRows,
                             Map<String, ErlPortalEnum> mismatchSides,
                             ErlGapAnalysisReportDTO report) {
    // ① ready：每个 Active 维度两端都 SUBMITTED 且无 mismatch
    if (!allDimensionsSubmitted(config, founderRows, gsvRows) || !mismatchSides.isEmpty()) {
      return false;
    }
    // ② 最新记录存在 ③ 未分享
    if (report == null || Boolean.TRUE.equals(report.getShared())) {
      return false;
    }
    Map<String, ErlGapAnalysisReportDTO.Task> byCode = new LinkedHashMap<>();
    if (report.getTasks() != null) {
      for (ErlGapAnalysisReportDTO.Task task : report.getTasks()) {
        byCode.putIfAbsent(task.getDimensionCode(), task);
      }
    }
    // ④ 每个 Active 维度的活任务都 SUCCESS ⑤ 每维任务的 source == 当前 SOT
    for (ErlDimensionConfigItemDTO item : config.getItems()) {
      String code = item.getDimensionCode();
      ErlGapAnalysisReportDTO.Task task = byCode.get(code);
      if (task == null || task.getStatus() != ErlGapAnalysisTaskStatusEnum.SUCCESS) {
        return false;
      }
      if (!Objects.equals(task.getSourceFounderAssessmentId(), founderRows.get(code).getId())
          || !Objects.equals(task.getSourceGsvAssessmentId(), gsvRows.get(code).getId())) {
        return false;
      }
    }
    return true;
  }

  /**
   * 报告级门槛的前半（D3，回到 PRD:193「所有维度两方都完成」）：该组织每一个 Active 维度的两端都有
   * SUBMITTED 记录。配置为空时不就绪。
   */
  private boolean allDimensionsSubmitted(ErlDimensionConfigDTO config,
                                         Map<String, ErlAssessment> founderRows,
                                         Map<String, ErlAssessment> gsvRows) {
    List<ErlDimensionConfigItemDTO> items = config.getItems();
    if (items.isEmpty()) {
      return false;
    }
    for (ErlDimensionConfigItemDTO item : items) {
      if (founderRows.get(item.getDimensionCode()) == null || gsvRows.get(item.getDimensionCode()) == null) {
        return false;
      }
    }
    return true;
  }

  // ── 题库版本 mismatch（P4，设计 §7）────────────────────────────────────

  @Override
  public Map<String, ErlPortalEnum> resolveQuestionSetMismatch(String companyId, String period,
                                                               ErlDimensionConfigDTO config,
                                                               Map<String, ErlAssessment> founderRows,
                                                               Map<String, ErlAssessment> gsvRows) {
    List<ErlDimensionConfigItemDTO> items = config.getItems();
    if (items.isEmpty()) {
      return Map.of();
    }
    // 两端绑定的发布批次一次 IN 查全：按维度循环查就是 N+1（coding.md §10）
    Set<String> versionIds = new LinkedHashSet<>();
    for (ErlDimensionConfigItemDTO item : items) {
      collectBoundVersionId(versionIds, founderRows.get(item.getDimensionCode()));
      collectBoundVersionId(versionIds, gsvRows.get(item.getDimensionCode()));
    }
    Map<String, Map<String, Integer>> versionNos =
        erlQuestionConfigVersionService.questionVersionNosOf(versionIds);

    Map<String, ErlPortalEnum> mismatchSides = new LinkedHashMap<>();
    // 解不出的 (维度:端) 逐个收集、循环后聚合成一条 WARN（快照行缺失是不会自愈的数据问题，别刷屏）
    List<String> unresolved = new ArrayList<>();
    for (ErlDimensionConfigItemDTO item : items) {
      String code = item.getDimensionCode();
      ErlAssessment founder = founderRows.get(code);
      ErlAssessment gsv = gsvRows.get(code);
      if (founder == null || gsv == null) {
        // 未提交态由 bothSubmitted 表达，这里既不判 mismatch 也不打 WARN（§7.3）
        continue;
      }
      Integer founderNo = questionVersionNo(versionNos, founder, code);
      Integer gsvNo = questionVersionNo(versionNos, gsv, code);
      if (founderNo == null) {
        unresolved.add(code + ":" + ErlPortalEnum.FOUNDER);
      }
      if (gsvNo == null) {
        unresolved.add(code + ":" + ErlPortalEnum.GSV);
      }
      if (founderNo == null || gsvNo == null) {
        // fail-open（§7.8）：只有两端都解得出才比较
        continue;
      }
      if (!founderNo.equals(gsvNo)) {
        // 落后的一端 = 版本号较小的那一端（= 未提交本季度新版本问卷的一方，§7.3）
        mismatchSides.put(code, founderNo < gsvNo ? ErlPortalEnum.FOUNDER : ErlPortalEnum.GSV);
      }
    }
    if (!unresolved.isEmpty()) {
      log.warn("ERL question set versions are unresolved, continuing without a mismatch flag: "
          + "companyId={}, period={}, unresolved={}", companyId, period, unresolved);
    }
    return mismatchSides;
  }

  /** 该端该维绑定的题集版本号；解不出返回 null（绝不当成 0 —— 0 是「该版下一道题都没有」的真实取值）。 */
  private Integer questionVersionNo(Map<String, Map<String, Integer>> versionNos,
                                    ErlAssessment assessment, String dimensionCode) {
    String versionId = boundVersionId(assessment);
    if (versionId == null) {
      return null;
    }
    return versionNos.getOrDefault(versionId, Map.of()).get(dimensionCode);
  }

  private void collectBoundVersionId(Set<String> versionIds, ErlAssessment assessment) {
    String versionId = boundVersionId(assessment);
    if (versionId != null) {
      versionIds.add(versionId);
    }
  }

  private String boundVersionId(ErlAssessment assessment) {
    if (assessment == null || StrUtil.isBlank(assessment.getErlQuestionConfigVersionId())) {
      return null;
    }
    return assessment.getErlQuestionConfigVersionId();
  }

  // ── Redis：规划锁与冷却 ────────────────────────────────────────────────

  /**
   * 规划锁（设计稿 §5 步骤 1）：SETNX 60s。Redis 抖动时 <b>fail-open</b>（当成拿到）：并发规划的最坏后果是
   * 部分唯一索引撞键让后到的事务回滚，而 fail-close 会让整条生成链路在 Redis 故障期间停摆。
   */
  private boolean acquirePlanLock(String companyId, String period) {
    String key = PLAN_LOCK_KEY_PREFIX + companyId + ":" + period;
    try {
      return Boolean.TRUE.equals(stringRedisTemplate.opsForValue()
          .setIfAbsent(key, "1", PLAN_LOCK_SECONDS, TimeUnit.SECONDS));
    } catch (Exception e) {
      log.warn("ERL gap analysis plan lock is unavailable, planning anyway: companyId={}, period={}, reason={}",
          companyId, period, e.getMessage(), e);
      return true;
    }
  }

  /** 释放规划锁；失败只记 WARN（TTL 60s 兜底）。 */
  private void releasePlanLock(String companyId, String period) {
    String key = PLAN_LOCK_KEY_PREFIX + companyId + ":" + period;
    try {
      stringRedisTemplate.delete(key);
    } catch (Exception e) {
      log.warn("ERL gap analysis plan lock could not be released, waiting for its TTL: companyId={}, period={}, "
          + "reason={}", companyId, period, e.getMessage(), e);
    }
  }

  /**
   * 触发点 ② 的<b>投递冷却</b>：同 (company, period) 60 秒内只投一次。它防的是「前端 5s × 24 轮询把
   * 读接口的写副作用放大成每 5 秒一轮的对账」。只管触发点 ②：① ③ 都是用户的真实动作，不查冷却。
   * Redis 抖动时 fail-open（当成拿到）：节流失效只是多规划几次，fail-close 会让自愈安全网停摆。
   */
  private boolean acquireRegenerationCooldown(String companyId, String period) {
    String key = REGENERATION_COOLDOWN_KEY_PREFIX + companyId + ":" + period;
    try {
      if (Boolean.TRUE.equals(stringRedisTemplate.opsForValue()
          .setIfAbsent(key, "1", REGENERATION_COOLDOWN_SECONDS, TimeUnit.SECONDS))) {
        return true;
      }
      // 正常路径（页面轮询期间每 5 秒撞一次），记 DEBUG 不记 INFO，免得刷屏
      log.debug("ERL gap analysis reconciliation is still cooling down, not redelivering: companyId={}, period={}",
          companyId, period);
      return false;
    } catch (Exception e) {
      log.warn("ERL gap analysis reconciliation cooldown is unavailable, redelivering anyway: "
          + "companyId={}, period={}, reason={}", companyId, period, e.getMessage(), e);
      return true;
    }
  }

  // ── 输入组装 ───────────────────────────────────────────────────────────

  /** 该端该期次全部维度的 SOT 记录，按维度归组（一次查全，不按维度循环）。 */
  private Map<String, ErlAssessment> latestSubmitted(String companyId, String period, ErlPortalEnum portal) {
    Map<String, ErlAssessment> rows = new LinkedHashMap<>();
    if (StrUtil.isBlank(companyId) || StrUtil.isBlank(period)) {
      return rows;
    }
    // 「最新一次提交」= submitted_at DESC, id DESC 首条（§5.2），只走 repository 的这一个方法
    for (ErlAssessment assessment : erlAssessmentRepository.findLatestSubmittedByCompanyAndPeriodAndPortal(
        companyId, period, portal, ErlAssessmentStatusEnum.SUBMITTED)) {
      rows.put(assessment.getDimensionCode(), assessment);
    }
    return rows;
  }

  /**
   * 组装 refresh 入参（设计稿 §6.1）：<b>只装刚认领的任务</b>，每个任务 = 一维双端 level 分 + 止步 level
   * + 逐题作答（题目一律取各自评估绑定的题库版本，按跨版本稳定的 {@code questionKey} 对齐）。
   * 作答 / 题目 / 附件三批查询只针对这些维度的评估行。
   */
  private ErlGapAnalysisRequestDTO buildInput(String companyId, String period, ErlDimensionConfigDTO config,
                                              Map<String, ErlAssessment> founderRows,
                                              Map<String, ErlAssessment> gsvRows,
                                              List<ErlGapAnalysisDimensionTask> claimed) {
    Map<String, ErlDimensionConfigItemDTO> configByCode = indexConfig(config);
    Map<String, BigDecimal> weights = erlDimensionConfigService.weightsOf(config);
    List<ErlAssessment> loaded = new ArrayList<>(claimed.size() * 2);
    for (ErlGapAnalysisDimensionTask task : claimed) {
      loaded.add(founderRows.get(task.getDimensionCode()));
      loaded.add(gsvRows.get(task.getDimensionCode()));
    }
    Map<String, Map<String, ErlAssessmentAnswer>> answers = loadAnswers(loaded);
    Map<String, List<ErlQuestionConfig>> questionsByAssessment = loadQuestions(loaded);
    Map<String, List<ErlAttachmentDTO>> attachments = loadAttachments(answers);

    List<ErlGapAnalysisRequestDTO.Task> tasks = new ArrayList<>(claimed.size());
    for (ErlGapAnalysisDimensionTask task : claimed) {
      String code = task.getDimensionCode();
      ErlDimensionConfigItemDTO item = configByCode.get(code);
      ErlAssessment founder = founderRows.get(code);
      ErlAssessment gsv = gsvRows.get(code);
      tasks.add(ErlGapAnalysisRequestDTO.Task.builder()
          // 只给 Python 落日志行与条目用，不进 prompt（设计稿 §6.1 第 4 条）
          .taskId(task.getId())
          .name(item.getDimensionName())
          .abbr(item.getDimensionAbbr())
          .weight(weights.get(code))
          .founderLevelScore(founder.getLevelScore())
          .gsvLevelScore(gsv.getLevelScore())
          .perceptionGap(ErlScoreCalculator.perceptionGap(founder.getLevelScore(), gsv.getLevelScore()))
          .founderTerminatedLevel(founder.getTerminatedLevel())
          .gsvTerminatedLevel(gsv.getTerminatedLevel())
          .questions(buildQuestions(code,
              questionsOf(questionsByAssessment, founder), answersOf(answers, founder),
              questionsOf(questionsByAssessment, gsv), answersOf(answers, gsv), attachments))
          .build());
    }
    return ErlGapAnalysisRequestDTO.builder()
        .companyId(companyId)
        .period(period)
        .tasks(tasks)
        .build();
  }

  /** 一次批量取全部评估的作答，按 {@code assessmentId -> questionId} 索引。 */
  private Map<String, Map<String, ErlAssessmentAnswer>> loadAnswers(List<ErlAssessment> assessments) {
    Map<String, Map<String, ErlAssessmentAnswer>> indexed = new LinkedHashMap<>();
    List<String> assessmentIds = new ArrayList<>(assessments.size());
    for (ErlAssessment assessment : assessments) {
      assessmentIds.add(assessment.getId());
    }
    if (assessmentIds.isEmpty()) {
      return indexed;
    }
    for (ErlAssessmentAnswer answer : erlAssessmentAnswerRepository.findByErlAssessmentIdIn(assessmentIds)) {
      indexed.computeIfAbsent(answer.getErlAssessmentId(), key -> new LinkedHashMap<>())
          .put(answer.getErlQuestionConfigId(), answer);
    }
    return indexed;
  }

  /** 一次批量取本轮全部作答的附件，按 {@code answerId} 归组；没有作答时不发空查询。 */
  private Map<String, List<ErlAttachmentDTO>> loadAttachments(
      Map<String, Map<String, ErlAssessmentAnswer>> answers) {
    Set<String> answerIds = new LinkedHashSet<>();
    for (Map<String, ErlAssessmentAnswer> byQuestion : answers.values()) {
      for (ErlAssessmentAnswer answer : byQuestion.values()) {
        answerIds.add(answer.getId());
      }
    }
    if (answerIds.isEmpty()) {
      return Map.of();
    }
    return erlAttachmentService.findByAnswerIds(answerIds);
  }

  /** 预取题目，key 为评估 id；同 {@code (版本行 id, 维度)} 只查一次（两端评估通常绑同一版同一维）。 */
  private Map<String, List<ErlQuestionConfig>> loadQuestions(List<ErlAssessment> assessments) {
    Map<String, List<ErlQuestionConfig>> byAssessment = new LinkedHashMap<>();
    Map<String, List<ErlQuestionConfig>> cache = new LinkedHashMap<>();
    for (ErlAssessment assessment : assessments) {
      if (assessment == null) {
        continue;
      }
      String key = assessment.getErlQuestionConfigVersionId() + "#" + assessment.getDimensionCode();
      byAssessment.put(assessment.getId(), cache.computeIfAbsent(key, ignored ->
          erlQuestionConfigVersionService.questionsOf(
              assessment.getErlQuestionConfigVersionId(),
              assessment.getErlQuestionConfigDimensionVersionId(), assessment.getDimensionCode())));
    }
    return byAssessment;
  }

  private Map<String, ErlAssessmentAnswer> answersOf(Map<String, Map<String, ErlAssessmentAnswer>> answers,
                                                     ErlAssessment assessment) {
    return assessment == null ? Collections.<String, ErlAssessmentAnswer>emptyMap()
        : answers.getOrDefault(assessment.getId(), Collections.emptyMap());
  }

  private List<ErlQuestionConfig> questionsOf(Map<String, List<ErlQuestionConfig>> questionsByAssessment,
                                              ErlAssessment assessment) {
    return assessment == null ? Collections.<ErlQuestionConfig>emptyList()
        : questionsByAssessment.getOrDefault(assessment.getId(), Collections.emptyList());
  }

  /** 该维的逐题输入：两端题目按 {@code questionKey} 取并集，Founder 版本的顺序在前。 */
  private List<ErlGapAnalysisRequestDTO.Question> buildQuestions(String dimension,
                                                                 List<ErlQuestionConfig> founderQuestions,
                                                                 Map<String, ErlAssessmentAnswer> founderAnswers,
                                                                 List<ErlQuestionConfig> gsvQuestions,
                                                                 Map<String, ErlAssessmentAnswer> gsvAnswers,
                                                                 Map<String, List<ErlAttachmentDTO>> attachments) {
    Map<String, ErlQuestionConfig> founderByKey = indexByQuestionKey(founderQuestions, dimension);
    Map<String, ErlQuestionConfig> gsvByKey = indexByQuestionKey(gsvQuestions, dimension);
    LinkedHashSet<String> questionKeys = new LinkedHashSet<>(founderByKey.keySet());
    questionKeys.addAll(gsvByKey.keySet());

    List<ErlGapAnalysisRequestDTO.Question> questions = new ArrayList<>(questionKeys.size());
    for (String questionKey : questionKeys) {
      ErlQuestionConfig founderQuestion = founderByKey.get(questionKey);
      ErlQuestionConfig gsvQuestion = gsvByKey.get(questionKey);
      ErlQuestionConfig template = founderQuestion != null ? founderQuestion : gsvQuestion;
      ErlAssessmentAnswer founderAnswer = founderQuestion == null ? null : founderAnswers.get(founderQuestion.getId());
      ErlAssessmentAnswer gsvAnswer = gsvQuestion == null ? null : gsvAnswers.get(gsvQuestion.getId());
      questions.add(ErlGapAnalysisRequestDTO.Question.builder()
          .questionText(template.getQuestionText())
          .eraBand(template.getEraBand())
          .eraLabel(ErlEraEnum.bandLabel(template.getEraBand()))
          .evidenceSource(template.getEvidenceSource())
          .founderYesNo(founderAnswer == null ? null : founderAnswer.getYesNo())
          .gsvYesNo(gsvAnswer == null ? null : gsvAnswer.getYesNo())
          .founderNote(founderAnswer == null ? null : founderAnswer.getNote())
          .gsvNote(gsvAnswer == null ? null : gsvAnswer.getNote())
          .attachments(mergeAttachments(founderAnswer, gsvAnswer, attachments))
          .build());
    }
    return questions;
  }

  /** 该题两端附件的并集：Founder 端在前，按 {@code fileId} 去重；无附件返回空数组而不是 null。 */
  private List<ErlGapAnalysisRequestDTO.Attachment> mergeAttachments(
      ErlAssessmentAnswer founderAnswer, ErlAssessmentAnswer gsvAnswer,
      Map<String, List<ErlAttachmentDTO>> attachments) {
    List<ErlGapAnalysisRequestDTO.Attachment> merged = new ArrayList<>();
    Set<String> seenFileIds = new HashSet<>();
    for (ErlAssessmentAnswer answer : new ErlAssessmentAnswer[] {founderAnswer, gsvAnswer}) {
      if (answer == null) {
        continue;
      }
      for (ErlAttachmentDTO attachment : attachments.getOrDefault(answer.getId(), List.of())) {
        if (StrUtil.isBlank(attachment.getFileId()) || !seenFileIds.add(attachment.getFileId())) {
          continue;
        }
        merged.add(ErlGapAnalysisRequestDTO.Attachment.builder()
            .fileId(attachment.getFileId())
            // files 行已被清理时文件名为 null，照原样下发：Python 按扩展名选 loader，没有文件名判该附件无摘要
            .fileName(attachment.getFileName())
            .build());
      }
    }
    return merged;
  }

  private Map<String, ErlQuestionConfig> indexByQuestionKey(List<ErlQuestionConfig> questions, String dimension) {
    Map<String, ErlQuestionConfig> indexed = new LinkedHashMap<>();
    for (ErlQuestionConfig question : questions) {
      if (dimension.equals(question.getDimensionCode())) {
        indexed.put(question.getQuestionKey(), question);
      }
    }
    return indexed;
  }

  // ── 杂项 ───────────────────────────────────────────────────────────────

  /**
   * 读写路径取配置用的组织：<b>有 SOT 行就按 SOT 行反解，解不出才按公司反查</b>。两条路径若给出不同组织，
   * Active 维度集合就不同，报告级门槛与出参骨架会各说各的。异步线程也因此不依赖登录态。
   */
  private String resolveConfigOrganizationId(String companyId, Map<String, ErlAssessment> founderRows,
                                             Map<String, ErlAssessment> gsvRows) {
    String organizationId = organizationOf(founderRows, gsvRows);
    return StrUtil.isNotBlank(organizationId) ? organizationId
        : erlAccessService.resolveOrganizationIdByCompany(companyId);
  }

  /** 从本轮取到的评估行反解组织：评估绑定的题库版本行上有 {@code organization_id}；一条提交都没有时返回 null。 */
  private String organizationOf(Map<String, ErlAssessment> founderRows, Map<String, ErlAssessment> gsvRows) {
    for (Map<String, ErlAssessment> rows : List.of(founderRows, gsvRows)) {
      for (ErlAssessment assessment : rows.values()) {
        String organizationId = erlQuestionConfigVersionService
            .organizationOf(assessment.getErlQuestionConfigVersionId());
        if (StrUtil.isNotBlank(organizationId)) {
          return organizationId;
        }
      }
    }
    return null;
  }

  /** 落后一端的出参取值：{@code FOUNDER} / {@code GSV}；不 mismatch 时不下发（null）。 */
  private static String portalName(ErlPortalEnum portal) {
    return portal == null ? null : portal.name();
  }

  /** 接口 17 的 {@code dimension} 查询参数归一：去空白 + 转大写，空白返回 null。 */
  private static String normalizeCode(String code) {
    return StrUtil.isBlank(code) ? null : code.trim().toUpperCase();
  }

  /**
   * 在<b>请求线程</b>里捕获调用者的 Bearer token（口径同 {@code ErlAssessmentServiceImpl.currentBearerToken()}）：
   * Python 侧每个接口都走 AuthMiddleware，没有 token 一律 401。异步线程没有请求上下文，
   * {@link #reconcileAsync} 的 token 一律由调用方作为入参传入。
   */
  private String currentBearerToken() {
    RequestAttributes attributes = RequestContextHolder.getRequestAttributes();
    if (!(attributes instanceof ServletRequestAttributes servletAttributes)) {
      return null;
    }
    return servletAttributes.getRequest().getHeader(HttpHeaders.AUTHORIZATION);
  }
}
```

- [ ] **Step 3: 轻量校验**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests 2>&1 | grep -E "ERROR.*\.java" | sed -E 's/.*erl\///' | sort -u
```
期望：报错清单只剩 `service/ErlCardServiceImpl.java`、`service/ErlDimensionServiceImpl.java`、`service/ErlAssessmentServiceImpl.java`（三处消费方仍在调已删除的 `loadResult(companyId, period)` / `visibleArtifact` / `regenerate`）。若本文件自身报错，按行号回到 Step 1 / Step 2 对照修正（常见：漏 import `Collection` / `PageRequest`、`switch` 表达式的 `case` 未穷举）。

---
### Task 9: 触发点与消费方（Assessment / Card / Dimension / Controller / Javadoc）—— 编译收口

**Files:**
- Modify: `erl/service/ErlAssessmentServiceImpl.java:299-300,893-909`
- Modify: `erl/service/ErlCardServiceImpl.java:3-34（import）,54-55,80-153,172-235,351-392`
- Modify: `erl/service/ErlDimensionServiceImpl.java:12,32（import）,122-144,480-561`
- Modify: `erl/controller/ErlGapAnalysisController.java:65-70`
- Modify: `erl/entity/ErlDimensionConfig.java:54-60`

- [ ] **Step 1: `ErlAssessmentServiceImpl.submit` 触发点 ① 改口（:299-300）**

把
```java
    String bearerToken = currentBearerToken();
    regenerateGapAnalysisAfterCommit(resolvedCompanyId, period, bearerToken);
```
改为
```java
    // 触发点 ①（任务化设计 §5）：提交事务提交后异步对账。⚠️ token 与 userId 都要在**请求线程**里捕获：
    // ioExecutor 线程上没有请求上下文也没有登录态，新建记录 / 任务的 created_by 全靠这里传下去的 userId
    reconcileGapAnalysisAfterCommit(resolvedCompanyId, period,
        erlAccessService.currentCaller().getUserId(), currentBearerToken());
```

- [ ] **Step 2: `ErlAssessmentServiceImpl` 的投递方法整段替换（:893-909）**

```java
  /**
   * 提交成功后异步触发差距分析对账（触发点 ①，任务化设计 §5；取代 2026-09-24 之前的 {@code regenerate}）。
   *
   * <p>对账本身跑在 {@code ioExecutor} 上（{@code ErlGapAnalysisService#reconcileAsync}），这里只是把它排进
   * 事务提交后的回调：报告级门槛（全部 Active 维度两端都交齐）没达成时它自己会收手、不建任何行。
   * {@code cio.erl.ai-enabled=false} 的短路也在它里面。</p>
   */
  private void reconcileGapAnalysisAfterCommit(String companyId, String period, String callerUserId,
                                               String bearerToken) {
    AfterCommitExecutor.execute(() -> {
      try {
        erlGapAnalysisService.reconcileAsync(companyId, period, callerUserId, bearerToken);
      } catch (Exception e) {
        // 排不进线程池（拒绝策略 / 代理异常）只记日志，绝不影响已提交的评估（§7.5 / §9）
        log.error("ERL gap analysis reconciliation could not be scheduled, companyId={}, period={}",
            companyId, period, e);
      }
    });
  }
```

- [ ] **Step 3: `ErlCardServiceImpl` import 与常量**

- :8 `import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;` → 改为 `import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisReportDTO;`
- 在 :16 `import com.gstdev.cioaas.web.erl.enums.ErlDimensionConfigStatusEnum;` 之后新增一行 `import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisTaskStatusEnum;`
- 删除 :29 `import java.util.HashSet;` 与 :34 `import java.util.Set;`（下面重写后两者不再使用）
- 删除 :54-55 的常量：
```java
  /** 卡片内摘要的截断长度（§6.1「截断展示」）。 */
  private static final int GAP_SUMMARY_MAX_LENGTH = 240;
```
- :72 字段注释 `/** 差距分析产物在 Python 侧，域内一律经本服务取（architecture.md §1.1 / §1.3）。 */` 改为 `/** 差距分析的记录与任务在本域两张表里，Card 一律经本服务取（选行口径只此一处），不调 Python。 */`

- [ ] **Step 4: `ErlCardServiceImpl.getCard` 整方法替换（:80-153）**

```java
  @Override
  public ErlCardDTO getCard(String requestedCompanyId, String requestedPeriod) {
    String companyId = erlAccessService.resolveCompanyId(requestedCompanyId);
    boolean adminEnd = erlAccessService.currentCaller().isAdminEnd();
    String period = erlPeriodService.resolvePeriod(companyId, requestedPeriod);
    // 配置跟着被看的公司走（理由同 ErlDimensionServiceImpl.listAll）
    String organizationId = erlAccessService.resolveOrganizationIdByCompany(companyId);
    ErlDimensionConfigDTO config = erlDimensionConfigService.activeConfigOf(organizationId);
    if (StrUtil.isBlank(period)) {
      // 期次定不下来（companyId 为空这一种防御分支）：空态 + 期次为 null。
      // closed month 取不到已不再走这里 —— 2026-09-15 起回退当前自然季度（§7.1.2）
      return emptyCard(companyId, null, organizationId, config, adminEnd);
    }

    Map<String, ErlAssessment> founderRows = latestSubmitted(companyId, period, ErlPortalEnum.FOUNDER);
    Map<String, ErlAssessment> gsvRows = latestSubmitted(companyId, period, ErlPortalEnum.GSV);
    if (founderRows.isEmpty() && gsvRows.isEmpty()) {
      // 该季度两端均无提交：空态，明确不回退到更早期次（§0.10-R3）
      return emptyCard(companyId, period, organizationId, config, adminEnd);
    }

    // 2026-09-24（任务化，设计稿 §7.3）：接口 1 **不调 Python**。这一端可见的记录 + 活任务全在 Java 表里，
    // 选行口径收在 gap 服务的 loadResult 一处（管理端最新记录 / 公司端最新已分享记录），
    // 小卡的 hasGap 直接读任务行 —— 与接口 17 同源，了结「接口 1 与 17 对 hasGap 口径不一致」那条台账
    ErlGapAnalysisReportDTO report = erlGapAnalysisService.loadResult(companyId, period, adminEnd);
    Map<String, ErlGapAnalysisReportDTO.Task> tasksByCode = indexTasks(report);
    // 题库版本 mismatch 判定与接口 17 同源（P4，§7.10），复用上面已查出的两端 SOT 行
    Map<String, ErlPortalEnum> mismatchSides =
        erlGapAnalysisService.resolveQuestionSetMismatch(companyId, period, config, founderRows, gsvRows);
    List<ErlDimensionScoreDTO> dimensions =
        buildDimensions(companyId, period, organizationId, config, founderRows, gsvRows,
            tasksByCode, mismatchSides, adminEnd);
    BigDecimal overallScore = ErlLevelScorer.computeOverall(
        displayedLevelScores(dimensions, adminEnd), erlDimensionConfigService.weightsOf(config));

    return ErlCardDTO.builder()
      .period(period)
      .overallScore(overallScore)
      .stage(ErlScoreCalculator.stageOf(overallScore))
      .era(ErlScoreCalculator.eraLabelOf(overallScore))
      // BPMM 在 V1 无任何数据源（design-doc §13-Q1 仍是待产品确认项），下发 null 让前端隐藏该行。
      .bpmmScore(null)
      // 管理端 = 最新记录.shared；公司端 loadResult 只会给已分享记录 ⇒ 有记录即已分享，同一表达式两端都对
      .shared(report != null && Boolean.TRUE.equals(report.getShared()))
      // 门槛五条与接口 17 / 27 同走一个方法（§7.10），复用上面取到的那一份记录，不重取
      .shareable(adminEnd
          ? erlGapAnalysisService.isShareable(config, founderRows, gsvRows, mismatchSides, report) : null)
      .hasAnyAssessment(Boolean.TRUE)
      .weightsApplied(config.getItems())
      .dimensions(dimensions)
      // 公司端整个雷达图不下发（PRD §3.5「该图仅在 Portfolio 端显示」），保持 null 而非空数组。
      .radar(adminEnd ? buildRadar(config, founderRows, gsvRows, companyId, period) : null)
      // 基准页在站内的唯一入口，与雷达图同条件仅管理端下发（§0.10-D7）
      .benchmarkUrl(adminEnd ? benchmarkUrl(companyId, period) : null)
      .build();
  }
```

- [ ] **Step 5: `ErlCardServiceImpl.buildDimensions` 整方法替换（原 :172-235）**

```java
  /**
   * 维度行。<b>公司端不写 {@code gsvScore} / {@code perceptionGap} / {@code gapDirection}</b>
   * （§4.3 的裁剪清单），三者留 null 后由出参层不下发该 key。
   *
   * <p><b>项数按该期次绑定的配置版本</b>；当前生效版本里已被删掉的维度照常显示，前端标灰。</p>
   */
  private List<ErlDimensionScoreDTO> buildDimensions(String companyId,
                                                     String period,
                                                     String organizationId,
                                                     ErlDimensionConfigDTO config,
                                                     Map<String, ErlAssessment> founderRows,
                                                     Map<String, ErlAssessment> gsvRows,
                                                     Map<String, ErlGapAnalysisReportDTO.Task> tasksByCode,
                                                     Map<String, ErlPortalEnum> mismatchSides,
                                                     boolean adminEnd) {
    List<ErlDimensionConfigItemDTO> items = config.getItems();
    Map<String, ErlDimensionConfigStatusEnum> displayStatus = displayStatusOf(organizationId, items);
    List<ErlDimensionScoreDTO> dimensions = new ArrayList<>(items.size());
    for (ErlDimensionConfigItemDTO item : items) {
      String code = item.getDimensionCode();
      Integer founderScore = levelScore(founderRows.get(code));
      Integer gsvScore = levelScore(gsvRows.get(code));
      Integer perceptionGap = adminEnd ? ErlScoreCalculator.perceptionGap(founderScore, gsvScore) : null;
      // 卡片行只展示一个分数，**按登录端取**：管理端看 GSV 校验分、公司端看 Founder 自评分
      // （2026-09-15 需求方定，与前端 ErlCard.tsx 的 `rowScore = isAdmin ? gsvScore : founderScore` 同源）。
      // ⚠️ **不回退到另一侧**：管理端在 GSV 未校验时该维就是「无数据」，该维在综合分里按 0 计入加权和。
      Integer displayed = adminEnd ? gsvScore : founderScore;
      boolean bothSubmitted = founderRows.containsKey(code) && gsvRows.containsKey(code);
      dimensions.add(ErlDimensionScoreDTO.builder()
        .dimensionCode(code)
        .dimensionName(item.getDimensionName())
        .dimensionAbbr(item.getDimensionAbbr())
        .weight(item.getWeight())
        .founderScore(founderScore)
        .gsvScore(adminEnd ? gsvScore : null)
        .perceptionGap(perceptionGap)
        .gapDirection(adminEnd ? ErlScoreCalculator.gapDirection(perceptionGap) : null)
        .era(ErlScoreCalculator.eraLabelOf(ErlScoreCalculator.ofLevel(displayed)))
        .detailUrl(buildDetailUrl(code, companyId, period, adminEnd))
        // 圆点颜色看 bothSubmitted、文字看 hasGap，两条独立信息（§0.10-D4）
        .bothSubmitted(bothSubmitted)
        // 文字：读任务行（SUCCESS ∧ has_gap）。未分析 / 在跑 / 失败都是 false —— 那是「没分析」，
        // 前端要分辨用接口 17 的 analyzed；本类不对「两端打分一致」做任何现算覆写（零感知差在建任务时就是终态行）
        .hasGap(hasGap(tasksByCode.get(code)))
        // 第三条独立信息（P4，§7.3）：两端都交了但答的不是同一套题。⚠ 不能压进 hasGap
        .questionSetMismatch(mismatchSides.containsKey(code))
        .mismatchSide(portalName(mismatchSides.get(code)))
        // 灰色 Retired 标注的依据：按**当前生效版本**判，不是按本期次绑定的版本（§9-19 / §5.1.4）
        .status(displayStatus.get(code))
        .build());
    }
    return dimensions;
  }
```

- [ ] **Step 6: `ErlCardServiceImpl` 差距分析 helper 替换（原 :351-392 的 `gapDimensions` / `normalizeCode` / `portalName` / `truncatedSummary` 四个方法整段替换为下面三个）**

```java
  /** 记录里的活任务按维度索引；没有可见记录（公司端未分享 / 期次尚无记录）时为空 Map ⇒ 每维 hasGap = false。 */
  private Map<String, ErlGapAnalysisReportDTO.Task> indexTasks(ErlGapAnalysisReportDTO report) {
    Map<String, ErlGapAnalysisReportDTO.Task> byCode = new HashMap<>();
    if (report == null || report.getTasks() == null) {
      return byCode;
    }
    for (ErlGapAnalysisReportDTO.Task task : report.getTasks()) {
      byCode.putIfAbsent(task.getDimensionCode(), task);
    }
    return byCode;
  }

  /**
   * 小卡文字：该维活任务 {@code SUCCESS} 且 {@code has_gap = true}。口径与接口 17 的
   * {@code ErlGapAnalysisServiceImpl#toDimension} 逐字相同（两处都是读任务行，不再各自从条目推）。
   */
  private static boolean hasGap(ErlGapAnalysisReportDTO.Task task) {
    return task != null && task.getStatus() == ErlGapAnalysisTaskStatusEnum.SUCCESS
      && Boolean.TRUE.equals(task.getHasGap());
  }

  /** mismatch 落后端的出参取值：{@code FOUNDER} / {@code GSV}；不 mismatch 时不下发（null）。 */
  private static String portalName(ErlPortalEnum portal) {
    return portal == null ? null : portal.name();
  }
```

- [ ] **Step 7: `ErlDimensionServiceImpl` import**

- 删除 :12 `import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;`
- 删除 :32 `import com.gstdev.cioaas.web.erl.enums.ErlSeverityEnum;`
- :99 字段注释改为 `/** 差距分析的记录与任务在本域两张表里、条目在 Python；A3 一律经本服务按「该维一个任务」取（接口 21）。 */`

- [ ] **Step 8: `ErlDimensionServiceImpl.getDetail` 中差距分析取数段替换（:122-144）**

把从 `List<ErlQuestionConfig> questions = loadDimensionQuestions(viewed, dimension);` 到方法末尾 `.build();` 的整段替换为：

```java
    List<ErlQuestionConfig> questions = loadDimensionQuestions(viewed, dimension);
    List<ErlAssessmentAnswer> answers = loadAnswers(viewed);
    // 2026-09-24（任务化，设计稿 §7.3）：该维条目经 gap 服务按「这一端可见记录里该维**一个任务**」取，
    // 一次调用同时带回 GAP / ACTION，这里按 itemType 拆两组。narrative **有意不取** —— 维度级叙述段只在
    // A1 的 GapDetailsModal 里渲染（接口 17），A3 不展示它、出参也没有承载它的字段。
    // 公司端没有已分享记录 / 任务未 SUCCESS / 无差距 / Python 取不到：都是空列表，整页不受影响（设计 §8）。
    List<ErlGapItemDTO> gapItems = erlGapAnalysisService.loadItems(companyId, period, dimension, adminEnd);

    return ErlDimensionDetailDTO.builder()
      .header(buildDetailHeader(config, portal, founderRows.get(dimension), gsvRows.get(dimension),
        questions, answers, adminEnd, companyId, period))
      .submission(buildSubmission(viewed))
      .questions(buildQuestions(questions, answers))
      .gaps(itemsOf(gapItems, ErlGapItemTypeEnum.GAP))
      .actions(itemsOf(gapItems, ErlGapItemTypeEnum.ACTION))
      .build();
```

- [ ] **Step 9: `ErlDimensionServiceImpl` 差距分析 helper 整段替换（原 :480-561 的 `loadGapDimension` / `normalizeCode` / `gapItems` / `actionItems`）**

```java
  // ── 差距分析 ──────────────────────────────────────────────────────────

  /** 按类型拆条目；顺序与 {@code sortOrder} 原样保留（gap 服务已按 Python 的 {@code sort_order} 编好）。 */
  private List<ErlGapItemDTO> itemsOf(List<ErlGapItemDTO> items, ErlGapItemTypeEnum type) {
    List<ErlGapItemDTO> matched = new ArrayList<>();
    for (ErlGapItemDTO item : items) {
      if (item.getItemType() == type) {
        matched.add(item);
      }
    }
    return matched;
  }
```

- [ ] **Step 10: `ErlGapAnalysisController` 接口 27 的 Javadoc 改口（:65-70）**

```java
  /**
   * 接口 27：分享给 Founder 端（v4.4 新增，§0.10-D3，<b>仅管理端</b>）。
   *
   * <p>门槛五条（任务化设计 §7.4）：全维两端都有 SUBMITTED 记录、无题集 mismatch、最新记录存在且未分享、
   * 每维任务都已 SUCCESS、每维任务依据的提交就是当前最新提交；服务端 {@code FOR UPDATE} 最新记录后校验，
   * 未达成时 400、不因前端已置灰就放行。分享后该记录及其任务不可变，后续改动新建记录。</p>
   */
```

- [ ] **Step 11: `ErlDimensionConfig.dimensionCode` 的 Javadoc 改口（:54-60）**

```java
  /**
   * 维度代码，如 {@code FRL}。<b>组织内稳定、跨版本不变</b> —— {@code erl_question_config}、
   * {@code erl_assessment}、{@code erl_reference_score_item}、
   * {@code erl_question_config_dimension_version}、{@code erl_gap_analysis_dimension_task} 五张表的
   * {@code dimension_code} 列全靠它关联（最后一张 2026-09-24 随差距分析任务化取代了 {@code erl_gap_analysis_item}），
   * 故 code 一经使用即不可改（要改显示名改 {@link #dimensionName} / {@link #dimensionAbbr}）。
   */
```

- [ ] **Step 12: 编译收口（必须全绿）**

```bash
mvn -q -pl gstdev-cioaas-web -am compile -DskipTests
```
期望：无输出、退出码 0。若 MapStruct 报 `Unmapped target property` 之类的**警告**可忽略（`unmappedTargetPolicy = IGNORE`），报**错误**则回到对应 Task 核对字段名。再确认死引用已清：
```bash
grep -rn "getGapAnalysis\|shareGapAnalysis\|visibleArtifact\|regenerate(\|submissionSignature\|analyzedContext\|noGapDimensions\|gapSummary\|getSharedSnapshot\|dimensionSignature" gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/erl
```
期望：零命中。

---
### Task 10: `ErlGapAnalysisServiceImplTest` 重写

**Files:**
- Test（整文件替换，分两步写入同一文件，Step 2 的代码紧接 Step 1 末尾）: `test/erl/service/ErlGapAnalysisServiceImplTest.java`

> 测试基建沿用现状：`@ExtendWith(MockitoExtension.class)` + `LENIENT` + `@InjectMocks`；`@Value` 字段用 `ReflectionTestUtils` 置位；`self` 默认是桩（读路径据此断言「投了 / 没投」），写路径用例经 `useRealSelf()` 把它换成真身，让 `reconcile → plan / applyResults` 跑在同一个对象上（单测里没有代理，也就没有事务，正合适）。两个新 repository 全 mock：`save` / `saveAllAndFlush` 的桩负责给没有 id 的实体补 id 并收集进 `savedReports` / `savedTasks`，用例直接对这两个列表断言。**没有 H2 / Testcontainers**（`gstdev-cioaas-web/pom.xml` 只有 `spring-boot-starter-test`），仓储层的部分唯一索引冲突与 CAS rowcount 不在本轮单测范围（记入 Task 12 的台账提议）。

- [ ] **Step 1: 写入文件上半 —— 包头、桩、助手、写路径（reconcile / plan / applyResults）用例**

```java
package com.gstdev.cioaas.web.erl.service;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.gstdev.cioaas.common.exception.BadRequestException;
import com.gstdev.cioaas.common.exception.ServiceException;
import com.gstdev.cioaas.web.erl.client.ErlPythonClient;
import com.gstdev.cioaas.web.erl.converter.ErlGapAnalysisConverter;
import com.gstdev.cioaas.web.erl.dto.ErlCallerDTO;
import com.gstdev.cioaas.web.erl.dto.ErlDimensionConfigDTO;
import com.gstdev.cioaas.web.erl.dto.ErlDimensionConfigItemDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisReportDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisRequestDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisShareDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapDimensionDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemDTO;
import com.gstdev.cioaas.web.erl.dto.ErlGapItemsResultDTO;
import com.gstdev.cioaas.web.erl.entity.ErlAssessment;
import com.gstdev.cioaas.web.erl.entity.ErlGapAnalysisDimensionTask;
import com.gstdev.cioaas.web.erl.entity.ErlGapAnalysisReport;
import com.gstdev.cioaas.web.erl.enums.ErlAssessmentStatusEnum;
import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisReconcileOutcomeEnum;
import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisTaskStatusEnum;
import com.gstdev.cioaas.web.erl.enums.ErlGapItemTypeEnum;
import com.gstdev.cioaas.web.erl.enums.ErlPortalEnum;
import com.gstdev.cioaas.web.erl.enums.ErlSeverityEnum;
import com.gstdev.cioaas.web.erl.repository.ErlAssessmentAnswerRepository;
import com.gstdev.cioaas.web.erl.repository.ErlAssessmentRepository;
import com.gstdev.cioaas.web.erl.repository.ErlGapAnalysisDimensionTaskRepository;
import com.gstdev.cioaas.web.erl.repository.ErlGapAnalysisReportRepository;
import com.gstdev.cioaas.web.erl.vo.response.ErlGapAnalysisResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mapstruct.factory.Mappers;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Pageable;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.tuple;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.ArgumentMatchers.startsWith;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * {@link ErlGapAnalysisServiceImpl} 的单测（任务化设计 2026-09-24，§10 测试策略）。
 *
 * <p><b>写路径</b>（{@code reconcile → plan → applyResults}）钉住设计稿 §5 的九步：报告级门槛、首建、
 * 已分享记录的复制（{@code result_task_id} 链）、未分享记录的软删重建、force、FAILED / 超龄 RUNNING 重投、
 * 零感知差直建 SUCCESS、规划锁、按响应逐任务 CAS。<b>读路径</b>钉住 §7：管理端 / 公司端选行、
 * {@code analyzed} / {@code hasGap} 取自任务行、条目一次批量取与失败降级、Share 门槛五条、
 * {@code FOR UPDATE} + 二次校验。</p>
 *
 * <p>{@code self} 默认是桩（读路径据此断言「投了 / 没投」）；写路径用例先调 {@code useRealSelf()}，
 * 让 {@code reconcile → plan / applyResults} 在同一对象上跑通（单测里没有代理与事务）。两个新 repository
 * 全 mock，{@code save} / {@code saveAllAndFlush} 的桩给实体补 id 并收进 {@code savedReports} /
 * {@code savedTasks}，用例直接对这两个列表断言。</p>
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class ErlGapAnalysisServiceImplTest {

  private static final String COMPANY = "c1";

  private static final String PERIOD = "2026Q3";

  private static final String TOKEN = "Bearer t";

  private static final String CALLER = "u-1";

  @Mock
  private ErlAccessService erlAccessService;

  @Mock
  private ErlDimensionConfigService erlDimensionConfigService;

  @Mock
  private ErlPeriodService erlPeriodService;

  @Mock
  private ErlAssessmentRepository erlAssessmentRepository;

  @Mock
  private ErlAssessmentAnswerRepository erlAssessmentAnswerRepository;

  @Mock
  private ErlQuestionConfigVersionService erlQuestionConfigVersionService;

  @Mock
  private ErlAttachmentService erlAttachmentService;

  @Mock
  private ErlGapAnalysisReportRepository erlGapAnalysisReportRepository;

  @Mock
  private ErlGapAnalysisDimensionTaskRepository erlGapAnalysisDimensionTaskRepository;

  @Mock
  private ErlPythonClient erlPythonClient;

  @Mock
  private StringRedisTemplate stringRedisTemplate;

  @Mock
  private ValueOperations<String, String> valueOperations;

  /** 自身代理：默认是桩，读路径据此断言触发点 ② 投没投；写路径用例经 {@link #useRealSelf()} 换成真身。 */
  @Mock
  private ErlGapAnalysisService self;

  @InjectMocks
  private ErlGapAnalysisServiceImpl erlGapAnalysisService;

  private final List<ErlGapAnalysisReport> savedReports = new ArrayList<>();

  private final List<ErlGapAnalysisDimensionTask> savedTasks = new ArrayList<>();

  @BeforeEach
  void setUp() {
    // @Value 字段不由 @InjectMocks 注入，不显式置位就是 boolean 默认的 false —— 异步入口会整体短路
    ReflectionTestUtils.setField(erlGapAnalysisService, "aiEnabled", true);
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL"));
    when(erlDimensionConfigService.weightsOf(any())).thenReturn(Map.of("FRL", new BigDecimal("100.00")));
    when(erlQuestionConfigVersionService.organizationOf(any())).thenReturn("org-1");
    when(erlQuestionConfigVersionService.questionVersionNosOf(any())).thenReturn(Map.of());
    when(erlQuestionConfigVersionService.questionsOf(any(), any(), any())).thenReturn(List.of());
    when(erlAssessmentAnswerRepository.findByErlAssessmentIdIn(any())).thenReturn(List.of());
    // 规划锁与冷却键默认拿得到；单个用例要测抢不到时再改桩
    when(stringRedisTemplate.opsForValue()).thenReturn(valueOperations);
    when(valueOperations.setIfAbsent(anyString(), anyString(), anyLong(), any())).thenReturn(Boolean.TRUE);
    when(erlGapAnalysisReportRepository.findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(any(), any()))
        .thenReturn(Optional.empty());
    when(erlGapAnalysisReportRepository
        .findFirstByCompanyIdAndPeriodAndSharedTrueOrderByCreatedAtDescIdDesc(any(), any()))
        .thenReturn(Optional.empty());
    when(erlGapAnalysisReportRepository.save(any())).thenAnswer(invocation -> {
      ErlGapAnalysisReport report = invocation.getArgument(0);
      if (report.getId() == null) {
        report.setId("r-new-" + savedReports.size());
      }
      savedReports.add(report);
      return report;
    });
    when(erlGapAnalysisDimensionTaskRepository.saveAllAndFlush(any())).thenAnswer(invocation -> {
      List<ErlGapAnalysisDimensionTask> saved = new ArrayList<>();
      for (ErlGapAnalysisDimensionTask task : invocation.<Iterable<ErlGapAnalysisDimensionTask>>getArgument(0)) {
        if (task.getId() == null) {
          // 生产里由 @UuidGenerator 在 persist 时赋值；这里按维度码造一个可读的 id 方便断言
          task.setId("t-new-" + task.getDimensionCode());
        }
        savedTasks.add(task);
        saved.add(task);
      }
      return saved;
    });
    when(erlGapAnalysisDimensionTaskRepository.updateStatus(any(), any(), any(), any(), any(), any())).thenReturn(1);
    when(erlGapAnalysisDimensionTaskRepository.markDeleted(any(), any(), any()))
        .thenAnswer(invocation -> invocation.<Collection<String>>getArgument(0).size());
    // Python 默认对送去的每个任务都回 SUCCESS + hasGap=true；单个用例要测失败 / FAILED 时再改桩
    when(erlPythonClient.refresh(any(), any())).thenAnswer(invocation -> allSucceeded(invocation.getArgument(0)));
    when(erlPythonClient.fetchItems(any(), any()))
        .thenReturn(ErlGapItemsResultDTO.builder().items(List.of()).build());
  }

  // ── 打桩助手 ──────────────────────────────────────────────────────────

  /** 写路径用例：让 reconcile → plan / applyResults 在真身上跑（默认的桩会把 plan 吞成 null）。 */
  private void useRealSelf() {
    ReflectionTestUtils.setField(erlGapAnalysisService, "self", erlGapAnalysisService);
  }

  private ErlAssessment submitted(String id, ErlPortalEnum portal) {
    return submitted(id, portal, "FRL");
  }

  private ErlAssessment submitted(String id, ErlPortalEnum portal, String dimensionCode) {
    // ⚠️ 双端分数**刻意不等**（Founder 5 / GSV 4）：相等会命中零感知差 ⇒ 建行即 SUCCESS、不送 Python
    return submitted(id, portal, dimensionCode, portal == ErlPortalEnum.FOUNDER ? 5 : 4);
  }

  private ErlAssessment submitted(String id, ErlPortalEnum portal, String dimensionCode, Integer levelScore) {
    ErlAssessment assessment = new ErlAssessment();
    assessment.setId(id);
    assessment.setCompanyId(COMPANY);
    assessment.setPeriod(PERIOD);
    assessment.setPortal(portal);
    assessment.setDimensionCode(dimensionCode);
    assessment.setDimensionAbbr(dimensionCode);
    assessment.setStatus(ErlAssessmentStatusEnum.SUBMITTED);
    assessment.setLevelScore(levelScore);
    return assessment;
  }

  private ErlDimensionConfigDTO configOf(String... dimensionCodes) {
    List<ErlDimensionConfigItemDTO> items = new ArrayList<>(dimensionCodes.length);
    for (String code : dimensionCodes) {
      items.add(ErlDimensionConfigItemDTO.builder()
          .dimensionCode(code)
          .dimensionName(code + " name")
          .dimensionAbbr(code)
          .weight(new BigDecimal("100.00"))
          .build());
    }
    return ErlDimensionConfigDTO.builder().items(items).build();
  }

  /** 双端各一批已提交记录。 */
  private void submissionsAre(List<ErlAssessment> founderRows, List<ErlAssessment> gsvRows) {
    when(erlAssessmentRepository.findLatestSubmittedByCompanyAndPeriodAndPortal(
        COMPANY, PERIOD, ErlPortalEnum.FOUNDER, ErlAssessmentStatusEnum.SUBMITTED)).thenReturn(founderRows);
    when(erlAssessmentRepository.findLatestSubmittedByCompanyAndPeriodAndPortal(
        COMPANY, PERIOD, ErlPortalEnum.GSV, ErlAssessmentStatusEnum.SUBMITTED)).thenReturn(gsvRows);
  }

  /** 单维 FRL 双端各一条。 */
  private void submissionsAre(String founderId, String gsvId) {
    submissionsAre(List.of(submitted(founderId, ErlPortalEnum.FOUNDER)),
        List.of(submitted(gsvId, ErlPortalEnum.GSV)));
  }

  /** 让 FRL 两端绑不同题集版本号（v1 → 1 / v2 → 2）⇒ mismatch，落后端 = FOUNDER。 */
  private void frlMismatches(ErlAssessment founder, ErlAssessment gsv) {
    founder.setErlQuestionConfigVersionId("v1");
    gsv.setErlQuestionConfigVersionId("v2");
    when(erlQuestionConfigVersionService.questionVersionNosOf(any()))
        .thenReturn(Map.of("v1", Map.of("FRL", 1), "v2", Map.of("FRL", 2)));
  }

  private ErlGapAnalysisReport report(String id, boolean shared) {
    ErlGapAnalysisReport report = new ErlGapAnalysisReport();
    report.setId(id);
    report.setCompanyId(COMPANY);
    report.setPeriod(PERIOD);
    report.setShared(shared);
    return report;
  }

  private ErlGapAnalysisDimensionTask task(String id, String reportId, String code, String founderId, String gsvId,
                                           ErlGapAnalysisTaskStatusEnum status, Boolean hasGap) {
    ErlGapAnalysisDimensionTask task = new ErlGapAnalysisDimensionTask();
    task.setId(id);
    task.setErlGapAnalysisReportId(reportId);
    task.setDimensionCode(code);
    task.setSourceFounderAssessmentId(founderId);
    task.setSourceGsvAssessmentId(gsvId);
    task.setStatus(status);
    task.setHasGap(hasGap);
    task.setDeleted(Boolean.FALSE);
    task.setUpdatedAt(Instant.now());
    return task;
  }

  /** 最新记录 + 它的活任务（已分享时同时也是「最新已分享记录」）。 */
  private void latestReportIs(ErlGapAnalysisReport report, ErlGapAnalysisDimensionTask... tasks) {
    when(erlGapAnalysisReportRepository.findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(COMPANY, PERIOD))
        .thenReturn(Optional.of(report));
    if (Boolean.TRUE.equals(report.getShared())) {
      latestSharedReportIs(report, tasks);
    }
    when(erlGapAnalysisDimensionTaskRepository.findByErlGapAnalysisReportIdAndDeletedFalse(report.getId()))
        .thenReturn(List.of(tasks));
  }

  /** 最新**已分享**记录 + 它的活任务（管理端的最新记录可以是另一条）。 */
  private void latestSharedReportIs(ErlGapAnalysisReport report, ErlGapAnalysisDimensionTask... tasks) {
    when(erlGapAnalysisReportRepository
        .findFirstByCompanyIdAndPeriodAndSharedTrueOrderByCreatedAtDescIdDesc(COMPANY, PERIOD))
        .thenReturn(Optional.of(report));
    when(erlGapAnalysisDimensionTaskRepository.findByErlGapAnalysisReportIdAndDeletedFalse(report.getId()))
        .thenReturn(List.of(tasks));
  }

  private ErlGapAnalysisDimensionTask savedTask(String code) {
    return savedTasks.stream().filter(task -> code.equals(task.getDimensionCode())).findFirst()
        .orElseThrow(() -> new AssertionError("no task was saved for " + code));
  }

  private ErlGapAnalysisResultDTO allSucceeded(ErlGapAnalysisRequestDTO request) {
    List<ErlGapAnalysisResultDTO.Task> tasks = new ArrayList<>();
    for (ErlGapAnalysisRequestDTO.Task task : request.getTasks()) {
      tasks.add(ErlGapAnalysisResultDTO.Task.builder()
          .taskId(task.getTaskId()).status("SUCCESS").hasGap(Boolean.TRUE).build());
    }
    return ErlGapAnalysisResultDTO.builder().tasks(tasks).build();
  }

  private ErlGapAnalysisRequestDTO sentInput() {
    ArgumentCaptor<ErlGapAnalysisRequestDTO> captor = ArgumentCaptor.forClass(ErlGapAnalysisRequestDTO.class);
    verify(erlPythonClient).refresh(captor.capture(), eq(TOKEN));
    return captor.getValue();
  }

  /** 读路径公共打桩：管理端调用、期次固定。 */
  private void adminReadsTheCard() {
    when(erlAccessService.resolveCompanyId(any())).thenReturn(COMPANY);
    when(erlAccessService.currentCaller())
        .thenReturn(ErlCallerDTO.builder().adminEnd(true).userId("u-admin").build());
    when(erlAccessService.resolveOrganizationIdByCompany(COMPANY)).thenReturn("org-1");
    when(erlPeriodService.resolvePeriod(any(), any())).thenReturn(PERIOD);
  }

  /** 同上的公司端（创始人）版本。 */
  private void companyEndReadsTheCard() {
    when(erlAccessService.resolveCompanyId(any())).thenReturn(COMPANY);
    when(erlAccessService.currentCaller())
        .thenReturn(ErlCallerDTO.builder().adminEnd(false).userId("u-founder").build());
    when(erlAccessService.resolveOrganizationIdByCompany(COMPANY)).thenReturn("org-1");
    when(erlPeriodService.resolvePeriod(any(), any())).thenReturn(PERIOD);
  }

  /** Python 对给定任务 id 回一条 narrative + 一条 GAP + 一条 ACTION。 */
  private ErlGapItemsResultDTO.Item itemFor(String taskId, String severity) {
    return ErlGapItemsResultDTO.Item.builder()
        .taskId(taskId)
        .narrative("narrative of " + taskId)
        .gaps(List.of(ErlGapItemsResultDTO.Gap.builder().title("gap of " + taskId).severity(severity).build()))
        .actions(List.of(ErlGapItemsResultDTO.Action.builder().title("action of " + taskId).build()))
        .build();
  }

  private ErlGapDimensionDTO dimensionOf(ErlGapAnalysisDTO result, String code) {
    return result.getDimensions().stream().filter(dimension -> code.equals(dimension.getDimensionCode()))
        .findFirst().orElseThrow(() -> new AssertionError("dimension not rendered: " + code));
  }

  private ErlGapAnalysisReportDTO.Task taskDTO(String code, String founderId, String gsvId,
                                               ErlGapAnalysisTaskStatusEnum status) {
    return ErlGapAnalysisReportDTO.Task.builder()
        .taskId("t-" + code).dimensionCode(code).status(status)
        .sourceFounderAssessmentId(founderId).sourceGsvAssessmentId(gsvId).build();
  }

  private ErlGapAnalysisReportDTO reportDTO(boolean shared, ErlGapAnalysisReportDTO.Task... tasks) {
    return ErlGapAnalysisReportDTO.builder().reportId("r-1").shared(shared).tasks(List.of(tasks)).build();
  }

  private ListAppender<ILoggingEvent> attachAppender() {
    ListAppender<ILoggingEvent> appender = new ListAppender<>();
    Logger logger = (Logger) LoggerFactory.getLogger(ErlGapAnalysisServiceImpl.class);
    appender.start();
    logger.addAppender(appender);
    return appender;
  }

  private void detach(ListAppender<ILoggingEvent> appender) {
    ((Logger) LoggerFactory.getLogger(ErlGapAnalysisServiceImpl.class)).detachAppender(appender);
  }

  // ── 写路径：reconcile → plan（设计稿 §5 步骤 2 ~ 7）───────────────────

  @Test
  @DisplayName("首建：一条记录 + 每个 Active 维度一个任务；有分歧的维度 PENDING → 认领 → 派发，零感知差维度直接 SUCCESS")
  void plansAFreshReportWithOneTaskPerActiveDimension() {
    useRealSelf();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL", 4)),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g2", ErlPortalEnum.GSV, "PRL", 4)));

    ErlGapAnalysisReconcileOutcomeEnum outcome =
        erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(outcome).isEqualTo(ErlGapAnalysisReconcileOutcomeEnum.DONE);
    assertThat(savedReports).singleElement().satisfies(report -> {
      assertThat(report.getCompanyId()).isEqualTo(COMPANY);
      assertThat(report.getPeriod()).isEqualTo(PERIOD);
      assertThat(report.getShared()).isFalse();
      assertThat(report.getCreatedBy()).as("异步线程没有登录态，created_by 必须显式落触发者").isEqualTo(CALLER);
    });
    String reportId = savedReports.get(0).getId();
    assertThat(savedTasks)
        .extracting(ErlGapAnalysisDimensionTask::getErlGapAnalysisReportId,
            ErlGapAnalysisDimensionTask::getDimensionCode, ErlGapAnalysisDimensionTask::getStatus,
            ErlGapAnalysisDimensionTask::getHasGap, ErlGapAnalysisDimensionTask::getSourceFounderAssessmentId,
            ErlGapAnalysisDimensionTask::getSourceGsvAssessmentId, ErlGapAnalysisDimensionTask::getCreatedBy)
        .containsExactly(
            tuple(reportId, "FRL", ErlGapAnalysisTaskStatusEnum.PENDING, null, "f1", "g1", CALLER),
            tuple(reportId, "PRL", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.FALSE, "f2", "g2", CALLER));
    String frlId = savedTask("FRL").getId();
    // 认领：PENDING → RUNNING 的 CAS
    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq(frlId), eq(ErlGapAnalysisTaskStatusEnum.PENDING),
        eq(ErlGapAnalysisTaskStatusEnum.RUNNING), isNull(), any(), eq(CALLER));
    // 零感知差任务建行即终态，不认领、不派发
    verify(erlGapAnalysisDimensionTaskRepository, never()).updateStatus(eq(savedTask("PRL").getId()),
        any(), any(), any(), any(), any());
    ErlGapAnalysisRequestDTO sent = sentInput();
    assertThat(sent.getCompanyId()).isEqualTo(COMPANY);
    assertThat(sent.getPeriod()).isEqualTo(PERIOD);
    assertThat(sent.getTasks()).singleElement().satisfies(task -> {
      assertThat(task.getTaskId()).isEqualTo(frlId);
      assertThat(task.getName()).isEqualTo("FRL name");
      assertThat(task.getAbbr()).isEqualTo("FRL");
      assertThat(task.getFounderLevelScore()).isEqualTo(5);
      assertThat(task.getGsvLevelScore()).isEqualTo(4);
      assertThat(task.getPerceptionGap()).isEqualTo(1);
      assertThat(task.getQuestions()).isNotNull();
    });
    // 落状态：RUNNING → SUCCESS(hasGap) 的 CAS
    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq(frlId), eq(ErlGapAnalysisTaskStatusEnum.RUNNING),
        eq(ErlGapAnalysisTaskStatusEnum.SUCCESS), eq(Boolean.TRUE), any(), eq(CALLER));
  }

  @Test
  @DisplayName("全维零感知差：任务全部直建 SUCCESS + has_gap=false，一次 Python 都不调")
  void createsTerminalTasksWithoutCallingPythonWhenEveryDimensionHasAZeroPerceptionGap() {
    useRealSelf();
    submissionsAre(List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL", 5)),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL", 5)));

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(savedTasks).singleElement().satisfies(task -> {
      assertThat(task.getStatus()).isEqualTo(ErlGapAnalysisTaskStatusEnum.SUCCESS);
      assertThat(task.getHasGap()).isFalse();
    });
    verify(erlPythonClient, never()).refresh(any(), any());
    verify(erlGapAnalysisDimensionTaskRepository, never()).updateStatus(any(), any(), any(), any(), any(), any());
  }

  @Test
  @DisplayName("已分享记录 + 一维依据变了：新建记录；未变且 SUCCESS 的维度复制并把 result_task_id 指向原任务；旧记录一行不动")
  void forksASharedReportAndCopiesUnchangedSuccessfulTasks() {
    useRealSelf();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    // GSV 端把 PRL 重交成 g3；FRL 的依据仍是 f1 / g1
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g3", ErlPortalEnum.GSV, "PRL")));
    latestReportIs(report("r-1", true),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE),
        task("t-prl", "r-1", "PRL", "f2", "g2", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.FALSE));

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(savedReports).singleElement().satisfies(fork -> {
      assertThat(fork.getId()).isNotEqualTo("r-1");
      assertThat(fork.getShared()).isFalse();
    });
    String forkId = savedReports.get(0).getId();
    assertThat(savedTasks)
        .extracting(ErlGapAnalysisDimensionTask::getErlGapAnalysisReportId,
            ErlGapAnalysisDimensionTask::getDimensionCode, ErlGapAnalysisDimensionTask::getStatus,
            ErlGapAnalysisDimensionTask::getHasGap, ErlGapAnalysisDimensionTask::getResultTaskId,
            ErlGapAnalysisDimensionTask::getSourceGsvAssessmentId)
        .containsExactlyInAnyOrder(
            tuple(forkId, "FRL", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE, "t-frl", "g1"),
            tuple(forkId, "PRL", ErlGapAnalysisTaskStatusEnum.PENDING, null, null, "g3"));
    // 不变量 I1：已分享记录的任务永不软删、永不改
    verify(erlGapAnalysisDimensionTaskRepository, never()).markDeleted(any(), any(), any());
    verify(erlGapAnalysisDimensionTaskRepository, never()).updateStatus(eq("t-frl"), any(), any(), any(), any(), any());
    verify(erlGapAnalysisDimensionTaskRepository, never()).updateStatus(eq("t-prl"), any(), any(), any(), any(), any());
    assertThat(sentInput().getTasks()).extracting(ErlGapAnalysisRequestDTO.Task::getTaskId)
        .as("只派发新建的 PRL 任务，复制品不进 refresh")
        .containsExactly(savedTask("PRL").getId());
  }

  @Test
  @DisplayName("复制的复制：result_task_id 始终指向最初持有内容的那个任务（链只有一层）")
  void copiesKeepPointingAtTheRootContentTask() {
    useRealSelf();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g3", ErlPortalEnum.GSV, "PRL")));
    ErlGapAnalysisDimensionTask copy = task("t-frl-copy", "r-2", "FRL", "f1", "g1",
        ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE);
    copy.setResultTaskId("t-frl-root");
    latestReportIs(report("r-2", true), copy,
        task("t-prl", "r-2", "PRL", "f2", "g2", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(savedTask("FRL").getResultTaskId()).isEqualTo("t-frl-root");
  }

  @Test
  @DisplayName("已分享记录里未变但没跑完的维度：不复制、建新 PENDING 重跑（复制品永远等不到回写到旧 id 的结果）")
  void rebuildsAnUnchangedButUnfinishedTaskInsteadOfCopyingIt() {
    useRealSelf();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g3", ErlPortalEnum.GSV, "PRL")));
    latestReportIs(report("r-1", true),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.RUNNING, null),
        task("t-prl", "r-1", "PRL", "f2", "g2", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(savedTask("FRL")).satisfies(task -> {
      assertThat(task.getStatus()).isEqualTo(ErlGapAnalysisTaskStatusEnum.PENDING);
      assertThat(task.getResultTaskId()).isNull();
    });
    assertThat(sentInput().getTasks()).extracting(ErlGapAnalysisRequestDTO.Task::getTaskId)
        .containsExactlyInAnyOrder(savedTask("FRL").getId(), savedTask("PRL").getId());
  }

  @Test
  @DisplayName("已分享记录、没有任何维度依据变化：不建新记录、不派发")
  void leavesASharedReportAloneWhenNothingChanged() {
    useRealSelf();
    submissionsAre("f1", "g1");
    latestReportIs(report("r-1", true),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    ErlGapAnalysisReconcileOutcomeEnum outcome =
        erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(outcome).isEqualTo(ErlGapAnalysisReconcileOutcomeEnum.DONE);
    assertThat(savedReports).isEmpty();
    assertThat(savedTasks).isEmpty();
    verify(erlPythonClient, never()).refresh(any(), any());
  }

  @Test
  @DisplayName("未分享记录 + 一维依据变了：旧活任务软删、同记录下建新 PENDING；不建新记录")
  void replacesChangedTasksInPlaceInAnUnsharedReport() {
    useRealSelf();
    submissionsAre("f1", "g2");
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(savedReports).isEmpty();
    verify(erlGapAnalysisDimensionTaskRepository).markDeleted(eq(List.of("t-frl")), any(), eq(CALLER));
    assertThat(savedTasks).singleElement().satisfies(task -> {
      assertThat(task.getErlGapAnalysisReportId()).isEqualTo("r-1");
      assertThat(task.getStatus()).isEqualTo(ErlGapAnalysisTaskStatusEnum.PENDING);
      assertThat(task.getSourceGsvAssessmentId()).isEqualTo("g2");
    });
    assertThat(sentInput().getTasks()).extracting(ErlGapAnalysisRequestDTO.Task::getTaskId)
        .containsExactly(savedTask("FRL").getId());
  }

  @Test
  @DisplayName("force：依据没变的维度也全部软删重建（手动 Generate 就是想重跑）")
  void forceRebuildsEveryDimensionEvenWhenSourcesMatch() {
    useRealSelf();
    submissionsAre("f1", "g1");
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, true);

    verify(erlGapAnalysisDimensionTaskRepository).markDeleted(eq(List.of("t-frl")), any(), eq(CALLER));
    assertThat(savedTask("FRL").getStatus()).isEqualTo(ErlGapAnalysisTaskStatusEnum.PENDING);
    verify(erlPythonClient).refresh(any(), eq(TOKEN));
  }

  @Test
  @DisplayName("自愈：FAILED 与超过 10 分钟的 RUNNING 同 id 重投；新鲜的 RUNNING 不碰")
  void redispatchesFailedAndStaleRunningTasks() {
    useRealSelf();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL", "TRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL"),
            submitted("f3", ErlPortalEnum.FOUNDER, "TRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g2", ErlPortalEnum.GSV, "PRL"),
            submitted("g3", ErlPortalEnum.GSV, "TRL")));
    ErlGapAnalysisDimensionTask stale = task("t-prl", "r-1", "PRL", "f2", "g2",
        ErlGapAnalysisTaskStatusEnum.RUNNING, null);
    stale.setUpdatedAt(Instant.now().minus(Duration.ofMinutes(11)));
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.FAILED, null),
        stale,
        task("t-trl", "r-1", "TRL", "f3", "g3", ErlGapAnalysisTaskStatusEnum.RUNNING, null));

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(savedTasks).as("依据都没变，不建任何新任务").isEmpty();
    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq("t-frl"), eq(ErlGapAnalysisTaskStatusEnum.FAILED),
        eq(ErlGapAnalysisTaskStatusEnum.RUNNING), isNull(), any(), eq(CALLER));
    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq("t-prl"), eq(ErlGapAnalysisTaskStatusEnum.RUNNING),
        eq(ErlGapAnalysisTaskStatusEnum.RUNNING), isNull(), any(), eq(CALLER));
    verify(erlGapAnalysisDimensionTaskRepository, never()).updateStatus(eq("t-trl"), any(),
        eq(ErlGapAnalysisTaskStatusEnum.RUNNING), any(), any(), any());
    assertThat(sentInput().getTasks()).extracting(ErlGapAnalysisRequestDTO.Task::getTaskId)
        .as("同一个 task id 重投，Python 命中 SUCCESS 日志行时直接回状态")
        .containsExactlyInAnyOrder("t-frl", "t-prl");
  }

  @Test
  @DisplayName("认领的 CAS 落空（rowcount 0）：该任务不派发")
  void doesNotDispatchATaskWhoseClaimLostTheRace() {
    useRealSelf();
    submissionsAre("f1", "g1");
    when(erlGapAnalysisDimensionTaskRepository.updateStatus(any(), eq(ErlGapAnalysisTaskStatusEnum.PENDING),
        eq(ErlGapAnalysisTaskStatusEnum.RUNNING), any(), any(), any())).thenReturn(0);

    erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    verify(erlPythonClient, never()).refresh(any(), any());
  }

  @Test
  @DisplayName("报告未就绪（有维度没两端交齐）：不建记录、不建任务、不调 Python，记 INFO 不记 ERROR")
  void doesNotTouchAnythingWhenADimensionIsNotSubmittedOnBothSides() {
    useRealSelf();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL")));
    ListAppender<ILoggingEvent> appender = attachAppender();
    try {
      ErlGapAnalysisReconcileOutcomeEnum outcome =
          erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

      assertThat(outcome).isEqualTo(ErlGapAnalysisReconcileOutcomeEnum.NOT_SUBMITTED);
      assertThat(savedReports).isEmpty();
      assertThat(savedTasks).isEmpty();
      verify(erlPythonClient, never()).refresh(any(), any());
      assertThat(appender.list)
          .as("门槛未达成是设计里的正常路径（一个维度提交一次就触发一次）")
          .noneMatch(event -> event.getLevel() == Level.ERROR);
    } finally {
      detach(appender);
    }
  }

  @Test
  @DisplayName("报告未就绪（有维度题集 mismatch）：同样不建任何行，且成因与「没交齐」分得开")
  void doesNotTouchAnythingWhenADimensionHasAQuestionSetMismatch() {
    useRealSelf();
    ErlAssessment founder = submitted("f1", ErlPortalEnum.FOUNDER);
    ErlAssessment gsv = submitted("g1", ErlPortalEnum.GSV);
    frlMismatches(founder, gsv);
    submissionsAre(List.of(founder), List.of(gsv));

    ErlGapAnalysisReconcileOutcomeEnum outcome =
        erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(outcome).isEqualTo(ErlGapAnalysisReconcileOutcomeEnum.MISMATCHED);
    assertThat(savedReports).isEmpty();
    verify(erlPythonClient, never()).refresh(any(), any());
  }

  @Test
  @DisplayName("规划锁被占：直接返回 LOCK_BUSY，一次库都不查")
  void returnsImmediatelyWhenThePlanLockIsHeld() {
    useRealSelf();
    submissionsAre("f1", "g1");
    when(valueOperations.setIfAbsent(startsWith("erl:gapAnalysis:plan:"), anyString(), anyLong(), any()))
        .thenReturn(Boolean.FALSE);

    ErlGapAnalysisReconcileOutcomeEnum outcome =
        erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false);

    assertThat(outcome).isEqualTo(ErlGapAnalysisReconcileOutcomeEnum.LOCK_BUSY);
    verify(erlGapAnalysisReportRepository, never()).findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(any(), any());
    verify(erlPythonClient, never()).refresh(any(), any());
  }

  @Test
  @DisplayName("规划锁：规划完（无论成败）都释放；派发在锁外")
  void releasesThePlanLockBeforeDispatching() {
    useRealSelf();
    submissionsAre("f1", "g1");
    when(erlPythonClient.refresh(any(), any())).thenThrow(new IllegalStateException("python down"));

    assertThatThrownBy(() -> erlGapAnalysisService.reconcile(COMPANY, PERIOD, CALLER, TOKEN, false))
        .isInstanceOf(IllegalStateException.class);

    verify(stringRedisTemplate).delete("erl:gapAnalysis:plan:" + COMPANY + ":" + PERIOD);
  }

  // ── 写路径：applyResults（设计稿 §5 步骤 9 / §4）─────────────────────

  @Test
  @DisplayName("按响应逐任务 CAS：SUCCESS 带 hasGap、FAILED 不带；未知 status 按 FAILED；rowcount 0 忽略不抛")
  void appliesTheRefreshResponseWithACompareAndSetPerTask() {
    when(erlGapAnalysisDimensionTaskRepository.updateStatus(eq("t-2"), any(), any(), any(), any(), any()))
        .thenReturn(0);
    ErlGapAnalysisResultDTO result = ErlGapAnalysisResultDTO.builder().tasks(List.of(
        ErlGapAnalysisResultDTO.Task.builder().taskId("t-1").status("SUCCESS").hasGap(Boolean.TRUE).build(),
        ErlGapAnalysisResultDTO.Task.builder().taskId("t-2").status("FAILED").build(),
        ErlGapAnalysisResultDTO.Task.builder().taskId("t-3").status("WEIRD").hasGap(Boolean.TRUE).build(),
        ErlGapAnalysisResultDTO.Task.builder().taskId("t-4").status("SUCCESS").build()))
        .build();

    erlGapAnalysisService.applyResults(result, CALLER);

    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq("t-1"), eq(ErlGapAnalysisTaskStatusEnum.RUNNING),
        eq(ErlGapAnalysisTaskStatusEnum.SUCCESS), eq(Boolean.TRUE), any(), eq(CALLER));
    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq("t-2"), eq(ErlGapAnalysisTaskStatusEnum.RUNNING),
        eq(ErlGapAnalysisTaskStatusEnum.FAILED), isNull(), any(), eq(CALLER));
    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq("t-3"), eq(ErlGapAnalysisTaskStatusEnum.RUNNING),
        eq(ErlGapAnalysisTaskStatusEnum.FAILED), isNull(), any(), eq(CALLER));
    verify(erlGapAnalysisDimensionTaskRepository).updateStatus(eq("t-4"), eq(ErlGapAnalysisTaskStatusEnum.RUNNING),
        eq(ErlGapAnalysisTaskStatusEnum.SUCCESS), eq(Boolean.FALSE), any(), eq(CALLER));
  }

  @Test
  @DisplayName("异步入口：Python 派发失败只记一条带栈的 ERROR，任务留 RUNNING（不置 FAILED），绝不向提交流程抛")
  void leavesTasksRunningWhenTheRefreshCallFails() {
    useRealSelf();
    submissionsAre("f1", "g1");
    when(erlPythonClient.refresh(any(), any())).thenThrow(new IllegalStateException("python down"));
    ListAppender<ILoggingEvent> appender = attachAppender();
    try {
      erlGapAnalysisService.reconcileAsync(COMPANY, PERIOD, CALLER, TOKEN);

      verify(erlGapAnalysisDimensionTaskRepository, never()).updateStatus(any(), any(),
          eq(ErlGapAnalysisTaskStatusEnum.FAILED), any(), any(), any());
      assertThat(appender.list)
          .as("coding.md §11：ERROR 必须附 Throwable")
          .anyMatch(event -> event.getLevel() == Level.ERROR && event.getThrowableProxy() != null);
    } finally {
      detach(appender);
    }
  }

  @Test
  @DisplayName("开关关闭：异步入口整体短路，不建行、不调 Python")
  void skipsTheAsyncReconcileWhenTheAiSwitchIsOff() {
    useRealSelf();
    ReflectionTestUtils.setField(erlGapAnalysisService, "aiEnabled", false);
    submissionsAre("f1", "g1");

    erlGapAnalysisService.reconcileAsync(COMPANY, PERIOD, CALLER, TOKEN);

    assertThat(savedReports).isEmpty();
    verify(erlPythonClient, never()).refresh(any(), any());
  }
```
- [ ] **Step 2: 紧接 Step 1 写入文件下半 —— 读路径、触发点 ②、接口 21、Share、Generate、Converter 用例（以类的 `}` 收尾）**

```java
  // ── 读路径：选行与映射（设计稿 §7.1 / §7.2）────────────────────────────

  @Test
  @DisplayName("管理端读最新记录（未分享也读）：SUCCESS+hasGap 的维度取条目，PENDING 的维度 analyzed=false")
  void adminEndReadsTheLatestReportEvenWhenItIsUnshared() {
    adminReadsTheCard();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g2", ErlPortalEnum.GSV, "PRL")));
    latestReportIs(report("r-2", false),
        task("t-frl", "r-2", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE),
        task("t-prl", "r-2", "PRL", "f2", "g2", ErlGapAnalysisTaskStatusEnum.PENDING, null));
    when(erlPythonClient.fetchItems(any(), any()))
        .thenReturn(ErlGapItemsResultDTO.builder().items(List.of(itemFor("t-frl", "HIGH"))).build());

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, null);

    assertThat(result.getShared()).isFalse();
    assertThat(result.getAnalysisServiceUnavailable()).isFalse();
    ErlGapDimensionDTO frl = dimensionOf(result, "FRL");
    assertThat(frl.getBothSubmitted()).isTrue();
    assertThat(frl.getAnalyzed()).isTrue();
    assertThat(frl.getHasGap()).isTrue();
    assertThat(frl.getDimensionStale()).as("恒 false，字段只为前端兼容保留一版").isFalse();
    assertThat(frl.getNarrative()).isEqualTo("narrative of t-frl");
    assertThat(frl.getGaps()).extracting(ErlGapItemDTO::getTitle, ErlGapItemDTO::getSeverity)
        .containsExactly(tuple("gap of t-frl", ErlSeverityEnum.HIGH));
    assertThat(frl.getActions()).extracting(ErlGapItemDTO::getTitle).containsExactly("action of t-frl");
    ErlGapDimensionDTO prl = dimensionOf(result, "PRL");
    assertThat(prl.getAnalyzed()).as("PENDING / RUNNING / FAILED 都是「在分析」（D9）").isFalse();
    assertThat(prl.getHasGap()).isFalse();
    assertThat(prl.getGaps()).isEmpty();
    assertThat(prl.getNarrative()).isNull();
  }

  @Test
  @DisplayName("公司端只读最新已分享记录：管理端的最新未分享记录对创始人不可见（记录级不可变，D4）")
  void companyEndReadsOnlyTheLatestSharedReport() {
    companyEndReadsTheCard();
    submissionsAre("f1", "g2");
    // 管理端最新记录 r-2（未分享，依据 g2）；创始人看的是 r-1（已分享，依据 g1）
    latestReportIs(report("r-2", false),
        task("t-frl-2", "r-2", "FRL", "f1", "g2", ErlGapAnalysisTaskStatusEnum.PENDING, null));
    latestSharedReportIs(report("r-1", true),
        task("t-frl-1", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));
    when(erlPythonClient.fetchItems(any(), any()))
        .thenReturn(ErlGapItemsResultDTO.builder().items(List.of(itemFor("t-frl-1", "LOW"))).build());

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, null);

    assertThat(result.getShared()).isTrue();
    assertThat(result.getShareable()).as("shareable 仅管理端下发").isNull();
    assertThat(dimensionOf(result, "FRL").getAnalyzed()).isTrue();
    assertThat(dimensionOf(result, "FRL").getGaps()).extracting(ErlGapItemDTO::getTitle)
        .containsExactly("gap of t-frl-1");
    verify(erlPythonClient).fetchItems(eq(List.of("t-frl-1")), isNull());
    verify(self, never()).reconcileAsync(any(), any(), any(), any());
  }

  @Test
  @DisplayName("公司端尚无已分享记录：shared=false 的空态，但维度骨架照常下发（analyzed 全 false），不调 Python")
  void companyEndGetsTheSkeletonWhenNothingIsSharedYet() {
    companyEndReadsTheCard();
    submissionsAre("f1", "g1");
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, null);

    assertThat(result.getShared()).isFalse();
    assertThat(result.getDimensions()).extracting(ErlGapDimensionDTO::getDimensionCode).containsExactly("FRL");
    assertThat(dimensionOf(result, "FRL").getAnalyzed()).isFalse();
    verify(erlPythonClient, never()).fetchItems(any(), any());
  }

  @Test
  @DisplayName("公司端只遍历已分享记录里的任务：分享后新增的 Active 维度不下发；记录里的停用维度按评估行快照缩写照常下发")
  void companyEndRendersTheTasksOfTheSharedReportNotTheActiveDimensions() {
    companyEndReadsTheCard();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "NEW"));
    ErlAssessment oldFounder = submitted("f9", ErlPortalEnum.FOUNDER, "OLD");
    oldFounder.setDimensionAbbr("OLDA");
    submissionsAre(List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), oldFounder),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g9", ErlPortalEnum.GSV, "OLD")));
    latestSharedReportIs(report("r-1", true),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.FALSE),
        task("t-old", "r-1", "OLD", "f9", "g9", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.FALSE));

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, null);

    assertThat(result.getDimensions())
        .extracting(ErlGapDimensionDTO::getDimensionCode, ErlGapDimensionDTO::getDimensionAbbr)
        .as("消掉「分享后新增维度渲染成绿点 No Gap」的假阴性；停用维度排在配置维度之后")
        .containsExactly(tuple("FRL", "FRL"), tuple("OLD", "OLDA"));
  }

  @Test
  @DisplayName("已分析且无差距：analyzed=true + hasGap=false，且不为它取条目（空态不是故障）")
  void marksAnAnalyzedDimensionWithoutGapsAsAnalyzedWithoutFetchingItems() {
    adminReadsTheCard();
    submissionsAre("f1", "g1");
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.FALSE));

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, null);

    ErlGapDimensionDTO frl = dimensionOf(result, "FRL");
    assertThat(frl.getAnalyzed()).isTrue();
    assertThat(frl.getHasGap()).isFalse();
    assertThat(frl.getGaps()).isEmpty();
    assertThat(frl.getNarrative()).isNull();
    assertThat(result.getAnalysisServiceUnavailable()).isFalse();
    verify(erlPythonClient, never()).fetchItems(any(), any());
  }

  @Test
  @DisplayName("条目一次批量取：按 result_task_id ?? id 攒齐 id、只调一次 Python；非法 severity 降级 MEDIUM")
  void fetchesItemsInOneBatchUsingTheContentTaskId() {
    adminReadsTheCard();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g2", ErlPortalEnum.GSV, "PRL")));
    ErlGapAnalysisDimensionTask copy = task("t-frl-copy", "r-2", "FRL", "f1", "g1",
        ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE);
    copy.setResultTaskId("t-frl-root");
    latestReportIs(report("r-2", false), copy,
        task("t-prl", "r-2", "PRL", "f2", "g2", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));
    when(erlPythonClient.fetchItems(any(), any())).thenReturn(ErlGapItemsResultDTO.builder()
        .items(List.of(itemFor("t-frl-root", "HIGH"), itemFor("t-prl", "urgent"))).build());

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, null);

    // 请求线程路径的 token 取自 RequestContextHolder，单测里没有请求上下文故恒为 null
    verify(erlPythonClient).fetchItems(eq(List.of("t-frl-root", "t-prl")), isNull());
    assertThat(dimensionOf(result, "FRL").getGaps())
        .extracting(ErlGapItemDTO::getTitle, ErlGapItemDTO::getSeverity, ErlGapItemDTO::getItemType,
            ErlGapItemDTO::getSortOrder)
        .containsExactly(tuple("gap of t-frl-root", ErlSeverityEnum.HIGH, ErlGapItemTypeEnum.GAP, 0));
    assertThat(dimensionOf(result, "PRL").getGaps().get(0).getSeverity())
        .as("一条取值异常不该让整维渲染失败")
        .isEqualTo(ErlSeverityEnum.MEDIUM);
    assertThat(dimensionOf(result, "PRL").getActions()).extracting(ErlGapItemDTO::getTitle)
        .containsExactly("action of t-prl");
  }

  @Test
  @DisplayName("Python 取条目失败：analysisServiceUnavailable=true，analyzed / hasGap 照常来自任务行，内容为空、不抛")
  void reportsTheAnalysisServiceUnavailableWhenItemsCannotBeFetched() {
    adminReadsTheCard();
    submissionsAre("f1", "g1");
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));
    when(erlPythonClient.fetchItems(any(), any())).thenThrow(new IllegalStateException("python down"));

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, null);

    assertThat(result.getAnalysisServiceUnavailable())
        .as("让前端走失败态 + Retry，而不是把 Python 宕机伪装成「正在分析」")
        .isTrue();
    ErlGapDimensionDTO frl = dimensionOf(result, "FRL");
    assertThat(frl.getAnalyzed()).isTrue();
    assertThat(frl.getHasGap()).isTrue();
    assertThat(frl.getGaps()).isEmpty();
    assertThat(frl.getNarrative()).isNull();
  }

  @Test
  @DisplayName("公司端同样下发 analysisServiceUnavailable：创始人也需要知道是坏了而不是在跑")
  void reportsTheOutageToTheCompanyEndToo() {
    companyEndReadsTheCard();
    submissionsAre("f1", "g1");
    latestSharedReportIs(report("r-1", true),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));
    when(erlPythonClient.fetchItems(any(), any())).thenThrow(new IllegalStateException("python down"));

    assertThat(erlGapAnalysisService.find(COMPANY, PERIOD, null).getAnalysisServiceUnavailable()).isTrue();
  }

  @Test
  @DisplayName("按维度限定读（find 带 dimension）：只回该维一项，大小写不敏感")
  void scopesTheReadToOneDimension() {
    adminReadsTheCard();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL"), submitted("g2", ErlPortalEnum.GSV, "PRL")));

    ErlGapAnalysisDTO result = erlGapAnalysisService.find(COMPANY, PERIOD, "prl");

    assertThat(result.getDimensions()).extracting(ErlGapDimensionDTO::getDimensionCode).containsExactly("PRL");
  }

  // ── 触发点 ②：管理端读接口 + 60s 冷却 ──────────────────────────────────

  @Test
  @DisplayName("管理端每次读：拿到冷却键就异步投一次 reconcile（带调用者 userId 与请求线程的 token）")
  void adminReadTriggersAnAsyncReconcileUnderCooldown() {
    adminReadsTheCard();
    submissionsAre("f1", "g1");

    erlGapAnalysisService.find(COMPANY, PERIOD, null);

    verify(self).reconcileAsync(COMPANY, PERIOD, "u-admin", null);
  }

  @Test
  @DisplayName("冷却键还在：不重复投递（防前端 5s 轮询把读接口的写副作用放大成每 5 秒一轮对账）")
  void doesNotRedeliverWhileTheCooldownIsActive() {
    adminReadsTheCard();
    submissionsAre("f1", "g1");
    when(valueOperations.setIfAbsent(startsWith("erl:gapAnalysis:cooldown:"), anyString(), anyLong(), any()))
        .thenReturn(Boolean.FALSE);

    erlGapAnalysisService.find(COMPANY, PERIOD, null);

    verify(self, never()).reconcileAsync(any(), any(), any(), any());
  }

  @Test
  @DisplayName("Redis 抖动：冷却判定 fail-open 照常投递 —— 节流失效只是多规划几次，fail-close 会让自愈停摆")
  void stillRedeliversWhenTheCooldownKeyCannotBeRead() {
    adminReadsTheCard();
    submissionsAre("f1", "g1");
    when(valueOperations.setIfAbsent(startsWith("erl:gapAnalysis:cooldown:"), anyString(), anyLong(), any()))
        .thenThrow(new IllegalStateException("redis down"));

    erlGapAnalysisService.find(COMPANY, PERIOD, null);

    verify(self).reconcileAsync(COMPANY, PERIOD, "u-admin", null);
  }

  @Test
  @DisplayName("公司端的读永不产生写副作用")
  void theCompanyEndReadNeverDeliversAReconcile() {
    companyEndReadsTheCard();
    submissionsAre("f1", "g1");

    erlGapAnalysisService.find(COMPANY, PERIOD, null);

    verify(self, never()).reconcileAsync(any(), any(), any(), any());
  }

  // ── 接口 21：loadItems ─────────────────────────────────────────────────

  @Test
  @DisplayName("loadItems：只带该维一个任务的 id 去取，GAP / ACTION 混在一个列表里靠 itemType 区分")
  void loadItemsReturnsTheItemsOfThatDimensionOnly() {
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE),
        task("t-prl", "r-1", "PRL", "f2", "g2", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));
    when(erlPythonClient.fetchItems(any(), any()))
        .thenReturn(ErlGapItemsResultDTO.builder().items(List.of(itemFor("t-prl", "LOW"))).build());

    List<ErlGapItemDTO> items = erlGapAnalysisService.loadItems(COMPANY, PERIOD, "PRL", true);

    verify(erlPythonClient).fetchItems(eq(List.of("t-prl")), isNull());
    assertThat(items).extracting(ErlGapItemDTO::getItemType, ErlGapItemDTO::getTitle, ErlGapItemDTO::getDimensionCode)
        .containsExactly(tuple(ErlGapItemTypeEnum.GAP, "gap of t-prl", "PRL"),
            tuple(ErlGapItemTypeEnum.ACTION, "action of t-prl", "PRL"));
  }

  @Test
  @DisplayName("loadItems：公司端无已分享记录 / 该维无任务 / 任务无差距 —— 都是空列表且不调 Python")
  void loadItemsIsEmptyWhenThereIsNothingToShow() {
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.FALSE));

    assertThat(erlGapAnalysisService.loadItems(COMPANY, PERIOD, "FRL", false)).isEmpty();
    assertThat(erlGapAnalysisService.loadItems(COMPANY, PERIOD, "PRL", true)).isEmpty();
    assertThat(erlGapAnalysisService.loadItems(COMPANY, PERIOD, "FRL", true)).isEmpty();
    verify(erlPythonClient, never()).fetchItems(any(), any());
  }

  // ── Share 门槛五条（设计稿 §7.4）与接口 27 ────────────────────────────

  @Test
  @DisplayName("isShareable 五条缺一不可：ready ∧ 记录存在 ∧ 未分享 ∧ 每维 SUCCESS ∧ 每维 source == 当前 SOT")
  void shareGateRequiresAllFiveConditions() {
    ErlDimensionConfigDTO config = configOf("FRL");
    Map<String, ErlAssessment> founderRows = Map.of("FRL", submitted("f1", ErlPortalEnum.FOUNDER));
    Map<String, ErlAssessment> gsvRows = Map.of("FRL", submitted("g1", ErlPortalEnum.GSV));
    ErlGapAnalysisReportDTO.Task ok = taskDTO("FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS);

    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows, Map.of(), reportDTO(false, ok)))
        .as("五条都成立").isTrue();
    // ① ready：漏交 / mismatch
    assertThat(erlGapAnalysisService.isShareable(config, Map.of(), gsvRows, Map.of(), reportDTO(false, ok))).isFalse();
    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows,
        Map.of("FRL", ErlPortalEnum.FOUNDER), reportDTO(false, ok))).isFalse();
    // ② 最新记录存在
    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows, Map.of(), null)).isFalse();
    // ③ 未分享
    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows, Map.of(), reportDTO(true, ok))).isFalse();
    // ④ 每维活任务 SUCCESS（在跑 / 失败 / 没任务）
    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows, Map.of(),
        reportDTO(false, taskDTO("FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.RUNNING)))).isFalse();
    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows, Map.of(),
        reportDTO(false, taskDTO("FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.FAILED)))).isFalse();
    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows, Map.of(), reportDTO(false))).isFalse();
    // ⑤ 每维任务 source == 当前 SOT
    assertThat(erlGapAnalysisService.isShareable(config, founderRows, gsvRows, Map.of(),
        reportDTO(false, taskDTO("FRL", "f1", "g0", ErlGapAnalysisTaskStatusEnum.SUCCESS)))).isFalse();
  }

  /** Share 公共打桩：管理端 + 锁到手的未分享最新记录（二次校验仍是它）。 */
  private ErlGapAnalysisReport lockedLatestReport(boolean shared, ErlGapAnalysisDimensionTask... tasks) {
    adminReadsTheCard();
    ErlGapAnalysisReport report = report("r-1", shared);
    when(erlGapAnalysisReportRepository.lockLatestByCompanyIdAndPeriod(eq(COMPANY), eq(PERIOD), any(Pageable.class)))
        .thenReturn(List.of(report));
    latestReportIs(report, tasks);
    return report;
  }

  @Test
  @DisplayName("Share 通过：FOR UPDATE 最新记录 → 五条门槛 → 置 shared / sharedAt / sharedBy，不调 Python")
  void shareLocksTheLatestReportAndMarksItShared() {
    submissionsAre("f1", "g1");
    ErlGapAnalysisReport report = lockedLatestReport(false,
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    ErlGapAnalysisShareDTO result = erlGapAnalysisService.share(COMPANY, PERIOD);

    assertThat(result.getShared()).isTrue();
    assertThat(result.getSharedBy()).isEqualTo("u-admin");
    assertThat(result.getSharedAt()).isNotNull();
    assertThat(report.getShared()).isTrue();
    assertThat(report.getSharedBy()).isEqualTo("u-admin");
    verify(erlGapAnalysisReportRepository).lockLatestByCompanyIdAndPeriod(eq(COMPANY), eq(PERIOD), any(Pageable.class));
    verify(erlGapAnalysisReportRepository).save(report);
    verify(erlPythonClient, never()).fetchItems(any(), any());
    verify(erlPythonClient, never()).refresh(any(), any());
  }

  @Test
  @DisplayName("锁到手时后台已换了最新记录：400 Content updated, please refresh，且不置位")
  void shareRejectsWhenAnotherReportAppearedMeanwhile() {
    submissionsAre("f1", "g1");
    ErlGapAnalysisReport locked = lockedLatestReport(false,
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));
    when(erlGapAnalysisReportRepository.findFirstByCompanyIdAndPeriodOrderByCreatedAtDescIdDesc(COMPANY, PERIOD))
        .thenReturn(Optional.of(report("r-2", false)));

    assertThatThrownBy(() -> erlGapAnalysisService.share(COMPANY, PERIOD))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("Content updated, please refresh");
    assertThat(locked.getShared()).isFalse();
  }

  @Test
  @DisplayName("该期次还没有记录：400 There is no gap analysis to share")
  void shareRejectsWhenThereIsNothingToShare() {
    adminReadsTheCard();
    submissionsAre("f1", "g1");
    when(erlGapAnalysisReportRepository.lockLatestByCompanyIdAndPeriod(eq(COMPANY), eq(PERIOD), any(Pageable.class)))
        .thenReturn(List.of());

    assertThatThrownBy(() -> erlGapAnalysisService.share(COMPANY, PERIOD))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("There is no gap analysis to share");
  }

  @Test
  @DisplayName("有任务还在跑：400，文案点明是在等分析而不是漏交")
  void shareRejectsWhenATaskIsStillRunning() {
    submissionsAre("f1", "g1");
    lockedLatestReport(false, task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.RUNNING, null));

    assertThatThrownBy(() -> erlGapAnalysisService.share(COMPANY, PERIOD))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("have not been analyzed for the latest submissions yet");
  }

  @Test
  @DisplayName("任务依据的不是最新提交（双端交错提交后对账还没追上）：同样 400 等分析")
  void shareRejectsWhenTheTaskIsBuiltOnAnOlderSubmission() {
    submissionsAre("f1", "g2");
    lockedLatestReport(false,
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    assertThatThrownBy(() -> erlGapAnalysisService.share(COMPANY, PERIOD))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("have not been analyzed for the latest submissions yet");
  }

  @Test
  @DisplayName("有维度没两端交齐：400 且根本不去锁记录")
  void shareRejectsWhenNotAllDimensionsSubmitted() {
    adminReadsTheCard();
    when(erlDimensionConfigService.activeConfigOf(any())).thenReturn(configOf("FRL", "PRL"));
    submissionsAre(
        List.of(submitted("f1", ErlPortalEnum.FOUNDER, "FRL"), submitted("f2", ErlPortalEnum.FOUNDER, "PRL")),
        List.of(submitted("g1", ErlPortalEnum.GSV, "FRL")));

    assertThatThrownBy(() -> erlGapAnalysisService.share(COMPANY, PERIOD))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("All dimensions must be submitted");
    verify(erlGapAnalysisReportRepository, never()).lockLatestByCompanyIdAndPeriod(any(), any(), any());
  }

  @Test
  @DisplayName("有维度题集不一致：400，文案点明是题集不一致而非漏交，且不去锁记录")
  void shareRejectsWhenADimensionHasAQuestionSetMismatch() {
    adminReadsTheCard();
    ErlAssessment founder = submitted("f1", ErlPortalEnum.FOUNDER);
    ErlAssessment gsv = submitted("g1", ErlPortalEnum.GSV);
    frlMismatches(founder, gsv);
    submissionsAre(List.of(founder), List.of(gsv));

    assertThatThrownBy(() -> erlGapAnalysisService.share(COMPANY, PERIOD))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("question bank has been updated");
    verify(erlGapAnalysisReportRepository, never()).lockLatestByCompanyIdAndPeriod(any(), any(), any());
  }

  @Test
  @DisplayName("最新记录已经分享过：400 already been shared（记录级不可变，不重复置位）")
  void shareRejectsWhenAlreadyShared() {
    submissionsAre("f1", "g1");
    lockedLatestReport(true, task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    assertThatThrownBy(() -> erlGapAnalysisService.share(COMPANY, PERIOD))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("already been shared");
    verify(erlGapAnalysisReportRepository, never()).save(any());
  }

  // ── 接口 18：手动 Generate ─────────────────────────────────────────────

  @Test
  @DisplayName("手动 Generate：force=true 的同步对账（依据没变也重跑），然后返回读结果")
  void manualGenerationRunsAForcedReconcileAndReturnsTheRead() {
    useRealSelf();
    adminReadsTheCard();
    submissionsAre("f1", "g1");
    latestReportIs(report("r-1", false),
        task("t-frl", "r-1", "FRL", "f1", "g1", ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    ErlGapAnalysisDTO result = erlGapAnalysisService.generate(COMPANY, PERIOD, TOKEN);

    verify(erlGapAnalysisDimensionTaskRepository).markDeleted(eq(List.of("t-frl")), any(), eq("u-admin"));
    verify(erlPythonClient).refresh(any(), eq(TOKEN));
    assertThat(result.getDimensions()).extracting(ErlGapDimensionDTO::getDimensionCode).containsExactly("FRL");
  }

  @Test
  @DisplayName("手动 Generate：有维度没两端交齐 ⇒ 400（文案沿用），不调 Python")
  void manualGenerationRejectsWhenADimensionIsNotSubmittedOnBothSides() {
    useRealSelf();
    adminReadsTheCard();
    submissionsAre(List.of(submitted("f1", ErlPortalEnum.FOUNDER)), List.of());

    assertThatThrownBy(() -> erlGapAnalysisService.generate(COMPANY, PERIOD, TOKEN))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("must be submitted by both sides before generating");
    verify(erlPythonClient, never()).refresh(any(), any());
  }

  @Test
  @DisplayName("手动 Generate：有维度题集 mismatch ⇒ 不报错、不调 Python，原样返回读结果（该维已是黄点）")
  void manualGenerationDoesNotFailOnAQuestionSetMismatch() {
    useRealSelf();
    adminReadsTheCard();
    ErlAssessment founder = submitted("f1", ErlPortalEnum.FOUNDER);
    ErlAssessment gsv = submitted("g1", ErlPortalEnum.GSV);
    frlMismatches(founder, gsv);
    submissionsAre(List.of(founder), List.of(gsv));

    ErlGapAnalysisDTO result = erlGapAnalysisService.generate(COMPANY, PERIOD, TOKEN);

    assertThat(dimensionOf(result, "FRL").getQuestionSetMismatch()).isTrue();
    assertThat(dimensionOf(result, "FRL").getMismatchSide()).isEqualTo("FOUNDER");
    verify(erlPythonClient, never()).refresh(any(), any());
  }

  @Test
  @DisplayName("手动 Generate：Python 派发失败转成 ServiceException 抛给管理端，不静默")
  void manualGenerationSurfacesThePythonFailure() {
    useRealSelf();
    adminReadsTheCard();
    submissionsAre("f1", "g1");
    when(erlPythonClient.refresh(any(), any())).thenThrow(new IllegalStateException("python down"));

    assertThatThrownBy(() -> erlGapAnalysisService.generate(COMPANY, PERIOD, TOKEN))
        .isInstanceOf(ServiceException.class)
        .hasMessageContaining("Gap analysis failed");
  }

  @Test
  @DisplayName("开关关闭不影响手动 Generate：人工动作照常规划并派发")
  void manualGenerationIgnoresTheAiSwitch() {
    useRealSelf();
    ReflectionTestUtils.setField(erlGapAnalysisService, "aiEnabled", false);
    adminReadsTheCard();
    submissionsAre("f1", "g1");

    erlGapAnalysisService.generate(COMPANY, PERIOD, TOKEN);

    verify(erlPythonClient).refresh(any(), eq(TOKEN));
  }

  @Test
  @DisplayName("手动 Generate：period 为空 ⇒ 400")
  void manualGenerationRequiresThePeriod() {
    adminReadsTheCard();

    assertThatThrownBy(() -> erlGapAnalysisService.generate(COMPANY, " ", TOKEN))
        .isInstanceOf(BadRequestException.class)
        .hasMessageContaining("period is required");
  }

  // ── Converter ──────────────────────────────────────────────────────────

  @Test
  @DisplayName("Converter：接口 17 只剩四个期次级字段；接口 27 的三个字段来自 ErlGapAnalysisShareDTO")
  void converterKeepsOnlyTheSurvivingFields() {
    ErlGapAnalysisConverter converter = Mappers.getMapper(ErlGapAnalysisConverter.class);
    ErlGapAnalysisResponse response = converter.toResponse(ErlGapAnalysisDTO.builder()
        .dimensions(List.of(ErlGapDimensionDTO.builder()
            .dimensionCode("FRL").analyzed(Boolean.TRUE).hasGap(Boolean.TRUE).dimensionStale(Boolean.FALSE)
            .gaps(List.of(ErlGapItemDTO.builder().title("g").severity(ErlSeverityEnum.HIGH).sortOrder(0).build()))
            .actions(List.of(ErlGapItemDTO.builder().title("a").sortOrder(0).build()))
            .build()))
        .analysisServiceUnavailable(Boolean.FALSE)
        .shared(Boolean.TRUE)
        .shareable(Boolean.FALSE)
        .build());

    assertThat(response.getShared()).isTrue();
    assertThat(response.getShareable()).isFalse();
    assertThat(response.getAnalysisServiceUnavailable()).isFalse();
    assertThat(response.getDimensions()).singleElement().satisfies(dimension -> {
      assertThat(dimension.getAnalyzed()).isTrue();
      assertThat(dimension.getGaps()).singleElement().satisfies(gap -> {
        assertThat(gap.getTitle()).isEqualTo("g");
        assertThat(gap.getSeverity()).isEqualTo("HIGH");
      });
      assertThat(dimension.getActions()).singleElement()
          .satisfies(action -> assertThat(action.getTitle()).isEqualTo("a"));
    });
    Instant sharedAt = Instant.parse("2026-09-24T10:00:00Z");
    assertThat(converter.toShareResponse(ErlGapAnalysisShareDTO.builder()
        .shared(Boolean.TRUE).sharedAt(sharedAt).sharedBy("u-admin").build())).satisfies(share -> {
      assertThat(share.getShared()).isTrue();
      assertThat(share.getSharedAt()).isEqualTo(sharedAt);
      assertThat(share.getSharedBy()).isEqualTo("u-admin");
    });
  }
}
```

- [ ] **Step 3: 轻量校验（只编译测试，不运行）**

```bash
mvn -q -pl gstdev-cioaas-web -am test-compile -DskipTests 2>&1 | grep -E "ERROR.*\.java" | sed -E 's/.*erl\///' | sort -u
```
期望：报错清单**只**剩 `service/ErlCardServiceImplTest.java`、`service/ErlDimensionServiceImplTest.java`、`service/ErlAssessmentServiceImplTest.java`（Task 11 处理）。本文件若报错，常见成因：`invocation.<Iterable<...>>getArgument(0)` 的显式类型实参写漏、`tuple` / `startsWith` / `isNull` 静态导入漏掉。

---
### Task 11: Card / Dimension / Assessment 测试同步

**Files:**
- Test: `test/erl/service/ErlCardServiceImplTest.java:8,31,36（import）,107-118,142-143,270-385,437-450`
- Test: `test/erl/service/ErlDimensionServiceImplTest.java:8,17,42,44（import）,126-137,342-447`
- Test: `test/erl/service/ErlAssessmentServiceImplTest.java:376-379`

- [ ] **Step 1: `ErlCardServiceImplTest` import 与 setUp**

- :8 `import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;` → 改为 `import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisReportDTO;`
- 在 :10 `import com.gstdev.cioaas.web.erl.enums.ErlAssessmentStatusEnum;` 之后新增 `import com.gstdev.cioaas.web.erl.enums.ErlGapAnalysisTaskStatusEnum;`
- 删除 :36 `import static org.mockito.Mockito.lenient;`；在 `import static org.mockito.Mockito.verify;` 之前新增 `import static org.mockito.Mockito.never;`（`anyBoolean` / `anyString` / `eq` / `same` 保留）
- 删除 setUp 里 :107-118 的整段 `visibleArtifact` 打桩（从 `// \`visibleArtifact\` 是「这一端该看哪一份」的唯一口径` 那行注释起到 `});` 止）
- `givenSubmitted` 里 :142-143 的
```java
    // 该期次尚无产物：Card 走空态（gapSummary / gapDimensions 都为空）
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD)).thenReturn(null);
```
改为
```java
    // 该期次这一端尚无可见记录：每维 hasGap = false、shared = false（任务化后 Card 不调 Python）
    when(erlGapAnalysisService.loadResult(eq(COMPANY), eq(PERIOD), anyBoolean())).thenReturn(null);
```

- [ ] **Step 2: `ErlCardServiceImplTest` 差距分析段整段替换**

删除以下 6 个用例及 `gapArtifact` 助手（:270-385 从 `// ── 差距分析产物 → 卡片（2026-09-18 P3：产物改从 Python 取）` 起）：`gapArtifact`、`adminCardTakesTheGapFlagsFromTheArtifact`、`companyCardRendersTheSharedSnapshotRatherThanTheLiveArtifact`、`adminCardReportsUnsharedOnceTheContentHasBeenRegenerated`、`adminCardTakesTheGapFlagFromTheArtifactEvenWhenBothSidesScoreTheSame`、`adminCardReportsNoGapOnceTheTerminalRowIsPersisted`；再删除文件末尾的 `companyEndCardShowsNoGapUntilItIsShared`（:437-450）。保留 `adminCardTakesTheQuestionSetMismatchFromTheGapService`、`adminCardTakesTheShareGateFromTheGapService`、`emptyCardReportsNoQuestionSetMismatch`（三者不引用被删 API）。在原 `// ── 差距分析产物 → 卡片` 的位置写入：

```java
  // ── 差距分析：记录与任务来自 Java 表（2026-09-24 任务化，接口 1 不调 Python）────────

  /** 这一端可见的一条记录 + FRL 一个任务；status / hasGap / shared 由用例给定。 */
  private ErlGapAnalysisReportDTO reportOf(boolean shared, ErlGapAnalysisTaskStatusEnum status, Boolean hasGap) {
    return ErlGapAnalysisReportDTO.builder()
      .reportId("r-1")
      .shared(shared)
      .tasks(List.of(ErlGapAnalysisReportDTO.Task.builder()
        .taskId("t-frl")
        .dimensionCode("FRL")
        .status(status)
        .hasGap(hasGap)
        .sourceFounderAssessmentId("f1")
        .sourceGsvAssessmentId("g1")
        .build()))
      .build();
  }

  @Test
  @DisplayName("管理端：小卡 hasGap 读任务行（SUCCESS ∧ has_gap），不再从 Python 条目推导；未分享也照给")
  void adminCardTakesHasGapFromTheTaskRow() {
    givenSubmitted(List.of(submitted("FRL", 3)), List.of(submitted("FRL", 7)));
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD, true))
      .thenReturn(reportOf(false, ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    ErlCardDTO card = erlCardService.getCard(COMPANY, null);

    assertThat(card.getDimensions().get(0).getHasGap()).isTrue();
    assertThat(card.getShared()).isFalse();
    verify(erlGapAnalysisService, never()).loadItems(anyString(), anyString(), anyString(), anyBoolean());
  }

  @Test
  @DisplayName("管理端：任务还在 PENDING / RUNNING / FAILED ⇒ hasGap=false（那是「没分析」，前端靠接口 17 的 analyzed 分辨）")
  void adminCardShowsNoGapWhileTheTaskIsNotSuccessful() {
    givenSubmitted(List.of(submitted("FRL", 3)), List.of(submitted("FRL", 7)));
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD, true))
      .thenReturn(reportOf(false, ErlGapAnalysisTaskStatusEnum.RUNNING, null));

    assertThat(erlCardService.getCard(COMPANY, null).getDimensions().get(0).getHasGap()).isFalse();
  }

  @Test
  @DisplayName("管理端：已分析且无差距（含零感知差建行即终态的任务）⇒ hasGap=false；本类不对打分做任何现算覆写")
  void adminCardShowsNoGapForASuccessfulTaskWithoutGap() {
    givenSubmitted(List.of(submitted("FRL", 5)), List.of(submitted("FRL", 5)));
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD, true))
      .thenReturn(reportOf(false, ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.FALSE));

    ErlCardDTO card = erlCardService.getCard(COMPANY, null);

    assertThat(card.getDimensions().get(0).getPerceptionGap()).isZero();
    assertThat(card.getDimensions().get(0).getHasGap()).isFalse();
  }

  @Test
  @DisplayName("管理端：最新记录已分享 ⇒ shared=true（后续改动会新建未分享记录，按钮自然重新可点）")
  void adminCardReportsSharedFromTheLatestReport() {
    givenSubmitted(List.of(submitted("FRL", 3)), List.of(submitted("FRL", 7)));
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD, true))
      .thenReturn(reportOf(true, ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    assertThat(erlCardService.getCard(COMPANY, null).getShared()).isTrue();
  }

  @Test
  @DisplayName("公司端：吃 gap 服务按公司端选出的那条记录（最新已分享记录），有记录即 shared=true")
  void companyCardReadsTheSharedReportSelectedByTheGapService() {
    givenCompanyEnd();
    givenSubmitted(List.of(submitted("FRL", 3)), List.of(submitted("FRL", 7)));
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD, false))
      .thenReturn(reportOf(true, ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE));

    ErlCardDTO card = erlCardService.getCard(COMPANY, null);

    assertThat(card.getDimensions().get(0).getHasGap()).isTrue();
    assertThat(card.getShared()).isTrue();
    verify(erlGapAnalysisService).loadResult(COMPANY, PERIOD, false);
  }

  @Test
  @DisplayName("公司端未分享：gap 服务给 null ⇒ hasGap 恒 false、shared=false（是不下发，不是前端隐藏）")
  void companyEndCardShowsNoGapUntilItIsShared() {
    givenCompanyEnd();
    givenSubmitted(List.of(submitted("FRL", 3)), List.of(submitted("FRL", 7)));
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD, false)).thenReturn(null);

    ErlCardDTO card = erlCardService.getCard(COMPANY, null);

    assertThat(card.getDimensions().get(0).getHasGap()).isFalse();
    assertThat(card.getShared()).isFalse();
  }

  @Test
  @DisplayName("接口 1 的 shareable 喂的是同一份记录：isShareable 收到的 report 就是 loadResult 给的那份")
  void adminCardPassesTheLoadedReportToTheShareGate() {
    givenSubmitted(List.of(submitted("FRL", 3)), List.of(submitted("FRL", 7)));
    ErlGapAnalysisReportDTO report = reportOf(false, ErlGapAnalysisTaskStatusEnum.SUCCESS, Boolean.TRUE);
    when(erlGapAnalysisService.loadResult(COMPANY, PERIOD, true)).thenReturn(report);
    when(erlGapAnalysisService.isShareable(any(), any(), any(), any(), same(report))).thenReturn(true);

    assertThat(erlCardService.getCard(COMPANY, null).getShareable())
      .as("接口 1 与 17 / 27 必须同源、且吃同一份记录，否则「按钮亮着、点下去被拒」")
      .isTrue();
  }
```

- [ ] **Step 3: `ErlDimensionServiceImplTest` import 与 setUp**

- 删除 :8 `import com.gstdev.cioaas.web.erl.dto.ErlGapAnalysisResultDTO;`，在 :7 `import com.gstdev.cioaas.web.erl.dto.ErlDimensionDetailDTO;` 之后新增 `import com.gstdev.cioaas.web.erl.dto.ErlGapItemDTO;`
- 删除 :42 `import static org.mockito.ArgumentMatchers.anyBoolean;` 与 :44 `import static org.mockito.Mockito.lenient;`；新增 `import static org.assertj.core.api.Assertions.tuple;` 与 `import static org.mockito.Mockito.verify;`
- 删除 setUp 里 :126-137 的整段 `visibleArtifact` 打桩（从 `// \`visibleArtifact\` 是「这一端该看哪一份」的唯一口径` 那行注释起到 `});` 止）

- [ ] **Step 4: `ErlDimensionServiceImplTest` 差距分析段整段替换（:342 起至文件末尾）**

删除 `gapArtifact` 助手与 `adminDetailMapsGapsAndActionsFromTheArtifact`、`detailTakesTheItemsFromTheArtifactEvenWhenBothSidesScoreTheSame`、`companyEndDetailShowsNoGapUntilItIsShared` 三个用例，替换为：

```java
  // ── A3 维度详情页的 gaps / actions（2026-09-24 任务化：条目经 gap 服务按该维一个任务取）──────

  private ErlGapItemDTO item(ErlGapItemTypeEnum type, String title, ErlSeverityEnum severity, int sortOrder) {
    return ErlGapItemDTO.builder()
      .dimensionCode("FRL")
      .itemType(type)
      .title(title)
      .severity(severity)
      .sortOrder(sortOrder)
      .build();
  }

  @Test
  @DisplayName("管理端：gap 服务回的混合列表按 itemType 拆成 gaps / actions，字段与顺序逐字透传")
  void adminDetailSplitsTheItemsFromTheGapServiceIntoGapsAndActions() {
    when(erlGapAnalysisService.loadItems(COMPANY, PERIOD, "FRL", true)).thenReturn(List.of(
        item(ErlGapItemTypeEnum.GAP, "Monthly close still takes 20 business days", ErlSeverityEnum.HIGH, 0),
        item(ErlGapItemTypeEnum.GAP, "No board pack", ErlSeverityEnum.LOW, 1),
        item(ErlGapItemTypeEnum.ACTION, "Version the close checklist", null, 0)));

    ErlDimensionDetailDTO detail = erlDimensionService.getDetail("FRL", COMPANY, null, null);

    assertThat(detail.getGaps())
        .extracting(ErlGapItemDTO::getTitle, ErlGapItemDTO::getSeverity, ErlGapItemDTO::getSortOrder)
        .containsExactly(
            tuple("Monthly close still takes 20 business days", ErlSeverityEnum.HIGH, 0),
            tuple("No board pack", ErlSeverityEnum.LOW, 1));
    assertThat(detail.getActions()).singleElement().satisfies(action -> {
      assertThat(action.getItemType()).isEqualTo(ErlGapItemTypeEnum.ACTION);
      assertThat(action.getTitle()).isEqualTo("Version the close checklist");
      assertThat(action.getDimensionCode()).isEqualTo("FRL");
    });
  }

  @Test
  @DisplayName("gap 服务给空列表（没记录 / 没任务 / 无差距 / Python 不可用）：gaps / actions 是空数组，整页不受影响")
  void detailReturnsEmptyListsWhenTheGapServiceHasNoItems() {
    when(erlGapAnalysisService.loadItems(COMPANY, PERIOD, "FRL", true)).thenReturn(List.of());

    ErlDimensionDetailDTO detail = erlDimensionService.getDetail("FRL", COMPANY, null, null);

    assertThat(detail.getGaps()).isNotNull().isEmpty();
    assertThat(detail.getActions()).isNotNull().isEmpty();
  }

  @Test
  @DisplayName("公司端：按公司端选行去取（adminEnd=false 传给 gap 服务），选哪条记录不在本类判")
  void companyEndDetailAsksForTheCompanyEndItems() {
    when(erlAccessService.currentCaller()).thenReturn(ErlCallerDTO.builder()
      .userId("u1")
      .roleType(2)
      .adminEnd(false)
      .build());
    when(erlGapAnalysisService.loadItems(COMPANY, PERIOD, "FRL", false)).thenReturn(List.of());

    ErlDimensionDetailDTO detail = erlDimensionService.getDetail("FRL", COMPANY, null, null);

    assertThat(detail.getGaps()).isEmpty();
    assertThat(detail.getActions()).isEmpty();
    verify(erlGapAnalysisService).loadItems(COMPANY, PERIOD, "FRL", false);
  }
}
```

- [ ] **Step 5: `ErlAssessmentServiceImplTest` 触发点断言改口（:376-379）**

把
```java
    // 提交成功必须投递差距分析重生成（触发点 A）。2026-09-21 删附件预生成链路时，
    // ingestAttachmentsAfterCommit 与 regenerateGapAnalysisAfterCommit 是紧挨着的两行，
    // 多删一行本类 34 个用例没有一个会红 —— 这条 verify 就是补上那道闸。
    verify(erlGapAnalysisService).regenerate(eq(COMPANY), eq(PERIOD), any());
```
改为
```java
    // 提交成功必须投递差距分析对账（触发点 ①，任务化设计 §5），且要把请求线程里的 userId 带过去 ——
    // 异步侧没有登录态，新建记录 / 任务的 created_by 全靠它。这条 verify 是「多删一行没人会红」的那道闸。
    verify(erlGapAnalysisService).reconcileAsync(eq(COMPANY), eq(PERIOD), eq("u1"), any());
```

- [ ] **Step 6: 轻量校验（测试编译收口，必须全绿；仍不运行测试）**

```bash
mvn -q -pl gstdev-cioaas-web -am test-compile -DskipTests
```
期望：无输出、退出码 0。再确认测试代码里没有旧 API 残留：
```bash
grep -rn "getGapAnalysis\|shareGapAnalysis\|visibleArtifact\|regenerate(\|ErlGapAnalysisResultDTO\.Dimension\|getSharedSnapshot\|getGapSummary\|submissionSignature" gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/erl
```
期望：零命中。

---
### Task 12: 文档同步（design-doc / 根 CLAUDE.md / Javadoc 核验 / 台账提议）

**Files:**
- Modify: `D:/workspace/github/LG/docs/Exit Readiness/设计/design-doc.md` §5.8（:1935 起）、§6.6（:2235 起）、§7.5（:2615 起）
- Modify: `D:/workspace/github/LG/CLAUDE.md:153,166`
- Verify only: 过时 Javadoc 4 处（已在 Task 6 / 7 / 9 改掉）
- Modify（**需用户确认后再改**）: `docs/待优化项.md:5,211,213,215,216,218`、`docs/已完成优化.md`

> design-doc 的三节按设计稿回写「要点」，不复制设计稿全文；每处开头挂 `v4.65 / §0.39` 锚点并指向设计稿路径。§0.39 已在 2026-09-24 写好，本任务不动它。文档提交在 LG 父仓库（记忆规则：文档直接提 master，不另开分支），与 Java 子仓库的提交分开。

- [ ] **Step 1: design-doc §5.8 改写（:1935 起，原 `### 5.8 ai_erl_gap_analysis_item …` 一节）**

标题改为 `### 5.8 差距分析的四张表（**2026-09-24 起任务化**，v4.65 / §0.39；PRD §3.6）`，正文替换为以下要点（原 §5.8 正文与 §5.9 `ai_erl_gap_analysis_dimension` 一节保留原文但在各自标题后加 `（**2026-09-24 作废**，随 Python V029 删表；见 §5.8）`）：

- 归属：Java 持有编排状态两张表 `erl_gap_analysis_report`（报告分享记录）/ `erl_gap_analysis_dimension_task`（维度任务）；Python 持有 `ai_erl_gap_analysis_task`（生成日志 + 幂等标记）/ `ai_erl_gap_analysis_task_item`（AI 条目）。四张表全部无外键，按 id 列关联。列级定义以设计稿 §3.1–§3.4 为准，Java 建表脚本 `deploy/upgrade_doc/sprint119/V2__erl_gap_analysis_report.sql`。
- `erl_gap_analysis_report`：`(company_id, period)` 下可多条，「最新记录」= `created_at DESC, id DESC`；`shared / shared_at / shared_by` 只由接口 27 写、永不复位；`created_by` 由服务显式落触发者。索引 `idx_erl_gap_analysis_report (company_id, period, created_at DESC)`。
- `erl_gap_analysis_dimension_task`：`status` = `PENDING / RUNNING / SUCCESS / FAILED`（不加 CHECK、不加 `@Version`）、`has_gap`（SUCCESS 必填）、`source_founder_assessment_id / source_gsv_assessment_id`（取代 sha256 指纹）、`result_task_id`（复制任务指向持有内容的原任务）、`deleted`（仅未分享记录内软删）。部分唯一索引 `uk_erl_gap_analysis_dimension_task (erl_gap_analysis_report_id, dimension_code) WHERE deleted = false`。
- 不变量 I1–I4（照抄设计稿 §2）。
- 旧表处置：`erl_gap_analysis` / `erl_gap_analysis_item` 随 sprint119 Java 脚本 DROP；`ai_erl_gap_analysis` / `ai_erl_gap_analysis_dimension` / `ai_erl_gap_analysis_item` 验证后 V029 DROP；存量产物不回填（D11）。

- [ ] **Step 2: design-doc §6.6 改写（:2235 起 `### 6.6 Goldie 差距分析（E，PRD §3.6）`）**

在标题后加 `（**2026-09-24 任务化重写**，v4.65 / §0.39）`，正文替换为以下要点：

- 接口 17 `GET /erl/gapAnalysis` 出参：期次级只剩 `dimensions / analysisServiceUnavailable / shared / shareable(仅管理端)`；维度级 `dimensionCode / dimensionAbbr / bothSubmitted / analyzed / hasGap / dimensionStale(恒 false) / questionSetMismatch / mismatchSide / narrative / gaps[{title, severity}] / actions[{title}]`。**删除**：`summary / generatedAt / model / stale / generating / sharedAt / sharedBy / analyzedAt / gaps[].note / gaps[].evidenceMissing / actions[].why`（D7）。管理端遍历当前 Active 维度；公司端有已分享记录时只遍历该记录里的任务，没有时下发 Active 维度骨架。
- 接口 18 `POST /erl/gapAnalysis/generate`：仍同步（D10）；内部 `reconcile(force=true)` 后返回接口 17 同形结果；有维度未两端交齐 400、有维度 mismatch 不报错原样返回、派发失败 500 文案 `Gap analysis failed. Please try again.`。
- 接口 27 `POST /erl/gapAnalysis/share`：请求体不变；出参 `{shared, sharedAt, sharedBy}`；门槛五条与 400 文案（四种：未全提交 / 题库不一致 / 尚未分析完 / 已分享；窄竞态 `Content updated, please refresh.`）。
- 接口 1 `dimensions[].hasGap` / `shared` / `shareable` 全部来自 Java 表，不调 Python；`gapSummary` 字段删除。接口 21 只取该维一个任务的条目。
- Java ↔ Python 契约（内网直连、转发 Bearer、读超时 refresh 500s / items 10s）：`POST /api/ai/erl/gap-analysis/refresh` 入出参与 `POST /api/ai/erl/gap-analysis/items` 入出参逐字抄设计稿 §6.1 / §6.2；**删除** `GET /api/ai/erl/gap-analysis`、`POST /api/ai/erl/gap-analysis/share`、`analyzedContext` / `noGapDimensions` / `submissionSignature` / `index` / `code`；prompt v1.7 单维输入。

- [ ] **Step 3: design-doc §7.5 改写（:2615 起 `### 7.5 差距分析的生成、刷新与分享`）**

在标题后加 `（**2026-09-24 任务化重写**，v4.65 / §0.39）`，正文替换为以下要点：

- 术语与门槛：SOT / 可分析维度 / 报告就绪（ready，**报告级**，D3）/ 零感知差维度（照抄设计稿 §2）。未就绪时不建任何行，两端已交的维度屏上沿用 `Analyzing…`（D9）。
- 触发点表（① 提交后 `reconcileAsync` force=false；② 管理端读接口 17，60s 冷却键 `erl:gapAnalysis:cooldown:{c}:{p}`；③ 接口 18 同步 force=true）；`cio.erl.ai-enabled=false` 时 ① ② 整体跳过。
- `reconcile` 九步（照抄设计稿 §5 的编号步骤，含规划锁 `erl:gapAnalysis:plan:{c}:{p}` SETNX 60s、规划一个事务、派发在锁外）。
- 任务状态机与自愈（设计稿 §4 图 + 四条规则：全部 CAS、HTTP 失败不置 FAILED、零感知差建行即 SUCCESS、不加扫描器）。
- 读路径：选行只在 `visibleReport` 一处；条目按 `result_task_id ?? id` 一次批量取；取失败 ⇒ `analysisServiceUnavailable`。
- Share：`FOR UPDATE` 最新记录 → 二次校验仍是最新 → 五条门槛 → 置三列；已分享记录及任务不可变，后续改动新建记录并复制未变维度（`result_task_id` 链）。**S4「重生成复位 shared」作废**，创始人继续看上一次分享的记录直到管理端再次 Share。
- 并发 / 幂等 / 自愈汇总表（照抄设计稿 §8）。

- [ ] **Step 4: 根 `D:/workspace/github/LG/CLAUDE.md` ERL 段两句改口**

:153 的
```
Java (`CIOaas-api` 的 `erl/` 域) 是前端唯一出口；Python (`CIOaas-python/source/erl/`) **只做 LLM 生成与附件入库编排，不落 ERL 业务表、不做公司 ACL**（Java 已校验）：
```
改为
```
Java (`CIOaas-api` 的 `erl/` 域) 是前端唯一出口，并持有差距分析的**编排状态**（`erl_gap_analysis_report` 报告分享记录 + `erl_gap_analysis_dimension_task` 维度任务，状态机 PENDING → RUNNING → SUCCESS | FAILED 全部条件 UPDATE）；Python (`CIOaas-python/source/erl/`) **只做每任务一次的 LLM 生成并持有 AI 内容**（`ai_erl_gap_analysis_task` 生成日志 + `ai_erl_gap_analysis_task_item` 条目），**不落其它 ERL 业务表、不做公司 ACL**（Java 已校验）：
```
同段的接口示意里把 `POST {cio.erl.ai-base-url}/api/ai/erl/gap-analysis      Goldie 差距分析` 改为两行：`POST …/api/ai/erl/gap-analysis/refresh   按任务生成，同步回每任务 status/hasGap` 与 `POST …/api/ai/erl/gap-analysis/items     按任务 id 批量取条目`；若段内还保留 `attachments/ingest` 那行（2026-09-21 已删的链路），一并删除。

:166 的
```
- 一次 LLM 调用产出**一份**分析（设计 v4.4 起双 audience 方案取消，改为 GSV 生成 → `Share to founder` 单向分享）；prompt 外置在 `source/ai/prompts/erl/`，单份 `erl_gap_analysis.md`。
```
改为
```
- **每个维度任务一次 LLM 调用**（Python 并发 3，2026-09-24 任务化），GSV 端生成 → `Share to founder` 单向分享，已分享记录不可变、改动新建记录；三个触发点（提交后异步 / 管理端读接口 60s 冷却 / 手动 Generate 同步）共用 Java 的 `reconcile`；prompt 外置在 `source/ai/prompts/erl/`，单份 `erl_gap_analysis.md`（v1.7，单维输入）。
```

- [ ] **Step 5: 核验过时 Javadoc 4 处已清**

```bash
grep -rn "Python 落库.*复位分享位\|强制复位分享位\|erl_gap_analysis_item" gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/erl
```
期望：零命中（`ErlGapAnalysisService.java` 整文件已重写；`ErlDimensionConverter.java:24`、`ErlActionItemResponse.java:13`、`ErlDimensionConfig.java:57` 已在 Task 6 / 9 改口）。设计稿 §9.3 写的 `ErlGapAnalysisService.java:483-486` 行号对不上（接口文件只有 189 行，那段文字原在 :163-166 的 `isShareable` Javadoc），以文件为准。

- [ ] **Step 6: 台账（`docs/待优化项.md` / `docs/已完成优化.md`）—— 先向用户列出提议，确认后再改**

| 条目 | 提议 | 提议文字 |
|---|---|---|
| :5 接口 18 同步占用请求线程 | **保留 + 改口** | 首句改为「`ErlGapAnalysisServiceImpl#generate` 仍在请求线程上同步跑 `reconcile(force=true)`（D10），超时上限仍是 refresh 的 500s，网关 120s 先掐断」；删去「附件摘要每次全量重算」之外与指纹短路相关的句子；补一句「任务化后超时只是任务留 RUNNING、10 分钟后重投，不再丢一轮生成」 |
| :211 接口 1 与 17 `hasGap` 口径不一致 | **了结 → 已完成优化** | `- **接口 1 与接口 17 的 hasGap 收成同源**（2026-09-24）：任务化后两处都读 `erl_gap_analysis_dimension_task.has_gap`（`ErlCardServiceImpl#hasGap` / `ErlGapAnalysisServiceImpl#toDimension`），接口 1 不再调 Python（sprint119 任务化提交）` |
| :213 零感知差落库形态与契约未回写 | **了结 → 已完成优化** | `- **零感知差的落库形态定稿并回写文档**（2026-09-24）：Java 建任务时直接写 `SUCCESS + has_gap=false`，不送 Python；design-doc §5.8 / §7.5 已随任务化回写` |
| :215 分享后内容冻结 §7.5-S4 未回写 | **了结 → 已完成优化** | `- **分享冻结改为记录级不可变并回写 §7.5**（2026-09-24）：`shared_snapshot` 快照方案作废，已分享的 `erl_gap_analysis_report` 及任务永不改，后续改动新建记录（设计稿 D4）` |
| :216 两处不是真冻结 + 缺回滚 runbook | **改口保留** | 保留「公司端 `questionSetMismatch / bothSubmitted` 按当前提交状态现算、不随记录冻结」这半条（设计稿 §11 明确接受）；删去 `shared_snapshot` / V027 相关句子；「回滚 runbook」改指向 `deploy/upgrade_doc/sprint119/README.md` 的三侧一起回滚说明 |
| :218 `ai-enabled=false` 下零感知差维度永久进行中 | **改口保留** | 症状改写为「开关关闭时触发点 ① ② 整体不建记录 / 任务，屏上全维 `Analyzing…`（不再有旧 gaps 常驻 —— 旧表已 DROP）；手动 Generate 仍可建行」，成因句改为 `reconcileAsync` 顶部的开关短路 |
| 新增提议 A | **待优化项** | `- **refresh 读超时 500s 在任务化后盖不住 4~6 个任务的最坏耗时**（2026-09-24）：每任务一次 LLM + Python `Semaphore(3)` ⇒ 最坏 ≈ 120s + ⌈任务数/3⌉ × 366s（5 维全重跑 852s）；撞超时只是任务留 RUNNING、10 分钟后重投且 Python 命中 SUCCESS 日志不重复烧 LLM，故本次沿用 500s；若手动 Generate 频繁撞网关 120s，考虑接口 18 改投递 + 轮询（来源：sprint119 任务化实施计划）` |
| 新增提议 B | **待优化项** | `- **两个新 repository 的部分唯一索引冲突与 CAS rowcount 无自动化覆盖**（2026-09-24）：`gstdev-cioaas-web` 没有 H2 / Testcontainers，`ErlGapAnalysisDimensionTaskRepository#updateStatus / markDeleted` 与 `uk_erl_gap_analysis_dimension_task` 只能靠 E2E；建议引入 `@DataJpaTest` + Testcontainers(PG) 补仓储层用例（来源：同上）` |
| ~~新增提议 C~~ | —— | 已在 Task 8 Step 1 直接改口为 "All dimensions must be submitted by both sides before generating."（2026-09-24 计划核对），不再入台账 |

---

### Task 13: 测试（需用户下令后执行）

> 项目规则：开发中不自动跑测试。本任务只在用户明确下达「跑测试」后执行，一次性覆盖本轮全部改动。

- [ ] **Step 1: 单元测试**

```bash
cd D:/workspace/github/LG/java/CIOaas-api && mvn -pl gstdev-cioaas-web test -Dtest='Erl*Test' -Dsurefire.failIfNoSpecifiedTests=false
```
关注：`ErlGapAnalysisServiceImplTest`、`ErlPythonClientTest`、`ErlCardServiceImplTest`、`ErlDimensionServiceImplTest`、`ErlAssessmentServiceImplTest` 全绿；其余 `Erl*Test`（scoring / access / attachment / config / period / question）不应受影响。

- [ ] **Step 2: E2E（按记忆规则：先审核再跑，只挑 2–3 个代表场景，设计稿 §10）**

前置：Python V028 + Java sprint119 脚本已在 test 库执行、Python 新版已起、`cio.erl.ai-enabled=true`。场景：① 首次交齐 → 管理端页面 `Analyzing…` → 各维 `analyzed=true` → Share；② 一端改一维重交 → 管理端见新记录（该维回到 `Analyzing…`）、创始人仍见旧报告；③ 再 Share → 创始人切到新报告。

---

### Task 14: 提交（需用户确认）

> 项目规则：`git add` / `git commit` 前需用户确认；**禁止 `git push`**。两个仓库分开提交。

- [ ] **Step 1: Java 子仓库 `D:/workspace/github/LG/java/CIOaas-api`（分支 `sprint119`）**

```bash
git add deploy/upgrade_doc/sprint119 deploy/upgrade_doc/sprint118 gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/erl gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/erl docs/待优化项.md docs/已完成优化.md
git commit -m "feat(erl): move gap analysis onto a report/task model orchestrated in Java

Java now owns the orchestration state (erl_gap_analysis_report +
erl_gap_analysis_dimension_task, PENDING -> RUNNING -> SUCCESS | FAILED
with compare-and-set updates) while Python only runs one LLM call per
task and stores the AI content. All three triggers share a flat
reconcile(): plan lock -> plan transaction -> single refresh call ->
per-task CAS. Shared reports are immutable; changes fork a new report
and copy unchanged tasks via result_task_id. Card / dimension detail
read the Java tables; items are fetched in one batch by task id.

BREAKING CHANGE: interface 17 drops summary / generatedAt / model /
stale / generating / sharedAt / sharedBy / analyzedAt / note / why /
evidenceMissing, interface 1 drops gapSummary; Python contract moves to
POST /api/ai/erl/gap-analysis/refresh (tasks) + /items, GET and /share
are removed. Requires Python V028 and deploy/upgrade_doc/sprint119/V2.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 2: LG 父仓库 `D:/workspace/github/LG`（文档直接提 master）**

```bash
git add "docs/Exit Readiness/设计/design-doc.md" CLAUDE.md docs/superpowers/plans/2026-09-24-erl-gap-task-java.md
git commit -m "docs(erl): sync the design doc and CLAUDE.md with the gap analysis task model

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## 自查清单（设计稿条目 → 本计划任务）

| 设计稿 | 内容 | 落点 |
|---|---|---|
| §3.1 `erl_gap_analysis_report` 列 / 索引 / `created_by` 显式赋值 | 表、`idx_erl_gap_analysis_report`、审计四列 | Task 1 Step 1（DDL）、Task 2 Step 3（Entity）、Task 8 `newReport()` |
| §3.2 `erl_gap_analysis_dimension_task` 列 / 部分唯一索引 / 无 CANCELLED / 无 `@Version` | 表、`uk_erl_gap_analysis_dimension_task … WHERE deleted = false`、`idx_…_report`、`status varchar(16)`、`has_gap`、`result_task_id`、`deleted` | Task 1 Step 1、Task 2 Step 1 / 4、Task 3 Step 2 |
| §4 状态机：CAS、HTTP 失败不置 FAILED、零感知差建行即 SUCCESS、10 分钟超龄重投、不加扫描器 | `updateStatus` 条件 UPDATE；`reconcile` 派发失败向上抛不改任务；`newTask()`；`isDispatchable()`；无 `@Scheduled` | Task 3 Step 2、Task 8 Step 1（`reconcile` / `applyResults` / `claimDispatchable` / `isDispatchable` / `newTask`）、Task 10 用例 `redispatchesFailedAndStaleRunningTasks` / `leavesTasksRunningWhenTheRefreshCallFails` / `appliesTheRefreshResponseWithACompareAndSetPerTask` |
| §5 触发点 ① ② ③ 与 `ai-enabled` 口径 | `reconcileGapAnalysisAfterCommit` → `reconcileAsync`；`find` 管理端 + 冷却 → `reconcileAsync`；`generate` 同步 `reconcile(force=true)`；开关只挡 `reconcileAsync` | Task 9 Step 1–2、Task 8 Step 1（`find` / `generate` / `reconcileAsync`）、Task 10 用例 `adminReadTriggersAnAsyncReconcileUnderCooldown` / `skipsTheAsyncReconcileWhenTheAiSwitchIsOff` / `manualGenerationIgnoresTheAiSwitch` |
| §5 步骤 1–9（锁 / ready / source / 首建 / 已分享复制 / 未分享软删重建 / CAS 认领 / 释放锁 / 派发落状态） | `reconcile` + `plan` + `targetSources` / `createReportWithTasks` / `forkSharedReport` / `replaceTasksInUnsharedReport` / `changedDimensions` / `claimDispatchable` / `applyResults`；锁键 `erl:gapAnalysis:plan:{c}:{p}` SETNX 60s | Task 8 Step 1、Task 10 Step 1 全部写路径用例 |
| §6 契约：内网直连、转发 Bearer、500s / 10s、refresh 入出参、items 入出参、删 GET / share | `ErlPythonClient.refresh / fetchItems`；`ErlGapAnalysisRequestDTO` / `ErlGapAnalysisResultDTO` / `ErlGapItemsResultDTO` | Task 4 Step 1–3、Task 5、`ErlPythonClientTest` |
| §7.1 选行只此一处 | `visibleReport()` + `loadResult()` | Task 8 Step 2、Task 10 用例 `adminEndReadsTheLatestReportEvenWhenItIsUnshared` / `companyEndReadsOnlyTheLatestSharedReport` |
| §7.2 接口 17 出参（期次级 / 维度级 / 删除字段 / 公司端遍历任务 / `dimensionStale` 恒 false / D9） | `ErlGapAnalysisDTO` / `ErlGapDimensionDTO` / `ErlGapItemDTO` + Response + Converter；`assemble` / `renderedCodes` / `toDimension` / `fetchItems` | Task 4 Step 7–9、Task 6、Task 8 Step 2、Task 10 读路径用例 |
| §7.3 接口 1 不调 Python、接口 21 只取一个任务 | `ErlCardServiceImpl.getCard` / `hasGap`；`ErlDimensionServiceImpl.getDetail` → `loadItems` | Task 9 Step 3–9、Task 11、Task 8 `loadItems` |
| §7.4 Share 五条 + `FOR UPDATE` + 窄竞态 400 | `isShareable`、`share`、`lockLatestReport`、`lockLatestByCompanyIdAndPeriod` | Task 3 Step 1、Task 8 Step 1–2、Task 10 用例 `shareGateRequiresAllFiveConditions` 与 7 个 `share*` 用例 |
| §9.1 Java 脚本（DROP 旧两表 + 建新表 + 索引）、sprint118 V1 与 README 改口 | `sprint119/V2__erl_gap_analysis_report.sql` + README；sprint118 删 §5.7 / §5.8 / 两索引 + 头注 + README | Task 1 |
| §9.3 同批清理（冷却键挂到 reconcile、两个 DTO 重写、过时 Javadoc 4 处、文档与台账） | `acquireRegenerationCooldown` 留在 `find`；DTO 重写；Javadoc 在 Task 6 / 7 / 9；文档在 Task 12 | Task 4 / 6 / 7 / 8 / 9 / 12 |
| §10 Java 测试策略 | 规划逻辑 / 客户端契约 / 接口 1 / 17 / 21 / 27 拼装全部有用例；仓储层（部分唯一索引、CAS rowcount）无 H2 不可测，记台账提议 B | Task 5 / 10 / 11 / 12 Step 6 |
| 计划格式：无 commit 步骤混入开发任务、测试与提交单列且需用户确认 | Task 13 / 14 | — |
