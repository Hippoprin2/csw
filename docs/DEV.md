# CSW 앱 개발 (Expo + Supabase)

담당 스레드: 앱 개발 (Slack project-csw)
최종 수정: 2026-11-08
기능 범위·흐름의 기준은 docs/FEATURES.md. 이 문서는 "어떻게 만들었고 어떻게 돌리는지"만 적는다.

## 구성
- 앱: `mobile/` — Expo SDK 58, expo-router(`mobile/src/app`), TypeScript, React Compiler. Expo 규칙은 `mobile/AGENTS.md`.
- 백엔드: Supabase 프로젝트 `csw` (ref `xbifxrvgdimwwijijthl`, 도쿄, 무료 플랜, org Hippoprin2's Org)
  - 스키마: `supabase/migrations/` · 엣지 함수: `supabase/functions/classify`
- 비밀값: 루트 `.env.local` (DB 비밀번호, service role 키, OpenAI 키) / `mobile/.env.local` (공개 URL·publishable 키만). 둘 다 gitignore.

## 화면 (mobile/src/app)
- `auth/` 펫 인사 + 가입: Apple(iOS 네이티브, `expo-apple-authentication` → signInWithIdToken), 카카오·구글(브라우저 OAuth → `auth/callback`), 이메일(6자리 코드 또는 메일 링크). 카카오·구글 버튼은 `EXPO_PUBLIC_AUTH_KAKAO/GOOGLE=1`일 때만 보임(키 넣기 전엔 숨김). 로직: `mobile/src/lib/auth.ts`
- `onboarding/` 이름 짓기 → 한 줄 안내 + 동의(14세 이상·상담 아님·개인정보/국외이전) → 선물 씨앗 6개
- `(tabs)/index` 방: 기록 입력(오늘/어제, 추천 칩 6개, "○○ 동작 · 바꾸기"), 펫 축하 7종, +3 씨앗, 첫 기록 연출, 첫 기록 후 알림 권한 요청, 자해 표현 시 "곁에 앉기" + 상담 번호 카드(같은 날 두 번째부터는 배너)
- `(tabs)/jar` 유리병: 누적 구슬, 이번 주 카드(개수·카테고리·"이 순간 기억나?"), 지난 주 카드, 날짜별 목록(같은 날 같은 내용 ×N 묶기, 하루 6개 넘으면 접기), 눌러서 수정·삭제
- `(tabs)/shop` 꾸미기: 소품 18개(임시), 구매 → 방에 배치 + 펫 축하
- `(tabs)/settings` 펫 이름, 알림 on/off·시간, 텍스트 내보내기, 모든 기록 지우기(2단계), 도움받을 수 있는 곳, 처리방침·약관·문의(URL은 env), 로그아웃, 계정 삭제(2단계)
- 단짝: `mobile/src/ui/Pet.tsx` — 캐릭터 스레드의 움직이는 WebP(`design/character/export/v1`) 재생. 대기는 항상 깔고 동작은 위에 겹쳐 duration_ms 타이머로 걷어냄, 동작 첫 프레임이 뜬 뒤(onLoad/onDisplay)에만 대기를 숨김. sit = sit_in → sit_loop 9초 → sit_out. 에셋 갱신: `python3 scripts/gen_pet_clips.py` (mobile/assets/pet 복사 + src/data/petClips.ts 생성). 웹: 동작 이미지를 opacity 0으로 숨기면 lazy 로딩이 안 끝남 → 숨기지 말 것
  - 2026-11-10 버그 수정(Expo Go에서 동작이 늦게·짧게·아예 안 나옴): 원인 = duration 타이머를 동작 이미지 마운트 시점부터 쟀음 + `cachePolicy="none"`이라 매번 1MB WebP를 다시 받고 디코딩(Expo Go는 require 에셋을 Metro에서 HTTP로 받음). 로딩 시간만큼 잘리고, duration보다 길면 안 보인 채 걷힘. 수정 = 타이머는 첫 프레임 표시(onDisplay/onLoad) 뒤부터(+150ms 여유), 5초 안에 안 뜨면 그 단계 건너뜀, `cachePolicy="disk"`(memory는 재생 위치 공유 위험), 앱 시작 때 클립 전부 `Image.prefetch(…, 'disk')`(네이티브만). 대표 아이폰 Expo Go에서 확인 완료(2026-11-10)
  - 남은 지연: 기록 → 동작 시작까지 분류 LLM 1.1~1.8초(콜드 스타트면 더, 5초 타임아웃) + record_win 0.2~0.5초. 대표 결정(2026-11-10, D1-A): 지금처럼 저장 끝난 뒤 동작 시작 유지(저장 실패 시 축하 안 함), 분류 타임아웃도 안 줄임(안전 감지 주력이 LLM)

## 서버 규칙 (전부 DB 함수에서 강제, 클라이언트는 wins/seed_ledger 직접 insert 불가)
- `record_win`: 오늘/어제(KST)만, 1~100자, 하루 50개 상한(남용 방지), 하루 10개까지 씨앗 3개, 첫 기록 여부 반환
- `edit_win` / wins delete: 씨앗 회수 없음 · `buy_item`: 잔액 확인, 중복 구매 막음 · `grant_onboarding_gift`: 1회만 6개
- `delete_all_wins`: 기록만 삭제(펫·방·씨앗 유지) · `delete_my_account`: auth 사용자 삭제 → 모든 행 cascade
- RLS: 전 테이블 본인 행만. `safety_events`는 시각·출처만(본문 없음). `app_events`(S9 분석)는 이름+작은 props만, 본문 금지.
- 분류 함수 `classify`: OpenAI `gpt-5.4-nano`(env `CLASSIFY_MODEL`로 교체), reasoning none, 6초 타임아웃, 사용자 식별자 안 보냄, store=false. 앱은 5초 안에 답이 없으면 키워드 결과로 저장.
- 자해 표현 판정 = 기기 키워드(`mobile/src/data/safety-keywords.json`) OR LLM. 하나라도 걸리면 안내(안전한 쪽).
- Auth 공급자: Apple 켜짐(client id `com.hippoprin.csw,host.exp.Exponent` — Expo Go에서도 테스트 가능, 네이티브 전용이라 비밀키 갱신 불필요). 카카오 이메일 선택(email_optional). 카카오·구글·SMTP 키는 `scripts/set_auth_keys.sh`(대표가 입력) → `python3 scripts/apply_auth_config.py`(Supabase 반영 + SMTP 있으면 코드 메일 템플릿).

## 테스트
- `python3 scripts/test_backend.py` — 실서버 스모크 25개 (OTP 로그인, 씨앗 규칙, RLS 차단, 구매, 수정·삭제, 분류, 계정 삭제 cascade). 2026-11-08 ALL PASS.
- `python3 scripts/eval_safety.py` — 위험 15 / 오탐 유도 15 문장. 2026-11-08: 키워드 15/15·오탐 0, LLM 15/15·오탐 1("시험 공부 죽어라 했다"), 최종 15/15·오탐 1.
  - 주의: 키워드 목록은 이 30문장을 보며 만들었다(과적합).
  - 2차 세트 `python3 scripts/eval_safety.py safety_cases_2.json` (위험 20 / 오탐 유도 20, 앞 9개는 대표가 프로토타입에서 시험한 문장 등): 키워드 10/20, LLM 18/20, 최종 19/20, 오탐 0. 놓친 것: "가족들한테 미안하다고 편지 썼어". 키워드는 처음 보는 표현에 약함 → LLM이 주력, 키워드는 오프라인·LLM 장애 대비용.
  - 프로토타입(csw-prototype.vercel.app)에는 감지 기능이 없다. 감지는 앱에만 있다.
- 앱: `cd mobile && npx tsc --noEmit && npx expo lint` (2026-11-08 둘 다 통과). 웹으로 흐름 확인: `npx expo start --web` → 400×860에서 가입 후 온보딩·기록·안전 카드·구매·유리병 수정·계정 삭제까지 확인함.
  - 웹에서 로그인 테스트: 메일 대신 service role로 OTP를 만들어 세션을 localStorage(`sb-xbifxrvgdimwwijijthl-auth-token`)에 넣는다 (`scripts/sb.py temp_user()` 참고).

## 대표와 실시간 확인 (Expo Go)
- `cd mobile && npx expo start --tunnel ngrok --port 8081` (Expo 계정 없이 ngrok 터널. `--tunnel`만 쓰면 Expo 로그인 요구). 터널 주소는 `curl localhost:4040/api/tunnels`의 public_url → `exp://<host>`로 QR 만들기(`npx qrcode -o qr.png "exp://..."`). 같은 서버가 웹 http://localhost:8081 도 제공.
- 맥이 잠들거나 서버가 꺼지면 주소가 바뀔 수 있음 → 다시 켜고 새 QR.
- 주의: 터널(ngrok 포함)로 열면 Expo Go가 "Expo Go와 Expo CLI 둘 다 로그인 필요" 오류를 낸다. 계정 없이 하려면 같은 와이파이에서 `npx expo start --lan` → `exp://<맥 IP>:8081` (맥 IP: `ifconfig | grep "inet "`, 이 맥은 en1 와이파이 192.168.0.x). 밖에서 보려면 대표가 Expo 계정을 만들고 폰 Expo Go + 맥 터미널 `npx expo login` 둘 다 로그인 후 `--tunnel`.

## 기종별 화면 대응
- 세로 고정, 태블릿 미지원(app.json), 넓은 화면은 최대 너비 520으로 가운데 정렬. 노치·홈 바는 SafeAreaView
- 공간 그림은 정사각형 캔버스(1080) → 카드도 정사각형. 방 = min(화면너비-32, max(300, 화면높이 45%)) 가운데 정렬, 텃밭·마당 = 화면너비-32 (`ui/layout.ts`). 모든 위치는 manifest px × (카드/1080)
- 좌우 넘기기 페이지 너비: onLayout 측정값, 없으면 화면 너비(웹에서 onLayout이 간헐적으로 안 와서 빈 화면 나던 문제 수정)
- 웹 확인 크기: 375×667(SE), 360×800(안드로이드 보급형), 393×852(15), 430×932(Pro Max) — 2026-11-10 모두 단짝·입력창 정상
- 키보드: 방 ScrollView가 키보드에 덮이는 만큼 아래 여백을 늘리고 맨 아래로 스크롤 (RoomPage, 2026-11-10 대표 폰에서 가림 보고 → 수정)
- 남은 확인: 큰 글씨 설정(Dynamic Type)에서 넘침, 안드로이드 실기기

## 배포·운영 메모
- 마이그레이션: `supabase db push --linked` (CLI: `/Users/soniakang/.bun/install/global/node_modules/supabase/bin/supabase`, 비번은 루트 .env.local `SUPABASE_DB_PASSWORD`)
- 함수: `supabase functions deploy classify --use-api --project-ref xbifxrvgdimwwijijthl` (Docker 불필요). 비밀값 `OPENAI_API_KEY`는 supabase secrets에 설정됨.
- Auth 설정(Management API로 변경): OTP 6자리, 10분 유효, site_url `csw://`, redirect 허용 `csw://**, exp://**, http://localhost:8081/**`
- 무료 플랜은 7일 활동 없으면 일시정지될 수 있음 → 출시 전 Pro 전환 여부 결정.

## 막힌 것 / 다음 할 일
- [ ] **이메일 OTP 메일 발송**: 무료 플랜 기본 메일은 템플릿 수정 불가(코드 대신 링크만 감) + 시간당 2통. 커스텀 SMTP 필요 → Resend(무료 월 3,000통) 계정 + 도메인. 도메인 전에는 Resend 계정 주인 메일로만 발송 가능(대표 본인 테스트용으로는 충분).
- [x] 카카오·구글 키 Supabase 반영, 앱 버튼 켬 (2026-11-08). 구글 인증 화면까지 정상 확인. 카카오: Supabase가 account_email+profile_image+profile_nickname 고정 요청 → 동의항목 3개 모두 설정해야 함(KOE205). 이메일 동의항목은 비즈 앱(개인 개발자 전환 가능) 필요
- [ ] 구글 OAuth 앱은 테스트 모드(테스트 사용자만 로그인) → 출시 때 Publish app
- [ ] 카카오·구글·Apple 실기기 로그인 확인 (Expo Go)
- 카카오 프로필 사진: Supabase가 항상 요청 → 동의 화면에 필수처럼 뜸(대표 결정: 일단 유지). 받은 사진 주소는 트리거로 즉시 삭제(`20261108000002_strip_profile_image.sql`, 확인 `scripts/test_strip_image.py`). 처리방침에 '보관하지 않음' 명시.
- [ ] 정식 빌드(TestFlight) 때 카카오 공식 SDK + signInWithIdToken으로 바꿔 이메일·닉네임만 요청
- 주의: Supabase Auth는 사설 IP 리다이렉트(exp://192.168.x.x…)를 허용 목록에 있어도 거부하고 site_url(csw://)로 보낸다 → OAuth redirectTo는 항상 `csw://auth/callback` (iOS 인증 창이 가로챔). 확인법: admin generate_link에 redirect_to 넣고 돌려받은 redirect_to 비교. (2026-11-08 Apple·카카오 계정 생성은 서버에서 확인)
- [ ] Apple: 코드·Supabase 설정 완료. Expo Go 실기기 테스트 필요. TestFlight/스토어는 Apple Developer 가입 후
- [ ] 개인정보처리방침·이용약관 페이지, 문의 메일 → `EXPO_PUBLIC_PRIVACY_URL / TERMS_URL / CONTACT_EMAIL`
- [ ] 구독(7일 체험 → 월 3,000원) 결제 연동 — 사업자등록 후. 구독 끝나도 기록 보기·내보내기·삭제, 펫·방, 안전장치는 무료 유지(STATUS 결정)
- [ ] continue/kill 지표용 SQL(D1/D7 재방문, 1인당 주간 기록 수) — `app_events` 기반
- [ ] 소품 목록·가격 확정(WORLD 스레드) → `items` 테이블 갱신, 방 배치 `mobile/src/data/itemSlots.ts`
- [ ] 최종 캐릭터 에셋(CHARACTER 스레드) → `Pet.tsx` 교체
- [ ] 실기기 확인(Expo Go 또는 개발 빌드): 알림 예약, 햅틱, 전화 연결, 키보드 동작

## 개발 계획 (2026-11-08 초안, 대표 확인 전)
근거: FEATURES.md 7장(공간·텃밭 확정), CHARACTER.md(3D 하마 + 동작 렌더, 공부/업무 분리 8종), STATUS 결정 사항.

### 1단계 — 확정 내용을 앱에 반영 (지금 바로 가능)
- 진행 (2026-11-09): 8종(업무 work 추가: DB·분류 함수·키워드·한마디) + 단짝 WebP 교체 + 앱 문구 펫→단짝 완료. 분류 평가 `scripts/eval_classify.py` 키워드 20/22·LLM 21/22. 웹에서 대기→업무→대기, 곁에 앉기 순서 확인. 실기기(대표 아이폰, Expo Go): 끊김 없음, 늦게 뜨지 않음 → 1단계 완료. RAM 수치는 아직 안 잼 → 저가 기기·Android 확인은 정식 빌드 때
- 동작 7 → 8종: '공부·일'을 공부(공책)·업무(노트북)로 분리 — DB 카테고리, 분류 함수, 키워드, 한마디, 바꾸기 목록, 유리병 색
- 진짜 하마 넣기: 렌더 PNG(600×800, 동작당 40~64장, 11~20MB) → 앱용으로 압축(절반 크기 WebP 스프라이트, 동작당 1~2MB 목표) + 프레임 재생 컴포넌트로 Pet.tsx 교체. 대기 루프 + 8종
  - 필요(캐릭터 스레드): "곁에 앉기"(자해 표현 대응) 동작. 책상 장면 시점 전환은 앱에서 페이드 추천
- 대표와 Expo Go로 화면 다듬기

### 2단계 — 텃밭 + 좌우 공간 (출시 범위)
- 진행 (2026-11-09): 구현 완료(임시 그림 = 이모지). 웹에서 심기→다음 날 수확→창턱 장식→먹이기, 소품 구매·바꿔 끼우기, 졸고 있음→탭해서 깸, 마당 잠금 확인. `scripts/test_garden.py` 26개 통과
  - 화면: `(tabs)/index.tsx` = 좌우 넘기기(텃밭 ← 방 → 마당, 위 탭으로도 이동), `screens/RoomPage|GardenPage|YardPage.tsx`. 입력창·축하·곁에 앉기·먹이기/선물하기는 방에서만(대표 결정)
  - DB: items(space/slot/layer) + owned_items.placed + place_item(), crops/plots/harvest_bag/harvest_unlocks, plant/harvest/use_harvest/garden_state/touch_seen
  - 성장 = 심은 날 다음부터 "기록한 날"(seed_ledger 'win' 행의 KST 날짜) 수 → 기록을 지워도 안 줄어듦. 첫 작물 고구마 무료·1일, 그 뒤 3씨앗·9일
  - 졸고 있음 = 이전 접속(touch_seen)이 3일 이상 전 → 앱 세션 동안 💤, 탭하면 깸(서버 진행 영향 없음)
  - 보안: Supabase 기본 권한(authenticated 테이블 ALL) 때문에 profiles 모든 열 수정이 가능했음 → `20261109000003_tighten_grants.sql`로 최소 권한 재부여. **새 테이블 만들 때마다 authenticated 권한을 revoke all 후 필요한 것만 grant**
  - 남은 것: 공간 스레드 렌더(배경·소품·작물 이미지 + 위치 JSON)로 이모지 교체(`data/itemSlots.ts` 대체), 텃밭용 25° 단짝 클립(대기·만세)·딸기 먹기 클립(캐릭터 스레드), 실기기 확인
- 한 화면 좌우 넘기기(방 ↔ 텃밭, 마당은 잠금 표시 "구슬 10개면 열려"), 입력창은 하단 공통, 펫은 보고 있는 공간에서 축하
- 서버: crops(작물 카탈로그·가격·수확물), plots(칸·심은 작물·심은 시각), plant/harvest 함수
  - 성장 = 심은 뒤 "기록한 날" 수 / 3 (3단계 = 9일, 첫 작물만 1일). 쉬어도 리셋 없음, 진행 안 줄어듦
  - 졸고 있음 = 마지막 접속 3일 이상 → 탭하면 깸(진행 영향 없음). 알림 문구에 언급 금지
  - 수확물 = owned_items(장식) + "잘 먹기" 동작으로 먹기
- 필요(공간 스레드): 소품·작물 목록, 가격, 그림. 그 전에는 임시 데이터로 개발

### 3단계 — 출시 준비 (외부 조건 많음)
- 이름·도메인 → Resend 메일(6자리 코드), 개인정보처리방침·약관 페이지
- Apple Developer 가입 → EAS 개발 빌드 → 카카오 공식 SDK(이메일·닉네임만), TestFlight
- 사업자등록 → 구독(7일 체험 → 월 3,000원). 결제 연동은 RevenueCat + StoreKit 추천, 구독 끝나도 무료로 남길 것(기록 보기·내보내기·삭제, 펫·방, 안전장치) 반영
- 처음 보는 문장으로 안전 감지 재평가, D1/D7·주간 기록 수 SQL, 스토어 자료(스크린샷·설명)

### 4단계 — 첫 업데이트
- 텃밭에서도 단짝이 걸어 다니기 (2026-11-09 대표 결정: 출시 전엔 안 함, 마당 걷기 만들 때 같이 적용). 필요: 25° 걷기 클립 3방향(캐릭터), 텃밭 걷기 영역(공간), 이동·앞뒤 층·탭하면 걸어오기(앱)
- 마당(구슬 10개에 열림): 펫이 혼자 돌아다니고 탭한 곳으로 걸어옴 → 걷기·앉기 동작 필요

## 공간 그림 연결 (2026-11-10)
- 원본: design/world/export/v1 (공간 스레드) → `python3 scripts/gen_world.py` → mobile/assets/world(0.86MB) + `src/data/world.ts`. 다시 내보내면 이것만 다시 실행
- 단짝 클립: `python3 scripts/gen_pet_clips.py` (garden_idle, garden_cheer, eat_strawberry 추가, 15개)
- 방(`RoomPage`): 배경 → 놓인 소품·창턱 수확 장식·단짝을 manifest z 순서로. 창턱 꽃병 자리는 튤립/해바라기 중 하나 — 둘 다 있으면 꽃병을 탭해서 바꿈(기기 저장 csw.sillVase). 딸기 먹이기 = eat_strawberry 클립
- 텃밭(`GardenPage`): 배경 → 단짝(25° 클립, 수확 시 garden_cheer) → 작물 그림(mound / 작물_단계[_doze], 사이 날 +5%씩) → 터치 영역(tap_rect) → 이름·진행 점·✨·💤 UI
- 상점 = 썸네일, 수확 바구니 = produce 아이콘, 심기 = 씨앗 봉투 아이콘. `data/itemSlots.ts`(임시 이모지 배치) 삭제
- 웹 확인: iPhone 15·SE 크기에서 방(소품 14개+창턱 3개), 텃밭(3단계 작물·수확·만세), 상점 썸네일 정상

## 버틴 하루 분류 (2026-11-10)
- Category 'endure'(마이그레이션 20261110000001), 키워드는 마지막 순서('힘들었지만 운동했다' → 운동), classify 프롬프트: 해낸 일이 있으면 그 일 분류 우선, self_harm=true면 endure 강제(함수에서도 강제), 앱도 unsafe면 endure로 저장
- 자해 키워드 보강: 팔을그/팔에그/허벅지·다리·몸에그/상처냈/자해 등 ("팔을 그었어" 키워드 누락 수정). 프롬프트에 '밑줄 그었다', '죽어라 공부했다' 같은 오탐 예시 추가
- 평가: eval_classify 키워드 30/34 · LLM 33/34(버틴 하루 12문장 포함), eval_safety 위험 15/15·19/20, 오탐 0~2개(실행마다 다름: '시험 공부 죽어라 했다', '칼질 연습하면서 요리했다'). 계속 놓침: '가족들한테 미안하다고 편지 썼어'

## 유리병 50개 → 선반 (2026-11-10)
- `src/lib/jars.ts` `JAR_SIZE = 50` (숫자 바꾸려면 이것만). 서버 저장 없이 기록을 created_at 순으로 50개씩 나눔: 꽉 찬 병 = 선반, 마지막 = 지금 병
- 유리병 화면: 지금 병(14px 구슬, 50개가 들어가는 크기) + "N번째 병" / 꽉 찬 직후 "새 병이야. 다음 구슬은 여기에 들어가." + 선반(최근 병이 왼쪽, 탭하면 기간·구슬·카테고리 시트). 남은 개수 문구는 넣지 않음(압박 문구 금지)
- 방: 기록으로 50의 배수가 되면 단짝 한마디 "유리병이 꽉 찼어! 뚜껑 닫아서 선반에 올려둘게. 새 병 시작이야" (자해 감지 기록이면 생략, 곁에 앉기 우선). 이벤트 jar_sealed / jar_viewed
- 알려진 한계: 사용자가 기록을 지우면 그만큼 병 경계가 앞으로 당겨짐(닫힌 병이 49개로 다시 열릴 수 있음). 본인이 지운 것만큼이라 잃는 장치로 보지 않음. 문제 되면 profiles에 닫은 병 수를 저장하는 방식으로 변경
- 웹 확인(393×852): 99개 계정 → 100번째 기록 시 한마디, 선반 2병 + 빈 새 병, 1번째 병 시트 정상

## 마당 (2026-11-11, WORLD 7장 '다른 스레드 요청 정리' 개발 9개)
- 서버 `supabase/migrations/20261111000001_yard.sql`: `yard_state()`(open·record_days·zones·tester·dev_open) — 열림 = 기록한 날(seed_ledger 'win' KST 날짜) 누적 7일, 열리는 순간 `profiles.yard_opened_at` 저장 = 영구. `buy_zone(2|3)` 60·120 영구, `buy_item`은 마당 소품이면 마당이 열려야 구매(`yard_locked`), 소품은 자리 1개씩 바로 놓임. `memory_card(p_seen)` = 7일 넘은 기록 하나(한 달 전 오늘 우선 'month', 아니면 무작위 'past', 버틴 하루 제외). 테스트 스위치 `dev_yard`/`dev_all_zones`/`dev_seeds`(+500)는 `testers` 표에 있는 계정만(표는 service role로만 추가)
- 테스트: `python3 scripts/test_yard.py` (2026-11-11 31개 FAILS 0 — 열림 6일/7일·영구, 구역 가격·중복·없는 구역, 직접 insert 차단, 소품 잠금, 추억 카드 규칙, 테스터 권한). test_garden은 방 소품만 세도록 수정
- 테스터 추가: `python3 scripts/add_tester.py <이메일>` (확인: `python3 scripts/list_users.py`). 대표 계정(카카오) 테스터 등록됨
- 그림·데이터: `python3 scripts/gen_world.py`가 manifest `spaces.yard`를 `src/data/yard.ts`(YARD + YARD_IMG require 표)로 그대로 생성 + assets/world/yard. 타입 `data/yardTypes.ts`. 방 넓은 export(2160×1080) 반영 완료(2026-11-11): `ROOM.width/height/view/jarCabinet`, `CANVAS` = 카드 창 폭(1080)
- 기하·길찾기 `lib/yardGeo.ts`(React 없음): 구역·걷기 격자·A*·카메라 범위·정렬선(sort_line)·나무 단계(10/30/60)·밤(19~06시). 테스트 페이지(design/yard_test) 이식
- 화면 `ui/YardScene.tsx`: 2160×3100 캔버스를 카드 폭 1080px 기준으로 축소, 보이는 타일만, README draw_order대로 zIndex(sort_y + sort_line), 밤 = 그림마다 tintColor 덮개(정원등·텐트는 night_file), 끌기 = 둘러보기(3초 뒤 1.2초 복귀), 탭 = 걸어감, 두 손가락 줌 0.6~1(저장, 나갔다 와도 유지), 왼쪽 끝에서 오른쪽으로 끌면 방으로(`onLeave`). gesture-handler v3 hooks + reanimated, 루트에 GestureHandlerRootView
- 밤 단짝: 밤 색을 미리 입힌 클립 한 장(`hippo_<clip>_night.webp`, `scripts/gen_yard_night_pet.py`, Pillow 필요 — 캐릭터 export·밤 색 바뀌면 다시 실행). 움직이는 그림 두 장(본체 + tintColor 덮개)을 겹치면 폰에서 각자 재생돼 어두운 형체가 따로 놂(2026-11-11 대표 발견, 수정). 정지 그림 소품은 덮개 방식 그대로
- 단짝: 걷기 = 25° 걷기 클립(walk_front/side/back, 왼쪽 = 옆 뒤집기), 속도 땅 위 0.9단위/초(세로는 0.426배) — character manifest walk. 서 있기·자리 동작(벤치·물장구·열매 보여주기 등)은 25° 동작 클립 오기 전까지 garden_idle + 통통 튀기 임시. 혼자 돌아다니다 3번째마다 산 소품·연못·나무로 감
- `screens/YardPage.tsx`: 잠김 화면(남은 날 카운트 없음: "기록한 날이 7일이 되면 열려"), 잠긴 구역·문 탭 → 구매 시트, 상점에서 산 소품만 표시(상점 '마당 꾸미기' 섹션, 사면 마당으로 이동), 열매 탭 → 단짝이 나무로 가서 카드(S11 문구 "한 달 전 오늘, 너는 이걸 해냈어"/"M월 D일, 너는 이걸 해냈어" + 원문). 자해 키워드에 걸리는 기록은 앱에서 한 번 더 걸러 다른 기록으로(서버는 버틴 하루만 제외). 딴 열매는 그 화면에 있는 동안만 사라짐. 손님(참새·나비) 마당 들어올 때 30%, 피크닉 매트에서 먹이기(수확 바구니 먹을 것), ⚙︎ 테스트 스위치(테스터 계정 또는 개발 빌드에서만 보임, 서버가 테스터만 허용): 마당 바로 열기/끄기, 구역 모두 열기, 씨앗 +500, 밤/낮 바꾸기
- 웹 확인(393×852, 테스트 계정 삭제함): 잠금/열림, 밤 색, 열매 → 나무로 걸어가 카드, 잠긴 구역 탭 → 시트 → 60씨앗으로 구매 후 울타리 사라짐, 씨앗 +500, 매트 먹이기 "냠냠", 두 손가락 줌 1→0.85 유지, 텐트 구매 → 마당 이동·앞뒤 순서, 왼쪽 끝 끌기 → 방, 뒤로 걷기 클립
- 자리 동작 (2026-11-11): character manifest `yard_actions` → `PET_YARD_ACTIONS`(gen_pet_clips.py). YardScene이 in → loop(반복 횟수로 5~10초) → out 순서로 재생, 물장구는 첫 뜀 4~15프레임에 연못 가장자리(enter) → 물속(stand) 이동. 동작 중 다른 곳을 누르면 그 동작은 바로 멈추고 출발(대표 결정 2026-11-11, 물장구 중이면 연못 가장자리에서 나옴). 못 끝낸 먹이기는 안 먹은 걸로(바구니 그대로), 열매 보여주기는 카드만 바로 열어 줌. 단짝 클립은 두 겹(새 클립 첫 프레임이 뜨면 이전 것 제거, 단계 타이머도 첫 프레임부터, 5초 넘으면 그냥 진행). 동작 중엔 클립 홀드아웃이 소품을 가리므로 벤치·해먹·화단 바로 위에 그림(ACT_OVER). 먹이기 = `walkTo('picnic_mat', 콜백, { eat })` 이미 앉아 있으면 그 자리에서 먹기만 끼움. 먹을 게 없으면 매트 탭 = 앉아 쉬기
- 마당 들어올 때마다 단짝은 하던 것 없이 첫 구역 화면 가운데에서 대기로 시작, 카메라도 가운데(3~5초 뒤 혼자 놀기). 다른 공간으로 나가면 그 자리에서 멈춤(동작 취소, 대기 클립). 대표 요청 2026-11-11
- 소품 탭 판정: `scripts/gen_yard_hit.py`(Pillow) → `data/yardHit.ts` 12px 알파 격자, 앞(sort_y 큰) 소품부터. 동작 없는 소품 = item_blocked 옆(단짝과 가까운 쪽)에 섬
- 밤 클립: gen_yard_night_pet.py가 yard_actions 클립까지 모두 만들고 `data/petNight.ts`(require 표) 생성. 같은 프레임이 합쳐진 WebP는 프레임별 길이를 그대로 옮김. pet 에셋 38MB(낮+밤) — 출시 전 줄일 것
- 방 넓히기 (2026-11-11): RoomPage = 2160 캔버스를 카드 창으로 끌어 보기(pan, 자동 복귀 없음, 위치는 앱 켜 둔 동안 유지), 끝을 넘겨 끌면 옆 공간이 따라 옴. 페이지 끌기는 `ui/pager.ts`(index가 만든 worklet 2개: drag/end)로 통일: 방 그림 밖(여백·기록 칸) 끌기, 방 그림 끝을 넘긴 끌기, 마당 왼쪽 끝을 넘긴 끌기 모두 바깥 스크롤을 UI 스레드(reanimated scrollTo)에서 손가락에 붙여 움직이고, 놓으면 1/4 넘게·빠르게(500px/s) 끌었으면 옆 페이지, 아니면 제자리로 부드럽게(withTiming). 예전 JS scrollTo·문턱 넘으면 바로 넘김 방식은 끊기고 툭 넘어가서 바꿈(2026-11-11 대표 피드백). 웹은 scroll-snap이 끌기를 되돌려서 바깥 스크롤이 꺼진 페이지에선 pagingEnabled 끔. 마당 제스처 설정은 useMemo로 한 번만 만듦(걷는 중 다시 그려져도 끌기 유지). 한 번 끌기 = 한 페이지: pager가 시작 페이지를 기억하고, 맞추는 동안 늦게 온 끌기·두 번째 놓기는 무시(마당→방이 텃밭까지 넘어가던 문제). 끄는 동안 보이는 건 시작 페이지의 바로 옆 페이지까지만(마당에서 끌어도 텃밭은 안 보임), 손가락 값이 숫자가 아니면(NaN) 무시 — 마당에서 미세하게 끌 때 텃밭이 한 프레임씩 튀던 문제(2026-11-11 대표 슬로모션 영상). 진짜 원인: pager의 공유값(시작 페이지 등)을 JS 스레드(runOnJS 제스처: 마당 끌기·방 그림 끌기)에서 읽고 쓰면, JS에서 쓴 값은 UI에 비동기로 반영되고 읽기는 UI 값을 동기로 가져와서 방금 쓴 시작 페이지가 -1로 읽힘 → 0(텃밭)으로 scrollTo. 방 여백 끌기는 UI 스레드 worklet이라 멀쩡했음. 그래서 pager.drag/end는 JS에서 불리면 scheduleOnUI로 UI 스레드에서 실행(공유값 읽고 쓰는 로직은 UI 스레드 한 곳에서만). ⏳ 출시 후: 방↔텃밭을 천천히 끌 때 여전히 툭 끊기는 느낌(대표 확인, 출시 후로 미룸). 방 페이지에선 바깥 ScrollView 끌기 끔(마당과 같은 방식). 유리장: 병 뒤 → 구슬 점 → 병 앞 → 유리 순서, 구슬 수 = 병 구슬 수/50 × 칸 수, 색 = jarMarbles 순서
- 웹 확인(390×844, 테스트 계정 170개 기록): 방 끌기 양끝·옆 공간 넘김, 유리장 3병 + 구슬, 병 탭 → /jar/1, 벤치·물장구·해먹·화단·매트 딸기 먹기(바구니 3→2). 헤드리스 탭은 rAF가 느려 동작이 늦게 보임(Page.bringToFront 후 정상)
- 남은 것: 실제 폰(Expo Go) 확인, 마당 열리는 1회 연출(WORLD 브레인스토밍 8, 미정), 실제 폰(Expo Go) 확인
