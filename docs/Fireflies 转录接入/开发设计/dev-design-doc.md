# Fireflies 会议转录接入 — 开发设计

> 关联文档: [会议内容提取规则](../调研/会议内容提取规则-需求文档.md) · [AI Meeting Type 自动映射标准](../调研/AI%20Meeting%20Type%20自动映射标准-需求文档.md) · [Cheat Sheet](../调研/Cheat%20Sheet-需求文档.md) · [Fireflies Configuration](../调研/Fireflies%20Configuration-需求文档.md) · [Fireflies Raw Data](../调研/Fireflies%20Raw%20Data-需求文档.md) · [Fireflies Summary Records](../调研/Fireflies%20Summary%20Records-需求文档.md) · [Goldie Base](../调研/Goldie%20Base需求文档.md) · [设计](../设计/design-doc.md) · [抽取提示词](../设计/extraction-prompts.md) · [代码示例（DDL）](./code-examples.md) · 设计稿：Lovable 项目 FFL（`5c905189-2a86-4020-abec-88a276b00861`，commit `76cc767`）
>
> **本文范围**：三端共用的契约——表、页面、接口、按钮、布局与已定口径（第 7 节）。各端实现细节（类结构、关键算法、异常处理）按 `docs/CLAUDE.md`「不在一个文件中混写 Java + Python + 前端的实现细节」另拆 `dev-java.md` / `dev-python.md` / `dev-frontend.md`。

## 0. 概述

**做什么**：把 Fireflies 录制的 Teams 会议拉进 LG，自动识别参会人与会议类型，用大模型提取摘要、知识库文档、跨公司内容与专家证词，经管理员审核后按可见范围投影进 Goldie 的知识库与记忆；管理端提供 Fireflies Management（Summary Records / Configuration / Cheat Sheet / Raw Data 四个 Tab），Ask Goldie 下新增 Goldie Base 页。

**谁用**：管理端 PGM / Super Admin（全部功能）、PM（Goldie Base 两个新 Tab 只读）、公司端创始人（Raw Data 看本人受邀会议的原文，以及 Goldie 召回）。

**涉及服务**（分工按设计第八章开头，第十章 #91）：

| 端 | 负责 |
|---|---|
| Java `CIOaas-api` | Configuration、Cheat Sheet（名册、专长标签、Email Domain、专家建议标签拒绝名单）、Raw Data（含公司端）、每日拉取与 Sync now；会议页的名册编辑与专家确认保存（前端直调，7 #Q44）；配套：新会议 / 公司增改经 SQS 交 Python、PGM/SA 判定方法、给 Python 的名册新建接口（Assign new external party 用） |
| Python `CIOaas-python` | 识别（P1 / P8）、提取与清洗（P2~P7）、中间表与投影入库、Summary Records 与矩阵、名册保存后的本场同步、保存后的证词补抽（7 #Q83、#Q87）、改判重算与自动路由、Goldie Base 两个新 Tab |
| Web `CIOaas-web` | Fireflies Management 页、会议详情 Review 页、原文页、名册历史页、Goldie Base 页 |

**关键假设**：

| # | 假设 | 出处 / 理由 |
|---|---|---|
| A1 | 页面、字段、文案、交互以设计稿为准；数据与业务规则以设计文档为准；两者冲突的列进第 7 节 | 约定 |
| A2 | Java 侧 Fireflies 表的时间列用 `timestamptz`（不用 ERL 的 `timestamp(6)`） | Python 直读这些表，带时区的类型两端都按 UTC 解释（7 #Q3） |
| A3 | Python 侧物理表名用 `ai_ff_*` | 设计第八章 #15（7 #Q2） |
| A4 | 审计只在 Python 侧建表（`ai_ff_audit_log`）；Java 侧的连接、邮箱域名、原文变化写应用日志 | 需求审计的「路由决策与覆写操作」都在 Python |
| A5 | 跨端读的数据权限（Python 直读 Java 表 / 经接口）不影响表结构，清单见 1.4 | — |
| A6 | 会话补 `organization_id`（设计第八章 #14）由 Java `c7892f54d` 实现，含存量会话回填接口 | Java 提交记录 |
| A7 | 迁移文件与执行顺序见 1.5 | 两端迁移约定 |

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
| P7 | `ai_ff_routing_row` | 路由中间表（矩阵正本与投影记录） | 新增 | Python | Python | 24 |
| P8 | `ai_ff_audit_log` | 审计：路由决策与覆写 | 新增 | Python | — | 11 |
| X1 | `ai_file_registry` | 知识库登记行：新增业务类型 `FIREFLIES` / `FIREFLIES_TESTIMONY` / `FIREFLIES_CROSS_COMPANY`（只改列注释） | 改造 | Python | Python、Java（已有实体映射，只写财务抽取行，不碰 Fireflies 行） | +0 |

Python 表编号 P6 空出（拒绝名单为 Java 表 J6，7 #Q45）。

不建新表的：LLM 调用记录复用 `ai_llm_call_log` / `ai_trace`；RAG 条目复用 `ai_rag_entry`（新增空间走代码种子 `rag/domain/enums.py`，只更新 `ai_rag_business_association.business_type` 列注释）；菜单行走管理后台配置（ERL 先例，见 1.4）。

**通用约定**

| 项 | Java 表 | Python 表 |
|---|---|---|
| 主键 | `id varchar(36)`，`@UuidGenerator` | `id VARCHAR(36)`，ORM `default=_uuid`，SQL `DEFAULT gen_random_uuid()::varchar(36)`；审计表用 `BIGSERIAL` |
| 审计列 | 继承 `AbstractCustomEntity`：`created_by` / `created_at` / `updated_by` / `updated_at`（`created_by` 等为 varchar(36)） | `created_by` / `created_at` / `updated_by` / `updated_at`，`updated_at` 配 `trg_ai_<表>_updated_at` 触发器 |
| 系统操作人 | 系统写入（定时拉取、SQS 消费、自动识别与提取）一律记 `"1"`（`CommonConstants.SYSTEM_USER_ID`），页面显示 `System`。拉取任务与消费者入口先 `SecurityUtils.setCurrentUserId("1")`、`finally` 里 `clearCurrentUserId()`（基类 `@PreUpdate` 无条件用线程里的用户覆盖 `updated_by`，不设会写成空） | 同样记 `"1"`（审计 `operator`、各表 `created_by` / `updated_by`）；由人引起的系统动作另记触发人（审计 `triggered_by`） |
| 时间 | `timestamptz`（A2）；Java 字段 `Instant`；有效期 `date` / `LocalDate` | `TIMESTAMPTZ` |
| 枚举 | `varchar(16~32)` + `@Enumerated(STRING)`，不加 CHECK，取值写进列注释 | `VARCHAR(16~32)` + `domain/enums.py` StrEnum，不加 CHECK，取值写进列注释 |
| 数组 / 对象 | `jsonb`（`@JdbcTypeCode(SqlTypes.JSON)`） | `JSONB`；非空数组 `DEFAULT '[]'`，可空列 `JSONB(none_as_null=True)` |
| 软删 | 6 张表都不设（只追加或物理删除） | P5、P7 软删：`deleted BOOLEAN NOT NULL DEFAULT FALSE`，配 `WHERE deleted = FALSE` 部分索引；其余只追加、物理删除或整场先删后写 |
| 外键 | 不建，应用层软引用 | 不建，应用层软引用 |
| 命名 | `pk_ff_<表>` / `uk_ff_<表>_<列>` / `idx_ff_<表>_<列>` | `pk_ai_ff_<表>` / `uk_…` / `idx_…` |
| 邮箱 | 一律存小写，比较忽略大小写 | 同左 |

### 1.2 Java 表

#### J1 `ff_connection_configuration`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `organization_id` | varchar(36) | 否 | — | 租户，一个租户一条 | 9.2.1 |
| `api_key_cipher` | text | 是 | — | API key 密文（AES-GCM，密钥取 Nacos `cio.fireflies.encryption`，1.4）；未连接或已移除为空。掩码（`••••a3f9`）由查询接口服务端解密后拼好返回，不另存后 4 位；原文与密文都不出接口 | 9.2.3、设计稿 1.2 |
| `account_email` | varchar(255) | 是 | — | key 持有者账号（Fireflies `user` 查询），页面「connected as …」；重新 Link 时比对，换了账号按首次连接处理（9.2.6），写应用日志。设计 9.2.3 的 `account_name` 不存 | 9.2.3、9.2.6 |
| `connection_status` | varchar(16) | 否 | `'UNCONNECTED'` | 连接状态：`UNCONNECTED`（未连接）/ `CONNECTED`（已连接）/ `FAILED`（key 鉴权失败）/ `DISCONNECTED`（连续 N 次非鉴权失败而断开） | 9.2.4 |
| `last_success_sync_at` | timestamptz | 是 | — | 最近一次成功完成的拉取；只记成功；换账号时清空 | 9.2.6 |
| `consecutive_failures` | int | 否 | `0` | 连续非鉴权失败次数，达阈值 N 转 `DISCONNECTED` | 9.2.4 |
| `sync_started_at` | timestamptz | 是 | — | 非空 = 正在同步：拉取开始时条件 UPDATE 抢占（为空或已超时才能抢到），结束清空；定时与手动互斥，页面「是否正在同步」读它 | 9.2.6 |
| `email_domains` | jsonb | 否 | `'[]'` | 本机构邮箱域名数组（Cheat Sheet 底部 Email Domain 维护）：小写、去 `@`，不能是公共邮箱域名，租户内不重复（代码校验）；识别 ① 整份读取 | 9.7.7、1.9 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计（基类） | |

- 主键 `pk_ff_connection_configuration (id)`；唯一 `uk_ff_connection_configuration_org (organization_id)`
- 设计 9.2.3 的 `last_attempt_at` / `last_error` 不存：拉取失败的时间与原因写应用日志
- 状态流转：`UNCONNECTED → CONNECTED`（Link 成功）；`CONNECTED → FAILED`（鉴权错误）；`CONNECTED → DISCONNECTED`（连续 N 次非鉴权失败）；`FAILED / DISCONNECTED → CONNECTED`（Link 或 Sync 成功）；任意 → `UNCONNECTED`（Remove：清空密文，7 #Q1）
- `FAILED` 与 `UNCONNECTED`（含 Remove 之后）定时拉取跳过该租户（9.2.4）
- 一个租户一行，第一次 Link 或第一次保存邮箱域名时创建（先配域名的建行时状态 `UNCONNECTED`）；Remove 只清密文、状态回 `UNCONNECTED`，这一行、域名、`account_email` 与 `last_success_sync_at` 保留：重新 Link 同一账号接着增量拉，换账号按 9.2.6 首次连接处理；谁移除的写应用日志
- 设计 9.7.7 的 `ff_email_domain` 表并入本列 `email_domains`（总是整份读写）；改动写应用日志；GS 租户的 3 个初始域名上线时由管理员在页面添加（7 #Q5）

#### J2 `ff_meeting_meta_info`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `organization_id` | varchar(36) | 否 | — | 连接所属租户，隔离依据 | 9.3.2 |
| `fireflies_id` | varchar(64) | 否 | — | Fireflies 原生 id，页面展示的会议 id | 9.3.2 |
| `title` | varchar(512) | 是 | — | 仅展示与检索，禁止用于类型识别 | 1.9 |
| `started_at` | timestamptz | 否 | — | 会议开始时间，取 Fireflies `dateString`，存 UTC | 9.3.2 |
| `duration_minutes` | numeric(8,2) | 是 | — | Fireflies `duration`（单位分钟） | 9.3.2 |
| `participants` | jsonb | 否 | `'[]'` | 受邀邮箱数组，入库转小写 | 1.9、9.3.6 |
| `attendance` | jsonb | 否 | `'[]'` | 出席记录（实际进入会议的人），每项 `{name, join_time, leave_time}`，Fireflies `meeting_attendance` 原样保存。只有姓名、没有邮箱（#92）：Raw Data 照原样显示，并作 P8 推断参会人身份的线索，不作参会人姓名 | 9.3.2、#92 |
| `speakers` | jsonb | 否 | `'[]'` | 发言人名单，每项 `{id, name}`（Fireflies 说话人 id、会议显示名）。`id` 即逐句表的 `speaker_id`，只在本场唯一；识别时按姓名对邮箱前缀把说话人绑到参会人（P3），没发言的人不在这里 | 9.3.2 |
| `overview` | text | 是 | — | Fireflies `summary.overview`，GS → 创始人摘要的来源 | 1.3、2.3 |
| `content_hash` | varchar(64) | 是 | — | 逐句与元信息的摘要哈希；回看重拉时比对，已投递的会议内容变了写一条警告日志（设计 9.10.2 的 `TRANSCRIPT_CHANGED`） | 9.3.1 |
| `dispatched_at` | timestamptz | 是 | — | 投递给 Python 识别成功的时间；非空 = 已进入识别，回看不再改原文（拿到 SQS 发送成功结果才写，见下方「投递与补投」） | 9.3.1、第八章 #30 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计（基类，系统写入记 `"1"`）。`created_at` 即首次入库时间（会议行只在首次拉到时插入，回看重拉与补拉句子都更新同一行）；Raw Data 的 `Ingested at` 列与原文页的 `captured` 读它（设计 9.3.2 的 `ingested_at` 不另存） | 9.3.3、9.3.5 |

- 主键 `pk_ff_meeting_meta_info (id)`
- 设计 9.3.2 的 `calendar_type`、`host_email`、`organizer_email`、`transcript_url`、`meeting_link`、`word_count` 不存（设计 9.3.5 页头的 `9,420 words` 不做）
- 唯一 `uk_ff_meeting_meta_info_org_ffid (organization_id, fireflies_id)` —— 幂等 upsert 的依据
- 索引
  - `idx_ff_meeting_meta_info_org_started (organization_id, started_at DESC)` —— Raw Data 列表默认按日期倒序、按日期范围筛选
  - `idx_ff_meeting_meta_info_participants_gin USING gin (participants jsonb_path_ops)` —— 公司端「本人受邀的会议」（`participants @> '["<email>"]'`）、按邮箱筛参会人；按显示名筛时匹配 `attendance`，不另建索引
  - `idx_ff_meeting_meta_info_undispatched (organization_id, created_at) WHERE dispatched_at IS NULL` —— 每次拉取开始时补投未投递成功的会议
- **Java 只拉数据，不判定 Invalid**（设计 9.3.2 的 `validity` 不建）：只入库 Fireflies 已处理完的会议（`meeting_info.summary_status = 'processed'`），处理中的跳过、由下次拉取的 72 小时回看补上，超过回看窗口仍未处理完的不再拉。入库的会议不论有没有句子都投递给 Python；转录为空与无实质内容统一由 Python 判，记 `ai_ff_meeting_state.identification_result = NO_SUBSTANCE`，Raw Data 的 Invalid 徽标与筛选只读它。投递后原文不再改
- **投递与补投**（7 #Q6）
  - `SQSService` 新增一个返回成败的发送方法，复用私有的 `sendMessageToSqs`（成功返回消息 id、失败返回空）；现有 `sendMessage` 不改
  - 每场会：入库事务提交 → 发消息 → 拿到消息 id 才写 `dispatched_at`；失败不写、打 ERROR 日志，接着处理下一场（先提交再发，Python 才读得到会议；先发后写，最坏只是重发一次）
  - 每次拉取（每日定时、Sync now）开始时，先补投本租户 `dispatched_at` 为空的会议，消息带本次拉取的触发方式与触发人。按「未投递」查、不按会议时间，不受 72 小时回看限制，也不设次数上限，每次失败一条 ERROR 日志
  - 未投递的会议被回看重拉到时照常整场重写（upsert 元信息、逐句先删后插）
  - Python 收到同一场会的重复消息，按 P1 `meeting_id` 唯一跳过。已知：发送成功而写 `dispatched_at` 失败时下次拉取会重发（Python 跳过），其间回看拉到改过的原文会覆盖
  - 投递成功后 Python 处理失败不归 Java：处理中被打断由 SQS 重投接手、从头重跑，最多 3 次，仍没跑完交定时清扫（P1「卡死兜底」）；大模型最终失败按设计 6.11 作废、会议进 Pending（待识别）

#### J3 `ff_meeting_sentence`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `meeting_id` | varchar(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | 9.3.2 |
| `sentence_order` | int | 否 | — | 句子在转录中的先后顺序，取 Fireflies `index`（不叫 `order`：PostgreSQL 保留字） | 9.3.2 |
| `speaker_id` | int | 是 | — | 与 `speakers[].id`、P5 / P7 的 `speaker_ref` 同值 | 6.3 |
| `speaker_name` | varchar(255) | 是 | — | 会议显示名，原样 | 9.3.5 |
| `text` | text | 否 | — | Fireflies `text`（有人在 Fireflies 编辑器改过的取改后版本）；原文页显示、大模型输入、时间戳回查、近逐字比对都用它 | 9.3.5、6.3 |
| `start_time` | numeric(10,3) | 是 | — | 浮点秒 | 9.3.5 |
| `end_time` | numeric(10,3) | 是 | — | 浮点秒 | 9.3.2 |

- 主键 `pk_ff_meeting_sentence (id)`
- 唯一 `uk_ff_meeting_sentence_meeting_order (meeting_id, sentence_order)` —— 原文页按 `sentence_order` 区间分批加载、提取时整场按序读取
- 设计 9.3.2 的 `raw_text` 不存：需要追溯时可按会议 id 向 Fireflies 重拉
- 不带审计列（批量子表，整场先删后插，9.3.1），实体不继承 `AbstractCustomEntity`（偏离 `standards/architecture.md`：线上 `ddl-auto: update` 会按实体自动加审计列）；不按租户分区（约 73 万句 / 年，9.3.2，过千万再评估）

#### J4 `ff_cheat_sheet`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键。一行即一个版本（同一人每改一次追加一行），「哪一版」用这一行的 `id` 表示；参会人表的 `cheat_sheet_id` 记它 | 9.7.1 |
| `organization_id` | varchar(36) | 否 | — | 租户 | 9.7.1 |
| `name` | varchar(255) | 否 | — | 唯一识别符，同一人各版本同值；新建时租户内重名（忽略大小写）不拒绝、不合并，自动加数字后缀（Tom → Tom1 → Tom2，取第一个未占用编号，7 #Q46） | 9.7.1 |
| `emails` | jsonb | 否 | `'[]'` | 邮箱数组，小写 | 9.7.1 |
| `organization` | varchar(255) | 否 | — | 外部机构名 | 9.7.1 |
| `role` | varchar(32) | 否 | — | 角色：`LP` / `STRATEGIC_PARTNER`（战略合作方）/ `EXIT_PARTNER`（退出合作方）/ `FOUNDER`（不使用 LG 平台的创始人）/ `GS_STAFF`（GS 人员）/ `OTHER`（其他） | 5.2 |
| `expertise_tags` | jsonb | 否 | `'[]'` | 标签文本数组；非空即专家 | 1.11 |
| `area_of_expertise` | varchar(2048) | 是 | — | 专业领域，自由文本，仅作描述、不参与路由；前后端同按 2048 字校验 | 9.7.1 |
| `valid_from` | date | 否 | — | 有效期起始日（页面 Validity period 的 From），按会议日期回溯版本时用 | 9.7.2 |
| `valid_to` | date | 是 | — | 有效期截止日；空 = 至今（页面显示 `present`） | 9.7.2 |
| `source` | varchar(32) | 否 | `'MANUAL'` | 来源：`MANUAL`（Cheat Sheet 页手工新增）/ `FF_SUMMARY_RECORDS`（审核会议时登记，含专家确认） | 9.7.1 |
| `source_meeting_id` | varchar(36) | 是 | — | 从会议页登记或专家确认时的来源会议（`ff_meeting_meta_info.id`）；History 的 Updated by 显示实际操作人（`updated_by`） | 9.7.1 |
| `reviewed_by` | varchar(36) | 是 | — | 「看过无需修改」的复核人 | 9.7.5 |
| `reviewed_at` | timestamptz | 是 | — | 复核时间；用 `@Modifying` 单独 UPDATE，不经实体保存（基类 `@PreUpdate` 会改写 `updated_at`，破坏版本裁决） | 9.7.5 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计；`updated_at` = 写入时间，是重合裁决的依据（只追加，不改） | 9.7.2 |

- 主键 `pk_ff_cheat_sheet (id)`
- 索引
  - `idx_ff_cheat_sheet_org_name (organization_id, name)` —— 列表取各人当前版本、History、按会议日期回溯
  - `idx_ff_cheat_sheet_emails_gin USING gin (emails jsonb_path_ops)` —— 识别 ④ 按邮箱查名册、拒绝名单按人展开邮箱
- 只追加：每次保存（Cheat Sheet 页 Confirm、会议页 Edit external party、专家确认 Save）追加一条完整的新行，不改旧行（7 #Q44）；复核只改 `reviewed_*`

#### J5 `ff_expertise_tag`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | varchar(36) | 否 | — | 主键 | |
| `organization_id` | varchar(36) | 否 | — | 租户 | 9.8.2 |
| `name` | varchar(64) | 否 | — | 标签文本 | 9.8.2 |
| `preset` | boolean | 否 | `false` | 是否预置的 7 项（预置的不可删） | 9.8.3 |
| `sort_no` | int | 否 | — | 展示顺序；预置 1~7（Fundraising 6、Market 7），新增追加 | 9.8.1 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ff_expertise_tag (id)`
- 唯一 `uk_ff_expertise_tag_org_name (organization_id, lower(name))` —— 租户内不区分大小写重名
- 索引 `idx_ff_expertise_tag_org_sort (organization_id, sort_no)` —— 下拉按顺序列出
- 物理删除（只有从未被用过的标签能删，9.8.3）
- 预置 7 项（7 #Q4；带定义，证词按各专家的标签抽，7 #Q85，同设计 9.8.1）：新建组织时写入（`OrganizationServiceImpl.save` 在初始化 KPA、Tech Stack 之后加一行调用）；存量组织由 Java V1 迁移 `INSERT … SELECT … FROM organization` 补齐（`sort_no` 1~7，`ON CONFLICT DO NOTHING`，可重跑）。不做懒加载：Python 直读本表（P7 专家推测的标签清单）

#### J6 `ff_expert_rejection`

专家建议标签的拒绝名单，由 Java 在专家确认保存的同一事务里写（7 #Q45）。

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
- 写：只有 API-08（专家确认保存）在同一事务里写：驳回 = 本次建议标签 − 保存后的 Expertise tags（7 #Q51）；邮箱取 P2 该参会人的本场邮箱
- 读：Python 只读——识别前从大模型标签里去掉（建议标签 = 大模型标签 − T1 − 拒绝名单，T1 见 P2 `expertise_tags`）、详情 `resolvedAs`、同步（API-28）判已驳回；「按人展开」：本场邮箱或此人名册各版本任一邮箱命中即算

### 1.3 Python 表

#### P1 `ai_ff_meeting_state`

即设计 9.5.9 的 `ff_meeting_state`。一场会一行，与 `ff_meeting_meta_info` 一对一；Python 收到投递时建行。为列表免跨表 JOIN（Python 仓储只做单表）冗余了几个原文侧字段——投递后原文不再改（9.3.1），冗余值不会过期。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | 9.5.9 |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | 1.1 |
| `fireflies_id` | VARCHAR(64) | 否 | — | 冗余：列表显示 id（原样，不加 `#`）、按 id 搜索 | 设计稿 1.1 |
| `title` | VARCHAR(512) | 是 | — | 冗余：列表、搜索、Goldie Base 卡片标题 | 设计稿 1.1 |
| `started_at` | TIMESTAMPTZ | 否 | — | 冗余：排序、时间筛选、会议日期（业务日期）、名册回溯 | 9.3.3 |
| `duration_minutes` | NUMERIC(8,2) | 是 | — | 冗余：列表 `52 min` | 设计稿 1.1 |
| `meeting_type` | VARCHAR(16) | 否 | `'UNKNOWN'` | 会议类型：`GS_FOUNDER`（GS → 创始人）/ `GS_LP`（GS → LP）/ `GS_INTERNAL`（GS 内部）/ `GS_PARTNER`（GS → Partner）/ `UNKNOWN`（判不出）；当前生效值 | 9.5.2 |
| `meeting_status` | VARCHAR(16) | 是 | — | 会议状态：`PASSED`（已放行）/ `PENDING`（待处理）；首轮未完成或 `Invalid` 为空（不进列表）。重新提取（Start Extraction、自动路由）进行中保持开始前的值，`pending_reasons` 同，提取结束按设计 6.11 重判；列表照旧显示，详情页按 `extraction_status = RUNNING` 显示「提取中」 | 1.10 |
| `pending_reasons` | JSONB | 否 | `'[]'` | Pending 原因：`TO_IDENTIFY`（待识别）/ `TO_CONFIRM_EXPERT`（待确认专家）/ `TO_REVIEW`（待审核），可并存；页面不显示原因（列表与详情页都只显示 Pending），红点按 Pending 会议总数计，状态筛选只分 Passed / Pending（7 #Q25d） | 9.4.2 |
| `portfolio_ids` | JSONB | 否 | `'[]'` | Portfolio 标记，`company_group` id | 9.5.4 |
| `processing_stage` | VARCHAR(16) | 否 | `'IDENTIFYING'` | 首轮自动加工进度：`IDENTIFYING`（识别中）/ `EXTRACTING`（提取中）/ `DONE`（完成）；`DONE` 且 `meeting_status` 非空才进列表；之后只有名册变更重跑会改回 `IDENTIFYING`（重跑期间会议暂时离开列表，7 #Q84 ①）。`Invalid` 与待识别的会议识别完即置 `DONE`、不经 `EXTRACTING`，`Invalid` 的 `meeting_status` 保持为空（停在 `IDENTIFYING` 会被当成卡死） | 1.10 |
| `processing_started_at` | TIMESTAMPTZ | 否 | — | 首轮本次处理的开始时间（建行时写入），兼作处理者凭证。首轮每次开跑（建行或接手重跑）先删本场全部产出（P2~P5、P7），从识别第一步跑起，产出跑完才算数（7 #Q13）。收到消息按本行分三种：① 没有本行 → 建行处理；② `DONE` → 重复消息，删掉；③ 仍在 `IDENTIFYING` / `EXTRACTING`：重投（`ApproximateReceiveCount` ≥ 2，上一处理者活着时会一直延长不可见时间）直接接手从头重跑、不看时间；首次收到（= 1）却已有本行是 Java 重复发送，删掉本条。接手时条件更新本列（`WHERE processing_started_at = <读到的值>`，0 行即已被别的实例接手，退出、**不删消息**）；每个阶段落库的事务先锁本行核对本列，对不上即丢弃结果退出、同样不删消息（旧回执可能删掉新持有者的消息）。重跑次数看 `ApproximateReceiveCount`；第 3 次（队列上限）仍没跑完，打 ERROR、不删消息，消息进死信，本行停在处理中、不进列表，见「卡死兜底」。大模型最终失败按设计 6.11 作废（设计 1.10、第八章 #30 的 `processing_attempts` / 心跳不存） | 1.10、第八章 #30 |
| `extraction_status` | VARCHAR(16) | 是 | — | 最近一次提取任务的状态：`RUNNING`（进行中）/ `SUCCEEDED`（成功）/ `VOIDED`（作废） | 9.5.1 |
| `extraction_trigger` | VARCHAR(24) | 是 | — | 该任务的发起方：`AUTO`（首轮自动提取）/ `AUTO_ROUTE`（公司增改后自动路由）/ `START_EXTRACTION`（管理员点 Start Extraction，含改判前补跑 P1）——作废后都置待识别，审计按它区分触发方式 | 6.11 |
| `extraction_started_at` | TIMESTAMPTZ | 是 | — | 最近一次提取开始时间。非首轮的提取（Start Extraction、自动路由、改判前补跑 P1）被打断后没有重投，靠定时清扫判超时：`extraction_status = RUNNING` 且本列超过卡死时限（120 分钟，写死，[定时清扫开发设计](../../卡死任务清扫/开发设计/dev-design-doc.md)第 3 节），条件更新（`WHERE extraction_status = 'RUNNING' AND extraction_started_at = <扫到的值>`）作废该次提取（规则同设计 6.11），Start Extraction 恢复可点 | 6.11、第八章 #30 |
| `identification_result` | VARCHAR(32) | 是 | — | 识别阶段的结果，识别跑完后写：`NORMAL` / `NO_SUBSTANCE`（会议 Invalid，不进列表：转录为空——识别第一步程序检查，没有句子即判、不调 P1；或 P1 判无实质内容。Raw Data 只读它显示 `Invalid`）/ `QUALITY_CHECK_FAILED`（P1 最终失败：待识别；自动路由跳过）/ `ATTENDEE_INFERENCE_FAILED`（P8 最终失败：待识别）。同时出现时按 `NO_SUBSTANCE` > `QUALITY_CHECK_FAILED` > `ATTENDEE_INFERENCE_FAILED` 只记一个，被盖掉的失败仍记在 `IDENTIFY` 审计。设计 9.5.9 的 `p1_status` / `p8_status` 合并为本列。改判为 GS 内部 / Partner 时补跑 P1：与上次成功提取的类型（`current_extraction_input` 里的）比，没变不补；快照为空按改了算；本列为 `QUALITY_CHECK_FAILED`、类型是这两类的也补（7 #Q50）。补跑成功不改本列，首轮 P1 失败的会议以后每次 Start Extraction 都会补跑 | 6.4、6.11、6.13、9.3.4、9.4.2、9.9.2、9.9.3 |
| `current_extraction_input` | JSONB | 是 | — | 当前线上内容提取时用的输入：类型、保留的公司、每位参会人的身份 / 组织 / 公司 / 专长标签、说话人对到谁（示例见 code-examples 第 3 节）；**不存提取出的内容**。只用来判断「参会人有没有改过」：拿最新识别结果和它比，有差异则 Start Extraction 激活（例外规则见设计 9.9.1）。提取成功时写入（首轮自动提取、自动路由、Start Extraction），改 Unknown 应用后清空。专长标签不参与比对（设计 9.9.1，7 #Q87）；名册同步（API-28）与登记（API-25）后，本场没有参会人改动时，把标签变了的专家的标签同步成 P2 新值并启动证词补抽（见 API-28，7 #Q83、#Q87）。同时改了角色等其他字段的仍比得出差异、照常激活 | 9.5.1、9.9.1 |
| `unknown_by_admin` | BOOLEAN | 否 | `FALSE` | 管理员把类型改成 `Unknown` 并应用（API-23）时置 `TRUE`：名册变更不自动重跑它（7 #Q89）。重新定类型点 Start Extraction（API-22）时清回 `FALSE`；首轮接手重跑时随本行回到初值 | 9.9.2、9.9.3 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_meeting_state (id)`
- **防过期提交用 `updated_at`**（设计 9.6.5「并发」，不另设 `lock_version`）：详情页加载时返回 `updated_at`，写操作带回它做条件更新 `WHERE id = ? AND updated_at = ?`，0 行即页面已过期、拒绝并提示刷新。凡改变本场可提交内容的写入都要更新本行（触发器刷新 `updated_at`）：应用、Start Extraction、矩阵行内 Save、登记或关联说话人、名册同步（API-28），以及系统侧的自动路由、提取完成、补抽返回；只改子表的也要同时「碰」一下本行。代码里注明这是乐观锁
- 唯一 `uk_ai_ff_meeting_state_meeting (meeting_id)` —— 一对一；投递重复时幂等
- 索引
  - `idx_ai_ff_meeting_state_list (organization_id, started_at DESC) WHERE meeting_status IS NOT NULL` —— Summary Records 列表默认排序、时间筛选
  - `idx_ai_ff_meeting_state_status (organization_id, meeting_status, meeting_type)` —— 按状态、类型筛选；Tab 红点计数；自动路由找「待识别的 GS → 创始人」
