> 关联文档: [chatManage 排序/QA/分析设计](./2026-07-10-chat-manage-sort-qa-analytics-design.md)、[devSupport 目录查询接口设计](./2026-07-03-devsupport-directory-options-design.md)

# devSupport 筛选栏与页头一致性 — 设计文档

**日期**: 2026-07-10
**范围**: CIOaas-web 纯前端；devSupport 下 AI/数据类页面（llm 全部 / tracing / rag / chat 三个管理页）
**一句话**: 把「每个筛选字段带大写标签」与「页面标题 + `N match current filters` 描述」两处重复样式收敛成 2 个共享组件（`FilterField` / `PageHeader`），铺到范围内所有页面，消除各页各写导致的不一致；顺带把 tracing 的组织下拉移到公司前。

---

## 1. 背景与目标

用户在 test 环境巡检发现 devSupport 各页筛选栏风格不统一：只有 `llm/CallList`（Call Logs）一页做到了「标题 + 描述副标题 + 每个筛选字段上方带大写标签（COMPANY / USER / TIME RANGE）」，其余页面要么缺字段标签、要么缺描述、要么标题嵌在筛选条里。用户要求 devSupport 下所有筛选栏统一采用 Call Logs 那套范式，并把 chat 页的端类型筛选逻辑「同步」到其它页面。

**调研结论（决定范围的关键事实）**：
- **端类型（client_type）数据只有 chatbot 会话表有**（company=App / admin）。LLM 调用日志（`ref_company_id`/`ref_user_id`）、tracing（company/organization）、rag（space/归属人）**都没有 client_type 维度**——因此不能给这些页面加「客户端」下拉（会是查不出正确结果的假筛选）。
- 全 devSupport 唯一符合目标范式的是 `llm/CallList.tsx` + `llm/components/FilterToolbar.tsx`，作为推广模板。
- 平台管理 6 页（indicator / connectorsManagement / menuManagement / portfolioGroupManagement / rolesManagement / benchmarkEntry）**大多没有页级筛选栏**，字段标签无从谈起，纳入仅剩标题排版统一、价值低、风险高。

**目标**：
1. 抽出共享 `FilterField`（标签+控件）与 `PageHeader`（标题+描述+操作槽），作为标签/页头的**单一来源**；
2. 范围内页面全部消费这两个组件，达成视觉一致并杜绝再漂移；
3. 端类型三逻辑（App/Admin 标签、组织在公司前、选 App 禁用组织）已在 chat 三页落地，本次对 chat 三页只补字段标签；
4. 组织排公司前推广到 tracing（唯一另有公司+组织的页面）。

**非目标（YAGNI / 已与用户确认）**：
- 不给 llm/rag/tracing 添加「客户端」下拉（无数据支撑）；
- 不改平台管理 6 页；
- 不引入 antd `Form`/`FormItem`（沿用现有 div+span 的轻量标签范式，与模板一致）；
- 不改任何后端接口、不改筛选的查询语义（纯展示层重构）。

---

## 2. 范式来源（模板实现）

**页头**（`llm/CallList.tsx:117-123`）：
```jsx
<div className={styles.titleBar}><h1 className={styles.title}>Call Logs</h1></div>
<div className={styles.subTitle}>Cross-task LLM call logs · {total} calls match current filters</div>
```
**字段标签**（`llm/components/FilterToolbar.tsx:117-124`，非 FormItem，是 div+span）：
```jsx
<div className={styles.filterItem}>
  <span className={styles.filterLabel}>Company</span>
  <CompanySelect .../>
</div>
```
关键样式在 `llm/index.less`：`.filterItem`（flex column, gap 6）+ `.filterLabel`（12px/700/navy `#0D2B56`/`letter-spacing:0.5px`/`text-transform:uppercase`）+ `.subTitle`（13px/`@c-muted`）+ `.titleBar`/`.title`。色板 token 来自 `_shared/tokens.less`（rag 已共享同一 less，跨域推广无色板漂移）。

---

## 3. 共享组件设计

### 3.1 `_shared/FilterField/`（index.tsx + index.less）

单个筛选项的「标签 + 控件」包装。

