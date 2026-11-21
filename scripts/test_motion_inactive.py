#!/usr/bin/env python3
"""S25 동작 요청 + 3년 미접속 삭제 테스트 (migration 20261121000001).
사용: python3 scripts/test_motion_inactive.py   (test_anon.py와 같은 준비 필요)
"""
import pathlib, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE, temp_user, delete_user  # noqa: E402

fails = 0
made = []
def check(name, cond, extra=''):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))
    if not cond: fails += 1

iso = lambda t: t.astimezone(timezone.utc).isoformat()
now = lambda: datetime.now(timezone.utc)
def rpc(T, name, body=None): return req('POST', f'/rest/v1/rpc/{name}', body or {}, token=T)
def svc(method, path, body=None): return req(method, path, body, token=SERVICE, key=SERVICE)
def exists(uid): return bool(svc('GET', f'/rest/v1/profiles?id=eq.{uid}&select=id')[1])

try:
    # ── S25 ──
    T, U = temp_user(); made.append(U)
    s, r = rpc(T, 'request_motion', {'p_keyword': '  테니스   치기 ', 'p_category': 'cheer'})
    check('동작 요청 저장', s in (200, 204), (s, r))
    rows = svc('GET', f'/rest/v1/motion_requests?user_id=eq.{U}&select=*')[1]
    check('키워드 공백 정리', len(rows) == 1 and rows[0]['keyword'] == '테니스 치기', rows)
    s, r = rpc(T, 'request_motion', {'p_keyword': 'ㄱ' * 21, 'p_category': 'cheer'})
    check('21자 거절', s >= 400, (s, r))
    s, r = req('GET', f'/rest/v1/motion_requests?select=*', token=T)
    check('앱에서 직접 읽기 불가(RLS)', s == 200 and r == [], (s, r))
    s, r = req('POST', '/rest/v1/motion_requests', {'user_id': U, 'category': 'cheer', 'keyword': 'x'}, token=T)
    check('앱에서 직접 쓰기 불가(RLS)', s >= 400, (s, r))
    for i in range(9): rpc(T, 'request_motion', {'p_keyword': f'동작{i}', 'p_category': 'cheer'})
    s, r = rpc(T, 'request_motion', {'p_keyword': '열한번째', 'p_category': 'cheer'})
    check('하루 10개 한도', s >= 400 and 'too_many' in str(r), (s, r))
    s, a = req('POST', '/auth/v1/signup', {}); made.append(a['user']['id'])
    s, r = rpc(a['access_token'], 'request_motion', {'p_keyword': '등산', 'p_category': 'cheer'})
    check('익명 계정은 거절', s >= 400, (s, r))

    # ── 3년 미접속 ──
    old = iso(now() - timedelta(days=365 * 3 + 5))
    T2, A = temp_user(); made.append(A)   # 안내 없음 → 남음
    T3, B = temp_user(); made.append(B)   # 안내 40일 전 → 삭제
    T4, Cc = temp_user(); made.append(Cc)  # 안내 10일 전 → 남음
    T5, D = temp_user(); made.append(D)   # 안내 40일 전 + 구독 중 → 남음
    T6, E = temp_user(); made.append(E)   # 안내 뒤 다시 접속 → 남음
    for u in (A, B, Cc, D):
        svc('PATCH', f'/rest/v1/profiles?id=eq.{u}', {'last_seen_at': old})
    svc('PATCH', f'/rest/v1/profiles?id=eq.{B}', {'inactive_notice_at': iso(now() - timedelta(days=40))})
    svc('PATCH', f'/rest/v1/profiles?id=eq.{Cc}', {'inactive_notice_at': iso(now() - timedelta(days=10))})
    svc('PATCH', f'/rest/v1/profiles?id=eq.{D}', {'inactive_notice_at': iso(now() - timedelta(days=40))})
    svc('PATCH', f'/rest/v1/profiles?id=eq.{E}', {'inactive_notice_at': iso(now() - timedelta(days=40)), 'last_seen_at': iso(now() - timedelta(days=1))})
    s, r = svc('POST', '/rest/v1/subscriptions', {'user_id': D, 'store': 'test', 'product_id': 'csw.monthly',
        'original_transaction_id': f'orig-{D[:8]}', 'transaction_id': f'tx-{D[:8]}', 'period_start': iso(now() - timedelta(days=3)),
        'expires_at': iso(now() + timedelta(days=27)), 'status': 'active', 'environment': 'sandbox'})
    check('준비: 구독 넣기', s in (200, 201), (s, r))

    due = {x['user_id'] for x in svc('POST', '/rest/v1/rpc/inactive_notice_due', {})[1]}
    check('안내 대상: 안내 안 한 3년 계정 포함', A in due, due)
    check('안내 대상: 이미 안내한 계정·구독 중 제외', not ({B, Cc, D, E} & due), due)
    s, r = rpc(T2, 'purge_inactive_accounts')
    check('삭제 함수는 앱에서 못 부름', s >= 400, (s, r))
    s, n = svc('POST', '/rest/v1/rpc/purge_inactive_accounts', {})
    check('삭제 실행', s == 200, (s, n))
    check('안내 없는 계정 남음', exists(A))
    check('안내 30일 지난 계정 삭제', not exists(B))
    check('안내 30일 안 된 계정 남음', exists(Cc))
    check('구독 중 계정 남음', exists(D))
    check('안내 뒤 다시 접속한 계정 남음', exists(E))
finally:
    for u in made:
        try: delete_user(u)
        except Exception: pass

print('ALL PASS' if fails == 0 else f'{fails} FAIL')
sys.exit(1 if fails else 0)
