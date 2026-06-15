# Chat 组件复用改造 — 设计文档

> 日期：2026-06-15　|　范围：CIOaas-web 前端　|　目标读者：实现该改造的开发/AI

## 1. 背景与目标

### 现状

`/AskAI`、`/devSupport/chat`、`/devSupport/chatClient` 三个路由**共用同一个页面组件** `src/pages/ai/chat/index.tsx`（`ChatPage`），在 `config/routes.ts` 里三条 `component` 都写成 `./ai/chat`。组件内部靠 `useLocation().pathname` 在运行时 if/else 区分三种行为：

```tsx
// src/pages/ai/chat/index.tsx:27,31
const simulationEnabled = isAdmin && pathname === '/devSupport/chat';   // 身份模拟工具条
const tokenOnly        = pathname === '/devSupport/chatClient';         // 对外镜像入口（不发 company_id）
```

**问题**：模式判断硬编码在组件内部、绑定具体 URL。要在新的入口/页面复用这个聊天，必须改组件内部的 pathname 判断——组件不是真正可复用的黑盒。

### 目标

把 `ChatPage` 改造成 **props 驱动的可复用组件 `Chat`**：

- **真实业务形态为默认**：`<Chat />` 不传任何参数即为"和真实业务系统同款"的聊天（按登录身份判定数据范围，不发 `company_id`，无任何管理控件）。
- **新增入口零成本**：系统里任意页面/入口只需把路由 `component` 指向 `./ai/chat`（或 `import` 该组件），不改组件代码、不传 props。
- 组件内部**不再读 `pathname`**。

## 2. 现状分析：三种 pathname 分支

| 入口 | 管理员看到 | 普通用户看到 | 发给后端的 company | 派生变量 |
|------|------|------|------|------|
| `/AskAI` | Analyzing 公司选择栏 | 纯净 | `resolveActiveCompanyId`（customer）/ picker 选中（admin） | `isAdmin && !simulationEnabled && !tokenOnly` |
| `/devSupport/chat` | 身份模拟工具条 | 纯净 | 模拟参数 + `companyId` | `simulationEnabled` |
| `/devSupport/chatClient` | 纯净（连管理控件都没有） | 纯净 | **不发**（`null`，后端按登录身份） | `tokenOnly` |

关键事实：`simulationEnabled` 和 `companyBar` 的显示条件都带 `isAdmin`，所以**对真实终端用户（非 admin），三个入口表现一致**。`chatClient`（`tokenOnly`）的真正特殊点只有两条：① 连管理员打开也保持纯净；② 不发送页面态 `company_id`。

company 相关现有逻辑分布：

- `companyId` state，由 `resolveActiveCompanyId(endType)` 初始化（`endContext.ts:27`：customer 取 `inviteDto.id`/`companyId`；admin 取 query string `id`）。
- `useAccessibleCompanies(isAdmin && !tokenOnly)` 拉公司列表（`index.tsx:83`）。
- **Analyzing companyBar**（`index.tsx:293-298`，条件 `isAdmin && !simulationEnabled && !tokenOnly`）—— 仅 `/AskAI` 管理员使用。
- **simulateBar**（`index.tsx:299-338`）—— 仅 `simulate` 模式使用，内含 `CompanyPicker`（模拟公司）。
- **needs_pick 内联选公司**（`ConversationPane` 的 `companies`/`onPickCompany`，`index.tsx:350-351`，条件 `isAdmin && !tokenOnly`）—— `/AskAI` + `simulate` 模式启用。
- `handleSelectThread` 里 `isAdmin && !tokenOnly` 时同步 `companyId`（`index.tsx:216-220`）。
- 发送路径 company 取值：`tokenOnly ? null : companyId`（`index.tsx:103,163`）。

## 3. 目标设计

### 3.1 组件 API

```tsx
// src/pages/ai/chat/Chat.tsx —— 唯一核心组件，不再读 pathname
interface ChatProps {
  simulate?: boolean;   // 不传 = 真实业务形态
}
export const Chat: React.FC<ChatProps> = ({ simulate }) => { ... };
```

| 取值 | 使用场景 | 谁用 |
|------|------|------|
| **不传（默认）** | **真实业务**：按登录身份，**不发 `company_id`**，连管理员也无任何控件 | `/devSupport/chat`、所有新入口 |
| `simulate` | **后台模拟身份调试**：模拟公司/组织/用户去复现客户问题（需路径权限 + admin 兜底） | `/devSupport/chatSimulate` |

