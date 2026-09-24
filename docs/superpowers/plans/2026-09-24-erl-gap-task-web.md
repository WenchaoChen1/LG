# ERL 差距分析任务化 — Web 侧清理计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 随 Java sprint119「差距分析任务化」（设计稿 §7.2：接口 17 / 1 / 21 出参裁剪），把前端契约层（`response.ts` / `dto.ts`）、归一层（`erlService.ts`）与对应单测里的死字段删干净；**页面行为零变化**。

**Architecture:** 只动 `services/api/exitReadiness/{response,dto}.ts → services/service/exitReadiness/erlService.ts` 这条 Response→DTO 转换链和它的测试。六态判定 `erlGapState.ts` 与页面组件**不改行为**（`dimensionStale` 后端恒发 `false` 但字段保留一版，`updating` 分支原样留着）。唯一还读 `note / why / evidenceMissing` 的 `PriorityGapsPanel`（2026-09-15 起全仓无 import 的死组件）先做三行止血保证 `tsc` 过关，整体删除单列一个「需用户确认」的 Task。

**Tech Stack:** React 16 / UmiJS 3 / TypeScript / Jest

**依赖/顺序：** 在 Java 计划部署后实施（前端解耦，先后都不会坏）

---

> 关联文档：设计稿 [2026-09-24-erl-gap-analysis-task-model-design.md](../specs/2026-09-24-erl-gap-analysis-task-model-design.md)（§7.2 出参增删 / D9 不加新态 / §10 Web 段 / §11 不做）· 前端规范 `web/CIOaas-web/standards/{coding,architecture,git}.md` · 仓库分支 `sprint119`（已核实 `git branch --show-current`）。

## 0. 删除清单与消费方核实结论

逐字段 grep 全仓 `src/`（含测试）后的结论——**每个字段都只在契约层 / 归一层 / 测试 fixture 里出现，没有一个还有页面渲染方或逻辑消费方**（唯一例外是死组件 `PriorityGapsPanel`，见 ②）：

| 设计稿 §7.2 删除项 | 接口 | `response.ts` | `dto.ts` | `erlService.ts` | 页面 / 逻辑消费方 | 结论 |
|---|---|---|---|---|---|---|
| `gapSummary` | 1 | :106 | :150 | :477 | 无（台账 :88 已登记「只映射不渲染」） | 删 |
| `summary` | 17 | :625 | :636 | :1053 | 无（`ErlGapBlock` 2026-09-21 撤下，台账 :291） | 删 |
| `sharedAt` / `sharedBy` | 17 | :628-629 | :639-640 | :1055-1056 | 无（`ErlGapBlock` / `useErlCard` 2026-09-20 撤下 prop） | 删 |
| `generatedAt` / `model` / `stale` / `generating` | 17 | :631-634 | :642-645 | :1083-1086 | 无（`ErlGapBlock.tsx:362` 只有注释提到） | 删 |
| `analyzedAt` | 17 | :606-607 | :621-622 | :1077 | 无（台账 :287 已登记） | 删 |
| `gaps[].note` / `gaps[].evidenceMissing` | 2 / 17 | :193 / :195 | :216 / :218 | :315 / :319 | **仅** `PriorityGapsPanel.tsx:81-84`（死组件） | 删 + 止血 |
| `actions[].why` | 2 / 17 | :200 | :223 | :547 / :1081 | **仅** `PriorityGapsPanel.tsx:95`（死组件） | 删 + 止血 |
| `dimensionStale` | 17 | :612 | :624 | :1078 | `erlGapState.ts:86`（六态 `updating`）、`useErlCard` 轮询判据 | **保留不动**（设计稿 §7.2 恒 false 兼容一版） |

② `PriorityGapsPanel.tsx`：`grep PriorityGapsPanel` 全仓只有它自己、`GapDetailsModal.tsx:25/294` 与 `DimensionPage.tsx:28` 的**注释**、README :91 与台账 :184/:277 —— 零 import。它没有专属 less（用域级 `components/index.less`）、没有测试文件。

③ 接口 27 `ErlGapShareResponse` / `ErlGapShareResultDTO` 的 `sharedAt` / `sharedBy` **不在** §7.2 删除清单里（那是 Share 的出参，`useErlCard.shareToFounder` 只读 `result.shared`），本计划不动。

## 1. 明确不做

- 不加 `waiting` / `failed` 新态（设计稿 D9 / §11：FAILED 由后端自动重投，屏上仍是 `Analyzing…`）。
- `useErlCard.ts` 的轮询逻辑（退避表 / 6 轮预算 / `pollExhausted`）一行不动。
- Share 请求体不动（接口 27 仍只发 `companyId` / `period`，不带 analysisId）；接口 27 出参类型不动（见 §0-③）。
- 六态优先级不动：`erlGapState.ts` / `erlGapState.test.ts` **零改动**，`dimensionStale` 归一保留。
- 设计稿给接口 17 新增的期次级 `shareable` **不声明**：前端 Share 门槛继续取接口 1 的 `card.shareable`，无消费方不镜像（同 `ErlWeightAppliedResponse` 的 YAGNI 口径）。
- 不改 design-doc（父仓库文档由 Java 计划回写 v4.65 / §0.39）。

## 2. 轻量校验命令（每个 Task 末尾）

```powershell
# 在 D:/workspace/github/LG/web/CIOaas-web 下执行
npm run lint:fix
npm run tsc
```

⚠️ `npm run tsc` 目前是已知的「空闸门」（台账 :285：`@types/color-convert` 是空 stub，`tsc` 在建 program 阶段就 `TS2688` 中止）。**2026-09-24 实测**绕开后全仓存量 1563 条报错、其中 **ERL 相关路径 0 条**，故本计划以下面这条为准（PowerShell）：

```powershell
npx tsc --noEmit -p tsconfig.json --types jest,node 2>&1 | Select-String -Pattern "exitReadiness|ErlCard"
```

**通过标准 = 上面这条输出 0 行**（Task 1 / 2 末尾允许残留的例外在各 Task 内写明）。`.less` 只手改点名的那几行，**不要**对 less 跑 `prettier --write`（台账 :90）。

## 3. 文件结构

```
web/CIOaas-web/
├── src/services/api/exitReadiness/
│   ├── response.ts                 Task 1  接口 1 / 2 / 17 的 Response：删 8 组死字段、改 2 段注释
│   └── dto.ts                      Task 1  对应 DTO：同上
├── src/services/service/exitReadiness/
│   ├── erlService.ts               Task 2  mapGapItem / fetchErlCard / fetchErlDimensionDetail / mapGapAnalysis
│   └── erlService.test.ts          Task 3  fetchErlCard 6 处 fixture + fetchErlGapAnalysis 整个 describe 重写
├── src/pages/exitReadiness/
│   ├── components/PriorityGapsPanel.tsx        Task 2 止血（删 3 行死渲染）→ Task 5 整体删除（需确认）
│   ├── components/index.less                   Task 5（需确认）删 .sev* 与 E2 段样式
│   ├── components/constants.ts                 Task 5（需确认）删 noGapAnalysisHint / noNotesProvided
│   ├── components/GapDetailsModal/GapDetailsModal.tsx   Task 4 注释订正（:20-23 / :290-295 / :313）；Task 5 :24-25
│   ├── components/__tests__/GapDetailsModal.test.tsx    Task 3
│   ├── dimension/DimensionPage.tsx             Task 5（需确认）:28 注释
│   └── README.md                               Task 5 / Task 6（需确认）
├── src/pages/companyOverview/home/components/ErlCard/
│   ├── ErlGapBlock.tsx                         Task 4 注释订正（:45-47 / :172-177 / :360-365 / :413-421）
│   └── __tests__/{useErlCard,ErlGapBlock,ErlCard}.test.tsx   Task 3
└── docs/{待优化项,已完成优化}.md              Task 5 / Task 6（需确认）
```

**不动**：`erlApi.ts` / `request.ts`（接口签名与 query 键都没变）、`erlGapState.ts(.test.ts)`、`useErlCard.ts`、`ErlCard.tsx`、`ErlCard.less`。

---

### Task 1：契约层 —— `response.ts` / `dto.ts` 删除死字段

**Files:**
- Modify: `web/CIOaas-web/src/services/api/exitReadiness/response.ts:100-125`（`ErlCardResponse`）、`:191-201`（`ErlGapItemResponse` / `ErlActionItemResponse`）、`:605-612`（`ErlGapAnalysisDimensionResponse` 尾段）、`:624-642`（`ErlGapAnalysisResponse`）
- Modify: `web/CIOaas-web/src/services/api/exitReadiness/dto.ts:143-150`（`ErlCardDTO`）、`:214-224`（`ErlGapItemDTO` / `ErlActionItemDTO`）、`:612-624`（`ErlGapAnalysisDimensionDTO` 尾段）、`:635-652`（`ErlGapAnalysisDTO`）

- [ ] **Step 1** `response.ts:100-108` —— `ErlCardResponse` 删 `gapSummary`（接口 1）

```ts
// Before
export interface ErlCardResponse {
  period: string | null;
  overallScore: number | null;
  stage: number | null;
  era: string | null;
  bpmmScore: number | null;
  gapSummary: string | null;
  /** v4.4-D3。 */
  shared?: boolean | null;
```

```ts
// After
export interface ErlCardResponse {
  period: string | null;
  overallScore: number | null;
  stage: number | null;
  era: string | null;
  bpmmScore: number | null;
  /** v4.4-D3。2026-09-24 任务化起全部来自 Java 任务表（设计稿 §7.3）；~~`gapSummary`~~ 同日随之删除。 */
  shared?: boolean | null;
```

- [ ] **Step 2** `response.ts:191-201` —— 条目 / 动作只剩标题与档位（接口 2 / 17 共用）

```ts
// Before
export interface ErlGapItemResponse {
  title: string;
  note: string | null;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | null;
  evidenceMissing: boolean | null;
}

export interface ErlActionItemResponse {
  title: string;
  why: string | null;
}
```

