"""Generate scripts/data/noise.wav: room hum, fan-like noise, keyboard clicks and a cough-ish burst."""

import os
import wave

import numpy as np

rng = np.random.default_rng(7)
sr, secs = 16000, 6
t = np.arange(sr * secs) / sr
audio = 0.004 * np.sin(2 * np.pi * 50 * t)  # mains hum
audio += np.convolve(rng.normal(0, 0.02, len(t)), np.ones(30) / 30, "same")  # fan rumble
for c in rng.uniform(0.3, 5.5, 14):  # key clicks
    i = int(c * sr)
    audio[i : i + 120] += rng.normal(0, 0.25, 120) * np.exp(-np.arange(120) / 25)
i = int(3.2 * sr)  # a short breathy burst
audio[i : i + 3000] += rng.normal(0, 0.08, 3000) * np.hanning(3000)
pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
path = os.path.join(os.path.dirname(__file__), "data", "noise.wav")
with wave.open(path, "wb") as w:
    w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr), w.writeframes(pcm.tobytes())
print(path)
