"""Caps Lock gestures, as a pure state machine (no Windows calls, easy to test).

Caps Lock stays a normal Caps Lock; the keyboard helper (hotkey.py) passes every tap
straight to Windows and only reports what happened:

- hold(t):        the key has been held for HOLD_S -> push-to-talk starts; key_up finishes.
- tap(down, up):  a normal tap. Two taps close together -> hands-free starts (the two
                  native toggles cancel out, so the Caps Lock state is unchanged).
- key_down/up:    raw presses while recording: a double-tap finishes hands-free.
- esc / click:    Esc cancels; clicking the on-screen bar starts hands-free or finishes.
"""

DEFAULT_HOLD_MS = 400
HOLD_S = 0.40  # default hold time for backward compatibility
DOUBLE_S = 0.35  # max gap between the taps of a double-tap


class Gestures:
    def __init__(self, start, finish, cancel, hands_free, hold_ms=DEFAULT_HOLD_MS):
        self._start, self._finish, self._cancel, self._hands_free = start, finish, cancel, hands_free
        self.set_hold_ms(hold_ms)
        self.state = "idle"
        self._last_tap_up = None  # idle: when the previous plain tap ended
        self._tap_down = None  # hands-free: when the current tap went down
        self._pending_tap = None  # hands-free: when the previous short tap ended

    def set_hold_ms(self, hold_ms):
        self.hold_ms = hold_ms
        self.hold_s = hold_ms / 1000.0

    def _go_idle(self):
        self.state = "idle"
        self._tap_down = self._pending_tap = None

    # -- from the keyboard helper ------------------------------------------ #
    def hold(self, t):
        if self.state == "idle":
            self._last_tap_up = None
            self.state = "held"
            self._start()

    def tap(self, t_down, t_up):
        if self.state != "idle":
            return
        if self._last_tap_up is not None and t_down - self._last_tap_up <= DOUBLE_S:
            self._last_tap_up = None
            self.state = "hands_free"
            self._start()
            self._hands_free()
        else:
            self._last_tap_up = t_up

    def key_down(self, t):
        if self.state == "hands_free":
            if self._pending_tap is not None and t - self._pending_tap <= DOUBLE_S:
                self._go_idle()
                self._finish()
            else:
                self._pending_tap = None
                self._tap_down = t

    def key_up(self, t):
        if self.state == "held":
            self._go_idle()
            self._finish()
        elif self.state == "hands_free":
            # Only short presses count as taps.
            if self._tap_down is not None and t - self._tap_down < self.hold_s:
                self._pending_tap = t
            self._tap_down = None

    def tick(self, t):
        if self.state == "hands_free" and self._pending_tap is not None and t - self._pending_tap > DOUBLE_S:
            self._pending_tap = None  # a single tap in hands-free is ignored

    # -- other inputs -------------------------------------------------------- #
    def esc(self):
        if self.state != "idle":
            self._go_idle()
            self._cancel()

    def click(self):
        if self.state == "idle":
            self.state = "hands_free"
            self._start()
            self._hands_free()
        else:
            self._go_idle()
            self._finish()

    def reset(self):
        """Dictation ended for another reason (auto-stop, error): forget the gesture."""
        self._go_idle()
        self._last_tap_up = None
