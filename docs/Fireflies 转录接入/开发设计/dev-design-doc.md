# Fireflies 会议转录接入 — 开发设计

> 关联文档: [会议内容提取规则](../调研/会议内容提取规则-需求文档.md) · [AI Meeting Type 自动映射标准](../调研/AI%20Meeting%20Type%20自动映射标准-需求文档.md) · [Cheat Sheet](../调研/Cheat%20Sheet-需求文档.md) · [Fireflies Configuration](../调研/Fireflies%20Configuration-需求文档.md) · [Fireflies Raw Data](../调研/Fireflies%20Raw%20Data-需求文档.md) · [Fireflies Summary Records](../调研/Fireflies%20Summary%20Records-需求文档.md) · [Goldie Base](../调研/Goldie%20Base需求文档.md) · [设计](../设计/design-doc.md) · [抽取提示词](../设计/extraction-prompts.md) · [代码示例（DDL）](./code-examples.md) · 设计稿：Lovable 项目 FFL（`5c905189-2a86-4020-abec-88a276b00861`，commit `76cc767`）
>
> **本文范围**：三端共用的契约——表、页面、接口、按钮、布局、需求追溯与开发任务拆分。按 `docs/CLAUDE.md`「不在一个文件中混写 Java + Python + 前端的实现细节」，各端的实现细节（类结构、关键算法、异常处理）开发前按需另拆 `dev-java.md` / `dev-python.md` / `dev-frontend.md`。
>
> **进度**：第 1 步（表）已确认（2026-10-27）；第 2、3 步（页面、接口）已写完并审核，确认② 的问题（Q14~Q24）已全部拍板（2026-10-27）；第 4、5 步（按钮、布局）在确认② 后续写。

## 0. 概述

**做什么**：把 Fireflies 录制的 Teams 会议拉进 LG，自动识别参会人与会议类型，用大模型提取摘要、知识库文档、跨公司内容与专家证词，经管理员审核后按可见范围投影进 Goldie 的知识库与记忆；管理端提供 Fireflies Management（Summary Records / Configuration / Cheat Sheet / Raw Data 四个 Tab），Ask Goldie 下新增 Goldie Base 页。

**谁用**：管理端 PGM / Super Admin（全部功能）、PM（Goldie Base 两个新 Tab 只读）、公司端创始人（Raw Data 看本人受邀会议的原文，以及 Goldie 召回）。

**涉及服务**（分工按设计第八章开头，第十章 #91）：

| 端 | 负责 |
|---|---|
| Java `CIOaas-api` | Configuration、Cheat Sheet（名册、专长标签、Email Domain）、Raw Data（含公司端）、每日拉取与 Sync now；配套：新会议 / 公司增改经 SQS 交 Python、PGM/SA 判定方法、给 Python 的名册写接口 |
| Python `CIOaas-python` | 识别（P1 / P8）、提取与清洗（P2~P7）、中间表与投影入库、Summary Records 与矩阵、专家确认、改判重算与自动路由、Goldie Base 两个新 Tab |
| Web `CIOaas-web` | Fireflies Management 页、会议详情 Review 页、原文页、名册历史页、Goldie Base 页 |

**关键假设**（确认点逐条过）：

| # | 假设 | 出处 / 理由 |
|---|---|---|
| A1 | 页面、字段、文案、交互以设计稿为准；数据与业务规则以设计文档为准；两者冲突的列进第 7 节 | 用户口径「页面以设计稿为准」 |
| A2 | Java 侧 Fireflies 表的时间列用 `timestamptz`（不用 ERL 的 `timestamp(6)`） | Python 要直读这些表，带时区的类型两端都按 UTC 解释，不靠约定；Java 侧 `timestamptz` 有 sprint107~110 先例；用户确认 2026-10-27（7 #Q3） |
| A3 | Python 侧物理表名用 `ai_ff_*` | 设计文档第八章 #15「Python 表的物理名加 `ai_` 前缀」；用户确认 2026-10-27（7 #Q2） |
| A4 | 审计只在 Python 侧建表（`ai_ff_audit_log`）；Java 侧的连接、邮箱域名、原文变化写应用日志 | 需求要求审计「路由决策与覆写操作」，都在 Python；Java 这几类不是路由决策（用户决定 2026-10-26） |
| A5 | 跨端读的数据权限（Python 直读 Java 表 / 经接口）不影响表结构，本步只列清单（1.4） | 用户口径「数据权限等表定了再看」 |
| A6 | 会话补 `organization_id`（设计第八章 #14）已由 Java `c7892f54d` 实现，含存量会话回填接口 | Java 仓库提交记录 |
| A7 | 迁移文件按 sprint122 暂定（Java `deploy/upgrade_doc/sprint122/V1`、Python `V034__sprint122_*`），以实际发版 sprint 为准 | 两端迁移约定 |

## 1. 数据库表

### 1.1 表清单

| # | 表名 | 用途 | 新增 / 改造 | 归属（写） | 读取方 | 字段数 |
|---|---|---|---|---|---|---|
| J1 | `ff_connection_configuration` | 租户的 Fireflies 连接、API key（密文）与本机构邮箱域名 | 新增 | Java | Java、Python（只读邮箱域名） | 13 |
| J2 | `ff_meeting_meta_info` | 会议元信息（原文侧） | 新增 | Java | Java、Python | 16 |
| J3 | `ff_meeting_sentence` | 逐句转录 | 新增 | Java | Java、Python | 8 |
| J4 | `ff_cheat_sheet` | 外部人员名册（一行一个版本） | 新增 | Java（Python 经接口写） | Java、Python | 18 |
| J5 | `ff_expertise_tag` | 专长标签字典 | 新增 | Java | Java、Python | 9 |
| P1 | `ai_ff_meeting_state` | 会议处理状态（类型、状态、提取输入…） | 新增 | Python | Python、Java（只读 `identification_result`） | 22 |
| P2 | `ai_ff_meeting_participant` | 识别结果：参会人 | 新增 | Python | Python | 21 |
| P3 | `ai_ff_meeting_speaker` | 识别结果：说话人绑定 | 新增 | Python | Python | 14 |
| P4 | `ai_ff_meeting_company` | 识别结果：公司关联与候选 | 新增 | Python | Python | 16 |
| P5 | `ai_ff_expert_candidate` | 专家候选（可能为专家的标签） | 新增 | Python | Python、Java（只读，标签删除校验） | 15 |
| P6 | `ai_ff_expert_rejection` | 专家候选拒绝名单 | 新增 | Python | Python | 9 |
| P7 | `ai_ff_routing_row` | 路由中间表（矩阵正本与投影记录） | 新增 | Python | Python | 25 |
| P8 | `ai_ff_audit_log` | 审计：路由决策与覆写 | 新增 | Python | — | 11 |
| X1 | `ai_file_registry` | 知识库登记行：新增业务类型 `FIREFLIES` / `FIREFLIES_SUMMARY`（只改列注释） | 改造 | Python | Python、Java（已有实体映射，只写财务抽取行，不碰 Fireflies 行） | +0 |

不建新表的：LLM 调用记录复用 `ai_llm_call_log` / `ai_trace`；RAG 条目复用 `ai_rag_entry`（新增空间走代码种子 `rag/domain/enums.py`，无建表 DDL，只更新 `ai_rag_business_association.business_type` 列注释）；菜单行走管理后台配置（ERL 先例，见 1.4）。

**通用约定**

| 项 | Java 表 | Python 表 |
|---|---|---|
| 主键 | `id varchar(36)`，`@UuidGenerator` | `id VARCHAR(36)`，ORM `default=_uuid`，SQL `DEFAULT gen_random_uuid()::varchar(36)`；审计表用 `BIGSERIAL` |
| 审计列 | 继承 `AbstractCustomEntity`：`created_by` / `created_at` / `updated_by` / `updated_at`（`created_by` 等为 varchar(36)） | `created_by` / `created_at` / `updated_by` / `updated_at`，`updated_at` 配 `trg_ai_<表>_updated_at` 触发器 |
| 系统操作人 | 系统写入（定时拉取、SQS 消费、自动识别与提取）一律记 `"1"`，即 `FinancialConstants.SYSTEM_USER_ID`（Benchmark Report 先例），页面显示为 `System`。拉取任务与消费者入口先 `SecurityUtils.setCurrentUserId("1")`、`finally` 里 `clearCurrentUserId()`：基类 `@PreUpdate` 无条件用线程里的用户覆盖 `updated_by`，不设的话定时任务里的更新会写成空（用户决定 2026-10-26） | 同样记 `"1"`（审计 `operator`、各表 `created_by` / `updated_by`）；由人引起的系统动作另记触发人（审计 `triggered_by`） |
| 时间 | `timestamptz`（A2）；Java 字段 `Instant`；有效期 `date` / `LocalDate` | `TIMESTAMPTZ` |
| 枚举 | `varchar(16~32)` + `@Enumerated(STRING)`，不加 CHECK，取值写进列注释 | `VARCHAR(16~32)` + `domain/enums.py` StrEnum，不加 CHECK，取值写进列注释 |
| 数组 / 对象 | `jsonb`（`@JdbcTypeCode(SqlTypes.JSON)`） | `JSONB`；非空数组 `DEFAULT '[]'`，可空列 `JSONB(none_as_null=True)` |
| 软删 | 5 张表都不设（只追加或物理删除） | `deleted BOOLEAN NOT NULL DEFAULT FALSE`，配 `WHERE deleted = FALSE` 部分索引 |
| 外键 | 不建，应用层软引用 | 不建，应用层软引用 |
| 命名 | `pk_ff_<表>` / `uk_ff_<表>_<列>` / `idx_ff_<表>_<列>` | `pk_ai_ff_<表>` / `uk_…` / `idx_…` |
| 邮箱 | 一律存小写，比较忽略大小写 | 同左 |

### 1.2 Java 表

#### J1 `ff_connection_configuration`

原名 `ff_connection`（用户决定 2026-10-26 改名：表里存的是 Configuration 页的配置，含 key、同步状态与邮箱域名）。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `organization_id` | varchar(36) | 否 | — | 租户，一个租户一条 | 9.2.1 |
| `api_key_cipher` | text | 是 | — | API key 密文（AES-GCM，密钥走环境变量）；未连接或已移除为空。设计稿的掩码（`••••a3f9`）由查询接口在服务端解密后拼好再返回，不另存后 4 位；原文与密文都不出接口 | 9.2.3、设计稿 1.2 |
| `account_email` | varchar(255) | 是 | — | key 持有者账号（Fireflies `user` 查询）：页面「connected as …」；重新 Link 时比对，换了账号按首次连接处理（9.2.6）；换账号写进 Java 应用日志。设计 9.2.3 的 `account_name` 不存——设计稿只显示邮箱，也没有逻辑用到 | 9.2.3、9.2.6 |
| `connection_status` | varchar(16) | 否 | `'UNCONNECTED'` | 连接状态：`UNCONNECTED`（未连接）/ `CONNECTED`（已连接）/ `FAILED`（key 鉴权失败）/ `DISCONNECTED`（连续 N 次非鉴权失败而断开） | 9.2.4 |
| `last_success_sync_at` | timestamptz | 是 | — | 最近一次成功完成的拉取；只记成功；换账号时清空 | 9.2.6 |
| `consecutive_failures` | int | 否 | `0` | 连续非鉴权失败次数，达阈值 N 转 `DISCONNECTED` | 9.2.4 |
| `sync_started_at` | timestamptz | 是 | — | 非空 = 正在同步：拉取开始时条件 UPDATE 抢占（为空或已超时才能抢到），结束清空；定时与手动互斥，页面「是否正在同步」读它 | 9.2.6 |
| `email_domains` | jsonb | 否 | `'[]'` | 本机构邮箱域名数组（Cheat Sheet 底部的 Email Domain 维护）：小写、去 `@`，不能是公共邮箱域名，租户内不重复（代码校验）；识别 ① 整份读取 | 9.7.7、1.9 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计（基类） | |

- 主键 `pk_ff_connection_configuration (id)`
- 设计 9.2.3 的 `last_attempt_at` / `last_error` 不存：设计稿不显示失败时间与原因，同步状态另有 `sync_started_at` / `consecutive_failures` / `connection_status`；拉取失败的时间与原因写应用日志，排障查日志
- 唯一 `uk_ff_connection_configuration_org (organization_id)`
- 状态流转：`UNCONNECTED → CONNECTED`（Link 成功）；`CONNECTED → FAILED`（鉴权错误）；`CONNECTED → DISCONNECTED`（连续 N 次非鉴权失败）；`FAILED / DISCONNECTED → CONNECTED`（Link 或 Sync 成功）；任意 → `UNCONNECTED`（设计稿的 Remove：清空密文，用户决定 2026-10-27，7 #Q1）
- `FAILED` 与 `UNCONNECTED`（含 Remove 之后）定时拉取跳过该租户（9.2.4）
- 一个租户一行，第一次 Link 或第一次保存邮箱域名时创建（还没 Link 就配域名的，先建一行，状态 `UNCONNECTED`）；Remove key 只清密文、状态回 `UNCONNECTED`，这一行、域名、`account_email` 与 `last_success_sync_at` 保留：重新 Link 同一账号接着增量拉，换账号按 9.2.6 首次连接处理；谁移除的写 Java 应用日志
- 设计 9.7.7 的 `ff_email_domain` 表并入本表 `email_domains` 列：域名就几个、总是整份读写；谁改了什么写 Java 应用日志；GS 租户的 3 个初始域名上线时由管理员在页面添加（用户决定 2026-10-27，7 #Q5）

#### J2 `ff_meeting_meta_info`

原名 `ff_meeting`（用户决定 2026-10-26 改名：只存会议元信息，逐句另在 J3）。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `organization_id` | varchar(36) | 否 | — | 连接所属租户，隔离依据 | 9.3.2 |
| `fireflies_id` | varchar(64) | 否 | — | Fireflies 原生 id，页面展示的会议 id | 9.3.2 |
| `title` | varchar(512) | 是 | — | 仅展示与检索，禁止用于类型识别 | 1.9 |
| `started_at` | timestamptz | 否 | — | 会议开始时间，取 Fireflies `dateString`，存 UTC | 9.3.2 |
| `duration_minutes` | numeric(8,2) | 是 | — | Fireflies `duration`（单位分钟） | 9.3.2 |
| `participants` | jsonb | 否 | `'[]'` | 受邀邮箱数组，入库转小写 | 1.9、9.3.6 |
| `attendance` | jsonb | 否 | `'[]'` | 出席记录：实际进入会议的人，每项 `{name, join_time, leave_time}`（入会显示名、加入与离开时间），Fireflies `meeting_attendance` 原样保存。只有姓名、没有邮箱，与受邀名单对不上（#92）：Raw Data 照原样显示，并作 P8 推断参会人身份的线索，不作参会人姓名 | 9.3.2、#92 |
| `speakers` | jsonb | 否 | `'[]'` | 发言人名单：转录里出现过的说话人，每项 `{id, name}`（Fireflies 说话人 id、会议显示名）。`id` 即逐句表的 `speaker_id`，只在本场唯一；识别时按姓名对邮箱前缀把说话人绑到参会人（P3），没发言的人不在这里 | 9.3.2 |
| `overview` | text | 是 | — | Fireflies `summary.overview`，GS → 创始人摘要的来源 | 1.3、2.3 |
| `content_hash` | varchar(64) | 是 | — | 逐句与元信息的摘要哈希；回看重拉时比对，已投递的会议内容变了写一条警告日志（设计 9.10.2 的 `TRANSCRIPT_CHANGED`，本方案，免得每次重读全部句子） | 9.3.1 |
| `dispatched_at` | timestamptz | 是 | — | 投递给 Python 识别成功的时间；非空 = 已进入识别，回看不再改原文（拿到 SQS 发送成功结果才写，见下方「投递与补投」） | 9.3.1、第八章 #30 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计（基类，系统写入记 `"1"`）。`created_at` 即首次入库时间：会议行只在首次拉到时插入，回看重拉与补拉句子都是更新同一行，所以它不变；Raw Data 的 `Ingested at` 列与原文页的 `captured` 读它（设计 9.3.2 的 `ingested_at` 不另存） | 9.3.3、9.3.5 |

