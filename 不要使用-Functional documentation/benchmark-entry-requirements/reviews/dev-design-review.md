# Benchmark Entry Requirements — 设计审查报告

> 功能：benchmark-entry-requirements
> 文档路径：features/benchmark-entry-requirements/dev-design/dev-design-doc.md
> 审查时间：2026-03-23
> 审查者：arch-reviewer
> 是否有需求文档：是
> 整体评估结论：修改后开发
> 严重问题数：3

---

## 审查结论

- **整体评分：7.5/10**
- **严重问题：3 个**（必须修复后才能开发）
- **警告：5 个**（建议修复）
- **通过项：14 个**

---

## 需求覆盖矩阵

| 需求项 | 来源 | 设计覆盖情况 |
|--------|------|-------------|
| P0: 指标分类展示（4 Category / 6 Metric） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.1、§ 5、§ 6.2）|
| P0: 指标展开/折叠（多 Metric 独立展开） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.4、§ 6.5）|
| P0: 新增详情行（至少填一字段校验） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.4、§ 6.3）|
| P0: 编辑详情行（确认/取消，互斥逻辑） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.4、§ 3.3）|
| P0: 删除详情行（无二次确认） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.4）|
| P0: 保存数据（批量提交后端，事务） | requirement-doc § 3 | ✅ 已覆盖（设计 § 4.1 POST /benchmark/save）|
| P0: 页面加载从后端获取数据 | requirement-doc § 1.2 | ✅ 已覆盖（设计 § 4.1 GET /benchmark/list）|
| P1: LG Formula 编辑（失焦自动保存） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.4、§ 4.2 PUT /benchmark/formula）|
| P1: 年份选择器（浮层，3x4 网格，十年段翻页） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.2、§ 3.3）|
| P2: 货币转换开关（仅 UI 状态） | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.2、§ 3.2）|
| P2: 空状态提示 | requirement-doc § 3 | ✅ 已覆盖（设计 § 2.2、§ 2.5）|
| BR-14: Platform + FY Period 唯一性（前端+后端双重校验） | requirement-doc § 5.3 | ✅ 已覆盖（设计 § 6.3）|
| BR-15: 编辑互斥 | requirement-doc § 5.3 | ✅ 已覆盖（设计 § 3.3）|
| BR-17: 未保存变更离开页面保护 | requirement-doc § 5.3 | ✅ 已覆盖（设计 § 2.4、§ 3.3）|

**覆盖率：14/14（100%）**

---

## 严重问题（必须修复）

### 问题 1：接口路径不符合项目规范，缺少 `/api/web/` 前缀

- **位置**：设计文档第 4.1 章接口汇总
- **描述**：设计文档中三个接口路径分别为 `/benchmark/list`、`/benchmark/save`、`/benchmark/formula`。查阅现有前端代码（`src/services/api/companyFinance/financeService.ts`），所有接口调用均带 `/api/web/` 前缀，如 `/api/web/companyQuickbooks/findByCompanyId`、`/api/web/financialStatements`。后端 Controller 的 `@RequestMapping` 只定义业务路径（如 `/financialForecastHistory`），网关在转发时统一添加 `/api/web/` 前缀。设计文档中的接口路径缺少 `/api/web/` 前缀说明，将导致前端服务文件的 URL 写法与实际路由不一致。
- **修复建议**：在接口汇总和接口详情中，统一补充说明实际调用路径为 `/api/web/benchmark/list`、`/api/web/benchmark/save`、`/api/web/benchmark/formula`；后端 Controller `@RequestMapping` 保持 `/benchmark` 不变，前端服务文件中写完整路径。

---

### 问题 2：benchmark_detail.metric_id 外键关联字段类型与主键类型不一致

