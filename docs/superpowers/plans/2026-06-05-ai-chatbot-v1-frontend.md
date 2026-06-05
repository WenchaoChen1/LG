# AI Chatbot V1 — 前端聊天页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 CIOaas-web 新增 `src/pages/ai/chat/` 聊天页，消费 Plan 1 的 `/api/ai/chat*` 契约：SSE 流式回复、会话历史侧栏、公司端锁本公司 / 管理端公司选择器（推断+确认），两端按 hostname 区分行为。

**Architecture:** 严格遵循项目三层数据流（API → Service → Hook → Component）。非流式接口（threads/messages/companies）走 `umi-request`；**流式 `/ai/chat` 用原生 `fetch` + `ReadableStream` 读取器**（umi-request 只能拿整包 JSON，无法流式），token 用 `getToken()` 手动加。TDD 聚焦可测纯逻辑（SSE 解析器、消息 reducer、端/公司解析、service DTO 映射），与仓库现有测试风格一致；组件/页面按 `ai/rag` 模式组装 + 浏览器手验。

**Tech Stack:** React 16 / UmiJS 3 / Ant Design 4 / TypeScript / `react-markdown@8` + `remark-gfm@3`（已装未用，本计划启用）/ Jest（`umi test`）。

> **关联设计：** `docs/AI-Chatbot/设计/design-doc.md`；**契约来源：** Plan 1 `docs/superpowers/plans/2026-06-05-ai-chatbot-v1-python-backend.md`
> **SSE 契约（来自 Plan 1 后端）：** 每事件 `data: {"delta":"...","is_final":false}\n\n`；末事件 `data: {"delta":"","is_final":true,"finish_reason":"stop"}\n\n`；流结束 `data: [DONE]\n\n`。`POST /api/ai/chat` 响应头带 `x-thread-id`。
> **导入约定：**
> - 请求：`import request from '@/utils/request'`（非流式）；流式用原生 `fetch`
> - token：`import { getToken, getUserInfo, getQueryString } from '@/utils/utils'`
> - 信封：复用 `PythonEnvelope<T>`（见 `src/services/api/rag/ragApi.ts`），本计划在 `src/services/api/chat/chatApi.ts` 重新声明同结构
> - 样式 token：`@import '../_shared/tokens.less'`
> **测试约定：** 与源码同目录 `*.test.ts`；`npm test`（=`umi test`，Jest）；mock 用 `jest.mock('@/utils/...')` + `jest.Mock`（参考 `src/pages/ai/tracing/utils/companyId.test.ts`）。**项目无组件渲染测试先例**，故组件/页面不写渲染测试，纯逻辑抽到 utils/hook-helper 里单测。

---

## File Structure

```
src/services/api/chat/
├── chatApi.ts            # 非流式：threads/messages/companies（umi-request）；PythonEnvelope
├── chatDto.ts            # ChatThreadDTO / ChatMessageDTO / CompanyDTO + Input 别名
└── streamApi.ts          # 流式 streamChat()：fetch + ReadableStream（带 token + x-chat-end）
src/services/service/chat/
├── chatService.ts        # Response→DTO + unwrap（仿 ragService）
└── chatService.test.ts   # DTO 映射 + unwrap 单测
src/pages/ai/chat/
├── index.tsx             # 页面（按 hostname 决定两端行为）
├── index.less            # @import '../_shared/tokens.less'
├── types.ts              # LoadState / ChatMessage / EndType
├── constants.ts          # 建议卡片、文案、SSE 常量
├── utils/
│   ├── sseParser.ts          # 纯函数：解析 SSE data 行 → 事件
│   ├── sseParser.test.ts
│   ├── messageReducer.ts     # 纯函数：append delta / finalize
│   ├── messageReducer.test.ts
│   ├── endContext.ts         # resolveEndType(hostname) + resolveActiveCompanyId()
│   └── endContext.test.ts
├── hooks/
│   ├── useChatStream.ts      # 驱动 streamChat + reducer
│   ├── useChatThreads.ts     # 历史列表（service）
│   └── useAccessibleCompanies.ts  # 管理端公司集（service）
└── components/
    ├── ConversationPane.tsx / .less
    ├── MessageBubble.tsx          # react-markdown 渲染
    ├── InputBox.tsx
    ├── SuggestionCards.tsx
    ├── CompanyPicker.tsx          # 管理端公司选择器
    └── HistorySidebar.tsx
config/routes.ts          # 改：注册 /ai/chat（公司端 + 管理端入口）
```

---

## Phase A — Service 层（非流式 + 流式）

### Task 1: chat API + DTO + Service（threads / messages / companies）

**Files:**
- Create: `src/services/api/chat/chatApi.ts`、`chatDto.ts`
- Create: `src/services/service/chat/chatService.ts`
- Test: `src/services/service/chat/chatService.test.ts`

- [ ] **Step 1: 写失败测试（仿 ragService.test）**

