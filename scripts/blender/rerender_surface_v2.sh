#!/bin/bash
# Re-render EVERY exported 단짝 clip from its existing .blend with render_clip.py (surface v2 is applied there), then export.
# Usage: scripts/blender/rerender_surface_v2.sh   (log: $TMPDIR/rr_<frames>.log)
B=/Applications/Blender.app/Contents/MacOS/Blender
R=~/projects/csw/design/character/3d/rig; S=~/projects/csw/scripts/blender
LIST="
hippo_rig_idle idle_frames 0.12
hippo_cheer_jump cheer_frames 0.12
hippo_sweep sweep_frames 0.12
hippo_hop hop_frames 0.12
hippo_eat eat_frames 0.12
hippo_eat_strawberry eat_strawberry_frames 0.12
hippo_stretch_spin stretch_spin_frames 0.12
hippo_wave wave_frames 0.12
hippo_sit_in sit_in_frames 0.12
hippo_sit_loop sit_loop_frames 0.12
hippo_sit_out sit_out_frames 0.12
hippo_drink drink_frames 0.12
hippo_cook cook_frames 0.12
hippo_desk_write desk_write_frames 0.12 glide
hippo_desk_laptop desk_laptop_frames 0.12 glide
hippo_rig_idle idle25_frames 0.5
hippo_cheer_jump cheer25_frames 0.5
hippo_walk_front walk_front25_frames 0.5
hippo_walk_side walk_side25_frames 0.5
hippo_walk_back walk_back25_frames 0.5
hippo_sit_bench_in sit_bench_in25_frames 0.5
hippo_sit_bench_loop sit_bench_loop25_frames 0.5
hippo_sit_bench_out sit_bench_out25_frames 0.5
hippo_sit_eat_in sit_eat_in25_frames 0.5
hippo_sit_eat_loop sit_eat_loop25_frames 0.5
hippo_sit_eat_strawberry sit_eat_strawberry25_frames 0.5
hippo_sit_eat_sweetpotato sit_eat_sweetpotato25_frames 0.5
hippo_sit_eat_out sit_eat_out25_frames 0.5
hippo_lie_in lie_in25_frames 0.5
hippo_lie_loop lie_loop25_frames 0.5
hippo_lie_out lie_out25_frames 0.5
hippo_splash_in splash_in25_frames 0.5
hippo_splash_loop splash_loop25_frames 0.5
hippo_splash_out splash_out25_frames 0.5
hippo_sniff sniff25_frames 0.5
hippo_show_fruit show_fruit25_frames 0.5
"
one() {
  set -- $1
  blend=$1; out=$2; shift 2
  n0=$(ls $R/$out | wc -l | tr -d ' ')
  log=$TMPDIR/rr_$out.log
  tmp=$R/.${out}_new; rm -rf $tmp
  $B -b $R/$blend.blend -P $S/render_clip.py -- $tmp "$@" > $log 2>&1
  n1=$(ls $tmp 2>/dev/null | wc -l | tr -d ' ')
  if grep -q "SURFACE v2" $log && [ "$n1" = "$n0" ]; then rm -rf $R/$out && mv $tmp $R/$out; echo "OK $out $n1"
  else echo "FAIL $out old=$n0 new=$n1 (see $log)"; fi
}
export -f one; export B R S
echo "$LIST" | grep . | xargs -P 4 -I{} bash -c 'one "{}"'
rm -f $R/*.blend1
~/.venvs/csw/bin/python ~/projects/csw/scripts/export_app_assets.py | tail -3
echo ALLDONE
