# Garden (텃밭) scene: background, 3 plots, crops x stages (+ dozing), harvest decorations/icons.
# Camera elev 0.5 (≈25°, docs/WORLD.md W2), same direction/lights as everything else. Hippo scale = room (visible width 2.7).
# usage:
#   blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/garden.py -- preview <out.png> [crop:stage[:doze] x3]
#   ... -- crops <out_dir>            every crop x stage (1..3) x awake/doze + mound, transparent, one fixed plot camera
#   ... -- icons <out_dir>            harvest icons + seed packets (512², transparent, front-ish camera)
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import room as R
from room import rbox, sph, cyl, M, P, group, setup_render, frame_on, item_parts

FLOOR = -0.5
ELEV = 0.5
P.update({
    "grass": (0.70, 0.86, 0.60), "grass2": (0.64, 0.82, 0.55), "hedge": (0.47, 0.74, 0.52), "hedge2": (0.42, 0.68, 0.48),
    "soil": (0.62, 0.44, 0.31), "soil2": (0.52, 0.36, 0.25), "stem": (0.40, 0.68, 0.43), "leafd": (0.42, 0.72, 0.47),
    "seed_brown": (0.50, 0.33, 0.20), "vine": (0.55, 0.35, 0.50), "skin": (0.62, 0.36, 0.55), "flesh": (0.98, 0.78, 0.25),
    "berry": (0.93, 0.33, 0.36), "petal_w": (0.99, 0.97, 0.93), "sun_y": (1.0, 0.82, 0.30), "sun_c": (0.55, 0.36, 0.22),
    "paper": (0.97, 0.93, 0.85),
})

PLOT_Y = -0.15
PLOT_X = (-0.9, 0.0, 0.9)
PLOT_W, PLOT_D, PLOT_H = 0.72, 0.5, 0.08
SOIL_Z = FLOOR + PLOT_H
HIPPO = (0.0, 0.72)          # stands behind the middle plot, so all three plots stay visible


# ------------------------------------------------------------------ helpers
def tube(name, pts, r, m, r_end=None):
    """smooth stem through 3D points (curve with bevel -> mesh)"""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS"); sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.use_endpoint_u = True; sp.order_u = min(4, len(pts))
    if r_end is not None:
        for k, p in enumerate(sp.points):
            p.radius = 1 + (r_end / r - 1) * k / (len(pts) - 1)
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(o); bpy.data.curves.remove(cu)
    for poly in me.polygons: poly.use_smooth = True
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def leaf(name, base, length, width, tilt, yaw, m, thick=0.3, lift=0.0):
    """ellipsoid leaf whose base sits at `base`, long axis tilted `tilt` deg from vertical toward +x, then yawed"""
    t, y = math.radians(tilt), math.radians(yaw)
    d = Matrix.Rotation(y, 3, "Z") @ Matrix.Rotation(t, 3, "Y") @ Vector((0, 0, 1))
    c = Vector(base) + d * (length / 2) + Vector((0, 0, lift))
    o = sph(name, length / 2, c, m, (width / length, width / length * thick, 1))
    o.rotation_euler = (0, t, y)
    return o


def heart_leaf(name, base, size, tilt, yaw, m):
    t, y = math.radians(tilt), math.radians(yaw)
    rot = Matrix.Rotation(y, 3, "Z") @ Matrix.Rotation(t, 3, "Y")
    parts = []
    for k, sx in enumerate((-1, 1)):
        c = Vector(base) + rot @ Vector((sx * size * 0.28, 0, size * 0.55))
        o = sph(f"{name}{k}", size * 0.42, c, m, (1, 0.28, 1.05)); o.rotation_euler = (0, t + sx * 0.35, y); parts.append(o)
    tip = Vector(base) + rot @ Vector((0, 0, size * 0.25))
    o = sph(f"{name}t", size * 0.3, tip, m, (1, 0.28, 1.1)); o.rotation_euler = (0, t, y); parts.append(o)
    return parts


def apply_tf(objs):
    bpy.context.view_layer.update()      # matrix_world is stale right after setting location/rotation/scale
    for o in objs:
        if o.type != "MESH": continue
        o.data = o.data.copy()
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)


