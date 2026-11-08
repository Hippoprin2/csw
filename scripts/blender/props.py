# Procedural props for the shared actions (imported by anim_actions.py / anim_cheer.py).
import bpy, bmesh, math, random
from mathutils import Vector, Matrix


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def mat(name, rgb, rough=0.6, emit=0.0, alpha=1.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    col = (*[_lin(c) for c in rgb], 1)
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = col
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def obj_from_bm(bm, name, materials):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def attach(o, rig, bone, frame=1):
    """bone-parent keeping the current world transform (evaluated at `frame`)"""
    sc = bpy.context.scene
    sc.frame_set(frame); bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]
    m = rig.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.length, 0))
    mw = o.matrix_world.copy()
    o.parent = rig; o.parent_type = "BONE"; o.parent_bone = bone
    o.matrix_parent_inverse = m.inverted()
    o.matrix_world = mw


def hand_pos(rig, bone, frame):
    bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
    return rig.matrix_world @ rig.pose.bones[bone].tail


def key_scale(o, keys):
    for f, s in keys:
        s = max(s, 0.001)
        o.scale = (s, s, s); o.keyframe_insert("scale", frame=f)


def cylinder(r, h, seg=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    for f in bm.faces: f.smooth = True
    return bm


# ---------------------------------------------------------------- broom (sweep)
def broom():
    handle = obj_from_bm(cylinder(0.012, 0.62), "BroomHandle", [mat("Broom_Wood", (0.62, 0.42, 0.25), 0.7)])
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.085, radius2=0.03, depth=0.16)
    for v in bm.verts:
        v.co.y *= 0.45                                   # flat fan shape
    for f in bm.faces: f.smooth = True
    head = obj_from_bm(bm, "BroomHead", [mat("Broom_Straw", (0.93, 0.78, 0.38), 0.85)])
    head.location = (0, 0, -0.31 - 0.07)
    band = obj_from_bm(cylinder(0.035, 0.025), "BroomBand", [mat("Broom_Band", (0.85, 0.35, 0.33), 0.5)])
    band.location = (0, 0, -0.30)
    bpy.context.view_layer.update()
    for o in (head, band):
        bpy.context.view_layer.objects.active = o
    b = join([handle, head, band], "Broom")
    return b


# ---------------------------------------------------------------- sweat drops (hop)
def sweat_drop(name):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1.0)
    for v in bm.verts:
        z = v.co.z
        k = 1 - 0.75 * max(0.0, z) ** 1.3           # pointed top
        v.co.x *= k; v.co.y *= k * 0.6; v.co.z *= 1.35
    for f in bm.faces: f.smooth = True
    o = obj_from_bm(bm, name, [mat("Sweat", (0.55, 0.82, 0.98), 0.15, emit=0.4)])
    o.scale = (0.022, 0.022, 0.022)
    return o


# ---------------------------------------------------------------- book (nod)
def book():
    parts = []
    cover = mat("Book_Cover", (0.36, 0.62, 0.55), 0.6)
    paper = mat("Book_Paper", (0.98, 0.96, 0.9), 0.8)
    for side in (-1, 1):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        c = obj_from_bm(bm, f"BookCover{side}", [cover])
        c.scale = (0.095, 0.006, 0.13); c.location = (side * 0.047, 0, 0)
        c.rotation_euler = (0, 0, math.radians(-14 * side))
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        p = obj_from_bm(bm, f"BookPages{side}", [paper])
        p.scale = (0.088, 0.01, 0.122); p.location = (side * 0.046, -0.008, 0)
        p.rotation_euler = (0, 0, math.radians(-14 * side))
        parts += [c, p]
    bpy.context.view_layer.update()
    for o in parts:
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        o.select_set(False)
    return join(parts, "Book")


# ---------------------------------------------------------------- sparkle (stretch_spin)
def sparkle(name, col=(1.0, 0.86, 0.35)):
    bm = bmesh.new()
    pts = []
    for i in range(8):
        a = math.pi / 4 * i
        r = 1.0 if i % 2 == 0 else 0.28
        pts.append(bm.verts.new((r * math.cos(a), 0, r * math.sin(a))))
    c = bm.verts.new((0, 0, 0))
    for i in range(8):
        bm.faces.new((c, pts[i], pts[(i + 1) % 8]))
    o = obj_from_bm(bm, name, [mat("Sparkle_" + name[-1], col, 0.3, emit=2.5)])
    return o


