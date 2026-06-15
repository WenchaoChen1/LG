# Chat 组件复用改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `ChatPage` 改造成 props 驱动的可复用 `Chat` 组件——真实业务形态为默认，新增聊天入口零改组件代码（只需路由指向 `./ai/chat`）。

**Architecture:** 抽出核心组件 `Chat.tsx`（`simulate?: boolean`，删掉 `useLocation`/pathname 判断），`index.tsx` 与 `simulate.tsx` 作为两个薄 wrapper；删除 `/AskAI`、`/devSupport/chatClient` 两个入口及其路由/菜单引用，模拟入口迁到 `/devSupport/chatSimulate`。本质是重构，行为基本不变（唯一可见变化：`/AskAI` 删除、`/devSupport/chat` 由模拟页变真实业务页）。

**Tech Stack:** React 16, UmiJS 3, TypeScript, Ant Design 4。

**关联文档:** [设计文档](../specs/2026-06-15-chat-component-reuse-design.md)

---

## 前置说明（执行前必读）

- 所有 `npm` / `npx` 命令需在 **PowerShell** 中、且 **node 已在 PATH** 时运行（本机 Node 走 User PATH 直挂版本目录，参见用户记忆 `node-installed-via-nvm` / `web-test-commands`）。
- 工作目录：`C:\Users\wenchao\LG\CIOaas-web`。
- 测试命令用 `npx umi-test`（`npm test` / `npx jest` 在本仓库不可用）；类型检查用 `npm run tsc`。
- `npm run tsc` 基线**已有 2 个存量坏文件**——验证目标是"不新增错误"，不是"零错误"。
- **提交前需用户确认**（项目 Git 规则）；commit message 用英文。

## 文件结构（改造后）

```
src/pages/ai/chat/
├── Chat.tsx          # 新建：核心可复用组件，props { simulate?: boolean }，不读 pathname
├── index.tsx        # 改写：export default () => <Chat />          （真实业务默认，/devSupport/chat + 新入口）
├── simulate.tsx     # 新建：export default () => <Chat simulate />  （/devSupport/chatSimulate）
├── components/ ...  # 不变
├── hooks/ ...       # 不变
└── utils/ ...       # 不变
config/routes.ts                       # 改：删 /AskAI、/devSupport/chatClient；加 /devSupport/chatSimulate
src/pages/ai/devSupport/DevSupportShell.tsx   # 改：菜单项 chatbot-chat-client → chatbot-chat-simulate
```

---

## Task 1: 抽出 `Chat.tsx` 核心组件

把现有 `index.tsx` 复制为 `Chat.tsx`，再把"模式判断"从 pathname 改为 `simulate` prop，并删除随 `/AskAI` 一起退场的 `companyBar`。

**Files:**
- Create: `src/pages/ai/chat/Chat.tsx`（内容 = 复制自 `src/pages/ai/chat/index.tsx` 后按下列 Step 改）

- [ ] **Step 1: 复制 index.tsx 为 Chat.tsx**

PowerShell：
```powershell
Copy-Item "src/pages/ai/chat/index.tsx" "src/pages/ai/chat/Chat.tsx"
```

- [ ] **Step 2: 删除 useLocation import（Chat.tsx 第 2 行）**

old:
```tsx
import { useLocation } from 'umi';
```
new：整行删除。

- [ ] **Step 3: 改函数签名 + 加 props（Chat.tsx 第 20 行）**

old:
```tsx
const ChatPage: React.FC = () => {
```
new:
```tsx
interface ChatProps {
  /** 不传 = 真实业务形态（按登录身份，不发 company_id）；true = 后台模拟身份调试 */
  simulate?: boolean;
}

export const Chat: React.FC<ChatProps> = ({ simulate }) => {
```

- [ ] **Step 4: 模式变量改为基于 simulate prop（Chat.tsx 原第 24-31 行）**

