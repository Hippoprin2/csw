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
            + '<div class="float" style="left:276px;top:654px">+1 씨앗</div>')
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
             STAGE + hippo('idle', 370, 130) + TOP.replace('<i class="lf"></i>9', '<i class="lf"></i>7') + SWITCH
             + '<div class="bubble" style="left:50%;transform:translateX(-50%);top:150px">선물이야! 씨앗 6개</div>'
             + PEEK.replace('오늘의 쪽지 3', '오늘의 쪽지 1').replace('방금 침대 정리했다', '이불 갰다') + INPUT + TAB + new(300, 200))
page('sheet2', [first, cel, signup, room])
print('ok')
