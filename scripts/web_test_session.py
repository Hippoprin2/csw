#!/usr/bin/env python3
"""웹 테스트판 확인용: 임시 테스트 계정 세션(JSON)을 출력. 브라우저 localStorage['sb-<ref>-auth-token']에 넣으면 로그인 상태.
사용: python3 scripts/web_test_session.py  → stdout: {"uid":..., "key":..., "session": {...}}  /  --delete <uid>"""
import json, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE, delete_user  # noqa: E402

if len(sys.argv) > 2 and sys.argv[1] == '--delete':
    delete_user(sys.argv[2]); print('deleted'); sys.exit()
email = f'csw-test-{int(time.time()*1000)}@example.com'
req('POST', '/auth/v1/admin/users', {'email': email, 'email_confirm': True}, token=SERVICE, key=SERVICE)
_, link = req('POST', '/auth/v1/admin/generate_link', {'type': 'magiclink', 'email': email}, token=SERVICE, key=SERVICE)
otp = link.get('email_otp') or link.get('properties', {}).get('email_otp')
_, sess = req('POST', '/auth/v1/verify', {'type': 'email', 'email': email, 'token': otp})
sess.setdefault('expires_at', int(time.time()) + sess.get('expires_in', 3600))
print(json.dumps({'uid': sess['user']['id'], 'key': 'sb-xbifxrvgdimwwijijthl-auth-token', 'session': sess}))