- **卡死兜底**（7 #Q12、#Q13）：首轮被打断由 SQS 重投接手（`processing_started_at`）；其余六类交定时清扫：① 连续 3 次没跑完的首轮会议，不再重跑，按失败收尾、转 Pending；② 已投递却没有本行的会议（`dispatched_at` 超时；可能误报，重投 Python 按会议去重）；③ 非首轮提取卡在 `RUNNING`；④ 证词补抽卡在 `RUNNING`；⑤ 投影卡在 `PENDING` 的中间表行（含摘要行的「只替换摘要」，按该行当前状态重推，7 #Q30）；⑥ 应下线却没下成的 RAG 条目：已删或已取消授权、仍挂着 `file_id`、下线重试用尽停在 `FAILED` 的 P7 行（会议转回 Pending 后仍已授权的归 ⑤，7 #Q88）、改正文后撤旧用尽的旧条目（审计 `after_value.replacedFileId`）、回写 `file_id` 前进程被杀留下的孤儿条目（后两种是不被任何 P7 行引用的 Fireflies 登记行）。③④⑤ 在 Python 进程内执行，只能靠超时解锁；不在打开详情页、点按钮时判超时。判定条件、动作与时限见 [卡死任务清扫开发设计](../../卡死任务清扫/开发设计/dev-design-doc.md) 第 3、4 节
- 不冗余采纳的公司：列表的 Companies 列按本页会议 id 批量查 P4（`meeting_id IN (...) AND adopted = TRUE`）；按公司搜索 / 筛选先得公司 id，再经 P4 的 `idx_ai_ff_meeting_company_org_company` 取会议 id
- 状态流转：`processing_stage` `IDENTIFYING → EXTRACTING → DONE`，`Invalid` 与待识别的 `IDENTIFYING → DONE`；`meeting_status` `null → PENDING / PASSED`（`Invalid` 保持 `null`），`PENDING ↔ PASSED`（应用、改 Unknown、重新提取结束后重判）；`extraction_status` `RUNNING → SUCCEEDED / VOIDED`
- **不设草稿，重新提取整场替换**（不做设计 9.6.4 的草稿）：点 Start Extraction 即保存页头（类型、公司、参会人写进识别结果），本场全部旧产物下线（中间表行、专家候选与知识库条目软删，未处理的候选置 `WITHDRAWN`），然后重新解析；成功后按授权初值落库（设计 9.9.5：跨公司与经 P8 识别的证词不勾、其余勾），落了行即 `Pending`（待审核）、整场先不投影，应用后才 `Passed`、才投影（7 #Q81）；失败则转 `Pending`（待识别 · 提取失败），旧内容不恢复。解析期间 Goldie 召回不到这场会。人工措辞、勾选与 Play candidate 都不保留（措辞可从 `CONTENT_EDIT` 审计找回）。`Discard Changes` 只撤销页面上未提交的改动；补抽的证词（7 #Q83、#Q87）直接替换此人原有的证词行、默认勾选，等 Confirm & Apply 上线（设计 2.5）

#### P2 `ai_ff_meeting_participant`

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键；P8 的 `attendee_ref` | 6.13 |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `email` | VARCHAR(255) | 否 | — | 受邀者为受邀邮箱；名册说话人取名册会议日期那版的第一个邮箱；按 LG 账号登记的取账号邮箱；小写 | 9.5.9、#92 |
| `matched_name` | VARCHAR(255) | 是 | — | 已对上的发言人名（多个取句数最多的），没配上为空 | 1.8、#92 |
| `invited` | BOOLEAN | 否 | — | 是否在受邀名单里 | 1.9 |
| `role` | VARCHAR(32) | 否 | `'UNIDENTIFIED'` | 身份：`GS_STAFF`（GS 人员）/ `FOUNDER`（创始人）/ `LP` / `STRATEGIC_PARTNER`（战略合作方）/ `EXIT_PARTNER`（退出合作方）/ `OTHER`（其他）/ `UNIDENTIFIED`（未识别）。LG 平台用户（识别 ②）在名册有会议当日生效的记录时以记录的角色为准，名册同步（API-28）也按它刷新；改离 Founder 后不再按平台账号挂到被投公司（7 #Q47） | 1.9 |
| `match_step` | VARCHAR(24) | 是 | — | 命中识别链的哪一步：`GS_DOMAIN`（① GS 邮箱域名）/ `LG_USER_EMAIL`（② LG 用户完整邮箱）/ `LG_USER_DOMAIN`（③ 公司 Team 域名）/ `CHEAT_SHEET_EMAIL`（④ 名册邮箱）/ `AI_INFERRED`（⑥ 姓名候选经 P8 核对、⑦ P8 推断）/ `MANUAL`（人工登记、关联或指定）；未识别为空 | 1.9、9.5.9 |
| `lg_user_id` | VARCHAR(36) | 是 | — | ② 命中的 LG 用户 | 1.9 |
| `company_id` | VARCHAR(36) | 是 | — | 公司方参会人所属公司（② / ③ 得出）；名册或 P8 的 Founder 为空 | 2.1 |
| `cheat_sheet_name` | VARCHAR(255) | 是 | — | Cheat Sheet 引用键（姓名） | 9.7.1 |
| `cheat_sheet_id` | VARCHAR(36) | 是 | — | 识别时按会议日期取到的那一行 `ff_cheat_sheet.id`（一行即一个版本），名册同步（API-28）时随之刷新；P8 输出的 `registry_id` 即它 | 9.5.9 |
| `display_name` | VARCHAR(255) | 是 | — | 胶囊显示名 | 9.5.5 |
| `organization` | VARCHAR(255) | 是 | — | 胶囊显示的组织 | 9.5.5 |
| `expertise_tags` | JSONB | 否 | `'[]'` | 补充识别：会议日期生效版本的专长标签；登记时由 API-25 就地刷新，Edit external party 与专家确认框保存后由名册同步（API-28）按名册当日生效版本刷新；刷新后标签变了的专家，本场没有参会人改动时同步进 P1 快照并补抽证词（见 P1 `current_extraction_input`，7 #Q87）。提取时本列与 `cheat_sheet_id` 即建议标签的扣除基准 T1：建议标签 = 大模型标签 − T1 − 拒绝名单（J6）（7 #Q44） | 1.11 |
| `ai_inferred_identity` | JSONB | 是 | — | AI（P8）推断的此人身份：`{confidence, evidence, name, role, organization, registry_id}`（P8 原样输出，`registry_id` 即 `ff_cheat_sheet.id`），不采纳的也存 | 6.13 |
| `testimony_backfill_status` | VARCHAR(16) | 是 | — | 专家的证词补抽状态：`QUEUED`（排队中）/ `RUNNING`（补抽中）/ `FAILED`（补抽失败，可重试）；空 = 没有补抽或已成功。名册同步（API-28）、登记（API-25）后标签变了的专家与 Retry（API-29）置 `RUNNING`（7 #Q83、#Q87）；同一场会一次只补一人，本场已有人 `RUNNING` 或 `QUEUED` 时改置 `QUEUED`，一人收尾时同一事务把下一个排队的置 `RUNNING`（7 #Q86）。定时清扫：`RUNNING` 且本行 `updated_at` 超过卡死时限，置 `FAILED`（条件更新），本场 `QUEUED` 的一并 `FAILED`，页面出现 Retry（不另设开始时间列） | 2.5 |
| `testimony_tags` | JSONB | 是 | — | 上次为此人抽证词所用的专长标签集合（首次提取与每次补抽成功时写入；标签清空、证词行软删时写 `[]`；空 = 从没为他抽过证词）。补抽前与他名册里会议当日生效的标签（即名册同步带回的 P2 `expertise_tags`；补抽不重读名册，7 #Q48、#Q51）比：相同不补，不同即按他当前全部标签整块重抽（7 #Q87） | 2.5 |
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
| `bind_source` | VARCHAR(24) | 是 | — | 绑定方式：`NAME_PREFIX`（程序按姓名对邮箱前缀）/ `AI_INFERRED`（P8 `speaker_map` 给出 `high`）/ `MANUAL_CHEAT_SHEET`（管理员登记进名册）；空 = 未绑定 | 1.9、#92 |
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
| `assigned_by` | VARCHAR(36) | 是 | — | 人工指定人（仅留痕，页面不展示） | 9.5.3 |
| `assigned_at` | TIMESTAMPTZ | 是 | — | 人工指定时间（同上） | 9.5.3 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_meeting_company (id)`
- 唯一 `uk_ai_ff_meeting_company_meeting_company (meeting_id, company_id)` —— 补跑 P1 按公司 upsert；Summary Records 列表按本页会议 id 批量取 Companies 列
- 索引 `idx_ai_ff_meeting_company_org_company (organization_id, company_id) WHERE adopted = TRUE` —— Summary Records 按公司搜索 / 筛选

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
| `decided_by` | VARCHAR(36) | 是 | — | 处理人：保存后触发同步（API-28）的管理员（自动消解的同样记他） | 9.5.6 |
| `decided_at` | TIMESTAMPTZ | 是 | — | 处理时间 | 9.5.6 |
| `deleted` | BOOLEAN | 否 | `false` | 软删 | 9.5.10 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_expert_candidate (id)`
- 索引 `idx_ai_ff_expert_candidate_meeting (meeting_id)` —— 按会议读、撤下（重新提取 / 改 Unknown）、删除（首轮重跑）本场建议标签；同一场同一人同一标签不重复由写入逻辑保证（提取时按人、标签去重），不设唯一约束
- 索引 `idx_ai_ff_expert_candidate_pending_tag (organization_id, tag) WHERE status = 'PENDING' AND deleted = FALSE` —— Java 删标签前查「正被未处理标记引用」
- 状态流转：`PENDING → ACCEPTED / DECLINED`（保存后的名册同步 API-28，含自动消解的标签；既不在记录也不在拒绝名单的保持 `PENDING`）；`PENDING → WITHDRAWN`（重新提取或改 Unknown 应用时仍未处理的，随旧产物软删）；会议状态只看未软删的 `PENDING` 行

#### P6（已改为 Java 表）

见 J6 `ff_expert_rejection`（7 #Q45）；编号空出、不复用。

#### P7 `ai_ff_routing_row`

一行 = 一个 Authorize 格（设计 9.6.6）。三类知识库去向下摘要与正文各占一行、各自编辑与授权（7 #Q9），但合投一条知识库条目，两行共用该条目的 `ai_rag_entry_id` / `file_id`，摘要跟着正文走（7 #Q42）；跨公司与证词一行投一条条目：跨公司每场一行、证词每位发言人每版一行，一行里是合并后的多条内容（7 #Q77）。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | 否 | — | 主键 | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | |
| `meeting_id` | VARCHAR(36) | 否 | — | 所属会议（`ff_meeting_meta_info.id`） | |
| `meeting_started_at` | TIMESTAMPTZ | 否 | — | 冗余会议开始时间（同 P1 `started_at`）：Goldie Base 两个新 Tab 按会议日期筛选（7 #Q23）；排序不用它（7 #Q72） | 9.11.4 |
| `meeting_title` | VARCHAR(512) | 是 | — | 冗余会议标题（同 P1 `title`）：两个新 Tab 的关键词同时匹配会议名称（7 #Q23） | 9.11.4 |
| `destination` | VARCHAR(24) | 否 | — | 去向：`KB_APP`（公司端知识库，GS → 创始人）/ `KB_ADMIN`（管理端公司层知识库，GS 内部与 Partner）/ `FUND_LEVEL`（设计的「机构层」：GS → LP 的基金层摘要 + 正文，`company_id` 为空）/ `CROSS_COMPANY`（跨公司内容）/ `TESTIMONY_ANON`（证词匿名版）/ `TESTIMONY_SIGNED`（证词署名版）；决定投影到哪个空间，组合键见 1.4 | 9.6.6 |
| `output_type` | VARCHAR(16) | 否 | — | 产出类型：`SUMMARY`（摘要，1a / 1b）/ `KB`（知识库正文：Founder KB / Portfolio KB）/ `CROSS_COMPANY`（跨公司内容）/ `TESTIMONY`（专家证词，每位发言人两版各一行，7 #Q77）。三类知识库去向下同一（去向, 公司）摘要一行、正文一行，各一个 Authorize（7 #Q9），合投一条条目：正文行内容为条目正文，摘要行内容为条目的 `summary`（7 #Q42） | 9.6.2 |
| `company_id` | VARCHAR(36) | 是 | — | `KB_APP` / `KB_ADMIN` 必填 | 6.11 步骤 7 |
| `content` | TEXT | 否 | `''` | 内容：摘要行为摘要（≤150 个英文单词）；知识库行为 markdown 正文（原始转录链接在投影时附加，不存）；跨公司为本场各条 `statement`、证词为该发言人本场各条正文，合成一块文本：每条一段，段首单独一行是程序加的类别标签 `**<类别>**`，段间空一行（7 #Q77）；证词不含来源行。设计 9.6.6 的 `summary` 列不建 | 1.3、9.6.3 |
| `speaker_participant_id` | VARCHAR(36) | 是 | — | 仅证词：证词发言人对应的参会人（P2 `id`），由 P5 输出的 `speaker_ref` 经说话人绑定解析而来 | 9.6.6 |
| `authorized` | BOOLEAN | 否 | `false` | 是否授权放行（矩阵的 Authorize 勾选）；取消勾选只改它、内容保留 | 9.6.4 |
| `in_playbook` | BOOLEAN | 否 | `false` | Play candidate：只标记为 playbook 候选，不影响授权、投影与召回，候选由后续另一任务处理（7 #Q8）；证词只打在署名行，匿名行恒为 `false` | 9.11.6 |
| `file_id` | VARCHAR(36) | 是 | — | 当前在线投影的合成 id，不指向真实文件（不是 Java `files.id`，也没有 S3 对象，7 #Q41）：每次投影生成一个，同时写进 RAG 条目、切片与登记行（`ai_file_registry.file_id`，ORM 主键）；RAG 条目经登记行的 `ai_rag_entry_id` 取，不另存（设计 9.6.6 的 `rag_entry_id` / `file_registry_id` 不建）。改内容时新条目写成功才换；下线完成后置空（重新勾选时按「`file_id` 为空且已授权 → 上线」推）。三类知识库去向的摘要行与正文行共用一个：正文行上线时生成，摘要写进在线条目时摘要行记同一个值（7 #Q42） | 1.2、1.6 |
| `projected_at` | TIMESTAMPTZ | 是 | — | 当前在线条目的入库时间：主行上线回写 `file_id` 时同写，下线同清；三类知识库去向的摘要行不写。Goldie Base 两个新 Tab 按它倒序分页（7 #Q72、#Q73），冗余在本表才能单表排序分页。改内容、投影重试、取消授权后再授权都生成新条目，时间随之重记 | 9.11.4 |
| `projection_status` | VARCHAR(16) | 否 | `'NONE'` | 投影状态：`NONE`（未投影或已下线）/ `PENDING`（投影中，含重试）/ `ONLINE`（已上线）/ `FAILED`（重试用尽仍失败）。摘要行在摘要写入在线条目时为 `ONLINE`，正文不在线或摘要未授权时为 `NONE`，只替换摘要进行中为 `PENDING`、重试用尽为 `FAILED`（审计 `PROJECTION_FAILED` 动作记 `SUMMARY_UPDATE`）（7 #Q42）。改正文时新条目上线后撤旧条目，撤旧按同样的退避重试，用尽时行保持 `ONLINE`、记 `PROJECTION_FAILED`（动作 `UPDATE`，`after_value.replacedFileId` 为旧条目），交清扫下线（P1「卡死兜底」⑥）。提取、证词补抽、Start Extraction（API-22）、Confirm & Apply（API-23）、改内容（API-24）落库时，都在同一事务里把要上线 / 下线的行置 `PENDING`，提交后、推送前进程被杀由清扫 ⑤ 接手（[定时清扫开发设计](../../卡死任务清扫/开发设计/dev-design-doc.md)第 4.7 节） | 1.6 |
| `projection_attempts` | INT | 否 | `0` | 已重试次数 | 1.6 |
| `deleted` | BOOLEAN | 否 | `false` | 软删 | 9.6.6 |
| `created_by` / `created_at` / `updated_by` / `updated_at` | — | — | — | 审计 | |

- 主键 `pk_ai_ff_routing_row (id)`
- 冗余会议时间与标题（7 #Q23）：Python 仓储只做单表；投递后原文不再改（9.3.1），冗余值不会过期；写行时从 P1 带入，用于日期筛选、会议名称匹配与卡片显示，排序按同样冗余的 `projected_at`（7 #Q72、#Q73）。会议类型、`fireflies_id` 只用于展示，分页后按本页会议 id 批量查 P1
- Portfolio 列：有公司取公司所属 Portfolio，无公司取会议 Portfolio 标记
- 不建唯一约束：同一场会、同一（去向, 公司, 产出类型）未软删的只有一行（证词每位发言人每版一行，7 #Q77），由写入逻辑保证——行只在提取成功时整场写入，写之前旧行已整场下线
- 索引
  - `idx_ai_ff_routing_row_meeting (meeting_id)` —— 矩阵加载、重新提取时整场下线、找已软删的上一版（故不加 `WHERE deleted = FALSE`）
  - `idx_ai_ff_routing_row_tab (organization_id, destination, projected_at DESC) WHERE deleted = FALSE AND authorized = TRUE AND file_id IS NOT NULL AND destination IN ('CROSS_COMPANY', 'TESTIMONY_SIGNED', 'TESTIMONY_ANON')`（7 #Q57、#Q73）—— Goldie Base 两个新 Tab 按租户、去向筛行并按条目入库时间倒序分页，管理端另按会议日期区间过滤（不用 `projection_status = 'ONLINE'`：改内容期间为 `PENDING`，旧条目仍在线）
  - `idx_ai_ff_routing_row_file (file_id)` —— 知识库 Source 列按登记行的 `file_id` 反查会议（不过滤软删）
  - `idx_ai_ff_routing_row_projection (projection_status) WHERE projection_status IN ('PENDING', 'FAILED')` —— 投影重试
- **摘要行与知识库行合投一条条目**（7 #Q42；矩阵仍是两行、各一个 Authorize）
  - 每个（去向, 公司）只投 1 条 RAG 条目：TEXT 来源，`content_text` 为正文行投影时生成的 markdown（7 #Q41），`summary` 列为摘要行内容（摘要行已授权时写，否则为空），不经大模型重写；登记行 `business_type = FIREFLIES`。正文进 Knowledge Base Tab，`summary` 非空时进 Memory Tab，两者都进 Goldie 召回
  - 摘要跟着正文走：正文行未授权或已软删时条目不上线，摘要行的授权不生效（前端把同一条目的正文与摘要当成一个勾选框，一起勾选、一起取消，7 #Q55）
  - 摘要向量：`summary` 非空时整段建一条 `chunk_kind=summary` 的向量（不拆分），用本行内容、不调系统摘要器；为空不建
  - 只改摘要（摘要行 Save，或勾选、取消摘要授权）且正文在线时：只替换条目的 `summary` 列与那条摘要向量，不重新向量化正文、不换 `file_id`。改正文仍是「写新条目、成功后软删旧条目」，新条目带上当前生效的摘要
  - 按 `file_id` 反查本表（Knowledge Base Tab 的 Source 列、Portfolio 显示）时，同一 `file_id` 有摘要、正文两行，取正文行（`output_type = KB`）
  - 已知：与现有知识库文件同一模型，不能只给 Memory 页摘要、不给知识库正文
- Expert Testimony Tab 以署名行为准（设计 9.11.5、9.11.6）：只列 `TESTIMONY_SIGNED` 已授权、已投影的行，一位发言人一行（7 #Q77）；Play candidate 也打在署名行。只放行了匿名版的证词不进本 Tab
- 证词两版是两条独立的行（设计 9.6.6 的 `testimony_group_id` 不建）：生成时正文相同、来源行由程序按版本附加，之后各自编辑、各自授权，不同步；矩阵按发言人排序，同一人的两版相邻（7 #Q77）
- 标签、可迁移理由不落库（设计 9.6.6 的 `tags` / `portable_reason` 不建）：P6 照旧输出，程序只用于 `EXTRACT` 审计；跨公司 markdown 只放正文。类别不另存：合并时由程序在每条段首加 `**<类别>**` 标签，随正文编辑；条目标题不带类别（7 #Q77）
- 证词发言人只存 `speaker_participant_id`（设计 9.6.6 的 `speaker_ref` / `speaker_name` / `speaker_organization` / `speaker_role` / `speaker_expertise_tags` 不建）：Expert Testimony Tab 的姓名与专长标签、投影时的来源行（署名版 `Source: <Organization> <Role> <Name>`、匿名版 `Expertise: …`，两版后面接 P7 `meeting_started_at` 折成的会议开始时间，7 #Q74）都按它关联 P2 的 `display_name` / `organization` / `role` / `expertise_tags`（会议日期生效版本）。已知：参会人改动后、重新提取前，Tab 显示新值而已投影的来源行仍是旧值
- 重新提取的勾选初值同首次自动提取，不读已软删行（7 #Q81）；同一次写入（整场提取、一次证词补抽）的行共用一个 `created_at`
- 不存软删时间（设计 9.6.6 的 `deleted_at` 不建）：找上一版用 `created_at`；何时下线看 `EXTRACT` 审计
- 状态流转：`projection_status` `NONE → PENDING → ONLINE`（上线）；`ONLINE → PENDING → ONLINE`（改内容）；`ONLINE → PENDING → NONE`（下线，完成后 `file_id` 置空）；`PENDING → FAILED`（重试用尽，记 `PROJECTION_FAILED`，最后一次错误只记在审计里；重试中途的错误看应用日志）
- 投影动作不落库（设计 9.6.6 的 `projection_action` 不建），处理 `PENDING` / `FAILED` 行时按行的当前状态与会议是否 `Passed` 推（只有 `Passed` 会议的内容在线，7 #Q75、#Q88；「该在线」= 未软删、已授权且会议是 `Passed`）；`PROJECTION_FAILED` 审计里的动作也按此算：
  - `file_id` 非空，不该在线（`deleted = TRUE`、`authorized = FALSE` 或会议不是 `Passed`）→ 下线
  - `file_id` 为空，该在线 → 上线（回写前锁 P1 复核会议仍是 `Passed`，否则本次结果作废）
  - `file_id` 非空，该在线 → 改内容（先写新条目、成功后换 id 再软删旧条目，期间 `file_id` 仍指旧条目；回写前同样复核）
  - 都不是 → 直接置 `NONE`
  - 按最新状态推：重试排队期间管理员改了勾选，不会照旧动作推错方向
  - 摘要行同样按上述推法，只是「上线 / 改内容」是把本行内容写进正文行在线的条目（只换 `summary` 与摘要向量），「下线」是清空它；正文行不在线时直接置 `NONE`，等正文上线时随之写入（7 #Q42）

#### P8 `ai_ff_audit_log`

Fireflies 只在 Python 侧记审计（A4，《会议内容提取规则》III）。Java 侧的换 key、移除 key、改邮箱域名、已处理会议的原文变化写 Java 应用日志（带租户、操作人、改前改后，不记 key），不建表。

| 字段 | 类型 | 可空 | 默认值 | 说明 | 需求条目 |
|---|---|---|---|---|---|
| `id` | BIGSERIAL | 否 | — | 主键（只追加的日志表，同 `ai_rag_operation_log` 先例） | |
| `organization_id` | VARCHAR(36) | 否 | — | 租户 | 9.10.1 |
| `event_type` | VARCHAR(32) | 否 | — | 事件类型：`IDENTIFY`（识别决策）/ `EXTRACT`（提取结果，含作废与补抽）/ `TYPE_CHANGE`（改类型）/ `COMPANY_CHANGE`（改公司）/ `CONTENT_EDIT`（矩阵改内容）/ `AUTHORIZE_CHANGE`（改授权）/ `PROJECTION_FAILED`（投影重试用尽仍失败） | 9.10.2 |
| `meeting_id` | VARCHAR(36) | 是 | — | 关联会议 | 9.10.1 |
| `target_type` | VARCHAR(16) | 是 | — | 受影响对象的类型：`COMPANY`（`COMPANY_CHANGE` 增删的公司）/ `ROUTING_ROW`（`CONTENT_EDIT`、`AUTHORIZE_CHANGE`、`PROJECTION_FAILED` 动到的中间表行）/ `PARTICIPANT`（`EXTRACT` 中证词补抽的那个人）；整场会议级的事件（`IDENTIFY`、`TYPE_CHANGE`、其余 `EXTRACT`）为空 | 9.10.1 |
| `target_id` | VARCHAR(36) | 是 | — | 受影响对象的 id，与 `target_type` 同空同非空。中间表行的去向与公司按 id 查（软删的行仍在）；`CONTENT_EDIT` 改的是摘要还是正文看该行的 `output_type`（7 #Q9） | 9.10.1 |
| `before_value` | JSONB | 是 | — | 变更前 | 9.10.1 |
| `after_value` | JSONB | 是 | — | 变更后 | 9.10.1 |
| `operator` | VARCHAR(36) | 否 | — | 操作人 user id；自动决策记 `"1"`（系统用户），页面显示为 `System` | 9.10.1 |
| `triggered_by` | VARCHAR(36) | 是 | — | `operator` 为系统、但由人的操作引起时记触发人（Sync now、Start Extraction、名册同步或登记保存后的证词补抽（7 #Q83、#Q87）、建公司引起的自动路由）；每日定时触发的与 `PROJECTION_FAILED` 留空 | 9.10.1 |
| `created_at` | TIMESTAMPTZ | 否 | `now()` | 事件时间 | 9.10.1 |

- 主键 `pk_ai_ff_audit_log (id)`；只追加，无 `updated_*`、无软删
- 事件只记 7 种：需求「所有路由决策与覆写操作都会写入审计日志」对应的 6 种（AI 的识别与提取决策，人工改类型、公司、内容、授权），加 `PROJECTION_FAILED`。设计 9.10.2 的其余事件不记，信息在业务表里：
  - `EXPERT_CONFIRM` / `EXPERT_DECLINE` → P5 的 `status` / `decided_by` / `decided_at` / `claims`，J6 拒绝名单，Cheat Sheet 来源 `From FF Summary Records`
  - `REGISTRY_IMPORT` → `ff_cheat_sheet` 的 `source` / `source_meeting_id` / `created_by`
  - `SPEAKER_ASSIGN` → P3 `bind_source = MANUAL_CHEAT_SHEET` + `updated_by` / `updated_at`（只针对未配上的说话人）
  - `PORTFOLIO_MARK`、`PLAYBOOK_TOGGLE` → 只留当前值与 `updated_by`，不留历史
- 重新提取是谁发起的，查这场会最近一次 Start Extraction 的 `EXTRACT` 记录（`triggered_by`、`created_at`），状态表不存发起人与时间
- 索引 `idx_ai_ff_audit_log_org_created (organization_id, created_at DESC)`、`idx_ai_ff_audit_log_meeting (meeting_id)` —— 按租户、按会议追溯（MVP 无查看页，9.10.3）

#### X1 `ai_file_registry`（改造）

| 变更 | 内容 | 存量数据 |
|---|---|---|
| `business_type` 新取值 `FIREFLIES`（三类知识库去向的条目：正文 + 摘要）/ `FIREFLIES_TESTIMONY`（证词两版）/ `FIREFLIES_CROSS_COMPANY`（跨公司）（7 #Q42） | 列无 CHECK，只更新列注释 | 无 |

- 不加列：登记表只管文件登记
- 两个页面都只认 `FIREFLIES`：Knowledge Base Tab 的查询纳入 `FIREFLIES`；Memory Tab 取 `KNOWLEDGE_BASE` 与 `FIREFLIES` 中摘要非空的条目（管理端 `scope=fireflies` 只取 `FIREFLIES`）；证词与跨公司不进两个页面（设计第八章 #11，7 #Q42）
- 与中间表的关联：登记行的 `file_id` = P7 的 `file_id`，本表不加反向列；Fireflies 登记行必须写 `ai_rag_entry_id`（一个 `file_id` 一个条目），中间表靠它找到 RAG 条目
- Fireflies 登记行的 `file_id` 是投影时生成的合成 id：没有 Java `files` 行，也没有 S3 对象（7 #Q41）；登记行由投影写入（现有 `ingest_text` 不建登记行），文件名为条目标题加 `.md`，下载时按它现生成（API-35）

### 1.4 跨端读写、种子数据与配置

**跨端读的表**（表结构不依赖读法；两端共用同一套数据库账号，不另授权，7 #Q36）：

| 方向 | 表 | 用途 |
|---|---|---|
| Python 读 Java 的 Fireflies 表（6 张） | `ff_meeting_meta_info`、`ff_meeting_sentence`、`ff_cheat_sheet`、`ff_expertise_tag`、`ff_connection_configuration`（只读 `organization_id`、`email_domains` 两列，不含 key 密文）、`ff_expert_rejection` | 识别与提取输入；名册回溯；P7 标签字典；识别 ①；拒绝名单（识别前过滤、同步时判已驳回） |
| Python 读 LG 业务表（7 张） | `user`、`r_organization_user`、`company`、`r_organization_company`、`company_group`、`r_company_group`、`organization` | 识别 ②③、自动路由、`firm_profile`、Portfolio 显示；`organization.pid` 取本租户的全部下级节点（本租户的人和公司含下级节点，自动路由反查各级父节点，7 #Q52） |
| Java 读 Python 的表（3 张） | `ai_ff_meeting_state.identification_result`、`ai_ff_expert_candidate`、`ai_ff_meeting_participant.email` | Raw Data 的 Invalid；标签删除校验；专家确认保存写拒绝名单时取本场邮箱（API-08） |

**跨端写**：无。会议页的名册编辑与专家确认由前端直调 Java（API-07 / 08，7 #Q44），Python 只在 Assign new external party 时经 API-06 新建（API-25，第八章 #31）；标签字典由前端直接调 Java（7 #Q19）；审计只有 Python 一张表（A4）。

**种子数据**

| 数据 | 方式 |
|---|---|
| 专长标签 7 项 | 新建组织时写入（`OrganizationServiceImpl.save`），存量组织由 Java V1 迁移补齐（J5，7 #Q4） |
| GS 租户 3 个邮箱域名 | 上线时管理员在 Cheat Sheet 页添加（7 #Q5） |
| Fireflies Management 菜单 | 管理后台 Menu & Function Management 加一条顶层菜单（path `/fireflies`，`pid = '0'`），在 Roles Management 只挂给 PGM / SA 的角色；配置后用户清浏览器 `localStorage.roles` 与同名 cookie 后重新登录（ERL 先例，7 #Q7） |
| RAG 新空间业务类型 `EXPERT_TESTIMONY` / `CROSS_COMPANY` | Python 代码种子 `rag/domain/enums.py`，无建表 DDL，V034 更新 `ai_rag_business_association.business_type` 列注释；机构层复用已有种子 `ADMIN_ORGANIZATION` |

**投影空间**（`ai_rag_business_association` 组合键 `(end_type, business_type, 作用域 id)`，设计 1.1）：

| P7 `destination` | 组合键 | 备注 |
|---|---|---|
| `KB_APP` | `(APP, APP_COMPANY, company_id)` | 已有 |
| `KB_ADMIN` | `(ADMIN, ADMIN_COMPANY, organization_id)` | 已有，行级按 `company_id` 过滤 |
| `FUND_LEVEL` | `(ADMIN, ADMIN_ORGANIZATION, organization_id)` | 复用已有种子 |
| `TESTIMONY_ANON` / `TESTIMONY_SIGNED` | `(APP / ADMIN, EXPERT_TESTIMONY, organization_id)` | 新业务类型 |
| `CROSS_COMPANY` | `(APP, CROSS_COMPANY, organization_id)` | 新业务类型；两端都召回，管理端在召回分支里另解此空间（设计第八章改造 #8） |

三类知识库去向的摘要行与正文行合投该空间的一条条目，登记 `FIREFLIES`；证词两版登记 `FIREFLIES_TESTIMONY`，跨公司登记 `FIREFLIES_CROSS_COMPANY`（P7、X1，7 #Q42）。

**新配置项**

