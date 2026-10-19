"""Soft start/stop chimes, synthesized once and played asynchronously from memory."""

import io
import wave
import winsound

import numpy as np

_cache = {}


def _tone(freqs, ms=110, volume=0.18):
    sr = 44100
    t = np.arange(int(sr * ms / 1000)) / sr
    wave_ = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
    env = np.minimum(1, t / 0.008) * np.exp(-t / (ms / 1000 / 3.5))  # quick attack, soft decay
    pcm = (wave_ * env * volume * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr), w.writeframes(pcm.tobytes())
    return buf.getvalue()


def play(name):
    if name not in _cache:
        _cache[name] = {"start": _tone([880, 1320]), "stop": _tone([660, 990]), "error": _tone([330, 311], ms=200)}[
            name
        ]
    try:
        # SND_ASYNC can't be combined with SND_MEMORY reliably, so play on a worker thread.
        import threading

        threading.Thread(target=winsound.PlaySound, args=(_cache[name], winsound.SND_MEMORY), daemon=True).start()
    except Exception:
        pass