- 主键 `pk_ff_meeting_meta_info (id)`
- 设计 9.3.2 的 `calendar_type`、`host_email`、`organizer_email`、`transcript_url`、`meeting_link` 不存：没有逻辑读它们，设计稿也不显示（`calendar_type` 只在调研时用来印证会议来自 Teams；主持人与组织者已在受邀名单 `participants` 里；原文页没有 Fireflies 链接）。`word_count` 也不存：设计稿的原文页不显示字数（设计 9.3.5 页头的 `9,420 words` 以设计稿为准不做）
- 唯一 `uk_ff_meeting_meta_info_org_ffid (organization_id, fireflies_id)`——幂等 upsert 的依据
- 索引
  - `idx_ff_meeting_meta_info_org_started (organization_id, started_at DESC)` —— Raw Data 列表默认按日期倒序、按日期范围筛选
  - `idx_ff_meeting_meta_info_participants_gin USING gin (participants jsonb_path_ops)` —— 公司端「本人受邀的会议」（`participants @> '["<email>"]'`）、按参会人筛选
  - `idx_ff_meeting_meta_info_undispatched (organization_id, created_at) WHERE dispatched_at IS NULL` —— 补投：入库了但没投递成功的会议，每次拉取开始时补投
- **Java 只拉数据，不判定 Invalid**（用户决定 2026-10-26，设计 9.3.2 的 `validity` 不建）：只入库 Fireflies 已处理完的会议（`meeting_info.summary_status = 'processed'`；取值与处理中的会是否出现在列表里，开发时实测），处理中的跳过、由下次拉取的 72 小时回看补上，超过回看窗口仍未处理完的不再拉。入库的会议不论有没有句子都投递给 Python；转录为空与无实质内容统一由 Python 判，记 `ai_ff_meeting_state.identification_result = NO_SUBSTANCE`，Raw Data 的 Invalid 徽标与筛选只读它。投递后原文不再改，所以不存在「投递后才拉到句子」的情况
- **投递与补投**（用户决定 2026-10-27，7 #Q6）
  - `SQSService` 新增一个返回成败的发送方法，复用私有的 `sendMessageToSqs`（成功返回消息 id、失败返回空）；现有 `sendMessage` 不返回结果、失败只打 ERROR 日志（`SQSServiceImpl.java:141`），其他业务在用，不改
  - 每场会：入库事务提交 → 发消息 → 拿到消息 id 才写 `dispatched_at`；失败不写、打 ERROR 日志，接着处理下一场。先提交再发：否则 Python 可能先收到消息、读不到会议。先发后写、不反过来：最坏只是重发一次（Python 跳过）；反过来进程在两步之间挂掉，会议被标成已投递而消息没发出，静默丢失
  - 每次拉取（每日定时、Sync now）开始时，先补投本租户 `dispatched_at` 为空的会议（上面的未投递索引），消息带本次拉取的触发方式与触发人。按「未投递」查、不按会议时间，不受 72 小时回看限制，也不设次数上限：消息只有租户、会议 id、触发方式与触发人，发不出去是 SQS 本身的问题（网络、权限、队列），修好后下一次拉取一次补齐
  - 未投递的会议被回看重拉到时照常整场重写（upsert 元信息、逐句先删后插）：Python 还没拿到
  - Python 收到同一场会的重复消息，按 P1 `meeting_id` 唯一跳过

| 情形（会议 A 周一开完） | 过程与结果 |
|---|---|
| 第一次就成功 | 周二 02:00 入库、发送成功、写 `dispatched_at`，Python 识别提取；之后回看再拉到只比 `content_hash`，不改原文、不重发 |
| 第一次失败，第二次成功 | 周二 02:00 发送失败，`dispatched_at` 为空：Raw Data 能看到 A，Summary Records 还没有；下一次拉取（管理员点 Sync now，或周三 02:00）先补投，成功后写 `dispatched_at`，Python 开始处理 |
| 连续失败 | 每次拉取都补投、每次一条 ERROR 日志，不放弃；SQS 修好后积压的会议在下一次拉取一次补齐，超过 72 小时的也补 |
| 发送成功，写 `dispatched_at` 失败（数据库瞬断、进程在两步之间被杀） | 下次拉取重发，Python 已有 A 的状态行、跳过，不会重复识别；期间回看若拉到改过的原文会覆盖，与「投递后才在 Fireflies 改转录」同性质，接受 |
| 投递成功，Python 处理失败（不归 Java） | Java 不再发。处理中被打断（进程被杀、代码异常）由 SQS 重投接手、从头重跑，最多 3 次，仍没跑完的停在处理中、交给定时清扫（P1「卡死兜底」）；大模型最终失败按设计 6.11 作废、会议进 Pending（待识别） |

#### J3 `ff_meeting_sentence`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `meeting_id` | varchar(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | 9.3.2 |
| `sentence_order` | int | 否 | — | 句子在转录中的先后顺序，取 Fireflies `index`。不叫 `order`：它是 PostgreSQL 保留字，做列名处处要加引号 | 9.3.2 |
| `speaker_id` | int | 是 | — | 与 `speakers[].id`、P5 / P7 的 `speaker_ref` 同值 | 6.3 |
| `speaker_name` | varchar(255) | 是 | — | 会议显示名，原样 | 9.3.5 |
| `text` | text | 否 | — | Fireflies `text`：默认转写结果，有人在 Fireflies 编辑器改过的取改后版本；原文页显示、大模型输入、时间戳回查、近逐字比对都用它 | 9.3.5、6.3 |
| `start_time` | numeric(10,3) | 是 | — | 浮点秒 | 9.3.5 |
| `end_time` | numeric(10,3) | 是 | — | 浮点秒 | 9.3.2 |

- 主键 `pk_ff_meeting_sentence (id)`
- 唯一 `uk_ff_meeting_sentence_meeting_order (meeting_id, sentence_order)` —— 原文页按 `sentence_order` 区间分批加载、提取时整场按序读取
- 设计 9.3.2 的 `raw_text` 不存：它是语音转写原句，只在有人于 Fireflies 编辑器改过时与 `text` 不同（实测样本 504 句逐句相同）；页面与逻辑都用 `text`，需要追溯时可按会议 id 向 Fireflies 重拉
- 不带审计列（批量子表，整场先删后插，9.3.1），实体不继承 `AbstractCustomEntity`（偏离 `standards/architecture.md`「所有 Entity 继承基类」：线上 `ddl-auto: update` 会按实体自动加审计列）；不按租户分区——量级约 73 万句 / 年（9.3.2），单表加唯一索引够用，过千万再评估分区

#### J4 `ff_cheat_sheet`

即设计文档的 `ff_cheat_sheet`（原名 `ff_registry_party`）。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键。表里没有版本号字段：一行即一个版本（同一人每改一次追加一行），所以「哪一版」就用这一行的 `id` 表示；参会人表的 `cheat_sheet_id` 记它 | 9.7.1 |
| `organization_id` | varchar(36) | 否 | — | 租户 | 9.7.1 |
| `name` | varchar(255) | 否 | — | 唯一识别符，同一人各版本同值；新建时应用层校验租户内不重名 | 9.7.1 |
| `emails` | jsonb | 否 | `'[]'` | 邮箱数组，小写 | 9.7.1 |
| `organization` | varchar(255) | 否 | — | 外部机构名 | 9.7.1 |
| `role` | varchar(32) | 否 | — | 角色：`LP` / `STRATEGIC_PARTNER`（战略合作方）/ `EXIT_PARTNER`（退出合作方）/ `FOUNDER`（不使用 LG 平台的创始人）/ `GS_STAFF`（GS 人员）/ `OTHER`（其他） | 5.2 |
| `expertise_tags` | jsonb | 否 | `'[]'` | 标签文本数组；非空即专家 | 1.11 |
| `area_of_expertise` | varchar(2048) | 是 | — | 专业领域，自由文本，仅作描述、不参与路由；前后端同按 2048 字校验（同 ERL 手填备注的长度） | 9.7.1 |
| `valid_from` | date | 否 | — | 有效期起始日（页面 Validity period 的 From），按会议日期回溯版本时用 | 9.7.2 |
| `valid_to` | date | 是 | — | 有效期截止日；空 = 至今（页面显示 `present`） | 9.7.2 |
| `source` | varchar(32) | 否 | `'MANUAL'` | 来源：`MANUAL`（Cheat Sheet 页手工新增）/ `FF_SUMMARY_RECORDS`（审核会议时登记，含专家确认） | 9.7.1 |
| `source_meeting_id` | varchar(36) | 是 | — | 从会议页登记或专家确认时的来源会议（`ff_meeting_meta_info.id`）；页面把它拼成 `System (<fireflies_id> import)` 展示——不塞进 `updated_by`（36 位放不下，且基类会覆盖） | 9.7.1 |
| `reviewed_by` | varchar(36) | 是 | — | 「看过无需修改」的复核人 | 9.7.5 |
| `reviewed_at` | timestamptz | 是 | — | 复核时间；用 `@Modifying` 单独 UPDATE，不经实体保存（基类 `@PreUpdate` 会改写 `updated_at`，破坏版本裁决） | 9.7.5 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计；`updated_at` = 写入时间，是重合裁决的依据（只追加，不改） | 9.7.2 |

- 主键 `pk_ff_cheat_sheet (id)`
- 索引
  - `idx_ff_cheat_sheet_org_name (organization_id, name)` —— 列表取各人当前版本、History、按会议日期回溯
  - `idx_ff_cheat_sheet_emails_gin USING gin (emails jsonb_path_ops)` —— 识别 ④ 按邮箱查名册、拒绝名单按人展开邮箱
- 只追加：每次 Confirm 追加新行，不改旧行；复核只改 `reviewed_*`

