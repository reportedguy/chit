import sys
from unittest.mock import MagicMock

import pytest

from chit import insert


@pytest.fixture(autouse=True)
def mock_external_deps(monkeypatch):
    mock_pyperclip = MagicMock()
    mock_pynput = MagicMock()
    mock_keyboard = MagicMock()
    mock_pynput.keyboard = mock_keyboard

    monkeypatch.setitem(sys.modules, "pyperclip", mock_pyperclip)
    monkeypatch.setitem(sys.modules, "pynput", mock_pynput)
    monkeypatch.setitem(sys.modules, "pynput.keyboard", mock_keyboard)

    # Fast time.sleep
    monkeypatch.setattr(insert.time, "sleep", lambda s: None)
    return mock_pyperclip, mock_keyboard


def _make_inserter():
    inserter = insert.Inserter.__new__(insert.Inserter)
    inserter.kb = MagicMock()
    inserter.Key = MagicMock()
    inserter.Key.ctrl = "CTRL_KEY"
    return inserter


def test_empty_or_none_text_does_nothing(monkeypatch, mock_external_deps):
    mock_pyperclip, _ = mock_external_deps
    inserter = _make_inserter()
    fg_mock = MagicMock()
    monkeypatch.setattr(insert, "_foreground_class", fg_mock)

    inserter.insert("")
    inserter.insert(None)

    fg_mock.assert_not_called()
    inserter.kb.type.assert_not_called()
    inserter.kb.tap.assert_not_called()
    mock_pyperclip.copy.assert_not_called()
    mock_pyperclip.paste.assert_not_called()


def test_console_window_class_types_directly(monkeypatch, mock_external_deps):
    mock_pyperclip, _ = mock_external_deps
    inserter = _make_inserter()
    monkeypatch.setattr(insert, "_foreground_class", lambda: "ConsoleWindowClass")

    inserter.insert("hello cmd")

    inserter.kb.type.assert_called_once_with("hello cmd")
    mock_pyperclip.copy.assert_not_called()
    mock_pyperclip.paste.assert_not_called()
    inserter.kb.tap.assert_not_called()


def test_standard_window_saves_copies_pastes_and_restores(monkeypatch, mock_external_deps):
    mock_pyperclip, _ = mock_external_deps
    inserter = _make_inserter()
    monkeypatch.setattr(insert, "_foreground_class", lambda: "Notepad")

    clipboard_state = ["previous text"]
    copied = []

    def fake_paste():
        return clipboard_state[-1] if clipboard_state else ""

    def fake_copy(val):
        copied.append(val)
        clipboard_state.append(val)

    sleep_calls = []
    monkeypatch.setattr(insert.time, "sleep", lambda s: sleep_calls.append(s))
    mock_pyperclip.paste.side_effect = fake_paste
    mock_pyperclip.copy.side_effect = fake_copy

    pressed_cm = MagicMock()
    inserter.kb.pressed.return_value = pressed_cm

    inserter.insert("inserted text")

    # 1. Text copied first, then original restored
    assert copied == ["inserted text", "previous text"]
    # 2. Ctrl key pressed and 'v' tapped
    inserter.kb.pressed.assert_called_once_with("CTRL_KEY")
    pressed_cm.__enter__.assert_called_once()
    inserter.kb.tap.assert_called_once_with("v")
    pressed_cm.__exit__.assert_called_once()
    # 3. Sleep called to allow target app to read clipboard
    assert sleep_calls == [0.3]


def test_clipboard_restore_skipped_if_initial_paste_fails(monkeypatch, mock_external_deps):
    mock_pyperclip, _ = mock_external_deps
    inserter = _make_inserter()
    monkeypatch.setattr(insert, "_foreground_class", lambda: "Notepad")

    mock_pyperclip.paste.side_effect = RuntimeError("Clipboard busy")

    inserter.insert("dictated text")

    mock_pyperclip.copy.assert_called_once_with("dictated text")
    inserter.kb.tap.assert_called_once_with("v")


def test_clipboard_restore_exception_is_suppressed(monkeypatch, mock_external_deps):
    mock_pyperclip, _ = mock_external_deps
    inserter = _make_inserter()
    monkeypatch.setattr(insert, "_foreground_class", lambda: "Notepad")
    mock_pyperclip.paste.return_value = "original"

    calls = []

    def mock_copy(text):
        calls.append(text)
        if text == "original":
            raise RuntimeError("Cannot restore clipboard")

    mock_pyperclip.copy.side_effect = mock_copy

    # Must not raise
    inserter.insert("dictated text")
    assert calls == ["dictated text", "original"]


def test_inserter_init_constructs_controller_and_key(mock_external_deps):
    _, mock_keyboard = mock_external_deps
    mock_controller_instance = MagicMock()
    mock_keyboard.Controller.return_value = mock_controller_instance
    mock_keyboard.Key = MagicMock()

    ins = insert.Inserter()
    assert ins.kb is mock_controller_instance
    assert ins.Key is mock_keyboard.Key
