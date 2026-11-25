# 服务间鉴权（Java ↔ Python）设计

> 关联文档: [多租户与企业级安全 · 系统架构（4-12 无用户上下文路径）](../../多租户与企业级安全/调研/system-architecture.md) | [Exit Readiness 设计](<../../Exit Readiness/设计/design-doc.md>) | [AI Chatbot 设计](../../AI-Chatbot/设计/design-doc.md)

> 状态：草案（2026-11-25）。§8 待确认项未拍板。

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

**结论**：目前还没有定时任务需要调对方的鉴权接口。本方案提前把通道建好，并顺带收掉上表中两处不鉴权的调用。

## 3. 方案总览

### 3.1 两条通道

| | 用户通道（不变） | 服务通道（新增） |
|---|---|---|
| 适用 | 有登录用户的请求 | 定时任务、SQS 消费、异步线程等没有用户的调用 |
| 凭证 | `Authorization: Bearer <用户 JWT>` | `X-Internal-Token: <共享密钥>` |
| 身份 | 该用户 | 系统用户 `"1"`（两边已有的 `SYSTEM_USER_ID`） |
| 数据范围 | 跟着用户权限走 | 调用方显式传公司 / 组织参数，接口不从"当前用户"推断 |
| 可用接口 | 所有要求登录的接口 | 只限显式标注过的接口（Java `@InternalAccess`、Python `get_caller`） |

两个方向共用**同一个请求头、同一个密钥**；每一端都既要会"发"、也要会"认"。

### 3.2 判定规则（两端一致）

1. **带了 `Authorization`**：按用户通道处理，不再看 `X-Internal-Token`。用户优先；token 无效就按无效 token 处理。
2. **没带 `Authorization`、带了 `X-Internal-Token`**：用常量时间比较与本端配置的密钥核对。
   - 一致、且该接口允许服务通道：以系统身份放行。
   - 其他情况：按未登录拒绝，响应与无效 token 相同，不暴露是密钥错了还是接口不允许。
3. **本端没配密钥**：服务通道关闭，任何 `X-Internal-Token` 都不认（默认拒绝）。

## 4. Java 端

### 4.1 接收（Python → Java）

- **新增注解 `@InternalAccess`**：标在 controller 方法上，表示该接口**额外**接受服务通道，用户访问规则不变。接口路径的收集方式与现有 `@AnonymousAccess` 相同。
- **新增过滤器**，放在 `JwtAuthenticationFilter` 旁边，按 §3.2 判定：
  - 通过时设置系统身份，包括 Spring Security 的认证对象和 `SecurityUtils.setCurrentUserId("1")`，审计字段自然记为 `"1"`。
- **配置**：Nacos `cio.internal-token`。改值需要重启，与现有 `@Value` 注入的配置一致。
- **首批接口**：`getFileLinkById` 从 `@AnonymousAccess` 改为 `@InternalAccess`，访问范围从"任何人"收紧为"登录用户或服务"。

### 4.2 发出（Java → Python）

- **`ErlPythonClient`**：有用户 token 继续转发；没有用户时带上密钥头。
- **预测批调 `/financial_forecast/predict`**：带上密钥头。
- 两处都读同一个配置项 `cio.internal-token`。

## 5. Python 端

### 5.1 接收（Java → Python）

- **`AuthMiddleware`**：按 §3.2 判定。服务通道通过时，跳过向 Java 的 `check_access`，并在请求状态里标记为服务调用。
- **新增依赖 `get_caller`**（`common/auth/identity.py`）：
  - 用户请求：与 `get_current_user` 相同。
  - 服务调用：返回 `AuthUser(user_id=SYSTEM_USER_ID)`，不带公司和组织。
  - 只有允许服务通道的路由改用 `get_caller`。其余路由仍用 `get_current_user`，服务调用到那里会返回 401。Python 端的"显式标注"就是看路由用不用 `get_caller`。
  - 不声明身份依赖的路由（如 `/financial_forecast/predict`），服务调用只要过了中间件就能进入。
