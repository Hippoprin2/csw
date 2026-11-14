# Render an action .blend with the shared look (ART_BIBLE lights/camera) + a soft floor shadow.
# Usage: Blender -b action.blend -P render_clip.py -- out_dir elev [glide] [noshadow]
#   elev 0.12 = room/default (6.5 deg), 0.5 = garden/yard (25 deg, WORLD.md W2)
#   glide  = desk scenes: camera eases 0.12 -> 0.5 over f1-10 and back over f52-62
import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
out, elev = a[0], float(a[1])
flags = set(a[2:])
s = bpy.context.scene

def fcurves(act):
    fcs = list(getattr(act, "fcurves", []) or [])
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags: fcs += list(cb.fcurves)
    except Exception:
        pass
    return fcs

# the confetti burst starts in front of the face and reads as a sticker on the snout -> start it above the head
if True:
    for o in bpy.data.objects:
        if o.name.startswith("Confetti") and o.animation_data and o.animation_data.action:
            for fc in fcurves(o.animation_data.action):
                if fc.data_path == "location" and fc.array_index in (1, 2):
                    d = 0.14 if fc.array_index == 1 else 0.16
                    for kp in fc.keyframe_points:
                        kp.co.y += d; kp.handle_left.y += d; kp.handle_right.y += d

for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: s.render.engine = e; break
    except Exception: pass
s.render.film_transparent = True
s.view_settings.view_transform = "Standard"; s.view_settings.look = "None"
W = int(next((x[2:] for x in flags if x.startswith("w=")), 600))   # w=1600: wide canvas for clips that travel sideways (roll), same px scale, centred
H = int(next((x[2:] for x in flags if x.startswith("h=")), 800))   # h=1100: taller canvas (extra room ABOVE, feet stay at y 713 from the bottom-aligned 800 frame)
s.render.resolution_x, s.render.resolution_y = W, H
s.render.fps = 24
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA") or o.name == "FloorShadow"]:
    bpy.data.objects.remove(o, do_unlink=True)
for n, rot, en in (("key", (50, 0, 30), 3.0), ("fill", (60, 0, -120), 1.2), ("rim", (110, 0, 180), 2.0), ("bounce", (150, 0, 0), 0.7)):
    d = bpy.data.lights.new(n, "SUN"); d.energy = en
    o = bpy.data.objects.new(n, d); s.collection.objects.link(o); o.rotation_euler = [math.radians(x) for x in rot]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import surface; surface.apply(s)          # 단짝 표면 v2 (매끈하게 + 줄 지움, 2026-11-13); HIPPO_SURFACE=0 = old look
# yard item reference geometry (anim_yard.py): holdouts cut the pet where the item is in front of it; the rest is hidden
for o in bpy.data.objects:
    if o.get("yard_ref") and not os.environ.get("YARD_SHOW"):   # YARD_SHOW=1: preview with the item visible
        if hasattr(o, "visible_shadow"): o.visible_shadow = False
        if o.get("holdout"): o.is_holdout = True
        else: o.hide_render = True
cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = 1.45 * max(W, H) / 800
c = bpy.data.objects.new("cam", cd); s.collection.objects.link(c); s.camera = c
t = Vector((0, 0, 0.07))
def place(e):
    c.location = t + Vector((0.35, -1, e)).normalized() * 10
    c.rotation_euler = (t - c.location).to_track_quat("-Z", "Y").to_euler()
if "glide" in flags:
    LOW, HIGH = 0.12, 0.5
    ease = lambda x: x * x * (3 - 2 * x)
    for f in range(s.frame_start, s.frame_end + 1):
        if f <= 10: e = LOW + (HIGH - LOW) * ease((f - 1) / 9)
        elif f >= 52: e = HIGH + (LOW - HIGH) * ease(min(1, (f - 52) / 10))
        else: e = HIGH
        place(e); c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_euler", frame=f)
else:
    place(elev)
    if H > 800:   # extend upward: shift the view along the camera's up axis by the extra height
        bpy.context.view_layer.update()
        c.location += c.matrix_world.to_3x3() @ Vector((0, (H - 800) / 2 * 1.45 / 800, 0))

