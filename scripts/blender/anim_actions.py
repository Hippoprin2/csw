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


def aim(f, bone, target, sx=1.08):
    """rotate+stretch a bone (from its rest pose) so its tail lands on world `target`"""
    pb = P[bone]
    B3 = pb.bone.matrix_local.to_3x3()
    head = rig.matrix_world @ pb.bone.head_local   # arms are children of body; body stays near rest here
    rest_dir = (B3 @ Vector((0, 1, 0))).normalized()
    v = target - head
    qw = rest_dir.rotation_difference(v.normalized())
    pb.rotation_quaternion = (B3.inverted() @ qw.to_matrix() @ B3).to_quaternion()
    pb.keyframe_insert("rotation_quaternion", frame=f)
    st = v.length / pb.bone.length
    pb.scale = (sx, st, sx); pb.keyframe_insert("scale", frame=f)

def seated(F, work):
    """common seated sequence: props pop in, sit (legs forward), work(f0, f1), stand, props pop out"""
    rest(1)
    for b in ("leg.L", "leg.R"):
        R(6, b, x=-75); R(54, b, x=-75); R(60, b)
    L(4, "root", 0.04); L(8, "root", 0.0); L(56, "root", 0.03); L(60, "root", 0.0)
    R(9, "body", x=6); R(53, "body", x=6); R(58, "body")
    work(11, 51)
    rest(F)
    dk = props.desk(); ch = props.chair()
    for o in (dk, ch):
        props.key_scale(o, [(1, 0), (2, 0), (6, 1.06), (8, 1), (54, 1), (59, 0), (F, 0)])
    return dk, ch

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


