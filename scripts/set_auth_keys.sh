#!/bin/zsh
# 로그인 키를 루트 .env.local에 저장 (입력값은 화면에 안 보임). 모르는 건 그냥 Enter로 건너뛰기.
f="$HOME/projects/csw/.env.local"
touch "$f"; chmod 600 "$f"
for name in KAKAO_CLIENT_ID KAKAO_CLIENT_SECRET GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET RESEND_API_KEY; do
  read -s "v?$name 붙여넣고 Enter (없으면 그냥 Enter): "; echo
  if [[ -n "$v" ]]; then
    grep -v "^$name=" "$f" > "$f.tmp"; mv "$f.tmp" "$f"; chmod 600 "$f"
    printf '%s=%s\n' "$name" "$v" >> "$f"
    echo "  → $name 저장됨"
  fi
  unset v
done
echo 끝. 하마대장에게 '키 넣었어'라고 알려줘.