```ts
// After
/**
 * 接口 2 / 17 共用的 gap 条目。**2026-09-24 差距分析任务化**（设计稿 §7.2）起后端只下发
 * `title` / `severity`：~~`note`~~ / ~~`evidenceMissing`~~ 不再生成也不再下发（Python 条目表
 * `ai_erl_gap_analysis_task_item` 只存标题），前端契约同步删除。
 */
export interface ErlGapItemResponse {
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | null;
}

/** 同上：动作只剩 `title`，~~`why`~~ 已随任务化删除。 */
export interface ErlActionItemResponse {
  title: string;
}
```

- [ ] **Step 3** `response.ts:605-612` —— 维度项删 `analyzedAt`，`dimensionStale` 注释改口（字段保留）

```ts
// Before
  analyzed?: boolean | null;
  /** 该维上次分析时间（`analyzed = false` 时为 `null`）。 */
  analyzedAt?: string | null;
  /**
   * 该维**已分析过、但之后又有新提交，正在重跑**。与期次级的 `stale` 并列但不同层：
   * 那个说的是整份分析待重生成，这个只说这一维。
   */
  dimensionStale?: boolean | null;
```

```ts
// After
  analyzed?: boolean | null;
  /**
   * 该维已分析过、但之后又有新提交正在重跑。
   * ⚠️ **2026-09-24 差距分析任务化后恒为 `false`**（设计稿 §7.2：字段保留一版供前端兼容；
   * 有新提交时后端改为建新任务 ⇒ 屏上走 `analyzed = false` 的 `Analyzing…`，六态里的
   * `Updating…` 不再可达）。前端归一与六态分支**原样保留**，等后端下一版撤字段时一起删。
   * ~~`analyzedAt`~~ 同日删除（全仓本就无渲染方）。
   */
  dimensionStale?: boolean | null;
```

- [ ] **Step 4** `response.ts:624-642` —— `ErlGapAnalysisResponse` 期次级只剩 `shared` / `dimensions` / `analysisServiceUnavailable`

```ts
// Before
export interface ErlGapAnalysisResponse {
  summary: string | null;
  /** v4.4-D3。 */
  shared?: boolean | null;
  sharedAt?: string | null;
  sharedBy?: string | null;
  dimensions: ErlGapAnalysisDimensionResponse[] | null;
  generatedAt: string | null;
  model: string | null;
  stale: boolean;
  generating: boolean;
  /**
   * **分析服务整体不可用**（2026-09-20 跨端审核后新增，Java `loadResult` 走降级分支时置真，
   * 两端都下发）：Python 宕机 / 401 / 结果落库失败等，Java 一律降级成 `artifact = null` 的
   * **200**，若没有这个顶层标志，前端只会看到「每维 `analyzed = false`」⇒ 全屏 `Analyzing…`，
   * 等两分钟再叫用户刷新，而刷新解决不了 Python 宕机。
   */
  analysisServiceUnavailable?: boolean | null;
}
```

```ts
// After
/**
 * 接口 17 / 18 出参。**2026-09-24 差距分析任务化**（设计稿 §7.2）后期次级只剩三个字段：
 * ~~`summary` / `generatedAt` / `model` / `stale` / `generating` / `sharedAt` / `sharedBy`~~
 * 全部不再下发（编排状态归 Java 任务表、AI 内容按维度取，没有「整份分析」这一层了）。
 * 设计稿另给管理端下发期次级 `shareable`，前端 Share 门槛继续取接口 1 的同名字段，这里不镜像（YAGNI）。
 */
export interface ErlGapAnalysisResponse {
  /** v4.4-D3。管理端 = 最新记录已分享；公司端 = 存在已分享记录。 */
  shared?: boolean | null;
  dimensions: ErlGapAnalysisDimensionResponse[] | null;
  /**
   * **分析服务整体不可用**（2026-09-20 新增；任务化后 = Java 向 Python 批量取条目失败，
   * 没有条目可取时恒 false，两端都下发）。若没有这个顶层标志，前端只会看到
   * 「每维 `analyzed = false`」⇒ 全屏 `Analyzing…`，等两分钟再叫用户刷新，而刷新解决不了 Python 宕机。
   */
  analysisServiceUnavailable?: boolean | null;
}
```

- [ ] **Step 5** `dto.ts:143-152` —— `ErlCardDTO` 删 `gapSummary`

```ts
// Before
export interface ErlCardDTO {
  period: string | null;
  /** 综合分（`Overall Score`），一位小数。 */
  overallScore: number | null;
  stage: number | null;
  era: string | null;
  bpmmScore: number | null;
  gapSummary: string | null;
  /** 该期次的差距分析是否已分享给 Founder 端（v4.4-D3）。 */
  shared: boolean;
```

```ts
// After
export interface ErlCardDTO {
  period: string | null;
  /** 综合分（`Overall Score`），一位小数。 */
  overallScore: number | null;
  stage: number | null;
  era: string | null;
  bpmmScore: number | null;
  /** 该期次的差距分析是否已分享给 Founder 端（v4.4-D3）。~~`gapSummary`~~ 2026-09-24 随任务化删除。 */
  shared: boolean;
```

- [ ] **Step 6** `dto.ts:214-224` —— 条目 / 动作 DTO 同步

```ts
// Before
export interface ErlGapItemDTO {
  title: string;
  note: string | null;
  severity: ErlGapSeverity;
  evidenceMissing: boolean;
}

export interface ErlActionItemDTO {
  title: string;
  why: string | null;
}
```

```ts
// After
/**
 * gap 条目（接口 2 / 17 共用）。**2026-09-24 差距分析任务化**起只有标题与档位：
 * ~~`note`~~ / ~~`evidenceMissing`~~ 后端不再生成也不再下发（前端 2026-09-21 / 09-23 就已不渲染）。
 */
export interface ErlGapItemDTO {
  title: string;
  severity: ErlGapSeverity;
}

/** 建议动作只有标题；~~`why`~~ 同上删除。 */
export interface ErlActionItemDTO {
  title: string;
}
```

- [ ] **Step 7** `dto.ts:612-624` —— 维度项：`analyzed` 注释改成任务化口径，删 `analyzedAt`，`dimensionStale` 注释改口

```ts
// Before
  /**
   * 该维**被分析过**（2026-09-20 后端改维度级增量生成后新增）：某一维两端都提交就立刻分析
   * 这一维，不必等全部维度 ⇒ 同一份出参里各维进度不同。`false` = 还没轮到 / 正在跑。
   *
   * ⚠️ 两点：① 该维**分析失败**目前也是 `false`（接口 17 没有维度级失败标志）；
   * ② 归一时若 `hasGap` 整个缺席，本字段会**一并降级成 `false`** —— 没有差距结论就等于
   * 这一维还没有结论，详见 `erlService.mapGapAnalysis`。
   */
  analyzed: boolean;
  /** 该维上次分析时间；`analyzed = false` 时为 `null`。 */
  analyzedAt: string | null;
  /** 该维已分析过、但之后又有新提交，**正在重跑**（维度级；期次级的那条是 `stale`）。 */
  dimensionStale: boolean;
```

```ts
// After
  /**
   * 该维**被分析过**（= 该维任务 `SUCCESS`，2026-09-24 任务化口径）。`false` = 还没轮到 /
   * 正在跑 / 报告级门槛未就绪（设计稿 D9：全部 Active 维度两端交齐前一律 `Analyzing…`）。
   *
   * ⚠️ 两点：① 该维**分析失败**也是 `false`（FAILED 由后端自动重投，接口 17 不下发失败态，
   * 设计稿 §11）；② 归一时若 `hasGap` 整个缺席，本字段会**一并降级成 `false`** ——
   * 没有差距结论就等于这一维还没有结论，详见 `erlService.mapGapAnalysis`。
   */
  analyzed: boolean;
  /**
   * 该维已分析过、但之后又有新提交正在重跑。⚠️ **2026-09-24 起后端恒发 `false`**（设计稿 §7.2
   * 保留一版供兼容），六态里的 `updating` 因此不可达；归一与分支原样保留，待后端撤字段时一起删。
   */
  dimensionStale: boolean;
```

- [ ] **Step 8** `dto.ts:635-652` —— `ErlGapAnalysisDTO` 期次级只剩三个字段

```ts
// Before
export interface ErlGapAnalysisDTO {
  summary: string | null;
  /** v4.4-D3：是否已分享给 Founder 端。公司端 `false` 时服务端直接返回空态。 */
  shared: boolean;
  sharedAt: string | null;
  sharedBy: string | null;
  dimensions: ErlGapAnalysisDimensionDTO[];
  generatedAt: string | null;
  model: string | null;
  stale: boolean;
  generating: boolean;
  /**
   * 分析服务整体不可用（Python 宕机 / 401 / 落库失败，Java 把它们降级成 200 后用这个标志
   * 告诉前端）。为真时 Gap 区块走**失败态 + Retry**，且**不再自动轮询** ——
   * 那种故障不会因为多轮几次好转，维度级的 `analyzed=false` 在这种时候不代表「正在跑」。
   */
  analysisServiceUnavailable: boolean;
}
```

```ts
// After
/**
 * 接口 17 / 18 的期次级形态。**2026-09-24 差距分析任务化**起只剩三个字段：
 * ~~`summary` / `sharedAt` / `sharedBy` / `generatedAt` / `model` / `stale` / `generating`~~
 * 已随后端出参删除（其中 `summary` 自 2026-09-21、`sharedAt` / `sharedBy` 自 2026-09-20
 * 起在前端本就没有渲染方）。
 */
export interface ErlGapAnalysisDTO {
  /** v4.4-D3：是否已分享给 Founder 端。公司端 `false` 时服务端直接返回空态。 */
  shared: boolean;
  dimensions: ErlGapAnalysisDimensionDTO[];
  /**
   * 分析服务整体不可用（Java 向 Python 取条目失败，降级成 200 后用这个标志告诉前端）。
   * 为真时 Gap 区块走**失败态 + Retry**，且**不再自动轮询** ——
   * 那种故障不会因为多轮几次好转，维度级的 `analyzed=false` 在这种时候不代表「正在跑」。
   */
  analysisServiceUnavailable: boolean;
}
```

