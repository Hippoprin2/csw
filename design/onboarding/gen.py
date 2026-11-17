#!/usr/bin/env python3
"""첫 실행 순서 변경 시안 (O1-A 첫 기록 축하 직후 가입, O2-B 바로 필수, O3 가입부터 14일).
의견·시안 단계 — 앱 코드 안 바꿈. python3 gen.py → sheet1~2.html/png (home_stage/gen.py 재사용)"""
import pathlib, subprocess

D = pathlib.Path(__file__).resolve().parent
src = (D.parent / 'home_stage/gen.py').read_text().split('# ---------- sheet1')[0]
hs = {'__file__': str(D.parent / 'home_stage/gen.py')}
exec(src, hs)
stage_room, hippo, phone, new = hs['stage_room'], hs['hippo'], hs['phone'], hs['new']
TOP, SWITCH, TAB, INPUT, PEEK = hs['TOP'], hs['SWITCH'], hs['TAB'], hs['INPUT'], hs['PEEK']
TOP = TOP.replace('11월 16일 월', '11월 17일 화')

CSS = hs['CSS'] + '''
.sh { font-size: 20px; font-weight: 800; line-height: 1.4; margin: 4px 2px 6px; }
.sp { font-size: 14px; color: #6E5848; line-height: 1.55; margin: 0 2px 14px; }
.btn { height: 52px; border-radius: 999px; background: #2F7D6B; color: #fff; font-weight: 800; font-size: 16px; display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }
.soc { height: 52px; border-radius: 999px; font-weight: 700; font-size: 15px; display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }
.btn2 { height: 44px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: #6E5848; font-weight: 700; }
.fine { font-size: 11.5px; color: #8A7666; line-height: 1.55; margin: 6px 4px 0; text-align: center; }
.set { position: absolute; inset: 0; padding: 62px 20px 0; background: #fff; }
.set h1 { font-size: 26px; font-weight: 800; margin: 0 2px 14px; }
.sec { font-size: 13px; color: #6E5848; font-weight: 700; margin: 16px 6px 6px; }
.grp { background: #F7F6F3; border-radius: 22px; overflow: hidden; }
.grp .r { padding: 15px 18px; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
.grp .r + .r { border-top: 1px solid #ECE9E3; }
.grp .r .m { color: #6E5848; font-size: 13.5px; }
.old { position: absolute; inset: 0; width: 390px; }
.strike { position: absolute; left: 10px; right: 10px; border: 3px dashed #C0503A; border-radius: 30px; z-index: 9; }
.lab { position: absolute; background: #C0503A; color: #fff; font-size: 12px; font-weight: 800; padding: 5px 11px; border-radius: 999px; z-index: 9; }
'''
hs['CSS'] = CSS
STAGE = stage_room() + '<div class="veil"></div>'


def page(name, phones):
    w = len(phones) * 418 + 30
    (D / f'{name}.html').write_text(f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><div class="row">{"".join(phones)}</div>')
    subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless=new', '--disable-gpu',
                    '--allow-file-access-from-files', '--hide-scrollbars', f'--window-size={w},1010',
                    f'--screenshot={D}/{name}.png', f'file://{D}/{name}.html'], check=True, capture_output=True)


def sheet(inner, pad_b=34):
    return f'<div class="scrim"></div><div class="sheet" style="padding-bottom:{pad_b}px"><div class="grab"></div>{inner}</div>'


# ---------- sheet1: 가입 전 (인사 · 이름 · 동의) ----------
now = phone('지금 · 첫 화면 = 가입', '앱을 열자마자 로그인 버튼 4개. 앱이 뭘 해 주는지 보기 전에 막힘',
            '<img class="old" src="../screens/01_auth.png">'
            '<div class="strike" style="top:590px;height:236px"></div><div class="lab" style="left:24px;top:560px">여기가 뒤로 감</div>')
hello = phone('① 인사 (바뀜)', '로그인 버튼 대신 "시작하기" 하나. 하마가 무슨 앱인지 한 줄로 말함',
              STAGE + hippo('people', 370, 150)
              + '<div class="bubble" style="left:50%;transform:translateX(-50%);top:120px;text-align:center;white-space:normal;width:270px">안녕! 오늘 해낸 걸 알려주면<br>내가 축하해 줄게. 아주 작은 것도 좋아.</div>'
              + '<div style="position:absolute;left:20px;right:20px;bottom:44px;z-index:6"><div class="btn">시작하기</div>'
                '<div class="btn2">이미 계정이 있어요</div></div>' + new(296, 664))
