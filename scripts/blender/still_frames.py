# Blender -b action.blend -P still_frames.py -- out_prefix f1,f2,...  (same camera/light as the action renders)
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
pre, frames = a[0], [int(x) for x in a[1].split(",")]
s = bpy.context.scene
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: s.render.engine = e; break
    except Exception: pass
s.render.film_transparent = True; s.view_settings.view_transform = "Standard"; s.view_settings.look = "None"
s.render.resolution_x, s.render.resolution_y = 600, 800
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for n, rot, en in (("k", (50, 0, 30), 3), ("f", (60, 0, -120), 1.2), ("r", (110, 0, 180), 2), ("b", (150, 0, 0), 0.7)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = en
    o = bpy.data.objects.new(n, d); s.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 1.45
c = bpy.data.objects.new("c", cd); s.collection.objects.link(c); s.camera = c
import os
t = Vector((0, 0, 0.07)); c.location = t + Vector((0.35, -1, float(os.environ.get("CAM_ELEV", "0.12")))).normalized() * 10
c.rotation_euler = (t - c.location).to_track_quat("-Z", "Y").to_euler()
for f in frames:
    s.frame_set(f); s.render.filepath = f"{pre}_{f}.png"; bpy.ops.render.render(write_still=True)