- **位置**：设计文档第 5.1 章 `benchmark_detail` 表定义
- **描述**：`benchmark_metric.id` 定义为 `VARCHAR(36)`（UUID 格式），而 `benchmark_detail.metric_id` 也定义为 `VARCHAR(36)`，并通过外键 `REFERENCES benchmark_metric(id)` 关联。两者类型相同，这一点本身没有问题。但设计文档第 4.2 章 `POST /benchmark/save` 接口的请求体中，`added[].metricId` 直接传入枚举字符串（如 `ARR_GROWTH_RATE`），而 `benchmark_detail.metric_id` 存储的是 UUID，两者并不对应。后端业务逻辑需要先根据枚举 key 查出 UUID 再插入，但文档中的校验逻辑（第 4.2 章步骤 2）直接写"校验 `metricId` 是否为有效枚举值"，没有说明如何将枚举值转为数据库 UUID 主键。如果开发者直接将 `metricId` 枚举字符串写入 `benchmark_detail.metric_id`，外键约束将失败，INSERT 会报错。
- **修复建议**：在第 4.2 章 `POST /benchmark/save` 的后端业务逻辑中，明确补充步骤：校验 `metricId` 枚举有效后，通过 `SELECT id FROM benchmark_metric WHERE metric_key = :metricId` 获取真实 UUID，再以该 UUID 写入 `benchmark_detail.metric_id`。同时在 `PUT /benchmark/formula` 中同样补充此转换说明。

---

### 问题 3：异常处理体系与项目现有规范不一致

- **位置**：设计文档第 7 章异常处理
- **描述**：设计文档异常返回格式使用 `Result.fail("400", "...")` 、`Result.fail("409", "...")`、`Result.fail("404", "...")` 等，code 字段写 HTTP 状态码字符串。然而查阅 `GlobalExceptionHandler` 实现，业务异常（`BadRequestException`、`ServiceException`）被捕获后调用 `Result.fail(ex.getMessage())` 返回，HTTP 状态码仍为 200，code 为默认 `null`（未填写具体 code）。项目现有 `Result.fail` 有两种形式：`fail(msg)` 和 `fail(code, msg)`，异常 code 与 HTTP 状态码分离。设计文档混淆了 HTTP 状态码与 `Result.code` 字段，并且将 409/404 这类非 200 状态码直接用作业务异常 code，与实际 `GlobalExceptionHandler` 对 `BadRequestException` 的处理方式（返回 HTTP 200 + Result.fail）不一致，开发时若按文档实现会产生歧义。另外，文档未说明使用 `BadRequestException` 还是 `ServiceException` 来抛出这些业务错误。
- **修复建议**：在第 7 章中明确异常抛出规范：业务校验失败（metricId 无效、platform 无效、全字段为空、Platform+FY Period 重复等）统一抛出 `BadRequestException(msg)`，由 `GlobalExceptionHandler` 捕获后返回 HTTP 200 + `Result.fail(msg)`，`Result.code` 字段可保持项目默认（null 或自定义业务码，不使用 HTTP 状态码字符串）。"更新行不存在"场景改用 `EntityNotFoundException` 或 `BadRequestException`。移除设计文档中 `Result.fail("409", ...)` 、`Result.fail("404", ...)` 等 HTTP 状态码作为 code 的写法，统一格式。

---

## 警告（建议修复）

### 警告 1：GET /benchmark/list 响应中 metricId 字段命名与前端 TypeScript 类型定义不一致

- **位置**：设计文档第 4.2 章 `GET /benchmark/list` 响应示例 vs 第 3.2 章 TypeScript 类型定义
- **描述**：响应 JSON 示例中 Metric 层级使用 `"metricId": "ARR_GROWTH_RATE"`，但该字段在数据库 `benchmark_metric` 表中对应列是 `metric_key`，不是主键 `id`。前端 `MetricData` 接口定义了 `metricId: string`，注释写"Metric 枚举标识"，即枚举 key 而非 UUID。这一字段语义含混——命名为 `metricId` 却存的是枚举 key 值，与项目中其他接口用 UUID 作为 `xxxId` 字段的习惯（如 `benchmark_detail.id` 为 UUID）不统一，容易引发误解。
- **修复建议**：将响应中的字段名由 `metricId` 改为 `metricKey`，前端 `MetricData` 接口对应字段也改为 `metricKey: string`，语义更准确。同理，`POST /benchmark/save` 中的 `added[].metricId` 改为 `metricKey`。

---

### 警告 2：保存接口缺少后端 Platform + FY Period 唯一性校验的完整逻辑描述

