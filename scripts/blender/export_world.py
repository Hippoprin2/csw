# Export room + garden art for the app: backgrounds, per-item layers (item + its own soft shadow), crop images,
# harvest decorations, and a manifest with pixel positions, draw order and the pet anchor.
# usage: blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/export_world.py -- <out_dir> [room|garden|all]
#
# Layers: item colour = Eevee render of the item alone (transparent); its shadow = Cycles shadow-catcher pass
#   (background objects as catchers, item as holdout). layer = item over black shadow.
#   Drawing the layers over the background in manifest order reproduces the full render.
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, os.path.dirname(__file__))
import room as R
import garden as G

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(argv[0]); WHAT = argv[1] if len(argv) > 1 else "all"
TMP = os.path.join(OUT, "_tmp"); os.makedirs(TMP, exist_ok=True)
SIZE = 1080
CLIP_PX_PER_UNIT = 800 / 1.45            # character clips: 600x800, ortho 1.45, centre = world (0,0,0.07)
HIPPO_OBJS = [bpy.data.objects[n] for n in ("Hippo", "EyeDecal", "HippoRig")]
sc = None; cam = None


def render(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path, check_existing=False)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)[::-1]   # top row first
    bpy.data.images.remove(im)
    return a


def save_png(arr, path):
    h, w = arr.shape[:2]
    im = bpy.data.images.new("out", w, h, alpha=True)
    im.pixels[:] = np.ascontiguousarray(arr[::-1]).ravel()
    im.filepath_raw = path; im.file_format = "PNG"; im.save()
    bpy.data.images.remove(im)


