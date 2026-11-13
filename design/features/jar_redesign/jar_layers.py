# 유리병 시안 v2: 병 껍데기(뒤 유리 / 앞 뚜껑·반사)만 3D로 렌더하고, 구슬은 앱이 한 겹으로 그리는 방식.
# 모든 구슬이 앞에서 다 보이고(뒤에 숨는 구슬 없음) 손가락 크기라 쓸어 보기(N5)가 된다.
# usage: blender -b --factory-startup --python design/features/jar_redesign/jar_layers.py -- <out_dir>
import bpy, json, math, os, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts/blender"))
import room as R
from room import M, P, rbox, sph, cyl, lathe
from props import mat

OUT = sys.argv[sys.argv.index("--") + 1]
CAT = ["#9ccfd8", "#f6b26b", "#a4c2f4", "#b4a7d6", "#f9cb9c", "#d5a6bd", "#ea9999", "#b6d7a8"]
for i, h in enumerate(CAT):
    P[f"cat{i}"] = tuple(int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))
P.update({"glass": (0.80, 0.91, 0.93), "jar_rim": (0.85, 0.79, 0.69), "lid": (0.80, 0.62, 0.45),
          "cloth": (0.62, 0.84, 0.76)})


def glass(name, alpha):
    m = mat(name, P["glass"], 0.1, alpha=alpha)
    try: m.surface_render_method = "BLENDED"
    except Exception: m.blend_method = "BLEND"
    m.use_backface_culling = True
    return m


def clear():
    for o in list(bpy.data.objects):
        if o.type == "MESH": bpy.data.objects.remove(o)


def jar_A():
    r, h = 0.62, 1.3
    # 2026-11-13 대표 요청: 각진 곳(바닥 모서리·어깨)을 둥글게 — 직선 꺾임 대신 원호 프로필
    cb, cs = 0.2, r * .26                # bottom corner radius / shoulder radius (shoulder ends at neck r*.74)
    prof = [(0, 0)]
    prof += [(r - cb + cb * math.sin(math.radians(a)), cb - cb * math.cos(math.radians(a))) for a in range(0, 91, 6)]
    prof += [(r - cs + cs * math.cos(math.radians(a)), h - .04 - cs + cs * math.sin(math.radians(a))) for a in range(0, 91, 6)]
    prof += [(r * .74, h)]
    back = [lathe("G", prof, glass("gA", .32), seg=64)]
    front = [cyl("Rim", r * .78, .09, (0, 0, h + .02), M("jar_rim", .6), bevel=.45, seg=64),
             cyl("Lid", r * .82, .15, (0, 0, h + .13), M("lid", .8), bevel=.45, seg=64),
             cyl("Band", r * .85, .06, (0, 0, h + .09), M("coral", .8), bevel=.45, seg=64),
]
    inner = (-r * .86, r * .86, .06, h - .2)
    return back, front, inner


def jar_B():
    R0, H = 0.66, 1.25
    # rounded-bottom tall candy jar (squircle side) so the front still holds a tidy grid
    prof = [(0, 0)]
    for a in range(10, 91, 8):
        t = math.radians(a)
        prof.append((R0 - .22 + .22 * math.sin(t), .22 - .22 * math.cos(t)))
    prof += [(R0, H - .25)]
    for a in range(0, 91, 10):
        t = math.radians(a)
        prof.append((R0 - .3 + .3 * math.cos(t), H - .25 + .2 * math.sin(t)))
    top = prof[-1][1]
    prof += [(R0 - .32, top + .1)]
    back = [lathe("G", prof, glass("gB", .32))]
    t2 = top + .1
    front = [cyl("Rim", R0 - .3, .06, (0, 0, t2), M("jar_rim", .6), bevel=.4),
             sph("Cap", R0 - .26, (0, 0, t2 + .05), M("cloth", .85), scale=(1, 1, .42)),
             cyl("Skirt", R0 - .28, .13, (0, 0, t2 - .03), M("cloth", .85), r2=R0 - .24, bevel=.3),
             cyl("Rib", R0 - .27, .045, (0, 0, t2 - .02), M("coral", .7), bevel=.3),
             sph("Bow1", .08, (-.08, -(R0 - .25), t2 - .02), M("coral", .7), scale=(1.3, .6, .8)),
             sph("Bow2", .08, (.08, -(R0 - .25), t2 - .02), M("coral", .7), scale=(1.3, .6, .8)),
             sph("Knot", .04, (0, -(R0 - .23), t2 - .02), M("coral", .7))]
    inner = (-R0 * .84, R0 * .84, .08, H - .28)
    return back, front, inner


def bbox_px(sc, cam, pts):
    vs = [world_to_camera_view(sc, cam, Vector(p)) for p in pts]
    W, H = sc.render.resolution_x, sc.render.resolution_y
    xs = [v.x * W for v in vs]; ys = [(1 - v.y) * H for v in vs]
    return [round(min(xs)), round(min(ys)), round(max(xs) - min(xs)), round(max(ys) - min(ys))]


sc, cam = R.setup_render(800, 1000, 2)
meta = {}
for name, fn in (("A", jar_A), ("B", jar_B)):
    clear()
    back, front, (x0, x1, z0, z1) = fn()
    R.frame_on(cam, back + front, elev=0.12, pad=1.06)
    bpy.context.view_layer.update()
    # inner = front face plane of the glass (y = -r): where the app lays the marble grid
    yf = min(v.co.y for v in back[0].data.vertices) * 0.9
    meta[name] = {"inner": bbox_px(sc, cam, [(x0, yf, z0), (x1, yf, z0), (x0, yf, z1), (x1, yf, z1)])}
    for part, objs, other in (("back", back, front), ("front", front, back)):
        for o in other: o.hide_render = True
        for o in objs: o.hide_render = False
        sc.render.filepath = os.path.join(OUT, f"{name}_{part}.png")
        bpy.ops.render.render(write_still=True)
# marble sprites (same lights): one sphere per category colour
clear()
sc.render.resolution_x = sc.render.resolution_y = 96
for i in range(len(CAT)):
    clear()
    s = sph("Mb", .1, (0, 0, 0), M(f"cat{i}", .35), seg=48)
    R.frame_on(cam, [s], elev=0.12, pad=1.0)
    sc.render.filepath = os.path.join(OUT, f"marble_{i}.png")
    bpy.ops.render.render(write_still=True)
json.dump(meta, open(os.path.join(OUT, "layers.json"), "w"))
print("done", meta)