| 端 | 配置 | 默认 |
|---|---|---|
| Java | Nacos `cio.fireflies.encryption`：API key 加密密钥（AES-256-GCM），Base64 编码的 32 字节，可用 `openssl rand -base64 32` 生成；漏配不影响启动，Link 与拉取时报错；配上后不要再换（换了已存的 key 解不开，只能重新 Link）。Nacos 登录不上的环境（test / uat）改配 Java 容器环境变量 `CIO_FIREFLIES_ENCRYPTION`（Spring 宽松绑定到同一个 key），只配一处 | 无，必配 |
| Java | Nacos `cio.fireflies.sync.first-lookback-days`：首次连接（含换账号）的回溯天数 | 14 |
| Java | Nacos `cio.fireflies.sync.lookback-hours`：增量拉取从上次成功往前回看的小时数 | 72 |
| Java | 连续非鉴权失败转 `Disconnected` 的次数：写死在 `FfSyncServiceImpl.DISCONNECT_THRESHOLD`，改要随 Java 发版（7 #Q58） | 3 |
| Java | Nacos `cio.fireflies.sync.pull-read-timeout-ms`：拉会议列表（一页 50 场，含逐句）的读超时 | 60000 |
| Java | Nacos `cio.fireflies.sync.sync-stale-minutes`：同步卡死时限（`sync_started_at` 超过即可被重新抢占，API-01 的 `syncing` 也按它判） | 60 |
| Java | 每日拉取 cron：写死在 `FixedScheduleTypeEnum.FirefliesDailyPull`（`cron(40 3 * * ? *)`），改要随 Java 发版（7 #Q33） | 每日 03:40 UTC |
| Java | Link 校验 key 的读超时：写死 | 15 秒 |
| Python | `SQS_INFLIGHT_LIMIT_FIREFLIES`：每条 Fireflies 队列的在途消息上限（两条队列各自生效） | 2 |
| Python | 处理中延长消息不可见时间的间隔（秒）：与财务提取共用 `consumer/heartbeat.py` 的 `HEARTBEAT_INTERVAL_SECONDS`，写死 | 120 |
| Python | 卡死时限：首轮停在处理中、非首轮提取 / 证词补抽停在 `RUNNING`、中间表行投影停在 `PENDING` 超过即视为中断，交定时清扫；按类写死在清扫代码里，数值见[定时清扫开发设计](../../卡死任务清扫/开发设计/dev-design-doc.md)第 3 节 | — |
| Python | 提示词重试次数：写死为 `common/config/fireflies.py` 的 `PROMPT_MAX_RETRIES`（每个提示词调用的最大重试次数，用尽即最终失败） | 3 |
| Python | `FIREFLIES_NGRAM_SIZE`：n-gram 近逐字的窗口（连续英文单词数，设计 1.5） | 8 |
| Python | `FIREFLIES_NGRAM_MATCH_RATIO`：一行的 n-gram 命中原文的比例达到即判近逐字、删整行 | 0.5 |
| Python | 投影重试次数：写死为 `projection_service.py` 的 `_MAX_ATTEMPTS`（写 / 删 RAG 条目、撤旧条目失败的最大尝试次数，用尽即投影失败） | 3 |

Java 的 4 项 `cio.fireflies.sync.*` 漏配时用上表默认值；它们与 `cio.fireflies.encryption` 同记在 `sql/migrations/env-vars/env-update.txt` 的 sprint122 段 `nacos` 下。Python 的 3 项记同一段与 `.env_example`；两条队列共用现有的 `SQS_NAME_PREFIX`、`CIO_AWS_REGION` 等 SQS 全局变量。

### 1.5 迁移文件与执行顺序

| 端 | 文件 | 内容 | 执行时机 |
|---|---|---|---|
| Java | `deploy/upgrade_doc/sprint122/V1__ff_init.sql` | J1~J6 建表、索引、注释；存量组织补齐 7 项预置专长标签 | **先于 Java 与 Python 发版**（ddl-auto 会自动建表但不建索引；Python 直读 J4 / J6） |
| Java | `deploy/upgrade_doc/sprint122/V4__ff_cheat_sheet_seed.sql` | Golden Section 租户的名册初始数据（173 人） | V1 之后，发版前后均可，可重跑 |
| Python | `sql/migrations/business/V034__sprint122_fireflies_init.sql` | P1~P5、P7、P8 建表、索引、触发器、注释；X1 只改 `business_type` 注释，`ai_rag_business_association.business_type` 注释补两个新空间业务类型；`ai_rag_entry.file_id` 加索引（下线、撤旧按它找条目） | **先于 Python 与 Java 发版** |
| Python | `sql/migrations/business/V035__sprint122_fireflies_routing_row_tab_index_anon.sql` | P7 加 `projected_at` 列并回填在线的存量行（取登记行的创建时间，7 #Q73）；重建 `idx_ai_ff_routing_row_tab`，纳入 `TESTIMONY_ANON`（7 #Q57）、排序列为 `projected_at`；`match_step` / `bind_source` 的 `P8` 改为 `AI_INFERRED`，`bind_source` 的存量 `MANUAL_ASSIGN` 并入 `MANUAL_CHEAT_SHEET`（两列注释直接改在 V034） | **先于 Python 发版**（新代码要读 `projected_at`），可重跑；执行过旧版本文件的环境重跑一遍 |
| Python | `sql/migrations/business/V036__sprint123_fireflies_routing_row_drop_category.sql` | P7 删 `category`、`source_timestamp` 两列（7 #Q77） | **Python 发版之后**（旧代码还会写这两列），可重跑 |
| Python | `sql/migrations/business/V037__sprint123_fireflies_meeting_state_unknown_by_admin.sql` | P1 加 `unknown_by_admin` 列（7 #Q89；存量不补标） | **Python 发版之前**（新代码读写这一列；旧代码不受影响），可重跑 |

两端迁移文件之间互不依赖，但两端发版都依赖对方的迁移：Java 的 Raw Data 列表（API-15 读 P1 `identification_result`）、标签删除校验（API-12 / 14 读 P5）与专家确认保存（API-08 读 P2）直读 Python 表，V034 没执行时直接报错；Python 直读 J1~J6。不另做数据库授权（7 #Q36）。DDL 见 [code-examples.md](./code-examples.md)。

## 2. 页面清单

页面编号用 `PG-`，避免与 Python 表 P1~P8 混淆。路由放在 web 的 `config/routes.ts`；两个 Tab 容器的当前 Tab 记在 `?tab=`（不用 `?active=`：它会改写公司端顶栏高亮，`BasicLayout.tsx:130,469-499`，PG-05 在 `/askGoldie` 下会丢掉 Ask Goldie 的高亮）。设计稿的路由（`/`、`/meetings/$id` 等）只作对照。角色：**PGM / SA** = 管理端，且 superAdmin 或角色菜单含 `seeAllPortfolio`；**PM** = 管理端其余用户；**公司端** = Company Admin / Company User。前端不自己判角色，用后端返回的标志位（API-19 及各接口的按行标志，设计 9.1）。

| 编号 | 页面 | 路由 | 入口 | 可访问角色 | 类型 | 新增 / 改造 | 需求条目 |
|---|---|---|---|---|---|---|---|
| PG-01 | Fireflies Management（Tab 容器） | `/fireflies?tab=summaryRecords\|configuration\|cheatSheet\|rawData&org=<组织 id>`（`org` 只在切换过租户时出现） | 两端都在头像下拉的 Fireflies Management（管理端按设计稿 `app-header.tsx:80-94`；公司端不受订阅状态限制，7 #Q14、#Q15）；PG-02 / PG-03 / PG-04 面包屑回到对应 Tab | PGM / SA（四个 Tab）；公司端（只显示 Raw Data Tab）；PM 进入显示无权限 | 容器 | 新增 | 9.1、9.3.6、第八章 #28、#32 |
| PG-01a | └ Summary Records Tab（默认） | `?tab=summaryRecords` | Tab 切换 | PGM / SA | 列表 | 新增 | 9.4 |
| PG-01b | └ Configuration Tab | `?tab=configuration` | Tab 切换 | PGM / SA | 表单 | 新增 | 9.2 |
| PG-01b1 | 　└ Remove API key 确认框 | — | Configuration 的 Remove | PGM / SA | 弹窗 | 新增 | 9.2.5 |
| PG-01c | └ Cheat Sheet Tab（名册列表 + 底部 Email Domain 块；LG 用户的条目在姓名旁标「LG user」，7 #Q51） | `?tab=cheatSheet` | Tab 切换 | PGM / SA | 列表 + 行内编辑 | 新增 | 9.7、9.7.7 |
| PG-01c1 | 　└ Add / Edit external party 弹窗（新增时另有 Confirm submission 二次确认；新增时姓名失焦查重，重名自动加后缀，7 #Q46） | — | Add external party / 行内 Edit | PGM / SA | 弹窗（表单） | 新增 | 9.7.4、9.7.5 |
| PG-01c2 | 　└ 专长标签下拉（选、`Add "<输入值>"`、删未用过的） | — | PG-01c1、PG-02a、PG-02b、PG-02c 的 Expertise tags 字段 | PGM / SA | 组件 | 新增 | 9.8 |
| PG-01d | └ Raw Data Tab | `?tab=rawData` | Tab 切换；公司端进入 PG-01 即此 Tab | PGM / SA；公司端（只列本人受邀的会议） | 列表 | 新增 | 9.3.3、9.3.4、9.3.6 |
| PG-02 | 会议 Review 详情（含 Content Routing Matrix） | `/fireflies/meetings/:meetingId` | PG-01a 的会议名 / Review；PG-05c、PG-05d 的会议名（仅 PGM / SA 可点） | PGM / SA（按会议所属租户） | 详情 + 表单 | 新增 | 9.5、9.6、9.9 |
| PG-02a | └ Assign new external party 弹窗（含 Confirm submission；姓名失焦查重，7 #Q46） | — | 点未识别、AI 推断未入册、按域名判出未入册的参会人；未对上说话人的「登记进名册」 | PGM / SA | 弹窗（表单） | 新增 | 9.5.5、9.5.7 |
| PG-02b | └ Edit external party 弹窗（前端直调 Java 保存一条完整记录，关窗后同步本场，7 #Q44） | — | 点名册中已有的外部人 | PGM / SA | 弹窗（表单） | 新增 | 9.5.5、9.5.7 |
| PG-02c | └ Possible expert 确认框（建议标签预填进标签栏，留下即同意、删掉即驳回；Save 一律写名册；前端直调 Java 保存，关窗后同步本场，7 #Q44、#Q45、#Q51） | — | 点带 `Possible expert` 的参会人 | PGM / SA | 弹窗（推测依据 + 表单） | 新增 | 9.5.6 |
| PG-02e | └ 行内 Save 的清洗回显 | — | 行内 Save 返回清洗结果时 | PGM / SA | 弹窗（设计稿未画） | 新增 | 9.6.3 |
| PG-02f | └ Link existing person 弹窗（两步：从名册选人 → 该人的信息弹框，保存后把本场参会人 / 说话人挂到此人，7 #Q53） | — | 点未识别参会人或未对上说话人下拉里的 `Link existing person` | PGM / SA | 弹窗（设计稿未画） | 新增 | 9.5.5 |
| PG-03 | 原文页 | `/fireflies/transcripts/:meetingId` | PG-01d 的 Raw transcript；PG-05a 中 Source = Fireflies 且可点的行 | PGM / SA；公司端（本人受邀的会议） | 详情（只读，整篇渲染、后台续加载） | 新增 | 9.3.5、9.3.6 |
| PG-04 | 名册 Role History | `/fireflies/cheat-sheet/:id/history`（`:id` 为此人任一版本行的 id） | PG-01c 的 History | PGM / SA | 列表（只读） | 新增 | 9.7.6 |
| PG-05 | Goldie Base（Tab 容器） | `/askGoldie/goldieBase?tab=knowledgeBase\|memorySettings\|crossCompany\|expertTestimony`（7 #Q16） | Ask Goldie 侧栏 / 手机端底栏的 Goldie Base 入口；旧地址 `/knowledgeBase`、`/memorySettings` 重定向到对应 Tab | 两端，按 Tab 区分 | 容器 | 新增（由两页合并） | 9.11.1、第八章 #17 |
| PG-05a | └ Knowledge Base Tab | `?tab=knowledgeBase`（默认） | Tab 切换 | 两端（原业务不变） | 列表 | 改造（原 `KnowledgeBasePage`） | 9.11.2、第八章 #11、#12、#18 |
| PG-05a1 | 　└ 基金标签选择：已取消（Portfolio 列纯文字） | — | — | — | — | 取消 | 9.11.2、第八章 #16 |
| PG-05b | └ Memory Settings Tab | `?tab=memorySettings` | Tab 切换 | 管理端；公司端 Company Admin | 列表 | 改造（原 `MemorySettingsPage`） | 9.11.3、第八章 #13、#19 |
| PG-05c | └ Cross company content Tab | `?tab=crossCompany` | Tab 切换 | 管理端 PM / PGM / SA；公司端所有用户（只有正文，7 #Q57） | 卡片列表 | 新增 | 9.11.4、9.11.6 |
| PG-05d | └ Expert Testimony Tab | `?tab=expertTestimony` | Tab 切换 | 管理端 PM / PGM / SA；公司端所有用户（匿名版，只有正文与专长标签，7 #Q57） | 卡片列表 | 新增 | 9.11.5、9.11.6 |

**入口与守卫**

- 管理端：头像下拉加一项（`BasicLayout.tsx` 的 `menuRight_SuperAdmin`，key 取 `fireflies`，`handleGSTMenuClick` 默认分支即跳 `/fireflies`，同 ERL；7 #Q14），`path` 与后台菜单 `/fireflies` 一致（1.4「种子数据」）
- 公司端：同样放头像下拉（7 #Q15），放在订阅条件之外（`BasicLayout.tsx:891` 的条件只管 Profile 与菜单项）——看本人受邀会议的原文是权限规则、不是付费功能。所有公司端用户都显示，没有受邀会议的看到空列表；key 同样取 `fireflies`，跳 `/fireflies`（不带 `?tab=`）；手机端是同一个下拉组件。进 PG-01 只渲染 Raw Data Tab，不显示租户下拉
- `SecurityLayout`：`/fireflies` 与 `/fireflies/transcripts/*` 两端都要进，**不加管理端守卫**；`/fireflies/meetings/*`、`/fireflies/cheat-sheet/*` 加管理端守卫（仿 ERL `SecurityLayout.tsx:73-98`，取不到端类型按公司端拦截）。PM 直接打开 `/fireflies` 时按 API-19 的标志位显示无权限提示，不请求管理端接口；PM 的拦截与数据权限一律靠后端
- 切换租户：PG-01 页头组织树下拉，组织树根下有子组织才显示（同 ERL、Portfolio Companies），默认会话租户；SA 借此切到子租户查看（7 #Q17）。ERL 的 `OrganizationSelect` 下沉到 `src/components/`，显示判定所在的 hook（`useErlOrganizationTree.ts:54`）、DTO 类型与 `subdata` → `children` 的归一函数一起搬。选中的租户记在 URL 的 `org` 上，PG-02 / PG-03 / PG-04 的面包屑把它带回；这三页不显示下拉，按会议（或名册行）所属租户执行，返回时 `org` 取该会议（或名册行）的租户（API-21、API-17、API-09 都返回 `organizationId`）
- Goldie Base：侧栏与手机端底栏的 Knowledge Base、Memory 两个入口合并为一个 Goldie Base 入口（设计稿 `ask-goldie.tsx:80-89`）；管理端一律取组织树第一个叶子租户（`orgScope.ts` 的 `firstLeafOrgId`），不提供切换（设计 9.11.1，7 #Q32）

**不在本期**：识别链的 HubSpot 一级（设计 1.9 ⑤，第十章 #25）；Ask Goldie 对话里展示 Fireflies 来源链接。Goldie 召回改造（第八章 #7~#10）不改页面（7 #Q21）。

## 3. 接口清单

**通用约定**

| 项 | Java（`/api/web/fireflies/*`） | Python（`/api/ai/fireflies/*`） |
|---|---|---|
| 位置 | `web/fireflies/` 按规范分 DDD 四层，路径 kebab-case 复数（7 #Q18）；每租户只有一个连接，按单例资源用单数 `/connection`；网关 `StripPrefix=1`，Controller `@RequestMapping("/fireflies")` | 新模块 `source/fireflies/`（`interfaces/routes/` 按页面拆文件），包根懒导出 router，`main.py` include |
| 响应 | `Result<T>` = `{success, code, message, data}`；业务错误 HTTP 200 + `success:false`；参数校验失败 HTTP 422，响应体为 `ErrorResponse{message, errors}`；错误码见 3.6 | 同结构；业务错误 HTTP 200 + `success:false` + 数字码（前端遇 ≥400 会弹全局横幅，码表见 3.6）；例外：改造的 file-registry 接口（API-33~36）沿用该模块现有的真实 HTTP 状态码（`_raise_business`） |
| 分页 | `page`（从 0 起）/ `size` / `sort`，返回 `PageResponse{totalElements, content}` | `page`（从 1 起）/ `pageSize`，返回 `{items, total}`；日期区间 `dateFrom` / `dateTo`，按会议业务日期、含两端（设计 9.3.3） |
| PGM / SA 判定 | `CompanyGroupService` 的一个方法：管理端 &&（任一角色 superAdmin \|\| 菜单码 `seeAllPortfolio`），Fireflies 接口首行断言，同时供 API-19 用 | 经 API-19 的新字段判定（`lgpi_api/current_user_api.py` 跟着加字段）；`auth_token` 缺失时在调 Java 之前就拒绝 |
| 租户 | 除按 id 定位的接口外，各接口可选 `organizationId`（一律走 query 参数）：为空取会话租户；传了就按传入的组织执行，**不校验调用者是否属于该组织**（7 #Q17）；PGM / SA 角色照常校验。按 id 定位的接口（API-07、09、14、17、18）不收组织 id，按该行（名册行、标签行、会议）自身的租户执行，同样不校验；API-06、API-41（带 `sourceMeetingId` 时）与 API-08 由来源会议推出租户。公司端一律会话租户 | Summary Records 列表同左；API-32 带 `meetingId`、由会议推出租户；会议级接口（`/meetings/{meetingId}/*`、`/routing-rows/{rowId}/content`）不收组织 id，按会议所属租户执行，同样不校验；Goldie Base（含知识库、Memory 的机构层条目）同样信任前端传入的组织 id：管理端一律传组织树首个叶子，没传时回退会话租户（知识库、Memory 没传时不纳入机构层条目），不做会话租户等值校验（7 #Q32） |
| 长任务 | Sync now 立即返回、异步拉取 | Start Extraction、证词补抽（保存后、Retry）立即返回、后台执行，前端轮询 API-21（线上 CloudFront 约 30 秒无响应即回 504） |
| 防过期提交 | — | 详情页的写接口都带 `updatedAt`（P1 乐观锁），0 行即提示刷新；凡改本场内容的写接口都要「碰」一下 P1 行。例外：名册同步 API-28 不带 `updatedAt`，按库里现状算、可重复调用，照样碰行（7 #Q44） |

前端调 Python 走同源 `/api/ai/...`（开发代理 `config/proxy.ts:21`）。线上 nginx 只有 `/api/web`、`/api/etl`（`nginx.prod.conf:163,176`），Java 网关只有 `/api/web/**`、`/web/**`（`cioaas-gateway.yml:27-39`），`/api/ai` 的分流应在 CloudFront / ALB 层（与运维确认）；`proxy.ts:19` 注释与 fileRegistry README 里「经 Java 网关转发」的说法已过时。

### 3.1 Java 接口

| 编号 | 方法 路径 | 功能 | 关键入参 | 关键出参 | 读写表 | 权限 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|---|---|---|---|
| API-01 | GET `/connection` | 连接状态 | `organizationId?` | `status`、`accountEmail`、`lastSuccessSyncAt`、`syncing`（`sync_started_at` 非空且未超过同步卡死时限，1.4）、`keyMask`（后 4 位，服务端拼好） | J1 读 | PGM / SA | PG-01b | 新增 |
| API-02 | POST `/connection/link` | 提交 key：调 Fireflies `user` 校验、加密落库；换账号按首次连接（9.2.6） | `apiKey`、`organizationId?` | 同 API-01；失败返回原因码（鉴权失败 / 网络不可达） | J1 写 | PGM / SA | PG-01b | 新增，见 3.6 |
| API-03 | POST `/connection/sync` | Sync now：条件更新抢占 `sync_started_at`，异步拉取（补投 → 拉列表 → 写原文 → 发 SQS），立即返回；正在同步、或没有 key（`UNCONNECTED`）时拒绝 | `organizationId?` | `syncing` | J1 写；J2 / J3 写；发 SQS | PGM / SA | PG-01b | 新增，见 3.6 |
| API-04 | POST `/connection/remove` | 清空密文、回 `UNCONNECTED` | `organizationId?` | 同 API-01 | J1 写 | PGM / SA | PG-01b1 | 新增 |
| API-05 | GET `/cheat-sheets` | 名册列表：每人取当前状态那一版（9.7.1），带逾期待复核标记；每行现算 `lgUser`（7 #Q51、#Q52） | `keyword`、`role`、`page`、`size`、`organizationId?`、`meetingId?`（PG-02f 用：以会议所属租户为准，每人改取会议当天生效的那一版，7 #Q53） | `content[{id, name, emails, organization, role, expertiseTags, areaOfExpertise, validFrom, validTo, source, needsReview, lgUser, effectiveOnMeeting?}]`、`totalElements` | J4 读；LG 用户表读（`lgUser`） | PGM / SA | PG-01c、PG-01c1（编辑预填同一行）、PG-02f | 新增，见 3.6 |
| API-06 | POST `/cheat-sheets` | 新建人员（第一版）；重名自动加后缀、返回最终姓名（7 #Q46）；邮箱查重（7 #Q49）；带 `sourceMeetingId` 时有效期必须包含会议日期（7 #Q44）；规则见 3.6「名册接口」 | `name`、`emails`、`organization`、`role`、`expertiseTags`、`areaOfExpertise`、`validFrom`、`validTo`、`sourceMeetingId?`、`organizationId?` | 新行（含最终姓名与 `id`） | J4 写（有 `sourceMeetingId` 记 `FF_SUMMARY_RECORDS` 与 `source_meeting_id`、租户由该会议推出，否则 `MANUAL`）；J2 读（推租户、取会议日期） | PGM / SA | PG-01c1；Python 经 API-25 调用 | 新增，见 3.6 |
| API-07 | PUT `/cheat-sheets/{id}` | 编辑：一律追加一条完整新版本（9.7.1），不改旧行（7 #Q44）。不带 `sourceMeetingId`（Cheat Sheet 页）：什么都没改时只在 `{id}` 那一版记复核（`reviewed_*`，9.7.5）；带 `sourceMeetingId`（会议页，`{id}` 为 API-21 返回的 `versionId`）：新行记来源，有效期必须包含会议日期，与 `{id}` 那一版相比没有改动时不写、也不记复核。邮箱查重（本条目自己的各版本不算，7 #Q49） | 同 API-06（无 `name`、`organizationId`） | 新行 id；或 `reviewed: true` | J4 写（带 `sourceMeetingId` 的记 `FF_SUMMARY_RECORDS` 与 `source_meeting_id`）；J2 读（取会议日期） | PGM / SA | PG-01c1、PG-02b（前端直调） | 新增，见 3.6 |
| API-08 | POST `/cheat-sheets/expert-confirmations` | 专家确认保存（7 #Q44、#Q45、#Q51），一个事务，一律写名册：已在册的按 API-07 规则以 `baseVersionId` 为底追加完整新版本（与 T2 相比没有改动不写），未登记的按 API-06 规则新建（LG 平台用户同样新建，#Q47）；Expertise tags 为空也照建 / 照追加；写拒绝名单 J6：驳回 = `suggestedTags` − 保存后的 Expertise tags，邮箱取 P2 该参会人的本场邮箱；有效期必须包含会议日期；租户由 `sourceMeetingId` 推出 | `sourceMeetingId`、`participantId`、`suggestedTags`（本次打开时的建议标签）、`entry`（登记字段同 API-06，必填，7 #Q51）、`baseVersionId?`（已在册时为预填的 T2 id，未登记为空） | 最终姓名、写入的版本 id | J4 写（新行记 `FF_SUMMARY_RECORDS` 与 `source_meeting_id`）；J6 写；J2 读（推租户、取会议日期）；P2 读（本场邮箱） | PGM / SA | PG-02c（前端直调） | 新增，见 3.6 |
| API-09 | GET `/cheat-sheets/{id}/history` | 此人全部版本，按 `updated_at` 倒序、相同再按 `id` 倒序，不看 `valid_from` | — | `name`、`organizationId`、`rows[{…快照字段, updatedBy, updatedAt}]`（`updatedBy` 为操作人显示名，会议页登记的也是实际操作人；系统用户为 `System`） | J4 读 | PGM / SA | PG-04 | 新增，见 3.6 |
| API-10 | GET `/email-domains` | 本租户邮箱域名 | `organizationId?` | `domains[]` | J1 读 | PGM / SA | PG-01c | 新增，见 3.6 |
| API-11 | PUT `/email-domains` | 整份提交（增、改、删都走它）：逐个去 `@`、转小写，校验格式、公共邮箱域名与重复；没有连接行时先建一行（`UNCONNECTED`）；应用日志记改前、改后两份列表（7 #Q22） | `domains[]`、`organizationId?` | `domains[]` | J1 写 | PGM / SA | PG-01c | 新增，见 3.6 |
| API-12 | GET `/expertise-tags` | 标签字典，按 `sort_no`；每项带能否删除 | `organizationId?` | `[{id, name, preset, deletable}]` | J5 读；J4（任一版本用过）、P5（未处理标记引用）读 | PGM / SA | PG-01c2 | 新增 |
| API-13 | POST `/expertise-tags` | 新增：不区分大小写重名拒绝，`sort_no` 追加到末尾 | `name`、`organizationId?` | 新标签 | J5 写 | PGM / SA | PG-01c2 | 新增，见 3.6 |
| API-14 | DELETE `/expertise-tags/{id}` | 删除：预置的、名册任一版本用过的、被未处理专家标记引用的拒绝 | — | — | J5 删；J4、P5 读 | PGM / SA | PG-01c2 | 新增，见 3.6 |
| API-15 | GET `/meetings` | Raw Data 列表：服务端过滤后分页，默认会议时间倒序 | `keyword`（会议 id、标题、参会人）、`dateFrom`、`dateTo`（按会议日期，7 #Q25f）、`participants[]`（按显示名匹配出席记录姓名，或按邮箱匹配受邀邮箱）、`validity`（全部 / 只看 Invalid / 隐藏 Invalid）、`sort`（`firefliesId` / `title` / `date` / `time`（按一天中的时刻）/ `duration` / `participants`（按显示名串）/ `ingestedAt`，加 `,asc` / `,desc`；空值排最后，同值按 `firefliesId`）、`page`、`size`、`organizationId?`（7 #Q20） | `content[{id, firefliesId, title, startedAt, durationMinutes, participantNames, ingestedAt, invalid}]`（`participantNames` 取出席记录姓名，没有出席记录的回退受邀邮箱，9.3.3）、`totalElements` | J2 读；P1 `identification_result` 读 | PGM / SA：本租户；公司端：会议所属租户是会话机构或其上级（7 #Q52）、本人邮箱在 `participants` 中 | PG-01d | 新增，见 3.6 |
| API-16 | GET `/meetings/participant-options` | 参会人筛选项：调用者看得到的会议里参会人显示名去重（口径同 `participantNames`） | `organizationId?` | `[{value, label}]` | J2 读 | 同 API-15 | PG-01d | 新增，见 3.6 |
| API-17 | GET `/meetings/{id}` | 原文页页头 | — | `organizationId`、`title`、`startedAt`、`durationMinutes`、`participantNames`、`capturedAt` | J2 读 | PGM / SA：按会议所属租户执行，只校验角色（7 #Q17）；公司端：会议所属租户是会话机构或其上级（7 #Q52）且本人邮箱在 `participants` 中 | PG-03 | 新增，见 3.6 |
| API-18 | GET `/meetings/{id}/sentences` | 逐句分批（首批显示后前端在后台连续取完全篇，每批 500 句，7 #Q29） | `fromOrder`、`limit` | `[{order, speakerName, startTime, text}]`、`hasMore` | J3 读 | 同 API-17 | PG-03 | 新增，见 3.6 |
| API-19 | GET `/api/web/users/current` | 现有接口，`AuthenticatedUserDto` 加 PGM / SA 布尔字段 `pgmOrSuperAdmin`（与 `superAdmin` 分开） | — | 新增字段 | 现有 | 登录 | PG-01、PG-05（标志位）；Python（判定 PGM / SA） | 改造（第八章 #22），见 3.6 |
| API-41 | GET `/cheat-sheets/name-check` | 姓名查重（7 #Q46）：按 API-06 的同一规则（忽略大小写）看租户内是否已有此姓名，给出保存时会用的姓名；只作提示，以保存时为准 | `name`、`organizationId?` 或 `sourceMeetingId?`（会议页由会议推出租户） | `exists`、`availableName`（不重名即原名，重名为加后缀后的姓名） | J4 读；J2 读（推租户） | PGM / SA | PG-01c1（新增）、PG-02a、PG-02c（姓名失焦） | 新增，见 3.6 |

### 3.2 Python 接口

