# Wide room (방 좌우 확장, 2026-11-10 대표 결정) — concept preview.
# Same camera/elev/px-per-unit as the 1080 room; canvas widened to WIDE x 1080 so existing item layers keep their
# positions (shifted by OFFSET_X px). Left extension = door to the garden, right extension = glass cabinet (유리장)
# holding closed jars (one jar per 50 marbles, app draws as many as the user has closed).
# usage:
#   blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/room_wide.py -- preview <out.png> <closed_jars> [all|none|a|b|ids...]
import bpy, math, os, random, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import room as R
from room import M, P, rbox, sph, cyl, group, lathe, FLOOR, YB
from props import mat

SCREENS = 2.0      # 2026-11-11 대표 결정 R1: 양쪽으로 화면 0.5장씩
WIDE = int(round(1080 * SCREENS / 2) * 2)          # 2160
ORTHO_W = R.ORTHO * SCREENS                         # 4.32 units visible width
OFFSET_X = (WIDE - 1080) // 2                       # original 1080 frame sits in the middle (start view = hippo centred)

P.update({
    "cab_back": (0.88, 0.95, 0.91),     # pale mint back panel so jars read
    "glass": (0.86, 0.94, 0.97),
    "jar_rim": (0.85, 0.79, 0.69),      # #d9c9b1 (app jar border)
    "lid": (0.80, 0.62, 0.45),          # wood2 cork lid
    "door": (0.80, 0.62, 0.45), "door2": (0.86, 0.69, 0.50),
    "grass_win": (0.62, 0.84, 0.60),
})
# app category colours (mobile/src/lib/categories.ts) for marbles
CAT_COLS = ["#9ccfd8", "#f6b26b", "#a4c2f4", "#b4a7d6", "#f9cb9c", "#d5a6bd", "#ea9999", "#b6d7a8", "#c3c8d6"]
for i, h in enumerate(CAT_COLS):
    P[f"cat{i}"] = tuple(int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))


def glass_mat(name, rgb, alpha):
    m = mat(name, rgb, 0.1, alpha=alpha)
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    m.use_backface_culling = True
    return m


# ------------------------------------------------------------------ jar (닫은 유리병)
JAR_W, JAR_H = 0.13, 0.175      # outer width, height incl. lid


JAR_BODY_H = JAR_H - 0.045
JAR_INNER = dict(r=JAR_W / 2 * 0.72, z0=0.012, z1=JAR_BODY_H - 0.03)   # where marbles sit (app draws them, R4)


def jar(name, loc, seed=0, marbles=True, part="all"):
    """closed jar. part: all | back (see-through glass body) | front (rim + cork lid + coral band + shine).
    marbles = category colours (preview only; the app draws real per-jar colours between back and front)"""
    x, y, z = loc
    r = JAR_W / 2
    body_h = JAR_BODY_H
    parts = []
    if part in ("all", "back"):
        prof = [(0.0, 0.0), (r * 0.82, 0.0), (r, 0.03), (r, body_h - 0.035), (r * 0.78, body_h - 0.01), (r * 0.72, body_h)]
        g = lathe(name + "Glass", prof, glass_mat("R_jarglass", P["glass"], 0.14))
        g.location = (x, y, z); parts.append(g)
    if part in ("all", "front"):
        parts += [cyl(name + "Rim", r * 0.78, 0.022, (x, y, z + body_h + 0.004), M("jar_rim", 0.6), bevel=0.35),
                  cyl(name + "Lid", r * 0.8, 0.035, (x, y, z + body_h + 0.03), M("lid", 0.8), bevel=0.35),
                  cyl(name + "Band", r * 0.83, 0.014, (x, y, z + body_h + 0.022), M("coral", 0.8), bevel=0.3)]
        sh = rbox(name + "Shine", (0.008, 0.003, body_h * 0.5), (x - r * 0.55, y - r - 0.004, z + body_h * 0.55), glass_mat("R_jarshine", P["off"], 0.45), r=0.45)
        parts.append(sh)
    if marbles and part == "all":
        rnd = random.Random(seed)
        w = [rnd.random() ** 5 for _ in CAT_COLS]
        mr = 0.015
        k = 0
        for layer in range(5):
            zz = z + 0.012 + mr + layer * mr * 1.7
            ring = r * 0.78 - mr
            n = 9
            for j in range(n):
                a = 2 * math.pi * j / n + layer * 0.35
                c = rnd.choices(range(len(CAT_COLS)), w)[0]
                parts.append(sph(f"{name}M{k}", mr, (x + ring * math.cos(a), y + ring * math.sin(a), zz), M(f"cat{c}", 0.45), seg=12))
                k += 1
            c = rnd.choices(range(len(CAT_COLS)), w)[0]
            parts.append(sph(f"{name}M{k}", mr, (x, y, zz), M(f"cat{c}", 0.45), seg=12)); k += 1
    return parts


