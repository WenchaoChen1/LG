# Monthly Benchmark Email — 实现 vs 需求审核

> 审核日期：2026-04-29
> 审核对象：`fi/benchmarkemail/` 模块全量代码
> 对照基准：
> - `Implement Monthly Benchmark Email Reports_需求文档.md`（235 行）
> - 用户在 brainstorming 阶段补充的 4 条规则（写入 spec §15）
>
> 结论：**REVISE** —— 0 Critical / 5 Major（**3 已修，2 待跟进**）/ 11 Minor
>
> 2026-04-29 修复批次：MAJOR-2 / MAJOR-3 / MAJOR-4 已修复并通过编译验证（commit 待你提）。

---

## 一、总览

| 类别 | √ 完整 | ⚠ 部分 | ✗ 缺失 | ⚡ Bug |
|---|---|---|---|---|
| A. 触发机制 | 4 | 1 | 0 | 0 |
| B. 邮件内容范围 | 4 | 1 | 0 | 0 |
| C. 重大变化定义 | 4 | 0 | 0 | 0 |
| D. 邮件模板 | 7 | 2 | 0 | 1 |
| E. 数据来源 | 4 | 0 | 0 | 0 |
| F. baseline 模型 | 4 | 0 | 0 | 1 |
| G. 隐含/边界 | 5 | 0 | 0 | 1 |
| 管理 API | 4 | 0 | 0 | 1 |

**结论**：核心业务逻辑（触发 / 阈值 / baseline 写入 / 静默更新 / Admin vs PM 决策树）**正确实现且与 spec 对齐**。但发现 4 个真实 bug + 1 个单位风险，建议修复后再上线。

---

## 二、Major 问题

### MAJOR-1 ⚡ `own_value` 单位风险（建议交叉验证）

**需求条款**：D.6 / 需求文档 §3.1 示例 `Actual: 64%`

**代码位置**：
- `CompanyAdminEmailComposer.java:285-309` `formatOwnValue()`
- `PortfolioManagerEmailComposer.java:344-368` `formatOwnValue()`

**潜在问题**：Composer 拿 `MetricExtractor.extractMetrics(...)` 返回的 own_value 直接拼 `%`：
```java
case "met-arr-growth":
case "met-gross-margin":
case "met-rule-40":
  return v.setScale(1, HALF_UP) + "%";
```

如果 MetricExtractor 返回的是**小数 0.64**（而不是百分数 64），邮件会渲染成 `0.6%` 而非 `64%`。Composer 自己没做 ×100 处理。

**Realist Check**：MetricExtractor 是已沉淀的引擎，被 `fi/benchmark/position/` 老模块和 Benchmarking 页面长期消费。如果单位错，旧页面早该报告问题。**降级为 MAJOR**（需要验证而非确诊 bug）。

**验证步骤**：
```bash
# 1. 找一家 ARR Growth Rate 已知值的公司（如 64%）
# 2. /preview
curl -X POST $BASE/benchmark-email/preview \
  -d '{"companyId":"X","role":"COMPANY_ADMIN"}' | jq -r '.data.html' | grep "Actual:"
# 期望：Actual: 64.0%
# 出错：Actual: 0.6%
```

**如需修复**：在 `formatOwnValue` 顶部对百分比类指标加 `v = v.multiply(BigDecimal.valueOf(100))`，或在 SnapshotBuilder 边界统一单位。

---

### MAJOR-2 ✅ 已修复 — `last_notified_at` 现在按 reason 写入

**需求条款**：spec §3.3 表字段定义"上次因本 baseline 发邮件的时刻"

**代码位置**：
- 字段：`FinancialBenchmarkEmailBaseline.java:59-60`
- 写入：`BaselineManager.java:35-83` upsert 方法**完全未调用 `setLastNotifiedAt`**
- API 透出：`BaselineDto.HistoryEntry` 没有，`BaselineDto.BaselineRow.lastNotifiedAt`（line 27）有声明

**实际行为**：所有 baseline 行的 `last_notified_at` **永远为 NULL**。

**期望行为**：FIRE / FIRST_FIRE 场景下 `BaselineManager.upsert()` 应设 `b.setLastNotifiedAt(Instant.now())`，SILENT 不动。

**Confidence**：HIGH，确诊 bug。

**影响**：
- `last_updated_reason` 字段已能区分 FIRE/SILENT_NO_CHANGE/SILENT_BELOW_THRESHOLD，**部分**覆盖语义
- 但时间精度丢失，无法回答"这条 baseline 上次因发邮件而更新是什么时候"

