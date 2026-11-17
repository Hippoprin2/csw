#!/usr/bin/env python3
"""익명(가입 전) 계정 테스트 — 2026-11-17 첫 실행 순서 변경 (가입을 첫 기록 축하 뒤로).
익명 RLS(남의 기록 못 봄, 서버 소유 칸 PATCH 불가), 가입 전 막힌 기능, 익명→정식 연결 시 무료·선물,
기존 계정으로 첫 기록 옮기기(claim-anon), 7일 지난 익명 계정 삭제, 분류 IP 한도.
사용: python3 scripts/test_anon.py   (test_backend.py와 같은 .env.local 필요, IP 한도 확인엔 Supabase 관리 토큰(CLI 로그인) 필요)
만든 테스트 계정은 끝에 모두 지움."""
import base64, hashlib, json, os, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from sb import req, SERVICE, URL

fails = 0
made = []
def check(name, cond, extra=''):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))
    if not cond: fails += 1

def anon():
    s, a = req('POST', '/auth/v1/signup', {})
    assert s == 200, (s, a)
    made.append(a['user']['id'])
    return a['access_token'], a['user']['id']

def member(onboard=True):
    email = f'csw-anontest-{int(time.time()*1000)}@example.com'
    req('POST', '/auth/v1/admin/users', {'email': email, 'email_confirm': True}, token=SERVICE, key=SERVICE)
    s, link = req('POST', '/auth/v1/admin/generate_link', {'type': 'magiclink', 'email': email}, token=SERVICE, key=SERVICE)
    otp = link.get('email_otp') or link.get('properties', {}).get('email_otp')
    s, sess = req('POST', '/auth/v1/verify', {'type': 'email', 'email': email, 'token': otp})
    T, uid = sess['access_token'], sess['user']['id']
    made.append(uid)
    if onboard:
        now = datetime.now(timezone.utc).isoformat()
        req('PATCH', f'/rest/v1/profiles?id=eq.{uid}', {'pet_name': '두부'}, token=T)
        consent(T, onboard=True)
    return T, uid

def consent(T, onboard=False):  # 동의 칸은 서버 함수로만 (2026-11-18)
    s, r = req('POST', '/rest/v1/rpc/give_consent', {'p_version': '2026-11-18', 'p_onboard': onboard}, token=T)
    assert s in (200, 204), (s, r)

def trial_end_for(t):  # 가입 + 14일을 그날 24시(KST)로 올림
    k = timezone(timedelta(hours=9))
    d = (t.astimezone(k) + timedelta(days=14)).date() + timedelta(days=1)
    return datetime(d.year, d.month, d.day, tzinfo=k)

def prof(uid):
    return req('GET', f'/rest/v1/profiles?id=eq.{uid}&select=*', token=SERVICE, key=SERVICE)[1][0]

def mgmt_sql(q):
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Supabase CLI', '-w'], capture_output=True, text=True).stdout.strip()
    if raw.startswith('go-keyring-base64:'): raw = base64.b64decode(raw.split(':', 1)[1]).decode()
    if not raw: return None
    ref = URL.split('//')[1].split('.')[0]
    r = urllib.request.Request(f'https://api.supabase.com/v1/projects/{ref}/database/query', method='POST',
        data=json.dumps({'query': q}).encode(), headers={'Authorization': 'Bearer ' + raw, 'Content-Type': 'application/json', 'User-Agent': 'csw-test'})
    with urllib.request.urlopen(r) as res: return json.loads(res.read() or 'null')

