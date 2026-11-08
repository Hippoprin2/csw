#!/usr/bin/env python3
"""프로필 사진 주소가 auth 메타데이터에 남지 않는지 확인."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE  # noqa: E402

KEYS = ('avatar_url', 'picture', 'profile_image', 'thumbnail_image')
ok = True
s, u = req('GET', '/auth/v1/admin/users', token=SERVICE, key=SERVICE)
for x in u['users']:
    meta = x.get('user_metadata') or {}
    ids = [i.get('identity_data') or {} for i in x.get('identities') or []]
    left = [k for k in KEYS if k in meta] + [k for d in ids for k in KEYS if k in d]
    print(x['app_metadata'].get('provider'), 'meta keys:', sorted(meta), '| 남은 사진키:', left)
    ok &= not left

# 새로 만들 때 사진 주소를 넣어도 저장 안 되는지
s, n = req('POST', '/auth/v1/admin/users', {'email': 'csw-test-strip@example.com', 'email_confirm': True,
           'user_metadata': {'avatar_url': 'https://x/y.jpg', 'picture': 'https://x/y.jpg', 'name': '테스트'}}, token=SERVICE, key=SERVICE)
_, g = req('GET', f"/auth/v1/admin/users/{n['id']}", token=SERVICE, key=SERVICE)  # 응답은 입력을 그대로 돌려줄 수 있어 DB에서 다시 읽음
meta = g.get('user_metadata', {})
print('신규 생성 meta(DB):', meta)
ok &= not any(k in meta for k in KEYS) and meta.get('name') == '테스트'
s, p = req('PUT', f"/auth/v1/admin/users/{n['id']}", {'user_metadata': {'avatar_url': 'https://x/z.jpg'}}, token=SERVICE, key=SERVICE)
_, p = req('GET', f"/auth/v1/admin/users/{n['id']}", token=SERVICE, key=SERVICE)
print('수정 후 meta(DB):', p.get('user_metadata'))
ok &= 'avatar_url' not in (p.get('user_metadata') or {})
req('DELETE', f"/auth/v1/admin/users/{n['id']}", token=SERVICE, key=SERVICE)
print('ALL PASS' if ok else 'FAIL')
