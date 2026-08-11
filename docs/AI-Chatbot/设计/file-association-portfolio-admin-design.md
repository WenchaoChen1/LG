# AI Chatbot — 文件公司归属识别与确认（Portfolio Admin 端）设计

> 关联文档: [需求 PRD](../ai-chatbot-file-association-portfolio-admin-prd.md) | [Chatbot V1 设计](./design-doc.md)
> 阶段：④ 设计 | 日期：2026-08-10 | 范围：Portfolio Admin 上传文件的公司归属推断与确认，含放开管理端门户上传

---

## 一、范围与核心结论

**本设计覆盖**：Portfolio Admin 在聊天中上传文件后的「公司归属推断 + 确认」交互，以及为使该流程真正可用而放开管理端门户上传（含配套的工具绑定与提示词调整）。

**核心结论（调研后收窄）**：PRD 三分支表描述的**后端落库行为已经完整存在**，本次无需新增表、列或迁移。真正的增量是：

| 增量 | 说明 |
|------|------|
| ① AI 推断归属公司 | 全新能力，新增一个推断接口 |
| ② 归属确认条补齐 | 现有 `CompanyBelongPicker` 已覆盖 PRD §3.2/§3.3 大部分，补交互缺口 + 结果反馈 |
| ③ 批次归属规则 | 现有状态只在切会话时重置，需按「一批一司」修正 |
| ④ 放开管理端上传 | 不止解绑一个 prop——工具绑定与提示词须同源调整，见 §2.4 |

### 两处与 PRD 的偏差（均需 PM 知悉）

**偏差 1 — 触发时机**。PRD §2 写「文件上传并**完成 RAG 索引后**，本流程启动」。实际链路中 **RAG 索引发生在消息发送之后**：文件先直传 S3 拿到 fileId（chip ready），fileId 随消息进 SSE payload，后端落完 user 消息才做登记与向量化。

设计据此把触发时机定为 **chip ready 之后、点发送之前**。该窗口早于登记、早于向量化、早于摘要生成，**比 PRD 字面要求更严格**地满足 AC1「在任何记忆处理开始之前」，且是唯一可行的窗口。

**偏差 2 — 取消「单一确认操作」**。PRD §四要求「清晰显示推断的公司名 + **单一"确认"操作** + 选择其他公司的入口」，AC3 措辞亦为「若 Admin **确认** AI 推断的公司」。本设计按决策 D3 取消了独立的确认动作——推断填入即视为已选，用户不操作直接发送即生效。

理由：PRD §3.2 同时要求「AI 推断态与用户选择态视觉**完全一致**」，若保留确认按钮则两态必然可区分，两条要求本身存在张力。设计选择保留 §3.2 的视觉一致性，以「文案提示 + 常驻可见」替代确认按钮（见 §6.2）。**此项改变了交互契约，需 PM 确认接受。**

---

## 二、现状盘点

### 2.1 已实现、本次不动的部分

**记忆层没有独立存储**：作用域由 `ai_file_registry` 圈定（`memory_service.py:107-109` → `list_kb_entry_scopes`，只取 entry_id/end_type/company_id），**记忆行本体来自 `ai_rag_entry.summary`**（向量化后由 LLM 生成）。层映射靠 `end_type`（`source/memory/application/memory_service.py:43-51`）：

| end_type | 产品语义 |
|----------|----------|
| `APP`（公司端上传） | Company Memory（Layer 1a） |
| `ADMIN`（管理端上传） | Portfolio Memory（Layer 1b） |

**PRD 三分支表已由现有代码实现**（`sse_provider.py:382`、`chat_attachment_service.py:68,126-142`）：

| 归属公司 | 现有落库行为 | 对应 PRD 分支 |
|----------|--------------|---------------|
| 有值 | `business_type='KNOWLEDGE_BASE'` + `company_id=X` + `end_type='ADMIN'` | 写入该公司 Portfolio Memory |
| 空 | `business_type='SESSION_UPLOAD'` + `company_id=NULL` | 仅当前会话，不写任何记忆 |

**AC13（不流入 Layer 2）满足，但隔离机制与直觉不同**——分两条路径，理由不可混用：

