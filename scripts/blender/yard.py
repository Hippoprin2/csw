# Yard (마당) scene — first update. Base (grass, hedges, path, pond) + memory tree stages + yard items keyed by app
# item id + guests (sparrow, butterfly). Camera elev 0.5 (≈25°) like the garden, visible width 2.7 (same hippo size).
# usage:
#   blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/yard.py -- preview <out.png> [ids...|all|none]
#       env TREE=1..4 (memory tree stage, default 4), FRUITS=1 (show memory fruits), BED=tulip,sunflower,tulip (flower bed),
#           HIPPO=x,y (pet position), GUESTS=1
#   ... -- thumbs <out_dir> [ids...]     shop thumbnails 512² (same framing rule as room.py thumbs)
#   ... -- layout                        print screen-space checks (frame bounds on the ground, item anchors)
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import room as R
import garden as G
from room import rbox, sph, cyl, M, P, group, setup_render, frame_on, item_parts, bake, lathe, _link
from garden import tube, leaf, apply_tf

FLOOR = -0.5
ELEV = 0.5
TARGET = Vector((-0.15, 0.55, 0.0))
ORTHO = 2.7

P.update({
    "water": (0.60, 0.83, 0.93), "water2": (0.50, 0.76, 0.90), "sand": (0.93, 0.87, 0.74),
    "fruit": (1.0, 0.66, 0.45), "fruit2": (0.98, 0.56, 0.42), "blossom": (1.0, 0.80, 0.85),
    "tent": (0.82, 0.80, 0.90), "tent2": (0.70, 0.66, 0.84), "duck": (1.0, 0.86, 0.35),
    "bird": (0.74, 0.54, 0.38), "bird2": (0.60, 0.42, 0.30), "lamp_glass": (1.0, 0.93, 0.70),
    "lily": (0.46, 0.74, 0.50), "lime": (0.66, 0.82, 0.46), "red": (0.92, 0.38, 0.36),
})

# ------------------------------------------------------------------ world canvas (2026-11-10: portrait viewport + zones)
# The yard is one big pre-rendered canvas; the app shows a 1080-px-wide window of it (card down to the tab bar,
# ≈1080×1860) and moves that window with the pet. Canvas px are the shared coordinate system for everything
# (items, walk data, zones). Zone 1's top-left = canvas (0,0); the old square framing = canvas (0,0)-(1080,1080).
PPU = 400                                   # px per world unit (same hippo size as room/garden)
CANVAS = (2160, 3100)
ZONES = {   # rect = (x, y, w, h) in canvas px
    1: {"rect": (0, 0, 1080, 1860), "price": 0, "name_ko": "집 앞마당", "note": "free when the yard opens"},
    2: {"rect": (1080, 0, 1080, 1860), "price": 60, "name_ko": "개울가", "note": "bought with seeds; its items ship with update 2"},
    3: {"rect": (0, 1860, 1080, 1240), "price": 120, "name_ko": "꽃언덕 숲길", "note": "bought with seeds; its items ship with a later update"},
    4: {"rect": (1080, 1860, 1080, 1240), "price": None, "name_ko": "숲", "note": "scenery only (not walkable, not for sale yet)"},
}
_D = Vector((0.35, -1, ELEV)).normalized()          # target -> camera
RX = Vector((1, 0.35, 0)).normalized()              # screen right
UP = RX.cross(-_D).normalized()                     # screen up


def px(p):
    """world -> canvas px (exact for the ortho camera)"""
    d = Vector(p) - TARGET
    return (540 + PPU * d.dot(RX), 540 - PPU * d.dot(UP))


def ground(X, Y, z=FLOOR):
    """canvas px -> world point on the plane z"""
    a, b = PPU * RX.x, PPU * RX.y
    c, d = -PPU * UP.x, -PPU * UP.y
    A = X - 540 - PPU * (RX.z * (z - TARGET.z))
    B = Y - 540 + PPU * (UP.z * (z - TARGET.z))
    det = a * d - b * c
    dx, dy = (A * d - b * B) / det, (a * B - c * A) / det
    return (TARGET.x + dx, TARGET.y + dy)


# ------------------------------------------------------------------ zone 1 layout (canvas px of each footprint centre)
TREE_PX = (215, 790)
POND_PX = (700, 1095); POND_R = (0.55, 0.36)
SPOT_PX = {
    "mailbox": (300, 585), "tent": (770, 640), "bench": (480, 860), "bird_feeder": (960, 900),
    "hammock": (250, 1180), "picnic_mat": (430, 1440), "flower_bed": (790, 1470), "garden_lamp": (110, 1560),
    "pinwheel": (1000, 1290),
}
HIPPO_PX = (600, 1300)          # on the path, clear of the hammock post
TREE = ground(*TREE_PX)
POND = ground(*POND_PX)
SPOT = {k: ground(*v) for k, v in SPOT_PX.items()}
SPOT["duck_float"] = (POND[0] + 0.28, POND[1] + 0.05)
HIPPO = ground(*HIPPO_PX)       # default standing spot (also where the app spawns the pet)
HEDGE_Y = 470                   # back hedge row (screen-horizontal line)
GATE2 = (1085, 1265)            # zone 1 <-> 2 gate (path crossing)
GATE3 = (560, 1850)             # zone 1 <-> 3 gate
STREAM = [(1730, 430), (1660, 760), (1780, 1080), (1640, 1420), (1520, 1860), (1470, 2300), (1530, 2800), (1480, 3250)]
STREAM_R = 0.3
STONES2 = [(1460, 1262), (1560, 1268), (1650, 1262), (1745, 1270), (1850, 1262)]   # path across the stream
WILLOW_PX = (1985, 760)
HILL_PX = (700, 2330); HILL_R = (1.05, 0.7)
FOREST3 = [(50, 2000), (30, 2330), (60, 2660), (110, 3000), (380, 3160), (660, 3140), (930, 3170)]


