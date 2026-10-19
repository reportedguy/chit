# Third-party notices

Chit is MIT-licensed (see [LICENSE](LICENSE)). It builds on the following projects. The
Windows installer bundles the libraries below; their license texts are installed in the
`licenses` folder next to `Chit.exe`.

## Models (downloaded from Hugging Face on first run, not bundled)

| Model | Used for | License |
| --- | --- | --- |
| [OpenVINO/whisper-small-int8-ov](https://huggingface.co/OpenVINO/whisper-small-int8-ov), converted from [openai/whisper-small](https://huggingface.co/openai/whisper-small) | Speech recognition | Apache-2.0 |
| [OpenVINO/Qwen3-1.7B-int4-ov](https://huggingface.co/OpenVINO/Qwen3-1.7B-int4-ov), converted from [Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) | Text cleanup | Apache-2.0 |

## Shipped with Chit

| Component | Used for | License |
| --- | --- | --- |
| [Silero VAD](https://github.com/snakers4/silero-vad) model (`silero_vad_v6.onnx`), as packaged in [faster-whisper](https://github.com/SYSTRAN/faster-whisper); the windowing in `src/chit/vad.py` follows faster-whisper | Voice-activity detection | MIT (Silero Team; SYSTRAN) |

## Python libraries

| Library | License |
| --- | --- |
| [OpenVINO](https://github.com/openvinotoolkit/openvino), [OpenVINO GenAI](https://github.com/openvinotoolkit/openvino.genai), [OpenVINO Tokenizers](https://github.com/openvinotoolkit/openvino_tokenizers) | Apache-2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | MIT |
| [huggingface_hub](https://github.com/huggingface/huggingface_hub) | Apache-2.0 |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) (with PortAudio) | MIT |
| [NumPy](https://numpy.org) | BSD-3-Clause |
| [Pillow](https://python-pillow.org) | MIT-CMU |
| [pyperclip](https://github.com/asweigart/pyperclip) | BSD-3-Clause |
| [pynput](https://github.com/moses-palmer/pynput) | **LGPL-3.0** |
| [pystray](https://github.com/moses-palmer/pystray) | **LGPL-3.0** |
| [Python](https://www.python.org) and Tcl/Tk (bundled by PyInstaller) | PSF / Tcl-Tk license |

**LGPL-3.0 note:** Chit uses pynput and pystray unmodified. In the installed app they are
kept as plain Python source files under `_internal\pynput` and `_internal\pystray`, so you can
replace them with your own versions. Their source is available at the links above.

## Build tools (not shipped)

[PyInstaller](https://pyinstaller.org) (GPL-2.0 with a bootloader exception that allows
distributing the resulting app under any license) and [Inno Setup](https://jrsoftware.org/isinfo.php)
(Inno Setup license).

## Test audio

`src/chit/assets/bench.wav` and `scripts/data/*.wav` were generated for this project with the
built-in Windows text-to-speech voice and synthetic noise.
