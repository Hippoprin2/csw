#!/usr/bin/env python3
"""Supabase Auth 메일 = Resend SMTP + 한국어 6자리 코드 메일 (2026-11-20, 대표 결정: no-reply@irumhq.com, 'Hamalog (기록하마)').

- Resend 열쇠는 Supabase 전용(.env.local RESEND_SMTP_KEY, irumhq.com 보내기만). 없으면 RESEND_API_KEY(전체 권한)로 새로 만들어 저장.
  Gmail '다른 주소로 보내기'가 쓰는 RESEND_API_KEY와 나눠서, 한쪽을 바꿔도 다른 쪽이 안 멈춤.
- 메일 3종: magic_link(이미 있는 주소 로그인), confirmation(처음 보는 주소 로그인 = 가입), email_change(익명 계정에 이메일 연결 — 가입 시트).
- 보내는 사람 이름은 프로젝트 하나에 하나뿐 → 지금은 한국 이름. 일본·대만 출시 때는 Send Email Hook(Edge Function → Resend API)으로
  사용자 지역별 이름·문구를 고르기 (DEV.md '이메일').
사용: python3 scripts/apply_email.py
"""
import base64, json, pathlib, re, subprocess, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENVF = ROOT / '.env.local'
REF = 'xbifxrvgdimwwijijthl'
SENDER = 'no-reply@irumhq.com'
SENDER_NAME = 'Hamalog (기록하마)'
CONTACT = 'contact@irumhq.com'
DOMAIN = 'irumhq.com'

env = dict(re.findall(r'^([A-Z0-9_]+)=(.*)$', ENVF.read_text(), re.M))
env = {k: v.strip().strip('"') for k, v in env.items()}

def http(method, url, body=None, headers=None):
    r = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                               headers={'Content-Type': 'application/json', 'User-Agent': 'csw', **(headers or {})})
    try:
        with urllib.request.urlopen(r) as f:
            return f.status, json.loads(f.read() or b'null')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]

# 1) Supabase 전용 Resend 열쇠
key = env.get('RESEND_SMTP_KEY')
if not key:
    rh = {'Authorization': 'Bearer ' + env['RESEND_API_KEY']}
    s, doms = http('GET', 'https://api.resend.com/domains', headers=rh)
    dom = next(d for d in doms['data'] if d['name'] == DOMAIN)
    s, k = http('POST', 'https://api.resend.com/api-keys',
                {'name': 'supabase-auth-hamalog', 'permission': 'sending_access', 'domain_id': dom['id']}, rh)
    assert s in (200, 201), (s, k)
    key = k['token']
    with ENVF.open('a') as f:
        f.write(f'\n# Supabase Auth SMTP 전용 (보내기만, {DOMAIN}) — scripts/apply_email.py\nRESEND_SMTP_KEY={key}\n')
    print('Resend 열쇠 새로 만듦: supabase-auth-hamalog (보내기 전용)')

# 2) 메일 본문
def tpl(title, lead, link_text):
    return f'''<div style="font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;max-width:440px;margin:0 auto;padding:28px 24px;color:#3b3247">
<p style="font-size:15px;font-weight:700;margin:0 0 20px">Hamalog</p>
<h2 style="font-size:20px;margin:0 0 12px">{title}</h2>
<p style="font-size:15px;line-height:1.6;margin:0 0 20px">{lead}</p>
<p style="font-size:34px;letter-spacing:10px;font-weight:700;color:#ff8a5c;margin:0 0 20px">{{{{ .Token }}}}</p>
<p style="font-size:14px;line-height:1.6;color:#6b6475;margin:0 0 24px">10분 동안만 쓸 수 있어. 휴대폰에서 이 메일을 열었다면 <a href="{{{{ .ConfirmationURL }}}}" style="color:#ff8a5c">{link_text}</a>를 눌러도 돼.</p>
<p style="font-size:12px;line-height:1.6;color:#9a94a3;margin:0;border-top:1px solid #eee;padding-top:16px">요청한 적이 없다면 이 메일은 무시해도 괜찮아.<br>이 메일은 보내기 전용이라 답장을 받을 수 없어. 궁금한 점은 <a href="mailto:{CONTACT}" style="color:#9a94a3">{CONTACT}</a>로 보내줘.</p>
</div>'''

body = {
    'smtp_host': 'smtp.resend.com', 'smtp_port': '465', 'smtp_user': 'resend', 'smtp_pass': key,
    'smtp_admin_email': SENDER, 'smtp_sender_name': SENDER_NAME, 'smtp_max_frequency': 60,
    'rate_limit_email_sent': 30,  # 프로젝트 전체 시간당 (기본 메일은 2)
    'mailer_subjects_magic_link': 'Hamalog 로그인 코드 {{ .Token }}',
    'mailer_templates_magic_link_content': tpl('로그인 코드', '앱에 아래 6자리 코드를 입력해줘.', '로그인 링크'),
    'mailer_subjects_confirmation': 'Hamalog 가입 코드 {{ .Token }}',
    'mailer_templates_confirmation_content': tpl('가입 코드', 'Hamalog에 온 걸 환영해! 앱에 아래 6자리 코드를 입력하면 가입이 끝나.', '가입 링크'),
    # email_change = 가입 시트에서 이메일 고름(익명 계정에 주소 연결) — 사용자에겐 '가입'
    'mailer_subjects_email_change': 'Hamalog 가입 코드 {{ .Token }}',
    'mailer_templates_email_change_content': tpl('가입 코드', 'Hamalog에 온 걸 환영해! 앱에 아래 6자리 코드를 입력하면 가입이 끝나.', '가입 링크'),
}

raw = subprocess.run(['security', 'find-generic-password', '-s', 'Supabase CLI', '-w'], capture_output=True, text=True).stdout.strip()
if raw.startswith('go-keyring-base64:'):
    raw = base64.b64decode(raw.split(':', 1)[1]).decode()
s, c = http('PATCH', f'https://api.supabase.com/v1/projects/{REF}/config/auth', body, {'Authorization': 'Bearer ' + raw})
print('Supabase Auth 메일 설정', s, 'ok' if s == 200 else c)
