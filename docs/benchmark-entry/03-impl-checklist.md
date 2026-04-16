# Benchmark Entry 实现检查清单

> 关联 PRD：`benchmark-entry-requirements.md` | 关联 TDD：`02-technical-design.md`
> 状态标记：⬜ 未开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已阻塞

---

## Phase 1: 后端基础（CIOaas-api）

### 1.1 数据层 — Entity 实体类 [TDD §2.1]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| B-01 | 创建 `BenchmarkCategory` 实体类 | `benchmark/domain/BenchmarkCategory.java` | ✅ | 无 |
| B-02 | 创建 `BenchmarkMetric` 实体类 | `benchmark/domain/BenchmarkMetric.java` | ✅ | 无 |
| B-03 | 创建 `BenchmarkDetail` 实体类 | `benchmark/domain/BenchmarkDetail.java` | ✅ | 无 |
| B-04 | 创建 `BenchmarkPlatform` 实体类 | `benchmark/domain/BenchmarkPlatform.java` | ✅ | 无 |

**验证**：实体类编译通过，字段、注解与 TDD §2.1 一致

### 1.2 数据层 — Repository [TDD §2.3]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| B-05 | 创建 `BenchmarkCategoryRepository` | `benchmark/repository/BenchmarkCategoryRepository.java` | ✅ | B-01 |
| B-06 | 创建 `BenchmarkMetricRepository` | `benchmark/repository/BenchmarkMetricRepository.java` | ✅ | B-02 |
| B-07 | 创建 `BenchmarkDetailRepository` | `benchmark/repository/BenchmarkDetailRepository.java` | ✅ | B-03 |
| B-08 | 创建 `BenchmarkPlatformRepository` | `benchmark/repository/BenchmarkPlatformRepository.java` | ✅ | B-04 |

**验证**：Spring Boot 启动不报错，Repository 可自动注入

### 1.3 数据库脚本 [TDD §2.1]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| B-09 | 编写 DDL 建表脚本（benchmark_category / benchmark_metric / benchmark_detail / benchmark_platform + 索引） | DDL 脚本或 JPA 自动建表 | ✅ | 无 |
| B-10 | 编写种子数据 SQL（4 Category + 6 Metric + 3 Platform） | 种子数据 SQL | ✅ | B-09 |

**验证**：数据库中表结构和种子数据正确创建

### 1.4 种子数据初始化器 [TDD §2.4]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| B-11 | 创建 `BenchmarkDataInitializer`（实现 `ApplicationRunner`，幂等检查 + `@Transactional`） | `benchmark/config/BenchmarkDataInitializer.java` | ✅ | B-05, B-06, B-08, B-10 |

**验证**：首次启动插入种子数据，再次启动跳过不重复插入

### 1.5 DTO + Mapper [TDD §2.3]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| B-12 | 创建 `BenchmarkCategoryDto`（嵌套 metrics 列表） | `benchmark/vo/BenchmarkCategoryDto.java` | ✅ | 无 |
| B-13 | 创建 `BenchmarkMetricDto`（嵌套 details 列表 + detailCount） | `benchmark/vo/BenchmarkMetricDto.java` | ✅ | 无 |
| B-14 | 创建 `BenchmarkDetailDto` | `benchmark/vo/BenchmarkDetailDto.java` | ✅ | 无 |
| B-15 | 创建 `BenchmarkPlatformDto` | `benchmark/vo/BenchmarkPlatformDto.java` | ✅ | 无 |
| B-16 | 创建 `BenchmarkDetailSaveInput`（新增请求体） | `benchmark/vo/BenchmarkDetailSaveInput.java` | ✅ | 无 |
| B-17 | 创建 `BenchmarkDetailModifyInput`（编辑请求体，不含 metricId） | `benchmark/vo/BenchmarkDetailModifyInput.java` | ✅ | 无 |
| B-18 | 创建 `BenchmarkFormulaInput`（Formula 更新请求体） | `benchmark/vo/BenchmarkFormulaInput.java` | ✅ | 无 |
| B-19 | 创建 `BenchmarkCategoryMapper` | `benchmark/mapper/BenchmarkCategoryMapper.java` | ✅ | B-01, B-12 |
| B-20 | 创建 `BenchmarkMetricMapper` | `benchmark/mapper/BenchmarkMetricMapper.java` | ✅ | B-02, B-13 |
| B-21 | 创建 `BenchmarkDetailMapper` | `benchmark/mapper/BenchmarkDetailMapper.java` | ✅ | B-03, B-14 |

