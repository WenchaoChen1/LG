# Benchmark Entry 技术设计文档（TDD）

> 版本：v1.0 | 更新日期：2026-03-23
> 关联 PRD：`benchmark-entry-requirements.md`

---

## 一、设计概览

### 1.1 需求摘要

实现一个全局共享的 SaaS 行业基准指标管理页面，支持按 Category → Metric → Detail Row 三级结构展示和管理基准数据，支持内联编辑、展开/折叠、LG Formula 防抖保存。

### 1.2 技术方案摘要

- **后端**：在 CIOaas-api 的 `gstdev-cioaas-web` 模块中新增 `benchmark` 包，提供 Metric 查询、Detail Row CRUD、Formula 更新的 REST API
- **前端**：在 CIOaas-web 中新增 `/benchmark-entry` 页面，使用 Ant Design Table + 自定义内联编辑组件

### 1.3 影响范围

| 项目 | 影响模块 | 变更类型 |
|------|----------|----------|
| CIOaas-api | 新增 `benchmark` 包 | 新增 |
| CIOaas-web | 新增 `BenchmarkEntry` 页面 + API 服务 + 路由 | 新增 |

---

## 二、后端设计（CIOaas-api）

### 2.1 数据模型

#### 实体关系

```
BenchmarkCategory (1) ──→ (N) BenchmarkMetric (1) ──→ (N) BenchmarkDetail
```

- Category 和 Metric 为种子数据，应用启动时确保存在
- Detail Row 由用户动态创建

#### 实体 1：BenchmarkCategory

```java
@Entity
@Table(name = "benchmark_category")
public class BenchmarkCategory extends AbstractCustomEntity {
    @Id
    @UuidGenerator
    @Column(name = "category_id", length = 36)
    private String id;

    @Column(name = "name", nullable = false, length = 100)
    private String name;                    // e.g. "Revenue & Growth"

    @Column(name = "sort_order", nullable = false)
    private Integer sortOrder;              // 显示顺序：1,2,3,4

    @OneToMany(mappedBy = "category", fetch = FetchType.LAZY)
    @OrderBy("sortOrder ASC")
    private List<BenchmarkMetric> metrics;
}
```

#### 实体 2：BenchmarkMetric

```java
@Entity
@Table(name = "benchmark_metric")
public class BenchmarkMetric extends AbstractCustomEntity {
    @Id
    @UuidGenerator
    @Column(name = "metric_id", length = 36)
    private String id;

    @Column(name = "name", nullable = false, length = 100)
    private String name;                    // e.g. "ARR Growth Rate"

    @Column(name = "lg_formula", columnDefinition = "TEXT DEFAULT ''")
    private String lgFormula;               // 可编辑公式，默认空字符串

    @Column(name = "sort_order", nullable = false)
    private Integer sortOrder;              // 在 Category 内的排序

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id", nullable = false)
    private BenchmarkCategory category;

    @OneToMany(mappedBy = "metric", fetch = FetchType.LAZY)
    @OrderBy("createdAt ASC")
    private List<BenchmarkDetail> details;
}
```

#### 实体 3：BenchmarkDetail

```java
@Entity
@Table(name = "benchmark_detail")
public class BenchmarkDetail extends AbstractCustomEntity {
    @Id
    @UuidGenerator
    @Column(name = "detail_id", length = 36)
    private String id;

    @Column(name = "platform", length = 50)
    private String platform;               // enum value or null

    @Column(name = "edition", length = 200)
    private String edition;

    @Column(name = "metric_name", length = 200)
    private String metricName;             // 平台原始指标名

    @Column(name = "definition", columnDefinition = "TEXT")
    private String definition;

    @Column(name = "fy_period", length = 4)
    private String fyPeriod;               // "2024"

    @Column(name = "segment", length = 200)
    private String segment;

    @Column(name = "p25", length = 50)
    private String p25;

    @Column(name = "median", length = 50)
    private String median;

    @Column(name = "p75", length = 50)
    private String p75;

    @Column(name = "data_type", length = 20)
    private String dataType;               // "Actual" / "Forecast"

    @Column(name = "best_guess", length = 200)
    private String bestGuess;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "metric_id", nullable = false)
    private BenchmarkMetric metric;
}
```

