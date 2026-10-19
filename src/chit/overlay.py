"""The small bar at the bottom center of the screen.

idle      a thin pill; hover it for a hint; click it to start hands-free dictation
listening a small pill with a live audio graph (a red dot when hands-free)
thinking  three pulsing dots while the last phrase is transcribed and cleaned up
message   a short note ("Starting up...", "No microphone") that fades back to idle

Drawn as a per-pixel-alpha layered window (UpdateLayeredWindow): edges are properly
anti-aliased against whatever is behind them, with a soft shadow so the dark pill reads
on white pages and a faint light rim so it reads on dark ones. Fully transparent pixels
are click-through, the window never takes focus (clicks don't pull focus from the app
you're typing in), and it follows the monitor of the focused window.
"""

import ctypes
import math
import time
import tkinter as tk
from ctypes import wintypes

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TOOLWINDOW, WS_EX_APPWINDOW, WS_EX_NOACTIVATE = 0x80000, 0x80, 0x40000, 0x08000000
ULW_ALPHA, AC_SRC_ALPHA = 0x2, 0x1
SS = 3  # supersampling for smooth shapes

PILL = (24, 24, 28, 238)
RIM = (255, 255, 255, 34)  # hairline highlight: defines the edge on dark backgrounds
ERROR_PILL = (150, 30, 44, 240)
TEXT = (240, 240, 244, 255)
RED = (240, 72, 88, 255)
SHADOW_ALPHA = 0.30  # soft drop shadow: defines the edge on light backgrounds

# Pill sizes in logical pixels (width, height).
IDLE = (36.0, 5.0)
LISTEN = (64.0, 20.0)
THINK = (44.0, 20.0)
BARS = 7

for fn, res, args in (
    (user32.GetDC, wintypes.HDC, [wintypes.HWND]),
    (user32.ReleaseDC, ctypes.c_int, [wintypes.HWND, wintypes.HDC]),
    (user32.GetParent, wintypes.HWND, [wintypes.HWND]),
    (user32.GetWindowLongW, ctypes.c_long, [wintypes.HWND, ctypes.c_int]),
    (user32.SetWindowLongW, ctypes.c_long, [wintypes.HWND, ctypes.c_int, ctypes.c_long]),
    (gdi32.CreateCompatibleDC, wintypes.HDC, [wintypes.HDC]),
    (gdi32.DeleteDC, wintypes.BOOL, [wintypes.HDC]),
    (gdi32.SelectObject, wintypes.HGDIOBJ, [wintypes.HDC, wintypes.HGDIOBJ]),
    (gdi32.DeleteObject, wintypes.BOOL, [wintypes.HGDIOBJ]),
):
    fn.restype, fn.argtypes = res, args


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_byte),
    ]


gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(BITMAPINFOHEADER),
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND,
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    ctypes.POINTER(wintypes.SIZE),
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    wintypes.COLORREF,
    ctypes.POINTER(BLENDFUNCTION),
    wintypes.DWORD,
]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def _monitor_of_focus():
    hwnd = user32.GetForegroundWindow()
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info))
    return hwnd, info


def _class_name(hwnd):
    buf = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, buf, 128)
    return buf.value


def _is_fullscreen(hwnd, info):
    """A game, video or slideshow covering the whole monitor (but not the desktop)."""
    if not hwnd or _class_name(hwnd) in ("Progman", "WorkerW", "Shell_TrayWnd"):
        return False
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    m = info.rcMonitor
    return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom


def premultiplied_bgra(img):
    """PIL RGBA -> premultiplied BGRA bytes, the format UpdateLayeredWindow expects."""
    a = np.asarray(img, dtype=np.uint16)
    alpha = a[..., 3:4]
    rgb = (a[..., :3] * alpha + 127) // 255
    return np.ascontiguousarray(np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], alpha[..., 0]]), dtype=np.uint8)


