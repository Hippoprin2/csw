#!/usr/bin/env python3
"""마당 소품·추억 나무 탭 판정용 알파 격자 → mobile/src/data/yardHit.ts
그림의 투명한 여백을 탭해도 소품으로 잡히지 않게 (참고 구현 design/yard_test 의 픽셀 판정을 앱용으로 미리 계산).
사용 (Pillow 필요): python scripts/gen_yard_hit.py   — 마당 그림이 바뀌면(gen_world.py 뒤) 다시 실행
"""
import json, pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'design/world/export/v1'
CELL = 12  # 캔버스 px
y = json.loads((SRC / 'manifest.json').read_text())['spaces']['yard']
ents = [(e['id'], e) for e in y['items']] + [(f"tree{t['stage']}", t) for t in y['tree']]
out = ["// 자동 생성: scripts/gen_yard_hit.py → 수정하지 말고 다시 생성",
       f"// 소품 그림 위 {CELL}px 칸마다 불투명(1)/투명(0). 행 우선 문자열",
       f"export const HIT_CELL = {CELL};",
       "export const YARD_HIT: Record<string, { cols: number; rows: number; bits: string }> = {"]
for key, e in ents:
    im = Image.open(SRC / e['file']).convert('RGBA')
    cols, rows = max(1, round(e['w'] / CELL)), max(1, round(e['h'] / CELL))
    a = im.getchannel('A').resize((cols, rows), Image.BOX)
    bits = ''.join('1' if a.getpixel((c, r)) > 50 else '0' for r in range(rows) for c in range(cols))
    out.append(f"  {key}: {{ cols: {cols}, rows: {rows}, bits: '{bits}' }},")
out += ["};", ""]
(ROOT / 'mobile/src/data/yardHit.ts').write_text("\n".join(out))
print('ok', len(ents))
