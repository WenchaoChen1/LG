# devSupport 筛选栏与页头一致性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 devSupport 各页重复的「筛选字段标签」与「页头标题+描述」收敛成 2 个共享组件（`FilterField` / `PageHeader`），铺到 llm / tracing / rag / chat 三管理页，达成视觉一致并杜绝再漂移。

**Architecture:** 纯前端。新增 `_shared/FilterField`（label+控件列布局）与 `_shared/PageHeader`（title+description+extra 槽），样式逐字取自现模板 `llm/index.less`。范围内页面把裸控件包进 `FilterField`、把页头换成 `PageHeader`；tracing 顺带把组织下拉移到公司前。不动后端、不改查询语义、不加假的「客户端」下拉。

**Tech Stack:** React 16 + TypeScript + Ant Design 4.9 + UmiJS 3 + less（CSS module）。测试 `npx umi-test`（jest），类型 `npm run tsc`。

## Global Constraints

- 纯前端 CIOaas-web；禁改后端接口 / 查询参数语义。
- 不用 antd `Form`/`FormItem`（沿用 div+span 轻量标签范式，与模板一致）。
- 不给 llm/rag/tracing 加「客户端(client_type)」下拉（无数据维度）。
- 平台管理 6 页（indicator/connectorsManagement/menuManagement/portfolioGroupManagement/rolesManagement/benchmarkEntry）**不在范围**。
- 色板/圆角/阴影 token 一律 `@import '../tokens.less'`（或相对深度对应），禁 hardcode 新色。
- `npm run tsc` 基线有 2 个存量坏文件（`components/Charts/awsCPULineCharts.tsx` + `user/userAdmin/TransferProject.ts` 共约 43 error），本计划任何改动**必须 0 新增 error**。
- 测试代码写完**不自动执行**（项目规则：测试统一由用户下令跑）；轻量校验 `npm run tsc` 可随时跑。
- 提交消息用英文；`git add` 窄暂存本任务文件；不 `git push`（等用户说推送）。
- 归属筛选顺序全站约定：**组织 → 公司 → 用户** 前置，时间/关键字/其它靠后。
- 标签调用方传原文（如 `label="Company"`），大写由 CSS `text-transform: uppercase` 完成。
- PowerShell 跑 node 命令须先挂 PATH：`$env:PATH = "$env:APPDATA\nvm\v16.20.2;$env:PATH"`（版本目录若变，取 `$env:APPDATA\nvm` 下 `v*` 首个）。

---

### Task 1: 共享组件 `FilterField`

**Files:**
- Create: `src/pages/devSupport/_shared/FilterField/index.tsx`
- Create: `src/pages/devSupport/_shared/FilterField/index.less`
- Test: `src/pages/devSupport/_shared/FilterField/index.test.tsx`

**Interfaces:**
- Produces: `FilterField: React.FC<{ label: string; children: React.ReactNode; className?: string }>` —— 渲染 `<div class={field}><span class={label}>{label}</span>{children}</div>`，label 经 CSS 大写。默认导出。

- [ ] **Step 1: 写失败测试**

```tsx
// src/pages/devSupport/_shared/FilterField/index.test.tsx
import React from 'react';
import { render } from '@testing-library/react';
import FilterField from './index';

describe('FilterField', () => {
  it('渲染 label 原文与 children', () => {
    const { getByText } = render(
      <FilterField label="Company">
        <input data-testid="ctrl" />
      </FilterField>,
    );
    // 传入原文（大写由 CSS 完成，DOM 文本仍是原文）
    expect(getByText('Company')).toBeTruthy();
  });

  it('children 被渲染在字段内', () => {
    const { getByTestId } = render(
      <FilterField label="User">
        <input data-testid="ctrl" />
      </FilterField>,
    );
    expect(getByTestId('ctrl')).toBeTruthy();
  });

  it('className 透传到外层容器', () => {
    const { container } = render(
      <FilterField label="X" className="my-extra">
        <span />
      </FilterField>,
    );
    expect(container.querySelector('.my-extra')).toBeTruthy();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `$env:PATH = "$env:APPDATA\nvm\v16.20.2;$env:PATH"; npx umi-test src/pages/devSupport/_shared/FilterField/index.test.tsx`
Expected: FAIL（`Cannot find module './index'`）

- [ ] **Step 3: 写 less**

```less
// src/pages/devSupport/_shared/FilterField/index.less
@import '../tokens.less';

