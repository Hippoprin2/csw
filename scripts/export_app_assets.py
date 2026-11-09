# Export the rendered PNG sequences as app assets (animated WebP + poster + manifest).
# Usage: python export_app_assets.py [out_dir]
import glob, json, os, sys
from PIL import Image

RIG = os.path.expanduser("~/projects/csw/design/character/3d/rig")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/projects/csw/design/character/export/v1")
FPS = 24
# app key (mobile/src/lib/categories.ts + extra) -> render clip, loop?
CLIPS = {
    "idle":     ("idle", True),
    "tidy":     ("sweep", False),
    "move":     ("hop", False),
    "study":    ("desk_write", False),
    "work":     ("desk_laptop", False),   # new category (공부·일 split, 2026-11-08)
    "eat":      ("eat", False),
    "care":     ("stretch_spin", False),
    "people":   ("wave", False),
    "cheer":    ("cheer", False),
    "sit_in":   ("sit_in", False),
    "sit_loop": ("sit_loop", True),
    "sit_out":  ("sit_out", False),
    "eat_strawberry": ("eat_strawberry", False),   # 방에서 '먹이기'(딸기)
    "garden_idle":    ("idle25", True),            # 텃밭 25도 (WORLD.md W2)
    "garden_cheer":   ("cheer25", False),          # 텃밭 수확 만세, 25도
}
os.makedirs(OUT, exist_ok=True)
manifest = {"version": 1, "fps": FPS, "width": 600, "height": 800, "background": "transparent",
            "note": "One-shot clips start and end on the idle rest pose (sit_in ends seated, sit_out starts seated). "
                    "Play one-shots once, then switch back to idle (use duration_ms; do not rely on the decoder's loop count).",
            "clips": {}}
total = 0
for key, (clip, loop) in CLIPS.items():
    fs = sorted(glob.glob(f"{RIG}/{clip}_frames/f_*.png"))
    assert fs, clip
    ims = [Image.open(f).convert("RGBA") for f in fs]
    path = f"{OUT}/hippo_{key}.webp"
    ims[0].save(path, "WEBP", save_all=True, append_images=ims[1:], duration=round(1000 / FPS),
                loop=0 if loop else 1, quality=80, method=4)
    ims[0].save(f"{OUT}/hippo_{key}_poster.png", optimize=True)
    kb = os.path.getsize(path) // 1024; total += kb
    manifest["clips"][key] = {"file": os.path.basename(path), "poster": f"hippo_{key}_poster.png",
                              "frames": len(ims), "duration_ms": round(len(ims) * 1000 / FPS), "loop": loop,
                              "source_clip": clip}
    print(f"{key:9s} {clip:13s} frames={len(ims):3d} loop={loop!s:5s} {kb} KB")
json.dump(manifest, open(f"{OUT}/manifest.json", "w"), ensure_ascii=False, indent=2)
print("TOTAL webp KB", total)