| 编号 | 方法 路径 | 功能 | 关键入参 | 关键出参 | 读写表 | 权限 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|---|---|---|---|
| API-20 | GET `/summary-records` | Summary Records 列表（`processing_stage = DONE` 且非 Invalid），默认会议时间倒序；顺带返回 Tab 红点用的 Pending 数 | `keyword`（标题、会议 id、公司名）、`meetingType`、`status`（`PASSED` / `PENDING`，不按 Pending 原因筛，7 #Q25d）、`dateFrom`、`dateTo`、`page`、`pageSize`、`organizationId?` | `items[{meetingId, firefliesId, title, startedAt, durationMinutes, meetingType, companies[], status, pendingReasons}]`、`total`、`pendingCount`（Pending 会议总数，不受筛选影响） | P1、P4 读；LG `company` 读 | PGM / SA | PG-01、PG-01a | 新增 |
| API-21 | GET `/meetings/{meetingId}` | 会议详情，含矩阵；也是提取 / 补抽进行中的轮询接口 | — | 会议元信息、`organizationId`、`meetingType`、`status`、`pendingReasons`、待识别子原因（现算）、`extractionStatus`、`participantsChanged`（最新识别结果与 P1 `current_extraction_input` 比，该列为空时恒为 false；口径按 9.9.1：只补邮箱、改 Area of expertise、专长标签不算（7 #Q87），组织变化只对 Founder 与本场有证词行的人算）、`registryChanged`；`companies[{companyId, name, adopted, basisText}]`（含未采纳候选）、`portfolioIds`；`participants[{id, displayName, email, organization, role, badges, aiEvidence, clickAction, registryState, testimonyBackfillStatus, registryForm, expertCandidates[{tag, claims[], resolvedAs}]}]`（`registryForm` 为弹框预填（7 #Q44）：已在册的为会议日期当天生效的那条记录 T2（覆盖会议日期、写入最晚的那条，9.7.2）及其 `versionId`，未入册者为已知值（含 P8 推断，From 默认会议日期、To 空），细节见 3.6；`aiEvidence` 前端不展示；`resolvedAs` 现算：已在 T2 里为 `ACCEPTED`、在拒绝名单 J6 为 `DECLINED`（不预填），否则为空（预填为建议标签）；`clickAction` 带 Possible expert 时优先开专家确认框，标签处理完后按是否入册开登记或编辑弹框）；`unmappedSpeakers[{speakerId, name, sentenceCount, aiSuggestedMatch, registryForm}]`；`routingRows[{rowId, outputType, destination, companyId, companyName, visibleTo, content, sourceLine, speakerParticipantId, authorized, projectionStatus}]`（按去向、发言人排序，7 #Q77；证词行的 `sourceLine` 带会议开始时间，7 #Q74；摘要行的 `projectionStatus` 表示摘要是否已写进在线的正文条目，正文不在线时为 `NONE`，7 #Q42）；`updatedAt` | P1~P5、P7 读；J2、J3（按说话人数句）、J4、J6 读；LG 表读 | PGM / SA（会议所属租户） | PG-02、PG-02a~c、PG-02f | 新增，见 3.6 |
| API-22 | POST `/meetings/{meetingId}/extraction` | Start Extraction：提取前先按会议当天生效的名册刷新参会人（7 #Q84 ②），页头写进识别结果、整场下线、后台提取，立即返回（6.11、9.5.1）。提取或证词补抽进行中、必填项不齐（9.5.1）时拒绝；点击时清空本场 P2 的 `testimony_backfill_status`（旧的补抽失败随旧产物作废） | `meetingType`、`companyIds`、`updatedAt` | `extractionStatus = RUNNING`、`updatedAt` | P1（含清 `unknown_by_admin`，7 #Q89）、P4、P2（清补抽状态）写；P5、P7 软删并下线；P8 `TYPE_CHANGE` / `COMPANY_CHANGE` / `EXTRACT` | PGM / SA | PG-02 | 新增，见 3.6 |
| API-23 | POST `/meetings/{meetingId}/routing/apply` | Confirm & Apply Routing：授权勾选、Portfolio 标记、改 `Unknown`、GS → LP 的公司增删（9.6.5）。应用时按每行的当前状态整体推一遍投影：已授权、未删、没上线的上线（应用后会议仍是 Pending（待识别）时不上线，只有 Passed 会议投影，7 #Q75），取消授权的下线。摘要行的授权依赖同一（去向, 公司）的正文行：正文行未授权或已软删时摘要不生效、不投影（静默归一：按未授权落库、记 `AUTHORIZE_CHANGE`，不返回错误；提取时的授权初值同样归一，7 #Q42）。提取或证词补抽进行中时拒绝（含改 `Unknown`）；不改 `Unknown` 时，参会人已改动但还没点 Start Extraction、有未处理的专家标记、GS → 创始人多于一家公司也拒绝（7 #Q25e）。需确认、不硬拦的一条（7 #Q48）：按当前参会人重跑类型判定、结果与当前类型不同（`TYPE_MISMATCH`，带 `suggestedType`）；Founder 的组织 / 所属公司与关联公司对不上不提示。服务端重算，有提示且未带 `confirmWarnings=true` 时返回 40903、`data.warnings` 列出；应用时不重读最新 Cheat Sheet（会议用自己的快照）；不补证词（7 #Q87） | `authorizations[{rowId, authorized}]`、`portfolioIds`、`meetingType?`（仅 `UNKNOWN`）、`companyIds?`（仅 GS → LP）、`confirmWarnings?`、`updatedAt` | `status`、`updatedAt` | P7 写 + 投影；P1 状态与 `portfolio_ids`；改 `Unknown` 整场下线、P1 置 `unknown_by_admin`（7 #Q89）；P4；P8 | PGM / SA | PG-02 | 新增，见 3.6 |
| API-24 | PUT `/routing-rows/{rowId}/content` | 行内 Save（9.6.3 两步提交合在一个接口）：先跑 n-gram 与该去向适用的实体剥离——清洗后没有变化就落库（已授权且会议 Passed 时重投影，Pending 时不投影，7 #Q75；摘要行在正文在线时只替换条目的 `summary` 与摘要向量，7 #Q42）；有变化就不落库，返回清洗结果与命中明细，管理员确认后把清洗后的文本连同首次提交稿再提交一次，不再有变化即落库，`CONTENT_EDIT` 记改前、首次提交稿、定稿与命中（服务端按首次提交稿重算）。内容为空（只有空白）、摘要行超过 150 个英文单词、该行发言人的证词补抽进行中时拒绝 | `content`、`originalContent?`（第二次提交时带首次提交稿）、`updatedAt` | 落库时：该行、`updatedAt`；未落库时：`cleanedContent`、`hits[]`（删去的行及原因、替换的实体）、`wordCount` | P7 写；P1 写（碰行）；J3 读（比对基准）；P8 `CONTENT_EDIT` | PGM / SA | PG-02 | 新增，见 3.6 |
| API-25 | POST `/meetings/{meetingId}/external-parties` | Assign new external party，按序判：① 填的邮箱是本租户 LG 平台用户 → 不进名册，按平台用户更新本场 P2 / P3，得出的公司写成 P4 未采纳的候选（`adopted = false`、依据 `EMAIL`），是否采纳由页头与 Start Extraction 决定；② 填的邮箱已在名册某条记录会议当天生效的版本里 → 不新建，把本场参会人 / 说话人绑到那条记录、按它刷新 P2 / P3，名册与表单其余内容不写；命中的邮箱都属同一条记录、且它当天生效的版本里至少有一个所填邮箱即认，所填邮箱都不在它当天生效的版本里或分属两条记录则拦截（42200，7 #Q49）；③ 都不是才调 API-06 写名册（带 `sourceMeetingId`；重名后缀后的最终姓名记进 P2，7 #Q46），更新本场 P2 / P3（9.5.5、9.5.7）。有效期必须包含会议日期（三条路径都按表单校验，7 #Q44）；来源是参会人时本场邮箱锁定（不可删改，可加别的邮箱），来源是未对上的说话人时邮箱由管理员填写、不锁。之后重跑类型判定；本场没有参会人改动时，把本场专长标签与提取快照不同的专家排进证词补抽（同 API-28，7 #Q87） | `participantId` 或 `speakerId`、表单字段、`updatedAt` | `platformUser`、`suggestedType?`、`suggestedCompany?`（按平台用户认出的公司）、`registryMatchedName?`（7 #Q49）、`participantsChanged`、`updatedAt` | P2、P3、P1（碰行、提取快照）写，必要时 P4（候选），补抽写 P7、P8；LG 表读；J4 读（按邮箱认人），新建经 API-06 | PGM / SA | PG-02a、PG-02f（说话人关联：`speakerId` + 所选人的邮箱，走按邮箱认人、不新建，7 #Q53）。保存成功后给本场还没挂上的说话人按设计 1.9 的条件再判一次、满足即挂上（#Q53 ⑤） | 新增，见 3.6 |
| API-28 | POST `/meetings/{meetingId}/participants/{participantId}/registry-sync` | 参会人名册同步（7 #Q44、#Q51）：PG-02b / PG-02c 保存成功、关窗后调，不收表单、不调 Java，按库里现状算、可重复调用。按会议日期生效的名册记录刷新本场 P2（平台用户按 #Q47 以记录角色为准）；此人的建议标签在记录里 → `ACCEPTED`、在拒绝名单 J6 → `DECLINED`（P5，含自动消解）；按 9.9.1 参会人改动口径（专长标签不比）与提取快照比：有参会人改动 → `participantsChanged = true`，角色变了重跑类型判定、返回 `suggestedType`（不静默改判）。本场没有参会人改动时，名册刷新提交后再起一个短事务，把本场所有专长标签与提取快照不同、不在补抽或排队中的专家的标签同步进快照、置 `RUNNING`（本场已有人在补抽或排队时置 `QUEUED`，7 #Q86）、碰 P1，响应后后台补抽证词（P5）；某人补抽在跑时又改了标签，这次不另起、快照不动，那次补完发现标签又变了即排到队尾再补（7 #Q87）。没传 `cheatSheetName`（如上次同步失败后重开）时，按本场邮箱找会议当天生效的记录挂上。首轮未完、提取进行中拒绝（40901）；证词补抽进行中不拦（7 #Q51） | `cheatSheetName?`（新登记时传 API-08 返回的最终姓名）；不带 `updatedAt` | `participantsChanged`、`suggestedType?`、`updatedAt` | P2、P5、P1（碰行、提取快照）写，补抽写 P7、P8；J4、J6 读 | PGM / SA | PG-02b、PG-02c、PG-02f（参会人关联：`cheatSheetName` 传所选人的姓名，7 #Q53）。同步成功后给本场还没挂上的说话人按设计 1.9 的条件再判一次、满足即挂上（#Q53 ⑤） | 新增，见 3.6 |
| API-29 | POST `/meetings/{meetingId}/participants/{participantId}/testimony-backfill` | 证词补抽失败后 Retry：只在该参会人 `testimony_backfill_status = FAILED`、且本场没有进行中的提取时接受；本场已有人在补抽或排队时置 `QUEUED`，否则置 `RUNNING` 并起后台任务（7 #Q86） | `updatedAt` | `testimonyBackfillStatus` | P2、P7、P1（碰行）写；P8 `EXTRACT` | PGM / SA | PG-02 | 新增，见 3.6 |
| API-30 | GET `/goldie-base/contents` | Goldie Base 两个新 Tab 共用：已授权、已投影的跨公司内容，或证词（管理端署名版、公司端匿名版，9.11.4、9.11.5、7 #Q57）；关键词匹配内容与会议名称（证词另匹配说话人姓名，7 #Q25b），按会议日期区间过滤（用 P7 冗余的会议时间与标题，7 #Q23）；按 P7 `projected_at DESC, id DESC` 排序（7 #Q72、#Q73）、按行分页，前端归卡片见 5.8 | `type`（`CROSS_COMPANY` / `TESTIMONY`）、`keyword`、`dateFrom`、`dateTo`、`page`、`pageSize`、`organizationId?` | `items[{rowId, content, meeting{meetingId, firefliesId, title, startedAt, meetingType, canOpen}, inPlaybook, speakerName?, expertiseTags?}]`（后两项仅证词）、`total`、`canTogglePlaybook` | P7 读（筛选、排序、分页都在 P7 内）；分页后按会议 id 批量读 P1（会议类型、`fireflies_id`）；证词另读 P2（说话人；关键词匹配说话人时先在 P2 按姓名查出参会人 id） | 管理端 PM / PGM / SA；公司端所有用户：租户只认会话机构（没有则返回空页）、不调 Java，`meeting` 与 `speakerName` 为 null、`inPlaybook` 恒 false、关键词只匹配内容、忽略 `dateFrom` / `dateTo`（7 #Q57） | PG-05c、PG-05d | 新增 |
| API-31 | PATCH `/routing-rows/{rowId}` | 改中间表行上的 Play candidate（`inPlaybook`，限跨公司行与证词署名行），立即生效、不写审计 | `inPlaybook` | 改后的值 | P7 写 | PGM / SA；不收组织 id，按该行所属租户，不做会话租户等值校验（7 #Q32） | PG-05c、PG-05d | 新增 |
| API-32 | GET `/org-options` | 本租户全部公司（含挂在下级节点的、含不在营的，带状态，7 #Q52）与本节点全部 Portfolio：会议页 Company / Portfolio 下拉候选（设计 9.5.3 / 9.5.4）。不复用 Java `companyGroup/companies`（它返回「公司 × Portfolio」配对，没挂 Portfolio 的公司不返回、也不去重） | `meetingId`（由会议推出租户） | `companies[{companyId, name, status}]`、`portfolios[{companyGroupId, name}]`；不在营的公司带状态返回，GS → 创始人时前端置灰不可选（2.1）；公司另带 `inPortfolio`（挂了本租户或其下级机构的 Active Portfolio），前端 Company 下拉只列为 true 的与已选的；识别、提取前校验、列表搜索、脱敏仍按全部公司 | LG `company`、`r_organization_company`、`company_group` 读 | PGM / SA | PG-02 | 新增，见 3.6 |

API-26、API-27 已删除（7 #Q44、#Q56），编号不复用。

### 3.3 改造与复用的现有接口

| 编号 | 方法 路径 | 改什么 | 使用页面 | 新增 / 改造 |
|---|---|---|---|---|
| API-33 | GET `/api/ai/file-registry/files` | 主表是登记表 `ai_file_registry`（分页、排序、筛选都在登记表上），P7 / P1 只在分页后按本页的 Fireflies 行补查。筛选与搜索保持现有：搜索只按文件名，不加 Source 筛选（7 #Q24a）；Source 列照加。只纳入 `FIREFLIES` 行（7 #Q42），公司端普通用户只列本人受邀的会议（按受邀名单里的邮箱，7 #Q59），公司管理员列本公司全部；机构层作用域按组织 + 机构层空间圈定；`source` 取值为 `GOLDIE` / `FIREFLIES`（第八章 #18）；Fireflies 行经 P7 按 `file_id`（取正文行，7 #Q42）带出会议 id、能否跳原文与 `portfolioDisplay`（有公司取公司所属 Portfolio，无公司取会议 Portfolio 标记）；Fireflies 行的 `uploadedBy` / `uploadedByName` 返回空（From Chat 与 Uploaded By 显示 `—`，设计 9.11.2，7 #Q25a）（第八章 #11~#13、#16、#18） | PG-05a | 改造，见 3.6 |
| API-34 | GET `/api/ai/file-registry/files/filter-options` | 作用域放开到 Fireflies 行后，上传者选项排除 `FIREFLIES` 行（7 #Q25a） | PG-05a | 改造 |
| API-35 | GET `/api/ai/file-registry/files/{entryId}/download` | 加 `FIREFLIES` 分支：公司端限本公司 APP 端，普通用户还须本人受邀、否则 404（7 #Q59），管理端限可访问公司或本组织机构层（#12）。没有 S3 对象，由后端按条目的 markdown 现生成（返回结构见 3.6，7 #Q41） | PG-05a | 改造，见 3.6 |
| API-36 | PUT、DELETE `/api/ai/file-registry/records/{registryId}` | `update_record` / `delete_record` 按 `business_type` 显式拒绝 `FIREFLIES` / `FIREFLIES_TESTIMONY` / `FIREFLIES_CROSS_COMPANY` 三类行（DELETE 会连带删 RAG 条目与向量）；`_PROTECTED_BIZ_TYPES` 另加这三个类型，防聊天上传改写会议行（7 #Q42）；Fireflies 行前端不显示删除（#12） | PG-05a | 改造 |
| API-37 | GET `/api/ai/memories` | 「登记表圈定条目 → `ai_rag_entry` 取摘要分页」两步，不读 P7（7 #Q42）。圈定 `KNOWLEDGE_BASE` 与 `FIREFLIES`，只列摘要非空的条目，返回项加来源字段，增加机构层（#11、#13、#19）。管理端 `scope` 加取值 `fireflies`：只取 `FIREFLIES`、不分层；`company` / `portfolio` 只取 `KNOWLEDGE_BASE`，不含会议摘要与机构层；公司端不加筛选；不加 Document Summary 选项。会议摘要的标签为 Fireflies Memory + Meeting Summary，Fireflies Memory 占层徽标的位置；文件摘要不变（7 #Q24b） | PG-05b | 改造，见 3.6 |
| API-38 | POST `/api/ai/sse/stream`（Goldie 召回） | 接口契约不变；召回改造见第八章 #7~#10 | Ask Goldie 对话（不在本页面清单） | 改造 |
| API-39 | GET `/api/web/organization/findByTree` | 不改：PG-01 的租户下拉、PG-05 的默认租户 | PG-01、PG-05 | 复用 |
| API-40 | POST `/api/web/storage/uploads/presign`、`/uploads/{id}/verify` | 不使用（投影为纯文本，7 #Q41）；接口本身不改 | 无页面 | 不再使用 |

接口合并（7 #Q22）：会议详情一次取回弹框预填、专家建议标签与矩阵；Summary Records 列表顺带返回红点数；行内 Save 的清洗预览与落库合成一个接口；已处理过的专家标签在同步（API-28）时落库；两个新 Tab 共用一个列表接口；Play candidate 单设一个改标记接口（API-31）；Email Domain 整份提交；Company / Portfolio 候选由 API-32 提供。

### 3.4 页面 × 接口对账

| 页面 | 加载 | 操作 |
|---|---|---|
| PG-01 | API-19（显示哪些 Tab、PM 无权限提示）、API-39（租户下拉）；PGM / SA 的红点取 API-20 的 `pendingCount`（从其他 Tab 进入时调一次 API-20）。公司端只调 API-19 | 切换租户后 URL 带 `org`，各 Tab 带 `organizationId` 重新加载 |
| PG-01a | API-20 | 搜索、类型 / 状态 / 时间筛选、分页：API-20 |
| PG-01b | API-01 | Link：API-02；Sync now：API-03（之后轮询 API-01 看 `syncing`） |
| PG-01b1 | — | Remove：API-04 |
| PG-01c | API-05（行带 `lgUser`，7 #Q51）、API-10 | 搜索、Role 筛选、分页：API-05；域名增 / 改 / 删：API-11（整份提交） |
| PG-01c1 | 编辑时用 API-05 的行数据预填（含 `lgUser` 标记） | Confirm：新增 API-06，编辑 API-07；新增时姓名失焦查重：API-41 |
| PG-01c2 | API-12 | `Add "<值>"`：API-13；删除：API-14 |
| PG-01d | API-15、API-16 | 搜索、日期 / 参会人 / 有效性筛选、排序、分页：API-15 |
| PG-02 | API-21、API-32 | Start Extraction：API-22（之后轮询 API-21）；Confirm & Apply：API-23（返回 40903 时二次确认后带 `confirmWarnings=true` 再调一次；成功后刷新 API-21）；行内 Save：API-24（有命中时确认后再调一次）；证词补抽 Retry：API-29；Discard Changes 只在前端 |
| PG-02a | 用 API-21 的 `registryForm`；API-12 | Confirm：API-25；姓名失焦查重：API-41；标签维护：API-13 / 14 |
| PG-02b | 用 API-21 的 `registryForm`（含 `versionId`）；API-12 | Confirm：API-07（带 `sourceMeetingId`）→ 关窗后 API-28 → 刷新 API-21；标签维护：API-13 / 14 |
| PG-02c | 用 API-21 的 `expertCandidates`、`registryForm`（含 `versionId`）；API-12 | Save：API-08 → 关窗后 API-28 → 刷新 API-21；新登记姓名失焦查重：API-41；标签维护：API-13 / 14 |
| PG-02f | API-05（带 `meetingId`）；API-12 | Confirm：参会人 API-07 → API-28；说话人 API-07（表单有改动时）→ API-25；标签维护：API-13 / 14 |
| PG-03 | API-17、API-18（首批） | 后台自动续加载至全篇：API-18 |
| PG-04 | API-09 | — |
| PG-05 | API-19、API-39 | — |
| PG-05a | API-33、API-34 | 下载：API-35；删除：API-36；Source 链接跳 PG-03 |
| PG-05a1 | —（已取消） | — |
| PG-05b | API-37 | — |
| PG-05c | API-30（`type=CROSS_COMPANY`） | 搜索、时间筛选、分页：API-30；开关：API-31（`inPlaybook`）；会议名跳 PG-02（`canOpen`） |
| PG-05d | API-30（`type=TESTIMONY`） | 同 PG-05c |

API-38 由 Ask Goldie 对话使用，对话页不在本清单。设计稿与设计文档不一致的几处见 7 #Q24、#Q25。

### 3.5 无页面的调用与跨服务链路

| 调用 | 调用方 → 被调方 | 说明 |
|---|---|---|
| 每日拉取 | AWS EventBridge → `scheduler-queue` → Java `ScheduleProcessor` | `FixedScheduleTypeEnum` 加一项，分发到 Fireflies 拉取服务（与 API-03 同一链路）；入口先 `setCurrentUserId("1")`；定时与手动互斥靠 J1 `sync_started_at` 条件更新（第八章 #29） |
| 新会议 | Java → SQS `fireflies-meeting-queue` → Python `consumer/fireflies/` | 队列在 Java `InitSqsQueueEnum` 登记（启动时建队列与死信队列），Java 不监听；消息带租户、会议 id、触发方式与触发人；投递与补投见 J2（第八章 #30）；消息体见 3.6 |
| 公司 / 公司端用户增改 | Java 保存入口发领域事件 → `@TransactionalEventListener(AFTER_COMMIT)` → SQS `fireflies-company-change-queue`（同样在 `InitSqsQueueEnum` 登记）→ Python 自动路由 | 入口：`CompanyServiceImpl.create` / `update`（`addWithoutEmail`、`addCompanyAndSetStage` 都汇到这两处）、`CommonServiceImpl.createInvitedUserAndSendEmail`（覆盖 `POST /users/invite` 与 `POST /project/inviteuser`）、`UserServiceImpl.clientUser` / `update`。归档（`POST /invite/archiveCompany`）与停用（`PUT /invite/delete/{companyId}`）不发：只改归档标记、解除 Portfolio 关联，不会产生新的匹配。拉会议与公司变更分两条队列（第八章 #27）；名册变更复用公司变更这条队列，Python 按 `type` 分发（7 #Q84）。消息只带公司 id、变更类型与操作人，不带租户（3.6，7 #Q52） |
| Cheat Sheet 名册增改 | Java 保存入口发领域事件 → `@TransactionalEventListener(AFTER_COMMIT)` → SQS `fireflies-company-change-queue`（复用）→ Python 重跑相关 Pending 会议 | 入口：`FfCheatSheetServiceImpl` 的 create（新增人员每次都发）、update 与 confirmExpert（追加了新版本且与上一版比姓名、邮箱、机构、角色、有效期、专长标签任一有变化才发；只改 Area of expertise、只记复核不发）；保存回滚不发，发送失败只记日志、不影响保存。消息体见 3.6，Python 按 7 #Q84 ① 找会议重跑 |
| 名册新建 | Python → Java API-06 | 只有 Assign new external party（API-25）经它新建，透传用户 token（第八章 #31）；会议页的名册编辑与专家确认由前端直调 API-07 / 08（7 #Q44） |
| PGM / SA 判定 | Python → Java API-19 | 透传用户 token |
| 跨端读表 | Java 读 P1、P2（本场邮箱）、P5；Python 读 J1~J6 与 7 张 LG 业务表 | 见 1.4；Python 直读 LG 业务表与 Python 规范「LG 业务数据经 Java 网关取」不一致，随数据权限一起定（A5） |
| 卡死兜底 | 定时清扫（单独功能） | 见 P1「卡死兜底」 |

跨服务调用链：

- 拉取：Java 定时 / API-03 → Fireflies GraphQL → J2 / J3 → SQS → Python 识别与提取 → P1~P7 → 投影：RAG 条目（TEXT 来源、合成 `file_id`）+ X1 登记，不调 Java（7 #Q41）
- 登记参会人：前端 → Python API-25 →（非平台用户、邮箱不在名册，7 #Q49）Java API-06 → Python 更新 P2 / P3
- 编辑参会人（Edit external party）：前端 → Java API-07（写 J4）→ 关窗 → 前端 → Python API-28（刷新 P2 / P5，碰 P1）
- 专家确认：前端 → Java API-08（写 J4、J6）→ 关窗 → 前端 → Python API-28（写 P5 / P2，碰 P1）
- 保存即补抽（7 #Q83、#Q87）：前端 → Java API-07 / 08 写名册 → Python API-28（Assign new external party 为 API-25，同样处理；本场没有参会人改动时把标签变了的专家同步进提取快照、置补抽中或排队）→ 响应后后台补抽证词（提示词 P5）→ 写 P7（会议已 Passed 的转回 Pending（待审核）、本场在线内容整场下线，应用后已勾选的行整批重新投影，7 #Q88）；前端轮询 API-21
- 自动路由：前端 → Java 公司 / 用户保存 → 事务提交后 SQS → Python 重跑 ②③ → 自动提取
- Raw Data 的 Invalid：前端 → Java API-15 → 读 Python 表 P1

### 3.6 开发期补定的契约

补在通用约定与 3.1~3.5 之上的接口细节（对应行末注「见 3.6」）；与前文冲突时以本节为准。

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
| — | 全部 | 无权限沿用 `FfAccessSupport` 抛的 `BadRequestException`，不另设码；名册的有效期校验（To 早于 From、带来源会议时不含会议日期）同样抛 `BadRequestException`。名册重名不报错，自动加后缀（7 #Q46）；新建或编辑时邮箱已登记在别的条目（API-06 / 07 / 08，7 #Q49）同样抛 `BadRequestException`，`message` 写明邮箱登记在谁名下（如 `This email is already registered to Tom in the Cheat Sheet.`） |

Python：`{success:false, code, message, data}`，HTTP 200；五位数，同 financial_extract 的 `40400` 风格（API-33~36 例外，见通用约定）。

| 错误码 | 含义 |
|---|---|
| `40300` | 无权限：非 PGM / SA、公司端调用管理端接口 |
| `40400` | 不存在 |
| `40900` | 页面已过期：`updatedAt` 对不上，前端用页面顶部错误提示条提示刷新（第 4 节通用约定，7 #Q54） |
| `40901` | 提取或证词补抽（含排队中 `QUEUED`，7 #Q86）进行中，前端提示稍后重试；名册同步（API-28）只在首轮未完、提取进行中时返回，证词补抽进行中不拦（7 #Q44、#Q51）；Retry（API-29）遇补抽进行中改为排队、不返回 |
| `40903` | Confirm & Apply 有需确认的提示（API-23，7 #Q48）：`data.warnings` 列出，前端二次确认后带 `confirmWarnings=true` 重提 |
| `42200` | 前置条件不满足：必填项不齐、有未处理专家标记、GS → 创始人多于一家公司、行内 Save 内容为空、摘要超 150 词、登记的有效期不含会议日期（API-25）、登记填的邮箱已在名册但会议当天生效的记录里没有它或分属两条记录（API-25，7 #Q49）等；`message` 写明原因 |
| `50200` | 调用 Java 失败 |

**SQS 消息体**（Java → Python）：JSON camelCase，带 `type` / `version`；值为 null 的字段不出现；另带 Java 消息基类的 `messageType` / `queueName` / `sendTime` / `uuid`，Python 忽略（名册变更消息用 `sendTime`）。不带 `traceId`：Python 每收到一条消息新建一条链路（重投也各留一条），两端日志靠会议 id 与 SQS messageId 对上。

| 队列 | 消息体 | 说明 |
|---|---|---|
| `fireflies-meeting-queue` | `{type: "FIREFLIES_MEETING", version: 1, organizationId, meetingId, trigger: "DAILY" \| "SYNC_NOW", triggeredBy?}` | 定时拉取没有 `triggeredBy` |
| `fireflies-company-change-queue` | `{type: "FIREFLIES_COMPANY_CHANGE", version: 1, companyId, changeType: "COMPANY" \| "CLIENT_USER", operatorId}` | **不带租户**，Python 按 `r_organization_company` 查公司挂的节点、再补上各级父节点作为公司所属租户（7 #Q52）；`operatorId` 必有，取不到当前用户时 Java 填 `"1"`；Python 只处理会议日期在最近 90 天内的会议（7 #Q90） |
| `fireflies-company-change-queue` | `{type: "FIREFLIES_REGISTRY_CHANGE", version: 1, organizationId, operatorId, sourceMeetingId?, before?: {name, emails, validFrom, validTo?}, after: {name, emails, validFrom, validTo?}}` | 与公司变更共用队列，靠 `type` 区分；新增人员没有 `before`，从 Cheat Sheet 页改的没有 `sourceMeetingId`；日期 `yyyy-MM-dd`；`operatorId` 取不到当前用户时填 `"1"`。Python 只看会议日期在最近 90 天内的会议（7 #Q90），用基类的 `sendTime`（截到秒）加 1 秒作这次保存已提交的上界（本机时钟没到先等，最多 2 秒）：识别开始或 Start Extraction 开始不早于它的会议已按新名册处理过、不跑不等；与此人有关的会议轮到它锁行时正在处理（首轮或重跑未完、提取或补抽进行中，含 Passed 会议的 Start Extraction）或重跑出错的，以及还在识别、参会人未写入、看不出有没有关的，不删消息，等重投再看（锁行时已按这次改动处理过或已不是 Pending 的不跑也不等），第 3 次仍要等进死信并记 WARNING 列出这些会议（7 #Q84） |

**Java 接口**

| 项 | 补定 |
|---|---|
| API-19 | `AuthenticatedUserDto` 新字段 `pgmOrSuperAdmin: boolean`，与 Fireflies 接口首行的 PGM / SA 断言同一判定；前端与 Python 都读它 |
| API-05 `meetingId`（7 #Q53） | 给了 `meetingId`：按会议取租户（忽略 `organizationId`，会议不存在按现有 `getMeetingById` 报错），会议日期取 `started_at` 的 UTC 自然日；每人按该日期用 9.7.2 的版本裁决取生效的那一版——取到则该行各字段用这一版、`effectiveOnMeeting = true`，取不到用当前状态那一版、`false`。`keyword`、`role` 过滤在取版本之后做，`needsReview`、`lgUser`、分页与排序照旧。不带 `meetingId` 时不出 `effectiveOnMeeting`。行的 `id` 即 PG-02f 第二步保存时 API-07 的路径参数 |
| API-05 取数（7 #Q69） | 每人一版在库里挑好再读回：当前那一版用 `DISTINCT ON (name)` 按 `updated_at`、`id` 倒序取第一条（与 Service 里 History 的 `WRITE_ORDER` 同一顺序，改规则两处同改）；带 `meetingId` 时另取每人有效期覆盖会议日期、`updated_at` 最晚的那一版；`needsReview` 另取每人全部版本最晚的 `updated_at` / `reviewed_at`。先按窄列挑出 `id` 再取整行（整行参与排序会溢写磁盘）。`keyword`、`role` 筛选、排序与分页仍在内存里做 |
| `organizationId` | 各接口的可选 `organizationId` 一律走 query 参数（GET 与写接口都是），写接口的 body 不带它 |
| 名册接口 | 邮箱查重（7 #Q49）：新建与编辑（API-06 / 07 / 08）时任一邮箱（忽略大小写）已出现在租户内别的条目（编辑时不含本条目）的任一版本里即拒绝，不认人、不合并；姓名后缀（7 #Q46）：API-06 / 08 新建与 API-41 查重同一规则——姓名忽略大小写比较，重名时从 1 起取第一个未占用编号接在姓名后（Tom → Tom1 → Tom2），保存时再算一次、以保存时为准；API-05 按姓名升序；API-06 / 07 / 08 的 To 早于 From 拒绝；带 `sourceMeetingId` 时有效期必须包含会议日期（From ≤ 会议日期，To 为空或 ≥ 会议日期；会议日期为 J2 `started_at` 的 UTC 日期，7 #Q44） |
| 返回结构 | API-06 成功返回新行（结构同 API-05 的一行，`name` 为最终姓名，`lgUser` 不现算、为空）；API-07 `{ids[], reviewed}`（每次至多一个新行；会议页没有改动时都为空）；API-08 `{name, id}`（最终姓名、写入的版本 id；已在册没有改动时 `id` 为空、`name` 为名册姓名）；API-41 `{exists, availableName}`；API-09 `rows` 含 `source`、`updatedBy`、`updatedAt`；API-10 / 11 `{domains[]}`；API-13 返回新标签 |
| API-05 `lgUser` | `boolean`，每行现算、不存表：该行（当前状态那一版）任一邮箱忽略大小写命中本租户 LG 账号（本租户管理端用户、本租户公司的公司端用户，本租户含下级节点，同识别 ②）即 true；前端在列表与编辑弹框（PG-01c1）的姓名旁显示「LG user」标记（7 #Q51） |
| API-15 | `validity`：`ALL`（缺省）\| `INVALID_ONLY` \| `HIDE_INVALID`；`sort`、`validity` 非法值拒绝、不回落；`size` 1~100 |
| API-16 | `[{value, label}]` 的 `value`、`label` 都是显示名；不分页（每租户量小，与 Java `coding.md` §10 的分页要求不一致） |
| API-18 | 响应 `{sentences: [{order, speakerName, startTime, text}], hasMore}`；`startTime` 为秒（number，可带小数）；`limit` 1~500，前端每批 500，首批显示后在后台连续取完全篇（7 #Q29） |
| 时间格式 | Raw Data 接口（API-15、17）的时间字段为 `yyyy-MM-dd'T'HH:mm:ss'Z'`（UTC） |

**Python 接口**