#### J5 `ff_expertise_tag`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `organization_id` | varchar(36) | 否 | — | 租户 | 9.8.2 |
| `name` | varchar(64) | 否 | — | 标签文本 | 9.8.2 |
| `preset` | boolean | 否 | `false` | 是否预置的 5 项（预置的不可删）；原名 `is_seed`，按业务含义改名（用户决定 2026-10-26） | 9.8.3 |
| `sort_no` | int | 否 | — | 展示顺序；种子 1~5，新增追加 | 9.8.1 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ff_expertise_tag (id)`
- 唯一 `uk_ff_expertise_tag_org_name (organization_id, lower(name))` —— 租户内不区分大小写重名
- 索引 `idx_ff_expertise_tag_org_sort (organization_id, sort_no)` —— 下拉按顺序列出
- 物理删除（只有从未被用过的标签能删，9.8.3）
- 预置 5 项（用户决定 2026-10-27，7 #Q4，同设计 9.8.1）：新建组织时写入——`OrganizationServiceImpl.save` 建完组织后已依次初始化 KPA、Tech Stack，其后加一行调用；存量组织由 Java V1 迁移一条 `INSERT … SELECT … FROM organization` 补齐（`sort_no` 1~5，`ON CONFLICT DO NOTHING`，可重跑）。不做懒加载：Python 直读本表（P7 专家推测归类、GS → 创始人证词主题），Java 没读过标签的租户，Python 会读到空字典

### 1.3 Python 表

#### P1 `ai_ff_meeting_state`

即设计文档 9.5.9 的 `ff_meeting_state`（原名 `ff_meeting_summary`：存的是会议的处理状态，不存摘要，故改名）。一场会一行，与 `ff_meeting_meta_info` 一对一；Python 收到投递时建行。为列表免跨表 JOIN（Python 仓储只做单表），冗余了几个原文侧字段——投递后原文不再改（9.3.1），冗余值不会过期。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | 9.5.9 |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | 1.1 |
| `fireflies_id` | VARCHAR(64) | 否 | — | 冗余：列表显示 `#<id>`、按 id 搜索 | 设计稿 1.1 |
| `title` | VARCHAR(512) | 是 | — | 冗余：列表、搜索、Goldie Base 卡片标题 | 设计稿 1.1 |
| `started_at` | TIMESTAMPTZ | 否 | — | 冗余：排序、时间筛选、会议日期（业务日期）、名册回溯 | 9.3.3 |
| `duration_minutes` | NUMERIC(8,2) | 是 | — | 冗余：列表 `52 min` | 设计稿 1.1 |
| `meeting_type` | VARCHAR(16) | 否 | `'UNKNOWN'` | 会议类型：`GS_FOUNDER`（GS → 创始人）/ `GS_LP`（GS → LP）/ `GS_INTERNAL`（GS 内部）/ `GS_PARTNER`（GS → Partner）/ `UNKNOWN`（判不出）；当前生效值 | 9.5.2 |
| `meeting_status` | VARCHAR(16) | 是 | — | 会议状态：`PASSED`（已放行）/ `PENDING`（待处理）；首轮未完成或 `Invalid` 为空（不进列表）。重新提取（Start Extraction、自动路由）进行中保持开始前的值，`pending_reasons` 同，提取结束再按设计 6.11 重判；列表照旧显示，详情页按 `extraction_status = RUNNING` 显示「提取中」 | 1.10 |
| `pending_reasons` | JSONB | 否 | `'[]'` | Pending 原因：`TO_IDENTIFY`（待识别）/ `TO_CONFIRM_EXPERT`（待确认专家）/ `TO_REVIEW`（待审核），可并存；列表筛选与红点计数用 | 9.4.2 |
| `portfolio_ids` | JSONB | 否 | `'[]'` | Portfolio 标记，`company_group` id | 9.5.4 |
| `processing_stage` | VARCHAR(16) | 否 | `'IDENTIFYING'` | 首轮自动加工进度：`IDENTIFYING`（识别中）/ `EXTRACTING`（提取中）/ `DONE`（完成）；`DONE` 且 `meeting_status` 非空才进列表，之后不回退。`Invalid` 与待识别的会议识别完即置 `DONE`、不经 `EXTRACTING`，`Invalid` 的 `meeting_status` 保持为空——停在 `IDENTIFYING` 会被当成卡死（下「卡死兜底」） | 1.10 |
| `processing_started_at` | TIMESTAMPTZ | 否 | — | 首轮本次处理的开始时间（建行时写入），兼作「谁在处理」的凭证。首轮每次开跑（新建本行或接手重跑）先删本场全部产出（P2~P5、P7），从识别第一步跑起，不从中断处接着跑：首轮还没进列表、也没投影过，删了不影响任何人；产出只有跑完才算数（用户决定 2026-10-27，7 #Q13）。收到消息时按本行分三种（用户决定 2026-10-27）：① 没有本行 → 建行处理；② `DONE` → 重复消息，删掉；③ 仍在 `IDENTIFYING` / `EXTRACTING`：重投（`ApproximateReceiveCount` ≥ 2）说明上一个处理者已不在——它活着时会一直延长消息的不可见时间，消息不会重新出现——直接接手从头重跑、不看时间；首次收到（= 1）却已有本行，是 Java 重复发送（J2「发送成功，写 `dispatched_at` 失败」），原消息仍在队列里，删掉本条。接手时把本列条件更新为本次开始时间（`WHERE processing_started_at = <读到的值>`，0 行即已被别的实例接手，删消息退出）；每个阶段落库的事务先锁本行、核对本列仍是自己写的值，核对不上即丢弃结果退出——延长调用连续失败、老进程其实还活着的少见情况。重跑次数不另存，看 `ApproximateReceiveCount`；收满队列上限（3）的那次仍没跑完（进程被杀或代码抛异常），消费者不做特殊处理：打 ERROR 日志、不删消息，消息进死信，本行停在处理中、不进列表，见下「卡死兜底」。大模型最终失败不在此列：那是跑完了、结果为失败，按设计 6.11 作废（设计 1.10、第八章 #30 的 `processing_attempts` / 心跳都不存） | 1.10、第八章 #30 |
| `extraction_status` | VARCHAR(16) | 是 | — | 最近一次提取任务的状态：`RUNNING`（进行中）/ `SUCCEEDED`（成功）/ `VOIDED`（作废） | 9.5.1 |
| `extraction_trigger` | VARCHAR(24) | 是 | — | 该任务的发起方：`AUTO`（首轮自动提取）/ `AUTO_ROUTE`（公司增改后自动路由）/ `START_EXTRACTION`（管理员点 Start Extraction，含改判前补跑 P1）——作废后都置待识别（Start Extraction 也是：旧内容在点击时已下线，用户决定 2026-10-26），审计按它区分触发方式 | 6.11 |
| `extraction_started_at` | TIMESTAMPTZ | 是 | — | 最近一次提取开始时间。非首轮的提取（Start Extraction、自动路由、改判前补跑 P1）被打断后没有重投接手（自动路由的消息重投时，这场会已有进行中的提取、不再匹配），靠定时清扫判超时：`extraction_status = RUNNING` 且本列距今超过卡死时限（配置，默认 1 小时），按该次提取作废（条件更新 `WHERE extraction_status = 'RUNNING' AND extraction_started_at = <扫到的值>`，作废规则同设计 6.11），Start Extraction 恢复可点（见下「卡死兜底」） | 6.11、第八章 #30 |
| `identification_result` | VARCHAR(32) | 是 | — | 识别阶段的结果，识别跑完后写：`NORMAL` / `NO_SUBSTANCE`（会议 Invalid，不进列表：转录为空——识别第一步程序检查，没有句子即判，不调 P1；或 P1 判无实质内容，如只有寒暄、没录上几句。Java 的 Raw Data 只读它显示 `Invalid`）/ `QUALITY_CHECK_FAILED`（P1 最终失败：待识别；自动路由跳过）/ `ATTENDEE_INFERENCE_FAILED`（P8 最终失败：待识别）。同时出现时按 `NO_SUBSTANCE` > `QUALITY_CHECK_FAILED` > `ATTENDEE_INFERENCE_FAILED` 只记一个，被盖掉的失败仍记在 `IDENTIFY` 审计。设计 9.5.9 的 `p1_status` / `p8_status` 合并为本列；P1 有没有做公司识别不再记，改判为 GS 内部 / Partner 时一律补跑 P1（本方案，调整设计 9.9.2 的「只做质量判断的才补跑」） | 6.4、6.11、6.13、9.3.4、9.4.2、9.9.2、9.9.3 |
| `current_extraction_input` | JSONB | 是 | — | 当前线上内容提取时用的输入：类型、保留的公司、每位参会人的身份 / 组织 / 公司 / 专长标签、说话人对到谁（示例见 code-examples 第 3 节）；**不存提取出的内容**（内容在中间表）。只用来判断「参会人有没有改过」：登记与指定说话人会立刻写进识别结果，拿最新识别结果和它比，有差异则 Start Extraction 激活（例外规则见设计 9.9.1）。提取成功时写入（首轮自动提取、自动路由、Start Extraction），改 Unknown 应用后清空。被推测者的专长标签刷新时（专家确认框 Save、`Edit external party` 改标签，P2），只把此人的专长标签同步写入、其余不动（本列为空时不写）：否则 P2 刷新后一比就成了参会人改动、激活 Start Extraction，与设计 9.9.1「被推测者的标签改动不算参会人改动」冲突；在刷新时同步而不是补抽成功后，补抽失败也不会激活。同时改了角色等其他字段的仍比得出差异、照常激活 | 9.5.1、9.9.1 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_meeting_state (id)`
- **防过期提交用 `updated_at`**（设计 9.6.5「并发」，本方案不另设 `lock_version`）：详情页加载时返回 `updated_at`，写操作带回它做条件更新 `WHERE id = ? AND updated_at = ?`，0 行即页面已过期、拒绝并提示刷新。凡会改变本场可提交内容的写入都要更新本行（触发器随之刷新 `updated_at`）：应用、Start Extraction、矩阵行内 Save、登记或指定说话人、专家确认，以及系统侧的自动路由、提取完成、补抽返回；只改子表的操作也要同时「碰」一下本行。代码里注明这是乐观锁
- 唯一 `uk_ai_ff_meeting_state_meeting (meeting_id)` —— 一对一；投递重复时幂等
- 索引
  - `idx_ai_ff_meeting_state_list (organization_id, started_at DESC) WHERE meeting_status IS NOT NULL` —— Summary Records 列表默认排序、时间筛选
  - `idx_ai_ff_meeting_state_status (organization_id, meeting_status, meeting_type)` —— 按状态、类型筛选；Tab 红点计数；自动路由找「待识别的 GS → 创始人」
- **卡死兜底**（用户决定 2026-10-27，7 #Q12、#Q13）：首轮被打断由 SQS 重投接手（`processing_started_at`）；其余四类交给定时清扫（单独功能，Fireflies 开发完成后设计、与本功能一起上线）：① 连续 3 次没跑完、停在处理中的首轮会议（按 `processing_started_at` 距今超过卡死时限判）；② 已投递却没有本行的会议（`dispatched_at` 距今超过同一时限；首次连接回溯 14 天、消息积压时可能误报，误报的重投 Python 按会议去重）；③ 非首轮的提取任务卡在 `RUNNING`（`extraction_started_at`）；④ 证词补抽卡在 `RUNNING`（P2 `testimony_backfill_status`）。③④ 在 Python 进程内执行，被打断后没有重投，只能靠超时解锁。Python 没有定时任务框架，清扫与 AI 财务提取任务卡在 `PROCESSING` 的同类问题一起设计，四类的查询见 code-examples 第 4 节。本功能不做「打开详情页、点按钮时判超时」（用户决定 2026-10-27：清扫一起上线，不必先写再下线）
- 不冗余采纳的公司（用户决定 2026-10-27）：列表的 Companies 列按本页会议 id 批量查 P4（`meeting_id IN (...) AND adopted = TRUE`，走 P4 唯一索引）；按公司搜索 / 筛选先得公司 id，再经 P4 的 `idx_ai_ff_meeting_company_org_company` 取会议 id
- 状态流转：`processing_stage` `IDENTIFYING → EXTRACTING → DONE`，`Invalid` 与待识别的 `IDENTIFYING → DONE`；`meeting_status` `null → PENDING / PASSED`（`Invalid` 保持 `null`），`PENDING ↔ PASSED`（应用、改 Unknown、重新提取结束后重判）；`extraction_status` `RUNNING → SUCCEEDED / VOIDED`
- **不设草稿，重新提取整场替换**（用户决定 2026-10-26，取消设计 9.6.4 的草稿）：点 Start Extraction 即保存页头（类型、公司、参会人写进识别结果），本场全部旧产物下线（中间表行、专家候选与知识库条目软删，未处理的候选置 `WITHDRAWN`），然后重新解析；成功后新内容按授权初值直接上线（初值规则见设计 9.9.5：沿用旧行的勾选，跨公司与经 P8 识别的证词一律不勾；有未处理的专家标记时整场先不投影，同首次提取），失败则会议转 `Pending`（待识别 · 提取失败），旧内容不恢复，可再点 Start Extraction 直到成功。解析期间 Goldie 召回不到这场会。改类型、公司、参会人都整场下线、整场重跑，不分受影响范围；行上的人工措辞、Play candidate 不保留（措辞可从 `CONTENT_EDIT` 审计找回），勾选与基金标签按（去向, 公司, 产出类型）沿用。`Discard Changes` 只撤销页面上未提交的改动，服务端没有可丢弃的东西；已 `Passed` 会议上补抽的证词也直接替换此人原有的证词行、默认勾选上线（设计 2.5），不再挂着等应用（设计 2.5 的待应用改动随之取消）

#### P2 `ai_ff_meeting_participant`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键；P8 的 `attendee_ref` | 6.13 |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `email` | VARCHAR(255) | 否 | — | 受邀者为受邀邮箱；名册说话人取名册会议日期那版的第一个邮箱；按 LG 账号登记的取账号邮箱；小写 | 9.5.9、#92 |
| `matched_name` | VARCHAR(255) | 是 | — | 已对上的发言人名（多个取句数最多的），没配上为空 | 1.8、#92 |
| `invited` | BOOLEAN | 否 | — | 是否在受邀名单里 | 1.9 |
| `role` | VARCHAR(32) | 否 | `'UNIDENTIFIED'` | 身份：`GS_STAFF`（GS 人员）/ `FOUNDER`（创始人）/ `LP` / `STRATEGIC_PARTNER`（战略合作方）/ `EXIT_PARTNER`（退出合作方）/ `OTHER`（其他）/ `UNIDENTIFIED`（未识别） | 1.9 |
| `match_step` | VARCHAR(24) | 是 | — | 命中识别链的哪一步：`GS_DOMAIN`（① GS 邮箱域名）/ `LG_USER_EMAIL`（② LG 用户完整邮箱）/ `LG_USER_DOMAIN`（③ 公司 Team 域名）/ `CHEAT_SHEET_EMAIL`（④ 名册邮箱）/ `P8`（⑥ 姓名候选经 P8 核对、⑦ P8 推断）/ `MANUAL`（人工登记、关联或指定）；未识别为空 | 1.9、9.5.9 |
| `lg_user_id` | VARCHAR(36) | 是 | — | ② 命中的 LG 用户 | 1.9 |
| `company_id` | VARCHAR(36) | 是 | — | 公司方参会人所属公司（② / ③ 得出）；名册或 P8 的 Founder 为空 | 2.1 |
| `cheat_sheet_name` | VARCHAR(255) | 是 | — | Cheat Sheet 引用键（姓名） | 9.7.1 |
| `cheat_sheet_id` | VARCHAR(36) | 是 | — | 识别时按会议日期取到的那一行 `ff_cheat_sheet.id`（一行即一个版本），留痕；P8 输出的 `registry_id` 即它 | 9.5.9 |
| `display_name` | VARCHAR(255) | 是 | — | 胶囊显示名 | 9.5.5 |
| `organization` | VARCHAR(255) | 是 | — | 胶囊显示的组织 | 9.5.5 |
| `expertise_tags` | JSONB | 否 | `'[]'` | 补充识别：会议日期生效版本的专长标签；登记、改登记、专家确认框 Save 后按名册当日生效版本刷新（徽标随之显示 `Expert`），被推测者的同时同步进 P1 `current_extraction_input` | 1.11 |
| `ai_inferred_identity` | JSONB | 是 | — | AI（P8）推断的此人身份：`{confidence, evidence, name, role, organization, registry_id}`（P8 原样输出，`registry_id` 即 `ff_cheat_sheet.id`），不采纳的也存 | 6.13 |
| `testimony_backfill_status` | VARCHAR(16) | 是 | — | 被推测者的证词补抽状态：`RUNNING`（补抽中）/ `FAILED`（补抽失败，可重试）；空 = 没有补抽或已成功。补抽在 Python 进程内执行，被打断后没有重投，靠定时清扫判超时：`RUNNING` 且本行 `updated_at` 距今超过卡死时限，置 `FAILED`（条件更新），页面出现 Retry。不另设开始时间列：置 `RUNNING` 时触发器刷新 `updated_at`，期间本行别的改动只会推迟判定（见 P1「卡死兜底」） | 2.5 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计；自动识别 `updated_by` 记 `"1"`（系统用户） | |

- 主键 `pk_ai_ff_meeting_participant (id)`
- 唯一 `uk_ai_ff_meeting_participant_meeting_email (meeting_id, email)` —— 登记时已是本场参会人的直接绑定、不另建
- 索引 `idx_ai_ff_meeting_participant_founder (organization_id, email) WHERE role = 'FOUNDER' AND company_id IS NULL` —— 自动路由：公司增改后按邮箱找「还没认出公司的 Founder」

#### P3 `ai_ff_meeting_speaker`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `speaker_id` | INT | 否 | — | Fireflies 说话人 id | 6.3 |
| `speaker_name` | VARCHAR(255) | 是 | — | 会议显示名 | 9.5.5 |
| `participant_id` | VARCHAR(36) | 是 | — | 绑定的参会人；空 = 未对上的说话人 | 1.9 |
| `bind_source` | VARCHAR(24) | 是 | — | 绑定方式：`NAME_PREFIX`（程序按姓名对邮箱前缀）/ `P8`（P8 `speaker_map` 给出 `high`）/ `MANUAL_ASSIGN`（管理员指定为某位参会人）/ `MANUAL_CHEAT_SHEET`（管理员登记进名册）；空 = 未绑定 | 1.9、#92 |
| `ai_speaker_match` | JSONB | 是 | — | AI（P8 `speaker_map`）判断这个说话人是哪位参会人或名册里的谁：对到谁、把握（`high` / `low`）、依据；`low` 也存 | 6.13 |
| `bound_by` | VARCHAR(36) | 是 | — | 人工绑定人 | 9.5.5 |
| `bound_at` | TIMESTAMPTZ | 是 | — | 人工绑定时间 | 9.5.5 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_meeting_speaker (id)`
- 唯一 `uk_ai_ff_meeting_speaker_meeting_spk (meeting_id, speaker_id)`

#### P4 `ai_ff_meeting_company`

