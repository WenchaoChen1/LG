# 按菜单与页面的多租户现状

> 关联文档: [可交付报告](./多租户与企业级安全-可交付报告.md) | [需求清单](../需求/requirement-doc.md) | [前端设计](./frontend-design.md)
>
> 本文把[需求清单](../需求/requirement-doc.md)的 21 条按**菜单与页面**重新归集，便于逐页验收。菜单名与路径取自 `src/layouts/BasicLayout.tsx` 与 `config/routes.ts`，均为系统内实名。

## 状态口径

| 标记 | 含义 |
|---|---|
| ✅ | 服务端已按登录身份校验归属，可直接接外部租户 |
| ❌ | 归属由页面传入且服务端不校验，或门禁只在前端 |
| ⚠️ | 待核实或待产品确认 |

**一条贯穿全表的事实**：`ErlCallerDTO.java:14` 写明「`roleType <= 1` 为管理端（GSV，**公司取入参**），否则为公司端（Founder，**公司锁定自身**）」。公司端的租户身份从会话锁死、页面改不了；管理端的组织身份是页面传上来的。**所以要改的页面几乎全在管理端。**

---

## 一、管理端菜单

| 菜单 | 页面 | 状况 | 对应需求 |
|---|---|---|---|
| **Portfolio Companies** | 公司列表页、Connections 页、Add Company 页、公司总览页 | ❌ Add Company 的 `?organizationId=` **优先于组织树且不校验是否在自己树内**；公司列表的 `?params=<base64>` 绕过同文件内的白名单校验（base64 非加密） | R-04 |
| **Portfolio Management** | Portfolio 列表页、新建 Portfolio 页 | ❌ `companyGroup/findAllSort` 按传入组织取数 | R-04 |
| **Portfolio Group Management** | 组织管理页（组织 CRUD + 菜单授权） | ❌ 任意登录用户可在任意位置建 / 挪组织，可形成环路 | R-11 |
| **User Management** | 用户管理页、用户详情页 | ❌ `users/query` 按传入组织；Add / Edit 的权限**算完从未消费**，编辑图标无条件渲染 | R-04、R-10 |
| **Roles Management** | 角色管理页（角色 × 菜单矩阵） | ❌ 8 个角色接口不校验租户；`role_key` 全局唯一，两租户同名角色即冲突 | R-12、R-13 |
| **Company Roles** | 公司角色页 | ❌ 同上 | R-12、R-13 |
| **Menu & Function Management** | 菜单与功能点管理页 | ❌ 平台级功能，但无服务端门禁 | R-10 |
| **KPAs Configuration** | KPA 配置页、KPA 配置编辑页 | ❌ URL `?organizationId=` 明文可改；方法论正文按编码**改一处对全部租户生效** | R-04、R-05 |
| **SDP Score Calculation Setup** | SDP 评分配置页 | ❌ `saveScoreConfiguration` **改写全库每个组织的权重** | R-04、R-05 |
| **Financial Health Score Configuration** | 财务健康分配置页 | ❌ 类目权重与等级为全平台唯一一套 | R-05 |
| **Tech Stack Management** | 技术栈管理页 | ❌ `techStackManagement/*` 拼入传入组织；类型全平台、条目按租户，口径不一 | R-04、R-05 |
| **Business Issues** | 问题列表页、问题详情页、提交结果页 | ❌ `businessIssues/admin`、`businessIssues/client` 按传入组织；公司列与超管操作 `roleType <= 1` 内联 | R-04、R-10 |
| **QBO Connection Log** | QBO 连接日志页 | ❌ 传入组织后展开该组织全部公司，**不校验调用者** | R-04 |
| **Financial Metrics Tracing** | 列表页、详情页 | ❌ `companyIds` 由页面传 | R-04 |
| **Normalization Tracing** | 列表页、详情页 | ❌ 同上，详情页 URL 带 `?companyId=` | R-04 |
| **Peer Group Management** | 同行组列表页、详情页 | ❌ 同行组取数不分租户；参照企业不足 3 家时回退为全平台取数 | R-07 |
| **Benchmark Entry** | 对标数据录入页 | ❌ `roleType <= 2` 内联 | R-10 |
| **Connectors Management** | 连接器目录页 | ⚠️ 平台级归属待产品确认 | 待确认问题 2 |
| **ERL Configuration** | 配置页、新增问题页、编辑问题页、历史页 | ✅ 走 `ErlAccessService` 统一校验 | — |
| **Company Settings** | 公司设置页、Company Stage 页 | ❌ 各 Tab `roleType <= 2` / `<= 1` 内联 | R-10 |
| **Dev Support** | 15 个子区（chat、llm、rag、tracing、financialExtract、indicator 等），共 36 个 URL | ❌ README 自述"登录即可访问、不加 role 门禁"，前端单点门禁在 `SecurityLayout.tsx:67-71` 读 **localStorage** | R-10 |
| **Alert Configuration** | 告警配置页 | ⚠️ 页面无组织 / 公司参数，需查后端接口口径 | — |
| **Indicator** | 指标页 | ⚠️ 同上 | — |
| **Dev Settings** | 开发设置页 | ⚠️ 同上 | — |