def droop(objs, base, height, ang=32):
    """dozing: bend the plant over from its base (more at the top), leaning right and toward the camera"""
    apply_tf(objs)
    b = Vector(base)
    for o in objs:
        if o.type != "MESH": continue
        for v in o.data.vertices:
            rel = v.co - b
            t = max(0.0, rel.z) / height
            a = math.radians(ang) * (t ** 1.4)
            ry = Matrix.Rotation(a, 3, "Y")                  # lean toward +x
            rx = Matrix.Rotation(-a * 0.45, 3, "X")          # and toward the camera (-y)
            v.co = b + rx @ (ry @ rel)
        o.data.update()


# ------------------------------------------------------------------ crops: build(base, stage) -> (objects, height)
# stage 1 = 싹, 2 = 자람, 3 = 다 자람(수확). stage 0 = 흙더미 (shared).
def mound(base):
    x, y, z = base
    parts = [sph("Mound", 0.11, (x, y, z), M("soil2", 0.95), (1.3, 1.0, 0.4))]
    for k, (dx, dy) in enumerate(((-0.05, -0.04), (0.04, 0.03), (0.0, -0.07))):
        parts.append(sph(f"Clod{k}", 0.018, (x + dx, y + dy, z + 0.035), M("soil", 0.95), (1, 1, 0.7)))
    return parts, 0.06


def sweet_potato(base, stage):
    x, y, z = base; L, V = M("leaf", 0.75), M("vine", 0.7)
    parts = [sph("SpSoil", 0.13, (x, y, z), M("soil2", 0.95), (1.4, 1.1, 0.35))]
    if stage == 1:
        parts.append(tube("SpStem", [(x, y, z), (x + 0.01, y, z + 0.06), (x, y, z + 0.1)], 0.008, V))
        parts += heart_leaf("SpL1", (x, y, z + 0.09), 0.08, -40, -19, L) + heart_leaf("SpL2", (x, y, z + 0.09), 0.07, 45, -19, L)
        return parts, 0.17
    n = 5 if stage == 2 else 8
    for k in range(n):
        a = -70 + 140 * k / (n - 1); r = 0.1 + 0.05 * (k % 2)
        tip = (x + math.sin(math.radians(a)) * r * 1.6, y + 0.04 * ((k % 3) - 1), z + 0.1 + 0.08 * math.cos(math.radians(a)))
        parts.append(tube(f"SpVine{k}", [(x, y, z), (x + (tip[0] - x) * 0.5, y, z + 0.12), tip], 0.007, V))
        parts += heart_leaf(f"SpL{k}", tip, 0.09 if stage == 2 else 0.11, a * 0.6, -19 + 20 * ((k % 3) - 1), L if k % 2 else M("leafd"))
    if stage == 3:   # purple potatoes peeking out of the soil, one showing yellow flesh-free top
        for k, (dx, rz) in enumerate(((-0.1, 30), (0.0, -10), (0.11, -35))):
            o = sph(f"SpPotato{k}", 0.05, (x + dx, y - 0.08, z + 0.02), M("skin", 0.65), (1.6, 0.95, 0.9))
            o.rotation_euler = (0, math.radians(rz), math.radians(-19)); parts.append(o)
    return parts, 0.3 if stage == 3 else 0.24