| 项 | 补定 |
|---|---|
| API-21 `participants[].registryState` | `UNREGISTERED`（未入册的外部人）\| `REGISTERED`（名册中已有）\| `PLATFORM_USER`（LG 平台用户）；PG-02c 按它决定 Name 是否可改（只有 `UNREGISTERED` 可改并失焦查重，其余只读；平台用户首次登记时姓名取账号姓名、只读，打开时即调 API-41 查重并在姓名下提示；平台用户的 Role 也可改，7 #Q46、#Q47）。未挂名册条目、但本场邮箱已在名册某条记录会议当天生效版本里的参会人按 `REGISTERED`，`registryForm` 预填那条记录并给 `versionId`（7 #Q51 ⑤）；LG 平台用户仍为 `PLATFORM_USER`，同样预填并给 `versionId` |
| 说话人自动挂的条件（7 #Q53 ④） | `identification_service._same_person_target`：命中一个直接取；命中多个时，每人取「已挂的名册条目姓名（`cheat_sheet_name`），没有则按邮箱在会议当天生效的名册记录里查到的姓名」，都有且相同才取第一个，GS 人员与公司不算。按邮箱查是因为按域名判出的人（识别 ①③）此时还没挂名册条目；平台账号在名册有记录时识别 ② 已挂 |
| 保存后重判说话人（7 #Q53 ⑤） | `identification_service` 把「姓名对邮箱前缀 + 上一行的条件」抽成可复用的纯函数（入参：本场参会人的邮箱与 `cheat_sheet_name`、未挂上的说话人；出参：要挂的说话人与参会人）。API-25 的两条保存路径与 API-28 在同一事务里、身份写完后调用，命中的说话人按 `bind_source = NAME_PREFIX` 挂上并刷新 `matched_name`；已挂上的不动 |
| API-25 说话人关联（PG-02f，7 #Q53） | 不加参数：前端带 `speakerId` 与所选人的邮箱，走「按邮箱认人」路径（`registryMatchedName` 返回该人姓名），不新建、不改名册；表单改动由前端先经 API-07 保存 |
| API-21 `registryChanged` | `boolean`：名册在会议之外改过、按会议当天生效的那一版刷新会改本场识别结果时为真，打开详情页时现算（按姓名、按邮箱各批量查一次名册）：挂了名册的人那一版的姓名 / 机构 / 角色 / 专长标签与参会人行不同（平台用户只比角色与标签，按域名识别的只比标签），或没挂名册的人按本场邮箱新对上了名册；当天没有生效版本的人不算。Passed 会议为真时 Start Extraction 激活、不加提示；API-22 提取前先按名册刷新这些人（7 #Q84 ②） |
| API-21 `participants[].registryForm.versionId` | T2（会议日期当天生效的那条记录）的 id；已在册时有值，PG-02b 作 API-07 的 `{id}`、PG-02c 作 API-08 的 `baseVersionId`（7 #Q44） |
| API-21 `badges` / `clickAction` | `badges`：`POSSIBLE_EXPERT` \| `AI_INFERRED`（7 #Q60）；`clickAction`：`EXPERT_CONFIRM` \| `ASSIGN` \| `EDIT` \| `NONE` |
| API-21 `identifySubReasons` | 待识别子原因（设计 9.4.2），现算，会议不在待识别时为空数组；前端不展示、不读取；取值：`PARTICIPANT_UNIDENTIFIED`（有未识别的参会人）、`SPEAKER_UNMAPPED`（有未对上的说话人）、`TYPE_UNDETERMINED`（类型为 Unknown，含被改为 Unknown）、`COMPANY_MULTIPLE`（GS → 创始人关联了多家公司）、`COMPANY_UNDETERMINED`（GS → 创始人定不出公司，含公司方只来自 P8 而反推的公司与推断机构对不上、名册反推不出）、`FOUNDER_COMPANY_MISMATCH`（有 Founder 归属不到关联的公司；近似，不区分是否到场）、`IDENTIFICATION_FAILED`（P1 / P8 最终失败，只在之后还没提取过时出现）、`EXTRACTION_FAILED`（最近一次提取作废） |
| API-21 `participants[].email` | 本场邮箱（参会人行 `email`；前端据此锁定本场那一个，7 #Q44）。`registryForm` 的 T2 里没有本场邮箱时已补在末尾；会议当天没有生效版本（会后改了有效期）时按识别时记的 `cheat_sheet_id` 那一行预填并作 `versionId`，管理员须把有效期改到包含会议日期才能保存 |
| API-21 `routingRows[].companyId` | 该行的公司 id（无公司的去向为空）；前端按（`destination`, `companyId`）配对摘要行与正文行、划分矩阵分区，不按公司名（同名或空名公司会串） |
| API-25 `platformUser` | `boolean`：按 LG 平台用户识别、不进名册时为 true；前端据此提示 |
| API-25 `registryMatchedName` | 填的邮箱已在名册某条记录会议当天生效的版本里、按那条记录认人未新建时，为该记录的姓名，否则不返回；前端据此提示（7 #Q49）。匹配忽略大小写，任一填写的邮箱命中即算；拦截时 `message` 写明邮箱登记在谁名下、请先到 Cheat Sheet 调整 |
| API-23 二次确认 | 入参 `confirmWarnings?: boolean`；有提示且未带 `true` 时返回 40903，`data.warnings[{code, message, suggestedType?}]`：`code` 只有 `TYPE_MISMATCH`（带 `suggestedType`；重判结果为 `Unknown` 时不提示，同 9.9.3「可判定为 X」口径；7 #Q48）；改为 `Unknown` 应用时不做 |
| API-25、28、29 响应 | 不返回 `participant`，成功后前端重新拉 API-21；API-28 返回 `{participantsChanged, suggestedType?, updatedAt}`（7 #Q51）；API-29 返回 `{testimonyBackfillStatus, updatedAt}` |
| API-32 `companies[].portfolioIds` | 该公司所属的 `company_group` id；GS → 创始人在页头改公司时，前端据此实时算只读 Portfolio（设计 9.5.4）；`status` 为公司状态码字符串，为空按 Thriving 给 `"4"`（设计 2.1） |
| API-33 `KbDocument` | 新增 `source: 'GOLDIE' \| 'FIREFLIES'`。以下仅 FIREFLIES 行有值、其余为 null：`meetingId`；`canOpenTranscript: boolean`（可跳 PG-03）；`portfolioDisplay: string[]`（公司所属 Portfolio——只认 `r_company_group.status = 0`（Active），与 Java 知识库列一致——无公司的取会议 Portfolio 标记，7 #Q50）。Fireflies 行的 `uploadedBy` / `uploadedByName` / `threadId` / `threadTitle` 为 null |
| API-35 下载 | Fireflies 行（登记 `FIREFLIES`）后端按该条目在线的 markdown（`content_text`）现生成，返回 `data = {url: null, fileName, content}`：`fileName` 为登记行文件名（`.md`），`content` 为 markdown 全文；其他行仍返回 `{url}`。前端见 `content` 时用 Blob 下载（7 #Q41） |
| API-37 `MemoryItemDTO` | 新增 `source: 'DOCUMENT' \| 'FIREFLIES'`；管理端 `scope` 新取值 `fireflies`（只取 `FIREFLIES` 中摘要非空的条目，7 #Q42） |
| `updatedAt` | P1 乐观锁凭证，在 API-21 与各写接口的出入参里一律保留**完整精度**（ISO 8601 带微秒与时区，如 `2026-10-28T03:15:42.123456+00:00`），前端原样回传、不格式化；写接口收到不带时区的按 UTC |
| 其余时间 | UTC `yyyy-MM-dd HH:mm:ss`（不带时区，前端按 UTC 解析，如 API-30 `startedAt`）；有效期 `yyyy-MM-dd` |

**知识库条目的摘要与登记类型**（7 #Q42）

| 项 | 补定 |
|---|---|
| 登记 `business_type` | `FIREFLIES`（三类知识库去向的条目：正文 + 摘要）\| `FIREFLIES_TESTIMONY`（证词两版）\| `FIREFLIES_CROSS_COMPANY`（跨公司）。Knowledge Base Tab（API-33）只取 `FIREFLIES`；Memory Tab（API-37）取 `KNOWLEDGE_BASE` 与 `FIREFLIES` 中摘要非空的条目，`scope=fireflies` 只取 `FIREFLIES`；API-36 拒绝这三个类型 |
| 摘要并入正文条目、摘要跟着正文走、摘要向量、只改摘要 | 见 P7「摘要行与知识库行合投一条条目」；API-23 遇「摘要授权而正文未授权」按正文为准 |
| RAG 管理端「重试」 | `POST /api/ai/rag/entries/{id}/retry` 遇到 Fireflies 条目：跳过系统摘要器，保留原 `summary`，并按它重建摘要向量 |

**两端共用的规则**

| 项 | 补定 |
|---|---|
| 名册版本平局 | 同一日期有多个生效版本时，按 `updated_at` 降序、再按 `id` 降序取第一个（设计 9.7.2）；Java 版本裁决与 Python 识别 ④ 一致 |
| 公共邮箱域名清单 | Java `FfConfigurationServiceImpl`（API-11 校验）与 Python `identification_service.PUBLIC_EMAIL_DOMAINS`（识别 ③ 排除）各写死一份、同为 23 个，改清单要两端同步改、同时发版；设计 1.9 的「清单可配」未做 |
| 在营公司状态 | `{2, 3, 4, 5}`：Needs Intervention / Needs Guidance / Thriving / Achieving（需求原文的 Active 即 Achieving）；Exited / Shut down / Off journey 不在营（Python `IN_OPERATION_COMPANY_STATUSES`，7 #Q28）；状态为空按 Thriving，读状态一律经 `effective_company_status`（同平台 Java `Invite.getCompanyStatus()`） |
| 每日拉取 | `FixedScheduleTypeEnum.FirefliesDailyPull`，每日 03:40 UTC，写死不可配（1.4、7 #Q33） |

## 4. 页面功能按钮

通用约定：中文提示只表达语义，界面文案一律英文；设计稿已有的标题、按钮名与提示照设计稿，没有的按设计稿语气定稿。成功用顶部 toast（antd `message`），表单校验错误显示在字段下方，后端拒绝的原因原样提示。详情页写操作遇到 `updatedAt` 冲突不覆盖，用页面顶部错误提示条 `This page is out of date. Refresh the page.`，不弹框、不自动刷新，发起写操作的弹框随之关闭（7 #Q54）。弹框标题、确认框标题、登记表单字段标题与专家确认框小节标题用 Blue/900 `#0d2b56`；确认框（`Modal.confirm`）不带图标、垂直居中；登记弹框与专家确认框内容超出屏幕时在弹框内滚动，标题与底部按钮不动。所有带 `org` 的跳转与面包屑保留 `org` 参数（第 2 节「入口与守卫」）。

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
| 状态筛选 | 筛选栏 | — | All statuses / Passed / Pending（7 #Q25d） | API-20 | 否 | — |
| 时间范围 | 筛选栏 | — | From / To，可 Clear；按会议日期 | API-20 | 否 | — |
| 分页 | 表格下方 | — | 同第 5 节开头（7 #Q43）；默认会议时间倒序 | API-20 | 否 | — |
| 会议名 / Review | 表格行 | — | 跳 PG-02 | — | 否 | — |
| 视图记忆 | — | — | 搜索、类型 / 状态 / 时间筛选、页码与条数存 sessionStorage，从 PG-02 面包屑或浏览器后退回来时恢复，从菜单、新开、手输地址进来或在本页刷新时清空（读写包在 try/catch 里，取不到用默认值；切过租户回到第 1 页；恢复的页码超出末页时落到最后一页，7 #Q67） | — | — | — |

### 4.3 PG-01b Configuration 与 PG-01b1 Remove 确认框

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 加载 | — | — | 显示状态点（Unconnected 灰 / Connected 绿 / Failed 红 / Disconnected 灰）、connected as（`UNCONNECTED` 时不显示）、Last sync、key 掩码；`syncing = true` 时同 Sync now 开始轮询 | API-01 | — | — |
| Link | API Key 区 | 未绑定（`UNCONNECTED`），输入框非空 | 校验 key 并保存，成功后切换为掩码 + Remove | API-02 | 否 | 成功 toast；失败在输入框下显示原因（鉴权失败 / 网络不可达），不清空输入、页面状态不变 |
| Sync now | Connection 区 | 已绑定（不是 `UNCONNECTED`）且 `syncing = false` | 触发同步，按钮转「Syncing…」并置灰，每 5 秒轮询 API-01 直到 `syncing = false`，刷新 Last sync 与状态点；离开页面停止轮询 | API-03 → API-01 | 否 | 已在同步时被拒，提示「正在同步」；同步后为 Failed / Disconnected 时状态点随之变化 |
| Remove | API Key 区 | 已绑定 | 打开 PG-01b1。没有「更换 key」入口，先 Remove 再 Link | — | — | — |
| PG-01b1 Remove | 确认框 | — | 清空 key、回未绑定，暂停定时拉取 | API-04 | 本身即二次确认 | 成功关闭并刷新；失败提示 |
| PG-01b1 Cancel | 确认框 | — | 关闭 | — | — | — |

### 4.4 PG-01c Cheat Sheet、PG-01c1 名册弹框、PG-01c2 专长标签下拉

逾期不设提示条，只靠每行的 `Needs review` 标记提示。

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 搜索 | 筛选栏 | — | 匹配姓名、邮箱、组织、专长标签与 Area of expertise | API-05 | 否 | 无结果：「No registry entries match this search.」 |
| Role 筛选 | 筛选栏 | — | All roles / 6 种角色 | API-05 | 否 | — |
| 分页 | 表格下方 | — | 同第 5 节开头（7 #Q43） | API-05 | 否 | — |
| Add external party | 列表右上 | — | 打开 PG-01c1（新增，Name 可填） | — | — | — |
| Edit | 行内 | — | 打开 PG-01c1（编辑，带当前状态那一版，Name 只读） | — | — | — |
| History | 行内 | — | 跳 PG-04 | — | — | — |
| LG user 标记 | 列表 Name 旁；PG-01c1 编辑时 Name 旁 | `lgUser = true` | 只读显示「LG user」（7 #Q51） | API-05 | — | — |
| Email Domain：加载 | Email Domain 块 | — | 列出本租户的邮箱域名（`@domain`），不分页 | API-10 | — | — |
| Email Domain：Add（按钮或 Enter） | Email Domain 块底部 | 输入去 `@`、转小写后格式合法且不重复（前端先校验，重复提示「This domain is already added.」；公共邮箱域名由后端判） | 把新域名并进列表，整份提交 | API-11 | 否 | 成功刷新列表；后端拒绝时在输入框下显示原因（重复 / 公共邮箱域名 / 格式） |
| Email Domain：Edit → Save / Cancel | 行内 | Save 在输入合法时可点；Enter 保存、Esc 取消 | 替换该项后整份提交 | API-11 | 否 | 同上 |
| Email Domain：Delete | 行内 Delete 按钮 | — | 确认后去掉该项、整份提交 | API-11 | 是：`Modal.confirm`，标题「Delete email domain?」，正文「@{域名} will no longer be used to identify internal participants.」，按钮 Cancel / Delete（红色），样式同 PG-01b1 | 成功刷新 |
| PG-01c1 字段 | 弹框 | Name*（新增可填、编辑只读；新增时失焦调 API-41 查重，重名时在姓名下方提示「A Cheat Sheet entry with this name already exists. It will be saved as Tom1.」，不拦提交，7 #Q46）；Email(s)*（至少一个，格式校验，可 `+ Add another email` / ×）；Organization*；Role*（新增时为空）；Expertise tags（Role 为 LP / Strategic Partner / Exit Partner 时必填，提示 `Please select at least one expertise tag.`，改选成不必填的角色时清掉该提示；Founder 选填；只在前端校验，7 #Q24d；Role 为 GS staff / Other 时置灰并清空）；Area of expertise（≤2048 字）；Validity period From* / To（可空） | 改动后才显示必填提示；提示文案 `"From" is required. Leave "To" empty to show the period as open-ended — e.g. "Aug 2, 2025 – present".` | API-41（Name 失焦） | — | — |
| PG-01c1 Confirm（新增） | 弹框底部 | 必填齐 | 弹「Confirm submission」（姓名提交后不可修改），Yes, submit 后提交 | API-06 | 是 | 成功关闭、刷新列表；重名时以 API-06 自动加后缀后的姓名保存（7 #Q46）；邮箱已登记在别人名下时在弹框内显示原因、不关窗（7 #Q49） |
| PG-01c1 Confirm（编辑） | 弹框底部 | 必填齐 | 提交；什么都没改也可提交，即记一次复核（9.7.5） | API-07 | 否 | 成功关闭、刷新列表；邮箱已登记在别人名下时在弹框内显示原因、不关窗（7 #Q49） |
| PG-01c1 Cancel | 弹框底部 | — | 关闭，不保存 | — | — | — |
| PG-01c2 加载 | 打开下拉时 | — | 按 `sort_no` 列出字典 | API-12 | — | — |
| PG-01c2 新增标签 | 下拉底部「Add a new tag…」输入框 | 输入值不在字典里（不区分大小写）；已存在的直接选中 | 加入字典并选中 | API-13 | 否 | 重名提示已存在 |
| PG-01c2 删除 | 选项悬停时的删除按钮 | `deletable = true`（预置的、用过的、被未处理专家标记引用的不显示） | 从字典删除 | API-14 | 否 | 被拒时提示原因 |

### 4.5 PG-01d Raw Data

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 搜索 | 工具栏 | — | 匹配会议 id、标题、参会人 | API-15 | 否 | 无结果：有筛选时「No meetings match your search and filters.」，只搜索时「No meetings match your search.」 |
| 日期范围 | 工具栏 | — | From / To，可 Clear | API-15 | 否 | — |
| 参会人多选 | 工具栏 | — | 选项来自 API-16，命中任一即列出，可 Clear | API-16、API-15 | 否 | — |
| 有效性筛选 | 工具栏 | — | All tags / Invalid only / Hide invalid | API-15 | 否 | — |
| Clear filters | 工具栏 | 有筛选生效时显示 | 清空全部筛选 | API-15 | 否 | — |
| 列头排序 | 表头（除操作列外 7 列） | — | 首次升序、再点降序；默认 Date 降序 | API-15 | 否 | — |
| 分页 | 表格下方 | — | 同第 5 节开头（7 #Q43） | API-15 | 否 | — |
| Raw transcript | 行内 | — | 跳 PG-03 | — | — | — |
| Invalid 徽标 | 行内 | `invalid = true` | 悬停说明 | — | — | — |
| 视图记忆 | — | — | 搜索、筛选、排序、页码存 sessionStorage，从 PG-03 面包屑 / ← Back 或浏览器后退回来时恢复，从菜单、新开、手输地址进来或在本页刷新时清空（读写包在 try/catch 里，取不到用默认值；7 #Q67） | — | — | — |

公司端同一张表：只列本人受邀的会议，参会人选项也只来自这些会议，没有租户下拉。

### 4.6 PG-02 会议 Review 详情

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 加载 | — | — | 会议信息卡、参会人、矩阵一次取回；Scrub Status 只显示状态，不列子原因与待确认专家剩余标签数；Pending 会议有跨公司内容时 Pending 后带问号，悬停提示审核（7 #Q78） | API-21 | — | 会议不存在或无权：显示「Meeting not found」 |
| AI Meeting Type 下拉 | 信息卡 | — | 只改页面上的类型；选 `Unknown` 时 Start Extraction 置灰、Confirm & Apply 激活 | — | 否 | — |
| Company：删除 chip / 下拉添加 | 信息卡 | 候选来自 API-32（只列挂了 Portfolio 的公司与已选的；不在营的公司带状态标注，GS → 创始人时置灰不可选）；GS → 创始人多于一家时提示「GS → 创始人会议只能保留一家公司」 | 只改页面上的公司；GS → LP 的增删只激活 Confirm & Apply，其余类型激活 Start Extraction | API-32 | 否 | — |
| Portfolio 多选 | 信息卡 | GS → 创始人只读，显示公司所属 Portfolio；其他类型可选 | 只改页面上的标记，激活 Confirm & Apply | API-32 | 否 | — |
| 点参会人 chip | Participants | 按 `clickAction`：带 Possible expert 的开 PG-02c（建议标签处理完后按是否入册改开 PG-02a / PG-02b）；平台用户不弹框；名册已有 → PG-02b；AI 推断未入册、按域名判出未入册 → PG-02a；未识别（`Unidentified`）与未对上的说话人 → 下拉两项 `Create new person`（PG-02a）/ `Link existing person`（PG-02f）（7 #Q53、#Q56） | 打开对应弹框 | 数据来自 API-21 | — | — |
| AI inferred 悬停 | chip | — | 不弹提示（`aiEvidence` 前端不展示） | — | — | — |
| 证词补抽状态 / Retry | chip 与矩阵证词区 | `RUNNING` 与 `QUEUED` 都显示「证词补抽中」（7 #Q86）；`FAILED` 显示「证词补抽失败 · Retry」 | Retry 重新补抽，之后每 5 秒轮询 API-21 | API-29 → API-21 | 否 | 被拒时提示原因 |
| Start Extraction | 页头右上 | 按 9.5.1：必填齐（类型不是 `Unknown`；参会人里没有 Unidentified、没有未对上的说话人；GS → 创始人恰好一家公司），并且已提取过的会议要页头有未提交的类型或公司改动（GS → LP 的公司改动与 Portfolio 改动不算）、`participantsChanged` 或 `registryChanged`（不加提示，7 #Q84 ②）；待识别、提取作废、P1 / P8 失败的会议必填齐即可。提取或补抽进行中置灰 | 提交页头的类型与公司，整场下线并后台提取；按钮显示进行中，每 5 秒轮询 API-21 直到 `extractionStatus` 不是 `RUNNING`，再刷新整页；进页面时若已在提取或补抽，同样开始轮询；轮询拿到新 `updatedAt` 时保留页面上未提交的改动 | API-22 → API-21 | 否（设计 9.9.4） | 成功 toast「Extraction started」；作废后页头显示「提取失败」，按钮恢复可点 |
| 编辑 Content | 矩阵每行 | 来源行只读；该行发言人证词补抽中时不可编辑；页头类型 / 公司或参会人有还没提取的改动（`participantsChanged`，GS → LP 的公司增删不算）或类型改为 `Unknown` 时整表不可编辑，表格上方提示先点 Start Extraction（改 `Unknown` 时提示应用后整场下线） | 编辑后该行琥珀高亮，出现 Save / Cancel | — | — | — |
| 行内 Save | 矩阵行 | 该行有改动；摘要行不超过 150 个英文单词（前端计数，超长置灰并提示）；整表不可编辑时置灰（Cancel 照常） | 调 API-24：返回已落库即完成；返回清洗结果则弹 PG-02e 回显（删去的行及原因、替换的实体），管理员确认后带 `originalContent` 再调一次，或返回继续改 | API-24 | 有命中时回显确认 | 成功 toast「Content saved」；被拒提示原因 |
| 行内 Cancel | 矩阵行 | 该行有改动 | 还原该行 | — | — | — |
| Authorize 勾选 | 矩阵行 | 摘要行：同一（去向, 公司）的正文行已删时置灰，置灰时不弹悬停提示；整表不可编辑时置灰 | 只改页面上的勾选，激活 Confirm & Apply；同一（去向, 公司）的正文行与摘要行当成一个勾选框，一起勾选、一起取消（7 #Q55） | — | — | — |
| Discard Changes | 页面底部 | 有未提交的页头类型 / 公司、勾选或 Portfolio 改动（比 9.6.5 收窄） | 还原这些改动以及编辑中未保存的行；不撤销已 Save 的内容、名册写入、补抽结果与已点过的 Start Extraction（9.6.5） | — | 否 | — |
| Confirm & Apply Routing | 页面底部 | 按 9.6.5 按钮状态表（自下而上优先）：改为 Unknown 即激活，只在提取或证词补抽进行中置灰（7 #Q25e）；Discard Changes 左侧不放任何提示；置灰时不弹悬停提示；有行在编辑未保存时先提示该行 Save 或 Cancel | 一次提交勾选、Portfolio、改 `Unknown`、GS → LP 的公司增删；返回 40903 时弹二次确认框逐条列出 `warnings`（按当前参会人判定的类型与当前类型不同，带建议类型），确认后带 `confirmWarnings=true` 重提，取消则不提交（7 #Q48） | API-23 → API-21 | 类型改为 `Unknown` 时不弹确认、直接提交；返回 40903 时弹上述二次确认 | 成功 toast「Routing applied」，刷新 API-21；被拒提示原因 |
| 面包屑 | 页头 | — | 回 PG-01 Summary Records Tab，`org` 取该会议的租户 | — | — | — |

### 4.7 PG-02a / PG-02b / PG-02c / PG-02f 会议页弹框

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| PG-02a 字段 | 弹框 | 用 API-21 的 `registryForm` 预填；Name 可改，失焦调 API-41 查重，重名提示同 PG-01c1（7 #Q46）；来源是参会人时本场邮箱锁定（不可删改，可加别的邮箱）；来源是未对上的说话人时 Name 取说话人名、Email 为空且必填、不锁；Validity From 默认会议日期、To 空，有效期必须包含会议日期，不含时在字段下提示并不能提交（7 #Q44）；其余字段与校验同 PG-01c1 | — | API-12（标签）、API-41 | — | — |
| PG-02a Confirm | 弹框底部 | 必填齐、有效期包含会议日期 | 弹「Confirm submission」→ Yes, submit 后提交 | API-25 | 是 | 成功关闭、刷新 API-21；`suggestedCompany`、`suggestedType` 前端不提示（公司、类型由管理员在页头手动选）；邮箱是本租户 LG 用户时提示「按平台用户识别，不进名册」；返回 `registryMatchedName` 时提示「已按名册中的 X 识别，未新建」（7 #Q49）；42200 时在弹框内显示原因、不关窗 |
| PG-02b 字段 | 弹框 | 用 API-21 的 `registryForm` 预填（会议日期当天生效的那条 T2，有效期为 T2 原有效期）；只有 Name 只读；本场邮箱锁定（不可删改，可加别的邮箱；T2 里没有本场邮箱时已补进）；有效期可改，必须包含会议日期（7 #Q44） | — | API-12 | — | — |
| PG-02b Confirm | 弹框底部 | 必填齐、有效期包含会议日期；首轮未完、提取进行中、页面上别的写请求在途时置灰（7 #Q44）；证词补抽进行中不置灰（7 #Q51） | 调 API-07（带 `sourceMeetingId`，`{id}` 为 `versionId`）追加一条完整新版本，成功后关窗、调 API-28 同步本场，再刷新 API-21；没有任何改动时 Java 不写，照常同步；本场没有参会人改动、且上次提取成功时，同步把专长标签与快照不同的专家都排进证词补抽（7 #Q83、#Q86、#Q87） | API-07 → API-28 → API-21 | 否 | 返回 40901 时提示稍后重试（同步可重复调用）；邮箱已登记在别人名下时在弹框内显示原因、不关窗、不同步（7 #Q49） |
| PG-02c 内容 | 弹框 | 只有登记字段，不列 AI 的推测依据、不设小节标题与说明文字（7 #Q82）；没有逐标签按钮，建议标签预填进 Expertise tags 标签栏（显示为「建议」标签）：`resolvedAs = DECLINED` 的不预填，`ACCEPTED` 的就是普通已有标签；留下即同意、删掉即驳回（7 #Q45）。保存一律写名册（7 #Q51）。登记字段：已在册的人用 T2 预填、只有 Name 只读；未入册的外部人为完整表单（同 PG-02a），Name 可改、失焦调 API-41 查重；LG 平台用户 Name 取账号姓名、只读，Role 预填平台账号推出的角色、可改（7 #Q47）。本场邮箱锁定（不可删改，可加别的邮箱）；有效期可改、必须包含会议日期，已在册的预填 T2 原有效期，新登记默认 From = 会议日期、To 空（7 #Q44） | — | API-12、API-41 | — | — |
| PG-02c Save | 弹框底部 | 首轮未完、提取进行中、页面上别的写请求在途时置灰（7 #Q44）；证词补抽进行中不置灰（7 #Q51）；登记字段必填齐、有效期包含会议日期；Expertise tags 可为空、不按角色必填（删光建议标签即拒绝） | 调 API-08（`suggestedTags` 为本次打开时的建议标签，`entry` 为登记字段（必填），`baseVersionId` 为 `versionId`），Java 同一事务写名册与拒绝名单：未登记的新建、已在册的追加一条完整新版本（与 T2 相比没改动不写），标签栏为空也照建 / 照追加（7 #Q51）；成功后关窗、调 API-28（新登记带 API-08 返回的最终姓名），再刷新 API-21；标签变了的专家同步时即补抽证词（同 PG-02b，7 #Q83、#Q87） | API-08 → API-28 → API-21 | 未入册的外部人新建名册时弹「Confirm submission」（9.5.6）；已在册的、LG 平台用户不弹 | 返回 40901 时提示稍后重试；邮箱已登记在别人名下时在弹框内显示原因、不关窗、不同步（7 #Q49） |
| PG-02c Cancel / 关闭 | 底部 Cancel、右上 × | — | 不保存、不调接口，什么都不写（7 #Q44）；徽标保留剩余未处理数 | — | — | — |
| PG-02f 选人 | 弹框第一步 | 标题 `Link existing person`，说明「Link <来源姓名> to a person in the Cheat Sheet.」；搜索框 + 名册人员列表（Name、Organization、Role、Email(s)），单选、分页；会议当天没有生效版本的人（`effectiveOnMeeting = false`）置灰，表格下方提示「No Cheat Sheet entry on the meeting date. Adjust the validity period in Cheat Sheet first.」（置灰行悬停同此）；提取进行中第二步的 Confirm 置灰（同 PG-02b） | 输入后查询（防抖 300ms，每页 10 条），关键字沿用 API-05 的匹配范围；选中后进入第二步 | API-05（带 `meetingId`） | 否 | 取数失败在弹框内提示 |
| PG-02f 人员信息 | 弹框第二步（表单同 PG-02b） | 预填所选人会议当天生效的那一版；Name 只读；来源是参会人时本场邮箱自动补进 Email(s) 并锁定（保存即写进名册，以后按邮箱直接认出），来源是说话人时不补不锁；有效期须包含会议日期 | 其余字段可改；可返回第一步重选 | — | — | — |
| PG-02f Confirm | 弹框底部 | 必填齐、有效期包含会议日期 | 来源是参会人：API-07 追加一版 → API-28 带所选人姓名把本场此人挂到该条目；来源是说话人：表单有改动先 API-07，再 API-25 把说话人绑到此人（本场已有他的邮箱就绑那位参会人，没有就并入一位非受邀参会人）。被关联的人在本场已有另一位参会人时仍是两位、同名显示，不合并（7 #Q53 ③） | API-07 → API-28；或 API-07 → API-25 | 否 | 成功 toast「Linked to <name>」、刷新 API-21，之后的类型判定按设计 9.9.3；被拒（如邮箱已登记在别人名下）时在弹框内提示原因。API-07 成功而后一步失败时：参会人同 PG-02b 的同步失败（已关窗，提示打开此人点 Save 重试，API-21 已按在册展示，7 #Q51 ⑤）；说话人留在弹框内提示原因，可直接再点 Confirm（API-07 没有改动时不再写） |
| 各弹框 Cancel | 弹框底部 | — | 关闭，不保存 | — | — | — |
| 专长标签维护 | Expertise tags 下拉 | 同 PG-01c2 | 新增 / 删除标签；调 API-12 / 13 / 14 时带 API-21 返回的会议所属 `organizationId` | API-13、API-14 | 同 PG-01c2 | 同 PG-01c2 |
| PG-02e 确认保存 / 继续修改 | 清洗回显弹框底部 | 确认保存：清洗后还有内容（删空时置灰） | 确认保存：带 `originalContent` 再调一次；继续修改：关闭弹框、回到该行 | API-24 | — | 同行内 Save |

### 4.8 PG-03 原文页、PG-04 Role History

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| PG-03 加载 | — | — | 页头与首批句子 | API-17、API-18 | — | 无权或不存在都显示未找到态（「Transcript not found」「No ingested meeting matches this ID.」「Back to Fireflies Meeting Data」），不区分两者；转录为空时正文显示「No transcript content.」 |
| PG-03 后台续加载 | 正文底部 | `hasMore = true` | 首批显示后自动连续取下一批直到取完（每批 500 句），期间底部显示「Loading the rest of the transcript…」 | API-18 | — | 某批失败即停，底部显示 Retry，从失败的批次接着取 |
| PG-03 面包屑 / ← Back | 页头、页尾 | — | 第一级「Fireflies Management」回 PG-01 默认 Tab；第二级「Fireflies Raw Data」与 ← Back 回 Raw Data Tab（都带 `org`；公司端回自己的 Raw Data） | — | — | — |
| PG-04 加载 | — | — | 此人全部版本 | API-09 | — | 不存在或无权（PM）：「Registry entry not found」 |
| PG-04 面包屑 | 页头 | — | 第一级回 PG-01 默认 Tab，第二级「Cheat Sheet」回 Cheat Sheet Tab（都带 `org`） | — | — | — |

### 4.9 PG-05 Goldie Base

