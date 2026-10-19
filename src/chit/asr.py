"""Speech recognition: multilingual Whisper through OpenVINO (NPU, GPU or CPU)."""

import re

DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Whisper's well-known hallucinations on near-silent audio.
HALLUCINATIONS = {
    "",
    "you",
    "thank you.",
    "thank you",
    "thanks for watching!",
    "thanks for watching.",
    "bye.",
    ".",
    "...",
    "shh.",
    "shh",
    "shh!",
    "hmm.",
    "mm-hmm.",
    "thanks.",
}


class Whisper:
    def __init__(self, model_dir, device, cache_dir=None):
        import openvino_genai as ov_genai

        self.device = device
        props = {"CACHE_DIR": cache_dir} if cache_dir else {}
        self.pipe = ov_genai.WhisperPipeline(model_dir, device, **props)

    def transcribe(self, audio, language=None):
        """language: None (auto-detect), 'en' or 'hi'."""
        kwargs = {"task": "transcribe"}
        if language:
            kwargs["language"] = f"<|{language}|>"
        text = str(self.pipe.generate(audio.tolist(), **kwargs)).strip()
        return "" if text.lower() in HALLUCINATIONS else text


def detect_language(text):
    """Pin a dictation to the language of its first phrase so later phrases don't flip."""
    return "hi" if DEVANAGARI.search(text) else "en"
