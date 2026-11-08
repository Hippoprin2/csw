# Usage: Blender -b -P anim_actions.py -- rig_dir action [render=1]
# Shared celebration actions for the hippo rig (bone names: root, body, head, ear.L/R,
# arm.L/R, leg.L/R, tail). Every action starts/ends at the idle rest pose.
# Rotations are given in WORLD axes (deg) and converted per bone, so they do not depend on
# bone roll. World axes: X = character's left->right (screen), Y = back (camera at -Y), Z = up.
#   arm.L: +y raises, +z swings forward.   arm.R: -y raises, -z swings forward.
import bpy, sys, os, math
from mathutils import Vector, Euler

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

def wq(bone, x=0, y=0, z=0):
    Bm = P[bone].bone.matrix_local.to_3x3()
    Rw = Euler((math.radians(x), math.radians(y), math.radians(z))).to_matrix()
    return (Bm.inverted() @ Rw @ Bm).to_quaternion()

def R(f, bone, x=0, y=0, z=0):
    P[bone].rotation_quaternion = wq(bone, x, y, z); P[bone].keyframe_insert("rotation_quaternion", frame=f)

def L(f, bone, up=0.0):  # root/body local Y == world up
    P[bone].location = (0, up, 0); P[bone].keyframe_insert("location", frame=f)

def S(f, bone, s):
    P[bone].scale = s; P[bone].keyframe_insert("scale", frame=f)

def arms(f, ly=0, lz=0, ry=None, rz=None, lx=0, rx=None):
    """symmetric by default: right arm mirrors left"""
    ry = -ly if ry is None else ry; rz = -lz if rz is None else rz; rx = lx if rx is None else rx
    R(f, "arm.L", lx, ly, lz); R(f, "arm.R", rx, ry, rz)

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
        S(f, "arm.L", (1.08, 1.3, 1.08)); S(f, "arm.R", (1.08, 1.3, 1.08))
        R(f, "body", 0, 10 * s, 14 * s)    # lean + twist toward the side
        R(f, "head", 0, -6 * s, 10 * s)
        S(f, "body", (1.03, 0.97, 1.03)); L(f, "root", 0.0)
        L(f + 3, "root", 0.015)            # little bounce between strokes
    rest(44); rest(F)
    eyes([(1, 0), (F, 0)]); wag(4, 40, 14, 4); return F

def hop():  # 몸 움직이기: two energetic hops with arm swings
    F = 40; rest(1)
    for base in (1, 19):
        S(base + 3, "body", (1.06, 0.9, 1.06)); L(base + 3, "root", -0.03); arms(base + 3, ly=-10, lz=-20)
        S(base + 6, "body", (0.95, 1.08, 0.95)); L(base + 6, "root", 0.0)
        L(base + 9, "root", 0.10); S(base + 9, "body", (1, 1, 1)); arms(base + 9, ly=40, lz=30)
        R(base + 9, "leg.L", x=-12); R(base + 9, "leg.R", x=-12)
        L(base + 13, "root", 0.0); S(base + 13, "body", (1.07, 0.9, 1.07)); arms(base + 13, ly=10, lz=0)
        R(base + 13, "leg.L"); R(base + 13, "leg.R")
        S(base + 16, "body", (1, 1, 1))
    ears_bounce([(1, 0), (8, -12), (12, 14), (16, 0), (26, -12), (30, 14), (34, 0)])
    rest(F); eyes([(1, 0), (8, 1), (34, 1), (35, 0), (F, 0)]); wag(4, 36, 20, 3); return F

def nod():  # 공부·일: content nods, small body bob, a slow blink at the end
    F = 44; rest(1)
    for f, a in ((6, 20), (11, -4), (16, 20), (21, -4), (26, 16), (31, 0)):
        R(f, "head", x=a); S(f, "body", (1.0, 0.985 if a > 5 else 1.0, 1.0))
    arms(8, ly=-6, lz=18); arms(30, ly=-6, lz=18)
    ears_bounce([(1, 0), (8, 6), (13, -4), (18, 6), (23, -4), (28, 5), (33, 0)])
    rest(38); rest(F); eyes([(1, 0), (33, 0), (34, 1), (39, 1), (40, 0), (F, 0)]); wag(4, 36, 10, 6); return F

def eat():  # 잘 먹기: both hands to mouth (onigiri later), chew bobs, happy eyes
    F = 52; rest(1)
    arms(7, ly=55, lz=80); arms(44, ly=55, lz=80)
    for f in (7, 44):
        S(f, "arm.L", (1.1, 1.5, 1.1)); S(f, "arm.R", (1.1, 1.5, 1.1))
    R(7, "head", x=6)
    for i, f in enumerate(range(10, 42, 4)):
        R(f, "head", x=12 if i % 2 else 2)
        S(f, "body", (1.02, 0.98, 1.02) if i % 2 else (1, 1, 1))
        L(f, "root", 0.012 if i % 2 else 0.0)
    ears_bounce([(1, 0), (12, 6), (20, -4), (28, 6), (36, -4), (44, 0)])
    rest(F); eyes([(1, 0), (9, 1), (42, 1), (43, 0), (F, 0)]); wag(6, 46, 16, 4); return F

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
    rest(52, others); rest(F, others); eyes([(1, 0), (8, 1), (24, 1), (25, 0), (F, 0)]); wag(26, 50, 20, 3); return F

def wave():  # 사람·마음: raise the right arm and wave, head tilt
    F = 52; rest(1)
    R(8, "arm.R", 0, -95, -10); S(8, "arm.R", (1.1, 1.35, 1.1)); R(8, "head", 0, 8, 0)
    for i, f in enumerate(range(12, 40, 5)):
        R(f, "arm.R", 0, -95 + (18 if i % 2 else -10), -10)
    R(40, "arm.R", 0, -95, -10); S(42, "arm.R", (1.1, 1.35, 1.1))
    R(8, "arm.L", 0, 0, 10); R(40, "arm.L", 0, 0, 10)
    R(24, "head", 0, 10, 4); R(40, "head", 0, 8, 0)
    ears_bounce([(1, 0), (12, 5), (22, -5), (32, 5), (42, 0)])
    rest(48); rest(F); eyes([(1, 0), (20, 0), (21, 1), (24, 1), (25, 0), (F, 0)]); wag(6, 44, 18, 4); return F

ACTIONS = {"sweep": sweep, "hop": hop, "nod": nod, "eat": eat, "stretch_spin": stretch_spin, "wave": wave}
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