# ------------------------------------------------------------------ glass cabinet (유리장)
CAB = dict(x=1.95, w=0.74, d=0.27, h=1.46, base=0.36, cols=4, rows=3)


def glass_cabinet(closed=0, split=False):
    """returns (body_group, front_group or None, slots). split=True: glass doors in their own group (drawn over the jars)"""
    c = CAB; x, w, d, h = c["x"], c["w"], c["d"], c["h"]
    y = YB - d / 2 - 0.01
    leg = 0.06
    zb = FLOOR + leg
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl(f"CabLeg{sx}{sy}", 0.022, leg + 0.01, (x + sx * (w / 2 - 0.05), y + sy * (d / 2 - 0.05), FLOOR + leg / 2), M("wood2"), r2=0.017))
    lo = c["base"]                      # closed wooden cupboard under the glass part (keeps jars above the input bar)
    parts.append(rbox("CabBack", (w - 0.04, 0.03, h - lo - 0.04), (x, YB - 0.03, zb + lo + (h - lo) / 2), M("cab_back", 0.85, 0.12), r=0.3))
    for sx in (-1, 1):
        parts.append(rbox(f"CabSide{sx}", (0.05, d, h), (x + sx * (w / 2 - 0.025), y, zb + h / 2), M("wood"), r=0.35))
    parts.append(rbox("CabLower", (w - 0.02, d, lo), (x, y, zb + lo / 2), M("wood"), r=0.25))
    for sx in (-1, 1):
        parts.append(rbox(f"CabLowDoor{sx}", (w / 2 - 0.06, 0.02, lo - 0.08), (x + sx * (w / 4 - 0.008), y - d / 2 - 0.006, zb + lo / 2), M("wood2"), r=0.3))
        parts.append(sph(f"CabLowKnob{sx}", 0.016, (x + sx * 0.04, y - d / 2 - 0.022, zb + lo / 2 + 0.03), M("coral", 0.6)))
    parts.append(rbox("CabTop", (w + 0.06, d + 0.04, 0.06), (x, y, zb + h), M("wood"), r=0.4))
    parts.append(rbox("CabCrown", (w - 0.12, 0.04, 0.07), (x, YB - 0.04, zb + h + 0.06), M("wood2"), r=0.45))
    inner0, inner1 = zb + lo + 0.02, zb + h - 0.03
    step = (inner1 - inner0) / c["rows"]
    shelf_z = [inner0 + i * step for i in range(c["rows"])]
    parts.append(rbox("CabShelfL", (w - 0.06, d - 0.02, 0.035), (x, y, inner0 - 0.005), M("wood"), r=0.35))
    for i, sz in enumerate(shelf_z[1:]):
        parts.append(rbox(f"CabShelf{i}", (w - 0.08, d - 0.04, 0.03), (x, y, sz), M("wood"), r=0.35))
    # glass doors: two very light panes + slim frames + one faint streak each
    fy = y - d / 2 - 0.012
    gz0, gz1 = zb + lo, zb + h - 0.03
    body = parts; front = []; parts = front
    for sx in (-1, 1):
        cx = x + sx * (w / 4 - 0.006)
        parts.append(rbox(f"CabPane{sx}", (w / 2 - 0.05, 0.006, gz1 - gz0 - 0.04), (cx, fy, (gz0 + gz1) / 2), glass_mat("R_cabglass", P["glass"], 0.05), r=0.2))
        st = rbox(f"CabShine{sx}", (0.01, 0.003, 0.22), (cx - 0.04, fy - 0.005, gz1 - 0.2), glass_mat("R_shine", P["off"], 0.35), r=0.4)
        st.rotation_euler = (0, math.radians(28), 0); parts.append(st)
        for sz in (gz0 + 0.015, gz1 - 0.015):
            parts.append(rbox(f"CabRailH{sx}{sz:.2f}", (w / 2 - 0.03, 0.02, 0.03), (cx, fy - 0.004, sz), M("wood2"), r=0.4))
        parts.append(sph(f"CabKnob{sx}", 0.016, (x + sx * 0.035, fy - 0.02, gz0 + 0.12), M("coral", 0.6)))
    parts.append(rbox("CabMullion", (0.03, 0.02, gz1 - gz0), (x, fy - 0.004, (gz0 + gz1) / 2), M("wood2"), r=0.4))
    # jar slots (row 0 = top, left -> right) — the app fills them in this order
    slots = []
    pitch = (w - 0.14) / c["cols"]
    for row in range(c["rows"]):
        sz = shelf_z[c["rows"] - 1 - row] + 0.015
        for col in range(c["cols"]):
            sx_ = x - (w - 0.14) / 2 + pitch * (col + 0.5)
            slots.append((sx_, y + 0.01, sz))
    for k, s in enumerate(slots[:closed]):
        body += jar(f"Jar{k}", s, seed=k + 3)
    if split:
        return group("glass_cabinet", body), group("glass_cabinet_front", front), slots
    return group("glass_cabinet", body + front), None, slots