def tulip(base, stage):
    x, y, z = base; L, S = M("leafd", 0.75), M("stem", 0.75)
    parts = []
    if stage == 1:
        parts += [leaf("TuL1", (x, y, z), 0.13, 0.045, -18, -19, L), leaf("TuL2", (x, y, z), 0.11, 0.04, 22, -19, L)]
        return parts, 0.13
    stems = [(-0.08, 0.0, -6), (0.07, 0.03, 8), (0.0, -0.05, 0)] if stage == 3 else [(0.0, 0.0, 0)]
    for k, (dx, dy, lean) in enumerate(stems):
        h = 0.3 + 0.04 * (k == 2)
        bx, by = x + dx, y + dy
        top = (bx + math.sin(math.radians(lean)) * h, by, z + h)
        parts.append(tube(f"TuStem{k}", [(bx, by, z), (bx + (top[0] - bx) * 0.3, by, z + h * 0.5), top], 0.009, S))
        parts += [leaf(f"TuLa{k}", (bx, by, z), 0.2, 0.05, -20 + lean, -19, L), leaf(f"TuLb{k}", (bx, by, z), 0.17, 0.045, 25 + lean, -19, L)]
        if stage == 2:
            parts.append(sph(f"TuBud{k}", 0.035, (top[0], top[1], top[2] + 0.03), M("leaf"), (0.8, 0.8, 1.3)))
            parts.append(sph(f"TuBudTip{k}", 0.022, (top[0], top[1], top[2] + 0.058), M("coral"), (0.8, 0.8, 1.2)))
        else:
            col = M("coral", 0.7) if k != 1 else M("pink", 0.7)
            cup = sph(f"TuCup{k}", 0.055, (top[0], top[1], top[2] + 0.045), col, (1, 1, 1.15)); parts.append(cup)
            for q in range(3):                                   # three petal tips around the rim
                a = q * 2 * math.pi / 3 + 0.3
                parts.append(sph(f"TuTip{k}{q}", 0.028, (top[0] + 0.035 * math.cos(a), top[1] + 0.035 * math.sin(a), top[2] + 0.095), col, (0.8, 0.8, 1.3)))
    return parts, 0.42 if stage == 3 else 0.36


def sunflower(base, stage):
    x, y, z = base; L, S = M("leaf", 0.75), M("stem", 0.75)
    parts = []
    if stage == 1:
        parts.append(tube("SuStem", [(x, y, z), (x, y, z + 0.06), (x, y, z + 0.1)], 0.009, S))
        parts += [leaf("SuL1", (x, y, z + 0.09), 0.08, 0.06, -70, -19, L), leaf("SuL2", (x, y, z + 0.09), 0.08, 0.06, 70, -19, L)]
        return parts, 0.15
    h = 0.4 if stage == 2 else 0.58
    top = (x + 0.02, y, z + h)
    parts.append(tube("SuStem", [(x, y, z), (x + 0.02, y, z + h * 0.5), top], 0.016, S, r_end=0.011))
    for k, (fz, side) in enumerate(((0.12, -1), (0.22, 1), (0.33, -1), (0.42, 1))[: (3 if stage == 2 else 4)]):
        parts.append(leaf(f"SuL{k}", (x + 0.01, y, z + fz), 0.13, 0.08, side * 62, -19 + side * 10, L if k % 2 else M("leafd")))
    if stage == 2:
        parts.append(sph("SuBud", 0.05, (top[0], top[1], top[2] + 0.03), M("leafd"), (1, 0.9, 0.85)))
        return parts, h + 0.08
    # flower faces the camera: disc + ring of petals, tilted slightly down
    face = Matrix.Rotation(math.radians(-19), 3, "Z") @ Matrix.Rotation(math.radians(-80), 3, "X")
    c = Vector(top) + Vector((0, -0.02, 0.06))
    disc = cyl("SuDisc", 0.075, 0.03, c, M("sun_c", 0.85), bevel=0.4); disc.rotation_euler = face.to_euler(); parts.append(disc)
    for q in range(14):
        a = q * 2 * math.pi / 14
        off = face @ Vector((math.cos(a) * 0.1, math.sin(a) * 0.1, -0.005))
        pe = sph(f"SuPetal{q}", 0.045, c + off, M("sun_y", 0.7), (0.55, 1.0, 0.18))
        pe.rotation_euler = (face @ Matrix.Rotation(a + math.pi / 2, 3, "Z")).to_euler(); parts.append(pe)
    for q in range(6):
        a = q * 2 * math.pi / 6
        parts.append(sph(f"SuSeed{q}", 0.012, c + face @ Vector((math.cos(a) * 0.035, math.sin(a) * 0.035, 0.016)), M("seed_brown", 0.9)))
    return parts, h + 0.16