**验证**：Mapper 可正确将 Entity ↔ DTO 互转

### 1.6 Service 层 [TDD §2.3, §2.4]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| B-22 | 创建 `BenchmarkService` 接口（定义 getAllBenchmarkData / addDetail / updateDetail / deleteDetail / updateFormula / getPlatforms） | `benchmark/service/BenchmarkService.java` | ✅ | B-12~B-18 |
| B-23 | 实现 `BenchmarkServiceImpl.getAllBenchmarkData()`：查询 Category + Metric + Detail，手动组装 DTO 树，避免 N+1 | `benchmark/service/BenchmarkServiceImpl.java` | ✅ | B-05~B-08, B-19~B-21, B-22 |
| B-24 | 实现 `BenchmarkServiceImpl.addDetail()`：校验 metricId 存在，保存 Detail，返回 DTO | 同上 | ✅ | B-23 |
| B-25 | 实现 `BenchmarkServiceImpl.updateDetail()`：校验 detailId 存在，更新字段，返回 DTO | 同上 | ✅ | B-23 |
| B-26 | 实现 `BenchmarkServiceImpl.deleteDetail()`：校验 detailId 存在，删除记录 | 同上 | ✅ | B-23 |
| B-27 | 实现 `BenchmarkServiceImpl.updateFormula()`：校验 metricId 存在，更新 lgFormula 字段（空字符串非 null） | 同上 | ✅ | B-23 |
| B-28 | 实现 `BenchmarkServiceImpl.getPlatforms()`：查询 benchmark_platform 表，按 sort_order 排序 | 同上 | ✅ | B-23 |

**验证**：Service 方法可独立测试通过（CRUD + 树组装）

### 1.7 Controller 层 [TDD §2.2]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| B-29 | 创建 `BenchmarkController`，基础路径 `/web/benchmark` | `benchmark/controller/BenchmarkController.java` | ✅ | B-22 |
| B-30 | API-01: `GET /web/benchmark/metrics` — 获取所有基准数据完整树 | 同上 | ✅ | B-23, B-29 |
| B-31 | API-02: `POST /web/benchmark/details` — 新增详情行 | 同上 | ✅ | B-24, B-29 |
| B-32 | API-03: `PUT /web/benchmark/details/{detailId}` — 编辑详情行 | 同上 | ✅ | B-25, B-29 |
| B-33 | API-04: `DELETE /web/benchmark/details/{detailId}` — 删除详情行 | 同上 | ✅ | B-26, B-29 |
| B-34 | API-05: `PUT /web/benchmark/metrics/{metricId}/formula` — 更新 LG Formula | 同上 | ✅ | B-27, B-29 |
| B-35 | API-06: `GET /web/benchmark/platforms` — 获取 Platform 列表 | 同上 | ✅ | B-28, B-29 |

### Phase 1 验证检查点

- ⬜ Spring Boot 启动正常，种子数据自动初始化
- ⬜ 6 个 API 可通过 Postman/curl 调通，响应格式与 TDD §2.2 一致
- ⬜ Detail CRUD 数据正确持久化到数据库
- ⬜ Formula 更新保存空字符串（非 null）
- ⬜ 不存在的 ID 返回合适的错误状态码

---

## Phase 2: 前端基础（CIOaas-web）

### 2.1 路由配置 [TDD §3.1]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-01 | 在 `config/routes.ts` 添加 `/benchmark-entry` 路由 | `config/routes.ts` | ✅ | 无 |

### 2.2 API Service 层 [TDD §3.5]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-02 | 创建 `benchmarkService.ts`，封装 6 个 API 调用（getBenchmarkMetrics / getBenchmarkPlatforms / addBenchmarkDetail / updateBenchmarkDetail / deleteBenchmarkDetail / updateBenchmarkFormula） | `src/services/api/benchmark/benchmarkService.ts` | ✅ | 无 |

### 2.3 类型定义 + 常量 [TDD §3.3]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-03 | 定义 TypeScript 类型（BenchmarkCategory / BenchmarkMetric / BenchmarkDetail / PlatformOption / BenchmarkPageState） | `src/pages/BenchmarkEntry/types.ts` | ✅ | 无 |
| F-04 | 定义常量（DataType 枚举等） | `src/pages/BenchmarkEntry/constants.ts` | ✅ | 无 |

