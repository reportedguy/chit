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


def test_new_install_defaults_hold_ms_to_400(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    assert config.Settings()["hold_ms"] == 400


def test_custom_hold_ms(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    s = config.Settings()
    for val in (250, 300, 400, 600, 800):
        s.set("hold_ms", val)
        assert config.Settings()["hold_ms"] == val


def test_invalid_hold_ms_validation(tmp_path, monkeypatch):
    import pytest

    _use(tmp_path, monkeypatch)
    s = config.Settings()
    for invalid in (249, 801, -1, 1000, "fast", None, True, False, 400.5):
        with pytest.raises(ValueError):
            s.set("hold_ms", invalid)


def test_stored_invalid_hold_ms_falls_back_to_default(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    path.write_text(json.dumps({"hold_ms": 100}))
    assert config.Settings()["hold_ms"] == 400

    path.write_text(json.dumps({"hold_ms": 600}))
    assert config.Settings()["hold_ms"] == 600

