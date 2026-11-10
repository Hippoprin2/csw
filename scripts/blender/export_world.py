# Export room + garden art for the app: backgrounds, per-item layers (item + its own soft shadow), crop images,
# harvest decorations, and a manifest with pixel positions, draw order and the pet anchor.
# usage: blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/export_world.py -- <out_dir> [room|garden|yard|walk|all]
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
import yard as Y

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
    return round(v.x * sc.render.resolution_x, 1), round((1 - v.y) * sc.render.resolution_y, 1)


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


# ------------------------------------------------------------------ walking (yard + garden): ground polygon helpers
def ground_px(x, y):
    return list(project((x, y, R.FLOOR)))


def px_to_ground(u, v):
    """inverse of ground_px (ortho camera -> affine on the ground plane)"""
    p0, px_, py_ = Vector(ground_px(0, 0)), Vector(ground_px(1, 0)), Vector(ground_px(0, 1))
    a, b = px_ - p0, py_ - p0
    det = a.x * b.y - a.y * b.x
    du, dv = u - p0.x, v - p0.y
    return ((du * b.y - dv * b.x) / det, (a.x * dv - a.y * du) / det)


def clip_poly(poly, inside, cross):
    """Sutherland-Hodgman against one half-plane"""
    out = []
    for i, cur in enumerate(poly):
        prev = poly[i - 1]
        if inside(cur):
            if not inside(prev): out.append(cross(prev, cur))
            out.append(cur)
        elif inside(prev):
            out.append(cross(prev, cur))
    return out


def walk_area(world_y_min, world_y_max, x_margin, y_top, y_bottom):
    """screen rect [x_margin, SIZE-x_margin] x [y_top, y_bottom] (feet positions) ∩ world y range -> polygon (px)"""
    poly = [(x_margin, y_top), (SIZE - x_margin, y_top), (SIZE - x_margin, y_bottom), (x_margin, y_bottom)]
    for lim, keep_below in ((world_y_max, True), (world_y_min, False)):
        f = lambda p: px_to_ground(*p)[1]
        inside = (lambda p, l=lim: f(p) <= l) if keep_below else (lambda p, l=lim: f(p) >= l)
        def cross(a, b, l=lim):
            fa, fb = f(a), f(b); t = (l - fa) / (fb - fa)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        poly = clip_poly(poly, inside, cross)
    return [[round(u, 1), round(v, 1)] for u, v in poly]


def ellipse_px(cx, cy, rx, ry, n=12):
    return [[round(c, 1) for c in ground_px(cx + rx * math.cos(k / n * math.tau), cy + ry * math.sin(k / n * math.tau))] for k in range(n)]