def desk_write():  # 공부·일 (앉아서): notebook flat on the desk, pencil scribbling
    F = 64
    page = Vector((0.04, props.DESK_Y + 0.02, props.DESK_TOP_Z + 0.012))
    def work(f0, f1):
        for f in (f0 - 2, f1 + 2):
            R(f, "head", x=4)
        for i, f in enumerate(range(f0, f1 + 1, 2)):
            pause = 30 <= f <= 34
            jit = Vector(((0.012 if i % 2 else -0.01), (0.006 if (i // 2) % 2 else -0.006), 0.0)) if not pause else Vector((0, 0.02, 0.04))
            aim(f, "arm.R", page + Vector((0.035, 0.03, 0.055)) + jit)
            aim(f, "arm.L", Vector((-0.1, props.DESK_Y + 0.03, props.DESK_TOP_Z + 0.03)))
            R(f, "head", x=(8 if pause else 20 + (2 if i % 3 == 0 else 0)))
        for b in ("arm.L", "arm.R"):
            R(f0 - 3, b); S(f0 - 3, b, (1, 1, 1)); R(f1 + 3, b); S(f1 + 3, b, (1, 1, 1))
    dk, ch = seated(F, work)
    eyes([(1, 0), (31, 0), (32, 1), (34, 1), (35, 0), (F, 0)]); wag(12, 50, 8, 6)
    ears_bounce([(1, 0), (14, 4), (24, -3), (32, 6), (42, -3), (52, 0)])
    nb = props.notebook_flat(Vector((0.0, props.DESK_Y + 0.02, props.DESK_TOP_Z + 0.002)), math.radians(8), 1.5)
    pc = props.pencil(); pc.rotation_mode = "QUATERNION"
    for o in (nb,):
        props.key_scale(o, [(1, 0), (4, 0), (8, 1.6), (10, 1.5), (52, 1.5), (57, 0), (F, 0)])
    # pencil: tip on the page near the hand, eraser end through the hand (keyed per frame)
    for f in range(1, F + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        hand = rig.matrix_world @ P["arm.R"].tail
        tip = Vector((hand.x - 0.03, hand.y - 0.015, props.DESK_TOP_Z + 0.014))
        axis = (hand - tip).normalized()
        pc.rotation_quaternion = axis.to_track_quat("Z", "Y")
        pc.location = tip + axis * 0.089
        on = 1.0 if 11 <= f <= 51 else 0.0
        pc.scale = (max(on, 1e-3),) * 3
        for path in ("location", "rotation_quaternion", "scale"):
            pc.keyframe_insert(path, frame=f)
    return F

def desk_laptop():  # 공부·일 (앉아서): typing on a laptop, glancing at the screen
    F = 64
    def work(f0, f1):
        base = props.DESK_TOP_Z + 0.03
        for i, f in enumerate(range(f0, f1 + 1, 2)):
            pause = 30 <= f <= 34
            upL = 0.018 if (i % 2 == 0 and not pause) else 0.0
            upR = 0.018 if (i % 2 == 1 and not pause) else 0.0
            aim(f, "arm.L", Vector((-0.07, props.DESK_Y + 0.05, base + upL)))
            aim(f, "arm.R", Vector((0.07, props.DESK_Y + 0.05, base + upR)))
            R(f, "head", x=(4 if pause else 10), z=(6 if pause else 0))
        for b in ("arm.L", "arm.R"):
            R(f0 - 3, b); S(f0 - 3, b, (1, 1, 1)); R(f1 + 3, b); S(f1 + 3, b, (1, 1, 1))
    dk, ch = seated(F, work)
    eyes([(1, 0), (31, 0), (32, 1), (34, 1), (35, 0), (F, 0)]); wag(12, 50, 8, 6)
    ears_bounce([(1, 0), (14, 3), (24, -3), (32, 6), (42, -3), (52, 0)])
    lp = props.laptop(Vector((0.0, props.DESK_Y + 0.0, props.DESK_TOP_Z)), 0.0)
    props.key_scale(lp, [(1, 0), (4, 0), (8, 1.06), (10, 1), (52, 1), (57, 0), (F, 0)])
    return F

SIT_DROP = -0.115     # root down so the bottom rests on the floor
def _sit_pose(f, breathe=0.0, tilt=6):
    L(f, "root", SIT_DROP)
    for b in ("leg.L", "leg.R"):
        R(f, b, x=-85)
    arms(f, ly=-18, lz=28)
    R(f, "head", x=5, y=tilt)
    S(f, "body", (1 - 0.4 * breathe, 1 + breathe, 1 - 0.4 * breathe))
    R(f, "body", x=3)

def sit_in():  # 곁에 앉기 (조용히): stand -> sit down on the floor. ends seated.
    F = 24; rest(1)
    S(6, "body", (1.03, 0.97, 1.03)); L(6, "root", 0.0)
    _sit_pose(16); L(13, "root", SIT_DROP - 0.012); S(16, "body", (1.04, 0.96, 1.04))
    _sit_pose(F)
    eyes([(1, 0), (F, 0)]); return F

def sit_loop():  # seated, slow breathing, one slow blink. loops.
    F = 72
    for f, b in ((1, 0.0), (19, 0.012), (37, 0.0), (55, 0.012), (F, 0.0)):
        _sit_pose(f, b, tilt=6 + (2 if b else 0))
    for f, a in ((1, 0), (30, 4), (F, 0)):
        R(f, "tail", z=a)
    eyes([(1, 0), (44, 0), (45, 1), (50, 1), (51, 0), (F, 0)]); return F

def sit_out():  # seated -> stand back up to the idle rest pose
    F = 20
    _sit_pose(1)
    L(8, "root", SIT_DROP + 0.02); S(8, "body", (0.97, 1.04, 0.97))
    rest(16); L(16, "root", 0.01); rest(F)
    eyes([(1, 0), (F, 0)]); return F

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

def eat_strawberry():  # 잘 먹기(딸기): same chew motion, a big strawberry held upright between the hands
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
    # --- strawberry held upright between the hands, shrinks with each bite ---
    sc.frame_set(20); bpy.context.view_layer.update()
    tl = rig.matrix_world @ P["arm.L"].tail; tr = rig.matrix_world @ P["arm.R"].tail
    hands = (tl + tr) / 2
    sb = props.strawberry(0.09)
    sb.location = Vector((0, hands.y - 0.07, hands.z + 0.03))     # resting on both hands
    sb.rotation_euler = (math.radians(28), 0, math.radians(15))     # tip toward the viewer so the leaves show
    body_m = rig.matrix_world @ P["body"].matrix
    sb.parent = rig; sb.parent_type = "BONE"; sb.parent_bone = "body"
    sb.matrix_parent_inverse = (body_m @ Matrix.Translation((0, P["body"].length, 0))).inverted()
    sc.frame_set(1)
    props.key_scale(sb, [(1, 0), (5, 0), (8, 1.1), (10, 1.0), (16, 1.0), (17, 0.86), (26, 0.86), (27, 0.72),
                         (36, 0.72), (37, 0.58), (43, 0.58), (47, 0), (F, 0)])
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

def make_glass(h=0.24, r0=0.088, r1=0.1):
    """big pastel tumbler (arms are short -> oversized glass), origin at the bottom centre.
    returns (glass, water); water origin also at the bottom so scale z lowers the level."""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=r0, radius2=r1, depth=h)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    edges = [e for e in bm.edges if all(abs(v.co.z) < 1e-4 or abs(v.co.z - h) < 1e-4 for v in e.verts)
             and len(e.link_faces) == 2 and any(len(f.verts) > 4 for f in e.link_faces)]
    bmesh.ops.bevel(bm, geom=edges, offset=0.012, segments=3, profile=0.5, affect="EDGES")
    for f in bm.faces: f.smooth = True
    m_glass = props.mat("Glass_Sky", (0.80, 0.92, 0.98), 0.25, alpha=0.38)
    try: m_glass.surface_render_method = "BLENDED"
    except Exception: m_glass.blend_method = "BLEND"
    glass = props.obj_from_bm(bm, "Glass", [m_glass])
    wh = h * 0.78
    bm = props.cylinder(r0 * 0.9, wh, 48)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, wh / 2 + 0.012))
    water = props.obj_from_bm(bm, "Water", [props.mat("Water_Sky", (0.55, 0.80, 0.98), 0.3, emit=0.15)])
    rim = bmesh.new()
    bmesh.ops.create_cone(rim, cap_ends=False, segments=48, radius1=r1 * 1.005, radius2=r1 * 1.005, depth=0.01)
    bmesh.ops.translate(rim, verts=rim.verts, vec=(0, 0, h - 0.008))
    for f in rim.faces: f.smooth = True
    rimo = props.obj_from_bm(rim, "GlassRim", [props.mat("Glass_Rim", (0.99, 0.97, 0.93), 0.4)])
    water.parent = glass; rimo.parent = glass
    return glass, water

def drink():  # 잘 먹기(물): big glass in both hands, tip head back, three gulps, "캬~" with closed eyes
    F = 64; rest(1)
    # hold the glass in front of the chest, then lift it to the mouth and lean back
    arms(7, ly=55, lz=80); S(7, "arm.L", (1.1, 1.5, 1.1)); S(7, "arm.R", (1.1, 1.5, 1.1))
    arms(14, ly=62, lz=84); arms(38, ly=62, lz=84)
    for f in (14, 38):
        S(f, "arm.L", (1.1, 1.62, 1.1)); S(f, "arm.R", (1.1, 1.62, 1.1))
    arms(44, ly=50, lz=70); S(44, "arm.L", (1.1, 1.45, 1.1)); S(44, "arm.R", (1.1, 1.45, 1.1))
    R(7, "head", x=4); R(14, "head", x=-14); R(38, "head", x=-14); R(43, "head", x=-4)
    R(14, "body", x=-6); R(38, "body", x=-6); R(43, "body")
    for i, f in enumerate(range(17, 38, 7)):          # three gulps: head dips + body squash
        R(f + 3, "head", x=-8); R(f + 6, "head", x=-14)
        S(f + 3, "body", (1.02, 0.97, 1.02)); S(f + 6, "body", (1, 1, 1))
    # "캬~": stretch tall, little hop, ears flick, glass down
    S(46, "body", (0.96, 1.07, 0.96)); L(46, "root", 0.035); R(46, "head", x=-8)
    S(51, "body", (1.04, 0.95, 1.04)); L(51, "root", 0.0); R(51, "head", x=2)
    ears_bounce([(1, 0), (14, -4), (38, -4), (46, 12), (50, -6), (54, 0)])
    rest(56); rest(F); eyes([(1, 0), (13, 1), (39, 1), (40, 0), (43, 0), (44, 1), (54, 1), (55, 0), (F, 0)])
    wag(42, 58, 20, 3)
    # --- glass between the hands, follows the body bone ---
    sc.frame_set(20); bpy.context.view_layer.update()
    tl = rig.matrix_world @ P["arm.L"].tail; tr = rig.matrix_world @ P["arm.R"].tail
    hands = (tl + tr) / 2
    print("hands at", tuple(round(v, 3) for v in hands))
    gl, wa = make_glass()
    gl.location = Vector((0, hands.y - 0.08, hands.z - 0.075))
    body_m = rig.matrix_world @ P["body"].matrix
    gl.parent = rig; gl.parent_type = "BONE"; gl.parent_bone = "body"
    gl.matrix_parent_inverse = (body_m @ Matrix.Translation((0, P["body"].length, 0))).inverted()
    sc.frame_set(1)
    props.key_scale(gl, [(1, 0), (4, 0), (8, 1.08), (10, 1.0), (44, 1.0), (49, 0), (F, 0)])
    for f, a in ((1, 0), (10, 0), (15, -28), (38, -28), (43, 0), (F, 0)):   # tip the top toward the mouth
        gl.rotation_euler = (math.radians(a), 0, 0); gl.keyframe_insert("rotation_euler", frame=f)
    for f, s in ((1, 1), (16, 1), (21, 0.72), (28, 0.45), (35, 0.18), (F, 0.18)):  # level drops per gulp
        wa.scale = (1, 1, max(s, 0.001)); wa.keyframe_insert("scale", frame=f)
    # one happy droplet + sparkles on "캬~"
    face = math.radians(19)
    dp = props.sweat_drop("DrinkDrop"); dp.location = (0.3, -0.3, 0.16); dp.rotation_euler = (0, math.radians(-25), face)
    props.key_scale(dp, [(1, 0), (44, 0), (47, 0.028), (53, 0.026), (57, 0), (F, 0)])
    for f, x, z in ((44, 0.3, 0.16), (57, 0.42, 0.24)):   # flies outward, outside the face silhouette
        dp.location = (x, -0.3, z); dp.keyframe_insert("location", frame=f)
    for i, (x, z, f0, s) in enumerate(((-0.34, 0.42, 45, 0.11), (0.36, 0.5, 47, 0.1), (-0.26, 0.6, 49, 0.08))):
        sp = props.sparkle(f"DrinkSparkle{i}", col=[(1.0, 0.86, 0.35), (0.75, 0.9, 1.0), (1.0, 0.75, 0.82)][i])
        sp.location = (x, -0.25, z); sp.rotation_euler = (0, 0, face)
        props.key_scale(sp, [(1, 0), (f0 - 1, 0), (f0 + 2, s), (f0 + 4, s * 0.6), (f0 + 6, s * 1.1), (f0 + 10, 0), (F, 0)])
    return F

def chef_hat(head_top):
    """small puffy toque sitting between the ears; origin at its band bottom (pops onto the head)"""
    import bmesh
    white = props.mat("Chef_White", (0.99, 0.97, 0.93), 0.85)
    parts = []
    bm = props.cylinder(0.085, 0.055, 48)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.0275))
    band = props.obj_from_bm(bm, "HatBand", [white])
    bev = band.modifiers.new("round", "BEVEL"); bev.width = 0.01; bev.segments = 3
    parts.append(band)
    for i, (x, y, z, r) in enumerate(((0, 0, 0.1, 0.075), (-0.055, 0.0, 0.085, 0.055), (0.055, 0.0, 0.085, 0.055),
                                       (0, -0.05, 0.085, 0.055), (0, 0.05, 0.085, 0.055))):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r)
        for f in bm.faces: f.smooth = True
        o = props.obj_from_bm(bm, f"HatPuff{i}", [white]); o.location = (x, y, z); parts.append(o)
    hat = props.join(parts, "ChefHat")
    bpy.context.view_layer.update()
    hat.location = head_top + Vector((0, 0.0, -0.035))
    hat.rotation_euler = (math.radians(-8), math.radians(6), 0)
    return hat

