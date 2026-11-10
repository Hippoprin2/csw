# A (current waddle, 126/54 px/s) vs B (bigger faster steps, 242/104 px/s) walking the same loop on the yard
import os, glob, math, subprocess
from PIL import Image, ImageDraw, ImageFont
H = os.path.expanduser("~/projects/csw"); T = os.path.expanduser("~/.hermes/cache/scratch/walkB")
Y = H + "/design/world/export/v1/yard"; R = H + "/design/character/3d/rig"
bg = Image.new("RGBA", (1080, 2160)); bg.paste(Image.open(Y + "/bg_0_0.webp").convert("RGBA"), (0, 0)); bg.paste(Image.open(Y + "/bg_1_0.webp").convert("RGBA"), (0, 1080))
bg = bg.crop((0, 760, 1080, 1560))
def load(d): return [Image.open(f).convert("RGBA").resize((435, 580), Image.LANCZOS) for f in sorted(glob.glob(d + "/f_*.png"))]
clips = {"A": {k: load(f"{R}/walk_{k}25_frames") for k in ("side", "front", "back")},
         "B": {k: load(f"{T}/walk_{k}_f") for k in ("side", "front", "back")}}
SPEED = {"A": 126, "B": 242}
DF = 0.426
x0, x1, y0, y1 = 200, 880, 1300, 1460          # canvas coords (strip starts at y 1150)
legs = [((x0, y0), (x1, y0), "side", False), ((x1, y0), (x1, y1), "front", False), ((x1, y1), (x0, y1), "side", True), ((x0, y1), (x0, y0), "back", False)]
def ground(a, b): return math.hypot(b[0] - a[0], (b[1] - a[1]) / DF)
def pose(k, t):
    tot = sum(ground(a, b) for a, b, *_ in legs); d = (t * SPEED[k]) % tot
    for a, b, c, m in legs:
        g = ground(a, b)
        if d <= g:
            u = d / g; return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, c, m)
        d -= g
font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 38)
small = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 28)
LABEL = {"A": ("A  지금 걸음 (아장아장)", "가로 126px/s · 초당 3걸음 · 한 바퀴 약 17초"),
         "B": ("B  큰 걸음 (빠르게)", "가로 242px/s · 초당 4걸음 · 한 바퀴 약 9초")}
DUR, FPS = 18, 24
os.makedirs(T + "/cmp", exist_ok=True)
for i in range(DUR * FPS):
    t = i / FPS; panels = []
    for k in ("A", "B"):
        im = bg.copy(); x, y, c, m = pose(k, t)
        fr = clips[k][c][i % 48]
        if m: fr = fr.transpose(Image.FLIP_LEFT_RIGHT)
        im.alpha_composite(fr, (int(x - 217.5), int(y - 760 - 505)))
        dr = ImageDraw.Draw(im); dr.rounded_rectangle((20, 676, 700, 780), 18, fill=(255, 255, 255, 215))
        dr.text((40, 684), LABEL[k][0], font=font, fill=(70, 50, 40)); dr.text((40, 736), LABEL[k][1], font=small, fill=(110, 90, 80))
        panels.append(im)
    out = Image.new("RGB", (1080, 1610), (240, 235, 228)); out.paste(panels[0], (0, 0)); out.paste(panels[1], (0, 810))
    out.save(f"{T}/cmp/{i:04d}.jpg", quality=88)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", f"{T}/cmp/%04d.jpg", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21",
                H + "/design/character/3d/share/hippo_walk25_speed_AB.mp4"], check=True)
print("ok")
