# Compose the wide room exactly as the app should draw it (manifest only): background, jar cabinet (N closed jars with
# marble dots in category colours), glass doors, owned items + pet in z order. Draws the start view (red) frame.
# usage: blender -b --python scripts/blender/compose_room_wide_preview.py -- <export_dir> <character_export_dir> <out.png> <closed_jars> [none]
import bpy, json, os, random, sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
D, CH, OUT = [os.path.abspath(a) for a in argv[:3]]
N = int(argv[3]); EMPTY = len(argv) > 4 and argv[4] == "none"
r = json.load(open(os.path.join(D, "manifest.json")))["spaces"]["room"]
CATS = ["#9ccfd8", "#f6b26b", "#a4c2f4", "#b4a7d6", "#f9cb9c", "#d5a6bd", "#ea9999", "#b6d7a8", "#c3c8d6"]


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


def srgb_lin(hx):
    c = np.array([int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def disc(canvas, cx, cy, rad, col):
    y0, y1 = int(cy - rad - 1), int(cy + rad + 2); x0, x1 = int(cx - rad - 1), int(cx + rad + 2)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    a = np.clip(rad + 0.5 - np.hypot(xx - cx, yy - cy), 0, 1)[..., None]
    canvas[y0:y1, x0:x1, :3] = col * a + canvas[y0:y1, x0:x1, :3] * (1 - a)


canvas = load(os.path.join(D, r["background"]))
jc = r["jar_cabinet"]
jb, jf = load(os.path.join(D, jc["jar_back"]["file"])), load(os.path.join(D, jc["jar_front"]["file"]))
for k, s in enumerate(jc["slots"][:N]):
    over(canvas, jb, *s["back"])
    rnd = random.Random(k + 3); w = [rnd.random() ** 5 for _ in CATS]
    mx, my, mw, mh = s["marbles"]; cols, rows = 7, 8          # same grid as the jar tab (50 = full closed jar)
    rad = mw / cols / 2 * 0.92
    for row in range(rows):              # bottom-up, alternate rows offset by half
        n = cols - 1 if row % 2 else cols
        for col in range(n):
            cx = mx + rad + (col + (0.5 if row % 2 else 0)) * (mw - 2 * rad) / (cols - 1)
            cy = my + mh - rad - row * (mh - 2 * rad) / (rows - 1)
            disc(canvas, cx, cy, rad, srgb_lin(rnd.choices(CATS, w)[0]))
    over(canvas, jf, *s["front"])
g = jc["glass"]; over(canvas, load(os.path.join(D, g["file"])), g["x"], g["y"])
owned = set() if EMPTY else {"bed", "bookshelf", "squirrel", "lamp", "frame", "wall_clock", "garland", "mobile", "curtain", "rug",
                             "big_plant", "low_table", "radio_stand", "easel", "harvest_tulip", "harvest_strawberry"}
owned |= {"harvest_sweet_potato"}
draw = [(e["z"], "item", e) for e in r["items"] if e["id"] in owned] + [(r["pet"]["z"], "pet", r["pet"])]
for z, kind, e in sorted(draw, key=lambda t: t[0]):
    if kind == "item":
        over(canvas, load(os.path.join(D, e["file"])), e["x"], e["y"])
    else:
        over(canvas, load(os.path.join(CH, "hippo_idle_poster.png"), (e["w"], e["h"])), e["x"], e["y"])
im = bpy.data.images.new("o", canvas.shape[1], canvas.shape[0], alpha=True)
canvas[..., 3] = 1
im.pixels[:] = np.ascontiguousarray(canvas[::-1]).ravel()
im.filepath_raw = OUT; im.file_format = "PNG"; im.save()
print("WROTE", OUT)
