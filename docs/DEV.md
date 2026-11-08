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
- 펫: `mobile/src/ui/Pet.tsx` — 프로토타입 꼬마하마 SVG를 부위별 레이어로 나눠 reanimated로 7종 + sit 동작. 최종 캐릭터 에셋이 나오면 이 파일만 교체.

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
