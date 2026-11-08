# Usage: Blender -b -P clean_model.py -- in.glb out.glb
# TRELLIS.2 GLB cleanup: the mesh is split at UV seams, so smoothing it directly opens
# cracks. Merge duplicate vertices first (UVs live on loops, so they survive), then
# shade smooth + real smoothing, matte material, export.
import bpy, bmesh, sys

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
iters = int(argv[2]) if len(argv) > 2 else 12

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obj = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]

bm = bmesh.new(); bm.from_mesh(obj.data)
before = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
print("merged verts", before, "->", len(bm.verts))
bm.to_mesh(obj.data); bm.free()

for p in obj.data.polygons:
    p.use_smooth = True
m = obj.modifiers.new("smooth", "CORRECTIVE_SMOOTH")
m.use_only_smooth = True
m.iterations = iters
m.factor = 0.5
m.smooth_type = "LENGTH_WEIGHTED"
m.use_pin_boundary = True

mat = obj.data.materials[0]
bsdf = [n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"][0]
for k, v in (("Metallic", 0.0), ("Roughness", 0.85)):
    for l in list(bsdf.inputs[k].links):
        mat.node_tree.links.remove(l)
    bsdf.inputs[k].default_value = v

bpy.ops.export_scene.gltf(filepath=dst, export_apply=True)
print("EXPORTED", dst)