- [ ] **Step 9** 轻量校验：`npm run lint:fix`；再跑 §2 的过滤版 `tsc`。**本 Task 末尾允许的残留** = 且仅 = 下列 7 个文件对已删字段的引用（Task 2 / 3 消掉）：`erlService.ts`、`PriorityGapsPanel.tsx`、`erlService.test.ts`、`useErlCard.test.tsx`、`ErlGapBlock.test.tsx`、`GapDetailsModal.test.tsx`、`ErlCard.test.tsx`。出现其它文件即说明漏核了消费方，停下回到 §0 表核对。

---

### Task 2：归一层 —— `erlService.ts` 同步 + `PriorityGapsPanel.tsx` 三行止血

**Files:**
- Modify: `web/CIOaas-web/src/services/service/exitReadiness/erlService.ts:312-321`（`mapGapItem`）、`:471-478`（`fetchErlCard` 的 `gapSummary`）、`:547`（`fetchErlDimensionDetail` 的 `actions`）、`:1047-1090`（`mapGapAnalysis` 整段）
- Modify: `web/CIOaas-web/src/pages/exitReadiness/components/PriorityGapsPanel.tsx:8-11`（文件头）、`:71-86`（gap 条目）、`:92-97`（动作条目）

> 为什么止血放在这里而不是等 Task 5：Task 1 删掉 `note` / `evidenceMissing` / `why` 后，`PriorityGapsPanel.tsx:81/82/95` 立即 `TS2339`；Task 5（整体删除）要等用户确认，不能让 `tsc` 卡在中间态。止血只删三行死渲染，不改组件签名。

- [ ] **Step 1** `erlService.ts:312-321` —— `mapGapItem` 只剩标题与档位

```ts
// Before
function mapGapItem(g: ErlGapItemResponse): ErlGapItemDTO {
  return {
    title: g.title,
    note: g.note ?? null,
    // 非法 severity 由 Java 侧降级为 MEDIUM；前端再兜一次 —— 档位要进 Gap 弹窗的条目文案
    // （`… — medium severity`）与 E2 面板的色标徽章，取不到值两处都会缺一块。
    severity: g.severity === 'HIGH' || g.severity === 'LOW' ? g.severity : 'MEDIUM',
    evidenceMissing: g.evidenceMissing === true,
  };
}
```

```ts
// After
/** 接口 2 / 17 共用。2026-09-24 任务化后条目只剩标题与档位（`note` / `evidenceMissing` 已从契约删除）。 */
function mapGapItem(g: ErlGapItemResponse): ErlGapItemDTO {
  return {
    title: g.title,
    // 非法 severity 由 Java 侧降级为 MEDIUM；前端再兜一次 —— 档位要进 Gap 弹窗的条目文案
    // （`… — medium severity`），取不到值那一句就缺一块。
    severity: g.severity === 'HIGH' || g.severity === 'LOW' ? g.severity : 'MEDIUM',
  };
}
```

- [ ] **Step 2** `erlService.ts:476-478` —— `fetchErlCard` 删 `gapSummary` 一行

```ts
// Before
    bpmmScore: data.bpmmScore ?? null,
    gapSummary: data.gapSummary ?? null,
    shared: data.shared === true,
```

```ts
// After
    bpmmScore: data.bpmmScore ?? null,
    shared: data.shared === true,
```

- [ ] **Step 3** `erlService.ts:547` —— 接口 2 的 `actions` 不再带 `why`

```ts
// Before
    actions: (data.actions || []).map((a) => ({ title: a.title, why: a.why ?? null })),
```

```ts
// After
    actions: (data.actions || []).map((a) => ({ title: a.title })),
```

- [ ] **Step 4** `erlService.ts:1047-1090` —— `mapGapAnalysis` 整段替换（Before = 现文件 `:1047-1090` 从 `/**` 注释头到函数收尾 `}` 整段）

```ts
// After
/**
 * 接口 17 / 18 共用（两个端点的出参都是 `ErlGapAnalysisResponse`）。
 * ⚠️ 该出参的维度项**只有 code 与 abbr**，没有 `dimensionName` —— DTO 侧同样没有 `name`。
 *
 * **2026-09-24 差距分析任务化**（设计稿 §7.2）：期次级只剩 `shared` / `analysisServiceUnavailable`，
 * 维度级删掉 `analyzedAt`，条目删掉 `note` / `evidenceMissing` / `why`；`dimensionStale` 后端恒发
 * `false`、这里原样归一（六态 `updating` 分支保留不动，待后端撤字段时一起删）。
 */
function mapGapAnalysis(data: ErlGapAnalysisResponse): ErlGapAnalysisDTO {
  return {
    shared: data.shared === true,
    dimensions: (data.dimensions || []).map((d) => ({
      code: d.dimensionCode,
      abbr: d.dimensionAbbr || d.dimensionCode,
      bothSubmitted: d.bothSubmitted === true,
      hasGap: d.hasGap === true,
      questionSetMismatch: d.questionSetMismatch === true,
      mismatchSide: mapPortal(d.mismatchSide),
      /*
        沿用本文件一贯的 `=== true` 归一，但 **fail 成 `false` 是不是安全，要逐字段看**
        （别把下面这段读成「缺失归 false 总是对的」）：
        · `analyzed` 缺失 → `false` → 蓝点 `Analyzing…`：**安全**。「还没分析」是可自愈的中性
          说法（有界轮询会把它推到终态），反过来当成 `true` 就是 2026-09-20 修掉的假阴性。
        · `dimensionStale` 缺失 → `false` → 不显示 `Updating…`：**安全**（任务化后后端本就恒发 false）。
        · `hasGap` 缺失 → `false` → 配上 `analyzed = true` 就是绿点 `No Gap`：**不安全**，
          与假阴性同一类。故这里**连 `analyzed` 一起降级**：没有差距结论 = 这一维还没有结论，
          让它落回 `analyzing`，而不是替后端断言「没有差距」。
      */
      analyzed: d.analyzed === true && typeof d.hasGap === 'boolean',
      dimensionStale: d.dimensionStale === true,
      narrative: d.narrative ?? null,
      gaps: (d.gaps || []).map(mapGapItem),
      actions: (d.actions || []).map((a) => ({ title: a.title })),
    })),
    // 缺席归 `false`（= 服务可用）：老后端没有这个字段，此时行为与加它之前完全一致。
    analysisServiceUnavailable: data.analysisServiceUnavailable === true,
  };
}
```

- [ ] **Step 5** `PriorityGapsPanel.tsx:8-11` —— 文件头改口（组件仍存在，只是不再渲染已删字段）

```ts
// Before
 * gap 的 severity 用色标徽章（HIGH 红 / MEDIUM 黄 / LOW 灰）；`evidenceMissing` 的条目
 * 追加灰色标注 `No supporting evidence provided`（design-doc §8.4「E2 区块」、PRD §5；
 * 2026-09-18 起该标志位表示「既无备注又无可用附件摘要」，见 §5.2）。
 * 双方已提交但无 gap 时显示 `No Gap`（design-doc §9）。
```

```ts
// After
 * gap 的 severity 用色标徽章（HIGH 红 / MEDIUM 黄 / LOW 灰）。
 * ~~`evidenceMissing` 的条目追加灰色标注、`note` / `why` 灰字说明~~ 三者已于 2026-09-24
 * 随差距分析任务化从契约删除（后端不再生成），本组件只剩标题 + 档位；它本身自 2026-09-15
 * 起全仓无消费方，整体去留见 `docs/待优化项.md`。
 * 双方已提交但无 gap 时显示 `No Gap`（design-doc §9）。
```

- [ ] **Step 6** `PriorityGapsPanel.tsx:71-86` —— gap 条目删 `note` / `evidenceMissing` 两段渲染

```tsx
// Before
            gaps.map((gap) => (
              <div key={gap.title} className={styles.gapItem}>
                <span className={styles.gapTitle}>{gap.title}</span>
                <span
                  className={`${styles.badge} ${styles.gapSeverity} ${
                    SEVERITY_CLASS[gap.severity]
                  }`}
                >
                  {gap.severity}
                </span>
                {gap.note && <div className={styles.gapNote}>{gap.note}</div>}
                {gap.evidenceMissing && (
                  <div className={styles.gapMissing}>{TEXT.noNotesProvided}</div>
                )}
              </div>
            ))
```

```tsx
// After
            gaps.map((gap) => (
              <div key={gap.title} className={styles.gapItem}>
                <span className={styles.gapTitle}>{gap.title}</span>
                <span
                  className={`${styles.badge} ${styles.gapSeverity} ${
                    SEVERITY_CLASS[gap.severity]
                  }`}
                >
                  {gap.severity}
                </span>
              </div>
            ))
```

- [ ] **Step 7** `PriorityGapsPanel.tsx:92-97` —— 动作条目删 `why`

```tsx
// Before
              {actions.map((action) => (
                <div key={action.title} className={styles.gapItem}>
                  <div className={styles.gapTitle}>{action.title}</div>
                  {action.why && <div className={styles.gapNote}>{action.why}</div>}
                </div>
              ))}
```

```tsx
// After
              {actions.map((action) => (
                <div key={action.title} className={styles.gapItem}>
                  <div className={styles.gapTitle}>{action.title}</div>
                </div>
              ))}
```

> 止血后 `TEXT.noNotesProvided`（`constants.ts:184`）与 `index.less` 的 `.gapNote` / `.gapMissing` 变成零引用；`TEXT` 仍被本组件的 `noGapAnalysis` / `noGapAnalysisHint` / `gapNoneForDimension` 用着，import 不动。三个孤儿随 Task 5 一起删；Task 5 若被否决，则在 Task 6 的台账里登记。