@nav-navy: #0D2B56;

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;

  .label {
    font-size: 12px;
    color: @nav-navy;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }

  // 统一控件高度 36（对齐模板 llm .filterItem）
  :global(.ant-select-selector),
  :global(.ant-input),
  :global(.ant-input-affix-wrapper),
  :global(.ant-picker) {
    height: 36px !important;
    border-radius: 6px;
  }
  :global(.ant-select-single .ant-select-selector .ant-select-selection-item),
  :global(.ant-select-single .ant-select-selector .ant-select-selection-placeholder) {
    line-height: 34px !important;
  }
  :global(.ant-switch-checked) {
    background-color: @nav-navy !important;
  }
}
```

- [ ] **Step 4: 写组件**

```tsx
// src/pages/devSupport/_shared/FilterField/index.tsx
/**
 * 单个筛选项的「标签 + 控件」包装（devSupport 全域统一范式）。
 * label 传原文（如 "Company"），展示为大写由 CSS text-transform 完成。
 * 只做布局，不含业务逻辑；控件宽度由 children 自身决定。
 */
import React from 'react';
import classNames from 'classnames';
import styles from './index.less';

interface FilterFieldProps {
  label: string;
  children: React.ReactNode;
  className?: string;
}

const FilterField: React.FC<FilterFieldProps> = ({ label, children, className }) => (
  <div className={classNames(styles.field, className)}>
    <span className={styles.label}>{label}</span>
    {children}
  </div>
);

export default FilterField;
```

- [ ] **Step 5: 跑测试确认通过 + tsc**

Run: `$env:PATH = "$env:APPDATA\nvm\v16.20.2;$env:PATH"; npx umi-test src/pages/devSupport/_shared/FilterField/index.test.tsx; npm run tsc`
Expected: 测试 PASS；tsc 仅基线 43 error、0 新增。

- [ ] **Step 6: 提交**

```bash
git add src/pages/devSupport/_shared/FilterField/
git commit -m "feat(devSupport): add shared FilterField (labeled filter wrapper)"
```

---

### Task 2: 共享组件 `PageHeader`

**Files:**
- Create: `src/pages/devSupport/_shared/PageHeader/index.tsx`
- Create: `src/pages/devSupport/_shared/PageHeader/index.less`
- Test: `src/pages/devSupport/_shared/PageHeader/index.test.tsx`

**Interfaces:**
- Produces: `PageHeader: React.FC<{ title: string; description?: React.ReactNode; extra?: React.ReactNode }>` —— 渲染 titleBar(h1.title + actions 槽) + 可选 subTitle。默认导出。

- [ ] **Step 1: 写失败测试**

```tsx
// src/pages/devSupport/_shared/PageHeader/index.test.tsx
import React from 'react';
import { render } from '@testing-library/react';
import PageHeader from './index';

