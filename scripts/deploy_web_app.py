#!/usr/bin/env python3
"""앱 웹 빌드를 Vercel(프로젝트 csw-app-web)에 올림 — 대표가 밖에서(Expo Go 안 될 때) 폰 브라우저로 확인하는 임시 테스트판.
실제 Supabase(csw)에 붙음. 지금 작업 트리(커밋 안 된 변경 포함)를 그대로 빌드하니, 올리기 전에 tsc 확인 권장.
사용: python3 scripts/deploy_web_app.py [--local]   (--local: 빌드만, mobile/dist)
첫 실행 때 배포 주소를 Supabase Auth uri_allow_list에 추가(카카오 로그인 복귀용)."""
import base64, hashlib, json, pathlib, shutil, subprocess, sys, time, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
MOBILE = ROOT / "mobile"
DIST = MOBILE / "dist"
NAME = "csw-app-web"
REF = "xbifxrvgdimwwijijthl"

shutil.rmtree(DIST, ignore_errors=True)
subprocess.run(["npx", "expo", "export", "--platform", "web", "--output-dir", "dist"], cwd=MOBILE, check=True)
# output: single (SPA) → 모든 경로를 index.html로
(DIST / "vercel.json").write_text(json.dumps({
    "rewrites": [{"source": "/(.*)", "destination": "/index.html"}],
    "headers": [{"source": "/index.html", "headers": [{"key": "Cache-Control", "value": "no-cache"}]}],
}))
files = [p for p in DIST.rglob("*") if p.is_file()]
print("built", len(files), "files,", sum(p.stat().st_size for p in files) // 1024 // 1024, "MB")
if "--local" in sys.argv:
    sys.exit()

sys.path.insert(0, str(ROOT / "scripts"))
from board import call  # Vercel REST 호출 재사용 (deploy_prototype.py는 board.py 호환 껍데기가 됨)

s, r = call("GET", f"/v9/projects/{NAME}")
if s != 200:
    s, r = call("POST", "/v11/projects", {"name": NAME, "framework": None})
    assert s < 300, r
pid = r["id"]
call("PATCH", f"/v9/projects/{pid}", {"ssoProtection": None})

entries = []
for p in files:
    data = p.read_bytes(); sha = hashlib.sha1(data).hexdigest()
    s, r = call("POST", "/v2/files", raw=data, headers={"x-vercel-digest": sha, "Content-Type": "application/octet-stream"})
    assert s < 300, r
    entries.append({"file": str(p.relative_to(DIST)), "sha": sha, "size": len(data)})
s, r = call("POST", "/v13/deployments", {"name": NAME, "project": pid, "target": "production", "files": entries,
                                         "projectSettings": {"framework": None}})
assert s < 300, r
did = r["id"]
alias = []
for _ in range(100):
    time.sleep(3)
    s, r = call("GET", f"/v13/deployments/{did}")
    if r.get("readyState") in ("READY", "ERROR", "CANCELED"):
        alias = r.get("alias") or []
        print(r["readyState"], alias)
        break

# Supabase redirect 허용 목록에 배포 주소 추가 (없을 때만)
raw = subprocess.run(["security", "find-generic-password", "-s", "Supabase CLI", "-w"], capture_output=True, text=True).stdout.strip()
if raw.startswith("go-keyring-base64:"):
    raw = base64.b64decode(raw.split(":", 1)[1]).decode()
def sb(method, body=None):
    req = urllib.request.Request(f"https://api.supabase.com/v1/projects/{REF}/config/auth", method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + raw, "Content-Type": "application/json", "User-Agent": "csw-agent"})
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())
cur = [u for u in (sb("GET").get("uri_allow_list") or "").split(",") if u]
want = [f"https://{min(alias, key=len)}/**"] if alias else []  # 가장 짧은 별칭 = 고정 production 주소
add = [u for u in want if u not in cur]
if add:
    sb("PATCH", {"uri_allow_list": ",".join(cur + add)})
print("allow list:", ",".join(cur + add))
