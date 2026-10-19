"""Put text into whatever app has keyboard focus."""

import ctypes
import time

user32 = ctypes.windll.user32
# Classic consoles mangle clipboard pastes of long text less reliably than typed input.
_TYPE_CLASSES = {"ConsoleWindowClass"}


def _foreground_class():
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(user32.GetForegroundWindow(), buf, 256)
    return buf.value


class Inserter:
    def __init__(self):
        from pynput.keyboard import Controller, Key

        self.kb, self.Key = Controller(), Key

    def insert(self, text):
        if not text:
            return
        if _foreground_class() in _TYPE_CLASSES:
            self.kb.type(text)
            return
        import pyperclip

        try:
            saved = pyperclip.paste()
        except Exception:
            saved = None
        pyperclip.copy(text)
        with self.kb.pressed(self.Key.ctrl):
            self.kb.tap("v")
        # Give the target app time to read the clipboard before restoring it.
        time.sleep(0.3)
        if saved is not None:
            try:
                pyperclip.copy(saved)
            except Exception:
                pass
