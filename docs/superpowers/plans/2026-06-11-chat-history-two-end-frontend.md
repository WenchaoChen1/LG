# AI Chatbot 历史与两端完善（Web 前端）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `/ai/devSupport/chat` 补齐会话标题实时同步、历史会话重命名/删除、两端差异化文案、roleType 端判定、needs_pick 内联选公司与移动端响应式。
**Architecture:** 严格沿用 api → dto → service → hook → 组件 分层：`chatApi/chatService` 增 PATCH/DELETE；`chatEvents` 契约单点已含 `title` 事件（基线）；页面层经 `useChatStream`/`useChatThreads` 两个 hook 接线，组件保持纯展示（props 上报事件）。
**Tech Stack:** React 16 / antd 4.9.2 / UmiJS 3 / TypeScript
**关联 spec:** docs/superpowers/specs/2026-06-11-chat-history-and-two-end-design.md

---

## 全局约定（执行者必读）

- **工作目录**：`C:\github-code\LG\CIOaas-web`，所有路径相对该目录。
- **门禁**：每个 Task 结束运行 `npm run tsc`。**已核实基线（2026-06-11）**：仅 `src/components/Charts/awsCPULineCharts.tsx` 与 `src/pages/user/userAdmin/TransferProject.ts` 两个历史文件报错（与本次无关）。验收标准 = **错误清单与基线完全一致，本次改动文件零错误**。
- **测试**：jest 基架损坏（jest.config 指向缺失的 `tests/PuppeteerEnvironment`），测试照写但**不执行、不动 jest.config**。
- **提交**：本计划执行期间**不执行任何 git add/commit**（工作区混有另一会话的未提交 SSE/停止生成改动，统一由主会话最后与用户确认提交方案）。`config/proxy.ts` 属用户本地配置，任何最终提交不得包含它。
- **工作区基线（另一会话已实现、未提交，叠加其上、不要回退）**：`streamSSE.ts`（signal + AbortError 静默）、`streamSSE.test.ts`、`chatEvents.ts/.test.ts`（`title` 事件 + `onTitle` + 用例）、`streamApi.ts`（`{ signal }` 第三参数）、`useChatStream.ts`（abortRef + `stop()`，stop 依赖 abort → streamChat 收尾 onDone → finish，**不要重写**）、`InputBox.tsx`（streaming 时方块停止按钮）、`index.tsx`（已接 stop/streaming）。
- 改任何文件前先 Read 当前版本（行号以实际为准）。
- antd 4.9.2：Dropdown 用 `overlay`（无 `menu` prop）、Popconfirm 受控 `visible`、Drawer 用 `visible`、`Grid.useBreakpoint` 可用。React 16.8：仅 hooks，不用 React 17+/18 API。

---

## Task 1：chatApi + chatService 增 renameThread / deleteThread

**Files:**
- Modify: `src/services/api/chat/chatApi.ts`（末尾追加）
- Modify: `src/services/service/chat/chatService.ts`（import 区 + 末尾追加）
- Test: `src/services/service/chat/chatService.test.ts`（末尾追加）

**Steps:**

- [ ] 1. `chatApi.ts` 末尾追加（PATCH/DELETE 照本文件既有 GET 同一 umi-request 模式；信封类型名以该文件现状为准，下用 `PythonEnvelope` 指代）：

```typescript
/** 重命名会话（PATCH /api/ai/chat/threads/{id}，body {title}；后端返回无 data 的 OkResponse）。 */
export async function renameThread(
  threadId: string,
  title: string,
): Promise<PythonEnvelope<null>> {
  return request(`/api/ai/chat/threads/${encodeURIComponent(threadId)}`, {
    method: 'PATCH',
    data: { title },
  });
}

/** 删除会话（DELETE 同路径，后端软删）。 */
export async function deleteThread(threadId: string): Promise<PythonEnvelope<null>> {
  return request(`/api/ai/chat/threads/${encodeURIComponent(threadId)}`, {
    method: 'DELETE',
  });
}
```

- [ ] 2. `chatService.ts` 的 chatApi import 块追加 `renameThread as apiRenameThread, deleteThread as apiDeleteThread`，并在文件末尾追加（`unwrapChat` 要求 `data != null`，OkResponse 无 data，故增配套校验）：

```typescript
/** @internal 校验无 data 的信封（OkResponse）：success !== true 抛 ChatApiError。 */
export function ensureChatOk(res: PythonEnvelope<null> | undefined): void {
  if (!res || res.success !== true) {
    throw new ChatApiError(res?.message ?? 'Network error', res?.code ?? -1);
  }
}

export async function renameThread(threadId: string, title: string): Promise<void> {
  ensureChatOk(await apiRenameThread(threadId, title));
}

export async function deleteThread(threadId: string): Promise<void> {
  ensureChatOk(await apiDeleteThread(threadId));
}
```

