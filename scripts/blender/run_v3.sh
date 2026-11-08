#!/bin/zsh
# Hippo v3: flat painted-eye decal (concept style). Usage: zsh scripts/blender/run_v3.sh
set -e
cd ~/projects/csw/design/character/3d
B=/Applications/Blender.app/Contents/MacOS/Blender
S=~/projects/csw/scripts/blender
PY=~/.hermes/cache/scratch/gc/bin/python
$PY $S/draw_eye_decals.py v3/decals
for st in open closed; do
  $B -b -P $S/build_hippo_v3.py -- v2/hippo_v2.blend v3/decals v3 $st 2>&1 | grep -E "decal faces|SAVED|Error|rror" || true
  $B -b -P $S/render_turnaround.py -- v3/hippo_v3_$st.glb renders/v3_$st 0 0 2>&1 | grep -cE "WROTE" || true
done
$PY - <<'EOF'
from PIL import Image
def comp(p, box=None):
    f=Image.open(p).convert("RGBA")
    if box: f=f.crop(box)
    bg=Image.new("RGBA",f.size,(235,232,228,255)); bg.paste(f,(0,0),f); return bg
ims=[comp(f"renders/v3_open_{v}.png") for v in ["front","threequarter","side","back"]]
row=Image.new("RGB",(sum(i.width for i in ims),ims[0].height)); x=0
for i in ims: row.paste(i,(x,0)); x+=i.width
row.resize((row.width//2,row.height//2)).save("renders/v3_sheet.png")
a=comp("renders/v3_open_front.png",(150,80,620,520)); b=comp("renders/v3_closed_front.png",(150,80,620,520))
s=Image.new("RGB",(a.width*2+10,a.height),(255,255,255)); s.paste(a,(0,0)); s.paste(b,(a.width+10,0))
s.save("renders/v3_face_open_closed.png"); print("composed")
EOF
