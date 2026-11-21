"""csw-prototype 주소는 2026-11-21부터 '화면 보드'. 예전 프로토타입(design/prototype.html)은 보드의 /prototype.html 로 같이 올라감.
이 파일은 옛 명령 호환용: python3 scripts/deploy_prototype.py == python3 scripts/board.py --deploy"""
import pathlib, subprocess, sys

sys.exit(subprocess.call([sys.executable, str(pathlib.Path(__file__).with_name('board.py')), '--deploy']))