def rect_px(cx, cy, hx, hy):
    return [[round(c, 1) for c in ground_px(cx + sx * hx, cy + sy * hy)] for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def feet_rule(ppu):
    c = project((0, 0, 0.07)); f = project((0, 0, R.FLOOR))
    s = ppu / CLIP_PX_PER_UNIT
    return {"feet_to_center": [round(c[0] - f[0], 1), round(c[1] - f[1], 1)], "w": round(600 * s, 1), "h": round(800 * s, 1),
            "note": "pet feet at (fx, fy) -> draw the 600x800 clip scaled to w x h centred at (fx, fy) + feet_to_center; "
                    "sort key = fy"}


# ------------------------------------------------------------------ garden walk data (no re-render)
def garden_walk():
    global sc, cam
    sc, cam = R.setup_render(SIZE, SIZE, G.ORTHO)
    cam.location = G.TARGET + G.cam_dir() * 12
    cam.rotation_euler = (G.TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    ppu = SIZE / G.ORTHO
    plot_back = G.PLOT_Y + G.PLOT_D / 2
    return {
        "area": walk_area(plot_back + 0.3, 0.98, 110, 0, SIZE),
        "blocked": {"sign": ellipse_px(1.0, 0.95, 0.2, 0.1), "watering_can": ellipse_px(-1.25, 0.75, 0.16, 0.12)},
        "home": [round(c, 1) for c in ground_px(*G.HIPPO)],
        "plot_stand": [[round(c, 1) for c in ground_px(px, plot_back + 0.35)] for px in G.PLOT_X],
        "pet": feet_rule(ppu),
        "rules": "the pet only walks the strip behind the plots (crops are drawn after the pet, so they never hide behind it). "
                 "Harvest: walk to plot_stand[i], face front, cheer. Tap on the grass -> walk to the nearest point inside "
                 "`area` that is not in `blocked`.",
        "world": {"y_range": [round(plot_back + 0.3, 2), 0.98], "units": "hippo height = 1"},
    }


# ------------------------------------------------------------------ yard
YARD_NIGHT_OVERLAY = [26, 34, 80, 0.38]
YARD_TILE = 1080
YARD_PEEK = 260                      # camera may look this far into a neighbouring locked zone (see the fence + scenery)
YARD_GROUND = ("picnic_mat",)        # flat: drawn under everything that sorts by y (pet sits on it)


def night_sky(B):
    """day background -> night version: sky pixels become a navy gradient with stars + moon (ground untouched,
    the app lays the night overlay over everything)"""
    Bn = B.copy()
    a = Bn[..., 3:4]
    h, W = Bn.shape[:2]
    t = (np.arange(h, dtype=np.float32) / 1080)[:, None, None]
    top, bot = np.array([0.16, 0.20, 0.42]), np.array([0.36, 0.40, 0.66])
    sky = top + (bot - top) * np.clip(t / 0.35, 0, 1)
    sky = np.broadcast_to(sky, (h, W, 3)).copy()
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:h, 0:W]
    for _ in range(int(46 * W / 1080)):
        sx, sy, r = rng.uniform(0, W), rng.uniform(0, 260), rng.uniform(1.6, 3.4)
        d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
        sky += np.clip(1 - d / r, 0, 1)[..., None] * np.array([1.0, 0.97, 0.85]) * 0.9
    mx, my, mr = 860, 110, 46            # crescent moon
    d1 = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2); d2 = np.sqrt((xx - mx - 20) ** 2 + (yy - my + 12) ** 2)
    moon = np.clip((mr - d1) / 2, 0, 1) * np.clip((d2 - mr * 0.92) / 2, 0, 1)
    halo = np.clip(1 - d1 / (mr * 2.6), 0, 1) ** 2 * 0.25
    sky = sky * (1 - moon[..., None]) + np.array([1.0, 0.95, 0.78]) * moon[..., None] + halo[..., None] * np.array([1.0, 0.95, 0.8])
    Bn[..., :3] = Bn[..., :3] * a + np.clip(sky, 0, 1) * (1 - a); Bn[..., 3] = 1.0
    return Bn


def add_glow(L, cx, cy, r, col=(1.0, 0.86, 0.5), strength=0.55):
    """note: the halo must stay inside the crop box -> crop is computed after adding it"""
    """warm halo (premultiplied-over) around a lit lamp, baked into the night layer"""
    yy, xx = np.mgrid[0:L.shape[0], 0:L.shape[1]]
    g = (np.clip(1 - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r, 0, 1) ** 2 * strength)[..., None]
    a = L[..., 3:4]
    out_a = a + g * (1 - a)
    rgb = np.where(out_a > 1e-4, (L[..., :3] * a + np.array(col) * g * (1 - a)) / np.maximum(out_a, 1e-4), 0)
    return np.concatenate([rgb, out_a], axis=2)