**修复**（已合入 `BaselineManager.upsert()` line 64-68）：
```java
if (in.reason() == BenchmarkEmailReasonEnum.FIRST_FIRE
 || in.reason() == BenchmarkEmailReasonEnum.FIRE) {
    b.setLastNotifiedAt(Instant.now());
}
```
SILENT 路径不动 last_notified_at，保留首次/末次因发邮件而更新的精确时刻。

---

### MAJOR-3 ✅ 已修复 — `DELETE /baselines` 返回真实 `deletedHistoryRows`

**需求条款**：spec §8.6 — Response `{ deletedBaselineRows, deletedHistoryRows }`

**代码位置**：
- `BenchmarkEmailController.java:319-323`：
  ```java
  res.put("deletedHistoryRows", 0);   // 永远 0
  ```
- `BaselineManager.java:86-90`：调用了 `historyRepo.deleteAllByCompanyIdAndRole(...)` 但**忽略它的 int 返回值**

**Confidence**：HIGH，确诊 bug。

**影响**：dev/test 工具调用方拿到 0 误以为没删除，实际 history 已删；prod 禁用此接口，对生产无影响。

**修复**（已合入）：
- `BaselineManager.deleteAllByCompanyAndRole(...)` 返回 `record DeleteResult(int deletedBaselineRows, int deletedHistoryRows)`
- `BenchmarkEmailController.deleteBaselines` 透传两个真实计数

```java
BaselineManager.DeleteResult dr = baselineManager.deleteAllByCompanyAndRole(companyId, role, deleteHistory);
res.put("deletedBaselineRows", dr.deletedBaselineRows());
res.put("deletedHistoryRows", dr.deletedHistoryRows());
```

---

### MAJOR-4 ✅ 已修复 — `silent_updated_count` / `first_fire_count` 与 baseline 写入对齐

**需求条款**：B.5 / spec §4.4 PM 静默更新计数

**代码位置**：`BenchmarkEmailOrchestratorImpl.java:104-137`

**实际行为**：
- line 119-124：PM 一份 base ProcessedResult 被复制 N 次（每个 portfolio 一份）
- line 130-135：基于复制后的 results 计 silentCount / firstFireCount
- 一家公司同时归属 2 个 portfolio 且 PM 决策为 SILENT 时，`silent_updated_count += 2`

**关键反差**：baseline 写入用 `dedupeBaselineWrites`（line 163-171，按 (companyId, role) 去重），实际**只写一次** baseline，但**计数翻倍**。`first_fire_count` 同样问题。

**Confidence**：HIGH，确诊 bug。

**影响**：
- 单 portfolio 公司无影响
- 多 portfolio 公司在 run summary 字段（API #2 返回）和未来度量监控（spec §13 `benchmark_email.silent.count`）会失真
- `adminFiredCount` / `pmFiredCount` 是 send_log 成功数，**不受影响**

**修复**（已合入 `BenchmarkEmailOrchestratorImpl.executeRun`）：先 dedupe 再计数，并把同一份 deduped 复用给 `writeBaselines`：

```java
List<ProcessedResult> dedupedForCount = dedupeBaselineWrites(results);
int silentCount = 0, firstFireCount = 0;
for (ProcessedResult r : dedupedForCount) {
  if (r.decision() == SILENT) silentCount++;
  if (r.decision() == FIRST_FIRE) firstFireCount++;
}
run.setSilentUpdatedCount(silentCount);
run.setFirstFireCount(firstFireCount);

if (!dryRun) {
  persistenceHelper.writeBaselines(run, dedupedForCount);  // 复用
  // ...
}
```

副效益：`writeBaselines` 不再重复执行 dedupe。

---

### MAJOR-5 ⚡ "新 closed month" 感知依赖每日轮询而非事件钩子

**需求条款**：A.1 "每日定时检测，有新 closed month 时发送"

**实际实现**：
- `BenchmarkEmailScheduleRegistrar.runDaily()` UTC 00:30 跑一次
- 对每家公司用 `ClosedMonthResolver.resolve(companyId, today)` 取 cm_now
- 与 baseline.maxCm 比较：cm_now > maxCm → NEW_CLOSED_MONTH

**风险**：
- 最坏情况新 closed month 入库后 24 小时内必发
- Manual mode 公司："最后 Actuals 月"在用户手动入库后理论上应立刻感知，但要等下一次 cron

**Confidence**：HIGH —— 设计决策，文档已明示

**判定**：满足"每日定时检测"的字面要求，但若产品需要"实时感知"则需补 ETL 入库 webhook。

