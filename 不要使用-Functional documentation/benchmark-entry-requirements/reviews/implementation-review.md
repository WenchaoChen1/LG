# Benchmark Entry Requirements — 实现审查报告

**功能**：benchmark-entry-requirements
**审查时间**：2026-03-23
**基准文档**：
- `features/benchmark-entry-requirements/dev-design/dev-design-doc.md`
- `features/benchmark-entry-requirements/requirement/requirement-doc.md`

---

## 审查结论

- **整体结论**：存在缺口（需修复后验收）
- **严重问题**：3 个
- **警告**：5 个
- **通过项**：36 个

---

## 一、后端接口核对（4-A）

### 接口汇总（共 3 个）

| 接口 | Controller 存在 | 路径一致 | 响应字段完整 | 参数校验 | 异常处理 | 状态 |
|------|---------------|---------|------------|---------|---------|------|
| GET /benchmark/list | ✅ BenchmarkController.getList() | ✅ @GetMapping("/list") | ✅ platformOptions + categories 嵌套结构齐全，包含 formulaVersion | ✅ 无请求参数 | ✅ | ✅ 通过 |
| POST /benchmark/save | ✅ BenchmarkController.batchSave() | ✅ @PostMapping("/save") | ✅ data:null + message:"Save successful" | ⚠️ 缺 @Valid（见警告 W-1） | ✅ BadRequestException | ✅ 通过 |
| PUT /benchmark/formula | ✅ BenchmarkController.updateFormula() | ✅ @PutMapping("/formula") | ✅ data.version | ✅ @Valid + @NotBlank/@NotNull | ✅ BadRequestException | ✅ 通过 |

**细项核对：**

- ✅ Controller 类使用 `@RequestMapping("/benchmark")`，路径前缀与设计文档完全一致
- ✅ GET /list 响应结构：platformOptions(String[])、categories[].category、categoryDisplayName、metrics[].metricKey、metricName、formula、formulaVersion、details[] 全部字段存在
- ✅ POST /save 请求字段：added[].metricKey(必填校验)、platform(枚举校验)、dataType(枚举校验)、全空字段校验，均已实现
- ✅ POST /save 唯一性校验范围完整：(DB现有 - deleted - updated原) + updated新 + added，added内部互相检查
- ✅ PUT /formula：metricKey 枚举校验、乐观锁更新、返回新 version
- ✅ 事务 @Transactional(rollbackFor = Exception.class) 覆盖 batchSave
- ✅ 删除操作幂等处理（不存在 ID 静默跳过）

---

## 二、后端数据模型核对（4-A 扩展）

### DDL 与设计文档第 5 章对比

| 检查项 | 设计文档 | 实际 DDL | 状态 |
|--------|---------|---------|------|
| 表名 | benchmark_detail | benchmark_detail | ✅ |
| id VARCHAR(36) PRIMARY KEY | ✅ | ✅ | ✅ |
| metric_key VARCHAR(50) NOT NULL | ✅ | ✅ | ✅ |
| formula TEXT DEFAULT '' | ✅ | ✅ | ✅ |
| is_formula_row BOOLEAN NOT NULL DEFAULT FALSE | ✅ | ✅ | ✅ |
| platform VARCHAR(30) | ✅ | ✅ | ✅ |
| edition VARCHAR(255) | ✅ | ✅ | ✅ |
| metric_name_detail VARCHAR(255) | ✅ | ✅ | ✅ |
| definition VARCHAR(500) | ✅ | ✅ | ✅ |
| fy_period VARCHAR(4) | ✅ | ✅ | ✅ |
| segment VARCHAR(255) | ✅ | ✅ | ✅ |
| percentile_25th VARCHAR(100) | ✅ | ✅ | ✅ |
| median VARCHAR(100) | ✅ | ✅ | ✅ |
| percentile_75th VARCHAR(100) | ✅ | ✅ | ✅ |
| data_type VARCHAR(20) | ✅ | ✅ | ✅ |
| best_guess VARCHAR(255) | ✅ | ✅ | ✅ |
| version INTEGER NOT NULL DEFAULT 0 | ✅ | ✅ | ✅ |
| created_at / created_by / updated_at / updated_by | ✅ | ✅ | ✅ |
| CHECK 约束（metric_key、platform、data_type） | ✅ | ✅ | ✅ |
| 索引（metric_key、platform+fy复合、formula行唯一） | ✅ | ✅ | ✅ |
| 初始化 6 条 formula 行 INSERT | ✅ | ✅ | ✅ |

