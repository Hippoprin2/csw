# Usage: Blender -b -P build_hippo_v2.py -- clean.glb out_dir [lid_angle_deg]
# - flattens body texture to cream beige (concept color), erases painted eyes,
#   recolors the tail to the body color
# - adds separate eye parts per side: eyeball (sclera), iris, highlight, eyelid + lash line.
#   Eyelid sits under an empty "Lid.L/R" -> rotate its local X to blink.
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
src, outdir = argv[0], argv[1]
LID_DEG = float(argv[2]) if len(argv) > 2 else -5.0
os.makedirs(outdir, exist_ok=True)

BODY = np.array([242, 207, 166]) / 255.0      # concept cream beige (sRGB)
LID = (0.80, 0.66, 0.52)                       # slightly darker beige lid (sRGB-ish)
SCLERA = (0.97, 0.94, 0.86)
IRIS = (0.30, 0.16, 0.08)
LASH = (0.22, 0.13, 0.08)

def srgb2lin(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obj = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
obj.name = "Hippo"
me = obj.data
mw = obj.matrix_world
mwi = mw.inverted()
uv = me.uv_layers.active.data

mat = me.materials[0]
bsdf = [n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"][0]
img = bsdf.inputs["Base Color"].links[0].from_node.image
W, H = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)

# ---------- bbox / front camera mapping (same as render_turnaround.py) ----------
verts = np.array([mw @ v.co for v in me.vertices])
mn, mx = verts.min(0), verts.max(0)
ctr, size = (mn + mx) / 2, mx - mn
S = max(size[2], size[0] * 1024 / 768, size[1] * 1024 / 768) * 1.1

def front_ray(pxx, pyy):
    x = ctr[0] + (pxx - 384) * S / 1024
    z = ctr[2] + (512 - pyy) * S / 1024
    o = mwi @ Vector((x, -10.0, z))
    d = (mwi.to_3x3() @ Vector((0, 1, 0))).normalized()
    hit, loc, nor, fi = obj.ray_cast(o, d)
    return (hit, loc, nor, fi)

def uv_at(loc, fi):
    poly = me.polygons[fi]
    vs = [me.vertices[me.loops[li].vertex_index].co for li in poly.loop_indices]
    uvs = [uv[li].uv for li in poly.loop_indices]
    a, b, c = vs[0], vs[1], vs[2]
    v0, v1, v2 = b - a, c - a, loc - a
    d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
    d20, d21 = v2.dot(v0), v2.dot(v1)
    den = d00 * d11 - d01 * d01 or 1e-12
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    u = 1 - v - w
    return uvs[0] * u + uvs[1] * v + uvs[2] * w

# ---------- texture: flatten body to concept beige ----------
rgb = px[..., :3]
used = px[..., 3] > 0.5
old_body = np.median(rgb[used], axis=0)
lum = rgb.mean(-1)
chroma = rgb / np.maximum(lum[..., None], 1e-4)
cd = np.linalg.norm(chroma - old_body / old_body.mean(), axis=-1)
is_body = used & (cd < 0.14) & (lum > old_body.mean() * 0.4) & (lum < old_body.mean() * 1.5)
# palette snap: every texel -> nearest of {body, pink (ear), dark (brows/nostrils)} -> flat
# colors. Avoids speckled ears/nostrils that a body-only threshold leaves behind.
pinkish = used & (rgb[..., 0] - rgb[..., 1] > 0.22)
darkish = used & (lum < old_body.mean() * 0.45)
old_pal = np.stack([old_body,
                    np.median(rgb[pinkish], axis=0) if pinkish.any() else np.array([0.82, 0.5, 0.46]),
                    np.median(rgb[darkish], axis=0) if darkish.any() else np.array([0.3, 0.2, 0.15])])
new_pal = np.array([BODY, np.array([236, 150, 140]) / 255.0, np.array([88, 54, 40]) / 255.0])
print("old palette", (old_pal * 255).round())
dists = np.stack([np.linalg.norm(rgb - c, axis=-1) for c in old_pal], -1)
cls = dists.argmin(-1)
# pink only where the texel is really pink (nostril/brow edge blends otherwise snap to pink)
real_pink = (rgb[..., 0] - rgb[..., 1] > 0.25) & (lum > 0.45)
fallback = np.where(dists[..., 0] <= dists[..., 2], 0, 2)
cls = np.where((cls == 1) & ~real_pink, fallback, cls)
for i in range(3):
    px[used & (cls == i), :3] = new_pal[i]
print("palette share body/pink/dark:", [round(float((used & (cls == i)).sum() / used.sum()), 3) for i in range(3)])

def fill_mask(mask, color):
    from_mask = mask.copy()
    # dilate a few texels so seams don't leave old color
    for _ in range(3):
        m = from_mask.copy()
        m[1:] |= from_mask[:-1]; m[:-1] |= from_mask[1:]
        m[:, 1:] |= from_mask[:, :-1]; m[:, :-1] |= from_mask[:, 1:]
        from_mask = m
    px[from_mask, :3] = color
    return from_mask.sum()

# ---------- erase painted eyes (sample through the front view) ----------
eye_boxes = [(250, 352, 200, 306), (416, 520, 200, 306)]
emask = np.zeros((H, W), bool)
for x0, x1, y0, y1 in eye_boxes:
    for yy in np.arange(y0, y1, 0.5):
        for xx in np.arange(x0, x1, 0.5):
            hit, loc, nor, fi = front_ray(xx, yy)
            if hit:
                t = uv_at(loc, fi)
                tx = int(np.clip(t.x * W, 0, W - 1)); ty = int(np.clip(t.y * H, 0, H - 1))
                emask[ty, tx] = True
print("eye texels erased:", fill_mask(emask, BODY))

# ---------- tail -> body color ----------
def raster_faces(face_ids):
    m = np.zeros((H, W), bool)
    for fi in face_ids:
        p = me.polygons[fi]
        t = np.array([[uv[li].uv.x * W, uv[li].uv.y * H] for li in p.loop_indices])
        x0, y0 = np.floor(t.min(0)).astype(int); x1, y1 = np.ceil(t.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a, b, c = t[0], t[1], t[2]
        def s(p1, p2):
            return (gx - p2[0]) * (p1[1] - p2[1]) - (p1[0] - p2[0]) * (gy - p2[1])
        d1, d2, d3 = s(a, b), s(b, c), s(c, a)
        neg = (d1 < 0) | (d2 < 0) | (d3 < 0); pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
        m[y0:y1 + 1, x0:x1 + 1] |= ~(neg & pos)
    return m

tail_faces = []
for p in me.polygons:
    c = mw @ p.center
    if c.z < -0.20 and c.z > -0.38 and c.y > 0.205 and abs(c.x) < 0.10:
        tail_faces.append(p.index)
print("tail faces:", len(tail_faces), "texels:", fill_mask(raster_faces(tail_faces), BODY))

img.pixels[:] = px.ravel()
img.filepath_raw = os.path.join(outdir, "hippo_v2_basecolor.png"); img.file_format = "PNG"
img.save()
# GLB export ignores edited pixels of the imported (packed) image -> reload from disk
img_node = bsdf.inputs["Base Color"].links[0].from_node
new_img = bpy.data.images.load(img.filepath_raw); new_img.pack()
img_node.image = new_img
bsdf.inputs["Roughness"].default_value = 0.85
for k in ("Metallic", "Roughness"):
    for l in list(bsdf.inputs[k].links):
        mat.node_tree.links.remove(l)
bsdf.inputs["Metallic"].default_value = 0.0

# ---------- eye parts ----------
def make_mat(name, rgb, rough=0.5, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    col = tuple(srgb2lin(rgb)) + (1,)
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = col
        b.inputs["Emission Strength"].default_value = emit
    return m

M_SCL = make_mat("Eye_Sclera", SCLERA, 0.25)
M_IRIS = make_mat("Eye_Iris", IRIS, 0.15)
M_HL = make_mat("Eye_Highlight", (1, 1, 1), 0.2, emit=3.0)
M_LID = make_mat("Eye_Lid", LID, 0.85)
M_LASH = make_mat("Eye_Lash", LASH, 0.6)

def sphere(name, r=1.0, seg=48, ring=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    for f in bm.faces: f.smooth = True
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(name, m); bpy.context.scene.collection.objects.link(o)
    return o

def hemisphere(name, r=1.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=r)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    for f in bm.faces: f.smooth = True
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(name, m); bpy.context.scene.collection.objects.link(o)
    sol = o.modifiers.new("thick", "SOLIDIFY"); sol.thickness = 0.04; sol.offset = 1
    return o

def torus(name, minor=0.05):
    bm = bmesh.new()
    seg, rs = 64, 12
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(rs):
            b = 2 * math.pi * j / rs
            rr = 1 + minor * math.cos(b)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), minor * math.sin(b))))
        rings.append(ring)
    for i in range(seg):
        for j in range(rs):
            f = bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % rs], rings[i][(j + 1) % rs]))
            f.smooth = True
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new(name, m); bpy.context.scene.collection.objects.link(o)
    return o

