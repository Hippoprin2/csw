# Usage: Blender -b -P anim_actions.py -- rig_dir action [render=1]
# Shared celebration actions for the hippo rig (bone names: root, body, head, ear.L/R,
# arm.L/R, leg.L/R, tail). Every action starts/ends at the idle rest pose.
# Rotations are given in WORLD axes (deg) and converted per bone, so they do not depend on
# bone roll. World axes: X = character's left->right (screen), Y = back (camera at -Y), Z = up.
#   arm.L: +y raises, +z swings forward.   arm.R: -y raises, -z swings forward.
import bpy, sys, os, math
from mathutils import Vector, Euler, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import props

argv = sys.argv[sys.argv.index("--") + 1:]
rdir, ACTION = argv[0], argv[1]
render = (argv[2] if len(argv) > 2 else "1") == "1"
bpy.ops.wm.open_mainfile(filepath=os.path.join(rdir, "hippo_rig_idle.blend"))
sc = bpy.context.scene
rig = bpy.data.objects["HippoRig"]
P = rig.pose.bones
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions.new(ACTION)
for pb in P:
    pb.rotation_mode = "QUATERNION"
    pb.location = (0, 0, 0); pb.scale = (1, 1, 1); pb.rotation_quaternion = (1, 0, 0, 0)

def wq(bone, x=0, y=0, z=0, order="XYZ"):
    Bm = P[bone].bone.matrix_local.to_3x3()
    Rw = Euler((math.radians(x), math.radians(y), math.radians(z)), order).to_matrix()
    return (Bm.inverted() @ Rw @ Bm).to_quaternion()

def R(f, bone, x=0, y=0, z=0, order="XYZ"):
    P[bone].rotation_quaternion = wq(bone, x, y, z, order); P[bone].keyframe_insert("rotation_quaternion", frame=f)

def L(f, bone, up=0.0):  # root/body local Y == world up
    P[bone].location = (0, up, 0); P[bone].keyframe_insert("location", frame=f)

def S(f, bone, s):
    P[bone].scale = s; P[bone].keyframe_insert("scale", frame=f)

def arms(f, ly=0, lz=0, ry=None, rz=None, lx=0, rx=None, order="XYZ"):
    """symmetric by default: right arm mirrors left. order='YXZ' = lower/raise first, then swing on X"""
    ry = -ly if ry is None else ry; rz = -lz if rz is None else rz; rx = lx if rx is None else rx
    R(f, "arm.L", lx, ly, lz, order); R(f, "arm.R", rx, ry, rz, order)

def eyes(keys):  # [(frame, 0 open | 1 closed)]
    dec = bpy.data.objects["EyeDecal"]; nt = dec.data.materials[0].node_tree
    if nt.animation_data: nt.animation_data.action = None
    for name in ("BlinkColor", "BlinkAlpha"):
        sock = nt.nodes[name].inputs[0]
        for f, v in keys:
            sock.default_value = v; sock.keyframe_insert("default_value", frame=f)
    for fc in fcurves(nt.animation_data.action):
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"

def fcurves(a):
    out = list(getattr(a, "fcurves", []) or [])
    try:
        for layer in a.layers:
            for strip in layer.strips:
                for cb in strip.channelbags: out += list(cb.fcurves)
    except Exception:
        pass
    return out

def rest(f, bones=("root", "body", "head", "ear.L", "ear.R", "arm.L", "arm.R", "leg.L", "leg.R", "tail")):
    bones = [b for b in bones if P[b].rotation_mode == "QUATERNION"]
    for b in bones:
        R(f, b)
    L(f, "root"); S(f, "body", (1, 1, 1))
    for b in ("arm.L", "arm.R"): S(f, b, (1, 1, 1))

def wag(f0, f1, amp=18, step=3):
    for i, f in enumerate(range(f0, f1, step)):
        R(f, "tail", z=amp if i % 2 else -amp)

def ears_bounce(frames_amps):
    for f, a in frames_amps:
        R(f, "ear.L", y=-a); R(f, "ear.R", y=a)

