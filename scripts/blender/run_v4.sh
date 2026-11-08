#!/bin/zsh
# Hippo v4: eyes/brows/nostrils projected straight from the concept art.
set -e
cd ~/projects/csw/design/character/3d
B=/Applications/Blender.app/Contents/MacOS/Blender
S=~/projects/csw/scripts/blender
PY=~/.hermes/cache/scratch/gc/bin/python
mkdir -p v4/decals
$PY $S/concept_eye_decal.py ../apose/hippo_apose_v1_front.png v4/decals/eyes_open.png 2>&1 | grep -v -i deprecat
DECAL_V4=1 $B -b -P $S/build_hippo_v3.py -- v2/hippo_v2.blend v4/decals v4 open 2>&1 | grep -E "decal faces|SAVED|rror" || true
$B -b -P $S/render_turnaround.py -- v4/hippo_v3_open.glb renders/v4 0 0 2>&1 | grep -c WROTE || true
$PY - <<'EOF'
from PIL import Image
def comp(p, box=None):
    f=Image.open(p).convert("RGBA")
    if box: f=f.crop(box)
    bg=Image.new("RGBA",f.size,(235,232,228,255)); bg.paste(f,(0,0),f); return bg
a=comp("renders/v4_front.png",(150,40,620,480))
c=comp("../apose/hippo_apose_v1_front_transparent.png")
s=1.254; c=c.resize((int(c.width*s),int(c.height*s)))
ox=383-279.5*s; oy=255.7-291.4*s
cc=Image.new("RGB",(768,1024),(235,232,228)); cc.paste(c,(int(ox),int(oy))); cc=cc.crop((150,40,620,480))
out=Image.new("RGB",(a.width*2+10,a.height),(255,255,255)); out.paste(cc,(0,0)); out.paste(a,(a.width+10,0))
out.save("renders/v4_vs_concept.png")
ims=[comp(f"renders/v4_{v}.png") for v in ["front","threequarter","side","back"]]
row=Image.new("RGB",(sum(i.width for i in ims),ims[0].height)); x=0
for i in ims: row.paste(i,(x,0)); x+=i.width
row.resize((row.width//2,row.height//2)).save("renders/v4_sheet.png"); print("ok")
EOF