def empty(name, parent=None):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    e.empty_display_size = 0.02
    if parent: e.parent = parent
    return e

# eye centers from the front view (centre of the old painted eye incl. lid)
hits = []
for cx in (301, 468):
    hit, loc, nor, fi = front_ray(cx, 258)
    assert hit, "eye ray missed"
    hits.append((mw @ loc, (mw.to_3x3() @ me.polygons[fi].normal).normalized()))
# symmetrize
ax = (abs(hits[0][0].x) + abs(hits[1][0].x)) / 2
ay = (hits[0][0].y + hits[1][0].y) / 2
az = (hits[0][0].z + hits[1][0].z) / 2
nrm = Vector(((abs(hits[0][1].x) + abs(hits[1][1].x)) / 2, (hits[0][1].y + hits[1][1].y) / 2,
              (hits[0][1].z + hits[1][1].z) / 2)).normalized()
R = 50 * S / 1024        # half eye width in world units
print("eye R", round(R, 4), "pos", (round(ax, 3), round(ay, 3), round(az, 3)), "normal", tuple(round(v, 3) for v in nrm))

for side, sx in (("L", -1), ("R", 1)):  # character's right is -X? naming by screen: L = screen-left
    P = Vector((sx * ax, ay, az))
    N = Vector((sx * nrm.x, nrm.y, nrm.z))
    # blend normal toward straight-forward (-Y) so eyes look at the viewer
    F = (N * 0.5 + Vector((0, -1, 0)) * 0.5).normalized()
    U = (Vector((0, 0, 1)) - F * F.z).normalized()
    Rt = F.cross(U).normalized()            # local X
    # local frame: X = Rt, Y = -F (so local -Y = outward, Blender "front"), Z = U
    rot = Matrix((Rt, -F, U)).transposed().to_4x4()
    root = empty(f"Eye.{side}")
    root.matrix_world = Matrix.Translation(P - F * (0.45 * R)) @ rot
    s = Vector((R, 0.75 * R, 0.8 * R))      # eyeball semi-axes (x, depth, z)

    ball = sphere(f"Eye_Ball.{side}"); ball.parent = root
    ball.scale = s; ball.data.materials.append(M_SCL)

    iris = sphere(f"Eye_Iris.{side}"); iris.parent = root
    iris.scale = (0.5 * R, 0.12 * R, 0.58 * R); iris.location = (0, -0.64 * R, -0.08 * R)
    iris.data.materials.append(M_IRIS)

    hl = sphere(f"Eye_Highlight.{side}", seg=16, ring=8); hl.parent = root
    hl.scale = (0.09 * R,) * 3; hl.location = (0.2 * R * sx, -0.78 * R, -0.12 * R)
    hl.data.materials.append(M_HL)

    lid_pivot = empty(f"Lid.{side}", root)
    lid_pivot.rotation_euler = (math.radians(LID_DEG), 0, 0)
    lid = hemisphere(f"Eye_Lid.{side}"); lid.parent = lid_pivot
    lid.scale = (1.07 * R, 0.9 * R, 0.88 * R); lid.data.materials.append(M_LID)
    lash = torus(f"Eye_Lash.{side}", minor=0.035); lash.parent = lid_pivot
    lash.scale = (1.08 * R, 0.91 * R, 1.0 * R); lash.data.materials.append(M_LASH)

blend = os.path.join(outdir, "hippo_v2.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
bpy.ops.export_scene.gltf(filepath=os.path.join(outdir, "hippo_v2.glb"), export_apply=True)
print("SAVED", blend)