name = phone('② 이름 짓기 (그대로)', '지금 화면 그대로. 아직 계정 없음 — 이름은 폰에만 잠깐 두고 가입 때 저장',
             '<img class="old" src="../screens/03_onboarding_name.png">')
consent = phone('③ 동의 (그대로)', '첫 기록이 AI 분류로 가기 전에 받아야 해서 기록보다 앞에 둠. 출시 전 민감정보 항목 추가는 따로 진행',
                '<img class="old" src="../screens/04_onboarding_notice.png">')
page('sheet1', [now, hello, name, consent])

# ---------- sheet2: 첫 기록 → 축하 → 가입(필수) → 방 ----------
first = phone('④ 첫 기록', '홈과 같은 무대지만 탭·씨앗·공간 전환은 아직 숨김. 예시 칩으로 바로 적기',
              STAGE + hippo('idle', 340, 120)
              + '<div class="bubble" style="left:50%;transform:translateX(-50%);top:96px">오늘 해낸 거 하나만 알려줘</div>'
              + '<div style="position:absolute;left:16px;right:16px;bottom:96px;z-index:6" class="chips">'
                '<span class="chip" style="background:#fff">물 한 잔 마셨다</span><span class="chip" style="background:#fff">이불 갰다</span><span class="chip" style="background:#fff">10분 걸었다</span></div>'
              + INPUT.replace('bottom: 100px', '').replace('class="inp"', 'class="inp" style="bottom:36px"') + new(300, 690))
cel = phone('⑤ 축하 (홈과 같은 연출)', '하마 동작 + 적은 문장 카드 + 씨앗. 이 순간이 앱의 가치 — 이걸 보고 나서 가입',
            stage_room() + '<div class="veil" style="background:rgba(255,255,255,.55)"></div>' + hippo('tidy', 430, 115)
            + '<div class="bubble" style="left:96px;top:120px">이불 갠 거 최고야!</div>'
            + '<div class="rec" style="top:700px"><i class="dot" style="background:#7FB3A0"></i>이불 갰다</div>'
            + '<div class="float" style="left:276px;top:654px">+3 씨앗</div>')
signup = phone('⑥ 저장하기 = 가입 (필수)', '축하가 끝나면 바로 올라옴. "나중에" 없음(O2-B). 겁주는 말 없이 "남게 해 줄게"로',
               stage_room() + '<div class="veil" style="background:rgba(255,255,255,.55)"></div>' + hippo('cheer', 360, 40)
               + sheet('<div class="sh">첫 기록, 잘 간직할게</div>'
                       '<div class="sp">계정을 연결하면 폰을 바꿔도 기록이랑 꼬마하마가 그대로 남아.</div>'
                       '<div class="soc" style="background:#111;color:#fff"> Apple로 계속하기</div>'
                       '<div class="soc" style="background:#FEE500;color:#191919">카카오로 계속하기</div>'
                       '<div class="soc" style="background:#F7F6F3">Google로 계속하기</div>'
                       '<div class="btn2">이메일로 계속하기</div>'
                       '<div class="fine">가입한 날부터 2주 무료 · 카드 등록 없음</div>', pad_b=30) + new(300, 486))
room = phone('⑦ 방 도착', '선물 씨앗 6개 + 방금 기록 1개가 그대로. 이어서 "12월 1일까지 무료" 안내(유료화 시안 ①)',
             STAGE + hippo('idle', 370, 130) + TOP + SWITCH
             + '<div class="bubble" style="left:50%;transform:translateX(-50%);top:150px">선물이야! 씨앗 6개</div>'
             + PEEK.replace('오늘의 쪽지 3', '오늘의 쪽지 1').replace('방금 침대 정리했다', '이불 갰다') + INPUT + TAB + new(300, 200))
page('sheet2', [first, cel, signup, room])

# ---------- sheet3: 가입 뒤 구독 안내 흐름 O6-A (추천) — 날짜는 가입 시트에서, 방에선 알림만 ----------
SIGN = ('<div class="sh">첫 기록, 잘 간직할게</div>'
        '<div class="sp">계정을 연결하면 폰을 바꿔도 기록이랑 꼬마하마가 그대로 남아.</div>'
        '<div class="soc" style="background:#111;color:#fff"> Apple로 계속하기</div>'
        '<div class="soc" style="background:#FEE500;color:#191919">카카오로 계속하기</div>'
        '<div class="soc" style="background:#F7F6F3">Google로 계속하기</div>'
        '<div class="btn2">이메일로 계속하기</div>')
