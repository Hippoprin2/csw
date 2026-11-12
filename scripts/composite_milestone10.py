# Composite a full-screen milestone celebration: underwater background + 2D bubbles around the rendered hippo frames.
# Usage: ~/.venvs/csw/bin/python scripts/composite_milestone10.py <frames_dir (f_####.png + track.json)> <out.mp4> [caption]
import sys, os, json, math, random, subprocess, tempfile, glob
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = "/Users/soniakang/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg"
src, out = sys.argv[1], sys.argv[2]
caption = sys.argv[3] if len(sys.argv) > 3 else "기록 10번, 축하해!"
frames = sorted(glob.glob(os.path.join(src, "f_*.png")))
track = {int(k): v for k, v in json.load(open(os.path.join(src, "track.json"))).items()}
W, H = Image.open(frames[0]).size
k = W / 1080.0
N = len(frames); HOLD = 14; TOTAL = N + HOLD
rnd = random.Random(10)

# ---------------- static background: gradient + seaweed is drawn per frame (sways)
top, bot = (204, 240, 250), (132, 200, 238)
bg = Image.new("RGB", (W, H))
d = ImageDraw.Draw(bg)
for y in range(H):
    t = y / H; d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
bg = bg.convert("RGBA")
# light rays (one layer, swayed by translating)
rays = Image.new("RGBA", (W + int(200 * k), H), (0, 0, 0, 0))
dr = ImageDraw.Draw(rays)
for x0, w0, a in ((0.12, 0.10, 46), (0.38, 0.07, 36), (0.6, 0.12, 40), (0.86, 0.06, 30)):
    x = x0 * W; ww = w0 * W
    dr.polygon([(x, 0), (x + ww, 0), (x + ww * 2.6 - 0.35 * W, H), (x - ww * 0.6 - 0.35 * W, H)], fill=(255, 255, 255, a))
rays = rays.filter(ImageFilter.GaussianBlur(28 * k))
# sandy floor glow at the bottom
floor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(floor).ellipse((-0.3 * W, H * 0.9, 1.3 * W, H * 1.25), fill=(250, 232, 200, 255))
floor = floor.filter(ImageFilter.GaussianBlur(30 * k))

def seaweed(img, f):
    dd = ImageDraw.Draw(img)
    for i, (x, h, col, ph) in enumerate(((0.08, 0.26, (158, 214, 194), 0), (0.16, 0.18, (128, 204, 140), 1.3),
                                         (0.86, 0.3, (158, 214, 194), 2.1), (0.93, 0.2, (128, 204, 140), 0.7))):
        pts_l, pts_r = [], []
        for j in range(21):
            t = j / 20; y = H * (1.02 - h * t)
            sway = math.sin(f * 0.08 + ph + t * 2.5) * 26 * k * t
            wdt = 22 * k * (1 - t * 0.85)
            pts_l.append((x * W + sway - wdt, y)); pts_r.append((x * W + sway + wdt, y))
        dd.polygon(pts_l + pts_r[::-1], fill=col + (255,))