#### 数据库表结构

```sql
CREATE TABLE benchmark_category (
    category_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(36)
);

CREATE TABLE benchmark_metric (
    metric_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    lg_formula TEXT DEFAULT '',
    sort_order INTEGER NOT NULL,
    category_id VARCHAR(36) NOT NULL REFERENCES benchmark_category(category_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(36)
);

CREATE TABLE benchmark_detail (
    detail_id VARCHAR(36) PRIMARY KEY,
    platform VARCHAR(50),
    edition VARCHAR(200),
    metric_name VARCHAR(200),
    definition TEXT,
    fy_period VARCHAR(4),
    segment VARCHAR(200),
    p25 VARCHAR(50),
    median VARCHAR(50),
    p75 VARCHAR(50),
    data_type VARCHAR(20),
    best_guess VARCHAR(200),
    metric_id VARCHAR(36) NOT NULL REFERENCES benchmark_metric(metric_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(36)
);

CREATE INDEX idx_benchmark_detail_metric ON benchmark_detail(metric_id);
CREATE INDEX idx_benchmark_metric_category ON benchmark_metric(category_id);
```

#### 种子数据

```sql
-- Categories
INSERT INTO benchmark_category (category_id, name, sort_order, created_at, updated_at) VALUES
('cat-revenue-growth',       'Revenue & Growth',            1, NOW(), NOW()),
('cat-profitability',        'Profitability & Efficiency',  2, NOW(), NOW()),
('cat-burn-runway',          'Burn & Runway',               3, NOW(), NOW()),
('cat-capital-efficiency',   'Capital Efficiency',          4, NOW(), NOW());

-- Metrics
INSERT INTO benchmark_metric (metric_id, name, lg_formula, sort_order, category_id, created_at, updated_at) VALUES
('met-arr-growth',           'ARR Growth Rate',         '', 1, 'cat-revenue-growth',     NOW(), NOW()),
('met-gross-margin',         'Gross Margin',            '', 1, 'cat-profitability',      NOW(), NOW()),
('met-net-burn',             'Monthly Net Burn Rate',   '', 1, 'cat-burn-runway',        NOW(), NOW()),
('met-runway',               'Monthly Runway',          '', 2, 'cat-burn-runway',        NOW(), NOW()),
('met-rule-of-40',           'Rule of 40',              '', 1, 'cat-capital-efficiency', NOW(), NOW()),
('met-sales-efficiency',     'Sales Efficiency Ratio',  '', 2, 'cat-capital-efficiency', NOW(), NOW());
```

**种子数据加载方式**：在 `benchmark` 包中创建 `BenchmarkDataInitializer` 实现 `ApplicationRunner`，在应用启动时检查数据是否存在，不存在则插入。

#### Platform 配置表

```sql
CREATE TABLE benchmark_platform (
    platform_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO benchmark_platform (platform_id, name, sort_order) VALUES
('plt-benchmarkit', 'Benchmarkit.ai', 1),
('plt-keybanc',     'KeyBanc',        2),
('plt-highalpha',   'High Alpha',     3);
```

---

### 2.2 API 接口设计

**基础路径**：`/web/benchmark`

