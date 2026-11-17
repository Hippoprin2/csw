#!/usr/bin/env python3
"""번역 준비: 앱 코드(mobile/src)의 한글 문자열 개수를 파일별로 센다 (읽기만 함).
사용: python3 scripts/i18n_inventory.py [--top N]
- 문자열 = 따옴표/백틱 안 또는 JSX 텍스트 중 한글이 든 것 (주석 제외)
- legal.ts 는 원문 문서에서 생성되므로 따로 표시 (번역은 docs/legal/<lang>/ 에서)
"""
import re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent / 'mobile' / 'src'
HAN = re.compile(r'[가-힣]')
STR = re.compile(r"""(['"`])((?:\\.|(?!\1).)*?)\1""")
JSX = re.compile(r'>([^<>{}]*[가-힣][^<>{}]*)<')
top = int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 25
rows, total, uniq = [], 0, set()
for p in sorted(ROOT.rglob('*.ts*')):
    src = p.read_text(encoding='utf-8')
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = '\n'.join(l.split('//')[0] if '://' not in l else l for l in src.splitlines())
    found = [m.group(2) for m in STR.finditer(src) if HAN.search(m.group(2))]
    found += [m.group(1).strip() for m in JSX.finditer(src)]
    if found:
        rel = str(p.relative_to(ROOT))
        rows.append((len(found), rel))
        if not rel.endswith('legal.ts'):
            total += len(found); uniq.update(found)
rows.sort(reverse=True)
print(f'파일 {len(rows)}개 / 한글 문자열 {total}개 (중복 제외 {len(uniq)}개, legal.ts 제외)')
for n, f in rows[:top]:
    print(f'{n:5d}  {f}' + ('  (생성 파일 — docs/legal 에서 번역)' if f.endswith('legal.ts') else ''))
