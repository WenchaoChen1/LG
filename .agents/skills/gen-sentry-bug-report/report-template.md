# LG {ENV} Java 未修复 Bug 清单（{startDate} ~ {endDate}）

> **报告时间区间**：{startDate} ~ {endDate}（最近 {N} 天）
> **生成时间**：{today}
> **数据来源**：Sentry org `lookingglass-3t` / project `{project-slug}`
> **查询条件**：`is:unresolved lastSeen:-{N}d`
> **范围**：{X} 个未解决 Issue，累计 ~{Y} events
> **关联报告**：[UAT 同期报告](./uat-...) / [PROD 同期报告](./prod-...) / [TEST 同期报告](./test-...)

> ⚠️（可选）特殊提醒：如某 issue 的 environment 多为 dev / 数据有偏差，在此说明。

---

## 总览（按事件数排序）

| # | Issue ID | 错误简述 | Events | Users | 优先级 |
|---|----------|---------|--------|-------|--------|
| 1 | LG-{ENV}-JAVA-XX | ... | 12345 | N | P0 |
| 2 | ... | ... | ... | ... | ... |

---

# 详细分析与修复方案

## 🔴 P0 - 立即修

### N. LG-{ENV}-JAVA-XX — 简短描述（{events} events）✅ 根因已确认

- **原标题**: `<Sentry 原报错文本>`
- **Sentry 链接**: https://lookingglass-3t.sentry.io/issues/LG-{ENV}-JAVA-XX
- **代码位置**: `<相对路径>:<行号>` `<方法名>`
- **调用链**（若复杂）:
  - `Controller.java:X` `methodA`
  - `ServiceImpl.java:Y` `methodB`
  - 抛点：`Util.java:Z` `methodC`

**精确根因**（从 stack 拿到的具体值）：

```
<贴关键 SQL/异常值/null 引用上下文>
```

公司 / 时间 / 触发条件等关键 metadata。

**修改方案**：

```java
// 文件路径
// 关键修改（可直接 copy）
```

> 如有上游/下游联动：注明"配合 Issue YY 一起修，消除 N 个事件"。

### N+1. ...

## 🟡 P1 - 本周修

（同上格式）

## 🟢 P2 - 配置 / 环境

（精简版，每个 issue 2-3 行）

## 🟤 P3 - 偶发

（表格形式即可，不展开）

| Issue | 错误 | Events | 说明 |
|-------|------|--------|------|

---

## 📋 修复方案速查表（{X} 个 issue 一图全览）

### 🔴 P0

| Issue | 文件:行 | 一句话修复 |
|-------|---------|------------|
| **LG-{ENV}-JAVA-XX** | `path:line` | <fix 描述> |

### 🟡 P1
（同上）

### 🟢 P2
（同上）

### 🟤 P3
（一行汇总）

### 公共改造（一处修复消除多个 issue）

| 改动 | 影响 issue | 一句话 |
|------|-----------|--------|
| **新增 `Xxx` 工具类** | A + B + C | 统一处理 ... |

---

## 📅 推荐处理时间表

| 周次 | 处理项 | 预期消除事件数 | 累计 |
|------|--------|---------------|------|
| **本周 Day 1** | Issue A（一句话） | -X | x% |
| **本周 Day 2-3** | Issue B + C 联动修 | -Y | y% |
| **下周** | ... | ... | ... |

→ **本周可清掉 ~XX events（X%）**。

---

## 🎯 共性修复优先做（杠杆最高）

按"一次改动消除最多事件"排序：

1. **Issue A 防御**（N 行代码 → -X events）
2. **Issue B + C + D 共用工具**（一个 util → -Y events）
3. ...

⏱️ 上面 K 项**全部加起来约 N 行业务代码 + M 个 SQL migration**，能消除 **~Z events（Z%）**。

---

## 🎯 跨环境共性修复表（如果一次分析多环境）

| 共性 issue | UAT | TEST | PROD | 一次修复影响 |
|-----------|-----|------|------|------------|
| <模式 X> | UAT-XX | TEST-YY | PROD-ZZ | ~N events |

→ 建议作为**一次跨环境 PR** 提交。

---

## 🆕 {ENV} 独有 Issue（仅本环境出现，与共性 issue 分开）

（仅当存在环境特有 issue 时加此节）

| Issue | 分类 | 备注 |
|-------|------|------|

---

## 后续操作命令

| 想做的事 | 提示语 |
|---------|--------|
| 看某 issue 完整 stack | "看下 LG-{ENV}-JAVA-XX 完整 stack" |
| 看影响哪些公司 | "LG-{ENV}-JAVA-XX 影响的 companyId 列表" |
| Seer AI 分析 | "用 seer 分析 LG-{ENV}-JAVA-XX" |
| 跨环境对照 | "查 lg-{otherEnv}-java 同期 issue" |
| 标记 issue 已解决 | "把 LG-{ENV}-JAVA-XX 标 resolved" |
| 批量修复 | "按 {env} 报告速查表把 P0 全部修了" |

---

*文档生成于 {today}。修复前请二次拉 Sentry 数据确认 issue 还在（脏数据可能已被运营清理）。*