CEL_BG = stage_room() + '<div class="veil" style="background:rgba(255,255,255,.55)"></div>' + hippo('cheer', 360, 40)
TIMES = '<div class="chips"><span class="chip">20:00</span><span class="chip on">21:00</span><span class="chip">22:00</span><span class="chip">23:00</span></div>'
ROOM_HOME = STAGE + hippo('idle', 370, 130) + TOP + SWITCH + PEEK.replace('오늘의 쪽지 3', '오늘의 쪽지 1').replace('방금 침대 정리했다', '이불 갰다') + INPUT + TAB


def settings_free(tag=True):
    tb = TAB.replace('<span class="on">방</span>', '<span>방</span>').replace('<span>설정</span>', '<span class="on">설정</span>')
    return ('<div class="set"><h1>설정</h1><div class="sec">구독</div><div class="grp">'
            '<div class="r">12월 1일까지 무료로 쓰는 중</div><div class="r">구독 둘러보기 <span class="m">›</span></div></div>'
            '<div class="sec">단짝</div><div class="grp"><div class="r">이름: 꼬마하마</div></div>'
            '<div class="sec">알림</div><div class="grp"><div class="r">하루 한 번 물어보기 <span class="m">켜짐</span></div><div class="r">시간: 오후 9:00</div></div>'
            '</div>' + tb)


a6 = phone('O6-A ⑥ · 무료 날짜는 가입 시트에서 ← 추천', '가입 버튼 바로 아래에 끝나는 날짜·가격. 결정하기 전에 알게 됨. 가입 뒤 무료 안내 시트는 따로 안 띄움',
           CEL_BG + sheet(SIGN + '<div class="fine"><b style="color:#4A3226">12월 1일까지 무료</b> · 카드 등록 없음<br>그 뒤엔 월 3,000원 또는 연 24,000원 · 그때 골라도 돼</div>', pad_b=26) + new(300, 470))
a7 = phone('⑦ 방 도착 · 선물', '시트 없이 말풍선 + 씨앗이 칩으로 날아감(+6). 방금 기록도 쪽지 한 줄로 보임',
           ROOM_HOME.replace('<i class="lf"></i>9', '<i class="lf"></i>9')
           + '<div class="bubble" style="left:50%;transform:translateX(-50%);top:150px">선물이야! 씨앗 6개</div>'
           + '<div class="float" style="left:300px;top:96px">+6</div>')
a8 = phone('⑧ 알림 물어보기 (시트 1장)', '가입 뒤 뜨는 시트는 이것 하나. 매일 알림 + 무료 끝나기 전 알림을 한 번에 물어봄',
           ROOM_HOME + sheet('<div class="sh">내일 이 시간쯤 한 번만 물어봐도 될까?</div>'
                             '<div class="sp">하루 한 번, 오늘 해낸 걸 물어볼게. 이미 적은 날엔 안 보내.<br>무료 이용이 끝나기 이틀 전에도 날짜를 알려줄게.</div>'
                             + TIMES + '<div class="btn">좋아</div><div class="btn2">괜찮아</div>', pad_b=36) + new(300, 486))
a9 = phone('⑨ 날짜는 설정에서 언제든', '홈·입력창엔 아무 표시 없음(카운트다운 없음). 유료화 시안 ②와 같음',
           settings_free())
page('sheet3', [a6, a7, a8, a9])

# ---------- sheet4: 다른 방법 ----------
b1 = phone('O6-B · 한 장에 다 넣기', '무료 날짜 + 선물 + 알림을 시트 하나에. 끊김은 1번이지만 글이 많고 버튼이 두 뜻을 겸함',
           ROOM_HOME + sheet('<div class="sh">반가워! 12월 1일까지<br>전부 무료로 쓸 수 있어</div>'
                             '<div class="sp">카드 등록은 필요 없어. 선물로 씨앗 6개도 넣어 뒀어.<br>하루 한 번, 오늘 해낸 걸 물어봐도 될까?</div>'
                             + TIMES + '<div class="btn">알림 받고 시작하기</div><div class="btn2">알림 없이 시작하기</div>', pad_b=36))
c1 = phone('O6-C ①/② · 지금 확정안 그대로', '방 도착 → 무료 안내 시트 [좋아] (유료화 시안 ① 그대로)',
           ROOM_HOME + sheet('<div class="sh">반가워! 가입한 날부터 2주 동안<br>전부 무료로 쓸 수 있어</div>'
                             '<div class="sp"><b style="color:#4A3226">12월 1일까지</b> 무료야. 카드 등록은 필요 없고, 그 뒤에 이어 쓸지는 그때 골라도 돼.</div>'
                             '<div class="btn">좋아</div>', pad_b=40))
