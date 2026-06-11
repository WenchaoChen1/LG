# AI Chatbot 两端对话与历史记录完善 — 设计文档

- **日期**：2026-06-11
- **状态**：已批准
- **范围**：`CIOaas-python`（chatbot 模块）+ `CIOaas-web`（chat 页面与 services）
- **关联需求**：LG-1332（公司端 Chat UI）、LG-1335（管理端 Chat UI）、LG-1339（聊天历史）
- **关联 spec**：`2026-06-11-sse-event-contract-design.md`（SSE 权威契约表，本次新增 `title` 事件已同步修订其 §4）
- **UI 稿**：Figma `2026 - Portfolio Portal` node `12659-18104`（两端样式以稿为准；功能设计不依赖稿）

---

## 1. 背景与目标

AI Chatbot V1 骨架已上线（SSE 流式对话、历史侧栏、图表、SSE 事件契约重构均已完成）。对照需求仍缺：

1. 🔴 **多轮上下文**：续聊历史会话时 `state["history"]` 恒为空数组，AI 不记得之前的对话（违反 LG-1339 验收标准"继续对话时 AI 保留先前对话的上下文"）；
2. 🔴 **会话标题**：`title` 永远 NULL，历史侧栏无法识别话题（LG-1339 UX 要点）；
3. 🔴 **两端差异化**：需求要求两端 headline/prompts 明确不同，当前两端共用一套文案；
4. 历史会话管理（重命名/删除）——需求标 post-MVP，经用户确认**提前实施**；
5. 停止生成按钮；
6. needs_pick 仅显示提示文本，管理端无法就地选公司；
7. 前端端类型判定依赖 hostname，本地开发恒判成客户端；
8. 移动端响应式 + 按 Figma 优化两端样式。

**入口保持原样**：路由 `/ai/devSupport/chat`（`hideInMenu: true`）不动、不新增菜单入口；保证两端用户经 URL 直达可用，后续任一端加入口即通。

**不做**（后续版本）：跨公司聚合问答、消息搜索/导出、Memory File、welcome prompt 个性化、Tool Calling Loop；不动 LangGraph 图结构、`llm` 公共层原语、`chart_fence_parser`。

---

## 2. 身份与端判定

### 2.1 后端（保持现状，权威机制）

| 端 | 判定 | 会话归属字段（`ai_chatbot_thread`） | 分析对象公司 |
|---|---|---|---|
| 管理端（roleType=1 超管） | Redis 会话 `companyId` **空** | `user_id` + `org_id`（组织）+ `end_type='admin'` | 前端所选 `active_company_id` |
| 客户端（roleType 2/3/4） | Redis 会话 `companyId` **非空** | `user_id` + `end_type='company'` | 锁定本公司（忽略前端传值） |

历史记录严格按 `user_id` 隔离（list/get/续聊均带 owner 过滤），不信前端 `x-chat-end`。**无表结构变更**（`title`/`deleted`/`org_id`/`end_type` 字段均已存在）。

### 2.2 前端（改动）

`pages/ai/chat/utils/endContext.ts` 的 `resolveEndType()`：优先按 `getUserInfo()?.roleType` 判定——`Number(roleType) === 1 → 'admin'`，其余 → `'company'`；roleType 缺失（异常态）回退现有 hostname 判定。代码库中 roleType 既有 number 也有 string 用法，必须 `Number()` 归一。

---

## 3. SSE 契约新增：`title` 事件

权威契约表（`2026-06-11-sse-event-contract-design.md` §4）新增一行，三个代码单点同步：

| 语义 | SSE 形态 | event 名 | payload | 触发点 |
|---|---|---|---|---|
| 标题已生成 | 结构化事件 | `title` | `{thread_id: string, title: string}` | 新建 thread 首轮，主文本流结束后、`[DONE]` 前 |

> **✅ 已由另一会话实现（2026-06-11，以其为准）**：后端事件类为 `chat_events.TitleGenerated`（`_SSE_NAME + sse_event()` 自描述协议），序列化统一在 `llm/.../sse.py` 通用 `to_sse`（`chatbot/interfaces/sse_events.py` 已删除）；前端 `chatEvents.ts` 的 `CHAT_EVENT.TITLE` + `onTitle` 已就位。实现注记（触发条件/落库顺序/失败语义）见契约 spec §4。

---

## 4. 后端设计（CIOaas-python）

### 4.1 repository.py

```python
def get_recent_messages(*, thread_id: str, limit: int = 10) -> list[ChatMessage]:
    """按 seq 倒序取最近 limit 条后反转为升序（多轮上下文用）。"""
```

- `soft_delete_thread(*, thread_id: str) -> None`：`UPDATE ... SET deleted = TRUE`；
- `get_thread` / `get_messages` 的归属查询**补 `deleted IS FALSE` 过滤**——已删会话不可续聊、不可读（`list_threads` 已过滤，保持）。

### 4.2 chat_service.stream_turn 改造

