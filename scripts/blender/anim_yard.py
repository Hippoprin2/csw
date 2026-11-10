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
C = 16          # 0.67 s per cycle, 3 steps/s: short-legged waddle
CYCLES = 3      # loop length 48 f (2 s); one blink per loop


def walk(yaw, blink=True):
    F = C * CYCLES
    for k in range(CYCLES + 1):
        b = 1 + k * C
        for ph, side in ((0, 1), (C // 2, -1)):          # contact: side=1 -> left leg forward
            f = b + ph
            if f > F + 1: continue
            R(f, "leg.L", x=-30 * side); R(f, "leg.R", x=30 * side)
            # opposite arm swings forward (arms first lowered toward the body, then swing on X)
            R(f, "arm.L", 24 * side, -18, 0, "YXZ"); R(f, "arm.R", -24 * side, 18, 0, "YXZ")
            L(f, "root", 0.0); S(f, "body", (1.035, 0.965, 1.035))
            R(f, "body", 2, 4 * side, -5 * side)          # lean onto the front foot side + small twist
            R(f, "head", 3, -2.5 * side, 3 * side)        # head counters the body a little
            fp = f + C // 4                                 # passing: legs under the body, up, stretched
            if fp <= F + 1:
                R(fp, "leg.L"); R(fp, "leg.R")
                R(fp, "arm.L", 0, -18, 0, "YXZ"); R(fp, "arm.R", 0, 18, 0, "YXZ")
                L(fp, "root", 0.032); S(fp, "body", (0.975, 1.03, 0.975))
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
F = ACTIONS[ACTION]()
LOOP = ACTION.startswith("walk")
sc.frame_start, sc.frame_end = 1, F
for fc in fcurves(rig.animation_data.action):
    for kp in fc.keyframe_points:
        kp.interpolation = "BEZIER"; kp.easing = "AUTO"
    if LOOP:   # seamless loop: cyclic extrapolation so frame F+1 == frame 1
        fc.modifiers.new("CYCLES")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(rdir, f"hippo_{ACTION}.blend"))
print("SAVED", ACTION, F)
