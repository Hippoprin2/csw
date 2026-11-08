#!/bin/zsh
# Build hippo v2 (eye parts + recolor) and render a turnaround sheet + face zoom.
# Usage: zsh scripts/blender/run_v2.sh [lid_angle_deg]
set -e
cd ~/projects/csw/design/character/3d
B=/Applications/Blender.app/Contents/MacOS/Blender
S=~/projects/csw/scripts/blender
$B -b -P $S/build_hippo_v2.py -- hippo_v1_clean.glb v2 ${1:--5} 2>&1 | grep -E "texels|faces|eye R|SAVED|Error|rror" || true
$B -b -P $S/render_turnaround.py -- v2/hippo_v2.glb renders/v2 0 0 2>&1 | grep -E "WROTE|rror" || true
~/.hermes/cache/scratch/gc/bin/python - <<'EOF'
from PIL import Image
ims=[Image.open(f"renders/v2_{v}.png").convert("RGBA") for v in ["front","threequarter","side","back"]]
row=Image.new("RGBA",(sum(i.width for i in ims),ims[0].height),(235,232,228,255)); x=0
for i in ims: row.paste(i,(x,0),i); x+=i.width
row.convert("RGB").resize((row.width//2,row.height//2)).save("renders/v2_sheet.png")
f=Image.open("renders/v2_front.png").convert("RGBA").crop((150,80,620,520))
bg=Image.new("RGBA",f.size,(235,232,228,255)); bg.paste(f,(0,0),f); bg.convert("RGB").resize((940,880)).save("renders/v2_face.png")
print("composed")
EOF
