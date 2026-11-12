# Surface look comparison stills for the hippo (대표 2026-11-12: current vs smoother surface vs fur).
# Usage: Blender -b hippo_rig_idle.blend -P texture_compare.py -- out.png <variant: current|smooth|fur> [frame=1] [res=2]
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
out, var = a[0], a[1]
kv = dict(x.split("=", 1) for x in a[2:] if "=" in x)
s = bpy.context.scene
s.frame_set(int(kv.get("frame", 1)))
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: s.render.engine = e; break
    except Exception: pass
s.render.film_transparent = True
s.view_settings.view_transform = "Standard"; s.view_settings.look = "None"
r = float(kv.get("res", 2))
s.render.resolution_x, s.render.resolution_y = int(600 * r), int(800 * r)
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA") or o.name == "FloorShadow"]:
    bpy.data.objects.remove(o, do_unlink=True)
lights = []
for n, rot, en in (("key", (50, 0, 30), 3.0), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2.0), ("bounce", (150, 0, 0), 0.7)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = en
    o = bpy.data.objects.new(n, d); s.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
    lights.append(d)
cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = 1.45
c = bpy.data.objects.new("cam", cd); s.collection.objects.link(c); s.camera = c
t = Vector((0, 0, 0.07))
c.location = t + Vector((0.35, -1, 0.12)).normalized() * 10
c.rotation_euler = (t - c.location).to_track_quat("-Z", "Y").to_euler()

h = bpy.data.objects["Hippo"]
mat = h.data.materials[0]; nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")

def soft_light():
    """warmer, softer key + soft sun shadows + ambient occlusion -> contact shading under arms/chin"""
    for d in lights:
        if hasattr(d, "angle"): d.angle = math.radians(18 if d.name == "key" else 30)
    lights[0].color = (1.0, 0.97, 0.93)
    ee = s.eevee
    for k, v in (("use_gtao", True), ("gtao_distance", 0.12), ("use_soft_shadows", True), ("taa_render_samples", 64)):
        if hasattr(ee, k):
            try: setattr(ee, k, v)
            except Exception: pass

def smooth_surface():
    """remove the mosaic: iron ripples of the AI-scanned mesh + replace the blotchy baked-shading texture with the flat body colour
    (only eyes/brows/nostrils/inner-ear pink keep the texture)"""
    import bmesh                                                  # the scan is split at UV seams -> weld first, or smoothing cracks it open
    bm = bmesh.new(); bm.from_mesh(h.data); n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(h.data); print("welded", n0 - len(bm.verts)); bm.free()
    sm = h.modifiers.new("SurfSmooth", "CORRECTIVE_SMOOTH")       # after the armature: keeps shape, irons ripples
    sm.factor = 1.0; sm.iterations = 25; sm.smooth_type = "LENGTH_WEIGHTED"; sm.use_only_smooth = True
    sm.rest_source = "ORCO"
    body = (0.891, 0.632, 0.389, 1)   # #F2CFA6 linear (= texture median)
    L = nt.links.new
    dif = nt.nodes.new("ShaderNodeMix"); dif.data_type = "RGBA"; dif.blend_type = "DIFFERENCE"; dif.inputs[0].default_value = 1
    L(tex.outputs["Color"], dif.inputs[6]); dif.inputs[7].default_value = body
    bw = nt.nodes.new("ShaderNodeRGBToBW"); L(dif.outputs[2], bw.inputs[0])
    r1 = nt.nodes.new("ShaderNodeMapRange"); L(bw.outputs[0], r1.inputs[0]); r1.inputs[1].default_value = 0.3; r1.inputs[2].default_value = 0.4
    sep = nt.nodes.new("ShaderNodeSeparateColor"); L(tex.outputs["Color"], sep.inputs[0])
    rg = nt.nodes.new("ShaderNodeMath"); rg.operation = "SUBTRACT"; L(sep.outputs[0], rg.inputs[0]); L(sep.outputs[1], rg.inputs[1])
    r2 = nt.nodes.new("ShaderNodeMapRange"); L(rg.outputs[0], r2.inputs[0]); r2.inputs[1].default_value = 0.4; r2.inputs[2].default_value = 0.48
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; L(r1.outputs[0], mx.inputs[0]); L(r2.outputs[0], mx.inputs[1])
    flat = nt.nodes.new("ShaderNodeMix"); flat.data_type = "RGBA"; flat.blend_type = "MIX"
    L(mx.outputs[0], flat.inputs[0]); flat.inputs[6].default_value = body; L(tex.outputs["Color"], flat.inputs[7])
    L(flat.outputs[2], bsdf.inputs["Base Color"])
    for k, v in (("Sheen Weight", 0.2), ("Roughness", 0.72)):
        if k in bsdf.inputs: bsdf.inputs[k].default_value = v
    if "Sheen Tint" in bsdf.inputs:
        try: bsdf.inputs["Sheen Tint"].default_value = (1, 0.93, 0.85, 1)
        except Exception: pass
    s["body_lin"] = body[:3]