只有两种形态，故用布尔 `simulate` 最直接（YAGNI）；以后真出现第三种形态再升级为 `mode` 枚举。命名取自业务原话"模拟"。

### 3.2 路由方案（最终只保留两条）

```
/devSupport/chat          → ./ai/chat            (默认真实业务，<Chat />)
/devSupport/chatSimulate  → ./ai/chat/simulate   (模拟，<Chat simulate />)
```

- **删除 `/AskAI`**（顶导 Ask AI 入口整个移除）。
- **删除 `/devSupport/chatClient`**（真实业务形态由 `/devSupport/chat` 承接）。
- **新增入口**：`routes.ts` 加一行 `component: './ai/chat'` + 在目标菜单/按钮加链接。**零新文件、零 props**。

#### URL 最佳实践：为何 `chatSimulate` 而非 `chat/simulate`

采用**独立平级路径 `/devSupport/chatSimulate`**，理由：

1. **语义更准**：`simulate` 不是 `chat` 的子资源/子页面，而是平行的、用途不同的入口（后台调试 vs 真实业务）。子路径暗示层级从属，名不副实。
2. **与现有约定一致**：项目已有 `/devSupport/chatManage`（驼峰平级），`chatSimulate` 同款风格。
3. **权限隔离（决定性）**：`simulate` 需路径权限、`chat` 对所有真实用户开放。独立平级路径可按**精确路径**拦 `chatSimulate`，绝不误伤 `chat`；若用 `chat/simulate` 子路径，按前缀 `/chat*` 做权限会把子路径一起圈进，需特意排除，易出错。

### 3.3 文件结构

```
src/pages/ai/chat/
├── Chat.tsx          # 核心组件（现 index.tsx 逻辑搬入，删 pathname；props: { simulate?: boolean }）
├── index.tsx        # export default () => <Chat />          ← 真实业务默认（/devSupport/chat 与所有新入口）
├── simulate.tsx     # export default () => <Chat simulate />  ← 模拟（/devSupport/chatSimulate）
├── components / hooks / utils ...   (见 3.4 改动)
```

> umi 配置式路由（`config/routes.ts`）下，`simulate.tsx`、`Chat.tsx` 不会被自动注册为路由，只有显式配置的 `component` 才生效。

### 3.4 组件内部改造

把两个 pathname 派生变量改写为基于 `simulate` prop，并随 `/AskAI` 删除清理第三分支：

- `simulationEnabled`：`isAdmin && pathname === '/devSupport/chat'` → **`simulate && isAdmin`**（即便 URL 权限被绕过，非 admin 也不显示模拟工具，行为兜底等价）。
- `tokenOnly`（真实业务"不发 company"）：删除 `/AskAI` 后，所有"非 simulate"入口都等同原 `tokenOnly` 行为，故 `tokenOnly` 等价物 = **`!simulationEnabled`**。
- **删除**：Analyzing `companyBar`（`index.tsx:293-298`）及其专属分支——唯一使用者 `/AskAI` 已删。
- **保留**（改为仅 `simulate` 模式启用，把原 `isAdmin && !tokenOnly` 条件统一改为 `simulationEnabled`）：
  - `CompanyPicker` 组件（simulateBar 内仍用）。
  - `useAccessibleCompanies`（simulate 模式拉公司列表给 simulateBar / needs_pick）。
  - needs_pick 内联选公司（`ConversationPane` 的 `companies`/`onPickCompany`、`handlePickCompany`）。
  - `handleSelectThread` 内同步 `companyId`。
- **发送路径 company 取值**：`tokenOnly ? null : companyId` → **`simulationEnabled ? companyId : null`**（默认真实业务恒发 `null`；simulate 模式发 `companyId` + 模拟参数）。涉及 `handleSend`（`index.tsx:103`）、`forkAndResend`（`index.tsx:163`）。
- `useLocation` import 移除。

`resolveEndType`（admin/customer 按 hostname + roleType 自适应）**保持不变**——它与 pathname 无关，新入口直接沿用。

### 3.5 DevSupportShell Sider 菜单改动

`src/pages/ai/devSupport/DevSupportShell.tsx` 的 `NAV_GROUPS` 里 `chatbot` 组现有三项（`chatbot-chat` / `chatbot-chat-client` / `chatbot-manage`）。改动：

