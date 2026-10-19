"""Chit's logo, drawn as vector shapes so it stays crisp at every size (16 px tray to 256 px).

Geometry and colours are measured from the brand artwork ("final logo chit.png"): a blue
open "C" arc around five rounded sound bars, on a dark tile (dark theme) or a white tile
with a hairline border (light theme). All coordinates are fractions of the tile size,
relative to its center.
"""

import math
import winreg

from PIL import Image, ImageDraw

BLUE = (0, 100, 253)
RED = (240, 66, 84)  # the arc while Chit is listening
INK = (10, 15, 20)  # dark tile / bars on the light tile
WHITE = (255, 255, 255)
BORDER = (216, 216, 220)

CORNER = 0.19  # tile corner radius
ARC_CENTER = (-0.118, 0.006)
ARC_RADIUS = 0.217  # to the middle of the stroke
ARC_STROKE = 0.060
ARC_END_DEG = 83.4  # the arc runs from +83.4 deg (bottom) round the left to -83.4 deg (top)
# (center x, width, top, bottom) of each bar
BARS = [
    (-0.228, 0.064, -0.039, 0.079),
    (-0.121, 0.080, -0.126, 0.137),
    (0.022, 0.084, -0.278, 0.274),
    (0.172, 0.085, -0.163, 0.176),
    (0.314, 0.084, -0.073, 0.086),
]


def system_theme():
    """'light' or 'dark', following the Windows taskbar/system colour setting."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        ) as k:
            return "light" if winreg.QueryValueEx(k, "SystemUsesLightTheme")[0] else "dark"
    except OSError:
        return "dark"


def app_icon(size=256, theme="dark", listening=False):
    ss = 4 if size >= 64 else 8  # supersample more at small sizes for clean edges
    n = size * ss
    pad = n * 0.03
    tile = n - 2 * pad
    cx = cy = n / 2
    # At tray sizes (16-24 px) thin strokes fade out: draw the mark larger and bolder.
    small = size <= 24
    grow, bold = (1.12, 1.3) if small else (1.0, 1.0)

    def P(x, y):
        return cx + x * tile * grow, cy + y * tile * grow

    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    light = theme == "light"
    box = (pad, pad, n - pad, n - pad)
    if light:
        border = max(ss, tile * 0.004)
        d.rounded_rectangle(box, radius=tile * CORNER, fill=BORDER)
        inner = tuple(v + (border if i < 2 else -border) for i, v in enumerate(box))
        d.rounded_rectangle(inner, radius=tile * CORNER - border, fill=WHITE)
    else:
        d.rounded_rectangle(box, radius=tile * CORNER, fill=INK)

    # Blue "C": the arc plus round caps at both ends.
    color = RED if listening else BLUE
    acx, acy = P(*ARC_CENTER)
    r, w = ARC_RADIUS * tile * grow, ARC_STROKE * tile * grow * bold
    d.arc(
        (acx - r - w / 2, acy - r - w / 2, acx + r + w / 2, acy + r + w / 2),
        start=ARC_END_DEG,
        end=360 - ARC_END_DEG,
        fill=color,
        width=round(w),
    )
    for deg in (ARC_END_DEG, -ARC_END_DEG):
        ex = acx + r * math.cos(math.radians(deg))
        ey = acy + r * math.sin(math.radians(deg))
        d.ellipse((ex - w / 2, ey - w / 2, ex + w / 2, ey + w / 2), fill=color)

    bar = INK if light else WHITE
    for x, bw, top, bottom in BARS:
        bw *= bold
        x0, y0 = P(x - bw / 2, top)
        x1, y1 = P(x + bw / 2, bottom)
        d.rounded_rectangle((x0, y0, x1, y1), radius=(x1 - x0) / 2, fill=bar)
    return img.resize((size, size), Image.LANCZOS)


def save_icon(path, theme="dark"):
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    app_icon(256, theme).save(
        path, format="ICO", sizes=[(s, s) for s in sizes], append_images=[app_icon(s, theme) for s in sizes]
    )
