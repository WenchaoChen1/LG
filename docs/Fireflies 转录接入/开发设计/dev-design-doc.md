# Fireflies 会议转录接入 — 开发设计

> 关联文档: [会议内容提取规则](../调研/会议内容提取规则-需求文档.md) · [AI Meeting Type 自动映射标准](../调研/AI%20Meeting%20Type%20自动映射标准-需求文档.md) · [Cheat Sheet](../调研/Cheat%20Sheet-需求文档.md) · [Fireflies Configuration](../调研/Fireflies%20Configuration-需求文档.md) · [Fireflies Raw Data](../调研/Fireflies%20Raw%20Data-需求文档.md) · [Fireflies Summary Records](../调研/Fireflies%20Summary%20Records-需求文档.md) · [Goldie Base](../调研/Goldie%20Base需求文档.md) · [设计](../设计/design-doc.md) · [抽取提示词](../设计/extraction-prompts.md) · [代码示例（DDL）](./code-examples.md) · 设计稿：Lovable 项目 FFL（`5c905189-2a86-4020-abec-88a276b00861`，commit `76cc767`）
>
> **本文范围**：三端共用的契约——表、页面、接口、按钮、布局、需求追溯与开发任务拆分。按 `docs/CLAUDE.md`「不在一个文件中混写 Java + Python + 前端的实现细节」，各端的实现细节（类结构、关键算法、异常处理）开发前按需另拆 `dev-java.md` / `dev-python.md` / `dev-frontend.md`。
>
> **进度**：第 1 步（表）已确认（2026-10-27）；第 2、3 步（页面、接口）已写完并审核，确认② 的问题（Q14~Q24）已全部拍板（2026-10-27），补审带出的 Q25、Q26 在确认③ 中拍板（2026-10-28）；第 4、5 步（按钮、布局）已写（2026-10-27），确认③ 已通过（2026-10-28），进入第 6 步开发；第 0、1 波已完成，第 2 波集成中，开发期补定的契约见 3.6，新发现的待确认问题见 7 #Q27~#Q40（2026-10-28）；投影改为纯文本条目见 7 #Q41（2026-10-28）；审核环节重新设计会议页回写 Cheat Sheet（前端直调 Java 保存、关窗后同步，拒绝名单改为 Java 表 J6，重名自动加后缀等），见 7 #Q44~#Q48（2026-10-29）。

## 0. 概述

**做什么**：把 Fireflies 录制的 Teams 会议拉进 LG，自动识别参会人与会议类型，用大模型提取摘要、知识库文档、跨公司内容与专家证词，经管理员审核后按可见范围投影进 Goldie 的知识库与记忆；管理端提供 Fireflies Management（Summary Records / Configuration / Cheat Sheet / Raw Data 四个 Tab），Ask Goldie 下新增 Goldie Base 页。

**谁用**：管理端 PGM / Super Admin（全部功能）、PM（Goldie Base 两个新 Tab 只读）、公司端创始人（Raw Data 看本人受邀会议的原文，以及 Goldie 召回）。

**涉及服务**（分工按设计第八章开头，第十章 #91）：

| 端 | 负责 |
|---|---|
| Java `CIOaas-api` | Configuration、Cheat Sheet（名册、专长标签、Email Domain、专家建议标签拒绝名单）、Raw Data（含公司端）、每日拉取与 Sync now；会议页的名册编辑与专家确认保存（前端直调，7 #Q44）；配套：新会议 / 公司增改经 SQS 交 Python、PGM/SA 判定方法、给 Python 的名册新建接口（Assign new external party 用） |
| Python `CIOaas-python` | 识别（P1 / P8）、提取与清洗（P2~P7）、中间表与投影入库、Summary Records 与矩阵、名册保存后的本场同步（含证词补抽）、改判重算与自动路由、Goldie Base 两个新 Tab |
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
| J4 | `ff_cheat_sheet` | 外部人员名册（一行一个版本） | 新增 | Java（Python 只在 Assign new external party 时经 API-06 新建） | Java、Python | 18 |
| J5 | `ff_expertise_tag` | 专长标签字典 | 新增 | Java | Java、Python | 9 |
| J6 | `ff_expert_rejection` | 专家建议标签拒绝名单 | 新增 | Java | Java、Python（只读：识别前过滤、同步时判已驳回） | 9 |
| P1 | `ai_ff_meeting_state` | 会议处理状态（类型、状态、提取输入…） | 新增 | Python | Python、Java（只读 `identification_result`） | 22 |
| P2 | `ai_ff_meeting_participant` | 识别结果：参会人 | 新增 | Python | Python、Java（只读本场邮箱，专家确认保存写拒绝名单时取） | 22 |
| P3 | `ai_ff_meeting_speaker` | 识别结果：说话人绑定 | 新增 | Python | Python | 14 |
| P4 | `ai_ff_meeting_company` | 识别结果：公司关联与候选 | 新增 | Python | Python | 16 |
| P5 | `ai_ff_expert_candidate` | 专家候选（可能为专家的标签） | 新增 | Python | Python、Java（只读，标签删除校验） | 15 |
| P7 | `ai_ff_routing_row` | 路由中间表（矩阵正本与投影记录） | 新增 | Python | Python | 25 |
| P8 | `ai_ff_audit_log` | 审计：路由决策与覆写 | 新增 | Python | — | 11 |
| X1 | `ai_file_registry` | 知识库登记行：新增业务类型 `FIREFLIES` / `FIREFLIES_TESTIMONY` / `FIREFLIES_CROSS_COMPANY`（只改列注释） | 改造 | Python | Python、Java（已有实体映射，只写财务抽取行，不碰 Fireflies 行） | +0 |

Python 表编号 P6 空出：拒绝名单改为 Java 表 J6（7 #Q45），P7、P8 不改号。

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
| 软删 | 6 张表都不设（只追加或物理删除） | P5、P7 软删：`deleted BOOLEAN NOT NULL DEFAULT FALSE`，配 `WHERE deleted = FALSE` 部分索引；其余只追加、物理删除或整场先删后写 |
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
  - `idx_ff_meeting_meta_info_participants_gin USING gin (participants jsonb_path_ops)` —— 公司端「本人受邀的会议」（`participants @> '["<email>"]'`）、按邮箱筛参会人；按显示名筛时匹配 `attendance`，每租户会议量小，不另建索引
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
| 第一次就成功 | 周二 03:40 入库、发送成功、写 `dispatched_at`，Python 识别提取；之后回看再拉到只比 `content_hash`，不改原文、不重发 |
| 第一次失败，第二次成功 | 周二 03:40 发送失败，`dispatched_at` 为空：Raw Data 能看到 A，Summary Records 还没有；下一次拉取（管理员点 Sync now，或周三 03:40）先补投，成功后写 `dispatched_at`，Python 开始处理 |
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
| `name` | varchar(255) | 否 | — | 唯一识别符，同一人各版本同值；新建时租户内重名（忽略大小写）不拒绝、不合并，应用层自动加数字后缀（Tom → Tom1 → Tom2，取第一个未占用编号，7 #Q46） | 9.7.1 |
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
- 只追加：每次保存（Cheat Sheet 页 Confirm、会议页 Edit external party、专家确认 Save）只追加一条完整的新行，不改旧行（7 #Q44）；复核只改 `reviewed_*`

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

#### J6 `ff_expert_rejection`

专家建议标签的拒绝名单（用户决定 2026-10-29，7 #Q45：原为 Python 表，改由 Java 在专家确认保存的同一事务里写）。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `organization_id` | varchar(36) | 否 | — | 租户；拒绝名单按租户生效 | 9.5.6 |
| `email` | varchar(255) | 否 | — | 被驳回者在本场参会人行（P2）上的邮箱，小写 | 9.5.10 |
| `tag` | varchar(64) | 否 | — | 被驳回的标签 | 9.5.6 |
| `meeting_id` | varchar(36) | 否 | — | 来源会议（`ff_meeting_meta_info.id`） | 9.5.6 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计（基类） | |

- 主键 `pk_ff_expert_rejection (id)`
- 唯一 `uk_ff_expert_rejection_org_email_tag (organization_id, email, tag)` —— 同一（邮箱, 标签）重复驳回不重复写；Python 按人展开邮箱时用 `email IN (...)`
- 写：只有 API-08（专家确认保存）在同一事务里写：驳回 = 本次建议标签 − 保存后的 Expertise tags（没有登记字段时全部算驳回）；邮箱取 P2 该参会人的本场邮箱（Java 只读 P2）
- 读：Python 只读——识别前从大模型标签里去掉（建议标签 = 大模型标签 − T1 − 拒绝名单，T1 见 P2 `expertise_tags`）、详情 `resolvedAs`、同步（API-28）判已驳回；查询「按人展开」：本场邮箱或此人名册各版本任一邮箱命中即算

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
| `pending_reasons` | JSONB | 否 | `'[]'` | Pending 原因：`TO_IDENTIFY`（待识别）/ `TO_CONFIRM_EXPERT`（待确认专家）/ `TO_REVIEW`（待审核），可并存；列表的原因旁注、详情与红点计数用；状态筛选只分 Passed / Pending，不按原因筛（7 #Q25d） | 9.4.2 |
| `portfolio_ids` | JSONB | 否 | `'[]'` | Portfolio 标记，`company_group` id | 9.5.4 |
| `processing_stage` | VARCHAR(16) | 否 | `'IDENTIFYING'` | 首轮自动加工进度：`IDENTIFYING`（识别中）/ `EXTRACTING`（提取中）/ `DONE`（完成）；`DONE` 且 `meeting_status` 非空才进列表，之后不回退。`Invalid` 与待识别的会议识别完即置 `DONE`、不经 `EXTRACTING`，`Invalid` 的 `meeting_status` 保持为空——停在 `IDENTIFYING` 会被当成卡死（下「卡死兜底」） | 1.10 |
| `processing_started_at` | TIMESTAMPTZ | 否 | — | 首轮本次处理的开始时间（建行时写入），兼作「谁在处理」的凭证。首轮每次开跑（新建本行或接手重跑）先删本场全部产出（P2~P5、P7），从识别第一步跑起，不从中断处接着跑：首轮还没进列表、也没投影过，删了不影响任何人；产出只有跑完才算数（用户决定 2026-10-27，7 #Q13）。收到消息时按本行分三种（用户决定 2026-10-27）：① 没有本行 → 建行处理；② `DONE` → 重复消息，删掉；③ 仍在 `IDENTIFYING` / `EXTRACTING`：重投（`ApproximateReceiveCount` ≥ 2）说明上一个处理者已不在——它活着时会一直延长消息的不可见时间，消息不会重新出现——直接接手从头重跑、不看时间；首次收到（= 1）却已有本行，是 Java 重复发送（J2「发送成功，写 `dispatched_at` 失败」），原消息仍在队列里，删掉本条。接手时把本列条件更新为本次开始时间（`WHERE processing_started_at = <读到的值>`，0 行即已被别的实例接手，删消息退出）；每个阶段落库的事务先锁本行、核对本列仍是自己写的值，核对不上即丢弃结果退出——延长调用连续失败、老进程其实还活着的少见情况。重跑次数不另存，看 `ApproximateReceiveCount`；收满队列上限（3）的那次仍没跑完（进程被杀或代码抛异常），消费者不做特殊处理：打 ERROR 日志、不删消息，消息进死信，本行停在处理中、不进列表，见下「卡死兜底」。大模型最终失败不在此列：那是跑完了、结果为失败，按设计 6.11 作废（设计 1.10、第八章 #30 的 `processing_attempts` / 心跳都不存） | 1.10、第八章 #30 |
| `extraction_status` | VARCHAR(16) | 是 | — | 最近一次提取任务的状态：`RUNNING`（进行中）/ `SUCCEEDED`（成功）/ `VOIDED`（作废） | 9.5.1 |
| `extraction_trigger` | VARCHAR(24) | 是 | — | 该任务的发起方：`AUTO`（首轮自动提取）/ `AUTO_ROUTE`（公司增改后自动路由）/ `START_EXTRACTION`（管理员点 Start Extraction，含改判前补跑 P1）——作废后都置待识别（Start Extraction 也是：旧内容在点击时已下线，用户决定 2026-10-26），审计按它区分触发方式 | 6.11 |
| `extraction_started_at` | TIMESTAMPTZ | 是 | — | 最近一次提取开始时间。非首轮的提取（Start Extraction、自动路由、改判前补跑 P1）被打断后没有重投接手（自动路由的消息重投时，这场会已有进行中的提取、不再匹配），靠定时清扫判超时：`extraction_status = RUNNING` 且本列距今超过卡死时限（配置，默认 1 小时），按该次提取作废（条件更新 `WHERE extraction_status = 'RUNNING' AND extraction_started_at = <扫到的值>`，作废规则同设计 6.11），Start Extraction 恢复可点（见下「卡死兜底」） | 6.11、第八章 #30 |
| `identification_result` | VARCHAR(32) | 是 | — | 识别阶段的结果，识别跑完后写：`NORMAL` / `NO_SUBSTANCE`（会议 Invalid，不进列表：转录为空——识别第一步程序检查，没有句子即判，不调 P1；或 P1 判无实质内容，如只有寒暄、没录上几句。Java 的 Raw Data 只读它显示 `Invalid`）/ `QUALITY_CHECK_FAILED`（P1 最终失败：待识别；自动路由跳过）/ `ATTENDEE_INFERENCE_FAILED`（P8 最终失败：待识别）。同时出现时按 `NO_SUBSTANCE` > `QUALITY_CHECK_FAILED` > `ATTENDEE_INFERENCE_FAILED` 只记一个，被盖掉的失败仍记在 `IDENTIFY` 审计。设计 9.5.9 的 `p1_status` / `p8_status` 合并为本列；P1 有没有做公司识别不再记，改判为 GS 内部 / Partner 时一律补跑 P1（本方案，调整设计 9.9.2 的「只做质量判断的才补跑」） | 6.4、6.11、6.13、9.3.4、9.4.2、9.9.2、9.9.3 |
| `current_extraction_input` | JSONB | 是 | — | 当前线上内容提取时用的输入：类型、保留的公司、每位参会人的身份 / 组织 / 公司 / 专长标签、说话人对到谁（示例见 code-examples 第 3 节）；**不存提取出的内容**（内容在中间表）。只用来判断「参会人有没有改过」：登记与指定说话人会立刻写进识别结果，拿最新识别结果和它比，有差异则 Start Extraction 激活（例外规则见设计 9.9.1）。提取成功时写入（首轮自动提取、自动路由、Start Extraction），改 Unknown 应用后清空。被推测者的专长标签刷新时（专家确认框或 `Edit external party` 保存后的名册同步 API-28 刷新 P2），只把此人的专长标签同步写入、其余不动（本列为空时不写）：否则 P2 刷新后一比就成了参会人改动、激活 Start Extraction，与设计 9.9.1「被推测者的标签改动不算参会人改动」冲突；在刷新时同步而不是补抽成功后，补抽失败也不会激活。同时改了角色等其他字段的仍比得出差异、照常激活 | 9.5.1、9.9.1 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_meeting_state (id)`
- **防过期提交用 `updated_at`**（设计 9.6.5「并发」，本方案不另设 `lock_version`）：详情页加载时返回 `updated_at`，写操作带回它做条件更新 `WHERE id = ? AND updated_at = ?`，0 行即页面已过期、拒绝并提示刷新。凡会改变本场可提交内容的写入都要更新本行（触发器随之刷新 `updated_at`）：应用、Start Extraction、矩阵行内 Save、登记或指定说话人、名册同步（API-28），以及系统侧的自动路由、提取完成、补抽返回；只改子表的操作也要同时「碰」一下本行。代码里注明这是乐观锁
- 唯一 `uk_ai_ff_meeting_state_meeting (meeting_id)` —— 一对一；投递重复时幂等
- 索引
  - `idx_ai_ff_meeting_state_list (organization_id, started_at DESC) WHERE meeting_status IS NOT NULL` —— Summary Records 列表默认排序、时间筛选
  - `idx_ai_ff_meeting_state_status (organization_id, meeting_status, meeting_type)` —— 按状态、类型筛选；Tab 红点计数；自动路由找「待识别的 GS → 创始人」
- **卡死兜底**（用户决定 2026-10-27，7 #Q12、#Q13）：首轮被打断由 SQS 重投接手（`processing_started_at`）；其余五类交给定时清扫（单独功能，Fireflies 开发完成后设计、与本功能一起上线）：① 连续 3 次没跑完、停在处理中的首轮会议（按 `processing_started_at` 距今超过卡死时限判）；② 已投递却没有本行的会议（`dispatched_at` 距今超过同一时限；首次连接回溯 14 天、消息积压时可能误报，误报的重投 Python 按会议去重）；③ 非首轮的提取任务卡在 `RUNNING`（`extraction_started_at`）；④ 证词补抽卡在 `RUNNING`（P2 `testimony_backfill_status`）；⑤ 投影卡在 `PENDING` 的中间表行（P7 `projection_status = PENDING` 且 `updated_at` 距今超过卡死时限，含摘要行的「只替换摘要」；清扫按失败处理并按该行当前状态重推，7 #Q30）。③④⑤ 在 Python 进程内执行，被打断后没有重投，只能靠超时解锁。Python 没有定时任务框架，清扫与 AI 财务提取任务卡在 `PROCESSING` 的同类问题一起设计，五类的查询见 code-examples 第 4 节。本功能不做「打开详情页、点按钮时判超时」（用户决定 2026-10-27：清扫一起上线，不必先写再下线）
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
| `role` | VARCHAR(32) | 否 | `'UNIDENTIFIED'` | 身份：`GS_STAFF`（GS 人员）/ `FOUNDER`（创始人）/ `LP` / `STRATEGIC_PARTNER`（战略合作方）/ `EXIT_PARTNER`（退出合作方）/ `OTHER`（其他）/ `UNIDENTIFIED`（未识别）。LG 平台用户（识别 ②）在名册有会议当日生效的记录时以记录的角色为准，优先于平台账号推出的角色，名册同步（API-28）也按它刷新；改离 Founder 后不再按平台账号挂到被投公司（7 #Q47） | 1.9 |
| `match_step` | VARCHAR(24) | 是 | — | 命中识别链的哪一步：`GS_DOMAIN`（① GS 邮箱域名）/ `LG_USER_EMAIL`（② LG 用户完整邮箱）/ `LG_USER_DOMAIN`（③ 公司 Team 域名）/ `CHEAT_SHEET_EMAIL`（④ 名册邮箱）/ `P8`（⑥ 姓名候选经 P8 核对、⑦ P8 推断）/ `MANUAL`（人工登记、关联或指定）；未识别为空 | 1.9、9.5.9 |
| `lg_user_id` | VARCHAR(36) | 是 | — | ② 命中的 LG 用户 | 1.9 |
| `company_id` | VARCHAR(36) | 是 | — | 公司方参会人所属公司（② / ③ 得出）；名册或 P8 的 Founder 为空 | 2.1 |
| `cheat_sheet_name` | VARCHAR(255) | 是 | — | Cheat Sheet 引用键（姓名） | 9.7.1 |
| `cheat_sheet_id` | VARCHAR(36) | 是 | — | 识别时按会议日期取到的那一行 `ff_cheat_sheet.id`（一行即一个版本），留痕，名册同步（API-28）时随之刷新；P8 输出的 `registry_id` 即它 | 9.5.9 |
| `display_name` | VARCHAR(255) | 是 | — | 胶囊显示名 | 9.5.5 |
| `organization` | VARCHAR(255) | 是 | — | 胶囊显示的组织 | 9.5.5 |
| `expertise_tags` | JSONB | 否 | `'[]'` | 补充识别：会议日期生效版本的专长标签；登记时由 API-25 就地刷新，Edit external party 与专家确认框保存后由名册同步（API-28）按名册当日生效版本刷新（徽标随之显示 `Expert`），被推测者的同时同步进 P1 `current_extraction_input`。提取时本列与 `cheat_sheet_id` 即建议标签的扣除基准 T1：建议标签 = 大模型标签 − T1 − 拒绝名单（J6），不另加字段（7 #Q44） | 1.11 |
| `ai_inferred_identity` | JSONB | 是 | — | AI（P8）推断的此人身份：`{confidence, evidence, name, role, organization, registry_id}`（P8 原样输出，`registry_id` 即 `ff_cheat_sheet.id`），不采纳的也存 | 6.13 |
| `testimony_backfill_status` | VARCHAR(16) | 是 | — | 被推测者的证词补抽状态：`RUNNING`（补抽中）/ `FAILED`（补抽失败，可重试）；空 = 没有补抽或已成功。补抽在 Python 进程内执行，被打断后没有重投，靠定时清扫判超时：`RUNNING` 且本行 `updated_at` 距今超过卡死时限，置 `FAILED`（条件更新），页面出现 Retry。不另设开始时间列：置 `RUNNING` 时触发器刷新 `updated_at`，期间本行别的改动只会推迟判定（见 P1「卡死兜底」） | 2.5 |
| `testimony_tags` | JSONB | 是 | — | 上次为此人抽证词时所用的专长标签集合（首次提取与每次补抽成功时写入；标签清空、证词行软删时写 `[]`；空 = 从没为他抽过证词）。补抽前与他名册里会议当日生效的标签比对：GS → 创始人相同即不补抽；GS → LP / Partner 的 P5 不带标签，只在从没抽过且现在有标签时补抽（7 #Q35） | 2.5 |
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
| `status` | VARCHAR(16) | 否 | `'PENDING'` | 处理状态：`PENDING`（未处理）/ `ACCEPTED`（同意：在此人会议日期生效的名册记录里）/ `DECLINED`（驳回：在拒绝名单 J6 里）/ `WITHDRAWN`（撤下：重新提取或改 Unknown 时仍未处理）；由名册同步（API-28）按库里现状写（7 #Q44） | 9.5.10 |
| `auto_resolved` | BOOLEAN | 否 | `false` | 自动消解：打开确认框前，该建议标签已在此人名册会议当天那一版里、或已在拒绝名单里（别场会议处理过，或在 Cheat Sheet 里直接加过；拒绝名单按人查），即算自动消解，由名册同步（API-28）落库为已同意 / 已驳回（用户决定 2026-10-27，7 #Q22；7 #Q44） | 9.5.6 |
| `decided_by` | VARCHAR(36) | 是 | — | 处理人：保存后触发同步（API-28）的管理员（自动消解的同样记他） | 9.5.6 |
| `decided_at` | TIMESTAMPTZ | 是 | — | 处理时间 | 9.5.6 |
| `deleted` | BOOLEAN | 否 | `false` | 软删 | 9.5.10 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_expert_candidate (id)`
- 唯一 `uk_ai_ff_expert_candidate_live (meeting_id, participant_id, tag) WHERE deleted = FALSE`
- 索引 `idx_ai_ff_expert_candidate_pending_tag (organization_id, tag) WHERE status = 'PENDING' AND deleted = FALSE` —— Java 删标签前查「正被未处理标记引用」
- 状态流转：`PENDING → ACCEPTED / DECLINED`（保存后的名册同步 API-28，含自动消解的标签；既不在记录也不在拒绝名单的保持 `PENDING`）；`PENDING → WITHDRAWN`（重新提取或改 Unknown 应用时仍未处理的，随旧产物软删）；会议状态只看未软删的 `PENDING` 行

#### P6（已改为 Java 表）

拒绝名单改由 Java 写，见 J6 `ff_expert_rejection`（7 #Q45）；编号空出、不复用。

#### P7 `ai_ff_routing_row`