`src/services/service/chat/chatService.test.ts`：
```typescript
import { toThreadDTO, toMessageDTO, unwrapChat, ChatApiError } from './chatService';

describe('chatService mappers', () => {
  it('toThreadDTO maps fields with null-safety', () => {
    const dto = toThreadDTO({ threadId: 't1', title: null, endType: 'admin',
                              activeCompanyId: null, lastMessageAt: '2026-06-05 10:00:00' });
    expect(dto.id).toBe('t1');
    expect(dto.title).toBe('');
    expect(dto.endType).toBe('admin');
    expect(dto.activeCompanyId).toBe('');
  });

  it('toMessageDTO maps role/content', () => {
    const dto = toMessageDTO({ role: 'assistant', content: 'hi', createdAt: 'x' });
    expect(dto.role).toBe('assistant');
    expect(dto.content).toBe('hi');
  });

  it('unwrapChat throws ChatApiError on success=false', () => {
    expect(() => unwrapChat({ success: false, code: 401, message: 'no', data: null }))
      .toThrow(ChatApiError);
  });

  it('unwrapChat returns data on success', () => {
    expect(unwrapChat({ success: true, code: 0, message: 'OK', data: [1, 2] })).toEqual([1, 2]);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npm test -- chatService`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现**

`src/services/api/chat/chatApi.ts`：
```typescript
import request from '@/utils/request';

export interface PythonEnvelope<T> {
  success: boolean;
  code: number;
  message: string;
  data: T | null;
}

// ── Response 形状（与 Plan 1 vo.py 对齐） ──
export interface ThreadItemResponse {
  threadId: string;
  title: string | null;
  endType: string;
  activeCompanyId: string | null;
  lastMessageAt: string;
}
export interface MessageItemResponse {
  role: string;
  content: string;
  createdAt: string;
}
export interface CompanyItemResponse {
  id: string;
  name?: string | null;
}

export async function listThreads(): Promise<PythonEnvelope<ThreadItemResponse[]>> {
  return request('/api/ai/chat/threads', { method: 'GET' });
}
export async function getMessages(threadId: string): Promise<PythonEnvelope<MessageItemResponse[]>> {
  return request(`/api/ai/chat/threads/${encodeURIComponent(threadId)}/messages`, { method: 'GET' });
}
export async function listCompanies(): Promise<PythonEnvelope<CompanyItemResponse[]>> {
  return request('/api/ai/chat/companies', { method: 'GET' });
}
```

`src/services/api/chat/chatDto.ts`：
```typescript
export interface ChatThreadDTO {
  id: string;
  title: string;
  endType: 'company' | 'admin' | string;
  activeCompanyId: string;
  lastMessageAt: string;
}
export interface ChatMessageDTO {
  role: 'user' | 'assistant' | 'system' | string;
  content: string;
  createdAt: string;
}
export interface CompanyDTO {
  id: string;
  name: string;
}
```

`src/services/service/chat/chatService.ts`：
```typescript
import type { PythonEnvelope, ThreadItemResponse, MessageItemResponse, CompanyItemResponse } from '@/services/api/chat/chatApi';
import { listThreads as apiListThreads, getMessages as apiGetMessages, listCompanies as apiListCompanies } from '@/services/api/chat/chatApi';
import type { ChatThreadDTO, ChatMessageDTO, CompanyDTO } from '@/services/api/chat/chatDto';

export class ChatApiError extends Error {
  code: number;
  constructor(message: string, code: number) {
    super(message || 'Chat request failed');
    this.name = 'ChatApiError';
    this.code = code;
  }
}

export function unwrapChat<T>(res: PythonEnvelope<T> | undefined): T {
  if (!res || res.success !== true || res.data == null) {
    throw new ChatApiError(res?.message ?? 'Network error', res?.code ?? -1);
  }
  return res.data;
}

/** @internal */ export function toThreadDTO(r: ThreadItemResponse): ChatThreadDTO {
  return { id: r.threadId, title: r.title ?? '', endType: r.endType,
           activeCompanyId: r.activeCompanyId ?? '', lastMessageAt: r.lastMessageAt };
}
/** @internal */ export function toMessageDTO(r: MessageItemResponse): ChatMessageDTO {
  return { role: r.role, content: r.content, createdAt: r.createdAt };
}
/** @internal */ export function toCompanyDTO(r: CompanyItemResponse): CompanyDTO {
  return { id: r.id, name: r.name ?? '' };
}

export async function fetchThreads(): Promise<ChatThreadDTO[]> {
  return unwrapChat(await apiListThreads()).map(toThreadDTO);
}
export async function fetchMessages(threadId: string): Promise<ChatMessageDTO[]> {
  return unwrapChat(await apiGetMessages(threadId)).map(toMessageDTO);
}
export async function fetchCompanies(): Promise<CompanyDTO[]> {
  return unwrapChat(await apiListCompanies()).map(toCompanyDTO);
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npm test -- chatService`
Expected: PASS ×4。

