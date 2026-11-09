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
WX, WZ, WW, WH = 0.1, 0.78, 0.84, 0.74   # window centre x/z, size (sill = 창턱 수확 선반)

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
    "orange": (0.98, 0.62, 0.35),       # 물고기·라디오 포인트
    "water": (0.62, 0.84, 0.95), "pebble": (0.85, 0.82, 0.78),
    "string": (0.55, 0.45, 0.38),
    "confetti_r": (0.98, 0.45, 0.45), "confetti_y": (0.99, 0.80, 0.30), "confetti_g": (0.50, 0.80, 0.55),
    "confetti_b": (0.45, 0.70, 0.98), "confetti_p": (0.85, 0.55, 0.95), "confetti_k": (1.0, 0.65, 0.75),
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
        wn = o.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.mode = "FACE_AREA"; wn.weight = 50; wn.keep_sharp = True
    return o


def rbox(name, size, loc, m, r=0.25, seg=5):
    """rounded box; r = bevel as fraction of the smallest side"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * min(r, 0.42), segments=seg, affect="EDGES", profile=0.5, clamp_overlap=True)
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
        bmesh.ops.bevel(bm, geom=edges, offset=min(r, h) * bevel, segments=3, affect="EDGES", profile=0.5)
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
    parts.append(rbox("Sill", (ww + 0.14, 0.16, 0.045), (wx, YB - 0.08, wz - wh / 2 - 0.02), M("wood"), r=0.3))
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
    x0, x1 = -1.05, -0.07; L = x1 - x0; y = YB - 0.36; Wd = 0.62
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
    x, w, d, h = 0.86, 0.58, 0.3, 1.02; y = YB - d / 2 - 0.01
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
    g.location = (*FRONT_CENTER, FLOOR); g.rotation_euler = (0, 0, math.radians(-28)); g.scale = (1.1, 1.1, 1.1)
    return g


def lamp():
    x, y = -0.74, -0.72      # pole stays clear of the bedside column (radio/aquarium)
    parts = [
        cyl("LampBase", 0.1, 0.035, (x, y, FLOOR + 0.0175), M("wood2"), bevel=0.4),
        cyl("LampPole", 0.014, 0.78, (x, y, FLOOR + 0.42), M("wood2"), bevel=0),
        cyl("LampShade", 0.17, 0.2, (x, y, FLOOR + 0.86), M("lemon", 0.6, 0.35), r2=0.1, bevel=0.15),
        sph("LampKnob", 0.025, (x, y, FLOOR + 0.975), M("wood2")),
    ]
    return group("lamp", parts)


def tri(name, w, h, loc, m, thick=0.012):
    """little rounded pennant hanging from its top edge, tip pointing down, facing the camera"""
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-w / 2, 0, 0), (0, 0, -h), (w / 2, 0, 0))]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, thick, 0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=thick * 0.45, segments=2, affect="EDGES", profile=0.5, clamp_overlap=True)
    o = _link(bm, name, m); o.location = (loc[0], loc[1] - thick, loc[2] + 0.06)
    o.rotation_euler = (0, 0, math.radians(-19))      # square to the 3/4 camera
    return o


def sag(x0, x1, z, depth, n):
    """points along a hanging string on the back wall"""
    return [(x0 + (x1 - x0) * t, z - depth * 4 * t * (1 - t)) for t in [k / (n - 1) for k in range(n)]]


def rope(name, pts, y, m, r=0.006):
    parts = []
    for k in range(len(pts) - 1):
        (xa, za), (xb, zb) = pts[k], pts[k + 1]
        L = math.hypot(xb - xa, zb - za)
        o = cyl(f"{name}{k}", r, L + r, ((xa + xb) / 2, y, (za + zb) / 2), m, bevel=0, seg=8)
        o.rotation_euler = (0, -math.atan2(zb - za, xb - xa) + math.pi / 2, 0)
        parts.append(o)
    return parts


WALL_Y = YB - 0.02          # things hung on the back wall


# --- free base decoration: small calendar (대표 결정: 처음 방 벽에 무료 장식 1개)
def calendar():
    x, z = -1.36, 0.95
    parts = [
        rbox("CalPaper", (0.24, 0.02, 0.3), (x, WALL_Y - 0.01, z), M("off", 0.85), r=0.3),
        rbox("CalTop", (0.26, 0.03, 0.05), (x, WALL_Y - 0.02, z + 0.15), M("coral"), r=0.4),
        rbox("CalPic", (0.18, 0.012, 0.11), (x, WALL_Y - 0.025, z + 0.05), M("skyglass", 0.7), r=0.3),
        sph("CalSun", 0.022, (x + 0.045, WALL_Y - 0.032, z + 0.075), M("yellow", 0.6), (1, 0.3, 1)),
        sph("CalHill", 0.07, (x - 0.02, WALL_Y - 0.03, z + 0.0), M("leaf"), (1.2, 0.2, 0.45)),
        sph("CalPin", 0.014, (x, WALL_Y - 0.04, z + 0.17), M("brown", 0.5)),
    ]
    for r in range(2):      # a couple of text-like lines (no dates, nothing to tick off)
        parts.append(rbox(f"CalLine{r}", (0.15 - r * 0.04, 0.008, 0.012), (x, WALL_Y - 0.025, z - 0.06 - r * 0.035), M("wainscot"), r=0.4))
    return group("calendar", parts)


# --- wall
def frame():
    """액자(단짝 그림): pink frame, little hippo face drawing"""
    x, z = -0.78, 0.92
    P.setdefault("hippo", (0.95, 0.81, 0.65))
    parts = [
        rbox("FrOuter", (0.34, 0.03, 0.28), (x, WALL_Y - 0.01, z), M("pink"), r=0.3),
        rbox("FrInner", (0.27, 0.02, 0.21), (x, WALL_Y - 0.022, z), M("off", 0.85), r=0.25),
        sph("FrHead", 0.06, (x, WALL_Y - 0.033, z - 0.012), M("hippo", 0.8), (1.3, 0.15, 1.0)),
    ]
    for sx in (-1, 1):
        parts += [sph(f"FrEar{sx}", 0.018, (x + sx * 0.05, WALL_Y - 0.033, z + 0.045), M("hippo", 0.8), (1, 0.15, 1)),
                  sph(f"FrEye{sx}", 0.008, (x + sx * 0.03, WALL_Y - 0.042, z + 0.005), M("brown", 0.5), (1, 0.3, 1.2)),
                  sph(f"FrNose{sx}", 0.006, (x + sx * 0.018, WALL_Y - 0.042, z - 0.04), M("brown", 0.5), (1, 0.3, 1)),
                  sph(f"FrCheek{sx}", 0.011, (x + sx * 0.055, WALL_Y - 0.04, z - 0.025), M("pink", 0.8), (1, 0.2, 0.7))]
    return group("frame", parts)


def wall_clock():
    x, z = 0.86, 0.86
    parts = [
        cyl("ClRim", 0.13, 0.05, (x, WALL_Y - 0.02, z), M("yellow", 0.6), bevel=0.4, rot=(math.radians(90), 0, 0)),
        cyl("ClFace", 0.105, 0.02, (x, WALL_Y - 0.04, z), M("off", 0.8), bevel=0.3, rot=(math.radians(90), 0, 0)),
        sph("ClCenter", 0.012, (x, WALL_Y - 0.055, z), M("brown", 0.5)),
    ]
    h1 = rbox("ClHour", (0.014, 0.008, 0.055), (x + 0.018, WALL_Y - 0.052, z + 0.02), M("brown", 0.5), r=0.4); h1.rotation_euler = (0, math.radians(40), 0)
    h2 = rbox("ClMin", (0.01, 0.008, 0.08), (x - 0.005, WALL_Y - 0.054, z + 0.038), M("coral"), r=0.4); h2.rotation_euler = (0, math.radians(-8), 0)
    parts += [h1, h2]
    for k in range(4):
        a = k * math.pi / 2
        parts.append(sph(f"ClTick{k}", 0.009, (x + 0.08 * math.sin(a), WALL_Y - 0.05, z + 0.08 * math.cos(a)), M("lav"), (1, 0.4, 1)))
    return group("wall_clock", parts)


GARLAND = (-1.45, 0.75, 1.62, 0.16)    # x0, x1, z, sag


def garland():
    x0, x1, z, d = GARLAND
    pts = sag(x0, x1, z, d, 24)
    parts = rope("GaRope", pts, WALL_Y - 0.03, M("string", 0.8))
    cols = ["confetti_r", "confetti_y", "confetti_g", "confetti_b", "confetti_p", "confetti_k"]
    for k, (px, pz) in enumerate(sag(x0, x1, z, d, 11)[1:-1]):
        parts.append(tri(f"GaFlag{k}", 0.11, 0.13, (px, WALL_Y - 0.035, pz - 0.06), M(cols[k % 6], 0.8)))
    return group("garland", parts)


def string_lights():
    x0, x1, z, d = GARLAND
    parts = rope("SlWire", sag(x0, x1, z, d, 24), WALL_Y - 0.03, M("string", 0.8), r=0.004)
    cols = ["lemon", "confetti_k", "lemon", "mint", "lemon", "lav"]
    for k, (px, pz) in enumerate(sag(x0, x1, z, d, 14)[1:-1]):
        parts.append(cyl(f"SlCap{k}", 0.012, 0.02, (px, WALL_Y - 0.035, pz - 0.012), M("string", 0.7), bevel=0.3))
        parts.append(sph(f"SlBulb{k}", 0.026, (px, WALL_Y - 0.04, pz - 0.045), M(cols[k % 6], 0.4, 1.6), (0.9, 0.9, 1.25)))
    return group("string_lights", parts)


def mobile():
    """천장 모빌: wooden bar with a cloud, star, moon hanging (strings go up out of frame)"""
    x, z = -0.42, 1.42; y = 0.35
    parts = [rbox("MoBar", (0.42, 0.025, 0.025), (x, y, z), M("wood2"), r=0.4)]
    parts += rope("MoTop", [(x, z), (x, z + 0.8)], y, M("string", 0.8), r=0.004)
    hangs = [(-0.18, 0.2, "cloud"), (0.0, 0.3, "star"), (0.18, 0.17, "moon")]
    for k, (dx, L, kind) in enumerate(hangs):
        hx, hz = x + dx, z - L
        parts += rope(f"MoStr{k}", [(hx, z), (hx, hz + 0.04)], y, M("string", 0.8), r=0.003)
        if kind == "cloud":
            for j, (cx, cz, r) in enumerate(((-0.03, 0, 0.035), (0.01, 0.015, 0.045), (0.045, -0.003, 0.032))):
                parts.append(sph(f"MoCloud{j}", r, (hx + cx, y, hz + cz), M("off", 0.8), (1, 0.6, 1)))
        elif kind == "star":
            bm = bmesh.new()
            pts = [(0.06 if q % 2 == 0 else 0.026) for q in range(10)]
            verts = [bm.verts.new((pts[q] * math.sin(q * math.pi / 5), 0, pts[q] * math.cos(q * math.pi / 5))) for q in range(10)]
            f = bm.faces.new(verts)
            ext = bmesh.ops.extrude_face_region(bm, geom=[f])
            bmesh.ops.translate(bm, vec=(0, 0.025, 0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.008, segments=2, affect="EDGES", profile=0.5, clamp_overlap=True)
            o = _link(bm, "MoStar", M("yellow", 0.6)); o.location = (hx, y - 0.012, hz); parts.append(o)
        else:
            o = sph("MoMoon", 0.045, (hx, y, hz), M("lemon", 0.6), (1, 0.45, 1))
            cut = sph("MoMoonCut", 0.04, (hx + 0.025, y, hz + 0.012), M("lemon"), (1, 0.6, 1))
            bo = o.modifiers.new("cut", "BOOLEAN"); bo.object = cut; bo.operation = "DIFFERENCE"; cut.hide_render = True
            parts += [o, cut]
    return group("mobile", parts)


def curtain():
    """커튼: two gathered pink panels tied back + rod over the window"""
    x0, x1 = WX - WW / 2, WX + WW / 2; top = WZ + WH / 2 + 0.06; y = YB - 0.07
    parts = [cyl("CuRod", 0.012, WW + 0.36, (WX, y, top), M("wood2"), bevel=0, rot=(0, math.radians(90), 0))]
    for sx, xe in ((-1, x0), (1, x1)):
        parts.append(sph(f"CuKnob{sx}", 0.024, (WX + sx * (WW / 2 + 0.18), y, top), M("wood2")))
        for k in range(3):                       # three soft folds per panel
            fx = xe + sx * (0.02 + k * 0.045)
            parts.append(rbox(f"CuFold{sx}{k}", (0.06, 0.05, WH + 0.05), (fx, y - 0.01 * (k % 2), top - (WH + 0.05) / 2), M("pink", 0.9), r=0.45))
        parts.append(rbox(f"CuTie{sx}", (0.17, 0.065, 0.035), (xe + sx * 0.065, y - 0.02, top - WH * 0.58), M("off", 0.8), r=0.45))
    return group("curtain", parts)


# --- floor / furniture
HIPPO = (0.05, -0.25)


def rug():
    x, y = HIPPO
    parts = [cyl("RugEdge", 0.62, 0.016, (x, y + 0.05, FLOOR + 0.008), M("off", 0.9), bevel=0.4),
             cyl("RugIn", 0.53, 0.02, (x, y + 0.05, FLOOR + 0.01), M("lav", 0.9), bevel=0.4)]
    for o in parts: o.scale = (1.35, 1, 1)
    return group("rug", parts)


FRONT_CENTER = (-0.36, -0.78)


def cushion():
    """쿠션(방석): round floor cushion with a button and piping"""
    x, y = FRONT_CENTER
    parts = [cyl("CuBase", 0.2, 0.09, (x, y, FLOOR + 0.045), M("yellow", 0.85), bevel=0.45),
             sph("CuTop", 0.19, (x, y, FLOOR + 0.085), M("yellow", 0.85), (1, 1, 0.22)),
             sph("CuButton", 0.022, (x, y, FLOOR + 0.13), M("coral"), (1, 1, 0.6))]
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        parts.append(sph(f"CuTuft{k}", 0.025, (x + 0.205 * math.cos(a), y + 0.205 * math.sin(a), FLOOR + 0.06), M("coral", 0.85)))
    return group("cushion", parts)


def big_plant():
    """큰 화분: off-white pot with coral band, round leaves on short stems"""
    x, y = 1.3, -0.82
    parts = [cyl("PlPot", 0.12, 0.2, (x, y, FLOOR + 0.1), M("off", 0.8), r2=0.1, bevel=0.2),
             cyl("PlBand", 0.126, 0.035, (x, y, FLOOR + 0.17), M("coral"), bevel=0.3),
             cyl("PlSoil", 0.11, 0.02, (x, y, FLOOR + 0.195), M("string", 0.9), bevel=0)]
    base_z = FLOOR + 0.2
    leaves = [(0, 0.34, 0.075), (-28, 0.27, 0.07), (30, 0.28, 0.07), (-55, 0.2, 0.06), (58, 0.21, 0.06), (-10, 0.22, 0.065), (12, 0.25, 0.065)]
    for k, (tilt, h, r) in enumerate(leaves):
        a = math.radians(tilt); dy = 0.03 * ((k % 3) - 1)
        tip = Vector((x + math.sin(a) * h, y + dy, base_z + math.cos(a) * h))
        stem = cyl(f"PlStem{k}", 0.007, h, (x + math.sin(a) * h / 2, y + dy, base_z + math.cos(a) * h / 2), M("green"), bevel=0, seg=8)
        stem.rotation_euler = (0, a, 0)
        leaf = sph(f"PlLeaf{k}", r, tip, M("leaf", 0.75), (1.0, 0.3, 1.25))
        leaf.rotation_euler = (math.radians(10), a * 0.8, math.radians(-19))
        parts += [stem, leaf]
    return group("big_plant", parts)


def low_table():
    """좌식 탁자 + 찻주전자·찻잔"""
    x, y = 0.82, -0.32; w, d, h = 0.48, 0.32, 0.2
    parts = [rbox("TbTop", (w, d, 0.045), (x, y, FLOOR + h), M("wood"), r=0.4)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl(f"TbLeg{sx}{sy}", 0.022, h - 0.02, (x + sx * (w / 2 - 0.05), y + sy * (d / 2 - 0.05), FLOOR + (h - 0.02) / 2), M("wood2"), bevel=0.3))
    t = FLOOR + h + 0.0225
    parts += [sph("TbPot", 0.06, (x - 0.08, y + 0.03, t + 0.055), M("mint", 0.7), (1.1, 1.1, 0.9)),
              sph("TbPotLid", 0.025, (x - 0.08, y + 0.03, t + 0.11), M("off", 0.7)),
              cyl("TbSpout", 0.012, 0.07, (x - 0.15, y + 0.03, t + 0.07), M("mint", 0.7), r2=0.008, bevel=0, rot=(0, math.radians(-50), 0)),
              cyl("TbCup", 0.03, 0.045, (x + 0.1, y - 0.05, t + 0.0225), M("off", 0.7), r2=0.025, bevel=0.3),
              cyl("TbTea", 0.026, 0.004, (x + 0.1, y - 0.05, t + 0.044), M("orange", 0.5), bevel=0)]
    return group("low_table", parts)


BEDSIDE = (-1.45, YB - 0.2)


def _bedside_table(x, y, parts):
    """협탁 v2: overhanging rounded wood top, mint body with one drawer + knob, open cubby, short round legs"""
    w, d = 0.28, 0.24
    leg_h, body_h, top_t = 0.07, 0.2, 0.035
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl(f"BsLeg{sx}{sy}", 0.018, leg_h + 0.01, (x + sx * (w / 2 - 0.035), y + sy * (d / 2 - 0.035), FLOOR + leg_h / 2), M("wood2"), r2=0.014, bevel=0.3))
    zb = FLOOR + leg_h
    parts += [
        rbox("BsBody", (w, d, body_h), (x, y, zb + body_h / 2), M("mint", 0.75), r=0.18),
        rbox("BsCubby", (w - 0.05, 0.02, 0.07), (x, y - d / 2 + 0.006, zb + 0.05), M("wood2", 0.85), r=0.3),     # dark inset = open shelf
        rbox("BsDrawer", (w - 0.05, 0.02, 0.085), (x, y - d / 2 - 0.004, zb + 0.145), M("off", 0.8), r=0.3),
        sph("BsKnob", 0.017, (x, y - d / 2 - 0.02, zb + 0.145), M("coral", 0.6)),
        rbox("BsTop", (w + 0.05, d + 0.04, top_t), (x, y, zb + body_h + top_t / 2), M("wood"), r=0.4),
    ]
    return zb + body_h + top_t


def radio_stand():
    x, y = BEDSIDE; parts = []
    top = _bedside_table(x, y, parts)
    parts += [rbox("RaBody", (0.22, 0.11, 0.13), (x, y, top + 0.065), M("coral", 0.7), r=0.35),
              cyl("RaSpeaker", 0.042, 0.012, (x - 0.045, y - 0.056, top + 0.06), M("off", 0.8), bevel=0.3, rot=(math.radians(90), 0, 0)),
              sph("RaDial", 0.018, (x + 0.06, y - 0.058, top + 0.075), M("yellow", 0.6), (1, 0.5, 1)),
              rbox("RaHandle", (0.14, 0.02, 0.02), (x, y, top + 0.15), M("brown", 0.6), r=0.45)]
    ant = cyl("RaAntenna", 0.005, 0.16, (x + 0.07, y, top + 0.2), M("string", 0.5), bevel=0, seg=8); ant.rotation_euler = (0, math.radians(25), 0)
    parts += [ant, sph("RaAntTip", 0.012, (x + 0.104, y, top + 0.272), M("coral"))]
    for k in range(3):
        parts.append(sph(f"RaDot{k}", 0.006, (x - 0.045 + (k - 1) * 0.018, y - 0.064, top + 0.06), M("lav"), (1, 0.4, 1)))
    return group("radio_stand", parts)


def aquarium():
    """어항 v2: tinted see-through tank (no opaque water block, so the fish show), 2 fish, weeds, bubbles"""
    x, y = BEDSIDE; parts = []
    top = _bedside_table(x, y, parts)
    w, d, h = 0.25, 0.15, 0.19
    glass = rbox("AqGlass", (w, d, h), (x, y, top + h / 2), mat("R_aqglass2", (0.70, 0.88, 0.97), 0.1, alpha=0.26), r=0.12)
    m = glass.active_material
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        m.blend_method = "BLEND"
    m.use_backface_culling = True
    parts += [glass,
              rbox("AqRim", (w + 0.012, d + 0.012, 0.02), (x, y, top + h), M("mint", 0.7), r=0.4),
              rbox("AqSand", (w - 0.02, d - 0.02, 0.03), (x, y, top + 0.02), M("pebble", 0.9), r=0.4)]
    for k, (px, col) in enumerate(((-0.07, "coral"), (-0.04, "lemon"), (0.075, "lav"))):
        parts.append(sph(f"AqPebble{k}", 0.014, (x + px, y - 0.02, top + 0.038), M(col, 0.8), (1.2, 1, 0.7)))
    for k in range(3):
        parts.append(sph(f"AqWeed{k}", 0.022, (x + 0.085 - k * 0.012, y + 0.02, top + 0.06 + k * 0.03), M("leaf"), (0.6, 0.6, 1.6)))
    # fish face the camera-ish, big enough to read at room scale
    for k, (fx, fz, col, flip) in enumerate(((-0.05, 0.12, "orange", 1), (0.035, 0.075, "lemon", -1))):
        fy = y - 0.01
        body = sph(f"AqFish{k}", 0.032, (x + fx, fy, top + fz), M(col, 0.6), (1.35, 0.7, 1.0))
        tail = sph(f"AqTail{k}", 0.02, (x + fx - flip * 0.045, fy, top + fz), M(col, 0.6), (0.6, 0.35, 1.25))
        eye = sph(f"AqEye{k}", 0.006, (x + fx + flip * 0.02, fy - 0.02, top + fz + 0.008), M("brown"))
        parts += [body, tail, eye]
    for k, (bx, bz, r) in enumerate(((-0.02, 0.155, 0.006), (-0.012, 0.172, 0.008))):
        parts.append(sph(f"AqBubble{k}", r, (x + bx, y - 0.02, top + bz), M("off", 0.3)))
    return group("aquarium", parts)


LEAN = (0.4, YB - 0.16)


def easel():
    """이젤: A-frame with a small canvas (sun over a hill)"""
    x, y = LEAN; z0 = FLOOR
    parts = []
    for sx in (-1, 1):
        leg = cyl(f"EaLeg{sx}", 0.012, 0.72, (x + sx * 0.09, y, z0 + 0.35), M("wood2"), bevel=0, seg=10); leg.rotation_euler = (0, math.radians(-sx * 9), 0)
        parts.append(leg)
    back = cyl("EaBack", 0.011, 0.66, (x, y + 0.12, z0 + 0.32), M("wood2"), bevel=0, seg=10); back.rotation_euler = (math.radians(-18), 0, 0)
    parts += [back, rbox("EaLedge", (0.26, 0.05, 0.025), (x, y - 0.04, z0 + 0.3), M("wood"), r=0.4),
              rbox("EaCanvas", (0.3, 0.025, 0.26), (x, y - 0.04, z0 + 0.445), M("off", 0.85), r=0.15),
              sph("EaSun", 0.035, (x + 0.06, y - 0.055, z0 + 0.5), M("yellow", 0.7), (1, 0.25, 1)),
              sph("EaHill", 0.11, (x - 0.03, y - 0.054, z0 + 0.36), M("leaf", 0.8), (1.25, 0.15, 0.55)),
              sph("EaHill2", 0.08, (x + 0.08, y - 0.056, z0 + 0.35), M("mint", 0.8), (1.1, 0.15, 0.5))]
    parts[1].rotation_euler.x = 0
    for o in parts[:2]:
        o.rotation_euler.x = math.radians(6)
    return group("easel", parts)


def guitar():
    """기타: leaning on the wall"""
    x, y = LEAN
    parts = [cyl("GuLow", 0.12, 0.06, (0, 0, 0.13), M("wood"), bevel=0.4, rot=(math.radians(90), 0, 0)),
             cyl("GuUp", 0.09, 0.06, (0, 0, 0.29), M("wood"), bevel=0.4, rot=(math.radians(90), 0, 0)),
             cyl("GuHole", 0.035, 0.01, (0, -0.031, 0.235), M("brown", 0.8), bevel=0, rot=(math.radians(90), 0, 0)),
             rbox("GuBridge", (0.08, 0.012, 0.018), (0, -0.032, 0.12), M("brown", 0.6), r=0.4),
             rbox("GuNeck", (0.045, 0.03, 0.3), (0, -0.005, 0.5), M("wood2"), r=0.35),
             rbox("GuHead", (0.07, 0.035, 0.09), (0, -0.005, 0.69), M("wood2"), r=0.4),
             rbox("GuGuard", (0.05, 0.008, 0.06), (0.05, -0.032, 0.19), M("coral"), r=0.45)]
    for k in range(4):
        parts.append(sph(f"GuPeg{k}", 0.008, ((-1) ** k * 0.04, -0.005, 0.66 + (k // 2) * 0.04), M("off")))
    for k in range(3):
        parts.append(rbox(f"GuStr{k}", (0.0025, 0.004, 0.48), ((k - 1) * 0.011, -0.034, 0.36), M("off", 0.4), r=0.3))
    parts.append(rbox("GuHook", (0.05, 0.04, 0.03), (0, 0.03, 0.7), M("wood2"), r=0.4))
    g = group("guitar", parts)
    # hung on the wall (on the floor it hid behind the low table / plant)
    g.location = (x - 0.02, WALL_Y - 0.06, FLOOR + 0.3); g.rotation_euler = (0, math.radians(-6), math.radians(-19))
    return g


ITEMS = {"bed": bed, "bookshelf": bookshelf, "squirrel": squirrel, "lamp": lamp,
         "frame": frame, "wall_clock": wall_clock, "garland": garland, "string_lights": string_lights,
         "mobile": mobile, "curtain": curtain, "rug": rug, "cushion": cushion, "big_plant": big_plant,
         "low_table": low_table, "radio_stand": radio_stand, "aquarium": aquarium, "easel": easel, "guitar": guitar}
# slot alternatives (same slot -> only one shown at a time)
SET_A = ["bed", "bookshelf", "squirrel", "lamp", "frame", "wall_clock", "garland", "mobile", "curtain", "rug",
         "big_plant", "low_table", "radio_stand", "easel"]
SET_B = ["bed", "bookshelf", "cushion", "lamp", "frame", "wall_clock", "string_lights", "mobile", "curtain", "rug",
         "big_plant", "low_table", "aquarium", "guitar"]

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

def item_parts(g):
    out = []
    def rec(o):
        for c in o.children:
            if c.type == "MESH" and not c.hide_render: out.append(c)
            rec(c)
    rec(g)
    return out


THUMB_ELEV = 0.45    # shop thumbnails look a bit from above so rugs/cushions/tables read (room itself stays 0.12)


def frame_on(cam, objs, elev=THUMB_ELEV, pad=1.12):
    """point a fixed-direction ortho camera at the screen-space bbox of objs"""
    d = Vector((0.35, -1, elev)).normalized()           # target -> camera
    right = Vector((1, 0.35, 0)).normalized()
    up = d.cross(right).normalized()
    if up.z < 0: up = -up
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    xs = [p.dot(right) for p in pts]; ys = [p.dot(up) for p in pts]; zs = [p.dot(d) for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * pad
    center = right * cx + up * cy + d * ((min(zs) + max(zs)) / 2)
    cam.location = center + d * 12
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    mode, out = argv[0], argv[1]
    ids = argv[2:] or ["all"]
    ids = {"all": SET_A, "a": SET_A, "b": SET_B, "none": []}.get(ids[0], ids) if len(ids) == 1 else ids
    if mode == "preview":
        sc, cam = setup_render(1080, 1080, ORTHO)
        cam.location = TARGET + Vector((0.35, -1, ELEV)).normalized() * 12
        cam.rotation_euler = (TARGET - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.frame_set(1)
        base(); calendar(); harvest_sweet_potato()
        for i in ids:
            ITEMS[i]()
        rig = bpy.data.objects["HippoRig"]; rig.location = (*HIPPO, 0)
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print("WROTE", out)
    elif mode == "thumbs":
        # shop thumbnails: each item alone, same light/direction, framed tight, transparent 512x512
        sc, cam = setup_render(512, 512, 1.0)
        for o in ("Hippo", "EyeDecal", "HippoRig"):
            bpy.data.objects[o].hide_render = True
        os.makedirs(out, exist_ok=True)
        groups = {i: ITEMS[i]() for i in (ids or list(ITEMS))}
        for i, g in groups.items():
            for j, h in groups.items():
                for c in item_parts(h) if j != i else []:
                    c.hide_render = True
            frame_on(cam, [c for c in item_parts(g) if not c.name.startswith("MoTop")])
            sc.render.filepath = os.path.join(out, f"{i}.png")
            bpy.ops.render.render(write_still=True)
            for j, h in groups.items():
                for c in h.children_recursive:
                    if c.type == "MESH" and not c.name.startswith(("MoMoonCut",)):
                        c.hide_render = False
            print("THUMB", i)
