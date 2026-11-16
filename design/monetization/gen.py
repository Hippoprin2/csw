#!/usr/bin/env python3
"""과금 체계(P1~P3 + 연간 Y1~Y3 추천안) 화면 시안. 의견 단계 — 앱 코드·문서 안 바꿈.
python3 gen.py → sheet1~2.html/png (home_stage/gen.py 의 방·하마·CSS 재사용)"""
import importlib.util, pathlib, subprocess

D = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hs', D.parent / 'home_stage/gen.py')
src = (D.parent / 'home_stage/gen.py').read_text().split('# ---------- sheet1')[0]
hs = {'__file__': str(D.parent / 'home_stage/gen.py')}
exec(src, hs)
stage_room, hippo, phone, new = hs['stage_room'], hs['hippo'], hs['phone'], hs['new']
TOP, SWITCH, TAB, INPUT, PEEK = hs['TOP'], hs['SWITCH'], hs['TAB'], hs['INPUT'], hs['PEEK']
TOP = TOP.replace('11월 16일 월', '12월 2일 수')

CSS = hs['CSS'] + '''
.sh { font-size: 20px; font-weight: 800; line-height: 1.4; margin: 4px 2px 6px; }
.sp { font-size: 14px; color: #6E5848; line-height: 1.55; margin: 0 2px 14px; }
.btn { height: 52px; border-radius: 999px; background: #2F7D6B; color: #fff; font-weight: 800; font-size: 16px; display: flex; align-items: center; justify-content: center; }
.btn2 { height: 44px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: #6E5848; font-weight: 700; }
.plans { display: flex; gap: 8px; margin-bottom: 14px; }
.plan { flex: 1; background: #F7F6F3; border-radius: 22px; padding: 14px 14px 13px; position: relative; }
.plan.on { background: #E3F1EC; box-shadow: inset 0 0 0 2px #2F7D6B; }
.plan .nm { font-size: 13px; color: #6E5848; font-weight: 700; }
.plan .pr { font-size: 21px; font-weight: 800; margin: 4px 0 2px; }
.plan .pe { font-size: 12.5px; color: #6E5848; }
.plan .rd { position: absolute; right: 12px; top: 13px; width: 20px; height: 20px; border-radius: 99px; background: #fff; }
.plan.on .rd { background: #2F7D6B; box-shadow: inset 0 0 0 5px #E3F1EC; }
.keep { background: #F7F6F3; border-radius: 22px; padding: 12px 16px; font-size: 13px; line-height: 1.7; margin-bottom: 14px; }
.keep b { color: #1F5F50; }
.fine { font-size: 11.5px; color: #8A7666; line-height: 1.55; margin: 10px 4px 0; text-align: center; }
.links { font-size: 12px; color: #6E5848; text-align: center; margin-top: 8px; }
.links u { margin: 0 6px; }
.set { position: absolute; inset: 0; padding: 62px 20px 0; background: #fff; }
.set h1 { font-size: 26px; font-weight: 800; margin: 0 2px 14px; }
.sec { font-size: 13px; color: #6E5848; font-weight: 700; margin: 16px 6px 6px; }
.grp { background: #F7F6F3; border-radius: 22px; overflow: hidden; }
.grp .r { padding: 15px 18px; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
.grp .r + .r { border-top: 1px solid #ECE9E3; }
.grp .r .m { color: #6E5848; font-size: 13.5px; }
.lock { position: absolute; inset: 0; }
.lock .tm { position: absolute; top: 120px; width: 100%; text-align: center; color: #fff; font-size: 84px; font-weight: 300; letter-spacing: -2px; text-shadow: 0 2px 12px rgba(0,0,0,.25); }
.lock .dt { position: absolute; top: 96px; width: 100%; text-align: center; color: #fff; font-size: 19px; font-weight: 600; text-shadow: 0 2px 8px rgba(0,0,0,.25); }
.noti { position: absolute; left: 12px; right: 12px; top: 300px; background: rgba(250,248,245,.92); border-radius: 24px; padding: 14px 16px; display: flex; gap: 12px; box-shadow: 0 6px 20px rgba(0,0,0,.15); }
.noti .ic { width: 38px; height: 38px; border-radius: 10px; background: #F2E6D2; overflow: hidden; flex: none; position: relative; }
.noti .ic img { position: absolute; width: 60px; left: -11px; top: -6px; }
.noti .tt { font-size: 14.5px; font-weight: 800; display: flex; justify-content: space-between; }
.noti .tt span { font-weight: 500; color: #8A7666; font-size: 13px; }
.noti .bd { font-size: 14px; line-height: 1.45; margin-top: 2px; }
'''
hs['CSS'] = CSS


def page(name, phones):
    w = len(phones) * 418 + 30
    (D / f'{name}.html').write_text(f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><div class="row">{"".join(phones)}</div>')
    subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless=new', '--disable-gpu',
                    '--allow-file-access-from-files', '--hide-scrollbars', f'--window-size={w},1010',
                    f'--screenshot={D}/{name}.png', f'file://{D}/{name}.html'], check=True, capture_output=True)


STAGE = stage_room() + '<div class="veil"></div>' + hippo('idle', 370, 130)


def sheet(inner, bottom=0, pad_b=34):
    return f'<div class="scrim"></div><div class="sheet" style="bottom:{bottom}px;padding-bottom:{pad_b}px"><div class="grab"></div>{inner}</div>'


