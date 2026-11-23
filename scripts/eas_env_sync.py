#!/usr/bin/env python3
"""mobile/.env.local 의 EXPO_PUBLIC_* 값을 EAS 환경 변수(development/preview/production)로 올림.
EAS 빌드는 git에 없는 .env.local 을 못 보므로 값이 바뀌면 다시 실행. 값은 출력하지 않음.
EXPO_PUBLIC_SIM_TEST 는 시뮬레이터 로그인용이라 절대 올리지 않음.
사용: python3 scripts/eas_env_sync.py"""
import pathlib, subprocess

MOBILE = pathlib.Path(__file__).resolve().parent.parent / "mobile"
for line in (MOBILE / ".env.local").read_text().splitlines():
    if not line.startswith("EXPO_PUBLIC_") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    v = v.strip().strip('"').strip("'")
    if k == "EXPO_PUBLIC_SIM_TEST":
        continue
    r = subprocess.run(["npx", "-y", "eas-cli@latest", "env:create", "--name", k, "--value", v,
                        "--environment", "development", "--environment", "preview", "--environment", "production",
                        "--visibility", "plaintext", "--scope", "project", "--non-interactive", "--force"],
                       cwd=MOBILE, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    print(k, "ok" if r.returncode == 0 else "FAIL " + (r.stderr or r.stdout).strip().splitlines()[-1])