带依据、候选等业务属性，按实体表命名（不用 `ai_r_` 关联表前缀）。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `company_id` | VARCHAR(36) | 否 | — | 本租户的公司 | 1.1 |
| `adopted` | BOOLEAN | 否 | — | 应用后是否采纳；未采纳的是候选或已移除 | 9.5.3 |
| `basis` | VARCHAR(16) | 是 | — | 关联依据：`EMAIL`（公司端用户完整邮箱）/ `EMAIL_DOMAIN`（公司 Team 域名）/ `TRANSCRIPT`（P1 正文提及）/ `MANUAL`（人工指定）；同一家多条依据只存命中的一条，完整邮箱优先 | 9.5.3 |
| `basis_participant_id` | VARCHAR(36) | 是 | — | 邮箱或域名依据命中的参会人 | 9.5.3 |
| `basis_value` | VARCHAR(255) | 是 | — | 命中的邮箱或域名 | 9.5.3 |
| `ai_transcript_mention` | JSONB | 是 | — | AI（P1）从会议正文里找到的这家公司提及：`{confidence, attendee_company, evidence}`（把握、是否到场者所在公司、依据）；P1 没提到这家时为空 | 6.4 |
| `auto_routed` | BOOLEAN | 否 | `false` | 是否由自动路由关联 | 9.9.3 |
| `assigned_by` | VARCHAR(36) | 是 | — | 人工指定人 | 9.5.3 |
| `assigned_at` | TIMESTAMPTZ | 是 | — | 人工指定时间 | 9.5.3 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_meeting_company (id)`
- 唯一 `uk_ai_ff_meeting_company_meeting_company (meeting_id, company_id)` —— 补跑 P1 按公司 upsert；Summary Records 列表按本页会议 id 批量取 Companies 列
- 索引 `idx_ai_ff_meeting_company_org_company (organization_id, company_id) WHERE adopted = TRUE` —— Summary Records 按公司搜索 / 筛选：按公司 id 找采纳了它的会议（P1 不冗余公司，用户决定 2026-10-27）

#### P5 `ai_ff_expert_candidate`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `participant_id` | VARCHAR(36) | 否 | — | 被推测者 | 6.11 步骤 5 |
| `tag` | VARCHAR(64) | 否 | — | 建议标签文本 | 1.11 |
| `claims` | JSONB | 否 | `'[]'` | 该标签下的实质性主张：每项 `{claim, basis, basis_type, timestamp}`（主张、依据、依据类型、出处时间点，时间点已回查原文）；确认框按标签分组展示 | 6.10 |
| `status` | VARCHAR(16) | 否 | `'PENDING'` | 处理状态：`PENDING`（未处理）/ `ACCEPTED`（同意）/ `DECLINED`（拒绝）/ `WITHDRAWN`（撤下：重新提取或改 Unknown 时仍未处理） | 9.5.10 |
| `auto_resolved` | BOOLEAN | 否 | `false` | 自动消解：该（邮箱，标签）已入册或已在拒绝名单（别场会议处理过，或在 Cheat Sheet 里直接加过；拒绝名单按人查），确认框里标出、`Save` 时一并落库（用户决定 2026-10-27，7 #Q22） | 9.5.6 |
| `decided_by` | VARCHAR(36) | 是 | — | 处理人：确认框 `Save` 的管理员（自动消解的同样记他） | 9.5.6 |
| `decided_at` | TIMESTAMPTZ | 是 | — | 处理时间 | 9.5.6 |
| `deleted` | BOOLEAN | 否 | `false` | 软删 | 9.5.10 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_expert_candidate (id)`
- 唯一 `uk_ai_ff_expert_candidate_live (meeting_id, participant_id, tag) WHERE deleted = FALSE`
- 索引 `idx_ai_ff_expert_candidate_pending_tag (organization_id, tag) WHERE status = 'PENDING' AND deleted = FALSE` —— Java 删标签前查「正被未处理标记引用」
- 状态流转：`PENDING → ACCEPTED / DECLINED`（确认框 Save，含自动消解的标签）；`PENDING → WITHDRAWN`（重新提取或改 Unknown 应用时仍未处理的，随旧产物软删）；会议状态只看未软删的 `PENDING` 行

#### P6 `ai_ff_expert_rejection`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户；拒绝名单按租户生效 | 9.5.6 |
| `email` | VARCHAR(255) | 否 | — | 被拒者在本场参会人行上的邮箱，小写 | 9.5.10 |
| `tag` | VARCHAR(64) | 否 | — | 被拒标签 | 9.5.6 |
| `meeting_id` | VARCHAR(36) | 否 | — | 来源会议 | 9.5.6 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_expert_rejection (id)`
- 唯一 `uk_ai_ff_expert_rejection_org_email_tag (organization_id, email, tag)` —— 推测前排除、自动消解；按人展开邮箱时用 `email IN (...)`

#### P7 `ai_ff_routing_row`

一行 = 一个 Authorize 格 = 投影后的一个知识库条目（设计 9.6.6）。摘要与知识库正文各占一行、各自授权与投影（用户决定 2026-10-27，7 #Q9）。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `meeting_started_at` | TIMESTAMPTZ | 否 | — | 冗余会议开始时间（同 P1 `started_at`）：Goldie Base 两个新 Tab 按会议时间倒序、按会议日期筛选（用户决定 2026-10-27，7 #Q23） | 9.11.4 |
| `meeting_title` | VARCHAR(512) | 是 | — | 冗余会议标题（同 P1 `title`）：两个新 Tab 的关键词同时匹配会议名称（7 #Q23） | 9.11.4 |
| `destination` | VARCHAR(24) | 否 | — | 去向：`KB_APP`（公司端知识库，GS → 创始人）/ `KB_ADMIN`（管理端公司层知识库，GS 内部与 Partner）/ `FUND_LEVEL`（设计的「机构层」：GS → LP 的基金层摘要 + 正文，`company_id` 为空）/ `CROSS_COMPANY`（跨公司内容）/ `TESTIMONY_ANON`（证词匿名版）/ `TESTIMONY_SIGNED`（证词署名版）；决定投影到哪个空间，组合键见 1.4 | 9.6.6 |
| `output_type` | VARCHAR(16) | 否 | — | 产出类型：`SUMMARY`（摘要，1a / 1b）/ `KB`（知识库正文：Founder KB / Portfolio KB）/ `CROSS_COMPANY`（跨公司内容）/ `TESTIMONY`（专家证词，两版各一行）。三类知识库去向下同一（去向, 公司）摘要一行、正文一行，矩阵里两行各一个 Authorize（同设计稿），各自投成一条条目（用户决定 2026-10-27，7 #Q9） | 9.6.2 |
| `company_id` | VARCHAR(36) | 是 | — | `KB_APP` / `KB_ADMIN` 必填 | 6.11 步骤 7 |
| `content` | TEXT | 否 | `''` | 内容：摘要行为摘要（≤150 个英文单词）；知识库行为 markdown 正文（原始转录链接在投影时附加，不存）；跨公司为 `statement`；证词为正文，不含来源行。设计 9.6.6 的 `summary` 列不建：摘要单独成行后同样存这里 | 1.3、9.6.3 |
| `category` | VARCHAR(64) | 是 | — | 仅跨公司与证词：P6 的四类之一 / P5 的证词类别；只用于投影时拼条目标题（`Cross-company insight · <category>`、`Expert testimony · <category>`，设计 6.11 步骤 8），页面不显示 | 6.8、6.9、6.11 |
| `source_timestamp` | VARCHAR(8) | 是 | — | 仅跨公司与证词：内容出自会议的时间点 `hh:mm:ss`（P6 / P5 输出，格式不合法或超出会议时长时置空）。只用于排序：Content Routing Matrix 里组内按「发言人 + 时间点」排，同一条证词的署名、匿名两版相邻，跨公司内容按会上先后；Goldie Base 两个新 Tab 的会议卡片内同样按它排。页面不显示，也不随内容投影 | 9.6.2 |
| `speaker_participant_id` | VARCHAR(36) | 是 | — | 仅证词：证词发言人对应的参会人（P2 `id`），写入时由 P5 输出的 `speaker_ref` 经说话人绑定解析而来 | 9.6.6 |
| `authorized` | BOOLEAN | 否 | `false` | 是否授权放行（矩阵的 Authorize 勾选）；取消勾选只改它、内容保留 | 9.6.4 |
| `in_playbook` | BOOLEAN | 否 | `false` | Play candidate：只把本条标记为 playbook 候选，不影响授权、投影与召回，候选由后续另一任务处理（用户确认 2026-10-27，7 #Q8）；证词只打在署名行，匿名行恒为 `false` | 9.11.6 |
| `fund_tag_ids` | JSONB | 是 | — | 基金标签：管理端 Knowledge Base Tab 手动选的 Portfolio（`company_group` id 数组），只用于 `KB` 行（Knowledge Base Tab 才有基金标签）；空 = 没选过，Portfolio 列按「公司所属 Portfolio → 会议 Portfolio 标记」回退 | 9.11.2 |
| `file_id` | VARCHAR(36) | 是 | — | 当前在线投影的 `files.id`，即 `ai_file_registry.file_id`（ORM 主键）；RAG 条目经登记行的 `ai_rag_entry_id` 取，不另存（设计 9.6.6 的 `rag_entry_id` / `file_registry_id` 不建）。改内容时新条目写成功才换；下线完成后置空（重新勾选时按「`file_id` 为空且已授权 → 上线」推） | 1.2、1.6 |
| `projection_status` | VARCHAR(16) | 否 | `'NONE'` | 投影状态：`NONE`（未投影或已下线）/ `PENDING`（投影中，含重试）/ `ONLINE`（已上线）/ `FAILED`（重试用尽仍失败） | 1.6 |
| `projection_attempts` | INT | 否 | `0` | 已重试次数 | 1.6 |
| `edited_by` | VARCHAR(36) | 是 | — | 最近一次行内 Save | 9.9.4 |
| `edited_at` | TIMESTAMPTZ | 是 | — | 最近一次行内 Save 的时间；为空即 AI 原文 | 9.9.4 |
| `deleted` | BOOLEAN | 否 | `false` | 软删 | 9.6.6 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_routing_row (id)`
- 冗余会议时间与标题（用户决定 2026-10-27，7 #Q23）：两个新 Tab 要按会议时间倒序、关键词同时匹配会议名称，Python 仓储只做单表、不许跨表 JOIN，分两步查又分不准页；投递后原文不再改（9.3.1），冗余值不会过期，理由同 P1 冗余 J2。写行时从 P1 带入。会议类型、`fireflies_id` 只用于展示，分页后按本页会议 id 批量查 P1，不冗余
- 不建唯一约束（用户决定 2026-10-27）：同一场会、同一（去向, 公司, 产出类型）未软删的只有一行，由写入逻辑保证——行只在提取成功时整场写入，写之前旧行已整场下线
- 索引
  - `idx_ai_ff_routing_row_meeting (meeting_id)` —— 矩阵加载、重新提取时整场下线、沿用旧行时找已软删的上一版（故不加 `WHERE deleted = FALSE`；一场会历次提取的行加起来也不多）
  - `idx_ai_ff_routing_row_tab (organization_id, destination, meeting_started_at DESC) WHERE deleted = FALSE AND authorized = TRUE AND file_id IS NOT NULL AND destination IN ('CROSS_COMPANY', 'TESTIMONY_SIGNED')` —— Goldie Base 两个新 Tab 按会议时间倒序分页（不用 `projection_status = 'ONLINE'`：改内容期间为 `PENDING`，旧条目仍在线）
  - `idx_ai_ff_routing_row_file (file_id)` —— 知识库 Source 列按登记行的 `file_id` 反查会议（不过滤软删）
  - `idx_ai_ff_routing_row_projection (projection_status) WHERE projection_status IN ('PENDING', 'FAILED')` —— 投影重试
- **摘要行与知识库行分开投影**（用户决定 2026-10-27，7 #Q9，取代设计 9.6.2「共用一个 Authorize 格」）
  - 摘要行：单独一条 RAG 条目——摘要写成一个小 markdown 文件，登记行 `business_type = FIREFLIES_SUMMARY`，`ai_rag_entry.summary` 直接写本行内容、不经大模型重写；进 Memory Tab 与 Goldie 召回，不进 Knowledge Base Tab
  - 知识库行：正文文件条目，登记 `FIREFLIES`；条目不带摘要（不写 `summary`、不生成摘要片），否则摘要没放行也会随正文条目被召回；进 Knowledge Base Tab 与召回，不进 Memory Tab
  - 不用「一条条目两个开关」：现有召回不区分摘要片与正文片（检索链路没有 `chunk_kind` 过滤），只放行一半就得删片重建，改动伸进召回
- Expert Testimony Tab 以署名行为准（设计 9.11.5、9.11.6 交开发设计定，用户决定 2026-10-26）：只列 `TESTIMONY_SIGNED` 已授权、已投影的行，天然一条证词一行；Play candidate 也打在署名行。两版可单独放行，只放行了匿名版的证词不进本 Tab
- 证词两版是两条独立的行（用户决定 2026-10-26，取代设计第十章 #80 ③ 的「改一版另一版同步」，设计 9.6.6 的 `testimony_group_id` 不建）：生成时正文相同、来源行由程序按版本附加，之后各自编辑、各自授权，不同步；矩阵按发言人、出处时间点排序，同一条的两版自然相邻
- 标签、可迁移理由不落库（用户决定 2026-10-26，设计 9.6.6 的 `tags` / `portable_reason` 不建）：设计稿的矩阵与两个新 Tab 都不显示它们；矩阵只能改正文，单独存会与改写后的正文脱节。P6 照旧输出（提示词与出参不变），程序只用于 `EXTRACT` 审计；跨公司 markdown 只放正文。`category` 保留（用户决定 2026-10-26）：投影发生在审核放行时、晚于提取，跨公司与证词匿名版的条目标题要用它拼；管理员改写正文后类别可能过时，只影响标题
- 证词发言人只存 `speaker_participant_id`（用户决定 2026-10-26，设计 9.6.6 的 `speaker_ref` / `speaker_name` / `speaker_organization` / `speaker_role` / `speaker_expertise_tags` 不建）：Expert Testimony Tab 的姓名与专长标签、投影时的来源行（署名版 `Source: <Organization> <Role> <Name>`、匿名版 `Expertise: …`）都按它关联 P2 的 `display_name` / `organization` / `role` / `expertise_tags`（会议日期生效版本）。参会人改动后、重新提取前，Tab 显示新值而已投影的来源行仍是旧值，重新提取成功后一致
- 基金标签只给会议解析产出的知识库条目打（用户决定 2026-10-26，收窄设计 9.11.2「人工上传的文件都能打」：只上传、不经会议解析的文件不打），故存在中间表、不进登记表。Knowledge Base Tab 列表对 `FIREFLIES` 行按 `file_id` 关联本表取 `fund_tag_ids`（与 Source 列反查会议同一次关联），改标签按 `file_id` 找到本行更新；改正文换 `file_id` 时行不变、标签随行；重新提取时新行按（去向, 公司, 产出类型）沿用整场下线前旧行的标签，同授权初值的沿用方式（设计 9.9.5、9.11.2「沿用同一会议、同一去向、同一公司的旧行标签」）
- **重新提取沿用旧行**（勾选、基金标签）按（去向, 公司, 产出类型）找上一版：同一场会、同一（去向, 公司, 产出类型）的已软删行里 `created_at` 最新的一条。行只在提取成功时新建，改内容不新建行，所以版本越新 `created_at` 越大；提取失败后再重试，找到的仍是点击前那一版。某家公司中间一版被移除、后来又加回时，沿用移除前那一版的勾选——管理员当时放行过这家公司在这场会上的内容（用户决定 2026-10-27）
- 不存软删时间（用户决定 2026-10-27，设计 9.6.6 的 `deleted_at` 不建）：页面不显示、没有定时物理清理（对比 `ai_rag_space` 留 `deleted_at` 是为 30 天后物理删），找上一版用 `created_at`；何时下线看 `EXTRACT` 审计
- 状态流转：`projection_status` `NONE → PENDING → ONLINE`（上线）；`ONLINE → PENDING → ONLINE`（改内容）；`ONLINE → PENDING → NONE`（下线，完成后 `file_id` 置空）；`PENDING → FAILED`（重试用尽，记 `PROJECTION_FAILED`，最后一次错误只记在审计里，行上不存；重试中途的错误看应用日志）
- 投影动作不落库（设计 9.6.6 的 `projection_action` 不建），处理 `PENDING` / `FAILED` 行时按行的当前状态推；`PROJECTION_FAILED` 审计里的动作也按此算：
  - `file_id` 非空，且 `deleted = TRUE` 或 `authorized = FALSE` → 下线
  - `file_id` 为空，未软删且已授权 → 上线
  - `file_id` 非空，未软删且已授权 → 改内容（先写新条目、成功后换 id 再软删旧条目，期间 `file_id` 仍指旧条目）
  - 都不是（未上线也不该上线）→ 直接置 `NONE`
  - 按最新状态推：重试排队期间管理员改了勾选，不会照旧动作推错方向