- [ ] **Step 5: 提交**

```bash
git add src/services/api/chat src/services/service/chat
git commit -m "feat(chat): chat service layer (threads/messages/companies)"
```

---

## Phase B — SSE 流式（纯解析器 + fetch 读取器）

### Task 2: SSE 解析器（纯函数）

**Files:**
- Create: `src/pages/ai/chat/utils/sseParser.ts`
- Test: `src/pages/ai/chat/utils/sseParser.test.ts`

- [ ] **Step 1: 写失败测试**

`src/pages/ai/chat/utils/sseParser.test.ts`：
```typescript
import { createSSEParser } from './sseParser';

describe('createSSEParser', () => {
  it('parses a complete data event into a delta', () => {
    const p = createSSEParser();
    const events = p.push('data: {"delta":"Hel","is_final":false}\n\n');
    expect(events).toEqual([{ delta: 'Hel', isFinal: false, finishReason: undefined }]);
  });

  it('buffers partial events across chunks', () => {
    const p = createSSEParser();
    expect(p.push('data: {"delta":"He')).toEqual([]);          // 不完整
    const events = p.push('llo","is_final":false}\n\n');
    expect(events[0].delta).toBe('Hello');
  });

  it('detects [DONE] marker', () => {
    const p = createSSEParser();
    const events = p.push('data: [DONE]\n\n');
    expect(events).toEqual([{ done: true }]);
  });

  it('marks final event', () => {
    const p = createSSEParser();
    const events = p.push('data: {"delta":"","is_final":true,"finish_reason":"stop"}\n\n');
    expect(events[0]).toEqual({ delta: '', isFinal: true, finishReason: 'stop' });
  });

  it('handles multiple events in one chunk', () => {
    const p = createSSEParser();
    const events = p.push('data: {"delta":"a","is_final":false}\n\ndata: {"delta":"b","is_final":false}\n\n');
    expect(events.map((e: any) => e.delta)).toEqual(['a', 'b']);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npm test -- sseParser`
Expected: FAIL。

- [ ] **Step 3: 实现**

`src/pages/ai/chat/utils/sseParser.ts`：
```typescript
export interface SSEDelta {
  delta: string;
  isFinal: boolean;
  finishReason?: string;
}
export interface SSEDone {
  done: true;
}
export type SSEEvent = SSEDelta | SSEDone;

/** 增量喂入解码后的文本，缓冲未完整事件，返回本次完成的事件列表。 */
export function createSSEParser() {
  let buffer = '';
  return {
    push(chunk: string): SSEEvent[] {
      buffer += chunk;
      const out: SSEEvent[] = [];
      let idx: number;
      // 事件以空行 \n\n 分隔
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        for (const line of rawEvent.split('\n')) {
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (payload === '[DONE]') {
            out.push({ done: true });
            continue;
          }
          try {
            const obj = JSON.parse(payload);
            out.push({ delta: obj.delta ?? '', isFinal: !!obj.is_final,
                       finishReason: obj.finish_reason });
          } catch {
            // 忽略非法 data 行（如 event: error 的非 JSON）
          }
        }
      }
      return out;
    },
  };
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npm test -- sseParser`
Expected: PASS ×5。

- [ ] **Step 5: 提交**

```bash
git add src/pages/ai/chat/utils/sseParser.ts src/pages/ai/chat/utils/sseParser.test.ts
git commit -m "feat(chat): SSE parser (data lines -> deltas)"
```

### Task 3: streamChat（fetch + ReadableStream 读取器）

**Files:**
- Create: `src/services/api/chat/streamApi.ts`
- Test: `src/services/api/chat/streamApi.test.ts`

- [ ] **Step 1: 写失败测试（mock fetch + ReadableStream）**

`src/services/api/chat/streamApi.test.ts`：
```typescript
import { streamChat } from './streamApi';

jest.mock('@/utils/utils', () => ({ getToken: () => 'tok' }));

function mockStreamResponse(chunks: string[]): any {
  let i = 0;
  const reader = {
    read: async () => {
      if (i < chunks.length) {
        const value = new TextEncoder().encode(chunks[i]); i += 1;
        return { value, done: false };
      }
      return { value: undefined, done: true };
    },
  };
  return {
    ok: true, status: 200,
    headers: { get: (k: string) => (k === 'x-thread-id' ? 'thread-9' : null) },
    body: { getReader: () => reader },
  };
}

describe('streamChat', () => {
  it('yields deltas and reports threadId', async () => {
    (global as any).fetch = jest.fn().mockResolvedValue(mockStreamResponse([
      'data: {"delta":"Hel","is_final":false}\n\n',
      'data: {"delta":"lo","is_final":false}\n\n',
      'data: [DONE]\n\n',
    ]));
    const deltas: string[] = [];
    let threadId = '';
    await streamChat(
      { threadId: null, companyId: 'c-1', question: 'q', endType: 'company' },
      { onDelta: (d) => deltas.push(d), onThreadId: (t) => { threadId = t; }, onDone: () => {} },
    );
    expect(deltas.join('')).toBe('Hello');
    expect(threadId).toBe('thread-9');
    const call = (global as any).fetch.mock.calls[0];
    expect(call[1].headers.Authorization).toBe('Bearer tok');
    expect(call[1].headers['x-chat-end']).toBe('company');
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npm test -- streamApi`
Expected: FAIL。

