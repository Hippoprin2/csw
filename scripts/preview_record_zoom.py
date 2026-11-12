# Room "record -> celebration" zoom preview: A (no zoom) vs C (gentle 1.25x zoom + dim around the pet).
# Usage: ~/.venvs/csw/bin/python scripts/preview_record_zoom.py <action_frames_dir> <out.mp4> [zoom=1.25]
# Draws only the room background + pet clip (no furniture) at the manifest pet placement.
import sys, os, glob, json, subprocess, tempfile, math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.expanduser("~/projects/csw")
FF = "/Users/soniakang/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg"
act_dir, out = sys.argv[1], sys.argv[2]
Z = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
man = json.load(open(f"{ROOT}/design/world/export/v1/manifest.json"))["spaces"]["room"]
vx = man["view"]["start_x"]; pet = man["pet"]
bg = Image.open(f"{ROOT}/design/world/export/v1/room/background.webp").convert("RGBA")
bg = bg.crop((vx, 0, vx + 1080, 1080))
idle = sorted(glob.glob(f"{ROOT}/design/character/3d/rig/idle_frames/f_*.png"))
act = sorted(glob.glob(os.path.join(act_dir, "f_*.png")))
cx, cy = pet["center"][0] - vx, pet["center"][1]
S = 540  # output panel size (~ phone card)
IN, OUT_ = 7, 9  # zoom in/out frames (0.3 s / 0.35 s at 24 fps)

seq = [("idle", i % len(idle)) for i in range(24)] + [("act", i) for i in range(len(act))] + [("idle", i % len(idle)) for i in range(30)]
a0, a1 = 24, 24 + len(act)

def ease(t): return t * t * (3 - 2 * t)

def zoom_at(n):
    if n < a0 or n >= a1 + OUT_: return 0.0
    if n < a0 + IN: return ease((n - a0) / IN)
    if n < a1: return 1.0
    return 1 - ease((n - a1) / OUT_)

vign = Image.new("L", (1080, 1080), 0)
d = ImageDraw.Draw(vign)
for r in range(700, 0, -10):
    v = int(255 * min(1, max(0, (r - 260) / 300)))
    d.ellipse((cx - r, cy - 40 - r, cx + r, cy - 40 + r), fill=v)
vign = vign.filter(ImageFilter.GaussianBlur(30))
font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)

def frame(kind, i, z, label):
    im = bg.copy()
    clip = Image.open(idle[i] if kind == "idle" else act[i]).convert("RGBA").resize((int(pet["w"]), int(pet["h"])), Image.LANCZOS)
    im.alpha_composite(clip, (int(pet["x"] - vx), int(pet["y"])))
    if z > 0:
        dark = Image.new("RGBA", im.size, (40, 30, 20, 0))
        dark.putalpha(vign.point(lambda v: int(v * 0.22 * z)))
        im.alpha_composite(dark)
        s = 1 + (Z - 1) * z
        w = 1080 / s
        fx, fy = cx, cy - 60  # focus a bit above the centre (head + prop)
        x0 = min(max(fx - w / 2, 0), 1080 - w); y0 = min(max(fy - w / 2, 0), 1080 - w)
        im = im.crop((x0, y0, x0 + w, y0 + w))
    im = im.resize((S, S), Image.LANCZOS).convert("RGB")
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((10, 10, 10 + dr.textlength(label, font=font) + 20, 46), 8, fill=(255, 255, 255))
    dr.text((20, 14), label, fill=(60, 45, 35), font=font)
    return im

tmp = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
for n, (k, i) in enumerate(seq):
    a = frame(k, i, 0.0, "A 지금 크기 그대로")
    c = frame(k, i, zoom_at(n), f"C 살짝 줌인 {Z:g}배 (추천)")
    canvas = Image.new("RGB", (S * 2 + 12, S), (255, 255, 255))
    canvas.paste(a, (0, 0)); canvas.paste(c, (S + 12, 0))
    canvas.save(f"{tmp}/f_{n:04d}.png")
subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", "24", "-i", f"{tmp}/f_%04d.png",
                "-vf", "format=yuv420p", "-c:v", "libx264", "-crf", "20", out], check=True)
print("wrote", out, len(seq), "frames")