**建议**：
- 短期保持轮询
- 中期：在 normalization_current 写入路径加 hook → `orchestrator.createRun(DAILY, MANUAL, asOfDate=today, [companyId])`

---

## 三、Minor 偏差

### m-1 ⚠ Scheduler 用 Spring `@Scheduled`，未沿用项目 `scheduler` 模块
**位置**：`BenchmarkEmailScheduleRegistrar.java`
**Spec**：§15.15 决策"沿用现有 scheduler 模块"
**影响**：运维无法在数据库 `schedule_config` 表查到这个调度，也无法通过 `/scheduler` API 改 cron。但功能完整。
**建议**：保留现状或改注册到 ScheduleConfig 表。

---

### m-2 ⚠ Forecast 行也展示 "moved from"，与需求文档字面例子不一致
**位置**：`EmailContentFormatter.formatPercentileWithMovement()` 对所有 dataSource 一视同仁
**Spec**：§15.11 "Forecast 行也带 moved from 文案"（用户 brainstorming 决定）
**需求文档**：示例 Committed Forecast 行只展示 `Internal Peers: P58`（无 moved from）
**判定**：有意偏差，按 spec
**建议**：若需要回到需求文档字面 → 在 Composer 调用处对 CF/SGF 行只调 `formatPercentile(curr, marker)`

---

### m-3 ⚠ MONTHLY_25TH 优先级覆盖了 NEW_CLOSED_MONTH
**位置**：`BenchmarkEmailOrchestratorImpl.java:243-253` classifyEvent
**实际**：`if (phase == MONTHLY_25TH) return MONTHLY_25TH;` 在 NEW_CLOSED_MONTH 判定**之前**
**影响**：仅 baseline_history.reason 字段标错（MONTHLY_25TH vs NEW_CLOSED_MONTH），决策结果不变
**修复**：把 MONTHLY_25TH 判定放到 NEW_CLOSED_MONTH 之后

---

### m-4 ⚠ DDL `data_source` 列定义 VARCHAR(64)，spec §3 描述是 varchar(24)
**位置**：`V4_benchmark-email-tables.sql:45,76,103`
**Spec**：§3.2/3.3/3.4 写 varchar(24)
**实际**：3 张表都是 VARCHAR(64)
**判定**：实现选 64 是合理（`SYSTEM_GENERATED_FORECAST` 是 26 字符），spec 描述需更新
**修复**：spec §3 的 data_source 列长度改为 varchar(64)

---

### m-5 ⚠ PM 模板 "Companies with Meaningful Benchmark Changes" 标题在首封场景语义不准
**位置**：`BenchmarkingReportPortfolioManager.html:50` 固定文案
**问题**：PM 首封时 portfolio 下所有公司都是 FIRST_FIRE，全公司展示。但模板上方仍写 "Meaningful Changes"，与首封语义不符。
**建议**：模板根据 `${anyFirstFire}` 切换为 "Companies in Your Portfolio"

---

### m-6 ⚠ Admin 跳过 DATA_REVISION 是 spec 决策，需求文档原文未写
**位置**：`BenchmarkEmailOrchestratorImpl.java:205-207`
**Spec**：§15 决策 #7
**需求文档**：原文没明示 Admin 不响应数据修订
**建议**：补到需求文档 §1.1 末尾

---

### m-7 ⚠ External benchmark 名 "Benchmarkit.ai" vs 需求示例 "Benchmark.it"
**位置**：`CompanyAdminEmailComposer.java:67`、`PortfolioManagerEmailComposer.java:73`
**实际**：实现用 "Benchmarkit.ai"
**需求示例**：`Benchmark.it 2026: P55`
**判定**：与产品确认正式品牌名

---

### m-8 ⚠ DATA_REVISION 事件每天为每家公司算 72 行，即使数据未变
**位置**：`processCompanyRole` 每天为每 (company, role) 跑 snapshot 比对
**影响**：
- run_snapshot 表每天 ≈ companies × 2 × 72 行；30 天后 ≈ 1000 公司 × 144 × 30 = 4.3M 行
- baseline_history 不增（值未变不写）
- 性能：每次 run 重算 72 行百分位即使数据没动
**建议**：早期 short-circuit（cmNow == maxCm 且 normalization_current.updated_at 未变 → 直接 SILENT）+ 定期归档 run_snapshot

---