| 操作 | 位置 | 显示 / 可用条件 | 行为 | 调用接口 | 二次确认 | 成功 / 失败反馈 |
|---|---|---|---|---|---|---|
| 进入 / 切换 Tab | Tab 栏 | 管理端 4 个；公司端 Company Admin 4 个；公司端普通用户没有 Memory Settings、其余 3 个（7 #Q57） | 改 URL `?tab=`；地址里的 Tab 没有权限时回落到 Knowledge Base；管理端一律取组织树第一个叶子租户（7 #Q32） | API-19、API-39 | 否 | — |
| 侧栏 / 底栏入口 | 门户侧栏、手机端底栏 | — | 合并后的 Goldie Base 入口高亮；Conversation history 回 `/askGoldie` | — | — | — |
| KB：搜索与筛选 | PG-05a 筛选栏 | — | 保持现有：只按文件名搜，筛选项不变，不加 Source 筛选（7 #Q24a） | API-33、API-34 | 否 | — |
| KB：下载 | PG-05a 行内 | 现有规则；Fireflies 行按 API-35 新分支（响应带 `content` 时前端用 Blob 下载，3.6） | 下载 | API-35 | 否 | 失败提示 |
| KB：删除 | PG-05a 行内 | Fireflies 行不显示 | 现有行为 | API-36 | 是（现有） | 现有 |
| KB：Source 链接 | Source 列 | Fireflies 行，且后端返回可点 | 跳 PG-03；不可点时显示纯文字 | — | — | — |
| Memory：File Scope | PG-05b 筛选栏 | 管理端；公司端不显示 | All Files / Company Memory / Portfolio Memory / Fireflies Memory（7 #Q24b）；Company / Portfolio Memory 只列上传文件的摘要，会议摘要只在 All Files 与 Fireflies Memory 下出现 | API-37 | 否 | — |
| Memory：搜索、公司筛选 | PG-05b 筛选栏 | 公司筛选只在管理端 | 现有行为：按摘要全文与文件名搜索，不加设计稿的公司匹配（7 #Q25c） | API-37 | 否 | — |
| Memory：查看详情 | PG-05b 行 | — | 现有详情弹框；会议摘要的标签为 Fireflies Memory + Meeting Summary，不带层徽标 | — | — | — |
| 跨公司 / 证词：搜索 | PG-05c / PG-05d 工具栏 | — | 管理端匹配内容与会议名称，证词另匹配说话人姓名（7 #Q25b）；公司端只匹配内容（7 #Q57） | API-30 | 否 | 无结果显示空态 |
| 跨公司 / 证词：时间范围 | 工具栏 | 管理端；公司端不显示（7 #Q57） | 按会议日期区间 | API-30 | 否 | — |
| 跨公司 / 证词：分页 | 列表下方 | — | 同第 5 节开头（7 #Q43） | API-30 | 否 | — |
| 跨公司 / 证词：会议名 | 卡片 | `canOpen`（PGM / SA）可点，PM 为纯文字；公司端不显示会议 | 跳 PG-02 | — | — | — |
| Play candidate 开关 | 每条内容旁 | `canTogglePlaybook`（PGM / SA）可切换；PM 只读显示；公司端不显示 | 切换即提交 | API-31（`inPlaybook`） | 否 | 失败还原并提示 |

### 4.10 按钮 ↔ 接口对账

- 每个按钮引用的接口都在第 3 节清单里；第 3 节对账表里属于各页面的接口，本节都有对应的加载时机或操作。
- 没有按钮直接触发的接口：API-38（Ask Goldie 对话，见 3.5）；API-40 不再使用（7 #Q41）。
- 设计没写、这里补定的交互：原文页与会议详情对「无权」与「不存在」显示同一提示；PG-02c 未入册的外部人新建名册时弹 Confirm submission（LG 平台用户不弹）；Discard 只在有未提交改动时激活（比 9.6.5 收窄）；证词补抽中该发言人的证词行不可编辑；有还没提取的页头 / 参会人改动或类型改为 `Unknown` 时矩阵整表不可编辑。

## 5. 页面布局

设计稿为 Lovable 项目 FFL（commit `76cc767`），下文「设计稿」后的路径相对其 `src/`。web 用 antd 4.9.2（没有 `items` API，Tab 用 `Tabs.TabPane`），优先复用：下沉后的组织树下拉（原 ERL `OrganizationSelect`，2「入口与守卫」）、`src/components/MultiSelectDropdown`、`common/breadCrumbs.tsx`、`common/SuspendClose.tsx`、`FileTypeIcon`、askGoldie 域内的 `orgScope.ts`、`MultiSelectFilter.tsx`；原文页整篇直接渲染、不用虚拟滚动（7 #Q29）。

设计稿已有的标题、按钮名、文案与控件样式（如 Sync now 是文字链接、Tab 名带 Fireflies 前缀）照设计稿，下文只记有意偏离与设计稿没画到的地方；线框只示意区域划分。

日期时间（7 #Q25f）：一律固定 UTC，格式照设计稿——日期时间 `Jul. 15, 2026 at 10:52 a.m. UTC`，只有日期 `Jul. 15, 2026`，只有时刻 `10:52 a.m. UTC`（月份缩写带点、日不补零、12 小时制补零）；会议日期按 UTC 自然日；逐句时间点为 `[hh:mm:ss]`。适用于本功能新增的页面与 Tab；Knowledge Base、Memory Settings 的日期列保持现有格式。

通用状态：加载用 antd `Spin`（表格用自带 loading）；空列表用 `Empty` 加设计稿文案；接口失败在区域内显示错误与「重试」，不弹全局横幅（这些接口加进 `request.ts` 的 `isInlineErrorEndpoint`）；无权限用 antd `Result`（403）。

分页（7 #Q43）：Summary Records、Cheat Sheet、Raw Data 与 Goldie Base 两个新 Tab 一律对齐现有 Knowledge Base（`KnowledgeBasePage.tsx` 的 `pagination`）：默认每页 10 条，可选 10 / 20 / 50；常显总数 `${start} - ${end} of ${total} items`，记录少时也不隐藏，不开跳页；手机端隐藏条数选择、用小号。

弹框：所有 `Modal` 去掉 antd 默认的标题下、底部按钮上两条分割线；输入框、下拉、日期与按钮一律 4px 圆角，确认框按钮靠 `className: 'ffConfirmDialog'`（`global.less`，弹框挂在 body 上、页面样式管不到）；主按钮置灰时为淡化品牌色、不弹悬停提示。

### 5.1 PG-01 Fireflies Management

参照设计稿：`routes/index.tsx:150-206`（Tab 容器）

```
┌──────────────────────────────────────────────────────────────┐
│ Fireflies Management                        [组织树下拉 ▾]   │
├──────────────────────────────────────────────────────────────┤
│ Fireflies Summary Records ● │ Fireflies Configuration │       │
│ Cheat Sheet │ Fireflies Raw Data                             │
├──────────────────────────────────────────────────────────────┤
│ 当前 Tab 内容（5.2~5.5）                                       │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 标题与面包屑 | `breadCrumbs` | 「Fireflies Management」 |
| 组织树下拉 | 下沉后的组织树下拉 | 根下有子组织才显示，公司端不显示（设计稿没有，7 #Q17） |
| Tab 栏 | `Tabs.TabPane` | Summary Records 标题旁红点；公司端只有 Raw Data，不渲染 Tab 栏 |

状态：PM 进入显示 403；公司端直接显示 Raw Data 内容。

### 5.2 PG-01a Summary Records

参照设计稿：`components/summary-records-tab.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ Fireflies Summary Records                                    │
│ [Search …] [类型 ▾] [状态 ▾] [时间 ▾]                          │
├──────────────────────────────────────────────────────────────┤
│ Meeting │ Time │ AI Meeting Type │ Companies │ Status │ Review │
├──────────────────────────────────────────────────────────────┤
│                                                     分页      │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 筛选栏 | `Input.Search`、`Select` ×2、时间区间浮层（`DatePicker.RangePicker`，标签显示 All time / From X / X – Y） | 搜索框占位文字「Search by meeting ID, title or company」（7 #Q67）；类型：All meeting types + 5 种；状态：All statuses / Passed / Pending（7 #Q25d） |
| 表格 | antd `Table`（服务端分页） | Meeting（标题链接 + `<fireflies_id> · <n> min`）、Time（单列合并）、AI Meeting Type（蓝标签，Unknown 灰）、Companies（逗号分隔，超宽省略号；GS → LP 没有公司时显示「Fund-level」）、Status（✓ Passed 绿 / ◷ Pending 红，悬停显示两态说明，白底细边框、无箭头；不旁注 Pending 原因）、Review 链接 |

状态：空列表「No meetings match your search.」。从 PG-02 回来时恢复查询条件（4.2「视图记忆」）。

### 5.3 PG-01b Configuration 与 PG-01b1

参照设计稿：`routes/index.tsx:208-326`

```
┌────────────────────────── Connection ─────────────────────────┐
│ Fireflies workspace connected as <account_email>              │
│ ● Connected     Last sync: …                        [Sync now]│
├────────────────────────── API Key ────────────────────────────┤
│ 未绑定： 说明文案                                               │
│          [Enter your Fireflies API key        ] [Link]        │
│ 已绑定： Current key  [••••••••a3f9]              [Remove]    │
└───────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| Connection | 状态点 + 文案 + `Button` | 接真实数据；状态点颜色按 9.2.4（含 Failed / Disconnected）；`UNCONNECTED` 时不显示 connected as 一行、Sync now 置灰；从未成功同步时 Last sync 显示 `—`；Sync now 同步中显示「Syncing…」并置灰 |
| API Key | `Input.Password`（未绑定）/ 只读掩码框（已绑定）+ `Button` | 未绑定时的说明文案「Link your Fireflies API key to enable automatic meeting ingestion.」；Link 失败的原因显示在输入框下方；掩码固定 8 个圆点 + 后 4 位（不暴露 key 长度） |
| PG-01b1 | `Modal.confirm` | 标题「Remove API key?」，正文「Fireflies will be disconnected and meetings will stop syncing until a new key is linked.」，按钮 Cancel / Remove（红色） |

### 5.4 PG-01c Cheat Sheet、PG-01c1、PG-01c2

参照设计稿：`routes/index.tsx:662-858`（列表与 Email Domain 块 `:332-459`）、`:860-1096`（PartyEditor）、`components/expertise-select.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ External Parties Registry                [Add external party]│
│ [Search …] [Role ▾]                                          │
├──────────────────────────────────────────────────────────────┤
│ Name │ Email(s) │ Organization │ Role │ Expertise tags │      │
│ Validity period（逾期加 [Needs review]）│ History / Edit       │
├──────────────────────────────────────────────────────────────┤
│                                                     分页      │
├────────────────────────── Email Domain ───────────────────────┤
│ Add the email domains used to identify internal participants.│
│ @gst.com                                      Edit  Delete   │
│ [e.g. goldie.vc                       ] [Add]                │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 列表 | antd `Table`（服务端分页） | Name（审核会议时导入的加 `From FF Summary Records` 标签、`lgUser = true` 的加 `LG user` 标记，7 #Q51；标签放姓名下方、放不下换行，姓名单行过长省略、悬停看全，表格总宽压到 1200 免出横向滚动条）、Email(s)（纵向全列，放不下时省略号、悬停看全）、Organization、Role（蓝标签）、Expertise tags（灰标签，显示全部，换行）、Validity period（`Aug. 2, 2026 – present`，逾期（设计 9.7.5：90 天）加黄 `Needs review`）、History / Edit。标签无边框、色块底、4px 圆角（同系统 Company Status 标签）；Role 与 `From FF Summary Records` 蓝、Expertise 灰，色值取自设计稿；`LG user` 用 Thriving 绿、`Needs review` 用 Needs Guidance 黄；History 页同 |
| Email Domain 块 | 列表 + 行内 `Input` + `Button` | 不分页；Edit 时该行变输入框 + Save / Cancel |
| PG-01c1 | `Modal` + `Form` | 字段与校验见 4.4；必填项（Name、Email(s)、Organization、Role、Validity period，Role 为 LP / Strategic Partner / Exit Partner 时另有 Expertise tags）标签后带红色 `*`（Red/900 `#c2060e`；`global.less` 藏掉了 antd 标签前的星号，照会议页 AI Meeting Type 手补）；Name 编辑时置灰，`lgUser = true` 的在 Name 旁显示 `LG user`（7 #Q51），新增时重名提示显示在 Name 下方（API-41，7 #Q46）；Email(s) 多行，`+ Add another email`；Role 为 6 项 `Select`，新增时为空（设计 9.7.4）；Expertise tags 用 PG-01c2；Area of expertise 为 `TextArea`；Validity period 为两个 `DatePicker`（To 可清空），To 禁选 From 之前、From 禁选 To 之后的日期，同一天可以（同 Java 校验）；新增的 Confirm 前弹 `Modal.confirm`「Confirm submission」。PG-02a / PG-02b 共用此弹框 |
| PG-01c2 | 多选 `Select`（`mode="multiple"`，带下拉箭头同 Role，`dropdownRender` 底部加「Add a new tag…」输入框，可删的选项悬停显示删除，同设计稿 `expertise-select.tsx`） | 预置 7 项在前，新增的按添加顺序在后 |

与设计稿的差异：Expertise tags 只对 LP / Strategic Partner / Exit Partner 必填（7 #Q24d）；不显示逾期提示条；搜索另匹配 Area of expertise（设计 9.7.3）；加分页。

### 5.5 PG-01d Raw Data

参照设计稿：`routes/index.tsx:481-660`、`components/raw-data-filters.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ [Search …] [日期 ▾] [参会人 ▾] [有效性 ▾] Clear filters        │
├──────────────────────────────────────────────────────────────┤
│ Meeting ID↕ │ Title↕ │ Date↕ │ Time↕ │ Duration↕ │            │
│ Participants↕ │ Ingested at↕ │ Raw transcript / [Invalid]     │
├──────────────────────────────────────────────────────────────┤
│                                                     分页      │
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 工具栏 | `Input.Search`、日期区间浮层、`MultiSelectDropdown`（参会人）、`Select`（All tags / Invalid only / Hide invalid）、Clear filters 链接 | 有筛选生效时才显示 Clear filters |
| 表格 | antd `Table`（服务端分页、服务端排序） | 7 列可排序；Participants 全部展示不截断；Ingested at 日期、时刻分两行，单元格左右内边距 12px，徽章在链接下方，窗口窄时横向滚动；Invalid 徽标灰色，悬停照设计稿原文「Automatically filtered out. The meeting was too short or had nothing worth routing. No action needed」，白底细边框无箭头、中灰字（判定本身不看长短，设计 9.3.4） |

状态：空结果有筛选时「No meetings match your search and filters.」，只搜索时「No meetings match your search.」。公司端同一布局，没有租户下拉。与设计稿的差异：加分页。

### 5.6 PG-02 会议 Review 详情与弹框

参照设计稿：`routes/meetings.$id.tsx:896-1237`（页面）、`:196-443`（AssignExternalPartyModal）、`:454-672`（ExpertSuggestionModal）、`lib/routing-content.ts`

```
┌──────────────────────────────────────────────────────────────┐
│ Fireflies Management > Meeting Detail                        │
│ <会议标题>                                                     │
│ Fireflies Summary Records > Meeting Detail                    │
├──────────────────────────────────────────────────────────────┤
│ 提示文案                                     [Start Extraction] │
│ Date … Duration … Fireflies ID … Scrub Status                 │
│ AI Meeting Type* [▾]                                          │
│ Company(*) [公司 ×] [Company ▾] （* 仅 GS → 创始人；每家公司下一行识别依据）│
│ Portfolio [Fund ×] [Portfolio ▾]                               │
│ Participants  [参会人胶囊 + 徽标] …                             │
│   [<姓名> · — (Unidentified) ●]                                │
│   [<姓名> · N sentences (Unmapped speaker) ●]                  │
│     └ 点开：Create new person / Link existing person            │
├────────────────────── Content Routing Matrix ─────────────────┤
│ Content                         │ Visible to        │ Authorize │
│ [摘要]                           │ …                 │    ☑      │
│ [KB 正文（markdown）]            │ …                 │    ☑      │
│ Source: …（证词只读来源行）        │                   │           │
│ [证词 / 跨公司内容]               │ …                 │    ☐      │
├──────────────────────────────────────────────────────────────┤
│                    [Discard Changes] [Confirm & Apply Routing]│
└──────────────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 页头 | `breadCrumbs`、提示文案、`Button`（Start Extraction） | 提取进行中按钮显示进行中并置灰 |
| 会议信息卡 | 描述列表 + `Select`（类型）+ 可关闭的标签（公司 / Portfolio）+ `Select` 入口（下拉列全部候选，已选的浅黄底高亮、再点移除，悬停灰底，不显示滚动条；Company 下拉顶部带搜索框，同设计稿） | 公司可多选（设计 9.5.3；GS → 创始人只允许一家，多于一家时提示）；每家公司下方一行识别依据（9.5.3 文案）；未采纳的候选不展示；GS → 创始人的 Portfolio 只读 |
| 参会人 | 胶囊 `Tag` | 按身份着色（GS 蓝、Founder 橙、外部紫、未识别与未对上的说话人灰 + 红点）；徽标 Possible expert / AI inferred 叠加在胶囊上（不弹依据，设计 9.5.5 / 9.5.6）；平台用户不弹框（带 Possible expert 的除外）；未识别与未对上的说话人点开下拉 `Create new person` / `Link existing person`（7 #Q53、#Q56）；证词补抽中 / 失败 · Retry 显示在胶囊旁 |
| Content Routing Matrix | 自写表格：每行内容 + Visible to 文本 + `Checkbox`；各行（摘要、Knowledge base、跨公司、证词）都是 markdown，平时按 markdown 渲染（react-markdown），点 Edit 换成 markdown 编辑器（react-markdown-editor-lite，只有工具栏与编辑区），Cancel / 保存成功后回到渲染态 | 改动行琥珀边框并出现 Save / Cancel，内容只经行内 Save 保存；证词行的来源行只读显示在正文上方（带会议开始时间，与投影写进条目的是同一行，7 #Q74）；不显示出处时间点 `[hh:mm:ss]`（7 #Q74）；跨公司一场会一行、证词每位发言人每版一行，整块一个编辑框（正文里每条一段、段首是类别标签，7 #Q77）；GS 内部 / Partner 按公司分组、行标注公司名；GS → LP 标注机构层；Pending 会议首次提取前矩阵为空，显示「提取后在此显示」；提取进行中显示「提取中」占位，作废后显示「提取失败，补齐后点 Start Extraction」；`projectionStatus = FAILED` 的行显示红色标记，悬停说明投影失败；摘要行的 `Checkbox` 与同组正文行一起勾选、一起取消，正文行已删时置灰（4.6，7 #Q55）；证词区按 `speakerParticipantId` 显示该发言人的「证词补抽中」/「证词补抽失败 · Retry」。Visible to 文案：`KB_APP` → Founder, PM & PGM；`TESTIMONY_SIGNED` → Expert testimony (Portfolio)；`TESTIMONY_ANON` → Expert testimony (Founder)；`CROSS_COMPANY` → Cross company（以上同设计稿）；`KB_ADMIN` → PM & PGM、`FUND_LEVEL` → PM & PGM (fund level)（设计稿没有） |
| 底部按钮 | `Button` ×2 | 置灰时不弹悬停提示 |
| PG-02e 行内 Save 的清洗回显 | `Modal` | 列出删去的行及原因、替换的实体，按钮「确认保存」/「继续修改」；清洗后什么都不剩时「确认保存」置灰（淡化品牌色）、预览处提示 `Nothing left to save. Keep editing to revise this content.` |
| PG-02a / PG-02b | `Modal` + `Form`（同 PG-01c1） | 标题 `Assign new external party — <name>` / `Edit external party — <name>`；PG-02b 的 Name 置灰，PG-02a 的 Name 下方显示重名提示（API-41）、From 默认会议日期；本场邮箱那一行锁定（不可删改、不显示 ×），可加别的邮箱；有 Area of expertise（设计 9.5.5）；有效期不含会议日期时在字段下提示并不能提交（7 #Q44） |
| PG-02c | `Modal` | 标题 `Possible expert — <name>`；内容、预填、只读与校验规则见 4.7 |
| Confirm & Apply 二次确认 | `Modal.confirm` | API-23 返回 40903 时弹出，逐条列出 `warnings`，确认后带 `confirmWarnings=true` 重提（7 #Q48）；文案按设计稿语气定稿 |
| PG-02f | `Modal` 两步：选人（搜索框 + 单选列表 + 分页）→ 人员信息（复用 PG-02b 的 `RegistryFormModal`，标题 `Link existing person — <name>`） | 按项目同类弹框样式 |

状态：会议不存在或无权显示「Meeting not found」；矩阵为空的说明见上。

与设计稿的差异：Start Extraction 只对 GS → 创始人要求有公司（设计 9.5.1）；Authorize 勾选激活 Confirm & Apply；改 Unknown 后 Confirm & Apply 激活（7 #Q25e）。

### 5.7 PG-03 原文页、PG-04 Role History

参照设计稿：`routes/fireflies-transcripts.$id.tsx`、`routes/registry.$id.history.tsx`