# ---------------------------------------------------------------- letter (wave)
def letter():
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    env = obj_from_bm(bm, "Envelope", [mat("Envelope", (0.99, 0.97, 0.93), 0.7)])
    env.scale = (0.12, 0.008, 0.08)
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((-0.06, -0.0045, 0.04), (0.06, -0.0045, 0.04), (0, -0.0045, -0.008))]
    bm.faces.new(v)
    flap = obj_from_bm(bm, "EnvFlap", [mat("EnvFlap", (0.97, 0.75, 0.75), 0.7)])
    bm = bmesh.new()
    pts = []
    for i in range(32):
        t = 2 * math.pi * i / 32
        x = 16 * math.sin(t) ** 3; z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(bm.verts.new((x * 0.0009, -0.0055, z * 0.0009 - 0.004)))
    bm.faces.new(pts)
    heart = obj_from_bm(bm, "EnvHeart", [mat("EnvHeart", (0.93, 0.36, 0.42), 0.5)])
    bpy.ops.object.select_all(action="DESELECT")
    env.select_set(True); bpy.context.view_layer.objects.active = env
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return join([env, flap, heart], "Letter")


# ---------------------------------------------------------------- confetti (cheer)
CONFETTI_COLS = [(0.98, 0.45, 0.45), (0.99, 0.8, 0.3), (0.5, 0.8, 0.55), (0.45, 0.7, 0.98), (0.85, 0.55, 0.95), (1.0, 0.65, 0.75)]


def confetti_burst(origin, f0, n=36, seed=3, life=26):
    random.seed(seed)
    out = []
    for i in range(n):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        col = CONFETTI_COLS[i % len(CONFETTI_COLS)]
        o = obj_from_bm(bm, f"Confetti{i:02d}", [mat(f"Confetti{i % len(CONFETTI_COLS)}", col, 0.5, emit=0.3)])
        o.scale = (0.022, 0.004, 0.014) if i % 3 else (0.01, 0.01, 0.01)
        ang = random.uniform(0, 2 * math.pi)
        sp = random.uniform(0.35, 0.75)
        vx, vy, vz = sp * math.cos(ang), sp * math.sin(ang) * 0.4, random.uniform(0.15, 0.55)
        rot = [random.uniform(-6, 6) for _ in range(3)]
        base_scale = o.scale.copy()
        for k in range(0, life + 1, 2):
            t = k / 24
            o.location = (origin.x + vx * t, origin.y + vy * t, origin.z + vz * t - 1.1 * t * t)
            o.rotation_euler = [r * t * 3 for r in rot]
            fade = 1.0 if k < life - 6 else max(0.0, (life - k) / 6)
            o.scale = base_scale * max(fade, 0.001)
            o.keyframe_insert("location", frame=f0 + k); o.keyframe_insert("rotation_euler", frame=f0 + k)
            o.keyframe_insert("scale", frame=f0 + k)
        o.scale = base_scale * 0.001
        o.keyframe_insert("scale", frame=f0 - 1); o.keyframe_insert("scale", frame=1)
        out.append(o)
    return out


