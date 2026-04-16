# Claude Code Skill 使用指南

> 生成时间：2026-03-18
> 适用项目：D:\github-code\LG

---

## 概览

本项目共配置 **13 个 Skill**，分为用户级（全局可用）和项目级（仅本项目可用）。
所有 Skill 通过 `/skill名称` 调用，服务于「需求 → 设计 → 开发 → 测试」完整工作流。

---

## 一、完整工作流顺序

```
需求材料（Word / 文字描述 / 截图）
  ↓ /gen-requirement-doc     → features/<name>/requirement/requirement-doc.md
  ↓ /review-requirement-doc  → 需求审查报告（发现问题则修复后继续）
  ↓ /gen-dev-design-doc      → features/<name>/dev-design/dev-design-doc.md
  ↓ /review-dev-design-doc   → 设计审查报告（发现问题则修复后继续）
  ↓ /gen-user-test-doc       → features/<name>/user-test/user-test-doc.md
  ↓ /run-dev-design-doc      → 后端代码 + 前端代码（两阶段，中间暂停确认）
  ↓ /review-implementation   → 实现闭环 PASS/FAIL 报告
  ↓ /gen-unit-test           → 各代码仓库的测试代码文件
  ↓ /run-tests               → 测试执行报告
```

---

## 二、用户级 Skill（9 个）

