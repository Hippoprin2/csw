#!/usr/bin/env python3
"""테스터 추가(마당 ⚙︎ 테스트 스위치 권한): 이메일로 사용자를 찾아 testers 표에 넣음.
사용: python3 scripts/add_tester.py someone@example.com
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE

email = sys.argv[1].strip().lower()
_, d = req('GET', '/auth/v1/admin/users?per_page=1000', token=SERVICE, key=SERVICE)
hits = [u for u in d['users'] if (u.get('email') or '').lower() == email]
if not hits:
    print('not found:', email)
    sys.exit(1)
for u in hits:
    s, r = req('POST', '/rest/v1/testers', {'user_id': u['id']}, token=SERVICE, key=SERVICE)
    print(u['id'], (u.get('app_metadata') or {}).get('provider'), 'insert', s, '' if s < 300 else r)
_, t = req('GET', '/rest/v1/testers?select=user_id', token=SERVICE, key=SERVICE)
ids = {r['user_id'] for r in t}
print('tester:', all(u['id'] in ids for u in hits))
