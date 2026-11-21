#!/usr/bin/env python3
"""화면 보드: 지금 앱 캡처 + 논의 중/개발 대기 시안을 한 페이지로 → https://csw-prototype.vercel.app
내용은 design/board/board.json. 예전 프로토타입은 /prototype.html 로 남김.

  python3 scripts/board.py            # 만들기만 (~/.hermes/cache/scratch/csw-board/index.html)
  python3 scripts/board.py --deploy   # 만들고 Vercel(csw-prototype)에 올리기

앱 캡처를 새로 찍으려면 (웹 테스트판 기준):
  python3 scripts/capture_screens.py https://csw-app-web.vercel.app
  node scripts/capture_onboarding.mjs design/screens/onboarding https://csw-app-web.vercel.app
"""
import datetime, hashlib, html, json, os, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(os.environ.get('TMPDIR', '/tmp')) / 'csw-board'
CFG = json.loads((ROOT / 'design/board/board.json').read_text())
STATUS = {'discussing': ('논의 중', '#f3c969'), 'decided': ('결정됨 · 개발 대기', '#9fd3b8'), 'built': ('개발 완료', '#d9d4cc')}


def img(src: str, width: int) -> str:
    """원본 PNG → 줄인 JPEG (sips). 보드 안 경로를 돌려줌."""
    p = ROOT / src
    name = src.replace('/', '_').rsplit('.', 1)[0] + '.jpg'
    dst = OUT / 'img' / name
    if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '78', '-Z', str(width), str(p), '--out', str(dst)],
                       check=True, capture_output=True)
    return 'img/' + name


def titles(d: pathlib.Path) -> dict:
    f = d / 'index.json'
    return {x['file'].rsplit('.', 1)[0]: x['title'] for x in json.loads(f.read_text())} if f.exists() else {}


def day(p: pathlib.Path) -> str:
    return datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime('%m-%d')


