import pytest

from chit.gesture import HOLD_S, Gestures
from chit.hotkey import TriggerKey


# --------------------------------------------------------------------------- #
# Gestures (app side)
# --------------------------------------------------------------------------- #
@pytest.fixture
def g():
    calls = []
    gestures = Gestures(
        start=lambda: calls.append("start"),
        finish=lambda: calls.append("finish"),
        cancel=lambda: calls.append("cancel"),
        hands_free=lambda: calls.append("hands_free"),
    )
    gestures.calls = calls
    return gestures


def raw_tap(g, t, length=0.08):
    """A tap while recording (the helper swallows it and forwards raw key events)."""
    g.key_down(t)
    g.key_up(t + length)


def test_hold_to_talk(g):
    g.hold(HOLD_S)
    g.tick(1.0)
    g.key_up(2.5)
    assert g.calls == ["start", "finish"]
    assert g.state == "idle"


def test_single_tap_does_nothing_in_chit(g):
    g.tap(0.0, 0.08)
    g.tick(1.0)
    assert g.calls == [] and g.state == "idle"  # Windows already toggled Caps Lock


def test_two_separate_taps_are_just_caps_lock(g):
    g.tap(0.0, 0.08)
    g.tap(1.0, 1.08)
    assert g.calls == []


def test_double_tap_starts_hands_free_and_double_tap_finishes(g):
    g.tap(0.0, 0.08)
    g.tap(0.30, 0.38)
    assert g.calls == ["start", "hands_free"]
    for t in (1, 5, 30):
        g.tick(t)
    assert g.state == "hands_free"
    raw_tap(g, 40.0)
    raw_tap(g, 40.25)
    assert g.calls == ["start", "hands_free", "finish"]
    assert g.state == "idle"


def test_triple_tap_does_not_start_twice(g):
    g.tap(0.0, 0.08)
    g.tap(0.25, 0.33)
    g.tap(0.5, 0.58)  # after hands-free began, taps arrive as raw keys, not taps
    assert g.calls == ["start", "hands_free"]


def test_single_tap_in_hands_free_is_ignored(g):
    g.tap(0.0, 0.08)
    g.tap(0.2, 0.28)
    raw_tap(g, 10.0)
    g.tick(11.0)
    raw_tap(g, 20.0)  # must not pair with the one at 10 s
    g.tick(21.0)
    assert g.calls == ["start", "hands_free"] and g.state == "hands_free"


def test_long_press_in_hands_free_does_not_count_as_tap(g):
    g.tap(0.0, 0.08)
    g.tap(0.2, 0.28)
    g.key_down(5.0)
    g.key_up(6.0)
    raw_tap(g, 6.1)
    g.tick(7.0)
    assert g.state == "hands_free"


def test_tap_after_a_hold_is_not_a_double_tap(g):
    g.tap(0.0, 0.08)
    g.hold(0.5)
    g.key_up(3.0)
    g.tap(3.1, 3.18)
    assert g.calls == ["start", "finish"]


def test_esc_cancels(g):
    g.hold(0.4)
    g.esc()
    assert g.calls == ["start", "cancel"] and g.state == "idle"
    g.esc()
    assert g.calls == ["start", "cancel"]


def test_click_toggles(g):
    g.click()
    assert g.calls == ["start", "hands_free"]
    g.click()
    assert g.calls[-1] == "finish" and g.state == "idle"


def test_reset_after_auto_stop(g):
    g.tap(0.0, 0.08)
    g.tap(0.2, 0.28)
    g.reset()
    assert g.state == "idle"
    g.hold(10.4)
    assert g.calls[-1] == "start"


# --------------------------------------------------------------------------- #
# TriggerKey (keyboard helper side)
# --------------------------------------------------------------------------- #
def test_tap_goes_straight_to_windows():
    k = TriggerKey()
    passthrough, msgs, timer = k.press(0.0)
    assert passthrough and msgs == [] and timer  # Windows toggles Caps Lock immediately
    passthrough, msgs = k.release(0.1)
    assert passthrough and msgs == [("tap", 0.0, 0.1)]


def test_hold_is_swallowed_after_threshold():
    k = TriggerKey()
    k.press(0.0)
    assert k.hold_due(0.0)  # timer fired while still down: switch Caps Lock back, start
    for t in (0.5, 0.53, 0.56):  # autorepeat
        assert k.press(t) == (False, [], False)
    passthrough, msgs = k.release(3.0)
    assert not passthrough and msgs == [("key", False, 3.0)]


def test_hold_timer_after_release_does_nothing():
    k = TriggerKey()
    k.press(0.0)
    k.release(0.1)
    assert not k.hold_due(0.0)


def test_stale_hold_timer_from_earlier_press_is_ignored():
    k = TriggerKey()
    k.press(0.0)
    k.release(0.1)
    k.press(0.2)
    assert not k.hold_due(0.0)
    assert k.hold_due(0.2)


def test_autorepeat_before_threshold_never_retoggles():
    k = TriggerKey()
    k.press(0.0)
    assert k.press(0.3) == (False, [], False)


def test_while_recording_everything_is_swallowed_and_forwarded():
    k = TriggerKey()
    k.recording = True
    passthrough, msgs, timer = k.press(5.0)
    assert not passthrough and msgs == [("key", True, 5.0)] and not timer
    passthrough, msgs = k.release(5.1)
    assert not passthrough and msgs == [("key", False, 5.1)]


def test_lost_key_up_is_recovered():
    k = TriggerKey()
    k.press(0.0)
    k.hold_due(0.0)
    passthrough, msgs, timer = k.press(5.0)  # no key-up for 5 s: it was lost
    assert msgs == [("key", False, 0.0)] and passthrough and timer
