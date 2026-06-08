# 鉴权下沉 common + 统一 rag + 合并上下文模型 — 重构计划

> 关联文档：`CIOaas-python/standards/architecture.md`（§2.1.1 横切平台豁免、§2.1 跨模块边界）、`docs/AI-Chatbot/设计/design-doc.md`、`docs/superpowers/plans/2026-06-05-ai-chatbot-v1-python-backend.md`
>
> 状态：**已落地（2026-06-08）**，详见 §8。company_id 来源已定（拆分 `company_id` / `organization_id` 两个独立字段）；**待确认两项**：专门鉴权接口路径(P1) + Java 是否在 `auth:user` 写入 `companyId`。

## 1. 背景：鉴权目前是「两套并存且不一致」

| 维度 | chatbot（真鉴权 ✅） | rag（dev 假占位 ❌） |
|---|---|---|
| 身份解析 | `chatbot/auth/redis_session.py::resolve_identity()`：`Authorization: Bearer` → SHA256 → `auth:token:{hash}` → `userId` → `auth:user:{userId}` | `rag/interfaces/deps.py::require_user_context()`：**不查 Redis**，读网关头，缺失就用 `dev-user`/`dev-company` 占位 |
| 上下文模型 | `Identity(user_id, org_id, authorities)` → `ChatUserContext(+is_admin, end_type, auth_token)` | `UserContext(user_id, company_id, role, is_admin, caller_type)` |
| Redis 结构 | **已核实**真实 Java 结构，DB 10 | TODO 里写的 `session:{key}` 是过时设想，与左列对不上 |
| 路由依赖数 | `chatbot/interfaces/routes.py` 4 处 | `rag/interfaces/routes.py` 约 40 处 |
| 公司范围 | `chatbot/auth/acl.py`（调 Java `/invite/portfolio` 取**可访问公司列表**） | 无（单 `company_id` 过滤） |

**模块依赖事实**：`chatbot` 与 `rag` 互不 import，唯一交集是都依赖 `common`（`main.py` 各自挂载 router）。→ 合并模型放 `common/auth`、两边各自薄封装，**架构上干净、不引入循环依赖**。

**命名坑**：`common/token_utils.py` 是 LLM 的 tiktoken 计数工具，与鉴权 token 无关——新鉴权代码不得复用该名字。

## 2. 目标形态（符合 architecture.md §2.1.1：common 可被任意模块 import）

```
source/common/auth/
├── __init__.py          # 对外唯一入口，re-export UserContext / resolve_identity / token_key
├── identity.py          # Identity 值对象 + resolve_identity(token)：token → Redis → 身份（= "获取用户信息的单独文件"）
├── redis_session.py     # token_key 公式（SHA256）+ Redis client（lru_cache 单例），从 chatbot 搬来
└── context.py           # 统一 UserContext（合并模型，见 §3）
```

- 各模块 `interfaces/deps.py` 只保留**薄封装**：`require_user_context()` 读 header → 调 `common.auth.resolve_identity` → 包装成 `UserContext`，并抛 401。
- 公司 ACL（`acl.py`）**留在 chatbot**：它是「可访问的多个被投资公司列表」（投资组合维度），与「租户隔离」是不同概念，rag 不需要，不下沉。

## 3. 合并上下文模型 `common/auth/context.py`

字段取两套并集（frozen dataclass，沿用现有不可变值对象惯例）：

| 字段 | 类型 | 来源 | chatbot 用 | rag 用 | 说明 |
|---|---|---|---|:--:|:--:|
| `user_id` | `str` | `auth:token` → userId | ✅ | ✅ | 必填 |
| `company_id` | `Optional[str]` | **见 P0** | ✅(原 `org_id`) | ✅(核心过滤键) | chatbot 的 `org_id` 与 rag 的 `company_id` 合并为此字段 |
| `authorities` | `list[str]` | `auth:user.authorities` | ✅(算 is_admin) | ➖ | role 字符串不再单列（rag routes 未直接用 `ctx.role`） |
| `is_admin` | `bool` | `authorities` 命中 `RAG_ADMIN_ROLES` 白名单 | ✅ | ✅ | 派生 |
| `auth_token` | `str` | 原始 Bearer | ✅(调 ACL) | ➖ | rag 真鉴权后亦持有 |
| `end_type` | `str` | header `x-chat-end`（company\|admin） | ✅ | ➖ | chatbot 特有；rag 默认 `company` |
| `caller_type` | `str` | header `x-caller-type`（USER\|CHATBOT） | ➖ | ✅ | rag 特有；chatbot 默认 `USER` |