- [ ] **Step 8** 轻量校验：`npm run lint:fix`；过滤版 `tsc` 的残留此时**只能**是 5 个测试文件（`erlService.test.ts` / `useErlCard.test.tsx` / `ErlGapBlock.test.tsx` / `GapDetailsModal.test.tsx` / `ErlCard.test.tsx`），源码文件必须为 0。

---

### Task 3：单测同步（5 个测试文件）

**Files:**
- Modify: `web/CIOaas-web/src/services/service/exitReadiness/erlService.test.ts:68,123,150,197,215,235`（`fetchErlCard` fixture）、`:509-704`（`fetchErlGapAnalysis` 整个 describe）
- Modify: `web/CIOaas-web/src/pages/companyOverview/home/components/ErlCard/__tests__/useErlCard.test.tsx:71-134`（工厂函数）、`:271-277`、`:394-420`、`:472-506`
- Modify: `web/CIOaas-web/src/pages/companyOverview/home/components/ErlCard/__tests__/ErlGapBlock.test.tsx:40-76`（工厂函数）、`:212-225`、`:249`、`:270-276`、`:288`、`:312-319`、`:323-333`、`:340-349`、`:359`、`:368`、`:418`、`:599-612`
- Modify: `web/CIOaas-web/src/pages/exitReadiness/components/__tests__/GapDetailsModal.test.tsx:25-55`（工厂 + `FRL` fixture）、`:90-104`、`:259`
- Modify: `web/CIOaas-web/src/pages/companyOverview/home/components/ErlCard/__tests__/ErlCard.test.tsx:108-124`（`cardWith`）
- 不动：`erlGapState.test.ts`（`flags()` 只含五个态标志，没有任何被删字段）

> `erlService.test.ts` 的 mock 走 `require` 出来的 `api`（无类型），多余键不会被 `tsc` 抓到，所以要**按契约手删**；其余四个文件的工厂函数都标了 `ErlGapAnalysisDTO` / `ErlGapAnalysisDimensionDTO` / `ErlCardDTO` 类型，漏一处 `tsc` 就红（对象字面量多余属性检查），Step 3-5 列的行号只是导航，以 `tsc` 为准。

- [ ] **Step 1** `erlService.test.ts` `fetchErlCard` 组：删 6 处 `gapSummary`（`:68` 的 `gapSummary: 'x',` 与 `:123 / :150 / :197 / :215 / :235` 的 `gapSummary: null,`），并在第一个用例 `:111` `expect(dto.shared).toBe(true);` 之后加一行钉住：

```ts
// After（:111-113）
    expect(dto.shared).toBe(true);
    // 2026-09-24 任务化：接口 1 不再下发 `gapSummary`，DTO 也不再有这个键（台账 :88 了结）
    expect(dto).not.toHaveProperty('gapSummary');
    expect(dto.benchmarkUrl).toBe('/exitReadiness/benchmark?companyId=1');
```

- [ ] **Step 2** `erlService.test.ts:509-704` —— `describe('fetchErlGapAnalysis（D3 / D4）', …)` **整段替换**为下面这份（fixture 全部按任务化契约裁掉 7 个期次级键、`analyzedAt`、`note` / `evidenceMissing` / `why`；原第 2 个用例改名去掉 `analyzedAt`；新增一条**键集合**钉子）：

```ts
describe('fetchErlGapAnalysis（D3 / D4 / 2026-09-24 任务化契约）', () => {
  it('shared / bothSubmitted / hasGap 独立归一，severity 非法值降级 MEDIUM', async () => {
    api.getErlGapAnalysis.mockResolvedValue(
      ok({
        shared: false,
        // 该出参的维度项只有 code 与 abbr（Java `ErlGapAnalysisDimensionResponse` 无 name）
        dimensions: [
          {
            dimensionCode: 'FRL',
            dimensionAbbr: 'FRL',
            bothSubmitted: true,
            hasGap: true,
            narrative: 'FRL currently scores 6/9.',
            gaps: [{ title: 'g', severity: 'CRITICAL' }],
            actions: [{ title: 'a' }],
          },
          // 后端补 `narrative` 之前该字段整个缺席，归一成 null（弹窗靠 null 退回固定文案）
          { dimensionCode: 'TRL', bothSubmitted: true, hasGap: false, gaps: null, actions: null },
        ],
      }),
    );

    const dto = await fetchErlGapAnalysis({ companyId: '1' });

    expect(dto.shared).toBe(false);
    // 维度码与缩写不为 undefined —— 读回 `d.code` / `d.abbr` 本组必红
    expect(dto.dimensions[0].code).toBe('FRL');
    expect(dto.dimensions[0].abbr).toBe('FRL');
    expect(dto.dimensions[0].gaps[0].severity).toBe('MEDIUM');
    expect(dto.dimensions[0].actions).toEqual([{ title: 'a' }]);
    // 绿点 + No Gap：bothSubmitted 与 hasGap 互不影响
    expect(dto.dimensions[1].code).toBe('TRL');
    expect(dto.dimensions[1].bothSubmitted).toBe(true);
    expect(dto.dimensions[1].hasGap).toBe(false);
    expect(dto.dimensions[1].gaps).toEqual([]);
    // narrative：下发了就透传，缺席归一成 null（写成 `?? ''` 会让弹窗少一句固定文案）
    expect(dto.dimensions[0].narrative).toBe('FRL currently scores 6/9.');
    expect(dto.dimensions[1].narrative).toBeNull();
  });

  /*
    2026-09-24 任务化：期次级 / 维度级 / 条目级的死字段都从契约删掉了。这里把三层的 **key 集合**
    钉死 —— 谁把 `summary` / `analyzedAt` / `note` 之类"顺手"加回 DTO，本条即红。
    ⚠️ `dimensionStale` **仍在**（后端恒发 false、保留一版供兼容，六态 `updating` 分支不动）。
  */
  it('任务化后的 DTO 键集合：期次级三键、维度级十一键、条目只剩 title / severity、动作只剩 title', async () => {
    api.getErlGapAnalysis.mockResolvedValue(
      ok({
        shared: true,
        dimensions: [
          {
            dimensionCode: 'FRL',
            dimensionAbbr: 'FRL',
            bothSubmitted: true,
            hasGap: true,
            analyzed: true,
            dimensionStale: false,
            narrative: 'n',
            gaps: [{ title: 'g', severity: 'HIGH' }],
            actions: [{ title: 'a' }],
          },
        ],
        analysisServiceUnavailable: false,
      }),
    );

    const dto = await fetchErlGapAnalysis({ companyId: '1' });

    expect(Object.keys(dto).sort()).toEqual(['analysisServiceUnavailable', 'dimensions', 'shared']);
    expect(Object.keys(dto.dimensions[0]).sort()).toEqual([
      'abbr',
      'actions',
      'analyzed',
      'bothSubmitted',
      'code',
      'dimensionStale',
      'gaps',
      'hasGap',
      'mismatchSide',
      'narrative',
      'questionSetMismatch',
    ]);
    expect(dto.dimensions[0].gaps[0]).toEqual({ title: 'g', severity: 'HIGH' });
    expect(dto.dimensions[0].actions[0]).toEqual({ title: 'a' });
  });

  // 2026-09-20 维度级增量生成引入的两个字段（`analyzedAt` 已于 2026-09-24 随任务化删除）。
  // ⚠️ 本用例的重点是**缺席时的方向**：`analyzed` 归一成 `false` ⇒ 屏上是 `Analyzing…`
  // （中性、可自愈）；若哪天有人把它改成 `!== false` 之类的宽松写法，缺席就会变成
  // 「分析完了、没差距」这个假阴性 —— 那正是当时修掉的 bug。
  it('analyzed / dimensionStale 各自独立归一，缺席落安全的一侧', async () => {
    api.getErlGapAnalysis.mockResolvedValue(
      ok({
        shared: false,
        dimensions: [
          {
            dimensionCode: 'FRL',
            bothSubmitted: true,
            hasGap: true,
            analyzed: true,
            dimensionStale: true,
            gaps: null,
            actions: null,
          },
          // 老后端 / 部分下发：两个字段整个缺席
          { dimensionCode: 'TRL', bothSubmitted: true, hasGap: false, gaps: null, actions: null },
        ],
      }),
    );

    const dto = await fetchErlGapAnalysis({ companyId: '1' });

    expect(dto.dimensions[0].analyzed).toBe(true);
    expect(dto.dimensions[0].dimensionStale).toBe(true);
    expect(dto.dimensions[1].analyzed).toBe(false);
    expect(dto.dimensions[1].dimensionStale).toBe(false);
  });

  // ⚠️ `hasGap` 缺席是**不安全**的那一侧：配上 `analyzed = true` 就是绿点 `No Gap`，
  // 与假阴性同类。故归一时连 `analyzed` 一起降级，让它落回 `Analyzing…`。
  it('hasGap 整个缺席时 analyzed 一并降级为 false（不替后端断言「没有差距」）', async () => {
    api.getErlGapAnalysis.mockResolvedValue(
      ok({
        shared: false,
        dimensions: [
          { dimensionCode: 'FRL', bothSubmitted: true, analyzed: true, gaps: null, actions: null },
        ],
      }),
    );

    const dto = await fetchErlGapAnalysis({ companyId: '1' });

    expect(dto.dimensions[0].hasGap).toBe(false);
    expect(dto.dimensions[0].analyzed).toBe(false);
  });

  // 顶层服务不可用标志（2026-09-20）：缺席归 false，行为与加它之前一致。
  it('analysisServiceUnavailable：下发则透传，缺席归一为 false', async () => {
    api.getErlGapAnalysis.mockResolvedValue(
      ok({ shared: false, dimensions: null, analysisServiceUnavailable: true }),
    );
    expect((await fetchErlGapAnalysis({ companyId: '1' })).analysisServiceUnavailable).toBe(true);

    api.getErlGapAnalysis.mockResolvedValue(ok({ shared: false, dimensions: null }));
    expect((await fetchErlGapAnalysis({ companyId: '1' })).analysisServiceUnavailable).toBe(false);
  });

  it('P4：questionSetMismatch / mismatchSide 独立归一，白名单外的方向一律 null', async () => {
    api.getErlGapAnalysis.mockResolvedValue(
      ok({
        shared: true,
        dimensions: [
          {
            dimensionCode: 'FRL',
            dimensionAbbr: 'FRL',
            bothSubmitted: true,
            hasGap: false,
            questionSetMismatch: true,
            mismatchSide: 'FOUNDER',
            gaps: null,
            actions: null,
          },
          // 方向取值不在白名单内（脏数据 / 契约漂移）：宁可少一句方向，也不能把「另一方」指错人
          {
            dimensionCode: 'PRL',
            bothSubmitted: true,
            hasGap: false,
            questionSetMismatch: true,
            mismatchSide: 'BOTH',
            gaps: null,
            actions: null,
          },
          // 第三维完全没带这两个字段：mismatch 归一 false，不得 fail-open 成黄点
          { dimensionCode: 'TRL', bothSubmitted: true, hasGap: true, gaps: null, actions: null },
        ],
      }),
    );

    const dto = await fetchErlGapAnalysis({ companyId: '1' });

    expect(dto.dimensions[0].questionSetMismatch).toBe(true);
    expect(dto.dimensions[0].mismatchSide).toBe('FOUNDER');
    expect(dto.dimensions[1].questionSetMismatch).toBe(true);
    expect(dto.dimensions[1].mismatchSide).toBeNull();
    expect(dto.dimensions[2].questionSetMismatch).toBe(false);
    expect(dto.dimensions[2].mismatchSide).toBeNull();
  });
});
```