### 2.4 页面骨架 [TDD §3.2]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-05 | 创建页面入口 `index.tsx`（标题区 + Loading 骨架） | `src/pages/BenchmarkEntry/index.tsx` | ✅ | F-01, F-03 |
| F-06 | 创建页面样式 `index.less` | `src/pages/BenchmarkEntry/index.less` | ✅ | F-05 |

### 2.5 数据 Hook [TDD §3.4]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-07 | 实现 `useBenchmarkData` hook（loadData / addDetail / updateDetail / deleteDetail / updateFormula） | `src/pages/BenchmarkEntry/hooks/useBenchmarkData.ts` | ✅ | F-02, F-03 |

### Phase 2 验证检查点

- ⬜ 访问 `/benchmark-entry` 可看到页面骨架
- ⬜ API Service 函数定义完整，类型正确
- ⬜ Hook 可正确加载数据并更新 state

---

## Phase 3: 前端表格与交互（CIOaas-web）

### 3.1 主表格组件 [TDD §3.6.1]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-08 | 创建 `BenchmarkTable.tsx`：HTML table 结构，14 列表头，遍历 categories → metrics 渲染 | `src/pages/BenchmarkEntry/components/BenchmarkTable.tsx` | ✅ | F-05, F-07 |
| F-09 | 创建 `BenchmarkTable.less`：表格基础样式 | `src/pages/BenchmarkEntry/components/BenchmarkTable.less` | ✅ | F-08 |

### 3.2 Metric 父行 [TDD §3.6.1, §3.6.2]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-10 | 创建 `MetricRow.tsx`：展开/折叠切换 + 折叠时显示 detailCount + Category rowSpan 动态计算 | `src/pages/BenchmarkEntry/components/MetricRow.tsx` | ✅ | F-08 |

### 3.3 Detail 行 — 只读态 [TDD §3.6.3]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-11 | 创建 `DetailRow.tsx`：只读渲染所有字段 + hover 显示编辑/删除按钮 | `src/pages/BenchmarkEntry/components/DetailRow.tsx` | ✅ | F-08 |

### 3.4 Detail 行 — 编辑态 [TDD §3.6.3]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-12 | 在 `DetailRow.tsx` 中实现编辑态：字段变输入控件、Platform 下拉、DataType 下拉、确认/取消按钮、Enter 提交 / Escape 取消 | 同 F-11 | ✅ | F-11 |

### 3.5 新增行 [TDD §3.6.3]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-13 | 创建 `AddDetailRow.tsx`：空白可编辑行 + "Add detail" 按钮触发 + 提交后追加到列表 | `src/pages/BenchmarkEntry/components/AddDetailRow.tsx` | ✅ | F-12 |

### 3.6 YearPicker 组件 [TDD §3.2]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-14 | 创建 `YearPicker.tsx`：年份选择器 + 样式 | `src/pages/BenchmarkEntry/components/YearPicker.tsx` | ✅ | 无 |

### 3.7 FormulaInput 组件 [TDD §3.6.4]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-15 | 创建 `FormulaInput.tsx`：防抖 800ms 自动保存 + 失焦 flush + 保存失败 Toast | `src/pages/BenchmarkEntry/components/FormulaInput.tsx` | ✅ | F-02 |

### 3.8 Category rowSpan [TDD §3.6.2]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-16 | 实现 `calcCategoryRowSpan` 函数：根据展开状态动态计算 Category 单元格 rowSpan | `BenchmarkTable.tsx` | ✅ | F-10 |

### Phase 3 验证检查点

- ⬜ 表格正确渲染 Category → Metric → Detail 三级结构
- ⬜ Metric 行点击可展开/折叠，detailCount 正确
- ⬜ Category rowSpan 随展开/折叠动态变化
- ⬜ Detail 行可在只读/编辑态间切换
- ⬜ 新增行填写后可成功提交
- ⬜ Formula 输入 800ms 防抖保存生效
- ⬜ YearPicker 可正常选择年份

---

## Phase 4: 完善与联调

### 4.1 权限控制 [TDD §3.6.5]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-17 | 实现管理员判断逻辑（roleType === 2） | `index.tsx` | ✅ | 无 |
| F-18 | 管理员可见：编辑/删除按钮、Add detail 按钮、FormulaInput 可编辑 | 各组件 | ✅ | F-17 |
| F-19 | 非管理员：Formula 显示纯文本，无增删改按钮 | 各组件 | ✅ | F-17 |