try:
    # ── 익명 계정: 기록·분류는 되고, 구매 등은 가입 뒤
    TA, A = anon(); TB, B = anon()
    s, u = req('GET', '/auth/v1/user', token=TA); check('익명 로그인 (is_anonymous)', u.get('is_anonymous') is True, u)
    check('익명도 프로필 생성, 무료 기간 아직 없음', prof(A)['trial_ends_at'] is None, prof(A))
    now = datetime.now(timezone.utc).isoformat()
    s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '이불 갰다', 'p_category': 'tidy'}, token=TA)
    check('동의 전: 기록 거절 (consent_required)', s >= 400 and 'consent_required' in str(r), (s, r))
    s, r = req('POST', '/functions/v1/classify', {'text': '물 한 잔 마셨다'}, token=TA)
    check('동의 전: AI 분류 안 보냄', s >= 400 and s != 429, (s, r))
    s, _ = req('PATCH', f'/rest/v1/profiles?id=eq.{A}', {'consented_at': now}, token=TA)
    check('동의 칸 직접 PATCH 불가', s >= 400, s)
    s, _ = req('PATCH', f'/rest/v1/profiles?id=eq.{A}', {'pet_name': '콩이'}, token=TA)
    consent(TA)
    check('익명: 이름·동의(판 포함) 저장', s in (200, 204) and prof(A)['pet_name'] == '콩이' and prof(A)['consent_version'] == '2026-11-18', s)
    s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '이불 갰다', 'p_category': 'tidy'}, token=TA)
    check('익명: 첫 기록 +3', s == 200 and r['earned'] == 3 and r['first'], r)
    a_win = r['win']['id']
    s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '물 마셨다', 'p_category': 'eat'}, token=TA)
    check('익명: 두 번째 기록은 가입 뒤 (signup_required)', s >= 400 and 'signup_required' in str(r), (s, r))
    s, r = req('POST', '/functions/v1/classify', {'text': '물 한 잔 마셨다'}, token=TA)
    check('익명: 분류 함수', s == 200 and r.get('category'), (s, r))
    s, _ = req('POST', '/rest/v1/app_events', {'user_id': A, 'name': 'ob_first_win', 'props': {'category': 'tidy'}}, token=TA)
    check('익명: 이벤트 저장', s in (200, 201), s)
    s, r = req('POST', '/rest/v1/rpc/buy_item', {'p_item_id': 'big_plant'}, token=TA)
    check('익명: 구매는 가입 뒤 (signup_required)', s >= 400 and 'signup_required' in json.dumps(r), (s, r))
    s, r = req('POST', '/rest/v1/rpc/plant', {'p_slot': 0, 'p_crop': 'sweet_potato'}, token=TA)
    check('익명: 심기도 가입 뒤', s >= 400 and 'signup_required' in json.dumps(r), (s, r))
    # RLS: B는 A를 못 봄
    s, w = req('GET', f'/rest/v1/wins?id=eq.{a_win}&select=id', token=TB); check('익명 B가 A 기록 못 봄', w == [], w)
    s, p = req('GET', f'/rest/v1/profiles?id=eq.{A}&select=id', token=TB); check('익명 B가 A 프로필 못 봄', p == [], p)
    s, _ = req('PATCH', f'/rest/v1/profiles?id=eq.{A}', {'pet_name': '해킹'}, token=TB)
    check('익명 B가 A 프로필 못 고침', prof(A)['pet_name'] == '콩이', s)
    s, _ = req('DELETE', f'/rest/v1/wins?id=eq.{a_win}', token=TB)
    s, w = req('GET', f'/rest/v1/wins?id=eq.{a_win}&select=id', token=TA); check('익명 B가 A 기록 못 지움', len(w) == 1, w)
    # 서버 소유 칸
    for col, val in [('trial_ends_at', '2099-01-01T00:00:00Z'), ('marbles_total', 999)]:
        s, r = req('PATCH', f'/rest/v1/profiles?id=eq.{A}', {col: val}, token=TA)
        check(f'익명: {col} 직접 PATCH 불가', s >= 400, (s, r))
    s, r = req('PATCH', f'/rest/v1/wins?id=eq.{a_win}', {'jar_no': 9}, token=TA); check('익명: wins 직접 PATCH 불가', s >= 400, (s, r))
    s, r = req('POST', '/rest/v1/seed_ledger', {'user_id': A, 'delta': 99, 'reason': 'win'}, token=TA); check('익명: 씨앗 직접 insert 불가', s >= 400, s)
    s, r = req('POST', '/rest/v1/rpc/claim_anon_data', {'p_anon': B, 'p_target': A}, token=TA); check('claim_anon_data 앱에서 직접 호출 불가', s >= 400, (s, r))

    # ── 익명 → 정식 연결 (앱에선 linkIdentity / updateUser email. 여기선 관리 API로 이메일 확인 = 같은 is_anonymous 전환)
    s, r = req('PUT', f'/auth/v1/admin/users/{A}', {'email': f'csw-anonlink-{A[:8]}@example.com', 'email_confirm': True}, token=SERVICE, key=SERVICE)
    s, u = req('GET', f'/auth/v1/admin/users/{A}', token=SERVICE, key=SERVICE)
    if u.get('is_anonymous'):  # 관리 API가 전환 안 하면 DB에서 직접 (트리거 확인용)
        mgmt_sql(f"update auth.users set is_anonymous = false where id = '{A}'")
    p = prof(A)
    te = datetime.fromisoformat(p['trial_ends_at'].replace('Z', '+00:00')) if p['trial_ends_at'] else None
    check('연결 시 무료 종료일 = 지금+14일을 그날 24시(KST)로', te and te == trial_end_for(datetime.now(timezone.utc)), (p, trial_end_for(datetime.now(timezone.utc))))
    check('연결 시 가입 시각 저장', p['signed_up_at'] is not None, p)
    check('연결 시 온보딩 완료', p['onboarded_at'] is not None, p)
    s, b = req('POST', '/rest/v1/rpc/seed_balance', {}, token=SERVICE, key=SERVICE)
    s, rows = req('GET', f'/rest/v1/seed_ledger?user_id=eq.{A}&select=delta,reason', token=SERVICE, key=SERVICE)
    check('연결 시 선물 씨앗 6 + 첫 기록 3', sorted(r['delta'] for r in rows) == [3, 6], rows)
    s, w = req('GET', f'/rest/v1/wins?user_id=eq.{A}&select=id', token=SERVICE, key=SERVICE); check('연결해도 첫 기록 그대로', len(w) == 1, w)

    # ── 기존 계정으로 로그인 → 첫 기록 옮기기
    TM, M = member()
    req('POST', '/rest/v1/rpc/record_win', {'p_text': '예전 기록', 'p_category': 'cheer'}, token=TM)
    TC, C = anon()
    req('PATCH', f'/rest/v1/profiles?id=eq.{C}', {'pet_name': '새이름'}, token=TC); consent(TC)
    s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '물 한 잔 마셨다', 'p_category': 'eat'}, token=TC)
    s, r = req('POST', '/functions/v1/claim-anon', {'anon_token': TM}, token=TM); check('claim: 익명 아닌 토큰 거부', s >= 400, (s, r))
    s, r = req('POST', '/functions/v1/claim-anon', {'anon_token': TC}, token=TB); check('claim: 익명 계정끼리 거부', s >= 400, (s, r))
    s, r = req('POST', '/functions/v1/claim-anon', {'anon_token': TC}, token=TM)
    check('claim: 기존 계정으로 옮김 (moved 1, 새 계정 아님)', s == 200 and r.get('moved') == 1 and r.get('target_new') is False, (s, r))
    s, w = req('GET', '/rest/v1/wins?select=text,jar_no&order=created_at', token=TM)
    check('claim: 기존 계정 기록 2개 (옮긴 기록 포함)', [x['text'] for x in w] == ['예전 기록', '물 한 잔 마셨다'], w)
    check('claim: 기존 계정 이름은 그대로', prof(M)['pet_name'] == '두부', prof(M)['pet_name'])
    s, rows = req('GET', f'/rest/v1/seed_ledger?user_id=eq.{M}&reason=eq.onboarding_gift&select=id', token=SERVICE, key=SERVICE)
    check('claim: 기존 계정엔 선물 없음', rows == [], rows)
    s, u = req('GET', f'/auth/v1/admin/users/{C}', token=SERVICE, key=SERVICE); check('claim: 옮긴 뒤 익명 계정 삭제', s == 404, s)
    s, r = req('POST', '/functions/v1/claim-anon', {'anon_token': TC}, token=TM); check('claim: 두 번째는 실패', s >= 400, (s, r))
    # 새로 만든 계정(온보딩 전)으로 로그인 → 가입과 같게
    TN, N = member(onboard=False)
    TD, D = anon()
    req('PATCH', f'/rest/v1/profiles?id=eq.{D}', {'pet_name': '말랑'}, token=TD); consent(TD)
    req('POST', '/rest/v1/rpc/record_win', {'p_text': '10분 산책', 'p_category': 'move'}, token=TD)
    s, r = req('POST', '/functions/v1/claim-anon', {'anon_token': TD}, token=TN)
    p = prof(N)
    check('claim: 새 계정이면 target_new, 이름·동의·온보딩 옮김', s == 200 and r.get('target_new') is True and p['pet_name'] == '말랑' and p['onboarded_at'] and p['consented_at'], (s, r, p))
    check('claim: 새 계정 무료 기간 있음', p['trial_ends_at'] is not None, p)
    s, b = req('POST', '/rest/v1/rpc/seed_balance', {}, token=TN); check('claim: 새 계정 선물 6 + 기록 3', b == 9, b)

    # ── 7일 지난 익명 계정 자동 삭제
    TE, E = anon()
    req('POST', '/rest/v1/app_events', {'user_id': E, 'name': 'ob_test_left', 'props': {}}, token=TE)
    if mgmt_sql(f"update auth.users set created_at = now() - interval '8 days' where id = '{E}'") is not None:
        mgmt_sql('select public.purge_stale_anon()')
        s, u = req('GET', f'/auth/v1/admin/users/{E}', token=SERVICE, key=SERVICE); check('7일 지난 익명 계정 삭제', s == 404, s)
        ev = mgmt_sql("select user_id::text from public.app_events where name = 'ob_test_left'")
        check('삭제된 익명 계정의 이벤트는 남고 누구 것인지만 바뀜 (B1)', ev and all(e['user_id'] != E for e in ev), ev)
        mgmt_sql("delete from public.app_events where name = 'ob_test_left'")
        s, u = req('GET', f'/auth/v1/admin/users/{B}', token=SERVICE, key=SERVICE); check('새 익명 계정은 안 지움', s == 200, s)
        jobs = mgmt_sql("select schedule from cron.job where jobname = 'purge-stale-anon'")
        check('매일 삭제 예약(pg_cron)', jobs and jobs[0]['schedule'] == '17 3 * * *', jobs)

        # ── 분류 IP 한도 (익명만). 함수가 보는 IP = 이 컴퓨터의 공인 IP
        ip = urllib.request.urlopen('https://api.ipify.org').read().decode().strip()
        h = hashlib.sha256((URL.rstrip('/') + ip).encode()).hexdigest()
        kday = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        mgmt_sql(f"insert into public.classify_ip_usage values ('{h}', '{kday}', 40) on conflict (ip_hash, day) do update set count = 40")
        consent(TB)
        s, r = req('POST', '/functions/v1/classify', {'text': '설거지 했다'}, token=TB); check('IP 한도 넘으면 익명 분류 429', s == 429, (s, r))
        s, r = req('POST', '/functions/v1/classify', {'text': '설거지 했다'}, token=TM); check('정식 계정은 IP 한도 안 받음', s == 200, (s, r))
        mgmt_sql(f"delete from public.classify_ip_usage where ip_hash = '{h}'")
    else:
        print('SKIP 7일 삭제·IP 한도 (Supabase 관리 토큰 없음)')
finally:
    for u in made:
        req('DELETE', f'/auth/v1/admin/users/{u}', token=SERVICE, key=SERVICE)
    left = [u for u in made if req('GET', f'/auth/v1/admin/users/{u}', token=SERVICE, key=SERVICE)[0] == 200]
    print(f'테스트 계정 {len(made)}개 정리, 남은 것 {len(left)}개')

print(f'\n{"ALL PASS" if not fails else f"{fails} FAIL"}')
sys.exit(1 if fails else 0)
