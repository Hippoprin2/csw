# 방귀 방방(tap_fart_hop)에 '뿡!' 글자를 2D로 얹는다 (대표 요청 2026-11-14). 렌더 프레임은 그대로 두고 언어별 폴더를 만든다.
# Usage: ~/.venvs/csw/bin/python scripts/composite_fart_text.py [ko|ja]
#   in : design/character/3d/rig/fart_hop_frames (600x1100, feet 303,1013)
#   out: design/character/3d/rig/fart_hop_<lang>_frames  -> export_app_assets.py CLIPS
# Font: Jua (OFL, design/fonts) — baked into pixels, so no app font/notice needed.
import glob, math, os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.expanduser("~/projects/csw")
LANG = sys.argv[1] if len(sys.argv) > 1 else "ko"
WORDS = {"ko": ("뿡!", "뿡", "뽕"), "ja": ("ぷっ!", "ぷっ", "ぷ")}[LANG]
FONT = f"{ROOT}/design/fonts/Jua-Regular.ttf"          # ja: Jua has no kana -> swap font before using ja
src = sorted(glob.glob(f"{ROOT}/design/character/3d/rig/fart_hop_frames/f_*.png"))
out = f"{ROOT}/design/character/3d/rig/fart_hop_{LANG}_frames"
os.makedirs(out, exist_ok=True)
CORAL, CREAM = (237, 92, 97, 255), (252, 247, 237, 255)
# (start frame = puff launch in anim_actions.fart_hop, word, centre x,y in clip px, size, tilt deg)
EVENTS = [(10, WORDS[0], 118, 870, 118, -12), (31, WORDS[1], 492, 905, 88, 10), (50, WORDS[2], 128, 930, 70, -8)]
LIFE = 16

def sticker(word, size):
    f = ImageFont.truetype(FONT, size)
    pad = size // 3
    l, t, r, b = f.getbbox(word, stroke_width=size // 11)
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((pad - l, pad - t), word, font=f, fill=CORAL, stroke_width=size // 11, stroke_fill=CREAM)
    return im

stickers = [sticker(w, s) for _, w, _, _, s, _ in EVENTS]
for i, p in enumerate(src):
    n = i + 1
    fr = Image.open(p).convert("RGBA")
    for (f0, _, cx, cy, _, tilt), st in zip(EVENTS, stickers):
        t = n - f0
        if t < 0 or t > LIFE: continue
        sc = {0: 0.4, 1: 0.95, 2: 1.22, 3: 1.08}.get(t, 1.0)          # pop
        alpha = 1.0 if t < LIFE - 5 else (LIFE - t) / 5                  # fade out
        rise = max(0, t - 3) * 2.2                                       # drifts up a little
        wob = tilt + 4 * math.sin(t * 1.3)
        im = st.resize((max(1, round(st.width * sc)), max(1, round(st.height * sc))), Image.LANCZOS).rotate(wob, expand=True, resample=Image.BICUBIC)
        if alpha < 1:
            a = im.getchannel("A").point(lambda v: round(v * alpha)); im.putalpha(a)
        fr.alpha_composite(im, (round(cx - im.width / 2), round(cy - rise - im.height / 2)))
    fr.save(f"{out}/f_{n:04d}.png")
print("wrote", out, len(src))
