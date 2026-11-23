#!/bin/sh
# EAS 빌드 (클라우드). 사용: scripts/eas_build.sh <development|development-device|preview|production> <ios|android|all>
# EAS_NO_VCS=1: .git(800MB+)을 올리지 않고 루트 .easignore 기준으로 mobile/만 올림(약 23MB).
# 환경 변수(EXPO_PUBLIC_*)는 EAS에 있음 — .env.local 바뀌면 python3 scripts/eas_env_sync.py
set -e
cd "$(dirname "$0")/../mobile"
EAS_NO_VCS=1 npx -y eas-cli@latest build --profile "${1:-development}" --platform "${2:-all}" --non-interactive --no-wait < /dev/null
