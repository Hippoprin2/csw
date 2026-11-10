#!/bin/zsh
# Re-render every app clip with render_clip.py (shared look + floor shadow), then export.
cd ~/projects/csw/design/character/3d/rig
B=/Applications/Blender.app/Contents/MacOS/Blender
S=~/projects/csw/scripts/blender
r() {  # blend out elev [flags]
  rm -rf "$2"
  $B -b "$1" -P $S/render_clip.py -- "$PWD/$2" "${@:3}" 2>&1 | grep -E "RENDERED|Traceback|Error" | sed "s#$PWD/##"
}
r hippo_rig_idle.blend   idle_frames 0.12
r hippo_cheer_jump.blend cheer_frames 0.12
for a in sweep hop eat eat_strawberry stretch_spin wave sit_in sit_loop sit_out; do
  r hippo_$a.blend ${a}_frames 0.12
done
r hippo_desk_write.blend  desk_write_frames 0.12 glide
r hippo_desk_laptop.blend desk_laptop_frames 0.12 glide
r hippo_rig_idle.blend   idle25_frames 0.5
r hippo_cheer_jump.blend cheer25_frames 0.5
~/.hermes/cache/scratch/gc/bin/python ~/projects/csw/scripts/export_app_assets.py | tail -3
echo ALLDONE