一行 = 一个 Authorize 格（设计 9.6.6）。摘要与知识库正文各占一行、各自编辑与授权（用户决定 2026-10-27，7 #Q9），但合投一条知识库条目：两行共用该条目的 `ai_rag_entry_id` / `file_id`，摘要跟着正文走（用户决定 2026-10-28，7 #Q42）；跨公司与证词一行投一条条目。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `meeting_started_at` | TIMESTAMPTZ | 否 | — | 冗余会议开始时间（同 P1 `started_at`）：Goldie Base 两个新 Tab 按会议时间倒序、按会议日期筛选（用户决定 2026-10-27，7 #Q23） | 9.11.4 |
| `meeting_title` | VARCHAR(512) | 是 | — | 冗余会议标题（同 P1 `title`）：两个新 Tab 的关键词同时匹配会议名称（7 #Q23） | 9.11.4 |
| `destination` | VARCHAR(24) | 否 | — | 去向：`KB_APP`（公司端知识库，GS → 创始人）/ `KB_ADMIN`（管理端公司层知识库，GS 内部与 Partner）/ `FUND_LEVEL`（设计的「机构层」：GS → LP 的基金层摘要 + 正文，`company_id` 为空）/ `CROSS_COMPANY`（跨公司内容）/ `TESTIMONY_ANON`（证词匿名版）/ `TESTIMONY_SIGNED`（证词署名版）；决定投影到哪个空间，组合键见 1.4 | 9.6.6 |
| `output_type` | VARCHAR(16) | 否 | — | 产出类型：`SUMMARY`（摘要，1a / 1b）/ `KB`（知识库正文：Founder KB / Portfolio KB）/ `CROSS_COMPANY`（跨公司内容）/ `TESTIMONY`（专家证词，两版各一行）。三类知识库去向下同一（去向, 公司）摘要一行、正文一行，矩阵里两行各一个 Authorize（同设计稿，用户决定 2026-10-27，7 #Q9），合投一条条目：正文行的内容为条目正文，摘要行的内容为条目的 `summary`（用户决定 2026-10-28，7 #Q42） | 9.6.2 |
| `company_id` | VARCHAR(36) | 是 | — | `KB_APP` / `KB_ADMIN` 必填 | 6.11 步骤 7 |
| `content` | TEXT | 否 | `''` | 内容：摘要行为摘要（≤150 个英文单词）；知识库行为 markdown 正文（原始转录链接在投影时附加，不存）；跨公司为 `statement`；证词为正文，不含来源行。设计 9.6.6 的 `summary` 列不建：摘要单独成行后同样存这里 | 1.3、9.6.3 |
| `category` | VARCHAR(64) | 是 | — | 仅跨公司与证词：P6 的四类之一 / P5 的证词类别；只用于投影时拼条目标题（`Cross-company insight · <category>`、`Expert testimony · <category>`，设计 6.11 步骤 8），页面不显示 | 6.8、6.9、6.11 |
| `source_timestamp` | VARCHAR(8) | 是 | — | 仅跨公司与证词：内容出自会议的时间点 `hh:mm:ss`（P6 / P5 输出，格式不合法或超出会议时长时置空）。用于排序：Content Routing Matrix 里组内按「发言人 + 时间点」排，同一条证词的署名、匿名两版相邻，跨公司内容按会上先后；Goldie Base 两个新 Tab 的会议卡片内同样按它排。Content Routing Matrix 里只读显示，供管理员回查原文（7 #Q26）；Goldie Base 不显示，也不随内容投影 | 9.6.2 |
| `speaker_participant_id` | VARCHAR(36) | 是 | — | 仅证词：证词发言人对应的参会人（P2 `id`），写入时由 P5 输出的 `speaker_ref` 经说话人绑定解析而来 | 9.6.6 |
| `authorized` | BOOLEAN | 否 | `false` | 是否授权放行（矩阵的 Authorize 勾选）；取消勾选只改它、内容保留 | 9.6.4 |
| `in_playbook` | BOOLEAN | 否 | `false` | Play candidate：只把本条标记为 playbook 候选，不影响授权、投影与召回，候选由后续另一任务处理（用户确认 2026-10-27，7 #Q8）；证词只打在署名行，匿名行恒为 `false` | 9.11.6 |
| `fund_tag_ids` | JSONB | 是 | — | 基金标签：管理端 Knowledge Base Tab 手动选的 Portfolio（`company_group` id 数组），只用于 `KB` 行（Knowledge Base Tab 才有基金标签）；空 = 没选过，Portfolio 列按「公司所属 Portfolio → 会议 Portfolio 标记」回退 | 9.11.2 |
| `file_id` | VARCHAR(36) | 是 | — | 当前在线投影的合成 id，不指向真实文件（不是 Java `files.id`，也没有 S3 对象，7 #Q41）：每次投影生成一个，同时写进 RAG 条目、切片与登记行，即 `ai_file_registry.file_id`（ORM 主键）；RAG 条目经登记行的 `ai_rag_entry_id` 取，不另存（设计 9.6.6 的 `rag_entry_id` / `file_registry_id` 不建）。改内容时新条目写成功才换；下线完成后置空（重新勾选时按「`file_id` 为空且已授权 → 上线」推）。三类知识库去向的摘要行与正文行共用一个：正文行上线时生成，摘要写进在线条目时摘要行记同一个值（7 #Q42） | 1.2、1.6 |
| `projection_status` | VARCHAR(16) | 否 | `'NONE'` | 投影状态：`NONE`（未投影或已下线）/ `PENDING`（投影中，含重试）/ `ONLINE`（已上线）/ `FAILED`（重试用尽仍失败）。摘要行在摘要写入在线条目时为 `ONLINE`，正文不在线或摘要未授权时为 `NONE`，只替换摘要进行中（含重试）为 `PENDING`、重试用尽为 `FAILED`（审计 `PROJECTION_FAILED` 的动作记 `SUMMARY_UPDATE`）（7 #Q42） | 1.6 |
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
- **摘要行与知识库行合投一条条目**（用户决定 2026-10-28，7 #Q42，调整 7 #Q9 的「分开投影」；矩阵仍是两行、各一个 Authorize）
  - 每个（去向, 公司）只投 1 条 RAG 条目：TEXT 来源，`content_text` 为正文行投影时生成的 markdown（7 #Q41），`summary` 列为摘要行内容（摘要行已授权时写，否则为空），不经大模型重写；登记行 `business_type = FIREFLIES`。正文进 Knowledge Base Tab，`summary` 非空时进 Memory Tab，两者都进 Goldie 召回
  - 摘要跟着正文走：正文行未授权或已软删时条目不上线，摘要行的授权不生效（前端把摘要的勾选框置灰，并随正文一起取消）。两行共用条目的 `ai_rag_entry_id` / `file_id`，摘要行在摘要写入在线条目时为 `ONLINE`
  - 摘要向量：`summary` 非空时整段建一条 `chunk_kind=summary` 的向量（不拆分），用本行内容、不调系统摘要器；为空不建
  - 只改摘要（摘要行 Save，或勾选、取消摘要授权）且正文在线时：只替换条目的 `summary` 列与那条摘要向量，不重新向量化正文、不换 `file_id`。改正文仍是「写新条目、成功后软删旧条目」，新条目带上当前生效的摘要
  - 按 `file_id` 反查本表（Knowledge Base Tab 的 Source 列、基金标签）时，同一 `file_id` 有摘要、正文两行，取正文行（`output_type = KB`）
  - 取舍：与现有知识库文件同一模型（登记表一个值，Memory 页与召回走同一套机制）；去掉摘要独立成条的两个毛病——与正文被重复召回、占掉名额，正文条目摘要为空、`get_file_summary` 取不到。代价是不能只给 Memory 页摘要、不给知识库正文
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
  - 摘要行同样按上述推法，只是「上线 / 改内容」是把本行内容写进正文行在线的条目（只换 `summary` 与摘要向量），「下线」是清空它；正文行不在线时直接置 `NONE`，等正文上线时随之写入（7 #Q42）

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
  - `EXPERT_CONFIRM` / `EXPERT_DECLINE` → P5 的 `status` / `decided_by` / `decided_at` / `auto_resolved` / `claims`，J6 拒绝名单，Cheat Sheet 来源 `From FF Summary Records`
  - `REGISTRY_IMPORT` → `ff_cheat_sheet` 的 `source` / `source_meeting_id` / `created_by`
  - `SPEAKER_ASSIGN` → P3 `bind_source = MANUAL_ASSIGN` + `updated_by` / `updated_at`（只针对未配上的说话人，改前值恒为「未配上」）
  - `PORTFOLIO_MARK`（需求「仅为标记」）、`PLAYBOOK_TOGGLE`（候选标记）→ 只留当前值与 `updated_by`，不留历史；`DRAFT_DISCARD` 随草稿取消不再存在
- 重新提取是谁发起的，查这场会最近一次 Start Extraction 的 `EXTRACT` 记录（`triggered_by`、`created_at`），状态表不存发起人与时间
- 索引 `idx_ai_ff_audit_log_org_created (organization_id, created_at DESC)`、`idx_ai_ff_audit_log_meeting (meeting_id)` —— 按租户、按会议追溯（MVP 无查看页，9.10.3）

#### X1 `ai_file_registry`（改造）

| 变更 | 内容 | 存量数据 |
|---|---|---|
| `business_type` 新取值 `FIREFLIES`（三类知识库去向的条目：正文 + 摘要）/ `FIREFLIES_TESTIMONY`（证词两版）/ `FIREFLIES_CROSS_COMPANY`（跨公司）（7 #Q42） | 列无 CHECK，只更新列注释 | 无 |

- 不加列：登记表只管文件登记，基金标签放 P7 的 `fund_tag_ids`（用户决定 2026-10-26）
- 两个页面都只认 `FIREFLIES`：Knowledge Base Tab 的查询纳入 `FIREFLIES`；Memory Tab 取 `KNOWLEDGE_BASE` 与 `FIREFLIES` 中摘要非空的条目（管理端 `scope=fireflies` 只取 `FIREFLIES`）；证词与跨公司不进两个页面（设计第八章 #11，7 #Q42）
- 与中间表的关联：登记行的 `file_id` = P7 的 `file_id`，本表不加反向列；Fireflies 登记行必须写 `ai_rag_entry_id`（一个 `file_id` 一个条目），中间表靠它找到 RAG 条目
- Fireflies 登记行的 `file_id` 是投影时生成的合成 id，不指向真实文件：没有 Java `files` 行，也没有 S3 对象（7 #Q41）；登记行由投影写入（现有文本入库 `ingest_text` 不建登记行），文件名为条目标题加 `.md`，下载时按它现生成（API-35）

### 1.4 跨端读写、种子数据与配置

**跨端读的表**（表结构不依赖读法；两端共用同一套数据库账号，不另授权，7 #Q36）：

| 方向 | 表 | 用途 |
|---|---|---|
| Python 读 Java 的 Fireflies 表（6 张） | `ff_meeting_meta_info`、`ff_meeting_sentence`、`ff_cheat_sheet`、`ff_expertise_tag`、`ff_connection_configuration`（只读 `organization_id`、`email_domains` 两列，不含 key 密文）、`ff_expert_rejection` | 识别与提取输入；名册回溯；P7 标签字典；识别 ①；拒绝名单（识别前过滤、同步时判已驳回） |
| Python 读 LG 业务表（7 张） | `user`、`r_organization_user`、`company`、`r_organization_company`、`company_group`、`r_company_group`、`organization` | 识别 ②③、自动路由、`firm_profile`、Portfolio 显示 |
| Java 读 Python 的表（3 张） | `ai_ff_meeting_state.identification_result`、`ai_ff_expert_candidate`、`ai_ff_meeting_participant.email` | Raw Data 的 Invalid；标签删除校验；专家确认保存写拒绝名单时取本场邮箱（API-08） |

**跨端写**：无。会议页的名册编辑与专家确认由前端直调 Java（API-07 / 08，7 #Q44），Python 只在 Assign new external party 时经 API-06 新建（API-25，第八章 #31）；标签字典由前端直接调 Java（7 #Q19）；审计只有 Python 一张表（A4）。

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

三类知识库去向的摘要行与正文行合投该空间的一条条目，登记 `FIREFLIES`；证词两版登记 `FIREFLIES_TESTIMONY`，跨公司登记 `FIREFLIES_CROSS_COMPANY`（P7、X1，7 #Q42）。

**新配置项**（按实际落地更新，2026-10-28）

| 端 | 配置 | 默认 |
|---|---|---|
| Java | 环境变量 `FIREFLIES_KEY_SECRET`：API key 加密密钥（AES-256-GCM），Base64 编码的 32 字节，可用 `openssl rand -base64 32` 生成；漏配不影响启动，Link 与拉取时报错 | 无，必配 |
| Java | Nacos `cio.fireflies.sync.first-lookback-days`：首次连接（含换账号）的回溯天数 | 14 |
| Java | Nacos `cio.fireflies.sync.lookback-hours`：增量拉取从上次成功往前回看的小时数 | 72 |
| Java | Nacos `cio.fireflies.sync.disconnect-threshold`：连续非鉴权失败达到即转 `Disconnected`（本方案，设计 9.12 #1 待确认） | 3 |
| Java | Nacos `cio.fireflies.sync.pull-read-timeout-ms`：拉会议列表（一页 50 场，含逐句）的读超时，按实测再调 | 60000 |
| Java | Nacos `cio.fireflies.sync.sync-stale-minutes`：同步卡死时限（`sync_started_at` 超过即可被重新抢占，API-01 的 `syncing` 也按它判） | 60 |
| Java | 每日拉取 cron：写死在 `FixedScheduleTypeEnum.FirefliesDailyPull`（`cron(40 3 * * ? *)`，每日 03:40 UTC，7 #Q33），不可配，改时段要改枚举、随 Java 发版（7 #Q33） | 每日 03:40 UTC |
| Java | Link 校验 key 的读超时：写死，不可配 | 15 秒 |
| Python | `SQS_INFLIGHT_LIMIT_FIREFLIES`：每条 Fireflies 队列的在途消息上限（两条队列各自生效） | 2 |
| Python | `SQS_HEARTBEAT_INTERVAL_FIREFLIES`：处理中延长消息不可见时间的间隔（秒） | 120 |
| Python | `FIREFLIES_STUCK_TIMEOUT_MINUTES`：卡死时限（分钟），首轮停在处理中、非首轮提取 / 证词补抽停在 `RUNNING`、中间表行投影停在 `PENDING` 超过即视为中断，交定时清扫 | 60 |
| Python | `FIREFLIES_PROMPT_MAX_RETRIES`：每个提示词调用的最大重试次数，用尽即最终失败 | 3 |
| Python | `FIREFLIES_NGRAM_SIZE`：n-gram 近逐字的窗口（连续英文单词数，设计 1.5） | 8 |
| Python | `FIREFLIES_NGRAM_MATCH_RATIO`：一行的 n-gram 命中原文的比例达到即判近逐字、删整行（实施期按样本再调） | 0.5 |
| Python | `FIREFLIES_PROJECTION_MAX_ATTEMPTS`：投影（写 / 删 RAG 条目）失败的最大重试次数，用尽即投影失败 | 3 |

Java 的 5 项 Nacos 配置漏配时用上表默认值。Python 的 7 项记 `sql/migrations/env-vars/env-update.txt` 的 sprint122 段与 `.env_example`；两条队列共用现有的 `SQS_NAME_PREFIX`、`CIO_AWS_REGION` 等 SQS 全局变量，不另配。

### 1.5 迁移文件与执行顺序

| 端 | 文件 | 内容 | 执行时机 |
|---|---|---|---|
| Java | `deploy/upgrade_doc/sprint122/V1__ff_init.sql` | J1~J6 建表、索引、注释；存量组织补齐 5 项预置专长标签 | **先于 Java 发版**（ddl-auto 会自动建表但不建索引） |
| Python | `sql/migrations/business/V034__sprint122_fireflies_init.sql` | P1~P5、P7、P8 建表、索引、触发器、注释；X1 只改 `business_type` 注释，`ai_rag_business_association.business_type` 注释补两个新空间业务类型 | **先于 Python 与 Java 发版** |

两份迁移文件之间互不依赖，但 Java 发版依赖 V034：Java 的 Raw Data 列表（API-15 每页读 P1 `identification_result`）、标签删除校验（API-12 / 14 读 P5）与专家确认保存（API-08 读 P2）直读 Python 的 `ai_ff_meeting_state` / `ai_ff_expert_candidate` / `ai_ff_meeting_participant`，V034 没执行时直接报错，所以 V034 要先于 Java 发版执行；反过来 Python 直读 J1~J6（拒绝名单 J6 在识别前过滤与同步时都要读），V1 也要先于 Python 发版执行。不另做数据库授权：Python 与 Java 现用同一套数据库账号，单独授权方案一直没实行（7 #Q36）。DDL 见 [code-examples.md](./code-examples.md)。

## 2. 页面清单

页面编号用 `PG-`，避免与 Python 表 P1~P8 混淆。路由放在 web 的 `config/routes.ts`；两个 Tab 容器的当前 Tab 记在 `?tab=`（本功能新定：web 现有页面多用 `?active=`，但它会改写公司端顶栏高亮，`BasicLayout.tsx:130,469-499`，PG-05 在 `/askGoldie` 下会因此丢掉 Ask Goldie 的高亮）。设计稿的路由（`/`、`/meetings/$id` 等）只作对照。角色：**PGM / SA** = 管理端，且 superAdmin 或角色菜单含 `seeAllPortfolio`；**PM** = 管理端其余用户；**公司端** = Company Admin / Company User。前端不自己判角色，用后端返回的标志位（API-19 及各接口的按行标志，设计 9.1）。

| 编号 | 页面 | 路由 | 入口 | 可访问角色 | 类型 | 新增 / 改造 | 需求条目 |
|---|---|---|---|---|---|---|---|
| PG-01 | Fireflies Management（Tab 容器） | `/fireflies?tab=summaryRecords\|configuration\|cheatSheet\|rawData&org=<组织 id>`（`org` 只在切换过租户时出现） | 两端都在头像下拉的 Fireflies Management（管理端按设计稿 `app-header.tsx:80-94`；公司端不受订阅状态限制，7 #Q14、#Q15）；PG-02 / PG-03 / PG-04 面包屑回到对应 Tab | PGM / SA（四个 Tab）；公司端（只显示 Raw Data Tab）；PM 进入显示无权限 | 容器 | 新增 | 9.1、9.3.6、第八章 #28、#32 |
| PG-01a | └ Summary Records Tab（默认） | `?tab=summaryRecords` | Tab 切换 | PGM / SA | 列表 | 新增 | 9.4 |
| PG-01b | └ Configuration Tab | `?tab=configuration` | Tab 切换 | PGM / SA | 表单 | 新增 | 9.2 |
| PG-01b1 | 　└ Remove API key 确认框 | — | Configuration 的 Remove | PGM / SA | 弹窗 | 新增 | 9.2.5 |
| PG-01c | └ Cheat Sheet Tab（名册列表 + 底部 Email Domain 块） | `?tab=cheatSheet` | Tab 切换 | PGM / SA | 列表 + 行内编辑 | 新增 | 9.7、9.7.7 |
| PG-01c1 | 　└ Add / Edit external party 弹窗（新增时另有 Confirm submission 二次确认；新增时姓名失焦查重，重名自动加后缀，7 #Q46） | — | Add external party / 行内 Edit | PGM / SA | 弹窗（表单） | 新增 | 9.7.4、9.7.5 |
| PG-01c2 | 　└ 专长标签下拉（选、`Add "<输入值>"`、删未用过的） | — | PG-01c1、PG-02a、PG-02b、PG-02c 的 Expertise tags 字段 | PGM / SA | 组件 | 新增 | 9.8 |
| PG-01d | └ Raw Data Tab | `?tab=rawData` | Tab 切换；公司端进入 PG-01 即此 Tab | PGM / SA；公司端（只列本人受邀的会议） | 列表 | 新增 | 9.3.3、9.3.4、9.3.6 |
| PG-02 | 会议 Review 详情（含 Content Routing Matrix） | `/fireflies/meetings/:meetingId` | PG-01a 的会议名 / Review；PG-05c、PG-05d 的会议名（仅 PGM / SA 可点） | PGM / SA（按会议所属租户） | 详情 + 表单 | 新增 | 9.5、9.6、9.9 |
| PG-02a | └ Assign new external party 弹窗（含 Confirm submission；姓名失焦查重，7 #Q46） | — | 点未识别、AI 推断未入册、按域名判出未入册的参会人；未对上说话人的「登记进名册」 | PGM / SA | 弹窗（表单） | 新增 | 9.5.5、9.5.7 |
| PG-02b | └ Edit external party 弹窗（前端直调 Java 保存一条完整记录，关窗后同步本场，7 #Q44） | — | 点名册中已有的外部人 | PGM / SA | 弹窗（表单） | 新增 | 9.5.5、9.5.7 |
| PG-02c | └ Possible expert 确认框（建议标签预填进标签栏，留下即同意、删掉即驳回；前端直调 Java 保存，关窗后同步本场，7 #Q44、#Q45） | — | 点带 `Possible expert` 的参会人 | PGM / SA | 弹窗（推测依据 + 表单） | 新增 | 9.5.6 |
| PG-02d | └ 指定说话人（未对上的说话人 → 本场某位参会人） | — | 点未对上的说话人 | PGM / SA | 弹窗（设计稿未画） | 新增 | 9.5.5 |
| PG-02e | └ 行内 Save 的清洗回显 | — | 行内 Save 返回清洗结果时 | PGM / SA | 弹窗（设计稿未画） | 新增 | 9.6.3 |
| PG-02f | └ 改为 Unknown 的二次确认 | — | 类型为 Unknown 时点 Confirm & Apply | PGM / SA | 确认框（本方案） | 新增 | 9.9.2 |
| PG-03 | 原文页 | `/fireflies/transcripts/:meetingId` | PG-01d 的 Raw transcript；PG-05a 中 Source = Fireflies 且可点的行 | PGM / SA；公司端（本人受邀的会议） | 详情（只读，整篇渲染、后台续加载） | 新增 | 9.3.5、9.3.6 |
| PG-04 | 名册 Role History | `/fireflies/cheat-sheet/:id/history`（`:id` 为此人任一版本行的 id） | PG-01c 的 History | PGM / SA | 列表（只读） | 新增 | 9.7.6 |
| PG-05 | Goldie Base（Tab 容器） | `/askGoldie/goldieBase?tab=knowledgeBase\|memorySettings\|crossCompany\|expertTestimony`（用户决定 2026-10-27，7 #Q16） | Ask Goldie 侧栏 / 手机端底栏的 Goldie Base 入口；旧地址 `/knowledgeBase`、`/memorySettings` 重定向到对应 Tab | 两端，按 Tab 区分 | 容器 | 新增（由两页合并） | 9.11.1、第八章 #17 |
| PG-05a | └ Knowledge Base Tab | `?tab=knowledgeBase`（默认） | Tab 切换 | 两端（原业务不变） | 列表 | 改造（原 `KnowledgeBasePage`） | 9.11.2、第八章 #11、#12、#18 |
| PG-05a1 | 　└ 基金标签选择（行内下拉） | — | 管理端 Fireflies 知识库正文行的 Portfolio 列 | 管理端 PM / PGM / SA（看得到该行即可改） | 行内下拉 | 新增 | 9.11.2、第八章 #16 |
| PG-05b | └ Memory Settings Tab | `?tab=memorySettings` | Tab 切换 | 管理端；公司端 Company Admin | 列表 | 改造（原 `MemorySettingsPage`） | 9.11.3、第八章 #13、#19 |
| PG-05c | └ Cross company content Tab | `?tab=crossCompany` | Tab 切换 | 管理端 PM / PGM / SA | 卡片列表 | 新增 | 9.11.4、9.11.6 |
| PG-05d | └ Expert Testimony Tab | `?tab=expertTestimony` | Tab 切换 | 管理端 PM / PGM / SA | 卡片列表 | 新增 | 9.11.5、9.11.6 |

**入口与守卫**

- 管理端：头像下拉加一项（`BasicLayout.tsx` 的 `menuRight_SuperAdmin`，key 取 `fireflies` 时 `handleGSTMenuClick` 的默认分支即跳 `/fireflies`；ERL 先例；用户决定 2026-10-27，7 #Q14），`path` 与后台菜单 `/fireflies` 一致（1.4「种子数据」）
- 公司端：同样放头像下拉（用户决定 2026-10-27，7 #Q15），放在订阅条件之外（`BasicLayout.tsx:891` 的条件只管 Profile 与菜单项；Switch Companies 另有 `userCount > 1`，Logout 不受限）——看本人受邀会议的原文是权限规则、不是付费功能。所有公司端用户都显示，没有受邀会议的看到空列表；key 同样取 `fireflies`，走 `handleGSTMenuClick` 的默认分支跳 `/fireflies`（公司端只有 Raw Data 一个 Tab，不用带 `?tab=`）；手机端是同一个下拉组件。进 PG-01 只渲染 Raw Data Tab，不显示租户下拉
- `SecurityLayout`：`/fireflies` 与 `/fireflies/transcripts/*` 两端都要进，**不加管理端守卫**；`/fireflies/meetings/*`、`/fireflies/cheat-sheet/*` 加管理端守卫（仿 ERL `SecurityLayout.tsx:73-98`，取不到端类型按公司端拦截）。PM 直接打开 `/fireflies` 时按 API-19 的标志位显示无权限提示，不请求管理端接口；PM 的拦截与数据权限一律靠后端
- 切换租户：PG-01 页头组织树下拉，组织树根下有子组织才显示（同 ERL、Portfolio Companies），默认会话租户；SA 借此切到子租户查看（用户决定 2026-10-27，7 #Q17）。下沉 ERL 的 `OrganizationSelect` 到 `src/components/` 时，显示判定所在的 hook（`useErlOrganizationTree.ts:54`）、DTO 类型与 `subdata` → `children` 的归一函数一起搬。选中的租户记在 URL 的 `org` 上，PG-02 / PG-03 / PG-04 的面包屑把它带回；这三页不显示下拉，按会议（或名册行）所属租户执行，返回时 `org` 取该会议（或名册行）的租户（API-21、API-17、API-09 都返回 `organizationId`）
- Goldie Base：侧栏与手机端底栏现有的 Knowledge Base、Memory 两个入口按设计稿合并为一个 Goldie Base 入口（设计稿 `ask-goldie.tsx:80-89`；设计 9.11 交开发设计定）；管理端一律取组织树第一个叶子租户（`orgScope.ts` 的 `firstLeafOrgId`，与现有知识库一致），不提供切换（设计 9.11.1，7 #Q32）；公司端普通用户只有 Knowledge Base 一个 Tab 时不显示 Tab 栏（设计 9.11.1 交开发设计定）

**不在本期**：识别链的 HubSpot 一级（设计 1.9 ⑤，MVP 跳过，第十章 #25）；Ask Goldie 对话里展示 Fireflies 来源链接——需求与设计稿都没有，现有聊天也没有结构化来源（只靠正文 Markdown）。Goldie 召回改造（第八章 #7~#10）不改页面（用户决定 2026-10-27，7 #Q21）。

## 3. 接口清单

**通用约定**

| 项 | Java（`/api/web/fireflies/*`） | Python（`/api/ai/fireflies/*`） |
|---|---|---|
| 位置 | `web/fireflies/` 按规范分 DDD 四层，路径 kebab-case 复数，不照 ERL 的平铺包与驼峰单数（用户决定 2026-10-27，7 #Q18）；每租户只有一个连接，按单例资源用单数 `/connection`；网关 `StripPrefix=1`，Controller `@RequestMapping("/fireflies")` | 新模块 `source/fireflies/`（`interfaces/routes/` 按页面拆文件），包根懒导出 router，`main.py` include |
| 响应 | `Result<T>` = `{success, code, message, data}`；业务错误 HTTP 200 + `success:false`；参数校验失败 HTTP 422，响应体为 `ErrorResponse{message, errors}`，不是 `Result`；业务错误码见 3.6 | 同结构；业务错误 HTTP 200 + `success:false` + 数字码（同 memory，前端遇 ≥400 会弹全局横幅，码表见 3.6）；例外：改造的 file-registry 接口（API-33~36）沿用该模块现有的真实 HTTP 状态码（`_raise_business`） |
| 分页 | `page`（从 0 起）/ `size` / `sort`，返回 `PageResponse{totalElements, content}` | `page`（从 1 起）/ `pageSize`，返回 `{items, total}`；日期区间 `dateFrom` / `dateTo`，按会议业务日期、含两端（设计 9.3.3） |
| PGM / SA 判定 | `CompanyGroupService` 新增一个方法：管理端 &&（任一角色 superAdmin \|\| 菜单码 `seeAllPortfolio`），Fireflies 接口首行断言，同时供 API-19 用 | 经 API-19 的新字段判定（`lgpi_api/current_user_api.py` 跟着加字段）；`auth_token` 缺失时在调 Java 之前就拒绝 |
| 租户 | 除按 id 定位的接口外，各接口可选 `organizationId`：为空取会话租户；传了就按传入的组织执行，**先不校验调用者是否属于该组织**，信任前端传入（用户决定 2026-10-27，7 #Q17）；PGM / SA 角色照常校验。按 id 定位的接口（API-07、09、14、17、18）不收组织 id，按该行（名册行、标签行、会议）自身的租户执行，同样不校验；API-06、API-41（带 `sourceMeetingId` 时）与 API-08 由来源会议推出租户。公司端一律会话租户。`organizationId` 一律走 query 参数（3.6） | Summary Records 列表同左；API-32 从会议页调用时带 `meetingId`、由会议推出租户，从 Goldie Base 调用时带组织树首叶组织 id、信任传入（7 #Q32）；会议级接口（`/meetings/{meetingId}/*`、`/routing-rows/{rowId}/content`）不收组织 id，按会议所属租户执行，同样不校验；Goldie Base（含知识库、Memory 的机构层条目）同样信任前端传入的组织 id：管理端一律传组织树首个叶子，没传时回退会话租户（知识库、Memory 没传时不纳入机构层条目，沿用原口径）；会话租户的等值校验先不启用（用户决定 2026-10-28，7 #Q32） |
| 长任务 | Sync now 立即返回、异步拉取 | Start Extraction、证词补抽立即返回，前端轮询 API-21（线上 CloudFront 约 30 秒无响应即回 504） |
| 防过期提交 | — | 详情页的写接口都带 `updatedAt`（P1 乐观锁），0 行即提示刷新；凡改本场内容的写接口都要「碰」一下 P1 行（P1「防过期提交」）。例外：名册同步 API-28 不带 `updatedAt`，按库里现状算、可重复调用，照样「碰」行（7 #Q44） |

前端调 Python 走同源 `/api/ai/...`（开发代理 `config/proxy.ts:21`）。线上 `/api/ai` 怎么分流到 Python 在三个仓库里查不到：nginx 只有 `/api/web`、`/api/etl`（`nginx.prod.conf:163,176`），Java 网关只有 `/api/web/**`、`/web/**`（`cioaas-gateway.yml:27-39`）；`proxy.ts:19` 注释与 fileRegistry README 里「经 Java 网关转发」的说法已过时。应在 CloudFront / ALB 层，上线前与运维确认，不影响接口设计。

### 3.1 Java 接口

