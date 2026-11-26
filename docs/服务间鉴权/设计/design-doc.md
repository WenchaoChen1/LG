# 服务间鉴权（Java ↔ Python）设计

> 关联文档: [多租户与企业级安全 · 系统架构（4-12 无用户上下文路径）](../../多租户与企业级安全/调研/system-architecture.md) | [Exit Readiness 设计](<../../Exit Readiness/设计/design-doc.md>) | [AI Chatbot 设计](../../AI-Chatbot/设计/design-doc.md)

> 状态：草案（2026-11-25）。§8 各项均已定。

## 1. 背景与目标

Java 与 Python 之间的 HTTP 调用目前全靠**当前登录用户的 token** 鉴权。定时任务、SQS 消费者、异步线程没有登录用户，也就拿不到合法凭证。

- **目标**：给"没有用户"的调用开一条有鉴权的通道，两个方向（Java → Python、Python → Java）都覆盖；有用户的调用保持不变。
- **不在范围**：
  - SQS 链路：由 AWS IAM 管控，不走 HTTP 鉴权。
  - 前端 → Python：仍用用户 token。
  - 租户隔离改造：属于多租户项目。
  - MCP：当前已屏蔽。

## 2. 现状

### 2.1 两边如何认 token

- **网关**不做鉴权，`Authorization` 原样转发给 Java web 服务。
- **Java web 服务**：
  - `JwtAuthenticationFilter` 校验三件事：签名、过期时间、Redis 里存在 `auth:token:*`。
  - 无效 token 不会直接返回 401，请求按"未登录"继续往下走。之后由 `anyRequest().authenticated()` 拒绝；带 `@AnonymousAccess` 的接口则放行。
- **Python**：
  - 全局 `AuthMiddleware` 每个请求都调 Java `/api/web/system/auth/check` 校验 token。
  - 需要身份的路由用 `get_current_user`，从 Redis 读 `auth:token:*` → `auth:user:*`。
  - 豁免路径：`/`、`/health_check`、`/actuator`，加上环境变量 `AUTH_CHECK_EXEMPT_PATHS` 里配置的前缀。
- **没有任何服务身份**：
  - Java `/oauth/token` 只支持 `password` 与 `refresh_token` 两种授权方式。
  - 没有 API key，也没有 IP 白名单。

### 2.2 现有跨服务 HTTP 调用

| 方向 | 调用 | 现在怎么鉴权 | 问题 |
|---|---|---|---|
| Java → Python | ERL 差距分析 `/api/ai/erl/gap-analysis/refresh`、`/items`（`ErlPythonClient`） | 转发用户 token；异步重算在请求线程里先捕获 token | 没有用户时调不了：Python 这两个路由依赖 `get_current_user` |
| Java → Python | 每日预测批调 `/financial_forecast/predict`（`FinancialForecastDataServiceImpl`） | **不带任何鉴权**，靠 Python 各环境配 `AUTH_CHECK_EXEMPT_PATHS=/financial_forecast` 豁免 | 每个环境都要单独配；该路径对所有能访问到 Python 的人都不设防 |
| Python → Java | 业务取数（`lgpi_api`：公司、财务、benchmark、当前用户等）、上传预签名、Fireflies 名册新建 | 转发用户 token | 无 |
| Python → Java | 后台取文件 `/storage/files/inner/getFileLinkById`（财务提取、RAG 入库、ERL 附件摘要） | Java 侧标了 `@AnonymousAccess`，**完全不鉴权**。请求头里带的是早期开发写死的 token，Java 会忽略它 | 经网关从外部也能访问，拿到 fileId 就能取下载链接 |
| Python → Java | 每个请求的 token 校验 `/api/web/system/auth/check` | 转发用户 token | 无 |

**结论**：目前还没有定时任务需要调对方的鉴权接口。本方案提前把通道建好；上表中两处不鉴权的调用留给后续任务切换（§7）。

## 3. 方案总览

### 3.1 两条通道

| | 用户通道（不变） | 服务通道（新增） |
|---|---|---|
| 适用 | 有登录用户的请求 | 定时任务、SQS 消费、异步线程等没有用户的调用 |
| 凭证 | `Authorization: Bearer <用户 JWT>` | `X-Internal-Token: <共享密钥>` |
| 身份 | 该用户 | 系统用户 `"1"`（两边已有的 `SYSTEM_USER_ID`） |
| 数据范围 | 跟着用户权限走 | 调用方显式传公司 / 组织参数，接口不从"当前用户"推断 |
| 可用接口 | 所有要求登录的接口 | 只限显式允许的接口（Java 标 `@InternalAccess`；Python 写死的名单 `SERVICE_CHANNEL_PATHS`） |