def frying_pan():
    """pan (origin = pan centre, cooking surface at z=0, handle toward +y = back to the hand) + fried egg child"""
    import bmesh
    dark = props.mat("Pan_Body", (0.93, 0.36, 0.38), 0.6)   # coral (ART_BIBLE accent), no black
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=0.1, radius2=0.125, depth=0.032)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, -0.012))
    for f in bm.faces: f.smooth = True
    pan = props.obj_from_bm(bm, "Pan", [dark])
    bev = pan.modifiers.new("round", "BEVEL"); bev.width = 0.008; bev.segments = 3
    bm = props.cylinder(0.014, 0.17, 24)
    handle = props.obj_from_bm(bm, "PanHandle", [props.mat("Pan_Handle", (0.86, 0.69, 0.50), 0.7)])
    handle.rotation_euler = (math.radians(90), 0, 0); handle.location = (0, 0.2, 0.0)
    handle.parent = pan
    # fried egg: wobbly white + yolk dome
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=16, radius=1.0)
    for v in bm.verts:
        a = math.atan2(v.co.y, v.co.x)
        r = 0.074 * (1 + 0.08 * math.sin(3 * a) + 0.05 * math.sin(5 * a + 1))
        v.co = Vector((v.co.x * r, v.co.y * r, v.co.z * 0.009))
    for f in bm.faces: f.smooth = True
    egg = props.obj_from_bm(bm, "EggWhite", [props.mat("Egg_White", (0.99, 0.97, 0.93), 0.5)])
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.03)
    for v in bm.verts: v.co.z *= 0.7
    for f in bm.faces: f.smooth = True
    yolk = props.obj_from_bm(bm, "EggYolk", [props.mat("Egg_Yolk", (0.98, 0.78, 0.25), 0.4)])
    yolk.location = (0.008, -0.006, 0.008); yolk.parent = egg
    egg.parent = pan; egg.location = (-0.005, 0, 0.012)
    return pan, egg

