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
CLIPS = ['garden_idle', 'walk_front', 'walk_side', 'walk_back']  # 마당에서 쓰는 클립 (YardScene FACE_CLIP)

r, g, b, a = json.loads((ROOT / 'design/world/export/v1/manifest.json').read_text())['spaces']['yard']['night']['overlay']
lut = [round(v * (1 - a) + c * a) for c in (r, g, b) for v in range(256)] + list(range(256))  # 알파는 그대로
cm = json.loads((SRC / 'manifest.json').read_text())['clips']
for key in CLIPS:
    c = cm[key]
    src = Image.open(SRC / c['file'])
    frames = [f.convert('RGBA').point(lut) for f in ImageSequence.Iterator(src)]
    assert len(frames) == c['frames'], (key, len(frames), c['frames'])
    out = DST / f'hippo_{key}_night.webp'
    frames[0].save(out, 'WEBP', save_all=True, append_images=frames[1:], duration=round(c['duration_ms'] / c['frames']),
                   loop=0 if c['loop'] else 1, quality=80, method=4)
    print(key, len(frames), os.path.getsize(out) // 1024, 'KB')