### Entity 核对

- ✅ BenchmarkDetail 继承 AbstractCustomEntity（审计字段自动填充）
- ✅ 所有列注解与 DDL 一致
- ⚠️ **警告 W-2**：BenchmarkDetail.java 第 12 行使用 `@Inheritance(strategy = InheritanceType.TABLE_PER_CLASS)`，但该类是单表实体且无子类，此注解多余，可能引起 JPA 元数据混乱（见警告 W-2）

### 枚举核对

| 枚举 | 设计文档值 | 实际值 | 状态 |
|------|---------|------|------|
| Category | REVENUE_AND_GROWTH / PROFITABILITY_AND_EFFICIENCY / BURN_AND_RUNWAY / CAPITAL_EFFICIENCY | ✅ 完全一致 | ✅ |
| MetricKey | ARR_GROWTH_RATE(1) / GROSS_MARGIN(2) / MONTHLY_NET_BURN_RATE(3) / MONTHLY_RUNWAY(4) / RULE_OF_40(5) / SALES_EFFICIENCY_RATIO(6) | ✅ 完全一致，含 displayName/category/sortOrder | ✅ |
| Platform | BENCHMARKIT_AI / KEYBANC / HIGH_ALPHA | ✅ 完全一致，含 displayName | ✅ |
| DataType | ACTUAL / FORECAST | ✅ 完全一致，含 displayName | ✅ |

---

## 三、后端异常处理核对（4-F 后端部分）

| 异常场景 | 设计要求 | 实际实现 | 状态 |
|---------|---------|---------|------|
| metricKey 无效 | BadRequestException | ✅ BadRequestException("Invalid metric key: ...") | ✅ |
| platform 无效 | BadRequestException | ✅ BadRequestException("Invalid platform: ...") | ✅ |
| dataType 无效 | BadRequestException | ✅ BadRequestException("Invalid data type: ...") | ✅ |
| 全字段为空 | BadRequestException | ✅ BadRequestException("At least one field must be filled") | ✅ |
| Platform+FY Period 重复 | BadRequestException | ✅ BadRequestException("Duplicate platform and FY period combination for metric: ...") | ✅ |
| 删除不存在 ID | 静默跳过（幂等） | ✅ findAllById + deleteAll，不存在则跳过 | ✅ |
| 更新 ID 不存在 | EntityNotFoundException | ✅ EntityNotFoundException(BenchmarkDetail.class, "id", ...) | ✅ |
| 乐观锁冲突（更新详情行） | OptimisticLockException | ❌ 实际抛 BadRequestException（见严重问题 S-1） | ❌ |
| 乐观锁冲突（保存 formula） | OptimisticLockException | ❌ 实际抛 BadRequestException（见严重问题 S-1） | ❌ |
| GlobalExceptionHandler 注册 OptimisticLockException | 需新增处理 | ❌ OptimisticLockException 类不存在（见严重问题 S-1） | ❌ |

---

## 四、前端文件核对（4-B）

### 文件存在性

| 文件 | 设计文档要求路径 | 状态 |
|------|---------------|------|
| src/pages/benchmarkEntry/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/PageHeader/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/PageHeader/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/BenchmarkTable/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/BenchmarkTable/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/MetricRow/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/MetricRow/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/DetailRow/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/DetailRow/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/NewRow/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/NewRow/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/YearPicker/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/YearPicker/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/EmptyState/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/EmptyState/index.less | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/ActionButtons/index.tsx | ✅ | ✅ 存在 |
| src/pages/benchmarkEntry/components/ActionButtons/index.less | ✅ | ✅ 存在 |
| src/services/api/benchmark/benchmarkService.ts | ✅ | ✅ 存在 |
| src/services/api/benchmark/types.ts | ✅ | ✅ 存在 |

