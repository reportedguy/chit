"""Screenshot the live bar (Chit must be running) over a white window: idle and hover.
Usage: python scripts/snap_bar_on_white.py out_dir"""

import ctypes
import os
import sys
import time
import tkinter as tk

ctypes.windll.shcore.SetProcessDpiAwareness(2)
from PIL import ImageGrab  # noqa: E402
from pynput.mouse import Controller as Mouse  # noqa: E402

from chit.overlay import _monitor_of_focus  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
scale = ctypes.windll.user32.GetDpiForSystem() / 96
root = tk.Tk()
root.title("white backdrop")
_, info = _monitor_of_focus()
w = info.rcWork
root.geometry(f"{w.right - w.left}x{int(160 * scale)}+{w.left}+{w.bottom - int(160 * scale)}")
root.configure(bg="white")
mouse = Mouse()


def run():
    cx = (w.left + w.right) // 2
    box = (cx - int(140 * scale), w.bottom - int(50 * scale), cx + int(140 * scale), w.bottom)
    time.sleep(1.2)
    ImageGrab.grab(bbox=box, all_screens=True).save(os.path.join(out, "white_idle.png"))
    old = mouse.position
    mouse.position = (cx, w.bottom - int(14 * scale))
    time.sleep(1.0)
    ImageGrab.grab(bbox=box, all_screens=True).save(os.path.join(out, "white_hover.png"))
    mouse.position = old
    root.destroy()


root.after(100, lambda: __import__("threading").Thread(target=run, daemon=True).start())
root.mainloop()
print("saved to", out)
