# Benchmark Entry 自动化测试索引

> 创建时间：2026-03-24
> 功能：Benchmark Entry（行业基准指标管理）

---

## 后端测试（JUnit 5 + Mockito）

| 测试文件 | 路径 | 测试类数 | 测试方法数 | 覆盖范围 |
|---------|------|---------|-----------|---------|
| BenchmarkServiceTest.java | `CIOaas-api/gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/benchmark/BenchmarkServiceTest.java` | 7 (Nested) | 24 | Service 层完整业务逻辑 |
| BenchmarkControllerTest.java | `CIOaas-api/gstdev-cioaas-web/src/test/java/com/gstdev/cioaas/web/benchmark/BenchmarkControllerTest.java` | 1 | 4 | Controller 层接口测试 |

### BenchmarkServiceTest 详细覆盖

| 嵌套类 | 测试点 |
|-------|--------|
| GetListTests | 返回 4 Category / 6 Metric、Platform 选项、详情行分组、Category-Metric 映射 |
| BatchSaveAddTests | 单条新增（UUID + version=0）、多条新增 |
| BatchSaveUpdateTests | 乐观锁更新、版本冲突异常、ID 不存在异常、缺少 id/version 校验 |
| BatchSaveDeleteTests | 正常删除、不存在 ID 幂等跳过 |
| BatchSaveMixedTests | 新增 + 更新 + 删除混合操作 |
| BatchSaveValidationTests | 无效 metricKey/platform/dataType、全字段为空（BR-13）、null platform 允许 |
| BatchSaveUniquenessTests | added 内部重复、与 DB 冲突、不同 Metric 允许、空字段跳过、deleted 排除 |
| UpdateFormulaTests | 正常保存、无效 metricKey、版本冲突、清空 formula |

### BenchmarkControllerTest 详细覆盖

| 测试方法 | 测试点 |
|---------|--------|
| getList_success | GET /benchmark/list 正常响应 |
| batchSave_success | POST /benchmark/save 正常保存 |
| batchSave_emptyRequest | POST /benchmark/save 空请求体 |
| updateFormula_success | PUT /benchmark/formula 正常保存 |
| updateFormula_missingMetricKey | PUT /benchmark/formula 缺少 metricKey 校验 |

---

## 前端测试（Jest + Enzyme）

| 测试文件 | 路径 | 测试方法数 | 覆盖范围 |
|---------|------|-----------|---------|
| BenchmarkEntry.test.tsx | `CIOaas-web/src/pages/benchmarkEntry/__tests__/BenchmarkEntry.test.tsx` | 7 | 页面级集成测试 |
| BenchmarkTable.test.tsx | `CIOaas-web/src/pages/benchmarkEntry/__tests__/BenchmarkTable.test.tsx` | 10 | 表格组件测试 |
| YearPicker.test.tsx | `CIOaas-web/src/pages/benchmarkEntry/__tests__/YearPicker.test.tsx` | 9 | 年份选择器组件测试 |

### BenchmarkEntry.test.tsx 覆盖

- 页面标题和副标题渲染
- 加载状态 Spinner 显示
- API 调用 getBenchmarkList
- 6 个 Metric 名称展示
- 4 个 Category 名称展示
- API 失败错误提示
- Save 按钮存在

### BenchmarkTable.test.tsx 覆盖

- 4 个 Category 名称渲染
- 6 个 Metric 名称渲染
- 折叠时显示 item count
- 展开时显示详情行数据
- 展开时显示 Add detail 按钮
- 折叠时隐藏详情行
- Formula 占位文字
- 已有 Formula 值展示
- 表头列名渲染
- 空 Metric 不显示 0 item(s)

### YearPicker.test.tsx 覆盖

- 日历图标渲染
- 已选值显示
- 点击打开浮层
- 12 个年份格子
- 正确十年段范围
- 选择年份回调
- 选择后关闭浮层
- 下一十年段翻页
- 上一十年段翻页
- disabled 状态不打开

---

## 执行命令

```bash
# 后端测试
cd CIOaas-api
mvn test -pl gstdev-cioaas-web -Dtest="com.gstdev.cioaas.web.benchmark.*"

# 前端测试
cd CIOaas-web
npm test -- --testPathPattern="benchmarkEntry"
```

## 统计

| 类别 | 文件数 | 测试方法数 |
|------|--------|-----------|
| 后端 (JUnit) | 2 | 28 |
| 前端 (Jest) | 3 | 26 |
| **合计** | **5** | **54** |