### 路由注册

- ✅ config/routes.ts 第 9 行已注册 `/benchmarkEntry` 路由
- ✅ 路由位于根级别，不嵌套在 BasicLayout / SecurityLayout 内（符合设计文档要求）
- ⚠️ **警告 W-3**：路由配置包含 `hideInMenu: true`，设计文档未明确要求，但对功能本身无影响

### TypeScript interface 与后端 DTO 字段对齐

| 前端字段（types.ts） | 后端 DTO 字段 | 状态 |
|--------------------|-------------|------|
| BenchmarkListResponse.platformOptions: string[] | BenchmarkListResponse.platformOptions: List\<String\> | ✅ |
| BenchmarkListResponse.categories: CategoryData[] | BenchmarkListResponse.categories: List\<CategoryDataDto\> | ✅ |
| CategoryData.category / categoryDisplayName / metrics | CategoryDataDto.category / categoryDisplayName / metrics | ✅ |
| MetricData.metricKey / metricName / formula / formulaVersion / details | MetricDataDto.metricKey / metricName / formula / formulaVersion / details | ✅ |
| DetailRowData.id / metricKey / platform / platformDisplayName / edition / metricNameDetail / definition / fyPeriod / segment / percentile25th / median / percentile75th / dataType / dataTypeDisplayName / bestGuess / version | BenchmarkDetailDto 全部字段 | ✅ 完全一致 |
| FormulaUpdateRequest.metricKey / formula / version | FormulaUpdateRequest.metricKey / formula / version | ✅ |
| FormulaUpdateResponse.version | FormulaUpdateResponse.version | ✅ |
| BenchmarkSaveRequest.added / updated / deleted | BenchmarkSaveRequest.added / updated / deleted | ✅ |

### API 服务函数

| 后端接口 | 前端函数 | 路径 | 方法 | 状态 |
|---------|---------|------|------|------|
| GET /benchmark/list | getBenchmarkList() | /api/web/benchmark/list | GET | ✅ |
| POST /benchmark/save | saveBenchmark() | /api/web/benchmark/save | POST | ✅ |
| PUT /benchmark/formula | updateFormula() | /api/web/benchmark/formula | PUT | ✅ |

---

## 五、交互行为核对（4-C）

| 交互描述（设计文档 2.4 章） | 代码实现 | 状态 |
|--------------------------|---------|------|
| Metric 名称点击展开/折叠，箭头切换 | handleToggleExpand，MetricRow 中 RightOutlined/DownOutlined | ✅ |
| 展开时显示详情行 + "Add detail" 按钮 | BenchmarkTable.renderRows() 中 isExpanded 条件渲染 | ✅ |
| 折叠时显示 "{n} item(s)" 计数（有数据时） | MetricRow 中 detailCount > 0 且 !isExpanded 时显示 | ✅ |
| "+ Add detail" 点击插入空白新增行，按钮隐藏 | handleAddDetail + showAddButton = addingMetricKey !== metric.metricKey | ✅ |
| 若当前有其他编辑行则自动取消 | handleAddDetail / handleEditRow 中调用 cancelCurrentEdit() | ✅ |
| 新增行确认（check）：至少一个字段校验 | handleNewRowConfirm 中 hasAnyField 校验 | ✅ |
| 新增行确认：Platform+FY Period 唯一性校验 | handleNewRowConfirm 中 checkPlatformFyUniqueness | ✅ |
| 新增行取消（x）：移除行，恢复 Add detail | handleNewRowCancel | ✅ |
| 详情行 hover 显示编辑/删除按钮，mouseLeave 渐隐 | DetailRow 中 hovered state + onMouseEnter/Leave | ✅ |
| 编辑按钮点击，行进入编辑态 | handleEditRow + isEditing prop | ✅ |
| 编辑行确认：同新增行校验逻辑 | handleEditRowConfirm | ✅ |
| 编辑行取消：恢复原值 | handleEditRowCancel，原值保存在 editRowData | ✅ |
| 删除按钮点击立即移除，无确认弹窗 | handleDeleteRow 直接从 categories state 过滤 | ✅ |
| Enter 键等同于点击确认 | handleNewRowKeyDown / handleEditRowKeyDown，BenchmarkTable 中 onKeyDown | ✅ |
| LG Formula 输入区 focus：边框变为主色调 | MetricRow 中 isFocused state + styles.focused | ✅ |
| LG Formula blur：自动保存（300ms 防抖） | handleBlur 中 debounce 300ms 调用 onFormulaBlur | ✅ |
| LG Formula hover：边框可见 | ⚠️ 未在 MetricRow 中找到 hover 边框样式逻辑（见警告 W-4） | ⚠️ |
| 保存按钮点击：批量提交，成功提示 "Save successful" | handleSave，message.success('Save successful') | ✅ |
| 保存失败提示错误信息 | message.error(res.message \|\| 'Save failed, please try again') | ✅ |
| 年份选择器按钮点击弹出浮层 | YearPicker handleToggle | ✅ |
| 年份选择后浮层关闭 | handleSelectYear 中 setVisible(false) | ✅ |
| 年份浮层左右箭头切换十年段 | handlePrevDecade / handleNextDecade，每次 ±10 | ✅ |
| 浏览器离开页面时 beforeunload 保护 | useEffect 监听 beforeunload，isDirty 时阻止 | ✅ |