def hbitmap_from_image(img):
    """A 32-bit premultiplied-alpha GDI bitmap from a PIL RGBA image (caller owns the handle)."""
    data = premultiplied_bgra(img)
    h, w = data.shape[:2]
    screen = user32.GetDC(None)
    try:
        bmi = BITMAPINFOHEADER(
            biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=w, biHeight=-h, biPlanes=1, biBitCount=32, biCompression=0
        )
        bits = ctypes.c_void_p()
        bmp = gdi32.CreateDIBSection(screen, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        ctypes.memmove(bits, data.ctypes.data, data.nbytes)
        return bmp
    finally:
        user32.ReleaseDC(None, screen)


class Overlay:
    W, H = 260, 48  # window size in logical pixels; the pill sits near its bottom

    def __init__(self, app, hint="Hold Caps Lock to talk"):
        self.app = app  # needs .ui_state(), .levels, .on_click()
        self.hint = hint
        self.quit_requested = False
        self.message = None  # (text, error, until)

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Chit")
        self.s = self.root.winfo_fpixels("1i") / 96.0
        self.pw, self.ph = int(self.W * self.s), int(self.H * self.s)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{self.pw}x{self.ph}+0+0")
        self.root.bind("<Button-1>", lambda e: self.app.on_click())

        self.font = ImageFont.truetype("segoeui.ttf", int(11 * self.s * SS))
        self.size = list(IDLE)
        self.bars = [0.0] * BARS
        self.peak = 0.012
        self.pos = None
        self.hidden = False
        self.last_key = None
        self.last_place = 0.0
        self.frame = None

        self.root.update_idletasks()
        self._set_styles()
        self._show()
        self._place(force=True)
        self.root.after(30, self._tick)

    # -- window plumbing -------------------------------------------------- #
    def _hwnd(self):
        return user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()

    def _set_styles(self):
        hwnd = self._hwnd()
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex = (ex | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)

    def _show(self):
        """Tk's deiconify activates the window; hand focus straight back to where it was."""
        previous = user32.GetForegroundWindow()
        self.root.deiconify()
        self.root.update_idletasks()
        if previous and user32.GetForegroundWindow() == self._hwnd():
            user32.SetForegroundWindow(previous)
        if self.frame is not None:
            self._blit(self.frame)

    def _place(self, state="idle", force=False):
        now = time.monotonic()
        if not force and now - self.last_place < 0.4:
            return
        self.last_place = now
        hwnd, info = _monitor_of_focus()
        hide = state == "idle" and not self.message and _is_fullscreen(hwnd, info)
        if hide != self.hidden:
            self.hidden = hide
            (self.root.withdraw if hide else self._show)()
        w = info.rcWork
        pos = (w.left + (w.right - w.left - self.pw) // 2, w.bottom - self.ph)
        if pos != self.pos:
            self.pos = pos
            if self.frame is not None:
                self._blit(self.frame)

    def _blit(self, img):
        """Show an RGBA image with per-pixel alpha at the current position."""
        if self.pos is None:
            return
        data = premultiplied_bgra(img)
        h, w = data.shape[:2]
        screen = user32.GetDC(None)
        mem = gdi32.CreateCompatibleDC(screen)
        bmi = BITMAPINFOHEADER(
            biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=w, biHeight=-h, biPlanes=1, biBitCount=32, biCompression=0
        )
        bits = ctypes.c_void_p()
        bmp = gdi32.CreateDIBSection(mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        try:
            ctypes.memmove(bits, data.ctypes.data, data.nbytes)
            old = gdi32.SelectObject(mem, bmp)
            blend = BLENDFUNCTION(0, 0, 255, AC_SRC_ALPHA)
            user32.UpdateLayeredWindow(
                self._hwnd(),
                screen,
                ctypes.byref(wintypes.POINT(*self.pos)),
                ctypes.byref(wintypes.SIZE(w, h)),
                mem,
                ctypes.byref(wintypes.POINT(0, 0)),
                0,
                ctypes.byref(blend),
                ULW_ALPHA,
            )
            gdi32.SelectObject(mem, old)
        finally:
            gdi32.DeleteObject(bmp)
            gdi32.DeleteDC(mem)
            user32.ReleaseDC(None, screen)

    def _pill_rect(self):
        w, h = self.size[0] * self.s, self.size[1] * self.s
        cx, bottom = self.pw / 2, self.ph - 10 * self.s
        return cx - w / 2, bottom - h, cx + w / 2, bottom

    def _hovering(self):
        if self.pos is None or self.hidden:
            return False
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        x0, y0, x1, y1 = self._pill_rect()
        m = 14 * self.s  # generous, so the thin idle pill is easy to find
        return (
            self.pos[0] + x0 - m <= pt.x <= self.pos[0] + x1 + m
            and self.pos[1] + y0 - m <= pt.y <= self.pos[1] + y1 + m
        )

    # -- public ------------------------------------------------------------ #
    def show_message(self, text, error=False, seconds=2.5):
        self.message = (text, error, time.monotonic() + seconds)

    def quit(self):
        self.quit_requested = True

    def run(self):
        self.root.mainloop()

    # -- frame loop ------------------------------------------------------- #
    def _target(self, state, hover):
        if self.message:
            return self.font.getlength(self.message[0]) / (self.s * SS) + 28, 24.0
        if state == "listening":
            return LISTEN
        if state == "thinking":
            return THINK
        if hover:
            return self.font.getlength(self.hint) / (self.s * SS) + 28, 24.0
        return IDLE

    def _tick(self):
        if self.quit_requested:
            self.root.destroy()
            return
        try:
            state, hands_free = self.app.ui_state()
            if self.message and time.monotonic() > self.message[2]:
                self.message = None
            self._place(state)
            hover = state == "idle" and not self.message and self._hovering()
            tw, th = self._target(state, hover)
            settled = True
            for i, t in enumerate((tw, th)):
                diff = t - self.size[i]
                if abs(diff) > 0.3:
                    self.size[i] += diff * 0.35
                    settled = settled and abs(diff) < 2.0  # draw content once nearly there
                else:
                    self.size[i] = t
            if state == "listening":
                levels = list(self.app.levels)[-BARS:]
                levels = [0.0] * (BARS - len(levels)) + levels
                # Auto-gain: scale against a slowly decaying recent peak, so quiet and loud
                # voices both fill the graph without pinning every bar at the top.
                self.peak = max(max(levels), self.peak * 0.97, 0.012)
                for i, lv in enumerate(levels):
                    self.bars[i] += (lv / self.peak - self.bars[i]) * 0.55
            else:
                self.peak = 0.012
            key = (
                state,
                hands_free,
                hover,
                self.message,
                round(self.size[0], 1),
                round(self.size[1], 1),
                tuple(round(b, 3) for b in self.bars) if state == "listening" else None,
                int(time.monotonic() * 14) if state == "thinking" else None,
            )
            if key != self.last_key and not self.hidden:
                self.last_key = key
                self.frame = self.render(state, hands_free, hover, settled=settled)
                self._blit(self.frame)
        except Exception:
            pass  # a drawing glitch must never stop the UI loop
        self.root.after(33, self._tick)

    def render(self, state, hands_free, hover, settled=True):
        """The bar as an RGBA image (window-sized), with real transparency."""
        s = self.s * SS
        big = Image.new("RGBA", (self.pw * SS, self.ph * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        x0, y0, x1, y1 = (v * SS for v in self._pill_rect())
        h = y1 - y0
        error = bool(self.message and self.message[1])
        d.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=h / 2,
            fill=ERROR_PILL if error else PILL,
            outline=RIM,
            width=max(1, round(1.0 * s)),
        )
        if settled:
            cy = (y0 + y1) / 2
            if self.message:
                d.text(((x0 + x1) / 2, cy), self.message[0], font=self.font, fill=TEXT, anchor="mm")
            elif state == "idle" and hover:
                d.text(((x0 + x1) / 2, cy), self.hint, font=self.font, fill=TEXT, anchor="mm")
            elif state == "listening":
                self._draw_wave(d, x0, x1, cy, h, s, hands_free)
            elif state == "thinking":
                t = time.monotonic() * 6
                for i in range(3):
                    r = (1.6 + 1.0 * (0.5 + 0.5 * math.sin(t - i * 0.9))) * s
                    x = (x0 + x1) / 2 + (i - 1) * 7 * s
                    d.ellipse((x - r, cy - r, x + r, cy + r), fill=TEXT)
        pill = big.resize((self.pw, self.ph), Image.LANCZOS)

        # Soft shadow from the pill's own shape, a little below it.
        shadow_alpha = pill.getchannel("A").point(lambda a: int(a * SHADOW_ALPHA))
        offset = round(1.5 * self.s)
        shifted = Image.new("L", pill.size, 0)
        shifted.paste(shadow_alpha, (0, offset))
        shadow = Image.new("RGBA", pill.size, (0, 0, 0, 0))
        shadow.putalpha(shifted.filter(ImageFilter.GaussianBlur(3.0 * self.s)))
        shadow.alpha_composite(pill)
        return shadow

    def _draw_wave(self, d, x0, x1, cy, h, s, hands_free):
        left = x0 + h * 0.55
        right = x1 - h * 0.55
        if hands_free:
            r = 2.2 * s
            d.ellipse((x0 + h * 0.42 - r, cy - r, x0 + h * 0.42 + r, cy + r), fill=RED)
            left += 4 * s
        step = (right - left) / BARS
        bw = max(2, step * 0.42)
        for i, lv in enumerate(self.bars):
            amp = min(1.0, max(0.0, lv) ** 0.8)
            bh = max(2.5 * s, amp * h * 0.66)
            x = left + step * (i + 0.5)
            d.rounded_rectangle((x - bw / 2, cy - bh / 2, x + bw / 2, cy + bh / 2), radius=bw / 2, fill=TEXT)
