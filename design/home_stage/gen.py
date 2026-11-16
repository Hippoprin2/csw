#!/usr/bin/env python3
"""홈 화면 '하마 무대' 시안 (의견 단계, 앱 코드 안 바꿈). python3 gen.py → sheet1~3.html → Chrome 헤드리스로 png"""
import json, pathlib, subprocess

D = pathlib.Path(__file__).resolve().parent
ROOT = D.parent.parent
M = json.load(open(ROOT / 'design/world/export/v1/manifest.json'))['spaces']['room']
W = '../world/export/v1/'
CH = '../character/export/v1/'
SHOWN = ['curtain', 'frame', 'wall_clock', 'string_lights', 'bookshelf', 'bed', 'aquarium', 'rug', 'low_table', 'lamp', 'cushion', 'big_plant']


def room(s, left, top, extra='', cls='room'):
    """넓은 방(2160x1080)을 배율 s, 위치(left, top)로. 소품은 manifest 좌표 그대로"""
    its = sorted([i for i in M['items'] if i['id'] in SHOWN], key=lambda i: i['z'])
    h = [f'<img src="{W}{M["background"]}" style="left:0;top:0;width:{2160*s}px;height:{1080*s}px">']
    for i in its:
        h.append(f'<img src="{W}{i["file"]}" style="left:{i["x"]*s}px;top:{i["y"]*s}px;width:{i["w"]*s}px;height:{i["h"]*s}px">')
    return f'<div class="{cls}" style="left:{left}px;top:{top}px;width:{2160*s}px;height:{1080*s}px;{extra}">{"".join(h)}</div>'


def room_pet(s):
    cam = 195 - 1066 * s
    return room(s, cam, 0) + hippo('idle', 435 * s, 496 * s, 848 * s + cam)


def stage_room(blur=True):
    s = 844 / 1080
    return room(s, 195 - 1066 * s, 0, 'filter:blur(7px) saturate(.9);' if blur else '')


def hippo(clip='idle', w=600, top=150, left=None):
    left = (390 - w) / 2 if left is None else left
    return f'<img class="hippo" src="{CH}hippo_{clip}_poster.png" style="width:{w}px;left:{left}px;top:{top}px">'


TOP = '''<div class="top"><span class="pill">11월 16일 월 · 꼬마하마의 방</span><span class="pill leaf"><i class="lf"></i>9</span></div>'''
SWITCH = '<div class="sw"><span>텃밭</span><span class="on">방</span><span>마당</span></div>'
TAB = '<div class="tabbar"><span class="on">방</span><span>유리병</span><span>꾸미기</span><span>설정</span></div>'
INPUT = '<div class="inp"><span>오늘 해낸 거, 아무리 작아도 좋아</span><b class="send">↑</b></div>'
PEEK = '<div class="peek"><span class="grabi"></span><b>오늘의 쪽지 3</b><span class="muted"> · 방금 침대 정리했다</span><span class="chev">⌃</span></div>'


def phone(cap, sub, body, bg='#FFFFFF'):
    return f'<div class="col"><div class="cap">{cap}</div><div class="phone" style="background:{bg}">{body}</div><div class="capsub">{sub}</div></div>'


def new(x, y, t='NEW'):
    return f'<span class="new" style="left:{x}px;top:{y}px">{t}</span>'