#### P8 `ai_ff_audit_log`

Fireflies 只在 Python 侧记审计：需求要求记的是「路由决策与覆写操作」（《会议内容提取规则》III），都发生在 Python。Java 侧的换 key、移除 key、改邮箱域名、已处理会议的原文变化不是路由决策，写 Java 应用日志（带租户、操作人、改前改后，不记 key），不建表。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | BIGSERIAL | 否 | — | 主键（只追加的日志表，同 `ai_rag_operation_log` 先例） | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | 9.10.1 |
| `event_type` | VARCHAR(32) | 否 | — | 事件类型：`IDENTIFY`（识别决策）/ `EXTRACT`（提取结果，含作废与补抽）/ `TYPE_CHANGE`（改类型）/ `COMPANY_CHANGE`（改公司）/ `CONTENT_EDIT`（矩阵改内容）/ `AUTHORIZE_CHANGE`（改授权）/ `PROJECTION_FAILED`（投影重试用尽仍失败） | 9.10.2 |
| `meeting_id` | VARCHAR(36) | 是 | — | 关联会议 | 9.10.1 |
| `target_type` | VARCHAR(16) | 是 | — | 受影响对象的类型：`COMPANY`（`COMPANY_CHANGE` 增删的公司）/ `ROUTING_ROW`（`CONTENT_EDIT`、`AUTHORIZE_CHANGE`、`PROJECTION_FAILED` 动到的中间表行）/ `PARTICIPANT`（`EXTRACT` 中证词补抽的那个人）；整场会议级的事件（`IDENTIFY`、`TYPE_CHANGE`、其余 `EXTRACT`）为空——会议已在 `meeting_id` | 9.10.1 |
| `target_id` | VARCHAR(36) | 是 | — | 受影响对象的 id，与 `target_type` 同空同非空。中间表行的去向与公司按 id 查（软删的行仍在）；`CONTENT_EDIT` 改的是摘要还是正文看该行的 `output_type`（摘要与正文分行，7 #Q9） | 9.10.1 |
| `before_value` | JSONB | 是 | — | 变更前 | 9.10.1 |
| `after_value` | JSONB | 是 | — | 变更后 | 9.10.1 |
| `operator` | VARCHAR(36) | 否 | — | 操作人 user id；自动决策记 `"1"`（系统用户，同 Java `FinancialConstants.SYSTEM_USER_ID`），页面显示为 `System` | 9.10.1 |
| `triggered_by` | VARCHAR(36) | 是 | — | `operator` 为系统、但由人的操作引起时记触发人（Sync now、Start Extraction、专家确认引起的补抽、建公司引起的自动路由）；每日定时触发的与 `PROJECTION_FAILED` 留空（用户决定 2026-10-26） | 9.10.1 |
| `created_at` | TIMESTAMPTZ | 否 | `now()` | 事件时间 | 9.10.1 |

- 主键 `pk_ai_ff_audit_log (id)`；只追加，无 `updated_*`、无软删
- 事件只记 7 种（用户决定 2026-10-26）：需求「所有路由决策与覆写操作都会写入审计日志」对应的 6 种（AI 的识别与提取决策，人工改类型、公司、内容、授权），加投影重试用尽的 `PROJECTION_FAILED`。设计 9.10.2 的其余事件不记，信息在业务表里：
  - `EXPERT_CONFIRM` / `EXPERT_DECLINE` → P5 的 `status` / `decided_by` / `decided_at` / `auto_resolved` / `claims`，P6 拒绝名单，Cheat Sheet 来源 `From FF Summary Records`
  - `REGISTRY_IMPORT` → `ff_cheat_sheet` 的 `source` / `source_meeting_id` / `created_by`
  - `SPEAKER_ASSIGN` → P3 `bind_source = MANUAL_ASSIGN` + `updated_by` / `updated_at`（只针对未配上的说话人，改前值恒为「未配上」）
  - `PORTFOLIO_MARK`（需求「仅为标记」）、`PLAYBOOK_TOGGLE`（候选标记）→ 只留当前值与 `updated_by`，不留历史；`DRAFT_DISCARD` 随草稿取消不再存在
- 重新提取是谁发起的，查这场会最近一次 Start Extraction 的 `EXTRACT` 记录（`triggered_by`、`created_at`），状态表不存发起人与时间
- 索引 `idx_ai_ff_audit_log_org_created (organization_id, created_at DESC)`、`idx_ai_ff_audit_log_meeting (meeting_id)` —— 按租户、按会议追溯（MVP 无查看页，9.10.3）

#### X1 `ai_file_registry`（改造）

| 变更 | 内容 | 存量数据 |
|---|---|---|
| `business_type` 新取值 `FIREFLIES`（知识库正文、跨公司、证词条目）/ `FIREFLIES_SUMMARY`（摘要条目，7 #Q9） | 列无 CHECK，只更新列注释 | 无 |

- 不加列：登记表只管文件登记，基金标签放 P7 的 `fund_tag_ids`（用户决定 2026-10-26）
- 两个页面各取一种：Memory Tab 的查询纳入 `FIREFLIES_SUMMARY`，Knowledge Base Tab 的查询纳入 `FIREFLIES`（设计第八章 #11）
- 与中间表的关联：登记行的 `file_id` = P7 的 `file_id`，本表不加反向列；Fireflies 登记行必须写 `ai_rag_entry_id`（一个文件一个条目），中间表靠它找到 RAG 条目

### 1.4 跨端读写、种子数据与配置

**跨端读的表**（数据权限待定，A5；表结构不依赖读法）：

| 方向 | 表 | 用途 |
|---|---|---|
| Python 读 Java 的 Fireflies 表（5 张） | `ff_meeting_meta_info`、`ff_meeting_sentence`、`ff_cheat_sheet`、`ff_expertise_tag`、`ff_connection_configuration`（只读 `organization_id`、`email_domains` 两列，不含 key 密文） | 识别与提取输入；名册回溯；P7 标签字典；识别 ① |
| Python 读 LG 业务表（7 张） | `user`、`r_organization_user`、`company`、`r_organization_company`、`company_group`、`r_company_group`、`organization` | 识别 ②③、自动路由、`firm_profile`、Portfolio 显示 |
| Java 读 Python 的表（2 张） | `ai_ff_meeting_state.identification_result`、`ai_ff_expert_candidate` | Raw Data 的 Invalid；标签删除校验 |

**跨端写**：无。Python 写名册调 Java 接口（第八章 #31），标签字典由前端直接调 Java（7 #Q19）；审计只有 Python 一张表（A4）。

**种子数据**

| 数据 | 方式 |
|---|---|
| 专长标签 5 项 | 新建组织时写入（`OrganizationServiceImpl.save`），存量组织由 Java V1 迁移补齐（J5，7 #Q4） |
| GS 租户 3 个邮箱域名 | 上线时管理员在 Cheat Sheet 页添加（用户决定 2026-10-27，7 #Q5） |
| Fireflies Management 菜单 | 管理后台 Menu & Function Management 加一条顶层菜单（path `/fireflies`），在 Roles Management 只挂给 PGM / SA 的角色；菜单 `pid = '0'`；配置后删 Redis `menu::menu:user:*`，再等进程内一级缓存过期（Caffeine 10 分钟）或重启各实例，用户清浏览器 `localStorage.roles` 与同名 cookie 后重新登录（ERL 先例；用户决定 2026-10-27，7 #Q7） |
| RAG 新空间业务类型 `EXPERT_TESTIMONY` / `CROSS_COMPANY` | Python 代码种子 `rag/domain/enums.py`，无建表 DDL，V034 更新 `ai_rag_business_association.business_type` 列注释；机构层复用已有种子 `ADMIN_ORGANIZATION`，不新增 |

**投影空间**（`ai_rag_business_association` 组合键 `(end_type, business_type, 作用域 id)`，设计 1.1）：

| P7 `destination` | 组合键 | 备注 |
|---|---|---|
| `KB_APP` | `(APP, APP_COMPANY, company_id)` | 已有 |
| `KB_ADMIN` | `(ADMIN, ADMIN_COMPANY, organization_id)` | 已有，行级按 `company_id` 过滤 |
| `FUND_LEVEL` | `(ADMIN, ADMIN_ORGANIZATION, organization_id)` | 复用已有种子（代码里无其他使用方；用户决定 2026-10-26） |
| `TESTIMONY_ANON` / `TESTIMONY_SIGNED` | `(APP / ADMIN, EXPERT_TESTIMONY, organization_id)` | 新业务类型 |
| `CROSS_COMPANY` | `(APP, CROSS_COMPANY, organization_id)` | 新业务类型；两端都召回，管理端在召回分支里另解此空间（设计第八章改造 #8） |

三类知识库去向的摘要行与正文行投到同一空间、是两条条目，登记行业务类型分别为 `FIREFLIES_SUMMARY` / `FIREFLIES`（P7、X1）。

**新配置项**

| 端 | 配置 | 默认 |
|---|---|---|
| Java | `FIREFLIES_KEY_SECRET`（API key 加密密钥，环境变量） | 无，必配 |
| Java | 首次回溯天数、回看小时数、`Disconnected` 阈值 N、每日拉取 cron、拉取读超时、同步卡死时限（`sync_started_at` 超过即可被重新抢占，API-01 的 `syncing` 也按它判） | 14 天、72 小时、待定（设计 9.12 #1）、待定、按实测定、1 小时 |
| Python | Fireflies 消费者并发、SQS 心跳续期间隔（沿用 consumer 模板）、卡死时限（默认 1 小时）；各提示词重试次数 | 记 `sql/migrations/env-vars/env-update.txt` |

### 1.5 迁移文件与执行顺序

| 端 | 文件 | 内容 | 执行时机 |
|---|---|---|---|
| Java | `deploy/upgrade_doc/sprint122/V1__ff_init.sql` | J1~J5 建表、索引、注释；存量组织补齐 5 项预置专长标签 | **先于 Java 发版**（ddl-auto 会自动建表但不建索引） |
| Python | `sql/migrations/business/V034__sprint122_fireflies_init.sql` | P1~P8 建表、索引、触发器、注释；X1 只改 `business_type` 注释，`ai_rag_business_association.business_type` 注释补两个新空间业务类型 | **先于 Python 发版** |

两份互不依赖，可任意先后；数据库授权（如 Python 账号读 Java 表）随数据权限决定后另补。DDL 见 [code-examples.md](./code-examples.md)。

## 2. 页面清单

页面编号用 `PG-`，避免与 Python 表 P1~P8 混淆。路由放在 web 的 `config/routes.ts`；两个 Tab 容器的当前 Tab 记在 `?tab=`（本功能新定：web 现有页面多用 `?active=`，但它会改写公司端顶栏高亮，`BasicLayout.tsx:130,469-499`，PG-05 在 `/askGoldie` 下会因此丢掉 Ask Goldie 的高亮）。设计稿的路由（`/`、`/meetings/$id` 等）只作对照。角色：**PGM / SA** = 管理端，且 superAdmin 或角色菜单含 `seeAllPortfolio`；**PM** = 管理端其余用户；**公司端** = Company Admin / Company User。前端不自己判角色，用后端返回的标志位（API-19 及各接口的按行标志，设计 9.1）。

| 编号 | 页面 | 路由 | 入口 | 可访问角色 | 类型 | 新增 / 改造 | 需求条目 |
|---|---|---|---|---|---|---|---|
| PG-01 | Fireflies Management（Tab 容器） | `/fireflies?tab=summaryRecords\|configuration\|cheatSheet\|rawData&org=<组织 id>`（`org` 只在切换过租户时出现） | 两端都在头像下拉的 Fireflies Management（管理端按设计稿 `app-header.tsx:80-94`；公司端不受订阅状态限制，7 #Q14、#Q15）；PG-02 / PG-03 / PG-04 面包屑回到对应 Tab | PGM / SA（四个 Tab）；公司端（只显示 Raw Data Tab）；PM 进入显示无权限 | 容器 | 新增 | 9.1、9.3.6、第八章 #28、#32 |
| PG-01a | └ Summary Records Tab（默认） | `?tab=summaryRecords` | Tab 切换 | PGM / SA | 列表 | 新增 | 9.4 |
| PG-01b | └ Configuration Tab | `?tab=configuration` | Tab 切换 | PGM / SA | 表单 | 新增 | 9.2 |
| PG-01b1 | 　└ Remove API key 确认框 | — | Configuration 的 Remove | PGM / SA | 弹窗 | 新增 | 9.2.5 |
| PG-01c | └ Cheat Sheet Tab（名册列表 + 底部 Email Domain 块） | `?tab=cheatSheet` | Tab 切换 | PGM / SA | 列表 + 行内编辑 | 新增 | 9.7、9.7.7 |
| PG-01c1 | 　└ Add / Edit external party 弹窗（新增时另有 Confirm submission 二次确认） | — | Add external party / 行内 Edit | PGM / SA | 弹窗（表单） | 新增 | 9.7.4、9.7.5 |
| PG-01c2 | 　└ 专长标签下拉（选、`Add "<输入值>"`、删未用过的） | — | PG-01c1、PG-02a、PG-02b、PG-02c 的 Expertise tags 字段 | PGM / SA | 组件 | 新增 | 9.8 |
| PG-01d | └ Raw Data Tab | `?tab=rawData` | Tab 切换；公司端进入 PG-01 即此 Tab | PGM / SA；公司端（只列本人受邀的会议） | 列表 | 新增 | 9.3.3、9.3.4、9.3.6 |
| PG-02 | 会议 Review 详情（含 Content Routing Matrix） | `/fireflies/meetings/:meetingId` | PG-01a 的会议名 / Review；PG-05c、PG-05d 的会议名（仅 PGM / SA 可点） | PGM / SA（按会议所属租户） | 详情 + 表单 | 新增 | 9.5、9.6、9.9 |
| PG-02a | └ Assign new external party 弹窗（含 Confirm submission） | — | 点未识别、AI 推断未入册、按域名判出未入册的参会人；未对上说话人的「登记进名册」 | PGM / SA | 弹窗（表单） | 新增 | 9.5.5、9.5.7 |
| PG-02b | └ Edit external party 弹窗 | — | 点名册中已有的外部人 | PGM / SA | 弹窗（表单） | 新增 | 9.5.5、9.5.7 |
| PG-02c | └ Possible expert 确认框 | — | 点带 `Possible expert` 的参会人 | PGM / SA | 弹窗（审批 + 表单） | 新增 | 9.5.6 |
| PG-02d | └ 指定说话人（未对上的说话人 → 本场某位参会人） | — | 点未对上的说话人 | PGM / SA | 弹窗（设计稿未画） | 新增 | 9.5.5 |
| PG-03 | 原文页 | `/fireflies/transcripts/:meetingId` | PG-01d 的 Raw transcript；PG-05a 中 Source = Fireflies 且可点的行 | PGM / SA；公司端（本人受邀的会议） | 详情（只读，滚动续加载） | 新增 | 9.3.5、9.3.6 |
| PG-04 | 名册 Role History | `/fireflies/cheat-sheet/:id/history`（`:id` 为此人任一版本行的 id） | PG-01c 的 History | PGM / SA | 列表（只读） | 新增 | 9.7.6 |
| PG-05 | Goldie Base（Tab 容器） | `/askGoldie/goldieBase?tab=knowledgeBase\|memorySettings\|crossCompany\|expertTestimony`（用户决定 2026-10-27，7 #Q16） | Ask Goldie 侧栏 / 手机端底栏的 Goldie Base 入口；旧地址 `/knowledgeBase`、`/memorySettings` 重定向到对应 Tab | 两端，按 Tab 区分 | 容器 | 新增（由两页合并） | 9.11.1、第八章 #17 |
| PG-05a | └ Knowledge Base Tab | `?tab=knowledgeBase`（默认） | Tab 切换 | 两端（原业务不变） | 列表 | 改造（原 `KnowledgeBasePage`） | 9.11.2、第八章 #11、#12、#18 |
| PG-05a1 | 　└ 基金标签选择（行内下拉） | — | 管理端 Fireflies 知识库正文行的 Portfolio 列 | 管理端 PM / PGM / SA（看得到该行即可改） | 行内下拉 | 新增 | 9.11.2、第八章 #16 |
| PG-05b | └ Memory Settings Tab | `?tab=memorySettings` | Tab 切换 | 管理端；公司端 Company Admin | 列表 | 改造（原 `MemorySettingsPage`） | 9.11.3、第八章 #13、#19 |
| PG-05c | └ Cross company content Tab | `?tab=crossCompany` | Tab 切换 | 管理端 PM / PGM / SA | 卡片列表 | 新增 | 9.11.4、9.11.6 |
| PG-05d | └ Expert Testimony Tab | `?tab=expertTestimony` | Tab 切换 | 管理端 PM / PGM / SA | 卡片列表 | 新增 | 9.11.5、9.11.6 |

