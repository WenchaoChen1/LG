# 方案：切换会话 / 刷新页面后恢复 SSE 流式（resume-on-switch / resume-on-refresh）

> 关联文档：[design-doc](../../AI-Chatbot/设计/design-doc.md)、[SSE 事件契约](../specs/2026-06-11-sse-event-contract-design.md)、[前端实现计划](./2026-06-05-ai-chatbot-v1-frontend.md)、[Python 后端实现计划](./2026-06-05-ai-chatbot-v1-python-backend.md)
>
> 状态：方案（不含代码改动）。本文经多视角对抗审查（竞态/串话、后端缓冲生命周期、双渲染、范围/UX/边界）后定稿。
> 性质：**纯前端修复**，后端 0 改动。

---

## 1. 问题与复现

| # | 复现步骤 | 现象 |
|---|----------|------|
| ① | 新建会话 A 提问（A 开始流式）→ 新建会话 B 提问 → 切回 A | A 不再继续输出，流断了；只看到切走那一刻的内容 |
| ② | 上述断流后刷新页面，重新进入 A | 仍不继续输出；**只有最后**（后端跑完落库后）才一次性显示完整答案 |

数据不丢、不重新生成（后端解耦照跑、落库）。缺的是「切走 / 刷新后回到 A 还能把流式接上」。

---

## 2. 根因（已对照真实代码确认）

**① 切到 B → A 断**

