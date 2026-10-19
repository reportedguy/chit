"""Microphone capture and the pause-based phrase segmenter."""

import threading
import time

import numpy as np

SAMPLE_RATE = 16000
BLOCK_MS = 100
BLOCK = SAMPLE_RATE * BLOCK_MS // 1000


class Segmenter:
    """Turns a stream of 100 ms blocks into phrase-sized chunks, cut at short pauses,
    so phrases can be transcribed while the user is still talking."""

    def __init__(self, emit, silence_ms=600, max_segment_s=20.0, min_threshold=0.006):
        self.emit = emit
        self.silence_blocks = max(1, silence_ms // BLOCK_MS)
        self.max_blocks = int(max_segment_s * 1000 / BLOCK_MS)
        self.min_threshold = min_threshold
        self.preroll = 3
        self.reset()

    def reset(self):
        self.blocks = []
        self.has_speech = False
        self.silent_run = 0
        self.noise = None

    def feed(self, block):
        rms = float(np.sqrt(np.mean(block * block)))
        if self.noise is None:
            self.noise = rms
        speech = rms > max(self.min_threshold, self.noise * 2.5)
        if not speech:
            # Track the room's noise floor only while nobody is talking.
            self.noise = 0.9 * self.noise + 0.1 * rms

        self.blocks.append(block)
        if speech:
            self.has_speech = True
            self.silent_run = 0
        else:
            self.silent_run += 1

        if not self.has_speech:
            self.blocks = self.blocks[-self.preroll :]
        elif self.silent_run >= self.silence_blocks or len(self.blocks) >= self.max_blocks:
            self._cut()
        return rms

    def flush(self):
        if self.has_speech:
            self._cut()
        self.reset()

    def _cut(self):
        audio = np.concatenate(self.blocks)
        self.blocks = self.blocks[-self.preroll :]  # trailing silence = next phrase's pre-roll
        self.has_speech = False
        self.silent_run = 0
        self.emit(audio)


class MicStream:
    def __init__(self, device, callback):
        import sounddevice as sd

        def cb(indata, frames, t, status):
            callback(indata[:, 0].copy())

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=BLOCK, device=device, callback=cb
        )

    def start(self):
        self.stream.start()

    def close(self):
        try:
            self.stream.stop()
        finally:
            self.stream.close()


class FileStream:
    """Test stand-in for the microphone: plays a WAV file in real time, then silence."""

    def __init__(self, path, callback):
        self.audio, self.callback, self.running = load_wav(path), callback, False

    def start(self):
        self.running = True

        def pump():
            i = 0
            while self.running:
                block = self.audio[i : i + BLOCK]
                self.callback(np.pad(block, (0, BLOCK - len(block))))
                i += BLOCK
                time.sleep(BLOCK_MS / 1000)

        threading.Thread(target=pump, daemon=True).start()

    def close(self):
        self.running = False


def input_devices():
    """(index, name) of usable microphones, default first."""
    import sounddevice as sd

    out = []
    try:
        default = sd.default.device[0]
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and sd.query_hostapis(d["hostapi"])["name"] == "Windows WASAPI":
                out.append((i, d["name"]))
        out.sort(key=lambda x: x[0] != default)
    except Exception:
        pass
    return out


def load_wav(path):
    """Read a PCM WAV file as 16 kHz mono float32."""
    import wave

    with wave.open(path, "rb") as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}[width]
    audio = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    if width == 1:
        audio = audio - 128
    audio /= float(2 ** (8 * width - 1))
    audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(len(audio) * SAMPLE_RATE / rate)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio)
    return audio.astype(np.float32)
