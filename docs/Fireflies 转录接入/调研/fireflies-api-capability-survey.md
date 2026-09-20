# Fireflies 转录接入 — API 能力与数据质量调研
> **阶段**：① 调研　**日期**：2026-09-18　
> 
> **目的**：评估方案可行性，不涉及落地实现
> **数据来源**：实测 Fireflies GraphQL API（`https://api.fireflies.ai/graphql`）；MCP 通道（`https://api.fireflies.ai/mcp`）与其 OAuth 授权流程于 2026-09-20 另行实测，见 3.0。
>
> **账号** `tingting@whalesongproduct.com`（`is_admin: true`），样本 **43 场真实会议 / 19,261 条句子**
> **多租户口径**：一把 API key 归属一个租户，该 key 下所有会议都属于这个租户。

---

## 1. 结论

**方案可行**——Fireflies 能提供所需的全部原料：可按租户拉取全部会议、正文带说话人与时间戳、自带多档摘要（可省下自建 LLM 摘要的成本）、支持 Webhook 与按日期增量拉取。

**实现范围**：需**同时实现 API key 与 MCP/OAuth 两条对接通道**（2026-09-20 澄清）。两条通道的数据不等价——MCP 缺 7 个会议字段、逐句丢 `ai_filters` 等 4 项、时间戳降到秒级，且 OAuth 凭据不能用于 GraphQL，**客户选哪种连接方式即决定其数据精度**。详见 3.0，设计阶段需据此规划凭据存储与下游降级。

但有 **三条必须写进前提**：

### 前提一：必须有「这场会能不能用」的准入判断

实测 43 场里，**2 场完全没有摘要**，**3 场句子颗粒度崩坏**（>30 秒/句，意味着整场会只捞到零星词句）。

### 前提二：五个摘要字段实测恒空，方案不能依赖

`outline`、`topics_discussed`、`meeting_type`、`transcript_chapters`、`short_overview` 在全部样本中填充率 **0%**，`extended_sections` 仅 5%（2/43）。schema 里有不代表会填。可用的是 `overview`／`short_summary`／`gist`／`keywords`／`action_items`／`bullet_gist`／`shorthand_bullet`（均 91%+），以及 `notes`（72%）。

### 前提三：公司识别准确率尚未验证，且输入质量会拖累它

「一场会提到哪些公司、各自抽哪段内容」是本方案的核心，目前**未经实测**。而输入端存在 ASR 错字（样本中可见 `"Okay full out."` 这类识别错误）、说话人识别不全（某场 9 名参会者只识别出 2 个说话人），都会直接拖累识别效果。

**风险不对称**：漏识别 = 该公司知识库少内容（静默）；错识别 = **A 公司的内容进了 B 公司的知识库**，属跨租户数据泄漏，后果严重得多。下一步应先用真实数据验证这一步的准确率，再谈落地。

---

## 2. 需求与 Fireflies 能力对照

| 需求 | Fireflies 提供 | 接口 |
|---|---|---|
| 拉取该租户全部会议 | ✅ 支持按日期/关键词/参会人过滤 + 分页 | `transcripts` |
| 会议正文（识别公司、抽取内容） | ✅ `sentences`，带说话人 + 起止时间戳 | `transcript` |
| 会议摘要（省自建 LLM 成本） | ✅ 多档摘要，`overview` / `action_items` 等可直接用 | `transcript.summary` |
| 增量同步 | ✅ Webhook（仅 `Transcription completed`）+ `fromDate/toDate` 轮询 | Webhook / `transcripts` |
| 参会者（辅助公司归属） | ✅ 邮箱列表，可用域名反推公司 | `transcript.participants` |

### 限流（官方文档）

| 套餐 | 限额 | 价格（USD / 席位 / 月） |
|---|---|---|
| Free | 50 次/天 | $0 |
| Pro | 500 次/天 | 年付 $10；月付 $18 |
| Business | 60 次/分钟 | 年付 $19；月付 $29 |
| Enterprise | 60 次/分钟 | 年付 $39 起（仅年付，50 席以上走销售报价） |

⚠️ `transcripts` 查询的 `limit` **上限为 50**，超过需用 `skip` 分页。会议量大的租户必须分页。

✅ **GraphQL 不需要「列表 + 逐场详情」两段式**：`transcripts` 与 `transcript` 同为 `Transcript` 类型，`sentences`、`summary` 可直接写进列表查询——实测一次 `transcripts(limit:50)` 即返回 43 场会议、19,261 条句子及全部摘要。故按日期增量拉取时，**每 50 场仅消耗 1 次配额**。（MCP 通道则必须逐场取正文，见 3.0。）

✅ **口径冲突已实测澄清（2026-09-18）**：官方 API 文档为 Free 列了 50 次/天配额，而 fireflies.ai/pricing 把「API access」写在 Business 档下，二者看似矛盾。实测结论是**前者为准，但有前提**：

- **API 本身对 Free 开放**——本次调研所用 key 即 Free 账号，`transcripts` / `transcript` / `user` 全部正常返回，43 场会议、正文、摘要一个不缺。
- **个别字段按套餐收费**：请求 `audio_url` / `video_url` 时返回 `paid_required`（HTTP 403，`extensions.metadata.tier = "pro_or_higher"`），即**音视频链接需 Pro 及以上**。本方案不消费音视频，不受影响。
- 因此价格页的「API access」应理解为**完整 API 能力**，而非「Free 完全不能调」。

⚠️ 由此引出一条**接入时必须处理的行为**：GraphQL 对这种部分失败返回 **HTTP 200 + `data` 中该字段为 `null` + `errors` 数组**，而非整体报错。上例中其余 28 个字段照常返回。**判定成功不能只看 HTTP 状态码，必须检查响应体的 `errors`**，否则套餐降级、字段权限变化都会表现为「字段悄悄变空」而无人察觉。

---

## 3. 可用接口清单（含返回字段）

### 3.0 两条接入通道：GraphQL + API key / MCP + OAuth

Fireflies 对外有**两条互不相通的通道**，认证方式和数据形态都不同。下表为 2026-09-18 实测对比（实测 = 本次亲自调通并验证，非文档转述）：

