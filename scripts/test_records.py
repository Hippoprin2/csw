#!/usr/bin/env python3
"""기록 다시 보기 C9 서버 규칙 테스트 (실서버): 메모(N2)·☆(M3)·분류 수.
사용: python3 scripts/test_records.py
"""
import datetime as dt, pathlib, sys, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, temp_user, delete_user  # noqa: E402

fails = 0
def check(name, cond, extra=''):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))
    if not cond: fails += 1

KST = dt.timezone(dt.timedelta(hours=9))
today = dt.datetime.now(KST).date().isoformat()
def rpc(T, name, body=None):
    return req('POST', f'/rest/v1/rpc/{name}', body or {}, token=T)
def err(r):
    return r[1].get('message') if isinstance(r[1], dict) else r[1]

T, uid = temp_user()
T2, uid2 = temp_user()
try:
    a = rpc(T, 'record_win', {'p_text': '10분 산책', 'p_category': 'move', 'p_source': 'user', 'p_win_date': today})[1]['win']
    b = rpc(T, 'record_win', {'p_text': '침대 정리', 'p_category': 'tidy', 'p_source': 'user', 'p_win_date': today})[1]
    bal = b['balance']; b = b['win']
    check('새 기록: 메모 없음 · ☆ 꺼짐', a['note'] is None and a['starred'] is False, a)

    s, w = rpc(T, 'set_win_note', {'p_id': a['id'], 'p_note': '  바람이 시원했다 '})
    check('메모 저장 (앞뒤 공백 정리)', s == 200 and w['note'] == '바람이 시원했다' and w['text'] == '10분 산책', w)
    check('메모해도 씨앗 그대로', rpc(T, 'seed_balance')[1] == bal)
    check('메모 200자 넘으면 거절', err(rpc(T, 'set_win_note', {'p_id': a['id'], 'p_note': '가' * 201})) == 'too_long')
    s, w = rpc(T, 'set_win_note', {'p_id': a['id'], 'p_note': '   '})
    check('빈 메모 = 지움', s == 200 and w['note'] is None, w)
    rpc(T, 'set_win_note', {'p_id': a['id'], 'p_note': '바람이 시원했다'})

    s, w = rpc(T, 'set_win_star', {'p_id': b['id'], 'p_on': True})
    check('☆ 켜기', s == 200 and w['starred'] is True, w)
    check('☆해도 씨앗 그대로', rpc(T, 'seed_balance')[1] == bal)
    c = rpc(T, 'win_counts')[1]
    check('분류 수 · ☆ 수', c['cats'] == {'move': 1, 'tidy': 1} and c['starred'] == 1, c)
    s, rows = req('GET', '/rest/v1/wins?select=id&starred=is.true', token=T)
    check('☆ 목록 조회', [r['id'] for r in rows] == [b['id']], rows)
    s, rows = req('GET', '/rest/v1/wins?select=id&or=' + urllib.parse.quote('(text.ilike.*시원*,note.ilike.*시원*)'), token=T)
    check('찾기: 메모 글자로도 찾힘', [r['id'] for r in rows] == [a['id']], rows)

    # ── 남의 기록·직접 쓰기 차단 ──
    check('남의 기록 메모 불가', err(rpc(T2, 'set_win_note', {'p_id': a['id'], 'p_note': 'x'})) == 'not_found')
    check('남의 기록 ☆ 불가', err(rpc(T2, 'set_win_star', {'p_id': a['id'], 'p_on': False})) == 'not_found')
    check('남의 분류 수는 0', rpc(T2, 'win_counts')[1] == {'cats': {}, 'starred': 0})
    s, _ = req('PATCH', f'/rest/v1/wins?id=eq.{a["id"]}', {'starred': False, 'note': 'hack'}, token=T)
    s2, rows = req('GET', f'/rest/v1/wins?select=note,starred&id=eq.{a["id"]}', token=T)
    check('직접 PATCH 불가 (함수로만)', s in (401, 403) and rows[0]['note'] == '바람이 시원했다', (s, rows))
    check('익명은 함수 못 부름', req('POST', '/rest/v1/rpc/win_counts', {})[0] in (401, 403, 404))
finally:
    delete_user(uid); delete_user(uid2)

print('\nALL PASS' if not fails else f'\n{fails} FAIL')
sys.exit(1 if fails else 0)