def strawberry(base, stage):
    x, y, z = base; L, S = M("leaf", 0.75), M("stem", 0.75)
    parts = []
    def trifoliate(nm, b, size, tilt, yaw):
        out = [tube(nm + "s", [b, (b[0] + math.sin(math.radians(tilt)) * size, b[1], b[2] + size * 0.8)], 0.006, S)]
        tip = (b[0] + math.sin(math.radians(tilt)) * size, b[1], b[2] + size * 0.8)
        for q, a in enumerate((-45, 0, 45)):
            out.append(leaf(f"{nm}{q}", tip, size * 0.75, size * 0.55, tilt + a, yaw, L if q != 1 else M("leafd"), thick=0.3))
        return out
    if stage == 1:
        parts += trifoliate("StT", (x, y, z), 0.09, 0, -19)
        return parts, 0.16
    n = 4 if stage == 2 else 6
    for k in range(n):
        a = -60 + 120 * k / (n - 1)
        parts += trifoliate(f"StT{k}", (x, y + 0.02 * ((k % 2) * 2 - 1), z), 0.12 + 0.02 * (k % 2), a, -19 + 15 * ((k % 3) - 1))
    if stage == 2:   # white flowers
        for k, (dx, dz) in enumerate(((-0.08, 0.14), (0.09, 0.12))):
            cx, cz = x + dx, z + dz
            for q in range(5):
                a = q * 2 * math.pi / 5
                parts.append(sph(f"StPet{k}{q}", 0.018, (cx + 0.02 * math.cos(a), y - 0.09, cz + 0.02 * math.sin(a)), M("petal_w", 0.7), (1, 0.4, 1)))
            parts.append(sph(f"StCtr{k}", 0.012, (cx, y - 0.1, cz), M("sun_y", 0.6)))
        return parts, 0.22
    for k, (dx, dz, s) in enumerate(((-0.1, 0.05, 1.0), (0.0, 0.03, 1.15), (0.11, 0.06, 0.95), (0.05, 0.1, 0.8))):
        c = (x + dx, y - 0.1, z + dz)
        b = sph(f"StBerry{k}", 0.04 * s, c, M("berry", 0.55), (1, 0.95, 1.2)); parts.append(b)
        parts.append(sph(f"StCalyx{k}", 0.025 * s, (c[0], c[1], c[2] + 0.04 * s), M("leafd"), (1.2, 1.2, 0.35)))
        for q in range(4):
            a = q * math.pi / 2 + 0.4
            parts.append(sph(f"StSeed{k}{q}", 0.005, (c[0] + 0.022 * s * math.cos(a), c[1] - 0.035 * s, c[2] - 0.01 + 0.02 * s * math.sin(a)), M("sun_y", 0.6)))
    return parts, 0.24


CROP_SCALE = 1.3
CROP_ORTHO, CROP_LIFT = 1.5, 0.42   # crop image camera: 512px = 1.35 units, centre 0.42 above soil (tallest = sunflower)
CROPS = {"sweet_potato": sweet_potato, "tulip": tulip, "sunflower": sunflower, "strawberry": strawberry}


def build_crop(cid, stage, base, doze=False, name=None):
    parts, h = mound(base) if stage == 0 else CROPS[cid](base, stage)
    # crops read better a bit bigger than modelled (beds are 0.72 wide)
    apply_tf(parts)
    b = Vector(base)
    for o in parts:
        for v in o.data.vertices:
            v.co = b + (v.co - b) * CROP_SCALE
        o.data.update()
    h *= CROP_SCALE
    if doze and stage > 0:
        droop([p for p in parts if not p.name.startswith(("SpSoil", "SpPotato"))], base, h)
    return group(name or f"{cid}_{stage}{'_doze' if doze else ''}", parts)