| 对比项 | GraphQL + API key | MCP + OAuth |
|---|---|---|
| 端点 | `POST https://api.fireflies.ai/graphql` | `https://api.fireflies.ai/mcp` |
| 认证 | `Authorization: Bearer <API_KEY>` | OAuth 2.1 授权码 + PKCE(S256) |
| 凭据怎么来 | **用户手动生成后粘贴给我们** | **跳转授权页，用户点同意**，无需粘贴 |
| 我方需注册应用 | 否 | 是，但支持**动态注册**（`POST /register` 实测 201，无需审批） |
| 凭据有效期 | 无（静态，不过期） | 实测 `expires_in` **90 天**，带 `refresh_token` |
| 可撤销 | 只能用户自己重置 key（影响所有用途） | ✅ 有 `revocation_endpoint` |
| 授权范围 | 全权限，含 20 个 Mutation（**可删会议**） | 20 个工具，其中 6 个写（改标题/隐私/分享/移动/剪辑）；**无删除** |
| scope 粒度 | 无 | 仅 `profile` / `email`，**无只读选项** |
| 跨通道可用 | — | ❌ 实测该 token 调 GraphQL 返回 `auth_failed` |
| 返回格式 | 结构化 JSON，字段任选 | 详情接口为**面向 LLM 的纯文本**（见下） |
| 拉取 50 场（含正文+摘要） | **1 次调用**——`transcripts` 与 `transcript` 同为 `Transcript` 类型，`sentences` 可直接写进列表查询（实测一次返回 43 场 / 19,261 句 / 含 summary） | **51 次起**：列表不含 `sentences`，正文须逐场取（1 + N）；若还要 `overview`／`notes` 等完整摘要，再加 N 次 `get_summary`（1 + 2N） |
| 限流 | 见 §2 | 官方说明**与 GraphQL 共用同一套配额** |

**MCP 的两条硬约束**（决定选型，实测 + 官方文档双向确认）：

1. **详情接口不支持 JSON**。<br/> `format` 参数（`toon` 默认 / `json` / `text`）只有 `fireflies_search`、`fireflies_get_transcripts`、`fireflies_get_soundbites`、`fireflies_get_user_contacts` 四个工具支持；<br/>**`fireflies_get_transcript` / `fireflies_get_summary` / `fireflies_fetch` 只接受 id，没有 format**，返回给 LLM 阅读的格式化文本。<br/>**实测** `fireflies_get_user` 返回即为 “User Id: …” / “Email: …” 这种逐行排布的纯文本。用于数据管道需要文本解析，比 GraphQL 脆弱。

2. **调用次数相差一个数量级**。GraphQL 的列表与详情是同一类型的两种取法，可在一次查询里把 50 场会议的正文与全部摘要一起取回；MCP 的 `get_transcripts` **不含 `sentences`**（官方描述 “excludes detailed transcript content”，实测确认），正文只能逐场调 `get_transcript`。

   | 拉 50 场会议（含正文+摘要） | 调用次数 |
   |---|---|
   | GraphQL | **1** |
   | MCP —— 列表自带的 `short_summary`／`keywords`／`action_items` 够用 | 1 + 50 = **51** |
   | MCP —— 还需要 `overview`／`notes`／`gist` 等完整摘要 | 1 + 100 = **101** |

   两条通道**共用同一套配额**（§2），因此 **Free 套餐（50 次/天）下走 MCP 一天拉不完 50 场会，而 GraphQL 一次调用即可**。

   `fireflies_fetch` 能一次返回「transcript + summary + analytics + metadata」，可把 MCP 降到 1 + N，但官方标注为实验特性：“may not be available to all users. They are being progressively rolled out and may require feature flag enablement.”——**不能作为方案基础**。

**字段是否同源——2026-09-18 实测结论：数据同源，差在序列化与粒度**

测法：把一场会议（`01KZYS4QBCSC54X8BTSB6G9Y35`，48 分钟）分享给 OAuth 账号后，用 MCP 与 GraphQL 分别取同一场会对比。

**结论 1：底层数据完全一致。** MCP 返回的空值分布与 GraphQL 逐项吻合——GraphQL 实测为空的字段（`transcript_chapters`、`audio_url` 等），MCP 同样为空，只是以占位文案呈现（`No transcript chapters`、`No audio url`）而非 `null`。**不存在"MCP 能拿到 GraphQL 拿不到的数据"或反之的情况。**

**结论 2：差异在表达方式，不在数据本身。** 四点实测差异：

| 差异 | GraphQL | MCP |
|---|---|---|
| 详情序列化 | JSON | **纯文本**（`get_transcript` 实测 53 KB、`get_summary` 16 KB，形如 `Id: …` / `Title: …` 逐行排布） |
| 列表序列化 | JSON | 可选 JSON（`format:"json"`），但**字段名为驼峰**（`organizerEmail`／`meetingLink`），与 GraphQL 的下划线（`organizer_email`）不一致 |
| 详情字段覆盖 | 30 个 | **21 个标签**；缺 `analytics`、`workspace_users`、`shared_with`、`meeting_attendance`、`meeting_info`、`apps_preview`、`channels` |
| 列表内嵌摘要 | 可取全部 14 子字段 | 仅 `short_summary`／`keywords`／`action_items` 三项 |

**结论 3（对本方案最关键）：逐句粒度被压平。** GraphQL 的 `Sentence` 有 8 个字段，MCP 把整段正文渲染成这种形式：

```
[00:02 - 00:04] Karen Arnoldi: We are recording here.
```

即**只保留说话人名、分秒级时间区间、文本**。丢失 `speaker_id`、`raw_text`、浮点秒精度，以及 `ai_filters` 的 7 个子字段（`sentiment`、`task`、`pricing`、`metric`、`question` 等）。按话轮切 chunk 仍可行，但基于 `ai_filters` 的筛选能力没有了。

**结论 4：摘要小节 MCP 一个不少。** `get_summary` 实测含 Keywords、Action Items、Overview、Notes、Gist、Bullet Gist、Shorthand Bullet、Short Summary、Transcript Chapters；未出现的 Outline／Topics Discussed／Meeting Type／Extended Sections／Short Overview **正是 4.1 中实测填充率为 0% 的那几个**。（此处修正本文早前基于官方文档的"MCP 只暴露 6 项"的说法——官方文档未列全，以实测为准。）

**附带发现**：同为 Free 账号，GraphQL 请求 `audio_url` 返回 `paid_required`（403 错误），MCP 则返回 `No audio url` 字符串。**MCP 对付费字段是降级而非报错**，接入时不能靠"有没有报错"判断字段是否可用。