# ---------------- soft floor shadow (blob): shrinks/fades as the character leaves the floor
if "noshadow" not in flags:
    rig = bpy.data.objects.get("HippoRig")
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0.02, -0.499))
    sh = bpy.context.active_object; sh.name = "FloorShadow"
    m = bpy.data.materials.new("FloorShadow"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    # radial falloff from the UV centre: r = |uv - 0.5| * 2
    sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = (0.5, 0.5, 0)
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = 0.15   # solid-ish core under the feet
    strength = nt.nodes.new("ShaderNodeValue"); strength.name = "Strength"; strength.outputs[0].default_value = 0.32
    amul = nt.nodes.new("ShaderNodeMath"); amul.operation = "MULTIPLY"
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    dark = nt.nodes.new("ShaderNodeEmission"); dark.inputs["Color"].default_value = (0.16, 0.1, 0.07, 1); dark.inputs["Strength"].default_value = 0.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    L = nt.links.new
    L(tc.outputs["UV"], sub.inputs[0]); L(sub.outputs[0], ln.inputs[0]); L(ln.outputs["Value"], mul.inputs[0])
    L(mul.outputs[0], ramp.inputs[0]); L(ramp.outputs["Color"], amul.inputs[0]); L(strength.outputs[0], amul.inputs[1])
    L(amul.outputs[0], mix.inputs[0]); L(tr.outputs[0], mix.inputs[1]); L(dark.outputs[0], mix.inputs[2])
    L(mix.outputs[0], outn.inputs["Surface"])
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        if hasattr(m, attr):
            try: setattr(m, attr, val)
            except Exception: pass
    sh.data.materials.append(m)
    if hasattr(sh, "visible_shadow"): sh.visible_shadow = False
    BASE = (0.72, 0.62)               # ellipse size (character footprint, a bit wider than the feet)
    rest_z = None
    for f in range(s.frame_start, s.frame_end + 1):
        s.frame_set(f)
        if rig:
            pb = rig.pose.bones["root"]
            hz = (rig.matrix_world @ pb.head).z
            rest_z = hz if rest_z is None and f == s.frame_start else rest_z
            h = hz - (-0.5)                # 0 when standing on the floor
        else:
            h = 0.0
        if rig and "shx" in rig.keys():    # tap clips (roll/fart_hop) key shadow x + lift on the rig
            sh.location.x = float(rig["shx"]); sh.location.y = 0.02 + float(rig.get("shy", 0.0)); sh.keyframe_insert("location", frame=f)
            h = float(rig.get("shh", 0.0))
        lift = max(0.0, h)
        k = max(0.5, 1.0 - 2.2 * lift)     # smaller + lighter while airborne
        sit = min(0.0, h)                  # sitting lowers the root -> slightly wider, darker
        kx = k * (1.0 - 1.5 * sit)
        sh.scale = (BASE[0] * kx, BASE[1] * k, 1)
        sh.keyframe_insert("scale", frame=f)
        if rig and "shadow" in rig.keys():   # yard clips key the shadow off while on a bench/hammock/in the water
            k = max(0.5, k); sit = 0.0; kx = k
            sh.scale = (BASE[0] * kx, BASE[1] * k, 1); sh.keyframe_insert("scale", frame=f)
        mulv = float(rig["shadow"]) if rig and "shadow" in rig.keys() else 1.0
        strength.outputs[0].default_value = 0.55 * (0.35 + 0.65 * k) * (1.0 - 1.2 * sit) * mulv
        strength.outputs[0].keyframe_insert("default_value", frame=f)

os.makedirs(out, exist_ok=True)
s.render.image_settings.file_format = "PNG"
stills = [x for x in flags if x.startswith("frames=")]
if stills:
    for f in [int(v) for v in stills[0][7:].split(",")]:
        s.frame_set(f); s.render.filepath = os.path.join(out, f"f_{f:04d}.png"); bpy.ops.render.render(write_still=True)
else:
    s.render.filepath = os.path.join(out, "f_")
    bpy.ops.render.render(animation=True)
print("RENDERED", out, s.frame_start, s.frame_end)
