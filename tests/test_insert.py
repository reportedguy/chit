from unittest.mock import MagicMock, patch

from chit import insert


def test_insert_empty_text():
    inserter = insert.Inserter()
    with patch("chit.insert._foreground_class") as mock_fg:
        inserter.insert("")
        mock_fg.assert_not_called()


def test_insert_console_window_class(monkeypatch):
    monkeypatch.setattr(insert, "_foreground_class", lambda: "ConsoleWindowClass")
    inserter = insert.Inserter()
    inserter.kb = MagicMock()

    inserter.insert("hello world")
    inserter.kb.type.assert_called_once_with("hello world")


def test_insert_clipboard_flow(monkeypatch):
    monkeypatch.setattr(insert, "_foreground_class", lambda: "NotAConsole")
    inserter = insert.Inserter()
    inserter.kb = MagicMock()

    mock_pyperclip = MagicMock()
    mock_pyperclip.paste.return_value = "old_clipboard"

    with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
        inserter.insert("new text")

    mock_pyperclip.paste.assert_called_once()
    mock_pyperclip.copy.assert_any_call("new text")
    inserter.kb.pressed.assert_called_once()
