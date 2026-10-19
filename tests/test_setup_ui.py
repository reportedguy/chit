import shutil
import time
import tkinter as tk
from collections import namedtuple

from chit import models, setup_ui

Usage = namedtuple("Usage", ["total", "used", "free"])


def test_format_size_bytes():
    assert setup_ui.format_size(0) == "0 B"
    assert setup_ui.format_size(512) == "512 B"


def test_format_size_kb():
    assert setup_ui.format_size(1024) == "1 KB"
    assert setup_ui.format_size(2048) == "2 KB"


def test_format_size_mb():
    assert setup_ui.format_size(240 * 1024 * 1024) == "240 MB"
    assert setup_ui.format_size(500 * 1024 * 1024) == "500 MB"


def test_format_size_gb():
    assert setup_ui.format_size(3 * 1024 * 1024 * 1024) == "3.0 GB"
    assert setup_ui.format_size(int(1.4 * 1024 * 1024 * 1024)) == "1.4 GB"
    assert setup_ui.format_size(1440 * 1024 * 1024) == "1.4 GB"
    assert setup_ui.format_size(1200 * 1024 * 1024) == "1.2 GB"


def test_get_free_disk_space_existing_path(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "disk_usage", lambda p: Usage(100, 40, 60))
    assert setup_ui.get_free_disk_space(str(tmp_path)) == 60


def test_get_free_disk_space_nonexistent_subpath(monkeypatch, tmp_path):
    called_with = []

    def mock_disk_usage(p):
        called_with.append(p)
        return Usage(100, 40, 60)

    monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)
    non_existent = tmp_path / "deep" / "nested" / "dir"
    assert setup_ui.get_free_disk_space(str(non_existent)) == 60
    assert called_with == [str(tmp_path)]


def test_get_free_disk_space_oserror(monkeypatch, tmp_path):
    def mock_err(p):
        raise OSError("Disk error")

    monkeypatch.setattr(shutil, "disk_usage", mock_err)
    assert setup_ui.get_free_disk_space(str(tmp_path)) == 0


def test_check_disk_space_sufficient(monkeypatch):
    monkeypatch.setattr(setup_ui, "get_free_disk_space", lambda p=None: 5 * 1024 * 1024 * 1024)
    has_space, free, req = setup_ui.check_disk_space()
    assert has_space is True
    assert free == 5 * 1024 * 1024 * 1024
    assert req == setup_ui.REQUIRED_DISK_SPACE


def test_check_disk_space_insufficient(monkeypatch):
    monkeypatch.setattr(setup_ui, "get_free_disk_space", lambda p=None: 1 * 1024 * 1024 * 1024)
    has_space, free, req = setup_ui.check_disk_space()
    assert has_space is False
    assert free == 1 * 1024 * 1024 * 1024
    assert req == setup_ui.REQUIRED_DISK_SPACE


def test_get_drive_name():
    assert setup_ui.get_drive_name(r"C:\Users\test") == "C:"
    assert setup_ui.get_drive_name(r"D:\data") == "D:"


def test_calculate_download_size_neither_downloaded(monkeypatch):
    monkeypatch.setattr(models, "is_downloaded", lambda repo: False)
    monkeypatch.setattr(models, "remote_size", lambda repo: (_ for _ in ()).throw(RuntimeError("offline")))
    expected = setup_ui.MODEL_SIZES[models.ASR_REPO] + setup_ui.MODEL_SIZES[models.LLM_REPO]
    assert setup_ui.calculate_download_size() == expected
    assert setup_ui.format_size(expected) == "1.4 GB"


def test_calculate_download_size_both_downloaded(monkeypatch):
    monkeypatch.setattr(models, "is_downloaded", lambda repo: True)
    assert setup_ui.calculate_download_size() == 0


def test_calculate_download_size_one_downloaded(monkeypatch):
    monkeypatch.setattr(models, "is_downloaded", lambda repo: repo == models.ASR_REPO)
    monkeypatch.setattr(models, "remote_size", lambda repo: (_ for _ in ()).throw(RuntimeError("offline")))
    expected = setup_ui.MODEL_SIZES[models.LLM_REPO]
    assert setup_ui.calculate_download_size() == expected


def test_calculate_download_size_uses_remote_size(monkeypatch):
    monkeypatch.setattr(models, "is_downloaded", lambda repo: False)
    mock_sizes = {
        models.ASR_REPO: (300 * 1024 * 1024, ["whisper.onnx"]),
        models.LLM_REPO: (1000 * 1024 * 1024, ["qwen.onnx"]),
    }
    monkeypatch.setattr(models, "remote_size", lambda repo: mock_sizes[repo])
    assert setup_ui.calculate_download_size() == 1300 * 1024 * 1024


def test_run_setup_insufficient_disk_space_stops_before_download(monkeypatch):
    monkeypatch.setattr(setup_ui, "check_disk_space", lambda *a, **k: (False, 1024**3, 3 * 1024**3))
    download_called = []
    monkeypatch.setattr(models, "download", lambda repo, on_progress: download_called.append(repo))

    class MockSettings:
        def set(self, k, v):
            pass

        def __getitem__(self, k):
            return None

    def custom_mainloop(self):
        self.update()
        time.sleep(0.05)
        self.update()
        self.destroy()

    monkeypatch.setattr(tk.Tk, "mainloop", custom_mainloop)
    res = setup_ui.run_setup(MockSettings())
    assert res is False
    assert download_called == []


def test_run_setup_sufficient_disk_space_proceeds_to_download(monkeypatch):
    monkeypatch.setattr(setup_ui, "check_disk_space", lambda *a, **k: (True, 10 * 1024**3, 3 * 1024**3))
    download_called = []
    monkeypatch.setattr(models, "download", lambda repo, on_progress: download_called.append(repo))
    monkeypatch.setattr(setup_ui.bench, "pick_devices", lambda status: ("CPU", "CPU", "0.1s", "0.1s"))

    class MockSettings:
        def set(self, k, v):
            pass

        def __getitem__(self, k):
            return None

    def custom_mainloop(self):
        self.update()
        time.sleep(0.05)
        self.update()
        self.destroy()

    monkeypatch.setattr(tk.Tk, "mainloop", custom_mainloop)
    res = setup_ui.run_setup(MockSettings())
    assert res is False
    assert len(download_called) > 0