**实现范围：两条通道都要做**（2026-09-20 需求澄清）

本方案**同时实现 API key 与 MCP/OAuth 两种对接方式**，由客户选择其一连接。两者并非备选关系，而是都要落地。

由此产生一个**必须在设计阶段就正视的后果**：

> **两条通道拿到的数据不等价，因此同一套知识库里会混进两种质量的数据。**
>
> MCP 通道相对 GraphQL 缺失：`analytics`、`workspace_users`、`shared_with`、`meeting_attendance`、`meeting_info`、`apps_preview`、`channels` 共 7 个字段；逐句层面丢失 `speaker_id`、`raw_text`、浮点秒精度与 `ai_filters` 的 7 个子字段（含 `sentiment`）；时间戳精度降到秒（实测平均误差 0.51s、最大 0.99s）。
>
> 且 **OAuth 凭据无法用于 GraphQL**（实测 `auth_failed`），所以"用 OAuth 授权、用 GraphQL 取数"这个组合不存在——客户选了哪种连接方式，就决定了他的数据走哪条通道、拿到哪个精度。

设计上需要据此明确三件事：① 凭据表要能同时承载「静态 key」与「OAuth token + refresh_token + 过期时间」两类形态；② 入库后的条目应记录来源通道，便于排查"为什么这家公司的数据没有 sentiment"；③ 依赖 `ai_filters`、精确时间戳的下游功能，必须对 MCP 来源的数据做降级处理，不能假设字段一定存在。

#### 工程实现：与现有 QuickBooks 授权的异同

MCP/OAuth 这条通道的跳转授权流程，可直接参考仓库内已有的 QuickBooks 实现（前端入口 `web/CIOaas-web/src/pages/companySettings/components/finance/FinanceTab.tsx`，后端回调 `java/CIOaas-api/.../fi/service/FinancialSettingServiceImpl.java`）。整体骨架一致：

```
前端整页跳转 → 后端拼授权 URL → 302 到第三方 → 用户同意
→ 第三方回调后端 → code 换 token → 存库 + 绑定租户 → 302 回业务页
```

但有三处**不能照搬**：

| 差异 | QuickBooks 现状 | Fireflies MCP |
|---|---|---|
| 客户端类型 | 机密客户端，有 `client_secret`（Intuit SDK 代劳） | **公开客户端**（动态注册返回 `token_endpoint_auth_method: "none"`，无 secret），**强制 PKCE（S256）** |
| 服务端状态 | **不存任何状态**，`state` 仅为 `companyId,roleType,userId` 明文拼接，回调只拆字符串（**无 CSRF 校验**） | PKCE 要求回调时提供 `code_verifier`，**必须按 state 在服务端存取 verifier**——天然要求做 QuickBooks 漏掉的那件事，顺带堵上 CSRF |
| 第三方账号标识 | 每次调 API 都要带 `realmId`，需随 token 一起存 | token 隐含工作区身份，**无需额外字段** |
| 令牌节奏 | access 约 1 小时 / refresh 约 100 天，采用「调用失败就地刷新」 | access **90 天**滚动续期，宜**定时集中刷新**；实测刷新会使旧 access 立即失效，**刷新必须单点，不能每个 worker 各自刷** |

另注：QuickBooks 申请的是 `Scope.Accounting`，而 Fireflies 只有 `profile` / `email` 两个 scope，**没有只读粒度可选**。

#### OAuth 凭据生命周期（2026-09-18 实测）

| 行为 | 实测结果 | 对实现的含义 |
|---|---|---|
| access_token 有效期 | 固定 `expires_in = 7776000`（90 天），客户端无法指定 | 服务端单方面决定，协议上也无参数可调 |
| 刷新后有效期 | **每次刷新重新给满 90 天**（连续多次实测均为整 7776000，差值 0 秒） | 不是「总共只能用 90 天」，而是**滚动窗口**；只要 90 天内刷一次即可无限续期 |
| refresh_token | 每次刷新都轮换出新值 | 必须把新值写回存储，否则下次刷新用的是旧值 |
| 旧 refresh_token | 轮换后**数秒内仍可换出新 token（HTTP 200），数分钟后失效（HTTP 400）** | 表现符合**短时宽限窗口**（用于容忍并发刷新），不是"旧凭据长期有效"。窗口具体时长未测。仍应按长期密钥保管，但不必据此判定其安全模型有缺陷 |
| 旧 access_token | 刷新后**立即失效**（实测 401） | access token 单活。**多进程各自刷新会互相踢下线**，刷新动作必须集中（加锁或单点），不能每个 worker 自己刷 |

**真正的断链风险不是 90 天**——那靠程序自动刷新即可解决。会导致 refresh 彻底失败的是：用户主动撤销授权、改密码、账号停用、离职。这些发生时**没有任何预警**，且只能请用户重新授权一次。所以无论走哪条通道，「凭据失效 → 通知用户重新授权」这个环节都省不掉（参见 QuickBooks 现有实现的邮件召回机制）。

---

### 3.1~3.5 以下均为 GraphQL 通道

端点：`POST https://api.fireflies.ai/graphql`　认证：`Authorization: Bearer <API_KEY>`

API key 获取：Fireflies 后台 → Integrations → 搜 `Fireflies API` → Get API Key；或 Settings → Developer settings（Personal tab）。**所有套餐均可用**。

### 3.1 `transcripts` — 会议列表（核心）

**请求参数**（官方文档）——本节唯一一张入参表，3.2 起均为返回字段：

| 参数 | 说明 |
|---|---|
| `keyword` | 在标题和/或发言内容中搜索关键词 |
| `scope` | 搜索范围：title / sentences / all |
| `fromDate` / `toDate` | ISO 8601 时间区间——**增量同步靠这个** |
| `limit` | **上限 50** |
| `skip` | 分页偏移 |
| `user_id` | 按用户过滤 |
| `mine` | 布尔，只看 API key 持有者的会议 |
| `organizers` | 组织者邮箱数组 |
| `participants` | 参会者邮箱数组 |
| `host_email` | 主持人邮箱 |
| `channel_id` | 频道 |
| ~~`title`~~ / ~~`date`~~ / ~~`organizer_email`~~ / ~~`participant_email`~~ | **已废弃**，分别改用 `keyword` / `fromDate,toDate` / `organizers` / `participants` |

