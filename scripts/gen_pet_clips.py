#!/usr/bin/env python3
"""캐릭터 export → 앱 에셋 복사 + mobile/src/data/petClips.ts 생성. 사용: python3 scripts/gen_pet_clips.py [export 폴더] [--new-only]
--new-only: 앱 폴더에 없는 클립만 복사(이미 압축한 클립을 원본으로 덮지 않음) → 그 뒤 compress_pet_clips.py <새 파일들>"""
import json, pathlib, shutil, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith('--')]
NEW_ONLY = '--new-only' in sys.argv
src = ROOT / (args[0] if args else 'design/character/export/v1')
dst = ROOT / 'mobile/assets/pet'
dst.mkdir(parents=True, exist_ok=True)
m = json.loads((src / 'manifest.json').read_text())
for v in m['clips'].values():
    if NEW_ONLY and (dst / v['file']).exists():
        continue
    shutil.copy(src / v['file'], dst / v['file'])
    print('copied', v['file'])
shutil.copy(src / m['clips']['idle']['poster'], dst / m['clips']['idle']['poster'])
lines = ["// 자동 생성: design/character/export/v1/manifest.json → 수정하지 말고 다시 생성 (scripts/gen_pet_clips.py)",
         "export type ClipKey = " + " | ".join(f"'{k}'" for k in m['clips']) + ";",
         "export const PET_ASPECT = %d / %d; // 높이 / 너비" % (m['height'], m['width']),
         "// canvas·feet: 600x800보다 큰 클립(탭 반응 등) = 같은 px 배율로 canvas 크기에 그리고 feet를 대기 클립 발 위치에 맞춤",
         "export const PET_CLIPS: Record<ClipKey, { source: number; durationMs: number; loop: boolean; canvas?: [number, number]; feet?: [number, number] }> = {"]
for k, v in m['clips'].items():
    extra = ''.join(f", {kk}: {json.dumps(v[kk])}" for kk in ('canvas', 'feet') if kk in v)
    lines.append(f"  {k}: {{ source: require('@/assets/pet/{v['file']}'), durationMs: {v['duration_ms']}, loop: {str(v['loop']).lower()}{extra} }},")
lines += ["};", f"export const PET_FPS = {m['fps']};",
          "// 마당 자리 동작 (manifest yard_actions): parts = in/loop/out 또는 한 번, stand = 발 위치(마당 캔버스 px)",
          "export type YardAction = { parts: ClipKey[]; stand: [number, number]; enter?: [number, number]; eat?: ClipKey[] };",
          "export const PET_YARD_ACTIONS: Record<string, YardAction> = {"]
for k, v in m.get('yard_actions', {}).items():
    if not isinstance(v, dict): continue
    o = {kk: v[kk] for kk in ('parts', 'stand', 'enter', 'eat') if kk in v}
    lines.append(f"  {k}: {json.dumps(o)},")
lines += ["};", "// 방 단짝 탭 반응 (manifest tap_reactions): 무작위 하나, mirror 가능한 클립은 50% 좌우 뒤집기",
          f"export const PET_TAP_REACTIONS: ClipKey[] = {json.dumps(m.get('tap_reactions', {}).get('clips', []))};",
          f"export const PET_FEET: [number, number] = {json.dumps(m.get('feet', [303, 713]))};"]
lines += ["", f"export const PET_POSTER = require('@/assets/pet/{m['clips']['idle']['poster']}');", ""]
(ROOT / 'mobile/src/data/petClips.ts').write_text("\n".join(lines))
print('ok', len(m['clips']), 'clips')
