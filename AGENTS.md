# CSW — 에이전트 작업 규칙

여러 Slack 스레드(세션)가 이 리포를 동시에 작업한다.

- 시작 전: docs/STATUS.md와 docs/GAME_DESIGN.md를 읽는다.
- 주제별 문서는 해당 스레드만 고친다:
  - 캐릭터 → docs/CHARACTER.md
  - 아이템/맵/공간 → docs/WORLD.md
  - 기능 → docs/FEATURES.md
  - 유료화 → docs/MONETIZATION.md
- 아트(캐릭터·공간·아이템 공통 기준) → docs/ART_BIBLE.md. 에셋 만드는 스레드는 시작 전에 읽는다. 기준 변경은 STATUS.md 결정 사항에도 남긴다.
  - 앱 개발(코드·스키마·배포) → docs/DEV.md, mobile/, supabase/
  - 데이터 보안 → docs/SECURITY.md
- 다른 주제에 영향을 주는 결정은 docs/STATUS.md의 '결정 사항'에 한 줄로 남긴다.
- 커밋 전에 git pull/status로 다른 세션 변경을 확인한다.
- 사용자에게는 한국어로 답하고, 끝나면 "완료했다"를 붙인다.
