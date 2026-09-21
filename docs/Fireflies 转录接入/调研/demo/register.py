"""动态注册一个 Fireflies OAuth 客户端（RFC 7591），结果写入 ff_oauth_client.json。

用法：python register.py [client_name]
"""
import json, sys, urllib.request, urllib.error

NAME = sys.argv[1] if len(sys.argv) > 1 else "LG Fireflies Integration (probe)"
REDIRECT = "http://localhost:8765/callback"

body = json.dumps({
    "redirect_uris": [REDIRECT],
    "token_endpoint_auth_method": "none",
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "client_name": NAME,
    "scope": "profile email",
    "application_type": "native",
}).encode()

req = urllib.request.Request("https://api.fireflies.ai/register", data=body,
                             headers={"Content-Type": "application/json"})
try:
    r = urllib.request.urlopen(req, timeout=30)
    st, raw = r.status, r.read().decode()
except urllib.error.HTTPError as e:
    print("REGISTER_HTTP", e.code)
    print(e.read().decode()[:600])
    raise SystemExit(1)

print("REGISTER_HTTP", st)
data = json.loads(raw)
json.dump(data, open("ff_oauth_client.json", "w"), indent=1)
print("client_id:", data["client_id"])
print("wrote ff_oauth_client.json -- next: python oauth_flow.py")