| 编号 | 方法 路径 | 功能 | 关键入参 | 关键出参 | 读写表 | 权限 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|---|---|---|---|
| API-01 | GET `/connection` | 连接状态 | `organizationId?` | `status`、`accountEmail`、`lastSuccessSyncAt`、`syncing`（`sync_started_at` 非空且未超过同步卡死时限，1.4）、`keyMask`（后 4 位，服务端拼好） | J1 读 | PGM / SA | PG-01b | 新增 |
| API-02 | POST `/connection/link` | 提交 key：调 Fireflies `user` 校验、加密落库；换账号按首次连接（9.2.6） | `apiKey`、`organizationId?` | 同 API-01；失败返回原因码（鉴权失败 / 网络不可达） | J1 写 | PGM / SA | PG-01b | 新增，见 3.6 |
| API-03 | POST `/connection/sync` | Sync now：条件更新抢占 `sync_started_at`，异步拉取（补投 → 拉列表 → 写原文 → 发 SQS），立即返回；正在同步、或没有 key（`UNCONNECTED`）时拒绝 | `organizationId?` | `syncing` | J1 写；J2 / J3 写；发 SQS | PGM / SA | PG-01b | 新增，见 3.6 |
| API-04 | POST `/connection/remove` | 清空密文、回 `UNCONNECTED` | `organizationId?` | 同 API-01 | J1 写 | PGM / SA | PG-01b1 | 新增 |
| API-05 | GET `/cheat-sheets` | 名册列表：每人取当前状态那一版（9.7.1），带逾期待复核标记 | `keyword`、`role`、`page`、`size`、`organizationId?` | `content[{id, name, emails, organization, role, expertiseTags, areaOfExpertise, validFrom, validTo, source, needsReview}]`、`totalElements`、`overdueCount` | J4 读 | PGM / SA | PG-01c | 新增，见 3.6 |
| API-06 | POST `/cheat-sheets` | 新建人员（第一版）；租户内重名（忽略大小写）不拒绝，姓名自动加数字后缀，返回最终姓名（7 #Q46）；填的邮箱已登记在名册别的条目里时拒绝（7 #Q49）；带 `sourceMeetingId` 时有效期必须包含会议日期（7 #Q44） | `name`、`emails`、`organization`、`role`、`expertiseTags`、`areaOfExpertise`、`validFrom`、`validTo`、`sourceMeetingId?`、`organizationId?` | 新行（含最终姓名与 `id`） | J4 写（有 `sourceMeetingId` 记 `FF_SUMMARY_RECORDS` 与 `source_meeting_id`、租户由该会议推出，否则 `MANUAL`）；J2 读（推租户、取会议日期） | PGM / SA | PG-01c1；Python 经 API-25 调用 | 新增，见 3.6 |
| API-07 | PUT `/cheat-sheets/{id}` | 编辑：一律按弹框追加一条完整新版本（9.7.1），不改旧行（7 #Q44）。不带 `sourceMeetingId`（Cheat Sheet 页）：什么都没改时只在当前状态那一行记复核（`reviewed_*`，9.7.5）；带 `sourceMeetingId`（会议页 Edit external party，`{id}` 为 API-21 返回的 `versionId`）：新行记来源，有效期必须包含会议日期，与 `{id}` 那一版相比没有任何改动时不写、也不记复核 | 同 API-06（无 `name`、`organizationId`） | 新行 id；或 `reviewed: true` | J4 写（带 `sourceMeetingId` 的记 `FF_SUMMARY_RECORDS` 与 `source_meeting_id`）；J2 读（取会议日期） | PGM / SA | PG-01c1、PG-02b（前端直调） | 新增，见 3.6 |
| API-08 | POST `/cheat-sheets/expert-confirmations` | 专家确认保存（7 #Q44、#Q45），一个事务：有 `entry` 时，已在册的按 API-07 规则以 `baseVersionId` 为底追加一条完整新版本（没有改动不写），未登记的按 API-06 规则新建（重名加后缀，邮箱已登记在名册别的条目里时拒绝，7 #Q49）；写拒绝名单 J6：驳回 = `suggestedTags` − 保存后的 Expertise tags（`entry` 为空时全部算驳回），邮箱取 P2 该参会人的本场邮箱；有效期必须包含会议日期；租户由 `sourceMeetingId` 推出 | `sourceMeetingId`、`participantId`、`suggestedTags`（本次打开时的建议标签）、`entry?`（登记字段同 API-06；建议标签全删且未登记时为空）、`baseVersionId?`（已在册时为预填的 T2 id，未登记为空） | 最终姓名、写入的版本 id | J4 写（新行记 `FF_SUMMARY_RECORDS` 与 `source_meeting_id`）；J6 写；J2 读（推租户、取会议日期）；P2 读（本场邮箱） | PGM / SA | PG-02c（前端直调） | 新增（7 #Q44 改造），见 3.6 |
| API-09 | GET `/cheat-sheets/{id}/history` | 此人全部版本，按 `valid_from`、`updated_at` 倒序 | — | `name`、`organizationId`、`rows[{…快照字段, updatedBy, updatedAt}]`（系统写入的显示为 `System (<fireflies_id> import)`） | J4 读；J2 取 `fireflies_id` | PGM / SA | PG-04 | 新增，见 3.6 |
| API-10 | GET `/email-domains` | 本租户邮箱域名 | `organizationId?` | `domains[]` | J1 读 | PGM / SA | PG-01c | 新增，见 3.6 |
| API-11 | PUT `/email-domains` | 整份提交（增、改、删都走它）：逐个去 `@`、转小写，校验格式、公共邮箱域名与重复；没有连接行时先建一行（`UNCONNECTED`）；应用日志记改前、改后两份列表（用户决定 2026-10-27，7 #Q22） | `domains[]`、`organizationId?` | `domains[]` | J1 写 | PGM / SA | PG-01c | 新增，见 3.6 |
| API-12 | GET `/expertise-tags` | 标签字典，按 `sort_no`；每项带能否删除 | `organizationId?` | `[{id, name, preset, deletable}]` | J5 读；J4（任一版本用过）、P5（未处理标记引用）读 | PGM / SA | PG-01c2 | 新增 |
| API-13 | POST `/expertise-tags` | 新增：不区分大小写重名拒绝，`sort_no` 追加到末尾 | `name`、`organizationId?` | 新标签 | J5 写 | PGM / SA | PG-01c2 | 新增，见 3.6 |
| API-14 | DELETE `/expertise-tags/{id}` | 删除：预置的、名册任一版本用过的、被未处理专家标记引用的拒绝 | — | — | J5 删；J4、P5 读 | PGM / SA | PG-01c2 | 新增，见 3.6 |
| API-15 | GET `/meetings` | Raw Data 列表：服务端过滤后分页，默认会议时间倒序 | `keyword`（会议 id、标题、参会人）、`dateFrom`、`dateTo`（按会议日期，口径见 7 #Q25f）、`participants[]`（按显示名匹配出席记录姓名，或按邮箱匹配受邀邮箱）、`validity`（全部 / 只看 Invalid / 隐藏 Invalid）、`sort`（`firefliesId` / `title` / `date` / `time`（按一天中的时刻）/ `duration` / `participants`（按显示名串）/ `ingestedAt`，加 `,asc` / `,desc`；空值排最后，同值按 `firefliesId`）、`page`、`size`、`organizationId?`（按设计稿，用户决定 2026-10-27，7 #Q20） | `content[{id, firefliesId, title, startedAt, durationMinutes, participantNames, ingestedAt, invalid}]`（`participantNames` 取出席记录姓名，没有出席记录的回退受邀邮箱，9.3.3）、`totalElements` | J2 读；P1 `identification_result` 读 | PGM / SA：本租户；公司端：会话租户内、本人邮箱在 `participants` 中 | PG-01d | 新增，见 3.6 |
| API-16 | GET `/meetings/participant-options` | 参会人筛选项：调用者看得到的会议里参会人显示名去重（口径同 `participantNames`） | `organizationId?` | `[{value, label}]` | J2 读 | 同 API-15 | PG-01d | 新增，见 3.6 |
| API-17 | GET `/meetings/{id}` | 原文页页头 | — | `organizationId`、`title`、`startedAt`、`durationMinutes`、`participantNames`、`capturedAt` | J2 读 | PGM / SA：按会议所属租户执行，只校验角色（7 #Q17）；公司端：会话租户内且本人邮箱在 `participants` 中 | PG-03 | 新增，见 3.6 |
| API-18 | GET `/meetings/{id}/sentences` | 逐句分批（首批显示后前端在后台连续取完全篇，每批 500 句，7 #Q29） | `fromOrder`、`limit` | `[{order, speakerName, startTime, text}]`、`hasMore` | J3 读 | 同 API-17 | PG-03 | 新增，见 3.6 |
| API-19 | GET `/api/web/users/current` | 现有接口，`AuthenticatedUserDto` 加一个 PGM / SA 布尔字段（与 `superAdmin` 分开，字段名开发时定） | — | 新增字段 | 现有 | 登录 | PG-01、PG-05（标志位）；Python（判定 PGM / SA） | 改造（第八章 #22），见 3.6 |
| API-41 | GET `/cheat-sheets/name-check` | 姓名查重（7 #Q46）：按 API-06 的同一规则（忽略大小写）看租户内是否已有此姓名，给出保存时会用的姓名；只作提示，保存时 Java 再算一次、以保存时为准 | `name`、`organizationId?` 或 `sourceMeetingId?`（会议页由会议推出租户） | `exists`、`availableName`（不重名即原名，重名为加后缀后的姓名） | J4 读；J2 读（推租户） | PGM / SA | PG-01c1（新增）、PG-02a、PG-02c（姓名失焦） | 新增，见 3.6 |

### 3.2 Python 接口

| 编号 | 方法 路径 | 功能 | 关键入参 | 关键出参 | 读写表 | 权限 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|---|---|---|---|
| API-20 | GET `/summary-records` | Summary Records 列表（`processing_stage = DONE` 且非 Invalid），默认会议时间倒序；顺带返回 Tab 红点用的 Pending 数 | `keyword`（标题、会议 id、公司名）、`meetingType`、`status`（`PASSED` / `PENDING`，不按 Pending 原因筛，7 #Q25d）、`dateFrom`、`dateTo`、`page`、`pageSize`、`organizationId?` | `items[{meetingId, firefliesId, title, startedAt, durationMinutes, meetingType, companies[], status, pendingReasons}]`、`total`、`pendingCount`（Pending 会议总数，不受筛选影响） | P1、P4 读；LG `company` 读 | PGM / SA | PG-01、PG-01a | 新增 |
| API-21 | GET `/meetings/{meetingId}` | 会议详情，含矩阵；也是提取 / 补抽进行中的轮询接口 | — | 会议元信息、`organizationId`、`meetingType`、`status`、`pendingReasons`、待识别子原因（现算）、`extractionStatus`、`participantsChanged`（拿最新识别结果与 P1 `current_extraction_input` 比，该列为空（从未提取过、改 Unknown 应用后）时恒为 false；按 9.9.1 口径：只补邮箱、改 Area of expertise、被推测者只改专长标签不算，组织变化只对 Founder 与本场有证词行的人算；前端据此与页头未提交的改动一起判 Start Extraction 与 Confirm & Apply 的置灰）；`companies[{companyId, name, adopted, basisText}]`（含未采纳候选）、`portfolioIds`、GS → 创始人的只读 Portfolio；`participants[{id, displayName, organization, role, badges, aiEvidence, clickAction, testimonyBackfillStatus, registryForm, expertCandidates[{tag, claims[], resolvedAs}]}]`（`registryForm` 为登记 / 编辑弹框预填（7 #Q44）：已在册的为会议日期当天生效的那条记录 T2（覆盖会议日期、写入最晚的那条，9.7.2），有效期为 T2 原有效期，T2 里没有本场邮箱时补进（按姓名回退认出的人，或登记时按另填的邮箱认到名册已有记录的人，7 #Q49），另返回 `versionId`（T2 的 id，供 API-08 `baseVersionId` / API-07 `{id}`）；未入册者为已知值，含 P8 推断，From 默认会议日期、To 空；`aiEvidence` 为 AI inferred 悬停的依据；`resolvedAs` 现算：已在 T2 里为 `ACCEPTED`（弹框里按普通已有标签显示）、在拒绝名单 J6 为 `DECLINED`（不预填），否则为空（预填为建议标签），同步时写进 P5 `auto_resolved`；`clickAction` 带 Possible expert 时优先开专家确认框，标签处理完后按是否入册开登记或编辑弹框）；`unmappedSpeakers[{speakerId, name, sentenceCount, aiSuggestedMatch, registryForm}]`；`routingRows[{rowId, outputType, destination, companyName, visibleTo, content, sourceLine, speakerParticipantId, sourceTimestamp, authorized, projectionStatus}]`（按去向、发言人、出处时间点排序；`sourceTimestamp` 仅跨公司与证词行，供矩阵只读显示，7 #Q26；摘要行的 `projectionStatus` 表示摘要是否已写进在线的正文条目，正文不在线时为 `NONE`，7 #Q42）；`updatedAt` | P1~P5、P7 读；J2、J3（按说话人数句）、J4、J6 读；LG 表读 | PGM / SA（会议所属租户） | PG-02、PG-02a~d | 新增，见 3.6 |
| API-22 | POST `/meetings/{meetingId}/extraction` | Start Extraction：页头写进识别结果、整场下线、后台提取，立即返回（6.11、9.5.1）。提取或证词补抽进行中、必填项不齐（9.5.1）时拒绝；点击时清空本场 P2 的 `testimony_backfill_status`（旧的补抽失败随旧产物作废） | `meetingType`、`companyIds`、`updatedAt` | `extractionStatus = RUNNING`、`updatedAt` | P1、P4、P2（清补抽状态）写；P5、P7 软删并下线；P8 `TYPE_CHANGE` / `COMPANY_CHANGE` / `EXTRACT` | PGM / SA | PG-02 | 新增，见 3.6 |
| API-23 | POST `/meetings/{meetingId}/routing/apply` | Confirm & Apply Routing：授权勾选、Portfolio 标记、改 `Unknown`、GS → LP 的公司增删（9.6.5）。应用时按每一行的当前状态整体推一遍投影：已授权、未删、没上线的上线（含待确认专家期间默认勾选、一直没投影的行），取消授权的同步下线。摘要行的授权依赖同一（去向, 公司）的正文行：正文行未授权或已软删时按正文为准，摘要不生效、不投影（静默归一：该摘要行按未授权落库、记 `AUTHORIZE_CHANGE`，不返回错误；提取时的授权初值同样归一，7 #Q42）。提取或证词补抽进行中时拒绝（含改 `Unknown`：否则后台任务结束会把内容写回已打回的会议）；不改 `Unknown` 时，参会人已改动但还没点 Start Extraction、有未处理的专家标记、GS → 创始人多于一家公司也拒绝（改 `Unknown` 时只受前一条限制，7 #Q25e）。另有两条需确认、不硬拦（7 #Q48）：按当前参会人重跑类型判定、结果与当前类型不同（`TYPE_MISMATCH`，带 `suggestedType`）；GS → 创始人会议有 Founder 的组织 / 所属公司与关联公司对不上（`FOUNDER_COMPANY_MISMATCH`）。服务端重算，有提示且未带 `confirmWarnings=true` 时返回 40903、`data.warnings` 列出，前端二次确认后带上重提；应用时不重读最新 Cheat Sheet（会议用自己的快照） | `authorizations[{rowId, authorized}]`、`portfolioIds`、`meetingType?`（仅 `UNKNOWN`）、`companyIds?`（仅 GS → LP）、`confirmWarnings?`、`updatedAt` | `status`、`updatedAt` | P7 写 + 投影；P1 状态与 `portfolio_ids`；改 `Unknown` 整场下线；P4；P8 | PGM / SA | PG-02 | 新增，见 3.6 |
| API-24 | PUT `/routing-rows/{rowId}/content` | 行内 Save（9.6.3 两步提交合在一个接口）：先跑 n-gram 与该去向适用的实体剥离——清洗后没有变化就落库（已授权的重投影，待确认专家时不投影；摘要行在正文在线时只替换条目的 `summary` 与摘要向量，不重新向量化正文，7 #Q42）；有变化就不落库，返回清洗结果与命中明细，管理员确认后把清洗后的文本连同首次提交稿再提交一次，这次不再有变化即落库，`CONTENT_EDIT` 记改前、首次提交稿、定稿与命中（服务端按首次提交稿重算）。摘要行超过 150 个英文单词、该行发言人的证词补抽进行中时拒绝 | `content`、`originalContent?`（第二次提交时带首次提交稿）、`updatedAt` | 落库时：该行、`updatedAt`；未落库时：`cleanedContent`、`hits[]`（删去的行及原因、替换的实体）、`wordCount` | P7 写；P1 写（碰行）；J3 读（比对基准）；P8 `CONTENT_EDIT` | PGM / SA | PG-02 | 新增，见 3.6 |
| API-25 | POST `/meetings/{meetingId}/external-parties` | Assign new external party：先看填的邮箱是不是本租户 LG 平台用户——是就不进名册，按平台用户更新本场 P2 / P3，得出的公司写成 P4 未采纳的候选（`adopted = false`、依据 `EMAIL`），是否采纳由页头与 Start Extraction 决定；再看填的邮箱是否已在名册某条记录会议当天生效的版本里——在就不新建，把本场参会人 / 说话人绑到那条记录、按它刷新 P2 / P3，名册不改、表单其余内容不写入；邮箱在名册里、但会议当天生效的记录里没有它，或分属两条记录，均拦截（42200，7 #Q49）；都不是才调 API-06 写名册（带 `sourceMeetingId`；重名由 API-06 自动加后缀并返回最终姓名，记进 P2，7 #Q46），更新本场 P2 / P3（9.5.5、9.5.7）。有效期必须包含会议日期（拦截，7 #Q44）；来源是参会人时本场邮箱锁定（不可删改，可加别的邮箱），来源是未对上的说话人时邮箱由管理员填写、不锁。之后重跑类型判定 | `participantId` 或 `speakerId`、表单字段、`updatedAt` | 更新后的参会人、`suggestedType?`（可判定为 X）、`suggestedCompany?`（按平台用户认出的公司）、`registryMatchedName?`（按名册已有记录认人时，7 #Q49）、`participantsChanged`、`updatedAt` | P2、P3、P1（碰行）写，必要时 P4（候选）；LG 表读；J4 读（按邮箱认人），新建经 API-06 | PGM / SA | PG-02a | 新增，见 3.6 |
| API-27 | POST `/meetings/{meetingId}/speakers/{speakerId}/assignment` | 把未对上的说话人指定为本场某位参会人，重跑类型判定 | `participantId`、`updatedAt` | 说话人、`suggestedType?`、`participantsChanged`、`updatedAt` | P3、P2（`matched_name`）、P1（碰行）写 | PGM / SA | PG-02d | 新增，见 3.6 |
| API-28 | POST `/meetings/{meetingId}/participants/{participantId}/registry-sync` | 参会人名册同步（7 #Q44）：PG-02b / PG-02c 保存成功、关窗后调，不收表单、不调 Java，按库里现状算、可重复调用。按会议日期生效的名册记录刷新本场 P2（平台用户按 #Q47 以记录角色为准）；此人的建议标签在记录里 → `ACCEPTED`、在拒绝名单 J6 → `DECLINED`（P5，含自动消解）；按 9.9.1 参会人改动口径与提取快照（P1 `current_extraction_input`）比：有参会人改动 → `participantsChanged = true`，角色变了重跑类型判定、返回 `suggestedType`（不静默改判）；没有参会人改动、只有被推测者的专长标签变了（与刷新前 P2 标签比）→ 同步提取输入里此人的标签，后台补抽此人证词（提示词 P5；是否真补按 #Q35 的 `testimony_tags` 规则，2.5）；都没变 → 只更新建议标签状态。首轮未完、提取或证词补抽进行中拒绝（40901） | `cheatSheetName?`（新登记时传 API-08 返回的最终姓名）；不带 `updatedAt` | `participantsChanged`、`suggestedType?`、`testimonyBackfillStatus`、`updatedAt` | P2、P5、P1（碰行、提取输入）、P7（补抽）写；J4、J6 读；P8 `EXTRACT` | PGM / SA | PG-02b、PG-02c | 新增（7 #Q44 改造），见 3.6 |
| API-29 | POST `/meetings/{meetingId}/participants/{participantId}/testimony-backfill` | 证词补抽失败后 Retry：只在该参会人 `testimony_backfill_status = FAILED`、且本场没有进行中的提取或补抽时接受 | `updatedAt` | `testimonyBackfillStatus` | P2、P7、P1（碰行）写；P8 `EXTRACT` | PGM / SA | PG-02 | 新增，见 3.6 |
| API-30 | GET `/goldie-base/contents` | Goldie Base 两个新 Tab 共用：已授权、已投影的跨公司内容，或署名版证词（9.11.4、9.11.5）；关键词匹配内容与会议名称（证词另匹配说话人姓名，按设计稿，7 #Q25b），按会议日期区间过滤；按 `meeting_started_at DESC, meeting_id, source_timestamp`（空的排最后）`, id` 排序、按行分页，前端把相邻的同场行归成一张卡片，同一场会跨页时拆成两张卡片，可以接受（排序与会议名称匹配用 P7 冗余的会议时间与标题，7 #Q23） | `type`（`CROSS_COMPANY` / `TESTIMONY`）、`keyword`、`dateFrom`、`dateTo`、`page`、`pageSize`、`organizationId?` | `items[{rowId, content, meeting{meetingId, firefliesId, title, startedAt, meetingType, canOpen}, inPlaybook, speakerName?, expertiseTags?}]`（后两项仅证词）、`total`、`canTogglePlaybook` | P7 读（排序、筛选都在 P7 内完成）；分页后按会议 id 批量读 P1（会议类型、`fireflies_id`）；证词另读 P2（说话人；关键词匹配说话人时先在 P2 按姓名查出参会人 id） | 管理端 PM / PGM / SA；公司端拒绝 | PG-05c、PG-05d | 新增 |
| API-31 | PATCH `/routing-rows/{rowId}` | 改中间表行上的标记，立即生效、不写审计：`inPlaybook`（Play candidate，限跨公司行与证词署名行，PGM / SA）；`fundTagIds`（基金标签，限知识库正文行，看得到该行的管理端 PM / PGM / SA——机构层行按租户判，候选须在本租户 `company_group` 内） | `inPlaybook?`、`fundTagIds?`（一次改一个） | 改后的值 | P7 写 | 按字段（见功能）；租户取前端传入的组织 id、不做会话租户等值校验（7 #Q32） | PG-05c、PG-05d、PG-05a1 | 新增 |
| API-32 | GET `/org-options` | 本租户全部公司（含不在营的，带状态）与全部 Portfolio：会议页 Company / Portfolio 下拉候选（只有 PGM / SA 进得了会议页，按设计 9.5.3 / 9.5.4 即本租户全部）、知识库基金标签候选（设计 9.11.2 为本租户 Portfolio）。不复用 Java `companyGroup/companies`：它返回「公司 × Portfolio」配对，没挂 Portfolio 的公司不返回、也不去重 | `meetingId?`（会议页：由会议推出租户）或 `organizationId?`（知识库页：传组织树首叶组织 id，信任传入，7 #Q32） | `companies[{companyId, name, status}]`、`portfolios[{companyGroupId, name}]`；PM 调用只返回 `portfolios`；不在营的公司带状态返回，GS → 创始人时前端置灰不可选（2.1） | LG `company`、`r_organization_company`、`company_group` 读 | 管理端（PGM / SA；PM 用于基金标签） | PG-02、PG-05a1 | 新增，见 3.6 |

API-26（Edit external party 经 Python 转调 API-07）已删除：改为前端直调 API-07、关窗后调 API-28（7 #Q44），编号不复用。

### 3.3 改造与复用的现有接口

| 编号 | 方法 路径 | 改什么 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|
| API-33 | GET `/api/ai/file-registry/files` | 主表仍是登记表 `ai_file_registry`（分页、排序、筛选都在登记表上），P7 / P1 只在分页后按本页的 Fireflies 行补查。筛选与搜索保持现有：搜索只按文件名，不加设计稿的 Source 筛选（用户决定 2026-10-27，7 #Q24a）；Source 列照加。只纳入 `FIREFLIES` 行（证词、跨公司登记为另两个值，不进本 Tab，7 #Q42），对公司端普通用户不按 `created_by` 收窄；机构层作用域按组织 + 机构层空间圈定；`source` 取值由 `company` / `session` 改为 `GOLDIE` / `FIREFLIES`（改语义，原值前端未使用，设计第八章 #18）；Fireflies 行经 P7 按 `file_id`（同一 `file_id` 有摘要、正文两行，取正文行，7 #Q42）带出会议 id、能否跳原文、中间表行 id（供 API-31 改基金标签）、`fundTagIds`（手动选过的，下拉只回显它）与 `portfolioDisplay`（列里显示的值：手动标签，或回退的公司所属 Portfolio / 会议 Portfolio 标记）；Fireflies 行的 From Chat 与 Uploaded By 都显示 `—`：`uploadedBy` / `uploadedByName` 返回空，不带出系统用户 id（设计 9.11.2 交开发设计定，7 #Q25a；设计稿 From Chat 一格写的是公司名，不照）（第八章 #11~#13、#16、#18） | PG-05a | 改造，见 3.6 |
| API-34 | GET `/api/ai/file-registry/files/filter-options` | 作用域放开到 Fireflies 行后，上传者选项排除 `FIREFLIES` 行（Uploaded By 显示 `—`，7 #Q25a） | PG-05a | 改造 |
| API-35 | GET `/api/ai/file-registry/files/{entryId}/download` | 加 `FIREFLIES` 分支：公司端限本公司 APP 端，管理端限可访问公司或本组织机构层（#12）。Fireflies 行没有 S3 对象，由后端按条目的 markdown 现生成，返回 `data = {url: null, fileName, content}`；其他行仍只返回 `url`（7 #Q41） | PG-05a | 改造，见 3.6 |
| API-36 | PUT、DELETE `/api/ai/file-registry/records/{registryId}` | `update_record` / `delete_record` 里按 `business_type` 显式拒绝 `FIREFLIES` / `FIREFLIES_TESTIMONY` / `FIREFLIES_CROSS_COMPANY` 三类行（现在两处都不看业务类型，DELETE 还会连带删 RAG 条目与向量）；`_PROTECTED_BIZ_TYPES` 另加这三个类型，防聊天上传改写会议行（7 #Q42）；Fireflies 行前端不显示删除（#12） | PG-05a | 改造 |
| API-37 | GET `/api/ai/memories` | 仍是「登记表圈定条目 → `ai_rag_entry` 取摘要分页」两步，不读 P7（Fireflies 摘要在投影时已写进正文条目的 `summary`，7 #Q42）。圈定 `KNOWLEDGE_BASE` 与 `FIREFLIES`，只列摘要非空的条目（现有第二步本就只取 `summary` 非空的），返回项加来源字段，增加机构层（#11、#13、#19）。管理端 `scope` 加取值 `fireflies`：只取 `FIREFLIES`、只看会议摘要、不分层；公司端不加筛选；设计稿 File Scope 里的 Document Summary 选项不加。会议摘要的标签并排显示：层徽标（Company / Portfolio Memory，管理端）+ Fireflies Memory + Meeting Summary；文件摘要不变（用户决定 2026-10-27，7 #Q24b） | PG-05b | 改造，见 3.6 |
| API-38 | POST `/api/ai/sse/stream`（Goldie 召回） | 接口契约不变；召回改造见第八章 #7~#10 | Ask Goldie 对话（不在本页面清单） | 改造 |
| API-39 | GET `/api/web/organization/findByTree` | 不改：PG-01 的租户下拉、PG-05 的默认租户 | PG-01、PG-05 | 复用 |
| API-40 | POST `/api/web/storage/uploads/presign`、`/uploads/{id}/verify` | 不再使用（改纯文本，7 #Q41）：原为 Python 投影上传 markdown 用，`FileBusinessTypeEnum` 新增 Fireflies 类型、放行 `md`（#3），已撤回；接口本身不改 | 无页面 | 不再使用 |