- 兼容处理：为不破坏 chatbot 现有 `ctx.org_id`，可在 `UserContext` 加 `org_id` 只读 property 返回 `company_id`（或一次性把 chatbot 4 处 `ctx.org_id` 改成 `ctx.company_id`）。
- `end_type` / `caller_type` 是两个**正交维度**（前端是哪个端 vs 调用方是真人还是 chatbot 代行），均保留，互不冲突。

## 4. ⚠️ P0 待确认：rag 的 `company_id` 在真鉴权下从哪来？

真鉴权下身份只来自 `auth:user:{userId}` = `{id, username, organizationId, authorities}`——**只有 `organizationId`，没有 `company_id`**。

**我的推断（倾向 A）**：rag 的 `company_id` 注释为「所属公司 ID、多租户隔离的强制过滤键」——这是**租户**维度，应等于用户所属组织 `organizationId`；而 chatbot 的 `accessible_companies`（/invite/portfolio）是「可查看哪些被投资公司财务」的**业务数据**维度，两者不同。因此：

- **方案 A（推荐）**：`company_id = organizationId`（从 `auth:user` 取）。合并模型里 chatbot `org_id` 与 rag `company_id` 天然是同一值。
- **方案 B**：`organizationId` 与 rag 的 `company_id` 不是一回事（如一个 organization 下挂多个 company），则 `company_id` 需由前端/网关通过显式 header（如当前选中公司）传入，`require_user_context` 读该 header。
- **方案 C**：rag 也走 `/invite/portfolio` 那套，但需重新定义「单值 company_id」如何从「可访问列表」收敛。

> **这一项必须由你拍板**——选 B/C 会改变 §5 Phase 3 与 §3 的 `company_id` 取值逻辑。若推断 A 错误而误用，rag 全部多租户过滤会失效（越权风险）。

## 5. 迁移阶段（确认 P0 后并行执行）

- **Phase 1 — common/auth 底座**：新建 `common/auth/{__init__,identity,redis_session,context}.py`；`redis_session`+`Identity` 从 chatbot 原样搬入；`UserContext` 按 §3 定义；`is_admin` 判定复用 `common.config.rag.load_rag_auth_settings().admin_roles`。
- **Phase 2 — chatbot 切换**：`chatbot/interfaces/deps.py::require_chat_user` 改为复用 `common.auth`（读 `Authorization`+`x-chat-end` → `resolve_identity` → `UserContext`）；删 `chatbot/auth/redis_session.py`、`chatbot/auth/__init__.py` 旧身份解析（`acl.py` 保留）；4 处路由 `ctx.org_id` 处理（property 兼容或改名）。
- **Phase 3 — rag 切真鉴权**：`rag/interfaces/deps.py::require_user_context` 改为复用 `common.auth`，按 P0 结论填 `company_id`；删除 `_DEV_FALLBACK_*` 占位与大段 TODO；约 40 处路由签名 `ctx: UserContext = Depends(require_user_context)` **保持不变**（只是 `UserContext` 改为从 common 导入）。
- **Phase 4 — 清理 + 测试**：更新 `tests/chatbot/auth/*`、`tests/chatbot/interfaces/test_deps.py`、`tests/rag/test_deps.py` 及依赖 dev 占位的 rag 测试；新增 `tests/common/auth/*`。
- **Phase 5 — 规范校验**：`ruff check source/`（TID251 等）+ `import-linter` + `uv run pytest tests/`，按 `CIOaas-python/CLAUDE.md`「完成开发后用规范审查一遍」收尾。

