# CSW 데이터 보안

담당: 앱 개발 스레드. 최종 수정: 2026-11-09
원칙: 기록은 일기에 가깝다 → 최소 수집, 본인만 접근, 운영자는 기록을 열람하지 않는다.

## 적용된 것
- 접근 제어: 전 테이블 RLS(본인 행만). 쓰기는 security definer 함수로만. authenticated 테이블 권한은 `revoke all` 후 필요한 것만 grant(20261109000003). 새 테이블도 같은 방식 필수
  - 검증: `scripts/test_backend.py`, `scripts/test_garden.py` (직접 insert/수정 차단, 보호 열 수정 차단 포함)
- 인증: 비밀번호 저장 없음(카카오·구글·Apple·이메일 코드). OAuth 리다이렉트는 csw:// 고정
- 전송·저장: HTTPS, Supabase 디스크 암호화(AES-256)
- 기기 안 세션: AES-256 암호화 후 앱 저장공간, 열쇠는 iOS 키체인(AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY) — `mobile/src/lib/supabase.ts`. 예전 평문 세션은 처음 읽을 때 자동 암호화 (2026-11-09 대표 아이폰 Expo Go에서 리로드 후 로그인 유지 확인)
- AI 분류(OpenAI): 문장만 전송(사용자 식별자 없음), store=false. OpenAI는 악용 감시용으로 최대 30일 보관 가능, 학습 미사용(API 기본). 사용자당 하루 80회 한도(`classify_usage`, 넘으면 429 → 앱은 키워드 분류로 저장, 기기 키워드 자해 감지는 계속 동작)
- 자해 감지 기록: 사용자 ID 없이 날짜·출처별 횟수만(`safety_daily`, 앱에서 읽기 불가)
- 분석(`app_events`): 이벤트 이름 + 작은 메타만, 기록 본문 금지
- 최소 수집: 카카오 프로필 사진 주소는 저장 직전 삭제(트리거)
- 삭제: 기록 1개 / 전체 기록 / 계정 삭제(auth 사용자 삭제 → 모든 행 cascade). 테스트로 확인
- 비밀값: DB 비밀번호·service role 키·OpenAI 키·OAuth 시크릿은 루트 `.env.local`(600, gitignore)과 Supabase secrets에만. 앱에는 공개 키(publishable)만

## 출시 전 체크리스트
- [ ] (대표) 2단계 인증: Supabase, Google Cloud, Kakao Developers, OpenAI, Apple, Expo, GitHub
- [ ] Supabase Pro 전환(매일 백업 7일) — 2026-11-09 대표 결정: 앱이 커지면. 그 전 위험: 무료 프로젝트는 7일 동안 요청이 없으면 일시정지, 자동 백업 복원 없음 → 필요하면 이 맥에서 매일 DB 덤프로 대체. 전환 시 처리방침에 백업 보관 기간 명시
- [ ] 열쇠 교체: service role/secret 키, OpenAI 키(새 키 → supabase secrets set), 카카오·구글 시크릿, DB 비밀번호. 교체 후 test_backend 재실행
- [x] 이 맥 FileVault 켜짐 (2026-11-09 확인)
- [ ] 처리방침: 수집 항목(이메일, 카카오 닉네임, 기록, 이용 이벤트), 보관 기간, 국외 이전(Supabase 일본 도쿄 / OpenAI 미국), 운영자 기록 열람 금지, 자해 감지는 익명 집계만, 14세 이상
- [ ] 이후 검토: 앱 잠금(Face ID), OpenAI 무보관(ZDR) 신청 가능 여부

## 유출 대응 (개인정보보호법)
1. 인지 즉시: 원인 차단(키 폐기·교체, 해당 계정 세션 만료, 필요하면 서비스 일시 중지), 시각·범위 기록
2. 72시간 안에 사용자 통지: 유출 항목, 시점·경위, 피해 최소화 방법, 대응 조치, 문의처
3. 신고: 1천 명 이상이거나 민감정보·해킹에 의한 유출이면 개인정보보호위원회 또는 KISA에 72시간 안에 신고 (최신 기준은 신고 시점에 다시 확인)
4. 사후: 원인 분석, 재발 방지, 이 문서 갱신
- 연락 담당: 대표(운영자). 기술 조치: 앱 개발 스레드