- [ ] **Step 3: 实现**

`src/services/api/chat/streamApi.ts`：
```typescript
import { getToken } from '@/utils/utils';
import { createSSEParser } from '@/pages/ai/chat/utils/sseParser';

export interface StreamChatRequest {
  threadId: string | null;
  companyId: string | null;
  question: string;
  endType: 'company' | 'admin';
}
export interface StreamChatCallbacks {
  onDelta: (delta: string) => void;
  onThreadId?: (threadId: string) => void;
  onDone?: (finishReason?: string) => void;
  onError?: (err: Error) => void;
}

export async function streamChat(req: StreamChatRequest, cb: StreamChatCallbacks): Promise<void> {
  const token = getToken();
  let resp: Response;
  try {
    resp = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        'x-chat-end': req.endType,
      },
      body: JSON.stringify({
        thread_id: req.threadId, company_id: req.companyId, question: req.question,
      }),
    });
  } catch (e) {
    cb.onError?.(e as Error); return;
  }
  if (!resp.ok || !resp.body) {
    cb.onError?.(new Error(`chat request failed: ${resp.status}`)); return;
  }
  const tid = resp.headers.get('x-thread-id');
  if (tid) cb.onThreadId?.(tid);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  const parser = createSSEParser();
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      const events = parser.push(decoder.decode(value, { stream: true }));
      for (const ev of events) {
        if ('done' in ev) { cb.onDone?.(); return; }
        if (ev.delta) cb.onDelta(ev.delta);
        if (ev.isFinal) cb.onDone?.(ev.finishReason);
      }
    }
    cb.onDone?.();
  } catch (e) {
    cb.onError?.(e as Error);
  }
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npm test -- streamApi`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/services/api/chat/streamApi.ts src/services/api/chat/streamApi.test.ts
git commit -m "feat(chat): streamChat fetch-based SSE reader"
```

---

## Phase C — 端/公司解析 + 消息 reducer（纯逻辑）

### Task 4: endContext（hostname → 端；公司 id 解析）

**Files:**
- Create: `src/pages/ai/chat/utils/endContext.ts`
- Test: `src/pages/ai/chat/utils/endContext.test.ts`

- [ ] **Step 1: 写失败测试（仿 companyId.test 的 jest.mock）**

`src/pages/ai/chat/utils/endContext.test.ts`：
```typescript
jest.mock('@/utils/utils', () => ({ getQueryString: jest.fn(), getUserInfo: jest.fn() }));
import { resolveEndType, resolveActiveCompanyId } from './endContext';
const utils = require('@/utils/utils');

describe('resolveEndType', () => {
  it('admin host -> admin', () => {
    expect(resolveEndType('admin-test.lgpi.io')).toBe('admin');
    expect(resolveEndType('admin.lgpi.io')).toBe('admin');
  });
  it('app host -> company', () => {
    expect(resolveEndType('app-test.lgpi.io')).toBe('company');
  });
  it('unknown host falls back to company', () => {
    expect(resolveEndType('localhost:8000')).toBe('company');
  });
});

