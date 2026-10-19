"""End-to-end test of the real app: Caps Lock gestures -> cleaned text pasted into a focused window.

Starts Chit with test hooks (accepts simulated keys; a WAV file stands in for the mic), drives it
with real keyboard/mouse events, and checks what lands in a Tk text box.

Usage: python scripts/e2e_app.py [path\\to\\Chit.exe]      (default: run from source)
Needs a desktop session, the models downloaded (run Chit once), and no other Chit running.
Screenshots of the bar go to build/e2e/.
"""

import ctypes
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk

ctypes.windll.shcore.SetProcessDpiAwareness(2)
from PIL import ImageGrab
from pynput.keyboard import Controller, Key
from pynput.mouse import Button
from pynput.mouse import Controller as Mouse

from chit.overlay import _monitor_of_focus
from chit.paths import LOG_PATH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, "scripts", "data", "en_fillers.wav")  # 14.3 s
OUT = os.path.join(ROOT, "build", "e2e")
os.makedirs(OUT, exist_ok=True)
user32 = ctypes.windll.user32
scale = user32.GetDpiForSystem() / 96

exe = sys.argv[1] if len(sys.argv) > 1 else None
pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
cmd = [exe] if exe else [pythonw, "-m", "chit"]
cmd += ["--background", "--test-injected-keys", "--test-audio", WAV]


def _log_lines():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, encoding="utf-8") as f:
        return f.readlines()


mark = len(_log_lines())


def log_tail():
    return "".join(_log_lines()[mark:])


proc = subprocess.Popen(cmd)
deadline = time.time() + 180
while time.time() < deadline and "Speech model ready" not in log_tail():
    time.sleep(0.5)
while time.time() < deadline and "Cleanup model" not in log_tail():
    time.sleep(0.5)
time.sleep(1)

kb, mouse = Controller(), Mouse()
root = tk.Tk()
root.title("Chit E2E")
root.geometry("760x220+120+120")
root.attributes("-topmost", True)
txt = tk.Text(root, wrap="word", font=("Segoe UI", 11))
txt.pack(fill="both", expand=True)
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def text():
    return txt.get("1.0", "end").strip()


def clear():
    root.after(0, lambda: txt.delete("1.0", "end"))
    time.sleep(0.3)


def bar_box():
    _, info = _monitor_of_focus()
    w = info.rcWork
    cx = (w.left + w.right) // 2
    return (
        cx,
        w.bottom - int(14 * scale),
        (cx - int(130 * scale), w.bottom - int(48 * scale), cx + int(130 * scale), w.bottom),
    )


def snap(name):
    ImageGrab.grab(bbox=bar_box()[2], all_screens=True).save(os.path.join(OUT, f"{name}.png"))


def caps_tap(hold=0.08):
    kb.press(Key.caps_lock)
    time.sleep(hold)
    kb.release(Key.caps_lock)


