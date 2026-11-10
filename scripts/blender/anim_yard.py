# Usage: Blender -b -P anim_yard.py -- rig_dir action
# 25° yard/garden clips (WORLD.md 7장 '25° 단짝 동작'). Saves rig_dir/hippo_<action>.blend;
# final render goes through render_clip.py <out> 0.5 (shared look + floor shadow).
# Same helper conventions as anim_actions.py: rotations in armature-rest (= character) axes,
#   X = character left->right, Y = back, Z = up. leg x<0 = forward. arm.L +y raises, arm.R -y raises.
# Facing: the root is yawed with an euler on its local Y (= world up).
#   front = 0 (same 3/4 as idle), back = 180, side = SIDE_YAW (walks toward screen-right; left = mirror in app)
import bpy, sys, os, math
from mathutils import Vector, Euler, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

argv = sys.argv[sys.argv.index("--") + 1:]
rdir, ACTION = argv[0], argv[1]
SIDE_YAW = float(os.environ.get("SIDE_YAW", "65"))   # 65 = mostly right, face still visible (3/4); 90 = pure profile
bpy.ops.wm.open_mainfile(filepath=os.path.join(rdir, "hippo_rig_idle.blend"))
sc = bpy.context.scene
rig = bpy.data.objects["HippoRig"]
P = rig.pose.bones
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions.new(ACTION)
for pb in P:
    pb.rotation_mode = "QUATERNION"
    pb.location = (0, 0, 0); pb.scale = (1, 1, 1); pb.rotation_quaternion = (1, 0, 0, 0)
P["root"].rotation_mode = "XYZ"; P["root"].rotation_euler = (0, 0, 0)


def fcurves(a):
    out = list(getattr(a, "fcurves", []) or [])
    try:
        for layer in a.layers:
            for strip in layer.strips:
                for cb in strip.channelbags: out += list(cb.fcurves)
    except Exception:
        pass
    return out


def wq(bone, x=0, y=0, z=0, order="XYZ"):
    Bm = P[bone].bone.matrix_local.to_3x3()
    Rw = Euler((math.radians(x), math.radians(y), math.radians(z)), order).to_matrix()
    return (Bm.inverted() @ Rw @ Bm).to_quaternion()


def R(f, bone, x=0, y=0, z=0, order="XYZ"):
    P[bone].rotation_quaternion = wq(bone, x, y, z, order); P[bone].keyframe_insert("rotation_quaternion", frame=f)


def L(f, bone, up=0.0):
    P[bone].location = (0, up, 0); P[bone].keyframe_insert("location", frame=f)


def S(f, bone, s):
    P[bone].scale = s; P[bone].keyframe_insert("scale", frame=f)


def YAW(f, deg):
    P["root"].rotation_euler = (0, math.radians(deg), 0); P["root"].keyframe_insert("rotation_euler", frame=f)


def arms(f, ly=0, lz=0, ry=None, rz=None, lx=0, rx=None, order="XYZ"):
    ry = -ly if ry is None else ry; rz = -lz if rz is None else rz; rx = lx if rx is None else rx
    R(f, "arm.L", lx, ly, lz, order); R(f, "arm.R", rx, ry, rz, order)


def eyes(keys):
    dec = bpy.data.objects["EyeDecal"]; nt = dec.data.materials[0].node_tree
    if nt.animation_data: nt.animation_data.action = None
    for name in ("BlinkColor", "BlinkAlpha"):
        sock = nt.nodes[name].inputs[0]
        for f, v in keys:
            sock.default_value = v; sock.keyframe_insert("default_value", frame=f)
    for fc in fcurves(nt.animation_data.action):
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"


# ------------------------------------------------------------------ walk cycle (in place; the app moves the sprite)
# speed in the app = 0.6 unit/s. cycle C frames = 2 steps -> stride per step = 0.6 * C/2/24
C = int(os.environ.get("WALK_C", "16"))          # 16 = 0.67 s per cycle, 3 steps/s: short-legged waddle
CYCLES = int(os.environ.get("WALK_CYCLES", "3"))  # loop length C*CYCLES (48 f = 2 s); one blink per loop
LEG = float(os.environ.get("WALK_LEG", "30"))     # leg swing (deg) -> stride


