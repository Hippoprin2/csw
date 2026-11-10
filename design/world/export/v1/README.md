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

## 마당 (spaces.yard) — 첫 업데이트, 2026-11-10 (세로 화면 + 구역 확장판)
- **좌표 = 큰 캔버스**(`canvas` 2160×3100 px, 1단위 = 400px). 화면은 그 위의 창: 가로 1080 = 카드 너비, 세로 = 카드 높이 × 1080 / 카드 너비(아이폰 15 ≈ 1860). 카드는 공간 탭 아래부터 하단 탭 바 바로 위까지
- 배경은 1080 타일(`tiles[]`, 낮 `file` / 밤 `night_file`) — 화면에 걸친 타일만 그림
- **구역** `walk.zones["1".."4"]`: `rect`·`price`(1 = 0 무료, 2 = 60, 3 = 120, 4 = 풍경만)·`area`·`blocked`·`gate`. 산 구역의 `area`를 합친 곳만 걸음. 안 산 구역은 `locks[z]` 울타리 그림을 그리고, 그 구역이나 문을 탭하면 구역 구매 시트
- **화면 이동** `camera`: 단짝 따라감(부드럽게) + 손가락으로 끌어 둘러보기 → 손 떼고 3초 뒤 단짝에게 복귀. 탭 = 단짝이 그곳으로 걸어감. 화면은 산 구역 범위 + 이웃 잠긴 구역으로 `peek`(260px)까지만
- 그리는 순서는 `draw_order`: 배경 타일 → 잠긴 구역 울타리 → `layer=ground`(피크닉 매트) → `layer=pond`(오리 튜브) → 나무 `tree[단계]` + `layer=sorted` 소품 + `bed_flowers` + 단짝 + 땅 참새를 **sort_y 오름차순**(단짝 키 = 발 y). 열매는 나무를 그린 직후 같은 순서에 그려(나무 앞에 선 단짝이 열매도 가리게) → (물장구 중) `extras.pond_water` → 나비 → 밤 덮개
- 소품은 자기 자리 1개씩(바꿔 끼우기 없음). 가진 것만 그림. 화단 3칸 = `bed_flowers`(spot 0~2 × tulip/sunflower). 지금 소품은 전부 1구역, 2·3구역 소품은 업데이트 때 같은 형식으로 추가
- 추억 나무: `tree[stage-1]` + 그 단계의 `fruits` 좌표마다 `fruit.webp`(80×80)를 가운데 맞춰. 단계 기준은 WORLD.md 7장(기록한 날 10/30/60)
- 손님: `sparrow_perch`(새 모이통 있을 때, 모이통 바로 뒤에) / `sparrow_ground`·`butterfly_open|closed`는 `anchor`를 원하는 점에 두는 움직이는 그림
- 밤(19~06시): 타일은 `night_file`, `night_file` 있는 소품(정원등·텐트)은 그 그림으로, 전부 그린 뒤 `night.overlay` rgba 덮개, 소품 `night_file` 그림만 덮개 위에 다시
- 걷기(텃밭은 `spaces.garden.walk`): 산 구역 `area` 안 + `walk.blocked`·구역 `blocked` 밖 + 가진 소품의 `item_blocked` 밖. 잠긴 구역과 맞닿은 변에서는 70px 떨어져. `interact[id]` = 서는 점·방향·동작. 단짝 발 (fx, fy)에 600×800 클립을 `pet.w×pet.h`로, 가운데 = 발 + `pet.feet_to_center`
- 합성 확인: `scripts/blender/compose_yard_preview.py` (기본 = 낮|밤 화면, `map` = 캔버스 전체, `walk` = 걷기 영역, `own=1,2` = 산 구역) → design/world/yard/yard_v2_*.jpg

## 그 밖
- `thumbs/<items.id>.webp` 상점 썸네일, `icons/produce_<작물>.webp` 수확 바구니, `icons/packet_<작물>.webp` 씨앗 봉투
- `_app_preview.jpg` = 이 파일들만으로 합성한 확인용 화면(앱에서 똑같이 보이면 정상)
