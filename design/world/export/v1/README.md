# 공간 그림 export v1 (앱용)

만든 스크립트: `scripts/blender/export_world.py` (다시 만들기: `blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/export_world.py -- $PWD/design/world/export/v1 all` → PNG 생성 후 WebP 변환은 docs/WORLD.md 참고)
위치·순서는 전부 `manifest.json`. 단위는 캔버스 px(1080×1080) → 앱은 **카드 너비 / 1080** 배율로 모두 곱한다.

## 방 (spaces.room)
- `room/background.webp` 먼저(무료 기본 방 + 달력 포함, 불투명)
- `items[]`: 가진 소품 중 자리(slot)에 놓인 것만, `z` 오름차순으로 (x, y, w, h)에 그린다. 그림자도 그림 안에 들어 있음
- 단짝: `pet.z` 순서에 끼워서 그린다. 캐릭터 클립(600×800)을 `pet.w × pet.h`로 줄여 `pet.x, pet.y`에. (단짝 키 = 카드 높이의 약 37%)
- 같은 자리 하나만: wall_top(가랜드/전구줄), lean(이젤/기타), bedside(라디오/어항), front_center(쿠션/다람쥐), sill_vase(튤립/해바라기 꽃병)
- `harvest_*`: 그 작물을 처음 수확하면 창턱에 생김(영구)

## 텃밭 (spaces.garden)
- `garden/background.webp` → 단짝(garden_idle / garden_cheer 클립, `pet` 위치) → 작물 3칸 순서
- 작물 그림은 모두 600×600 같은 크기·같은 기준점: `plots[i].crop_x, crop_y`에 그대로. 파일: `mound`(심음) / `<작물>_<1|2|3>` / `<작물>_<1|2|3>_doze`
- `plots[i].tap_rect` = 밭 칸 터치 영역. 진행 점·Zzz·반짝임은 앱 UI

## 그 밖
- `thumbs/<items.id>.webp` 상점 썸네일, `icons/produce_<작물>.webp` 수확 바구니, `icons/packet_<작물>.webp` 씨앗 봉투
- `_app_preview.jpg` = 이 파일들만으로 합성한 확인용 화면(앱에서 똑같이 보이면 정상)