- [ ] 3. `chatService.test.ts` 末尾追加：

```typescript
it('ensureChatOk passes on success envelope without data', () => {
  expect(() =>
    ensureChatOk({ success: true, code: 0, message: 'OK', data: null }),
  ).not.toThrow();
});

it('ensureChatOk throws ChatApiError on failure envelope', () => {
  expect(() =>
    ensureChatOk({ success: false, code: 404, message: 'not found', data: null }),
  ).toThrow(ChatApiError);
});
```

- [ ] 4. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 2：endContext 按 roleType 判端（hostname 兜底）

**Files:**
- Modify: `src/pages/ai/chat/utils/endContext.ts`（`resolveEndType` 改写，`resolveActiveCompanyId` 不动）
- Test: `src/pages/ai/chat/utils/endContext.test.ts`（`resolveEndType` describe 重写，沿用该文件既有的 utils mock 方式）

**Steps:**

- [ ] 1. `endContext.ts` 头部（`ADMIN_HOSTS` 之后）与 `resolveEndType` 替换为：

```typescript
/** 客户端角色（roleType 2/3/4，与后端 Redis 会话判定口径一致）。 */
const COMPANY_ROLE_TYPES = [2, 3, 4];

/**
 * 端类型判定：优先登录用户 roleType（1=超管→admin，2/3/4→company）；
 * roleType 缺失（未登录/异常态）回退 hostname 判定（本地 dev 不再恒判 company）。
 * 代码库中 roleType 既有 number 也有 string 用法，必须 Number() 归一。
 */
export function resolveEndType(host: string = window.location.host): EndType {
  const roleType = Number((getUserInfo() as { roleType?: number | string })?.roleType);
  if (roleType === 1) return 'admin';
  if (COMPANY_ROLE_TYPES.includes(roleType)) return 'company';
  return ADMIN_HOSTS.includes(host) ? 'admin' : 'company';
}
```

- [ ] 2. `endContext.test.ts` 的 `resolveEndType` describe 重写（先 Read 该文件确认 mock 形态）：

```typescript
describe('resolveEndType', () => {
  beforeEach(() => {
    utils.getUserInfo.mockReset();
    utils.getUserInfo.mockReturnValue({});
  });

  it('roleType 1 -> admin regardless of host (local dev included)', () => {
    utils.getUserInfo.mockReturnValue({ roleType: 1 });
    expect(resolveEndType('localhost:8004')).toBe('admin');
  });
  it('string roleType "1" is Number-normalized to admin', () => {
    utils.getUserInfo.mockReturnValue({ roleType: '1' });
    expect(resolveEndType('app-test.lgpi.io')).toBe('admin');
  });
  it('roleType 2/3/4 -> company even on admin host', () => {
    utils.getUserInfo.mockReturnValue({ roleType: '3' });
    expect(resolveEndType('admin.lgpi.io')).toBe('company');
  });
  it('missing roleType falls back to admin host detection', () => {
    expect(resolveEndType('admin-test.lgpi.io')).toBe('admin');
  });
  it('missing roleType on app host falls back to company', () => {
    expect(resolveEndType('app-test.lgpi.io')).toBe('company');
    expect(resolveEndType('localhost:8000')).toBe('company');
  });
});
```

- [ ] 3. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 3：两端差异化文案 WELCOME_BY_END + SuggestionCards 接 props

**Files:**
- Modify: `src/pages/ai/chat/constants.ts`（整文件重写）
- Modify: `src/pages/ai/chat/components/SuggestionCards.tsx`（props 化）
- Modify: `src/pages/ai/chat/index.tsx`（最小接线，保证本 Task 结束 tsc 通过）

**Steps:**

- [ ] 1. `constants.ts` 整文件替换为：

