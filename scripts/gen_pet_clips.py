#!/usr/bin/env python3
"""캐릭터 export → 앱 에셋 복사 + mobile/src/data/petClips.ts 생성. 사용: python3 scripts/gen_pet_clips.py [export 폴더]"""
import json, pathlib, shutil, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
src = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'design/character/export/v1')
dst = ROOT / 'mobile/assets/pet'
dst.mkdir(parents=True, exist_ok=True)
m = json.loads((src / 'manifest.json').read_text())
for v in m['clips'].values():
    shutil.copy(src / v['file'], dst / v['file'])
shutil.copy(src / m['clips']['idle']['poster'], dst / m['clips']['idle']['poster'])
lines = ["// 자동 생성: design/character/export/v1/manifest.json → 수정하지 말고 다시 생성 (scripts/gen_pet_clips.py)",
         "export type ClipKey = " + " | ".join(f"'{k}'" for k in m['clips']) + ";",
         "export const PET_ASPECT = %d / %d; // 높이 / 너비" % (m['height'], m['width']),
         "export const PET_CLIPS: Record<ClipKey, { source: number; durationMs: number; loop: boolean }> = {"]
for k, v in m['clips'].items():
    lines.append(f"  {k}: {{ source: require('@/assets/pet/{v['file']}'), durationMs: {v['duration_ms']}, loop: {str(v['loop']).lower()} }},")
lines += ["};", f"export const PET_POSTER = require('@/assets/pet/{m['clips']['idle']['poster']}');", ""]
(ROOT / 'mobile/src/data/petClips.ts').write_text("\n".join(lines))
print('ok', len(m['clips']), 'clips')
