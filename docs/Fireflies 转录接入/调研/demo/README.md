# Fireflies MCP / OAuth 实测脚本

2026-09-18 做通道调研时写的几个最小脚本（`register.py`、`cross_channel_check.py` 为 2026-09-21 补），`fireflies-api-capability-survey.md` §3.0 与附录 B 的 MCP 侧数据都由它们跑出来。
**只是验证可行性的探针，不是生产实现**——产品化时授权回调要落到 Java 后端（参照 QuickBooks 那套），不是这里的 localhost 服务。

> Fireflies 自己没有开发者级的 OAuth 文档，只在帮助中心说了句「按提示完成授权」。
> 但这里的每一步都不是自定义实现，全部对应 [MCP 官方授权规范](https://modelcontextprotocol.io/specification/latest/basic/authorization)
> 及其引用的 RFC 的强制条款：动态注册 [RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591)、
> 端点发现 [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414) / [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728)、
> PKCE（OAuth 2.1 §7.5.2）、资源指示符 [RFC 8707](https://www.rfc-editor.org/rfc/rfc8707.html)。
> Fireflies 的具体参数以 `https://api.fireflies.ai/.well-known/oauth-authorization-server` 为准。

## 文件

| 文件 | 作用 |
|---|---|
| `register.py` | 动态客户端注册（RFC 7591），产出 `client_id`；原先这步是手动 curl 的，2026-09-21 补成脚本 |
| `oauth_flow.py` | OAuth 2.1 授权码 + PKCE(S256) 全流程：生成 challenge → 打印授权 URL → 本地 8765 端口收回调 → 用 code 换 token |
| `mcp_client.py` | 带 token 调 `https://api.fireflies.ai/mcp` 的最小 JSON-RPC 客户端，兼容 SSE 与纯 JSON 响应 |
| `cross_channel_check.py` | 验证两条通道凭据是否互通：API key→MCP、OAuth token→GraphQL，外加伪造 token 的阴性对照（2026-09-21 补） |

## 怎么跑

三个脚本只用标准库，直接 `python xxx.py` 即可，无需装依赖。后两个读同目录下的凭据文件（`ff_oauth_client.json` / `ff_oauth_token.json`），**这两个文件已 gitignore、不入库**，按下面的顺序自己生成。

### 1. 动态注册，产出 `ff_oauth_client.json`

Fireflies 支持免审批动态注册（RFC 7591），返回 201：

```
python register.py "你的应用名"
```

返回里有 `client_id`，**没有 client_secret**（公开客户端，故强制 PKCE）。

> Windows 注意：PowerShell 5.1 的 `curl` 是 `Invoke-WebRequest` 的别名，不认 `-X` / `-H` / `-d`，续行也不是 `\`。
> 所以这一步用上面的 `register.py`，不要照搬网上的 curl 写法。真要用命令行，PowerShell 里是：
>
> ```powershell
> $body = @{ redirect_uris=@("http://localhost:8765/callback")
>            token_endpoint_auth_method="none"
>            grant_types=@("authorization_code","refresh_token")
>            response_types=@("code"); client_name="你的应用名"
>            scope="profile email"; application_type="native" } | ConvertTo-Json
> Invoke-RestMethod -Method Post -Uri https://api.fireflies.ai/register `
>   -ContentType 'application/json' -Body $body |
>   ConvertTo-Json | Out-File -Encoding utf8 ff_oauth_client.json
> ```

### 2. 走授权，产出 `ff_oauth_token.json`

```bash
python oauth_flow.py
```

脚本打印一条 `https://api.fireflies.ai/authorize?...`，手动在浏览器打开、用 Fireflies 账号点同意，浏览器跳回 `localhost:8765` 后脚本自动换 token 并落盘。
token 形如 `{access_token, token_type, expires_in: 7776000, scope, refresh_token}`——90 天，且每次刷新重新给满 90 天（滚动窗口，见 §3.0 凭据生命周期表）。

### 3. 调 MCP

`mcp_client.py` 是个模块，import 后用 `rpc()`：

```python
from mcp_client import rpc
rpc("initialize", {"protocolVersion":"2025-06-18","capabilities":{},
                   "clientInfo":{"name":"probe","version":"0"}})
rpc("notifications/initialized", {}, notify=True)   # 必须发，否则后续调用报错
rpc("tools/list")
rpc("tools/call", {"name":"fireflies_get_transcripts","arguments":{"limit":5,"format":"json"}})

```

首次 `initialize` 的响应头带 `Mcp-Session-Id`，脚本会自动记住并在后续请求里带上。

## 注意

- **`ff_oauth_client.json` / `ff_oauth_token.json` 含真实凭据，不要提交**。
- MCP 与 GraphQL **共用同一套日配额**，Free 套餐 50 次/天，跑 demo 时容易把当天配额耗光。
- OAuth token **不能用于 GraphQL**（实测 `auth_failed`），反之 API key 也不能用于 MCP。