接口合并（用户决定 2026-10-27，7 #Q22）：会议详情一次取回弹框预填、专家建议标签与矩阵；Summary Records 列表顺带返回红点数；行内 Save 的清洗预览与落库合成一个接口；专家确认框不再单设「打开即消解」接口，打开前已处理过的标签改为保存后的同步（API-28）时落库；两个新 Tab 共用一个列表接口；Play candidate 与基金标签合成一个改标记接口；Email Domain 整份提交。审核时发现 Java `companyGroup/companies`、`companyGroup/user` 的口径不合用，改由 API-32 提供候选。

### 3.4 页面 × 接口对账

| 页面 | 加载 | 操作 |
|---|---|---|
| PG-01 | API-19（显示哪些 Tab、PM 无权限提示）、API-39（租户下拉）；PGM / SA 的红点取 API-20 的 `pendingCount`（默认 Tab 即 Summary Records，从其他 Tab 进入时调一次 API-20）。公司端只调 API-19，不调 API-20 / 39 | 切换租户后 URL 带 `org`，各 Tab 带 `organizationId` 重新加载 |
| PG-01a | API-20 | 搜索、类型 / 状态 / 时间筛选、分页：API-20 |
| PG-01b | API-01 | Link：API-02；Sync now：API-03（之后轮询 API-01 看 `syncing`） |
| PG-01b1 | — | Remove：API-04 |
| PG-01c | API-05、API-10 | 搜索、Role 筛选、分页：API-05；域名增 / 改 / 删：API-11（整份提交） |
| PG-01c1 | 编辑时用 API-05 的行数据预填 | Confirm：新增 API-06，编辑 API-07；新增时姓名失焦查重：API-41 |
| PG-01c2 | API-12 | `Add "<值>"`：API-13；删除：API-14 |
| PG-01d | API-15、API-16 | 搜索、日期 / 参会人 / 有效性筛选、排序、分页：API-15 |
| PG-02 | API-21、API-32 | Start Extraction：API-22（之后轮询 API-21）；Confirm & Apply：API-23（返回 40903 时二次确认后带 `confirmWarnings=true` 再调一次）；行内 Save：API-24（有命中时确认后再调一次）；证词补抽 Retry：API-29；Discard Changes 只在前端 |
| PG-02a | 用 API-21 的 `registryForm`；API-12 | Confirm：API-25；姓名失焦查重：API-41；标签维护：API-13 / 14 |
| PG-02b | 用 API-21 的 `registryForm`（含 `versionId`）；API-12 | Confirm：API-07（带 `sourceMeetingId`）→ 关窗后 API-28 → 刷新 API-21；标签维护：API-13 / 14 |
| PG-02c | 用 API-21 的 `expertCandidates`、`registryForm`（含 `versionId`）；API-12 | Save：API-08 → 关窗后 API-28 → 刷新 API-21；新登记姓名失焦查重：API-41；标签维护：API-13 / 14 |
| PG-02d | 用 API-21 的参会人列表与说话人的 `aiSuggestedMatch` | 确认：API-27 |
| PG-03 | API-17、API-18（首批） | 后台自动续加载至全篇：API-18 |
| PG-04 | API-09 | — |
| PG-05 | API-19、API-39 | — |
| PG-05a | API-33、API-34 | 下载：API-35；删除：API-36；Source 链接跳 PG-03 |
| PG-05a1 | API-32 | 选择：API-31（`fundTagIds`） |
| PG-05b | API-37 | — |
| PG-05c | API-30（`type=CROSS_COMPANY`） | 搜索、时间筛选、分页：API-30；开关：API-31（`inPlaybook`）；会议名跳 PG-02（`canOpen`） |
| PG-05d | API-30（`type=TESTIMONY`） | 同 PG-05c |

对账结果：每个页面的加载与改数据操作都有接口；Java 名册写接口都由页面直调（API-08 由 PG-02c 直调，7 #Q44），API-26 已删除；API-40 已不再使用（7 #Q41）；API-38 由 Ask Goldie 对话使用，对话页不在本清单。设计稿与设计文档不一致的几处已在 7 #Q24 拍板，补审新发现的已在 7 #Q25 拍板。

### 3.5 无页面的调用与跨服务链路

| 调用 | 调用方 → 被调方 | 说明 |
|---|---|---|
| 每日拉取 | AWS EventBridge → `scheduler-queue` → Java `ScheduleProcessor` | `FixedScheduleTypeEnum` 加一项，分发到 Fireflies 拉取服务（与 API-03 同一链路）；入口先 `setCurrentUserId("1")`；定时与手动互斥靠 J1 `sync_started_at` 条件更新（第八章 #29） |
| 新会议 | Java → SQS 新队列（如 `fireflies-meeting-queue`）→ Python `consumer/fireflies/` | 队列在 Java `InitSqsQueueEnum` 登记（启动时建队列与死信队列），Java 不监听；消息带租户、会议 id、触发方式与触发人；投递与补投见 J2（第八章 #30）；消息体见 3.6 |
| 公司 / 公司端用户增改 | Java 保存入口发领域事件 → `@TransactionalEventListener(AFTER_COMMIT)` → SQS 新队列（如 `fireflies-company-change-queue`，同样在 `InitSqsQueueEnum` 登记）→ Python 自动路由 | 入口：`CompanyServiceImpl.create` / `update`（`addWithoutEmail`、`addCompanyAndSetStage` 都汇到这两处）、`CommonServiceImpl.createInvitedUserAndSendEmail`（覆盖 `POST /users/invite` 与 `POST /project/inviteuser`，后者设计第八章 #27 漏列）、`UserServiceImpl.clientUser` / `update`。归档（`POST /invite/archiveCompany`）与停用（`PUT /invite/delete/{companyId}`）不发：两者只改归档标记、解除 Portfolio 关联，不改公司状态与公司端用户，不会产生新的匹配。Python 现有约定一条队列一种消息，故两条队列（第八章 #27）。消息只带公司 id、变更类型与操作人，不带租户，Python 按 `r_organization_company` 查（3.6） |
| 名册新建 | Python → Java API-06 | 只有 Assign new external party（API-25）经它新建，透传用户 token（第八章 #31）；会议页的名册编辑与专家确认由前端直调 API-07 / 08，Python 不再写名册（7 #Q44） |
| PGM / SA 判定 | Python → Java API-19 | 透传用户 token |
| 跨端读表 | Java 读 P1、P2（本场邮箱）、P5；Python 读 J1~J6 与 7 张 LG 业务表 | 见 1.4；Python 直读 LG 业务表与 Python 规范「LG 业务数据经 Java 网关取」不一致，随数据权限一起定（A5）。现有只读映射 `lg/db/models/models.py:570` 起的 `Company` 没有公司名列，API-20 / 21 / 32 要补 |
| 卡死兜底 | 定时清扫（单独功能，与本功能一起上线） | 见 P1「卡死兜底」 |

跨服务调用链：

- 拉取：Java 定时 / API-03 → Fireflies GraphQL → J2 / J3 → SQS → Python 识别与提取 → P1~P7 → 投影：RAG 条目（TEXT 来源、合成 `file_id`）+ X1 登记，不调 Java（7 #Q41）
- 登记参会人：前端 → Python API-25 →（非平台用户、邮箱不在名册，7 #Q49）Java API-06 → Python 更新 P2 / P3
- 编辑参会人（Edit external party）：前端 → Java API-07（写 J4）→ 关窗 → 前端 → Python API-28（刷新 P2 / P5 / P1，必要时后台补抽 → P7 → 投影）
- 专家确认：前端 → Java API-08（写 J4 + J6）→ 关窗 → 前端 → Python API-28（写 P5 / P2 / P1，后台补抽证词（提示词 P5）→ 写 P7 → 投影）
- 自动路由：前端 → Java 公司 / 用户保存 → 事务提交后 SQS → Python 重跑 ②③ → 自动提取
- Raw Data 的 Invalid：前端 → Java API-15 → 读 Python 表 P1

### 3.6 开发期补定的契约（2026-10-28）

第 1 波开发中补定、前后端已按此对齐的契约，补在通用约定与 3.1~3.5 之上（对应行末注「见 3.6」）；与前文冲突时以本节为准。

**错误码**

Java：`Result.fail(code, message, data)`，HTTP 200 + `success:false`；`message` 为英文，前端原样显示。

| 错误码 | 接口 | 含义 |
|---|---|---|
| `FF_KEY_INVALID` | API-02 | Link 时 Fireflies 鉴权失败 |
| `FF_NETWORK_UNREACHABLE` | API-02 | 网络不可达或超时 |
| `FF_SYNC_IN_PROGRESS` | API-03 | 正在同步 |
| `FF_NOT_CONNECTED` | API-03 | 没有 key（`UNCONNECTED`） |
| `FF_EMAIL_DOMAIN_INVALID` | API-11 | 域名校验不过；`message` 写明哪一个、什么原因 |
| `FF_EXPERTISE_TAG_DUPLICATE` | API-13 | 标签重名 |
| `FF_EXPERTISE_TAG_UNDELETABLE` | API-14 | 不可删；`message` 写明原因：预置 / 名册用过 / 有未处理专家标记 |
| — | 全部 | 无权限沿用 `FfAccessSupport` 抛的 `BadRequestException`，不另设码；名册的有效期校验（To 早于 From、带来源会议时不含会议日期）同样抛 `BadRequestException`。名册重名不再报错，自动加后缀（7 #Q46）；新建时邮箱已登记在别的条目（API-06 / 08，7 #Q49）同样抛 `BadRequestException`，`message` 写明邮箱登记在谁名下（如 `This email is already registered to Tom in the Cheat Sheet.`） |

Python：`{success:false, code, message, data}`，HTTP 200；五位数，同 financial_extract 的 `40400` 风格（API-33~36 例外，见通用约定）。

| 错误码 | 含义 |
|---|---|
| `40300` | 无权限：非 PGM / SA、公司端调用管理端接口 |
| `40400` | 不存在 |
| `40900` | 页面已过期：`updatedAt` 对不上，前端提示刷新 |
| `40901` | 提取或证词补抽进行中；名册同步（API-28）另含首轮未完，前端提示稍后重试（7 #Q44） |
| `40903` | Confirm & Apply 有需确认的提示（API-23，7 #Q48）：`data.warnings` 列出，前端二次确认后带 `confirmWarnings=true` 重提 |
| `42200` | 前置条件不满足：必填项不齐、有未处理专家标记、GS → 创始人多于一家公司、摘要超 150 词、登记的有效期不含会议日期（API-25）、登记填的邮箱已在名册但会议当天生效的记录里没有它或分属两条记录（API-25，7 #Q49）等；`message` 写明原因 |
| `50200` | 调用 Java 失败 |

**SQS 消息体**（Java → Python）：JSON camelCase，带 `type` / `version`；值为 null 的字段不出现；另带 Java 消息基类的 `messageType` / `queueName` / `sendTime` / `uuid`，Python 忽略。

| 队列 | 消息体 | 说明 |
|---|---|---|
| `fireflies-meeting-queue` | `{type: "FIREFLIES_MEETING", version: 1, organizationId, meetingId, trigger: "DAILY" \| "SYNC_NOW", triggeredBy?, traceId?}` | 定时拉取没有 `triggeredBy` |
| `fireflies-company-change-queue` | `{type: "FIREFLIES_COMPANY_CHANGE", version: 1, companyId, changeType: "COMPANY" \| "CLIENT_USER", operatorId, traceId?}` | **不带租户**，Python 按 `r_organization_company` 查公司所属租户（设计第八章 #27 已回写）；`operatorId` 必有，取不到当前用户时 Java 填 `"1"` |

**Java 接口**

| 项 | 补定 |
|---|---|
| API-19 | `AuthenticatedUserDto` 新字段 `pgmOrSuperAdmin: boolean`，与 Fireflies 接口首行的 PGM / SA 断言同一判定；前端与 Python 都读它 |
| `organizationId` | 各接口的可选 `organizationId` 一律走 query 参数（GET 与写接口都是），写接口的 body 不带它 |
| 名册接口 | 邮箱查重（7 #Q49）：新建（API-06、API-08 未登记分支）时任一邮箱（忽略大小写）已出现在租户内别的条目的任一版本里即拒绝，不认人、不合并；姓名后缀（7 #Q46）：API-06 / 08 新建与 API-41 查重同一规则——姓名忽略大小写比较，重名时从 1 起取第一个未占用编号接在姓名后（Tom → Tom1 → Tom2），保存时再算一次、以保存时为准；API-05 按姓名升序，`overdueCount` 按全租户算；API-06 / 07 / 08 的 To 早于 From 拒绝；带 `sourceMeetingId` 时有效期必须包含会议日期（From ≤ 会议日期，To 为空或 ≥ 会议日期；会议日期为 J2 `started_at` 的 UTC 日期，7 #Q44） |
| 返回结构 | API-06 成功返回新行（结构同 API-05 的一行，`name` 为最终姓名）；API-07 `{ids[], reviewed}`（每次至多一个新行；会议页没有改动时都为空）；API-08 `{name, id}`（最终姓名、写入的版本 id；只写了驳回、没有登记字段或已在册没有改动时 `id` 为空）；API-41 `{exists, availableName}`；API-09 `rows` 含 `source`、`updatedBy`、`updatedAt`；API-10 / 11 `{domains[]}`；API-13 返回新标签 |
| API-15 | `validity`：`ALL`（缺省）\| `INVALID_ONLY` \| `HIDE_INVALID`；`sort`、`validity` 非法值拒绝、不回落；`size` 1~100 |
| API-16 | `[{value, label}]` 的 `value`、`label` 都是显示名；不分页（每租户量小，与 Java `coding.md` §10 的分页要求不一致） |
| API-18 | 响应 `{sentences: [{order, speakerName, startTime, text}], hasMore}`；`startTime` 为秒（number，可带小数）；`limit` 1~500，前端每批 500，首批显示后在后台连续取完全篇（7 #Q29） |
| 时间格式 | Raw Data 接口（API-15、17）的时间字段为 `yyyy-MM-dd'T'HH:mm:ss'Z'`（UTC） |

**Python 接口**

| 项 | 补定 |
|---|---|
| API-21 `participants[].registryState` | `UNREGISTERED`（未入册的外部人）\| `REGISTERED`（名册中已有）\| `PLATFORM_USER`（LG 平台用户）；PG-02c 按它决定 Name 是否可改（只有 `UNREGISTERED` 可改并失焦查重，其余只读；平台用户首次登记时姓名取账号姓名、只读，打开时即调 API-41 查重并在姓名下提示；平台用户的 Role 也可改，7 #Q46、#Q47） |
| API-21 `participants[].registryForm.versionId` | T2（会议日期当天生效的那条记录）的 id；已在册时有值，PG-02b 作 API-07 的 `{id}`、PG-02c 作 API-08 的 `baseVersionId`（7 #Q44） |
| API-21 `badges` / `clickAction` | `badges`：`EXPERT` \| `POSSIBLE_EXPERT` \| `AI_INFERRED`；`clickAction`：`EXPERT_CONFIRM` \| `ASSIGN` \| `EDIT` \| `NONE` |
| API-21 `identifySubReasons` | 待识别子原因（设计 9.4.2），现算，会议不在待识别时为空数组；取值由前端提出、Python 对齐，不在下列的前端原样显示：`PARTICIPANT_UNIDENTIFIED`（有未识别的参会人）、`SPEAKER_UNMAPPED`（有未对上的说话人）、`TYPE_UNDETERMINED`（类型为 Unknown，含被改为 Unknown）、`COMPANY_MULTIPLE`（GS → 创始人关联了多家公司）、`COMPANY_UNDETERMINED`（GS → 创始人定不出公司，含公司方只来自 P8、名册反推不出）、`FOUNDER_COMPANY_MISMATCH`（有 Founder 归属不到关联的公司；近似，不区分是否到场）、`IDENTIFICATION_FAILED`（P1 / P8 最终失败，只在之后还没提取过时出现）、`EXTRACTION_FAILED`（最近一次提取作废） |
| API-21 `companyPortfolios` | `[{companyGroupId, name}]`：采纳公司经 `r_company_group`（`status = 0`）关联的本租户 Portfolio，不论会议类型都返回；即 3.2 所说「GS → 创始人的只读 Portfolio」 |
| API-25 `platformUser` | `boolean`：按 LG 平台用户识别、不进名册时为 true；前端据此提示，不再从 `suggestedCompany` 推断 |
| API-25 `registryMatchedName` | 填的邮箱已在名册某条记录会议当天生效的版本里、按那条记录认人未新建时，为该记录的姓名，否则不返回；前端据此提示（7 #Q49）。匹配忽略大小写，任一填写的邮箱命中即算；拦截时 `message` 写明邮箱登记在谁名下、请先到 Cheat Sheet 调整 |
| API-23 二次确认 | 入参 `confirmWarnings?: boolean`；有提示且未带 `true` 时返回 40903，`data.warnings[{code, message, suggestedType?}]`：`code` 为 `TYPE_MISMATCH`（带 `suggestedType`）\| `FOUNDER_COMPANY_MISMATCH`（7 #Q48）；改为 `Unknown` 应用时不做这两条 |
| API-25、27~29 响应 | 不返回 `participant`，成功后前端重新拉 API-21；API-27 另返回 `speaker{speakerId, name, participantId}`；API-28 返回 `{participantsChanged, suggestedType?, testimonyBackfillStatus, updatedAt}`；API-29 返回 `{testimonyBackfillStatus, updatedAt}` |
| API-32 `companies[].portfolioIds` | 该公司所属的 `company_group` id；GS → 创始人在页头改公司时，前端据此实时算只读 Portfolio（设计 9.5.4）；`status` 为公司状态码字符串 |
| API-33 `KbDocument` | 新增 `source: 'GOLDIE' \| 'FIREFLIES'`（原 `company` / `session` 语义作废）。以下仅 FIREFLIES 行有值、其余为 null：`meetingId`；`canOpenTranscript: boolean`（可跳 PG-03）；`routingRowId`（供 API-31）；`fundTagEditable: boolean`（知识库正文行且调用者是管理端，前端据此把 Portfolio 列变下拉）；`fundTagIds: string[]`（手动选过的 `company_group` id，下拉只回显它）；`portfolioDisplay: string[]`（列里显示的 Portfolio 名：手动标签或回退值）。Fireflies 行的 `uploadedBy` / `uploadedByName` / `threadId` / `threadTitle` 为 null |
| API-35 下载 | Fireflies 行（登记 `FIREFLIES`）没有 S3 对象，后端按该条目在线的 markdown（`content_text`）现生成，返回 `data = {url: null, fileName, content}`：`fileName` 为登记行文件名（`.md`），`content` 为 markdown 全文；其他行仍返回 `{url}`，不变。前端见 `content` 时用 Blob 下载（7 #Q41） |
| API-37 `MemoryItemDTO` | 新增 `source: 'DOCUMENT' \| 'FIREFLIES'`；管理端 `scope` 新取值 `fireflies`（只取 `FIREFLIES` 中摘要非空的条目，7 #Q42） |
| `updatedAt` | P1 乐观锁凭证，在 API-21 与各写接口的出入参里一律保留**完整精度**（ISO 8601 带微秒与时区，如 `2026-10-28T03:15:42.123456+00:00`），前端原样回传、不格式化，不要截成 `yyyy-MM-dd HH:mm:ss`；写接口收到不带时区的按 UTC |
| 其余时间 | UTC `yyyy-MM-dd HH:mm:ss`（不带时区，前端按 UTC 解析，如 API-30 `startedAt`）；有效期 `yyyy-MM-dd` |

**知识库条目的摘要与登记类型**（用户决定 2026-10-28，7 #Q42；P7、X1）

| 项 | 补定 |
|---|---|
| 登记 `business_type` | `FIREFLIES`（三类知识库去向的条目：正文 + 摘要）\| `FIREFLIES_TESTIMONY`（证词两版）\| `FIREFLIES_CROSS_COMPANY`（跨公司）；不再有 `FIREFLIES_SUMMARY`。Knowledge Base Tab（API-33）只取 `FIREFLIES`；Memory Tab（API-37）取 `KNOWLEDGE_BASE` 与 `FIREFLIES` 中摘要非空的条目，`scope=fireflies` 只取 `FIREFLIES`；API-36 拒绝这三个类型 |
| 摘要并入正文条目 | 每个（去向, 公司）只投 1 条 TEXT 条目：`content_text` = 正文 markdown，`summary` 列 = 摘要（摘要行已授权时写，否则为空）。中间表仍是摘要行、正文行两行，各自编辑、各自 Authorize，共用条目的 `ai_rag_entry_id` / `file_id` |
| 摘要跟着正文走 | 正文行未授权或已软删时条目不上线，摘要行的授权不生效：前端把摘要勾选框置灰并随正文取消；API-23 遇「摘要授权而正文未授权」按正文为准 |
| 摘要向量 | `summary` 非空时整段建一条 `chunk_kind=summary` 的向量（不拆分），用我方传入的摘要，不调系统摘要器；为空不建 |
| 只改摘要 | 摘要行改内容（API-24）或勾 / 取消摘要授权（API-23），且正文在线：只替换条目的 `summary` 列与那条摘要向量，不重新向量化正文 |
| RAG 管理端「重试」 | `POST /api/ai/rag/entries/{id}/retry` 遇到 Fireflies 条目：跳过系统摘要器，保留原 `summary`，并按它重建摘要向量 |

**两端共用的规则**

| 项 | 补定 |
|---|---|
| 名册版本平局 | 同一日期有多个生效版本时，按 `updated_at` 降序、再按 `id` 降序取第一个（设计 9.7.2）；Java 版本裁决与 Python 识别 ④ 一致 |
| 公共邮箱域名清单 | Java `FfEmailDomainServiceImpl`（API-11 校验）与 Python `identification_service.PUBLIC_EMAIL_DOMAINS`（识别 ③ 排除）各写死一份、同为 23 个，改清单要两端同步改、同时发版；设计 1.9「清单可配」暂未做 |
| 在营公司状态 | `{2, 3, 4, 5}`：Needs Intervention / Needs Guidance / Thriving / Achieving（需求原文的 Active 即 Achieving）；Exited / Shut down / Off journey 与状态为空的不在营（Python `IN_OPERATION_COMPANY_STATUSES`，7 #Q28） |
| 每日拉取 | `FixedScheduleTypeEnum.FirefliesDailyPull`，每日 03:40 UTC，写死不可配（1.4、7 #Q33） |

## 4. 页面功能按钮

通用约定：文中的中文提示只表达语义，界面文案一律英文，设计稿已有的标题、按钮名与提示照设计稿，没有的开发时按设计稿语气定稿。成功用顶部 toast（antd `message`），表单校验错误显示在字段下方，后端拒绝的原因原样提示；详情页的写操作遇到 `updatedAt` 冲突一律提示「页面已过期，请刷新」，不覆盖；所有带 `org` 的跳转与面包屑保留 `org` 参数（第 2 节「入口与守卫」）。

### 4.1 PG-01 Fireflies Management（容器）

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 进入页面 | — | 管理端 PGM / SA、公司端 | 按 API-19 的标志位决定显示哪些 Tab；PM 显示无权限提示，不请求管理端接口 | API-19 | 否 | — |
| 切换 Tab | 页头 Tab 栏 | PGM / SA 四个 Tab；公司端只有 Raw Data，不显示 Tab 栏 | 改 URL `?tab=`（replace），加载对应 Tab | 各 Tab 接口 | 否 | — |
| Summary Records 红点 | Tab 标题 | PGM / SA，`pendingCount > 0` | 显示红点；从其他 Tab 进入时调一次 API-20 取数 | API-20 | — | — |
| 切换租户 | 页头右上组织树下拉 | 组织树根下有子组织（7 #Q17） | URL 写入 `org`，当前 Tab 与红点带 `organizationId` 重新加载 | API-39（下拉数据）、各 Tab 接口 | 否 | — |

### 4.2 PG-01a Summary Records

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 搜索 | 筛选栏 | — | 按标题、会议 id、公司名，输入防抖后从第 1 页重查 | API-20 | 否 | 无结果显示空态 |
| 会议类型筛选 | 筛选栏 | — | All / 5 种类型 | API-20 | 否 | — |
| 状态筛选 | 筛选栏 | — | All statuses / Passed / Pending（按设计稿，不按 Pending 原因筛，7 #Q25d） | API-20 | 否 | — |
| 时间范围 | 筛选栏 | — | From / To，可 Clear；按会议日期 | API-20 | 否 | — |
| 分页 | 表格下方 | — | 对齐 Knowledge Base（第 5 节开头，7 #Q43）：默认每页 10 条，可选 10 / 20 / 50；默认会议时间倒序 | API-20 | 否 | — |
| 会议名 / Review | 表格行 | — | 跳 PG-02 | — | 否 | — |

### 4.3 PG-01b Configuration 与 PG-01b1 Remove 确认框

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 加载 | — | — | 显示状态点（Unconnected 灰 / Connected 绿 / Failed 红 / Disconnected 灰）、connected as（`UNCONNECTED` 时不显示这一行）、Last sync、key 掩码；`syncing = true` 时同 Sync now 开始轮询 | API-01 | — | — |
| Link | API Key 区 | 未绑定（`UNCONNECTED`），输入框非空 | 校验 key 并保存，成功后切换为掩码 + Remove | API-02 | 否 | 成功 toast；失败在输入框下显示原因（鉴权失败 / 网络不可达），不清空输入、页面状态不变 |
| Sync now | Connection 区 | 已绑定（不是 `UNCONNECTED`）且 `syncing = false` | 触发同步，按钮转「Syncing…」并置灰，每 5 秒轮询 API-01 直到 `syncing = false`，刷新 Last sync 与状态点；离开页面停止轮询 | API-03 → API-01 | 否 | 已在同步时被拒，提示「正在同步」；同步后状态为 Failed / Disconnected 时状态点随之变化 |
| Remove | API Key 区 | 已绑定 | 打开 PG-01b1。没有「更换 key」入口：先 Remove 再 Link（同设计稿） | — | — | — |
| PG-01b1 Remove | 确认框 | — | 清空 key、回未绑定，暂停定时拉取 | API-04 | 本身即二次确认 | 成功关闭并刷新；失败提示 |
| PG-01b1 Cancel | 确认框 | — | 关闭 | — | — | — |

