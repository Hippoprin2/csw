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
    "drink": ("drink", False),   # 잘 먹기 > 물 마시기 (2026-11-12, 기록에 '물')
    "cook": ("cook", False),     # 잘 먹기 > 요리 (2026-11-12, 요리/만들/끓/볶)
    # 방에서 단짝 탭 → 랜덤 반응 (2026-11-14). 캔버스가 600x800이 아님 → manifest clips[key].canvas/feet, tap_reactions
    "tap_fart_hop": ("fart_hop_ko", False),   # 600x1100 (위로 300px 더: 방방 높이), '뿡!' 글자 = scripts/composite_fart_text.py ko
    "tap_roll":     ("roll", False),       # 1600x800 (양옆 500px씩 더), 엎드려 통나무 구르기 v2, 왼쪽 = 좌우 뒤집기
    "garden_idle":    ("idle25", True),            # 텃밭 25도 (WORLD.md W2)
    "garden_cheer":   ("cheer25", False),          # 텃밭 수확 만세, 25도
    # 마당·텃밭 걷기 25도 (anim_yard.py). 제자리 걷기 루프, 앱이 위치를 옮김. 왼쪽 = walk_side 좌우 뒤집기
    "walk_front":     ("walk_front25", True),
    "walk_side":      ("walk_side25", True),
    "walk_back":      ("walk_back25", True),
    # 마당 아이템 동작 25도 (anim_yard.py, 2026-11-11). 클립 원점(발 303,697) = manifest yard_actions의 stand 점
    "sit_bench_in":        ("sit_bench_in25", False),
    "sit_bench_loop":      ("sit_bench_loop25", True),
    "sit_bench_out":       ("sit_bench_out25", False),
    "sit_eat_in":          ("sit_eat_in25", False),
    "sit_eat_loop":        ("sit_eat_loop25", True),
    "sit_eat_strawberry":  ("sit_eat_strawberry25", False),
    "sit_eat_sweetpotato": ("sit_eat_sweetpotato25", False),
    "sit_eat_out":         ("sit_eat_out25", False),
    "lie_in":              ("lie_in25", False),
    "lie_loop":            ("lie_loop25", True),
    "lie_out":             ("lie_out25", False),
    "splash_in":           ("splash_in25", False),
    "splash_loop":         ("splash_loop25", True),
    "splash_out":          ("splash_out25", False),
    "sniff":               ("sniff25", False),
    "show_fruit":          ("show_fruit25", False),
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
    if ims[0].size != (600, 800):   # bigger canvas: same px scale, feet point moves (wide = both sides, tall = extra on top)
        W, H = ims[0].size
        manifest["clips"][key]["canvas"] = [W, H]
        manifest["clips"][key]["feet"] = [303 + (W - 600) // 2, 713 + (H - 800)]
    print(f"{key:9s} {clip:13s} frames={len(ims):3d} loop={loop!s:5s} {kb} KB")
manifest["tap_reactions"] = {
    "clips": ["tap_fart_hop", "tap_roll"],
    "note": "Room: tapping the pet plays one of these at random (tap_roll: 50% mirrored = roll left), then idle. "
            "Clips with `canvas` are bigger than 600x800 at the SAME px scale: draw at canvas*(pet.w/600) and put clip `feet` "
            "on the room feet point (= the idle clip's (303,713)). Ignore taps while a record/feed action plays.",
}
# walk loops: the sprite speed at which the feet do not slide (scripts/blender/measure_stride.py: 0.42 unit/s,
# ortho 1.45 spans the 800-px HEIGHT -> 1 unit = 800/1.45 clip px; yard/garden draw the clip at w=435 -> x0.725 = 400 px = yard px_per_unit)
GROUND = 0.42 * 800 / 1.45 * 0.725
manifest["walk"] = {
    "clips": {"front": "walk_front", "back": "walk_back", "right": "walk_side", "left": "walk_side (draw mirrored)"},
    "speed_px_s": 360, "no_slide_px_s": round(GROUND), "depth_factor": 0.426,
    "speed_note": "speed_px_s = 0.9 unit/s x 400 px (대표 결정 2026-11-11, felt on the web test page). The clip's stride matches 0.42 unit/s "
                  "(no_slide_px_s), so the feet glide a little at 0.9 - accepted.",
    "note": "speed in yard/garden canvas px at pet w=435. Screen-down/up movement is foreshortened by the 25 deg camera: "
            "ground distance = hypot(dx, dy / depth_factor); move so that ground distance grows by speed_px_s per second "
            "(pure horizontal = 360 px/s, pure vertical = 153 px/s). Clip: |dx| >= |dy / depth_factor| -> side (mirror when dx < 0), "
            "else dy > 0 -> front, dy < 0 -> back. Feet = same floor point as the garden clips (303, 697)." % (),
}
# yard item actions: where to place the clip (its feet point = (303, 697)) and how to chain the parts
manifest["yard_actions"] = {
    "note": "Draw the clip with its feet point on `stand` (yard canvas px). Holdouts are baked in: where the item is in front of the pet "
            "the clip is transparent, so draw the item sprite first and the pet clip on top (bench, hammock, flower bed, pond water). "
            "Shadow under the pet is baked in and switches off while it sits on the bench / lies in the hammock / stands in the water. "
            "Seated/lying parts: play *_in once, repeat *_loop for 5-10 s, then *_out once (in ends where loop starts, loop ends where out starts).",
    "sit_bench": {"parts": ["sit_bench_in", "sit_bench_loop", "sit_bench_out"], "stand": [437.7, 911.6],
                  "stand_note": "NEW stand: 0.30 world units in front of the seat (world manifest bench stand 477.4,863.2 is ON the seat). "
                                "The pet walks to the front of the bench and the clip hops it up; it then sorts in front of the bench."},
    "sit_eat": {"parts": ["sit_eat_in", "sit_eat_loop", "sit_eat_out"], "stand": [392.2, 1434.4],
                "eat": ["sit_eat_strawberry", "sit_eat_sweetpotato"],
                "eat_note": "feeding (Y5): while seated, play one eat clip once (starts/ends on the sit_eat_loop pose), then back to the loop"},
    "lie": {"parts": ["lie_in", "lie_loop", "lie_out"], "stand": [207.7, 1231.6],
            "stand_note": "NEW stand: 0.32 world units in front of the hammock centre (world manifest stand 250,1180 is the cloth centre)."},
    "splash": {"parts": ["splash_in", "splash_loop", "splash_out"], "stand": [681.1, 1092.2], "enter": [429.1, 1063.6],
               "note": "splash_in: move the clip from enter to stand during frames 4-15 (the hop); splash_out: stand -> enter during frames 8-19. "
                       "Lower body is already cut at the waterline: do NOT draw extras.pond_water over the pet (it would also cover the torso where it overlaps the far half of the pond)."},
    "sniff": {"parts": ["sniff"], "stand": [845.5, 1402.3], "note": "one-shot, idle -> idle (behind the bed, flowers cover the feet)"},
    "show_fruit": {"parts": ["show_fruit"], "stand": [288.6, 855.3],
                   "note": "one-shot: starts facing the tree (back view), points at the fruit, turns to the camera, ends on idle"},
}
json.dump(manifest, open(f"{OUT}/manifest.json", "w"), ensure_ascii=False, indent=2)
print("TOTAL webp KB", total)