#### API-01: 获取所有基准数据（含 Category → Metric → Detail 完整树）

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/web/benchmark/metrics` |
| 认证 | 需要登录态 |
| 权限 | 所有已登录用户 |

**响应体**：

```json
{
  "success": true,
  "message": "success",
  "data": [
    {
      "categoryId": "cat-revenue-growth",
      "categoryName": "Revenue & Growth",
      "sortOrder": 1,
      "metrics": [
        {
          "metricId": "met-arr-growth",
          "metricName": "ARR Growth Rate",
          "lgFormula": "(Current ARR - Previous ARR) / Previous ARR",
          "sortOrder": 1,
          "detailCount": 3,
          "details": [
            {
              "detailId": "uuid-xxx",
              "platform": "Benchmarkit.ai",
              "edition": "Q3 2024 SaaS Benchmarks",
              "metricName": "ARR Growth",
              "definition": "...",
              "fyPeriod": "2024",
              "segment": "",
              "p25": "15%",
              "median": "25%",
              "p75": "40%",
              "dataType": "Actual",
              "bestGuess": "30%"
            }
          ]
        }
      ]
    }
  ]
}
```

#### API-02: 新增详情行

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/web/benchmark/details` |
| 认证 | 需要登录态 |
| 权限 | 本期不校验管理员（BR-15） |

**请求体**：

```json
{
  "metricId": "met-arr-growth",
  "platform": "Benchmarkit.ai",
  "edition": "Q3 2024 SaaS Benchmarks",
  "metricName": "ARR Growth",
  "definition": "",
  "fyPeriod": "2024",
  "segment": "",
  "p25": "15%",
  "median": "25%",
  "p75": "40%",
  "dataType": "Actual",
  "bestGuess": "30%"
}
```

**响应体**：

```json
{
  "success": true,
  "message": "success",
  "data": {
    "detailId": "uuid-generated",
    "platform": "Benchmarkit.ai",
    "edition": "Q3 2024 SaaS Benchmarks",
    ...
  }
}
```

#### API-03: 编辑详情行

| 项目 | 说明 |
|------|------|
| 方法 | PUT |
| 路径 | `/web/benchmark/details/{detailId}` |
| 认证 | 需要登录态 |
| 权限 | 本期不校验管理员 |

**请求体**：同 API-02（不含 metricId）

**响应体**：更新后的完整 Detail 对象

#### API-04: 删除详情行

| 项目 | 说明 |
|------|------|
| 方法 | DELETE |
| 路径 | `/web/benchmark/details/{detailId}` |
| 认证 | 需要登录态 |
| 权限 | 本期不校验管理员 |

**响应体**：

```json
{
  "success": true,
  "message": "success",
  "data": null
}
```

#### API-05: 更新 LG Formula

| 项目 | 说明 |
|------|------|
| 方法 | PUT |
| 路径 | `/web/benchmark/metrics/{metricId}/formula` |
| 认证 | 需要登录态 |
| 权限 | 本期不校验管理员 |

**请求体**：

```json
{
  "lgFormula": "(Current ARR - Previous ARR) / Previous ARR"
}
```

**响应体**：

```json
{
  "success": true,
  "message": "success",
  "data": {
    "metricId": "met-arr-growth",
    "lgFormula": "(Current ARR - Previous ARR) / Previous ARR"
  }
}
```

#### API-06: 获取 Platform 列表

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/web/benchmark/platforms` |
| 认证 | 需要登录态 |
| 权限 | 所有已登录用户 |

**响应体**：

```json
{
  "success": true,
  "message": "success",
  "data": [
    { "platformId": "plt-benchmarkit", "name": "Benchmarkit.ai" },
    { "platformId": "plt-keybanc", "name": "KeyBanc" },
    { "platformId": "plt-highalpha", "name": "High Alpha" }
  ]
}
```

---

### 2.3 包结构

```
com.gstdev.cioaas.web.benchmark
├── controller/
│   └── BenchmarkController.java
├── service/
│   ├── BenchmarkService.java              (interface)
│   └── BenchmarkServiceImpl.java          (implementation)
├── repository/
│   ├── BenchmarkCategoryRepository.java
│   ├── BenchmarkMetricRepository.java
│   ├── BenchmarkDetailRepository.java
│   └── BenchmarkPlatformRepository.java
├── domain/
│   ├── BenchmarkCategory.java
│   ├── BenchmarkMetric.java
│   ├── BenchmarkDetail.java
│   └── BenchmarkPlatform.java
├── vo/
│   ├── BenchmarkCategoryDto.java          (嵌套 metrics 列表)
│   ├── BenchmarkMetricDto.java            (嵌套 details 列表)
│   ├── BenchmarkDetailDto.java
│   ├── BenchmarkPlatformDto.java
│   ├── BenchmarkDetailSaveInput.java
│   ├── BenchmarkDetailModifyInput.java
│   └── BenchmarkFormulaInput.java
├── mapper/
│   ├── BenchmarkCategoryMapper.java
│   ├── BenchmarkMetricMapper.java
│   └── BenchmarkDetailMapper.java
└── config/
    └── BenchmarkDataInitializer.java      (种子数据初始化)
