# Usage: Blender -b -P rig_idle.py -- v4_dir out_dir
# Rig the confirmed hippo (v4) with a simple 12-bone armature (scripted region weights,
# robust on the TRELLIS mesh where bone-heat often fails), add an idle loop
# (breathing, head bob, ear flick, arm sway, tail wag, blink via decal swap),
# save .blend, export .glb, render a transparent PNG sequence.
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
v4, outdir = argv[0], argv[1]
render = (argv[2] if len(argv) > 2 else "1") == "1"
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(v4, "hippo_v3_open.blend"))
sc = bpy.context.scene
hippo = bpy.data.objects["Hippo"]
dec = bpy.data.objects["EyeDecal"]

# bake transforms to world space
for o in (dec, hippo):
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type == "EMPTY":
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
for o in (hippo, dec):
    o.select_set(True)
bpy.context.view_layer.objects.active = hippo
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for m in list(hippo.modifiers):
    bpy.ops.object.modifier_apply(modifier=m.name)

V = np.array([v.co[:] for v in hippo.data.vertices])
mn, mx = V.min(0), V.max(0)
print("bbox", mn.round(3), mx.round(3))

# ---------- armature ----------
B = {  # name: (head, tail, parent)
    "root":   ((0, 0, -0.50), (0, 0, -0.42), None),
    "body":   ((0, 0, -0.38), (0, 0, -0.05), "root"),
    "head":   ((0, 0, -0.05), (0, 0, 0.35), "body"),
    "ear.L":  ((-0.14, 0.05, 0.38), (-0.17, 0.06, 0.50), "head"),
    "ear.R":  ((0.14, 0.05, 0.38), (0.17, 0.06, 0.50), "head"),
    "arm.L":  ((-0.18, 0, -0.14), (-0.30, 0, -0.22), "body"),
    "arm.R":  ((0.18, 0, -0.14), (0.30, 0, -0.22), "body"),
    "leg.L":  ((-0.09, 0, -0.36), (-0.09, 0, -0.50), "root"),
    "leg.R":  ((0.09, 0, -0.36), (0.09, 0, -0.50), "root"),
    "tail":   ((0, 0.20, -0.30), (0, 0.29, -0.33), "body"),
}
arm_d = bpy.data.armatures.new("HippoRig")
rig = bpy.data.objects.new("HippoRig", arm_d); sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for n, (h, t, p) in B.items():
    eb = arm_d.edit_bones.new(n); eb.head, eb.tail = h, t
for n, (h, t, p) in B.items():
    if p:
        arm_d.edit_bones[n].parent = arm_d.edit_bones[p]
bpy.ops.object.mode_set(mode="OBJECT")

# ---------- region weights ----------
def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
x, y, z = V[:, 0], V[:, 1], V[:, 2]
w = {}
w["head"] = ss(-0.07, 0.04, z)
arm = ss(0.195, 0.225, np.abs(x)) * ss(-0.29, -0.26, z) * (1 - ss(-0.07, -0.03, z))
leg = (1 - ss(-0.40, -0.34, z)) * ss(0.015, 0.05, np.abs(x))
ear = ss(0.37, 0.41, z) * ss(0.08, 0.11, np.abs(x)) * w["head"]
tail = ss(0.19, 0.215, y) * ss(-0.40, -0.37, z) * (1 - ss(-0.21, -0.18, z)) * (1 - ss(0.09, 0.11, np.abs(x)))
L, R = x < 0, x >= 0
w["arm.L"], w["arm.R"] = arm * L, arm * R
w["leg.L"], w["leg.R"] = leg * L, leg * R
w["ear.L"], w["ear.R"] = ear * L, ear * R
w["tail"] = tail
w["head"] = w["head"] * (1 - ear)
for k in ("arm.L", "arm.R", "leg.L", "leg.R", "tail"):
    w["head"] = w["head"] * (1 - w[k])
w["body"] = np.clip(1 - sum(w[k] for k in w), 0, 1)
tot = sum(w.values())
for n in w:
    vg = hippo.vertex_groups.new(name=n)
    vals = w[n] / tot
    for i in np.nonzero(vals > 1e-3)[0]:
        vg.add([int(i)], float(vals[i]), "REPLACE")
print("weights: verts per bone", {n: int((w[n] / tot > 0.5).sum()) for n in w})
mod = hippo.modifiers.new("Armature", "ARMATURE"); mod.object = rig
hippo.parent = rig
# face decal follows the head bone
dec.parent = rig; dec.parent_type = "BONE"; dec.parent_bone = "head"
# set parent inverse properly: keep world position
bpy.context.view_layer.update()
pb = rig.pose.bones["head"]
from mathutils import Matrix
bone_world = rig.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.length, 0))
dec.matrix_parent_inverse = bone_world.inverted()