**入口与守卫**

- 管理端：头像下拉加一项（`BasicLayout.tsx` 的 `menuRight_SuperAdmin`，key 取 `fireflies` 时 `handleGSTMenuClick` 的默认分支即跳 `/fireflies`；ERL 先例；用户决定 2026-10-27，7 #Q14），`path` 与后台菜单 `/fireflies` 一致（1.4「种子数据」）
- 公司端：同样放头像下拉（用户决定 2026-10-27，7 #Q15），放在订阅条件之外（`BasicLayout.tsx:891` 的条件只管 Profile 与菜单项；Switch Companies 另有 `userCount > 1`，Logout 不受限）——看本人受邀会议的原文是权限规则、不是付费功能。所有公司端用户都显示，没有受邀会议的看到空列表；要带 `?tab=rawData`，所以在 `handleGSTMenuClick` 加显式分支；手机端是同一个下拉组件。进 PG-01 只渲染 Raw Data Tab，不显示租户下拉
- `SecurityLayout`：`/fireflies` 与 `/fireflies/transcripts/*` 两端都要进，**不加管理端守卫**；`/fireflies/meetings/*`、`/fireflies/cheat-sheet/*` 加管理端守卫（仿 ERL `SecurityLayout.tsx:73-98`，取不到端类型按公司端拦截）。PM 直接打开 `/fireflies` 时按 API-19 的标志位显示无权限提示，不请求管理端接口；PM 的拦截与数据权限一律靠后端
- 切换租户：PG-01 页头组织树下拉，组织树根下有子组织才显示（同 ERL、Portfolio Companies），默认会话租户；SA 借此切到子租户查看（用户决定 2026-10-27，7 #Q17）。下沉 ERL 的 `OrganizationSelect` 到 `src/components/` 时，显示判定所在的 hook（`useErlOrganizationTree.ts:54`）、DTO 类型与 `subdata` → `children` 的归一函数一起搬。选中的租户记在 URL 的 `org` 上，PG-02 / PG-03 / PG-04 的面包屑把它带回；这三页不显示下拉，按会议（或名册行）所属租户执行，返回时 `org` 取该会议的租户（API-21、API-17 都返回 `organizationId`）
- Goldie Base：侧栏与手机端底栏现有的 Knowledge Base、Memory 两个入口按设计稿合并为一个 Goldie Base 入口（设计稿 `ask-goldie.tsx:80-89`；设计 9.11 交开发设计定）；Super Admin 默认取组织树第一个叶子租户（`orgScope.ts` 的 `firstLeafOrgId`），不提供切换（设计 9.11.1）；公司端普通用户只有 Knowledge Base 一个 Tab 时不显示 Tab 栏（设计 9.11.1 交开发设计定）

**不在本期**：Ask Goldie 对话里展示 Fireflies 来源链接——需求与设计稿都没有，现有聊天也没有结构化来源（只靠正文 Markdown）。Goldie 召回改造（第八章 #7~#10）不改页面（用户决定 2026-10-27，7 #Q21）。

## 3. 接口清单

**通用约定**

| 项 | Java（`/api/web/fireflies/*`） | Python（`/api/ai/fireflies/*`） |
|---|---|---|
| 位置 | `web/fireflies/` 按规范分 DDD 四层，路径 kebab-case 复数，不照 ERL 的平铺包与驼峰单数（用户决定 2026-10-27，7 #Q18）；每租户只有一个连接，按单例资源用单数 `/connection`；网关 `StripPrefix=1`，Controller `@RequestMapping("/fireflies")` | 新模块 `source/fireflies/`（`interfaces/routes/` 按页面拆文件），包根懒导出 router，`main.py` include |
| 响应 | `Result<T>` = `{success, code, message, data}`；业务错误 HTTP 200 + `success:false`；参数校验失败 HTTP 422，响应体为 `ErrorResponse{message, errors}`，不是 `Result` | 同结构；业务错误 HTTP 200 + `success:false` + 数字码（同 memory，前端遇 ≥400 会弹全局横幅）；例外：改造的 file-registry 接口（API-33~36）沿用该模块现有的真实 HTTP 状态码（`_raise_business`） |
| 分页 | `page`（从 0 起）/ `size` / `sort`，返回 `PageResponse{totalElements, content}` | `page`（从 1 起）/ `pageSize`，返回 `{items, total}`；日期区间 `dateFrom` / `dateTo`，按会议业务日期、含两端（设计 9.3.3） |
| PGM / SA 判定 | `CompanyGroupService` 新增一个方法：管理端 &&（任一角色 superAdmin \|\| 菜单码 `seeAllPortfolio`），Fireflies 接口首行断言，同时供 API-19 用 | 经 API-19 的新字段判定（`lgpi_api/current_user_api.py` 跟着加字段）；`auth_token` 缺失时在调 Java 之前就拒绝 |
| 租户 | 列表类接口可选 `organizationId`：为空取会话租户；传了就按传入的组织执行，**先不校验调用者是否属于该组织**，信任前端传入（用户决定 2026-10-27，7 #Q17）；PGM / SA 角色照常校验。按 id 定位的接口（API-07、09、14、17、18）不收组织 id，按该行（名册行、标签行、会议）自身的租户执行，同样不校验；API-08 由 `sourceMeetingId` 推出租户。公司端一律会话租户 | Summary Records 列表与 API-32 同左；会议级接口（`/meetings/{meetingId}/*`、`/routing-rows/{rowId}/content`）不收组织 id，按会议所属租户执行，同样不校验；Goldie Base 的 API-30、API-31 按设计 9.11.1 等值校验：非 SA 时组织 id（或该行所属租户）须等于会话租户，SA 放行 |
| 长任务 | Sync now 立即返回、异步拉取 | Start Extraction、证词补抽立即返回，前端轮询 API-21（线上 CloudFront 约 30 秒无响应即回 504） |
| 防过期提交 | — | 详情页的写接口都带 `updatedAt`（P1 乐观锁），0 行即提示刷新；凡改本场内容的写接口都要「碰」一下 P1 行（P1「防过期提交」） |

前端调 Python 走同源 `/api/ai/...`（开发代理 `config/proxy.ts:21`）。线上 `/api/ai` 怎么分流到 Python 在三个仓库里查不到：nginx 只有 `/api/web`、`/api/etl`（`nginx.prod.conf:163,176`），Java 网关只有 `/api/web/**`、`/web/**`（`cioaas-gateway.yml:27-39`）；`proxy.ts:19` 注释与 fileRegistry README 里「经 Java 网关转发」的说法已过时。应在 CloudFront / ALB 层，上线前与运维确认，不影响接口设计。

### 3.1 Java 接口

| 编号 | 方法 路径 | 功能 | 关键入参 | 关键出参 | 读写表 | 权限 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|---|---|---|---|
| API-01 | GET `/connection` | 连接状态 | `organizationId?` | `status`、`accountEmail`、`lastSuccessSyncAt`、`syncing`（`sync_started_at` 非空且未超过同步卡死时限，1.4）、`keyMask`（后 4 位，服务端拼好） | J1 读 | PGM / SA | PG-01b | 新增 |
| API-02 | POST `/connection/link` | 提交 key：调 Fireflies `user` 校验、加密落库；换账号按首次连接（9.2.6） | `apiKey`、`organizationId?` | 同 API-01；失败返回原因码（鉴权失败 / 网络不可达） | J1 写 | PGM / SA | PG-01b | 新增 |
| API-03 | POST `/connection/sync` | Sync now：条件更新抢占 `sync_started_at`，异步拉取（补投 → 拉列表 → 写原文 → 发 SQS），立即返回；正在同步、或没有 key（`UNCONNECTED`）时拒绝 | `organizationId?` | `syncing` | J1 写；J2 / J3 写；发 SQS | PGM / SA | PG-01b | 新增 |
| API-04 | POST `/connection/remove` | 清空密文、回 `UNCONNECTED` | `organizationId?` | 同 API-01 | J1 写 | PGM / SA | PG-01b1 | 新增 |
| API-05 | GET `/cheat-sheets` | 名册列表：每人取当前状态那一版（9.7.1），带逾期待复核标记 | `keyword`、`role`、`page`、`size`、`organizationId?` | `content[{id, name, emails, organization, role, expertiseTags, areaOfExpertise, validFrom, validTo, source, needsReview}]`、`totalElements`、`overdueCount` | J4 读 | PGM / SA | PG-01c | 新增 |
| API-06 | POST `/cheat-sheets` | 新建人员（第一版）；租户内重名拒绝并返回已有条目 | `name`、`emails`、`organization`、`role`、`expertiseTags`、`areaOfExpertise`、`validFrom`、`validTo`、`sourceMeetingId?`、`organizationId?` | 新行 `id`；重名时错误码 + 已有条目摘要 | J4 写（有 `sourceMeetingId` 记 `FF_SUMMARY_RECORDS`，否则 `MANUAL`） | PGM / SA | PG-01c1；Python 经 API-25、API-28 调用 | 新增 |
| API-07 | PUT `/cheat-sheets/{id}` | 编辑，按来源分两支：**Cheat Sheet 页**（不带 `sourceMeetingId`）按弹框追加一行完整新版本（9.7.1），什么都没改时只在当前状态那一行记复核（`reviewed_*`，9.7.5）；**会议页**（带 `sourceMeetingId`）以 `{id}` 那一版为底，对 From~To 内生效的各版本追加副本（9.5.7），没改动则什么都不写 | 同 API-06（无 `name`、`organizationId`） | 追加的行 id 列表；或 `reviewed: true` | J4 写 | PGM / SA | PG-01c1；Python 经 API-26 调用 | 新增 |
| API-08 | POST `/cheat-sheets/expertise-tags` | 专家确认同意：对此人自会议日期起生效的各版本各追加一份只加了新标签的副本（9.5.6）；租户由 `sourceMeetingId` 推出 | `name`、`tags`、`fromDate`、`sourceMeetingId` | 追加的行 id 列表 | J4 写；J2 读（推租户） | PGM / SA | 无页面，Python 经 API-28 调用 | 新增 |
| API-09 | GET `/cheat-sheets/{id}/history` | 此人全部版本，按 `valid_from`、`updated_at` 倒序 | — | `name`、`organizationId`、`rows[{…快照字段, updatedBy, updatedAt}]`（系统写入的显示为 `System (<fireflies_id> import)`） | J4 读；J2 取 `fireflies_id` | PGM / SA | PG-04 | 新增 |
| API-10 | GET `/email-domains` | 本租户邮箱域名 | `organizationId?` | `domains[]` | J1 读 | PGM / SA | PG-01c | 新增 |
| API-11 | PUT `/email-domains` | 整份提交（增、改、删都走它）：逐个去 `@`、转小写，校验格式、公共邮箱域名与重复；没有连接行时先建一行（`UNCONNECTED`）；应用日志记改前、改后两份列表（用户决定 2026-10-27，7 #Q22） | `domains[]`、`organizationId?` | `domains[]` | J1 写 | PGM / SA | PG-01c | 新增 |
| API-12 | GET `/expertise-tags` | 标签字典，按 `sort_no`；每项带能否删除 | `organizationId?` | `[{id, name, preset, deletable}]` | J5 读；J4（任一版本用过）、P5（未处理标记引用）读 | PGM / SA | PG-01c2 | 新增 |
| API-13 | POST `/expertise-tags` | 新增：不区分大小写重名拒绝，`sort_no` 追加到末尾 | `name`、`organizationId?` | 新标签 | J5 写 | PGM / SA | PG-01c2 | 新增 |
| API-14 | DELETE `/expertise-tags/{id}` | 删除：预置的、名册任一版本用过的、被未处理专家标记引用的拒绝 | — | — | J5 删；J4、P5 读 | PGM / SA | PG-01c2 | 新增 |
| API-15 | GET `/meetings` | Raw Data 列表：服务端过滤后分页，默认会议时间倒序 | `keyword`（会议 id、标题、参会人）、`dateFrom`、`dateTo`、`participants[]`（按显示名匹配出席记录姓名，或按邮箱匹配受邀邮箱）、`validity`（全部 / 只看 Invalid / 隐藏 Invalid）、`sort`、`page`、`size`、`organizationId?`（按设计稿，用户决定 2026-10-27，7 #Q20） | `content[{id, firefliesId, title, startedAt, durationMinutes, participantNames, ingestedAt, invalid}]`（`participantNames` 取出席记录姓名，没有出席记录的回退受邀邮箱，9.3.3）、`totalElements` | J2 读；P1 `identification_result` 读 | PGM / SA：本租户；公司端：会话租户内、本人邮箱在 `participants` 中 | PG-01d | 新增 |
| API-16 | GET `/meetings/participant-options` | 参会人筛选项：调用者看得到的会议里参会人显示名去重（口径同 `participantNames`） | `organizationId?` | `[{value, label}]` | J2 读 | 同 API-15 | PG-01d | 新增 |
| API-17 | GET `/meetings/{id}` | 原文页页头 | — | `organizationId`、`title`、`startedAt`、`durationMinutes`、`participantNames`、`capturedAt` | J2 读 | PGM / SA：按会议所属租户执行，只校验角色（7 #Q17）；公司端：会话租户内且本人邮箱在 `participants` 中 | PG-03 | 新增 |
| API-18 | GET `/meetings/{id}/sentences` | 逐句分批（滚动续加载，每批数百句） | `fromOrder`、`limit` | `[{order, speakerName, startTime, text}]`、`hasMore` | J3 读 | 同 API-17 | PG-03 | 新增 |
| API-19 | GET `/api/web/users/current` | 现有接口，`AuthenticatedUserDto` 加一个 PGM / SA 布尔字段（与 `superAdmin` 分开，字段名开发时定） | — | 新增字段 | 现有 | 登录 | PG-01、PG-05（标志位）；Python（判定 PGM / SA） | 改造（第八章 #22） |