# ------------------------------------------------------------------ background
def background():
    parts = [rbox("Grass", (12, 10, 0.1), (0, 1.5, FLOOR - 0.05), M("grass", 0.9), r=0.02)]
    # grass tufts / tiny flowers for colour detail
    import random
    rnd = random.Random(4)
    for k in range(26):
        gx, gy = rnd.uniform(-1.9, 2.2), rnd.uniform(-1.3, 1.1)
        if abs(gy - PLOT_Y) < 0.35 and abs(gx) < 1.35: continue
        if abs(gx - HIPPO[0]) < 0.4 and abs(gy - HIPPO[1]) < 0.3: continue
        if k % 3 == 0:
            parts.append(sph(f"Fl{k}", 0.018, (gx, gy, FLOOR + 0.012), M(rnd.choice(["petal_w", "pink", "sun_y"]), 0.7), (1, 1, 0.6)))
        else:
            parts.append(sph(f"Tuft{k}", 0.04, (gx, gy, FLOOR), M("grass2", 0.9), (1.3, 0.8, 0.45)))
    # picket fence along the back + hedge bumps behind it
    fy = 1.25
    for k in range(17):
        x = -2.2 + k * 0.27
        parts.append(rbox(f"Picket{k}", (0.09, 0.04, 0.38), (x, fy, FLOOR + 0.19), M("off", 0.8), r=0.42))
        parts.append(sph(f"PicketTop{k}", 0.045, (x, fy, FLOOR + 0.38), M("off", 0.8), (1, 0.45, 0.6)))
    for z in (0.12, 0.27):
        parts.append(rbox(f"Rail{z}", (4.6, 0.03, 0.04), (0, fy + 0.03, FLOOR + z), M("off", 0.8), r=0.4))
    for k in range(9):
        x = -3.0 + k * 0.78
        parts.append(sph(f"Hedge{k}", 0.48, (x, fy + 0.5, FLOOR + 0.34), M("hedge" if k % 2 else "hedge2", 0.85), (1.2, 0.8, 1.05)))
    for k in range(7):        # round trees further back fill the top of the frame
        x = -2.6 + k * 0.95
        parts.append(cyl(f"Trunk{k}", 0.05, 0.6, (x, fy + 1.35, FLOOR + 0.3), M("wood2"), bevel=0))
        parts.append(sph(f"Crown{k}", 0.55, (x, fy + 1.35, FLOOR + 0.95 + 0.12 * (k % 2)), M("leafd" if k % 2 else "hedge", 0.85), (1, 0.85, 0.95)))
    # raised beds (wooden frame + soil)
    for i, px in enumerate(PLOT_X):
        parts.append(rbox(f"Bed{i}", (PLOT_W, PLOT_D, PLOT_H), (px, PLOT_Y, FLOOR + PLOT_H / 2), M("wood2"), r=0.4))
        parts.append(rbox(f"Soil{i}", (PLOT_W - 0.07, PLOT_D - 0.07, 0.03), (px, PLOT_Y, SOIL_Z - 0.005), M("soil", 0.95), r=0.4))
    # sign + watering can + stepping stones in front of the hippo
    parts += [rbox("SignBoard", (0.3, 0.035, 0.18), (1.0, 0.95, FLOOR + 0.4), M("wood"), r=0.3),
              cyl("SignPost", 0.018, 0.34, (1.0, 0.97, FLOOR + 0.17), M("wood2"), bevel=0),
              sph("SignSprout", 0.03, (0.97, 0.92, FLOOR + 0.41), M("leaf"), (1, 0.3, 1.3)),
              sph("SignSprout2", 0.03, (1.03, 0.92, FLOOR + 0.41), M("leafd"), (1, 0.3, 1.3))]
    cx, cy = -1.25, 0.75
    parts += [cyl("CanBody", 0.075, 0.13, (cx, cy, FLOOR + 0.065), M("sky", 0.6), r2=0.065, bevel=0.3),
              cyl("CanSpout", 0.012, 0.16, (cx + 0.1, cy, FLOOR + 0.09), M("sky", 0.6), r2=0.009, bevel=0, rot=(0, math.radians(55), 0)),
              sph("CanRose", 0.022, (cx + 0.165, cy, FLOOR + 0.135), M("sky", 0.6), (1, 1, 0.6)),
              tube("CanHandle", [(cx - 0.05, cy, FLOOR + 0.1), (cx - 0.02, cy, FLOOR + 0.19), (cx + 0.04, cy, FLOOR + 0.13)], 0.01, M("sky", 0.6))]
    for k, (sx, sy) in enumerate(((0.0, 0.35), (0.12, -0.6), (-0.1, -0.95))):
        parts.append(sph(f"Stone{k}", 0.09, (sx, sy, FLOOR), M("pebble", 0.85), (1.3, 1.0, 0.22)))
    for o in parts:
        if o.name.startswith(("Grass",)):
            o.visible_shadow = False
    return group("GardenBase", parts)


