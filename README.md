<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo-dark.png">
  <img src="docs/images/logo-light.png" alt="Chit logo" width="112">
</picture>

# Chit

**Hold Caps Lock, talk, and clean text appears in any app — all on your own PC.**

A free, open-source, fully local alternative to Wispr Flow for Windows.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/reportedguy/chit?include_prereleases)](https://github.com/reportedguy/chit/releases)
[![CI](https://github.com/reportedguy/chit/actions/workflows/ci.yml/badge.svg)](https://github.com/reportedguy/chit/actions/workflows/ci.yml)
![Platform: Windows 10/11](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6)
[![Stars](https://img.shields.io/github/stars/reportedguy/chit?style=social)](https://github.com/reportedguy/chit/stargazers)

</div>

<!--
TODO (maintainer): record the demo and save it as docs/images/demo.gif, then replace the
"Demo coming soon" line below with:   ![Chit demo](docs/images/demo.gif)
What to record (15-25 s, 1280 px wide or less, under ~8 MB):
  1. Click into an empty email or chat box.
  2. Hold Caps Lock: the bar at the bottom center turns into the audio graph (chime plays).
  3. Say: "Um, so the meeting is on Tuesday, no wait, Wednesday at three. Can you bring the slides?"
  4. Release: the cleaned sentence appears.
  5. Optional: tap Caps Lock to show it still works as normal Caps Lock.
Tools: ScreenToGif (free) or ShareX -> export as GIF. Crop to the text box and the bottom of the screen.
-->
<p align="center"><em>🎬 Demo coming soon</em></p>

## What is Chit?

Chit is voice typing for Windows. Click into any text box, hold **Caps Lock**, say what you want
to write, and let go: your words appear where the cursor is, with the "um"s removed and
punctuation fixed.

**Why it exists:** dictation tools like Wispr Flow are great, but they process your voice in the
cloud and charge a subscription. Chit does the same core job **entirely on your computer**, for
free, with open-source code you can read and change. After a one-time model download it works
with no internet connection at all.

## Features

- **Works in any app**: email, chat, documents, browsers, code editors, anything you can type into.
- **Caps Lock stays Caps Lock**: a quick tap toggles capitals as usual; only holding it for 0.4 s starts dictation.
- **Hands-free mode**: double-tap Caps Lock to talk as long as you like; double-tap again to finish.
- **Clean text, not a raw transcript**: *Smart* cleanup removes filler words and stutters, applies
  self-corrections ("Tuesday, no wait, Wednesday" → "Wednesday") and fixes punctuation with a small
  local AI model. Guards fall back to rule-based cleanup if the model would change your meaning.
- **Fast**: phrases are transcribed while you are still talking, so text appears about a second
  after you let go (measured on an Intel Core Ultra 7 155U).
- **Uses your NPU or GPU**: on first run Chit tests your CPU, integrated GPU and Intel NPU and
  picks the fastest for each model.
- **Ignores background noise**: a voice detector drops keyboard clicks and room noise before
  transcription, so they never turn into words.
- **English and Hindi**: English by default; Hindi (Devanagari) and auto-detect in the tray menu.
- **Tiny on-screen indicator**: a thin pill at the bottom of the screen shows a live audio graph
  while listening and never steals focus from what you're typing in.
- **Private by design**: your audio and text never leave your PC. No account, no telemetry.

## How it compares

| | **Chit** | **Wispr Flow** | **Windows Voice Typing (Win+H)** |
| --- | --- | --- | --- |
| Where speech is processed | On your PC | In the cloud ([Wispr data controls](https://wisprflow.ai/data-controls)) | Microsoft's online speech service |
| Works offline | Yes, after the one-time model download | No | No |
| Price | Free | Free tier with a weekly word limit; paid Pro plan ([pricing](https://wisprflow.ai/pricing)) | Included with Windows |
| Open source | Yes (MIT) | No | No |
| AI cleanup (fillers, self-corrections) | Yes, local model | Yes, cloud | No |
| Platforms | Windows 10/11 | Mac, Windows, iPhone, Android | Windows |
| Accuracy | Good for clear speech; small local models | Mature, large cloud models | Good |

Facts about other products were checked against public sources in October 2026 and may change.

## Install

### Windows (recommended): download the installer

1. Go to the [latest release](https://github.com/reportedguy/chit/releases/latest) and download
   `ChitSetup-<version>.exe`.
2. Run it. If Windows shows **"Windows protected your PC"**, click **More info → Run anyway**
   (the installer isn't code-signed yet).
3. Leave **"Start Chit when I sign in to Windows"** ticked and finish. No admin rights are needed.
4. On first launch Chit downloads its models (about 1.4 GB, one time) and spends a minute or two
   finding the fastest chip on your PC. Then it's ready.

To uninstall: **Settings → Apps → Installed apps → Chit → Uninstall**. It asks whether to delete
the downloaded models and settings too.

### macOS and Linux

Not supported yet; see the [roadmap](ROADMAP.md). Help is welcome.

### Build from source

See [Development setup](#development-setup).

## Quick start

1. **Microphone access:** Windows must allow desktop apps to use the microphone:
   **Settings → Privacy & security → Microphone → Let desktop apps access your microphone** = On.
   No other permissions are needed.
2. Click into any text box.
3. **Hold Caps Lock.** After 0.4 s a soft chime plays and the bar at the bottom center shows a live
   audio graph. Talk, then **release**.
4. The cleaned text is pasted at your cursor, and your clipboard is restored.

**Examples** (real outputs of Smart cleanup)

| You say | Chit types |
| --- | --- |
| "Um, so I wanted to, uh, let you know that the the meeting is on Tuesday, no wait, Wednesday at three. And, you know, please, like, bring the slides." | "So I wanted to let you know that the meeting is on Wednesday at three. And, please, bring the slides." |
| "hey can you uh can you review my PR when you get a chance it's the one about the login page" | "Hey, can you review my PR when you get a chance? It's the one about the login page." |
| "send the invoice to Rahul, sorry, to Priya by end of day" | "Send the invoice to Priya by end of day." |

| Gesture | What happens |
| --- | --- |
| Tap Caps Lock | Normal Caps Lock |
| Hold Caps Lock (0.4 s+), talk, release | Dictate |
| Double-tap Caps Lock | Hands-free dictation (red dot on the bar) |
| Double-tap again, or click the bar | Finish hands-free |
| Esc while dictating | Cancel; nothing is typed |
| Shift + Caps Lock | Always a plain Caps Lock |

Hands-free stops on its own after 60 s without speech, and any dictation stops after 10 minutes.

## Settings

Right-click the Chit icon near the clock (it follows your light/dark theme):

| Menu item | Options |
| --- | --- |
| **Start / Stop dictation** | Same as clicking the bar |
| **Cleanup** | **Smart** (AI rewrite, default) · **Light** (remove fillers and repeats only) · **Off** (exact words) |
| **Language** | **English** (default) · **Hindi** · **Auto-detect** (can switch languages mid-dictation) |
| **Microphone** | System default or a specific input |
| **Sounds** | Start/stop chimes on or off |
| **Start at login** | Start Chit when you sign in (on by default) |
| **Open log** | Opens `%LOCALAPPDATA%\Chit\chit.log` |
| **Quit Chit** | Stops Chit until you start it again or next sign in |

Settings live in `%LOCALAPPDATA%\Chit\settings.json`. Advanced keys: `asr_device` / `llm_device`
(`CPU`, `GPU` or `NPU`, chosen by the setup benchmark) and `debug_log` (`true` writes dictated
text to the log; off by default).

Command-line options for `Chit.exe`: `--setup` re-runs the model download and chip benchmark;
`--background` starts without the welcome notification (used at sign-in).

## Requirements

| | |
| --- | --- |
| **OS** | Windows 10 (version 1809 or newer) or Windows 11, 64-bit |
| **CPU** | 64-bit x86 (Intel or AMD). Intel NPUs (AI Boost) and Intel integrated GPUs are used automatically when they are faster |
| **RAM** | 8 GB or more recommended (Chit uses about 1.4 GB while running) |
| **Disk** | About 2.5 GB: app ~0.4 GB, models ~1.4 GB, plus a compiled-model cache when the NPU is used |
| **Microphone** | Any |
| **Internet** | Only for the one-time model download |

**Models**

| Model | Job | Size |
| --- | --- | --- |
| [Whisper small](https://huggingface.co/OpenVINO/whisper-small-int8-ov) (OpenVINO, int8) | Speech recognition (multilingual) | ~257 MB download |
| [Qwen3-1.7B](https://huggingface.co/OpenVINO/Qwen3-1.7B-int4-ov) (OpenVINO, int4) | Smart cleanup | ~1.15 GB download |
| [Silero VAD](https://github.com/snakers4/silero-vad) | Voice detection | 1.2 MB, bundled |

**Speed** on the development laptop (Intel Core Ultra 7 155U, 32 GB RAM): Whisper ≈0.55 s per
phrase on the NPU or integrated GPU (≈0.95 s on the CPU); Smart cleanup ≈0.5–0.9 s per dictation
on the integrated GPU; about 1 s from releasing Caps Lock to text appearing. Expect slower results
on older CPUs without an NPU or Intel graphics; if Smart cleanup feels slow, switch to **Light**.
Whisper *small* trades some accuracy for speed: it does well on clear speech but is less accurate
than large cloud models on strong accents, unusual names and noisy rooms.

## Privacy

- **Your audio and text stay on your PC.** Audio is processed in memory and never saved to disk.
  Dictated text is not written to the log unless you turn on `debug_log`.
- **The only network access** is during first-run setup (or `--setup`): Chit downloads the two
  models above from [Hugging Face](https://huggingface.co). This is the only code in Chit that
  touches the network ([`src/chit/models.py`](src/chit/models.py)).
- **No telemetry or analytics.** Chit turns off ONNX Runtime's Windows telemetry events and
  Hugging Face Hub telemetry, and does not ship OpenVINO's (opt-in) model-converter telemetry.
- Clicking **Built by ReportedGuy** in the tray menu opens the author's website in your browser,
  only when you click it.

## How it's built

Python 3.12 · [OpenVINO](https://github.com/openvinotoolkit/openvino) and OpenVINO GenAI for Whisper
and the cleanup model · ONNX Runtime for Silero VAD · Tk for the on-screen bar · pystray for the
tray · pynput for the keyboard hook · PyInstaller and Inno Setup for the installer.

```
Caps Lock ─► keyboard-hook helper process ─► gesture state machine ─► microphone
   ─► pause segmenter ─► voice check (Silero) ─► Whisper (per phrase, while you talk)
   ─► on release: rules + Qwen3 cleanup ─► paste into the focused app
```

Diagram and module-by-module tour: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Project structure

```
chit/
├── src/chit/      # the app (see docs/ARCHITECTURE.md)
│   └── assets/    # VAD model, benchmark audio, author stamp
├── tests/         # unit tests (pytest)
├── scripts/       # end-to-end test, benchmarks, UI previews, brand images
├── packaging/     # PyInstaller spec, Inno Setup script, build.ps1
├── docs/          # architecture notes and images
└── .github/       # CI, release workflow, issue and PR templates
```

## Development setup

Requires Windows 10/11, [Python 3.12](https://www.python.org/downloads/) and Git.

```powershell
git clone https://github.com/reportedguy/chit.git
cd chit
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m chit                  # run (the first run downloads the models)
.venv\Scripts\python -m pytest                # unit tests
.venv\Scripts\python -m ruff check .          # lint
.venv\Scripts\python -m ruff format .         # format
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # build Chit.exe + installer
```

Building the installer also needs [Inno Setup 6](https://jrsoftware.org/isinfo.php)
(`winget install JRSoftware.InnoSetup`). Only one Chit runs at a time, so quit an installed copy
before running from source. More in [CONTRIBUTING.md](CONTRIBUTING.md).

## Troubleshooting / FAQ

**Nothing happens when I hold Caps Lock.**
Check that the Chit icon is in the tray. Hold for at least 0.4 s and wait for the chime before
speaking. Make sure no other app (another dictation tool, a keyboard remapper) also uses Caps Lock.

**It listens, but nothing is typed.**
Check the microphone permission (see Quick start) and the **Microphone** choice in the tray menu.
Very quiet or very short speech is treated as noise; speak normally after the chime.

**Text doesn't appear in one particular app.**
Windows doesn't let normal apps send input to apps running as administrator. Run that app
normally, or run Chit as administrator.

**The first words get cut off.**
Chit starts listening when the chime plays (0.4 s after you press). Wait for the chime.

**Transcription or cleanup is slow.**
Switch Cleanup to **Light**, or re-run the chip test with `Chit.exe --setup`.

**It typed in the wrong language.**
Set **Language** to English or Hindi instead of Auto-detect.

**The Caps Lock light blinks when I dictate.**
Expected: Windows toggles Caps Lock the moment you press it, and Chit switches it back once it
knows you're dictating, so your Caps Lock state is unchanged.

**Windows SmartScreen blocks the installer.**
Click **More info → Run anyway**. Signed builds are on the roadmap.

**Where are the logs?** `%LOCALAPPDATA%\Chit\chit.log` (tray → **Open log**). Please attach it to bug reports.

### Windows audio device troubleshooting

If the bottom indicator bar stays flat, audio capture fails, or text is not generated:

- **Windows Privacy & Microphone Permissions:**
  Windows requires explicit permission for desktop applications to access audio input:
  1. Go to **Settings → Privacy & security → Microphone** (Windows 11) or **Settings → Privacy → Microphone** (Windows 10).
  2. Verify that **Microphone access** is turned **On**.
  3. Verify that **Let desktop apps access your microphone** is toggled **On**. If this is turned off, Windows blocks audio capture at the API level and WASAPI streams will receive silence without raising an error.

- **Default Microphone Selection:**
  1. Open **Settings → System → Sound** (or press `Win+R`, type `mmsys.cpl`, and select the **Recording** tab).
  2. Set your primary microphone as the **Default Device** and **Default Communication Device**.
  3. Speak into your microphone and verify the Windows input level meter responds. If levels are too low, adjust input volume or mic boost.
  4. In device properties under the **Advanced** tab, ensure **Exclusive Mode** ("Allow applications to take exclusive control of this device") is not locked exclusively by another application.

- **WASAPI Device Configuration in Chit:**
  Chit captures audio via Windows WASAPI endpoints:
  1. Right-click the Chit tray icon and inspect the **Microphone** menu.
  2. If you have multiple input devices (e.g. built-in array, USB headset, external mic, or virtual audio device), select your specific hardware microphone directly instead of relying on the system default.
  3. If you plug in a new USB or Bluetooth microphone while Chit is running, open the tray menu or restart Chit to refresh WASAPI device enumeration.
  4. For Bluetooth headsets, ensure the device is connected in Hands-Free/Headset mode (HFP/HSP) rather than Stereo output only (A2DP).


## Roadmap

Next up: signed builds, a customizable hotkey, transcription history, a model manager, a custom
dictionary and per-app cleanup modes. Full list: [ROADMAP.md](ROADMAP.md).

## Contributing

Contributions are welcome! Start with [CONTRIBUTING.md](CONTRIBUTING.md), then look for issues
labelled [`good first issue`](https://github.com/reportedguy/chit/labels/good%20first%20issue).
Questions and ideas go to [Discussions](https://github.com/reportedguy/chit/discussions). Please
follow the [Code of Conduct](CODE_OF_CONDUCT.md), and report security issues privately as
described in [SECURITY.md](SECURITY.md).

## License and acknowledgements

Chit is released under the [MIT License](LICENSE). Built by [ReportedGuy](https://reportedguy.com).

Chit stands on the shoulders of
[OpenAI Whisper](https://github.com/openai/whisper),
[Qwen3](https://github.com/QwenLM/Qwen3),
[OpenVINO and OpenVINO GenAI](https://github.com/openvinotoolkit) (and their pre-converted models),
[Silero VAD](https://github.com/snakers4/silero-vad),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[ONNX Runtime](https://github.com/microsoft/onnxruntime),
[Hugging Face Hub](https://github.com/huggingface/huggingface_hub),
[sounddevice](https://github.com/spatialaudio/python-sounddevice) and PortAudio,
[pynput](https://github.com/moses-palmer/pynput),
[pystray](https://github.com/moses-palmer/pystray),
[Pillow](https://python-pillow.org), [NumPy](https://numpy.org),
[pyperclip](https://github.com/asweigart/pyperclip),
[PyInstaller](https://pyinstaller.org) and [Inno Setup](https://jrsoftware.org/isinfo.php).
Licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Wispr Flow is a trademark of its owner. Chit is an independent project and is not affiliated with
or endorsed by Wispr.
