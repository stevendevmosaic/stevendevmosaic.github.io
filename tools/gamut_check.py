#!/usr/bin/env python3
"""Measure how far a colour shifts when printed: sRGB -> CMYK -> sRGB, reported
as Delta-E 1976. Uses the system Generic CMYK profile — indicative of a typical
press, not a substitute for your printer's own profile.

  under 2  : imperceptible shift — prints as you see it
  2 to 5   : noticeable if you compare side by side
  over 5   : obvious shift — the printed colour is not the one you chose
"""
from PIL import Image, ImageCms
import io, sys

SRGB = ImageCms.getOpenProfile("/System/Library/ColorSync/Profiles/sRGB Profile.icc")
CMYK = ImageCms.getOpenProfile("/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc")
to_cmyk = ImageCms.buildTransform(SRGB, CMYK, "RGB", "CMYK", renderingIntent=0)
to_rgb  = ImageCms.buildTransform(CMYK, SRGB, "CMYK", "RGB", renderingIntent=0)

def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb2lab(rgb):
    def lin(c):
        c /= 255.0
        return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    r, g, b = (lin(v) for v in rgb)
    X = 0.4124564*r + 0.3575761*g + 0.1804375*b
    Y = 0.2126729*r + 0.7151522*g + 0.0721750*b
    Z = 0.0193339*r + 0.1191920*g + 0.9503041*b
    Xn, Yn, Zn = 0.95047, 1.0, 1.08883
    eps, kap = 216/24389, 24389/27
    def f(t):
        return t**(1/3) if t > eps else (kap*t + 16)/116
    fx, fy, fz = f(X/Xn), f(Y/Yn), f(Z/Zn)
    return (116*fy - 16, 500*(fx - fy), 200*(fy - fz))

def roundtrip(hexcol):
    im = Image.new("RGB", (1, 1), hex2rgb(hexcol))
    out = ImageCms.applyTransform(ImageCms.applyTransform(im, to_cmyk), to_rgb)
    return out.getpixel((0, 0))

def deltaE(hexcol):
    a, b = rgb2lab(hex2rgb(hexcol)), rgb2lab(roundtrip(hexcol))
    return sum((x-y)**2 for x, y in zip(a, b))**0.5

def report(name, cols):
    print(f"\n{name}")
    worst = 0
    for label, h in cols:
        d = deltaE(h); worst = max(worst, d)
        rt = roundtrip(h)
        flag = "OK " if d < 2 else ("~  " if d < 5 else "XX ")
        print(f"  {flag} {label:<10} {h}  ->  #{rt[0]:02x}{rt[1]:02x}{rt[2]:02x}   dE {d:5.1f}")
    print(f"  worst shift: dE {worst:.1f}")
    return worst

report("CURRENT template colours", [
    ("orange", "#ff9300"), ("green", "#00f900"), ("yellow", "#fffb00"), ("red", "#ff2600")])
report("A — Muted original (same hues, pulled in-gamut)", [
    ("orange", "#d98324"), ("green", "#4c9a5a"), ("yellow", "#e3b53f"), ("red", "#c24230")])
report("B — Coastal (photo-derived)", [
    ("sand", "#c9a66b"), ("sea", "#3e7c8b"), ("sky", "#7fa8c4"), ("coral", "#c96f5a")])
report("C — Bold editorial", [
    ("red", "#d64545"), ("amber", "#e29c2e"), ("teal", "#2e8b7a"), ("blue", "#4a6fa5")])