**返回**：`Transcript` 列表，字段与 3.2 相同（按需取，GraphQL 只返回请求的字段）。

```graphql
{ transcripts(fromDate: "2026-09-01T00:00:00Z", limit: 50, skip: 0) {
    id title dateString duration participants
  } }
```

### 3.2 `transcript(id)` — 会议详情（核心，30 个字段）

**请求参数**：仅 `id`（String，必填）。

**返回字段**（30 个）。「返回示例」列为 2026-09-18 实测真实取值，样本会议 `ERL + LG huddle`（id `01M2K2WWFXH01WZCBFAV5M0YPZ`，39 分钟 / 4 位说话人 / 51 句）：

| 分组 | 字段 | 返回示例（实测） |
|---|---|---|
| **正文** | `sentences` | 51 条，逐句 8 子字段见 3.3 |
| **正文** | `transcript_url` | `https://app.fireflies.ai/view/01M2K2WWFXH01WZCBFAV5M0YPZ` |
| **摘要** | `summary` | 14 子字段，见 3.4 |
| **归属/鉴权** | `host_email` | `li.wang@goldensection.com` |
| **归属/鉴权** | `organizer_email` | `li.wang@goldensection.com`（本场与 host 相同） |
| **归属/鉴权** | `user` | `{user_id:"P3oUHZW4st", name:"Li Wang", num_transcripts:277, is_admin:false}` |
| **归属/鉴权** | `privacy` | `"teammatesandparticipants"` |
| **归属/鉴权** | `fireflies_users` | 5 个邮箱（装了 Fireflies 的参会人） |
| **归属/鉴权** | `workspace_users` | 1 个邮箱（与 key 同工作区的人） |
| **归属/鉴权** | `shared_with` | `[]`（本场未分享） |
| **会议元信息** | `title` | `"ERL + LG huddle"` |
| **会议元信息** | `date` | `1789696800000`（毫秒时间戳） |
| **会议元信息** | `dateString` | `"2026-09-18T02:00:00.000Z"` |
| **会议元信息** | `duration` | `39.06`（**单位是分钟，不是秒**） |
| **会议元信息** | `participants` | 6 个邮箱字符串 |
| **会议元信息** | `meeting_attendees` | `[{email:"li.wang@…", displayName:null, name:null, location:null}]`——**除邮箱外基本全 null** |
| **会议元信息** | `meeting_attendance` | `[{name:"Li Wang", join_time:"…T02:00:51Z", leave_time:"…T02:38:10Z"}]` |
| **会议元信息** | `speakers` | `[{id:0,name:"Chunru Liang"}, …]`（4 人） |
| **会议元信息** | `meeting_link` | `"https://teams.microsoft.com/l/meetup-join/19:meeting_…"` |
| **会议元信息** | `calendar_id` | `"040000008200E00074C5B7101A82E008…"`（Outlook 长 id） |
| **会议元信息** | `cal_id` | `"AAMkADFkM2Y1MDg4LTcxMWYtNDEzYi04ZWI4…"` |
| **会议元信息** | `calendar_type` | `"outlook"` |
| **会议元信息** | `analytics` | `null`——**本场无数据**，不可依赖 |
| **会议元信息** | `meeting_info` | `{silent_meeting:false, summary_status:"processed", fred_joined:true}` |
| **媒体** | `audio_url` | ❌ 实测报 `paid_required`（403，`tier: pro_or_higher`）；本方案不用 |
| **媒体** | `video_url` | ❌ 同上；本方案不用 |
| **其他** | `id` | `"01M2K2WWFXH01WZCBFAV5M0YPZ"` |
| **其他** | `is_live` | `false` |
| **其他** | `apps_preview` | `{outputs: []}`（空） |
| **其他** | `channels` | `[]`（空） |

> ⚠️ **原表少列了 `meeting_info`**：schema 实有 30 个字段，原表只列出 29 个，已补。
>
> ⚠️ **`duration` 单位是分钟**：`39.06` 对应实际 02:00:51→02:38:10 约 37 分钟。按秒理解会把时长算错 60 倍。
>
> ⚠️ **`meeting_attendees` 名字列全是 null**：实测只有 `email` 有值，`displayName` / `name` / `location` / `phoneNumber` 均为 null。要人名请取 `speakers` 或 `meeting_attendance`。

### 3.3 `Sentence` — 正文逐句（8 字段）

示例取自样本会议第 0 句：

| 字段 | 类型 | 说明 | 返回示例（实测） |
|---|---|---|---|
| `index` | Int | 句序号 | `0` |
| `speaker_name` | String | 说话人姓名 | `"Chunru Liang"` |
| `speaker_id` | Int | 说话人 id | `0`（对应 `speakers[].id`） |
| `text` | String | 文本（清洗后） | `"Hello hello?"` |
| `raw_text` | String | 原始文本 | `"Hello hello?"`（本场与 `text` 一致） |
| `start_time` | Float | 起始秒 | `0.08` |
| `end_time` | Float | 结束秒 | `1.76` |
| `ai_filters` | AIFilters | AI 标注 | `{text_cleanup:"Hello hello?", question:"Hello hello?", sentiment:"neutral", task:null, pricing:null, metric:null, date_and_time:null}` |

`ai_filters` 的 7 个子字段：`text_cleanup`、`task`、`pricing`、`metric`、`question`、`date_and_time`、`sentiment`。实测 51 句**全部**返回该对象，但多数子字段为 null——`sentiment` 和 `text_cleanup` 基本恒有值，`task` / `pricing` / `metric` 只在相关句子上才填。

→ **有说话人 + 时间戳**，切 chunk 可按话轮而非字数硬切，召回时能带「谁在第几分钟说的」。

### 3.4 `Summary` — 摘要（14 字段，含 5 个恒空）

填充率与平均长度见 4.1；下表给字段含义与实测取值样例：