# ---------------- bubble sprite cache
_cache = {}
def bubble(r):
    r = max(3, int(r))
    if r in _cache: return _cache[r]
    S = 4; R = r * S; im = Image.new("RGBA", (2 * R + 8, 2 * R + 8), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    c = R + 4; lw = max(S * 2, int(R * 0.11))
    g.ellipse((c - R, c - R, c + R, c + R), fill=(255, 255, 255, 46), outline=(255, 255, 255, 240), width=lw)
    g.ellipse((c - R * 0.62, c - R * 0.66, c - R * 0.18, c - R * 0.3), fill=(255, 255, 255, 235))
    g.ellipse((c + R * 0.25, c + R * 0.35, c + R * 0.42, c + R * 0.52), fill=(255, 255, 255, 170))
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    _cache[r] = im; return im

def put(img, x, y, r, alpha=1.0):
    b = bubble(r)
    if alpha < 1: b = b.copy(); b.putalpha(b.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(b, (int(x - b.width / 2), int(y - b.height / 2)))

def star(img, x, y, s, col, rot):
    g = ImageDraw.Draw(img); pts = []
    for i in range(8):
        a = rot + i * math.pi / 4; rr = s if i % 2 == 0 else s * 0.32
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    g.polygon(pts, fill=col + (255,))

# ambient bubbles
amb = [dict(x=rnd.uniform(0.04, 0.96) * W, y0=rnd.uniform(0, H * 1.3), v=rnd.uniform(2.0, 4.5) * k,
            r=rnd.uniform(8, 30) * k, ph=rnd.uniform(0, 6.3)) for _ in range(22)]
# mouth bubbles: spawn events
mouth = []
spawn_frames = list(range(22, 40, 3)) + list(range(120, 156, 4))
for f0 in spawn_frames:
    for j in range(2 if f0 < 40 else 1):
        mouth.append(dict(f0=f0 + j, r0=rnd.uniform(16, 28) * k, grow=rnd.uniform(0.15, 0.3) * k, v=rnd.uniform(5, 8) * k,
                          dx=rnd.uniform(-1.5, 1.5) * k, ph=rnd.uniform(0, 6.3), x=None, y=None))
# swirl ring
SW0, SW1 = 40, 108
swirl = [dict(a0=2 * math.pi * i / 18, h=i / 18, r=rnd.uniform(18, 36) * k) for i in range(16)]
# burst on "짠"
BURST = 106
burst = [dict(a=2 * math.pi * i / 22 + rnd.uniform(-0.1, 0.1), v=rnd.uniform(14, 24) * k, r=rnd.uniform(16, 34) * k) for i in range(20)]
sparks = [dict(x=rnd.uniform(0.12, 0.88), y=rnd.uniform(0.18, 0.62), f0=BURST + rnd.randint(0, 30), s=rnd.uniform(18, 34) * k,
               col=rnd.choice([(255, 219, 89), (255, 166, 191), (250, 199, 64), (255, 255, 240)])) for _ in range(14)]

try: font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", int(64 * k), index=6)
except Exception: font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", int(64 * k))

def ease(t): t = max(0, min(1, t)); return t * t * (3 - 2 * t)

tmp = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
for n in range(1, TOTAL + 1):
    fi = min(n, N); tr = track[fi]
    im = bg.copy()
    sway = int((math.sin(n * 0.03) * 60 - 100) * k)
    im.alpha_composite(rays, (sway, 0)); im.alpha_composite(floor)
    seaweed(im, n)
    for b in amb:
        y = (b["y0"] - b["v"] * n) % (H * 1.3) - H * 0.15
        put(im, b["x"] + math.sin(n * 0.07 + b["ph"]) * 10 * k, y, b["r"], 0.8)
    cx, cy = tr["root"][0], tr["root"][1]
    hx, hy = tr["head"][0], tr["head"][1]
    front = []
    if SW0 <= n <= SW1:                                  # bubble whirl around the dancing hippo
        t = (n - SW0) / (SW1 - SW0); fade = min(1, t * 5, (1 - t) * 5)
        for b in swirl:
            a = b["a0"] + t * 4 * math.pi * 1.3
            yy = cy + 160 * k - (b["h"] * 0.8 + t * 0.4) % 1.0 * 620 * k
            xx = cx + math.cos(a) * 360 * k
            yy += math.sin(a) * 60 * k
            if math.sin(a) > 0: front.append((xx, yy, b["r"] * 1.15, fade))   # in front of the hippo
            else: put(im, xx, yy, b["r"], fade)                                  # behind
    im.alpha_composite(Image.open(frames[fi - 1]).convert("RGBA"))
    for xx, yy, r, a in front: put(im, xx, yy, r, a)
    for b in mouth:                                      # bubbles blown from the snout
        if n < b["f0"]: continue
        if b["x"] is None:
            trs = track[min(b["f0"], N)]
            if trs["facing"] < 0.15: b["f0"] = 10 ** 6; continue
            b["x"], b["y"] = trs["snout"][0], trs["snout"][1]
        age = n - b["f0"]
        y = b["y"] - b["v"] * age - 0.04 * age * age * k
        if y < -60: continue
        x = b["x"] + b["dx"] * age + math.sin(age * 0.25 + b["ph"]) * 9 * k
        put(im, x, y, b["r0"] + b["grow"] * age, min(1, age / 3))
    if BURST <= n <= BURST + 30:
        age = n - BURST; fade = 1 - age / 30
        for b in burst:
            dist = 230 * k + b["v"] * (1 - math.exp(-age / 7)) * 7   # start outside the face
            put(im, hx + math.cos(b["a"]) * dist, hy + math.sin(b["a"]) * dist * 0.9 - age * 2 * k, b["r"], fade)
    for s in sparks:
        age = n - s["f0"]
        if 0 <= age <= 14:
            sz = s["s"] * math.sin(math.pi * age / 14)
            star(im, s["x"] * W, s["y"] * H, sz, s["col"], age * 0.12)
    if n >= 116:                                         # caption pill
        t = ease((n - 116) / 8)
        cap = Image.new("RGBA", im.size, (0, 0, 0, 0)); g = ImageDraw.Draw(cap)
        tw = g.textlength(caption, font=font); ph = 120 * k; pw = tw + 110 * k
        x0 = (W - pw) / 2; y0 = H * 0.80 + (1 - t) * 40 * k
        g.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), radius=ph / 2, fill=(252, 247, 237, 245))
        g.text((W / 2, y0 + ph / 2), caption, font=font, fill=(88, 54, 40, 255), anchor="mm")
        cap.putalpha(cap.getchannel("A").point(lambda v: int(v * t)))
        im.alpha_composite(cap)
    im.convert("RGB").save(f"{tmp}/c_{n:04d}.png")
subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", "24", "-i", f"{tmp}/c_%04d.png", "-vf", "format=yuv420p",
                "-c:v", "libx264", "-crf", "24", "-preset", "slow", "-movflags", "+faststart", out], check=True)
print("wrote", out, TOTAL, "frames", round(os.path.getsize(out) / 1e6, 2), "MB")
