"""Global hotkey via a low-level keyboard hook running in its own helper process.

Keeping the hook in a tiny process means nothing in the main app (Whisper, the LLM,
pasting, the UI) can ever slow the hook down enough for Windows to silently remove it.

Caps Lock stays a normal Caps Lock: a press goes straight to Windows, so a tap toggles
instantly. Only when the key is still held after HOLD_S does it become dictation; then
the helper switches Caps Lock back (undoing the press's toggle) and swallows the rest
of that press. While Chit is recording (hands-free), Caps Lock is swallowed entirely.

helper -> app:  ("hold", t)                  the key has been held for HOLD_S: start
                ("tap", t_down, t_up)        a normal tap (already handled by Windows)
                ("key", down: bool, t)       presses while recording / end of a hold
                ("esc", t)
app -> helper:  ("recording", bool)          Esc is only captured while recording
"""

import os
import threading
import time

from .gesture import HOLD_S

WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
LLKHF_INJECTED = 0x10
VK_SHIFT, VK_ESCAPE, VK_CAPITAL = 0x10, 0x1B, 0x14

# Marks keystrokes Chit sends itself (switching Caps Lock back after a hold), so the hook
# lets them through instead of treating them as the user's key.
CHIT_TAG = 0x43484954  # "CHIT"
KEYEVENTF_KEYUP = 0x2

# Typematic delay is at most ~1 s, so a key-down after a longer quiet gap while we think
# the key is held means its key-up was lost: treat it as a fresh press.
LOST_KEYUP_S = 1.2


class TriggerKey:
    """Decides, per Caps Lock event, whether Windows sees it and what the app is told.
    Pure logic (no Windows calls) so it can be unit-tested."""

    def __init__(self):
        self.down = False
        self.holding = False
        self.recording = False
        self.down_at = 0.0
        self.last = 0.0

    def press(self, now):
        """Returns (pass_to_windows, messages, start_hold_timer)."""
        repeat = self.down and now - self.last <= LOST_KEYUP_S
        previous, self.last = self.last, now
        if repeat:
            return False, [], False  # autorepeat: never let it re-toggle Caps Lock
        msgs = []
        if self.down:  # the previous press's key-up was lost
            if self.holding or self.recording:
                msgs.append(("key", False, previous))
            self.down = self.holding = False
        self.down, self.down_at = True, now
        if self.recording:
            return False, msgs + [("key", True, now)], False
        return True, msgs, True  # a normal Caps Lock press: Windows toggles it right now

    def hold_due(self, down_at):
        """The hold timer fired. True = this press is dictation (switch Caps Lock back)."""
        if self.down and self.down_at == down_at and not self.holding and not self.recording:
            self.holding = True
            return True
        return False

    def release(self, now):
        """Returns (pass_to_windows, messages)."""
        was_down, holding = self.down, self.holding
        self.down = self.holding = False
        if holding or self.recording:
            return False, [("key", False, now)] if was_down else []
        return True, [("tap", self.down_at, now)] if was_down else []


def _send_caps(*flags):
    import ctypes

    for f in flags:
        ctypes.windll.user32.keybd_event(VK_CAPITAL, 0x3A, f, CHIT_TAG)


def hook_main(conn, vk, accept_injected=False):
    import ctypes

    from pynput import keyboard

    get_key = ctypes.windll.user32.GetAsyncKeyState
    key = TriggerKey()
    lock = threading.Lock()
    send_lock = threading.Lock()
    listener = None

    def send(msg):
        with send_lock:
            try:
                conn.send(msg)
            except (BrokenPipeError, OSError):
                os._exit(0)

    def watch_parent():
        while True:
            try:
                kind, value = conn.recv()
            except (EOFError, OSError):
                os._exit(0)  # the app exited: never leave a stray hook behind
            if kind == "recording":
                with lock:
                    key.recording = value

    def hold_timer(down_at):
        with lock:
            due = key.hold_due(down_at)
        if not due:
            return
        if vk == VK_CAPITAL:
            # The press toggled Caps Lock; this is dictation, so switch it back. The
            # physical key is still down, so release it first or the toggle won't register.
            _send_caps(KEYEVENTF_KEYUP, 0, KEYEVENTF_KEYUP)
        send(("hold", time.monotonic()))

    def win32_filter(msg, data):
        if data.dwExtraInfo == CHIT_TAG:
            return True  # Chit's own keystroke
        if data.flags & LLKHF_INJECTED and not accept_injected:
            return True
        now = time.monotonic()
        is_down = msg in (WM_KEYDOWN, WM_SYSKEYDOWN)
        is_up = msg in (WM_KEYUP, WM_SYSKEYUP)

        if data.vkCode == VK_ESCAPE and vk != VK_ESCAPE and key.recording:
            if is_down:
                send(("esc", now))
            listener.suppress_event()

        if data.vkCode != vk:
            return True
        # Shift+Caps Lock is always a plain Caps Lock.
        if vk == VK_CAPITAL and get_key(VK_SHIFT) & 0x8000 and not key.down:
            return True

        with lock:
            if is_down:
                passthrough, msgs, start_timer = key.press(now)
            elif is_up:
                (passthrough, msgs), start_timer = key.release(now), False
            else:
                return True
        for m in msgs:
            send(m)
        if start_timer:
            threading.Timer(HOLD_S, hold_timer, args=(now,)).start()
        if not passthrough:
            listener.suppress_event()
        return True

    threading.Thread(target=watch_parent, daemon=True).start()
    listener = keyboard.Listener(win32_event_filter=win32_filter)
    listener.start()
    listener.join()


class KeyHook:
    """App-side handle: runs the helper, restarts it if it dies, forwards its events."""

    def __init__(self, vk, on_event, accept_injected=False):
        import multiprocessing as mp

        self.on_event = on_event
        self.vk, self.accept_injected = vk, accept_injected
        self.ctx = mp.get_context("spawn")
        self.recording = False
        self.stopping = False
        self._start()
        threading.Thread(target=self._pump, daemon=True).start()

    def _start(self):
        parent, child = self.ctx.Pipe()
        self.proc = self.ctx.Process(
            target=hook_main, args=(child, self.vk, self.accept_injected), daemon=True, name="chit-keyhook"
        )
        self.proc.start()
        child.close()
        self.conn = parent
        self.set_recording(self.recording)

    def _pump(self):
        from .log import log

        while not self.stopping:
            try:
                msg = self.conn.recv()
            except (EOFError, OSError):
                if self.stopping:
                    return
                log("Keyboard helper exited; restarting it")
                time.sleep(0.5)
                self._start()
                continue
            self.on_event(msg)

    def set_recording(self, recording):
        self.recording = recording
        try:
            self.conn.send(("recording", recording))
        except (BrokenPipeError, OSError):
            pass

    def stop(self):
        self.stopping = True
        try:
            self.conn.close()
        except OSError:
            pass
        self.proc.terminate()