### 4.4 PG-01c Cheat Sheet、PG-01c1 名册弹框、PG-01c2 专长标签下拉

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 逾期提示条 | 列表上方 | `overdueCount > 0` | 显示「N entries are overdue and flagged "needs review".」 | API-05 | — | — |
| 搜索 | 筛选栏 | — | 匹配姓名、邮箱、组织、专长标签与 Area of expertise | API-05 | 否 | 无结果：「No registry entries match this search.」 |
| Role 筛选 | 筛选栏 | — | All roles / 6 种角色 | API-05 | 否 | — |
| 分页 | 表格下方 | — | 对齐 Knowledge Base（第 5 节开头，7 #Q43）：默认每页 10 条，可选 10 / 20 / 50 | API-05 | 否 | — |
| Add external party | 列表右上 | — | 打开 PG-01c1（新增，Name 可填） | — | — | — |
| Edit | 行内 | — | 打开 PG-01c1（编辑，带当前状态那一版，Name 只读） | — | — | — |
| History | 行内 | — | 跳 PG-04 | — | — | — |
| Email Domain：加载 | Email Domain 块 | — | 列出本租户的邮箱域名（`@domain`），不分页 | API-10 | — | — |
| Email Domain：Add（按钮或 Enter） | Email Domain 块底部 | 输入去 `@`、转小写后格式合法且不重复（前端先校验，重复提示「This domain is already added.」；公共邮箱域名由后端判） | 把新域名并进列表，整份提交 | API-11 | 否 | 成功刷新列表；后端拒绝时在输入框下显示原因（重复 / 公共邮箱域名 / 格式） |
| Email Domain：Edit → Save / Cancel | 行内 | Save 在输入合法时可点；Enter 保存、Esc 取消 | 替换该项后整份提交 | API-11 | 否 | 同上 |
| Email Domain：Delete | 行内 Delete 按钮 | — | 去掉该项后整份提交 | API-11 | 否（同设计稿） | 成功刷新 |
| PG-01c1 字段 | 弹框 | Name*（新增可填、编辑只读；新增时失焦调 API-41 查重，重名时在姓名下方提示「A Cheat Sheet entry with this name already exists. It will be saved as Tom1.」，不拦提交，7 #Q46）、Email(s)*（至少一个，格式校验，可 `+ Add another email` / ×）、Organization*、Role*（新增时为空）、Expertise tags（选填，7 #Q24d）、Area of expertise（≤2048 字）、Validity period From* / To（可空） | 改动后才显示必填提示；提示文案 `"From" is required. Leave "To" empty to show the period as open-ended.` | API-41（Name 失焦） | — | — |
| PG-01c1 Confirm（新增） | 弹框底部 | 必填齐 | 弹「Confirm submission」：姓名提交后不可修改；Yes, submit 后提交 | API-06 | 是 | 成功关闭、刷新列表；重名时以 API-06 自动加后缀后的姓名保存（以保存时为准，7 #Q46）；邮箱已登记在别人名下时在弹框内显示原因、不关窗（7 #Q49） |
| PG-01c1 Confirm（编辑） | 弹框底部 | 必填齐 | 提交；什么都没改也可提交，即记一次复核（9.7.5） | API-07 | 否 | 成功关闭、刷新列表 |
| PG-01c1 Cancel | 弹框底部 | — | 关闭，不保存 | — | — | — |
| PG-01c2 加载 | 打开下拉时 | — | 按 `sort_no` 列出字典 | API-12 | — | — |
| PG-01c2 新增标签 | 下拉底部的「Add a new tag…」输入框（同设计稿） | 输入值不在字典里（不区分大小写）；已存在的直接选中 | 加入字典并选中 | API-13 | 否 | 重名提示已存在 |
| PG-01c2 删除 | 选项悬停时出现的删除按钮 | `deletable = true`（预置的、用过的、被未处理专家标记引用的不显示） | 从字典删除 | API-14 | 否 | 被拒时提示原因 |

### 4.5 PG-01d Raw Data

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 搜索 | 工具栏 | — | 匹配会议 id、标题、参会人 | API-15 | 否 | 无结果：有筛选时「No meetings match your search and filters.」，只搜索时「No meetings match your search.」 |
| 日期范围 | 工具栏 | — | From / To，可 Clear | API-15 | 否 | — |
| 参会人多选 | 工具栏 | — | 选项来自 API-16，命中任一即列出，可 Clear | API-16、API-15 | 否 | — |
| 有效性筛选 | 工具栏 | — | All tags / Invalid only / Hide invalid | API-15 | 否 | — |
| Clear filters | 工具栏 | 有筛选生效时显示 | 清空全部筛选 | API-15 | 否 | — |
| 列头排序 | 表头（除操作列外 7 列） | — | 首次升序、再点降序；默认 Date 降序 | API-15 | 否 | — |
| 分页 | 表格下方 | — | 对齐 Knowledge Base（第 5 节开头，7 #Q43）：默认每页 10 条，可选 10 / 20 / 50 | API-15 | 否 | — |
| Raw transcript | 行内 | — | 跳 PG-03 | — | — | — |
| Invalid 徽标 | 行内 | `invalid = true` | 悬停说明 | — | — | — |
| 视图记忆 | — | — | 搜索、筛选、排序、页码存 sessionStorage，从 PG-03 返回时恢复（读写包在 try/catch 里，取不到就用默认值） | — | — | — |

公司端同一张表：只列本人受邀的会议，参会人选项也只来自这些会议，没有租户下拉。

### 4.6 PG-02 会议 Review 详情

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 加载 | — | — | 会议信息卡、参会人、矩阵一次取回 | API-21 | — | 会议不存在或无权：显示「Meeting not found」 |
| 待识别子原因 | Scrub Status 旁 | `Pending` 待识别 | 显示卡在哪一步、去哪处理（9.4.2）；待确认专家显示剩余未处理标签数，或「只差应用」 | API-21 | — | — |
| AI Meeting Type 下拉 | 信息卡 | — | 只改页面上的类型；选 `Unknown` 时 Start Extraction 置灰、Confirm & Apply 激活 | — | 否 | — |
| Company：删除 chip / 下拉添加 | 信息卡 | 候选来自 API-32（不在营的公司带状态标注，GS → 创始人时置灰不可选）；GS → 创始人多于一家时提示「GS → 创始人会议只能保留一家公司」 | 只改页面上的公司；GS → LP 的增删只激活 Confirm & Apply，其余类型激活 Start Extraction | API-32 | 否 | — |
| Portfolio 多选 | 信息卡 | GS → 创始人只读，显示公司所属 Portfolio；其他类型可选 | 只改页面上的标记，激活 Confirm & Apply | API-32 | 否 | — |
| 点参会人 chip | Participants | 按 `clickAction`：带 Possible expert 的先开 PG-02c（标签处理完后按是否入册开 PG-02a / PG-02b）；平台用户不弹框；名册已有 → PG-02b；未识别、AI 推断未入册、按域名判出未入册 → PG-02a；未对上的说话人 → 两个操作：指定为参会人（PG-02d）、登记进名册（PG-02a） | 打开对应弹框 | 数据来自 API-21 | — | — |
| AI inferred 悬停 | chip | 徽标含 AI inferred | 显示 `aiEvidence` | API-21 | — | — |
| 证词补抽状态 / Retry | chip 与矩阵证词区 | `RUNNING` 显示「证词补抽中」；`FAILED` 显示「证词补抽失败 · Retry」 | Retry 重新补抽，之后每 5 秒轮询 API-21 | API-29 → API-21 | 否 | 被拒时提示原因 |
| Start Extraction | 页头右上 | 按 9.5.1：必填齐（类型不是 `Unknown`；参会人里没有 Unidentified、没有未对上的说话人；GS → 创始人恰好一家公司），并且——已提取过的会议要页头有未提交的类型或公司改动（GS → LP 的公司改动与 Portfolio 改动不算）或 `participantsChanged`；待识别、提取作废、P1 / P8 失败的会议必填齐即可。提取或补抽进行中置灰 | 提交页头的类型与公司，整场下线并后台提取；按钮显示进行中，每 5 秒轮询 API-21 直到 `extractionStatus` 不是 `RUNNING`，再刷新整页；进页面时若已在提取或补抽，同样开始轮询，轮询拿到新 `updatedAt` 时保留页面上未提交的改动 | API-22 → API-21 | 否（设计 9.9.4：不弹确认框） | 成功 toast「Extraction started」；作废后页头显示「提取失败」，按钮恢复可点 |
| 编辑 Content | 矩阵每行 | 来源行只读；该行发言人证词补抽中时不可编辑 | 编辑后该行琥珀高亮，出现 Save / Cancel | — | — | — |
| 行内 Save | 矩阵行 | 该行有改动；摘要行不超过 150 个英文单词（前端计数，超长置灰并提示） | 调 API-24：返回已落库即完成；返回清洗结果则弹出 PG-02e 回显（删去的行及原因、替换的实体），管理员确认后带 `originalContent` 再调一次，或返回继续改 | API-24 | 有命中时回显确认 | 成功 toast「Content saved」；被拒提示原因 |
| 行内 Cancel | 矩阵行 | 该行有改动 | 还原该行 | — | — | — |
| Authorize 勾选 | 矩阵行 | 摘要行：同一（去向, 公司）的正文行未勾选时置灰，悬停说明摘要随正文生效（7 #Q42） | 只改页面上的勾选，激活 Confirm & Apply；取消勾选正文行时，同组摘要行随之取消 | — | — | — |
| Discard Changes | 页面底部 | 有未提交的页头类型 / 公司、勾选或 Portfolio 改动 | 还原这些改动以及编辑中未保存的行（可用条件比 9.6.5 收窄：只在有未提交改动时激活）；不撤销已 Save 的内容、名册写入、补抽结果与已点过的 Start Extraction（9.6.5） | — | 否 | — |
| Confirm & Apply Routing | 页面底部 | 按 9.6.5 按钮状态表（自下而上优先；改为 Unknown 即激活，只在提取或证词补抽进行中置灰，7 #Q25e），置灰时提示原因（如「还有 N 个建议标签未处理」）；有行在编辑未保存时先提示该行 Save 或 Cancel | 一次提交勾选、Portfolio、改 `Unknown`、GS → LP 的公司增删；返回 40903 时弹二次确认框逐条列出 `warnings`（按当前参会人判定的类型与当前类型不同，带建议类型；GS → 创始人会议有 Founder 的组织 / 所属公司与关联公司对不上），确认后带 `confirmWarnings=true` 重提，取消则不提交（7 #Q48） | API-23 | 类型改为 `Unknown` 时弹 PG-02f（本方案）；返回 40903 时弹上述二次确认 | 成功 toast「Routing applied」，状态刷新；被拒提示原因 |
| 面包屑 | 页头 | — | 回 PG-01 Summary Records Tab，`org` 取该会议的租户 | — | — | — |

### 4.7 PG-02a / PG-02b / PG-02c / PG-02d 会议页弹框

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| PG-02a 字段 | 弹框 | 用 API-21 的 `registryForm` 预填；Name 可改，失焦调 API-41 查重，重名时在姓名下方提示将保存为的姓名（同 PG-01c1，7 #Q46）；来源是参会人时本场邮箱锁定（不可删改，可加别的邮箱）；未对上的说话人：Name 取说话人名、Email 为空且必填、不锁；Validity From 默认会议日期、To 空，有效期必须包含会议日期，不含时在字段下提示并不能提交（7 #Q44）；其余字段与校验同 PG-01c1 | — | API-12（标签）、API-41 | — | — |
| PG-02a Confirm | 弹框底部 | 必填齐、有效期包含会议日期 | 弹「Confirm submission」→ Yes, submit 后提交 | API-25 | 是 | 成功关闭、刷新 API-21；返回 `suggestedType` 时提示「已可判定为 X 类型，是否应用」，应用只是把页头类型设为 X（有 `suggestedCompany` 时一并加进页头 Company），仍需点 Start Extraction；邮箱是本租户 LG 用户时提示「按平台用户识别，不进名册」；返回 `registryMatchedName` 时提示「已按名册中的 X 识别，未新建」（7 #Q49）；42200 时在弹框内显示原因、不关窗 |
| PG-02b 字段 | 弹框 | 用 API-21 的 `registryForm` 预填（会议日期当天生效的那条 T2，有效期为 T2 原有效期）；只有 Name 只读；本场邮箱锁定（不可删改，可加别的邮箱；T2 里没有本场邮箱时已补进）；有效期可改，必须包含会议日期（7 #Q44） | — | API-12 | — | — |
| PG-02b Confirm | 弹框底部 | 必填齐、有效期包含会议日期；首轮未完、提取或证词补抽进行中置灰（7 #Q44） | 调 API-07（带 `sourceMeetingId`，`{id}` 为 `versionId`）追加一条完整新版本，成功后关窗、调 API-28 同步本场，再刷新 API-21；没有任何改动时 Java 不写，照常同步 | API-07 → API-28 → API-21 | 否 | API-28 返回 `testimonyBackfillStatus = RUNNING` 时显示「证词补抽中」并轮询；返回 `suggestedType` 时提示同 PG-02a；返回 40901 时提示稍后重试（同步可重复调用） |
| PG-02c 内容 | 弹框 | 上半按标签分组列出主张与依据（推测依据区块）；去掉逐标签按钮，建议标签预填进 Expertise tags 标签栏（区分显示为「建议」标签，样式开发定）：`resolvedAs = DECLINED`（已在拒绝名单）的不预填，`ACCEPTED`（已在 T2 里）的就是普通已有标签；留下即同意、删掉即驳回（7 #Q45）。登记字段：已在册的人用 T2 预填、只有 Name 只读；未入册的外部人为完整表单（同 PG-02a），Name 可改、失焦调 API-41 查重；LG 平台用户 Name 取账号姓名、只读，Role 预填平台账号推出的角色、可改（7 #Q47）。本场邮箱锁定（不可删改，可加别的邮箱）；有效期可改、必须包含会议日期，已在册的预填 T2 原有效期，新登记默认 From = 会议日期、To 空（7 #Q44） | — | API-12、API-41 | — | — |
| PG-02c Save | 弹框底部 | 首轮未完、提取或证词补抽进行中置灰（7 #Q44）；建议标签全删且此人未登记时不校验登记字段（只写拒绝名单、不建条目），否则登记字段必填齐、有效期包含会议日期（7 #Q45） | 调 API-08（`suggestedTags` 为本次打开时的建议标签，`entry` 为登记字段，`baseVersionId` 为 `versionId`），Java 同一事务写名册与拒绝名单；成功后关窗、调 API-28（新登记带 API-08 返回的最终姓名），再刷新 API-21 | API-08 → API-28 → API-21 | 未入册的人要新建名册时弹「Confirm submission」（9.5.6），否则否 | API-28 返回 `testimonyBackfillStatus = RUNNING` 时显示「证词补抽中」并轮询；返回 `suggestedType` 时提示同 PG-02a；返回 40901 时提示稍后重试；新登记的邮箱已登记在别人名下时在弹框内显示原因、不关窗（7 #Q49） |
| PG-02c Cancel / 关闭 | 底部 Cancel、右上 × | — | 不保存、不调接口，什么都不写（识别出的参会人数据只在本会议内使用，7 #Q44）；徽标保留剩余未处理数 | — | — | — |
| PG-02d 选择参会人 | 弹框 | 下拉列本场参会人；`aiSuggestedMatch` 是本场参会人时预选 | — | — | — | — |
| PG-02d 确认 | 弹框底部 | 选了参会人 | 提交 | API-27 | 否 | 成功关闭、刷新 API-21；`suggestedType` 同上 |
| 各弹框 Cancel | 弹框底部 | — | 关闭，不保存 | — | — | — |
| 专长标签维护 | Expertise tags 下拉 | 同 PG-01c2 | 新增 / 删除标签；调 API-12 / 13 / 14 时带 API-21 返回的会议所属 `organizationId` | API-13、API-14 | 同 PG-01c2 | 同 PG-01c2 |
| PG-02e 确认保存 / 继续修改 | 清洗回显弹框底部 | — | 确认保存：带 `originalContent` 再调一次；继续修改：关闭弹框、回到该行 | API-24 | — | 同行内 Save |
| PG-02f Apply / Cancel | 改 Unknown 确认框底部 | — | Apply：提交；Cancel：关闭 | API-23 | 本身即二次确认 | 同 Confirm & Apply |

### 4.8 PG-03 原文页、PG-04 Role History

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| PG-03 加载 | — | — | 页头与首批句子 | API-17、API-18 | — | 无权或不存在都显示设计稿的未找到态（「Transcript not found」「No ingested meeting matches this ID.」「Back to Fireflies Meeting Data」），不区分两者（本方案：不暴露会议是否存在）；转录为空时正文显示「No transcript content.」 |
| PG-03 后台续加载 | 正文底部 | `hasMore = true` | 首批显示后自动连续取下一批直到取完（每批 500 句），期间底部显示「Loading the rest of the transcript…」 | API-18 | — | 某批失败即停，底部显示 Retry，从失败的批次接着取 |
| PG-03 面包屑 / ← Back | 页头、页尾 | — | 第一级「Fireflies Management」回 PG-01 默认 Tab；第二级「Fireflies Raw Data」与 ← Back 回 Raw Data Tab（都带 `org`；公司端回自己的 Raw Data） | — | — | — |
| PG-04 加载 | — | — | 此人全部版本 | API-09 | — | 不存在或无权（PM）：「Registry entry not found」 |
| PG-04 面包屑 | 页头 | — | 第一级回 PG-01 默认 Tab，第二级「Cheat Sheet」回 Cheat Sheet Tab（都带 `org`） | — | — | — |

### 4.9 PG-05 Goldie Base

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 进入 / 切换 Tab | Tab 栏 | 管理端 4 个；公司端 Company Admin 有 Knowledge Base 与 Memory Settings；公司端普通用户只有 Knowledge Base，不显示 Tab 栏 | 改 URL `?tab=`；地址里的 Tab 没有权限时回落到 Knowledge Base；管理端一律取组织树第一个叶子租户（7 #Q32） | API-19、API-39 | 否 | — |
| 侧栏 / 底栏入口 | 门户侧栏、手机端底栏 | — | 合并后的 Goldie Base 入口高亮；Conversation history 回 `/askGoldie` | — | — | — |
| KB：搜索与筛选 | PG-05a 筛选栏 | — | 保持现有：只按文件名搜，筛选项不变，不加 Source 筛选（7 #Q24a） | API-33、API-34 | 否 | — |
| KB：下载 | PG-05a 行内 | 现有规则；Fireflies 行按 API-35 新分支（响应带 `content` 时前端用 Blob 下载，3.6） | 下载 | API-35 | 否 | 失败提示 |
| KB：删除 | PG-05a 行内 | Fireflies 行不显示 | 现有行为 | API-36 | 是（现有） | 现有 |
| KB：Source 链接 | Source 列 | Fireflies 行，且后端返回可点 | 跳 PG-03；不可点时显示纯文字 | — | — | — |
| KB：基金标签（PG-05a1） | Portfolio 列 | 管理端 Fireflies 知识库正文行；候选来自 API-32 | 多选，下拉只回显 `fundTagIds`（手动选过的），变化即提交 | API-31（`fundTagIds`） | 否 | 失败还原并提示 |
| Memory：File Scope | PG-05b 筛选栏 | 管理端；公司端不显示 | All Files / Company Memory / Portfolio Memory / Fireflies Memory（7 #Q24b） | API-37 | 否 | — |
| Memory：搜索、公司筛选 | PG-05b 筛选栏 | 公司筛选只在管理端 | 现有行为：按摘要全文与文件名搜索，不加设计稿的公司匹配（7 #Q25c） | API-37 | 否 | — |
| Memory：查看详情 | PG-05b 行 | — | 现有详情弹框；会议摘要的标签并排显示层徽标 + Fireflies Memory + Meeting Summary | — | — | — |
| 跨公司 / 证词：搜索 | PG-05c / PG-05d 工具栏 | — | 匹配内容与会议名称，证词另匹配说话人姓名（7 #Q25b） | API-30 | 否 | 无结果显示空态 |
| 跨公司 / 证词：时间范围 | 工具栏 | — | 按会议日期区间 | API-30 | 否 | — |
| 跨公司 / 证词：分页 | 列表下方 | — | 对齐 Knowledge Base（第 5 节开头，7 #Q43）：默认每页 10 条，可选 10 / 20 / 50 | API-30 | 否 | — |
| 跨公司 / 证词：会议名 | 卡片 | `canOpen`（PGM / SA）可点，PM 为纯文字 | 跳 PG-02 | — | — | — |
| Play candidate 开关 | 每条内容旁 | `canTogglePlaybook`（PGM / SA）可切换；PM 只读显示 | 切换即提交 | API-31（`inPlaybook`） | 否 | 失败还原并提示 |

### 4.10 按钮 ↔ 接口对账

- 每个按钮引用的接口都在第 3 节清单里；第 3 节对账表里属于各页面的接口，本节都有对应的加载时机或操作。
- 没有按钮直接触发的接口：API-38（Ask Goldie 对话），见 3.5；API-08 改为 PG-02c Save 直调、API-26 已删除（7 #Q44）；API-40 已不再使用（7 #Q41）。
- 本方案新增、设计没写的交互：类型改为 `Unknown` 并应用时二次确认（PG-02f）；原文页与会议详情对「无权」与「不存在」显示同一提示；PG-02c 新建名册时弹 Confirm submission；Discard 只在有未提交改动时激活（比 9.6.5 收窄）；证词补抽中该发言人的证词行不可编辑。

## 5. 页面布局

设计稿为 Lovable 项目 FFL（commit `76cc767`），下文「设计稿」后的路径相对其 `src/`。web 用 antd 4.9.2（没有 `items` API，Tab 用 `Tabs.TabPane`），优先复用：下沉后的组织树下拉（原 ERL `OrganizationSelect`，2.「入口与守卫」）、`src/components/MultiSelectDropdown`、`common/breadCrumbs.tsx`、`common/SuspendClose.tsx`、`FileTypeIcon`、askGoldie 域内的 `orgScope.ts`、`MultiSelectFilter.tsx`；原文页整篇直接渲染、不用虚拟滚动（7 #Q29）。

设计稿已有的标题、按钮名、文案与控件样式（如 Sync now 是文字链接、Tab 名带 Fireflies 前缀、弹框标题与提示文案）照设计稿，下文只记有意偏离与设计稿没画到的地方。日期时间一律固定 UTC 显示，格式照设计稿（7 #Q25f）：日期时间 `Jul. 15, 2026 at 10:52 a.m. UTC`，只有日期的 `Jul. 15, 2026`，只有时刻的 `10:52 a.m. UTC`（月份缩写带点、日不补零、12 小时制补零）；会议日期按 UTC 自然日；逐句时间点仍为 `[hh:mm:ss]`。适用于本功能新增的页面与 Tab；Knowledge Base、Memory Settings 是现有页，日期列保持现有格式。下文线框里的日期只示意位置。

通用状态：加载用 antd `Spin`（表格用自带 loading）；空列表用 `Empty` 加设计稿文案；接口失败在区域内显示错误与「重试」，不弹全局横幅（这些接口加进 `request.ts` 的 `isInlineErrorEndpoint`）；无权限用 antd `Result`（403）。

分页（用户决定 2026-10-28，7 #Q43）：Summary Records、Cheat Sheet、Raw Data 与 Goldie Base 两个新 Tab 一律对齐现有 Knowledge Base 的分页样式（`KnowledgeBasePage.tsx` 的 `pagination`），不看设计稿——默认每页 10 条，可选 10 / 20 / 50；常显总数 `${start} - ${end} of ${total} items`，记录少时也不隐藏，不开跳页；手机端隐藏条数选择、用小号。下文线框里的「分页（10 / 页）」只示意位置。

### 5.1 PG-01 Fireflies Management

参照设计稿：`routes/index.tsx:150-206`（Tab 容器）

```
┌──────────────────────────────────────────────────────────────┐
│ Fireflies Management                        [组织树下拉 ▾]   │
├──────────────────────────────────────────────────────────────┤
│ Summary Records ● │ Configuration │ Cheat Sheet │ Raw Data    │
├──────────────────────────────────────────────────────────────┤
│ 当前 Tab 内容（5.2~5.5）                                       │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 标题与面包屑 | `breadCrumbs` | 「Fireflies Management」 |
| 组织树下拉 | 下沉后的组织树下拉 | 根下有子组织才显示，公司端不显示 |
| Tab 栏 | `Tabs.TabPane` | Summary Records 标题旁红点；公司端只有 Raw Data，不渲染 Tab 栏 |

状态：PM 进入显示 403；公司端直接显示 Raw Data 内容。与设计稿的差异：组织树下拉为 7 #Q17 新增，设计稿没有。

### 5.2 PG-01a Summary Records

参照设计稿：`components/summary-records-tab.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ Fireflies Summary Records                                    │
│ [Search by meeting title or company] [类型 ▾] [状态 ▾] [时间 ▾]│
├──────────────────────────────────────────────────────────────┤
│ Meeting           │ Time        │ AI Meeting Type │ Companies │ Status   │       │
│ 标题（链接）       │ Jul 15, 2026│ [GS → Founder]  │ TechVision│ ◷ Pending│Review │
│ #FF-xxx · 52 min  │ · 10:00 AM  │                 │           │ 待审核    │       │
├──────────────────────────────────────────────────────────────┤
│                                          分页（10 / 页）       │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 筛选栏 | `Input.Search`、`Select` ×2、时间区间浮层（`DatePicker.RangePicker`，标签显示 All time / From X / X – Y） | 类型：All meeting types + 5 种；状态：All statuses / Passed / Pending（7 #Q25d） |
| 表格 | antd `Table`（服务端分页） | Meeting（标题链接 + `#<fireflies_id> · <n> min`）、Time（单列合并）、AI Meeting Type（蓝标签，Unknown 灰）、Companies（逗号分隔，超宽省略号）、Status（✓ Passed 绿 / ◷ Pending 红，旁注原因，悬停显示状态说明）、Review 链接 |

状态：空列表「No meetings match your search.」。与设计稿的差异：设计稿没有分页，分页对齐 Knowledge Base（见本节开头，7 #Q43）；Status 的原因旁注与悬停说明按设计 9.4.2（设计稿只有两态说明）；GS → LP 没有公司时 Companies 列显示「Fund-level」（同设计稿）；状态筛选照设计稿只分 Passed / Pending，三种 Pending 原因只在 Status 列旁注（7 #Q25d）。

### 5.3 PG-01b Configuration 与 PG-01b1

参照设计稿：`routes/index.tsx:208-326`