describe('PageHeader', () => {
  it('渲染标题', () => {
    const { getByText } = render(<PageHeader title="Chat Management" />);
    expect(getByText('Chat Management')).toBeTruthy();
  });

  it('有 description 才渲染副标题', () => {
    const { getByText } = render(
      <PageHeader title="T" description="10 threads match current filters" />,
    );
    expect(getByText('10 threads match current filters')).toBeTruthy();
  });

  it('无 description 不渲染副标题', () => {
    const { container } = render(<PageHeader title="T" />);
    // 只有 titleBar，无 subTitle 节点
    expect(container.querySelectorAll('div').length).toBe(1);
  });

  it('extra 槽渲染', () => {
    const { getByTestId } = render(
      <PageHeader title="T" extra={<button data-testid="refresh">R</button>} />,
    );
    expect(getByTestId('refresh')).toBeTruthy();
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `$env:PATH = "$env:APPDATA\nvm\v16.20.2;$env:PATH"; npx umi-test src/pages/devSupport/_shared/PageHeader/index.test.tsx`
Expected: FAIL（`Cannot find module './index'`）

- [ ] **Step 3: 写 less**

```less
// src/pages/devSupport/_shared/PageHeader/index.less
@import '../tokens.less';

.titleBar {
  display: flex;
  align-items: center;
  margin-bottom: 4px;

  .title {
    flex: 1;
    font-size: 22px;
    font-weight: 600;
    color: @c-text;
    line-height: 1.3;
    letter-spacing: -0.2px;
  }
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.subTitle {
  margin-bottom: 20px;
  font-size: 13px;
  color: @c-muted;
}
```

- [ ] **Step 4: 写组件**

```tsx
// src/pages/devSupport/_shared/PageHeader/index.tsx
/**
 * devSupport 统一页头：标题 + 可选描述（「N X match current filters」）+ 右侧操作槽。
 * 描述文案由调用方拼装；无 description 时不渲染副标题行。
 */
import React from 'react';
import styles from './index.less';

interface PageHeaderProps {
  title: string;
  description?: React.ReactNode;
  extra?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, description, extra }) => (
  <>
    <div className={styles.titleBar}>
      <h1 className={styles.title}>{title}</h1>
      {extra && <div className={styles.actions}>{extra}</div>}
    </div>
    {description !== undefined && description !== null && (
      <div className={styles.subTitle}>{description}</div>
    )}
  </>
);

export default PageHeader;
```

> 注：Task 1 的第 3 个测试断言「无 description 时只有 1 个 div」。`PageHeader` 无 description 时渲染 titleBar(1 个 div) + 内部 actions 仅当 extra 存在才有。测试用例未传 extra，故仅 titleBar 一个 div，符合断言。若某页 title 很长换行影响，可后续微调，不阻塞。

- [ ] **Step 5: 跑测试确认通过 + tsc**

Run: `$env:PATH = "$env:APPDATA\nvm\v16.20.2;$env:PATH"; npx umi-test src/pages/devSupport/_shared/PageHeader/index.test.tsx; npm run tsc`
Expected: 测试 PASS；tsc 0 新增。

- [ ] **Step 6: 提交**

```bash
git add src/pages/devSupport/_shared/PageHeader/
git commit -m "feat(devSupport): add shared PageHeader (title + description + extra)"
```

---

## 页面迁移通用配方（Task 3-9 共用，此处定义一次）

**A. 包字段标签**：把筛选栏里每个「裸控件」用 `FilterField` 包起来，label 见各任务字段表。
```jsx
// 之前：<CompanySelect value=... onChange=... />
// 之后：
<FilterField label="Company">
  <CompanySelect value={...} onChange={...} />
</FilterField>
```
非筛选控件（Reset/Refresh 按钮、时区 Tag）**不包** FilterField，直接留在容器里。

**B. 换页头**：把页面顶部 `titleBar`/`title` + `subTitle`（或内联标题）替换为：
```jsx
<PageHeader
  title="<页面标题>"
  description={<>{...上下文} · {total.toLocaleString()} {名词} match current filters</>}
  extra={<>{...原 Refresh/时区 Tag 等}</>}
/>
```

**C. 容器对齐**：该页筛选容器 less 类加 `align-items: flex-end;`（若已是则跳过），保证带标签项与 Reset/Tag 底端对齐。

**D. 收尾**：`npm run tsc` 0 新增；目视/单测确认无回归；窄暂存提交。

每个页面任务末尾统一：
```
Run: $env:PATH = "$env:APPDATA\nvm\v16.20.2;$env:PATH"; npm run tsc
Expected: 0 新增 error（基线 43 除外）
git add <该任务文件>; git commit -m "<英文消息>"
```

---

### Task 3: llm CallList + FilterToolbar（模板迁移到共享源）

**Files:**
- Modify: `src/pages/devSupport/llm/components/FilterToolbar.tsx`（15 个 `filterItem`+`filterLabel` → `FilterField`）
- Modify: `src/pages/devSupport/llm/CallList.tsx`（页头 → `PageHeader`）
- Modify: `src/pages/devSupport/llm/index.less`（删已无引用的 `.filterItem`/`.filterLabel`，保留 `.filterToolbar`/`.filterActions` 容器；容器已是 `align-items: flex-end`）

**Interfaces:**
- Consumes: `FilterField`（Task 1）、`PageHeader`（Task 2）。

字段表（label 原文 → 控件，顺序保持现状）：Company / User / Time Range / Provider / Status / Agent / Node / Call Mode / Call Type / Model / Trace ID / Min Cost (USD) / Finish Reason / Sort By / Show retries。

- [ ] **Step 1**：`FilterToolbar.tsx` 顶部 `import FilterField from '../../_shared/FilterField';`，把每个 `<div className={styles.filterItem}><span className={styles.filterLabel}>X</span><Ctrl/></div>` 改为 `<FilterField label="X"><Ctrl/></FilterField>`（Show retries 的 Tooltip 包在 label 上——改为 `label` 传 "Show retries"，Tooltip 移到 FilterField 外层包裹或保留在控件上；最简：label 直接传文案，去掉 Tooltip 或用 `title` 属性提示）。
- [ ] **Step 2**：`CallList.tsx` 顶部 `import PageHeader from '../_shared/PageHeader';`，把 `<div className={styles.titleBar}><h1 className={styles.title}>Call Logs</h1></div>` + `<div className={styles.subTitle}>Cross-task LLM call logs · {total.toLocaleString()} calls match current filters</div>` 替换为：
```jsx
<PageHeader
  title="Call Logs"
  description={`Cross-task LLM call logs · ${total.toLocaleString()} calls match current filters`}
/>
```
- [ ] **Step 3**：`index.less` 删除 `.filterItem { ... }` 整块（含内嵌 `.filterLabel`，行 186-216），保留 `.filterToolbar`/`.filterActions`/`.subTitle`/`.titleBar`/`.title`（仍被其它 llm 页引用，Task 4 再逐步替换；本任务只删已确认无引用的 `.filterItem`）。**先 grep 确认**：`grep -rn "styles.filterItem\|styles.filterLabel" src/pages/devSupport/llm` 应仅剩 0 处（FilterToolbar 已改完）再删。
- [ ] **Step 4**：tsc + 提交
```bash
git add src/pages/devSupport/llm/components/FilterToolbar.tsx src/pages/devSupport/llm/CallList.tsx src/pages/devSupport/llm/index.less
git commit -m "refactor(llm): migrate Call Logs filter labels & header to shared components"
```

---

### Task 4: llm AnalyticsFilterBar + 6 分析页页头

**Files:**
- Modify: `src/pages/devSupport/llm/components/AnalyticsFilterBar.tsx`（各字段包 `FilterField`）
- Modify: `src/pages/devSupport/llm/Dashboard.tsx`、`Cost.tsx`、`Performance.tsx`、`Tokens.tsx`、`Errors.tsx`、`Providers.tsx`（页头 → `PageHeader` + 描述）
- Modify: `src/pages/devSupport/llm/index.less`（`dashboardFilterBar` 加 `align-items: flex-end`——现为 `center`）

**Interfaces:** Consumes `FilterField` / `PageHeader`。

AnalyticsFilterBar 字段：Company / User / Time Range / Interval / Provider / Agent（按现有顺序，前三为归属+时间）。

各页 `PageHeader` 描述文案（`{...}` 用各页已有的 total/count 变量；无计数的用固定上下文句）：
- Dashboard：`title="LLM Dashboard"`，`description="Global LLM usage overview"`（Dashboard 是聚合，无单一 total → 固定上下文，不带 match 计数）。
- Cost：`title="Cost Analytics"`，`description="LLM spend by dimension"`。
- Performance：`title="Performance Analytics"`，`description="LLM latency percentiles by dimension"`。
- Tokens：`title="Token Analytics"`，`description="LLM token usage by dimension"`。
- Errors：`title="Error Analytics"`，`description="LLM failures by class / provider / model"`。
- Providers：`title="Provider Comparison"`，`description="Cost / latency / reliability across providers"`。

> 说明：分析页是聚合视图、无「N 条匹配」计数，描述用一句上下文即可（与 CallList 的「N calls match」格式并列、不强套计数）。

- [ ] **Step 1**：`AnalyticsFilterBar.tsx` 每个筛选控件包 `FilterField`（label：Company/User/Time Range/Interval/Provider/Agent）。
- [ ] **Step 2**：6 个页面各把标题（部分嵌在筛选条内，如 Dashboard 的 `h1.title`）移出为顶部 `PageHeader`。Dashboard 现状标题在 `dashboardFilterBar` 内——改为筛选条上方独立 `PageHeader`，筛选条只留控件。
- [ ] **Step 3**：`index.less` `dashboardFilterBar` 的 `align-items: center` → `flex-end`。
- [ ] **Step 4**：tsc + 提交
```bash
git add src/pages/devSupport/llm/components/AnalyticsFilterBar.tsx src/pages/devSupport/llm/Dashboard.tsx src/pages/devSupport/llm/Cost.tsx src/pages/devSupport/llm/Performance.tsx src/pages/devSupport/llm/Tokens.tsx src/pages/devSupport/llm/Errors.tsx src/pages/devSupport/llm/Providers.tsx src/pages/devSupport/llm/index.less
git commit -m "refactor(llm): shared filter labels & headers for analytics pages"
```

---

### Task 5: tracing TraceList（标签 + 页头 + 组织排公司前）

**Files:**
- Modify: `src/pages/devSupport/tracing/TraceList/index.tsx`
- Modify: `src/pages/devSupport/tracing/TraceList/index.less`（或 `tracing.less`，看 import；筛选容器加 `align-items: flex-end`）

**Interfaces:** Consumes `FilterField` / `PageHeader`。

字段（调整后顺序）：Organization / Company / Source / Status / Time Range / Name / Task ID。**组织移到公司前**（现为 Company→Organization，改为 Organization→Company）。

- [ ] **Step 1**：`import FilterField from '../../_shared/FilterField'; import PageHeader from '../../_shared/PageHeader';`
- [ ] **Step 2**：筛选栏每个控件包 `FilterField`；把 Organization 的 `<FilterField>` 块移到 Company 之前。
- [ ] **Step 3**：页头（现有 `titleBar`+`title`+Refresh + `subTitle`）替换为 `PageHeader title="Trace Explorer" description={...现有描述文案...} extra={<Refresh/>}`。
- [ ] **Step 4**：筛选容器 less 加 `align-items: flex-end`（若已是则跳过）。
- [ ] **Step 5**：tsc + 提交
```bash
git add src/pages/devSupport/tracing/TraceList/
git commit -m "refactor(tracing): shared filter labels & header, org before company"
```

---

### Task 6: chatManage

**Files:**
- Modify: `src/pages/devSupport/chatManage/index.tsx`
- Modify: `src/pages/devSupport/chatManage/index.less`（`.filterBar` 加 `align-items: flex-end`）

**Interfaces:** Consumes `FilterField` / `PageHeader`。

字段（顺序已是组织→公司→用户）：Client Type / Organization / Company / User / Search / Time Range。（Reset 按钮不包。）端类型三逻辑已完成，本任务只加标签、换页头、对齐容器。

- [ ] **Step 1**：import 两组件。筛选栏每个控件包 `FilterField`（label：Client Type / Organization / Company / User / Search / Time Range）；`OrganizationSelect` 的 `disabled` 等属性保持不动。Reset 按钮留在容器内不包。
- [ ] **Step 2**：页头（`titleBar` + `title` "Chat Management" + tzTag + Refresh + `subTitle`）→ `PageHeader title="Chat Management" description={\`Conversation analytics & history across all users · ${total.toLocaleString()} threads match current filters\`} extra={<><Tag className={styles.tzTag}>{TZ_LABEL}</Tag><Button icon={<ReloadOutlined/>} onClick={handleRefresh}>Refresh</Button></>} />`。
- [ ] **Step 3**：`index.less` `.filterBar` 加 `align-items: flex-end`。
- [ ] **Step 4**：tsc + 提交
```bash
git add src/pages/devSupport/chatManage/index.tsx src/pages/devSupport/chatManage/index.less
git commit -m "refactor(chatManage): shared filter labels & header"
```

---

### Task 7: chatMessages

**Files:**
- Modify: `src/pages/devSupport/chatMessages/index.tsx`
- Modify: `src/pages/devSupport/chatMessages/index.less`（`.filterBar` 加 `align-items: flex-end`）

字段（顺序组织→公司→用户）：Client Type / Organization / Company / User / Search / Time Range。组织的 `disabled={orgDisabled}` 等保持。

- [ ] **Step 1**：import 两组件；每个筛选控件包 `FilterField`（级联的普通 Select 也一样包）。Reset 不包。
- [ ] **Step 2**：页头 → `PageHeader title="Chat Q&A" description={\`Question → answer turns across all threads · ${total.toLocaleString()} turns match current filters\`} extra={<><Tag className={styles.tzTag}>{TZ_LABEL}</Tag><Button ...>Refresh</Button></>} />`。（`Chat Q&A` 里的 `&` 在 JSX 字符串用 `Chat Q&A` 即可，非属性用 `&amp;` 场景不适用——此处是 prop 字符串，直接写 `"Chat Q&A"`。）
- [ ] **Step 3**：`index.less` `.filterBar` 加 `align-items: flex-end`。
- [ ] **Step 4**：tsc + 提交
```bash
git add src/pages/devSupport/chatMessages/index.tsx src/pages/devSupport/chatMessages/index.less
git commit -m "refactor(chatMessages): shared filter labels & header"
```

---

### Task 8: chatAnalytics

**Files:**
- Modify: `src/pages/devSupport/chatAnalytics/index.tsx`
- Modify: `src/pages/devSupport/chatAnalytics/index.less`（筛选条 `filterBar` 加 `align-items: flex-end`；标题从筛选条内移出）

字段（顺序组织→公司→用户）：Client Type / Organization / Company / User / Time Range / Interval。组织 `disabled` 保持。

- [ ] **Step 1**：import 两组件；筛选控件包 `FilterField`。把当前嵌在 `filterBar` 内的 `<h1 className={styles.filterTitle}>Chat Analytics</h1>` 移出。
- [ ] **Step 2**：页面顶部加 `PageHeader title="Chat Analytics" description="Chatbot usage analytics by user / company / organization / client / time" extra={<><Refresh/><Reset/> + 时区 Tag>} />`（Refresh/Reset/tzTag 从筛选条移到 header extra，或保留在筛选条尾部——二选一，保持与 Dashboard 一致：header 放标题+描述+tzTag，Refresh/Reset 留筛选条尾）。实现者按 Dashboard 观感二选一，保证一致即可。
- [ ] **Step 3**：`index.less` 筛选容器加 `align-items: flex-end`。
- [ ] **Step 4**：tsc + 提交
```bash
git add src/pages/devSupport/chatAnalytics/index.tsx src/pages/devSupport/chatAnalytics/index.less
git commit -m "refactor(chatAnalytics): shared filter labels & header with description"
```

---

### Task 9: rag 各页

**Files:**
- Modify: `src/pages/devSupport/rag/index.tsx`（Spaces：keyword 搜索包 `FilterField` label "Search"；页头 → `PageHeader`）
- Modify: `src/pages/devSupport/rag/stats/index.tsx`（space 选择器包 `FilterField` label "Space"；页头 → `PageHeader`）
- Modify: `src/pages/devSupport/rag/connections/index.tsx`（backend 选择器包 `FilterField` label "Backend"；页头 → `PageHeader`）
- Modify: `src/pages/devSupport/rag/search/index.tsx` + `RecallPanel`（各控件包 `FilterField`；页头 → `PageHeader`）
- Modify: `src/pages/devSupport/rag/dashboard/index.tsx`（标题从内联 style → `PageHeader` + 描述）
- Modify: `src/pages/devSupport/rag/binding/index.tsx`（仅页头 → `PageHeader`，Modal 内不动）
- Modify: 对应 less（筛选容器 `align-items: flex-end`）

**Interfaces:** Consumes `FilterField` / `PageHeader`。

- [ ] **Step 1**：逐页 import 两组件，按上表包字段标签 + 换页头。rag/dashboard 的内联 style 标题改走 `PageHeader`（title "RAG Overview" + 一句描述）。
- [ ] **Step 2**：各页筛选容器 less 加 `align-items: flex-end`（无筛选栏的页跳过）。
- [ ] **Step 3**：tsc + 提交
```bash
git add src/pages/devSupport/rag/
git commit -m "refactor(rag): shared filter labels & headers across pages"
```

---

## Self-Review

**Spec coverage：**
- §3.1 FilterField → Task 1 ✓；§3.2 PageHeader → Task 2 ✓
- §4 应用矩阵：llm CallList/FilterToolbar → Task 3；AnalyticsFilterBar+6 页 → Task 4；tracing → Task 5；chatManage → Task 6；chatMessages → Task 7；chatAnalytics → Task 8；rag 各页 → Task 9 ✓
- §5 容器对齐 → 每个页面任务的 less 步骤 ✓
- §6 tracing 组织排公司前 → Task 5 Step 2 ✓
- §7 影响文件 → 各任务 Files 覆盖 ✓
- §8 测试：组件单测 Task 1/2；tsc 每任务；手动冒烟在执行时逐页做 ✓
- 非目标（不加客户端下拉、不动平台管理页、不用 FormItem）→ Global Constraints ✓

**Placeholder scan：** 页面迁移任务用「通用配方 + 字段表 + 具体页头文案」表达，非「similar to」偷懒；shared 组件有完整代码+测试。rag 各页因控件在各自文件、以字段表 + label 明确表达（控件的 value/onChange 保持原样，纯包裹），无需重述其内部 props。✓

**Type consistency：** `FilterField({label,children,className})` 与 `PageHeader({title,description,extra})` 在 Task 1/2 定义、Task 3-9 一致消费 ✓

**已知取舍：** 分析类页面（llm Dashboard/Cost 等、chatAnalytics）无单一「N 条匹配」计数，描述用一句上下文（不强套计数格式），已在 Task 4/8 显式说明。
