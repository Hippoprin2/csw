# Usage: Blender -b -P anim_cheer.py -- rig_dir [render=1]
# "만세 + 점프" (other wins): anticipation squat -> jump with arms up, happy closed eyes
# -> squash landing -> arms wiggle -> settle back to the idle rest pose. 40f @24fps.
import bpy, sys, os, math
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:]
rdir = argv[0]
render = (argv[1] if len(argv) > 1 else "1") == "1"
bpy.ops.wm.open_mainfile(filepath=os.path.join(rdir, "hippo_rig_idle.blend"))
sc = bpy.context.scene
rig = bpy.data.objects["HippoRig"]
P = rig.pose.bones
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions.new("cheer_jump")
for pb in P:
    pb.rotation_mode = "QUATERNION"
    pb.location = (0, 0, 0); pb.scale = (1, 1, 1); pb.rotation_quaternion = (1, 0, 0, 0)

F = 40
sc.frame_start, sc.frame_end = 1, F

def wq(bone, x=0, y=0, z=0):
    """world-space euler (deg) -> bone-local quaternion"""
    Bm = P[bone].bone.matrix_local.to_3x3()
    Rw = Euler((math.radians(x), math.radians(y), math.radians(z))).to_matrix()
    return (Bm.inverted() @ Rw @ Bm).to_quaternion()

def K(f, bone, rot=None, loc=None, scale=None):
    pb = P[bone]
    if rot is not None:
        pb.rotation_quaternion = rot; pb.keyframe_insert("rotation_quaternion", frame=f)
    if loc is not None:
        pb.location = loc; pb.keyframe_insert("location", frame=f)
    if scale is not None:
        pb.scale = scale; pb.keyframe_insert("scale", frame=f)

UP = 78    # arms raised up-and-out (deg around world Y); rest pose is ~35 deg below horizontal
STRETCH = 1.4   # cartoon arm stretch along the bone while cheering
# root: local Y == world up
for f, h in ((1, 0), (5, -0.035), (8, 0.0), (12, 0.14), (14, 0.15), (18, 0.0), (21, -0.02), (24, 0.0), (F, 0)):
    K(f, "root", loc=(0, h, 0))
# body squash & stretch (local Y == world up)
for f, s in ((1, (1, 1, 1)), (5, (1.06, 0.9, 1.06)), (8, (0.95, 1.08, 0.95)), (13, (1, 1, 1)),
             (18, (1.08, 0.88, 1.08)), (21, (0.97, 1.04, 0.97)), (25, (1, 1, 1)), (F, (1, 1, 1))):
    K(f, "body", scale=s)
# arms
for f, a in ((1, 0), (5, -12), (9, UP), (14, UP + 8), (18, UP - 6), (22, UP + 6), (26, UP - 8),
             (30, UP + 6), (34, UP - 4), (F, 0)):
    K(f, "arm.L", rot=wq("arm.L", y=a)); K(f, "arm.R", rot=wq("arm.R", y=-a))
for f, s in ((1, 1), (6, 1), (9, STRETCH), (34, STRETCH), (F, 1)):
    for b in ("arm.L", "arm.R"):
        K(f, b, scale=(1 + (s - 1) * 0.3, s, 1 + (s - 1) * 0.3))
# legs tuck in the air
for f, a in ((1, 0), (8, 0), (12, -18), (16, -10), (18, 0), (F, 0)):
    K(f, "leg.L", rot=wq("leg.L", x=a)); K(f, "leg.R", rot=wq("leg.R", x=a))
# head: dip on squat, look up at the top, nod on landing
for f, a in ((1, 0), (5, 6), (10, -8), (14, -10), (18, 6), (22, -3), (26, 0), (F, 0)):
    K(f, "head", rot=wq("head", x=a))
# ears lag (overlap): flop down when rising, up when falling
for f, a in ((1, 0), (8, 8), (12, -18), (16, 16), (19, 20), (23, -8), (27, 4), (31, 0), (F, 0)):
    K(f, "ear.L", rot=wq("ear.L", y=-a)); K(f, "ear.R", rot=wq("ear.R", y=a))
# tail wag fast
for i, f in enumerate(range(1, F + 1, 3)):
    K(f, "tail", rot=wq("tail", z=(0 if f in (1,) or f > 34 else (22 if i % 2 else -22))))
K(F, "tail", rot=wq("tail"))

# happy closed eyes from take-off to after landing
dec = bpy.data.objects["EyeDecal"]; nt = dec.data.materials[0].node_tree
if nt.animation_data:
    nt.animation_data.action = None
for name in ("BlinkColor", "BlinkAlpha"):
    sock = nt.nodes[name].inputs[0]
    for f, v in ((1, 0), (8, 0), (9, 1), (27, 1), (28, 0), (F, 0)):
        sock.default_value = v; sock.keyframe_insert("default_value", frame=f)
act = nt.animation_data.action
def fcurves(a):
    out = list(getattr(a, "fcurves", []) or [])
    try:
        for layer in a.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out += list(cb.fcurves)
    except Exception:
        pass
    return out
for fc in fcurves(act):
    for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"
# snappier body motion
for fc in fcurves(rig.animation_data.action):
    for kp in fc.keyframe_points:
        kp.interpolation = "BEZIER"; kp.easing = "AUTO"

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(rdir, "hippo_cheer_jump.blend"))
print("SAVED cheer")
if not render:
    sys.exit(0)
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except Exception: pass
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 600, 800
cam = sc.camera
if cam is None or cam.type != "CAMERA":
    cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    for n, rot, e in (("key", (50, 0, 30), 3), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2), ("bounce", (150, 0, 0), 0.7)):
        d = bpy.data.lights.new(n, "SUN"); d.energy = e
        o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
cam.data.ortho_scale = 1.45
target = Vector((0, 0, 0.07))
cam.location = target + Vector((0.35, -1, 0.12)).normalized() * 10
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = os.path.join(rdir, "cheer_frames", "f_")
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(animation=True)
print("RENDERED")