def cook():  # 잘 먹기(요리): chef hat pops on, pan by the handle in ONE hand (대표 11-12), other hand on the hip, flip the egg, proud
    F = 76; rest(1)
    ARM = (0, -50, -88)                                  # right arm forward, a bit raised (holds the handle)
    def rarm(f, dy=0, st=1.35):
        R(f, "arm.R", ARM[0], ARM[1] + dy, ARM[2]); S(f, "arm.R", (1.1, st, 1.1))
    for f in (7, 25, 34, 44, 49, 62): rarm(f)
    rarm(28, 10); rarm(31, -22, 1.45); rarm(46, 8)           # dip -> flick up (toss), catch dip
    for f in (7, 62):                                     # left hand rests on the hip
        R(f, "arm.L", 0, -28, -18); S(f, "arm.L", (1, 1, 1))
    R(8, "head", x=12); R(24, "head", x=12)
    for i, f in enumerate(range(10, 25, 3)):            # sizzle: little side shakes
        R(f, "body", z=4 if i % 2 else -4)
    R(25, "body")
    S(27, "body", (1.04, 0.95, 1.04)); L(27, "root", 0.0)                 # dip
    S(31, "body", (0.97, 1.05, 0.97)); L(31, "root", 0.02); R(31, "head", x=-6)   # toss
    R(37, "head", x=-18); R(43, "head", x=6)                               # watch the egg go up and land
    S(36, "body", (1, 1, 1)); L(36, "root", 0.0)
    S(45, "body", (1.03, 0.96, 1.03)); S(48, "body", (1, 1, 1))           # catch
    # proud: little hops with closed eyes
    L(51, "root", 0.04); L(55, "root", 0.0); L(58, "root", 0.03); L(61, "root", 0.0)
    R(51, "head", x=-4); R(60, "head", x=0)
    ears_bounce([(1, 0), (27, 4), (33, -10), (40, 6), (46, 8), (51, -8), (56, 6), (62, 0)])
    rest(68); rest(F)
    eyes([(1, 0), (20, 0), (21, 1), (23, 1), (24, 0), (48, 0), (49, 1), (63, 1), (64, 0), (F, 0)])
    wag(48, 64, 20, 3)
    # --- chef hat on the head ---
    hippo = bpy.data.objects["Hippo"]
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get(); ev = hippo.evaluated_get(deps); mwi = hippo.matrix_world.inverted()
    sc.frame_set(1); bpy.context.view_layer.update()
    hit, loc, nor, fi = ev.ray_cast(mwi @ Vector((0, 0.02, 1.0)), (mwi.to_3x3() @ Vector((0, 0, -1))).normalized())
    top = hippo.matrix_world @ loc if hit else Vector((0, 0, 0.42))
    print("head top", tuple(round(v, 3) for v in top))
    hat = chef_hat(top)
    props.attach(hat, rig, "head", 1)
    props.key_scale(hat, [(1, 0), (3, 0), (7, 1.1), (9, 1.0), (64, 1.0), (68, 0), (F, 0)])
    # --- pan held by the handle in the right hand (follows arm.R) ---
    hand = props.hand_pos(rig, "arm.R", 20)
    # pan points FORWARD (toward the camera, 대표 11-12): handle runs back/up to the hand, pan sits in front of the belly
    GRIP, TILT = 0.27, math.radians(30)                  # +X tilt shows the cooking surface to the camera
    d = GRIP * math.cos(TILT); vx = hand.x * 0.25; vy = math.sqrt(max(d * d - vx * vx, 1e-6))
    yaw = math.atan2(-vx, vy)
    print("right hand", tuple(round(v, 3) for v in hand), "yaw", round(math.degrees(yaw), 1))
    pan, egg = frying_pan()
    pan.location = Vector((hand.x - vx, hand.y - vy, hand.z - GRIP * math.sin(TILT)))
    pan.rotation_euler = (TILT, 0, yaw)
    props.attach(pan, rig, "arm.R", 20)
    sc.frame_set(1)
    props.key_scale(pan, [(1, 0), (4, 0), (8, 1.08), (10, 1.0), (62, 1.0), (66, 0), (F, 0)])
    for f, dz, tilt in ((1, 0, 0), (25, 0, 0), (28, -0.025, 6), (31, 0.03, -14), (34, 0.0, 0), (44, 0.0, 0),
                        (46, -0.02, 4), (49, 0, 0), (F, 0, 0)):
        pan.delta_location = (0, 0, dz); pan.keyframe_insert("delta_location", frame=f)
        pan.delta_rotation_euler = (math.radians(tilt), 0, 0); pan.keyframe_insert("delta_rotation_euler", frame=f)
    for i, f in enumerate(range(10, 25, 3)):            # egg slides a little with the shakes
        egg.delta_location = (0.008 if i % 2 else -0.008, 0, 0); egg.keyframe_insert("delta_location", frame=f)
    for f, z, rx in ((25, 0, 0), (31, 0.02, 0), (34, 0.36, 120), (37, 0.5, 220), (40, 0.36, 300), (44, 0.0, 360), (F, 0.0, 360)):
        egg.delta_location = (0, 0, z); egg.keyframe_insert("delta_location", frame=f)
        egg.delta_rotation_euler = (math.radians(rx), 0, 0); egg.keyframe_insert("delta_rotation_euler", frame=f)
    # sparkles when it lands
    face = math.radians(19)
    for i, (x, z, f0, s) in enumerate(((-0.34, 0.3, 46, 0.11), (0.36, 0.42, 48, 0.1), (-0.28, 0.55, 51, 0.09), (0.3, 0.6, 54, 0.08))):
        sp = props.sparkle(f"CookSparkle{i}", col=[(1.0, 0.86, 0.35), (1.0, 0.75, 0.82), (0.75, 0.9, 1.0), (1.0, 0.86, 0.35)][i])
        sp.location = (x, -0.25, z); sp.rotation_euler = (0, 0, face)
        props.key_scale(sp, [(1, 0), (f0 - 1, 0), (f0 + 2, s), (f0 + 4, s * 0.6), (f0 + 6, s * 1.1), (f0 + 10, 0), (F, 0)])
    return F