```

### 2.4 关键实现逻辑

1. **全量加载**：API-01 一次性返回 Category → Metric → Detail 完整树结构，前端无需多次请求。由于数据量可控（4 Category × 6 Metric × N Detail），使用 JPA `FetchType.LAZY` + 在 Service 层手动组装 DTO 树避免 N+1 查询。

2. **种子数据初始化**：`BenchmarkDataInitializer` 实现 `ApplicationRunner`，启动时检查 `benchmark_category` 表是否有数据，无则插入种子数据。使用 `@Transactional` 确保原子性。

3. **Platform 可配置**：Platform 存储在独立表 `benchmark_platform` 中，前端通过 API-06 获取下拉选项，后续扩展只需在数据库插入新记录。

4. **Formula 更新**：API-05 只更新 `lg_formula` 字段，不影响其他数据。保存空字符串（不是 null）。

5. **Detail 排序**：按 `created_at ASC` 排序（BR-18）。

6. **并发策略**：Last-write-wins（BR-24），不做乐观锁或版本检查。

---

## 三、前端设计（CIOaas-web）

### 3.1 路由配置

```typescript
// config/routes.ts — 在 BasicLayout 子路由中新增
{
  path: '/benchmark-entry',
  name: 'Benchmark Entry',
  component: './BenchmarkEntry',
  role: true,  // 需要角色校验
}
```

### 3.2 页面与组件结构

```
src/pages/BenchmarkEntry/
├── index.tsx                          // 页面入口
├── index.less                         // 页面样式
├── types.ts                           // TypeScript 类型定义
├── constants.ts                       // 常量（Data 枚举等）
├── components/
│   ├── BenchmarkTable.tsx             // 主表格组件
│   ├── BenchmarkTable.less
│   ├── MetricRow.tsx                  // Metric 父行（展开/折叠）
│   ├── DetailRow.tsx                  // 详情行（只读/编辑态）
│   ├── AddDetailRow.tsx               // 新增行
│   ├── YearPicker.tsx                 // 年份选择器组件
│   ├── YearPicker.less
│   └── FormulaInput.tsx               // LG Formula 防抖输入框
└── hooks/
    └── useBenchmarkData.ts            // 数据加载与操作 hook
```

### 3.3 状态管理

本页面使用**组件内 state + 自定义 hook**，不创建 DVA model（页面较独立，不需要全局状态共享）。

```typescript
// types.ts
interface BenchmarkCategory {
  categoryId: string;
  categoryName: string;
  sortOrder: number;
  metrics: BenchmarkMetric[];
}

interface BenchmarkMetric {
  metricId: string;
  metricName: string;
  lgFormula: string;
  sortOrder: number;
  detailCount: number;
  details: BenchmarkDetail[];
}

interface BenchmarkDetail {
  detailId: string;
  platform: string | null;
  edition: string | null;
  metricName: string | null;
  definition: string | null;
  fyPeriod: string | null;
  segment: string | null;
  p25: string | null;
  median: string | null;
  p75: string | null;
  dataType: string | null;
  bestGuess: string | null;
}

interface PlatformOption {
  platformId: string;
  name: string;
}

