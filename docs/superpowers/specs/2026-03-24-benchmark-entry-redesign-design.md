# Benchmark Entry 全栈重新设计 — 设计规范

> 版本：v1.1 | 日期：2026-03-24

---

## 一、设计目标

基于原始 PRD 的功能需求，对 Benchmark Entry 功能进行全栈重新设计。功能范围不变（4 个分类、6 个指标、详情行 CRUD），技术栈不变（React + Ant Design Pro + UmiJS / Spring Boot + JPA + PostgreSQL），核心变化：

| 维度 | 现有方案 | 新方案 |
|------|----------|--------|
| 数据库 | 单表 + `is_formula_row` 混存公式和详情 | 单表纯存详情行，公式在枚举中 |
| 保存方式 | 批量攒变更 → 全局保存 | 每次操作即时保存 |
| 公式管理 | 数据库存储，前端可编辑 | 代码枚举管理，前端只读 |
| API 风格 | 3 个端点（list / batch-save / formula） | 4 个标准 RESTful 端点 |

### 设计决策偏离 PRD 说明

| PRD 功能 | 偏离内容 | 原因 |
|----------|---------|------|
| 场景 4：公式录入（PRD 4.5 节） | 公式改为代码枚举管理，前端只读展示，不支持用户编辑 | 公式为固定业务规则，几乎不会变动，无需用户运行时编辑。若未来需要可编辑，需新增 API 和数据库字段 |

### PRD 字段名 → 设计字段名映射

| PRD 字段名 | 数据库字段名 | DTO 字段名 | 说明 |
|-----------|-------------|-----------|------|
| year | fy_period | fyPeriod | 统一为财年周期语义 |
| p25 | percentile_25th | percentile25th | 使用完整语义命名 |
| p75 | percentile_75th | percentile75th | 使用完整语义命名 |
| guess | best_guess | bestGuess | 使用完整语义命名 |
| dataType | data_type | dataType | 一致 |
| lgFormula | — | formula（MetricKey 枚举属性） | 不入库 |
| lgCategory | — | category（Category 枚举） | 不入库 |
| lgMetricName | — | displayName（MetricKey 枚举属性） | 不入库 |

### 空值约定

- 前端不选择/不填写时，不传该字段或传 `null`
- 后端存储为 `NULL`（不存空字符串）
- 后端校验：空字符串 `""` 视同 `null`

---

## 二、数据库模型

### 单表：`benchmark_detail`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | UUID 主键 |
| metric_key | VARCHAR(50) | NOT NULL | 枚举值，见下方 MetricKey |
| platform | VARCHAR(20) | | 枚举值，见下方 Platform |
| edition | VARCHAR(255) | | 版本/期数 |
| metric_name | VARCHAR(255) | | 平台指标名 |
| definition | VARCHAR(500) | | 定义说明 |
| fy_period | VARCHAR(4) | | 年份，如 "2024" |
| segment | VARCHAR(255) | | 细分 |
| percentile_25th | VARCHAR(50) | | 25th 分位值 |
| median | VARCHAR(50) | | 中位数 |
| percentile_75th | VARCHAR(50) | | 75th 分位值 |
| data_type | VARCHAR(20) | | 枚举值，见下方 DataType |
| best_guess | VARCHAR(255) | | 综合判断 |
| version | INT | NOT NULL DEFAULT 0 | 乐观锁版本号 |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |
| created_by | VARCHAR(100) | | |
| updated_by | VARCHAR(100) | | |

**索引：**

- `idx_benchmark_detail_metric_key` ON (metric_key)
- `idx_benchmark_detail_metric_platform_fy` ON (metric_key, platform, fy_period)

**DDL：**

```sql
CREATE TABLE benchmark_detail (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_key      VARCHAR(50)     NOT NULL,
    platform        VARCHAR(20),
    edition         VARCHAR(255),
    metric_name     VARCHAR(255),
    definition      VARCHAR(500),
    fy_period       VARCHAR(4),
    segment         VARCHAR(255),
    percentile_25th VARCHAR(50),
    median          VARCHAR(50),
    percentile_75th VARCHAR(50),
    data_type       VARCHAR(20),
    best_guess      VARCHAR(255),
    version         INT             NOT NULL DEFAULT 0,
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    created_by      VARCHAR(100),
    updated_by      VARCHAR(100)
);

CREATE INDEX idx_benchmark_detail_metric_key ON benchmark_detail (metric_key);
CREATE INDEX idx_benchmark_detail_metric_platform_fy ON benchmark_detail (metric_key, platform, fy_period);
```

---

## 三、后端枚举定义

### Category（4 个分类）

