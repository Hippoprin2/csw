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

## 열린 질문
- 최종 동물 종류, 이름, 성격/말투
- 아트 스타일, 제작 방식 (AI 생성 / 외주 / 무료 에셋)
- 공통 동작 7종을 어떻게 그릴지 (GAME_DESIGN.md 참고)