```
PG-03                                    PG-04
┌───────────────────────────────┐      ┌───────────────────────────────┐
│ 面包屑 / <会议标题> / 二级面包屑 │      │ 面包屑 / <Name> — Role History │
├───────────────────────────────┤      ├───────────────────────────────┤
│ Date … Time … Duration …      │
│ Participants …                │      │ 版本表：Name │ Email(s) │ Role │
│ Full Transcript               │      │ Organization │ Expertise tags │
│ [00:00:04] Speaker: text      │      │ Area of expertise │ Validity   │
│ …（整篇渲染，后台续加载）       │      │ period │ Updated by           │
├───────────────────────────────┤      │ 最新在前，每行一个完整快照       │
│ ← Back                        │      └───────────────────────────────┘
└───────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| PG-03 页头 | 文本 | 标题下一行「Raw verbatim transcript — unclassified and unmodified · captured <created_at>」（设计 9.3.5） |
| PG-03 信息卡 | 描述列表 | Participants 用出席记录姓名，没有则回退受邀邮箱 |
| PG-03 正文 | 逐行直接渲染（不用虚拟滚动，保证浏览器 Ctrl+F、复制、打印覆盖全篇，7 #Q29） | 每行 `[hh:mm:ss] speaker_name: text`，说话人照原样显示；首批到达即显示，其余批次在后台连续加载，期间底部显示 `Spin` 与「Loading the rest of the transcript…」（此时 Ctrl+F 只覆盖已加载部分）；某批失败即停并显示 Retry |
| PG-04 表格 | antd `Table`（不分页） | 按 `updated_at`、`id` 倒序（同 API-09）；每行一个完整快照（设计 9.7.6，含 Area of expertise 与全部标签）；Updated by 显示操作人与日期（会议页登记的也是实际操作人，系统用户为 `System`） |

状态：PG-03 无权或不存在显示「Transcript not found」；PG-04 不存在显示「Registry entry not found」。

### 5.8 PG-05 Goldie Base

参照设计稿：`routes/knowledge-base.tsx`（Tab 容器 `:815-891`、Knowledge Base `:142-303`、Memory Settings `:577-661`、Cross Company Content `:332-493`（时间筛选 `:332-397`、卡片 `:399-438`）、Expert Testimony `:691-813`）、`routes/ask-goldie.tsx:80-89`（入口）

```
┌────────┬─────────────────────────────────────────────────────┐
│ 门户    │ Goldie Base                                          │
│ 侧栏    │ 页头说明（同设计稿）                                    │
│ Goldie │ Knowledge Base │ Memory Settings │ Cross Company Content │ Expert Testimony │
│ Base ● ├─────────────────────────────────────────────────────┤
│        │ [Search …] [时间 ▾]                                  │
│        │ ┌ Meeting source: <会议名>                         ┐ │
│        │ │ <fireflies_id> · <会议时间 UTC>（不加 #、不显示类型） │ │
│        │ │ • 内容                         Play candidate [○ ] │ │
│        │ │ （证词另显示 Expert <姓名> [专长标签]）              │ │
│        │ └───────────────────────────────────────────────────┘ │
│        │                                              分页    │
└────────┴─────────────────────────────────────────────────────┘
```

| 区域 | 组件 | 说明 |
|---|---|---|
| 门户外壳 | 现有 `PortalNavSidebar` / `PortalTabBar`（上提到 Goldie Base 页） | 两个入口合并为一个 Goldie Base；两个旧页去掉自带外壳，只保留内容区；侧栏「+」沿用现有行为 |
| Tab 栏 | `Tabs.TabPane` | 顺序：Knowledge Base · Memory Settings · Cross Company Content · Expert Testimony；公司端普通用户没有 Memory Settings（7 #Q57） |
| Knowledge Base | 现有 `KnowledgeBasePage` 内容区 | 新增 Source 列（`Goldie` / `Fireflies`，Fireflies 可点时为链接）；Portfolio 列纯文字，显示 `portfolioDisplay`；Fireflies 行不显示删除；手机端折行同样显示 Source，空 Portfolio / Company 显示 `—`；Fireflies 行的 From Chat 与 Uploaded By 显示 `—`（7 #Q25a） |
| Memory Settings | 现有 `MemorySettingsPage` 内容区 | 摘要按 markdown 渲染：详情弹框渲染，列表两行预览去掉标记（设计第十章 #20）；管理端 File Scope 加 Fireflies Memory；会议摘要的 `MemoryMetaRow` 显示 Fireflies Memory（青色，占层徽标的位置）+ Meeting Summary，不带层徽标；公司位为空显示 `—` |
| 两个新 Tab | 卡片列表：相邻的同场行归成一张卡片，`Switch`（Play candidate，接真实数据） | 工具栏：`Input.Search`（包含匹配）+ 时间区间浮层；证词卡片另显示 `Expert <姓名>` 与专长标签（一行一位发言人，7 #Q77；取不到说话人姓名时显示 `Unassigned`，当日没有专长标签时标签区不显示）；会议名与开关按角色控制，会议名 PM 为纯文字；按条目入库时间倒序、分页按行（7 #Q72），同一场会跨页或与别场交错入库时拆成多张卡片，卡片内按入库先后。公司端（7 #Q57）：每行一张卡片（跨公司一场会一行、证词一人一行，7 #Q77）、不按会议归组，没有会议名与元数据、没有 `Switch`，工具栏没有时间区间；证词在正文下显示 `Expertise` 与专长标签，没有姓名，没有标签时这一行不显示 |

状态：两个新 Tab 空列表用设计稿文案「No content matches your search.」「No expert testimony matches your search.」；公司端搜索框占位文字为 `Search by content` / `Search by testimony`。与设计稿的差异：Knowledge Base 不做 Source 筛选与文件名以外的搜索（7 #Q24a）；Memory File Scope 不加 Document Summary 选项（7 #Q24b）。

## 7. 已定口径（按 Q 编号）

本节按编号列各项的现行口径，正文与代码注释按「7 #Qn」引用；Q61 暂缓，Q37~Q40 为待核实事项（见节末）。

| # | 主题 | 现行口径 | 影响位置 |
|---|---|---|---|
| Q1 | Configuration 回显 key 与 `Remove` | 查询接口服务端解密后只返回掩码串（后 4 位），原文与密文不出接口；`Remove` 清空密文、状态回 `UNCONNECTED`、暂停定时拉取，写 Java 应用日志 | J1；设计 9.2.3~9.2.5、9.2.7 |
| Q2 | Python 物理表名前缀 | `ai_ff_*` | A3、P1~P8 |
| Q3 | Java 表时间列类型 | `timestamptz` | A2、J1~J5 |
| Q4 | 预置专长标签的写入时机 | 新建组织时写入（`OrganizationServiceImpl.save`，同 KPA、Tech Stack 初始化），存量组织由 Java V1 补齐；不懒加载 | J5；设计 9.8.1 |
| Q5 | GS 租户邮箱域名初始化 | 上线时管理员在 Cheat Sheet 页添加，不写迁移 | J1、1.4；设计 9.7.7 |
| Q6 | SQS 投递成败与 `dispatched_at` | 用返回成败的发送方法，拿到消息 id 才写 `dispatched_at`；失败的在每次拉取开始时补投，不限回看窗口与次数；Python 按会议去重 | J2「投递与补投」；设计 9.3.1、第八章 #30 |
| Q7 | Fireflies Management 菜单配置 | 管理后台手工配置，只挂给 PGM / SA 的角色（同 ERL），不写迁移 | 1.4；设计第八章 #32 |
| Q8 | Play candidate 的含义 | 开关：只标记本条为 playbook 候选（由另一任务处理，不是 Goldie 召回的 Playbook 手册），不影响授权、投影与召回；存 P7 `in_playbook`，证词打在署名行 | P7；设计 9.11.6、第十章 #62 |
| Q9 | 摘要与 KB 正文的授权行 | P7 加 `output_type`、不设 `summary` 列，摘要行与正文行在中间表各占一行；投影与登记见 #Q42，勾选联动见 #Q55 | P7、X1；设计 9.6.2、9.6.6、第八章 #4 / #11 |
| Q10 | 提取后 Authorize 初值 | 跨公司一律不勾、要管理员审核（会议因此 Pending · 待审核）；证词按邮箱认出发言人的两版默认勾，经 P8 认出的不勾；人工 Start Extraction 同此（#Q81） | P7；设计 9.6.4、9.9.5 |
| Q11 | 重投时会议仍在识别 / 提取中 | 重投（接收次数 ≥ 2）即直接接手从头重跑；凭 `processing_started_at` 条件更新，老进程落库时核对不上即放弃；首次收到却已有状态行的是 Java 重复发送，删掉 | P1；设计第八章 #30 |
| Q12 | 卡死兜底 | 由卡死任务清扫功能处理（单独功能，与本功能一起上线）：死信 / 过期的首轮会议、已投递无状态行的会议、非首轮提取与证词补抽卡在 `RUNNING` 的超时；本功能不做读时判断 | P1「卡死兜底」、P2；[卡死任务清扫开发设计](../../卡死任务清扫/开发设计/dev-design-doc.md) 第 4 节；设计 1.10、第八章 #30 |
| Q13 | 首轮没跑完的产出与会议 | 没跑完的产出全部作废；首轮每次开跑先删本场产出、从头跑；首轮跑完才进 Summary Records（Passed / Pending）。连续 3 次没跑完的由定时清扫按失败收尾、转 Pending：卡在提取中按 6.11 作废，卡在识别中不调大模型补完、按识别失败计（清扫开发设计 4.1）。大模型最终失败不在此列（设计 6.11） | P1「卡死兜底」；J2；设计 1.10、9.5.9、第八章 #30；提示词 6.11 |
| Q14 | 管理端入口 | 头像下拉（同 ERL 的 `menuRight_SuperAdmin`），菜单 path `/fireflies` | 第 2 节「入口与守卫」；设计第八章 #32 |
| Q15 | 公司端入口 | 也放头像下拉，在订阅条件之外（该条件只管 Profile 与菜单项）；所有公司端用户都显示，无受邀会议的看到空列表；只有 Raw Data Tab | 第 2 节「入口与守卫」；设计 9.3.6、第八章 #28、第十章 #90 |
| Q16 | Goldie Base 路由 | `/askGoldie/goldieBase?tab=…`，门户布局判定与顶栏高亮不用改；旧 `/knowledgeBase`、`/memorySettings` 重定向到对应 Tab | PG-05；设计 9.11.1 |
| Q17 | 管理端切换租户与组织 id 校验 | 组织树根下有子组织才显示下拉（同 ERL），默认会话租户；SA 可借此切到子租户；后端信任前端传入的组织 id，PGM / SA 角色照常校验 | 第 2、3 节；设计 9.1、第十章 #69 |
| Q18 | Java 包结构与路径命名 | `web/fireflies/` 分 DDD 四层、路径 kebab-case 复数 | 第 3 节 |
| Q19 | 会议页弹框增删专长标签 | 前端直调 Java API-13 / 14（带会议所属租户），不经 Python，与 Cheat Sheet 页同一组件；名册写入见 #Q44 | J5、API-13 / 14；设计第八章 #31 |
| Q20 | Raw Data 筛选与排序 | 关键词 + 日期区间 + 参会人多选 + 有效性筛选 + 列头排序，服务端过滤后分页；筛选状态存会话、返回时恢复（时机见 #Q67） | API-15 / 16；设计 9.3.3 |
| Q21 | Ask Goldie 对话展示 Fireflies 来源链接 | 不做：召回照改，对话页面不改 | 第 2 节 |
| Q22 | 合并的接口 | 会议详情一次取回弹框预填、专家建议标签与矩阵；Summary Records 列表带红点数；行内 Save 清洗预览与落库合一；两个新 Tab 共用列表接口；Play candidate 一个改标记接口；Email Domain 整份提交；专家确认框不「打开即消解」，打开前已入册或已在拒绝名单的标签在同步时落库 | 第 3 节；P5；设计 9.5.6、9.5.10、9.7.7、第八章 #20 / #26、第十章 #63 |
| Q23 | Goldie Base 新 Tab 的会议冗余列 | P7 冗余 `meeting_started_at`、`meeting_title`（投递后不变），用于日期筛选、会议名称匹配与卡片上的会议标题和时间，不参与排序（见 #Q73）；会议类型、`fireflies_id` 分页后批量查 P1，不跨表 JOIN | P7、V034、API-30；设计第八章 #20、9.11.4、9.11.5 |
| Q24 | 设计稿与设计文档不一致的 4 处 | a. Knowledge Base 搜索只按文件名，不加 Source 筛选（Source 列照加）；b. Memory Settings 管理端 File Scope 加 Fireflies Memory（只看会议摘要），不加 Document Summary，公司端不加筛选；会议摘要标签为 Fireflies Memory + Meeting Summary，Fireflies Memory 占层徽标位置；c. 由 #Q45 取代；d. Role 为 LP / Strategic Partner / Exit Partner 时 Expertise tags 必填，Founder 选填，只在前端校验 | API-33、API-37、API-28；设计 9.5.6、9.7.4、9.11.2、9.11.3、第十章 #46 / #58 |
| Q25 | 设计稿与设计文档不一致的另 6 处 | a. Knowledge Base 的 Fireflies 行 From Chat 与 Uploaded By 显示 `—`；b. Expert Testimony 搜索另匹配说话人姓名；c. Memory Settings 搜索保持现有（摘要全文与文件名）；d. Summary Records 状态筛选只有 All statuses / Passed / Pending，列表与详情页不显示 Pending 原因（跨公司审核提示见 #Q78）；e. 改为 Unknown 后 Confirm & Apply 激活（这是把会议打回 Pending 的唯一入口），只在提取或证词补抽进行中（含排队，#Q86）置灰；f. 日期时间固定 UTC 显示，会议日期按 UTC 自然日；现有 Knowledge Base、Memory Settings 日期列保持原格式 | API-20 / 23 / 30 / 33 / 34、第 4、5 节；设计 9.3.3、9.4.1、9.5.9、9.11.2、9.11.5 |
| Q26 | 跨公司与证词的出处时间点 | 由 #Q74 取代：矩阵不显示出处时间点，证词来源行带会议开始时间 | API-21、5.6；设计 3.4、9.6.6 |
| Q27 | 改判 GS 内部 / GS → Partner 后补跑 P1 新认出的公司 | 新出现的 `high` 公司（本场 P4 原本没有）直接采纳、计入本次提取，产出按公司分行的 1b，勾选初值按 #Q81，Confirm & Apply 后才上线（只到管理端）；已有行只更新提及、不改采纳与依据，管理员去掉过的不复活；非 `high` 只记候选 | `rerun_company_mentions`、API-22；P4；设计 9.5.9、提示词 6.11 |
| Q28 | 在营公司的状态口径 | 在营 = Needs Intervention(2) / Needs Guidance(3) / Thriving(4) / Achieving(5)（需求的 Active 即 Achieving）；Exited(1) / Shut down(6) / Off journey(7) 不在营；状态为空按 Thriving（同 `Invite.getCompanyStatus()`） | 识别 ②、P1 反推、API-22、API-32、自动路由；设计 2.1 |
| Q29 | 原文页支持浏览器 Ctrl+F | 不用虚拟滚动、逐行渲染；首批显示后前端在后台连续取完全篇（API-18 每批 500 句），底部显示加载提示，某批失败即停并显示 Retry | PG-03、API-18；设计 9.3.5 |
| Q30 | 投影卡在 `PENDING` 的行 | 由定时清扫（#Q12）接手：`projection_status = PENDING` 且 `updated_at` 超过卡死时限的行（含摘要行「只替换摘要」）按该行当前状态重推（已授权未删且会议 `Passed` 的上线，否则下线，#Q88） | P1「卡死兜底」⑤；卡死任务清扫开发设计第 4 节 |
| Q31 | 识别与提取的模型与输入上限 | P1、P8 与 P2~P7（含摘要压缩、实体改写、在途交易核查）都用 sonnet（temperature 0）；输入不设上限，超出上下文时按调用失败走重试与最终失败 | 提示词 6.11 |
| Q32 | Goldie Base 管理端的租户 | 管理端一律传组织树首个叶子组织 id（Knowledge Base、Memory、两个新 Tab）；后端信任传入值，没传回退会话租户（同 #Q17）；角色校验照旧；API-32 只按会议取 | 第 3 节「租户」、API-30~37、4.9；设计 9.1、9.11.1 |
| Q33 | 每日拉取时段 | 每日 03:40 UTC（`cron(40 3 * * ? *)`） | `FixedScheduleTypeEnum.FirefliesDailyPull`；1.4 |
| Q34 | 删除组织后的 Fireflies 数据 | 不处理，Java 与 Python 数据都留着；每日拉取跳过组织已不存在的租户（`getOrganizationById` 为空即跳过、记 WARN）；Sync now 选不到已删组织 | `FfSyncServiceImpl.pullDailyForAllTenants`；J1 |
| Q35 | 证词补抽的标签比对 | P2 `testimony_tags`（JSONB，上次为此人抽证词所用的标签）在首次提取与补抽成功时写入；比对以 #Q87 ② 为准：补抽执行时与它比，相同不补，不同按当前全部标签整块重抽，标签清空软删他的证词行并写 `[]` | P2、V034；设计 2.5 |
| Q36 | 跨端读表的数据库授权 | 不另授权：两端用同一套数据库账号，不按列授权 | 1.4、1.5 |
| Q41 | 投影产物的形态 | 纯文本条目 + 合成 `file_id`：`ai_rag_entry` 用 TEXT 来源，`content_text` 存生成的 markdown；每次投影生成合成 `file_id`，写进条目、切片、登记行与 P7，不对应 Java `files` 行与 S3 对象，按文件圈定召回与三方关联照旧走它；不调 API-40，Java 不设 `FileBusinessTypeEnum.FIREFLIES`，不依赖 `LGPI_BEARER_TOKEN`；API-35 对 Fireflies 行现生成 md，返回 `data = {url: null, fileName, content}` | P7、X1、API-35；设计 1.6、2.4、第八章 #1 / #5 / #16、9.11.2 |
| Q42 | 摘要的投影 | 每个知识库（去向, 公司）只投 1 条 TEXT 条目：`content_text` 放正文，`summary` 列放摘要（摘要行已授权时写，否则为空）；中间表摘要行、正文行各自编辑，共用条目的 `ai_rag_entry_id` / `file_id`。**摘要跟着正文走**：正文未授权或已删时条目不上线、摘要授权不生效，API-23 按正文为准（#Q55）。**摘要向量**：整段建一条 `chunk_kind=summary` 向量，用我方摘要、不调系统摘要器，为空不建。**只改摘要**：正文在线时改摘要内容或授权，只替换 `summary` 列与摘要向量。**登记三值**：`business_type` 为 `FIREFLIES`（正文 + 摘要）/ `FIREFLIES_TESTIMONY` / `FIREFLIES_CROSS_COMPANY`；Knowledge Base Tab 只取 `FIREFLIES`，Memory Tab 取 `KNOWLEDGE_BASE` 与摘要非空的 `FIREFLIES`。**重试**：RAG 管理端重试 Fireflies 条目跳过系统摘要器、按原摘要重建摘要向量。已知：不能只给 Memory 页摘要、不给知识库正文 | P7、X1、API-21 / 23 / 24 / 33 / 36 / 37；设计 2.4、9.6.2~9.6.4、9.11.2、9.11.3、第十章 #19 / #38；提示词 6.5、6.12 |
| Q43 | 新列表的分页样式 | Goldie Base 两个新 Tab 与 Summary Records、Cheat Sheet、Raw Data 对齐 Knowledge Base：默认每页 10 条，可选 10 / 20 / 50，常显 `${start} - ${end} of ${total} items`；手机端隐藏条数选择、用小号 | 4.2~4.9、5.2~5.8；设计 9.3.3、9.4.1、9.7.3、9.11.2~9.11.5 |
| Q44 | 会议页回写 Cheat Sheet；PG-02b From 预填版本起始日 | 不逐版本写副本。T1 = 提取时 P2 的 `cheat_sheet_id` + `expertise_tags`，建议标签 = 大模型标签 − T1 − 拒绝名单；弹框预填 T2 = 会议日期当天生效的记录（9.7.2）。保存由前端直调 Java（专家确认框 → API-08，Edit external party → API-07），每次追加一条完整记录、旧行不改；有效期必须包含会议日期（Java 拦截），已在册的预填 T2 原有效期，新登记默认 From = 会议日期、To 空；只有已在册者的 Name 只读；本场邮箱锁定（可加别的邮箱；T2 里没有本场邮箱的——按姓名回退认出或按邮箱认到名册已有的人（#Q49）——打开时自动补进并锁定）。不保存关窗什么都不写；保存关窗后前端调 Python 同步（API-28），按库里现状算、可重复调用，首轮未完、提取进行中返回 40901，前端此时把 Save 置灰；证词补抽在同步时按 #Q83 / #Q87 排；组织变化不自动重新匹配公司（9.9.2）。已知（不提示）：新记录与别的版本区间重合时写入最晚的覆盖；标签可能从早于会议日期的那天生效；改动可能进不了更新的版本 | P2、P5、J4、API-06 / 07 / 08 / 21 / 25 / 28、4.7；设计 2.5、9.5.5~9.5.9、9.7.1、第十章 #63；提示词 6.8 |
| Q45 | 专家确认框同意 / 驳回建议标签；拒绝名单 | 建议标签预填进 Expertise tags（已在拒绝名单的不预填），留下 = 同意、删掉 = 驳回，不设逐标签按钮；Java 在 API-08 同一事务写驳回 = 本次建议标签 − 保存后的 Expertise tags（Save 一律写名册，#Q51 ①）；不展示推测依据（#Q82）；未入册者新建前弹 Confirm submission。拒绝名单为 Java 表 J6 `ff_expert_rejection`（不设 P6；`timestamptz`，建表在 V1），Java 写、Python 只读（识别前过滤、同步时判已驳回），查询按人展开 | J6、P5、API-08、API-21 `resolvedAs`、4.7；设计 9.5.6、9.5.8、9.5.10、第八章 #15 / #26；提示词 6.10~6.12 |
| Q46 | 名册重名处理 | 租户内姓名唯一（忽略大小写）；新建时重名不拒绝、不合并，自动加后缀：从 1 起取第一个未占用编号（Tom → Tom1 → Tom2）。姓名失焦时前端调 Java API-41 查重，重名在姓名下方提示「A Cheat Sheet entry with this name already exists. It will be saved as Tom1.」；保存时 Java 按同一规则再算、以保存时为准并返回最终姓名。Cheat Sheet 页 Add（PG-01c1）、Create new person（PG-02a）、专家确认框（PG-02c）三处统一。已知：同一人换了邮箱、登记时又没填他在册的邮箱（#Q49）会被建成 Tom1，历史分在两个条目、无合并功能，由管理员在 Cheat Sheet 页维护 | J4 `name`、API-06、API-08、API-25、API-41、3.4、3.6、4.4、4.7、5.4、5.6；设计 9.5.5、9.5.7、9.7.1、9.7.4、第十章 #77 |
| Q47 | LG 平台用户在名册有记录时角色以谁为准 | 以名册为准：专家确认框里平台用户的 Role 可改（只有 Name 只读）；平台用户有会议当天生效的名册记录时，角色以该记录为准、优先于平台账号推出的角色，API-28 同步也按它刷新；改离 Founder 后不再按平台账号挂到被投公司。API-28 同步时平台用户的公司：仍是 Founder 的不动（含为空），保持识别时记下的公司；从别的角色改回 Founder 才按识别 ② 补上（只认在营公司）；改离 Founder 摘掉。不论记录从哪个入口建（专家确认或 Cheat Sheet 页 Add）都如此；名册里是 LP / Partner 的平台用户不判成 Founder（设计第十章 #74 ① 按此） | P2 `role`、识别 ②、API-28、3.6、4.7；设计 1.9、1.11、2.1、9.5.5~9.5.7、9.7.1、第十章 #13 / #74；提示词 6.11 |
| Q48 | Confirm & Apply 的拦截与「类型不符」确认 | 3 条硬拦截：参会人改了未重提、有未处理建议标签、GS → 创始人多于一家公司。1 条需确认、不硬拦：按当前参会人重跑类型判定，结果与当前类型不同（`TYPE_MISMATCH`，带 `suggestedType`）。服务端在 API-23 重算，有提示且请求未带 `confirmWarnings=true` 时返回 40903、`data.warnings` 列出，前端二次确认后带 `confirmWarnings=true` 重提；改为 `Unknown` 应用时不做这条。应用时不重读最新 Cheat Sheet（会议用自己的快照）；不校验 Founder 与关联公司（公司已在 Start Extraction 时定），`FOUNDER_COMPANY_MISMATCH` 只作 API-21 的待识别子原因 | API-23、3.4、3.6、4.6、5.6；设计 9.6.5 |
| Q49 | 会议页登记时认出名册已有的人 | Create new person（API-25）按邮箱认人：先判 LG 平台用户；再看填的邮箱（忽略大小写，任一命中即算）是否在名册某条记录会议当天生效的版本里——在就不新建，把本场参会人 / 说话人绑到那条记录、按它刷新识别结果，名册不改、表单其余内容不写入，返回 `registryMatchedName`，前端提示「已按名册中的 X 识别，未新建」，之后要改点胶囊走 Edit external party；邮箱在名册里、但会议当天生效的记录里没有它，或分属两条记录，拦截（42200，提示先到 Cheat Sheet 调整）；都不是才新建。换邮箱来开会的人认上后，打开 Edit external party 时本场邮箱自动补进并锁定，保存即写进名册。从名册选人见 #Q53。其余写名册的入口只拦截、不认人：Cheat Sheet 页 Add（API-06）、专家确认框（API-08）、Cheat Sheet 页与会议页的编辑（API-07），填的邮箱已登记在名册别的条目（任一版本；编辑时不含本条目）时拒绝，提示登记在谁名下。未挂条目但本场邮箱已在名册的参会人按已在册展示（#Q51 ⑤） | API-25、API-06、API-08、API-21 `registryForm`、3.4、3.6、4.4、4.7；设计 1.9、9.5.5、9.5.7、9.5.9、9.7.4、第十章 #77 |
| Q50 | 提取时何时补跑 P1、证词勾选、知识库行的 Portfolio 关联 | ① Start Extraction 只在类型被改成 GS 内部 / GS → Partner（与上次成功提取的类型比；从未成功提取过的按改了算）或首轮 P1 最终失败时补跑 P1，其余沿用已有提及结果（提示词 6.11）② 由 #Q81 取代：重新提取不沿用旧勾选，按首次提取的默认勾选 ③ Goldie Base 知识库列表 Fireflies 行的公司所属 Portfolio 只认 Active（`status = 0`）关联，同普通文件 | P7 `authorized`、3.6 API-33；设计 9.5.9、9.6.4、9.6.6、9.9.2、9.9.5、第八章 #16；提示词 6.4、6.11、6.12 |
| Q51 | 专家确认框保存、名册同步与应用时校验 | ① **专家确认框（PG-02c）Save 一律写 Cheat Sheet**：未登记的新建（必填校验、重名加后缀、邮箱查重、有效期含会议日期，新建前弹 Confirm submission），已登记的追加一条完整新版本（与 T2 相比没改动不写）；标签栏为空也照建 / 照追加；驳回 = 本次建议标签 − 保存后的 Expertise tags。API-08 的 `entry` 必填。LG 平台用户同样建条目（姓名取账号姓名只读、角色预填 Founder 可改，#Q47）② **关窗后名册同步（API-28）把名单带回本场**：按会议日期生效的名册记录刷新 P2；P5 建议标签落成已同意 / 已驳回；按 9.9.1 算 `participantsChanged`，角色变了给 `suggestedType`；标签变了的专家按 #Q87 排证词补抽。响应为 `{participantsChanged, suggestedType?, updatedAt}`。40901 只在首轮未完、提取进行中时返回；PG-02b / PG-02c 的 Save 因首轮未完、提取进行中、页面上别的写请求在途而置灰，证词补抽进行中不置灰。新登记时拿不到 `cheatSheetName`（如上次同步失败后重开）时，按本场邮箱找会议当天生效的记录挂上 ③ **Confirm & Apply（API-23）统一校验**：3 条硬拦与 #Q48 需确认的提示；提取或补抽进行中拒绝（#Q25e）；应用时不补证词（#Q87）④ **Cheat Sheet 列表与编辑弹框标出 LG 用户**：不加表字段，Java 在 API-05 列表行（编辑弹框用同一行数据）现算 `lgUser`——按该条目当前那一版的邮箱匹配本租户 LG 账号（同识别 ② 口径：本租户管理端用户、本租户公司的公司端用户，忽略大小写），命中即 true；前端在姓名旁显示「LG user」。名册里可以有 LG 用户 ⑤ **已在名册、本场还没挂上的人按已在册处理**：参会人未挂名册条目（P2 无 `cheat_sheet_name`）但本场邮箱在名册某条记录会议当天生效的版本里时，API-21 现算按已在册展示：`registryState = REGISTERED`、`registryForm` 预填那条记录（T2）并给 `versionId`、`clickAction` 按已在册定；专家确认框 / Edit external party 保存在那条记录上追加（没改动不写），关窗后同步（API-28）按本场邮箱挂上。邮箱在名册里但当天生效的版本里没有它时，保存被邮箱查重拦下、提示先到 Cheat Sheet 调整 ⑥ 已取消（#Q87）。已知：只想驳回、不想登记的未入册者也要填齐必填项进名册；LG 平台用户全部驳回也会建一条 Founder 记录（按 #Q47，以后会议角色以记录为准） | 0、J6、P1 `current_extraction_input` / 「不设草稿」、P2 `expertise_tags` / `testimony_backfill_status`、P8 `triggered_by`、2 PG-01c / PG-02c、3.1 API-05 / 08、3.2 API-21 / 23 / 28、3.4~3.6、4.4、4.6、4.7、5.4、5.6、7 #Q44 / #Q45 / #Q49；设计 2.5、9.5.5~9.5.8、9.6.4、9.6.5、9.7.1、9.7.3、9.7.4、第十章 #13；API-21 `registryState` / `registryForm`（⑤） |
| Q52 | 「本租户的人和公司」含不含下级节点（设计第十章 #95） | 含全部下级节点，父节点不含。① Python：`organization` 只读映射补 `pid`；organization 仓储加「本节点及全部下级」「这些节点及全部上级」两个单表递归查询（UNION 去重，机构树成环也会停；Java 复用的 `findByTreeInId` 是 UNION ALL，成环会一直递归，同平台其他用处）；两张关联表仓储按多个节点查，由 service 先取节点再查。以下都取本租户及全部下级：识别 ②③ 的管理端用户与公司、P1 候选公司（首轮与改判后补跑）、API-32 公司候选、API-20 关键词按公司名搜、API-22 / API-23 校验所选公司属本租户、内容清洗的机构名（下级节点名称也当本机构名）、人名与公司名；自动路由按公司挂的节点补上各级父节点逐个处理 ② Java：API-05 `lgUser` 的 `findTenantAccountEmails` 用 `OrganizationRepository.findByTreeInId`（本节点 + 全部下级）取管理端关联与公司 ③ 公司端看原文（API-15 / 16 / 17 / 18 与 API-33 的原文跳转）：会议所属租户在「会话机构及其全部上级」里（Java `OrganizationService.findSelfAndAncestorIds`，向上递归、UNION 去重；Python `organization_repository.list_with_ancestor_ids`）且本人邮箱在 `participants` 中即可看，不加公司匹配 ④ 不变：Portfolio（`company_group`，`firm_profile` 基金清单与 API-32 Portfolio 下拉）、GS 域名、名册、空间与数据的租户键、页面切换租户、管理端权限、知识库召回范围（代价见设计 #95） | 1.4、3.1 API-05 / 15 / 17、3.2 API-32、3.3 API-33、3.5 公司增改链路、3.6 自动路由消息与 API-05 `lgUser`；设计 1.1、1.9 ②③、9.3.6、9.5.3、9.7、第八章 #24 / #27 / #28、第十章 #69 / #95 |
| Q53 | 未识别参会人 / 未对上说话人关联名册；发言人自动挂的条件 | ① 下拉两项：`Create new person`（PG-02a）/ `Link existing person`（#Q56）② 关联 = 选人弹框（搜索沿用 API-05 关键字，单选，会议当天没有生效版本的人置灰）+ 复用 Edit external party 弹框：预填此人会议当天生效的那一版，Name 只读，本场邮箱自动补进并锁定，其余可改；保存走 API-07 写名册（以后按邮箱直接认出），再走 API-28 按姓名把本场参会人挂到该条目。Java 只给 API-05 加「按会议日期取生效版本」，Python 不新增接口 ③ 被关联的人在本场已有另一位参会人时，仍是两位参会人、身份相同、同名显示，不合并 ④ 发言人按姓名对邮箱前缀自动挂（设计 1.9）：对上多个邮箱时，只有它们对应名册里同一个人才挂到第一个；同为 GS 人员、同一家公司不自动挂，交 P8，拿不准即为未对上的说话人；已挂上的发言人没有改挂入口。名册同一人的比较不看其中一位是不是平台账号 ⑤ 关联或登记保存成功后，对本场还没挂上的说话人按 ④ 再判一次、满足即挂上（已挂上的不动）。不做自动合并参会人、「可能是同一人」提示 | 2 PG-02、3.1 API-05、3.6 API-25 / API-28、4.6、5.6；设计 1.9、9.5.5、9.5.7、9.5.9、第十章 #77 / #92 |
| Q54 | 防过期提交（P1 `updated_at` 乐观锁）的提示方式 | 保留防过期提交，用页面顶部错误提示条：`This page is out of date. Refresh the page.`，不弹框、不自动刷新、不清页面草稿；发起写操作的弹框（PG-02a / e / f）收到 40900 仍先关掉；40900 的 `message` 前端不显示。已知：别人改了本场任何内容后，自己页面上不相干的写入也会被拒，刷新后未保存的编辑与勾选要重做 | 4 通用约定、3.6 错误码 `40900`、P1「防过期提交」；设计 9.6.5「并发」；web `review/utils/writeError.ts` |
| Q55 | 正文与摘要的 Authorize 联动 | 同一（去向, 公司）的正文与摘要当成一个勾选框：勾选或取消任一个，另一个随之变；只在正文行已删时摘要置灰。不支持只放行正文、不放行摘要。后端 API-23 仍按「摘要授权而正文未授权按正文为准」归一 | 4.6 Authorize、5.6、X1「摘要跟着正文走」、P7；设计 9.6.2；web `review/utils/routingMatrix.ts` |
| Q56 | 未对上的说话人怎么挂到已有参会人 | 下拉没有 `Assign to a participant`（无 PG-02d、API-27），与未识别参会人一致只有 `Create new person` / `Link existing person`。要把说话人挂到本场已有参会人名下，走 `Create new person` 填那位参会人的邮箱——API-25 按邮箱认出本场已有参会人（平台用户、名册已有的人都不新建），直接挂上；那位参会人既非平台用户、也不在名册时，等于先登记进名册再挂说话人（Name 预填的是说话人显示名，要改成本人姓名）；一位参会人可挂多个说话人。P3 `bind_source` 无 `MANUAL_ASSIGN`（存量由 V035 并入 `MANUAL_CHEAT_SHEET`）；API-21 `aiSuggestedMatch` 仍返回，页面不使用。已知：要多填一张登记表单；说话人查不到邮箱时只能填本场某位参会人的邮箱、挂到他名下 | 2 PG-02、3.2、3.4、3.6、4.6、4.7、5.6、P3 `bind_source`；设计 1.9、9.5.5、9.5.9、9.7.4、9.9.1、9.10.2、第十章 #66；提示词 6.13；web `review/components/ParticipantChips.tsx`；Python `participant_service.py` |
| Q57 | 公司端 Goldie Base 的两个新 Tab | 公司端也显示 Cross company content、Expert Testimony，内容与公司端在 Goldie 召回到的一致：跨公司只有正文；证词列匿名版的行，只有正文与专长标签。API-30 对公司端调用者不返回会议名称与元数据、说话人姓名、Play candidate（`meeting`、`speakerName` 为 null，`inPlaybook` 恒 false），不靠前端隐藏。公司端所有用户可见；租户只认会话机构、不采信前端传入的组织，没有机构时返回空页；不调 Java；关键词只匹配正文；不提供时间过滤、接口忽略公司端传入的日期（逐日收窄能反推会议日期、进而认出匿名证词的说话人）；一行一张卡片：跨公司一场会一张、证词一人一张（#Q77）。管理端 Tab 看署名行的授权，公司端看匿名行的授权；管理端两个 Tab 不变。`idx_ai_ff_routing_row_tab` 谓词含 `TESTIMONY_ANON`（V035，发版前后执行均可）。API-31 对公司端仍拒绝 | 2 PG-05c / PG-05d、3 API-30、4.9、5.8、P7 索引；设计 9.11、9.11.1、9.11.4、9.11.5、第十章 #41；Python `goldie_base_service.py`、`routing_row_repository.py`、`business/V035`、`source/rag/ROLE_VISIBILITY.md` §8；web `askGoldie/goldieBase/` |
| Q58 | `Disconnected` 的连续失败次数 | 写死为 3：`FfSyncServiceImpl` 常量 `DISCONNECT_THRESHOLD = 3`，`FfSyncProperties` 不设 `disconnectThreshold`；Nacos 里多余的 `cio.fireflies.sync.disconnect-threshold` 键被忽略 | 1.4；设计 9.2.4 |
| Q59 | 公司端普通用户只看本人受邀会议的 Memory 与 KB | 公司端普通用户只看本人受邀的会议，公司管理员仍看本公司全部，管理端不变；跨公司内容与证词匿名版不动。「受邀」= 本人邮箱在 `ff_meeting_meta_info.participants` 里（忽略大小写），同 Raw Data 与原文页；只圈本公司 `KB_APP` 去向、在线的行，不比对会话机构。清单查询时现算（fireflies `list_invited_kb_file_ids`，返回与登记行、条目、切片共用的 `file_id`），不加字段，四处共用：① Goldie 召回：行级过滤为「创建人是本人，或 `file_id` 在清单里」② `find_files` / `get_file_summary`：会议文件只取清单里的 ③ Knowledge Base 页（API-33）：会议行只列清单里的 ④ 下载（API-35）：本人没受邀按不存在处理（404）。邮箱取 Java 当前用户（聊天取每轮开头存下的用户快照），取不到即看不到任何会议内容。普通用户没有 Memory Settings 页，摘要只在 Goldie 里召回 | 3.3 API-33 / API-35、3.6；设计 1.3、第八章 #10~#12；Python `goldie_base_service.py`、`chunk_repository.py`、`file_registry_repository.py`、`knowledge_base_tool.py`、`source/rag/ROLE_VISIBILITY.md` §8 |
| Q60 | 参会人胶囊不显示 `Expert` 徽标 | API-21 `badges` 不返回 `EXPERT`，只有 `Possible expert`（本场有未处理的建议标签）与 `AI inferred`；前端不渲染没有文案的徽标。名册里的专长标签照常用于补充识别、证词与建议标签扣除 | 3.6 API-21；5.6；设计 9.5.5 徽标表、9.5.6 |
| Q61 | 同一人以多个邮箱受邀的合并显示 | **暂缓**，未开发（Python + Web 估算约 1000 行，重启时先定范围）。现状：一个邮箱一位参会人，同一人的多个邮箱会一个被认出、另一个 Unidentified，说话人同时对上两个前缀也不挂（#Q53 ④），会议可能卡在待识别。曾拟方案要点：只合并显示、不合并数据；以说话人为锚按邮箱前缀归组，P2 加 `same_person_as` 指向主邮箱行；组内邮箱不全是名册同一人时留在待识别（卡点 `SAME_PERSON_TO_CONFIRM`）；页面一组一个胶囊，下拉加 `Not the same person` 拆组。该方案第 1 步审核已改为附属行不抄主邮箱身份、按人计数与比对处一律跳过附属行，并需补主邮箱是 LG 平台用户的组的登记入口 | 设计 1.9、1.10、9.5.5、9.5.9；P2；API-21、API-25、API-28；Python `identification_service.py`、`participant_service.py`、`summary_record_service.py`、`meeting_context_service.py`；web `review/components/ParticipantChips.tsx` |
| Q62 | 跨公司与证词的实体改写 | 提取（含证词补抽）时，Cross-Company 与证词条目有实体命中的，追加一次**实体改写**调用：删去 n-gram 行与精确数值句、邮箱与网址已直接替换（交给模型会被还原成人名或机构名）之后，把替换清单实体前的文本与清单命中词（附类别）交 sonnet（temperature 0），命中词一律去掉、只改写含命中词的句子，泛称用中性说法、不猜角色、同一人前后一致，**不允许以「不是名字」为由保留**（误命中的普通词换同义说法）。改写结果同时满足才采用：再过一遍机械清洗没有任何变化、命中词按整词不分大小写查都已不在（单个词的清单条目区分大小写，只改大小写的机械清洗查不出）、不含命中词的句子原样保留、还有正文；不满足、调用最终失败或这一步意外出错，退回直接替换，不丢条目、不按调用失败处理。只有带命中的条目才调，按条并行；不读转录、不追加平台常识。矩阵编辑保存（API-24）只做机械清洗、回显给管理员。剥离清单的来源与匹配口径见设计 1.5（每场取全部来源） | 设计 1.5「命中怎么处理」、9.6.3；提示词 6.1、6.2、6.11 步骤 2 与「修订调用」；#Q31 |
| Q63 | 在途交易不进跨公司 | ① P6「具体交易」一节：出自在途交易的做法、经验与教训同样不写（去身份也不行），输出前逐条自查；不点名具体的出售安排 ② 程序**在途交易核查**：有通过校验的条目时，把整场转录与全部条目（编号、出处时间点、statement）交 sonnet（temperature 0）逐条判是否出自在途交易，判是的丢弃、记进审计丢弃清单；拿不准按在途处理，但本机构自己的基金募集不算在途交易（GS 基金募资细节由 P6 的 LP 会议附加剥离处理）。传整场转录不截窗口（交易状态可能在别处才说明、时间点可能为空）；不追加平台常识；缺编号或结论不是布尔值按输出不合法重跑；最终失败时条目照常保留、记审计，不作废整场（跨公司默认不放行，审核兜底）。四类会议都做，核查跨公司与证词（#Q65）；1a / 1b、矩阵编辑保存不核查 | 设计 1.7「在途交易隔离」；提示词 6.1、6.2、6.9「具体交易」、6.11 调用编排 / 失败处理 / 成本 / 「在途交易核查」；#Q31 |
| Q64 | 跨公司内容不替发言人补建议 | 只收紧 P6 提示词：判据「有参考价值」是决定要不要输出的门槛、不要求在 statement 里写建议；「忠于原意」加「不替发言人补建议」——原话只陈述现象、经验或判断的按原意转述，不另加原话没有的建议或结论。不加程序核查，跨公司默认不放行、靠审核兜底 | 提示词 6.9「判据」「忠于原意」与出处表 |
| Q65 | 专家证词的在途交易与补建议 | ① P5：「交易事实不进证词」包括出自进行中、尚未交割交易的做法、经验与教训（去身份也不行）；「个案不外推」的 one sale process / one deal 限已交割的交易；输出前逐条自查；不替发言人补判断、建议或结论（署名版会算在他名下）② 在途交易核查含证词：整场提取时 P5 证词与 P6 条目放进同一次核查调用；证词补抽对补抽出的证词单独核查一次；判为在途的证词丢弃、记审计（两版都不产出）；核查没跑成时证词照常按初始授权放行。核查提示词泛指「条目（跨公司内容或专家证词）」，判定口径同 #Q63 | 设计 1.7「交易事实只落 1b」、2.5 证词过滤表「交易敏感」；提示词 6.8 抽取要求与过滤出处表、6.1、6.2、6.11 调用编排 / 失败处理 / 成本 / 「在途交易核查」；#Q63 |
| Q66 | 跨公司内容的普适性 | 三类分开：① 普适规律照常 ② 只在特定行业、阶段或监管环境下成立的规律可以进，写明适用条件 ③ 个案只写从中提炼出、脱离这家公司仍能成立的教训或做法（用「可以」「可能」，不写成普遍趋势），该公司的具体做法细节、客户、数字与经过一律不写，也不用「in one case / one company」把数字带回来，提炼不出的整条不输出。P6 对应三处：「忠于原意」个案只写提炼出的教训；「战略决议闭环」写到问题类型与应对方式这一层；「有参考价值」的经验教训为提炼后什么有效、什么无效。只改提示词，不加程序核查，靠审核兜底 | 提示词 6.9「抽取类别」「判据」「忠于原意」与出处表、说明；#Q64 |
| Q67 | Summary Records 与 Raw Data 的视图记忆 | 两个 Tab 一致：搜索、类型 / 状态 / 时间筛选、页码与条数存会话，切过租户回到第 1 页，恢复的页码超出末页时落到最后一页；Summary Records 关键词也匹配会议 id，占位文字「Search by meeting ID, title or company」。何时恢复：PG-02 / 03 / 04 的面包屑与 ← Back 带 `restore=1`（进页后去掉），连同浏览器后退 / 前进，都恢复；点菜单（含已在本页时再点）、新开标签页、手输或粘贴地址、在本页刷新（F5），清空两个 Tab 存的条件（在别的页刷新后再后退回来仍恢复） | 4.2「视图记忆」、5.2；设计 9.4.1 |
| Q68 | Cheat Sheet 列表每人显示哪一版 | 每人取最后保存的那一版（`updated_at` 最晚，再按 `id`），不看生效日期与今天；History 按同一顺序倒序，列表这一行即 History 第一行。会议回溯（9.7.2）不受影响。已知：补录旧时段、从旧会议页追加的记录写入更晚，列表随之显示这条可能已结束的版本，要换回须对当前那一版有改动再保存 | API-05（含带 `meetingId` 时会议当天没有生效版本的兜底）、API-07 无改动只记复核的那一行；设计 9.7.1、9.7.6 |
| Q69 | Cheat Sheet 列表取数 | 每人挑一版在库里做（`DISTINCT ON`，先窄列挑 `id` 再取整行），`needsReview` 另用一条按人汇总的查询；筛选、排序、分页仍在内存里（本地 5,000 人 × 20 版单次约 150 ms、分配约 70 MB）。已知：挑版本的规则在 SQL 与 Service History 的 `WRITE_ORDER` 各写一份，改须两处同改；这三条查询的语义不在单测范围，靠本地造数据实测 | 3.6「API-05 取数」；Java `FfCheatSheetRepository`、`FfCheatSheetServiceImpl#list` |
| Q70 | Cheat Sheet 页编辑无改动时复核记在哪一版 | 记在弹框带入的那一版（`{id}`），不重查。复核字段只用于算 Needs review（取此人全部版本里最晚的写入或复核时间），记在哪一版结果相同。挑当前版的规则只在仓储 SQL 一处 | API-07；设计 9.7.1、9.7.5；Java `FfCheatSheetServiceImpl#markVersionReviewed` |
| Q71 | 多公司到场的 GS → 创始人会议，公司端条目的标题与文件名 | 有其他公司到场时（口径同 P2 的 `other_companies`）不用会议标题，标题与文件名固定为 `Meeting summary · <会议开始时间>`（UTC，精确到分钟，如 `Meeting summary · 2026-11-20 23.30 UTC.md`；带时刻免得同一公司同一天两场会重名，文件名不允许冒号，时分用点隔开），与跨公司、证词匿名版同理；只有一家公司参会时用会议标题。已上线的这类条目发版后对其正文行重推一次投影换成新名字。已知：这类会议的文件名看不出主题（正文 Meeting Info 里有 P2 去过名的标题） | Python `projection_service._entry_title`；提示词文档 6.11 步骤 8「条目标题与文件名」 |
| Q72 | Goldie Base 两个新 Tab 的排序 | 两端、两个 Tab 都严格逐条按知识库条目入库时间倒序（同 Memory Settings）；取数见 #Q73。日期筛选仍按会议日期，卡片上显示的仍是会议开始时间。V034 中 P7 `meeting_started_at` 列注释已去掉排序说法，已执行过 V034 的环境注释不更新，不影响功能。已知：管理端仍只把相邻的同场行合成一张卡片，同一场会的行入库先后不定，两场会同时入库时可能交错拆成多张卡片；凡重新上线的条目（改内容、投影重试、取消授权后再授权）都是新条目、单独排到最前 | 3 API-30、5.8、P7 字段与索引说明、7 #Q23；设计 9.11.4、9.11.5、9.11.6、第八章 #20；Python `goldie_base_service.list_contents`、`routing_row_model.py`、`business/V034`（列注释）、`source/rag/ROLE_VISIBILITY.md` §8；web `askGoldie/goldieBase/utils/groupByMeeting.ts` |
| Q73 | 两个新 Tab 的排序取数（P7 `projected_at`） | P7 冗余列 `projected_at`（当前在线条目的入库时间）：主行上线回写 `file_id` 时同写、取回写那一刻，下线同清，摘要行不写。两个新 Tab 在 P7 单表筛选、排序（`projected_at DESC, id DESC`）、分页与计数；`idx_ai_ff_routing_row_tab` 的排序列为 `projected_at`。加列、回填与索引在 V035：在线的存量行取登记行 `ai_file_registry.created_at`（登记行紧跟条目创建写入），执行过旧版 V035 的环境（本地、test）重跑一遍。已知：`projected_at` 比 `ai_rag_entry.created_at` 晚一次向量化的耗时，两场会在这几秒内同时投影时先后可能与按条目创建时间排的不同。Memory Settings 的同类问题不在本条范围（记在 Python 待优化项） | P7 字段与索引说明、3 API-30、迁移文件清单、code-examples 2；Python `routing_row_model.py`、`routing_row_repository.list_goldie_base_rows` / `count_goldie_base_rows`、`goldie_base_service.list_contents`、`projection_service._commit_online` / `_finish_offline`、`business/V035` |
| Q74 | 证词的时间戳 = 会议开始时间 | 两版证词的来源行后都接 ` · Meeting <YYYY-MM-DD HH:MM> UTC`（P7 `meeting_started_at` 折成 UTC），供 Goldie 作答时说出是哪场会上说的——署名版 `Source: <Organization> <Role> <Name> · Meeting …`，匿名版 `Expertise: <expertise tag> · Meeting …`，匿名版当日无专长标签时首行只剩 `Meeting …`；矩阵预览与投影用同一行。矩阵不显示出处时间点 `[hh:mm:ss]`，API-21 不返回 `sourceTimestamp`。已上线的条目不补，改内容、重新授权或重新提取后重新投影时才带上。已知：需求写「不向 Founder 展示任何来源信息」，匿名版带会议时间偏离这一条，会议时间加专长标签可能让创始人反推出说话人；公司端 Goldie Base 证词页不显示会议、不能按会议日期筛选，聊天里却能看到每条证词的会议时间 | P7 字段说明、证词发言人说明、3 API-21、5.6、#Q26；设计 3.4、6.x 标签来源、9.6.2、9.6.6、9.8.1；提示词 6.11 步骤 3、7；Python `meeting_context_service.testimony_source_line`、`projection_service._render_markdown`、`summary_record_converter`、`source/rag/ROLE_VISIBILITY.md` §8.6；web `RoutingMatrix.tsx`、`routingMatrix.ts` |
| Q75 | 只有 `Passed` 会议的内容进 RAG | `Pending`（待识别、待确认专家、待审核，不论原因）会议的行只记授权（`authorized`），不投影（`projection_status` 保持 `NONE`）；勾选只表示授权，与是否入库无关。`Confirm & Apply Routing` 转 `Passed` 时已授权的行整批投影；待识别的会议应用后仍是 `Pending`，不投影。已 `Passed` 的会议：行内 Save 重投、应用时勾选或取消，照常即时上线或下线；证词补抽见 #Q83、#Q88。会议退回 `Pending` 的路径（Start Extraction 重新提取、改 `Unknown`、证词补抽转回）都先整场下线；自动路由只处理还没提取过的待识别会议。除调用方外投影服务自己也按会议状态把关（#Q88）。提取审计 `EXTRACT` 的 `projection` 在会议 `Pending` 时记 `DEFERRED_UNTIL_PASSED`，`Passed` 时记 `REQUESTED`。已知：默认授权的内容要等管理员处理完 Pending 会议才进 Goldie。存量不主动清，行被推到时按 #Q88 下线 | P1 说明（不设草稿）、3 API-23、API-24；设计 1.10、5.4、9.4.2、9.6.3、9.6.4、9.6.5、9.9.4、9.9.5、9.11.5；提示词 6.11 步骤 1、8，6.12 初始授权的例外；Python `extraction_service`、`summary_record_service`、`projection_service._prepare_resume` |
| Q76 | 会议投影条目的标题与上传时间 | 条目标题（`ai_rag_entry.title`，即 Goldie 引用的 `source_title`）不带 `.md`；登记行文件名为标题加 `.md`（知识库页展示与下载）。rag 检索对 TEXT 来源带合成 `file_id` 的条目（只有会议投影这样建）不返回上传时间，Goldie 引用会议内容不带 `(uploaded <日期>)`（投影时间不是上传时间，公司端还会透出跨公司内容出自哪天的会）；上传的文件与 `/texts` 粘贴入库的照旧。已上线的条目要重新投影或改库后标题才不带 `.md` | 提示词 6.11 步骤 8；Python `projection_service._render_markdown` / `_create_entry`、rag `search_service._enrich` |
| Q77 | 矩阵里跨公司与证词合并成块 | **合并点**：P5 / P6 照旧逐条产出，输出校验、在途交易核查、机械清洗（含实体改写）、`EXTRACT` 审计（类别、标签、可迁移理由、出处时间点、丢弃原因）照旧逐条做；落中间表（提示词 6.11 步骤 7）时由程序拼成一行，整块一个编辑框、一个 Authorize。**粒度**：跨公司每场一行（0 条不写）；证词每位发言人每版一行，署名版、匿名版各自编辑、各自授权；来源行、P8 识别者默认不勾、补抽替换、Goldie Base 证词卡片的姓名与专长标签都按发言人；补抽出的证词同样合成此人每版一行。**正文格式**：每条一段，段首单独一行是程序加的类别标签 `**<类别>**`（跨公司为类别 key 转标题写法，如 `**Market trend**`；证词为标签名，#Q85 ⑤），下面是该条正文（提示词要求每条 1~3 句写成一段、不用列表），段间空一行；块内按出处时间点排，为空的排后。证词来源行由程序生成、只读、不进正文，投影时加在首行。不放行某一条就在编辑框里删掉那一段；行内 Save 的清洗与两步提交、Confirm & Apply 按行。**切片**：跨公司按空间默认切（800 字符）。证词按段切：正文按空行分段（只有空白的行也算空行），每段前补上来源行成一片，只有一行类别标签的段并入下一段、没有下一段就不单独成片；rag `vectorize_entry` 收调用方切好的片。已知：rag `retry_entry` 按默认切法重切、来源行只在第一片（证词条目向量化失败时投影自己删条目重试，走不到它）；管理员编辑破坏段落只改变切片粒度，来源行每片都有。**标题**：跨公司 `Cross-company insights`；证词匿名版 `Expert testimony · <专长标签>`（会议当日的标签，逗号分隔；当日没有时只写 `Expert testimony`），署名版 `<会议标题> · Expert testimony · <姓名>`。**中间表**：无 `category`、`source_timestamp`（V036，Python 发版后执行）；矩阵证词行按发言人排序。**Goldie Base**：管理端把相邻的同场行归成一张卡片（跨公司一场一项，证词每位发言人一项）；公司端一行一张卡片（跨公司一场会一张、证词一人一张）。Play candidate 按行开关。已知：公司端看得出这几条出自同一场会、同一个人。存量不处理：老会议保留逐条的行与已上线条目，重新提取或补抽后变成合并行；编辑保存老行按新规则重投影。证词与跨公司条目不能从 Knowledge Base 页下载（API-35） | P7 字段与说明、3 API-21、5.6、5.8、#Q57、#Q74、迁移清单；设计 1.3、3.4、第七章、第八章 #1、9.6.2、9.6.3、9.6.6、9.9.5、9.11.4~9.11.6、第十章 #38；提示词 6.11 步骤 3、7、8；Python `extraction_service`（落中间表合并）、`projection_service`（标题、证词切片）、rag `ingest_service.vectorize_entry` 与流水线、`summary_record_service`（排序）、`routing_row_model`、`business/V036`、`source/rag/ROLE_VISIBILITY.md` §8 |
| Q78 | Pending 会议有跨公司行时的审核提示 | Pending 会议的矩阵里有跨公司行时，Scrub Status 的 Pending 徽章后加问号图标，悬停显示「`Cross-Company content needs review.`」（白底说明框，样式同列表 Status 的悬停）。按矩阵里有没有跨公司行判断，不看 `pendingReasons`。不显示：会议不是 Pending、提取或证词补抽进行中、页头类型 / 公司或参会人有还没提取的改动、改为 Unknown。其他 Pending 情况不加提示；列表不旁注原因、不按原因筛（#Q25d） | 4.6 PG-02「加载」；设计 1.10、9.4.2、9.5.1；web `review/utils/reviewRules.ts`、`review/components/MeetingInfoCard.tsx` |
| Q79 | GS → Partner 的公司层知识库正文 | `kb_doc` 为该公司退出情况的摘要，只分两节、按此顺序：`## Exit Readiness`（退出准备的缺口、风险，以及为达退出标准定下的方向与决定，每条一行，只写是什么、要在哪个退出节点前解决、GS 定下的处理方式，不写成因、具体表现、谁提出的）→ `## Exit Process`（交易形式与所处阶段；流程节点合写一行、不压缩；每个买方一行，只写名称（带所属或经由的机构）、意向程度、报价或估值区间、附带条件，不写协调人、它的历史、它正在做的准备）。不写 `## Summary`（与同一条目的 1b 摘要重复）与 `## Action Items`；买方与报价保留（在途交易只能放本公司 1b）。GS 内部不变（Summary、各抽取重点、Action Items，节结构由各类型的抽取重点给出）；`summary`（≤150 词）不变 | 设计 1.1（类型四）、1.3、5.4；提示词文档 6.3「已定」、6.6；python `ai/prompts/fireflies/company_1b.md` |
| Q80 | GS → LP 的基金层摘要与知识库正文 | 「只写已确定事实」只适用于跨公司与证词，不适用于基金层摘要与正文：没定的事照写并写明状态（如 not final），LP 写出机构名，会上表明不宜外传的（off the record）不写。正文为组合（基金）级别摘要，只分四节、按此顺序：`## Fundraising`（基金层募资一行；每个 LP 一行：机构名、基金、金额、审批阶段与预计何时决定、附带条件）→ `## LP Concerns & Requests`（关切、要求与 LP 引用的指标；GP response 含 `Noted`，GP 答应的事连同期限写成 Committed）→ `## Fund Matters`（基金业绩、LP 结构与其他基金事项）→ `## Live Deals`（格式不变）。不写 Summary（与 1b 摘要重复）、Action Items、Open Questions；同一信息只放一处（出资前提连同具体内容只在 Fundraising，LP 的关切与它引用的指标只在 LP Concerns，某个 LP 的出资不记为 LP 结构变化）；会上没说的项省略（Live Deals 固定格式除外），不写原因与背景，摘要同样适用（不写「没有谈到在途交易」）；LP 讲的同行与市场情况不写（归证词与跨公司）。`summary`（≤150 词）不变 | 设计 1.1（类型二）、1.3；提示词文档 6.3「已定」、6.7；python `ai/prompts/fireflies/fund_1b.md` |
| Q81 | 人工 Start Extraction 的默认勾选与会议状态 | 与首次自动提取统一：知识库、摘要、证词默认勾，Cross-Company 与发言人经 P8 识别的证词不勾，不沿用上一版。点 Start Extraction 先整场撤下旧内容；提取后只要落了行，会议一律 `Pending`（待审核），整场先不投影，管理员看过矩阵点 `Confirm & Apply Routing` 才 `Passed`、勾选的整批投影；一行都没落的直接 `Passed`。证词补抽不在此列（#Q83）。这种 Pending 不加提示（问号只针对跨公司，#Q78） | 设计 1.10、9.4.2、9.6.4、9.9、9.9.5；提示词 6.11 步骤 1、7；python `fireflies/application/service/extraction_service.py`、`fireflies/domain/repository/routing_row_repository.py` |
| Q82 | 专家确认框不展示推测依据 | 确认框只留登记字段，不设「Why AI suggests these tags」推测依据区块、Registry entry 小节标题与说明文字；建议标签照旧预填进 Expertise tags（留下即同意、删掉即驳回，#Q45）。P7 的主张与依据照旧落库留痕，API-21 照旧返回，前端不展示 | 4.6 PG-02c、5.6；设计 9.5.6、9.5.10；web `review/components/ExpertConfirmModal.tsx` |
| Q83 | 证词补抽的时机与上线 | 确认即补抽：名册同步（API-28）/ 登记（API-25）保存后，按 #Q87 判定谁要补、按 #Q86 排队；名册刷新提交后再起一个短事务把快照里他的标签同步成新值、置 `testimony_backfill_status`、碰 P1（响应带这次的 `updatedAt`），响应后后台补抽证词（P5）；页面刷新后按补抽中轮询 API-21，补完矩阵即显示新证词；补抽期间 Confirm & Apply 与 Start Extraction 置灰（服务端也拒绝）。补出的证词默认勾选，都等 Confirm & Apply 才上线：会议 Pending 时等应用转 Passed（#Q75）；已 Passed 的补出新证词即转回 Pending（待审核）并整场下线（#Q88）；删光标签只撤他的证词、不转回。失败后 Retry（API-29）同此 | 3.2 API-23 / API-25 / API-28、3.6；设计 2.5、9.5.6、9.5.7、9.5.9、9.6.5、9.9.1、9.10；python `participant_service.py`、`participant_routes.py` |
| Q84 | 名册变更后已有会议怎么重跑 | ① **Pending 会议自动重跑**：Cheat Sheet 新增人员，或编辑后姓名、邮箱、机构、角色、有效期、专长标签任一有变化（新的一版与上一版比），Java 保存提交后发一条名册变更消息（带租户、此人改前改后的姓名 / 邮箱 / 有效期、来源会议）；Python 找出本租户与此人有关的 Pending 会议（待识别、待确认专家、待审核都算）：参会人邮箱对上他改前或改后的任一邮箱、参会人已挂在他名下，或没认出的参会人 / 没对上的说话人的姓名与他改前或改后的姓名一致（同识别 ⑥），且会议日期在他改前或改后的有效期内、在最近 90 天内（#Q90）（已认出、没挂名册、标签是识别时按同名名册补上的参会人不算）；排除来源会议（详情页里改名册的那场由同步处理）、管理员改成 `Unknown` 的会议（#Q89）与首轮未完、提取或补抽进行中的。消息重投不重复、不漏：相关会议清单开跑前读、逐场串行，要不要跑只在轮到某场时锁行按那一刻的状态判——识别开始或 Start Extraction 开始不早于这次保存的（已按这次改动处理过）、已不是 Pending 的，不跑也不等；正在处理（含 Passed 会议的 Start Extraction，提完转 Pending）、重跑出错、还在识别 / 参会人未写入看不出有没有关的，消息不删、等重投再跑。每场从头重跑，同首次处理：撤下在线内容，清掉识别与提取产物，重新识别再自动提取；手动定过的类型、公司以重跑结果为准，人工编辑与勾选不保留。已知：重跑中途进程被杀的那一场由清扫 F1 按首轮卡死收尾成待识别，交管理员 ② **Passed 会议不自动重跑、放开 Start Extraction**：打开详情页时按会议日期生效的名册与本场识别结果比（挂了名册的参会人的姓名、机构、角色、专长标签；按邮箱新对上名册的人），有变化即 Start Extraction 可点，页面不加提示；点击后先按名册刷新这些参会人、再整场重提（按 #Q81 提完 Pending，应用后上线） | 设计 9.9.3；API-21、API-22；java Cheat Sheet 写入与消息；python 名册变更消费、相关会议匹配与重跑 |
| Q85 | 专家证词按人、按标签抽 | ① 只有 GS → LP、GS → Partner、GS → 创始人三类会议抽专家证词（GS 内部不抽）② 每位专家只抽他名册里会议当日生效版本的全部专长标签对应的内容，类别 = 标签（预置 7 项与管理员新增的都算）；预置 7 项带定义，新增的只按名字抽，不加定义字段 ③ P5 一次调用，`testimony_speakers` 每人带自己的标签（预置的附定义）作他的可抽类别；程序按人校验，类别不在此人标签内的整条丢弃；`category` 取值为标签名；按角色的约束不变（LP 只抽市场判断、不写自己的投资，创始人只讲市场、不涉及自己公司，交易敏感与保密过滤照旧）④ P7 推测范围为此人还没有的标签（字典全部标签 − 已有 − 已拒绝），主张直接归到标签（出参无 `category`）；≥ 2 条门槛与其余判据不变，已是专家的人照样推测新标签 ⑤ 合并成块（#Q77）的段首标签即标签名 ⑥ 为某人重抽证词一律按他当前的全部标签整块重抽，他那块上的人工编辑不保留 ⑦ 标签变了的重抽触发见 #Q87 ⑧ 存量不处理，要看新效果点 Start Extraction 重提 | P2 `testimony_tags`；设计 1.11、2.5、3.4、5.6、9.8.1、9.8.3；提示词 6.8、6.10、6.11；python `extraction_service`、`fireflies_extract_agent` |
| Q86 | 同一场会多人的证词补抽排队 | 一次只补一个人，其余排队：① P2 `testimony_backfill_status` 含 `QUEUED`（该列 VARCHAR(16)、无约束）② 要为某人启动补抽时（API-28 同步、API-25 登记、API-29 Retry），本场已有人 `RUNNING` 或 `QUEUED` 即置 `QUEUED`、不起后台任务，否则置 `RUNNING` 并起后台任务 ③ 每人补抽收尾（补完、不必补跑、撤证词、失败，含代码出错置失败）的同一事务里，按进队列先后（P2 `updated_at`：排队期间他这一行又被改过的排到后面）把下一个 `QUEUED` 改成 `RUNNING`，同一后台任务接着补，排空为止；有人排队时一定有人 `RUNNING`。结果被丢弃（他已不是补抽中：只有定时清扫会这样改，排队的人一并失败）时不接 ④ 补出新证词按 #Q83 上线（已 Passed 会议转回待审核）；审计 `triggered_by` 记最后一次改他这一行的人（即把他放进队列的人，排队中又被同步刷新的换成那次的人）⑤ 凡判断「证词补抽进行中」的地方 `QUEUED` 都算：API-22 / 23 拒绝、名册变更重跑的「正在处理」（#Q84）、前端按钮置灰与轮询 API-21；API-29 在本场有补抽时排队、不拒绝；页面上排队中与补抽中同一标记，名册弹框的 `Save` 不因补抽置灰 ⑥ 定时清扫 F4：卡在 `RUNNING` 的置 `FAILED` 时，本场 `QUEUED` 的一并置 `FAILED`，各自 Retry ⑦ 触发条件见 #Q87 | P2 `testimony_backfill_status`；3.2 API-21 / 22 / 23 / 28 / 29、3.6 `40901`；设计 2.5、9.5.7、9.5.9、9.6.5；定时清扫开发设计 4.4；python `participant_service`、`extraction_service`、`summary_record_service`、`registry_change_service`、`meeting_pipeline_service`；web `reviewRules`、`dto` |
| Q87 | 专家的专长标签变了怎么重抽证词 | 只为这个人整块重抽：① 范围：所有能抽证词的专家（角色能当专家、本场发过言、会议是 GS → LP / GS → Partner / GS → 创始人）② 判定：要不要启动，按 P2 专长标签与提取快照（P1 `current_extraction_input`）里他的标签比（忽略大小写与顺序）；补抽执行时再与上次为他抽证词所用的标签（P2 `testimony_tags`）比，相同不补，不同即按他当前全部标签整块重抽（#Q85 ⑥），删掉一部分按剩下的抽，删光撤他的证词 ③ 专长标签变化对任何人都不算参会人改动；是否识别、身份与角色、Founder 的公司、说话人对到谁、参会人增减照旧算；Founder 与本场有证词的人改组织仍算，要整场 Start Extraction ④ 入口：名册同步（API-28）与登记（API-25）保存后，本场没有参会人改动、且上次提取成功时（提取作废的会议行已全部下线，要整场重提，不补），把本场所有「专长标签与快照不同、不在补抽或排队中」的专家（不只这次保存的人）的标签同步进快照、排进补抽（#Q86）；有参会人改动时谁都不补，等整场 Start Extraction；参会人改动改回去的那次保存即顺带排上 ⑤ 他的补抽在跑时又改了标签：这次不另起、快照不动，那次补完写回时发现标签与这次所用的不同，自动排到队尾按最新标签再补一次 ⑥ Confirm & Apply（API-23）应用时不补证词：④⑤ 保证本场没有参会人改动时，标签变了的专家要么已补完、要么在补或排队，而补抽进行中 Confirm & Apply 置灰 ⑦ 补出的证词按 #Q83 上线 | P1 `current_extraction_input`、P2 `expertise_tags` / `testimony_tags` / `testimony_backfill_status`；3.2 API-21 / 23 / 25 / 28；设计 1.11、2.5、9.5.7、9.5.9、9.6.5、9.9.1；python `participant_service`、`extraction_service`、`extraction_input_service`、`summary_record_service`；web `reviewRules`、`dto` |
| Q88 | 证词补抽把 `Passed` 会议转回 `Pending` 时整场下线 | ① 补抽落库的同一事务里，本场所有挂着条目的行置待下线，提交后逐行撤下 RAG 条目；行不软删，勾选（`authorized`）与内容不动 ② 管理员点 `Confirm & Apply Routing` 转 `Passed` 时，已勾选的行整批重新投影（同 #Q75）；重新投影是新条目，`projected_at` 随之刷新（Goldie Base 两个新 Tab 里这场会的内容回到最前，#Q73）③ 投影服务把关（调用方之外再把一道）：推动作时除行的状态外再看会议是否 `Passed`——非 `Passed` 会议挂着条目的行一律下线、没上线的不上线；上线回写前锁 P1 复核会议仍是 `Passed`，否则本次结果作废。定时清扫 F5 接手卡住的行时同此（非 `Passed` 会议里挂着条目的行照推下线，含仍已授权的）④ 不转回：会议本来就是 `Pending` 的补抽；已 Passed 会议删光标签或补抽没抽出新证词的，只撤他的旧证词、其余照常在线。Start Extraction、改 `Unknown`、名册变更重跑本来就整场软删下线；补抽失败后先应用、之后点 Retry 补出新证词的同样转回 `Pending`、整场下线，要再应用一次。已知：从补抽完成到管理员应用之间，这场会的全部内容在 Goldie 里查不到；应用时整场重新向量化。存量不主动清，行被推到时按此规则下线 | P7 投影动作；3.6；设计 1.10、2.5、9.9.5；卡死任务清扫开发设计 4.5；python `projection_service`、`extraction_service` |
| Q89 | 管理员改成 `Unknown` 的会议不随名册变更重跑 | ① P1 列 `unknown_by_admin`（BOOLEAN，默认 `FALSE`）：API-23 改 `Unknown` 应用时置 `TRUE`（前端只在管理员把已有类型改成 `Unknown` 时才带 `meetingType`）；API-22 Start Extraction 清回 `FALSE`；首轮接手重跑时随 P1 回到初值 ② 名册变更选会议时不选它，轮到某场锁行再判时也按「不用跑」处理，消息也不等它 ③ 名册改动不丢：管理员之后定类型点 Start Extraction，提取前按会议当天生效的名册刷新参会人（#Q84 ②）④ 存量不补标：此前已改成 `Unknown` 的会议仍会被重跑。自动路由不受影响（只处理类型为 GS → 创始人的待识别会议）。已知：重跑途中大模型失败，会议落到待识别、内容清空，消息不为它重试（同首次处理失败）；有会议卡在识别中时，本租户的名册变更消息都算要等、收 3 次进死信，直到定时清扫收尾；证词补抽失败不挡 Confirm & Apply（设计 2.5），应用后 Retry 补出新证词的按 #Q88 转回 `Pending`、整场下线 | P1 `unknown_by_admin`；3.2 API-22 / API-23；1.5 迁移 V037；设计 9.5.9、9.9.2、9.9.3；python `meeting_state_model`、`summary_record_service`、`meeting_pipeline_service`、`meeting_state_repository` |
| Q90 | 名册变更重跑与自动路由只处理最近 90 天的会议 | 两路都只处理会议日期（`started_at`）在最近 90 天内的会议（处理消息时往前推 90 天），更早的不自动重跑、不自动路由，名册变更消息也不等它：① 名册变更：与 #Q84 ① 的其余条件同时满足 ② 自动路由：候选会议（待识别、只因定不出公司的 GS → 创始人会议）同样加这一条 ③ 90 天为 Python 代码常量、两路共用，改要发版 ④ 期限外的会议照旧在列表里、由管理员处理：名册改动在点 Start Extraction 时按最新名册刷新参会人（#Q84 ②）；公司改动由管理员在详情页指定公司（设计 9.5.3）。`Passed` 会议打开时按名册判 Start Extraction 可点（#Q84 ②）不受影响 | 设计 9.9.3；3.5 消息表；python `registry_change_service`、`auto_route_service`、`meeting_state_repository` |

