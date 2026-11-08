# Stress-test the rig weights: exaggerated pose, render one still. Blender -b file.blend -P stress_pose.py -- out.png
import bpy, sys, math
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene
rig = bpy.data.objects["HippoRig"]
if rig.animation_data: rig.animation_data.action = None
P = rig.pose.bones
for pb in P: pb.rotation_mode = "XYZ"
P["head"].rotation_euler = (math.radians(15), 0, math.radians(20))
P["arm.L"].rotation_euler = (0, math.radians(35), 0)
P["arm.R"].rotation_euler = (math.radians(30), 0, 0)
P["leg.L"].rotation_euler = (math.radians(25), 0, 0)
P["ear.L"].rotation_euler = (0, math.radians(-30), 0)
P["tail"].rotation_euler = (0, 0, math.radians(40))
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except Exception: pass
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 600, 800
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for n, rot, e in (("key", (50, 0, 30), 3), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = e
    o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.rotation_euler = [math.radians(a) for a in rot]
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 1.25
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = Vector((0.6, -1, 0.15)).normalized() * 10
cam.rotation_euler = (-cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