def build():
    (OUT / 'img').mkdir(parents=True, exist_ok=True)
    e = html.escape
    parts = []
    # 1. 지금 앱
    parts.append('<h2>지금 앱 <small>웹 테스트판을 자동으로 돌며 찍은 실제 화면</small></h2>')
    for g in CFG['app_groups']:
        d = ROOT / g['dir']
        t = titles(d)
        cells = []
        for f in g['files']:
            p = d / f'{f}.png'
            if not p.exists():
                continue
            src = img(str(p.relative_to(ROOT)), 780)
            cells.append(f'<a class="ph" href="{src}"><img loading="lazy" src="{src}"><span>{e(t.get(f, f))}</span></a>')
        when = max((day(d / f'{f}.png') for f in g['files'] if (d / f'{f}.png').exists()), default='-')
        parts.append(f'<h3>{e(g["title"])} <small>캡처 {when}</small></h3><div class="row">{"".join(cells)}</div>')
    # 2. 시안
    def mock(m):
        label, col = STATUS[m['status']]
        ims = ''.join(f'<a class="sh" href="{s}"><img loading="lazy" src="{s}"></a>' for s in (img(i, 1400) for i in m['images']))
        note = f'<p>{e(m["note"])}</p>' if m.get('note') else ''
        return (f'<div class="card"><div class="meta"><b class="tag" style="background:{col}">{label}</b> {e(m["date"])} · {e(m["thread"])} 스레드</div>'
                f'<h3>{e(m["title"])}</h3><p class="dec">{e(m["decisions"])}</p>{note}<div class="row">{ims}</div></div>')
    open_ = [m for m in CFG['mocks'] if m['status'] != 'built']
    open_.sort(key=lambda m: (m['status'] != 'discussing', m['date']), reverse=False)
    parts.append('<h2>논의 중 · 개발 대기 <small>아직 앱에 없는 화면 (화면마다 최신 시안만)</small></h2>')
    parts += [mock(m) for m in open_] or ['<p>없음</p>']
    done = [m for m in CFG['mocks'] if m['status'] == 'built']
    parts.append(f'<details><summary>개발 끝난 시안 보관 ({len(done)}) — 지금 앱 화면과 비교할 때만</summary>{"".join(mock(m) for m in done)}</details>')

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Hamalog 화면 보드</title><style>
body{{margin:0;font-family:-apple-system,system-ui,sans-serif;background:#faf7f2;color:#3a3330}}
header{{padding:18px 16px 4px}} h1{{font-size:20px;margin:0}} header p{{margin:4px 0;color:#8a817a;font-size:13px}}
h2{{font-size:17px;margin:26px 16px 4px}} h3{{font-size:15px;margin:14px 16px 6px}} small{{font-weight:400;color:#8a817a;font-size:12px}}
.row{{display:flex;gap:10px;overflow-x:auto;padding:4px 16px 10px;scroll-snap-type:x proximity}}
.ph{{flex:0 0 150px;scroll-snap-align:start;text-decoration:none;color:inherit}} .ph img{{width:150px;border-radius:14px;box-shadow:0 1px 6px #0002;display:block}}
.ph span{{display:block;font-size:11.5px;margin-top:5px;line-height:1.3}}
.sh{{flex:0 0 auto;scroll-snap-align:start}} .sh img{{height:300px;border-radius:10px;box-shadow:0 1px 6px #0002;display:block}}
.card{{background:#fff;border-radius:18px;margin:10px 12px;padding:10px 0 4px}} .card h3{{margin:6px 16px 2px}}
.card p{{margin:2px 16px;font-size:13px;color:#6b625c}} .dec{{color:#3a3330!important}} .meta{{margin:0 16px;font-size:12px;color:#8a817a}}
.tag{{padding:2px 8px;border-radius:99px;color:#3a3330;font-size:11.5px}}
details{{margin:22px 4px 40px}} summary{{font-size:14px;margin:0 12px;color:#6b625c}}
</style></head><body><header><h1>Hamalog 화면 보드</h1><p>업데이트 {now} · 사진을 누르면 크게 · 예전 프로토타입은 <a href="prototype.html">여기</a></p></header>
{"".join(parts)}</body></html>'''
    (OUT / 'index.html').write_text(page)
    proto = (ROOT / 'design/prototype.html').read_bytes()
    (OUT / 'prototype.html').write_bytes(proto)
    used = {'index.html', 'prototype.html'} | {'img/' + p.name for p in (OUT / 'img').iterdir()}
    keep = set(page.split('src="')[i].split('"')[0] for i in range(1, page.count('src="') + 1))
    return [f for f in used if not f.startswith('img/') or f in keep]


TEAM, NAME = 'team_MSzBYrXIhnKEz4uV6OF0WmQe', 'csw-prototype'


def call(method, path, body=None, raw=None, headers=None):
    import urllib.error, urllib.request
    sys.path[:0] = [os.path.expanduser('~/.hermes/scripts'), os.path.expanduser('~/.hermes/cache/scratch')]
    try:
        from vercel_auth import get_token
        tok = get_token()
    except ImportError:
        tok = json.load(open(os.path.expanduser('~/Library/Application Support/com.vercel.cli/auth.json')))['token']
    url = f"https://api.vercel.com{path}{'&' if '?' in path else '?'}teamId={TEAM}"
    h = {'Authorization': f'Bearer {tok}', **(headers or {})}
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if raw is None and body is not None:
        h['Content-Type'] = 'application/json'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method, data=data, headers=h), timeout=120) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b'{}')


def deploy(files):
    s, r = call('GET', f'/v9/projects/{NAME}')
    assert s == 200, r
    pid = r['id']
    entries = []
    for f in sorted(files):
        data = (OUT / f).read_bytes()
        sha = hashlib.sha1(data).hexdigest()
        s, r = call('POST', '/v2/files', raw=data, headers={'x-vercel-digest': sha, 'Content-Type': 'application/octet-stream'})
        assert s < 300, (f, r)
        entries.append({'file': f, 'sha': sha, 'size': len(data)})
    s, r = call('POST', '/v13/deployments', {'name': NAME, 'project': pid, 'target': 'production', 'files': entries,
                                             'projectSettings': {'framework': None}})
    assert s < 300, r
    did = r['id']
    for _ in range(60):
        time.sleep(3)
        s, r = call('GET', f'/v13/deployments/{did}')
        if r.get('readyState') in ('READY', 'ERROR', 'CANCELED'):
            print(r['readyState'], 'https://csw-prototype.vercel.app')
            return


if __name__ == '__main__':
    files = build()
    print(len(files), 'files →', OUT / 'index.html')
    if '--deploy' in sys.argv:
        deploy(files)