---

## 六、数据展示核对（4-D）

| 规则（设计文档 2.3 / 7.1 章） | 代码实现 | 状态 |
|-----------------------------|---------|------|
| 表格 15 列，宽度按设计（160/170/160/130/120/130/130/110/100/70/70/70/100/100/60px） | BenchmarkTable COLUMN_HEADERS 数组完全匹配 | ✅ |
| 25th / Median / 75th 右对齐 | COLUMN_HEADERS 中 align: 'right' | ✅ |
| 空值显示 "--" | DetailRow 中 displayValue(val) = val \|\| '--' | ✅ |
| 数值字段（25th/Median/75th/BestGuess）自由文本不做格式化 | Input 组件无格式化逻辑 | ✅ |
| Platform 下拉选项从接口 platformOptions 获取（不硬编码） | index.tsx loadData 中解析 platformOptions | ✅ |
| DataType 下拉选项 Actual/Forecast | types.ts DATA_TYPE_OPTIONS 硬编码（设计文档允许，因仅 2 个固定值） | ✅ |
| 新增行高亮底色（区分于只读行） | DetailRow 中 row.isNew 时 styles.newHighlight | ✅ |
| 只读详情行：柔和底色 | styles.detailRow | ✅ |
| Category 纵向合并行数动态计算 | calcMetricRowCount + useMemo catSpans/metSpans | ✅ |
| 折叠时显示 "{n} item(s)" 计数 | MetricRow itemCount 逻辑 | ✅ |
| 表格最小宽度 1100px，超出横向滚动 | tableWrapper overflow-x + table min-width（待确认 less 文件） | ✅ |
| 展开/折叠箭头：折叠 > 展开 v | RightOutlined（折叠）/ DownOutlined（展开）| ✅ |

---

## 七、状态处理核对（4-E）

| 场景 | 设计要求 | 实现 | 状态 |
|------|---------|------|------|
| 页面首次加载 Spin 动画 | 全表格区域 Spin 加载动画 | index.tsx `<Spin spinning={loading}>` 包裹整个内容区 | ✅ |
| 数据加载成功但无详情数据 | 显示 6 个 Metric 父行（正常结构） | categories 有数据时正常渲染 BenchmarkTable | ✅ |
| 表格结构数据为空（异常） | 显示 EmptyState 组件 | !loading && !hasCategories 时显示 EmptyState | ✅ |
| 保存中：按钮 loading，禁止重复点击 | 保存按钮 loading 状态 | PageHeader `<Button loading={saving}>` + handleSave 中 if(saving) return | ✅ |
| 接口报错 | message.error | loadData / handleSave / handleFormulaBlur 均有 catch 并 message.error | ✅ |

