#!/usr/bin/env python3
"""For a chosen colour, find the most vivid colour of the SAME HUE that still
prints faithfully (sRGB -> CMYK -> sRGB round trip within a small Delta-E).

You keep the colour you wanted; it just stops being a colour the press can't
reach. Batched through one ICC transform so the search is fast."""
from PIL import Image, ImageCms
import colorsys, sys

SRGB = ImageCms.getOpenProfile("/System/Library/ColorSync/Profiles/sRGB Profile.icc")
CMYK = ImageCms.getOpenProfile("/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc")
to_cmyk = ImageCms.buildTransform(SRGB, CMYK, "RGB", "CMYK", renderingIntent=0)
to_rgb  = ImageCms.buildTransform(CMYK, SRGB, "CMYK", "RGB", renderingIntent=0)

def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def rgb2hex(c): return '#%02x%02x%02x' % c

def rgb2lab(rgb):
    def lin(c):
        c /= 255.0
        return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    r, g, b = (lin(v) for v in rgb)
    X = 0.4124564*r+0.3575761*g+0.1804375*b
    Y = 0.2126729*r+0.7151522*g+0.0721750*b
    Z = 0.0193339*r+0.1191920*g+0.9503041*b
    eps, kap = 216/24389, 24389/27
    def f(t): return t**(1/3) if t > eps else (kap*t+16)/116
    fx, fy, fz = f(X/0.95047), f(Y/1.0), f(Z/1.08883)
    return (116*fy-16, 500*(fx-fy), 200*(fy-fz))

def dE(a, b): return sum((x-y)**2 for x, y in zip(a, b))**0.5
def chroma(lab): return (lab[1]**2 + lab[2]**2)**0.5

def roundtrip_many(cols):
    im = Image.new("RGB", (len(cols), 1))
    im.putdata(cols)
    out = ImageCms.applyTransform(ImageCms.applyTransform(im, to_cmyk), to_rgb)
    return list(out.getdata())

def best_printable(hexcol, tol=2.0):
    orig = hex2rgb(hexcol); olab = rgb2lab(orig)
    h, l0, s0 = colorsys.rgb_to_hls(*[c/255 for c in orig])
    cands = []
    for si in range(20, 101, 2):                 # saturation 20..100%
        for li in range(20, 86, 2):              # lightness  20..85%
            r, g, b = colorsys.hls_to_rgb(h, li/100, si/100)
            cands.append((round(r*255), round(g*255), round(b*255)))
    printed = roundtrip_many(cands)
    best = None
    for c, p in zip(cands, printed):
        if dE(rgb2lab(c), rgb2lab(p)) > tol:     # must print true
            continue
        lab = rgb2lab(c)
        # most vivid, then closest to the original
        score = (chroma(lab), -dE(lab, olab))
        if best is None or score > best[0]:
            best = (score, c, p, lab)
    if not best: return None
    _, c, p, lab = best
    return {'chosen': hexcol, 'printable': rgb2hex(c), 'prints_as': rgb2hex(p),
            'shift_from_chosen': dE(lab, olab), 'chroma_kept': chroma(lab)/max(1e-6, chroma(olab))}

for h in (sys.argv[1:] or ['#ff9300', '#ff2600', '#00f900', '#fffb00']):
    r = best_printable(h)
    if not r: print(f"{h}: no faithful match found"); continue
    print(f"{r['chosen']}  ->  {r['printable']}   (prints as {r['prints_as']}, "
          f"moved dE {r['shift_from_chosen']:.1f} from your colour, "
          f"keeps {r['chroma_kept']*100:.0f}% of the vividness)")