# ------------------------------------------------------------------ actions
def sweep():  # 정리·청소: both arms to one side, scrub left-right (broom later)
    F = 48; rest(1)
    sides = [(8, 1), (14, -1), (20, 1), (26, -1), (32, 1), (38, -1)]
    for f, s in sides:
        # both arms swing across the front toward side s (one raised, one lowered), stretched
        R(f, "arm.L", 0, 25 * s + 10, 50 + 30 * s); R(f, "arm.R", 0, 25 * s - 10, -50 + 30 * s)
        R(f, "body", 0, 10 * s, 14 * s)    # lean + twist toward the side
        R(f, "head", 0, -6 * s, 10 * s)
        S(f, "body", (1.03, 0.97, 1.03)); L(f, "root", 0.0)
        L(f + 3, "root", 0.015)            # little bounce between strokes
    rest(44); rest(F)
    eyes([(1, 0), (F, 0)]); wag(4, 40, 14, 4)
    hp = props.hand_pos(rig, "arm.R", 8)
    b = props.broom()
    b.location = hp + Vector((0.0, -0.03, -0.1)); b.rotation_euler = (math.radians(-22), math.radians(-10), 0)
    props.attach(b, rig, "arm.R", 8)
    props.key_scale(b, [(1, 0), (4, 0), (7, 1), (42, 1), (45, 0), (F, 0)])
    return F

def hop():  # 몸 움직이기: two energetic hops with arm swings
    F = 40; rest(1)
    # arms swing FRONT/BACK: first let them hang closer to the body (Y), then swing on world X
    # (+x = back, -x = forward). Arms point sideways in rest, so X alone would only twist them.
    D = -30
    sw = lambda f, x: arms(f, ly=D, lx=x, order="YXZ")
    for base in (1, 19):
        S(base + 3, "body", (1.06, 0.9, 1.06)); L(base + 3, "root", -0.03); sw(base + 3, 60)      # wind up: back
        S(base + 6, "body", (0.95, 1.08, 0.95)); L(base + 6, "root", 0.0); sw(base + 6, -40)      # take-off: forward
        L(base + 9, "root", 0.10); S(base + 9, "body", (1, 1, 1)); sw(base + 9, -80)             # apex: forward-up
        R(base + 9, "leg.L", x=-12); R(base + 9, "leg.R", x=-12)
        L(base + 13, "root", 0.0); S(base + 13, "body", (1.07, 0.9, 1.07)); sw(base + 13, 40)   # landing: back
        R(base + 13, "leg.L"); R(base + 13, "leg.R")
        S(base + 16, "body", (1, 1, 1)); sw(base + 16, 0)
    ears_bounce([(1, 0), (8, -12), (12, 14), (16, 0), (26, -12), (30, 14), (34, 0)])
    rest(F); eyes([(1, 0), (8, 1), (34, 1), (35, 0), (F, 0)]); wag(4, 36, 20, 3)
    # headband on the forehead (pops on/off with the action), follows the head
    sc.frame_set(1); bpy.context.view_layer.update()
    hb = props.headband(bpy.data.objects["Hippo"])
    props.attach(hb, rig, "head", 1)
    props.key_scale(hb, [(1, 0), (2, 0), (5, 1.06), (7, 1), (36, 1), (39, 0), (F, 0)])
    # sweat: one at the (screen-)left eyebrow height, one at the right cheek height,
    # just outside the head silhouette, flicking outward on each hop apex
    for i, (x, z, f0) in enumerate(((-0.215, 0.36, 10), (0.245, 0.16, 11), (-0.215, 0.36, 28), (0.245, 0.16, 29))):
        d = props.sweat_drop(f"Sweat{i}")
        side = 1 if x > 0 else -1
        start = Vector((x, -0.06, z))
        d.rotation_euler = (0, math.radians(30 * side), 0)
        props.attach(d, rig, "head", 1)
        for f, off, sz in ((1, 0, 0), (f0 - 1, 0, 0), (f0, 0, 0.02), (f0 + 3, 0.035, 0.026), (f0 + 7, 0.07, 0.0), (F, 0.07, 0)):
            sc.frame_set(f); bpy.context.view_layer.update()
            d.matrix_world = Matrix.Translation(start + Vector((side * off, 0, (0.5 if side < 0 else 0.15) * off))) @ Euler(d.rotation_euler).to_matrix().to_4x4()
            d.scale = (max(sz, 1e-4),) * 3
            d.keyframe_insert("location", frame=f); d.keyframe_insert("scale", frame=f)
    return F