| 字段 | 说明 | 返回示例（实测） |
|---|---|---|
| `overview` | 分点总览，最常用 | `"- **Meeting start:** Participants confirmed readiness…"`（约 916 字符） |
| `short_summary` | 段落式摘要 | `"Participants began with readiness checks and brief status remarks…"` |
| `gist` | 一句话要旨 | `"The meeting addressed expense classification, file-upload errors…"` |
| `keywords` | 关键词数组 | `["closing activities","expense categorization","file upload issues", …]`（平均 6 个） |
| `action_items` | 待办，按人分组的 Markdown | 形如 `**Chunru Liang**` 换行接 `Review and finalize last month’s closing documentation…`，每人一段（平均 1134 字符） |
| `bullet_gist` | 要点列表 | 分点 Markdown，平均 692 字符 |
| `shorthand_bullet` | 速记要点，最详细的分点 | 平均 2347 字符 |
| `notes` | 结构化笔记，最长 | 平均 6533 字符，**但仅 72% 有值** |
| `extended_sections` | 分节摘要，`[{title, content}]` | 章节名如 `Meeting Outline` / `Topics` / `Decisions` / `Key Takeaways`；**仅 2/43 有值** |
| `short_overview` | —— | ❌ **恒空**（0/43） |
| `outline` | —— | ❌ **恒空**（0/43） |
| `topics_discussed` | —— | ❌ **恒空**（0/43） |
| `meeting_type` | —— | ❌ **恒空**（0/43） |
| `transcript_chapters` | —— | ❌ **恒空**（0/43） |

> ⚠️ 原文写「含 4 个恒空」，实测补测 `short_overview` 后为 **5 个恒空**；`extended_sections` 填充率仅 5%（2/43），同样不可依赖。

### 3.5 `user` / `users` — 账号与团队

`user` 返回 key 持有者自己的账号信息（示例为本次实测所用 key）：

| 字段 | 说明 | 返回示例（实测） |
|---|---|---|
| `user_id` | 用户 id | `"01K73SAVP0XTFEJQNCMAZQCJFC"` |
| `name` | 姓名 | `"Tingting Song"` |
| `email` | 邮箱 | `"tingting@whalesongproduct.com"` |
| `is_admin` | 是否管理员 | `true` |
| `num_transcripts` | 本人会议数 | `1` |
| `minutes_consumed` | 已消耗分钟数 | `48.97` |
| `is_calendar_in_sync` | 日历是否同步 | `true` |
| `integrations` | 已接集成 | `null` |
| `recent_transcript` | 最近一场会议 id | `"01KZYS4QBCSC54X8BTSB6G9Y35"` |
| `recent_meeting` | 最近一场会议 | `"01KZYS4QBCSC54X8BTSB6G9Y35"` |
| `user_groups` | 所属分组（`id`/`name`/`handle`/`members`） | `[]`（本账号无分组） |

> ⚠️ **`num_transcripts` 只统计本人的会议，不等于能拉到的会议数**：该 key 的 `num_transcripts` 为 1，但 `transcripts` 实际返回 43 场——列表接口给的是**整个工作区可见**的会议。估算数据量不要用这个字段。

### 3.6 其余 Query（暂不需要，备查）

| 接口 | 作用 |
|---|---|
| `analytics(start_time, end_time)` | 会议分析统计 |
| `contacts` | 联系人列表——**可能对公司归属有用** |
| `askfred_threads` / `askfred_thread` | Fireflies 自带 AI 问答线程 |
| `bites` / `bite` | 会议片段剪辑 |
| `channels` / `channel`、`user_groups` | 频道 / 用户组 |
| `apps` | 应用集成输出 |
| `active_meetings` | 进行中的会议 |
| `live_action_items` | 实时行动项 |
| `rule_executions_by_meeting` | 规则执行日志 |
| `auditEvents` | 审计事件 |

### 3.7 ⚠️ Mutation：接入时应避开

共 20 个写接口。**我们是只读消费方，接入时不应调用任何 Mutation。**

---

## 4. 数据质量实测

样本：**全部 43 场会议**
### 4.1 摘要字段填充率

| 字段 | 有值 | 填充率 | 平均长度 | 可用性 |
|---|---|---|---|---|
| `overview` | 41/43 | 95% | 916 字符 | ✅ 可用 |
| `short_summary` | 41/43 | 95% | 835 字符 | ✅ 可用 |
| `gist` | 41/43 | 95% | 132 字符 | ✅ 可用 |
| `keywords` | 41/43 | 95% | 6 个 | ✅ 可用 |
| `action_items` | 41/43 | 95% | 1134 字符 | ✅ 可用 |
| `bullet_gist` | 41/43 | 95% | 692 字符 | ✅ 可用 |
| `shorthand_bullet` | 39/43 | 91% | 2347 字符 | ✅ 可用 |
| `notes` | 31/43 | 72% | 6533 字符 | ⚠️ 部分缺失 |
| `extended_sections` | 2/43 | 5% | 12612 字符 / 8 段 | ❌ 近乎恒空 |
| `outline` | 0/43 | 0% | 0 字符 | ❌ **恒空，不可依赖** |
| `topics_discussed` | 0/43 | 0% | 0 字符 | ❌ **恒空，不可依赖** |
| `meeting_type` | 0/43 | 0% | 0 字符 | ❌ **恒空，不可依赖** |
| `transcript_chapters` | 0/43 | 0% | 0 字符 | ❌ **恒空，不可依赖** |
| `short_overview` | 0/43 | 0% | 0 字符 | ❌ **恒空，不可依赖** |

**要点**：

- `notes` 最长（平均 6533 字符），`overview` / `short_summary` 长度适中，**可直接当 `ai_rag_entry.summary` 用，省下自建 LLM 摘要的调用**
- `outline` / `topics_discussed` / `meeting_type` / `transcript_chapters` / `short_overview` **填充率 0%**，方案不可依赖；`extended_sections` 仅 5%（2/43），同样不可依赖
- 原表遗漏 `short_overview` / `extended_sections` 两个字段（Summary 实有 14 个，原表只列 12 个），已于 2026-09-18 补测
- 2 场完全没有摘要

### 4.2 逐场质量表（全部 43 场）

`秒/句` 是「时长 ÷ 句数」，正常值 5~10；>30 表示整场只捞到零星词句。

