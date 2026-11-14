#!/usr/bin/env python3
"""docs/legal/{privacy,terms}.md → mobile/src/data/legal.ts (앱 안에서 바로 읽는 약관·처리방침).
작성 메모(> 로 시작하는 줄)는 빼고, 표는 '항목: 값' 줄로 바꾼다. 문서를 고치면 다시 실행.
도메인이 생겨 EXPO_PUBLIC_PRIVACY_URL / TERMS_URL 이 있으면 앱은 그 주소를 연다(이 데이터는 대신 쓰는 것)."""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def convert(md: str):
    out, header = [], None
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith('>'):
            continue
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c):
                continue
            if header is None:
                header = cells
                continue
            parts = [f'{h}: {c}' if h else c for h, c in zip(header, cells) if c]
            out.append(['li', ' / '.join(parts)])
            continue
        header = None
        line = re.sub(r'\*\*(.+?)\*\*', r'\1', line).replace('`', '')
        if not line.strip():
            continue
        if line.startswith('# '):
            out.append(['h1', line[2:]])
        elif line.startswith('## ') or line.startswith('### '):
            out.append(['h2', line.lstrip('#').strip()])
        elif re.match(r'^\s*[-*] ', line):
            out.append(['li', re.sub(r'^\s*[-*] ', '', line)])
        else:
            out.append(['p', line.strip()])
    return out


docs = {k: convert((ROOT / f'docs/legal/{k}.md').read_text()) for k in ('privacy', 'terms')}
ts = ['// 자동 생성: scripts/gen_legal.py (docs/legal/*.md) — 직접 고치지 말고 문서를 고친 뒤 다시 생성',
      "export type LegalBlock = ['h1' | 'h2' | 'p' | 'li', string];",
      'export const LEGAL: Record<\'privacy\' | \'terms\', LegalBlock[]> = ' + json.dumps(docs, ensure_ascii=False) + ';', '']
(ROOT / 'mobile/src/data/legal.ts').write_text('\n'.join(ts))
print({k: len(v) for k, v in docs.items()})