```typescript
import type { EndType } from './utils/endContext';

export interface SuggestionCard {
  tag: string;
  text: string;
}

// 客户端建议卡：沿用 V1 现有 6 张（已是单公司视角）
export const SUGGESTION_CARDS: SuggestionCard[] = [
  { tag: 'FINANCIALS', text: "Summarize this company's latest financial highlights" },
  { tag: 'TREND', text: 'How has ARR/MRR trended over the last 4 quarters?' },
  { tag: 'BENCHMARK', text: 'Where does this company rank vs peers (percentile)?' },
  { tag: 'RUNWAY', text: "What's the current runway and burn rate?" },
  { tag: 'FORECAST', text: 'Compare actuals vs committed forecast for revenue' },
  { tag: 'COMPANY', text: 'What does this company do and what stage is it at?' },
];

// 管理端建议卡：单公司可答版（围绕已选公司；与 LG-1335 原文跨公司 prompts 的偏差
// 已确认，见 docs/superpowers/specs/2026-06-11-chat-history-and-two-end-design.md §5.3）
export const ADMIN_SUGGESTION_CARDS: SuggestionCard[] = [
  { tag: 'RISKS', text: 'Is the selected company showing signs of underperformance this month?' },
  { tag: 'FINANCIALS', text: "Summarize the selected company's latest financial highlights" },
  { tag: 'BENCHMARK', text: 'How does this company score against benchmark peers right now?' },
  { tag: 'FORECAST', text: 'Is this company falling behind its committed forecast?' },
  { tag: 'RUNWAY', text: "What's this company's runway and monthly burn rate?" },
  { tag: 'COMPANY', text: 'Give me a quick profile of this company and its stage' },
];

export const DISCLAIMER = 'AI can make mistakes. Please check important information.';

/** 两端差异化欢迎文案（设计文档 §5.3，headline 逐字以设计文档为准）。 */
export const WELCOME_BY_END: Record<EndType, { title: string; cards: SuggestionCard[] }> = {
  company: {
    title: 'Always here, always in sync—your partner for every business move.',
    cards: SUGGESTION_CARDS,
  },
  admin: {
    title: 'Always-on intelligence for your entire portfolio.',
    cards: ADMIN_SUGGESTION_CARDS,
  },
};
```

- [ ] 2. `SuggestionCards.tsx`：props 增加 `cards: SuggestionCard[]`，map 源由 `SUGGESTION_CARDS` 改为 `cards`（JSX 其余不动）：

```tsx
import React from 'react';
import type { SuggestionCard } from '../constants';
import styles from './SuggestionCards.less';

interface Props {
  cards: SuggestionCard[];
  onPick: (text: string) => void;
}

const SuggestionCards: React.FC<Props> = ({ cards, onPick }) => (
  <div className={styles.grid}>
    {cards.map((c) => (
```

- [ ] 3. `index.tsx` 最小接线：`import { WELCOME_TITLE }` 改为 `import { WELCOME_BY_END }`；`empty` 计算前加 `const welcome = WELCOME_BY_END[endType];`；欢迎区改为：

```tsx
<h2 className={styles.welcomeTitle}>{welcome.title}</h2>
<SuggestionCards cards={welcome.cards} onPick={handleSend} />
```

- [ ] 4. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 4：messageReducer 增 needsPick action

**Files:**
- Modify: `src/pages/ai/chat/utils/messageReducer.ts`（ChatMsg / ChatAction / reducer 新 case）
- Test: `src/pages/ai/chat/utils/messageReducer.test.ts`（末尾追加）

**Steps:**

- [ ] 1. `ChatMsg` 增加可选标记：

```typescript
export interface ChatMsg {
  role: 'user' | 'assistant';
  blocks: MessageBlock[];
  /** needs_pick 标记：MessageBubble 据此渲染内联公司下拉（仅管理端 SSE 流中产生）。 */
  needsPick?: boolean;
}
```

- [ ] 2. `ChatAction` union 中 `| { type: 'finish' }` 之前加 `| { type: 'needsPick'; hint: string }`。
- [ ] 3. reducer 的 `case 'finish':` 之前插入（`updateLastAssistant`/`nextId` 等 helper 名以该文件现状为准）：

```typescript
    case 'needsPick': {
      // 最后一条 assistant 消息：追加提示文本块 + 打 needsPick 标记，streaming 归零。
      const appended = updateLastAssistant(state, (blocks) => [
        ...blocks,
        { type: 'text', text: action.hint, id: nextId() },
      ]);
      const msgs = appended.messages.slice();
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, needsPick: true };
      }
      return { ...appended, messages: msgs, streaming: false };
    }
```

- [ ] 4. `messageReducer.test.ts` 末尾追加：

```typescript
it('needsPick 在最后一条 assistant 消息追加提示文本并打标记、streaming 归零', () => {
  let s = chatReducer(initialChatState, { type: 'startAssistant' });
  s = chatReducer(s, { type: 'needsPick', hint: 'Please tell me which company.' });
  const msg = s.messages[0];
  expect(msg.needsPick).toBe(true);
  expect(msg.blocks[msg.blocks.length - 1]).toMatchObject({
    type: 'text',
    text: 'Please tell me which company.',
  });
  expect(s.streaming).toBe(false);
});
```

- [ ] 5. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 5：useChatStream — onTitle 上抛 + needsPick 派发（不动 stop）

**Files:**
- Modify: `src/pages/ai/chat/hooks/useChatStream.ts`（函数签名 + send 回调对象 + deps；**stop/abortRef 保持基线原样**）

