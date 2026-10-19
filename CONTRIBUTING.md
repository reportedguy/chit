# Contributing to Chit

Thanks for helping! Chit is a small project, so every bug report, idea and pull request matters.

## Ways to help

- **Report a bug** or **suggest a feature** with the issue templates.
- **Pick an issue** labelled [`good first issue`](https://github.com/reportedguy/chit/labels/good%20first%20issue)
  or [`help wanted`](https://github.com/reportedguy/chit/labels/help%20wanted).
- **Try Chit on different hardware** (Intel/AMD CPUs, NPUs, GPUs) and share timings from the
  log (`%LOCALAPPDATA%\Chit\chit.log`).

## Development setup

You need **Windows 10/11 (64-bit)**, **Python 3.12** and Git.

```powershell
git clone https://github.com/reportedguy/chit.git
cd chit
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m chit
```

The first launch opens the setup window: it downloads the models (~1.4 GB) into
`%LOCALAPPDATA%\Chit` and picks the fastest chip. Later launches start in a few seconds.
Only one copy of Chit runs at a time, so quit an installed Chit (tray icon → **Quit Chit**)
before running from source.

## Checks

| Command | What it does |
| --- | --- |
| `.venv\Scripts\python -m pytest` | Unit tests (gestures, cleanup rules and guards, audio front end, settings, icons) |
| `.venv\Scripts\python -m ruff check .` | Lint |
| `.venv\Scripts\python -m ruff format .` | Format (CI fails if formatting is off) |
| `.venv\Scripts\python scripts\e2e_app.py` | End-to-end test on a real desktop: simulated Caps Lock + a WAV file as the mic, pasting into a test window. Needs the models downloaded and no other Chit running. |
| `powershell -ExecutionPolicy Bypass -File packaging\build.ps1` | Builds `Chit.exe` and the installer (needs [Inno Setup 6](https://jrsoftware.org/isinfo.php): `winget install JRSoftware.InnoSetup`) |

Handy scripts in `scripts/`: `bench_llm.py` (cleanup quality and speed per chip),
`preview_bar.py` and `preview_tray_menu.py` (render the UI to PNG), `check_install.ps1`
(what an install left on the PC).

## Branches and commits

- Branch from `main`: `feat/short-name`, `fix/short-name`, `docs/short-name`.
- Use [Conventional Commits](https://www.conventionalcommits.org): `feat: …`, `fix: …`,
  `docs: …`, `refactor: …`, `test: …`, `build: …`, `ci: …`, `chore: …`.
- Keep pull requests focused: one change per PR.

## Pull request checklist

- [ ] `pytest` passes and `ruff check` / `ruff format --check` are clean
- [ ] New logic has a unit test where practical (pure logic lives in `gesture.py`, `cleanup.py`,
      `audio.py`, `hotkey.TriggerKey` so it can be tested without Windows input)
- [ ] You ran Chit and tried the change by hand (describe what you tried in the PR)
- [ ] Docs updated if behaviour changed (README, `docs/ARCHITECTURE.md`, CHANGELOG under *Unreleased*)
- [ ] No personal data, logs, models or build output committed

## Proposing features

Open a **Feature request** issue first for anything bigger than a small fix, so we can agree
on the approach before you spend time on it. Check [ROADMAP.md](ROADMAP.md): it may already be
planned, and a comment saying you'd like to work on it is welcome.

## Privacy rule

Chit's promise is that dictation never leaves the computer. Changes that add network access,
analytics or telemetry will not be accepted, except for clearly user-initiated actions (like
downloading models during setup).

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE)
and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