- `newChat()`、`loadThread()`、`send()` 进入时都 `abortRef.current?.abort()`（[useChatStream.ts:30](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)、[:174](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）。
- `streamApi` 的断线续传循环条件是 `while (!terminal && !options?.signal?.aborted && streamId && retries < MAX_RESUME_RETRIES)`（[streamApi.ts:136](../../../CIOaas-web/src/services/api/chat/streamApi.ts)）。`abort()` 后 `signal.aborted === true`，**续传循环恒不触发**——这是「用户主动放弃」语义，设计如此。
- 切回 A 走 `loadThread(A)` → `fetchMessages` 读 DB，**完全不走 `/subscribe` 续传**。

**② 刷新只在最后显示**

- `streamId` 只活在 `streamChat` 的闭包变量 + `streamIdRef`（内存，[useChatStream.ts:22](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）。刷新即丢。
- 刷新进 A → `handleSelectThread` → `loadThread` 读 DB（[index.tsx:210](../../../CIOaas-web/src/pages/ai/chat/index.tsx)）。后端仍在生成时 DB 只有已落库部分（通常为空，见下 §3 第 4 条）；等后端跑完再读才完整 → 「只有最后才显示」。

**关键结论**：`streamApi` **已经实现**了基于 `GET /api/ai/sse/subscribe/{streamId}` + `Last-Event-ID` 的续传，只是

1. 续传仅对「同一次 `streamChat` 调用里的网络抖动」生效（reader 抛错、未 abort）；
2. `streamId` 不持久化，切走 / 刷新就丢。

所以**整个修复都在前端**，且无需碰已有的网络抖动续传逻辑。

---

## 3. 后端能力确认（方案可行性的基石）

深读 `CIOaas-python/source/sse/`（broker / runner / routes / stop_signal）后确认 —— 这些**已存在、无需改动**：

| # | 事实 | 证据 |
|---|------|------|
| 1 | 每条流的缓冲存在 **Redis list** `sse:buf:{stream_id}`（RPUSH / LRANGE），**非进程内存** → 跨 worker / pod / 进程重启可读 | `broker.py` `_BUF_KEY_TMPL`、RPUSH/EXPIRE |
| 2 | 缓冲 **TTL = 3600s（1 小时）**；只随 Redis TTL 过期淘汰，**DONE / stop 都不立即清** | `broker.py:16` `_TTL_SECONDS = 3600` |
| 3 | `Last-Event-ID: N` → 后端从 `start = int(N) + 1` 重放；**无该头则从 index 0 重放整条流** | `routes.py:143`、`get_frames(start)` |
| 4 | **流已结束（DONE 已发）也能完整重放**（含终结帧 `[DONE]`），只要还在 1h 内 | `broker.py`（DONE 帧与普通帧一样留在 list） |
| 5 | stream_id 未知/过期：**HTTP 200**，10s 空窗（`_EMPTY_GRACE`）后下发 SSE `error` 帧（**不是 404**） | `routes.py:43`、`:85` |
| 6 | 后台生成与 `POST /stream` 连接**完全解耦**：POST 发完首帧 `event: stream` 即返回，生成任务 fire-and-forget 跑完并持续写 Redis；客户端断开不影响生成 | `routes.py`、`runner.py`（任务held 在 `_RUNNING`） |
| 7 | event id 为**单调递增整数**（每帧 +1，`id: {seq}`），与 W3C SSE / `Last-Event-ID` 一致 | `runner.py` `_with_id` |
| 8 | 生成期间**不增量落库** assistant 文本：`fetchMessages` 只返回已完成轮次的最终内容（进行中那一轮 DB 里没有） | `chatService.fetchMessages` → `getMessages`（[chatApi.ts:41](../../../CIOaas-web/src/services/api/chat/chatApi.ts)） |

第 4、第 8 条是方案正确性的两块基石：**DB（已完成轮次）与缓冲（进行中那一轮）互不重叠**，因此「重放 from 0」不会和 DB 内容重复计数（见 §6）。

> 网关注意（既有约束，非本次引入）：Java 网关当前无 `/api/ai/sse/**` 显式路由（只有 `/api/web/**`），且有 **120s 全局响应超时**。续传复用的是 live 流式**已经在用**的同一条 `/api/ai/sse/subscribe` 路径——live 能流，续传就能流，本方案不新增任何网关配置。120s 超时对**单条** subscribe 连接的截断由 §7 的重连循环兜底。

---

## 4. 方案总览

> 一句话：**切走/刷新时只 abort 前端连接、但把 `streamId` 按 threadId 持久化；回到该会话时，若有「在跑的流」记录就 `subscribe` 续传，否则才读 DB。** 后台生成本来就一直在跑、一直在写 Redis，所以「断了再回来续」零丢失。

改动面（全部前端）：

1. **新文件** `src/pages/ai/chat/utils/streamResume.ts` —— sessionStorage 持久化工具（~40 行，纯函数）。
2. **`streamApi.ts`** —— 把现有续传循环抽成可导出的 `subscribeStream(streamId, cb, { signal, fromLastEventId? })`；`streamChat` 内部复用，行为不变。
3. **`useChatStream.ts`** —— 写/清持久化记录；新增 `enterThread(threadId)`。
4. **`index.tsx`** —— `handleSelectThread` 调 `enterThread` 取代裸 `loadThread`；删会话 / newChat 时清记录。

**保持单流 Hook 设计**：不为「切走的 A」维持后台活跃流（那要多路复用 per-thread 状态，违反单流设计与 YAGNI）。切走照常 abort，靠**持久化 + 回来时 subscribe** 续上即可——因为 Redis 缓冲全程兜底。

---

## 5. 持久化设计

### 5.1 记录结构（去掉冗余字段）

```ts
// streamResume.ts
interface StreamResumeRecord {
  streamId: string;
  updatedAt: number;   // ms epoch，用于 55 分钟陈旧剪枝
}
```

- **不存 `status`**：只有「在跑的流」才写记录，终结即删 → 「记录存在 = 可续传」是干净的布尔信号，再加 `status:'active'` 是同义重复（YAGNI，对抗审查 4#9）。
- **不存 `lastEventId`**：跨会话/刷新一律 **from 0 重放**（§6 证明无重复），逐 delta 写 sessionStorage 纯属浪费（YAGNI，对抗审查 4#5/#10）。`lastEventId` 只活在 §7 单次 subscribe 会话的闭包里，用于该会话内部重连续读。
- **不存 `companyId`**：续传按 threadId，而 thread 与 company 绑定、缓冲内容本就属于该 thread；模拟工具条只影响「新提问」去哪个公司，不影响「重放已有流」。故无跨公司串流风险，不加该字段（对抗审查 2#13，判为低风险、YAGNI）。

### 5.2 存储位置：`sessionStorage`（非 `localStorage`）

- **刷新（同标签页）**：`sessionStorage` 在同标签 reload 后保留 ✅ —— 正是要修的场景。
- **多标签**：`sessionStorage` **按标签隔离**。在跑的流只活在发起它的那个标签的 Hook 里；用 `sessionStorage` 时其它标签打开 A 只会 `getResume(A) → null → loadThread`（读 DB），不会去抢订阅同一条 `sse:buf`。
- 真正的兜底是 **55 分钟陈旧剪枝**（对齐后端 1h TTL）：任何残留记录超时即作废。
- 现有代码 `localStorage` 用于 `authority` / `localuser` 等**持久身份**（跨标签是刻意的）；流恢复态是**易失、标签内**，`sessionStorage` 才对口。

> 叙述更正（对抗审查 4#1）：是「单流-单标签架构」决定了不跨标签同步，`sessionStorage` 与之吻合；跨标签直播同步属 YAGNI / 范围外。

### 5.3 单键存整张表

键 `chat_stream_resume`，值 `JSON.stringify(Record<threadId, StreamResumeRecord>)`。单键便于整体剪枝/清理，避免 key 泛滥。

工具 API（读写都 `try/catch` 吞 quota/parse 错误，失败即「无记录」安全降级到 `loadThread`）：

```ts
getResume(threadId): StreamResumeRecord | null   // 缺失 或 超过 55min → 返回 null
setResume(threadId, record): void
clearResume(threadId): void
pruneStale(): void                               // 启动时调一次，删除 >55min 的记录
```

### 5.4 写入时机（两阶段 + alive 门控）

新建会话时帧序为 `stream`(带 stream_id) → `thread`(带 thread_id) → delta……（[chatEvents.ts](../../../CIOaas-web/src/services/api/chat/chatEvents.ts)）。`stream` 帧到时还没有 threadId 可作键，故：

- 提供一个 `persistResumeIfReady()`：**仅当 `streamIdRef.current` 与 `threadIdRef.current` 都就绪、且 `alive()` 为真**时写记录（幂等）。
- 在 `onStreamId`（[:83](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）与 `onThreadId`（[:86](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）末尾各调一次：
  - 续问已有会话：`onStreamId` 时 threadId 已知 → 立即写。
  - 全新会话：`onStreamId` 时 threadId 仍空 → 不写；`onThreadId` 设好 `threadIdRef.current` 后再写。
- **`alive()` 门控写入本身**（不只门控 dispatch，对抗审查 4#2）：若在 `stream`↔`thread` 之间已切走，`genRef` 已自增 → 不写陈旧记录。此时该新会话尚未进入侧栏（`onThreadStarted` 也被 alive 拦下），用户也无入口回到它，安全。

### 5.5 清除时机（终结即删 + 主动清 + 启动剪枝）

记录的删除必须覆盖**所有**会让流终结/废弃的路径：

- 终结回调里 `clearResume(threadIdRef.current)`：`onDone`（[:115](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）、`onError`（[:118](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）、`onBlocked`（[:108](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）、`onNeedsPick`（[:104](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）。
- `stop()`（[:155](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）：用户主动停 → 清。
- **删除会话**：`handleDeleteThread`（[index.tsx:233](../../../CIOaas-web/src/pages/ai/chat/index.tsx)）里 `clearResume(id)`（对抗审查 4#4，回调不会触发的路径）。
- **`newChat`**：开新会话前 `clearResume(threadIdRef.current)`（对抗审查 4#9）。
- **启动剪枝**：Hook 首次挂载 `pruneStale()`，清掉 >55min 的死记录（对抗审查 4#4）。
- 幂等：多个终结回调可能都触发，删不存在的键是 no-op，安全。

---

## 6. 进会话决策：`enterThread(threadId)`

`handleSelectThread`（切换 / 刷新后点侧栏）统一改走 `enterThread`，取代裸 `loadThread`。

```text
async enterThread(threadId):
  myGen = ++genRef.current          // 作废任何在途流（与 loadThread 一致）
  abortRef.current?.abort()         // 断开上一条前端连接（后台生成不受影响）
  threadIdRef.current = threadId

  rec = getResume(threadId)         // sessionStorage；缺失/陈旧 → null
  if rec == null:
     await loadThread(threadId)     // 无在跑的流 → 读 DB（今日行为）
     return

  // 有「在跑的流」记录 → 先铺历史，再续流
  loaded = await loadThread(threadId)      // 1) 先把 DB 已完成轮次画出来
  if myGen !== genRef.current: return       // 期间又切走 → 放弃

  // 2) 剥离可能存在的「空 assistant 占位」，再加一个干净的空气泡（见下硬性要求）
  if last(loaded) is assistant with empty blocks:
     dispatch load(loaded.slice(0, -1))     // 去掉幻影空气泡
  dispatch startAssistant                    // 一个干净空气泡承接重放的 delta

  // 3) 订阅缓冲，from 0 重放（不带 Last-Event-ID）
  controller = new AbortController(); abortRef.current = controller
  streamIdRef.current = rec.streamId
  await subscribeStream(rec.streamId, resumeCallbacks(myGen), { signal: controller.signal })
  // resumeCallbacks 全部用 alive()=(myGen===genRef.current) 包裹；终结里 clearResume + 选择性 loadThread 回填 id
```

### 6.1 与 DB 历史的对账（杜绝双渲染）—— 这是正确性核心

依据后端事实（§3 第 4、8 条）：

1. `loadThread` 画的全是**已完成轮次**；进行中那一轮 DB 里**没有** assistant 内容（第 8 条）。
2. `startAssistant` 造**一个全新空气泡**。
3. `subscribeStream` **不带 `Last-Event-ID`** → 后端 from 0 重放进行中那一轮 → `onDelta` 追加进这个空气泡（`appendDelta` 拼到最后一条 assistant 的文本块）。

因为**进行中那一轮从来没进过 DB**，from 0 重放不可能与 DB 内容重复 → 整轮从头无重影地重建。

**为什么不用 `Last-Event-ID`**：刷新后内存里的 `lastEventId` 已丢；from 0 重放更简单且（因第 8 条）恰好正确。重放头部那几帧（`stream`/`thread`/控制帧）成本极低。

**硬性要求（对抗审查 3，从「可选」升级为「必做」）**：步骤 2 必须先剥离尾部空 assistant 再 `startAssistant`。虽然第 8 条保证正常不会出现 DB 里有空 assistant，但一旦后端将来改成增量落库，没有这道护栏就会出现「幻影双气泡」（delta 追加进第二个气泡、第一个空着）。3 行成本，杜绝唯一的双渲染路径。

### 6.2 先 `await loadThread` 再 `subscribeStream`（串行，别并行）

对抗审查 4#3：若两者并行，缓冲可能在 DB 还没画出来时就先把直播答案铺进空气泡，随后历史轮次"啪"地插到上方、直播答案被挤下去 —— 视觉跳动。**串行**（先历史、后直播填充）与今日体验一致，代价仅 `loadThread` 延迟（已完成轮次通常 <100ms）。

### 6.3 刷新入口说明（澄清，对抗审查 2）

`activeThread` 是组件 state（[index.tsx:59](../../../CIOaas-web/src/pages/ai/chat/index.tsx)），刷新后归 `''`，不自动恢复。刷新后用户从侧栏点 A → `handleSelectThread` → `enterThread`，即命中续传。**无需额外 mount effect**；本方案只增强「点进去之后能续流」，不改「初次进入仍靠用户点侧栏」。

---

## 7. `streamApi` 重构：统一一个 `subscribeStream`

把现有续传循环（[streamApi.ts:134-157](../../../CIOaas-web/src/services/api/chat/streamApi.ts)）抽成导出函数，**消除「两条续传路径」的歧义**（对抗审查 4#5）：

```ts
// 唯一区别：首次 subscribe 是否带 Last-Event-ID。
export async function subscribeStream(
  streamId: string,
  cb: SubscribeCallbacks,                 // 不含 onStreamId/onThreadId（见下）
  options: { signal?: AbortSignal; fromLastEventId?: string },
): Promise<void> {
  let lastEventId = options.fromLastEventId;   // 本会话内累积，用于断连续读
  let terminal = false; let retries = 0;
  // 复用现有 handle + while 重连退避循环（MAX_RESUME_RETRIES / RESUME_BACKOFF_MS 不变）
  // 首轮：lastEventId 为 undefined → 不发头 → 后端 from 0；live 断线路径传入累积值 → from N+1
}
```

- **`streamChat`（live 流式）**：POST 流断（非 abort）后调 `subscribeStream(streamId, cb, { signal, fromLastEventId: 累积的 lastEventId })` —— 行为与今日完全一致（from N+1），只是把循环体抽出去。
- **`enterThread`（切换/刷新续传）**：调 `subscribeStream(rec.streamId, resumeCallbacks, { signal })`，**不传 fromLastEventId** → from 0。
- **回调子集**（对抗审查 4#8）：续传路径的 `cb` **不含 `onStreamId` / `onThreadId`**——streamId 已知、thread 已定，重复触发会多写一次记录（幂等但多余）。续传只要 `onDelta / onChart / onBlocked / onNeedsPick / onDone / onError`。
- **重连/超时策略**（对抗审查 4#6/#7）：循环天然继承 `MAX_RESUME_RETRIES`(3) + `RESUME_BACKOFF_MS`(500)；网关 120s 截断或网络抖动时按 `Last-Event-ID` 自动续读；彻底失败 → `onError('Stream connection lost')`。这也覆盖了 §9「worker 崩溃」的兜底退出。

---

## 8. 串话 / `genRef` 守卫如何接入

现有 `genRef` + `alive()` 守卫足够稳，续传路径必须**和 `send` 一样**骑在上面：

- `enterThread` 进入即 `++genRef.current` 并在任何 await 前捕获 `myGen`。
- `resumeCallbacks` 的**每个**回调都包 `alive() = () => myGen === genRef.current`，且**为每次 `enterThread` 调用新建闭包**（不复用同一个回调对象，对抗审查 1#8）。
- 快速 A→B→A：每次 `enterThread` 自增 `genRef`，旧续传的在途回调 `alive()` 失败被静默丢弃 → A 的重放帧**绝不可能**追加进 B 的气泡。
- 每次 `enterThread` 换新 `AbortController`，旧 `subscribeStream` 的 `GET /subscribe` 被物理 abort、循环经 `signal.aborted` 退出停轮询（双保险）。
- `streamIdRef.current = rec.streamId` 让 `stop()` 能停到**续传的**这条流（[useChatStream.ts:162](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）。

---

## 9. 边界场景（每条对应一个已验证事实）

| 场景 | 后端行为（§3） | 前端处理 |
|------|----------------|----------|
| 流已结束才回来 | 缓冲含 `[DONE]` 可重放 1h（#4） | `subscribeStream` from 0 画完整答案 → 命中终结 → `onDone` → `clearResume` →（可选）`loadThread` 回填 id。**优于今日** |
| 缓冲已过期（>1h） | 10s 空窗后 SSE `error`（#5） | `onError` → `clearResume` → DB 内容（§6 第 1 步已画）留屏，不卡。且 55min 剪枝通常让我们根本不发起 subscribe，直接 `loadThread` |
| 未知 streamId | 同上：**HTTP 200 + error 帧**（非 404，#5） | 同「过期」：经 `onError` 处理，**不**判 HTTP 状态码 |
| worker/pod 崩溃 mid-stream | 任务进程本地、不复制，随进程死；但**缓冲在 Redis 仍在**（#1） | 重放崩前缓冲帧后无终结帧 → 重连循环 ~5s 内超时 → `onError` → `clearResume`。**已知局限**：崩掉的流无法「继续生成」，只能恢复已缓冲部分，用户可重新生成。需后端任务持久化才能根治（范围外） |
| 多标签 | 缓冲共享、`/subscribe` 是重放式轮询（#1） | `sessionStorage` 按标签隔离 → 只有发起标签有记录、才续传；其它标签 `loadThread` 读 DB，无双订阅 |
| `stop()` 交互 | 设 `sse:stop`（60s），不清缓冲，发 `stopped`+`[DONE]`（#6） | `stop()` 必 `clearResume`，下次进入走 `loadThread`，不会去续一条用户已停的流 |
| 流中途 error 帧 | `error` 为终结（chatEvents.ts:91） | `onError` 已 `clearResume` + toast；下次进入 `loadThread` |
| `needs_pick` | 发出 pick 提示后流在服务端结束 | `onNeedsPick` → `clearResume`。**pick 内联 UI 是 reducer-only state，刷新后丢**（既有坑 [useChatStream.ts:133](../../../CIOaas-web/src/pages/ai/chat/hooks/useChatStream.ts)）——本方案**不改善也不恶化**，用户重新提问即可 |
| 切走发生在 `stream` 帧到达前 | 还没有 streamId | 未写记录 → 重进 `loadThread`。可接受 |

---

## 10. 改动清单（按文件，最小化）

| 文件 | 改动 | 规模 |
|------|------|------|
| **新增** `src/pages/ai/chat/utils/streamResume.ts` | `getResume / setResume / clearResume / pruneStale`，单 `sessionStorage` 键 + 55min 剪枝，纯函数、吞错降级 | ~40 行 |
| `src/services/api/chat/streamApi.ts` | 抽出并导出 `subscribeStream(streamId, cb, { signal, fromLastEventId? })`；`streamChat` 内部复用（**行为不变**，纯重构 + 导出） | 小 |
| `src/pages/ai/chat/hooks/useChatStream.ts` | `persistResumeIfReady()`（onStreamId/onThreadId 调用，alive 门控）；终结回调 + `stop()` 调 `clearResume`；新增并导出 `enterThread(threadId)`；挂载时 `pruneStale()` | 主要但仍小 |
| `src/pages/ai/chat/index.tsx` | `handleSelectThread` 调 `enterThread(id)` 取代 `loadThread(id)`；解构 `enterThread`；`handleDeleteThread` / `handleNewChat` 加 `clearResume` | 几行 |
| `src/pages/ai/chat/utils/messageReducer.ts` | **不改**，仅复用 `load / startAssistant / appendDelta` | — |

**后端：0 改动。** Redis 缓冲、1h TTL、`Last-Event-ID` 重放、from-0 重放、终结帧入缓冲、未知 id 的 10s-grace error —— 全部已具备，正是本方案消费的能力。续传复用 live 已在用的 `/api/ai/sse/subscribe` 路径，不新增网关配置。

---

## 11. 诚实的局限（前端无法单独解决）

1. **worker/pod 生成中崩溃**：可恢复崩前缓冲，但无法「继续生成」；需后端任务持久化/复制。范围外。
2. **缓冲 1h TTL 后**：续传降级到 DB 最终内容。后端 3600s TTL 固有，非前端 bug。
3. **`needs_pick` 内联 UI 刷新后不重建**：既有 reducer-only-state 坑，本方案不碰、不恶化。

---

## 12. 对抗审查纳入的「实现必守」清单

1. **回调工厂**：`enterThread` 每次新建包 `alive()` 的回调闭包，**不复用**同一对象。
2. **两阶段持久化 + alive 门控**：仅在 streamId & threadId 都就绪且 `alive()` 时 `setResume`；新会话写在 `onThreadId` 后。
3. **终结全路径清记录**：`onDone / onError / onBlocked / onNeedsPick / stop() / 删会话 / newChat` 都 `clearResume`；挂载 `pruneStale()`。
4. **剥离空 assistant 再 `startAssistant`**（硬性，§6.1）。
5. **串行**：先 `await loadThread` 再 `subscribeStream`（§6.2）。
6. **`subscribeStream` 回调子集**：续传不含 `onStreamId / onThreadId`（§7）。
7. **去 `status` 字段、不持久化 `lastEventId`、不加 `companyId`**（YAGNI，§5.1）。

---

## 13. 验收 / 手测（覆盖用户报的两个复现）

| 用例 | 步骤 | 预期 |
|------|------|------|
| 复现① 切换会话续流 | 新建 A 提问（流式中）→ 新建 B 提问 → 切回 A | A 从断点续上、继续逐字输出直至完成（不重新生成、不重影） |
| 复现② 刷新续流 | A 流式中刷新页面 → 侧栏点 A | A 续上流式输出（流仍在跑则继续；已跑完则瞬间重放完整答案），**不再只在最后一次性出现** |
| 串话 | A 流式中切 B 再切 A，反复快切 | 任一会话气泡只显示自己的内容，无串话 |
| 停止后再进 | A 流式中 `stop()` → 切走 → 回 A | 走 `loadThread` 读 DB，不会去续一条已停的流 |
| 删除会话 | 删除有在跑流记录的会话 | `sessionStorage` 记录被清，无残留 |
| 缓冲过期 | 构造 >1h（或后端缩短 TTL 验证）后回到会话 | 不卡死；10s 内降级到 DB 最终内容 |
| 多标签 | 标签1 流式 A，标签2 打开 A | 标签2 读 DB（不抢订阅）；标签1 续流正常 |

> 测试命令见 [web-test-commands] 约定：单测 `npx umi-test`；类型检查 `npm run tsc`（须先挂 node PATH）。建议为 `streamResume.ts`（getResume 陈旧判定 / 吞错降级）补单测，为 `enterThread` 的「有记录走续传 / 无记录走 loadThread / 剥离空气泡」补 Hook 测试。