## 6. 风险与注意

1. **rag 转真鉴权会打断「前端直连 Python 联调」**：dev 占位本就是为联调便利而设。切换后 rag 所有路由必须带真 token（且需 Java 网关已把 `auth:token`/`auth:user` 写进 Redis）。**确认 rag 当前是否已具备真 token 联调条件**，否则建议把 Phase 3 拆为独立可回退提交。
2. **P0 推断若错，rag 多租户过滤全错** → 越权。Phase 3 前必须钉死 P0。
3. `caller_type` 的两个来源（header `x-caller-type` 与 `request.callerType`，后者用于 search）属 rag 内部行为，本次重构**不改变**其语义，仅迁移 `UserContext` 定义位置。
4. `acl.py` 依赖 `lgpi_api`（顶层包），留在 chatbot 不违反分层。

## 7. 执行方式

确认 P0 后用 Agent Teams 并行：Phase 1（common 底座）先行 → Phase 2（chatbot）/ Phase 3（rag）可并行分派给两个 dev agent → Reviewer agent 对照本计划审查 → 统一跑 ruff + pytest。

## 8. 实现记录（2026-06-08 落地）

### 已完成
- **common/auth 底座**：`context.py`(UserContext) / `redis_session.py`(取数) / `mock_provider.py`(mock) / `identity.py`(get_current_user) / `access_check.py`(调 Java 鉴权) / `config/auth.py`(配置)；对外经 `__init__.py` 收口。
- **数据模型（根治原 P4）**：`UserContext` / `RedisUserData` 拆出**两个独立字段** `company_id`(rag 多租户键，读 `auth:user.companyId`) 与 `organization_id`(读 `organizationId`，chatbot 的 `org_id` property 指向它)。
- **鉴权接入(H2)**：chatbot/rag 的 `deps` 改 `async`，每请求 `await check_access(token)`（调 Java、按状态 `2xx 放行 / 401 未登录 / 403 无权 / 其它保守拒绝`）；受 `AUTH_CHECK_ENABLED` 开关控制（默认 false，待专门接口路径确认后开）。
- **取用户数据 + mock**：`get_current_user` 按 `AUTH_MOCK_ENABLED` 走 Redis 或 mock；`ensure_mock_safe()` 已接入 `main.py` 启动期（prod/uat 误开即 fail-fast）。
- **中危修复**：rag `company_id` 取不到 → 401(code 40102，防 `None` 进 SQL 越权)；两端 Bearer 提取统一为大小写不敏感。
- **既有缺陷**：chatbot `get_messages/get_thread` 加 `user_id` 归属校验（IDOR，admin 端豁免）；Sentry `before_send` 剥离 `Authorization`/`Cookie` 头（防 token 上报）。

### 待确认（你提供后改 env / 微调即生效）
1. **专门鉴权接口路径(P1)**：`AUTH_CHECK_PATH` 默认仍是 `/invite/portfolio` 占位。确认真实路径 + 状态码语义后改 env，并置 `AUTH_CHECK_ENABLED=true`，每请求调 Java 判权限才真正生效。
2. **Java `auth:user` 是否写入 `companyId`**：`company_id` 读该字段。若 Java 未写，rag 请求会因 company_id 兜底返回 401(40102) —— 需 Java 侧补写。

### 验证
- `pytest tests/common/auth tests/chatbot tests/rag/test_deps.py` → **88 passed**。
- `ruff check`（全部改动文件，含 TID251 LLM 黑名单）→ **All checks passed**。
- 新增 env：`AUTH_MOCK_ENABLED` / `AUTH_MOCK_USER_ID` / `AUTH_MOCK_COMPANY_ID` / `AUTH_MOCK_ORGANIZATION_ID` / `AUTH_MOCK_AUTHORITIES` / `AUTH_CHECK_ENABLED` / `AUTH_CHECK_PATH`。
