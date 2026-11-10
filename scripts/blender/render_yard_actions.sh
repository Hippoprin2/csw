#!/bin/bash
# Build + render the 25° yard item clips (anim_yard.py) -> design/character/3d/rig/<action>25_frames/
# Usage: scripts/blender/render_yard_actions.sh [action ...]   (default: all)
B=/Applications/Blender.app/Contents/MacOS/Blender
H=~/projects/csw; R=$H/design/character/3d/rig; S=$H/scripts/blender
ALL="sit_bench_in sit_bench_loop sit_bench_out sit_eat_in sit_eat_loop sit_eat_strawberry sit_eat_sweetpotato sit_eat_out lie_in lie_loop lie_out splash_in splash_loop splash_out sniff show_fruit"
one() {
  a=$1
  $B -b -P $S/anim_yard.py -- $R $a > /tmp/yard_$a.log 2>&1 || { echo "FAIL gen $a"; return; }
  rm -rf $R/${a}25_frames
  $B -b $R/hippo_$a.blend -P $S/render_clip.py -- $R/${a}25_frames 0.5 >> /tmp/yard_$a.log 2>&1 || { echo "FAIL render $a"; return; }
  rm -f $R/hippo_$a.blend1
  echo "OK $a $(ls $R/${a}25_frames | wc -l) frames"
}
export -f one; export B R S
printf "%s\n" ${@:-$ALL} | xargs -P 3 -I{} bash -c 'one {}'