- **记忆面板**：`list_kb_entry_scopes` 谓词确实带 `business_type='KNOWLEDGE_BASE'`，故 `SESSION_UPLOAD` 行不出现在 Memory 面板。
- **聊天检索**：现行链路**不走** `business_type` 谓词。带该谓词的 `list_kb_space_ids` 只在 `search_service.recall` 的 `mode is not None` 分支触发，而 `knowledge_base_tool` 调 `recall` 时**不传 `mode`**。真正的隔离在 **chunk 行级析取**：`(company_id IN (...) OR thread_id = ...)`。会话文件的 chunk `company_id` 恒 NULL，因此只能靠 `thread_id` 在本会话内命中，进不了任何公司的检索范围。

> 该差异影响的是「为什么安全」的论证，不影响「是否安全」的结论。但若后续有人给 `recall` 补上 `mode` 参数，两条路径的行为会分叉，需一并复核。

### 2.2 关键约束：推断能力必须新建

「chip ready 到点发送」这个窗口内，**后端不存在任何可读取的会话公司状态**：

- 附件登记发生在发消息之后（`sse_provider.py:373-398`），此刻尚未发生；thread 本身可能还没建。
- 公司识别结果只活在模型的 tool-call 参数里，**不进 `ChatState`、不落库**；三张对话图 compile 时不挂 checkpointer（`main.py:166-170`），per-turn 状态轮末即丢。`ChatState` 中与公司相关的字段只有 `accessible_company_list` / `home_company_id` / `active_company_id`，没有任何承载「模型识别出的目标公司」的字段。
- `ai_chatbot_thread.company_id` 看似可用，但**真实业务形态下管理端为 NULL**——前端仅在模拟形态才发 `company_id`（`Chat.tsx:237`），且管理端 init 分支不读 `active_company_id`（`init_node.py:79-97`）。**注意：devSupport 模拟页开启模拟时会写入非空值**，不能假定恒空。

> 补充事实：曾存在的三段式识别器 `company_match`（精确 id → RapidFuzz 模糊 → haiku 消歧）已于 2026-07-15 commit `f034f0b3` 随 sql 直查轨整链删除，同时删除的还有 `company_scope.py` / `sql_exec_tool.py` / `resolve_cid`。同族实现仅存 `portfolio_match.py`。当前公司识别由取数轨模型自行比对 `get_companies` 清单完成，工具层只做 `∩allowed` 鉴权。

### 2.3 为什么不放在对话图内

评估过「绑定放到问题改写节点」，三条硬阻碍：

1. `rewrite` 节点在附件轨**不执行**——函数体首条语句即 `if state.get("file_need"): return {}`（`rewrite_node.py:59-60`）。且 `rewrite` 只有 standard 图有，kb / combo 图均无。
2. 归属在**进图之前**就已落库（顺序：落 user 消息 → `attach_files_to_message` → 才构造 state 跑图）。
3. 图内识别结果无载体，且用户看不到确认机会，与 PRD「确认条」的核心诉求相悖。

### 2.4 放开管理端上传的真实范围（重要）

仅解绑 `uploadDisabled` **不足以让功能可用**。当前管理端在 standard 轨上被三处联动屏蔽：

| 屏蔽点 | 现状 | 后果 |
|--------|------|------|
| 工具 `end_types` 声明 | `search_knowledge_base` / `find_files` / `get_file_summary` 均声明 `metadata["end_types"] = {"company"}` | `_tools_for_turn` 在管理端**一律不绑**这三个工具 |
| `_file_directive` | 对 `end_type == "admin"` 直接返回空指令，注释写明「前端已禁管理端上传 → turn_files 恒空」 | 模型收不到任何附件处理指令 |
| `_KB_FILE_RULES` 提示词段 | 按 `end_type` 分叉，管理端不含文件规则 | 模型不知道该如何使用附件 |

若只放开上传：文件传得上去、也登记进了 Portfolio Memory，但**同一轮问答里模型看不见它**，除非用户显式敲 `/knowledge` 或 `/combined`（kb 子图硬编码绑定、不读 metadata）。

**三者必须同源修改**——代码注释中已记录过风险：工具绑定与提示词不同源时，模型会被命令去调用它实际看不见的工具，转而**谎称查过知识库**。

---

## 三、设计决策