> **✅ 标题生成与部分落库已由另一会话实现（2026-06-11，以实现为准）**：`needs_title` 参数（routes 按「thread 尚无 title」判定，含续聊补生成）；主文本流结束后经 `llm_db_router.acomplete`（Sonnet，≤16 字 prompt、截 50 字符）串行生成，**先 `set_title` 落库再下发 `TitleGenerated`**，失败只记 warning、不下发、title 留 None 下轮重试，客户端打断时不生成；try/finally 部分落库（`completed or buf` 即落，沿用图 attribution，无额外标记）。

本设计仍待实现的部分（历史回填）：

```
读最近 10 条历史（get_recent_messages，在落当前用户消息之前）
→ append_message(user)
→ state["history"] = [{"role": m.role, "content": m.content} for m in 历史 if m.role in ("user","assistant")]
→ 其余编排保持现状（ThreadStarted / 图 / 主流 / needs_title / finally 落库均不动）
```

### 4.3 routes.py

- **POST `""`（发送）**：
  - 管理端分支调用 `accessible_companies(user=ctx, auth_token=...)`（已有 5 分钟/用户缓存）传入 `stream_turn(accessible_company_list=...)`，替代现在写死的 `[]`——恢复 `resolve_company` 的公司提及匹配与 `call_company` 上下文；公司端仍传 `[]`（零开销，锁本公司用不到）；
  - 续聊分支：管理端且 `request.company_id` 非空且 ≠ thread 当前 `active_company_id` 时调 `set_active_company` 更新；
  - 新建分支：`stream_turn(..., generate_title=True)`。
- **PATCH `/threads/{thread_id}`**：body `vo.ThreadRenameRequest(title: str)`；owner 校验（`get_thread(thread_id, user_id)`，无则 404，沿用现有 IDOR 模式）；`title.strip()` 后空 → 422，>255 → 422（pydantic `max_length`）；`set_title`；返回 `vo.OkResponse`。
- **DELETE `/threads/{thread_id}`**：owner 校验 404；`soft_delete_thread`；返回 `vo.OkResponse`。

### 4.4 vo.py

- `ThreadRenameRequest`（`title: str`，`Field(min_length=1, max_length=255)`）；
- `OkResponse`（`success/code/message`，与现有信封同构、无 data）。

---

## 5. 前端设计（CIOaas-web）

### 5.1 services 层

| 文件 | 改动 |
|---|---|
| `services/sse/streamSSE.ts` | `StreamSSEOptions` 增加 `signal?: AbortSignal` 透传给 fetch；catch 中 `e.name === 'AbortError'` 静默返回（主动取消不是错误，公共层保持零业务） |
| `services/api/chat/chatEvents.ts` | §3 所述 `TITLE` 事件 + `onTitle` 回调 |
| `services/api/chat/streamApi.ts` | `streamChat(req, cb, signal?)` 第三参数透传 |
| `services/api/chat/chatApi.ts` | `renameThread(threadId, title)`（PATCH）、`deleteThread(threadId)`（DELETE），umi-request 普通 JSON |
| `services/service/chat/chatService.ts` | `renameThread` / `deleteThread` service 封装 + 既有 `ChatApiError` 统一错误处理 |

### 5.2 hooks

**useChatStream**：
- `abortRef = useRef<AbortController | null>`；`send` 时新建 controller 传入 `streamChat`；
- 新增 `stop()`：`abort()` + `genRef` 自增（作废后续回调）+ `dispatch finish`（已收文本保留）；
- `onTitle` 回调上抛（由页面联动 useChatThreads 更新侧栏）；
- `onNeedsPick` 改为：`dispatch({type:'needsPick', hint})`——最后一条 assistant 消息渲染提示语并打上 `needsPick` 标记（不再当纯文本结束）。

**useChatThreads**：
- `applyTitle(threadId, title)`：本地 immutable 更新对应条目（收到 `title` 事件 / 重命名成功后调用，不整表 reload）；
- `removeThread(threadId)`：调 service 删除成功后本地移除；
- `renameThread(threadId, title)`：调 service 成功后本地更新。

### 5.3 页面与组件

- **constants.ts** 按端导出两套文案：

  | 端 | headline | 建议卡 |
  |---|---|---|
  | company | `Always here, always in sync—your partner for every business move.` | 沿用现有 6 张（已是单公司视角） |
  | admin | `Always-on intelligence for your entire portfolio.` | 6 张**单公司可答版**（管理端视角、围绕已选公司）：RISKS「Is the selected company showing signs of underperformance this month?」/ FINANCIALS「Summarize the selected company's latest financial highlights」/ BENCHMARK「How does this company score against benchmark peers right now?」/ FORECAST「Is this company falling behind its committed forecast?」/ RUNWAY「What's this company's runway and monthly burn rate?」/ COMPANY「Give me a quick profile of this company and its stage」 |

  > **与 LG-1335 的偏差（已确认）**：需求原文 prompts 为跨公司问题，V1 无跨公司聚合能力，点击只会触发"请选公司"。经用户确认改用单公司可答版；待跨公司能力（V1.1）上线后换回需求原文。Portfolio/Strategy 两类别（依赖跨公司与 GS 知识库）暂以 RISKS/RUNWAY 替代。