def wait_text(timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        if text():
            return True
        time.sleep(0.1)
    return False


def focused():
    return user32.GetForegroundWindow() == user32.GetParent(root.winfo_id())


def ensure_focus():
    """Click into the text box: a real click is the only reliable way to put keyboard focus
    inside it (an activated Tk window alone keeps focus on its frame, which ignores Ctrl+V).
    Never test without it, or the app's pastes could land in some other window."""
    x, y = txt.winfo_rootx() + 40, txt.winfo_rooty() + 40
    old = mouse.position
    mouse.position = (x, y)
    mouse.click(Button.left)
    mouse.position = old
    time.sleep(0.4)
    if not focused():
        root.after(0, root.destroy)
        raise SystemExit("Could not focus the test window; aborting so nothing is typed elsewhere")


focus_trace = []
armed = threading.Event()  # set once the test window has focus
aborted = []


def trace_focus():
    """Record every change of the foreground window, and abort the moment another app takes
    focus: from then on Chit's pastes would land in that app instead of the test window."""
    last = None
    while True:
        hwnd = user32.GetForegroundWindow()
        title, cls = ctypes.create_unicode_buffer(128), ctypes.create_unicode_buffer(128)
        user32.GetWindowTextW(hwnd, title, 128)
        user32.GetClassNameW(hwnd, cls, 128)
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        d = f"{title.value!r} {cls.value} pid={pid.value}"
        if d != last:
            focus_trace.append(f"{time.strftime('%H:%M:%S')} {d}")
            last = d
        if armed.is_set() and pid.value not in (0, os.getpid()) and not aborted:
            aborted.append(f"another app took focus: {d}")
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            root.after(0, root.destroy)
            return
        time.sleep(0.02)


def driver():
    threading.Thread(target=trace_focus, daemon=True).start()
    time.sleep(1)
    ensure_focus()
    armed.set()
    caps_before = user32.GetKeyState(0x14) & 1
    import pyperclip

    pyperclip.copy("USER CLIPBOARD")
    snap("1_idle")

    # 1. Hold Caps Lock for the whole recording, release -> cleaned text.
    kb.press(Key.caps_lock)
    time.sleep(5)
    snap("2_listening")
    time.sleep(10)
    kb.release(Key.caps_lock)
    released = time.time()
    time.sleep(0.45)
    snap("3_thinking")
    got = wait_text()
    latency = time.time() - released
    check("hold: text pasted", got, text())
    check("hold: fillers removed", got and not re.search(r"(?i)\b(um|uh)\b|, you know,|, like,", text()), text())
    check("hold: self-correction applied", "wednesday" in text().lower() and "tuesday" not in text().lower(), text())
    check(f"hold: release-to-text latency {latency:.2f}s", latency < 3.0)
    check("hold: Caps Lock unchanged afterwards", (user32.GetKeyState(0x14) & 1) == caps_before)
    clear()

    # 2. A quick tap is a normal Caps Lock: it toggles at once and nothing is dictated.
    ensure_focus()
    caps = lambda: user32.GetKeyState(0x14) & 1  # noqa: E731
    before = caps()
    caps_tap()
    time.sleep(0.05)
    kb.type("abc")  # typed immediately after the tap
    time.sleep(0.3)
    check("tap: Caps Lock toggled", caps() != before)
    check("tap: letters typed right after are in the new case", text() == ("ABC" if not before else "abc"), text())
    time.sleep(3)
    check("tap: nothing dictated", text() in ("ABC", "abc"), text())
    caps_tap()  # a second, separate tap toggles back
    time.sleep(1)
    check("second tap: Caps Lock restored", caps() == before)
    clear()

    # 3. Double-tap -> hands-free (Caps Lock unchanged); double-tap again -> finish.
    ensure_focus()
    caps_tap()
    time.sleep(0.12)
    caps_tap()
    time.sleep(6)
    snap("4_hands_free")
    check("double-tap: listening", "Dictation cancelled" not in log_tail()[-300:])
    check("double-tap: Caps Lock unchanged", caps() == before)
    time.sleep(9)
    caps_tap()
    time.sleep(0.12)
    caps_tap()
    check("double-tap again: text pasted", wait_text(), text())
    clear()

    # 4. Esc cancels hands-free: nothing pasted.
    ensure_focus()
    caps_tap()
    time.sleep(0.12)
    caps_tap()
    time.sleep(4)
    kb.press(Key.esc)
    kb.release(Key.esc)
    time.sleep(4)
    check("Esc: dictation cancelled, nothing pasted", text() == "" and "Dictation cancelled" in log_tail(), text())

    # 5. Clicking the bar starts hands-free without stealing focus; clicking again finishes.
    ensure_focus()
    cx, cy, _ = bar_box()
    old = mouse.position
    mouse.position = (cx, cy)
    time.sleep(0.6)
    snap("5_hover")
    mouse.click(Button.left)
    time.sleep(1)
    check("click: focus stays in the text box", focused())
    time.sleep(13)
    mouse.click(Button.left)
    mouse.position = old
    check("click again: text pasted", wait_text(), text())
    check("focus still in the text box", focused())

    time.sleep(1)  # the app restores the clipboard 0.3 s after pasting
    check("Caps Lock state unchanged", caps_before == (user32.GetKeyState(0x14) & 1))
    check("clipboard restored", pyperclip.paste() == "USER CLIPBOARD")
    time.sleep(1)
    snap("6_idle_after")
    armed.clear()  # the test is done: closing its window hands focus back, which is expected
    root.after(0, root.destroy)


threading.Thread(target=driver, daemon=True).start()
root.mainloop()
subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)

if aborted:
    print(f"ABORTED: {aborted[0]}. Chit was stopped so nothing more could be typed there.")
    print("Re-run without touching the PC (about 3 minutes).")
    sys.exit(2)
failed = 0
for name, ok, detail in results:
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not ok else ""))
print(f"\n{len(results) - failed}/{len(results)} passed. Screenshots in {OUT}")
print("--- focus changes ---")
print("\n".join(focus_trace))
print("--- app log ---")
print(log_tail())
sys.exit(1 if failed else 0)