// 关键状态
interface BenchmarkPageState {
  categories: BenchmarkCategory[];       // 完整数据树
  platforms: PlatformOption[];            // Platform 下拉选项
  loading: boolean;                      // 页面加载状态
  expandedMetrics: Set<string>;          // 展开的 Metric ID 集合
  editingDetailId: string | null;        // 正在编辑的 Detail ID
  addingMetricId: string | null;         // 正在新增的 Metric ID
  isAdmin: boolean;                      // 是否系统管理员
}
```

### 3.4 自定义 Hook

```typescript
// hooks/useBenchmarkData.ts
function useBenchmarkData() {
  const [categories, setCategories] = useState<BenchmarkCategory[]>([]);
  const [platforms, setPlatforms] = useState<PlatformOption[]>([]);
  const [loading, setLoading] = useState(true);

  // 加载数据
  const loadData = async () => { ... };

  // Detail CRUD
  const addDetail = async (metricId: string, data: Partial<BenchmarkDetail>) => { ... };
  const updateDetail = async (detailId: string, data: Partial<BenchmarkDetail>) => { ... };
  const deleteDetail = async (detailId: string, metricId: string) => { ... };

  // Formula 更新
  const updateFormula = async (metricId: string, formula: string) => { ... };

  return { categories, platforms, loading, loadData, addDetail, updateDetail, deleteDetail, updateFormula };
}
```

### 3.5 API 调用层

```typescript
// src/services/api/benchmark/benchmarkService.ts
import request from '@/utils/request';

// 获取所有基准数据
export async function getBenchmarkMetrics() {
  return request('/api/web/benchmark/metrics', { method: 'GET' });
}

// 获取 Platform 列表
export async function getBenchmarkPlatforms() {
  return request('/api/web/benchmark/platforms', { method: 'GET' });
}

// 新增详情行
export async function addBenchmarkDetail(data: any) {
  return request('/api/web/benchmark/details', { method: 'POST', data });
}

// 编辑详情行
export async function updateBenchmarkDetail(detailId: string, data: any) {
  return request(`/api/web/benchmark/details/${detailId}`, { method: 'PUT', data });
}

// 删除详情行
export async function deleteBenchmarkDetail(detailId: string) {
  return request(`/api/web/benchmark/details/${detailId}`, { method: 'DELETE' });
}

// 更新 LG Formula
export async function updateBenchmarkFormula(metricId: string, data: { lgFormula: string }) {
  return request(`/api/web/benchmark/metrics/${metricId}/formula`, { method: 'PUT', data });
}
```

### 3.6 关键交互实现

#### 3.6.1 表格渲染策略

不使用 Ant Design `<Table>` 的标准 dataSource/columns 模式（因为需要 rowSpan、展开/折叠、内联编辑等高度定制化渲染），改为使用 **HTML `<table>` + Ant Design 基础组件** 手动渲染表格结构。

```
<table>
  <thead> 14列表头 </thead>
  <tbody>
    {categories.map(cat => (
      <>
        {cat.metrics.map((metric, metricIdx) => (
          <>
            {/* Metric 父行 */}
            <MetricRow
              metric={metric}
              category={metricIdx === 0 ? cat : null}  // 首个 metric 渲染 category 单元格
              categoryRowSpan={计算动态 rowSpan}
            />
            {/* 展开时：Detail 行 */}
            {expanded && metric.details.map(detail => (
              <DetailRow detail={detail} />
            ))}
            {/* 展开时：Add Detail 按钮行 */}
            {expanded && isAdmin && <AddDetailRow />}
          </>
        ))}
      </>
    ))}
  </tbody>
