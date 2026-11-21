# 유리병 탭 정리 시안 (의견 단계 — 앱 코드 그대로). python3 gen.py → sheet1.html, sheet2.html
# 예시 날짜: 오늘 = 2026-11-19(목). 기록 문구는 지어낸 예시.
import os
HERE = os.path.dirname(os.path.abspath(__file__))
A = '../../mobile/assets/world/jar/'
CAT = {  # lib/categories.ts
    'tidy': ('정리·청소', '#9ccfd8'), 'move': ('몸 움직이기', '#f6b26b'), 'study': ('공부', '#a4c2f4'),
    'work': ('업무', '#b4a7d6'), 'eat': ('잘 먹기', '#f9cb9c'), 'care': ('나 돌보기', '#d5a6bd'),
    'people': ('사람·마음', '#ea9999'), 'cheer': ('그 밖의 승리', '#b6d7a8'), 'endure': ('버틴 하루', '#c3c8d6'),
}
DAYS = {  # 날짜 → [(분류, 문구, ☆)]
    '오늘': [('eat', '물 한 잔 마심', 0), ('tidy', '책상 위 컵 치움', 0), ('move', '10분 산책', 1)],
    '어제': [('work', '메일 3개 답장', 0), ('eat', '아침 챙겨 먹음', 0), ('care', '일찍 씻고 누움', 0)],
    '11월 17일 (화)': [('study', '단어 20개', 0), ('people', '엄마한테 전화', 1),
                      ('tidy', '빨래 개기', 0), ('eat', '물 한 잔 마심', 0), ('move', '스트레칭', 0),
                      ('work', '회의 자료 정리', 0), ('care', '영양제 먹기', 0), ('cheer', '버스 안 놓침', 0)],
    '11월 16일 (월)': [('endure', '오늘 좀 힘들었어', 0)],
    '11월 15일 (일)': [('tidy', '방 청소', 0), ('eat', '집밥 해 먹음', 0)],
    '11월 13일 (금)': [('work', '보고서 제출', 1), ('move', '계단으로 올라감', 0)],
    '11월 11일 (수)': [('care', '산책하며 하늘 봄', 0), ('study', '책 10쪽', 0), ('eat', '과일 먹기', 0)],
    '11월 9일 (월)': [('people', '친구 생일 축하', 0)],
}
THIS = ['오늘', '어제', '11월 17일 (화)', '11월 16일 (월)']
LAST = ['11월 15일 (일)', '11월 13일 (금)', '11월 11일 (수)', '11월 9일 (월)']
JAR = [c for d in reversed(THIS + LAST) for c, _, _ in DAYS[d]] + ['tidy', 'eat', 'move', 'care', 'study']
JAR = JAR[:19]

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#E9E6E0;font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;color:#4A3226;padding:24px 15px;display:flex;gap:28px;align-items:flex-start}
.col{width:390px;flex:none}
.cap{display:inline-block;background:#4A3226;color:#fff;font-size:15px;font-weight:700;border-radius:999px;padding:7px 16px;margin-bottom:6px}
.cap.rec{background:#2F7D6B}
.sub{font-size:13px;color:#6E5848;margin:0 4px 10px;line-height:1.45;min-height:38px}
.phone{position:relative;width:390px;background:#fff;border-radius:44px;overflow:hidden;padding:58px 20px 40px;box-shadow:0 4px 18px rgba(0,0,0,.08)}
.phone.fix{height:844px}
.fold{position:absolute;left:0;right:0;top:844px;border-top:2px dashed #2F7D6B;z-index:9}
.fold span{position:absolute;right:12px;top:-24px;background:#2F7D6B;color:#fff;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px}
h1{font-size:24px;font-weight:800}
.head{display:flex;justify-content:space-between;align-items:center}
.search{background:#F2F0EB;border-radius:999px;font-size:13px;font-weight:600;padding:8px 14px}
.lead{font-size:14px;color:#6E5848;margin:6px 0 4px}
.jar{position:relative;width:290px;height:363px;margin:4px auto 0}
.jar img.l{position:absolute;inset:0;width:100%;height:100%}
.jar img.m{position:absolute;width:31px;height:31px}
.link{text-align:center;font-size:13px;color:#1F5F50;font-weight:700;margin:2px 0 16px}
.t{font-size:13px;color:#6E5848;font-weight:700;margin:0 4px 8px}
.card{background:#F7F6F3;border-radius:22px;padding:18px;margin-bottom:14px}
.big{font-size:19px;font-weight:800;margin-bottom:12px}
.mrow{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px}.mrow i{width:14px;height:14px;border-radius:7px}
.pills{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.pill{display:flex;align-items:center;gap:5px;background:#F2F0EB;border-radius:999px;height:28px;padding:0 11px;font-size:12px}
.dot{width:8px;height:8px;border-radius:9px;flex:none}
.mem{background:#F2F0EB;border-radius:22px;padding:16px}
.mem.top{background:#F7F6F3;margin-bottom:22px}
.mem b{display:block;font-size:12px;color:#6E5848;font-weight:400;margin-bottom:4px}.mem span{font-size:14px;font-weight:600}
.alink{font-size:14px;color:#1F5F50;font-weight:700;margin:0 4px 14px}
.chips{display:flex;gap:8px;overflow:hidden;margin-bottom:16px}
.chip{flex:none;display:flex;align-items:center;gap:6px;height:36px;padding:0 14px;border-radius:999px;background:#F2F0EB;font-size:13px;font-weight:600}
.shelf{display:flex;gap:12px;padding:0 6px;align-items:flex-end}
.sj{width:64px;text-align:center}.sj .lid{width:40px;height:9px;border-radius:3px;background:#c9a27a;margin:0 auto -1px}
.sj .b{width:54px;height:62px;margin:0 auto;border:3px solid #d9c9b1;border-radius:10px 10px 16px 16px;background:#fffaf2;display:flex;flex-wrap:wrap-reverse;align-content:flex-start;gap:1px;padding:3px;overflow:hidden}
.sj .b i{width:6px;height:6px;border-radius:3px}.sj p{font-size:11px;color:#6E5848;margin:4px 0 6px}
.board{height:8px;border-radius:4px;background:#d9c9b1;margin:-2px 0 18px}
.dayh{font-size:13px;color:#6E5848;font-weight:700;margin:0 4px 8px}
.win{display:flex;align-items:center;gap:10px;background:#F7F6F3;border-radius:22px;padding:14px 18px;margin-bottom:6px;font-size:15px}
.win .x{flex:1}.win .tag{font-size:11px;color:#6E5848;background:#F2F0EB;border-radius:999px;padding:4px 10px}
.win .dot{width:10px;height:10px}.star{color:#1F5F50;font-size:14px}
.day{margin-bottom:16px}
.more{text-align:center;font-size:14px;font-weight:700;color:#1F5F50;padding:11px;background:#F2F0EB;border-radius:22px}
.older{text-align:center;color:#6E5848;font-size:13px;line-height:19px;padding:12px 0}
.dup{position:relative;outline:2.5px dashed #D9534F;outline-offset:4px;border-radius:16px;margin-bottom:22px}
.dup>.lab{position:absolute;right:-6px;top:-16px;z-index:5;background:#D9534F;color:#fff;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px}
.wk{margin:6px 0 14px}
.wk .k{font-size:13px;color:#6E5848;font-weight:700;margin:0 4px 2px}
.wk .n{font-size:22px;font-weight:800;margin:0 4px 8px}
.wk .cd{display:flex;flex-wrap:wrap;gap:10px;margin:0 4px;font-size:12px;color:#6E5848}
.wk .cd span{display:flex;align-items:center;gap:4px}
.sec{border-top:6px solid #F7F6F3;margin:12px -20px 0;padding:22px 20px 0}
.new{position:absolute;background:#2F7D6B;color:#fff;font-size:10px;font-weight:800;padding:2px 7px;border-radius:999px;z-index:6}
.gone{display:flex;align-items:center;justify-content:center;height:46px;border:2px dashed #C9BBA8;border-radius:16px;color:#A8968A;font-size:12px;margin-bottom:14px}
.tab{position:absolute;left:20px;right:20px;bottom:24px;height:68px;border-radius:999px;background:#F7F6F3;box-shadow:0 4px 14px rgba(74,50,38,.12);display:flex;justify-content:space-around;align-items:center;font-size:12px;color:#6E5848;z-index:8}
.tab b{color:#1F5F50}
.daypg h2{font-size:22px;font-weight:800;margin:10px 4px 2px}
"""

def jar(n=19):
    K = 290 / 800; IN_X0, IN_X1, IN_YB = 96 * K, 704 * K, 918 * K; M = 31; RH = M * .88
    start = IN_X0 + (IN_X1 - IN_X0 - 7 * M) / 2
    ms = ''
    for i, c in enumerate(JAR[:n]):
        r, col = divmod(i, 7)
        x = start + col * M + (M * .12 if r % 2 else -M * .12); y = IN_YB - M - r * RH
        ms += f'<img class="m" src="{A}marble_{c}.webp" style="left:{x:.1f}px;top:{y:.1f}px">'
    return (f'<div class="jar"><img class="l" src="{A}jar_back.webp">{ms}'
            f'<img class="l" src="{A}jar_front.webp" style="z-index:2"></div><div class="link">목록으로 보기</div>')

def head():
    return ('<div class="head"><h1>나의 작은 승리 유리병</h1><div class="search">⌕ 찾기</div></div>'
            '<div class="lead">지금까지 구슬 69개. 구슬은 줄어들지 않아.</div>')

def win(c, t, s):
    return (f'<div class="win"><div class="dot" style="background:{CAT[c][1]}"></div><div class="x">{t}</div>'
            + ('<span class="star">★</span>' if s else '') + f'<span class="tag">{CAT[c][0]}</span></div>')

def day_now(d):  # 지금 WinList: 7개 이상이면 '펼치기'
    ws = DAYS[d]
    body = (f'<div class="win"><b class="x">{d} {len(ws)}가지 · 펼치기</b></div>' if len(ws) > 6
            else ''.join(win(*w) for w in ws))
    return f'<div class="day"><div class="dayh">{d} ›</div>{body}</div>'

def day_new(d, cap=5):
    ws = DAYS[d]
    body = ''.join(win(*w) for w in ws[:cap])
    if len(ws) > cap:
        body += f'<div class="more">+{len(ws) - cap}개 더 보기 ›</div>'
    return f'<div class="day"><div class="dayh">{d} ›</div>{body}</div>'

def shelf():
    b = ''.join(f'<i style="background:{CAT[c][1]}"></i>' for c in (JAR * 3)[:50])
    return (f'<div class="shelf"><div class="sj"><div class="lid"></div><div class="b">{b}</div><p>1번째 병</p></div></div>'
            '<div class="board"></div>')

def chips():
    cs = [('star', '★ 다시 보고 싶은 3')] + [(k, f'{CAT[k][0]} {n}') for k, n in [('eat', 14), ('tidy', 11), ('move', 9), ('work', 8)]]
    return '<div class="chips">' + ''.join(
        f'<div class="chip">' + ('' if k == 'star' else f'<span class="dot" style="background:{CAT[k][1]}"></span>') + f'{t}</div>'
        for k, t in cs) + '</div>'

def weekcard(title, days, memory=True):
    ws = [w for d in days for w in DAYS[d]]
    cnt = {}
    for c, _, _ in ws: cnt[c] = cnt.get(c, 0) + 1
    mr = ''.join(f'<i style="background:{CAT[c][1]}"></i>' for c, _, _ in ws)
    pl = ''.join(f'<div class="pill"><span class="dot" style="background:{CAT[c][1]}"></span>{CAT[c][0]} {n}</div>' for c, n in cnt.items())
    mem = '<div class="mem"><b>이 순간 기억나?</b><span>“엄마한테 전화” · 11월 17일 (화)</span></div>' if memory else ''
    return f'<div class="card"><div class="t" style="margin-left:0">{title}</div><div class="big">너는 {len(ws)}가지를 해냈어</div><div class="mrow">{mr}</div><div class="pills">{pl}</div>{mem}</div>'

def weekhead(k, days):
    ws = [w for d in days for w in DAYS[d]]
    cnt = {}
    for c, _, _ in ws: cnt[c] = cnt.get(c, 0) + 1
    cd = ''.join(f'<span><i class="dot" style="background:{CAT[c][1]}"></i>{n}</span>' for c, n in cnt.items())
    return f'<div class="wk"><div class="k">{k}</div><div class="n">{len(ws)}가지 해냈어</div><div class="cd">{cd}</div></div>'

def col(cap, sub, inner, rec=False, fix=False, fold=True):
    return (f'<div class="col"><div class="cap{" rec" if rec else ""}">{cap}</div><div class="sub">{sub}</div>'
            f'<div class="phone{" fix" if fix else ""}">{inner}'
            + ('<div class="fold"><span>여기까지 첫 화면</span></div>' if fold and not fix else '') + '</div></div>')

def page(cols):
    return f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><body>{"".join(cols)}</body>'

# ---------- sheet1: 지금 vs 정리안 (화면 전체 길이)
now = (head() + jar() + '<div class="t">선반 · 꽉 찬 병 1개</div>' + shelf()
       + '<div class="dup"><span class="lab">② 분류 칩</span><div class="t">분류별로 보기</div>' + chips() + '</div>'
       + '<div class="dup"><span class="lab">① 구슬 · ② 분류 · ③ 같은 기간</span>' + weekcard('이번 주 유리병', THIS) + '</div>'
       + '<div class="alink">지난 주 돌아보기 (8) ›</div>'
       + '<div class="dup"><span class="lab">③ 이번 주 + 지난 주 섞임</span><div class="t">최근 2주</div>'
       + ''.join(day_now(d) for d in THIS + LAST[:2]) + '</div>'
       + '<div class="older">더 지난 기록은 선반의 병을 열거나 찾기로 볼 수 있어. 하나도 없어지지 않아.</div>')
new = (head() + jar()
       + '<div style="position:relative"><span class="new" style="right:10px;top:-8px">NEW 자리</span>'
       + '<div class="mem top"><b>이 순간 기억나?</b><span>“엄마한테 전화” · 11월 17일 (화)</span></div></div>'
       + weekhead('이번 주', THIS) + ''.join(day_new(d) for d in THIS)
       + '<div class="sec">' + weekhead('지난 주', LAST) + ''.join(day_new(d) for d in LAST) + '</div>'
       + '<div class="sec"><div class="wk"><div class="k">더 지난 기록</div><div class="n" style="font-size:17px">하나도 없어지지 않아</div></div>'
       + '<div class="t">선반 · 꽉 찬 병 1개</div>' + shelf()
       + '<div class="t">분류별로 보기</div>' + chips()
       + '<div class="older" style="padding-top:0">위 ⌕ 찾기로 글자를 찾아도 돼</div></div>')
open(os.path.join(HERE, 'sheet1.html'), 'w').write(page([
    col('지금', '빨간 점선 = 같은 내용이 다른 모양으로 또 나오는 곳 (①②③)', now),
    col('정리안 · 시간 순서 하나로', '병 → 이번 주 → 지난 주 → 더 지난 기록. 주 카드·구슬 줄·지난 주 카드·펼치기 없음', new, rec=True),
]))

# ---------- sheet2: 결정별 다른 선택지 (첫 화면 844)
g3 = ('<div class="dayh" style="text-align:center">(아래로 내린 모습)</div>'
      + weekhead('이번 주', THIS) + day_new('어제') + day_new('11월 17일 (화)')
      + '<div class="tab"><span>방</span><b>유리병</b><span>꾸미기</span><span>설정</span></div>')
dayp = ('<div class="dayh" style="font-size:15px">‹ 유리병</div><div class="daypg"><h2>11월 17일 (화)</h2>'
        '<div class="lead" style="margin:0 4px 14px">8가지 해냈어 · 좌우로 넘기면 기록한 다른 날</div></div>'
        + ''.join(win(*w) for w in DAYS['11월 17일 (화)']))
g1b = (head() + jar()
       + '<div class="card"><div class="t" style="margin-left:0">이번 주 유리병</div><div class="big">너는 15가지를 해냈어</div>'
       + '<div class="mem"><b>이 순간 기억나?</b><span>“엄마한테 전화” · 11월 17일 (화)</span></div></div>'
       + '<div class="dup" style="outline-color:#E0A33A"><span class="lab" style="background:#E0A33A">같은 주가 목록으로 또</span>'
       + weekhead('이번 주', THIS) + day_new('오늘') + '</div>'
       + '<div class="tab"><span>방</span><b>유리병</b><span>꾸미기</span><span>설정</span></div>')
g4b = (head() + jar()
       + '<div class="t">선반 · 꽉 찬 병 1개</div>' + shelf() + '<div class="t">분류별로 보기</div>' + chips()
       + '<div class="mem top" style="margin-bottom:14px"><b>이 순간 기억나?</b><span>“엄마한테 전화” · 11월 17일 (화)</span></div>'
       + weekhead('이번 주', THIS)
       + '<div class="tab"><span>방</span><b>유리병</b><span>꾸미기</span><span>설정</span></div>')
open(os.path.join(HERE, 'sheet2.html'), 'w').write(page([
    col('G3-A · 많은 날은 5개 + “더 보기”', '기록 6개 이상인 날: 5개만, 나머지는 “+n개 더 보기” (펼치기 대신)', g3, rec=True, fix=True),
    col('G3-A · 누르면 하루 한 장', '“+3개 더 보기”나 날짜 제목 = 같은 화면. 하루를 여는 길이 하나', dayp, rec=True, fix=True),
    col('G1-B · 이번 주 카드 남기기', '구슬 줄·분류 알약만 빼고 카드 유지. 같은 주가 카드+목록 두 번', g1b, fix=True),
    col('G4-B · 선반·분류 칩 병 바로 아래', '오래된 병이 잘 보이지만 이번 주 기록은 첫 화면 밖으로 밀림', g4b, fix=True),
]))

# ---------- sheet3: 분류별 보기 자리 (대표: 맨 아래는 쓰기 힘듦)
TAB = '<div class="tab"><span>방</span><b>유리병</b><span>꾸미기</span><span>설정</span></div>'
mem = '<div class="mem top" style="margin-bottom:16px"><b>이 순간 기억나?</b><span>“엄마한테 전화” · 11월 17일 (화)</span></div>'
small_jar = '<div style="transform:scale(.7);transform-origin:top center;height:285px">' + jar() + '</div>'
def chips_wrap():
    cs = [('star', '★ 다시 보고 싶은 3')] + [(k, f'{CAT[k][0]} {n}') for k, n in [('eat', 14), ('tidy', 11), ('move', 9), ('work', 8), ('care', 7), ('study', 6), ('people', 5), ('cheer', 4), ('endure', 2)]]
    return '<div class="chips" style="flex-wrap:wrap">' + ''.join(
        f'<div class="chip">' + ('' if k == 'star' else f'<span class="dot" style="background:{CAT[k][1]}"></span>') + f'{t}</div>' for k, t in cs) + '</div>'
pa1 = ('<div style="position:relative">' + '<div class="head"><h1>나의 작은 승리 유리병</h1><div class="search" style="outline:2.5px solid #2F7D6B">⌕ 찾기·모아보기</div></div>'
       + '<div class="lead">지금까지 구슬 69개. 구슬은 줄어들지 않아.</div></div>' + small_jar + mem + weekhead('이번 주', THIS) + day_new('오늘') + TAB)
pa2 = ('<div class="dayh" style="font-size:15px">‹ 유리병</div><h2 style="font-size:22px;font-weight:800;margin:10px 4px 14px">찾기·모아보기</h2>'
       + '<div class="win" style="color:#6E5848">⌕ 예) 산책, 엄마, 책</div><div style="height:18px"></div>'
       + '<div class="t">모아보기</div>' + chips_wrap()
       + '<div class="t" style="margin-top:8px">선반 · 꽉 찬 병 1개</div>' + shelf())
pb = (head() + small_jar
      + '<div style="position:relative"><span class="new" style="right:6px;top:-10px">NEW 자리</span>' + chips() + '</div>'
      + mem + weekhead('이번 주', THIS) + day_new('오늘') + TAB)
sticky = ('<div style="position:absolute;left:0;right:0;top:0;background:#fff;padding:58px 20px 10px;z-index:7;box-shadow:0 6px 10px -8px rgba(74,50,38,.25)">'
          '<div class="chips" style="margin:0"><div class="chip">전체</div><div class="chip">★ 3</div>'
          f'<div class="chip" style="background:#E3F1EC;color:#1F5F50"><span class="dot" style="background:{CAT["move"][1]}"></span>몸 움직이기 9 ✕</div>'
          f'<div class="chip"><span class="dot" style="background:{CAT["eat"][1]}"></span>잘 먹기 14</div></div></div>')
mv = lambda d: [w for w in DAYS[d] if w[0] == 'move']
pc = (sticky + '<div style="height:46px"></div>'
      + '<div class="wk"><div class="k">이번 주 · 몸 움직이기</div><div class="n">2가지</div></div>'
      + ''.join(f'<div class="day"><div class="dayh">{d} ›</div>' + ''.join(win(*w) for w in mv(d)) + '</div>' for d in THIS if mv(d))
      + '<div class="sec"><div class="wk"><div class="k">지난 주 · 몸 움직이기</div><div class="n">1가지</div></div>'
      + ''.join(f'<div class="day"><div class="dayh">{d} ›</div>' + ''.join(win(*w) for w in mv(d)) + '</div>' for d in LAST if mv(d))
      + '<div class="more">더 지난 몸 움직이기 6개 보기 ›</div></div>' + TAB)
open(os.path.join(HERE, 'sheet3.html'), 'w').write(page([
    col('F-A ① · 위 버튼 “찾기·모아보기”', '맨 위 버튼 하나로. 유리병 탭에 칩이 아예 없음', pa1, fix=True),
    col('F-A ② · 누르면 나오는 화면', '글자 찾기 + ☆·분류 칩 + 선반. 오래된 기록 찾기를 한 곳에', pa2, fix=True),
    col('F-B · 병 바로 아래 칩 한 줄', '첫 화면에서 보임. 이번 주 기록이 한 줄(약 50pt) 내려감', pb, rec=True, fix=True),
    col('F-C · 위에 붙는 거르기 칩', '내리면 칩 줄이 위에 붙고, 누르면 이 화면 기록이 그 분류만 남음', pc, fix=True),
]))

# ---------- sheet4: F-B 흐름 (칩 누르기 → 분류 목록 화면 → ‹ 유리병 = 전체)
finger = '<div style="position:absolute;width:44px;height:44px;border-radius:22px;background:rgba(47,125,107,.35);border:2px solid #2F7D6B;z-index:9;{}"></div>'
def chips4():
    cs = [('star', '★ 다시 보고 싶은 3')] + [(k, f'{CAT[k][0]} {n}') for k, n in [('move', 14), ('tidy', 11), ('eat', 9)]]
    return '<div class="chips">' + ''.join(f'<div class="chip">' + ('' if k == 'star' else f'<span class="dot" style="background:{CAT[k][1]}"></span>') + f'{t}</div>' for k, t in cs) + '</div>'
pb1 = (head() + small_jar + '<div style="position:relative">' + chips4()
       + finger.format('left:190px;top:-4px') + '</div>' + mem + weekhead('이번 주', THIS) + day_new('오늘') + TAB)
MOVE = [('11월 19일 (목)', '10분 산책', 1), ('11월 17일 (화)', '스트레칭', 0), ('11월 13일 (금)', '계단으로 올라감', 0),
        ('11월 5일 (목)', '요가 15분', 0), ('11월 2일 (월)', '자전거 타기', 0), ('10월 28일 (수)', '산책', 0), ('10월 21일 (수)', '스쿼트 20개', 0)]
rows, cur = '', ''
for dd, t, st_ in MOVE:
    m = dd.split('월')[0] + '월'
    if m != cur:
        rows += f'<div class="t" style="font-size:15px;color:#4A3226;margin-top:10px">{m}</div>'; cur = m
    rows += (f'<div class="win"><div class="dot" style="background:{CAT["move"][1]}"></div><div class="x">{t}'
             f'<div style="font-size:12px;color:#6E5848;margin-top:2px">{dd}</div></div>' + ('<span class="star">★</span>' if st_ else '') + '</div>')
pb2 = ('<div class="dayh" style="font-size:15px;color:#1F5F50;outline:2.5px solid #2F7D6B;outline-offset:4px;border-radius:10px;display:inline-block">‹ 유리병</div>'
       f'<h2 style="font-size:24px;font-weight:800;margin:12px 4px 4px;display:flex;align-items:center;gap:10px"><span class="dot" style="width:14px;height:14px;background:{CAT["move"][1]}"></span>몸 움직이기</h2>'
       '<div class="lead" style="margin:0 4px 10px">지금까지 14가지 모였어.</div>' + rows)
pb3 = (head() + small_jar + chips4() + mem + weekhead('이번 주', THIS) + day_new('오늘') + TAB)
open(os.path.join(HERE, 'sheet4.html'), 'w').write(page([
    col('① 칩 누르기', '병 아래 칩 줄에서 “몸 움직이기” 탭', pb1, rec=True, fix=True),
    col('② 그 분류만 모은 화면', '새 화면(지금 있는 분류 목록). 달별로, 처음부터 전부. 기록 누르면 크게 보기', pb2, rec=True, fix=True),
    col('③ ‹ 유리병 (또는 뒤로 밀기)', '해지 버튼 없이 원래 화면 그대로, 전체가 보임. 보던 위치도 유지', pb3, rec=True, fix=True),
]))

print('ok')