def _flower(name, col, r=0.026):
    """5-petal pastel flower, origin at its centre, faces local +Z"""
    import bmesh
    parts = []
    for k in range(5):
        a = 2 * math.pi * k / 5
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=r)
        for v in bm.verts: v.co.z *= 0.42; v.co.y *= 0.82
        for f in bm.faces: f.smooth = True
        o = props.obj_from_bm(bm, f"{name}_p{k}", [props.mat(f"Petal_{col}", col, 0.7)])
        o.location = (math.cos(a) * r * 0.95, math.sin(a) * r * 0.95, 0); o.rotation_euler = (0, 0, a + math.pi / 2)
        parts.append(o)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=r * 0.5)
    for v in bm.verts: v.co.z *= 0.6
    for f in bm.faces: f.smooth = True
    c = props.obj_from_bm(bm, f"{name}_c", [props.mat("FlowerCentre", (0.98, 0.85, 0.4), 0.6)])
    c.location = (0, 0, r * 0.25); parts.append(c)
    bpy.context.view_layer.update()
    return props.join(parts, name)

def flower_crown():
    """yellow band around the top of the head + pastel flowers on the front half (대표 sketch 2026-11-12)"""
    hippo = bpy.data.objects["Hippo"]
    band = props.headband(hippo, z0=0.372, tilt=-0.08, height=0.034, thick=0.014,
                          col=(0.98, 0.80, 0.30), stripe=(1.0, 0.88, 0.45))
    band.name = "CrownBand"
    bpy.context.view_layer.update()
    me = band.data; cz = band.location.z
    ring = [(band.matrix_world @ v.co) for v in me.vertices if v.co.z > 0]     # top edge
    cols = [(0.99, 0.72, 0.78), (0.99, 0.97, 0.93), (0.60, 0.86, 0.62), (0.82, 0.74, 0.95),
            (0.99, 0.72, 0.78), (0.99, 0.97, 0.93), (0.98, 0.90, 0.62), (0.60, 0.86, 0.62), (0.82, 0.74, 0.95)]
    angs = [-90 + d for d in (0, -28, 28, -56, 56, -84, 84, -122, 122)]
    for i, (a, col) in enumerate(zip(angs, cols)):
        ar = math.radians(a)
        wrap = lambda d: abs((d + math.pi) % (2 * math.pi) - math.pi)
        p = min(ring, key=lambda q: wrap(math.atan2(q.y, q.x) - ar))
        out = Vector((math.cos(ar), math.sin(ar), 0))
        n = (out * 0.75 + Vector((0, 0, 0.66))).normalized()
        fl = _flower(f"CrownFlower{i}", col, r=0.036 if i < 3 else 0.03)
        fl.location = p + out * 0.006 + Vector((0, 0, 0.006))
        fl.rotation_euler = n.to_track_quat("Z", "Y").to_euler()
        fl.rotation_euler.rotate_axis("Z", math.radians(17 * i))
        bpy.context.view_layer.update(); mw = fl.matrix_world.copy(); fl.parent = band
        fl.matrix_parent_inverse = band.matrix_world.inverted(); fl.matrix_world = mw
    return band