```
┌────────────────────────── Connection ─────────────────────────┐
│ Fireflies workspace connected as <account_email>              │
│ ● Connected     Last sync: Jul 15, 2026 · 10:52 AM  [Sync now]│
├────────────────────────── API Key ────────────────────────────┤
│ 未绑定： 说明文案                                               │
│          [Enter your Fireflies API key        ] [Link]        │
│ 已绑定： Current key  [••••••••••••a3f9]          [Remove]    │
└───────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| Connection | 状态点 + 文案 + `Button` | 状态点颜色按 9.2.4；从未成功同步时 Last sync 显示 `—`；Sync now 同步中显示「Syncing…」并置灰 |
| API Key | `Input.Password`（未绑定）/ 只读掩码框（已绑定）+ `Button` | 未绑定时的说明文案用需求原文「Link your Fireflies API key to enable automatic meeting ingestion.」；Link 失败的原因显示在输入框下方；掩码固定 8 个圆点 + 后 4 位 |
| PG-01b1 | `Modal.confirm` | 标题「Remove API key?」，正文「Fireflies will be disconnected and meetings will stop syncing until a new key is linked.」，按钮 Cancel / Remove（红色） |

与设计稿的差异：key 输入框用 Password 类型（设计稿是明文输入框）；掩码圆点数固定（设计稿按 key 长度出圆点，会暴露长度）；`UNCONNECTED` 时不显示 connected as 一行；设计稿 Connection 区的文案、状态与 Last sync 写死，Sync now 没有行为，这里都接真实数据；设计稿没画 Failed / Disconnected 的状态点与「未连接时 Sync now 置灰」，按 9.2.4 补。

### 5.4 PG-01c Cheat Sheet、PG-01c1、PG-01c2

参照设计稿：`routes/index.tsx:662-858`（列表与 Email Domain 块 `:332-459`）、`:860-1096`（PartyEditor）、`components/expertise-select.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ External Parties Registry                [Add external party]│
│ N entries are overdue and flagged "needs review".            │
│ [Search by name, email, organization or expertise] [Role ▾]  │
├──────────────────────────────────────────────────────────────┤
│ Name        │ Email(s)    │ Organization │ Role │ Expertise tags │ Validity period │      │
│ Jane Doe    │ jane@a.com  │ Acme Capital │ [LP] │ [Multiples]    │ Aug 2, 2026 –   │History│
│ From FF ... │ j@b.com     │              │      │                │ present [Needs  │ Edit │
│             │             │              │      │                │ review]         │      │
├──────────────────────────────────────────────────────────────┤
│                                          分页（10 / 页）       │
├────────────────────────── Email Domain ───────────────────────┤
│ Add the email domains used to identify internal participants.│
│ @gst.com                                      Edit  Delete   │
│ [e.g. goldie.vc                       ] [Add]                │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 列表 | antd `Table`（服务端分页） | Name（审核会议时导入的下方加 `From FF Summary Records` 标签）、Email(s)（纵向全列，实在放不下时省略号、悬停看全）、Organization、Role（蓝标签）、Expertise tags（灰小标签，换行）、Validity period（`Aug. 2, 2026 – present`，逾期加琥珀 `Needs review`）、History / Edit |
| Email Domain 块 | 列表 + 行内 `Input` + `Button` | 不分页；Edit 时该行变输入框 + Save / Cancel |
| PG-01c1 | `Modal` + `Form` | 字段与校验见 4.4；Name 编辑时置灰，新增时重名提示显示在 Name 下方（API-41，7 #Q46）；Email(s) 多行，`+ Add another email`；Role 为 6 项 `Select`；Expertise tags 用 PG-01c2；Area of expertise 为 `TextArea`；Validity period 为两个 `DatePicker`（To 可清空）；新增的 Confirm 前弹 `Modal.confirm`「Confirm submission」 |
| PG-01c2 | 多选 `Select`（`mode="multiple"`，`dropdownRender` 底部加「Add a new tag…」输入框，可删的选项悬停显示删除，同设计稿 `expertise-select.tsx`） | 种子 5 项在前，新增的按添加顺序在后 |

与设计稿的差异：设计稿 Expertise tags 必填，按设计维持选填（7 #Q24d）；新增时 Role 为空（设计稿默认 LP，不沿用：角色影响会议类型判定，设计 9.7.4）；逾期提示条设计稿只算了逾期数、没有渲染，按设计 9.7.3 显示；Needs review 按设计 9.7.5 为 90 天（设计稿常量 92）；搜索另匹配 Area of expertise（设计 9.7.3）；设计稿表格只显示固定 5 个标签，这里显示该人全部标签；设计稿没有分页，分页对齐 Knowledge Base（见本节开头，7 #Q43）。

### 5.5 PG-01d Raw Data

参照设计稿：`routes/index.tsx:481-660`、`components/raw-data-filters.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ [Search by meeting ID, title or participant] [日期 ▾] [参会人 ▾] [有效性 ▾] Clear filters │
├──────────────────────────────────────────────────────────────┤
│ Meeting ID ↕ │ Title ↕ │ Date ↕ │ Time ↕ │ Duration ↕ │ Participants ↕ │ Ingested at ↕ │              │
│ FF-2026...   │ ...     │Sep 15, │09:30 AM│ 58 min     │ Alice, Bob,... │ Sep 15, 2026  │Raw transcript│
│              │         │2026    │        │            │                │ · 10:31 AM    │ [Invalid]    │
├──────────────────────────────────────────────────────────────┤
│                                          分页（10 / 页）       │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 工具栏 | `Input.Search`、日期区间浮层、`MultiSelectDropdown`（参会人）、`Select`（All tags / Invalid only / Hide invalid）、Clear filters 链接 | 有筛选生效时才显示 Clear filters |
| 表格 | antd `Table`（服务端分页、服务端排序） | 7 列可排序；Participants 全部展示不截断；Invalid 徽标灰色，悬停「Automatically filtered out: no substantive content. No action needed.」（设计稿原文含 too short，按设计 9.3.4「不看长短」不沿用） |

状态：空结果有筛选时「No meetings match your search and filters.」，只搜索时「No meetings match your search.」。公司端同一布局，没有租户下拉。设计稿没有分页，分页对齐 Knowledge Base（见本节开头，7 #Q43）。

### 5.6 PG-02 会议 Review 详情与弹框

参照设计稿：`routes/meetings.$id.tsx:896-1237`（页面）、`:196-443`（AssignExternalPartyModal）、`:454-672`（ExpertSuggestionModal）、`lib/routing-content.ts`

```
┌──────────────────────────────────────────────────────────────┐
│ Fireflies Management > Meeting Detail                        │
│ <会议标题>                                                     │
│ Fireflies Summary Records > Meeting Detail                    │
├──────────────────────────────────────────────────────────────┤
│ 提示文案（待识别：补齐类型、公司、参会人后可提取）    [Start Extraction] │
│ Date …  Duration …  Fireflies ID #…  Scrub Status ◷ Pending · 待识别（子原因）│
│ AI Meeting Type* [GS → Founder ▾]                              │
│ Company*  [TechVision ×]  [Company ▾ 可搜索]                    │
│           Matched via jane@techvision.io (LG company user)     │
│ Portfolio [Fund I ×] [Portfolio ▾]                             │
│ Participants  [Sarah · GS (PM)] [James · TechVision (Founder) Possible expert] │
│               [Michael · — (Unidentified) ●] [David · 97 sentences (Unmapped speaker) ●] │
├────────────────────── Content Routing Matrix ─────────────────┤
│ Content                         │ Visible to        │ Authorize │
│ [textarea：摘要]                 │ Founder, PM & PGM │    ☑      │
│                      [Cancel][Save]（有改动时出现）              │
│ [textarea：KB 正文]              │ Founder, PM & PGM │    ☑      │
│ Source: …（证词的只读来源行）      │                   │           │
│ [textarea：证词署名版]            │ Expert testimony (Portfolio) ☑│
│ [textarea：跨公司内容]            │ Cross company     │    ☐      │
├──────────────────────────────────────────────────────────────┤
│                    [Discard Changes] [Confirm & Apply Routing]│
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 页头 | `breadCrumbs`、提示文案、`Button`（Start Extraction） | 提取进行中按钮显示进行中并置灰 |
| 会议信息卡 | 描述列表 + `Select`（类型）+ `Tag`（公司 / Portfolio，可关闭）+ 可搜索 `Select`（公司、Portfolio 候选） | 每家公司下方一行识别依据（9.5.3 文案）；未采纳的候选是否展示以设计稿为准（设计稿未画，先不展示）；GS → 创始人的 Portfolio 只读 |
| 参会人 | 胶囊 `Tag` | 按身份着色（GS 蓝、Founder 橙、外部紫、未识别与未对上的说话人灰 + 红点）；徽标 Expert / Possible expert / AI inferred（悬停显示依据）；证词补抽中 / 失败 · Retry 显示在胶囊旁 |
| Content Routing Matrix | 自写表格：每行 `TextArea` + Visible to 文本 + `Checkbox` | 改动行琥珀边框并出现 Save / Cancel；证词行的来源行只读显示在正文上方；跨公司与证词行另以灰色小字只读显示出处时间点 `[hh:mm:ss]`（`sourceTimestamp` 为空时不显示，7 #Q26）；GS 内部 / Partner 按公司分组、行标注公司名；GS → LP 标注机构层；Pending 会议首次提取前矩阵为空，显示「提取后在此显示」；提取进行中显示「提取中」占位，作废后显示「提取失败，补齐后点 Start Extraction」；`projectionStatus = FAILED` 的行显示红色标记，悬停说明投影失败；摘要行的 `Checkbox` 在同组正文行未勾选时置灰（4.6，7 #Q42）；证词区按 `speakerParticipantId` 显示该发言人的「证词补抽中」/「证词补抽失败 · Retry」。Visible to 文案：`KB_APP` → Founder, PM & PGM；`TESTIMONY_SIGNED` → Expert testimony (Portfolio)；`TESTIMONY_ANON` → Expert testimony (Founder)；`CROSS_COMPANY` → Cross company（以上同设计稿）；`KB_ADMIN` → PM & PGM、`FUND_LEVEL` → PM & PGM (fund level)（设计稿没有这两类，本方案） |
| 底部按钮 | `Button` ×2 | 置灰时悬停显示原因 |
| PG-02e 行内 Save 的清洗回显 | `Modal` | 列出删去的行及原因、替换的实体，按钮「确认保存」/「继续修改」 |
| PG-02a / PG-02b | `Modal` + `Form`（同 PG-01c1） | 标题 `Assign new external party — <name>` / `Edit external party — <name>`；PG-02b 的 Name 置灰，PG-02a 的 Name 下方显示重名提示（API-41）；本场邮箱那一行锁定（不可删改、不显示 ×），可加别的邮箱；设计稿这两个弹框没有 Area of expertise，按设计 9.5.5 加上（同 Cheat Sheet 弹框）；有效期不含会议日期时在字段下提示并不能提交（7 #Q44） |
| PG-02c | `Modal`：上半为按标签分组的主张与依据（带时间点），下半为登记字段；不设逐标签按钮行，建议标签预填在 Expertise tags 标签栏里，区分显示为「建议」（样式开发定） | 标题 `Possible expert — <name>`；已驳回的建议标签不预填，已在 T2 里的按普通标签显示；登记字段与只读规则见 4.7，本场邮箱锁定同 PG-02a / PG-02b；设计稿是整人 Approve / Reject，改为标签栏增删：留下即同意、删掉即驳回（7 #Q45，推翻 #Q24c 的逐标签同意 / 拒绝） |
| Confirm & Apply 二次确认 | `Modal.confirm` | API-23 返回 40903 时弹出，逐条列出 `warnings`，确认后带 `confirmWarnings=true` 重提（7 #Q48）；设计稿没画，文案开发时按设计稿语气定稿 |
| PG-02d | `Modal` + 参会人 `Select` | 设计稿没画，按项目同类弹框样式；标题「Assign speaker — <说话人名>」 |
| PG-02f | `Modal.confirm` | 标题「Revert to Pending?」，正文「All routed content of this meeting will be taken offline and the meeting goes back to Pending.」，按钮 Cancel / Apply |

状态：会议不存在或无权显示「Meeting not found」（设计稿此时显示空字段，不沿用）；矩阵为空的说明见上。

与设计稿的差异：设计稿选公司会替换成只剩一家，按设计 9.5.3 可多选（GS → 创始人只允许一家，多于一家时提示）；设计稿 Start Extraction 对所有类型都要求有公司，按设计 9.5.1 只对 GS → 创始人要求；设计稿没画「未对上的说话人」胶囊与指定弹框、证词补抽状态、清洗回显、置灰原因，按设计补；参会人胶囊：设计稿把 Possible expert 画成整颗橙色胶囊加「— Possible expert?」、所有 Founder 不可点、悬停显示邮箱、没有 Expert / AI inferred 徽标，按设计 9.5.5 / 9.5.6 改为徽标叠加、平台用户不弹框（带 Possible expert 的除外）；PG-02a 的 From 默认会议日期（设计稿为空）；专家确认框加推测依据区块、建议标签预填进标签栏（留下即同意、删掉即驳回，7 #Q45）、未入册者 Name 可改、有 Area of expertise（设计稿没有）；Authorize 勾选激活 Confirm & Apply，内容只经行内 Save 保存（设计稿 Confirm 时整表保存）；Portfolio 在 GS → 创始人时只读（设计稿所有类型可编辑）；改 Unknown 后 Confirm & Apply 激活（7 #Q25e；设计稿把 Unknown 当作必填未填齐而置灰）；跨公司与证词行显示出处时间点（设计稿没有，7 #Q26）。

### 5.7 PG-03 原文页、PG-04 Role History

参照设计稿：`routes/fireflies-transcripts.$id.tsx`、`routes/registry.$id.history.tsx`

```
PG-03                                           PG-04
┌──────────────────────────────────────┐      ┌──────────────────────────────────────────┐
│ Fireflies Management > Raw Transcript│      │ Fireflies Management > Role History       │
│ <会议标题>                            │      │ <Name> — Role History                     │
│ Fireflies Raw Data > Raw Transcript  │      │ Cheat Sheet > Role History                │
├──────────────────────────────────────┤      ├──────────────────────────────────────────┤
│ Date … Time … Duration … Participants│      │ Name │ Email(s) │ Role │ Organization │   │
│ Full Transcript                      │      │ Expertise tags │ Area of expertise │       │
│ [00:00:04] Speaker: text             │      │ Validity period │ Updated by（含日期）       │
│ …（整篇渲染，后台续加载至全篇）        │      ├──────────────────────────────────────────┤
├──────────────────────────────────────┤      │ 最新在前，每行一个完整快照                  │
│ ← Back                               │      └──────────────────────────────────────────┘
└──────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| PG-03 页头 | 文本 | 标题下一行「Raw verbatim transcript — unclassified and unmodified · captured <created_at>」（设计稿没画，按设计 9.3.5 补） |
| PG-03 信息卡 | 描述列表 | Participants 用出席记录姓名，没有则回退受邀邮箱 |
| PG-03 正文 | 逐行直接渲染（不用虚拟滚动，保证浏览器 Ctrl+F、复制、打印覆盖全篇，7 #Q29） | 每行 `[hh:mm:ss] speaker_name: text`，说话人照原样显示；首批到达即显示，其余批次在后台连续加载，期间底部显示 `Spin` 与「Loading the rest of the transcript…」（此时 Ctrl+F 只覆盖已加载部分）；某批失败即停并显示 Retry |
| PG-04 表格 | antd `Table`（不分页） | 按 `valid_from`、`updated_at` 倒序；系统写入的 Updated by 显示 `System (<fireflies_id> import)` |

状态：PG-03 无权或不存在显示「Transcript not found」；PG-04 不存在显示「Registry entry not found」。与设计稿的差异：设计稿 PG-04 不显示 Area of expertise、只显示固定 5 个标签，按设计 9.7.6 显示完整快照与全部标签。

### 5.8 PG-05 Goldie Base

参照设计稿：`routes/knowledge-base.tsx`（Tab 容器 `:815-891`、Knowledge Base `:142-303`、Memory Settings `:577-661`、Cross Company Content `:332-493`（时间筛选 `:332-397`、卡片 `:399-438`）、Expert Testimony `:691-813`）、`routes/ask-goldie.tsx:80-89`（入口）

```
┌────────┬─────────────────────────────────────────────────────┐
│ + Add  │ Goldie Base                                          │
│ History│ All files uploaded through chat attachments are ...  │
│ Goldie │ Knowledge Base │ Memory Settings │ Cross Company Content │ Expert Testimony │
│ Base ● ├─────────────────────────────────────────────────────┤
│        │ [Search …] [时间 ▾]                                  │
│        │ ┌ Meeting source: <会议名>（PGM / SA 可点）          ┐ │
│        │ │ #FF-xxx · Jul 15, 2026 · GS → Founder              │ │
│        │ │ • 内容一                       Play candidate [○ ] │ │
│        │ │ • 内容二                       Play candidate [● ] │ │
│        │ │ （证词另显示 Expert <姓名> [专长标签]）              │ │
│        │ └───────────────────────────────────────────────────┘ │
│        │                                      分页（10 / 页） │
└────────┴─────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 门户外壳 | 现有 `PortalNavSidebar` / `PortalTabBar`（上提到 Goldie Base 页） | 两个入口合并为一个 Goldie Base；两个旧页去掉自带外壳，只保留内容区 |
| Tab 栏 | `Tabs.TabPane` | 顺序按需求：Knowledge Base · Memory Settings · Cross Company Content · Expert Testimony；只有一个 Tab 时不渲染 Tab 栏 |
| Knowledge Base | 现有 `KnowledgeBasePage` 内容区 | 新增 Source 列（`Goldie` / `Fireflies`，Fireflies 可点时为链接）；管理端 Fireflies 正文行的 Portfolio 列变成多选 `Select`（PG-05a1）；Fireflies 行不显示删除；手机端折行同样显示 Source，空 Portfolio / Company 显示 `—`；Fireflies 行的 From Chat 与 Uploaded By 显示 `—`（7 #Q25a） |
| Memory Settings | 现有 `MemorySettingsPage` 内容区 | 摘要按 markdown 渲染：详情弹框渲染，列表两行预览去掉标记（设计第十章 #20 交开发设计定，本方案）；管理端 File Scope 加 Fireflies Memory；会议摘要的 `MemoryMetaRow` 并排显示层徽标 + Fireflies Memory（青色）+ Meeting Summary；公司位为空显示 `—` |
| 两个新 Tab | 卡片列表：相邻的同场行归成一张卡片，`Switch`（Play candidate） | 工具栏：`Input.Search` + 时间区间浮层；证词卡片每条另显示 `Expert <姓名>` 与专长标签（取不到说话人姓名时显示 `Unassigned`，同设计稿；当日没有专长标签时标签区不显示）；会议名 PM 为纯文字；分页按行，同一场会跨页时拆成两张卡片 |

状态：两个新 Tab 空列表用设计稿文案「No content matches your search.」「No expert testimony matches your search.」；公司端打开两个新 Tab 的地址按 403 处理（接口拒绝，Tab 不显示）。与设计稿的差异：设计稿 Knowledge Base 的 Source 筛选、文件名以外的搜索不做（7 #Q24a）；设计稿 Memory File Scope 的 Document Summary 选项不加（7 #Q24b）；设计稿 Play candidate 开关不持久化、专家归属写死，这里接真实数据；设计稿两个新 Tab 没有分页，分页对齐 Knowledge Base（见本节开头，7 #Q43）；卡片元数据加会议类型（设计 9.11.4），会议名与开关按角色控制（设计稿谁都能点）；搜索为包含匹配（设计稿是子序列模糊匹配，还匹配会议 id、日期与标签）；Knowledge Base 的 Source 取值按需求为 Goldie / Fireflies（设计稿为 Chat）；Memory 的会议摘要标签并排（设计稿 Fireflies 徽标占了层徽标的位置，7 #Q24b）；页头说明「All files uploaded through chat attachments…」已不能概括四个 Tab，改为「Goldie's sources: knowledge files, memories, cross-company content and expert testimony.」（本方案）；侧栏「+」沿用现有行为。

## 6. 需求追溯

7 份需求文档（`../调研/` 下）拆成 94 条，逐条对到设计章节（6.x 在提示词文档，「提示词 Pn」指提示词编号）、表、页面、接口与按钮（第 4 节小节号）。备注里的 #n 是设计第十章条目，Qn 是本文第 7 节。