- **配置**：环境变量 `INTERNAL_TOKEN`，放在 `common/config/auth.py`，并记入 `sql/migrations/env-vars/env-update.txt`。

### 5.2 发出（Python → Java）

- **`lgpi_api/_http.py`**：传了 `auth_token` 就发 Bearer；没传就发 `X-Internal-Token`。
- **删除写死的 token**：删掉 `DEFAULT_BEARER_TOKEN` 和 `LGPI_BEARER_TOKEN` 回退（早期开发遗留，生产不依赖）。
- **效果**：漏传用户 token 的调用打到没标注的 Java 接口时会直接 401，不再悄悄以超管身份执行。
- **自动走服务通道**：`query_file_link_internal` / `download_file_via_java` 本来就不传用户 token，改完自然走服务通道。
- **同步改文档**：`lgpi_api/CLAUDE.md` 中「双 token 契约」的描述，回退目标从"静态 service token"改为"服务通道"。

## 6. 安全约束

- **密钥**：至少 32 字节的随机串，各环境各不相同；只放在 Nacos 和部署环境变量里，不进代码库。
- **比较**：用常量时间比较（Java `MessageDigest.isEqual`，Python `secrets.compare_digest`）。
- **日志**：两端日志和 trace 都不得输出这个请求头。
  - Python `lgpi_api` 的请求日志只打印 `Authorization` 的脱敏预览，不会输出新头；服务调用时那一栏显示"(无)"，可以顺手改成"服务通道"，方便排查。
  - 网关日志只记方法、路径，不受影响。
- **传输**：Python → Java 经 `LGPI_BASE_URL`，可能是公网域名；走 HTTPS 时可以接受。
- **轮换**：两边同时改并重启。两边值不一致的那段时间里，服务通道调用会失败；目前没有用户的调用量很小。
- **数据范围**：服务身份不带公司和组织，所以允许服务通道的接口必须要求调用方显式传公司参数，缺参就拒绝（对齐多租户需求 1.4「取不到上下文时拒绝执行而非放行」）。

## 7. 上线顺序

每一步都兼容旧版本，没有硬期限。

1. **配密钥**：各环境的 Nacos（`cio.internal-token`）和 Python 环境变量（`INTERNAL_TOKEN`）配同一个随机密钥。
2. **Java 发版**：加过滤器和 `@InternalAccess`；调 Python 时带上密钥头。此时 Python 还不认这个头，多带一个也不影响。
3. **Python 发版**：中间件认这个头、新增 `get_caller`；调 Java 时发这个头；删掉写死的 token。
4. **收尾**：
   - `getFileLinkById` 去掉 `@AnonymousAccess`、改为 `@InternalAccess`。
   - 各环境删掉 `AUTH_CHECK_EXEMPT_PATHS=/financial_forecast`。

本地开发时两边配同一个值即可。不配的话服务通道关闭，用户通道不受影响。

## 8. 待确认

| # | 问题 | 建议 |
|---|---|---|
| Q1 | 服务通道只在标注过的接口可用，还是放开到所有要求登录的接口？ | 只在标注过的接口可用：默认拒绝；放开到全部接口等于又造了一个超管 |
| Q2 | 第一批要接入的定时任务 / 场景是哪个？ | 决定首批给哪些接口加 `@InternalAccess` / `get_caller` |
| Q3 | 两个方向共用一个密钥，还是每个方向各一个？ | 先共用一个，以后要拆只改配置，代码不动 |

## 9. 未采用的方案

- **Java 签发系统 JWT（client_credentials）**：
  - 改动更多：Java 要新增一种授权方式；Python 要做 token 缓存与续期，还要在 Redis 里准备 `auth:user:1`。
  - 风险更大：系统 JWT 能通过所有只要求登录的接口，等于又造了一个超管。
- **继续用豁免路径 / 匿名端点**：本质上是不鉴权，每个环境都要单独配置，而且外部可访问。
- **IP 白名单**：Python 调 Java 经过网关，Java 看到的来源地址是网关，区分不出调用方。