CSS = '''
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #E9E2D4; font-family: -apple-system, "Apple SD Gothic Neo", sans-serif; color: #4A3226; padding: 26px; }
.row { display: flex; gap: 28px; align-items: flex-start; }
.col { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.cap { font-size: 19px; font-weight: 800; background: #fff; padding: 8px 18px; border-radius: 999px; }
.capsub { font-size: 14px; color: #6E5848; width: 390px; text-align: center; line-height: 1.45; }
.phone { width: 390px; height: 844px; border-radius: 44px; overflow: hidden; position: relative; box-shadow: 0 8px 30px rgba(74,50,38,.18); }
.room, .room img { position: absolute; }
.veil { position: absolute; inset: 0; background: rgba(255,255,255,.42); }
.hippo { position: absolute; }
.top { position: absolute; top: 54px; left: 16px; right: 16px; display: flex; justify-content: space-between; z-index: 5; }
.pill { background: rgba(255,255,255,.94); border-radius: 999px; padding: 8px 14px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 6px; }
.lf { width: 12px; height: 12px; background: #2F7D6B; border-radius: 0 10px 0 10px; display: inline-block; }
.sw { position: absolute; top: 100px; left: 50%; transform: translateX(-50%); display: flex; gap: 2px; background: rgba(255,255,255,.9); border-radius: 999px; padding: 3px; font-size: 12px; color: #6E5848; z-index: 5; }
.sw span { padding: 5px 13px; border-radius: 999px; }
.sw .on { background: #E3F1EC; color: #1F5F50; font-weight: 800; }
.tabbar { position: absolute; left: 16px; right: 16px; bottom: 24px; height: 64px; background: #F7F6F3; border-radius: 999px; display: flex; justify-content: space-around; align-items: center; box-shadow: 0 6px 18px rgba(74,50,38,.12); font-size: 12px; color: #6E5848; z-index: 6; }
.tabbar .on { background: #E3F1EC; color: #1F5F50; font-weight: 800; padding: 10px 18px; border-radius: 999px; }
.inp { position: absolute; left: 16px; right: 16px; bottom: 100px; height: 54px; background: #F7F6F3; border-radius: 999px; display: flex; align-items: center; padding: 0 6px 0 20px; font-size: 15px; color: #A8968A; z-index: 6; box-shadow: 0 4px 14px rgba(74,50,38,.10); }
.inp span { flex: 1; }
.send { width: 42px; height: 42px; border-radius: 99px; background: #2F7D6B; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.peek { position: absolute; left: 16px; right: 16px; bottom: 164px; height: 44px; background: rgba(255,255,255,.96); border-radius: 22px; display: flex; align-items: center; padding: 0 16px; font-size: 13.5px; z-index: 6; box-shadow: 0 3px 12px rgba(74,50,38,.08); white-space: nowrap; overflow: hidden; }
.peek .muted { color: #6E5848; flex: 1; overflow: hidden; text-overflow: ellipsis; }
.chev { color: #6E5848; font-size: 16px; margin-left: 6px; }
.bubble { position: absolute; background: #fff; border-radius: 20px; padding: 10px 16px; font-size: 15px; font-weight: 700; z-index: 5; box-shadow: 0 4px 14px rgba(74,50,38,.12); white-space: nowrap; }
.bubble:after { content: ''; position: absolute; bottom: -8px; left: 50%; margin-left: -8px; border: 8px solid transparent; border-bottom: 0; border-top-color: #fff; }
.rec { position: absolute; left: 50%; transform: translateX(-50%); background: #fff; border-radius: 22px; padding: 12px 18px; font-size: 15px; z-index: 5; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 16px rgba(74,50,38,.12); white-space: nowrap; }
.dot { width: 10px; height: 10px; border-radius: 99px; display: inline-block; }
.float { position: absolute; color: #2F7D6B; font-weight: 800; font-size: 16px; z-index: 5; }
.new { position: absolute; background: #2F7D6B; color: #fff; font-size: 12px; font-weight: 800; padding: 5px 11px; border-radius: 999px; z-index: 9; }
.scrim { position: absolute; inset: 0; background: rgba(74,50,38,.32); z-index: 7; }
.sheet { position: absolute; left: 0; right: 0; bottom: 0; background: #fff; border-radius: 32px 32px 0 0; padding: 12px 20px 30px; z-index: 8; }
.grab { width: 40px; height: 5px; border-radius: 9px; background: #E4E0D8; margin: 0 auto 14px; }
.grabi { width: 4px; }
.h { font-size: 17px; font-weight: 800; margin-bottom: 10px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.chip { height: 34px; padding: 0 13px; border-radius: 999px; background: #F2F0EB; font-size: 13px; display: flex; align-items: center; }
.chip.on { background: #E3F1EC; color: #1F5F50; font-weight: 800; }
.win { display: flex; align-items: center; gap: 10px; background: #F7F6F3; border-radius: 22px; padding: 13px 16px; margin-bottom: 6px; font-size: 15px; }
.win .t { flex: 1; } .win .tm { font-size: 12px; color: #6E5848; }
.kb { position: absolute; left: 0; right: 0; bottom: 0; height: 290px; background: #D3D6DC; z-index: 9; display: flex; align-items: center; justify-content: center; color: #8a8f99; font-size: 14px; }
.field { background: #F7F6F3; border-radius: 999px; height: 52px; display: flex; align-items: center; padding: 0 6px 0 18px; font-size: 15px; margin-bottom: 10px; }
.field span { flex: 1; }
.iconbtn { width: 40px; height: 40px; border-radius: 99px; background: rgba(255,255,255,.94); display: flex; align-items: center; justify-content: center; font-size: 17px; z-index: 6; position: absolute; }
.note-ic { width: 18px; height: 14px; border: 2px solid #4A3226; border-radius: 3px; position: relative; }
.note-ic:after { content: ''; position: absolute; left: 3px; right: 3px; top: 3px; height: 2px; background: #4A3226; box-shadow: 0 4px 0 #4A3226; }
.shot { position: absolute; inset: 0; width: 390px; }
.tag { font-size: 12px; font-weight: 800; color: #1F5F50; background: #E3F1EC; border-radius: 999px; padding: 6px 12px; position: absolute; z-index: 6; white-space: nowrap; }
.card { position: absolute; background: #F7F6F3; border-radius: 22px; }
.arrow { position: absolute; font-size: 22px; color: #2F7D6B; font-weight: 900; z-index: 9; }
'''