两个方向共用**同一个请求头、同一个密钥**；每一端都既要会"发"、也要会"认"。

**本任务范围**：只建服务通道机制，让两端都具备用密钥互相调用的能力。现有两处无鉴权调用的切换（`getFileLinkById` 改为校验密钥、去掉预测接口的鉴权豁免）不在本任务，已记入台账，等本迭代发布、各环境配好密钥后处理（§7）。其他接口是否开放服务通道，另开任务分析（§8）。

### 3.2 判定规则（两端一致）

1. **带了 `Authorization`**：按用户通道处理，不再看 `X-Internal-Token`。用户优先；token 无效就按无效 token 处理。
2. **没带 `Authorization`、带了 `X-Internal-Token`**：用常量时间比较与本端配置的密钥核对。
   - 一致、且该接口允许服务通道：以系统身份放行。
   - 其他情况：按未登录拒绝，响应与无效 token 相同，不暴露是密钥错了还是接口不允许。
3. **本端没配密钥**：服务通道关闭，任何 `X-Internal-Token` 都不认（默认拒绝）。

**同一接口可以同时接两种请求**：页面请求照常走用户通道，带密钥的请求走服务通道，互不影响。但两种请求下，接口内部读到的身份不同：服务调用时"当前用户"是系统用户 `"1"`，没有组织和公司。如果接口靠当前用户来圈定数据范围，服务调用过来时可能查不到数据、报错，甚至因为取不到组织而不加过滤、返回全量数据。开放这类接口前要逐个确认（见 §6「数据范围」）。

## 4. Java 端

### 4.1 接收（Python → Java）

- **新增注解 `@InternalAccess`**：标在 controller 方法上，表示该接口**额外**接受服务通道，用户访问规则不变。判定以 Spring 实际路由到的处理方法上有没有这个注解为准，所以同一路径下 HTTP 方法不同的接口、或路径更具体的同级接口，不会被连带放行。
- **新增过滤器**，放在 `JwtAuthenticationFilter` 旁边，按 §3.2 判定：
  - 通过时设置系统身份，包括 Spring Security 的认证对象和 `SecurityUtils.setCurrentUserId("1")`，审计字段自然记为 `"1"`。
- **配置**：Nacos `cio.internal-token`。改值需要重启，与现有 `@Value` 注入的配置一致。
- **首批接口（不在本任务，已记入台账）**：`getFileLinkById` 从 `@AnonymousAccess` 改为 `@InternalAccess`，访问范围从"任何人"收紧为"登录用户或服务"。
  - **不影响前端预览**（含微软 Office 在线预览）：前端用的是 `/storage/files/getFileLinkById`、`/storage/files/getPreviewLinkById`，以及列表数据里 Java 在进程内生成好的 S3 预签名链接，都不经过 `/inner/`。`/inner/getFileLinkById` 目前只有 Python 的 `query_file_link_internal` 一个调用方。

### 4.2 发出（Java → Python）

- **预测批调 `/financial_forecast/predict`**：带上密钥头，读同一个配置项 `cio.internal-token`。
- **ERL（`ErlPythonClient`）不在本任务**：照旧转发用户 token。Python 的 ERL 路由仍用 `get_current_user`，是否开放给服务通道，留给后续的接口分析任务。

### 4.3 网关拒绝内部接口（后续任务，可选）

- 不在本任务，已记入台账。它只是第二层防护：真正堵住匿名访问的是 §4.1 的改注解；登录用户本来就能通过不带 `/inner/` 的同功能接口取下载链接。它的价值在于符合规范，以及密钥泄露时多一层保险。
- 网关配置（Nacos `cioaas-gateway.yml`）在现有两条路由之前加一条规则，拒绝 `/api/web/storage/files/inner/**` 和 `/web/storage/files/inner/**`。只改配置，不改代码。
- 效果：内部接口从公网访问不到，符合 Java 规范「内部专用接口须在网关限制为内网可达」；密钥是第二道防线。
- Python 直连 Java 业务服务（§5.3），不经网关，不受这条规则影响。

## 5. Python 端

### 5.1 接收（Java → Python）

