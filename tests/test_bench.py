import os
import stat

import pytest

from chit import bench


def test_prune_removes_readonly_caches_and_keeps_the_active_one(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "OV_CACHE_DIR", str(tmp_path))
    for name in ("asr-npu", "asr-cpu", "llm-gpu"):
        (tmp_path / name).mkdir()
        blob = tmp_path / name / "1.blob"
        blob.write_bytes(b"x")
        os.chmod(blob, stat.S_IREAD)  # OpenVINO writes blobs read-only
    (tmp_path / "loose.blob").write_bytes(b"x")

    bench.prune_caches({str(tmp_path / "asr-npu"), None})

    assert sorted(os.listdir(tmp_path)) == ["asr-npu"]


def test_cache_only_for_npu():
    assert bench.cache_dir("asr", "NPU").endswith("asr-npu")
    assert bench.cache_dir("llm", "GPU") is None
    assert bench.cache_dir("llm", "CPU") is None


import time


def _load_run(delays, failing=()):
    def load(dev):
        if dev in failing:
            raise RuntimeError(f"boom on {dev}")
        return dev

    def run(dev):
        time.sleep(delays[dev])

    return load, run


def test_pick_fastest_device_wins():
    load, run = _load_run({"CPU": 0.05, "GPU": 0.01})
    statuses = []

    best, results = bench._pick("llm", ["CPU", "GPU"], load, run, statuses.append)

    assert best == "GPU"
    assert set(results) == {"CPU", "GPU"}
    assert results["GPU"] <= results["CPU"]


def test_pick_prefers_npu_on_near_tie():
    load, run = _load_run({"CPU": 0.05, "GPU": 0.04, "NPU": 0.042})

    best, results = bench._pick("llm", ["CPU", "GPU", "NPU"], load, run, lambda _msg: None)

    assert best == "NPU"
    assert "NPU" in results


def test_pick_skips_npu_when_already_fast_enough():
    load, run = _load_run({"CPU": 0.001, "GPU": 0.001, "NPU": 0.001})
    calls = []
    statuses = []

    def tracking_load(dev):
        calls.append(dev)
        if dev in ("CPU", "GPU", "NPU"):
            return dev
        raise RuntimeError(f"boom on {dev}")

    best, results = bench._pick(
        "llm", ["CPU", "GPU", "NPU"], tracking_load, run, statuses.append, good_enough=1.0
    )

    assert "NPU" not in calls
    assert "NPU" not in results
    assert best in {"CPU", "GPU"}
    assert not any("NPU" in msg for msg in statuses)


def test_pick_ignores_failing_device():
    load, run = _load_run({"CPU": 0.02, "GPU": 0.001, "NPU": 0.10}, failing=("GPU",))

    best, results = bench._pick("llm", ["CPU", "GPU", "NPU"], load, run, lambda _msg: None)

    assert "GPU" not in results
    assert best == "CPU"


def test_pick_raises_when_all_devices_fail():
    load, run = _load_run({"CPU": 0.01, "GPU": 0.01}, failing=("CPU", "GPU"))

    with pytest.raises(RuntimeError, match="No device could run the llm model"):
        bench._pick("llm", ["CPU", "GPU"], load, run, lambda _msg: None)
