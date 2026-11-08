# Build the eye decal straight from the concept art pixels (exact look).
# Maps concept-image px -> front-render px with a similarity transform anchored on the
# irises, samples the concept into the decal canvas, soft elliptical mask around eyes+brows,
# per-channel gain so the concept skin matches the model's body color at the mask edge.
# Usage: python concept_eye_decal.py concept_front.png out.png
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

src, out = sys.argv[1], sys.argv[2]
X0, Y0, X1, Y1 = 200, 110, 570, 420   # decal canvas window (render px), same as build_hippo_v3.py
SS = 4
BODY = np.array([242, 207, 166], float)

c = np.array(Image.open(src).convert("RGB")).astype(float)
Hc, Wc, _ = c.shape
# concept iris centres (dark blobs in the upper half)
lum = c.mean(-1); dark = lum < 90; dark[Hc // 2:] = False
lab, n = ndimage.label(dark)
blobs = sorted([b for b in (np.argwhere(lab == i) for i in range(1, n + 1)) if len(b) > 800],
               key=lambda b: b[:, 1].mean())
(cy1, cx1), (cy2, cx2) = blobs[0].mean(0), blobs[1].mean(0)
# render eye centres (old painted eyes on the TRELLIS model)
rx1, rx2, ry = 306.8, 459.2, 255.7
s = (rx2 - rx1) / (cx2 - cx1)
ccx, ccy, rcx = (cx1 + cx2) / 2, (cy1 + cy2) / 2, (rx1 + rx2) / 2
print("concept irises", (round(cx1), round(cy1)), (round(cx2), round(cy2)), "scale", round(s, 3))

w, h = (X1 - X0) * SS, (Y1 - Y0) * SS
gx, gy = np.meshgrid(np.arange(w) / SS + X0, np.arange(h) / SS + Y0)
ux = (gx - rcx) / s + ccx
uy = (gy - ry) / s + ccy
samp = np.stack([ndimage.map_coordinates(c[..., k], [uy, ux], order=1, mode="nearest") for k in range(3)], -1)

# soft mask: one ellipse per eye, covering lid + brow, in concept px
m = np.zeros((h, w))
def add(ex, ey, rx, ry, soft=0.35):
    global m
    d = ((ux - ex) / rx) ** 2 + ((uy - ey) / ry) ** 2
    m = np.maximum(m, np.clip((1 - d) / soft, 0, 1))
for ex, ey in ((cx1, cy1), (cx2, cy2)):
    add(ex, ey - 30, 68, 84)          # eye + lid + brow (concept brows sit ~60px above iris)
# nostrils: cover both the concept nostrils and the model's own painted ones
lum2 = c.mean(-1); nd = (lum2 < 150) & (c[..., 0] - c[..., 2] > 40)
nd[: int(ccy + 40)] = False; nd[int(ccy + 160):] = False
labn, nn = ndimage.label(nd)
nos = [b.mean(0) for b in (np.argwhere(labn == i) for i in range(1, nn + 1)) if 80 < len(b) < 3000]
print("concept nostrils", [tuple(np.round(b[::-1])) for b in nos])
for ny, nx in nos:
    add(nx, ny, 26, 30)
for rx_, ry_ in ((321, 364), (445, 364)):     # model nostrils (render px) -> concept px
    add((rx_ - rcx) / s + ccx, (ry_ - ry) / s + ccy, 30, 32)
m = m ** 1.5

# colour match: concept skin ring around the mask edge -> BODY
ring = (m > 0.02) & (m < 0.3)
skin = np.median(samp[ring], axis=0)
gain = BODY / skin
print("skin", skin.round(), "gain", gain.round(3))
samp = np.clip(samp * gain, 0, 255)

rgba = np.dstack([samp, m * 255]).astype(np.uint8)
Image.fromarray(rgba, "RGBA").save(out)
print("wrote", out, (w, h))