def _catmull(pts, n=10):
    out = []
    P_ = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P_) - 2):
        p0, p1, p2, p3 = P_[i - 1], P_[i], P_[i + 1], P_[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(pts[-1])
    return out


STREAM_PTS = _catmull(STREAM, 12)
PATH1 = [(-40, 1300), (120, 1270), (300, 1240), (470, 1225), (640, 1255), (800, 1275), (960, 1268), (1085, 1265)]
PATH1B = [(640, 1255), (600, 1420), (610, 1600), (570, 1760), (560, 1850)]
PATH3 = [(560, 1850), (520, 2050), (420, 2300), (330, 2560), (290, 2800), (250, 3150)]


def ground_poly(name, pts_px, mat, z=FLOOR):
    bm = bmesh.new()
    vs = [bm.verts.new((*ground(*q, z), z)) for q in pts_px]
    bm.faces.new(vs)
    return _link(bm, name, mat, weighted=False)


def round_tree(name, X, Y, s=1.0, cols=("hedge", "leafd"), rnd=None):
    x, y = ground(X, Y)
    h = 0.35 * s
    parts = [cyl(f"{name}T", 0.06 * s, h, (x, y, FLOOR + h / 2), M("wood2"), r2=0.045 * s, bevel=0.2)]
    for k, (dx, dz, r) in enumerate(((0, 0.3, 0.36), (-0.24, 0.12, 0.26), (0.24, 0.14, 0.26), (0.02, 0.5, 0.24))):
        parts.append(sph(f"{name}C{k}", r * s, (x + dx * s, y, FLOOR + h + dz * s), M(cols[k % 2], 0.85), (1, 0.9, 0.95)))
    return parts


# ------------------------------------------------------------------ base (free)
def background(zones=(1, 2, 3, 4)):
    W, H = CANVAS
    grass = ground_poly("Grass", [(-400, HEDGE_Y - 10), (W + 600, HEDGE_Y - 10), (W + 600, H + 500), (-400, H + 500)], M("grass", 0.9))
    parts = [grass]
    rnd = random.Random(7)
    def free(X, Y):
        if ((X - POND_PX[0]) / 260) ** 2 + ((Y - POND_PX[1]) / 110) ** 2 < 1: return False
        if any(abs(X - a) < 150 and abs(Y - b) < 90 for a, b in SPOT_PX.values()): return False
        if min((X - a) ** 2 + (Y - b) ** 2 for a, b in STREAM_PTS) < 150 ** 2: return False
        if ((X - HILL_PX[0]) / 430) ** 2 + ((Y - HILL_PX[1]) / 140) ** 2 < 1: return False
        if X > 1080 and Y > 1900: return False
        return True
    for k in range(260):
        X, Y = rnd.uniform(0, W), rnd.uniform(HEDGE_Y + 70, H - 40)
        if not free(X, Y): continue
        gx, gy = ground(X, Y)
        if k % 3 == 0:
            parts.append(sph(f"Fl{k}", 0.018, (gx, gy, FLOOR + 0.012), M(rnd.choice(["petal_w", "pink", "sun_y"]), 0.7), (1, 1, 0.6)))
        else:
            parts.append(sph(f"Tuft{k}", 0.04, (gx, gy, FLOOR), M("grass2", 0.9), (1.3, 0.8, 0.45)))
    # back hedge row along the whole top + a few round trees peeking over it (sky stays open for the night)
    for k, X in enumerate(range(-160, W + 300, 290)):
        x, y = ground(X, HEDGE_Y)
        parts.append(sph(f"Hedge{k}", 0.46, (x, y, FLOOR + 0.3), M("hedge" if k % 2 else "hedge2", 0.85), (1.2, 0.8, 1.0)))
    for k, (X, s) in enumerate(((870, 0.42), (1300, 0.5), (2080, 0.46))):
        x, y = ground(X, HEDGE_Y - 150)
        parts.append(sph(f"Crown{k}", s, (x, y, FLOOR + 0.62 + s * 0.4), M("leafd" if k % 2 else "hedge", 0.85), (1.1, 0.85, 0.9)))
    # stepping-stone paths (from the room on the left -> home -> zone 2 gate; branch down to the zone 3 gate)
    k = 0
    for path, step in ((PATH1, 120), (PATH1B, 125)):
        pts = _catmull(path, 20)
        acc, last = 0, None
        for q in pts:
            if last is not None:
                acc += math.dist(q, last)
            last = q
            if acc >= step or k == 0:
                acc = 0; x, y = ground(*q)
                parts.append(sph(f"Stone{k}", 0.1, (x, y, FLOOR), M("pebble", 0.85), (1.3, 1.0, 0.22))); k += 1
    parts += pond()
    if 2 in zones: parts += zone2_base()
    if 3 in zones: parts += zone3_base()
    if 4 in zones: parts += zone4_base()
    for o in parts:
        if o.name.startswith(("Grass", "Pond", "Stream", "Bank", "Dirt", "Hill")):
            o.visible_shadow = False
    return group("YardBase", parts)


def zone2_base():
    """개울가: a stream from under the back hedge down into the forest, stepping stones, willow, reeds, rocks"""
    parts = []
    for i, q in enumerate(STREAM_PTS):
        x, y = ground(*q)
        b = cyl(f"Bank{i}", 1.0, 0.02, (x, y, FLOOR + 0.003), M("sand", 0.9), bevel=0.4); b.scale = (STREAM_R + 0.1, STREAM_R * 0.8 + 0.08, 1)
        w = cyl(f"StreamW{i}", 1.0, 0.02, (x, y, FLOOR + 0.012), M("water", 0.35), bevel=0.4); w.scale = (STREAM_R, STREAM_R * 0.8, 1)
        parts += [b, w]
        if i % 3 == 1:
            x2, y2 = ground(q[0] + 25, q[1] + 6)
            d = cyl(f"StreamD{i}", 1.0, 0.02, (x2, y2, FLOOR + 0.014), M("water2", 0.35), bevel=0.4); d.scale = (STREAM_R * 0.45, STREAM_R * 0.3, 1)
            parts.append(d)
    for k, q in enumerate(STONES2):
        x, y = ground(*q)
        parts.append(sph(f"SStone{k}", 0.13, (x, y, FLOOR + 0.02), M("pebble", 0.85), (1.25, 1.0, 0.35)))
    rnd = random.Random(11)
    for k in range(26):                 # reeds / cattails / rocks along the banks
        q = STREAM_PTS[rnd.randrange(4, len(STREAM_PTS) - 30)]
        side = rnd.choice((-1, 1))
        X, Y = q[0] + side * rnd.uniform(150, 190), q[1] + rnd.uniform(-20, 20)
        if abs(Y - 1265) < 70: continue
        x, y = ground(X, Y)
        if k % 3 == 0:
            parts.append(sph(f"Rock{k}", rnd.uniform(0.06, 0.1), (x, y, FLOOR + 0.02), M("pebble", 0.85), (1.3, 1.0, 0.6)))
        else:
            for j in range(3):
                h = rnd.uniform(0.16, 0.28)
                parts.append(cyl(f"Reed{k}_{j}", 0.008, h, (x + j * 0.025 - 0.025, y, FLOOR + h / 2), M("leafd", 0.8), bevel=0))
                if j == 1 and k % 2:
                    parts.append(sph(f"Cat{k}", 0.018, (x, y, FLOOR + h + 0.01), M("brown", 0.7), (1, 1, 2.4)))
    # willow: trunk + round crown + hanging fronds
    x, y = ground(*WILLOW_PX)
    parts.append(cyl("WilT", 0.08, 0.5, (x, y, FLOOR + 0.25), M("wood2"), r2=0.06, bevel=0.2))
    parts.append(sph("WilC", 0.42, (x, y, FLOOR + 0.82), M("lime", 0.85), (1.15, 1.0, 0.75)))
    for k in range(9):
        a = math.radians(-160 + k * 20)
        fx, fy = x + math.cos(a) * 0.38, y + math.sin(a) * 0.2 - 0.05
        parts.append(sph(f"WilF{k}", 0.07, (fx, fy, FLOOR + 0.6), M("lime" if k % 2 else "leaf", 0.85), (0.8, 0.6, 3.0)))
    # flowers on the far bank
    for k, (X, Y) in enumerate(((1250, 700), (1300, 1550), (2050, 1450), (1960, 1650), (1230, 980))):
        x, y = ground(X, Y)
        for j in range(4):
            parts.append(sph(f"BkFl{k}_{j}", 0.025, (x + (j % 2) * 0.06, y + (j // 2) * 0.05, FLOOR + 0.02), M(("pink", "lemon", "petal_w", "lav")[j], 0.7), (1, 1, 0.7)))
    return parts


def zone3_base():
    """꽃언덕 숲길: a low flower hill, a dirt path into the trees, mushrooms"""
    parts = []
    x, y = ground(*HILL_PX)
    parts.append(sph("Hill", 1.0, (x, y, FLOOR - 0.2), M("grass2", 0.9), (HILL_R[0], HILL_R[1], 0.42)))
    rnd = random.Random(5)
    for k in range(70):
        a = rnd.uniform(0, math.tau); rr = math.sqrt(rnd.uniform(0, 0.85))
        fx, fy = x + math.cos(a) * rr * HILL_R[0], y + math.sin(a) * rr * HILL_R[1]
        z = FLOOR - 0.2 + 0.42 * math.sqrt(max(0, 1 - rr * rr))
        parts.append(sph(f"HillFl{k}", 0.026, (fx, fy, z + 0.012), M(rnd.choice(["pink", "lemon", "petal_w", "lav", "sun_y"]), 0.7), (1, 1, 0.6)))
    for i, q in enumerate(_catmull(PATH3, 10)):
        px_, py_ = ground(*q)
        d = cyl(f"Dirt{i}", 1.0, 0.012, (px_, py_, FLOOR + 0.004), M("sand", 0.95), bevel=0.4); d.scale = (0.2, 0.15, 1); parts.append(d)
    for k, (X, Y) in enumerate(FOREST3):
        parts += round_tree(f"F3T{k}", X, Y, 0.85 + (k % 3) * 0.1, ("hedge", "leafd") if k % 2 else ("leafd", "hedge2"))
    for k, (X, Y) in enumerate(((180, 2150), (230, 2480), (860, 2750), (150, 2830))):
        mx, my = ground(X, Y)
        parts.append(cyl(f"MushS{k}", 0.018, 0.05, (mx, my, FLOOR + 0.025), M("off", 0.8), bevel=0))
        parts.append(sph(f"MushC{k}", 0.04, (mx, my, FLOOR + 0.055), M("red", 0.6), (1, 1, 0.6)))
    return parts


def zone4_base():
    parts = []
    rnd = random.Random(9)
    for k, (X, Y) in enumerate([(1290 + c * 200 + (r % 2) * 95 + rnd.uniform(-25, 25), 2160 + r * 250 + rnd.uniform(-25, 25))
                                for r in range(5) for c in range(5)]):
        if min(abs(X - qx) + abs(Y - qy) for qx, qy in STREAM_PTS) < 110: continue
        parts += round_tree(f"F4T{k}", X, Y, 0.78 + (k % 3) * 0.1, ("hedge", "leafd") if k % 2 else ("leafd", "hedge2"))
    return parts


def fence(name, a_px, b_px, gate_px):
    """low wooden fence between two canvas points with a closed gate at gate_px (drawn only while the zone is locked)"""
    parts = []
    A, B = Vector((*ground(*a_px), 0)), Vector((*ground(*b_px), 0)); G_ = Vector((*ground(*gate_px), 0))
    L = (B - A).length; dirv = (B - A).normalized()
    ang = math.atan2(dirv.y, dirv.x)
    n = int(L / 0.32)
    tg = (G_ - A).dot(dirv)
    for i in range(n + 1):
        t = i * L / n
        if abs(t - tg) < 0.22: continue
        p = A + dirv * t
        parts.append(rbox(f"{name}Post{i}", (0.05, 0.05, 0.24), (p.x, p.y, FLOOR + 0.12), M("wood", 0.8), r=0.012))
    for t0, t1 in ((0, tg - 0.24), (tg + 0.24, L)):
        if t1 - t0 < 0.05: continue
        c = A + dirv * ((t0 + t1) / 2)
        for h in (0.08, 0.17):
            rail = rbox(f"{name}Rail{t0:.1f}{h}", (t1 - t0, 0.025, 0.035), (c.x, c.y, FLOOR + h), M("wood", 0.8), r=0.008)
            rail.rotation_euler = (0, 0, ang); parts.append(rail)
    # gate: two posts + a little arch board, door closed
    for s in (-1, 1):
        p = G_ + dirv * (s * 0.22)
        parts.append(rbox(f"{name}GP{s}", (0.06, 0.06, 0.32), (p.x, p.y, FLOOR + 0.16), M("wood2", 0.8), r=0.015))
    door = rbox(f"{name}Door", (0.38, 0.03, 0.2), (G_.x, G_.y, FLOOR + 0.12), M("wood", 0.8), r=0.01); door.rotation_euler = (0, 0, ang); parts.append(door)
    knob = sph(f"{name}Knob", 0.018, (G_.x, G_.y - 0.03, FLOOR + 0.14), M("yellow", 0.5)); parts.append(knob)
    return group(name, parts)


LOCKS = {2: lambda: fence("Lock2", (1092, HEDGE_Y + 40), (1092, 1860), GATE2),
         3: lambda: fence("Lock3", (0, 1852), (1080, 1852), GATE3)}


def pond():
    """small free pond: sand rim, water, lily pad. PondWater is also exported alone (drawn over the pet when it splashes)."""
    x, y = POND; rx, ry = POND_R
    parts = []
    rim = cyl("PondRim", 1.0, 0.03, (x, y, FLOOR + 0.004), M("sand", 0.9), bevel=0.4); rim.scale = (rx + 0.09, ry + 0.08, 1); parts.append(rim)
    w = cyl("PondWater", 1.0, 0.02, (x, y, FLOOR + 0.012), M("water", 0.35), bevel=0.4); w.scale = (rx, ry, 1); parts.append(w)
    d = cyl("PondDeep", 1.0, 0.02, (x + 0.05, y + 0.04, FLOOR + 0.014), M("water2", 0.35), bevel=0.4); d.scale = (rx * 0.62, ry * 0.58, 1); parts.append(d)
    rnd = random.Random(3)
    for k in range(16):      # pebbles around the rim (colour detail)
        a = k / 16 * math.tau + rnd.uniform(-0.1, 0.1)
        if 3.6 < a < 5.0 and k % 2: continue
        parts.append(sph(f"PondPebble{k}", 0.035, (x + math.cos(a) * (rx + 0.1), y + math.sin(a) * (ry + 0.09), FLOOR + 0.02),
                         M("pebble", 0.85), (1.3, 1, 0.5)))
    lp = cyl("PondLily", 0.09, 0.008, (x - 0.32, y + 0.12, FLOOR + 0.026), M("lily", 0.7), bevel=0.3); lp.scale = (1, 0.8, 1); parts.append(lp)
    parts.append(sph("PondLilyFl", 0.03, (x - 0.31, y + 0.11, FLOOR + 0.04), M("pink", 0.7), (1, 1, 0.7)))
    return parts


# ------------------------------------------------------------------ memory tree (free, grows with recorded days)
TREE_STAGE = {   # trunk height, trunk radius, crown balls (dx, dz-above-trunk-top, r)
    1: (0.22, 0.022, []),
    2: (0.4, 0.04, [(0, 0.1, 0.2), (-0.1, 0.0, 0.14), (0.11, 0.02, 0.14)]),
    3: (0.5, 0.055, [(0, 0.16, 0.28), (-0.2, 0.02, 0.2), (0.2, 0.04, 0.2), (0.02, -0.06, 0.22)]),
    4: (0.58, 0.07, [(0, 0.22, 0.36), (-0.3, 0.04, 0.27), (0.3, 0.06, 0.27), (-0.12, -0.06, 0.27), (0.17, -0.05, 0.25),
                     (0.0, 0.48, 0.24)]),
}
FRUIT_SLOTS = {1: [], 2: [(0.05, -0.1)], 3: [(-0.18, -0.1), (0.12, -0.16), (0.25, 0.02)],
               4: [(-0.34, -0.05), (-0.1, -0.21), (0.18, -0.18), (0.36, 0.02), (0.06, 0.3)]}   # (dx, dz) on the crown front


def memory_tree(stage):
    x, y = TREE
    h, r, balls = TREE_STAGE[stage]
    parts = [cyl("TrTrunk", r, h, (x, y, FLOOR + h / 2), M("wood2"), r2=r * 0.75, bevel=0.2)]
    if stage == 1:   # sapling + little wooden stake with a ribbon
        parts += [leaf("TrL1", (x, y, FLOOR + h), 0.12, 0.07, -50, -19, M("leaf")), leaf("TrL2", (x, y, FLOOR + h), 0.12, 0.07, 50, -19, M("leafd")),
                  leaf("TrL3", (x, y, FLOOR + h - 0.06), 0.09, 0.06, -75, -19, M("leaf"))]
        parts.append(cyl("TrStake", 0.012, 0.3, (x + 0.08, y + 0.02, FLOOR + 0.15), M("wood"), bevel=0))
        parts.append(rbox("TrRibbon", (0.035, 0.03, 0.02), (x + 0.08, y + 0.0, FLOOR + 0.24), M("coral"), r=0.4))
        return group("tree_1", parts)
    if stage >= 3:   # root flare
        for k in range(3):
            a = math.radians(-100 + k * 110)
            ro = sph(f"TrRoot{k}", r * 1.2, (x + math.cos(a) * r * 1.1, y + math.sin(a) * r * 1.1, FLOOR + r * 0.3), M("wood2"), (1.6, 1, 0.55))
            ro.rotation_euler = (0, 0, a); parts.append(ro)
    top = FLOOR + h
    for k, (dx, dz, br) in enumerate(balls):
        parts.append(sph(f"TrCrown{k}", br, (x + dx, y + 0.04 * (k % 2), top + dz + br * 0.7),
                         M("leaf" if k % 2 else "leafd", 0.85), (1, 0.88, 0.92)))
    if stage == 4:   # a few soft blossoms (colour detail, not a reward size difference: every user reaches it with time)
        rnd = random.Random(11)
        for k in range(12):
            a = rnd.uniform(-1.2, 1.2); e = rnd.uniform(0.1, 0.9)
            dx, dz, br = balls[k % len(balls)]
            c = Vector((x + dx + math.sin(a) * br * 0.8, y - br * 0.7 * math.cos(a) * math.cos(e - 0.5), top + dz + br * 0.7 + (e - 0.5) * br))
            parts.append(sph(f"TrBlossom{k}", 0.028, c, M("blossom", 0.7), (1, 0.6, 1)))
    return group(f"tree_{stage}", parts)


def fruit_points(stage):
    """world positions of memory fruits on the crown's camera side"""
    x, y = TREE
    h = TREE_STAGE[stage][0]
    c = Vector((x, y, FLOOR + h + (0.24 if stage == 4 else 0.16 if stage == 3 else 0.1) + 0.16))
    d = Vector((0.35, -1, ELEV)).normalized()
    right = Vector((1, 0.35, 0)).normalized()
    up = d.cross(right).normalized()
    if up.z < 0: up = -up
    R0 = {2: 0.25, 3: 0.37, 4: 0.47}.get(stage, 0)
    return [c + right * dx + up * dz + d * R0 for dx, dz in FRUIT_SLOTS[stage]]


def memory_fruits(stage):
    parts = []
    for k, p in enumerate(fruit_points(stage)):
        parts.append(sph(f"Fruit{k}", 0.055, p, M("fruit", 0.45), (1, 1, 0.95)))
        parts.append(sph(f"FruitBlush{k}", 0.03, p + Vector((0.02, -0.03, -0.015)), M("fruit2", 0.5), (1, 0.5, 1)))
        parts.append(leaf(f"FruitLeaf{k}", tuple(p + Vector((0, 0, 0.045))), 0.06, 0.035, 55, -19, M("leaf")))
        parts.append(sph(f"FruitShine{k}", 0.012, p + Vector((-0.02, -0.05, 0.025)), M("off", 0.3, 1.0)))
    return group(f"fruits_{stage}", parts)


# ------------------------------------------------------------------ items (one builder per app item id)
def flower_bed():
    """화단 ★: oval bed with pebble edging; 3 spots for harvested flowers (flowers are separate layers, bed_flower())"""
    x, y = SPOT["flower_bed"]
    parts = []
    s = cyl("FbSoil", 1.0, 0.05, (x, y, FLOOR + 0.025), M("soil", 0.95), bevel=0.4); s.scale = (0.42, 0.24, 1); parts.append(s)
    for k in range(18):
        a = k / 18 * math.tau
        parts.append(sph(f"FbStone{k}", 0.045, (x + math.cos(a) * 0.44, y + math.sin(a) * 0.26, FLOOR + 0.03),
                         M("pebble" if k % 3 else "off", 0.85), (1.2, 1, 0.75)))
    for k, dx in enumerate((-0.24, 0.0, 0.24)):        # little planting holes
        parts.append(sph(f"FbHole{k}", 0.05, (x + dx, y + (0.04 if k == 1 else -0.02), FLOOR + 0.05), M("soil2", 0.95), (1.2, 1, 0.3)))
    return group("flower_bed", parts)


BED_SPOTS = (-0.24, 0.0, 0.24)


def bed_flower(kind, i):
    x, y = SPOT["flower_bed"]
    base = (x + BED_SPOTS[i], y + (0.04 if i == 1 else -0.02), FLOOR + 0.05)
    parts, h = G.CROPS[kind](base, 3)
    apply_tf(parts)
    b = Vector(base)
    for o in parts:
        for v in o.data.vertices:
            v.co = b + (v.co - b) * 0.8
        o.data.update()
    return group(f"bed_{kind}_{i}", parts)


def pinwheel():
    """바람개비: stick + 4 petal blades facing the camera"""
    x, y = SPOT["pinwheel"]
    top = Vector((x, y - 0.02, FLOOR + 0.5))
    parts = [cyl("PwStick", 0.012, 0.5, (x, y, FLOOR + 0.25), M("off", 0.7), bevel=0)]
    face = Matrix.Rotation(math.radians(-19), 3, "Z") @ Matrix.Rotation(math.radians(-90), 3, "X")
    for k, col in enumerate(("coral", "yellow", "sky", "mint")):
        a = k * math.pi / 2 + 0.4
        c = top + face @ Vector((math.cos(a) * 0.075, math.sin(a) * 0.075, 0))
        b = sph(f"PwBlade{k}", 0.075, c, M(col, 0.7), (1, 0.55, 0.12))
        b.rotation_euler = (face @ Matrix.Rotation(a, 3, "Z")).to_euler(); parts.append(b)
    parts.append(sph("PwPin", 0.02, top + Vector((0, -0.02, 0)), M("off", 0.6)))
    return group("pinwheel", parts)


def duck_float():
    """오리 튜브: yellow ring with a duck head, floating on the pond"""
    x, y = SPOT["duck_float"]; z = FLOOR + 0.03
    prof = [(0.08 + 0.045 * math.cos(t), 0.045 * math.sin(t)) for t in [k / 12 * math.tau for k in range(13)]]
    ring = lathe("DkRing", prof, M("duck", 0.6)); ring.location = (x, y, z + 0.02)
    parts = [ring]
    hx, hy = x - 0.11, y - 0.04
    parts += [sph("DkNeck", 0.05, (hx, hy, z + 0.08), M("duck", 0.6), (1, 1, 1.2)),
              sph("DkHead", 0.055, (hx - 0.005, hy, z + 0.15), M("duck", 0.6)),
              sph("DkBeak", 0.028, (hx - 0.05, hy - 0.02, z + 0.14), M("orange", 0.6), (1.3, 0.9, 0.55)),
              sph("DkEye", 0.009, (hx - 0.03, hy - 0.045, z + 0.165), M("brown", 0.5))]
    return group("duck_float", parts)


def mailbox():
    """우체통: post + rounded box with domed top + coral flag"""
    x, y = SPOT["mailbox"]
    parts = [rbox("MbPost", (0.06, 0.06, 0.42), (x, y, FLOOR + 0.21), M("wood2"), r=0.3),
             rbox("MbBox", (0.17, 0.26, 0.13), (x, y, FLOOR + 0.48), M("sky", 0.65), r=0.3)]
    dome = cyl("MbDome", 0.085, 0.26, (x, y, FLOOR + 0.545), M("sky", 0.65), bevel=0.15, rot=(math.radians(90), 0, 0)); parts.append(dome)
    parts += [rbox("MbDoor", (0.012, 0.0, 0.0), (x, y, FLOOR), M("off"), r=0.1)][:0]
    parts += [cyl("MbDoorC", 0.07, 0.012, (x, y - 0.13, FLOOR + 0.5), M("off", 0.7), bevel=0.3, rot=(math.radians(90), 0, 0)),
              rbox("MbFlagPole", (0.015, 0.015, 0.16), (x + 0.095, y + 0.02, FLOOR + 0.56), M("coral"), r=0.4),
              rbox("MbFlag", (0.015, 0.07, 0.05), (x + 0.095, y + 0.05, FLOOR + 0.62), M("coral"), r=0.4)]
    return group("mailbox", parts)


def garden_lamp(lit=False):
    """정원등: short post + lantern. lit=True -> glowing glass (night layer)"""
    x, y = SPOT["garden_lamp"]
    glass = M("lamp_glass", 0.4, 2.0 if lit else 0.0)
    parts = [cyl("GlBase", 0.07, 0.05, (x, y, FLOOR + 0.025), M("wood2"), bevel=0.3),
             cyl("GlPost", 0.025, 0.42, (x, y, FLOOR + 0.26), M("wood2"), bevel=0),
             rbox("GlGlass", (0.13, 0.13, 0.15), (x, y, FLOOR + 0.55), glass, r=0.3),
             rbox("GlFrameB", (0.16, 0.16, 0.025), (x, y, FLOOR + 0.47), M("off", 0.7), r=0.4),
             cyl("GlCap", 0.11, 0.07, (x, y, FLOOR + 0.66), M("off", 0.7), r2=0.02, bevel=0.2),
             sph("GlKnob", 0.022, (x, y, FLOOR + 0.71), M("coral"))]
    for k, (dx, dy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        parts.append(rbox(f"GlBar{k}", (0.02, 0.02, 0.16), (x + dx * 0.065, y + dy * 0.065, FLOOR + 0.55), M("off", 0.7), r=0.4))
    return group("garden_lamp_lit" if lit else "garden_lamp", parts)


def bird_feeder():
    """새 모이통: pole + tray with seeds + little coral roof (the guest sparrow perches on the tray rim)"""
    x, y = SPOT["bird_feeder"]
    parts = [cyl("BfPole", 0.022, 0.62, (x, y, FLOOR + 0.31), M("wood2"), bevel=0),
             rbox("BfTray", (0.26, 0.2, 0.03), (x, y, FLOOR + 0.63), M("wood"), r=0.3)]
    for k, (dx, dy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        parts.append(cyl(f"BfPost{k}", 0.01, 0.14, (x + dx * 0.11, y + dy * 0.08, FLOOR + 0.71), M("wood2"), bevel=0))
    for s in (-1, 1):
        rf = rbox(f"BfRoof{s}", (0.17, 0.27, 0.025), (x + s * 0.075, y, FLOOR + 0.82), M("coral", 0.7), r=0.4)
        rf.rotation_euler = (0, s * math.radians(32), 0); parts.append(rf)
    rnd = random.Random(5)
    for k in range(14):
        parts.append(sph(f"BfSeed{k}", 0.012, (x + rnd.uniform(-0.09, 0.09), y + rnd.uniform(-0.06, 0.06), FLOOR + 0.655),
                         M("seed_brown" if k % 2 else "sun_y", 0.8), (1, 0.8, 0.6)))
    return group("bird_feeder", parts)


FEEDER_PERCH = lambda: (SPOT["bird_feeder"][0] - 0.06, SPOT["bird_feeder"][1] - 0.1, FLOOR + 0.65)


def bench():
    """벤치 ★: wooden slats on chunky mint legs, facing the camera"""
    x, y = SPOT["bench"]
    sz = FLOOR + 0.17     # seat height (hippo legs are short; desk chair seat = 0.14)
    parts = []
    for k in range(3):
        parts.append(rbox(f"BnSeat{k}", (0.78, 0.075, 0.035), (x, y - 0.09 + k * 0.09, sz), M("wood"), r=0.35))
    for k in range(2):
        b = rbox(f"BnBack{k}", (0.78, 0.035, 0.07), (x, y + 0.16, sz + 0.14 + k * 0.1), M("wood"), r=0.35); b.rotation_euler = (math.radians(-10), 0, 0); parts.append(b)
    for s in (-1, 1):
        parts += [rbox(f"BnLegF{s}", (0.06, 0.06, 0.17), (x + s * 0.33, y - 0.09, FLOOR + 0.085), M("mint", 0.7), r=0.3),
                  rbox(f"BnLegB{s}", (0.06, 0.06, 0.42), (x + s * 0.33, y + 0.15, FLOOR + 0.21), M("mint", 0.7), r=0.3),
                  rbox(f"BnArm{s}", (0.06, 0.28, 0.04), (x + s * 0.36, y + 0.02, sz + 0.11), M("mint", 0.7), r=0.4)]
    return group("bench", parts)


def picnic_mat():
    """피크닉 매트 ★: pink/cream check blanket + little basket (the pet sits and eats here)"""
    x, y = SPOT["picnic_mat"]
    parts = [rbox("PmBase", (0.86, 0.62, 0.012), (x, y, FLOOR + 0.006), M("off", 0.9), r=0.4)]
    n, m_ = 5, 4
    for i in range(n):
        for j in range(m_):
            if (i + j) % 2: continue
            parts.append(rbox(f"PmSq{i}{j}", (0.86 / n, 0.62 / m_, 0.004), (x - 0.43 + (i + 0.5) * 0.86 / n, y - 0.31 + (j + 0.5) * 0.62 / m_, FLOOR + 0.013),
                              M("pink", 0.9), r=0.2))
    bx, by = x + 0.3, y + 0.2
    parts += [rbox("PmBasket", (0.18, 0.13, 0.1), (bx, by, FLOOR + 0.06), M("basket", 0.8), r=0.3),
              rbox("PmCloth", (0.17, 0.12, 0.02), (bx, by, FLOOR + 0.115), M("coral", 0.8), r=0.4),
              tube("PmHandle", [(bx - 0.07, by, FLOOR + 0.11), (bx, by, FLOOR + 0.2), (bx + 0.07, by, FLOOR + 0.11)], 0.011, M("basket", 0.8))]
    return group("picnic_mat", parts)


def hammock():
    """해먹 ★: two chunky A-frame posts + a sagging striped cloth"""
    x, y = SPOT["hammock"]
    L, Wd, z0, sagd = 0.75, 0.32, FLOOR + 0.42, 0.18
    parts = []
    for s in (-1, 1):
        for t in (-1, 1):
            p = rbox(f"HmLeg{s}{t}", (0.05, 0.05, 0.62), (x + s * (L / 2 + 0.1), y + t * 0.12, FLOOR + 0.29), M("wood2"), r=0.3)
            p.rotation_euler = (t * math.radians(-16), 0, 0); parts.append(p)
        parts.append(sph(f"HmTop{s}", 0.04, (x + s * (L / 2 + 0.1), y, FLOOR + 0.6), M("wood2")))
    nu, nv = 18, 7
    bm = bmesh.new()
    vs = []
    for i in range(nu + 1):
        u = i / nu
        row = []
        for j in range(nv + 1):
            v = j / nv - 0.5
            zz = z0 - sagd * 4 * u * (1 - u) + 0.1 * (2 * v) ** 2 * (0.3 + 4 * u * (1 - u))
            row.append(bm.verts.new((x - L / 2 + L * u, y + v * Wd * (0.55 + 0.9 * 4 * u * (1 - u)), zz)))
        vs.append(row)
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
            f.material_index = 1 if i in (4, 8, 9, 13) else 0          # coral stripes across the cloth
    cloth = _link(bm, "HmCloth", M("mint", 0.85), weighted=False)
    cloth.data.materials.append(M("coral", 0.8))
    sol = cloth.modifiers.new("s", "SOLIDIFY"); sol.thickness = 0.018
    parts.append(cloth)
    for s in (-1, 1):       # ropes from cloth ends to posts
        parts.append(tube(f"HmRope{s}", [(x + s * L / 2, y, z0 + 0.02), (x + s * (L / 2 + 0.05), y, z0 + 0.1), (x + s * (L / 2 + 0.1), y, FLOOR + 0.58)], 0.008, M("string")))
    return group("hammock", parts)


def tent(lit=False):
    """텐트: lavender A-frame with cream stripes, open flap, coral pennant. lit=True -> warm glow inside (night layer)"""
    x, y = SPOT["tent"]
    w, d, h = 0.78, 0.7, 0.6
    def prism(name, w_, d_, h_, m, loc):
        bm = bmesh.new()
        f = [bm.verts.new((-w_ / 2, -d_ / 2, 0)), bm.verts.new((w_ / 2, -d_ / 2, 0)), bm.verts.new((0, -d_ / 2, h_))]
        b = [bm.verts.new((-w_ / 2, d_ / 2, 0)), bm.verts.new((w_ / 2, d_ / 2, 0)), bm.verts.new((0, d_ / 2, h_))]
        bm.faces.new(f); bm.faces.new(b[::-1])
        for i in range(3):
            j = (i + 1) % 3
            bm.faces.new((f[j], f[i], b[i], b[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.03, segments=4, affect="EDGES", profile=0.5, clamp_overlap=True)
        o = _link(bm, name, m); o.location = loc
        return o
    parts = [prism("TnBody", w, d, h, M("tent", 0.85), (x, y, FLOOR))]
    inner = M("lamp_glass", 0.6, 1.2) if lit else M("tent2", 0.9)
    door = prism("TnDoor", w * 0.46, 0.02, h * 0.62, inner, (x, y - d / 2 - 0.005, FLOOR + 0.005)); parts.append(door)
    dh = h * 0.62; dw = w * 0.46
    for s in (-1, 1):      # rolled-up door flaps along both door edges
        L_ = math.hypot(dw / 2, dh)
        fl = cyl(f"TnFlap{s}", 0.02, L_ * 0.9, (x + s * dw / 4, y - d / 2 - 0.03, FLOOR + dh / 2), M("off", 0.85), bevel=0.4)
        fl.rotation_euler = (0, -s * math.atan2(dw / 2, dh), 0); parts.append(fl)
    ridge = cyl("TnRidge", 0.012, d + 0.04, (x, y, FLOOR + h - 0.01), M("off", 0.85), bevel=0.4, rot=(math.radians(90), 0, 0))
    parts.append(ridge)
    for s in (-1, 1):      # pegs + guy lines
        parts.append(cyl(f"TnPeg{s}", 0.012, 0.06, (x + s * (w / 2 + 0.14), y - d / 2 + 0.08, FLOOR + 0.03), M("wood2"), bevel=0))
    parts += [cyl("TnPole", 0.008, 0.16, (x, y - d / 2 + 0.04, FLOOR + h + 0.06), M("wood2"), bevel=0),
              R.tri("TnPennant", 0.09, 0.06, (x + 0.05, y - d / 2 + 0.04, FLOOR + h + 0.08), M("coral", 0.7))]
    parts[-1].rotation_euler = (0, math.radians(90), math.radians(-19))
    return group("tent_lit" if lit else "tent", parts)


ITEMS = {"flower_bed": flower_bed, "pinwheel": pinwheel, "duck_float": duck_float, "mailbox": mailbox,
         "garden_lamp": garden_lamp, "bird_feeder": bird_feeder, "bench": bench, "picnic_mat": picnic_mat,
         "hammock": hammock, "tent": tent}
PRICES = {"flower_bed": 9, "pinwheel": 9, "mailbox": 12, "duck_float": 12, "garden_lamp": 12, "picnic_mat": 18,
          "bird_feeder": 18, "bench": 18, "hammock": 24, "tent": 30}      # = room tiers, total 162 (WORLD.md 2장)
NAMES_KO = {"flower_bed": "화단", "pinwheel": "바람개비", "duck_float": "오리 튜브", "mailbox": "우체통", "garden_lamp": "정원등",
            "bird_feeder": "새 모이통", "bench": "벤치", "picnic_mat": "피크닉 매트", "hammock": "해먹", "tent": "텐트"}

# footprint on the ground (half sizes, world) -> blocks walking; interaction spot = where the pet stands + facing + action
FOOT = {"flower_bed": (0.47, 0.3), "pinwheel": (0.06, 0.06), "duck_float": None, "mailbox": (0.12, 0.15),
        "garden_lamp": (0.09, 0.09), "bird_feeder": (0.08, 0.08), "bench": (0.42, 0.22), "picnic_mat": None,
        "hammock": (0.6, 0.22), "tent": (0.42, 0.38)}
INTERACT = {   # (dx, dy from SPOT, facing, action)
    "flower_bed": (0.0, 0.42, "front", "sniff"),          # stands behind the bed facing the camera (flowers in front of its feet)
    "bench": (0.0, -0.02, "front", "sit_bench"),          # sits on the seat facing the camera
    "picnic_mat": (-0.1, 0.0, "front", "sit_eat"),        # sits on the mat (Y5: feeding allowed here)
    "hammock": (0.0, 0.0, "front", "lie"),                # lies in the cloth
}


# ------------------------------------------------------------------ guests (no collection; occasional visitors)
def sparrow(pose="ground", loc=(0, 0, FLOOR)):
    x, y, z = loc
    parts = [sph("SpBody", 0.06, (x, y, z + 0.06), M("bird", 0.75), (1.25, 0.9, 0.9)),
             sph("SpBelly", 0.045, (x - 0.01, y - 0.03, z + 0.05), M("off", 0.8), (1.1, 0.7, 0.8)),
             sph("SpHead", 0.042, (x - 0.06, y - 0.01, z + 0.11), M("bird", 0.75)),
             sph("SpCheek", 0.018, (x - 0.07, y - 0.04, z + 0.1), M("off", 0.8), (1, 0.5, 1)),
             sph("SpBeak", 0.013, (x - 0.1, y - 0.02, z + 0.105), M("yellow", 0.6), (1.4, 0.8, 0.7)),
             sph("SpEye", 0.008, (x - 0.08, y - 0.045, z + 0.122), M("brown", 0.5)),
             sph("SpWing", 0.04, (x + 0.015, y - 0.045, z + 0.07), M("bird2", 0.75), (1.3, 0.4, 0.8)),
             sph("SpTail", 0.03, (x + 0.08, y, z + 0.08), M("bird2", 0.75), (1.4, 0.6, 0.35))]
    parts[-1].rotation_euler = (0, math.radians(-25), 0)
    for s in (-1, 1):
        parts.append(cyl(f"SpLeg{s}", 0.005, 0.03, (x, y + s * 0.015, z + 0.012), M("orange", 0.6), bevel=0))
    return group(f"sparrow_{pose}", parts)


def butterfly(frame="open", loc=(0, 0, 0)):
    x, y, z = loc
    parts = [sph("BtBody", 0.012, (x, y, z), M("brown", 0.6), (1, 1, 3.5))]
    ang = math.radians(10 if frame == "open" else 70)
    for s in (-1, 1):
        for k, (dz, r, col) in enumerate(((0.012, 0.035, "pink"), (-0.018, 0.024, "lemon"))):
            c = Vector((x + s * math.cos(ang) * r * 1.1, y + 0.0, z + dz + math.sin(ang) * r))
            w = sph(f"BtWing{s}{k}", r, c, M(col, 0.7), (1, 0.15, 0.8))
            w.rotation_euler = (0, s * -ang, math.radians(-19)); parts.append(w)
    return group(f"butterfly_{frame}", parts)


def cam_dir(elev=ELEV):
    return Vector((0.35, -1, elev)).normalized()


def place_cam(sc, cam):
    cam.location = TARGET + cam_dir() * 12
    cam.rotation_euler = (TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()


def place_cam_rect(sc, cam, rect):
    """frame the canvas rect (x, y, w, h) px exactly: resolution = w×h, same 400 px/unit"""
    x, y, w, h = rect
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
    cam.data.ortho_scale = max(w, h) / PPU
    place_cam(sc, cam)
    cx, cy = x + w / 2 - 540, y + h / 2 - 540          # canvas offset from TARGET's px
    cam.location = TARGET + cam_dir() * 40 + RX * (cx / PPU) - UP * (cy / PPU)   # far back: the front of zone 3 is >12 units nearer
    cam.data.clip_end = 200
    bpy.context.view_layer.update()


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode = argv[0]
    hippo = [bpy.data.objects[n] for n in ("Hippo", "EyeDecal", "HippoRig")]
    if mode == "preview":
        out = argv[1]
        ids = argv[2:] or ["all"]
        ids = list(ITEMS) if ids == ["all"] else ([] if ids == ["none"] else ids)
        rect = [int(v) for v in os.environ.get("RECT", "0,0,1080,1860").split(",")]
        sc, cam = setup_render(1080, 1080, ORTHO); place_cam_rect(sc, cam, rect)
        sc.frame_set(1)
        background()
        for z in os.environ.get("LOCKS", "").split(","):
            if z: LOCKS[int(z)]()
        st = int(os.environ.get("TREE", "4")); memory_tree(st)
        if os.environ.get("FRUITS", "1") == "1" and st > 1: memory_fruits(st)
        for i in ids:
            ITEMS[i]()
        if "flower_bed" in ids:
            for k, f in enumerate(os.environ.get("BED", "tulip,sunflower,tulip").split(",")):
                if f: bed_flower(f, k)
        if os.environ.get("GUESTS") == "1":
            sparrow("perch", FEEDER_PERCH()) if "bird_feeder" in ids else sparrow("ground", (0.3, -0.9, FLOOR))
            butterfly("open", (0.75, -0.35, FLOOR + 0.35))
        hx, hy = [float(v) for v in os.environ.get("HIPPO", f"{HIPPO[0]},{HIPPO[1]}").split(",")]
        hippo[2].location = (hx, hy, 0)
        sc.render.filepath = os.path.abspath(out)
        bpy.ops.render.render(write_still=True)
        print("WROTE", out)
    elif mode == "thumbs":
        out = argv[1]
        sc, cam = setup_render(512, 512, 1.0)
        for o in hippo: o.hide_render = True
        os.makedirs(out, exist_ok=True)
        for i in (argv[2:] or list(ITEMS)):
            g = ITEMS[i]()
            if i == "flower_bed":
                fl = [bed_flower(f, k) for k, f in enumerate(("tulip", "sunflower", "tulip"))]
            else:
                fl = []
            parts = item_parts(g) + [c for f in fl for c in item_parts(f)]
            frame_on(cam, parts)
            sc.render.filepath = os.path.join(os.path.abspath(out), f"{i}.png")
            bpy.ops.render.render(write_still=True)
            for c in list(parts): bpy.data.objects.remove(c, do_unlink=True)
            for e in [g] + fl: bpy.data.objects.remove(e, do_unlink=True)
            print("THUMB", i)
