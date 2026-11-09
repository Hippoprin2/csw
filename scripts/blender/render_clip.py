# Render an existing action .blend from a different camera elevation (ART_BIBLE lights/camera).
# Usage: Blender -b action.blend -P render_clip.py -- out_dir elev
# 0.12 = room/default (6.5 deg), 0.5 = garden/yard (25 deg, WORLD.md W2).
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
out, elev = a[0], float(a[1])
s = bpy.context.scene
# from a higher camera the confetti burst (origin in front of the face) lands on the snout -> lift it
if elev >= 0.4:
    for o in bpy.data.objects:
        if o.name.startswith("Confetti") and o.animation_data and o.animation_data.action:
            act = o.animation_data.action
            fcs = list(getattr(act, "fcurves", []) or [])
            try:
                for layer in act.layers:
                    for strip in layer.strips:
                        for cb in strip.channelbags: fcs += list(cb.fcurves)
            except Exception:
                pass
            for fc in fcs:
                if fc.data_path == "location" and fc.array_index in (1, 2):
                    d = 0.14 if fc.array_index == 1 else 0.16
                    for kp in fc.keyframe_points:
                        kp.co.y += d; kp.handle_left.y += d; kp.handle_right.y += d
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: s.render.engine = e; break
    except Exception: pass
s.render.film_transparent = True
s.view_settings.view_transform = "Standard"; s.view_settings.look = "None"
s.render.resolution_x, s.render.resolution_y = 600, 800
s.render.fps = 24
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA")]:
    bpy.data.objects.remove(o, do_unlink=True)
for n, rot, en in (("key", (50, 0, 30), 3.0), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2.0), ("bounce", (150, 0, 0), 0.7)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = en
    o = bpy.data.objects.new(n, d); s.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = 1.45
c = bpy.data.objects.new("cam", cd); s.collection.objects.link(c); s.camera = c
t = Vector((0, 0, 0.07)); c.location = t + Vector((0.35, -1, elev)).normalized() * 10
c.rotation_euler = (t - c.location).to_track_quat("-Z", "Y").to_euler()
os.makedirs(out, exist_ok=True)
s.render.filepath = os.path.join(out, "f_"); s.render.image_settings.file_format = "PNG"
bpy.ops.render.render(animation=True)
print("RENDERED", out, s.frame_start, s.frame_end)