| 需求条目（文档 · 章节） | 设计 | 表 | 页面 | 接口 | 按钮 | 备注 |
|---|---|---|---|---|---|---|
| **《会议内容提取规则》** | | | | | | |
| R01 分类后一次性读原文、产出全部衍生内容，下游不再读原文（I） | 6.1、6.11 | J3、P7 | — | — | — | 改判后重提取、证词补抽算加工自身再触发 |
| R02 面向 Founder 的界面绝不呈现原始逐字（I） | 1.4、9.3.5 | P7 | PG-05a、PG-05b；例外 PG-03 | API-24 | — | 创始人可看本人受邀会议的原文（#76） |
| R03 LLM 摘要层直接用 Fireflies Summary（I.1） | 1.3、2.3、6.5（提示词 P2） | J2 `overview` | — | — | — | 改为仍经 P2 整理（#56） |
| R04 机械擦除层：实体 / 姓名剥离 + n-gram 近逐字（I.2） | 1.4、1.5、6.11 步骤 2 | J3、P7 | PG-02 | API-24 | 4.6 行内 Save | 剥离只用于跨公司与证词（#2） |
| R05 n-gram 阈值可配置（I.2） | 1.5、#31 | — | — | — | — | 已补进 1.4 新配置项 |
| R06 剥离清单：公司 / 产品 / 人名 / 邮箱域名 / 客户等关系方 / 诉讼 / 数字 / 地址（I.2） | 1.5、6.8 / 6.9、第八章 #23 | 读 J4、J2、LG 业务表 | — | API-24 | — | 1.5 交开发设计的细则（常用词表、月份名、数值与量级、泛指措辞）放到开发前另拆的 `dev-python.md` |
| R07 保留行业与 ARR 区间轮廓；传播前管理员审核（I.2） | 1.5、1.7、9.6.4 | P7 `authorized` | PG-02 | API-23 | 4.6 Authorize、Confirm & Apply | 跨公司默认不勾（Q10） |
| R08 GS→Founder 1a / 1b 摘要 ≤150 词（II） | 1.1、2.2~2.4、6.5 | P7（KB_APP·SUMMARY）、X1 | PG-02、PG-05b | API-21、API-23、API-37 | 4.6 Authorize | 摘要行单独 Authorize（Q9），随正文条目上线、写进条目 `summary`，正文未勾时不生效（Q42） |
| R09 GS→Founder Founder KB / Portfolio KB（II） | 2.2、2.3、6.5 | P7（KB_APP·KB）、X1 | PG-02、PG-05a | API-21、API-33 | — | 两列为同一份（#3）；正文条目同时带摘要（Q42） |
| R10 GS→LP 1b 与 Portfolio KB 为基金级（II） | 3.2、3.3、6.7（提示词 P4） | P7（FUND_LEVEL）、P1 `portfolio_ids` | PG-02、PG-05a、PG-05b | API-21、API-33、API-37 | — | 不按公司拆分（#49） |
| R11 GS Internal 涉及具体公司的摘要（II） | 4.2、4.3、6.6（提示词 P3） | P7（KB_ADMIN）、P4 | 同 R10 | 同 R10 | — | 默认放行（#87） |
| R12 GS→Partner 涉及公司退出的摘要（II） | 5.3、5.4、6.6、6.12 | P7（KB_ADMIN）、P4 | 同 R10 | 同 R10 | — | 默认放行（#88） |
| R13 Cross Company 四类会议同一口径（II、术语 (2)(3)） | 1.1、2.3、3.5、4.4、5.5、6.9（提示词 P6） | P7（CROSS_COMPANY）、X1 | PG-02、PG-05c | API-21、API-23、API-30 | 4.6、4.9 | 默认不勾（1.7、Q10） |
| R14 进行中的交易永不放出（II、术语 (3)） | 1.7、2.3、3.3、6.7、6.9 | P7 | — | — | — | LP 在途交易写进基金层（#57） |
| R15 保密过滤（术语 (4)） | 1.7、3.6、5.7、6.8 / 6.9 | — | — | — | — | 加严（#17） |
| R16 证词 · GS→LP 类别（II） | 3.4、6.8（提示词 P5） | P7（TESTIMONY_*） | PG-02、PG-05d | API-21、API-30 | 4.6、4.9 | — |
| R17 证词 · GS→Partner 类别（II） | 5.6、6.8 | P7 | PG-02、PG-05d | API-21、API-30 | 4.6、4.9 | 与 LP 共用证词库（#28） |
| R18 证词 · GS→Founder 限专家、只谈市场（II） | 2.5、6.8、6.10（提示词 P7） | P7、P5、P2 `testimony_backfill_status` | PG-02、PG-02c | API-08 → API-28、API-29 | 4.6 证词补抽、4.7 PG-02c | 同场其他专家也抽（#14、#72） |
| R19 证词带角色、时间戳、会议日期生效的专长标签（II） | 3.4、6.11 步骤 7 | P7 `speaker_participant_id` / `source_timestamp`、P2 `expertise_tags` | PG-02、PG-05d | API-21、API-30 | — | 矩阵里只读显示时间点，不进投影（Q26，5.6） |
| R20 证词权限：管理端看完整来源，Founder 只看内容与标签（II） | 1.1、3.4、9.6.2、9.11.5 | P7 两版 | PG-02、PG-05d | API-21、API-30 | — | Tab 只显示姓名与标签（#44） |
| R21 管理员在详情页干预，改后实时更新到 AI 聊天（III） | 9.5、9.6、1.6、第八章 #7~#10 | P7、X1 | PG-02 | API-22~24、API-38 | 4.6 | 对话里的来源链接不做（Q21）；投影写纯文本条目、不调 API-40（Q41） |
| R22 重新分类会议类型 → 重算路由（III） | 9.5.2、9.9.1、9.9.2 | P1、P8 `TYPE_CHANGE` | PG-02 | API-22；改 Unknown 走 API-23 | 4.6 类型下拉、Start Extraction | Pending 首次提取全部不勾（9.6.4） |
| R23 更改公司（× 移除、多选、可搜索、只列有权限的公司）（III；SR） | 9.5.3、9.9.1 | P4、P8 `COMPANY_CHANGE` | PG-02 | API-22、API-32 | 4.6 Company | GS→Founder 只留一家（#73） |
| R24 更改内容：单元格编辑、琥珀高亮、行内 Save / Cancel、保存时再清洗（III；SR） | 9.6.3、9.6.5 | P7、J3、P8 `CONTENT_EDIT` | PG-02、PG-02e | API-24 | 4.6 编辑 Content、行内 Save / Cancel | 只重跑机械层（#80②） |
| R25 更改授权：Authorize 复选框（III；SR） | 9.6.4 | P7 `authorized`、P8 | PG-02 | API-23 | 4.6 Authorize | 摘要勾选依赖正文：正文未勾时置灰并随之取消（Q42） |
| R26 Start Extraction 激活 / 置灰规则（III；SR） | 9.5.1、9.9.1 | P1 | PG-02 | API-22、API-21 | 4.6 Start Extraction | Company 只对 GS→Founder 必填（#6） |
| R27 Discard Changes（III） | 9.6.5 | — | PG-02 | 前端 | 4.6 Discard | 已写库的不撤销（#80①） |
| R28 Confirm & Apply Routing（III） | 9.6.5 | P7、P1、P8 | PG-02、PG-02f | API-23 | 4.6、4.7 PG-02f | 改 Unknown 即激活（Q25e）；类型 / Founder 公司对不上时二次确认（Q48） |
| R29 公司或公司人员增改 → 自动路由 Pending 的 GS-Founder 会议（III） | 9.9.3、第八章 #27 | P2、P4 `auto_routed`、P1 | — | SQS（3.5） | — | #89 |
| R30 路由决策与覆写写审计（III） | 9.10 | P8 | — | — | — | 只记 7 种事件；无查看页 |
| **《AI Meeting Type 自动映射标准》** | | | | | | |
| R31 识别链顺序；禁止用会议标题（一） | 1.9、第八章 #24 | P2、P3、P4、P1、P8 `IDENTIFY` | PG-02 | API-21 | — | — |
| R32 GS 域名三个（一） | 1.9 ①、9.7.7 | J1 `email_domains` | PG-01c | API-10、API-11 | 4.4 Email Domain | 上线时手工添加（Q5） |
| R33 LG 平台用户按邮箱 / 域名判 GS 或 Founder 并关联公司（一） | 1.9 ②③ | P2、P4、LG 业务表 | — | — | — | #52、#54；名册有当日生效记录时角色以记录为准（Q47） |
| R34 公司端只认在营公司（一） | 1.9 ②、2.1 | 读 `company` | PG-02 | API-32（带状态） | 4.6 Company | 不在营的口径（#86） |
| R35 Cheat Sheet 取会议日期生效版本，重复取最新（一） | 1.9 ④、9.7.2 | J4、P2 `cheat_sheet_id` | — | — | — | — |
| R36 HubSpot 联系人匹配（一） | 1.9 ⑤、#25 | — | — | — | — | 本期不做，见第 2 节「不在本期」 |
| R37 先邮箱后姓名（一） | 1.8、1.9 ⑥ | P2 `match_step` | — | — | — | 姓名只出候选，交 P8 核对（#77） |
| R38 LLM 从转录推断（一） | 1.9 ⑦、6.13（提示词 P8）、6.4（提示词 P1） | P2、P3、P4 的 AI 字段 | PG-02 | API-21 | 4.6 AI inferred 悬停 | 经 P8 认出的证词默认不勾 |
| R39 仍无法解析 → Pending（一、二） | 1.9 ⑧、1.10、9.4.2 | P1 | PG-01a、PG-02 | API-20、API-21 | 4.2、4.6 | — |
| R40 Founder 为专家时补充识别（特殊说明） | 1.11、2.5 | P2 `expertise_tags` | PG-02 | API-21 | — | Expert 徽标 |
| R41 专家推测触发（专家推测） | 1.11、6.10、6.11 步骤 5 | P5 | PG-02 | API-21 | 4.6 点参会人 | ≥2 条门槛（本方案） |
| R42 多标签逐条确认 / 拒绝；拒绝记邮箱 + 标签（专家推测；SR） | 1.11、9.5.6、9.5.7、9.5.10 | P5、J6、J4 | PG-02c | API-08 → API-28 | 4.7 PG-02c | Q22；逐个标签在标签栏留下或删掉（Q45，推翻 Q24c 的逐标签按钮） |
| R43 GS 员工永不标为专家（专家推测） | 1.11、9.5.6 | 程序过滤 | — | — | — | 另排除 Other（#72） |
| R44 五个固定类别，只有管理员能加（专家推测） | 1.11、9.8、6.10 | J5 | PG-01c2 | API-12~14 | 4.4、4.7 | Q4、Q19 |
| R45 专业领域为自由文本，不用于路由（专家推测；CS） | 1.11、9.7.1 | J4 `area_of_expertise` | PG-01c1、PG-02a / b | API-06、API-07 | 4.4 | — |
| R46 何为 GS 人员；名册里的 GS staff / Founder 指未用平台的人（一） | 1.9、9.7.1 | P2、J4 `role` | — | — | — | #51、#13 |
| R47 可追溯会议为何关联到某公司（补充规则） | 1.9、9.5.3 | P4 `basis*`、P8 | PG-02 | API-21 `basisText` | — | 未采纳的候选先不展示 |
| R48 整场作为一个整体分类，不做子会议切分（二） | 1.10（隐含） | P1（一场一个 `meeting_type`） | PG-02 | API-22 | 4.6 | 实现上满足，混合会议靠手动改判 |
| R49 按身份分类，保留发言人级归属（二） | 1.9 | J3、P3、P7 | PG-02、PG-02d | API-21、API-27 | 4.7 PG-02d | — |
| R50 GS→Founder 与 GS Internal 判定（二） | 2.1、4.1 | P1 | — | — | — | Board Call 已取消 |
| R51 GS→LP 与 GS→Partner 判定（二） | 3.1、5.0、5.1、1.8 | P1、P2、J4 | — | — | — | #30、#77 |
| **《Cheat Sheet》** | | | | | | |
| R52 列表字段；多个邮箱放不下用省略号（列表） | 9.7.3 | J4 | PG-01c | API-05 | 4.4 | 5.4 已补省略号 |
| R53 超过 90 天未复核显示 Needs review（列表） | 9.7.5 | J4 | PG-01c | API-05、API-07 | 4.4 | — |
| R54 除 Area of expertise 外必填（列表） | 9.7.4 | J4 | PG-01c1 | API-06、API-07 | 4.4 | Expertise tags 选填（Q24d） |
| R55 来源标识 From FF Summary Records（列表） | 9.7.1、9.5.7 | J4 `source` | PG-01c | API-05 | — | — |
| R56 按 Role 过滤；模糊搜索（列表） | 9.7.3 | J4 | PG-01c | API-05 | 4.4 | — |
| R57 Add External Party 弹窗字段（Add） | 9.7.4、5.2 | J4 | PG-01c1 | API-06 | 4.4 | — |
| R58 姓名唯一、确认后不可改，二次确认（Add） | 9.7.1、9.7.4 | J4 | PG-01c1 | API-06、API-41 | 4.4 Confirm（新增） | 重名自动加数字后缀，失焦提示（Q46） |
| R59 专长标签下拉可新增、删除，已用过的不可删（列表 / Add） | 9.8 | J5、J4、P5 | PG-01c2 | API-12~14 | 4.4 | — |
| R60 有效期重合以最后一条为准（Add） | 9.7.2 | J4 `updated_at` | — | API-07 / 08 与 Python 识别 | — | 两端同一算法 |
| R61 Edit 同新增，姓名置灰（Edit） | 9.7.4、9.7.5 | J4 | PG-01c1 | API-07 | 4.4 | — |
| R62 History 独立页面、面包屑可跳回、完整快照（History） | 9.7.6 | J4 | PG-04 | API-09 | 4.4、4.8 | 面包屑去向已补（4.8） |
| R63 Email Domain 可多个、可编辑删除（Email Domain） | 9.7.7、1.9 ① | J1 | PG-01c | API-10、API-11 | 4.4 | 整份提交（Q22） |
| **《Fireflies Configuration》** | | | | | | |
| R64 只支持 API Key；说明文案；Link（Connection / API Key） | 9.2、9.2.5 | J1 | PG-01b、PG-01b1 | API-02、API-04 | 4.3 | 掩码 + Remove 按设计稿（Q1）；说明文案已补（5.3） |
| R65 连接状态四种（Connection） | 9.2.4 | J1 | PG-01b | API-01 | 4.3 | `Disconnected` 阈值默认 3（1.4） |
| R66 显示最近同步时间（Connection） | 9.2.6 | J1 | PG-01b | API-01 | 4.3 | 固定 UTC 显示（Q25f） |
| R67 Sync now（Connection） | 9.2.6、9.3.1 | J1、J2、J3 | PG-01b | API-03 → API-01 | 4.3 | — |
| R68 每日拉取（拉取；RD） | 9.2.6、9.3.1、第八章 #29 / #30 | J1、J2、J3 | — | EventBridge → Java → SQS（3.5） | — | 每日 03:40 UTC（1.4） |
| **《Fireflies Raw Data》** | | | | | | |
| R69 保存所有会议原文与元数据，完整可追溯（描述） | 9.3、9.3.6 | J2、J3 | PG-01d、PG-03 | API-15、API-17、API-18 | — | 永久留存 |
| R70 列表字段（Meeting list） | 9.3.3 | J2 | PG-01d | API-15 | 4.5 | 另加筛选与排序（Q20） |
| R71 无实质内容显示 Invalid（Status） | 9.3.4、1.10 | P1 `identification_result` | PG-01d | API-15 | 4.5 | 误判无补救入口（#65） |
| R72 Raw transcript 详情（原始转录入口） | 9.3.5 | J2、J3 | PG-03 | API-17、API-18 | 4.5、4.8 | — |
| R73 Search 模糊搜索（Search） | 9.3.3 | J2 | PG-01d | API-15、API-16 | 4.5 | — |
| R74 权限：创始人看本人参加的会议（权限） | 9.3.6、第八章 #14 / #28 | J2 `participants` | PG-01、PG-01d、PG-03 | API-15~19 | 4.1、4.5 | 公司端入口在头像下拉（Q15） |
| **《Fireflies Summary Records》** | | | | | | |
| R75 每日拉取、分析完后展示（说明） | 1.10、9.4 | P1 | PG-01a | API-20 | — | 首轮跑完才进列表（Q13） |
| R76 列表字段；会议名与 Review 跳详情（列表） | 9.4.1 | P1、P4 | PG-01a → PG-02 | API-20 | 4.2 | — |
| R77 Search 与 Filter（列表） | 9.4.1 | P1、P4 | PG-01a | API-20 | 4.2 | 状态筛选只分 Passed / Pending（Q25d） |
| R78 Status 与 Scrub Status；信息卡字段（列表、信息卡） | 1.10、9.4.2、9.5.1 | P1 | PG-01a、PG-02 | API-20、API-21 | 4.1、4.6 | Pending 细分三种原因 |
| R79 必填项（信息卡） | 9.5.1 | P1~P4 | PG-02 | API-22 | 4.6 | — |
| R80 AI Meeting Type 下拉 5 项（信息卡） | 9.5.2 | P1 | PG-02 | API-21 | 4.6 | — |
| R81 Portfolio 标记；GS-Founder 只读（信息卡） | 9.5.4 | P1 `portfolio_ids` | PG-02 | API-21、API-23、API-32 | 4.6 | — |
| R82 Participants 着色；Unidentified 点开 Assign（信息卡） | 9.5.5、9.5.7 | P2、P3、J4 | PG-02、PG-02a | API-21、API-25 | 4.6、4.7 | — |
| R83 平台外人员可编辑、回流名册；平台内人员无弹框（信息卡） | 9.5.5、9.5.7 | P2、J4 | PG-02b | API-07 → API-28 | 4.7 | #80④；前端直调 Java、关窗后同步（Q44） |
| R84 Visible to 合并展示（Matrix） | 9.6.2 | P7 `destination` | PG-02 | API-21 `visibleTo` | — | 文案对照见 5.6 |
| R85 证词分别展示管理端与 Founder 端措辞（Matrix） | 9.6.2、3.4 | P7 两版 | PG-02 | API-21 | 4.6 | 两版各自编辑（#80③ 已改） |
| **《Goldie Base》** | | | | | | |
| R86 Goldie Base 四个 Tab（概述） | 9.11、9.11.1、第八章 #17 | — | PG-05 | API-19、API-39 | 4.9 | Q16 |
| R87 Knowledge Base 原业务不变，不关联显示「—」（KB） | 9.11.2、第八章 #11 / #12 | X1、P7 `fund_tag_ids` | PG-05a、PG-05a1 | API-33~36、API-31 | 4.9 | Q24a；From Chat / Uploaded By 显示 `—`（Q25a） |
| R88 KB 新增 Source 栏，Fireflies 可跳原文（KB） | 9.11.2、第八章 #18 | P7 `file_id` | PG-05a → PG-03 | API-33 | 4.9 | 只有有原文权限的人可点（#47） |
| R89 Memory：Fireflies Memory / Meeting Summary 标签，≤150 词，不关联显示「—」（Memory） | 9.11.3、1.3、第八章 #13 / #19 | X1 `FIREFLIES`（摘要非空） | PG-05b | API-37 | 4.9 | Q24b；摘要按 markdown 渲染（5.8，#20）；摘要并入正文条目（Q42） |
| R90 Cross Company Tab（CC） | 9.11.4 | P7 | PG-05c | API-30 | 4.9 | 只列已放行的（#42） |
| R91 附会议名称与元数据，PM 不可点（CC / ET） | 9.11.4、9.11.5 | P7 冗余、P1 | PG-05c、PG-05d → PG-02 | API-30 `canOpen` | 4.9 | #43、#48 |
| R92 Play candidate 开关（CC / ET） | 9.11.6 | P7 `in_playbook` | PG-05c、PG-05d | API-31 | 4.9 | Q8 |
| R93 模糊查询与时间过滤（CC / ET） | 9.11.4、9.11.5 | P7 | PG-05c、PG-05d | API-30 | 4.9 | 证词另匹配说话人姓名（Q25b） |
| R94 Expert Testimony 每条带说话人姓名与专家标签（ET） | 9.11.5 | P7 → P2 | PG-05d | API-30 | 4.9 | 只列署名版 |

**追溯缺口的处理**（94 条中 11 条原有缺口）：

| 条目 | 缺口 | 处理 |
|---|---|---|
| R05 | n-gram 阈值、投影重试上限没进配置表 | 已补进 1.4 新配置项 |
| R06 | 设计 1.5 交开发设计的剥离细则没有落点 | 属于 Python 算法细节，放到开发前另拆的 `dev-python.md`（文档头已注明各端实现细节另拆） |
| R19 | 证词时间戳在任何界面都看不到，设计 3.4 与 6.11 前后矛盾 | 已定：矩阵里只读显示（7 #Q26） |
| R36 | HubSpot 一级没有落点 | 已写进第 2 节「不在本期」 |
| R48 | 「整场分类、不做子会议切分」没有明文 | 实现上满足（P1 一场一个类型，混合会议靠 4.6 手动改判），不另加 |
| R52、R62、R64 | 邮箱省略号、History 面包屑去向、Configuration 说明文案 | 已补进 5.4、4.8、5.3 |
| R65 | `Disconnected` 阈值与每日拉取时间没人拍板 | 1.4 给默认值：阈值 3（Nacos 可配）、每日 03:40 UTC（落地时写死在枚举、不可配，7 #Q33）（本方案） |
| R66 | 展示时区未定 | 已定：固定 UTC 显示（7 #Q25f） |
| R89 | Memory 摘要按 markdown 渲染还是写成纯文本（设计 #20 交开发设计定） | 定为 Memory 页按 markdown 渲染：详情弹框渲染，列表两行预览去掉标记；提示词不改（本方案，5.8） |

设计第十章里仍等需求方确认、本文按当前假设落地的：#9（PM 看不看 Raw Data）、#32（GS→Founder 在途交易）、#41~#43（跨公司内容的审核与可见范围）、#48（PM 看到全租户会议名）、#84（Cheat Sheet 限 PGM / SA）。

## 7. 待确认问题

待确认（第 6 步开发中发现，2026-10-28）：需要拍板的 Q27~Q36 已全部拍板（见已定表），Q37~Q40 是待核实的事实或知会的风险；拍板前都按「现在的实现」落地。

| # | 问题 | 现在的实现（当前假设） | 影响范围 |
|---|---|---|---|
| Q37 | 投影 markdown 里的原文链接点不点得开 | 链接取 `LGPI_BASE_URL` + `/fireflies/transcripts/{meetingId}`；`LGPI_BASE_URL` 原本是 Python 回调 Java 网关用的地址（`.env_example` 为 `http://localhost:9000`） | 某环境的 `LGPI_BASE_URL` 若是内网网关地址，Goldie 引用的原文链接用户打不开。需运维确认各环境的值；不是用户可访问的前端域名，就新增一个前端域名环境变量（记 env-update 与 `.env_example`） |
| Q38 | PG-01 租户下拉的默认显示 | 没切换过租户时下拉显示组织树 `nodes[0]`（同 Portfolio Companies 写法），各 Tab 不带 `organizationId`、按会话租户取数 | 多组织用户的 `nodes[0]` 不一定是会话租户：下拉显示的租户与列表数据不一致，直到手动切换一次。第 2 节「入口与守卫」写的是「默认会话租户」 |
| Q39 | 公司变更通知没覆盖的入口（知会） | 按设计第八章 #27 与 3.5，只在 `CompanyServiceImpl.create` / `update`、`CommonServiceImpl.createInvitedUserAndSendEmail`、`UserServiceImpl.clientUser` / `update` 发；其中邀请的是管理端用户时不发，其余直接调 `companyRepository.save` 的入口也不发 | 经这些入口改的公司不触发自动路由，相关的待识别 GS → 创始人会议要管理员在 Summary Records 手动处理 |
| Q40 | Raw Data 的几处文案与筛选细节 | a. 日期筛选的空值标签照设计稿为 `All dates`，Summary Records 为 `All time`（5.2）；b. 没搜索、没筛选也没有会议时（如没有受邀会议的公司端用户）仍显示「No meetings match your search.」，5.5 没定无数据的文案；c. 切换租户时不清参会人筛选 | a. 两个 Tab 文案不一致；b. 空列表的提示不贴切；c. 新租户里可能没有这些参会人，列表为空，要手动 Clear filters |

