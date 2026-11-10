# Preview: the yard item clips placed on the real yard export (bg tiles + item sprites) at manifest yard_actions stands.
# Usage: ~/.venvs/csw/bin/python scripts/preview_yard_actions.py out.mp4
import glob, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
H = os.path.expanduser("~/projects/csw")
W = json.load(open(f"{H}/design/world/export/v1/manifest.json"))["spaces"]["yard"]
C = json.load(open(f"{H}/design/character/export/v1/manifest.json"))["yard_actions"]
WD = f"{H}/design/world/export/v1/"
RIG = f"{H}/design/character/3d/rig"
OUT = sys.argv[1]
TMP = os.path.expanduser("~/.hermes/cache/scratch/yard_prev_frames"); os.makedirs(TMP, exist_ok=True)
canvas = Image.new("RGBA", tuple(W["canvas"]))
for t in W["tiles"]:
    canvas.paste(Image.open(WD + t["file"]).convert("RGBA"), (t["x"], t["y"]))
_im = {}
def img(f, size=None):
    k = (f, size)
    if k not in _im:
        im = Image.open(f).convert("RGBA")
        _im[k] = im.resize(size, Image.LANCZOS) if size else im
    return _im[k]
items = [it for it in W["items"] if it["id"] in ("bench", "hammock", "flower_bed", "picnic_mat")] + W["bed_flowers"]
tree = W["tree"][3]
def sprite(c, it): c.alpha_composite(img(WD + it["file"], (it["w"], it["h"])), (round(it["x"]), round(it["y"])))
def frames(clip): return sorted(glob.glob(f"{RIG}/{clip}25_frames/f_*.png"))
IDLE = frames("idle")
PW, PH, FX, FY = 435, 580, 303 * 0.725, 697 * 0.725
N = 210
def seq(parts, loops=1, start_idle=0):
    out = [IDLE[i % len(IDLE)] for i in range(start_idle)]
    for p in parts:
        fs = frames(p); out += fs * (loops if p.endswith("_loop") else 1)
    i = 0
    while len(out) < N: out.append(IDLE[i % len(IDLE)]); i += 1
    return out[:N]
A = C
scenes = [
    ("벤치 앉기", A["sit_bench"]["stand"], seq(A["sit_bench"]["parts"], 1, 8), None),
    ("매트 앉아 먹기", A["sit_eat"]["stand"], seq(["sit_eat_in", "sit_eat_strawberry", "sit_eat_loop", "sit_eat_out"], 1, 8)[:N], None),
    ("해먹 눕기", A["lie"]["stand"], seq(A["lie"]["parts"], 1, 6), None),
    ("물장구", A["splash"]["stand"], seq(A["splash"]["parts"], 2, 8), "splash"),
    ("화단 냄새 맡기", A["sniff"]["stand"], seq(["sniff", "sniff"], 1, 12), None),
    ("열매 보여주기", A["show_fruit"]["stand"], seq(["show_fruit"], 1, 30), None),
]
# splash: x/y lerp enter->stand during splash_in f4-15 and stand->enter during splash_out f8-19
def splash_pos(fs, k, stand, enter):
    f = fs[k]; name = os.path.basename(os.path.dirname(f)); n = int(f[-8:-4])
    lerp = lambda a, b, t: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    first_in = next((i for i, g in enumerate(fs) if "splash_in" in g), None)
    if first_in is not None and k < first_in: return enter
    if name.startswith("splash_in"): return lerp(enter, stand, min(1, max(0, (n - 4) / 11)))
    if name.startswith("splash_out"): return lerp(stand, enter, min(1, max(0, (n - 8) / 11)))
    if name.startswith("idle"): return enter
    return stand
font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 30)
CROP = 640
for k in range(N):
    sheet = Image.new("RGB", (3 * 480, 2 * 480))
    for si, (title, stand, fs, kind) in enumerate(scenes):
        pos = splash_pos(fs, k, stand, A["splash"]["enter"]) if kind else stand
        cx, cy = stand[0] + (-60 if kind else 0), stand[1] - 170
        box = (round(cx - CROP / 2), round(cy - CROP / 2), round(cx + CROP / 2), round(cy + CROP / 2))
        c = canvas.copy()
        front = []
        for it in sorted(items, key=lambda i: i["sort_y"]):
            if it["id"] == "flower_bed" or it["id"].startswith("bed_"): front.append(it); continue   # pet stands behind the bed
            sprite(c, it)
        sprite(c, tree)
        for fx, fy in tree["fruits"]:
            c.alpha_composite(img(WD + W["fruit"]["file"], (80, 80)), (round(fx - 40), round(fy - 40)))
        c.alpha_composite(img(fs[k], (PW, PH)), (round(pos[0] - FX), round(pos[1] - FY)))
        for it in front: sprite(c, it)
        p = c.crop(box).convert("RGB").resize((480, 480), Image.LANCZOS)
        d = ImageDraw.Draw(p); d.rectangle((0, 0, 480, 44), fill=(255, 255, 255)); d.text((12, 5), title, font=font, fill=(40, 40, 40))
        sheet.paste(p, ((si % 3) * 480, (si // 3) * 480))
    sheet.save(f"{TMP}/f_{k:04d}.png")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", f"{TMP}/f_%04d.png", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "20", OUT], check=True)
print(OUT)