**Steps:**

- [ ] 1. 函数签名改为：

```typescript
export function useChatStream(
  endType: EndType,
  onTitle?: (threadId: string, title: string) => void,
) {
```

- [ ] 2. `send` 的回调对象中，`onThreadId` 块之后插入：

```typescript
          // 标题已生成：上抛给页面联动 useChatThreads.applyTitle（不在本 hook 持有侧栏状态）
          onTitle: (t, title) => {
            if (alive()) onTitle?.(t, title);
          },
```

- [ ] 3. `onNeedsPick` 块（连同其上方"暂按纯文本渲染"注释）替换为：

```typescript
          // needs_pick：在最后一条 assistant 消息追加提示并打标记，
          // 由 MessageBubble 渲染内联公司下拉（仅管理端出现该事件）。
          onNeedsPick: (hint) => {
            if (alive()) dispatch({ type: 'needsPick', hint });
          },
```

      （`onBlocked` 保持原样不动。）
- [ ] 4. `send` 的 deps `[endType]` 改为 `[endType, onTitle]`。
- [ ] 5. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 6：useChatThreads — applyTitle / renameThread / removeThread

**Files:**
- Modify: `src/pages/ai/chat/hooks/useChatThreads.ts`（整文件重写，保留既有 reload/alive 行为）

**Steps:**

- [ ] 1. 整文件替换为（先 Read 现状，保留其加载行为语义；DTO 字段名以 `chatDto.ts` 现状为准）：

```typescript
import { useState, useCallback, useEffect, useRef } from 'react';
import { message } from 'antd';
import {
  fetchThreads,
  renameThread as serviceRenameThread,
  deleteThread as serviceDeleteThread,
  ChatApiError,
} from '@/services/service/chat/chatService';
import type { ChatThreadDTO } from '@/services/api/chat/chatDto';

export function useChatThreads() {
  const [threads, setThreads] = useState<ChatThreadDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const alive = useRef(true);
  useEffect(
    () => () => {
      alive.current = false;
    },
    [],
  );

  const reload = useCallback(() => {
    setLoading(true);
    fetchThreads()
      .then((ts) => {
        if (alive.current) setThreads(ts);
      })
      .catch((e) => {
        if (alive.current) message.error(e instanceof ChatApiError ? e.message : 'Load failed');
      })
      .finally(() => {
        if (alive.current) setLoading(false);
      });
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  /** 本地 immutable 更新某条会话标题（SSE title 事件 / 重命名成功后调用，不整表 reload）。 */
  const applyTitle = useCallback((threadId: string, title: string) => {
    setThreads((prev) => prev.map((t) => (t.id === threadId ? { ...t, title } : t)));
  }, []);

  /** 重命名会话：service 成功后本地更新；失败 toast、state 不变（无乐观更新）。 */
  const renameThread = useCallback(
    async (threadId: string, title: string): Promise<boolean> => {
      try {
        await serviceRenameThread(threadId, title);
        if (alive.current) applyTitle(threadId, title);
        return true;
      } catch (e) {
        if (alive.current) {
          message.error(e instanceof ChatApiError ? e.message : 'Rename failed');
        }
        return false;
      }
    },
    [applyTitle],
  );

  /** 删除会话：service 成功后本地移除；失败 toast、state 不变（无乐观更新）。 */
  const removeThread = useCallback(async (threadId: string): Promise<boolean> => {
    try {
      await serviceDeleteThread(threadId);
      if (alive.current) setThreads((prev) => prev.filter((t) => t.id !== threadId));
      return true;
    } catch (e) {
      if (alive.current) {
        message.error(e instanceof ChatApiError ? e.message : 'Delete failed');
      }
      return false;
    }
  }, []);

  return { threads, loading, reload, applyTitle, renameThread, removeThread };
}
```

- [ ] 2. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 7：HistorySidebar — Rename/Delete 菜单 + 桌面折叠

**Files:**
- Modify: `src/pages/ai/chat/components/HistorySidebar.tsx`（整文件重写）
- Modify: `src/pages/ai/chat/components/HistorySidebar.less`（整文件重写）
- Modify: `src/pages/ai/chat/index.tsx`（配套接线，保证 tsc 通过；完整接线在 Task 9 收口）

**Steps:**

- [ ] 1. `HistorySidebar.tsx` 整文件替换为（先 Read 现状对齐 `groupThreads`/DTO 字段名）：