已定（用户决定 2026-10-27~29；Q1~Q13 在确认① 中拍板，Q14~Q24 在确认② 中拍板，Q25、Q26 在确认③ 中拍板，Q27~Q36、Q41~Q43 在第 6 步开发中拍板，Q44~Q49 在审核环节拍板（2026-10-29））：

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
| Q9 | 摘要与 KB 正文是否共用一个 Authorize | 分开（同设计稿：矩阵两行各一个 Authorize）。P7 加 `output_type`、删 `summary`；摘要行单独投成条目（登记 `FIREFLIES_SUMMARY`，进 Memory Tab），知识库行条目不带摘要（登记 `FIREFLIES`，进 Knowledge Base Tab）；唯一约束先不加（已由 #Q42 调整） | P7、X1、1.4；设计 1.1~1.3、2.4、9.6.2、9.6.6、第八章 #4 / #11 已回写 |
| Q10 | 跨公司与证词提取完默认勾不勾 Authorize | 维持现行设计：跨公司一律默认不勾、要管理员审核（会议因此 Pending · 待审核）；证词按邮箱认出发言人的两版默认勾选，经 P8 认出的默认不勾 | P7 授权初值；设计 9.6.4、9.9.5 不变 |
| Q11 | 收到重投、会议还在识别中 / 提取中怎么办（原写「1 小时内视为有人在跑、跳过」，但重投约 10 分钟就到，自动重跑实际不会发生） | 重投（接收次数 ≥ 2）即上一处理者已不在，直接接手从头重跑；凭 `processing_started_at` 条件更新，老进程落库时核对不上即放弃；首次收到却已有状态行的是 Java 重复发送，删掉 | P1 `processing_started_at`；设计第八章 #30 已回写 |
| Q12 | 卡死清扫要不要本期做（Python 没有定时任务框架） | 拆为单独功能，与 AI 财务提取任务卡在 `PROCESSING` 一起做，Fireflies 开发完成后设计、与本功能一起上线；死信 / 过期的首轮会议与已投递无状态行的会议交给它；非首轮提取与证词补抽卡在 `RUNNING` 也由它判超时，本功能不做读时判断 | P1「卡死兜底」、P2、1.4；code-examples 第 4 节；设计 1.10、第八章 #30 已回写 |
| Q13 | 首轮处理中途没跑完（进程被杀、代码异常）的产出与会议怎么处理 | 只要没跑完，本次产出全部作废；首轮每次开跑先删本场产出、从头跑，不从中断处接着跑；连续 3 次没跑完不做特殊处理，停在处理中、交给定时清扫。首轮跑完才进 Summary Records（Passed / Pending），处理中不显示。大模型最终失败不在此列（设计 6.11） | P1 `processing_started_at`、「卡死兜底」；J2；设计 1.10、9.5.9、第八章 #30、提示词 6.11 已回写 |
| Q14 | 管理端入口放哪 | 头像下拉（按设计稿，同 ERL 的 `menuRight_SuperAdmin`），后台菜单 path `/fireflies` | 第 2 节「入口与守卫」；设计第八章 #32 已回写 |
| Q15 | 公司端入口放哪（设计稿没有公司端页面） | 也放头像下拉，放在订阅条件之外（该条件只管 Profile 与菜单项）；所有公司端用户都显示，没有受邀会议的看到空列表；进去只有 Raw Data Tab | 第 2 节「入口与守卫」；设计 9.3.6、第八章 #28、第十章 #90 已回写 |
| Q16 | Goldie Base 的路由形态（设计 9.11.1 交开发设计定） | `/askGoldie/goldieBase?tab=…`，放在 `/askGoldie` 下，门户布局判定与顶栏高亮不用改；旧 `/knowledgeBase`、`/memorySettings` 重定向到对应 Tab | 第 2 节 PG-05；设计 9.11.1 已回写 |
| Q17 | Fireflies Management 的切换租户与组织 id 校验 | 组织树根下有子组织才显示下拉（同 ERL、Portfolio Companies），默认会话租户；SA 可借此切到子租户查看；后端先不校验组织 id，信任前端传入，PGM / SA 角色照常校验 | 第 2 节「入口与守卫」、第 3 节通用约定；设计 9.1、第十章 #69 已回写 |
| Q18 | Java 包结构与路径命名 | 按 Java 规范：`web/fireflies/` 分 DDD 四层、路径 kebab-case 复数；不照 ERL 的平铺包与驼峰单数路径 | 第 3 节通用约定 |
| Q19 | 会议页弹框里新增 / 删除专长标签走哪 | 前端直接调 Java API-13 / 14（带会议所属租户），不经 Python 转发，与 Cheat Sheet 页同一组件、同一组接口；名册写入仍经 Python（要同时更新本场识别结果、触发补抽）（名册写入部分已由 #Q44 调整：会议页编辑与专家确认改为前端直调 Java、关窗后同步） | 1.1 J5、1.4、第 3 节 API-13 / 14；设计第八章 #31 与「两端怎么衔接」已回写 |
| Q20 | Raw Data 的筛选与排序（设计 9.3.3 只有关键词搜索） | 按设计稿：关键词 + 日期区间 + 参会人多选 + 有效性筛选 + 列头排序，服务端过滤后分页；筛选状态存会话，从原文页返回时恢复 | 第 3 节 API-15 / 16；设计 9.3.3 已回写 |
| Q21 | Ask Goldie 对话里展示 Fireflies 来源链接 | 本期不做：需求与设计稿都没有，现有聊天也没有结构化来源；召回改造照做，对话页面不改，以后需要再单独立项 | 第 2 节「不在本期」 |
| Q22 | 前端两端都能直调，接口有没有可删减或复用的 | 合并 8 处，50 → 41 个（审核后新增 API-32、去掉两个 Java 复用，现 40 个）：会议详情一次取回弹框预填、专家建议标签与矩阵；Summary Records 列表顺带返回红点数；行内 Save 的清洗预览与落库合成一个接口；两个新 Tab 共用一个列表接口；Play candidate 与基金标签合成一个改标记接口；Email Domain 整份提交；专家确认框不再「打开即消解」，打开前已入册或已在拒绝名单的标签同步时落库。名册写入仍经 Python（规则留在后端）（名册写入部分已由 #Q44 调整） | 第 3 节；P5；code-examples 第 2 节；设计 9.5.6、9.5.10、9.7.7、第八章 #20、#26、第十章 #63、提示词 6.11 已回写 |
| Q23 | Goldie Base 两个新 Tab 的排序与会议名称匹配（内容在 P7、会议时间与标题在 P1，Python 仓储不许跨表 JOIN） | P7 冗余 `meeting_started_at`、`meeting_title`（投递后不变，同 P1 冗余 J2），`idx_ai_ff_routing_row_tab` 改为按 `meeting_started_at DESC`；会议类型、`fireflies_id` 分页后批量查 P1。对已确认表结构的变更 | P7、1.1、code-examples 第 2 节、API-30；设计 1.4 跨端读表、第八章 #20、9.11.4、9.11.5 已回写 |
| Q24 | 设计稿与设计文档不一致的 4 处（A1 要求列出） | a. Knowledge Base 保持现有功能：搜索只按文件名，不加 Source 筛选（Source 列照加）；b. Memory Settings：管理端 File Scope 加一项 Fireflies Memory（只看会议摘要），Document Summary 选项不加，公司端不加筛选；会议摘要标签并排：层徽标 + Fireflies Memory + Meeting Summary；c. 专家确认框按需求逐个标签同意 / 拒绝，不照设计稿的整人 Approve / Reject（已被 #Q45 推翻：改为标签栏增删）；d. Expertise tags 维持选填，不照设计稿的必填 | API-33、API-37、API-28；d 在第 4 步的表单校验落地；设计 9.5.6、9.7.4、9.11.2、9.11.3、第八章 #19、第十章 #46 已回写 |
| Q25 | 补审与自检发现的 6 处设计稿与设计文档不一致 | a. Knowledge Base 的 Fireflies 行 From Chat 与 Uploaded By 都显示 `—`（设计稿 From Chat 一格写公司名，不照）；b. Expert Testimony 搜索按设计稿另匹配说话人姓名；c. Memory Settings 搜索保持现有（摘要全文与文件名），不加设计稿的公司匹配；d. Summary Records 状态筛选按设计稿只有 All statuses / Passed / Pending，不按三种 Pending 原因筛，原因只在 Status 列旁注；e. 改为 Unknown 后 Confirm & Apply 激活（这是把会议打回 Pending 的唯一入口），只在提取或证词补抽进行中置灰；f. 日期时间按设计稿格式固定 UTC 显示，会议日期按 UTC 自然日；现有的 Knowledge Base、Memory Settings 日期列保持原格式 | API-20、API-23、API-30、API-33、API-34、第 4、5 节；设计 9.3.3、9.4.1、9.5.9、9.11.2、9.11.5、9.12 #3 已回写 |
| Q26 | 跨公司与证词的出处时间点要不要显示（需求证词表要求带时间戳，原方案任何界面都看不到） | Content Routing Matrix 里跨公司与证词行只读显示时间点 `[hh:mm:ss]`，供管理员回查原文；不进投影，Goldie Base 两个新 Tab 不显示 | P7 说明、API-21（`routingRows.sourceTimestamp`）、5.6；设计 3.4、9.6.2、9.6.6、6.11 步骤 7 已回写 |
| Q27 | 改判为 GS 内部 / GS → Partner 后，Start Extraction 前补跑 P1 新认出的公司要不要直接采纳（原实现只写提及、不改采纳，与设计 9.5.9 不一致） | 按设计 9.5.9：补跑新出现的 `high` 公司（本场 P4 原本没有的）直接置为采纳、计入本次提取的保留公司，本次即产出按公司分行的 1b；这些行属于重跑后新出现的去向，按设计 9.9.5 默认不勾，管理员在矩阵勾选、Confirm & Apply 后才上线（只到管理端）；已有行只更新提及、不改采纳与依据，管理员手动去掉过的不复活；非 `high` 只记候选。用户决定 2026-10-28 | 识别服务 `rerun_company_mentions` 与 Start Extraction（API-22）；P4；设计 9.5.9、提示词 6.11 |
| Q28 | 在营公司的状态口径：需求写 Active、Thriving、Needs Intervention、Needs Guidance，页面公司状态下拉与 Java `CompanyStatusEnum` 没有 Active | 需求的 Active 即 Achieving（5）：在营 = Needs Intervention(2) / Needs Guidance(3) / Thriving(4) / Achieving(5)；Exited(1) / Shut down(6) / Off journey(7) 与状态为空的不在营。与现有实现一致，代码不改。用户决定 2026-10-28 | 识别 ② 判 Founder、GS → 创始人只认在营公司（P1 反推、API-22）、自动路由（9.9.3）、会议页 Company 下拉置灰（API-32）；设计 2.1 |
| Q29 | 原文页能否用浏览器 Ctrl+F 查找全篇（需求只要求展示完整逐字转录，Ctrl+F 是设计 9.3.5 的理由；原实现用虚拟滚动，只渲染可视区附近的句子） | 去掉虚拟滚动、逐行直接渲染；首批显示后前端在后台连续取完全篇（API-18 每批 500 句），底部显示加载提示，某批失败即停并显示 Retry。依据：真实样本 43 场平均 448 句、最长 1,245 句（93 分钟），3 小时约 2,400 句，整篇渲染无性能压力，且去掉虚拟滚动的行高估算跳动。后端不改。用户决定 2026-10-28 | PG-03（4.8、5.7）、3.4、API-18 说明；设计 9.3.5 |
| Q30 | 投影卡在 `PENDING` 的中间表行由谁接手（投影重试在进程内，进程重启后没人接手；API-23 把 `PENDING` 当作进行中、不重推，已授权内容一直不上线） | 并入定时清扫（单独功能，与本功能一起上线，7 #Q12）：P7 `projection_status = PENDING` 且 `updated_at` 距今超过卡死时限的行（含摘要行「只替换摘要」）按失败处理，并按该行当前状态重推（已授权未删的上线、否则下线）；本功能不另做。查询见 code-examples 第 4 节。用户决定 2026-10-28 | P1「卡死兜底」⑤、1.4 卡死时限；定时清扫功能设计 |
| Q31 | 识别与提取用哪个模型、输入要不要设上限（设计未指定；原实现超过 60 万字符不发调用、按最终失败处理） | P1、P8 与 P2~P7（含摘要压缩）都用 sonnet（temperature 0）；输入不设上限、不预先拦截，超出模型上下文时由模型调用报错，按调用失败走重试与最终失败。实际样本最长一场约 4.9 万字符，3 小时约 10 万字符，远低于上下文上限。用户决定 2026-10-28 | 识别与提取两个智能体；提示词 6.11「不做分段抽取」 |
| Q32 | Goldie Base 用哪个租户：现有 Knowledge Base、Memory 对所有管理端传组织树首叶租户；设计 9.11.1 原定只有 SA 取首叶、其余用会话租户并等值校验，两套口径在「会话租户有子组织 / 多组织」的非 SA 用户上不一致（机构层条目被排除、基金标签候选对不上、改标签被拒） | 统一用组织树首叶租户：Goldie Base 下管理端一律传首个叶子组织 id（Knowledge Base、Memory、两个新 Tab、基金标签候选与修改）；后端信任传入的组织 id，没传时回退会话租户，会话租户的等值校验先不启用（同 #Q17）；角色校验与「基金标签候选须在该行租户」照旧。用户决定 2026-10-28 | 第 3 节通用约定「租户」、API-30~32、API-33/35/37 的机构层；2「入口与守卫」、4.9；设计 9.1、9.11.1、第十章 #69 |
| Q33 | 每日拉取的时段（原定 02:00 UTC，与 QuickBooks 日拉、ETLScore 同一时刻，落在 UTC 00~03 夜间高峰） | 改为每日 03:40 UTC（`cron(40 3 * * ? *)`）：排在 00:00~03:00 那批任务之后、错开整点与每 15 分钟的轻量任务，让夜间任务排得紧凑、便于后续再加定时任务。用户决定 2026-10-28 | Java `FixedScheduleTypeEnum.FirefliesDailyPull`；1.4、J2「投递与补投」示例 |
| Q34 | 删除组织（`OrganizationServiceImpl.deleteById`，硬删）时 Fireflies 数据怎么处理；连接行仍是已连接，每日拉取按连接状态选租户，已删组织会被天天空拉、空跑大模型 | 数据不处理：J1~J5 与 Python `ai_ff_*` 都留着。每日拉取跳过「组织已不存在」的租户（`OrganizationService.getOrganizationById` 为空即跳过，记 WARN 日志），不改任何数据；Sync now 选不到已删组织，不另处理。用户决定 2026-10-28 | Java `FfSyncServiceImpl.pullDailyForAllTenants`；J1 |
| Q35 | 证词补抽「标签没变不补」怎么判（设计 2.5）：P7 不存每行所用的标签，原近似规则拿「现有证词行的类别集合」比，某标签没抽出过证词时会误判成「变了」，多跑一次 P5 并冲掉此人证词行上的人工编辑与勾选 | 方案 B：P2 加 `testimony_tags`（JSONB，上次为此人抽证词所用的标签），首次提取与补抽成功时写入；补抽前与名册里会议当日生效的标签比对——GS → 创始人相同即不补；GS → LP / Partner 只在从没抽过且现在有标签时补；标签清空软删证词行并写 `[]`。V034 尚未执行，直接改。用户决定 2026-10-28 | P2、V034；提取服务（首次提取、补抽）；设计 2.5 |
| Q36 | 跨端读表的数据库授权（A5：Python 读 J1~J5 与 7 张 LG 业务表、Java 读 P1 / P5） | 不另授权：Python 与 Java 现用同一套数据库账号和密码，单独授权方案一直没实行；按列授权等建议不做。用户决定 2026-10-28 | 1.4「跨端读的表」、1.5、V034 文件头 |
| Q41 | 投影产物还要不要生成 md 文件、经 Java（API-40）上传 S3（后台任务没有用户 token，要靠静态 `LGPI_BEARER_TOKEN`，其默认值是某用户的 JWT，约 2026-12-28 过期） | 投影改纯文本条目 + 合成 `file_id`，下载现生成 md（用户决定 2026-10-28）：`ai_rag_entry` 用 TEXT 来源，`content_text` 存按原规则生成的 markdown；每次投影生成一个合成 `file_id`，同时写进条目、切片、登记行与 P7，不对应 Java `files` 行，也不对应 S3 对象，按文件圈定召回与三方关联照旧走它；不再调 API-40，Java 撤回 `FileBusinessTypeEnum.FIREFLIES` 与 md 魔数校验，Fireflies 不再依赖 `LGPI_BEARER_TOKEN`；API-35 对 Fireflies 行现生成 md，返回 `data = {url: null, fileName, content}`。理由：省掉 S3 上传和对 Java 的依赖，不依赖长期服务 token，少了孤儿文件等异常路径 | P7 `file_id`、X1、1.4、3.3 API-35 / API-40、3.4、3.5、3.6、4.9、4.10、6 R21、8 0-J / 1-P4；设计 1.1~1.3、1.6、2.4、3.3、七、第八章 #1~#3 / #5 / #11 / #12 / #16、9.1、9.6.4、9.6.6、9.11.2 已回写 |
| Q42 | 摘要行单独投成条目（#Q9）的两个毛病：摘要条目与正文条目在同一空间，会被重复召回、占掉名额；正文条目摘要为空，`get_file_summary` 取不到 | 摘要并入正文条目（用户决定 2026-10-28）：每个知识库（去向, 公司）只投 1 条 TEXT 条目，`content_text` 放正文，`summary` 列放摘要（摘要行已授权时写，否则为空）；中间表仍是摘要行、正文行两行，各自编辑、各自 Authorize，共用条目的 `ai_rag_entry_id` / `file_id`。**摘要跟着正文走**：正文未授权或已删时条目不上线、摘要授权不生效，前端把摘要勾选框置灰并随正文取消，API-23 按正文为准。**摘要向量**：整段建一条 `chunk_kind=summary` 的向量，用我方传入的摘要，不调系统摘要器，为空不建。**只改摘要**：正文在线时改摘要内容或摘要授权，只替换 `summary` 列与摘要向量，不重新向量化正文。**登记三值**：`business_type` 改为 `FIREFLIES`（知识库正文 + 摘要）/ `FIREFLIES_TESTIMONY`（证词两版）/ `FIREFLIES_CROSS_COMPANY`（跨公司），去掉 `FIREFLIES_SUMMARY`；Knowledge Base Tab 只取 `FIREFLIES`，Memory Tab 取 `KNOWLEDGE_BASE` 与 `FIREFLIES` 中摘要非空的条目。**重试跳过摘要**：RAG 管理端「重试」遇到 Fireflies 条目，跳过系统摘要器、保留原摘要并按它重建摘要向量。理由：与现有知识库文件同一模型，登记表只用一个值，Memory 页与召回走同一套机制；代价是不能只给 Memory 页摘要、不给知识库正文 | P7、X1、1.1、1.4、3.2 API-21 / 23 / 24、3.3 API-33 / 36 / 37、3.6、4.6、5.6、6 R08 / R09 / R25 / R89；code-examples V034 注释；设计 1.1~1.3、1.6、2.4、3.3、4.3、5.4、七、第八章 #1 / #4 / #11 / #12 / #19、9.1、9.6.2~9.6.4、9.6.6、9.11.2、9.11.3、第十章 #19 / #23 / #38 / #94、十一；提示词 6.5、6.11、6.12 已回写 |
| Q43 | 新列表的分页样式（设计稿多数没画分页，设计按每页 10 条） | Goldie Base 两个新 Tab 与 Fireflies Management 的 Summary Records、Cheat Sheet、Raw Data 一律对齐现有 Knowledge Base 的分页样式：默认每页 10 条，可选 10 / 20 / 50，常显 `${start} - ${end} of ${total} items`；手机端隐藏条数选择、用小号；不看设计稿（用户决定 2026-10-28） | 4.2、4.4、4.5、4.9、第 5 节开头、5.2、5.4、5.5、5.8；设计 9.3.3、9.4.1、9.7.3、9.11.2~9.11.5 已回写 |
| Q44 | 会议页回写 Cheat Sheet（专家确认框、Edit external party）怎么写。代码审核 P1：专家确认 Save 时 Python 把表单整份标签发给 API-08，Java 当「要追加的标签」合进会议日期起的每个生效版本，管理员后来在 Cheat Sheet 删掉的标签被加回当前版本，弹框里删标签被静默忽略；另 WA6（PG-02b From 预填版本起始日） | 会议维护 Cheat Sheet 与会议管理解耦，不再逐版本写副本。T1 = 提取时 P2 已记的 `cheat_sheet_id` + `expertise_tags`（不加字段），建议标签 = 大模型标签 − T1 − 拒绝名单；弹框预填 T2 = 会议日期当天生效的那条记录（9.7.2 回溯）。保存由前端直调 Java（专家确认框 → API-08，Edit external party → API-07），每次只追加一条完整记录、旧行不改（原 9.5.6 / 9.5.7 的逐版本副本作废）；有效期可改、必须包含会议日期（Java 拦截），已在册的预填 T2 原有效期，新登记默认 From = 会议日期、To 空；只有已在册者的 Name 只读；本场邮箱锁定（不可删改、可加别的邮箱；T2 里没有本场邮箱的（按姓名回退认出，或登记时按邮箱认到名册已有的人，#Q49）打开时自动补进并锁定）。不保存关窗什么都不写；保存关窗后前端调 Python 同步（API-28 改造），按库里现状算、可重复调用，首轮未完、提取或补抽进行中返回 40901，前端在这些状态下把 Save 置灰；组织变化不自动重新匹配公司（9.9.2）。已接受的后果（弹窗不提示）：新记录与别的版本区间重合时按写入最晚覆盖它们；标签可能从早于会议日期的那天生效；改动可能进不了更新的版本。WA6 随之成为预期行为（预填 T2 原有效期）。用户决定 2026-10-29 | 0、P1、P2、P5、J4、1.4、API-06 / 07 / 08、API-21、API-25、API-26（删）、API-28、3.4~3.6、4.7、4.10、5.6、6 R18 / R83；设计 1.11、2.5、第八章 #26 / #31、9.4.2、9.5.5~9.5.9、9.7.1、9.9.1、9.9.3、9.10.1、第十章 #63；提示词 6.8 |
| Q45 | 专家确认框逐标签同意 / 拒绝（#Q24c）操作繁琐；拒绝名单在 Python P6，Java 保存时写不了 | 去掉逐标签按钮行：建议标签预填进 Expertise tags 标签栏（已在拒绝名单的不预填，已在 T2 里的就是普通已有标签），留下 = 同意、删掉 = 驳回，Save 不再要求逐个选；驳回由 Java 在 API-08 同一事务里写：驳回 = 本次建议标签 − 保存后的 Expertise tags（没有登记字段时全部算驳回）；建议标签全删且此人未登记时不建条目、不校验登记字段，只写拒绝名单；推测依据区块保留，未入册者新建名册仍弹 Confirm submission。拒绝名单由 P6 `ai_ff_expert_rejection` 改为 Java 表 J6 `ff_expert_rejection`：字段与唯一约束不变，时间列 `timestamptz`（#Q3）；Java 写、Python 只读（识别前过滤、同步时判已驳回）；建表从 V034 挪到 Java V1（都未执行，直接挪）；查询仍按人展开。理由：用户体验好。用户决定 2026-10-29 | J6、P6（删）、P5、1.1、1.4、1.5、API-08、API-21 `resolvedAs`、4.7、5.6、6 R42、8；code-examples 第 1、2 节；设计 1.11、第七章、第八章 #15 / #26、9.5.6、9.5.8、9.5.10；提示词 6.10~6.12 |
| Q46 | 名册重名：原为新建时重名拒绝，会议页可「关联已有条目」（`linkExistingName`） | 租户内姓名仍唯一（忽略大小写）；新建时重名不拒绝、不合并，自动加后缀：从 1 起取第一个未占用编号（Tom → Tom1 → Tom2）。姓名失焦时前端调 Java 新接口 API-41 查重，重名在姓名下方提示「A Cheat Sheet entry with this name already exists. It will be saved as Tom1.」；保存时 Java 再按同一规则算一次、以保存时为准并返回最终姓名。Cheat Sheet 页 Add（PG-01c1）、Assign new external party（PG-02a）、专家确认框（PG-02c）三处统一。删除 `linkExistingName`、Python 40902、Java `FF_CHEAT_SHEET_DUPLICATE_NAME` 与前端重名 / 关联弹框。已接受的后果：同一个人换了邮箱、登记时又没填他在册的邮箱（#Q49）时会被建成 Tom1，历史分在两个条目、没有合并功能，由管理员在 Cheat Sheet 页自行维护。用户决定 2026-10-29 | J4 `name`、API-06、API-08、API-25、API-41、3.4、3.6、4.4、4.7、5.4、5.6、6 R58；设计 9.5.5、9.5.7、9.7.1、9.7.4、第十章 #77 |
| Q47 | LG 平台用户（识别 ②）在名册里有记录时，角色以名册还是平台账号为准 | 以名册（管理员修改）为准：专家确认框里平台用户的 Role 也可改（只有 Name 只读）；平台用户在 Cheat Sheet 有会议当天生效的记录时，角色以该记录为准、优先于平台账号推出的角色，本场同步（API-28）也按它刷新；改离 Founder 后不再按平台账号挂到被投公司。不论记录从哪个入口建（专家确认或 Cheat Sheet 页 Add）都按此处理，取代设计第十章 #74 ①（名册里是 LP / Partner 的平台用户不再判成 Founder）。用户决定 2026-10-29 | P2 `role`、识别 ②、API-28、3.6、4.7、6 R33；设计 1.9、1.11、2.1、9.5.5~9.5.7、9.7.1、第十章 #13 / #74；提示词 6.11 |
| Q48 | Confirm & Apply 要不要对「类型与当前参会人不符」「Founder 与关联公司不符」提示 | 保留现有 3 条拦截（参会人改了未重提、有未处理建议标签、GS → 创始人多于一家公司）；新增两条需确认、不硬拦：① 按当前参会人重跑类型判定，结果与当前类型不同（`TYPE_MISMATCH`，带 `suggestedType`）；② GS → 创始人会议有 Founder 的组织 / 所属公司与关联公司对不上（`FOUNDER_COMPANY_MISMATCH`）。服务端在 API-23 重算，有提示且请求未带 `confirmWarnings=true` 时返回新错误码 40903、`data.warnings` 列出，前端二次确认后带 `confirmWarnings=true` 重提；改为 `Unknown` 应用时不做这两条。不在应用时重读最新 Cheat Sheet（会议用自己的快照，与 Cheat Sheet 页在会议外的修改解耦）。用户决定 2026-10-29 | API-23、3.4、3.6、4.6、5.6、6 R28；设计 9.6.5 |
| Q49 | 去掉「关联已有条目」（#Q46）后，名册已有的人在会议页登记时会被建成 Tom1：① 拿转发的链接进会、不在受邀名单的名册人员，显示名对不上或 P8 没给 `high`，成为未对上的说话人，「指定为参会人」只列本场参会人、选不到他 ② 名册里的人换了个邮箱来开会，显示为 `Unidentified`。两种都只能新建，且与原条目共用邮箱，以后按邮箱匹配会同时命中两条 | Assign new external party（API-25）按邮箱认人：先判 LG 平台用户（不变）；再看填的邮箱（忽略大小写，任一命中即算）是否在名册某条记录会议当天生效的版本里——在就不新建，把本场参会人 / 说话人绑到那条记录、按它刷新识别结果，名册不改、表单其余内容不写入，返回 `registryMatchedName`，前端提示「已按名册中的 X 识别，未新建」，之后要改点胶囊走 Edit external party；邮箱在名册里、但会议当天生效的记录里没有它，或分属两条记录，拦截（42200，提示先到 Cheat Sheet 调整）；都不是才新建。情形 ② 认上后本场邮箱不在他的记录里，打开 Edit external party 时自动补进并锁定（同按姓名回退认出的人），保存即写进名册，下次用这个邮箱来能直接认出。不另加「指定为名册里的人」操作。另两个新建入口不认人、只拦截：Cheat Sheet 页 Add（API-06）与专家确认框给未入册的人新登记（API-08），填的邮箱已登记在名册别的条目（任一版本）里时拒绝，提示登记在谁名下。用户决定 2026-10-29 | API-25、API-06、API-08、API-21 `registryForm`、3.4、3.6、4.4、4.7；设计 1.9、9.5.5、9.5.7、9.5.9、9.7.4、第十章 #77 |

## 8. 开发任务拆分（第 6 步计划）

三个子仓库（Java `CIOaas-api`、Python `CIOaas-python`、web `CIOaas-web`）都是独立 git 仓库，按用户决定直接在三个子仓库的 `sprint122` 工作副本开发，不开分支（2026-10-28）。每个 agent 只改自己范围内的路径；多个任务都要碰的注册文件由主 agent 在第 2 波统一改；只做轻量校验（Java 编译、Python `py_compile` / ruff、web `tsc` / lint），不跑完整测试，不 git add / commit。路径缩写：Java `web/` = `gstdev-cioaas-web/src/main/java/com/gstdev/cioaas/web/`、`common/` = `gstdev-cioaas-common/src/main/java/com/gstdev/cioaas/common/`；Python 相对 `source/`；web 相对 `src/`。

| 波次 | 任务 | 负责范围 | 允许改动的路径（主要） | 依赖 |
|---|---|---|---|---|
| 0 | 0-J Java 数据层与共享 | J1~J6 迁移（含存量组织补 5 项预置标签；J6 由 7 #Q45 补）、实体 / 枚举 / Repository；PGM / SA 判定方法 + `AuthenticatedUserDto` 字段（API-19）；Fireflies 角色断言与租户解析；两条新队列、消息类型与消息体；`FileBusinessTypeEnum` 放行 md（已撤回，7 #Q41）；`FixedScheduleTypeEnum` 加一项；新建组织写预置标签 | `deploy/upgrade_doc/sprint122/V1__ff_init.sql`、`web/fireflies/domain/**`、`web/fireflies/application/dto/**`、`web/system/service/CompanyGroupService*`、`UserServiceImpl`（`current`）、`AuthenticatedUserDto`、`OrganizationServiceImpl`（`save`）、`common/sqs/enums/**`、`FileBusinessTypeEnum`（已撤回）、`FixedScheduleTypeEnum` | — |
| 0 | 0-P Python 数据层与共享 | P1~P5、P7、P8 迁移、触发器、X1 与关联表注释；ORM 模型、枚举、单表 Repository；Java 表只读映射（J1~J6）与 `Company` 补公司名；`current_user_api` 加字段；`escape_like` 等挪到 `common/`（#20）；空间种子（#6）；Fireflies 登记行的写入函数与 `_PROTECTED_BIZ_TYPES`；`source/fireflies/` 骨架与跨任务调用的服务接口（提取、投影、识别的函数签名） | `sql/migrations/business/V034__sprint122_fireflies_init.sql`、`fireflies/domain/**`、`fireflies/application/` 下的接口定义、`lg/db/models/**`、`lg/db/service/file_registry.py`（只加 Fireflies 登记函数与常量）、`lgpi_api/current_user_api.py`、`common/`、`chatbot/domain/repository/_common.py`、`rag/domain/enums.py` | — |
| 0 | 0-W 前端共享 | `services/api/fireflies/`（Java、Python 两个 api 文件 + request / response / dto，照第 3 节契约）与 `services/service/fireflies/`；组织树下拉下沉到 `components/`（ERL 改用它）；名册表单组件（PG-01c1、PG-02a~c 共用）与专长标签下拉（PG-01c2） | `services/api/fireflies/**`、`services/service/fireflies/**`、`components/OrganizationSelect/**`、`pages/exitReadiness/`（只改引用）、`pages/fireflies/components/**` | — |
| 1 | 1-J1 Configuration 与拉取 | API-01~04；Fireflies GraphQL 客户端；每日拉取与 Sync now 同一服务（抢占、补投、拉列表、写 J2 / J3、发 SQS、写 `dispatched_at`）；key 加解密；`ScheduleProcessor` 分发 | `web/fireflies/` 下 connection、sync 相关的 interfaces / application / infrastructure；`web/scheduler/service/ScheduleProcessor.java`（只加一个 case） | 0-J |
| 1 | 1-J2 Cheat Sheet | API-05~14、API-41：名册列表与版本裁决（9.7.2）、新建（重名加后缀）、编辑（每次追加一条完整记录）、专家确认保存（API-08，含写拒绝名单 J6）、姓名查重、History、Email Domain、专长标签（7 #Q44~#Q46） | `web/fireflies/` 下 cheat sheet、email domain、expertise tag 相关文件 | 0-J |
| 1 | 1-J3 Raw Data | API-15~18：管理端与公司端权限、按显示名筛参会人、读 P1 的 Invalid、逐句分批 | `web/fireflies/` 下 meeting 相关文件 | 0-J |
| 1 | 1-J4 公司变更通知 | 公司与公司端用户保存后发领域事件，事务提交后投 SQS | `web/system/event/` 新事件；`CompanyServiceImpl`（`create` / `update`）、`CommonServiceImpl`、`UserServiceImpl`（`clientUser` / `update`）只加发布点；`web/fireflies/infrastructure/messaging/` 监听器 | 0-J |
| 1 | 1-P1 消费者与自动路由 | `consumer/fireflies/` 两条队列；首轮编排（接手重跑、开跑先删本场产出、第 3 次不特殊处理）；公司变更后的自动路由 | `consumer/fireflies/**`、`fireflies/application/service/` 下编排与自动路由 | 0-P |
| 1 | 1-P2 识别 | 匹配链 ①~⑦、说话人绑定、P8、类型判定、P1 提示词与公司裁决、补充识别（1.9、1.11、6.4、6.13） | `fireflies/application/service/` 下识别相关、`ai/agent/fireflies_identify*`、`ai/prompts/fireflies/`（P1、P8） | 0-P |
| 1 | 1-P3 提取与后置 | P2~P7 提示词并行调用、修订调用、清洗、校验、落中间表、初始授权、专家候选、证词补抽（6.11） | `fireflies/application/service/` 下提取相关、`ai/agent/fireflies_extract*`、`ai/prompts/fireflies/`（P2~P7） | 0-P |
| 1 | 1-P4 投影与召回 | 第八章 #1~#5（文本入库、登记、跳过二次摘要、重投影、重试；#2、#3 已不再需要，7 #Q41）、#6 空间 ensure / find、#7~#10 召回改造（API-38 契约不变） | `fireflies/application/service/` 下投影相关、`rag/application/**`、`rag/infrastructure/processor/**`、`rag/domain/repository/chunk_repository.py`、`ai/tools/knowledge_base_tool.py` | 0-P |
| 1 | 1-P5 Summary Records 接口（一） | API-20~24、API-32：列表、详情（含 `participantsChanged`）、Start Extraction、Confirm & Apply、行内 Save | `fireflies/interfaces/routes/summary_record_routes.py`、对应 service、vo | 0-P；调用 1-P3 / 1-P4 的服务接口 |
| 1 | 1-P6 Summary Records 接口（二） | API-25、27~29：登记、指定说话人、名册同步（API-28，7 #Q44）、补抽重试；调 Java API-06 的 `lgpi_api` 封装 | `fireflies/interfaces/routes/participant_routes.py`、对应 service、vo、`lgpi_api/fireflies_cheat_sheet_api.py` | 0-P |
| 1 | 1-P7 Goldie Base 与现有接口改造 | API-30、31；API-33~36（file_registry）；API-37（memory） | `fireflies/interfaces/routes/goldie_base_routes.py`、`file_registry/**`、`memory/**`、`lg/db/service/file_registry.py`（列表与作用域查询部分） | 0-P |
| 1 | 1-W1 Fireflies Management 容器、Summary Records、Configuration | PG-01、PG-01a、PG-01b、PG-01b1 | `pages/fireflies/home/**` | 0-W |
| 1 | 1-W2 Cheat Sheet 与 History | PG-01c（含 Email Domain）、PG-04 | `pages/fireflies/home/components/cheatSheet/**`、`pages/fireflies/cheatSheetHistory/**` | 0-W |
| 1 | 1-W3 Raw Data 与原文页 | PG-01d、PG-03 | `pages/fireflies/home/components/rawData/**`、`pages/fireflies/transcript/**` | 0-W |
| 1 | 1-W4 会议详情 | PG-02、PG-02a~d、清洗回显、轮询；PG-02b / PG-02c 直调 Java 保存后调 API-28 同步（7 #Q44） | `pages/fireflies/review/**` | 0-W |
| 1 | 1-W5 Goldie Base | PG-05、PG-05a~d：新容器、门户外壳上提、入口合并、两页去外壳、Knowledge Base 与 Memory 改造、两个新 Tab | `pages/askGoldie/**`、`services/api/{fileRegistry,memory}/**`、`services/service/{fileRegistry,memory}/**`、`pages/devSupport/chat/components/{HistorySidebar,PortalNavSidebar,PortalTabBar}` 及其测试 | 0-W |
| 2 | 主 agent 集成 | 共享注册文件、前后端契约逐个核对、轻量校验、汇总偏离回写开发设计 | web `config/routes.ts`、`layouts/BasicLayout.tsx`（两端头像下拉）、`layouts/SecurityLayout.tsx`、`utils/request.ts`（`isInlineErrorEndpoint`）、`standards/architecture.md` 域表与 README；Python `main.py`、`bootstrap/lifespan.py`、`tracing` 前缀、`sql/migrations/env-vars/env-update.txt`、`.env_example`；Java 无共享注册 | 第 1 波全部 |

并行计划：第 0 波 3 个 agent 同时派出；第 1 波 16 个按「后端 11 个、前端 5 个」两批派出——前端按第 3 节契约开发，不等后端完成，两批可同时进行；第 2 波由主 agent 完成。1-P1 / 1-P5 对提取、投影的调用只依赖第 0 波定下的服务接口，不必等 1-P3 / 1-P4 写完。

文件归属的几处说明：`lg/db/service/file_registry.py` 由 0-P（Fireflies 登记函数）与 1-P7（列表与作用域查询）先后改，不同波次不冲突；`UserServiceImpl` 由 0-J（`current`）与 1-J4（发布点）先后改，同理；`ai/prompts/fireflies/` 下按提示词分文件，1-P2 与 1-P3 各管各的。

收尾：第 2 波完成后停下，报告改了哪些文件、偏离设计的地方，提醒「有改动待审核」与建议的测试范围，等你确认后再审核、测试、提交。

**进度**（2026-10-28）：第 0、1 波已完成，第 2 波集成中。
