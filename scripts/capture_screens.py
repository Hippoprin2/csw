#!/usr/bin/env python3
"""앱 전체 화면 캡처: 임시 테스트 계정(기록 9일치) 생성 → 웹 앱을 헤드리스 Chrome으로 돌며 캡처 → 계정 삭제.
사용: (mobile에서 `npx expo start --web --port 8081` 가 떠 있어야 함)
  python3 scripts/capture_screens.py            # → design/screens/*.png
결과는 클로드 디자인 캔버스 'CSW 앱 전체 화면'에 올려서 화면별로 봄 (DEV.md '화면 캡처')
"""
import sys, json, time, datetime, pathlib, subprocess, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, SERVICE, URL

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'design' / 'screens'
APP = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8081'

TEXTS = [('침대 정리했다', 'tidy'), ('30분 산책', 'move'), ('영단어 20개 외움', 'study'), ('아침밥 챙겨 먹음', 'eat'),
         ('일찍 잠들었다', 'care'), ('친구한테 먼저 연락함', 'people'), ('오늘 그냥 버텼다', 'cheer'), ('보고서 마감', 'work'),
         ('설거지 바로 함', 'tidy'), ('스트레칭 10분', 'move'), ('물 2리터 마심', 'eat'), ('엄마랑 통화', 'people')]


def make_user():
    email = f'csw-test-{int(time.time() * 1000)}@example.com'
    req('POST', '/auth/v1/admin/users', {'email': email, 'email_confirm': True}, token=SERVICE, key=SERVICE)
    _, link = req('POST', '/auth/v1/admin/generate_link', {'type': 'magiclink', 'email': email}, token=SERVICE, key=SERVICE)
    otp = link.get('email_otp') or link.get('properties', {}).get('email_otp')
    s, sess = req('POST', '/auth/v1/verify', {'type': 'email', 'email': email, 'token': otp})
    assert s == 200, sess
    sess['expires_at'] = int(time.time()) + sess['expires_in']
    return sess


def seed(uid):
    today = datetime.date.today()
    for d in range(9, 0, -1):  # 기록한 날 9일 → 마당 열림, 유리병에 구슬
        for k in range(2):
            t, c = TEXTS[(d * 2 + k) % len(TEXTS)]
            s, e = req('POST', '/rest/v1/wins', {'user_id': uid, 'text': t, 'category': c, 'jar_no': 1,
                                                 'win_date': str(today - datetime.timedelta(days=d))}, token=SERVICE, key=SERVICE)
            assert s < 300, e


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sess = make_user()
    uid = sess['user']['id']
    try:
        seed(uid)
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump(sess, f)
        ref = URL.split('//')[1].split('.')[0]
        node = subprocess.Popen(['node', str(ROOT / 'scripts' / 'capture_screens.mjs'), f.name, ref, str(OUT), APP],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        for line in node.stdout:  # 잠긴 마당을 찍은 뒤 node가 OPEN_YARD를 보내면 마당을 열어 줌
            if line.strip() == 'OPEN_YARD':
                req('PATCH', f'/rest/v1/profiles?id=eq.{uid}', {'yard_opened_at': 'now()'}, token=SERVICE, key=SERVICE)
                node.stdin.write('ok\n'); node.stdin.flush()
            else:
                print(line, end='')
        pathlib.Path(f.name).unlink(missing_ok=True)
        sys.exit(node.wait())
    finally:
        s, _ = req('DELETE', f'/auth/v1/admin/users/{uid}', token=SERVICE, key=SERVICE)
        print('test user deleted', s)


if __name__ == '__main__':
    main()