| # | 决策 | 结论 |
|---|------|------|
| D1 | 管理端门户上传当前被禁用 | **一并放开**，且按 §2.4 同源修改工具绑定与提示词 |
| D2 | 推断能力建在哪 | **新增推断接口**，前端在 chip ready 时调用 |
| D3 | AI 推断填入后用户未操作即发送 | **算已选中，直接生效** |
| D4 | 发送后是否回显归属 | **折中**：保留一条会话内 inline 提示，不改消息侧契约（见 §6.5） |

### D3 的风险与缓解（展开）

**暴露面**：错误归属写入 B 公司的 Portfolio Memory 后，(1) 同组织所有管理员在 Memory Settings 面板（`GET /api/ai/memories`，scope=portfolio）均可见；(2) 之后任何针对 B 公司的知识库检索都会召回它。不是「悄悄错了、自己改掉」的量级。

**缓解手段**：
1. 归属条常驻可见直到发送，与 chip 同区域呈现，公司名过长时省略号 + hover 全名。
2. **AI 推断态使用差异化提示文案**（`AI matched — will be added to {X}'s memory.`）。PRD §3.2 约束的是**选择器 chip 的三态视觉**，并未约束归属条上的提示文案，故此举与 §3.2 不冲突，可在保持 chip 视觉一致的前提下消除「用户不知道这是机器猜的」这一风险放大器。
3. 发送后保留一条 inline 提示（D4），使发现时机延后到用户看到回答之时。

**补救路径（必须写明）**：`ai_file_registry` **支持事后删除，不支持事后改归属**——`PUT /records/{id}` 的请求 VO 中没有 `companyId`/`businessType`，路由白名单也不映射这两个 key。因此：

- **正确纠错方式**：在 Knowledge Base 面板删除该文件（`DELETE /api/ai/file-registry/records/{id}`，级联软删 entry + 硬删 chunk + 清 ES），然后重新上传并选择正确公司。
- **⚠️ 禁止「换个公司把文件再发一遍」**：这会造成登记行、entry、chunk **三方归属分叉**。chunk 的冗余列只在向量化成功那一次回填（`stamp_kb_registry_columns`），之后永不重同步；而管理端 space 按**组织**解析，重发命中同 space 同 file 会走复用去重、不重新向量化。结果是登记行改成了 B 公司，`ai_rag_entry` 与 chunk 仍是 A 公司——记忆面板显示 B，KB 检索仍按 A 命中。**此路径必须在实现与测试用例中显式规避。**

---

## 四、接口设计

### 4.1 新增：推断文件归属公司

```
POST /api/ai/chat/threads/{threadId}/infer-company
```

挂载于 chatbot 域（`source/chatbot/interfaces/routes.py`）。路径采用「父资源 + 动作段」形态，与本域既有的 `/threads/{id}/fork`、`/threads/{id}/messages/{mid}/switch` 一致；不使用 `/files/...`，避免与 file_registry 域的 `/api/ai/file-registry/*` 语义撞名。

**请求**

| 位置 | 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| path | `threadId` | string | 是 | 当前会话 id。新会话尚未建 thread 时前端**不发起请求**，故无需可空 |
| body | `draft` | string \| null | 否 | composer 中已输入但未发送的文本 |

不接收 `fileIds`。**取舍记录**：文件名（如 `Acme_2026Q3_Board.pdf`）其实是零成本高信号，前端手里也有；本期不用是为了让推断口径严格等同 PRD §二的「当前会话上下文」，避免文件名与会话内容冲突时的歧义。若上线后推断命中率不足，优先考虑纳入文件名。

**响应**（沿用 Python 统一 envelope）

| 字段 | 类型 | 说明 |
|------|------|------|
| `companyId` | string \| null | 推断出的公司 id；无法确定时为 null |
| `companyName` | string \| null | 公司名，供前端直接回填 chip 展示 |

判定过程**不出现在响应里**——对前端只有「推断出了」和「没推断出」两种结果，`companyId === null` 即后者。

> `companyName` 必须返回、不能让前端自行从下拉清单查名：`GET /api/ai/chat/companies` 在上游 LGPI 失败时会降级返回**空列表**，此时前端无从取名。chip 直接渲染响应中的 `companyName`，允许它暂时不在下拉清单中。

**行为规则**

