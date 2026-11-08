# Draw flat "sleepy" eye decals matching the concept art (run with any python + Pillow).
# Canvas = a window of the 768x1024 front render (see render_turnaround.py framing).
# Usage: python draw_eye_decals.py out_dir
import sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageChops

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
X0, Y0, X1, Y1 = 200, 170, 570, 360          # canvas window in render px
SS = 8                                       # supersampling
EYES = [(301, 262), (468, 262)]              # eye centres in render px
W, H = 78, 58                                # eye (white almond) size in render px

SOCKET = (222, 186, 148, 255)                # darker beige lid / socket
WHITE = (248, 236, 214, 255)
IRIS = (92, 54, 34, 255)
LINE = (170, 124, 90, 255)
LASH = (120, 78, 52, 255)

def P(x, y):  # render px -> canvas px (supersampled)
    return ((x - X0) * SS, (y - Y0) * SS)

def ell(cx, cy, w, h):
    a = P(cx - w / 2, cy - h / 2); b = P(cx + w / 2, cy + h / 2)
    return [a, b]

def mask(size):
    return Image.new("L", size, 0)

def draw(state):
    size = ((X1 - X0) * SS, (Y1 - Y0) * SS)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    for i, (cx, cy) in enumerate(EYES):
        s = -1 if i == 0 else 1                 # outer side direction
        # socket: a bit bigger than the eye, shifted up; soft edge
        m = mask(size); ImageDraw.Draw(m).ellipse(ell(cx, cy - 5, W * 1.08, H * 1.12), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(4.0 * SS))
        img.paste(Image.new("RGBA", size, SOCKET), (0, 0), m)
        lid_y = cy - 0.16 * H                    # lid edge (white/iris visible below)
        if state == "open":
            almond = mask(size); ImageDraw.Draw(almond).ellipse(ell(cx, cy + 2, W, H), fill=255)
            below = mask(size)
            # lid edge: gentle droop toward the outer corner
            def ly(x):  # lid edge y at render x: lower toward the outer corner (sleepy droop)
                t = (x - cx) / (W / 2) * s        # +1 = outer corner, -1 = inner
                return lid_y + 2.5 * t
            ImageDraw.Draw(below).polygon([P(cx - W, ly(cx - W)), P(cx + W, ly(cx + W)),
                                           P(cx + W, cy + H), P(cx - W, cy + H)], fill=255)
            white = ImageChops.multiply(almond, below).filter(ImageFilter.GaussianBlur(0.5 * SS))
            img.paste(Image.new("RGBA", size, WHITE), (0, 0), white)
            iris = mask(size); ImageDraw.Draw(iris).ellipse(ell(cx, cy + 3, W * 0.5, W * 0.5), fill=255)
            iris = ImageChops.multiply(iris, white)
            img.paste(Image.new("RGBA", size, IRIS), (0, 0), iris)
            # lid edge line
            d = ImageDraw.Draw(img)
            pts = [P(x, ly(x)) for x in [cx - W * 0.47 + k * W * 0.094 for k in range(11)]]
            d.line(pts, fill=LINE, width=int(2.2 * SS), joint="curve")
        else:  # closed: soft smile-shaped lash line
            d = ImageDraw.Draw(img)
            box = ell(cx, cy - 2, W * 0.86, H * 0.55)
            d.arc(box, start=15, end=165, fill=LASH, width=int(3.4 * SS))
    img = img.resize((size[0] // 2, size[1] // 2), Image.Resampling.LANCZOS)
    p = os.path.join(OUT, f"eyes_{state}.png"); img.save(p); print("wrote", p, img.size)

draw("open"); draw("closed")
