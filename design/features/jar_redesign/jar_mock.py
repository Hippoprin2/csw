# 유리병 탭 병 디자인 시안 3종 (기능 스레드, 2026-11-13). ART_BIBLE 7번 조명/색 변환 그대로.
# usage: blender -b --python design/features/jar_redesign/jar_mock.py -- <out_dir>
import bpy, math, os, random, sys
from mathutils import Vector
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts/blender"))
import room as R
from room import M, P, rbox, sph, cyl, lathe
from props import mat

OUT = sys.argv[sys.argv.index("--") + 1]
CAT = ["#9ccfd8", "#f6b26b", "#a4c2f4", "#b4a7d6", "#f9cb9c", "#d5a6bd", "#ea9999", "#b6d7a8"]
for i, h in enumerate(CAT):
    P[f"cat{i}"] = tuple(int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))
P.update({"glass": (0.80, 0.91, 0.93), "jar_rim": (0.85, 0.79, 0.69), "lid": (0.80, 0.62, 0.45),
          "cloth": (0.62, 0.84, 0.76), "cloth2": (0.99, 0.97, 0.93)})


def glass(name, alpha=0.32):
    m = mat(name, P["glass"], 0.1, alpha=alpha)
    try: m.surface_render_method = "BLENDED"
    except Exception: m.blend_method = "BLEND"
    m.use_backface_culling = True
    return m


def clear():
    for o in list(bpy.data.objects):
        if o.type == "MESH": bpy.data.objects.remove(o)


def marbles(radius_at, z0, n, mr, seed=3):
    """pile n marbles bottom-up inside a lathe whose inner radius at height z is radius_at(z)"""
    rnd = random.Random(seed); out = []; k = 0; layer = 0
    while k < n:
        z = z0 + mr + layer * mr * 1.75
        rin = radius_at(z) - mr * 1.05
        pts = [(0.0, 0.0)]
        ring = 1
        while ring * mr * 2.05 <= rin + 1e-6:
            rr = ring * mr * 2.05; cnt = int(2 * math.pi * rr / (mr * 2.1))
            pts += [(rr * math.cos(2 * math.pi * j / cnt + layer), rr * math.sin(2 * math.pi * j / cnt + layer)) for j in range(cnt)]
            ring += 1
        # front marbles first so a partly filled top layer reads from the camera
        pts.sort(key=lambda p: p[1])
        for x, y in pts:
            if k >= n: break
            c = rnd.randrange(len(CAT))
            out.append(sph(f"Mb{k}", mr, (x + rnd.uniform(-.004, .004), y, z + rnd.uniform(-.003, .003)), M(f"cat{c}", 0.4), seg=24)); k += 1
        layer += 1
    return out


def jar_cork(n):
    """A: 방 유리장 병과 같은 모양 (원통 + 코르크 뚜껑 + 코랄 띠), 크게"""
    r, h = 0.5, 1.0
    prof = [(0, 0), (r * .82, 0), (r, .1), (r, h - .14), (r * .8, h - .04), (r * .74, h)]
    parts = [lathe("G", prof, glass("gA"))]
    parts += [cyl("Rim", r * .78, .09, (0, 0, h + .02), M("jar_rim", .6), bevel=.35),
              cyl("Lid", r * .82, .15, (0, 0, h + .13), M("lid", .8), bevel=.35),
              cyl("Band", r * .85, .06, (0, 0, h + .09), M("coral", .8), bevel=.3)]
    parts.append(rbox("Sh", (.04, .01, h * .5), (-r * .58, -r - .01, h * .55), glass("shA", .5), r=.45))
    parts += marbles(lambda z: r * .97, 0.02, n, 0.072)
    return parts


def jar_round(n):
    """B: 배가 둥근 병 + 천 뚜껑 + 코랄 리본 (말랑한 실루엣)"""
    R0 = 0.56
    prof = [(0, 0)] + [(R0 * math.sin(math.radians(a)) * (1 if a < 150 else 1), R0 - R0 * math.cos(math.radians(a))) for a in range(12, 151, 6)]
    neck = prof[-1][1]
    prof += [(0.26, neck + 0.05), (0.27, neck + 0.16)]
    parts = [lathe("G", prof, glass("gB"))]
    top = neck + 0.16
    parts.append(cyl("Rim", 0.29, 0.06, (0, 0, top), M("jar_rim", .6), bevel=.4))
    # cloth cap: squashed dome + skirt
    parts.append(sph("Cap", 0.33, (0, 0, top + 0.04), M("cloth", .85), scale=(1, 1, .45)))
    parts.append(cyl("Skirt", 0.31, 0.12, (0, 0, top - 0.04), M("cloth", .85), r2=0.34, bevel=.3))
    parts.append(cyl("Rib", 0.3, 0.04, (0, 0, top - 0.02), M("coral", .7), bevel=.3))
    parts.append(sph("Bow1", 0.07, (-0.07, -0.29, top - 0.02), M("coral", .7), scale=(1.3, .6, .8)))
    parts.append(sph("Bow2", 0.07, (0.07, -0.29, top - 0.02), M("coral", .7), scale=(1.3, .6, .8)))
    parts.append(sph("Knot", 0.035, (0, -0.31, top - 0.02), M("coral", .7)))
    parts.append(rbox("Sh", (.04, .01, .32), (-0.33, -0.45, 0.5), glass("shB", .5), r=.45))
    def rad(z):
        if z >= R0 * 2 - 0.2: return 0.25
        return math.sqrt(max(R0 ** 2 - (z - R0) ** 2, 0.01))
    parts += marbles(lambda z: min(rad(z), rad(z + 0.07)) * .97, 0.03, n, 0.07)
    return parts


def table():
    """C 장면용 낮은 나무 탁자"""
    p = [rbox("Top", (1.5, .8, .1), (0, 0, -.06), M("wood"), r=.4)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(cyl(f"Leg{sx}{sy}", .06, .4, (sx * .58, sy * .26, -.31), M("wood2"), r2=.05))
    return p


def render(parts, name, elev=0.22, pad=1.08, ortho=None):
    sc = bpy.context.scene
    R.frame_on(sc.camera, parts, elev=elev, pad=pad)
    if ortho: sc.camera.data.ortho_scale = ortho
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)


sc, cam = R.setup_render(800, 900, 2)
N = 19
clear(); render(jar_cork(N), "A_cork.png")
clear(); render(jar_round(N), "B_round.png")
clear(); ps = jar_cork(N) + table()
render(ps, "C_scene_jar.png", elev=0.12)
print("done")