# ------------------------------------------------------------------ door to the garden (left extension, free)
def garden_door():
    x = -2.6; w, h = 0.56, 1.28
    zb = FLOOR
    parts = [
        rbox("DoorFrame", (w + 0.1, 0.06, h + 0.06), (x, YB - 0.015, zb + (h + 0.06) / 2), M("off", 0.7), r=0.2),
        rbox("Door", (w, 0.05, h), (x, YB - 0.04, zb + h / 2), M("door2", 0.8), r=0.12),
        rbox("DoorPanelLo", (w - 0.16, 0.02, 0.34), (x, YB - 0.07, zb + 0.28), M("door", 0.8), r=0.3),
        cyl("DoorWin", 0.12, 0.03, (x, YB - 0.07, zb + h - 0.33), M("off", 0.7), bevel=0.3, rot=(math.radians(90), 0, 0)),
        cyl("DoorWinG", 0.095, 0.03, (x, YB - 0.075, zb + h - 0.33), M("grass_win", 0.5, 0.5), bevel=0.3, rot=(math.radians(90), 0, 0)),
        sph("DoorKnob", 0.025, (x + w / 2 - 0.08, YB - 0.09, zb + 0.6), M("yellow", 0.5)),
        rbox("DoorMat", (0.62, 0.32, 0.02), (x + 0.02, YB - 0.3, FLOOR + 0.01), M("coral", 0.9), r=0.4),
        # little sprout sign = "텃밭으로"
        rbox("DoorSign", (0.16, 0.02, 0.1), (x, YB - 0.075, zb + h - 0.62), M("off", 0.8), r=0.3),
        sph("DoorSprout", 0.02, (x - 0.02, YB - 0.09, zb + h - 0.61), M("leaf"), (1.2, 0.4, 0.8)),
        sph("DoorSprout2", 0.02, (x + 0.02, YB - 0.09, zb + h - 0.61), M("leaf"), (1.2, 0.4, 0.8)),
    ]
    # watering can by the door (garden hint)
    parts += [cyl("CanBody", 0.07, 0.12, (x + 0.42, YB - 0.22, FLOOR + 0.06), M("sky", 0.6), bevel=0.25),
              cyl("CanSpout", 0.012, 0.13, (x + 0.5, YB - 0.22, FLOOR + 0.11), M("sky", 0.6), bevel=0.2, rot=(0, math.radians(55), 0)),
              cyl("CanTop", 0.04, 0.02, (x + 0.42, YB - 0.22, FLOOR + 0.13), M("blue", 0.6), bevel=0.3)]
    return group("garden_door", parts)


def project_px(p, cam_target):
    """world -> wide-canvas px (ortho, fixed 3/4 direction)"""
    d = Vector((0.35, -1, R.ELEV)).normalized()
    right = Vector((1, 0.35, 0)).normalized()
    up = d.cross(right).normalized()
    if up.z < 0: up = -up
    v = Vector(p) - cam_target
    ppu = WIDE / ORTHO_W
    return WIDE / 2 + v.dot(right) * ppu, 540 - v.dot(up) * ppu


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode, out, closed = argv[0], argv[1], int(argv[2])
    ids = argv[3:] or ["all"]
    ids = {"all": R.SET_A, "a": R.SET_A, "b": R.SET_B, "none": []}.get(ids[0], ids) if len(ids) == 1 else ids
    sc, cam = R.setup_render(WIDE, 1080, ORTHO_W)
    cam.location = R.TARGET + Vector((0.35, -1, R.ELEV)).normalized() * 12
    cam.rotation_euler = (R.TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.frame_set(1)
    R.W = 3.0                      # wider floor / wall strips (base() only uses W for widths)
    R.base(); R.calendar()
    for hv in os.environ.get("HARVEST", "sweet_potato").split(","):
        if hv: R.HARVEST[hv]()
    for i in ids:
        R.ITEMS[i]()
    _, _, slots = glass_cabinet(closed)
    garden_door()
    bpy.data.objects["HippoRig"].location = (*R.HIPPO, 0)
    sc.render.filepath = os.path.abspath(out)
    bpy.ops.render.render(write_still=True)
    print("SLOTS_PX", [tuple(round(v) for v in project_px((sx, sy, sz + JAR_H / 2), R.TARGET)) for sx, sy, sz in slots])
    print("WROTE", out)