- [ ] **Step 3** `useErlCard.test.tsx` —— 工厂函数与 4 处用 `summary` 当标记的断言

3a `:71-88` `makeCard`：删 `gapSummary: null,`（`:78`）。

3b `:90-110` `makeDimension`：删 `analyzedAt: '2026-09-20 10:00:00',`（`:103`；上一行注释「缺省是**终态**…」保留）。

3c `:112-129` `makeGap` 整段：

```ts
// Before
function makeGap(
  dimensions: ErlGapAnalysisDimensionDTO[],
  overrides: Partial<ErlGapAnalysisDTO> = {},
): ErlGapAnalysisDTO {
  return {
    summary: null,
    shared: false,
    sharedAt: null,
    sharedBy: null,
    dimensions,
    generatedAt: null,
    model: null,
    stale: false,
    generating: false,
    analysisServiceUnavailable: false,
    ...overrides,
  };
}
```

```ts
// After
function makeGap(
  dimensions: ErlGapAnalysisDimensionDTO[],
  overrides: Partial<ErlGapAnalysisDTO> = {},
): ErlGapAnalysisDTO {
  return {
    shared: false,
    dimensions,
    analysisServiceUnavailable: false,
    ...overrides,
  };
}
```

3d `:132` `analyzingDim`：`makeDimension('FRL', { analyzed: false, analyzedAt: null })` → `makeDimension('FRL', { analyzed: false })`。

3e `:271-277`（「全部维度都是终态 → 一次都不轮询」用例）：

```ts
// Before
          makeDimension('TRL', { bothSubmitted: false, analyzed: false, analyzedAt: null }),
          makeDimension('BERL', {
            questionSetMismatch: true,
            mismatchSide: 'FOUNDER',
            analyzed: false,
            analyzedAt: null,
          }),
```

```ts
// After
          makeDimension('TRL', { bothSubmitted: false, analyzed: false }),
          makeDimension('BERL', {
            questionSetMismatch: true,
            mismatchSide: 'FOUNDER',
            analyzed: false,
          }),
```

3f `:394-420`（「静默轮询某一轮失败」用例）：原来拿期次级 `summary` 当 OLD / NEW 标记，改用维度级 `narrative`（同为透传字符串，语义等价）：

```ts
// Before
    mockGap.mockImplementationOnce(() =>
      Promise.resolve(makeGap([analyzingDim], { summary: 'OLD' })),
    );
    mockGap.mockImplementationOnce(() => Promise.reject(new Error('boom')));
    mockGap.mockImplementation(() =>
      Promise.resolve(makeGap([makeDimension('FRL', { hasGap: true })], { summary: 'NEW' })),
    );

    mount('c1');
    await flush();
    expect(latest.gap?.summary).toBe('OLD');

    await advanceOnePoll(0);

    // 失败那一轮：屏上一切照旧
    expect(latest.gap?.summary).toBe('OLD');
```

```ts
// After
    // 标记用维度级 `narrative`（期次级 `summary` 已于 2026-09-24 随任务化从 DTO 删除）
    mockGap.mockImplementationOnce(() =>
      Promise.resolve(makeGap([{ ...analyzingDim, narrative: 'OLD' }])),
    );
    mockGap.mockImplementationOnce(() => Promise.reject(new Error('boom')));
    mockGap.mockImplementation(() =>
      Promise.resolve(makeGap([makeDimension('FRL', { hasGap: true, narrative: 'NEW' })])),
    );

    mount('c1');
    await flush();
    expect(latest.gap?.dimensions[0].narrative).toBe('OLD');

    await advanceOnePoll(0);

    // 失败那一轮：屏上一切照旧
    expect(latest.gap?.dimensions[0].narrative).toBe('OLD');
```

同用例 `:418`：`expect(latest.gap?.summary).toBe('NEW');` → `expect(latest.gap?.dimensions[0].narrative).toBe('NEW');`

3g `:474-475` 与 `:495 / :503`（「第一轮的接口 17 迟到」用例）：

```ts
// Before
    const stale = makeGap([makeDimension('FRL')], { summary: 'STALE' });
    const fresh = makeGap([makeDimension('FRL')], { summary: 'FRESH' });
```

```ts
// After
    const stale = makeGap([makeDimension('FRL', { narrative: 'STALE' })]);
    const fresh = makeGap([makeDimension('FRL', { narrative: 'FRESH' })]);
```

`:495` 与 `:503` 两处 `expect(latest.gap?.summary).toBe('FRESH');` → `expect(latest.gap?.dimensions[0].narrative).toBe('FRESH');`

- [ ] **Step 4** `ErlGapBlock.test.tsx`

4a `:40-59` `gapDimension`：删 `analyzedAt: '2026-09-06 10:00:00',`（`:53`）。

4b `:61-76` `gapAnalysis` 整段：

```ts
// Before
const gapAnalysis = (
  dimensions: ErlGapAnalysisDTO['dimensions'],
  overrides: Partial<ErlGapAnalysisDTO> = {},
): ErlGapAnalysisDTO => ({
  summary: 'Founder and GSV diverge on revenue quality.',
  shared: false,
  sharedAt: null,
  sharedBy: null,
  dimensions,
  generatedAt: '2026-09-06 10:00:00',
  model: 'claude',
  stale: false,
  generating: false,
  analysisServiceUnavailable: false,
  ...overrides,
});
```

```ts
// After
const gapAnalysis = (
  dimensions: ErlGapAnalysisDTO['dimensions'],
  overrides: Partial<ErlGapAnalysisDTO> = {},
): ErlGapAnalysisDTO => ({
  shared: false,
  dimensions,
  analysisServiceUnavailable: false,
  ...overrides,
});
```

4c 三处 `{ summary: null }` 覆盖删掉（DTO 已无此键，留着是 `tsc` 多余属性错误）：

```ts
// :212-225 Before → After（只删 overrides 参数）
    const { getByText, queryByText } = renderBlock(
      gapAnalysis([
        gapDimension('FRL', true, false),
        gapDimension('PRL', true, false),
        gapDimension('BERL', true, false),
      ]),
    );
```

```ts
// :323-333 Before
    const { getByText, queryByText } = renderBlock(
      gapAnalysis([gapDimension('FRL', false, false)], {
        // 期次级 summary 还留着上一轮的内容也不算数：本期没有任何终态维度
        summary: null,
      }),
    );
```

```ts
// :323-333 After
    const { getByText, queryByText } = renderBlock(
      gapAnalysis([gapDimension('FRL', false, false)]),
    );
```

```ts
// :340-349 After（同样只删第二个参数）
    const { getByText, queryByText } = renderBlock(
      gapAnalysis([
        gapDimension('FRL', true, false, { analyzed: false }),
        gapDimension('PRL', true, false, { analyzed: false }),
      ]),
    );
```

4d **删除** `:312-319` 整个用例「期次级 summary 不再上屏（字段仍下发）」（连同上方两行注释）—— 字段已从 DTO 删除，该守卫由类型系统接管，用例失去被测对象。

4e `analyzedAt: null` 逐处删掉（`:249 / :270 / :273 / :288 / :344 / :345 / :359 / :368 / :418`），形态一律是 `{ analyzed: false, analyzedAt: null }` → `{ analyzed: false }`；`:270-276` 那处多行对象只删 `analyzedAt: null,` 一行。

4f `:599-612` 用例改口（期次级 `stale` 没了，钉的仍是「横幅位为空 + 旧结论不清空」）：

```ts
// Before
  it('stale / generating 且未分享 → 两条期次级横幅都不出，旧内容不清空', () => {
    const { container, getByText } = renderBlock(
      gapAnalysis([gapDimension('FRL', true, true)], { stale: true }),
    );
    // 需求方 2026-09-20 撤下 `Refreshing analysis…`、2026-09-21 撤下重新分享提示。
    // ⚠️ 断的是**横幅位本身为空**而不是那两句字面量（2026-09-21 审核）：两个串在 src/ 里
    // 已一个字符都不存在，只断文字的话换个措辞加回横幅照样绿。`pollExhausted` 为 false
    // 时 `.gapNotice` 应当一个都没有。
    expect(container.querySelectorAll('.gapNotice')).toHaveLength(0);
    // §9「保留旧内容」：期次 stale 不清空已有结论（summary 2026-09-21 撤下后，
    // 卡面上的落点是维度小卡与计数句）。
    expect(getByText('Gap analysis ready')).toBeTruthy();
    expect(getByText('1 of 1 dimensions have gap analysis for Q2 2026')).toBeTruthy();
  });
```

