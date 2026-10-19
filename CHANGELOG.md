# Changelog

All notable changes to Chit are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-20

First public release.

### Added

- Hold **Caps Lock** for 0.4 s to dictate, release to type the text into the focused app. A quick
  tap is still a normal Caps Lock; a double-tap starts hands-free dictation; **Esc** cancels.
- Local speech recognition with Whisper *small* (English and Hindi) through OpenVINO.
- Phrase-by-phrase transcription while you speak, so text appears about a second after you stop.
- Text cleanup: *Smart* (local Qwen3-1.7B rewrite that removes fillers and applies
  self-corrections, with safety guards), *Light* (rule-based filler removal) or *Off*.
- Voice-activity detection (Silero VAD) so background noise is never typed.
- First-run setup that downloads the models and picks the fastest chip (CPU, integrated GPU or
  Intel NPU) for each model.
- Minimal bar at the bottom of the screen: idle pill, live audio graph, and "thinking" dots.
- Tray menu: cleanup mode, language, microphone, sounds, start at login, log, quit.
- Windows installer (per-user, no admin), start at sign-in, clean uninstall.

[Unreleased]: https://github.com/reportedguy/chit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/reportedguy/chit/releases/tag/v0.1.0
