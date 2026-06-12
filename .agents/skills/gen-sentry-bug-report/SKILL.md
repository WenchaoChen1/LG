---
name: gen-sentry-bug-report
description: 基于 Sentry MCP 拉取指定 project + 时间区间的 unresolved issue，逐个定位代码位置、根因、修复方案，按统一格式生成 markdown 报告到 docs/sentry-bug-reports/。支持 prod / uat / test / dev 多环境 + 跨环境对比。触发词：sentry bug 报告、分析 sentry XXX 环境、看下 prod/uat/test 最近 N 天 issue、生成环境 bug 清单。
tags: [sentry, bug-report, monitoring, ops]
version: 1.0.0
author: Wenchao Chen
---

# 生成 Sentry Bug 报告

把 Sentry 上某个 project 一段时间的未修复 issue **逐条**翻译成"代码位置 + 根因 + 修复方案"清单，
输出到 `docs/sentry-bug-reports/{project}-{startDate}-to-{endDate}.md`。

最适合**周报 / 迭代回顾 / 上线前体检**等需要批量梳理 Sentry issue 的场景。

## 使用方式

自然语言触发（推荐）：
- "查 lg-uat-java 最近 7 天 issue 生成 bug 报告"
- "分析 prod/uat/test 三个环境这周的 sentry 错误"
- "看下 lg-prod-java 最近 30 天有哪些未修复 bug 并生成文档"

也支持显式调用：`/gen-sentry-bug-report <project-slug> <days>`

## 前置条件