```tsx
interface FilterFieldProps {
  label: string;                 // 展示为大写（CSS text-transform，调用方传原文如 "Company"）
  children: React.ReactNode;     // 任意控件（DirectorySelect / antd Select / Input / RangePicker / Switch）
  className?: string;            // 透传到外层，便于个别页微调宽度
}
```
渲染：`<div class={field}><span class={label}>{label}</span>{children}</div>`。
`index.less` 内 `.field`（flex column, gap 6）+ `.label`（12px/700/navy/uppercase/letter-spacing 0.5，样式逐字取自模板），`@import '../tokens.less'` 取色板。

**契约**：组件不管控件宽度（宽度由 children 自身 `style`/`className` 决定，沿用各页现状）；不带业务逻辑，纯布局。

### 3.2 `_shared/PageHeader/`（index.tsx + index.less）

统一页头：标题 + 描述 + 右侧操作槽。

```tsx
interface PageHeaderProps {
  title: string;
  description?: React.ReactNode;  // 缺省不渲染 subTitle 行
  extra?: React.ReactNode;        // 右侧操作区（Refresh 按钮 / 时区 Tag 等）
}
```
渲染：
```jsx
<div class={titleBar}>
  <h1 class={title}>{title}</h1>
  {extra && <div class={actions}>{extra}</div>}
</div>
{description && <div class={subTitle}>{description}</div>}
```
描述文案由调用方拼装，统一格式 `{一句话上下文} · {N} {名词} match current filters`（`N` 用 `total.toLocaleString()`）。

**样式归属决策**：`.filterItem`/`.filterLabel`/`.titleBar`/`.title`/`.subTitle` 目前散在 `llm/index.less`（仅 llm 用）。收敛后**权威样式落在两个共享组件各自的 `.less`**；llm/index.less 里被 FilterToolbar/CallList 直接引用的这些类，改为消费共享组件后按「无其它消费者才删」处理——保留 `.filterToolbar`（容器，见 §5）等仍在用的类，删除已无引用的 `.filterItem`/`.filterLabel`（由 FilterField 接管）。

---

## 4. 逐页应用矩阵

| 页面 | 字段标签 | 描述 | 其它 |
|---|---|---|---|
| `llm/components/FilterToolbar.tsx`（CallList） | 15 个字段的 `filterItem`+`filterLabel` → 换成 `FilterField` | 已有（CallList 页头改走 `PageHeader`） | 模板迁移到共享源 |
| `llm/components/AnalyticsFilterBar.tsx`（Dashboard + Cost/Performance/Tokens/Errors/Providers 共 6 页共用） | ✅ 各字段包 `FilterField`（**改一处覆盖 6 页**） | ✅ 6 个页面各补 `PageHeader` 描述 | 最大杠杆点 |
| `llm/Dashboard.tsx` | （筛选走 AnalyticsFilterBar） | ✅ 标题从筛选条内移出，改 `PageHeader` + 描述 | |
| `llm/Cost/Performance/Tokens/Errors/Providers.tsx` | （同上共用） | ✅ 各补 `PageHeader` 描述 | |
| `tracing/TraceList/index.tsx` | ✅ company/org/source/status/time/name/taskId 各包 `FilterField` | 已有 → 改走 `PageHeader` | **组织移到公司前**（§6） |
| `chatManage/index.tsx` | ✅ 各筛选包 `FilterField` | 已有 → 改走 `PageHeader` | 端类型三逻辑已完成 |
| `chatMessages/index.tsx` | ✅（含级联的普通 Select 与关键字/时间） | 已有 → 改走 `PageHeader` | 同上 |
| `chatAnalytics/index.tsx` | ✅ 各筛选包 `FilterField` | ✅ 标题从筛选条内移出，改 `PageHeader` + 描述 | |
| `rag/index.tsx`（Spaces） | ✅ keyword 搜索框包 `FilterField`（"Search"） | 已有 → 改走 `PageHeader` | |
| `rag/stats/index.tsx` | ✅ space 选择器包 `FilterField` | 已有 → 改走 `PageHeader` | |
| `rag/connections/index.tsx` | ✅ backend 选择器包 `FilterField` | 已有 → 改走 `PageHeader` | |
| `rag/search/index.tsx`（Recall） | ✅ RecallPanel 内各控件包 `FilterField` | 已有 → 改走 `PageHeader` | |
| `rag/dashboard/index.tsx`（Overview） | —（无筛选） | ✅ 标题从内联 style 改走 `PageHeader` + 描述 | |
| `rag/binding/index.tsx` | —（筛选在 Modal 内，无页级筛选） | 已有 → 改走 `PageHeader` | 仅页头统一，Modal 内表单不动 |