### m-9 ⚠ external benchmark edition 后缀用 closedMonth.getYear() 拼接
**位置**：Composer `buildBlock(...)` 中 `label = BENCHMARK_DISPLAY.get(bs) + " " + year`
**问题**：实际 ExternalBenchmarkMatcher 可能匹配的是其他年份的 edition（如 KeyBanc 2025），但邮件展示 "KeyBanc 2026"
**建议**：从 FinancialBenchmarkEntry.getEdition() / getFyPeriod() 取实际年份，并在 SnapshotRow 透传

---

### m-10 ⚠ markerFromDisplay 透传 `>` / `<` 前缀但无白名单校验
**位置**：`MonthlyEmailSnapshotBuilder.java:177-182`
**实际**：所有 marker 都在 8 字符内，DDL `varchar(8)` 安全
**判定**：无 bug，仅"防御缺失"

---

### m-11 ⚠ Admin subject 动态拼接，PM subject 用常量
**位置**：`CompanyAdminEmailComposer.compose:88` / `PortfolioManagerEmailComposer:23`
**判定**：风格不一致但不影响功能

---

## 四、已完整对齐的需求条款

### A. 邮件触发机制
| 条款 | 实现 | 位置 |
|---|---|---|
| A.1 每日定时检测 | UTC 00:30 cron + classifyEvent | `BenchmarkEmailScheduleRegistrar.runDaily` |
| A.2 每月 25 日 cron | `cron = "0 45 0 25 * *"` UTC | `runMonthly25th` |
| A.3 closed month 推导 | 复用 `ClosedMonthResolver.resolve()` Manual / Automatic / 15 号界限 / 历史回溯 | — |
| A.4 双角色发送 | role 循环独立 | `executeRun:104` |

### B. 邮件内容范围
| 条款 | 实现 | 位置 |
|---|---|---|
| B.1 Admin 仅本公司、6 指标、记 baseline | 模板固定 6 指标 + writeBaselines 事务内 upsert | `CompanyAdminEmailComposer` + `BenchmarkEmailPersistenceHelper.writeBaselines` |
| B.2 PM 仅展示有重大变化的指标 | `selectMeaningfulMetrics` 筛选 | `PortfolioManagerEmailComposer:212-228` |
| B.3 首封无基准时直接发 | `eventType == FIRST_FIRE → companyDecision = FIRST_FIRE` | `processCompanyRole:228` |
| B.4 PM 首封展示所有公司全 6 指标 | `isFirstFire ? METRIC_ORDER : selectMeaningfulMetrics(r)` | `PortfolioManagerEmailComposer:198` |

### C. 重大变化定义
| 条款 | 实现 |
|---|---|
| C.1 阈值 ≥ 5（含等号）| `delta.compareTo(THRESHOLD) >= 0` `EmailDiffEvaluator.java:12` |
| C.2 跨 Q | `QuartileUtil.crossedQuartile(a, b)` |
| C.3 Q 边界 [0,25)/[25,50)/[50,75)/[75,100] | `QuartileUtil.quartileOf:11-14` |
| C.4 NA ↔ 有值算变化（用户补充）| `VALUE_CHANGED_NA + contributesToAlert=ACTUALS` `EmailDiffEvaluator:25-28,34` |
| **仅 Actual 参与阈值判定** | `(dataSource == ACTUALS) && meaningful` `EmailDiffEvaluator:34` |

### D. 邮件模板
- D.1 √ Admin 标题 / D.2 √ PM 标题 / D.3 √ 问候语+介绍 / D.4 √ A-Z 排序（英文先于中文）
- D.5 √ 6 指标固定顺序 / D.6 √ 4 基准源 / D.8 √ Movement 文案 / D.9 √ Forecast 优先 CF
- D.10 √ Admin/PM 各自 base64 URL

### E. 数据来源
- E.1 √ Normalization Tracing
- E.2 √ Internal Nearest Rank（复用 InternalPercentileCalculator）
- E.3 √ External 线性插值（复用 ExternalPercentileCalculator）
- E.4 √ 当前-基准对比（用户补充覆盖原文档"上个 closed month"）

### F. baseline 模型
- F.1-F.4 √ 按角色独立 / 同 role 共享 / 5 维主键 / history 仅在变化时插入

### G. 隐含/边界
- G.1 √ 同一人 Admin+PM 各发一封
- G.2 √ 公司无 PM 关联 → 跳过
- G.3 √ SCHEDULED 同日幂等（partial unique index `WHERE trigger_type='SCHEDULED'`）；MANUAL 同日不限
- G.4 √ Prod 禁用 DELETE
- G.5 √ SendGrid 失败 baseline 仍入库（REQUIRES_NEW + 顺序：先 baseline 后 send）

