#!/usr/bin/env python3
"""방 자리(slot) + 텃밭 규칙 테스트 (실서버). 날짜는 service role로 seed_ledger·plots를 과거로 옮겨 흉내낸다.
사용: python3 scripts/test_garden.py
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
def add_record_day(uid, day):  # 그날 기록한 것처럼 씨앗 행 추가 (정오 KST)
    ts = dt.datetime.combine(day, dt.time(12), KST).isoformat()
    svc('POST', '/rest/v1/seed_ledger', {'user_id': uid, 'delta': 3, 'reason': 'win', 'created_at': ts})
def set_planted(uid, slot, day):
    svc('PATCH', f'/rest/v1/plots?user_id=eq.{uid}&slot=eq.{slot}', {'planted_day': day.isoformat()})
def garden(T):
    return {p['slot']: p for p in req('POST', '/rest/v1/rpc/garden_state', {}, token=T)[1]}

T, uid = temp_user()
try:
    req('POST', '/rest/v1/rpc/grant_onboarding_gift', {}, token=T)
    s, items = req('GET', '/rest/v1/items?select=id,price,slot&space=eq.room&order=sort', token=T)
    check('방 소품 18개 · 합계 264', len(items) == 18 and sum(i['price'] for i in items) == 264, (len(items), sum(i['price'] for i in items)))

    # ── 방: 같은 자리 바꿔 끼우기 ──
    for _ in range(10): add_record_day(uid, today - dt.timedelta(days=30))  # 씨앗 30 추가 → 36
    req('POST', '/rest/v1/rpc/buy_item', {'p_item_id': 'cushion'}, token=T)
    req('POST', '/rest/v1/rpc/buy_item', {'p_item_id': 'squirrel'}, token=T)   # 같은 자리(front_center)
    s, own = req('GET', '/rest/v1/owned_items?select=item_id,placed', token=T)
    placed = {o['item_id']: o['placed'] for o in own}
    check('새로 산 소품이 그 자리에 놓임', placed == {'cushion': False, 'squirrel': True}, placed)
    s, _ = req('POST', '/rest/v1/rpc/place_item', {'p_item_id': 'cushion'}, token=T)
    s, own = req('GET', '/rest/v1/owned_items?select=item_id,placed', token=T)
    placed = {o['item_id']: o['placed'] for o in own}
    check('바꿔 끼우기', placed == {'cushion': True, 'squirrel': False}, placed)
    s, r = req('POST', '/rest/v1/rpc/place_item', {'p_item_id': 'bed'}, token=T); check('안 가진 소품은 못 놓음', s >= 400)

    # ── 텃밭: 첫 작물 ──
    s, r = req('POST', '/rest/v1/rpc/plant', {'p_slot': 1, 'p_crop': 'tulip'}, token=T); check('첫 작물은 고구마만', s >= 400, r)
    s, bal0 = req('POST', '/rest/v1/rpc/seed_balance', {}, token=T)
    s, r = req('POST', '/rest/v1/rpc/plant', {'p_slot': 1, 'p_crop': 'sweet_potato'}, token=T)
    check('첫 고구마 무료', s == 200 and r == bal0, (s, r, bal0))
    g = garden(T)
    check('심은 날은 0일, 필요 1일', g[1]['days'] == 0 and g[1]['required_days'] == 1, g)
    add_record_day(uid, today)  # 심은 당일 기록은 세지 않음
    check('심은 당일 기록은 안 셈', garden(T)[1]['days'] == 0)
    s, r = req('POST', '/rest/v1/rpc/harvest', {'p_slot': 1}, token=T); check('덜 자라면 수확 불가', s >= 400)
    set_planted(uid, 1, today - dt.timedelta(days=1))  # 어제 심음 → 오늘 기록 1일
    check('다음 날 기록하면 1일', garden(T)[1]['days'] == 1)
    s, r = req('POST', '/rest/v1/rpc/harvest', {'p_slot': 1}, token=T)
    check('첫 수확 + 장식 생김', s == 200 and r == {'crop_id': 'sweet_potato', 'first_unlock': True}, r)
    s, bag = req('GET', '/rest/v1/harvest_bag?select=crop_id,count', token=T); check('바구니 고구마 1', bag == [{'crop_id': 'sweet_potato', 'count': 1}], bag)

    # ── 두 번째부터: 3씨앗, 기록한 날 9일 ──
    s, bal1 = req('POST', '/rest/v1/rpc/seed_balance', {}, token=T)
    s, r = req('POST', '/rest/v1/rpc/plant', {'p_slot': 2, 'p_crop': 'tulip'}, token=T)
    check('튤립 심기 3씨앗', s == 200 and r == bal1 - 3, (s, r, bal1))
    s, r = req('POST', '/rest/v1/rpc/plant', {'p_slot': 2, 'p_crop': 'sunflower'}, token=T); check('찬 칸에는 못 심음', s >= 400)
    start = today - dt.timedelta(days=20)
    set_planted(uid, 2, start)
    days = [start + dt.timedelta(days=d) for d in (1, 2, 5, 9, 10, 11, 14, 17)]  # 띄엄띄엄 8일 (+오늘 = 9일)
    for d in days[:3]: add_record_day(uid, d)
    check('기록한 날 3일(+오늘) = 싹 단계', garden(T)[2]['days'] == 4, garden(T)[2])
    for d in days[3:]: add_record_day(uid, d)
    add_record_day(uid, days[0])  # 같은 날 여러 번 기록해도 1일
    g = garden(T)[2]
    check('같은 날 여러 기록은 1일로 셈 (8일 + 오늘 = 9)', g['days'] == 9, g)
    # 기록을 모두 지워도 성장은 줄지 않음
    req('POST', '/rest/v1/rpc/delete_all_wins', {}, token=T)
    check('기록 지워도 성장 유지', garden(T)[2]['days'] == 9)
    s, r = req('POST', '/rest/v1/rpc/harvest', {'p_slot': 2}, token=T); check('9일이면 수확', s == 200 and r['first_unlock'] is True, r)

    # ── 먹이기/선물하기 ──
    s, n = req('POST', '/rest/v1/rpc/use_harvest', {'p_crop': 'sweet_potato'}, token=T); check('먹이기 → 바구니 0', n == 0, n)
    s, r = req('POST', '/rest/v1/rpc/use_harvest', {'p_crop': 'sweet_potato'}, token=T); check('빈 바구니는 거부', s >= 400)
    s, un = req('GET', '/rest/v1/harvest_unlocks?select=crop_id', token=T)
    check('먹어도 장식은 그대로', {u['crop_id'] for u in un} == {'sweet_potato', 'tulip'}, un)

    # ── 직접 조작 차단 ──
    s, _ = req('POST', '/rest/v1/plots', {'user_id': uid, 'slot': 3, 'crop_id': 'tulip', 'planted_day': '2020-01-01', 'required_days': 0}, token=T)
    check('plots 직접 insert 차단', s >= 400, s)
    s, _ = req('POST', '/rest/v1/harvest_bag', {'user_id': uid, 'crop_id': 'tulip', 'count': 99}, token=T)
    check('바구니 직접 insert 차단', s >= 400, s)
    s, _ = req('PATCH', f'/rest/v1/profiles?id=eq.{uid}', {'first_crop_used': False}, token=T)
    s, p = req('GET', '/rest/v1/profiles?select=first_crop_used', token=T)
    check('첫 작물 무료 재사용 차단', p[0]['first_crop_used'] is True, p)

    # ── 접속 기록 ──
    s, prev = req('POST', '/rest/v1/rpc/touch_seen', {}, token=T); check('첫 접속은 이전 기록 없음', prev is None, prev)
    s, prev = req('POST', '/rest/v1/rpc/touch_seen', {}, token=T); check('두 번째는 이전 시각', isinstance(prev, str), prev)
finally:
    delete_user(uid)

print('\nALL PASS' if not fails else f'\n{fails} FAIL')
sys.exit(1 if fails else 0)
