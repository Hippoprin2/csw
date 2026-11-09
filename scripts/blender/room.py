# Room (방) scene: base room + props keyed by app item id (supabase items.id) + the real hippo.
# usage:
#   blender -b design/character/3d/rig/hippo_rig_idle.blend --python scripts/blender/room.py -- preview <out.png> [item ids...|all]
# Camera = character default (elev 0.12 ≈ 6.5°, docs/WORLD.md W2). Units: hippo height 1.0, feet z=-0.5, front = -Y.
import bpy, bmesh, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
from props import mat, obj_from_bm

FLOOR = -0.5
W = 1.35           # half width  (x -1.35 .. 1.35)
YF, YB = -2.0, 0.85   # floor runs past the bottom of the frame; back wall face
H = 3.0            # wall height above floor (taller than the frame so no gap at the top)
ELEV = 0.12
WX, WZ, WW, WH = 0.2, 0.78, 0.84, 0.74   # window centre x/z, size (sill = 창턱 수확 선반)

# ------------------------------------------------------------------ palette (ART_BIBLE 4장 + room additions)
P = {
    "wall": (0.965, 0.914, 0.847),      # #F6E9D8 크림 벽 (new)
    "wainscot": (0.91, 0.84, 0.76),     # #E8D6C2 아랫벽 (new)
    "floor": (0.86, 0.69, 0.50),        # #DBB080
    "floor2": (0.83, 0.66, 0.47),       # 판자 이음 톤
    "wood": (0.86, 0.69, 0.50), "wood2": (0.80, 0.62, 0.45),
    "mint": (0.62, 0.84, 0.76), "off": (0.99, 0.97, 0.93),
    "coral": (0.93, 0.36, 0.38), "lav": (0.82, 0.80, 0.90),
    "yellow": (0.98, 0.78, 0.25), "lemon": (1.0, 0.86, 0.35),
    "sky": (0.55, 0.82, 0.98), "skyglass": (0.80, 0.91, 0.96),
    "blue": (0.42, 0.60, 0.86), "pink": (1.0, 0.65, 0.75),
    "leaf": (0.50, 0.80, 0.55), "green": (0.50, 0.80, 0.55),
    "squirrel": (0.85, 0.57, 0.36),     # #D9925B 다람쥐 (new)
    "brown": (0.345, 0.21, 0.157),      # #583628 눈·코
    "potato": (0.55, 0.35, 0.55), "basket": (0.80, 0.62, 0.45),
}
_M = {}
def M(k, rough=0.75, emit=0.0):
    key = (k, emit)
    if key not in _M:
        _M[key] = mat(f"R_{k}_{emit}", P[k], rough, emit)
    return _M[key]


def _link(bm, name, m, weighted=True):
    for f in bm.faces: f.smooth = True
    o = obj_from_bm(bm, name, [m])
    if weighted:
        # big flat faces keep flat normals; only the bevels are smooth. Without this, smooth shading of a
        # beveled box bleeds the corner normals across the whole face (dark gradient on walls, faceted books).
        wn = o.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.mode = "FACE_AREA"; wn.weight = 100; wn.keep_sharp = True
    return o


