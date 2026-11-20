#!/usr/bin/env python3
"""실제 메일 발송 테스트 (Supabase Auth → Resend SMTP). Resend 테스트 주소(delivered+…@resend.dev)로 보내고
Resend API에서 받은 메일(제목·본문)을 읽어 6자리 코드로 로그인까지 확인. 3종: 가입(confirmation), 로그인(magic_link), 익명 연결(email_change).
사용: python3 scripts/test_email.py   (같은 주소 재발송 간격 60초 때문에 1분 30초쯤 걸림)
"""
import json, pathlib, re, sys, time, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE  # noqa: E402

env = dict(re.findall(r'^([A-Z0-9_]+)=(.*)$', (pathlib.Path(__file__).parent.parent / '.env.local').read_text(), re.M))
RK = env['RESEND_API_KEY'].strip().strip('"')
fails = 0
made = []
def check(name, cond, extra=''):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))
    if not cond: fails += 1

def resend(path):
    r = urllib.request.Request('https://api.resend.com' + path, headers={'Authorization': 'Bearer ' + RK, 'User-Agent': 'csw'})
    return json.loads(urllib.request.urlopen(r).read())

def wait_mail(to, since, tries=20):
    for _ in range(tries):
        time.sleep(3)
        for m in resend('/emails?limit=20').get('data', []):
            if to in m.get('to', []) and m['created_at'] >= since:
                return resend('/emails/' + m['id'])
    return None

def now_iso():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())

tag = str(int(time.time()))
A = f'delivered+hl{tag}a@resend.dev'
B = f'delivered+hl{tag}b@resend.dev'
try:
    # 1) 처음 보는 주소 = 가입 메일
    t0 = now_iso()
    s, r = req('POST', '/auth/v1/otp', {'email': A, 'create_user': True})
    check('가입 코드 요청', s == 200, (s, r))
    m = wait_mail(A, t0)
    check('가입 메일 도착 (Resend)', m is not None)
    if m:
        code = re.search(r'(\d{6})', m['subject']).group(1)
        check('보내는 사람 = Hamalog (기록하마) <no-reply@irumhq.com>', 'no-reply@irumhq.com' in m['from'] and 'Hamalog (기록하마)' in m['from'], m['from'])
        check('제목 = Hamalog 가입 코드 ######', m['subject'].startswith('Hamalog 가입 코드'), m['subject'])
        check('본문에 같은 코드 + 문의 주소', code in m['html'] and 'contact@irumhq.com' in m['html'] and '{{' not in m['html'])
        pathlib.Path('/Users/soniakang/.hermes/cache/scratch/mail_confirmation.html').write_text(m['html'])
        s, sess = req('POST', '/auth/v1/verify', {'type': 'email', 'email': A, 'token': code})
        check('가입 코드로 로그인', s == 200 and 'access_token' in sess, (s, sess))
        if s == 200: made.append(sess['user']['id'])

    # 2) 익명 계정에 이메일 연결 (가입 시트)
    s, an = req('POST', '/auth/v1/signup', {})
    TA, uid = an['access_token'], an['user']['id']; made.append(uid)
    t0 = now_iso()
    s, r = req('PUT', '/auth/v1/user', {'email': B}, token=TA)
    check('익명: 이메일 연결 요청', s == 200, (s, r))
    m = wait_mail(B, t0)
    check('연결 메일 도착', m is not None)
    if m:
        code = re.search(r'(\d{6})', m['subject']).group(1)
        check('제목 = Hamalog 이메일 연결 코드', m['subject'].startswith('Hamalog 이메일 연결 코드'), m['subject'])
        pathlib.Path('/Users/soniakang/.hermes/cache/scratch/mail_email_change.html').write_text(m['html'])
        s, sess = req('POST', '/auth/v1/verify', {'type': 'email_change', 'email': B, 'token': code}, token=TA)
        check('연결 코드 → 같은 계정이 정식 계정', s == 200 and sess.get('user', {}).get('id') == uid and not sess['user'].get('is_anonymous'), (s, sess))

    # 3) 이미 있는 주소 = 로그인 메일 (같은 주소 재발송 60초 제한)
    time.sleep(62)
    t0 = now_iso()
    s, r = req('POST', '/auth/v1/otp', {'email': A, 'create_user': True})
    check('로그인 코드 요청', s == 200, (s, r))
    m = wait_mail(A, t0)
    check('로그인 메일 도착', m is not None)
    if m:
        code = re.search(r'(\d{6})', m['subject']).group(1)
        check('제목 = Hamalog 로그인 코드', m['subject'].startswith('Hamalog 로그인 코드'), m['subject'])
        pathlib.Path('/Users/soniakang/.hermes/cache/scratch/mail_magic_link.html').write_text(m['html'])
        s, sess = req('POST', '/auth/v1/verify', {'type': 'email', 'email': A, 'token': code})
        check('로그인 코드로 로그인', s == 200 and 'access_token' in sess, (s, sess))
finally:
    for u in made:
        req('DELETE', f'/auth/v1/admin/users/{u}', token=SERVICE, key=SERVICE)
    print(f'테스트 계정 {len(made)}개 정리')

print(f'\n{"ALL PASS" if not fails else f"{fails} FAIL"}')
sys.exit(1 if fails else 0)