# ---------- blink: mix open/closed decal ----------
mat = dec.data.materials[0]; nt = mat.node_tree
tex_open = [n for n in nt.nodes if n.type == "TEX_IMAGE"][0]
tex_closed = nt.nodes.new("ShaderNodeTexImage")
tex_closed.image = bpy.data.images.load(os.path.join(v4, "decals", "eyes_closed.png")); tex_closed.image.pack()
tex_closed.extension = "CLIP"
for l in list(tex_open.outputs["Color"].links) + list(tex_open.outputs["Alpha"].links):
    nt.links.remove(l)
mixc = nt.nodes.new("ShaderNodeMix"); mixc.data_type = "RGBA"; mixc.name = "BlinkColor"
mixa = nt.nodes.new("ShaderNodeMix"); mixa.data_type = "FLOAT"; mixa.name = "BlinkAlpha"
bsdf = nt.nodes["Principled BSDF"]
nt.links.new(tex_open.outputs["Color"], mixc.inputs[6]); nt.links.new(tex_closed.outputs["Color"], mixc.inputs[7])
nt.links.new(tex_open.outputs["Alpha"], mixa.inputs[2]); nt.links.new(tex_closed.outputs["Alpha"], mixa.inputs[3])
nt.links.new(mixc.outputs[2], bsdf.inputs["Base Color"]); nt.links.new(mixa.outputs[0], bsdf.inputs["Alpha"])

# ---------- idle animation (48f @ 24fps, loops) ----------
F = 48
sc.frame_start, sc.frame_end = 1, F
sc.render.fps = 24
for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"

def key(bone, path, frames_vals):
    pb = rig.pose.bones[bone]
    for f, v in frames_vals:
        setattr(pb, path, v); pb.keyframe_insert(path, frame=f)

def wave(fn, n=9):
    return [(1 + i * F / (n - 1), fn(i / (n - 1))) for i in range(n)]

c = lambda t, a=1.0, ph=0.0: a * math.sin(2 * math.pi * (t + ph))
key("body", "scale", wave(lambda t: (1 - 0.012 * (1 - math.cos(2 * math.pi * t)) / 2,
                                     1 - 0.012 * (1 - math.cos(2 * math.pi * t)) / 2,
                                     1 + 0.03 * (1 - math.cos(2 * math.pi * t)) / 2)))
key("head", "rotation_euler", wave(lambda t: (math.radians(c(t, 2.0, 0.1)), 0, math.radians(c(t, 1.0, 0.3)))))
key("arm.L", "rotation_euler", wave(lambda t: (0, math.radians(c(t, 4.0)), 0)))
key("arm.R", "rotation_euler", wave(lambda t: (0, math.radians(c(t, -4.0)), 0)))
key("tail", "rotation_euler", wave(lambda t: (0, 0, math.radians(c(2 * t, 18.0))), 17))
# ear flick on the left ear around frame 18
key("ear.L", "rotation_euler", [(1, (0, 0, 0)), (16, (0, 0, 0)), (19, (0, math.radians(-14), 0)),
                                 (22, (0, math.radians(6), 0)), (25, (0, 0, 0)), (F, (0, 0, 0))])
key("ear.R", "rotation_euler", [(1, (0, 0, 0)), (F, (0, 0, 0))])
# blink frames 34-37
for node in (mixc, mixa):
    sock = node.inputs[0]
    for f, v in ((1, 0), (33, 0), (34, 1), (37, 1), (38, 0), (F, 0)):
        sock.default_value = v; sock.keyframe_insert("default_value", frame=f)
if mat.node_tree.animation_data and mat.node_tree.animation_data.action:
    act = mat.node_tree.animation_data.action
    for fc in getattr(act, "fcurves", []):
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"
    except Exception:
        pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, "hippo_rig_idle.blend"))
try:
    bpy.ops.export_scene.gltf(filepath=os.path.join(outdir, "hippo_rig_idle.glb"), export_animations=True)
except Exception as e:
    print("GLB export failed", e)
print("SAVED rig")

if not render:
    sys.exit(0)
# ---------- render ----------
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except Exception: pass
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 600, 800
sc.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
def light(name, rot, energy):
    d = bpy.data.lights.new(name, "SUN"); d.energy = energy
    ob = bpy.data.objects.new(name, d); sc.collection.objects.link(ob)
    ob.rotation_euler = [math.radians(a) for a in rot]
light("key", (50, 0, 30), 3.0); light("fill", (60, 0, -120), 1.2)
light("rim", (110, 0, 180), 2.0); light("bounce", (150, 0, 0), 0.7)
cam_d = bpy.data.cameras.new("cam"); cam_d.type = "ORTHO"; cam_d.ortho_scale = 1.45   # same framing for every action (jump headroom)
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
target = Vector((0, 0, 0.07))
cam.location = target + Vector((0.35, -1, 0.12)).normalized() * 10
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = os.path.join(outdir, "idle_frames", "f_")
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(animation=True)
print("RENDERED")