| # | 会议 | 日期 | 时长(min) | 句数 | 字符 | 秒/句 | 参会 | 说话人 | 摘要 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ERL + LG huddle | 2026-09-18 | 39.1 | 51 | 579 | 46.0 | 6 | 4 | 有 | ❌ 不可用 |
| 2 | LG Weekly Business Requirements Discussion | 2026-08-28 | 32.8 | 283 | 22586 | 7.0 | 9 | 2 | 有 | ✅ 可用 |
| 3 | LG Weekly Business Requirements Discussion | 2026-08-28 | 50 | 295 | 23675 | 10.2 | 9 | 2 | 有 | ✅ 可用 |
| 4 | ERL + LG huddle | 2026-08-28 | 19.1 | 36 | 277 | 31.9 | 7 | 4 | **无** | ❌ 不可用 |
| 5 | LG Weekly Business Requirements Discussion | 2026-08-21 | 49.0 | 504 | 35469 | 5.8 | 8 | 2 | 有 | ✅ 可用 |
| 6 | ERL + LG huddle | 2026-08-14 | 42 | 23 | 152 | 109.6 | 6 | 2 | **无** | ❌ 不可用 |
| 7 | ERL + LG huddle | 2026-07-24 | 24.5 | 59 | 818 | 24.9 | 6 | 3 | 有 | ⚠️ 偏差 |
| 8 | Exit Readiness feature review | 2026-07-21 | 28.2 | 346 | 17821 | 4.9 | 6 | 4 | 有 | ✅ 可用 |
| 9 | LG Storytelling and Product Coordination | 2026-05-19 | 31 | 369 | 19263 | 5.0 | 7 | 2 | 有 | ✅ 可用 |
| 10 | LG Storytelling and Product Coordination | 2026-04-21 | 79.7 | 830 | 38038 | 5.8 | 6 | 4 | 有 | ✅ 可用 |
| 11 | LG Storytelling and Product Coordination | 2026-04-10 | 58.8 | 825 | 35689 | 4.3 | 7 | 3 | 有 | ✅ 可用 |
| 12 | UX / Dev sync | 2026-04-09 | 93.6 | 1245 | 49320 | 4.5 | 6 | 2 | 有 | ✅ 可用 |
| 13 | LG Storytelling and Product Coordination | 2026-03-31 | 73.0 | 950 | 45200 | 4.6 | 7 | 4 | 有 | ✅ 可用 |
| 14 | LG Q1 Magna Retrospective – Let’s Reflect, Ali | 2026-03-27 | 64.3 | 630 | 42531 | 6.1 | 13 | 9 | 有 | ✅ 可用 |
| 15 | LG recurring Design Meting | 2026-03-10 | 24.1 | 310 | 16411 | 4.7 | 7 | 2 | 有 | ✅ 可用 |
| 16 | LG Workflow & Backlog review / Housekeeping | 2026-02-27 | 29.0 | 330 | 20078 | 5.3 | 11 | 5 | 有 | ✅ 可用 |
| 17 | Following: UAT Working Session – Review & Alig | 2026-02-25 | 42.7 | 399 | 24892 | 6.4 | 9 | 5 | 有 | ✅ 可用 |
| 18 | LG Storytelling and Product Coordination | 2026-02-24 | 62.6 | 796 | 37582 | 4.7 | 8 | 4 | 有 | ✅ 可用 |
| 19 | LG Storytelling and Product Coordination | 2026-02-10 | 26.6 | 405 | 16528 | 3.9 | 8 | 4 | 有 | ✅ 可用 |
| 20 | LG Internal Aligment Touchbase | 2026-02-04 | 35.4 | 405 | 24244 | 5.2 | 14 | 7 | 有 | ✅ 可用 |
| 21 | LG Storytelling and Product Coordination | 2026-01-27 | 36.0 | 425 | 23422 | 5.1 | 8 | 4 | 有 | ✅ 可用 |
| 22 | VerityPay: API scope touchbase | 2026-01-19 | 29.7 | 312 | 21366 | 5.7 | 5 | 3 | 有 | ✅ 可用 |
| 23 | LG Storytelling and Product Coordination | 2026-01-16 | 32.4 | 411 | 20767 | 4.7 | 8 | 4 | 有 | ✅ 可用 |
| 24 | Verity: 3 months scope touchbase | 2025-12-31 | 31.9 | 367 | 16921 | 5.2 | 6 | 4 | 有 | ✅ 可用 |
| 25 | Verity - Quick Call | 2025-12-23 | 47.3 | 548 | 32122 | 5.2 | 5 | 4 | 有 | ✅ 可用 |
| 26 | Beyond79/VerityPay Integration Call | 2025-12-18 | 36.9 | 465 | 29345 | 4.8 | 10 | 7 | 有 | ✅ 可用 |
| 27 | LG Storytelling and Product Coordination | 2025-12-17 | 45.1 | 655 | 27802 | 4.1 | 7 | 5 | 有 | ✅ 可用 |
| 28 | Verity touchbase: Code Quality Assessment | 2025-12-04 | 26.4 | 279 | 17103 | 5.7 | 5 | 3 | 有 | ✅ 可用 |
| 29 | LG Storytelling and Product Coordination | 2025-12-02 | 65.1 | 803 | 37665 | 4.9 | 8 | 4 | 有 | ✅ 可用 |
| 30 | LG Storytelling and Product Coordination | 2025-11-07 | 65.1 | 962 | 44211 | 4.1 | 6 | 7 | 有 | ✅ 可用 |
| 31 | LG Storytelling and Product Coordination | 2025-11-04 | 12.8 | 224 | 7474 | 3.4 | 6 | 3 | 有 | ✅ 可用 |
| 32 | LG All Hands: Roadmap and Strategy Review | 2025-10-28 | 44.4 | 587 | 34223 | 4.5 | 9 | 9 | 有 | ✅ 可用 |
| 33 | Following: VerityPay: Kick-off with Devs & Bus | 2025-10-28 | 22.1 | 318 | 15531 | 4.2 | 11 | 5 | 有 | ✅ 可用 |
| 34 | LG Storytelling and Product Coordination | 2025-10-15 | 17.0 | 240 | 10751 | 4.3 | 7 | 3 | 有 | ✅ 可用 |
| 35 | LG Storytelling and Product Coordination | 2025-09-23 | 52.0 | 692 | 33175 | 4.5 | 6 | 5 | 有 | ✅ 可用 |
| 36 | LG: UAT Items Catch-up and Storytelling | 2025-09-10 | 40.1 | 488 | 26326 | 4.9 | 10 | 4 | 有 | ✅ 可用 |
| 37 | Following: LG touchbase | 2025-08-20 | 77.3 | 261 | 14997 | 17.8 | 12 | 6 | 有 | ⚠️ 偏差 |
| 38 | Verity Touchbase: Transactions Volume | 2025-05-29 | 28.6 | 321 | 19606 | 5.3 | 7 | 4 | 有 | ✅ 可用 |
| 39 | Verity Touchbase | 2025-04-24 | 8.2 | 138 | 5512 | 3.6 | 7 | 3 | 有 | ✅ 可用 |
| 40 | LG Demo: Latest Improvements. | 2025-02-27 | 30.5 | 373 | 22609 | 4.9 | 11 | 6 | 有 | ✅ 可用 |
| 41 | VER touchbase | 2024-12-17 | 45 | 515 | 31334 | 5.2 | 6 | 4 | 有 | ✅ 可用 |
| 42 | MON: Dev Sync and Demo | 2024-12-17 | 26 | 290 | 11015 | 5.4 | 3 | 2 | 有 | ✅ 可用 |
| 43 | LG knowledge transfer | 2024-11-13 | 40 | 496 | 20986 | 4.8 | 12 | 4 | 有 | ✅ 可用 |

