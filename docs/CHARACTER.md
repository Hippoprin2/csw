# 캐릭터 디자인

담당 스레드: 캐릭터 디자인

## 결정 사항
- 동물 컨셉 (2026-10-19)
- 프로토타입 임시 캐릭터: 꼬마하마
- 권리 확보(저작권·상표·디자인, AI 생성 이슈) → docs/CHARACTER_IP.md (2026-11-23)
- **캐릭터 이름: 하몽 (HAMONG) 확정** (대표, 2026-11-23). 후보 하몬은 16·09류에 같은 발음 등록이 있어 제외 → CHARACTER_IP.md 7장

## 시도 기록
- 2026-11-08: 대표가 OpenAI `gpt-image-2.6-sunburst`로 생성 시도 (동숲풍 3D, 베이지 하마, 무민 닮음, 졸린 눈, 옷 없음).
  - 비용(공식 단가 = gpt-image-2와 동일, 출력 $30/1M 토큰): 1024² 1장 기준 low ≈ $0.006, medium ≈ $0.05, high ≈ $0.21. quality="auto"면 high로 갈 수 있음.
  - 캐릭터 4종 × 시안 10장씩 high로 해도 ≈ $8~9. 진짜 비용은 동작 7종 등 일관성 맞추는 반복 작업(참조 이미지 편집 시 입력 토큰 추가).
  - 주의: gpt-image-2 계열은 투명 배경 미지원으로 알려짐 → 앱 에셋은 배경 제거 후처리 필요할 수 있음.

