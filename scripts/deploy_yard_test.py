"""Build + deploy the yard motion test page (design/yard_test) as a static site to Vercel (project csw-yard-test).
Uses the committed world export as-is: design/world/export/v1/{manifest.json, yard/*} + the garden idle clip.
Usage: python3 scripts/deploy_yard_test.py [--local]   (--local: only build into ~/.hermes/cache/scratch/yard_test_dist)"""
import hashlib, json, os, pathlib, shutil, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = pathlib.Path(os.path.expanduser("~/.hermes/cache/scratch/yard_test_dist"))
NAME = "csw-yard-test"

shutil.rmtree(DIST, ignore_errors=True); (DIST / "yard").mkdir(parents=True)
shutil.copy(ROOT / "design/yard_test/index.html", DIST / "index.html")
m = json.load(open(ROOT / "design/world/export/v1/manifest.json"))
json.dump(m["spaces"]["yard"], open(DIST / "yard.json", "w"), ensure_ascii=False)
for f in (ROOT / "design/world/export/v1/yard").glob("*.webp"):
    shutil.copy(f, DIST / "yard" / f.name)
shutil.copy(ROOT / "design/character/export/v1/hippo_garden_idle.webp", DIST / "hippo_garden_idle.webp")
files = [p for p in DIST.rglob("*") if p.is_file()]
print("built", len(files), "files,", sum(p.stat().st_size for p in files) // 1024, "KB ->", DIST)
if "--local" in sys.argv:
    sys.exit()

sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("dp", ROOT / "scripts/deploy_prototype.py")
src = (ROOT / "scripts/deploy_prototype.py").read_text()
ns = {"__file__": str(ROOT / "scripts/deploy_prototype.py")}
exec(src.split("s, r = call(\"GET\"")[0], ns)        # reuse token() + call() only
call = ns["call"]

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
for _ in range(80):
    time.sleep(3)
    s, r = call("GET", f"/v13/deployments/{did}")
    if r.get("readyState") in ("READY", "ERROR", "CANCELED"):
        print(r["readyState"], r.get("alias"))
        break