**汇总：38/43 场可用（88%）**，其余 5 场需被准入闸门拦下。

### 4.3 典型问题

**① 颗粒度崩坏**——同一账号下差异可达 20 倍以上：

| 会议 | 时长 | 句数 | 秒/句 |
|---|---|---|---|
| ERL + LG huddle | 42 | 23 | 109.6 |
| ERL + LG huddle | 39.1 | 51 | 46.0 |
| ERL + LG huddle | 19.1 | 36 | 31.9 |
| LG Storytelling and Product Coordination | 26.6 | 405 | 3.9 |
| Verity Touchbase | 8.2 | 138 | 3.6 |
| LG Storytelling and Product Coordination | 12.8 | 224 | 3.4 |

**② 说话人识别不全**——参会者数与识别出的说话人数差距明显：

| 会议 | 参会者 | 识别出的说话人 |
|---|---|---|
| LG knowledge transfer | 12 | 4 |
| LG Weekly Business Requirements Discussi | 9 | 2 |
| LG Weekly Business Requirements Discussi | 9 | 2 |
| LG Internal Aligment Touchbase | 14 | 7 |

**③ ASR 错字**——样本中可见 `"Okay full out."` 这类明显识别错误；公司名若被转录错，识别会直接失败。

**④ 寒暄噪声**——多数会议开头是 `Hello.` / `Okay.` / `Yep.` 这类无信息量短句，入库前需合并与过滤，否则会产生大量无意义 chunk 污染召回。

---

## 附录 A：官方文档索引

| 文档 | 地址 | 用途 |
|---|---|---|
| API 主文档 | https://docs.fireflies.ai/introduction | 总入口 |
| Transcript 查询 | https://docs.fireflies.ai/graphql-api/query/transcript | 单场详情字段 |
| Transcripts 列表查询 | https://docs.fireflies.ai/graphql-api/query/transcripts | 列表参数与分页 |
| User 查询 | https://docs.fireflies.ai/graphql-api/query/user | 账号字段 |
| Webhooks | https://docs.fireflies.ai/graphql-api/webhooks | 事件、载荷、签名校验 |
| 取 API key 指引 | https://guide.fireflies.ai/articles/3737786777-fireflies-api-overview-get-api-key | 后台取 key 步骤 |
| **全量文档（LLM 友好）** | https://docs.fireflies.ai/llms-full.txt | **做 demo 时直接喂这个最省事** |
| 文档索引（LLM 友好） | https://docs.fireflies.ai/llms.txt | 文档目录 |
| 套餐与价格（官方博客） | https://fireflies.ai/blog/fireflies-pricing-which-plan-is-right-for-you | §2 价格数字来源 |
| 套餐与价格（官方帮助中心） | https://guide.fireflies.ai/articles/3734844560-learn-about-the-fireflies-pricing-plans | §2 价格数字来源（与上一条互相印证） |
| 价格页 | https://fireflies.ai/pricing | 特性对照；数字为 JS 渲染，抓取不到 |
| MCP 工具清单 | https://docs.fireflies.ai/mcp-tools/overview | §3.0 的工具与 `format` 支持范围来源 |
| MCP 服务端说明 | https://guide.fireflies.ai/articles/8272956938-learn-about-the-fireflies-mcp-server-model-context-protocol | MCP 端点与 OAuth 说明（**注意：该文只列了 3 个工具，与实测 20 个不符，以实测为准**） |
| OAuth 授权服务器元数据 | https://api.fireflies.ai/.well-known/oauth-authorization-server | 公开可取，§3.0 的端点/授权模式来源 |
| OAuth 受保护资源元数据 | https://api.fireflies.ai/.well-known/oauth-protected-resource | 说明 token 受限于 `/mcp` 资源 |

---

## 附录 B：关键接口返回结构对比（API key / MCP）

两条通道对同一场会议的实际返回，用于评估「客户选了哪种连接方式，我们拿到什么」。

> **样本**：`01KZYS4QBCSC54X8BTSB6G9Y35`（`LG Weekly Business Requirements Discussion`，48.97 分钟 / 504 句 / 8 名参会者）
> **测法**：该会议归属 API key 账号，经 `shareMeeting` 分享给 OAuth 账号后，用两条通道分别取同一场会对比。日期 2026-09-20。

### B.0 结构性差异（先看这条）

| | GraphQL + API key | MCP + OAuth |
|---|---|---|
| 列表与详情的类型关系 | **同一个 `Transcript` 类型**，按需选字段——列表也能取正文，详情也能只取标题 | **两个固定形状**，工具决定返回什么，不可裁剪 |
| 字段可选性 | 调用方声明要哪些字段 | 由服务端定死 |
| 命名风格 | 下划线 `organizer_email` | 列表为驼峰 `organizerEmail`；详情为空格标题 `Organizer Email` |

**这是最根本的差异**：GraphQL 里「列表」和「详情」只是同一类型的两种取法；MCP 里它们是两个不同的返回形状。下面按接口分别列。

### B.1 会议列表接口

**请求**