```tsx
import React, { useState } from 'react';
import { Button, Dropdown, Menu, Input, Popconfirm } from 'antd';
import {
  PlusOutlined,
  MoreOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import type { ChatThreadDTO } from '@/services/api/chat/chatDto';
import { groupThreads } from '../utils/groupThreads';
import styles from './HistorySidebar.less';

interface Props {
  threads: ChatThreadDTO[];
  activeId: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  /** 重命名/删除：由页面接 useChatThreads，resolve(false) 表示失败（toast 已在 hook 内）。 */
  onRename: (id: string, title: string) => Promise<boolean>;
  onDelete: (id: string) => Promise<boolean>;
  /** 桌面折叠态；折叠时仅展示展开按钮 + New Chat 图标按钮（New Chat 始终可见）。 */
  collapsed?: boolean;
  /** 不传则不渲染折叠开关（移动端抽屉内由 Drawer 自带关闭）。 */
  onToggleCollapsed?: () => void;
  now?: number;
}

const HistorySidebar: React.FC<Props> = ({
  threads,
  activeId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  collapsed = false,
  onToggleCollapsed,
  now,
}) => {
  const [editingId, setEditingId] = useState('');
  const [draft, setDraft] = useState('');
  const [deletingId, setDeletingId] = useState('');

  const startEdit = (t: ChatThreadDTO) => {
    setEditingId(t.id);
    setDraft(t.title || '');
  };

  const commitEdit = async () => {
    const id = editingId;
    const title = draft.trim();
    setEditingId('');
    if (!id || !title) return; // 空标题不提交（后端 422 口径，strip 后校验）
    const current = threads.find((t) => t.id === id);
    if (current && current.title === title) return; // 未变更不发请求
    await onRename(id, title);
  };

  if (collapsed) {
    return (
      <aside className={styles.sidebarCollapsed}>
        <Button
          type="text"
          icon={<MenuUnfoldOutlined />}
          aria-label="Expand chat history"
          onClick={onToggleCollapsed}
        />
        <Button
          type="primary"
          shape="circle"
          icon={<PlusOutlined />}
          aria-label="New Chat"
          onClick={onNewChat}
        />
      </aside>
    );
  }

  const groups = groupThreads(threads, now ?? Date.now());
  return (
    <aside className={styles.sidebar}>
      <div className={styles.header}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          className={styles.newChat}
          onClick={onNewChat}
        >
          New Chat
        </Button>
        {onToggleCollapsed && (
          <Button
            type="text"
            icon={<MenuFoldOutlined />}
            aria-label="Collapse chat history"
            onClick={onToggleCollapsed}
          />
        )}
      </div>
      <div className={styles.list}>
        {groups.map((g) => (
          <div key={g.group} className={styles.group}>
            <div className={styles.groupTitle}>{g.group}</div>
            {g.items.map((t) =>
              t.id === editingId ? (
                <Input
                  key={t.id}
                  className={styles.renameInput}
                  size="small"
                  autoFocus
                  maxLength={255}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onPressEnter={() => {
                    void commitEdit();
                  }}
                  onBlur={() => {
                    void commitEdit();
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') setEditingId('');
                  }}
                />
              ) : (
                <div
                  key={t.id}
                  className={`${styles.item} ${t.id === activeId ? styles.itemActive : ''}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelect(t.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') onSelect(t.id);
                  }}
                  title={t.title || t.id}
                >
                  <span className={styles.itemTitle}>{t.title || 'Untitled chat'}</span>
                  <Popconfirm
                    title="Delete this chat?"
                    okText="Delete"
                    okButtonProps={{ danger: true }}
                    visible={deletingId === t.id}
                    onConfirm={async () => {
                      setDeletingId('');
                      await onDelete(t.id);
                    }}
                    onCancel={() => setDeletingId('')}
                  >
                    <Dropdown
                      trigger={['click']}
                      overlay={
                        <Menu
                          onClick={({ key, domEvent }) => {
                            domEvent.stopPropagation();
                            if (key === 'rename') startEdit(t);
                            if (key === 'delete') setDeletingId(t.id);
                          }}
                        >
                          <Menu.Item key="rename">Rename</Menu.Item>
                          <Menu.Item key="delete" danger>
                            Delete
                          </Menu.Item>
                        </Menu>
                      }
                    >
                      <Button
                        type="text"
                        size="small"
                        className={styles.moreBtn}
                        icon={<MoreOutlined />}
                        aria-label="Thread actions"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Dropdown>
                  </Popconfirm>
                </div>
              ),
            )}
          </div>
        ))}
      </div>
    </aside>
  );
};