```ts
// After
  it('未轮询耗尽时横幅位为空，已有结论照常展示', () => {
    const { container, getByText } = renderBlock(gapAnalysis([gapDimension('FRL', true, true)]));
    // 需求方 2026-09-20 撤下 `Refreshing analysis…`、2026-09-21 撤下重新分享提示；
    // 两条横幅当年依据的期次级 `stale` / `generating` 已于 2026-09-24 随任务化从契约删除。
    // ⚠️ 断的是**横幅位本身为空**而不是那两句字面量（2026-09-21 审核）：两个串在 src/ 里
    // 已一个字符都不存在，只断文字的话换个措辞加回横幅照样绿。`pollExhausted` 为 false
    // 时 `.gapNotice` 应当一个都没有。
    expect(container.querySelectorAll('.gapNotice')).toHaveLength(0);
    // §9「保留旧内容」：卡面上的落点是维度小卡与计数句。
    expect(getByText('Gap analysis ready')).toBeTruthy();
    expect(getByText('1 of 1 dimensions have gap analysis for Q2 2026')).toBeTruthy();
  });
```

- [ ] **Step 5** `GapDetailsModal.test.tsx`

5a `:25-42` `dimension()`：删 `analyzedAt: '2026-09-06 10:00:00',`（`:36`）。

5b `:44-55` `FRL` fixture：

```ts
// Before
const FRL = dimension('FRL', {
  hasGap: true,
  gaps: [
    {
      title: 'No audit-ready quality of earnings package',
      note: 'Buyers will discount without one.',
      severity: 'HIGH',
      evidenceMissing: true,
    },
  ],
  actions: [{ title: 'Assign an owner and 90-day plan.', why: 'Closes the biggest gap first.' }],
});
```

```ts
// After
const FRL = dimension('FRL', {
  hasGap: true,
  gaps: [{ title: 'No audit-ready quality of earnings package', severity: 'HIGH' }],
  actions: [{ title: 'Assign an owner and 90-day plan.' }],
});
```

5c `:90-104` 用例：删掉三条已经断不到任何东西的 `queryByText`（fixture 里不再有这些串），只留档位那一条：

```ts
// Before（:97-103）
  // gap 的备注、建议动作的理由已于 2026-09-23 撤下（字段仍下发，只是不再渲染）
  expect(queryByText('Buyers will discount without one.')).toBeNull();
  expect(queryByText('Closes the biggest gap first.')).toBeNull();
  // 缺证据标注已于 2026-09-21 撤下（`evidenceMissing` 仍为 true，只是不再渲染）
  expect(queryByText('No supporting evidence provided')).toBeNull();
  // 档位只以文字出现，不再单独渲染一个 HIGH 徽章
  expect(queryByText('HIGH')).toBeNull();
```

```ts
// After
  // gap 的备注 / 动作理由 / 缺证据标注：2026-09-21 与 09-23 先后撤下渲染，2026-09-24 随任务化
  // 从契约删除（`note` / `why` / `evidenceMissing` 已不在 DTO 里，无从渲染）
  // 档位只以文字出现，不再单独渲染一个 HIGH 徽章
  expect(queryByText('HIGH')).toBeNull();
```

5d `:259`：`dimension('TRL', { analyzed: false, analyzedAt: null })` → `dimension('TRL', { analyzed: false })`。

- [ ] **Step 6** `ErlCard.test.tsx:108-124` `cardWith`：删 `gapSummary: null,`（`:115`）。

- [ ] **Step 7** 轻量校验：`npm run lint:fix`；过滤版 `tsc` 必须 **0 行**（源码 + 测试全部收口）。另 `Grep` 复核全仓 `src/` 对 `gapSummary|analyzedAt|evidenceMissing|sharedAt|sharedBy|generatedAt` 的命中只剩：`ErlGapBlock.tsx` / `useErlCard.tsx` / `GapDetailsModal.tsx` 的注释、`constants.ts:179-180` 的注释、`ErlGapShareResponse` / `ErlGapShareResultDTO`（接口 27，保留）。

---

### Task 4：过时注释订正（只改注释，零行为变化）

**Files:**
- Modify: `web/CIOaas-web/src/pages/companyOverview/home/components/ErlCard/ErlGapBlock.tsx:45-47`、`:172-177`、`:360-365`、`:413-421`
- Modify: `web/CIOaas-web/src/pages/exitReadiness/components/GapDetailsModal/GapDetailsModal.tsx:20-23`、`:290-295`、`:313`

> 这几处注释明确写着「接口仍下发 / 字段本身不裁 / DTO 照旧保留」，Task 1 之后就是错话；`useErlCard.ts:89-91` 那段说的是 hook **出参**删了 `sharedAt` / `sharedBy`，仍然成立，不动。

- [ ] **Step 1** `ErlGapBlock.tsx:45-47`（文件头）

```ts
// Before
 * 期次级 `stale` / `generating` 时**继续展示旧内容不清空**（§9）；~~顶部挂 `Refreshing analysis…`~~
 * 已于 2026-09-20 撤下（需求方），进行时改由维度小卡逐维表达；
 * ~~`Content updated — reshare to founder.`~~ 2026-09-21 同样撤下，横幅位只剩轮询耗尽那条。
```

```ts
// After
 * ~~期次级 `stale` / `generating`~~ 已于 2026-09-24 随差距分析任务化从接口 17 出参删除，进行时
 * 只由维度小卡逐维表达；~~顶部挂 `Refreshing analysis…`~~ 2026-09-20 撤下、
 * ~~`Content updated — reshare to founder.`~~ 2026-09-21 撤下，横幅位只剩轮询耗尽那条。
```

- [ ] **Step 2** `ErlGapBlock.tsx:172-177`（`ErlGapBlockProps` 上方的 BREAKING CHANGE 注）

```ts
// Before
 * `sharedAt` / `sharedBy` 两个 prop。影响面仅同目录 `ErlCard.tsx`（本类型虽 `export`，但按
 * architecture.md §4.1 页面私有组件不得跨域引用，全仓无第二个消费方）。接口仍下发这两个字段，
 * `ErlGapAnalysisDTO` 里照旧保留 —— 契约层不因某个消费方不再渲染就裁字段。
 */
```

```ts
// After
 * `sharedAt` / `sharedBy` 两个 prop。影响面仅同目录 `ErlCard.tsx`（本类型虽 `export`，但按
 * architecture.md §4.1 页面私有组件不得跨域引用，全仓无第二个消费方）。
 * 2026-09-24 起接口 17 也不再下发这两个字段（差距分析任务化），`ErlGapAnalysisDTO` 已随之删除。
 */
```

- [ ] **Step 3** `ErlGapBlock.tsx:360-365`（JSX 内注释）

```tsx
// Before
          {/*
            ⚠️ 需求方 2026-09-21 撤下按钮下方那条 `Content updated — reshare to founder.`
            （`gap.stale || gap.generating` 且未分享时出）。连同 2026-09-20 撤下的
            `Refreshing analysis…`，**期次级的横幅位现在只剩轮询耗尽那一条**；
            期次级 `stale` / `generating` 仍按 §9 继续展示旧内容，只是不再上屏播报。
          */}
```

```tsx
// After
          {/*
            ⚠️ 需求方 2026-09-21 撤下按钮下方那条 `Content updated — reshare to founder.`
            （当时按 `gap.stale || gap.generating` 且未分享时出）。连同 2026-09-20 撤下的
            `Refreshing analysis…`，**期次级的横幅位现在只剩轮询耗尽那一条**。
            `stale` / `generating` 两个字段本身已于 2026-09-24 随差距分析任务化从接口 17 删除。
          */}
```

- [ ] **Step 4** `ErlGapBlock.tsx:413-421`（JSX 内注释，只改最后三行）

```tsx
// Before（:418-420）
            ⚠️ 弹框里看到的是**维度级** `narrative`，**不是**这里撤下的期次级 `summary` ——
            后者在全前端已再无渲染方（`gap.summary` 字段本身不裁，契约照旧下发；
            要不要挪进弹框顶部已登记 `docs/待优化项.md`）。别把人引到弹框去找它。
```

```tsx
// After
            ⚠️ 弹框里看到的是**维度级** `narrative`，**不是**这里撤下的期次级 `summary` ——
            后者已于 2026-09-24 随差距分析任务化从接口 17 出参与 DTO 整体删除（任务化后每维
            一次 LLM，不再有整期小结）。别把人引到弹框去找它。
```

- [ ] **Step 5** `GapDetailsModal.tsx:20-23`（文件头）

```ts
// Before
 * ⚠️ 说明行恒是 `TEXT.gapDetailsSubtitle` 那句 `AI-generated analysis…`，**不拿接口 17 的
 * `summary` 顶掉它** —— `AI GENERATED` 徽章撤下后这是弹窗里唯一的 AI 告知，被顶掉就一处不剩；
 * 且 `summary` 在 ERL Card 卡面上（`ErlGapBlock`）已经渲染过一遍，弹窗里再来一次是重复。
```

```ts
// After
 * ⚠️ 说明行恒是 `TEXT.gapDetailsSubtitle` 那句 `AI-generated analysis…` —— `AI GENERATED`
 * 徽章撤下后这是弹窗里唯一的 AI 告知。~~接口 17 的期次级 `summary`~~ 已于 2026-09-24 随差距
 * 分析任务化删除，弹窗只有维度级 `narrative` 可用，没有别的叙述能顶掉这一句。
```

- [ ] **Step 6** `GapDetailsModal.tsx:290-295`（gap 条目内注释）