| | GraphQL | MCP |
|---|---|---|
| 调用 | `transcripts(fromDate, toDate, limit, skip, keyword, scope, …)` | `fireflies_get_transcripts(fromDate, toDate, limit, skip, keyword, scope, format)` |
| 分页上限 | `limit` 最大 50 | 同为 50 |
| 输出格式 | JSON（固定） | `format`: `toon`（默认）/ `json` / `text` |

**返回结构**

GraphQL 返回 `Transcript` 数组，**字段由查询语句决定**（可选范围即 3.2 的 30 个字段）。

MCP 在 `format:"json"` 下返回固定 10 个字段：

| MCP 列表字段 | 实测值 | GraphQL 对应                                         |
|---|---|----------------------------------------------------|
| `id` | `"01KZYS4QBCSC54X8BTSB6G9Y35"` | `id`（**值完全相同**）                                    |
| `title` | `"LG Weekly Business Requirements Discussion"` | `title`                                            |
| `dateString` | `"2026-08-21T16:00:00.000Z"` | `dateString`                                       |
| `duration` | `48.970001220703125` | `duration`                                         |
| `organizerEmail` | `"tingting@whalesongproduct.com"` | `organizer_email`（**命名不同**）                        |
| `meetingLink` | Teams 会议链接 | `meeting_link`                                     |
| `participants` | 邮箱数组 | `participants`                                     |
| `meetingAttendees` | `[{displayName: null, email: "karen@…"}]` | `meeting_attendees`（**MCP仅 2 个子字段**，GraphQL 有 5 个） |
| `meetingInfo` | `{fred_joined: true, silent_meeting: false, summary_status: "processed"}` | `meeting_info`                                     |
| `summary` | **仅 3 项**：`short_summary`、`keywords`、`action_items` | `summary`（可取全部 14 子字段）                             |

**列表层面 MCP 取不到**：`host_email`、`privacy`、`speakers`、`transcript_url`、`date`(数值)、`is_live`、`calendar_id`／`cal_id`／`calendar_type`、`fireflies_users`、`workspace_users`、`shared_with`、`meeting_attendance`、`analytics`、`user`。

### B.2 会议详情接口

**请求**

| | GraphQL | MCP |
|---|---|---|
| 调用 | `transcript(id)` —— 一次取全 | `fireflies_get_transcript(transcriptId)` 取正文<br/>`fireflies_get_summary(transcriptId)` 取摘要（**两次调用**；若列表自带的 `short_summary`／`keywords`／`action_items` 已够用，可省去后者，见 3.0 调用次数对比） |
| 输出格式 | JSON | **纯文本，无 `format` 参数** |
| 实测体积 | —— | 正文 53 KB、摘要 16 KB |

`fireflies_fetch(id)` 可一次返回正文+摘要，但官方标注 **Experimental**，不能作为方案基础。

**返回结构**

GraphQL `transcript(id)` 本次实测取到 25 个字段（另有 `audio_url`／`video_url`／`analytics`／`apps_preview`／`channels` 共 5 个未取，合计 30）。

MCP `get_transcript` 返回 21 个顶层标签，形如 `Id: …` 逐行排布：

```
Id: 01KZYS4QBCSC54X8BTSB6G9Y35
DateString: 2026-08-21T16:00:00.000Z
Privacy: link
Speakers: Karen Arnoldi, Dougal Cameron
Sentences: [00:00 - 00:00] Karen Arnoldi: Sure.
[00:02 - 00:04] Karen Arnoldi: We are recording here.
...
Audio Url: No audio url
```

**详情层面 MCP 缺失的 7 个字段**：`meeting_attendance`、`meeting_info`、`workspace_users`、`shared_with`、`user`、`analytics`、`apps_preview`／`channels`。

> ⚠️ 其中 `meeting_attendance` 承载**进出场时间**（`join_time` / `leave_time`），是判断「谁中途离场、谁迟到」的唯一数据源（实测 43 场全部有值，但 `leave_time` 仅 55% 的记录有）。**MCP 通道完全不具备该能力，也无法由其他字段推断**——其逐句数据连 `speaker_id` 都没有。

**逐句结构对比（本方案最关键的差异）**

GraphQL 每句是一个对象，8 个字段：

```json
{"index": 1, "speaker_name": "Karen Arnoldi", "speaker_id": 0,
 "text": "We are recording here.", "raw_text": "We are recording here.",
 "start_time": 2.32, "end_time": 4.4,
 "ai_filters": {"text_cleanup": "We are recording here.", "task": null,
                "pricing": null, "metric": null, "question": null,
                "date_and_time": null, "sentiment": "neutral"}}
```

MCP 把同一句压平成一行文本：

```
[00:02 - 00:04] Karen Arnoldi: We are recording here.
```

| 逐句字段 | GraphQL | MCP |
|---|---|---|
| `speaker_name` | ✅ | ✅ |
| `text` | ✅ | ✅ |
| `index` | ✅ | ⚠️ 可由行序重建 |
| `start_time` / `end_time` | ✅ 浮点秒（`2.32`） | ⚠️ 仅到秒（实测平均误差 0.51s、最大 0.99s） |
| `speaker_id` | ✅ | ❌ |
| `raw_text` | ✅ | ❌ |
| `ai_filters`（7 子字段，含 `sentiment`） | ✅ | ❌ |

### B.3 内容一致性与可解析性（实测）

- **正文**：MCP 文本 504 行全部解析成功，与 GraphQL 的 504 句**逐句比对零差异**（说话人 + 文本完全一致）。
- **摘要**：8 个非空小节与 GraphQL **逐字节相同**（`notes` 8965 字符、`action_items` 1321 字符、`overview` 979 字符等）。
- **空值**：GraphQL 为 `null`／空数组；MCP 为自然语言占位符，且**每个字段措辞不同**（`No audio url`、`No transcript chapters`），解析时须维护映射表，漏了会把占位文案当真值入库。
- **付费字段行为不同**：同为 Free 账号，GraphQL 请求 `audio_url` 返回 `paid_required`（403），MCP 返回 `No audio url` 字符串——**MCP 是降级而非报错**，不能靠有无报错判断字段可用性。

**结论**：两条通道**内容同源、值一致**，差异在于 MCP 丢失了逐句细粒度与 7 个会议级字段，且以展示文本而非数据契约的形式交付。MCP 文本可稳定解析（实测 100%），但它是为阅读设计的格式，Fireflies 未承诺其稳定性，措辞调整会造成**静默的脏数据而非报错**。

