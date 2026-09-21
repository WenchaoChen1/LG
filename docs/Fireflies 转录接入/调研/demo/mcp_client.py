import json,urllib.request,urllib.error
TOK=json.load(open('ff_oauth_token.json'))['access_token']
URL="https://api.fireflies.ai/mcp"
SESSION={'id':None}

def rpc(method,params=None,notify=False):
    body={"jsonrpc":"2.0","method":method}
    if params is not None: body["params"]=params
    if not notify: body["id"]=rpc.n; rpc.n+=1
    h={"Authorization":"Bearer "+TOK,"Content-Type":"application/json",
       "Accept":"application/json, text/event-stream",
       "MCP-Protocol-Version":"2025-06-18"}
    if SESSION['id']: h["Mcp-Session-Id"]=SESSION['id']
    req=urllib.request.Request(URL,data=json.dumps(body).encode(),headers=h)
    try:
        r=urllib.request.urlopen(req,timeout=60)
        sid=r.headers.get('Mcp-Session-Id')
        if sid: SESSION['id']=sid
        raw=r.read().decode()
    except urllib.error.HTTPError as e:
        return {"_http":e.code,"_body":e.read().decode()[:400]}
    if not raw.strip(): return {}
    for line in raw.splitlines():          # SSE 或纯 JSON 都兼容
        if line.startswith('data:'):
            return json.loads(line[5:].strip())
    return json.loads(raw)
rpc.n=1