```tsx
// Before
                            {/*
                              ⚠️ 标题下那行灰字说明（`gap.note`）需求方 2026-09-23 圈图撤下，
                              条目只留一行标题；更早（2026-09-21）撤下的 `evidenceMissing` 标注同理。
                              两个字段本身**不裁**：接口仍下发、DTO 照旧保留，A4 的
                              `PriorityGapsPanel` 也还在渲染它们（那一处需求方没动）。
                            */}
```

```tsx
// After
                            {/*
                              ⚠️ 标题下那行灰字说明（`gap.note`）需求方 2026-09-23 圈图撤下，
                              条目只留一行标题；更早（2026-09-21）撤下的 `evidenceMissing` 标注同理。
                              两个字段已于 2026-09-24 随差距分析任务化从接口出参与 DTO 删除
                              （Python 条目表只存标题，`note` 不再生成）。
                            */}
```

- [ ] **Step 7** `GapDetailsModal.tsx:313`

```tsx
// Before
                          {/* 理由 `action.why` 同 gap 的 `note`，2026-09-23 撤下，只留标题 */}
```

```tsx
// After
                          {/* 理由 `action.why` 同 gap 的 `note`：2026-09-23 撤下渲染、2026-09-24 随任务化从契约删除 */}
```

- [ ] **Step 8** 轻量校验：`npm run lint:fix`；过滤版 `tsc` 0 行。

---

### Task 5（需用户确认）：删除死组件 `PriorityGapsPanel` 及其专属样式 / 文案

> **执行前必须停下问用户**：台账 :184 / :277 明写「等需求方确认 E2 是否还要回来再定去留」，且 2026-09-23 追记「裁决 `PriorityGapsPanel` 去留时一并定这两个字段要不要留」—— 字段现在由设计稿 D7 拍板删了，组件本身仍需用户点头。否决则跳过本 Task，Task 2 的止血版留着。

**Files:**
- Delete: `web/CIOaas-web/src/pages/exitReadiness/components/PriorityGapsPanel.tsx`（无专属 less、无测试文件，已核实）
- Modify: `web/CIOaas-web/src/pages/exitReadiness/components/index.less:373-385`、`:825-857`
- Modify: `web/CIOaas-web/src/pages/exitReadiness/components/constants.ts:167-169`、`:178-184`
- Modify: `web/CIOaas-web/src/pages/exitReadiness/components/GapDetailsModal/GapDetailsModal.tsx:24-25`
- Modify: `web/CIOaas-web/src/pages/exitReadiness/dimension/DimensionPage.tsx:27-29`
- Modify: `web/CIOaas-web/src/pages/exitReadiness/README.md:91-92`、`:99`（域文档随删除同步，architecture.md §3.1 R8）
- Modify: `web/CIOaas-web/docs/待优化项.md:184`、`:277` → `web/CIOaas-web/docs/已完成优化.md` 追加一条

- [ ] **Step 1** 删除文件 `src/pages/exitReadiness/components/PriorityGapsPanel.tsx`。删前再 `Grep` 一次 `PriorityGapsPanel`：命中只允许是注释 / README / 台账。

- [ ] **Step 2** `index.less:373-385` 删 severity 色标三类（`Grep styles\.sev` 全仓只有该组件在用）

```less
// Before
// gap 的 severity 色标（HIGH 红 / MEDIUM 黄 / LOW 灰），与 .badge 组合使用。
// 原先 E2 面板与 A1 弹框各在 JSX 里抄一份 `SEVERITY_COLOR` 十六进制表，改一个色要改两处。
.sevHigh {
  .erlTinted(@erl-founder);
}

.sevMedium {
  .erlTinted(@erl-harvest);
}

.sevLow {
  .erlTinted(@erl-muted);
}

```

```less
// After —— 整段删除（`.badgeMuted` 与 `.dimBadge` 之间只留一个空行）
```

- [ ] **Step 3** `index.less:825-857` 删 E2 段（`.mutedRow / .gapItem / .gapTitle / .gapSeverity / .gapNote / .gapMissing / .actionsBlock` 七个类全仓只有该组件引用；`.sectionLabel / .empty / .emptyHint / .card / .badge` 另有消费方，**不动**）

```less
// Before
// ── E2 Priority Gaps（v4.4-D4：Strengths 已删，单列铺满） ──────────────
.mutedRow {
  margin-top: 8px;
  color: @erl-text-muted;
}

.gapItem {
  margin-top: 12px;
}

.gapTitle {
  font-weight: 600;
}

// severity 徽章紧跟 gap 标题（域级 .badge 本身不带外边距，间距在这里给）。
.gapSeverity {
  margin-left: 8px;
}

.gapNote {
  color: @erl-text-secondary;
  font-size: 13px;
  line-height: 20px;
}

.gapMissing {
  color: @erl-text-muted;
  font-size: 12px;
}

.actionsBlock {
  margin-top: 24px;
}

```

```less
// After —— 整段删除；紧随其后 `:859-861` 那段「A1 Gap 小卡样式已迁到 ErlCard.less」的注释保留
```

- [ ] **Step 4** `constants.ts` 删两个孤儿串（删后 `Grep noGapAnalysisHint|noNotesProvided` 全仓 0 命中；测试里断「不出现」用的是字面量正则，不引用这两个 key）

```ts
// Before（:167-170）
  noGapAnalysis: 'No gap analysis yet',
  noGapAnalysisHint:
    'Goldie needs scored questions with evidence notes for this dimension before it can suggest gaps and recommended actions.',
  gapAnalysisFailed: 'Gap analysis failed. Please try again.',
```

```ts
// After
  noGapAnalysis: 'No gap analysis yet',
  gapAnalysisFailed: 'Gap analysis failed. Please try again.',
```

```ts
// Before（:178-185）
  /**
   * `evidenceMissing` 条目下的灰色标注。
   * 2026-09-18：`evidenceMissing` 的判定口径由「该题无备注」放宽为「无备注**且**无可用附件
   * 摘要」（design-doc §5.2），有附件的题不再被错标成「没写备注」，文案随之改为不提 notes。
   * 串名 `noNotesProvided` 沿用原名。
   */
  noNotesProvided: 'No supporting evidence provided',
  noBenchmarkRecords: 'No benchmark records yet.',
```

```ts
// After
  noBenchmarkRecords: 'No benchmark records yet.',
```

- [ ] **Step 5** `GapDetailsModal.tsx:24-25`

```ts
// Before
 * ⚠️ severity 不再画色标徽章，改成原型的写法：图标一律琥珀色，档位落在文字
 * （`… — high severity`）。色标那套还在 `PriorityGapsPanel`（E2 面板）上，别顺手一起改。
```

```ts
// After
 * ⚠️ severity 不再画色标徽章，改成原型的写法：图标一律琥珀色，档位落在文字
 * （`… — high severity`）。~~色标那套还在 `PriorityGapsPanel`（E2 面板）上~~ 该死组件已于
 * 2026-09-24 删除，域级 `.sevHigh / .sevMedium / .sevLow` 随之一并删除。
```

- [ ] **Step 6** `DimensionPage.tsx:27-29`

```ts
// Before
 * Priority Gaps & Suggested Actions（E2）、Attached files。页面随之不再调接口 23，
 * `PriorityGapsPanel` 就此**没有消费方**（留着未删，见 `docs/待优化项.md`）；同样失去消费方的
 * `AttachedFilesCard` 已于 2026-09-21 随 `ingestStatus` 字段删除一并删掉。
```

```ts
// After
 * Priority Gaps & Suggested Actions（E2）、Attached files。页面随之不再调接口 23；失去消费方的
 * `AttachedFilesCard` 已于 2026-09-21 随 `ingestStatus` 字段删除一并删掉，`PriorityGapsPanel`
 * 已于 2026-09-24 随差距分析任务化（`note` / `why` / `evidenceMissing` 从契约删除）一并删除。
```

- [ ] **Step 7** `README.md`：① 删 `:91` 整行（`` `PriorityGapsPanel`（E2，⚠️ **2026-09-15 起全仓无消费方** …待需求方确认去留）、``）；② `:92` 中「（色标那套还在 `PriorityGapsPanel`）」→「（~~色标那套还在 `PriorityGapsPanel`~~ 已随该组件删除）」；③ 在 `:99` 「**2026-09-21 已删除**」段**之前**插入：

```md
  **2026-09-24 已删除**：`PriorityGapsPanel`（E2 Priority Gaps 面板）—— 2026-09-15 A3 撤下该区块后
  全仓无消费方；差距分析任务化把它唯一还在渲染的 `note` / `why` / `evidenceMissing` 从契约删除后
  整体下线，域级 `index.less` 的 `.sevHigh / .sevMedium / .sevLow` 与 E2 段七个类、
  `TEXT.noGapAnalysisHint` / `TEXT.noNotesProvided` 随之一并删除（删除时均无在线渲染方）。
```

- [ ] **Step 8** 台账：从 `docs/待优化项.md` 删 `:184`（「A3 砍掉四个区块后，两个组件没有消费方」，其 `AttachedFilesCard` 半边早已了结）与 `:277`（「`PriorityGapsPanel` 复活时要补题集 mismatch 第四态」）两条；`docs/已完成优化.md` 追加：

```md
- **删除死组件 `PriorityGapsPanel`（E2 面板）**（2026-09-24）：2026-09-15 起全仓零 import，差距分析任务化把它唯一还在渲染的 `note` / `why` / `evidenceMissing` 从契约删除后整体下线；连带删 `components/index.less` 的 `.sev*` 三类与 E2 段七个类、`TEXT.noGapAnalysisHint` / `TEXT.noNotesProvided`，README 与 `DimensionPage.tsx` / `GapDetailsModal.tsx` 注释同步。原待优化项「A3 砍掉四个区块后两个组件没有消费方」「`PriorityGapsPanel` 复活时要补 mismatch 第四态」一并了结（涉及文件见提交）
```

