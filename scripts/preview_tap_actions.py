# Room tap-reaction preview: idle -> fart_hop -> idle -> roll -> idle -> roll (mirrored = left) -> idle,
# on the room background at the manifest pet placement. Left = whole room card (phone scale), right = 2x close-up.
# Usage: ~/.venvs/csw/bin/python scripts/preview_tap_actions.py <out.mp4>
import sys, os, glob, json, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.expanduser("~/projects/csw")
FF = "/Users/soniakang/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg"
out = sys.argv[1]
man = json.load(open(f"{ROOT}/design/world/export/v1/manifest.json"))["spaces"]["room"]
vx = man["view"]["start_x"]; pet = man["pet"]
bg = Image.open(f"{ROOT}/design/world/export/v1/room/background.webp").convert("RGBA").crop((vx, 0, vx + 1080, 1080))
RIG = f"{ROOT}/design/character/3d/rig"
fr = lambda n: sorted(glob.glob(f"{RIG}/{n}_frames/f_*.png"))
idle, fart, roll = fr("idle"), fr("fart_hop"), fr("roll")
K = pet["w"] / 600                       # clip px -> room px
cx, cy = pet["center"][0] - vx, pet["center"][1]
font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 30)

seq = []
def add_idle(n): seq.extend((idle[i % len(idle)], False, "") for i in range(n))
add_idle(24); seq += [(f, False, "방귀 뿡 → 방방") for f in fart]
add_idle(16); seq += [(f, False, "데굴 (오른쪽)") for f in roll]
add_idle(16); seq += [(f, True, "데굴 (왼쪽 = 앱이 뒤집기)") for f in roll]
add_idle(20)

tmp = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
cache = {}
for n, (path, mirror, label) in enumerate(seq):
    im = cache.get(path) or Image.open(path).convert("RGBA"); cache[path] = im
    if mirror: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    w, h = round(im.width * K), round(im.height * K)
    # feet anchor: (303, 713) in the 600x800 clip; wide canvases add width on both sides, tall ones add height on top
    fx, fy = cx + (303 - 300) * K, cy + (713 - 400) * K
    ax, ay = (303 + (im.width - 600) / 2) * K, (713 + (im.height - 800)) * K
    if mirror: ax = w - ax
    card = bg.copy()
    card.alpha_composite(im.resize((w, h), Image.LANCZOS), (round(fx - ax), round(fy - ay)))
    left = card.resize((540, 540), Image.LANCZOS)
    zx, zy = cx - 270, cy - 380            # 2x close-up window (540x540 room px -> 540 out... shown at 1:1 then x1)
    right = card.crop((round(zx), round(zy), round(zx + 540), round(zy + 540)))
    frame = Image.new("RGB", (1080, 600), (240, 235, 228))
    frame.paste(left.convert("RGB"), (0, 60)); frame.paste(right.convert("RGB"), (540, 60))
    d = ImageDraw.Draw(frame)
    d.text((16, 14), "방 카드 크기", fill=(74, 50, 38), font=font); d.text((556, 14), "2배 확대  " + label, fill=(74, 50, 38), font=font)
    frame.save(f"{tmp}/{n:04d}.png")
subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", "24", "-i", f"{tmp}/%04d.png", "-c:v", "libx264", "-crf", "22",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
print("wrote", out, len(seq), "frames")