仍需核实（尚无结论，按现在的实现）：

| # | 问题 | 现在的实现 | 影响范围 |
|---|---|---|---|
| Q37 | 投影 markdown 里的原文链接点不点得开 | 链接取 `LGPI_BASE_URL` + `/fireflies/transcripts/{meetingId}`；`LGPI_BASE_URL` 是 Python 回调 Java 网关用的地址（`.env_example` 为 `http://localhost:9000`） | 某环境的 `LGPI_BASE_URL` 若是内网网关地址，Goldie 引用的原文链接用户打不开。需运维确认各环境的值；不是用户可访问的前端域名，就新增一个前端域名环境变量（记 env-update 与 `.env_example`） |
| Q38 | PG-01 租户下拉的默认显示 | 没切换过租户时下拉显示组织树 `nodes[0]`（同 Portfolio Companies 写法），各 Tab 不带 `organizationId`、按会话租户取数 | 多组织用户的 `nodes[0]` 不一定是会话租户：下拉显示的租户与列表数据不一致，直到手动切换一次。第 2 节「入口与守卫」与 #Q17 写的是「默认会话租户」 |
| Q39 | 公司变更通知没覆盖的入口（知会） | 按设计第八章 #27 与 3.5，只在 `CompanyServiceImpl.create` / `update`、`CommonServiceImpl.createInvitedUserAndSendEmail`、`UserServiceImpl.clientUser` / `update` 发；其中邀请的是管理端用户时不发，其余直接调 `companyRepository.save` 的入口也不发 | 经这些入口改的公司不触发自动路由，相关的待识别 GS → 创始人会议要管理员在 Summary Records 手动处理 |
| Q40 | Raw Data 的几处文案与筛选细节 | a. 日期筛选的空值标签照设计稿为 `All dates`，Summary Records 为 `All time`（5.2）；b. 没搜索、没筛选也没有会议时（如没有受邀会议的公司端用户）仍显示「No meetings match your search.」，5.5 没定无数据的文案；c. 切换租户时不清参会人筛选 | a. 两个 Tab 文案不一致；b. 空列表的提示不贴切；c. 新租户里可能没有这些参会人，列表为空，要手动 Clear filters |
