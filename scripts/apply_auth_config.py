#!/usr/bin/env python3
"""루트 .env.local의 로그인 키를 Supabase Auth 설정에 반영 (Management API, 토큰은 Supabase CLI 키체인).
있는 키만 반영: KAKAO_CLIENT_ID/SECRET, GOOGLE_CLIENT_ID/SECRET, RESEND_API_KEY(+선택 SMTP_SENDER).
사용: python3 scripts/apply_auth_config.py
"""
import base64, json, pathlib, re, subprocess, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
REF = 'xbifxrvgdimwwijijthl'
env = dict(re.findall(r'^\s*([A-Z_]+)\s*=\s*(\S+)', (ROOT / '.env.local').read_text(), re.M))

raw = subprocess.run(['security', 'find-generic-password', '-s', 'Supabase CLI', '-w'], capture_output=True, text=True).stdout.strip()
if raw.startswith('go-keyring-base64:'):
    raw = base64.b64decode(raw.split(':', 1)[1]).decode()

def patch(body):
    req = urllib.request.Request(f'https://api.supabase.com/v1/projects/{REF}/config/auth', method='PATCH',
                                 data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + raw, 'Content-Type': 'application/json', 'User-Agent': 'csw-agent'})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

body = {}
if env.get('KAKAO_CLIENT_ID') and env.get('KAKAO_CLIENT_SECRET'):
    body.update(external_kakao_enabled=True, external_kakao_client_id=env['KAKAO_CLIENT_ID'],
                external_kakao_secret=env['KAKAO_CLIENT_SECRET'], external_kakao_email_optional=True)
if env.get('GOOGLE_CLIENT_ID') and env.get('GOOGLE_CLIENT_SECRET'):
    body.update(external_google_enabled=True, external_google_client_id=env['GOOGLE_CLIENT_ID'],
                external_google_secret=env['GOOGLE_CLIENT_SECRET'])
if env.get('RESEND_API_KEY'):
    body.update(smtp_host='smtp.resend.com', smtp_port='465', smtp_user='resend', smtp_pass=env['RESEND_API_KEY'],
                smtp_admin_email=env.get('SMTP_SENDER', 'onboarding@resend.dev'), smtp_sender_name='CSW',
                rate_limit_email_sent=60)

if not body:
    print('반영할 키가 없음'); raise SystemExit(0)
s, c = patch(body)
print('설정', s, 'ok' if s == 200 else c, '| 반영:', sorted({k.split('_')[1] if k.startswith('external') else 'smtp' for k in body}))

# SMTP가 있으면 메일 본문을 6자리 코드로 교체 (무료 기본 메일에서는 불가했던 부분)
if env.get('RESEND_API_KEY') and s == 200:
    tpl = lambda title: (f'<div style="font-family:sans-serif;max-width:420px;margin:auto;padding:24px"><h2 style="color:#3b3247">{title}</h2>'
                         '<p>앱에 아래 6자리 코드를 입력해줘.</p><p style="font-size:32px;letter-spacing:8px;font-weight:bold;color:#ff8a5c">{{ .Token }}</p>'
                         '<p style="color:#999;font-size:12px">10분 동안만 쓸 수 있어. 요청한 적 없다면 이 메일은 무시해도 괜찮아.</p></div>')
    s2, c2 = patch({'mailer_subjects_magic_link': '[CSW] 로그인 코드', 'mailer_templates_magic_link_content': tpl('로그인 코드'),
                    'mailer_subjects_confirmation': '[CSW] 가입 확인 코드', 'mailer_templates_confirmation_content': tpl('가입 확인 코드')})
    print('메일 템플릿', s2, 'ok' if s2 == 200 else c2)