# ------------------------------------------------------------------ icons (basket UI + planting picker)
def produce(cid):
    """harvested produce alone, for the 수확 바구니 list"""
    o = Vector((0, 0, 0)); parts = []
    if cid == "sweet_potato":
        for k, (dx, rz, s) in enumerate(((-0.06, 25, 1.0), (0.06, -20, 0.9))):
            p = sph(f"IcPot{k}", 0.07 * s, (dx, 0.01 * k, 0.05), M("skin", 0.65), (1.7, 0.95, 0.9)); p.rotation_euler = (0, math.radians(rz), math.radians(-19)); parts.append(p)
        parts.append(sph("IcPotTip", 0.02, (-0.165, 0, 0.07), M("vine", 0.7), (1.5, 0.6, 0.6)))
    elif cid == "tulip":
        for k, (dx, col) in enumerate(((-0.04, "coral"), (0.0, "coral"), (0.045, "pink"))):
            top = (dx * 2, 0, 0.26 + 0.02 * (k == 1))
            st = tube(f"IcTuS{k}", [(dx * 0.3, 0, 0.0), (dx, 0, 0.12), top], 0.008, M("stem"))
            parts += [st, sph(f"IcTuC{k}", 0.045, top, M(col, 0.7), (1, 1, 1.2))]
            for q in range(3):
                a = q * 2.1 + 0.3
                parts.append(sph(f"IcTuT{k}{q}", 0.022, (top[0] + 0.028 * math.cos(a), 0.028 * math.sin(a), top[2] + 0.04), M(col, 0.7), (0.8, 0.8, 1.3)))
        parts.append(rbox("IcTuRibbon", (0.07, 0.05, 0.03), (0, -0.01, 0.07), M("lemon", 0.7), r=0.45))
    elif cid == "sunflower":
        face = Matrix.Rotation(math.radians(-19), 3, "Z") @ Matrix.Rotation(math.radians(-90), 3, "X")
        c = Vector((0, 0, 0.12))
        d = cyl("IcSuD", 0.07, 0.03, c, M("sun_c", 0.85), bevel=0.4); d.rotation_euler = face.to_euler(); parts.append(d)
        for q in range(14):
            a = q * 2 * math.pi / 14
            pe = sph(f"IcSuP{q}", 0.045, c + face @ Vector((math.cos(a) * 0.1, math.sin(a) * 0.1, -0.005)), M("sun_y", 0.7), (0.55, 1.0, 0.18))
            pe.rotation_euler = (face @ Matrix.Rotation(a + math.pi / 2, 3, "Z")).to_euler(); parts.append(pe)
        parts.append(tube("IcSuStem", [(0, 0.01, 0.0), (0.0, 0.01, -0.12)], 0.012, M("stem")))
    else:
        for k, (dx, dz, s) in enumerate(((-0.05, 0.0, 1.0), (0.05, 0.01, 0.9))):
            c = (dx, 0, dz)
            parts += [sph(f"IcStB{k}", 0.06 * s, c, M("berry", 0.55), (1, 0.95, 1.2)),
                      sph(f"IcStC{k}", 0.04 * s, (dx, 0, dz + 0.065 * s), M("leafd"), (1.2, 1.2, 0.35))]
            for q in range(6):
                a = q * 1.05 + 0.3
                parts.append(sph(f"IcStS{k}{q}", 0.007, (dx + 0.035 * s * math.cos(a), -0.055 * s, dz - 0.01 + 0.035 * s * math.sin(a)), M("sun_y", 0.6)))
    return group(f"produce_{cid}", parts)


PACKET_COL = {"sweet_potato": "lav", "tulip": "pink", "sunflower": "sun_y", "strawberry": "mint"}


