#!/usr/bin/env python3
"""Contact sheet of transparent PNGs on the art-bible preview colour (ffmpeg only, no PIL).
usage: python3 scripts/contact_sheet.py <out.png> <cols> <tile_px> img1.png img2.png ...
"""
import subprocess, sys

out, cols, tile = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
imgs = sys.argv[4:]
args = ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=0xF0EBE4:s={tile}x{tile}"]
for f in imgs:
    args += ["-i", f]
fc = []
for k in range(1, len(imgs) + 1):
    fc.append(f"[{k}]scale={tile}:{tile}[s{k}];[0][s{k}]overlay[o{k}]")
layout = "|".join(f"{(i % cols) * tile}_{(i // cols) * tile}" for i in range(len(imgs)))
fc.append("".join(f"[o{k}]" for k in range(1, len(imgs) + 1)) + f"xstack=inputs={len(imgs)}:layout={layout}:fill=0xF0EBE4")
args += ["-filter_complex", ";".join(fc), "-frames:v", "1", out]
subprocess.run(args, check=True)
print("WROTE", out)