- **位置**：设计文档第 4.2 章 `POST /benchmark/save` 后端业务逻辑第 2 步
- **描述**：文档描述"需联合数据库现有数据一起校验（排除 `deleted` 中的 ID 和 `updated` 中被更新的行）"。但 `updated` 中的行在更新后可能改变 platform 或 fyPeriod 值，校验应基于更新后的值，而非仅排除这些 ID。文档未说明 `added` 中多条记录之间的相互唯一性校验（例如两条 added 记录有相同 metricId + platform + fyPeriod）。
- **修复建议**：补充说明：唯一性校验范围 = （数据库现有数据 - deleted 的 ID - updated 中原有的 ID）∪ updated 中更新后的数据 ∪ added 数据；且 added 内部也需要做互相检查。

---

### 警告 3：前端路由 path 大小写与项目现有路由风格不一致

- **位置**：设计文档第 3.1 章路由配置
- **描述**：设计文档定义路由 `path: '/benchmarkEntry'`（camelCase）。查阅 CLAUDE.md 和现有前端结构，`src/pages/` 目录下功能目录均为 camelCase（如 `companyFinance`、`portfolioCompanies`），路由 path 也采用 camelCase，因此 `/benchmarkEntry` 本身是一致的。但 `hideInMenu: true` 的说明缺少依据——这是一个相对重要的入口功能，需求中未明确说明该页面隐藏于侧边导航菜单。
- **修复建议**：明确说明 `hideInMenu: true` 的原因，若后续需要在侧边栏显示需改为 `hideInMenu: false` 并增加对应的 icon 和权限配置；若确认隐藏，补充说明页面的入口方式（如通过某个父菜单跳转）。

---

### 警告 4：前端 API 服务文件路径与服务目录现有分类风格有偏差

- **位置**：设计文档第 3.1 章 API 服务文件
- **描述**：设计文档将服务文件定义为 `src/services/api/benchmark/benchmarkService.ts`，新建了 `benchmark/` 子目录。查阅现有服务文件结构，`src/services/api/` 下按功能域分目录（`companyFinance/`、`setting/`、`peerGroup/` 等），该规划是一致的，但文档中写的导入路径为 `@/utils/request`，而实际代码（financeService.ts 第 1 行）中导入为 `import request from '@/utils/request'`，两者一致，无问题。值得注意的是文档在 § 8（开发注意事项第 8 条）提到使用"来自 `@/utils/request` 的 `request` 工具函数"，但未说明 TypeScript 接口类型应放在 service 文件中还是单独的 `types.ts` 文件——现有 service 文件中类型定义风格不统一。
- **修复建议**：补充说明 TypeScript 类型定义文件的存放位置，建议新建 `src/services/api/benchmark/types.ts` 统一管理接口 DTO 类型。

---

### 警告 5：database 表设计中 benchmark_detail.metric_id 存储 UUID 但接口传枚举 key 的不一致性未在数据模型章节体现

- **位置**：设计文档第 5.1 章 `benchmark_detail` 表注释
- **描述**：表注释写 `COMMENT ON COLUMN benchmark_detail.metric_id IS '关联 benchmark_metric 主键'`，但接口层（`POST /benchmark/save`、`GET /benchmark/list` 响应）对外暴露的是 `metricId: "ARR_GROWTH_RATE"`（枚举 key 字符串），而非 UUID。此设计无问题（外键存 UUID，接口用枚举 key，后端做转换），但数据模型章节未说明这层映射关系，开发者阅读时会困惑。
- **修复建议**：在第 5.1 章或第 8 章补充说明：接口层 `metricId` 字段传递的是 `metric_key`（枚举标识），后端服务层负责将其转换为 `benchmark_metric.id`（UUID）后再写入 `benchmark_detail.metric_id`。

---

## 通过项

