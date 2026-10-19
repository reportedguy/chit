# Security policy

## Supported versions

Only the latest release of Chit receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately through GitHub: open the repository's **Security** tab and click
**Report a vulnerability**. Only the maintainer can see the report.

Please include:

- what the problem is and what an attacker could do with it,
- steps to reproduce (and the Chit version and Windows version),
- any ideas you have for a fix.

You can expect a first reply within 7 days. Once a fix is released, the report can be
made public and you will be credited unless you prefer not to be.

## Scope notes

Chit is a local desktop app. Things that are especially relevant:

- **Keyboard hook**: Chit installs a low-level keyboard hook to watch Caps Lock and Esc
  (`src/chit/hotkey.py`). It must never record or transmit other keystrokes.
- **Clipboard**: Chit temporarily replaces the clipboard to paste text, then restores it
  (`src/chit/insert.py`).
- **Network**: the only network access is downloading the speech and cleanup models from
  Hugging Face during first-run setup (`src/chit/models.py`).
- **Model files**: models are loaded from `%LOCALAPPDATA%\Chit\models`. Anyone who can write
  to that folder can change what Chit runs.