</table>
```

#### 3.6.2 Category rowSpan 动态计算

```typescript
function calcCategoryRowSpan(category: BenchmarkCategory, expandedMetrics: Set<string>): number {
  return category.metrics.reduce((sum, metric) => {
    let rows = 1; // metric 父行自身
    if (expandedMetrics.has(metric.metricId)) {
      rows += metric.details.length;  // 详情行数
      if (isAdmin) rows += 1;        // "Add detail" 按钮行
    }
    return sum + rows;
  }, 0);
}
```

#### 3.6.3 内联编辑状态机

```
只读态 ──→ [hover: 显示编辑/删除按钮]
  │
  ├── 点击 ✏️ ──→ 编辑态（字段变为输入控件）
  │                 ├── ✓ / Enter ──→ 调API → 成功：回到只读态 / 失败：保持编辑态
  │                 └── ✕ / Escape ──→ 丢弃修改，回到只读态
  │
  └── 点击 🗑️ ──→ 乐观删除（UI 先移除行） → 失败：恢复行显示
```

#### 3.6.4 LG Formula 防抖保存

```typescript
// FormulaInput.tsx
const debouncedSave = useMemo(
  () => debounce(async (metricId: string, value: string) => {
    try {
      await updateBenchmarkFormula(metricId, { lgFormula: value });
      // 静默成功（或轻量成功提示）
    } catch (e) {
      message.error('Failed to save formula');
    }
  }, 800),
  []
);

// 失焦时 flush 防抖
const handleBlur = () => {
  debouncedSave.flush();
};
```

#### 3.6.5 权限控制

```typescript
// 判断是否为系统管理员
const isAdmin = useMemo(() => {
  const userInfo = getUserInfo();
  return userInfo?.roleType === 2;  // roleType 2 = Admin/Staff
}, []);

// 控制 UI 元素显示
{isAdmin && <Button onClick={handleAdd}>+ Add detail</Button>}
{isAdmin && <FormulaInput editable />}
// 非管理员看到纯文本
{!isAdmin && <span>{formula || '—'}</span>}
```

#### 3.6.6 删除乐观更新 + 失败恢复

```typescript
const handleDelete = async (detailId: string, metricId: string) => {
  // 1. 乐观更新：先从 UI 移除
  const backup = { ...detail };
  removeDetailFromState(metricId, detailId);

  try {
    // 2. 调后端 API
    await deleteBenchmarkDetail(detailId);
  } catch (e) {
    // 3. 失败：恢复行
    restoreDetailToState(metricId, backup);
    message.error('Failed to delete');
  }
};
```

---

## 四、数据流

```
页面加载:
  useEffect → getBenchmarkMetrics() + getBenchmarkPlatforms()
    → 后端 BenchmarkController.getMetrics()
    → BenchmarkServiceImpl.getAllBenchmarkData()
    → Repository 查询 Category + Metric + Detail
    → 组装 DTO 树 → Result<List<BenchmarkCategoryDto>>
    → 前端 setCategories(data)

新增 Detail:
  用户填写 → 点击 ✓ → addBenchmarkDetail(data)
    → POST /web/benchmark/details
    → BenchmarkServiceImpl.addDetail()
    → Repository.save(entity)
    → 返回 BenchmarkDetailDto
    → 前端更新 categories state（将新 detail 插入对应 metric）

编辑 Detail:
  用户修改 → 点击 ✓ → updateBenchmarkDetail(id, data)
    → PUT /web/benchmark/details/{id}
    → BenchmarkServiceImpl.updateDetail()
    → Repository.save(updatedEntity)
    → 返回更新后的 BenchmarkDetailDto
    → 前端更新 categories state

删除 Detail:
  用户点击 🗑️ → 乐观移除行 → deleteBenchmarkDetail(id)
    → DELETE /web/benchmark/details/{id}
    → BenchmarkServiceImpl.deleteDetail()
    → Repository.deleteById(id)
    → 成功：无操作 / 失败：前端恢复行

更新 Formula:
  用户输入 → 防抖 800ms → updateBenchmarkFormula(metricId, formula)
    → PUT /web/benchmark/metrics/{id}/formula
    → BenchmarkServiceImpl.updateFormula()
    → 更新 metric.lgFormula 字段
    → 成功：静默 / 失败：Toast 错误
