#!/bin/zsh
# OpenAI API 키를 화면/기록에 남기지 않고 .env.local에 저장한다.
f="$HOME/projects/csw/.env.local"
read -s "k?OpenAI 키 붙여넣고 Enter: "
echo
if [ -z "$k" ]; then echo "키가 비어 있어요. 다시 실행해 주세요."; exit 1; fi
touch "$f"; chmod 600 "$f"
grep -v '^OPENAI_API_KEY=' "$f" > "$f.tmp"; mv "$f.tmp" "$f"; chmod 600 "$f"
printf '%s=%s\n' OPENAI_API_KEY "$k" >> "$f"
unset k
echo "저장됨"
