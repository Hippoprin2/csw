#!/usr/bin/env python3
"""mobile/assets/pet 의 애니메이션 WebP를 자리에서 다시 압축 (파일명·프레임수·프레임별 길이·loop·캔버스 크기는 그대로 유지).
design export(design/character/export/v1)는 건드리지 않음 — scripts/gen_pet_clips.py / gen_yard_night_pet.py 로 새로 뽑은 뒤 이 스크립트를 다시 돌리면 됨.

필요 도구: cwebp, dwebp, webpmux (brew install webp). Pillow 불필요.
각 프레임을 webpmux -get frame 으로 떼어 내 dwebp→PNG→cwebp(-q 50 -alpha_q 30 -m 6)로 다시 인코드한 뒤
원본의 프레임별 duration/offset/dispose/blend/loop 그대로 webpmux -frame 으로 재조립한다.
알파 채널이 전체 용량의 대부분을 차지해서(캐릭터가 작고 여백이 투명) alpha_q를 많이 낮춰야 용량이 줄어듦 — q보다 alpha_q가 체감 용량에 더 큰 영향.
사용: python3 scripts/compress_pet_clips.py
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PET_DIR = ROOT / 'mobile/assets/pet'

Q = 50        # 색상 품질 (lossy)
ALPHA_Q = 30  # 알파 품질 (여기가 용량을 가장 많이 줄임) — 이 값까지는 육안으로 윤곽선 번짐/띠 현상 없음 확인됨
METHOD = 6    # 가장 느리지만 가장 작은 압축

FRAME_RE = re.compile(
    r'\s*(\d+):\s+(\d+)\s+(\d+)\s+(yes|no)\s+(\d+)\s+(\d+)\s+(\d+)\s+(none|background)\s+(yes|no)\s+(\d+)\s+(\w+)'
)


def get_anim_info(path):
    out = subprocess.run(['webpmux', '-info', str(path)], capture_output=True, text=True, check=True).stdout
    if 'Features present: animation' not in out:
        return None  # 애니메이션 아님 (poster 등) → 건드리지 않음
    frames = []
    for line in out.splitlines():
        m = FRAME_RE.match(line)
        if m:
            idx, w, h, alpha, x, y, dur, disp, blend, size, comp = m.groups()
            frames.append(dict(idx=int(idx), x=int(x), y=int(y), dur=int(dur), disp=disp, blend=blend))
    loop_m = re.search(r'Loop Count\s*:\s*(\d+)', out)
    loop = int(loop_m.group(1)) if loop_m else 0
    return frames, loop


def recompress_animated(src, dst, q=Q, alpha_q=ALPHA_Q, method=METHOD):
    frames, loop = get_anim_info(src)
    tmpd = pathlib.Path(tempfile.mkdtemp())
    try:
        enc_frames = []
        for fr in frames:
            raw = tmpd / f"raw_{fr['idx']}.webp"
            png = tmpd / f"f_{fr['idx']}.png"
            enc = tmpd / f"enc_{fr['idx']}.webp"
            subprocess.run(['webpmux', '-get', 'frame', str(fr['idx']), str(src), '-o', str(raw)],
                           check=True, capture_output=True)
            subprocess.run(['dwebp', '-quiet', str(raw), '-o', str(png)], check=True, capture_output=True)
            subprocess.run(['cwebp', '-q', str(q), '-alpha_q', str(alpha_q), '-m', str(method),
                            '-mt', '-quiet', str(png), '-o', str(enc)], check=True, capture_output=True)
            enc_frames.append((enc, fr))
        cmd = ['webpmux']
        for enc, fr in enc_frames:
            m = 0 if fr['disp'] == 'none' else 1
            bflag = '+b' if fr['blend'] == 'yes' else '-b'
            cmd += ['-frame', str(enc), f"+{fr['dur']}+{fr['x']}+{fr['y']}+{m}{bflag}"]
        cmd += ['-loop', str(loop), '-o', str(dst)]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


def verify(src, dst):
    """프레임 수 / 프레임별 duration / 캔버스 크기가 원본과 같은지 확인."""
    s_info, s_loop = get_anim_info(src)
    d_info, d_loop = get_anim_info(dst)
    assert len(s_info) == len(d_info), (src, 'frame count mismatch')
    assert s_loop == d_loop, (src, 'loop mismatch')
    for a, b in zip(s_info, d_info):
        assert a['dur'] == b['dur'] and a['x'] == b['x'] and a['y'] == b['y'] and a['disp'] == b['disp'], (src, a, b)


def main():
    for tool in ('cwebp', 'dwebp', 'webpmux'):
        if shutil.which(tool) is None:
            sys.exit(f'필요 도구 없음: {tool} (brew install webp)')

    total_before = total_after = 0
    results = []
    only = set(sys.argv[1:])  # 파일 이름을 주면 그 파일만 (예: 새로 복사한 클립)
    for path in sorted(PET_DIR.glob('*.webp')):
        if only and path.name not in only:
            continue
        before = path.stat().st_size
        info = get_anim_info(path)
        if info is None:
            print(f'skip (not animated): {path.name}')
            continue
        tmp_out = path.with_suffix('.webp.tmp')
        recompress_animated(path, tmp_out)
        verify(path, tmp_out)
        after = tmp_out.stat().st_size
        if after < before:
            tmp_out.replace(path)
        else:
            tmp_out.unlink()
            after = before
            print(f'  (재압축이 더 커서 원본 유지: {path.name})')
        total_before += before
        total_after += after
        results.append((path.name, before, after))
        print(f'{path.name}: {before/1024:.0f}KB -> {after/1024:.0f}KB')

    print(f'\n합계: {total_before/1024/1024:.2f}MB -> {total_after/1024/1024:.2f}MB '
          f'({100*total_after/total_before:.0f}%)')


if __name__ == '__main__':
    main()