- **index.tsx**：端文案按 `endType` 取；管理端点开历史会话时 picker 自动切到该会话 `activeCompanyId`（`onSelect` 里从 threads 取）；持有 `stop`、`onTitle→applyTitle`、needs_pick 选择回调；侧栏折叠状态。
- **HistorySidebar**：每条会话 hover 显示 `···` Dropdown（Rename / Delete）：Rename → 行内 Input（回车/失焦提交，Esc 取消）；Delete → Popconfirm；删除当前激活会话 → `newChat()` 回欢迎页。桌面端侧栏可折叠；≤768px 改为滑入抽屉（history 图标开关）；"New Chat" 始终可见。
- **InputBox**：`streaming` 时发送按钮变「停止」（方块图标）→ `onStop`；非 streaming 恢复发送。
- **ConversationPane / MessageBubble**：带 `needsPick` 标记的 assistant 消息（仅管理端出现）在气泡内渲染提示语 + 内联公司下拉（复用已加载 companies）；选中后 `setCompanyId(picked)` 并以所选公司**自动重发原问题**（从 state 倒数最近一条 user 消息取文本）到同一 thread。重发会再落一条相同 user 消息——接受（诚实反映会话流）。
- **样式与响应式**：断点 ≤768px；消息区/输入框自适应；视觉细节（配色、气泡、侧栏、建议卡、间距）按 Figma node `12659-18104` 两端稿对齐，主题 tokens 沿用 `src/pages/ai/_shared/tokens.less` 体系（如与稿冲突，以稿为准并在实现说明中记录）。

---

## 6. 错误处理

| 场景 | 处理 |
|---|---|
| title LLM 失败 | （✅ 已实现口径）只记 warning、不下发事件，title 留 None 下一轮自动补生成；绝不阻塞/中断主流 |
| 用户停止生成 | （✅ 已实现口径）前端 abort → 已收文本保留、streaming 归零；后端 finally 落部分答案（沿用图 attribution） |
| PATCH/DELETE 非本人 thread | 404（沿用现有 IDOR 语义，不泄露存在性） |
| PATCH title 空/超长 | 422（strip 后校验） |
| 已删 thread 续聊/读消息 | get_thread/get_messages 过滤 deleted → 404 / 空 |
| rename/delete 网络失败 | `ChatApiError` → antd message.error，本地 state 不变（无乐观更新） |
| AbortError | streamSSE 静默返回，不进 onError |

---

## 7. 测试

**后端**（`tests/chatbot/`，pytest，`uv run pytest`）：
- `test_repository.py`：`get_recent_messages` 截断与排序；`soft_delete_thread` 后 `list_threads`/`get_thread`/`get_messages` 均不可见；
- `test_chat_service.py`：续聊时 history 注入图 state（构造既有消息断言 `ainvoke` 入参）；首轮 `TitleSet` 事件下发与 set_title（mock llm）；title 失败回退截断；取消主流时部分答案落库（`attribution=["stopped"]`）；
- `test_routes.py`：PATCH/DELETE 成功路径 + 非本人 404 + title 校验 422；管理端发送注入 accessible_companies（mock）；续聊换公司触发 `set_active_company`；
- `test_sse_events.py`：`TitleSet` → 期望 SSE bytes。

**前端**：门禁 `npm run tsc` 零错误 + 人工 review（测试基架损坏，jest 跑不起来——照既有约定不动基架）；`chatEvents.test.ts` 补 `title` 分发用例（基架修复后可跑）。

**验证项（实现时人工确认）**：
1. 客户端用户经 URL 直达 `/ai/devSupport/chat` 不被 `clientRoutePermissions` 守卫拦截（保证后续加菜单入口即通）；
2. 本地 dev（localhost）管理端账号登录后正确显示管理端 UI（roleType 判定生效）；
3. `config/proxy.ts` 本地改动中的笔误 `ttp://127.0.0.1:9000` 修正为 `http://...`（属用户本地配置，仅修笔误不改指向）。

---

## 8. 决策记录

| 决策点 | 选择 | 理由 |
|---|---|---|
| 标题生成方式 | Haiku 并行生成 + `title` 事件，失败回退截断 | 不阻塞首 token；LG-1339 允许截断，LLM 标题体验更好，回退保证恒有标题 |
| 重命名/删除 | 提前实施（需求标 post-MVP） | 用户明确要求；后端字段已就绪、增量小 |
| 停止生成 | 纯前端 abort + 后端 finally 部分落库 | 不引入服务端取消通道（YAGNI）；部分落库保证历史完整 |
| needs_pick 重发 | 正常重发（会出现重复 user 消息） | 诚实反映会话流，避免隐藏发送的特殊路径 |
| 管理端建议卡 | 单公司可答版（偏差已记录） | V1 无跨公司能力，需求原文点击必触发 needs_pick，体验差；用户已确认 |
| 端判定 | 前端 roleType===1，hostname 兜底 | 与后端 Redis 判定一致；本地 dev 可用；登录流程已保证两端账号互斥 |
| 历史窗口 | 最近 10 条消息（约 5 轮） | 与 `build_synthesis` 现有 `history[-10:]` 对齐，控制 token 成本 |
