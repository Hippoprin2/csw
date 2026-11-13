# Render a full-screen milestone celebration scene (portrait) with the shared ART_BIBLE look, transparent bg.
# Usage: Blender -b hippo_milestone10.blend -P render_milestone.py -- out_dir [W=1080] [H=1920] [frames=1,40,...]
# Also writes out_dir/track.json: per frame snout/head/centre pixel positions (for the 2D bubble overlay).
import bpy, sys, os, math, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]
kv = dict(x.split("=", 1) for x in a[1:] if "=" in x)
W, H = int(kv.get("W", 1080)), int(kv.get("H", 1920))
s = bpy.context.scene
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: s.render.engine = e; break
    except Exception: pass
s.render.film_transparent = True
s.view_settings.view_transform = "Standard"; s.view_settings.look = "None"
s.render.resolution_x, s.render.resolution_y = W, H
s.render.fps = 24
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA")]:
    bpy.data.objects.remove(o, do_unlink=True)
for n, rot, en in (("key", (50, 0, 30), 3.0), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2.0), ("bounce", (150, 0, 0), 0.7)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = en
    o = bpy.data.objects.new(n, d); s.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import surface; surface.apply(s)          # 단짝 표면 v2 (2026-11-13); HIPPO_SURFACE=0 = old look
cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = float(kv.get("scale", 2.6))
c = bpy.data.objects.new("cam", cd); s.collection.objects.link(c); s.camera = c
t = Vector((0, 0, float(kv.get("tz", 0.12))))
c.location = t + Vector((0.35, -1, 0.12)).normalized() * 10
c.rotation_euler = (t - c.location).to_track_quat("-Z", "Y").to_euler()

rig = bpy.data.objects["HippoRig"]; sn = bpy.data.objects.get("SnoutPt")
track = {}
for f in range(s.frame_start, s.frame_end + 1):
    s.frame_set(f)
    def px(p):
        v = world_to_camera_view(s, c, p); return [round(v.x * W, 1), round((1 - v.y) * H, 1), round(v.z, 3)]
    head = rig.matrix_world @ rig.pose.bones["head"].head
    root = rig.matrix_world @ rig.pose.bones["root"].head
    snp = sn.matrix_world.translation if sn else head
    # snout faces the camera when it is closer to the camera than the head centre
    cam_dir = (c.location - t).normalized()
    facing = (snp - head).normalized().dot(cam_dir)
    track[f] = {"snout": px(snp), "head": px(head), "root": px(root), "facing": round(facing, 3)}
os.makedirs(out, exist_ok=True)
json.dump(track, open(os.path.join(out, "track.json"), "w"))
s.render.image_settings.file_format = "PNG"
if "frames" in kv:
    for f in [int(v) for v in kv["frames"].split(",")]:
        s.frame_set(f); s.render.filepath = os.path.join(out, f"f_{f:04d}.png"); bpy.ops.render.render(write_still=True)
else:
    s.render.filepath = os.path.join(out, "f_")
    bpy.ops.render.render(animation=True)
print("RENDERED", out, s.frame_start, s.frame_end)
