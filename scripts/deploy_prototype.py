"""Deploy design/prototype.html as a static site to Vercel (project csw-prototype) via REST API.
Usage: python3 scripts/deploy_prototype.py"""
import hashlib, json, os, pathlib, sys, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEAM = "team_MSzBYrXIhnKEz4uV6OF0WmQe"
NAME = "csw-prototype"


def token():
    sys.path[:0] = [os.path.expanduser("~/.hermes/scripts"), os.path.expanduser("~/.hermes/cache/scratch")]
    try:
        from vercel_auth import get_token
        return get_token()
    except ImportError:
        return json.load(open(os.path.expanduser("~/Library/Application Support/com.vercel.cli/auth.json")))["token"]


TOKEN = token()


def call(method, path, body=None, raw=None, headers=None):
    url = f"https://api.vercel.com{path}{'&' if '?' in path else '?'}teamId={TEAM}"
    h = {"Authorization": f"Bearer {TOKEN}", **(headers or {})}
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if raw is None and body is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


s, r = call("GET", f"/v9/projects/{NAME}")
if s != 200:
    s, r = call("POST", "/v11/projects", {"name": NAME, "framework": None})
    assert s < 300, r
pid = r["id"]
# public prototype link: turn off Vercel deployment protection
call("PATCH", f"/v9/projects/{pid}", {"ssoProtection": None})

data = (ROOT / "design/prototype.html").read_bytes()
sha = hashlib.sha1(data).hexdigest()
s, r = call("POST", "/v2/files", raw=data, headers={"x-vercel-digest": sha, "Content-Type": "application/octet-stream"})
assert s < 300, r
s, r = call("POST", "/v13/deployments", {"name": NAME, "project": pid, "target": "production",
                                         "files": [{"file": "index.html", "sha": sha, "size": len(data)}],
                                         "projectSettings": {"framework": None}})
assert s < 300, r
did = r["id"]
for _ in range(60):
    time.sleep(3)
    s, r = call("GET", f"/v13/deployments/{did}")
    if r.get("readyState") in ("READY", "ERROR", "CANCELED"):
        print(r["readyState"], r.get("alias"))
        break