- **`AuthMiddleware`**：按 §3.2 判定。服务通道通过时，跳过向 Java 的 `check_access`。
- **允许名单**：`common/auth/access_check.py` 里写死的 `SERVICE_CHANNEL_PATHS`（完整路径、精确匹配，不放环境变量）。目前只有 `/financial_forecast/predict`。不在名单里的接口，密钥正确也按未登录拒绝。
- **路由层面**：
  - 用 `get_current_user` 的路由不变：即使以后进了名单，服务调用没有用户 token，到那里仍返回 401。
  - 需要身份、又要开放给服务通道的路由，后续任务再新增依赖 `get_caller`（`common/auth/identity.py`）：用户请求与 `get_current_user` 相同；服务调用返回 `AuthUser(user_id=SYSTEM_USER_ID)`，不带公司和组织。到时再在请求状态里标记服务调用。本任务没有这样的路由，暂不加。
- **配置**：环境变量 `INTERNAL_TOKEN`，放在 `common/config/auth.py`，并记入 `sql/migrations/env-vars/env-update.txt`。

### 5.2 发出（Python → Java）

- **`lgpi_api/_http.py`**：凭证最多带一种。
  - 传了 `auth_token`：发 Bearer。
  - 没传、且调用点声明走服务通道：发 `X-Internal-Token`。
  - 其余情况：不带任何凭证，Java 按未登录返回 401。
- **服务通道由调用点明确声明**：目前只有后台取文件（`query_file_link_internal` / `download_file_via_java`）。密钥只随这类调用发往集群内地址（§5.3），不会被带到公网那条路上。
- **删除写死的 token**：删掉 `DEFAULT_BEARER_TOKEN` 和 `LGPI_BEARER_TOKEN` 回退（早期开发遗留，生产不依赖）。
- **效果**：漏传用户 token 的调用会直接 401，不再悄悄以超管身份执行。
- **同步改文档**：`lgpi_api/CLAUDE.md` 中「双 token 契约」的描述。

### 5.3 服务通道调用走集群内网

- **原则**：带用户 token 的调用保持原路（`LGPI_BASE_URL` + `/api/web/`，经公网域名和网关），行为完全不变。每个请求的 token 校验带的也是用户 token，同样不变，`AUTH_CHECK_PATH` 不动。只有服务通道调用改走集群内直连。
- **新增环境变量 `LGPI_INNER_URL`**：Java 业务服务在集群内的地址，不配（或配成空）时默认 `http://java-business:5213`。服务通道调用直连它，路径前缀 `/web/`，不经网关、不出公网。目前只有后台取文件这一个调用。
- **默认值就是集群内地址，不回退到网关**：服务名是 `java-business` 的环境不用配。
  - 上线前先在该环境的 Python 容器里确认能连通（§7）。连不通的话，后台取文件（知识库上传与聊天附件的入库、财务提取、ERL 附件摘要）会失败，其中知识库上传和聊天里的文件问答对用户可见；其余页面请求不受影响。服务名不同的环境要显式配。
  - 本地开发解析不了 `java-business`，本地 `.env` 要配成本机 Java 业务服务的地址（如 `http://127.0.0.1:5213`），`.env_example` 给出示例。
- **`LGPI_BASE_URL` 不变**：继续用于带用户 token 的调用、token 校验，以及拼给用户点击的页面链接。

## 6. 安全约束

- **密钥**：至少 32 字节的随机串，各环境各不相同；只放在 Nacos 和部署环境变量里，不进代码库。
- **比较**：用常量时间比较（Java `MessageDigest.isEqual`，Python `secrets.compare_digest`）。
- **日志**：两端日志和 trace 都不得输出这个请求头。
  - Python `lgpi_api` 的请求日志只打印 `Authorization` 的脱敏预览，不会输出新头；服务调用时那一栏显示"(无)"，可以顺手改成"服务通道"，方便排查。
  - 网关日志只记方法、路径，不受影响。
- **Sentry**：两端的 Sentry 都会把请求头随错误事件和性能事务上报，这个头不在任何一方的默认脱敏名单里，必须自己脱敏。
  - Python：`main.py` 的 `_scrub_sensitive_headers` 加上这个头，并同时挂到错误事件和性能事务上。
  - Java：新增 `SentrySensitiveHeaderScrubber`，从两类事件里删掉 `X-Internal-Token`，顺带删掉此前一直没脱敏的 `Authorization`。
- **传输**：带密钥的调用都是集群内直连，不经网关、不出公网。Java → Python 用 `http://python:8090`；Python → Java 的服务通道调用用 `LGPI_INNER_URL`（§5.3）。内部接口另在网关拒绝（§4.3）。带用户 token 的调用不带密钥，仍走原来的公网域名和网关。
- **轮换**：两边同时改并重启。两边值不一致的那段时间里，服务通道调用会失败；目前没有用户的调用量很小。
- **数据范围**：服务身份不带公司和组织，所以允许服务通道的接口必须要求调用方显式传公司参数，缺参就拒绝（对齐多租户需求 1.4「取不到上下文时拒绝执行而非放行」）。

