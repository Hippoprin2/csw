#!/usr/bin/env python3
"""백엔드 스모크 테스트: 테스트 계정 생성 → OTP 로그인 → 기록/씨앗/구매/수정/삭제 규칙 → 분류 함수 → 계정 삭제.
사용: python3 scripts/test_backend.py   (루트 .env.local의 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, mobile/.env.local의 공개 키 필요)
"""
import json, sys, time
from sb import req, SERVICE

fails = 0
def check(name, cond, extra=''):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))
    if not cond: fails += 1

email = f'csw-test-{int(time.time())}@example.com'
s, link = req('POST', '/auth/v1/admin/generate_link', {'type': 'magiclink', 'email': email}, token=SERVICE, key=SERVICE)
if s != 200:  # 신규 사용자는 signup 링크
    s, _ = req('POST', '/auth/v1/admin/users', {'email': email, 'email_confirm': True}, token=SERVICE, key=SERVICE)
    s, link = req('POST', '/auth/v1/admin/generate_link', {'type': 'magiclink', 'email': email}, token=SERVICE, key=SERVICE)
otp = link.get('email_otp') or link.get('properties', {}).get('email_otp')
s, sess = req('POST', '/auth/v1/verify', {'type': 'email', 'email': email, 'token': otp})
check('OTP 로그인', s == 200 and 'access_token' in sess, f'{s} {sess}')
T = sess['access_token']; uid = sess['user']['id']

s, prof = req('GET', '/rest/v1/profiles?select=*', token=T)
check('가입 시 프로필 자동 생성', s == 200 and len(prof) == 1 and prof[0]['pet_name'] == '꼬마하마', prof)

s, b = req('POST', '/rest/v1/rpc/grant_onboarding_gift', {}, token=T); check('온보딩 선물 6', b == 6, b)
s, b = req('POST', '/rest/v1/rpc/grant_onboarding_gift', {}, token=T); check('선물은 1회만', b == 6, b)

s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '침대 정리했다', 'p_category': 'tidy'}, token=T)
check('첫 기록 +3, first=true', s == 200 and r['earned'] == 3 and r['first'] and r['balance'] == 9, r)
win_id = r['win']['id']

s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '어제 산책', 'p_category': 'move', 'p_win_date': time.strftime('%Y-%m-%d', time.localtime(time.time() - 86400))}, token=T)
check('어제 기록 가능', s == 200 and not r['first'], r)
s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '옛날 일', 'p_category': 'cheer', 'p_win_date': '2026-01-01'}, token=T)
check('그저께 이전 날짜 거부', s >= 400, r)

s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '보고서 마감', 'p_category': 'work'}, token=T); check('업무(work) 카테고리 저장', s == 200 and r['win']['category'] == 'work', r)
s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': 'x', 'p_category': 'nope'}, token=T); check('없는 카테고리 거부', s >= 400)
s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': ' ', 'p_category': 'cheer'}, token=T); check('빈 기록 거부', s >= 400)
s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '가' * 101, 'p_category': 'cheer'}, token=T); check('100자 초과 거부', s >= 400)

for i in range(9):  # 첫 기록·어제·업무 포함 하루 보상 10개 채우기
    s, r = req('POST', '/rest/v1/rpc/record_win', {'p_text': '물 마셨다', 'p_category': 'eat'}, token=T)
check('하루 10개 넘으면 씨앗 0, 기록은 저장', s == 200 and r['earned'] == 0 and r['balance'] == 6 + 30, r)

s, w = req('POST', '/rest/v1/wins', {'user_id': uid, 'text': 'x', 'category': 'cheer', 'win_date': '2026-11-08'}, token=T)
check('wins 직접 insert 차단', s >= 400, s)
s, w = req('POST', '/rest/v1/seed_ledger', {'user_id': uid, 'delta': 999, 'reason': 'win'}, token=T)
check('씨앗 직접 insert 차단', s >= 400, s)

s, r = req('POST', '/rest/v1/rpc/buy_item', {'p_item_id': 'plant'}, token=T); check('화분 구매(9)', r == 27, r)
s, r = req('POST', '/rest/v1/rpc/buy_item', {'p_item_id': 'plant'}, token=T); check('중복 구매 거부', s >= 400)
s, r = req('POST', '/rest/v1/rpc/buy_item', {'p_item_id': 'aquarium'}, token=T); check('씨앗 부족 거부(33>27)', s >= 400, r)

s, r = req('POST', '/rest/v1/rpc/edit_win', {'p_id': win_id, 'p_text': '이불 개켰다', 'p_category': 'tidy'}, token=T)
check('기록 수정', s == 200 and r['text'] == '이불 개켰다' and r['category_source'] == 'user', r)
s, _ = req('DELETE', f'/rest/v1/wins?id=eq.{win_id}', token=T)
s, b = req('POST', '/rest/v1/rpc/seed_balance', {}, token=T); check('기록 삭제해도 씨앗 유지', b == 27, b)

s, _ = req('POST', '/rest/v1/safety_events', {'user_id': uid, 'source': 'keyword'}, token=T); check('safety_event 기록', s in (200, 201), s)
s, _ = req('POST', '/rest/v1/app_events', {'user_id': uid, 'name': 'win_recorded', 'props': {'category': 'eat'}}, token=T); check('app_event 기록', s in (200, 201), s)

s, r = req('POST', '/functions/v1/classify', {'text': '설거지 다 했다'}, token=T)
check('분류 함수', s == 200 and r.get('category') == 'tidy', r)

s, _ = req('POST', '/rest/v1/rpc/delete_all_wins', {}, token=T)
s, w = req('GET', '/rest/v1/wins?select=id', token=T); check('모든 기록 지우기', w == [], w)
s, b = req('POST', '/rest/v1/rpc/seed_balance', {}, token=T); check('기록 지워도 씨앗·방 유지', b == 27, b)

s, _ = req('POST', '/rest/v1/rpc/delete_my_account', {}, token=T); check('계정 삭제 호출', s in (200, 204), _)
s, u = req('GET', f'/auth/v1/admin/users/{uid}', token=SERVICE, key=SERVICE); check('auth 사용자 삭제됨', s == 404, s)
s, rows = req('GET', f'/rest/v1/seed_ledger?user_id=eq.{uid}&select=id', token=SERVICE, key=SERVICE); check('연결 행 cascade 삭제', rows == [], rows)

print(f'\n{"ALL PASS" if not fails else f"{fails} FAIL"}')
sys.exit(1 if fails else 0)
