"""Render every state of the bottom bar over white and dark backgrounds into one image.
Usage: python scripts/preview_bar.py out.png"""

import ctypes
import sys
from collections import deque

ctypes.windll.shcore.SetProcessDpiAwareness(2)
from PIL import Image, ImageDraw  # noqa: E402

from chit import overlay  # noqa: E402


class FakeApp:
    levels = deque([0.02, 0.05, 0.09, 0.04, 0.12, 0.07, 0.03], maxlen=32)

    def ui_state(self):
        return "idle", False

    def on_click(self):
        pass


o = overlay.Overlay(FakeApp())
o.root.withdraw()
o.bars = [0.25, 0.6, 1.0, 0.45, 0.85, 0.5, 0.2]
states = []
for name, state, hf, hover, size in (
    ("idle", "idle", False, False, overlay.IDLE),
    ("hover", "idle", False, True, None),
    ("listening", "listening", False, False, overlay.LISTEN),
    ("hands-free", "listening", True, False, overlay.LISTEN),
    ("thinking", "thinking", False, False, overlay.THINK),
):
    o.size = list(size or o._target("idle", True))
    states.append((name, o.render(state, hf, hover)))
w, h = states[0][1].size
sheet = Image.new("RGBA", (w * 2 + 3 * w, (h + 20) * len(states)), (255, 255, 255, 255))
d = ImageDraw.Draw(sheet)
for i, (name, img) in enumerate(states):
    y = i * (h + 20)
    d.text((4, y + 2), name, fill=(0, 0, 0, 255))
    white = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    white.alpha_composite(img)
    dark = Image.new("RGBA", (w, h), (32, 33, 36, 255))
    dark.alpha_composite(img)
    sheet.paste(white, (0, y + 16))
    sheet.paste(dark, (w, y + 16))
    # 3x zoom of the middle of the white version, to inspect the edges pixel by pixel.
    zw, zh = w // 3, h // 3
    zoom = white.crop((w // 2 - zw // 2, h - zh, w // 2 + zw // 2, h)).resize((zw * 3, zh * 3), Image.NEAREST)
    sheet.paste(zoom, (2 * w + 10, y + 16))
sheet.save(sys.argv[1])
print("saved", sys.argv[1])