old:
```tsx
  const { pathname } = useLocation();
  // 身份模拟仅超管 + /devSupport/chat 入口；同组件挂载的 /AskAI 与
  // /devSupport/chatClient（镜像入口）恒不显示模拟工具条。
  const simulationEnabled = isAdmin && pathname === '/devSupport/chat';
  // 对外镜像入口（token-only）：权限/数据范围完全由 token 决定，页面不提供任何
  // 公司选择 UI（无 Analyzing 栏、无内联公司下拉），也不发送页面态 company_id；
  // 管理员在此页可直接在问题里写公司名（后端按名匹配）。
  const tokenOnly = pathname === '/devSupport/chatClient';
```
new:
```tsx
  // 后台模拟身份调试形态：simulate prop + 超管双重兜底（即便绕过路由权限，
  // 非超管也不渲染模拟工具条）。不传 simulate = 真实业务形态：无任何管理控件、
  // 不发送页面态 company_id，数据范围完全由后端按登录身份判定。
  const simulationEnabled = simulate === true && isAdmin;
```
（`tokenOnly` 定义删除；下面各 Step 把原 `tokenOnly` 用法改为 `simulationEnabled` 取反语义。）

- [ ] **Step 5: useAccessibleCompanies 改条件（Chat.tsx 原第 82-83 行）**

old:
```tsx
  // token-only 页无任何公司选择 UI，不拉公司列表
  const { companies } = useAccessibleCompanies(isAdmin && !tokenOnly);
```
new:
```tsx
  // 仅模拟形态需要公司列表（simulateBar 下拉 + needs_pick 内联选公司）
  const { companies } = useAccessibleCompanies(simulationEnabled);
```

- [ ] **Step 6: handleSend 的 company 取值（Chat.tsx 原第 101-105 行）**

old:
```tsx
  const handleSend = useCallback(
    // token-only 页不发送页面态 company_id（公司归属交给后端按 token 判定）
    (text: string) => sendWith(text, tokenOnly ? null : companyId || null),
    [sendWith, companyId, tokenOnly],
  );
```
new:
```tsx
  const handleSend = useCallback(
    // 真实业务形态不发送页面态 company_id（公司归属交后端按登录身份判定）；
    // 仅模拟形态发送当前 companyId（配合模拟参数）
    (text: string) => sendWith(text, simulationEnabled ? companyId || null : null),
    [sendWith, companyId, simulationEnabled],
  );
```

- [ ] **Step 7: forkAndResend 的 company 取值（Chat.tsx 原第 163-165 行）**

old:
```tsx
      await sendWith(text, tokenOnly ? null : companyId || null);
    },
    [forkFromMessage, loadThread, newChat, sendWith, companyId, tokenOnly, threadIdRef],
```
new:
```tsx
      await sendWith(text, simulationEnabled ? companyId || null : null);
    },
    [forkFromMessage, loadThread, newChat, sendWith, companyId, simulationEnabled, threadIdRef],
```

- [ ] **Step 8: handleSelectThread 切公司条件（Chat.tsx 原第 216-223 行）**

old:
```tsx
      if (isAdmin && !tokenOnly) {
        // 管理端：picker 自动切到该会话的分析对象公司（token-only 页无公司状态）
        const t = threads.find((th) => th.id === id);
        if (t?.companyId) setCompanyId(t.companyId);
      }
      setDrawerOpen(false);
    },
    [enterThread, isAdmin, tokenOnly, threads],
```
new:
```tsx
      if (simulationEnabled) {
        // 模拟形态：picker 自动切到该会话的分析对象公司（真实业务形态无公司状态）
        const t = threads.find((th) => th.id === id);
        if (t?.companyId) setCompanyId(t.companyId);
      }
      setDrawerOpen(false);
    },
    [enterThread, simulationEnabled, threads],
```

- [ ] **Step 9: 删除 Analyzing companyBar 整块（Chat.tsx 原第 291-298 行）**