def walk(yaw, blink=True):
    F = C * CYCLES
    for k in range(CYCLES + 1):
        b = 1 + k * C
        for ph, side in ((0, 1), (C // 2, -1)):          # contact: side=1 -> left leg forward
            f = b + ph
            if f > F + 1: continue
            R(f, "leg.L", x=-LEG * side); R(f, "leg.R", x=LEG * side)
            # opposite arm swings forward (arms first lowered toward the body, then swing on X)
            R(f, "arm.L", 24 * side, -18, 0, "YXZ"); R(f, "arm.R", -24 * side, 18, 0, "YXZ")
            L(f, "root", 0.0); S(f, "body", (1.035, 0.965, 1.035))
            R(f, "body", 2, 4 * side, -5 * side)          # lean onto the front foot side + small twist
            R(f, "head", 3, -2.5 * side, 3 * side)        # head counters the body a little
            fp = f + C // 4                                 # passing: legs under the body, up, stretched
            if fp <= F + 1:
                R(fp, "leg.L"); R(fp, "leg.R")
                R(fp, "arm.L", 0, -18, 0, "YXZ"); R(fp, "arm.R", 0, 18, 0, "YXZ")
                L(fp, "root", 0.032 * LEG / 30); S(fp, "body", (0.975, 1.03, 0.975))
                R(fp, "body", 2, 0, 0); R(fp, "head", 3, 0, 0)
            fe = f + 2                                      # ears lag behind the bob
            if fe <= F + 1:
                R(fe, "ear.L", y=6); R(fe, "ear.R", y=-6)
            fe2 = f + 6
            if fe2 <= F + 1:
                R(fe2, "ear.L", y=-5); R(fe2, "ear.R", y=5)
            R(f, "tail", z=16 * side)
    for f in range(1, F + 2):
        YAW(f, yaw) if f in (1, F + 1) else None
    eyes([(1, 0), (29, 0), (30, 1), (32, 1), (33, 0), (F + 1, 0)] if blink else [(1, 0), (F + 1, 0)])
    return F


ACTIONS = {
    "walk_front": lambda: walk(0),
    "walk_back": lambda: walk(180, blink=False),
    "walk_side": lambda: walk(SIDE_YAW),
}


# ================================================================== yard item actions (2026-11-11)
# Clip origin (feet anchor, clip px (300, 684)) = the interact `stand` point. Items sit at ITEM_REL from it (world units,
# x right, y away from the camera). bench / hammock assume the stand IN FRONT of the item (proposal: stand = item + (0, -0.32),
# so the pet sorts in front of the item and the clip itself climbs back onto it); the others use today's manifest stands.
# Item geometry is built from yard.py for reference: hidden in the final render, or a holdout where it must cover the pet
# (bench slats/arms, hammock cloth, pond water) -> the app draws the item sprite, then the pet clip over it.
import random
from mathutils import Matrix
FLOORZ = -0.5
ITEM_REL = {"bench": (0.0, 0.32), "hammock": (0.0, 0.32), "picnic_mat": (0.1, 0.0),
            "flower_bed": (0.0, -0.42), "pond": (0.05, 0.0), "tree": (-0.3, 0.3)}
SIT_DROP = -0.115           # sitting on a surface: root this much below the surface (same as the room's sit)
SEAT = 0.1875               # bench seat top above the floor (yard.py bench: FLOOR + 0.17 + slat 0.035/2)
BENCH_SIT = (0.0, ITEM_REL["bench"][1] - 0.11, SEAT + SIT_DROP)    # back touches the backrest
WATER_DROP = -0.13          # standing in the pond: legs + belly bottom under the water


def RP(f, x=0.0, y=0.0, up=0.0):
    """root location in world terms (root local: X = x, Y = up, Z = -y)"""
    P["root"].location = (x, up, -y); P["root"].keyframe_insert("location", frame=f)


def ROT(f, x=0.0, y=0.0, z=0.0):
    P["root"].rotation_euler = (math.radians(x), math.radians(y), math.radians(z)); P["root"].keyframe_insert("rotation_euler", frame=f)


def SHADOW(f, v):
    rig["shadow"] = float(v); rig.keyframe_insert('["shadow"]', frame=f)


BODY = ("body", "head", "ear.L", "ear.R", "arm.L", "arm.R", "leg.L", "leg.R", "tail")


def rest(f, bones=BODY):
    for b in bones:
        R(f, b)
    S(f, "body", (1, 1, 1))
    for b in ("arm.L", "arm.R"): S(f, b, (1, 1, 1))


def ears(keys):
    for f, a in keys:
        R(f, "ear.L", y=-a); R(f, "ear.R", y=a)


def wag(f0, f1, amp=16, step=4):
    for i, f in enumerate(range(f0, f1, step)):
        R(f, "tail", z=amp if i % 2 else -amp)


def sit_pose(f, breathe=0.0, tilt=6, legs=-85, head_z=0, arm_l=(-18, 28), arm_r=None):
    for b in ("leg.L", "leg.R"):
        R(f, b, x=legs if not isinstance(legs, tuple) else (legs[0] if b == "leg.L" else legs[1]))
    ar = arm_r or arm_l
    R(f, "arm.L", 0, arm_l[0], arm_l[1]); R(f, "arm.R", 0, -ar[0], -ar[1])
    R(f, "head", x=5, y=tilt, z=head_z)
    S(f, "body", (1 - 0.4 * breathe, 1 + breathe, 1 - 0.4 * breathe))
    R(f, "body", x=3)


def item_ref(kind):
    """build the yard item around the clip origin; tag objects for render_clip.py (hidden / holdout)"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import yard as Yd
    before = set(bpy.data.objects.keys())
    if kind == "bench": Yd.bench(); item = Yd.SPOT["bench"]; hold = lambda n: True
    elif kind == "hammock": Yd.hammock(); item = Yd.SPOT["hammock"]; hold = lambda n: True
    elif kind == "picnic_mat": Yd.picnic_mat(); item = Yd.SPOT["picnic_mat"]; hold = lambda n: False
    elif kind == "flower_bed":
        Yd.flower_bed(); [Yd.bed_flower(k, i) for i, k in enumerate(("tulip", "sunflower", "tulip"))]
        item = Yd.SPOT["flower_bed"]; hold = lambda n: True
    elif kind == "pond": Yd.pond(); item = Yd.POND; hold = lambda n: n in ("PondWater", "PondDeep")
    elif kind == "tree": Yd.memory_tree(4); Yd.memory_fruits(4); item = Yd.TREE; hold = lambda n: True
    rel = ITEM_REL[kind]
    sx, sy = item[0] - rel[0], item[1] - rel[1]        # stand point in yard world coords
    for n in set(bpy.data.objects.keys()) - before:
        o = bpy.data.objects[n]
        if o.parent is None:
            o.location.x -= sx; o.location.y -= sy
        o["yard_ref"] = 1
        if hold(n) and o.type == "MESH": o["holdout"] = 1


def on_body(o, frame):
    body_m = rig.matrix_world @ P["body"].matrix
    o.parent = rig; o.parent_type = "BONE"; o.parent_bone = "body"
    o.matrix_parent_inverse = (body_m @ Matrix.Translation((0, P["body"].length, 0))).inverted()


def hands_at(f):
    sc.frame_set(f); bpy.context.view_layer.update()
    return (rig.matrix_world @ P["arm.L"].tail + rig.matrix_world @ P["arm.R"].tail) / 2


def key_scale(o, keys):
    for f, s in keys:
        s = max(s, 0.001); o.scale = (s, s, s); o.keyframe_insert("scale", frame=f)


def droplets(origin, f0, n=7, seed=1, spread=0.22, up=0.32, life=14, size=0.028):
    """water drops thrown up from origin at frame f0 (parabolas, pop out)"""
    import props
    rnd = random.Random(seed)
    m = props.mat("Drop", (0.72, 0.89, 1.0), 0.15, emit=0.25)
    for i in range(n):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size * rnd.uniform(0.7, 1.2), segments=12, ring_count=8)
        d = bpy.context.active_object; d.name = f"Drop{seed}_{i}"; d.data.materials.append(m)
        for p in d.data.polygons: p.use_smooth = True
        a = rnd.uniform(0, math.tau); r = spread * rnd.uniform(0.4, 1.0); h = up * rnd.uniform(0.6, 1.1)
        o = Vector(origin)
        for k in range(life + 1):
            t = k / life
            d.location = (o.x + math.cos(a) * r * t, o.y + math.sin(a) * r * 0.5 * t - 0.05 * t, o.z + 4 * h * t * (1 - t) - 0.06 * t)
            d.keyframe_insert("location", frame=f0 + k)
        key_scale(d, [(1, 0), (f0 - 1, 0), (f0, 1), (f0 + life - 3, 1), (f0 + life, 0), (max(F_END, f0 + life + 1), 0)])


def heart(f0, loc, s=0.07):
    import props
    sp = props.sparkle(f"Heart{f0}", col=(1.0, 0.62, 0.72)); sp.location = loc; sp.rotation_euler = (0, 0, math.radians(19))
    key_scale(sp, [(1, 0), (f0 - 1, 0), (f0 + 3, s * 1.2), (f0 + 5, s), (f0 + 16, s), (f0 + 20, 0), (F_END, 0)])
    for f, z in ((f0, loc[2]), (f0 + 20, loc[2] + 0.12)):
        sp.location.z = z; sp.keyframe_insert("location", frame=f)


F_END = 1


# ------------------------------------------------------------------ bench (벤치 앉기)
def sit_bench_in():
    global F_END; F = F_END = 30
    item_ref("bench"); RP(1); rest(1); SHADOW(1, 1)
    S(6, "body", (1.07, 0.92, 1.07)); RP(6, 0, 0, -0.03); arms(6, ly=-30, lz=10); R(6, "body", x=8)
    RP(13, 0, 0.13, 0.22); S(13, "body", (0.95, 1.06, 0.95)); arms(13, ly=40, lz=30); R(13, "leg.L", x=-40); R(13, "leg.R", x=-40)
    R(13, "body", x=-4); SHADOW(11, 0.6); SHADOW(16, 0)
    x, y, up = BENCH_SIT
    RP(18, x, y, up - 0.02); sit_pose(18); S(18, "body", (1.06, 0.93, 1.06))
    RP(22, x, y, up + 0.008); sit_pose(22); S(22, "body", (0.98, 1.02, 0.98))
    RP(26, x, y, up); sit_pose(26); RP(F, x, y, up); sit_pose(F)
    ears([(1, 0), (13, -8), (18, 10), (23, -4), (28, 0)])
    eyes([(1, 0), (F, 0)]); return F


def sit_bench_loop():
    global F_END; F = F_END = 96
    item_ref("bench"); x, y, up = BENCH_SIT
    for f in (1, F + 1): RP(f, x, y, up); SHADOW(f, 0)
    # little legs swing (dangling off the seat), head looks around, slow breathing
    swing = [(1, 0), (13, 1), (25, 0), (37, -1), (49, 0), (61, 1), (73, 0), (85, -1), (97, 0)]
    look = {1: 0, 25: 0, 37: 14, 55: 14, 67: 0, 77: -10, 88: -10, 97: 0}
    for f, s in swing:
        hz = look.get(f, None)
        sit_pose(f, breathe=0.012 if s else 0.0, legs=(-85 + 14 * s, -85 - 14 * s),
                 head_z=hz if hz is not None else 0, tilt=6 + (3 if s else 0))
    for f, z in look.items(): R(f, "head", x=5, y=6, z=z)
    wag(1, 96, 10, 12); R(97, "tail", z=-10)
    eyes([(1, 0), (58, 0), (59, 1), (63, 1), (64, 0), (F + 1, 0)]); return F


def sit_bench_out():
    global F_END; F = F_END = 26
    item_ref("bench"); x, y, up = BENCH_SIT
    RP(1, x, y, up); sit_pose(1); SHADOW(1, 0)
    RP(6, x, y - 0.03, up); sit_pose(6); R(6, "body", x=14); arms(6, ly=-30, lz=12); S(6, "body", (1.05, 0.95, 1.05))
    RP(12, 0, 0.1, 0.16); S(12, "body", (0.95, 1.06, 0.95)); arms(12, ly=35, lz=25); R(12, "leg.L", x=-30); R(12, "leg.R", x=-30)
    R(12, "body", x=0); SHADOW(10, 0); SHADOW(14, 0.7)
    RP(17, 0, 0, -0.025); rest(17); S(17, "body", (1.07, 0.92, 1.07)); SHADOW(17, 1)
    RP(21, 0, 0, 0.006); rest(21); S(21, "body", (0.98, 1.02, 0.98))
    RP(F); rest(F); SHADOW(F, 1)
    ears([(1, 0), (12, -8), (17, 10), (22, -4), (F, 0)])
    eyes([(1, 0), (F, 0)]); return F


# ------------------------------------------------------------------ picnic mat (매트에 앉기 / 먹기)
def mat_sit(f, **kw):
    RP(f, 0, 0, SIT_DROP); sit_pose(f, **kw)


def sit_eat_in():
    global F_END; F = F_END = 24
    item_ref("picnic_mat"); RP(1); rest(1); SHADOW(1, 1)
    S(6, "body", (1.03, 0.97, 1.03)); RP(6)
    mat_sit(16); RP(13, 0, 0, SIT_DROP - 0.012); S(16, "body", (1.04, 0.96, 1.04)); mat_sit(F)
    ears([(1, 0), (14, 6), (19, -3), (F, 0)])
    eyes([(1, 0), (F, 0)]); return F


def sit_eat_loop():          # seated on the mat: breathing, looks at the basket (behind right), sways a little
    global F_END; F = F_END = 96
    item_ref("picnic_mat")
    keys = [(1, 0.0, 0, 6), (19, 0.012, 0, 8), (37, 0.0, 18, 8), (55, 0.012, 18, 10), (73, 0.0, 0, 6), (85, 0.01, -6, 4), (97, 0.0, 0, 6)]
    for f, b, hz, tl in keys:
        mat_sit(f, breathe=b, head_z=hz, tilt=tl)
    for f in (1, 97): SHADOW(f, 1)
    wag(1, 96, 8, 16); R(97, "tail", z=-8)
    eyes([(1, 0), (66, 0), (67, 1), (71, 1), (72, 0), (F + 1, 0)]); return F


def _mat_eat(food):
    global F_END; F = F_END = 56
    item_ref("picnic_mat")
    mat_sit(1); SHADOW(1, 1); SHADOW(F, 1)
    hold = dict(arm_l=(55, 80))
    for f in (8, 46):
        mat_sit(f, **hold); S(f, "arm.L", (1.1, 1.5, 1.1)); S(f, "arm.R", (1.1, 1.5, 1.1))
    for i, f in enumerate(range(11, 44, 4)):
        RP(f, 0, 0, SIT_DROP + (0.01 if i % 2 else 0.0))
        R(f, "head", x=16 if i % 2 else 4, y=4)
        S(f, "body", (1.02, 0.98, 1.02) if i % 2 else (1, 1, 1))
    ears([(1, 0), (13, 6), (21, -4), (29, 6), (37, -4), (45, 0)])
    mat_sit(52); mat_sit(F); wag(8, 48, 16, 4)
    eyes([(1, 0), (10, 1), (43, 1), (44, 0), (F, 0)])
    h = hands_at(24)
    if food == "strawberry":
        import props
        o = props.strawberry(0.09); o.location = Vector((h.x, h.y - 0.07, h.z + 0.03))
        o.rotation_euler = (math.radians(28), 0, math.radians(15))
    else:
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "anim_actions.py")).read()
        a = src.index("def make_sweet_potato"); b = src.index("\n\n\ndef ", a)
        exec(src[a:b], globals())
        o = make_sweet_potato(); o.location = Vector((h.x, h.y - 0.07, h.z - 0.005)); o.rotation_euler = (math.radians(18), 0, 0)
    on_body(o, 24); sc.frame_set(1)
    key_scale(o, [(1, 0), (6, 0), (9, 1.08), (11, 1.0), (17, 1.0), (18, 0.86), (27, 0.86), (28, 0.72),
                  (37, 0.72), (38, 0.58), (44, 0.58), (48, 0), (F, 0)])
    if food != "strawberry":     # sweet potato gets shorter (x) instead of smaller
        for fc in fcurves(o.animation_data.action):
            if fc.array_index != 0:
                for kp in fc.keyframe_points:
                    if 0.05 < kp.co.y < 0.99: kp.co.y = 1.0
    return F


def sit_eat_strawberry(): return _mat_eat("strawberry")
def sit_eat_sweetpotato(): return _mat_eat("sweet_potato")


def sit_eat_out():
    global F_END; F = F_END = 20
    item_ref("picnic_mat"); mat_sit(1); SHADOW(1, 1)
    RP(8, 0, 0, SIT_DROP + 0.02); S(8, "body", (0.97, 1.04, 0.97))
    RP(16, 0, 0, 0.01); rest(16); RP(F); rest(F); SHADOW(F, 1)
    ears([(1, 0), (10, 5), (16, -3), (F, 0)])
    eyes([(1, 0), (F, 0)]); return F


# ------------------------------------------------------------------ hammock (해먹 눕기)
LIE_ROT = tuple(float(v) for v in os.environ.get("LIE_ROT", "-30,0,90").split(","))       # root euler ZYX: roll 90 (head to screen-left), then tilt the belly up 40
LIE = None
LIE_LIFT = float(os.environ.get("LIE_LIFT", "0.09"))   # body rests ON the sagging cloth, near edge under the face


LIE_HEAD = tuple(float(v) for v in os.environ.get("LIE_HEAD", "38,-14,0").split(","))


def lie_limbs(f, breathe=0.0, head=None):
    head = head or LIE_HEAD
    R(f, "arm.L", 20, 40, 40, "YXZ"); R(f, "arm.R", -20, -40, -40, "YXZ")        # hands resting on the belly
    R(f, "leg.L", x=-30, z=-8); R(f, "leg.R", x=-20, z=8)
    R(f, "head", *head)
    S(f, "body", (1 + 0.5 * breathe, 1 - 0.2 * breathe, 1 + 0.5 * breathe)); R(f, "body")


def lie_fit():
    """root location so the lying body sits in the cloth (min z = cloth bottom, centre over the hammock)"""
    global LIE
    P["root"].rotation_mode = "ZYX"
    P["root"].rotation_euler = [math.radians(a) for a in LIE_ROT]
    lie_limbs(500); bpy.context.view_layer.update()
    hip = bpy.data.objects["Hippo"]; dg = bpy.context.evaluated_depsgraph_get()
    me = hip.evaluated_get(dg).to_mesh(); vs = [hip.matrix_world @ v.co for v in me.vertices]
    cx = sum(v.x for v in vs) / len(vs); cy = sum(v.y for v in vs) / len(vs); mz = min(v.z for v in vs)
    hip.evaluated_get(dg).to_mesh_clear()
    tx, ty = ITEM_REL["hammock"][0] - 0.12, ITEM_REL["hammock"][1]   # vertex centroid sits in the (dense) head: shift left so the feet stay in frame
    LIE = (tx - cx, ty - cy, (FLOORZ + 0.17 + LIE_LIFT) - mz)
    for fc in fcurves(rig.animation_data.action):     # drop the probe keys
        for kp in list(fc.keyframe_points):
            if kp.co.x == 500: fc.keyframe_points.remove(kp)
    print("LIE fit", tuple(round(v, 3) for v in LIE))


def lie_root(f, k=1.0, lift=0.0):
    """k: 0 = standing at the stand point, 1 = lying in the hammock"""
    x, y, up = LIE
    RP(f, x * k, y * k, up * k + lift); ROT(f, LIE_ROT[0] * k, 0, LIE_ROT[2] * k)


def lie_in():
    global F_END; F = F_END = 40
    item_ref("hammock"); lie_fit(); P["root"].rotation_mode = "ZYX"
    lie_root(1, 0); rest(1); SHADOW(1, 1)
    lie_root(6, 0, -0.03); S(6, "body", (1.07, 0.92, 1.07)); arms(6, ly=-30, lz=10); R(6, "body", x=8)
    lie_root(14, 0.45, 0.2); S(14, "body", (0.95, 1.06, 0.95)); arms(14, ly=50, lz=30); R(14, "body", x=-6)
    R(14, "leg.L", x=-40); R(14, "leg.R", x=-40); SHADOW(12, 0.5); SHADOW(17, 0)
    lie_root(21, 1.0, -0.02); lie_limbs(21); S(21, "body", (1.06, 0.95, 1.06))
    lie_root(26, 1.0, 0.012); lie_limbs(26)
    lie_root(31, 1.0, 0.0); lie_limbs(31); lie_root(F, 1.0); lie_limbs(F, head=None)
    ears([(1, 0), (14, -8), (21, 10), (27, -4), (32, 0)])
    eyes([(1, 0), (34, 0), (35, 1), (F, 1)]); return F


def lie_loop():               # napping: slow breathing, an ear twitch, a sleepy head nuzzle
    global F_END; F = F_END = 96
    item_ref("hammock"); lie_fit(); P["root"].rotation_mode = "ZYX"
    for f in (1, F + 1): lie_root(f); SHADOW(f, 0)
    for f, b in ((1, 0.0), (25, 0.02), (49, 0.0), (73, 0.02), (97, 0.0)):
        lie_limbs(f, b, head=None)
    R(60, "head", LIE_HEAD[0], LIE_HEAD[1] - 4, LIE_HEAD[2] - 4); R(70, "head", *LIE_HEAD)
    ears([(1, 0), (40, 0), (42, -12), (44, 4), (47, 0), (97, 0)])
    for f, z in ((1, 0), (48, 8), (97, 0)): R(f, "tail", z=z)
    eyes([(1, 1), (F + 1, 1)]); return F


def lie_out():
    global F_END; F = F_END = 36
    item_ref("hammock"); lie_fit(); P["root"].rotation_mode = "ZYX"
    lie_root(1); lie_limbs(1); SHADOW(1, 0)
    lie_root(6); lie_limbs(6, head=(LIE_HEAD[0] - 6, LIE_HEAD[1] + 8, LIE_HEAD[2])); ears([(1, 0), (5, -10), (9, 6), (12, 0)])
    lie_root(12, 0.75, 0.03); S(12, "body", (1.04, 0.97, 1.04)); arms(12, ly=-20, lz=20); R(12, "head")
    lie_root(19, 0.3, 0.16); S(19, "body", (0.95, 1.06, 0.95)); arms(19, ly=40, lz=30); R(19, "leg.L", x=-30); R(19, "leg.R", x=-30)
    SHADOW(16, 0); SHADOW(21, 0.7)
    lie_root(25, 0, -0.025); rest(25); S(25, "body", (1.07, 0.92, 1.07)); SHADOW(25, 1)
    lie_root(29, 0, 0.006); rest(29); S(29, "body", (0.98, 1.02, 0.98))
    lie_root(F, 0); rest(F)
    eyes([(1, 1), (4, 1), (5, 0), (F, 0)]); return F


# ------------------------------------------------------------------ pond (물장구)
def water_pose(f, l=0, r=0, bob=0.0):
    """standing in the water; l/r = arm slap phase (1 = raised, -1 = slapped down on the water)"""
    RP(f, 0, 0, WATER_DROP + bob)
    def arm(side, ph):
        y = {1: 85, 0: 30, -1: 10}[ph]; z = {1: 40, 0: 50, -1: 70}[ph]
        if side == "L": R(f, "arm.L", 0, y, z)
        else: R(f, "arm.R", 0, -y, -z)
    arm("L", l); arm("R", r)
    R(f, "leg.L", x=-20); R(f, "leg.R", x=10)


def splash_loop():            # slap the water left/right, drops fly, giggling head bob
    global F_END; F = F_END = 48
    item_ref("pond")
    seq = [(1, 1, -1), (7, -1, 1), (13, 1, -1), (19, -1, 1), (25, 1, -1), (31, -1, 1), (37, 1, -1), (43, -1, 1), (49, 1, -1)]
    for i, (f, l, r) in enumerate(seq):
        water_pose(f, l, r, bob=0.012 if i % 2 else 0.0)
        R(f, "head", x=4, y=8 if i % 2 else -8, z=0)
        R(f, "body", y=4 if i % 2 else -4)
        S(f, "body", (1.03, 0.97, 1.03) if i % 2 else (0.98, 1.02, 0.98))
    for f in (1, 49): SHADOW(f, 0)
    ears([(1, 0), (4, 8), (10, -8), (16, 8), (22, -8), (28, 8), (34, -8), (40, 8), (46, -8), (49, 0)])
    eyes([(1, 1), (49, 1)])          # happy closed eyes while splashing
    wz = FLOORZ + 0.03
    for k, f in enumerate((7, 13, 19, 25, 31, 37, 43)):
        x = 0.3 if f in (7, 19, 31, 43) else -0.3      # slapped hand (L at screen-left = -x)
        x = -0.3 if (f - 1) // 6 % 2 == 1 else 0.3
        droplets((x, -0.12, wz), f, n=6, seed=10 + k, life=12)
    droplets((-0.3, -0.12, wz), 1, n=5, seed=40, life=10)
    return F


def splash_in():              # hop from the rim into the water (app moves the sprite enter -> stand during f4-f15)
    global F_END; F = F_END = 32
    item_ref("pond"); RP(1); rest(1); YAW(1, 0); SHADOW(1, 1)
    RP(4, 0, 0, -0.03); S(4, "body", (1.07, 0.92, 1.07)); arms(4, ly=-30, lz=10); YAW(4, 40)
    RP(10, 0, 0, 0.18); S(10, "body", (0.95, 1.07, 0.95)); arms(10, ly=70, lz=40); R(10, "leg.L", x=-35); R(10, "leg.R", x=-35)
    YAW(10, 30); SHADOW(4, 1); SHADOW(10, 0.6); SHADOW(15, 0)
    water_pose(15, 1, 1, bob=-0.05); S(15, "body", (1.08, 0.92, 1.08)); YAW(15, 0)
    water_pose(20, 0, 0, bob=0.02); S(20, "body", (0.97, 1.03, 0.97))
    water_pose(25, 0, 0); water_pose(F, 1, -1); S(F, "body", (0.98, 1.02, 0.98))
    for f in (25, F): R(f, "head", x=4, y=-8)
    ears([(1, 0), (10, -10), (15, 12), (20, -5), (26, 0)]); YAW(F, 0)
    eyes([(1, 0), (14, 0), (15, 1), (F, 1)])
    droplets((0, -0.05, FLOORZ + 0.03), 15, n=12, seed=3, spread=0.35, up=0.4, life=14, size=0.032)
    return F


def splash_out():             # hop back out to the rim (app moves the sprite stand -> enter during f8-f19)
    global F_END; F = F_END = 32
    item_ref("pond")
    water_pose(1, 1, -1); S(1, "body", (0.98, 1.02, 0.98)); R(1, "head", x=4, y=-8); YAW(1, 0); SHADOW(1, 0)
    water_pose(7, 0, 0, bob=-0.04); S(7, "body", (1.07, 0.92, 1.07)); YAW(7, -30); R(7, "head")
    RP(13, 0, 0, 0.18); S(13, "body", (0.95, 1.07, 0.95)); arms(13, ly=70, lz=40); R(13, "leg.L", x=-35); R(13, "leg.R", x=-35)
    YAW(13, -35); SHADOW(11, 0); SHADOW(14, 0.6)
    RP(19, 0, 0, -0.025); rest(19); S(19, "body", (1.07, 0.92, 1.07)); YAW(19, -15); SHADOW(19, 1)
    RP(23, 0, 0, 0.006); rest(23); YAW(24, 0)
    R(25, "body", y=8); R(27, "body", y=-8); R(29, "body", y=6); rest(F); RP(F); YAW(F, 0)     # little shake-off
    ears([(1, 0), (13, -10), (19, 12), (25, -10), (27, 10), (29, -6), (F, 0)])
    eyes([(1, 1), (6, 1), (7, 0), (F, 0)])
    droplets((0, -0.05, FLOORZ + 0.03), 9, n=7, seed=5, spread=0.2, up=0.25, life=10)
    droplets((0, -0.05, FLOORZ + 0.35), 25, n=8, seed=6, spread=0.35, up=0.12, life=8, size=0.02)
    return F


# ------------------------------------------------------------------ flower bed (냄새 맡기) — one-shot, idle -> idle
def sniff():
    global F_END; F = F_END = 72
    item_ref("flower_bed"); RP(1); rest(1); SHADOW(1, 1); SHADOW(F, 1)
    for f in (12, 34):
        R(f, "body", x=22); R(f, "head", x=20); arms(f, ly=-10, lz=-25); RP(f, 0, -0.02, -0.02)
        S(f, "body", (1.03, 0.97, 1.03))
    for i, f in enumerate((16, 20, 24, 28)):      # little sniffs: tiny inhale + head jiggle
        R(f, "head", x=20 + (4 if i % 2 else -2), y=(-3 if i % 2 else 3))
        S(f, "body", (1.0, 1.02, 1.0) if i % 2 else (1.03, 0.97, 1.03))
    R(42, "body", x=-6); R(42, "head", x=-14, y=8); S(42, "body", (0.96, 1.05, 0.96)); arms(42, ly=20, lz=20); RP(42, 0, 0, 0.01)
    R(50, "body", x=-4); R(50, "head", x=-12, y=-8); R(56, "head", x=-10, y=8)
    S(50, "body", (1.02, 0.98, 1.02)); arms(56, ly=10, lz=12)
    rest(64); RP(64); rest(F); RP(F)
    ears([(1, 0), (12, 4), (38, 4), (42, -12), (46, 10), (50, -8), (54, 6), (58, 0)])
    wag(40, 60, 18, 3)
    eyes([(1, 0), (15, 0), (16, 1), (52, 1), (53, 0), (F, 0)])
    heart(43, (0.12, -0.2, 0.72))
    return F


# ------------------------------------------------------------------ memory tree (열매 보여주기) — back view -> turns to the camera
def show_fruit():
    global F_END; F = F_END = 84
    item_ref("tree"); RP(1); rest(1); SHADOW(1, 1); SHADOW(F, 1)
    YAW(1, 180); YAW(8, 212)          # 3/4 back, turned toward the tree (back-left)
    R(8, "head", x=-16); R(8, "body", x=-3, y=4)
    # right arm (screen-left in the back view = toward the tree) points at the fruit (rig arms stop at ~shoulder height)
    R(14, "arm.R", 0, -92, -15); R(14, "head", x=-20, z=-8); R(14, "body", x=-4, y=9)   # stubby arms only reach shoulder height: lean into the point
    for i, f in enumerate((18, 22, 26, 30)):
        R(f, "arm.R", 0, -92 + (6 if i % 2 else -6), -15)
        RP(f, 0, 0, 0.012 if i % 2 else 0.0)
    R(32, "head", x=-6, z=-55)                          # look back over the shoulder at the user
    YAW(34, 212); R(34, "body", x=-4, y=9); YAW(44, 115); R(44, "body"); R(44, "head", x=-4, z=-30)
    R(44, "arm.R", 0, -90, -15)
    YAW(56, 0); R(56, "head", x=0, y=8, z=0); R(56, "arm.R", 0, -75, -25)
    RP(52, 0, 0, 0.05); RP(57, 0, 0, -0.015); S(57, "body", (1.05, 0.95, 1.05)); RP(60, 0, 0, 0.0)
    R(64, "arm.R", 0, -75, -25)
    rest(74); RP(74); rest(F); RP(F); YAW(F, 0)
    ears([(1, 0), (14, 5), (22, -5), (30, 5), (44, -8), (52, 10), (58, -6), (64, 0)])
    wag(14, 70, 18, 4)
    eyes([(1, 0), (46, 0), (47, 1), (62, 1), (63, 0), (F, 0)])
    return F


ACTIONS.update({
    "sit_bench_in": sit_bench_in, "sit_bench_loop": sit_bench_loop, "sit_bench_out": sit_bench_out,
    "sit_eat_in": sit_eat_in, "sit_eat_loop": sit_eat_loop, "sit_eat_strawberry": sit_eat_strawberry,
    "sit_eat_sweetpotato": sit_eat_sweetpotato, "sit_eat_out": sit_eat_out,
    "lie_in": lie_in, "lie_loop": lie_loop, "lie_out": lie_out,
    "splash_in": splash_in, "splash_loop": splash_loop, "splash_out": splash_out,
    "sniff": sniff, "show_fruit": show_fruit,
})


F = ACTIONS[ACTION]()
LOOP = ACTION.startswith("walk") or ACTION.endswith("_loop")
sc.frame_start, sc.frame_end = 1, F
for fc in fcurves(rig.animation_data.action):
    for kp in fc.keyframe_points:
        kp.interpolation = "BEZIER"; kp.easing = "AUTO"
    if LOOP:   # seamless loop: cyclic extrapolation so frame F+1 == frame 1
        fc.modifiers.new("CYCLES")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(rdir, f"hippo_{ACTION}.blend"))
print("SAVED", ACTION, F)
