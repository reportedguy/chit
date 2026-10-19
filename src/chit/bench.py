"""Pick the fastest working device (NPU, integrated GPU or CPU) for each model on this PC."""

import functools
import gc
import os
import shutil
import stat
import time

from .log import log
from .paths import OV_CACHE_DIR, asset

LABELS = {"CPU": "processor (CPU)", "GPU": "graphics (GPU)", "NPU": "AI chip (NPU)"}
LLM_SAMPLE = (
    "um so can you send the the report to Rahul, sorry, to Priya by friday and uh let me know if anything is missing"
)
# Once some device cleans the sample this fast, testing a slower-to-compile one isn't worth minutes.
LLM_GOOD_ENOUGH_S = 1.0
NPU_TIE = 1.10


def cache_dir(kind, device):
    """Compiled-model cache, only for the NPU: compiling there takes ~45-80 s, while on the
    CPU/GPU it takes a few seconds and the cache would cost gigabytes of disk."""
    return os.path.join(OV_CACHE_DIR, f"{kind}-npu") if device == "NPU" else None


def _force_remove(func, path, _exc):
    # OpenVINO writes its cache blobs read-only; clear the flag and retry.
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def prune_caches(keep):
    """Delete compiled caches that aren't in use (e.g. from devices that lost the benchmark)."""
    if not os.path.isdir(OV_CACHE_DIR):
        return
    keep = {os.path.normcase(os.path.abspath(k)) for k in keep if k}
    for name in os.listdir(OV_CACHE_DIR):
        path = os.path.join(OV_CACHE_DIR, name)
        if os.path.normcase(os.path.abspath(path)) in keep:
            continue
        if os.path.isdir(path):
            shutil.rmtree(path, onerror=_force_remove)
        else:
            _force_remove(os.remove, path, None)
        if os.path.exists(path):
            log(f"Could not remove unused cache {name}")


def devices():
    try:
        import openvino as ov

        found = ov.Core().available_devices
    except Exception:
        return ["CPU"]
    out = ["CPU"]
    if any(d == "GPU" or d.startswith("GPU.") for d in found):
        out.append("GPU" if "GPU" in found else next(d for d in found if d.startswith("GPU")))
    if "NPU" in found:
        out.append("NPU")
    return out


def _time(fn, runs=2):
    fn()  # warm-up (first call can include lazy initialization)
    best = float("inf")
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


def _pick(kind, candidates, load, run, status, good_enough=None):
    results = {}
    for dev in candidates:
        if good_enough and results and min(results.values()) <= good_enough and dev == "NPU":
            log(f"{kind}: skipping {dev}, already fast enough")
            continue
        status(f"Testing on your {LABELS.get(dev.split('.')[0], dev)}...")
        model = None
        try:
            t = time.perf_counter()
            model = load(dev)
            compile_s = time.perf_counter() - t
            results[dev] = _time(functools.partial(run, model))
            log(f"{kind} on {dev}: {results[dev]:.2f}s (compiled in {compile_s:.0f}s)")
        except Exception as e:
            log(f"{kind} on {dev} failed: {e}")
        finally:
            model = None  # release the compiled model before testing the next device
            gc.collect()
    if not results:
        raise RuntimeError(f"No device could run the {kind} model")
    best = min(results, key=results.get)
    # Near-tie: prefer the NPU. It's built for this, saves battery, and keeps the GPU free.
    if "NPU" in results and results["NPU"] <= results[best] * NPU_TIE:
        best = "NPU"
    return best, results


def pick_devices(status=lambda msg: None):
    from . import models
    from .asr import Whisper
    from .audio import load_wav
    from .cleanup import SmartCleaner, light

    cands = devices()
    log(f"Benchmarking on {cands}")
    audio = load_wav(asset("bench.wav"))
    asr_dir, llm_dir = models.local_path(models.ASR_REPO), models.local_path(models.LLM_REPO)

    asr, asr_times = _pick(
        "asr", cands, lambda d: Whisper(asr_dir, d, cache_dir("asr", d)), lambda m: m.transcribe(audio, "en"), status
    )
    sample = light(LLM_SAMPLE)
    llm, llm_times = _pick(
        "llm",
        cands,
        lambda d: SmartCleaner(llm_dir, d, cache_dir("llm", d)),
        lambda m: m.rewrite(sample, 60),
        status,
        good_enough=LLM_GOOD_ENOUGH_S,
    )
    return asr, llm, asr_times, llm_times
