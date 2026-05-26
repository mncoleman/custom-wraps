#!/usr/bin/env python3
"""Generate LevoAir custom wrap textures for the Tesla Model 3 (2024+ base).

Brand palette (from mncoleman/LevoAir):
  Primary gold  #E6B325
  Accent  gold  #F2A818
  Greys: stealth gunmetal / charcoal base with a "brand grey" look.

Each design fills the vehicle's UV panels (using a mask derived from the
official template) with a grey base + gold accents, places a gold drone icon
on the hood, and a "LevoAir" wordmark on the side door panels.

Run from repo root:  python3 levoair/generate.py
"""
import os, math
from collections import deque
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "model3-2024-base", "template.png")
EXAMPLE_DIR = os.path.join(ROOT, "model3-2024-base", "example")
OUT_DIR = os.path.join(ROOT, "levoair")
W = H = 1024

# ---- palette ------------------------------------------------------------
GOLD       = (230, 179, 37)    # #E6B325
GOLD_DEEP  = (242, 168, 24)    # #F2A818
GOLD_LIGHT = (247, 209, 110)
GREY_STEALTH = (74, 78, 84)    # gunmetal
GREY_CHARCOAL = (43, 46, 51)
GREY_LIGHT = (124, 130, 138)
GREY_DARK  = (28, 30, 34)
NEAR_BLACK = (18, 19, 22)

FONT_BOLD = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
FONT_OBL  = "/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf"

# Official LevoAir wordmark (downloaded from the brand site CDN, committed to brand/)
LOGO = os.path.join(OUT_DIR, "brand", "levoair_logo.png")

# ---- panel mask ---------------------------------------------------------
def build_panel_mask():
    cache = os.path.join(OUT_DIR, "_panel_mask.png")
    if os.path.exists(cache):
        return Image.open(cache).convert("L")
    tmpl = Image.open(TEMPLATE).convert("RGBA")
    px = tmpl.load()
    def light(p):
        r, g, b, a = p
        if a < 30:
            return True
        return (r + g + b) / 3 > 110
    ext = bytearray(W * H)
    dq = deque()
    for sx, sy in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        if light(px[sx, sy]):
            ext[sy * W + sx] = 1
            dq.append((sx, sy))
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not ext[ny * W + nx] and light(px[nx, ny]):
                ext[ny * W + nx] = 1
                dq.append((nx, ny))
    mask = Image.new("L", (W, H), 0)
    mp = mask.load()
    for y in range(H):
        base = y * W
        for x in range(W):
            if not ext[base + x]:
                mp[x, y] = 255
    mask.save(cache)
    return mask