# ---------------------------------------------------------------- headband (hop)
def headband(body_obj, z0=0.372, tilt=-0.08, height=0.042, thick=0.012, gap=0.004, n=128,
             col=(0.93, 0.36, 0.38), stripe=(0.99, 0.97, 0.93)):
    """terry headband hugging the head: ring of ray-casts toward the head axis on the plane
    z = z0 + tilt * y (front = -y is a bit higher). Origin at the ring centre (scale-in pops onto the head)."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = body_obj.evaluated_get(deps)
    mwi = body_obj.matrix_world.inverted()
    ring = []
    for i in range(n):
        a = 2 * math.pi * i / n
        d = Vector((math.cos(a), math.sin(a), 0))
        z = z0 + tilt * (0.25 * math.sin(a))
        o = Vector((0, 0, z)) + d * 0.6
        hit, loc, nor, fi = ev.ray_cast(mwi @ o, (mwi.to_3x3() @ (-d)).normalized())
        p = (body_obj.matrix_world @ loc) if hit else Vector((0, 0, z)) + d * 0.2
        ring.append((p, d))
    # smooth the radius (ears / bumps) so the band reads as one clean loop
    radii = [((p - Vector((0, 0, p.z))).length) for p, d in ring]
    sm = [sum(radii[(i + k) % n] for k in range(-4, 5)) / 9 for i in range(n)]
    sm = [max(r, rr) for r, rr in zip(sm, radii)]
    zs = [p.z for p, d in ring]
    cz = sum(zs) / n
    bm = bmesh.new()
    lay = []
    for (p, d), r in zip(ring, sm):
        c = Vector((0, 0, p.z)) + d * (r + gap)
        lay.append([bm.verts.new(c + Vector((0, 0, -height / 2)) - Vector((0, 0, cz))),
                    bm.verts.new(c + Vector((0, 0, height / 2)) - Vector((0, 0, cz)))])
    for i in range(n):
        a, b = lay[i], lay[(i + 1) % n]
        f = bm.faces.new((a[0], b[0], b[1], a[1])); f.smooth = True
    o = obj_from_bm(bm, "Headband", [mat("Headband", col, 0.9)])
    o.location = (0, 0, cz)
    sol = o.modifiers.new("thick", "SOLIDIFY"); sol.thickness = thick; sol.offset = 1
    bev = o.modifiers.new("round", "BEVEL"); bev.width = 0.004; bev.segments = 3
    # white centre stripe
    bm = bmesh.new(); lay = []
    for (p, d), r in zip(ring, sm):
        c = Vector((0, 0, p.z)) + d * (r + gap + thick + 0.0008)
        lay.append([bm.verts.new(c + Vector((0, 0, -height * 0.12)) - Vector((0, 0, cz))),
                    bm.verts.new(c + Vector((0, 0, height * 0.12)) - Vector((0, 0, cz)))])
    for i in range(n):
        a, b = lay[i], lay[(i + 1) % n]
        f = bm.faces.new((a[0], b[0], b[1], a[1])); f.smooth = True
    s = obj_from_bm(bm, "HeadbandStripe", [mat("HeadbandStripe", stripe, 0.8)])
    s.parent = o; s.location = (0, 0, 0)
    return o


# ---------------------------------------------------------------- notebook + pencil (write)
def notebook():
    parts = []
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    cover = obj_from_bm(bm, "NB_Cover", [mat("NB_Cover", (0.42, 0.6, 0.86), 0.6)])
    cover.scale = (0.17, 0.12, 0.008)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    paper = obj_from_bm(bm, "NB_Paper", [mat("NB_Paper", (0.99, 0.98, 0.94), 0.85)])
    paper.scale = (0.155, 0.108, 0.006); paper.location = (0.004, 0, 0.006)
    parts += [cover, paper]
    for k in range(5):                                   # ruled lines + a scribbled line
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        ln = obj_from_bm(bm, f"NB_Line{k}", [mat("NB_Line", (0.62, 0.74, 0.9), 0.8)])
        ln.scale = (0.13, 0.0022, 0.001); ln.location = (0.008, -0.04 + 0.02 * k, 0.0095)
        parts.append(ln)
    for k in range(6):                                   # spiral rings on the left edge
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.006)
        rg = obj_from_bm(bm, f"NB_Ring{k}", [mat("NB_Ring", (0.75, 0.75, 0.78), 0.3)])
        rg.location = (-0.082, -0.045 + 0.018 * k, 0.008); parts.append(rg)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        o.select_set(False)
    return join(parts, "Notebook")


def pencil():
    body = obj_from_bm(cylinder(0.007, 0.13, seg=6), "PencilBody", [mat("Pencil_Yellow", (0.99, 0.8, 0.25), 0.5)])
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.007, radius2=0.0, depth=0.024)
    tip = obj_from_bm(bm, "PencilTip", [mat("Pencil_Wood", (0.93, 0.8, 0.62), 0.7)])
    tip.location = (0, 0, -0.077); tip.rotation_euler = (math.pi, 0, 0)
    era = obj_from_bm(cylinder(0.0072, 0.016), "PencilEraser", [mat("Pencil_Eraser", (0.96, 0.6, 0.65), 0.6)])
    era.location = (0, 0, 0.073)
    bpy.ops.object.select_all(action="DESELECT")
    for o in (tip, era):
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        o.select_set(False)
    return join([body, tip, era], "Pencil")
