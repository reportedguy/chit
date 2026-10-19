# Roadmap

Where Chit is heading. It reflects the current code (v0.1.0: Windows, Whisper small,
Qwen3-1.7B cleanup, Caps Lock gestures). Want to help? Comment on the matching issue or open
one. Items marked **good first issue** are self-contained; **help wanted** needs someone with
the right skills or hardware.

## Now

- [ ] Demo GIF and screenshots in the README *(good first issue)*
- [ ] Code-signed Windows builds so SmartScreen stops warning on first run
- [ ] Customizable hotkey: pick another key than Caps Lock, and adjust the 0.4 s hold time
      *(good first issue: the trigger key is already a parameter of `KeyHook`)*
- [ ] Transcription history in the tray: re-paste or copy recent dictations *(help wanted)*
- [ ] More tests: `insert.py`, `bench.py` device picking, and a recorded-audio regression set
      *(good first issue)*

## Next

- [ ] Model manager: see, switch, re-download and delete models from the tray *(help wanted)*
- [ ] Choice of speech model size (tiny / small / medium / large-v3-turbo) with speed and
      accuracy shown per model
- [ ] Custom dictionary: names, jargon and spellings Whisper should prefer *(help wanted)*
- [ ] Snippets: say a trigger phrase, get a saved block of text
- [ ] Per-app cleanup modes (email, chat, code) based on the focused app *(help wanted)*
- [ ] Voice edit commands: "delete that", "new paragraph", "make it formal"
- [ ] Auto-updates (check GitHub Releases, opt-in)
- [ ] Settings window instead of tray-only settings *(help wanted)*
- [ ] NVIDIA GPU acceleration (OpenVINO targets Intel; add a CUDA backend for Whisper)
      *(help wanted)*

## Later

- [ ] Live preview of the words while you speak (streaming transcription)
- [ ] More languages, plus translation (speak Hindi, type English)
- [ ] macOS and Linux versions *(help wanted: needs hotkey, paste and overlay code per OS)*
- [ ] Plugin / extension API for custom post-processing
- [ ] Public accuracy and speed benchmark across hardware *(help wanted)*
- [ ] Accessibility review (screen readers, high contrast), UI localization and themes
