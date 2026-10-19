"""Open Chit's tray menu in-process (with a stand-in app) and screenshot it over a plain backdrop.
Usage: python scripts/preview_tray_menu.py out.png"""

import ctypes
import sys
import threading
import time
import tkinter as tk

ctypes.windll.shcore.SetProcessDpiAwareness(2)
from PIL import ImageGrab
from pynput.mouse import Button
from pynput.mouse import Controller as Mouse
from pystray._util import win32

from chit.tray import Tray

user32 = ctypes.windll.user32


class FakeSettings:
    values = {"cleanup": "smart", "language": "en", "mic": None, "sounds": True}

    def __getitem__(self, key):
        return self.values[key]


class FakeApp:
    recording = False
    settings = FakeSettings()

    def set_setting(self, key, value):
        pass

    def on_click(self):
        pass

    def device_summary(self):
        return "Speech on NPU · Cleanup on GPU"

    def quit(self):
        pass


out = sys.argv[1]
tray = Tray(FakeApp())
tray.start()

# A plain backdrop that this process owns, so the menu may open and the screenshot shows only Chit.
root = tk.Tk()
root.title("menu backdrop")
x0, y0, w, h = 200, 120, 640, 760
root.geometry(f"{w}x{h}+{x0}+{y0}")
root.configure(bg="#e9e9ec")
root.attributes("-topmost", True)


def run():
    time.sleep(1.5)
    mouse = Mouse()
    old = mouse.position
    mouse.position = (x0 + 40, y0 + 40)
    mouse.click(Button.left)  # make this process the foreground one
    time.sleep(0.4)
    deadline = time.time() + 5
    while time.time() < deadline and not getattr(tray.icon, "_menu_handle", None):
        time.sleep(0.1)
    # Tray menus open up and to the left of the cursor: anchor at the backdrop's bottom-right.
    mouse.position = (x0 + w - 30, y0 + h - 30)
    user32.PostMessageW(tray.icon._hwnd, win32.WM_NOTIFY, 0, win32.WM_RBUTTONUP)
    time.sleep(1.0)
    ImageGrab.grab(bbox=(x0, y0, x0 + w, y0 + h), all_screens=True).save(out)
    user32.keybd_event(0x1B, 0, 0, 0)  # Esc closes the menu
    user32.keybd_event(0x1B, 0, 2, 0)
    mouse.position = old
    time.sleep(0.3)
    tray.stop()
    root.after(0, root.destroy)


threading.Thread(target=run, daemon=True).start()
root.mainloop()
print("saved", out)
