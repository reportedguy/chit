"""System-tray icon and menu."""

import os
import subprocess
import sys
import threading
import webbrowser
import winreg

from .icon import app_icon, system_theme
from .log import log
from .paths import APP_NAME, FROZEN, LOG_PATH, asset

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTHOR = "ReportedGuy"
AUTHOR_URL = "https://reportedguy.com"
STAMP_LABEL = f"Built by {AUTHOR}"
STAMP_HEIGHT = 40  # logical pixels


def launch_command():
    """How Windows should start Chit at login (the installer writes the same value)."""
    if FROZEN:
        return subprocess.list2cmdline([sys.executable, "--background"])
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return subprocess.list2cmdline([pyw, "-m", "chit", "--background"])


def start_at_login():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_start_at_login(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except OSError:
                pass


def promote_icon():
    """Show the tray icon on the taskbar instead of the hidden overflow (Windows 11)."""
    exe_name = os.path.basename(sys.executable).lower()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\NotifyIconSettings") as k:
            for i in range(winreg.QueryInfoKey(k)[0]):
                with winreg.OpenKey(k, winreg.EnumKey(k, i), 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as s:
                    try:
                        exe = winreg.QueryValueEx(s, "ExecutablePath")[0].lower()
                        tip = str(winreg.QueryValueEx(s, "InitialTooltip")[0]).lower()
                    except OSError:
                        continue
                    if exe.endswith(exe_name) and (FROZEN or "chit" in tip):
                        winreg.SetValueEx(s, "IsPromoted", 0, winreg.REG_DWORD, 1)
    except OSError as e:
        log(f"Could not pin tray icon: {e}")


def _stamp_bitmap():
    """The author's face cutout, sized for the menu, as a native bitmap (or None)."""
    import ctypes

    from PIL import Image

    from .overlay import hbitmap_from_image

    try:
        height = round(STAMP_HEIGHT * ctypes.windll.user32.GetDpiForSystem() / 96)
        img = Image.open(asset("author.png")).convert("RGBA")
        img = img.resize((round(img.width * height / img.height), height), Image.LANCZOS)
        return hbitmap_from_image(img)
    except Exception as e:
        log(f"Author stamp unavailable: {e}")
        return None


def _icon_class():
    """pystray's Windows icon, with the author's face on the "Built by" menu item."""
    from pystray import _win32
    from pystray._util import win32

    class StampedIcon(_win32.Icon):
        stamp = None

        def _create_menu_item(self, descriptor, callbacks):
            info = super()._create_menu_item(descriptor, callbacks)
            if self.stamp and getattr(descriptor, "text", None) == STAMP_LABEL:
                info.fMask |= win32.MIIM_BITMAP
                info.hbmpItem = self.stamp
            return info

    StampedIcon.stamp = _stamp_bitmap()
    return StampedIcon


class Tray:
    def __init__(self, app):
        from pystray import Menu
        from pystray import MenuItem as Item

        self.app = app
        s = app.settings

        def radio(key, value, label):
            return Item(label, lambda: app.set_setting(key, value), radio=True, checked=lambda item: s[key] == value)

        def mic_items():
            from .audio import input_devices

            items = [
                Item(
                    "System default",
                    lambda: app.set_setting("mic", None),
                    radio=True,
                    checked=lambda item: s["mic"] is None,
                )
            ]
            for _, name in input_devices():
                items.append(
                    Item(
                        name,
                        (lambda n: lambda: app.set_setting("mic", n))(name),
                        radio=True,
                        checked=(lambda n: lambda item: s["mic"] == n)(name),
                    )
                )
            return items

        menu = Menu(
            Item(STAMP_LABEL, lambda: webbrowser.open(AUTHOR_URL)),
            Menu.SEPARATOR,
            Item(
                lambda item: "Stop dictation" if app.recording else "Start dictation",
                lambda: app.on_click(),
                default=True,
            ),
            Menu.SEPARATOR,
            Item(
                "Cleanup",
                Menu(
                    radio("cleanup", "smart", "Smart (AI rewrite)"),
                    radio("cleanup", "light", "Light (remove fillers)"),
                    radio("cleanup", "off", "Off (exact words)"),
                ),
            ),
            Item(
                "Language",
                Menu(
                    radio("language", "en", "English"),
                    radio("language", "hi", "Hindi"),
                    radio("language", "auto", "Auto-detect (may switch languages)"),
                ),
            ),
            Item(
                "Hold time",
                Menu(
                    radio("hold_ms", 300, "Fast (300 ms)"),
                    radio("hold_ms", 400, "Normal (400 ms)"),
                    radio("hold_ms", 600, "Relaxed (600 ms)"),
                ),
            ),
            Item("Microphone", Menu(mic_items)),
            Item("Sounds", lambda: app.set_setting("sounds", not s["sounds"]), checked=lambda item: s["sounds"]),
            Item(
                "Start at login",
                lambda: set_start_at_login(not start_at_login()),
                checked=lambda item: start_at_login(),
            ),
            Menu.SEPARATOR,
            Item(lambda item: app.device_summary(), None, enabled=False),
            Item("Open log", lambda: os.startfile(LOG_PATH)),
            Item("Quit Chit", lambda: app.quit()),
        )
        self.icon = _icon_class()(APP_NAME, app_icon(64, system_theme()), self._title(False), menu=menu)
        self.listening = None

    @staticmethod
    def _title(listening):
        return f"{APP_NAME}: listening..." if listening else f"{APP_NAME}: hold Caps Lock to talk"

    def set_listening(self, listening):
        if listening != self.listening:
            self.listening = listening
            self.icon.icon = app_icon(64, system_theme(), listening)
            self.icon.title = self._title(listening)

    def start(self, notify=None):
        def setup(icon):
            icon.visible = True
            if notify:
                icon.notify(notify, APP_NAME)
            threading.Timer(3.0, promote_icon).start()

        threading.Thread(target=self.icon.run, kwargs={"setup": setup}, daemon=True).start()

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass
