#!/usr/bin/env python3
"""공간 export → 앱 에셋 복사 + mobile/src/data/world.ts 생성.
사용: python3 scripts/gen_world.py [export 폴더, 기본 design/world/export/v1]
공간 스레드가 다시 내보내면 이것만 다시 돌리면 된다."""
import json, pathlib, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'design/world/export/v1')
dst = ROOT / 'mobile/assets/world'
m = json.loads((src / 'manifest.json').read_text())

files = set()
room, garden = m['spaces']['room'], m['spaces']['garden']
files.add(room['background']); files.add(garden['background'])
files.update(i['file'] for i in room['items'])
jc = room.get('jar_cabinet')
if jc: files.update([jc['jar_back']['file'], jc['jar_front']['file'], jc['glass']['file']])
files.update(garden['crops'].values())
files.update(m['shop_thumbnails'].values())
files.update(m['icons'].values())
yard = m['spaces'].get('yard')
yard_files = set()
if yard:
    for t in yard['tiles']: yard_files.update([t['file'], t['night_file']])
    yard_files.update(l['file'] for l in yard['locks'].values())
    for e in yard['items']:
        yard_files.add(e['file'])
        if e.get('night_file'): yard_files.add(e['night_file'])
    yard_files.update(e['file'] for e in yard['bed_flowers'])
    yard_files.update(e['file'] for e in yard['tree'])
    yard_files.add(yard['fruit']['file'])
    yard_files.update(e['file'] for e in yard['extras'].values())
    files.update(yard_files)
if dst.exists():
    shutil.rmtree(dst)
for f in sorted(files):
    (dst / f).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / f, dst / f)

req = lambda f: f"require('@/assets/world/{f}')"
L = [f"// 자동 생성: {src.relative_to(ROOT)}/manifest.json → 수정하지 말고 다시 생성 (scripts/gen_world.py)",
     "// 단위: 캔버스 px (정사각형). 앱은 (카드 너비 / CANVAS) 배율로 곱한다.",
     "// CANVAS = 카드 한 장(정사각형 창)의 폭. 방은 더 넓은 캔버스(ROOM.width)를 이 창으로 좌우로 끌어 본다",
     f"export const CANVAS = {room.get('view', {}).get('w', room['canvas'][0])};",
     "export type Rect = { x: number; y: number; w: number; h: number };",
     "export type PetPlace = Rect & { z: number };",
     "",
     "export const ROOM = {",
     f"  background: {req(room['background'])},",
     f"  width: {room['canvas'][0]}, height: {room['canvas'][1]},",
     f"  view: {json.dumps({k: v for k, v in room.get('view', {'w': room['canvas'][0], 'start_x': 0, 'min_x': 0, 'max_x': 0}).items() if k != 'note'})},",
     f"  pet: {{ x: {room['pet']['x']}, y: {room['pet']['y']}, w: {room['pet']['w']}, h: {room['pet']['h']}, z: {room['pet']['z']} }} as PetPlace,",
     "  // z 오름차순으로 그린다. 같은 slot은 하나만 (방 소품은 owned.placed, sill_vase는 튤립/해바라기 중 하나)",
     "  items: ["]
for i in room['items']:
    L.append(f"    {{ id: '{i['id']}', slot: '{i['slot']}', z: {i['z']}, x: {i['x']}, y: {i['y']}, w: {i['w']}, h: {i['h']}, source: {req(i['file'])} }},")
if jc:
    L += ["  ],",
          "  // 유리장: 닫힌 병 최근 12개 (슬롯 0 = 그중 가장 오래된 병). 병 뒤 → 구슬 → 병 앞 → 유리 순서",
          "  jarCabinet: {",
          f"    jarBack: {{ source: {req(jc['jar_back']['file'])}, w: {jc['jar_back']['w']}, h: {jc['jar_back']['h']} }},",
          f"    jarFront: {{ source: {req(jc['jar_front']['file'])}, w: {jc['jar_front']['w']}, h: {jc['jar_front']['h']} }},",
          f"    glass: {{ source: {req(jc['glass']['file'])}, x: {jc['glass']['x']}, y: {jc['glass']['y']}, w: {jc['glass']['w']}, h: {jc['glass']['h']} }},",
          "    slots: ["]
    for sl in jc['slots']:
        L.append(f"      {{ back: {sl['back']}, front: {sl['front']}, marbles: {sl['marbles']}, tap: {sl['tap']} }},")
    L += ["    ] as { back: number[]; front: number[]; marbles: number[]; tap: number[] }[],", "  },"]
else:
    L += ["  ],"]
L += ["};", "", "export const GARDEN = {",
      f"  background: {req(garden['background'])},",
      f"  pet: {{ x: {garden['pet']['x']}, y: {garden['pet']['y']}, w: {garden['pet']['w']}, h: {garden['pet']['h']}, z: 0 }} as PetPlace,",
      f"  cropSize: {garden['crop_image_size'][0]},",
      "  // 그리는 순서: 배경 → 단짝 → 작물(0,1,2) → UI. 앱 plots.slot = index + 1",
      "  plots: ["]
for p in garden['plots']:
    t = p['tap_rect']
    L.append(f"    {{ cropX: {p['crop_x']}, cropY: {p['crop_y']}, cx: {p['crop_center'][0]}, cy: {p['crop_center'][1]}, tap: {{ x: {t[0]}, y: {t[1]}, w: {t[2]}, h: {t[3]} }} }},")
L += ["  ],", "  crops: {"]
for k, f in sorted(garden['crops'].items()):
    L.append(f"    {k}: {req(f)},")
L += ["  } as Record<string, number>,", "};", "", "export const THUMBS: Record<string, number> = {"]
for k, f in sorted(m['shop_thumbnails'].items()):
    L.append(f"  {k}: {req(f)},")
L += ["};", "", "export const ICONS: Record<string, number> = {"]
for k, f in sorted(m['icons'].items()):
    L.append(f"  {k}: {req(f)},")
L += ["};", ""]
(ROOT / 'mobile/src/data/world.ts').write_text("\n".join(L))

# 마당: 큰 캔버스 데이터(JSON 그대로) + 그림 파일 → require 표 (mobile/src/data/yard.ts)
if yard:
    Y = [f"// 자동 생성: {src.relative_to(ROOT)}/manifest.json spaces.yard → 수정하지 말고 다시 생성 (scripts/gen_world.py)",
         "// 좌표 = 마당 큰 캔버스 px (README '마당' 절). 그림은 YARD_IMG[file]",
         "import type { YardData } from './yardTypes';",
         "",
         f"export const YARD: YardData = {json.dumps(yard, ensure_ascii=False)};",
         "",
         "export const YARD_IMG: Record<string, number> = {"]
    for f in sorted(yard_files):
        Y.append(f"  '{f}': {req(f)},")
    Y += ["};", ""]
    (ROOT / 'mobile/src/data/yard.ts').write_text("\n".join(Y))
print('ok', len(files), 'files')