## 7. 上线顺序

两端都只在本端配了密钥时才发送密钥头，所以**先发版、后配密钥**。这样任何一方开始发密钥头时，对方已经带着 Sentry 脱敏上线。没有硬期限。

0. **发版前确认连通**：在该环境的 Python 容器里执行 `curl -i http://java-business:5213/web/system/auth/check`，应返回 401。Python 新版本一上线，后台取文件就直连这个地址，连不通的话 知识库上传与聊天附件的入库、财务提取、ERL 附件摘要会失败。服务名不同的环境先配好 `LGPI_INNER_URL` 再发版。
1. **两端发版，都不配密钥**：服务通道关闭（预测批仍靠豁免路径，`getFileLinkById` 仍是匿名）；Python 后台取文件改为集群内直连，其余调用不变。两端谁先谁后都可以。
2. **配密钥并重启**：各环境的 Nacos（`cio.internal-token`）和 Python 环境变量（`INTERNAL_TOKEN`）配同一个随机密钥。
3. **收尾（后续任务，已记入 Java 与 Python 台账）**：本任务到第 2 步为止。Java 需要再发一次版：
   - `getFileLinkById` 去掉 `@AnonymousAccess`、改为 `@InternalAccess`。**不能和第 1 步同一次发版**：密钥还没配时，Python 后台取文件会全部 401。
   - 网关加上拒绝 `/inner/**` 的规则（§4.3）。必须在该环境的 Python 新版本（已改为直连）上线之后，否则后台取文件会被网关挡住。
   - 各环境删掉 `AUTH_CHECK_EXEMPT_PATHS=/financial_forecast`。

本地开发时两边配同一个值即可。不配的话服务通道关闭，用户通道不受影响。

## 8. 已定与待定事项（2026-11-25）

| # | 问题 | 结论 |
|---|---|---|
| Q4 | 现有两处无鉴权调用（`getFileLinkById`、预测接口的鉴权豁免）什么时候切换到服务通道？ | **不在本任务**（2026-11-26 定）。本任务只交付两端用密钥互相调用的能力；切换记入 Java 与 Python 的待优化项台账，等本迭代发布、各环境配好密钥后处理 |
| Q3 | Python 调 Java 是否改走内网地址？Java 规范（`standards/coding.md` 安全一节）要求内部专用接口在网关限制为内网可达 | **只有服务通道调用改走内网**（目前是后台取文件）：经 `LGPI_INNER_URL` 直连业务服务（§5.3，不配时默认 `http://java-business:5213`），网关拒绝 `/inner/**`（§4.3）。带用户 token 的调用和 token 校验保持原路，行为不变（2026-11-26 定）。test 环境已实测 Python 容器能连通 `http://java-business:5213`（2026-11-25）；uat、prod 上线前各测一次 |
| Q1 | 服务通道能用哪些接口（包括第一批接入哪个场景、ERL 是否接入）？ | **不在本任务范围**。本任务只建机制（默认不开放），并迁移 `getFileLinkById` 与预测批两处现有调用；其余接口是否开放，本任务完成后另开任务分析 |
| Q2 | 两个方向共用一个密钥，还是每个方向各一个？ | **共用一个密钥** |

## 9. 未采用的方案

- **Java 签发系统 JWT（client_credentials）**：
  - 改动更多：Java 要新增一种授权方式；Python 要做 token 缓存与续期，还要在 Redis 里准备 `auth:user:1`。
  - 风险更大：系统 JWT 能通过所有只要求登录的接口，等于又造了一个超管。
- **继续用豁免路径 / 匿名端点**：本质上是不鉴权，每个环境都要单独配置，而且外部可访问。
- **IP 白名单**：集群内调用方的地址不固定，按来源地址区分不出是谁在调。
- **在公网入口（ALB）拒绝内部接口，Python 经网关的内网地址调用**：拦截规则要运维在每个环境的入口上维护，不在代码仓库里；也不是规范要求的"在网关限制"。
- **直接把 `LGPI_BASE_URL` 改成内网地址**：它同时用来拼给用户点击的页面链接，改了链接就打不开。
- **Python 调 Java 全部改走内网**（曾经做过一版）：会连带改变所有页面请求的行为——没有了公网入口的 30 秒上限，慢查询的超时与重试表现都变了，网关日志里也不再有这些调用，本地开发还要多配地址。这些都超出「让没有用户的调用有鉴权」这个目标。
