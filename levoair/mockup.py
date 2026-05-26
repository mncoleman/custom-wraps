#!/usr/bin/env python3
"""Render side-profile car mockups so each LevoAir wrap can be previewed
'on a car'. Produces levoair/mockups/<name>.png for every design.

These are stylised Tesla Model 3 side-profile previews (not a photoreal
render) intended to communicate colour, accent placement, drone and logo.

Run from repo root:  python3 levoair/mockup.py
"""
import os, math
from PIL import Image, ImageDraw, ImageFilter
import generate as G   # reuse palette + drone + logo helpers

OUT = os.path.join(G.OUT_DIR, "mockups")
W, H = 1280, 520
GROUND = 372
SCALE = 1  # canvas already final size

# ---- Model 3 side-profile silhouette ------------------------------------
BODY = [
    (150, 360), (118, 332), (150, 300), (250, 286), (360, 270),
    (430, 250), (505, 180), (610, 158), (760, 156), (880, 178),
    (985, 232), (1070, 262), (1120, 300), (1132, 338), (1118, 360),
]
ROCKER_Y = 360
GREENHOUSE = [  # window glass area
    (470, 196), (548, 186), (660, 178), (770, 178), (852, 196),
    (835, 250), (548, 250), (500, 250),
]
WHEELS = [(330, GROUND), (955, GROUND)]
WHEEL_R = 82
ARCH_R = 92


def base_fill(design):
    """Return an RGB image (W×H) of the paint to clip into the body."""
    if design == "stealth":
        return G.vgrad(G.GREY_STEALTH, G.GREY_CHARCOAL).resize((W, H))
    if design == "gold_edge":
        return G.vgrad(G.GREY_CHARCOAL, G.GREY_DARK).resize((W, H))
    if design == "carbon":
        return G.carbon_texture_wh(W, H, G.GREY_DARK, (38, 41, 46)) \
            if hasattr(G, "carbon_texture_wh") else carbon_wh()
    if design == "aerial":
        img = Image.new("RGB", (W, H), G.GREY_LIGHT)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 270, W, H], fill=G.GREY_CHARCOAL)
        d.rectangle([0, 262, W, 270], fill=G.GOLD)
        d.rectangle([0, 270, W, 276], fill=G.GOLD_DEEP)
        return img
    return Image.new("RGB", (W, H), G.GREY_STEALTH)