| 枚举值 | displayName |
|--------|-------------|
| REVENUE_AND_GROWTH | Revenue & Growth |
| PROFITABILITY_AND_EFFICIENCY | Profitability & Efficiency |
| BURN_AND_RUNWAY | Burn & Runway |
| CAPITAL_EFFICIENCY | Capital Efficiency |

### MetricKey（6 个指标）

| 枚举值 | category | displayName | displayOrder | formula |
|--------|----------|-------------|-------------|---------|
| ARR_GROWTH_RATE | REVENUE_AND_GROWTH | ARR Growth Rate | 1 | (Current ARR - Previous ARR) / Previous ARR |
| GROSS_MARGIN | PROFITABILITY_AND_EFFICIENCY | Gross Margin | 2 | (Revenue - COGS) / Revenue |
| MONTHLY_NET_BURN_RATE | BURN_AND_RUNWAY | Monthly Net Burn Rate | 3 | |
| MONTHLY_RUNWAY | BURN_AND_RUNWAY | Monthly Runway | 4 | |
| RULE_OF_40 | CAPITAL_EFFICIENCY | Rule of 40 | 5 | |
| SALES_EFFICIENCY_RATIO | CAPITAL_EFFICIENCY | Sales Efficiency Ratio | 6 | |

### Platform（3 个平台）

| 枚举值 | displayName |
|--------|-------------|
| BENCHMARKIT_AI | Benchmarkit.ai |
| KEYBANC | KeyBanc |
| HIGH_ALPHA | High Alpha |

### DataType（2 个数据类型）

| 枚举值 | displayName |
|--------|-------------|
| ACTUAL | Actual |
| FORECAST | Forecast |

---

## 四、后端 API 设计

### 4.1 获取指标列表

**`GET /api/web/benchmark/metrics`**

响应：

```json
{
  "platformOptions": [
    {"key": "BENCHMARKIT_AI", "displayName": "Benchmarkit.ai"},
    {"key": "KEYBANC", "displayName": "KeyBanc"},
    {"key": "HIGH_ALPHA", "displayName": "High Alpha"}
  ],
  "dataTypeOptions": [
    {"key": "ACTUAL", "displayName": "Actual"},
    {"key": "FORECAST", "displayName": "Forecast"}
  ],
  "categories": [
    {
      "key": "REVENUE_AND_GROWTH",
      "displayName": "Revenue & Growth",
      "metrics": [
        {
          "key": "ARR_GROWTH_RATE",
          "displayName": "ARR Growth Rate",
          "formula": "(Current ARR - Previous ARR) / Previous ARR",
          "details": [
            {
              "id": "550e8400-e29b-41d4-a716-446655440000",
              "platform": "BENCHMARKIT_AI",
              "platformDisplayName": "Benchmarkit.ai",
              "edition": "Q3 2024 SaaS Benchmarks",
              "metricName": "",
              "definition": "",
              "fyPeriod": "2024",
              "segment": "",
              "percentile25th": "15%",
              "median": "25%",
              "percentile75th": "40%",
              "dataType": "ACTUAL",
              "dataTypeDisplayName": "Actual",
              "bestGuess": "",
              "version": 0
            }
          ]
        }
      ]
    }
  ]
}
```

### 4.2 新增详情行

**`POST /api/web/benchmark/details`**

请求：

```json
{
  "metricKey": "ARR_GROWTH_RATE",
  "platform": "BENCHMARKIT_AI",
  "edition": "Q3 2024 SaaS Benchmarks",
  "metricName": "",
  "definition": "",
  "fyPeriod": "2024",
  "segment": "",
  "percentile25th": "15%",
  "median": "25%",
  "percentile75th": "40%",
  "dataType": "ACTUAL",
  "bestGuess": ""
}
```