```

---

## 五、技术风险与决策

| # | 风险/决策 | 方案 | 理由 |
|---|----------|------|------|
| 1 | 表格渲染方案选择 | HTML table + Ant Design 组件（非 `<Table>` 组件） | 需要动态 rowSpan、多级展开折叠、内联编辑，Ant Design Table 的 expandable 和 column 模式难以满足 |
| 2 | 全量加载 vs 按需加载 | 全量加载一棵树 | 数据量可控（6 Metric × N Detail），暂不分页（BR-27） |
| 3 | 种子数据初始化 | ApplicationRunner + 幂等检查 | 确保每次部署后种子数据存在，已存在则跳过 |
| 4 | Platform 存储 | 独立表 benchmark_platform | 支持后续配置扩展（BR-25），不硬编码在代码中 |
| 5 | 状态管理选型 | 组件内 state + custom hook | 页面独立性强，不需要 DVA 全局 model |
| 6 | N+1 查询风险 | Service 层手动组装 DTO，使用 JOIN FETCH 或单独查询 + 内存组装 | 避免 JPA lazy loading 的 N+1 问题 |

---

## 六、工作量评估

| 模块 | 任务 | 复杂度 | 依赖 |
|------|------|--------|------|
| 后端 | 数据模型（4 Entity + DDL + 种子数据） | 中 | 无 |
| 后端 | DTO + Mapper | 低 | 数据模型 |
| 后端 | Service 层（CRUD + 树组装） | 中 | 数据模型, DTO |
| 后端 | Controller（6 API） | 低 | Service |
| 后端 | DataInitializer | 低 | 数据模型 |
| 前端 | 路由 + API Service | 低 | 后端 API |
| 前端 | 类型定义 + 常量 | 低 | 无 |
| 前端 | BenchmarkTable 主表格 | 高 | 类型定义 |
| 前端 | MetricRow + 展开折叠 | 中 | BenchmarkTable |
| 前端 | DetailRow（只读 + 编辑态） | 高 | BenchmarkTable |
| 前端 | AddDetailRow | 中 | BenchmarkTable |
| 前端 | YearPicker 组件 | 中 | 无 |
| 前端 | FormulaInput（防抖） | 低 | API Service |
| 前端 | 权限控制 | 低 | 无 |
| 前端 | 样式（Less） | 中 | 组件完成后 |
| 联调 | 前后端联调 + Bug 修复 | 中 | 前后端完成 |

---

## 七、实现顺序

```
Phase 1: 后端基础（Day 1）
├── 1.1 Entity 类（BenchmarkCategory, BenchmarkMetric, BenchmarkDetail, BenchmarkPlatform）
├── 1.2 Repository 接口
├── 1.3 DDL 脚本 + 种子数据
├── 1.4 BenchmarkDataInitializer
├── 1.5 DTO + Mapper
├── 1.6 Service 接口 + 实现
└── 1.7 Controller（6 个 API 端点）

Phase 2: 前端基础（Day 2）
├── 2.1 路由配置
├── 2.2 API Service 层
├── 2.3 类型定义 + 常量
├── 2.4 页面骨架 + 标题区
└── 2.5 useBenchmarkData hook

Phase 3: 前端表格（Day 3-4）
├── 3.1 BenchmarkTable 基础表格（表头 + 遍历渲染）
├── 3.2 MetricRow（展开/折叠 + 折叠计数）
├── 3.3 DetailRow 只读态
├── 3.4 DetailRow 编辑态
├── 3.5 AddDetailRow 新增行
├── 3.6 YearPicker 组件
├── 3.7 FormulaInput 防抖组件
└── 3.8 Category rowSpan 动态计算

Phase 4: 完善与联调（Day 5）
├── 4.1 权限控制
├── 4.2 Loading 状态
├── 4.3 错误处理（Toast）
├── 4.4 空状态展示
├── 4.5 样式完善
└── 4.6 前后端联调 + Bug 修复
```
