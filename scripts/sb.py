"""Supabase 테스트 공용 헬퍼 (service role은 테스트 스크립트에서만)."""
import json, re, sys, time, urllib.request, urllib.error, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
def env(path, key):
    m = re.search(rf'^\s*{key}\s*=\s*(\S+)', (ROOT / path).read_text(), re.M)
    return m.group(1)
URL = env('.env.local', 'SUPABASE_URL')
SERVICE = env('.env.local', 'SUPABASE_SERVICE_ROLE_KEY')
PUB = env('mobile/.env.local', 'EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY')

def req(method, path, body=None, token=None, key=PUB):
    h = {'apikey': key, 'Content-Type': 'application/json', 'Authorization': f'Bearer {token or key}'}
    r = urllib.request.Request(URL + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=20) as res:
            raw = res.read(); return res.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(); 
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw


def temp_user():
    """테스트 계정 생성 + OTP 로그인 → (access_token, user_id)"""
    import time as _t
    email = f'csw-test-{int(_t.time()*1000)}@example.com'
    req('POST', '/auth/v1/admin/users', {'email': email, 'email_confirm': True}, token=SERVICE, key=SERVICE)
    _, link = req('POST', '/auth/v1/admin/generate_link', {'type': 'magiclink', 'email': email}, token=SERVICE, key=SERVICE)
    otp = link.get('email_otp') or link.get('properties', {}).get('email_otp')
    _, sess = req('POST', '/auth/v1/verify', {'type': 'email', 'email': email, 'token': otp})
    return sess['access_token'], sess['user']['id']

def delete_user(uid):
    req('DELETE', f'/auth/v1/admin/users/{uid}', token=SERVICE, key=SERVICE)
