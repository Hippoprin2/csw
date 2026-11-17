#!/usr/bin/env python3
"""기록 권한·구독 라이프사이클 테스트 (2026-11-18 DB 검토 B1~B7).
무료 중 → 무료 끝 → 구독 → 만료 → 재구독, 테스터 예외, 끝나도 되는 것(고치기·☆·삭제·심기), 권한 없는 계정으로 익명 기록 옮기기(B5),
계정 삭제 뒤 결제 기록 보관(B2). 구독 줄은 웹훅 대신 service_role로 직접 넣음.
사용: python3 scripts/test_access.py   (test_anon.py와 같은 준비 필요)
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

KST = timezone(timedelta(hours=9))
iso = lambda t: t.astimezone(timezone.utc).isoformat()
now = lambda: datetime.now(timezone.utc)
def rpc(T, name, body=None): return req('POST', f'/rest/v1/rpc/{name}', body or {}, token=T)
def svc(method, path, body=None): return req(method, path, body, token=SERVICE, key=SERVICE)
def win(T, text='물 한 잔', d=None):
    b = {'p_text': text, 'p_category': 'eat', 'p_source': 'user'}
    if d: b['p_win_date'] = d
    return rpc(T, 'record_win', b)
def set_trial(uid, t): svc('PATCH', f'/rest/v1/profiles?id=eq.{uid}', {'trial_ends_at': iso(t)})
def sub(uid, start, end, status='active', tx='1'):
    s, r = svc('POST', '/rest/v1/subscriptions', {'user_id': uid, 'store': 'test', 'product_id': 'csw.monthly',
        'original_transaction_id': f'orig-{uid[:8]}', 'transaction_id': f'tx-{uid[:8]}-{tx}',
        'period_start': iso(start), 'expires_at': iso(end), 'status': status, 'environment': 'sandbox'})
    assert s in (200, 201), (s, r)
def anon():
    s, a = req('POST', '/auth/v1/signup', {})
    made.append(a['user']['id'])
    return a['access_token'], a['user']['id']

try:
    T, U = temp_user(); made.append(U)
    p = svc('GET', f'/rest/v1/profiles?id=eq.{U}&select=*')[1][0]
    te = datetime.fromisoformat(p['trial_ends_at'])
    tk = te.astimezone(KST)
    check('무료 끝 = KST 자정', (tk.hour, tk.minute, tk.second) == (0, 0, 0), tk)
    check('무료 끝 = 가입 + 14일인 날의 끝', tk.date() == (datetime.fromisoformat(p['signed_up_at']).astimezone(KST) + timedelta(days=15)).date(), (p['signed_up_at'], tk))
    st = rpc(T, 'access_state')[1]
    check('무료 중: access_state.access', st.get('access') is True and st.get('tester') is False, st)
    s, r = win(T); check('무료 중: 기록 됨', s == 200, (s, r))
    w1 = r['win']['id']

    # 무료 끝 → 새 기록만 잠김 (B7-B: 어제 기록도 잠김)
    set_trial(U, now() - timedelta(minutes=1))
    s, r = win(T); check('무료 끝: 오늘 기록 거절 (subscription_required)', s >= 400 and 'subscription_required' in str(r), (s, r))
    yday = (datetime.now(KST).date() - timedelta(days=1)).isoformat()
    s, r = win(T, d=yday); check('무료 끝: 어제 기록도 거절 (B7-B)', s >= 400 and 'subscription_required' in str(r), (s, r))
    check('무료 끝: access_state.access false', rpc(T, 'access_state')[1].get('access') is False)
    s, r = rpc(T, 'edit_win', {'p_id': w1, 'p_text': '물 두 잔', 'p_category': 'eat'}); check('무료 끝: 고치기는 됨', s == 200, (s, r))
    s, r = rpc(T, 'set_win_note', {'p_id': w1, 'p_note': '시원했다'}); check('무료 끝: 메모는 됨', s == 200, (s, r))
    s, r = rpc(T, 'set_win_star', {'p_id': w1, 'p_on': True}); check('무료 끝: ☆는 됨', s == 200, (s, r))
    s, r = rpc(T, 'plant', {'p_slot': 1, 'p_crop': 'sweet_potato'}); check('무료 끝: 심기는 됨', s == 200, (s, r))
    s, r = req('GET', f'/rest/v1/subscriptions?select=*', token=T); check('구독 이력: 본인 것만 읽기(아직 없음)', s == 200 and r == [], (s, r))

    # 구독 → 기록 됨
    sub(U, now() - timedelta(days=1), now() + timedelta(days=29), tx='1')
    s, r = win(T, '구독 첫 기록'); check('구독 중: 기록 됨', s == 200, (s, r))
    st = rpc(T, 'access_state')[1]; check('구독 중: access_state에 만료일·상태', st.get('access') and st.get('sub_status') == 'active' and st.get('sub_expires_at'), st)
    s, r = svc('PATCH', f'/rest/v1/subscriptions?user_id=eq.{U}', {'status': 'cancelled'})
    s, r = win(T, '해지했지만 기간 남음'); check('해지(자동 갱신 끔)해도 기간 끝까지 기록 됨', s == 200, (s, r))
    s, r = req('POST', '/rest/v1/subscriptions', {'user_id': U, 'store': 'test', 'product_id': 'x', 'original_transaction_id': 'x', 'transaction_id': 'x',
        'period_start': iso(now()), 'expires_at': iso(now() + timedelta(days=365)), 'status': 'active'}, token=T)
    check('구독 줄 앱에서 직접 insert 불가', s >= 400, s)
    s, r = req('PATCH', f'/rest/v1/subscriptions?user_id=eq.{U}', {'expires_at': iso(now() + timedelta(days=999))}, token=T)
    check('구독 줄 앱에서 직접 수정 불가', s >= 400 or r == [], (s, r))

    # 만료 → 잠김, 결제 유예 → 됨, 환불 → 잠김
    svc('PATCH', f'/rest/v1/subscriptions?user_id=eq.{U}', {'status': 'expired', 'expires_at': iso(now() - timedelta(minutes=1))})
    s, r = win(T); check('구독 만료: 기록 거절', s >= 400 and 'subscription_required' in str(r), (s, r))
    sub(U, now() - timedelta(minutes=1), now() + timedelta(days=16), status='grace', tx='2')
    s, r = win(T, '유예 중'); check('결제 유예: 기록 됨', s == 200, (s, r))
    svc('PATCH', f'/rest/v1/subscriptions?transaction_id=eq.tx-{U[:8]}-2', {'status': 'refunded'})
    s, r = win(T); check('환불: 기록 거절', s >= 400 and 'subscription_required' in str(r), (s, r))

    # 재구독 → 새 줄, 이력 그대로
    sub(U, now(), now() + timedelta(days=30), tx='3')
    s, r = win(T, '다시 구독'); check('재구독: 기록 됨', s == 200, (s, r))
    rows = req('GET', '/rest/v1/subscriptions?select=transaction_id,status&order=id', token=T)[1]
    check('재구독: 이전 이력 3줄 그대로', [x['status'] for x in rows] == ['expired', 'refunded', 'active'], rows)

    # 테스터 예외: 무료 끝·구독 없어도 기록 됨
    T2, U2 = temp_user(); made.append(U2)
    set_trial(U2, now() - timedelta(days=1))
    s, r = win(T2); check('테스터 아님 + 무료 끝: 거절', s >= 400, (s, r))
    svc('POST', '/rest/v1/testers', {'user_id': U2})
    s, r = win(T2); check('테스터: 무료 끝나도 기록 됨', s == 200, (s, r))
    svc('DELETE', f'/rest/v1/testers?user_id=eq.{U2}')

    # B5: 권한 없는 계정으로 익명 기록 옮기면 기록만, 씨앗(= 기록한 날 수)은 안 옮김
    set_trial(U2, now() - timedelta(days=1))
    rpc(T2, 'give_consent', {'p_version': '2026-11-18', 'p_onboard': True})  # 이미 쓰던 계정 (새 계정 선물 대상 아님)
    bal_before = rpc(T2, 'seed_balance')[1]
    TA, A = anon()
    rpc(TA, 'give_consent', {'p_version': '2026-11-18'})
    s, r = win(TA, '익명으로 우회'); check('익명: 기록 1개', s == 200, (s, r))
    s, r = req('POST', '/functions/v1/claim-anon', {'anon_token': TA}, token=T2)
    check('권한 없는 계정으로 옮기기: 기록은 옮김, 씨앗은 안 옮김', s == 200 and r.get('moved') == 1 and r.get('seeds_moved') is False, (s, r))
    check('권한 없는 계정: 씨앗 그대로', rpc(T2, 'seed_balance')[1] == bal_before, (bal_before, rpc(T2, 'seed_balance')[1]))
    texts = [w['text'] for w in req('GET', '/rest/v1/wins?select=text', token=T2)[1]]
    check('옮긴 기록은 남음', '익명으로 우회' in texts, texts)

    # 권한 있는 계정이면 씨앗도 옮김 (기존 동작)
    T3, U3 = temp_user(); made.append(U3)
    TB, B = anon(); rpc(TB, 'give_consent', {'p_version': '2026-11-18'}); win(TB, '익명 첫 기록')
    s, r = req('POST', '/functions/v1/claim-anon', {'anon_token': TB}, token=T3)
    check('권한 있는 계정으로 옮기기: 씨앗도 옮김', s == 200 and r.get('seeds_moved') is True, (s, r))

    # B2: 계정 삭제해도 결제 기록은 사용자 연결만 끊고 남음
    s, _ = rpc(T, 'delete_my_account'); check('계정 삭제', s in (200, 204), s)
    rows = svc('GET', f'/rest/v1/subscriptions?original_transaction_id=eq.orig-{U[:8]}&select=user_id,user_deleted_at')[1]
    check('삭제 뒤 결제 기록 3줄 보관, user_id 없음, 삭제 시각 있음', len(rows) == 3 and all(x['user_id'] is None and x['user_deleted_at'] for x in rows), rows)
    ev = svc('GET', f'/rest/v1/app_events?user_id=eq.{U}&select=id')[1]
    check('정식 계정 삭제: 이용 통계는 같이 삭제', ev == [], ev)
    svc('DELETE', f'/rest/v1/subscriptions?original_transaction_id=eq.orig-{U[:8]}')
finally:
    for u in made:
        delete_user(u)
    print(f'테스트 계정 {len(made)}개 정리')

print(f'\n{"ALL PASS" if not fails else f"{fails} FAIL"}')
sys.exit(1 if fails else 0)