def seed_packet(cid):
    """씨앗 봉투 for the planting picker: paper packet + crop-colour band + little produce on the front"""
    parts = [rbox("PkBody", (0.24, 0.03, 0.32), (0, 0, 0.16), M("paper", 0.85), r=0.25),
             rbox("PkBand", (0.245, 0.035, 0.07), (0, -0.002, 0.07), M(PACKET_COL[cid], 0.8), r=0.4),
             rbox("PkFold", (0.25, 0.036, 0.035), (0, 0, 0.31), M(PACKET_COL[cid], 0.8), r=0.45)]
    g = produce(cid)
    kids = list(g.children)
    for c in kids:
        c.parent = None                  # group empty sits at the origin, so world transforms don't change
    bpy.data.objects.remove(g)
    apply_tf(kids)
    vs = [v.co for o in kids for v in o.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    c = (lo + hi) / 2; k = 0.16 / max(hi.x - lo.x, hi.z - lo.z)        # fit in the area between band and fold
    for o in kids:
        for v in o.data.vertices:
            v.co = (v.co - c) * k + Vector((0, -0.03, 0.19))
        o.data.update()
    return group(f"packet_{cid}", parts + kids)


TARGET = Vector((0.0, 0.55, 0.0))
ORTHO = 2.7


def cam_dir(elev=ELEV):
    return Vector((0.35, -1, elev)).normalized()


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode, out = argv[0], argv[1]
    hippo = [bpy.data.objects[n] for n in ("Hippo", "EyeDecal", "HippoRig")]
    if mode == "preview":
        sc, cam = setup_render(1080, 1080, ORTHO)
        cam.location = TARGET + cam_dir() * 12
        cam.rotation_euler = (TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.frame_set(1)
        background()
        spec = argv[2:] or ["sweet_potato:3", "tulip:2", "sunflower:3"]
        for px, sp in zip(PLOT_X, spec):
            f = sp.split(":")
            build_crop(f[0], int(f[1]), (px, PLOT_Y, SOIL_Z), doze=len(f) > 2)
        hippo[2].location = (*HIPPO, 0)
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print("WROTE", out)
    elif mode == "crops":
        # one image per crop/stage/doze, all from the SAME plot-centred camera -> app places by plot anchor only
        sc, cam = setup_render(512, 512, CROP_ORTHO)
        for o in hippo: o.hide_render = True
        base = Vector((0, 0, SOIL_Z))
        anchor = base + Vector((0, 0, CROP_LIFT))     # camera looks at this point above the soil centre
        cam.location = anchor + cam_dir() * 12
        cam.rotation_euler = (anchor - cam.location).to_track_quat("-Z", "Y").to_euler()
        os.makedirs(out, exist_ok=True)
        jobs = [("mound", 0, False)] + [(c, s, d) for c in CROPS for s in (1, 2, 3) for d in (False, True)]
        for cid, stage, doze in jobs:
            g = build_crop(cid if cid != "mound" else "sweet_potato", stage, tuple(base), doze, name=f"{cid}_{stage}")
            sc.render.filepath = os.path.join(out, "mound.png" if cid == "mound" else f"{cid}_{stage}{'_doze' if doze else ''}.png")
            bpy.ops.render.render(write_still=True)
            for c in g.children_recursive:
                bpy.data.objects.remove(c)
            bpy.data.objects.remove(g)
            print("CROP", sc.render.filepath)
    elif mode == "icons":
        sc, cam = setup_render(512, 512, 1.0)
        for o in hippo: o.hide_render = True
        os.makedirs(out, exist_ok=True)
        for cid in CROPS:
            for kind, fn in (("produce", produce), ("packet", seed_packet)):
                g = fn(cid)
                parts = [c for c in g.children_recursive if c.type == "MESH"]
                frame_on(cam, parts, elev=0.3, pad=1.15)
                sc.render.filepath = os.path.join(out, f"{kind}_{cid}.png")
                bpy.ops.render.render(write_still=True)
                for c in parts: bpy.data.objects.remove(c)
                bpy.data.objects.remove(g)
                print("ICON", kind, cid)