1. **归属校验（安全，必须）**：以 `thread_id + user_id` 定位会话，取不到即返回空结果。与本域既有 thread 作用域接口口径一致（`routes.py:83-93` 注释直书「IDOR 防护」）。**不校验会导致他人会话在谈哪家公司被泄露**——推断结果直接携带公司名。此处返回空结果而非 404，因为对前端而言「查不到」与「推断不出」的处理完全相同。
2. **端类型限制**：仅管理端有意义。公司端调用直接返回空结果——公司端归属恒为登录身份公司，不存在推断需求。
3. **短路条件**（不调用 LLM，直接返回空）：thread 无历史消息**且** `draft` 为空、可访问公司清单为空。
4. **推断依据**：该 thread 末 5 条消息 + `draft` + 该用户可访问公司清单。
   > 数值 5 与取数轨历史窗口一致，但**本服务自持常量、不 import** `_HISTORY_WINDOW`——后者是 ai 域某个图节点内的私有下划线常量，跨域引用违反分层规范，且它是按取数提示词预算调的，与公司推断无关。
   > 纳入 `draft` 是因为用户往往边传文件边打字，而那句还没发出去的话常常正是最强信号（「这是 Acme 的 Q3」）；只看已落库的历史会漏掉它。
   > **注意其适用边界**：新会话在首条消息发送前没有 thread id，前端不发起请求（见请求表），因此 `draft` 只在**已有会话**里起作用。「New chat → 拖文件 → 打字」这条路径**不做推断**，归属条留空由用户手选——这是刻意取舍，见 §八。
5. **序号式判定（非置信度分数）**：把可访问公司清单编号后交给模型，模型只返回 **1-based 序号**，无法确定时返回 **0**。返回 0、越界序号、非整数输出一律判为无法识别 → `companyId=null`。多家都像、无任何公司线索同样落此分支。
   > 不采用「模型自报 0–1 置信度 + 阈值切分」：LLM 自报的连续分校准性差、分布随 prompt 措辞漂移，阈值难以稳定。把「敢不敢选」直接做成离散输出更可控。已删除的 `company_match` 第③段即此形态。
6. **候选红线**：模型**不接触也不产出 company id**——序号式天然保证 id 只能由服务端按序号回查清单得到，不存在模型编造 id 的可能。回查失败即降级为 null。
7. **模型与调用方式**：haiku（单一选择任务，无需 sonnet），经统一的 `llm.llm_db_router` 调用，不直连 SDK。
8. **超时预算**：该调用位于「上传完 → 发送」的关键路径上，需设置明确超时（建议 ≤3s），超时即按空结果返回。
9. **失败降级与可观测性**：异常、超时一律返回空结果，**不阻断上传流程**，前端静默落到空态。但**服务端必须区分「模型弃权（返回 0）」与「调用失败」**：分别记 span 属性与 warning 日志。否则该能力回归失效时对外表现完全相同（都是归属条空着），无人会察觉。
10. **候选清单规模**：序号式要求把全量可访问公司编号进提示词。超管的可访问集可能覆盖整个组织，需在实现时确认清单规模上界与提示词长度预算。

### 4.2 复用的既有接口

| 接口 | 用途 |
|------|------|
| `GET /api/ai/chat/companies` | 下拉候选公司清单（现有，无改动） |
| SSE `chatbot.chat` payload 的 `file_company_id` | 发送时上送归属公司（现有，无改动） |
| `DELETE /api/ai/file-registry/records/{id}` | 归属错误时的纠错路径（现有，无改动） |

---

## 五、数据模型

**无新表、无新列、无迁移。** 完全复用 `ai_file_registry` 现有结构，归属结果经既有的 `file_company_id` → `attach_files_to_message` 链路落库。

推断结果**不持久化**——它只是前端归属条的初始值，用户可改；最终生效的唯一事实来源是发送时上送的 `file_company_id`。

---

## 六、前端交互与状态流转

### 6.1 主流程

```
用户选择文件 → 直传 S3 → chip 变 ready
    │
    ├─ 满足推断触发条件（见 6.3）→ 调 infer-company(threadId, draft)
    │      ├─ 返回公司 → 回填归属条（AI 推断态）
    │      └─ 返回空 → 归属条留空（"Select company"）
    │
    ├─ 用户可随时改选 / 移除 / 保持不动
    │
    └─ 发送消息 → 带 file_company_id
           ├─ 有值 → 登记为 KNOWLEDGE_BASE，写入该公司 Portfolio Memory
           └─ 无值 → 登记为 SESSION_UPLOAD，仅本会话可用
```