### 3.2 Python 接口

| 编号 | 方法 路径 | 功能 | 关键入参 | 关键出参 | 读写表 | 权限 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|---|---|---|---|
| API-20 | GET `/summary-records` | Summary Records 列表（`processing_stage = DONE` 且非 Invalid），默认会议时间倒序；顺带返回 Tab 红点用的 Pending 数 | `keyword`（标题、会议 id、公司名）、`meetingType`、`status`（`PASSED` / `PENDING`）、`pendingReason`、`dateFrom`、`dateTo`、`page`、`pageSize`、`organizationId?` | `items[{meetingId, firefliesId, title, startedAt, durationMinutes, meetingType, companies[], status, pendingReasons}]`、`total`、`pendingCount{total, byReason}`（不受筛选影响） | P1、P4 读；LG `company` 读 | PGM / SA | PG-01、PG-01a | 新增 |
| API-21 | GET `/meetings/{meetingId}` | 会议详情，含矩阵；也是提取 / 补抽进行中的轮询接口 | — | 会议元信息、`organizationId`、`meetingType`、`status`、`pendingReasons`、待识别子原因（现算）、`extractionStatus`、`participantsChanged`（拿最新识别结果与 P1 `current_extraction_input` 比，按 9.9.1 口径：只补邮箱、改 Area of expertise、被推测者只改专长标签不算；前端据此与页头未提交的改动一起判 Start Extraction 与 Confirm & Apply 的置灰）；`companies[{companyId, name, adopted, basisText}]`（含未采纳候选）、`portfolioIds`、GS → 创始人的只读 Portfolio；`participants[{id, displayName, organization, role, badges, aiEvidence, clickAction, testimonyBackfillStatus, registryForm, expertCandidates[{tag, claims[], resolvedElsewhere}]}]`（`registryForm` 为登记 / 编辑弹框预填：名册中会议日期那一版，或未入册者的已知值，含 P8 推断；`aiEvidence` 为 AI inferred 悬停的依据）；`unmappedSpeakers[{speakerId, name, sentenceCount, aiSuggestedMatch, registryForm}]`；`routingRows[{rowId, outputType, destination, companyName, visibleTo, content, sourceLine, authorized, edited, projectionStatus}]`（按去向、发言人、出处时间点排序）；`updatedAt` | P1~P7 读；J2、J3（按说话人数句）、J4 读；LG 表读 | PGM / SA（会议所属租户） | PG-02、PG-02a~d | 新增 |
| API-22 | POST `/meetings/{meetingId}/extraction` | Start Extraction：页头写进识别结果、整场下线、后台提取，立即返回（6.11、9.5.1）。提取或证词补抽进行中、必填项不齐（9.5.1）时拒绝 | `meetingType`、`companyIds`、`updatedAt` | `extractionStatus = RUNNING`、`updatedAt` | P1、P4 写；P5、P7 软删并下线；P8 `TYPE_CHANGE` / `COMPANY_CHANGE` / `EXTRACT` | PGM / SA | PG-02 | 新增 |
| API-23 | POST `/meetings/{meetingId}/routing/apply` | Confirm & Apply Routing：授权勾选、Portfolio 标记、改 `Unknown`、GS → LP 的公司增删（9.6.5）。应用时按每一行的当前状态整体推一遍投影：已授权、未删、没上线的上线（含待确认专家期间默认勾选、一直没投影的行），取消授权的同步下线。有未处理的专家标记（改 `Unknown` 除外）、证词补抽进行中、GS → 创始人多于一家公司时拒绝 | `authorizations[{rowId, authorized}]`、`portfolioIds`、`meetingType?`（仅 `UNKNOWN`）、`companyIds?`（仅 GS → LP）、`updatedAt` | `status`、`updatedAt` | P7 写 + 投影；P1 状态与 `portfolio_ids`；改 `Unknown` 整场下线；P4；P8 | PGM / SA | PG-02 | 新增 |
| API-24 | PUT `/routing-rows/{rowId}/content` | 行内 Save（9.6.3 两步提交合在一个接口）：先跑 n-gram 与该去向适用的实体剥离——清洗后没有变化就落库（已授权的重投影，待确认专家时不投影）；有变化就不落库，返回清洗结果与命中明细，管理员确认后把清洗后的文本连同首次提交稿再提交一次，这次不再有变化即落库，`CONTENT_EDIT` 记改前、首次提交稿、定稿与命中（服务端按首次提交稿重算）。摘要行超过 150 个英文单词拒绝 | `content`、`originalContent?`（第二次提交时带首次提交稿）、`updatedAt` | 落库时：该行、`updatedAt`；未落库时：`cleanedContent`、`hits[]`（删去的行及原因、替换的实体）、`wordCount` | P7 写；P1 写（碰行）；J3 读（比对基准）；P8 `CONTENT_EDIT` | PGM / SA | PG-02 | 新增 |
| API-25 | POST `/meetings/{meetingId}/external-parties` | Assign new external party：先看填的邮箱是不是本租户 LG 平台用户——是就不进名册，按平台用户更新本场 P2 / P3（必要时 P4）；否则调 API-06 写名册，更新本场 P2 / P3；重名时可选关联已有条目（9.5.5、9.5.7）。之后重跑类型判定 | `participantId` 或 `speakerId`、表单字段、`linkExistingName?`、`updatedAt` | 更新后的参会人、`suggestedType?`（可判定为 X）、`participantsChanged`、`updatedAt`；重名错误码 + 已有条目 | P2、P3、P1（碰行）写，必要时 P4；LG 表读；J4 经 API-06 | PGM / SA | PG-02a | 新增 |
| API-26 | PUT `/meetings/{meetingId}/external-parties/{participantId}` | Edit external party：调 API-07（带 `sourceMeetingId`），刷新本场 P2；被推测者只改了专长标签时为他补抽证词（提示词 P5）并同步提取输入（2.5、9.9.1） | 表单字段、`updatedAt` | 同 API-25 + `testimonyBackfillStatus` | P2、P1、P7 写；P8 `EXTRACT`；J4 经 API-07 | PGM / SA | PG-02b | 新增 |
| API-27 | POST `/meetings/{meetingId}/speakers/{speakerId}/assignment` | 把未对上的说话人指定为本场某位参会人，重跑类型判定 | `participantId`、`updatedAt` | 说话人、`suggestedType?`、`participantsChanged`、`updatedAt` | P3、P2（`matched_name`）、P1（碰行）写 | PGM / SA | PG-02d | 新增 |
| API-28 | POST `/meetings/{meetingId}/expert-candidates/{participantId}/decisions` | 确认框 Save：逐标签同意 / 拒绝，并把已入册或已在拒绝名单的标签一并落库（自动消解，用户决定 2026-10-27，7 #Q22）；同意写名册（未入册的经 API-06 新建，重名时可选关联已有条目；已入册的经 API-08 加标签），拒绝写拒绝名单；后台为此人补抽证词（2.5） | `decisions[{tag, accept}]`、表单字段、`linkExistingName?`、`updatedAt` | 参会人、`testimonyBackfillStatus`、`updatedAt`；重名错误码 + 已有条目 | P5、P6、P2、P7、P1 写；P8 `EXTRACT`；J4 经 API-06 / API-08 | PGM / SA | PG-02c | 新增 |
| API-29 | POST `/meetings/{meetingId}/participants/{participantId}/testimony-backfill` | 证词补抽失败后 Retry | `updatedAt` | `testimonyBackfillStatus` | P2、P7、P1（碰行）写；P8 `EXTRACT` | PGM / SA | PG-02 | 新增 |
| API-30 | GET `/goldie-base/contents` | Goldie Base 两个新 Tab 共用：已授权、已投影的跨公司内容，或署名版证词（9.11.4、9.11.5）；关键词匹配内容与会议名称（证词另匹配说话人姓名），按会议日期区间过滤；按会议时间倒序、同一场会内按出处时间点排，按行分页，前端把相邻的同场行归成一张卡片（排序与会议名称匹配用 P7 冗余的会议时间与标题，7 #Q23） | `type`（`CROSS_COMPANY` / `TESTIMONY`）、`keyword`、`dateFrom`、`dateTo`、`page`、`pageSize`、`organizationId?` | `items[{rowId, content, meeting{meetingId, firefliesId, title, startedAt, meetingType, canOpen}, inPlaybook, speakerName?, expertiseTags?}]`（后两项仅证词）、`total`、`canTogglePlaybook` | P7 读（排序、筛选都在 P7 内完成）；分页后按会议 id 批量读 P1（会议类型、`fireflies_id`）；证词另读 P2（说话人；关键词匹配说话人时先在 P2 按姓名查出参会人 id） | 管理端 PM / PGM / SA；公司端拒绝 | PG-05c、PG-05d | 新增 |
| API-31 | PATCH `/routing-rows/{rowId}` | 改中间表行上的标记，立即生效、不写审计：`inPlaybook`（Play candidate，限跨公司行与证词署名行，PGM / SA）；`fundTagIds`（基金标签，限知识库正文行，看得到该行的管理端 PM / PGM / SA——机构层行按租户判，候选须在本租户 `company_group` 内） | `inPlaybook?`、`fundTagIds?`（一次改一个） | 改后的值 | P7 写 | 按字段（见功能）；租户按 9.11.1 等值校验 | PG-05c、PG-05d、PG-05a1 | 新增 |
| API-32 | GET `/org-options` | 本租户全部公司（含不在营的，带状态）与全部 Portfolio：会议页 Company / Portfolio 下拉候选（只有 PGM / SA 进得了会议页，按设计 9.5.3 / 9.5.4 即本租户全部）、知识库基金标签候选（设计 9.11.2 为本租户 Portfolio）。不复用 Java `companyGroup/companies`：它返回「公司 × Portfolio」配对，没挂 Portfolio 的公司不返回、也不去重 | `organizationId?`（会议页传会议所属租户） | `companies[{companyId, name, status}]`、`portfolios[{companyGroupId, name}]` | LG `company`、`r_organization_company`、`company_group` 读 | 管理端（PGM / SA；PM 用于基金标签） | PG-02、PG-05a1 | 新增 |

### 3.3 改造与复用的现有接口

| 编号 | 方法 路径 | 改什么 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|
| API-33 | GET `/api/ai/file-registry/files` | 主表仍是登记表 `ai_file_registry`（分页、排序、筛选都在登记表上），P7 / P1 只在分页后按本页的 Fireflies 行补查。筛选与搜索保持现有：搜索只按文件名，不加设计稿的 Source 筛选（用户决定 2026-10-27，7 #Q24a）；Source 列照加。纳入 `FIREFLIES` 行，对公司端普通用户不按 `created_by` 收窄；机构层作用域按组织 + 机构层空间圈定；`source` 取值由 `company` / `session` 改为 `GOLDIE` / `FIREFLIES`（改语义，原值前端未使用，设计第八章 #18）；Fireflies 行经 P7 按 `file_id` 带出会议 id、能否跳原文、中间表行 id（供 API-31 改基金标签）、`fundTags` 与 Portfolio 回退；From Chat 显示 `—`、Uploaded By 显示 `System`（设计 9.11.2 交开发设计定，设计稿该格写的是公司名，按语义不沿用）（第八章 #11~#13、#16、#18） | PG-05a | 改造 |
| API-34 | GET `/api/ai/file-registry/files/filter-options` | 上传者选项纳入 Fireflies（显示 `System`） | PG-05a | 改造 |
| API-35 | GET `/api/ai/file-registry/files/{entryId}/download` | 加 `FIREFLIES` 分支：公司端限本公司 APP 端，管理端限可访问公司或本组织机构层（#12） | PG-05a | 改造 |
| API-36 | PUT、DELETE `/api/ai/file-registry/records/{registryId}` | `update_record` / `delete_record` 里按 `business_type` 显式拒绝 `FIREFLIES` / `FIREFLIES_SUMMARY` 行（现在两处都不看业务类型，DELETE 还会连带删 RAG 条目与向量）；`_PROTECTED_BIZ_TYPES` 另加这两个类型，防聊天上传改写会议行；Fireflies 行前端不显示删除（#12） | PG-05a | 改造 |
| API-37 | GET `/api/ai/memories` | 仍是「登记表圈定条目 → `ai_rag_entry` 取摘要分页」两步，不读 P7（Fireflies 摘要在投影时已写进条目的 `summary`）。纳入 `FIREFLIES_SUMMARY`，返回项加来源字段，增加机构层（#11、#13、#19）。管理端 `scope` 加取值 `fireflies`：只看会议摘要、不分层；公司端不加筛选；设计稿 File Scope 里的 Document Summary 选项不加。会议摘要的标签并排显示：层徽标（Company / Portfolio Memory，管理端）+ Fireflies Memory + Meeting Summary；文件摘要不变（用户决定 2026-10-27，7 #Q24b） | PG-05b | 改造 |
| API-38 | POST `/api/ai/sse/stream`（Goldie 召回） | 接口契约不变；召回改造见第八章 #7~#10 | Ask Goldie 对话（不在本页面清单） | 改造 |
| API-39 | GET `/api/web/organization/findByTree` | 不改：PG-01 的租户下拉、PG-05 的默认租户 | PG-01、PG-05 | 复用 |
| API-40 | POST `/api/web/storage/uploads/presign`、`/uploads/{id}/verify` | 接口不改；`FileBusinessTypeEnum` 新增 Fireflies 类型、放行 `md`（#3）。Python 投影上传 markdown 用 | 无页面 | 改造（枚举） |

接口合并（用户决定 2026-10-27，7 #Q22）：会议详情一次取回弹框预填、专家建议标签与矩阵；Summary Records 列表顺带返回红点数；行内 Save 的清洗预览与落库合成一个接口；专家确认框不再单设「打开即消解」接口，改为详情里标出、Save 时一并落库；两个新 Tab 共用一个列表接口；Play candidate 与基金标签合成一个改标记接口；Email Domain 整份提交。审核时发现 Java `companyGroup/companies`、`companyGroup/user` 的口径不合用，改由 API-32 提供候选。

### 3.4 页面 × 接口对账