# ---- helpers ------------------------------------------------------------
def vgrad(top, bottom):
    """Vertical gradient image."""
    g = Image.new("RGB", (1, H))
    gp = g.load()
    for y in range(H):
        t = y / (H - 1)
        gp[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return g.resize((W, H))

def carbon_texture(base, light, cell=10):
    """Subtle woven carbon-fibre look."""
    img = Image.new("RGB", (W, H), base)
    d = ImageDraw.Draw(img)
    for y in range(0, H, cell):
        for x in range(0, W, cell):
            shade = light if ((x // cell + y // cell) % 2 == 0) else base
            d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=shade)
    return img.filter(ImageFilter.GaussianBlur(1.1))

def diagonal_band(layer, x_center, width, color, slope=0.45, alpha=255):
    """Draw a diagonal band across the full canvas onto an RGBA layer."""
    d = ImageDraw.Draw(layer, "RGBA")
    half = width / 2
    pts_top_x = x_center - slope * 0
    # band defined by two parallel lines y = (x - c)/slope ; draw as polygon
    # build polygon from x at y=0 and y=H
    x_at_0 = x_center
    x_at_H = x_center + slope * H
    poly = [
        (x_at_0 - half, 0), (x_at_0 + half, 0),
        (x_at_H + half, H), (x_at_H - half, H),
    ]
    d.polygon(poly, fill=color + (alpha,))

def draw_drone(layer, cx, cy, R, ring_col, body_col, blade_col, stroke=None):
    """Top-view quadcopter drone centred at (cx,cy), overall radius R."""
    d = ImageDraw.Draw(layer, "RGBA")
    arm = R * 0.62           # distance to rotor hubs
    rotor_r = R * 0.40
    arm_w = max(4, int(R * 0.12))
    # diagonal arms
    for ang in (45, 135, 225, 315):
        ex = cx + arm * math.cos(math.radians(ang))
        ey = cy + arm * math.sin(math.radians(ang))
        d.line([(cx, cy), (ex, ey)], fill=body_col + (255,), width=arm_w)
    # rotors
    for ang in (45, 135, 225, 315):
        ex = cx + arm * math.cos(math.radians(ang))
        ey = cy + arm * math.sin(math.radians(ang))
        rb = [ex - rotor_r, ey - rotor_r, ex + rotor_r, ey + rotor_r]
        ring_w = max(3, int(R * 0.07))
        d.ellipse(rb, outline=ring_col + (255,), width=ring_w)
        # two blurred propeller blades
        for bang in (0, 90):
            ba = math.radians(bang + (20 if ang in (45, 225) else -20))
            bx = rotor_r * 0.82
            d.line([(ex - bx * math.cos(ba), ey - bx * math.sin(ba)),
                    (ex + bx * math.cos(ba), ey + bx * math.sin(ba))],
                   fill=blade_col + (210,), width=max(2, int(R * 0.05)))
        d.ellipse([ex - R * 0.06, ey - R * 0.06, ex + R * 0.06, ey + R * 0.06],
                  fill=ring_col + (255,))
    # central body
    bw = R * 0.30
    d.rounded_rectangle([cx - bw, cy - bw * 0.8, cx + bw, cy + bw * 0.8],
                        radius=R * 0.12, fill=body_col + (255,),
                        outline=ring_col + (255,), width=max(2, int(R * 0.05)))
    # camera / gimbal eye
    d.ellipse([cx - R * 0.13, cy - R * 0.13, cx + R * 0.13, cy + R * 0.13],
              fill=ring_col + (255,))
    d.ellipse([cx - R * 0.06, cy - R * 0.06, cx + R * 0.06, cy + R * 0.06],
              fill=(NEAR_BLACK) + (255,))

def fit_font(path, text, target_w, max_size=200):
    size = 12
    f = ImageFont.truetype(path, size)
    while size < max_size:
        nf = ImageFont.truetype(path, size + 2)
        w = nf.getbbox(text)[2] - nf.getbbox(text)[0]
        if w > target_w:
            break
        size += 2
        f = nf
    return f

def wordmark(layer, cx, cy, text, color, target_w, font_path=FONT_OBL,
             shadow=True, mirror=False):
    """Render LevoAir wordmark centred at (cx,cy)."""
    f = fit_font(font_path, text, target_w)
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tile = Image.new("RGBA", (tw + 20, th + 20), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    if shadow:
        td.text((10 - bb[0] + 2, 10 - bb[1] + 2), text, font=f, fill=(0, 0, 0, 150))
    td.text((10 - bb[0], 10 - bb[1]), text, font=f, fill=color + (255,))
    if mirror:
        tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
    layer.alpha_composite(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))

_LOGO_CACHE = {}
def _load_logo(tint=None):
    key = tint or "orig"
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    logo = Image.open(LOGO).convert("RGBA")
    if tint is not None:
        # recolour every visible pixel to a single brand colour, keep alpha
        r, g, b = tint
        px = logo.load()
        for y in range(logo.height):
            for x in range(logo.width):
                a = px[x, y][3]
                if a:
                    px[x, y] = (r, g, b, a)
    _LOGO_CACHE[key] = logo
    return logo

def place_logo(layer, cx, cy, target_w, mirror=False, tint=None, shadow=True):
    """Composite the official LevoAir wordmark, scaled to target_w, centred."""
    logo = _load_logo(tint)
    scale = target_w / logo.width
    tile = logo.resize((target_w, max(1, int(logo.height * scale))), Image.LANCZOS)
    if mirror:
        tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
    ox, oy = int(cx - tile.width / 2), int(cy - tile.height / 2)
    if shadow:
        sh = Image.new("RGBA", tile.size, (0, 0, 0, 0))
        sa = tile.split()[3].point(lambda v: int(v * 0.55))
        sh.putalpha(sa)
        layer.alpha_composite(sh, (ox + 2, oy + 2))
    layer.alpha_composite(tile, (ox, oy))

# ---- placement (from mask analysis) -------------------------------------
HOOD = (512, 272)            # teardrop centre
L_DOOR = (162, 432)          # left door panel centre
R_DOOR = (862, 432)          # right door panel centre
DOOR_W = 132

def finalize(design, name, mask):
    """Clip design (RGB) to panels over white, save texture + preview."""
    out = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    out.paste(design, (0, 0), mask)
    rgb = out.convert("RGB")
    path = os.path.join(EXAMPLE_DIR, name + ".png")
    rgb.save(path)
    print("wrote", path)

# ---- designs ------------------------------------------------------------
def design_stealth(mask):
    base = vgrad(GREY_STEALTH, GREY_CHARCOAL).convert("RGBA")
    # bold gold diagonal accent flowing across hood + body
    diagonal_band(base, 300, 70, GOLD_DEEP, slope=0.45)
    diagonal_band(base, 360, 26, GREY_DARK, slope=0.45)
    diagonal_band(base, 392, 50, GOLD, slope=0.45)
    drone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_drone(drone, *HOOD, 92, GOLD, GREY_DARK, GOLD_LIGHT)
    base.alpha_composite(drone)
    place_logo(base, *L_DOOR, 124, mirror=True)
    place_logo(base, *R_DOOR, 124)
    finalize(base, "LevoAir_Stealth_Grey", mask)

def design_gold_edge(mask):
    base = vgrad(GREY_CHARCOAL, GREY_DARK).convert("RGBA")
    # lower-body gold rocker accent (horizontal band low on the canvas)
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle([0, 690, W, 726], fill=GOLD + (255,))
    d.rectangle([0, 726, W, 736], fill=GOLD_DEEP + (255,))
    drone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_drone(drone, *HOOD, 96, GOLD, GREY_LIGHT, GOLD_LIGHT)
    base.alpha_composite(drone)
    place_logo(base, L_DOOR[0], 400, 130, mirror=True)
    place_logo(base, R_DOOR[0], 400, 130)
    finalize(base, "LevoAir_Gold_Edge", mask)

def design_carbon(mask):
    base = carbon_texture(GREY_DARK, (38, 41, 46)).convert("RGBA")
    # thin twin gold pinstripes running diagonally
    diagonal_band(base, 470, 7, GOLD, slope=0.18)
    diagonal_band(base, 492, 7, GOLD, slope=0.18)
    drone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_drone(drone, HOOD[0], HOOD[1], 96, GOLD, GREY_LIGHT, GOLD_LIGHT)
    base.alpha_composite(drone)
    place_logo(base, *L_DOOR, 124, mirror=True)
    place_logo(base, *R_DOOR, 124)
    finalize(base, "LevoAir_Carbon_Drone", mask)

def design_aerial(mask):
    # two-tone: light grey upper, charcoal lower, gold split line
    base = Image.new("RGBA", (W, H), GREY_LIGHT + (255,))
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle([0, 470, W, H], fill=GREY_CHARCOAL + (255,))
    d.rectangle([0, 458, W, 470], fill=GOLD + (255,))
    d.rectangle([0, 470, W, 478], fill=GOLD_DEEP + (255,))
    drone = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_drone(drone, *HOOD, 94, GOLD_DEEP, (60, 64, 70), GREY_DARK)
    base.alpha_composite(drone)
    place_logo(base, L_DOOR[0], 540, 124, mirror=True)
    place_logo(base, R_DOOR[0], 540, 124)
    finalize(base, "LevoAir_Aerial_TwoTone", mask)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    mask = build_panel_mask()
    design_stealth(mask)
    design_gold_edge(mask)
    design_carbon(mask)
    design_aerial(mask)

if __name__ == "__main__":
    main()