- 2026-11-08: 하마 v1 앞/뒤 이미지 확보 → design/character/hippo_v1_front.png, hippo_v1_back.png. 동물은 하마 1종으로 가도 됨(대표).
  - 일관성 방안 제안: 2D로 매번 생성하지 말고 '3D 모델 1개'를 원본으로 삼는다. 턴어라운드 이미지 → AI 이미지→3D(Tripo/Meshy/Hunyuan3D) → 자동 리깅 → Blender로 동작 7종 → 투명 PNG 시퀀스로 렌더. 2D 편집(참조 이미지)은 정지 일러스트용 보조.
  - 리깅을 위해 팔이 몸에서 살짝 떨어진 정면/측면/뒷면 A포즈 시트를 다시 뽑아야 함.
  - Hunyuan3D는 한국 사용 불가(라이선스 제외 지역) → TRELLIS.2(MS, MIT)로 대체 검토.
    - 경로: ① HF Space microsoft/TRELLIS.2 (무료 ZeroGPU, 일일 할당량) ② 이 맥(M4/24GB)에서 trellis-silicon(MPS 포팅) 로컬 실행 ③ 클라우드 GPU 대여.
    - 한계: 단일 이미지 입력(앞/옆/뒤 동시 입력 아님), 출력은 고밀도 메시(수십만 버텍스) → 리깅 전 Blender에서 단순화/리토폴로지 필요.
    - 라이선스: TRELLIS.2 MIT지만 파이프라인 내 배경제거 RMBG-2.0은 비상업(CC BY-NC) → 배경 미리 제거한 이미지로 넣는 게 안전.
  - 리깅/애니 도구: Blender 메인 + Mixamo는 무료 보조 테스트. Mixamo는 사람형 이족 전용·사실적 모션캡처 라이브러리라 머리 크고 팔다리 짧은 하마에는 마커/변형 실패 위험, 동작 7종(통통 튀기, 찌부/늘어남 등)도 커스텀이라 결국 Blender 필요. 뼈 10~15개 단순 리그면 Blender 스크립트로 충분.
  - 2026-11-08: OpenAI 키(서비스 계정, CSW 프로젝트) → .env.local(600, gitignore). 저장 스크립트 scripts/set_openai_key.sh.
  - 2026-11-08: A포즈 턴어라운드 v1 생성(images/edits, v1 앞/뒤 참조, medium, 1536x1024, ≈$0.06) → design/character/apose/hippo_apose_v1.png, 정면 크롭 hippo_apose_v1_front.png (TRELLIS 입력용). 3면 일관성 양호, 팔 분리됨, 꼬리 생김.
  - 2026-11-08: A포즈 v1 시안 대표 OK. RMBG-2.0 접근 신청 안 함(CSW는 상업용 → 비상업 조건 위반). 대신 배경 제거는 BiRefNet(MIT)로 하고 투명 PNG를 넣는다(TRELLIS.2 preprocess_image는 알파 있으면 배경 제거 생략). 로컬 설치 시 rembg 설정을 RMBG-2.0 → ZhengPeng7/BiRefNet으로 교체. DINOv3(Meta)는 신청 OK.
  - 2026-11-08: 정면 투명 배경 PNG → design/character/apose/hippo_apose_v1_front_transparent.png. AI 모델 없이 단색 회색 배경 색상 키(Pillow/numpy/scipy) → 라이선스 이슈 없음. 배경이 단색이면 이 방식으로 충분. HF Space는 hippocap 브라우저에서 로그인 403 → 대표 브라우저에서 실행.
  - 2026-11-08: TRELLIS.2 Space 결과 GLB(1024, decimation 100k) → design/character/3d/hippo_trellis_v1.glb (57,776 verts). Blender 5.2.3 설치. 정리본 hippo_v1_clean.glb: 중복 버텍스 병합(UV 이음새에서 메시가 갈라져 있어 그냥 스무딩하면 금이 감) → Shade Smooth + Corrective Smooth(only smooth, 12회) → 각진 면 해결. 렌더 renders/compare_raw_vs_clean.png. 스크립트 scripts/blender/clean_model.py, render_turnaround.py.
    - 남은 문제: 눈(텍스처라 흐릿·가장자리 거침, 시안보다 눈동자 표현 약함), 색이 시안보다 주황/갈색 쪽, 턱 아래 어두운 얼룩. 다음: 눈 데칼 교체 → 별도 눈/눈꺼풀.
  - 2026-11-08: 대표 결정 → 눈은 별도 부품, 꼬리는 본체와 같은 크림 베이지.
  - 2026-11-08: hippo v2 → design/character/3d/v2/ (hippo_v2.blend = 편집 원본, hippo_v2.glb, hippo_v2_basecolor.png). 스크립트 scripts/blender/build_hippo_v2.py, 실행 run_v2.sh [눈꺼풀 각도].
    - 텍스처: 3색 팔레트로 평탄화(본체 크림 베이지 #F2CFA6, 귀 안 분홍, 눈썹/콧구멍 진갈색) → 얼룩/주황빛 제거. 그려진 눈은 정면 레이캐스트로 지움. 꼬리 면을 본체 색으로.
    - 눈 부품(좌우): Eye_Ball(흰자), Eye_Iris(갈색 홍채), Eye_Highlight, Eye_Lid(반구 눈꺼풀)+Eye_Lash(속눈썹 라인). 눈꺼풀은 빈 객체 Lid.L/R의 X 회전으로 깜빡임(-5° 기본 졸린 눈, 70° 감은 눈 확인).
    - 렌더: renders/v2_sheet.png, v2_face.png, v2_blink_test.png. 주의: GLB 임포트 이미지의 pixels를 고쳐도 export에 반영 안 됨 → 저장 후 images.load로 다시 연결.
    - 다음: 리깅(뼈 10~15개) → 동작 7종.
  - 2026-11-08: v2 3D 눈 부품은 대표 피드백 "너무 이상함" → 폐기. 시안처럼 '그려진 눈'으로 v3: 2D 눈 데칼(진한 베이지 눈두덩 + 크림 흰자 + 눈꺼풀에 잘린 갈색 홍채)을 얼굴 표면 복사 셸(+1.2mm)에 정면 투영 UV로 입힘. 깜빡임 = 데칼 이미지 교체(eyes_open/eyes_closed). 표정 추가도 이미지 1장씩.
    - 파일: design/character/3d/v3/ (hippo_v3_open/closed .blend/.glb, decals/), 렌더 renders/v3_sheet.png, v3_face_open_closed.png. 스크립트 draw_eye_decals.py, build_hippo_v3.py, run_v3.sh.
    - 교훈: 이 캐릭터 스타일(동숲/무민풍)은 입체 눈알보다 평면 데칼이 맞음.
  - 2026-11-08: 대표 "시안이랑 똑같게" → v4: 시안 이미지 픽셀을 그대로 얼굴에 투영(눈+눈두덩+눈썹+콧구멍). 홍채 위치 기준 닮음변환(시안→렌더 scale 1.254), 부드러운 타원 마스크, 경계 피부색을 본체색에 맞춤. 정면은 시안과 거의 동일. 파일 design/character/3d/v4/ (hippo_v3_open.blend/.glb, decals/eyes_open.png), 비교 renders/v4_vs_concept.png. 스크립트 concept_eye_decal.py, run_v4.sh (build_hippo_v3.py를 DECAL_V4=1로 재사용).
    - 남은 것: 감은 눈/표정용 이미지(시안 스타일로 OpenAI 편집 생성 → 같은 방식 투영), 귀 안쪽 얼룩, 콧구멍 주변 옅은 음영(메시 굴곡).
  - 2026-11-08: **대표 확정: v4 얼굴(시안 투영)**. 감은 눈 표정: 시안 정면을 1024x1536로 패딩 → OpenAI images/edits(눈만 감게, 나머지 동일, medium ≈$0.04) → 패딩 제거 + bbox 정렬(시안과 bbox 1px 이내) → expressions/closed_front.png → 같은 투영(iris 앵커 고정 인자) → v4/hippo_v3_closed.*, decals/eyes_closed.png. 비교 renders/v4_open_closed.png. 스크립트 run_v4_closed.sh. 표정 추가도 같은 방식.
    - 다음: 뼈대(10~15개) + 동작 샘플 1개.
  - 2026-11-08: 리깅 + 대기 동작 샘플 → design/character/3d/rig/ (hippo_rig_idle.blend/.glb, idle_frames/ 투명 PNG 48장 @24fps 2초 루프, idle_preview.mp4/.gif, idle_keyframes.png). 스크립트 rig_idle.py, stress_pose.py.
    - 뼈 10개: root, body, head, ear.L/R, arm.L/R, leg.L/R, tail. 가중치는 자동(bone heat) 대신 영역 기반 스크립트 가중치(부드러운 경계) → TRELLIS 메시에서도 안정. 과장 포즈 테스트(renders/rig_stress.png) 찢김 없음, 얼굴 데칼은 head 뼈에 붙어 따라감.
    - 대기 동작: 숨쉬기(body 스케일), 머리 살짝 흔들림, 팔 흔들림, 꼬리 살랑, 19f 왼쪽 귀 쫑긋, 34~37f 깜빡임(데칼 open/closed 믹스, CONSTANT 보간).
    - 다음: 공통 동작 7종(GAME_DESIGN.md) 하나씩. 앱 포맷 결정(PNG 시퀀스 vs GLB).
  - 2026-11-08: 대표 반응 "너무 귀엽다" → 대기 동작 OK. 공통 동작 1번 '만세 + 점프'(그 밖의 승리) → rig/hippo_cheer_jump.blend, cheer_frames/ 투명 PNG 40장(1.7초, 1회성, 끝은 대기 자세), cheer_preview.mp4(대기→만세→대기). 스크립트 anim_cheer.py.
    - 동작: 웅크림 → 점프(팔 위·바깥 78° + 팔 1.4배 늘림, 공중에서 다리 접기, 감은 눈=행복) → 찌부 착지 → 팔 흔들기 → 복귀. 귀는 늦게 따라와 출렁.
    - 팔이 짧고 머리가 넓어서 팔을 수직으로 올리면 머리에 가려짐 → 위·바깥 대각선 + 만화식 늘림이 맞음. 팔 회전은 월드축 기준(본 로컬축은 롤 때문에 예측 불가) → wq() 헬퍼.
    - 팔 가중치 경계를 |x| 0.195~0.225로 좁힘(이전 값은 팔 올릴 때 옆구리가 같이 끌려옴). 모든 동작 카메라 통일(ortho 1.45, 중심 z 0.07).
    - 남은 동작 6종: 쓱싹, 점프, 고개 끄덕, 냠냠, 기지개+회전, 손 흔들기. 소품은 동작 확정 후.
  - 2026-11-08: 만세 영상 중간 색 바뀜 원인 = 만세 렌더만 Blender 기본 색 변환(AgX), 대기는 Standard. anim_cheer.py에 Standard 고정 후 재렌더 → 대기/만세 첫·끝 프레임 색 동일(210,178,143) 확인. 규칙: 모든 동작 스크립트는 view_transform=Standard.
  - 2026-11-08: 나머지 공통 동작 6종 v1 → rig/hippo_{sweep,hop,nod,eat,stretch_spin,wave}.blend, *_frames/ 투명 PNG, *_preview.mp4, *_keyframes.png. 7종 모음 share/hippo_7actions_v1.mp4(대기 사이사이). 스크립트 anim_actions.py <rig_dir> <action>, render_actions.sh.
    - 쓱싹 48f(팔 앞으로 모아 좌우 + 몸 기울기/비틀기), 점프 40f(2회), 끄덕 44f(3회 + 끝 깜빡), 냠냠 52f(두 손 앞 + 씹기 + 감은 눈), 기지개+회전 60f(팔 쭉 + 360° 회전), 손 흔들기 52f(오른팔).
    - 함정: 루트 360° 회전을 쿼터니언으로 키 잡으면 240°가 -120°로 돌아감 → 루트만 오일러(Y축) 사용.
    - 한계: 팔이 짧아 냠냠 때 손이 입까지 안 닿음(배 앞) → 주먹밥 소품을 손에 들려서 해결 예정.
  - 2026-11-08 대표 피드백 반영 v2: 점프 팔을 위아래 → 앞뒤 흔들기(팔을 몸 쪽으로 30° 내린 뒤 월드 X축으로 스윙, 회전 순서 YXZ. 팔이 옆으로 뻗어 있어 X축만 돌리면 비틀리기만 함). 냠냠에 군고구마 소품(스크립트 생성 메시: 가로로 누운 반 갈린 고구마, 윗면 노란 속살 #FAC740 계열, 아랫면 자주빛 껍질, 들쭉날쭉 경계) — 두 손 위에 걸쳐 들고, 3번 베어 물 때마다 짧아짐, 시작/끝에 나타났다 사라짐. share/hippo_eat_sweetpotato_v2.mp4, hippo_hop_v2.mp4.
  - 재사용성(대표 질문): 동작은 뼈 이름(10개) + 월드축 회전으로 저장돼서, 같은 뼈 구조의 이족 통통 캐릭터면 그대로 재사용 가능. 단 rig_idle.py의 뼈 위치·가중치 경계가 하마 좌표로 하드코딩 → 2번째 캐릭터 때 bbox 비율 기준으로 일반화 필요(반나절). 체형이 다르면(긴 목, 네발) 동작 값 조정 필요.
  - 2026-11-08: 소품 6종 추가(대표 OK "좋아") → scripts/blender/props.py(전부 스크립트 생성, 외부 에셋 없음 → 라이선스 이슈 없음). 만세=색종이 46조각(정점에서 터져 떨어짐), 쓱싹=빗자루(오른손), 점프=땀방울 4개(정점마다), 끄덕=펼친 책(두 손), 기지개+회전=반짝이 12개(노랑/분홍/하늘), 손 흔들기=하트 편지(흔드는 손). 손에 드는 소품은 뼈 자식으로 붙여 동작을 따라가고, 등장/퇴장은 스케일 0↔1이라 끝 자세는 대기와 동일. 모음 share/hippo_7actions_props_v2.mp4, 스틸 hippo_7actions_props_sheet.png.
    - 함정: 쓱싹은 팔 늘림(scale)을 빼야 함(뼈 자식 소품이 같이 늘어남). 색종이 시작점이 높으면 화면 밖(ortho 1.45 기준 위 끝 z≈0.8) → z 0.42에서 시작.
  - 2026-11-08 대표 피드백 v3: 점프에 헤드밴드(코랄 + 흰 줄, 머리 표면 레이캐스트로 이마에 맞춤, head 뼈에 붙음, 시작/끝 팝). 땀방울은 눈물처럼 보여서 화면 왼쪽 눈썹 높이 1개 + 오른쪽 볼 높이 1개로, 얼굴 실루엣 바깥에서 바깥쪽으로 튐. 공부·일 동작을 '고개 끄덕' → '공책에 쓰기'(write, 56f)로 교체: 공책(파란 표지, 스프링, 줄)을 두 손에 걸쳐 들고, 연필 끝이 페이지에 닿은 채 오른손이 끄적임, 중간에 멈추고 위를 보며 눈 감기, 고개는 숙이고 작게 끄덕. nod는 대체안으로 보관. share/hippo_hop_write_v3.mp4, hippo_7actions_v3.mp4.
  - 2026-11-08 대표 피드백: 서서 공책 쓰기는 어색(공책 면이 유저 쪽, 연필 가로) → 앉아서 하는 버전 2종: desk_write(책상 위에 공책 펼쳐 놓고 연필로 쓰기, 왼손은 공책 누름, 중간에 멈추고 눈 감기), desk_laptop(노트북 타자, 양손 번갈아 두드림, 뚜껑 뒷면 하트 스티커가 화면 쪽). 64f: 책상·의자 팝인 → 앉기(다리 앞으로 75°) → 작업 → 일어나기 → 팝아웃. 의자 좌판 높이 = 다리 길이라 몸 높이는 그대로.
    - 손 위치는 aim() 헬퍼(목표 지점으로 팔 회전 + 길이 늘림), 연필은 뼈 자식 대신 매 프레임 손 위치로 키(팔 늘림에 같이 찌그러지지 않게).
    - 책상 장면만 카메라를 더 위에서(고도 0.5) 봐야 책상 위가 보임 → 대기 클립과 이어 붙이면 시점이 한 번 바뀜. 앱에서 책상 장면을 별도 연출(페이드)하거나, 책상 동작 시작/끝에 카메라를 보간하는 방식 중 결정 필요.
    - 함정: props에서 scale/location 설정 직후 matrix_world는 갱신 전 값 → view_layer.update() 후 사용(노트북이 1m짜리로 커졌던 버그).
    - share/hippo_desk_write_laptop_v1.mp4, hippo_desk_still.png.
  - 2026-11-08 **대표 결정: '공부·일'을 둘로 나눔 → 공부 = desk_write(공책), 업무 = desk_laptop(노트북).** 공통 동작은 7 → 8종(만세, 쓱싹, 점프, 공부, 업무, 냠냠, 기지개+회전, 손 흔들기). 서서 쓰기(write)·고개 끄덕(nod)은 대체안으로 보관.
    - 카메라 시점 전환: 대표 결정 = 동작 안에서 카메라 보간. 1~10f 고도 0.12→0.5, 52~62f 0.5→0.12(smoothstep) → 첫/끝 프레임이 대기와 픽셀 단위로 동일 확인. share/hippo_study_work_v2.mp4.
  - 2026-11-08: 공간·아이템 스레드용 docs/ART_BIBLE.md 작성(톤, 레퍼런스, 형태, 팔레트 hex, 재질, 크기 기준, 조명·카메라·렌더 고정값, 파이프라인, 금지, 체크리스트).

- 2026-11-08 대표 결정: 캐릭터 호칭 '펫' 대신 '단짝'.
- A/B 혼용(방=A, 마당·텃밭=B) 검토 의견: 비추천. 장면마다 단짝 모습이 달라지고(렌더 vs 실시간 조명) 제작·QA·꾸미기 대응이 두 배. 단계별로 하나만: MVP는 A 전체, 자유 이동·단짝 꾸미기가 필요해지면 B로 전체 전환. A는 앱 밖 용도(스토어 이미지, 알림, 위젯, 공유 카드)에 계속 사용. 마당에서 걷기도 A로 8방향 걷기 렌더 가능.

- 2026-11-08 대표 결정: 앱 형식 A(미리 렌더한 움직이는 WebP). 내보내기 v1 → design/character/export/v1/ (README.md, manifest.json, hippo_<key>.webp 12개 + 포스터, 600x800 투명 24fps, 합계 7.5MB). key는 앱 categories.ts 기준 + work + idle + 곁에 앉기 3종.
  - 앱에 이미 '곁에 앉기(sit)' 동작이 있어서 새로 만듦: sit_in(바닥에 앉기) → sit_loop(천천히 숨쉬기, 느린 깜빡임) → sit_out(일어나기). share/hippo_sit_v1.mp4.

- 2026-11-09: 공간 스레드 요청분 → export v1에 추가(합계 15클립 9.3MB). eat_strawberry(방 먹이기, 군고구마 냠냠과 같은 동작 + 스크립트 딸기: 빨강·노란 씨·초록 꽃받침, 3번 베어 물면 작아짐), garden_idle·garden_cheer(25° = 고도 0.5, render_clip.py로 기존 .blend를 다른 카메라로 렌더. 25°에서는 색종이 시작점이 콧등에 겹쳐서 머리 위로 올림). share/hippo_strawberry_garden25_v1.mp4.

- 2026-11-10: 바닥 그림자(대표 OK, 렌더에 포함 방식). render_clip.py에 바닥 타원 그림자(평면 + 방사형 알파, 블렌드) 추가, 루트 뼈 높이로 프레임마다 크기·진하기 키(점프 시 최소 0.5배, 앉으면 넓게). 최종 렌더 경로를 render_clip.py 하나로 통일(rerender_all.sh: 15클립, 책상은 glide 플래그). 방 만세의 색종이도 콧등에 붙어 보여서 머리 위에서 시작하게 함. 바닥 기준점: 방 (303,713), 텃밭 (303,697) / 600x800. export v1 갱신(11MB). share/hippo_shadow_sheet.png, hippo_shadow_v1.mp4.

- 2026-11-11: 마당 25° 동작 1단계 — 걷기 3방향(텃밭 공용) → export v1 `walk_front`·`walk_side`·`walk_back`(48f 2초 루프, 한 루프에 깜빡임 1번, 뒤는 깜빡임 없음). 스크립트 scripts/blender/anim_yard.py(마당 동작 전용), 렌더는 render_clip.py 0.5.
  - 걸음: 16f에 두 걸음(초당 3걸음, 짧은 다리로 아장아장), 다리 ±30°, 반대 팔 흔들기, 걸음마다 몸 통통(0.032)·기울기·귀 늦게 출렁, 꼬리 살랑. 키는 CYCLES 모디파이어로 끊김 없이 반복.
  - 옆 방향 = 루트 65° 회전(완전 옆모습 90°보다 얼굴이 보이는 3/4). 왼쪽은 앱이 좌우 뒤집기. 앞 = 대기와 같은 방향, 뒤 = 180°.
  - 발 미끄러짐 없는 속도: 측정 0.42 단위/초(measure_stride.py) → 마당 그림 px로 가로 168px/s, 세로 72px/s(25° 원근, 1단위 = 400px). manifest `walk`에 계산법. 처음 126/54로 적었던 건 ortho 1.45가 세로(800px) 기준인 걸 놓친 계산 실수.
  - 걸음 비교(대표): B안(초당 4걸음, 다리 46°, 0.81단위/초)은 "너무 빠르게 통통" → A 유지. 웹 테스트 페이지에 걷기 클립(스프라이트 시트, scripts/make_walk_sheets.py) + 땅 기준 속도(세로 ×0.426) + 기본 속도 0.42 반영
  - 대표 결정(2026-11-11): 테스트 페이지에서 걷는 속도 0.9단위/초로 확정(가로 360px/s). 발이 조금 미끄러지는 건 감수. 보폭을 늘려 맞추면 초당 4걸음 넘게 돼서 B처럼 통통거림
  - 확인: share/hippo_walk25_keys.png, hippo_walk25_loops_v1.mp4, hippo_walk25_yard_v1.mp4(마당 위 합성).
  - 2026-11-11 2단계: 나머지 6종(16클립) 완료 — 벤치(앞에서 폴짝 올라앉기, 다리 까딱·두리번 루프), 매트(앉기·숨쉬기 루프, 딸기·군고구마 먹기), 해먹(폴짝 올라가 누워 낮잠, 얼굴 보이게 머리 돌림), 물장구(물 높이에서 잘림, 물방울), 냄새 맡기(숙여 킁킁 → 하트), 열매 보여주기(나무 쪽 3/4 뒷모습에서 가리키다 돌아봄). 클립 원점 = manifest `yard_actions.stand`(벤치·해먹은 아이템 앞 0.3단위 새 지점 제안). 아이템은 yard.py로 만들어 홀드아웃(하마 앞 부분만 투명) → 앱은 아이템 먼저, 하마 위에.
  - 리그 한계: 팔이 짧아 어깨 높이(-90°)까지만 자연스럽게 올라감. 그 이상은 몸 속으로 접힘 → 가리키기는 몸 기울이기로 보완.

## 동작 추가·기록 줌·누적 축하 영상 (2026-11-12 대표 결정 Z1~Z4 = 전부 추천안)
- Z1 기록 축하 줌: **살짝 줌인 1.25배 + 주변 살짝 어둡게**(들어가기 0.3초, 동작 끝나면 0.35초에 복귀). 줌 중 화면 탭 = 바로 복귀, 기기 '동작 줄이기' 켜져 있으면 줌 없음. 1.3배까지는 지금 그림 해상도로 충분(단짝 600px 클립·방 1080 창). 비교 영상 share/record_zoom_AC_drink_v1.mp4(가구 없이 방 배경만), 스크립트 scripts/preview_record_zoom.py
  - 정정: 첫 의견에서 "단짝 = 화면 폭 40%(약 160pt)"라 했는데 그건 클립 칸(435/1080) 크기. 실제 보이는 몸은 화면 폭 약 20%(약 80pt) → 줌 필요성이 더 큼
- Z2 새 동작은 '잘 먹기' 안에서 갈라짐: 물 마시기(`drink`), 요리(`cook`, 계란후라이 뒤집기 + 작은 요리사 모자). 키워드 '물' → drink, '요리/만들/끓/볶' → cook, 나머지 = 냠냠
  - 2026-11-12 `drink` v1 시안: 큰 하늘색 유리잔(높이 0.24, 반투명 + 물이 꿀꺽마다 줄어듦)을 두 손으로 → 고개 젖혀 꿀꺽 3번 → 잔 내리고 눈 감고 "캬~"(몸 쭉, 작은 점프, 반짝이 3개, 물방울 1개는 얼굴 밖으로). 64f 2.7초. rig/hippo_drink.blend, drink_frames/, share/hippo_drink_v1.mp4. anim_actions.py `drink`. 대표 OK(11-12) → export v1 `drink`(hippo_drink.webp)
  - 2026-11-12 `cook` v1: 요리사 모자(퐁실한 흰 모자, 귀 사이) + 코랄 프라이팬(검정 대신 팔레트 코랄, 나무 손잡이) 두 손으로 → 지글지글 좌우 흔들기 → 툭 던져 계란후라이 한 바퀴 돌아 머리 옆까지 → 받고 눈 감고 뿌듯하게 통통 + 반짝이. 76f 3.2초. rig/hippo_cook.blend, share/hippo_cook_v1.mp4. 대표 확인 전이지만 export v1 `cook`에 넣어 둠(고치면 다시 export)
  - 2026-11-12 `cook` v2 (대표: "후라이팬 한 손으로"): 오른손으로 손잡이 끝을 잡고(팬은 arm.R에 붙음) 팔을 내렸다 휙 올려 뒤집기, 왼손은 옆에 내림. share/hippo_cook_v2.mp4, export v1 `cook` 갱신
  - 2026-11-12 `cook` v3 (대표: "후라이팬이 앞으로 향하게"): 팬이 배 앞에서 카메라 쪽을 향하고 손잡이가 오른손으로 이어짐(옆으로 뻗던 v2 수정, 팔 앞으로 -88°). share/hippo_cook_v3.mp4, export v1 `cook` 갱신
- Z3 누적 축하 기준 = 기록 수(구슬 수, 서버 marbles_total). Z4 횟수 = 10·30·50·100(출시) → 200·300·500·1000(업데이트). 전체 화면 mp4(개당 1~2MB 예상), 횟수마다 테마만 다르고 더 화려해지지 않음, 카운트다운 문구 없음, 넘기기 + '축하 모음'에서 다시 보기, 하루에 여러 기준 넘어도 1개. 50번은 유리병 뚜껑 닫힘과 이어 붙임
  - 10번 테마 = 대표 스케치(2026-11-12): 꽃 화관(분홍·초록·흰·보라·노랑 꽃, 노란 띠), 물속에서 둥실 떠서 두 팔 들고 회오리 춤, 보글보글 방울, 하늘색 물 배경. 30 구름 트램펄린 / 50 구슬 불꽃놀이 → 유리병 뚜껑 / 100 열기구 (안)
  - 2026-11-12 10번 축하 영상 v1 (시안, 대표 확인 대기): 6.9초 1080×1920 mp4 1.25MB. 아래에서 둥실 떠오름 → 입에서 보글보글 방울 → 두 팔 들고 회오리 2바퀴(방울 고리가 몸을 감고 올라감) → "짠" 정면 만세 + 방울 터짐 + 반짝이 → '기록 10번, 축하해!' 문구. 꽃 화관 = 노란 띠 + 분홍·흰·민트·라벤더·크림 5잎 꽃 9송이(anim_actions.py `flower_crown`). 단짝은 Blender(`milestone10` → rig/hippo_milestone10.blend, 렌더 scripts/blender/render_milestone.py scale=2.15 tz=-0.12), 바다 배경·방울·문구는 2D 합성(scripts/composite_milestone10.py, 단짝 위치 track.json 사용). 렌더 프레임(1080×1920 PNG 156장)은 커밋 안 함 — 위 두 명령으로 다시 만듦(렌더 약 5분). share/milestone10_underwater_v1.mp4

- 2026-11-13 단짝 표면 비교 시안 (대표 요청: 털 질감 / 지금보다 매끄러운 표면, 대표 확인 대기): scripts/blender/texture_compare.py `current|smooth|fur` → share/surface_compare_closeup_v1.png, surface_compare_phone_v1.png, surface_compare_body_v1.png(몸통: smooth에도 배 가로 이음새 줄이 희미하게 남음). smooth = AI 스캔 메쉬의 UV 이음새 용접(remove_doubles 1e-5, 11220개) 후 Corrective Smooth(용접 없이 하면 이음새가 갈라짐) + 몸 텍스처의 얼룩(구워진 음영)을 #F2CFA6 단색으로 교체(눈·눈썹·콧구멍·귀 안쪽만 텍스처 유지) + sheen 0.2. fur = Geometry Nodes 짧은 털(0.0075, 17만 가닥, 아마추어 뒤라 포즈 따라감; Blender 5는 Curve to Mesh 'Scale' 입력에 반지름 연결 필요). 폰 크기에서 털은 거칠게(모래처럼) 보이고 움직이면 반짝거릴 위험, 용량도 늘어남

- 2026-11-13 표면 비교 v1에 '배 줄 지움' 추가 (share/surface_compare_seamfix_v1.png, _phone_v1.png, 대표 확인 대기). 원인: GLB에서 가져온 custom_normal/sharp_edge 속성이 이음새 주름을 그대로 들고 있었음 → 속성 제거 + 전체 smooth shading + 울퉁불퉁한 정점(이웃 평균에서 법선 방향으로 튀어나온 상위 10%)만 vertex group으로 Corrective Smooth 15회. 배 가로줄·다리·팔 이음새가 사라지고 형태 손실 없음. 목 아래 그늘은 접촉 그림자(조명)라 남음

- 2026-11-13 **표면 v2 확정 (대표: '매끈하게 + 줄 지움')** → scripts/blender/surface.py를 render_clip.py·render_milestone.py가 렌더할 때 자동 적용(HIPPO_SURFACE=0이면 예전 모습). 용접 → custom normal 제거 → Corrective Smooth 2단(전체 25회 + 울퉁불퉁한 정점 15회) → 몸 단색 #F2CFA6 + sheen 0.2 → 부드러운 그림자(sun angle 18°/30°) + AO. 몸 색 샘플 (233,200,162) → (232,198,159)로 거의 같음. 덤으로 돌아선 각도에서 목에 생기던 진한 고리 그림자도 거의 사라짐. export v1 36클립 전부 다시 렌더·export(scripts/blender/rerender_surface_v2.sh). 10번 축하 영상 v1은 다시 만들 때(Higgsfield 여부 결정 후) 적용

## 방 탭 반응 (2026-11-14 대표 요청: 방 하마 누르면 랜덤 동작)
- v1 시안 2종 (대표 확인 대기, export v1에 미리 넣음): share/hippo_tap_actions_v1.mp4 (방 배경 위, 왼쪽 폰 크기·오른쪽 2배)
  - `tap_fart_hop` (anim_actions.py `fart_hop`, 90f 3.75초): 힘주기(눈 꼭, 부르르) → '뿡' 엉덩이에서 방귀 구름(#EDF2CC, 양옆으로 퍼지며 사라짐) → 위로 방방 3번(0.46 / 0.3 / 0.16단위, 다리 대롱·팔 허우적, 착지마다 작은 구름) → 눈 감고 고개 갸웃 헤헤 + 꼬리 살랑. 높이 때문에 **캔버스 600x1100**(render_clip.py `h=1100`, 위쪽만 늘림)
  - `tap_roll` (`roll`, 76f 3.2초): 몸 말기 → 오른쪽으로 데굴 한 바퀴(0.9단위 ≈ 방 360px, 실제 굴림 거리의 약 40% — 더 멀리 가면 방 창의 절반을 넘음) → 끝에서 살짝 흔들 → 반대로 데굴 돌아옴 → '짠' 폴짝. 화면 평면에서 굴러서 얼굴이 계속 보임. 프레임마다 가장 낮은 정점으로 바닥에 붙임. **캔버스 1600x800**(`w=1600`), 그림자가 따라감(rig `shx`/`shh` 키)
  - v2 (2026-11-15 대표 피드백): ① 방귀인 걸 알게 **'뿡!' 글자**를 애니메이션 안에 넣음 — 방귀 구름 나올 때마다 뿡! / 뿡 / 뽕 (코랄 #ED5C61 + 크림 테두리, 톡 튀어나와 살짝 떠오르며 사라짐). 렌더 위에 2D 합성 = scripts/composite_fart_text.py (글꼴 Jua, OFL, design/fonts). 글자가 그림에 박혀서 언어별로 클립이 따로 필요(일본어판 낼 때 `ja` + 가나 글꼴). ② 구르기 = **엎드려서 통나무처럼** (몸 길이 축으로 회전): 엎드림(머리 앞쪽 비스듬히, 턱 들어 얼굴 보임) → 오른쪽으로 한 바퀴 → 흔들 → 반대로 한 바퀴 → 일어나 '짠'. 100f 4.2초, ROLL_YAW -20 / ROLL_TRAVEL 1.2. 미리보기 share/hippo_tap_actions_v2.mp4
  - 앱 쪽 규칙 제안: manifest `tap_reactions` (랜덤, 굴러가기 50% 좌우 뒤집기, 기록·먹이기 동작 중엔 탭 무시)

## 앱 형식 비교 (2026-11-08, 결정 대기)
- 측정: 원본 PNG 9클립 약 137MB. 프레임별 WebP(q80): 300px 4.6MB / 450px 7.2MB. 움직이는 WebP 1파일(600px, 원본 해상도): 만세 578KB → 9클립 추정 5~6MB. GLB(애니 포함, 미최적화) 6.3MB → 최적화 시 2~3MB 추정.
- A. 미리 렌더한 움직이는 WebP(추천, MVP): expo-image로 재생, Pet.tsx만 교체, 1~2일. 렌더와 픽셀 단위로 같음. 단점: 고정 각도, 펫 꾸미기 아이템은 아이템마다 오버레이 시퀀스 추가 렌더 필요. 확인 필요: expo-image 재생 끝 감지/메모리(실기기).
- B. 앱 안 3D(GLB + three.js/expo-gl): 4~6일, 의존성 추가, 조명을 three.js로 다시 맞춰야 해서 색이 렌더와 달라질 위험, 저가 안드로이드 성능·배터리 확인 필요, 깜빡임(셰이더 믹스)은 코드로 다시 구현. 장점: 용량 최소, 펫 꾸미기 아이템을 머리 뼈에 바로 붙임, 탭 반응 등 인터랙션.

## 열린 질문
- 성격/말투 (동물=하마, 이름=하몽 확정)
- 아트 스타일, 제작 방식 (AI 생성 / 외주 / 무료 에셋)
- 공통 동작 7종을 어떻게 그릴지 (GAME_DESIGN.md 참고)