def nod():  # 공부·일: content nods, small body bob, a slow blink at the end
    F = 44; rest(1)
    for f, a in ((6, 20), (11, -4), (16, 20), (21, -4), (26, 16), (31, 0)):
        R(f, "head", x=a); S(f, "body", (1.0, 0.985 if a > 5 else 1.0, 1.0))
    arms(5, ly=50, lz=78); arms(36, ly=50, lz=78)
    for f in (5, 36):
        S(f, "arm.L", (1.08, 1.35, 1.08)); S(f, "arm.R", (1.08, 1.35, 1.08))
    ears_bounce([(1, 0), (8, 6), (13, -4), (18, 6), (23, -4), (28, 5), (33, 0)])
    rest(40); rest(F); eyes([(1, 0), (33, 0), (34, 1), (39, 1), (40, 0), (F, 0)]); wag(4, 36, 10, 6)
    tl = props.hand_pos(rig, "arm.L", 12); tr = props.hand_pos(rig, "arm.R", 12)
    bk = props.book()
    bk.location = Vector((0, (tl.y + tr.y) / 2 - 0.05, (tl.z + tr.z) / 2 + 0.04))
    bk.rotation_euler = (math.radians(-22), 0, math.radians(15))   # pages toward the viewer, slight 3/4 turn
    props.attach(bk, rig, "body", 12)
    props.key_scale(bk, [(1, 0), (3, 0), (6, 1.6), (8, 1.5), (36, 1.5), (39, 0), (F, 0)])
    return F

def make_sweet_potato(name="SweetPotato", half_len=0.16, rad=0.058):
    """split-open roasted sweet potato lying along X, origin at its centre.
    upper side = golden flesh, lower side = reddish-purple skin (jagged split edge)."""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=1.0)
    for v in bm.verts:
        xn = v.co.z                                    # use sphere's pole axis as the length axis
        ry, rz = v.co.x, v.co.y
        taper = 1 - 0.55 * abs(xn) ** 2.2              # pointed ends
        bumps = 1 + 0.05 * math.sin(4 * math.atan2(rz, ry) + 5 * xn)
        flat = 0.85 if rz > 0 else 1.0                  # slightly flattened open top
        v.co = Vector((xn * half_len, ry * rad * taper * bumps, rz * rad * taper * bumps * flat))
    for f in bm.faces:
        f.smooth = True
        c = f.calc_center_median()
        edge = 0.2 * rad + 0.12 * rad * math.sin(c.x / half_len * 9)
        f.material_index = 1 if c.z > edge else 0
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    def mat(n, rgb, rough):
        m = bpy.data.materials.new(n); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        b.inputs["Base Color"].default_value = (*lin, 1); b.inputs["Roughness"].default_value = rough
        return m
    me.materials.append(mat("SP_Skin", (0.52, 0.22, 0.27), 0.7))     # reddish-purple roasted skin
    me.materials.append(mat("SP_Flesh", (0.98, 0.78, 0.25), 0.55))   # golden yellow flesh
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    return o

