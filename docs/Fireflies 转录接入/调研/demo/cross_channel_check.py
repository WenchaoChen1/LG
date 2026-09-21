"""实测两条通道的凭据是否互通（2026-09-21）。

方向 A：API key     -> MCP      需要环境变量 FIREFLIES_API_KEY
方向 B：OAuth token -> GraphQL  读同目录 ff_oauth_token.json
阴性对照：伪造 token -> MCP     证明 MCP 确实校验鉴权，A 的 200 不是"不校验"

用法：python cross_channel_check.py
每个方向各消耗配额（两条通道共用 50 次/天），A 走完整握手约 3 次。
"""
import json, os, urllib.request, urllib.error

MCP = "https://api.fireflies.ai/mcp"
GQL = "https://api.fireflies.ai/graphql"


def mcp_session(token, label):
    """跑一遍 initialize -> tools/list -> get_user，打印每步结果。"""
    session, seq = {"id": None}, [1]

    def rpc(method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            body["id"] = seq[0]; seq[0] += 1
        h = {"Authorization": "Bearer " + token, "Content-Type": "application/json",
             "Accept": "application/json, text/event-stream",
             "MCP-Protocol-Version": "2025-06-18"}
        if session["id"]:
            h["Mcp-Session-Id"] = session["id"]
        req = urllib.request.Request(MCP, data=json.dumps(body).encode(), headers=h)
        try:
            r = urllib.request.urlopen(req, timeout=40)
            sid = r.headers.get("Mcp-Session-Id")
            if sid:
                session["id"] = sid
            raw = r.read().decode()
        except urllib.error.HTTPError as e:
            return {"_http": e.code, "_body": e.read().decode()[:300]}
        if not raw.strip():
            return {}
        for line in raw.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return json.loads(raw)

    print("=====", label)
    init = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                              "clientInfo": {"name": "cross-check", "version": "0"}})
    print("initialize ->", json.dumps(init)[:200])
    if "_http" in init:
        return
    rpc("notifications/initialized", {}, notify=True)
    tools = rpc("tools/list")
    print("tools/list ->", "%d tools" % len(tools["result"]["tools"])
          if "result" in tools else json.dumps(tools)[:300])
    print("get_user   ->", json.dumps(rpc("tools/call",
          {"name": "fireflies_get_user", "arguments": {}}))[:600])


def graphql_with(token, label):
    print("=====", label)
    req = urllib.request.Request(GQL, data=json.dumps({"query": "{ user { user_id email } }"}).encode(),
                                 headers={"Authorization": "Bearer " + token,
                                          "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        print("HTTP", r.status, r.read().decode()[:400])
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:400])


mcp_session("invalid-token-negative-control", "阴性对照：伪造 token -> MCP")
print()

key = os.environ.get("FIREFLIES_API_KEY")
if key:
    mcp_session(key, "方向 A：GraphQL 的 API key -> MCP")
else:
    print("===== 方向 A SKIPPED：先设 FIREFLIES_API_KEY（见 CIOaas-python/.env 的 FIREFLIES=）")
print()

try:
    tok = json.load(open("ff_oauth_token.json"))["access_token"]
except Exception as e:
    print("===== 方向 B SKIPPED：ff_oauth_token.json 读不到 —", e)
else:
    graphql_with(tok, "方向 B：OAuth access_token -> GraphQL")
