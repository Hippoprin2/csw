#!/usr/bin/env python3
"""iOS 시뮬레이터 앱에 테스트 계정으로 로그인 (개발 전용).
앱이 EXPO_PUBLIC_SIM_TEST=1로 빌드돼 있어야 함 (lib/auth.ts sessionFromUrl, 실기기에선 무시).
사용: python3 scripts/sim_login.py [UDID]  → 새 테스트 계정 만들고 csw://auth/callback?sim_refresh=… 열기, uid 출력
지우기: python3 scripts/web_test_session.py --delete <uid>"""
import json, subprocess, sys, pathlib, urllib.parse
here = pathlib.Path(__file__).parent
out = subprocess.run([sys.executable, str(here / 'web_test_session.py')], capture_output=True, text=True, check=True).stdout
d = json.loads(out)
udid = sys.argv[1] if len(sys.argv) > 1 else 'booted'
url = 'csw://auth/callback?sim_refresh=' + urllib.parse.quote(d['session']['refresh_token'])
subprocess.run(['xcrun', 'simctl', 'openurl', udid, url], check=True)
print(d['uid'])
