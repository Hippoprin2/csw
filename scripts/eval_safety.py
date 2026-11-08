#!/usr/bin/env python3
"""자해 표현 감지 정확도 확인 (FEATURES.md 5장 출시 전 체크).
키워드(기기 안) / LLM(classify 함수) / 최종(키워드 OR LLM) — 위험 15 · 오탐유도 15 문장.
사용: python3 scripts/eval_safety.py
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, temp_user, delete_user, ROOT  # noqa: E402

kw = json.loads((ROOT / 'mobile/src/data/safety-keywords.json').read_text())
cases = json.loads((ROOT / 'scripts/safety_cases.json').read_text())
norm = lambda s: re.sub(r'\s+', '', s)
keyword_hit = lambda s: any(k in norm(s) for k in kw)

T, uid = temp_user()
try:
    stats = {m: {'tp': 0, 'fn': 0, 'fp': 0, 'tn': 0} for m in ('keyword', 'llm', 'final')}
    for label, texts in cases.items():
        for t in texts:
            s, r = req('POST', '/functions/v1/classify', {'text': t}, token=T)
            llm = r.get('self_harm') if s == 200 else None
            k = keyword_hit(t)
            final = bool(llm) or k  # 앱 규칙: 키워드 또는 LLM 중 하나라도 걸리면 안내 (안전한 쪽)
            for m, v in (('keyword', k), ('llm', bool(llm)), ('final', final)):
                key = ('tp' if v else 'fn') if label == 'risk' else ('fp' if v else 'tn')
                stats[m][key] += 1
            flag = '' if (final == (label == 'risk')) else '  ← 틀림'
            print(f"[{label}] kw={int(k)} llm={llm} cat={r.get('category')}  {t}{flag}")
    print()
    for m, st in stats.items():
        print(f"{m:8s} 위험 감지 {st['tp']}/15 · 오탐 {st['fp']}/15")
finally:
    delete_user(uid)
