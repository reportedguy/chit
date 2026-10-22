"""User settings, stored as JSON in the data dir."""

import json
import os
import threading

from .paths import DATA_DIR, SETTINGS_PATH

MIN_HOLD_MS = 250
MAX_HOLD_MS = 800

DEFAULTS = {
    "cleanup": "smart",  # smart | light | off
    "language": "en",  # en | hi | auto (auto can drift between languages mid-dictation)
    "asr_device": None,  # chosen by the first-run benchmark: NPU / GPU / CPU
    "llm_device": None,
    "mic": None,  # None = system default input
    "sounds": True,
    "debug_log": False,  # write dictated text to the log
    "hold_ms": 400,  # Caps Lock hold threshold to start dictation (250-800 ms)
    "setup_version": 0,  # bumped when the model set changes
    "defaults_version": 2,  # bumped when a default changes for existing installs
}


class Settings:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = dict(DEFAULTS)
        stored = {}
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                stored = json.load(f)
            for k, v in stored.items():
                if k == "hold_ms":
                    if isinstance(v, int) and not isinstance(v, bool) and MIN_HOLD_MS <= v <= MAX_HOLD_MS:
                        self._data[k] = v
                elif k in DEFAULTS:
                    self._data[k] = v
        except (OSError, ValueError):
            pass
        if stored and stored.get("defaults_version", 1) < 2:
            # v2: English instead of auto-detect (auto switched languages mid-dictation).
            self.set("language", "en")
            self.set("defaults_version", 2)

    def __getitem__(self, key):
        return self._data[key]

    def set(self, key, value):
        if key == "hold_ms" and (
            not isinstance(value, int) or isinstance(value, bool) or not (MIN_HOLD_MS <= value <= MAX_HOLD_MS)
        ):
            raise ValueError(f"hold_ms must be an integer between {MIN_HOLD_MS} and {MAX_HOLD_MS}, got {value!r}")
        with self._lock:
            self._data[key] = value
            os.makedirs(DATA_DIR, exist_ok=True)
            tmp = SETTINGS_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, SETTINGS_PATH)