- [ ] **Step 9** 轻量校验：`npm run lint:fix`（stylelint 会跑到 `index.less`，但**不要**对 less 跑 prettier）；过滤版 `tsc` 0 行；`Grep "sevHigh|gapNote|gapMissing|mutedRow|actionsBlock|noNotesProvided|noGapAnalysisHint"` 全仓 `src/` 0 命中。

---

### Task 6（需用户确认后再改）：README gap 段与 `docs/` 台账

> 只有文档。按仓库记忆规则「台账别不请自写」，本 Task **先给用户看下面三条改动再动手**；否决则只做 Task 1-4 的代码，台账原样。

**Files:**
- Modify: `web/CIOaas-web/src/pages/exitReadiness/README.md:92`（`GapDetailsModal` 条目里关于 `summary` 的括注）
- Modify: `web/CIOaas-web/docs/待优化项.md:88`（接口 1 `gapSummary`）、`:287`（接口 17 `analyzedAt`）、`:291`（接口 17 `summary`）—— 三条删除
- Modify: `web/CIOaas-web/docs/已完成优化.md` —— 追加一条

- [ ] **Step 1** `README.md:92`：把「（`TEXT.gapDetailsSubtitle`；⚠️ 不拿接口 17 的 `summary` 顶掉它 —— `AI GENERATED` 徽章撤下后这是弹框里唯一的 AI 告知，且 `summary` 在卡面上已渲染过）」改为「（`TEXT.gapDetailsSubtitle`；`AI GENERATED` 徽章撤下后这是弹框里唯一的 AI 告知；~~接口 17 的期次级 `summary`~~ 已于 2026-09-24 随差距分析任务化从契约删除）」。其余 gap 相关段落（`services/api/exitReadiness/README.md:60-64/87-91` 的五个态标志与 D4 口径）**仍然成立，不动**。

- [ ] **Step 2** `docs/待优化项.md` 删除 `:88`、`:287`、`:291` 三条（各自整条 `- **…**` 行）。`:284`（接口 1 `questionSetMismatch / mismatchSide` 只映射不渲染）与 `:286`（无维度级失败信号）**不在本次范围，保留**；`:100` 里「同『接口 1 的 `gapSummary` 只映射不渲染』那条的处理方式」这句交叉引用改为「同 2026-09-24 已了结的 `gapSummary` 那条的处理方式（见已完成优化）」。

- [ ] **Step 3** `docs/已完成优化.md` 追加：

```md
- **接口 1 / 17 / 2 只映射不渲染的差距分析死字段随任务化整体删除**（2026-09-24）：设计稿 §7.2 拍板后，前端契约层 `response.ts` / `dto.ts` 与归一层 `erlService.ts` 删掉接口 1 `gapSummary`、接口 17 期次级 `summary / generatedAt / model / stale / generating / sharedAt / sharedBy`、维度级 `analyzedAt`、条目 `note / evidenceMissing`、动作 `why`（接口 2 / 17 共用），5 个测试同步并新增 DTO 键集合钉子；`dimensionStale` 后端恒发 false、前端六态 `updating` 分支保留。原待优化项「接口 1 的 `gapSummary` 只映射不渲染」「接口 17 的 `analyzedAt` 只映射不渲染」「接口 17 的期次级 `summary` 只映射不渲染」三条了结（涉及文件见提交）
```

- [ ] **Step 4** 校验：文档改动无需 lint / tsc；`Grep "gapSummary|analyzedAt" docs/待优化项.md` 只剩 `:284`（接口 1 mismatch 那条里的顺带提及）与 `:100` 的交叉引用。

---

### Task 7：测试（需用户下令后执行）

按仓库规则**改完不自动跑测试**；用户说「跑测试」后，在 `web/CIOaas-web` 下一次性跑本轮涉及的全部文件：

```powershell
npm test -- src/services/service/exitReadiness/erlService.test.ts src/services/service/exitReadiness/erlGapState.test.ts src/pages/companyOverview/home/components/ErlCard/__tests__ src/pages/exitReadiness/components/__tests__/GapDetailsModal.test.tsx
```

- [ ] **Step 1** 上面这条全绿（`umi test` 透传路径给 jest，多路径可一次给）。
- [ ] **Step 2** 若 Task 5 已执行，追加 `npm test -- src/pages/exitReadiness/components/__tests__/constants.test.ts`（它枚举域内 `TEXT`，确认删串没有连带）。
- [ ] **Step 3** 失败只允许是本计划改过的断言；`useErlCard.test.tsx` 若挂在 timer 上先看 `flush()` 拍数，别改 hook。

---

### Task 8：提交（需用户确认）

按 `standards/git.md`（`<type>(<scope>): <subject>`，英文、祈使、≤72 字符）。**`git add` / `git commit` 前找用户确认；不推送。** 建议拆两笔：

- [ ] **Step 1** Task 1-4（+ Task 6 若已确认）：

```
refactor(exitReadiness): drop gap analysis fields removed by the task model

Java sprint119 moves gap analysis to per-dimension tasks and stops sending
summary/generatedAt/model/stale/generating/sharedAt/sharedBy on the
period, analyzedAt on dimensions, note/evidenceMissing on gaps, why on
actions, and gapSummary on the ERL card. Remove them from response/dto,
erlService mapping and the related tests; dimensionStale is kept (server
now always false) so the six-state logic is untouched.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

- [ ] **Step 2** Task 5（若已确认）单独一笔：

```
refactor(exitReadiness): delete the unused PriorityGapsPanel

No importer since 2026-09-15; its last rendered fields (note/why/
evidenceMissing) were removed from the gap analysis contract. Drop the
component, its severity/E2 styles in index.less and two orphan TEXT keys.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

---

## 自查清单（设计稿 §7.2 删除项 ↔ 本计划落点）

| §7.2 删除项 | Response（Task 1） | DTO（Task 1） | 归一（Task 2） | 测试（Task 3） | 注释 / 文档 |
|---|---|---|---|---|---|
| 期次级 `summary` | `response.ts:625`（Step 4） | `dto.ts:636`（Step 8） | `erlService.ts:1053`（Step 4） | `erlService.test.ts` describe 重写（Step 2）；`useErlCard.test.tsx:117,396,400,405,410,418,474-475,495,503`（Step 3c/3f/3g）；`ErlGapBlock.test.tsx:65,220,312-319,327,347`（Step 4b/4c/4d） | `ErlGapBlock.tsx:413-421`、`GapDetailsModal.tsx:20-23`（Task 4）；README :92、台账 :291（Task 6） |
| 期次级 `generatedAt` / `model` / `stale` / `generating` | `response.ts:631-634`（Step 4） | `dto.ts:642-645`（Step 8） | `erlService.ts:1083-1086`（Step 4） | `useErlCard.test.tsx:122-125`（Step 3c）；`ErlGapBlock.test.tsx:70-73,601`（Step 4b/4f）；`erlService.test.ts` 各 fixture（Step 2） | `ErlGapBlock.tsx:45-47,360-365`（Task 4） |
| 期次级 `sharedAt` / `sharedBy`（接口 17） | `response.ts:628-629`（Step 4） | `dto.ts:639-640`（Step 8） | `erlService.ts:1055-1056`（Step 4） | `useErlCard.test.tsx:119-120`；`ErlGapBlock.test.tsx:67-68`；`erlService.test.ts` 各 fixture | `ErlGapBlock.tsx:172-177`（Task 4）；接口 27 出参**保留**（§0-③） |
| 接口 1 `gapSummary` | `response.ts:106`（Step 1） | `dto.ts:150`（Step 5） | `erlService.ts:477`（Step 2） | `erlService.test.ts:68,111,123,150,197,215,235`（Step 1）；`useErlCard.test.tsx:78`（Step 3a）；`ErlCard.test.tsx:115`（Step 6） | 台账 :88（Task 6） |
| 维度级 `analyzedAt` | `response.ts:606-607`（Step 3） | `dto.ts:621-622`（Step 7） | `erlService.ts:1077`（Step 4） | `erlService.test.ts` 第 3 个用例（Step 2）；`useErlCard.test.tsx:103,132,271,276`（Step 3b/3d/3e）；`ErlGapBlock.test.tsx:53` + 9 处（Step 4a/4e）；`GapDetailsModal.test.tsx:36,259`（Step 5a/5d） | 台账 :287（Task 6） |
| 条目 `note` / `evidenceMissing` | `response.ts:193,195`（Step 2） | `dto.ts:216,218`（Step 6） | `erlService.ts:315,319`（Step 1） | `erlService.test.ts:525,545`（Step 2）；`GapDetailsModal.test.tsx:49,51,97-101`（Step 5b/5c） | `PriorityGapsPanel.tsx:81-84` 止血（Task 2 Step 6）→ 删除（Task 5）；`GapDetailsModal.tsx:290-295`（Task 4） |
| 动作 `why` | `response.ts:200`（Step 2） | `dto.ts:223`（Step 6） | `erlService.ts:547,1081`（Step 3/4） | `erlService.test.ts:526`（Step 2）；`GapDetailsModal.test.tsx:54,98`（Step 5b/5c） | `PriorityGapsPanel.tsx:95` 止血（Task 2 Step 7）→ 删除（Task 5）；`GapDetailsModal.tsx:313`（Task 4） |
| `dimensionStale`（恒 false，**保留**） | `response.ts:612` 注释改口（Step 3） | `dto.ts:624` 注释改口（Step 7） | `erlService.ts:1078` 原样 | `erlGapState.test.ts` 零改动；`erlService.test.ts` 键集合钉子含它 | `useErlCard.ts` / `erlGapState.ts` 不动 |

- [ ] 计划内每个 Task 的校验命令都写死（§2）；无「运行测试」步骤混进 Task 1-6。
- [ ] Task 5 / Task 6 / Task 8 标注了「需用户确认」，Task 7 标注了「需用户下令」。
- [ ] 不做清单（§1）覆盖任务书要求的四条：不加 waiting / failed 态、轮询不动、Share 请求体不动、六态优先级不动。