### 6.2 归属条状态与文案

| 状态 | chip 视觉 | 提示文案 |
|------|-----------|----------|
| 空 | 虚线占位 "Select company" **+ 下拉指示（caret）** | `session-only, not saved to memory` |
| AI 推断 | 已填充：图标 + 公司名 + × | `AI matched — will be added to {X}'s memory.` |
| 用户选择 | 同上，**视觉完全一致** | `Will be added to {X}'s memory.` |

三点说明：

- **chip 三态视觉一致**（PRD §3.2）由 chip 本身保证；提示文案的差异不属于 §3.2 约束范围，用于满足 D3 的风险缓解。
- **时态**：发送前尚未写入任何内容，故用 `Will be added to…` 而非 `Added to…`——后者是承诺不是结果。
- 空态的**下拉指示**是当前实现缺失项：现有空态只有大楼图标 + 文字，无 caret（PRD §3.2 明确要求）。

### 6.3 批次归属规则与推断触发条件

**批次生命周期**（四个终结点，缺一不可）：

| 事件 | 归属处理 | 备注 |
|------|----------|------|
| 新增文件（批次内） | **不重新推断、不重置** | PRD §二明确要求 |
| 所有 chip 清空 | 重置归属，允许下批重新推断 | |
| **发送消息** | 重置归属，允许下批重新推断 | **相对现状的行为变更**：现有 `submit` 只清 chips、不动归属，导致同一会话连发两条带附件消息会静默沿用上一条的公司 |
| 切换会话 / New chat | 清空归属（现有行为已满足） | |

> **顺序不变式**：归属重置**必须发生在 `file_company_id` 读取之后**。发送路径先读归属组装 payload、再清空，若把重置实现成 submit 内的命令式调用且顺序颠倒，归属会在上送前被清掉。

**推断触发条件**（三条同时成立）：

1. 本批**首个** chip 变 ready；
2. 当前归属为空；
3. **用户本批未曾显式移除过归属**。

第 3 条不可省：用户手动点 × 移除推断结果，是「有意选择 session-only」的显式决定。若仅凭「当前归属为空」就重新推断，同批再拖入一个文件时会覆盖该决定，与 PRD §二的用户意图优先相悖。需为每个批次维护一个「已被显式移除」标记，随批次重置一同清除。

### 6.4 竞态处理（单一不变式）

不逐一枚举场景，改用统一规则：

> 推断请求发起时记录**批次 token**（会话 id + 批次序号）。响应回来后，仅当 **token 未变 且 归属仍为空 且 chips 非空 且 本批未被显式移除过** 时才应用，其余一律丢弃。

该不变式一次覆盖全部已知竞态：

| 竞态场景 | 若不处理的后果 |
|----------|----------------|
| 在途时用户手选公司 | 覆盖用户选择 |
| 在途时用户点 × 移除 | 覆盖用户的 session-only 决定 |
| 在途时用户清空所有 chip | 归属残留到空批次，并因「已有归属」**永久抑制**下一批推断 |
| 在途时用户切会话 | 回填进新会话，跨会话污染 |
| 快速「清空 → 重传」产生两个在途请求 | 响应乱序 |

### 6.5 发送后的归属提示（D4 折中方案）

发送后 chips 被清空、归属条随之消失，用户最可能发现推断错误的时机（看到回答时）反而失去所有归属信息。折中处理：

- 发送后在聊天流中该条 user 消息之后，保留一条 inline 提示：`{N} file(s) added to {X}'s memory.` / `{N} file(s) available for this session only — not saved to memory.`
- **仅存于前端本次会话内存**，不改消息侧契约、不落库。

**已知局限（明确记录）**：刷新页面、切走再切回、断流续传后该提示消失。因为 `file_company_id` 目前不随消息存储（`Chat.tsx:257` 已有注释确认），要做持久回显必须改消息侧契约，超出本期范围。AC10 的「明确告知」在刷新后不再成立——用户届时需到 Knowledge Base / Memory Settings 面板核对，那里有 Portfolio/Company 标签与删除入口。

---

## 七、改动点清单

### 7.1 Python