def page(name, phones):
    n = len(phones)
    (D / f'{name}.html').write_text(f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><div class="row">{"".join(phones)}</div>')
    w = n * 418 + 30
    subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless=new', '--disable-gpu',
                    '--allow-file-access-from-files', '--hide-scrollbars', f'--window-size={w},1010',
                    f'--screenshot={D}/{name}.png', f'file://{D}/{name}.html'], check=True, capture_output=True)


# ---------- sheet1: 홈 배치 ----------
cur = phone('지금', '방 그림 약 45%, 입력·칩·공간 탭이 아래 반 이상',
            '<img class="shot" src="../screens/05_room.png">')
ha = phone('H-A · 흐린 방 무대 ← 추천', '하마가 화면 가운데 크게. 방은 뒤에서 뿌옇게(소품은 색만 보임). 입력은 알약 한 줄',
           stage_room() + '<div class="veil"></div>' + hippo('idle', 370, 130) + TOP + SWITCH + PEEK + INPUT + TAB + new(296, 600))
hb = phone('H-B · 흰 바탕 무대', '방 없이 하마만. 가장 깔끔하지만 산 소품·방이 홈에서 안 보임',
           hippo('idle', 370, 130) 
           + TOP.replace('꼬마하마의 방', '꼬마하마') + SWITCH + PEEK + INPUT + TAB)
cel = phone('H-A · 기록한 순간', '입력이 내려가고 하마 동작이 화면 주인공. 적은 문장이 카드로 떠서 "이걸 축하하는 중"이 보임',
            stage_room() + '<div class="veil" style="background:rgba(255,255,255,.55)"></div>' + hippo('tidy', 430, 115)
            + TOP + '<div class="bubble" style="left:96px;top:150px">침대 정리 최고야!</div>'
            + '<div class="rec" style="top:700px"><i class="dot" style="background:#7FB3A0"></i>침대 정리했다</div>'
            + '<div class="float" style="left:276px;top:654px">+1 씨앗</div>' + TAB)
page('sheet1', [cur, ha, hb, cel])

# ---------- sheet2: 입력 + 쪽지 ----------
inp = phone('입력 · 누르면 펼침', '알약을 누르면 키보드 위로 올라옴: 오늘/어제, 예시 칩, 분류. 보내면 다시 한 줄로',
            stage_room() + '<div class="veil"></div>' + hippo('idle', 340, 90) + TOP + '<div class="scrim" style="background:rgba(74,50,38,.12)"></div>'
            + '<div class="sheet" style="bottom:290px;border-radius:32px;left:8px;right:8px;padding:16px 16px 14px">'
              '<div class="chips"><span class="chip on">오늘</span><span class="chip">어제</span></div>'
              '<div class="field"><span>침대 정리했다</span><b class="send">↑</b></div>'
              '<div style="font-size:13px;color:#6E5848;margin:2px 4px 10px"><b style="color:#4A3226">정리</b> 동작을 할 거예요 · <u>바꾸기</u></div>'
              '<div class="chips" style="margin:0"><span class="chip">물 한 잔 마셨다</span><span class="chip">10분 산책</span><span class="chip">사워했다</span></div></div>'
            + '<div class="kb">키보드</div>')
na1 = phone('N-A · 쪽지 접힘 ← 추천', '입력 위 한 줄: 오늘 몇 가지 + 방금 적은 것. 저장됐다는 확인도 겸함',
            stage_room() + '<div class="veil"></div>' + hippo('idle', 370, 130) + TOP + SWITCH + PEEK + INPUT + TAB + new(290, 448, '한 줄'))