def fur():
    """short plush fur via Geometry Nodes curves (after the armature, so it follows every pose); no fur on eyes/brows/nostrils/inner ears"""
    img = tex.image; px = img.pixels[:]; W, H = img.size
    bsrgb = (0.949, 0.812, 0.651)
    uvname = h.data.uv_layers.active.name; uvl = h.data.uv_layers.active.data
    wts = {}
    for poly in h.data.polygons:
        for li in poly.loop_indices:
            u, v = uvl[li].uv; x = min(W - 1, max(0, int(u * W))); y = min(H - 1, max(0, int(v * H)))
            i = (y * W + x) * 4; c3 = px[i:i + 3]
            ok = sum(abs(c3[j] - bsrgb[j]) for j in range(3)) < 0.3 and (c3[0] - c3[1]) < 0.22
            vi = h.data.loops[li].vertex_index; wts[vi] = min(wts.get(vi, 1.0), 1.0 if ok else 0.0)
    vg = h.vertex_groups.new(name="fur_density")
    vg.add([vi for vi, wv in wts.items() if wv > 0], 1.0, "REPLACE")
    print("fur verts", sum(1 for wv in wts.values() if wv > 0), "of", len(wts), "uv", uvname)
    g = bpy.data.node_groups.new("Fur", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = g.nodes.new; L = g.links.new
    gi = N("NodeGroupInput"); go = N("NodeGroupOutput")
    sel = N("GeometryNodeInputNamedAttribute"); sel.data_type = "FLOAT"; sel.inputs["Name"].default_value = "fur_density"
    dist = N("GeometryNodeDistributePointsOnFaces"); dist.distribute_method = "RANDOM"
    dist.inputs["Density"].default_value = float(kv.get("density", 170000)); dist.inputs["Seed"].default_value = 7
    L(gi.outputs[0], dist.inputs["Mesh"]); L(sel.outputs[0], dist.inputs["Selection"])
    line = N("GeometryNodeCurvePrimitiveLine"); line.inputs["End"].default_value = (0, 0, 1)
    res = N("GeometryNodeResampleCurve"); res.inputs["Count"].default_value = 4; L(line.outputs[0], res.inputs[0])
    sp = N("GeometryNodeSplineParameter")
    st = N("GeometryNodeStoreNamedAttribute"); st.data_type = "FLOAT"; st.domain = "POINT"; st.inputs["Name"].default_value = "tip"
    L(res.outputs[0], st.inputs["Geometry"]); L(sp.outputs["Factor"], st.inputs["Value"])
    rnd = N("FunctionNodeRandomValue"); rnd.data_type = "FLOAT"
    fl = [x for x in rnd.inputs if x.type == "VALUE" and x.name in ("Min", "Max")]; fl[0].default_value = 0.6; fl[1].default_value = 1.0
    rout = next(x for x in rnd.outputs if x.type == "VALUE")
    mul = N("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = float(kv.get("len", 0.0075))
    L(rout, mul.inputs[0])
    inst = N("GeometryNodeInstanceOnPoints")
    L(dist.outputs["Points"], inst.inputs["Points"]); L(st.outputs[0], inst.inputs["Instance"])
    L(dist.outputs["Rotation"], inst.inputs["Rotation"]); L(mul.outputs[0], inst.inputs["Scale"])
    real = N("GeometryNodeRealizeInstances"); L(inst.outputs[0], real.inputs[0])
    rad = N("GeometryNodeSetCurveRadius"); L(real.outputs[0], rad.inputs[0])
    tipa = N("GeometryNodeInputNamedAttribute"); tipa.data_type = "FLOAT"; tipa.inputs["Name"].default_value = "tip"
    tap = N("ShaderNodeMath"); tap.operation = "MULTIPLY_ADD"; L(tipa.outputs[0], tap.inputs[0])
    th = float(kv.get("thick", 0.0007)); tap.inputs[1].default_value = -0.85 * th; tap.inputs[2].default_value = th
    L(tap.outputs[0], rad.inputs["Radius"])
    prof = N("GeometryNodeCurvePrimitiveCircle"); prof.inputs["Resolution"].default_value = 3; prof.inputs["Radius"].default_value = 1.0
    c2m = N("GeometryNodeCurveToMesh"); L(rad.outputs[0], c2m.inputs["Curve"]); L(prof.outputs[0], c2m.inputs["Profile Curve"])
    if "Scale" in c2m.inputs: L(tap.outputs[0], c2m.inputs["Scale"])     # Blender 5: profile scale is an input, not the radius
    mat_n = N("GeometryNodeSetMaterial"); L(c2m.outputs[0], mat_n.inputs[0])
    j = N("GeometryNodeJoinGeometry"); L(gi.outputs[0], j.inputs[0]); L(mat_n.outputs[0], j.inputs[0]); L(j.outputs[0], go.inputs[0])
    # hair material: body colour, darker at the root, lighter at the tip
    hm = bpy.data.materials.new("Fur"); hm.use_nodes = True; hn = hm.node_tree
    hb = next(n for n in hn.nodes if n.type == "BSDF_PRINCIPLED")
    at = hn.nodes.new("ShaderNodeAttribute"); at.attribute_name = "tip"
    ramp = hn.nodes.new("ShaderNodeValToRGB"); hn.links.new(at.outputs["Fac"], ramp.inputs[0])
    b = s["body_lin"]
    ramp.color_ramp.elements[0].color = (b[0] * 0.93, b[1] * 0.91, b[2] * 0.89, 1)
    ramp.color_ramp.elements[1].color = (min(1, b[0] * 1.03), min(1, b[1] * 1.03), min(1, b[2] * 1.04), 1)
    hn.links.new(ramp.outputs[0], hb.inputs["Base Color"]); hb.inputs["Roughness"].default_value = 0.7
    mat_n.inputs["Material"].default_value = hm
    m = h.modifiers.new("Fur", "NODES"); m.node_group = g

if var in ("smooth", "fur"):
    if not kv.get("nolight"): soft_light()
    smooth_surface()
    if kv.get("nocs"): h.modifiers.remove(h.modifiers["SurfSmooth"])
    if kv.get("notex"): nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
if var == "fur":
    fur()
if var == "fur":
    dg = bpy.context.evaluated_depsgraph_get(); ev = h.evaluated_get(dg)
    print("mods", [m.type for m in h.modifiers])
    for inst in dg.object_instances:
        if inst.object.original == h or inst.object.name.startswith("Hippo"):
            print("inst", inst.object.type, inst.object.name, getattr(inst.object.data, "curves", None) and len(inst.object.data.curves))
s.render.image_settings.file_format = "PNG"; s.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDERED", var, out)
