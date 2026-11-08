# 캐릭터 디자인

담당 스레드: 캐릭터 디자인

## 결정 사항
- 동물 컨셉 (2026-10-19)
- 프로토타입 임시 캐릭터: 꼬마하마

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

## 앱 형식 비교 (2026-11-08, 결정 대기)
- 측정: 원본 PNG 9클립 약 137MB. 프레임별 WebP(q80): 300px 4.6MB / 450px 7.2MB. 움직이는 WebP 1파일(600px, 원본 해상도): 만세 578KB → 9클립 추정 5~6MB. GLB(애니 포함, 미최적화) 6.3MB → 최적화 시 2~3MB 추정.
- A. 미리 렌더한 움직이는 WebP(추천, MVP): expo-image로 재생, Pet.tsx만 교체, 1~2일. 렌더와 픽셀 단위로 같음. 단점: 고정 각도, 펫 꾸미기 아이템은 아이템마다 오버레이 시퀀스 추가 렌더 필요. 확인 필요: expo-image 재생 끝 감지/메모리(실기기).
- B. 앱 안 3D(GLB + three.js/expo-gl): 4~6일, 의존성 추가, 조명을 three.js로 다시 맞춰야 해서 색이 렌더와 달라질 위험, 저가 안드로이드 성능·배터리 확인 필요, 깜빡임(셰이더 믹스)은 코드로 다시 구현. 장점: 용량 최소, 펫 꾸미기 아이템을 머리 뼈에 바로 붙임, 탭 반응 등 인터랙션.

## 열린 질문
- 최종 동물 종류, 이름, 성격/말투
- 아트 스타일, 제작 방식 (AI 생성 / 외주 / 무료 에셋)
- 공통 동작 7종을 어떻게 그릴지 (GAME_DESIGN.md 참고)