> 存放位置：`C:\Users\WenchaoChen\.claude\commands\`
> 所有项目均可使用。

---

### `/gen-requirement-doc` — 生成产品需求文档

**用途**：将原始需求材料（Word 文档、文字描述、截图草稿等）整理为结构化的产品需求文档（PRD）。

**输入**：
- 需求文件路径（`.docx` / `.txt` / `.md`）
- 截图路径（可选，支持多张）
- 或直接在对话中粘贴需求描述

**输出**：`features/<功能名>/requirement/requirement-doc.md`

**文档包含**：
1. 功能概述（目的 / 范围 / 角色）
2. 使用场景
3. 功能清单（含优先级 P0/P1/P2）
4. 业务流程（主流程 + 分支）
5. 业务规则（筛选 / 状态流转 / 权限 / 边界条件）
6. 计算公式（含口径 / 精度 / 除零处理）
7. 数据展示逻辑
8. 页面层级说明（含 ASCII 布局图）
9. 待确认问题

**特性**：
- 发现逻辑不闭环时自动提问，等用户确认后再生成
- 生成后对页面设计做 UI 合理性检查，逐条征求确认

**调用示例**：
```
/gen-requirement-doc features/benchmark-entry/raw/需求草稿.docx screenshots/mockup.png
/gen-requirement-doc financial-dashboard
```

---

### `/review-requirement-doc` — 审查需求文档

**用途**：对已生成的需求文档做三维度审查，输出问题清单，判断是否可进入设计阶段。

**输入**：功能名称（自动定位 `features/<name>/requirement/requirement-doc.md`）

**输出**：控制台审查报告（不生成文件）

**审查维度**：
- **完整性**：9 个章节是否都有实质性内容（7 个核心章节打分）
- **逻辑闭环**：流程是否有终态、规则是否覆盖所有分支、公式是否完整
- **可测试性**：规则是否具体可验证，是否存在模糊表述

**报告内容**：
- 完整性评分（X/7）
- 严重问题（必须修复）/ 一般问题 / 建议优化
- 明确结论：是否可以进入设计阶段

**调用示例**：
```
/review-requirement-doc benchmark-entry
/review-requirement-doc financial-dashboard
```

---

### `/gen-dev-design-doc` — 生成功能设计文档

**用途**：根据需求文档和页面截图，生成面向 AI 开发的完整功能设计文档，前端和后端开发均可直接参考执行。

**输入**：
- 需求文档路径（或直接功能名称，自动读取）
- 截图路径（可选，多张）

**输出**：`features/<功能名>/dev-design/dev-design-doc.md`

**文档包含**：
1. 功能概述
2. UI 界面设计（ASCII 布局 / 组件清单 / 展示规则 / 交互行为 / 空态加载态）
3. 前端实现要点（路由 / 状态管理 / 关键实现说明）
4. 后端接口设计（接口汇总 + 每个接口详情）
5. 数据模型（表结构 / 关联关系）
6. 业务规则与计算公式
7. 异常处理
8. 开发注意事项

**特性**：
- 截图优先于文字描述，有截图时必须输出「截图分析存档」再生成文档
- 截图与需求冲突时以截图为准并注明差异

**调用示例**：
```
/gen-dev-design-doc benchmark-entry
/gen-dev-design-doc features/benchmark-entry/requirement/requirement-doc.md screenshots/list.png
```

---

### `/review-dev-design-doc` — 审查功能设计文档

**用途**：对照需求文档和设计文档，检查设计完整性、接口规范性、前后端字段一致性。

**输入**：功能名称（自动读取 `requirement/requirement-doc.md` 和 `dev-design/dev-design-doc.md`）

**输出**：控制台审查报告（不生成文件）

**审查维度**：
- **需求覆盖**：P0/P1 功能点、业务规则、计算公式、边界条件是否全覆盖
- **接口设计**：路径风格 / HTTP 方法 / 参数完整性 / 响应结构 / 业务逻辑说明
- **数据模型**：主键 / 字段类型 / 外键 / 审计字段 / 索引
- **前后端一致**：表格字段名、筛选参数、表单字段与接口字段是否逐一对应
- **UI 完整性**：空态 / 加载态 / 错误态是否设计

**调用示例**：
```
/review-dev-design-doc benchmark-entry
```

---

### `/gen-user-test-doc` — 生成手动测试文档

**用途**：根据需求文档和设计文档，生成供测试人员手动点击验证的测试文档。

**输入**：功能名称（自动读取 `requirement/requirement-doc.md` 和 `dev-design/dev-design-doc.md`）

**输出**：`features/<功能名>/user-test/user-test-doc.md`

**文档包含四部分**：
1. **功能测试步骤**：按 P0/P1 功能点逐步操作验证，含前置条件、操作步骤、预期结果、实际结果（留空）、通过复选框
2. **边界与异常场景**：数据边界 / 错误输入 / 权限访问 / 网络异常
3. **UI 交互验证**：对照设计文档第 2.4 章逐条验证，含数字格式 / 加载态 / 空态
4. **验收检查清单**：功能完整性 / 数据正确性 / 异常处理 / UI 规范 / 性能体验

> ⚠️ **工作流位置**：在开发（`/run-dev-design-doc`）之前生成，让开发阶段有明确验收标准。

**调用示例**：
```
/gen-user-test-doc benchmark-entry
```

---

### `/run-dev-design-doc` — 根据设计文档开发功能

**用途**：读取功能设计文档，完整实现后端 + 前端代码，两阶段执行，阶段间暂停等待用户确认。

**输入**：功能名称（自动读取 `dev-design/dev-design-doc.md` 和 `requirement/requirement-doc.md`）

**输出**：实际代码文件（Controller / Service / Repository / DTO / 前端页面 / API service / 路由注册等）

**执行规则**：
- **先读后写**：动笔前必须读至少 2 个同类现有文件作为模式参考
- **两阶段**：阶段一（后端）→ 输出文件清单 + 数据存档 → 等用户说"继续" → 阶段二（前端）
- **改动最小化**：不修改无关文件，不重构现有代码
- **遇到冲突**：停下来列出冲突点，询问用户决策，不擅自推翻现有架构

**阶段一（后端）顺序**：DDL → Entity → Repository → DTO → Mapper → Service → Controller → 自检

**阶段二（前端）顺序**：API Service → 页面组件 → 路由注册 → 自检

**调用示例**：
```
/run-dev-design-doc benchmark-entry
```

---

### `/review-implementation` — 审查功能实现闭环

**用途**：对照需求文档、设计文档、测试文档三份基准，逐项扫描实际代码，输出 PASS/FAIL 状态的检查清单。

**输入**：功能名称（自动读取三份文档 + 探索实际代码文件）

**输出**：控制台审查报告（不生成文件）

**检查维度**：
- **后端接口**：Controller 是否存在 / 路径一致性 / 响应字段完整性 / 参数校验 / 异常处理
- **前端文件**：页面文件 / 路由注册 / API service 函数 / TypeScript interface 字段名
- **交互行为**：设计文档第 2.4 章每条交互是否有对应实现
- **数据展示规则**：数字格式 / 颜色语义 / 空值处理
- **状态处理**：加载态 / 空态 / 错误态
- **异常处理**：每个异常场景的后端错误码和前端提示
- **测试文档验收**：功能测试预期结果 / 边界校验 / UI 验收标准

**调用示例**：
```
/review-implementation benchmark-entry
```

---

### `/gen-unit-test` — 生成自动化测试代码

**用途**：根据设计文档和需求文档，自动探测项目测试框架，生成后端单元测试、接口测试和前端组件测试代码，写入各代码仓库。

**输入**：功能名称（自动读取 `dev-design/dev-design-doc.md` 和 `requirement/requirement-doc.md`）

**输出**：测试代码文件（写入实际代码仓库）
- 后端：`CIOaas-api/.../test/java/.../XxxServiceTest.java`
- 前端：`CIOaas-web/src/pages/xxx/__tests__/index.test.tsx`

**自动探测框架**：
- 后端：读取 `pom.xml` → JUnit 5 + Mockito + Spring Boot Test
- 前端：读取 `package.json` → Jest + React Testing Library / Vitest / UmiJS Test

**后端测试覆盖**：
- Service 单元测试：正常流程 / 边界条件 / 异常场景 / 计算公式验证
- Controller 集成测试：HTTP 200 / 400 / 404 / 401-403

**前端测试覆盖**：
- 渲染测试 / 交互测试 / API 调用测试 / 空态测试 / 加载态测试

**调用示例**：
```
/gen-unit-test benchmark-entry
```

---

### `/run-tests` — 执行测试并报告

**用途**：在实际环境中运行后端和前端测试，汇总结果，对失败用例逐一分析根因并给出修复建议。

**输入**：功能名称（可选 `--backend-only` / `--frontend-only`）

**输出**：控制台测试报告（不生成文件）

**执行方式**：
- 后端：`mvn test -pl gstdev-cioaas-web -Dtest=XxxServiceTest,XxxControllerTest`
- 前端：`npm run test -- --testPathPattern="xxx" --watchAll=false`

**报告内容**：
- 每个测试用例的状态（PASSED / FAILED / SKIPPED）
- 失败用例的错误信息 + 根因分析 + 具体修复建议（含文件路径和代码行定位）
- 汇总统计 + 是否可以提测的结论

> ⚠️ 失败用例分析完一个立即输出一个，不等全部完成后再统一输出（防止上下文淡出）。

**调用示例**：
```
/run-tests benchmark-entry
/run-tests benchmark-entry --backend-only
/run-tests benchmark-entry --frontend-only
```

---

## 三、项目级 Skill（4 个）

> 存放位置：`D:\github-code\LG\.claude\commands\`
> 仅本项目可用，属于旧工作流兼容 Skill。

---

### `/parse-req` — 解析并补全需求文档

**用途**：读取任意格式原始需求文档（Word / txt / md），分析补全为含 11 章的完整需求规格文档。

**输出**：`features/<功能名>/req-spec.md`

**调用示例**：
```
/parse-req features/benchmark-entry/raw/需求草稿.docx
```

---

### `/req-to-skill` — 需求文件转开发 Skill

**用途**：将需求规格文档（`req-spec.md`）转换为可直接执行的开发 Skill 文件，存入项目级 `.claude/commands/`。

**输出**：`.claude/commands/<功能名>.md`

**生成的 Skill 文件包含**：需求摘要 / 开发范围（前端/后端/DB）/ 业务规则 / 执行步骤 / 验收标准 / 注意事项

**调用示例**：
```
/req-to-skill features/benchmark-entry/req-spec.md
```

---

### `/edit-skill` — 编辑开发 Skill

**用途**：列出 `.claude/commands/` 下所有由需求生成的开发 Skill，选择并修改其内容。修改后自动更新文件头部的「最后更新」日期。

**调用示例**：
```
/edit-skill
/edit-skill benchmark-entry
```

---

### `/run-skill` — 执行开发 Skill

**用途**：列出所有可用的需求开发 Skill，选择后主动执行其中定义的步骤（相当于手动触发开发流程）。

**调用示例**：
```
/run-skill
/run-skill benchmark-entry
```

---

## 四、输出文件结构总览

```
features/<功能名称>/
  requirement/
    requirement-doc.md       ← /gen-requirement-doc 生成
  dev-design/
    dev-design-doc.md        ← /gen-dev-design-doc 生成
  user-test/
    user-test-doc.md         ← /gen-user-test-doc 生成
  unit-test/                 ← /gen-unit-test 生成（写入代码仓库，非此目录）
  req-spec.md                ← /parse-req 生成（旧工作流）

