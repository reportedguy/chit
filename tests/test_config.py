import json

from chit import config


def _use(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "SETTINGS_PATH", str(tmp_path / "settings.json"))
    return tmp_path / "settings.json"


def test_new_install_defaults_to_english(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    assert config.Settings()["language"] == "en"


def test_existing_auto_install_moves_to_english_once(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    path.write_text(json.dumps({"language": "auto", "cleanup": "light", "setup_version": 1}))
    s = config.Settings()
    assert s["language"] == "en" and s["cleanup"] == "light"
    # A later explicit choice of auto is respected (the migration runs only once).
    s.set("language", "auto")
    assert config.Settings()["language"] == "auto"
