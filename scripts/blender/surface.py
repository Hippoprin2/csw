# 단짝 표면 v2 ("매끈하게 + 줄 지움", 대표 확정 2026-11-13). Applied at render time by render_clip.py / render_milestone.py.
#  - weld the UV-seam duplicate verts of the AI scan (else smoothing cracks the seams open)
#  - drop the GLB custom normals / sharp flags (they keep the belly line + leg/arm seam creases)
#  - Corrective Smooth after the armature (whole body) + a stronger one on the bumpy seam verts only
#  - body texels -> flat #F2CFA6 (eyes, brows, nostrils, inner-ear pink keep the texture), soft sheen
#  - softer sun shadows + ambient occlusion (the light used in the approved comparison)
# Off switch: env HIPPO_SURFACE=0 (old look).
import bpy, bmesh, math, os

BODY = (0.891, 0.632, 0.389, 1)   # #F2CFA6 linear (= texture median)


def _weld_and_mark(h, pct=0.9):
    bm = bmesh.new(); bm.from_mesh(h.data); n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.verts.ensure_lookup_table(); bm.normal_update()
    lap = {}
    for v in bm.verts:
        nb = [e.other_vert(v).co for e in v.link_edges]
        if not nb: continue
        avg = sum(nb, v.co * 0) / len(nb)
        el = sum((c - v.co).length for c in nb) / len(nb) + 1e-9
        lap[v.index] = abs((v.co - avg).dot(v.normal)) / el          # scale-free bumpiness
    vals = sorted(lap.values()); thr = vals[int(len(vals) * pct)]
    ring = {i: 1.0 for i, x in lap.items() if x > thr}; front = set(ring)
    for wv in (0.8, 0.5, 0.2):                                         # 3 falloff rings
        nxt = set()
        for i in front:
            for e in bm.verts[i].link_edges:
                j = e.other_vert(bm.verts[i]).index
                if j not in ring: ring[j] = wv; nxt.add(j)
        front = nxt
    bm.to_mesh(h.data); bm.free()
    me = h.data
    for an in ("custom_normal", "sharp_edge", "sharp_face"):
        if an in me.attributes: me.attributes.remove(me.attributes[an])
    for poly in me.polygons: poly.use_smooth = True
    vg = h.vertex_groups.new(name="seam_ridge")
    for i, wv in ring.items(): vg.add([i], wv, "REPLACE")
    return n0 - len(me.vertices)


def _smooth_mods(h):
    sm = h.modifiers.new("SurfSmooth", "CORRECTIVE_SMOOTH")           # appended after the armature
    sm.factor = 1.0; sm.iterations = 25; sm.smooth_type = "LENGTH_WEIGHTED"; sm.use_only_smooth = True; sm.rest_source = "ORCO"
    s2 = h.modifiers.new("SeamSmooth", "CORRECTIVE_SMOOTH")
    s2.factor = 1.0; s2.iterations = 15; s2.smooth_type = "LENGTH_WEIGHTED"; s2.use_only_smooth = True
    s2.vertex_group = "seam_ridge"; s2.rest_source = "ORCO"


def _flat_body_material(h):
    nt = h.data.materials[0].node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    L = nt.links.new
    dif = nt.nodes.new("ShaderNodeMix"); dif.data_type = "RGBA"; dif.blend_type = "DIFFERENCE"; dif.inputs[0].default_value = 1
    L(tex.outputs["Color"], dif.inputs[6]); dif.inputs[7].default_value = BODY
    bw = nt.nodes.new("ShaderNodeRGBToBW"); L(dif.outputs[2], bw.inputs[0])
    r1 = nt.nodes.new("ShaderNodeMapRange"); L(bw.outputs[0], r1.inputs[0]); r1.inputs[1].default_value = 0.3; r1.inputs[2].default_value = 0.4
    sep = nt.nodes.new("ShaderNodeSeparateColor"); L(tex.outputs["Color"], sep.inputs[0])
    rg = nt.nodes.new("ShaderNodeMath"); rg.operation = "SUBTRACT"; L(sep.outputs[0], rg.inputs[0]); L(sep.outputs[1], rg.inputs[1])
    r2 = nt.nodes.new("ShaderNodeMapRange"); L(rg.outputs[0], r2.inputs[0]); r2.inputs[1].default_value = 0.4; r2.inputs[2].default_value = 0.48
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; L(r1.outputs[0], mx.inputs[0]); L(r2.outputs[0], mx.inputs[1])
    flat = nt.nodes.new("ShaderNodeMix"); flat.data_type = "RGBA"; flat.blend_type = "MIX"
    L(mx.outputs[0], flat.inputs[0]); flat.inputs[6].default_value = BODY; L(tex.outputs["Color"], flat.inputs[7])
    L(flat.outputs[2], bsdf.inputs["Base Color"])
    for k, v in (("Sheen Weight", 0.2), ("Roughness", 0.72)):
        if k in bsdf.inputs: bsdf.inputs[k].default_value = v
    if "Sheen Tint" in bsdf.inputs:
        try: bsdf.inputs["Sheen Tint"].default_value = (1, 0.93, 0.85, 1)
        except Exception: pass


def soft_light(scene):
    for o in scene.objects:
        if o.type == "LIGHT" and hasattr(o.data, "angle"):
            o.data.angle = math.radians(18 if o.name == "key" else 30)
            if o.name == "key": o.data.color = (1.0, 0.97, 0.93)
    ee = scene.eevee
    for k, v in (("use_gtao", True), ("gtao_distance", 0.12), ("use_soft_shadows", True), ("taa_render_samples", 64)):
        if hasattr(ee, k):
            try: setattr(ee, k, v)
            except Exception: pass


def apply(scene):
    if os.environ.get("HIPPO_SURFACE") == "0":
        print("SURFACE old"); return
    h = bpy.data.objects.get("Hippo")
    if h is None or "SurfSmooth" in h.modifiers:
        return
    n = _weld_and_mark(h); _smooth_mods(h); _flat_body_material(h); soft_light(scene)
    print("SURFACE v2 welded", n)