c2 = phone('O6-C ②/② · 이어서 알림 시트', '닫자마자 알림 시트가 또. 가입 → 시트 → 시트, 3번 연속 끊김',
           ROOM_HOME + sheet('<div class="sh">내일 이 시간쯤 한 번만 물어봐도 될까?</div>'
                             '<div class="sp">하루 한 번, 오늘 해낸 걸 물어볼게. 이미 적은 날엔 안 보내.</div>'
                             + TIMES + '<div class="btn">좋아</div><div class="btn2">괜찮아</div>', pad_b=36))
page('sheet4', [b1, c1, c2])

# ---------- sheet5: 무료 기간 중 미리 구독 (O7-A 대표 결정) ----------
MCSS = (D.parent / 'monetization/gen.py').read_text().split("CSS = hs['CSS'] + \'\'\'")[1].split("\'\'\'")[0]
CSS5 = CSS + MCSS + '''
.early { background: #FFF6E6; border-radius: 22px; padding: 12px 16px; font-size: 13.5px; line-height: 1.6; margin-bottom: 14px; }
.early b { color: #4A3226; }
.hl { box-shadow: inset 0 0 0 3px #2F7D6B; }
'''
hs['CSS'] = CSS5


def page5(name, phones):
    w = len(phones) * 418 + 30
    (D / f'{name}.html').write_text(f'<!doctype html><meta charset="utf-8"><style>{CSS5}</style><div class="row">{"".join(phones)}</div>')
    subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--headless=new', '--disable-gpu',
                    '--allow-file-access-from-files', '--hide-scrollbars', f'--window-size={w},1010',
                    f'--screenshot={D}/{name}.png', f'file://{D}/{name}.html'], check=True, capture_output=True)


TB_SET = TAB.replace('<span class="on">방</span>', '<span>방</span>').replace('<span>설정</span>', '<span class="on">설정</span>')


def settings5(rows):
    return ('<div class="set"><h1>설정</h1><div class="sec">구독</div><div class="grp">' + rows + '</div>'
            '<div class="sec">단짝</div><div class="grp"><div class="r">이름: 꼬마하마</div></div>'
            '<div class="sec">알림</div><div class="grp"><div class="r">하루 한 번 물어보기 <span class="m">켜짐</span></div><div class="r">시간: 오후 9:00</div></div>'
            '</div>' + TB_SET)


e1 = phone('① 무료 기간 · 설정', '구독하고 싶으면 설정 맨 위 "구독 둘러보기". 홈·입력창엔 결제 버튼 없음 (지금 확정안 그대로)',
           settings5('<div class="r">12월 1일까지 무료로 쓰는 중</div><div class="r hl">구독 둘러보기 <span class="m">›</span></div>'))
early_sheet = ('<div class="sh">미리 구독할 수도 있어</div>'
               '<div class="early">지금 구독하면 <b>오늘(11월 17일)부터 결제</b>돼.<br><b>12월 1일까지는</b> 구독 안 해도 무료라, 그때 골라도 괜찮아.</div>'
               '<div class="plans"><div class="plan on"><i class="rd"></i><div class="nm">월간</div><div class="pr">3,000원</div><div class="pe">매달</div></div>'
               '<div class="plan"><i class="rd"></i><div class="nm">연간</div><div class="pr">24,000원</div><div class="pe">1년 · 월 2,000원꼴</div></div></div>'
               '<div class="btn">월 3,000원으로 구독하기</div>'
               '<div class="fine">매달 같은 날 자동 갱신 · 해지는 iPhone 설정 › Apple 계정 › 구독<br>결제 후 지나간 기간은 청약철회가 제한돼요. 결제 후 7일 안에는 남은 기간을 철회할 수 있어요</div>'
               '<div class="links"><u>구매 복원</u>·<u>이용약관</u>·<u>개인정보처리방침</u></div>'
               '<div class="btn2" style="margin-top:4px">나중에</div>')
e2 = phone('② 무료 기간 중 구독 시트', '14일 뒤 시트와 같은 카드·버튼·안내. 위 "안 해도 그대로" 대신 "오늘부터 결제" 한 줄만 다름',
           settings5('<div class="r">12월 1일까지 무료로 쓰는 중</div><div class="r">구독 둘러보기 <span class="m">›</span></div>')
           + sheet(early_sheet, pad_b=26) + new(300, 412))
e3 = phone('③ 구독한 뒤 · 설정', '무료 문구는 사라지고 구독 상태로. 다음 결제는 구독한 날 기준 (12월 17일)',
           settings5('<div class="r">월간 구독 중 <span class="m">3,000원</span></div><div class="r">다음 결제 <span class="m">12월 17일</span></div><div class="r">구독 관리 <span class="m">›</span></div>'))
page5('sheet5', [e1, e2, e3])
print('ok')