old:
```tsx
        {/* 模拟入口页只留模拟工具条（自带公司选择），不再叠加 Analyzing 栏（两个
            公司选择器并存会让人困惑）；镜像入口/AskAI 保持原 Analyzing 栏。 */}
        {isAdmin && !simulationEnabled && !tokenOnly && (
          <div className={styles.companyBar}>
            <span className={styles.companyBarLabel}>Analyzing:</span>
            <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} />
          </div>
        )}
```
new：整块删除（这是 `/AskAI` 专用的 Analyzing 栏，`/AskAI` 已删；`CompanyPicker` 仍被下方 simulateBar 使用，import 保留）。

- [ ] **Step 10: ConversationPane 的 needs_pick 条件（Chat.tsx 原第 350-351 行）**

old:
```tsx
            companies={isAdmin && !tokenOnly ? companies : undefined}
            onPickCompany={isAdmin && !tokenOnly ? handlePickCompany : undefined}
```
new:
```tsx
            companies={simulationEnabled ? companies : undefined}
            onPickCompany={simulationEnabled ? handlePickCompany : undefined}
```

- [ ] **Step 11: 改默认导出（Chat.tsx 末行）**

old:
```tsx
export default ChatPage;
```
new:
```tsx
export default Chat;
```

- [ ] **Step 12: 类型检查 Chat.tsx 无新错误**

Run: `npm run tsc`
Expected: 不出现 `Chat.tsx` 相关的报错（仅可能保留基线那 2 个存量坏文件的错误）。此时 `index.tsx`（旧）与 `Chat.tsx` 并存，均能通过类型检查。

- [ ] **Step 13: Commit**

```bash
git add src/pages/ai/chat/Chat.tsx
git commit -m "refactor(chat): extract reusable Chat component driven by simulate prop"
```

---

## Task 2: 把 `index.tsx` 改为真实业务 wrapper

**Files:**
- Modify: `src/pages/ai/chat/index.tsx`（整文件替换为 wrapper）

- [ ] **Step 1: 用 wrapper 替换 index.tsx 全部内容**

把 `src/pages/ai/chat/index.tsx` 整个文件内容替换为：
```tsx
import React from 'react';
import { Chat } from './Chat';

/**
 * AI Chatbot 真实业务形态入口（/devSupport/chat 及所有新增入口）。
 *
 * 和真实业务系统同款：按登录身份判定数据范围，不发送 company_id，无任何管理控件。
 * 新增入口只需在 config/routes.ts 把 component 指向 './ai/chat'——无需新建文件、
 * 无需传 props。
 */
export default () => <Chat />;
```

- [ ] **Step 2: 类型检查**

Run: `npm run tsc`
Expected: 不新增错误。

- [ ] **Step 3: 现有单测回归**

Run: `npx umi-test`
Expected: `utils/` 下现有单测全部 PASS（本改造未动 utils）。

- [ ] **Step 4: Commit**

```bash
git add src/pages/ai/chat/index.tsx
git commit -m "refactor(chat): make index.tsx a thin real-business wrapper over Chat"
```

---

## Task 3: 新建模拟形态 wrapper `simulate.tsx`

**Files:**
- Create: `src/pages/ai/chat/simulate.tsx`

- [ ] **Step 1: 创建 simulate.tsx**

```tsx
import React from 'react';
import { Chat } from './Chat';

/**
 * AI Chatbot 后台模拟身份调试入口（/devSupport/chatSimulate，需路径权限）。
 *
 * 模拟"哪家公司 / 组织 / 用户"去问答，用于复现客户会遇到的问题。
 */
export default () => <Chat simulate />;
```

- [ ] **Step 2: 类型检查**

Run: `npm run tsc`
Expected: 不新增错误。

- [ ] **Step 3: Commit**

```bash
git add src/pages/ai/chat/simulate.tsx
git commit -m "feat(chat): add chatSimulate wrapper entry"
```

---

## Task 4: 更新路由配置

