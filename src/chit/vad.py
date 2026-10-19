"""Silero voice-activity detection: how much of a chunk is a human voice.

Used to drop phrases that are only room noise, taps or breathing, which Whisper would
otherwise "hear" as words like "Thanks." or "Shh.". The ONNX model and the windowing
scheme come from faster-whisper (MIT) / Silero VAD (MIT); see THIRD_PARTY_NOTICES.md.
"""

import numpy as np

from .paths import asset

WINDOW = 512  # samples per decision at 16 kHz (32 ms)
CONTEXT = 64


class VoiceDetector:
    def __init__(self):
        import onnxruntime

        # Windows builds of ONNX Runtime emit telemetry events by default; Chit sends nothing.
        onnxruntime.disable_telemetry_events()
        opts = onnxruntime.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        opts.enable_cpu_mem_arena = False
        opts.log_severity_level = 4
        self.session = onnxruntime.InferenceSession(
            asset("silero_vad_v6.onnx"), providers=["CPUExecutionProvider"], sess_options=opts
        )

    def probabilities(self, audio):
        audio = np.pad(audio.astype(np.float32), (0, (-len(audio)) % WINDOW))
        windows = audio.reshape(-1, WINDOW)
        context = np.roll(windows[:, -CONTEXT:], 1, axis=0)
        context[0] = 0
        batch = np.concatenate([context, windows], axis=1)
        h = np.zeros((1, 1, 128), dtype=np.float32)
        c = np.zeros((1, 1, 128), dtype=np.float32)
        out, _, _ = self.session.run(None, {"input": batch, "h": h, "c": c})
        return np.asarray(out).reshape(-1)

    def voiced_seconds(self, audio, threshold=0.5, min_run=3):
        """Seconds of speech, counting only runs of >= min_run windows (~100 ms)."""
        voiced, run = 0, 0
        for p in self.probabilities(audio):
            if p >= threshold:
                run += 1
            else:
                if run >= min_run:
                    voiced += run
                run = 0
        if run >= min_run:
            voiced += run
        return voiced * WINDOW / 16000
