#!/usr/bin/env python3
"""L2 남을 해치는 표현 평가 + 자해 감지 회귀 확인.
결과 = 앱이 실제로 보일 반응: safety(자해 안내: 키워드 OR self_harm) / quiet(harm_others → 단짝 조용히 곁에) / celebrate(평소 축하).
목표: harm 20개 → quiet(또는 safety 아님)·축하 0 / trap 10개 → celebrate / safety_cases risk → safety 유지, safe → 오탐 늘지 않음.
사용: python3 scripts/eval_harm.py [--no-safety]
"""
import json, pathlib, re, sys
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, temp_user, delete_user, ROOT  # noqa: E402

kw = json.loads((ROOT / 'mobile/src/data/safety-keywords.json').read_text())
norm = lambda s: re.sub(r'\s+', '', s)
keyword_hit = lambda s: any(k in norm(s) for k in kw)


def outcome(T, t):
    s, r = req('POST', '/functions/v1/classify', {'text': t}, token=T)
    if s != 200:
        return 'error', r
    if keyword_hit(t) or r.get('self_harm'):
        return 'safety', r
    return ('quiet' if r.get('harm_others') else 'celebrate'), r


sets = [('harm', 'quiet'), ('trap', 'celebrate'), ('holdout_harm', 'quiet'), ('holdout_trap', 'celebrate')]
harm = json.loads((ROOT / 'scripts/harm_cases.json').read_text())
groups = {k: harm[k] for k, _ in sets}
if '--no-safety' not in sys.argv:
    sc = json.loads((ROOT / 'scripts/safety_cases.json').read_text())
    groups['self_risk'], groups['self_safe'] = sc['risk'], sc['safe']
    sets += [('self_risk', 'safety'), ('self_safe', 'celebrate')]

T, uid = temp_user()
try:
    for name, want in sets:
        c = Counter()
        for t in groups[name]:
            o, r = outcome(T, t)
            c[o] += 1
            mark = '' if o == want else '  ← ' + o
            print(f"[{name}] {o:9s} cat={r.get('category')} {t}{mark}")
        print(f"== {name}: {dict(c)} (목표 {want})\n")
finally:
    delete_user(uid)
