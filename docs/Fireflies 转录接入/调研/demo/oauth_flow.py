import json,base64,hashlib,os,urllib.parse,urllib.request,urllib.error,threading
from http.server import BaseHTTPRequestHandler,HTTPServer

CID=json.load(open('ff_oauth_client.json'))['client_id']
REDIRECT="http://localhost:8765/callback"
ver=base64.urlsafe_b64encode(os.urandom(64)).rstrip(b'=').decode()
chal=base64.urlsafe_b64encode(hashlib.sha256(ver.encode()).digest()).rstrip(b'=').decode()
state=base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode()

url="https://api.fireflies.ai/authorize?"+urllib.parse.urlencode({
 "response_type":"code","client_id":CID,"redirect_uri":REDIRECT,
 "scope":"profile email","state":state,
 "code_challenge":chal,"code_challenge_method":"S256",
 "resource":"https://api.fireflies.ai/mcp",
})
open('authorize_url.txt','w').write(url)
print("OPEN_THIS_URL:\n"+url,flush=True)

result={}

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'code' not in q and 'error' not in q:
            self.send_response(404); self.end_headers(); return
        result.update({k:v[0] for k,v in q.items()})
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers()
        self.wfile.write("<h2>Received. You can close this tab.</h2>".encode())
        threading.Thread(target=srv.shutdown,daemon=True).start()

srv=HTTPServer(('127.0.0.1',8765),H)
srv.timeout=600
srv.serve_forever()

if result.get('error'):
    print("AUTH_ERROR:",json.dumps(result)); raise SystemExit(1)
    
if result.get('state')!=state:
    print("STATE_MISMATCH"); raise SystemExit(1)
    
print("code received, exchanging...",flush=True)

data=urllib.parse.urlencode({
 "grant_type":"authorization_code","code":result['code'],
 "redirect_uri":REDIRECT,"client_id":CID,"code_verifier":ver,
 "resource":"https://api.fireflies.ai/mcp",
}).encode()

req=urllib.request.Request("https://api.fireflies.ai/token",data=data,
  headers={"Content-Type":"application/x-www-form-urlencoded"})
  
try:
    r=urllib.request.urlopen(req,timeout=30); body=r.read().decode(); st=r.status
except urllib.error.HTTPError as e:
    body=e.read().decode(); st=e.code
print("TOKEN_HTTP",st)

try:
    tok=json.loads(body); json.dump(tok,open('ff_oauth_token.json','w'),indent=1)
    print(json.dumps({k:(('<len %d>'%len(str(v))) if 'token' in k else v) for k,v in tok.items()},indent=1))
except Exception:
    print(body[:600])
