# Compose the yard from the export exactly as the app would (manifest draw rules): day | night, all items owned,
# tree stage 4 + fruits, bed flowers, guests, pet at home (25° garden idle poster). Optional walk-area overlay.
# usage: blender -b --python scripts/blender/compose_yard_preview.py -- <export_dir> <character_export_dir> <out.png> [walk] [map] [own=1,2] [tree_stage]
#   default: day | night viewports (1080 x 1860, camera rule from the manifest) ; map: the whole canvas (day)
import bpy, json, os, sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
D, CH, OUT = [os.path.abspath(a) for a in argv[:3]]
SHOW_WALK = "walk" in argv[3:]
STAGE = int(next((a for a in argv[3:] if a.isdigit()), "4"))
MAP = "map" in argv[3:]
OWN = [z for a in argv[3:] if a.startswith("own=") for z in a[4:].split(",")] or ["1"]
VIEW_H = 1860
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
    CW, CH_ = Y["canvas"]
    c = np.zeros((CH_, CW, 4), dtype=np.float32)
    for t in Y["tiles"]:
        L = load(os.path.join(D, t["night_file" if night else "file"])); c[t["y"]:t["y"] + t["h"], t["x"]:t["x"] + t["w"]] = L
    for z, lk in Y["locks"].items():
        if z not in OWN: over(c, load(os.path.join(D, lk["file"])), lk["x"], lk["y"])
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
        area = np.zeros(c.shape[:2], dtype=bool); blk = np.zeros_like(area)
        for z, Z in walk["zones"].items():
            if Z["area"] is None or z not in OWN: continue
            area |= poly_mask(Z["area"], c.shape[:2])
            for p in Z["blocked"].values(): blk |= poly_mask(p, c.shape[:2])
        for p in list(walk["blocked"].values()) + list(walk["item_blocked"].values()):
            blk |= poly_mask(p, c.shape[:2])
        ok = area & ~blk
        c[ok, :3] = c[ok, :3] * 0.6 + np.array([0.2, 0.5, 1.0]) * 0.4
        c[area & blk, :3] = c[area & blk, :3] * 0.6 + np.array([1.0, 0.2, 0.2]) * 0.4
        for it in walk["interact"].values():
            x, y = [int(v) for v in it["stand"]]
            c[max(0, y - 6):y + 6, max(0, x - 6):x + 6, :3] = [1, 1, 0]
    if MAP:
        return c
    # camera: centre on the pet, clamp to owned zones (+ peek into locked neighbours)
    cam = Y["camera"]; peek = cam["peek"]; zs = walk["zones"]
    rs = [zs[z]["rect"] for z in OWN]
    x0, y0 = min(r[0] for r in rs), min(r[1] for r in rs)
    x1, y1 = max(r[0] + r[2] for r in rs), max(r[1] + r[3] for r in rs)
    for z, Z in zs.items():
        if z in OWN or Z["price"] is None: continue
        rx, ry, rw, rh = Z["rect"]
        if rx == x1: x1 += peek
        if ry == y1: y1 += peek
    cx = fx + pr["feet_to_center"][0]; cy = fy + pr["feet_to_center"][1]
    vx = int(min(max(cx - 540, x0), max(x0, x1 - 1080)))
    vy = int(min(max(cy - VIEW_H / 2, y0), max(y0, y1 - VIEW_H)))
    return c[vy:vy + VIEW_H, vx:vx + 1080]


out = compose(False) if MAP else np.concatenate([compose(False), compose(True)], axis=1)
im = bpy.data.images.new("o", out.shape[1], out.shape[0], alpha=True)
out[..., 3] = 1
im.pixels[:] = np.ascontiguousarray(out[::-1]).ravel()
im.filepath_raw = OUT; im.file_format = "PNG"; im.save()
print("WROTE", OUT)