1. **Sentry MCP 已注册并连接**：执行 `Codex mcp list` 应能看到 `sentry: ✓ Connected`。
   未配置时参考 [Sentry MCP 接入步骤](#附录a)。
2. **当前在 LG 项目根目录**（`D:/github-code/LG`）。

## 执行步骤

### Step 1 — 确认输入参数

需要明确：
- **project slug**（如 `lg-uat-java` / `lg-prod-java` / `lg-test-java`）
- **时间区间**（默认最近 7 天，用 `lastSeen:-{N}d` 查询）
- **org slug**（LG 项目固定为 `lookingglass-3t`，region `https://us.sentry.io`）

如用户只说"prod 环境"，默认推断为 `lg-prod-java`；如同时要 prod/uat/test，**为每个环境生成一份独立报告**。

### Step 2 — 拉取 issue 列表

并行调用：

```
mcp__sentry__list_issues(
  organizationSlug='lookingglass-3t',
  regionUrl='https://us.sentry.io',
  projectSlugOrId=<project-slug>,
  query='is:unresolved lastSeen:-{N}d',
  sort='freq',
  limit=100
)
```

记录每个 issue 的：`Issue ID` / 标题 / Events / Users / Culprit (class.method) / First/Last seen。

### Step 3 — 优先级分级（按 Events × Users 估算）

| 优先级 | 阈值 | 含义 |
|--------|------|------|
| 🔴 P0 | Events > 5000 或影响核心数据链 | 立即修，本周必修 |
| 🟡 P1 | Events 100-5000 或 NPE/数据丢失风险 | 本周内修 |
| 🟢 P2 | Events 10-100 或第三方 API/配置问题 | 下周修 |
| 🟤 P3 | Events < 10 或偶发网络抖动 | 观察 |

> 注意：Events 数大不一定代表严重——查 environment 标签，**`environment=dev` 多为开发者本地反复触发**，应在报告里标注并降权排序。

### Step 4 — 对 P0/P1 issue 拉完整 stack

并行调用：

```
mcp__sentry__get_sentry_resource(
  organizationSlug='lookingglass-3t',
  resourceType='issue',
  resourceId='<Issue ID>'
)
```

提取：精确行号 / 失败 SQL 值 / 调用链 / 关键变量值（如导致溢出的数字、null 对象的字段）。

### Step 5 — 代码 grep 定位行号

对每个 culprit 用 `grep -n` 在 LG 代码里找精确行号：

```bash
grep -rn "public.*<methodName>\|<className>\.java" \
  D:/github-code/LG/CIOaas-api/gstdev-cioaas-web/src/main/java | head
```

### Step 6 — 按模板写报告

模板见 [report-template.md](./report-template.md)。每个 issue 必含：

1. **原标题**（Sentry 报错原文）
2. **Sentry 链接**：`https://lookingglass-3t.sentry.io/issues/<Issue ID>`
3. **代码位置**：`文件:行号` + 方法名
4. **根因**：基于完整 stack 分析（不要靠猜）
5. **修改方案**：可直接 copy 的代码片段

聚合章节必含：
- 总览表（按 Events 排序，列：`#` / `Issue ID` / 简述 / Events / Users / 优先级）
- 详细分析（按 P0 → P1 → P2 → P3 分块）
- **修复方案速查表**（一行一个 issue，写 `文件:行` + 一句话修复）
- **推荐处理时间表**（按 Day 排，每行带预期消除事件数 + 累计百分比）
- **🎯 跨环境共性修复表**（如果同时生成了多个环境的报告）

### Step 7 — 文件命名 + 路径

```
docs/sentry-bug-reports/{project-slug-no-prefix}-{startDate}-to-{endDate}.md
```

例子：
- `docs/sentry-bug-reports/uat-java-2026-05-13-to-2026-05-20.md`
- `docs/sentry-bug-reports/prod-java-2026-05-13-to-2026-05-20.md`
- `docs/sentry-bug-reports/test-java-2026-05-13-to-2026-05-20.md`

> project-slug-no-prefix 是去掉 `lg-` 前缀（团队约定，简洁）。

### Step 8 — 提交（仅当用户明确要求）

```bash
git -C D:/github-code/LG add docs/sentry-bug-reports/<new-files>
git -C D:/github-code/LG commit -m "docs(sentry): 新增 <env> Java <date-range> Bug 清单"
git -C D:/github-code/LG pull --rebase --autostash
git -C D:/github-code/LG push
```

⚠️ **必须用显式文件路径 add**，不要 `git add .`（避免误带 AI-Chatbot / usage-reports 等其他人的未提交工作）。

## 规则

1. **根因必须基于 get_sentry_resource 拿到的真实 stack**，不要靠猜。
   - 如果某个 issue 没拉完整 stack，标注"根因（推断）"+"建议下一步"。
2. **跨环境同源 issue 必须互相引用**（用 markdown 相对链接）。
   - 不重复贴长代码，写 `详见 [UAT 报告 #X](./uat-...md)`。
3. **修改方案必须可执行**（具体到代码片段 + 文件:行），不要写"考虑加 null 检查"这种空话。
4. **时间表按 Day 排，每行带预期消除事件数 + 累计百分比**。
5. **共性发现单独列章节**，呈现"一次修复 N 个 issue"的杠杆点。
6. **environment=dev 的 issue 要降权**：可能是开发者本地反复触发，不代表真实流量。报告里明确标注。
7. **文档全部用中文**（除代码片段、Sentry 原标题）。
8. **commit message 用中文**（符合项目 AGENTS.md 规范）。
9. **不要提交 bootstrap.yml / AI-Chatbot 其他人的修改**——显式 add 报告文件。
10. **不要主动 pull/push 子项目仓库**（CIOaas-api/web/python）—— skill 只在 LG 根仓库工作。

## 输入参数推断规则

| 用户说 | 推断 |
|--------|------|
| "prod 环境" / "线上" | `lg-prod-java` |
| "uat" | `lg-uat-java` |
| "test" / "测试环境" | `lg-test-java` |
| "前端" + 环境 | `lg-{env}-react` |
| "python" + 环境 | `lg-{env}-python` |
| 没说时间 | 默认 7 天 |
| "最近 N 天" | `lastSeen:-Nd` |
| "三个环境" / "prod uat test" | 生成 3 份独立报告 + 一份跨环境对比 |

## 跨环境对比（多环境时）

当一次性分析 prod / uat / test 时，每份报告底部加一节：

```markdown
## 🎯 跨环境共性修复表

| 共性 issue | UAT | TEST | PROD | 一次修复影响 |
|-----------|-----|------|------|------------|
| 数值溢出 (safeRatio + clamp) | 2Y + 1S | Y + 1C | — | ~92800 events |
| ...
```

帮助决策"哪些是跨环境共性 bug，可以一次 PR 解决"。

## 验证

生成后检查：
1. `ls docs/sentry-bug-reports/` 看到新文件
2. 打开报告检查总览表行数 == Sentry 返回的 issue 数
3. P0/P1 都有"✅ 根因已确认"（拉过 stack）
4. 速查表覆盖全部 issue（行数对得上）
5. 时间表 Day 1/2/... 累计百分比合理

## 附录 A：Sentry MCP 接入步骤

如果 `Codex mcp list` 看不到 sentry：

```powershell
# 1. 去 sentry.io → Settings → User Auth Tokens → Create New
#    勾选 scope: org:read, project:read, project:write, team:read, event:write
# 2. 注册（Windows 必须 cmd /c npx 包装绕开 hook ENOENT）
Codex mcp add sentry -s user -- cmd /c npx -y '@sentry/mcp-server' --access-token=sntryu_<TOKEN>
```

Self-hosted Sentry 加 `--host=sentry.你公司域名.com`。

## 关联文件

- [report-template.md](./report-template.md) — 报告完整模板
- 历史报告：`docs/sentry-bug-reports/`