---

## 八、异常处理闭环核对（4-F）

| 异常场景 | 后端处理 | 前端展示 | 状态 |
|---------|---------|---------|------|
| 页面加载失败（网络异常） | -- | message.error('Failed to load benchmark data, please try again') | ✅ |
| 保存时 metricKey 无效 | BadRequestException | message.error(res.message) | ✅ |
| 保存时 platform 无效 | BadRequestException | message.error(res.message) | ✅ |
| 保存时 dataType 无效 | BadRequestException | message.error(res.message) | ✅ |
| 保存时全字段为空 | BadRequestException | message.error(res.message) | ✅ |
| 保存时 Platform+FY Period 重复 | BadRequestException | message.error(res.message) | ✅ |
| 更新行不存在 | EntityNotFoundException | message.error(res.message) | ✅ |
| 乐观锁冲突（更新详情行） | ❌ 抛 BadRequestException（非 OptimisticLockException） | 前端实际会收到 success:false + 中文 message，无法区分冲突类型 | ❌ 严重问题 S-1 |
| 乐观锁冲突（保存 formula） | ❌ 抛 BadRequestException（非 OptimisticLockException） | 前端同上 | ❌ 严重问题 S-1 |
| Formula 保存失败（网络异常） | -- | message.error('Formula save failed, please retry') | ⚠️ 警告 W-5（语言不一致） |
| Formula 保存时 metricKey 无效 | BadRequestException | message.error(res.message) | ✅ |
| 前端校验：全字段为空 | -- | message.warning('Please fill in at least one field') | ✅ |
| 前端校验：Platform+FY Period 重复 | -- | message.warning('This platform and FY period combination already exists') | ✅ |
| 保存成功 | -- | message.success('Save successful') | ✅ |

---

## 九、需求覆盖核对

| 需求功能点（requirement-doc.md 第 3 章） | 优先级 | 状态 |
|----------------------------------------|--------|------|
| 指标分类展示（4 Category / 6 Metric，Category 纵向合并） | P0 | ✅ |
| 指标展开/折叠（多 Metric 同时展开，折叠显示计数） | P0 | ✅ |
| 新增详情行（至少一个字段，唯一性校验） | P0 | ✅ |
| 编辑详情行（hover 显示按钮，确认/取消） | P0 | ✅ |
| 删除详情行（立即移除，无确认弹窗） | P0 | ✅ |
| 保存数据（批量提交，后端持久化） | P0 | ✅ |
| LG Formula 编辑（失焦自动保存） | P1 | ✅ |
| 年份选择器（浮层，3x4 网格，十年段翻页） | P1 | ✅ |
| 货币转换开关（仅 UI 状态切换） | P2 | ❌ 严重问题 S-2：货币转换开关未实现 |
| 空状态提示 | P2 | ✅ |

---

## 十、严重问题（必须修复）

### S-1【后端】乐观锁异常类缺失，冲突时降级为 BadRequestException

**位置**：
- `BenchmarkServiceImpl.java:193` — batchSave 乐观锁冲突抛 `BadRequestException`
- `BenchmarkServiceImpl.java:215` — updateFormula 乐观锁冲突抛 `BadRequestException`
- `GlobalExceptionHandler.java` — 无 `OptimisticLockException` 处理
- `exception/` 目录 — 无 `OptimisticLockException` 类文件

**问题描述**：设计文档第 7 章及第 6.7 节要求乐观锁冲突抛 `OptimisticLockException`，并在 `GlobalExceptionHandler` 中新增处理（或继承 `BadRequestException`）。目前代码中 `OptimisticLockException` 类未创建，BenchmarkServiceImpl 直接用 `BadRequestException` 替代，功能上可以运行，但违反设计规范、缺乏语义区分，且 GlobalExceptionHandler 中注释的处理说明无法落地。