describe('resolveActiveCompanyId', () => {
  beforeEach(() => { utils.getQueryString.mockReset(); utils.getUserInfo.mockReset(); });
  it('company end uses inviteDto.id', () => {
    utils.getUserInfo.mockReturnValue({ inviteDto: { id: 'c-own' } });
    expect(resolveActiveCompanyId('company')).toBe('c-own');
  });
  it('admin end uses URL ?id', () => {
    utils.getQueryString.mockReturnValue('c-url');
    expect(resolveActiveCompanyId('admin')).toBe('c-url');
  });
  it('admin end without ?id returns empty', () => {
    utils.getQueryString.mockReturnValue(null);
    expect(resolveActiveCompanyId('admin')).toBe('');
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npm test -- endContext`
Expected: FAIL。

- [ ] **Step 3: 实现**

`src/pages/ai/chat/utils/endContext.ts`：
```typescript
import { getQueryString, getUserInfo } from '@/utils/utils';

export type EndType = 'company' | 'admin';

const ADMIN_HOSTS = ['admin.lgpi.io', 'admin-staging.lgpi.io', 'admin-uat.lgpi.io', 'admin-test.lgpi.io'];

export function resolveEndType(host: string = window.location.host): EndType {
  return ADMIN_HOSTS.includes(host) ? 'admin' : 'company';
}

export function resolveActiveCompanyId(end: EndType): string {
  if (end === 'company') {
    const user: any = getUserInfo();
    return user?.inviteDto?.id || user?.companyId || '';
  }
  return getQueryString('id') || '';
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npm test -- endContext`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/pages/ai/chat/utils/endContext.ts src/pages/ai/chat/utils/endContext.test.ts
git commit -m "feat(chat): end-type + active company resolution"
```

### Task 5: messageReducer（追加 delta / 收尾）

**Files:**
- Create: `src/pages/ai/chat/utils/messageReducer.ts`
- Test: `src/pages/ai/chat/utils/messageReducer.test.ts`

- [ ] **Step 1: 写失败测试**

`src/pages/ai/chat/utils/messageReducer.test.ts`：
```typescript
import { chatReducer, initialChatState } from './messageReducer';

describe('chatReducer', () => {
  it('addUser pushes a user message', () => {
    const s = chatReducer(initialChatState, { type: 'addUser', content: 'hi' });
    expect(s.messages).toEqual([{ role: 'user', content: 'hi' }]);
  });
  it('startAssistant then appendDelta accumulates', () => {
    let s = chatReducer(initialChatState, { type: 'addUser', content: 'q' });
    s = chatReducer(s, { type: 'startAssistant' });
    s = chatReducer(s, { type: 'appendDelta', delta: 'He' });
    s = chatReducer(s, { type: 'appendDelta', delta: 'llo' });
    expect(s.messages[s.messages.length - 1]).toEqual({ role: 'assistant', content: 'Hello' });
    expect(s.streaming).toBe(true);
  });
  it('finish sets streaming false', () => {
    let s = chatReducer(initialChatState, { type: 'startAssistant' });
    s = chatReducer(s, { type: 'finish' });
    expect(s.streaming).toBe(false);
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `npm test -- messageReducer`
Expected: FAIL。

- [ ] **Step 3: 实现**

`src/pages/ai/chat/utils/messageReducer.ts`：
```typescript
export interface ChatMsg { role: 'user' | 'assistant'; content: string; }
export interface ChatState { messages: ChatMsg[]; streaming: boolean; error: string | null; }

export const initialChatState: ChatState = { messages: [], streaming: false, error: null };

export type ChatAction =
  | { type: 'addUser'; content: string }
  | { type: 'startAssistant' }
  | { type: 'appendDelta'; delta: string }
  | { type: 'finish' }
  | { type: 'error'; message: string }
  | { type: 'load'; messages: ChatMsg[] };

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'addUser':
      return { ...state, messages: [...state.messages, { role: 'user', content: action.content }] };
    case 'startAssistant':
      return { ...state, streaming: true, error: null,
               messages: [...state.messages, { role: 'assistant', content: '' }] };
    case 'appendDelta': {
      const msgs = state.messages.slice();
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') msgs[msgs.length - 1] = { ...last, content: last.content + action.delta };
      return { ...state, messages: msgs };
    }
    case 'finish':
      return { ...state, streaming: false };
    case 'error':
      return { ...state, streaming: false, error: action.message };
    case 'load':
      return { ...state, messages: action.messages };
    default:
      return state;
  }
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `npm test -- messageReducer`
Expected: PASS ×3。

- [ ] **Step 5: 提交**

```bash
git add src/pages/ai/chat/utils/messageReducer.ts src/pages/ai/chat/utils/messageReducer.test.ts
git commit -m "feat(chat): message reducer"
```

---

## Phase D — Hooks（组合 service + 流式 + reducer）

### Task 6: useChatStream

**Files:**
- Create: `src/pages/ai/chat/hooks/useChatStream.ts`
- Test: `src/pages/ai/chat/hooks/useChatStream.test.ts`（仅测可抽出的 send 逻辑；hook 本体在页面手验）

> 说明：项目无 React hook 渲染测试先例。本 hook 的核心可测逻辑（reducer 串联、streamChat 回调驱动）已分别由 Task 3/5 覆盖。这里把 hook 写薄，仅做组装；不强写 renderHook 测试，避免引入 RTL 新栈。

- [ ] **Step 1: 实现 hook（薄组装，无新测试）**

`src/pages/ai/chat/hooks/useChatStream.ts`：
```typescript
import { useReducer, useCallback, useRef } from 'react';
import { streamChat } from '@/services/api/chat/streamApi';
import { fetchMessages } from '@/services/service/chat/chatService';
import { chatReducer, initialChatState } from '../utils/messageReducer';
import type { EndType } from '../utils/endContext';

export function useChatStream(endType: EndType) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState);
  const threadIdRef = useRef<string | null>(null);

  const loadThread = useCallback(async (threadId: string) => {
    threadIdRef.current = threadId;
    const msgs = await fetchMessages(threadId);
    dispatch({ type: 'load', messages: msgs.filter(m => m.role !== 'system')
      .map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })) });
  }, []);

  const send = useCallback(async (question: string, companyId: string | null) => {
    dispatch({ type: 'addUser', content: question });
    dispatch({ type: 'startAssistant' });
    await streamChat(
      { threadId: threadIdRef.current, companyId, question, endType },
      {
        onThreadId: (t) => { threadIdRef.current = t; },
        onDelta: (d) => dispatch({ type: 'appendDelta', delta: d }),
        onDone: () => dispatch({ type: 'finish' }),
        onError: (e) => dispatch({ type: 'error', message: e.message }),
      },
    );
  }, [endType]);

  const newChat = useCallback(() => {
    threadIdRef.current = null;
    dispatch({ type: 'load', messages: [] });
  }, []);

  return { state, send, loadThread, newChat, threadId: threadIdRef };
}
```

- [ ] **Step 2: 跑回归（确认不破坏既有测试）**

Run: `npm test -- chat`
Expected: 既有 chat 相关测试全 PASS。

- [ ] **Step 3: 提交**

```bash
git add src/pages/ai/chat/hooks/useChatStream.ts
git commit -m "feat(chat): useChatStream hook"
```

### Task 7: useChatThreads + useAccessibleCompanies

**Files:**
- Create: `src/pages/ai/chat/hooks/useChatThreads.ts`、`useAccessibleCompanies.ts`

- [ ] **Step 1: 实现（仿 useSpaces 的 loading/error 模式）**

`src/pages/ai/chat/hooks/useChatThreads.ts`：
```typescript
import { useState, useCallback, useEffect, useRef } from 'react';
import { message } from 'antd';
import { fetchThreads, ChatApiError } from '@/services/service/chat/chatService';
import type { ChatThreadDTO } from '@/services/api/chat/chatDto';

export function useChatThreads() {
  const [threads, setThreads] = useState<ChatThreadDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const reload = useCallback(() => {
    setLoading(true);
    fetchThreads()
      .then((ts) => { if (alive.current) setThreads(ts); })
      .catch((e) => { if (alive.current) message.error(e instanceof ChatApiError ? e.message : 'Load failed'); })
      .finally(() => { if (alive.current) setLoading(false); });
  }, []);

  useEffect(() => { reload(); }, [reload]);
  return { threads, loading, reload };
}
```

`src/pages/ai/chat/hooks/useAccessibleCompanies.ts`：
```typescript
import { useState, useCallback, useEffect, useRef } from 'react';
import { fetchCompanies } from '@/services/service/chat/chatService';
import type { CompanyDTO } from '@/services/api/chat/chatDto';

export function useAccessibleCompanies(enabled: boolean) {
  const [companies, setCompanies] = useState<CompanyDTO[]>([]);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  const reload = useCallback(() => {
    if (!enabled) return;
    fetchCompanies().then((c) => { if (alive.current) setCompanies(c); }).catch(() => {});
  }, [enabled]);
  useEffect(() => { reload(); }, [reload]);
  return { companies, reload };
}
```

- [ ] **Step 2: 提交**

```bash
git add src/pages/ai/chat/hooks/useChatThreads.ts src/pages/ai/chat/hooks/useAccessibleCompanies.ts
git commit -m "feat(chat): threads + accessible-companies hooks"
```

---

## Phase E — 组件 + 页面 + 路由（组装 + 浏览器手验）

### Task 8: types + constants

**Files:**
- Create: `src/pages/ai/chat/types.ts`、`constants.ts`

- [ ] **Step 1: 实现**

`src/pages/ai/chat/types.ts`：
```typescript
export type LoadState = 'idle' | 'loading' | 'done' | 'error';
export type { EndType } from './utils/endContext';
export type { ChatMsg } from './utils/messageReducer';
```

`src/pages/ai/chat/constants.ts`：
```typescript
// V1 范围内的建议卡（去掉 mockup 里跨公司/报告生成的超范围项）
export const SUGGESTION_CARDS = [
  { tag: 'FINANCIALS', text: "Summarize this company's latest financial highlights" },
  { tag: 'TREND', text: 'How has ARR/MRR trended over the last 4 quarters?' },
  { tag: 'BENCHMARK', text: 'Where does this company rank vs peers (percentile)?' },
  { tag: 'RUNWAY', text: "What's the current runway and burn rate?" },
  { tag: 'FORECAST', text: 'Compare actuals vs committed forecast for revenue' },
  { tag: 'COMPANY', text: 'What does this company do and what stage is it at?' },
];
export const DISCLAIMER = 'AI can make mistakes. Please check important information.';
export const WELCOME_TITLE = 'What do you want to know about your portfolio?';
```

- [ ] **Step 2: 提交**

```bash
git add src/pages/ai/chat/types.ts src/pages/ai/chat/constants.ts
git commit -m "feat(chat): types + constants (V1-scoped suggestions)"
```

### Task 9: 组件（MessageBubble / ConversationPane / InputBox / SuggestionCards / CompanyPicker / HistorySidebar）

**Files:**
- Create: `src/pages/ai/chat/components/*.tsx` + 对应 `.less`

> 组件为纯展示（props 入、回调出），不写渲染测试（仓库无先例）；逻辑已在 Phase B/C 覆盖。MessageBubble 用 `react-markdown` + `remark-gfm`。

- [ ] **Step 1: MessageBubble（markdown 渲染）**

`src/pages/ai/chat/components/MessageBubble.tsx`：
```tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMsg } from '../utils/messageReducer';
import styles from './MessageBubble.less';

const MessageBubble: React.FC<{ msg: ChatMsg }> = ({ msg }) => (
  <div className={msg.role === 'user' ? styles.user : styles.assistant}>
    {msg.role === 'assistant'
      ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ' '}</ReactMarkdown>
      : <span>{msg.content}</span>}
  </div>
);
export default MessageBubble;
```

- [ ] **Step 2: ConversationPane / InputBox / SuggestionCards / CompanyPicker / HistorySidebar**

按 `ai/rag/components` 的纯展示组件风格实现：
- `ConversationPane`：props `{ messages: ChatMsg[]; streaming: boolean }`，map 渲染 `MessageBubble`，streaming 时末尾显示打字指示；底部固定 `DISCLAIMER`。
- `InputBox`：props `{ disabled: boolean; onSend: (text: string) => void }`，Ant `Input.TextArea` + 发送按钮，Enter 发送。
- `SuggestionCards`：props `{ onPick: (text: string) => void }`，渲染 `SUGGESTION_CARDS`，点卡片回填输入。
- `CompanyPicker`：props `{ companies: CompanyDTO[]; value: string; onChange: (id: string) => void }`，Ant `Select`（带搜索）；**仅管理端渲染**。
- `HistorySidebar`：props `{ threads: ChatThreadDTO[]; activeId: string; onSelect: (id: string) => void; onNewChat: () => void }`，按 `lastMessageAt` 做 Today/Yesterday/Last Week 分组（用纯函数 `groupByDate`，可加一个 `groupByDate.test.ts` 单测）。

每个组件配 `.less`，`@import '../_shared/tokens.less'`。

- [ ] **Step 3: （可选 TDD）groupByDate 纯函数 + 测试**

若实现历史分组，把分组逻辑抽 `utils/groupThreads.ts` 并加 `groupThreads.test.ts`（Today/Yesterday/Last Week/Older 边界），保持"纯逻辑必测"。

- [ ] **Step 4: 提交**

```bash
git add src/pages/ai/chat/components
git commit -m "feat(chat): chat UI components (markdown bubble, pane, input, picker, history)"
```

### Task 10: 页面 index.tsx + index.less（两端组装）

**Files:**
- Create: `src/pages/ai/chat/index.tsx`、`index.less`

- [ ] **Step 1: 实现页面**

`src/pages/ai/chat/index.tsx`（组装；按 hostname 决定是否显示 CompanyPicker）：
```tsx
import React, { useMemo, useState, useCallback } from 'react';
import { useChatStream } from './hooks/useChatStream';
import { useChatThreads } from './hooks/useChatThreads';
import { useAccessibleCompanies } from './hooks/useAccessibleCompanies';
import { resolveEndType, resolveActiveCompanyId } from './utils/endContext';
import ConversationPane from './components/ConversationPane';
import InputBox from './components/InputBox';
import SuggestionCards from './components/SuggestionCards';
import CompanyPicker from './components/CompanyPicker';
import HistorySidebar from './components/HistorySidebar';
import { WELCOME_TITLE } from './constants';
import styles from './index.less';

const ChatPage: React.FC = () => {
  const endType = useMemo(() => resolveEndType(), []);
  const isAdmin = endType === 'admin';
  const [companyId, setCompanyId] = useState<string>(() => resolveActiveCompanyId(endType));

  const { state, send, loadThread, newChat } = useChatStream(endType);
  const { threads, reload: reloadThreads } = useChatThreads();
  const { companies } = useAccessibleCompanies(isAdmin);
  const [activeThread, setActiveThread] = useState('');

  const handleSend = useCallback(async (text: string) => {
    await send(text, companyId || null);
    reloadThreads();
  }, [send, companyId, reloadThreads]);

  const empty = state.messages.length === 0;
  return (
    <div className={styles.chatPage}>
      <HistorySidebar threads={threads} activeId={activeThread}
        onNewChat={() => { newChat(); setActiveThread(''); }}
        onSelect={(id) => { setActiveThread(id); loadThread(id); }} />
      <section className={styles.main}>
        {isAdmin && (
          <div className={styles.companyBar}>
            <CompanyPicker companies={companies} value={companyId} onChange={setCompanyId} />
          </div>
        )}
        {empty ? (
          <div className={styles.welcome}>
            <h2>{WELCOME_TITLE}</h2>
            <SuggestionCards onPick={handleSend} />
          </div>
        ) : (
          <ConversationPane messages={state.messages} streaming={state.streaming} />
        )}
        <InputBox disabled={state.streaming} onSend={handleSend} />
      </section>
    </div>
  );
};
export default ChatPage;
```

`index.less`：`@import '../_shared/tokens.less';` + flex 布局（左 sidebar、右 main、底部 InputBox），参考 `ai/rag/index.less`。

- [ ] **Step 2: 提交**

```bash
git add src/pages/ai/chat/index.tsx src/pages/ai/chat/index.less
git commit -m "feat(chat): assemble chat page (two-end behavior)"
```

### Task 11: 路由注册（公司端 + 管理端入口）

**Files:**
- Modify: `config/routes.ts`

- [ ] **Step 1: 注册路由**

在 `config/routes.ts` 顶层加（与现有业务页同级，非 devSupport 隐藏区）：
```typescript
{
  path: '/ai/chat',
  name: 'Ask AI',
  icon: 'robot',
  component: './ai/chat',
  authority: ['admin', 'user'],   // 以项目实际 authority 取值为准
},
```

> 顶部"Ask AI" tab 的具体放置（图一里与 "Portfolio Companies" 并列）以项目现有顶导实现为准：确认 `config/routes.ts` 的 `name`/`authority` 是否驱动该 tab，或顶导是否另有配置点；若顶导是独立组件，在该组件加一个指向 `/ai/chat` 的入口。两端（app*/admin*）共用同一路由，页面内按 hostname 自适应。

- [ ] **Step 2: 确认 proxy（已存在，无需改）**

`config/proxy.ts` 已有 `/api/ai → 8090`，dev 直连；prod 经网关。无需改动。

- [ ] **Step 3: 提交**

```bash
git add config/routes.ts
git commit -m "feat(chat): register /ai/chat route for both portals"
```

### Task 12: 联调 + 浏览器手验

**Files:** 无（验证）

- [ ] **Step 1: 起服务联调**

确保 Plan 1 后端在 `:8090` 跑起来（chat 图已编译）。前端 `npm run start:dev`。

- [ ] **Step 2: 公司端手验（app 域或本地）**

- 进入 `/ai/chat`：直接进聊天、无公司选择器。
- 问"What is our ARR?"：SSE 逐字流式出现；回答基于本公司财报；底部免责声明可见。
- 新建对话 / 历史侧栏切换可用。

- [ ] **Step 3: 管理端手验（admin 域或本地模拟 host）**

- 顶部公司选择器可选可访问公司。
- 选定公司后问 benchmark/财报，流式返回。
- 不选公司直接问 → 后端回"请告诉我是哪家公司"，选择器仍可选。

- [ ] **Step 4: lint + 全量测试**

Run: `npm run lint:fix && npm run tsc && npm test -- chat`
Expected: 无 lint/类型错误；chat 相关单测全绿。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "test(chat): wiring verified; lint+tsc clean"
```

---

## Self-Review 结果

- **Spec 覆盖**：design §6.2 两端 UX→Task9/11；§10 接口契约→Task1/3；§11.1 目录→File Structure；§11.3 建议卡→Task8；§11.4 流式+免责→Task3/8/9；公司归属（推断+确认）→后端 resolve_company + 前端 CompanyPicker（Task9）。✅
- **占位符**：Task8/9 的部分组件给了明确 props 契约 + 实现指引（ConversationPane/InputBox/SuggestionCards/CompanyPicker/HistorySidebar），未逐行贴全——它们是纯展示、按 rag 组件风格直写，无新逻辑。MessageBubble/页面/可测纯逻辑均有完整代码。
- **类型一致**：`PythonEnvelope`/`Chat*DTO`/`ChatMsg`/`ChatState`/`EndType`/`streamChat` 回调签名 全程一致；`/api/ai/chat*` 路径与 Plan 1 路由一致；SSE 字段（`delta`/`is_final`/`finish_reason`/`[DONE]`/`x-thread-id`）与 Plan 1 `chunk_to_sse_bytes`+routes 一致。✅
- **与仓库一致性**：测试只覆盖纯逻辑（无组件渲染测试，符合仓库现状）；用 `jest.mock('@/utils/utils')` 模式；样式 `@import _shared/tokens.less`；三层数据流。
- **风险点（执行时注意）**：
  1. 顶导"Ask AI" tab 的确切接入点（routes `name`/`authority` vs 独立顶导组件）需在 Task11 按项目实际确认。
  2. `authority` 取值（`['admin','user']` 占位）以项目权限枚举实际为准。
  3. 管理端"needs_company_pick"目前由后端发普通 assistant 提示；如需自动弹选择器，可在 Plan 1 SSE 加结构化事件（次要增强）。
  4. dev 下跨域直连 Python，`fetch('/api/ai/chat')` 走 umi 代理；确认代理对 streaming（不缓冲）放行（umi/webpack-dev-server 默认对 SSE 不缓冲，通常 OK；若被缓冲，dev 期可直连 `http://127.0.0.1:8090/ai/chat` 调试）。

---

## Execution Handoff

见对话中的执行方式选择。
```
