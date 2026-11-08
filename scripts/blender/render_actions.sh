#!/bin/zsh
# Render actions + build previews. Usage: zsh scripts/blender/render_actions.sh sweep hop ...
cd ~/projects/csw/design/character/3d
B=/Applications/Blender.app/Contents/MacOS/Blender
S=~/projects/csw/scripts/blender
F=/Users/soniakang/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg
PY=~/.hermes/cache/scratch/gc/bin/python
T=${TMPDIR:-/tmp}
cd rig
[ -f $T/idle1.mp4 ] || $F -y -loglevel error -framerate 24 -i idle_frames/f_%04d.png -filter_complex "color=c=0xF0EBE4:s=600x800:r=24[bg];[bg][0:v]overlay=shortest=1,format=yuv420p" -c:v libx264 -crf 20 $T/idle1.mp4
for a in "$@"; do
  rm -rf ${a}_frames
  $B -b -P $S/anim_actions.py -- . $a 1 2>&1 | grep -E "RENDERED|rror"
  $F -y -loglevel error -framerate 24 -i ${a}_frames/f_%04d.png -filter_complex "color=c=0xF0EBE4:s=600x800:r=24[bg];[bg][0:v]overlay=shortest=1,format=yuv420p" -c:v libx264 -crf 20 $T/${a}1.mp4
  printf "file '%s'\n" $T/idle1.mp4 $T/${a}1.mp4 $T/idle1.mp4 > $T/list_$a.txt
  $F -y -loglevel error -f concat -safe 0 -i $T/list_$a.txt -c copy ${a}_preview.mp4
  $PY - "$a" <<'EOF'
import sys, glob
from PIL import Image
a = sys.argv[1]
fs = sorted(glob.glob(f"{a}_frames/f_*.png")); n = len(fs)
idx = [round(i * (n - 1) / 7) for i in range(8)]
s = Image.new("RGB", (200 * 8, 267), (255, 255, 255))
for k, i in enumerate(idx):
    im = Image.open(fs[i]).convert("RGBA"); bg = Image.new("RGBA", im.size, (240, 235, 228, 255)); bg.paste(im, (0, 0), im)
    s.paste(bg.convert("RGB").resize((200, 267)), (200 * k, 0))
s.save(f"{a}_keyframes.png"); print("sheet", a, n, idx)
EOF
done
