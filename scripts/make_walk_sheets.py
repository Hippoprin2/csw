# Sprite sheets of the 25° walk loops for the yard web test page (canvas can't step animated WebP frames).
# Usage: ~/.venvs/csw/bin/python scripts/make_walk_sheets.py   -> design/yard_test/walk_<dir>.webp (8x6 frames, 435x580 each)
import glob, os
from PIL import Image
H = os.path.expanduser("~/projects/csw")
FW, FH, COLS = 435, 580, 8
for d in ("front", "side", "back"):
    fs = sorted(glob.glob(f"{H}/design/character/3d/rig/walk_{d}25_frames/f_*.png"))
    rows = -(-len(fs) // COLS)
    sh = Image.new("RGBA", (FW * COLS, FH * rows))
    for i, f in enumerate(fs):
        sh.paste(Image.open(f).convert("RGBA").resize((FW, FH), Image.LANCZOS), ((i % COLS) * FW, (i // COLS) * FH))
    out = f"{H}/design/yard_test/walk_{d}.webp"
    sh.save(out, "WEBP", quality=80, method=4)
    print(d, len(fs), "frames", os.path.getsize(out) // 1024, "KB")