响应（201 Created）：返回 `BenchmarkDetailDto` 结构：

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "platform": "BENCHMARKIT_AI",
  "platformDisplayName": "Benchmarkit.ai",
  "edition": "Q3 2024 SaaS Benchmarks",
  "metricName": "",
  "definition": "",
  "fyPeriod": "2024",
  "segment": "",
  "percentile25th": "15%",
  "median": "25%",
  "percentile75th": "40%",
  "dataType": "ACTUAL",
  "dataTypeDisplayName": "Actual",
  "bestGuess": "",
  "version": 0
}
```

**校验规则：**

- `metricKey` 必填，必须是有效的 MetricKey 枚举值
- `platform` 若提供，必须是有效的 Platform 枚举值
- `dataType` 若提供，必须是有效的 DataType 枚举值
- 其余字段均可为空

### 4.3 编辑详情行

**`PUT /api/web/benchmark/details/{id}`**

请求：

```json
{
  "platform": "KEYBANC",
  "edition": "Updated Edition",
  "metricName": "",
  "definition": "",
  "fyPeriod": "2024",
  "segment": "",
  "percentile25th": "20%",
  "median": "30%",
  "percentile75th": "45%",
  "dataType": "ACTUAL",
  "bestGuess": "",
  "version": 0
}
```

响应（200 OK）：返回 `BenchmarkDetailDto` 结构（同 POST 响应，version 自增）。

**校验规则：**

- `version` 必填（乐观锁）
- `id` 必须存在
- 枚举字段校验同新增
- version 不匹配时返回 409 Conflict

### 4.4 删除详情行

**`DELETE /api/web/benchmark/details/{id}`**

响应：204 No Content

**规则：**

- `id` 必须存在，不存在返回 404
- 即时删除，无需确认
- 设计决策：删除不校验 version，因为删除操作的语义是"移除此行"，与行内容无关

---

## 五、后端分层结构

```
web/benchmark/
├── controller/
│   └── BenchmarkController.java       # 4 个端点
├── service/
│   ├── BenchmarkService.java          # 接口
│   └── BenchmarkServiceImpl.java      # 实现
├── repository/
│   └── BenchmarkDetailRepository.java # JPA Repository
├── domain/
│   └── BenchmarkDetail.java           # JPA Entity
├── contract/
│   ├── BenchmarkListResponse.java     # GET 响应
│   ├── CategoryDataDto.java           # 分类 DTO
│   ├── MetricDataDto.java             # 指标 DTO
│   ├── BenchmarkDetailDto.java        # 详情行 DTO
│   ├── BenchmarkDetailCreateRequest.java  # POST 请求
│   └── BenchmarkDetailUpdateRequest.java  # PUT 请求
├── mapper/
│   └── BenchmarkMapper.java           # Entity ↔ DTO 映射（MapStruct）
└── enums/
    ├── Category.java
    ├── MetricKey.java
    ├── Platform.java
    └── DataType.java
```

---

## 六、前端架构设计

### 6.1 目录结构

```
pages/benchmarkEntry/
├── index.tsx                    # 主页面：加载数据，管理全局状态
├── components/
│   ├── BenchmarkTable/
│   │   └── index.tsx            # 表格容器：rowSpan 计算、列定义
│   ├── MetricRow/
│   │   └── index.tsx            # 指标行：展开/折叠、公式显示、计数
│   ├── DetailRow/
│   │   └── index.tsx            # 详情行：只读展示、悬停操作按钮
│   ├── EditableRow/
│   │   └── index.tsx            # 编辑行：新增和编辑共用
│   ├── YearPicker/
│   │   └── index.tsx            # 年份选择器组件
│   └── EmptyState/
│       └── index.tsx            # 空状态提示
├── hooks/
│   └── useBenchmark.ts          # 数据获取与 CRUD 操作封装
└── types.ts                     # TypeScript 类型定义
```

### 6.2 核心 Hook：`useBenchmark`

```typescript
function useBenchmark() {
  // 状态
  const [categories, setCategories] = useState<CategoryData[]>([]);
  const [loading, setLoading] = useState(false);

  // 加载数据
  const loadData = async () => { /* GET /metrics */ };

  // CRUD — 每个操作直接调 API，成功后更新局部状态
  const addDetail = async (metricKey: string, data: Omit<CreateDetailRequest, 'metricKey'>) => {
    // 内部合并 metricKey 到请求体，POST /details → 成功后将返回的 detail 插入对应 metric 的 details 数组
  };

  const updateDetail = async (id: string, data: UpdateDetailRequest) => {
    // PUT /details/{id} → 成功后替换对应行数据
  };

  const deleteDetail = async (id: string, metricKey: string) => {
    // DELETE /details/{id} → 成功后从对应 metric 的 details 数组中移除
  };

  return { categories, loading, loadData, addDetail, updateDetail, deleteDetail };
}
```

### 6.3 组件交互设计

**MetricRow（指标行）：**

- 点击展开/折叠，箭头图标同步切换
- 折叠时显示 "{n} item(s)" 计数
- LG Formula 列只读展示（来自枚举）
- 多个 Metric 可同时展开

**DetailRow（只读详情行）：**

- 悬停时背景变色，行尾渐变显示 ✏️ 🗑️ 按钮
- 点击 ✏️ → 该行切换为 EditableRow（编辑模式）
- 点击 🗑️ → 直接调 DELETE API，即时移除

**EditableRow（新增/编辑共用）：**

- `mode: 'add' | 'edit'` 区分模式
- 新增模式：accent/30 高亮背景
- 编辑模式：加载已有值到表单控件
- 点击 ✓ 或 Enter → 调对应 API（POST 或 PUT），成功后退出编辑状态
- 点击 ✕ → 丢弃变更，退出编辑状态
- API 调用期间显示 loading 状态，防止重复提交

**更新策略：**

- 新增/编辑/删除：统一等 API 成功后再更新 UI
- 删除期间行显示 loading 状态（半透明），API 成功后移除
- API 失败时显示 message.error 提示，UI 状态不变

**编辑状态冲突规则：**

- 同一 Metric 下同时只允许一个行处于编辑/新增状态
- 进入新的编辑/新增状态前，自动取消当前未保存的操作

**列样式规则：**

- 25th / Median / 75th 列：右对齐，等宽字体（monospace）
- 其余列：左对齐，常规字体
- 列宽、边框、悬停效果等 UI 细节参考 PRD 5.2 和 5.3 节

### 6.4 API Service 层

```typescript
// services/api/benchmark/benchmarkService.ts