def lum(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def _engine_eevee():
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng; return
        except Exception:
            pass


def shadow_pass(path, catcher_objs, item_objs):
    """Cycles shadow-catcher render: only the item's shadow on the background, as alpha (Eevee has no shadow catcher)"""
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"; prefs.get_devices()
        for dv in prefs.devices: dv.use = dv.type != "CPU"
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.cycles.samples = 128; sc.cycles.use_denoising = True   # low samples left denoiser blotches on the wall
    saved = [(o, o.visible_shadow) for o in catcher_objs]
    for o in catcher_objs:
        o.is_shadow_catcher = True; o.visible_shadow = False     # background never shadows itself in this pass
    for o in item_objs:
        o.is_holdout = True
    bg = sc.world.node_tree.nodes["Background"].inputs[1]
    wsave = bg.default_value; bg.default_value = 0.0      # sun shadows only (Eevee doesn't occlude world light either)
    lights = [o for o in sc.objects if o.type == "LIGHT"]
    lsave = [(o, o.data.use_shadow) for o in lights]
    for o in lights:
        o.data.use_shadow = (o.name == "key")              # one clean shadow per item (fill/rim/bounce made ghost copies)
    A = render(path)[..., 3]
    for o, v in lsave:
        o.data.use_shadow = v
    bg.default_value = wsave
    for o, v in saved:
        o.is_shadow_catcher = False; o.visible_shadow = v
    for o in item_objs:
        o.is_holdout = False
    _engine_eevee()
    return A


SHADOW_REACH = 220     # px: shadow farther than this from the item is ignored (only stray noise lives there)
FEATHER = 50           # px soft edge on that limit so nothing shows a hard cut


def box_blur(m, r):
    ii = np.pad(m.astype(np.float32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    h, w = m.shape
    y0 = np.clip(np.arange(h) - r, 0, h); y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w); x1 = np.clip(np.arange(w) + r + 1, 0, w)
    s = ii[y1][:, x1] - ii[y0][:, x1] - ii[y1][:, x0] + ii[y0][:, x0]
    return s / ((y1 - y0)[:, None] * (x1 - x0)[None, :])


def dilate(mask, r):
    """square max-filter via prefix sums (no scipy in Blender)"""
    m = mask.astype(np.int32)
    h, w = m.shape
    c = np.pad(m, ((1, 0), (0, 0))).cumsum(0)
    lo = np.clip(np.arange(h) - r, 0, h); hi = np.clip(np.arange(h) + r + 1, 0, h)
    rows = ((c[hi] - c[lo]) > 0).astype(np.int32)
    c2 = np.pad(rows, ((0, 0), (1, 0))).cumsum(1)
    lo = np.clip(np.arange(w) - r, 0, w); hi = np.clip(np.arange(w) + r + 1, 0, w)
    return (c2[:, hi] - c2[:, lo]) > 0


def layer(I, S):
    """item (Eevee, straight alpha) over a black shadow with alpha S"""
    ai = I[..., 3:4]
    as_ = np.clip(S, 0.0, 0.75)
    as_ *= box_blur(dilate(ai[..., 0] > 0.01, SHADOW_REACH - FEATHER), FEATHER)
    as_ = as_[..., None]
    as_[as_ < 0.045] = 0.0
    out_a = ai + as_ * (1 - ai)
    rgb = np.where(out_a > 1e-4, I[..., :3] * ai / np.maximum(out_a, 1e-4), 0.0)
    return np.concatenate([rgb, out_a], axis=2)


def crop_bbox(L, pad=3):
    ys, xs = np.where(L[..., 3] > 0.004)
    if len(xs) == 0:
        return None
    x0, x1 = max(0, xs.min() - pad), min(L.shape[1], xs.max() + pad + 1)
    y0, y1 = max(0, ys.min() - pad), min(L.shape[0], ys.max() + pad + 1)
    return x0, y0, x1 - x0, y1 - y0


def project(p):
    v = world_to_camera_view(sc, cam, Vector(p))
    return round(v.x * SIZE, 1), round((1 - v.y) * SIZE, 1)


def hide(objs, flag=True):
    for o in objs:
        o.hide_render = flag


def meshes(g):
    return [c for c in g.children_recursive if c.type == "MESH"] if g else []


def remove(g):
    for c in list(g.children_recursive):
        bpy.data.objects.remove(c, do_unlink=True)
    bpy.data.objects.remove(g, do_unlink=True)


def clear_scene_meshes(keep):
    for o in list(bpy.data.objects):
        if o not in keep and o.type in ("MESH", "EMPTY"):
            bpy.data.objects.remove(o, do_unlink=True)


def pet_entry(world_xy, px_per_unit, clip_set):
    cx, cy = project((world_xy[0], world_xy[1], 0.07))
    s = px_per_unit / CLIP_PX_PER_UNIT
    w, h = 600 * s, 800 * s
    return {"clips": clip_set, "center": [cx, cy], "w": round(w, 1), "h": round(h, 1),
            "x": round(cx - w / 2, 1), "y": round(cy - h / 2, 1),
            "note": "draw the character clip (600x800 frame) scaled to w x h with its centre at `center`"}


# ------------------------------------------------------------------ room
ROOM_ORDER = [  # draw order (back -> front); 'PET' marks where the character goes
    "curtain", "frame", "wall_clock", "garland", "string_lights", "mobile", "bookshelf", "bed", "radio_stand", "aquarium",
    "easel", "guitar", "harvest_tulip", "harvest_sunflower", "harvest_strawberry", "harvest_sweet_potato",
    "rug", "low_table", "PET", "lamp", "squirrel", "cushion", "big_plant"]
SLOT = {"frame": "wall_left", "garland": "wall_top", "cushion": "front_center", "mobile": "ceiling", "big_plant": "front_right",
        "wall_clock": "wall_right", "curtain": "window", "rug": "floor_center", "squirrel": "front_center", "lamp": "front_left",
        "string_lights": "wall_top", "low_table": "floor_right", "radio_stand": "bedside", "easel": "lean", "guitar": "lean",
        "bookshelf": "back_right", "aquarium": "bedside", "bed": "back_left",
        "harvest_tulip": "sill_vase", "harvest_sunflower": "sill_vase", "harvest_strawberry": "sill_plate", "harvest_sweet_potato": "sill_basket"}


def export_room():
    global sc, cam
    sc, cam = R.setup_render(SIZE, SIZE, R.ORTHO)
    cam.location = R.TARGET + Vector((0.35, -1, R.ELEV)).normalized() * 12
    cam.rotation_euler = (R.TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.frame_set(1); hide(HIPPO_OBJS)
    d = os.path.join(OUT, "room"); os.makedirs(d, exist_ok=True)
    base = R.base(); cal = R.calendar()
    base_objs = meshes(base) + meshes(cal)
    B = render(os.path.join(TMP, "room_B.png"))
    save_png(B, os.path.join(d, "background.png"))
    builders = dict(R.ITEMS); builders.update({f"harvest_{k}": v for k, v in R.HARVEST.items()})
    entries = []
    for z, iid in enumerate(ROOM_ORDER):
        if iid == "PET" or (os.environ.get("ONLY") and iid not in os.environ["ONLY"].split(",")):
            continue
        g = builders[iid]()
        hide(base_objs); I = render(os.path.join(TMP, "I.png")); hide(base_objs, False)
        S = shadow_pass(os.path.join(TMP, "S.png"), base_objs, meshes(g))
        L = layer(I, S)
        x, y, w, h = crop_bbox(L)
        save_png(L[y:y + h, x:x + w], os.path.join(d, f"{iid}.png"))
        entries.append({"id": iid, "file": f"room/{iid}.png", "slot": SLOT[iid], "z": z, "x": int(x), "y": int(y), "w": int(w), "h": int(h)})
        remove(g)
        print("ROOM", iid, x, y, w, h)
    pet = pet_entry(R.HIPPO, SIZE / R.ORTHO, "room (default, 6.5°): idle + all actions")
    pet["z"] = ROOM_ORDER.index("PET")
    clear_scene_meshes(HIPPO_OBJS)
    return {"canvas": [SIZE, SIZE], "background": "room/background.png", "px_per_unit": SIZE / R.ORTHO,
            "pet": pet, "items": entries,
            "rules": "draw background, then items you own+placed and the pet in ascending z. One item per slot "
                     "(sill_vase: tulip or sunflower). harvest_* appear after the first harvest of that crop."}


# ------------------------------------------------------------------ garden
def export_garden():
    global sc, cam
    sc, cam = R.setup_render(SIZE, SIZE, G.ORTHO)
    cam.location = G.TARGET + G.cam_dir() * 12
    cam.rotation_euler = (G.TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.frame_set(1); hide(HIPPO_OBJS)
    d = os.path.join(OUT, "garden"); os.makedirs(os.path.join(d, "crops"), exist_ok=True)
    bg = G.background(); bg_objs = meshes(bg)
    B = render(os.path.join(TMP, "garden_B.png"))
    sky = np.array([0xCD, 0xE8, 0xF5], dtype=np.float32) / 255.0
    Bo = B.copy(); a = Bo[..., 3:4]
    Bo[..., :3] = Bo[..., :3] * a + sky * (1 - a); Bo[..., 3] = 1.0
    save_png(Bo, os.path.join(d, "background.png"))
    ppu = SIZE / G.ORTHO
    win = int(round(G.CROP_ORTHO * ppu))                  # same window for every crop image -> one anchor rule
    mid = (G.PLOT_X[1], G.PLOT_Y, G.SOIL_Z)
    ax, ay = project((mid[0], mid[1], mid[2] + G.CROP_LIFT))
    x0, y0 = int(round(ax - win / 2)), int(round(ay - win / 2))
    jobs = [("mound", 0, False)] + [(c, s, dz) for c in G.CROPS for s in (1, 2, 3) for dz in (False, True)]
    crops = []
    for cid, stage, doze in jobs:
        name = "mound" if cid == "mound" else f"{cid}_{stage}{'_doze' if doze else ''}"
        g = G.build_crop("sweet_potato" if cid == "mound" else cid, stage, mid, doze, name=name)
        hide(bg_objs); I = render(os.path.join(TMP, "I.png")); hide(bg_objs, False)
        S = shadow_pass(os.path.join(TMP, "S.png"), bg_objs, meshes(g))
        L = layer(I, S)
        pad = np.zeros((win, win, 4), dtype=np.float32)
        sx0, sy0 = max(0, x0), max(0, y0); sx1, sy1 = min(SIZE, x0 + win), min(SIZE, y0 + win)
        pad[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = L[sy0:sy1, sx0:sx1]
        save_png(pad, os.path.join(d, "crops", f"{name}.png"))
        crops.append(name)
        remove(g)
        print("CROP", name)
    plots = []
    for i, px in enumerate(G.PLOT_X):
        cx, cy = project((px, G.PLOT_Y, G.SOIL_Z + G.CROP_LIFT))
        pts = [project((px + sx * G.PLOT_W / 2, G.PLOT_Y + sy * G.PLOT_D / 2, z)) for sx in (-1, 1) for sy in (-1, 1)
               for z in (G.FLOOR, G.SOIL_Z + 0.6)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        plots.append({"slot": i, "crop_center": [cx, cy], "crop_x": round(cx - win / 2, 1), "crop_y": round(cy - win / 2, 1),
                      "tap_rect": [round(min(xs)), round(min(ys)), round(max(xs) - min(xs)), round(max(ys) - min(ys))]})
    pet = pet_entry(G.HIPPO, ppu, "garden_idle / garden_cheer (25°)")
    pet["z_note"] = "pet stands behind the middle plot: draw pet, then the crop images (crops overlap its feet)"
    clear_scene_meshes(HIPPO_OBJS)
    return {"canvas": [SIZE, SIZE], "background": "garden/background.png", "px_per_unit": ppu,
            "crop_image_size": [win, win], "crops": {n: f"garden/crops/{n}.png" for n in crops},
            "crop_files": "mound = planted (stage 0, all crops); <crop>_<1|2|3>[_doze]; draw at plots[i].crop_x/crop_y, size crop_image_size",
            "plots": plots, "pet": pet,
            "draw_order": ["background", "pet", "crops (plot 0, 1, 2)", "UI: progress dots, Zzz, sparkle"]}


if __name__ == "__main__":
    manifest = {"version": 1, "units": "px on the canvas; scale everything by (card width / canvas width)",
                "made_by": "scripts/blender/export_world.py", "spaces": {}}
    mp = os.path.join(OUT, "manifest.json")
    if os.path.exists(mp):
        manifest = json.load(open(mp))
    if WHAT in ("room", "all"):
        manifest["spaces"]["room"] = export_room()
    if WHAT in ("garden", "all"):
        manifest["spaces"]["garden"] = export_garden()
    json.dump(manifest, open(mp, "w"), ensure_ascii=False, indent=1)
    print("MANIFEST", mp)
