# Usage: Blender -b -P build_hippo_v3.py -- v2.blend decal_dir out_dir [state=open|closed]
# Replaces the 3D eye parts of v2 with a flat painted-eye decal (matches concept art):
# a thin shell copied from the visible face surface, UV = front orthographic projection
# into the decal canvas (same framing as render_turnaround.py). Blink = swap decal image.
import bpy, bmesh, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
blend, decals, outdir = argv[0], argv[1], argv[2]
state = argv[3] if len(argv) > 3 else "open"
os.makedirs(outdir, exist_ok=True)
import os as _os
X0, Y0, X1, Y1 = (200, 110, 570, 420) if _os.environ.get('DECAL_V4') else (200, 170, 570, 360)
OFFSET = 0.0012

bpy.ops.wm.open_mainfile(filepath=blend)
for o in list(bpy.data.objects):
    if o.name.startswith(("Eye", "Lid")):
        bpy.data.objects.remove(o, do_unlink=True)
hippo = bpy.data.objects["Hippo"]
mw = hippo.matrix_world
deps = bpy.context.evaluated_depsgraph_get()
ev = hippo.evaluated_get(deps)
me = ev.to_mesh()

verts = [mw @ v.co for v in me.vertices]
xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
ctr = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
size = Vector((max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)))
S = max(size.z, size.x * 1024 / 768, size.y * 1024 / 768) * 1.1

def to_px(p):
    return (384 + (p.x - ctr.x) * 1024 / S, 512 - (p.z - ctr.z) * 1024 / S)

# visible front faces inside the canvas window
bvh_obj = ev
keep = []
mwi = mw.inverted()
for poly in me.polygons:
    c = mw @ poly.center
    px, py = to_px(c)
    if not (X0 - 4 < px < X1 + 4 and Y0 - 4 < py < Y1 + 4):
        continue
    n = (mw.to_3x3() @ poly.normal).normalized()
    if n.y > -0.05:
        continue
    o = mwi @ Vector((c.x, ctr.y - 5, c.z))
    hit, loc, nor, fi = ev.ray_cast(o, (mwi.to_3x3() @ Vector((0, 1, 0))).normalized())
    if hit and ((mw @ loc) - c).length < 0.004:
        keep.append(poly.index)
print("decal faces", len(keep))

bm = bmesh.new()
vmap = {}
uvl = bm.loops.layers.uv.new("UVMap")
for fi in keep:
    poly = me.polygons[fi]
    bv = []
    for vi in poly.vertices:
        if vi not in vmap:
            v = me.vertices[vi]
            p = mw @ (v.co + v.normal * OFFSET)
            vmap[vi] = bm.verts.new(p)
        bv.append(vmap[vi])
    try:
        f = bm.faces.new(bv)
    except ValueError:
        continue
    f.smooth = True
    for loop in f.loops:
        px, py = to_px(loop.vert.co)
        loop[uvl].uv = ((px - X0) / (X1 - X0), 1 - (py - Y0) / (Y1 - Y0))
dm = bpy.data.meshes.new("EyeDecal"); bm.to_mesh(dm); bm.free()
ev.to_mesh_clear()
dec = bpy.data.objects.new("EyeDecal", dm); bpy.context.scene.collection.objects.link(dec)
dec.parent = hippo; dec.matrix_parent_inverse = mw.inverted()

mat = bpy.data.materials.new("EyeDecal"); mat.use_nodes = True
nt = mat.node_tree; b = nt.nodes["Principled BSDF"]
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(os.path.join(decals, f"eyes_{state}.png")); tex.image.pack()
tex.extension = "CLIP"
nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
b.inputs["Roughness"].default_value = 0.85
for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
    if hasattr(mat, attr):
        try: setattr(mat, attr, val)
        except Exception: pass
dm.materials.append(mat)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, f"hippo_v3_{state}.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(outdir, f"hippo_v3_{state}.glb"), export_apply=True)
print("SAVED", state)