| 页面 | 加载 | 操作 |
|---|---|---|
| PG-01 | API-19（显示哪些 Tab、PM 无权限提示）、API-39（租户下拉）；PGM / SA 的红点取 API-20 的 `pendingCount`（默认 Tab 即 Summary Records，从其他 Tab 进入时调一次 API-20）。公司端只调 API-19，不调 API-20 / 39 | 切换租户后 URL 带 `org`，各 Tab 带 `organizationId` 重新加载 |
| PG-01a | API-20 | 搜索、类型 / 状态 / 时间筛选、分页：API-20 |
| PG-01b | API-01 | Link：API-02；Sync now：API-03（之后轮询 API-01 看 `syncing`） |
| PG-01b1 | — | Remove：API-04 |
| PG-01c | API-05、API-10 | 搜索、Role 筛选、分页：API-05；域名增 / 改 / 删：API-11（整份提交） |
| PG-01c1 | 编辑时用 API-05 的行数据预填 | Confirm：新增 API-06，编辑 API-07 |
| PG-01c2 | API-12 | `Add "<值>"`：API-13；删除：API-14 |
| PG-01d | API-15、API-16 | 搜索、日期 / 参会人 / 有效性筛选、排序、分页：API-15 |
| PG-02 | API-21、API-32 | Start Extraction：API-22（之后轮询 API-21）；Confirm & Apply：API-23；行内 Save：API-24（有命中时确认后再调一次）；证词补抽 Retry：API-29；Discard Changes 只在前端 |
| PG-02a | 用 API-21 的 `registryForm`；API-12 | Confirm：API-25；标签维护：API-13 / 14 |
| PG-02b | 用 API-21 的 `registryForm`；API-12 | Confirm：API-26；标签维护：API-13 / 14 |
| PG-02c | 用 API-21 的 `expertCandidates`、`registryForm`；API-12 | Save：API-28；标签维护：API-13 / 14 |
| PG-02d | 用 API-21 的参会人列表与说话人的 `aiSuggestedMatch` | 确认：API-27 |
| PG-03 | API-17、API-18（首批） | 滚动续加载：API-18 |
| PG-04 | API-09 | — |
| PG-05 | API-19、API-39 | — |
| PG-05a | API-33、API-34 | 下载：API-35；删除：API-36；Source 链接跳 PG-03 |
| PG-05a1 | API-32 | 选择：API-31（`fundTagIds`） |
| PG-05b | API-37 | — |
| PG-05c | API-30（`type=CROSS_COMPANY`） | 搜索、时间筛选、分页：API-30；开关：API-31（`inPlaybook`）；会议名跳 PG-02（`canOpen`） |
| PG-05d | API-30（`type=TESTIMONY`） | 同 PG-05c |

对账结果：每个页面的加载与改数据操作都有接口；没有页面直接使用的接口只有 API-08（Python 专家确认时调用）与 API-40（Python 投影上传），调用方见 3.5；API-38 由 Ask Goldie 对话使用，对话页不在本清单。设计稿与设计文档不一致、尚待拍板的几处见 7 #Q24。

### 3.5 无页面的调用与跨服务链路

| 调用 | 调用方 → 被调方 | 说明 |
|---|---|---|
| 每日拉取 | AWS EventBridge → `scheduler-queue` → Java `ScheduleProcessor` | `FixedScheduleTypeEnum` 加一项，分发到 Fireflies 拉取服务（与 API-03 同一链路）；入口先 `setCurrentUserId("1")`；定时与手动互斥靠 J1 `sync_started_at` 条件更新（第八章 #29） |
| 新会议 | Java → SQS 新队列（如 `fireflies-meeting-queue`）→ Python `consumer/fireflies/` | 队列在 Java `InitSqsQueueEnum` 登记（启动时建队列与死信队列），Java 不监听；消息带租户、会议 id、触发方式与触发人；投递与补投见 J2（第八章 #30） |
| 公司 / 公司端用户增改 | Java 保存入口发领域事件 → `@TransactionalEventListener(AFTER_COMMIT)` → SQS 新队列（如 `fireflies-company-change-queue`，同样在 `InitSqsQueueEnum` 登记）→ Python 自动路由 | 入口：`CompanyServiceImpl.create` / `update`（`addWithoutEmail`、`addCompanyAndSetStage` 都汇到这两处）、`CommonServiceImpl.createInvitedUserAndSendEmail`（覆盖 `POST /users/invite` 与 `POST /project/inviteuser`，后者设计第八章 #27 漏列）、`UserServiceImpl.clientUser` / `update`。归档（`POST /invite/archiveCompany`）与停用（`PUT /invite/delete/{companyId}`）不发：公司只会因此变成不在营，不会产生新的匹配。Python 现有约定一条队列一种消息，故两条队列（第八章 #27） |
| 名册写入 | Python → Java API-06 / 07 / 08 | 透传用户 token（第八章 #31） |
| PGM / SA 判定 | Python → Java API-19 | 透传用户 token |
| 投影上传 markdown | Python → Java API-40 | SQS 触发的后台任务没有用户 token，回退静态 service token：各环境要配长期有效的 `LGPI_BEARER_TOKEN`（代码里写死的默认值是某用户 JWT，约 2026-12-28 过期） |
| 跨端读表 | Java 读 P1、P5；Python 读 J1~J5 与 7 张 LG 业务表 | 见 1.4；Python 直读 LG 业务表与 Python 规范「LG 业务数据经 Java 网关取」不一致，随数据权限一起定（A5）。现有只读映射 `lg/db/models/models.py:570` 起的 `Company` 没有公司名列，API-20 / 21 / 32 要补 |
| 卡死兜底 | 定时清扫（单独功能，与本功能一起上线） | 见 P1「卡死兜底」 |

跨服务调用链：

- 拉取：Java 定时 / API-03 → Fireflies GraphQL → J2 / J3 → SQS → Python 识别与提取 → P1~P7 → API-40 上传 markdown → RAG 条目 + X1 登记
- 登记参会人：前端 → Python API-25 / 26 →（非平台用户）Java API-06 / 07 → Python 更新 P2 / P3
- 专家确认：前端 → Python API-28 → Java API-06 / 08 → Python 写 P5 / P6，后台补抽证词（提示词 P5）→ 写 P7 → 投影
- 自动路由：前端 → Java 公司 / 用户保存 → 事务提交后 SQS → Python 重跑 ②③ → 自动提取
- Raw Data 的 Invalid：前端 → Java API-15 → 读 Python 表 P1

## 4. 页面功能按钮

（第 4 步）

## 5. 页面布局

（第 5 步）

## 6. 需求追溯

（一致性自检时补）

## 7. 待确认问题

第 1~3 步的问题已全部拍板，暂无待确认项。

已定（用户决定 2026-10-27；Q1~Q13 在确认① 中拍板，Q14 起在确认② 中拍板）：

| # | 问题 | 结论 | 落在 |
|---|---|---|---|
| Q1 | 设计稿 Configuration 显示 key 后 4 位、有 `Remove`；设计 9.2.5 原写「从不回显 key，连掩码都不显示，没有断开按钮」 | 按设计稿：查询接口在服务端解密后只返回掩码串（后 4 位），原文与密文都不出接口；Remove 清空密文、状态回 `UNCONNECTED`、暂停定时拉取，写 Java 应用日志 | J1；设计 9.2.3~9.2.5、9.2.7 已回写 |
| Q2 | Python 物理表名 `ai_ff_*` 还是 `ai_fireflies_*` | `ai_ff_*` | A3、P1~P8 |
| Q3 | Java 表时间列 `timestamptz` 还是跟 ERL 用 `timestamp(6)` | `timestamptz` | A2、J1~J5 |
| Q4 | 专长标签 5 项预置：首次读时懒加载，还是新建组织时写入 | 新建组织时写入（`OrganizationServiceImpl.save` 加一行，同 KPA、Tech Stack 初始化先例），存量组织由 Java V1 迁移补齐；懒加载不行：Python 直读字典，Java 没读过的租户 Python 会读到空 | J5、设计 9.8.1 |
| Q5 | GS 租户的 3 个邮箱域名：迁移脚本写死（要各环境的 GS 组织 id），还是上线时管理员在页面加 | 上线时管理员在 Cheat Sheet 页添加，不写迁移 | J1、1.4「种子数据」；设计 9.7.7 已回写 |
| Q6 | Java 的 SQS 发送失败不抛异常（`SQSServiceImpl` 只打日志），`dispatched_at` 怎么保证 | 新增返回成败的发送方法，拿到消息 id 才写 `dispatched_at`；失败的在每次拉取开始时补投，不限回看窗口、不设次数上限；Python 按会议去重 | J2「投递与补投」；设计 9.3.1、第八章 #30 已回写 |
| Q7 | Fireflies Management 菜单：管理后台手工配置，还是写迁移 | 管理后台手工配置，只挂给 PGM / SA 的角色（ERL 先例），不写迁移 | 1.4「种子数据」；设计第八章 #32 已回写 |
| Q8 | Play candidate 是挂在证词 / 跨公司条目上的开关，还是单独一种产出 | 开关：只把本条标记为 playbook 候选，不影响授权、投影与召回，Goldie Base 两个 Tab 仍只读查看；候选由后续另一任务处理、产出 playbook（不是本项目 Goldie 召回的 Playbook 手册）。存 P7 `in_playbook`，证词打在署名行 | P7；设计 9.11.6、第十章 #62 已回写 |
| Q9 | 摘要与 KB 正文是否共用一个 Authorize | 分开（同设计稿：矩阵两行各一个 Authorize）。P7 加 `output_type`、删 `summary`；摘要行单独投成条目（登记 `FIREFLIES_SUMMARY`，进 Memory Tab），知识库行条目不带摘要（登记 `FIREFLIES`，进 Knowledge Base Tab）；唯一约束先不加 | P7、X1、1.4；设计 1.1~1.3、2.4、9.6.2、9.6.6、第八章 #4 / #11 已回写 |
| Q10 | 跨公司与证词提取完默认勾不勾 Authorize | 维持现行设计：跨公司一律默认不勾、要管理员审核（会议因此 Pending · 待审核）；证词按邮箱认出发言人的两版默认勾选，经 P8 认出的默认不勾 | P7 授权初值；设计 9.6.4、9.9.5 不变 |
| Q11 | 收到重投、会议还在识别中 / 提取中怎么办（原写「1 小时内视为有人在跑、跳过」，但重投约 10 分钟就到，自动重跑实际不会发生） | 重投（接收次数 ≥ 2）即上一处理者已不在，直接接手从头重跑；凭 `processing_started_at` 条件更新，老进程落库时核对不上即放弃；首次收到却已有状态行的是 Java 重复发送，删掉 | P1 `processing_started_at`；设计第八章 #30 已回写 |
| Q12 | 卡死清扫要不要本期做（Python 没有定时任务框架） | 拆为单独功能，与 AI 财务提取任务卡在 `PROCESSING` 一起做，Fireflies 开发完成后设计、与本功能一起上线；死信 / 过期的首轮会议与已投递无状态行的会议交给它；非首轮提取与证词补抽卡在 `RUNNING` 也由它判超时，本功能不做读时判断 | P1「卡死兜底」、P2、1.4；code-examples 第 4 节；设计 1.10、第八章 #30 已回写 |
| Q13 | 首轮处理中途没跑完（进程被杀、代码异常）的产出与会议怎么处理 | 只要没跑完，本次产出全部作废；首轮每次开跑先删本场产出、从头跑，不从中断处接着跑；连续 3 次没跑完不做特殊处理，停在处理中、交给定时清扫。首轮跑完才进 Summary Records（Passed / Pending），处理中不显示。大模型最终失败不在此列（设计 6.11） | P1 `processing_started_at`、「卡死兜底」；J2；设计 1.10、9.5.9、第八章 #30、提示词 6.11 已回写 |
| Q14 | 管理端入口放哪 | 头像下拉（按设计稿，同 ERL 的 `menuRight_SuperAdmin`），后台菜单 path `/fireflies` | 第 2 节「入口与守卫」；设计第八章 #32 已回写 |
| Q15 | 公司端入口放哪（设计稿没有公司端页面） | 也放头像下拉，放在订阅条件之外（同 Switch Companies）；所有公司端用户都显示，没有受邀会议的看到空列表；进去只有 Raw Data Tab | 第 2 节「入口与守卫」；设计 9.3.6、第八章 #28、第十章 #90 已回写 |
| Q16 | Goldie Base 的路由形态（设计 9.11.1 交开发设计定） | `/askGoldie/goldieBase?tab=…`，放在 `/askGoldie` 下，门户布局判定与顶栏高亮不用改；旧 `/knowledgeBase`、`/memorySettings` 重定向到对应 Tab | 第 2 节 PG-05；设计 9.11.1 已回写 |
| Q17 | Fireflies Management 的切换租户与组织 id 校验 | 组织树根下有子组织才显示下拉（同 ERL、Portfolio Companies），默认会话租户；SA 可借此切到子租户查看；后端先不校验组织 id，信任前端传入，PGM / SA 角色照常校验 | 第 2 节「入口与守卫」、第 3 节通用约定；设计 9.1、第十章 #69 已回写 |
| Q18 | Java 包结构与路径命名 | 按 Java 规范：`web/fireflies/` 分 DDD 四层、路径 kebab-case 复数；不照 ERL 的平铺包与驼峰单数路径 | 第 3 节通用约定 |
| Q19 | 会议页弹框里新增 / 删除专长标签走哪 | 前端直接调 Java API-13 / 14（带会议所属租户），不经 Python 转发，与 Cheat Sheet 页同一组件、同一组接口；名册写入仍经 Python（要同时更新本场识别结果、触发补抽） | 1.1 J5、1.4、第 3 节 API-13 / 14；设计第八章 #31 与「两端怎么衔接」已回写 |
| Q20 | Raw Data 的筛选与排序（设计 9.3.3 只有关键词搜索） | 按设计稿：关键词 + 日期区间 + 参会人多选 + 有效性筛选 + 列头排序，服务端过滤后分页；筛选状态存会话，从原文页返回时恢复 | 第 3 节 API-15 / 16；设计 9.3.3 已回写 |
| Q21 | Ask Goldie 对话里展示 Fireflies 来源链接 | 本期不做：需求与设计稿都没有，现有聊天也没有结构化来源；召回改造照做，对话页面不改，以后需要再单独立项 | 第 2 节「不在本期」 |
| Q22 | 前端两端都能直调，接口有没有可删减或复用的 | 合并 8 处，50 → 41 个：会议详情一次取回弹框预填、专家建议标签与矩阵；Summary Records 列表顺带返回红点数；行内 Save 的清洗预览与落库合成一个接口；两个新 Tab 共用一个列表接口；Play candidate 与基金标签合成一个改标记接口；Email Domain 整份提交；专家确认框不再「打开即消解」，改为标出「已在别的会议处理过」、`Save` 时一并落库。名册写入仍经 Python（规则留在后端） | 第 3 节；P5；code-examples 第 2 节；设计 9.5.6、9.5.10、9.7.7、第八章 #20、#26、第十章 #63、提示词 6.11 已回写 |
| Q23 | Goldie Base 两个新 Tab 的排序与会议名称匹配（内容在 P7、会议时间与标题在 P1，Python 仓储不许跨表 JOIN） | P7 冗余 `meeting_started_at`、`meeting_title`（投递后不变，同 P1 冗余 J2），`idx_ai_ff_routing_row_tab` 改为按 `meeting_started_at DESC`；会议类型、`fireflies_id` 分页后批量查 P1。对已确认表结构的变更 | P7、1.1、code-examples 第 2 节、API-30 |
| Q24 | 设计稿与设计文档不一致的 4 处（A1 要求列出） | a. Knowledge Base 保持现有功能：搜索只按文件名，不加 Source 筛选（Source 列照加）；b. Memory Settings：管理端 File Scope 加一项 Fireflies Memory（只看会议摘要），Document Summary 选项不加，公司端不加筛选；会议摘要标签并排：层徽标 + Fireflies Memory + Meeting Summary；c. 专家确认框按需求逐个标签同意 / 拒绝，不照设计稿的整人 Approve / Reject；d. Expertise tags 维持选填，不照设计稿的必填 | API-33、API-37、PG-02c、PG-01c1；设计 9.5.6、9.7.4、9.11.2、9.11.3、第十章 #46 已回写 |