| 位置 | 改动 |
|------|------|
| `source/chatbot/interfaces/routes.py` | 新增 `POST /threads/{threadId}/infer-company` 端点，含 thread 归属校验 |
| `source/chatbot/interfaces/vo/{request,response}.py` | 新增该端点的 Request / Response VO（分层规范强制：Request/Response 在路由层、Service 签名只用 DTO） |
| `source/chatbot/application/service/` | 新增推断服务：归属校验 → 短路判断 → 取历史+draft → 取候选清单 → 编号 → haiku 判定 → 序号回查 → 结果。主方法平铺调用子方法 |
| `source/ai/prompts/chatbot/` | 新增推断提示词（中文）：给编号候选清单，要求只返回序号、拿不准返回 0，不得输出公司名或 id |
| **`source/ai/tools/knowledge_base_tool.py`**<br>**`find_files_tool.py`**<br>**`file_summary_tool.py`** | **（D1）** 调整 `metadata["end_types"]` 声明，使管理端 standard 轨能绑定这三个工具 |
| **`source/ai/agent/chatbot_graph/nodes/retrieval_agent.py`** | **（D1）** `_file_directive` 的 admin 分支：不再返回空指令；同步移除「前端已禁管理端上传」的过期注释 |
| **`source/ai/prompts/chatbot/`（`_KB_FILE_RULES` 段）** | **（D1）** 按端分叉的文件规则需覆盖管理端。**必须与上面两项同源修改**——不同源会导致模型被命令调用它看不见的工具，转而谎称查过知识库 |

### 7.2 前端

| 位置 | 改动 |
|------|------|
| `src/pages/devSupport/chat/components/Chat.tsx:491` | 解除 `uploadDisabled={portalAdminLite}` 绑定 |
| `src/pages/devSupport/chat/components/Chat.tsx:52-55` | 同步修改 `portalAdminLite` 的内联注释（现写有「附件上传（含整页拖放）禁用」） |
| `src/pages/devSupport/chat/utils/endContext.ts:42-57` | 同步修改 `isPortalAdminLite` 文档注释首句。**注意其影响面不止 rail**：共 6 处使用点——ChatSidebar rail、InputBox uploadDisabled、手机端 PortalTabBar、PortalNavSidebar、KnowledgeBasePage、MemorySettingsPage。本次只解除 uploadDisabled 一处，其余保持不变 |
| `src/pages/devSupport/chat/components/InputBox.tsx` | **摘除 `uploadDisabled` 死代码整片**——解绑后 `Chat.tsx:491` 是其唯一调用点，prop 声明与注释、`uploadDisabledRef`、两处拖放守卫、菜单置灰逻辑均变为零调用方 |
| `src/services/api/chat/` | 新增推断接口客户端 |
| `src/pages/devSupport/chat/components/InputBox.tsx` | ① 按 §6.3 三条件触发推断，含批次 token 竞态控制（§6.4）；② 补「发送」与「chips 清空」两个批次终结点的归属重置，注意 §6.3 的顺序不变式；③ 维护「本批已被显式移除」标记；④ 按 §6.2 实现三态差异化文案 |
| `src/pages/devSupport/chat/components/` | 新增发送后 inline 归属提示（§6.5，会话内存态） |
| `src/pages/devSupport/chat/components/CompanyBelongPicker.tsx` | ① 再次点击已选项 → 取消选择（现有 `pick` 无条件选中）；② 支持 Esc 关闭（antd 4.9 的 `trigger="click"` 底层无 Escape 处理）；③ 空态补下拉指示 caret；④ **空结果文案分叉两句**——现有 `No companies` 同时服务「搜索无匹配」与「清单本身为空」，而后者真实可达（`/companies` 上游失败会降级为空列表），一刀改成 "No results found" 会让拉取失败显示成没搜到；⑤ 顺手清理从无调用方的 `disabled` prop |

### 7.3 无需改动

后端登记逻辑、`ai_file_registry` 结构、记忆视图、SSE payload 契约、消息存储契约、对话图拓扑与节点。

> 已核实**不需要新增测试适配**：现有 `endContext.test.ts` 只断言函数布尔返回值，`InputBox.test.tsx` 对 `uploadDisabled` 零覆盖，`KnowledgeBasePage.test.tsx` 只 mock 它测导航。但反过来，`Chat.tsx:55` 那个 `variant === 'askGoldie' && isPortalAdminLite()` 的与条件（保障 devSupport 入口不受影响的唯一约束）本就无自动化保护，本次又要动它——应在⑦测试用例阶段点名覆盖。