.claude/commands/
  <功能名>.md                ← /req-to-skill 生成（旧工作流）
```

---

## 五、快速参考卡

| Skill | 输入 | 输出位置 | 阶段 |
|-------|------|---------|------|
| `/gen-requirement-doc` | 原始材料/描述 | `requirement/requirement-doc.md` | 需求 |
| `/review-requirement-doc` | 功能名 | 控制台报告 | 需求 |
| `/gen-dev-design-doc` | 功能名/截图 | `dev-design/dev-design-doc.md` | 设计 |
| `/review-dev-design-doc` | 功能名 | 控制台报告 | 设计 |
| `/gen-user-test-doc` | 功能名 | `user-test/user-test-doc.md` | 设计后/开发前 |
| `/run-dev-design-doc` | 功能名 | 代码文件（两阶段） | 开发 |
| `/review-implementation` | 功能名 | 控制台报告 | 开发后 |
| `/gen-unit-test` | 功能名 | 测试代码文件 | 测试 |
| `/run-tests` | 功能名 | 控制台报告 | 测试 |
| `/parse-req` | 原始文档 | `req-spec.md` | 旧工作流 |
| `/req-to-skill` | req-spec.md | `.claude/commands/<name>.md` | 旧工作流 |
| `/edit-skill` | Skill名 | 修改 commands 文件 | 旧工作流 |
| `/run-skill` | Skill名 | 执行开发步骤 | 旧工作流 |