### 4.2 Loading 与空状态 [TDD §3.3]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-20 | 页面加载中显示 Loading/Spin | `index.tsx` | ✅ | F-07 |
| F-21 | 数据为空时显示空状态提示 | `BenchmarkTable.tsx` | ✅ | F-08 |

### 4.3 错误处理 [TDD §3.6.6]

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-22 | CRUD 操作失败时 Toast 错误提示 | `useBenchmarkData.ts` | ✅ | F-07 |
| F-23 | 删除乐观更新 + 失败恢复逻辑 | `useBenchmarkData.ts` | ✅ | F-07 |

### 4.4 样式完善

| # | 任务 | 文件 | 状态 | 依赖 |
|---|------|------|------|------|
| F-24 | 表格整体样式（边框、间距、hover 效果、Category 背景色区分） | `BenchmarkTable.less` / `index.less` | ✅ | F-08~F-16 |
| F-25 | 编辑态输入框样式对齐 | `BenchmarkTable.less` | ✅ | F-12 |

### 4.5 前后端联调

| # | 任务 | 说明 | 状态 | 依赖 |
|---|------|------|------|------|
| I-01 | API-01 联调：页面加载 → 获取完整数据树 → 正确渲染表格 | 验证数据格式、字段映射 | ⬜ | B-30, F-08 |
| I-02 | API-02 联调：新增 Detail → 行追加到 UI → 数据库已持久化 | 验证 metricId 关联 | ⬜ | B-31, F-13 |
| I-03 | API-03 联调：编辑 Detail → UI 更新 → 数据库已更新 | 验证字段完整性 | ⬜ | B-32, F-12 |
| I-04 | API-04 联调：删除 Detail → 乐观移除 → 数据库已删除 / 失败恢复 | 验证乐观更新 | ⬜ | B-33, F-23 |
| I-05 | API-05 联调：编辑 Formula → 防抖保存 → 数据库已更新 | 验证防抖 800ms | ⬜ | B-34, F-15 |
| I-06 | API-06 联调：Platform 下拉选项正确加载 | 验证选项列表 | ⬜ | B-35, F-12 |

---

## 完成标准

| 标准 | 状态 |
|------|------|
| 所有后端 API（6 个）已实现并可调通 | ⬜ |
| 种子数据初始化正常工作 | ⬜ |
| 前端 Category → Metric → Detail 三级表格正确渲染 | ⬜ |
| 展开/折叠交互正常，rowSpan 动态计算正确 | ⬜ |
| Detail CRUD 全流程可用（新增/编辑/删除） | ⬜ |
| LG Formula 防抖保存正常 | ⬜ |
| 管理员/非管理员权限控制生效 | ⬜ |
| 删除乐观更新 + 失败恢复正常 | ⬜ |
| 错误场景有 Toast 提示 | ⬜ |
| 前后端 6 个接口全部联调通过 | ⬜ |

---

## 任务依赖总览

```
B-01~B-04 (Entity)
    ↓
B-05~B-08 (Repository)     B-12~B-18 (DTO/Input)
    ↓                           ↓
B-09~B-10 (DDL/Seed)    B-19~B-21 (Mapper)
    ↓                           ↓
B-11 (DataInitializer)   B-22 (Service 接口)
                              ↓
                         B-23~B-28 (Service 实现)
                              ↓
                         B-29~B-35 (Controller)
                              ↓
                         ─── 后端完成 ───
                              ↓
F-01 (路由)  F-02 (API Service)  F-03~F-04 (类型/常量)
    ↓              ↓                    ↓
F-05~F-06 (页面骨架)    F-07 (Hook)
         ↓                  ↓
    F-08~F-09 (主表格)
         ↓
    F-10 (MetricRow) → F-16 (rowSpan)
         ↓
    F-11 (DetailRow 只读) → F-12 (编辑态) → F-13 (AddDetailRow)
                                              ↓
    F-14 (YearPicker)   F-15 (FormulaInput)
         ↓                    ↓
    F-17~F-19 (权限)   F-20~F-21 (Loading/空态)
         ↓                    ↓
    F-22~F-23 (错误处理)  F-24~F-25 (样式)
                              ↓
                         ─── 前端完成 ───
                              ↓
                         I-01~I-06 (联调)
```
