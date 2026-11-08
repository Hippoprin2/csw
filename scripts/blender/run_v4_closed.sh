#!/bin/zsh
# Closed-eye variant of v4 (expression image pre-aligned to the concept front).
set -e
cd ~/projects/csw/design/character/3d
B=/Applications/Blender.app/Contents/MacOS/Blender
S=~/projects/csw/scripts/blender
PY=~/.hermes/cache/scratch/gc/bin/python
$PY $S/concept_eye_decal.py ../expressions/closed_front.png v4/decals/eyes_closed.png 218.8,290.9,340.3,291.8 2>&1 | grep -v -i deprecat
DECAL_V4=1 $B -b -P $S/build_hippo_v3.py -- v2/hippo_v2.blend v4/decals v4 closed 2>&1 | grep -E "SAVED|rror" || true
$B -b -P $S/render_turnaround.py -- v4/hippo_v3_closed.glb renders/v4_closed 0 0 2>&1 | grep -c WROTE || true
$PY - <<'EOF'
from PIL import Image
def comp(p, box):
    f=Image.open(p).convert("RGBA").crop(box)
    bg=Image.new("RGBA",f.size,(235,232,228,255)); bg.paste(f,(0,0),f); return bg
box=(150,40,620,480)
a=comp("renders/v4_front.png",box); b=comp("renders/v4_closed_front.png",box); c=comp("renders/v4_closed_threequarter.png",box)
s=Image.new("RGB",(a.width*3+20,a.height),(255,255,255)); s.paste(a,(0,0)); s.paste(b,(a.width+10,0)); s.paste(c,(2*a.width+20,0))
s.save("renders/v4_open_closed.png"); print("ok")
EOF