def milestone10():  # 누적 10번 축하 (전체 화면): float up underwater w/ flower crown, bubbles, swirl dance x2, "짠"
    F = 156
    rest(1)
    # enter from below, settle with a little overshoot, gentle bob the whole time
    L(1, "root", -1.7); L(20, "root", 0.06); L(26, "root", -0.02); L(32, "root", 0.0)
    for f in range(38, 108, 12):
        L(f, "root", 0.035 if (f // 12) % 2 else -0.01)
    L(110, "root", 0.06); L(118, "root", 0.0)
    for f in range(124, F + 1, 14):
        L(f, "root", 0.03 if (f // 14) % 2 else -0.01)
    # feet dangle / paddle
    for i, f in enumerate(range(1, F, 8)):
        a = 14 if i % 2 else -14
        R(f, "leg.L", x=a); R(f, "leg.R", x=-a)
    # float in: arms out paddling, blow bubbles (head slightly up)
    for i, f in enumerate(range(4, 36, 6)):
        arms(f, ly=45, lz=20 if i % 2 else -10)
    R(1, "head", x=6); R(22, "head", x=-6); R(36, "head", x=0)
    # swirl dance: arms up high, 2 full turns with a body wobble
    arms(42, ly=84); S(42, "arm.L", (1.12, 1.45, 1.12)); S(42, "arm.R", (1.12, 1.45, 1.12))
    for i, f in enumerate(range(48, 100, 6)):
        arms(f, ly=84 if i % 2 else 72, lx=10 if i % 2 else -10)
    S(36, "body", (1, 1, 1)); S(44, "body", (0.95, 1.08, 0.95)); S(98, "body", (0.95, 1.08, 0.95))
    rp = P["root"]; rp.rotation_mode = "XYZ"
    spin = [(1, 0), (40, 0), (48, 70), (56, 190), (64, 330), (72, 460), (80, 590), (88, 680), (96, 715), (102, 720), (F, 720)]
    for f, deg in spin:
        rp.rotation_euler = (0, math.radians(deg), 0); rp.keyframe_insert("rotation_euler", frame=f)
    for i, f in enumerate(range(44, 100, 7)):
        R(f, "body", z=7 if i % 2 else -7)
    R(102, "body")
    # "짠!": face the camera, arms wide up, stretch, happy closed eyes
    arms(104, ly=60, lz=-10); S(104, "body", (1.05, 0.94, 1.05))
    arms(110, ly=86, lz=10); S(110, "arm.L", (1.12, 1.5, 1.12)); S(110, "arm.R", (1.12, 1.5, 1.12))
    S(110, "body", (0.94, 1.09, 0.94)); R(110, "head", x=-8)
    S(116, "body", (1, 1, 1)); R(116, "head", x=-4)
    for i, f in enumerate(range(120, F, 9)):           # little happy arm waves while floating
        arms(f, ly=80 if i % 2 else 70, lz=12 if i % 2 else 2)
    ears_bounce([(1, 0), (20, -10), (30, 8), (40, 0), (60, -12), (80, -12), (100, 0), (106, 12), (112, -8), (118, 0)])
    eyes([(1, 0), (16, 1), (18, 0), (60, 0), (61, 1), (64, 1), (65, 0), (108, 0), (109, 1), (F, 1)])
    wag(20, F - 4, 22, 4)
    sc.frame_set(32); bpy.context.view_layer.update()     # rest height, facing the camera
    crown = flower_crown()
    props.attach(crown, rig, "head", 32)
    # snout point for the 2D bubble overlay (render_milestone.py projects it per frame)
    hippo = bpy.data.objects["Hippo"]
    sc.frame_set(32); bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get(); ev = hippo.evaluated_get(deps); mwi = hippo.matrix_world.inverted()
    hit, loc, nor, fi = ev.ray_cast(mwi @ Vector((0, -1.0, 0.12)), (mwi.to_3x3() @ Vector((0, 1, 0))).normalized())
    sp = hippo.matrix_world @ loc if hit else Vector((0, -0.33, 0.12))
    print("snout", hit, tuple(round(v, 3) for v in sp))
    e = bpy.data.objects.new("SnoutPt", None); sc.collection.objects.link(e); e.location = sp
    props.attach(e, rig, "head", 32)
    return F

# ------------------------------------------------------------------ tap reactions (방에서 단짝 탭 → 랜덤, 2026-11-14)
def _key_shadow(f, x=0.0, h=0.0):
    """render_clip.py reads these animated rig props: shadow x (world) and lift above the floor"""
    rig["shx"] = x; rig["shh"] = h
    rig.keyframe_insert('["shx"]', frame=f); rig.keyframe_insert('["shh"]', frame=f)

def puff(name, n=6, seed=1, r=0.07):
    """soft cartoon gas cloud: a lumpy cluster of spheres, pale butter-mint (ART_BIBLE 4, 2026-11-14)"""
    import random
    rnd = random.Random(seed); parts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.3, 0.3)
        rr = r * rnd.uniform(0.7, 1.15)
        loc = (math.cos(a) * r * 0.9, rnd.uniform(-0.02, 0.02), math.sin(a) * r * 0.55)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rr, location=loc, segments=20, ring_count=12)
        parts.append(bpy.context.active_object)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r * 1.25, location=(0, 0, 0), segments=24, ring_count=14)
    parts.append(bpy.context.active_object)
    o = props.join(parts, name)
    for pg in o.data.polygons: pg.use_smooth = True
    o.data.materials.clear(); o.data.materials.append(props.mat("Puff", (0.93, 0.95, 0.80), 0.8, emit=0.35))
    if hasattr(o, "visible_shadow"): o.visible_shadow = False
    return o

def fart_hop():  # 탭 반응: 뿡! 방귀 추진력으로 위로 방방 3번 → 착지, 헤헤 쑥스러운 웃음
    F = 90; rest(1)
    _key_shadow(1)
    # strain: tiny squat, eyes squeezed, body trembles
    S(5, "body", (1.06, 0.9, 1.06)); L(5, "root", -0.02); arms(5, ly=-30, lz=10)
    R(6, "body", y=2); R(7, "body", y=-2); R(8, "body", y=2); R(9, "body", y=0)
    hops = [(10, 0.46, 10), (31, 0.3, 9), (50, 0.16, 7)]     # (launch frame, height, frames to apex); needs render h=1100
    for i, (f0, hgt, up) in enumerate(hops):
        S(f0, "body", (0.92, 1.1, 0.92)); L(f0, "root", 0.0)                       # pop
        arms(f0 + 2, ly=70, lz=-10); S(f0 + 2, "arm.L", (1.1, 1.3, 1.1)); S(f0 + 2, "arm.R", (1.1, 1.3, 1.1))
        L(f0 + up, "root", hgt); S(f0 + up, "body", (0.97, 1.04, 0.97))
        R(f0 + up, "leg.L", x=18); R(f0 + up, "leg.R", x=22)                      # legs dangle
        arms(f0 + up - 2, ly=55, lz=-25); arms(f0 + up + 1, ly=75, lz=5)           # flail
        R(f0 + up, "body", x=-6 + 3 * i); R(f0 + up, "head", x=-8)
        land = f0 + 2 * up - 1
        L(land, "root", 0.0); S(land, "body", (1.08, 0.88, 1.08)); R(land, "leg.L"); R(land, "leg.R")
        arms(land, ly=-20, lz=10); S(land, "arm.L", (1, 1, 1)); S(land, "arm.R", (1, 1, 1)); R(land, "body"); R(land, "head")
        S(land + 3, "body", (1.0, 1.0, 1.0))
        for f, hh in ((f0, 0), (f0 + up, hgt), (land, 0)): _key_shadow(f, 0, hh)
    ears_bounce([(1, 0), (10, 0), (15, 16), (20, -14), (27, 10), (34, 14), (40, -12), (47, 8), (53, 10), (57, -8), (62, 0)])
    # 헤헤: head tilt, body wiggle, tail wag, eyes closed smile
    for f, y, z in ((66, 10, 6), (72, -6, -4), (78, 8, 4), (84, 0, 0)):
        R(f, "head", y=y, x=4); R(f, "body", z=z)
    arms(66, ly=-25, lz=30); arms(82, ly=-25, lz=30)
    rest(F); _key_shadow(F)
    eyes([(1, 0), (4, 1), (10, 0), (62, 0), (64, 1), (84, 1), (85, 0), (F, 0)])
    wag(62, 86, 22, 3)
    # gas puffs: pop at the butt on each launch, stay low and drift backward/sideways while the hippo rises
    for i, (f0, hgt, up) in enumerate(hops):
        sz = (1.0, 0.75, 0.55)[i]
        for j, (sx, seed) in enumerate(((-1, 3 + i), (1, 7 + i))):
            if i > 0 and j == 1: continue
            pf = puff(f"Puff{i}{j}", seed=seed, r=0.075 * sz)
            side = sx if i == 0 else (-1 if i == 1 else 1)
            start = Vector((0.06 * side, 0.12, -0.42)); end = Vector((0.36 * side, 0.18, -0.36 + 0.04 * i))
            for f, t, s in ((1, 0, 0), (f0 - 1, 0, 0), (f0, 0, 0.6 * sz), (f0 + 3, 0.45, 1.25 * sz),
                            (f0 + 9, 0.85, 1.1 * sz), (f0 + 15, 1.0, 0.0), (F, 1.0, 0.0)):
                pf.location = start.lerp(end, t); pf.keyframe_insert("location", frame=f)
                s = max(s, 1e-3); pf.scale = (s, s, s); pf.keyframe_insert("scale", frame=f)
    return F

def roll():  # 탭 반응: 몸을 동그랗게 말아 옆으로 데굴 한 바퀴 → 반대로 데굴 돌아와 '짠' (왼쪽은 앱이 좌우 뒤집기)
    F = 76; TRAVEL = float(os.environ.get("ROLL_TRAVEL", "0.9"))
    rest(1); _key_shadow(1)
    rp = P["root"]; B = rp.bone.matrix_local
    c0 = Vector((0, 0, -0.06)); A, Bh = 0.33, 0.44           # curled half-width / half-height
    def curl(f, k=1.0):
        S(f, "body", (1 + 0.05 * k, 1 - 0.12 * k, 1 + 0.05 * k)); R(f, "head", x=12 * k)
        arms(f, ly=-45 * k, lz=40 * k); R(f, "leg.L", x=-55 * k); R(f, "leg.R", x=-55 * k)
        R(f, "ear.L", y=14 * k); R(f, "ear.R", y=-14 * k)
    def pose_root(f, theta, dx, lift=0.0):
        h = math.sqrt((A * math.sin(theta)) ** 2 + (Bh * math.cos(theta)) ** 2)
        c = Vector((dx, 0, -0.5 + h + lift))
        Rw = Matrix.Rotation(theta, 4, "Y")
        M = B.inverted() @ Matrix.Translation(c) @ Rw @ Matrix.Translation(-c0) @ B
        loc, q, _ = M.decompose()
        rp.location = loc; rp.rotation_quaternion = q
        rp.keyframe_insert("location", frame=f); rp.keyframe_insert("rotation_quaternion", frame=f)
        _key_shadow(f, dx, max(0.0, lift))
    ease = lambda t: t * t * (3 - 2 * t)
    # tuck in
    S(4, "body", (1.06, 0.9, 1.06)); curl(9)
    for f in range(1, 10): pose_root(f, 0, 0, 0)
    # roll right (top moves +X), then a little settle, then roll back
    R1, R2 = (10, 30), (40, 60)
    for f in range(R1[0], R1[1] + 1):
        t = ease((f - R1[0]) / (R1[1] - R1[0])); pose_root(f, 2 * math.pi * t, TRAVEL * t)
    for f in range(R1[1] + 1, R2[0]):                       # rock a little at the far end
        w = math.sin((f - R1[1]) / (R2[0] - R1[1]) * math.pi)
        pose_root(f, 2 * math.pi - 0.12 * w, TRAVEL - 0.02 * w)
    for f in range(R2[0], R2[1] + 1):
        t = ease((f - R2[0]) / (R2[1] - R2[0])); pose_root(f, 2 * math.pi * (1 - t), TRAVEL * (1 - t))
    curl(R2[1])
    # pop up: '짠' — uncurl, small hop, arms out
    for f, lift in ((61, 0.0), (64, 0.07), (67, 0.0), (F, 0.0)): pose_root(f, 0, 0, lift)
    rest(64, ("body", "head", "ear.L", "ear.R", "leg.L", "leg.R", "tail"))
    S(64, "body", (0.95, 1.08, 0.95)); arms(64, ly=60, lz=-10)
    S(67, "body", (1.06, 0.92, 1.06)); arms(68, ly=40); S(71, "body", (1, 1, 1))
    rest(F, ("body", "head", "ear.L", "ear.R", "arm.L", "arm.R", "leg.L", "leg.R", "tail")); S(F, "body", (1, 1, 1))
    eyes([(1, 0), (6, 1), (62, 1), (63, 0), (F, 0)])
    wag(62, 74, 20, 3)
    # floor pass: the curled shape is not an ellipse -> measure the lowest vertex per frame and re-key so it touches the floor
    keys = {}
    for f in range(1, F + 1):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        ho = bpy.data.objects["Hippo"].evaluated_get(dg); mw = ho.matrix_world
        keys[f] = min((mw @ v.co).z for v in ho.data.vertices) + 0.5
    rest_gap = keys[1]
    for f in range(10, 61):
        rp.location = (0, 0, 0); sc.frame_set(f)
        loc = Vector(rp.location); dz = keys[f] - rest_gap
        rp.location = loc - (B.inverted().to_3x3() @ Vector((0, 0, dz))); rp.keyframe_insert("location", frame=f)
    print("ROLL floor gaps", [round(keys[f] - rest_gap, 3) for f in range(10, 61, 5)])
    return F

ACTIONS = {"fart_hop": fart_hop, "roll": roll, "milestone10": milestone10, "cook": cook, "drink": drink, "eat_strawberry": eat_strawberry, "sit_in": sit_in, "sit_loop": sit_loop, "sit_out": sit_out, "sweep": sweep, "hop": hop, "nod": nod, "write": write, "desk_write": desk_write, "desk_laptop": desk_laptop, "eat": eat, "stretch_spin": stretch_spin, "wave": wave}
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
def place_cam(elev):
    cam.location = target + Vector((0.35, -1, elev)).normalized() * 10
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
if ACTION.startswith("desk_"):
    # start/end at the shared idle angle, glide up to look down on the desk while seated
    LOW, HIGH = 0.12, 0.5
    def ease(t): return t * t * (3 - 2 * t)
    for f in range(1, F + 1):
        if f <= 10: e = LOW + (HIGH - LOW) * ease((f - 1) / 9)
        elif f >= 52: e = HIGH + (LOW - HIGH) * ease(min(1, (f - 52) / 10))
        else: e = HIGH
        place_cam(e)
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
else:
    place_cam(0.12)
sc.render.filepath = os.path.join(rdir, f"{ACTION}_frames", "f_")
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(animation=True)
print("RENDERED", ACTION)