def carbon_wh():
    img = Image.new("RGB", (W, H), G.GREY_DARK)
    d = ImageDraw.Draw(img)
    cell = 10
    for y in range(0, H, cell):
        for x in range(0, W, cell):
            if ((x // cell + y // cell) % 2 == 0):
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(38, 41, 46))
    return img.filter(ImageFilter.GaussianBlur(1.0))


def body_mask():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.polygon(BODY, fill=255)
    # subtract wheel arches
    for (wx, wy) in WHEELS:
        d.ellipse([wx - ARCH_R, wy - ARCH_R, wx + ARCH_R, wy + ARCH_R], fill=0)
    return m


def accents(layer, design):
    d = ImageDraw.Draw(layer, "RGBA")
    if design == "stealth":
        # diagonal gold swoosh along the lower body
        poly = [(150, 352), (1118, 300), (1118, 330), (150, 372)]
        d.polygon(poly, fill=G.GOLD + (255,))
        d.line([(150, 300), (1100, 250)], fill=G.GOLD_DEEP + (255,), width=6)
    elif design == "gold_edge":
        d.rectangle([150, 344, 1120, 360], fill=G.GOLD + (255,))
        d.rectangle([150, 360, 1120, 366], fill=G.GOLD_DEEP + (255,))
    elif design == "carbon":
        d.line([(150, 318), (1118, 286)], fill=G.GOLD + (255,), width=4)
        d.line([(150, 330), (1118, 298)], fill=G.GOLD + (255,), width=4)
    elif design == "aerial":
        pass  # gold split line already in base_fill


def render(design, title, outname):
    canvas = Image.new("RGBA", (W, H), (245, 246, 248, 255))
    # soft floor gradient
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fld = ImageDraw.Draw(fl)
    fld.rectangle([0, GROUND + 60, W, H], fill=(225, 227, 231, 255))
    canvas.alpha_composite(fl)

    # paint clipped to body
    paint = base_fill(design).convert("RGBA")
    acc_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    accents(acc_layer, design)
    paint.alpha_composite(acc_layer)
    bm = body_mask()
    body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    body.paste(paint, (0, 0), bm)

    # subtle body shading (top highlight / bottom shadow) within mask
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.polygon(BODY, outline=(255, 255, 255, 60), width=3)
    body.alpha_composite(Image.composite(shade, Image.new("RGBA", (W, H), (0,0,0,0)), bm))

    canvas.alpha_composite(body)

    d = ImageDraw.Draw(canvas, "RGBA")
    # glass
    d.polygon(GREENHOUSE, fill=(20, 22, 26, 255))
    d.line([(548, 186), (548, 250)], fill=(60, 64, 70, 255), width=3)  # B-pillar
    d.line([(770, 178), (760, 250)], fill=(60, 64, 70, 255), width=3)  # C-pillar

    # wheels
    for (wx, wy) in WHEELS:
        d.ellipse([wx - WHEEL_R, wy - WHEEL_R, wx + WHEEL_R, wy + WHEEL_R],
                  fill=(16, 17, 20, 255))
        d.ellipse([wx - WHEEL_R + 6, wy - WHEEL_R + 6, wx + WHEEL_R - 6, wy + WHEEL_R - 6],
                  fill=(28, 30, 34, 255))
        # rim spokes (gold)
        rr = WHEEL_R - 24
        d.ellipse([wx - rr, wy - rr, wx + rr, wy + rr], fill=(48, 51, 56, 255))
        for a in range(0, 360, 36):
            ex = wx + rr * math.cos(math.radians(a))
            ey = wy + rr * math.sin(math.radians(a))
            d.line([(wx, wy), (ex, ey)], fill=G.GOLD + (255,), width=4)
        d.ellipse([wx - 14, wy - 14, wx + 14, wy + 14], fill=(20, 22, 26, 255))
        d.ellipse([wx - 14, wy - 14, wx + 14, wy + 14], outline=G.GOLD + (255,), width=3)

    # door handles + headlight/taillight hints
    d.line([(560, 232), (610, 230)], fill=(150, 155, 162, 255), width=4)
    d.line([(720, 230), (770, 232)], fill=(150, 155, 162, 255), width=4)
    d.ellipse([150, 312, 196, 330], fill=(210, 214, 220, 200))      # headlight
    d.polygon([(1060, 268), (1118, 276), (1116, 292), (1060, 286)],
              fill=(150, 40, 44, 220))                               # taillight

    # ----- LevoAir logo on the door -----
    G.place_logo(canvas, 660, 305, 230, mirror=False, shadow=True)
    # ----- gold drone on the front fender / hood shoulder -----
    drone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    body_col = G.GREY_DARK if design != "aerial" else (60, 64, 70)
    G.draw_drone(drone, 250, 300, 40, G.GOLD, body_col, G.GOLD_LIGHT)
    canvas.alpha_composite(drone)

    # reflection
    refl = canvas.crop((0, 0, W, GROUND + 60)).transpose(Image.FLIP_TOP_BOTTOM)
    refl.putalpha(refl.split()[3].point(lambda v: int(v * 0.18)))
    canvas.alpha_composite(refl, (0, GROUND + 60))

    # title bar
    d = ImageDraw.Draw(canvas, "RGBA")
    from PIL import ImageFont
    f = ImageFont.truetype(G.FONT_BOLD, 30)
    d.text((40, 30), title, font=f, fill=(40, 43, 48, 255))
    fs = ImageFont.truetype(G.FONT_BOLD, 16)
    d.text((42, 70), "Tesla Model 3 (2024+)  -  LevoAir custom wrap", font=fs,
           fill=(120, 125, 132, 255))

    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, outname + ".png")
    canvas.convert("RGB").save(p)
    print("wrote", p)


def main():
    render("stealth",  "Stealth Grey",   "LevoAir_Stealth_Grey")
    render("gold_edge", "Gold Edge",     "LevoAir_Gold_Edge")
    render("carbon",   "Carbon Drone",   "LevoAir_Carbon_Drone")
    render("aerial",   "Aerial Two-Tone", "LevoAir_Aerial_TwoTone")


if __name__ == "__main__":
    main()