- `chatbot-chat`（78-84）：保持指 `/devSupport/chat`，label `Chat` 不变（现在它是真实业务默认页）。
- `chatbot-chat-client`（85-93）：改为模拟入口——`key` → `chatbot-chat-simulate`，`label` → `Chat (Simulate)`，`path` 与 `matchPrefix` → `/devSupport/chatSimulate`，图标可沿用或改（如 `BugOutlined` 表"调试"）。
- `chatbot-manage`（94-101）：不变。
- 选中态走最长 `matchPrefix` 前缀匹配：`/devSupport/chatSimulate` 比 `/devSupport/chat` 长，进模拟页时不会被 `chatbot-chat` 抢占选中态（与现有 `chatManage` 同理，自洽）。

## 4. 行为变化清单（需知情）

1. **`/AskAI` 删除**：顶导 "Ask AI" 入口消失；指向它的导航链接/菜单项需一并清理（design-doc §11.2 提到的顶部 "Ask AI" tab）。
2. **`/devSupport/chatClient` 删除**：指向该 URL 的链接需清理或确认无引用。
3. **`/devSupport/chat` 语义对调**：由"身份模拟页"变为"真实业务默认页"；模拟功能搬到 `/devSupport/chatSimulate`。
4. **默认形态对所有端不发 `company_id`**：含 customer 端——原 `/AskAI` 对 customer 会发 `resolveActiveCompanyId`（`inviteDto.id`），改造后真实业务统一不发，完全交后端按登录身份判定。

## 5. 权限

- `/devSupport/chatSimulate` 需路径权限（仅开发/后台管理员）。独立平级路径便于网关/路由按精确路径拦截。
- 组件内 `simulate && isAdmin` 双重兜底：即便有人绕过路由权限访问 `chatSimulate`，非 admin 也不会渲染模拟工具条。
- `/devSupport/chat` 及新入口：真实业务，按登录身份，对所有合法登录用户开放。

## 6. 新增入口的标准步骤（文档化，供后续复用）

1. 在 `config/routes.ts` 目标位置加一条：`{ path: '<新路径>', component: './ai/chat', ... }`。
2. 在目标页面/菜单/按钮加一个指向 `<新路径>` 的链接。
3. 完成——无需新建文件、无需传 props，得到的就是"真实业务同款"聊天。

## 7. 测试与验证

本仓库**无 `.test.tsx` 组件渲染测试先例**，`package.json` 未显式装 `@testing-library/react`，且 `Chat` 依赖大量 hook/子组件/services——为其新建渲染测试成本高、收益低（YAGNI）。本改造本质是**重构**（模式来源从 pathname 换 prop + 删一个入口，行为基本不变），验证策略为：

- **类型检查**：`npm run tsc`，对比基线（基线已有 2 个存量坏文件），确保**不新增**类型错误。
- **现有单测回归**：`npx umi-test`，`utils/` 下现有单测（`endContext`/`messageReducer`/`streamResume` 等）保持全绿（本改造不动 `utils/`）。
- **手动三形态验证**（跑 dev，管理员登录）：
  - `/devSupport/chat`：纯净——无 Simulate 工具条、无 Analyzing 栏；发送不带 `company_id`。
  - `/devSupport/chatSimulate`：显示 Simulate 工具条，模拟参数生效。
  - `/AskAI`、`/devSupport/chatClient`：均 404（已删除）。

## 8. 风险与待核实

1. **后端依赖**：默认形态不发 `company_id`，依赖后端在登录态、无 `company_id` 时按 token 正确判定数据范围。这是原 `chatClient`（真实业务镜像，customer 亦可访问）一直在跑的行为，视为已验证；改造后扩大到所有真实业务入口，建议回归确认 customer 端无 `company_id` 路径。
2. **链接清理**：全局搜索 `/AskAI`、`devSupport/chatClient`、`AskAI` 的引用（菜单、跳转、文档），删除或改指 `/devSupport/chat`。
3. **续流不受影响**：sessionStorage 续流记录按 `threadId` 存（非 URL），路由改名/删除不影响断流恢复。
4. **needs_pick 去留**：内联选公司流程**保留**给 simulate 模式（用于"模拟身份后后端要求选具体公司"）；默认真实业务形态沿用原 `tokenOnly` 行为（不启用内联选公司）。
