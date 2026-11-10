#!/usr/bin/env python3
"""가입 사용자 목록(관리용): id 앞자리, 이메일, 공급자, 가입일, 테스터 여부. 사용: python3 scripts/list_users.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE

_, d = req('GET', '/auth/v1/admin/users?per_page=200', token=SERVICE, key=SERVICE)
_, t = req('GET', '/rest/v1/testers?select=user_id', token=SERVICE, key=SERVICE)
testers = {r['user_id'] for r in t} if isinstance(t, list) else set()
for u in d['users']:
    print(u['id'], u.get('email'), (u.get('app_metadata') or {}).get('provider'), u['created_at'][:10],
          'tester' if u['id'] in testers else '')
