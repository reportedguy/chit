"""Tiny logger: console when there is one, plus a rotating file in the data dir."""

import os
import sys
import threading
import time

from .paths import DATA_DIR, LOG_PATH

_file = None
_lock = threading.Lock()
debug_text = False  # when False, dictated text never reaches the log


def setup():
    global _file
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        if os.path.getsize(LOG_PATH) > 2_000_000:
            os.replace(LOG_PATH, LOG_PATH + ".old")
    except OSError:
        pass
    _file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - open for the app's lifetime
    if sys.stdout is None:  # windowed app: send stray prints and tracebacks to the file
        sys.stdout = sys.stderr = _file


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with _lock:
        if sys.stdout is not None and sys.stdout is not _file:
            try:
                print(line, flush=True)
            except Exception:
                pass
        if _file is not None:
            print(line, file=_file, flush=True)


def log_text(label, text):
    """Log dictated text only if the user turned on debug logging."""
    log(f"{label}: {text}" if debug_text else f"{label}: <{len(text)} chars>")