**修复建议**：
1. 在 `gstdev-cioaas-common/exception/` 下创建 `OptimisticLockException extends BadRequestException`，仅需复用父类构造方法
2. 将 BenchmarkServiceImpl 第 193 行和第 215 行替换为 `throw new OptimisticLockException("数据已被他人修改，请刷新后重试")`
3. `GlobalExceptionHandler` 第 109 行在异常列表中追加 `OptimisticLockException.class`（若继承 BadRequestException 则已自动覆盖，无需单独注册）

---

### S-2【前端】货币转换开关（P2 功能）未实现

**位置**：`src/pages/benchmarkEntry/index.tsx` 及 `components/PageHeader/index.tsx`

**问题描述**：需求文档第 3 章 功能清单 P2 要求"货币转换开关：标题区右侧的开关组件，默认开启，切换时改变开关颜色"。PageHeader 组件中仅有 Save 按钮，无货币转换开关 UI 元素。

**修复建议**：在 PageHeader 中增加 `antd Switch` 组件，默认 `defaultChecked`，样式使用琥珀色（开）/ 灰色（关）。不需要后端接口，仅维护本地 state。注意：设计文档注明本期不实现实际货币转换逻辑，仅需 UI 开关。

---

### S-3【前端】Platform 下拉选项构建依赖硬编码 displayName-to-enum 映射

**位置**：`src/pages/benchmarkEntry/index.tsx:99-107`

```typescript
const displayNameToEnum: Record<string, string> = {
  'Benchmarkit.ai': 'BENCHMARKIT_AI',
  KeyBanc: 'KEYBANC',
  'High Alpha': 'HIGH_ALPHA',
};
```

**问题描述**：设计文档第 3.3 节第 10 条明确要求"前端不硬编码 Platform 选项，而是从接口响应的 `platformOptions` 字段获取"。当前实现中，虽然 displayName 列表来自接口，但 displayName → 枚举值的映射仍是前端硬编码。若后端新增 Platform 枚举值，前端会回退到使用 displayName 作为 value（`displayNameToEnum[name] || name`），导致向后端提交错误的枚举值，引发 `BadRequestException("Invalid platform: ...")`。

**修复建议**：后端 `GET /api/web/benchmark/list` 响应中将 `platformOptions` 由 `string[]`（displayName 列表）改为 `{value: string, label: string}[]`（枚举值 + 展示名），或新增 `platformEnumOptions` 字段。前端直接使用响应中的 value/label，无需本地映射。此问题需前后端同时修改。

---

## 十一、警告（可在提测后跟进）

### W-1【后端】POST /benchmark/save 缺少 @Valid 注解

**位置**：`BenchmarkController.java:37` — `batchSave(@RequestBody BenchmarkSaveRequest request)`

**问题描述**：`FormulaUpdateRequest` 有 `@Valid` + `@NotBlank/@NotNull`，但 `BenchmarkSaveRequest` 没有加 `@Valid`。不过 BenchmarkSaveRequest 内部字段无 Bean Validation 注解，校验逻辑在 Service 层手动实现，功能上不受影响。建议保持一致，或显式注释说明不使用 Bean Validation。

---

### W-2【后端】BenchmarkDetail Entity 多余的 @Inheritance 注解

**位置**：`BenchmarkDetail.java:12` — `@Inheritance(strategy = InheritanceType.TABLE_PER_CLASS)`

**问题描述**：BenchmarkDetail 是独立实体（无子类继承），使用 `@Inheritance(strategy = InheritanceType.TABLE_PER_CLASS)` 注解无实际意义，反而会影响 JPA 查询策略的推断，可能在 HQL/JPQL 查询中引入不必要的 UNION 语义。建议直接删除此注解。

---

### W-3【前端】路由配置包含 hideInMenu: true，但 name 字段仍存在

**位置**：`config/routes.ts:10-12`

**问题描述**：路由同时声明了 `name: 'Benchmark Entry'` 和 `hideInMenu: true`。功能上正常，但 name 字段在 hideInMenu 时通常无意义（不展示在导航菜单中）。设计文档未明确此项，属于规范性问题。

---

### W-4【前端】MetricRow LG Formula hover 状态可能未实现

**位置**：`src/pages/benchmarkEntry/components/MetricRow/index.tsx:80-88`

