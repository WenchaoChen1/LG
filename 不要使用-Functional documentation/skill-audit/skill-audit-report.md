# Skill 体系全面审查报告

**审查范围**：11 个 dev/ skill + 10 个顶层 skill + 13 个 agent 定义
**审查日期**：2026-03-26

---

## 一、严重问题（会导致功能异常）

### 1.1 Agent frontmatter 中 skills 引用的是旧名称

移动文件到 `dev/` 后，`skills:` 字段仍指向旧名称（不带 `dev:` 前缀），Claude Code 会找不到对应 skill。

| Agent 文件 | 当前 frontmatter | 应改为 |
|-----------|-----------------|--------|
| `arch-designer.md` | `gen-dev-design-doc` | `dev:gen-design-doc` |
| `arch-reviewer.md` | `review-dev-design-doc` | `dev:review-design-doc` |
| `dev-reviewer.md` | `review-implementation` | `dev:review-implementation` |
| `qa-developer.md` | `gen-unit-test` | `dev:gen-unit-test` |
| `qa-executor.md` | `run-tests` | `dev:run-tests` |

> `dev-backend.md` 和 `dev-frontend.md` 已经手动修正过，无问题。

---

### 1.2 hotfix 报告输出路径错误

**文件**：`dev/hotfix.md`

sed 替换把 `features/<feature>/reviews/hotfix-` 错误替换成了 `features/<feature>/reviews/dev/hotfix-`（`/hotfix` 被替换为 `/dev/hotfix`，影响了路径中非命令引用的 `/hotfix` 子串）。

需确认并修复被错误替换的路径。

---

## 二、项目特有硬编码（用户级 skill 不应包含）

### 2.1 dev/ 目录下的 skill（6 处）

| 文件 | 硬编码内容 | 行为 |
|------|-----------|------|
| `run.md` | `CIOaas-api`、`CIOaas-python`、`CIOaas-web` | 技术栈检测描述 |
| `hotfix.md` | `CIOaas-api/`、`CIOaas-web/src/` | 代码搜索路径 |
| `run-tests.md` | `mvn test -pl gstdev-cioaas-web` | 测试执行命令 |
| `gen-unit-test.md` | `CIOaas-api/`、`CIOaas-web/src/pages/` | 测试文件路径 |
| `review-design-doc.md` | `"CIOaas-api 核心架构"` 和 `"模块结构"` | CLAUDE.md 章节名 |
| `review-implementation.md` | `/fi/`、`/di/`、`/etl/` 等业务域路径 | 代码定位策略 |

### 2.2 顶层 skill（4 处）

| 文件 | 硬编码内容 |
|------|-----------|
| `run-e2e-pipeline.md` | 报告模板中 `CIOaas-api/...`、`CIOaas-web/...` |
| `team-all.md` | 报告模板中 `CIOaas-api/...`、`CIOaas-web/...` |
| `team-code.md` | 角色描述 "Spring Boot 全栈实现"、"React + Ant Design Pro 实现" |
| `team-test.md` | 角色描述 "JUnit + Jest 自动化测试代码" |

### 2.3 Agent 定义（10 处）

| 问题 | 涉及文件 |
|------|---------|
| 硬编码 "CIOaaS 平台" | dev-reviewer、arch-designer、arch-reviewer、arch-questioner、pm-writer、pm-reviewer、pm-questioner、qa-designer、qa-developer、qa-executor（共 10 个） |
| 硬编码仓库路径 `CIOaas-api/`、`CIOaas-web/` | qa-developer.md 输出示例 |

---

## 三、设计问题

### 3.1 pm-questioner 和 arch-questioner 无 skills 引用

这两个 agent 的 frontmatter 中 `skills:` 为空，意味着它们无法通过 Skill tool 调用任何 slash command。如果这些 agent 的工作流需要调用技能，会失败。

### 3.2 设计文档章节号硬编码

多个 skill 硬编码了设计文档的章节号映射（第 2 章 = UI、第 4 章 = 接口、第 5 章 = 数据模型…）。如果 `/dev/gen-design-doc` 的模板章节顺序变化，所有下游 skill 都需要同步修改。

**涉及文件**：`run.md`、`backend-java.md`、`frontend.md`、`review-design-doc.md`、`review-implementation.md`、`gen-unit-test.md`

### 3.3 gen-unit-test 和 run-tests 的框架探测示例偏 Java/React

`gen-unit-test.md` 的代码示例只展示了 JUnit 5 + Mockito 和 Jest + RTL，没有 Python 测试（pytest）的探测和示例。如果用于 Python 项目，缺少引导。

---

## 四、一致性问题

### 4.1 "下一步"提示链不完整

| Skill 末尾提示 | 指向 | 状态 |
|---------------|------|------|
| `gen-requirement-doc` → `/review-requirement-doc` | 顶层 | ✅ 正确 |
| `review-requirement-doc` → `/dev/gen-design-doc` | dev/ | ✅ 已更新 |
| `dev/gen-design-doc` → `/dev/review-design-doc` 或 `/dev/run` | dev/ | ✅ 已更新 |
| `dev/run` → `/dev/review-implementation` | dev/ | ✅ 已更新 |
| `dev/review-implementation` → `/dev/gen-unit-test` | dev/ | ✅ 已更新 |
| `dev/gen-unit-test` → `/dev/run-tests` | dev/ | ✅ 已更新 |
| `dev/hotfix` → 无下一步 | — | ✅ 合理（独立流程） |

提示链本身已由 sed 批量更新，基本正确。

### 4.2 dev-backend agent 的 description 不再正确

当前 description 仍是通用的 "根据项目技术栈执行..."，但 body text 里之前提到的 "CIOaaS 平台" 已被清理。description 和 body 现在一致（都是通用的），这是正确的。但其他 agent（如 dev-reviewer）description 字段仍带 "CIOaaS"：

```
description: Dev Team 代码审查角色。对照设计文档审查 CIOaaS 后端和前端实现...
```

---

## 五、问题汇总

| 编号 | 严重度 | 类型 | 问题 | 涉及文件数 |
|------|--------|------|------|-----------|
| 1.1 | **严重** | 功能 | Agent frontmatter skills 指向旧名称 | 5 个 agent |
| 1.2 | **严重** | Bug | hotfix 路径被 sed 误替换 | 1 |
| 2.1 | 中 | 硬编码 | dev/ skill 中残留项目名称和路径 | 6 |
| 2.2 | 中 | 硬编码 | 顶层 skill 中残留项目名称 | 4 |
| 2.3 | 中 | 硬编码 | Agent 硬编码 "CIOaaS 平台" | 10 |
| 3.1 | 低 | 设计 | pm/arch-questioner 无 skills 引用 | 2 |
| 3.2 | 低 | 设计 | 设计文档章节号硬编码 | 6 |
| 3.3 | 低 | 设计 | gen-unit-test 缺少 Python 测试引导 | 1 |
| 4.2 | 低 | 一致性 | 部分 agent description 仍带项目名 | ~8 |

**严重问题 2 个**，中等问题 3 类（共 20 个文件），低级问题 4 类。