删除 `/AskAI`、`/devSupport/chatClient`，把 `/devSupport/chat` 明确为真实业务默认，新增 `/devSupport/chatSimulate`。

**Files:**
- Modify: `config/routes.ts`

- [ ] **Step 1: 删除 /AskAI 路由块（routes.ts 原第 466-473 行）**

old:
```ts
          {
            // AI Chatbot V1：两端共用同一路由，页面内按 hostname 自适应（公司端/管理端）。
            // 顶部 "Ask AI" tab 的入口放置以现有顶导实现为准（见 design-doc §11.2）。
            path: '/AskAI',
            name: 'Ask AI',
            hideInMenu: true,
            component: './ai/chat',
          },
```
new：整块删除。

- [ ] **Step 2: 替换 chat + chatClient 两块为 chat + chatSimulate（routes.ts 原第 707-722 行）**

old:
```ts
              {
                // AI Chatbot：复用顶导 "Ask AI" 同一页面组件（./ai/chat），
                // 但挂在 devSupport 下，使其在 DevSupportShell 的 Sider 框架内展示。
                path: '/devSupport/chat',
                name: 'AI Chatbot',
                hideInMenu: true,
                component: './ai/chat',
              },
              {
                // AI Chatbot 对外入口（token-only）：同组件（页面内按 pathname 区分），
                // 无身份模拟工具条、无任何公司选择 UI，权限/数据范围完全由 token 决定。
                path: '/devSupport/chatClient',
                name: 'AI Chat Client',
                hideInMenu: true,
                component: './ai/chat',
              },
```
new:
```ts
              {
                // AI Chatbot 真实业务形态（默认）：和真实业务系统同款，按登录身份判定
                // 数据范围、不发 company_id。新增入口指向 ./ai/chat 即可复用，无需新建文件。
                path: '/devSupport/chat',
                name: 'AI Chatbot',
                hideInMenu: true,
                component: './ai/chat',
              },
              {
                // AI Chatbot 后台模拟身份调试（需路径权限）：模拟公司/组织/用户复现问题。
                path: '/devSupport/chatSimulate',
                name: 'AI Chat Simulate',
                hideInMenu: true,
                component: './ai/chat/simulate',
              },
```

- [ ] **Step 3: 类型检查 + 编译启动自检**

Run: `npm run tsc`
Expected: 不新增错误（路由 component 路径 `./ai/chat/simulate` 对应新建的 `simulate.tsx`）。

- [ ] **Step 4: Commit**

```bash
git add config/routes.ts
git commit -m "feat(chat): route chat to real-business default, move simulate to /devSupport/chatSimulate, drop AskAI & chatClient"
```

---

## Task 5: 更新 DevSupportShell 侧栏菜单

把镜像入口菜单项改成模拟入口（指向新 URL）。

**Files:**
- Modify: `src/pages/ai/devSupport/DevSupportShell.tsx`

- [ ] **Step 1: 替换 chatbot-chat-client 菜单项（DevSupportShell.tsx 原第 85-93 行）**

old:
```tsx
      {
        // 镜像入口（无身份模拟工具条）：同组件按 pathname 区分；
        // 前缀比 chat 长，最长前缀匹配下不会被 chatbot-chat 抢占选中态
        key: 'chatbot-chat-client',
        label: 'Chat Client',
        icon: <CommentOutlined />,
        path: '/devSupport/chatClient',
        matchPrefix: '/devSupport/chatClient',
      },
```
new:
```tsx
      {
        // 后台模拟身份调试（需路径权限）：前缀比 chat 长，
        // 最长前缀匹配下不会被 chatbot-chat 抢占选中态
        key: 'chatbot-chat-simulate',
        label: 'Chat (Simulate)',
        icon: <BugOutlined />,
        path: '/devSupport/chatSimulate',
        matchPrefix: '/devSupport/chatSimulate',
      },
```
（`BugOutlined` 已在文件顶部 import；`CommentOutlined` 若改后无其他引用，ESLint 会在 lint:fix 阶段提示，按需移除。）