na2 = phone('N-A · 끌어올리면', '반쯤 올라오는 시트 = 오늘의 쪽지(지금과 같은 목록). 줄 누르면 크게 보기, 아래로 내리면 접힘',
            stage_room() + '<div class="veil"></div>' + hippo('idle', 340, 90) + TOP
            + '<div class="sheet" style="bottom:0;padding-bottom:110px"><div class="grab"></div><div class="h">오늘의 쪽지 · 3가지 <span style="float:right;font-size:13px;color:#6E5848;font-weight:600">다 보기 ›</span></div>'
              '<div class="win"><i class="dot" style="background:#7FB3A0"></i><span class="t">침대 정리했다</span><span class="tm">오전 9:12</span></div>'
              '<div class="win"><i class="dot" style="background:#E3A86B"></i><span class="t">물 한 잔 마셨다</span><span class="tm">오전 8:40</span></div>'
              '<div class="win"><i class="dot" style="background:#8FA9D8"></i><span class="t">영단어 20개 외움</span><span class="tm">오전 7:55</span></div></div>' + TAB)
nb = phone('N-B · 위 쪽지 아이콘', '하마 화면이 가장 넓음. 대신 방금 적은 게 저장됐는지 바로 안 보이고, 숫자 배지는 "안 읽은 알림"처럼 보임',
           stage_room() + '<div class="veil"></div>' + hippo('idle', 370, 150) + TOP.replace('<span class="pill leaf">', '<span style="display:flex;gap:8px"><span class="pill"><i class="note-ic"></i>3</span><span class="pill leaf">').replace('9</span></div>', '9</span></span></div>')
           + SWITCH + INPUT + TAB + new(232, 20, '쪽지'))
page('sheet2', [inp, na1, na2, nb])

# ---------- sheet3: 방 꾸미기 접근 ----------
s = 520 / 1080
ra1 = phone('R-A · 무대에서 "방 보기"', '하마 화면 오른쪽 위 작은 버튼(또는 방 그림을 두 번 탭)',
            stage_room() + '<div class="veil"></div>' + hippo('idle', 370, 130) + TOP + SWITCH
            + '<span class="pill" style="position:absolute;right:16px;top:146px;z-index:6">방 보기 ⤢</span>' + PEEK + INPUT + TAB + new(240, 186, 'NEW'))
ra2 = phone('R-A · 방 모드 ← 추천', '뿌연 막이 걷히고 지금 방 화면 그대로(끌어 둘러보기·유리장·바구니). "꾸미기" 누르면 꾸미기 탭, "‹ 하마"로 복귀',
            room_pet(740 / 1080)
            + '<div class="top"><span class="pill">‹ 하마</span><span style="display:flex;gap:8px"><span class="pill">수확 바구니 2</span><span class="pill" style="background:#2F7D6B;color:#fff">꾸미기</span></span></div>'
            + '<div class="tag" style="left:110px;top:700px">← 끌어서 방 둘러보기 →</div>' + TAB, bg='#EADBC4')
rb = phone('R-B · 꾸미기 탭에 방 미리보기', '꾸미기 탭 위쪽이 선명한 방(끌어 둘러보기·유리장), 아래가 상점. 홈은 하마만',
           room_pet(s)
           + '<div style="position:absolute;left:0;right:0;top:505px;bottom:0;background:#fff;border-radius:28px 28px 0 0;padding:18px 18px">'
             '<div class="h">방 꾸미기</div><div class="chips"><span class="chip on">방</span><span class="chip">마당</span><span class="chip">테마</span></div>'
             '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
           + ''.join(f'<div style="background:#F7F6F3;border-radius:22px;height:104px;display:flex;align-items:center;justify-content:center"><img src="../world/export/v1/thumbs/{t}.webp" style="width:72px"></div>'
                     for t in ['bed', 'lamp', 'aquarium', 'easel', 'guitar', 'radio_stand'])
           + '</div></div>' + TAB.replace('<span class="on">방</span><span>유리병</span><span>꾸미기</span>', '<span>방</span><span>유리병</span><span class="on">꾸미기</span>'))
rc = phone('R-C · 방을 별도 페이지로', '텃밭 ← 방 ← 홈(하마) → 마당. 공간이 4개로 늘고 "하마는 어디 사는지"가 흐려짐',
           stage_room() + '<div class="veil"></div>' + hippo('idle', 370, 130) + TOP
           + '<div class="sw"><span>텃밭</span><span>방</span><span class="on">홈</span><span>마당</span></div>' + PEEK + INPUT + TAB)
page('sheet3', [ra1, ra2, rb, rc])
print('ok')
