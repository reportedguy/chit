"""Screenshot a top-level window by title. Usage: python scripts/snap_window.py "<title>" out.png"""

import ctypes
import sys
from ctypes import wintypes

from PIL import ImageGrab

ctypes.windll.shcore.SetProcessDpiAwareness(2)
user32 = ctypes.windll.user32
hwnd = user32.FindWindowW(None, sys.argv[1])
if not hwnd:
    sys.exit(f"window not found: {sys.argv[1]}")
r = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(r))
ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True).save(sys.argv[2])
print("saved", sys.argv[2])