- [ ] **Step 2: 类型检查 + 确认无未用 import**

Run: `npm run tsc`
Expected: 不新增错误。

- [ ] **Step 3: Commit**

```bash
git add src/pages/ai/devSupport/DevSupportShell.tsx
git commit -m "feat(chat): replace Chat Client sidebar item with Chat (Simulate)"
```

---

## Task 6: 全量验证 + 注释/文档收尾

**Files:**
- Modify（注释收尾，可选但建议）：`src/pages/ai/chat/index.less`（第 49 行注释提及 chatClient）

- [ ] **Step 1: 更新 index.less 过时注释（原第 49 行）**

old:
```less
// 身份模拟工具条：仅超管 + /devSupport/chat 入口显示（镜像入口 chatClient 无）
```
new:
```less
// 身份模拟工具条：仅模拟形态（/devSupport/chatSimulate）+ 超管显示
```

- [ ] **Step 2: ESLint 自动修复（清理可能的未用 import 等）**

Run: `npm run lint:fix`
Expected: 无报错（自动修复未用 import / 格式）。

- [ ] **Step 3: 类型检查（对比基线）**

Run: `npm run tsc`
Expected: 仅剩基线那 2 个存量坏文件的错误，**无本次改动引入的新错误**。

- [ ] **Step 4: 现有单测回归**

Run: `npx umi-test`
Expected: 全部 PASS。

- [ ] **Step 5: 手动三形态验证**

启动 dev（`npm run start:dev`，端口 8004），以**管理员**登录后逐一确认：

| URL | 预期 |
|------|------|
| `/devSupport/chat` | 纯净：无 Simulate 工具条、无 Analyzing 栏；发问正常，请求体不含页面态 `company_id` |
| `/devSupport/chatSimulate` | 显示 Simulate 工具条；填模拟公司/用户后发问，模拟参数随包发送 |
| `/AskAI` | 404 / 路由不存在 |
| `/devSupport/chatClient` | 404 / 路由不存在 |
| 左侧 DevSupportShell 菜单 | chatbot 组下为 `Chat` / `Chat (Simulate)` / `Chat Management`，点击跳转与选中态正确 |

- [ ] **Step 6: Commit**

```bash
git add src/pages/ai/chat/index.less
git commit -m "chore(chat): refresh stale chatClient comments after reuse refactor"
```

---

## Self-Review 结果（对照 spec）

- **§3.1 组件 API**（`Chat` + `simulate?: boolean`）→ Task 1 Step 3。
- **§3.2 路由方案**（删 AskAI/chatClient、加 chatSimulate、chat 指 ./ai/chat）→ Task 4。
- **§3.3 文件结构**（Chat.tsx / index.tsx / simulate.tsx）→ Task 1 / 2 / 3。
- **§3.4 组件内部改造**（模式变量、company 条件、删 companyBar、发送取值、移除 useLocation）→ Task 1 Step 2-11。
- **§3.5 DevSupportShell 菜单** → Task 5。
- **§4 行为变化**（AskAI/chatClient 删除、chat 语义对调、默认不发 company_id）→ Task 4 + 验证表（Task 6 Step 5）。
- **§7 测试与验证**（tsc + umi-test + 手动三形态）→ Task 6。
- **§8 风险**：链接清理已穷举（routes.ts + DevSupportShell + index.less 注释；CLAUDE.md/architecture.md 中 `/devSupport/chat` 描述仍有效，无需改）；needs_pick 保留给 simulate 形态（Task 1 Step 10）；续流按 threadId 不受 URL 影响（无需改动）。

类型一致性核对：全程使用 `simulationEnabled`（Task 1 内统一定义）；wrapper 用具名导入 `import { Chat } from './Chat'`，与 Task 1 Step 3 的 `export const Chat` 一致。
