import json

from chit import config


def _use(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "SETTINGS_PATH", str(tmp_path / "settings.json"))
    return tmp_path / "settings.json"


def test_new_install_defaults_to_english(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    assert config.Settings()["language"] == "en"


def test_new_install_defaults_to_caps_lock(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    assert config.Settings()["hotkey"] == "caps_lock"


def test_set_hotkey_persists(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    s = config.Settings()
    s.set("hotkey", "rctrl")
    assert s["hotkey"] == "rctrl"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["hotkey"] == "rctrl"
    assert config.Settings()["hotkey"] == "rctrl"


def test_existing_auto_install_moves_to_english_once(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    path.write_text(json.dumps({"language": "auto", "cleanup": "light", "setup_version": 1}))
    s = config.Settings()
    assert s["language"] == "en" and s["cleanup"] == "light"
    # A later explicit choice of auto is respected (the migration runs only once).
    s.set("language", "auto")
    assert config.Settings()["language"] == "auto"


def test_hotkey_choices_and_mapping():
    from chit.hotkey import HOTKEYS, VK_CAPITAL, VK_F9, VK_RCONTROL, VK_RMENU, get_hotkey

    assert get_hotkey("caps_lock").vk == VK_CAPITAL
    assert get_hotkey("caps_lock").label == "Caps Lock"
    assert get_hotkey("rctrl").vk == VK_RCONTROL
    assert get_hotkey("rctrl").label == "Right Ctrl"
    assert get_hotkey("ralt").vk == VK_RMENU
    assert get_hotkey("ralt").label == "Right Alt"
    assert get_hotkey("f9").vk == VK_F9
    assert get_hotkey("f9").label == "F9"
    # Unknown key defaults to caps_lock
    assert get_hotkey("unknown") == HOTKEYS["caps_lock"]
