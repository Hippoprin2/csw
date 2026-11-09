# Space blockouts (room / garden / yard) to compare camera elevation with the real hippo.
# usage: blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/world_blockout.py -- <scene> <elev> <out.png>
#   scene: room | garden | yard ; elev: camera z component (0.12 = character default, 0.5 = desk scene)
import bpy, bmesh, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
from props import mat, box, obj_from_bm, cylinder

argv = sys.argv[sys.argv.index("--") + 1:]
SCENE, ELEV, OUT = argv[0], float(argv[1]), argv[2]
sc = bpy.context.scene
sc.frame_set(1)
FLOOR = -0.5


def sphere(name, r, loc, m, scale=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
    for f in bm.faces: f.smooth = True
    o = obj_from_bm(bm, name, [m]); o.location = loc; o.scale = scale
    return o


def cyl(name, r, h, loc, m):
    o = obj_from_bm(cylinder(r, h), name, [m]); o.location = loc
    return o


C = {k: mat("W_" + k, v, r) for k, v, r in [
    ("wall", (0.965, 0.914, 0.847), 0.9), ("wall2", (0.93, 0.87, 0.80), 0.9),
    ("wood", (0.86, 0.69, 0.50), 0.7), ("wood2", (0.80, 0.62, 0.45), 0.7),
    ("mint", (0.62, 0.84, 0.76), 0.7), ("off", (0.99, 0.97, 0.93), 0.8),
    ("coral", (0.93, 0.36, 0.38), 0.7), ("lav", (0.82, 0.80, 0.90), 0.8),
    ("yellow", (0.98, 0.78, 0.25), 0.6), ("pink", (1.0, 0.65, 0.75), 0.7),
    ("leaf", (0.50, 0.80, 0.55), 0.7), ("sky", (0.55, 0.82, 0.98), 0.5),
    ("grass", (0.66, 0.84, 0.60), 0.9), ("soil", (0.66, 0.47, 0.35), 0.9),
    ("hedge", (0.45, 0.72, 0.50), 0.85), ("water", (0.55, 0.78, 0.92), 0.3),
    ("stone", (0.85, 0.82, 0.78), 0.8), ("purple", (0.55, 0.35, 0.55), 0.7)]}


def room():
    W, D0, D1, H = 1.55, -0.95, 1.0, 1.9          # half width, front y, back wall y, wall height
    box("Floor", (2 * W, D1 - D0, 0.08), (0, (D0 + D1) / 2, FLOOR - 0.04), C["wood"])
    box("BackWall", (2 * W, 0.08, H), (0, D1 + 0.04, FLOOR + H / 2), C["wall"])
    box("LeftWall", (0.08, D1 - D0, H), (-W - 0.04, (D0 + D1) / 2, FLOOR + H / 2), C["wall2"])
    # window (back wall centre-left) + sill = harvest shelf
    box("WinFrame", (0.62, 0.05, 0.56), (-0.25, D1 - 0.02, 0.55), C["wood"])
    box("WinGlass", (0.52, 0.05, 0.46), (-0.25, D1 - 0.035, 0.55), C["sky"])
    box("Sill", (0.78, 0.14, 0.05), (-0.25, D1 - 0.08, 0.24), C["wood2"])
    cyl("VaseHarvest", 0.04, 0.1, (-0.45, D1 - 0.08, 0.32), C["off"]); sphere("Tulip", 0.05, (-0.45, D1 - 0.08, 0.42), C["coral"])
    box("Basket", (0.14, 0.09, 0.06), (-0.05, D1 - 0.08, 0.3), C["wood"]); sphere("Berry", 0.035, (-0.05, D1 - 0.08, 0.35), C["coral"])
    # wall items
    box("Frame", (0.28, 0.03, 0.34), (0.65, D1 - 0.01, 0.75), C["pink"])
    cyl_o = cyl("Clock", 0.13, 0.04, (1.15, D1 - 0.01, 0.95), C["yellow"]); cyl_o.rotation_euler = (math.radians(90), 0, 0)
    box("Garland", (1.6, 0.02, 0.06), (0.1, D1 - 0.01, 1.2), C["coral"])
    # back-left: bed against left wall
    box("BedBase", (0.75, 1.25, 0.22), (-W + 0.4, 0.3, FLOOR + 0.11), C["wood2"])
    box("Blanket", (0.74, 0.85, 0.08), (-W + 0.4, 0.15, FLOOR + 0.26), C["mint"])
    box("Pillow", (0.5, 0.25, 0.1), (-W + 0.4, 0.75, FLOOR + 0.28), C["off"])
    # back-right: bookshelf
    box("Shelf", (0.6, 0.3, 0.95), (W - 0.38, D1 - 0.18, FLOOR + 0.475), C["wood"])
    for i, col in enumerate(("lav", "sky", "coral", "yellow")):
        box(f"Books{i}", (0.1, 0.22, 0.2), (W - 0.6 + i * 0.13, D1 - 0.2, FLOOR + 0.62), C[col])
    # centre floor: rug + low table (좌식 탁자) with mug
    rug = cyl("Rug", 0.62, 0.015, (0.25, 0.0, FLOOR + 0.008), C["lav"]); rug.scale = (1.3, 1, 1)
    box("Table", (0.5, 0.34, 0.05), (0.75, -0.05, FLOOR + 0.2), C["wood"])
    for sx in (-1, 1):
        box(f"TLeg{sx}", (0.05, 0.25, 0.18), (0.75 + sx * 0.2, -0.05, FLOOR + 0.09), C["wood2"])
    cyl("Mug", 0.04, 0.07, (0.85, -0.05, FLOOR + 0.26), C["coral"])
    # front: lamp left, big plant right, cushion
    cyl("LampPole", 0.015, 0.9, (-1.25, -0.6, FLOOR + 0.45), C["wood2"])
    sphere("LampShade", 0.13, (-1.25, -0.6, FLOOR + 0.95), C["yellow"], (1, 1, 0.8))
    cyl("Pot", 0.12, 0.2, (1.25, -0.65, FLOOR + 0.1), C["coral"])
    for i, (dx, dz) in enumerate(((0, 0.38), (-0.09, 0.3), (0.1, 0.32))):
        sphere(f"Leaf{i}", 0.12, (1.25 + dx, -0.65, FLOOR + dz), C["leaf"], (1, 0.6, 1.2))
    sphere("Cushion", 0.14, (0.15, -0.6, FLOOR + 0.07), C["pink"], (1.2, 1, 0.5))
    return Vector((0, 0.1, 0.35)), 3.5, (0.05, -0.05)


def garden():
    box("Grass", (3.2, 2.2, 0.08), (0, 0.05, FLOOR - 0.04), C["grass"])
    for i in range(9):                                       # back fence
        box(f"Picket{i}", (0.1, 0.05, 0.5), (-1.45 + i * 0.36, 1.05, FLOOR + 0.25), C["off"])
    box("Rail", (3.1, 0.04, 0.05), (0, 1.03, FLOOR + 0.3), C["off"])
    for i, x in enumerate((-1.2, -0.3, 0.7)):                # hedge bumps
        sphere(f"Hedge{i}", 0.35, (x, 1.25, FLOOR + 0.25), C["hedge"], (1.6, 0.8, 1))
    box("Sign", (0.3, 0.04, 0.2), (1.2, 0.85, FLOOR + 0.45), C["wood"]); cyl("SignPost", 0.02, 0.35, (1.2, 0.86, FLOOR + 0.17), C["wood2"])
    cyl("Can", 0.07, 0.12, (-1.25, -0.55, FLOOR + 0.06), C["sky"])
    # three plots in a row behind the hippo, each a different stage
    for i, x in enumerate((-0.95, 0.0, 0.95)):
        box(f"Plot{i}", (0.7, 0.55, 0.08), (x, 0.45, FLOOR + 0.04), C["soil"])
        y, z0 = 0.45, FLOOR + 0.08
        if i == 0:      # 싹
            cyl("Stem0", 0.012, 0.1, (x, y, z0 + 0.05), C["leaf"])
            for s in (-1, 1): sphere(f"SL{s}", 0.04, (x + s * 0.04, y, z0 + 0.1), C["leaf"], (1.3, 0.5, 0.6))
        elif i == 1:    # 자람 (봉오리)
            cyl("Stem1", 0.014, 0.25, (x, y, z0 + 0.125), C["leaf"])
            for s in (-1, 1): sphere(f"ML{s}", 0.06, (x + s * 0.06, y, z0 + 0.12), C["leaf"], (1.4, 0.5, 0.7))
            sphere("Bud", 0.045, (x, y, z0 + 0.27), C["coral"], (0.8, 0.8, 1.2))
        else:           # 꽃 (수확 가능)
            cyl("Stem2", 0.015, 0.32, (x, y, z0 + 0.16), C["leaf"])
            for s in (-1, 1): sphere(f"FL{s}", 0.07, (x + s * 0.07, y, z0 + 0.14), C["leaf"], (1.4, 0.5, 0.7))
            sphere("Flower", 0.08, (x, y, z0 + 0.36), C["coral"], (1, 1, 1.1))
    return Vector((0, 0.15, 0.2)), 3.5, (0.0, -0.45)


def yard():
    box("Grass", (4.0, 3.0, 0.08), (0, 0.3, FLOOR - 0.04), C["grass"])
    for i, x in enumerate((-1.6, -0.6, 0.5, 1.6)):
        sphere(f"Hedge{i}", 0.4, (x, 1.75, FLOOR + 0.3), C["hedge"], (1.5, 0.8, 1))
    cyl("Trunk", 0.08, 0.7, (-1.4, 1.2, FLOOR + 0.35), C["wood2"]); sphere("Crown", 0.45, (-1.4, 1.2, FLOOR + 1.0), C["leaf"])
    pond = cyl("Pond", 0.55, 0.02, (1.0, 0.9, FLOOR + 0.01), C["water"]); pond.scale = (1.4, 1, 1)
    box("Bench", (0.7, 0.25, 0.05), (-0.6, 1.1, FLOOR + 0.16), C["wood"]); box("BenchBack", (0.7, 0.04, 0.2), (-0.6, 1.22, FLOOR + 0.3), C["wood"])
    for i in range(5):
        sphere(f"Path{i}", 0.12, (0.1 + i * 0.1, -0.5 + i * 0.32, FLOOR + 0.0), C["stone"], (1.2, 1, 0.15))
    for i in range(4):
        sphere(f"Bed{i}", 0.06, (-1.4 + i * 0.13, -0.6, FLOOR + 0.1), C["coral" if i % 2 else "yellow"])
    return Vector((0, 0.5, 0.2)), 4.2, (0.2, -0.2)


target, width, (hx, hy) = {"room": room, "garden": garden, "yard": yard}[SCENE]()
rig = bpy.data.objects["HippoRig"]; rig.location = (hx, hy, 0)
if len(argv) > 3 and argv[3] == "close":      # close-up on the hippo to judge the face at this elevation
    target, width = Vector((hx, hy, 0.05)), 1.3

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except Exception: pass
# world = same as character renders (new world, default dark grey) so the hippo gets the same light.
# A bright world colour acts as strong ambient light and blows the hippo out (v1 blockouts had this bug).
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
RX, RY = 590, 840
sc.render.resolution_x, sc.render.resolution_y = RX, RY
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
# backdrop colour is composited afterwards (room #F0EBE4, outdoors #CDE8F5)
for n, rot, e in (("key", (50, 0, 30), 3.0), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2.0), ("bounce", (150, 0, 0), 0.7)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = e
    o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = width * RY / RX
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = target + Vector((0.35, -1, ELEV)).normalized() * 12
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.clip_end = 100
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("WROTE", OUT)