def settings(sub_rows, tag_y=None):
    body = ('<div class="set"><h1>설정</h1>'
            f'<div class="sec">구독</div><div class="grp">{sub_rows}</div>'
            '<div class="sec">단짝</div><div class="grp"><div class="r">이름: 꼬마하마</div></div>'
            '<div class="sec">알림</div><div class="grp"><div class="r">하루 한 번 물어보기 <span class="m">켜짐</span></div><div class="r">시간: 오후 9:00</div></div>'
            '<div class="sec">내 기록</div><div class="grp"><div class="r">텍스트로 내보내기</div><div class="r" style="color:#A13A2A">모든 기록 지우기</div></div>'
            '</div>' + TAB.replace('<span class="on">방</span>', '<span>방</span>').replace('<span>설정</span>', '<span class="on">설정</span>'))
    return body + (new(300, tag_y) if tag_y else '')


# ---------- sheet1: 무료 14일 동안 ----------
welcome = phone('① 가입 직후 (한 번)', '온보딩 \'시작하기\' 다음 방에 처음 들어오면 한 번. 날짜만 알려 주고 카드·결제 이야기는 없음',
    STAGE + TOP.replace('12월 2일 수', '11월 17일 화') + SWITCH + TAB + sheet(
        '<div class="sh">반가워! 가입한 날부터 2주 동안<br>전부 무료로 쓸 수 있어</div>'
        '<div class="sp"><b style="color:#4A3226">12월 1일까지</b> 무료야. 카드 등록은 필요 없고, 그 뒤에 이어 쓸지는 그때 골라도 돼.</div>'
        '<div class="btn">좋아</div>', pad_b=40) + new(300, 520))
set_free = phone('② 설정 · 무료 기간 중', '설정 맨 위에 조용히 날짜만. 홈·입력창에는 아무 표시 없음 (카운트다운 없음)',
    settings('<div class="r">12월 1일까지 무료로 쓰는 중</div><div class="r">구독 둘러보기 <span class="m">›</span></div>', 106))
noti = phone('③ 끝나기 2일 전 알림 (한 번)', '기기 안에서 예약한 알림 1회. 날짜로 말하고 "N일 남음"은 안 씀. 방·기록이 그대로라는 것도 같이',
    '<div class="lock">' + stage_room() + '<div class="veil" style="background:rgba(40,28,20,.35)"></div>'
    '<div class="dt">11월 29일 일요일</div><div class="tm">9:00</div>'
    '<div class="noti"><div class="ic"><img src="../character/export/v1/hippo_idle_poster.png"></div><div style="flex:1">'
    '<div class="tt">꼬마하마 <span>지금</span></div>'
    '<div class="bd">무료 이용은 12월 1일까지야. 그 뒤에도 기록을 이어가려면 구독을 골라 줘. 방이랑 지난 기록은 그대로 있어.</div></div></div></div>')
page('sheet1', [welcome, set_free, noti])

# ---------- sheet2: 14일 지난 뒤 ----------
home = phone('④ 14일 뒤 · 앱을 열면', '평소 화면 그대로. 막는 창 없음. 방·텃밭·마당·유리병·꾸미기(가진 씨앗) 다 됨',
    STAGE + TOP + SWITCH + PEEK.replace('오늘의 쪽지 3', '지난 쪽지').replace('방금 침대 정리했다', '어제 · 물 한 잔 마셨다') + INPUT + TAB)


def paywall(year):
    pl = ('<div class="plans">'
          f'<div class="plan{"" if year else " on"}"><i class="rd"></i><div class="nm">월간</div><div class="pr">3,000원</div><div class="pe">매달</div></div>'
          f'<div class="plan{" on" if year else ""}"><i class="rd"></i><div class="nm">연간</div><div class="pr">24,000원</div><div class="pe">1년 · 월 2,000원꼴</div></div></div>')
    btn = '연 24,000원으로 구독하기' if year else '월 3,000원으로 구독하기'
    renew = '매년 같은 날 자동 갱신' if year else '매달 같은 날 자동 갱신'
    return (STAGE + TOP + SWITCH + TAB + sheet(
        '<div class="sh">기록을 이어가려면 구독이 필요해</div>'
        '<div class="keep">구독하지 않아도 그대로야 · <b>지난 기록 보기·내보내기</b> · <b>방·단짝·텃밭·마당</b> · <b>가진 씨앗과 소품</b></div>'
        + pl + f'<div class="btn">{btn}</div>'
        f'<div class="fine">{renew} · 해지는 iPhone 설정 › Apple 계정 › 구독<br>결제 후 이미 시작된 기간은 청약철회가 제한돼요</div>'
        '<div class="links"><u>구매 복원</u>·<u>이용약관</u>·<u>개인정보처리방침</u></div>'
        '<div class="btn2" style="margin-top:4px">나중에</div>', pad_b=26))


pw_m = phone('⑤ 입력창을 누르면 → 구독 시트', '월·연 같은 크기로 나란히, 배지 없음, 처음 선택은 월. 위에 "안 해도 그대로인 것"부터 보여 줌',
             paywall(False) + new(300, 300))
pw_y = phone('⑥ 연간을 고르면', '버튼·갱신 문구만 바뀜. 연간 쪽엔 "월 2,000원꼴"만 (할인율·BEST 강조 없음)', paywall(True))
set_sub = phone('⑦ 구독한 뒤 · 설정', '구독 상태와 다음 결제일. 해지·변경은 Apple 구독 화면으로 연결',
    settings('<div class="r">월간 구독 중 <span class="m">3,000원</span></div><div class="r">다음 결제 <span class="m">1월 2일</span></div><div class="r">구독 관리 <span class="m">›</span></div>'))
page('sheet2', [home, pw_m, pw_y, set_sub])
print('ok')
