# 단짝(하마) 앱 에셋 v1

만든 곳: 캐릭터 스레드 (2026-11-08). 앱에 붙이는 작업은 앱 개발 스레드가 한다. 대상 파일은 `mobile/src/ui/Pet.tsx`.

## 파일
- `hippo_<key>.webp`: 움직이는 WebP, 600x800, 투명 배경, 24fps. 전체 약 7.5MB.
- `hippo_<key>_poster.png`: 첫 프레임(로딩 중이나 정지 화면용)
- `manifest.json`: 프레임 수, 길이(ms), 반복 여부

## key (앱 categories.ts 기준)
- 반복: `idle`(대기), `sit_loop`(곁에 앉기 유지)
- 한 번 재생: `tidy`(쓱싹+빗자루), `move`(점프+헤드밴드·땀), `study`(책상+공책), `work`(책상+노트북), `eat`(냠냠+군고구마), `care`(기지개+회전+반짝이), `people`(손 흔들기+편지), `cheer`(만세+점프+색종이)
- 곁에 앉기(자해 표현 대응, 조용한 동작): `sit_in`(앉기, 앉은 채로 끝남) → `sit_loop`(반복) → `sit_out`(일어나서 대기 자세로 끝남)
- `work`는 새 카테고리다. '공부·일'을 공부(study)와 업무(work)로 나눴다(STATUS.md 결정 사항). 분류 로직과 문구 추가가 필요하다.

## 재생 규칙
- 한 번 재생하는 동작은 모두 대기 자세로 시작해서 대기 자세로 끝난다. 그래서 idle → 동작 → idle로 바로 이어 붙여도 튀지 않는다.
- 동작이 끝난 시점은 `duration_ms` 타이머로 판단한다. 디코더의 반복 횟수 설정(loop=1)은 플랫폼마다 다르게 동작할 수 있다.
- 모든 클립의 카메라와 크기가 같다. 같은 크기와 같은 위치에 겹쳐서 바꿔 끼우면 된다. study/work 클립은 동작 안에서 카메라가 올라갔다 내려오고, 시작과 끝 프레임은 idle과 같다.
- 실기기에서 확인할 것: expo-image의 움직이는 WebP 재생, 메모리 사용량, 저가 안드로이드 성능.

## 다시 만들기
- 렌더: `scripts/blender/render_actions.sh <clip...>` (idle은 `rig_idle.py`, cheer는 `anim_cheer.py`)
- 내보내기: `python scripts/export_app_assets.py` (Pillow 필요)