const BASE = '/api/web/benchmark';

export async function getMetrics(): Promise<BenchmarkListResponse> {
  return request(`${BASE}/metrics`, { method: 'GET' });
}

export async function createDetail(data: CreateDetailRequest): Promise<BenchmarkDetailDto> {
  return request(`${BASE}/details`, { method: 'POST', data });
}

export async function updateDetail(id: string, data: UpdateDetailRequest): Promise<BenchmarkDetailDto> {
  return request(`${BASE}/details/${id}`, { method: 'PUT', data });
}

export async function deleteDetail(id: string): Promise<void> {
  return request(`${BASE}/details/${id}`, { method: 'DELETE' });
}
```

### 6.5 TypeScript 类型定义

```typescript
// types.ts

interface CategoryData {
  key: string;
  displayName: string;
  metrics: MetricData[];
}

interface MetricData {
  key: string;
  displayName: string;
  formula: string;
  details: BenchmarkDetailDto[];
}

interface BenchmarkDetailDto {
  id: string;
  platform: string | null;
  platformDisplayName: string | null;
  edition: string | null;
  metricName: string | null;
  definition: string | null;
  fyPeriod: string | null;
  segment: string | null;
  percentile25th: string | null;
  median: string | null;
  percentile75th: string | null;
  dataType: string | null;
  dataTypeDisplayName: string | null;
  bestGuess: string | null;
  version: number;
}

interface CreateDetailRequest {
  metricKey: string;
  platform?: string;
  edition?: string;
  metricName?: string;
  definition?: string;
  fyPeriod?: string;
  segment?: string;
  percentile25th?: string;
  median?: string;
  percentile75th?: string;
  dataType?: string;
  bestGuess?: string;
}

interface UpdateDetailRequest {
  platform?: string;
  edition?: string;
  metricName?: string;
  definition?: string;
  fyPeriod?: string;
  segment?: string;
  percentile25th?: string;
  median?: string;
  percentile75th?: string;
  dataType?: string;
  bestGuess?: string;
  version: number;
}

interface EnumOption {
  key: string;
  displayName: string;
}

interface BenchmarkListResponse {
  platformOptions: EnumOption[];
  dataTypeOptions: EnumOption[];
  categories: CategoryData[];
}
```

---

## 七、错误处理

| 场景 | HTTP 状态码 | 前端处理 |
|------|------------|----------|
| 新增成功 | 201 Created | message.success 提示，插入新行 |
| 编辑成功 | 200 OK | 静默更新行数据 |
| 删除成功 | 204 No Content | 移除行 |
| 乐观锁冲突 | 409 Conflict | message.error 提示"数据已被修改，请刷新"，刷新该指标数据 |
| 记录不存在 | 404 Not Found | message.error 提示，刷新数据 |
| 参数校验失败 | 400 Bad Request | 显示后端返回的错误信息 |
| 服务器错误 | 500 | message.error 通用提示 |

---

## 八、与原始 PRD 的功能对照

| PRD 功能 | 本设计覆盖情况 |
|----------|---------------|
| 顶部导航栏（Logo、货币开关、用户头像） | 不在本次范围，沿用现有全局布局 |
| 页面标题区 | 覆盖，简化（去掉保存按钮） |
| 指标分类管理（4 个 Category + rowSpan） | 覆盖，枚举定义 + 前端 rowSpan 计算 |
| 指标管理（展开/折叠、计数） | 覆盖 |
| 公式编辑（PRD 场景 4、4.5 节） | **设计偏离**：公式固化到代码枚举，前端只读。原因：公式为固定业务规则，几乎不变 |
| 详情行新增 | 覆盖，即时保存 |
| 详情行编辑 | 覆盖，即时保存 + 乐观锁 |
| 详情行删除 | 覆盖，即时删除 |
| 年份选择器 | 覆盖，复用 YearPicker 组件 |
| 空状态 | 覆盖 |
| 货币转换开关 | 沿用现有实现（UI 状态） |