## 二、公司端菜单

| 菜单 | 页面 | 状况 |
|---|---|---|
| **SDP Score** | `/company/sdp`，页内含 Overview、Projects、KPA Reviews、Documentation、**Trends and Benchmarks** 五个页签 | ✅ 公司身份从会话锁定，页面改不了 |
| **KPAs** | KPA 用户设置页 | ✅ 同上 |
| **Tech Journey** | 技术历程页 | ✅ 同上 |
| **Products** | 产品页 | ✅ 同上 |
| **Finance** | 财务页 | ✅ 同上 |

> **Trends 与 Benchmarks 已不是独立菜单或页面**：两项在 `BasicLayout.tsx` 里仍有定义，但点击后都跳 `/company/sdp` 并切页签（`active: 'monthly'` / `'benchmark'`），现已合并为单个页签 `Trends and Benchmarks`。同期 routes.ts 里一批老路由标注 `@deprecated` 并注释，注明「零入口路由已注释（组件作 `/company/sdp` 页内 Tab 内嵌保留），观察期后删」。
>
> 需要注意的是，**财务对标模块 3 个接口的授权守卫仍然成立**——守卫在后端接口上，前端入口变化不影响它，R-04 改造的模板仍取自这里。
>
> 另：`BasicLayout.tsx:637` 把 `Monthly`、`projects`、`Finance`、`Development`、`documents` 硬编码白名单放行，不走权限列表校验（归 R-10）。

## 三、两端通用

| 菜单 | 页面 | 状况 | 对应需求 |
|---|---|---|---|
| **Ask Goldie** | 对话页 | ✅ 知识库授权公司集 fail-closed、SSE `/subscribe` 归属校验、身份模拟非超管 403 | — |
| **Knowledge Base** | 知识库页 | ❌ 召回按客户端给的空间标识放行，不校验调用者归属 | R-04 |
| **Memory Settings** | 记忆设置页 | ✅ 后端 40301 兜底 | — |
| **Audit Trail** | 审计页 | ⚠️ 业务审计已有，操作审计写入未开启 | R-15 ~ R-17 |

---

## 结论

1. **要改的集中在管理端**：24 个管理菜单里 17 个要动，公司端 5 个基本不用改。差别不在页面质量，而在于公司端身份锁死、管理端身份由页面传。
2. **已经做对的有 4 处**：ERL、Ask Goldie、Memory Settings，以及财务对标模块的授权守卫（覆盖 3 个接口并配回归测试，是全仓唯一正面样板，可作 R-04 的改造模板）。
3. **Dev Support 是页面数量上的重灾区，但改法最省事**：36 个 URL 同质性高，套模板可批量改完——这也是 R-04 只估 1.25 周的原因。
4. **风险今天就能复现**：生产有 5 个组织，改 URL 里的组织标识即可看到别家数据，只是目前跨过去看到的是自己的测试组织。

## 待核实

Alert Configuration、Indicator、Dev Settings 三个菜单的页面里看不到组织或公司参数，需查其后端接口才能定性。
