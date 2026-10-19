"""The models Chit uses, and downloading them (with progress) into the data dir."""

import os
import shutil
import threading
import time

from .paths import MODELS_DIR

# This module is the only code in Chit that touches the network, and only during first-run
# setup (downloading the two models below from Hugging Face).
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

ASR_REPO = "OpenVINO/whisper-small-int8-ov"  # multilingual Whisper (English + Hindi)
LLM_REPO = "OpenVINO/Qwen3-1.7B-int4-ov"  # text cleanup
SETUP_VERSION = 1
_MARKER = ".chit-complete"


def local_path(repo):
    return os.path.join(MODELS_DIR, repo.split("/")[-1])


def is_downloaded(repo):
    return os.path.exists(os.path.join(local_path(repo), _MARKER))


def _dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def remote_size(repo):
    from huggingface_hub import HfApi

    info = HfApi().model_info(repo, files_metadata=True)
    return sum(s.size or 0 for s in info.siblings), [s.rfilename for s in info.siblings]


def download(repo, on_progress=lambda done, total: None):
    """Download a model repo; on_progress(bytes_done, bytes_total) is called ~4x a second."""
    from huggingface_hub import hf_hub_download

    if is_downloaded(repo):
        return local_path(repo)
    dest = local_path(repo)
    os.makedirs(dest, exist_ok=True)
    total, files = remote_size(repo)
    finished = threading.Event()

    def report():
        while not finished.wait(0.25):
            on_progress(min(_dir_size(dest), total), total)

    threading.Thread(target=report, daemon=True).start()
    try:
        for name in files:
            for attempt in range(3):
                try:
                    hf_hub_download(repo, name, local_dir=dest)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2)
    finally:
        finished.set()
    # hf_hub_download keeps its own bookkeeping folder inside local_dir; not needed afterwards.
    shutil.rmtree(os.path.join(dest, ".cache"), ignore_errors=True)
    open(os.path.join(dest, _MARKER), "w").close()
    on_progress(total, total)
    return dest