def export_yard():
    global sc, cam
    # Canvas = the whole yard (all zones), px = canvas px (Y.px). Background is rendered once for the full canvas
    # and cut into 1080-px tiles; items (all in zone 1) are rendered with the camera on the zone 1 rect, which starts
    # at canvas (0,0), so render px == canvas px for every pass.
    sc, cam = R.setup_render(SIZE, SIZE, Y.ORTHO)
    sc.frame_set(1); hide(HIPPO_OBJS)
    d = os.path.join(OUT, "yard"); os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.endswith(".png"): os.remove(os.path.join(d, f))
    ppu = Y.PPU
    bg = Y.background(); bg_objs = meshes(bg)
    sky = np.array([0xCD, 0xE8, 0xF5], dtype=np.float32) / 255.0
    CW, CH = Y.CANVAS
    Y.place_cam_rect(sc, cam, (0, 0, CW, CH))
    B = render(os.path.join(TMP, "yard_B.png"))
    Bo = B.copy(); a = Bo[..., 3:4]
    Bo[..., :3] = Bo[..., :3] * a + sky * (1 - a); Bo[..., 3] = 1.0
    Bn = night_sky(B)
    tiles = []
    for ty in range(0, CH, YARD_TILE):
        for tx in range(0, CW, YARD_TILE):
            w_, h_ = min(YARD_TILE, CW - tx), min(YARD_TILE, CH - ty)
            nm = f"bg_{ty // YARD_TILE}_{tx // YARD_TILE}"
            save_png(Bo[ty:ty + h_, tx:tx + w_], os.path.join(d, nm + ".png"))
            save_png(Bn[ty:ty + h_, tx:tx + w_], os.path.join(d, nm + "_night.png"))
            tiles.append({"file": f"yard/{nm}.png", "night_file": f"yard/{nm}_night.png", "x": tx, "y": ty, "w": w_, "h": h_})
    save_png(Bo[::4, ::4], os.path.join(TMP, "yard_full_small.png"))
    only = os.environ.get("ONLY", "").split(",") if os.environ.get("ONLY") else None

    # ---- locked-zone fences (drawn only while that zone is not bought), full-canvas camera
    locks = {}
    for z, mk in Y.LOCKS.items():
        g = mk()
        hide(bg_objs); I = render(os.path.join(TMP, "I.png")); hide(bg_objs, False)
        L = layer(I, shadow_pass(os.path.join(TMP, "S.png"), bg_objs, meshes(g))); remove(g)
        x, y, w, h = crop_bbox(L)
        save_png(L[y:y + h, x:x + w], os.path.join(d, f"lock_{z}.png"))
        locks[z] = {"file": f"yard/lock_{z}.png", "x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        print("YARD lock", z, x, y, w, h)
    Y.place_cam_rect(sc, cam, Y.ZONES[1]["rect"])

    def shoot(name, g, union=None, glow=None):
        hide(bg_objs); I = render(os.path.join(TMP, "I.png")); hide(bg_objs, False)
        S = shadow_pass(os.path.join(TMP, "S.png"), bg_objs, meshes(g))
        L = layer(I, S)
        if glow: L = add_glow(L, *glow)
        box = union or crop_bbox(L)
        x, y, w, h = box
        save_png(L[y:y + h, x:x + w], os.path.join(d, f"{name}.png"))
        return box, L

    def entry(iid, file, box, sort_y, **kw):
        x, y, w, h = box
        e = {"id": iid, "file": f"yard/{file}.png", "x": int(x), "y": int(y), "w": int(w), "h": int(h), "sort_y": round(sort_y, 1)}
        e.update(kw); return e

    # ---- items
    items = []
    for iid in Y.ITEMS:
        if only and iid not in only: continue
        sx, sy = Y.SPOT[iid]
        foot = Y.FOOT[iid]
        sort_y = project((sx, sy - (foot[1] if foot else 0), R.FLOOR))[1]
        if iid in ("garden_lamp", "tent"):     # day + lit night versions share one crop box
            g = Y.ITEMS[iid]()
            hide(bg_objs); I = render(os.path.join(TMP, "I.png")); hide(bg_objs, False)
            Ld = layer(I, shadow_pass(os.path.join(TMP, "S.png"), bg_objs, meshes(g))); remove(g)
            g2 = Y.ITEMS[iid](lit=True)
            glow = None
            if iid == "garden_lamp":
                gx, gy = project((sx, sy, R.FLOOR + 0.55)); glow = (gx, gy, 130, (1.0, 0.85, 0.5), 0.7)
            else:
                gx, gy = project((sx, sy - 0.33, R.FLOOR + 0.18)); glow = (gx, gy, 170, (1.0, 0.85, 0.5), 0.55)
            hide(bg_objs); I = render(os.path.join(TMP, "I.png")); hide(bg_objs, False)
            S = shadow_pass(os.path.join(TMP, "S.png"), bg_objs, meshes(g2))
            Lr = layer(I, S)
            # night layer = the day layer already darkened by the night overlay + only the light the lamp adds
            # (drawn on top of the overlay, so it must not be a full-bright copy of the object)
            ov = np.array(YARD_NIGHT_OVERLAY[:3]) / 255.0; oa = YARD_NIGHT_OVERLAY[3]
            add = np.clip(Lr[..., :3] * Lr[..., 3:4] - Ld[..., :3] * Ld[..., 3:4], 0, 1)
            base = (Ld[..., :3] * (1 - oa) + ov * oa) * Ld[..., 3:4]
            a_ = np.maximum(Ld[..., 3:4], Lr[..., 3:4])
            lit_m = np.clip(add.sum(axis=2, keepdims=True) * 3, 0, 1)          # glowing glass/door keep full brightness
            rgb = (base + add) * (1 - lit_m) + Lr[..., :3] * Lr[..., 3:4] * lit_m
            Ln = np.concatenate([np.clip(rgb / np.maximum(a_, 1e-4), 0, 1), a_], axis=2)
            Ln = add_glow(Ln, *glow)
            m = np.maximum(Ld[..., 3], Ln[..., 3])
            box = crop_bbox(np.dstack([np.zeros_like(Ld[..., :3]), m]))
            x, y, w, h = box
            save_png(Ld[y:y + h, x:x + w], os.path.join(d, f"{iid}.png"))
            save_png(Ln[y:y + h, x:x + w], os.path.join(d, f"{iid}_night.png"))
            remove(g2)
            e = entry(iid, iid, box, sort_y, night_file=f"yard/{iid}_night.png")
        else:
            g = Y.ITEMS[iid](); box, _ = shoot(iid, g); remove(g)
            e = entry(iid, iid, box, sort_y)
        e["price"] = Y.PRICES[iid]; e["name_ko"] = Y.NAMES_KO[iid]
        e["layer"] = "ground" if iid in YARD_GROUND else ("pond" if iid == "duck_float" else "sorted")
        items.append(e)
        print("YARD", iid, e["x"], e["y"], e["w"], e["h"])
    # flowers planted in the flower bed: 3 spots x (tulip, sunflower)
    bed_flowers = []
    if not only or "bed" in only:
        for i in range(3):
            for kind in ("tulip", "sunflower"):
                g = Y.bed_flower(kind, i); box, _ = shoot(f"bed_{kind}_{i}", g); remove(g)
                fx, fy = Y.SPOT["flower_bed"]
                bed_flowers.append(entry(f"bed_{kind}_{i}", f"bed_{kind}_{i}", box,
                                         project((fx + Y.BED_SPOTS[i], fy - 0.02, R.FLOOR))[1], spot=i, flower=kind))
    # ---- memory tree stages + one fruit image + fruit positions per stage
    tree = []
    if not only or "tree" in only:
        tx, ty = Y.TREE
        for st in (1, 2, 3, 4):
            g = Y.memory_tree(st); box, _ = shoot(f"tree_{st}", g); remove(g)
            tree.append(entry(f"tree_{st}", f"tree_{st}", box, project((tx, ty - 0.1, R.FLOOR))[1], stage=st,
                              fruits=[[round(c, 1) for c in project(tuple(p))] for p in Y.fruit_points(st)]))
        # single fruit sprite centred on (0,0,0) world -> cropped; app centres it on each fruit point
        fr = Y.sph("Fruit", 0.055, (0, 0, 0), Y.M("fruit", 0.45))
        parts = [fr, Y.sph("FruitBlush", 0.03, (0.02, -0.03, -0.015), Y.M("fruit2", 0.5), (1, 0.5, 1)),
                 Y.leaf("FruitLeaf", (0, 0, 0.045), 0.06, 0.035, 55, -19, Y.M("leaf")),
                 Y.sph("FruitShine", 0.012, (-0.02, -0.05, 0.025), Y.M("off", 0.3, 1.0))]
        hide(bg_objs); I = render(os.path.join(TMP, "I.png")); hide(bg_objs, False)
        cx, cy = project((0, 0, 0)); half = 40
        x0, y0 = int(round(cx - half)), int(round(cy - half))
        save_png(I[y0:y0 + 2 * half, x0:x0 + 2 * half], os.path.join(d, "fruit.png"))
        for o in parts: bpy.data.objects.remove(o, do_unlink=True)
    # ---- pond water (drawn over the pet's legs while it splashes) + guests
    extras = {}
    if not only or "extras" in only:
        water = [o for o in bg_objs if o.name.startswith(("PondWater", "PondDeep", "PondLily"))]
        others = [o for o in bg_objs if o not in water]
        hide(others); I = render(os.path.join(TMP, "I.png")); hide(others, False)
        box = crop_bbox(I); x, y, w, h = box
        save_png(I[y:y + h, x:x + w], os.path.join(d, "pond_water.png"))
        extras["pond_water"] = entry("pond_water", "pond_water", box, 0, note="draw over the pet only during `splash`")
        g = Y.sparrow("perch", Y.FEEDER_PERCH()); box, _ = shoot("sparrow_perch", g); remove(g)
        extras["sparrow_perch"] = entry("sparrow_perch", "sparrow_perch", box, 0, needs="bird_feeder",
                                        note="draw right after bird_feeder")
        g = Y.sparrow("ground", (0, 0, R.FLOOR)); box, _ = shoot("sparrow_ground", g); remove(g)
        f = project((0, 0, R.FLOOR))
        extras["sparrow_ground"] = entry("sparrow_ground", "sparrow_ground", box, 0,
                                         anchor=[round(f[0] - box[0], 1), round(f[1] - box[1], 1)],
                                         note="movable sprite: put `anchor` (feet, px inside the image) on any walkable point; sort by its y")
        for fr_ in ("open", "closed"):
            g = Y.butterfly(fr_, (0, 0, 0)); box, _ = shoot(f"butterfly_{fr_}", g); remove(g)
            c = project((0, 0, 0))
            extras[f"butterfly_{fr_}"] = entry(f"butterfly_{fr_}", f"butterfly_{fr_}", box, 0,
                                               anchor=[round(c[0] - box[0], 1), round(c[1] - box[1], 1)],
                                               note="2-frame flap (open/closed ~6 fps); float it around above the flower bed, drawn on top")

    # ---- walking data
    blocked = {"pond": ellipse_px(*Y.POND, Y.POND_R[0] + 0.12, Y.POND_R[1] + 0.1),
               "tree": ellipse_px(*Y.TREE, 0.2, 0.14)}
    item_blocked = {i: rect_px(*Y.SPOT[i], *Y.FOOT[i]) for i in Y.ITEMS if Y.FOOT[i]}
    interact = {}
    for i, (dx, dy, face, act) in Y.INTERACT.items():
        sx, sy = Y.SPOT[i]
        interact[i] = {"stand": [round(c, 1) for c in ground_px(sx + dx, sy + dy)], "face": face, "action": act}
    interact["pond"] = {"stand": [round(c, 1) for c in ground_px(Y.POND[0] - 0.05, Y.POND[1])], "face": "front", "action": "splash",
                        "note": "free (no item). Walk to the rim point `enter`, then hop to `stand`; draw pond_water over the pet"}
    interact["pond"]["enter"] = [round(c, 1) for c in ground_px(Y.POND[0] - Y.POND_R[0] - 0.15, Y.POND[1] - 0.05)]
    interact["tree"] = {"stand": [round(c, 1) for c in ground_px(Y.TREE[0] + 0.3, Y.TREE[1] - 0.3)], "face": "back",
                        "action": "show_fruit", "note": "free. tap a fruit -> pet walks here, then the memory card opens"}
    hippo_home = [round(c, 1) for c in ground_px(*Y.HIPPO)]
    # per-zone walkable polygons (canvas px, feet positions). Neighbouring zones share an edge, so the union of the
    # owned zones is one connected area. The stream is blocked except at the stepping stones.
    TOP = Y.HEDGE_Y + 170
    def band(pts, half, y0, y1):
        seg = [q for q in pts if y0 <= q[1] <= y1]
        return [[round(x - half, 1), round(y, 1)] for x, y in seg] + [[round(x + half, 1), round(y, 1)] for x, y in reversed(seg)]
    sy = Y.STONES2[0][1]
    zones = {}
    for z, Z in Y.ZONES.items():
        x, y, w, h = Z["rect"]
        e = {"rect": [x, y, w, h], "price": Z["price"], "name_ko": Z["name_ko"], "note": Z["note"]}
        if z == 1:
            # bottom-left corner left out: the crown of a zone-3 tree (baked into the background) reaches up there
            e["area"] = [[50, TOP], [1080, TOP], [1080, 1860], [230, 1860], [230, 1700], [50, 1700]]
            e["blocked"] = {}
        elif z == 2:
            e["area"] = [[1080, TOP], [2110, TOP], [2110, 1720], [1080, 1720]]     # stops above the zone-4 forest crowns
            e["blocked"] = {"stream_upper": band(Y.STREAM_PTS, 135, 0, sy - 45), "stream_lower": band(Y.STREAM_PTS, 135, sy + 45, 1900),
                            "willow": [[round(c, 1) for c in q] for q in ellipse_px(*Y.ground(*Y.WILLOW_PX), 0.2, 0.14)]}
            e["gate"] = list(Y.GATE2)
        elif z == 3:
            e["area"] = [[230, 1860], [1000, 1860], [1000, 2600], [230, 2600]]     # front tree row is baked in: keep the pet behind it
            e["blocked"] = {f"tree_{k}": ellipse_px(*Y.ground(*q), 0.18, 0.13) for k, q in enumerate(Y.FOREST3)}
            e["gate"] = list(Y.GATE3)
        else:
            e["area"] = None
        zones[str(z)] = e
    # background trees are baked into the tiles (not sorted), so every walk area stays where nothing baked is in front of the pet
    walk = {"zones": zones, "blocked": blocked, "item_blocked": item_blocked,
            "interact": interact, "home": hippo_home, "pet": feet_rule(ppu),
            "rules": "walkable = inside the `area` of any OWNED zone, outside `blocked` (all zones) and that zone's blocked, "
                     "outside item_blocked[id] for owned items. Keep feet >= 70 px away from an edge shared with a LOCKED zone "
                     "(the fence stands there). "
                     "Loop: idle 4-8 s -> walk to a random walkable point (usually in the zone the camera shows) -> every 3rd time go to "
                     "a random owned interact[id] (pond/tree are free) and play its action 5-10 s. Tap -> stop and walk to the tapped point "
                     "(nearest walkable point if outside). Tap on a locked zone / its gate -> zone purchase sheet. "
                     "interact stand points may lie inside item_blocked (the pet takes the last step in). "
                     "Walk speed ~ 0.6 unit/s = ppu*0.6 px/s. 4 directions = 3 clips (left = right mirrored)."}
    camera = {
        "viewport": "card width = 1080 canvas px; height = card height * 1080 / card width (≈1860 on iPhone 15, card from below "
                    "the space tabs to just above the tab bar)",
        "follow": "centre the viewport on the pet (feet + feet_to_center) with a soft follow (lerp ~0.12/frame, dead-zone 120 px)",
        "drag": "finger drag pans freely; after release wait 3 s, then glide back to the pet (~0.6 s ease-out). "
                "Tap = pet walks there (tap and drag never conflict)",
        "bounds": "clamp the viewport to the bounding box of the OWNED zone rects, extended by peek px into each locked neighbour "
                  "zone that shares an edge (so the fence + scenery beyond show). If the viewport is taller than the bounds, align to the top",
        "peek": YARD_PEEK,
        "open": "on enter: viewport centred on the pet, pet at `home` the first time",
    }
    clear_scene_meshes(HIPPO_OBJS)
    return {"canvas": [CW, CH], "tiles": tiles, "tile": YARD_TILE, "camera": camera, "locks": locks,
            "px_per_unit": ppu, "items": items, "bed_flowers": bed_flowers, "tree": tree,
            "fruit": {"file": "yard/fruit.png", "size": [80, 80], "note": "centre the image on each tree[stage].fruits point"},
            "extras": extras, "walk": walk,
            "night": {"hours": "19:00-06:00 local time = night, otherwise day",
                      "overlay": YARD_NIGHT_OVERLAY,
                      "draw": "background_night instead of background; draw everything as by day using <item>.night_file when it has one "
                              "(lit lamp / tent glow); then fill the canvas with `overlay` rgba EXCEPT the *_night lit layers, "
                              "which go on top of the overlay"},
            "draw_order": ["background tiles that intersect the viewport (night_file at night)", "locks[z] for every locked zone",
                           "layer=ground items (picnic_mat)",
                           "layer=pond (duck_float)", "tree[stage] + layer=sorted items + bed_flowers + pet + sparrow_ground, ascending sort_y "
                           "(pet sort key = feet y)", "sparrow_perch right after bird_feeder", "fruits right after tree[stage] (same sort slot as the tree, so a pet in front of the tree covers them)", "fruits on the tree",
                           "pond_water over the pet only while splashing", "butterfly", "night overlay"],
            "rules": "one of each item; all positions are fixed (no slots to swap in v1 of the yard). Zone 1 items only for now; "
                     "zone 2/3 items arrive with later updates and use the same entry format. "
                     "bed_flowers: spot i shows the flower the user planted there (tulip/sunflower), 3 spots."}


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
    if WHAT in ("garden", "all", "walk"):
        manifest["spaces"]["garden"]["walk"] = garden_walk()
    if WHAT in ("yard", "all"):
        manifest["spaces"]["yard"] = export_yard()
    json.dump(manifest, open(mp, "w"), ensure_ascii=False, indent=1)
    print("MANIFEST", mp)