def write():  # 공부·일: notebook held in front (left hand under it), pencil scribbling in the right, head down
    F = 56; rest(1)
    for f in (5, 50):
        R(f, "arm.L", 0, 52, 82); S(f, "arm.L", (1.08, 1.4, 1.08))
        R(f, "arm.R", 0, -40, -84); S(f, "arm.R", (1.06, 1.3, 1.06))
    for i, f in enumerate(range(8, 47, 2)):              # scribble: quick little hand wiggles
        if 26 <= f <= 30:                                # pause: tap pencil, look up a bit
            R(f, "arm.R", 0, -48, -80); continue
        R(f, "arm.R", 0, -40 + (4 if i % 2 else -3), -84 + (6 if (i // 2) % 2 else -4))
    for f, a in ((1, 0), (6, 18), (12, 22), (18, 17), (24, 22), (28, 8), (32, 18), (38, 23), (44, 18), (49, 4)):
        R(f, "head", x=a)
    S(28, "body", (1, 1.01, 1)); S(34, "body", (1, 1, 1))
    ears_bounce([(1, 0), (10, 4), (20, -3), (28, 6), (36, -3), (46, 0)])
    rest(53); rest(F)
    for b in ("arm.L", "arm.R"):
        S(53, b, (1, 1, 1))
    eyes([(1, 0), (27, 0), (28, 1), (30, 1), (31, 0), (F, 0)]); wag(4, 50, 10, 6)
    hl = props.hand_pos(rig, "arm.L", 16); hr = props.hand_pos(rig, "arm.R", 16)
    print("write hands", tuple(round(v, 3) for v in hl), tuple(round(v, 3) for v in hr))
    nb = props.notebook()
    NB = 1.55                                            # notebook scale: spans both hands
    nb.location = Vector(((hl.x + hr.x) / 2 - 0.01, min(hl.y, hr.y) - 0.03, (hl.z + hr.z) / 2 - 0.005))
    nb.rotation_euler = (math.radians(55), 0, math.radians(8))    # page tilted up toward the face + viewer
    nb.scale = (NB,) * 3
    props.attach(nb, rig, "body", 16)
    # pencil: tip on the right half of the page, eraser end in the right hand
    bpy.context.view_layer.update()
    page_n = (nb.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    tip = nb.matrix_world @ Vector((0.045, 0.0, 0.012))
    axis = (hr + Vector((0, -0.02, 0.0)) - tip).normalized()
    pc = props.pencil()
    pc.rotation_mode = "QUATERNION"
    pc.rotation_quaternion = axis.to_track_quat("Z", "Y")
    pc.location = tip + axis * 0.089
    props.attach(pc, rig, "arm.R", 16)
    props.key_scale(nb, [(1, 0), (3, 0), (6, NB * 1.05), (8, NB), (48, NB), (51, 0), (F, 0)])
    props.key_scale(pc, [(1, 0), (3, 0), (6, 1.05), (8, 1), (48, 1), (51, 0), (F, 0)])
    return F

def eat():  # 잘 먹기: both hands hold a sweet potato up to the mouth, bites + chew, happy eyes
    F = 52; rest(1)
    arms(7, ly=55, lz=80); arms(44, ly=55, lz=80)
    for f in (7, 44):
        S(f, "arm.L", (1.1, 1.5, 1.1)); S(f, "arm.R", (1.1, 1.5, 1.1))
    R(7, "head", x=6)
    for i, f in enumerate(range(10, 42, 4)):
        R(f, "head", x=16 if i % 2 else 4)
        S(f, "body", (1.02, 0.98, 1.02) if i % 2 else (1, 1, 1))
        L(f, "root", 0.012 if i % 2 else 0.0)
    ears_bounce([(1, 0), (12, 6), (20, -4), (28, 6), (36, -4), (44, 0)])
    rest(F); eyes([(1, 0), (9, 1), (42, 1), (43, 0), (F, 0)]); wag(6, 46, 16, 4)
    # --- sweet potato prop held between the hands, top near the snout ---
    sc.frame_set(20); bpy.context.view_layer.update()
    tl = rig.matrix_world @ P["arm.L"].tail; tr = rig.matrix_world @ P["arm.R"].tail
    hands = (tl + tr) / 2
    print("hands at", tuple(round(v, 3) for v in hands))
    sp = make_sweet_potato()
    sp.location = Vector((0, hands.y - 0.07, hands.z - 0.005))      # across both hands, in front of the chest
    sp.rotation_euler = (math.radians(18), 0, 0)                      # +X tilts the flesh side toward the camera
    # follow the body bone (keeps world placement)
    body_m = rig.matrix_world @ P["body"].matrix
    sp.parent = rig; sp.parent_type = "BONE"; sp.parent_bone = "body"
    sp.matrix_parent_inverse = (body_m @ Matrix.Translation((0, P["body"].length, 0))).inverted()
    sc.frame_set(1)
    # pop in with the arms, three bites (shrinks from the top), pop out before rest
    for f, s in ((1, 0.0), (5, 0.0), (8, 1.08), (10, 1.0), (16, 1.0), (17, 0.88), (26, 0.88), (27, 0.76),
                 (36, 0.76), (37, 0.64), (43, 0.64), (47, 0.0), (F, 0.0)):
        if s == 0:
            sp.scale = (0.001, 0.001, 0.001)
        elif s < 1:                       # bites: it gets shorter
            sp.scale = (s, 1, 1)
        else:
            sp.scale = (s, s, s)
        sp.keyframe_insert("scale", frame=f)
    return F

def stretch_spin():  # 나 돌보기: big stretch up (arms up, body tall), then a happy spin
    F = 60; rest(1, ("body", "head", "ear.L", "ear.R", "arm.L", "arm.R", "leg.L", "leg.R", "tail"))
    arms(10, ly=80); S(10, "arm.L", (1.12, 1.4, 1.12)); S(10, "arm.R", (1.12, 1.4, 1.12))
    S(10, "body", (0.95, 1.08, 0.95)); R(10, "head", x=-10)
    arms(18, ly=84); S(18, "body", (0.94, 1.1, 0.94)); R(18, "head", x=-12)
    S(18, "arm.L", (1.12, 1.45, 1.12)); S(18, "arm.R", (1.12, 1.45, 1.12))
    arms(24, ly=40); S(24, "arm.L", (1, 1, 1)); S(24, "arm.R", (1, 1, 1))
    S(24, "body", (1.04, 0.95, 1.04)); R(24, "head")
    # spin 360 around world up on the root, with a small hop
    # quaternions take the short way (240 deg == -120) -> use euler on the root's local Y (= world up)
    rp = P["root"]; rp.rotation_mode = "XYZ"
    for f, deg, up in ((1, 0, 0.0), (26, 0, 0.0), (32, 120, 0.05), (38, 240, 0.05), (44, 360, 0.0), (F, 360, 0.0)):
        rp.rotation_euler = (0, math.radians(deg), 0); rp.keyframe_insert("rotation_euler", frame=f); L(f, "root", up)
    arms(34, ly=30, lz=-10); S(46, "body", (1.05, 0.93, 1.05))
    ears_bounce([(1, 0), (26, 0), (32, -14), (38, -14), (46, 10), (50, 0)])
    others = ("body", "head", "ear.L", "ear.R", "arm.L", "arm.R", "leg.L", "leg.R", "tail")
    rest(52, others); rest(F, others); eyes([(1, 0), (8, 1), (24, 1), (25, 0), (F, 0)]); wag(26, 50, 20, 3)
    face = math.radians(19)                                  # face the 3/4 camera
    spots = [(-0.36, 0.35, 9, 0.12), (0.38, 0.45, 12, 0.1), (-0.3, -0.05, 16, 0.09), (0.36, 0.05, 19, 0.11),
             (-0.4, 0.55, 26, 0.09), (0.3, 0.62, 29, 0.1), (-0.32, 0.15, 33, 0.11), (0.4, 0.28, 36, 0.09),
             (-0.2, 0.62, 40, 0.08), (0.24, -0.1, 43, 0.1), (-0.42, 0.3, 47, 0.09), (0.36, 0.5, 50, 0.08)]
    for i, (x, z, f0, s) in enumerate(spots):
        sp = props.sparkle(f"Sparkle{i % 3}{i}", col=[(1.0, 0.86, 0.35), (1.0, 0.75, 0.82), (0.75, 0.9, 1.0)][i % 3])
        sp.location = (x, -0.25, z); sp.rotation_euler = (0, 0, face)
        props.key_scale(sp, [(1, 0), (f0 - 1, 0), (f0 + 2, s), (f0 + 4, s * 0.6), (f0 + 6, s * 1.1), (f0 + 10, 0), (F, 0)])
        for f, a in ((f0, 0), (f0 + 10, 90)):
            sp.rotation_euler = (0, math.radians(a), face); sp.keyframe_insert("rotation_euler", frame=f)
    return F

def wave():  # 사람·마음: raise the right arm and wave, head tilt
    F = 52; rest(1)
    R(8, "arm.R", 0, -95, -10); S(8, "arm.R", (1.1, 1.35, 1.1)); R(8, "head", 0, 8, 0)
    for i, f in enumerate(range(12, 40, 5)):
        R(f, "arm.R", 0, -95 + (18 if i % 2 else -10), -10)
    R(40, "arm.R", 0, -95, -10); S(42, "arm.R", (1.1, 1.35, 1.1))
    R(8, "arm.L", 0, 0, 10); R(40, "arm.L", 0, 0, 10)
    R(24, "head", 0, 10, 4); R(40, "head", 0, 8, 0)
    ears_bounce([(1, 0), (12, 5), (22, -5), (32, 5), (42, 0)])
    rest(48); rest(F); eyes([(1, 0), (20, 0), (21, 1), (24, 1), (25, 0), (F, 0)]); wag(6, 44, 18, 4)
    hp = props.hand_pos(rig, "arm.R", 10)
    lt = props.letter()
    lt.location = hp + Vector((0.0, -0.04, 0.03)); lt.rotation_euler = (0, math.radians(-15), math.radians(19))
    props.attach(lt, rig, "arm.R", 10)
    props.key_scale(lt, [(1, 0), (6, 0), (9, 1.8), (11, 1.65), (42, 1.65), (46, 0), (F, 0)])
    return F

ACTIONS = {"sweep": sweep, "hop": hop, "nod": nod, "write": write, "eat": eat, "stretch_spin": stretch_spin, "wave": wave}
F = ACTIONS[ACTION]()
sc.frame_start, sc.frame_end = 1, F
for fc in fcurves(rig.animation_data.action):
    for kp in fc.keyframe_points:
        kp.interpolation = "BEZIER"; kp.easing = "AUTO"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(rdir, f"hippo_{ACTION}.blend"))
print("SAVED", ACTION, F)
if not render:
    sys.exit(0)

# ------------------------------------------------------------------ render (same as idle/cheer)
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except Exception: pass
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.render.resolution_x, sc.render.resolution_y = 600, 800
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for n, rot, e in (("key", (50, 0, 30), 3.0), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2.0), ("bounce", (150, 0, 0), 0.7)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = e
    o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = 1.45
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
target = Vector((0, 0, 0.07))
cam.location = target + Vector((0.35, -1, 0.12)).normalized() * 10
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = os.path.join(rdir, f"{ACTION}_frames", "f_")
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(animation=True)
print("RENDERED", ACTION)
