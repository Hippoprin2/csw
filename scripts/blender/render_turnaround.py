# Usage: Blender -b -P render_turnaround.py -- in.glb out_prefix [smooth=1] [sheen=1]
import bpy, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = argv[0], argv[1]
smooth = (argv[2] if len(argv) > 2 else "1") == "1"
sheen = (argv[3] if len(argv) > 3 else "1") == "1"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in meshes:
    print("MESH", o.name, "verts", len(o.data.vertices), "faces", len(o.data.polygons),
          "mats", [m.name for m in o.data.materials if m])

# bounding box
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr, size = (mn + mx) / 2, mx - mn
print("BBOX size", tuple(round(v, 3) for v in size))

for o in meshes:
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
        m = o.modifiers.new("smooth", "CORRECTIVE_SMOOTH")
        m.iterations = 8
        m.factor = 0.5
        m.use_only_smooth = True
    for mat in o.data.materials:
        if not mat or not mat.use_nodes or mat.name.startswith("Eye_"):
            continue
        for n in mat.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                n.inputs["Roughness"].default_value = 0.85
                if "Metallic" in n.inputs:
                    for l in list(n.inputs["Metallic"].links):
                        mat.node_tree.links.remove(l)
                    n.inputs["Metallic"].default_value = 0.0
                if sheen:
                    for k, v in (("Sheen Weight", 0.6), ("Sheen Roughness", 0.4)):
                        if k in n.inputs:
                            n.inputs[k].default_value = v

sc = bpy.context.scene
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = eng
        break
    except Exception:
        pass
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 768, 1024
sc.view_settings.view_transform = "Standard"

world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.9

def light(name, rot, energy):
    d = bpy.data.lights.new(name, "SUN"); d.energy = energy
    ob = bpy.data.objects.new(name, d); sc.collection.objects.link(ob)
    ob.rotation_euler = [math.radians(a) for a in rot]
light("key", (50, 0, 30), 3.0)
light("fill", (60, 0, -120), 1.2)
light("rim", (110, 0, 180), 2.0)
light("bounce", (150, 0, 0), 0.7)   # from front-below: softens chin/belly shadow

cam_d = bpy.data.cameras.new("cam"); cam_d.type = "ORTHO"
cam_d.ortho_scale = max(size.z, size.x * 1024 / 768, size.y * 1024 / 768) * 1.1
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam

# glTF is Y-up -> Blender Z-up; character front faces -Y after import
dist = 10 * max(size)
views = {"front": (0, -1), "side": (1, 0), "back": (0, 1), "threequarter": (0.7, -0.7)}
for name, (dx, dy) in views.items():
    cam.location = ctr + Vector((dx, dy, 0)).normalized() * dist
    direction = ctr - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("WROTE", sc.render.filepath)
