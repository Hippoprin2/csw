# Compose the yard from the export exactly as the app would (manifest draw rules): day | night, all items owned,
# tree stage 4 + fruits, bed flowers, guests, pet at home (25° garden idle poster). Optional walk-area overlay.
# usage: blender -b --python scripts/blender/compose_yard_preview.py -- <export_dir> <character_export_dir> <out.png> [walk] [tree_stage]
import bpy, json, os, sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
D, CH, OUT = [os.path.abspath(a) for a in argv[:3]]
SHOW_WALK = "walk" in argv[3:]
STAGE = int(next((a for a in argv[3:] if a.isdigit()), "4"))
Y = json.load(open(os.path.join(D, "manifest.json")))["spaces"]["yard"]


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


def poly_mask(poly, shape):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    inside = np.zeros(shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        cond = ((y1 > yy) != (y2 > yy)) & (xx < (x2 - x1) * (yy - y1) / (y2 - y1 + 1e-9) + x1)
        inside ^= cond
    return inside


def compose(night):
    c = load(os.path.join(D, Y["background_night" if night else "background"]))
    items = {e["id"]: e for e in Y["items"]}
    walk = Y["walk"]; pr = walk["pet"]
    fx, fy = walk["home"]
    for e in Y["items"]:
        if e["layer"] == "ground": over(c, load(os.path.join(D, e["file"])), e["x"], e["y"])
    for e in Y["items"]:
        if e["layer"] == "pond": over(c, load(os.path.join(D, e["file"])), e["x"], e["y"])
    tree = next(t for t in Y["tree"] if t["stage"] == STAGE)
    flowers = [f for f in Y["bed_flowers"] if f["flower"] == ("sunflower" if f["spot"] == 1 else "tulip")]
    sp = Y["extras"]["sparrow_perch"]
    sorted_ = [(tree["sort_y"], "img", tree)] + [(e["sort_y"], "img", e) for e in Y["items"] if e["layer"] == "sorted"] + \
              [(f["sort_y"], "img", f) for f in flowers] + [(fy, "pet", None)]
    lit = []
    for _, kind, e in sorted(sorted_, key=lambda t: t[0]):
        if kind == "pet":
            over(c, load(os.path.join(CH, "hippo_garden_idle_poster.png"), (pr["w"], pr["h"])),
                 fx + pr["feet_to_center"][0] - pr["w"] / 2, fy + pr["feet_to_center"][1] - pr["h"] / 2)
            continue
        if night and e.get("night_file"):
            over(c, load(os.path.join(D, e["file"])), e["x"], e["y"]); lit.append(e); continue
        over(c, load(os.path.join(D, e["file"])), e["x"], e["y"])
        if e["id"] == "bird_feeder":
            over(c, load(os.path.join(D, sp["file"])), sp["x"], sp["y"])
        if e is tree:
            fr = load(os.path.join(D, Y["fruit"]["file"]))
            for px, py in tree["fruits"]:
                over(c, fr, px - fr.shape[1] / 2, py - fr.shape[0] / 2)
    bf = Y["extras"]["butterfly_open"]; bed = items["flower_bed"]
    over(c, load(os.path.join(D, bf["file"])), bed["x"] + bed["w"] * 0.7 - bf["anchor"][0], bed["y"] - 30 - bf["anchor"][1])
    if night:
        r, g, b, a = Y["night"]["overlay"]
        c[..., :3] = c[..., :3] * (1 - a) + np.array([r, g, b]) / 255.0 * a
        for e in lit:
            over(c, load(os.path.join(D, e["night_file"])), e["x"], e["y"])
    if SHOW_WALK:
        area = poly_mask(walk["area"], c.shape[:2])
        blk = np.zeros_like(area)
        for p in list(walk["blocked"].values()) + list(walk["item_blocked"].values()):
            blk |= poly_mask(p, c.shape[:2])
        ok = area & ~blk
        c[ok, :3] = c[ok, :3] * 0.6 + np.array([0.2, 0.5, 1.0]) * 0.4
        c[area & blk, :3] = c[area & blk, :3] * 0.6 + np.array([1.0, 0.2, 0.2]) * 0.4
        for it in walk["interact"].values():
            x, y = [int(v) for v in it["stand"]]
            c[max(0, y - 6):y + 6, max(0, x - 6):x + 6, :3] = [1, 1, 0]
    return c


out = np.concatenate([compose(False), compose(True)], axis=1)
im = bpy.data.images.new("o", out.shape[1], out.shape[0], alpha=True)
out[..., 3] = 1
im.pixels[:] = np.ascontiguousarray(out[::-1]).ravel()
im.filepath_raw = OUT; im.file_format = "PNG"; im.save()
print("WROTE", OUT)