### 7.4 已实现、无需改动的项（避免误列为缺口）

| 项 | 现状 |
|----|------|
| 下拉列表超高滚动 | `CompanyBelongPicker.less` 已有 `max-height: 240px; overflow-y: auto` |
| 选中态灰化/高亮 | `itemActive` 已实现 |
| 选中后关闭、点击外部关闭 | `pick` 内 `setOpen(false)`；antd Popover 默认行为 |
| 打开方式（点槽位/点 chip） | Popover `trigger="click"` 已覆盖两者 |
| 搜索实时过滤 | 已实现 |
| 公司名省略号 + hover 全名 | `.pillName` 已有 max-width + ellipsis，`title` 提供原生 tooltip |
| 移除 / 更换选择 | ✕ 已 stopPropagation 只清除；点 chip 重开下拉 |
| 归属条不阻塞发送 | `canSend` 不依赖 `belongCompanyId` |

---

## 八、边界与异常

| 场景 | 行为 |
|------|------|
| **新会话首次上传（无论 draft 是否为空）** | **不发起请求**，归属条留空，用户手选。新会话在首条消息发出前没有 thread id，而 thread 是归属校验与取历史的锚点。取舍已确认：不为此放宽 IDOR 校验路径，代价是这条路径拿不到推断 |
| 推断接口失败 / 超时 | 静默降级为空态，**不阻断上传与发送**；服务端记 warning + span |
| 推断出的公司已不在可访问清单 | 序号回查失败，降级为空 |
| thread 不属于当前用户 | 返回空结果（IDOR 防护） |
| 用户上传后不发送直接切会话 | 归属与 chip 一并清空（现有行为） |
| 公司端上传 | 不触发推断；归属恒为登录身份公司 |
| 上传失败的 chip | 不参与批次判定（沿用现有 failed chip 排除规则） |
| 归属错误已发送 | 删除后重传（§三 D3）；**禁止换公司重发同一文件** |

---

## 九、验收标准映射

| AC | 满足方式 | 备注 |
|----|----------|------|
| 1 | §4.1 推断接口在 chip ready 后、记忆写入前调用 | 触发时机见偏差 1 |
| 2 | §6.2 归属条展示公司名 + 存储位置提示 | |
| 3 | 现有 `file_company_id` 链路 | **确认动作已取消，见偏差 2** |
| 4 | 现有 `file_company_id` 链路 | |
| 5 | 序号式判定返回 0 → 空态 → 点击打开可搜索下拉 | |
| 6 | 现有 `SESSION_UPLOAD` 分支 | |
| 7 | §6.2 三态；chip 视觉一致，文案差异化 | 空态 caret 为新增项 |
| 8 | §7.2 四项修补 + §7.4 六项已实现 | |
| 9 | §7.4 已实现 | |
| 10 | §6.2 发送前提示 + §6.5 发送后 inline 提示 | 刷新后不成立，局限见 §6.5 |
| 11 | §6.3 批次规则（四个终结点 + 三条触发条件） | |
| 12 | §7.4 `canSend` 不依赖归属 | |
| 13 | §2.1 chunk 级析取隔离 | 论证路径见 §2.1 |

---

## 十、范围外

- **后端 Layer 1b 写入逻辑**：PRD 声明由配套 Backend Story 负责；调研确认已实现，本设计不动。
- **文件上传 UI 本体**（chip、进度、校验）：已实现。
- **推断结果持久化 / 跨会话记忆**：本期不做，推断仅作前端初始值。
- **归属的持久化回显**：需改消息侧契约，见 §6.5 局限。
- **事后修改归属**：现有接口不支持，纠错走删除 + 重传。
- **公司端归属选择**：公司端无此需求，形态不变。

### 附：需知会后端的既有缺口（非本设计引入）

本次让「AI 推断的归属」直接生效，以下两处既有缺口的风险权重相应上升，建议单独排查：

1. `POST /api/ai/file-registry/records` 实际是 upsert，可无校验地改写任意 fileId 的归属公司。
2. `register_session_file` 缺少 `register_playbook_file` 已有的 business_type 守卫，能把公司 KB 行改成无公司的会话行。