export default HistorySidebar;
```

  > 实现注记：Delete 不直接放 Popconfirm 进 Menu.Item（Dropdown 点击即关、Popconfirm 会随之卸载）；改为菜单点击 `delete` 置 `deletingId`，受控 `visible` 的 Popconfirm 锚定在 `···` 按钮上——antd 4.9 兼容、行为确定。

- [ ] 2. `HistorySidebar.less` 整文件替换为（token 变量名以 `_shared/tokens.less` 现状为准，没有对应变量就用其最接近变量或字面值）：

```less
@import '../../_shared/tokens.less';

.sidebar {
  flex: 0 0 260px;
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid @c-line;
  background: #fff;
  padding: 16px 12px;
  overflow: hidden;
}

.sidebarCollapsed {
  flex: 0 0 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  border-right: 1px solid @c-line;
  background: #fff;
  padding: 16px 8px;
}

.header {
  display: flex;
  align-items: center;
  gap: 4px;
}

.newChat {
  flex: 1;
}

.list {
  flex: 1;
  overflow-y: auto;
  margin-top: 12px;
}

.group {
  margin-bottom: 12px;
}

.groupTitle {
  font-size: 11px;
  font-weight: 600;
  color: @c-muted;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 6px 8px;
}

.item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 4px 4px 10px;
  border-radius: @radius-sm;
  cursor: pointer;

  &:hover {
    background: @c-bg-soft;
  }
  &:hover .moreBtn {
    opacity: 1;
  }
  &:focus-visible {
    outline: 2px solid @c-primary;
  }
}

.itemActive {
  background: @c-primary-soft;

  .moreBtn {
    opacity: 1;
  }
}

