# Compose app-style previews from the export (exactly what the app will draw): room set A + pet, garden + pet + 3 crops.
# usage: blender -b --python scripts/blender/compose_world_preview.py -- <export_dir> <character_export_dir> <out.png>
import bpy, json, os, sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
D, CH, OUT = [os.path.abspath(a) for a in argv[:3]]
M = json.load(open(os.path.join(D, "manifest.json")))["spaces"]


def load(path, size=None):
    im = bpy.data.images.load(path, check_existing=False)
    if size:
        im.scale(int(round(size[0])), int(round(size[1])))
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)[::-1].copy()
    bpy.data.images.remove(im)
    return a


def over(canvas, L, x, y):
    x, y = int(round(x)), int(round(y))
    h, w = L.shape[:2]
    cx0, cy0 = max(0, x), max(0, y); cx1, cy1 = min(canvas.shape[1], x + w), min(canvas.shape[0], y + h)
    if cx1 <= cx0 or cy1 <= cy0: return
    l = L[cy0 - y:cy1 - y, cx0 - x:cx1 - x]; a = l[..., 3:4]
    canvas[cy0:cy1, cx0:cx1, :3] = l[..., :3] * a + canvas[cy0:cy1, cx0:cx1, :3] * (1 - a)


# room: set A + harvest decorations + pet in z order
r = M["room"]; room = load(os.path.join(D, r["background"]))
owned = {"bed", "bookshelf", "squirrel", "lamp", "frame", "wall_clock", "garland", "mobile", "curtain", "rug", "big_plant",
         "low_table", "radio_stand", "easel", "harvest_tulip", "harvest_strawberry", "harvest_sweet_potato"}
draw = [(e["z"], "item", e) for e in r["items"] if e["id"] in owned] + [(r["pet"]["z"], "pet", r["pet"])]
for z, kind, e in sorted(draw, key=lambda t: t[0]):
    if kind == "item":
        over(room, load(os.path.join(D, e["file"])), e["x"], e["y"])
    else:
        over(room, load(os.path.join(CH, "hippo_idle_poster.png"), (e["w"], e["h"])), e["x"], e["y"])

# garden: background, pet, then crops
g = M["garden"]; garden = load(os.path.join(D, g["background"]))
p = g["pet"]; over(garden, load(os.path.join(CH, "hippo_garden_idle_poster.png"), (p["w"], p["h"])), p["x"], p["y"])
for plot, name in zip(g["plots"], ("sweet_potato_3", "tulip_3_doze", "strawberry_2")):
    over(garden, load(os.path.join(D, g["crops"][name])), plot["crop_x"], plot["crop_y"])

out = np.concatenate([room, garden], axis=1)
im = bpy.data.images.new("o", out.shape[1], out.shape[0], alpha=True)
out[..., 3] = 1
im.pixels[:] = np.ascontiguousarray(out[::-1]).ravel()
im.filepath_raw = OUT; im.file_format = "PNG"; im.save()
print("WROTE", OUT)