**平台管理 6 页不在范围**（indicator / connectorsManagement / menuManagement / portfolioGroupManagement / rolesManagement / benchmarkEntry）。

**归属筛选顺序全站约定**（各页统一）：组织 → 公司 → 用户 前置，时间及其它靠后（chat 三页已是；tracing 本次调整；llm 只有 company/user 不涉及组织）。

---

## 5. 容器对齐（唯一需要留意的视觉风险）

`FilterField` 是「标签在上、控件在下」的列布局。若页面的筛选容器是 flex 行且 `align-items: center`，带标签项与不带标签项（Reset 按钮 / 时区 Tag）会竖直错位。

**处理**：范围内页面的筛选容器统一 `align-items: flex-end`（控件底端对齐）。这是每页 `.filterBar`/`.filterToolbar`/`dashboardFilterBar` 一处 less 改动。`llm/.filterToolbar` 已是此布局（模板本就如此），其余页面对齐它即可。Reset/Refresh/时区 Tag 这类非筛选控件不包 `FilterField`，直接置于容器内、靠 `flex-end` 与字段底端对齐。

---

## 6. tracing 组织排公司前

`tracing/TraceList/index.tsx` 现为 Company → Organization（DirectorySelect）。调整为 **Organization → Company**，与 chat 三页一致。tracing 无 client_type，不涉及「选 App 禁用组织」。纯 JSX 顺序调整，查询参数不变。

---

## 7. 影响文件清单

| 类型 | 文件 | 改动 |
|---|---|---|
| 新增 | `src/pages/devSupport/_shared/FilterField/index.tsx` + `index.less` + `index.test.tsx` | 标签+控件包装组件 + 单测 |
| 新增 | `src/pages/devSupport/_shared/PageHeader/index.tsx` + `index.less` + `index.test.tsx` | 页头组件 + 单测 |
| 改 | `llm/components/FilterToolbar.tsx`、`AnalyticsFilterBar.tsx` | 各字段包 `FilterField` |
| 改 | `llm/CallList.tsx`、`Dashboard.tsx`、`Cost/Performance/Tokens/Errors/Providers.tsx` | 页头改 `PageHeader` + 补描述 |
| 改 | `llm/index.less` | 删已无引用的 `.filterItem`/`.filterLabel`；容器 `align-items` 保持 |
| 改 | `tracing/TraceList/index.tsx` + `tracing.less` | 字段包 `FilterField`、页头改 `PageHeader`、组织排公司前、容器对齐 |
| 改 | `chatManage/index.tsx`、`chatMessages/index.tsx`、`chatAnalytics/index.tsx` + 各 `index.less` | 字段包 `FilterField`、页头改 `PageHeader`、容器对齐 |
| 改 | `rag/index.tsx`、`rag/stats/index.tsx`、`rag/connections/index.tsx`、`rag/search/*`、`rag/dashboard/index.tsx`、`rag/binding/index.tsx` + 相关 less | 字段包 `FilterField`、页头改 `PageHeader`、rag/dashboard 标题脱离内联 style |

---

## 8. 测试与验证

1. **组件单测**（`npx umi-test`，写完待用户下令跑）：
   - `FilterField`：渲染 label + children；label 经 CSS 大写（断言传入原文、className 存在）；className 透传。
   - `PageHeader`：渲染 title；有 description 才渲染 subTitle、无则不渲染；extra 插槽渲染。
2. **tsc**：`npm run tsc` 本次改动 0 新增 error（基线 2 个存量坏文件 43 error 除外）。
3. **check-routes**：无新增违规（本次不新增路由）。
4. **手动冒烟**：范围内每页目视核对——字段标签齐全对齐、页头标题+描述在位、tracing 组织在公司前、控件底端对齐无错位、筛选行为不变（查询结果与改造前一致）。

---

## 9. 分期

一次性完成（纯前端、无接口依赖、按域可并行实现）：
- **P0**：两个共享组件 + llm 域（FilterToolbar/AnalyticsFilterBar/6 页头）+ tracing + chat 三页 + rag 各页。
- 无 P1/P2（范围已收敛；平台管理页明确排除）。