.itemTitle {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 24px;
  color: @c-text;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.moreBtn {
  flex: none;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.renameInput {
  margin: 2px 0;
}
```

- [ ] 3. 运行 `npm run tsc`（预期：与基线一致；index.tsx 的新 props 接线若未完成会报错——可在本 Task 先做最小接线，完整版在 Task 9）

---

## Task 8：MessageBubble / ConversationPane — needsPick 内联公司下拉

**Files:**
- Modify: `src/pages/ai/chat/components/MessageBubble.tsx`（props 扩展 + needsPick 渲染）
- Modify: `src/pages/ai/chat/components/MessageBubble.less`（末尾追加 `.pickRow`）
- Modify: `src/pages/ai/chat/components/ConversationPane.tsx`（props 透传）

**Steps:**

- [ ] 1. `MessageBubble.tsx`：props 增加 `companies?: CompanyDTO[]`、`onPickCompany?: (companyId: string) => void`；assistant 渲染块末尾追加（`import CompanyPicker from './CompanyPicker';` + DTO 类型 import；其余渲染保持现状）：

```tsx
{msg.needsPick && onPickCompany && (
  <div className={styles.pickRow}>
    <CompanyPicker companies={companies ?? []} value="" onChange={onPickCompany} />
  </div>
)}
```

- [ ] 2. `MessageBubble.less` 末尾追加：

```less
.pickRow {
  margin-top: 8px;
}
```

- [ ] 3. `ConversationPane.tsx`：props 增加 `companies?: CompanyDTO[]`、`onPickCompany?: (companyId: string) => void`，map 渲染时**仅最后一条消息**接 `onPickCompany`（重发后旧 needsPick 气泡的下拉自动失效）：

```tsx
<MessageBubble
  key={i}
  msg={m}
  companies={companies}
  onPickCompany={i === messages.length - 1 ? onPickCompany : undefined}
/>
```

- [ ] 4. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 9：index.tsx 全接线 — onTitle、needs_pick 重发、管理端公司同步、移动端抽屉

**Files:**
- Modify: `src/pages/ai/chat/index.tsx`（整文件重写；基于 Task 3/7 后的状态）
- Modify: `src/pages/ai/chat/index.less`（末尾追加 `.mobileBar`）

**Steps:**

- [ ] 1. `index.tsx` 整文件替换为（`InputBox` 的 props 形态以工作区基线为准——另一会话已实现 streaming/onStop，若签名不同按基线对齐）：

```tsx
import React, { useMemo, useState, useCallback } from 'react';
import { Button, Drawer, Grid } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';
import { useChatStream } from './hooks/useChatStream';
import { useChatThreads } from './hooks/useChatThreads';
import { useAccessibleCompanies } from './hooks/useAccessibleCompanies';
import { resolveEndType, resolveActiveCompanyId } from './utils/endContext';
import ConversationPane from './components/ConversationPane';
import InputBox from './components/InputBox';
import SuggestionCards from './components/SuggestionCards';
import CompanyPicker from './components/CompanyPicker';
import HistorySidebar from './components/HistorySidebar';
import { WELCOME_BY_END } from './constants';
import styles from './index.less';

const ChatPage: React.FC = () => {
  const endType = useMemo(() => resolveEndType(), []);
  const isAdmin = endType === 'admin';
  const [companyId, setCompanyId] = useState<string>(() => resolveActiveCompanyId(endType));

  const {
    threads,
    reload: reloadThreads,
    applyTitle,
    renameThread,
    removeThread,
  } = useChatThreads();
  // SSE title 事件 → 侧栏本地更新（不整表 reload）
  const { state, send, stop, loadThread, newChat, threadIdRef } = useChatStream(
    endType,
    applyTitle,
  );
  const { companies } = useAccessibleCompanies(isAdmin);
  const [activeThread, setActiveThread] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const screens = Grid.useBreakpoint();
  const isMobile = screens.md === false; // <768px：侧栏抽屉化（md 断点 = 768px）

  const sendWith = useCallback(
    async (text: string, cid: string | null) => {
      await send(text, cid);
      setActiveThread(threadIdRef.current || '');
      reloadThreads();
    },
    [send, reloadThreads, threadIdRef],
  );

  const handleSend = useCallback(
    (text: string) => sendWith(text, companyId || null),
    [sendWith, companyId],
  );

  /** needs_pick 内联选中公司：同步 picker 并以所选公司自动重发最近一条 user 消息
   *（同一 thread；会再落一条相同 user 消息——诚实反映会话流，设计文档 §8 已确认）。 */
  const handlePickCompany = useCallback(
    (picked: string) => {
      if (!picked) return;
      setCompanyId(picked);
      const lastUser = [...state.messages].reverse().find((m) => m.role === 'user');
      const text = lastUser
        ? lastUser.blocks.map((b) => (b.type === 'text' ? b.text : '')).join('')
        : '';
      if (text) void sendWith(text, picked);
    },
    [state.messages, sendWith],
  );

  const handleSelectThread = useCallback(
    (id: string) => {
      setActiveThread(id);
      void loadThread(id);
      if (isAdmin) {
        // 管理端：picker 自动切到该会话的分析对象公司
        const t = threads.find((th) => th.id === id);
        if (t?.activeCompanyId) setCompanyId(t.activeCompanyId);
      }
      setDrawerOpen(false);
    },
    [loadThread, isAdmin, threads],
  );

  const handleNewChat = useCallback(() => {
    newChat();
    setActiveThread('');
    setDrawerOpen(false);
  }, [newChat]);

  const handleDeleteThread = useCallback(
    async (id: string) => {
      const ok = await removeThread(id);
      if (ok && id === activeThread) handleNewChat(); // 删除当前激活会话 → 回欢迎页
      return ok;
    },
    [removeThread, activeThread, handleNewChat],
  );

  const welcome = WELCOME_BY_END[endType];
  const empty = state.messages.length === 0;

  const sidebar = (
    <HistorySidebar
      threads={threads}
      activeId={activeThread}
      onNewChat={handleNewChat}
      onSelect={handleSelectThread}
      onRename={renameThread}
      onDelete={handleDeleteThread}
      collapsed={!isMobile && sidebarCollapsed}
      onToggleCollapsed={isMobile ? undefined : () => setSidebarCollapsed((c) => !c)}
    />
  );

  return (
    <div className={styles.chatPage}>
      {isMobile ? (
        <Drawer
          placement="left"
          visible={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          bodyStyle={{ padding: 0 }}
          width={280}
          closable={false}
        >
          {sidebar}
        </Drawer>
      ) : (
        sidebar
      )}
      <section className={styles.main}>
        {isMobile && (
          <div className={styles.mobileBar}>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              aria-label="Open chat history"
              onClick={() => setDrawerOpen(true)}
            />
          </div>
        )}
        {isAdmin && (
          <div className={styles.companyBar}>
            <span className={styles.companyBarLabel}>Analyzing:</span>
            <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} />
          </div>
        )}
        {empty ? (
          <div className={styles.welcome}>
            <h2 className={styles.welcomeTitle}>{welcome.title}</h2>
            <SuggestionCards cards={welcome.cards} onPick={handleSend} />
          </div>
        ) : (
          <ConversationPane
            messages={state.messages}
            streaming={state.streaming}
            companies={isAdmin ? companies : undefined}
            onPickCompany={isAdmin ? handlePickCompany : undefined}
          />
        )}
        <InputBox
          disabled={state.streaming}
          streaming={state.streaming}
          onSend={handleSend}
          onStop={stop}
        />
      </section>
    </div>
  );
};

export default ChatPage;
```

- [ ] 2. `index.less` 末尾追加：

```less
.mobileBar {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-bottom: 1px solid @c-line;
}
```

- [ ] 3. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 10：≤768px 响应式样式

**Files:**
- Modify: `src/pages/ai/chat/index.less` / `components/ConversationPane.less` / `components/InputBox.less` / `components/MessageBubble.less` / `components/SuggestionCards.less` / `components/HistorySidebar.less`（各文件末尾追加媒体查询）
- Modify: `src/pages/ai/chat/components/CompanyPicker.tsx`（宽度自适应）

**Steps:**

- [ ] 1. `index.less` 末尾追加：

```less
@media (max-width: 768px) {
  .companyBar {
    flex-wrap: wrap;
    padding: 8px 12px;
  }
  .welcome {
    padding: 16px;
  }
  .welcomeTitle {
    font-size: 18px;
  }
}
```

- [ ] 2. `ConversationPane.less` 末尾追加：

```less
@media (max-width: 768px) {
  .list {
    padding: 12px;
  }
}
```

- [ ] 3. `InputBox.less` 末尾追加：

```less
@media (max-width: 768px) {
  .box {
    padding: 8px 12px 12px;
  }
}
```

- [ ] 4. `MessageBubble.less` 末尾追加：

```less
@media (max-width: 768px) {
  .user,
  .assistant {
    max-width: 92%;
  }
}
```

- [ ] 5. `SuggestionCards.less` 末尾追加：

```less
@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }
}
```

- [ ] 6. `HistorySidebar.less` 末尾追加（抽屉内占满 Drawer body）：

```less
@media (max-width: 768px) {
  .sidebar {
    flex-basis: auto;
    width: 100%;
    border-right: none;
  }
}
```

- [ ] 7. `CompanyPicker.tsx` 的 `style={{ width: 280 }}` 改为 `style={{ width: '100%', maxWidth: 280 }}`（needs_pick 气泡与窄屏 companyBar 内自适应，桌面观感不变）。
- [ ] 8. 运行 `npm run tsc`（预期：与基线一致）

---

## Task 11：视觉 token 对齐 Figma 稿（node 12659-18104）

> **本 Task 是全计划唯一允许的待定项**：具体数值待 Figma 授权后由执行者按稿填入。主题 token 沿用 `src/pages/ai/_shared/tokens.less`（共享 token 文件**不可私改**——chat 专属差异在 chat 自己的 less 内覆盖）；如与稿冲突，以稿为准并在实现说明中记录（设计文档 §5.3）。

**Files:** chat 页全部 less（index / MessageBubble / HistorySidebar / SuggestionCards / InputBox / ConversationPane）

**Steps:**

- [ ] 1. 获取 Figma 两端稿，逐项核对并填入：页面背景、welcomeTitle 字号/字重、气泡配色与圆角、侧栏 item 样式、建议卡样式、输入框形态、disclaimer 样式（具体数值待 Figma 授权后按稿填入）。
- [ ] 2. 对照两端稿分别核验（admin / company 各过一遍欢迎页 + 会话页 + 侧栏）。
- [ ] 3. 运行 `npm run tsc` + `npm run lint:fix`（Stylelint 校验 less）。

---

## 建议提交拆分（最终由主会话与用户确认后执行）

1. 另一会话基线：`feat(chat): sse abort support, title event contract and stop button`
2. Task 1：`feat(chat): rename and delete thread api and service`
3. Task 2：`feat(chat): resolve end type by roleType with hostname fallback`
4. Task 3：`feat(chat): per-end welcome headline and suggestion cards`
5. Task 4–6：`feat(chat): title sync, needs-pick dispatch and thread management hooks`
6. Task 7–9：`feat(chat): sidebar rename/delete, inline company pick and mobile drawer`
7. Task 10–11：`style(chat): responsive layout and figma visual alignment`

> `config/proxy.ts` 永不入提交。

---

## Spec 覆盖对照（自查）

| 设计文档条目 | 状态 |
|---|---|
| §3 前端 title 事件单点 / §5.1 streamSSE signal / streamApi signal / §5.3 InputBox 停止按钮 | ✅ 另一会话基线已实现，不在本计划重做 |
| §5.1 chatApi/chatService rename+delete | Task 1 |
| §2.2 roleType 端判定 | Task 2 |
| §5.3 constants 两端文案 | Task 3 |
| §5.2 needsPick reducer / onNeedsPick / onTitle 上抛 | Task 4、5 |
| §5.2 useChatThreads applyTitle/rename/remove | Task 6 |
| §5.3 HistorySidebar 菜单/折叠/New Chat 始终可见 | Task 7 |
| §5.3 needsPick 内联下拉 | Task 8 |
| §5.3 index.tsx 接线（公司同步/重发/抽屉） | Task 9 |
| §5.3 响应式 + Figma 对齐 | Task 10、11 |
| §6 前端错误行 | Task 1（信封校验）/ Task 6（toast 无乐观更新）/ 基线（AbortError 静默） |