- 需求覆盖度：全部 P0/P1/P2 功能点均有对应设计，覆盖率 100%
- 业务规则覆盖：BR-01 到 BR-19 全部在设计文档中有明确对应描述
- 接口 HTTP 方法：GET 用于查询，POST 用于批量写，PUT 用于单记录更新，语义正确
- 接口响应结构：三个接口均有完整 JSON 示例，字段有类型和说明
- 前后端字段名一致性（camelCase）：前端 TypeScript `DetailRowData` 与 `POST /benchmark/save` 请求体字段名完全匹配（`percentile25th`、`median`、`percentile75th`、`dataType`、`bestGuess`、`fyPeriod` 等）
- 枚举前后端对齐：Category、Metric、Platform、DataType 枚举在设计文档第 6.2 章有完整定义，前端下拉选项与后端枚举一致
- 数据库主键规范：两张表均使用 `VARCHAR(36)` UUID 主键，符合项目现有规范
- 数据库审计字段：`benchmark_metric` 和 `benchmark_detail` 均包含 `created_at`、`created_by`、`updated_at`、`updated_by`，与 `AbstractCustomEntity` 字段一致（Entity 继承该基类可自动填充）
- 索引设计：`benchmark_detail` 有 `metric_id` 单字段索引和 `(metric_id, platform, fy_period)` 复合索引，覆盖唯一性查询场景
- 外键约束：`benchmark_detail.metric_id` 设有外键约束并配置 `ON DELETE CASCADE`，级联删除合理
- 分层架构：第 8 章注意事项明确要求新建 `benchmark/controller/service/repository/domain/contract/mapper/enums/` 标准分层，符合 CLAUDE.md 规范
- 前端状态管理：使用页面级 `useState/useReducer`，不使用 dva 全局 model，理由充分（数据不跨页面共享）
- 事务一致性：`POST /benchmark/save` 明确要求 `@Transactional` 注解，批量操作原子性有保障
- 空态与加载态设计完整：第 2.5 章覆盖了页面加载、无数据、保存中、接口报错等所有状态场景

---

## 修复优先级

| 优先级 | 问题 | 预计影响 |
|--------|------|---------|
| P0 | 问题 2：metricId 枚举值与 benchmark_detail.metric_id UUID 的转换逻辑缺失 | 后端 INSERT 将触发外键约束失败，功能完全不可用 |
| P0 | 问题 3：异常处理体系（Result.fail code 字段写法）与项目现有 GlobalExceptionHandler 不一致 | 开发时产生歧义，可能导致返回格式与前端期望不符，前端错误处理逻辑失效 |
| P1 | 问题 1：接口路径缺少 `/api/web/` 前缀说明 | 前端服务文件 URL 写错导致联调失败（所有接口 404） |
| P1 | 警告 1：metricId 字段命名语义含混（枚举 key 命名为 id） | 后续维护混淆，与 UUID 主键命名冲突 |
| P2 | 警告 2：批量保存唯一性校验边界条件不完整 | 特定场景下后端校验漏洞，脏数据可能写入 |
| P2 | 警告 5：数据模型层未说明枚举 key 与 UUID 的映射 | 开发者理解困难，需要额外沟通 |
| P3 | 警告 3：路由 hideInMenu 缺少说明 | UI 入口问题，不影响功能正确性 |
| P3 | 警告 4：TypeScript 类型文件位置未说明 | 代码组织问题，不影响运行时行为 |

---

## 总结

**整体评估：修改后开发**

设计文档整体质量较高，需求覆盖完整（100%），前后端字段名对齐，数据库设计规范，业务规则描述细致。但存在 3 个必须修复后才能开发的问题：

**阻断开发的问题（共 3 个）**：
1. `POST /benchmark/save` 后端业务逻辑缺少将接口层 `metricId`（枚举 key）转换为数据库 `metric_id`（UUID）的步骤，否则外键约束报错导致功能不可用
2. 异常处理中 `Result.fail("409", ...)` / `Result.fail("404", ...)` 的写法与项目 `GlobalExceptionHandler` 实际处理方式不一致，需统一改为 `BadRequestException` / `EntityNotFoundException` 体系
3. 接口路径 `/benchmark/list`、`/benchmark/save`、`/benchmark/formula` 缺少 `/api/web/` 前缀说明，前端联调时所有接口将 404

**开发中可处理的问题（共 5 个）**：
1. `metricId` 字段命名建议改为 `metricKey` 语义更准确
2. 批量保存唯一性校验边界条件补充 added 内部互相检查
3. `hideInMenu: true` 补充说明入口方式
4. TypeScript 类型文件存放位置补充说明
5. 数据模型章节补充枚举 key 与 UUID 映射说明

---

如设计文档已按上述 3 个严重问题修复，运行 `/gen-user-test-doc benchmark-entry-requirements` 生成测试文档，再运行 `/run-dev-design-doc benchmark-entry-requirements` 开始开发。