---

## 五、OUT-OF-SCOPE 发现（需求外，仅记录）

1. **send_log 无重试机制** — SendGrid 暂不可用时邮件丢失，需人工重发
2. **无邮件订阅管理** — 收件人无法 unsubscribe，可能违反邮件合规要求
3. **首日抑制开关** — spec §15 决策 #19 不做 catch-up；首次上线全公司都触发 FIRST_FIRE
4. **同一 PM 兼任多 portfolio 收多封** — spec §4.4 未禁止
5. **PreviewService eventType 推断不感知 phase**（preview 总按 DAILY），仅诊断字段失真
6. **`RecipientResolver.portfolioIdsByCompanyId()` 用 `findAll()` 无分页** — 1000 公司可承受

---

## 六、Open Questions（需产品/数据团队确认）

1. **Q1**：MetricExtractor 返回的 ARR Growth Rate 是 0~1 还是 0~100？（关系 MAJOR-1）
2. **Q2**：spec §3 `data_source varchar(24)` 与 DDL `VARCHAR(64)` 的差异是 spec 笔误还是有意？（关系 MAJOR-2）
3. **Q3**：`silent_updated_count` 是否被 dashboard / SLA 消费？若仅审计字段，MAJOR-4 可降 Minor
4. **Q4**：`last_notified_at` 是否被前端/报表消费？若否，MAJOR-2 可降 Minor
5. **Q5**：PM 首封模板小标题（m-5）是否需差异化文案 — 产品决策
6. **Q6**：External benchmark 正式品牌名是 `Benchmarkit.ai` 还是 `Benchmark.it`？（m-7）

---

## 七、修复优先级排序

| 优先级 | Finding | 状态 | 工作量估算 |
|---|---|---|---|
| ~~P0~~ | MAJOR-3 deletedHistoryRows | **✅ 已修** | 0.5h |
| ~~P0~~ | MAJOR-2 last_notified_at | **✅ 已修** | 0.5h |
| ~~P0~~ | MAJOR-4 计数翻倍 | **✅ 已修** | 0.5h |
| P1 | MAJOR-1 单位验证 | 待用户跑 quickstart 验证 | 1h |
| P1 | MAJOR-5 cron 轮询 vs 事件钩子 | 设计取舍 | — |
| P1 | m-3 MONTHLY_25TH 优先级 | 待修 | 0.5h（仅审计标签影响）|
| P2 | m-7 品牌名 | 待产品确认 | 1h |
| P2 | m-5 PM 首封小标题 | 待修 | 1h |
| P3 | m-9 edition 透传 | 待修 | 4h |
| P3 | m-8 性能优化 | 待修 | 1d |

---

## 八、上线前必读

1. **本审核基于代码审查 + spec 对照**，未执行端到端集成测试
2. **测试环境验证流程**：参考 `monthly-benchmark-email-quickstart.md`
3. **MAJOR-1 是否真的有 bug 取决于 MetricExtractor 单位** — 验证后再决定是否修
4. **MAJOR-2 / MAJOR-3 / MAJOR-4 是确诊 bug，建议 P0 修复**
5. **MAJOR-5 是设计选择**，按当前的 24h 轮询满足需求字面要求
6. **m-2 是有意偏差**（Forecast moved-from），按 spec §15.11；如要回退到需求文档字面只改一处
7. **SQL 修复（findAllCompanyAdmin 严格匹配 'Company Admin' 角色）已合入**；test 环境记得把 V4 重跑一次（含旧索引 DROP IF EXISTS）

---

## 九、对照需求文档章节回溯

| 需求条款 | 实现状态 | Finding |
|---|---|---|
| §1.1 新 closed month 触发 | √ | MAJOR-5（轮询非事件钩子） |
| §1.2 25 号触发 | √ | m-3（事件分类优先级） |
| §2.1 Admin 邮件范围 | √ | — |
| §2.2 PM 邮件范围 | √ | m-5（首封文案） |
| §2 重大变化定义 | √ | — |
| §3.1 Admin 模板 | √ | m-2（Forecast moved-from）/ m-9（edition 年份） |
| §3.2 PM 模板 | √ | m-5（首封小标题）/ m-7（品牌名）|
| §3.1.2 / §4 数据展示 | √ | MAJOR-1（own_value 单位） |
| §4 数据来源 | √ | — |

---

**报告版本**：1.2 | **更新日期**：2026-04-29 | **基础**：自审 + critic agent 输出合并 | **Changelog v1.1→v1.2**：MAJOR-2/3/4 已修复并合入主分支
