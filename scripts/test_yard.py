#!/usr/bin/env python3
"""마당 서버 규칙 테스트 (실서버, WORLD 7장). 기록한 날은 service role로 seed_ledger 'win' 행을 과거 날짜로 넣어 흉내낸다.
사용: python3 scripts/test_yard.py
"""
import datetime as dt, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE, temp_user, delete_user  # noqa: E402

fails = 0
def check(name, cond, extra=''):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))
    if not cond: fails += 1

KST = dt.timezone(dt.timedelta(hours=9))
today = dt.datetime.now(KST).date()
def svc(method, path, body=None):
    return req(method, path, body, token=SERVICE, key=SERVICE)
def add_record_day(uid, day, n=1):
    ts = dt.datetime.combine(day, dt.time(12), KST).isoformat()
    for _ in range(n): svc('POST', '/rest/v1/seed_ledger', {'user_id': uid, 'delta': 3, 'reason': 'win', 'created_at': ts})
def rpc(T, name, body=None):
    return req('POST', f'/rest/v1/rpc/{name}', body or {}, token=T)
def err(r):
    return r[1].get('message') if isinstance(r[1], dict) else r[1]

T, uid = temp_user()
T2, uid2 = temp_user()
try:
    rpc(T, 'grant_onboarding_gift')
    s, items = req('GET', '/rest/v1/items?select=id,price&space=eq.yard', token=T)
    check('마당 소품 10개 · 합계 162', len(items) == 10 and sum(i['price'] for i in items) == 162, (len(items), sum(i['price'] for i in items)))

    # ── 열림: 기록한 날 누적 7일 (연속 아님, 하루 여러 개는 1일) ──
    st = rpc(T, 'yard_state')[1]
    check('처음엔 닫힘', st['open'] is False and st['record_days'] == 0 and st['zones'] == [] and st['tester'] is False, st)
    check('닫힌 마당 소품은 못 삼', err(rpc(T, 'buy_item', {'p_item_id': 'bench'})) == 'yard_locked')
    check('닫힌 마당 구역은 못 삼', err(rpc(T, 'buy_zone', {'p_zone': 2})) == 'yard_locked')
    for k in range(6): add_record_day(uid, today - dt.timedelta(days=40 + k * 3), n=5)  # 띄엄띄엄 6일, 하루 5개
    st = rpc(T, 'yard_state')[1]
    check('6일(기록 30개)은 아직 닫힘', st['open'] is False and st['record_days'] == 6, st)
    add_record_day(uid, today - dt.timedelta(days=10))
    st = rpc(T, 'yard_state')[1]
    check('7일째 열림', st['open'] is True and st['record_days'] == 7, st)
    svc('DELETE', f'/rest/v1/seed_ledger?user_id=eq.{uid}&reason=eq.win')
    check('한 번 열리면 영구', rpc(T, 'yard_state')[1]['open'] is True)

    # ── 구역: 60·120, 영구, 잔액 부족 ──
    bal = rpc(T, 'seed_balance')[1]
    add_record_day(uid, today - dt.timedelta(days=60), n=60)  # +180
    bal = rpc(T, 'seed_balance')[1]
    r = rpc(T, 'buy_zone', {'p_zone': 2})
    check('2구역 60씨앗', r[0] == 200 and r[1] == bal - 60, r)
    check('같은 구역 두 번은 안 됨', err(rpc(T, 'buy_zone', {'p_zone': 2})) == 'already_owned')
    check('없는 구역(1·4)은 못 삼', err(rpc(T, 'buy_zone', {'p_zone': 4})) == 'not_found' and err(rpc(T, 'buy_zone', {'p_zone': 1})) == 'not_found')
    r = rpc(T, 'buy_zone', {'p_zone': 3})
    check('3구역 120씨앗', r[0] == 200 and r[1] == bal - 180, r)
    check('산 구역이 상태에 나옴', rpc(T, 'yard_state')[1]['zones'] == [2, 3])
    s, z = req('POST', '/rest/v1/yard_zones', {'user_id': uid, 'zone': 2}, token=T2)
    check('구역 표에 직접 넣기 막힘', s >= 400, s)

    # ── 마당 소품 ──
    add_record_day(uid, today - dt.timedelta(days=61), n=10)
    r = rpc(T, 'buy_item', {'p_item_id': 'bench'})
    check('열린 마당 소품 구매', r[0] == 200, r)
    r = rpc(T, 'buy_item', {'p_item_id': 'picnic_mat'})
    s, own = req('GET', '/rest/v1/owned_items?select=item_id,placed', token=T)
    placed = {o['item_id']: o['placed'] for o in own}
    check('마당 소품은 각자 자리 (바꿔 끼우기 없음)', placed.get('bench') is True and placed.get('picnic_mat') is True, placed)

    # ── 추억 열매 ──
    def win(day, text, cat):
        r = svc('POST', '/rest/v1/wins', {'user_id': uid, 'text': text, 'category': cat, 'win_date': day.isoformat(), 'jar_no': 1})
        assert r[0] < 300, r
        return r
    win(today - dt.timedelta(days=2), '어제 산책', 'move')
    check('7일 안 된 기록만 있으면 null', rpc(T, 'memory_card')[1] is None)
    win(today - dt.timedelta(days=20), '버틴 날', 'endure')
    check('버틴 하루는 안 나옴', rpc(T, 'memory_card')[1] is None)
    s, w = win(today - dt.timedelta(days=20), '책 한 장 읽음', 'study')
    c = rpc(T, 'memory_card')[1]
    check('7일 지난 기록 → past', c and c['text'] == '책 한 장 읽음' and c['kind'] == 'past', c)
    check('본 기록은 빼고 고름', rpc(T, 'memory_card', {'p_seen': [c['id']]})[1] is None)
    mon = (dt.date(today.year if today.month > 1 else today.year - 1, today.month - 1 if today.month > 1 else 12, min(today.day, 28)))
    if today.day <= 28:
        win(mon, '한 달 전 운동', 'move')
        c = rpc(T, 'memory_card')[1]
        check('한 달 전 오늘 기록이 먼저 (month)', c and c['kind'] == 'month' and c['text'] == '한 달 전 운동', c)
    check('다른 계정 기록은 안 나옴', rpc(T2, 'memory_card')[1] is None)

    # ── 테스트 스위치: 테스터만 ──
    check('테스터 아니면 마당 열기 막힘', err(rpc(T2, 'dev_yard', {'p_open': True})) == 'forbidden')
    check('테스터 아니면 구역 열기 막힘', err(rpc(T2, 'dev_all_zones')) == 'forbidden')
    check('테스터 아니면 씨앗 막힘', err(rpc(T2, 'dev_seeds')) == 'forbidden')
    s, _ = req('POST', '/rest/v1/testers', {'user_id': uid2}, token=T2)
    check('테스터 표에 스스로 넣기 막힘', s >= 400, s)
    svc('POST', '/rest/v1/testers', {'user_id': uid2})
    check('테스터 표시', rpc(T2, 'yard_state')[1]['tester'] is True)
    rpc(T2, 'dev_yard', {'p_open': True})
    check('테스터: 마당 바로 열기', rpc(T2, 'yard_state')[1]['open'] is True)
    rpc(T2, 'dev_yard', {'p_open': False})
    check('테스터: 바로 열기 끄면 닫힘 (영구 열림 안 남김)', rpc(T2, 'yard_state')[1]['open'] is False)
    rpc(T2, 'dev_all_zones')
    check('테스터: 구역 모두 열기', rpc(T2, 'yard_state')[1]['zones'] == [2, 3])
    r = rpc(T2, 'dev_seeds')
    check('테스터: 씨앗 +500', r[0] == 200 and r[1] >= 500, r)
finally:
    delete_user(uid); delete_user(uid2)
    s, left = svc('GET', f'/rest/v1/profiles?select=id&id=in.({uid},{uid2})')
    print('cleaned', left == [])
print('FAILS', fails)
sys.exit(1 if fails else 0)
