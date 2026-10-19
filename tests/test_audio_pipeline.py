"""Audio front end: phrase segmentation and the noise gate (no speech models needed)."""

import os

import numpy as np
import pytest

from chit.asr import detect_language
from chit.audio import BLOCK, SAMPLE_RATE, Segmenter, load_wav

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "data")


def phrases(path):
    out = []
    seg = Segmenter(out.append)
    audio = load_wav(path)
    for i in range(0, len(audio), BLOCK):
        seg.feed(audio[i : i + BLOCK])
    seg.flush()
    return out


def test_load_wav_is_16k_mono_float():
    audio = load_wav(os.path.join(DATA, "en_fillers.wav"))
    assert audio.dtype == np.float32 and audio.ndim == 1
    assert 14 < len(audio) / SAMPLE_RATE < 15
    assert np.abs(audio).max() <= 1.0


def test_segmenter_cuts_at_pauses():
    chunks = phrases(os.path.join(DATA, "en_fillers.wav"))
    assert len(chunks) == 3  # the recording has two clear pauses
    assert all(1.0 < len(c) / SAMPLE_RATE < 7.0 for c in chunks)


def test_silence_produces_no_phrases():
    out = []
    seg = Segmenter(out.append)
    for _ in range(50):
        seg.feed(np.zeros(BLOCK, dtype=np.float32))
    seg.flush()
    assert out == []


def test_voice_detector_accepts_speech_and_rejects_noise():
    vad = pytest.importorskip("chit.vad").VoiceDetector()
    speech = phrases(os.path.join(DATA, "en_fillers.wav"))
    noise = load_wav(os.path.join(DATA, "noise.wav"))
    assert all(vad.voiced_seconds(c) > 1.0 for c in speech)
    assert vad.voiced_seconds(noise) < 0.3  # below Chit's MIN_VOICE_S: never transcribed


@pytest.mark.parametrize(
    "text, lang",
    [("Hello there", "en"), ("मैं कल ऑफिस नहीं आऊंगा", "hi"), ("Kal meeting hai", "en")],
)
def test_detect_language_pins_by_script(text, lang):
    assert detect_language(text) == lang
