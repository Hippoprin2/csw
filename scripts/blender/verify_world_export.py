# Verify the exported room layers: composite background + layers (manifest order) and compare with a real full render.
# usage: blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/verify_world_export.py -- <export_dir> <set a|b>
import bpy, json, os, sys
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import room as R
import export_world as E   # reuses render/save helpers (its __main__ block does not run on import)

argv = sys.argv[sys.argv.index("--") + 1:]
D, SET = os.path.abspath(argv[0]), argv[1]
man = json.load(open(os.path.join(D, "manifest.json")))["spaces"]["room"]
ids = R.SET_A if SET == "a" else R.SET_B
ids = ids + ["harvest_tulip", "harvest_strawberry", "harvest_sweet_potato"]


def load(path):
    im = bpy.data.images.load(path, check_existing=False)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)[::-1]
    bpy.data.images.remove(im)
    return a


comp = load(os.path.join(D, man["background"]))[..., :3].copy()
for it in sorted(man["items"], key=lambda e: e["z"]):
    if it["id"] not in ids: continue
    L = load(os.path.join(D, it["file"]))
    x, y, w, h = it["x"], it["y"], it["w"], it["h"]
    a = L[..., 3:4]
    comp[y:y + h, x:x + w] = L[..., :3] * a + comp[y:y + h, x:x + w] * (1 - a)

E.sc, E.cam = R.setup_render(E.SIZE, E.SIZE, R.ORTHO)
E.cam.location = R.TARGET + Vector((0.35, -1, R.ELEV)).normalized() * 12
E.cam.rotation_euler = (R.TARGET - E.cam.location).to_track_quat("-Z", "Y").to_euler()
E.sc.frame_set(1); E.hide(E.HIPPO_OBJS)
R.base(); R.calendar()
for i in ids:
    (R.ITEMS.get(i) or R.HARVEST[i.replace("harvest_", "")])()
full = E.render(os.path.join(E.TMP, "verify_full.png"))[..., :3]
diff = np.abs(full - comp).max(axis=2)
print("VERIFY mean", round(float(diff.mean()), 4), "p99", round(float(np.percentile(diff, 99)), 4), "max", round(float(diff.max()), 4),
      "pct>0.06", round(float((diff > 0.06).mean() * 100), 2))
side = np.concatenate([full, comp, np.repeat(np.clip(diff * 5, 0, 1)[..., None], 3, 2)], axis=1)
E.save_png(np.concatenate([side, np.ones(side.shape[:2] + (1,), np.float32)], axis=2), os.path.join(D, f"_verify_room_{SET}.png"))