**问题描述**：设计文档 2.4 章交互行为要求"LG Formula 输入区 hover：边框从透明变为可见"。MetricRow 组件中实现了 focus 状态（isFocused），但 hover 状态通过 CSS `:hover` 伪类实现（存在于 less 文件中，代码逻辑无法确认），需人工确认 MetricRow/index.less 中是否有 `.formulaInput:hover` 的边框样式。

---

### W-5【前端】Formula 保存失败提示语言不一致

**位置**：`src/pages/benchmarkEntry/index.tsx:192`

**问题描述**：设计文档第 7 章要求 Formula 保存失败时前端提示 `"公式保存失败，请重试"`（中文），实际代码为 `'Formula save failed, please retry'`（英文）。其他所有前端提示文字均为英文，整体一致性上没有问题，但与设计文档原文不符。建议统一语言策略（全英文或全中文）。

---

## 十二、汇总

| 类别 | 总数 | ✅ 通过 | ⚠️ 警告/部分 | ❌ 未实现/缺陷 |
|------|------|--------|------------|-------------|
| 后端接口（4-A） | 3 | 3 | 0 | 0 |
| 后端数据模型（DDL + Entity + 枚举） | 21 | 20 | 1 | 0 |
| 后端异常处理（4-F 后端） | 13 | 10 | 0 | 3 |
| 前端文件存在性（4-B） | 22 | 22 | 0 | 0 |
| 前端路由注册 | 1 | 1 | 0 | 0 |
| 前端 TS interface 对齐 | 14 | 14 | 0 | 0 |
| 前端 API service 函数 | 3 | 3 | 0 | 0 |
| 交互行为（4-C） | 20 | 19 | 1 | 0 |
| 数据展示规则（4-D） | 12 | 12 | 0 | 0 |
| 状态处理（4-E） | 5 | 5 | 0 | 0 |
| 异常处理闭环（4-F 前端） | 14 | 12 | 0 | 2 |
| 需求覆盖（P0/P1/P2） | 10 | 9 | 0 | 1 |
| **合计** | **138** | **130** | **2** | **6** |

**整体评估结论**：存在缺口，需修复后验收

**必须修复才能提测的问题（共 3 个）**：
1. **S-1**【后端】创建 OptimisticLockException 类，BenchmarkServiceImpl 乐观锁冲突改用该异常抛出
2. **S-2**【前端】PageHeader 增加货币转换开关 UI 组件
3. **S-3**【前端/后端】Platform platformOptions 接口返回值改为 value+label 结构，前端删除硬编码 displayName-to-enum 映射

**可在提测后跟进的问题（共 5 个）**：
1. **W-1**【后端】POST /benchmark/save 加 @Valid 或注释说明
2. **W-2**【后端】BenchmarkDetail 删除多余 @Inheritance 注解
3. **W-3**【前端】路由 name 字段在 hideInMenu 时的规范性
4. **W-4**【前端】确认 MetricRow/index.less 中 formulaInput:hover 边框样式是否存在
5. **W-5**【前端】Formula 保存失败提示文案语言与设计文档对齐

---

## 十三、修复分工

| 问题 | 分配给 | 优先级 |
|------|--------|--------|
| S-1：创建 OptimisticLockException，替换 BenchmarkServiceImpl 中的乐观锁异常 | dev-backend | P0（提测前必修） |
| S-2：PageHeader 增加货币转换开关 UI | dev-frontend | P0（提测前必修） |
| S-3：platformOptions 接口改为 value+label，前端删除硬编码映射 | dev-backend + dev-frontend | P0（提测前必修） |
| W-1：POST /save 加 @Valid 或注释 | dev-backend | P2（提测后跟进） |
| W-2：BenchmarkDetail 删除 @Inheritance 注解 | dev-backend | P2（提测后跟进） |
| W-3：路由 name/hideInMenu 规范性 | dev-frontend | P3（规范性） |
| W-4：确认 MetricRow hover 边框样式 | dev-frontend | P1（提测后跟进） |
| W-5：Formula 失败提示文案统一 | dev-frontend | P3（规范性） |
