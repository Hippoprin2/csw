# Blender -b rig.blend -P pose_test.py -- out.png "bone:rx,ry,rz;bone:..."
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
out, spec = a[0], a[1]
sc = bpy.context.scene
rig = bpy.data.objects["HippoRig"]
if rig.animation_data: rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, 0)
for item in spec.split(";"):
    if not item: continue
    b, r = item.split(":")
    pb = rig.pose.bones[b]
    if r.startswith("w"):   # world-space euler (deg) -> bone-local quaternion
        from mathutils import Euler
        Bm = pb.bone.matrix_local.to_3x3()
        Rw = Euler([math.radians(float(v)) for v in r[1:].split(",")]).to_matrix()
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (Bm.inverted() @ Rw @ Bm).to_quaternion()
    else:
        pb.rotation_euler = [math.radians(float(v)) for v in r.split(",")]
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except Exception: pass
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 400, 500
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for n, rot, e in (("key", (50, 0, 30), 3), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = e
    o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 1.4
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = Vector((0, -10, 0.05))
cam.rotation_euler = (Vector((0, 0, 0.05)) - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
