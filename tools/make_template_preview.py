#!/usr/bin/env python3
"""
Generate a preview thumbnail for a Mosaic Collage Maker template (.json).

Templates contain no photos, so this draws the *design*: photo frames as muted
placeholder blocks, text boxes with their real background colour and title text.
The result shows someone what layout they're downloading.

Usage:
    python3 tools/make_template_preview.py templates/my-template.json
    python3 tools/make_template_preview.py templates/my-template.json --page 1 --width 1400

Writes <same-name>.jpg next to the .json.
"""
import json, sys, argparse, os
from PIL import Image, ImageDraw, ImageFont

# Muted placeholder tones — clearly stand-ins, not pretending to be real photos.
PLACEHOLDERS = ["#6b7f99", "#7f9e8e", "#a68b7f", "#8e7f9e", "#9e9178", "#7f8f9e",
                "#99857f", "#7f998f", "#8a8f9e", "#9e8f7f"]


def font(px, bold=False):
    paths = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold
             else ["/System/Library/Fonts/Supplemental/Arial.ttf"]) + \
            ["/System/Library/Fonts/Helvetica.ttc"]
    for p in paths:
        try:
            return ImageFont.truetype(p, px)
        except Exception:
            pass
    return ImageFont.load_default()


def page_bg(colour):
    if not colour or colour == "black":
        return (17, 17, 17)
    if colour == "white":
        return (255, 255, 255)
    c = colour.lstrip("#")
    if len(c) == 6:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return (17, 17, 17)


def render(path, page_index=0, out_width=1200):
    data = json.load(open(path, encoding="utf-8"))
    pages = data.get("pages", [])
    if not pages:
        raise SystemExit("no pages in template")
    p = pages[min(page_index, len(pages) - 1)]

    pw, ph = p["pw"], p["ph"]
    s = out_width / pw
    W, H = out_width, max(1, round(ph * s))
    im = Image.new("RGB", (W, H), page_bg(data.get("bgColour")))
    d = ImageDraw.Draw(im, "RGBA")

    # photo frames
    for i, c in enumerate(p.get("cells", [])):
        x0, y0 = round(c["x"] * s), round(c["y"] * s)
        x1, y1 = round((c["x"] + c["w"]) * s), round((c["y"] + c["h"]) * s)
        d.rectangle([x0, y0, x1, y1], fill=PLACEHOLDERS[i % len(PLACEHOLDERS)])

    # text boxes — real background colour, plus the title so the design reads
    for t in p.get("texts", []):
        x0, y0 = round(t["x"] * s), round(t["y"] * s)
        x1, y1 = round((t["x"] + t["w"]) * s), round((t["y"] + t["h"]) * s)
        bg = t.get("bgColour")
        if bg and bg != "none":
            c = bg.lstrip("#")
            rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
            op = t.get("bgOpacity", 0.8)
            d.rectangle([x0, y0, x1, y1], fill=rgb + (int(op * 255),))
        label = (t.get("titleText") or "").strip() or (t.get("text") or "").strip()
        if label:
            # Size the label from the BOX, not the stored titleSize: text sizes are
            # still held in legacy screen-pixel units, which don't translate to a
            # thumbnail. Fitting to the box gives a readable, representative preview.
            box_w, box_h = max(1, x1 - x0), max(1, y1 - y0)
            size = max(9, round(box_h * 0.42))
            f = font(size, bold=bool(t.get("titleBold")))
            while size > 9 and d.textlength(label, font=f) > box_w * 0.88:
                size -= 1
                f = font(size, bold=bool(t.get("titleBold")))
            col = t.get("colour") or "#ffffff"
            cc = col.lstrip("#")
            rgb = tuple(int(cc[i:i + 2], 16) for i in (0, 2, 4)) if len(cc) == 6 else (255, 255, 255)
            tw = d.textlength(label, font=f)
            tx = x0 + max(0, (box_w - tw) / 2)
            ty = y0 + max(0, (box_h - size * 1.2) / 2)
            d.text((tx, ty), label, font=f, fill=rgb)

    out = os.path.splitext(path)[0] + ".jpg"
    im.save(out, "JPEG", quality=86)
    print("wrote %s  (%dx%d, from page %d of %d)" % (out, W, H, page_index + 1, len(pages)))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--width", type=int, default=1200)
    a = ap.parse_args()
    render(a.template, a.page, a.width)