def rbox(name, size, loc, m, r=0.25, seg=3):
    """rounded box; r = bevel as fraction of the smallest side"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * min(r, 0.42), segments=seg, affect="EDGES", clamp_overlap=True)
    o = _link(bm, name, m); o.location = loc
    return o


def sph(name, r, loc, m, scale=(1, 1, 1), seg=32):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    o = _link(bm, name, m, weighted=False); o.location = loc; o.scale = scale
    return o


def cyl(name, r, h, loc, m, r2=None, seg=40, bevel=0.3, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    if bevel:
        edges = [e for e in bm.edges if not e.is_manifold or e.calc_face_angle(0) > 0.5]
        bmesh.ops.bevel(bm, geom=edges, offset=min(r, h) * bevel, segments=3, affect="EDGES")
    o = _link(bm, name, m); o.location = loc
    if rot: o.rotation_euler = rot
    # flat caps keep sharp shading
    return o


def blob(name, balls, m, res=0.012):
    """soft plush shapes: list of (loc, radius, (sx,sy,sz)) metaballs -> mesh"""
    mb = bpy.data.metaballs.new(name); mb.resolution = res; mb.render_resolution = res; mb.threshold = 0.6
    for loc, r, s in balls:
        e = mb.elements.new(); e.co = loc; e.radius = r
        if s != (1, 1, 1):
            e.type = "ELLIPSOID"; e.size_x, e.size_y, e.size_z = [r * k * 0.5 for k in s]
    o = bpy.data.objects.new(name, mb); bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o); bpy.data.metaballs.remove(mb)
    for p in me.polygons: p.use_smooth = True
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def group(name, parts):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    for p in parts:
        p.parent = e
    return e


# ------------------------------------------------------------------ base room (free)
def base():
    parts = []
    # floor: boards = alternating tone strips running left-right (colour detail, no texture)
    parts.append(rbox("Floor", (2 * W + 1.6, YB - YF, 0.08), (0, (YF + YB) / 2, FLOOR - 0.04), M("floor", 0.8), r=0.02))
    for i in range(7):   # board seams: thin darker strips running left-right (colour detail, no texture)
        y = YB - 0.16 - i * 0.24
        parts.append(rbox(f"Seam{i}", (2 * W + 1.6, 0.012, 0.004), (0, y, FLOOR + 0.001), M("floor2", 0.8), r=0.2))
    # back wall + wainscot + baseboard
    parts.append(rbox("BackWall", (2 * W + 1.6, 0.1, H), (0, YB + 0.05, FLOOR + H / 2), M("wall", 0.9), r=0.02))
    parts.append(rbox("Wainscot", (2 * W + 1.6, 0.03, 0.5), (0, YB - 0.01, FLOOR + 0.25), M("wainscot", 0.9), r=0.1))
    parts.append(rbox("Rail", (2 * W + 1.6, 0.05, 0.035), (0, YB - 0.02, FLOOR + 0.51), M("wood2"), r=0.3))
    parts.append(rbox("Baseboard", (2 * W + 1.6, 0.04, 0.06), (0, YB - 0.02, FLOOR + 0.03), M("wood2"), r=0.3))
    # no side wall: at this near-frontal camera it only showed as a dark strip and threw a big shadow on the back wall
    # window above the hippo + sill (= 창턱 수확 선반)
    wx, wz, ww, wh = WX, WZ, WW, WH
    parts.append(rbox("WinFrame", (ww, 0.06, wh), (wx, YB - 0.02, wz), M("off", 0.7), r=0.18))
    parts.append(rbox("WinGlass", (ww - 0.1, 0.03, wh - 0.1), (wx, YB - 0.045, wz), M("skyglass", 0.4, 0.6), r=0.15))
    parts.append(rbox("WinBarV", (0.03, 0.04, wh - 0.08), (wx, YB - 0.06, wz), M("off", 0.7), r=0.4))
    parts.append(rbox("WinBarH", (ww - 0.08, 0.04, 0.03), (wx, YB - 0.06, wz), M("off", 0.7), r=0.4))
    for i, (cx, cz, s) in enumerate(((-0.08, 0.1, 1.0), (0.04, 0.12, 0.8), (0.16, -0.12, 0.7))):   # little clouds
        sph(f"Cloud{i}", 0.04 * s, (wx + cx, YB - 0.05, wz + cz), M("off", 0.6, 0.4), (2.2, 0.3, 1))
        parts.append(bpy.data.objects[f"Cloud{i}"])
    parts.append(rbox("Sill", (ww + 0.22, 0.16, 0.045), (wx, YB - 0.08, wz - wh / 2 - 0.02), M("wood"), r=0.3))
    for o in parts:
        if o.name.startswith(("BackWall", "LeftWall", "Wainscot", "Floor", "Seam")):
            o.visible_shadow = False   # walls/floor receive but never cast (no big wall shadow)
    return group("Base", parts)


SILL_Z = WZ - WH / 2 - 0.02 + 0.0225   # top of sill
SILL_Y = YB - 0.09


def harvest_sweet_potato():
    """고구마 바구니 on the sill (first crop decoration)"""
    x = WX + 0.3
    parts = [cyl("BasketBody", 0.075, 0.06, (x, SILL_Y, SILL_Z + 0.03), M("basket", 0.8), r2=0.09, bevel=0.25)]
    for i, (dx, dz, rz) in enumerate(((-0.03, 0.07, 0.4), (0.035, 0.075, -0.3), (0.0, 0.095, 0.1))):
        o = sph(f"Potato{i}", 0.035, (x + dx, SILL_Y, SILL_Z + dz), M("potato", 0.7), (1.6, 0.9, 0.9))
        o.rotation_euler = (0, rz, 0.3); parts.append(o)
    return group("harvest_sweet_potato", parts)


# ------------------------------------------------------------------ items (id = supabase items.id)
def bed():
    x0, x1 = -1.2, -0.22; L = x1 - x0; y = YB - 0.36; Wd = 0.62
    cx = (x0 + x1) / 2
    top = FLOOR + 0.31                      # mattress top
    parts = [
        rbox("BedBase", (L, Wd, 0.14), (cx, y, FLOOR + 0.11), M("wood"), r=0.35),
        rbox("Headboard", (0.1, Wd + 0.06, 0.56), (x0 - 0.03, y, FLOOR + 0.3), M("wood2"), r=0.5),
        rbox("Footboard", (0.09, Wd + 0.04, 0.34), (x1 + 0.03, y, FLOOR + 0.2), M("wood2"), r=0.5),
        rbox("Mattress", (L - 0.02, Wd - 0.02, 0.14), (cx, y, top - 0.07), M("off", 0.85), r=0.5),
        sph("Pillow", 0.14, (x0 + 0.19, y + 0.02, top + 0.06), M("off", 0.85), (1.05, 1.85, 0.55)),
    ]
    # puffy blanket over the foot 60%, overhanging the front side and folded back at the top
    bl0 = x0 + L * 0.36
    parts.append(rbox("Blanket", (x1 - bl0, Wd + 0.06, 0.08), ((bl0 + x1) / 2, y, top + 0.03), M("mint", 0.9), r=0.5))
    parts.append(rbox("BlanketDrape", (x1 - bl0, 0.05, 0.2), ((bl0 + x1) / 2, y - Wd / 2 - 0.035, top - 0.07), M("mint", 0.9), r=0.45))
    parts.append(sph("BlanketFold", 0.055, (bl0 + 0.02, y, top + 0.05), M("off", 0.85), (1.0, (Wd + 0.08) / 0.11, 0.85)))   # rolled top edge
    for i, (dx, dz) in enumerate(((0.12, 0.0), (0.3, 0.0), (0.21, -0.1), (0.4, -0.1))):   # dots on the drape
        parts.append(sph(f"Dot{i}", 0.022, (bl0 + 0.08 + dx, y - Wd / 2 - 0.062, top - 0.03 + dz), M("off", 0.85), (1, 0.3, 1)))
    return group("bed", parts)


def bookshelf():
    x, w, d, h = 0.92, 0.58, 0.3, 1.02; y = YB - d / 2 - 0.01
    parts = [rbox("ShelfBack", (w, 0.03, h), (x, YB - 0.02, FLOOR + h / 2), M("wood2"), r=0.3)]
    for sx in (-1, 1):
        parts.append(rbox(f"ShelfSide{sx}", (0.05, d, h), (x + sx * (w / 2 - 0.025), y, FLOOR + h / 2), M("wood"), r=0.35))
    levels = [0.03, 0.36, 0.69, h - 0.025]
    for i, z in enumerate(levels):
        parts.append(rbox(f"ShelfBoard{i}", (w, d, 0.045), (x, y, FLOOR + z), M("wood"), r=0.35))
    # books: (width, height, colour, tilt)
    rows = [
        [(0.07, 0.24, "coral", 0), (0.06, 0.27, "blue", 0), (0.08, 0.22, "yellow", 0), (0.06, 0.25, "lav", 0), (0.07, 0.2, "mint", 0.0)],
        [(0.06, 0.25, "mint", 0), (0.07, 0.22, "pink", 0), (0.06, 0.26, "blue", 0)],
    ]
    for r, row in enumerate(rows):
        bx = x - w / 2 + 0.07
        for i, (bw, bh, col, tilt) in enumerate(row):
            o = rbox(f"Book{r}{i}", (bw, d * 0.75, bh), (bx + bw / 2, y, FLOOR + levels[r] + 0.0225 + bh / 2), M(col), r=0.12, seg=2)
            if tilt:
                o.rotation_euler = (0, tilt, 0); o.location.x += 0.03; o.location.z -= 0.012
            parts.append(o); bx += bw + 0.008
    # middle shelf right side: little pot plant; top: ball + small box
    z2 = FLOOR + levels[1] + 0.0225
    parts.append(cyl("ShelfPot", 0.055, 0.09, (x + 0.17, y, z2 + 0.045), M("coral"), r2=0.045, bevel=0.2))
    for i, (dx, dz, s) in enumerate(((0, 0.13, 1), (-0.035, 0.1, 0.8), (0.04, 0.11, 0.8))):
        parts.append(sph(f"ShelfLeaf{i}", 0.045 * s, (x + 0.17 + dx, y, z2 + dz), M("leaf"), (1, 0.8, 1.3)))
    z3 = FLOOR + levels[2] + 0.0225
    parts.append(sph("ShelfBall", 0.07, (x - 0.15, y, z3 + 0.07), M("yellow", 0.6)))
    parts.append(rbox("ShelfBox", (0.16, 0.18, 0.1), (x + 0.12, y, z3 + 0.05), M("lav"), r=0.3))
    return group("bookshelf", parts)


def squirrel():
    """다람쥐 인형: sitting plush, big curled tail, cream belly, button eyes. ~0.33 tall."""
    m, c = M("squirrel", 0.85), M("off", 0.85)
    parts = [
        sph("SqBody", 0.105, (0, 0, 0.1), m, (1, 0.9, 1.05)),
        sph("SqHead", 0.095, (0, -0.01, 0.235), m, (1.08, 0.95, 0.95)),
        sph("SqBelly", 0.075, (0, -0.045, 0.095), c, (0.95, 0.75, 1.0)),
        sph("SqMuzzle", 0.045, (0, -0.07, 0.215), c, (1.35, 0.8, 0.85)),
        sph("SqNose", 0.014, (0, -0.108, 0.232), M("brown", 0.5)),
    ]
    for sx in (-1, 1):
        parts += [
            sph(f"SqEar{sx}", 0.032, (sx * 0.06, 0.0, 0.32), m, (0.8, 0.55, 1.3)),
            sph(f"SqEarIn{sx}", 0.018, (sx * 0.06, -0.016, 0.318), M("pink", 0.8), (0.8, 0.4, 1.2)),
            sph(f"SqFoot{sx}", 0.04, (sx * 0.055, -0.06, 0.025), m, (1.0, 1.4, 0.65)),
            sph(f"SqPaw{sx}", 0.03, (sx * 0.075, -0.07, 0.13), m, (0.9, 1.0, 1.25)),
            sph(f"SqEye{sx}", 0.014, (sx * 0.042, -0.083, 0.258), M("brown", 0.35), (1, 0.6, 1.2)),
            sph(f"SqCheek{sx}", 0.017, (sx * 0.066, -0.07, 0.205), M("pink", 0.8), (1, 0.4, 0.7)),
        ]
    # tail: overlapping spheres rising behind the body and curling forward at the top
    for i, (ty, tz, r) in enumerate(((0.09, 0.05, 0.065), (0.13, 0.11, 0.075), (0.15, 0.18, 0.085), (0.15, 0.26, 0.088),
                                      (0.12, 0.33, 0.08), (0.07, 0.37, 0.065), (0.03, 0.375, 0.05))):
        parts.append(sph(f"SqTail{i}", r, (0, ty, tz), m if i < 6 else c))
    g = group("squirrel", parts)
    g.location = (-0.62, -0.62, FLOOR); g.rotation_euler = (0, 0, math.radians(-28)); g.scale = (1.1, 1.1, 1.1)
    return g


def lamp():
    x, y = -1.12, -0.7
    parts = [
        cyl("LampBase", 0.1, 0.035, (x, y, FLOOR + 0.0175), M("wood2"), bevel=0.4),
        cyl("LampPole", 0.014, 0.78, (x, y, FLOOR + 0.42), M("wood2"), bevel=0),
        cyl("LampShade", 0.17, 0.2, (x, y, FLOOR + 0.86), M("lemon", 0.6, 0.35), r2=0.1, bevel=0.15),
        sph("LampKnob", 0.025, (x, y, FLOOR + 0.975), M("wood2")),
    ]
    return group("lamp", parts)


ITEMS = {"bed": bed, "bookshelf": bookshelf, "squirrel": squirrel, "lamp": lamp}

# ------------------------------------------------------------------ scene, camera, render
def setup_render(rx, ry, ortho):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: sc.render.engine = eng; break
        except Exception: pass
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.9     # ART_BIBLE: never recolour the World
    for n, rot, e in (("key", (50, 0, 30), 3.0), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2.0), ("bounce", (150, 0, 0), 0.7)):
        d = bpy.data.lights.new(n, "SUN"); d.energy = e; d.angle = math.radians(12)   # soft shadows in rooms
        o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.rotation_euler = [math.radians(v) for v in rot]
    cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = ortho; cd.clip_end = 100
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    return sc, cam


# Framing: square canvas like the app room card (361x360 pt). Visible width 3.05 units -> hippo ≈ 1/3 of the card height.
TARGET = Vector((0.0, 0.0, 0.66))   # frame bottom ≈ floor, top = wall
ORTHO = 2.7

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode, out = argv[0], argv[1]
    ids = argv[2:] or ["all"]
    if ids == ["all"]:
        ids = list(ITEMS)
    elif ids == ["none"]:
        ids = []
    sc, cam = setup_render(1080, 1080, ORTHO)
    cam.location = TARGET + Vector((0.35, -1, ELEV)).normalized() * 12
    cam.rotation_euler = (TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.frame_set(1)
    base(); harvest_sweet_potato()
    for i in ids:
        ITEMS[i]()
    rig = bpy.data.objects["HippoRig"]; rig.location = (0.05, -0.25, 0)
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("WROTE", out)
