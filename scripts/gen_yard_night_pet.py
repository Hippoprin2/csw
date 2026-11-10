"""마당 밤용 단짝 클립: export 클립에 manifest spaces.yard.night.overlay 색을 자기 픽셀에만(source-atop) 미리 입힘.
앱에서 움직이는 그림 두 장(본체 + 색 덮개)을 겹치면 각자 따로 재생돼 박자가 어긋나서, 밤엔 이 한 장만 그림.
사용 (Pillow 필요): python scripts/gen_yard_night_pet.py  → mobile/assets/pet/hippo_<clip>_night.webp
캐릭터 export나 밤 색이 바뀌면 다시 실행.
"""
import json, os, pathlib
from PIL import Image, ImageSequence

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'design/character/export/v1'
DST = ROOT / 'mobile/assets/pet'
import sys
_cm = json.loads((SRC / 'manifest.json').read_text())
# 마당에서 쓰는 클립: 대기·걷기 + yard_actions 의 모든 동작 (YardScene)
CLIPS = ['garden_idle', 'walk_front', 'walk_side', 'walk_back'] + [
    c for a in _cm.get('yard_actions', {}).values() if isinstance(a, dict) for c in a.get('parts', []) + a.get('eat', [])]
if len(sys.argv) > 1: CLIPS = sys.argv[1:]  # 일부만 다시 만들 때

r, g, b, a = json.loads((ROOT / 'design/world/export/v1/manifest.json').read_text())['spaces']['yard']['night']['overlay']
lut = [round(v * (1 - a) + c * a) for c in (r, g, b) for v in range(256)] + list(range(256))  # 알파는 그대로
cm = json.loads((SRC / 'manifest.json').read_text())['clips']
for key in CLIPS:
    c = cm[key]
    src = Image.open(SRC / c['file'])
    frames, durs = [], []
    for f in ImageSequence.Iterator(src):  # 같은 프레임이 이어지면 인코더가 합쳐 둠 → 프레임별 길이를 그대로 옮김
        frames.append(f.convert('RGBA').point(lut)); durs.append(f.info.get('duration') or round(c['duration_ms'] / c['frames']))
    assert abs(sum(durs) - c['duration_ms']) < 60, (key, sum(durs), c['duration_ms'])
    out = DST / f'hippo_{key}_night.webp'
    frames[0].save(out, 'WEBP', save_all=True, append_images=frames[1:], duration=durs,
                   loop=0 if c['loop'] else 1, quality=80, method=4)
    print(key, len(frames), os.path.getsize(out) // 1024, 'KB')

# 앱용 require 표 (YardScene이 씀)
ts = ["// 자동 생성: scripts/gen_yard_night_pet.py → 수정하지 말고 다시 생성", "export const PET_NIGHT: Record<string, number> = {"]
for key in dict.fromkeys(CLIPS if len(sys.argv) == 1 else []):
    ts.append(f"  {key}: require('@/assets/pet/hippo_{key}_night.webp'),")
ts += ["};", ""]
if len(sys.argv) == 1:
    (ROOT / 'mobile/src/data/petNight.ts').write_text("\n".join(ts))
