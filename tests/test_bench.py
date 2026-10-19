import os
import stat

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
